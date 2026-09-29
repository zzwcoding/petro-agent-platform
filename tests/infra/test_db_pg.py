"""infra.db PG 集成测试——SAVEPOINT 回滚 / EncryptedField SM4 往返 / readonly 双保险。

约定（tickets/phase0/README.md P0-03）：环境变量 TEST_DATABASE_URL 未配置即 skip；
本地跑法：
    export TEST_DATABASE_URL=postgresql+asyncpg://petro:petro@localhost:5433/petro
    uv run pytest tests/infra/test_db_pg.py -q
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.infra.crypto import sm4_decrypt, sm4_encrypt
from app.infra.db import (
    ConnectionManager,
    DatabaseRole,
    DatabaseSpec,
    EncryptedField,
    ReadOnlyViolation,
)

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
SM4_TEST_KEY = "0f1e2d3c4b5a69788796a5b4c3d2e1f0"  # 测试专用密钥（hex 32＝16 字节）


class _PgBase(DeclarativeBase):
    pass


def _enc(value: str) -> str:
    return sm4_encrypt(value, SM4_TEST_KEY)


def _dec(value: str) -> str:
    return sm4_decrypt(value, SM4_TEST_KEY)


class Note(_PgBase):
    __tablename__ = "infra_db_smoke_note"

    id: Mapped[str] = mapped_column(primary_key=True)
    body: Mapped[str | None] = mapped_column(default=None)


class Secret(_PgBase):
    __tablename__ = "infra_db_smoke_secret"

    id: Mapped[str] = mapped_column(primary_key=True)
    credential: Mapped[str | None] = mapped_column(
        EncryptedField(encrypt=_enc, decrypt=_dec)
    )


def _spec_from_url(url: URL, role: DatabaseRole, *, readonly: bool = False) -> DatabaseSpec:
    return DatabaseSpec(
        name=role,
        role=role,
        driver=url.drivername.split("+", 1)[0],  # postgresql+asyncpg → postgresql
        host=url.host or "localhost",
        port=url.port or 5433,
        database=url.database or "",
        user=url.username or "",
        password=url.password or "",
        pool_size=2,
        max_overflow=1,
        readonly=readonly,
    )


@pytest.fixture
async def db() -> AsyncIterator[ConnectionManager]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL 未配置——PG 集成测试跳过（约定见票面）")
    url = make_url(TEST_DATABASE_URL)
    manager = ConnectionManager(
        [
            _spec_from_url(url, "primary"),
            _spec_from_url(url, "midplatform", readonly=True),  # 只读双保险（99 §4.2）
        ]
    )
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(_PgBase.metadata.drop_all)
        await conn.run_sync(_PgBase.metadata.create_all)
    await engine.dispose()
    yield manager
    await manager.dispose()


async def test_savepoint_rollback_keeps_outer(db: ConnectionManager) -> None:
    async with db.transaction() as session:
        session.add(Note(id="a", body="outer"))
        with pytest.raises(ValueError, match="boom"):
            async with db.transaction(session):  # 内层＝SAVEPOINT（99 §4.1 事务语义）
                session.add(Note(id="b", body="inner"))
                raise ValueError("boom")
        session.add(Note(id="c", body="after-savepoint"))
    async with db.session() as session:
        ids = set((await session.execute(text("SELECT id FROM infra_db_smoke_note"))).scalars())
    assert ids == {"a", "c"}


async def test_encrypted_field_sm4_roundtrip(db: ConnectionManager) -> None:
    async with db.session() as session:
        session.add(Secret(id="s1", credential="井口压力 42.5 · outbound credential"))
        session.add(Secret(id="s2", credential="井口压力 42.5 · outbound credential"))

    # 裸 SQL 读＝SM4 密文落库（base64，两行密文不同——随机 IV）
    async with db.session() as session:
        rows = (await session.execute(
            text("SELECT credential FROM infra_db_smoke_secret ORDER BY id")
        )).scalars().all()
    assert len(rows) == 2
    c1, c2 = rows
    assert c1 != "井口压力 42.5 · outbound credential"  # 落库非明文
    assert c1 != c2  # 同明文不同密文（随机 IV 前置）
    assert sm4_decrypt(c1, SM4_TEST_KEY) == "井口压力 42.5 · outbound credential"

    # ORM 读＝明文出列（EncryptedField process_result_value）
    async with db.session() as session:
        row = await session.get(Secret, "s1")
        assert row is not None
        assert row.credential == "井口压力 42.5 · outbound credential"


async def test_readonly_double_insurance(db: ConnectionManager) -> None:
    # 双保险第一道：意图级 flush 守卫（readonly() 语境恒挂）
    async with db.readonly(role="midplatform") as session:
        session.add(Note(id="nope", body="orm-write"))
        with pytest.raises(ReadOnlyViolation, match="禁止 flush"):
            await session.flush()

    # 双保险第二道：DB 级兜底＝方言连接特性 postgresql_readonly（BEGIN READ ONLY，
    # 拦绕过 ORM 的 Core 写）——断言事务只读标志而非 GUC（GUC 方案已退役，
    # asyncpg 方言 BEGIN READ WRITE 覆盖连接级 SET，实证见 db.py 差异注）。
    async with db.readonly(role="midplatform") as session:
        flag = (await session.execute(
            text("SHOW transaction_read_only")
        )).scalar_one()
        assert flag == "on"
        with pytest.raises(DBAPIError):  # asyncpg ReadOnlySqlTransactionError 包装
            await session.execute(
                text("INSERT INTO infra_db_smoke_note (id, body) VALUES ('raw', 'core-write')")
            )

    # 写会话在只读角色上直接拒（_assert_writable 前置校验）
    with pytest.raises(ReadOnlyViolation, match="只读"):
        async with db.session(role="midplatform"):
            pass

    # primary 写会话不受影响（默认可写——事务可写标志 off）
    async with db.session() as session:
        flag = (await session.execute(
            text("SHOW transaction_read_only")
        )).scalar_one()
        assert flag == "off"


async def test_health_lights_on_real_pg(db: ConnectionManager) -> None:
    lights = await db.check_health()
    assert lights == {"primary": "up", "midplatform": "up"}
