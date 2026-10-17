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
  行（非懒加载——零 discover 也注入）；常驻块 run 内恰一次（2026-10-17 消重批——
  与 §A 段同属 run 级共享上下文，只挂澄清轮首入包）；
- caliber_key 三态：场景词确定性匹配／无场景词阈值判断形 ASK 反问／无场景词
  取数形双口径并列注记＋非法口径拒；
- ToolContext 放行态：approved_tables 进 ctx（A2 裁决落点）；
- 生产装配接线：create_app＝V2 装配（runtimev2 受理面；旧指南件「OntologyGuideProvider
  构造形参＋four_phase 开关」已退役——改接/退役断言见本文件末「装配面」节）；
  DefaultGuideProvider 退役。
"""

from __future__ import annotations

import ast
import asyncio
import json
from collections.abc import Sequence
from datetime import date, datetime, timedelta
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
    configure_audit_sink,
    configure_tables,
)
from appv2.runtimev2.persistence import (
    RunStore as V2RunStore,
)
from appv2.runtimev2.state import AskChoice as V2AskChoice
from appv2.runtimev2.state import AskRequest as V2AskRequest
from appv2.runtimev2.understanding.constants import CONVERGE_DRAFT_TEMPLATE
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

# 收敛拒答正文的稳定头部（模板首段——文案本体真源＝`understanding.constants`；本件只判「是拒答」）
_REFUSAL_MARK = CONVERGE_DRAFT_TEMPLATE.split("{", 1)[0]

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


# 审计写口收集器（本测试装配点的注入件；生产同物＝`security.audit` 桥）。
V2_AUDIT: list[Any] = []


def v2_audit_records() -> list[Any]:
    """本次装配以来落的审计记录（`persistence.AuditRecord` 序列——最近一次 `v2_runtime` 起算）。"""
    return list(V2_AUDIT)


def v2_ledger_dump() -> dict[str, Any]:
    store = InMemoryKnowledgeStore(question_array_snapshot(), today=V2_TODAY)
    return dict(dump_from_store(store))


# 台账注释窗段（锚定窗形——窗段合法形；测试面统一用同一窗，模型侧窗结论另经工具匹配载荷给）
V2_NOTE_WINDOW = "2025-09-01~2025-09-03"


def v2_ledger_note(dump: dict[str, Any], keyword: str) -> str:
    """台账注释（**三段槽位对账**形 `槽位｜绑定态｜窗`——相位侧判据面，流水 64）。

    段一＝台账名录名（指标 slot／对象／关系名——`dump` 投影结构名；本件就地核 `keyword` 真在
    名录，防测试面造假名）；段二＝闭世界「已绑定」；段三＝锚定窗形（`V2_NOTE_WINDOW`）。
    """
    registry = {
        row.get(key)
        for block, key in (("metrics", "slot"), ("objects", "obj"), ("relations", "rel"))
        for row in dump.get(block) or []
    }
    assert keyword in registry, keyword  # 槽位须 ∈ 台账名录（假名不得进剧本）
    return f"{keyword}｜已绑定｜{V2_NOTE_WINDOW}"


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
    guide_text: str = "",
    completer: ScriptedCompleter | None = None,
    tables: Any = None,
    clock: Any = None,
) -> tuple[Any, ScriptedCompleter]:
    """runtimev2 标准装配：剧本 completer＋内存簿记表＋四相位图（零 DB、零真实端口）。

    `tables` 非空＝复用既有内存表件（跨 run 的追问／恢复面需要同一份表）；`clock` 非空＝注入计时
    读数口替身（段时长闸的用量注入面——缺省走 `infra.clock`）。`guide_text`＝§A 指南段文本注入值
    （流水 63——经 `RunExecutor` 下传 `clarify`／`match`；缺省空串＝空段头）。

    **审计写口装配点**（生产侧同物＝`security.audit` 桥，归 `api` 组合根 RT-W5-02）：审计唯一写口
    由装配点经 `persistence.configure_audit_sink` 注入——本处注入收集器（`v2_audit_records()`
    读面），使 `orchestration` 的五处留痕（受理／三态收口／拒答收口／外表审批决定／禁用词豁免）
    真实落账，而非走「写口未装配」的缺口通道。
    """
    configure_tables(tables if tables is not None else MemoryTables())
    V2_AUDIT.clear()
    configure_audit_sink(V2_AUDIT.append)
    channel = completer if completer is not None else ScriptedCompleter(script)
    set_completer(channel)
    executor = RunExecutor(
        registry=registry if registry is not None else v2_registry(),
        store=V2RunStore(),
        budget=budget,
        watermark=watermark,
        guide_text=guide_text,
        clock=clock,
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
    """行 5｜前置条件机零 LLM（AST＋import 双证扫描）——V2 两层 ＋ 编排侧同红线。

    规格原文（`specs/agent-loop.md:89`）：「**前置条件机（precondition）**：纯固定代码零 LLM（铁律
    ——LLM 无权判定）」；本行双证扫 **V2 落地面**（`appv2/runtimev2/preconditions/` 与
    `appv2/runtimev2/parsing/` 两包 ＋ 闸件本体 `appv2/tools/precondition.py`）：

    ① **直接面 AST**（裸名＋属性调用形双查）——两包与闸件本体不出现模型调用形；
    ② **import 闭包递归扫描**（「及其传递依赖」锁进机器闸）——闭包内任一 appv2 文件 import 模型
       判定通道（供应商 SDK／V1 模型通道）即红；`appv2.infra.llm_client`（B6 embedding 唯一出口
       ——供应商 SDK 接触的在册单点）显式放行不入闭包禁面。
    另加**编排侧同红线**：本块（`orchestration`）不直引模型出口与供应商 SDK——模型调用发起面＝
    `bookkeeping.call_model` 单点（规格 `specs/agent-loop.md:72`）；编排层不为这两层引入任何 LLM
    判定面。
    """
    repo = Path(__file__).resolve().parents[2]
    seeds = {
        Path("appv2/tools/precondition.py"),
        *(
            path.relative_to(repo)
            for path in (repo / "appv2/runtimev2/preconditions").rglob("*.py")
            if "__pycache__" not in path.parts
        ),
        *(
            path.relative_to(repo)
            for path in (repo / "appv2/runtimev2/parsing").rglob("*.py")
            if "__pycache__" not in path.parts
        ),
    }
    forbidden_calls = {"complete", "ainvoke", "invoke", "agenerate", "generate"}
    forbidden_modules = ("llm", "gateway", "litellm", "openai", "langchain")
    closure_forbidden = ("appv2.runtime.llm", "litellm", "openai", "langchain")

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
                        f"{rel}: 前置条件机／解析层直接面出现模型调用形 {name}"
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
    assert repo / "appv2/runtimev2/bookkeeping/ports.py" in visited  # 已知传递依赖（闭包真达面）
    assert repo / "appv2/runtimev2/state/models.py" in visited

    # 编排侧同红线：本块不直引模型出口／供应商 SDK（发起面＝bookkeeping.call_model 单点）
    orchestration = repo / "appv2/runtimev2/orchestration"
    for path in sorted(orchestration.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            for name in _imported(node):
                assert name not in {
                    "appv2.runtimev2.gateway_adapter",
                    "appv2.infra.llm_client",
                    "litellm",
                    "openai",
                }, f"{path.relative_to(repo)}: 编排层直引模型出口／供应商 SDK：{name}"


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


async def test_four_phase_understand_schema_feedback_retry_recovers() -> None:
    """理解步 schema 首拒 → 拒因回喂 → 次读合规 → 四相位正常走通（run `completed`）。

    2026-10-16 补·流水 67（`specs/understanding.md` 行为 13／`specs/agent-loop.md` 行为 1 承条）——
    真机病灶面（`run-60bc4aaa` 首拒即 `failed`）的端到端反证：首读剧本＝真机原形（旧两行式被塞进
    `text`、漏 `metric_candidates`）→ 回喂载荷落链尾 → 次读合规 → 澄清→分解→过闸→批量→汇总→收口
    全程照旧。判据：verdict(final) 非 failed；理解模型调用恰 2 次（上限恰一次）；回喂载荷在链上
    （逐字前缀延伸）；回喂支零 notice（如实上报面零增）。
    """
    dump = v2_ledger_dump()
    bad_understand = json.dumps(
        {"route": "full", "text": "理解：问各井日产油量。\n指标候选：日产油量"},
        ensure_ascii=False,
    )
    note = v2_ledger_note(dump, "日产油量")
    clarify = v2_decompose(
        subtask_id="s1",
        question="2025-09-01 到 09-03 各井日产油量",
        ledger_notes=note,
        chain="data",
    )
    script = {
        "understand": [bad_understand, V2_UNDERSTAND],
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
        runtime, completer = v2_runtime(script=script, registry=v2_registry(engine=engine))
        events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
        run_id = next(
            event.data["run_id"] for event in reversed(events) if "run_id" in event.data
        )
    assert events[-2].data["status"] == "completed"  # 零 failed（真机病灶面的反证）
    row = V2RunStore().run(run_id)
    assert row is not None and row.status == "completed" and "21.16" in (row.answer or "")
    # 上限恰一次：理解模型调用恰 2 次（首读＋回喂后次读），无第三次
    understand_calls = [item for item in completer.calls if item[0] == "understand"]
    assert len(understand_calls) == 2
    # 回喂＝追加形：第二次调用的链＝第一次的逐字前缀延伸（末两件＝首答原话＋回喂载荷）
    first, second = understand_calls[0][1], understand_calls[1][1]
    assert second[: len(first)] == first
    assert second[len(first)]["role"] == "assistant"
    feedback = second[-1]
    assert feedback["role"] == "user"
    assert feedback["content"].startswith("【拒因】缺必填字段 `metric_candidates`")
    assert "【期望形】" in feedback["content"]
    # 落库面留痕：回喂载荷在链上、过程档案有回喂注记、理解步零 notice（回喂支零副作用）
    state = V2RunStore().load(run_id)
    assert any(m["content"] == feedback["content"] for m in state.messages)
    titles = [entry["title"] for entry in state.process_notes]
    assert titles.count("读题回喂重试") == 1 and titles.count("读题") == 2
    assert [n for n in state.notices if n["type"] == "run_failed"] == []


async def test_four_phase_understand_schema_feedback_twice_converges_to_refusal() -> None:
    """理解步两读皆拒 → **收敛拒答**收口 `completed`（上限恰一次，无第三次调用）。

    **2026-10-17 EB3 D4.4 改判**（真机 `eval/results/frames/EB2-NQ-D2.json`：模型两次都在 JSON
    字符串里带未转义引号 → 旧形「抛 `UnderstandingParseError` → 编排收 `failed`」整 run 零交付）：
    双读皆不合 schema → `bookkeeping.direct_answer` 落拒答正文 ＋ `next_intent=answer` → run 走
    收口（`completed`），有正文帧、有留痕，**不判 `failed`、不零交付**；**修正回路只一轮**
    （理解模型调用恰 2 次——第三次永不发生），拒因载荷留痕在链上。

    **2026-10-17 EB5a 补**：本件剧本＝**非引号病**形（旧两行式塞进 `text` ＋ 合法 JSON 缺必填字段）
    ——确定性引号自修零命中，故仍走「回喂恰一次 → 收敛拒答」（拒答文案随 EB5a 改）。引号病形
    （EB3 三题同形）的端到端面＝`::test_four_phase_understand_quote_repair_delivers_answer`。
    """
    bad_understand = json.dumps(
        {"route": "full", "text": "理解：问各井日产油量。\n指标候选：日产油量"},
        ensure_ascii=False,
    )
    script = {"understand": [bad_understand]}
    wire_ledger_projection(V2LedgerPort(v2_ledger_dump()))
    runtime, completer = v2_runtime(script=script)
    events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    run_id = next(
        event.data["run_id"] for event in reversed(events) if "run_id" in event.data
    )
    assert events[-2].data["status"] == "completed"  # 不判 failed（不零交付）
    failed_notices = [
        event
        for event in events
        if event.event == "notice" and event.data["type"] == "run_failed"
    ]
    assert failed_notices == []
    # 拒绝零交付：拒答正文在流上（直答旁路 text 帧）＋落库答案
    texts = [event.data["content"] for event in events if event.event == "text"]
    assert texts and _REFUSAL_MARK in texts[-1]
    row = V2RunStore().run(run_id)
    assert row is not None and row.status == "completed" and _REFUSAL_MARK in (row.answer or "")
    # 上限恰一次：两读皆拒即收口，绝无第三次调用
    assert len([call for call in completer.calls if call[0] == "understand"]) == 2
    # 拒因留痕（链上载荷）；四相位未入场（理解步即收敛收口）
    state = V2RunStore().load(run_id)
    assert state.messages[-2]["role"] == "assistant"  # 次读原话（照旧追加链尾）
    assert state.messages[-3]["role"] == "user"
    assert state.messages[-3]["content"].startswith("【拒因】缺必填字段 `metric_candidates`")
    assert [row for row in v2_steps(run_id, "clarify")] == []


# EB3 三题（NQ-C3／NQ-D3／NQ-M1）的真机失败形之一（逐字取自 `logs/llm_calls/20261017.jsonl`
# run-7fec93ff 首读——**`text` 值内的成对引号未转义**；题面原句见 `eval/results/frames/
# EB3-NQ-C3.json` 的 blackbox 记录）。三题同形，本件取一题作端到端代表（逐题面在
# `tests/domains/test_v2_understanding.py::` 同题逐题面用例
# `test_eb5a_zero_delivery_three_questions_quote_repair_admits`）。
_EB5A_RAW_UNDERSTAND = (
    '{"route": "full", "text": "理解：判断评审人关于报告4.2节防砂说法与报告的逐项不符之处，并作答'
    '（1）本井实际防砂方式与筛管型号、防砂精度；（2）"20/40目砾石挤压充填"在报告中的真实身份及'
    '报告是否给出实施后的砾石量与充填井段；（3）"占船日4.0天"在4.2节语境下的含义及报告中另两处'
    '"4.0天"分别指什么（指出章节与口径）。", "metric_candidates": []}'
)
_EB5A_RAW_UNDERSTAND_TEXT = (
    "理解：判断评审人关于报告4.2节防砂说法与报告的逐项不符之处，并作答（1）本井实际防砂方式与"
    "筛管型号、防砂精度；（2）「20/40目砾石挤压充填」在报告中的真实身份及报告是否给出实施后的"
    "砾石量与充填井段；（3）「占船日4.0天」在4.2节语境下的含义及报告中另两处「4.0天」分别指"
    "什么（指出章节与口径）。"
)


async def test_four_phase_understand_quote_repair_delivers_answer() -> None:
    """理解步**引号自修受理** → 四相位照常走通、答案真交付（2026-10-17 EB5a：整题零交付三题同形）。

    病灶（`eval/results/frames/EB3-{NQ-C3,NQ-D3,NQ-M1}.json`）：理解步严格解析两次皆拒（同一形＝
    题干引号被照搬进 `text` 值不转义）→ 旧形「回喂恰一次 → 收敛拒答」，用户只拿到拒答正文，判分
    记「整题零交付 ❌」。新行为：**首读即受理**（`parsing.parse_with_quote_repair`，零模型零占轮）
    → `route="full"` 分派 → 澄清→分解→过闸→批量→汇总→收口全程照旧 → run `completed` 携**真答案**。

    判据：解析失败**零报告步**（不成拒）／理解模型调用**恰 1 次**（自修不占回喂上限）／
    理解字段非空且＝真机原话＋引号中文形／`emission_quote_repair` notice 在流上／终态 `completed`
    且答案行携真数值（非拒答正文）。
    """
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    clarify = v2_decompose(
        subtask_id="s1",
        question="2025-09-01 到 09-03 各井日产油量",
        ledger_notes=note,
        chain="data",
    )
    script = {
        "understand": [_EB5A_RAW_UNDERSTAND],
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
        runtime, completer = v2_runtime(script=script, registry=v2_registry(engine=engine))
        events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
        run_id = next(
            event.data["run_id"] for event in reversed(events) if "run_id" in event.data
        )
    assert events[-2].data["status"] == "completed"  # 不判 failed
    assert [event for event in events if event.event == "notice"
            and event.data["type"] == "run_failed"] == []
    row = V2RunStore().run(run_id)
    assert row is not None and row.status == "completed"
    assert "21.16" in (row.answer or "")  # **真交付**（不是拒答正文）
    assert _REFUSAL_MARK not in (row.answer or "")
    # 引号自修受理：notice 在流上、理解调用恰 1 次（不占回喂上限）、解析失败报告步零条
    assert [event.data["type"] for event in events if event.event == "notice"] == [
        "emission_quote_repair"
    ]
    assert len([call for call in completer.calls if call[0] == "understand"]) == 1
    state = V2RunStore().load(run_id)
    assert state.understanding == _EB5A_RAW_UNDERSTAND_TEXT
    assert [row for row in v2_steps(run_id, "understand")] == []
    assert [row for row in v2_steps(run_id, "clarify")]  # 四相位真入场（非理解步即收口）


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


async def test_decision_prompt_discover_budget_shows_real_used_count() -> None:
    """缺陷二回归（2026-10-17 消重批）：决策 prompt 的「已用 N 次」＝**真实已发 discover 次数**。

    病根：静态相位合同块内曾嵌 `{discover_used}` 槽——槽值只在相位首入替换一次（首入时恒 0），
    随追加链一路带到 answer 调用仍写着「已用 0 次」，模型看不见自己烧了几支（真机 run-e1b6ff1e：
    8 次 decision、4 次 discover 全 no_hit，烧到 `budget_converged`）。现静态合同只留上限、不载
    计数；真实已用数只由**每轮动态条**①「探查预算：全 run ≤{上限} 次，已用 {已用} 次。」披露
    （行为 16①——机计数权威披露面）。本钉＝发 N 次 discover 后决策 prompt 显示已用 N 次。
    """
    def _double(prefix: str) -> str:
        return json.dumps(
            {
                "action": "discover",
                "discovers": [
                    {"tool": "semantic_query", "args": {"question": f"{prefix}-1"}},
                    {"tool": "semantic_query", "args": {"question": f"{prefix}-2"}},
                ],
            },
            ensure_ascii=False,
        )

    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            _double("轮1"),  # 两支 discover → 已用 2
            _double("轮2"),  # 再两支 → 已用 4
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
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(
            script=script, registry=v2_registry(engine=V2QueueEngine([_rows_outcome()]))
        )
        events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"

    run_id = events[-1].data["run_id"]
    state = V2RunStore().load(run_id)
    assert int(state.discover_used) == 4  # 真计数面：两轮各两支
    cap = int(state.budget.discovers_per_run)

    calls = completer.messages_of("decision")
    # 第 2 轮决策：本轮动态条＝探查预算条，显示**真实**已用 2 次（非冻值 0）
    assert calls[1][-1]["content"] == f"探查预算：全 run ≤{cap} 次，已用 2 次。"
    # 第 3 轮决策：真实已用 4 次（每轮随链尾现披露）
    assert calls[2][-1]["content"] == f"探查预算：全 run ≤{cap} 次，已用 4 次。"
    # 静态合同只留上限、不载计数：整链零「已用 0 次」冻值（模型不再被陈旧读数误导）
    chain = "\n".join(
        str(message.get("content", "")) for message in calls[-1]
    )
    assert "已用 0 次" not in chain
    assert f"可用探查（discover，全 run ≤{cap} 次）：" in chain
    assert f"探查预算：全 run ≤{cap} 次，已用 2 次。" in chain
    assert f"探查预算：全 run ≤{cap} 次，已用 4 次。" in chain


async def test_four_phase_ledger_dump_round1_injection() -> None:
    """词典层第 1 轮全量注入（拍板 a）：澄清相位包携台账全量块；
    零 discover 也注入（非懒加载）；**run 级共享上下文只注一次**（2026-10-17 消重批——匹配包不再
    重注）；决策调用面互为前缀延伸（pin-22）。"""
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

    # 追加式链（pin-22）：第 2 次决策调用＝第 1 次的**前缀延长**（消重不动已有消息）
    second_call = completer.messages_of("decision")[1]
    assert second_call[: len(first_call)] == first_call
    # run 级共享上下文只注一次（2026-10-17 消重批·缺陷一）：台账全量块在整链恰一次——挂澄清轮
    # 首入包；匹配包不再重注（末轮 answer 无重复 token）。第二链里台账块**逐字**＝第一链条内
    # 那一块（字节级不变，只改出现次数）。
    assert sum("台账全量" in message.get("content", "") for message in second_call) == 1
    assert sum("台账全量" in message.get("content", "") for message in first_call) == 1
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


# ---------- 边界集／保留集（RT-W5-01c 行 35／36——收口簇的两端钉） ----------


async def test_boundary_suspend_interrupt_budget_rewire_bad_cite() -> None:
    """行 35｜【边界集】挂起／中断／预算触界／换链回炉／坏引标 → 各自落到对应分支。

    五个边界形各跑一遍真链，逐形钉住**落到哪条分支**（不互串、不吞）：

    1. **挂起**——工具侧 ask（引擎观察为等用户）→ `ask` 帧 ＋ run 转 `waiting_ask`（本腿收束、
       run 未收口）；
    2. **中断**——台账投影端口中断 → fail-closed 收束为 `failed`（**不产出半成品答案**）；
    3. **预算触界**——轮预算到顶 → 收敛交付（`budget_converged` notice ＋ 终态 `completed`）；
    4. **换链回炉**——在册未绑定 agg 触发换链闸 → 回炉①澄清（`chain_switch_reentry` notice、
       数据链零执行、知识链真执行）；
    5. **坏引标**——草稿引标越界（坏引标）→ 作答相位**剥除该记号**（2026-10-17 EB5b 改判：
       不判失败），材料照常带引标交付 → 终态 `completed`、无 `run_failed`。
    """
    from appv2.infra.clock import freeze
    from appv2.query import ASKBACK_TIME_CHOICES, ASKBACK_TIME_QUESTION, QueryOutcome
    from appv2.runtimev2.state import Budget

    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")

    # ——1 挂起：工具侧 ask ——
    wire_ledger_projection(V2LedgerPort(dump))
    ask_engine = V2QueueEngine(
        [
            QueryOutcome.need_clarify(
                question=ASKBACK_TIME_QUESTION, choices=ASKBACK_TIME_CHOICES
            )
        ]
    )
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script={
                "understand": [V2_UNDERSTAND],
                "decision": [
                    v2_decompose(subtask_id="s1", question="最近的日产油量",
                                 ledger_notes=note, chain="data"),
                    v2_matches(v2_data_match(subtask_id="s1", slot="日产油量",
                                             start="2025-09-01", end="2025-09-03")),
                ],
            },
            registry=v2_registry(engine=ask_engine),
        )
        suspend_events = await v2_run(runtime, "最近的日产油量")
    asks = v2_ask_frames(suspend_events)
    assert asks and asks[-1]["frame"]["kind"] == "clarify"
    assert suspend_events[-1].event == "verdict"
    assert suspend_events[-1].data["status"] == "waiting_ask"
    assert V2RunStore().run(asks[-1]["run_id"]).status == "waiting_ask"

    # ——2 中断：台账装载中断 → fail-closed failed ——
    class _BrokenLedger:
        async def fetch(self) -> dict[str, Any]:
            raise RuntimeError("台账投影端口中断")

    wire_ledger_projection(_BrokenLedger())
    with freeze("2026-10-08T09:00:00"):
        runtime_i, _completer_i = v2_runtime(
            script={"understand": [V2_UNDERSTAND]},
            registry=v2_registry(),
        )
        interrupt_events = await v2_run(runtime_i, "中断题")
    assert interrupt_events[-1].event == "blackbox"
    assert interrupt_events[-1].data["status"] == "failed"
    interrupt_row = V2RunStore().run(interrupt_events[-1].data["run_id"])
    assert interrupt_row is not None and interrupt_row.status == "failed"
    assert not (interrupt_row.answer or ""), "非法降级：失败不得产出半成品答案"
    assert any(
        event.data.get("type") == "run_failed"
        for event in interrupt_events
        if event.event == "notice"
    )

    # ——3 预算触界：轮预算 0 → 首相位入口收敛 ——
    dump_budget = v2_ledger_dump()
    wire_ledger_projection(V2LedgerPort(dump_budget))
    with freeze("2026-10-08T09:00:00"):
        runtime_b, _completer_b = v2_runtime(
            script={"understand": [V2_UNDERSTAND], "decision": [], "answer": []},
            registry=v2_registry(engine=V2QueueEngine([_rows_outcome()])),
            budget=Budget(rounds=0),
        )
        budget_events = await v2_run(runtime_b, "预算触界题")
    assert budget_events[-1].data["status"] == "completed"
    budget_row = V2RunStore().run(budget_events[-1].data["run_id"])
    assert budget_row is not None and budget_row.status == "completed"
    assert budget_row.answer  # 触界收敛正文（有界终止，非降级）
    assert any(
        event.data.get("type") == "budget_converged"
        for event in budget_events
        if event.event == "notice"
    )

    # ——4 换链回炉：在册未绑定 agg → 回炉①澄清改链 ——
    dump_rewire = v2_ledger_dump()
    bound_note = v2_ledger_note(dump_rewire, "配产量")
    # 换链轮子问题同问配产量 → 台账注释载同名录名（旧形曾抄术语行首名「老完成率」——流水 64
    # 判据下段一须 ∈ 名录（指标/对象/关系名），术语名不在名录，登记项呈主窗）
    knowledge_note = v2_ledger_note(dump_rewire, "配产量")
    wire_ledger_projection(V2LedgerPort(dump_rewire))
    retrieval = _retrieval_with(_fragment_obs(
        "配产量按月度计划分解下达：各井合计月度配产 21.4 万方（月报所载）。", "frag-peichan-b"
    ))
    data_engine = V2QueueEngine([])
    with freeze("2026-10-08T09:00:00"):
        runtime_r, _completer_r = v2_runtime(
            script={
                "understand": [V2_UNDERSTAND],
                "decision": [
                    v2_decompose(subtask_id="s1", question="去年各井配产量",
                                 ledger_notes=bound_note, chain="data"),
                    v2_matches(v2_data_match(subtask_id="s1", slot="配产量",
                                             start="2025-01-01", end="2026-01-01")),
                    v2_decompose(subtask_id="s1", question="去年各井配产量（换链）",
                                 ledger_notes=knowledge_note, chain="knowledge"),
                    v2_matches(v2_knowledge_match(subtask_id="s1", question="去年各井配产量")),
                ],
                "answer": ["去年各井配产量：月度配产合计 21.4 万方 [1]（按文档所载交付）。"],
            },
            registry=v2_registry(engine=data_engine, retrieval=retrieval),
        )
        rewire_events = await v2_run(runtime_r, "去年各井配产量是多少？")
    assert rewire_events[-1].data["status"] == "completed"
    assert not v2_ask_frames(rewire_events)  # 换链回炉不挂起（回炉①澄清改链）
    assert any(
        event.data.get("type") == "chain_switch_reentry"
        for event in rewire_events
        if event.event == "notice"
    )
    rewire_run_id = rewire_events[-1].data["run_id"]
    rewire_steps = v2_steps(rewire_run_id, "precondition")
    assert rewire_steps[0].payload["chain_switch_reentry"] is True  # 换链回炉首次触发
    assert data_engine.run_calls == 0  # 数据链零执行（不直答不执行）
    assert retrieval.retrieve_calls == 1  # 换知识链真执行

    # ——5 坏引标：草稿引标越界 → 剥除后带材料直答 → completed（2026-10-17 EB5b 改判） ——
    dump_cite = v2_ledger_dump()
    cite_note = v2_ledger_note(dump_cite, "日产油量")
    wire_ledger_projection(V2LedgerPort(dump_cite))
    with freeze("2026-10-08T09:00:00"):
        runtime_c, _completer_c = v2_runtime(
            script={
                "understand": [V2_UNDERSTAND],
                "decision": [
                    v2_decompose(subtask_id="s1", question="2025-09-01 到 09-03 各井日产油量",
                                 ledger_notes=cite_note, chain="data"),
                    v2_matches(v2_data_match(subtask_id="s1", slot="日产油量",
                                             start="2025-09-01", end="2025-09-03")),
                ],
                "answer": ["N-01 井 2025-09-01 日产油量 21.16 吨 [9]。"],  # 引标越界（坏引标）
            },
            registry=v2_registry(engine=V2QueueEngine([_rows_outcome()])),
        )
        cite_events = await v2_run(runtime_c, "坏引标题")
    assert cite_events[-1].event == "blackbox"
    assert cite_events[-1].data["status"] == "completed"
    cite_row = V2RunStore().run(cite_events[-1].data["run_id"])
    assert cite_row is not None and cite_row.status == "completed"
    assert cite_row.error is None
    cite_run_id = cite_events[-1].data["run_id"]
    # 界外记号离场（正文其余字面零改）、留痕在起草步 payload——不判失败、不 run_failed
    assert "[9]" not in (cite_row.answer or "")
    cite_steps = v2_steps(cite_run_id, "draft")
    assert cite_steps and cite_steps[0].payload["dangling_citation_seqs"] == [9]
    # 剥除后该行失去引标 → 按核验面**既有处置**收口（无据断言删句＋`unsupported_claim` 留痕）：
    # 本形唯一断言即坏引标行 → 删句后空稿不推（行为 9），如实缺口收口、终态 completed
    assert any(
        event.data.get("type") == "unsupported_claim"
        for event in cite_events
        if event.event == "notice"
    )
    assert not any(
        event.data.get("type") == "run_failed"
        for event in cite_events
        if event.event == "notice"
    )


async def test_retention_plain_four_phase_unchanged() -> None:
    """行 36｜【保留集】普通提问四相位收口行为不变（无挂起、无触界、无回炉）。

    保留集判据＝**普通提问的收口行为逐项不变**：一轮四相位走完直接收口——零 `ask` 帧（不挂起）、
    零预算触界（`budget_hit` 空、无 `budget_converged`）、零换链回炉（无 `chain_switch_reentry`）、
    零失败（无 `run_failed`）；步序与收口帧序（`verdict(final)` → `blackbox`）保持既有形状。
    """
    from appv2.infra.clock import freeze
    from appv2.runtimev2.persistence import RunStore

    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    wire_ledger_projection(V2LedgerPort(dump))
    engine = V2QueueEngine([_rows_outcome()])
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(
            script={
                "understand": [V2_UNDERSTAND],
                "decision": [
                    v2_decompose(subtask_id="s1", question="2025-09-01 到 09-03 各井日产油量",
                                 ledger_notes=note, chain="data"),
                    v2_matches(v2_data_match(subtask_id="s1", slot="日产油量",
                                             start="2025-09-01", end="2025-09-03")),
                ],
                "answer": ["子任务 s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
            },
            registry=v2_registry(engine=engine),
        )
        events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")

    # 收口形状不变：末帧 blackbox、其前 verdict(final)、状态 completed
    assert [event.event for event in events][-1] == "blackbox"
    assert events[-2].event == "verdict"
    assert events[-2].data["status"] == "completed"
    assert events[-2].data["subtype"] == "final"
    run_id = events[-1].data["run_id"]
    row = RunStore().run(run_id)
    assert row is not None and row.status == "completed"
    assert row.answer and "21.16" in row.answer
    assert row.manifest_digest

    # 三类「异常分支」零命中：不挂起、不触界、不回炉、不失败
    assert not [event for event in events if event.event == "ask"]
    notices = [event.data for event in events if event.event == "notice"]
    assert not [
        item
        for item in notices
        if item.get("type") in {"budget_converged", "chain_switch_reentry", "run_failed"}
    ]
    state = RunStore().load(run_id)
    assert state.budget_hit == []
    assert state.pending_ask is None
    assert int(state.rounds) == 1  # 一轮收口（普通提问不占二轮）
    assert engine.run_calls == 1  # 单支恰执行一次

    # 步序不变：决策×5（读题／澄清／匹配／过闸／收口路由）＋执行／作答两拍／核验各就位
    kinds = [row.step for row in v2_steps(run_id)]
    assert kinds == [
        "decision", "decision", "decision", "decision", "decision",
        "execute", "answer", "answer", "verify", "answer",
    ]
    phases = {
        (row.payload or {}).get("phase") for row in v2_steps(run_id) if row.payload
    }
    assert {"clarify", "precondition", "execution", "draft", "verify", "finalize"} <= phases
    assert completer.counts() == {"understand": 1, "decision": 2, "answer": 1}


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
    knowledge_note = v2_ledger_note(dump, "配产量")  # 同上：段一 ∈ 名录（术语名已不可作段一）
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

    # 相位合同一次性（钉 `pin-24`）：回炉轮不重发合同包——标记记一次、链上台账全量块恰一块
    # （run 级共享上下文只注一次，挂澄清轮首入包——2026-10-17 消重批：匹配包不再重注），
    # 不随轮数增长。
    state = V2RunStore().load(run_id)
    assert state.contracts_appended.count("clarify") == 1
    assert state.contracts_appended.count("toolmatch") == 1
    last_call = completer.messages_of("decision")[-1]
    assert sum("台账全量" in message.get("content", "") for message in last_call) == 1


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


# ---------- 段时长闸接线（流水 61 裁：编排侧自计时——秒闸真跑） ----------


class V2AdvancingClock:
    """可推进的注入钟（`RunExecutor` 的计时读数口替身——`infra.clock` 语义：零参调用回时刻）。"""

    def __init__(self, at: str) -> None:
        self.at = datetime.fromisoformat(at)

    def __call__(self) -> datetime:
        return self.at


async def test_four_phase_seconds_gate_overrun_converges_under_limit_clean() -> None:
    """行 7｜段时长闸（`specs/agent-loop.md:149`「单段时限 300s」）＋流水 61 裁：编排侧自计时。

    两半同判（用量注入面＝`RunExecutor` 的受理腿起点＋`infra.clock` 读数差，挂起等人工不计时、
    跨段不累计）：

    ① **跑过上限**：注入钟推过 `state.budget.seconds` → 轮闸入口（澄清相位入口）经
       `state.check_limits(elapsed_seconds=…)` 判出 `seconds` 触界 → `bookkeeping.converge` 落地
       ——`budget_hit` 含 `seconds`、收敛注记 `gates` 含 `seconds`（触界不静默，且不再发起模型
       调用——免无界自旋）；
    ② **未超上限**：同一注入钟不推进 → 零副作用（照常四相位收口：`budget_hit` 空、无
       `budget_converged` 注记、答案如实交付）。
    """
    from appv2.runtimev2.state import TOTAL_SECONDS

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
                v2_data_match(subtask_id="s1", slot="日产油量",
                              start="2025-09-01", end="2025-09-03")
            ),
        ],
        "answer": ["s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))

    # —— ① 跑过时长上限：受理腿取起点（钟未推）→ 图起跑前把钟推过上限 ——
    clock = V2AdvancingClock("2026-10-08T09:00:00")
    runtime, completer = v2_runtime(
        script=script, registry=v2_registry(engine=V2QueueEngine([_rows_outcome()])), clock=clock
    )
    handle = await runtime.ask(V2AskRequest(question="段时长闸题", actor=V2_ACTOR))
    clock.at = clock.at + timedelta(seconds=TOTAL_SECONDS)  # 段内用时＝上限（判据「达上限即触界」）
    events = [event async for event in handle.stream]

    assert events[-1].event == "blackbox"
    assert events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    state = V2RunStore().load(run_id)
    assert "seconds" in state.budget_hit  # 机读信号面（行为 13：触界必留 budget_hit）
    converged = [item for item in state.notices if item.get("type") == "budget_converged"]
    assert converged and "seconds" in converged[0]["gates"]  # 收敛注记 gates 含 seconds（如实）
    assert "seconds" in converged[0]["content"]
    assert state.answer  # 收敛正文（有界终止，非降级）
    assert completer.counts().get("decision", 0) == 0  # 入口收敛：零决策调用（免无界自旋）

    # —— ② 未超时长零副作用：同一注入钟不推进（用时 0 < 上限）→ 照常四相位收口 ——
    dump_clean = v2_ledger_dump()
    wire_ledger_projection(V2LedgerPort(dump_clean))
    runtime_clean, completer_clean = v2_runtime(
        script=script,
        registry=v2_registry(engine=V2QueueEngine([_rows_outcome()])),
        clock=V2AdvancingClock("2026-10-08T09:00:00"),
    )
    clean_events = await v2_run(runtime_clean, "时长未到的日产油量题")

    assert clean_events[-1].event == "blackbox"
    assert clean_events[-1].data["status"] == "completed"
    clean_state = V2RunStore().load(clean_events[-1].data["run_id"])
    assert clean_state.budget_hit == []  # 未触界：零机读信号
    assert not [
        item for item in clean_state.notices if item.get("type") == "budget_converged"
    ]  # 未触界恒无注记（行为 12）
    assert "21.16" in (clean_state.answer or "")  # 照常交付（不误伤）
    assert completer_clean.counts().get("decision", 0) == 2


def test_legacy_guide_contract_knob_retired() -> None:
    """C6 收尾（RT-W5-02 偏差 2——eng/04 §五 织网②改写面）：旧指南合同切换面已退役。

    旧断言（`make_runtime(four_phase=…)` 切 `include_decision_contract` ＋
    `GraphRunExecutor._guide`／`._four_phase` 两件）属**旧 runtime 装配面**（ReAct 单相位
    决策面）：api 组合根改 V2 装配后该面退场——G9 登记，`DECISION_CONTRACT`（真源＝旧编排件
    `appv2/runtime/guide.py`，与 `graph.parse_decision` schema 校验同源）服务对象＝旧装配面，
    V2 四相位**从不请求**该合同（相位合同承载面见
    `test_ontology_guide_provider_loads_section_a_and_v2_phase_contracts`）。

    三向如实断言：① 旧形参在装载件保留＝构造兼容且**惰性**（两取值同文）；② 旧决策合同正文
    不落指南面（本层零旧码进口、不复制正文）；③ V2 装配面（runtimev2 `RunExecutor`）不携带该
    V1 件（`_guide`／`_four_phase` 两属性均无）。
    """
    from appv2.api.ontology_guide import OntologyGuideProvider
    from appv2.runtime.guide import DECISION_CONTRACT

    today = date(2026, 10, 8)
    with_contract = OntologyGuideProvider(today=today, include_decision_contract=True).guide()
    without = OntologyGuideProvider(today=today, include_decision_contract=False).guide()
    assert with_contract == without  # 旧装配面构造兼容形参＝惰性（G9 登记）
    assert DECISION_CONTRACT not in with_contract  # 合同正文不落指南面

    runtime, _completer = v2_runtime(script={"understand": [V2_UNDERSTAND]})
    assert not hasattr(runtime._executor, "_guide")
    assert not hasattr(runtime._executor, "_four_phase")


# ---------- 装配面：§A 装载件＋create_app V2 装配＋占位退役（RT-W5-02 改接面） ----------


def test_ontology_guide_provider_loads_section_a_and_v2_phase_contracts() -> None:
    """§A 装载面照旧在场；决策合同面**改接 V2 公开出口**（RT-W5-02 偏差 2 收尾）。

    §A 装载与占位符填充不变（装载件本体零动）；旧面（§A 拼接旧编排件 `DECISION_CONTRACT`——
    服务对象＝旧 runtime 装配面）随 api 改 V2 装配退役（G9 登记，本层不复制正文、不设第二真源）。
    改接断言走 V2 出口两件：① 相位合同常量（`appv2.runtimev2.prompts` 六族——澄清/匹配两族）
    声明**本相位动作闭世界**，旧四动作合同（`discover|execute|ask|finalize`）零命中（消 SK1
    双合同隐患形态 / 相位合同唯一有效）；② §A 文本经 `assemble_decision_package` 的 `guide_text`
    注入口**逐字**进决策轮首入包（两相位同口）。
    """
    from appv2.api.ontology_guide import OntologyGuideProvider
    from appv2.runtime.guide import DECISION_CONTRACT
    from appv2.runtimev2.prompts import (
        GUIDE_REFERENCE_HEAD,
        PHASE_CLARIFY,
        PHASE_TOOLMATCH,
        TOOLMATCH_EMISSION_CONTRACT,
        assemble_decision_package,
    )
    from appv2.runtimev2.state import RunState

    guide = OntologyGuideProvider(today=date(2026, 10, 8)).guide()
    assert "发射判据" in guide  # §A 装载面（ontology 资产原文）
    assert "2026-10-08" in guide and "2026-09-08" in guide  # 占位符填充（today／start30）
    assert "2026-10-01" in guide  # month_start
    assert DECISION_CONTRACT not in guide  # 旧决策合同不落指南面（G9 退役面）

    # V2 出口①：§A 文本经决策轮首入包注入口逐字进相位包（澄清／匹配两相位同口）
    state = RunState(run_id="run-guide", actor="dev-u1", question="各井日产油量")
    clarify = assemble_decision_package(
        state, phase=PHASE_CLARIFY, guide_text=guide, today=date(2026, 10, 8), max_subtasks=4
    )
    assert GUIDE_REFERENCE_HEAD in clarify and "2026-09-08" in clarify  # §A 窗词锚定随注入面
    # V2 出口②：本相位动作闭世界（V2 动词面 decompose）——旧四动作合同零命中
    assert "discover|decompose|ask|finalize" in clarify
    assert "discover|execute|ask|finalize" not in clarify

    toolmatch = assemble_decision_package(state, phase=PHASE_TOOLMATCH, guide_text=guide)
    assert TOOLMATCH_EMISSION_CONTRACT in toolmatch  # 匹配相位合同常量逐字入包
    assert "discover|execute|ask|finalize" not in toolmatch


def test_default_guide_provider_retired() -> None:
    """占位指南退役（不设双真源）——生产唯一指南源＝ontology 资产装载件。"""
    import appv2.runtime as runtime_pkg

    assert not hasattr(runtime_pkg, "DefaultGuideProvider")
    import appv2.runtime.graph as graph_mod

    assert not hasattr(graph_mod, "DefaultGuideProvider")


def test_create_app_wires_v2_runtime_not_legacy_guide(tmp_path: Any) -> None:
    """create_app 组合根＝V2 装配（RT-W5-02 改接后）：受理面为 runtimev2，无旧指南件。

    旧断言（`app.state.agent_runtime._executor._guide` 为 `OntologyGuideProvider` ＋
    `._four_phase is True`）属**旧 runtime 装配面**（任务 10 的真指南接线）：V2 `RunExecutor`
    无指南形参——「四相位」是编排面本体（无 V1 式开关），指南合同面由
    `appv2.runtimev2.prompts` 六族承载（G9 登记：`DECISION_CONTRACT` 服务对象＝旧装配面，
    V2 从不请求——见 `test_legacy_guide_contract_knob_retired`）。
    """
    from appv2.api import create_app
    from appv2.infra.db import ConnectionManager, DatabaseSpec
    from appv2.runtimev2.gateway_adapter import ScriptedCompleter
    from appv2.runtimev2.orchestration import AgentRuntime, RunExecutor
    from appv2.runtimev2.persistence import RunStore as V2RunStore

    async def _main() -> None:
        spec = DatabaseSpec(
            name="primary", role="primary", driver="sqlite", host="", port=0,
            database=str(tmp_path / "guide-wiring.db"), user="", password="",
            pool_size=2, max_overflow=1,
        )
        db = ConnectionManager([spec])
        registry = ToolRegistry(
            knowledge=FakeKnowledgeStore(),
            query=FakeQueryEngine(),
            retrieval=FakeRetrievalEngine(),
        )
        app = create_app(db=db, registry=registry, completer=ScriptedCompleter({}))
        try:
            runtime = app.state.agent_runtime
            assert isinstance(runtime, AgentRuntime)  # 受理面＝runtimev2 公开面
            executor = runtime._executor
            assert isinstance(executor, RunExecutor)
            # 旧装配面两件不随 V2 装配出场（G9 退役面——四相位恒为编排面本体）
            assert not hasattr(executor, "_guide")
            assert not hasattr(executor, "_four_phase")
            assert isinstance(app.state.run_store, V2RunStore)  # 簿记读口＝persistence 件
        finally:
            await db.dispose()

    asyncio.run(_main())


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


async def test_guide_text_injected_into_decision_phase_via_orchestration() -> None:
    """§A 指南文本经编排注入决策相位（流水 63）：注入后消息面在场；缺省＝空段头（回归）；
    **落链恰一次**（2026-10-17 消重批·缺陷一——run 级共享上下文只挂第一次决策装配）。

    接线面：`RunExecutor(guide_text=…)` → 编排 `LoopDeps.guide_text` → 相位 `clarify`／`match`
    → `prompts.assemble_decision_package(guide_text=…)`。特征串「◆ **三链路由**」**只出自
    ontology 指南 §A**（不在任何相位合同常量内——agent-112 已取证）。
    """
    from appv2.api.ontology_guide import OntologyGuideProvider
    from appv2.runtimev2.prompts import GUIDE_REFERENCE_HEAD

    guide_mark = "◆ **三链路由**"
    guide = OntologyGuideProvider(today=date(2026, 10, 8)).guide()
    assert guide_mark in guide  # 前置：特征串确实出自 §A 装载面
    assert guide.count(guide_mark) == 1  # 计数判据前提：特征串在 §A 内唯一

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
                v2_data_match(
                    subtask_id="s1",
                    slot="日产油量",
                    start="2025-09-01",
                    end="2025-09-03",
                )
            ),
        ),
        "answer": ["子任务 s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }

    async def _decision_messages(guide_text: str) -> list[str]:
        wire_ledger_projection(V2LedgerPort(dump))
        with freeze("2026-10-08T09:00:00"):
            runtime, completer = v2_runtime(
                script=script,
                registry=v2_registry(engine=V2QueueEngine([_rows_outcome()])),
                guide_text=guide_text,
            )
            await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
        return [
            "\n".join(str(message.get("content", "")) for message in messages)
            for caller, messages in completer.calls
            if caller == "decision"
        ]

    injected = await _decision_messages(guide)
    assert injected and all(guide_mark in joined for joined in injected)  # §A 全文随注入面在场
    # 落链恰一次（链为追加形：后一调用恒含前一调用全部消息，故计数不随调用序号增长）
    assert all(joined.count(guide_mark) == 1 for joined in injected)
    assert all(joined.count(GUIDE_REFERENCE_HEAD) == 1 for joined in injected)

    plain = await _decision_messages("")
    assert plain  # 决策相位照常发起模型调用
    assert all(guide_mark not in joined for joined in plain)  # 缺省空串＝空段头（回归）
    # 空段头同属 run 级共享上下文：亦只挂第一次决策装配（后一调用零新增段头）
    assert all(joined.count(GUIDE_REFERENCE_HEAD) == 1 for joined in plain)


async def test_decision_shared_context_injected_once_per_run() -> None:
    """缺陷一回归（2026-10-17 消重批）：同一 run 两次决策调用拼出的消息链中，§A 指南正文与台账
    常驻块**各恰出现一次**（挂第一次决策调用=澄清轮首入包），后续决策调用零新增；链仍为
    **前缀延伸**（pin-22／KV 加形纪律——消重不动已有消息），两段文本**字节级不变**（只改次数）。

    真机病根（`docs/runtime-refactor/ladder/L3/07` run-919ed881）：末轮 answer prompt 19359
    tokens 里 §A 全文 2310 chars＋台账全量块 4935 chars 各两遍（澄清包＋匹配包）——约 44% 是纯重复。
    """
    from appv2.runtimev2.prompts import (
        GUIDE_REFERENCE_HEAD,
        RESIDENT_BLOCK_BEGIN,
        RESIDENT_BLOCK_END,
    )
    from appv2.runtimev2.state import RunState

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
                v2_data_match(
                    subtask_id="s1",
                    slot="日产油量",
                    start="2025-09-01",
                    end="2025-09-03",
                )
            ),
        ),
        "answer": ["子任务 s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(
            script=script, registry=v2_registry(engine=V2QueueEngine([_rows_outcome()]))
        )
        events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"

    calls = completer.messages_of("decision")
    assert len(calls) >= 2  # 澄清轮＋匹配轮两次决策调用

    def _count(messages: list[dict[str, str]], needle: str) -> int:
        return sum(str(message.get("content", "")).count(needle) for message in messages)

    for messages in calls:
        assert _count(messages, GUIDE_REFERENCE_HEAD) == 1
        assert _count(messages, RESIDENT_BLOCK_BEGIN) == 1
        assert _count(messages, RESIDENT_BLOCK_END) == 1

    first, second = calls[0], calls[1]
    assert second[: len(first)] == first  # 前链恒为后链前缀（KV 加形纪律不破）
    # 共享上下文挂第一次决策调用（澄清轮首入包）；匹配轮新增消息里两段**零命中**
    added = "\n".join(str(message.get("content", "")) for message in second[len(first) :])
    assert GUIDE_REFERENCE_HEAD not in added
    assert RESIDENT_BLOCK_BEGIN not in added and RESIDENT_BLOCK_END not in added
    # 字节级不变（只改出现次数）：第二次调用链里那一块逐字＝第一次调用链里的同一块
    block_from_first = _slice_block(first)
    block_from_second = _slice_block(second)
    assert block_from_first and block_from_first == block_from_second
    assert RESIDENT_BLOCK_BEGIN + "\n" in block_from_first  # 包裹对完整（BEGIN＋…＋END）
    # 装配面同源核（runs 外）：状态机里澄清相位标记已落（共享上下文唯一挂载点的判据面）
    run_id = events[-1].data["run_id"]
    state = V2RunStore().load(run_id)
    assert isinstance(state, RunState)
    assert state.contracts_appended == ["clarify", "toolmatch"]


def _slice_block(messages: list[dict[str, str]]) -> str:
    """消息链内常驻块整段切片（BEGIN 起 END 止；缺席＝空串）——字节比对件。"""
    from appv2.runtimev2.prompts import RESIDENT_BLOCK_BEGIN, RESIDENT_BLOCK_END

    text = "\n".join(str(message.get("content", "")) for message in messages)
    if RESIDENT_BLOCK_BEGIN not in text or RESIDENT_BLOCK_END not in text:
        return ""
    return text[
        text.index(RESIDENT_BLOCK_BEGIN) : text.index(RESIDENT_BLOCK_END) + len(RESIDENT_BLOCK_END)
    ]


# ---------- L0/L2 三病灶修复批③：直答旁路（route=direct）文本帧 ----------


async def test_four_phase_direct_answer_emits_text_frame() -> None:
    """直答旁路收口后补发一帧交付正文（2026-10-16 补，L0/L2 三病灶修复批③）。

    真机证据 `docs/runtime-refactor/ladder/L0/01`：`route="direct"` 一路六帧（session／step×2／
    verdict／blackbox／done）**无任何 text 帧**、runs 读口无答案正文——免起草旁路（`direct_answer`
    三键）的收口段只发 `citation` 帧，交付正文只落状态不上流，用户端读到空。断言：帧流含**恰一帧**
    text、content＝直答草稿、帧在 `verdict(final)` 之前；帧形不带 kind（照 `answering` 起草段，
    不新造 kind 值）；免起草免核验（零 ask／零 verify 帧、步序＝读题＋收口两拍）。
    """
    from appv2.infra.clock import freeze
    from appv2.runtimev2.persistence import RunStore

    greeting = "好的，不客气！有需要随时叫我。"
    wire_ledger_projection(V2LedgerPort(v2_ledger_dump()))
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script={
                "understand": [
                    json.dumps({"route": "direct", "text": greeting}, ensure_ascii=False)
                ],
            }
        )
        events = await v2_run(runtime, "谢谢")

    names = [event.event for event in events]
    direct_text = [
        (index, event.data) for index, event in enumerate(events) if event.event == "text"
    ]
    assert len(direct_text) == 1  # 恰一帧（不重复推）
    index, payload = direct_text[0]
    assert payload == {"content": greeting}  # 帧形不带 kind（kind 值不新造）
    assert index < names.index("verdict")  # 正文帧在收口 verdict 之前
    assert events[names.index("verdict")].data["subtype"] == "final"
    assert names[-1] == "blackbox"

    # 免起草免核验：零 ask、零 verify 帧；步序＝读题（decision）＋收口（answer）两拍
    assert v2_ask_frames(events) == []
    verdicts = [event.data for event in events if event.event == "verdict"]
    assert [data for data in verdicts if data["subtype"] == "verify"] == []
    run_id = events[-1].data["run_id"]
    row = RunStore().run(run_id)
    assert row is not None and row.status == "completed"
    assert row.answer == greeting  # runs 读口正文（原症状＝读口无答案正文）
    assert [record.step for record in v2_steps(run_id)] == ["decision", "answer"]


async def test_four_phase_no_ledger_hit_report_chain_end_to_end() -> None:
    """流水 66 端到端｜无台账行的**报告内容题**走 knowledge 链交付（真机 `run-18e5d273` 指控题）。

    真机病灶＝「完井液在二开钻进段与三开完井段的密度各是多少？」是报告内容题（台账里**没有**
    这一行），旧闸只认台账名录 → 模型三次诚实发 `完井液密度｜未绑定｜null~null` 三次被拒、
    三轮预算烧光（`docs/runtime-refactor/ladder/L3/01-完井液在二开钻进段与三开-summary.md`）。
    本测用新合法形（槽位段「无台账命中」）把同一题**跑完四相位**：澄清放行（零拒因／零回喂条）
    → 工具匹配 knowledge／`doc_retrieve` → 前置放行 → 检索执行恰一次 → 作答收口交付；并核台账
    名录面零改写（占位形原样随链，下游三块按形取值）。
    """
    dump = v2_ledger_dump()
    registry_names = {
        row.get(key)
        for block, key in (("metrics", "slot"), ("objects", "obj"), ("relations", "rel"))
        for row in dump.get(block) or []
    }
    assert "完井液密度" not in registry_names  # 真机自造名真不在名录（报告内容题）
    no_hit_note = "无台账命中｜未绑定｜null~null"  # 真机 s1 原形（槽位段＝新合法形）
    retrieval = _retrieval_with(
        _fragment_obs("完井液密度：二开钻进段 1.05 g/cm³、三开完井段 1.15 g/cm³。", "frag-wjj-md")
    )
    wire_ledger_projection(V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script={
                "understand": [V2_UNDERSTAND],
                "decision": v2_decision_turn(
                    clarify=v2_decompose(
                        subtask_id="s1",
                        question="完井液在二开钻进段与三开完井段的密度各是多少？",
                        ledger_notes=no_hit_note,
                        chain="knowledge",
                    ),
                    toolmatch=v2_matches(
                        v2_knowledge_match(subtask_id="s1", question="完井液密度 二开 三开")
                    ),
                ),
                "answer": ["完井液密度：二开钻进段 1.05 g/cm³、三开完井段 1.15 g/cm³ [1]。"],
            },
            registry=v2_registry(retrieval=retrieval),
        )
        events = await v2_run(runtime, "完井液在二开钻进段与三开完井段的密度各是多少？")

    # 四相位一路收口：零 ask（不挂起）、零拒因步（真机旧形此处三轮全拒）
    assert events[-1].event == "blackbox"
    assert events[-1].data["status"] == "completed"
    assert v2_ask_frames(events) == []
    run_id = events[-1].data["run_id"]
    rejection_steps = [
        row
        for phase in ("clarify", "toolmatch")
        for row in v2_steps(run_id, phase)
        if row.payload.get("rejection")
    ]
    assert rejection_steps == []  # 澄清／匹配轮零被拒步（真机旧形此处三轮全拒）
    assert not any(
        event.data.get("type") == "budget_converged" for event in events if event.event == "notice"
    )

    # 台账注释形原样随链（零改写）＋知识链真执行恰一次
    state = V2RunStore().load(run_id)
    subtasks = state.question_group["subtasks"]
    assert [item["ledger_notes"] for item in subtasks] == [no_hit_note]
    assert [item["chain"] for item in state.tool_matches] == ["knowledge"]
    assert retrieval.retrieve_calls == 1
    assert "1.05" in (V2RunStore().run(run_id).answer or "")


async def test_four_phase_knowledge_need_full_form_reaches_engine() -> None:
    """L3-02 检索透传断点钉测（runtimev2 到达性）：族提示原样到达引擎 ＋ 题面实体确定性补锚。

    证据源 `docs/runtime-refactor/ladder/L3/02-完井液在二开钻进段与三开-summary.md`：真机 02 号题
    模型发 `retrieval_need={"question":…, "anchors":[…], "family_hints":["completion"]}`，引擎侧只剩
    `{question, anchors}`（族提示被工具匹配相位重建时丢弃——族配额退化成每族 1 席、gold 章被裁）。
    本测把同形（模型只给 `question`／`family_hints`）走完四相位：断言 `FakeRetrievalEngine` 捕获的
    `RetrievalNeed` 族提示到场、题面实体（「渤中 34-5 油田」）由代码确定性补入 anchors，且注入项与
    族提示随定案载荷留痕落 `state.tool_matches`（批量执行输入面同源）。
    """
    dump = v2_ledger_dump()
    retrieval = _retrieval_with(
        _fragment_obs(
            "渤中 34-5 油田完井液密度：二开钻进段 1.05 g/cm³、三开完井段 1.15 g/cm³。",
            "frag-bz345-md",
        )
    )
    need_question = "渤中 34-5 油田完井液在二开钻进段与三开完井段的密度各是多少？"
    wire_ledger_projection(V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script={
                "understand": [V2_UNDERSTAND],
                "decision": v2_decision_turn(
                    clarify=v2_decompose(
                        subtask_id="s1",
                        question=need_question,
                        ledger_notes="无台账命中｜未绑定｜null~null",
                        chain="knowledge",
                    ),
                    toolmatch=v2_matches(
                        {
                            "id": "s1",
                            "chain": "knowledge",
                            "tool": "doc_retrieve",
                            "mention_mode": "executed",
                            "retrieval_need": {
                                "question": need_question,
                                "family_hints": ["completion"],
                            },
                        }
                    ),
                ),
                "answer": [
                    "渤中 34-5 油田完井液密度：二开钻进段 1.05 g/cm³、"
                    "三开完井段 1.15 g/cm³ [1]。"
                ],
            },
            registry=v2_registry(retrieval=retrieval),
        )
        events = await v2_run(runtime, need_question)

    assert events[-1].event == "blackbox"
    assert events[-1].data["status"] == "completed"
    assert retrieval.retrieve_calls == 1
    need = retrieval.needs[0]
    assert need.question == need_question
    assert need.family_hints == ("completion",)  # 病灶 A：旧实现此处为空（族提示被丢）
    assert need.anchors == ("渤中34-5油田", "34-5")  # 模型未填 anchors——代码确定性补锚到达引擎

    # 留痕面：族提示与注入锚随定案载荷落状态（成功路径零补记步——返回值承载，同 `caliber_key` 口径）
    state = V2RunStore().load(events[-1].data["run_id"])
    assert state.tool_matches[0]["retrieval_need"] == {
        "question": need_question,
        "anchors": ["渤中34-5油田", "34-5"],
        "family_hints": ["completion"],
    }
