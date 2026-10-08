"""domains.chat.store —— chat 域骨架三表（99 §2.2 逐字段）与仓储。

- `chat_session` / `chat_message` / `chat_run`：99 §2.2 逐字段（`group` 为 SQL
  保留字——SQLAlchemy DDL 自动引号承载，DTO 零映射；产物/工具/场景三族表不属
  本票——chat_artifact_task/chat_artifact/chat_tool/chat_scenario 随其端点票落）。
- `chat_run.clarify_count` smallint CHECK 0–1＝澄清帧有界循环的存储强制
  （第二次 clarify 409——99 §2.2 合同锚原文）。
- 19 类事件帧不落库（99 §1.5「SSE 事件缓冲不落库」裁决——帧是流内最小单位非
  持久业务实体；`chat_run.verdict/pending_interrupt` jsonb 承载裁决与挂起态）。
- `ensure_chat_tables` 幂等 checkfirst（P0-04 惯例），与 Alembic 0009 并行存活
  （双轨退役拍挂 P1-11 收官票——P1-01 差异 10 同口径）。

边界：B3（只经 infra.db）、B14（时间只经 infra.clock）、B1（不咬框架）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import (
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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.infra.clock import now
from app.infra.db import Base, ConnectionManager

_J = JSONB().with_variant(JSON(), "sqlite")

# chat_run.status 六值（99 §2.2 CHECK 冻结——interrupt 双挂起态为双入口保留）。
RUN_STATUSES = ("running", "interrupt_clarify", "interrupt_approval", "done", "failed", "cancelled")


class ChatSessionRow(Base):
    """chat_session——服务端持久会话（换设备、断线重连不丢；A1 端点 2）。"""

    __tablename__ = "chat_session"
    __table_args__ = (Index("ix_chat_session_user_updated", "user_id", "updated_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # sess-<短码>
    title: Mapped[str] = mapped_column(Text, nullable=False)
    group: Mapped[str | None] = mapped_column(Text, nullable=True)  # SQL 保留字——DDL 引号
    scenario_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_id: Mapped[str] = mapped_column(String(32), nullable=False)  # who 解析归属（技术列）
    updated_at: Mapped[datetime] = mapped_column(nullable=False)  # 排序键（99 §2.2）
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class ChatMessageRow(Base):
    """chat_message——会话消息（answer 与 SSE answer 帧同形 DTO，一份两处消费）。"""

    __tablename__ = "chat_message"
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant')", name="ck_chat_message_role"),
        Index("uq_chat_message_session_seq", "session_id", "seq", unique=True),
        Index("ix_chat_message_run", "run_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # msg-<短码>
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("chat_session.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    answer: Mapped[dict[str, Any] | None] = mapped_column(_J, nullable=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class ChatRunRow(Base):
    """chat_run——一次问答运行（聚合根：状态＋interrupt＋记账投影锚；A1 端点 4/5）。

    `id` 与 D5 run_id 同标识（99 §2.2「一 run 两视图」）；clarify_count CHECK 0–1
    ＝澄清帧最多弹一次（第二次 409——有界循环的存储强制）。
    """

    __tablename__ = "chat_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running','interrupt_clarify','interrupt_approval',"
            "'done','failed','cancelled')",
            name="ck_chat_run_status",
        ),
        CheckConstraint("clarify_count >= 0 AND clarify_count <= 1", name="ck_chat_run_clarify"),
        Index("ix_chat_run_session", "session_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # run-<短码>
    session_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("chat_session.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="running")
    verdict: Mapped[dict[str, Any] | None] = mapped_column(_J, nullable=True)
    pending_interrupt: Mapped[dict[str, Any] | None] = mapped_column(_J, nullable=True)
    pending_approval_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # L-05 pinned_plan 持久化载体（机制 11——已验证 QueryPlan 的 dict 投影，
    # domain.plan_pinned_payload 单源序列化；NULL＝本 run 未走 LLM 生效路）。
    # 恢复消费前必经 revalidate_pinned_plan 确定性复验——不盲信持久化载荷。
    plan_pinned: Mapped[dict[str, Any] | None] = mapped_column(_J, nullable=True)
    clarify_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


async def ensure_chat_tables(engine: AsyncEngine) -> None:
    """建表函数（幂等 checkfirst，P0-04 惯例）——与 Alembic 并行存活，切换迁移
    属收官票（P0-08 票面惯例）。"""
    for table in (ChatSessionRow.__table__, ChatMessageRow.__table__, ChatRunRow.__table__):
        async with engine.begin() as conn:
            await conn.run_sync(cast(Table, table).create, checkfirst=True)


class ChatStore:
    """chat 仓储：会话保障／消息追加／运行生命周期（编排见 service）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    # ---------- 会话（A1 端点 4：session_id 缺省＝新建） ----------

    async def ensure_session(
        self, session_id: str | None, *, user_id: str, title: str
    ) -> ChatSessionRow:
        """取既有会话或新建（title＝首问；scenario/group 骨架期空——场景注册表
        端点 1 随其票落）。"""
        async with self._db.session() as session:
            if session_id:
                row = await session.get(ChatSessionRow, session_id)
                if row is not None:
                    return row
            new_id = session_id or await self._next_id(session, ChatSessionRow, "sess")
            row = ChatSessionRow(
                id=new_id, title=title, group=None, scenario_id=None,
                user_id=user_id, updated_at=now(), created_at=now(),
            )
            session.add(row)
            await session.flush()
            return row

    async def touch_session(self, session_id: str) -> None:
        """会话 updated_at 推进（排序键——端点 2 倒序依据）。"""
        async with self._db.session() as session:
            row = await session.get(ChatSessionRow, session_id)
            if row is not None:
                row.updated_at = now()
                await session.flush()

    async def list_sessions(self, *, user_id: str, limit: int = 100) -> list[ChatSessionRow]:
        """会话历史读口（A1 端点 2——当前身份的会话，updated_at 倒序）。"""
        async with self._db.readonly() as session:
            rows = (
                await session.execute(
                    select(ChatSessionRow)
                    .where(ChatSessionRow.user_id == user_id)
                    .order_by(ChatSessionRow.updated_at.desc())
                    .limit(limit)
                )
            ).scalars().all()
        return list(rows)

    # ---------- 消息（会话历史写口——B3 扫库料源缝的落库面） ----------

    async def next_seq(self, session_id: str) -> int:
        async with self._db.readonly() as session:
            value = await session.scalar(
                select(func.max(ChatMessageRow.seq)).where(ChatMessageRow.session_id == session_id)
            )
        return int(value or 0) + 1

    async def append_message(
        self,
        session_id: str,
        *,
        role: str,
        text: str,
        run_id: str | None = None,
        answer: dict[str, Any] | None = None,
    ) -> ChatMessageRow:
        row = ChatMessageRow(
            id=await self._fresh_id(ChatMessageRow, "msg"),
            session_id=session_id,
            role=role,
            text=text,
            run_id=run_id,
            answer=answer,
            seq=await self.next_seq(session_id),
            created_at=now(),
            updated_at=now(),
        )
        async with self._db.session() as session:
            session.add(row)
            await session.flush()
        return row

    async def messages_of_run(self, run_id: str) -> list[ChatMessageRow]:
        async with self._db.readonly() as session:
            rows = (
                await session.execute(
                    select(ChatMessageRow)
                    .where(ChatMessageRow.run_id == run_id)
                    .order_by(ChatMessageRow.seq)
                )
            ).scalars().all()
        return list(rows)

    async def get_session(self, session_id: str) -> ChatSessionRow | None:
        """会话行读口（A1 端点 3 归属校验面）。"""
        async with self._db.readonly() as session:
            return await session.get(ChatSessionRow, session_id)

    async def list_messages(self, session_id: str) -> list[ChatMessageRow]:
        """会话消息读口（A1 端点 3——seq 升序即回放序）。"""
        async with self._db.readonly() as session:
            rows = (
                await session.execute(
                    select(ChatMessageRow)
                    .where(ChatMessageRow.session_id == session_id)
                    .order_by(ChatMessageRow.seq)
                )
            ).scalars().all()
        return list(rows)

    # ---------- 运行（A1 端点 4/5 状态机） ----------

    async def create_run(self, session_id: str, *, run_id: str | None = None) -> ChatRunRow:
        row = ChatRunRow(
            id=run_id or await self._fresh_id(ChatRunRow, "run"),
            session_id=session_id,
            status="running",
            clarify_count=0,
            started_at=now(),
            created_at=now(),
            updated_at=now(),
        )
        async with self._db.session() as session:
            session.add(row)
            await session.flush()
        return row

    async def get_run(self, run_id: str) -> ChatRunRow | None:
        async with self._db.readonly() as session:
            return await session.get(ChatRunRow, run_id)

    async def save_run(self, row: ChatRunRow) -> None:
        """运行行回写（状态/verdict/pending_interrupt/clarify_count/finished_at）。"""
        row.updated_at = now()
        async with self._db.session() as session:
            await session.merge(row)
            await session.flush()

    # ---------- 会话料源读口（B3 扫库消费——faq session_loader 注入位） ----------

    async def recent_qa_pairs(self, *, limit: int = 50) -> list[dict[str, str]]:
        """A1 历史问答对（[{question, answer}]——B3 挖掘管线料源；done 运行的
        user 问＋assistant 答配对，最近优先）。answer 帧 kind=text 取 text，
        其余 kind 序列化摘要（料源只做人话消费）。"""
        async with self._db.readonly() as session:
            runs = (
                await session.execute(
                    select(ChatRunRow)
                    .where(ChatRunRow.status == "done")
                    .order_by(ChatRunRow.started_at.desc())
                    .limit(limit)
                )
            ).scalars().all()
            if not runs:
                return []
            run_ids = [r.id for r in runs]
            messages = (
                await session.execute(
                    select(ChatMessageRow)
                    .where(ChatMessageRow.run_id.in_(run_ids))
                    .order_by(ChatMessageRow.seq)
                )
            ).scalars().all()
        by_run: dict[str, dict[str, str]] = {}
        order: list[str] = []
        for message in messages:
            pair = by_run.setdefault(message.run_id or "", {})
            if message.run_id not in order:
                order.append(message.run_id or "")
            if message.role == "user":
                pair["question"] = message.text
            elif message.answer is not None:
                pair["answer"] = _answer_text(message.answer)
        return [
            by_run[run_id]
            for run_id in reversed(order)
            if run_id in by_run and by_run[run_id].get("question") and by_run[run_id].get("answer")
        ][:limit]

    # ---------- id 发生器（机器短 id 族——00 §1.5 sess-/msg-/run-） ----------

    @staticmethod
    async def _next_id(session: AsyncSession, model: type[Any], prefix: str) -> str:
        return await _fresh_id_in(session, model, prefix)

    async def _fresh_id(self, model: type[Any], prefix: str) -> str:
        async with self._db.readonly() as session:
            return await _fresh_id_in(session, model, prefix)


def _answer_text(answer: dict[str, Any]) -> str:
    """answer 帧 → 人话料源（kind=text 取正文；alert 取 text；表卡取 note/title）。"""
    kind = str(answer.get("kind", ""))
    if kind in ("text", "alert"):
        return str(answer.get("text", ""))
    if kind == "table":
        return str(answer.get("note") or answer.get("title") or "")
    return str(answer.get("text") or answer.get("notice") or "")


async def _fresh_id_in(session: AsyncSession, model: type[Any], prefix: str) -> str:
    """短 id 发生（<prefix>-<六位十六进制>；撞库重掷——演示量级足够）。"""
    while True:
        candidate = f"{prefix}-{uuid4().hex[:6]}"
        existing = await session.get(model, candidate)
        if existing is None:
            return candidate
