"""GatewayService 单测——failover 判据/重试/预算熔断/记账公式/演练状态机（sqlite 底座＋桩 LLM）。

红线：任何测试不得真实调用 MiniMax/GLM 端点——CompletionBackend 全量打桩。
合同锚：D1 演练三连（done 落两笔账）、ADR-0003 裁决 13（切换判据/per-attempt
超时/单向熔断）、W-F2-2（fallback 留痕 attempted_fallbacks）、W-F2-5（冷却）。
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.domains.gateway import (
    Completion,
    DrillConflictError,
    DrillNotFoundError,
    GatewayConfigError,
    GatewayParams,
    GatewayService,
)
from app.domains.gateway.store import BudgetConfigRow, SpendRecord
from app.infra.config import load_models_config
from app.infra.llm_client import LlmCompletion, UpstreamRejected, UpstreamUnavailable

# ---------- 桩 LLM（B6：gateway 只认 CompletionBackend seam；永不触网） ----------

MAIN_COMPLETION = LlmCompletion(
    content="主模型应答",
    prompt_tokens=2140,
    completion_tokens=1380,
    usage_estimated=False,
    duration_ms=4000,
    model="anthropic/MiniMax-M3",
)
LITE_COMPLETION = LlmCompletion(
    content="线路正常",
    prompt_tokens=100,
    completion_tokens=50,
    usage_estimated=False,
    duration_ms=2400,
    model="anthropic/glm-5.3-flash",
)


class StubBackend:
    """按别名脚本应答；可注延迟（演练 409 用例）。"""

    def __init__(self, script: dict[str, Any], delay: float = 0.0) -> None:
        self.script = script
        self.delay = delay
        self.calls: list[tuple[str, float]] = []  # (alias, timeout_seconds)

    async def complete(
        self,
        alias: str,
        messages: list[dict[str, str]],
        *,
        timeout_seconds: float,
        max_tokens: int = 4096,
        **params: Any,
    ) -> LlmCompletion:
        self.calls.append((alias, timeout_seconds))
        if self.delay:
            await asyncio.sleep(self.delay)
        out = self.script[alias]
        if isinstance(out, Exception):
            raise out
        return out


@pytest.fixture
def service(
    gateway_db: Any, primed_registry: Path
) -> GatewayService:
    return GatewayService(
        gateway_db, StubBackend({"petro-main": MAIN_COMPLETION, "petro-lite": LITE_COMPLETION})
    )


# ---------- complete：记账公式与账本唯一（Owner 裁决公式） ----------


async def test_complete_records_ledger_with_owner_formula(
    gateway_db: Any, service: GatewayService
) -> None:
    out = await service.complete("petro-main", [{"role": "user", "content": "q"}], caller="test")
    assert isinstance(out, Completion)
    assert out.fallback is False
    assert out.served_alias == "petro-main"
    assert out.cost_yuan == pytest.approx(2140 / 1e6 * 1.0 + 1380 / 1e6 * 3.0)
    row = await service._spend.get(out.call_id)  # 账本唯一——一行对一调用
    assert row is not None
    assert row.model_key == "main"
    assert row.input_tokens == 2140 and row.output_tokens == 1380
    assert row.cost_yuan == pytest.approx(0.00628)
    assert row.note == "test"  # 备注缺省＝调用方标识（keyword 可检索）
    # 切换留痕注记列（served_model/attempted_fallbacks——99 §2.13）在存储行上
    records = await _all_spend(gateway_db)
    assert len(records) == 1
    assert records[0].served_model == "anthropic/MiniMax-M3"
    assert records[0].attempted_fallbacks is None  # 主路直达，无切换留痕


# ---------- failover 判据：网络错/超时切备；4xx/429 不切 ----------


async def test_network_failure_switches_to_backup(
    gateway_db: Any, primed_registry: Path
) -> None:
    backend = StubBackend(
        {"petro-main": UpstreamUnavailable("petro-main", "超时"), "petro-lite": LITE_COMPLETION}
    )
    service = GatewayService(gateway_db, backend, drill_step_seconds=0)
    out = await service.complete("petro-main", [{"role": "user", "content": "q"}], caller="test")
    assert out.served_alias == "petro-lite" and out.fallback is True
    row = await service._spend.get(out.call_id)
    assert row is not None
    assert row.fallback is True
    assert row.model_key == "backup"
    records = await _all_spend(gateway_db)
    # W-F2-2 切换留痕：attempted_fallbacks 记失败部署序（存储列）
    assert records[0].attempted_fallbacks == ["anthropic/MiniMax-M3"]
    # 同别名先重试（1＋num_retries=3 次全败）才切备——重试是网关层语义
    assert [alias for alias, _ in backend.calls] == ["petro-main"] * 4 + ["petro-lite"]


async def test_4xx_429_never_switches_and_raises(gateway_db: Any, primed_registry: Path) -> None:
    backend = StubBackend(
        {
            "petro-main": UpstreamRejected("petro-main", "上游拒绝 429"),
            "petro-lite": LITE_COMPLETION,
        }
    )
    service = GatewayService(gateway_db, backend)
    with pytest.raises(UpstreamRejected):
        await service.complete("petro-main", [{"role": "user", "content": "q"}], caller="test")
    assert [alias for alias, _ in backend.calls] == ["petro-main"]  # 未切备（椒图判据）
    # 4xx 失败不落账本（记账只对应答成功的调用——成本公式无输入）
    assert await _all_spend(gateway_db) == []


async def test_retry_within_alias_before_switching(gateway_db: Any, primed_registry: Path) -> None:
    """num_retries 只在网关层：同别名重试耗尽才计一次失败再切备。"""

    class FlakyMain(StubBackend):
        def __init__(self) -> None:
            super().__init__({"petro-main": LITE_COMPLETION, "petro-lite": LITE_COMPLETION})
            self.main_attempts = 0

        async def complete(self, alias: str, messages: Any, **kw: Any) -> LlmCompletion:
            if alias == "petro-main":
                self.main_attempts += 1
                if self.main_attempts <= 3:  # 默认 num_retries=3 → 第 4 次成功
                    raise UpstreamUnavailable("petro-main", "抖动")
            return await super().complete(alias, messages, **kw)

    backend = FlakyMain()
    service = GatewayService(gateway_db, backend)
    out = await service.complete("petro-main", [{"role": "user", "content": "q"}], caller="test")
    assert backend.main_attempts == 4  # 1＋num_retries=3
    assert out.served_alias == "petro-main" and out.fallback is False  # 重试救回＝无切换


# ---------- 预算熔断：双阈值触顶→单向置位→改路由降级组 ----------


async def test_budget_fuse_latches_and_degrades_route(
    gateway_db: Any, primed_registry: Path
) -> None:
    # 合同默认阈值 0.05 元/单次——2140/1380 的 0.00628 元不触顶
    service = GatewayService(
        gateway_db, StubBackend({"petro-main": MAIN_COMPLETION, "petro-lite": LITE_COMPLETION})
    )
    await service.complete("petro-main", [{"role": "user", "content": "q"}], caller="test")
    assert service._router.fuse_latched is False

    # 首笔已按合同默认阈值落 singleton 行——改小单次阈值（等价 D5 端点 9 保存）→ 下一笔触顶
    async with gateway_db.session() as session:
        row = await session.get(BudgetConfigRow, "singleton")
        assert row is not None  # 首次 complete 已自动种子（BudgetStore.limits 缺省行）
        row.per_call_cost_limit_yuan = 0.001
    out2 = await service.complete("petro-main", [{"role": "user", "content": "q2"}], caller="test")
    assert service._router.fuse_latched is True  # 单向置位（不自动恢复）
    assert out2.fallback is False  # 触顶前在途调用照跑完（本笔仍走主路）

    out3 = await service.complete("petro-main", [{"role": "user", "content": "q3"}], caller="test")
    assert out3.served_alias == "petro-lite" and out3.fallback is True  # 后续调用改降级组


async def test_monthly_budget_fuse(gateway_db: Any, primed_registry: Path) -> None:
    service = GatewayService(
        gateway_db, StubBackend({"petro-main": MAIN_COMPLETION, "petro-lite": LITE_COMPLETION})
    )
    # 先种 singleton（首笔前落阈值——避免与 limits() 缺省种子撞唯一键）
    async with gateway_db.session() as session:
        session.add(
            BudgetConfigRow(
                id="singleton", per_call_cost_limit_yuan=100.0, gateway_budget_yuan_per_month=0.005
            )
        )
    await service.complete("petro-main", [{"role": "user", "content": "q"}], caller="test")
    assert service._router.fuse_latched is True  # 首笔累计 0.00628 > 0.005 触顶
    out = await service.complete("petro-main", [{"role": "user", "content": "q2"}], caller="test")
    assert out.served_alias == "petro-lite"


# ---------- config：校验/写回/热加载（表单每个数字对应文件一行） ----------


def test_save_gateway_config_write_back_and_hot_reload(
    gateway_db: Any, primed_registry: Path
) -> None:
    service = GatewayService(gateway_db, StubBackend({}), config_path=primed_registry)
    view = service.save_gateway_config(
        GatewayParams(allowed_fails=3, cooldown_seconds=120, num_retries=1, request_timeout=45)
    )
    assert (view.params.allowed_fails, view.params.cooldown_seconds) == (3, 120)
    text = primed_registry.read_text(encoding="utf-8")
    assert "allowed_fails: 3" in text and "cooldown_seconds: 120" in text
    assert "num_retries: 1" in text and "request_timeout: 45" in text
    assert "# 测试用模型注册表" in text  # 其余段零改动
    assert load_models_config(primed_registry).gateway.allowed_fails == 3  # 热加载生效
    assert service.gateway_config().params.allowed_fails == 3  # 快照为唯一真值


def test_save_gateway_config_is_idempotent_no_duplicate_block(
    gateway_db: Any, primed_registry: Path
) -> None:
    """重复保存不产生重复 gateway 段（真装配冒烟发现：块头带行内注释曾致追加重放）。"""
    service = GatewayService(gateway_db, StubBackend({}), config_path=primed_registry)
    params = GatewayParams(allowed_fails=5, cooldown_seconds=60, num_retries=3, request_timeout=30)
    for _ in range(3):
        service.save_gateway_config(params)  # 重复保存三次——幂等
    text = primed_registry.read_text(encoding="utf-8")
    assert text.count("gateway:") == 1  # 恰一段
    assert "allowed_fails: 5" in text
    assert text.count("allowed_fails:") == 1
    # 段头行内注释在写回后仍自释（表单里每个数字对应文件里的一行）
    assert "D1 配置面四参数" in text


def test_save_gateway_config_rejects_out_of_range(gateway_db: Any, primed_registry: Path) -> None:
    service = GatewayService(gateway_db, StubBackend({}), config_path=primed_registry)
    before = primed_registry.read_text(encoding="utf-8")
    with pytest.raises(GatewayConfigError):
        service.save_gateway_config(
            GatewayParams(allowed_fails=99, cooldown_seconds=60, num_retries=3, request_timeout=30)
        )
    assert primed_registry.read_text(encoding="utf-8") == before  # 拒绝即无副作用


# ---------- 演练状态机：202 受理/重入 409/轮询/两笔账/历史 ----------


async def test_drill_happy_path_leaves_two_ledger_traces(
    gateway_db: Any, primed_registry: Path
) -> None:
    service = GatewayService(
        gateway_db,
        StubBackend({"petro-main": MAIN_COMPLETION, "petro-lite": LITE_COMPLETION}),
        drill_step_seconds=0,
    )
    handle = await service.start_drill()
    for _ in range(200):  # 轮询直至终态（00 §5.2：轮询节奏服务端定）
        progress = await service.drill(handle.drill_id)
        if progress.status == "done":
            break
        await asyncio.sleep(0.01)
    assert progress.status == "done"
    keys = [n["key"] for n in progress.nodes]
    assert keys == ["fail1", "fail2", "fallback", "ledger"]  # 阈值 2→两次注入
    assert all(n["state"] in ("finish", "error") for n in progress.nodes)
    result = progress.result
    assert result is not None
    assert result["fallback"]["event"] == "fallback_triggered"
    assert result["fallback"]["request_alias"] == "petro-main"
    assert result["fallback"]["failed_deploy"] == "anthropic/MiniMax-M3"
    assert result["fallback"]["failover_target"] == "anthropic/glm-5.3-flash"
    assert result["fallback"]["consecutive_fails"] == 2  # 当前配置值（合同原文）
    assert result["fallback"]["cooldown_sec"] == 60
    assert result["ledger_row"]["fallback"] is True
    assert result["ledger_row"]["model_key"] == "backup"

    # done 落两笔账：备用记账行（fallback=true）＋演练历史行
    logs = await _all_spend(gateway_db)
    assert len(logs) == 1 and logs[0].fallback is True  # 演练即真实流量——恰一条备用流水
    history = await service.drill_history()
    assert len(history) == 1
    assert "阈值 2" in history[0].summary and "冷却 60s" in history[0].summary
    # 主用进入冷却 → 网关态 degraded（页头徽标：备用承载中）
    assert service.models().gateway_status == "degraded"


async def test_drill_reentry_conflict_then_history(gateway_db: Any, primed_registry: Path) -> None:
    backend = StubBackend(
        {"petro-main": MAIN_COMPLETION, "petro-lite": LITE_COMPLETION}, delay=0.15
    )
    service = GatewayService(gateway_db, backend, drill_step_seconds=0)
    first = await service.start_drill()
    with pytest.raises(DrillConflictError):  # 重入 409（进行中）
        await service.start_drill()
    for _ in range(400):
        if (await service.drill(first.drill_id)).status == "done":
            break
        await asyncio.sleep(0.01)
    second = await service.start_drill()  # 终态后可再次受理
    assert second.drill_id != first.drill_id
    for _ in range(400):
        if (await service.drill(second.drill_id)).status == "done":
            break
        await asyncio.sleep(0.01)
    history = await service.drill_history()
    assert len(history) == 2


async def test_drill_unknown_id_not_found(service: GatewayService) -> None:
    with pytest.raises(DrillNotFoundError):
        await service.drill("drill-00000000")


async def test_drill_backup_also_down_closes_as_done_with_reason(
    gateway_db: Any, primed_registry: Path
) -> None:
    """备用也应答失败：双态合同（running|done）不留僵尸 running——失败收口带人话原因。"""
    backend = StubBackend({
        "petro-main": MAIN_COMPLETION,
        "petro-lite": UpstreamUnavailable("petro-lite", "上游 503"),
    })
    service = GatewayService(gateway_db, backend, drill_step_seconds=0)
    handle = await service.start_drill()
    for _ in range(400):
        progress = await service.drill(handle.drill_id)
        if progress.status == "done":
            break
        await asyncio.sleep(0.01)
    assert progress.status == "done"
    assert progress.result is None  # 失败无切换结果
    assert "演练失败" in (await service.drill_history())[0].summary
    assert await _all_spend(gateway_db) == []  # 无成功应答即无记账


# ---------- 辅助 ----------


async def _all_spend(db: Any) -> list[SpendRecord]:
    from sqlalchemy import select

    async with db.readonly() as session:
        return list((await session.execute(select(SpendRecord))).scalars().all())
