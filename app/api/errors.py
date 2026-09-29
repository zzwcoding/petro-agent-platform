"""api.errors —— 00 §3 统一错误包唯一装配点。

形状（00 §3.1）：{ "code", "message", "detail"?, "trace_id"? }——message 人话
可透传；detail 结构化附加可选；trace_id 可选预留位（携带策略悬置 §15-Q3，
现恒不携带）。HTTP 语义按 00 §3.2：400 入参形状非法／401 身份解析失败／
403 已认证越权／404 资源不存在／409 状态机冲突／500 服务端内部错误。

业务错误码（00 §3.3 `<域>_<语义>` 蛇形；合同未冻结具体值——本仓新立值
登记于 tickets/phase0/README.md P0-04/P0-05 差异清单）：
- security_unauthenticated：身份解析失败（00 §2.3 401）
- security_forbidden：已认证但越权（00 §2.3 403，页面角色组直调）
- request_invalid：入参形状非法（00 §3.2 400；FastAPI 缺省 422 与合同冲突，
  统一映射 400——R8 判据「请求还没进门＝400」）
- gateway_param_invalid：网关参数越界/枚举非法（D1 400「错误体带字段与允许
  区间」——detail.violations 逐项 {field, constraint}）
- gateway_drill_not_found / gateway_drill_conflict：演练 404/409（D1 错误码草案）
- gateway_config_write_failed：配置写回/热加载失败（D1 500「需回滚提示」）
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domains.gateway import (
    ConfigWriteError,
    DrillConflictError,
    DrillNotFoundError,
    GatewayConfigError,
)
from app.domains.security import ForbiddenError, UnauthenticatedError

CODE_UNAUTHENTICATED = "security_unauthenticated"
CODE_FORBIDDEN = "security_forbidden"
CODE_REQUEST_INVALID = "request_invalid"
CODE_GATEWAY_PARAM_INVALID = "gateway_param_invalid"
CODE_GATEWAY_DRILL_NOT_FOUND = "gateway_drill_not_found"
CODE_GATEWAY_DRILL_CONFLICT = "gateway_drill_conflict"
CODE_GATEWAY_CONFIG_WRITE_FAILED = "gateway_config_write_failed"


class ApiError(Exception):
    """携带统一错误包的业务异常（接口层自行抛错时用）。"""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        detail: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail
        self.trace_id = trace_id


def error_payload(
    code: str,
    message: str,
    detail: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """00 §3.1 错误包形状（可选键缺省时不占位——可选项语义）。"""
    body: dict[str, Any] = {"code": code, "message": message}
    if detail is not None:
        body["detail"] = detail
    if trace_id is not None:
        body["trace_id"] = trace_id
    return body


def install_error_handlers(app: FastAPI) -> None:
    """把领域异常与框架校验异常统一映射为 00 §3 错误包（一次性装配）。"""

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(exc.code, exc.message, exc.detail, exc.trace_id),
        )

    @app.exception_handler(UnauthenticatedError)
    async def handle_unauthenticated(request: Request, exc: UnauthenticatedError) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content=error_payload(CODE_UNAUTHENTICATED, str(exc)),
        )

    @app.exception_handler(ForbiddenError)
    async def handle_forbidden(request: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content=error_payload(CODE_FORBIDDEN, str(exc)),
        )

    @app.exception_handler(GatewayConfigError)
    async def handle_gateway_config_error(
        request: Request, exc: GatewayConfigError
    ) -> JSONResponse:
        # D1 错误码草案「参数越界 400：错误体含字段名与允许区间」。
        message = "；".join(f"{field} 允许 {constraint}" for field, constraint in exc.violations)
        return JSONResponse(
            status_code=400,
            content=error_payload(
                CODE_GATEWAY_PARAM_INVALID,
                "参数越界——" + message,
                detail={
                    "violations": [
                        {"field": field, "constraint": constraint}
                        for field, constraint in exc.violations
                    ]
                },
            ),
        )

    @app.exception_handler(DrillNotFoundError)
    async def handle_drill_not_found(request: Request, exc: DrillNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=error_payload(CODE_GATEWAY_DRILL_NOT_FOUND, str(exc)),
        )

    @app.exception_handler(DrillConflictError)
    async def handle_drill_conflict(request: Request, exc: DrillConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=error_payload(CODE_GATEWAY_DRILL_CONFLICT, str(exc)),
        )

    @app.exception_handler(ConfigWriteError)
    async def handle_config_write_failed(request: Request, exc: ConfigWriteError) -> JSONResponse:
        # D1 错误码草案「配置写回失败 500：网关热加载失败，需回滚提示」。
        return JSONResponse(
            status_code=500,
            content=error_payload(CODE_GATEWAY_CONFIG_WRITE_FAILED, str(exc)),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_invalid(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # 00 §3.2：400＝请求还没进门（形状/枚举/缺项），detail 带字段与问题——
        # FastAPI 缺省 422 形状不合合同，统一收口为 400 错误包。
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
