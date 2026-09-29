"""domains.security.service —— 薄服务面：编排 store，零业务语义（语义在 domain.py）。

公开面照 98 §3.13 卡：audit（B12 唯一写口）/ audit_logs（D3 端点 14 读面）。
身份语义（resolve_actor/authorize）无状态，直接由 domain.py 暴露——router 经
包出口（__init__）取用（B2：router 只调 domains 公开接口）。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.security.domain import AuditFilter, AuditLogView, AuditRow
from app.domains.security.store import AuditLogStore
from app.infra.db import ConnectionManager, Page


class SecurityService:
    """security 域服务（薄）：存储编排；身份解析不走此类（无状态，见 domain.py）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._store = AuditLogStore(db)

    async def audit(self, row: AuditRow, *, session: AsyncSession | None = None) -> None:
        """横切操作日志唯一写口（B12；SM3 digest；拦截也是审计事件——00 §8.2）。

        session 传参＝追加进调用方事务（同事务留痕）；缺省自管会话独立提交。
        """
        if session is None:
            await self._store.append(row)
        else:
            await self._store.append_in(session, row)

    async def audit_logs(
        self,
        audit_filter: AuditFilter | None = None,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[AuditLogView]:
        """D3 端点 14 读面：time/who/action/digest 投影＋倒序分页（R3 total 筛选后）。"""
        return await self._store.page(audit_filter, page=page, page_size=page_size)
