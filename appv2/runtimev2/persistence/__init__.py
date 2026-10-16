"""存储归档：运行记录、检查点（框架无关表与读写入口）、黑匣子（只追加）、审计唯一写口、引用载体。

模块卡见 `specs/modules.md` 的 `## persistence` 一节；规格与形状真源见 `specs/persistence.md`
（签名以卡为准）。包根即公开面——**卡面八类形状**（`RunRecord`／`StepRecord`／`BlackBox`／`BlobRef`／
`CheckpointRow`／`CheckpointBlobRow`／`CheckpointWriteRow`／`AuditRecord`）＋`RunStore` 八法
（`save`／`load`／`run`／`steps`／`blackbox`／`put_ref`／`read_ref`／`ensure_tables`）＋检查点三表
五个框架无关行级口（`put_checkpoint_rows`／`checkpoint_rows`／`checkpoint_blobs`／`checkpoint_writes`／
`delete_thread`）＋`audit`。

实现面（卡面之外、装配与回放所需，均带真源指针）：端口与缺省件 `Tables`／`MemoryTables`／
`configure_tables`／`current_tables`／`RowOp`（Seam＝存储入口，换载体不改调用面）；检查点载荷
编解码 `encode_state`／`decode_state`／`encode_metadata`／`decode_metadata`／`latest_state_row`
（框架无关载荷：状态快照＋通道版本机读映射——编排块 saver 组合本口、不直连表）；黑匣子回放面
`replay_channels`／`dialogue_channel`（旧记录如实空显，行为 12）；审计写口装配
`configure_audit_sink`（唯一写口＝`security.audit`，B12）；错误族 `errors`。

`load` 的返回面＝`state.RunState`（真源 `specs/state.md`）；本块只依赖 `state` 与 `infra`
（R4／R5b／R6／R7 由边界闸与人审看守）。
"""

from appv2.runtimev2.persistence.audit import (
    AuditSink,
    audit,
    configure_audit_sink,
    current_audit_sink,
)
from appv2.runtimev2.persistence.blackbox import (
    REPLAY_CHANNELS,
    dialogue_channel,
    is_v2_dialogue_entry,
    replay_channels,
)
from appv2.runtimev2.persistence.checkpoint import (
    CHECKPOINT_KIND_STATE,
    DEFAULT_NS,
    checkpoint_blobs,
    checkpoint_rows,
    checkpoint_writes,
    decode_metadata,
    decode_state,
    delete_thread,
    encode_metadata,
    encode_state,
    latest_state_row,
    put_checkpoint_rows,
)
from appv2.runtimev2.persistence.errors import (
    AlreadyArchivedError,
    AuditSinkNotConfiguredError,
    PersistenceError,
    RunNotFoundError,
    StatusTransitionError,
    StepConflictError,
    TableWriteError,
    UnknownHandleError,
)
from appv2.runtimev2.persistence.models import (
    AUDIT_ACTION_BAN_EXEMPT,
    AUDIT_ACTION_EXTABLE_APPROVED,
    AUDIT_ACTION_EXTABLE_REJECTED,
    AUDIT_ACTION_PREFIX,
    AUDIT_ACTION_REFUSED,
    AUDIT_ACTION_RUN_COMPLETED,
    AUDIT_ACTION_RUN_CREATED,
    AUDIT_ACTION_RUN_FAILED,
    AUDIT_ACTIONS,
    BLACKBOX_IDENTITY_KEYS,
    BLACKBOX_RECORD_KEYS,
    STEP_STATUS_DEFAULT,
    STEP_STATUS_FAILED,
    STEP_STATUS_KINDS,
    STEP_STATUS_OK,
    STEP_STATUS_REFUSED,
    AuditRecord,
    BlackBox,
    BlobRef,
    CheckpointBlobRow,
    CheckpointRow,
    CheckpointWriteRow,
    RunRecord,
    StepRecord,
)
from appv2.runtimev2.persistence.store import REF_HANDLE_PREFIX, RunStore
from appv2.runtimev2.persistence.tables import (
    APPEND_ONLY_TABLES,
    BOOKKEEPING_TABLE_PREFIX,
    CHECKPOINT_TABLES,
    TABLE_BLACKBOX,
    TABLE_BLOB,
    TABLE_CHECKPOINT,
    TABLE_CHECKPOINT_BLOB,
    TABLE_CHECKPOINT_WRITE,
    TABLE_OPS,
    TABLE_RUN,
    TABLE_STEP,
    TABLES,
    MemoryTables,
    RowOp,
    Tables,
    configure_tables,
    current_tables,
)

__all__ = [
    "APPEND_ONLY_TABLES",
    "AUDIT_ACTIONS",
    "AUDIT_ACTION_BAN_EXEMPT",
    "AUDIT_ACTION_EXTABLE_APPROVED",
    "AUDIT_ACTION_EXTABLE_REJECTED",
    "AUDIT_ACTION_PREFIX",
    "AUDIT_ACTION_REFUSED",
    "AUDIT_ACTION_RUN_COMPLETED",
    "AUDIT_ACTION_RUN_CREATED",
    "AUDIT_ACTION_RUN_FAILED",
    "BLACKBOX_IDENTITY_KEYS",
    "BLACKBOX_RECORD_KEYS",
    "BOOKKEEPING_TABLE_PREFIX",
    "CHECKPOINT_KIND_STATE",
    "CHECKPOINT_TABLES",
    "DEFAULT_NS",
    "REF_HANDLE_PREFIX",
    "REPLAY_CHANNELS",
    "STEP_STATUS_DEFAULT",
    "STEP_STATUS_FAILED",
    "STEP_STATUS_KINDS",
    "STEP_STATUS_OK",
    "STEP_STATUS_REFUSED",
    "TABLES",
    "TABLE_BLACKBOX",
    "TABLE_BLOB",
    "TABLE_CHECKPOINT",
    "TABLE_CHECKPOINT_BLOB",
    "TABLE_CHECKPOINT_WRITE",
    "TABLE_OPS",
    "TABLE_RUN",
    "TABLE_STEP",
    "AlreadyArchivedError",
    "AuditRecord",
    "AuditSink",
    "AuditSinkNotConfiguredError",
    "BlackBox",
    "BlobRef",
    "CheckpointBlobRow",
    "CheckpointRow",
    "CheckpointWriteRow",
    "MemoryTables",
    "PersistenceError",
    "RowOp",
    "RunNotFoundError",
    "RunRecord",
    "RunStore",
    "StatusTransitionError",
    "StepConflictError",
    "StepRecord",
    "TableWriteError",
    "Tables",
    "UnknownHandleError",
    "audit",
    "checkpoint_blobs",
    "checkpoint_rows",
    "checkpoint_writes",
    "configure_audit_sink",
    "configure_tables",
    "current_audit_sink",
    "current_tables",
    "decode_metadata",
    "decode_state",
    "delete_thread",
    "dialogue_channel",
    "encode_metadata",
    "encode_state",
    "is_v2_dialogue_entry",
    "latest_state_row",
    "put_checkpoint_rows",
    "replay_channels",
]
