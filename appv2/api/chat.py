"""appv2.api.chat —— /api/v2/chat 路由族（A1 问一问 V2 主链——四端点＋SSE）。

合同真源（只读引用）：specs/agent-loop.md 接口定义节＋specs/modules.md api 卡。
端点四行（薄层——编排语义全在 orchestration，本层只做鉴权/参数校验/SSE 桥接）：

- POST /api/v2/chat/asks            → text/event-stream（首帧 session 携 run_id）
- POST /api/v2/chat/runs/{id}/resume → text/event-stream（挂起段续跑流）
- GET  /api/v2/chat/runs             → [{run_id, question, status, answer, …}]（最近任务读口）
- GET  /api/v2/chat/runs/{id}        → {status, steps, manifest_digest, pending_ask?}

断线游标续传（V1 帧形兼容——web/src/api/chat.js reconnectRun 同形态）：asks 携
`resume_run_id`（＋`Last-Event-ID` 头）＝重连形态，不重新执行——读本进程帧缓冲里
`seq ≥ cursor` 的帧（`cursor`＝客户端回送帧号＋1，transport 行为 5 的排他起点）；
仅 `Last-Event-ID` 头无 run 定位＝400（V2 无「缓冲窗口」语义——补不出不是诚实降级
而是请求缺参，如实拒）。`Last-Event-ID` 非整数 400；**换算后为负游标**（帧号 ≤ -2）
＝400——负游标被 transport 拒（`EventBus.stream` 错误契约），故在开流前同步段收口
（00 §3.2——请求还没进门，不开流）；帧号 -1 合法（wire 帧流首号——回送即 cursor 0）。

resume 入参＝**HTTP 词面 → V2 形**映射（裁：api 是 HTTP 适配层）：`kind:"clarify"` →
`AskChoice(kind="clarify", choice=…)`；`kind:"approval"` → `AskChoice(kind=
"external_table_approval", decision="approve"/"reject", approval_id=…)`（`kind` 两值
闭世界真源＝`specs/state.md` 行为 14／`AskChoiceKind`；`external_table_approval` 与
`transport.ASK_FRAME_KINDS` 同值集、与编排块外表审批决定判形同值）。

SSE 内异常不走 HTTP 错误包（00 §6.1）——error 帧收场；流开前的同步段
（404/409/400/401）才出状态码。resume 的 run 校验在开流前完成（受理面同步段抛
`RunNotFoundError`／`RunNotSuspendedError` → errors 统一映射）。
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
from appv2.runtimev2.orchestration import AskChoice, AskRequest
from appv2.runtimev2.state import RUN_WAITING_ASK

router = APIRouter(prefix="/api/v2/chat", tags=["chat-v2"])

_STREAM_HEADERS = {"Cache-Control": "no-cache"}

_CLARIFY_KIND: Literal["clarify"] = "clarify"
_APPROVAL_KIND: Literal["external_table_approval"] = "external_table_approval"


def parse_last_event_id(raw: str | None) -> int | None:
    """`Last-Event-ID` 解析缝（00 §6.1：帧序号为整型；缺头/空白＝None 非重连）。

    非整数＝400 错误包不开流；**换算后为负游标**（`id + 1 < 0`，即 id ≤ -2）＝400——
    transport 对负 cursor 抛错（`EventBus.stream` 错误契约），本层在开流前同步段收口，
    不让它翻到流内（00 §3.2）。id ＝ -1（wire 帧流首号）合法：换算得 cursor 0＝从全流头重放。
    """
    key = (raw or "").strip()
    if not key:
        return None
    try:
        value = int(key)
    except ValueError as exc:
        raise ApiError(
            status_code=400,
            code=CODE_LAST_EVENT_ID_INVALID,
            message="Last-Event-ID 必须为帧序号（整数）",
        ) from exc
    if value + 1 < 0:
        raise ApiError(
            status_code=400,
            code=CODE_LAST_EVENT_ID_INVALID,
            message="Last-Event-ID 为负游标（帧号 ≤ -2——cursor＝帧号＋1 须 ≥ 0）",
        )
    return value


def _cursor_of(breakpoint_id: int | None) -> int:
    """回送帧号 → 事件消费起点（`cursor`＝**下一帧 seq**，transport 行为 5 排他起点）。"""
    return 0 if breakpoint_id is None else breakpoint_id + 1


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
    """POST /api/v2/chat/runs/{run_id}/resume 入参（HTTP 词面——映射归 `_choice_of`）。"""

    kind: Literal["clarify", "approval"]
    choice: str | None = None
    decision: Literal["approve", "reject"] | None = None
    approval_id: str | None = None


class StepView(BaseModel):
    """步记录投影（`agent_v2_step` 行——INV-5 存档形的读面直出）。"""

    seq: int
    step: str
    status: str
    title: str
    manifest: dict[str, Any] | None
    payload: dict[str, Any] | None


class RunView(BaseModel):
    """GET runs/{run_id} 响应（接口定义节合同形：{status, steps, manifest_digest}）。

    pending_ask（V2-78）：挂起轮的 AskFrame dict 投影（kind/prompt/options/detail）
    ——仅 waiting_ask 且线程态在场时非 None；刷新后反问选项由此还原（投影源＝
    `RunState.pending_ask`，经 persistence 读口 `RunStore.load`）。
    """

    status: str
    steps: list[StepView]
    manifest_digest: str | None
    pending_ask: dict[str, Any] | None = None


class RunListItem(BaseModel):
    """GET runs 列表项（V2-73 会话历史读口——最近任务面；answer 全文随行）。

    followup_of（V2-74 对话任务面）：追问链前轮 run_id——空串＝独立新对话（链根），
    非空＝追问轮；前端按链分组呈现「一个对话任务一行」。

    supplements（2026-10-17 EB3 D1 交付面分层）：增补面条目列（`[{block, text}]`——
    split／attribution／citations／lineage 四类块）随行回读；正文（answer）不再含这些块，
    旁路展示随前端重设计落地（本轮只备通道）。
    """

    run_id: str
    question: str
    status: str
    answer: str | None
    followup_of: str
    created_at: str
    updated_at: str
    supplements: list[dict[str, Any]] | None = None


def _choice_of(body: ResumeBody) -> AskChoice:
    """resume 入参 → `AskChoice`（HTTP 词面→V2 形映射单点；形状 400 同点）。

    `kind:"clarify"`＝澄清回收（须携 `choice`，值＝挂起帧 options 点选项）；
    `kind:"approval"`＝外表越集审批（须携 `decision`；`approval_id` 透传留痕）。
    """
    if body.kind == _CLARIFY_KIND:
        value = (body.choice or "").strip()
        if not value:
            raise ApiError(
                status_code=400,
                code=CODE_PARAM_INVALID,
                message="clarify resume 须携 choice（挂起帧 options 点选项）",
            )
        return AskChoice(kind=_CLARIFY_KIND, choice=value)
    if body.decision is None:
        raise ApiError(
            status_code=400,
            code=CODE_PARAM_INVALID,
            message="approval resume 须携 decision（approve/reject）",
        )
    return AskChoice(
        kind=_APPROVAL_KIND, decision=body.decision, approval_id=body.approval_id
    )


@router.get("/runs")
async def list_runs(
    actor: CurrentActor, store: StoreDep, registry: RegistryDep, limit: int = 20
) -> list[RunListItem]:
    """GET /api/v2/chat/runs?limit=N → 最近 N 条任务（V2-73 会话历史读口）。

    created_at 降序；limit 夹取 1..100（越界静默夹取，不 400——只读面宽容）。
    **行集来源（本层装配形状——登记缺口）**：run 号集＝本进程 SSE 帧桥注册表
    （`RunStreamRegistry.run_ids`）；行投影＝persistence 读口 `RunStore.run`（既有
    读口组合——不改 persistence、不自造 SQL）。故持久库中**非本进程服务过**的历史
    run 不进列表（跨进程/重启后为空）——弱于「最近任务读口」的全量语义，补口
    （persistence 侧列表读口，如 `recent_runs(limit)`）呈主窗裁。
    """
    rows = [
        row
        for run_id in registry.run_ids()
        if (row := store.run(run_id)) is not None
    ]
    rows.sort(key=lambda row: row.created_at, reverse=True)
    wanted = max(1, min(limit, 100))
    return [
        RunListItem(
            run_id=row.run_id,
            question=row.question,
            status=row.status,
            answer=row.answer,
            followup_of=row.followup_of,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
            supplements=[dict(entry) for entry in row.supplements] or None,
        )
        for row in rows[:wanted]
    ]


@router.post("/asks")
async def post_ask(
    actor: CurrentActor,
    runtime: RuntimeDep,
    registry: RegistryDep,
    body: AskBody | None = None,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """POST /api/v2/chat/asks → text/event-stream（接口定义节第一行）。

    - 重连形态（resume_run_id 在场）：不重新执行——读本进程帧缓冲里 `seq ≥ cursor`
      的帧（run 不存在／不在本进程缓冲＝404；缓冲在 api 层进程内——跨进程重启后
      重放归 ADR-0003 队列消费者形态）；
    - 提问形态：question 必填非空（400）；每问新建 run（行为约定 1）；
    - 追问形态（question＋followup_run_id，V2-38）：会话线程新轮——前轮不存在
      404／未收口 409 在开流前抛（受理面同步段）。
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
        return StreamingResponse(
            sse_frames(
                stream,
                cursor=_cursor_of(breakpoint_id),
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
        AskRequest(question=question, actor=actor, followup_run_id=followup_run_id)
    )
    stream = registry.register(handle)
    return StreamingResponse(
        sse_frames(
            stream,
            cursor=handle.cursor,
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

    run 不存在 404／非挂起态 409 在开流前抛（受理面同步段——00 §3.1 流开前才有
    状态码）；入参形状 400 单点 `_choice_of`。响应只出**本腿**新帧：消费起点＝
    回执 `cursor`（＝本腿下一帧 `seq`——上一腿收口帧之后，跨腿续编不重启、
    不重放已完成部分）。
    """
    handle = await runtime.resume(run_id, _choice_of(body))
    stream = registry.register(handle)
    return StreamingResponse(
        sse_frames(
            stream,
            cursor=handle.cursor,
            session={"run_id": run_id, "resume": True},
        ),
        media_type="text/event-stream",
        headers=_STREAM_HEADERS,
    )


@router.get("/runs/{run_id}")
async def get_run(run_id: str, actor: CurrentActor, store: StoreDep) -> RunView:
    """GET /api/v2/chat/runs/{run_id} → {status, steps, manifest_digest, pending_ask?}
    （接口定义节第三行——run 历史/步详情回看，页面映射 A1 行）。

    步记录按 seq 升序直出（INV-5 存档形——Manifest 随模型调用步在场）；
    run 不存在 404（不泄漏存在性差异）。V2-78：waiting_ask 随行挂起帧
    （pending_ask——刷新后反问选项/审批面由此还原，读数源＝`RunState.pending_ask`
    经 persistence 读口 `RunStore.load`；非挂起＝None）。
    """
    row = store.run(run_id)
    if row is None:
        raise ApiError(
            status_code=404,
            code=CODE_RUN_NOT_FOUND,
            message=f"run 不存在：{run_id}",
        )
    steps = store.steps(run_id)
    pending = (
        store.load(run_id).pending_ask if row.status == RUN_WAITING_ASK else None
    )
    return RunView(
        pending_ask=pending,
        status=row.status,
        steps=[
            StepView(
                seq=step.seq,
                step=step.step,
                status=step.status,
                title=step.title,
                manifest=step.manifest,
                payload=step.payload,
            )
            for step in steps
        ],
        manifest_digest=row.manifest_digest,
    )
