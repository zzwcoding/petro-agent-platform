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

from app.domains.chat import ChatService
from app.domains.dataops.quality import QualityService
from app.domains.derivatives import DerivativesService
from app.domains.faq import FaqService
from app.domains.gateway import GatewayService
from app.domains.kb import KbService
from app.domains.retrieval import RetrievalService
from app.domains.security import (
    Actor,
    SecurityService,
    authorize,
    resolve_actor,
)
from app.domains.semantics import SemanticsService
from app.domains.wells import WellsService
from app.infra.db import ConnectionManager

ACTOR_HEADER = "X-Dev-User"


async def current_actor(
    x_dev_user: Annotated[str | None, Header(alias=ACTOR_HEADER)] = None,
) -> Actor:
    """身份桩依赖：请求头取值 → resolve_actor（OAuth2.0 替换缝唯一入口，00 §2.4）。

    OAuth2.0 切换时取头来源（X-Dev-User Header 名，ACTOR_HEADER）同属开发期
    实现，需随 resolve_actor 同步替换；合同语义面（Actor/401 判例）零改动。
    """
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


def get_gateway(request: Request) -> GatewayService:
    """gateway 服务定位（lifespan 装配于 app.state——main.py）。"""
    return cast(GatewayService, request.app.state.gateway)


def get_semantics(request: Request) -> SemanticsService:
    """semantics 服务定位（lifespan 装配于 app.state——main.py；P1-01b 读面起）。"""
    return cast(SemanticsService, request.app.state.semantics)


def get_kb(request: Request) -> KbService:
    """kb 服务定位（lifespan 装配于 app.state——main.py；P1-02a 起）。"""
    return cast(KbService, request.app.state.kb)


def get_derivatives(request: Request) -> DerivativesService:
    """derivatives 服务定位（lifespan 装配于 app.state——main.py；P1-02b 起）。"""
    return cast(DerivativesService, request.app.state.derivatives)


def get_faq(request: Request) -> FaqService:
    """faq 服务定位（lifespan 装配于 app.state——main.py；P1-06 起）。"""
    return cast(FaqService, request.app.state.faq)


def get_retrieval(request: Request) -> RetrievalService:
    """retrieval 服务定位（lifespan 装配于 app.state——main.py；P1-07 起）。"""
    return cast(RetrievalService, request.app.state.retrieval)


def get_chat(request: Request) -> ChatService:
    """chat 服务定位（lifespan 装配于 app.state——main.py；P1-08a 起）。"""
    return cast(ChatService, request.app.state.chat)


def get_wells(request: Request) -> WellsService:
    """wells 服务定位（lifespan 装配于 app.state——main.py；M-02 起）。"""
    return cast(WellsService, request.app.state.wells)


def get_quality(request: Request) -> QualityService:
    """quality 服务定位（lifespan 装配于 app.state——main.py；M-05a 起）。"""
    return cast(QualityService, request.app.state.quality)


DbDep = Annotated[ConnectionManager, Depends(get_db)]
SecurityDep = Annotated[SecurityService, Depends(get_security)]
GatewayDep = Annotated[GatewayService, Depends(get_gateway)]
SemanticsDep = Annotated[SemanticsService, Depends(get_semantics)]
KbDep = Annotated[KbService, Depends(get_kb)]
WikiDep = Annotated[DerivativesService, Depends(get_derivatives)]
GraphDep = Annotated[DerivativesService, Depends(get_derivatives)]
FaqDep = Annotated[FaqService, Depends(get_faq)]
RetrievalDep = Annotated[RetrievalService, Depends(get_retrieval)]
ChatDep = Annotated[ChatService, Depends(get_chat)]
WellsDep = Annotated[WellsService, Depends(get_wells)]
QualityDep = Annotated[QualityService, Depends(get_quality)]
