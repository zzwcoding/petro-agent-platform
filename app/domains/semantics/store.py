"""domains.semantics.store —— sem_* 九表 ORM（99 §2.8 逐字段）与建表/仓储。

表清单（99 §2.8 semantics —— 语义台账域，写口唯一纪律见 B4/98 §3.7）：
    sem_term / sem_metric / sem_object / sem_relation / sem_join_whitelist /
    sem_workflow / sem_action / sem_ledger_revision / sem_version

落库裁决（tickets/phase1/README.md P1-01）：
- 建表双轨并行存活（P0-08 交接关系首执行点）：ensure_semantics_tables（幂等
  checkfirst，main.py lifespan——沿 P0-04 audit / P0-05 gateway 惯例）与
  Alembic 迁移 0002_sem_baseline（sem 域首迁移）同批落；后续域票照此序。
- 枚举落 CHECK（99 §1.4 裁决）：sem_term.status_key 六值 / sem_metric.mark
  ★☆ / sem_join_whitelist.verdict 两值 / sem_workflow.status 两值 /
  sem_ledger_revision.domain 七值——合同冻结枚举进 DDL，违约即 DB 层报错。
- jsonb 列（99 §1.5 裁决清单）：sem_metric.status/calibers/modifiers、
  sem_workflow.card、sem_ledger_revision.payload——整读整存、无内部字段
  SQL 查询；sqlite 单测底座以 JSON 文本落（非生产角色替身）。
- 台账行禁手工改（ADR-0004 投影纪律）：本模块外的写路径只有
  SemanticsService.sync_from_ontology_repo（本体仓同步投影）与将来的
  apply_definition_merge/rollback_to（governance 汇入批）——变更一律随
  sem_ledger_revision 行版本轴留痕。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.clock import now
from app.infra.db import Base

# jsonb（99 §2.8）——PG/金仓真 jsonb；sqlite 单测底座以 JSON 文本落。
_JSON = JSONB().with_variant(JSON(), "sqlite")


class SemTerm(Base):
    """sem_term——业务术语账现行行（99 §2.8；C1 端点 2）。"""

    __tablename__ = "sem_term"
    __table_args__ = (
        CheckConstraint(
            "status_key IN ('有效','禁用词','有效（限作业区语境）',"
            "'有效（待联席裁决）','有效（引用马涛）','有效（已届满）')",
            name="ck_sem_term_status_key",
        ),
        Index("ix_sem_term_status_key_owner", "status_key", "owner"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    term: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # 类型展示串（含「别名 → X」族）
    def_: Mapped[str] = mapped_column("def", Text, nullable=False)  # 定义（列名照抄合同 DTO）
    status: Mapped[str] = mapped_column(Text, nullable=False)  # 状态展示串（双轨之展示面）
    status_key: Mapped[str] = mapped_column(String(24), nullable=False)  # 六值筛选键
    owner: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[Any] = mapped_column(Date, nullable=True)  # expired 现算派生不落列（F60）
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class SemMetric(Base):
    """sem_metric——指标口径账现行行（99 §2.8；C1 端点 3/4）。"""

    __tablename__ = "sem_metric"
    __table_args__ = (
        CheckConstraint("mark IS NULL OR mark IN ('★','☆')", name="ck_sem_metric_mark"),
        UniqueConstraint("slot_name", name="uq_sem_metric_slot_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)  # 台账原名（含 ★☆ 与括注尾缀）
    mark: Mapped[str | None] = mapped_column(String(1), nullable=True)  # ★晨会常问 / ☆专业常用
    slot_name: Mapped[str] = mapped_column(Text, nullable=False)  # 剥法纯名（服务端单点，票 93）
    def_: Mapped[str] = mapped_column("def", Text, nullable=False)
    grain: Mapped[str] = mapped_column(Text, nullable=False)  # 统计粒度（M3 口径字段组真源）
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[list[str]] = mapped_column(_JSON, nullable=False)  # 数组多徽标（#10 双徽标）
    owner: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    dispute: Mapped[str | None] = mapped_column(Text, nullable=True)
    modifiers: Mapped[list[str] | None] = mapped_column(_JSON, nullable=True)
    ambiguous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    calibers: Mapped[list[dict[str, Any]]] = mapped_column(_JSON, nullable=False, default=list)
    default_caliber: Mapped[str | None] = mapped_column(String(8), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class SemObject(Base):
    """sem_object——对象账现行行（草案态整体呈现；99 §2.8；C1 端点 5）。"""

    __tablename__ = "sem_object"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    obj: Mapped[str] = mapped_column(Text, nullable=False)
    attr: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)  # 「草案」恒定（固定值常量）
    owner: Mapped[str | None] = mapped_column(Text, nullable=True)  # null → 「—（未落）」
    source: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)  # null → 「—（未落）」
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class SemRelation(Base):
    """sem_relation——关系账现行行（99 §2.8；C1 端点 6）。"""

    __tablename__ = "sem_relation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    rel: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[str] = mapped_column(Text, nullable=False)  # 关系的人话读法（C1 列名照抄）
    source: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class SemJoinWhitelist(Base):
    """sem_join_whitelist——Join 白名单（连表合法性唯一判据源；99 §2.8；C1 端点 7）。"""

    __tablename__ = "sem_join_whitelist"
    __table_args__ = (
        CheckConstraint("verdict IN ('可以','默认不给')", name="ck_sem_join_whitelist_verdict"),
        Index("ix_sem_join_whitelist_left_right", "left_table", "right_table"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    left_table: Mapped[str] = mapped_column(Text, nullable=False)  # 机器键（判据结构化技术列）
    right_table: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[str] = mapped_column(String(8), nullable=False)  # 可以/默认不给（默认拒绝）
    tables: Mapped[str] = mapped_column(Text, nullable=False)  # 展示文本照抄 C1
    how: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class SemWorkflow(Base):
    """sem_workflow——分析工作流登记（99 §2.8；C1 端点 8/9）。"""

    __tablename__ = "sem_workflow"
    __table_args__ = (
        CheckConstraint("status IN ('登记','草案')", name="ck_sem_workflow_status"),
    )

    id: Mapped[str] = mapped_column(String(8), primary_key=True)  # wf1…wf10 注册序
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(4), nullable=False)  # 账号绑定两态（登记/草案）
    account: Mapped[str | None] = mapped_column(Text, nullable=True)  # null → 「未绑定」
    source: Mapped[str | None] = mapped_column(Text, nullable=True)  # null → 「未登记」
    card: Mapped[dict[str, Any]] = mapped_column(_JSON, nullable=False)  # 七项缺项 null，整卡读写
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class SemAction(Base):
    """sem_action——Action 合同（下线备查资产仍可读；99 §2.8；C1 端点 10）。"""

    __tablename__ = "sem_action"
    __table_args__ = (
        UniqueConstraint("register_name", name="uq_sem_action_register_name"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    register_name: Mapped[str] = mapped_column(String(64), nullable=False)
    business_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class SemLedgerRevision(Base):
    """sem_ledger_revision——台账行版本轴（共享 append-only；99 §2.8；C2 端点 7 事务②）。

    投影纪律（ADR-0004）：行版本轴同时承载本体仓同步器写入——
    sync_from_ontology_repo 消费 MR 合入事件、钉版 schemaVersion 1.1.0，
    changed_by 记同步器身份；台账行禁手工改。
    """

    __tablename__ = "sem_ledger_revision"
    __table_args__ = (
        CheckConstraint(
            "domain IN ('term','metric','object','relation','whitelist','workflow','action')",
            name="ck_sem_ledger_revision_domain",
        ),
        UniqueConstraint("domain", "row_id", "version", name="uq_sem_ledger_revision_row_ver"),
        Index("ix_sem_ledger_revision_source_proposal", "source_proposal_id"),
    )

    # bigserial：PG/金仓渲染 BIGSERIAL；sqlite 单测底座经 variant 渲染 INTEGER。
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True
    )
    domain: Mapped[str] = mapped_column(String(16), nullable=False)
    row_id: Mapped[str] = mapped_column(Text, nullable=False)  # 各账行 id（int/text 族统 text）
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(_JSON, nullable=False)  # 该版全行快照
    changed_by: Mapped[str] = mapped_column(Text, nullable=False)  # 同步器身份/审批人（who 槽）
    source_proposal_id: Mapped[str | None] = mapped_column(Text, nullable=True)  # 汇入提案可溯
    changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class SemVersion(Base):
    """sem_version——语义层全量版本轴（单例行；99 §2.8；C1/C2/C3/D3 同一口径）。

    与行版本轴（sem_ledger_revision）显式分离（C2 对账 8）；版本推进只发生在
    治理链发布事务（C3）——同步器投影不推全量版本。
    """

    __tablename__ = "sem_version"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default="current")
    current: Mapped[str] = mapped_column(Text, nullable=False)  # 形如 v37（C3 演示值同源）
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


SEM_TABLE_MODELS: tuple[type[Base], ...] = (
    SemTerm,
    SemMetric,
    SemObject,
    SemRelation,
    SemJoinWhitelist,
    SemWorkflow,
    SemAction,
    SemLedgerRevision,
    SemVersion,
)


async def ensure_semantics_tables(engine: AsyncEngine) -> None:
    """建表函数（幂等 checkfirst，P0-04 惯例）——sem_* 九表 99 §2.8 逐字段。

    与 Alembic 0002_sem_baseline 并行存活（P0-08 交接关系；本票即首执行点，
    票面登记见 tickets/phase1/README.md P1-01）。
    """
    for model in SEM_TABLE_MODELS:
        table = cast(Table, model.__table__)
        async with engine.begin() as conn:
            await conn.run_sync(table.create, checkfirst=True)


async def load_current_version(session: AsyncSession) -> str | None:
    """语义层当前全量版本读面（C1/C3 同口径锚点；无行即 None）。"""
    row = await session.get(SemVersion, "current")
    return None if row is None else row.current


async def latest_row_version(
    session: AsyncSession, domain: str, row_id: str
) -> int:
    """某台账行当前版本号（无 revision 行＝0——首写即落 version 1）。"""
    stmt = (
        select(SemLedgerRevision.version)
        .where(
            SemLedgerRevision.domain == domain,
            SemLedgerRevision.row_id == row_id,
        )
        .order_by(SemLedgerRevision.version.desc())
        .limit(1)
    )
    value = await session.scalar(stmt)
    return int(value or 0)
