"""infra_outbox PG 集成测试——99 §6-4 infra 技术表逐字段落位与 jsonb 真库断言。

约定（tickets/phase0/README.md P0-03 起）：环境变量 TEST_DATABASE_URL 未配置
即 skip；本地跑法（该变量只用于定位服务器与凭据——测试自动改用其 <库名>_test
独立库，不碰同服务器演示库 petro，P0-07 审查 P3 测试/演示库分离）：
    TEST_DATABASE_URL="postgresql+asyncpg://petro:petro@localhost:5433/petro" \\
        uv run pytest tests/infra/test_eventbus_outbox_pg.py -q

表结构真源：99 册未落（「表结构随接线批落本册」）——本票按标准 outbox 模式落，
逐列登记于 tickets/phase0/README.md P0-08 差异清单（id bigserial/aggregate/
event_type/payload jsonb/occurred_at/published_at nullable＋基线列＋待投递索引）。
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.infra.db import ConnectionManager, DatabaseSpec
from app.infra.eventbus import OutboxStore, ensure_outbox_table, make_event

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

_TABLE = "infra_outbox"


def _isolated_url() -> URL:
    """TEST_DATABASE_URL → 独立测试库 URL（<库名>_test；测试/演示库分离，P0-07 审查 P3）。"""
    url = make_url(TEST_DATABASE_URL)
    return url.set(database=f"{url.database}_test")


async def _ensure_test_database(url: URL) -> None:
    """测试库不存在则建（CREATE DATABASE IF NOT EXISTS 语义——PG 无原生子句）。"""
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
        await conn.execute(text(f"DROP TABLE IF EXISTS {_TABLE}"))
    await ensure_outbox_table(engine)
    await engine.dispose()
    yield manager
    await manager.dispose()


async def _column_meta(db: ConnectionManager, column: str) -> dict[str, object]:
    async with db.session() as session:
        row = (
            await session.execute(
                text(
                    "SELECT data_type, column_default, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_name = :t AND column_name = :c"
                ),
                {"t": _TABLE, "c": column},
            )
        ).one_or_none()
    assert row is not None, f"列不存在: {_TABLE}.{column}"
    return {"data_type": row[0], "default": row[1], "nullable": row[2]}


async def test_outbox_columns_match_registered_structure(db: ConnectionManager) -> None:
    """逐列断言（票面登记结构）：bigserial 主键/jsonb 载荷/published_at nullable。"""
    for column in (
        "id", "aggregate", "event_type", "payload",
        "occurred_at", "published_at", "created_at", "updated_at",
    ):
        assert (await _column_meta(db, column)) is not None
    id_meta = await _column_meta(db, "id")
    assert id_meta["data_type"] == "bigint"
    assert "nextval" in str(id_meta["default"])  # bigserial（注册序＝投递序）
    assert (await _column_meta(db, "payload"))["data_type"] == "jsonb"
    assert (await _column_meta(db, "published_at"))["nullable"] == "YES"
    async with db.session() as session:
        index_rows = (
            await session.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = :t"),
                {"t": _TABLE},
            )
        ).scalars().all()
    assert "ix_infra_outbox_pending" in index_rows  # 待投递扫描序（published_at, id）


async def test_outbox_roundtrip_on_real_pg(db: ConnectionManager) -> None:
    """登记→待投递→回执全链真库往返；jsonb 载荷结构保真。"""
    store = OutboxStore(db)
    event = make_event(
        "IngestCompleted",
        {"lib_id": "lib-1", "report_id": "rpt-pg001", "switches": {"semantic": True}},
        aggregate="kb_report:rpt-pg001",
    )
    row = store.row_for(event)
    await store.add(row)

    pending = await store.pending()
    assert len(pending) == 1
    assert pending[0].aggregate == "kb_report:rpt-pg001"
    assert pending[0].payload["switches"] == {"semantic": True}  # jsonb 往返保真
    assert pending[0].occurred_at == event.occurred_at  # B14 时戳透传不重盖

    assert await store.mark_published(pending[0].id) is True
    assert await store.pending() == []
    async with db.session() as session:
        stamped = (
            await session.execute(
                text(f"SELECT published_at FROM {_TABLE} WHERE id = :i"),
                {"i": pending[0].id},
            )
        ).scalar_one()
    assert stamped is not None  # 回执已盖（中继消费序＝id 升序的前提成立）
