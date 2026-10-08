"""appv2.api.wire —— SSE wire schema 定型（V2-07；specs/agent-loop.md 接口定义节
「事件枚举」与 R10 审查发现的落点）。

三段定型（本模块是 wire 形唯一真源，端点与事件桥只消费不另立）：
①帧信封＝00 §6.1 V1 wire 形：`id/event/data` 三行＋空行收束；帧序号即
  Last-Event-ID 断点依据；中文不转义（ensure_ascii=False）。
②事件类型集＝runtime 八类闭世界（step/text/tool/observation/ask/verdict/
  citation/notice——appv2.runtime.events 单源 re-export）＋wire 面三帧：
  session（首帧携 run_id——接口定义节「首帧 run_id」；V1 前端 applyFrame
  以 session 帧接线 run 上下文）＋done/error 保留帧（V1 客户端 streamChat
  只在保留帧上干净收流——web/ 零改动可连的机制判据）。
③verdict 拆 subtype（R10：verify 步与终局两形同挂 "verdict" 类型，消费面
  不再靠键猜载荷形态）：verify 载 {supported,rewritten,split,cited}、终局载
  {status,run_id,manifest_digest}；subtype 判别单点 verdict_subtype，事件桥
  据此把 `subtype` 键写进 wire 载荷（runtime 事件零改动——拆形只落 api 层）。

SSE 帧不携带 langgraph 类型（ADR-0002 红线①——载荷全 JSON 原语，本模块
零框架依赖；事件桥只透传 runtime RunEvent.data）。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from appv2.runtime import (
    EVENT_ASK,
    EVENT_CITATION,
    EVENT_KINDS,
    EVENT_NOTICE,
    EVENT_OBSERVATION,
    EVENT_STEP,
    EVENT_TEXT,
    EVENT_TOOL,
    EVENT_VERDICT,
)

# ---------- 帧信封（00 §6.1 V1 wire 形） ----------

FRAME_SESSION = "session"
FRAME_DONE = "done"
FRAME_ERROR = "error"

# ---------- 事件类型集（runtime 八类闭世界＋wire 面三帧——V1 超集面） ----------

WIRE_EVENT_KINDS: frozenset[str] = EVENT_KINDS | {FRAME_SESSION, FRAME_DONE, FRAME_ERROR}

# ---------- verdict subtype（R10 两形闭世界） ----------

VERDICT_VERIFY = "verify"
VERDICT_FINAL = "final"
VERDICT_SUBTYPES: frozenset[str] = frozenset({VERDICT_VERIFY, VERDICT_FINAL})


def verdict_subtype(data: Mapping[str, Any]) -> str:
    """verdict 载荷 subtype 判别单点：终局形携 status 键（verify 形无）。

    runtime 两发射点（graph.verify_node/answer_node）载荷键集互斥——按键判别
    是确定性分型，不是内容猜测；未知键集（runtime 契约外）判 verify 并在
    wire 载荷如实透传原键（不吞不猜）。
    """
    return VERDICT_FINAL if "status" in data else VERDICT_VERIFY


def render_frame(frame_id: int, event: str, data: Mapping[str, Any]) -> str:
    """00 §6.1 帧信封：`id/event/data` 三行＋空行收束（SSE 帧界）。

    帧序号即 Last-Event-ID 依据（00 §6.1）——续推断点按此回放；
    ensure_ascii=False（中文不转义，V1 render_frame 同形）；default=str 兜底
    （问数链表格答案含 Decimal/date 对象——V1 同款防流内异常）。
    """
    payload = json.dumps(dict(data), ensure_ascii=False, default=str)
    return f"id: {frame_id}\nevent: {event}\ndata: {payload}\n\n"


__all__ = [
    "EVENT_ASK",
    "EVENT_CITATION",
    "EVENT_KINDS",
    "EVENT_NOTICE",
    "EVENT_OBSERVATION",
    "EVENT_STEP",
    "EVENT_TEXT",
    "EVENT_TOOL",
    "EVENT_VERDICT",
    "FRAME_DONE",
    "FRAME_ERROR",
    "FRAME_SESSION",
    "VERDICT_FINAL",
    "VERDICT_SUBTYPES",
    "VERDICT_VERIFY",
    "WIRE_EVENT_KINDS",
    "render_frame",
    "verdict_subtype",
]
