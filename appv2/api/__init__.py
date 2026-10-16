"""appv2.api —— /api/v2/chat 薄端点层（V2-07；specs/modules.md api 卡）。

三端点＋SSE 事件桥：鉴权（X-Dev-User 身份桩——resolve_actor 单点）、参数校验
（400/401/404/409 统一错误包）、SSE 桥接（事件流 → transport 帧信封）。端点
薄层纪律：编排语义全在 runtime——本包只消费 AgentRuntime 公开接口（ask/resume）
＋读面＋infra（security/db/gateway 装配面）；不 import app.** 及引擎模块
（importlinter V2 契约在案）；SSE 帧不携带 langgraph 类型（ADR-0002 红线①
——载荷全 JSON 原语）。

公开面：
- router（三端点路由——挂线进 appv2 自有 app 工厂，V1 main.py 零改动）；
- create_app（组合缝——registry 注入；缺省＝生产组合 compose_production_
  registry，V2-19）＋lifespan；
- wire 面（V2-07·R10 定型）：WIRE_EVENT_KINDS 事件枚举（九 runtime＋三 wire
  十二值）＋render_frame 帧→SSE 渲染——帧对象、信封与 verdict subtype 判别的
  真源在 appv2.runtimev2.transport（本层只渲染，不另立第二套帧通路）；
- RunStream/RunStreamRegistry（SSE 事件桥——断线游标续传的缓冲面）；
- ApiError/install_error_handlers（00 §3 统一错误包，V1 同形）。
"""

from appv2.api.app import (
    MODEL_KEYS,
    compose_production_registry,
    create_app,
    ensure_app_tables,
    lifespan,
)
from appv2.api.bridge import RunStream, RunStreamRegistry, sse_frames
from appv2.api.chat import (
    AskBody,
    ResumeBody,
    RunView,
    StepView,
    parse_last_event_id,
    router,
)
from appv2.api.errors import (
    CODE_LAST_EVENT_ID_INVALID,
    CODE_PARAM_INVALID,
    CODE_REQUEST_INVALID,
    CODE_RUN_NOT_FOUND,
    CODE_RUN_STATE,
    CODE_STREAM_FAILED,
    CODE_UNAUTHENTICATED,
    ApiError,
    error_payload,
    install_error_handlers,
)
from appv2.api.wire import (
    FRAME_DONE,
    FRAME_ERROR,
    FRAME_SESSION,
    WIRE_EVENT_KINDS,
    render_frame,
)

__all__ = [
    "CODE_LAST_EVENT_ID_INVALID",
    "CODE_PARAM_INVALID",
    "CODE_REQUEST_INVALID",
    "CODE_RUN_NOT_FOUND",
    "CODE_RUN_STATE",
    "CODE_STREAM_FAILED",
    "CODE_UNAUTHENTICATED",
    "FRAME_DONE",
    "FRAME_ERROR",
    "FRAME_SESSION",
    "MODEL_KEYS",
    "WIRE_EVENT_KINDS",
    "ApiError",
    "AskBody",
    "ResumeBody",
    "RunStream",
    "RunStreamRegistry",
    "RunView",
    "StepView",
    "compose_production_registry",
    "create_app",
    "ensure_app_tables",
    "error_payload",
    "install_error_handlers",
    "lifespan",
    "parse_last_event_id",
    "render_frame",
    "router",
    "sse_frames",
]
