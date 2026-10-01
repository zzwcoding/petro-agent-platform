"""Alembic 迁移环境（P0-08 迁移分组）。

- 目标库 URL 推导：config/database.yaml → infra.config.load_database_specs()
  → primary spec.url()（99 §4.2；不读 alembic.ini 的 sqlalchemy.url——恒空）。
  驱动＝postgresql+asyncpg（infra.db DRIVER_REGISTRY 定型），迁移以异步引擎跑
  （run_sync 桥接 alembic 同步 context）。
- target_metadata＝infra.db.Base.metadata（全平台单一 MetaData——autogenerate
  单一来源与跨域 FK 共图前提，P0-04 票面）。域模型 import 不在此预挂：各域
  切换迁移时由**该域票**在下方「域模型登记区」补 import（补齐才能 autogenerate
  出本域表；P0-08 不切换、只立空基线）。
- 版本文件命名域前缀纪律见 alembic.ini 头注（versions/ 单目录平放）。
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import URL, Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.infra.config import load_database_specs
from app.infra.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 域模型登记区（各域切换票补挂——挂齐才有完整 autogenerate，见模块 docstring）：
from app.domains.semantics import store as _sem_models  # noqa: F401,E402  (P1-01 sem 域首执行)

target_metadata = Base.metadata


def _primary_url() -> URL:
    """primary 连接推导（99 §4.1 三角色；未配置即显式失败，不猜默认库）。"""
    for spec in load_database_specs():
        if spec.role == "primary":
            return spec.url()
    raise RuntimeError(
        "config/database.yaml 未配置 primary——迁移目标无法推导（99 §4.1）"
    )


def run_migrations_offline() -> None:
    """离线模式：不连库，只出 SQL 脚本（--sql）。"""
    context.configure(
        url=_primary_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_sync_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_online() -> None:
    engine = create_async_engine(_primary_url(), poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run_sync_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    """在线模式：asyncpg 异步引擎上跑迁移（NullPool——一次性运维连接）。"""
    asyncio.run(_run_online())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
