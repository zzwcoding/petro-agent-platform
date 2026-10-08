"""appv2.api.deps —— 公共依赖：X-Dev-User 身份桩解包 → Actor、服务定位。

B1 同款纪律（V1 api/deps 先例）：请求头名（X-Dev-User）是接口层事实——
runtime/infra 只见值对象；本文件是 router 与 appv2.infra.security 公开面之间
唯一的框架接触带。

身份桩语义（00 §2.4，appv2.infra.security.resolve_actor 单点）：缺头/空白 →
缺省落默认角色（不 401）；非五角色键 → UnauthenticatedError → 错误包 401
（映射在 errors.py 统一装配）。OAuth2.0 替换只动 resolve_actor 实现。
"""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Header, Request

from appv2.api.bridge import RunStreamRegistry
from appv2.infra.security import Actor, resolve_actor
from appv2.runtime import AgentRuntime, RunStore

ACTOR_HEADER = "X-Dev-User"


async def current_actor(
    x_dev_user: Annotated[str | None, Header(alias=ACTOR_HEADER)] = None,
) -> Actor:
    """身份桩依赖：请求头取值 → resolve_actor（OAuth2.0 替换缝唯一入口）。"""
    return resolve_actor(x_dev_user)


CurrentActor = Annotated[Actor, Depends(current_actor)]


def get_runtime(request: Request) -> AgentRuntime:
    """runtime 服务定位（create_app 装配于 app.state）。"""
    return cast(AgentRuntime, request.app.state.agent_runtime)


def get_registry(request: Request) -> RunStreamRegistry:
    """SSE 事件桥注册表定位（create_app 装配于 app.state）。"""
    return cast(RunStreamRegistry, request.app.state.stream_registry)


def get_run_store(request: Request) -> RunStore:
    """run 簿记读面定位（create_app 装配于 app.state——GET runs 消费）。"""
    return cast(RunStore, request.app.state.run_store)


RuntimeDep = Annotated[AgentRuntime, Depends(get_runtime)]
RegistryDep = Annotated[RunStreamRegistry, Depends(get_registry)]
StoreDep = Annotated[RunStore, Depends(get_run_store)]
