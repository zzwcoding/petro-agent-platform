"""persistence 的落盘入口与读回入口（`RunStore`）：一次运行的落盘与读回真源。

真源＝`specs/persistence.md` 接口定义节（签名以 `specs/modules.md` `## persistence` 卡为准）＋
行为 1（三类落盘语义）／行为 2（状态机把守）／行为 3（恢复可重放）／行为 4（黑匣子首写为准）／
行为 8（`payload` 原样保真）／行为 9（`run_id` 全盖章）／行为 10（引用载体可寻址）／行为 11
（黑匣子键白名单闭世界）／行为 12（旧记录如实读入）。

边界纪律：写面只有簿记表（`tables.TABLES`，前缀 `agent_v2_*`；INV-2 业务数据零写入）；时间列经
`infra.clock`（B14，唯二时间出口之一）；本模块零框架类型（R5b）、零引擎直引（R6）、零模型出口（R7）、
不 import 包内其它块（只依赖 `state`）。存储不可用／写失败 → 上抛（fail-closed，行为 14）——
本块只把错误如实抛出，不产帧、不吞错、不半写。
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import asdict
from datetime import datetime
from typing import Any

from appv2.infra import clock as infra_clock
from appv2.runtimev2.persistence.checkpoint import decode_state, latest_state_row
from appv2.runtimev2.persistence.errors import (
    AlreadyArchivedError,
    BlackBoxKeyOutOfWorldError,
    PersistenceError,
    RunNotFoundError,
    StatusTransitionError,
    StepConflictError,
    UnknownHandleError,
)
from appv2.runtimev2.persistence.models import (
    BLACKBOX_ALLOWED_KEYS,
    STEP_STATUS_KINDS,
    BlackBox,
    BlobRef,
    RunRecord,
    StepRecord,
)
from appv2.runtimev2.persistence.tables import (
    TABLE_BLACKBOX,
    TABLE_BLOB,
    TABLE_RUN,
    TABLE_STEP,
    RowOp,
    Tables,
    current_tables,
)
from appv2.runtimev2.state import (
    RUN_RUNNING,
    RUN_STATUS_KINDS,
    RUN_WAITING_ASK,
    STEP_KINDS,
    RunState,
)

REF_HANDLE_PREFIX = "blob-"  # 可寻址 handle＝内容定址（同原文恒同 handle）
_SHA256_CHARS = 64

# 步记录「同键幂等」的等价面（行为 1②）：语义列全参与，**末次落盘时间不参与**——重复落盘刷新
# 落盘时间但不产生第二行（列语义真源：该记录末次落盘时间，见规格「依赖与风险」4）。
_STEP_SIGNATURE_FIELDS = ("run_id", "seq", "step", "status", "title", "manifest", "payload")


class RunStore:
    """落盘入口／读回入口／引用载体／幂等建表（Seam：换载体不改调用面）。"""

    def __init__(
        self,
        tables: Tables | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._tables: Tables = current_tables() if tables is None else tables
        self._clock: Callable[[], datetime] = infra_clock.now if clock is None else clock

    # ── 建表 ────────────────────────────────────────────────────────────────

    def ensure_tables(self) -> None:
        """幂等建表（缺省件＝簿记表清单齐备；真件＝与迁移脚本同形，双轨同形靠人审）。"""
        self._tables.ensure()

    # ── 落盘（三类语义分行；行为 1）───────────────────────────────────────────

    def save(self, record: RunRecord | StepRecord | BlackBox) -> None:
        """统一落盘入口：运行记录＝按状态机**更新**；步记录＝**同键幂等**；黑匣子＝**只追加**。"""
        if isinstance(record, RunRecord):
            self._save_run(record)
        elif isinstance(record, StepRecord):
            self._save_step(record)
        elif isinstance(record, BlackBox):
            self._save_blackbox(record)
        else:
            raise TypeError(f"落盘记录类型未知（三类之外）：{type(record).__name__}")

    def _save_run(self, record: RunRecord) -> None:
        """运行记录＝同一 run 一行（更新）；状态取值闭世界＋恢复方向把守（行为 2）。"""
        _guard_status_closed_world(record.status)
        stored = self._tables.get(TABLE_RUN, (record.run_id,))
        if stored is None:
            created_at = self._clock()  # 首写时间（此后不回溯）
        else:
            _guard_resume_direction(str(stored["status"]), record.status)
            created_at = _as_datetime(stored["created_at"])
        row = asdict(record)  # 列名＝记录字段名（投影不改名），时间列由本块经 infra.clock 盖
        row["created_at"] = created_at
        row["updated_at"] = self._clock()
        self._tables.write([RowOp(TABLE_RUN, (record.run_id,), row, "put")])

    def _save_step(self, record: StepRecord) -> None:
        """步记录＝同键 `(run_id, seq)` 幂等（不产生第二行；内容等价才允许覆盖——行为 1②）。"""
        _guard_step_closed_world(record.step, record.status)
        self._require_run(record.run_id)
        key = (record.run_id, str(record.seq))
        row = asdict(record)  # 列名＝记录字段名；`payload` 原样保真（不裁剪、不做假值归一——行为 8）
        row["created_at"] = self._clock()  # 该记录末次落盘时间
        stored = self._tables.get(TABLE_STEP, key)
        if stored is not None and _step_signature(stored) != _step_signature(row):
            raise StepConflictError(
                f"步记录同键内容不等价，不许覆盖：run={record.run_id!r} seq={record.seq}"
            )
        self._tables.write([RowOp(TABLE_STEP, key, row, "put")])

    def _save_blackbox(self, record: BlackBox) -> None:
        """黑匣子＝只追加、首写为准（行为 4）：重复归档不覆盖并抛出「已归档」（跳过的机读信号）。

        键闭世界把守（行为 11）：`record` 键越出白名单（R-J-02 二十键＋身份面四键）→ 抛错、
        一行不落（未入列键不进黑匣子；新增状态键须同批入列）。
        """
        self._require_run(record.run_id)
        unknown = sorted(set(record.record) - BLACKBOX_ALLOWED_KEYS)
        if unknown:
            raise BlackBoxKeyOutOfWorldError(record.run_id, unknown)
        stored = self._tables.get(TABLE_BLACKBOX, (record.run_id,))
        if stored is not None:
            raise AlreadyArchivedError(record.run_id, _as_datetime(stored["created_at"]))
        stamped = record.record.get("run_id")
        if stamped is not None and stamped != record.run_id:
            raise PersistenceError(
                f"黑匣子记录 run_id 与行键错挂：{stamped!r} ≠ {record.run_id!r}"
            )
        row = asdict(record)
        row["created_at"] = self._clock()  # 首写时间（此后不改写——行为 4）
        self._tables.write([RowOp(TABLE_BLACKBOX, (record.run_id,), row, "append")])

    # ── 读回（行为 3：只读、无副作用）─────────────────────────────────────────

    def load(self, run_id: str) -> RunState:
        """检查点恢复（跨进程重放）：两次 `load` 等价、不写盘（行为 3）。

        载荷＝该 run 默认通道域下最新状态快照行（`checkpoint.latest_state_row`）按 `schema_version`
        如实读入（行为 12）；无快照行＝按 run 行身份面装配（旧 run／未落检查点的如实面，不伪造
        历史、不补写对话通道）。run 行不存在 → 抛错（fail-closed）。
        """
        row = self._tables.get(TABLE_RUN, (run_id,))
        if row is None:
            raise RunNotFoundError(run_id)
        snapshot = latest_state_row(run_id, tables=self._tables)
        if snapshot is None:
            return _state_from_run_row(row)
        return decode_state(snapshot.checkpoint)

    def run(self, run_id: str) -> RunRecord | None:
        """按 run_id 取运行记录（缺行＝None——读口签名如实；缺行把守见 `_require_run`／`load`）。"""
        row = self._tables.get(TABLE_RUN, (run_id,))
        return None if row is None else _run_record_of(row)

    def steps(self, run_id: str) -> list[StepRecord]:
        """该 run 全步记录（`seq` 升序；无分页——上限归 `api` 侧，本块读口不改语义）。"""
        rows = self._tables.scan(TABLE_STEP, "run_id", run_id)
        rows.sort(key=lambda row: int(row["seq"]))
        return [_step_record_of(row) for row in rows]

    def blackbox(self, run_id: str) -> BlackBox | None:
        """按 run_id 取黑匣子（缺行＝None）；只追加面见 `_save_blackbox`。"""
        row = self._tables.get(TABLE_BLACKBOX, (run_id,))
        if row is None:
            return None
        return BlackBox(
            run_id=str(row["run_id"]),
            record=dict(row["record"]),
            created_at=_as_datetime(row["created_at"]),
        )

    # ── 引用载体（行为 10：可寻址 handle；语义不随载体变）─────────────────────

    def put_ref(self, blob: bytes) -> BlobRef:
        """落原文并返回凭据（内容定址：同原文恒同 handle，重复落不新增行）。"""
        digest = hashlib.sha256(blob).hexdigest()
        handle = f"{REF_HANDLE_PREFIX}{digest}"
        stored = self._tables.get(TABLE_BLOB, (handle,))
        if stored is None:
            row: dict[str, Any] = {
                "handle": handle,
                "blob": blob,
                "bytes": len(blob),
                "sha256": digest,
            }
            self._tables.write([RowOp(TABLE_BLOB, (handle,), row, "append")])
        elif _as_bytes(stored["blob"]) != blob:
            raise PersistenceError(f"引用载体内容定址冲突（handle 已占且原文不同）：{handle}")
        return BlobRef(handle=handle, bytes=len(blob), sha256=digest)

    def read_ref(self, handle: str) -> bytes:
        """按 handle 取回原文（**逐字节相同**）；handle 不可解析／未在册／与在册原文不符 → 抛错。"""
        if not handle.startswith(REF_HANDLE_PREFIX) or len(handle) != len(
            REF_HANDLE_PREFIX
        ) + _SHA256_CHARS:
            raise UnknownHandleError(handle, "格式不可解析")
        stored = self._tables.get(TABLE_BLOB, (handle,))
        if stored is None:
            raise UnknownHandleError(handle, "未在册")
        data = _as_bytes(stored["blob"])
        if hashlib.sha256(data).hexdigest() != handle[len(REF_HANDLE_PREFIX) :]:
            raise UnknownHandleError(handle, "与在册原文不符")
        return data

    # ── 内部件 ──────────────────────────────────────────────────────────────

    def _require_run(self, run_id: str) -> None:
        """步／黑匣子写入前把守 run 行在场（无外键错挂，行为 9）。"""
        if self._tables.get(TABLE_RUN, (run_id,)) is None:
            raise RunNotFoundError(run_id)


# ── 形状↔行 的投影与把守（模块级纯函数）───────────────────────────────────────


def _guard_status_closed_world(status: str) -> None:
    if status not in RUN_STATUS_KINDS:
        values = "／".join(sorted(RUN_STATUS_KINDS))
        raise ValueError(f"RunRecord.status 越界（闭世界 RUN_STATUS_KINDS＝{values}）：{status!r}")


def _guard_resume_direction(current: str, target: str) -> None:
    """行为 2 结构约束：写 `running` 只许自 `waiting_ask` 来——唯一合法「恢复」迁移方向。

    先例＝`recon/J` R-J-17「唯一合法转移 waiting_ask→running；running→running（重复调用）也拒」。
    终态／挂起方向的**该不该迁移**由 `orchestration` 决策，本块只把守方向与取值闭世界。
    """
    if target == RUN_RUNNING and current != RUN_WAITING_ASK:
        raise StatusTransitionError(
            f"非法迁移方向 {current}→{target}：唯一合法「恢复」方向＝waiting_ask→running（R-J-17）"
        )


def _guard_step_closed_world(step: str, status: str) -> None:
    if step not in STEP_KINDS:
        values = "／".join(sorted(STEP_KINDS))
        raise ValueError(f"StepRecord.step 越界（闭世界 STEP_KINDS＝{values}）：{step!r}")
    if status not in STEP_STATUS_KINDS:
        values = "／".join(sorted(STEP_STATUS_KINDS))
        raise ValueError(f"StepRecord.status 越界（闭世界 ok／failed／refused）：{status!r}")


def _step_signature(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(field) for field in _STEP_SIGNATURE_FIELDS)


def _run_record_of(row: Mapping[str, Any]) -> RunRecord:
    return RunRecord(
        run_id=str(row["run_id"]),
        question=str(row["question"]),
        actor=str(row["actor"]),
        status=str(row["status"]),
        answer=row["answer"] if isinstance(row["answer"], str) else None,
        error=row["error"] if isinstance(row["error"], str) else None,
        manifest_digest=row["manifest_digest"] if isinstance(row["manifest_digest"], str) else None,
        followup_of=str(row["followup_of"]),
        created_at=_as_datetime(row["created_at"]),
        updated_at=_as_datetime(row["updated_at"]),
        supplements=_supplements_of(row.get("supplements")),
    )


def _supplements_of(value: Any) -> list[dict[str, Any]]:
    """增补面列的读回形（2026-10-17 EB3 D1）：只认映射条目；旧行缺列／非列表＝空列（如实读入）。"""
    if not isinstance(value, (list, tuple)):
        return []
    return [dict(entry) for entry in value if isinstance(entry, Mapping)]


def _step_record_of(row: Mapping[str, Any]) -> StepRecord:
    return StepRecord(
        run_id=str(row["run_id"]),
        seq=int(row["seq"]),
        step=str(row["step"]),
        status=str(row["status"]),
        title=str(row["title"]),
        manifest=dict(row["manifest"]) if isinstance(row["manifest"], dict) else None,
        payload=dict(row["payload"]) if isinstance(row["payload"], dict) else None,
        created_at=_as_datetime(row["created_at"]),
    )


def _state_from_run_row(row: Mapping[str, Any]) -> RunState:
    """无快照行时的如实化装配：只取 run 行身份面，其余字段取 `RunState` 缺省（不伪造历史）。"""
    return RunState(
        run_id=str(row["run_id"]),
        question=str(row["question"]),
        actor=str(row["actor"]),
        status=str(row["status"]),
        followup_of=str(row["followup_of"]),
        answer=str(row["answer"] or ""),
        manifest_digest=str(row["manifest_digest"] or ""),
        error=row["error"] if isinstance(row["error"], str) else None,
    )


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise PersistenceError(f"时间列读入非时间值：{type(value).__name__}")


def _as_bytes(value: Any) -> bytes:
    return value if isinstance(value, bytes) else bytes(value)
