"""GatewayService 单测——failover 判据/重试/预算熔断/记账公式/演练状态机（sqlite 底座＋桩 LLM）。

红线：任何测试不得真实调用 MiniMax/GLM 端点——CompletionBackend 全量打桩。
合同锚：D1 演练三连（done 落两笔账）、ADR-0003 裁决 13（切换判据/per-attempt
超时/单向熔断）、W-F2-2（fallback 留痕 attempted_fallbacks）、W-F2-5（冷却）。
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest
import yaml

import app.infra.config as infra_config
from app.domains.gateway import (
    BudgetThresholds,
    Completion,
    ConfigWriteError,
    DrillConflictError,
    DrillNotFoundError,
    GatewayConfigError,
    GatewayParams,
    GatewayService,
    SpendStatsFilter,
    build_drill_nodes,
)
from app.domains.gateway.store import BudgetConfigRow, DrillRun, SpendRecord
from app.infra.clock import freeze, now
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
    assert row.caller == "test"  # caller 归因落列（D1 v0.2 端点 4/8 聚合基础）
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


# ---------- spend_stats：聚合投影（D1 端点 8——caller 归因/unattributed/sums 全量） ----------


async def _seed_stats_rows(gateway_db: Any) -> None:
    """caller 归因矩阵种子：三条已归因（不同 caller/模型/日）＋一条存量未归因。"""
    from datetime import datetime

    rows = [
        SpendRecord(
            id="call-a1", time=datetime(2026, 9, 28, 9, 0, 0), model_key="main",
            alias="petro-main", input_tokens=2000, output_tokens=1000,
            first_ms=1000, total_ms=4000, cost_yuan=0.005, fallback=False,
            note="", caller="chat.retrieval.answer",
        ),
        SpendRecord(
            id="call-a2", time=datetime(2026, 9, 28, 10, 0, 0), model_key="backup",
            alias="petro-lite", input_tokens=500, output_tokens=300,
            first_ms=1000, total_ms=2000, cost_yuan=0.003, fallback=True,
            note="", caller="wiki.gen",
        ),
        SpendRecord(
            id="call-a3", time=datetime(2026, 9, 29, 8, 0, 0), model_key="main",
            alias="petro-main", input_tokens=100, output_tokens=50,
            first_ms=800, total_ms=900, cost_yuan=0.002, fallback=False,
            note="", caller=None,  # 存量未归因流水
        ),
        SpendRecord(
            id="call-a4", time=datetime(2026, 8, 15, 8, 0, 0), model_key="main",
            alias="petro-main", input_tokens=800, output_tokens=400,
            first_ms=900, total_ms=1500, cost_yuan=0.004, fallback=False,
            note="", caller="kb.ingest.summary",  # 30d 窗外（12m 窗内）——range 判别行
        ),
    ]
    async with gateway_db.session() as session:
        for row in rows:
            session.add(row)


async def test_spend_stats_caller_dimension_with_unattributed(
    gateway_db: Any, primed_registry: Path
) -> None:
    await _seed_stats_rows(gateway_db)
    service = GatewayService(gateway_db, StubBackend({}))
    with freeze("2026-09-29T10:00:00"):
        stats = await service.spend_stats(SpendStatsFilter(group_by="caller", range="all"))
    assert [(r.bucket, r.calls, r.fallback_calls) for r in stats.items] == [
        ("chat.retrieval.answer", 1, 0),  # cost 0.005 降序居首
        ("kb.ingest.summary", 1, 0),
        ("wiki.gen", 1, 1),
        ("unattributed", 1, 0),  # 存量 caller 为空 → 归 unattributed 桶
    ]
    assert stats.total == 4
    assert (stats.sums.calls, stats.sums.fallback_calls) == (4, 1)  # sums＝窗口全量
    assert stats.sums.cost_yuan == pytest.approx(0.014)


async def test_spend_stats_model_day_and_range_window(
    gateway_db: Any, primed_registry: Path
) -> None:
    await _seed_stats_rows(gateway_db)
    service = GatewayService(gateway_db, StubBackend({}))
    with freeze("2026-09-29T10:00:00"):  # range 窗口对齐种子行日期
        model_stats = await service.spend_stats(SpendStatsFilter(group_by="model", range="all"))
        assert [(r.bucket, r.alias, r.calls) for r in model_stats.items] == [
            ("main", "petro-main", 3),  # cost 0.011 降序居首；alias 与 model_list 同源
            ("backup", "petro-lite", 1),
        ]
        day_stats = await service.spend_stats(SpendStatsFilter(group_by="day", range="all"))
        assert [r.bucket for r in day_stats.items] == [
            "2026-08-15", "2026-09-28", "2026-09-29"
        ]  # 时序升序全量
        assert day_stats.total == 3
        assert day_stats.sums.calls == 4  # sums 不随分页截断（day 全量恒 sums）
        # range 统计窗（与端点 4 不同族——无 today）：7d/30d 不含 8-15，12m 全含
        week = await service.spend_stats(SpendStatsFilter(group_by="day", range="7d"))
        assert [r.bucket for r in week.items] == ["2026-09-28", "2026-09-29"]
        assert week.sums.calls == 3
        month = await service.spend_stats(SpendStatsFilter(group_by="caller", range="30d"))
        assert [r.bucket for r in month.items] == [
            "chat.retrieval.answer", "wiki.gen", "unattributed"
        ]
        twelve = await service.spend_stats(SpendStatsFilter(group_by="caller", range="12m"))
        assert len(twelve.items) == 4 and twelve.sums.calls == 4


# ---------- config：校验/写回/热加载（表单每个数字对应文件一行）＋预算双阈值 ----------


async def test_save_gateway_config_write_back_and_hot_reload(
    gateway_db: Any, primed_registry: Path
) -> None:
    service = GatewayService(gateway_db, StubBackend({}), config_path=primed_registry)
    view = await service.save_gateway_config(
        GatewayParams(allowed_fails=3, cooldown_seconds=120, num_retries=1, request_timeout=45),
        BudgetThresholds(per_call_cost_limit_yuan=0.1, gateway_budget_yuan_per_month=500),
    )
    assert (view.params.allowed_fails, view.params.cooldown_seconds) == (3, 120)
    # 预算双阈值随 config 保存落单例行（直接生效——判据 complete 现读）
    assert (
        view.budget.per_call_cost_limit_yuan, view.budget.gateway_budget_yuan_per_month
    ) == (0.1, 500.0)
    text = _read_yaml(primed_registry)
    assert "allowed_fails: 3" in text and "cooldown_seconds: 120" in text
    assert "num_retries: 1" in text and "request_timeout: 45" in text
    assert "# 测试用模型注册表" in text  # 其余段零改动
    assert load_models_config(primed_registry).gateway.allowed_fails == 3  # 热加载生效
    assert (await service.gateway_config()).params.allowed_fails == 3  # 快照为唯一真值
    assert (await service.gateway_config()).budget.gateway_budget_yuan_per_month == 500.0


async def test_save_gateway_config_is_idempotent_no_duplicate_block(
    gateway_db: Any, primed_registry: Path
) -> None:
    """重复保存不产生重复 gateway 段（真装配冒烟发现：块头带行内注释曾致追加重放）。"""
    service = GatewayService(gateway_db, StubBackend({}), config_path=primed_registry)
    params = GatewayParams(allowed_fails=5, cooldown_seconds=60, num_retries=3, request_timeout=30)
    budget = BudgetThresholds(per_call_cost_limit_yuan=0.05, gateway_budget_yuan_per_month=800)
    for _ in range(3):
        await service.save_gateway_config(params, budget)  # 重复保存三次——幂等
    text = _read_yaml(primed_registry)
    assert text.count("gateway:") == 1  # 恰一段
    assert "allowed_fails: 5" in text
    assert text.count("allowed_fails:") == 1
    # 段头行内注释在写回后仍自释（表单里每个数字对应文件里的一行）
    assert "D1 配置面四参数" in text


async def test_save_gateway_config_rejects_out_of_range(
    gateway_db: Any, primed_registry: Path
) -> None:
    service = GatewayService(gateway_db, StubBackend({}), config_path=primed_registry)
    before = _read_yaml(primed_registry)
    with pytest.raises(GatewayConfigError):
        await service.save_gateway_config(
            GatewayParams(allowed_fails=99, cooldown_seconds=60, num_retries=3, request_timeout=30),
            BudgetThresholds(per_call_cost_limit_yuan=0.05, gateway_budget_yuan_per_month=800),
        )
    assert _read_yaml(primed_registry) == before  # 拒绝即无副作用


async def test_save_gateway_config_rejects_negative_budget(
    gateway_db: Any, primed_registry: Path
) -> None:
    """预算双阈值 >=0（D1 v0.2）：负数 400 带字段与区间；yaml 与单例行均无副作用。"""
    service = GatewayService(gateway_db, StubBackend({}), config_path=primed_registry)
    before = _read_yaml(primed_registry)
    with pytest.raises(GatewayConfigError) as exc_info:
        await service.save_gateway_config(
            GatewayParams(allowed_fails=2, cooldown_seconds=60, num_retries=3, request_timeout=30),
            BudgetThresholds(per_call_cost_limit_yuan=-0.01, gateway_budget_yuan_per_month=800),
        )
    assert exc_info.value.violations == [("params.per_call_cost_limit_yuan", ">=0")]
    assert _read_yaml(primed_registry) == before
    # 阈值行未被污染（首次读取才种子——此刻查表应为空）
    from sqlalchemy import select

    async with gateway_db.readonly() as session:
        rows = list((await session.execute(select(BudgetConfigRow))).scalars().all())
    assert rows == []


async def test_save_gateway_config_maps_reload_failure_to_config_write_error(
    gateway_db: Any, primed_registry: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """热加载失败（yaml 坏/校验不过）与写失败同收口 ConfigWriteError（不只 OSError）。"""

    def broken_load(path: object = None) -> object:
        raise yaml.YAMLError("半截 yaml")

    monkeypatch.setattr(infra_config, "load_models_config", broken_load)
    service = GatewayService(gateway_db, StubBackend({}), config_path=primed_registry)
    with pytest.raises(ConfigWriteError, match="半截 yaml"):
        await service.save_gateway_config(
            GatewayParams(allowed_fails=3, cooldown_seconds=60, num_retries=3, request_timeout=30),
            BudgetThresholds(per_call_cost_limit_yuan=0.05, gateway_budget_yuan_per_month=800),
        )


# ---------- 记账计价真源：prices.default 缺失＝部署错误，fail-fast 拒绝记账 ----------


def _read_yaml(path: Path) -> str:
    """同步小助手（async 测试体不做阻塞 IO——ruff ASYNC240）。"""
    return path.read_text(encoding="utf-8")


def _write_yaml(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _drop_prices_block(yaml_text: str) -> str:
    lines = yaml_text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln == "prices:")
    end = start + 1
    while end < len(lines) and (lines[end].startswith((" ", "\t")) or not lines[end].strip()):
        end += 1
    return "\n".join(lines[:start] + lines[end:]) + "\n"


async def test_complete_fails_fast_when_prices_default_missing(
    gateway_db: Any, models_yaml: Path
) -> None:
    """Owner 裁决单价真源缺失：拒绝记账而非静默落硬编码 1.0/3.0（真源禁第二份）。"""
    _write_yaml(models_yaml, _drop_prices_block(_read_yaml(models_yaml)))
    load_models_config(models_yaml)
    service = GatewayService(
        gateway_db, StubBackend({"petro-main": MAIN_COMPLETION}), drill_step_seconds=0
    )
    with pytest.raises(RuntimeError, match=r"prices\.default"):
        await service.complete("petro-main", [{"role": "user", "content": "q"}], caller="test")
    assert await _all_spend(gateway_db) == []  # 未落账（无硬编码兜底价流水）


# ---------- 域级参数不转发上游（note＝记账备注槽，litellm 不识） ----------


async def test_complete_strips_domain_note_before_forwarding(
    gateway_db: Any, primed_registry: Path
) -> None:
    forwarded: dict[str, Any] = {}

    class Capture(StubBackend):
        async def complete(
            self,
            alias: str,
            messages: Any,
            *,
            timeout_seconds: float,
            max_tokens: int = 4096,
            **params: Any,
        ) -> LlmCompletion:
            forwarded.update(params)
            return await super().complete(
                alias, messages, timeout_seconds=timeout_seconds, **params
            )

    service = GatewayService(
        gateway_db, Capture({"petro-main": MAIN_COMPLETION, "petro-lite": LITE_COMPLETION})
    )
    out = await service.complete(
        "petro-main", [{"role": "user", "content": "q"}],
        caller="quality.report", note="质检周报草稿", temperature=0.1,
    )
    assert "note" not in forwarded  # 域级键剥除——上游只见业务参数
    assert forwarded.get("temperature") == 0.1  # 透传参数照转
    row = await service._spend.get(out.call_id)
    assert row is not None and row.note == "质检周报草稿"  # 备注槽照常记账


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


# ---------- 启动收口与受理快照（P0-05 审查收口） ----------


async def test_close_stale_drills_reaps_zombie_running(
    gateway_db: Any, primed_registry: Path
) -> None:
    """进程崩溃遗留 running 行：启动收口 done「进程中断收口」——has_running 不再恒真。"""
    service = GatewayService(gateway_db, StubBackend({}), drill_step_seconds=0)
    await service._drills.create(
        DrillRun(id="drill-zombie01", status="running", nodes=[], started_at=now())
    )
    assert await service._drills.has_running() is True  # 僵尸行 → start_drill 会永久 409
    closed = await service.close_stale_drills()
    assert closed == 1
    run = await service._drills.get("drill-zombie01")
    assert run is not None and run.status == "done"
    assert run.summary is not None and "进程中断收口" in run.summary
    assert run.finished_at is not None
    assert await service._drills.has_running() is False  # 重启后 start_drill 可受理
    assert await service.close_stale_drills() == 0  # 幂等：无 running 行即 0
    history = await service.drill_history()
    assert len(history) == 1 and "进程中断收口" in history[0].summary  # 收口进历史（人话 summary）


async def test_drill_body_uses_acceptance_snapshot_not_runtime_config(
    gateway_db: Any, primed_registry: Path
) -> None:
    """受理后热加载改 allowed_fails：任务体按受理快照跑——节点列与索引同源，不 IndexError。"""
    service = GatewayService(
        gateway_db,
        StubBackend({"petro-main": MAIN_COMPLETION, "petro-lite": LITE_COMPLETION}),
        drill_step_seconds=0,
    )
    snapshot_params = load_models_config(primed_registry).gateway  # 受理时快照（allowed_fails=2）
    run_id = "drill-race001"
    await service._drills.create(
        DrillRun(
            id=run_id,
            status="running",
            nodes=[n.as_dict() for n in build_drill_nodes(snapshot_params.allowed_fails)],
            started_at=now(),
        )
    )
    # 受理后运行时配置被热加载改掉（2→4，模拟并发保存）——旧实现按运行时值
    # 索引 nodes[4] 即 IndexError；快照传参后任务体照受理时刻继续
    _write_yaml(
        primed_registry, _read_yaml(primed_registry).replace("allowed_fails: 2", "allowed_fails: 4")
    )
    load_models_config(primed_registry)
    await service._run_drill(run_id, snapshot_params, "petro-main")
    progress = await service.drill(run_id)
    assert progress.status == "done"
    assert progress.result is not None  # 演练正常收口（未被竞态打断）
    assert [n["key"] for n in progress.nodes] == ["fail1", "fail2", "fallback", "ledger"]
    assert progress.result["fallback"]["consecutive_fails"] == 2  # 受理快照值而非运行时 4


# ---------- 辅助 ----------


async def _all_spend(db: Any) -> list[SpendRecord]:
    from sqlalchemy import select

    async with db.readonly() as session:
        return list((await session.execute(select(SpendRecord))).scalars().all())
