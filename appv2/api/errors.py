"""appv2.api.errors —— V2 统一错误包装配（00 §3 同形；appv2 自有装配点——
不咬 V1 app/api，V1 端点与错误处理零改动）。

形状（00 §3.1）：{ "code", "message" }——message 人话可透传；HTTP 语义按
00 §3.2：400 入参形状非法／401 身份解析失败／404 资源不存在／409 状态机冲突
（specs/agent-loop.md 接口定义节错误行：400 参数非法｜401 身份缺失｜
404 run 不存在｜409 run 非挂起态不可 resume）。

**映射源错误族（两族同形兜底）**：404／409 两条的异常源＝`orchestration` 包根错误族
（受理侧与追问播种侧上抛，`specs/modules.md` `## orchestration` 卡公开面注）——其
**同形兜底**＝`persistence` 同族两件（读口 `RunStore.load` 缺行抛 `RunNotFoundError`、
状态机把守抛 `StatusTransitionError`）：两族同语义同对外形（真源 `specs/persistence.md`
「状态机把守」），故映射表各出一条，HTTP 形一致（不因异常源不同而漂移）。

错误码值沿用 00 §3.3 `<域>_<语义>` 蛇形与 V1 已登记值（A1 错误码草案族——
身份码 security_unauthenticated 为 00 §2.3 系统级值，run 族与 V1 chat 域
同语义同值：前端错误处理面零改动可连）。V2 侧不新立码值；新立须登记票面
差异清单（V1 先例）。
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from appv2.infra.security import UnauthenticatedError
from appv2.runtimev2.orchestration import RunNotFoundError, RunNotSuspendedError
from appv2.runtimev2.persistence import RunNotFoundError as StoreRunNotFoundError
from appv2.runtimev2.persistence import StatusTransitionError

CODE_UNAUTHENTICATED = "security_unauthenticated"
CODE_REQUEST_INVALID = "request_invalid"
CODE_PARAM_INVALID = "chat_param_invalid"
CODE_LAST_EVENT_ID_INVALID = "chat_last_event_id_invalid"
CODE_RUN_NOT_FOUND = "chat_run_not_found"
CODE_RUN_STATE = "chat_run_state"
CODE_STREAM_FAILED = "chat_stream_failed"


class ApiError(Exception):
    """携带统一错误包的业务异常（接口层自行抛错时用——V1 同形）。"""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail


def error_payload(
    code: str, message: str, detail: dict[str, Any] | None = None
) -> dict[str, Any]:
    """00 §3.1 错误包形状（可选键缺省时不占位）。"""
    body: dict[str, Any] = {"code": code, "message": message}
    if detail is not None:
        body["detail"] = detail
    return body


def install_error_handlers(app: FastAPI) -> None:
    """把领域异常与框架校验异常统一映射为 00 §3 错误包（一次性装配）。"""

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message, exc.detail),
        )

    @app.exception_handler(UnauthenticatedError)
    async def handle_unauthenticated(request: Request, exc: UnauthenticatedError) -> JSONResponse:
        # 00 §2.3 401＝身份解析失败（非五角色键；缺头落默认角色不 401）。
        return JSONResponse(
            status_code=401, content=error_payload(CODE_UNAUTHENTICATED, str(exc))
        )

    @app.exception_handler(RunNotFoundError)
    async def handle_run_not_found(request: Request, exc: RunNotFoundError) -> JSONResponse:
        # 接口定义节错误行：404 run 不存在（orchestration 包根错误族——受理侧异常源单点映射）。
        return JSONResponse(
            status_code=404, content=error_payload(CODE_RUN_NOT_FOUND, str(exc))
        )

    @app.exception_handler(RunNotSuspendedError)
    async def handle_run_not_suspended(request: Request, exc: RunNotSuspendedError) -> JSONResponse:
        # 接口定义节错误行：409 run 非挂起态不可 resume（状态机约束源）。
        return JSONResponse(
            status_code=409, content=error_payload(CODE_RUN_STATE, str(exc))
        )

    @app.exception_handler(StoreRunNotFoundError)
    async def handle_store_run_not_found(
        request: Request, exc: StoreRunNotFoundError
    ) -> JSONResponse:
        # 同族兜底（persistence 侧）：读口缺行（`RunStore.load`）——404 对外形与上一条一致。
        return JSONResponse(
            status_code=404, content=error_payload(CODE_RUN_NOT_FOUND, str(exc))
        )

    @app.exception_handler(StatusTransitionError)
    async def handle_status_transition(
        request: Request, exc: StatusTransitionError
    ) -> JSONResponse:
        # 同族兜底（persistence 侧）：状态机把守拒（行为 2）——409 对外形与上一条一致。
        return JSONResponse(
            status_code=409, content=error_payload(CODE_RUN_STATE, str(exc))
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        # 00 §3.2：400＝请求还没进门（形状/枚举/缺项）——FastAPI 缺省 422 与
        # 合同冲突，统一收口 400 错误包（V1 同判据）。
        return JSONResponse(
            status_code=400,
            content=error_payload(
                CODE_REQUEST_INVALID,
                "入参形状非法",
                detail={
                    "errors": [
                        {"loc": list(err.get("loc", ())), "msg": err.get("msg", "")}
                        for err in exc.errors()
                    ]
                },
            ),
        )
