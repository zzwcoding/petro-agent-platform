"""retrieval 测试共享夹具：sqlite 底座（真 RetrievalService——纯配置域无外缝可桩）。"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import select

from app.domains.retrieval import RetrievalService
from app.domains.retrieval.store import RetrievalConfigVersionRow, ensure_retrieval_tables
from app.infra.db import ConnectionManager, DatabaseSpec


@pytest.fixture
async def retrieval_db(tmp_path: Any) -> AsyncIterator[ConnectionManager]:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "retrieval.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_retrieval_tables(manager.engine())
    yield manager
    await manager.dispose()


@pytest.fixture
def service(retrieval_db: ConnectionManager) -> RetrievalService:
    return RetrievalService(retrieval_db)


async def version_rows(db: ConnectionManager) -> list[RetrievalConfigVersionRow]:
    """版本轴全行（version_no 升序——via 回链断言用）。"""
    async with db.readonly() as session:
        rows = (
            await session.execute(
                select(RetrievalConfigVersionRow).order_by(RetrievalConfigVersionRow.version_no)
            )
        )
        return list(rows.scalars().all())
