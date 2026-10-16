"""appv2.api.wire —— wire 面适配（帧对象与信封的真源在 transport；本层只渲染）。

帧通路收口（specs/transport.md「框架与依赖红线」原文「**禁手写替代（不得自建
第二套帧通路）**：帧对象、信封、游标都只在本块实现；`api` 只做渲染」）：本模块
**不自建**帧对象与信封——`SseEvent`／`envelope` 与闭世界常量族一律取
`appv2.runtimev2.transport` 包根，帧信封字节形的唯一实现在该包 `frames.py`；
本层把帧渲染成 SSE 文本，不另立第二套编号或第二套 subtype 判别。

消费面（`specs/modules.md` `## api` 卡的「类型/常量形状面」——帧类型 SseEvent）：

- `FRAME_SESSION`／`FRAME_DONE`／`FRAME_ERROR`＝wire 三帧名（开流段 `session` 与
  收束段 `done`／`error` 的发射时机归本层——`specs/transport.md`「不做什么」表行；
  帧名闭世界与信封形状归 transport）；
- `WIRE_EVENT_KINDS`＝事件十二值全集（九 runtime＋三 wire）；
- `render_frame`＝帧→SSE 文本渲染缝（`id/event/data` 三行＋空行收束；中文不转义；
  非 JSON 原语兜底为字符串——三条都由 transport 的 `envelope` 单点保证）；
- `render_event`＝**已编号帧**的渲染缝（流内帧原样渲染——`seq` 由 transport 出帧面
  定死，本层不重新编号；`RunHandle.stream` 出来的帧走本缝）；
- verdict 帧的 `subtype` 注入同在该调用链内由 `SseEvent` 构造期单点完成
  （specs/transport.md 行为 6「唯一改造＝`verdict` 帧注入 `subtype` 键」）——
  本层零第二套判别（旧 `verdict_subtype` 单点随帧通路收口撤除）。

**编号语义（本层两缝的分工，真源 specs/transport.md 行为 3／4／5）**：事件帧的 `seq`
＝本帧位次（一处编号、跨段不重启、重放不位移）；wire 三帧（`session`／`done`／`error`）
不占 `seq` 号位——其 `seq`＝**最后已消费事件 `seq`**（本响应尚未消费事件时＝-1，即流首）。
故本层 wire 帧用 `render_frame(seq, ...)` 显式给号，事件帧用 `render_event(frame)` 原样渲染
（`id:` 行恒＝`frame.seq`，行为 4 两型同式）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from appv2.runtimev2.transport import (
    EVENT_KINDS,
    WIRE_FRAMES,
    SseEvent,
    envelope,
)

# ---------- 帧名（wire 三帧——取值真源 transport.WIRE_FRAMES） ----------

FRAME_SESSION = "session"
FRAME_DONE = "done"
FRAME_ERROR = "error"

# ---------- 事件类型集（runtime 九类闭世界＋wire 面三帧——V1 超集面） ----------

WIRE_EVENT_KINDS: frozenset[str] = EVENT_KINDS | WIRE_FRAMES


def render_frame(frame_id: int, event: str, data: Mapping[str, Any]) -> str:
    """帧→SSE 文本（信封字节形的唯一实现＝transport 的 `envelope`）。

    帧名越界与定形载荷（`notice`／`ask`／`error`）越界在帧构造期抛错
    （fail-closed，不静默丢弃、不降级）；verdict 帧的 `subtype` 注入同在构造期
    单点完成（本层不再注入）。本缝供本层**自产帧**（`session`／`done`／`error`
    三 wire 帧）用——号位由调用方按行为 4 给（流首＝-1、收场＝最后已消费事件 `seq`）。
    """
    return envelope(SseEvent(seq=frame_id, event=event, data=dict(data)))


def render_event(frame: SseEvent) -> str:
    """**已编号帧** → SSE 文本（帧号原样透传，不重新编号）。

    流内帧的 `seq` 由 transport 出帧面定死（事件帧＝本帧位次，跨段不重启、重放不位移——
    specs/transport.md 行为 3／4／5）；本层只渲染。治现状历史缺陷原文：「重放流自 L＋1
    续枚举帧号（重放帧号与原流不对齐……）」（`appv2/api/bridge.py` 旧自述）——改接后该处
    编号随运行时出帧面，本层零第二套计数器。
    """
    return envelope(frame)


__all__ = [
    "FRAME_DONE",
    "FRAME_ERROR",
    "FRAME_SESSION",
    "WIRE_EVENT_KINDS",
    "render_event",
    "render_frame",
]
