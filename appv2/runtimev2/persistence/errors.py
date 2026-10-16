"""persistence 的错误族（fail-closed：不静默丢弃、不返回哨兵）。

真源＝`specs/persistence.md` 接口定义节「错误契约」：`save` 的 `status`／`step` 越界、归档重复、
run 不存在、`read_ref` 的 `handle` 不可解析 → **抛错**；错误码映射归调用方
（`api`／`orchestration`），本块只抛类型、不产对外码。闭世界取值越界沿用 `ValueError`
（与 `state` 块同款把守）。
"""

from __future__ import annotations

from datetime import datetime


class PersistenceError(Exception):
    """本块错误族根——调用方据类型映射对外错误码。"""


class RunNotFoundError(PersistenceError):
    """run 行不存在：`load` 与「步／黑匣子写入」的在场把守上抛（`run()` 读口按签名返回 None）。"""

    def __init__(self, run_id: str) -> None:
        super().__init__(f"run 不存在：{run_id}")
        self.run_id = run_id


class AlreadyArchivedError(PersistenceError):
    """黑匣子已归档——首写为准、重复归档不覆盖（行为 4）。

    携带首写行的 `run_id`／`archived_at`＝**跳过记账的机读信号**：调用方据本异常记一条 notice，
    发帧由 `orchestration` 协调（规格 行为 4；发帧实施口＝`transport`）。
    """

    def __init__(self, run_id: str, archived_at: datetime) -> None:
        super().__init__(
            f"已归档：{run_id}（首写 {archived_at.isoformat()}）——重复归档不覆盖，跳过本次"
        )
        self.run_id = run_id
        self.archived_at = archived_at


class StepConflictError(PersistenceError, ValueError):
    """步记录同键（`(run_id, seq)`）内容不等价——不许覆盖（行为 1②：内容等价才允许覆盖）。"""


class StatusTransitionError(PersistenceError, ValueError):
    """状态迁移方向非法（行为 2 结构约束；现状先例 `recon/J` R-J-17
    「唯一合法转移 waiting_ask→running」）。"""


class UnknownHandleError(PersistenceError, ValueError):
    """引用 `handle` 不可解析（行为 10：坏 handle 抛错，不猜、不返回哨兵）。"""

    def __init__(self, handle: str, reason: str = "不可解析") -> None:
        super().__init__(f"引用 handle {reason}：{handle!r}")
        self.handle = handle


class TableWriteError(PersistenceError, ValueError):
    """簿记表行级写被拒：非簿记表（INV-2 业务数据零写入）、表不允许该操作、只追加表键已在场。"""


class AuditSinkNotConfiguredError(PersistenceError):
    """审计写口未装配：审计唯一写口＝`security.audit`（B12），真件由装配点注入
    （本票不建 DB 连接件）。"""
