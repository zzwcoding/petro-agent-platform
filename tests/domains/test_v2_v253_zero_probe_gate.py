"""V2-53 零观察定稿治理——零探查拒回闸钉测（附 E，TDD 红先绿后）。

施工基准＝tickets/v2/V2-53-零观察定稿治理.md 附 A–F（逐字稿与伪代码照抄）。
病形（Q15 族 Z 12 题）：模型一次检索未做即发射 finalize 定稿→12 题零交付。
修法两层：话术统一（附 A/B——合同授权冲突拆除＋台账「字典不是数据」注）
＋零探查拒回闸（附 C——复用预算拒收敛机 S2 同款公式与既有拒因回喂通道）
＋发射原文入档（附 D——放行/拒两点 step 事件加 emission 键）。

钉面（附 E T1–T6；T7＝既有合同文本断言随新逐字稿同步更新，落在
tests/domains/test_v2_v252_five_station.py 与
tests/domains/test_v2_p039b_f2c_two_branch_wording.py 两处既有断言面）：

- T1 零探查 finalize 拒回：拒因与 ZERO_PROBE_FEEDBACK 逐字相等＋步标题含
  「被拒：零探查观察禁定稿」＋首拒免轮（rounds 不变）＋下一轮 instruction
  含拒因回喂句。budget_reject_streak==1 钉经其公开后果断言（首拒免轮＝
  streak<2 分支被走到——streak 本体不经公开面直接可读，行为断言锁轮记账）。
- T2 连环拒占轮：第二次零探查 finalize → rounds+1（步标题 r1）。
- T3 放行不回退：discover 已执行（faq 命中形）→ finalize 照旧放行（步标题
  「澄清定稿：材料足够——直答收口」不变）。
- T4 followup 旁路：followup_of 非空＋零探查 finalize → 放行。
- T5 逐字稿钉：CLARIFY_CONTRACT 含附 A1/A2 新句、不含旧句；常驻块首行含
  LEDGER_DICT_NOTE 句。
- T6 step 事件 emission 键在场（放行与拒两点）。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from appv2.runtime import AskRequest, RunStore, ScriptedCompleter
from appv2.runtime.context import LEDGER_DICT_NOTE, ContextBuilder
from appv2.runtime.graph import ZERO_PROBE_FEEDBACK
from appv2.runtime.guide import CLARIFY_CONTRACT
from appv2.runtime.state import STEP_DECISION, RunState
from appv2.tools import RESIDENT_BLOCK_BEGIN
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    QueueQueryEngine,
    drain,
    make_runtime,
)
from tests.domains.test_v2_four_phase import LEDGER_DUMP, UNDERSTAND_MULTI
from tests.domains.test_v2_react_loop import _rows_outcome
from tests.domains.test_v2_v252_five_station import _faq_hit, _FaqFace

# ---------- 剧本罐头（四相位 clarify 面） ----------

_FINALIZE = '{"thought": "材料已足够", "action": "finalize"}'

_CLARIFY_S1 = json.dumps({
    "action": "decompose",
    "question_group": {"subtasks": [
        {"id": "s1", "question": "2025-09-01 到 09-03 各井日产油量",
         "ledger_notes": "日产油量｜bound｜窗 2025-09-01~2025-09-03", "chain": "data"},
    ]},
}, ensure_ascii=False)

_TOOLMATCH_S1 = json.dumps({"matches": [
    {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
        "metric_slot": "日产油量", "ranking": False,
        "window_start": "2025-09-01", "window_end": "2025-09-03"}},
]}, ensure_ascii=False)

_ANSWER = "N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"

_FAQ_DISCOVER = json.dumps({
    "action": "discover",
    "discovers": [{
        "tool": "faq_lookup",
        "args": {"question": "N-02 井是什么时候投产的？"},
    }],
}, ensure_ascii=False)

_FAQ_HIT_FACE = _FaqFace([
    _faq_hit("faq-4", "N-02 井是什么时候投产的？", "2019-06-15 投产。"),
])

# ---------- 附 A 逐字稿（票面 char 相等——T5 断言基准） ----------

_A1_NEW = (
    "- faq_lookup：FAQ 现成问答库——问句有现成标准答案时加速/互证；\n"
    "  命中条目作观察材料进上下文——有探查观察在场方可 finalize，不够继续检索"
)
_A1_OLD = "你判断够 finalize 即可直答"
_A2_NEW = (
    '- 定稿直答：{"action": "finalize"}——仅当本 run 已有探查观察'
    "（discover 命中条目）时可用：系统按观察材料起草带引用的答案"
    "（秒答形，不走检索执行）。零探查观察发射 finalize＝非法发射，"
    "程序拒回并要求改发。台账常驻注入是字典不是数据——指标/术语在台账＝"
    "知道名字与定义，不等于数值在手，注入不进交付面；要数值先 discover 钻取"
    "或 decompose 分解走检索执行。"
)
_A2_OLD = "探查观察（辅助材料）已足够回答时"


async def _run(
    tmp_path: Path,
    script: dict[str, Sequence[str]],
    question: str,
    *,
    faq: _FaqFace | None = None,
) -> tuple[list[Any], RunStore, Any, ScriptedCompleter]:
    """四相位装配真跑一题（events/store/db/completer 出列——各测试自管 dispose）。"""
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP), faq=faq,
    )
    store = RunStore(db)
    handle = await runtime.ask(AskRequest(question=question, actor=ACTOR))
    events = await drain(handle)
    return events, store, db, completer


# ---------- T1：零探查 finalize 拒回（拒因逐字回喂＋首拒免轮） ----------


async def test_t1_zero_probe_finalize_rejected_with_verbatim_feedback(
    tmp_path: Path,
) -> None:
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": [_FINALIZE, _CLARIFY_S1, _TOOLMATCH_S1],
        "v2.runtime.answer": [_ANSWER],
    }
    events, store, db, completer = await _run(tmp_path, script, "各井日产油量是多少")
    try:
        final = events[-1].data
        assert final["status"] == "completed"
        steps = await store.list_steps(final["run_id"])
        # 拒步恰一：步标题含「被拒：零探查观察禁定稿」＋payload.rejection 与
        # ZERO_PROBE_FEEDBACK 逐字相等（拒因回喂真源同源）。
        rejects = [s for s in steps if "被拒：零探查观察禁定稿" in s.title]
        assert len(rejects) == 1
        payload = rejects[0].payload or {}
        assert payload["rejection"] == ZERO_PROBE_FEEDBACK
        # 首拒免轮（budget_reject_streak==1 → streak<2 分支）：rounds 不变——
        # 拒步记 r0，后续分解照常记 r1。
        assert rejects[0].title.startswith("澄清 r0 被拒：")
        assert any(s.title == "澄清 r1：分解 1 子问题" for s in steps)
        # 下一轮 instruction 含拒因回喂句（既有通道承接——决策被拒同款）。
        second_call = completer.messages_of("v2.runtime.decision")[1]
        assert ZERO_PROBE_FEEDBACK in str(second_call[-1]["content"])
        assert "上次发射被拒：" in str(second_call[-1]["content"])
    finally:
        await db.dispose()


# ---------- T2：连环拒占轮（第二次零探查 finalize → rounds+1） ----------


async def test_t2_second_zero_probe_finalize_consumes_round(tmp_path: Path) -> None:
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": [_FINALIZE, _FINALIZE, _CLARIFY_S1, _TOOLMATCH_S1],
        "v2.runtime.answer": [_ANSWER],
    }
    events, store, db, _completer = await _run(tmp_path, script, "各井日产油量是多少")
    try:
        final = events[-1].data
        assert final["status"] == "completed"
        steps = await store.list_steps(final["run_id"])
        rejects = [s.title for s in steps if "被拒：零探查观察禁定稿" in s.title]
        # 首拒免轮（r0）＋连环拒自第 2 次起占轮（r1＝rounds+1）。
        assert rejects == [
            "澄清 r0 被拒：零探查观察禁定稿",
            "澄清 r1 被拒：零探查观察禁定稿",
        ]
        # 占轮面继续：后续分解记 r2。
        assert any(s.title == "澄清 r2：分解 1 子问题" for s in steps)
    finally:
        await db.dispose()


# ---------- T3：放行不回退（discover 已执行→finalize 照旧放行） ----------


async def test_t3_discover_then_finalize_passes_through(tmp_path: Path) -> None:
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问 N-02 井投产日期。\n指标候选：无"],
        "v2.runtime.decision": [_FAQ_DISCOVER, _FINALIZE],
        "v2.runtime.answer": ["N-02 井 2019-06-15 投产 [1]。"],
    }
    events, store, db, _completer = await _run(
        tmp_path, script, "N-02 井是什么时候投产的？", faq=_FAQ_HIT_FACE,
    )
    try:
        final = events[-1].data
        assert final["status"] == "completed"
        steps = await store.list_steps(final["run_id"])
        # 定稿步标题不变（原放行路径逐字零改动——放行面不回退）。
        assert any(s.title == "澄清定稿：材料足够——直答收口" for s in steps)
        assert not [s for s in steps if "被拒" in s.title]
    finally:
        await db.dispose()


# ---------- T4：followup 旁路（followup_of 非空＋零探查 finalize → 放行） ----------


async def test_t4_followup_run_zero_probe_finalize_bypasses(tmp_path: Path) -> None:
    # 前轮与追问 run 同库（追问播种面经 checkpointer 读前轮线程——多轮测试同法）。
    script_a: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": [_CLARIFY_S1, _TOOLMATCH_S1],
        "v2.runtime.answer": [_ANSWER],
    }
    runtime_a, _completer_a, db_a = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_a,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    store_a = RunStore(db_a)
    run_id_a = ""
    try:
        handle_a = await runtime_a.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        await drain(handle_a)
        run_a = await store_a.get_run(handle_a.run_id)
        assert run_a is not None and run_a.status == "completed"
        run_id_a = handle_a.run_id
    finally:
        await db_a.dispose()

    script_b: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": [_FINALIZE],  # 追问续跑零探查——旁路放行
        "v2.runtime.answer": ["按前轮材料如实作答。"],
    }
    runtime_b, _completer_b, db_b = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_b,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    store_b = RunStore(db_b)
    try:
        handle_b = await runtime_b.ask(
            AskRequest(question="那 N-01 井 9 月 2 日的日产油量呢？", actor=ACTOR,
                       followup_of=run_id_a)
        )
        events_b = await drain(handle_b)
        assert events_b[-1].data["status"] == "completed"
        steps = await store_b.list_steps(handle_b.run_id)
        # 旁路放行：定稿步标题在场，零被拒步（追问语义本票零触碰）。
        assert any(s.title == "澄清定稿：材料足够——直答收口" for s in steps)
        assert not [s for s in steps if "被拒" in s.title]
    finally:
        await db_b.dispose()


# ---------- T5：逐字稿钉（附 A 新句在场/旧句退场＋常驻块头注） ----------


def test_t5_contract_verbatim_and_ledger_dict_note() -> None:
    # 附 A1：新句在场、旧句退场。
    assert _A1_NEW in CLARIFY_CONTRACT
    assert _A1_OLD not in CLARIFY_CONTRACT
    # 附 A2：新句在场、旧句退场。
    assert _A2_NEW in CLARIFY_CONTRACT
    assert _A2_OLD not in CLARIFY_CONTRACT
    # 附 B：常驻块 BEGIN 后首行＝LEDGER_DICT_NOTE（历史簿记 _slim_resident
    # 整块收窄自动覆盖面——注入缝单点）。
    builder = ContextBuilder()
    compiled = builder.compile(
        RunState(run_id="run-t5"),
        step=STEP_DECISION,
        instruction="任务",
        extra_sources=[{"source_type": "ledger_dump", "source_id": "d1",
                        "label": "台账全量", "content": "日产油量——bound——行"}],
    )
    content = str(compiled.messages[-1]["content"])
    assert (RESIDENT_BLOCK_BEGIN + "\n" + LEDGER_DICT_NOTE + "\n") in content
    assert "（台账全量是字典不是数据" in content


# ---------- T6：step 事件 emission 键在场（放行与拒两点） ----------


async def test_t6_step_event_carries_emission_key_at_both_points(
    tmp_path: Path,
) -> None:
    # 拒点：零探查 finalize 被拒——step 事件第四键 emission 在场。
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": [_FINALIZE, _CLARIFY_S1, _TOOLMATCH_S1],
        "v2.runtime.answer": [_ANSWER],
    }
    events, _store, db, _completer = await _run(tmp_path, script, "各井日产油量是多少")
    try:
        step_events = [e.data for e in events if e.event == "step"]
        reject_events = [
            d for d in step_events if "被拒：零探查观察禁定稿" in str(d.get("title"))
        ]
        assert len(reject_events) == 1
        assert reject_events[0]["emission"]["action"] == "finalize"
    finally:
        await db.dispose()

    # 放点：discover 后 finalize 放行——step 事件同样带 emission 键。
    dir_pass = tmp_path / "pass"
    dir_pass.mkdir()
    script_pass: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问 N-02 井投产日期。\n指标候选：无"],
        "v2.runtime.decision": [_FAQ_DISCOVER, _FINALIZE],
        "v2.runtime.answer": ["N-02 井 2019-06-15 投产 [1]。"],
    }
    events2, _store2, db2, _completer2 = await _run(
        dir_pass, script_pass, "N-02 井是什么时候投产的？", faq=_FAQ_HIT_FACE,
    )
    try:
        step_events2 = [e.data for e in events2 if e.event == "step"]
        pass_events = [
            d for d in step_events2
            if d.get("title") == "澄清定稿：材料足够——直答收口"
        ]
        assert len(pass_events) == 1
        assert pass_events[0]["emission"]["action"] == "finalize"
    finally:
        await db2.dispose()
