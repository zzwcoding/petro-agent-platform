"""检查点 saver 组合（本块专责）——LangGraph PG saver 实现，**组合** `persistence` 的框架无关行级口。

模块卡职责行逐字（`specs/modules.md` `## orchestration`）：「编排与执行——图装配与路由、命令受理与
执行器、挂起恢复、**检查点 saver 组合**（LangGraph PG saver 实现——组合 `persistence` 的框架无关行
级口，不直连表）」；`specs/modules.md` `## persistence` 卡注逐字：「① **框架类型不进本块**——
`langgraph` 的 PG saver（`BaseCheckpointSaver` 实现，需框架类型）归 `## orchestration`……**本块出
框架无关的检查点三表行级读写口**，编排块 saver **组合本口、不直连表**」。故本模块是**唯一**允许出现
`BaseCheckpointSaver` 一族的落点（边界闸 **R5b**），且**零表级直连符号**（表主人＝`persistence`）。

三处纪律（逐条对读 -a/-b 登记的接缝）：

1. **组合而非复制**：读行／写行／读通道值／读 task 级写行／删线程五件事**全部**经 `persistence` 的
   五个行级口（`put_checkpoint_rows`／`checkpoint_rows`／`checkpoint_blobs`／`checkpoint_writes`／
   `delete_thread`）；本模块**不 import** `persistence.tables` 的表名／行操作，不出现任何 DB driver
   （裸 `sqlalchemy`／`asyncpg`／`psycopg`）——行级口是唯一的表接触面（`specs/persistence.md` 接口
   定义节：「编排块的 LangGraph saver **组合它、不直连表**」）。
2. **表前缀隔离**：saver 的行不落新表——它们落在 `persistence` 的 `agent_v2_checkpoint*` 三表里
   （簿记前缀 `agent_v2_*`，与 V1 表共存隔离；`specs/agent-loop.md:219` 依赖与风险行）。
3. **载荷＝本模块自有的不透明体**：`CheckpointRow.kind` 列在本块的行上＝serde 格式标签；`checkpoint`
   列＝「检查点体 ＋ 框架元数据」的 serde 体（本模块自解码）；`metadata` 列＝`persistence` 的
   **通道版本机读映射**（`encode_metadata`）——通道值行按 `(thread_id, ns, channel, version)` 定键，
   故 `checkpoint_blobs` 读口对本块的行走同一条解析路径（`specs/persistence.md` 接口定义节注：
   「其它 `kind` 的行＝saver 自带的不透明体（本块不解读）」）。

**与执行器状态快照行的分工**（同一张表、互不混淆）：执行器的收口快照行以
`persistence.CHECKPOINT_KIND_STATE`（`kind="state"`）落，是 `RunStore.load` 的恢复载体；本模块的行
`kind` 恒为 serde 标签（非 `"state"`）——两族行以 `kind` 列区分，读面各取各的（本模块只取非 `"state"`
族）。
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping, Sequence
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
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from appv2.runtimev2.persistence import (
    CHECKPOINT_KIND_STATE,
    CheckpointBlobRow,
    CheckpointRow,
    CheckpointWriteRow,
    checkpoint_blobs,
    checkpoint_rows,
    checkpoint_writes,
    delete_thread,
    encode_metadata,
    put_checkpoint_rows,
)
from appv2.runtimev2.state import Budget

SERDE_EMPTY_TAG = "empty"  # 空通道值的 serde 占位标签（先例＝recon/J 三表事实）

# 通道值落库的**显式白名单**：`RunState` 字段值只含 JSON 原语，唯一例外＝`budget`（`state` 侧的
# 冻结 dataclass，形状真源为 `Budget`）。显式列举＝不靠 serde 的「宽容回退」（未来版本默认封禁未登记
# 类型）；新增非原语状态字段必须同批入列（同 `persistence` 黑匣子白名单纪律）。
SERDE_ALLOWED_MODULES: tuple[type, ...] = (Budget,)


class PgCheckpointer(BaseCheckpointSaver[str]):
    """LangGraph PG saver（框架无关行级口组合件）——本块内私有件，不出口本包根。

    `thread_id` ＝ `run_id`（一 run 一线程）；`ns` 取配置里的 `checkpoint_ns`（缺省空串）。框架类型
    （`Checkpoint`／`CheckpointMetadata`／`CheckpointTuple`）只在本模块签名上出现——它们**不出本模块**
    （`specs/agent-loop.md:71` 逐字：「LangGraph（含 `langchain*`）**不得渗漏出本模块**」）。
    """

    def __init__(self, *, serde: Any = None) -> None:
        super().__init__(
            serde=(
                serde
                if serde is not None
                else JsonPlusSerializer(allowed_msgpack_modules=SERDE_ALLOWED_MODULES)
            )
        )

    # ── 读面 ────────────────────────────────────────────────────────────────

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """取检查点元组（最新一条，或 `config` 指定的 `checkpoint_id`）。

        通道值走 `checkpoint_blobs`（该行的通道版本映射逐键取）；task 级写行走 `checkpoint_writes`
        （按 `(task_id, idx)` 升序——装配先例 `recon/J` aget_tuple）。
        """
        thread_id, ns = _thread_and_ns(config)
        row = self._row(thread_id, ns, get_checkpoint_id(config))
        if row is None:
            return None
        body, metadata = self._body_of(row)
        blobs = {
            blob.channel: self._loads(blob.kind, blob.blob)
            for blob in checkpoint_blobs(thread_id, row.checkpoint_id)
            if blob.kind != SERDE_EMPTY_TAG
        }
        pending = [
            (write.task_id, write.channel, self._loads(write.kind, write.blob))
            for write in sorted(
                checkpoint_writes(thread_id, row.checkpoint_id),
                key=lambda write: (write.task_id, write.idx),
            )
        ]
        parent = row.parent_checkpoint_id
        return CheckpointTuple(
            config=(
                config if get_checkpoint_id(config) else _config(thread_id, ns, row.checkpoint_id)
            ),
            checkpoint=cast(Checkpoint, {**body, "channel_values": blobs}),
            metadata=cast(CheckpointMetadata, metadata),
            pending_writes=pending,
            parent_config=_config(thread_id, ns, parent) if parent else None,
        )

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """按线程列出检查点（`checkpoint_id` 降序；`limit` 截断）。

        `filter`／`before` 两参不承载（本块只做 thread 维度的读面——先例＝旧码骨架 saver 的
        `alist`）。
        """
        if config is None:
            return
        thread_id, ns = _thread_and_ns(config)
        if not thread_id:
            return
        for row in sorted(
            self._rows(thread_id, ns), key=lambda row: row.checkpoint_id, reverse=True
        ):
            if limit is not None and limit <= 0:
                return
            if limit is not None:
                limit -= 1
            body, metadata = self._body_of(row)
            blobs = {
                blob.channel: self._loads(blob.kind, blob.blob)
                for blob in checkpoint_blobs(thread_id, row.checkpoint_id)
                if blob.kind != SERDE_EMPTY_TAG
            }
            yield CheckpointTuple(
                config=_config(thread_id, ns, row.checkpoint_id),
                checkpoint=cast(Checkpoint, {**body, "channel_values": blobs}),
                metadata=cast(CheckpointMetadata, metadata),
                parent_config=(
                    _config(thread_id, ns, row.parent_checkpoint_id)
                    if row.parent_checkpoint_id
                    else None
                ),
            )

    # ── 写面 ────────────────────────────────────────────────────────────────

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """落一步检查点：通道值行（按新版本逐条）＋检查点行（含父指针），**一批原子提交**。"""
        thread_id, ns = _thread_and_ns(config)
        body = dict(checkpoint)
        values = cast(Mapping[str, Any], body.pop("channel_values", {})) or {}
        tag, blob = self.serde.dumps_typed(
            {
                "body": body,
                "metadata": get_checkpoint_metadata(config, metadata),
            }
        )
        rows: list[CheckpointRow | CheckpointBlobRow | CheckpointWriteRow] = []
        for channel, version in new_versions.items():
            blob_tag, blob_value = (
                self.serde.dumps_typed(values[channel])
                if channel in values
                else (SERDE_EMPTY_TAG, b"")
            )
            rows.append(
                CheckpointBlobRow(
                    thread_id=thread_id,
                    ns=ns,
                    channel=channel,
                    version=str(version),
                    kind=blob_tag,
                    blob=blob_value,
                )
            )
        rows.append(
            CheckpointRow(
                thread_id=thread_id,
                ns=ns,
                checkpoint_id=str(checkpoint["id"]),
                parent_checkpoint_id=config["configurable"].get("checkpoint_id"),
                kind=tag,
                checkpoint=blob,
                metadata=encode_metadata(
                    {
                        str(channel): str(version)
                        for channel, version in (checkpoint.get("channel_versions") or {}).items()
                    }
                ),
            )
        )
        put_checkpoint_rows(rows)
        return _config(thread_id, ns, str(checkpoint["id"]))

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """落 task 级写行（`(thread_id, ns, checkpoint_id, task_id, idx)` 定键；特殊通道取索引
        表值）。"""
        thread_id, ns = _thread_and_ns(config)
        checkpoint_id = get_checkpoint_id(config)
        if not checkpoint_id:
            return
        rows: list[CheckpointRow | CheckpointBlobRow | CheckpointWriteRow] = []
        for position, (channel, value) in enumerate(writes):
            tag, blob = self.serde.dumps_typed(value)
            rows.append(
                CheckpointWriteRow(
                    thread_id=thread_id,
                    ns=ns,
                    checkpoint_id=checkpoint_id,
                    task_id=task_id,
                    idx=WRITES_IDX_MAP.get(channel, position),
                    channel=channel,
                    kind=tag,
                    blob=blob,
                )
            )
        put_checkpoint_rows(rows)

    async def adelete_thread(self, thread_id: str) -> None:
        """删线程（三表全部行——`delete_thread` 是 `persistence` 的既定语义）。"""
        delete_thread(thread_id)

    # ── 内部位（行族区分与载荷编解码）─────────────────────────────────────────

    def _rows(self, thread_id: str, ns: str) -> list[CheckpointRow]:
        """本模块的行族（`kind != CHECKPOINT_KIND_STATE`——执行器状态快照行归 `RunStore.load`）。"""
        return [
            row
            for row in checkpoint_rows(thread_id)
            if row.ns == ns and row.kind != CHECKPOINT_KIND_STATE
        ]

    def _row(self, thread_id: str, ns: str, checkpoint_id: str | None) -> CheckpointRow | None:
        rows = self._rows(thread_id, ns)
        if checkpoint_id:
            return next((row for row in rows if row.checkpoint_id == checkpoint_id), None)
        if not rows:
            return None
        return max(rows, key=lambda row: row.checkpoint_id)

    def _body_of(self, row: CheckpointRow) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = self._loads(row.kind, row.checkpoint)
        body = payload.get("body") if isinstance(payload, Mapping) else None
        metadata = payload.get("metadata") if isinstance(payload, Mapping) else None
        return (
            dict(body) if isinstance(body, Mapping) else {},
            dict(metadata) if isinstance(metadata, Mapping) else {},
        )

    def _loads(self, tag: str, blob: bytes) -> Any:
        return self.serde.loads_typed((tag, bytes(blob)))


def _thread_and_ns(config: RunnableConfig) -> tuple[str, str]:
    configurable = config["configurable"]
    return str(configurable["thread_id"]), str(configurable.get("checkpoint_ns", ""))


def _config(thread_id: str, ns: str, checkpoint_id: str) -> RunnableConfig:
    return {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": ns,
            "checkpoint_id": checkpoint_id,
        }
    }


__all__ = ["SERDE_EMPTY_TAG", "PgCheckpointer"]
