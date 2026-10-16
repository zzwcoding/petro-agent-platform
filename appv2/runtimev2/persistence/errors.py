"""persistence 的错误族（fail-closed：不静默丢弃、不返回哨兵）。

真源＝`specs/persistence.md` 接口定义节「错误契约」：`save` 的 `status`／`step` 越界、归档重复、
run 不存在、`read_ref` 的 `handle` 不可解析 → **抛错**；错误码映射归调用方
（`api`／`orchestration`），本块只抛类型、不产对外码。闭世界取值越界沿用 `ValueError`
（与 `state` 块同款把守）。
"""

from __future__ import annotations

from collections.abc import Sequence
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


class AuditElementMissingError(PersistenceError, ValueError):
    """审计四要素缺项（行为 5）：主体（`who`；`scope` 是主体的范围细化）／意图（`action`）／
    事实（`facts`）／结果（`evidence`）——缺项判失败（不静默丢弃、不落残缺行）。"""

    def __init__(self, run_id: str, missing: Sequence[str]) -> None:
        super().__init__(f"审计四要素缺项（run={run_id!r}）：{'／'.join(missing)}")
        self.run_id = run_id
        self.missing: tuple[str, ...] = tuple(missing)


class AuditActionOutOfWorldError(PersistenceError, ValueError):
    """审计 `action` 越界（行为 6）：闭世界七值、恒 `agent_v2.` 前缀（真源 `recon/J` R-J-05）。"""

    def __init__(self, action: str) -> None:
        super().__init__(f"审计 action 越界（闭世界七值、恒 agent_v2. 前缀）：{action!r}")
        self.action = action


class BlackBoxKeyOutOfWorldError(PersistenceError, ValueError):
    """黑匣子记录键越界（行为 11）：`record` 键 ⊆ 白名单（真源 `recon/J` R-J-02 二十键＋
    R-J-50 身份面四键）——**新增状态键须显式入列**，未入列键不进黑匣子。"""

    def __init__(self, run_id: str, unknown: Sequence[str]) -> None:
        super().__init__(
            f"黑匣子记录键越界（未入列白名单——新增状态键须同批入列）："
            f"run={run_id!r} 键={'／'.join(unknown)}"
        )
        self.run_id = run_id
        self.unknown: tuple[str, ...] = tuple(unknown)


class AuditSinkNotConfiguredError(PersistenceError):
    """审计写口未装配：审计唯一写口＝`security.audit`（B12），真件由装配点注入
    （本票不建 DB 连接件）。"""
