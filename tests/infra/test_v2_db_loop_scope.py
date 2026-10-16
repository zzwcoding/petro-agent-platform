"""infra.db 环绑定回归（2026-10-16 真机缺陷固化——同步缝桥的一次性工作环不与服务器环共池）。

真机证据（`:8001` V2 服务「Y-41井昨天的日产液量是多少？」首问即 `run_failed`）：
`Task <complete() at appv2/runtimev2/gateway_adapter/bridge.py:296> got Future <Future pending
cb=[BaseProtocol._on_waiter_completed()]> attached to a different loop`——`asyncpg` 连接**绑创建
它的环**，而引擎/池原先是共享的：服务器环（api 落帧／审计／建表）先建的连接，被
`bookkeeping.closing._run_sync` 自建的一次性工作环取用（车道 `GatewayService._settle` 写账，
`pool_pre_ping` 探活处先炸）。修法＝引擎/会话工厂按**使用环**分置（见 `ConnectionManager.
_resources`）。

本测试以 sqlite 单测底座钉语义（不依赖外部服务）：同一个 `ConnectionManager` 在**多个环**上使用
→ 每环各一套引擎（连接不跨环复用）；已关环（一次性工作环退出）的条目不残留。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy import text

from appv2.infra.db import ConnectionManager, DatabaseSpec


def _spec(path: Path) -> DatabaseSpec:
    return DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(path),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )


def test_engine_sets_are_scoped_per_event_loop(tmp_path: Path) -> None:
    """多环用同一管理器：每环一套引擎＋关环条目剔除（跨环共池＝真机 run_failed 根因）。"""
    manager = ConnectionManager([_spec(tmp_path / "loop-scope.db")])

    async def touch() -> object:
        async with manager.session() as session:
            await session.execute(text("select 1"))
        return manager.engine()

    # 三次 `asyncio.run`＝三个环（同 `_run_sync` 桥自建的一次性工作环形——环退出即关）。
    engines = [asyncio.run(touch()) for _ in range(3)]
    assert len({id(engine) for engine in engines}) == 3, "同一引擎跨环复用（连接绑环——即缺陷形）"
    # `None` 桶（构造期装配）＋当前环桶；已关环的桶在取用时剔除（不残留池/连接）。
    assert len(manager._resources_by_loop) == 2

    asyncio.run(manager.dispose())


def test_same_loop_reuses_one_engine(tmp_path: Path) -> None:
    """同一环内复用同一套引擎（池语义不因按环分置而丢失）。"""
    manager = ConnectionManager([_spec(tmp_path / "loop-reuse.db")])

    async def twice() -> tuple[object, object]:
        async with manager.session() as session:
            await session.execute(text("select 1"))
        async with manager.session() as session:
            await session.execute(text("select 1"))
        return manager.engine(), manager.engine()

    first, second = asyncio.run(twice())
    assert first is second
