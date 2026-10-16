"""审计唯一写口桥（B12：审计只经 `security.audit`）。

真源＝`specs/persistence.md` 接口定义节（`def audit(record: AuditRecord) -> None   # 唯一写口＝
security.audit（B12）`）＋「不降级与静默禁令」（**审计不可改写**：既成审计行不得 UPDATE／DELETE，
本块不提供任何改写入口——Owner 裁决 `walk/16` §七 Q-C「原始事实不可改写」）。

本模块是**只追加**的单点：`audit()` 把记录交给装配点注入的写口（真件＝`security.audit` 的桥，
`appv2.infra.security.SecurityService.audit`，B12），自身零表写入、零改写／删除路径。写口未装配
→ 抛错（fail-closed：不静默丢审计）——真 DB 连接件不在本票面，由装配点注入（登记：阶段 5）。
"""

from __future__ import annotations

from collections.abc import Callable

from appv2.runtimev2.persistence.errors import AuditSinkNotConfiguredError
from appv2.runtimev2.persistence.models import AuditRecord

AuditSink = Callable[[AuditRecord], None]

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
    """审计留痕唯一写口（只追加）：交给装配的写口落库；本块不提供任何改写／删除入口。"""
    current_audit_sink()(record)
