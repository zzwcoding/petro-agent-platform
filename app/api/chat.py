"""api.chat —— /api/chat 路由族（A1 会话域——P1-08a SSE 主链填肉＋P1-08c 真恢复）。

合同真源（只读引用）：
- specs/api/00-系统级API.md §6 SSE 事件帧规范——帧信封 `id/event/data` 三行＋
  `done/error/replay_truncated` 三保留帧＋Last-Event-ID 断点解析。
- specs/api/A1-问一问.md 端点 4（POST /api/chat/asks——统一入口无旁路；同路径
  携 `resume_run_id`＋Last-Event-ID 头＝断线重连续推、不重新执行）＋端点 5
  （POST /api/chat/runs/{run_id}/resume——interrupt 决策回流续推）＋断线恢复
  三收场节（①窗内重连/②缓冲耗尽/③生成已取消）。
- 19 类业务帧由 domains.chat 域面产出（帧类型集＝A1 会话域合同值，不收编）；
  本文件只做信封渲染（帧序号枚举）与错误包出口——四层流水线全在服务端域内。
- 断线重连（P1-08c 真恢复）：resume_run_id 在场→chat_run/chat_message 持久帧
  重放（能补多少补多少——done 全量/挂起前缀；补不出 replay_truncated ③诚实
  收场）；仅 Last-Event-ID 头无法定位 run→P0-08 骨架判据 replay_truncated ②
  收场保持。重放流帧序号自断点续枚举（重放帧与原流帧 id 不对齐——能补的是
  持久化内容而非原流断点后的原帧序列，如实登记）。

鉴权（A1 权限行）：SSE 通道鉴权与 D1 第三道「身份与数据域」同闸——未认证 401
（CurrentActor 依赖）；A1 页全员可见，本端点不设页面组闸。
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Mapping
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import ChatDep, CurrentActor
from app.api.errors import ApiError
from app.domains.chat import ChatParamError, SseEvent
from app.domains.chat.domain import (
    FRAME_ERROR,
    FRAME_REPLAY_TRUNCATED,
    REPLAY_TRUNCATED_MESSAGE,
)

LOGGER = logging.getLogger("api.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])

# 00 §6.2 三保留帧名单源自 domains.chat（A1 会话域合同值 19 帧集，单源不双写）；
# 本模块 re-export 的 REPLAY_TRUNCATED_MESSAGE 保持 P0-08 测试导入名不变。

# 本票新立错误码（00 §3.3 <域>_<语义>；登记 tickets/phase1/README.md P1-08a）。
CODE_CHAT_LAST_EVENT_ID_INVALID = "chat_last_event_id_invalid"
CODE_CHAT_PARAM_INVALID = "chat_param_invalid"
CODE_CHAT_RUN_NOT_FOUND = "chat_run_not_found"
CODE_CHAT_RUN_STATE = "chat_run_state"
CODE_CHAT_STREAM_FAILED = "chat_stream_failed"


def render_frame(frame_id: int, event: str, data: Mapping[str, Any]) -> str:
    """00 §6.1 帧信封：`id/event/data` 三行＋空行收束（SSE 帧界）。

    帧序号即 Last-Event-ID 依据（00 §6.1）——续推断点按此回放。
    """
    return f"id: {frame_id}\nevent: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def error_frame(frame_id: int, code: str, message: str, hint: str | None = None) -> str:
    """00 §6.1 异常帧：`{code, message, hint?}`——发出后关闭流（调用方约定）。"""
    data: dict[str, Any] = {"code": code, "message": message}
    if hint is not None:
        data["hint"] = hint
    return render_frame(frame_id, FRAME_ERROR, data)


def parse_last_event_id(raw: str | None) -> int | None:
    """Last-Event-ID 解析缝（00 §6.1：帧序号为整型）。

    缺头/空白 → None（非重连）；非整数 → 400 错误包（00 §3.2——请求还没进门，
    流未开，走 HTTP 错误包而非 error 帧）。
    """
    key = (raw or "").strip()
    if not key:
        return None
    try:
        return int(key)
    except ValueError as exc:
        raise ApiError(
            status_code=400,
            code=CODE_CHAT_LAST_EVENT_ID_INVALID,
            message="Last-Event-ID 必须为帧序号（整数）",
        ) from exc


class PageContextBody(BaseModel):
    """page_context（A1 端点 4——对象页背景；F44 确定性注入随 wells 批消费）。"""

    page: str
    object_type: str | None = None
    object_id: str | None = None


class AskBody(BaseModel):
    """POST /api/chat/asks 入参（A1 端点 4 全量形状）。

    `resume_run_id` 在场即断线重连形态（question 等入参不再需要）。
    """

    session_id: str | None = None
    question: str | None = None
    page_context: PageContextBody | None = None
    anchors: list[str] | None = None
    resume_run_id: str | None = None


class ResumeBody(BaseModel):
    """POST /api/chat/runs/{run_id}/resume 入参（A1 端点 5——二选一按挂起帧类型）。

    - clarify：`choice` 点选项；
    - approval：`decision` approve/reject——reject 须写 `reason`（Action 链 400）。
    """

    kind: Literal["clarify", "approval"]
    choice: str | None = None
    decision: Literal["approve", "reject"] | None = None
    reason: str | None = None


async def _render(
    events: AsyncIterator[SseEvent], *, start: int = 0
) -> AsyncIterator[str]:
    """域事件帧流 → 00 §6.1 信封（帧序号自 start 枚举——Last-Event-ID 依据）。

    流内异常＝error 帧收场后关闭流（00 §6.1——SSE 内异常不走 HTTP 错误包；
    已知状态机错误在 post_resume 开流前经 resume_preflight 走 HTTP 错误包）。
    replay_truncated 帧注入 `resume_point`（A1 帧 19 合同载荷——已重放到的帧号，
    即截断帧前一帧；首帧即截断时为 None）。
    """
    idx = start
    try:
        async for event in events:
            data = event.data
            if event.event == FRAME_REPLAY_TRUNCATED:
                data = {"resume_point": idx - 1 if idx > 0 else None, **data}
            yield render_frame(idx, event.event, data)
            idx += 1
    except Exception:
        LOGGER.exception("chat SSE 流内异常——error 帧收场")
        yield error_frame(idx, CODE_CHAT_STREAM_FAILED, "流内异常——请重新提问")


async def _skeleton_replay_events() -> AsyncIterator[SseEvent]:
    """重连形态（无法定位 run——仅 Last-Event-ID 头在场）事件流（P0-08 判据保持）。

    按 00 §6.2 收场②家族以 replay_truncated 收场，data 携合同话术原文——
    不静默丢帧；resume_point 由 _render 注入（＝断点帧号）。
    """
    yield SseEvent(FRAME_REPLAY_TRUNCATED, {"message": REPLAY_TRUNCATED_MESSAGE})


class SessionItemBody(BaseModel):
    """会话行（A1 端点 2 合同形状——R1 snake）。"""

    id: str
    title: str
    group: str | None
    scenario_id: str | None
    updated_at: str


class SessionListResponse(BaseModel):
    items: list[SessionItemBody]


class AssetItemBody(BaseModel):
    """@ 资产条目（A1 端点 6 合同形状）。"""

    type: str
    name: str
    token: str


class AssetListResponse(BaseModel):
    items: list[AssetItemBody]


@router.get("/sessions")
async def get_sessions(chat: ChatDep, actor: CurrentActor) -> SessionListResponse:
    """GET /api/chat/sessions → 200（A1 端点 2——会话历史服务端持久读口）。

    当前身份（身份桩 X-Dev-User）的会话列表，updated_at 倒序；group/scenario_id
    骨架期 null（场景注册表端点 1 随其票）；新会话不设独立端点——asks 缺省即建。
    """
    items = await chat.list_sessions(actor.who)
    return SessionListResponse(items=[
        SessionItemBody(
            id=item.id, title=item.title, group=item.group,
            scenario_id=item.scenario_id, updated_at=item.updated_at,
        )
        for item in items
    ])


@router.get("/assets")
async def get_assets(
    chat: ChatDep,
    actor: CurrentActor,
    q: Annotated[str | None, Query()] = None,
    type: Annotated[str | None, Query()] = None,
) -> AssetListResponse:
    """GET /api/chat/assets?q=&type= → 200（A1 端点 6——@ 资产面板读口）。

    各注册表现取投影不建仓（指标卡/术语/工作流＝C1 台账、FAQ＝B3 服务中、
    报告＝B1 台账；工具注册表未建投影为空）；token＝「类型·名称」结晶体；
    type 越界 400（六类闭世界）。
    """
    try:
        items = await chat.assets(q, type)
    except ChatParamError as exc:
        raise ApiError(
            status_code=400, code=CODE_CHAT_PARAM_INVALID, message=str(exc)
        ) from exc
    return AssetListResponse(items=[
        AssetItemBody(type=item.type, name=item.name, token=item.token) for item in items
    ])


@router.post("/asks")
async def post_ask(
    chat: ChatDep,
    actor: CurrentActor,
    body: AskBody | None = None,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """POST /api/chat/asks → text/event-stream（A1 端点 4——统一入口无旁路）。

    - 身份闸：未认证 401（A1 权限行——SSE 与 D1 第三道同闸；缺头落默认角色
      不 401，00 §2.4）。
    - 断线重连形态（`resume_run_id` 或 Last-Event-ID 头任一在）：识别重连、
      不重新执行（P1-08c 真恢复——重放已持久化帧序列，能补多少补多少）：
      resume_run_id 在场→run 存在性开流前校验（不存在 404）＋持久帧重放
      （done 全量/interrupt 挂起前缀/其余 replay_truncated ③收场）；
      仅 Last-Event-ID 头（无法定位 run）→ 补不出维持 replay_truncated 诚实
      收场（P0-08 判据保持）。
    - 提问形态：question 为空且非重连/续跑模式 → 400（A1 错误码草案）；
      四层流水线在 domains.chat 域内，逐帧渲染为信封流。
    """
    breakpoint_id = parse_last_event_id(last_event_id)
    resume_run_id = body.resume_run_id if body is not None else None
    if resume_run_id is not None or breakpoint_id is not None:
        start = breakpoint_id + 1 if breakpoint_id is not None else 0
        if resume_run_id is not None:
            await chat.replay_preflight(resume_run_id)
            return StreamingResponse(
                _render(chat.replay(resume_run_id), start=start),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache"},
            )
        return StreamingResponse(
            _render(_skeleton_replay_events(), start=start),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )
    question = (body.question or "").strip() if body is not None else ""
    if not question:
        raise ApiError(
            status_code=400,
            code=CODE_CHAT_PARAM_INVALID,
            message="question 为空且非重连/续跑模式——提问必填（A1 错误码草案）",
        )
    return StreamingResponse(
        _render(chat.ask(
            question,
            session_id=body.session_id if body is not None else None,
            page_context=(
                body.page_context.model_dump() if body is not None and body.page_context else None
            ),
            anchors=list(body.anchors) if body is not None and body.anchors else [],
            actor_who=actor.who,
        )),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/runs/{run_id}/resume")
async def post_resume(
    run_id: str,
    chat: ChatDep,
    actor: CurrentActor,
    body: ResumeBody,
) -> StreamingResponse:
    """POST /api/chat/runs/{run_id}/resume → text/event-stream（A1 端点 5 续推）。

    interrupt 决策回流（澄清帧点选／审批批准·驳回）→ 续推 SSE；
    run 不存在 404 / 非 interrupt 挂起态 409（状态机约束——澄清帧最多弹一次）/
    形状非法 400，均在开流前经 resume_preflight 校验走 HTTP 错误包（00 §3.1：
    SSE 内异常不走 HTTP 错误包——流开前的同步段才能出状态码）。
    """
    await chat.resume_preflight(run_id, kind=body.kind, decision=body.decision, reason=body.reason)
    return StreamingResponse(
        _render(chat.resume(
            run_id,
            kind=body.kind,
            choice=body.choice,
            decision=body.decision,
            reason=body.reason,
            actor_who=actor.who,
        )),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
