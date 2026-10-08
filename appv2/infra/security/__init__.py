"""appv2.infra.security —— 身份与审计公开出口（V2 复制层：appv2 各模块只 import 本包公开名）。

V2 复制层（V2-01 自 V1 app/domains/security/__init__.py 复制清理；公开名
清单剥 authorize/PageGroup/PAGE_GROUP_ROLES/ForbiddenError——V1 web 页面
组闸业务语义不进复制层）。

身份桩：resolve_actor（OAuth2.0 唯一替换缝，00 §2.4）；
审计：SecurityService.audit（B12 横切唯一写口）——appv2 各模块落审计时
action 槽恒用 `agent_v2.*` 前缀（specs/infra.md 行为约定 3：前缀与 V1 隔离）。
"""

from appv2.infra.security.domain import (
    DEFAULT_ROLE_KEY,
    ROLE_REGISTRY,
    Actor,
    AuditFilter,
    AuditLogView,
    AuditRow,
    RoleProfile,
    UnauthenticatedError,
    audit_digest,
    resolve_actor,
)
from appv2.infra.security.service import SecurityService

__all__ = [
    "DEFAULT_ROLE_KEY",
    "ROLE_REGISTRY",
    "Actor",
    "AuditFilter",
    "AuditLogView",
    "AuditRow",
    "RoleProfile",
    "SecurityService",
    "UnauthenticatedError",
    "audit_digest",
    "resolve_actor",
]
