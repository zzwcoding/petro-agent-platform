"""事件通路：事件名闭世界（9 类）、事件总线、帧通路与断线续推

模块卡见 specs/modules.md 的 `## transport` 一节；规格见 `specs/transport.md`（形状真源）。
包根即公开面（`specs/modules.md` `## transport` 卡「公开接口」节）：帧对象 `SseEvent`／
per-run 总线 `EventBus`（`emit`／`stream`／`close`／`closed`）／信封 `envelope` ＋ 五个闭世界
常量族（`constants`，取值真源逐族注在该模块）。

本块只出「出去的那一帧长什么样、怎么编号、怎么续」——事件的本体与发帧时机在各发射方；
总线 per-run 由编排块持有并注入各相位，**不挂在状态上**（`RunState` 保持 JSON 可投影，
`specs/state.md` 行为 3）；帧→SSE 的渲染与断线游标接缝归 `api`。
"""

from appv2.runtimev2.transport.bus import EventBus
from appv2.runtimev2.transport.constants import (
    ASK_FRAME_KINDS,
    EVENT_KINDS,
    NOTICE_TYPES,
    VERDICT_SUBTYPES,
    WIRE_FRAMES,
)
from appv2.runtimev2.transport.frames import SseEvent, envelope

__all__ = [
    "ASK_FRAME_KINDS",
    "EVENT_KINDS",
    "NOTICE_TYPES",
    "VERDICT_SUBTYPES",
    "WIRE_FRAMES",
    "EventBus",
    "SseEvent",
    "envelope",
]
