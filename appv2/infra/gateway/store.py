"""domains.gateway.store —— 网关域三表（99 §2.13 逐字段）与仓储。

V2 复制层（V2-01 自 V1 app/domains/gateway/store.py 复制清理——仅模块路径
app.* → appv2.*，语义逐字节同形；本三表为网关域纪律表，非业务表——specs/
infra.md「不带」清单的 kb_*/sem_*/chat_* 业务 ORM 零出现）。

- `gateway_spend_record`：花费账本（**全平台唯一**——D5 裁决一「不建第二份
  账本」，D5 将来只做 run 聚合投影）。演练即真实流量同表落账；`caller` 归因列
  （D1 v0.2：网关受理时落列、枚举不封闭、存量可空聚合归 unattributed）＋
  id/note pg_trgm GIN 索引（spend-logs keyword 子串检索——内存过滤惯例本端点
  退役，与 Alembic 0011 双轨同形）。
- `gateway_drill_run`：故障演练任务（done 落两笔账之历史行；节点/结果 jsonb）。
- `gateway_budget_config`：花费双阈值单例行（判据消费方＝本域 complete；
  D1 v0.2 起读写面归端点 2/3 config 族）。

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
    case,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from appv2.infra.clock import now
from appv2.infra.db import Base, ConnectionManager, Page
from appv2.infra.gateway.domain import (
    UNATTRIBUTED,
    DrillSummary,
    SpendFilter,
    SpendStatsFilter,
    SpendStatsPage,
    SpendStatsRow,
    SpendStatsSums,
    SpendView,
)

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
    caller: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 调用方归因（D1 v0.2）
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
        caller=row.caller,
    )


def _like_pattern(keyword: str) -> str:
    """keyword → LIKE 模式（子串语义；通配符转义防用户 %/_ 劫持匹配面）。"""
    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _stats_bucket_expr(group_by: str, dialect: str) -> Any:
    """分组键表达式（caller 存量空值归 unattributed 桶——D1 v0.2 合同值）。"""
    if group_by == "caller":
        return func.coalesce(SpendRecord.caller, UNATTRIBUTED)
    if group_by == "model":
        return SpendRecord.model_key
    if dialect == "postgresql":
        fmt = "YYYY-MM-DD" if group_by == "day" else "YYYY-MM"
        return func.to_char(SpendRecord.time, fmt)
    fmt = "%Y-%m-%d" if group_by == "day" else "%Y-%m"
    return func.strftime(fmt, SpendRecord.time)


def _stats_group_keys(group_by: str, bucket: Any) -> list[Any]:
    """GROUP BY 键列（model 维度按 model_key 分组、alias 取组内代表值）。"""
    if group_by == "model":
        return [SpendRecord.model_key]
    return [bucket]


# ---------- 仓储 ----------


class SpendStore:
    """账本仓储（append-only——记账不删改；读面分页 SQL 筛选＋聚合投影）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def add(self, row: SpendRecord) -> SpendRecord:
        async with self._db.session() as session:
            session.add(row)
            await session.flush()
        return row

    async def _filter_conditions(self, spend_filter: SpendFilter) -> list[Any]:
        """筛选条件单源（分页与计数共用——total 恒对当前筛选条件，R3）。"""
        conds: list[Any] = []
        if spend_filter.model != "all":
            conds.append(SpendRecord.model_key == spend_filter.model)
        since = spend_filter.since(now())
        if since is not None:
            conds.append(SpendRecord.time >= since)
        if spend_filter.keyword:
            # keyword 匹配调用号/备注——SQL LIKE 子串（PG pg_trgm GIN 索引加速，
            # Alembic 0011；「98 keyword 内存过滤惯例」本端点退役）
            pattern = _like_pattern(spend_filter.keyword)
            conds.append(
                or_(
                    SpendRecord.id.like(pattern, escape="\\"),
                    SpendRecord.note.like(pattern, escape="\\"),
                )
            )
        return conds

    async def page(
        self, spend_filter: SpendFilter, *, page: int = 1, page_size: int = 15
    ) -> Page[SpendView]:
        """倒序分页读面（排序恒 time 倒序——D1 合同；total＝筛选后 SQL 计数，R3）。"""
        page = max(page, 1)
        page_size = max(page_size, 1)
        conds = await self._filter_conditions(spend_filter)
        async with self._db.readonly() as session:
            total = await session.scalar(
                select(func.count()).select_from(SpendRecord).where(*conds)
            )
            rows = (
                (
                    await session.execute(
                        select(SpendRecord)
                        .where(*conds)
                        .order_by(SpendRecord.time.desc(), SpendRecord.id.desc())
                        .offset((page - 1) * page_size)
                        .limit(page_size)
                    )
                )
                .scalars()
                .all()
            )
        return Page(
            items=[_to_spend_view(r) for r in rows],
            total=int(total or 0),
            page=page,
            page_size=page_size,
        )

    async def stats(
        self, stats_filter: SpendStatsFilter, *, page: int = 1, page_size: int = 15
    ) -> SpendStatsPage:
        """端点 8 聚合投影（账本唯一真源 GROUP BY——不建第二份账本）。

        caller/model 维度＝分组键全量聚合后按 cost_yuan 降序分页（组数＝归因
        域数，演示量级个位）；day/month＝趋势时序升序全量、page/pageSize 忽略
        （合同：行数受 range 天然约束）。sums＝窗口全量合计（不随分页截断），
        由全组行求和承载（组是窗口的划分，求和即全量）。
        """
        page = max(page, 1)
        page_size = max(page_size, 1)
        since = stats_filter.since(now())  # 统计窗＝端点 8 族（all|7d|30d|12m）——不是端点 4 族
        conds: list[Any] = []
        if since is not None:
            conds.append(SpendRecord.time >= since)
        async with self._db.readonly() as session:
            dialect = session.get_bind().dialect.name
            bucket = _stats_bucket_expr(stats_filter.group_by, dialect)
            cost_sum = func.sum(SpendRecord.cost_yuan)
            stmt = select(
                bucket.label("bucket"),
                func.count().label("calls"),
                func.coalesce(
                    func.sum(case((SpendRecord.fallback.is_(True), 1), else_=0)), 0
                ).label("fallback_calls"),
                func.coalesce(func.sum(SpendRecord.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(SpendRecord.output_tokens), 0).label("output_tokens"),
                func.coalesce(cost_sum, 0.0).label("cost_yuan"),
            )
            if stats_filter.group_by == "model":
                stmt = stmt.add_columns(func.max(SpendRecord.alias).label("alias"))
            stmt = stmt.where(*conds).group_by(*_stats_group_keys(stats_filter.group_by, bucket))
            stmt = stmt.order_by(
                bucket.asc() if stats_filter.group_by in ("day", "month") else cost_sum.desc()
            )
            groups = (await session.execute(stmt)).all()
        items = [
            SpendStatsRow(
                bucket=str(row.bucket),
                alias=getattr(row, "alias", None),
                calls=int(row.calls),
                fallback_calls=int(row.fallback_calls),
                input_tokens=int(row.input_tokens),
                output_tokens=int(row.output_tokens),
                cost_yuan=float(row.cost_yuan),
            )
            for row in groups
        ]
        if stats_filter.group_by in ("caller", "model"):
            window = items[(page - 1) * page_size : (page - 1) * page_size + page_size]
        else:
            window = items  # day/month＝趋势时序全量（分页忽略——合同原话）
        return SpendStatsPage(
            group_by=stats_filter.group_by,
            range=stats_filter.range,
            items=window,
            sums=SpendStatsSums(
                calls=sum(i.calls for i in items),
                fallback_calls=sum(i.fallback_calls for i in items),
                cost_yuan=sum(i.cost_yuan for i in items),
            ),
            total=len(items),
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
    """双阈值单例行（缺省自动种子——D1/D5 合同默认值 0.05/800，判据消费方＝complete）。"""

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
            try:
                await session.flush()
            except Exception:  # 并发同插 singleton（G-06 并发闸下首次落账竞速）——回读既有行
                await session.rollback()
                row = await session.get(BudgetConfigRow, "singleton")
                if row is None:
                    raise
            return float(row.per_call_cost_limit_yuan), float(row.gateway_budget_yuan_per_month)

    async def save(self, per_call_cost_limit_yuan: float, monthly_yuan: float) -> None:
        """端点 3 保存预算双阈值（单例行 upsert；直接生效——complete 每次现读）。"""
        async with self._db.session() as session:
            row = await session.get(BudgetConfigRow, "singleton")
            if row is None:
                row = BudgetConfigRow(
                    id="singleton",
                    per_call_cost_limit_yuan=per_call_cost_limit_yuan,
                    gateway_budget_yuan_per_month=monthly_yuan,
                )
                session.add(row)
            else:
                row.per_call_cost_limit_yuan = per_call_cost_limit_yuan
                row.gateway_budget_yuan_per_month = monthly_yuan
            row.updated_at = now()
            await session.flush()


async def ensure_gateway_tables(engine: AsyncEngine) -> None:
    """建表函数（P0-08 前票面约定：无 Alembic；99 §2.13 三表逐字段）。

    PG 并建 pg_trgm 扩展＋spend 账本 id/note trgm GIN 索引（P1-10 起 keyword
    SQL 检索的物理落法，与 Alembic 0011 双轨同形——kb ensure_kb_tables 先例）。
    """
    for model in (SpendRecord, DrillRun, BudgetConfigRow):
        table = cast(Table, model.__table__)
        async with engine.begin() as conn:
            await conn.run_sync(table.create, checkfirst=True)
    if engine.dialect.name == "postgresql":
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_gateway_spend_note_trgm "
                "ON gateway_spend_record USING gin (note gin_trgm_ops)"
            ))
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_gateway_spend_id_trgm "
                "ON gateway_spend_record USING gin (id gin_trgm_ops)"
            ))
