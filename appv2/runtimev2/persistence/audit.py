"""审计唯一写口桥（B12：审计只经 `security.audit`）。

真源＝`specs/persistence.md` 接口定义节（`def audit(record: AuditRecord) -> None   # 唯一写口＝
security.audit（B12）`）＋「不降级与静默禁令」（**审计不可改写**：既成审计行不得 UPDATE／DELETE，
本块不提供任何改写入口——Owner 裁决 `walk/16` §七 Q-C「原始事实不可改写」）＋两道守门（行为 5
四要素齐备／行为 6 action 闭世界）＋行为 13 截断可见（`facts` 经截断单点 `summary.summarize`，
长度受控 ≤ `SUMMARY_LIMIT`）。

本模块是**只追加**的单点：`audit()` 把记录交给装配点注入的写口（真件＝`security.audit` 的桥，
`appv2.infra.security.SecurityService.audit`，B12），自身零表写入、零改写／删除路径。写口未装配
→ 抛错（fail-closed：不静默丢审计）——真 DB 连接件不在本票面，由装配点注入（登记：阶段 5）。

守门次序：① 四要素缺项 → `AuditElementMissingError`；② `action` 越界 →
`AuditActionOutOfWorldError`；③ `facts` 截断（可见标记）。前两道任一不过＝**不落库**
（缺项／越界记录不得进审计面）。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from appv2.runtimev2.persistence.errors import (
    AuditActionOutOfWorldError,
    AuditElementMissingError,
    AuditSinkNotConfiguredError,
)
from appv2.runtimev2.persistence.models import AUDIT_ACTIONS, AuditRecord
from appv2.runtimev2.persistence.summary import summarize

AuditSink = Callable[[AuditRecord], None]

# 四要素（行为 5；真源 Owner 裁决 walk/16 §七 Q-C）：主体＝who（scope 是其范围细化、并入本项）／
# 意图＝action（authorization 是其授权依据、无则空串、并入本项）／事实＝facts／结果＝evidence。
# `run_id` 是范围键（四类记录同源可聚合——行为 9），缺它即无法聚合，同列必填项。
AUDIT_REQUIRED_FIELDS: tuple[str, ...] = ("run_id", "who", "scope", "action", "facts", "evidence")

_sink: AuditSink | None = None


def configure_audit_sink(sink: AuditSink | None) -> AuditSink | None:
    """装配点注入审计写口（返回旧件——测试还原便利）。**唯一替换缝**，调用面不变。"""
    global _sink
    previous = _sink
    _sink = sink
    return previous


def current_audit_sink() -> AuditSink:
    """当前审计写口；未装配 → 抛错（不静默丢审计）。"""
    if _sink is None:
        raise AuditSinkNotConfiguredError(
            "审计写口未装配：唯一写口＝security.audit（B12）——装配点经 configure_audit_sink 注入"
        )
    return _sink


def audit(record: AuditRecord) -> None:
    """审计留痕唯一写口（只追加）：守门过→交给装配的写口落库；本块不提供任何改写／删除入口。"""
    current_audit_sink()(guard_audit_record(record))


def guard_audit_record(record: AuditRecord) -> AuditRecord:
    """四要素齐备 ＋ `action` 闭世界把守，并把 `facts` 过截断单点（行为 5／6／13）。

    `authorization` 无则空串（并入意图、不另立要素）——空串不算缺项。
    """
    missing = [name for name in AUDIT_REQUIRED_FIELDS if not _present(getattr(record, name))]
    if missing:
        raise AuditElementMissingError(record.run_id, missing)
    if record.action not in AUDIT_ACTIONS:
        raise AuditActionOutOfWorldError(record.action)
    return replace(record, facts=summarize(record.facts))


def _present(value: object) -> bool:
    """要素在场的判据：字符串非空、映射非空、其它面非 `None`（不猜、不做语义判定）。"""
    if isinstance(value, str):
        return value != ""
    if isinstance(value, dict):
        return len(value) > 0
    return value is not None
