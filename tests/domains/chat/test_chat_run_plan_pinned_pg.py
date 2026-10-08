"""chat_run.plan_pinned 迁移 PG16 集成——L-05 真迁移 0021 消费（up/down 可逆实证）。

跑法：TEST_DATABASE_URL=postgresql://...@localhost:5433/petro uv run pytest
tests/domains/chat/test_chat_run_plan_pinned_pg.py -q（未配置即 skip——约定同
tests/domains/dataops/quality/test_quality_tables_pg.py）。测试自动落 <库名>_test
独立库；表结构＝真迁移 0021 程序化执行（importlib 装载版本文件＋Operations.context
——非 ORM 仿造），downgrade 后列消失（可逆）。
"""

import importlib.util
import os
from pathlib import Path
from typing import Any

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL 未配置——PG 集成测试跳过"
)

_MIGRATION_0021 = (
    Path(__file__).resolve().parents[3]
    / "migrations" / "versions" / "20261007_0021_chat_run_plan_pinned.py"
)


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


def _load_migration(path: Path) -> Any:
    """版本文件名以日期开头非合法标识符——importlib 文件位装载。"""
    spec = importlib.util.spec_from_file_location("m0021_chat_run_plan_pinned", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _apply(url: URL, direction: str) -> None:
    """真迁移 0021 upgrade()/downgrade() 程序化执行（Operations.context 桥 alembic.op）。

    前置＝Alembic 0009 chat_baseline 照抄建 chat_run 最小形状（迁移只做加列——
    依赖基线表在场；本测试自建最小底座，随库销毁）。方向名映射＝alembic 惯例
    （upgrade/downgrade——版本文件函数名；先例 0015 测试同款直调 upgrade()）。
    """
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            if direction == "up":
                await conn.execute(text(
                    "CREATE TABLE IF NOT EXISTS chat_run ("
                    " id VARCHAR(32) PRIMARY KEY,"
                    " session_id VARCHAR(32) NOT NULL,"
                    " status VARCHAR(24) NOT NULL,"
                    " clarify_count SMALLINT NOT NULL DEFAULT 0"
                    ")"
                ))
            def _run(sync_conn: Any) -> None:
                context = MigrationContext.configure(sync_conn)
                with Operations.context(context):
                    module = _load_migration(_MIGRATION_0021)
                    getattr(module, "upgrade" if direction == "up" else "downgrade")()

            await conn.run_sync(_run)
    finally:
        await engine.dispose()


async def _column_exists(url: URL, column: str) -> bool:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            row = (
                await conn.execute(text(
                    "SELECT 1 FROM information_schema.columns"
                    " WHERE table_name = 'chat_run' AND column_name = :col"
                ), {"col": column})
            ).first()
        return row is not None
    finally:
        await engine.dispose()


async def test_migration_0021_up_down_reversible() -> None:
    url = _isolated_url()
    await _ensure_test_database(url)
    await _apply(url, "up")
    try:
        assert await _column_exists(url, "plan_pinned") is True
        # jsonb 形状实证（列类型——jsonb 承载 QueryPlan dict 投影）。
        engine = create_async_engine(url)
        try:
            async with engine.connect() as conn:
                data_type = (
                    await conn.execute(text(
                        "SELECT data_type FROM information_schema.columns"
                        " WHERE table_name = 'chat_run' AND column_name = 'plan_pinned'"
                    ))
                ).scalar()
            assert data_type == "jsonb"
        finally:
            await engine.dispose()
    finally:
        await _apply(url, "down")
    assert await _column_exists(url, "plan_pinned") is False
