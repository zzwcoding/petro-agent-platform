"""gateway 三表 PG 集成测试——99 §2.13 逐字段落位与 CHECK/jsonb/numeric 真库断言。

约定（tickets/phase0/README.md P0-03 起）：环境变量 TEST_DATABASE_URL 未配置
即 skip；本地跑法：
    TEST_DATABASE_URL="postgresql+asyncpg://petro:petro@localhost:5433/petro" \\
        uv run pytest tests/domains/gateway/test_gateway_tables_pg.py -q
"""

import os
from collections.abc import AsyncIterator
from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.gateway.store import (
    BudgetStore,
    DrillRun,
    SpendRecord,
    SpendStore,
    ensure_gateway_tables,
)
from app.infra.db import ConnectionManager, DatabaseSpec

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

_TABLES = ("gateway_spend_record", "gateway_drill_run", "gateway_budget_config")


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
    url = make_url(TEST_DATABASE_URL)
    manager = ConnectionManager([_spec(url)])
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        for table in _TABLES:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
    await ensure_gateway_tables(engine)
    await engine.dispose()
    yield manager
    await manager.dispose()


async def _column_meta(db: ConnectionManager, table: str, column: str) -> dict[str, object]:
    async with db.session() as session:
        row = (
            await session.execute(
                text(
                    "SELECT data_type, numeric_precision, numeric_scale, column_default "
                    "FROM information_schema.columns "
                    "WHERE table_name = :t AND column_name = :c"
                ),
                {"t": table, "c": column},
            )
        ).one_or_none()
    assert row is not None, f"列不存在: {table}.{column}"
    return {"data_type": row[0], "precision": row[1], "scale": row[2], "default": row[3]}


async def test_spend_record_columns_match_99(db: ConnectionManager) -> None:
    # 99 §2.13：id(call-) · time · model_key · alias · input/output_tokens ·
    # first/total_ms · cost_yuan · fallback · note · run_id · served_model ·
    # attempted_fallbacks（切换留痕注记列）
    for column in (
        "id", "time", "model_key", "alias", "input_tokens", "output_tokens",
        "first_ms", "total_ms", "cost_yuan", "fallback", "note", "run_id",
        "served_model", "attempted_fallbacks", "created_at", "updated_at",
    ):
        assert (await _column_meta(db, "gateway_spend_record", column)) is not None
    assert (await _column_meta(db, "gateway_spend_record", "cost_yuan"))["data_type"] == "numeric"
    fallbacks_meta = await _column_meta(db, "gateway_spend_record", "attempted_fallbacks")
    assert fallbacks_meta["data_type"] == "jsonb"
    async with db.session() as session:
        index_rows = (
            await session.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = 'gateway_spend_record'")
            )
        ).scalars().all()
    assert "ix_gateway_spend_time_desc" in index_rows
    assert "ix_gateway_spend_model_time" in index_rows
    assert "ix_gateway_spend_run" in index_rows


async def test_drill_run_status_check_constraint(db: ConnectionManager) -> None:
    meta = await _column_meta(db, "gateway_drill_run", "status")
    assert meta is not None
    async with db.session() as session:
        session.add(
            DrillRun(
                id="drill-check", status="running", nodes=[],
                started_at=datetime(2026, 9, 29, 10, 0, 0),
            )
        )
    async with db.session() as session:
        session.add(
            DrillRun(
                id="drill-bad", status="paused", nodes=[],
                started_at=datetime(2026, 9, 29, 10, 0, 0),
            )
        )
        with pytest.raises(IntegrityError):  # CHECK(running,done)——99 §2.13
            await session.flush()
        await session.rollback()  # 复位会话状态（轻会话收口不再撞 PendingRollback）


async def test_spend_roundtrip_with_fallback_trace_on_real_pg(db: ConnectionManager) -> None:
    store = SpendStore(db)
    row = await store.add(
        SpendRecord(
            id="call-pg0001",
            time=datetime(2026, 9, 29, 10, 1, 0),
            model_key="backup",
            alias="petro-lite",
            input_tokens=2140,
            output_tokens=1380,
            first_ms=2400,
            total_ms=2600,
            cost_yuan=0.00628,
            fallback=True,
            note="故障演练流水",
            served_model="anthropic/glm-5.3-flash",
            attempted_fallbacks=["anthropic/MiniMax-M3"],
        )
    )
    view = await store.get(row.id)
    assert view is not None
    assert view.fallback is True and view.model_key == "backup"
    assert view.cost_yuan == pytest.approx(0.00628)
    # 切换留痕 jsonb 往返
    async with db.session() as session:
        trace = (
            await session.execute(
                text(
                    "SELECT attempted_fallbacks FROM gateway_spend_record "
                    "WHERE id = 'call-pg0001'"
                )
            )
        ).scalar_one()
    assert trace == ["anthropic/MiniMax-M3"]
    # 月度合计（熔断判据累计半边）
    assert await store.month_total(datetime(2026, 9, 29, 12, 0, 0)) == pytest.approx(0.00628)


async def test_budget_singleton_defaults_seeded_once(db: ConnectionManager) -> None:
    store = BudgetStore(db)
    per_call, monthly = await store.limits()
    assert (per_call, monthly) == (0.05, 800.0)  # D5 §8 合同默认值（F2 改注）
    # 二次读取不重复种子（单例行 id='singleton'）
    per_call2, monthly2 = await store.limits()
    assert (per_call2, monthly2) == (0.05, 800.0)
    async with db.session() as session:
        count = (
            await session.execute(text("SELECT count(*) FROM gateway_budget_config"))
        ).scalar_one()
    assert count == 1
