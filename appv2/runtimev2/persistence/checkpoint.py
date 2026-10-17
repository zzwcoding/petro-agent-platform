"""检查点三表的框架无关行级读写口＋检查点载荷的框架无关编解码。

真源＝`specs/persistence.md` 接口定义节（五个行级口＋`CheckpointRow`／`CheckpointBlobRow`／
`CheckpointWriteRow` 三投影）与卡级澄清①（**框架类型零出现**：LangGraph 的 PG saver
`BaseCheckpointSaver` 一族归 `orchestration`，编排块 saver **组合**本口、**不直连表**
——表主人＝本块；边界闸 R5b）＋行为 12（旧检查点**回放**不抛错）。

两处列语义在本块定死（框架无关，故必须自描述）：

- `CheckpointRow.checkpoint`：`kind == CHECKPOINT_KIND_STATE` 的行＝**运行状态快照载荷**
  （`encode_state`／`decode_state`，行为 3「恢复可重放」的载体）；其它 `kind` 的行＝saver 自带的
  不透明体（本块不解读）。
- `CheckpointRow.metadata`：**通道版本机读映射**（`encode_metadata`）——blob 行按
  `(thread_id, ns, channel, version)` 定键（真源 `recon/J` 三表事实），无版本映射即无法解析
  「该检查点的通道值」；缺映射／非 JSON（v1 serde 体）→ 空映射，读回如实为空（不抛错、不猜）。

排序先例（真源 `recon/J`）：最新＝`checkpoint_id` 字符串降序首行（R-J-47）；写行＝按
`(task_id, idx)` 升序（aget_tuple 装配先例）。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, fields
from typing import Any

from appv2.runtimev2.persistence.errors import PersistenceError
from appv2.runtimev2.persistence.models import (
    CheckpointBlobRow,
    CheckpointRow,
    CheckpointWriteRow,
)
from appv2.runtimev2.persistence.tables import (
    TABLE_CHECKPOINT,
    TABLE_CHECKPOINT_BLOB,
    TABLE_CHECKPOINT_WRITE,
    RowOp,
    Tables,
    current_tables,
)
from appv2.runtimev2.state import DIALOGUE_ORIGINS, Budget, RunState

DEFAULT_NS = ""  # 默认通道域（checkpoint_ns 缺省 ""——recon/J 先例）
CHECKPOINT_KIND_STATE = "state"  # 行类型标签：运行状态快照（本块载荷）

CheckpointRowLike = CheckpointRow | CheckpointBlobRow | CheckpointWriteRow

# 元组形状态字段（V2-82a 2026-10-17 追加 `subjects`／`terms`；V2-82b 追加
# `pending_subject_options`）：JSON 无元组——快照往返会把
# 声明形退化成 list，故读入时按声明形归位（同 `budget`／`dialogue` 的字段形归一先例——
# 「读回与落盘快照逐字段相等」是恢复可重放的判据面，字段形不漂移）。
_TUPLE_STATE_FIELDS: tuple[str, ...] = ("subjects", "terms", "pending_subject_options")


def _tables(tables: Tables | None) -> Tables:
    return current_tables() if tables is None else tables


# ── 状态快照编解码（框架无关载荷；旧版本按 schema_version 如实读入——行为 12）────────


def encode_state(state: RunState) -> bytes:
    """状态快照载荷：`RunState` 全字段 JSON（`schema_version` 随 `RunState` 字段自带）。"""
    return json.dumps(asdict(state), ensure_ascii=False).encode("utf-8")


def decode_state(payload: bytes) -> RunState:
    """载荷→`RunState` **如实读入**：未知键丢弃、缺字段补缺省、`schema_version` 取读入态。

    旧版本（v1／v2 旧形）不抛错：`budget` 裸 dict 按七键转 `Budget`（缺键取缺省）；`dialogue`
    兼容字段只承接 v2 三键条目——旧条目无来源标签，**补标即伪造历史**，如实空显（行为 12）。

    载荷非 JSON／非映射（真实损坏）→ 抛错（fail-closed：不静默降级为空状态）。
    """
    raw: Any = json.loads(payload.decode("utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"检查点载荷须为状态映射，实为 {type(raw).__name__}")
    known = {field.name for field in fields(RunState)}
    kwargs: dict[str, Any] = {key: value for key, value in raw.items() if key in known}
    if isinstance(kwargs.get("budget"), dict):
        budget_keys = {field.name for field in fields(Budget)}
        kwargs["budget"] = Budget(
            **{key: value for key, value in kwargs["budget"].items() if key in budget_keys}
        )
    entries = kwargs.get("dialogue")
    if isinstance(entries, list):
        kwargs["dialogue"] = [
            entry
            for entry in entries
            if isinstance(entry, dict) and entry.get("origin") in DIALOGUE_ORIGINS
        ]
    for name in _TUPLE_STATE_FIELDS:  # V2-82a：元组形字段按声明形归位（list → tuple）
        value = kwargs.get(name)
        if isinstance(value, list):
            kwargs[name] = tuple(value)
    return RunState(**kwargs)


# ── 通道版本机读映射（metadata 列语义）────────────────────────────────────────


def encode_metadata(channel_versions: Mapping[str, str]) -> bytes:
    """通道→版本机读映射（`CheckpointRow.metadata` 列语义）：blob 行的解析凭据。"""
    return json.dumps(
        {
            "channel_versions": {
                str(channel): str(version) for channel, version in channel_versions.items()
            }
        },
        ensure_ascii=False,
    ).encode("utf-8")


def decode_metadata(metadata: bytes) -> dict[str, str]:
    """机读映射读面：非 JSON／缺键（v1 serde 体）→ 空映射，如实为空、不抛错（行为 12）。"""
    try:
        raw: Any = json.loads(metadata.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    versions = raw.get("channel_versions")
    if not isinstance(versions, dict):
        return {}
    return {str(channel): str(version) for channel, version in versions.items()}


# ── 五个行级读写口（框架无关；编排块 saver 组合它、不直连表）─────────────────────


def put_checkpoint_rows(rows: Sequence[CheckpointRowLike], *, tables: Tables | None = None) -> None:
    """批量落行（三表分行）：**全行备齐后一次原子提交**——任一行非法／未知行类型 → 一行不落
    （行为 14）。"""
    ops: list[RowOp] = []
    for row in rows:
        if isinstance(row, CheckpointRow):
            key: tuple[str, ...] = (row.thread_id, row.ns, row.checkpoint_id)
            ops.append(RowOp(TABLE_CHECKPOINT, key, _row_body(row), "put"))
        elif isinstance(row, CheckpointBlobRow):
            key = (row.thread_id, row.ns, row.channel, row.version)
            ops.append(RowOp(TABLE_CHECKPOINT_BLOB, key, _row_body(row), "put"))
        elif isinstance(row, CheckpointWriteRow):
            key = (row.thread_id, row.ns, row.checkpoint_id, row.task_id, str(row.idx))
            ops.append(RowOp(TABLE_CHECKPOINT_WRITE, key, _row_body(row), "put"))
        else:
            raise TypeError(f"检查点行类型未知（三投影之外）：{type(row).__name__}")
    if not ops:
        return
    _tables(tables).write(ops)


def checkpoint_rows(thread_id: str, *, tables: Tables | None = None) -> list[CheckpointRow]:
    """该线程全部检查点行（按 `(ns, checkpoint_id)` 升序——确定性读序）。"""
    stored = _tables(tables).scan(TABLE_CHECKPOINT, "thread_id", thread_id)
    stored.sort(key=lambda row: (str(row["ns"]), str(row["checkpoint_id"])))
    return [
        CheckpointRow(
            thread_id=str(row["thread_id"]),
            ns=str(row["ns"]),
            checkpoint_id=str(row["checkpoint_id"]),
            parent_checkpoint_id=row["parent_checkpoint_id"],
            kind=str(row["kind"]),
            checkpoint=_as_bytes(row["checkpoint"]),
            metadata=_as_bytes(row["metadata"]),
        )
        for row in stored
    ]


def checkpoint_blobs(
    thread_id: str, checkpoint_id: str, *, tables: Tables | None = None
) -> list[CheckpointBlobRow]:
    """该检查点的通道值行：按该行的通道版本映射逐键取（无映射＝无行，如实为空）。

    检查点行不存在 → 抛错（fail-closed：不留无声缺口，行为 14）。
    """
    table = _tables(tables)
    checkpoint = _row_by_id(thread_id, checkpoint_id, tables=table)
    versions = decode_metadata(checkpoint.metadata)
    blobs: list[CheckpointBlobRow] = []
    for channel, version in sorted(versions.items()):
        row = table.get(TABLE_CHECKPOINT_BLOB, (thread_id, checkpoint.ns, channel, version))
        if row is None:
            continue  # 版本行缺（未写该通道）——不入结果，如实
        blobs.append(
            CheckpointBlobRow(
                thread_id=str(row["thread_id"]),
                ns=str(row["ns"]),
                channel=str(row["channel"]),
                version=str(row["version"]),
                kind=str(row["kind"]),
                blob=_as_bytes(row["blob"]),
            )
        )
    return blobs


def checkpoint_writes(
    thread_id: str, checkpoint_id: str, *, tables: Tables | None = None
) -> list[CheckpointWriteRow]:
    """该检查点的 task 级写行（按 `(task_id, idx)` 升序——装配先例 `recon/J` aget_tuple）。"""
    stored = [
        row
        for row in _tables(tables).scan(TABLE_CHECKPOINT_WRITE, "thread_id", thread_id)
        if row["checkpoint_id"] == checkpoint_id
    ]
    stored.sort(key=lambda row: (str(row["task_id"]), int(row["idx"])))
    return [
        CheckpointWriteRow(
            thread_id=str(row["thread_id"]),
            ns=str(row["ns"]),
            checkpoint_id=str(row["checkpoint_id"]),
            task_id=str(row["task_id"]),
            idx=int(row["idx"]),
            channel=str(row["channel"]),
            kind=str(row["kind"]),
            blob=_as_bytes(row["blob"]),
        )
        for row in stored
    ]


def delete_thread(thread_id: str, *, tables: Tables | None = None) -> None:
    """删线程三表全部行（簿记与黑匣子不随线程删——`recon/J` R-J-45）；一次原子提交、幂等。"""
    table = _tables(tables)
    ops: list[RowOp] = []
    for name in (TABLE_CHECKPOINT, TABLE_CHECKPOINT_BLOB, TABLE_CHECKPOINT_WRITE):
        for key in _keys_of(table, name, thread_id):
            ops.append(RowOp(name, key, {}, "delete"))
    if not ops:
        return
    table.write(ops)


def latest_state_row(thread_id: str, *, tables: Tables | None = None) -> CheckpointRow | None:
    """该线程默认通道域下最新的一条**状态快照行**（`checkpoint_id` 降序首行——R-J-47 先例）。"""
    rows = [
        row
        for row in checkpoint_rows(thread_id, tables=tables)
        if row.ns == DEFAULT_NS and row.kind == CHECKPOINT_KIND_STATE
    ]
    if not rows:
        return None
    return max(rows, key=lambda row: row.checkpoint_id)


# ── 内部件 ──────────────────────────────────────────────────────────────────


def _row_body(row: CheckpointRowLike) -> dict[str, Any]:
    return {field.name: getattr(row, field.name) for field in fields(row)}


def _as_bytes(value: Any) -> bytes:
    return value if isinstance(value, bytes) else bytes(value)


def _row_by_id(thread_id: str, checkpoint_id: str, *, tables: Tables) -> CheckpointRow:
    for row in checkpoint_rows(thread_id, tables=tables):
        if row.checkpoint_id == checkpoint_id:
            return row
    raise PersistenceError(f"检查点行不存在：thread={thread_id!r} checkpoint={checkpoint_id!r}")


def _keys_of(tables: Tables, name: str, thread_id: str) -> list[tuple[str, ...]]:
    """该线程在该表的全部主键（扫描结果只用于定键——行体不参与）。"""
    return [_primary_key(name, row) for row in tables.scan(name, "thread_id", thread_id)]


def _primary_key(name: str, row: Mapping[str, Any]) -> tuple[str, ...]:
    if name == TABLE_CHECKPOINT:
        return (str(row["thread_id"]), str(row["ns"]), str(row["checkpoint_id"]))
    if name == TABLE_CHECKPOINT_BLOB:
        return (
            str(row["thread_id"]),
            str(row["ns"]),
            str(row["channel"]),
            str(row["version"]),
        )
    return (
        str(row["thread_id"]),
        str(row["ns"]),
        str(row["checkpoint_id"]),
        str(row["task_id"]),
        str(row["idx"]),
    )
