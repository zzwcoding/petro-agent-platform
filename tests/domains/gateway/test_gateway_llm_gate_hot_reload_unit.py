"""DE-14 信号量尺寸热加载单测——动态并发门四态（放大/缩小/在途保护/排队语义）。

G-06 原门（asyncio.Semaphore 直用）在首次 complete 构造时定格尺寸，改
stream.llm_max_concurrency 需重启（挂账清单 §E1）。本票以 _DynamicGate 轻量
包装替换：acquire 时刻读当前配置判额。四态断言：

1. 放大 2→4：已在途 2 路照跑，新起 2 路即时进闸（峰值 4）；
2. 缩小 4→2：新起调用排队不报错，待在途释放到新额内才逐个补位；
3. 缩小时已在途 4 路不被中断——全部照常应答（无取消/无异常）；
4. G-06 原语义零破坏：超限排队等而非挂死（6 路/上限 2——逐放行逐补位，全成功）。

编排确定性（DE-15 交错测试先例）：探测后端进闸即挂（Event 栅栏），测试逐个
放行；自旋 sleep(0) 推进事件循环，无 wall-clock 依赖、无真实上游。进闸等待
只看 entered 单调计数（active 在「旧调用未退/新调用未进」瞬时会暂时等于
目标值——不看它判进闸）；active 只用于确认退出与满额时刻。

配置感知（票面交付②）：get_models_config() 是内存缓存路径——每 acquire 读
配置无 IO 成本，票面裁决「廉路径直接读、零节流」；本文件末尾以「移除真源
文件后缓存读仍成功」作机器钉。
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.domains.gateway import Completion, GatewayService
from app.infra.config import get_models_config, load_models_config
from app.infra.llm_client import LlmCompletion

# 受控注册表（字面假值；stream.llm_max_concurrency 是本票被测参数）。
TEST_YAML = """\
models:
  - alias: petro-main
    provider: anthropic
    model: MiniMax-M3
    base_url: https://main.example.test
    api_key: sk-test
    context_window: 1000000
    group: standard
  - alias: petro-lite
    provider: anthropic
    model: glm-5.3-flash
    base_url: https://lite.example.test
    api_key: sk-test
    context_window: 1000000
    group: lite
routing:
  default: petro-main
  fallback_order: [petro-main, petro-lite]
prices:
  default:
    input_per_mtok: 1.0
    output_per_mtok: 3.0
gateway:
  allowed_fails: 99
  cooldown_seconds: 0
  num_retries: 0
  request_timeout: 5
stream:
  idle_timeout: 5
  max_seconds: 30
  llm_max_concurrency: {limit}
"""


def _reload(path: Path, limit: int) -> None:
    """改 stream.llm_max_concurrency 后走 load_models_config 热加载（生产热加载同缝）。"""
    path.write_text(TEST_YAML.format(limit=limit), encoding="utf-8")
    load_models_config(path)


@pytest.fixture
def gate_yaml(tmp_path: Path) -> Path:
    """受控 models.yaml（初始上限 2＝缺省基线）＋预热注册表缓存。"""
    path = tmp_path / "models.yaml"
    path.write_text(TEST_YAML.format(limit=2), encoding="utf-8")
    load_models_config(path)
    return path


def _completion(alias: str) -> LlmCompletion:
    return LlmCompletion(
        content="好",
        prompt_tokens=1,
        completion_tokens=1,
        usage_estimated=False,
        duration_ms=1,
        model=alias,
    )


class _HoldBackend:
    """并发探针后端：进闸即挂（Event 栅栏持额），测试逐个放行——进出门事件化。"""

    def __init__(self) -> None:
        self.active = 0
        self.peak = 0
        self.entered: list[str] = []
        self.holds: list[asyncio.Event] = []

    def release(self, index: int) -> None:
        """放行第 index 个进闸调用（进闸序＝holds 序）。"""
        self.holds[index].set()

    def release_all(self) -> None:
        for hold in self.holds:
            hold.set()

    async def complete(self, alias: str, messages: list[dict[str, str]], *,
                       timeout_seconds: float, max_tokens: int = 4096,
                       **kw: Any) -> LlmCompletion:
        self.active += 1
        self.peak = max(self.peak, self.active)
        self.entered.append(alias)
        hold = asyncio.Event()
        self.holds.append(hold)
        try:
            await hold.wait()
        finally:
            self.active -= 1
        return _completion(alias)


def _fire(gw: GatewayService, i: int) -> asyncio.Task[Completion]:
    return asyncio.create_task(
        gw.complete("petro-main", [{"role": "user", "content": f"q{i}"}], caller="test.gate")
    )


async def _wait_entered(backend: _HoldBackend, n: int) -> None:
    """自旋等待第 n 路进闸（entered 单调计数——进闸判据；sleep(0) 确定性推进）。"""
    for _ in range(2000):
        if len(backend.entered) >= n:
            return
        await asyncio.sleep(0)
    raise AssertionError(
        f"等待 {n} 路进闸超时（entered={len(backend.entered)}，active={backend.active}）"
    )


async def _wait_active(backend: _HoldBackend, n: int) -> None:
    """自旋等待在途数到达 n（仅用于确认退出/满额时刻——不做进闸判据）。"""
    for _ in range(2000):
        if backend.active == n:
            return
        await asyncio.sleep(0)
    raise AssertionError(
        f"等待 active={n} 超时（active={backend.active}，entered={len(backend.entered)}）"
    )


async def _settle() -> None:
    """放行若干圈事件循环——排队任务要么已进闸要么仍在队（「未进」断言窗口）。"""
    for _ in range(50):
        await asyncio.sleep(0)


# ---------- 四态测试 ----------


async def test_grow_admits_new_calls_immediately(gateway_db: Any, gate_yaml: Path) -> None:
    """放大 2→4：已在途 2 路照跑，新起 2 路即时进闸（峰值 4——热加载即时生效）。"""
    backend = _HoldBackend()
    gw = GatewayService(gateway_db, backend)
    legacy = [_fire(gw, i) for i in range(2)]
    await _wait_entered(backend, 2)

    _reload(gate_yaml, 4)  # 热加载：2→4（不重启）
    newcomers = [_fire(gw, i) for i in range(2, 4)]
    await _wait_entered(backend, 4)  # 旧实现此处红：尺寸定格 2，新起进不来

    assert backend.active == 4
    assert backend.peak == 4  # 新额 4 路同时在途

    backend.release_all()
    results = await asyncio.gather(*legacy, *newcomers)
    assert len(results) == 4


async def test_shrink_queues_new_calls_per_new_limit(gateway_db: Any, gate_yaml: Path) -> None:
    """缩小 4→2：新起调用排队不报错；在途释放到新额内才逐个补位（队首 FIFO）。"""
    backend = _HoldBackend()
    gw = GatewayService(gateway_db, backend)

    _reload(gate_yaml, 4)  # 先放大到 4 造出 4 路在途
    legacy = [_fire(gw, i) for i in range(4)]
    await _wait_entered(backend, 4)

    _reload(gate_yaml, 2)  # 热加载：4→2（在途 4 路不受影响）
    newcomers = [_fire(gw, i) for i in range(4, 6)]
    await _settle()
    assert len(backend.entered) == 4  # 新起 2 路未进闸（排队）
    assert backend.active == 4

    backend.release(0)  # 在途 4→3：仍 ≥ 新额 2，排队者继续等
    await _wait_active(backend, 3)  # 确认第 1 路已退出（进闸判据不看 active）
    await _settle()
    assert len(backend.entered) == 4
    backend.release(1)  # 在途 3→2：恰在新额上，排队者继续等
    await _wait_active(backend, 2)
    await _settle()
    assert len(backend.entered) == 4

    backend.release(2)  # 在途 2→1：低于新额——队首（第 5 起）进闸
    await _wait_entered(backend, 5)
    await _wait_active(backend, 2)
    backend.release(3)  # 再释一位：第 6 起补位
    await _wait_entered(backend, 6)
    await _wait_active(backend, 2)

    backend.release_all()
    results = await asyncio.gather(*legacy, *newcomers)
    assert len(results) == 6  # 排队不报错——全员应答


async def test_shrink_does_not_interrupt_in_flight(gateway_db: Any, gate_yaml: Path) -> None:
    """缩小 4→2：已在途 4 路不被新额中断——全部照常应答（无取消/无异常）。"""
    backend = _HoldBackend()
    gw = GatewayService(gateway_db, backend)

    _reload(gate_yaml, 4)
    tasks = [_fire(gw, i) for i in range(4)]
    await _wait_entered(backend, 4)

    _reload(gate_yaml, 2)
    await _settle()
    assert all(not t.done() for t in tasks)  # 缩小未打断任何在途

    backend.release_all()
    results = await asyncio.gather(*tasks)  # 有取消/异常在此即红
    assert len(results) == 4
    assert gw._llm_gate is not None
    assert gw._llm_gate.current_limit() == 2  # 收流后现额＝新配置
    assert gw._llm_gate.locked() is False  # 闸全释放


async def test_over_limit_queues_then_flows_not_rejects(gateway_db: Any, gate_yaml: Path) -> None:
    """G-06 原语义零破坏：6 路并发/上限 2——超限排队等而非挂死，逐放行逐补位全成功。"""
    backend = _HoldBackend()
    gw = GatewayService(gateway_db, backend)
    tasks = [_fire(gw, i) for i in range(6)]
    await _wait_entered(backend, 2)
    await _settle()
    assert len(backend.entered) == 2  # 超限 4 路排队未进、未报错

    for i in range(4):  # 前四次放行各恰好补进一名排队者（FIFO）
        backend.release(i)
        await _wait_entered(backend, 3 + i)
        await _wait_active(backend, 2)

    backend.release(4)
    backend.release(5)  # 已全员进闸——余下放行纯收流
    results = await asyncio.gather(*tasks)
    assert len(results) == 6  # 排队等而非拒绝
    assert backend.peak == 2  # 峰值恒 ≤ 上限


async def test_cancel_while_queued_does_not_leak_slot(gateway_db: Any, gate_yaml: Path) -> None:
    """排队中被取消：额度不泄漏——后继调用照常进闸（取消回吐路径回归钉）。"""
    backend = _HoldBackend()
    gw = GatewayService(gateway_db, backend)
    first = [_fire(gw, i) for i in range(2)]
    await _wait_entered(backend, 2)
    queued = _fire(gw, 2)
    await _settle()
    assert len(backend.entered) == 2  # 第 3 路排队中

    queued.cancel()
    with pytest.raises(asyncio.CancelledError):
        await queued

    backend.release(0)
    await _wait_active(backend, 1)  # 第 1 路退出、无补位（队列已空）
    third = _fire(gw, 3)
    await _wait_entered(backend, 3)  # 取消未泄漏额度——第 4 路可进
    await _wait_active(backend, 2)

    backend.release_all()
    results = await asyncio.gather(*first, third)
    assert len(results) == 3


# ---------- 配置感知成本钉（票面交付②） ----------


def test_per_acquire_config_read_is_memory_cached(gate_yaml: Path) -> None:
    """每 acquire 读配置＝内存缓存路径：移除真源文件后读取仍成功（无 IO 成本→零节流）。"""
    first = get_models_config()
    gate_yaml.unlink()  # 真源移除——若读取走 IO 此处即 FileNotFoundError
    second = get_models_config()
    assert second is first  # 同一缓存对象——读取未触盘
