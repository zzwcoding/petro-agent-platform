"""V2-56 浅探查定稿治理——三层六件钉测（附 F，TDD 红先绿后）。

施工基准＝tickets/v2/V2-56-浅探查定稿治理.md 附 A–G（伪代码照抄，插入位置与
判定次序不变）。病形（V2-54 批 B-正4/C-观察＋Q15 同病形 14 支）：V2-53 闸把
「探查过一次」当通行证（discover_used≥1 即放行）——模型拿 FAQ/口径查询空手
探一下（只留一条 notice 通知）就 finalize 定稿交白卷，能出答案的报告检索
一步未走。修三层：信息到位（附 B 打回带路＋附 D 回炉行路由动词）＋措辞核对
（零改动）＋代码兜底（附 A 闸收紧＋附 C 同款空手探查拒重发＋既有轮次机制）。

钉面（附 F T1–T10；公开行为断言——图节点输入输出/状态，不测内部私有细节）：

- T1 浅探查收紧：FAQ 空手（仅 notice 观察）后 finalize → 拒（V2-53 放行形
  反转）；拒因含兜底段；步标题逐字不变。
- T2 FAQ 命中放行：faq_aux 观察在场 → finalize 放行（定稿标题不变）。
- T3 台账条目卡放行：semantic_query 命中条目卡（非 notice）→ finalize 放行。
- T4 followup 旁路保留：followup_of 非空＋零材料 finalize → 放行。
- T5 同参拒重发：faq_lookup 同参第二次发射 → 整发射拒、不执行工具、不占探查
  预算、拒因含「同参已空手」；首拒免轮。
- T6 换参放行：faq_lookup 换问法 → 正常执行（「第二次用对参数」的门）。
- T7 回炉路由动词：failed 子问题拒因含「未绑定／不在台账」→ 重入指令行尾带
  「→改走 knowledge 链（tool=doc_retrieve）」；不含词面的拒因行零追加。
- T8 空手记录语义：failed／no_hit 后同参重发被拒（指纹已记）；命中后同参复查
  放行（不记录——允许同参复查）。
- T9 带路拒因拼装：前置判定 note 在场＋空手清单在场 → finalize 拒因含数据链
  路由段＋空手清单段＋兜底段（「；」连接单段文本）。
- T10 连环拒占轮收敛（新条件下复验 V2-53 T2）；V2-53 旧钉随动见
  tests/domains/test_v2_v253_zero_probe_gate.py（拒因文本随附 B 函数化修订）。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from appv2.retrieval import RetrievalBundle
from appv2.runtime import AskRequest, RunStore
from appv2.runtime.subtask import parse_question_group
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    QueueQueryEngine,
    drain,
    make_runtime,
)
from tests.domains.test_v2_four_phase import DUMP_STORE, LEDGER_DUMP
from tests.domains.test_v2_react_loop import (
    _fragment_obs,
    _retrieval_with,
    _rows_outcome,
)
from tests.domains.test_v2_v252_five_station import _faq_hit, _FaqFace

# ---------- 剧本罐头（四相位 clarify 面） ----------

_FINALIZE = '{"thought": "材料已足够", "action": "finalize"}'

_FAQ_Q_A = "N-02 井是什么时候投产的？"
_FAQ_Q_B = "N-02 井哪一年投产的？"

# faq_lookup 原问法（T1/T5/T8/T9/T10 空手形——空 FAQ 面＝no_hit 通知形观察）
_FAQ_DISCOVER_A = json.dumps({
    "action": "discover",
    "discovers": [{"tool": "faq_lookup", "args": {"question": _FAQ_Q_A}}],
}, ensure_ascii=False)

# faq_lookup 换问法（T6——同工具不同参＝新尝试，门开着）
_FAQ_DISCOVER_B = json.dumps({
    "action": "discover",
    "discovers": [{"tool": "faq_lookup", "args": {"question": _FAQ_Q_B}}],
}, ensure_ascii=False)

# faq_lookup 缺参发射（T8——bad_args 错误分支＝空手，指纹照记）
_DISCOVER_NOARGS = json.dumps({
    "action": "discover",
    "discovers": [{"tool": "faq_lookup", "args": {}}],
}, ensure_ascii=False)

# knowledge 链分解罐头（回炉改发/继续检索的承接面）
_CLARIFY_KNOWLEDGE = json.dumps({
    "action": "decompose",
    "question_group": {"subtasks": [
        {"id": "s1", "question": "W-111 井投产初期日产油是多少",
         "ledger_notes": "完井报告事实——检索链（台账无此口径）", "chain": "knowledge"},
    ]},
}, ensure_ascii=False)

_TOOLMATCH_KNOWLEDGE = json.dumps({"matches": [
    {"id": "s1", "chain": "knowledge", "tool": "doc_retrieve",
     "retrieval_need": {"question": "W-111 井投产初期日产油是多少"}},
]}, ensure_ascii=False)

# data 链在册未绑定罐头（T7/T9——注采比在 LEDGER_DUMP 系在册未绑定 agg：
# 前置条件机 note＋换链触发面→回炉面 failed 拒因含「在册未绑定」）
_CLARIFY_UNBOUND = json.dumps({
    "action": "decompose",
    "question_group": {"subtasks": [
        {"id": "s1", "question": "渤中 34-5 油田注采比",
         "ledger_notes": "注采比｜unbound｜窗 2025-09-01~2025-09-03", "chain": "data"},
    ]},
}, ensure_ascii=False)

_TOOLMATCH_UNBOUND = json.dumps({"matches": [
    {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
        "metric_slot": "注采比", "ranking": False,
        "window_start": "2025-09-01", "window_end": "2025-09-03"}},
]}, ensure_ascii=False)

_ANSWER_KNOWLEDGE = "W-111 井投产初期日产油 291 方 [1]。"
_ANSWER_FAQ = "N-02 井 2019-06-15 投产 [1]。"

# 附 B 兜底段（恒在段——票面逐字稿）
_FALLBACK_SEGMENT = (
    "先 discover 取得条目（精确名单词），或 decompose 分解走 doc_retrieve 检索执行。"
)
# 附 B 数据链路由段（前置判定绑定拒/台账外形在场段——票面逐字稿）
_ROUTE_SEGMENT = (
    "数据链已被前置判定拒（在册未绑定/台账外）——该指标材料走报告检索："
    "分解时 chain=knowledge、tool=doc_retrieve"
)
# 附 D 回炉行路由动词（票面逐字稿）
_ROUTE_VERB = "→改走 knowledge 链（tool=doc_retrieve）"


class _QuestionFaq:
    """按问句分流命中与否的 FAQ 剧本件（T6 换参门——同工具不同参各判各）。"""

    def __init__(self, hits_by_question: dict[str, list[Any]]) -> None:
        self._hits = hits_by_question
        self.calls: list[str] = []

    def similar(self, question: str, top: int = 3) -> list[Any]:
        self.calls.append(question)
        return list(self._hits.get(question, []))


class _FlakyRetrieval:
    """首调超时二调出数的检索剧本件（T7 反面半——拒因行零追加的对照面）。"""

    def __init__(self, bundle: RetrievalBundle) -> None:
        self._bundle = bundle
        self.calls = 0

    async def retrieve(self, need: Any) -> RetrievalBundle:
        self.calls += 1
        if self.calls == 1:
            raise TimeoutError("boom")
        return self._bundle

    async def graph(self, need: Any) -> RetrievalBundle:
        return self._bundle


async def _run(
    tmp_path: Path,
    script: dict[str, Sequence[str]],
    question: str,
    *,
    faq: Any = None,
    retrieval: Any = None,
    answer: Sequence[str] = (_ANSWER_KNOWLEDGE,),
) -> tuple[list[Any], RunStore, Any, Any]:
    """四相位装配真跑一题（events/store/db/completer 出列——各测试自管 dispose）。"""
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
        faq=faq, retrieval=retrieval,
    )
    store = RunStore(db)
    handle = await runtime.ask(AskRequest(question=question, actor=ACTOR))
    events = await drain(handle)
    return events, store, db, completer


# ---------- T1：浅探查收紧（FAQ 空手后 finalize → 拒——V2-53 放行形反转） ----------


async def test_t1_empty_faq_probe_then_finalize_rejected(tmp_path: Path) -> None:
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问 W-111 井投产初期日产油。\n指标候选：无"],
        "v2.runtime.decision": [
            _FAQ_DISCOVER_A, _FINALIZE, _CLARIFY_KNOWLEDGE, _TOOLMATCH_KNOWLEDGE,
        ],
        "v2.runtime.answer": [_ANSWER_KNOWLEDGE],
    }
    events, store, db, _completer = await _run(
        tmp_path, script, "N-02 井是什么时候投产的？", faq=_FaqFace(),
        retrieval=_retrieval_with(_fragment_obs(
            "W-111 井采用酸压完井，投产初期日产油 291 方。", "f-1")),
    )
    try:
        final = events[-1].data
        assert final["status"] == "completed"
        steps = await store.list_steps(final["run_id"])
        # V2-53 放行形反转：FAQ 空手（discover_used==1、观察仅 notice）后
        # finalize 被拒——拒步恰一、步标题逐字不变（V2-53 格式零改动）。
        rejects = [s for s in steps if "被拒：零探查观察禁定稿" in s.title]
        assert len(rejects) == 1
        assert rejects[0].title == "澄清 r0 被拒：零探查观察禁定稿"
        payload = rejects[0].payload or {}
        # 拒因含兜底段（r0 无前置判定、空手清单已记 faq_lookup——②③两段）。
        assert _FALLBACK_SEGMENT in str(payload["rejection"])
        assert "已空手探查：faq_lookup——禁再试同名同参" in str(payload["rejection"])
        assert "澄清定稿：材料足够——直答收口" not in [s.title for s in steps]
        # 打回后改发分解照常走完检索出数（带路→检索出数全链）。
        run = await store.get_run(final["run_id"])
        assert run is not None and "291" in (run.answer or "")
    finally:
        await db.dispose()


# ---------- T2：FAQ 命中放行（faq_aux 观察在场 → finalize 放行） ----------


async def test_t2_faq_hit_then_finalize_passes(tmp_path: Path) -> None:
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问 N-02 井投产日期。\n指标候选：无"],
        "v2.runtime.decision": [_FAQ_DISCOVER_A, _FINALIZE],
        "v2.runtime.answer": [_ANSWER_FAQ],
    }
    events, store, db, _completer = await _run(
        tmp_path, script, _FAQ_Q_A,
        faq=_FaqFace([_faq_hit("faq-4", _FAQ_Q_A, "2019-06-15 投产。")]),
        answer=[_ANSWER_FAQ],
    )
    try:
        final = events[-1].data
        assert final["status"] == "completed"
        steps = await store.list_steps(final["run_id"])
        # 定稿标题不变（命中卡＝实质观察——闸放行）。
        assert any(s.title == "澄清定稿：材料足够——直答收口" for s in steps)
        assert not [s for s in steps if "被拒" in s.title]
    finally:
        await db.dispose()


# ---------- T3：台账条目卡放行（semantic_query 命中非 notice → finalize 放行） ----------


async def test_t3_semantic_entry_card_then_finalize_passes(tmp_path: Path) -> None:
    sem_discover = json.dumps({
        "action": "discover",
        "discovers": [{"tool": "semantic_query",
                       "args": {"element_name": "日产油量"}}],
    }, ensure_ascii=False)
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问日产油量口径。\n指标候选：日产油量"],
        "v2.runtime.decision": [sem_discover, _FINALIZE],
        "v2.runtime.answer": ["口径见台账条目卡 [1]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
        knowledge=DUMP_STORE,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="日产油量是什么口径", actor=ACTOR)
        )
        events = await drain(handle)
        final = events[-1].data
        assert final["status"] == "completed"
        steps = await store.list_steps(final["run_id"])
        # 条目卡（非 notice）＝实质观察——finalize 放行、定稿标题不变。
        assert any(s.title == "澄清定稿：材料足够——直答收口" for s in steps)
        assert not [s for s in steps if "被拒" in s.title]
    finally:
        await db.dispose()


# ---------- T4：followup 旁路保留（followup_of 非空＋零材料 finalize → 放行） ----------


async def test_t4_followup_run_zero_probe_finalize_bypasses(tmp_path: Path) -> None:
    # 前轮与追问 run 同库（追问播种面经 checkpointer 读前轮线程——多轮测试同法）。
    script_a: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：既要数值也要报告佐证。\n指标候选：日产油量"],
        "v2.runtime.decision": [_CLARIFY_KNOWLEDGE, _TOOLMATCH_KNOWLEDGE],
        "v2.runtime.answer": [_ANSWER_KNOWLEDGE],
    }
    runtime_a, _completer_a, db_a = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_a,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
        retrieval=_retrieval_with(_fragment_obs(
            "W-111 井采用酸压完井，投产初期日产油 291 方。", "f-1")),
    )
    store_a = RunStore(db_a)
    run_id_a = ""
    try:
        handle_a = await runtime_a.ask(
            AskRequest(question="W-111 井投产初期日产油是多少", actor=ACTOR)
        )
        await drain(handle_a)
        run_a = await store_a.get_run(handle_a.run_id)
        assert run_a is not None and run_a.status == "completed"
        run_id_a = handle_a.run_id
    finally:
        await db_a.dispose()

    script_b: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：追问语义。\n指标候选：无"],
        "v2.runtime.decision": [_FINALIZE],  # 追问续跑零材料——旁路放行
        "v2.runtime.answer": ["按前轮材料如实作答。"],
    }
    runtime_b, _completer_b, db_b = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_b,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    store_b = RunStore(db_b)
    try:
        handle_b = await runtime_b.ask(
            AskRequest(question="那它的完井方式呢？", actor=ACTOR,
                       followup_of=run_id_a)
        )
        events_b = await drain(handle_b)
        assert events_b[-1].data["status"] == "completed"
        steps = await store_b.list_steps(handle_b.run_id)
        # 旁路放行：定稿步标题在场，零被拒步（追问语义零触碰）。
        assert any(s.title == "澄清定稿：材料足够——直答收口" for s in steps)
        assert not [s for s in steps if "被拒" in s.title]
    finally:
        await db_b.dispose()


# ---------- T5：同参拒重发（整发射拒、不执行工具、不占探查预算、首拒免轮） ----------


async def test_t5_same_args_empty_probe_rejected(tmp_path: Path) -> None:
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问 W-111 井投产初期日产油。\n指标候选：无"],
        "v2.runtime.decision": [
            _FAQ_DISCOVER_A,   # 首发空手（no_hit）——指纹在记
            _FAQ_DISCOVER_A,   # 同参重发——整发射拒（附 C2）
            _CLARIFY_KNOWLEDGE, _TOOLMATCH_KNOWLEDGE,
        ],
        "v2.runtime.answer": [_ANSWER_KNOWLEDGE],
    }
    faq = _FaqFace()
    events, store, db, completer = await _run(
        tmp_path, script, "N-02 井是什么时候投产的？", faq=faq,
        retrieval=_retrieval_with(_fragment_obs(
            "W-111 井采用酸压完井，投产初期日产油 291 方。", "f-1")),
    )
    try:
        final = events[-1].data
        assert final["status"] == "completed"
        steps = await store.list_steps(final["run_id"])
        rejects = [s for s in steps if "同参已空手" in s.title]
        assert len(rejects) == 1
        assert rejects[0].title == "澄清 r1 被拒：faq_lookup 同参已空手"
        assert "同参已空手" in str((rejects[0].payload or {}).get("rejection", ""))
        # 不执行工具：faq 读缝只被首发消费一次（重发在发射级被拦——零引擎触碰）。
        assert faq.calls == [(_FAQ_Q_A, 3)]
        # 不占探查预算：拒后第三次决策调用合同槽仍是「已用 1 次」（首发耗 1，
        # 拒发零耗）。
        third_call = completer.messages_of("v2.runtime.decision")[2]
        assert "已用 1 次" in str(third_call[-1]["content"])
        # 首拒免轮：拒后分解记 r1（rounds 未被拒发消耗——分解只占其自己的轮）。
        assert any(s.title == "澄清 r1：分解 1 子问题" for s in steps)
    finally:
        await db.dispose()


# ---------- T6：换参放行（faq_lookup 换问法 → 正常执行） ----------


async def test_t6_changed_args_probe_executes(tmp_path: Path) -> None:
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问 N-02 井投产日期。\n指标候选：无"],
        "v2.runtime.decision": [_FAQ_DISCOVER_A, _FAQ_DISCOVER_B, _FINALIZE],
        "v2.runtime.answer": [_ANSWER_FAQ],
    }
    faq = _QuestionFaq({_FAQ_Q_B: [_faq_hit("faq-4", _FAQ_Q_B, "2019-06-15 投产。")]})
    events, store, db, _completer = await _run(
        tmp_path, script, _FAQ_Q_A, faq=faq, answer=[_ANSWER_FAQ],
    )
    try:
        final = events[-1].data
        assert final["status"] == "completed"
        steps = await store.list_steps(final["run_id"])
        # 换参＝新尝试（门开着）：两问法都真执行（faq 恰 2 调），命中后定稿放行。
        assert faq.calls == [_FAQ_Q_A, _FAQ_Q_B]
        assert any(s.title == "澄清定稿：材料足够——直答收口" for s in steps)
        assert not [s for s in steps if "被拒" in s.title]
    finally:
        await db.dispose()


# ---------- T7：回炉路由动词（含词面行尾追加；不含词面零追加） ----------


async def test_t7_rework_line_routing_verb(tmp_path: Path) -> None:
    # 正面半：换链回炉面 failed 拒因含「在册未绑定」→ 重入指令行尾带路由动词。
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：数据问句。\n指标候选：注采比"],
        "v2.runtime.decision": [
            _CLARIFY_UNBOUND, _TOOLMATCH_UNBOUND,
            _CLARIFY_KNOWLEDGE, _TOOLMATCH_KNOWLEDGE,
        ],
        "v2.runtime.answer": ["渤中 34-5 注采比口径见报告 [1]。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
        retrieval=_retrieval_with(_fragment_obs(
            "渤中 34-5 油田注采比按月度注采统计 1.2。", "f-1")),
    )
    try:
        handle = await runtime.ask(
            AskRequest(question="渤中 34-5 油田注采比是多少", actor=ACTOR)
        )
        events = await drain(handle)
        assert events[-1].data["status"] == "completed"
        # decision caller 调用序：clarify r1 → toolmatch → clarify r2（回炉）→ …
        second_clarify = completer.messages_of("v2.runtime.decision")[2]
        instruction = str(second_clarify[-1]["content"])
        # 回炉行在指令内且行尾带路由动词（「→改走 knowledge 链（tool=doc_retrieve）」）。
        assert "回炉：只分解以下失败/缺失子问题" in instruction
        rework_lines = [
            line for line in instruction.splitlines()
            if line.startswith("- [s1]") and "拒因：" in line
        ]
        assert len(rework_lines) == 1
        assert rework_lines[0].endswith(_ROUTE_VERB)
        assert "在册未绑定" in rework_lines[0]
    finally:
        await db.dispose()

    # 反面半：拒因不含词面（上游超时）→ 拒因行零追加（逐行原样）。
    dir_neg = tmp_path / "neg"
    dir_neg.mkdir()
    script_neg: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问 W-111 井投产初期日产油。\n指标候选：无"],
        "v2.runtime.decision": [
            _CLARIFY_KNOWLEDGE, _TOOLMATCH_KNOWLEDGE,
            _CLARIFY_KNOWLEDGE, _TOOLMATCH_KNOWLEDGE,
        ],
        "v2.runtime.answer": [_ANSWER_KNOWLEDGE],
    }
    bundle = RetrievalBundle(
        observations=[_fragment_obs(
            "W-111 井采用酸压完井，投产初期日产油 291 方。", "f-1")],
        window_note="召回 1 支/送窗 1 支",
    )
    runtime_neg, completer_neg, db_neg = await make_runtime(
        dir_neg, engine=QueueQueryEngine([_rows_outcome()]), script=script_neg,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
        retrieval=_FlakyRetrieval(bundle),
    )
    try:
        handle_neg = await runtime_neg.ask(
            AskRequest(question="W-111 井投产初期日产油是多少", actor=ACTOR)
        )
        events_neg = await drain(handle_neg)
        assert events_neg[-1].data["status"] == "completed"
        second_clarify_neg = completer_neg.messages_of("v2.runtime.decision")[2]
        instruction_neg = str(second_clarify_neg[-1]["content"])
        rework_lines_neg = [
            line for line in instruction_neg.splitlines()
            if line.startswith("- [s1]") and "拒因：" in line
        ]
        assert len(rework_lines_neg) == 1
        assert "上游超时" in rework_lines_neg[0]
        assert not rework_lines_neg[0].endswith(_ROUTE_VERB)
        assert _ROUTE_VERB not in instruction_neg
    finally:
        await db_neg.dispose()


# ---------- T8：空手记录语义（failed 记指纹；命中不记——同参复查放行） ----------


async def test_t8_empty_probe_fingerprint_semantics(tmp_path: Path) -> None:
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问 N-02 井投产日期。\n指标候选：无"],
        "v2.runtime.decision": [
            _DISCOVER_NOARGS,   # bad_args 错误分支——空手，指纹在记
            _DISCOVER_NOARGS,   # 同参重发——发射级拒（指纹消费面）
            _FAQ_DISCOVER_A,    # 换参真发射——命中（非 notice）
            _FAQ_DISCOVER_A,    # 同参复查——命中不记录，放行执行
            _FINALIZE,
        ],
        "v2.runtime.answer": [_ANSWER_FAQ],
    }
    faq = _FaqFace([_faq_hit("faq-4", _FAQ_Q_A, "2019-06-15 投产。")])
    events, store, db, _completer = await _run(
        tmp_path, script, _FAQ_Q_A, faq=faq, answer=[_ANSWER_FAQ],
    )
    try:
        final = events[-1].data
        assert final["status"] == "completed"
        steps = await store.list_steps(final["run_id"])
        # failed（bad_args）后同参重发被拒恰一（指纹已记的公开后果面）。
        rejects = [s for s in steps if "同参已空手" in s.title]
        assert len(rejects) == 1
        # 命中后同参复查放行：faq 读缝被真发射消费恰 2 次（第 3/4 两发射）。
        assert faq.calls == [(_FAQ_Q_A, 3), (_FAQ_Q_A, 3)]
        # 全链收口：定稿放行（命中卡在场）、零零探查拒步。
        assert any(s.title == "澄清定稿：材料足够——直答收口" for s in steps)
        assert not [s for s in steps if "被拒：零探查观察禁定稿" in s.title]
    finally:
        await db.dispose()


# ---------- T9：带路拒因拼装（前置判定 note＋空手清单 → 三段单文本） ----------


async def test_t9_rejection_routing_assembly(tmp_path: Path) -> None:
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：数据问句。\n指标候选：注采比"],
        "v2.runtime.decision": [
            _FAQ_DISCOVER_A,        # 空手探查——空手清单段素材
            _CLARIFY_UNBOUND, _TOOLMATCH_UNBOUND,   # 前置判定 note——路由段素材
            _FINALIZE,              # r2 浅探查定稿——拒（三段拼装）
            _CLARIFY_KNOWLEDGE, _TOOLMATCH_KNOWLEDGE,
        ],
        "v2.runtime.answer": ["渤中 34-5 注采比口径见报告 [1]。"],
    }
    events, store, db, _completer = await _run(
        tmp_path, script, "渤中 34-5 油田注采比是多少", faq=_FaqFace(),
        retrieval=_retrieval_with(_fragment_obs(
            "渤中 34-5 油田注采比按月度注采统计 1.2。", "f-1")),
    )
    try:
        final = events[-1].data
        assert final["status"] == "completed"
        steps = await store.list_steps(final["run_id"])
        rejects = [s for s in steps if "被拒：零探查观察禁定稿" in s.title]
        assert len(rejects) == 1
        assert rejects[0].title == "澄清 r1 被拒：零探查观察禁定稿"
        rejection = str((rejects[0].payload or {}).get("rejection", ""))
        # 三段拼装：「；」连接的单段文本——数据链路由段＋空手清单段＋兜底段。
        assert rejection == (
            f"{_ROUTE_SEGMENT}；已空手探查：faq_lookup——禁再试同名同参；"
            f"{_FALLBACK_SEGMENT}"
        )
    finally:
        await db.dispose()


# ---------- T10：连环拒占轮收敛（新条件下复验 V2-53 T2） ----------


async def test_t10_chained_rejects_consume_rounds(tmp_path: Path) -> None:
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问 W-111 井投产初期日产油。\n指标候选：无"],
        "v2.runtime.decision": [
            _FAQ_DISCOVER_A, _FINALIZE, _FINALIZE,
            _CLARIFY_KNOWLEDGE, _TOOLMATCH_KNOWLEDGE,
        ],
        "v2.runtime.answer": [_ANSWER_KNOWLEDGE],
    }
    events, store, db, _completer = await _run(
        tmp_path, script, "W-111 井投产初期日产油是多少", faq=_FaqFace(),
        retrieval=_retrieval_with(_fragment_obs(
            "W-111 井采用酸压完井，投产初期日产油 291 方。", "f-1")),
    )
    try:
        final = events[-1].data
        assert final["status"] == "completed"
        steps = await store.list_steps(final["run_id"])
        # 首拒免轮（r0）＋连环拒自第 2 次起占轮（r1＝rounds+1）——V2-53 T2
        # 收敛公式在新条件下复验。
        rejects = [s.title for s in steps if "被拒：零探查观察禁定稿" in s.title]
        assert rejects == [
            "澄清 r0 被拒：零探查观察禁定稿",
            "澄清 r1 被拒：零探查观察禁定稿",
        ]
        # 占轮面继续：后续分解记 r2。
        assert any(s.title == "澄清 r2：分解 1 子问题" for s in steps)
    finally:
        await db.dispose()


# ---------- 附 C1 指纹单测（同参判定键——逐字 json 指纹；参数改了＝新尝试） ----------


def test_discover_fingerprint_args_sensitive() -> None:
    from appv2.runtime.graph import _discover_fingerprint

    a = _discover_fingerprint("faq_lookup", {"question": "问法一"})
    b = _discover_fingerprint("faq_lookup", {"question": "问法二"})
    c = _discover_fingerprint("semantic_query", {"question": "问法一"})
    assert a != b  # 换参＝新尝试（键不同）
    assert a != c  # 换工具＝新尝试
    # 键序归一：同参不同序同指纹。
    assert _discover_fingerprint(
        "faq_lookup", {"question": "q", "top": 3}
    ) == _discover_fingerprint("faq_lookup", {"top": 3, "question": "q"})


# ---------- 附 F T5 前置：发射罐头合法形自检（解析闭世界——防罐头漂移） ----------


def test_canned_discover_emissions_parse() -> None:
    for canned in (_FAQ_DISCOVER_A, _FAQ_DISCOVER_B, _DISCOVER_NOARGS):
        emission = parse_question_group(canned)
        assert not isinstance(emission, str)
        assert emission.kind == "discover"
        assert len(emission.discovers) == 1
        assert emission.discovers[0].get("tool") == "faq_lookup"
