"""appv2.api —— /api/v2/chat 薄端点层（V2-07；specs/modules.md api 卡）。

四端点＋SSE 事件桥：鉴权（X-Dev-User 身份桩——resolve_actor 单点）、参数校验
（400/401/404/409 统一错误包）、SSE 桥接（`RunHandle.stream` 的 `SseEvent` 帧 →
transport 帧信封文本）。端点薄层纪律：编排语义全在 `orchestration`——本包只消费其
**包根公开接口**（`AgentRuntime.ask/resume`＋受理三形状＋装配面 re-export）＋
persistence 两读口（run 行／步记录行投影）＋transport 类型/常量形状面＋infra（security/
db/gateway 装配面）；不 import 旧运行时包（`appv2/runtime/`——RT-W5-02 改接）；SSE 帧不携带
langgraph 类型（ADR-0002 红线①——载荷全 JSON 原语）。

公开面：
- router（四端点路由——挂线进 appv2 自有 app 工厂，V1 main.py 零改动）；
- create_app（组合缝——registry 注入；缺省＝生产组合 compose_production_
  registry，V2-19）＋lifespan；
- wire 面（V2-07·R10 定型）：WIRE_EVENT_KINDS 事件枚举（九 runtime＋三 wire
  十二值）＋render_frame（自产 wire 帧）＋render_event（**已编号流内帧**）——帧对象、
  信封与 verdict subtype 判别的真源在 appv2.runtimev2.transport（本层只渲染，
  不另立第二套帧通路、不重新编号）；
- RunStream/RunStreamRegistry/sse_frames（SSE 事件桥——断线游标续传的缓冲面）；
- ApiError/install_error_handlers（00 §3 统一错误包，V1 同形）。
"""

from appv2.api.app import (
    LedgerProjectionAdapter,
    SecurityAuditSink,
    compose_production_registry,
    create_app,
    ensure_app_tables,
    lifespan,
)
from appv2.api.bridge import (
    ERROR_FRAME_MESSAGE,
    FIRST_WIRE_SEQ,
    RunStream,
    RunStreamRegistry,
    sse_frames,
)
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
    render_event,
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
    "ERROR_FRAME_MESSAGE",
    "FIRST_WIRE_SEQ",
    "FRAME_DONE",
    "FRAME_ERROR",
    "FRAME_SESSION",
    "WIRE_EVENT_KINDS",
    "ApiError",
    "AskBody",
    "LedgerProjectionAdapter",
    "ResumeBody",
    "RunStream",
    "RunStreamRegistry",
    "RunView",
    "SecurityAuditSink",
    "StepView",
    "compose_production_registry",
    "create_app",
    "ensure_app_tables",
    "error_payload",
    "install_error_handlers",
    "lifespan",
    "parse_last_event_id",
    "render_event",
    "render_frame",
    "router",
    "sse_frames",
]
