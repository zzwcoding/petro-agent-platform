"""P-040/V2-43 换链回炉闸钉测（Owner 方案 A——P-039 疑点 3 拍板落地）。

票面四验收的钉面：
- B-反3 形端到端（剧本）：data 链＋指标在册（F7 归一后）＋绑定闸拒（未绑定
  agg）→ 不直答不执行——携拒因＋改链 hint＋「换链提议」标记回炉①澄清相位
  （复用失败子集回炉机制；占一轮，零 ask 零挂起）→ 轮 2 换 knowledge 链 →
  doc_retrieve 真执行 → 出数（或如实说无）；
- 不环钉：回炉后坚持 data 链同参 → 前置条件机再判 blocked_refuse 直答终局
  恰一次（chain_switch_marks 指纹簿记在场——step payload 断言面）；
- 四态零回退钉：全未命中仍直拒（C5）/禁用词仍拒/水位仍注记/越集与口径仍反问/
  单井仍注记——trigger 面只在绑定闸（在册未绑定）点亮，其余判定面语义一字不动；
- 混合组钉：触发支＋可执行支并存——可执行支先进批量（部分结果先行），触发支
  随失败子集回炉换链，两支结果都进汇总。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

from appv2.runtime import AskRequest, RunStore
from appv2.tools import (
    CHAIN_SWITCH_HINT,
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

_UNDERSTAND = "理解：数据问句。\n指标候选：注采比"

_WINDOW = {"window_start": "2026-08-01", "window_end": "2026-08-31"}


def _decompose(payload: dict[str, Any]) -> str:
    return json.dumps({"action": "decompose", **payload}, ensure_ascii=False)


def _matches(items: list[dict[str, Any]]) -> str:
    return json.dumps({"matches": items}, ensure_ascii=False)


# ---------- 判定面：触发面只在绑定闸（在册未绑定）点亮 ----------


def test_p040_binding_unbound_trigger_judge_face() -> None:
    """V2-43 触发面＝data 链＋在册（F7 归一后）＋绑定闸拒（未绑定 agg）——
    其余拒因（全未命中/禁用词/水位/越集/单井/口径反问/bound/knowledge）
    四态语义一字不动，trigger 面 False。"""
    facts = ledger_facts(LEDGER_DUMP)
    window = {"window_start": "2025-09-01", "window_end": "2025-09-03"}

    hit = judge(SubtaskInput(
        "t1", "渤中 34-5 油田注采比", "data",
        plan={"metric_slot": "注采比", "ranking": False, **window},
    ), facts)
    assert hit.state == STATE_NOTE  # 判定四态不变（note）
    assert hit.chain_switch_trigger is True  # 触发面（F7 归一命中＋绑定闸拒）
    assert hit.normalized_slot == "注采比 β"
    assert CHAIN_SWITCH_HINT in hit.reason  # 拒因携改链 hint（附 3 模板随行）

    bound = judge(SubtaskInput(
        "t2", "各井日产油量", "data",
        plan={"metric_slot": "日产油量", "ranking": False, **window},
    ), facts)
    assert bound.chain_switch_trigger is False  # bound 不触发

    knowledge = judge(SubtaskInput("t3", "报告所载内容", "knowledge"), facts)
    assert knowledge.state == STATE_PASS
    assert knowledge.chain_switch_trigger is False  # knowledge 链无取数闸面

    miss = judge(SubtaskInput(
        "t4", "各井采出程度", "data",
        plan={"metric_slot": "采出程度", "ranking": False, **window},
    ), facts)
    assert miss.state == STATE_BLOCKED_REFUSE  # 全未命中仍直拒（C5 语义不变）
    assert miss.chain_switch_trigger is False

    banned = judge(SubtaskInput(
        "t5", "各井老完成率", "data",
        plan={"metric_slot": "老完成率", "ranking": False, **window},
    ), facts)
    assert banned.state == STATE_BLOCKED_REFUSE  # 禁用词拒语义不变
    assert banned.chain_switch_trigger is False

    watermark = judge(SubtaskInput(
        "t6", "今年各井日产油量", "data",
        plan={"metric_slot": "日产油量", "ranking": False,
              "window_start": "2026-01-01", "window_end": "2026-10-08"},
    ), facts, watermark=date(2026, 8, 31))
    assert watermark.state == STATE_NOTE  # 水位注记语义不变
    assert watermark.chain_switch_trigger is False

    ext = judge(SubtaskInput(
        "t7", "井位台账关联日产油量", "data",
        plan={"metric_slot": "日产油量", "ranking": False,
              "external_tables": ["erp_well_register"]},
    ), facts)
    assert ext.state == STATE_BLOCKED_ASK  # 越集审批闸先于绑定闸——语义不变
    assert ext.chain_switch_trigger is False

    well = judge(SubtaskInput(
        "t8", "N-01 井 2025-09-01 日产油量", "data",
        plan={"metric_slot": "日产油量", "ranking": False, **window},
    ), facts)
    assert well.state == STATE_NOTE  # 单井注记语义不变
    assert well.chain_switch_trigger is False


# ---------- B-反3 形端到端：归一→未绑定→回炉→换 knowledge 链→出数 ----------


async def test_p040_refurnace_switches_to_knowledge_and_retrieves(
    tmp_path: Path,
) -> None:
    """「注采比」形（B-反3 剧本钉）：归一命中「☆注采比 β」→绑定闸拒（未绑定
    agg）→不直答不执行——标记回炉①（零 ask 零挂起）→轮 2 换 knowledge 链 →
    doc_retrieve 真执行出数。"""
    retrieval = _retrieval_with(_fragment_obs(
        "渤中 34-5 油田 2026 年 8 月注采比 0.98（月报所载）。", "frag-zcb-1"))
    engine = FourPhaseEngine([_rows_outcome()], slots=frozenset({"注采比 β"}))
    clarify_r1 = _decompose({"question_group": {"subtasks": [
        {"id": "s1", "question": "渤中 34-5 油田注采比",
         "ledger_notes": "注采比｜登记名☆注采比 β", "chain": "data"},
    ]}})
    toolmatch_r1 = _matches([
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "注采比", "ranking": False, **_WINDOW}},
    ])
    clarify_r2 = _decompose({"question_group": {"subtasks": [
        {"id": "s1", "question": "渤中 34-5 油田注采比（据拒因提示换检索链）",
         "ledger_notes": "文档所载——knowledge 链", "chain": "knowledge",
         "tool": "doc_retrieve"},
    ]}})
    toolmatch_r2 = _matches([
        {"id": "s1", "chain": "knowledge", "tool": "doc_retrieve",
         "retrieval_need": {"question": "渤中 34-5 油田注采比"}},
    ])
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1, clarify_r2, toolmatch_r2],
        "v2.runtime.answer": ["渤中 34-5 油田 2026 年 8 月注采比 0.98[1]。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=engine, script=script, retrieval=retrieval,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        handle = await runtime.ask(AskRequest(
            question="渤中 34-5 油田注采比是多少？", actor=ACTOR))
        events = await drain(handle)
        assert events[-1].data["status"] == "completed"
        assert not [e for e in events if e.event == "ask"]  # 回炉非挂起——零 ask 帧
        assert engine.run_calls == 0  # data 引擎零执行（首轮被回炉闸拦下）
        assert retrieval.retrieve_calls == 1  # 轮 2 换链真执行
        store = RunStore(db)
        run_id = events[-1].data["run_id"]
        steps = await store.list_steps(run_id)
        preconds = _step_payloads(steps, "precondition")
        assert len(preconds) == 2  # 回炉后前置条件机再判恰一次
        first = preconds[0]["verdicts"][0]
        assert first["state"] == STATE_NOTE
        assert first["chain_switch_trigger"] is True
        assert first["normalized_slot"] == "注采比 β"  # F7 归一先行
        assert preconds[0]["chain_switch_marks"]["s1"]  # 换链指纹簿记在场
        second = preconds[1]["verdicts"][0]
        assert second["state"] == STATE_PASS  # 换 knowledge 链放行
        assert second["chain_switch_trigger"] is False
        notices = [e.data for e in events if e.event == "notice"]
        reentries = [n for n in notices if n.get("type") == "chain_switch_reentry"]
        assert len(reentries) == 1  # 回炉①恰一次（机读 notice）
        # 回炉①澄清轮携失败子集＋拒因＋hint＋换链提议（第 3 次决策调用＝轮 2 澄清）
        round2_clarify = completer.messages_of("v2.runtime.decision")[2][-1]["content"]
        assert "回炉：" in round2_clarify and "s1" in round2_clarify
        assert "在册未绑定" in round2_clarify and CHAIN_SWITCH_HINT in round2_clarify
        assert "换链提议" in round2_clarify
        run_row = await store.get_run(run_id)
        assert run_row is not None and "0.98" in (run_row.answer or "")
    finally:
        await db.dispose()


# ---------- 不环钉：坚持 data 链同参→直答终局恰一次 ----------


async def test_p040_insist_same_data_params_direct_answer_once(
    tmp_path: Path,
) -> None:
    """回炉后坚持 data 链同参＝前置条件机再判 blocked_refuse 直答终局（不环）：
    直答恰一次、data 引擎零触碰、同参指纹在簿、终局拒因不带改链 hint。"""
    engine = FourPhaseEngine([_rows_outcome()], slots=frozenset({"注采比 β"}))
    clarify_r1 = _decompose({"question_group": {"subtasks": [
        {"id": "s1", "question": "渤中 34-5 油田注采比",
         "ledger_notes": "注采比｜登记名☆注采比 β", "chain": "data"},
    ]}})
    toolmatch_r1 = _matches([
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "注采比", "ranking": False, **_WINDOW}},
    ])
    clarify_r2 = _decompose({"question_group": {"subtasks": [
        {"id": "s1", "question": "渤中 34-5 油田注采比",
         "ledger_notes": "注采比｜登记名☆注采比 β", "chain": "data"},
    ]}})
    toolmatch_r2 = _matches([
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "注采比", "ranking": False, **_WINDOW}},
    ])
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1, clarify_r2, toolmatch_r2],
        "v2.runtime.answer": ["（终局面——不应被起草消费）"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        handle = await runtime.ask(AskRequest(
            question="渤中 34-5 油田注采比是多少？", actor=ACTOR))
        events = await drain(handle)
        assert events[-1].data["status"] == "completed"
        assert engine.run_calls == 0  # 坚持原链同参——引擎零执行（不环）
        store = RunStore(db)
        run_id = events[-1].data["run_id"]
        steps = await store.list_steps(run_id)
        preconds = _step_payloads(steps, "precondition")
        assert len(preconds) == 2
        assert preconds[0]["chain_switch_marks"]["s1"]  # 首轮触发即簿记
        assert (
            preconds[1]["chain_switch_marks"]["s1"]
            == preconds[0]["chain_switch_marks"]["s1"]  # 同参指纹一致
        )
        second = preconds[1]["verdicts"][0]
        assert second["state"] == STATE_BLOCKED_REFUSE  # 再判＝直答终局
        assert "换链回炉已用尽" in second["reason"]
        assert CHAIN_SWITCH_HINT not in second["reason"]  # 终局不带 hint
        run_row = await store.get_run(run_id)
        assert run_row is not None
        answer = run_row.answer or ""
        assert "换链回炉已用尽" in answer  # 直答拒因如实转用户
        assert CHAIN_SWITCH_HINT not in answer  # 直答是终局（hint 剥除语义延续）
        assert not [e for e in events if e.event == "ask"]  # 全程零挂起
        # 恰一次：2 轮×（澄清＋匹配）＝4 次决策调用——无第三轮回炉（一次为界）
        assert len(completer.messages_of("v2.runtime.decision")) == 4
    finally:
        await db.dispose()


# ---------- 混合组钉：可执行支先进批量，触发支随失败子集回炉 ----------


async def test_p040_mixed_group_executes_and_refurnaces(tmp_path: Path) -> None:
    """触发支＋可执行支并存：可执行支先进批量（部分结果先行——与 blocked_ask
    同款部分先行语义），触发支随失败子集回炉①换链，两支结果都进汇总。"""
    retrieval = _retrieval_with(_fragment_obs(
        "渤中 34-5 油田 2026 年 8 月注采比 0.98（月报所载）。", "frag-zcb-2"))
    engine = FourPhaseEngine(
        [_rows_outcome()], slots=frozenset({"日产油量", "注采比 β"})
    )
    clarify_r1 = _decompose({"question_group": {"subtasks": [
        {"id": "s1", "question": "2026-08-01 到 08-31 各井日产油量",
         "ledger_notes": "日产油量｜bound", "chain": "data"},
        {"id": "s2", "question": "渤中 34-5 油田注采比",
         "ledger_notes": "注采比｜登记名☆注采比 β", "chain": "data"},
    ]}})
    toolmatch_r1 = _matches([
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2026-08-01", "window_end": "2026-08-31"}},
        {"id": "s2", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "注采比", "ranking": False, **_WINDOW}},
    ])
    clarify_r2 = _decompose({"question_group": {"subtasks": [
        {"id": "s2", "question": "渤中 34-5 油田注采比（据拒因提示换检索链）",
         "ledger_notes": "文档所载——knowledge 链", "chain": "knowledge",
         "tool": "doc_retrieve"},
    ]}})
    toolmatch_r2 = _matches([
        {"id": "s2", "chain": "knowledge", "tool": "doc_retrieve",
         "retrieval_need": {"question": "渤中 34-5 油田注采比"}},
    ])
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1, clarify_r2, toolmatch_r2],
        "v2.runtime.answer": [
            "s1：N-01 21.16 吨[1]；s2：注采比 0.98[2]。"
        ],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script, retrieval=retrieval,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        handle = await runtime.ask(AskRequest(question="混合题", actor=ACTOR))
        events = await drain(handle)
        assert events[-1].data["status"] == "completed"
        assert engine.run_calls == 1  # 可执行支照常执行（部分结果先行）
        assert retrieval.retrieve_calls == 1  # 触发支回炉换链后真执行
        store = RunStore(db)
        steps = await store.list_steps(events[-1].data["run_id"])
        executed = [
            s for s in steps
            if s.step_type == "execute" and (s.payload or {}).get("subtask_id")
        ]
        assert [(s.payload["subtask_id"], s.payload["status"]) for s in executed] == [
            ("s1", "ok"), ("s2", "ok"),
        ]
        preconds = _step_payloads(steps, "precondition")
        assert len(preconds) == 2
        states_r1 = {
            v["subtask_id"]: (v["state"], v["chain_switch_trigger"])
            for v in preconds[0]["verdicts"]
        }
        assert states_r1["s1"] == (STATE_PASS, False)
        assert states_r1["s2"] == (STATE_NOTE, True)  # 触发支随失败子集回炉
        assert preconds[1]["verdicts"][0]["state"] == STATE_PASS  # 换链放行
    finally:
        await db.dispose()
