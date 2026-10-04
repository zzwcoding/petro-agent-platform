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
- semantics_param_invalid：台账读面筛选枚举越界（C1 错误码草案「筛选枚举越界 400」；
  P1-01b 新立值，登记于 tickets/phase1/README.md P1-01b 差异清单）
- kb_param_invalid / kb_not_found / kb_conflict：kb 域 400/404/409（B1 错误码
  草案；P1-02a 新立值，登记于 tickets/phase1/README.md P1-02a 差异清单）——
  KbParamError/KbConflictError 携带合同 code（kb_lib_disabled 停用库受理拦截
  400 带码/kb_lib_name_duplicate 重名 409/kb_route_unresolved 路由未定型等；
  B2 队列族（P1-04）：kb_issue_duplicate 待质检复核态重复标记 409 /
  kb_issue_state 状态机冲突 409 / kb_issue_reject_reason_required 驳回空理由
  400——B2 错误码草案，登记于 tickets/phase1/README.md P1-04 差异清单）
- kb_fragment_revise_deferred：片段修正端点壳（P1-02a 立壳，修正动作归
  P1-02b——501 非合同状态码，差异登记票面）
- wiki_not_found：wiki 域 404（B4 错误码草案；P1-02b 新立值，登记于
  tickets/phase1/README.md P1-02b 差异清单）——B4 v0.4 起纯读两态，
  wiki_param_invalid/wiki_conflict（400/409 版本/回滚族）随端点撤除废止
- graph_not_found / graph_param_invalid / graph_ontology_mismatch：graph 域
  404/400（B5 错误码草案；P1-05 新立值，登记于 tickets/phase1/README.md
  P1-05 差异清单）——强校 400 带对号明细（detail.mismatches）
- faq_param_invalid / faq_not_found / faq_conflict：faq 域 400/404/409
  （B3 错误码草案；P1-06 新立值，登记于 tickets/phase1/README.md P1-06 差异
  清单）——409 code 由异常携带（faq_scan_running 重入/faq_negative_toggle
  负例停用/faq_state_noop 状态未变化/faq_review_state 重复审核/
  faq_compare_state 未比对重复比对/faq_draft_state 未比对起草/
  faq_similar_duplicate 相似问重复/faq_candidate_published 候选重复回写）
- retrieval_param_invalid / retrieval_conflict：retrieval 域 400/409（D2 错误
  码草案；P1-07 新立值，登记于 tickets/phase1/README.md P1-07 差异清单）——
  400 带字段名与允许区间（D1 400 先例同形，detail.violations 逐项
  {field, constraint}）；409＝在途变更单重入（阶段 1 受理→生效一体，在途
  窗口＝并发受理撞闸）
- chat_param_invalid / chat_run_not_found / chat_run_state：chat 域 400/404/409
  （A1 错误码草案；P1-08a 新立值，登记于 tickets/phase1/README.md P1-08a 差异
  清单）——400＝question 为空且非重连/续跑模式、澄清选项无效、Action 链驳回
  缺理由；404＝run 不存在或已过期；409＝run 非 interrupt 挂起态（对已终态
  resume／二次澄清／重入 clarify——澄清帧有界循环最多弹一次，状态机约束）。
  Last-Event-ID 非整数 400（chat_last_event_id_invalid）P0-08 已登记沿用。
- well_not_found：wells 域 404（A2 错误码草案；M-02 新立值，登记于
  tickets/phase2/README.md M-02 差异清单）——井不存在（归一化后无此主键，
  设定书 §4 规则 7）；直调越权 403 走 security_forbidden 既有映射
  （A2 行为规则 1——预埋期 403 分支不可达，形状照写，开放问题 6 裁决）。
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domains.chat import ChatParamError, ChatRunNotFoundError, ChatRunStateError
from app.domains.derivatives import (
    GraphNotFoundError,
    GraphOntologyMismatchError,
    GraphParamError,
    WikiNotFoundError,
)
from app.domains.faq import (
    FaqConflictError,
    FaqNotFoundError,
    FaqParamError,
)
from app.domains.gateway import (
    ConfigWriteError,
    DrillConflictError,
    DrillNotFoundError,
    GatewayConfigError,
)
from app.domains.kb import (
    KbConflictError,
    KbDeferredError,
    KbNotFoundError,
    KbParamError,
)
from app.domains.retrieval import RetrievalConflictError, RetrievalParamError
from app.domains.security import ForbiddenError, UnauthenticatedError
from app.domains.wells import WellNotFoundError

CODE_UNAUTHENTICATED = "security_unauthenticated"
CODE_FORBIDDEN = "security_forbidden"
CODE_REQUEST_INVALID = "request_invalid"
CODE_GATEWAY_PARAM_INVALID = "gateway_param_invalid"
CODE_GATEWAY_DRILL_NOT_FOUND = "gateway_drill_not_found"
CODE_GATEWAY_DRILL_CONFLICT = "gateway_drill_conflict"
CODE_GATEWAY_CONFIG_WRITE_FAILED = "gateway_config_write_failed"
CODE_SEMANTICS_PARAM_INVALID = "semantics_param_invalid"
CODE_KB_DEFERRED = "kb_fragment_revise_deferred"
CODE_WIKI_NOT_FOUND = "wiki_not_found"
CODE_GRAPH_NOT_FOUND = "graph_not_found"
CODE_FAQ_NOT_FOUND = "faq_not_found"
CODE_WELL_NOT_FOUND = "well_not_found"


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

    @app.exception_handler(KbParamError)
    async def handle_kb_param_error(request: Request, exc: KbParamError) -> JSONResponse:
        # B1 错误码草案 400（含停用库受理拦截「400 带码」——kb_lib_disabled）。
        return JSONResponse(
            status_code=400,
            content=error_payload(exc.code, str(exc)),
        )

    @app.exception_handler(KbNotFoundError)
    async def handle_kb_not_found(request: Request, exc: KbNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=error_payload("kb_not_found", str(exc)),
        )

    @app.exception_handler(KbConflictError)
    async def handle_kb_conflict(request: Request, exc: KbConflictError) -> JSONResponse:
        # B1 错误码草案 409 族（confirm 未落桶/凭证已用/running 重试/未 done 读产物/
        # 路由未定型/重名——code 由异常携带）。
        return JSONResponse(
            status_code=409,
            content=error_payload(exc.code, str(exc)),
        )

    @app.exception_handler(KbDeferredError)
    async def handle_kb_deferred(request: Request, exc: KbDeferredError) -> JSONResponse:
        # 片段修正端点壳（P1-02a 立壳——修正动作归 P1-02b）。
        return JSONResponse(
            status_code=501,
            content=error_payload(CODE_KB_DEFERRED, "片段修正随 P1-02b 批开放"),
        )

    @app.exception_handler(WikiNotFoundError)
    async def handle_wiki_not_found(request: Request, exc: WikiNotFoundError) -> JSONResponse:
        # B4 错误码草案 404：百科页不存在（含 wiki 开关关未生成、直调未知 id）。
        return JSONResponse(
            status_code=404,
            content=error_payload(CODE_WIKI_NOT_FOUND, str(exc)),
        )

    @app.exception_handler(GraphNotFoundError)
    async def handle_graph_not_found(request: Request, exc: GraphNotFoundError) -> JSONResponse:
        # B5 错误码草案 404：库不存在（端点 1/2/3/4 同）。
        return JSONResponse(
            status_code=404,
            content=error_payload(CODE_GRAPH_NOT_FOUND, str(exc)),
        )

    @app.exception_handler(GraphParamError)
    async def handle_graph_param_error(request: Request, exc: GraphParamError) -> JSONResponse:
        # B5 错误码草案 400 族：入参形状非法（graph_param_invalid）＋
        # 对号强校不过（graph_ontology_mismatch——400 带对号明细：
        # 逐项未收录实体类型/关系标签＋最接近台账词条，前端原样展示）。
        detail: dict[str, Any] | None = None
        if isinstance(exc, GraphOntologyMismatchError):
            detail = {"mismatches": list(exc.mismatches)}
        return JSONResponse(
            status_code=400,
            content=error_payload(exc.code, str(exc), detail=detail),
        )

    @app.exception_handler(FaqParamError)
    async def handle_faq_param_error(request: Request, exc: FaqParamError) -> JSONResponse:
        # B3 错误码草案 400 族（入参形状非法/枚举越界/空白；code 由异常携带——
        # faq_param_invalid，P1-06 新立值，登记 tickets/phase1 README P1-06）。
        return JSONResponse(
            status_code=400,
            content=error_payload(exc.code, str(exc)),
        )

    @app.exception_handler(FaqNotFoundError)
    async def handle_faq_not_found(request: Request, exc: FaqNotFoundError) -> JSONResponse:
        # B3 错误码草案 404：条目/候选/相似问/扫库任务不存在（含已合并删除、
        # 已过期清理任务）。
        return JSONResponse(
            status_code=404,
            content=error_payload(CODE_FAQ_NOT_FOUND, str(exc)),
        )

    @app.exception_handler(FaqConflictError)
    async def handle_faq_conflict(request: Request, exc: FaqConflictError) -> JSONResponse:
        # B3 错误码草案 409 族（状态机冲突/重入/重复——code 由异常携带：
        # faq_scan_running/faq_negative_toggle/faq_state_noop/faq_review_state/
        # faq_compare_state/faq_draft_state/faq_similar_duplicate/
        # faq_candidate_published）。
        return JSONResponse(
            status_code=409,
            content=error_payload(exc.code, str(exc)),
        )

    @app.exception_handler(RetrievalParamError)
    async def handle_retrieval_param_error(
        request: Request, exc: RetrievalParamError
    ) -> JSONResponse:
        # D2 错误码草案 400「错误体带字段名与允许区间」——D1 400 带区间先例同形。
        message = "；".join(f"{field} 允许 {constraint}" for field, constraint in exc.violations)
        return JSONResponse(
            status_code=400,
            content=error_payload(
                "retrieval_param_invalid",
                "参数越界——" + message,
                detail={
                    "violations": [
                        {"field": field, "constraint": constraint}
                        for field, constraint in exc.violations
                    ]
                },
            ),
        )

    @app.exception_handler(RetrievalConflictError)
    async def handle_retrieval_conflict(
        request: Request, exc: RetrievalConflictError
    ) -> JSONResponse:
        # D2 错误码草案 409：同页在途变更单串行（阶段 1＝并发受理撞闸）。
        return JSONResponse(
            status_code=409,
            content=error_payload("retrieval_conflict", str(exc)),
        )

    @app.exception_handler(ChatParamError)
    async def handle_chat_param_error(request: Request, exc: ChatParamError) -> JSONResponse:
        # A1 错误码草案 400 族（question 为空且非重连/续跑模式、澄清选项无效、
        # Action 链驳回缺理由——code 由异常携带 chat_param_invalid）。
        return JSONResponse(
            status_code=400,
            content=error_payload(exc.code, str(exc)),
        )

    @app.exception_handler(ChatRunNotFoundError)
    async def handle_chat_run_not_found(
        request: Request, exc: ChatRunNotFoundError
    ) -> JSONResponse:
        # A1 错误码草案 404：run/session/task 不存在或已过期。
        return JSONResponse(
            status_code=404,
            content=error_payload("chat_run_not_found", str(exc)),
        )

    @app.exception_handler(WellNotFoundError)
    async def handle_well_not_found(request: Request, exc: WellNotFoundError) -> JSONResponse:
        # A2 错误码草案 404：井不存在（归一化后无此主键——「世界里根本没有」）；
        # 存在但无权 403 走 ForbiddenError 既有映射（行为规则 1②③——A2 同口径）。
        return JSONResponse(
            status_code=404,
            content=error_payload(CODE_WELL_NOT_FOUND, str(exc)),
        )

    @app.exception_handler(ChatRunStateError)
    async def handle_chat_run_state(request: Request, exc: ChatRunStateError) -> JSONResponse:
        # A1 错误码草案 409：run 非 interrupt 挂起态（对已终态 resume／二次澄清／
        # 重入 clarify——澄清帧最多弹一次，状态机约束）。
        return JSONResponse(
            status_code=409,
            content=error_payload("chat_run_state", str(exc)),
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
