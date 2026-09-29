"""audit_log PG 集成测试——bigserial/jsonb/timestamp 真库落位与 SM3 摘要复算。

约定（tickets/phase0/README.md P0-03）：环境变量 TEST_DATABASE_URL 未配置即
skip；本地跑法：
    TEST_DATABASE_URL="postgresql+asyncpg://petro:petro@localhost:5433/petro" \
        uv run pytest tests/domains/security/test_security_audit_pg.py -q
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.security import AuditRow, SecurityService
from app.domains.security.store import ensure_audit_table
from app.infra.clock import ISO_FMT
from app.infra.crypto import sm3_digest
from app.infra.db import ConnectionManager, DatabaseSpec

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")


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
        await conn.execute(text("DROP TABLE IF EXISTS audit_log"))
    await ensure_audit_table(engine)
    await engine.dispose()
    yield manager
    await manager.dispose()


async def _column_meta(db: ConnectionManager, column: str) -> dict[str, object]:
    async with db.session() as session:
        row = (
            await session.execute(
                text(
                    "SELECT data_type, character_maximum_length, column_default "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'audit_log' AND column_name = :col"
                ),
                {"col": column},
            )
        ).one_or_none()
    assert row is not None, f"列不存在: {column}"
    return {"data_type": row[0], "max_len": row[1], "default": row[2]}


async def test_bigserial_autoincrement_on_real_pg(db: ConnectionManager) -> None:
    service = SecurityService(db)
    await service.audit(AuditRow(who="系统", action="probe.first", content="第一行"))
    await service.audit(AuditRow(who="系统", action="probe.second", content="第二行"))

    async with db.session() as session:
        ids = (await session.execute(text("SELECT id FROM audit_log ORDER BY id"))).scalars().all()
    assert ids == [1, 2]  # 建表后首两行——bigserial 自增（99 §2.1：id bigserial）
    id_meta = await _column_meta(db, "id")
    assert id_meta["data_type"] == "bigint"
    assert str(id_meta["default"]).startswith("nextval(")  # BIGSERIAL 序列默认值


async def test_pg_column_types_match_99(db: ConnectionManager) -> None:
    # 99 §2.1 逐字段 + §1.7.4（timestamp 无时区）+ §1.7.2（jsonb/bigserial 金仓兼容面）
    assert (await _column_meta(db, "time"))["data_type"] == "timestamp without time zone"
    for col in ("who", "action", "content"):
        assert (await _column_meta(db, col))["data_type"] == "text"
    digest_meta = await _column_meta(db, "digest")
    assert digest_meta["data_type"] == "character varying"
    assert digest_meta["max_len"] == 64
    assert (await _column_meta(db, "meta"))["data_type"] == "jsonb"
    for col in ("created_at", "updated_at"):
        assert (await _column_meta(db, col))["data_type"] == "timestamp without time zone"

    async with db.session() as session:
        index_row = (
            await session.execute(
                text(
                    "SELECT indexdef FROM pg_indexes "
                    "WHERE tablename = 'audit_log' AND indexname = 'ix_audit_log_time_desc'"
                )
            )
        ).scalar_one()
    assert "DESC" in index_row and "time" in index_row.lower()  # idx(time desc)——99 §2.1


async def test_meta_jsonb_roundtrip_on_real_pg(db: ConnectionManager) -> None:
    service = SecurityService(db)
    await service.audit(
        AuditRow(
            who="阿强 · 平台运维",
            action="security.query_policy.saved",
            content="查询安检配置保存（进 C3 审批）",
            meta={"trace_id": "call-8c31", "actor": "aqiang"},
        )
    )
    async with db.session() as session:
        trace = (
            await session.execute(text("SELECT meta->>'trace_id' FROM audit_log"))
        ).scalar_one()
    assert trace == "call-8c31"  # jsonb 运算符真库可用


async def test_digest_recomputable_from_stored_slots_on_real_pg(db: ConnectionManager) -> None:
    # SM3 由应用层写入、不依赖 DB 函数（99 §1.7.3 跨库一致）——真库行按存储四槽复算即合。
    service = SecurityService(db)
    await service.audit(
        AuditRow(
            who="小李 · 地质/质检",
            action="kb.report.uploaded",
            content="《2026年9月产量报告》入库",
            meta={"trace_id": "call-9001"},
        )
    )
    async with db.session() as session:
        row = (
            await session.execute(
                text("SELECT time, who, action, content, digest FROM audit_log")
            )
        ).one()
    canonical = (
        f"{row[0].strftime(ISO_FMT)}|{row[1]}|{row[2]}|{row[3]}"  # type: ignore[union-attr]
    )
    assert row[4] == sm3_digest(canonical)
