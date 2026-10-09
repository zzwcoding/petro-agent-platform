"""V2-31 ReAct 重构验收钉测（票面验收①②③⑥——剧本六分支＋三 caller 桶＋澄清分级
＋轮上限兜底；骨架可跑＝知识型题自主走 doc_retrieve 全链一出引用答案）。

拍板七条（tickets/v2/V2-31-ReAct重构.md＝设计合同）的钉测落点：
- 剧本分支①知识型：LLM 自主选 doc_retrieve（零台账校验触碰——data_query 零调用）；
- 剧本分支②数证结合：task_type=mixed 一轮双执行（plan＋retrieval_need）；
- 剧本分支③全链：发现→发射→执行→再决策各分支（semantic_query 先行→execute→
  finalize）；
- 剧本分支④3 轮上限收敛兜底（预算闸 ReAct 语义——拍板①）；
- 拒因回喂重决策（拍板②——无 repair 调用）：caller 桶计数 understand/decision/
  answer 三桶闭世界＋拒因进下轮消息的断言面（ScriptedCompleter.messages_of）；
- 澄清分级（拍板⑥）：时间窗自动默认＋note 注记／目标歧义 ask 挂起→resume 回喂；
- 处理指南缝（拍板⑦）：GuideProvider 注入——决策上下文消费指南正文；
- 决策发射 schema 校验单测（parse_decision——四 action 闭世界＋轮内上限）。

行为断言锁在决策出口（step payload emission）与观察流形（observe/工具调用计数），
不锁模型原话（拍板任务 5）。
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from appv2.knowledge import Evidence
from appv2.query import (
    LINEAGE_KEY_CALIBER,
    LINEAGE_KEY_WATERMARK,
    LineageLine,
    QueryOutcome,
)
from appv2.retrieval import (
    Observation as RetrievalObservation,
)
from appv2.retrieval import RetrievalBundle
from appv2.runtime import (
    AskChoice,
    AskRequest,
    Budget,
    DefaultGuideProvider,
    RunEvent,
    RunStore,
    parse_decision,
)
from appv2.tools import (
    SCHEMA_PROBE,
    FakeKnowledgeStore,
    FakeQueryEngine,
    FakeRetrievalEngine,
    ToolContext,
    ToolRegistry,
)
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    ANSWER_DRAFT_CITED,
    DECISION_FINALIZE,
    DECISION_WINDOWED,
    UNDERSTAND_DATA,
    QueueQueryEngine,
    drain,
    make_runtime,
)

# ---------- 剧本罐头（结构化决策发射——拍板①合同形） ----------

UNDERSTAND_KNOWLEDGE = "理解：问 W-111 井完井报告记载的投产初期日产油。\n指标候选：无"
DECISION_KNOWLEDGE = (
    '{"thought": "报告事实题——走检索", "action": "execute", '
    '"task_type": "knowledge", "retrieval_need": {"question": '
    '"W-111 井 投产初期日产油", "family_hints": ["completion"]}}'
)
DECISION_MIXED = (
    '{"action": "execute", "task_type": "mixed", '
    '"plan": {"metric_slot": "日产油量", "ranking": false, '
    '"window_start": "2025-09-01", "window_end": "2025-09-03", "limit": 5}, '
    '"retrieval_need": {"question": "日产油量 口径 单位"}}'
)
DECISION_DISCOVER = (
    '{"action": "discover", "discovers": '
    '[{"tool": "semantic_query", "args": {"element_name": "日产油量"}}]}'
)
DECISION_ASK_TARGET = (
    '{"action": "ask", "ask": {"prompt": "您想问哪口井的日产油量？", '
    '"options": ["N-01 井", "Z-16 井"]}}'
)
DECISION_DEFAULT_NOTE = (
    '{"action": "execute", "task_type": "data", '
    '"plan": {"metric_slot": "日产油量", "ranking": false, '
    '"window_start": "2025-09-01", "window_end": "2025-09-03", "limit": 5, '
    '"is_default": true}, "note": "未指明时间窗——已按近 30 天默认"}'
)
DECISION_BAD_METRIC = (
    '{"action": "execute", "task_type": "data", '
    '"plan": {"metric_slot": "采出程度", "ranking": false, '
    '"window_start": "2025-09-01", "window_end": "2025-09-03"}}'
)

_FRAGMENT_TEXT = "W-111 井采用酸压完井，投产初期日产油 291 方。"
_CALIBER_TEXT = "口径说明：日产油量为班次合计日口径，单位吨。"


def _fragment_obs(text: str, fragment_id: str) -> RetrievalObservation:
    return RetrievalObservation(
        kind="fragment",
        text=text,
        snippet=text[:80],
        score=0.9,
        leg="keyword",
        family="completion",
        fragment_id=fragment_id,
        report_id="rep-w111",
        report="W-111 井完井报告",
        library_id="lib-completion",
        library="完井工程库",
        section="第一章",
        locator={"library": "完井工程库", "report": "W-111 井完井报告"},
    )


def _retrieval_with(*obs: RetrievalObservation) -> FakeRetrievalEngine:
    return FakeRetrievalEngine(
        bundle=RetrievalBundle(
            observations=list(obs), window_note=f"召回 {len(obs)} 支/送窗 {len(obs)} 支"
        )
    )


def _rows_outcome() -> QueryOutcome:
    return QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
        lineage=(
            LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量（单位：吨）——口径声明"),
            LineageLine(key=LINEAGE_KEY_WATERMARK, value="汇总层水位 2026-08-31"),
        ),
    )


def _step_kinds(events: list[RunEvent]) -> list[str]:
    return [e.data["step"] for e in events if e.event == "step"]


def _notices(events: list[RunEvent]) -> list[dict[str, Any]]:
    return [e.data for e in events if e.event == "notice"]


# ---------- 剧本分支①：知识型问句自主选 doc_retrieve（零台账校验触碰） ----------


async def test_knowledge_question_autonomous_doc_retrieve(tmp_path: Path) -> None:
    """骨架可跑钉测（票面验收⑥停点）：知识型问句 LLM 自主选 doc_retrieve 全链
    一出引用答案——data_query 台账校验零触碰（Q12 病灶 1 路由翻面的反面钉）。"""
    retrieval = _retrieval_with(_fragment_obs(_FRAGMENT_TEXT, "frag-w111-1"))
    engine = FakeQueryEngine()  # 台账校验计数观测面——必须全零
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_KNOWLEDGE],
        "v2.runtime.decision": [DECISION_KNOWLEDGE, DECISION_FINALIZE],
        "v2.runtime.answer": ["W-111 井投产初期日产油 291 方[1]。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=engine, script=script, retrieval=retrieval,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="W-111 井完井报告里投产初期日产油是多少？", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        # 零台账校验触碰：data_query 的 validate/run 全零（Q12 病灶反面钉）。
        assert engine.validate_calls == 0 and engine.run_calls == 0
        # doc_retrieve 全链恰一次：检索需要逐字进 RetrievalNeed（族提示在位）。
        assert retrieval.retrieve_calls == 1
        assert retrieval.needs[0].question == "W-111 井 投产初期日产油"
        assert retrieval.needs[0].family_hints == ("completion",)
        # 一出引用答案：答案带引标＋引用块带报告出处（INV-1 fail-closed 引用）。
        answer = run.answer or ""
        assert "291 方[1]" in answer
        assert "引用：" in answer and "W-111 井完井报告" in answer
        citations = [e.data for e in events if e.event == "citation"]
        assert [c["index"] for c in citations] == [1]
        assert citations[0]["source"] == "W-111 井完井报告"
        # 决策出口锁定：r1＝execute knowledge、r2＝finalize（不锁模型原话）。
        steps = await store.list_steps(handle.run_id)
        decisions = [
            s for s in steps
            if s.step_type == "decision"
            and (s.payload or {}).get("phase") == "decision"
        ]
        assert decisions[0].payload["emission"]["action"] == "execute"
        assert decisions[0].payload["emission"]["task_type"] == "knowledge"
        assert decisions[1].payload["emission"]["action"] == "finalize"
        # 步序（ReAct 周期）：understand(decision)→decision→execute→observe→
        # decision(finalize)→answer→verify→answer。
        assert _step_kinds(events) == [
            "decision", "decision", "execute", "observe", "decision",
            "answer", "verify", "answer",
        ]
        # 三 caller 桶（无 repair）。
        assert completer.counts() == {
            "v2.runtime.understand": 1,
            "v2.runtime.decision": 2,
            "v2.runtime.answer": 1,
        }
    finally:
        await db.dispose()


# ---------- 剧本分支②：数证结合一轮双执行（task_type=mixed） ----------


async def test_mixed_round_dual_execution(tmp_path: Path) -> None:
    """数证结合：同一轮发射 plan＋retrieval_need——固定代码按序双执行（data→
    knowledge），两支观察都回流后再决策。"""
    retrieval = _retrieval_with(_fragment_obs(_CALIBER_TEXT, "frag-caliber-1"))
    engine = QueueQueryEngine([_rows_outcome()])
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_MIXED, DECISION_FINALIZE],
        "v2.runtime.answer": [
            "N-01 井 2025-09-01 日产油量 21.16 吨[1]；口径：班次合计日口径[3]。",
        ],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=engine, script=script, retrieval=retrieval,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量及口径", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        # 一轮双执行：execute 步恰 2（data_query＋doc_retrieve）、observe 恰 2，
        # 决策轮恰 2（r1 mixed、r2 finalize）。
        kinds = _step_kinds(events)
        assert kinds == [
            "decision", "decision", "execute", "observe", "execute", "observe",
            "decision", "answer", "verify", "answer",
        ]
        assert completer.counts()["v2.runtime.decision"] == 2
        # 双执行计数：data_query run 恰 1＋doc_retrieve 恰 1（同轮两支）。
        assert engine.run_calls == 1
        assert retrieval.retrieve_calls == 1
        # 两支观察都回流（观察流形：[1] 权威行＋[3] 检索片段——[2] 为随行血缘卡）。
        answer = run.answer or ""
        assert "21.16 吨[1]" in answer and "班次合计日口径[3]" in answer
        verdicts = [
            e.data for e in events
            if e.event == "verdict" and e.data.get("rewritten") is not None
        ]
        assert verdicts and verdicts[0]["cited"] == [1, 3]
    finally:
        await db.dispose()


# ---------- 剧本分支③：发现→发射→执行→再决策全链 ----------


async def test_discover_execute_redecide_full_chain(tmp_path: Path) -> None:
    """发现先行：semantic_query 探台账口径卡→观察回流→再决策 execute data→
    再决策 finalize——三决策轮全分支。"""
    knowledge = FakeKnowledgeStore(
        metric_hit=Evidence(
            element_id="201",
            kind="metric",
            value="日产油量：班次合计日口径，单位吨（口径卡）",
            source="sem_metric#201",
            version="1",
            freshness="",
            scope="日",
            binding_state="bound",
        )
    )
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [
            DECISION_DISCOVER, DECISION_WINDOWED, DECISION_FINALIZE,
        ],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    runtime, completer, db = await make_runtime(
        tmp_path,
        engine=QueueQueryEngine([_rows_outcome()]),
        script=script,
        knowledge=knowledge,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "21.16" in (run.answer or "")
        # 全链步序：decision(discover 发射)→discover→observe→decision(execute)→
        # execute→observe→decision(finalize)→answer→verify→answer。
        assert _step_kinds(events) == [
            "decision", "decision", "discover", "observe", "decision",
            "execute", "observe", "decision", "answer", "verify", "answer",
        ]
        # 发现工具经 registry 调用（discover 步 payload 在案）。
        steps = await store.list_steps(handle.run_id)
        discover_steps = [s for s in steps if s.step_type == "discover"]
        assert len(discover_steps) == 1
        assert discover_steps[0].payload["tool"] == "semantic_query"
        assert discover_steps[0].payload["status"] == "ok"
        # 三决策轮（discover→execute→finalize）。
        assert completer.counts()["v2.runtime.decision"] == 3
    finally:
        await db.dispose()


# ---------- 剧本分支④：3 轮上限收敛兜底 ----------


async def test_three_round_cap_converges(tmp_path: Path) -> None:
    """轮预算兜底（拍板①）：模型轮轮重执行不 finalize——第 4 决策入口轮数闸收敛，
    已取得材料如实交付（不静默截断），零起草零核验。"""
    runtime, completer, db = await make_runtime(
        tmp_path,
        engine=QueueQueryEngine([_rows_outcome()]),
        script={
            "v2.runtime.understand": [UNDERSTAND_DATA],
            "v2.runtime.decision": [DECISION_WINDOWED],  # 末条驻留——轮轮重执行
        },
        budget=Budget(max_rounds=3),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "21.16" in (run.answer or "")  # 已取得材料交付——不静默截断
        # 三轮整耗：decision 恰 3 轮、execute/observe 各 3；answer 零调用。
        assert completer.counts() == {
            "v2.runtime.understand": 1,
            "v2.runtime.decision": 3,
        }
        kinds = _step_kinds(events)
        assert kinds.count("execute") == 3 and kinds.count("observe") == 3
        converged = [n for n in _notices(events) if n.get("type") == "budget_converged"]
        assert len(converged) == 1
        assert converged[0]["gates"] == ["max_rounds"]
        # 兜底收敛零起草零核验（无 verify 判定事件）。
        assert not [
            v for v in events
            if v.event == "verdict" and v.data.get("rewritten") is not None
        ]
    finally:
        await db.dispose()


# ---------- 拒因回喂重决策（拍板②——无 repair；三 caller 桶计数钉） ----------


async def test_rejection_feedback_redecision_no_repair(tmp_path: Path) -> None:
    """工具 schema 校验拒（metric_slot 不在台账）→拒因回喂 LLM 重决策——无任何
    repair caller；下轮决策消息携「上次决策被拒」＋拒因原文（messages_of 断言面）。"""
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [
            DECISION_BAD_METRIC, DECISION_WINDOWED, DECISION_FINALIZE,
        ],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "21.16" in (run.answer or "")  # 重决策后成功出数
        # 三 caller 桶闭世界（无 repair 桶——拍板②核心计数断言）。
        counts = completer.counts()
        assert counts == {
            "v2.runtime.understand": 1,
            "v2.runtime.decision": 3,
            "v2.runtime.answer": 1,
        }
        assert not any("repair" in caller for caller in counts)
        # 拒因回喂：第 2 轮决策消息含「上次决策被拒」＋台账拒因原文。
        second_round = completer.messages_of("v2.runtime.decision")[1]
        user_content = second_round[1]["content"]
        assert "上次决策被拒" in user_content
        assert "不在指标台账" in user_content
        # 机读分型 notice（decision_rejected）＋工具拒步留痕（发射合法、
        # 拒在 data_query 校验——execute 步 failed 在案）。
        rejected = [n for n in _notices(events) if n.get("type") == "decision_rejected"]
        assert len(rejected) == 1 and "不在指标台账" in rejected[0]["content"]
        steps = await store.list_steps(handle.run_id)
        failed = [
            s for s in steps
            if s.step_type == "execute" and s.payload.get("status") == "failed"
        ]
        assert len(failed) == 1 and failed[0].payload["tool"] == "data_query"
    finally:
        await db.dispose()


async def test_unparsable_decision_feedback(tmp_path: Path) -> None:
    """决策不可解析（纯散文）→拒因回喂一轮→合法 finalize——真非法产不误解析。"""
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": ["抱歉，我无法输出该决策。", DECISION_FINALIZE],
        "v2.runtime.answer": ["观察材料未覆盖该问题，无法给出结论。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=FakeQueryEngine(), script=script,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        assert "21.16" not in answer  # 零材料零编造
        assert completer.counts()["v2.runtime.decision"] == 2
        second_round = completer.messages_of("v2.runtime.decision")[1]
        assert "决策不可解析" in second_round[1]["content"]
        steps = await store.list_steps(handle.run_id)
        titles = [s.title for s in steps if s.step_type == "decision"]
        assert any("被拒" in title for title in titles)
    finally:
        await db.dispose()


# ---------- 澄清分级（拍板⑥三形态之①②；越集审批归 wiring 钉测） ----------


async def test_clarify_time_window_auto_default(tmp_path: Path) -> None:
    """时间窗歧义不 ask——模型按指南自动默认（近 30 天）＋note 注记出 notice，
    plan.is_default=true 进引擎（Q12 病灶 2 模板卡的反面钉）。"""
    engine = QueueQueryEngine([_rows_outcome()])
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_DEFAULT_NOTE, DECISION_FINALIZE],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="最近的日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "21.16" in (run.answer or "")
        # 注记出流（机读 notice——decision_note）。
        notes = [n for n in _notices(events) if n.get("type") == "decision_note"]
        assert len(notes) == 1 and "近 30 天" in notes[0]["content"]
        # is_default 进引擎计划（engine 侧标注面）。
        assert engine.plans[0].is_default is True
        # 零 ASK 帧（时间窗歧义不挂起）。
        assert not [e for e in events if e.event == "ask"]
    finally:
        await db.dispose()


async def test_clarify_target_ambiguity_ask(tmp_path: Path) -> None:
    """目标歧义→决策发射 ask→clarify 帧挂起→resume 选择回喂决策（user_hint 进
    下轮消息）→带窗执行出数。"""
    script_a: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_ASK_TARGET],
    }
    script_b: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_WINDOWED, DECISION_FINALIZE],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    runtime_a, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_a,
    )
    store = RunStore(db)
    run_id = ""
    try:
        handle = await runtime_a.ask(AskRequest(question="日产油量", actor=ACTOR))
        events = await drain(handle)
        run_id = handle.run_id
        ask_events = [e for e in events if e.event == "ask"]
        assert ask_events, "目标歧义 ASK 帧未发出"
        frame = ask_events[0].data["frame"]
        assert frame["kind"] == "clarify"
        assert frame["prompt"] == "您想问哪口井的日产油量？"
        assert frame["options"] == ["N-01 井", "Z-16 井"]
        run = await store.get_run(run_id)
        assert run is not None and run.status == "waiting_ask"
    finally:
        await db.dispose()

    runtime_b, completer, db_b = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_b,
    )
    store_b = RunStore(db_b)
    try:
        handle_b = await runtime_b.resume(run_id, AskChoice(value="N-01 井"))
        events_b = await drain(handle_b)
        final = await store_b.get_run(run_id)
        assert final is not None and final.status == "completed"
        assert "21.16" in (final.answer or "")
        # 用户补充进下轮决策消息（回喂面）。
        second_round = completer.messages_of("v2.runtime.decision")[0]
        assert "用户已补充：N-01 井" in second_round[1]["content"]
        assert any(e.event == "citation" for e in events_b)
    finally:
        await db_b.dispose()


# ---------- 处理指南缝（拍板⑦——V2-32 消费接口） ----------


async def test_guide_provider_seam(tmp_path: Path) -> None:
    """GuideProvider 注入即生效：决策上下文消费指南正文（V2-32 ontology 资产件
    整替注入的接口钉）。"""

    class _MarkerGuide:
        def guide(self) -> str:
            return "GUIDE-MARKER-XYZ 处理指南注入钉"

    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_FINALIZE],
        "v2.runtime.answer": ["观察材料未覆盖该问题。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=FakeQueryEngine(), script=script, guide=_MarkerGuide(),
    )
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        await drain(handle)
        first_decision = completer.messages_of("v2.runtime.decision")[0]
        assert "GUIDE-MARKER-XYZ" in first_decision[1]["content"]
    finally:
        await db.dispose()


def test_default_guide_contains_contract_and_grading() -> None:
    guide = DefaultGuideProvider(today=date(2026, 10, 8)).guide()
    assert "action" in guide and "finalize" in guide  # 决策发射合同
    assert "近 30 天" in guide and "2026-09-08" in guide  # 澄清分级①（today−30）
    assert "2026-10-08" in guide  # 今天锚点
    assert "ask" in guide and "审批" in guide  # 澄清分级②③


# ---------- 决策发射 schema 校验单测（parse_decision——拒因回喂的闸单点） ----------


def test_parse_decision_four_actions() -> None:
    emission = parse_decision('{"action": "finalize", "note": "收工"}')
    assert not isinstance(emission, str)
    assert emission.action == "finalize" and emission.note == "收工"

    discover = parse_decision(
        '{"action": "discover", "discovers": [{"tool": "table_schema", "args": {}}]}'
    )
    assert not isinstance(discover, str)
    assert discover.discovers == ({"tool": "table_schema", "args": {}},)

    knowledge = parse_decision(
        '{"action": "execute", "task_type": "knowledge", '
        '"retrieval_need": {"question": "Q"}}'
    )
    assert not isinstance(knowledge, str)
    assert knowledge.task_type == "knowledge" and knowledge.plan is None

    mixed = parse_decision(
        '{"action": "execute", "task_type": "mixed", '
        '"plan": {"metric_slot": "日产油量", "ranking": false}, '
        '"retrieval_need": {"question": "Q"}}'
    )
    assert not isinstance(mixed, str)
    assert mixed.plan is not None and mixed.retrieval_need is not None

    ask = parse_decision(
        '{"action": "ask", "ask": {"prompt": "哪口井？", "options": ["A", "B"]}}'
    )
    assert not isinstance(ask, str)
    assert ask.ask_prompt == "哪口井？" and ask.ask_options == ("A", "B")


def test_parse_decision_rejections() -> None:
    assert isinstance(parse_decision("纯散文"), str)
    assert "不可解析" in str(parse_decision("纯散文"))
    assert isinstance(parse_decision('{"action": "fly"}'), str)
    assert isinstance(parse_decision('{"action": "discover"}'), str)  # 缺 discovers
    assert isinstance(parse_decision(
        '{"action": "discover", "discovers": [{"tool": "raw_sql", "args": {}}]}'
    ), str)  # 未知发现工具（湖表通道不在白名单）
    assert isinstance(parse_decision(
        '{"action": "discover", "discovers": ['
        '{"tool": "semantic_query", "args": {}}, '
        '{"tool": "table_schema", "args": {}}, '
        '{"tool": "semantic_query", "args": {}}]}'
    ), str)  # 超轮内上限（≤2）
    assert isinstance(parse_decision('{"action": "execute"}'), str)  # 缺 task_type
    assert isinstance(parse_decision(
        '{"action": "execute", "task_type": "data"}'
    ), str)  # data 缺 plan
    assert isinstance(parse_decision(
        '{"action": "execute", "task_type": "data", "plan": {"ranking": false}}'
    ), str)  # plan 缺 metric_slot
    assert isinstance(parse_decision(
        '{"action": "execute", "task_type": "knowledge", "retrieval_need": {}}'
    ), str)  # 缺 question
    assert isinstance(parse_decision(
        '{"action": "ask", "ask": {"prompt": "P", "options": ["只此一项"]}}'
    ), str)  # 选项不足


def test_table_schema_discovery_tool() -> None:
    """发现工具 table_schema：白名单⑥卡＋湖表不开放（拍板④）；registry 五工具。"""
    registry = ToolRegistry(
        knowledge=FakeKnowledgeStore(),
        query=FakeQueryEngine(),
        retrieval=FakeRetrievalEngine(),
    )
    names = [d.name for d in registry.descriptors()]
    assert names == [
        "semantic_query", "data_query", "doc_retrieve", "graph_query", "table_schema",
    ]
    ctx = ToolContext(actor="dev-u1", budget=4)
    cards = asyncio.run(registry.call(SCHEMA_PROBE, {}, ctx))
    assert cards.status == "ok"
    text = "\n".join(obs.content for obs in cards.observations)
    assert "agg.fct_daily_metering" in text and "agg.dim_well" in text
    assert "sem_metric" in text and "sem_term" in text
    assert "kb 片段清单" in text
    # 白名单按面取卡。
    agg = asyncio.run(registry.call(SCHEMA_PROBE, {"area": "agg"}, ctx))
    assert len(agg.observations) == 3
    # 湖表不开放（拍板④）——如实告知，零结构泄漏。
    raw = asyncio.run(registry.call(SCHEMA_PROBE, {"table": "raw_lake_wide"}, ctx))
    assert raw.status == "ok"
    assert "不在探查白名单" in raw.observations[0].content
    assert "raw/lake 湖表不开放" in raw.observations[0].content
    locator = raw.observations[0].locator
    assert locator["kind"] == "notice"
    assert locator["notice_type"] == "schema_not_allowed"


def test_table_schema_by_name_forms() -> None:
    """P-024b 审查 S1 修复钉：按名查询两形态——全名/短名（去 schema 前缀）都命中
    白名单卡。agg 卡文本表名后紧跟全角「（」（旧匹配要求表名后跟半角空格＝白名单内
    三表全部误判不开放——P-024.rev S1 实测）；kb 组「库 …（」形同失配。修复后：
    agg/sem/kb 三组按名可达，白名单外照拒不回退。"""
    registry = ToolRegistry(
        knowledge=FakeKnowledgeStore(),
        query=FakeQueryEngine(),
        retrieval=FakeRetrievalEngine(),
    )
    ctx = ToolContext(actor="dev-u1", budget=4)

    def _one_card(args: dict[str, Any]):
        result = asyncio.run(registry.call(SCHEMA_PROBE, args, ctx))
        assert result.status == "ok"
        assert len(result.observations) == 1
        return result.observations[0]

    # agg 全名（指南示范形——handlers._SCHEMA_SCHEMA 示例值）与短名（去前缀）。
    full = _one_card({"table": "agg.fct_daily_metering"})
    assert "日产计量事实表" in full.content
    assert full.locator["kind"] == "schema"
    short = _one_card({"table": "fct_daily_metering"})
    assert short.content == full.content
    # agg 其余两表（旧缺陷同形态——全角括号紧邻表名）。
    assert "井维度" in _one_card({"table": "agg.dim_well"}).content
    assert "井维度" in _one_card({"table": "dim_well"}).content
    assert "日期维度" in _one_card({"table": "agg.dim_date"}).content
    # sem 账按名（旧形态本已命中——修复不回退）。
    assert "指标台账" in _one_card({"table": "sem_metric"}).content
    assert "术语台账" in _one_card({"table": "sem_term"}).content
    # kb 组按名（S1 第二失配形态——「库 kb 片段清单（」无匹配模式）。
    assert "检索库" in _one_card({"table": "kb 片段清单"}).content
    # 白名单外照拒（修复不放开湖表）。
    rejected = _one_card({"table": "raw_lake_wide"})
    assert rejected.locator["notice_type"] == "schema_not_allowed"


async def test_consecutive_asks_capped_material_direct_answer(tmp_path: Path) -> None:
    """P-024b 疑点2 钉：连环 ask 截断＋材料直答形——r1 执行出数、r2 clarify 挂起
    （ask＝1），resume 回收后执行一轮再 ask（run-69517e02 实测形态——执行不清零，
    ask＝2 达上限）→不再挂起，带已取得材料如实直答（completed；零新 ask 帧；
    机读 notice clarify_capped 恰 1 条）。"""
    script_a: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_WINDOWED, DECISION_ASK_TARGET],
    }
    runtime_a, _completer_a, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_a,
    )
    store = RunStore(db)
    run_id = ""
    try:
        handle = await runtime_a.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run_id = handle.run_id
        assert len([e for e in events if e.event == "ask"]) == 1  # 首次澄清照常挂起
        run = await store.get_run(run_id)
        assert run is not None and run.status == "waiting_ask"
    finally:
        await db.dispose()

    script_b: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        # 恢复段：先执行（出数）再 ask——执行轮不清零计数（封口环的关键语义）。
        "v2.runtime.decision": [DECISION_WINDOWED, DECISION_ASK_TARGET],
    }
    runtime_b, _completer, db_b = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_b,
    )
    store_b = RunStore(db_b)
    try:
        handle_b = await runtime_b.resume(run_id, AskChoice(value="N-01 井"))
        events_b = await drain(handle_b)
        final = await store_b.get_run(run_id)
        assert final is not None and final.status == "completed"
        # 材料直答形：已取得的权威行材料原样交付（不再挂起、不编造）。
        answer = final.answer or ""
        assert "21.16" in answer and "连续澄清" in answer
        # 连环 ask 被截断：恢复段零新 ask 帧；截断机读 notice 恰 1 条。
        assert not [e for e in events_b if e.event == "ask"]
        capped = [n for n in _notices(events_b) if n.get("type") == "clarify_capped"]
        assert len(capped) == 1
    finally:
        await db_b.dispose()


async def test_tool_retry_budget_is_per_tool_name(tmp_path: Path) -> None:
    """P-024b C2 钉：retryable 同参重试一次按工具名计数——discover 链（semantic_
    query）上的重试不再挤占 execute（data_query）的重试份额（旧全局一次计数下
    discover 重试耗掉 execute 份额＝tool_unavailable 零交付）。"""

    class _FlakyKnowledge(FakeKnowledgeStore):
        """首次 evidence 抛超时（retryable 通道）——discover 重试的被控源。"""

        def __init__(self, hit: Evidence) -> None:
            super().__init__(metric_hit=hit)
            self.evidence_calls_list: list[int] = []

        def evidence(self, query: Any) -> list[Evidence]:
            self.evidence_calls_list.append(1)
            if len(self.evidence_calls_list) == 1:
                raise TimeoutError("上游抖动（剧本注入）")
            return [self._metric_hit]  # type: ignore[list-item]

    class _FlakyOnceEngine(FakeQueryEngine):
        """首次 run 抛超时（retryable 通道）——execute 重试的被控源。"""

        def __init__(self, outcome: QueryOutcome) -> None:
            super().__init__()
            self._outcome = outcome

        def run(self, plan: Any) -> QueryOutcome:
            self.run_calls += 1
            if self.run_calls == 1:
                raise TimeoutError("上游抖动（剧本注入）")
            return self._outcome

    knowledge = _FlakyKnowledge(
        Evidence(
            element_id="201",
            kind="metric",
            value="日产油量：班次合计日口径，单位吨（口径卡）",
            source="sem_metric#201",
            version="1",
            freshness="",
            scope="日",
            binding_state="bound",
        )
    )
    engine = _FlakyOnceEngine(_rows_outcome())
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [
            DECISION_DISCOVER, DECISION_WINDOWED, DECISION_FINALIZE,
        ],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script, knowledge=knowledge,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "21.16" in (run.answer or "")
        # 两工具各得一次重试：semantic_query 恰 2 调（失败＋重试成功）、
        # data_query run 恰 2 调（失败＋重试成功）。
        assert len(knowledge.evidence_calls_list) == 2
        assert engine.run_calls == 2
        kinds = _step_kinds(events)
        assert kinds.count("discover") == 2 and kinds.count("execute") == 2
        assert not [n for n in _notices(events) if n.get("type") == "tool_unavailable"]
    finally:
        await db.dispose()
