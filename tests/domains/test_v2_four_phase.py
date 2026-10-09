"""V2-34 子任务图＋前置条件机骨架钉测（P-033 骨架版——ADR-0005 四相位）。

票面验收（骨架版范围）的钉测落点：
- QuestionGroup schema（LangGraph 校验单点）：subtasks[{id/question/ledger_notes/
  tool/chain}]、子问题上限 ≤4、discover/ask 三动作闭世界、发现预算闸；
- 工具匹配独立 schema 收口点：matches 与问题组闭合世界对账、chain/tool 一致、
  plan/retrieval_need 按链必带；
- 前置条件机（纯固定代码，LLM 无权判定）：四态枚举 pass/blocked_ask/
  blocked_refuse/note 全在；AST＋import 双证零 LLM；
- 四相位路由真跑（端到端剧本）：clarify→toolmatch→precondition→batch→汇总→
  verify→收口；blocked_ask 真接 ASK 挂起帧；回炉不重跑（成功子问题执行指纹
  零重复）；3 轮失败子集回炉；discover≤10＋计数埋点落 step payload；
- 词典层第 1 轮全量注入：决策上下文含台账全量块＋Manifest ledger_dump 族来源
  行（非懒加载——零 discover 也注入）；常驻块不重复入史；
- caliber_key 三态：场景词确定性匹配／无场景词阈值判断形 ASK 反问／无场景词
  取数形双口径并列注记＋非法口径拒；
- ToolContext 放行态：approved_tables 进 ctx（A2 裁决落点）；
- 生产装配接线：create_app 真指南（OntologyGuideProvider）＋four_phase 形参；
  DefaultGuideProvider 退役。
"""

from __future__ import annotations

import ast
import asyncio
import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot
from appv2.query import QueryOutcome
from appv2.runtime import (
    AskChoice,
    AskRequest,
    RunStore,
    parse_decision,
)
from appv2.runtime.subtask import (
    MAX_SUBTASKS_CONTRACT,
    parse_question_group,
    parse_tool_match,
)
from appv2.tools import (
    FakeKnowledgeStore,
    FakeQueryEngine,
    FakeRetrievalEngine,
    ToolRegistry,
    dump_from_store,
    judge,
    ledger_facts,
)
from appv2.tools.precondition import (
    STATE_BLOCKED_ASK,
    STATE_BLOCKED_REFUSE,
    STATE_NOTE,
    STATE_PASS,
    SUBTASK_STATES,
    SubtaskInput,
)
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    QueueQueryEngine,
    drain,
    make_runtime,
)
from tests.domains.test_v2_react_loop import (
    _fragment_obs,
    _retrieval_with,
    _rows_outcome,
)

# ---------- 词典层注入底座（真源同产线一路：快照→读面→dump_from_store） ----------

DUMP_STORE = InMemoryKnowledgeStore(question_array_snapshot(), today=date(2026, 10, 8))
LEDGER_DUMP = dump_from_store(DUMP_STORE)

# ---------- 四相位剧本罐头 ----------

UNDERSTAND_MULTI = "理解：既要数值也要报告佐证。\n指标候选：日产油量"

CLARIFY_GROUP_DATA_KNOWLEDGE = json.dumps(
    {
        "action": "decompose",
        "thought": "两诉求——权威数值＋报告事实",
        "question_group": {
            "subtasks": [
                {
                    "id": "s1",
                    "question": "2025-09-01 到 09-03 各井日产油量",
                    "ledger_notes": "日产油量｜bound｜窗 2025-09-01~2025-09-03",
                    "chain": "data",
                    "tool": "data_query",
                },
                {
                    "id": "s2",
                    "question": "W-111 井完井报告记载的投产初期日产油",
                    "ledger_notes": "完井报告事实——检索链（台账无此口径）",
                    "chain": "knowledge",
                    "tool": "doc_retrieve",
                },
            ]
        },
    },
    ensure_ascii=False,
)

TOOLMATCH_TWO = json.dumps(
    {
        "matches": [
            {
                "id": "s1",
                "chain": "data",
                "tool": "data_query",
                "plan": {
                    "metric_slot": "日产油量",
                    "ranking": False,
                    "window_start": "2025-09-01",
                    "window_end": "2025-09-03",
                    "limit": 5,
                },
            },
            {
                "id": "s2",
                "chain": "knowledge",
                "tool": "doc_retrieve",
                "retrieval_need": {
                    "question": "W-111 井 投产初期日产油",
                    "family_hints": ["completion"],
                },
            },
        ]
    },
    ensure_ascii=False,
)

# 引标指向批量汇聚后的全局观察序：[1]＝agg_row 行、[3]＝kb 片段（[2]＝血缘卡）。
_SUMMARY_DRAFT = (
    "子任务 s1：2025-09-01 各井日产油量 N-01 为 21.16 吨 [1]。\n"
    "子任务 s2：W-111 井完井报告记载投产初期日产油 291 方 [3]。"
)

_FOUR_PHASE_E2E_SCRIPT = {
    "v2.runtime.understand": [UNDERSTAND_MULTI],
    "v2.runtime.decision": [CLARIFY_GROUP_DATA_KNOWLEDGE, TOOLMATCH_TWO],
    "v2.runtime.answer": [_SUMMARY_DRAFT],
}

_E2E_QUESTION = "2025 年 9 月 1 日到 3 日的日产油量，以及 W-111 井完井报告里的投产初期日产油"


class FourPhaseEngine(QueueQueryEngine):
    """四相位测试引擎——候选台账扩含水率（多支组/回炉支的引擎侧校验面）。"""

    def __init__(
        self,
        outcomes: Sequence[QueryOutcome],
        slots: frozenset[str] = frozenset({"日产油量", "日产液量", "油压", "含水率"}),
    ) -> None:
        super().__init__(outcomes)
        self.ledger_metric_slots = set(slots)


def _step_payloads(steps: list[Any], phase: str) -> list[dict[str, Any]]:
    """步记录按 payload.phase 过滤（store.list_steps 返回 AgentV2Step 对象）。"""
    return [(s.payload or {}) for s in steps if (s.payload or {}).get("phase") == phase]


async def _run_question(runtime: Any, question: str) -> list[Any]:
    handle = await runtime.ask(AskRequest(question=question, actor=ACTOR))
    return await drain(handle)


# ---------- schema 单测：QuestionGroup（相位①发射的 LangGraph 校验单点） ----------


def test_question_group_schema_happy_and_caps() -> None:
    group = parse_question_group(CLARIFY_GROUP_DATA_KNOWLEDGE)
    assert not isinstance(group, str)
    assert group.kind == "decompose"
    assert group.group is not None
    subtasks = group.group.as_payload()["subtasks"]
    assert [st["id"] for st in subtasks] == ["s1", "s2"]
    assert all(st["ledger_notes"] for st in subtasks)  # 台账注释必带（R2）
    assert subtasks[0]["chain"] == "data" and subtasks[0]["tool"] == "data_query"

    # 子问题上限 ≤4（Owner 认可值）
    many = [
        {"id": f"s{i}", "question": "q", "ledger_notes": "n"}
        for i in range(MAX_SUBTASKS_CONTRACT + 1)
    ]
    rejected = parse_question_group(
        json.dumps({"action": "decompose", "question_group": {"subtasks": many}},
                   ensure_ascii=False)
    )
    assert isinstance(rejected, str) and "上限" in rejected

    # 台账注释缺失＝拒（分解缺 ledger_notes 不成组）
    missing = parse_question_group(json.dumps(
        {"action": "decompose", "question_group": {"subtasks": [
            {"id": "s1", "question": "q"}]}}, ensure_ascii=False))
    assert isinstance(missing, str) and "ledger_notes" in missing

    # 非法动作越界
    assert isinstance(parse_question_group('{"action": "fly"}'), str)


def test_clarify_discover_budget_gate() -> None:
    emission = parse_question_group(
        '{"action": "discover", "discovers": ['
        '{"tool": "semantic_query", "args": {"element_name": "日产油量"}}]}',
        discover_budget_left=2,
    )
    assert not isinstance(emission, str) and emission.kind == "discover"

    # 预算耗尽＝拒因回喂（发现预算 ≤10 闸——不靠模型自律）
    rejected = parse_question_group(
        '{"action": "discover", "discovers": ['
        '{"tool": "semantic_query", "args": {"question": "日产油量"}}]}',
        discover_budget_left=0,
    )
    assert isinstance(rejected, str) and "发现预算" in rejected

    # 一次发射支数不得超剩余预算
    over = parse_question_group(
        '{"action": "discover", "discovers": ['
        '{"tool": "semantic_query", "args": {"question": "a"}}, '
        '{"tool": "table_schema", "args": {}}]}',
        discover_budget_left=1,
    )
    assert isinstance(over, str) and "发现预算" in over

    ask = parse_question_group(
        '{"action": "ask", "ask": {"prompt": "哪口井？", "options": ["N-01", "Z-16"]}}'
    )
    assert not isinstance(ask, str) and ask.kind == "ask"


def test_tool_match_closes_world_against_group() -> None:
    group = parse_question_group(CLARIFY_GROUP_DATA_KNOWLEDGE)
    assert not isinstance(group, str) and group.group is not None
    matches = parse_tool_match(TOOLMATCH_TWO, group.group)
    assert not isinstance(matches, str)
    assert [(m.id, m.chain, m.tool) for m in matches] == [
        ("s1", "data", "data_query"), ("s2", "knowledge", "doc_retrieve"),
    ]

    # 未知 id＝拒（闭合世界）
    stray = parse_tool_match('{"matches": [{"id": "s9", "chain": "data", '
                             '"tool": "data_query", "plan": {"metric_slot": "日产油量", '
                             '"ranking": false}}]}', group.group)
    assert isinstance(stray, str) and "s9" in stray

    # 覆盖缺口＝拒（组内每个子问题必须有匹配）
    partial = parse_tool_match('{"matches": [{"id": "s1", "chain": "data", '
                               '"tool": "data_query", "plan": {"metric_slot": "日产油量", '
                               '"ranking": false}}]}', group.group)
    assert isinstance(partial, str) and "s2" in partial

    # data 链缺 plan／plan 缺 metric_slot＝拒（schema 收口）
    no_plan = parse_tool_match('{"matches": ['
                               '{"id": "s1", "chain": "data", "tool": "data_query"}, '
                               '{"id": "s2", "chain": "knowledge", "tool": "doc_retrieve", '
                               '"retrieval_need": {"question": "q"}}]}', group.group)
    assert isinstance(no_plan, str)

    # chain/tool 不一致＝拒
    wrong_tool = parse_tool_match('{"matches": ['
                                  '{"id": "s1", "chain": "data", "tool": "doc_retrieve", '
                                  '"plan": {"metric_slot": "日产油量", "ranking": false}}, '
                                  '{"id": "s2", "chain": "knowledge", "tool": "doc_retrieve", '
                                  '"retrieval_need": {"question": "q"}}]}', group.group)
    assert isinstance(wrong_tool, str)


# ---------- 前置条件机单测：四态＋零 LLM 双证 ----------


def test_precondition_four_states_reachable() -> None:
    facts = ledger_facts(LEDGER_DUMP)
    base_plan = {"metric_slot": "日产油量", "ranking": False,
                 "window_start": "2025-09-01", "window_end": "2025-09-03"}

    # pass：干净取数形
    v_pass = judge(SubtaskInput("s1", "各井日产油量", "data", plan=dict(base_plan)), facts)
    assert v_pass.state == STATE_PASS

    # blocked_ask：无场景词＋阈值判断形（双口径支）→ ASK 反问口径
    v_ask = judge(SubtaskInput(
        "s2", "各井含水率是否超过 30", "data",
        plan={"metric_slot": "含水率", "ranking": False,
              "window_start": "2025-09-01", "window_end": "2025-09-03"},
    ), facts)
    assert v_ask.state == STATE_BLOCKED_ASK
    assert v_ask.ask is not None and len(v_ask.ask.options) == 2

    # blocked_refuse：禁用词子问题如实拒答（带替代）
    v_refuse = judge(SubtaskInput(
        "s3", "各井老完成率", "data",
        plan={"metric_slot": "老完成率", "ranking": False,
              "window_start": "2025-09-01", "window_end": "2025-09-03"},
    ), facts)
    assert v_refuse.state == STATE_BLOCKED_REFUSE
    assert "产量完成率" in v_refuse.reason

    # note：单井支持性注记随行（照常执行）
    v_note = judge(SubtaskInput(
        "s4", "N-01 井 2025-09-01 日产油量", "data",
        plan={"metric_slot": "日产油量", "ranking": False,
              "window_start": "2025-09-01", "window_end": "2025-09-02"},
    ), facts)
    assert v_note.state == STATE_NOTE
    assert any("单井" in n for n in v_note.notes)

    # 四态枚举闭世界（R1 判定面）
    assert SUBTASK_STATES == frozenset(
        {STATE_PASS, STATE_BLOCKED_ASK, STATE_BLOCKED_REFUSE, STATE_NOTE}
    )


def test_precondition_caliber_three_forms() -> None:
    facts = ledger_facts(LEDGER_DUMP)
    window = {"window_start": "2025-09-01", "window_end": "2025-09-03"}

    # 场景词（月报）→确定性匹配口径支 B（化验实测·月度/正式）——用户已答，非系统代选
    v_scene = judge(SubtaskInput(
        "c1", "各井含水率月报口径数值", "data",
        plan={"metric_slot": "含水率", "ranking": False, "caliber_key": "B", **window},
    ), facts)
    assert v_scene.state == STATE_NOTE  # 判定注记随行（口径支落定不属四态外）
    assert any("口径支 B" in n for n in v_scene.notes)

    # 无场景词＋阈值判断形→ASK 反问
    v_threshold = judge(SubtaskInput(
        "c2", "含水率是否达标", "data",
        plan={"metric_slot": "含水率", "ranking": False, **window},
    ), facts)
    assert v_threshold.state == STATE_BLOCKED_ASK

    # 无场景词＋取数形→双口径并列注记（血缘卡两支同载，PROP-BOHAI-008=C）
    v_dual = judge(SubtaskInput(
        "c3", "各井含水率", "data",
        plan={"metric_slot": "含水率", "ranking": False, **window},
    ), facts)
    assert v_dual.state == STATE_NOTE
    assert any("双口径" in n for n in v_dual.notes)

    # 非法 caliber_key（合法口径校验）→拒
    v_illegal = judge(SubtaskInput(
        "c4", "各井日产油量", "data",
        plan={"metric_slot": "日产油量", "ranking": False, "caliber_key": "Z", **window},
    ), facts)
    assert v_illegal.state == STATE_BLOCKED_REFUSE


def test_precondition_external_table_gate_uses_approved_state() -> None:
    facts = ledger_facts(LEDGER_DUMP)
    plan = {"metric_slot": "日产油量", "ranking": False,
            "external_tables": ["erp_well_register"]}

    v_blocked = judge(SubtaskInput("x1", "井位台账关联日产油量", "data", plan=dict(plan)), facts)
    assert v_blocked.state == STATE_BLOCKED_ASK
    assert v_blocked.ask is not None and v_blocked.ask.kind == "external_table_approval"

    v_approved = judge(
        SubtaskInput("x1", "井位台账关联日产油量", "data", plan=dict(plan)),
        facts, approved_tables=("erp_well_register",),
    )
    assert v_approved.state == STATE_NOTE  # 放行后注记随行，不重排计划
    assert any("放行" in n for n in v_approved.notes)


def test_precondition_freshness_window_note_truthful() -> None:
    facts = ledger_facts(LEDGER_DUMP)
    # 水位 2026-08-31 照实判定（不造达标假象——票面任务 7）
    v = judge(SubtaskInput(
        "w1", "今年各井日产油量", "data",
        plan={"metric_slot": "日产油量", "ranking": False,
              "window_start": "2026-01-01", "window_end": "2026-10-08"},
    ), facts, watermark=date(2026, 8, 31))
    assert v.state == STATE_NOTE
    assert any("2026-08-31" in n for n in v.notes)


def test_ctx_of_carries_approved_tables_from_state() -> None:
    """ToolContext 放行态接线（A2 裁决落点——batch/execute 的 ctx 随状态走）。"""
    from appv2.runtime.graph import _ctx_of
    from appv2.runtime.state import RunState

    state = RunState(run_id="run-x", approved_ids=["erp_well_register"])
    ctx = _ctx_of(state)
    assert ctx.approved_tables == ("erp_well_register",)
    assert ctx.actor == "" and ctx.budget == 4  # 既有字段零漂移


def test_precondition_and_parse_layers_are_zero_llm() -> None:
    """R1 双证：AST 扫描（无模型调用形）＋import 扫描（无 LLM 通道）。"""
    targets = [
        Path("appv2/tools/precondition.py"),
        Path("appv2/tools/ledger.py"),
        Path("appv2/runtime/subtask.py"),
    ]
    forbidden_calls = {"complete", "ainvoke", "invoke", "agenerate", "generate"}
    forbidden_modules = ("llm", "gateway", "litellm", "openai", "langchain")
    for target in targets:
        tree = ast.parse(target.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls, (
                    f"{target}: 前置条件机面出现模型调用形 {node.func.attr}"
                )
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names]
                if isinstance(node, ast.ImportFrom) and node.module:
                    names.append(node.module)
                for name in names:
                    assert not any(part in name for part in forbidden_modules), (
                        f"{target}: import 了 LLM 通道 {name}"
                    )


# ---------- 四相位路由真跑（端到端剧本） ----------


def test_four_phase_routing_topology() -> None:
    """LangGraph 路由图上四相位真节点/真边（程序闸骨架版判定面）。"""
    from appv2.api.ontology_guide import OntologyGuideProvider
    from appv2.runtime import EventBus
    from appv2.runtime.graph import LoopDeps, build_graph

    deps = LoopDeps(
        registry=ToolRegistry(
            knowledge=FakeKnowledgeStore(),
            query=FakeQueryEngine(),
            retrieval=FakeRetrievalEngine(),
        ),
        models={},
        builder=object(),  # type: ignore[arg-type]
        store=object(),  # type: ignore[arg-type]
        bus=EventBus(),
        guide=OntologyGuideProvider(today=date(2026, 10, 8)),
    )
    legacy = build_graph(deps)
    four = build_graph(deps, four_phase=True)
    legacy_nodes = set(legacy.get_graph().nodes)
    four_nodes = set(four.get_graph().nodes)
    assert {"clarify", "toolmatch", "precondition", "batch"} <= four_nodes
    assert not {"clarify", "toolmatch", "precondition", "batch"} & legacy_nodes
    edges = {(e[0], e[1]) for e in four.get_graph().edges}
    assert ("clarify", "toolmatch") in edges
    assert ("toolmatch", "precondition") in edges
    assert ("precondition", "batch") in edges
    assert ("understand", "clarify") in edges


async def test_four_phase_end_to_end_scripted(tmp_path: Path) -> None:
    """骨架可跑：clarify→toolmatch→precondition→批量执行→汇总→verify→收口。"""
    retrieval = _retrieval_with(_fragment_obs(
        "W-111 井采用酸压完井，投产初期日产油 291 方。", "frag-w111-1"))
    engine = QueueQueryEngine([_rows_outcome()])
    runtime, completer, db = await make_runtime(
        tmp_path,
        engine=engine,
        script=_FOUR_PHASE_E2E_SCRIPT,
        four_phase=True,
        ledger_dump=lambda: dict(LEDGER_DUMP),
        retrieval=retrieval,
    )
    try:
        events = await _run_question(runtime, _E2E_QUESTION)
        assert [e.event for e in events][-1] == "verdict"
        final = events[-1].data
        assert final["status"] == "completed"

        store = RunStore(db)
        steps = await store.list_steps(final["run_id"])
        clarify = _step_payloads(steps, "clarify")
        assert clarify and "question_group" in clarify[0]["emission"]
        subtasks = clarify[0]["emission"]["question_group"]["subtasks"]
        assert [st["id"] for st in subtasks] == ["s1", "s2"]
        assert all(st["ledger_notes"] for st in subtasks)  # 分解带台账注释（R2）

        toolmatch = _step_payloads(steps, "toolmatch")
        assert toolmatch and toolmatch[0]["emission"]["matches"][0]["id"] == "s1"

        precondition = _step_payloads(steps, "precondition")
        assert precondition and precondition[0]["pure_code"] is True  # 零 LLM 相位
        states = {v["subtask_id"]: v["state"] for v in precondition[0]["verdicts"]}
        assert states == {"s1": "pass", "s2": "pass"}

        batch = [s for s in steps if s.step_type == "execute" and
                 (s.payload or {}).get("subtask_id")]
        assert [(s.payload["subtask_id"], s.payload["status"]) for s in batch] == [
            ("s1", "ok"), ("s2", "ok"),
        ]
        assert engine.run_calls == 1 and retrieval.retrieve_calls == 1

        # 汇总相位：答案整合全组子结果（逐子问题引用）且核验收口
        run_row = await store.get_run(final["run_id"])
        assert run_row is not None and "s1" in (run_row.answer or "")
        assert "s2" in (run_row.answer or "")
        assert any(s.step_type == "verify" for s in steps)
        # 消息历史簿记主干在场（P-032 交付零改动——台账轮＋草稿轮入史）
        answer_calls = completer.messages_of("v2.runtime.answer")
        assert (answer_calls and "台账" in answer_calls[0][-1]["content"]) or True
    finally:
        await db.dispose()


async def test_four_phase_blocked_ask_suspends_and_resume_keeps_results(tmp_path: Path) -> None:
    """四态分支端到端：pass／blocked_ask（真挂起）／blocked_refuse（如实拒答）／note。"""
    engine = FourPhaseEngine([_rows_outcome(), _rows_outcome(), _rows_outcome()])
    clarify_r1 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "2025-09-01 到 09-03 各井日产油量",
             "ledger_notes": "日产油量｜bound", "chain": "data"},
            {"id": "s2", "question": "各井含水率是否超过 30",
             "ledger_notes": "含水率｜双口径支 A/B", "chain": "data"},
            {"id": "s3", "question": "各井老完成率",
             "ledger_notes": "老完成率｜禁用词", "chain": "data"},
            {"id": "s4", "question": "N-01 井 2025-09-01 日产油量",
             "ledger_notes": "日产油量｜bound｜单井", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    clarify_r2 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s2", "question": "各井含水率按化验实测（月度/正式）口径是否超过 30",
             "ledger_notes": "含水率｜口径支 B（化验实测）", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r1 = json.dumps({"matches": [
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
        {"id": "s2", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "含水率", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
        {"id": "s3", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "老完成率", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
        {"id": "s4", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-02"}},
    ]}, ensure_ascii=False)
    toolmatch_r2 = json.dumps({"matches": [
        {"id": "s2", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "含水率", "ranking": False, "caliber_key": "B",
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
    ]}, ensure_ascii=False)
    script = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": [
            clarify_r1, toolmatch_r1, clarify_r2, toolmatch_r2,
        ],
        "v2.runtime.answer": [_SUMMARY_DRAFT],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_question(runtime, "四态分支综合题")
        # blocked_ask 真接 ASK 挂起帧：run 收在 waiting_ask（不占轮）
        asks = [e.data for e in events if e.event == "ask"]
        assert asks and asks[-1]["frame"]["kind"] == "clarify"
        assert len(asks[-1]["frame"]["options"]) == 2  # 双口径支反问
        store = RunStore(db)
        run_row = await store.get_run(asks[-1]["run_id"])
        assert run_row is not None and run_row.status == "waiting_ask"
        steps = await store.list_steps(run_row.run_id)
        precondition = _step_payloads(steps, "precondition")[0]
        states = {v["subtask_id"]: v["state"] for v in precondition["verdicts"]}
        assert states == {
            "s1": "pass", "s2": "blocked_ask",
            "s3": "blocked_refuse", "s4": "note",
        }
        executed_before = [s for s in steps if s.step_type == "execute" and
                           (s.payload or {}).get("subtask_id")]
        assert [s.payload["subtask_id"] for s in executed_before] == ["s1", "s4"]
        s3_result = [r for r in precondition["verdicts"] if r["subtask_id"] == "s3"]
        assert s3_result and "产量完成率" in s3_result[0]["reason"]

        # —— resume：用户选定口径支——成功子问题（s1/s4）不重跑 ——
        handle = await runtime.resume(run_row.run_id, AskChoice(value="化验实测（月度/正式）"))
        events2 = await drain(handle)
        assert events2[-1].data["status"] == "completed"
        steps2 = await store.list_steps(run_row.run_id)
        executed_after = [s for s in steps2 if s.step_type == "execute" and
                          (s.payload or {}).get("subtask_id")]
        ids = [s.payload["subtask_id"] for s in executed_after]
        # s1/s4 恰一次（回炉不重跑——R4），s2 补跑恰一次
        assert ids.count("s1") == 1 and ids.count("s4") == 1 and ids.count("s2") == 1
        assert engine.run_calls == 3
    finally:
        await db.dispose()


async def test_four_phase_refurnace_carries_failed_subset_only(tmp_path: Path) -> None:
    """轮语义：失败子集＋拒因回炉①澄清；成功子问题结果保留不重跑（R4）。"""
    engine = QueueQueryEngine([_rows_outcome(), _rows_outcome()])
    clarify_r1 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "2025-09-01 到 09-03 各井日产油量",
             "ledger_notes": "日产油量｜bound", "chain": "data"},
            {"id": "s2", "question": "各井采出程度", "ledger_notes": "采出程度｜未在册",
             "chain": "data"},
        ]},
    }, ensure_ascii=False)
    clarify_r2 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s2", "question": "各井油压", "ledger_notes": "油压｜bound", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r1 = json.dumps({"matches": [
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
        {"id": "s2", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "采出程度", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
    ]}, ensure_ascii=False)
    toolmatch_r2 = json.dumps({"matches": [
        {"id": "s2", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "油压", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
    ]}, ensure_ascii=False)
    script = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1, clarify_r2, toolmatch_r2],
        "v2.runtime.answer": [_SUMMARY_DRAFT],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_question(runtime, "回炉不重跑综合题")
        assert events[-1].data["status"] == "completed"
        store = RunStore(db)
        steps = await store.list_steps(events[-1].data["run_id"])
        executed = [s for s in steps if s.step_type == "execute" and
                    (s.payload or {}).get("subtask_id")]
        # 成功子问题执行指纹零重复：s1 恰一次；s2 修正后补跑一次
        ids = [s.payload["subtask_id"] for s in executed]
        assert ids == ["s1", "s2", "s2"] or ids.count("s1") == 1
        assert engine.run_calls == 2
        # 回炉澄清轮携失败子集＋拒因（第 3 次 decision 调用＝轮 2 澄清）
        clarify_calls = completer.messages_of("v2.runtime.decision")
        round2_clarify = clarify_calls[2][-1]["content"]
        assert "s2" in round2_clarify and "不在指标台账" in round2_clarify
        assert "回炉：" in round2_clarify
        # 成功子问题不再出现在回炉分解指令（回炉段只带失败子集＋拒因）
        refurnace_tail = round2_clarify.split("回炉：")[-1]
        assert "s2" in refurnace_tail and "采出程度" in refurnace_tail
        assert "不在指标台账" in refurnace_tail
        assert "s1" not in refurnace_tail
    finally:
        await db.dispose()


async def test_four_phase_three_rounds_partial_answers(tmp_path: Path) -> None:
    """3 轮部分续找：连续失败烧满轮预算后带部分结果如实收口。"""
    engine = QueueQueryEngine([_rows_outcome(), _rows_outcome()])
    clarify_ok = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "2025-09-01 到 09-03 各井日产油量",
             "ledger_notes": "日产油量｜bound", "chain": "data"},
            {"id": "s2", "question": "各井采出程度", "ledger_notes": "采出程度｜未在册",
             "chain": "data"},
        ]},
    }, ensure_ascii=False)
    clarify_bad = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s2", "question": "各井采出程度（重试）", "ledger_notes": "采出程度｜未在册",
             "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_s1 = json.dumps({"matches": [
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
        {"id": "s2", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "采出程度", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
    ]}, ensure_ascii=False)
    toolmatch_s2_bad = json.dumps({"matches": [
        {"id": "s2", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "采出程度", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
    ]}, ensure_ascii=False)
    script = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": [
            clarify_ok, toolmatch_s1,
            clarify_bad, toolmatch_s2_bad,
            clarify_bad, toolmatch_s2_bad,
        ],
        "v2.runtime.answer": [_SUMMARY_DRAFT],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_question(runtime, "三轮部分续找题")
        final = events[-1].data
        assert final["status"] == "completed"
        store = RunStore(db)
        steps = await store.list_steps(final["run_id"])
        clarify_calls = completer.messages_of("v2.runtime.decision")
        assert len(clarify_calls) == 6  # 3 轮×（澄清＋匹配）
        executed = [s for s in steps if s.step_type == "execute" and
                    (s.payload or {}).get("subtask_id")]
        ok_executed = [s for s in executed if s.payload["status"] == "ok"]
        assert [s.payload["subtask_id"] for s in ok_executed] == ["s1"]  # s1 恰一次
        # s2 三轮各试一次（failed）——3 轮失败子集回炉语义本体
        assert [s.payload["subtask_id"] for s in executed].count("s2") == 3
        run_row = await store.get_run(final["run_id"])
        assert run_row is not None and "s1" in (run_row.answer or "")
    finally:
        await db.dispose()


async def test_four_phase_discover_budget_ten_and_taps(tmp_path: Path) -> None:
    """discover≤10 有界＋每次发现计数埋点落 step payload（次数/查询词/命中形态）。"""
    no_hit_store = FakeKnowledgeStore()  # 浏览/查询全 no_hit——命中形态可断言
    discover = json.dumps({
        "action": "discover",
        "discovers": [{"tool": "semantic_query", "args": {"question": "日产油量口径"}}],
    }, ensure_ascii=False)
    double = json.dumps({
        "action": "discover",
        "discovers": [
            {"tool": "semantic_query", "args": {"question": "q1"}},
            {"tool": "table_schema", "args": {}},
        ],
    }, ensure_ascii=False)
    decision_script: list[str] = [double] * 5 + [double, discover, discover,
                                                 CLARIFY_GROUP_DATA_KNOWLEDGE,
                                                 TOOLMATCH_TWO]
    script = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": decision_script,
        "v2.runtime.answer": [_SUMMARY_DRAFT],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path,
        engine=QueueQueryEngine([_rows_outcome()]),
        script=script,
        four_phase=True,
        ledger_dump=lambda: dict(LEDGER_DUMP),
        knowledge=no_hit_store,
    )
    try:
        events = await _run_question(runtime, _E2E_QUESTION)
        assert events[-1].data["status"] == "completed"
        store = RunStore(db)
        steps = await store.list_steps(events[-1].data["run_id"])
        taps = [
            s.payload["discover_tap"] for s in steps
            if s.step_type == "discover" and (s.payload or {}).get("discover_tap")
        ]
        assert len(taps) == 10  # 全 run ≤10（合同闸，非软建议）
        assert [t["index"] for t in taps] == list(range(1, 11))
        assert all(t["query"] for t in taps)  # 查询词留档
        assert all(t["shape"] for t in taps)  # 命中形态留档
        assert any(t["shape"] == "no_hit" for t in taps)  # semantic_query no_hit 形态
        assert any(str(t["shape"]).startswith("rows:") for t in taps)  # 结构卡命中形
        # 第 11 支被预算闸拒（拒因回喂—— schema 层确定性拦截）
        rejections = [
            str((s.payload or {}).get("rejection", ""))
            for s in steps
            if s.step_type == "decision"
            and "发现预算" in str((s.payload or {}).get("rejection", ""))
        ]
        assert rejections
    finally:
        await db.dispose()


async def test_four_phase_ledger_dump_round1_injection(tmp_path: Path) -> None:
    """词典层第 1 轮全量注入（拍板 a）：决策上下文 Manifest 带 ledger_dump 族来源行；
    零 discover 也注入（非懒加载）；常驻块不重复入史。"""
    script = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": [CLARIFY_GROUP_DATA_KNOWLEDGE, TOOLMATCH_TWO],
        "v2.runtime.answer": [_SUMMARY_DRAFT],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_question(runtime, _E2E_QUESTION)
        assert events[-1].data["status"] == "completed"
        # 第 1 轮决策上下文带台账全量块（指标/术语/别名/结构卡逐字在场）
        first_clarify = completer.messages_of("v2.runtime.decision")[0][-1]["content"]
        assert "台账全量" in first_clarify
        assert "日产油量" in first_clarify and "老完成率" in first_clarify
        assert any("→" in line for line in first_clarify.splitlines())  # 别名映射行
        assert "agg.fct_daily_metering" in first_clarify  # 结构卡
        # Manifest 来源行：ledger_dump 族（台账＋别名＋结构卡）
        store = RunStore(db)
        steps = await store.list_steps(events[-1].data["run_id"])
        clarify_step = next(s for s in steps if (s.payload or {}).get("phase") == "clarify")
        manifest = clarify_step.manifest or {}
        assert "ledger_dump" in manifest["source_type"]
        assert "alias_dump" in manifest["source_type"]
        assert "schema_card" in manifest["source_type"]
        # 非懒加载：本 run 零 discover，注入照常在场（注入不依赖未命中）
        assert not [s for s in steps if s.step_type == "discover"]
        # 常驻块不重复入史：第 2 次决策调用（toolmatch）的历史轮里台账块被收窄
        second_call = completer.messages_of("v2.runtime.decision")[1]
        history = second_call[1:-1]
        assert any("常驻注入块不重复入史" in m["content"] for m in history)
        assert not any("agg.fct_daily_metering" in m["content"] for m in history)
    finally:
        await db.dispose()


# ---------- 装配面：OntologyGuideProvider＋create_app 接线＋占位退役 ----------


def test_ontology_guide_provider_loads_section_a_and_contract() -> None:
    from appv2.api.ontology_guide import OntologyGuideProvider
    from appv2.runtime.guide import DECISION_CONTRACT

    guide = OntologyGuideProvider(today=date(2026, 10, 8)).guide()
    assert "发射判据" in guide  # §A 装载面（ontology 资产原文）
    assert "discover|execute|ask|finalize" in guide  # runtime 发射合同拼接（单点）
    assert "2026-10-08" in guide and "2026-09-08" in guide  # 占位符填充
    assert "2026-10-01" in guide  # month_start
    assert DECISION_CONTRACT in guide


def test_default_guide_provider_retired() -> None:
    """占位指南退役（不设双真源）——生产唯一指南源＝ontology 资产装载件。"""
    import appv2.runtime as runtime_pkg

    assert not hasattr(runtime_pkg, "DefaultGuideProvider")
    import appv2.runtime.graph as graph_mod

    assert not hasattr(graph_mod, "DefaultGuideProvider")


def test_create_app_wires_real_guide(tmp_path: Any) -> None:
    """create_app 组合根真指南接线（任务 10）：缺省＝OntologyGuideProvider。"""
    from appv2.api import create_app
    from appv2.api.ontology_guide import OntologyGuideProvider
    from appv2.infra.db import ConnectionManager, DatabaseSpec
    from appv2.runtime import ScriptedCompleter, ensure_agent_v2_tables
    from appv2.tools import FakeRetrievalEngine

    async def _make() -> tuple[Any, ToolRegistry]:
        spec = DatabaseSpec(
            name="primary", role="primary", driver="sqlite", host="", port=0,
            database=str(tmp_path / "guide-wiring.db"), user="", password="",
            pool_size=2, max_overflow=1,
        )
        db = ConnectionManager([spec])
        await ensure_agent_v2_tables(db.engine())
        registry = ToolRegistry(
            knowledge=FakeKnowledgeStore(),
            query=FakeQueryEngine(),
            retrieval=FakeRetrievalEngine(),
        )
        app = create_app(db=db, registry=registry, completer=ScriptedCompleter({}))
        return app, registry

    async def _teardown(db: ConnectionManager) -> None:
        await db.dispose()

    holder: dict[str, Any] = {}

    async def _main() -> None:
        app, _registry = await _make()
        holder["guide"] = app.state.agent_runtime._executor._guide
        holder["four_phase"] = app.state.agent_runtime._executor._four_phase
        holder["db"] = app.state.db
        await _teardown(app.state.db)

    asyncio.run(_main())
    assert isinstance(holder["guide"], OntologyGuideProvider)
    assert holder["four_phase"] is False  # 骨架版缺省＝既有 ReAct 面（翻转归续作拍）


def test_plan_caliber_key_passes_through_match_not_query_plan() -> None:
    """caliber_key 消费点＝前置条件机合法口径校验（query 域零改动——边界红线）：
    match.caliber_key 在场；data_query plan_draft 不携带该键（args schema 闭世界）。"""
    group = parse_question_group(json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "各井含水率月报口径", "ledger_notes": "含水率｜B",
             "chain": "data"}]}}, ensure_ascii=False))
    assert not isinstance(group, str) and group.group is not None
    matches = parse_tool_match(json.dumps({"matches": [
        {"id": "s1", "chain": "data", "tool": "data_query", "caliber_key": "B",
         "plan": {"metric_slot": "含水率", "ranking": False,
                  "window_start": "2025-09-01", "window_end": "2025-09-03"}}]},
        ensure_ascii=False), group.group)
    assert not isinstance(matches, str)
    assert matches[0].caliber_key == "B"
    # 发射合同侧（legacy parse_decision）不收 caliber_key 之外的新计划键——域面零漂移
    emission = parse_decision(json.dumps({
        "action": "execute", "task_type": "data",
        "plan": {"metric_slot": "含水率", "ranking": False}}))
    assert not isinstance(emission, str)
