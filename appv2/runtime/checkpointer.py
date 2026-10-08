"""runtime.checkpointer —— PgCheckpointer（langgraph BaseCheckpointSaver 的 DB 实现）。

ADR-0002/0003 落点：checkpointer 每步落 PG，挂起态跨进程恢复（resume 可达）。
官方 langgraph-checkpoint-postgres 直连 psycopg——绕开 appv2.infra.db 违 B3
（全平台唯一 DB 出口），故自写 saver：存储模型镜像官方 saver（checkpoint 行＋
channel blob 按 (thread, ns, channel, version) 去重＋task 级 write），序列化走
BaseCheckpointSaver.serde（JsonPlusSerializer），会话全部经 ConnectionManager。

ADR-0002 红线③：state schema 自有（RunState）——本类只作存储机制，不理解
状态语义；thread_id＝run_id（一 run 一线程）。
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    get_checkpoint_id,
    get_checkpoint_metadata,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from appv2.infra.db import ConnectionManager
from appv2.runtime.store import AgentV2Checkpoint, AgentV2CheckpointBlob, AgentV2CheckpointWrite


class PgCheckpointer(BaseCheckpointSaver[str]):
    """checkpoint 落库（agent_v2_checkpoint 三表；会话经 infra.db——B3 合规）。"""

    def __init__(self, db: ConnectionManager) -> None:
        super().__init__()
        self._db = db

    # ---------- 读面 ----------

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        async with self._db.session() as session:
            row = await self._latest_or_by_id(session, thread_id, checkpoint_ns, config)
            if row is None:
                return None
            checkpoint: Checkpoint = self._loads(row.type, row.checkpoint)
            blobs = await self._load_blobs(
                session, thread_id, checkpoint_ns, checkpoint["channel_versions"]
            )
            write_rows = (
                (
                    await session.execute(
                        select(AgentV2CheckpointWrite).where(
                            AgentV2CheckpointWrite.thread_id == thread_id,
                            AgentV2CheckpointWrite.checkpoint_ns == checkpoint_ns,
                            AgentV2CheckpointWrite.checkpoint_id == row.checkpoint_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
            writes = sorted(write_rows, key=lambda w: (w.task_id, w.idx))
            parent = row.parent_checkpoint_id
            return CheckpointTuple(
                config=(
                    config
                    if get_checkpoint_id(config)
                    else {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": row.checkpoint_id,
                        }
                    }
                ),
                checkpoint={**checkpoint, "channel_values": blobs},
                metadata=self._loads(row.type, row.metadata_json),
                pending_writes=[
                    (w.task_id, w.channel, self._loads(w.type, w.blob)) for w in writes
                ],
                parent_config=(
                    {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": parent,
                        }
                    }
                    if parent
                    else None
                ),
            )

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """按线程倒序列出（骨架版：thread_id 维度；metadata filter 语义不承载）。"""
        if config is None:
            return
        thread_id: str = config["configurable"].get("thread_id", "")
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        if not thread_id:
            return
        async with self._db.session() as session:
            rows = (
                (
                    await session.execute(
                        select(AgentV2Checkpoint)
                        .where(
                            AgentV2Checkpoint.thread_id == thread_id,
                            AgentV2Checkpoint.checkpoint_ns == checkpoint_ns,
                        )
                        .order_by(AgentV2Checkpoint.checkpoint_id.desc())
                    )
                )
                .scalars()
                .all()
            )
            for row in rows:
                if limit is not None and limit <= 0:
                    return
                checkpoint: Checkpoint = self._loads(row.type, row.checkpoint)
                blobs = await self._load_blobs(
                    session, thread_id, checkpoint_ns, checkpoint["channel_versions"]
                )
                if limit is not None:
                    limit -= 1
                yield CheckpointTuple(
                    config={
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": row.checkpoint_id,
                        }
                    },
                    checkpoint={**checkpoint, "channel_values": blobs},
                    metadata=self._loads(row.type, row.metadata_json),
                    parent_config=(
                        {
                            "configurable": {
                                "thread_id": thread_id,
                                "checkpoint_ns": checkpoint_ns,
                                "checkpoint_id": row.parent_checkpoint_id,
                            }
                        }
                        if row.parent_checkpoint_id
                        else None
                    ),
                )

    # ---------- 写面 ----------

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        body = dict(checkpoint)
        values = cast(dict[str, Any], body.pop("channel_values"))
        ckpt_type, ckpt_blob = self.serde.dumps_typed(body)
        # metadata 与 checkpoint 同一 serde 格式标签（JsonPlusSerializer 恒同）——
        # 行上单 type 列两用；格式分拆需求出现时再拆列（骨架版注记）。
        _meta_type, meta_blob = self.serde.dumps_typed(
            get_checkpoint_metadata(config, metadata)
        )
        async with self._db.session() as session:
            for channel, version in new_versions.items():
                blob_type, blob = (
                    self.serde.dumps_typed(values[channel])
                    if channel in values
                    else ("empty", b"")
                )
                await self._upsert_blob(
                    session, thread_id, checkpoint_ns, channel, str(version), blob_type, blob
                )
            row = await session.get(
                AgentV2Checkpoint,
                (thread_id, checkpoint_ns, checkpoint["id"]),
            )
            if row is None:
                row = AgentV2Checkpoint(
                    thread_id=thread_id,
                    checkpoint_ns=checkpoint_ns,
                    checkpoint_id=checkpoint["id"],
                )
                session.add(row)
            row.parent_checkpoint_id = config["configurable"].get("checkpoint_id")
            row.type = ckpt_type
            row.checkpoint = ckpt_blob
            row.metadata_json = meta_blob
            await session.flush()
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id: str = get_checkpoint_id(config) or ""
        if not checkpoint_id:
            return
        async with self._db.session() as session:
            for idx, (channel, value) in enumerate(writes):
                blob_type, blob = self.serde.dumps_typed(value)
                write_idx = WRITES_IDX_MAP.get(channel, idx)
                key = (thread_id, checkpoint_ns, checkpoint_id, task_id, write_idx)
                row = await session.get(AgentV2CheckpointWrite, key)
                if row is None:
                    row = AgentV2CheckpointWrite(
                        thread_id=thread_id,
                        checkpoint_ns=checkpoint_ns,
                        checkpoint_id=checkpoint_id,
                        task_id=task_id,
                        idx=write_idx,
                    )
                    session.add(row)
                row.channel = channel
                row.type = blob_type
                row.blob = blob
            await session.flush()

    async def adelete_thread(self, thread_id: str) -> None:
        async with self._db.session() as session:
            for model in (AgentV2Checkpoint, AgentV2CheckpointBlob, AgentV2CheckpointWrite):
                rows = (
                    (
                        await session.execute(
                            select(model).where(model.thread_id == thread_id)
                        )
                    )
                    .scalars()
                    .all()
                )
                for row in rows:
                    await session.delete(row)

    # ---------- 内部位 ----------

    def _loads(self, type_tag: str, blob: bytes) -> Any:
        return self.serde.loads_typed((type_tag, bytes(blob)))

    async def _latest_or_by_id(
        self, session: AsyncSession, thread_id: str, checkpoint_ns: str, config: RunnableConfig
    ) -> AgentV2Checkpoint | None:
        checkpoint_id = get_checkpoint_id(config)
        if checkpoint_id:
            return await session.get(
                AgentV2Checkpoint, (thread_id, checkpoint_ns, checkpoint_id)
            )
        rows = (
            (
                await session.execute(
                    select(AgentV2Checkpoint)
                    .where(
                        AgentV2Checkpoint.thread_id == thread_id,
                        AgentV2Checkpoint.checkpoint_ns == checkpoint_ns,
                    )
                    .order_by(AgentV2Checkpoint.checkpoint_id.desc())
                    .limit(1)
                )
            )
            .scalars()
            .all()
        )
        return rows[0] if rows else None

    async def _load_blobs(
        self,
        session: AsyncSession,
        thread_id: str,
        checkpoint_ns: str,
        versions: ChannelVersions,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for channel, version in versions.items():
            row = await session.get(
                AgentV2CheckpointBlob, (thread_id, checkpoint_ns, channel, str(version))
            )
            if row is None or row.type == "empty":
                continue
            result[channel] = self._loads(row.type, row.blob)
        return result

    async def _upsert_blob(
        self,
        session: AsyncSession,
        thread_id: str,
        checkpoint_ns: str,
        channel: str,
        version: str,
        type_tag: str,
        blob: bytes,
    ) -> None:
        row = await session.get(
            AgentV2CheckpointBlob, (thread_id, checkpoint_ns, channel, version)
        )
        if row is None:
            row = AgentV2CheckpointBlob(
                thread_id=thread_id,
                checkpoint_ns=checkpoint_ns,
                channel=channel,
                version=version,
            )
            session.add(row)
        row.type = type_tag
        row.blob = blob
