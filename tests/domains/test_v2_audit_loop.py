"""V2-20 审计闭环＋resume 状态回写验收（P-010 S3/C1）。

四事件各落一行（票面任务 1／验收 1——唯一写口 security.audit，action 恒
`agent_v2.*` 前缀，who 槽＝resolve_actor 产的 Actor.who，content 槽携输入/
收口摘要，meta 槽携 run_id 主体）：
- run 创建 agent_v2.run_created；
- 终态收口 agent_v2.run_completed / agent_v2.run_failed（一类两值）；
- 拒答收口 agent_v2.refused（与 notice type=refused 机读同源）；
- 外表审批决定 agent_v2.extable_approved / agent_v2.extable_rejected（一类两值）。

resume 回写（票面任务 3／C1／验收 3）：挂起恢复 execute() 受理段 run 行即回写
running（闸门 completer 钉死观察窗——闸持有期终态写不可能先发），全程跑完后
run 达 completed 且 step 留痕 seq 连续无断档（resume 段整体重投影）。

直写扫描（验收 4）归 tests/infra/test_v2_infra.py::audit_single_writer 所有
——本文件不产冗余扫描（runtime/audit.py 零直写面由该测试全树复扫钉死）。
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select

from appv2.infra.db import ConnectionManager
from appv2.infra.security import Actor
from appv2.infra.security.store import AuditLog
from appv2.query import (
    ASKBACK_TIME_CHOICES,
    ASKBACK_TIME_QUESTION,
    QueryOutcome,
    QueryPlan,
    build_extable_ask,
)
from appv2.runtime import AskChoice, AskRequest, RunStore, ScriptedCompleter
from appv2.tools import FakeQueryEngine
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    ANSWER_DRAFT_CITED,
    HAPPY_QUESTION,
    HAPPY_SCRIPT,
    PLAN_VAGUE,
    PLAN_WINDOWED,
    UNDERSTAND_DATA,
    QueueQueryEngine,
    drain,
    make_runtime,
)

TODAY = date(2026, 10, 8)

_VAGUE_SCRIPT: dict[str, Sequence[str]] = {
    "v2.runtime.understand": [UNDERSTAND_DATA],
    "v2.runtime.plan": [PLAN_VAGUE],
}
_WINDOWED_SCRIPT: dict[str, Sequence[str]] = {
    "v2.runtime.understand": [UNDERSTAND_DATA],
    "v2.runtime.plan": [PLAN_WINDOWED],
    "v2.runtime.answer_draft": [ANSWER_DRAFT_CITED],
}


def _rows_outcome() -> QueryOutcome:
    return QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
        lineage=(),
    )


def _need_clarify() -> QueryOutcome:
    return QueryOutcome.need_clarify(
        question=ASKBACK_TIME_QUESTION, choices=ASKBACK_TIME_CHOICES
    )


class _GateCompleter(ScriptedCompleter):
    """闸门 completer：指定 caller 挂等 Event 再放行剧本应答（钉状态观察窗）。"""

    def __init__(self, script: dict[str, Sequence[str]], *, gate_caller: str) -> None:
        super().__init__(script)
        self._gate_caller = gate_caller
        self.gate = asyncio.Event()

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any:
        if caller == self._gate_caller:
            await self.gate.wait()
        return await super().complete(alias, messages, caller=caller, **params)


class _ExplodingCompleter(ScriptedCompleter):
    """爆炸 completer：模型调用即抛（引擎异常→run failed 路径的确定性注入）。"""

    def __init__(self) -> None:
        super().__init__({})

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any:
        raise RuntimeError("网关异常注入（run failed 审计行钉测）")


async def _audit_rows(db: ConnectionManager) -> list[AuditLog]:
    """audit_log 全表按写入序读出（断言面——读侧不受 B12 写口纪律约束）。"""
    async with db.readonly() as session:
        rows = (
            (await session.execute(select(AuditLog).order_by(AuditLog.id)))
            .scalars()
            .all()
        )
        return list(rows)


async def _run_audit_rows(db: ConnectionManager, run_id: str) -> list[AuditLog]:
    """单 run 的审计行（同库多 run 场景按 meta.run_id 主体切片）。"""
    return [
        row
        for row in await _audit_rows(db)
        if isinstance(row.meta, dict) and row.meta.get("run_id") == run_id
    ]


# ---------- 验收 1：四事件各落一行、前缀/agent/输入摘要字段齐 ----------


async def test_four_events_audit_rows(tmp_path: Path) -> None:
    # （a）run 创建＋终态 completed：who＝actor、content 携输入摘要、meta 携 run_id。
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=HAPPY_SCRIPT
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        rows = await _run_audit_rows(db, handle.run_id)
        assert [row.action for row in rows] == [
            "agent_v2.run_created",
            "agent_v2.run_completed",
        ]
        for row in rows:
            assert row.action.startswith("agent_v2.")  # 前缀槽（V1 隔离）
            assert row.who == ACTOR.who  # agent 槽＝resolve_actor 产的 Actor.who
            assert row.meta is not None and row.meta["run_id"] == handle.run_id
        assert HAPPY_QUESTION in rows[0].content  # 输入摘要（content 槽）
        assert rows[1].meta["manifest_digest"] == run.manifest_digest  # 收口随摘要
    finally:
        await db.dispose()

    # （b）拒答收口：闸拒（PermissionError）→notice type=refused→agent_v2.refused 行。
    runtime, _completer, db = await make_runtime(
        tmp_path,
        engine=FakeQueryEngine(run_error=PermissionError("越权口径：无据出数")),
        script=HAPPY_SCRIPT,
    )
    try:
        handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        await drain(handle)
        rows = await _run_audit_rows(db, handle.run_id)
        assert [row.action for row in rows] == [
            "agent_v2.run_created",
            "agent_v2.refused",
        ]
        assert "越权拒绝" in rows[-1].content  # 拒因同源（refused notice 内容槽）
        assert rows[-1].who == ACTOR.who
    finally:
        await db.dispose()

    # （c）终态 failed：模型调用即抛→_drive 异常路径→agent_v2.run_failed 行。
    runtime, _completer, db = await make_runtime(
        tmp_path,
        engine=QueueQueryEngine([_rows_outcome()]),
        script=HAPPY_SCRIPT,
        completer=_ExplodingCompleter(),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "failed"
        rows = await _run_audit_rows(db, handle.run_id)
        assert [row.action for row in rows] == [
            "agent_v2.run_created",
            "agent_v2.run_failed",
        ]
        assert "网关异常注入" in rows[-1].content  # 失败缘由如实进责任账
    finally:
        await db.dispose()


async def test_extable_decision_audit_rows(tmp_path: Path) -> None:
    """外表审批批准/驳回各落一行（四事件之四；单号留痕进 meta）。"""
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
    _script = _WINDOWED_SCRIPT

    # （a）批准：ask 段挂起→resume 批准→决定行（单号＝run 前缀重种子值）＋完成行。
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([extable, _rows_outcome()]), script=_script
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question="跨表问数", actor=ACTOR))
        events = await drain(handle)
        run_id = handle.run_id
        run = await store.get_run(run_id)
        assert run is not None and run.status == "waiting_ask"
        frame = next(e for e in events if e.event == "ask").data["frame"]
        approval_id = str(frame["detail"]["approval_id"])
        assert approval_id == f"{run_id}#{engine_seed}"  # 接线③重种子同源
        handle_b = await runtime.resume(
            run_id, AskChoice(value="批准", approval_id=approval_id)
        )
        await drain(handle_b)
        rows = await _run_audit_rows(db, run_id)
        assert [row.action for row in rows] == [
            "agent_v2.run_created",
            "agent_v2.extable_approved",
            "agent_v2.run_completed",
        ]
        assert rows[1].meta["approval_id"] == approval_id
        assert approval_id in rows[1].content
        assert rows[1].who == ACTOR.who
    finally:
        await db.dispose()

    # （b）驳回：决定行照落（驳回也是审计事件——00 §8.2 同语义），终态 completed。
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([extable, _rows_outcome()]), script=_script
    )
    try:
        handle = await runtime.ask(AskRequest(question="跨表问数", actor=ACTOR))
        await drain(handle)
        handle_b = await runtime.resume(
            handle.run_id, AskChoice(value="驳回", approval_id="x#y")
        )
        await drain(handle_b)
        rows = await _run_audit_rows(db, handle.run_id)
        assert [row.action for row in rows] == [
            "agent_v2.run_created",
            "agent_v2.extable_rejected",
            "agent_v2.run_completed",
        ]
        assert "驳回" in rows[1].content
    finally:
        await db.dispose()


async def test_clarify_resume_zero_extra_audit(tmp_path: Path) -> None:
    """四事件闭世界外不溢行：clarify resume 全程只落创建＋终态两行。"""
    engine = QueueQueryEngine([_need_clarify(), _rows_outcome()])
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=_VAGUE_SCRIPT
    )
    run_id = ""
    try:
        handle = await runtime.ask(AskRequest(question="最近的日产油量", actor=ACTOR))
        await drain(handle)
        run_id = handle.run_id
    finally:
        await db.dispose()

    runtime_b, _completer, db_b = await make_runtime(
        tmp_path, engine=engine, script=_WINDOWED_SCRIPT
    )
    store_b = RunStore(db_b)
    try:
        handle_b = await runtime_b.resume(run_id, AskChoice(value="近 3 天"))
        events_b = await drain(handle_b)
        assert any(e.event == "citation" for e in events_b)
        rows = await _run_audit_rows(db_b, run_id)
        assert [row.action for row in rows] == [
            "agent_v2.run_created",
            "agent_v2.run_completed",
        ]
        run = await store_b.get_run(run_id)
        assert run is not None and run.status == "completed"
    finally:
        await db_b.dispose()


# ---------- 验收 3：resume 段 running 回写——状态机全程无断档 ----------


async def test_resume_running_writeback_no_gap(tmp_path: Path) -> None:
    engine = QueueQueryEngine([_need_clarify(), _rows_outcome()])
    # 进程 A：提问→缺窗→need_clarify 挂起（waiting_ask）。
    runtime_a, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=_VAGUE_SCRIPT
    )
    store = RunStore(db)
    run_id = ""
    steps_a_count = 0
    try:
        handle = await runtime_a.ask(AskRequest(question="最近的日产油量", actor=ACTOR))
        await drain(handle)
        run_id = handle.run_id
        run = await store.get_run(run_id)
        assert run is not None and run.status == "waiting_ask"
        steps_a = await store.list_steps(run_id)
        steps_a_count = len(steps_a)
        assert [s.seq for s in steps_a] == list(range(1, steps_a_count + 1))
    finally:
        await db.dispose()

    # 进程 B：闸门 completer 挂住恢复段 plan 调用——受理段 running 回写的确定性观察窗。
    gate = _GateCompleter(_WINDOWED_SCRIPT, gate_caller="v2.runtime.plan")
    runtime_b, _completer, db_b = await make_runtime(
        tmp_path, engine=engine, script=_WINDOWED_SCRIPT, completer=gate
    )
    store_b = RunStore(db_b)
    try:
        handle_b = await runtime_b.resume(run_id, AskChoice(value="近 3 天"))
        # 闸持有期：run 行已回写 running（C1——修复前此处停留 waiting_ask＝断档）。
        during = await store_b.get_run(run_id)
        assert during is not None and during.status == "running"
        gate.gate.set()
        await drain(handle_b)
        run = await store_b.get_run(run_id)
        assert run is not None and run.status == "completed"
        # 全程 step 留痕无断档：seq 自 1 起连续，恢复段在挂起段基础上续写。
        steps = await store_b.list_steps(run_id)
        seqs = [s.seq for s in steps]
        assert seqs == list(range(1, len(seqs) + 1))
        assert len(seqs) > steps_a_count > 0  # 恢复段续写非清零重演
    finally:
        await db_b.dispose()


async def test_mark_running_transition_guard(tmp_path: Path) -> None:
    """状态机转移合法性把守：仅 waiting_ask→running；越界转移拒写。"""
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=HAPPY_SCRIPT
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        try:
            await store.mark_running(handle.run_id)
        except ValueError:
            pass
        else:
            raise AssertionError("终态 run 未拒绝 running 回写（状态机越界）")
        run_again = await store.get_run(handle.run_id)
        assert run_again is not None and run_again.status == "completed"
    finally:
        await db.dispose()


# ---------- who 兜底钉测：空 actor 缺省落默认角色（00 §2.4 口径） ----------


async def test_audit_who_default_role_fallback(tmp_path: Path) -> None:
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=HAPPY_SCRIPT
    )
    try:
        handle = await runtime.ask(
            AskRequest(question=HAPPY_QUESTION, actor=Actor(user_id="", display=""))
        )
        await drain(handle)
        rows = await _audit_rows(db)
        assert rows, "审计行未落"
        assert rows[0].who == "阿强 · 平台运维"  # resolve_actor 缺省角色（PRD 拍板）
    finally:
        await db.dispose()
