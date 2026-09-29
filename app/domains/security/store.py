"""domains.security.store —— audit_log 表（99 §2.1 逐字段）与 append-only 仓储。

B12 结构说明（横切操作日志唯一写口，specs/api/98 §6-B12）：
- 本表的写入口只有 AuditLogStore.append / append_in（后者供调用方事务内
  同事务追加），且仅经 service.audit 可达；本类**刻意不继承**
  infra.db.Repository（通用 CRUD 基类带 add/delete 面）——append-only 表
  不给改写任何出口（00 §8.2「审计只读追加、不可关闭」：无 UPDATE/DELETE 通路）。
- 读面只有 page()（D3 端点 14）；经 db.readonly() 只读会话开启（意图级
  flush 守卫恒挂）。
- 其他模块的单据留痕＝各自聚合内嵌留痕子表（B12 双轨）；写 audit_log 的
  代码只应存在于本包——新增写路径＝违反 B12，审查即拒。

本票无 Alembic（P0-08 才立迁移分组，票面约定）：建表走 ensure_audit_table，
表结构与 99 §2.1 逐字段一致（id bigserial · time · who · action · content ·
digest · meta jsonb；PK(id)＋idx(time desc)；基线列 created_at/updated_at）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import Index, String, Table, Text, func, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, BigInteger, DateTime, Integer

from app.domains.security.domain import (
    AuditFilter,
    AuditLogView,
    AuditRow,
    audit_digest,
)
from app.infra.clock import now
from app.infra.db import Base, ConnectionManager, Page


class AuditLog(Base):
    """audit_log——横切操作日志唯一写口 security.audit 的存储（99 §2.1）。"""

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_time_desc", text("time DESC")),)

    # bigserial：PG/金仓渲染 BIGSERIAL（99 §1.7.2 金仓兼容面内）；
    # sqlite 单测底座经 variant 渲染 INTEGER（rowid 别名自增）。
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    # time：timestamp 无时区（99 §1.7.4）
    time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    who: Mapped[str] = mapped_column(Text, nullable=False)  # 操作者槽（label 全名或「系统」）
    action: Mapped[str] = mapped_column(Text, nullable=False)  # 动作槽
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 内容槽（正文不出 D3 面）
    # digest：SM3 hex 64（应用层写入——99 §1.7.3）
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    # jsonb（99 §2.1）——sqlite 底座以 JSON 文本落（单测替身，非生产角色）。
    meta: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    # 基线列（99 §2 卷首）；append-only 无更新通路——updated_at 不挂 onupdate，
    # 恒等于写入时刻（挂了反而暗示存在更新通路）。
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


def _to_entity(row: AuditRow) -> AuditLog:
    """四槽＋digest＋meta → 存储行（digest 在此统一计算，写口外无从旁路）。"""
    return AuditLog(
        time=row.resolved_at(),
        who=row.who,
        action=row.action,
        content=row.content,
        digest=audit_digest(row),
        meta=dict(row.meta) if row.meta is not None else None,
    )


def _to_view(entity: AuditLog) -> AuditLogView:
    """D3 面投影（time/who/action/digest——正文不出门，00 §8.1）。"""
    return AuditLogView(
        time=entity.time, who=entity.who, action=entity.action, digest=entity.digest
    )


class AuditLogStore:
    """audit_log 唯一仓储：append（自管会话）/ append_in（调用方事务内）/ page（D3 读面）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def append(self, row: AuditRow) -> AuditLog:
        """独立追加（轻会话自动提交）；返回落库行（取到 bigserial id）。"""
        entity = _to_entity(row)
        async with self._db.session() as session:
            session.add(entity)
            await session.flush()
        return entity

    async def append_in(self, session: AsyncSession, row: AuditRow) -> AuditLog:
        """调用方事务内追加（同事务留痕——B12「随各聚合事务落库」形状）；提交归调用方。"""
        entity = _to_entity(row)
        session.add(entity)
        await session.flush()
        return entity

    async def page(
        self,
        audit_filter: AuditFilter | None = None,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[AuditLogView]:
        """倒序分页读面（D3 端点 14）；total＝当前筛选条件总数（R3 裁决值）。"""
        page = max(page, 1)
        page_size = max(page_size, 1)
        stmt = select(AuditLog).order_by(AuditLog.time.desc(), AuditLog.id.desc())
        if audit_filter is not None:
            if audit_filter.who is not None:
                stmt = stmt.where(AuditLog.who == audit_filter.who)
            if audit_filter.action is not None:
                stmt = stmt.where(AuditLog.action == audit_filter.action)
        async with self._db.readonly() as session:  # 只读会话（意图级守卫恒挂）
            total = await session.scalar(
                select(func.count()).select_from(stmt.order_by(None).subquery())
            )
            rows = (
                (await session.execute(stmt.offset((page - 1) * page_size).limit(page_size)))
                .scalars()
                .all()
            )
        return Page(
            items=[_to_view(row) for row in rows],
            total=int(total or 0),
            page=page,
            page_size=page_size,
        )


async def ensure_audit_table(engine: AsyncEngine) -> None:
    """建表函数（P0-08 前的票面约定：无 Alembic，表结构与 99 §2.1 逐字段一致）。"""
    table = cast(Table, AuditLog.__table__)  # DeclarativeBase 把 __table__ 标注为 FromClause
    async with engine.begin() as conn:
        await conn.run_sync(table.create, checkfirst=True)
