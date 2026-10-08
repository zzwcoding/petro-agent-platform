"""V2-01 infra 复制层验收——specs/infra.md「验收测试」表五条逐条落测。

五条对应（票面验收表）：
- llm_single_exit：appv2 树 AST 扫描——litellm import 只出现在
  appv2/infra/llm_client.py（B6 单出口；V1 树有自家 llm_client，不在本票
  扫描域——「全仓」指 V2 复制层全集）。
- no_v1_dependency：appv2 树 AST 扫描——零条 app.*（V1）import（双向禁引
  之 V2 侧；specs/modules.md 边界规则 Owner 2026-10-08 拍板）。
- gateway_gate：动态闸＋预算熔断行为与 V1 一致——超限排队等而非拒、峰值
  恒 ≤ llm_max_concurrency（G-06/DE-14 语义）；预算触顶改路由降级组不拒绝
  （F2 改注语义）。
- readonly_guard：midplatform 只读会话写意图抛 ReadOnlyViolation（INV-2；
  意图级 flush 守卫）＋只读角色拒开写会话。
- audit_single_writer：audit 表直写代码只许存在于 appv2/infra/security
  （B12 唯一写口的代码扫描面）——其他模块 import AuditLog/AuditLogStore
  或 raw SQL 直写即红；正向面：security.audit 落库可读（agent_v2.* 前缀）。

扫描口径：AST import 面（Import/ImportFrom），与 import-linter 契约同语义
——docstring 提及不算接触。
"""

import ast
import asyncio
import re
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

import appv2.infra.config as v2_config
from appv2.infra.config import load_models_config
from appv2.infra.db import ConnectionManager, DatabaseSpec, ReadOnlyViolation
from appv2.infra.gateway import Completion, GatewayService
from appv2.infra.gateway.store import ensure_gateway_tables
from appv2.infra.llm_client import LlmCompletion
from appv2.infra.security import AuditRow, SecurityService
from appv2.infra.security.store import ensure_audit_table

_REPO_ROOT = Path(__file__).resolve().parents[2]
_APPV2_ROOT = _REPO_ROOT / "appv2"
_LLM_CLIENT = _APPV2_ROOT / "infra" / "llm_client.py"
_SECURITY_PKG = _APPV2_ROOT / "infra" / "security"


def _v2_py_files() -> list[Path]:
    files = sorted(_APPV2_ROOT.rglob("*.py"))
    assert files, "appv2 树为空——扫描面失效（测试自保护）"
    return files


def _imported_roots(path: Path) -> list[str]:
    """AST 提取绝对 import 的顶层包名序列（完整模块路径；相对 import 不出包，略）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.append(node.module)
    return modules


def _imported_names(path: Path) -> list[str]:
    """AST 提取 import 的绑定名（import x as y 取 y；from m import x 取 x）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.extend(alias.asname or alias.name for alias in node.names)
    return names


# ---------- 验收①：litellm 只出现在 appv2/infra/llm_client.py ----------


def test_llm_single_exit() -> None:
    offenders = [
        path
        for path in _v2_py_files()
        if any(m == "litellm" or m.startswith("litellm.") for m in _imported_roots(path))
        and path != _LLM_CLIENT
    ]
    assert offenders == [], f"litellm 逃逸 B6 单出口（只许 appv2/infra/llm_client.py）: {offenders}"
    assert any(
        m == "litellm" or m.startswith("litellm.") for m in _imported_roots(_LLM_CLIENT)
    ), "appv2/infra/llm_client.py 未 import litellm——B6 出口本体缺失"


# ---------- 验收②：复制层无任何 app/（V1）import ----------


def test_no_v1_dependency() -> None:
    offenders: dict[str, list[str]] = {}
    for path in _v2_py_files():
        v1 = [m for m in _imported_roots(path) if m.split(".")[0] == "app"]
        if v1:
            offenders[str(path.relative_to(_REPO_ROOT))] = v1
    assert offenders == {}, "appv2 咬了 V1（app.* import 禁）:" + str(offenders)


# ---------- 验收③：gateway 动态闸＋预算熔断（与 V1 一致） ----------

# 受控注册表（字面假值；结构同 config/models.yaml。stream.llm_max_concurrency
# 是动态闸被测参数；prices.input_per_mtok 由熔断场景热加载放大）。
_GATE_YAML = """\
models:
  - alias: petro-main
    provider: anthropic
    model: MiniMax-M3
    base_url: https://main.example.test
    api_key: sk-test-main
    context_window: 1000000
    group: standard
  - alias: petro-lite
    provider: anthropic
    model: glm-5.3-flash
    base_url: https://lite.example.test
    api_key: sk-test-lite
    context_window: 1000000
    group: lite
routing:
  default: petro-main
  fallback_order: [petro-main, petro-lite]
prices:
  default:
    input_per_mtok: {input_per_mtok}
    output_per_mtok: 3.0
gateway:
  allowed_fails: 99
  cooldown_seconds: 0
  num_retries: 0
  request_timeout: 5
stream:
  idle_timeout: 5
  max_seconds: 30
  llm_max_concurrency: 2
"""


@pytest.fixture
def gate_yaml(tmp_path: Path) -> Iterator[Path]:
    """受控 models.yaml 预热 appv2 注册表缓存；用例结束复位（测试隔离）。"""
    path = tmp_path / "models.yaml"
    path.write_text(_GATE_YAML.format(input_per_mtok=1.0), encoding="utf-8")
    load_models_config(path)
    yield path
    v2_config._models_cache = None


@pytest.fixture
async def gateway_db(tmp_path: Path) -> AsyncIterator[ConnectionManager]:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "v2-gateway.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_gateway_tables(manager.engine())
    yield manager
    await manager.dispose()


class _HoldBackend:
    """并发探针后端：进闸即挂（Event 栅栏持额），测试逐个放行——进出门事件化。"""

    def __init__(self) -> None:
        self.active = 0
        self.peak = 0
        self.entered: list[str] = []
        self.holds: list[asyncio.Event] = []

    def release(self, index: int) -> None:
        self.holds[index].set()

    def release_all(self) -> None:
        for hold in self.holds:
            hold.set()

    async def complete(
        self,
        alias: str,
        messages: list[dict[str, str]],
        *,
        timeout_seconds: float,
        max_tokens: int = 4096,
        **kw: Any,
    ) -> LlmCompletion:
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


def _completion(alias: str) -> LlmCompletion:
    return LlmCompletion(
        content="好",
        prompt_tokens=1,
        completion_tokens=1,
        usage_estimated=False,
        duration_ms=1,
        model=alias,
    )


def _fire(gw: GatewayService, i: int) -> asyncio.Task[Completion]:
    return asyncio.create_task(
        gw.complete("petro-main", [{"role": "user", "content": f"q{i}"}], caller="test.v2gate")
    )


async def _wait_entered(backend: _HoldBackend, n: int) -> None:
    """自旋等待第 n 路进闸（entered 单调计数；sleep(0) 确定性推进，无 wall-clock）。"""
    for _ in range(2000):
        if len(backend.entered) >= n:
            return
        await asyncio.sleep(0)
    raise AssertionError(f"等待 {n} 路进闸超时（entered={len(backend.entered)}）")


async def _settle() -> None:
    for _ in range(50):
        await asyncio.sleep(0)


def _reload(path: Path, input_per_mtok: float) -> None:
    """改 prices.default.input_per_mtok 后走 load_models_config 热加载（生产热加载同缝）。

    阻塞 IO 收在同步函数（ASYNC240——async 测试体不直接做 Path 写盘）。
    """
    path.write_text(_GATE_YAML.format(input_per_mtok=input_per_mtok), encoding="utf-8")
    load_models_config(path)


async def test_gateway_gate(
    gate_yaml: Path, gateway_db: ConnectionManager
) -> None:
    """动态闸并发上限生效＋预算熔断改路由不拒绝（V1 G-06/DE-14/F2 同语义）。"""
    backend = _HoldBackend()
    gw = GatewayService(gateway_db, backend)

    # （a）超限排队等而非拒：6 路/上限 2——峰值恒 2，逐放行逐补位全员成功。
    tasks = [_fire(gw, i) for i in range(6)]
    await _wait_entered(backend, 2)
    await _settle()
    assert len(backend.entered) == 2  # 超限 4 路排队未进、未报错
    for i in range(4):  # 前四次放行各恰好补进一名排队者（FIFO）
        backend.release(i)
        await _wait_entered(backend, 3 + i)
    backend.release_all()
    results = await asyncio.gather(*tasks)
    assert len(results) == 6
    assert backend.peak == 2  # 并发上限生效——峰值恒 ≤ llm_max_concurrency

    # （b）预算熔断改路由不拒绝：单价放大→单笔超 per-call 阈值 0.05 元→
    # 熔断位单向置位→后续调用仅降级组（lite）可服务（fallback=true）。
    # 栅栏后端进闸即挂——两笔走 task，逐笔放行（holds 索引＝进闸序）。
    _reload(gate_yaml, 100000.0)  # 热加载：单价放大（complete 每次现读同一缓存）
    big_task = _fire(gw, 6)
    await _wait_entered(backend, 7)
    backend.release(6)
    big = await big_task
    assert big.fallback is False  # 触顶前的最后一笔正常由主用承载

    fused_task = _fire(gw, 7)
    await _wait_entered(backend, 8)
    assert backend.entered[7] == "petro-lite"  # 熔断改路由降级组（不拒绝）
    backend.release(7)
    fused = await fused_task
    assert gw._router.fuse_latched is True  # 预算双阈值熔断位已单向置位
    assert fused.served_alias == "petro-lite"
    assert fused.fallback is True


# ---------- 验收④：midplatform 只读（INV-2） ----------


class _GuardBase(DeclarativeBase):
    pass


class _ProbeRow(_GuardBase):
    __tablename__ = "v2_readonly_probe"

    id: Mapped[str] = mapped_column(primary_key=True)


def _midplatform_spec(tmp_path: Path) -> DatabaseSpec:
    return DatabaseSpec(
        name="midplatform",
        role="midplatform",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "v2-midplatform.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=0,
        readonly=True,
    )


async def test_readonly_guard(tmp_path: Path) -> None:
    manager = ConnectionManager([_midplatform_spec(tmp_path)])
    try:
        # (a) 只读角色拒开写会话（写会话前置校验）。
        with pytest.raises(ReadOnlyViolation, match="只读"):
            async with manager.session("midplatform") as session:
                session.add(_ProbeRow(id="x"))
        # (b) 只读会话写意图：flush 被意图级守卫拦（INV-2）。
        async with manager.readonly("midplatform") as session:
            session.add(_ProbeRow(id="y"))
            with pytest.raises(ReadOnlyViolation, match="禁止 flush"):
                await session.flush()
    finally:
        await manager.dispose()


# ---------- 验收⑤：审计写口唯一（B12 代码扫描＋正向落库） ----------

_AUDIT_WRITE_SQL = re.compile(
    r"(INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+audit_log", re.IGNORECASE
)
_AUDIT_WRITE_NAMES = frozenset({"AuditLog", "AuditLogStore"})


def test_audit_single_writer(tmp_path: Path) -> None:
    # （a）代码扫描：security 包外禁止直写面——import AuditLog/AuditLogStore
    # 或 raw SQL 写 audit_log 即违反 B12（写口唯一＝SecurityService.audit）。
    offenders: list[str] = []
    for path in _v2_py_files():
        if _SECURITY_PKG in path.parents or path == _SECURITY_PKG / "__init__.py":
            continue
        source = path.read_text(encoding="utf-8")
        hits = [n for n in _imported_names(path) if n in _AUDIT_WRITE_NAMES]
        raw = bool(_AUDIT_WRITE_SQL.search(source))
        if hits or raw:
            offenders.append(
                f"{path.relative_to(_REPO_ROOT)}（imports={hits}, raw_sql={raw}）"
            )
    assert offenders == [], "audit 表直写面逃逸 security 包（B12）: " + "; ".join(offenders)

    # （b）正向面：security.audit 唯一写口落库可读（agent_v2.* 前缀入 action 槽）。
    asyncio.run(_audit_roundtrip(tmp_path))


async def _audit_roundtrip(tmp_path: Path) -> None:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "v2-audit.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    try:
        await ensure_audit_table(manager.engine())
        service = SecurityService(manager)
        await service.audit(
            AuditRow(who="系统", action="agent_v2.test.write", content="唯一写口验证")
        )
        page = await service.audit_logs()
        assert page.total == 1
        assert page.items[0].action == "agent_v2.test.write"
    finally:
        await manager.dispose()
