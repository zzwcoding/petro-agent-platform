"""domains.faq.store —— faq 域四表（99 §2.6 逐字段）与仓储。

- `faq_entry` / `faq_similar_question` / `faq_candidate` / `faq_scan_task`：
  99 §2.6 逐字段（`faq_config` 已撤除——扩检收敛 D2 `qa_behavior.faq_expand_rounds`，
  B3 v0.2 端点撤除登记，不建表）。
- 差异登记（99 关键列未列、审核流落定需要）：`faq_entry.is_negative` bool——
  待审核行承载负例登记意向（端点 3 `is_negative`），审核 publish 落定
  `status: negative`；kb_upload.lib_id 可空先例同族，登记 tickets/phase1
  README P1-06 差异清单。
- `question_norm`/`norm_hash`（条目）与 `text_norm`（相似问）为归一化派生列
  （归一化规则在 domain.normalize_text——SHA256 族＝票 49）。
- ensure_faq_tables 幂等 checkfirst（P0-04 惯例），与 Alembic 0007 并行存活
  （双轨退役拍挂后续票——P1-01 差异 10 同口径）。

边界：B3（只经 infra.db）、B14（时间只经 infra.clock）、B1（不咬框架）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    delete,
    func,
    insert,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.domains.faq import domain as d
from app.infra.clock import now
from app.infra.db import Base, ConnectionManager

_J = JSONB().with_variant(JSON(), "sqlite")


class EntryRow(Base):
    """faq_entry——问答条目（三态互斥状态机＋待审核前置态；99 §2.6 逐字段）。"""

    __tablename__ = "faq_entry"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_review','serve','negative','disabled')",
            name="ck_faq_entry_status",
        ),
        CheckConstraint("hook_kind IS NULL OR hook_kind IN ('metric','term')",
                        name="ck_faq_entry_hook_kind"),
        Index("ix_faq_entry_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # faq-<n>
    question: Mapped[str] = mapped_column(Text, nullable=False)
    question_norm: Mapped[str] = mapped_column(Text, nullable=False)
    norm_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    is_negative: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hook_kind: Mapped[str | None] = mapped_column(String(8), nullable=True)
    hook_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    maintainer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    # 展示日期粒度读侧取 date（R2 展示串不入库）
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)

    def hook(self) -> d.Hook | None:
        if self.hook_kind and self.hook_name:
            return d.Hook(kind=self.hook_kind, name=self.hook_name)
        return None


class SimilarRow(Base):
    """faq_similar_question——相似问（独立检索项，W-F35-2 分离索引）。"""

    __tablename__ = "faq_similar_question"
    __table_args__ = (
        Index("ix_faq_similar_entry", "entry_id"),
        Index("ix_faq_similar_text_norm", "text_norm"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # sq-<n>
    entry_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("faq_entry.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_norm: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class CandidateRow(Base):
    """faq_candidate——候选问题簇（候选状态机 pending→compared→drafted→published）。"""

    __tablename__ = "faq_candidate"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','compared','drafted','published')",
            name="ck_faq_candidate_status",
        ),
        CheckConstraint(
            "hook_kind IS NULL OR hook_kind IN ('metric','term')",
            name="ck_faq_candidate_hook_kind",
        ),
        Index("ix_faq_candidate_freq", "freq"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # c<n>
    question: Mapped[str] = mapped_column(Text, nullable=False)
    variants: Mapped[list[str]] = mapped_column(_J, nullable=False, default=list)
    freq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window: Mapped[str] = mapped_column(String(16), nullable=False, default=d.SCAN_WINDOW)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    compare: Mapped[dict[str, Any] | None] = mapped_column(_J, nullable=True)
    draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    hook_kind: Mapped[str | None] = mapped_column(String(8), nullable=True)
    hook_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_entry_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("faq_entry.id"), nullable=True
    )  # 入库回写锚（端点 3 携 source_candidate_id 登记进链、审核发布事务内落 published）
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)

    def hook(self) -> d.Hook | None:
        if self.hook_kind and self.hook_name:
            return d.Hook(kind=self.hook_kind, name=self.hook_name)
        return None


class ScanTaskRow(Base):
    """faq_scan_task——扫库任务（全局单例重入；running→done 双态，99 §1.5/R4）。"""

    __tablename__ = "faq_scan_task"
    __table_args__ = (
        CheckConstraint("status IN ('running','done')", name="ck_faq_scan_task_status"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # scan-<MMDD>
    status: Mapped[str] = mapped_column(String(8), nullable=False, default="running")
    new_cluster_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_clusters: Mapped[list[dict[str, Any]]] = mapped_column(_J, nullable=False, default=list)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


# ---------- 仓储（服务编排层只见这些类；SQL 细节不漏出） ----------


class EntryStore:
    """faq_entry ＋ faq_similar_question 仓储（条目与相似问同一聚合读写）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def all_entries(self, session: AsyncSession | None = None) -> list[EntryRow]:
        """全量条目（创建时间正序——合同排序；服务层筛选/关键词现算）。"""
        stmt = select(EntryRow).order_by(EntryRow.created_at.asc(), EntryRow.id.asc())
        if session is not None:
            return list((await session.execute(stmt)).scalars())
        async with self._db.readonly() as s:
            return list((await s.execute(stmt)).scalars())

    async def get(self, entry_id: str, session: AsyncSession | None = None) -> EntryRow | None:
        if session is not None:
            return await session.get(EntryRow, entry_id)
        async with self._db.session() as s:
            return await s.get(EntryRow, entry_id)

    async def sims_of(
        self, entry_id: str, session: AsyncSession | None = None
    ) -> list[SimilarRow]:
        stmt = select(SimilarRow).where(SimilarRow.entry_id == entry_id).order_by(SimilarRow.id)
        if session is not None:
            return list((await session.execute(stmt)).scalars())
        async with self._db.readonly() as s:
            return list((await s.execute(stmt)).scalars())

    async def all_sims(self, session: AsyncSession | None = None) -> list[SimilarRow]:
        stmt = select(SimilarRow).order_by(SimilarRow.id)
        if session is not None:
            return list((await session.execute(stmt)).scalars())
        async with self._db.readonly() as s:
            return list((await s.execute(stmt)).scalars())

    async def next_sim_id(self, session: AsyncSession) -> str:
        rows = (await session.execute(select(SimilarRow.id))).scalars().all()
        return d.new_sim_id(list(rows))

    async def bump_version(self, entry: EntryRow, session: AsyncSession) -> None:
        entry.version += 1
        entry.updated_at = now()

    async def insert_entry(self, entry: EntryRow, session: AsyncSession) -> None:
        session.add(entry)
        await session.flush()

    async def insert_sim(self, sim: SimilarRow, session: AsyncSession) -> None:
        session.add(sim)
        await session.flush()

    async def delete_sim(self, sim_id: str, entry_id: str, session: AsyncSession) -> None:
        await session.execute(
            delete(SimilarRow).where(SimilarRow.id == sim_id, SimilarRow.entry_id == entry_id)
        )

    async def delete_entry(self, entry_id: str, session: AsyncSession) -> None:
        await session.execute(delete(SimilarRow).where(SimilarRow.entry_id == entry_id))
        await session.execute(delete(EntryRow).where(EntryRow.id == entry_id))

    async def next_entry_id(self, session: AsyncSession) -> str:
        rows = (await session.execute(select(EntryRow.id))).scalars().all()
        return d.new_entry_id(list(rows))


class CandidateStore:
    """faq_candidate 仓储。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def all(self, session: AsyncSession | None = None) -> list[CandidateRow]:
        """全量候选（频次倒序——服务端排序合同；id 升序破并列）。"""
        stmt = select(CandidateRow).order_by(CandidateRow.freq.desc(), CandidateRow.id.asc())
        if session is not None:
            return list((await session.execute(stmt)).scalars())
        async with self._db.readonly() as s:
            return list((await s.execute(stmt)).scalars())

    async def get(self, cid: str, session: AsyncSession | None = None) -> CandidateRow | None:
        if session is not None:
            return await session.get(CandidateRow, cid)
        async with self._db.session() as s:
            return await s.get(CandidateRow, cid)

    async def insert(self, row: CandidateRow, session: AsyncSession) -> None:
        session.add(row)
        await session.flush()

    async def insert_detached(self, row: CandidateRow) -> None:
        async with self._db.session() as session:
            session.add(row)
            await session.flush()

    async def clear(self, session: AsyncSession) -> None:
        """清空候选（本票导入 replace 不级联清候选——留作死链无害，注记见 service）。"""
        await session.execute(delete(CandidateRow))

    async def by_source_entry(self, entry_id: str, session: AsyncSession) -> list[CandidateRow]:
        stmt = select(CandidateRow).where(CandidateRow.source_entry_id == entry_id)
        return list((await session.execute(stmt)).scalars())

    async def count(self) -> int:
        async with self._db.readonly() as session:
            return int(await session.scalar(select(func.count()).select_from(CandidateRow)) or 0)


class ScanTaskStore:
    """faq_scan_task 仓储（全局单例重入判据源）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def get(self, task_id: str) -> ScanTaskRow | None:
        async with self._db.readonly() as session:
            return await session.get(ScanTaskRow, task_id)

    async def insert(self, row: ScanTaskRow) -> None:
        async with self._db.session() as session:
            session.add(row)
            await session.flush()

    async def save(self, row: ScanTaskRow) -> None:
        async with self._db.session() as session:
            await session.merge(row)
            await session.flush()

    async def running(self) -> ScanTaskRow | None:
        async with self._db.readonly() as session:
            row = await session.scalar(
                select(ScanTaskRow).where(ScanTaskRow.status == "running").limit(1)
            )
            return row

    async def latest_done(self) -> ScanTaskRow | None:
        async with self._db.readonly() as session:
            row = await session.scalar(
                select(ScanTaskRow)
                .where(ScanTaskRow.status == "done")
                .order_by(ScanTaskRow.finished_at.desc(), ScanTaskRow.id.desc())
                .limit(1)
            )
            return row

    async def all_ids(self) -> list[str]:
        async with self._db.readonly() as session:
            return list((await session.execute(select(ScanTaskRow.id))).scalars())


# ---------- 建表与演示种子 ----------


async def ensure_faq_tables(engine: AsyncEngine) -> None:
    """建 faq 四表（幂等 checkfirst，P0-04 惯例）——与 Alembic 0007 并行存活。"""
    for model in (EntryRow, SimilarRow, CandidateRow, ScanTaskRow):
        table = cast(Table, model.__table__)
        async with engine.begin() as conn:
            await conn.run_sync(table.create, checkfirst=True)


# 演示种子（合同端点 1/9 DTO 逐条注源照抄——faq-1…faq-9 问答与 c1…c4 候选；
# freq/相似度等无设定书直锚的演示值如实标注；种子直接发布——九条不进待审核）。
_SEED_ENTRIES: tuple[tuple[str, str, str, str, list[str], str, bool], ...] = (
    # (id, question, answer, status, similar_questions, hook, is_negative)
    ("faq-1", "产量完成率怎么算？",
     "Σ实际产油 ÷ Σ计划配产 × 100%（按月、按区块或油田；负责人：开发室）",
     "serve", ["「月度完成率口径」（主任常问）"], "", False),
    ("faq-2", "完成率公式是什么？",
     "Σ实际产油 ÷ Σ计划配产 × 100%（与上一条同义，待合并）",
     "serve", [], "", False),
    ("faq-3", '"躺井"是什么意思？',
     "停产待检泵，作业区口语（限作业区语境；Owner：采油工艺所）",
     "serve", ["「躺井啥意思」"], "", False),
    ("faq-4", "N-02 井是什么时候投产的？", "2019-06-15 投产。", "serve", [], "", False),
    ("faq-5", "渤中区块的原油密度按多少折算？",
     "0.89 t/m³；吨↔方换算＝质量÷密度（渤南 0.86 / 渤西 0.91）。",
     "serve", [], "", False),
    ("faq-6", "N-11 井现在什么状态？", "停产：2026-08-30 起检泵。", "serve", [], "", False),
    ("faq-7", "递减增油怎么算？",
     "按「递减增油」口径模板计算；多井受效时按劈分系数（Σ=1）分摊。",
     "serve", [], "", False),
    ("faq-8", '"老完成率"是什么口径？',
     '旧口径条目，已随口径改版停用——"老完成率"已登记为禁用词，现行口径见「产量完成率怎么算」。',
     "disabled", [], "", False),
    ("faq-9", "帮我预测明年油价",
     '（负例：不回答。库里登记为"不该答的问题"）',
     "negative", ["「油价预测」"], "", True),
)

_SeedCand = tuple[str, str, list[str], int, str, dict[str, Any] | None, str | None]
_SEED_CANDIDATES: tuple[_SeedCand, ...] = (
    # (id, question, variants, freq, status, compare, draft)——合同端点 9 四簇演示种子
    ("c1", "产量完成率咋算的",
     ["「完成率咋算的」", "「完成率怎么计算」"], 23, "pending", None, None),
    ("c2", "自然递减率怎么算", ["「递减率公式」"], 11, "compared",
     {"verdict": "ok", "dup_question": None, "similarity": None,
      "onto_hit": "指标卡 · 自然递减率",
      "hint": "向量比对：与既有问答无重复。本体命中：指标卡 · 自然递减率。"}, None),
    ("c3", "时率是什么意思", [], 6, "pending", None, None),
    ("c4", "N-02 的完井方式是啥", ["「完井方式是啥」"], 15, "pending", None, None),
)


async def seed_demo_if_empty(engine: AsyncEngine) -> None:
    """演示种子装载（幂等：faq_entry 非空即跳过）——九条问答＋四簇候选。

    种子直接发布（合同：九条种子不进待审核）；候选 last_hint 以独立 seed 行
    承载会引入伪任务行，故落 faq_scan_task 空表＋页面 last_hint 由最近 done
    任务派生——种子态 scan.last_hint 为 null（差异登记：合同 DTO 示例为演示
    扫库后的状态快照，种子库取"未扫库"初态，如实登记）。
    """
    async with engine.begin() as conn:
        exists = (
            await conn.execute(select(func.count()).select_from(EntryRow))
        ).scalar()
        if int(exists or 0) > 0:
            return
        used_sim_ids: list[str] = []  # sq-<n> 全库连续（demo 族 sq-101 起）
        for eid, q, a, status, sims, _hook, neg in _SEED_ENTRIES:
            await conn.execute(
                insert(EntryRow).values(
                    id=eid,
                    question=q,
                    question_norm=d.normalize_text(q),
                    norm_hash=d.norm_hash(q),
                    answer=a,
                    status=status,
                    is_negative=neg,
                    hook_kind=None,
                    hook_name=None,
                    version=1,
                    maintainer="小李",
                )
            )
            for text in sims:
                sim_id = d.new_sim_id(used_sim_ids)
                used_sim_ids.append(sim_id)
                await conn.execute(
                    insert(SimilarRow).values(
                        id=sim_id,
                        entry_id=eid,
                        text=text,
                        text_norm=d.normalize_text(text),
                    )
                )
        for cid, q, variants, freq, status, compare, draft in _SEED_CANDIDATES:
            await conn.execute(
                insert(CandidateRow).values(
                    id=cid,
                    question=q,
                    variants=variants,
                    freq=freq,
                    window=d.SCAN_WINDOW,
                    status=status,
                    compare=compare,
                    draft=draft,
                    hook_kind=None,
                    hook_name=None,
                )
            )
