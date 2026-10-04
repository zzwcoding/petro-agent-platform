"""domains.dataops.quality.store —— quality 表族取数与留痕（99 §2.12 六表五用）。

边界（票面红线：表结构不改——DP-05 迁移 0015 已落列形）：
- B3：只走 infra.db——读走 ``db.readonly()``（意图级 flush 守卫恒挂），写走
  ``db.session()``（轻会话块末自动提交/异常回滚——retrieval 先例）或调用方
  传入会话（同事务多写：问题单态＋流转留痕行原子落）。
- 表结构真源＝migrations/versions/20261004_0015_quality_waterline.py（本域
  ORM 声明与迁移逐列同形、零 DDL 创新）；``ensure_quality_tables`` 幂等
  checkfirst——Alembic 并行存活惯例（P0-08 约定，本票不切换）；种子（20 条
  规则）随迁移承载，ORM 侧不重播（单一来源）。
- 隔离区 append-only（E2 端点 9/行为约定 3）：坏行 payload/loc/batch_id/
  rule_no/action 永不改写、无删除出口；唯一 UPDATE＝issue_id 回挂（建单后
  回链——0015 列注记明示归本票写，payload 零触碰）。
- 诊断说明 ai_note 存储恒可空（0015 列注记——v0.5 服务端投影规则判据，
  读侧拼装在 service，不落列）。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.infra.clock import now
from app.infra.db import Base, ConnectionManager, Page, ReadOnlyRepository

# ---------- ORM 声明（0015 列形照抄——零 DDL 创新） ----------


class QualityRule(Base):
    """quality_rule——质检规则（20 条种子＋启停态；判据权威源＝本体 M3）。"""

    __tablename__ = "quality_rule"

    no: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    rule: Mapped[str] = mapped_column(String(512), nullable=False)
    crit: Mapped[str] = mapped_column(String(512), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    autofix: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )


class QualityIssue(Base):
    """quality_issue——问题单（五态状态机；dedupe_key 挂单去重唯一）。"""

    __tablename__ = "quality_issue"
    __table_args__ = (
        Index("idx_quality_issue_rule_no", "rule_no"),
        Index("idx_quality_issue_lane", "lane"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    lane: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    rule_no: Mapped[int] = mapped_column(
        Integer, ForeignKey("quality_rule.no"), nullable=False
    )
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    dedupe_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    title: Mapped[str | None] = mapped_column(String(256))
    # 合同 DTO 键即 `desc`——SQL 保留字由方言引号承载（0015 同 0009 group 先例）。
    desc: Mapped[str | None] = mapped_column("desc", String(1024))
    owner: Mapped[str | None] = mapped_column(String(128))  # 责任岗展示文案（含环节前缀）
    # v0.5：存储恒可空——读侧投影规则判据（service），LLM 起草语义冻结挂观察。
    ai_note: Mapped[str | None] = mapped_column(String(1024))
    verify: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite")
    )
    close_note: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)


class QualityIssueTransition(Base):
    """quality_issue_transition——流转留痕（操作人/时间/前后态，与 A3 审计同口径）。"""

    __tablename__ = "quality_issue_transition"

    issue_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("quality_issue.id"), primary_key=True
    )
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_lane: Mapped[int | None] = mapped_column(SmallInteger)
    to_lane: Mapped[int | None] = mapped_column(SmallInteger)
    operator: Mapped[str | None] = mapped_column(String(64))
    time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)


class QuarantineRow(Base):
    """quarantine_row——隔离区（append-only；唯一 UPDATE＝issue_id 回挂）。"""

    __tablename__ = "quarantine_row"
    __table_args__ = (
        Index("idx_quarantine_row_batch_id", "batch_id"),
        Index("idx_quarantine_row_rule_no", "rule_no"),
        Index("idx_quarantine_row_issue_id", "issue_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    batch_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_no: Mapped[int] = mapped_column(
        Integer, ForeignKey("quality_rule.no"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    loc: Mapped[str | None] = mapped_column(String(256))
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False
    )
    issue_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("quality_issue.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)


class WaterLine(Base):
    """water_line——三层数据新鲜度水位（原始/清洗＝入湖回写、汇总＝agg 刷新）。"""

    __tablename__ = "water_line"

    layer: Mapped[str] = mapped_column(String(8), primary_key=True)
    data_date: Mapped[date] = mapped_column(Date, nullable=False)
    promise: Mapped[str] = mapped_column(String(8), nullable=False, default="T-1")
    refreshed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now)


_QUALITY_TABLES = (
    QualityRule.__table__,
    QualityIssue.__table__,
    QualityIssueTransition.__table__,
    QuarantineRow.__table__,
    WaterLine.__table__,
)


async def ensure_quality_tables(engine: AsyncEngine) -> None:
    """quality 五表幂等建表（P0-08 惯例——与 Alembic 0015 并行存活；本票不切换）。

    PG 上 0015 已建即 checkfirst 跳过（种子/约束随迁移）；sqlite 单测底座经
    本函数落 ORM 同形表。quality_task（第六表）归 M-05b 执行通道票随其消费
    语义登记——本域无读写面不预挂（零死代码）。
    """
    await _create_tables(engine, _QUALITY_TABLES)


async def _create_tables(engine: AsyncEngine, tables: tuple[Any, ...]) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=list(tables), checkfirst=True
            )
        )


# ---------- 取数与留痕 ----------


class QualityStore:
    """quality 表族取数（读走 readonly；写会话由 service 开启或调用方传入）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    # ---------- 规则面（端点 1/2） ----------

    async def list_rules(self) -> list[QualityRule]:
        """规则全行（no 升序——规则号即台账序）。"""
        async with self._db.readonly() as session:
            result = await session.execute(select(QualityRule).order_by(QualityRule.no))
        return list(result.scalars().all())

    async def get_rule(self, no: int) -> QualityRule | None:
        async with self._db.readonly() as session:
            return await session.get(QualityRule, no)

    async def set_rule_enabled(self, no: int, enabled: bool) -> bool:
        """启停写口（端点 2——本域唯一 quality_rule 写出口；返回是否命中行）。"""
        async with self._db.session() as session:
            rule = await session.get(QualityRule, no)
            if rule is None:
                return False
            rule.enabled = enabled
        return True

    # ---------- 问题单面（端点 6/7＋挂单语义） ----------

    async def page_issues(
        self,
        *,
        lane: int | None = None,
        rule_no: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[QualityIssue]:
        """问题单分页（lane/rule_no 可选筛选；序＝lane 升序＋建单先后——五态队列）。"""
        stmt = select(QualityIssue).order_by(QualityIssue.lane.asc(), QualityIssue.id.asc())
        if lane is not None:
            stmt = stmt.where(QualityIssue.lane == lane)
        if rule_no is not None:
            stmt = stmt.where(QualityIssue.rule_no == rule_no)
        async with self._db.readonly() as session:
            return await ReadOnlyRepository.paginate(
                session, stmt, page=page, page_size=page_size
            )

    async def get_issue(self, issue_id: str) -> QualityIssue | None:
        async with self._db.readonly() as session:
            return await session.get(QualityIssue, issue_id)

    async def qrows_by_issue(
        self, issue_ids: list[str]
    ) -> dict[str, list[QuarantineRow]]:
        """问题单 → 隔离/拦截明细（issue_id 回挂行；id 升序＝落区先后）。"""
        if not issue_ids:
            return {}
        stmt = (
            select(QuarantineRow)
            .where(QuarantineRow.issue_id.in_(issue_ids))
            .order_by(QuarantineRow.id.asc())
        )
        async with self._db.readonly() as session:
            rows = (await session.execute(stmt)).scalars().all()
        grouped: dict[str, list[QuarantineRow]] = {}
        for row in rows:
            grouped.setdefault(row.issue_id or "", []).append(row)
        return grouped

    async def list_quarantine(
        self,
        *,
        batch_id: str | None = None,
        rule_no: int | None = None,
        issue_id: str | None = None,
    ) -> list[QuarantineRow]:
        """隔离区读面（端点 9——batch/rule/issue 三过滤可组合；id 升序 append 序）。"""
        stmt = select(QuarantineRow).order_by(QuarantineRow.id.asc())
        if batch_id is not None:
            stmt = stmt.where(QuarantineRow.batch_id == batch_id)
        if rule_no is not None:
            stmt = stmt.where(QuarantineRow.rule_no == rule_no)
        if issue_id is not None:
            stmt = stmt.where(QuarantineRow.issue_id == issue_id)
        async with self._db.readonly() as session:
            rows = (await session.execute(stmt)).scalars().all()
        return list(rows)

    async def list_water_lines(self) -> list[WaterLine]:
        """水位全行（三 tier 逐层一行——排序在 service 按固定 tier 序）。"""
        async with self._db.readonly() as session:
            rows = (await session.execute(select(WaterLine))).scalars().all()
        return list(rows)

    # ---------- 会话内写（service 开启 db.session()——同事务原子） ----------

    @staticmethod
    async def max_transition_seq(session: AsyncSession, issue_id: str) -> int:
        """流转序号现值（无留痕行＝0——seq 从 1 起）。"""
        stmt = (
            select(QualityIssueTransition.seq)
            .where(QualityIssueTransition.issue_id == issue_id)
            .order_by(QualityIssueTransition.seq.desc())
            .limit(1)
        )
        last = (await session.execute(stmt)).scalar()
        return int(last or 0)

    @staticmethod
    async def append_transition(
        session: AsyncSession,
        *,
        issue_id: str,
        seq: int,
        from_lane: int,
        to_lane: int,
        operator: str,
    ) -> None:
        session.add(
            QualityIssueTransition(
                issue_id=issue_id, seq=seq, from_lane=from_lane,
                to_lane=to_lane, operator=operator, time=now(),
            )
        )

    @staticmethod
    async def find_by_dedupe_key(session: AsyncSession, dedupe_key: str) -> QualityIssue | None:
        stmt = select(QualityIssue).where(QualityIssue.dedupe_key == dedupe_key)
        return (await session.execute(stmt)).scalars().first()

    @staticmethod
    async def next_dynamic_issue_id(session: AsyncSession) -> str:
        """动态单号（d 前缀序——原型种子 d1/d3… 同族；max+1 单调不复用）。"""
        stmt = select(QualityIssue.id).where(QualityIssue.id.like("d%"))
        existing = (await session.execute(stmt)).scalars().all()
        max_seq = 0
        for raw in existing:
            digits = raw[1:]
            if digits.isdigit():
                max_seq = max(max_seq, int(digits))
        return f"d{max_seq + 1}"

    @staticmethod
    async def add_issue(session: AsyncSession, issue: QualityIssue) -> QualityIssue:
        session.add(issue)
        await session.flush()  # FK 被引用方先落（P1-06 flush 排序纪律）
        return issue

    @staticmethod
    async def attach_quarantine_rows(
        session: AsyncSession, issue_id: str, row_ids: list[int]
    ) -> int:
        """隔离行 issue_id 回挂（建单后回链——append-only 例外口，payload 零触碰）。"""
        if not row_ids:
            return 0
        stmt = select(QuarantineRow).where(QuarantineRow.id.in_(row_ids))
        rows = (await session.execute(stmt)).scalars().all()
        for row in rows:
            row.issue_id = issue_id
        return len(rows)
