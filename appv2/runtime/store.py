"""runtime.store —— run/step/checkpoint 持久化（specs/agent-loop.md 行为约定 8）。

三组表（前缀 agent_v2_ 隔离 V1 表——票面验收「agent_v2_run/agent_v2_step 新表
迁移文件（alembic 独立版本文件，前缀隔离）」）：
- agent_v2_run：run 状态机行（running→waiting_ask→（resume）→running→
  completed/failed；answer/manifest_digest 随终态落）；
- agent_v2_step：步记录（过程态簿记：每步一行，Manifest 随模型调用步存档）；
- agent_v2_checkpoint／_blob／_write：PgCheckpointer 存储载体（langgraph
  checkpoint 机制表——state schema 自有，checkpointer 仅存储，ADR-0002 红线③）。

职责边界（V2-20 票面注记）：本文件两表＝簿记（过程态——状态机现值＋逐步留痕，
服务状态读面/回放，resume 段整体重投影）；责任账＝audit_log（谁在何时以何输入
收的口，只追加不可改写）——经 security.audit 唯一写口落（appv2/runtime/audit.py），
两账分工不互替。

B3：DB 只经 appv2.infra.db（ConnectionManager）；P0-08 前 ensure_agent_v2_tables
幂等建表（gateway/security store 同款双轨——Alembic 0022 与 ensure 同形）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from sqlalchemy import Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import Table
from sqlalchemy.types import JSON

from appv2.infra.clock import now
from appv2.infra.db import Base, ConnectionManager

_TERMINABLE: frozenset[str] = frozenset({"waiting_ask", "completed", "failed"})


class AgentV2Run(Base):
    """run 状态机行（行为约定 8 四态闭世界在 RunStore 写入口把守）。"""

    __tablename__ = "agent_v2_run"

    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(16), default="running")
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    manifest_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now)
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)


class AgentV2Step(Base):
    """步记录（过程态簿记：六类 step 各一行；manifest 随模型调用步存档）。"""

    __tablename__ = "agent_v2_step"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # 〈run_id〉:〈seq〉
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    step_type: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="ok")
    title: Mapped[str] = mapped_column(Text, default="")
    manifest: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now)


class AgentV2Checkpoint(Base):
    """checkpoint 行（thread_id＝run_id；只作存储机制——schema 自有红线③）。"""

    __tablename__ = "agent_v2_checkpoint"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    checkpoint_ns: Mapped[str] = mapped_column(String(128), primary_key=True)
    checkpoint_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_checkpoint_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    type: Mapped[str] = mapped_column(String(16))
    checkpoint: Mapped[bytes] = mapped_column()
    # P-006b·R13 工程债注记：列名 metadata_json 沿官方 saver 存储模型命名，实存
    # serde.dumps_typed 产物（类型标签＋二进制——非 JSON 文本），与 checkpoint 主列
    # 共用行上单 type 列（见 checkpointer.aput 注记）；改名需迁移文件联动小改，本拍择注记。
    metadata_json: Mapped[bytes] = mapped_column()


class AgentV2CheckpointBlob(Base):
    """channel 值 blob（按 (thread, ns, channel, version) 去重存储）。"""

    __tablename__ = "agent_v2_checkpoint_blob"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    checkpoint_ns: Mapped[str] = mapped_column(String(128), primary_key=True)
    channel: Mapped[str] = mapped_column(String(128), primary_key=True)
    version: Mapped[str] = mapped_column(String(64), primary_key=True)
    type: Mapped[str] = mapped_column(String(16))
    blob: Mapped[bytes] = mapped_column()


class AgentV2CheckpointWrite(Base):
    """中间写入（task 级——interrupt/resume 哨兵与分支写入的持久面）。"""

    __tablename__ = "agent_v2_checkpoint_write"

    thread_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    checkpoint_ns: Mapped[str] = mapped_column(String(128), primary_key=True)
    checkpoint_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idx: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(16))
    blob: Mapped[bytes] = mapped_column()


class RunStore:
    """run/step 读写的领域出口（状态机四态把守；checkpoint 行归 PgCheckpointer）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def create_run(self, *, run_id: str, question: str, actor: str) -> AgentV2Run:
        row = AgentV2Run(run_id=run_id, question=question, actor=actor, status="running")
        async with self._db.session() as session:
            session.add(row)
            await session.flush()
        return row

    async def get_run(self, run_id: str) -> AgentV2Run | None:
        async with self._db.session() as session:
            return await session.get(AgentV2Run, run_id)

    async def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        answer: str | None = None,
        error: str | None = None,
        manifest_digest: str | None = None,
    ) -> None:
        """终态/挂起态收口（状态机四态闭世界——越界拒写）。"""
        if status not in _TERMINABLE:
            raise ValueError(f"run 终态越界（waiting_ask|completed|failed）：{status!r}")
        async with self._db.session() as session:
            row = await session.get(AgentV2Run, run_id)
            if row is None:
                raise ValueError(f"run 不存在：{run_id}")
            row.status = status
            row.answer = answer
            row.error = error
            row.manifest_digest = manifest_digest
            row.updated_at = now()
            await session.flush()

    async def mark_running(self, run_id: str) -> None:
        """resume 段 running 回写（行为约定 8：waiting_ask→（resume）→running——C1）。

        挂起恢复受理段即回写（executor.execute 在 spawn 前调用）：恢复段执行期
        GET run 报 running 现值（修复前停留 waiting_ask 直至终态＝断档）。转移
        合法性把守：仅 waiting_ask→running（挂起恢复唯一入口），越界转移拒写。
        """
        async with self._db.session() as session:
            row = await session.get(AgentV2Run, run_id)
            if row is None:
                raise ValueError(f"run 不存在：{run_id}")
            if row.status != "waiting_ask":
                raise ValueError(
                    f"run 状态机越界转移（仅 waiting_ask→running）：{row.status!r}"
                )
            row.status = "running"
            row.updated_at = now()
            await session.flush()

    async def put_steps(self, run_id: str, steps: list[dict[str, Any]]) -> None:
        """步记录整体落库（幂等 upsert——resume 续跑后整体重投影）。"""
        if not steps:
            return
        async with self._db.session() as session:
            for record in steps:
                row = await session.get(AgentV2Step, f"{run_id}:{record['seq']}")
                if row is None:
                    row = AgentV2Step(id=f"{run_id}:{record['seq']}", run_id=run_id)
                    session.add(row)
                row.seq = int(record["seq"])
                row.step_type = str(record["step"])
                row.status = str(record.get("status", "ok"))
                row.title = str(record.get("title", ""))
                row.manifest = record.get("manifest")
                row.payload = record.get("payload") or None
                row.created_at = now()
            await session.flush()

    async def list_steps(self, run_id: str) -> list[AgentV2Step]:
        async with self._db.session() as session:
            rows = (
                (
                    await session.execute(
                        select(AgentV2Step)
                        .where(AgentV2Step.run_id == run_id)
                        .order_by(AgentV2Step.seq)
                    )
                )
                .scalars()
                .all()
            )
            return list(rows)

    async def count_checkpoints(self, run_id: str) -> int:
        async with self._db.session() as session:
            total = await session.scalar(
                select(func.count())
                .select_from(AgentV2Checkpoint)
                .where(AgentV2Checkpoint.thread_id == run_id)
            )
            return int(total or 0)


async def ensure_agent_v2_tables(engine: AsyncEngine) -> None:
    """幂等建表（P0-08 前票面约定：Alembic 0022 与本函数双轨同形）。"""
    for model in (
        AgentV2Run,
        AgentV2Step,
        AgentV2Checkpoint,
        AgentV2CheckpointBlob,
        AgentV2CheckpointWrite,
    ):
        table = cast(Table, model.__table__)
        async with engine.begin() as conn:
            await conn.run_sync(table.create, checkfirst=True)
