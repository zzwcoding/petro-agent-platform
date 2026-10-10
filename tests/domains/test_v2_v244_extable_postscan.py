"""P-041/V2-44 越集后置确定性闸钉测（Owner 签发 2026-10-10——Q14 前最后一张）。

票面四验收的钉面（行为定义＝确定性，零 LLM）：
- 漏报捕获钉（数-察2 形剧本红→绿）：plan 无 external_tables 但问句词面触
  外表别名（「井位台账」→erp_well_register）→ 前置条件机执行前拦截＋审批
  挂起帧同形（ASK_EXTERNAL_TABLE_APPROVAL——复用现有帧/resume 通道零新建）；
  修复前该形直通批量出数（P039BW run-afbe7aad 高危实证＝红）；
- 申报正路不回退钉：申报＋未审定仍拦（拒因现语义逐字）；申报＋已审定放行
  →note 随行照常执行（既有钉语义零回退）；
- 未申报未越集零误拦钉：干净取数形 pass 零新增注记（性能面无多余拦截）；
- 漏报捕获留痕机读：拦截与放行两形的 notes／审批卡 detail 均携「漏报捕获」
  机读标记＋表名集在场（declared/detected——审计可溯）；
- 扫描件单测：别名面（井位台账→erp_well_register）＋schema 前缀面
  （raw/lake/schema 全解析——裸名归一比对）＋agg 三表基座恒白名单。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from appv2.runtime import AskChoice
from appv2.tools import judge, ledger_facts
from appv2.tools.precondition import (
    STATE_BLOCKED_ASK,
    STATE_NOTE,
    STATE_PASS,
    SubtaskInput,
)
from appv2.tools.table_scan import (
    extract_external_table_refs,
    scan_unapproved_tables,
)
from tests.domains.test_v2_agent_loop import (
    QueueQueryEngine,
    drain,
    make_runtime,
)
from tests.domains.test_v2_four_phase import (
    LEDGER_DUMP,
    _run_question,
)
from tests.domains.test_v2_react_loop import _rows_outcome

_FACTS = ledger_facts(LEDGER_DUMP)

# 数-察2 题册原句（eval/answers/问数组-题目与答案.md——题干原句不改写）。
_CHA2_QUESTION = "井位台账里日产油量最高的井是哪口？"

_WINDOW = {"window_start": "2025-09-01", "window_end": "2025-09-03"}

_UNDERSTAND = "理解：数据问句。\n指标候选：日产油量"

_SUMMARY_DRAFT = "子任务 s1：井位台账里日产油量最高的井 Z-16 [1]。"


def _decompose(question: str) -> str:
    return json.dumps(
        {
            "action": "decompose",
            "question_group": {"subtasks": [
                {"id": "s1", "question": question,
                 "ledger_notes": "日产油量｜bound｜外表关联", "chain": "data"},
            ]},
        },
        ensure_ascii=False,
    )


def _toolmatch(plan_extra: dict[str, Any]) -> str:
    plan = {"metric_slot": "日产油量", "ranking": True, **_WINDOW, **plan_extra}
    return json.dumps(
        {"matches": [
            {"id": "s1", "chain": "data", "tool": "data_query", "plan": plan},
        ]},
        ensure_ascii=False,
    )


# ---------- 扫描件单测：词面提取＋白名单比对（agg/raw/lake/schema 全解析） ----------


def test_v244_scan_alias_word_face_detects_external() -> None:
    """别名面：「井位台账」→erp_well_register（F14 越集比对触发源单源复用）。"""
    assert extract_external_table_refs(_CHA2_QUESTION) == ("erp_well_register",)
    # 已申报词面（模型发射面写法——schema 裸名直书）同样命中。
    assert extract_external_table_refs("erp_well_register 关联的日产油量") == (
        "erp_well_register",
    )


def test_v244_scan_schema_qualified_resolution() -> None:
    """schema 前缀面：raw/lake/schema 全解析——前缀剥除裸名归一比对。"""
    assert extract_external_table_refs("raw.erp_well_register 里日产油量") == (
        "erp_well_register",
    )
    assert extract_external_table_refs("lake.custom_log 与湖表联查") == ("custom_log",)
    # agg 三表基座（agg.fct_daily_metering 等）命中也归裸名——基座恒白名单。
    assert extract_external_table_refs("agg.fct_daily_metering 各井日产油量") == (
        "fct_daily_metering",
    )


def test_v244_scan_base_tables_never_unapproved() -> None:
    """agg 三表基座＋已审定放行集＝白名单——基座引用零误拦。"""
    findings = scan_unapproved_tables(
        "agg.fct_daily_metering 各井日产油量",
        {"metric_slot": "日产油量", "ranking": False},
        approved_tables=(),
    )
    assert findings.unapproved == ()  # 基座恒开放——零误拦
    # 别名外表未审定＝拦（数-察2 漏报形——判定面核心）。
    miss = scan_unapproved_tables(
        _CHA2_QUESTION, {"metric_slot": "日产油量", "ranking": True}, approved_tables=()
    )
    assert miss.unapproved == ("erp_well_register",)
    assert miss.miss_declared == ("erp_well_register",)  # 计划未申报＝漏报捕获面
    # 已放行＝不拦；漏报捕获面仍在（留痕不随放行消失）。
    ok = scan_unapproved_tables(
        _CHA2_QUESTION, {"metric_slot": "日产油量", "ranking": True},
        approved_tables=("erp_well_register",),
    )
    assert ok.unapproved == ()
    assert ok.miss_declared == ("erp_well_register",)
    # 申报在案（申报面）＋实扫无增量＝零漏报标记。
    declared = scan_unapproved_tables(
        _CHA2_QUESTION,
        {"metric_slot": "日产油量", "ranking": True,
         "external_tables": ["erp_well_register"]},
        approved_tables=(),
    )
    assert declared.unapproved == ("erp_well_register",)
    assert declared.miss_declared == ()  # 申报在案——非漏报（申报面现语义拦）


# ---------- 验收①：漏报捕获钉（数-察2 形——判定面） ----------


def test_v244_miss_declared_intercepted_before_execute() -> None:
    """plan 无 external_tables＋问句词面触未审定表→blocked_ask 审批挂起帧同形。"""
    v = judge(
        SubtaskInput(
            "s1", _CHA2_QUESTION, "data",
            plan={"metric_slot": "日产油量", "ranking": True, **_WINDOW},
        ),
        _FACTS,
    )
    assert v.state == STATE_BLOCKED_ASK  # 修复前＝pass 直通出数（红——高危形）
    assert v.ask is not None
    assert v.ask.kind == "external_table_approval"  # 现有审批帧同形（零新建）
    assert v.ask.options == ("批准", "驳回")
    detail = dict(v.ask.detail or {})
    assert detail["tables"] == ["erp_well_register"]  # 表名集在场（resume 通道消费键）
    assert "erp_well_register" in v.ask.prompt  # 拦停原因在场（审计可溯）
    # 漏报捕获机读留痕（notes 判定载荷＋detail 双落）。
    assert any("漏报捕获" in n for n in v.notes)
    assert detail["declared_tables"] == []
    assert detail["detected_tables"] == ["erp_well_register"]
    assert detail["miss_declared"] == ["erp_well_register"]
    payload = v.as_payload()
    assert any("漏报捕获" in n for n in payload["notes"])  # 机读 JSON 载荷面


# ---------- 验收②：申报正路不回退钉 ----------


def test_v244_declared_path_semantics_unchanged() -> None:
    """申报＋未审定仍拦（拒因现语义逐字）；申报＋已审定放行→note 零回退。"""
    plan = {"metric_slot": "日产油量", "ranking": False,
            "external_tables": ["erp_well_register"]}
    v_blocked = judge(
        SubtaskInput("x1", "井位台账关联日产油量", "data", plan=dict(plan)), _FACTS,
    )
    assert v_blocked.state == STATE_BLOCKED_ASK
    # 拒因现语义逐字（申报面不动——V2-44 前后 byte 相等）。
    assert v_blocked.reason == (
        "计划引用外部表 ['erp_well_register']——越集审批（模型与流程无权自批）"
    )
    assert not any("漏报捕获" in n for n in v_blocked.notes)  # 申报在案＝非漏报
    v_approved = judge(
        SubtaskInput("x1", "井位台账关联日产油量", "data", plan=dict(plan)),
        _FACTS, approved_tables=("erp_well_register",),
    )
    assert v_approved.state == STATE_NOTE  # 放行后注记随行，不重排计划（现语义）
    assert any("放行" in n for n in v_approved.notes)
    assert not any("漏报捕获" in n for n in v_approved.notes)  # 申报在案＝非漏报


async def test_v244_four_phase_miss_declared_ask_resume_chain(tmp_path: Path) -> None:
    """数-察2 形剧本红→绿（端到端）：toolmatch 漏带 external_tables→前置条件机
    实扫拦截挂审批帧→resume 批准→前置重判放行→批量续跑出数全通。
    修复前：零 ask 帧直通出数（P039BW run-afbe7aad 高危形——本钉红态）。"""
    engine = QueueQueryEngine([_rows_outcome()])
    script = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [
            _decompose(_CHA2_QUESTION),
            _toolmatch({}),  # 漏报形——plan 无 external_tables 键
        ],
        "v2.runtime.answer": [_SUMMARY_DRAFT],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine,
        script=script, four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_question(runtime, _CHA2_QUESTION)
        asks = [e.data for e in events if e.event == "ask"]
        assert asks, "漏报形必须被前置条件机实扫拦截挂审批帧（修复前直通出数＝红）"
        assert asks[-1]["frame"]["kind"] == "external_table_approval"
        detail = asks[-1]["frame"]["detail"]
        assert detail["tables"] == ["erp_well_register"]
        assert detail["miss_declared"] == ["erp_well_register"]  # 漏报捕获机读留痕
        assert engine.run_calls == 0  # 拦截在执行前——引擎零调用（零数值出闸）
        run_id = asks[-1]["run_id"]
        # resume 批准（现有 resume 通道复用零新建）→前置重判放行→批量续跑出数。
        handle = await runtime.resume(
            run_id,
            AskChoice(value="批准", approval_id=detail["approval_id"]),
        )
        events2 = await drain(handle)
        assert events2[-1].data["status"] == "completed"
        assert engine.run_calls == 1  # 放行后批量真执行（恰一次）
        resume_steps = [e.data for e in events2 if e.event == "step"]
        assert any("审批回收" in str(s.get("title", "")) for s in resume_steps)
    finally:
        await db.dispose()


# ---------- 验收③：未申报未越集零误拦钉 ----------


def test_v244_clean_data_form_zero_extra_notes() -> None:
    """干净取数形（无申报无外表词面）＝pass 零新增注记（性能面无多余拦截）。"""
    v = judge(
        SubtaskInput(
            "s1", "去年各井日产油量是多少？", "data",
            plan={"metric_slot": "日产油量", "ranking": False, **_WINDOW},
        ),
        _FACTS,
    )
    assert v.state == STATE_PASS
    assert v.notes == ()  # 零新增注记——实扫零误伤


# ---------- 验收④：漏报捕获放行形留痕（拦停之外的机读留痕面） ----------


def test_v244_miss_declared_approved_note_trail() -> None:
    """漏报但已审定放行＝照常执行＋漏报捕获注记随行（留痕不静默）。"""
    v = judge(
        SubtaskInput(
            "s1", _CHA2_QUESTION, "data",
            plan={"metric_slot": "日产油量", "ranking": True, **_WINDOW},
        ),
        _FACTS, approved_tables=("erp_well_register",),
    )
    assert v.state == STATE_NOTE
    assert any("放行" in n for n in v.notes)  # 现语义放行注记在场
    assert any("漏报捕获" in n for n in v.notes)  # 漏报捕获机读留痕随行
