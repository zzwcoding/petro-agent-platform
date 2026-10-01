"""kb 八表 PG 集成测试——99 §2.5 逐字段落位与 CHECK/jsonb/pgvector 真库断言。

约定同 gateway/semantics PG 组（tickets/phase0 P0-03 起）：TEST_DATABASE_URL
未配置即 skip；测试自动改用 <库名>_test 独立库（测试/演示库分离）。
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.kb.domain import LocalHashEmbedder
from app.domains.kb.store import (
    ActivityRow,
    FragmentRow,
    FragmentVersionRow,
    IngestTaskRow,
    LibraryConfigRow,
    LibraryRow,
    ReportRow,
    UploadRow,
    ensure_kb_tables,
)
from app.infra.clock import now
from app.infra.db import ConnectionManager, DatabaseSpec

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

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


async def _columns(db: ConnectionManager, table: str) -> set[str]:
    async with db.session() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :t"
                ),
                {"t": table},
            )
        ).scalars().all()
    return set(rows)


async def test_kb_tables_columns_match_99(db: ConnectionManager) -> None:
    """kb 族逐列断言（99 §2.5 关键列＋基线列 created_at/updated_at）。"""
    expected = {
        "kb_library": {"id", "name", "biz_template", "status", "created_at", "updated_at"},
        "kb_library_config": {
            "lib_id", "semantic", "keyword", "wiki", "graph", "mode",
            "add_summary", "add_questions", "saved_at", "saved_by",
            "created_at", "updated_at",
        },
        "kb_upload": {
            "id", "filename", "size", "lib_id", "bucket", "status", "expires_at",
            "suggested_topic", "routed_lib_id", "route_confirmed_by", "object_key",
            "created_at", "updated_at",
        },
        "kb_report": {
            "id", "lib_id", "doc", "subject", "status", "related_objects",
            "object_key", "wiki_current_version", "created_at", "updated_at",
        },
        "kb_ingest_task": {
            "id", "upload_id", "report_id", "lib_id", "state", "source",
            "current_step", "stop_at", "reason", "nodes", "config_snapshot",
            "extract_snapshot", "started_at", "finished_at", "created_at", "updated_at",
        },
        "kb_fragment": {
            "id", "report_id", "type", "section", "well", "hit_text",
            "current_version", "is_parent_only", "embedding", "created_at", "updated_at",
        },
        "kb_fragment_version": {
            "fragment_id", "v", "text", "context_text", "note", "created_at", "updated_at",
        },
        "kb_issue_report": {
            "id", "fragment_id", "state", "reject_reason", "marked_by", "marked_at",
            "reviewed_by", "reviewed_at", "created_at", "updated_at",
        },
        "kb_activity": {
            "id", "lib_id", "time", "who", "action", "target", "created_at", "updated_at",
        },
    }
    for table, columns in expected.items():
        actual = await _columns(db, table)
        missing = columns - actual
        assert not missing, f"{table} 缺列: {missing}"
    # 路由三列可空（差异登记：kb_upload.lib_id 路由流受理时未定）
    async with db.session() as session:
        nullables = (
            await session.execute(
                text(
                    "SELECT column_name, is_nullable FROM information_schema.columns "
                    "WHERE table_name = 'kb_upload' "
                    "AND column_name IN ('lib_id','suggested_topic','routed_lib_id')"
                )
            )
        ).all()
    assert all(row[1] == "YES" for row in nullables)


async def test_kb_checks_and_indexes(db: ConnectionManager) -> None:
    async with db.session() as session:
        checks = (
            await session.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE contype = 'c' AND conrelid = 'kb_library'::regclass"
                )
            )
        ).scalars().all()
        task_checks = (
            await session.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE contype = 'c' AND conrelid = 'kb_ingest_task'::regclass"
                )
            )
        ).scalars().all()
        indexes = (
            await session.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = 'kb_ingest_task'")
            )
        ).scalars().all()
        frag_indexes = (
            await session.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = 'kb_fragment'")
            )
        ).scalars().all()
        act_indexes = (
            await session.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = 'kb_activity'")
            )
        ).scalars().all()
    assert "ck_kb_library_biz_template" in checks
    assert "ck_kb_library_status" in checks
    assert "ck_kb_ingest_task_state" in task_checks
    assert "ck_kb_ingest_task_source" in task_checks
    assert "ix_kb_ingest_task_lib_started" in indexes
    assert "ix_kb_ingest_task_source" in indexes
    assert "ix_kb_fragment_report" in frag_indexes
    assert "ix_kb_fragment_type" in frag_indexes
    assert "ix_kb_activity_lib_time" in act_indexes
    # kb_issue_report（B2/P1-04）：state 索引＋待质检复核态部分唯一索引（99 注记
    # 「uq fragment_id」语义锚＝待质检复核态重复标记 409——全列 uq 会卡死重新标记）
    issue_indexes = (
        await session.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'kb_issue_report'")
        )
    ).scalars().all()
    assert "ix_kb_issue_report_state" in issue_indexes
    assert "uq_kb_issue_report_pending_fragment" in issue_indexes
    partial = (
        await session.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'uq_kb_issue_report_pending_fragment'"
            )
        )
    ).scalar_one()
    assert "待质检复核" in partial  # WHERE 子句在（部分唯一）


async def test_kb_ingest_task_state_check_enforced(db: ConnectionManager) -> None:
    async with db.session() as session:
        session.add(LibraryRow(id="lib-1", name="库", biz_template="blank", status="active"))
    async with db.session() as session:
        session.add(
            ReportRow(id="rpt-1", lib_id="lib-1", doc="《X》", object_key="k")
        )
    async with db.session() as session:
        session.add(
            IngestTaskRow(
                id="task-ok", upload_id=None, report_id="rpt-1", lib_id="lib-1",
                state="running", source="上传入库", current_step=0, nodes=[],
                config_snapshot={}, started_at=now(),
            )
        )
    async with db.session() as session:
        session.add(
            IngestTaskRow(
                id="task-bad", upload_id=None, report_id="rpt-1", lib_id="lib-1",
                state="paused", source="上传入库", current_step=0, nodes=[],
                config_snapshot={}, started_at=now(),
            )
        )
        with pytest.raises(IntegrityError):  # CHECK(running,done,failed,stuck)
            await session.flush()
        await session.rollback()


async def test_kb_fragment_pgvector_roundtrip(db: ConnectionManager) -> None:
    """向量列真库往返（pgvector vector(384)——99 册向量半边的物理落点）。"""
    async with db.session() as session:
        kind = (
            await session.execute(
                text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name = 'kb_fragment' AND column_name = 'embedding'"
                )
            )
        ).scalar_one()
    assert kind == "USER-DEFINED"  # vector 类型（pgvector 扩展承载）
    vector = (await LocalHashEmbedder().embed(["渤中28-1 井完井报告"]))[0]
    async with db.session() as session:
        session.add(LibraryRow(id="lib-v", name="向量库", biz_template="blank", status="active"))
    async with db.session() as session:
        session.add(ReportRow(id="rpt-v", lib_id="lib-v", doc="《V》", object_key="k"))
    async with db.session() as session:  # 父行先落（无 relationship 不保证 UOW 排序）
        session.add(
            FragmentRow(
                id="f1", report_id="rpt-v", type="原文块", section="正文",
                current_version=1, is_parent_only=False, embedding=vector,
            )
        )
        session.add(
            FragmentVersionRow(
                fragment_id="f1", v=1, text="渤中28-1 井完井报告", note="原始解析"
            )
        )
    async with db.session() as session:
        row = await session.get(FragmentRow, "f1")
        assert row is not None and row.embedding is not None
        assert len(row.embedding) == len(vector)
        assert row.embedding[0] == pytest.approx(vector[0], abs=1e-5)


async def test_kb_upload_routing_columns_and_activity_roundtrip(db: ConnectionManager) -> None:
    """路由三列落库（suggested_topic/routed_lib_id/route_confirmed_by）＋活动流追加。"""
    async with db.session() as session:
        session.add(
            LibraryRow(id="lib-r", name="路由库", biz_template="completion", status="active")
        )
    async with db.session() as session:
        session.add(
            UploadRow(
                id="up-1", filename="N-02 井完井报告.pdf", size=1024, lib_id=None,
                bucket="reports", status="pending", expires_at=now(),
                suggested_topic="完井投产", object_key="reports/up-1/x.pdf",
            )
        )
    async with db.session() as session:
        row = await session.get(UploadRow, "up-1")
        assert row is not None
        row.status = "confirmed"
        row.routed_lib_id = "lib-r"
        row.route_confirmed_by = "阿强 · 平台运维"
    async with db.session() as session:
        session.add(
            ActivityRow(
                lib_id="lib-r", time=now(), who="阿强 · 平台运维",
                action="上传报告", target="《N-02 井完井报告》",
            )
        )
    async with db.session() as session:
        row = await session.get(UploadRow, "up-1")
        assert row is not None and row.routed_lib_id == "lib-r"
        count = (
            await session.execute(text("SELECT count(*) FROM kb_activity"))
        ).scalar_one()
    assert count == 1


async def test_kb_library_config_mode_check(db: ConnectionManager) -> None:
    async with db.session() as session:
        session.add(LibraryRow(id="lib-c", name="配置库", biz_template="blank", status="active"))
    async with db.session() as session:
        session.add(
            LibraryConfigRow(
                lib_id="lib-c", semantic=True, keyword=True, wiki=True, graph=False,
                mode="smart", add_summary=True, add_questions=True,
            )
        )
    async with db.session() as session:
        session.add(
            LibraryConfigRow(
                lib_id="lib-c2", semantic=True, keyword=True, wiki=True, graph=False,
                mode="chunked", add_summary=True, add_questions=True,
            )
        )
        with pytest.raises(IntegrityError):  # CHECK(smart,fixed,mixed)
            await session.flush()
        await session.rollback()
