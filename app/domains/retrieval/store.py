"""domains.retrieval.store —— 检索配置域两表（99 §2.10 逐字段）与仓储。

- `retrieval_config`：生效指针单例行（id='singleton' PK＋current_version_no FK）——
  D2 端点 1「恒返回生效值；待审 patch 不进响应」的承载。
- `retrieval_config_version`：配置版本 append-only（version_no 自然键——99 自然键
  注册表「v23」形合同字段即键；config jsonb 六配置节〔R1 snake 节键〕；updated_at/
  updated_by；via 生效变动单号——种子行 None 非变更产生；回滚端点不立〔D2 开放
  问题 4 已裁决〕，版本行承载＝append-only 修改历史〔页头「修改历史」弹窗数据源，
  A3 接入批前由本表回链〕）。
- 基线列 created_at/updated_at（P0-04 惯例）；版本行 append-only，created_at 与
  updated_at 同值写入（updated_at 即版本生效时刻）。
- 枚举不落列级 CHECK：配置节枚举（rerank 三档/citation 两格/merge 两式/fallback
  两策/clarify 唯一档）承载于 jsonb——校验在域层（D2 400 带字段与允许区间），
  99 §2.10 未冻结 CHECK。
- ensure_retrieval_tables 幂等 checkfirst（P0-04 惯例），与 Alembic 0008 并行
  存活（双轨退役拍挂后续票——P1-01 差异 10 同口径）。

边界：B3（只经 infra.db）、B14（时间只经 infra.clock）、B1（不咬框架）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Table,
    Text,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.domains.retrieval.domain import SEED_UPDATED_BY, default_config_dict
from app.infra.clock import now
from app.infra.db import Base, ConnectionManager

_J = JSONB().with_variant(JSON(), "sqlite")


class RetrievalConfigVersionRow(Base):
    """retrieval_config_version——配置版本（append-only；99 §2.10 逐字段）。"""

    __tablename__ = "retrieval_config_version"

    version_no: Mapped[str] = mapped_column(String(16), primary_key=True)  # v<n> 形
    config: Mapped[dict[str, Any]] = mapped_column(_J, nullable=False)  # 六配置节
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # 版本生效时刻
    updated_by: Mapped[str] = mapped_column(Text, nullable=False)
    via: Mapped[str | None] = mapped_column(Text, nullable=True)  # 生效变动单号 #CFG-…
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class RetrievalConfigRow(Base):
    """retrieval_config——生效指针单例行（99 §2.10 逐字段＋基线列）。"""

    __tablename__ = "retrieval_config"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default="singleton")
    current_version_no: Mapped[str] = mapped_column(
        String(16), ForeignKey("retrieval_config_version.version_no"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class ConfigStore:
    """生效指针＋版本轴仓储（种子缺省自动落库——gateway_budget_config 单例先例）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def ensure_seeded(
        self, session: AsyncSession
    ) -> tuple[RetrievalConfigRow, RetrievalConfigVersionRow]:
        """首次读取自动落种子（合同默认值 v1、via=None、updated_by=系统）——幂等。"""
        pointer = await session.get(RetrievalConfigRow, "singleton")
        if pointer is None:
            return await self._insert_seed(session, default_config_dict(), now())
        current = await session.get(RetrievalConfigVersionRow, pointer.current_version_no)
        if current is None:  # 指针悬空＝脏状态（种子与指针同事务写入，正常不可达）
            raise LookupError(
                f"retrieval_config 指针指向不存在的版本 {pointer.current_version_no!r}"
            )
        return pointer, current

    async def seed_if_absent(self, session: AsyncSession, config: dict[str, Any]) -> bool:
        """空库才写种子行（DE-10 env 播种缝），行在位不触返回 False——DB 行恒胜。

        config＝完整六配置节（rerank_seed_config_dict/default_config_dict 形状）；
        写入形状与首读种子完全同构（v1/via=None/updated_by=系统，行格式零变化）。
        """
        if await session.get(RetrievalConfigRow, "singleton") is not None:
            return False
        await self._insert_seed(session, config, now())
        return True

    @staticmethod
    async def _insert_seed(
        session: AsyncSession, config: dict[str, Any], at: datetime
    ) -> tuple[RetrievalConfigRow, RetrievalConfigVersionRow]:
        """种子两行同事务写入（版本行先行——FK 被引用方，P1-06 flush 排序纪律）。"""
        seed = RetrievalConfigVersionRow(
            version_no="v1",
            config=config,
            updated_at=at,
            updated_by=SEED_UPDATED_BY,
            via=None,
            created_at=at,
        )
        session.add(seed)
        await session.flush()  # 先 INSERT 版本行（FK 被引用方——P1-06 flush 排序纪律）
        pointer = RetrievalConfigRow(
            id="singleton", current_version_no="v1", created_at=at, updated_at=at
        )
        session.add(pointer)
        await session.flush()
        return pointer, seed

    async def version_nos(self, session: AsyncSession) -> list[str]:
        rows = (await session.execute(select(RetrievalConfigVersionRow.version_no))).scalars()
        return list(rows)

    async def vias(self, session: AsyncSession) -> list[str | None]:
        rows = (await session.execute(select(RetrievalConfigVersionRow.via))).scalars()
        return list(rows)


async def ensure_retrieval_tables(engine: AsyncEngine) -> None:
    """建检索配置两表（幂等 checkfirst，P0-04 惯例）——与 Alembic 0008 并行存活。"""
    for model in (RetrievalConfigVersionRow, RetrievalConfigRow):
        table = cast(Table, model.__table__)
        async with engine.begin() as conn:
            await conn.run_sync(table.create, checkfirst=True)
