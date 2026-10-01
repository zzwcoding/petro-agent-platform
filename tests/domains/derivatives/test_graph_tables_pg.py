"""kb_extract_config PG 集成测试——99 §2.7 逐字段落位与仓储真库往返。

约定同 kb/semantics PG 组（tickets/phase0 P0-03 起）：TEST_DATABASE_URL 未配
置即 skip；测试自动改用 <库名>_test 独立库（测试/演示库分离）。
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.derivatives import domain as d
from app.domains.derivatives.store import ExtractConfigStore, ensure_derivatives_tables
from app.domains.kb import KbService
from app.domains.kb.store import ensure_kb_tables
from app.infra.db import ConnectionManager, DatabaseSpec
from tests.domains.kb.conftest import FakeObjectStorage, StubCompleter

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")


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
        for table in ("kb_extract_config", "kb_library", "kb_library_config"):
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
    await ensure_kb_tables(engine)
    await ensure_derivatives_tables(engine)
    await engine.dispose()
    yield manager
    await manager.dispose()


async def test_kb_extract_config_columns_and_fk(db: ConnectionManager) -> None:
    """kb_extract_config 逐列＋FK 断言（99 §2.7：lib_id PK FK＋四段 jsonb＋
    few_shot_examples 增列＋saved_at/saved_by）。"""
    async with db.session() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns WHERE table_name = 'kb_extract_config'"
                )
            )
        ).all()
    columns = {r[0]: (r[1], r[2]) for r in rows}
    assert set(columns) == {
        "lib_id", "entity_types", "relation_tags", "custom_instructions",
        "few_shot_examples", "saved_at", "saved_by",
    }
    assert columns["lib_id"] == ("character varying", "NO")
    for col in ("entity_types", "relation_tags", "few_shot_examples"):
        assert columns[col][0] == "jsonb", col
    async with db.session() as session:
        fk = (
            await session.execute(
                text(
                    "SELECT 1 FROM pg_constraint WHERE conrelid = "
                    "'kb_extract_config'::regclass AND contype = 'f'"
                )
            )
        ).all()
    assert fk  # FK 约束存在（lib_id → kb_library.id——99 §2.7）


async def test_extract_config_store_pg_roundtrip(db: ConnectionManager) -> None:
    """仓储真库往返：save→config_of→覆盖写（整存整取＋saved_by 留痕）。"""
    kb = KbService(db, StubCompleter(), FakeObjectStorage())
    lib = await kb.create_library("PG·完井报告库", "completion", "aqiang · 平台运维")
    store = ExtractConfigStore(db)
    cfg = d.ExtractConfig(
        entity_types=["井", "区块", "平台", "油田", "措施"],
        relation_tags=[d.RelationTag(rel="隶属", example="N-02 —隶属→ 渤南", desc="d")],
        custom_instructions="关系必须原文有依据",
        few_shot_examples=[d.FewShotPair(sentence="s", triple="t")],
    )
    await store.save(lib.lib_id, cfg, actor_who="小李 · 地质/质检")
    row = await store.config_of(lib.lib_id)
    assert row is not None
    assert row.entity_types == cfg.entity_types
    assert row.relation_tags[0]["rel"] == "隶属"
    assert row.few_shot_examples == [{"sentence": "s", "triple": "t"}]
    assert row.saved_by == "小李 · 地质/质检" and row.saved_at is not None
    # 覆盖写（整存整取——无版本轴，下次入库定型）
    cfg2 = d.config_from_snapshot(
        {**cfg.as_snapshot(), "entity_types": ["井"], "relation_tags": []}
    )
    await store.save(lib.lib_id, cfg2, actor_who="aqiang · 平台运维")
    row2 = await store.config_of(lib.lib_id)
    assert row2 is not None and row2.entity_types == ["井"]
    assert row2.saved_by == "aqiang · 平台运维"
