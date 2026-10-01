"""faq 族 PG 集成——四表逐列断言（99 §2.6 关键列＋基线列）＋CHECK/索引。

跑法：TEST_DATABASE_URL=postgresql://...@localhost:5433/petro uv run pytest
tests/domains/faq/test_faq_tables_pg.py -q（未配置即 skip——约定见票面）。
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.faq.store import CandidateStore, ensure_faq_tables, seed_demo_if_empty
from app.infra.db import ConnectionManager, DatabaseSpec

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

_TABLES = ("faq_entry", "faq_similar_question", "faq_candidate", "faq_scan_task")


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
    await ensure_faq_tables(engine)  # 幂等建表（P0-04 惯例）
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


async def test_faq_tables_columns_match_99(db: ConnectionManager) -> None:
    """faq 族逐列断言（99 §2.6 关键列＋基线列 created_at/updated_at）。"""
    expected = {
        "faq_entry": {
            "id", "question", "question_norm", "norm_hash", "answer", "status",
            "is_negative", "hook_kind", "hook_name", "version", "maintainer",
            "created_at", "updated_at",
        },
        "faq_similar_question": {
            "id", "entry_id", "text", "text_norm", "created_at", "updated_at",
        },
        "faq_candidate": {
            "id", "question", "variants", "freq", "window", "status", "compare",
            "draft", "hook_kind", "hook_name", "source_entry_id",
            "created_at", "updated_at",
        },
        "faq_scan_task": {
            "id", "status", "new_cluster_count", "new_clusters", "hint",
            "started_at", "finished_at", "created_at", "updated_at",
        },
    }
    for table, columns in expected.items():
        actual = await _columns(db, table)
        missing = columns - actual
        assert not missing, f"{table} 缺列: {missing}"
    # 差异登记列（票面 P1-06）：faq_entry.is_negative NOT NULL——待审核行承载
    # 负例登记意向，审核 publish 落定 negative
    async with db.session() as session:
        row = (
            await session.execute(
                text(
                    "SELECT is_nullable FROM information_schema.columns "
                    "WHERE table_name = 'faq_entry' AND column_name = 'is_negative'"
                )
            )
        ).scalar_one()
    assert row == "NO"


async def test_faq_checks_and_indexes(db: ConnectionManager) -> None:
    async with db.session() as session:
        entry_checks = (
            await session.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE contype = 'c' AND conrelid = 'faq_entry'::regclass"
                )
            )
        ).scalars().all()
        cand_checks = (
            await session.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE contype = 'c' AND conrelid = 'faq_candidate'::regclass"
                )
            )
        ).scalars().all()
        scan_checks = (
            await session.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE contype = 'c' AND conrelid = 'faq_scan_task'::regclass"
                )
            )
        ).scalars().all()
        entry_indexes = (
            await session.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = 'faq_entry'")
            )
        ).scalars().all()
        sim_indexes = (
            await session.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = 'faq_similar_question'")
            )
        ).scalars().all()
        cand_indexes = (
            await session.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = 'faq_candidate'")
            )
        ).scalars().all()
    assert "ck_faq_entry_status" in entry_checks  # pending_review,serve,negative,disabled
    assert "ck_faq_entry_hook_kind" in entry_checks
    assert "ck_faq_candidate_status" in cand_checks  # pending,compared,drafted,published
    assert "ck_faq_candidate_hook_kind" in cand_checks
    assert "ck_faq_scan_task_status" in scan_checks  # running,done（双态）
    assert "ix_faq_entry_status" in entry_indexes
    assert "ix_faq_similar_entry" in sim_indexes
    assert "ix_faq_similar_text_norm" in sim_indexes  # 重复添加 409 判据列
    assert "ix_faq_candidate_freq" in cand_indexes  # 频次倒序排序列


async def test_seed_demo_if_empty_idempotent_on_pg(db: ConnectionManager) -> None:
    """演示种子幂等：首跑装载九条问答＋四簇候选；重跑零写入。"""
    engine = db.engine()
    await seed_demo_if_empty(engine)
    async with db.session() as session:
        entries = (
            await session.execute(text("SELECT count(*) FROM faq_entry"))
        ).scalar_one()
        sims = (
            await session.execute(text("SELECT count(*) FROM faq_similar_question"))
        ).scalar_one()
        candidates = (
            await session.execute(text("SELECT count(*) FROM faq_candidate"))
        ).scalar_one()
        statuses = (
            await session.execute(
                text("SELECT status, count(*) FROM faq_entry GROUP BY status")
            )
        ).all()
    assert entries == 9 and sims == 3 and candidates == 4
    status_map = {s: n for s, n in statuses}
    assert status_map.get("serve") == 7
    assert status_map.get("disabled") == 1
    assert status_map.get("negative") == 1
    assert status_map.get("pending_review", 0) == 0  # 种子直接发布（合同）
    await seed_demo_if_empty(engine)  # 重跑幂等——零写入
    async with db.session() as session:
        again = (
            await session.execute(text("SELECT count(*) FROM faq_entry"))
        ).scalar_one()
    assert again == 9


async def test_candidate_writeback_fk_order_on_pg(db: ConnectionManager) -> None:
    """候选回写链真库 FK 实证：携 source_candidate_id 入库（回写锚 source_entry_id
    随新增事务登记）→ 审核发布 → 候选 published 零悬挂。

    回归看守：无 relationship 的 UOW 不保证 FK 插序——回写锚 UPDATE 先于条目
    INSERT 发出即撞 faq_candidate_source_entry_id_fkey（PG 即时 FK 检查；sqlite
    单测 FK 默认关不显，P1-02a flush 排序先例同款，真装配冒烟实证）。
    """
    from tests.domains.faq.conftest import (
        FakeObjectStorage,
        StubCompleter,
        make_service,
    )

    await seed_demo_if_empty(db.engine())
    service = make_service(db, StubCompleter(), FakeObjectStorage())
    created = await service.create_entry(
        "时率怎么算？",
        "时率＝1 −（检出时率损失…）。",
        is_negative=False,
        hook=None,
        source_candidate_id="c1",
        actor_who="阿强",
    )
    assert created.status == "pending_review"
    assert created.candidate is not None and created.candidate.id == "c1"
    row = await CandidateStore(db).get("c1")
    assert row is not None and row.source_entry_id == created.id  # 锚随新增事务落库
    reviewed = await service.review_entry(created.id, "publish", actor_who="阿强")
    assert reviewed.status == "serve"
    row = await CandidateStore(db).get("c1")
    assert row is not None and row.status == "published"  # 发布事务内落 published
