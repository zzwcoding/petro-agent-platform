"""V2-51 小票批钉测（P-050——软失败域闸＋数-反1 词面门＋数-排2 支配校验）。

票面四验收的钉面：
- 域闸钉（R4·A-正8 形）：data 链题眼井全外于数据链井闭世界（agg.dim_well）＝
  域错成功返回软失败面——前置条件机 note＋换链回炉触发面（V2-43 轨道同轨），
  端到端＝不直答不执行→回炉①→轮 2 换 knowledge 链真检索；单源域对
  （数-界1 形 N-01 ∈ 世界）零误伤；闭世界未接线＝闸静默零漂移；不环钉＝
  坚持 data 链同参再触发＝blocked_refuse 直答终局恰一次。
- 词面门钉（R6·数-反1 形）：模糊时间词（最近/近期/前段时间）＋plan 非空窗→
  确定性改判窗双 null（引擎缺参反问三选一兜底）；真无时间词默认窗直发零误伤
  （test_v2_p039b 既有钉继续看守）；用户已答窗（resume 后）不改判（零误伤）。
- 支配钉（R6·数-排2 形）：drafting 指令面携 plan 支配标记——排名型子问题在
  汇总清单行标注「结论必须从本子问题排名观察支取值」，明细型不标（零噪声）。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from appv2.query import (
    ASKBACK_TIME_CHOICES,
    ASKBACK_TIME_QUESTION,
    LINEAGE_KEY_CALIBER,
    LineageLine,
    QueryOutcome,
)
from appv2.runtime import AskRequest, RunStore
from appv2.tools import (
    CHAIN_SWITCH_HINT,
    STATE_NOTE,
    judge,
    ledger_facts,
)
from appv2.tools.precondition import SubtaskInput
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

_UNDERSTAND = "理解：数据问句。\n指标候选：日产油量"

_WINDOW = {"window_start": "2026-08-01", "window_end": "2026-08-31"}

# 数据链井闭世界夹具（生产＝agg.dim_well 井号集——N/X/Z 系域；W 系井只在
# 报告域——A-正8 形题眼）。
_DATA_WELLS = frozenset({"N-01", "N-09", "X-14", "Z-16", "Z-22"})


def _decompose(payload: dict[str, Any]) -> str:
    return json.dumps({"action": "decompose", **payload}, ensure_ascii=False)


def _matches(items: list[dict[str, Any]]) -> str:
    return json.dumps({"matches": items}, ensure_ascii=False)


# ---------- 域闸判定面钉（A-正8 形点亮／域对零误伤／未接线静默） ----------


def test_v251_domain_gate_judge_face() -> None:
    """域闸判定面：data 链＋题眼井全外于井闭世界＝note＋换链触发（kind=domain）；
    单源域对（N-01）/混合域/无题眼井/未接线/knowledge 链零误伤。"""
    facts = ledger_facts(LEDGER_DUMP)

    hit = judge(
        SubtaskInput(
            "t1", "邻井 W-07 井初期日产油多少？现在呢？", "data",
            plan={"metric_slot": "日产油量", "ranking": False, **_WINDOW},
        ),
        facts,
        data_wells=_DATA_WELLS,
    )
    assert hit.state == STATE_NOTE  # 判定四态不变（note）
    assert hit.chain_switch_trigger is True  # 换链回炉触发面（V2-43 轨道）
    assert hit.chain_switch_kind == "domain"  # 域闸触发面机读标
    assert "W-07" in hit.reason and "数据链井闭世界" in hit.reason
    assert CHAIN_SWITCH_HINT in hit.reason  # 拒因携改链 hint（同轨随行）

    indomain = judge(
        SubtaskInput(
            "t2", "N-01 井去年的日产油量是多少？", "data",
            plan={"metric_slot": "日产油量", "ranking": False, **_WINDOW},
        ),
        facts,
        data_wells=_DATA_WELLS,
    )
    assert indomain.chain_switch_trigger is False  # 单源域对零误伤（数-界1 形）

    mixed = judge(
        SubtaskInput(
            "t3", "N-01 井和 W-07 井的日产油量对比", "data",
            plan={"metric_slot": "日产油量", "ranking": False, **_WINDOW},
        ),
        facts,
        data_wells=_DATA_WELLS,
    )
    assert mixed.chain_switch_trigger is False  # 混合域（部分域对）保守不判

    well_less = judge(
        SubtaskInput(
            "t4", "各井日产油量", "data",
            plan={"metric_slot": "日产油量", "ranking": False, **_WINDOW},
        ),
        facts,
        data_wells=_DATA_WELLS,
    )
    assert well_less.chain_switch_trigger is False  # 无题眼井＝闸辖外

    unwired = judge(
        SubtaskInput(
            "t5", "邻井 W-07 井初期日产油多少？", "data",
            plan={"metric_slot": "日产油量", "ranking": False, **_WINDOW},
        ),
        facts,
    )
    assert unwired.chain_switch_trigger is False  # 闭世界未接线＝闸静默（零漂移）

    knowledge = judge(
        SubtaskInput("t6", "W-07 井初期日产油（报告所载）", "knowledge"),
        facts,
        data_wells=_DATA_WELLS,
    )
    assert knowledge.state == "pass"  # knowledge 链无取数闸面——域闸不辖
    assert knowledge.chain_switch_trigger is False


def test_v251_fuzzy_window_gate_judge_face() -> None:
    """词面门判定面：模糊时间词（最近/近期/前段时间）＋非空窗＝改判标记；
    窗已 null／真无时间词／用户已答窗（window_resolved）＝零误伤。"""
    facts = ledger_facts(LEDGER_DUMP)

    hit = judge(
        SubtaskInput(
            "t1", "最近各井日产油量怎么样？", "data",
            plan={"metric_slot": "日产油量", "ranking": False, **_WINDOW},
        ),
        facts,
    )
    assert hit.fuzzy_window_rewrite is True  # 改判标记（窗双 null 由节点执行）
    assert hit.state == STATE_NOTE  # 判定四态不变（note）
    assert "缺参反问" in hit.reason  # 注记点名引擎兜底去向

    for marker in ("近期", "前段时间"):
        flagged = judge(
            SubtaskInput(
                "t2", f"{marker}各井日产油量怎么样？", "data",
                plan={"metric_slot": "日产油量", "ranking": False, **_WINDOW},
            ),
            facts,
        )
        assert flagged.fuzzy_window_rewrite is True  # 词表三词全覆盖

    nulled = judge(
        SubtaskInput(
            "t3", "最近各井日产油量怎么样？", "data",
            plan={"metric_slot": "日产油量", "ranking": False,
                  "window_start": None, "window_end": None},
        ),
        facts,
    )
    assert nulled.fuzzy_window_rewrite is False  # 窗已 null（合同面已跟）不改判

    no_marker = judge(
        SubtaskInput(
            "t4", "各井日产油量是多少？", "data",
            plan={"metric_slot": "日产油量", "ranking": False, **_WINDOW},
        ),
        facts,
    )
    assert no_marker.fuzzy_window_rewrite is False  # 真无时间词默认窗零误伤

    explicit = judge(
        SubtaskInput(
            "t5", "近 7 天各井日产液量是多少？", "data",
            plan={"metric_slot": "日产液量", "ranking": False, **_WINDOW},
        ),
        facts,
    )
    assert explicit.fuzzy_window_rewrite is False  # 显式窗词非模糊词零误伤

    resolved = judge(
        SubtaskInput(
            "t6", "最近各井日产油量怎么样？", "data",
            plan={"metric_slot": "日产油量", "ranking": False, **_WINDOW},
        ),
        facts,
        window_resolved=True,
    )
    assert resolved.fuzzy_window_rewrite is False  # 用户已答窗（resume 后）不改判

    payload = hit.as_payload()
    assert payload["fuzzy_window_rewrite"] is True  # wire 投影随行（机读锚）
    assert payload["chain_switch_kind"] == ""  # 未绑定轨道缺省标（V2-43 零漂移）


# ---------- 域闸端到端钉（A-正8 形：回炉→换 knowledge 链→真检索） ----------


async def test_v251_domain_gate_end_to_end_refurnace(tmp_path: Path) -> None:
    """A-正8 形端到端：data 链题眼 W-07 全外于井闭世界→不直答不执行（data 引擎
    零调用）→回炉①（机读 notice）→轮 2 换 knowledge 链→doc_retrieve 真执行。"""
    retrieval = _retrieval_with(_fragment_obs(
        "W-07 井初期日产油 291 m³/d，目前递减至 96 m³/d（第十章邻井对照表所载）。",
        "frag-w07-1",
    ))
    engine = FourPhaseEngine([_rows_outcome()])
    clarify_r1 = _decompose({"question_group": {"subtasks": [
        {"id": "s1", "question": "邻井 W-07 井初期日产油多少？现在呢？",
         "ledger_notes": "日产油量｜bound", "chain": "data"},
    ]}})
    toolmatch_r1 = _matches([
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False, **_WINDOW}},
    ])
    clarify_r2 = _decompose({"question_group": {"subtasks": [
        {"id": "s1", "question": "邻井 W-07 井初期日产油多少？现在呢？（据拒因提示换检索链）",
         "ledger_notes": "报告所载——knowledge 链", "chain": "knowledge",
         "tool": "doc_retrieve"},
    ]}})
    toolmatch_r2 = _matches([
        {"id": "s1", "chain": "knowledge", "tool": "doc_retrieve",
         "retrieval_need": {"question": "邻井 W-07 井初期日产油多少？现在呢？"}},
    ])
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1, clarify_r2, toolmatch_r2],
        "v2.runtime.answer": ["W-07 初期 291 m³/d，现 96 m³/d[1]。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=engine, script=script, retrieval=retrieval,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
        data_wells=lambda: _DATA_WELLS,
    )
    try:
        handle = await runtime.ask(AskRequest(
            question="邻井 W-07 井初期日产油多少？现在呢？", actor=ACTOR))
        events = await drain(handle)
        assert events[-1].data["status"] == "completed"
        assert engine.run_calls == 0  # data 引擎零执行（域错预判——软失败未发生）
        assert retrieval.retrieve_calls == 1  # 轮 2 换 knowledge 链真执行
        assert not [e for e in events if e.event == "ask"]  # 回炉非挂起——零 ask 帧
        store = RunStore(db)
        steps = await store.list_steps(events[-1].data["run_id"])
        preconds = _step_payloads(steps, "precondition")
        assert len(preconds) == 2  # 回炉后前置条件机再判恰一次
        first = preconds[0]["verdicts"][0]
        assert first["state"] == STATE_NOTE
        assert first["chain_switch_trigger"] is True
        assert first["chain_switch_kind"] == "domain"  # 域闸触发面（step 断言面）
        assert preconds[0]["chain_switch_marks"]["s1"]  # 换链指纹簿记在场（同轨）
        assert preconds[1]["verdicts"][0]["state"] == "pass"  # 换 knowledge 链放行
        notices = [e.data for e in events if e.event == "notice"]
        reentries = [n for n in notices if n.get("type") == "chain_switch_reentry"]
        assert len(reentries) == 1
        assert "数据链井闭世界" in reentries[0]["content"]  # 域闸措辞（非绑定闸措辞）
        # 回炉①澄清轮携失败子集＋域错拒因＋hint（第 3 次决策调用＝轮 2 澄清）
        round2_clarify = completer.messages_of("v2.runtime.decision")[2][-1]["content"]
        assert "回炉：" in round2_clarify and "s1" in round2_clarify
        assert "数据链井闭世界" in round2_clarify and CHAIN_SWITCH_HINT in round2_clarify
        run_row = await store.get_run(events[-1].data["run_id"])
        assert run_row is not None and "291" in (run_row.answer or "")
    finally:
        await db.dispose()


async def test_v251_domain_gate_insist_same_data_terminal_once(tmp_path: Path) -> None:
    """不环钉：回炉后坚持 data 链同参＝blocked_refuse 直答终局恰一次（域错措辞，
    data 引擎零触碰——V2-43 轨道语义零改动）。"""
    engine = FourPhaseEngine([_rows_outcome()])
    clarify_r1 = _decompose({"question_group": {"subtasks": [
        {"id": "s1", "question": "邻井 W-07 井初期日产油多少？",
         "ledger_notes": "日产油量｜bound", "chain": "data"},
    ]}})
    toolmatch_r1 = _matches([
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False, **_WINDOW}},
    ])
    clarify_r2 = _decompose({"question_group": {"subtasks": [
        {"id": "s1", "question": "邻井 W-07 井初期日产油多少？",
         "ledger_notes": "日产油量｜bound", "chain": "data"},
    ]}})
    toolmatch_r2 = _matches([
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False, **_WINDOW}},
    ])
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1, clarify_r2, toolmatch_r2],
        "v2.runtime.answer": ["（终局面——不应被起草消费）"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
        data_wells=lambda: _DATA_WELLS,
    )
    try:
        handle = await runtime.ask(AskRequest(
            question="邻井 W-07 井初期日产油多少？", actor=ACTOR))
        events = await drain(handle)
        assert events[-1].data["status"] == "completed"
        assert engine.run_calls == 0  # 坚持原链同参——引擎零执行（不环）
        store = RunStore(db)
        steps = await store.list_steps(events[-1].data["run_id"])
        preconds = _step_payloads(steps, "precondition")
        assert len(preconds) == 2
        second = preconds[1]["verdicts"][0]
        assert second["state"] == "blocked_refuse"  # 再判＝直答终局
        assert "换链回炉已用尽" in second["reason"]
        assert "域错如实拒答" in second["reason"]  # 域闸措辞终局
        assert CHAIN_SWITCH_HINT not in second["reason"]  # 终局不带 hint
        run_row = await store.get_run(events[-1].data["run_id"])
        assert run_row is not None
        assert "换链回炉已用尽" in (run_row.answer or "")
        assert not [e for e in events if e.event == "ask"]  # 全程零挂起
    finally:
        await db.dispose()


# ---------- 词面门端到端钉（数-反1 形：非空窗改判 null→引擎缺参反问） ----------


async def test_v251_fuzzy_gate_rewrites_window_engine_askback(tmp_path: Path) -> None:
    """数-反1 形端到端：模型违约直发非空窗（「最近」在场）→前置条件机确定性
    改判窗双 null（引擎收到的计划窗为 null）→引擎缺参反问三选一帧在场。"""
    engine = FourPhaseEngine([
        QueryOutcome.need_clarify(
            question=ASKBACK_TIME_QUESTION, choices=ASKBACK_TIME_CHOICES
        ),
        _rows_outcome(),
    ])
    clarify_r1 = _decompose({"question_group": {"subtasks": [
        {"id": "s1", "question": "最近各井日产油量怎么样？",
         "ledger_notes": "日产油量｜bound", "chain": "data"},
    ]}})
    toolmatch_r1 = _matches([
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2026-08-01", "window_end": "2026-08-31"}},
    ])
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1],
        "v2.runtime.answer": ["（不应被消费——挂起面）"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        handle = await runtime.ask(AskRequest(
            question="最近各井日产油量怎么样？", actor=ACTOR))
        events = await drain(handle)
        asks = [e.data for e in events if e.event == "ask"]
        assert asks, "非空窗未被改判——数-反1 直发形复现"
        assert asks[-1]["frame"]["prompt"] == ASKBACK_TIME_QUESTION  # 引擎兜底
        assert asks[-1]["frame"]["options"] == list(ASKBACK_TIME_CHOICES)
        # 确定性改判实证：引擎收到的计划窗双 null（非模型原发射的非空窗）。
        assert engine.plans, "data 引擎未被调用——改判链路断"
        assert engine.plans[0].window_start is None
        assert engine.plans[0].window_end is None
        store = RunStore(db)
        steps = await store.list_steps(asks[-1]["run_id"])
        preconds = _step_payloads(steps, "precondition")
        assert preconds[0]["verdicts"][0]["fuzzy_window_rewrite"] is True
        toolmatch = _step_payloads(steps, "toolmatch")[0]
        # 相位② step 是模型原发射的历史记录（保留非空窗原样——审计面）；
        # 改写落 state 执行面——引擎收到的计划窗双 null（上方 engine.plans 断言）。
        assert toolmatch["emission"]["matches"][0]["plan"]["window_start"] == "2026-08-01"
        run_row = await store.get_run(asks[-1]["run_id"])
        assert run_row is not None and run_row.status == "waiting_ask"  # 挂起反问
    finally:
        await db.dispose()


# ---------- 支配钉（数-排2 形：drafting 指令面携 plan 支配标记） ----------


async def test_v251_dominance_marker_in_summary_instruction(tmp_path: Path) -> None:
    """数-排2 形：排名型子问题在汇总清单行携「排名观察支取值」支配标记；
    明细型子问题不标（零噪声）。"""
    engine = FourPhaseEngine([
        _rows_outcome(),  # s1 明细
        QueryOutcome.rows_with_lineage(
            columns=(("well_id", "井号"), ("日产油量合计（吨）", "日产油量合计（吨）")),
            rows=(
                {"well_id": "Z-22", "日产油量合计（吨）": Decimal("1784.67")},
                {"well_id": "N-09", "日产油量合计（吨）": Decimal("1851.55")},
            ),
            lineage=(
                LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量（单位：吨）——口径声明"),
            ),
        ),  # s2 排名
    ])
    clarify_r1 = _decompose({"question_group": {"subtasks": [
        {"id": "s1", "question": "去年各井每天的日产油量",
         "ledger_notes": "日产油量｜bound", "chain": "data"},
        {"id": "s2", "question": "去年日产油量最低的两口井是哪两口？",
         "ledger_notes": "日产油量｜bound｜排名", "chain": "data"},
    ]}})
    toolmatch_r1 = _matches([
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2025-01-01", "window_end": "2026-01-01"}},
        {"id": "s2", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": True, "direction": "asc",
            "window_start": "2025-01-01", "window_end": "2026-01-01"}},
    ])
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1],
        "v2.runtime.answer": ["s2：Z-22、N-09[1]。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        handle = await runtime.ask(AskRequest(
            question="去年日产油量最低的两口井是哪两口？", actor=ACTOR))
        events = await drain(handle)
        assert events[-1].data["status"] == "completed"
        answer_call = completer.messages_of("v2.runtime.answer")[0][-1]["content"]
        # 支配标记在排名支清单行（排名型→排名观察支），明细支零标记（零噪声）。
        assert "[s2]" in answer_call and "排名观察支" in answer_call
        s2_line = next(line for line in answer_call.splitlines() if "[s2]" in line)
        assert "排名" in s2_line and "排名观察支" in s2_line
        s1_line = next(line for line in answer_call.splitlines() if "[s1]" in line)
        assert "排名观察支" not in s1_line
    finally:
        await db.dispose()


def test_v251_drafting_instruction_clauses_present() -> None:
    """指令面合同钉：SUMMARY_CONTRACT 携排名支配句；起草指令携台账卡非数据源句。"""
    from appv2.runtime.graph import _ANSWER_INSTRUCTION
    from appv2.runtime.guide import SUMMARY_CONTRACT

    assert "排名型子问题" in SUMMARY_CONTRACT and "排名观察支" in SUMMARY_CONTRACT
    assert "台账卡" in _ANSWER_INSTRUCTION and "拼装" in _ANSWER_INSTRUCTION


def test_v251_data_wells_reader_schema_pinned() -> None:
    """读缝 schema 钉：agg.dim_well 带 schema 限定（agg 星型不在默认 search_path
    ——裸表名＝UndefinedTableError→runtime 吞空集闸静默（P050CA8 首批实录：
    域闸生产面静默的根因）。"""
    from appv2.query.pg_wells import _DIM_WELL, production_data_wells

    assert _DIM_WELL.schema == "agg"
    assert callable(production_data_wells(()))
