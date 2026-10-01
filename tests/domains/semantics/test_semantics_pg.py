"""semantics 九表 PG 集成——99 §2.8 逐字段落位与 jsonb/CHECK/索引真库断言。

约定（tickets/phase0/README.md P0-03 起；P0-07 审查 P3 测试/演示库分离）：
环境变量 TEST_DATABASE_URL 未配置即 skip；真正建表跑测的库机械折算为独立库
`<库名>_test`（演示库不受影响）。本地跑法：
    TEST_DATABASE_URL="postgresql+asyncpg://petro:petro@localhost:5433/petro" \\
        uv run pytest tests/domains/semantics/test_semantics_pg.py -q
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.domains.security import SecurityService
from app.domains.security.domain import resolve_actor
from app.domains.semantics import SemanticsService
from app.domains.semantics.store import (
    SemAction,
    SemJoinWhitelist,
    SemMetric,
    SemObject,
    SemRelation,
    SemTerm,
    SemVersion,
    SemWorkflow,
    ensure_semantics_tables,
)
from app.infra.db import ConnectionManager, DatabaseSpec

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

# 99 §2.8 九表逐列期望（列名 → (data_type, nullable)——information_schema 口径）；
# 基线列 created_at/updated_at（99 §2 卷首）逐表携带。row_id 统一 text（int/text
# id 族同列承载）；jsonb 列照 99 §1.5 裁决清单。
_EXPECTED_COLUMNS: dict[str, dict[str, tuple[str, bool]]] = {
    "sem_term": {
        "id": ("integer", False), "term": ("text", False), "type": ("text", False),
        "def": ("text", False), "status": ("text", False),
        "status_key": ("character varying", False), "owner": ("text", False),
        "source": ("text", False), "version": ("integer", False),
        "expires_at": ("date", True),
        "created_at": ("timestamp without time zone", False),
        "updated_at": ("timestamp without time zone", False),
    },
    "sem_metric": {
        "id": ("integer", False), "name": ("text", False),
        "mark": ("character varying", True), "slot_name": ("text", False),
        "def": ("text", False), "grain": ("text", False), "unit": ("text", False),
        "status": ("jsonb", False), "owner": ("text", False),
        "source": ("text", False), "dispute": ("text", True),
        "modifiers": ("jsonb", True), "ambiguous": ("boolean", False),
        "calibers": ("jsonb", False),
        "default_caliber": ("character varying", True), "version": ("integer", False),
        "created_at": ("timestamp without time zone", False),
        "updated_at": ("timestamp without time zone", False),
    },
    "sem_object": {
        "id": ("integer", False), "obj": ("text", False), "attr": ("text", True),
        "status": ("text", False), "owner": ("text", True), "source": ("text", False),
        "version": ("integer", True),
        "created_at": ("timestamp without time zone", False),
        "updated_at": ("timestamp without time zone", False),
    },
    "sem_relation": {
        "id": ("integer", False), "rel": ("text", False), "read": ("text", False),
        "source": ("text", False),
        "created_at": ("timestamp without time zone", False),
        "updated_at": ("timestamp without time zone", False),
    },
    "sem_join_whitelist": {
        "id": ("integer", False), "left_table": ("text", False),
        "right_table": ("text", False), "verdict": ("character varying", False),
        "tables": ("text", False), "how": ("text", False),
        "version": ("integer", False),
        "created_at": ("timestamp without time zone", False),
        "updated_at": ("timestamp without time zone", False),
    },
    "sem_workflow": {
        "id": ("character varying", False), "name": ("text", False),
        "status": ("character varying", False), "account": ("text", True),
        "source": ("text", True), "card": ("jsonb", False),
        "version": ("integer", True),
        "created_at": ("timestamp without time zone", False),
        "updated_at": ("timestamp without time zone", False),
    },
    "sem_action": {
        "id": ("character varying", False),
        "register_name": ("character varying", False),
        "business_name": ("text", False),
        "created_at": ("timestamp without time zone", False),
        "updated_at": ("timestamp without time zone", False),
    },
    "sem_ledger_revision": {
        "id": ("bigint", False), "domain": ("character varying", False),
        "row_id": ("text", False), "version": ("integer", False),
        "payload": ("jsonb", False), "changed_by": ("text", False),
        "source_proposal_id": ("text", True),
        "changed_at": ("timestamp without time zone", False),
        "created_at": ("timestamp without time zone", False),
        "updated_at": ("timestamp without time zone", False),
    },
    "sem_version": {
        "id": ("character varying", False), "current": ("text", False),
        "updated_at": ("timestamp without time zone", False),
        "created_at": ("timestamp without time zone", False),
    },
}

_EXPECTED_CONSTRAINTS: dict[str, set[str]] = {
    "sem_term": {"ck_sem_term_status_key"},
    "sem_metric": {"ck_sem_metric_mark", "uq_sem_metric_slot_name"},
    "sem_join_whitelist": {"ck_sem_join_whitelist_verdict"},
    "sem_workflow": {"ck_sem_workflow_status"},
    "sem_action": {"uq_sem_action_register_name"},
    "sem_ledger_revision": {"ck_sem_ledger_revision_domain", "uq_sem_ledger_revision_row_ver"},
}

_EXPECTED_INDEXES: set[str] = {
    "ix_sem_term_status_key_owner",
    "ix_sem_join_whitelist_left_right",
    "ix_sem_ledger_revision_source_proposal",
}


def _isolated_url() -> URL:
    """TEST_DATABASE_URL → 独立测试库 URL（<库名>_test——P0-07 分离约定）。"""
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
        for table in _EXPECTED_COLUMNS:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
    await ensure_semantics_tables(engine)
    await engine.dispose()
    yield manager
    await manager.dispose()


async def _columns(conn: AsyncConnection, table: str) -> dict[str, tuple[str, bool]]:
    result = await conn.execute(
        text(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t"
        ),
        {"t": table},
    )
    return {r[0]: (r[1], r[2] == "YES") for r in result}


async def test_nine_tables_per_column_per_99(db: ConnectionManager) -> None:
    """九表逐列断言（列名/类型/可空——99 §2.8 + 基线列；应零差异）。"""
    async with db.engine().connect() as conn:
        for table, expected in _EXPECTED_COLUMNS.items():
            actual = await _columns(conn, table)
            missing = sorted(set(expected) - set(actual))
            extra = sorted(set(actual) - set(expected))
            assert not missing, f"{table} 缺列：{missing}"
            assert not extra, f"{table} 多列（99 §2.8 未冻结）：{extra}"
            for column, (data_type, nullable) in expected.items():
                assert actual[column] == (data_type, nullable), (
                    f"{table}.{column}＝{actual[column]}，期望 {(data_type, nullable)}"
                )


async def test_check_constraints_unique_and_indexes(db: ConnectionManager) -> None:
    """枚举落 CHECK（99 §1.4 裁决）＋slot_name uq＋行版本轴 uq＋登记序索引。"""
    async with db.engine().connect() as conn:
        for table, expected in _EXPECTED_CONSTRAINTS.items():
            rows = await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = to_regclass(:t) AND contype IN ('c','u')"
                ),
                {"t": f"public.{table}"},
            )
            names = {r[0] for r in rows}
            assert expected <= names, f"{table} 缺约束：{expected - names}"
        rows = await conn.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = 'public' AND indexname = ANY(:names)"
            ),
            {"names": sorted(_EXPECTED_INDEXES)},
        )
        assert {r[0] for r in rows} == _EXPECTED_INDEXES


async def test_sync_roundtrip_and_revision_on_pg(db: ConnectionManager) -> None:
    """同步器 PG 往返：行计数/revision bigserial/jsonb 快照/全量版本种子。"""
    service = SemanticsService(db, SecurityService(db))
    report = await service.sync_from_ontology_repo("mr#pg", resolve_actor(None))
    assert report.counts == {
        "term": 11, "metric": 15, "object": 10, "relation": 5,
        "whitelist": 4, "workflow": 10, "action": 3,
    }
    again = await service.sync_from_ontology_repo("mr#pg", resolve_actor(None))
    assert again.revisions_appended == 0 and again.rows_unchanged == 58  # 幂等重放
    async with db.readonly() as session:
        assert (await session.get(SemTerm, 1)).term == "老完成率"
        metric = await session.get(SemMetric, 10)
        assert metric.ambiguous is False and metric.status == ["生效中", "待联席裁决"]
        assert (await session.get(SemObject, 9)).status == "草案"
        assert (await session.get(SemRelation, 3)).rel == "注水井 —受效→ 油井"
        whitelist = await session.get(SemJoinWhitelist, 4)
        assert "受效关系" in whitelist.how  # 展示串照抄（含直引号原值）
        workflow = await session.get(SemWorkflow, "wf1")
        assert workflow.card["contract"].startswith("结论＋证据链＋数据版本")
        assert (await session.get(SemAction, "update_well_remark")).business_name == "更新井备注"
        version = await session.get(SemVersion, "current")
        assert version.current == "v37"
        revisions = (
            (await session.execute(text("SELECT count(*) FROM sem_ledger_revision"))).scalar_one()
        )
        assert revisions == 58
        payload = (
            await session.execute(
                text(
                    "SELECT payload FROM sem_ledger_revision "
                    "WHERE domain = 'metric' AND row_id = '15'"
                )
            )
        ).scalar_one()
        assert payload["dispute"] == "经营 × 技术联席"  # deferredAdditions 占位快照
        assert payload["grain"] == "批次"  # jsonb 快照随行入档（bigserial 轴可溯）
