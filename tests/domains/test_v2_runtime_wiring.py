"""V2-06 runtime 接线项四条验收（票面「接线项四条随本票落实」逐条落测）。

- ask_detail_resume_wire（接线①——源自 V2-05 收口）：AskFrame.detail（审批卡素材，
  approval_id 在场）接线 resume——resume 的 AskChoice 携 approval_id 留痕进
  step 记录（V2-07 api 409/留痕面的 runtime 侧落点）。
- approval_id_run_seed（接线③——源自 V2-03 偏差 7）：runtime 换 run 前缀种子——
  引擎侧表名种子（APP-〈月日〉-〈表〉）在挂起出栈时被 runtime 重种子为
  「〈run_id〉#〈引擎种子〉」（run 可溯＋引擎种子保留），帧与留痕同源。
- de16_freshness_gate_switch（接线②——源自 V2-03 收口）：ChatSettings.
  freshness_gate_enabled 开关在编排层接线＝gate_freshness 决定是否向问数
  引擎供给水位读面——false＝不供给（引擎不读水位、不拦停不改绑，N7.4a 关）；
  true＝现状。开关语义只翻水位供给，行级权限/外表审批零触碰（N7.4b/c）。
- today_question_refused（接线④——源自 V2-03/V2-05 收口）：「今天」问句行为
  复核——runtime 无快路豁免，data_query 引擎窗界校验 refuse 原样如实转答
  （维持 refuse，注记关闭）。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from appv2.query import (
    CsvSnapshotExecutor,
    QueryEngine,
    QueryOutcome,
    QueryPlan,
    WatermarkFace,
    build_extable_ask,
)
from appv2.runtime import (
    AskChoice,
    AskRequest,
    RunStore,
    gate_freshness,
)
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    QueueQueryEngine,
    drain,
    make_runtime,
)

TODAY = date(2026, 10, 8)
WATERMARK = date(2026, 8, 31)

_UNDERSTAND = "理解：问日产油量。\n指标候选：日产油量"
_ANSWER = "答案：见引用[1]。"


def _notices(events: list[Any]) -> list[dict[str, Any]]:
    return [e.data for e in events if e.event == "notice"]


# ---------- 接线①＋③：AskFrame.detail(approval_id) 接线 resume＋run 前缀种子 ----------


async def test_ask_detail_resume_wire(tmp_path: Path) -> None:
    engine_seed = f"APP-{TODAY:%m%d}-erp_well_register"
    plan = QueryPlan(
        metric_slot="日产油量",
        window_start=date(2025, 9, 1),
        window_end=date(2025, 9, 3),
        limit=5,
        ranking=False,
        external_tables=("erp_well_register",),
        actor="dev-u1",
    )
    extable = QueryOutcome.external_table_approval(
        tables=("erp_well_register",),
        ask=build_extable_ask(plan, approval_id=engine_seed),
    )
    rows = QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
        lineage=(),
    )
    engine = QueueQueryEngine([extable, rows])
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.plan": [
            '{"metric_slot": "日产油量", "ranking": false, '
            '"window_start": "2025-09-01", "window_end": "2025-09-03", '
            '"limit": 5, "external_tables": ["erp_well_register"]}'
        ],
        "v2.runtime.answer_draft": ["外表审批通过后取数：N-01 21.16 吨[1]。"],
    }
    runtime, _completer, db = await make_runtime(tmp_path, engine=engine, script=script)
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question="按井位台账对的日产油量", actor=ACTOR))
        events = await drain(handle)
        run_id = handle.run_id
        # 接线③：runtime 换 run 前缀种子——帧内 approval_id＝〈run_id〉#〈引擎种子〉。
        ask_events = [e for e in events if e.event == "ask"]
        assert ask_events, "审批 ASK 帧未发出"
        frame = ask_events[0].data["frame"]
        assert frame["kind"] == "external_table_approval"
        assert frame["detail"] is not None
        approval_id = frame["detail"]["approval_id"]
        assert approval_id.startswith(run_id + "#")
        assert approval_id.endswith(engine_seed)  # 引擎种子保留可溯
        # 接线①：resume 携 approval_id——留痕进 step 记录。
        handle_b = await runtime.resume(run_id, AskChoice(value="批准", approval_id=approval_id))
        events_b = await drain(handle_b)
        run = await store.get_run(run_id)
        assert run is not None and run.status == "completed"
        assert "21.16" in (run.answer or "")
        steps = await store.list_steps(run_id)
        resume_records = [
            s for s in steps if (s.payload or {}).get("resume") is not None
        ]
        assert resume_records, "resume 留痕缺失（接线①落空）"
        record = resume_records[-1].payload["resume"]
        assert record["approval_id"] == approval_id
        assert record["value"] == "批准"
        # 审批留痕 notice（run 前缀种子单号可回溯——接线①③的机读信号）。
        assert _notices(events_b), "审批留痕 notice 缺失"
        assert any(
            n.get("type") == "approval_recorded" for n in _notices(events_b)
        )
    finally:
        await db.dispose()


# ---------- 接线②：DE-16 freshness_gate_enabled 开关＝水位供给翻板 ----------


def _gate_engine(*, enabled: bool) -> QueryEngine:
    from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot

    knowledge = InMemoryKnowledgeStore(question_array_snapshot(), today=TODAY)
    return QueryEngine(
        knowledge=knowledge,
        executor=CsvSnapshotExecutor(),
        waterline=gate_freshness(
            lambda: WatermarkFace(
                data_date=WATERMARK, promise="T-1", tag="落后 38 天（超期）"
            ),
            enabled=enabled,
        ),
        today=lambda: TODAY,
    )


async def test_de16_freshness_gate_switch(tmp_path: Path) -> None:
    # 窗 2026-09-01..09-15：窗头晚于水位 2026-08-31——闸开＝拦停（零数值）；
    # 闸关＝不读水位不拦停（引擎继续走执行，0 行如实 refuse，不冒充）。
    plan_json = (
        '{"metric_slot": "日产油量", "ranking": false, '
        '"window_start": "2026-09-01", "window_end": "2026-09-15"}'
    )
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.plan": [plan_json],
        "v2.runtime.answer_draft": [_ANSWER],
    }
    # （a）开关开（缺省现状）：新鲜度闸拦停话术进答案，零数值。
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=_gate_engine(enabled=True), script=script
    )
    try:
        handle = await runtime.ask(AskRequest(question="9 月上旬的日产油量", actor=ACTOR))
        events = await drain(handle)
        store = RunStore(db)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "新鲜度闸拦停" in (run.answer or "")
        assert "21.16" not in (run.answer or "")  # 零数值（拦停不冒充）
        assert _notices(events)
    finally:
        await db.dispose()

    # （b）开关关：水位不供给——不拦停（无拦停话术）；执行后 0 行如实拒答。
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=_gate_engine(enabled=False), script=script
    )
    try:
        handle = await runtime.ask(AskRequest(question="9 月上旬的日产油量", actor=ACTOR))
        await drain(handle)
        store = RunStore(db)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        assert "新鲜度闸拦停" not in answer  # 闸关＝不拦停（N7.4a off）
        assert "查无数据" in answer  # 0 行如实拒答——不冒充出数
    finally:
        await db.dispose()


# ---------- 接线④：「今天」问句维持 refuse（注记关闭——无快路豁免） ----------


async def test_today_question_refused(tmp_path: Path) -> None:
    from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot

    knowledge = InMemoryKnowledgeStore(question_array_snapshot(), today=TODAY)
    engine = QueryEngine(
        knowledge=knowledge,
        executor=CsvSnapshotExecutor(),
        waterline=None,
        today=lambda: TODAY,
    )
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.plan": [
            '{"metric_slot": "日产油量", "ranking": false, '
            '"window_start": "2026-10-08", "window_end": "2026-10-09"}'
        ],
        "v2.runtime.plan_repair": [
            # repair 一轮（同窗重排——合同：repair 一次）；
            '{"metric_slot": "日产油量", "ranking": false, '
            '"window_start": "2026-10-08", "window_end": "2026-10-09"}'
        ],
        "v2.runtime.answer_draft": [_ANSWER],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script, knowledge=knowledge
    )
    try:
        handle = await runtime.ask(AskRequest(question="今天的日产油量", actor=ACTOR))
        events = await drain(handle)
        store = RunStore(db)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        # 维持 refuse：引擎窗界校验拒因原样转答（未来窗不代猜不冒充——R6-03）。
        assert "窗界越界" in answer
        assert "未来窗不代猜" in answer
        # 无快路豁免：零数值出数，notice 如实。
        assert "21.16" not in answer
        notices = _notices(events)
        assert any(n.get("type") == "refused" for n in notices)
    finally:
        await db.dispose()
