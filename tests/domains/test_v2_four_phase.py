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

from appv2.infra.clock import freeze
from appv2.infra.security import Actor
from appv2.knowledge import (
    InMemoryKnowledgeStore,
    question_array_snapshot,
)
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
from appv2.runtimev2.context import wire_ledger_projection
from appv2.runtimev2.gateway_adapter import ScriptedCompleter, set_completer
from appv2.runtimev2.orchestration import AgentRuntime, RunExecutor
from appv2.runtimev2.persistence import (
    MemoryTables,
    configure_tables,
)
from appv2.runtimev2.persistence import (
    RunStore as V2RunStore,
)
from appv2.runtimev2.state import AskChoice as V2AskChoice
from appv2.runtimev2.state import AskRequest as V2AskRequest
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

# ---------- runtimev2 编排网（RT-W5-01a：四相位链路＝runtimev2 17 子包） ----------

V2_TODAY = date(2026, 10, 8)
V2_WATERMARK = date(2026, 8, 31)
V2_ACTOR = Actor(user_id="dev-u1", display="开发用户")
V2_UNDERSTAND = json.dumps(
    {"route": "full", "text": "既要数值也要报告佐证。", "metric_candidates": ["日产油量"]},
    ensure_ascii=False,
)


class V2QueueEngine(FakeQueryEngine):
    """剧本化按次出列引擎（末位驻留——多轮剧本）。"""

    def __init__(self, outcomes: Sequence[QueryOutcome]) -> None:
        super().__init__()
        self._queue = list(outcomes)
        self.ledger_metric_slots = {"日产油量", "日产液量", "油压", "含水率", "配产量"}

    def run(self, plan: Any, *, approved_tables: tuple[str, ...] = ()) -> QueryOutcome:
        self.run_calls += 1
        if len(self._queue) > 1:
            return self._queue.pop(0)
        return self._queue[0]


class V2LedgerPort:
    """台账投影端口（`context.wire_ledger_projection` 的注入件）。"""

    def __init__(self, dump: dict[str, Any]) -> None:
        self._dump = dump

    async def fetch(self) -> dict[str, Any]:
        return dict(self._dump)


def v2_ledger_dump() -> dict[str, Any]:
    store = InMemoryKnowledgeStore(question_array_snapshot(), today=V2_TODAY)
    return dict(dump_from_store(store))


def v2_ledger_note(dump: dict[str, Any], keyword: str) -> str:
    """台账注释（**逐字**取自常驻注入块——相位侧在校「是否台账原话」）。"""
    from appv2.runtimev2.prompts import render_ledger_resident_block
    from appv2.runtimev2.state import RunState as V2RunState

    block = render_ledger_resident_block(V2RunState(run_id="probe", ledger_dump=dict(dump)))
    return next(line for line in block.splitlines() if keyword in line)


def v2_registry(
    *,
    engine: Any = None,
    retrieval: Any = None,
    knowledge: Any = None,
) -> ToolRegistry:
    return ToolRegistry(
        knowledge=knowledge if knowledge is not None else FakeKnowledgeStore(),
        query=engine if engine is not None else FakeQueryEngine(),
        retrieval=retrieval if retrieval is not None else FakeRetrievalEngine(),
    )


def v2_runtime(
    *,
    script: dict[str, Sequence[str]],
    registry: ToolRegistry | None = None,
    budget: Any = None,
    watermark: Any = V2_WATERMARK,
    completer: ScriptedCompleter | None = None,
    tables: Any = None,
) -> tuple[Any, ScriptedCompleter]:
    """runtimev2 标准装配：剧本 completer＋内存簿记表＋四相位图（零 DB、零真实端口）。

    `tables` 非空＝复用既有内存表件（跨 run 的追问／恢复面需要同一份表）。
    """
    configure_tables(tables if tables is not None else MemoryTables())
    channel = completer if completer is not None else ScriptedCompleter(script)
    set_completer(channel)
    executor = RunExecutor(
        registry=registry if registry is not None else v2_registry(),
        store=V2RunStore(),
        budget=budget,
        watermark=watermark,
    )
    return AgentRuntime(executor), channel


async def v2_run(runtime: Any, question: str) -> list[Any]:
    handle = await runtime.ask(V2AskRequest(question=question, actor=V2_ACTOR))
    return [event async for event in handle.stream]


async def v2_resume(runtime: Any, run_id: str, choice: Any) -> tuple[list[Any], Any]:
    """恢复受理（runtimev2）：返回（本腿事件流，受理回执）——回执携本腿排他起点 `cursor`。"""
    handle = await runtime.resume(run_id, choice)
    return [event async for event in handle.stream], handle


def v2_ask_frames(events: list[Any]) -> list[dict[str, Any]]:
    """流内 `ask` 帧载荷序列（挂起信号面）。"""
    return [event.data for event in events if event.event == "ask"]


def v2_resume_steps(run_id: str, kind: str) -> list[Any]:
    """恢复留痕步（澄清回收步 payload 携 `resume` 键／执行面恢复守卫步携 `volatile` 键）。"""
    return [
        row
        for row in v2_steps(run_id)
        if isinstance(row.payload, dict) and row.payload.get(kind) is not None
    ]


def v2_steps(run_id: str, phase: str | None = None) -> list[Any]:
    rows = V2RunStore().steps(run_id)
    if phase is None:
        return rows
    return [row for row in rows if (row.payload or {}).get("phase") == phase]


def v2_decision_turn(*, clarify: str, toolmatch: str) -> list[str]:
    """一轮决策剧本（澄清发射 ＋ 匹配发射）。"""
    return [clarify, toolmatch]


def v2_data_match(*, subtask_id: str, slot: str, start: str, end: str) -> dict[str, Any]:
    return {
        "id": subtask_id,
        "chain": "data",
        "tool": "data_query",
        "mention_mode": "executed",
        "plan": {
            "metric_slot": slot,
            "ranking": False,
            "window_start": start,
            "window_end": end,
            "limit": 5,
        },
    }


def v2_knowledge_match(*, subtask_id: str, question: str) -> dict[str, Any]:
    return {
        "id": subtask_id,
        "chain": "knowledge",
        "tool": "doc_retrieve",
        "mention_mode": "executed",
        "retrieval_need": {"question": question},
    }


def v2_decompose(*, subtask_id: str, question: str, ledger_notes: str, chain: str) -> str:
    return json.dumps(
        {
            "action": "decompose",
            "question_group": {
                "subtasks": [
                    {
                        "id": subtask_id,
                        "question": question,
                        "ledger_notes": ledger_notes,
                        "chain": chain,
                    }
                ]
            },
        },
        ensure_ascii=False,
    )


def v2_matches(*items: dict[str, Any]) -> str:
    return json.dumps({"matches": list(items)}, ensure_ascii=False)


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
    """QuestionGroup schema（runtimev2 `parsing` 单点：上限／必填／动作闭世界）。"""
    from appv2.runtimev2.parsing import parse_question_group

    def _parse(text: str) -> Any:
        return parse_question_group(text, max_discovers=2, max_subtasks=MAX_SUBTASKS_CONTRACT)

    emission = _parse(CLARIFY_GROUP_DATA_KNOWLEDGE)
    assert not isinstance(emission, str)
    assert emission.kind == "decompose"
    assert emission.group is not None
    subtasks = emission.group.as_payload()["subtasks"]
    assert [st["id"] for st in subtasks] == ["s1", "s2"]
    assert all(st["ledger_notes"] for st in subtasks)  # 台账注释必带（R2）
    assert subtasks[0]["chain"] == "data"

    # 子问题上限 ≤4（Owner 认可值）
    many = [
        {"id": f"s{i}", "question": "q", "ledger_notes": "n"}
        for i in range(MAX_SUBTASKS_CONTRACT + 1)
    ]
    rejected = _parse(
        json.dumps({"action": "decompose", "question_group": {"subtasks": many}},
                   ensure_ascii=False)
    )
    assert isinstance(rejected, str) and "上限" in rejected

    # 台账注释缺失＝拒（分解缺 ledger_notes 不成组）
    missing = _parse(json.dumps(
        {"action": "decompose", "question_group": {"subtasks": [
            {"id": "s1", "question": "q"}]}}, ensure_ascii=False))
    assert isinstance(missing, str) and "ledger_notes" in missing

    # 非法动作越界
    assert isinstance(_parse('{"action": "fly"}'), str)


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
    """工具匹配与问题组闭世界对账（runtimev2 `parsing` 收口单点：缺／多／未知 id 拒）。"""
    from appv2.runtimev2.parsing import parse_question_group, parse_tool_match

    emission = parse_question_group(
        CLARIFY_GROUP_DATA_KNOWLEDGE, max_discovers=2, max_subtasks=MAX_SUBTASKS_CONTRACT
    )
    assert not isinstance(emission, str) and emission.group is not None
    group = emission.group
    matches = parse_tool_match(TOOLMATCH_TWO, group)
    assert not isinstance(matches, str)
    assert [(m.id, m.chain, m.tool) for m in matches] == [
        ("s1", "data", "data_query"), ("s2", "knowledge", "doc_retrieve"),
    ]

    # 未知 id＝拒（闭合世界）
    stray = parse_tool_match('{"matches": [{"id": "s9", "chain": "data", '
                             '"tool": "data_query", "plan": {"metric_slot": "日产油量", '
                             '"ranking": false}}]}', group)
    assert isinstance(stray, str) and "s9" in stray

    # 覆盖缺口＝拒（组内每个子问题必须有匹配）
    partial = parse_tool_match('{"matches": [{"id": "s1", "chain": "data", '
                               '"tool": "data_query", "plan": {"metric_slot": "日产油量", '
                               '"ranking": false}}]}', group)
    assert isinstance(partial, str) and "s2" in partial

    # data 链缺 plan／plan 缺 metric_slot＝拒（schema 收口）
    no_plan = parse_tool_match('{"matches": ['
                               '{"id": "s1", "chain": "data", "tool": "data_query"}, '
                               '{"id": "s2", "chain": "knowledge", "tool": "doc_retrieve", '
                               '"retrieval_need": {"question": "q"}}]}', group)
    assert isinstance(no_plan, str)

    # chain/tool 不一致＝拒
    wrong_tool = parse_tool_match('{"matches": ['
                                  '{"id": "s1", "chain": "data", "tool": "doc_retrieve", '
                                  '"plan": {"metric_slot": "日产油量", "ranking": false}}, '
                                  '{"id": "s2", "chain": "knowledge", "tool": "doc_retrieve", '
                                  '"retrieval_need": {"question": "q"}}]}', group)
    assert isinstance(wrong_tool, str)


# ---------- 前置条件机单测：三态（B2b 织网②——四态断言退役，钉新不钉旧）＋零 LLM 双证 ----------


def test_precondition_three_states_reachable() -> None:
    """三态版（`eng/04` 盲区 B2b 的织网② 动作——`specs/agent-loop.md:180` 验收行挂此名）。

    旧四态闭世界断言（`SUBTASK_STATES == {pass, blocked_ask, blocked_refuse, note}`）随 Owner
    裁决 §12-B 退役：V2 前置条件机（`appv2.runtimev2.preconditions.gate_all`）是**三态**闭世界
    ——`allow`／`refuse`／`ask`，注记并入放行＝**不设第四态**。V1 闸件
    （`appv2.tools.precondition.judge`）的四位面作为三态的输入照旧在场（工具侧行为零回归，
    其闭世界由 tools 自守）。
    """
    from appv2.runtimev2.preconditions import DECISIONS, gate_all
    from appv2.runtimev2.state import RunState

    window = {"window_start": "2025-09-01", "window_end": "2025-09-03"}
    state = RunState(
        run_id="run-three-state",
        actor="dev-user",
        question="各井日产油量",
        question_group={
            "subtasks": [
                {"id": "s1", "question": "各井日产油量", "chain": "data", "tool": "data_query"},
                {"id": "s2", "question": "各井含水率是否超过 30", "chain": "data",
                 "tool": "data_query"},
                {"id": "s3", "question": "各井老完成率", "chain": "data", "tool": "data_query"},
                {"id": "s4", "question": "N-01 井 2025-09-01 日产油量", "chain": "data",
                 "tool": "data_query"},
            ]
        },
        tool_matches=[
            {"id": "s1", "chain": "data", "tool": "data_query",
             "plan": {"metric_slot": "日产油量", "ranking": False, **window}},
            {"id": "s2", "chain": "data", "tool": "data_query",
             "plan": {"metric_slot": "含水率", "ranking": False, **window}},
            {"id": "s3", "chain": "data", "tool": "data_query",
             "plan": {"metric_slot": "老完成率", "ranking": False, **window}},
            {"id": "s4", "chain": "data", "tool": "data_query",
             "plan": {"metric_slot": "日产油量", "ranking": False, **window}},
        ],
        ledger_dump=LEDGER_DUMP,
    )
    verdicts = {verdict.subtask_id: verdict for verdict in gate_all(state)}

    # 三态各态可达：放行／等用户／拒答
    assert verdicts["s1"].decision == "allow"
    assert verdicts["s2"].decision == "ask"
    assert verdicts["s3"].decision == "refuse"
    # 注记并入放行（单井注记随行照常执行）——**不设第四态**
    assert verdicts["s4"].decision == "allow"
    assert verdicts["s4"].notes and any("单井" in n for n in verdicts["s4"].notes)
    # 三态闭世界（R1 判定面——2026-10-15 Owner 裁决 §12-B）
    assert DECISIONS == frozenset(
        {verdicts["s1"].decision, verdicts["s2"].decision, verdicts["s3"].decision}
    )

    # V1 闸件四位面仍在场（工具侧零回归：三态是它的消费面，不是它的替换）
    facts = ledger_facts(LEDGER_DUMP)
    v_note = judge(SubtaskInput(
        "s4", "N-01 井 2025-09-01 日产油量", "data",
        plan={"metric_slot": "日产油量", "ranking": False,
              "window_start": "2025-09-01", "window_end": "2025-09-02"},
    ), facts)
    assert v_note.state == STATE_NOTE


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


def test_precondition_unknown_slot_refuses_when_ledger_present() -> None:
    """C5（FX-13 闸力恢复，P-033 中途审查）：data 链指标键 ∈ 台账键闭世界
    （slot∪指标名∪别名键——引擎 metric_by_name 两段命中同构）确定性校验
    （零 LLM）——全未命中＝blocked_refuse（不在目录不代答）；名形/别名形发射
    归一到 slot（绑定态/口径闸照常生效——run-c849d5fb 误伤形的修正钉）；
    退化世界（空台账＝注入缺缝）不硬拒全量，引擎台账校验仍权威；knowledge
    链不辖此闸。"""
    facts = ledger_facts(LEDGER_DUMP)
    window = {"window_start": "2025-09-01", "window_end": "2025-09-03"}

    v_refuse = judge(SubtaskInput(
        "f1", "各井采出程度", "data",
        plan={"metric_slot": "采出程度", "ranking": False, **window},
    ), facts)
    assert v_refuse.state == STATE_BLOCKED_REFUSE
    assert "不在台账全量" in v_refuse.reason

    # 名形发射（真模型常见形——台账名带单位）：归一命中，不误伤（C5 闸对
    # 引擎可解析键放行——run-c849d5fb 教训）。
    v_name = judge(SubtaskInput(
        "f2", "各井日产油量", "data",
        plan={"metric_slot": "日产油量（吨）", "ranking": False, **window},
    ), facts)
    assert v_name.state in (STATE_PASS, STATE_NOTE)

    # 别名形发射（别名归一——引擎第二段命中同构）。
    v_alias = judge(SubtaskInput(
        "f3", "各井日产液", "data",
        plan={"metric_slot": "日产液", "ranking": False, **window},
    ), facts)
    assert v_alias.state in (STATE_PASS, STATE_NOTE)

    empty = ledger_facts({})
    v_skip = judge(SubtaskInput(
        "f4", "各井采出程度", "data",
        plan={"metric_slot": "采出程度", "ranking": False, **window},
    ), empty)
    assert v_skip.state == STATE_NOTE  # 引擎台账校验兜底注记（不硬拒全量）

    v_knowledge = judge(SubtaskInput("f5", "W-111 井完井报告", "knowledge"), facts)
    assert v_knowledge.state == STATE_PASS


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


def test_precondition_hit_rule_closed_world() -> None:
    """Verdict.hit_rule（2026-10-16 补（流水 56）裁②——judge() 单点产）：非 allow
    支必携判定位标识（八位闭世界，命名以 specs/preconditions.md 判定序明文表位次
    为准逐字），allow 支（pass／note）＝空串——fail-closed 且对账可检（拒支漏填
    即成空串）；wire 投影（as_payload）随行。"""
    from appv2.tools.precondition import (
        HIT_RULE_ASK,
        HIT_RULE_BAN,
        HIT_RULE_NONE,
        HIT_RULE_UNREGISTERED_METRIC,
        HIT_RULES,
        Verdict,
    )

    assert len(HIT_RULES) == 8 and len(set(HIT_RULES)) == 8
    assert HIT_RULE_NONE not in HIT_RULES

    facts = ledger_facts(LEDGER_DUMP)
    window = {"window_start": "2025-09-01", "window_end": "2025-09-03"}

    # 位 1 禁用词／位 3 外表越集（ask）／位 4 台账闭世界——拒支如实填位
    banned = judge(SubtaskInput(
        "h1", "各井老完成率", "data",
        plan={"metric_slot": "老完成率", "ranking": False, **window},
    ), facts)
    assert banned.state == STATE_BLOCKED_REFUSE
    assert banned.hit_rule == HIT_RULE_BAN

    external = judge(SubtaskInput(
        "h2", "井位台账关联日产油量", "data",
        plan={"metric_slot": "日产油量", "ranking": False,
              "external_tables": ["erp_well_register"]},
    ), facts)
    assert external.state == STATE_BLOCKED_ASK
    assert external.hit_rule == HIT_RULE_ASK

    unknown = judge(SubtaskInput(
        "h3", "各井采出程度", "data",
        plan={"metric_slot": "采出程度", "ranking": False, **window},
    ), facts)
    assert unknown.state == STATE_BLOCKED_REFUSE
    assert unknown.hit_rule == HIT_RULE_UNREGISTERED_METRIC

    # allow 支（pass／note——注记并入放行）＝空串（note 侧结构化信号仍由既有
    # 类型化标记承载：fuzzy_window_rewrite／normalized_slot／chain_switch_trigger）
    allows = [
        judge(SubtaskInput(
            "h4", "各井日产油量", "data",
            plan={"metric_slot": "日产油量", "ranking": False, **window},
        ), facts),
        judge(SubtaskInput(
            "h5", "N-01 井 2025-09-01 日产油量", "data",
            plan={"metric_slot": "日产油量", "ranking": False, **window},
        ), facts),
        judge(SubtaskInput(
            "h6", "最近各井日产油量", "data",
            plan={"metric_slot": "日产油量", "ranking": False, **window},
        ), facts),
        judge(SubtaskInput("h7", "W-111 井完井报告", "knowledge"), facts),
    ]
    assert {v.state for v in allows} <= {STATE_PASS, STATE_NOTE}
    for verdict in allows:
        assert isinstance(verdict, Verdict)
        assert verdict.hit_rule == HIT_RULE_NONE
        assert verdict.as_payload()["hit_rule"] == HIT_RULE_NONE


def test_ctx_of_carries_approved_tables_from_state() -> None:
    """ToolContext 放行态接线（A2 裁决落点——batch/execute 的 ctx 随状态走）。"""
    from appv2.runtime.graph import _ctx_of
    from appv2.runtime.state import RunState

    state = RunState(run_id="run-x", approved_ids=["erp_well_register"])
    ctx = _ctx_of(state)
    assert ctx.approved_tables == ("erp_well_register",)
    # budget＝送窗预算动态化（V2-45 R1a）：无问题组＝按 1 支计→基线 6
    # （旧硬编码 4 由单支基线覆盖——只扩不缩；组尺寸随数扩另钉 R1a 钉测）。
    assert ctx.actor == "" and ctx.budget == 6


def test_precondition_and_parse_layers_are_zero_llm() -> None:
    """R1 双证补强（S4，P-033 中途审查）：直接面 AST（裸名＋属性调用形双查——
    裸名 complete(...) 不再漏检）＋import 闭包递归扫描（「及其传递依赖」锁进
    机器闸——闭包内任何 appv2 文件 import 模型判定通道即红）。

    闭包扫描通道集＝模型判定面（appv2.runtime.llm／appv2.infra.gateway／
    langchain/litellm/openai 供应商 SDK）；appv2.infra.llm_client（B6 embedding
    唯一出口——供应商 SDK 接触的在册单点，其 litellm import 由 B6 纪律＋
    import-linter 合同管辖，非判定面）显式放行不入闭包扫描。
    """
    repo = Path(__file__).resolve().parents[2]
    seeds = {
        Path("appv2/tools/precondition.py"),
        Path("appv2/tools/ledger.py"),
        Path("appv2/runtime/subtask.py"),
    }
    forbidden_calls = {"complete", "ainvoke", "invoke", "agenerate", "generate"}
    forbidden_modules = ("llm", "gateway", "litellm", "openai", "langchain")
    closure_forbidden = (
        "appv2.runtime.llm",
        "appv2.infra.gateway",
        "langchain",
        "litellm",
        "openai",
    )

    def _module_file(module: str) -> Path | None:
        base = repo.joinpath(*module.split("."))
        for candidate in (base.with_suffix(".py"), base / "__init__.py"):
            if candidate.is_file():
                return candidate
        return None

    def _imported(node: ast.AST) -> list[str]:
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        return names

    visited: set[Path] = set()
    queue: list[Path] = [repo / target for target in seeds]
    while queue:
        target = queue.pop()
        if target in visited or not target.is_file():
            continue
        visited.add(target)
        rel = target.relative_to(repo)
        tree = ast.parse(target.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(
                node.func, (ast.Attribute, ast.Name)
            ):
                name = (
                    node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else node.func.id
                )
                if rel in seeds and name in forbidden_calls:
                    raise AssertionError(
                        f"{rel}: 前置条件机直接面出现模型调用形 {name}"
                    )
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for name in _imported(node):
                    if rel in seeds and any(
                        part in name for part in forbidden_modules
                    ):
                        raise AssertionError(f"{rel}: import 了 LLM 通道 {name}")
                    if any(
                        name == channel or name.startswith(channel + ".")
                        for channel in closure_forbidden
                    ):
                        raise AssertionError(
                            f"{rel}: 传递依赖 import 模型判定通道 {name}（R1 闭包闸）"
                        )
                    if name == "appv2" or name.startswith("appv2."):
                        resolved = _module_file(name)
                        if resolved is not None and str(resolved) != str(
                            repo / "appv2/infra/llm_client.py"
                        ):
                            # B6 embedding 唯一出口显式放行（见 docstring 注记）。
                            queue.append(resolved)
    # 扫描器空转防假绿：闭包须真到达传递依赖（三种子之外还有被扫文件）。
    assert len(visited) > len(seeds), f"import 闭包扫描未达传递依赖（扫了 {len(visited)} 文件）"


# ---------- 四相位路由真跑（端到端剧本） ----------


def test_four_phase_routing_topology() -> None:
    """四相位路由拓扑（runtimev2 编排块：四相位真节点入图、回决策边重定向）。"""
    from appv2.runtimev2.orchestration.graph import LoopDeps, build_graph
    from appv2.runtimev2.transport import EventBus

    deps = LoopDeps(bus=EventBus(), registry=v2_registry(), store=V2RunStore())
    graph = build_graph(deps)
    view = graph.get_graph()
    nodes = {str(node) for node in view.nodes}
    expected = {"understand", "clarify", "toolmatch", "precondition", "batch", "answer", "verify"}
    assert expected <= nodes
    edges = {
        (str(getattr(edge, "source", edge[0])), str(getattr(edge, "target", edge[1])))
        for edge in view.edges
    }
    assert ("understand", "clarify") in edges
    assert ("clarify", "toolmatch") in edges
    assert ("toolmatch", "precondition") in edges
    assert ("precondition", "batch") in edges
    assert ("batch", "answer") in edges
    assert ("answer", "verify") in edges


async def test_four_phase_end_to_end_scripted() -> None:
    """四相位端到端剧本（runtimev2 编排：澄清→分解→过闸→批量→汇总→核验→收口）。"""
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    clarify = v2_decompose(
        subtask_id="s1",
        question="2025-09-01 到 09-03 各井日产油量",
        ledger_notes=note,
        chain="data",
    )
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": v2_decision_turn(
            clarify=clarify,
            toolmatch=v2_matches(
                v2_data_match(subtask_id="s1", slot="日产油量",
                              start="2025-09-01", end="2025-09-03")
            ),
        ),
        "answer": ["子任务 s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    engine = V2QueueEngine([_rows_outcome()])
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(script=script, registry=v2_registry(engine=engine))
        events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
        run_id = next(
            event.data["run_id"] for event in reversed(events) if "run_id" in event.data
        )
    # 帧序：收口终形 verdict(final) 在 blackbox 之前（黑匣子＝业务帧意义上的流末帧）
    assert [event.event for event in events][-1] == "blackbox"
    assert [event.event for event in events][-2] == "verdict"
    assert events[-2].data["status"] == "completed"
    assert events[-2].data["subtype"] == "final"
    # 核验裁决形（verify）与收口形（final）同批在场
    verdicts = [event for event in events if event.event == "verdict"]
    assert any(event.data.get("subtype") == "verify" for event in verdicts)

    row = V2RunStore().run(run_id)
    assert row is not None and row.status == "completed"
    assert row.manifest_digest
    assert "21.16" in (row.answer or "")

    clarify_steps = v2_steps(run_id, "clarify")
    assert clarify_steps and "question_group" in (clarify_steps[0].payload or {})["emission"]
    subtasks = clarify_steps[0].payload["emission"]["question_group"]["subtasks"]
    assert [item["id"] for item in subtasks] == ["s1"]
    assert all(item["ledger_notes"] for item in subtasks)

    # 工具匹配产物落状态（相位②返回位经编排投影——下游三块按 `state.tool_matches` 取支）
    state = V2RunStore().load(run_id)
    assert [item["id"] for item in state.tool_matches] == ["s1"]
    assert state.tool_matches[0]["plan"]["metric_slot"] == "日产油量"

    precondition = v2_steps(run_id, "precondition")
    assert precondition and precondition[0].payload["decision"] == "allow"

    executed = [row for row in v2_steps(run_id) if row.step == "execute"]
    assert executed and executed[0].payload["subtask_id"] == "s1"
    assert engine.run_calls == 1
    assert [row.step for row in v2_steps(run_id)].count("verify") == 1


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
    # V2-43：resume 后 s2 口径已答仍触发绑定闸拒（含水率未绑定）——回炉①换链。
    clarify_r3 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s2", "question": "各井含水率按化验实测（月度/正式）口径是否超过 30"
             "（据拒因提示换检索链）",
             "ledger_notes": "文档所载——knowledge 链", "chain": "knowledge",
             "tool": "doc_retrieve"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r3 = json.dumps({"matches": [
        {"id": "s2", "chain": "knowledge", "tool": "doc_retrieve",
         "retrieval_need": {"question": "各井含水率 化验实测 口径"}},
    ]}, ensure_ascii=False)
    script = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": [
            clarify_r1, toolmatch_r1, clarify_r2, toolmatch_r2,
            clarify_r3, toolmatch_r3,
        ],
        "v2.runtime.answer": [_SUMMARY_DRAFT],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script, four_phase=True,
        ledger_dump=lambda: dict(LEDGER_DUMP),
        retrieval=_retrieval_with(_fragment_obs(
            "各井含水率化验实测口径 21.4%（月报所载）。", "frag-hsl-e2e")),
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
        # s1/s4 恰一次（回炉不重跑——R4），s2 补跑恰一次（V2-43：回炉①换
        # knowledge 链——含水率未绑定，data 面零执行）
        assert ids.count("s1") == 1 and ids.count("s4") == 1 and ids.count("s2") == 1
        assert engine.run_calls == 2  # 仅 s1/s4 走 data 引擎；s2 走 doc_retrieve
    finally:
        await db.dispose()


async def test_four_phase_refurnace_carries_failed_subset_only() -> None:
    """行 9｜失败子集回炉（成功子结果不重跑断言）。

    回炉轮①携**失败子集＋拒因**（增量条「回炉：」段只列 failed 子问题），成功子问题结果保留、
    执行指纹零重复（`subtask_results` 簿记面命中即跳过——「不重放已完成部分」）。
    """
    dump = v2_ledger_dump()
    note_oil = v2_ledger_note(dump, "日产油量")
    note_liquid = v2_ledger_note(dump, "日产液量")
    note_pressure = v2_ledger_note(dump, "油压")
    engine = V2QueueEngine([_rows_outcome(), _rows_outcome()])
    # 剧本槽位集不含「日产液量」——引擎校验拒＝failed 回炉面（在册 bound 槽位才可达此面）。
    engine.ledger_metric_slots = {"日产油量", "油压"}
    # 问句指标候选集含三槽（FX-13 候选集闸面照常）：失败面只由脚本槽位集造成。
    understand = json.dumps(
        {"route": "full", "text": "既要数值也要报告佐证。",
         "metric_candidates": ["日产油量", "日产液量", "油压"]},
        ensure_ascii=False,
    )
    script = {
        "understand": [understand],
        "decision": [
            json.dumps(
                {
                    "action": "decompose",
                    "question_group": {
                        "subtasks": [
                            {
                                "id": "s1",
                                "question": "2025-09-01 到 09-03 各井日产油量",
                                "ledger_notes": note_oil,
                                "chain": "data",
                            },
                            {
                                "id": "s2",
                                "question": "各井日产液量",
                                "ledger_notes": note_liquid,
                                "chain": "data",
                            },
                        ]
                    },
                },
                ensure_ascii=False,
            ),
            v2_matches(
                v2_data_match(subtask_id="s1", slot="日产油量",
                              start="2025-09-01", end="2025-09-03"),
                v2_data_match(subtask_id="s2", slot="日产液量",
                              start="2025-09-01", end="2025-09-03"),
            ),
            v2_decompose(
                subtask_id="s2", question="各井油压", ledger_notes=note_pressure, chain="data"
            ),
            v2_matches(
                v2_data_match(subtask_id="s2", slot="油压",
                              start="2025-09-01", end="2025-09-03")
            ),
        ],
        "answer": ["s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]；s2：油压见材料。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(script=script, registry=v2_registry(engine=engine))
        events = await v2_run(runtime, "回炉不重跑综合题")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]

    executed = [row for row in v2_steps(run_id, "execution") if row.payload.get("subtask_id")]
    ids = [row.payload["subtask_id"] for row in executed]
    assert ids.count("s1") == 1 and ids.count("s2") == 2  # 成功子问题恰一次；失败支回炉补跑
    assert engine.run_calls == 2  # s1 首轮出数、s2 修正后出数——引擎恰两次

    # 回炉轮①的增量条：携失败子集的拒因（`decision_error` 回喂条——execution 的闸拒面单点）
    calls = completer.messages_of("decision")
    refurnace = str(calls[2][-1].get("content", ""))
    assert "上次发射被拒" in refurnace and "不在指标台账" in refurnace
    assert "日产液量" in refurnace and "日产油量" not in refurnace  # 只带失败子集
    assert [item["id"] for item in V2RunStore().load(run_id).question_group["subtasks"]] == ["s2"]


async def test_four_phase_refurnace_route_two_tier_bad_args_and_all_refused() -> None:
    """流水 59｜回炉路由两档化：批次含**重跑档**（`bad_args`／`retryable`）支才回炉①；全 `refused`
    批次直落作答收口——终局档不再白烧一轮澄清。

    支一（真 `bad_args` 批次）：轮 1 一支成功、一支引擎台账校验拒（`bad_args`）→ 轮 2 澄清指令携
    回炉条（逐字头「回炉：只分解以下失败/缺失子问题（成功子问题结果已保留，禁止重复分解执行）：」
    ＋逐行「- [id] question——拒因：…」只列失败支），成功子问题不重跑、修正支补跑（引擎恰两次
    调用）。
    支二（全 `refused` 批次）：单支引擎闸拒（`refused`＝终局）→ 零回炉轮（决策相位恰一轮调用）、
    拒因经 answering 缺口面如实交付（`gaps` 条目 `kind="refused"`＋拒因原文，notices 同携拒因）。
    """
    rework_head = "回炉：只分解以下失败/缺失子问题（成功子问题结果已保留，禁止重复分解执行）："

    # —— 支一：真 bad_args 批次 → 回炉轮 2 ——
    dump = v2_ledger_dump()
    note_oil = v2_ledger_note(dump, "日产油量")
    note_liquid = v2_ledger_note(dump, "日产液量")
    note_pressure = v2_ledger_note(dump, "油压")
    engine = V2QueueEngine([_rows_outcome(), _rows_outcome()])
    # 剧本槽位集不含「日产液量」——引擎台账校验拒＝bad_args 档（在册 bound 槽位才可达此面）。
    engine.ledger_metric_slots = {"日产油量", "油压"}
    understand = json.dumps(
        {"route": "full", "text": "既要数值也要报告佐证。",
         "metric_candidates": ["日产油量", "日产液量", "油压"]},
        ensure_ascii=False,
    )
    script = {
        "understand": [understand],
        "decision": [
            json.dumps(
                {
                    "action": "decompose",
                    "question_group": {
                        "subtasks": [
                            {
                                "id": "s1",
                                "question": "2025-09-01 到 09-03 各井日产油量",
                                "ledger_notes": note_oil,
                                "chain": "data",
                            },
                            {
                                "id": "s2",
                                "question": "各井日产液量",
                                "ledger_notes": note_liquid,
                                "chain": "data",
                            },
                        ]
                    },
                },
                ensure_ascii=False,
            ),
            v2_matches(
                v2_data_match(subtask_id="s1", slot="日产油量",
                              start="2025-09-01", end="2025-09-03"),
                v2_data_match(subtask_id="s2", slot="日产液量",
                              start="2025-09-01", end="2025-09-03"),
            ),
            v2_decompose(
                subtask_id="s2", question="各井油压", ledger_notes=note_pressure, chain="data"
            ),
            v2_matches(
                v2_data_match(subtask_id="s2", slot="油压",
                              start="2025-09-01", end="2025-09-03")
            ),
        ],
        "answer": ["s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]；s2：油压见材料。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(script=script, registry=v2_registry(engine=engine))
        events = await v2_run(runtime, "回炉路由两档化综合题")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]

    decisions = completer.messages_of("decision")
    assert len(decisions) == 4  # 轮 1（澄清＋匹配）＋轮 2（回炉澄清＋匹配）
    round2 = str(decisions[2][-1].get("content", ""))
    assert rework_head in round2
    assert "- [s2] 各井日产液量——拒因：" in round2 and "不在指标台账" in round2
    assert "- [s1]" not in round2  # 成功支不进回炉条
    assert engine.run_calls == 2  # s1 首轮出数 ＋ s2 修正后出数（轮 1 的 s2 校验拒＝引擎零调用）
    assert V2RunStore().load(run_id).rounds == 2
    assert len(v2_steps(run_id, "clarify")) == 2

    # —— 支二：全 refused 批次 → 零回炉轮（路由 answering，一轮收）——
    dump_refused = v2_ledger_dump()
    note_refused = v2_ledger_note(dump_refused, "日产油量")
    refused_reason = "口径/数据闸拒：所问口径无据——不代答"
    engine_refused = V2QueueEngine([QueryOutcome.refuse(reason=refused_reason)])
    understand_refused = json.dumps(
        {"route": "full", "text": "所问口径无据。", "metric_candidates": ["日产油量"]},
        ensure_ascii=False,
    )
    script_refused = {
        "understand": [understand_refused],
        "decision": [
            json.dumps(
                {
                    "action": "decompose",
                    "question_group": {
                        "subtasks": [
                            {
                                "id": "s1",
                                "question": "2025-09-01 到 09-03 各井日产油量",
                                "ledger_notes": note_refused,
                                "chain": "data",
                            }
                        ]
                    },
                },
                ensure_ascii=False,
            ),
            v2_matches(
                v2_data_match(subtask_id="s1", slot="日产油量",
                              start="2025-09-01", end="2025-09-03")
            ),
        ],
        "answer": ["所问井日产油量的取数被闸拒，拒因见缺口面——不代答。"],
    }
    wire_ledger_projection(V2LedgerPort(dump_refused))
    with freeze("2026-10-08T09:00:00"):
        runtime_refused, completer_refused = v2_runtime(
            script=script_refused, registry=v2_registry(engine=engine_refused)
        )
        events_refused = await v2_run(runtime_refused, "全拒批次题")
    assert events_refused[-1].event == "blackbox"
    assert events_refused[-1].data["status"] == "completed"
    run_id_refused = events_refused[-1].data["run_id"]

    decisions_refused = completer_refused.messages_of("decision")
    assert len(decisions_refused) == 2  # 恰一轮决策（澄清＋匹配）——零回炉轮
    assert all(
        rework_head not in str(call[-1].get("content", "")) for call in decisions_refused
    )
    assert V2RunStore().load(run_id_refused).rounds == 1
    assert len(v2_steps(run_id_refused, "clarify")) == 1
    assert engine_refused.run_calls == 1  # 支已派遣（拒＝引擎侧闸拒，非零调用）
    drafts = [
        row.payload or {}
        for row in v2_steps(run_id_refused)
        if row.step == "answer" and (row.payload or {}).get("phase") == "draft"
    ]
    refused_gaps = [
        gap for gap in (drafts[0].get("gaps") or []) if gap.get("kind") == "refused"
    ]
    assert refused_gaps and refused_reason in str(refused_gaps[0].get("reason"))
    notices = [event.data for event in events_refused if event.event == "notice"]
    assert any(refused_reason in str(item.get("content", "")) for item in notices)


async def test_four_phase_three_rounds_partial_answers() -> None:
    """行 10｜3 轮部分续找语义（轮 1 部分答案→轮 2/3 带失败子集）。

    轮预算（`state.budget` 轮数键）用尽即收口：连续失败支在轮 2／3 只带失败子集＋拒因回炉，
    成功子问题结果保留不重跑；到顶以**已取得材料＋未完成项**如实交付（触界不静默）。
    """
    dump = v2_ledger_dump()
    note_oil = v2_ledger_note(dump, "日产油量")
    note_liquid = v2_ledger_note(dump, "日产液量")
    engine = V2QueueEngine([_rows_outcome()])
    engine.ledger_metric_slots = {"日产油量"}  # 日产液量恒不在槽位集——三轮恒 failed

    def decompose_liquid(marker: str) -> str:
        return json.dumps(
            {
                "action": "decompose",
                "question_group": {
                    "subtasks": [
                        {
                            "id": "s2",
                            "question": f"各井日产液量{marker}",
                            "ledger_notes": note_liquid,
                            "chain": "data",
                        }
                    ]
                },
            },
            ensure_ascii=False,
        )

    def match_liquid(day: str) -> str:
        return v2_matches(
            v2_data_match(subtask_id="s2", slot="日产液量", start="2025-09-01", end=day)
        )

    understand = json.dumps(
        {"route": "full", "text": "既要数值也要报告佐证。",
         "metric_candidates": ["日产油量", "日产液量"]},
        ensure_ascii=False,
    )
    script = {
        "understand": [understand],
        "decision": [
            json.dumps(
                {
                    "action": "decompose",
                    "question_group": {
                        "subtasks": [
                            {
                                "id": "s1",
                                "question": "2025-09-01 到 09-03 各井日产油量",
                                "ledger_notes": note_oil,
                                "chain": "data",
                            },
                            {
                                "id": "s2",
                                "question": "各井日产液量",
                                "ledger_notes": note_liquid,
                                "chain": "data",
                            },
                        ]
                    },
                },
                ensure_ascii=False,
            ),
            v2_matches(
                v2_data_match(subtask_id="s1", slot="日产油量",
                              start="2025-09-01", end="2025-09-03"),
                v2_data_match(subtask_id="s2", slot="日产液量",
                              start="2025-09-01", end="2025-09-03"),
            ),
            decompose_liquid("（轮 2 重试）"),
            match_liquid("2025-09-04"),
            decompose_liquid("（轮 3 重试）"),
            match_liquid("2025-09-05"),
        ],
        "answer": ["s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(script=script, registry=v2_registry(engine=engine))
        events = await v2_run(runtime, "三轮部分续找题")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]

    state = V2RunStore().load(run_id)
    assert int(state.rounds) == int(state.budget.rounds) == 3  # 轮预算用尽（三轮各占一轮）
    assert int(state.discover_used) == 0
    executed = [row for row in v2_steps(run_id, "execution") if row.payload.get("subtask_id")]
    attempt_ids = [row.payload["subtask_id"] for row in executed]
    assert attempt_ids.count("s1") == 1  # 成功子问题零重复执行
    assert attempt_ids.count("s2") == 3  # 失败支三轮各试一次
    assert engine.run_calls == 1  # 只有 s1 真出数（s2 三投皆配置拒）

    # 轮 2／3 的增量条都只带失败子集的拒因（连续拒因回喂——轮 1 部分答案语义本体）
    calls = completer.messages_of("decision")
    for call in (calls[2], calls[4]):
        text = str(call[-1].get("content", ""))
        assert "上次发射被拒" in text and "不在指标台账" in text
        assert "日产液量" in text and "日产油量" not in text
    assert [item["id"] for item in V2RunStore().load(run_id).question_group["subtasks"]] == ["s2"]
    assert "21.16" in (V2RunStore().run(run_id).answer or "")


async def test_four_phase_discover_budget_ten_and_taps() -> None:
    """行 11｜discover 全 run ≤10＋计数埋点落 payload。

    钻取预算＝硬闸（数值只引 `state.budget` 全 run 发现键）：超预算的发射被确定性拦截（不是
    「模型自律」），且每次钻取落 step payload 计数埋点（工具／查询词指纹／命中数／命中形态）
    供跑批分析。
    """
    doubles = [
        json.dumps(
            {
                "action": "discover",
                "discovers": [
                    {"tool": "semantic_query", "args": {"question": f"q{i}"}},
                    {"tool": "table_schema", "args": {}},
                ],
            },
            ensure_ascii=False,
        )
        for i in range(1, 6)
    ]
    overflow = json.dumps(
        {
            "action": "discover",
            "discovers": [{"tool": "semantic_query", "args": {"question": "超预算支"}}],
        },
        ensure_ascii=False,
    )
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            *doubles,
            overflow,  # 第 11 支：预算闸确定性拦截（拒因回喂）
            v2_decompose(
                subtask_id="s1",
                question="2025-09-01 到 09-03 各井日产油量",
                ledger_notes=note,
                chain="data",
            ),
            v2_matches(
                v2_data_match(
                    subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03"
                )
            ),
        ],
        "answer": ["s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    engine = V2QueueEngine([_rows_outcome()])
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(script=script, registry=v2_registry(engine=engine))
        events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]

    state = V2RunStore().load(run_id)
    cap = int(state.budget.discovers_per_run)
    taps = [row for row in v2_steps(run_id) if row.step == "discover"]
    assert len(taps) == cap == 10  # 全 run ≤10（合同闸，非软建议）
    assert int(state.discover_used) == cap
    # 计数埋点落 payload：查询词指纹／命中数／命中形态（`status`／`reject_reason` 同理可查）
    assert all(str(row.payload.get("args_fingerprint") or "") for row in taps)
    assert all(isinstance(row.payload.get("row_count"), int) for row in taps)
    assert all(str(row.payload.get("status") or "") in {"ok", "failed", "ask"} for row in taps)
    assert max(int(row.payload["row_count"]) for row in taps) > 0  # 结构卡命中（rows:N 形）
    assert state.empty_probes  # 空手探查指纹（no_hit 形——no_hit 循环回归判定面）
    assert len(state.empty_probes) == len(taps) // 2  # 半数为语义探查（逐支 question 各异）
    no_hit_fingerprints = {
        json.dumps(row.payload["args"], ensure_ascii=False, sort_keys=True) for row in taps
        if row.payload["tool"] == "semantic_query"
    }
    assert no_hit_fingerprints  # 空手支的查询词如实留档
    # 越预算发射被拦（拒因回喂面在场），run 照常续推（拦截不炸链）
    rejections = [
        str(row.payload.get("rejection") or "")
        for row in v2_steps(run_id, "clarify")
    ]
    assert any("发现预算" in reason for reason in rejections)


async def test_four_phase_ledger_dump_round1_injection() -> None:
    """词典层第 1 轮全量注入（拍板 a）：澄清／匹配相位包携台账全量块；
    零 discover 也注入（非懒加载）；常驻块不重复入史；决策调用面互为前缀延伸（pin-22）。"""
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": v2_decision_turn(
            clarify=v2_decompose(
                subtask_id="s1",
                question="2025-09-01 到 09-03 各井日产油量",
                ledger_notes=note,
                chain="data",
            ),
            toolmatch=v2_matches(
                v2_data_match(subtask_id="s1", slot="日产油量",
                              start="2025-09-01", end="2025-09-03")
            ),
        ),
        "answer": ["s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(
            script=script, registry=v2_registry(engine=V2QueueEngine([_rows_outcome()]))
        )
        events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"

    first_call = completer.messages_of("decision")[0]
    package = next(
        message["content"]
        for message in first_call
        if message.get("role") == "user" and "台账全量" in str(message.get("content", ""))
    )
    assert "日产油量" in package and "老完成率" in package  # 指标台账逐字在场
    assert "agg.fct_daily_metering" in package  # 结构卡
    assert any("→" in line for line in package.splitlines())  # 别名映射行

    # 追加式链（pin-22）：第 2 次决策调用＝第 1 次的**前缀延长**
    second_call = completer.messages_of("decision")[1]
    assert second_call[: len(first_call)] == first_call
    # 相位包一次性（pin-24）：台账全量恰两次（澄清包＋匹配包各一次，无逐轮重复）
    assert sum("台账全量" in message.get("content", "") for message in second_call) == 2
    # 非懒加载：本 run 零 discover，注入照常在场
    run_id = events[-1].data["run_id"]
    assert not [row for row in v2_steps(run_id) if row.step == "discover"]


# ---------- S5 审批恢复全链钉（B1 修复面——两链全通：clarify 面＋legacy 面） ----------


async def test_four_phase_extable_approval_resume_precondition_chain() -> None:
    """行 14｜越集审批挂起→批准→前置条件机重判→批量执行（钉 `pin-29` 闭环面·审批形态）。

    两处形状面（-01b 承载）：① ask 帧 `detail` 承载位＝`precond-{subtask_id}` ＋
    `plan.external_tables`（外集表名集随帧）；② 批准落 `approved_ids`（放行名单面）＋
    `extable_rounds` 计点，回前置条件机**重判**（同一条链续推，不重起第二套形状）。
    """
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    clarify = v2_decompose(
        subtask_id="s1",
        question="井位台账关联的日产油量",
        ledger_notes=note,
        chain="data",
    )
    match = v2_data_match(
        subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03"
    )
    match["plan"]["external_tables"] = ["erp_well_register"]
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [clarify, v2_matches(match)],
        "answer": ["s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    engine = V2QueueEngine([_rows_outcome()])
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(script=script, registry=v2_registry(engine=engine))
        events = await v2_run(runtime, "外表越集审批恢复题")
        asks = v2_ask_frames(events)
        assert asks and asks[-1]["frame"]["kind"] == "external_table_approval"
        frame = asks[-1]["frame"]
        assert frame["detail"]["approval_id"] == "precond-s1"  # 承载位：precond-{subtask_id}
        assert frame["detail"]["tables"] == ["erp_well_register"]  # plan.external_tables 原样取
        run_id = asks[-1]["run_id"]
        assert V2RunStore().run(run_id).status == "waiting_ask"
        assert engine.run_calls == 0  # 未批准＝不执行（不静默放行）

        # 批准 → 前置条件机重判（放行态进 ToolContext）→ 批量续跑。
        resumed, _handle = await v2_resume(
            runtime,
            run_id,
            V2AskChoice(
                kind="external_table_approval",
                decision="approve",
                approval_id=frame["detail"]["approval_id"],
            ),
        )
    assert resumed[-1].event == "blackbox" and resumed[-1].data["status"] == "completed"
    assert not v2_ask_frames(resumed)  # 批准后不再挂起（放行名单生效）

    state = V2RunStore().load(run_id)
    assert "erp_well_register" in state.approved_ids  # 批准落放行名单
    assert state.extable_rounds == 1  # 外表审批轮计点
    assert state.approved_ids == [frame["detail"]["approval_id"], "erp_well_register"]
    preconditions = v2_steps(run_id, "precondition")
    assert len(preconditions) == 2  # 挂起前 ask ＋ 批准后重判
    assert preconditions[0].payload["decision"] == "ask"
    assert preconditions[-1].payload["decision"] == "allow"
    executed = [row for row in v2_steps(run_id, "execution") if row.payload.get("subtask_id")]
    assert [row.payload["subtask_id"] for row in executed] == ["s1"]  # 恰执行一次
    assert engine.run_calls == 1
    assert "21.16" in (V2RunStore().run(run_id).answer or "")


async def test_four_phase_engine_ask_resume_batch_chain() -> None:
    """行 15｜引擎侧 ask 挂起→resume→批量续跑收口（钉 `pin-29` 闭环面·工具侧审批帧）。

    引擎帧（`data_query` 越集审批 outcome）同走**挂起—恢复链**：挂起帧 kind 与前置条件机
    形态同族 → 入口回**前置条件机重判** → 批量续跑（首投挂起未出数、批准后恰补跑一次）。
    """
    ask_outcome = QueryOutcome.external_table_approval(
        tables=("erp_well_register",),
        ask={
            "approval_id": "APP-1008-erp_well_register",
            "reason": "外表越集审批",
            "impact": "批准后该表进放行名单",
            "audit_hint": "外表 erp_well_register",
        },
    )
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            v2_decompose(
                subtask_id="s1",
                question="2025-09-01 到 09-03 各井日产油量",
                ledger_notes=note,
                chain="data",
            ),
            v2_matches(
                v2_data_match(
                    subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03"
                )
            ),
        ],
        "answer": ["s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    engine = V2QueueEngine([ask_outcome, _rows_outcome()])
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(script=script, registry=v2_registry(engine=engine))
        events = await v2_run(runtime, "引擎侧审批恢复题")
        asks = v2_ask_frames(events)
        assert asks and asks[-1]["frame"]["kind"] == "external_table_approval"
        frame = asks[-1]["frame"]
        assert frame["detail"]["approval_id"] == "APP-1008-erp_well_register"  # 引擎卡素材透传
        assert frame["detail"]["tables"] == ["erp_well_register"]  # 表名集随卡（放行名单回填面）
        run_id = asks[-1]["run_id"]
        assert V2RunStore().run(run_id).status == "waiting_ask"
        assert engine.run_calls == 1  # 首投挂起（引擎未出数）

        resumed, _handle = await v2_resume(
            runtime,
            run_id,
            V2AskChoice(
                kind="external_table_approval",
                decision="approve",
                approval_id=frame["detail"]["approval_id"],
            ),
        )
    assert resumed[-1].event == "blackbox" and resumed[-1].data["status"] == "completed"
    assert engine.run_calls == 2  # 批准后恰补跑一次

    state = V2RunStore().load(run_id)
    assert state.approved_ids == ["APP-1008-erp_well_register", "erp_well_register"]
    assert state.extable_rounds == 1
    assert len(v2_steps(run_id, "precondition")) == 2  # 批准→重判路由真走通
    executed = [row for row in v2_steps(run_id, "execution") if row.payload.get("subtask_id")]
    assert [row.payload["status"] for row in executed] == ["ask", "ok"]  # 首挂起＋续跑
    assert v2_resume_steps(run_id, "volatile")  # 恢复守卫：重取易变环境量（执行面四项）
    assert "21.16" in (V2RunStore().run(run_id).answer or "")


# ---------- P-033c 降2 收窄：CLARIFY_CONTRACT 反问收窄（窗可锚定＝禁 ask） ----------


def test_clarify_contract_narrows_ask_to_threshold_and_true_ambiguity() -> None:
    """P-033c 降2 修复（真回退——合同面措辞钉）：CLARIFY_CONTRACT 反问收窄。

    P033BW1 数-降2 根因（P-033b 停报闸裁决）：发射判据只有「禁再 discover」
    面，无「禁不必要 ask」对称面——模型在台账命中＋窗可锚定下仍反问窗/粒度。
    收窄：ask 仅限阈值判断形/真歧义两种白场；窗可锚定（拍板⑥：无时间词→
    默认近 30 天/窗词锚定表）＝禁 ask。合同文本＝runtime 单点真源（guide.py）。"""
    from appv2.runtime import CLARIFY_CONTRACT

    assert "禁再 discover" in CLARIFY_CONTRACT  # 原对称面原样在（零漂移）
    assert "窗可锚定＝禁 ask" in CLARIFY_CONTRACT  # 新增对称面（本拍收窄）
    assert "阈值判断形" in CLARIFY_CONTRACT  # ask 白场一：无场景词阈值判断形
    assert "真歧义" in CLARIFY_CONTRACT  # ask 白场二：目标/对象/口径真歧义
    assert "默认近 30 天" in CLARIFY_CONTRACT  # 拍板⑥默认窗（无时间词）


async def test_four_phase_anchorable_window_skips_ask_delivers_degrade() -> None:
    """窗可锚定＝禁 ask：带明确窗的题全链零 ask 帧零挂起；换链回炉闸
    （在册未绑定 agg）携拒因回炉①澄清相位，轮 2 换 knowledge 链真执行、如实交付。"""
    dump = v2_ledger_dump()
    bound_note = v2_ledger_note(dump, "配产量")
    knowledge_note = v2_ledger_note(dump, "老完成率")
    clarify = v2_decompose(
        subtask_id="s1",
        question="去年各井配产量",
        ledger_notes=bound_note,
        chain="data",
    )
    toolmatch = v2_matches(
        v2_data_match(subtask_id="s1", slot="配产量",
                      start="2025-01-01", end="2026-01-01")
    )
    clarify_r2 = v2_decompose(
        subtask_id="s1",
        question="去年各井配产量（据拒因提示换检索链）",
        ledger_notes=knowledge_note,
        chain="knowledge",
    )
    toolmatch_r2 = v2_matches(
        v2_knowledge_match(subtask_id="s1", question="去年各井配产量")
    )
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [clarify, toolmatch, clarify_r2, toolmatch_r2],
        "answer": ["去年各井配产量：月度配产合计 21.4 万方 [1]（按文档所载交付）。"],
    }
    retrieval = _retrieval_with(_fragment_obs(
        "配产量按月度计划分解下达：各井合计月度配产 21.4 万方（月报所载）。",
        "frag-peichan-1",
    ))
    wire_ledger_projection(V2LedgerPort(dump))
    engine = V2QueueEngine([])
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(
            script=script, registry=v2_registry(engine=engine, retrieval=retrieval)
        )
        events = await v2_run(runtime, "去年各井配产量是多少？")

    assert events[-1].event == "blackbox"
    assert events[-1].data["status"] == "completed"  # 窗可锚定零 ask——不挂起直收口
    assert not [event for event in events if event.event == "ask"]  # 全链零 ask 帧

    first_decision = "\n".join(
        message.get("content", "") for message in completer.messages_of("decision")[0]
    )
    assert "窗可锚定＝禁 ask" in first_decision  # 收窄合同随相位包在场（非死文本）

    run_id = events[-1].data["run_id"]
    preconditions = v2_steps(run_id, "precondition")
    assert preconditions[0].payload["chain_switch_reentry"] is True  # 换链回炉首次触发
    assert preconditions[0].payload["decision"] == "allow"
    assert preconditions[1].payload["decision"] == "allow"  # 换 knowledge 链放行
    assert engine.run_calls == 0  # data 引擎零执行
    assert retrieval.retrieve_calls == 1
    notices = [event.data for event in events if event.event == "notice"]
    assert any(item.get("type") == "chain_switch_reentry" for item in notices)
    assert not any(item.get("type") == "unbound_degrade" for item in notices)

    # 相位合同一次性（钉 `pin-24`）：回炉轮不重发合同包——标记记一次、链上台账全量块仍恰两块
    # （澄清包 ＋ 匹配包），不随轮数增长。
    state = V2RunStore().load(run_id)
    assert state.contracts_appended.count("clarify") == 1
    assert state.contracts_appended.count("toolmatch") == 1
    last_call = completer.messages_of("decision")[-1]
    assert sum("台账全量" in message.get("content", "") for message in last_call) == 2


async def test_four_phase_clarify_ask_threshold_form_still_suspends_and_resumes() -> None:
    """行 8｜阈值判断形口径反问仍挂起→resume 回喂→续跑收口（钉 `pin-29` 闭环面·clarify 形态）。

    收窄（行 7）只禁窗可锚定下的不必要反问，不禁阈值判断形／真歧义两白场：`ask` 支照发射→run
    置 `waiting_ask` 挂起（挂起帧投影＝GET 读面 `pending_ask`，与流内 `ask` 帧同形）→`resume`
    带 kind 判别字段回喂（`resume_choices` 留痕、用户原话进对话链、**恢复时重取易变环境量**读数
    落步 payload）→**同链续推**到收口（链前缀延伸、跨腿 `seq` 不重启）。
    """
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    ask_first = json.dumps(
        {
            "action": "ask",
            "ask": {
                "prompt": "「日产油量」按哪一口径支判断阈值？",
                "options": ["A 月报口径", "B 化验实测"],
            },
        },
        ensure_ascii=False,
    )
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            ask_first,
            v2_decompose(
                subtask_id="s1",
                question="2025-09-01 到 09-03 各井日产油量",
                ledger_notes=note,
                chain="data",
            ),
            v2_matches(
                v2_data_match(
                    subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03"
                )
            ),
        ],
        "answer": ["答案：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    engine = V2QueueEngine([_rows_outcome()])
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(script=script, registry=v2_registry(engine=engine))
        events = await v2_run(runtime, "各井日产油量是否超过 30 吨？")
        asks = v2_ask_frames(events)
        assert asks and asks[-1]["frame"]["kind"] == "clarify"  # 真挂起帧
        assert asks[-1]["frame"]["options"] == ["A 月报口径", "B 化验实测"]
        # 挂起收束：本腿以收口帧 verdict(status=waiting_ask) 止（`ask` 帧之后的行为归 api 开流段
        # ——挂起铁律「ask 帧之后照发 done」，`specs/transport.md` 行为 8）
        assert events[-1].event == "verdict" and events[-1].data["status"] == "waiting_ask"
        assert not [event for event in events if event.event == "blackbox"]
        run_id = asks[-1]["run_id"]
        row = V2RunStore().run(run_id)
        assert row is not None and row.status == "waiting_ask"
        suspended = V2RunStore().load(run_id)
        assert suspended.pending_ask == asks[-1]["frame"]  # 挂起帧投影（GET 读面）
        chain_before = list(suspended.messages)

        # resume：用户选定口径支→回喂→（同链）续推到收口。
        resumed, handle = await v2_resume(
            runtime, run_id, V2AskChoice(kind="clarify", choice="B 化验实测")
        )
    assert resumed[-1].event == "blackbox" and resumed[-1].data["status"] == "completed"
    assert V2RunStore().run(run_id).status == "completed"
    assert "21.16" in (V2RunStore().run(run_id).answer or "")

    # 恢复选择留痕（`resume_choices` 四键投影）＋挂起帧已消费（不再挂起）
    state = V2RunStore().load(run_id)
    assert state.resume_choices[-1] == {
        "kind": "clarify",
        "choice": "B 化验实测",
        "decision": None,
        "approval_id": None,
    }
    assert state.pending_ask is None

    # 恢复时重取易变环境量（行为 13）：读数落步 payload（四项台账面读数＋用户原话），可机检
    resumption = v2_resume_steps(run_id, "resume")
    assert resumption and resumption[-1].payload["resume"] == "B 化验实测"
    readings = resumption[-1].payload["volatile"]
    assert set(readings) == {"watermark", "freshness", "foundation", "new_rows"}

    # 用户原话进链（对话层来源闭世界 `clarify_approval_replay`）＋链前缀延伸（pin-22 跨腿同链）
    assert [entry["origin"] for entry in state.dialogue] == ["clarify_approval_replay"]
    assert state.messages[: len(chain_before)] == chain_before
    assert any(
        message.get("role") == "user" and message.get("content") == "B 化验实测"
        for message in state.messages[len(chain_before) :]
    )
    calls = completer.messages_of("decision")
    assert calls[1][: len(calls[0])] == calls[0]  # 恢复腿首次决策调用＝首腿链的前缀延长

    # 跨腿续编（`specs/transport.md` 行为 3「跨段不重启」）：游标＝上一腿收口帧之后，本腿帧不重启
    leg1_last = events[-1].seq
    assert handle.cursor == leg1_last + 1  # 受理回执 cursor＝本腿下一帧 seq（排他起点）
    assert all(event.seq >= handle.cursor for event in resumed)
    assert engine.run_calls == 1


# ---------- S2 落闸：clarify 预算拒例外不再开无界自旋洞 ----------


async def test_four_phase_clarify_budget_reject_spin_gate() -> None:
    """行 12｜预算拒免轮例外只留首次（连续第 2 次转占轮）。

    预算驱动的发射拒（发现预算已尽）享有「首拒免轮」例外；在顽投模型下该例外**不得**变成零代价
    自环——连续第 2 次起转占轮，由**轮数闸**确定性收敛（触界必带如实注记，不静默截断）；发现
    预算 ≤10 本体不被绕过。
    """
    discover = json.dumps(
        {
            "action": "discover",
            "discovers": [
                {"tool": "semantic_query", "args": {"question": "日产油量口径"}},
            ],
        },
        ensure_ascii=False,
    )
    # 逐支 question 各异（同参空手重发由发射级拒另管）——本钉只测预算拒的轮语义。
    doubles = [
        json.dumps(
            {
                "action": "discover",
                "discovers": [
                    {"tool": "semantic_query", "args": {"question": f"q{i}"}},
                    {"tool": "table_schema", "args": {}},
                ],
            },
            ensure_ascii=False,
        )
        for i in range(1, 6)
    ]
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [*doubles, discover],  # 末位驻留＝顽投 discover（预算已尽，逢发必拒）
        "answer": ["（预算触界前无草稿——本用例只测收敛面）"],
    }
    wire_ledger_projection(V2LedgerPort(v2_ledger_dump()))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(
            script=script, registry=v2_registry(engine=V2QueueEngine([_rows_outcome()]))
        )
        events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]

    state = V2RunStore().load(run_id)
    cap = int(state.budget.discovers_per_run)
    taps = [row for row in v2_steps(run_id) if row.step == "discover"]
    assert len(taps) == cap  # 发现预算 ≤10 本体不被绕过
    assert int(state.discover_used) == cap

    # 轮语义：首拒免轮（轮号不进）、其后逐拒占轮——轮号序列＝[0, 1, 2, 3]
    rejections = [
        row.title for row in v2_steps(run_id, "clarify") if "被拒" in row.title
    ]
    rounds_used = [int(title.split("澄清 r")[1].split(" ")[0]) for title in rejections]
    assert rounds_used == list(range(len(rejections)))
    assert rounds_used[0] == 0  # 首拒免轮（`rounds` 不动）
    # 决策调用有界：5 支双发 ＋ 首拒免轮 ＋ 其后逐拒耗轮至入口收敛（收敛那一次不发模型）
    assert completer.counts()["decision"] == len(doubles) + 1 + int(state.budget.rounds)
    assert int(state.rounds) == int(state.budget.rounds)  # 轮数闸到顶即收敛

    converged = [notice for notice in state.notices if notice.get("type") == "budget_converged"]
    assert converged and "rounds" in converged[0]["gates"]  # 轮数闸收敛（非时长闸）
    assert "未完成项" in converged[0]["content"]  # 触界不静默（未完成项明示）
    assert state.budget_hit  # 机读信号面（`budget_hit` 与注记同现）


async def test_make_runtime_guide_contract_follows_four_phase(tmp_path: Path) -> None:
    """C6（P-033 中途审查）：测试装配随 four_phase 切换指南合同面——四相位
    装配不拼 legacy 决策合同（与生产接线同形，消 SK1 双合同隐患形态）；
    legacy 装配照旧拼接（决策合同不缺席）。"""
    from appv2.api.ontology_guide import OntologyGuideProvider

    runtime4, _completer, db4 = await make_runtime(
        tmp_path,
        engine=QueueQueryEngine([_rows_outcome()]),
        script={"v2.runtime.understand": [UNDERSTAND_MULTI]},
        four_phase=True,
        ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        guide4 = runtime4._executor._guide
        assert isinstance(guide4, OntologyGuideProvider)
        assert guide4._include_decision_contract is False
        assert "discover|execute|ask|finalize" not in guide4.guide()
    finally:
        await db4.dispose()

    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    runtime_legacy, _completer_l, db_legacy = await make_runtime(
        legacy_dir,
        engine=QueueQueryEngine([_rows_outcome()]),
        script={"v2.runtime.understand": [UNDERSTAND_MULTI]},
    )
    try:
        guide_legacy = runtime_legacy._executor._guide
        assert guide_legacy._include_decision_contract is True
        assert "discover|execute|ask|finalize" in guide_legacy.guide()
    finally:
        await db_legacy.dispose()


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
    # 缺省翻转（P-033b——待细化①闭合）：生产缺省＝四相位装配；指南合同面
    # 随之联动（include_decision_contract=False——相位合同在 runtime 消费缝前置）。
    assert holder["four_phase"] is True
    assert holder["guide"]._include_decision_contract is False


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
