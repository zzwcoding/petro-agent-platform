"""retrieval 族 PG 集成——逐列断言（99 §2.10＋基线列）＋FK＋版本链/via 回链/在途 409 真库实证。

跑法：TEST_DATABASE_URL=postgresql://...@localhost:5433/petro uv run pytest
tests/domains/retrieval/test_retrieval_tables_pg.py -q（未配置即 skip——约定见票面）。
"""

import asyncio
import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.retrieval import (
    ChangeRequestReceipt,
    RetrievalConflictError,
    RetrievalParamError,
    RetrievalService,
)
from app.domains.retrieval.store import ensure_retrieval_tables
from app.infra.clock import freeze
from app.infra.db import ConnectionManager, DatabaseSpec
from tests.domains.retrieval.conftest import version_rows

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

_TABLES = ("retrieval_config", "retrieval_config_version")


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
    await ensure_retrieval_tables(engine)  # 幂等建表（P0-04 惯例）
    await engine.dispose()
    yield manager
    await manager.dispose()


def _service(db: ConnectionManager) -> RetrievalService:
    return RetrievalService(db)


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


async def test_retrieval_tables_columns_and_fk(db: ConnectionManager) -> None:
    """两表逐列断言（99 §2.10 关键列＋基线列）＋生效指针 FK。"""
    expected = {
        "retrieval_config": {"id", "current_version_no", "created_at", "updated_at"},
        "retrieval_config_version": {
            "version_no", "config", "updated_at", "updated_by", "via", "created_at",
        },
    }
    for table, columns in expected.items():
        actual = await _columns(db, table)
        missing = columns - actual
        assert not missing, f"{table} 缺列: {missing}"
    async with db.session() as session:
        fk = (
            await session.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE contype = 'f' AND conrelid = 'retrieval_config'::regclass"
                )
            )
        ).scalars().all()
        jsonb_kind = (
            await session.execute(
                text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name = 'retrieval_config_version' AND column_name = 'config'"
                )
            )
        ).scalar_one()
    assert any("current_version_no" in name for name in fk), fk  # 生效指针 FK
    assert jsonb_kind == "jsonb"  # 99 §1.5 jsonb 列


async def test_version_chain_via_backlink_on_pg(db: ConnectionManager) -> None:
    """版本推进链＋via 回链（真库）：种子 v1（via 空）→ 两单受理 v2/v3（via=单号）。"""
    service = _service(db)
    with freeze("2026-10-02 12:00:00"):
        snapshot = await service.effective_config()
        assert snapshot.version.no == "v1" and snapshot.version.via is None
        first = await service.submit_change_request({"rerank": "llm"}, updated_by="阿强 · 平台运维")
        second = await service.submit_change_request(
            {
                "params": {
                    "semantic_top_k": 12,
                    "keyword_top_k": 20,
                    "merge": "rrf_rank",
                    "top_n": 20,
                }
            },
            updated_by="阿强 · 平台运维",
        )
    rows = await version_rows(db)
    assert [r.version_no for r in rows] == ["v1", "v2", "v3"]
    assert [r.via for r in rows] == [None, first.change_request_id, second.change_request_id]
    assert first.change_request_id == "#CFG-20261002-01"
    assert second.change_request_id == "#CFG-20261002-02"
    async with db.session() as session:
        pointer_no = (
            await session.execute(text("SELECT current_version_no FROM retrieval_config"))
        ).scalar_one()
    assert pointer_no == "v3"  # 生效指针随受理切换
    final = await service.effective_config()
    assert final.params.semantic_top_k == 12 and final.rerank == "llm"


async def test_out_of_range_400_with_range_on_pg(db: ConnectionManager) -> None:
    """越界 400 带区间（D2 错误码草案——D1 先例同形）；失败路径零写。"""
    service = _service(db)
    with pytest.raises(RetrievalParamError) as ei:
        await service.submit_change_request(
            {
                "qa_behavior": {
                    "faq_direct_hit": True,
                    "refuse_threshold": 0.4,
                    "clarify_strategy": "ask_missing",
                    "confidence_thresholds": {"high": 0.8, "low": 0.4},
                    "faq_expand_rounds": 0,
                }
            },
            updated_by="阿强 · 平台运维",
        )
    assert ("patch.qa_behavior.faq_expand_rounds", "1–5") in ei.value.violations
    assert await version_rows(db) == []


async def test_concurrent_submit_409_on_pg(db: ConnectionManager) -> None:
    """在途 409（并发受理撞闸——阶段 1 受理→生效一体，在途窗口＝受理处理期）。"""
    service = _service(db)
    results = await asyncio.gather(
        service.submit_change_request({"rerank": "llm"}, updated_by="阿强 · 平台运维"),
        service.submit_change_request({"rerank": "compound"}, updated_by="阿强 · 平台运维"),
        return_exceptions=True,
    )
    receipts = [r for r in results if isinstance(r, ChangeRequestReceipt)]
    conflicts = [r for r in results if isinstance(r, RetrievalConflictError)]
    assert len(receipts) == 1 and len(conflicts) == 1
    rows = await version_rows(db)
    assert [r.version_no for r in rows] == ["v1", "v2"]  # 版本轴只推进一次
