"""domains.gateway.store —— 网关域三表（99 §2.13 逐字段）与仓储。

- `gateway_spend_record`：花费账本（**全平台唯一**——D5 裁决一「不建第二份
  账本」，D5 将来只做 run 聚合投影）。演练即真实流量同表落账。
- `gateway_drill_run`：故障演练任务（done 落两笔账之历史行；节点/结果 jsonb）。
- `gateway_budget_config`：花费双阈值单例行（判据消费方＝本域 complete）。

P0-08 前无 Alembic（票面约定）：建表走 ensure_gateway_tables（幂等
checkfirst，沿用 P0-04 ensure_audit_table 惯例），表结构与 99 §2.13 一致
（PK＋idx(time desc)／idx(model_key,time desc)／idx run_id；drill status
CHECK(running,done)；budget id='singleton'）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import (
    CheckConstraint,
    Index,
    Numeric,
    String,
    Table,
    Text,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.domains.gateway.domain import DrillSummary, SpendFilter, SpendView, keyword_matches
from app.infra.clock import now
from app.infra.db import Base, ConnectionManager, Page

# numeric（99 §2.13）——PG/金仓真 numeric；sqlite 单测底座以 float 近似（非生产角色）。
_YUAN = Numeric(12, 6).with_variant(Numeric(12, 6, asdecimal=False), "sqlite")


class SpendRecord(Base):
    """gateway_spend_record——调用粒度账本（全平台唯一）。"""

    __tablename__ = "gateway_spend_record"
    __table_args__ = (
        Index("ix_gateway_spend_time_desc", text("time DESC")),
        Index("ix_gateway_spend_model_time", "model_key", text("time DESC")),
        Index("ix_gateway_spend_run", "run_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # call- 机器短 id
    time: Mapped[datetime] = mapped_column(nullable=False)
    model_key: Mapped[str] = mapped_column(String(16), nullable=False)  # main | backup
    alias: Mapped[str] = mapped_column(String(64), nullable=False)
    input_tokens: Mapped[int] = mapped_column(nullable=False)
    output_tokens: Mapped[int] = mapped_column(nullable=False)
    first_ms: Mapped[int] = mapped_column(nullable=False)
    total_ms: Mapped[int] = mapped_column(nullable=False)
    cost_yuan: Mapped[float] = mapped_column(_YUAN, nullable=False)
    fallback: Mapped[bool] = mapped_column(default=False, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(32), nullable=True)  # run 聚合投影锚
    served_model: Mapped[str | None] = mapped_column(Text, nullable=True)  # 切换留痕：实际部署
    attempted_fallbacks: Mapped[list[str] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )  # 切换留痕：失败部署序
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class DrillRun(Base):
    """gateway_drill_run——故障演练任务（00 §5 双态 running|done）。"""

    __tablename__ = "gateway_drill_run"
    __table_args__ = (CheckConstraint("status IN ('running','done')", name="ck_drill_status"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # drill- 机器短 id
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    nodes: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class BudgetConfigRow(Base):
    """gateway_budget_config——花费双阈值单例行（D5 端点 8/9 的读写对象；判据在本域）。"""

    __tablename__ = "gateway_budget_config"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default="singleton")
    per_call_cost_limit_yuan: Mapped[float] = mapped_column(_YUAN, nullable=False)
    gateway_budget_yuan_per_month: Mapped[float] = mapped_column(_YUAN, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


# ---------- 行 ↔ 域投影 ----------


def _to_spend_view(row: SpendRecord) -> SpendView:
    return SpendView(
        id=row.id,
        time=row.time,
        model_key=row.model_key,
        alias=row.alias,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        first_ms=row.first_ms,
        total_ms=row.total_ms,
        cost_yuan=float(row.cost_yuan),
        fallback=row.fallback,
        note=row.note,
    )


# ---------- 仓储 ----------


class SpendStore:
    """账本仓储（append-only——记账不删改；读面 page 月度合计）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def add(self, row: SpendRecord) -> SpendRecord:
        async with self._db.session() as session:
            session.add(row)
            await session.flush()
        return row

    async def page(
        self, spend_filter: SpendFilter, *, page: int = 1, page_size: int = 15
    ) -> Page[SpendView]:
        """倒序分页读面（排序恒 time 倒序——D1 合同；total＝筛选后，R3）。"""
        page = max(page, 1)
        page_size = max(page_size, 1)
        stmt = select(SpendRecord).order_by(SpendRecord.time.desc(), SpendRecord.id.desc())
        if spend_filter.model != "all":
            stmt = stmt.where(SpendRecord.model_key == spend_filter.model)
        since = spend_filter.since(now())
        if since is not None:
            stmt = stmt.where(SpendRecord.time >= since)
        async with self._db.readonly() as session:
            rows = (await session.execute(stmt)).scalars().all()
        # keyword 匹配调用号/备注——量级演示级，取回后内存过滤（索引不背 keyword）
        hits = [r for r in rows if keyword_matches(spend_filter.keyword, r.id, r.note)]
        window = hits[(page - 1) * page_size : (page - 1) * page_size + page_size]
        return Page(
            items=[_to_spend_view(r) for r in window],
            total=len(hits),
            page=page,
            page_size=page_size,
        )

    async def month_total(self, at: datetime) -> float:
        """当月累计花费（熔断判据的累计半边；月起点＝当月 1 日零点）。"""
        month_start = at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        async with self._db.readonly() as session:
            total = await session.scalar(
                select(func.coalesce(func.sum(SpendRecord.cost_yuan), 0)).where(
                    SpendRecord.time >= month_start
                )
            )
        return float(total or 0)

    async def get(self, call_id: str) -> SpendView | None:
        async with self._db.readonly() as session:
            row = await session.get(SpendRecord, call_id)
        return _to_spend_view(row) if row is not None else None


class DrillStore:
    """演练任务仓储（受理/轮询/历史/重入判据）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def create(self, run: DrillRun) -> DrillRun:
        async with self._db.session() as session:
            session.add(run)
            await session.flush()
        return run

    async def get(self, drill_id: str) -> DrillRun | None:
        async with self._db.readonly() as session:
            return await session.get(DrillRun, drill_id)

    async def save(self, run: DrillRun) -> None:
        """任务推进写回（节点状态/result/summary——任务行是域内聚合，非 append-only）。"""
        run.updated_at = now()
        async with self._db.session() as session:
            await session.merge(run)

    async def has_running(self) -> bool:
        async with self._db.readonly() as session:
            count = await session.scalar(
                select(func.count()).select_from(DrillRun).where(DrillRun.status == "running")
            )
        return bool(count)

    async def close_stale_running(self, *, summary: str) -> int:
        """遗留 running 行收口为 done（进程崩溃重启后的僵尸收口——幂等，无行即 0）。

        任务体是进程内 asyncio task：进程死了任务必死，DB 行却遗留 running
        → has_running() 恒真 → 重启后所有 start_drill 永久 409。启动时收口
        一次（done＋人话 summary），双态合同 running|done 不新增第三态。
        """
        async with self._db.session() as session:
            rows = (
                (await session.execute(select(DrillRun).where(DrillRun.status == "running")))
                .scalars()
                .all()
            )
            at = now()
            for row in rows:
                row.status = "done"
                row.summary = summary
                row.finished_at = at
                row.updated_at = at
            await session.flush()
            return len(rows)

    async def history(self) -> list[DrillSummary]:
        """done 行倒序（D1 端点 7：[{id, time, summary}]——time 取 finished_at）。"""
        async with self._db.readonly() as session:
            rows = (
                (
                    await session.execute(
                        select(DrillRun)
                        .where(DrillRun.status == "done")
                        .order_by(DrillRun.finished_at.desc(), DrillRun.id.desc())
                    )
                )
                .scalars()
                .all()
            )
        return [
            DrillSummary(
                id=r.id,
                time=r.finished_at or r.started_at,
                summary=r.summary or "",
            )
            for r in rows
        ]


class BudgetStore:
    """双阈值单例行（缺省自动种子——D5 合同默认值 0.05/800，判据消费方＝complete）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def limits(self) -> tuple[float, float]:
        """返回 (per_call_cost_limit_yuan, gateway_budget_yuan_per_month)；无行落合同默认。"""
        async with self._db.session() as session:
            row = await session.get(BudgetConfigRow, "singleton")
            if row is None:
                row = BudgetConfigRow(
                    id="singleton",
                    per_call_cost_limit_yuan=0.05,  # F2 改注合同默认（D5 §8）
                    gateway_budget_yuan_per_month=800.0,  # GATEWAY_BUDGET 演示值（D5 §8）
                )
                session.add(row)
                await session.flush()
            return float(row.per_call_cost_limit_yuan), float(row.gateway_budget_yuan_per_month)


async def ensure_gateway_tables(engine: AsyncEngine) -> None:
    """建表函数（P0-08 前票面约定：无 Alembic；99 §2.13 三表逐字段）。"""
    for model in (SpendRecord, DrillRun, BudgetConfigRow):
        table = cast(Table, model.__table__)
        async with engine.begin() as conn:
            await conn.run_sync(table.create, checkfirst=True)
