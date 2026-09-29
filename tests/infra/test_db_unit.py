"""infra.db 单测——连接层语义（SQLite 底座，不依赖外部服务）。

覆盖：驱动注册表/URL 装配、EncryptedField 回调 seam、行级注入点、
session/transaction（嵌套 SAVEPOINT）/readonly 意图守卫、仓储基类与分页、
慢查询钩子、健康探活。DB 级只读兜底（default_transaction_read_only）属
PG 方言——PG 集成测试覆盖（test_db_pg.py）。
"""

import dataclasses
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.infra.db import (
    DRIVER_REGISTRY,
    ConnectionManager,
    DatabaseSpec,
    EncryptedField,
    Page,
    ReadOnlyRepository,
    ReadOnlyViolation,
    Repository,
)


class _UnitBase(DeclarativeBase):
    pass


def _fake_encrypt(value: str) -> str:
    return f"ENC[{value}]"


def _fake_decrypt(value: str) -> str:
    return value.removeprefix("ENC[").removesuffix("]")


class NoteUnit(_UnitBase):
    __tablename__ = "unit_note"

    id: Mapped[str] = mapped_column(primary_key=True)
    body: Mapped[str | None] = mapped_column(default=None)


class SecretUnit(_UnitBase):
    __tablename__ = "unit_secret"

    id: Mapped[str] = mapped_column(primary_key=True)
    credential: Mapped[str | None] = mapped_column(
        EncryptedField(encrypt=_fake_encrypt, decrypt=_fake_decrypt)
    )


def _spec(tmp_path: Path, role: str, *, readonly: bool = False) -> DatabaseSpec:
    return DatabaseSpec(
        name=role,
        role=role,  # type: ignore[arg-type]
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / f"unit-{role}.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
        readonly=readonly,
    )


@pytest.fixture
async def db(tmp_path: Path) -> AsyncIterator[ConnectionManager]:
    spec = _spec(tmp_path, "primary")
    manager = ConnectionManager([spec])
    engine = create_async_engine(spec.url())
    async with engine.begin() as conn:
        await conn.run_sync(_UnitBase.metadata.create_all)
    await engine.dispose()
    yield manager
    await manager.dispose()


async def _all_note_ids(manager: ConnectionManager) -> set[str]:
    async with manager.session() as session:
        rows = await session.execute(select(NoteUnit.id))
        return set(rows.scalars().all())


# ---------- 驱动注册表与 URL ----------


def test_driver_registry_postgresql_is_asyncpg() -> None:
    assert DRIVER_REGISTRY["postgresql"] == "postgresql+asyncpg"  # 本仓驱动定型
    assert "kingbase" in DRIVER_REGISTRY  # 金仓占位（99 §4.2 结构不动）


def test_database_spec_url_and_unknown_driver(tmp_path: Path) -> None:
    spec = _spec(tmp_path, "primary")
    assert spec.url().drivername == "sqlite+aiosqlite"

    bad = DatabaseSpec(
        name="x",
        role="primary",
        driver="oracle",
        host="h",
        port=1,
        database="d",
        user="u",
        password="p",
    )
    with pytest.raises(ValueError, match="未登记的数据库驱动"):
        bad.url()


# ---------- EncryptedField（seam 语义——真实 SM4 见 PG 集成测试） ----------


def test_encrypted_field_default_identity() -> None:
    field = EncryptedField()
    assert field.process_bind_param("明文", None) == "明文"
    assert field.process_bind_param(None, None) is None
    assert field.process_result_value("明文", None) == "明文"
    assert field.process_result_value(None, None) is None


def test_encrypted_field_callbacks_roundtrip() -> None:
    field = EncryptedField(encrypt=_fake_encrypt, decrypt=_fake_decrypt)
    cipher = field.process_bind_param("井口压力", None)
    assert cipher == "ENC[井口压力]"  # 密文出 bind
    assert field.process_result_value(cipher, None) == "井口压力"  # 明文回读


async def test_encrypted_field_write_read_through_db(db: ConnectionManager) -> None:
    async with db.session() as session:
        session.add(SecretUnit(id="s1", credential="secret-token"))
    async with db.session() as session:
        row = await session.get(SecretUnit, "s1")
        assert row is not None and row.credential == "secret-token"  # ORM 读＝明文
    async with db.session() as session:
        raw = await session.execute(text("SELECT credential FROM unit_secret"))
        assert raw.scalar_one() == "ENC[secret-token]"  # 裸 SQL 读＝密文落库


# ---------- 行级权限注入点（00 §9.3 / 99 §4.2） ----------


def test_with_row_filter_and_predicates() -> None:
    stmt = ConnectionManager.with_row_filter(
        select(NoteUnit), [NoteUnit.id == "a", NoteUnit.body.is_not(None)]
    )
    compiled = str(stmt.compile())
    assert "unit_note.id" in compiled and "unit_note.body IS NOT NULL" in compiled


# ---------- 会话与事务（嵌套 SAVEPOINT） ----------


async def test_session_commits_and_rolls_back(db: ConnectionManager) -> None:
    async with db.session() as session:
        session.add(NoteUnit(id="ok", body="kept"))
    assert await _all_note_ids(db) == {"ok"}

    with pytest.raises(RuntimeError, match="abort"):
        async with db.session() as session:
            session.add(NoteUnit(id="bad", body="dropped"))
            raise RuntimeError("abort")
    assert await _all_note_ids(db) == {"ok"}  # 异常路径回滚


async def test_transaction_outer_and_savepoint_rollback(db: ConnectionManager) -> None:
    async with db.transaction() as session:
        session.add(NoteUnit(id="a", body="outer"))
        with pytest.raises(ValueError, match="boom"):
            async with db.transaction(session):  # 内层＝SAVEPOINT
                session.add(NoteUnit(id="b", body="inner"))
                raise ValueError("boom")
        session.add(NoteUnit(id="c", body="after-savepoint"))
    assert await _all_note_ids(db) == {"a", "c"}  # b 随 SAVEPOINT 回滚，外层照常提交


async def test_transaction_savepoint_commit_keeps_inner(db: ConnectionManager) -> None:
    async with db.transaction() as session:
        session.add(NoteUnit(id="x", body="outer"))
        async with db.transaction(session):
            session.add(NoteUnit(id="y", body="inner"))
    assert await _all_note_ids(db) == {"x", "y"}


async def test_transaction_by_role_writes_commit(db: ConnectionManager) -> None:
    async with db.transaction() as session:
        session.add(NoteUnit(id="t1", body="role-path"))
    assert await _all_note_ids(db) == {"t1"}


# ---------- 只读双保险（意图级守卫；DB 级见 PG 集成） ----------


async def test_readonly_guard_blocks_flush(db: ConnectionManager) -> None:
    async with db.readonly() as session:
        rows = await session.execute(select(NoteUnit.id))
        assert rows.scalars().all() == []  # 读放行
        session.add(NoteUnit(id="nope", body="write"))
        with pytest.raises(ReadOnlyViolation, match="禁止 flush"):
            await session.flush()


async def test_writable_session_on_readonly_role_rejected(tmp_path: Path) -> None:
    manager = ConnectionManager(
        [_spec(tmp_path, "primary"), _spec(tmp_path, "midplatform", readonly=True)]
    )
    with pytest.raises(ReadOnlyViolation, match="只读"):
        async with manager.session(role="midplatform"):
            pass
    await manager.dispose()


def test_resolve_read_role_fallback(tmp_path: Path) -> None:
    primary_only = ConnectionManager([_spec(tmp_path, "primary")])
    assert primary_only.resolve_read_role("primary") == "primary"  # 未配 replica 回落
    both = ConnectionManager(
        [_spec(tmp_path, "primary"), _spec(tmp_path, "replica")]
    )
    assert both.resolve_read_role("primary") == "replica"  # 读走 replica（预留 seam）


# ---------- 观测钩子与健康 ----------


async def test_slow_query_hook_logs(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    eager = dataclasses.replace(_spec(tmp_path, "primary"), slow_query_ms=0)
    manager = ConnectionManager([eager])
    with caplog.at_level("WARNING", logger="infra.db"):
        async with manager.session() as session:
            await session.execute(select(1))
    assert "slow query on primary" in caplog.text
    await manager.dispose()


async def test_check_health_reports_up(db: ConnectionManager) -> None:
    assert await db.check_health() == {"primary": "up"}


# ---------- 仓储基类与分页（R3 信封） ----------


async def test_repository_add_get_delete(db: ConnectionManager) -> None:
    class NoteRepo(Repository[NoteUnit]):  # 99 §4.3：具体仓储归模块包，此处按同形验证基类
        model = NoteUnit

    repo = NoteRepo(db)
    async with db.session() as session:
        repo.add(session, NoteUnit(id="r1", body="v"))
    async with db.session() as session:
        got = await repo.get(session, "r1")
        assert got is not None and got.body == "v"
        await repo.delete(session, got)
    assert await _all_note_ids(db) == set()


async def test_readonly_repository_paginate(db: ConnectionManager) -> None:
    async with db.session() as session:
        for i in range(3):
            session.add(NoteUnit(id=f"p{i}", body=str(i)))

    repo: ReadOnlyRepository[NoteUnit] = ReadOnlyRepository[NoteUnit](db)
    async with db.session() as session:
        page: Page[NoteUnit] = await repo.paginate(
            session, select(NoteUnit).order_by(NoteUnit.id), page=2, page_size=2
        )
        assert [item.id for item in page.items] == ["p2"]
        assert page.total == 3  # total＝当前筛选条件总数（R3）
        assert (page.page, page.page_size) == (2, 2)

    async with db.session() as session:
        first: Page[NoteUnit] = await repo.paginate(
            session, select(NoteUnit), page=0, page_size=1  # 越界页码归一
        )
        assert first.page == 1
