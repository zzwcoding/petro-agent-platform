"""命令侧与事件侧的显式接缝：`RunCommand → 执行器 → RunEvent`（卡面 Seam，ADR-0003 预留件）。

本模块只落**接缝两端的形状**——命令一端的闭世界（`RunCommand.kind`＝`ask`｜`resume`）与事件
一端的**别名**（`RunEvent`＝`transport.SseEvent`，帧形状真源在 `transport`：本块不定义第二套帧
形状、也不给它安第二套含义）。将来执行器换队列消费者（Redis Stream 等），`api`／`tools`／事件
契约零改动——这正是本 seam 存在的理由。

受理三形状（`AskRequest`／`AskChoice`／`RunHandle`）的真源在 `state`（`specs/state.md` 接口定义
节），本模块只做**对象面→命令面**的投影（`actor` 对象→行级身份字符串的转换点唯一在编排受理段，
`specs/state.md`「依赖与风险」5）。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from appv2.infra.security import Actor
from appv2.runtimev2.orchestration.constants import (
    COMMAND_ASK,
    COMMAND_KINDS,
    COMMAND_RESUME,
    NEW_RUN_PREFIX,
)
from appv2.runtimev2.state import AskChoice, AskRequest, RunHandle
from appv2.runtimev2.transport import SseEvent

__all__ = [
    "COMMAND_ASK",
    "COMMAND_KINDS",
    "COMMAND_RESUME",
    "RunCommand",
    "RunEvent",
    "RunHandle",
    "ask_command",
    "new_run_id",
    "resume_command",
]

# 事件侧别名：帧形状真源＝`transport.SseEvent`（本块零第二定义——同物异名，非第二套形状）。
RunEvent = SseEvent


@dataclass(frozen=True, slots=True)
class RunCommand:
    """run 命令（两态闭世界：`ask` 受理新问／`resume` 带回挂起选择）。

    三形态在命令面上的落法（`specs/agent-loop.md` 接口定义节）：①提问＝`ask`＋`question`；
    ②断线重连＝`ask`＋`resume_run_id`（复用既有 run 的流，不新起 run）；③追问续会话＝`ask`＋
    `question`＋`followup_of`（新 run 播种前轮检查点终链）。`resume` 命令＝挂起恢复（`run_id`＋
    `choice`）。
    """

    kind: str
    question: str = ""
    actor: Actor | None = None
    run_id: str = ""
    choice: AskChoice | None = None
    followup_of: str = ""

    def __post_init__(self) -> None:
        if self.kind not in COMMAND_KINDS:
            values = "／".join(sorted(COMMAND_KINDS))
            raise ValueError(f"RunCommand.kind 越界（闭世界＝{values}）：{self.kind!r}")


def new_run_id() -> str:
    """run 号（机器短 id 族 `run-`——同族既有形态）。"""
    return f"{NEW_RUN_PREFIX}{uuid.uuid4().hex[:8]}"


def ask_command(request: AskRequest) -> RunCommand:
    """`AskRequest` → `ask` 命令（三形态逐形照实投影，不猜、不补默认）。"""
    return RunCommand(
        kind=COMMAND_ASK,
        question=request.question or "",
        actor=request.actor,
        run_id=request.resume_run_id or "",
        followup_of=request.followup_run_id or "",
    )


def resume_command(run_id: str, choice: AskChoice) -> RunCommand:
    """`(run_id, AskChoice)` → `resume` 命令。"""
    return RunCommand(kind=COMMAND_RESUME, run_id=run_id, choice=choice)


def choice_payload(choice: AskChoice) -> dict[str, Any]:
    """`AskChoice` → 状态投影四键（`state.resume_choices` 条目形；相位侧读面在 `clarification`
    `_resume_choice`——按键读、按 `kind` 判，本投影与之同形）。"""
    return {
        "kind": choice.kind,
        "choice": choice.choice,
        "decision": choice.decision,
        "approval_id": choice.approval_id,
    }


def handle_of(run_id: str, stream: Any, *, cursor: int = 0) -> RunHandle:
    """受理回执（`RunHandle` 形状真源 `state`）：`cursor`＝全流单调断线游标＝下一帧 `seq`。"""
    return RunHandle(run_id=run_id, stream=stream, cursor=cursor)
