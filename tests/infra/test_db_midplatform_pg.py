"""infra.db midplatform 只读路由 PG16 集成——DP-03 建账号 SQL 实建角色（M-01 测试 d）。

约定（同 test_db_pg.py）：TEST_DATABASE_URL 未配置即 skip；环境变量只用于定位
服务器与凭据——测试自动落 <库名>_test 独立库，不碰同服务器演示库。

本文件只读消费 data-plane 仓（DP-03）两份交付物（不改数据面仓一字）：
- migrations/001_lake_schemas.up.sql：中台库 raw 8 表 DDL（IF NOT EXISTS 幂等）；
- migrations/midplatform_readonly.sql：midplatform 建账号 SQL 模板——<SET_ME>
  由本测试替换为测试口令实建角色（角色已存在则 ALTER PASSWORD 保幂等）。
断言（票面 (d)）：midplatform 连接 SELECT 8 表放行、INSERT 两道闸拒绝——
①授权面默认拒绝（无 INSERT 授权，DP-03 闭世界；会话级关掉 GUC 兜底后仍拒）
②连接级 default_transaction_read_only=on 兜底；clean/data_plane 零授权；
verify_midplatform_route() 真库通过；健康灯含 midplatform。

本地跑法（PG16＝主仓 compose pg 容器，宿主 5433；dev 期中台库与平台库同实例
不同 schema——DP-03 回报拍板，生产独立实例走环境量）：
    export TEST_DATABASE_URL=postgresql+asyncpg://petro:petro@localhost:5433/petro
    uv run pytest tests/infra/test_db_midplatform_pg.py -q
"""

import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.infra.db import ConnectionManager, DatabaseRole, DatabaseSpec

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
MIDPLATFORM_TEST_PASSWORD = "midplatform-m01-pw"  # 测试口令（模板 <SET_ME> 替换值）

_REPO_ROOT = Path(__file__).resolve().parents[2]
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


def _isolated_url() -> URL:
    """TEST_DATABASE_URL → 独立测试库 URL（<库名>_test；测试/演示库分离）。"""
    url = make_url(TEST_DATABASE_URL)
    return url.set(database=f"{url.database}_test")


async def _ensure_test_database(url: URL) -> None:
    """测试库不存在则建（同 test_db_pg.py——CREATE DATABASE 不进事务块）。"""
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
    """按行尾分号切语句（两份迁移均为 DDL/GRANT 直句——无函数体、串内只有全角；）。

    判定终止前剥行内 `--` 注释：`CREATE SCHEMA ...;  -- 注` 形态的行尾分号
    不在行末，须看剥注后的代码尾。
    """
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
    return [s for s in statements if _has_effective_line(s)]


def _has_effective_line(statement: str) -> bool:
    """剔除纯注释块（asyncpg 空语句报错）——只认非注释非空行。"""
    return any(
        line.strip() and not line.strip().startswith("--")
        for line in statement.splitlines()
    )


def _first_effective_code(statement: str) -> str:
    """语句块首个有效代码行（语句块可带头注释——模板头部说明不进判定）。"""
    for line in statement.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("--"):
            return stripped
    return ""


async def _apply_lake_schema(conn: Any) -> None:
    """raw 8 表 DDL 幂等落库（已存在的表/对象 IF NOT EXISTS 跳过）。"""
    for statement in _split_statements(LAKE_SCHEMA_SQL.read_text(encoding="utf-8")):
        await conn.execute(text(statement))


async def _ensure_midplatform_role(conn: Any) -> None:
    """DP-03 建账号 SQL 模板原句实建角色（幂等）：仅 <SET_ME> 换测试口令。"""
    template = ROLE_SQL.read_text(encoding="utf-8").replace(
        "<SET_ME>", MIDPLATFORM_TEST_PASSWORD
    )
    role_exists = (
        await conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = 'midplatform'"))
    ).scalar()
    for statement in _split_statements(template):
        if _first_effective_code(statement).upper().startswith("CREATE ROLE"):
            if role_exists:
                await conn.execute(  # 幂等：角色已在（历史实跑残留）→ 只对口令归一
                    # 实用命令（ALTER ROLE）不吃绑定参数——口令＝本文件测试常量内插
                    text(
                        "ALTER ROLE midplatform WITH LOGIN PASSWORD "
                        f"'{MIDPLATFORM_TEST_PASSWORD}'"
                    )
                )
            else:
                await conn.execute(text(statement))
            continue
        await conn.execute(text(statement))  # GRANT/ALTER ROLE 均可重复执行


def _spec_from_url(
    url: URL,
    role: DatabaseRole,
    *,
    user: str,
    password: str,
    readonly: bool = False,
) -> DatabaseSpec:
    return DatabaseSpec(
        name=role,
        role=role,
        driver=url.drivername.split("+", 1)[0],  # postgresql+asyncpg → postgresql
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
            await _apply_lake_schema(conn)
            await _ensure_midplatform_role(conn)
    finally:
        await admin.dispose()

    manager = ConnectionManager(
        [
            _spec_from_url(
                url, "primary", user=url.username or "", password=url.password or ""
            ),
            _spec_from_url(  # midplatform 角色：DP-03 SQL 实建的只读账号
                url,
                "midplatform",
                user="midplatform",
                password=MIDPLATFORM_TEST_PASSWORD,
                readonly=True,
            ),
        ]
    )
    yield manager
    await manager.dispose()


async def test_midplatform_selects_eight_source_tables(db: ConnectionManager) -> None:
    """SELECT 8 表全放行（99 §2.0② 只读路由：经 readonly(role=) 命名会话取行）。"""
    for table in SOURCE_TABLES:
        async with db.readonly(role="midplatform") as session:
            total = (
                await session.execute(text(f"SELECT count(*) FROM raw.{table}"))
            ).scalar_one()
        assert total >= 0


async def test_midplatform_insert_rejected_by_grants(db: ConnectionManager) -> None:
    """授权面默认拒绝：会话级关掉 GUC 兜底后 INSERT 仍拒（无 INSERT 授权）。"""
    async with db.engine("midplatform").connect() as conn:
        await conn.execute(text("SET default_transaction_read_only = off"))
        await conn.commit()  # SET 与 INSERT 落同一事务则事务只读态不刷新——先收尾再开新事务
        first_column: str = (
            await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'raw' AND table_name = 'well_info' "
                    "ORDER BY ordinal_position LIMIT 1"
                )
            )
        ).scalar_one()
        with pytest.raises(DBAPIError, match="permission denied"):
            await conn.execute(
                # 探针值 ≤ varchar(8)：常量超长会在 ACL 检查前的类型收纳期爆，
                # 盖住权限错误（首跑实证）——探针必须短到不触发约束
                text(f"INSERT INTO raw.well_info ({first_column}) VALUES ('M01')")
            )


async def test_midplatform_insert_rejected_by_readonly_guc(db: ConnectionManager) -> None:
    """连接级兜底：ALTER ROLE ... default_transaction_read_only=on（DP-03 模板末句）。"""
    async with db.engine("midplatform").connect() as conn:
        flag = (await conn.execute(text("SHOW transaction_read_only"))).scalar_one()
        assert flag == "on"
        with pytest.raises(DBAPIError, match="read-only"):
            await conn.execute(
                text("INSERT INTO raw.well_info (well_id) VALUES ('M01')")
            )


async def test_midplatform_zero_grant_schemas_denied(db: ConnectionManager) -> None:
    """clean/data_plane 零授权（DP-03 闭世界：不设 USAGE/SELECT/默认授权）。"""
    async with db.engine("midplatform").connect() as conn:
        await conn.execute(text("SET default_transaction_read_only = off"))
        with pytest.raises(DBAPIError, match="permission denied"):
            await conn.execute(text("SELECT count(*) FROM data_plane.lake_table"))


async def test_verify_midplatform_route_passes_on_real_role(
    db: ConnectionManager,
) -> None:
    """启动校验真库通过：可达＋写探针被拒（GUC 兜底生效即只读验证通过）。"""
    await db.verify_midplatform_route()


async def test_midplatform_health_light_up(db: ConnectionManager) -> None:
    lights = await db.check_health()
    assert lights == {"primary": "up", "midplatform": "up"}
