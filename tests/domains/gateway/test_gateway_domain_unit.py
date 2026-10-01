"""gateway 领域单测——记账公式/参数边界/路由熔断状态机/演练节点（纯语义，无 IO）。

合同锚：D1 端点 2/3 参数边界、端点 4 数据形状与公式（Owner 裁决
input/1e6*1+output/1e6*3）、ADR-0003 裁决 13（熔断改路由不拒绝/单向置位/
降级组 petro-lite）、D5 §8 双阈值合同默认值（0.05/800）、00 §5.3 节点四态。
"""

from datetime import datetime, timedelta

import pytest

from app.domains.gateway import (
    PARAM_LIMITS,
    STATS_GROUP_BYS,
    STATS_RANGES,
    UNATTRIBUTED,
    BudgetThresholds,
    GatewayConfigError,
    GatewayParams,
    PriceSpec,
    RouterState,
    SpendFilter,
    SpendStatsFilter,
    build_drill_nodes,
    cost_yuan,
    estimate_tokens,
    project_models,
)
from app.infra.clock import freeze, now
from app.infra.config import load_models_config

_AT = datetime(2026, 9, 29, 10, 0, 0)

# ---------- 记账金额公式（Owner 2026-09-29 裁决——票面挂账清零项） ----------


def test_cost_formula_owner_ruling() -> None:
    prices = PriceSpec(input_per_mtok=1.0, output_per_mtok=3.0)
    # D1 合同示例量级：input 2140 / output 1380 → 0.00214 + 0.00414 = 0.00628 元
    assert cost_yuan(2140, 1380, prices) == pytest.approx(0.00628)
    assert cost_yuan(0, 0, prices) == 0.0
    assert cost_yuan(1_000_000, 0, prices) == pytest.approx(1.0)
    assert cost_yuan(0, 1_000_000, prices) == pytest.approx(3.0)


def test_estimate_tokens_chars_over_four() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("x" * 40) == 10  # 椒图蓝本 chars/4


# ---------- 调用参数边界（D1 端点 3：越界 400——错误体带字段与允许区间） ----------


def test_gateway_params_validated_defaults() -> None:
    params = GatewayParams.validated({})
    assert (
        params.allowed_fails, params.cooldown_seconds,
        params.num_retries, params.request_timeout,
    ) == (2, 60, 3, 30)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("allowed_fails", 0),  # 下界外（1–10）
        ("allowed_fails", 11),  # 上界外
        ("cooldown_seconds", 9),  # 10–600
        ("cooldown_seconds", 601),
        ("num_retries", -1),  # 0–5
        ("num_retries", 6),
        ("request_timeout", 4),  # 5–120
        ("request_timeout", 121),
    ],
)
def test_gateway_params_out_of_range_carries_field_and_range(field: str, value: int) -> None:
    with pytest.raises(GatewayConfigError) as exc_info:
        GatewayParams.validated({field: value})
    fields = [f for f, _ in exc_info.value.violations]
    ranges = [r for _, r in exc_info.value.violations]
    assert fields == [f"params.{field}"]
    low, high = PARAM_LIMITS[field]  # type: ignore[index]
    assert ranges == [f"{low}–{high}"]


def test_gateway_params_boundary_values_pass() -> None:
    params = GatewayParams.validated(
        {"allowed_fails": 1, "cooldown_seconds": 10, "num_retries": 0, "request_timeout": 5}
    )
    assert params.allowed_fails == 1 and params.cooldown_seconds == 10
    params = GatewayParams.validated(
        {"allowed_fails": 10, "cooldown_seconds": 600, "num_retries": 5, "request_timeout": 120}
    )
    assert params.request_timeout == 120


# ---------- 路由状态机（allowed_fails/cooldown——W-F2-5 语义） ----------


def test_router_cooldown_trips_at_allowed_fails() -> None:
    router = RouterState()
    not_tripped = router.record_failure(
        "petro-main", allowed_fails=2, cooldown_seconds=60, at=_AT
    )
    assert not_tripped is False
    assert not router.in_cooldown("petro-main", _AT)
    tripped = router.record_failure("petro-main", allowed_fails=2, cooldown_seconds=60, at=_AT)
    assert tripped is True  # 第 2 次连续失败触发冷却
    assert router.in_cooldown("petro-main", _AT)
    assert router.route_candidates(
        ["petro-main", "petro-lite"], groups={}, requested="petro-main", at=_AT
    ) == ["petro-lite"]  # 冷却期内主用不被选中（W-F2-5）


def test_router_cooldown_expires_and_success_resets() -> None:
    router = RouterState()
    for _ in range(2):
        router.record_failure("petro-main", 2, 60, _AT)
    assert router.in_cooldown("petro-main", _AT)
    after = _AT + timedelta(seconds=61)  # 冷却过期即恢复可选
    assert not router.in_cooldown("petro-main", after)
    router.record_success("petro-main")
    # 成功清零计数：再一次失败不应触发冷却（阈值 2）
    assert router.record_failure("petro-main", 2, 60, after) is False


def test_router_status_three_states() -> None:
    """运行态三态判定单源（D1 页头徽标——service.models 只消费不重推导）。"""
    router = RouterState()
    order = ["petro-main", "petro-lite"]
    assert router.status("petro-main", order, _AT) == "running"
    router.record_failure("petro-main", allowed_fails=1, cooldown_seconds=60, at=_AT)
    assert router.status("petro-main", order, _AT) == "degraded"  # 主用冷却·备用承载
    router.record_failure("petro-lite", allowed_fails=1, cooldown_seconds=60, at=_AT)
    assert router.status("petro-main", order, _AT) == "down"  # 全线路冷却
    after = _AT + timedelta(seconds=61)
    assert router.status("petro-main", order, after) == "running"  # 冷却过期恢复
    assert router.status("petro-main", [], _AT) == "running"  # 空序不判 down


def test_router_fuse_latch_routes_degrade_group_only() -> None:
    """熔断三语义：改路由不拒绝（降级组 petro-lite）、单向置位不自动恢复。"""
    router = RouterState()
    groups = {"petro-main": "standard", "petro-lite": "lite"}
    assert router.route_candidates(
        ["petro-main", "petro-lite"], groups=groups, requested="petro-main", at=_AT
    ) == ["petro-main", "petro-lite"]
    router.fuse_latched = True
    candidates = router.route_candidates(
        ["petro-main", "petro-lite"], groups=groups, requested="petro-main", at=_AT
    )
    assert candidates == ["petro-lite"]  # 触顶后整体改降级组（改路由不拒绝）
    # 单向置位语义由 service._maybe_latch_fuse 承担：只置 True、无解除口——
    # RouterState 本身不提供取消熔断的公开方法（进程生命周期内不自动恢复）。


def test_router_fuse_latch_with_no_degrade_alias_yields_empty() -> None:
    """降级组无可用别名时宁空勿滥（降级语义单向——不回捞非降级组）。"""
    router = RouterState()
    router.fuse_latched = True
    assert (
        router.route_candidates(
            ["petro-main"], groups={"petro-main": "standard"}, requested="petro-main", at=_AT
        )
        == []
    )


# ---------- 模型清单投影（D1 端点 1：key/role 派生自 routing） ----------


def test_project_models_derives_main_backup(primed_registry: object) -> None:
    config = load_models_config(primed_registry)  # type: ignore[arg-type]
    view = project_models(
        config.models, config.routing.default, config.routing.fallback_order, "running"
    )
    assert [(m.key, m.role, m.alias) for m in view.models] == [
        ("main", "main", "petro-main"),
        ("backup", "backup", "petro-lite"),
    ]
    assert view.gateway_status == "running"
    assert view.models[0].name == "MiniMax-M3"  # 注册表展示名（缺省回退 model 名）


# ---------- spend-logs 筛选语义 ----------


def test_spend_filter_since_ranges() -> None:
    with freeze("2026-09-29T10:00:00"):
        assert SpendFilter(range="all").since(now()) is None
        today = SpendFilter(range="today").since(now())
        assert today is not None and (today.hour, today.minute) == (0, 0)
        week = SpendFilter(range="7d").since(now())
        assert week is not None and week.day == 22  # 7×24h 前


def test_spend_filter_enum_out_of_range() -> None:
    with pytest.raises(GatewayConfigError):
        SpendFilter(model="everything").validated()
    with pytest.raises(GatewayConfigError):
        SpendFilter(range="30d").validated()


# ---------- 花费聚合筛选（D1 端点 8——D5 撤页归并；与端点 4 range 不同族） ----------


def test_spend_stats_filter_since_ranges() -> None:
    with freeze("2026-09-29T10:00:00"):
        assert SpendStatsFilter(range="all").since(now()) is None
        week = SpendStatsFilter(range="7d").since(now())
        assert week is not None and week.day == 22
        month = SpendStatsFilter(range="30d").since(now())
        assert month is not None and month.day == 30  # 30×24h 前
        year = SpendStatsFilter(range="12m").since(now())
        assert year is not None and (year.year, year.day) == (2025, 29)  # 365d 前


def test_spend_stats_filter_enum_out_of_range_carries_legal_enums() -> None:
    with pytest.raises(GatewayConfigError) as exc_info:
        SpendStatsFilter(group_by="well").validated()
    assert exc_info.value.violations == [("group_by", "|".join(STATS_GROUP_BYS))]
    with pytest.raises(GatewayConfigError) as exc_info:
        SpendStatsFilter(range="today").validated()  # 端点 4 族值不通用——统计窗最小 7 天
    assert exc_info.value.violations == [("range", "|".join(STATS_RANGES))]
    # 合法枚举边界全过
    for group_by in STATS_GROUP_BYS:
        assert SpendStatsFilter(group_by=group_by).validated().group_by == group_by


def test_unattributed_bucket_constant() -> None:
    # 存量未归因流水（caller 为空）聚合桶名——D1 v0.2 合同值
    assert UNATTRIBUTED == "unattributed"


# ---------- 预算双阈值校验（D1 v0.2 端点 2/3 扩段：>=0；负数/非数值 400） ----------


def test_budget_thresholds_validated_pass_and_normalize() -> None:
    budget = BudgetThresholds.validated(
        {"per_call_cost_limit_yuan": 0.05, "gateway_budget_yuan_per_month": 800}
    )
    assert (
        budget.per_call_cost_limit_yuan, budget.gateway_budget_yuan_per_month
    ) == (0.05, 800.0)
    zero = BudgetThresholds.validated(
        {"per_call_cost_limit_yuan": 0, "gateway_budget_yuan_per_month": 0}
    )
    assert zero.per_call_cost_limit_yuan == 0.0


@pytest.mark.parametrize(
    ("per_call", "monthly"),
    [
        (-0.01, 800),  # 负数
        (0.05, -1),
        ("0.05", 800),  # 非数值
        (0.05, None),
        (True, 800),  # 布尔冒充数值
    ],
)
def test_budget_thresholds_rejects_with_field_and_range(per_call: object, monthly: object) -> None:
    with pytest.raises(GatewayConfigError) as exc_info:
        BudgetThresholds.validated(
            {"per_call_cost_limit_yuan": per_call, "gateway_budget_yuan_per_month": monthly}
        )
    fields = [f for f, _ in exc_info.value.violations]
    assert all(f.startswith("params.") for f in fields)
    assert all(r == ">=0" for _, r in exc_info.value.violations)


# ---------- 演练节点（00 §5.3 四态；N 次注入＋切换＋记账） ----------


def test_build_drill_nodes_follows_allowed_fails() -> None:
    nodes = build_drill_nodes(3)
    assert [n.key for n in nodes] == ["fail1", "fail2", "fail3", "fallback", "ledger"]
    assert all(n.state == "wait" for n in nodes)
    assert nodes[0].label == "第 1 次调用失败（注入）"
    assert nodes[-1].label.startswith("记账落账")
