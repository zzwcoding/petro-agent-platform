"""V2-06 PgCheckpointer 落 PG 集成测试——挂起态跨实例恢复（specs/agent-loop.md
行为约定 8：进程重启后可恢复 waiting_ask 态，resume 可达）。

约定（tests/infra/test_db_pg.py 同款）：环境变量 TEST_DATABASE_URL 未配置即 skip；
环境变量只定位服务器与凭据——测试落 <库名>_test 独立库（测试/演示库分离），
跑后清 agent_v2_checkpoint 三表（run/step 行随库保留无害——幂等重建）。

sqlite 单测底座（tests/domains/test_v2_agent_loop.py::run_recover_after_restart）
已钉跨实例恢复语义；本测试补真 PG 面——checkpoint/blob/write 三表 bytea 往返
＋serde 序列化在 PG 方言下的跨实例（两个独立 ConnectionManager）恢复。
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Sequence
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.infra.security import Actor
from appv2.query import (
    ASKBACK_TIME_CHOICES,
    ASKBACK_TIME_QUESTION,
    LINEAGE_KEY_CALIBER,
    LineageLine,
    QueryOutcome,
)
from appv2.runtime import (
    AgentRuntime,
    AskChoice,
    AskRequest,
    PgCheckpointer,
    RunStore,
    ScriptedCompleter,
    ensure_agent_v2_tables,
)
from appv2.runtime.executor import GraphRunExecutor
from appv2.runtime.llm import GatewayChatModel
from appv2.tools import FakeKnowledgeStore, FakeQueryEngine, FakeRetrievalEngine, ToolRegistry

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
TODAY = date(2026, 10, 8)
ACTOR = Actor(user_id="dev-u1", display="开发用户")

_VAGUE_DECISION = (
    '{"action": "execute", "task_type": "data", '
    '"plan": {"metric_slot": "日产油量", "ranking": false}}'
)
_WINDOWED_DECISION = (
    '{"action": "execute", "task_type": "data", '
    '"plan": {"metric_slot": "日产油量", "ranking": false, '
    '"window_start": "2025-09-01", "window_end": "2025-09-03", "limit": 5}}'
)
# 剧本按段分装（ScriptedCompleter 按 caller FIFO——A 段模糊计划出 clarify，
# B 段起带窗计划＋定稿）。
_SCRIPT_A: dict[str, Sequence[str]] = {
    "v2.runtime.understand": ["理解：问最近的日产油量。\n指标候选：日产油量"],
    "v2.runtime.decision": [_VAGUE_DECISION],
}
_SCRIPT_B: dict[str, Sequence[str]] = {
    "v2.runtime.understand": ["理解：问最近的日产油量。\n指标候选：日产油量"],
    "v2.runtime.decision": [_WINDOWED_DECISION, '{"action": "finalize"}'],
    "v2.runtime.answer": ["N-01 井 21.16 吨[1]。"],
}


def _isolated_url() -> URL:
    url = make_url(TEST_DATABASE_URL)
    return url.set(database=f"{url.database}_test")


async def _ensure_test_database(url: URL) -> None:
    admin = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = (
                await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": url.database},
                )
            ).scalar()
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        await admin.dispose()


def _spec(url: URL) -> DatabaseSpec:
    return DatabaseSpec(
        name="primary",
        role="primary",
        driver="postgresql",
        host=url.host or "localhost",
        port=url.port or 5433,
        database=url.database or "",
        user=url.username or "",
        password=url.password or "",
        pool_size=2,
        max_overflow=1,
    )


@pytest.fixture
async def pg_url() -> AsyncIterator[URL]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL 未配置——PG 集成测试跳过（约定见票面）")
    url = _isolated_url()
    await _ensure_test_database(url)
    yield url
    # 跑后清 checkpoint 三表（跨测幂等；run/step 行随 truncate 一并清）。
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        for table in (
            "agent_v2_checkpoint_write",
            "agent_v2_checkpoint_blob",
            "agent_v2_checkpoint",
            "agent_v2_step",
            "agent_v2_run",
        ):
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
    await engine.dispose()


def _engine_script(*, segment: str) -> FakeQueryEngine:
    """引擎剧本按段分装：A 段＝need_clarify（挂起源）；B 段＝rows（恢复段出数）。"""
    if segment == "a":
        outcomes = [
            QueryOutcome.need_clarify(
                question=ASKBACK_TIME_QUESTION,
                choices=ASKBACK_TIME_CHOICES,
            ),
            QueryOutcome.rows_with_lineage(
                columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
                rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
                lineage=(LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量口径"),),
            ),
        ]

        class QueueEngine(FakeQueryEngine):
            def run(self, plan: object) -> QueryOutcome:
                self.run_calls += 1
                return outcomes.pop(0) if len(outcomes) > 1 else outcomes[0]

        return QueueEngine()

    class RowsEngine(FakeQueryEngine):
        def run(self, plan: object) -> QueryOutcome:
            self.run_calls += 1
            return QueryOutcome.rows_with_lineage(
                columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
                rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
                lineage=(LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量口径"),),
            )

    return RowsEngine()


def _runtime(
    db: ConnectionManager,
    engine: FakeQueryEngine,
    script: dict[str, Sequence[str]],
) -> AgentRuntime:
    registry = ToolRegistry(
        knowledge=FakeKnowledgeStore(),
        query=engine,
        retrieval=FakeRetrievalEngine(),
    )
    completer = ScriptedCompleter(script)
    models = {
        name: GatewayChatModel(completer=completer, caller=f"v2.runtime.{name}", alias="")
        for name in ("understand", "decision", "answer")
    }
    return AgentRuntime(
        GraphRunExecutor(
            registry=registry,
            models=models,
            db=db,
            saver=PgCheckpointer(db),
        )
    )


async def test_checkpoint_roundtrip_on_pg(pg_url: URL) -> None:
    # 实例 A：提问→need_clarify 挂起（checkpoint 落 PG）。
    db_a = ConnectionManager([_spec(pg_url)])
    try:
        await ensure_agent_v2_tables(db_a.engine())
        engine = _engine_script(segment="a")
        runtime_a = _runtime(db_a, engine, _SCRIPT_A)
        handle = await runtime_a.ask(AskRequest(question="最近的日产油量", actor=ACTOR))
        events = [e async for e in handle.stream]
        assert any(e.event == "ask" for e in events)
        run_id = handle.run_id
        store_a = RunStore(db_a)
        run = await store_a.get_run(run_id)
        assert run is not None and run.status == "waiting_ask"
        assert await store_a.count_checkpoints(run_id) > 0  # checkpoint 落 PG
    finally:
        await db_a.dispose()

    # 实例 B（全新 ConnectionManager——同 PG 库）：凭 run_id resume 续跑完成。
    db_b = ConnectionManager([_spec(pg_url)])
    try:
        await ensure_agent_v2_tables(db_b.engine())
        engine_b = _engine_script(segment="b")
        runtime_b = _runtime(db_b, engine_b, _SCRIPT_B)
        store_b = RunStore(db_b)
        run_b = await store_b.get_run(run_id)
        assert run_b is not None and run_b.status == "waiting_ask"
        handle_b = await runtime_b.resume(run_id, AskChoice(value="近 3 天"))
        events_b = [e async for e in handle_b.stream]
        assert any(e.event == "citation" for e in events_b)
        run_b = await store_b.get_run(run_id)
        assert run_b is not None and run_b.status == "completed"
        assert "21.16" in (run_b.answer or "")
        assert engine_b.run_calls == 1  # 澄清段零执行；恢复段执行一次
    finally:
        await db_b.dispose()
