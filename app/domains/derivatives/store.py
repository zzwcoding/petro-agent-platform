"""domains.derivatives.store —— wiki 表族（99 §2.7 逐字段）与仓储。

- `wiki_page`：百科页（1:1 报告；当前版指针）——id（wiki- slug，稳定不随
  重建变化）·title·lib_id FK·source_report_id FK·current_version int
  ·updated_at；digest（一句话摘要——页级元数据，随自动生成刷新；B4 端点 2
  `?version=N` 取该版固化值的字段清单不含 digest，故落页级不落版本级）。
- `wiki_page_version`：版本 append-only（回滚＝追加新版本、指针前进）——
  content（自由 markdown 全文——B4 v0.3 改版：99 册 `body` 五段 jsonb 已被
  v0.3 拍板撤除，登记于 tickets/phase1 README）＋claims/glossary_terms jsonb
  （生成时固化随版本走）＋source CHECK(`自动重建,智能体,人工,回滚`)（F52 ①
  四态冻结值照抄）＋desc/operator/task_no（v0.3 落位列）。
- `status` 不落列（B4：按当前版正文有无 [[flag:]] 派生——99 §2.7 同注）；
  `generation_source/operator` 从当前版本行派生；`related_objects` 为报告读
  面投影（票 93 不建仓——derivatives 读面直取，不落第二份）。
- ensure_derivatives_tables 幂等 checkfirst（P0-04 惯例），与 Alembic 0004
  并行存活（双轨退役拍挂后续票——P1-01 差异 10 同口径）。

边界：B3（只经 infra.db）、B14（时间只经 infra.clock）、B1（不咬框架）。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, cast

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.domains.derivatives import domain as d
from app.infra.clock import now
from app.infra.db import Base, ConnectionManager

_J = JSONB().with_variant(JSON(), "sqlite")


class WikiPageRow(Base):
    """wiki_page——百科页（1:1 报告；当前版指针；slug 稳定性＝id 承载）。"""

    __tablename__ = "wiki_page"
    __table_args__ = (
        Index("ix_wiki_page_lib", "lib_id"),
        Index("ix_wiki_page_updated", text("updated_at DESC")),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # wiki- slug
    title: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str | None] = mapped_column(Text, nullable=True)
    lib_id: Mapped[str] = mapped_column(String(32), ForeignKey("kb_library.id"), nullable=False)
    source_report_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("kb_report.id"), nullable=False, unique=True
    )
    current_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(nullable=True)


class WikiPageVersionRow(Base):
    """wiki_page_version——百科版本（append-only；回滚＝追加新版本）。"""

    __tablename__ = "wiki_page_version"
    __table_args__ = (
        CheckConstraint(
            "source IN ('自动重建','智能体','人工','回滚')",
            name="ck_wiki_page_version_source",
        ),
    )

    page_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("wiki_page.id"), primary_key=True
    )
    v: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    claims: Mapped[list[dict[str, Any]]] = mapped_column(_J, nullable=False, default=list)
    glossary_terms: Mapped[list[dict[str, Any]]] = mapped_column(
        _J, nullable=False, default=list
    )
    source: Mapped[str] = mapped_column(String(8), nullable=False, default=d.SOURCE_AUTO)
    desc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    operator: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class ExtractConfigRow(Base):
    """kb_extract_config——按库抽取设置（99 §2.7 逐字段；仍留 PG——ADR-0003）。

    与 B1 库配置（kb_library_config）并列、互不嵌套（B5 端点 2 注记）；
    保存＝写待生效配置（下次入库定型不热切换——F32 同族语义）。
    """

    __tablename__ = "kb_extract_config"

    lib_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("kb_library.id"), primary_key=True
    )
    entity_types: Mapped[list[Any]] = mapped_column(_J, nullable=False, default=list)
    relation_tags: Mapped[list[dict[str, Any]]] = mapped_column(
        _J, nullable=False, default=list
    )
    custom_instructions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    few_shot_examples: Mapped[list[dict[str, Any]]] = mapped_column(
        _J, nullable=False, default=list
    )
    saved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    saved_by: Mapped[str | None] = mapped_column(Text, nullable=True)


DERIVATIVES_TABLES: tuple[type[Base], ...] = (
    WikiPageRow,
    WikiPageVersionRow,
    ExtractConfigRow,
)


async def ensure_derivatives_tables(engine: AsyncEngine) -> None:
    """建表函数（幂等 checkfirst，P0-04 惯例）——与 Alembic 0004 并行存活。"""
    for model in DERIVATIVES_TABLES:
        table = cast(Table, model.__table__)
        async with engine.begin() as conn:
            await conn.run_sync(table.create, checkfirst=True)


class WikiStore:
    """wiki 表族仓储（多写显式 flush 排序——无 relationship 的 UOW 先例）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def page(self, page_id: str) -> WikiPageRow | None:
        async with self._db.readonly() as session:
            return await session.get(WikiPageRow, page_id)

    async def page_by_report(self, report_id: str) -> WikiPageRow | None:
        async with self._db.readonly() as session:
            rows = (
                (
                    await session.execute(
                        select(WikiPageRow).where(
                            WikiPageRow.source_report_id == report_id
                        )
                    )
                )
                .scalars()
                .all()
            )
        return rows[0] if rows else None

    async def all_pages(self) -> list[WikiPageRow]:
        async with self._db.readonly() as session:
            rows = (
                (
                    await session.execute(
                        select(WikiPageRow).order_by(WikiPageRow.updated_at.desc().nullslast(),
                                                     WikiPageRow.id)
                    )
                )
                .scalars()
                .all()
            )
        return list(rows)

    async def versions_of(self, page_id: str) -> list[WikiPageVersionRow]:
        async with self._db.readonly() as session:
            rows = (
                (
                    await session.execute(
                        select(WikiPageVersionRow)
                        .where(WikiPageVersionRow.page_id == page_id)
                        .order_by(WikiPageVersionRow.v)
                    )
                )
                .scalars()
                .all()
            )
        return list(rows)

    async def version(self, page_id: str, v: int) -> WikiPageVersionRow | None:
        async with self._db.readonly() as session:
            return await session.get(WikiPageVersionRow, (page_id, v))

    async def create_page_with_version(
        self, page: WikiPageRow, version: WikiPageVersionRow
    ) -> tuple[WikiPageRow, WikiPageVersionRow]:
        """建页＋v1（slug 稳定性：1:1 建页后 id 恒定，重建原地追加版本）。"""
        async with self._db.session() as session:
            session.add(page)
            await session.flush()  # 页行先落——版本行 FK 依赖页
            session.add(version)
            await session.flush()
        return page, version

    async def append_version(
        self,
        page_id: str,
        version: WikiPageVersionRow,
        *,
        title: str | None = None,
        digest: str | None = None,
    ) -> tuple[WikiPageRow, WikiPageVersionRow]:
        """追加版本＋当前指针前进（版本只追加、不可篡改——B4 行为规则 1）。

        自动重建刷新页级 title/digest；回滚不动 digest（B4 `?version=N` 固化
        字段清单不含 digest——回滚横幅承载恢复语义）。
        """
        async with self._db.session() as session:
            page = await session.get(WikiPageRow, page_id)
            if page is None:
                raise d.WikiNotFoundError(f"百科页不存在：{page_id}")
            if title is not None:
                page.title = title
            if digest is not None:
                page.digest = digest
            page.current_version = version.v
            page.updated_at = now()
            session.add(page)
            await session.flush()
            session.add(version)
            await session.flush()
        return page, version


class ExtractConfigStore:
    """kb_extract_config 仓储（B5 端点 2/3——按库整存整取）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def config_of(self, lib_id: str) -> ExtractConfigRow | None:
        async with self._db.readonly() as session:
            return await session.get(ExtractConfigRow, lib_id)

    async def save(
        self, lib_id: str, cfg: d.ExtractConfig, *, actor_who: str,
        record_activity: Callable[[AsyncSession], Awaitable[None]] | None = None,
    ) -> ExtractConfigRow:
        """写待生效配置（下次入库定型；不动正在处理的入库任务——各 run 用
        自己的快照）。

        record_activity（B5 端点 3 合同「保存同事务记 B1 活动流 F62」——
        P1-05b 审查裁决）：传入时在**同一会话/事务内**追加活动行——活动行
        与配置行同 commit/同 rollback，保存回滚时活动行不孤儿、活动行写入
        失败时配置保存同败（丢失窗口消除）。B9 边界不破：callable 由服务层
        以组合根注入的 kb 写口装配（kb 侧经 session 注入追加，本仓不见
        kb 表模型）。
        """
        snapshot = cfg.as_snapshot()
        async with self._db.session() as session:
            row = await session.get(ExtractConfigRow, lib_id)
            if row is None:
                row = ExtractConfigRow(lib_id=lib_id)
            row.entity_types = list(snapshot["entity_types"])
            row.relation_tags = list(snapshot["relation_tags"])
            row.few_shot_examples = list(snapshot["few_shot_examples"])
            row.custom_instructions = snapshot["custom_instructions"]
            row.saved_at = now()
            row.saved_by = actor_who
            await session.merge(row)
            await session.flush()
            if record_activity is not None:
                await record_activity(session)
            return row
