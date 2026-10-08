"""L-05 生效路与 pinned_plan 与最小披露测试（闸 B 交付——先红后绿）。

票面（tickets/phase3/L-05-生效路与pinned_plan与最小披露.md）四件交付物对应：
①生效开关（InfraSettings additive 键 plan_effective_enabled，缺省 false＝快路-only
  现状逐字节不变——off 态 verdict 帧零新键）＋兜底生效路（LLM#plan 拒→澄清额度在弹
  candidates 澄清帧有界一次／无额度或无候选现状降级解释链接续）；
②pinned_plan 新缝（ChainContext 字段＋N7.1 确定性复验消费零模型＋chat_run.plan_pinned
  持久化＋审批恢复重放——不盲信挂起载荷，篡改拒例在案，全程零 LLM 重调）；
③最小披露（verdict 帧 intent_source additive 键＋血缘①LLM 路尾缀——五要素键序不动；
  前端渲染归 web/src/landing/A1.test.jsx）；
④闸 B 机器面帧断言——golden 实跑归收尾报告。

影子并存语义（L-02 铁律不回翻）：生效 on 时影子日志照记（观测不断）；钉入成功影子行
消费 ctx.pinned_plan 不重调 LLM（一份流量一次调用）；钉入失败链内影子观测照 L-02
现状自行调用落行。钉入计划只进链体 N7.1 确定性复验（D1——LLM 只在入口层）。
"""

import logging
from datetime import date
from typing import Any

from app.domains.chat import chains as chains_mod
from app.domains.chat import domain as d
from app.domains.chat.store import ChatStore
from app.infra.clock import now
from app.infra.config import InfraSettings
from app.infra.db import ConnectionManager
from tests.domains.chat.conftest import AQIANG, Seams, collect, events_by_name, make_service

SHADOW_LOGGER = "domains.chat"

# 触发 qualifying 问句（产量完成率在台账但未绑定计量列——解析缺件→触发谓词命中）。
TRIGGER_QUESTION = "上个月产量完成率最高的井"
# 快路可解问句（词面齐＋日产油量绑定——谓词不命中）。
FAST_QUESTION = "上个月日产油量最高的三口井"

_VALID_PLAN_REPLY = (
    '{"metric_slot": "日产油量", "window": {"start": "2026-09-01", "end": "2026-10-01"}, '
    '"limit_requested": null, "ranking": true, "direction": "desc"}'
)
_UNBOUND_PLAN_REPLY = (
    '{"metric_slot": "完井数", "window": {"start": "2026-09-01", "end": "2026-10-01"}, '
    '"limit_requested": null, "ranking": true, "direction": "desc"}'
)

_SIX_STATION_INTENT = '{"chain": "状态机六站链", "confidence": 0.95}'


def _plan_reply_for(slot: str) -> str:
    return (
        f'{{"metric_slot": "{slot}", "window": {{"start": "2026-09-01", "end": "2026-10-01"}}, '
        f'"limit_requested": null, "ranking": true, "direction": "desc"}}'
    )


def _pinned_plan(
    *, metric_slot: str = "日产油量", question: str = TRIGGER_QUESTION,
    ranking: bool = True, limit_requested: int | None = None,
) -> d.QueryPlan:
    """合法钉入计划（走 validator 产出——测试基准对象）。"""
    draft = d.QueryPlanDraft(
        metric_slot=metric_slot,
        window=d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "上个月"),
        limit_requested=limit_requested, ranking=ranking, direction=d.DIRECTION_DESC,
    )
    return d.validate_query_plan_draft(draft, question=question, actor=AQIANG)


def _raw_plan(**overrides: Any) -> d.QueryPlan:
    """绕 validator 直接构造 QueryPlan（模拟持久化载荷被篡改后的重建对象）。"""
    fields: dict[str, Any] = dict(
        metric_slot="完井数", metric_name="完井数", measure_column="well_count",
        unit="口", window=d.TimeWindow(date(2026, 9, 1), date(2026, 10, 1), "改窗"),
        limit_requested=None, limit_effective=50, ranking=True,
        direction=d.DIRECTION_DESC, external_tables=(), actor="篡改者",
    )
    fields.update(overrides)
    return d.QueryPlan(**fields)


def _plan_calls(seams: Seams) -> int:
    return seams.completions.count("chat.intent.plan")


# ---------- 交付物①：生效开关（off＝现状逐字节不变；on＝六站链 run 恒带来源键） ----------


class TestSwitchOffByteIdentical:
    async def test_off_trigger_question_no_key_no_pin_shadow_only_call(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """off（缺省）＋触发谓词命中问句：verdict 零新键、无钉入、LLM#plan 只影子调一次。"""
        seams.plan_reply = _VALID_PLAN_REPLY
        service = make_service(chat_db, seams)  # plan_effective_enabled=None＝缺省 false
        events = await collect(service.ask(
            TRIGGER_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert "intent_source" not in by_name["verdict"][0]
        assert "clarify" not in by_name  # 兜底澄清不因 off 出现
        # 链内影子观测照 L-02 现状自行调用（生效路未接线——一份流量一次调用）。
        assert _plan_calls(seams) == 1
        # 产量完成率未绑定——现行降级解释链（行为零变化）。
        n71_finish = [
            f for f in by_name["node"]
            if f["key"] == "N7.1" and f["state"] == "finish"
        ]
        assert any("降级解释链" in str(f.get("note")) for f in n71_finish)
        assert all("意图来源" not in str(f.get("note")) for f in n71_finish)

    async def test_off_fast_question_zero_plan_call(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """off＋快路可解：谓词不命中零 LLM#plan 调用（L-02 现状），verdict 零新键。"""
        service = make_service(chat_db, seams)
        events = await collect(service.ask(
            FAST_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert "intent_source" not in by_name["verdict"][0]
        assert _plan_calls(seams) == 0
        assert seams.calls.get("query_exec") == 1  # 快路照常出数


class TestSwitchOnDisclosure:
    async def test_on_fast_path_intent_source_deterministic(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """on＋快路可解：intent_source=deterministic（快路恒 deterministic），链路零改动。"""
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.ask(
            FAST_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert by_name["verdict"][0]["intent_source"] == d.INTENT_SOURCE_DETERMINISTIC
        assert _plan_calls(seams) == 0  # 快路不调 LLM#plan（D3 快路优先）
        n71_finish = [
            f for f in by_name["node"] if f["key"] == "N7.1" and f["state"] == "finish"
        ]
        assert any("三要素齐" in str(f.get("note")) for f in n71_finish)
        assert all("LLM 精解析" not in str(f.get("note")) for f in n71_finish)
        lineage = by_name["lineage"][0]["items"]
        assert "意图来源" not in lineage[0]["value"]  # 快路血缘零尾缀

    async def test_on_non_query_chain_no_key(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """on＋裁决检索问答链：verdict 零新键（非问数入口——既有形状不变）。"""
        seams.intent_reply = '{"chain": "检索问答链", "confidence": 0.9}'
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.ask(
            "防砂方式是什么", session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert by_name["verdict"][0]["chain"] == "检索问答链"
        assert "intent_source" not in by_name["verdict"][0]


# ---------- 交付物①：兜底生效路（on∧触发→钉入；拒→澄清帧有界一次／现状降级） ----------


class TestEffectivePathPin:
    async def test_on_trigger_pin_success_end_to_end(
        self, chat_db: ConnectionManager, seams: Seams, caplog: Any
    ) -> None:
        """on∧触发∧validator 过：钉入进链出数——来源披露三面（verdict 键/N7.1 行/血缘①尾缀）
        ＋plan_pinned 持久化＋一份流量一次调用（影子行消费钉入计划不重调）。"""
        caplog.set_level(logging.INFO, logger=SHADOW_LOGGER)
        seams.plan_reply = _VALID_PLAN_REPLY
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.ask(
            TRIGGER_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        # 来源披露①：verdict 帧 additive 键。
        assert by_name["verdict"][0]["intent_source"] == d.INTENT_SOURCE_LLM_PLAN
        # 来源披露②：N7.1 finish 行（golden 提取器兼容——「三要素齐：」前缀保留）。
        n71_finish = [
            f for f in by_name["node"] if f["key"] == "N7.1" and f["state"] == "finish"
        ]
        assert len(n71_finish) == 1
        note = str(n71_finish[0]["note"])
        assert note.startswith("三要素齐：")
        assert "意图来源：LLM 精解析（已复验）" in note
        # 来源披露③：血缘①口径行 LLM 路尾缀；五要素键序不动。
        lineage = by_name["lineage"][0]["items"]
        assert lineage[0]["value"].endswith("——意图来源：LLM 精解析（经校验）")
        assert [item["key"] for item in lineage] == [
            "① 口径", "② 来源表", "③ 过滤条件", "　└（权限注入）",
            "④ 数据截至批次", "⑤ 收口注记",
        ]
        # 钉入计划进执行缝（LLM 解析的指标/排名进链体模板装配）。
        assert seams.calls.get("query_exec") == 1
        assert seams.executed_plans[0].metric_slot == "日产油量"
        assert seams.executed_plans[0].ranking is True
        assert seams.executed_plans[0].window.start == date(2026, 9, 1)
        # 持久化：chat_run.plan_pinned 落列（QueryPlan dict 投影）。
        run_id = by_name["session"][0]["run_id"]
        run = await ChatStore(chat_db).get_run(run_id)
        assert run is not None and run.plan_pinned is not None
        assert run.plan_pinned["metric_slot"] == "日产油量"
        # 一份流量一次调用：生效路入口层调用，链内影子观测消费钉入计划不重调。
        assert _plan_calls(seams) == 1
        # 影子观测照记（观测不断——L-02 语义并存）。
        shadow_rows = [
            r.getMessage() for r in caplog.records
            if r.name == SHADOW_LOGGER and "[shadow-plan]" in r.getMessage()
        ]
        assert len(shadow_rows) == 1
        assert "生效路" in shadow_rows[0]

    async def test_on_trigger_validator_reject_clarify_bounded_once(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """on∧触发∧validator 拒（草案指标未绑定→drafter 兜底 None）：澄清额度在→
        candidates 澄清帧有界一次（挂起 interrupt_clarify）；链不分派；来源键 deterministic。"""
        seams.plan_reply = _UNBOUND_PLAN_REPLY
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.ask(
            TRIGGER_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        verdict = by_name["verdict"][0]
        assert verdict["intent_source"] == d.INTENT_SOURCE_DETERMINISTIC
        assert verdict["need_clarify"] is True
        assert verdict["chain"] is None
        clarify = by_name["clarify"][0]
        assert clarify["subtype"] == "candidates"
        assert clarify["choices"]  # 产量完成率候选在场
        # 挂起（流收束不发 done）——有界一次的存储强制。
        assert "done" not in by_name
        run_id = by_name["session"][0]["run_id"]
        run = await ChatStore(chat_db).get_run(run_id)
        assert run is not None
        assert run.status == "interrupt_clarify"
        assert run.clarify_count == 1
        assert run.plan_pinned is None  # 拒＝不钉
        assert "N7.1" not in [f["key"] for f in by_name.get("node", [])]
        assert _plan_calls(seams) == 1  # 链未分派——影子观测未发生

    async def test_on_trigger_llm_none_clarify_bounded_once(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """on∧触发∧LLM#plan 不可用（解析坏→None）：同澄清兜底（有界一次）。"""
        service = make_service(chat_db, seams, plan_effective_enabled=True)  # plan_reply=None
        events = await collect(service.ask(
            TRIGGER_QUESTION, session_id=None, page_context=None, anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert by_name["verdict"][0].get("need_clarify") is True
        assert by_name["clarify"][0]["subtype"] == "candidates"

    async def test_on_trigger_reject_no_candidates_current_degrade(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """on∧触发∧拒∧无候选可澄清（build_candidate_clarify None）：现状链路——
        链内降级解释链接续（W-AUX③），零新帧形状；链内影子观测再调一次落行（L-02 现状）。"""
        seams.intent_reply = _SIX_STATION_INTENT  # 无候选——兜底信号路由不达六站链，LLM 采信强制
        seams.plan_reply = _UNBOUND_PLAN_REPLY
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.ask(
            "三季度累积亏空是多少", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert "clarify" not in by_name
        assert by_name["verdict"][0]["intent_source"] == d.INTENT_SOURCE_DETERMINISTIC
        n71_finish = [
            f for f in by_name["node"] if f["key"] == "N7.1" and f["state"] == "finish"
        ]
        assert any("降级解释链" in str(f.get("note")) for f in n71_finish)
        assert "answer" in by_name  # 接续检索照常收场
        assert _plan_calls(seams) == 2  # 生效路一次＋链内影子观测一次（钉入失败路）

    async def test_on_trigger_zero_time_words_window_grounded_to_default(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """生效钉入路时间落定守卫（golden L05G2 L04-14 红例）：问句零时间词＋LLM 编造
        1 天窗→钉入前落默认窗（持久化/执行/帧三面同源），来源键仍 llm_plan。"""
        seams.intent_reply = _SIX_STATION_INTENT  # 词面不齐——确定性信号路由不达，LLM 采信强制
        seams.plan_reply = (
            '{"metric_slot": "日产油量", "window": {"start": "2026-10-08", '
            '"end": "2026-10-09"}, "limit_requested": null, "ranking": false, '
            '"direction": "desc"}'
        )
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.ask(
            "各井日产油量是多少？", session_id=None, page_context=None,
            anchors=[], actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert by_name["verdict"][0]["intent_source"] == d.INTENT_SOURCE_LLM_PLAN
        default = d.default_time_window(today=now().date())
        assert seams.executed_plans[0].window == default  # 编造窗不进执行
        n71_finish = [
            f for f in by_name["node"] if f["key"] == "N7.1" and f["state"] == "finish"
        ]
        assert any("默认窗" in str(f.get("note")) for f in n71_finish)
        run_id = by_name["session"][0]["run_id"]
        run = await ChatStore(chat_db).get_run(run_id)
        assert run is not None and run.plan_pinned is not None
        assert run.plan_pinned["window"]["is_default"] is True  # 持久化同源落定
        assert run.plan_pinned["window"]["label"] == default.label

    async def test_pin_fallback_quota_exhausted_no_clarify_flip(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """无澄清额度（clarify_count 已 1）：拒后不翻澄清帧——现状链路（unit 直测私有面）。"""
        from app.domains.chat.store import ChatRunRow

        seams.plan_reply = _UNBOUND_PLAN_REPLY
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        assembly = d.AssemblyResult(
            anchor_line=None, slots="", terms=[],
            candidates=[d.Candidate(matcher="台账", name="产量完成率",
                                    confidence="high", kind="metric")],
            lanes=[], metric_cards=[],
        )
        verdict = {"chain": "状态机六站链", "slots": "", "confidence": "高",
                   "need_clarify": False, "source": "llm"}
        run = ChatRunRow(
            id="run-quota", session_id="sess-quota", status="running",
            clarify_count=1, started_at=now(), created_at=now(), updated_at=now(),
        )
        pinned = await service._effective_plan_pin(
            TRIGGER_QUESTION, assembly, verdict, run, AQIANG,
        )
        assert pinned is None
        assert verdict.get("need_clarify") is not True  # 无额度——不翻澄清帧
        assert verdict["intent_source"] == d.INTENT_SOURCE_DETERMINISTIC
        assert run.plan_pinned is None


# ---------- golden L05G2 实跑红例修正：时间落定守卫（问句零时间词→窗强制默认窗） ----------
#
# 实证：L04-14「各井日产油量是多少？」（词面不齐→触发；零时间词）——LLM#plan 编造
# 1 天窗（2026-10-08→2026-10-09）过 validator 被钉入，机器判窗端点分歧（红）。平台
# 纪律「无显式时间→默认窗」（parse_time_window missing 契约）——零时间词时任何
# LLM window 都是编造，落默认窗照快路同语义（守卫纯函数零模型，钉入与复验同源）。


def _invented_window_plan(question: str) -> d.QueryPlan:
    """已验证但窗为编造值的钉入计划（bound 指标——validator 本身拦不住编造窗）。"""
    draft = d.QueryPlanDraft(
        metric_slot="日产油量",
        window=d.TimeWindow(date(2026, 10, 8), date(2026, 10, 9), "编造窗"),
        limit_requested=None, ranking=False, direction=d.DIRECTION_DESC,
    )
    return d.validate_query_plan_draft(draft, question=question, actor=AQIANG)


class TestGroundPinnedWindow:
    def test_zero_time_words_forces_default_window(self) -> None:
        """问句零时间词＋编造窗→默认窗（照快路 missing 契约同语义）。"""
        plan = _invented_window_plan("各井日产油量是多少？")
        grounded = d.ground_pinned_window(plan, question="各井日产油量是多少？")
        assert grounded.window == d.default_time_window(today=now().date())
        assert grounded.window.is_default is True
        assert grounded.metric_slot == plan.metric_slot  # 其余字段不动

    def test_explicit_time_words_keep_pinned_window(self) -> None:
        """有显式时间词照钉入窗不动（LLM 具体化＝设计内能力）。"""
        plan = _pinned_plan()  # TRIGGER_QUESTION 带「上个月」
        assert d.ground_pinned_window(
            plan, question=TRIGGER_QUESTION,
        ) == plan

    def test_vague_time_words_keep_pinned_window(self) -> None:
        """模糊时间词（「最近」）照钉入窗不动（模糊窗由 LLM 具体化——设计内）。"""
        question = "最近各井采得最狠是哪几口"
        plan = _pinned_plan(question=question)
        assert d.ground_pinned_window(plan, question=question) == plan


# ---------- 交付物②：pinned_plan 新缝（ChainContext 字段＋N7.1 复验消费——链级） ----------


def _chain_deps(seams: Seams) -> chains_mod.ChainDeps:
    """直构链体注入缝（Seams 假缝——plan_drafter/shadow_log_sink 缺省未装配）。"""
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
    )


def _chain_ctx(
    question: str, *, pinned_plan: d.QueryPlan | None = None,
    candidates: list[d.Candidate] | None = None,
    metric_cards: list[d.MetricCard] | None = None,
    clarify_available: bool = True,
) -> d.ChainContext:
    return d.ChainContext(
        run_id="run-pin-test", question=question, actor_who=AQIANG,
        assembly=d.AssemblyResult(
            anchor_line=None, slots="", terms=[], candidates=candidates or [],
            lanes=[], metric_cards=metric_cards or [],
        ),
        pinned_plan=pinned_plan, clarify_available=clarify_available,
    )


class TestChainPinnedConsumption:
    async def test_pinned_revalidated_and_consumed(self, seams: Seams) -> None:
        """有钉→复验过直用：零模型出数（无任何 LLM caller），行标「已复验」。"""
        plan = _pinned_plan(question="哪几口井采得最狠")
        events = await collect(chains_mod.query_chain(
            _chain_deps(seams), _chain_ctx("哪几口井采得最狠", pinned_plan=plan),
        ))
        by_name = events_by_name(events)
        n71_finish = [
            f for f in by_name["node"] if f["key"] == "N7.1" and f["state"] == "finish"
        ]
        assert len(n71_finish) == 1
        assert str(n71_finish[0]["note"]).startswith("三要素齐：")
        assert "意图来源：LLM 精解析（已复验）" in str(n71_finish[0]["note"])
        assert seams.completions == []  # 链体零模型（D1——复验确定性）
        assert seams.calls.get("query_exec") == 1
        # 直用＝消费复验产出（D1：执行与复验后计划一致；问句零时间词时含时间落定）。
        assert seams.executed_plans[0] == d.revalidate_pinned_plan(
            plan, question="哪几口井采得最狠", actor=AQIANG,
        )

    async def test_pinned_bypasses_vague_window_askback(self, seams: Seams) -> None:
        """有钉→模糊时间窗不再缺参反问（钉入计划携确定窗——LLM 路已解析，链体直用）。"""
        question = "最近各井采得最狠是哪几口"
        plan = _pinned_plan(question=question)
        events = await collect(chains_mod.query_chain(
            _chain_deps(seams), _chain_ctx(question, pinned_plan=plan),
        ))
        by_name = events_by_name(events)
        assert "clarify" not in by_name
        assert seams.calls.get("query_exec") == 1
        assert seams.executed_plans[0].window == plan.window

    async def test_pinned_reject_clarify_available_bounded_once(self, seams: Seams) -> None:
        """复验拒（篡改载荷→指标未绑定）∧澄清额度在→candidates 澄清帧（链内哨兵）零执行。"""
        tampered = _raw_plan()
        candidates = [d.Candidate(matcher="台账", name="产量完成率",
                                  confidence="high", kind="metric")]
        events = await collect(chains_mod.query_chain(_chain_deps(seams), _chain_ctx(
            TRIGGER_QUESTION, pinned_plan=tampered, candidates=candidates,
        )))
        by_name = events_by_name(events)
        clarify = by_name["clarify"][0]
        assert clarify["subtype"] == "candidates"
        assert clarify.get("_chain_signal") is True  # 链内哨兵（service 拦截面承接）
        assert seams.calls.get("query_exec") is None  # 复验拒＝零执行

    async def test_pinned_reject_no_quota_degrades(self, seams: Seams) -> None:
        """复验拒∧无额度：现状降级解释链接续（W-AUX③）——零新帧形状。"""
        tampered = _raw_plan()
        events = await collect(chains_mod.query_chain(_chain_deps(seams), _chain_ctx(
            TRIGGER_QUESTION, pinned_plan=tampered, clarify_available=False,
        )))
        by_name = events_by_name(events)
        assert "clarify" not in by_name
        n71_finish = [
            f for f in by_name["node"] if f["key"] == "N7.1" and f["state"] == "finish"
        ]
        assert any("降级解释链" in str(f.get("note")) for f in n71_finish)
        assert "answer" in by_name  # 接续检索收场
        assert seams.calls.get("query_exec") is None

    async def test_pinned_reject_no_usable_candidates_degrades(self, seams: Seams) -> None:
        """复验拒∧额度在但无可用候选（build_candidate_clarify None）：现状降级解释链接续。"""
        tampered = _raw_plan()
        events = await collect(chains_mod.query_chain(_chain_deps(seams), _chain_ctx(
            TRIGGER_QUESTION, pinned_plan=tampered, candidates=[],
        )))
        by_name = events_by_name(events)
        assert "clarify" not in by_name
        assert "answer" in by_name

    async def test_pinned_replay_grounds_time_less_question_window(
        self, seams: Seams
    ) -> None:
        """链内复验同源时间落定：零时间词问句＋钉入编造窗→复验落默认窗后消费。"""
        plan = _invented_window_plan("各井日产油量是多少？")
        events = await collect(chains_mod.query_chain(
            _chain_deps(seams), _chain_ctx("各井日产油量是多少？", pinned_plan=plan),
        ))
        by_name = events_by_name(events)
        assert seams.calls.get("query_exec") == 1
        assert seams.executed_plans[0].window == d.default_time_window(today=now().date())
        n71_finish = [
            f for f in by_name["node"] if f["key"] == "N7.1" and f["state"] == "finish"
        ]
        assert any("默认窗" in str(f.get("note")) for f in n71_finish)

    async def test_fast_path_untouched_without_pin(self, seams: Seams) -> None:
        """无钉（快路）链路零改动：现行「三要素齐」行无来源标注、血缘零尾缀。"""
        card = d.MetricCard(slot_name="日产油量", name="★日产油量", calibers=[])
        events = await collect(chains_mod.query_chain(
            _chain_deps(seams), _chain_ctx(FAST_QUESTION, metric_cards=[card]),
        ))
        by_name = events_by_name(events)
        n71_finish = [
            f for f in by_name["node"] if f["key"] == "N7.1" and f["state"] == "finish"
        ]
        note = str(n71_finish[0]["note"])
        assert "三要素齐" in note and "LLM 精解析" not in note
        lineage = by_name["lineage"][0]["items"]
        assert "意图来源" not in lineage[0]["value"]
        assert [item["key"] for item in lineage] == [
            "① 口径", "② 来源表", "③ 过滤条件", "　└（权限注入）",
            "④ 数据截至批次", "⑤ 收口注记",
        ]


# ---------- 交付物②：持久化载体（序列化两向）＋恢复重放（审批挂起——不盲信） ----------


class TestPinnedSerialization:
    def test_payload_round_trip_equal(self) -> None:
        plan = _pinned_plan(limit_requested=5)
        payload = d.plan_pinned_payload(plan)
        assert payload["metric_slot"] == "日产油量"
        assert payload["window"] == {
            "start": "2026-09-01", "end": "2026-10-01", "label": "上个月", "is_default": False,
        }
        assert payload["limit_effective"] == 5
        import json

        json.dumps(payload, ensure_ascii=False)  # JSONB 可序列化（无 date/裸对象）
        assert d.plan_pinned_from_payload(payload) == plan

    def test_payload_malformed_rejected(self) -> None:
        good = d.plan_pinned_payload(_pinned_plan())
        for broken in (
            {**good, "metric_slot": ""},  # 空槽位
            {k: v for k, v in good.items() if k != "measure_column"},  # 缺键
            {**good, "window": {"start": "2026-09-01"}},  # 窗缺端点
            {**good, "window": {**good["window"], "start": "2026/09/01"}},  # 非 ISO
            {**good, "ranking": "是"},  # 布尔位被串占
        ):
            try:
                d.plan_pinned_from_payload(broken)
            except ValueError:
                continue
            raise AssertionError(f"坏载荷未被拒：{broken}")

    def test_revalidate_rederives_deterministically(self) -> None:
        plan = _pinned_plan()
        revalidated = d.revalidate_pinned_plan(plan, question=TRIGGER_QUESTION, actor=AQIANG)
        assert revalidated == plan


async def _suspend_approval_run(
    chat_db: ConnectionManager, *, question: str, plan_pinned: dict[str, Any] | None,
) -> str:
    """直构审批挂起 run（interrupt_approval＋持久化 plan_pinned——恢复重放测试底座）。"""
    store = ChatStore(chat_db)
    session = await store.ensure_session(None, user_id="aqiang", title=question[:20])
    run = await store.create_run(session.id)
    run.status = "interrupt_approval"
    run.pending_approval_id = "APP-1007-t00001"
    run.pending_interrupt = {
        "kind": "approval", "scene": "extable", "approval_id": "APP-1007-t00001",
        "chain": "状态机六站链", "question": question,
        "tables": ["erp_well_register"], "plan": {}, "anchors": [],
    }
    run.plan_pinned = plan_pinned
    await store.save_run(run)
    return run.id


class TestApprovalResumeReplay:
    async def test_resume_consumes_pinned_plan_zero_llm_recall(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """恢复重放：取持久化 plan→重跑 validator→整节点重跑消费（零 LLM 重调——替身断言）。"""
        plan = _pinned_plan()
        run_id = await _suspend_approval_run(
            chat_db, question=TRIGGER_QUESTION, plan_pinned=d.plan_pinned_payload(plan),
        )
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.resume(
            run_id, kind="approval", choice=None, decision="approve", reason=None,
            actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert seams.completions == []  # 全程零 LLM（复验确定性——不重调模型）
        n71_finish = [
            f for f in by_name["node"] if f["key"] == "N7.1" and f["state"] == "finish"
        ]
        assert any("意图来源：LLM 精解析（已复验）" in str(f.get("note")) for f in n71_finish)
        assert by_name["verdict"][0]["intent_source"] == d.INTENT_SOURCE_LLM_PLAN
        assert seams.calls.get("query_exec") == 1
        assert seams.executed_plans[0] == plan  # 执行与批过的钉入计划一致（D1 前提）

    async def test_resume_tampered_slot_rejected_falls_back(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """篡改持久化载荷（指标槽位换未绑定指标）：复验拒——不盲信，按现状链路续跑。"""
        tampered = d.plan_pinned_payload(_pinned_plan())
        tampered["metric_slot"] = "完井数"
        run_id = await _suspend_approval_run(
            chat_db, question=TRIGGER_QUESTION, plan_pinned=tampered,
        )
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        events = await collect(service.resume(
            run_id, kind="approval", choice=None, decision="approve", reason=None,
            actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert seams.calls.get("query_exec") is None  # 篡改计划未被执行
        n71_finish = [
            f for f in by_name["node"] if f["key"] == "N7.1" and f["state"] == "finish"
        ]
        assert all("已复验" not in str(f.get("note")) for f in n71_finish)
        assert any("降级解释链" in str(f.get("note")) for f in n71_finish)
        assert by_name["verdict"][0]["intent_source"] == d.INTENT_SOURCE_DETERMINISTIC

    async def test_resume_tampered_derived_field_ignored(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """篡改重推导字段（measure_column 换他列）：复验按槽位重推导——篡改不生效。"""
        tampered = d.plan_pinned_payload(_pinned_plan())
        tampered["measure_column"] = "liquid_output"
        run_id = await _suspend_approval_run(
            chat_db, question=TRIGGER_QUESTION, plan_pinned=tampered,
        )
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        await collect(service.resume(
            run_id, kind="approval", choice=None, decision="approve", reason=None,
            actor_who=AQIANG,
        ))
        assert seams.calls.get("query_exec") == 1
        assert seams.executed_plans[0].measure_column == "oil_output"  # 重推导胜出

    async def test_resume_tampered_window_grounded_for_time_less_question(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """篡改持久化窗（零时间词问句＋编造 1 天窗）：复验时间落定守卫拦——
        重放执行落默认窗（不盲信持久化载荷的 window 槽位）。"""
        tampered = d.plan_pinned_payload(
            _invented_window_plan("各井日产油量是多少？"),
        )
        run_id = await _suspend_approval_run(
            chat_db, question="各井日产油量是多少？", plan_pinned=tampered,
        )
        service = make_service(chat_db, seams, plan_effective_enabled=True)
        await collect(service.resume(
            run_id, kind="approval", choice=None, decision="approve", reason=None,
            actor_who=AQIANG,
        ))
        assert seams.calls.get("query_exec") == 1
        assert seams.executed_plans[0].window == d.default_time_window(today=now().date())

    async def test_resume_without_pin_off_switch_byte_identical(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """off＋无持久化 plan：恢复路径零新键（现状逐字节不变）。"""
        run_id = await _suspend_approval_run(
            chat_db, question=TRIGGER_QUESTION, plan_pinned=None,
        )
        service = make_service(chat_db, seams, plan_effective_enabled=False)
        events = await collect(service.resume(
            run_id, kind="approval", choice=None, decision="approve", reason=None,
            actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert "intent_source" not in by_name["verdict"][0]

    async def test_resume_pinned_under_off_switch_still_consumes(
        self, chat_db: ConnectionManager, seams: Seams
    ) -> None:
        """off＋挂起前已钉入：恢复仍消费持久化 plan（完成已生效 run——确定性重放），键 llm_plan。"""
        plan = _pinned_plan()
        run_id = await _suspend_approval_run(
            chat_db, question=TRIGGER_QUESTION, plan_pinned=d.plan_pinned_payload(plan),
        )
        service = make_service(chat_db, seams, plan_effective_enabled=False)
        events = await collect(service.resume(
            run_id, kind="approval", choice=None, decision="approve", reason=None,
            actor_who=AQIANG,
        ))
        by_name = events_by_name(events)
        assert by_name["verdict"][0]["intent_source"] == d.INTENT_SOURCE_LLM_PLAN
        assert seams.calls.get("query_exec") == 1
        assert seams.executed_plans[0] == plan


# ---------- 交付物①：生效开关装配面（Settings 键＋显式注入/env 覆盖） ----------


class TestSwitchWiring:
    def test_settings_default_false(self) -> None:
        """InfraSettings additive 键缺省 false（回退纪律载体——off＝快路-only 现状）。"""
        assert InfraSettings().plan_effective_enabled is False

    def test_service_default_reads_settings_off(
        self, chat_db: ConnectionManager, seams: Seams, monkeypatch: Any
    ) -> None:
        """显式注入缺省（None）＝读 Settings；env 未设＝off。"""
        monkeypatch.delenv("PLAN_EFFECTIVE_ENABLED", raising=False)
        from app.infra.config import get_settings

        get_settings.cache_clear()
        try:
            service = make_service(chat_db, seams)
            assert service._plan_effective_enabled is False
        finally:
            get_settings.cache_clear()

    def test_service_env_override_on(
        self, chat_db: ConnectionManager, seams: Seams, monkeypatch: Any
    ) -> None:
        """env 覆盖 on（FX-08 lifespan 测试策略同款——env 注入验证 on 态装配）。"""
        monkeypatch.setenv("PLAN_EFFECTIVE_ENABLED", "true")
        from app.infra.config import get_settings

        get_settings.cache_clear()
        try:
            service = make_service(chat_db, seams)
            assert service._plan_effective_enabled is True
        finally:
            get_settings.cache_clear()

    def test_settings_illegal_value_rejected(self, monkeypatch: Any) -> None:
        """非法值拒绝装载（禁静默回落——DE-16 strict-bool 同口径）。"""
        import pytest

        monkeypatch.setenv("PLAN_EFFECTIVE_ENABLED", "yes")
        from app.infra.config import get_settings

        get_settings.cache_clear()
        try:
            with pytest.raises(ValueError):
                InfraSettings()
        finally:
            get_settings.cache_clear()
