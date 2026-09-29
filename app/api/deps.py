"""api.deps —— 公共依赖：X-Dev-User 身份桩解包 → Actor、服务定位、页面组闸。

B1/B2：请求头名（X-Dev-User）是接口层事实——领域层只见字符串；本文件是
router 与 domains.security 公开面之间唯一的框架接触带（B1：domains/infra
禁 import fastapi——router 除外，且 router 只调 domains 公开接口）。

身份桩语义（00 §2.4）：缺头/空白 → 缺省落默认角色（＝aqiang，PRD 拍板）；
非五角色键 → UnauthenticatedError → 错误包 401（映射在 errors.py 统一装配）。
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Header, Request

from app.domains.security import (
    Actor,
    SecurityService,
    authorize,
    resolve_actor,
)
from app.infra.db import ConnectionManager

ACTOR_HEADER = "X-Dev-User"


async def current_actor(
    x_dev_user: Annotated[str | None, Header(alias=ACTOR_HEADER)] = None,
) -> Actor:
    """身份桩依赖：请求头取值 → resolve_actor（OAuth2.0 替换缝唯一入口，00 §2.4）。"""
    return resolve_actor(x_dev_user)


CurrentActor = Annotated[Actor, Depends(current_actor)]


async def require_settings_actor(actor: CurrentActor) -> Actor:
    """设置中心组闸（D3 权限行：页面仅「平台运维」可见——00 §2.3 直调越权 403）。"""
    authorize(actor, "设置中心")
    return actor


SettingsActor = Annotated[Actor, Depends(require_settings_actor)]


def get_db(request: Request) -> ConnectionManager:
    """连接管理器定位（lifespan 装配于 app.state——main.py）。"""
    return cast(ConnectionManager, request.app.state.db)


def get_security(request: Request) -> SecurityService:
    """security 服务定位（lifespan 装配于 app.state——main.py）。"""
    return cast(SecurityService, request.app.state.security)


DbDep = Annotated[ConnectionManager, Depends(get_db)]
SecurityDep = Annotated[SecurityService, Depends(get_security)]
