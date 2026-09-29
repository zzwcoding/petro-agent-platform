"""api.chat —— /api/chat 路由族空壳（P0-08 预留件；A1 会话域阶段 1 落地）。

合同真源（只读引用）：
- specs/api/00-系统级API.md §6 SSE 事件帧规范——本票只落**信封级骨架**：
  `id/event/data` 三行信封＋`done/error/replay_truncated` 三保留帧＋
  Last-Event-ID 请求头解析缝。**19 类业务帧不落**（A1 会话域合同值，帧类型集
  不收编——00 §6.2 尾注：他页/他域开 SSE 复用信封与三帧语义，业务帧自行立集）。
- specs/api/A1-问一问.md 端点 4（POST /api/chat/asks；同路径携 `resume_run_id`
  ＋Last-Event-ID 头＝断线重连续推、不重新执行）——只读形态参考，业务零实现。

骨架行为（阶段 1 填肉，票面差异清单已登记）：
- 提问形态 → 单枚 `done` 帧（`data:{}`，00 §6.1 结束帧形）后关流——占位收场；
- 重连形态（`resume_run_id` 或 Last-Event-ID 头任一在）→ 骨架无事件缓冲
  （98 §4 `infra.sse_channel` 未建），任何断点都补不出 → `replay_truncated`
  帧收场，data 携带 00 §6.2 收场②合同话术**原文**——不静默丢帧；
- `error` 帧构造器已备（`{code,message,hint?}`，发出后关闭流——00 §6.1：
  SSE 内异常不走 HTTP 错误包），阶段 1 业务链接管；唯一 HTTP 错误包出口＝
  Last-Event-ID 头非整数（「请求还没进门」＝400，00 §3.2/R8）。

鉴权（A1 权限行）：SSE 通道鉴权与 D1 第三道「身份与数据域」同闸——
未认证 401（CurrentActor 依赖）；A1 页全员可见，本端点不设页面组闸。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping
from typing import Annotated, Any

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import CurrentActor
from app.api.errors import ApiError

router = APIRouter(prefix="/api/chat", tags=["chat"])

# 00 §6.2 三保留帧（全通道复用；与 web/src/api/sse.js RESERVED_FRAMES 同源）。
FRAME_DONE = "done"
FRAME_ERROR = "error"
FRAME_REPLAY_TRUNCATED = "replay_truncated"

# 00 §6.2 收场②合同话术原文（不静默丢帧）。
REPLAY_TRUNCATED_MESSAGE = "会话中断较久，中间漏了一段（超出缓冲窗口），请重新提问。"

# 本票新立错误码（00 §3.3 <域>_<语义>；登记 tickets/phase0/README.md P0-08）。
CODE_CHAT_LAST_EVENT_ID_INVALID = "chat_last_event_id_invalid"


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
    流未开，走 HTTP 错误包而非 error 帧）。阶段 1 接 infra.sse_channel 后，
    本值即断点续推的回放起点。
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


class AskBody(BaseModel):
    """POST /api/chat/asks 入参骨架——仅合同已冻结的两名（A1 端点 4）。

    `question` 本骨架不消费（业务零实现）；`resume_run_id` 在场即重连形态。
    全量入参形状（附件/@资产/澄清回流等）阶段 1 按 A1 册收紧。
    """

    question: str | None = None
    resume_run_id: str | None = None


async def _skeleton_stream(
    resume_run_id: str | None, breakpoint_id: int | None
) -> AsyncIterator[str]:
    """骨架事件流（阶段 1 换 19 类业务帧流——00 §6.2 帧类型集不收编）。

    断点续推帧序＝断点 +1（「已出内容不丢、不重复」的序号演示缝；
    真实回放由 infra.sse_channel 按缓冲补发——本票未建）。
    """
    if resume_run_id is not None or breakpoint_id is not None:
        # 重连形态：骨架无事件缓冲（98 §4 infra.sse_channel 未建），任何断点
        # 都补不出——按 00 §6.2 收场②/③家族以 replay_truncated 收场，data 携
        # 合同话术原文，不静默丢帧。
        next_id = breakpoint_id + 1 if breakpoint_id is not None else 0
        yield render_frame(
            next_id, FRAME_REPLAY_TRUNCATED, {"message": REPLAY_TRUNCATED_MESSAGE}
        )
        return
    # 提问形态：占位收场（00 §6.1 结束帧形 data:{}）——阶段 1 填业务帧流。
    yield render_frame(0, FRAME_DONE, {})


@router.post("/asks")
async def post_ask(
    actor: CurrentActor,
    body: AskBody | None = None,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """POST /api/chat/asks → text/event-stream（A1 端点 4 骨架，业务零实现）。

    - 身份闸：未认证 401（A1 权限行——SSE 与 D1 第三道同闸；缺头落默认角色
      不 401，00 §2.4）。业务留痕（审计/账本）阶段 1 接。
    - 传输形态：POST 流式按现框架落 StreamingResponse（00 §6.1 悬置收敛为
      「结合实际框架定，合同只冻结帧协议」）；断线续推同路径（A1 端点 4）。
    """
    breakpoint_id = parse_last_event_id(last_event_id)
    resume_run_id = body.resume_run_id if body is not None else None
    return StreamingResponse(
        _skeleton_stream(resume_run_id, breakpoint_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
