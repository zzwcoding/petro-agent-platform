"""事件通路：事件名闭世界（10 类）、事件总线、帧通路与断线续推

模块卡见 specs/modules.md 的 `## transport` 一节；规格见 `specs/transport.md`（形状真源）。
包根即公开面（`specs/modules.md` `## transport` 卡「公开接口」节）：帧对象 `SseEvent`／
per-run 总线 `EventBus`（`emit`／`stream`／`close`／`closed`）／信封 `envelope` ＋ 七个闭世界
常量族（`constants`，取值真源逐族注在该模块）＋ 块头模式族与块剥除单点（`blocks`，2026-10-17
EB5c——两相位共用的«四类块不进正文»文本判据面）。

本块只出「出去的那一帧长什么样、怎么编号、怎么续」——事件的本体与发帧时机在各发射方；
总线 per-run 由编排块持有并注入各相位，**不挂在状态上**（`RunState` 保持 JSON 可投影，
`specs/state.md` 行为 3）；帧→SSE 的渲染与断线游标接缝归 `api`。`blocks` 是块型闭世界的
**文本面**（形态处理单点：块头条判据与段剥离），不判业务语义、不发帧。
"""

from appv2.runtimev2.transport.blocks import (
    block_head_kind,
    same_family_head_in,
    split_block_sections,
    undecorated_head,
)
from appv2.runtimev2.transport.bus import EventBus
from appv2.runtimev2.transport.constants import (
    ASK_FRAME_KINDS,
    EVENT_KINDS,
    NOTICE_TYPES,
    SUPPLEMENT_BLOCK_ATTRIBUTION,
    SUPPLEMENT_BLOCK_CITATIONS,
    SUPPLEMENT_BLOCK_HEAD_MARKS,
    SUPPLEMENT_BLOCK_LINEAGE,
    SUPPLEMENT_BLOCK_SPLIT,
    SUPPLEMENT_BLOCKS,
    SUPPLEMENT_HEAD_DECORATIONS,
    SUPPLEMENT_HEAD_MARK_ATTRIBUTION,
    SUPPLEMENT_HEAD_MARK_CITATIONS,
    SUPPLEMENT_HEAD_MARK_CITATIONS_BARE,
    SUPPLEMENT_HEAD_MARK_LINEAGE_CLOSING,
    SUPPLEMENT_HEAD_MARK_LINEAGE_SOURCE,
    SUPPLEMENT_HEAD_MARK_SPLIT,
    SUPPLEMENT_HEAD_MARK_SPLIT_VERIFY,
    SUPPLEMENT_LINEAGE_HEAD_MARKS,
    SUPPLEMENT_LINEAGE_KEEP_MAX_LINES,
    SUPPLEMENT_PAYLOAD_BLOCK_KEY,
    SUPPLEMENT_PAYLOAD_TEXT_KEY,
    SUPPLEMENT_STRIPPABLE_BLOCKS,
    VERDICT_SUBTYPES,
    WIRE_FRAMES,
)
from appv2.runtimev2.transport.frames import SseEvent, envelope

__all__ = [
    "ASK_FRAME_KINDS",
    "EVENT_KINDS",
    "NOTICE_TYPES",
    "SUPPLEMENT_BLOCKS",
    "SUPPLEMENT_BLOCK_ATTRIBUTION",
    "SUPPLEMENT_BLOCK_CITATIONS",
    "SUPPLEMENT_BLOCK_HEAD_MARKS",
    "SUPPLEMENT_BLOCK_LINEAGE",
    "SUPPLEMENT_BLOCK_SPLIT",
    "SUPPLEMENT_HEAD_DECORATIONS",
    "SUPPLEMENT_HEAD_MARK_ATTRIBUTION",
    "SUPPLEMENT_HEAD_MARK_CITATIONS",
    "SUPPLEMENT_HEAD_MARK_CITATIONS_BARE",
    "SUPPLEMENT_HEAD_MARK_LINEAGE_CLOSING",
    "SUPPLEMENT_HEAD_MARK_LINEAGE_SOURCE",
    "SUPPLEMENT_HEAD_MARK_SPLIT",
    "SUPPLEMENT_HEAD_MARK_SPLIT_VERIFY",
    "SUPPLEMENT_LINEAGE_HEAD_MARKS",
    "SUPPLEMENT_LINEAGE_KEEP_MAX_LINES",
    "SUPPLEMENT_PAYLOAD_BLOCK_KEY",
    "SUPPLEMENT_PAYLOAD_TEXT_KEY",
    "SUPPLEMENT_STRIPPABLE_BLOCKS",
    "VERDICT_SUBTYPES",
    "WIRE_FRAMES",
    "EventBus",
    "SseEvent",
    "block_head_kind",
    "envelope",
    "same_family_head_in",
    "split_block_sections",
    "undecorated_head",
]
