"""appv2.api.chat —— /api/v2/chat 路由族（A1 问一问 V2 主链——三端点＋SSE）。

合同真源（只读引用）：specs/agent-loop.md 接口定义节＋specs/modules.md api 卡。
端点三行（薄层——编排语义全在 runtime，本层只做鉴权/参数校验/SSE 桥接）：
- POST /api/v2/chat/asks            → text/event-stream（首帧 session 携 run_id）
- POST /api/v2/chat/runs/{id}/resume → text/event-stream（挂起段续跑流）
- GET  /api/v2/chat/runs/{id}        → {status, steps, manifest_digest}

断线游标续传（V1 帧形兼容——web/src/api/chat.js reconnectRun 同形态）：
asks 携 `resume_run_id`（＋Last-Event-ID 头）＝重连形态，不重新执行——重放
该 run 缓冲断点后事件（尾随 running 流），仅 Last-Event-ID 头无 run 定位＝
400（V2 无「缓冲窗口」语义——补不出不是诚实降级而是请求缺参，如实拒）。
Last-Event-ID 非整数 400（00 §3.2——请求还没进门，不开流）。

resume 入参（V1 端点 5 形态兼容）：clarify＝`choice` 点选项；approval＝
`decision` approve/reject——值映射 AskFrame 选项闭世界（"批准"/"驳回"），
approval_id 透传留痕（V2-03 偏差 7 接线③——run 前缀种子单号回传）。

SSE 内异常不走 HTTP 错误包（00 §6.1）——error 帧收场；流开前的同步段
（404/409/400/401）才出状态码。resume 的 run 校验在开流前完成（runtime
execute 同步段抛 RunNotFoundError/RunNotSuspendedError → errors 统一映射）。
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from appv2.api.bridge import sse_frames
from appv2.api.deps import CurrentActor, RegistryDep, RuntimeDep, StoreDep
from appv2.api.errors import (
    CODE_LAST_EVENT_ID_INVALID,
    CODE_PARAM_INVALID,
    CODE_RUN_NOT_FOUND,
    CODE_RUN_STATE,
    ApiError,
)
from appv2.runtime import AskChoice, AskRequest

router = APIRouter(prefix="/api/v2/chat", tags=["chat-v2"])

_STREAM_HEADERS = {"Cache-Control": "no-cache"}


def parse_last_event_id(raw: str | None) -> int | None:
    """Last-Event-ID 解析缝（00 §6.1：帧序号为整型；缺头/空白＝None 非重连；
    非整数＝400 错误包不开流）。"""
    key = (raw or "").strip()
    if not key:
        return None
    try:
        return int(key)
    except ValueError as exc:
        raise ApiError(
            status_code=400,
            code=CODE_LAST_EVENT_ID_INVALID,
            message="Last-Event-ID 必须为帧序号（整数）",
        ) from exc


class AskBody(BaseModel):
    """POST /api/v2/chat/asks 入参（三形态：question 提问｜resume_run_id 重连｜
    question＋followup_run_id 追问续会话）。

    followup_run_id（V2-38/ADR-0006 追问续会话）：对话框追问＝会话线程新轮——
    新 run 播种该前轮线程的消息历史（前轮问句/决策/执行台账/答案随追问进上下文）；
    前轮须 completed（不存在 404／未收口 409——开流前错误包）；V1 帧兼容不破
    （session 首帧形不变，新 run_id＋resume=False）。

    resume_run_id 与 followup_run_id 互斥（P-032b C7）：同在场＝409＋机读注记
    （detail.conflict）——重连形态不重新执行，同在场的 followup 不被静默忽略。
    """

    question: str | None = None
    resume_run_id: str | None = None
    followup_run_id: str | None = None


class ResumeBody(BaseModel):
    """POST /api/v2/chat/runs/{run_id}/resume 入参（V1 端点 5 形态兼容）。"""

    kind: Literal["clarify", "approval"]
    choice: str | None = None
    decision: Literal["approve", "reject"] | None = None
    approval_id: str | None = None


class StepView(BaseModel):
    """步记录投影（agent_v2_step 行——INV-5 存档形的读面直出）。"""

    seq: int
    step: str
    status: str
    title: str
    manifest: dict[str, Any] | None
    payload: dict[str, Any] | None


class RunView(BaseModel):
    """GET runs/{run_id} 响应（接口定义节合同形：{status, steps, manifest_digest}）。"""

    status: str
    steps: list[StepView]
    manifest_digest: str | None


def _choice_of(body: ResumeBody) -> AskChoice:
    """resume 入参 → AskChoice（形状 400 单点；值映射 AskFrame 选项闭世界）。"""
    if body.kind == "clarify":
        value = (body.choice or "").strip()
        if not value:
            raise ApiError(
                status_code=400,
                code=CODE_PARAM_INVALID,
                message="clarify resume 须携 choice（挂起帧 options 点选项）",
            )
        return AskChoice(value=value)
    if body.decision is None:
        raise ApiError(
            status_code=400,
            code=CODE_PARAM_INVALID,
            message="approval resume 须携 decision（approve/reject）",
        )
    return AskChoice(
        value="批准" if body.decision == "approve" else "驳回",
        approval_id=body.approval_id,
    )


@router.post("/asks")
async def post_ask(
    actor: CurrentActor,
    runtime: RuntimeDep,
    registry: RegistryDep,
    body: AskBody | None = None,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """POST /api/v2/chat/asks → text/event-stream（接口定义节第一行）。

    - 重连形态（resume_run_id 在场）：不重新执行——重放该 run 缓冲断点后事件
      （run 不存在 404；缓冲在 api 层进程内——跨进程重启后重放归 ADR-0003
      队列消费者形态）；
    - 提问形态：question 必填非空（400）；每问新建 run（行为约定 1）；
    - 追问形态（question＋followup_run_id，V2-38）：会话线程新轮——前轮不存在
      404／未收口 409 在开流前抛（runtime execute 同步段）。
    """
    breakpoint_id = parse_last_event_id(last_event_id)
    resume_run_id = body.resume_run_id if body is not None else None
    followup_run_id = (body.followup_run_id or "").strip() if body is not None else ""
    if resume_run_id and followup_run_id:
        # 参数互斥闸（P-032b C7）：重连与追问同在场＝显式拒绝——重连形态不重新
        # 执行，同在场的 followup 不许被静默忽略（409＋机读注记，不静默）。
        raise ApiError(
            status_code=409,
            code=CODE_RUN_STATE,
            message=(
                "resume_run_id 与 followup_run_id 同在场——重连与追问互斥"
                "（重连不重新执行，追问须去 resume_run_id 二选一）"
            ),
            detail={
                "conflict": ["resume_run_id", "followup_run_id"],
                "resume_run_id": resume_run_id,
                "followup_run_id": followup_run_id,
            },
        )
    if resume_run_id is not None:
        stream = registry.get(resume_run_id)
        if stream is None:
            raise ApiError(
                status_code=404,
                code=CODE_RUN_NOT_FOUND,
                message=f"run 不存在（或不在本进程缓冲内）：{resume_run_id}",
            )
        cursor = breakpoint_id if breakpoint_id is not None else 0
        return StreamingResponse(
            sse_frames(
                stream,
                first_frame_id=breakpoint_id + 1 if breakpoint_id is not None else 0,
                follow_cursor=cursor,
                session={"run_id": resume_run_id, "resume": True},
            ),
            media_type="text/event-stream",
            headers=_STREAM_HEADERS,
        )
    if breakpoint_id is not None:
        raise ApiError(
            status_code=400,
            code=CODE_PARAM_INVALID,
            message="Last-Event-ID 断点续传须携 resume_run_id 定位 run",
        )
    question = (body.question or "").strip() if body is not None else ""
    if not question:
        raise ApiError(
            status_code=400,
            code=CODE_PARAM_INVALID,
            message="question 为空——提问必填（接口定义节错误行 400 参数非法）",
        )
    handle = await runtime.ask(
        AskRequest(
            question=question, actor=actor, followup_of=followup_run_id
        )
    )
    stream, mark = registry.register(handle)
    return StreamingResponse(
        sse_frames(
            stream,
            first_frame_id=0,
            follow_cursor=mark,
            session={"run_id": handle.run_id, "resume": False},
        ),
        media_type="text/event-stream",
        headers=_STREAM_HEADERS,
    )


@router.post("/runs/{run_id}/resume")
async def post_resume(
    run_id: str,
    body: ResumeBody,
    actor: CurrentActor,
    runtime: RuntimeDep,
    registry: RegistryDep,
) -> StreamingResponse:
    """POST /api/v2/chat/runs/{run_id}/resume → text/event-stream（挂起段续跑）。

    run 不存在 404／非挂起态 409 在开流前抛（runtime execute 同步段——00 §3.1
    流开前才有状态码）；入参形状 400 单点 _choice_of。
    """
    handle = await runtime.resume(run_id, _choice_of(body))
    stream, mark = registry.register(handle)
    return StreamingResponse(
        sse_frames(
            stream,
            first_frame_id=0,
            follow_cursor=mark,
            session={"run_id": run_id, "resume": True},
        ),
        media_type="text/event-stream",
        headers=_STREAM_HEADERS,
    )


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str, actor: CurrentActor, store: StoreDep
) -> RunView:
    """GET /api/v2/chat/runs/{run_id} → {status, steps, manifest_digest}
    （接口定义节第三行——run 历史/步详情回看，页面映射 A1 行）。

    步记录按 seq 升序直出（INV-5 存档形——Manifest 随模型调用步在场）；
    run 不存在 404（不泄漏存在性差异）。
    """
    row = await store.get_run(run_id)
    if row is None:
        raise ApiError(
            status_code=404,
            code=CODE_RUN_NOT_FOUND,
            message=f"run 不存在：{run_id}",
        )
    steps = await store.list_steps(run_id)
    return RunView(
        status=row.status,
        steps=[
            StepView(
                seq=step.seq,
                step=step.step_type,
                status=step.status,
                title=step.title,
                manifest=step.manifest,
                payload=step.payload,
            )
            for step in steps
        ],
        manifest_digest=row.manifest_digest,
    )
