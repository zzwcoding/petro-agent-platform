"""P-039/V2-41 检索域合同修补＋名归一闸钉测（九验收的钉面）。

票面验收钉测落点：
- 合同零业务名词 grep 硬项：四份发射合同（DECISION/CLARIFY/TOOLMATCH/SUMMARY）
  扫井号形/报告名书名号/数字段/台账真源（快照 metrics/terms/aliases）汉字连串——
  检出任何一类即红（过拟合防线——合同措辞不得携带业务事实）；
- 附 1/附 2 逐字在场（票面施工基准——现有措辞零删改防双合同面漂移）；
- F1 断裂①钉：retrieval_need 三键（question 必填/anchors/family_hints）——
  三键通过／缺 question 仍拒／造键在 doc_retrieve args_schema 拒（闭世界）；
- F2 三态钉＋反向钉：检索语境 knowledge 直发零 ask／口径歧义走前置条件机
  caliber 反问不走 clarify ask／无时间词默认锚定（窗双 null 由引擎缺参反问
  兜底）／真歧义反问白场仍通（P-033c 先例不回退）；
- 改链建议钉：在册闸/绑定闸拒因携 knowledge 备选 hint（附 3 逐字尾缀）——
  全部拦截直答剥除 hint（直答是终局）、混合路径保留、回炉重决策换链执行；
- F7 名归一钉（附 4 真值对）：normalize 确定性／「注采比」命中「☆注采比 β」
  归一 slot（判定面＋执行面 plan 改写双钉）／「日产油量」恒等路径／乱造名
  全未命中仍拒。
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from appv2.query import (
    ASKBACK_TIME_QUESTION,
    PlanCheck,
    QueryOutcome,
)
from appv2.runtime import AskChoice, AskRequest, RunStore
from appv2.runtime.guide import (
    CLARIFY_CONTRACT,
    DECISION_CONTRACT,
    SUMMARY_CONTRACT,
    TOOLMATCH_CONTRACT,
)
from appv2.runtime.subtask import parse_tool_match
from appv2.tools import (
    CHAIN_SWITCH_HINT,
    DOC_RETRIEVE,
    FakeKnowledgeStore,
    FakeQueryEngine,
    FakeRetrievalEngine,
    ToolContext,
    ToolRegistry,
    judge,
    ledger_facts,
    normalize_metric_name,
    resolve_metric_slot,
)
from appv2.tools.precondition import (
    STATE_BLOCKED_ASK,
    STATE_BLOCKED_REFUSE,
    STATE_NOTE,
    SubtaskInput,
)
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    drain,
    make_runtime,
)
from tests.domains.test_v2_four_phase import (
    LEDGER_DUMP,
    FourPhaseEngine,
    _step_payloads,
)
from tests.domains.test_v2_react_loop import (
    _fragment_obs,
    _retrieval_with,
    _rows_outcome,
)

# ---------- 附 1/附 2 逐字基准（票面施工基准照抄——增删一字即红） ----------

ATTACH_1 = (
    "retrieval_need 形（knowledge 链必带，键名逐字）：{\"question\": \"检索问句原文"
    "（必填非空——逐字转抄该子问题的 question）\", \"anchors\": [\"锚点词\", …]"
    "（可选——井号/报告名/章节等精确定位词）, \"family_hints\": [\"completion\"|"
    "\"monthly\"|\"dynamic\"|\"blank\"]（可选——族机器名，不要写中文名）}"
    "——缺 question＝参数校验拒；只许这三个键，禁造键名。"
)

ATTACH_2 = (
    "knowledge 链规则：问文档所载内容（非台账指标的数值取数）＝单子问题组直发"
    "（chain=knowledge, tool=doc_retrieve）——不问范围、不问载体（全库检索"
    "是合同口径，路由建议已代选库）、不问口径支；口径支歧义不归本相位——"
    "由前置条件机按 caliber_key 三态处理（双口径并列或阈值反问）；检索式"
    "问题没有「窗」概念——缺窗不是歧义、不构成反问白场；无时间词的数据链"
    "问题＝默认近 30 天直发，禁反问时间窗（窗双 null 由引擎缺参反问兜底）。"
)


def test_p039_contracts_append_verbatim_and_old_wording_intact() -> None:
    """附 1/附 2 逐字在场＋现有措辞零删改（施工红线——只许追加两段）。"""
    assert ATTACH_1 in TOOLMATCH_CONTRACT
    assert ATTACH_2 in CLARIFY_CONTRACT
    # 现有措辞一字不删（追加前的收尾句原样在场——双合同面漂移防线）。
    assert "缺 ranking 等必填键＝参数校验拒。" in TOOLMATCH_CONTRACT
    assert "不预判、不对窗/粒度反问）。" in CLARIFY_CONTRACT
    assert "禁再 discover" in CLARIFY_CONTRACT  # P-033c 对称面不回退
    assert TOOLMATCH_CONTRACT.index(ATTACH_1) > TOOLMATCH_CONTRACT.index("plan 形")
    assert CLARIFY_CONTRACT.index(ATTACH_2) > CLARIFY_CONTRACT.index("发射判据")


def test_p039_contract_zero_business_nouns_grep() -> None:
    """合同零业务名词 grep 硬项：井号形/报告名书名号/数字段/台账真源汉字连串。

    名词宇宙＝台账快照真源（metrics slot+name／terms／aliases——零发明：与
    前置条件机同一份夹具真源）；汉字连串按 ≥2 字提取（「☆注采比 β」抽出
    「注采比」，防装饰符残缺形漏检）。检出任何一类＝打回。
    """
    texts = {
        "DECISION_CONTRACT": DECISION_CONTRACT,
        "CLARIFY_CONTRACT": CLARIFY_CONTRACT,
        "TOOLMATCH_CONTRACT": TOOLMATCH_CONTRACT,
        "SUMMARY_CONTRACT": SUMMARY_CONTRACT,
    }
    nouns: list[str] = []
    for metric in LEDGER_DUMP.get("metrics") or []:
        nouns += [str(metric.get("slot") or ""), str(metric.get("name") or "")]
    for term in LEDGER_DUMP.get("terms") or []:
        nouns.append(str(term.get("term") or ""))
    nouns += [str(alias) for alias in (LEDGER_DUMP.get("aliases") or {})]
    han_runs = sorted({
        run for noun in nouns for run in re.findall(r"[\u4e00-\u9fff]{2,}", noun)
    })
    assert han_runs, "台账真源抽空——夹具断了（测试自身失效）"
    for name, text in texts.items():
        assert not re.search(r"[A-Z]{1,3}-\d{1,4}", text), f"{name} 检出井号形"
        assert "《" not in text and "》" not in text, f"{name} 检出报告名书名号"
        assert not re.search(r"\d{1,4}-\d{1,2}", text), f"{name} 检出数字段（井号/报告名形）"
        leaked = [run for run in han_runs if run in text]
        assert not leaked, f"{name} 检出台账指标/术语名：{leaked}"


# ---------- F1 断裂①钉（retrieval_need 三键——合同与 schema 两面） ----------


def _group_of_two() -> Any:
    from appv2.runtime.subtask import parse_question_group

    raw = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "q1", "ledger_notes": "n1",
             "chain": "knowledge", "tool": "doc_retrieve"},
        ]},
    }, ensure_ascii=False)
    parsed = parse_question_group(raw)
    assert not isinstance(parsed, str) and parsed.group is not None
    return parsed.group


def test_p039_f1_retrieval_need_three_keys_pass_and_missing_question_rejects() -> None:
    """三键形（question 必填＋anchors/family_hints 可选）通过；缺 question 仍拒。"""
    group = _group_of_two()
    matches = parse_tool_match(json.dumps({"matches": [{
        "id": "s1", "chain": "knowledge", "tool": "doc_retrieve",
        "retrieval_need": {"question": "检索问句原文", "anchors": ["锚点词"],
                            "family_hints": ["completion"]},
    }]}, ensure_ascii=False), group)
    assert not isinstance(matches, str)
    assert matches[0].retrieval_need == {
        "question": "检索问句原文", "anchors": ["锚点词"], "family_hints": ["completion"],
    }

    missing = parse_tool_match(json.dumps({"matches": [{
        "id": "s1", "chain": "knowledge", "tool": "doc_retrieve",
        "retrieval_need": {"anchors": ["锚点词"]},
    }]}, ensure_ascii=False), group)
    assert isinstance(missing, str) and "question" in missing


async def test_p039_f1_invented_key_rejected_at_doc_retrieve_schema() -> None:
    """造键拒（断裂③——模型自由发挥造键在 args_schema 闭世界确定性拒）。"""
    registry = ToolRegistry(
        knowledge=FakeKnowledgeStore(),
        query=FakeQueryEngine(),
        retrieval=FakeRetrievalEngine(),
    )
    ctx = ToolContext(actor=ACTOR.user_id, budget=4)
    invented = await registry.call(
        DOC_RETRIEVE, {"question": "q", "term_hints": ["x"]}, ctx
    )
    assert invented.status == "failed" and invented.error is not None
    assert "未知参数键" in invented.error.message
    assert "term_hints" in invented.error.message

    # 三键合法形照常通过（同一出口——闭世界只拒造键不拒三键）。
    ok = await registry.call(
        DOC_RETRIEVE,
        {"question": "q", "anchors": ["a"], "family_hints": ["completion"]}, ctx,
    )
    assert ok.status == "ok"


# ---------- F2 三态钉＋反向钉（e2e 剧本——行为形状锁） ----------


_UNDERSTAND = "理解：检索问句。\n指标候选：无"

_CLARIFY_KNOWLEDGE_DIRECT = json.dumps({
    "action": "decompose",
    "question_group": {"subtasks": [
        {"id": "s1", "question": "报告所载内容问句（检索式——无台账数值取数）",
         "ledger_notes": "文档事实——检索链直发（附 2：不问范围/载体/口径支）",
         "chain": "knowledge", "tool": "doc_retrieve"},
    ]},
}, ensure_ascii=False)

_TOOLMATCH_KNOWLEDGE = json.dumps({"matches": [{
    "id": "s1", "chain": "knowledge", "tool": "doc_retrieve",
    "retrieval_need": {"question": "报告所载内容问句（检索式）",
                        "anchors": ["锚点词"], "family_hints": ["monthly"]},
}]}, ensure_ascii=False)


async def test_p039_f2_knowledge_direct_dispatch_zero_ask(tmp_path: Path) -> None:
    """检索语境 knowledge 直发（附 2a）：分解直发零反问——不问范围/载体/口径支。"""
    retrieval = _retrieval_with(_fragment_obs("文档片段内容。", "frag-1"))
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [_CLARIFY_KNOWLEDGE_DIRECT, _TOOLMATCH_KNOWLEDGE],
        "v2.runtime.answer": ["文档片段内容[1]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=FakeQueryEngine(), script=script, retrieval=retrieval,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_all(runtime, "检索式问题")
        assert events[-1].data["status"] == "completed"
        assert not [e for e in events if e.event == "ask"], "检索语境出现反问帧"
        assert retrieval.retrieve_calls == 1
        need = retrieval.needs[0]
        assert need.question == "报告所载内容问句（检索式）"
        assert need.family_hints == ("monthly",) or need.family_hints == ["monthly"]
    finally:
        await db.dispose()


async def _run_all(runtime: Any, question: str) -> list[Any]:
    handle = await runtime.ask(AskRequest(question=question, actor=ACTOR))
    return await drain(handle)


async def test_p039_f2_caliber_ambiguity_goes_to_precondition_not_clarify(
    tmp_path: Path,
) -> None:
    """口径歧义走前置条件机 caliber 三态（附 2b）——clarify 发射是分解不是反问。"""
    engine = FourPhaseEngine([_rows_outcome(), _rows_outcome()])
    clarify_r1 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "各井含水率是否超过 30",
             "ledger_notes": "含水率｜双口径支 A/B（阈值形——前置条件机反问）",
             "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r1 = json.dumps({"matches": [{
        "id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "含水率", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"},
    }]}, ensure_ascii=False)
    clarify_r2 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "各井含水率月报口径是否超过 30",
             "ledger_notes": "含水率｜口径支 B（场景词已答）", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r2 = json.dumps({"matches": [{
        "id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "含水率", "ranking": False, "caliber_key": "B",
            "window_start": "2025-09-01", "window_end": "2025-09-03"},
    }]}, ensure_ascii=False)
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1, clarify_r2, toolmatch_r2],
        "v2.runtime.answer": ["各井含水率 21.4%[1]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_all(runtime, "含水率阈值题")
        asks = [e.data for e in events if e.event == "ask"]
        assert asks and asks[-1]["frame"]["kind"] == "clarify"
        assert "按哪一口径支判断" in asks[-1]["frame"]["prompt"]  # 前置条件机的口径反问
        store = RunStore(db)
        steps = await store.list_steps(asks[-1]["run_id"])
        clarify_steps = _step_payloads(steps, "clarify")
        assert clarify_steps[0]["emission"]["action"] == "decompose"  # clarify 不反问口径
        verdicts = _step_payloads(steps, "precondition")[0]["verdicts"]
        assert verdicts[0]["state"] == STATE_BLOCKED_ASK
        # 用户选定口径支——续跑收口。
        handle = await runtime.resume(asks[-1]["run_id"], AskChoice(value="B 检修剔除"))
        events2 = await drain(handle)
        assert events2[-1].data["status"] == "completed"
    finally:
        await db.dispose()


async def test_p039_f2_window_null_engine_askback_fallback(tmp_path: Path) -> None:
    """无时间词默认锚定（附 2c）：clarify 不反问窗——窗双 null 由引擎缺参反问兜底。"""
    engine = FourPhaseEngine([
        QueryOutcome.need_clarify(
            question=ASKBACK_TIME_QUESTION, choices=(("近 7 天"), ("近 30 天"))
        ),
        _rows_outcome(),
    ])
    clarify_r1 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "各井日产油量（无时间词——默认近 30 天直发面）",
             "ledger_notes": "日产油量｜bound｜无时间词", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r1 = json.dumps({"matches": [{
        "id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": None, "window_end": None},
    }]}, ensure_ascii=False)
    clarify_r2 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "近 30 天各井日产油量",
             "ledger_notes": "日产油量｜bound｜窗已答", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r2 = json.dumps({"matches": [{
        "id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2026-08-01", "window_end": "2026-08-31"},
    }]}, ensure_ascii=False)
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1, clarify_r2, toolmatch_r2],
        "v2.runtime.answer": ["N-01 21.16[1]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_all(runtime, "各井日产油量")
        asks = [e.data for e in events if e.event == "ask"]
        assert asks and asks[-1]["frame"]["prompt"] == ASKBACK_TIME_QUESTION  # 引擎兜底
        store = RunStore(db)
        steps = await store.list_steps(asks[-1]["run_id"])
        clarify_steps = _step_payloads(steps, "clarify")
        assert clarify_steps[0]["emission"]["action"] == "decompose"  # clarify 未反问窗
        from appv2.runtime import AskChoice

        handle = await runtime.resume(asks[-1]["run_id"], AskChoice(value="近 30 天"))
        events2 = await drain(handle)
        assert events2[-1].data["status"] == "completed"
    finally:
        await db.dispose()


async def test_p039_f2_true_ambiguity_ask_white_field_still_open(tmp_path: Path) -> None:
    """反向钉：目标/对象真歧义反问白场仍通（P-033c 先例不回退）——挂起＋续跑收口。"""
    engine = FourPhaseEngine([_rows_outcome()])
    clarify_ask = json.dumps({
        "action": "ask",
        "ask": {"prompt": "「它」指哪一口井？", "options": ["N-01", "Z-16"]},
    }, ensure_ascii=False)
    clarify_r2 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "N-01 井 2025-09-01 日产油量",
             "ledger_notes": "日产油量｜bound｜用户已答对象", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r2 = json.dumps({"matches": [{
        "id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-02"},
    }]}, ensure_ascii=False)
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_ask, clarify_r2, toolmatch_r2],
        "v2.runtime.answer": ["N-01 21.16[1]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_all(runtime, "它的日产油量是多少？")
        asks = [e.data for e in events if e.event == "ask"]
        assert asks and asks[-1]["frame"]["kind"] == "clarify"
        assert asks[-1]["frame"]["prompt"] == "「它」指哪一口井？"  # 真歧义白场原样
        store = RunStore(db)
        run_row = await store.get_run(asks[-1]["run_id"])
        assert run_row is not None and run_row.status == "waiting_ask"
        handle = await runtime.resume(asks[-1]["run_id"], AskChoice(value="N-01"))
        events2 = await drain(handle)
        assert events2[-1].data["status"] == "completed"
    finally:
        await db.dispose()


# ---------- 改链建议钉（附 3——拒因携 hint＋直答剥除＋回炉换链） ----------


def test_p039_chain_switch_hint_on_ledger_and_binding_gates_only() -> None:
    """在册闸/绑定闸拦停拒因携 hint（附 3 逐字尾缀）；N1 禁用词拒不带。"""
    facts = ledger_facts(LEDGER_DUMP)
    window = {"window_start": "2025-09-01", "window_end": "2025-09-03"}

    refuse = judge(SubtaskInput(
        "g1", "各井采出程度", "data",
        plan={"metric_slot": "采出程度", "ranking": False, **window},
    ), facts)
    assert refuse.state == STATE_BLOCKED_REFUSE
    assert refuse.reason.endswith(CHAIN_SWITCH_HINT)  # 拒因尾部追加（附 3 位置）

    unbound = judge(SubtaskInput(
        "g2", "各井含水率", "data",
        plan={"metric_slot": "含水率", "ranking": False, **window},
    ), facts)
    assert unbound.state == STATE_NOTE
    assert CHAIN_SWITCH_HINT in unbound.reason  # 绑定闸（在册未绑定）同样携带

    banned = judge(SubtaskInput(
        "g3", "各井老完成率", "data",
        plan={"metric_slot": "老完成率", "ranking": False, **window},
    ), facts)
    assert banned.state == STATE_BLOCKED_REFUSE
    assert CHAIN_SWITCH_HINT not in banned.reason  # 禁用词拒（终局语义）不带 hint


async def test_p039_hint_stripped_on_all_refused_direct_answer(tmp_path: Path) -> None:
    """blocked_refuse 直答路径剥除 hint（附 3——直答是终局）；判定面拒因仍携。"""
    clarify_r1 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "各井采出程度",
             "ledger_notes": "采出程度｜不在台账", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r1 = json.dumps({"matches": [{
        "id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "采出程度", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"},
    }]}, ensure_ascii=False)
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=FourPhaseEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_all(runtime, "采出程度题")
        assert events[-1].data["status"] == "completed"
        store = RunStore(db)
        run_row = await store.get_run(events[-1].data["run_id"])
        assert run_row is not None
        assert CHAIN_SWITCH_HINT not in (run_row.answer or "")  # 直答不带 hint
        verdicts = _step_payloads(await store.list_steps(run_row.run_id), "precondition")
        assert verdicts[0]["verdicts"][0]["reason"].endswith(CHAIN_SWITCH_HINT)
    finally:
        await db.dispose()


async def test_p039_hint_kept_on_mixed_path_and_seen_by_answer_phase(
    tmp_path: Path,
) -> None:
    """混合路径（拒答＋可执行并存）hint 保留——汇总相位指令可见（非直答终局）。"""
    retrieval = _retrieval_with(_fragment_obs("文档片段。", "frag-1"))
    clarify_r1 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "各井采出程度",
             "ledger_notes": "采出程度｜不在台账", "chain": "data"},
            {"id": "s2", "question": "报告里的相关记载",
             "ledger_notes": "文档事实——检索链", "chain": "knowledge",
             "tool": "doc_retrieve"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r1 = json.dumps({"matches": [
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "采出程度", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
        {"id": "s2", "chain": "knowledge", "tool": "doc_retrieve",
         "retrieval_need": {"question": "报告里的相关记载"}},
    ]}, ensure_ascii=False)
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1],
        "v2.runtime.answer": ["s1 已拒答；s2 文档片段[1]。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=FakeQueryEngine(), script=script, retrieval=retrieval,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_all(runtime, "混合题")
        assert events[-1].data["status"] == "completed"
        answer_calls = completer.messages_of("v2.runtime.answer")
        assert answer_calls
        instruction = str(answer_calls[0][-1].get("content", ""))
        assert CHAIN_SWITCH_HINT in instruction  # 拒因携 hint 进汇总面（非直答）
    finally:
        await db.dispose()


async def test_p039_refurnace_redecides_with_knowledge_chain(tmp_path: Path) -> None:
    """回炉重决策换链执行：data 链被在册闸拦（拒因携 hint）＋同组执行失败回炉
    ——轮 2 换 knowledge 链重分解，doc_retrieve 真执行收口。"""
    retrieval = _retrieval_with(_fragment_obs("文档载有答案。", "frag-1"))
    engine = FakeQueryEngine(
        check=PlanCheck(ok=False, reason="引擎台账校验拒（剧本）"),
    )
    clarify_r1 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "各井采出程度",
             "ledger_notes": "采出程度｜不在台账", "chain": "data"},
            {"id": "s2", "question": "各井日产油量",
             "ledger_notes": "日产油量｜bound", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r1 = json.dumps({"matches": [
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "采出程度", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
        {"id": "s2", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
    ]}, ensure_ascii=False)
    clarify_r2 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "各井采出程度（据拒因提示换检索链）",
             "ledger_notes": "文档所载——knowledge 链", "chain": "knowledge",
             "tool": "doc_retrieve"},
            {"id": "s2", "question": "各井日产油量（据拒因提示换检索链）",
             "ledger_notes": "文档所载——knowledge 链", "chain": "knowledge",
             "tool": "doc_retrieve"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r2 = json.dumps({"matches": [
        {"id": "s1", "chain": "knowledge", "tool": "doc_retrieve",
         "retrieval_need": {"question": "各井采出程度"}},
        {"id": "s2", "chain": "knowledge", "tool": "doc_retrieve",
         "retrieval_need": {"question": "各井日产油量"}},
    ]}, ensure_ascii=False)
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1, clarify_r2, toolmatch_r2],
        "v2.runtime.answer": ["文档载有答案[1]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script, retrieval=retrieval,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_all(runtime, "回炉换链题")
        assert events[-1].data["status"] == "completed"
        assert retrieval.retrieve_calls == 2  # 轮 2 双支都走 doc_retrieve（换链执行）
        assert engine.validate_calls == 1  # 轮 1 data 引擎被拒一次；轮 2 零 data 发射
        store = RunStore(db)
        steps = await store.list_steps(events[-1].data["run_id"])
        verdicts_r1 = _step_payloads(steps, "precondition")[0]["verdicts"]
        assert verdicts_r1[0]["reason"].endswith(CHAIN_SWITCH_HINT)  # 拒因携 hint 在场
    finally:
        await db.dispose()


# ---------- F7 名归一钉（附 4 真值对——判定面＋执行面） ----------


def test_p039_f7_normalize_deterministic() -> None:
    """附 4 normalize：删装饰符→去首尾空白→连续空白收 1→小写拉丁。"""
    assert normalize_metric_name("☆注采比 β") == "注采比 β"
    assert normalize_metric_name("★产量完成率") == "产量完成率"
    assert normalize_metric_name("☆措施有效率 η") == "措施有效率 η"
    assert normalize_metric_name("  A  B  ") == "a b"
    assert normalize_metric_name("＊REC＊") == "rec"


def test_p039_f7_resolve_truth_pairs() -> None:
    """真值对：「注采比」命中「☆注采比 β」归一 slot；恒等路径；乱造名全未命中。"""
    facts = ledger_facts(LEDGER_DUMP)
    assert resolve_metric_slot(facts, "注采比") == "注采比 β"  # token 子集命中（附 4）
    assert resolve_metric_slot(facts, "日产油量") == "日产油量"  # 精确键恒等路径
    assert resolve_metric_slot(facts, "产量完成率") == "产量完成率"  # 装饰符相等命中
    assert resolve_metric_slot(facts, "不存在的指标") is None  # 全未命中（语义不变）
    assert resolve_metric_slot(facts, "躺井率") is None  # 未登记指标仍不代答
    assert resolve_metric_slot(facts, "   ") is None  # 空串不硬凑


def test_p039_f7_judge_normalizes_reports_slot_and_keeps_miss_refusal() -> None:
    """判定面：归一命中不拒（note 携归一注记＋normalized_slot）；全未命中仍拒。"""
    facts = ledger_facts(LEDGER_DUMP)
    window = {"window_start": "2025-09-01", "window_end": "2025-09-03"}

    hit = judge(SubtaskInput(
        "n1", "渤中 34-5 油田注采比", "data",
        plan={"metric_slot": "注采比", "ranking": False, **window},
    ), facts)
    assert hit.state == STATE_NOTE  # 归一命中（未绑定注记随行——不拒）
    assert hit.normalized_slot == "注采比 β"
    assert any("归一" in n and "注采比 β" in n for n in hit.notes)

    identity = judge(SubtaskInput(
        "n2", "各井日产油量", "data",
        plan={"metric_slot": "日产油量", "ranking": False, **window},
    ), facts)
    assert identity.normalized_slot == ""  # 精确键命中——零归一注记

    miss = judge(SubtaskInput(
        "n3", "各井不存在的指标", "data",
        plan={"metric_slot": "不存在的指标", "ranking": False, **window},
    ), facts)
    assert miss.state == STATE_BLOCKED_REFUSE  # 全未命中语义不变
    assert miss.normalized_slot == ""


async def test_p039_f7_e2e_plan_rewritten_to_ledger_slot(tmp_path: Path) -> None:
    """执行面：命中归一的 plan.metric_slot 改写为台账 slot——引擎按 slot 精确命中。"""
    engine = FourPhaseEngine([_rows_outcome()], slots=frozenset({"注采比 β"}))
    clarify_r1 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "渤中 34-5 油田注采比",
             "ledger_notes": "注采比｜登记名☆注采比 β", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r1 = json.dumps({"matches": [{
        "id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "注采比", "ranking": False,
            "window_start": "2026-08-01", "window_end": "2026-08-31"},
    }]}, ensure_ascii=False)
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1],
        "v2.runtime.answer": ["注采比 0.98[1]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_all(runtime, "注采比题")
        assert events[-1].data["status"] == "completed"
        assert engine.run_calls == 1
        assert engine.plans[0].metric_slot == "注采比 β"  # 归一 slot 进执行面
        store = RunStore(db)
        steps = await store.list_steps(events[-1].data["run_id"])
        verdicts = _step_payloads(steps, "precondition")[0]["verdicts"]
        assert verdicts[0]["normalized_slot"] == "注采比 β"
        toolmatch = _step_payloads(steps, "toolmatch")[0]
        assert toolmatch["emission"]["matches"][0]["plan"]["metric_slot"] == "注采比"
    finally:
        await db.dispose()
