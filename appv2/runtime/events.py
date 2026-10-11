"""runtime.events —— RunEvent 流（V1 wire 形兼容＋loop 新形态）。

事件帧＝00 §6.1 信封 `id/event/data` 的流内最小单位：RunEvent{seq, event, data}
——seq 即断线游标（V2-07 SSE 游标续传消费）；event 九类闭世界（specs/modules.md
api 卡枚举）：step/text/tool/observation/ask/verdict/citation/notice/blackbox
（blackbox＝V2-54 黑匣子终态蒸馏——执行器收口单点发射，帧落盘自动收录）。

EventBus＝进程内事件流（asyncio.Queue）：节点发射、RunHandle.stream 消费；
ask 挂起帧发出后流正常收束（specs/agent-loop.md 行为约定 4）。本模块零框架
依赖（langgraph 禁入——ADR-0002 红线①；纯 stdlib asyncio）。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

# ---------- 事件八类闭世界（V1 wire 形兼容＋loop 步/观察新形态） ----------

EVENT_STEP = "step"
EVENT_TEXT = "text"
EVENT_TOOL = "tool"
EVENT_OBSERVATION = "observation"
EVENT_ASK = "ask"
EVENT_VERDICT = "verdict"
EVENT_CITATION = "citation"
EVENT_NOTICE = "notice"
EVENT_BLACKBOX = "blackbox"
EVENT_KINDS: frozenset[str] = frozenset(
    {
        EVENT_STEP,
        EVENT_TEXT,
        EVENT_TOOL,
        EVENT_OBSERVATION,
        EVENT_ASK,
        EVENT_VERDICT,
        EVENT_CITATION,
        EVENT_NOTICE,
        EVENT_BLACKBOX,
    }
)


@dataclass(frozen=True, slots=True)
class RunEvent:
    """事件帧（seq＝断线游标；event 八类闭世界；data wire 载荷）。"""

    seq: int
    event: str
    data: dict[str, Any]

    def __post_init__(self) -> None:
        if self.event not in EVENT_KINDS:
            raise ValueError(
                f"RunEvent.event 越界（八类闭世界 {sorted(EVENT_KINDS)}）：{self.event!r}"
            )


class EventBus:
    """进程内事件流：节点 emit、RunHandle.stream 消费（ask 后正常收束）。"""

    def __init__(self) -> None:
        self._events: list[RunEvent] = []
        self._queue: asyncio.Queue[RunEvent | None] = asyncio.Queue()
        self._closed = False

    def emit(self, event: str, data: dict[str, Any]) -> RunEvent:
        """发射事件（seq 自增即游标；close 后发射＝缺陷，拒收）。"""
        if self._closed:
            raise RuntimeError("EventBus 已收束——close 后不得再发射")
        run_event = RunEvent(seq=len(self._events), event=event, data=data)
        self._events.append(run_event)
        self._queue.put_nowait(run_event)
        return run_event

    def close(self) -> None:
        """收束事件流（run 终态/挂起收束后调用；幂等）。"""
        if not self._closed:
            self._closed = True
            self._queue.put_nowait(None)

    @property
    def closed(self) -> bool:
        return self._closed

    def snapshot(self) -> list[RunEvent]:
        """已发射事件快照（游标回看的进程内面——V2-07 断线续传消费）。"""
        return list(self._events)

    async def stream(self, cursor: int = 0) -> AsyncIterator[RunEvent]:
        """按游标消费事件流（cursor=断线前收到的最大 seq＋1；不重复不遗漏）。"""
        index = cursor
        while True:
            if index < len(self._events):
                yield self._events[index]
                index += 1
                continue
            item = await self._queue.get()
            if item is None:
                return
            if item.seq < index:  # 排队期间已被历史分支消费——跳过（不重复）
                continue
            yield item
            index = item.seq + 1
