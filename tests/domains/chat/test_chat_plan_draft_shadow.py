"""L-01 问数入口精解析影子观测件测试——Draft schema/validator/比对算子/触发谓词＋影子接线。

票面（tickets/phase3/L-01-问数入口精解析-影子观测件.md）验收对应：
- 六组红例逐组（①携 actor／②携伪 measure_column／③携非空 external_tables／
  ④metric_slot 不在 MEASURE_COLUMNS／⑤window 非半开／⑥limit_requested 非 [1,200]）；
- validator 与 build_query_plan 零第二真源（同输入同 column/unit——MEASURE_COLUMNS
  单源断言）；
- 比对算子三态（一致／分歧列明字段／不可比）＋window.label/is_default 记日志不判分歧；
- 触发谓词：「哪几口井采得最狠」→True（词面缺件）、「上月产油最多的前 10 口井」→False
  （快路可解）；
- 影子接线：ChainDeps 可空缝（plan_drafter）＋影子日志一行结构化（run_id/触发原因/
  draft 三态/耗时_ms）——注入缝未装配（生产现状）＝链行为零变化。

影子期铁律：llm_plan 产物只落日志不进任何生效路（真实 gateway 接线归 L-02——本票
测试以替身喂 Draft）。时间基准＝infra.clock 真值（B14）——窗口断言动态推导不写死。
"""

import logging
from datetime import date, timedelta
from typing import Any

import pytest

from app.domains.chat import chains as chains_mod
from app.domains.chat import domain as d
from app.infra.clock import now
from app.infra.db import ConnectionManager
from tests.domains.chat.conftest import AQIANG, Seams, collect, make_service

SHADOW_LOGGER = "domains.chat"


def _today() -> date:
    return now().date()


def _base_payload() -> dict[str, Any]:
    """合法 Draft 载荷底版（五源槽位齐——各红例在其上叠禁区键/坏值）。"""
    return {
        "metric_slot": "日产油量",
        "window": {"start": "2026-09-01", "end": "2026-10-01"},
        "limit_requested": None,
        "ranking": True,
        "direction": "desc",
    }


# ---------- 交付物①：QueryPlanDraft schema（五源槽位白名单＋六禁区键出现即拒） ----------


class TestQueryPlanDraftSchema:
    def test_payload_happy_path_builds_frozen_draft(self) -> None:
        draft = d.QueryPlanDraft.from_payload(_base_payload())
        assert draft.metric_slot == "日产油量"
        assert draft.window == d.TimeWindow(
            date(2026, 9, 1), date(2026, 10, 1), "", False
        )
        assert draft.limit_requested is None
        assert draft.ranking is True
        assert draft.direction == "desc"
        with pytest.raises(Exception, match=r"cannot assign|frozen"):
            draft.metric_slot = "日产液量"  # type: ignore[misc]

    def test_defaults_direction_desc_and_ranking_false(self) -> None:
        draft = d.QueryPlanDraft.from_payload(
            {"metric_slot": "油压", "window": {"start": "2026-09-01", "end": "2026-09-02"}}
        )
        assert draft.ranking is False
        assert draft.direction == d.DIRECTION_DESC
        assert draft.limit_requested is None

    def test_red1_actor_key_rejected_with_reason(self) -> None:
        """红例①：携 actor 即拒——身份字段恒服务端注入，逐键报禁因。"""
        with pytest.raises(ValueError) as errinfo:
            d.QueryPlanDraft.from_payload({**_base_payload(), "actor": AQIANG})
        message = str(errinfo.value)
        assert "actor" in message
        assert "禁区" in message
        assert "服务端注入" in message

    def test_red2_fake_measure_column_rejected_with_reason(self) -> None:
        """红例②：携伪 measure_column（与 metric_slot 重推导 oil_output 不一致）即拒。"""
        with pytest.raises(ValueError) as errinfo:
            d.QueryPlanDraft.from_payload(
                {**_base_payload(), "measure_column": "liquid_output"}
            )
        message = str(errinfo.value)
        assert "measure_column" in message
        assert "重推导" in message

    def test_red3_external_tables_rejected_with_reason(self) -> None:
        """红例③：携非空 external_tables 即拒——外表集唯一产源＝词面比对。"""
        with pytest.raises(ValueError) as errinfo:
            d.QueryPlanDraft.from_payload(
                {**_base_payload(), "external_tables": ["erp_well_register"]}
            )
        message = str(errinfo.value)
        assert "external_tables" in message
        assert "词面比对" in message

    def test_red3b_empty_external_tables_still_rejected(self) -> None:
        """禁区键出现即拒（与值是否为空无关——键不在准产白名单）。"""
        with pytest.raises(ValueError) as errinfo:
            d.QueryPlanDraft.from_payload({**_base_payload(), "external_tables": []})
        assert "external_tables" in str(errinfo.value)

    def test_all_six_forbidden_keys_rejected_each_with_reason(self) -> None:
        """六禁区键逐键出现即拒（actor/metric_name/measure_column/unit/limit_effective/external_tables）。"""
        for key in d.DRAFT_FORBIDDEN_REASONS:
            with pytest.raises(ValueError) as errinfo:
                d.QueryPlanDraft.from_payload({**_base_payload(), key: "x"})
            message = str(errinfo.value)
            assert key in message
            assert d.DRAFT_FORBIDDEN_REASONS[key] in message

    def test_unknown_key_outside_whitelist_rejected(self) -> None:
        """白名单双向收窄——五源槽位之外的未知键同样拒（闭世界）。"""
        with pytest.raises(ValueError) as errinfo:
            d.QueryPlanDraft.from_payload({**_base_payload(), "sql": "SELECT 1"})
        assert "sql" in str(errinfo.value)

    def test_red5_window_not_halfopen_rejected(self) -> None:
        """红例⑤：window 非半开区间（start≥end）即拒。"""
        for window in (
            {"start": "2026-10-01", "end": "2026-09-01"},
            {"start": "2026-09-01", "end": "2026-09-01"},
        ):
            with pytest.raises(ValueError) as errinfo:
                d.QueryPlanDraft.from_payload({**_base_payload(), "window": window})
            assert "半开" in str(errinfo.value)

    def test_window_bad_date_rejected(self) -> None:
        with pytest.raises(ValueError, match="ISO"):
            d.QueryPlanDraft.from_payload(
                {**_base_payload(), "window": {"start": "昨天", "end": "2026-10-01"}}
            )

    def test_red6_limit_requested_out_of_range_rejected(self) -> None:
        """红例⑥：limit_requested 非 [1,200] 整数即拒（0/负/超 200/非整数/布尔）。"""
        for bad in (0, -3, 201, 1.5, "3", True):
            with pytest.raises(ValueError) as errinfo:
                d.QueryPlanDraft.from_payload({**_base_payload(), "limit_requested": bad})
            assert "[1, 200]" in str(errinfo.value)

    def test_limit_boundary_values_accepted(self) -> None:
        for value in (1, 200):
            draft = d.QueryPlanDraft.from_payload(
                {**_base_payload(), "limit_requested": value}
            )
            assert draft.limit_requested == value

    def test_direction_outside_binary_rejected(self) -> None:
        with pytest.raises(ValueError, match="asc"):
            d.QueryPlanDraft.from_payload({**_base_payload(), "direction": "倒序"})

    def test_ranking_non_bool_rejected(self) -> None:
        with pytest.raises(ValueError, match="布尔"):
            d.QueryPlanDraft.from_payload({**_base_payload(), "ranking": "是"})

    def test_missing_or_empty_metric_slot_rejected(self) -> None:
        payload = _base_payload()
        del payload["metric_slot"]
        with pytest.raises(ValueError, match="metric_slot"):
            d.QueryPlanDraft.from_payload(payload)
        with pytest.raises(ValueError, match="metric_slot"):
            d.QueryPlanDraft.from_payload({**_base_payload(), "metric_slot": "  "})

    def test_non_mapping_payload_rejected(self) -> None:
        with pytest.raises(ValueError, match="JSON 对象"):
            d.QueryPlanDraft.from_payload(["not", "a", "dict"])  # type: ignore[arg-type]


# ---------- 交付物②：validator（metric_slot 唯一锚重推导——零第二真源） ----------


class TestValidateQueryPlanDraft:
    def test_red4_slot_not_in_registry_rejected(self) -> None:
        """红例④：metric_slot 不在 MEASURE_COLUMNS——不在目录不代答。"""
        draft = d.QueryPlanDraft.from_payload({**_base_payload(), "metric_slot": "完井数"})
        with pytest.raises(ValueError) as errinfo:
            d.validate_query_plan_draft(draft, question="上个月完井数最多的井")
        message = str(errinfo.value)
        assert "MEASURE_COLUMNS" in message
        assert "完井数" in message

    def test_validator_matches_build_query_plan_same_input_same_column_unit(self) -> None:
        """验收：validator 与 build_query_plan 同输入产出同 column/unit（零第二真源）。"""
        question = "上个月日产油量最高的前 5 口井"
        today = _today()
        window = d.parse_time_window(question, today=today)[1]
        assert window is not None
        for slot in d.MEASURE_COLUMNS:
            draft = d.QueryPlanDraft(
                metric_slot=slot, window=window, limit_requested=5,
                ranking=True, direction=d.DIRECTION_DESC,
            )
            plan = d.validate_query_plan_draft(draft, question=question, actor=AQIANG)
            expected = d.build_query_plan(
                metric_slot=slot, metric_name=slot, question=question,
                window=window, today=today, actor=AQIANG,
            )
            assert plan.measure_column == expected.measure_column
            assert plan.unit == expected.unit
            assert plan.limit_effective == expected.limit_effective
            assert plan.external_tables == expected.external_tables
            assert plan.actor == expected.actor == AQIANG

    def test_validator_measure_columns_registry_untouched_single_source(self) -> None:
        """MEASURE_COLUMNS 定义仅 domain.py 一处（票面 grep 闸——禁第二份映射表）。"""
        import subprocess
        result = subprocess.run(
            ["grep", "-rln", r"MEASURE_COLUMNS\s*[:=]", "app/", "tests/"],
            capture_output=True, text=True,
        )
        files = {
            line for line in result.stdout.splitlines()
            if not line.startswith("tests/")
        }
        assert files == {"app/domains/chat/domain.py"}

    def test_validator_limit_effective_via_current_clamp_function(self) -> None:
        """limit_effective←现行收口纯函数（50/200 只封顶不抬底——没写补默认 50）。"""
        window = d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "上个月")
        unspecified = d.QueryPlanDraft(
            metric_slot="日产油量", window=window, limit_requested=None,
            ranking=False, direction=d.DIRECTION_DESC,
        )
        plan = d.validate_query_plan_draft(unspecified, question="日产油量明细")
        assert plan.limit_effective == d.QUERY_DEFAULT_LIMIT
        assert plan.limit_requested is None
        capped = d.QueryPlanDraft(
            metric_slot="日产油量", window=window, limit_requested=200,
            ranking=False, direction=d.DIRECTION_DESC,
        )
        assert d.validate_query_plan_draft(capped, question="x").limit_effective == 200

    def test_validator_external_tables_from_question_word_scan(self) -> None:
        """external_tables←detect_external_tables(问句) 复用（唯一产源＝词面比对）。"""
        window = d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "上个月")
        draft = d.QueryPlanDraft(
            metric_slot="日产油量", window=window, limit_requested=None,
            ranking=False, direction=d.DIRECTION_DESC,
        )
        plan = d.validate_query_plan_draft(
            draft, question="上个月日产油量和 ERP 井位台账对一下"
        )
        assert plan.external_tables == ("erp_well_register",)

    def test_validator_actor_injected_via_parameter(self) -> None:
        """actor←函数参数注入（生产调用点恒传 ctx.actor_who——影子期为测试替身值）。"""
        window = d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "上个月")
        draft = d.QueryPlanDraft(
            metric_slot="日产液量", window=window, limit_requested=None,
            ranking=False, direction=d.DIRECTION_DESC,
        )
        plan = d.validate_query_plan_draft(draft, question="x", actor="替身 · 测试")
        assert plan.actor == "替身 · 测试"
        assert plan.measure_column == "liquid_output"
        assert plan.unit == "方"

    def test_validator_metric_name_is_registry_name(self) -> None:
        """metric_name←MEASURE_COLUMNS 注册名（票面规定——台账原名重推导的注册面锚）。"""
        window = d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "上个月")
        draft = d.QueryPlanDraft(
            metric_slot="油压", window=window, limit_requested=None,
            ranking=False, direction=d.DIRECTION_DESC,
        )
        plan = d.validate_query_plan_draft(draft, question="x")
        assert plan.metric_name == "油压"
        assert plan.measure_column == "oil_pressure"
        assert plan.unit == "MPa"


# ---------- 交付物③：比对算子（执行语义字段集逐字段等值——三态） ----------


def _paired_plans(
    *, draft_kwargs: dict[str, Any] | None = None
) -> tuple[d.QueryPlan, d.QueryPlan]:
    """同源双计划（确定性＝build_query_plan 产出；draft 计划＝validator 重推导产出）。"""
    question = "上个月日产油量最高的前 5 口井"
    today = _today()
    window = d.parse_time_window(question, today=today)[1]
    assert window is not None
    deterministic = d.build_query_plan(
        metric_slot="日产油量", metric_name="★日产油量", question=question,
        window=window, today=today, actor=AQIANG,
    )
    draft_window = d.TimeWindow(window.start, window.end, "", True)
    draft = d.QueryPlanDraft(
        metric_slot="日产油量", window=draft_window, limit_requested=5,
        ranking=True, direction=d.DIRECTION_DESC,
    )
    draft_plan = d.validate_query_plan_draft(
        draft, question=question, actor=AQIANG, **(draft_kwargs or {})
    )
    return draft_plan, deterministic


class TestCompareQueryPlans:
    def test_match_when_execution_fields_equal(self) -> None:
        draft_plan, deterministic = _paired_plans()
        comparison = d.compare_query_plans(draft_plan, deterministic)
        assert comparison.status == d.PLAN_COMPARE_MATCH
        assert comparison.divergent_fields == ()

    def test_label_and_is_default_diff_note_only_not_divergence(self) -> None:
        """window.label/is_default 记差异日志不判分歧——执行语义字段集之外。"""
        draft_plan, deterministic = _paired_plans()
        comparison = d.compare_query_plans(draft_plan, deterministic)
        assert comparison.status == d.PLAN_COMPARE_MATCH
        assert any("window.label" in note for note in comparison.notes)
        assert any("window.is_default" in note for note in comparison.notes)

    def test_diverge_lists_divergent_fields(self) -> None:
        draft_plan, deterministic = _paired_plans()
        flipped = d.clamp_plan_window(
            draft_plan,
            d.TimeWindow(draft_plan.window.start, draft_plan.window.end, "改窗"),
        )
        diverged = d.QueryPlan(
            metric_slot=flipped.metric_slot,
            metric_name=flipped.metric_name,
            measure_column=flipped.measure_column,
            unit=flipped.unit,
            window=flipped.window,
            limit_requested=flipped.limit_requested,
            limit_effective=flipped.limit_effective,
            ranking=flipped.ranking,
            direction=d.DIRECTION_ASC,  # 方向分歧
            external_tables=flipped.external_tables,
            actor=flipped.actor,
        )
        comparison = d.compare_query_plans(diverged, deterministic)
        assert comparison.status == d.PLAN_COMPARE_DIVERGE
        assert "direction" in comparison.divergent_fields
        assert set(comparison.divergent_fields) <= set(d.PLAN_COMPARE_FIELDS)

    def test_diverge_window_endpoint_field_named(self) -> None:
        draft_plan, deterministic = _paired_plans()
        shifted = d.clamp_plan_window(
            draft_plan,
            d.TimeWindow(
                draft_plan.window.start, draft_plan.window.end + timedelta(days=1), "x"
            ),
        )
        comparison = d.compare_query_plans(shifted, deterministic)
        assert comparison.status == d.PLAN_COMPARE_DIVERGE
        assert "window.end" in comparison.divergent_fields

    def test_metric_slot_divergence_named(self) -> None:
        draft_plan, deterministic = _paired_plans()
        other = d.validate_query_plan_draft(
            d.QueryPlanDraft(
                metric_slot="日产液量", window=draft_plan.window,
                limit_requested=draft_plan.limit_requested,
                ranking=draft_plan.ranking, direction=draft_plan.direction,
            ),
            question="上个月日产液量最高的前 5 口井", actor=AQIANG,
        )
        comparison = d.compare_query_plans(other, deterministic)
        assert comparison.status == d.PLAN_COMPARE_DIVERGE
        assert "metric_slot" in comparison.divergent_fields

    def test_incomparable_when_deterministic_missing(self) -> None:
        draft_plan, _det = _paired_plans()
        comparison = d.compare_query_plans(draft_plan, None)
        assert comparison.status == d.PLAN_COMPARE_INCOMPARABLE
        assert any("确定性" in note for note in comparison.notes)

    def test_incomparable_when_draft_missing(self) -> None:
        _draft, deterministic = _paired_plans()
        comparison = d.compare_query_plans(None, deterministic)
        assert comparison.status == d.PLAN_COMPARE_INCOMPARABLE
        assert any("draft" in note for note in comparison.notes)

    def test_compare_fields_constant_covers_execution_set(self) -> None:
        """执行语义字段集合同值（六字段——方案 §2.3 D3 冻结比对范围）。"""
        assert d.PLAN_COMPARE_FIELDS == (
            "metric_slot", "window.start", "window.end",
            "limit_effective", "ranking", "direction",
        )


# ---------- 交付物④：触发谓词（verdict 六站链 ∧ 词面不齐∨解析缺件） ----------


class TestTriggerPredicate:
    def test_casual_wording_triggers_true(self) -> None:
        """「哪几口井采得最狠」→True（词面缺件——DATA_QUESTION_RE 无「几/最狠」）。"""
        assert d.should_trigger_plan_parse(
            verdict_chain="状态机六站链", question="哪几口井采得最狠",
            metric_slot="日产油量",
        ) is True
        reasons = d.plan_parse_trigger_reasons(
            question="哪几口井采得最狠", metric_slot="日产油量"
        )
        assert reasons == (d.PLAN_TRIGGER_LEXICAL_GAP,)

    def test_fast_path_solvable_no_trigger_false(self) -> None:
        """「上月产油最多的前 10 口井」→False（快路可解——词面齐＋metric 锚在册）。"""
        assert d.should_trigger_plan_parse(
            verdict_chain="状态机六站链", question="上月产油最多的前 10 口井",
            metric_slot="日产油量",
        ) is False
        assert d.plan_parse_trigger_reasons(
            question="上月产油最多的前 10 口井", metric_slot="日产油量"
        ) == ()

    def test_other_chain_never_triggers(self) -> None:
        assert d.should_trigger_plan_parse(
            verdict_chain="检索问答链", question="哪几口井采得最狠",
            metric_slot=None,
        ) is False
        assert d.should_trigger_plan_parse(
            verdict_chain=None, question="哪几口井采得最狠", metric_slot=None,
        ) is False

    def test_missing_metric_anchor_is_parse_gap(self) -> None:
        """无指标候选＝解析缺件（LLM#plan 可从 C1 投影填槽——覆盖增值主场景）。"""
        reasons = d.plan_parse_trigger_reasons(
            question="上个月产油情况如何", metric_slot=None
        )
        assert d.PLAN_TRIGGER_PARSE_GAP in reasons
        assert d.should_trigger_plan_parse(
            verdict_chain="状态机六站链", question="上个月产油情况如何",
            metric_slot=None,
        ) is True

    def test_unbound_slot_is_parse_gap(self) -> None:
        """槽位在台账但未绑定计量列（如产量完成率）＝解析缺件——模板装配前提不成立。"""
        reasons = d.plan_parse_trigger_reasons(
            question="上个月产量完成率最高的井", metric_slot="产量完成率"
        )
        assert reasons == (d.PLAN_TRIGGER_PARSE_GAP,)

    def test_both_gaps_reported_together(self) -> None:
        reasons = d.plan_parse_trigger_reasons(
            question="哪几口井采得最狠", metric_slot=None
        )
        assert reasons == (d.PLAN_TRIGGER_LEXICAL_GAP, d.PLAN_TRIGGER_PARSE_GAP)

    def test_data_route_signal_single_source_reused(self) -> None:
        """抽取的确定性路由信号（指标命中＋词面）——与 service 兜底路由同源同判。"""
        metric_hit = [
            d.Candidate(matcher="台账", name="日产油量", confidence="high", kind="metric")
        ]
        term_only = [d.Candidate(matcher="词表", name="躺井", confidence="high", kind="term")]
        fast_question = "上月产油最多的前 10 口井"
        assert d.data_route_signal(fast_question, metric_hit) is True
        assert d.data_route_signal(fast_question, term_only) is False
        assert d.data_route_signal("哪几口井采得最狠", metric_hit) is False


# ---------- 影子接线：ChainDeps 可空缝（plan_drafter）＋影子日志一行结构化 ----------


def _waterline_ok() -> d.WaterlineFace:
    """达标水位面（承诺 T-1＝昨天——N7.4a 放行，影子观测不受安检干扰）。"""
    return d.WaterlineFace(
        layer="汇总层", data_date=_today() - timedelta(days=1),
        promise="T-1", tag="达标（承诺 T-1）", late_days=0,
    )


def _shadow_deps(seams: Seams, drafter: Any) -> chains_mod.ChainDeps:
    """直构链体注入缝（Seams 假缝镜像组合根——另挂 L-01 plan_drafter 替身）。"""
    return chains_mod.ChainDeps(
        config_loader=seams.load_config,
        metrics_loader=seams.load_metrics,
        terms_loader=seams.load_terms,
        faq_matcher=seams.match_faq,
        faq_searcher=seams.search_faq_similar,
        index_searcher_dual=seams.search_index_dual,
        graph_searcher=seams.search_graph,
        anchor_loader=seams.load_anchor,
        completer=seams,
        query_executor=seams.execute_query,
        waterline_loader=seams.load_waterline,
        plan_drafter=drafter,
    )


def _chain_ctx(question: str, *, metric_cards: list[d.MetricCard]) -> d.ChainContext:
    return d.ChainContext(
        run_id="run-shadow-test", question=question, actor_who=AQIANG,
        assembly=d.AssemblyResult(
            anchor_line=None, slots="", terms=[], candidates=[], lanes=[],
            metric_cards=metric_cards,
        ),
    )


_OIL_CARD = d.MetricCard(slot_name="日产油量", name="★日产油量", calibers=[])


def _recording_drafter(
    payload: dict[str, Any] | None, calls: list[str], *, raise_error: bool = False
) -> Any:
    """替身 drafter（喂 Draft——记录调用；None＝返回 None；raise_error＝直接抛）。"""

    async def drafter(question: str) -> Any:
        calls.append(question)
        if raise_error:
            raise RuntimeError("LLM#plan 替身故障")
        if payload is None:
            return None
        return d.QueryPlanDraft.from_payload(payload)

    return drafter


def _shadow_records(caplog: Any) -> list[Any]:
    return [
        record for record in caplog.records
        if record.name == SHADOW_LOGGER and "[shadow-plan]" in record.getMessage()
    ]


class TestShadowWiring:
    async def test_shadow_log_one_structured_line_on_trigger(
        self, seams: Seams, caplog: Any
    ) -> None:
        """触发即一行结构化日志：run_id/触发原因/draft 三态/耗时_ms＋替身被喂 Draft。"""
        caplog.set_level(logging.INFO, logger=SHADOW_LOGGER)
        seams.waterline = _waterline_ok()
        calls: list[str] = []
        payload = {
            "metric_slot": "日产油量",
            "window": {
                "start": (_today() - timedelta(days=30)).isoformat(),
                "end": _today().isoformat(),
            },
            "limit_requested": None,
            "ranking": False,
            "direction": "desc",
        }
        deps = _shadow_deps(seams, _recording_drafter(payload, calls))
        ctx = _chain_ctx("哪几口井采得最狠", metric_cards=[_OIL_CARD])
        events = await collect(chains_mod.query_chain(deps, ctx))
        records = _shadow_records(caplog)
        assert calls == ["哪几口井采得最狠"]  # 替身被喂问句、只调一次
        assert len(records) == 1  # 一问一行
        message = records[0].getMessage()
        assert "\n" not in message  # 结构化单行
        assert "run_id=run-shadow-test" in message
        assert "trigger=词面不齐" in message
        assert "draft_state=一致" in message
        assert "elapsed_ms=" in message
        assert "window.label" in message  # label/is_default 差异记日志不判分歧
        # 影子零生效：SSE 帧不掺影子内容，主链照常出六站帧。
        assert all("shadow" not in str(event.data) for event in events)
        assert any(
            event.event == "node" and event.data["key"] == "N7.3" for event in events
        )

    async def test_unwired_seam_production_default_silent(
        self, seams: Seams, caplog: Any
    ) -> None:
        """注入缝未装配（生产组合根现状）＝恒静默——现网行为零变化硬验收。"""
        caplog.set_level(logging.INFO, logger=SHADOW_LOGGER)
        seams.waterline = _waterline_ok()
        deps = _shadow_deps(seams, None)
        deps = deps.__class__(  # 去掉 plan_drafter——缺省 None 形状
            config_loader=deps.config_loader, metrics_loader=deps.metrics_loader,
            terms_loader=deps.terms_loader, faq_matcher=deps.faq_matcher,
            faq_searcher=deps.faq_searcher, index_searcher_dual=deps.index_searcher_dual,
            graph_searcher=deps.graph_searcher, anchor_loader=deps.anchor_loader,
            completer=deps.completer, query_executor=deps.query_executor,
            waterline_loader=deps.waterline_loader,
        )
        ctx = _chain_ctx("哪几口井采得最狠", metric_cards=[_OIL_CARD])
        await collect(chains_mod.query_chain(deps, ctx))
        assert _shadow_records(caplog) == []

    def test_production_composition_root_never_wires_plan_drafter(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """组合根守护（FX-09/R3-01）：真实生产装配点（ChatService.__init__ →
        ChainDeps 构造，service.py 生产组合根）不装配 plan_drafter——影子期
        「现网行为零变化」硬验收的前提＝缝恒未装配（缝一装配即活：链内
        `if deps.plan_drafter is not None` 守卫对生产装配点零设防，装配即影子
        LLM 调用上现网）。L-02 接线时本守护必须同步改写为断言装配。"""
        service = make_service(chat_db, seams)
        assert service._deps.plan_drafter is None

    async def test_no_trigger_fast_path_no_call_no_log(
        self, seams: Seams, caplog: Any
    ) -> None:
        """快路可解（词面齐＋锚在册）不触发——替身不被调、零影子日志。"""
        caplog.set_level(logging.INFO, logger=SHADOW_LOGGER)
        seams.waterline = _waterline_ok()
        calls: list[str] = []
        deps = _shadow_deps(seams, _recording_drafter(None, calls))
        ctx = _chain_ctx("上个月日产油量最高的三口井", metric_cards=[_OIL_CARD])
        await collect(chains_mod.query_chain(deps, ctx))
        assert calls == []
        assert _shadow_records(caplog) == []

    async def test_parse_gap_downgrade_path_observed_incomparable(
        self, seams: Seams, caplog: Any
    ) -> None:
        """解析缺件（台账指标未绑定计量列→链降级）仍被影子观测——三态＝不可比。"""
        caplog.set_level(logging.INFO, logger=SHADOW_LOGGER)
        calls: list[str] = []
        payload = {
            "metric_slot": "日产油量",
            "window": {
                "start": (_today() - timedelta(days=30)).isoformat(),
                "end": _today().isoformat(),
            },
        }
        deps = _shadow_deps(seams, _recording_drafter(payload, calls))
        unbound_card = d.MetricCard(slot_name="产量完成率", name="★产量完成率")
        ctx = _chain_ctx("上个月产量完成率最高的井", metric_cards=[unbound_card])
        await collect(chains_mod.query_chain(deps, ctx))
        records = _shadow_records(caplog)
        assert calls == ["上个月产量完成率最高的井"]
        assert len(records) == 1
        message = records[0].getMessage()
        assert "trigger=解析缺件" in message
        assert "draft_state=不可比" in message

    async def test_drafter_none_logged_as_incomparable(
        self, seams: Seams, caplog: Any
    ) -> None:
        """替身返回 None（L-02 三重兜底形状）——照落影子行，三态＝不可比。"""
        caplog.set_level(logging.INFO, logger=SHADOW_LOGGER)
        seams.waterline = _waterline_ok()
        calls: list[str] = []
        deps = _shadow_deps(seams, _recording_drafter(None, calls))
        ctx = _chain_ctx("哪几口井采得最狠", metric_cards=[_OIL_CARD])
        await collect(chains_mod.query_chain(deps, ctx))
        records = _shadow_records(caplog)
        assert len(records) == 1
        message = records[0].getMessage()
        assert "draft_state=不可比" in message
        assert "trigger=词面不齐" in message

    async def test_validator_reject_logged_with_reason(
        self, seams: Seams, caplog: Any
    ) -> None:
        """替身喂「不在目录」草案——validator 拒，禁因进影子行注记，主链不受扰。"""
        caplog.set_level(logging.INFO, logger=SHADOW_LOGGER)
        seams.waterline = _waterline_ok()
        calls: list[str] = []
        payload = {
            "metric_slot": "完井数",
            "window": {
                "start": (_today() - timedelta(days=30)).isoformat(),
                "end": _today().isoformat(),
            },
        }
        deps = _shadow_deps(seams, _recording_drafter(payload, calls))
        ctx = _chain_ctx("哪几口井采得最狠", metric_cards=[_OIL_CARD])
        await collect(chains_mod.query_chain(deps, ctx))
        records = _shadow_records(caplog)
        assert len(records) == 1
        message = records[0].getMessage()
        assert "draft_state=不可比" in message
        assert "validator 拒" in message
        assert "MEASURE_COLUMNS" in message

    async def test_drafter_raise_swallowed_chain_unaffected(
        self, seams: Seams, caplog: Any
    ) -> None:
        """替身抛异常——影子路吞并降级（主链零受扰照常走完），异常进影子行注记。"""
        caplog.set_level(logging.INFO, logger=SHADOW_LOGGER)
        seams.waterline = _waterline_ok()
        calls: list[str] = []
        deps = _shadow_deps(seams, _recording_drafter(None, calls, raise_error=True))
        ctx = _chain_ctx("哪几口井采得最狠", metric_cards=[_OIL_CARD])
        events = await collect(chains_mod.query_chain(deps, ctx))
        records = _shadow_records(caplog)
        assert len(records) == 1
        message = records[0].getMessage()
        assert "draft_state=不可比" in message
        assert "drafter 异常" in message
        assert any(  # 主链未断——N7.5 执行帧照常在场
            event.event == "node" and event.data["key"] == "N7.5" for event in events
        )
