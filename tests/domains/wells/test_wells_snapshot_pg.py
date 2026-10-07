"""DE-01 湖当前版快照解析器 PG16 集成——真账本三态＋midplatform 授权面零变更对账。

约定（同 tests/infra/test_db_midplatform_pg.py）：TEST_DATABASE_URL 未配置即
skip；测试自动落 <库名>_test 独立库；DP-03 两份交付物只读消费（不改数据面仓
一字）——001_lake_schemas.up.sql 幂等落 raw/data_plane schema＋
midplatform_readonly.sql 模板渲染为专属测试角色 midplatform_test 实建（M-08
根治：dev 共享角色 midplatform 全程零触碰）。

断言（DE-01 票面验收）：
- 三态逐态（真 data_plane.lake_snapshot 账本）：多批（well_info 两批）→最新批；
  单批（well_measures 一批）→该批；账本无记录（equip_status）→None＋warning 一次。
- midplatform 账号授权面零变更：information_schema.role_table_grants 对账——
  恰 8 张 raw 源表 SELECT、data_plane schema 零行（runbook §1.4 三分法第三关
  闭世界对账同款）；负向探针＝midplatform_test 读 data_plane.lake_snapshot 被拒
  （证解析器取数路径必须走 primary——零扩权，DE-01 红线）。

本地跑法（PG16＝主仓 compose pg 容器，宿主 5433）：
    export TEST_DATABASE_URL=postgresql+asyncpg://petro:petro@localhost:5433/petro
    uv run pytest tests/domains/wells/test_wells_snapshot_pg.py -q
"""

import logging
import os
import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.wells.snapshot import LakeSnapshotReader
from app.infra.db import ConnectionManager, DatabaseRole, DatabaseSpec

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
MIDPLATFORM_DEV_ROLE = "midplatform"  # dev 共享角色——测试禁碰（M-08 根治点）
MIDPLATFORM_TEST_ROLE = "midplatform_test"  # 测试专属角色——DP-03 模板渲染目标
MIDPLATFORM_TEST_PASSWORD = "midplatform-de01-pw"  # 测试口令（模板 <SET_ME> 替换值）

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DATA_PLANE_MIGRATIONS = _REPO_ROOT / "data-plane" / "migrations"
LAKE_SCHEMA_SQL = _DATA_PLANE_MIGRATIONS / "001_lake_schemas.up.sql"
ROLE_SQL = _DATA_PLANE_MIGRATIONS / "midplatform_readonly.sql"

# DP-03 模板 GRANT 名单＝8 张 as-is 源表（teach 设定书 §2.2；99 册 §2.0）
SOURCE_TABLES: tuple[str, ...] = (
    "well_info",
    "oil_production_daily",
    "water_injection_daily",
    "well_overhaul",
    "well_measures",
    "fluid_test",
    "equip_status",
    "monthly_settlement",
)

_LOGGER_NAME = "app.domains.wells.snapshot"


# ---------- 底座（照 test_db_midplatform_pg.py 惯例——DP-03 SQL 实建） ----------


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


def _split_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    for line in sql_text.splitlines():
        buffer.append(line)
        if line.split("--", 1)[0].rstrip().endswith(";"):
            statements.append("\n".join(buffer))
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        statements.append(tail)
    return [
        s for s in statements
        if any(
            line.strip() and not line.strip().startswith("--")
            for line in s.splitlines()
        )
    ]


def _first_effective_code(statement: str) -> str:
    for line in statement.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("--"):
            return stripped
    return ""


def _render_role_sql() -> str:
    """DP-03 模板 → 专属测试角色版（先换名后换 <SET_ME>——口令串含角色名前缀）。"""
    rendered = re.sub(
        rf"\b{MIDPLATFORM_DEV_ROLE}\b",
        MIDPLATFORM_TEST_ROLE,
        ROLE_SQL.read_text(encoding="utf-8"),
    )
    return rendered.replace("<SET_ME>", MIDPLATFORM_TEST_PASSWORD)


async def _apply_dp03(conn: Any) -> None:
    """湖 schema DDL 幂等落库＋专属测试角色实建（幂等——已在则只归一口令）。"""
    for statement in _split_statements(LAKE_SCHEMA_SQL.read_text(encoding="utf-8")):
        await conn.execute(text(statement))
    template = _render_role_sql()
    role_exists = (
        await conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :role"),
            {"role": MIDPLATFORM_TEST_ROLE},
        )
    ).scalar()
    for statement in _split_statements(template):
        if _first_effective_code(statement).upper().startswith("CREATE ROLE"):
            if role_exists:
                await conn.execute(
                    text(
                        f"ALTER ROLE {MIDPLATFORM_TEST_ROLE} WITH LOGIN PASSWORD "
                        f"'{MIDPLATFORM_TEST_PASSWORD}'"
                    )
                )
            else:
                await conn.execute(text(statement))
            continue
        await conn.execute(text(statement))


async def _load_ledger_fixture(url: URL) -> None:
    """账本 fixture：well_info 两批（多批态）＋well_measures 一批（单批态）。

    先清后插幂等（只清 DE01 前缀自留地）；snapshot_id＝BIGSERIAL 跨跑单调——
    插入序 B1→B2→M1 保证 id 严格递增，断言按批次相对序（不按绝对值）。
    """
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            await conn.execute(
                text("DELETE FROM data_plane.lake_snapshot WHERE batch_id LIKE 'DE01-%'")
            )
            for table_name, batch_id in (
                ("well_info", "DE01-B1"),
                ("well_info", "DE01-B2"),
                ("well_measures", "DE01-M1"),
            ):
                await conn.execute(
                    text(
                        "INSERT INTO data_plane.lake_snapshot "
                        "(table_name, batch_id, data_object_key, manifest) "
                        "VALUES (:t, :b, :k, '{}'::jsonb)"
                    ),
                    {
                        "t": table_name,
                        "b": batch_id,
                        "k": f"tpa-raw/{table_name}/{batch_id}/data.csv",
                    },
                )
    finally:
        await admin.dispose()


def _spec(
    url: URL, role: DatabaseRole, *, user: str, password: str, readonly: bool
) -> DatabaseSpec:
    return DatabaseSpec(
        name=role,
        role=role,
        driver=url.drivername.split("+", 1)[0],
        host=url.host or "localhost",
        port=url.port or 5433,
        database=url.database or "",
        user=user,
        password=password,
        pool_size=2,
        max_overflow=1,
        readonly=readonly,
    )


@pytest.fixture
async def db() -> AsyncIterator[ConnectionManager]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL 未配置——PG 集成测试跳过（约定见票面）")
    missing = [p for p in (LAKE_SCHEMA_SQL, ROLE_SQL) if not p.is_file()]
    if missing:
        raise RuntimeError(f"DP-03 交付物缺失（data-plane 仓未就位）: {missing}")
    url = _isolated_url()
    await _ensure_test_database(url)
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            await _apply_dp03(conn)
    finally:
        await admin.dispose()
    await _load_ledger_fixture(url)

    manager = ConnectionManager(
        [
            _spec(url, "primary", user=url.username or "",
                  password=url.password or "", readonly=False),
            _spec(url, "midplatform", user=MIDPLATFORM_TEST_ROLE,
                  password=MIDPLATFORM_TEST_PASSWORD, readonly=True),
        ]
    )
    yield manager
    await manager.dispose()


# ---------- 三态（真 data_plane.lake_snapshot 账本） ----------


async def test_multi_batch_real_ledger_returns_latest(db: ConnectionManager) -> None:
    """多批态：well_info 两批→最新批（DE01-B2；snapshot_id 递增序最大）。"""
    reader = LakeSnapshotReader(db)
    face = await reader.current_snapshot("well_info")
    assert face is not None
    assert face.table_name == "well_info"
    assert face.batch_id == "DE01-B2"
    assert isinstance(face.snapshot_id, int) and face.snapshot_id > 0


async def test_single_batch_real_ledger_returns_that_batch(
    db: ConnectionManager,
) -> None:
    """单批态：well_measures 一批→该批原样返回。"""
    reader = LakeSnapshotReader(db)
    face = await reader.current_snapshot("well_measures")
    assert face is not None
    assert face.batch_id == "DE01-M1"
    assert face.table_name == "well_measures"


async def test_no_ledger_record_returns_none_and_warns_once(
    db: ConnectionManager, caplog: Any
) -> None:
    """无记录态：真账本查无 equip_status→None＋warning 一次（重复调用不刷屏）。"""
    reader = LakeSnapshotReader(db)
    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        first = await reader.current_snapshot("equip_status")
        second = await reader.current_snapshot("equip_status")
    assert first is None and second is None
    warnings = [r for r in caplog.records if r.name == _LOGGER_NAME]
    assert len(warnings) == 1
    assert "equip_status" in warnings[0].getMessage()


# ---------- midplatform 账号授权面零变更（runbook §1.4 第三关对账） ----------


async def test_midplatform_grant_surface_unchanged(db: ConnectionManager) -> None:
    """role_table_grants 对账：恰 8 张 raw 源表 SELECT；data_plane schema 零行。

    本票交付的解析器上线前后该结果集必须逐行相同（闭世界——解析器取数走
    primary，不靠给 midplatform 扩授权）。
    """
    async with db.readonly(role="primary") as session:
        grants = (
            await session.execute(
                text(
                    "SELECT table_schema, table_name, privilege_type "
                    "FROM information_schema.role_table_grants "
                    "WHERE grantee = :role ORDER BY table_name"
                ),
                {"role": MIDPLATFORM_TEST_ROLE},
            )
        ).all()
    assert len(grants) == len(SOURCE_TABLES)
    assert {g[1] for g in grants} == set(SOURCE_TABLES)
    assert all(g[0] == "raw" for g in grants)
    assert all(g[2] == "SELECT" for g in grants)
    # 湖元数据两表所在 schema 显式零行（DE-01 红线「不扩 midplatform 授权」）
    assert not [g for g in grants if g[0] == "data_plane"]


async def test_midplatform_cannot_read_lake_ledger(db: ConnectionManager) -> None:
    """负向探针：midplatform_test 读 data_plane.lake_snapshot 被拒（闭世界）——
    解析器取数路径定案 primary 的必要性实证（非风格选择）。"""
    async with db.engine("midplatform").connect() as conn:
        await conn.execute(text("SET default_transaction_read_only = off"))
        with pytest.raises(DBAPIError, match="permission denied"):
            await conn.execute(text("SELECT count(*) FROM data_plane.lake_snapshot"))
