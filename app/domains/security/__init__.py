"""domains.security —— 身份权限与安全域公开出口（B2：router 只 import 本包公开名）。

身份桩：resolve_actor（OAuth2.0 唯一替换缝，00 §2.4）；
审计：SecurityService.audit（B12 横切唯一写口）；
横切原语与读面照 98 §3.13 卡（authenticate/authorize/audit/audit_logs）。
"""

from app.domains.security.domain import (
    DEFAULT_ROLE_KEY,
    PAGE_GROUP_ROLES,
    ROLE_REGISTRY,
    Actor,
    AuditFilter,
    AuditLogView,
    AuditRow,
    ForbiddenError,
    PageGroup,
    RoleProfile,
    UnauthenticatedError,
    audit_digest,
    authorize,
    resolve_actor,
)
from app.domains.security.service import SecurityService

__all__ = [
    "DEFAULT_ROLE_KEY",
    "PAGE_GROUP_ROLES",
    "ROLE_REGISTRY",
    "Actor",
    "AuditFilter",
    "AuditLogView",
    "AuditRow",
    "ForbiddenError",
    "PageGroup",
    "RoleProfile",
    "SecurityService",
    "UnauthenticatedError",
    "audit_digest",
    "authorize",
    "resolve_actor",
]
