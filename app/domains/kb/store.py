"""domains.kb.store —— kb 域八表（99 §2.5 逐字段）与仓储。

- `kb_library` / `kb_library_config` / `kb_upload` / `kb_ingest_task` /
  `kb_report` / `kb_fragment` / `kb_fragment_version` / `kb_activity`：
  99 §2.5 逐字段（kb_issue_report 归 B2 批、kb_extract_config 归 derivatives 批）。
- `kb_fragment.embedding`＝pgvector 向量列（ADR-0003 裁决 1）——维度占位
  384 待 embedding 模型回填（99 注记待办）；sqlite 单测底座以 JSON 近似
  （非生产角色）。CREATE EXTENSION vector 由 ensure_kb_tables/迁移先行。
- `kb_upload.lib_id` 可空（差异登记：入库路由流受理时目标库未定——LLM 只
  建议、confirm 定型 routed_lib_id；直指定 lib_id 的旧流两值同落）。
- ensure_kb_tables 幂等 checkfirst（P0-04 惯例），与 Alembic 0003 并行存活
  （双轨退役拍挂后续票——P1-01 差异 10 同口径）。

边界：B3（只经 infra.db）、B14（时间只经 infra.clock）、B1（不咬框架）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
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
from sqlalchemy.types import JSON, UserDefinedType

from app.domains.kb import domain as d
from app.infra.clock import now
from app.infra.db import Base, ConnectionManager

_J = JSONB().with_variant(JSON(), "sqlite")


class PgVectorType(UserDefinedType[list[float] | None]):
    """pgvector `vector(384)` 列类型（PG 方言）；sqlite 由 with_variant(JSON) 替换。"""

    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        return f"vector({d.EMBED_DIM})"

    def bind_processor(self, dialect: Any):  # type: ignore[no-untyped-def]
        def process(value: list[float] | None) -> str | None:
            if value is None:
                return None
            return "[" + ",".join(f"{v:.6f}" for v in value) + "]"

        return process

    def result_processor(self, dialect: Any, coltype: Any):  # type: ignore[no-untyped-def]
        def process(value: str | None) -> list[float] | None:
            if value is None:
                return None
            body = value.strip().strip("[]")
            return [float(x) for x in body.split(",")] if body else []

        return process


class LibraryRow(Base):
    """kb_library——知识库（v0.3 建库批：biz_template＋status）。"""

    __tablename__ = "kb_library"
    __table_args__ = (
        CheckConstraint(
            "biz_template IN ('completion','monthly','dynamic','blank')",
            name="ck_kb_library_biz_template",
        ),
        CheckConstraint("status IN ('active','disabled')", name="ck_kb_library_status"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # lib-
    name: Mapped[str] = mapped_column(Text, nullable=False)
    biz_template: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class LibraryConfigRow(Base):
    """kb_library_config——待生效配置（两态之一：保存值≠最近入库快照）。"""

    __tablename__ = "kb_library_config"
    __table_args__ = (
        CheckConstraint("mode IN ('smart','fixed','mixed')", name="ck_kb_library_config_mode"),
    )

    lib_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("kb_library.id"), primary_key=True
    )
    semantic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    keyword: Mapped[bool] = mapped_column(Boolean, nullable=False)
    wiki: Mapped[bool] = mapped_column(Boolean, nullable=False)
    graph: Mapped[bool] = mapped_column(Boolean, nullable=False)
    mode: Mapped[str] = mapped_column(String(8), nullable=False)
    add_summary: Mapped[bool] = mapped_column(Boolean, nullable=False)
    add_questions: Mapped[bool] = mapped_column(Boolean, nullable=False)
    saved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    saved_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class UploadRow(Base):
    """kb_upload——直传受理单（两拍第一拍；路由三列＝v0.3 落库面）。"""

    __tablename__ = "kb_upload"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','confirmed','expired')", name="ck_kb_upload_status"
        ),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # up-
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    size: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), nullable=False
    )
    lib_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("kb_library.id"), nullable=True
    )
    bucket: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    suggested_topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    routed_lib_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("kb_library.id"), nullable=True
    )
    route_confirmed_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_key: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class IngestTaskRow(Base):
    """kb_ingest_task——入库任务（四态＋五步＋定型快照＋来源）。"""

    __tablename__ = "kb_ingest_task"
    __table_args__ = (
        CheckConstraint(
            "state IN ('running','done','failed','stuck')", name="ck_kb_ingest_task_state"
        ),
        CheckConstraint(
            "source IN ('上传入库','片段修正','重跑定型')", name="ck_kb_ingest_task_source"
        ),
        Index("ix_kb_ingest_task_lib_started", "lib_id", text("started_at DESC")),
        Index("ix_kb_ingest_task_source", "source"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # task-
    upload_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("kb_upload.id"), nullable=True
    )
    report_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("kb_report.id"), nullable=False
    )
    lib_id: Mapped[str] = mapped_column(String(32), ForeignKey("kb_library.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="上传入库")
    current_step: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    stop_at: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(_J, nullable=False)
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(_J, nullable=False)
    extract_snapshot: Mapped[dict[str, Any] | None] = mapped_column(_J, nullable=True)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class ReportRow(Base):
    """kb_report——报告台账（原件句柄在对象存储；status 列恒「已入库」，
    台账「入库中」标由最近任务状态读侧派生——99 CHECK 单值与 B1 端点 1 两态
    的 reconcile 口径，差异登记见票面）。"""

    __tablename__ = "kb_report"
    __table_args__ = (
        CheckConstraint("status IN ('已入库')", name="ck_kb_report_status"),
        Index("ix_kb_report_lib", "lib_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # rpt-
    lib_id: Mapped[str] = mapped_column(String(32), ForeignKey("kb_library.id"), nullable=False)
    doc: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(8), nullable=False, default="已入库")
    related_objects: Mapped[list[dict[str, str]]] = mapped_column(_J, nullable=False, default=list)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    wiki_current_version: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class FragmentRow(Base):
    """kb_fragment——片段（chunk 台账行；父块不对外寻址——F30）。"""

    __tablename__ = "kb_fragment"
    __table_args__ = (
        CheckConstraint(
            "type IN ('原文块','图片说明块','图片文字块','摘要块','问题块')",
            name="ck_kb_fragment_type",
        ),
        Index("ix_kb_fragment_report", "report_id"),
        Index("ix_kb_fragment_type", "type"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # f{n}
    report_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("kb_report.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(8), nullable=False)
    section: Mapped[str | None] = mapped_column(Text, nullable=True)
    well: Mapped[str | None] = mapped_column(Text, nullable=True)
    hit_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_parent_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        PgVectorType().with_variant(JSON(), "sqlite"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class FragmentVersionRow(Base):
    """kb_fragment_version——片段版本（v1 永存＋乐观锁）。"""

    __tablename__ = "kb_fragment_version"
    __table_args__ = (
        CheckConstraint("note IN ('原始解析','人工修正')", name="ck_kb_fragment_version_note"),
    )

    fragment_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("kb_fragment.id"), primary_key=True
    )
    v: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    context_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str] = mapped_column(String(8), nullable=False, default="原始解析")
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class ActivityRow(Base):
    """kb_activity——库活动流（F62 只读追加；写口＝kb.record_activity）。"""

    __tablename__ = "kb_activity"
    __table_args__ = (Index("ix_kb_activity_lib_time", "lib_id", text("time DESC")),)

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"), primary_key=True, autoincrement=True
    )
    lib_id: Mapped[str] = mapped_column(String(32), ForeignKey("kb_library.id"), nullable=False)
    time: Mapped[datetime] = mapped_column(nullable=False)
    who: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


KB_TABLES: tuple[type[Base], ...] = (
    LibraryRow,
    LibraryConfigRow,
    UploadRow,
    ReportRow,  # 先于 IngestTaskRow 建（FK 依赖）
    IngestTaskRow,
    FragmentRow,
    FragmentVersionRow,
    ActivityRow,
)


async def ensure_kb_tables(engine: AsyncEngine) -> None:
    """建表函数（幂等 checkfirst；PG 先 CREATE EXTENSION vector——pgvector 列前提）。"""
    async with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    for model in KB_TABLES:
        table = cast("Table", model.__table__)
        async with engine.begin() as conn:
            await conn.run_sync(table.create, checkfirst=True)


# ---------- 仓储（会话编排；语义在 service/domain） ----------


class LibraryStore:
    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def create_library_with_config(
        self,
        lib: LibraryRow,
        config: LibraryConfigRow,
        *,
        activity: tuple[str, str, str],  # (who, action, target)——建库同事务记 F62
    ) -> LibraryRow:
        async with self._db.session() as session:
            session.add(lib)
            await session.flush()  # 父行先落（无 relationship 不保证 UOW 插序）
            session.add(config)
            who, action, target = activity
            session.add(
                ActivityRow(lib_id=lib.id, time=now(), who=who, action=action, target=target)
            )
            await session.flush()
        return lib

    async def get(self, lib_id: str) -> LibraryRow | None:
        async with self._db.readonly() as session:
            return await session.get(LibraryRow, lib_id)

    async def by_name(self, name: str) -> LibraryRow | None:
        async with self._db.readonly() as session:
            rows = (await session.execute(select(LibraryRow))).scalars().all()
        for row in rows:
            if d.normalize_name(row.name) == d.normalize_name(name):
                return row
        return None

    async def all(self) -> list[LibraryRow]:
        async with self._db.readonly() as session:
            rows = (
                (await session.execute(select(LibraryRow).order_by(LibraryRow.created_at)))
                .scalars()
                .all()
            )
        return list(rows)

    async def config_of(self, lib_id: str) -> LibraryConfigRow | None:
        async with self._db.readonly() as session:
            return await session.get(LibraryConfigRow, lib_id)

    async def save_config_with_activity(
        self,
        lib_id: str,
        *,
        switches: dict[str, bool],
        mode: str,
        add_summary: bool,
        add_questions: bool,
        actor_who: str,
        activity: tuple[str, str, str],  # (who, action, target)——保存同事务记 F62
    ) -> tuple[LibraryConfigRow, ActivityRow]:
        async with self._db.session() as session:
            row = await session.get(LibraryConfigRow, lib_id)
            at = now()
            if row is None:
                row = LibraryConfigRow(
                    lib_id=lib_id,
                    semantic=switches["semantic"],
                    keyword=switches["keyword"],
                    wiki=switches["wiki"],
                    graph=switches["graph"],
                    mode=mode,
                    add_summary=add_summary,
                    add_questions=add_questions,
                    saved_at=at,
                    saved_by=actor_who,
                )
                session.add(row)
            else:
                row.semantic = switches["semantic"]
                row.keyword = switches["keyword"]
                row.wiki = switches["wiki"]
                row.graph = switches["graph"]
                row.mode = mode
                row.add_summary = add_summary
                row.add_questions = add_questions
                row.saved_at = at
                row.saved_by = actor_who
                row.updated_at = at
            who, action, target = activity
            activity_row = ActivityRow(
                lib_id=lib_id, time=at, who=who, action=action, target=target
            )
            session.add(activity_row)
            await session.flush()
            return row, activity_row

    async def set_status_with_activity(
        self, lib_id: str, status: str, *, activity: tuple[str, str, str]
    ) -> LibraryRow | None:
        """停用/启用（持久状态字段——与配置同属库管理写面、同事务记 F62）。"""
        async with self._db.session() as session:
            row = await session.get(LibraryRow, lib_id)
            if row is None:
                return None
            row.status = status
            row.updated_at = now()
            who, action, target = activity
            session.add(
                ActivityRow(lib_id=lib_id, time=now(), who=who, action=action, target=target)
            )
            await session.flush()
            return row


class UploadStore:
    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def create(self, row: UploadRow) -> UploadRow:
        async with self._db.session() as session:
            session.add(row)
            await session.flush()
        return row

    async def get(self, upload_id: str) -> UploadRow | None:
        async with self._db.readonly() as session:
            return await session.get(UploadRow, upload_id)

    async def mark_confirmed(self, upload_id: str, routed_lib_id: str, confirmed_by: str) -> None:
        async with self._db.session() as session:
            row = await session.get(UploadRow, upload_id)
            if row is None:
                return
            row.status = "confirmed"
            row.routed_lib_id = routed_lib_id
            row.route_confirmed_by = confirmed_by
            row.updated_at = now()
            await session.flush()


class ReportStore:
    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def create(self, row: ReportRow) -> ReportRow:
        async with self._db.session() as session:
            session.add(row)
            await session.flush()
        return row

    async def get(self, report_id: str) -> ReportRow | None:
        async with self._db.readonly() as session:
            return await session.get(ReportRow, report_id)

    async def all(self) -> list[ReportRow]:
        async with self._db.readonly() as session:
            rows = (
                (
                    await session.execute(
                        select(ReportRow).order_by(
                            ReportRow.created_at.desc(), ReportRow.id.desc()
                        )
                    )
                )
                .scalars()
                .all()
            )
        return list(rows)

    async def by_object_key(self, object_key: str) -> ReportRow | None:
        async with self._db.readonly() as session:
            rows = (
                (
                    await session.execute(
                        select(ReportRow).where(ReportRow.object_key == object_key)
                    )
                )
                .scalars()
                .all()
            )
        return rows[0] if rows else None


class TaskStore:
    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def create(self, row: IngestTaskRow) -> IngestTaskRow:
        async with self._db.session() as session:
            session.add(row)
            await session.flush()
        return row

    async def get(self, task_id: str) -> IngestTaskRow | None:
        async with self._db.readonly() as session:
            return await session.get(IngestTaskRow, task_id)

    async def save(self, row: IngestTaskRow) -> None:
        row.updated_at = now()
        async with self._db.session() as session:
            await session.merge(row)

    async def all(self) -> list[IngestTaskRow]:
        async with self._db.readonly() as session:
            rows = (
                (
                    await session.execute(
                        select(IngestTaskRow).order_by(
                            IngestTaskRow.started_at.desc(), IngestTaskRow.id.desc()
                        )
                    )
                )
                .scalars()
                .all()
            )
        return list(rows)

    async def latest_for_report(self, report_id: str) -> IngestTaskRow | None:
        async with self._db.readonly() as session:
            rows = (
                (
                    await session.execute(
                        select(IngestTaskRow)
                        .where(IngestTaskRow.report_id == report_id)
                        .order_by(IngestTaskRow.started_at.desc(), IngestTaskRow.id.desc())
                        .limit(1)
                    )
                )
                .scalars()
                .all()
            )
        return rows[0] if rows else None

    async def mark_stale_stuck(self, *, before: datetime, summary: str) -> int:
        """stuck 收口：running 且 updated_at 早于 before 的任务置 stuck（幂等）。"""
        async with self._db.session() as session:
            rows = (
                (
                    await session.execute(
                        select(IngestTaskRow).where(
                            IngestTaskRow.state == "running",
                            IngestTaskRow.updated_at < before,
                        )
                    )
                )
                .scalars()
                .all()
            )
            at = now()
            for row in rows:
                row.state = "stuck"
                row.reason = summary
                row.updated_at = at
            await session.flush()
            return len(rows)

    async def confirm_upload(
        self,
        upload: UploadRow,
        report: ReportRow,
        task: IngestTaskRow,
        *,
        routed_lib_id: str,
        confirmed_by: str,
        activity: tuple[str, str, str],  # (who, action, target)——受理确认同事务记 F62
    ) -> IngestTaskRow:
        """confirm 定型事务：upload 状态/routed_lib_id＋report 行＋task 行＋活动一行。"""
        async with self._db.session() as session:
            upload.status = "confirmed"
            upload.routed_lib_id = routed_lib_id
            upload.route_confirmed_by = confirmed_by
            upload.updated_at = now()
            session.add(upload)
            await session.flush()  # 父行先落：upload→report→task→activity（FK 链）
            session.add(report)
            await session.flush()
            session.add(task)
            await session.flush()
            who, action, target = activity
            session.add(
                ActivityRow(lib_id=task.lib_id, time=now(), who=who, action=action, target=target)
            )
            await session.flush()
        return task

    async def finish_with_activity(
        self, task: IngestTaskRow, *, activity: tuple[str, str, str] | None
    ) -> None:
        """终态落痕：任务行收口（done/failed/stuck）＋F62 活动一行（同事务）。"""
        async with self._db.session() as session:
            await session.merge(task)
            if activity is not None:
                who, action, target = activity
                session.add(
                    ActivityRow(
                        lib_id=task.lib_id, time=now(), who=who, action=action, target=target
                    )
                )
            await session.flush()


class FragmentStore:
    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def next_fragment_seq(self) -> int:
        """片段号全局自增（99：id（f1…）——量级演示级，count+1 取号）。"""
        async with self._db.readonly() as session:
            count = await session.scalar(select(func.count()).select_from(FragmentRow))
        return int(count or 0) + 1

    async def replace_report_fragments(
        self, report_id: str, rows: list[FragmentRow], versions: list[FragmentVersionRow]
    ) -> None:
        """整卷置换（重跑＝一次新入库——旧片段随重建被置换；修正历史保留策略
        归 P1-02b/B2 批，差异登记票面）。"""
        async with self._db.session() as session:
            old = (
                (
                    await session.execute(
                        select(FragmentRow).where(FragmentRow.report_id == report_id)
                    )
                )
                .scalars()
                .all()
            )
            for row in old:
                await session.delete(row)
            await session.flush()
            for row in rows:
                session.add(row)
            await session.flush()  # 片段行先落——版本行 FK 依赖片段
            for ver in versions:
                session.add(ver)
            await session.flush()

    async def count_by_report(self, report_id: str) -> int:
        """refs 口径（端点 1/2）：该报告非父块片段数（与 B2 同源——差异登记票面）。"""
        async with self._db.readonly() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(FragmentRow)
                .where(
                    FragmentRow.report_id == report_id,
                    FragmentRow.is_parent_only.is_(False),
                )
            )
        return int(count or 0)

    async def set_embeddings(self, pairs: list[tuple[str, list[float]]]) -> None:
        """向量半边写回（semantic 支路——索引步的物理落点）。"""
        async with self._db.session() as session:
            for fragment_id, vector in pairs:
                row = await session.get(FragmentRow, fragment_id)
                if row is not None:
                    row.embedding = vector
                    row.updated_at = now()
            await session.flush()

    async def for_report(self, report_id: str) -> list[FragmentRow]:
        async with self._db.readonly() as session:
            rows = (
                (
                    await session.execute(
                        select(FragmentRow)
                        .where(FragmentRow.report_id == report_id)
                        .order_by(FragmentRow.id)
                    )
                )
                .scalars()
                .all()
            )
        return list(rows)

    async def versions_of(self, fragment_ids: list[str]) -> dict[str, list[FragmentVersionRow]]:
        if not fragment_ids:
            return {}
        async with self._db.readonly() as session:
            rows = (
                (
                    await session.execute(
                        select(FragmentVersionRow)
                        .where(FragmentVersionRow.fragment_id.in_(fragment_ids))
                        .order_by(FragmentVersionRow.v)
                    )
                )
                .scalars()
                .all()
            )
        grouped: dict[str, list[FragmentVersionRow]] = {}
        for row in rows:
            grouped.setdefault(row.fragment_id, []).append(row)
        return grouped


class ActivityStore:
    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def append(
        self, lib_id: str, *, who: str, action: str, target: str, at: datetime | None = None
    ) -> ActivityRow:
        row = ActivityRow(
            lib_id=lib_id, time=at or now(), who=who, action=action, target=target
        )
        async with self._db.session() as session:
            session.add(row)
            await session.flush()
        return row

    async def list_by_lib(self, lib_id: str) -> list[ActivityRow]:
        async with self._db.readonly() as session:
            rows = (
                (
                    await session.execute(
                        select(ActivityRow)
                        .where(ActivityRow.lib_id == lib_id)
                        .order_by(ActivityRow.time.desc(), ActivityRow.id.desc())
                    )
                )
                .scalars()
                .all()
            )
        return list(rows)
