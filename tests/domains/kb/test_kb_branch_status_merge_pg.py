"""branch_status 键级合并 PG 集成测试（DE-15——jsonb `||` 路径实证）。

约定同 kb 族 PG 组（tests/domains/kb/test_kb_tables_pg.py）：TEST_DATABASE_URL
未配置即 skip；自动改用 <库名>_test 独立库（测试/演示库分离）。

sqlite 底座走 json_set 路径、PG 走 jsonb `||`——两侧「只覆盖 patch 顶层键、
他键原样保留」同语义，本文件钉 PG 侧：交错写两键均存、整行 save 不抹键、
顶层键整值替换、chunk_check/wiki/graph 三键共存。
"""

import asyncio
import os
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.kb import KbService
from app.domains.kb.store import (
    IngestTaskRow,
    LibraryRow,
    ReportRow,
    TaskStore,
    ensure_kb_tables,
)
from app.infra.clock import now
from app.infra.db import ConnectionManager, DatabaseSpec
from tests.domains.kb.conftest import FakeObjectStorage, StubCompleter

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

TASK_ID = "task-de15pg"

_TABLES = (
    "kb_library",
    "kb_library_config",
    "kb_upload",
    "kb_report",
    "kb_ingest_task",
    "kb_fragment",
    "kb_fragment_version",
    "kb_issue_report",
    "kb_activity",
)


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
        driver=url.drivername.split("+", 1)[0],
        host=url.host or "localhost",
        port=url.port or 5433,
        database=url.database or "",
        user=url.username or "",
        password=url.password or "",
        pool_size=2,
        max_overflow=1,
    )


@pytest.fixture
async def db() -> AsyncIterator[ConnectionManager]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL 未配置——PG 集成测试跳过（约定见票面）")
    url = _isolated_url()
    await _ensure_test_database(url)
    manager = ConnectionManager([_spec(url)])
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        for table in _TABLES:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
    await ensure_kb_tables(engine)  # 幂等建表（含 CREATE EXTENSION IF NOT EXISTS vector）
    await engine.dispose()
    yield manager
    await manager.dispose()


async def _seed_task(manager: ConnectionManager) -> str:
    async with manager.session() as session:
        session.add(LibraryRow(id="lib-de15pg", name="DE15 PG 库", biz_template="completion"))
        await session.flush()  # 父行先落（无 relationship 不保证 UOW 插序——store 惯例）
        session.add(
            ReportRow(
                id="rpt-de15pg",
                lib_id="lib-de15pg",
                doc="DE15 PG 报告",
                object_key="de15pg/doc.txt",
            )
        )
        await session.flush()
        session.add(
            IngestTaskRow(
                id=TASK_ID,
                report_id="rpt-de15pg",
                lib_id="lib-de15pg",
                state="running",
                source="上传入库",
                current_step=0,
                nodes=[],
                config_snapshot={},
                started_at=now(),
            )
        )
    return TASK_ID


def _service(manager: ConnectionManager) -> KbService:
    return KbService(manager, StubCompleter(), FakeObjectStorage())


class TestBranchStatusKeyLevelMergePg:
    """jsonb `||` 路径：键级合并语义与交错保全（DE-15 PG 侧实证）。"""

    async def test_interleaved_writes_keep_both_keys(self, db: ConnectionManager) -> None:
        """wiki done ∥ graph 进度并发写——jsonb || 浅合并，终态两键均保留。"""
        service = _service(db)
        task_id = await _seed_task(db)

        async def wiki_writer() -> None:
            for i in range(10):
                await service.set_branch_status(task_id, "wiki", "running", detail=f"生成中 {i}")
            await service.set_branch_status(task_id, "wiki", "done")

        async def graph_writer() -> None:
            for i in range(1, 11):
                await service.set_branch_status(
                    task_id,
                    "graph",
                    "running",
                    extra={"chunks_done": i, "chunks_total": 10, "edges": i * 2, "blocked": 1},
                )
            await service.set_branch_status(
                task_id,
                "graph",
                "done",
                extra={"chunks_done": 10, "chunks_total": 10, "edges": 20, "blocked": 1},
            )

        await asyncio.gather(wiki_writer(), graph_writer())

        branches = (await service.ingest_task(task_id)).branches
        assert branches["wiki"] == {"state": "done"}, f"wiki 键被并发写抹掉：{branches}"
        graph = branches["graph"]
        assert graph["state"] == "done", f"graph 键被并发写抹掉：{branches}"
        assert graph["chunks_done"] == 10 and graph["edges"] == 20

    async def test_full_row_save_keeps_branch_key(self, db: ConnectionManager) -> None:
        """整行 save 不携 branch_status（列归属键级写口）——并发支路键存活。"""
        service = _service(db)
        store = TaskStore(db)
        task_id = await _seed_task(db)

        row = await store.get(task_id)
        assert row is not None
        await service.set_branch_status(
            task_id,
            "graph",
            "running",
            extra={"chunks_done": 1, "chunks_total": 3, "edges": 0, "blocked": 0},
        )
        row.state = "running"
        row.current_step = 2
        await store.save(row)

        branches = (await service.ingest_task(task_id)).branches
        assert branches.get("graph", {}).get("chunks_done") == 1, (
            f"整行 save 抹掉并发支路键：{branches}"
        )

    async def test_shallow_replace_and_three_keys_coexist(self, db: ConnectionManager) -> None:
        """顶层键整值替换（jsonb || 浅合并不深并）＋ chunk_check 三键共存。"""
        service = _service(db)
        task_id = await _seed_task(db)

        await service.set_branch_status(task_id, "wiki", "running", detail="生成中")
        await service.set_branch_status(task_id, "wiki", "done")
        await service.set_branch_status(
            task_id,
            "chunk_check",
            "warn",
            detail="切块自检 2 条违规",
            extra={"violations": 2, "evidence": "/tmp/chunk_validate_de15pg.md"},
        )
        await service.set_branch_status(
            task_id, "graph", "done", extra={"chunks_total": 3, "chunks_done": 3}
        )

        branches: dict[str, Any] = (await service.ingest_task(task_id)).branches
        assert branches["wiki"] == {"state": "done"}  # 旧 detail 不残留（浅合并）
        assert branches["chunk_check"] == {
            "state": "warn",
            "detail": "切块自检 2 条违规",
            "violations": 2,
            "evidence": "/tmp/chunk_validate_de15pg.md",
        }
        assert branches["graph"] == {"state": "done", "chunks_total": 3, "chunks_done": 3}
