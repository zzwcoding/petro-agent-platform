"""appv2.api.bridge —— SSE 事件桥：runtime RunEvent 流 ↔ 00 §6.1 信封帧。

两端职责：
- RunStream（per-run 缓冲）：api 层是 handle.stream 的唯一排空点——ask/resume
  各段事件流续拼进同一 run 缓冲，多消费者（原响应/断线重放/后连观察者）各凭
  游标读同一缓冲，互不抢占（AsyncIterator 单消费者限制在桥内收口）；
- sse_frames（帧渲染）：缓冲 → `id/event/data` 信封帧流（`wire.render_frame`——
  帧对象与信封的唯一实现在 transport，本层只渲染），verdict 的 subtype 由该帧
  构造期单点注入（specs/transport.md 行为 6），流尾保留帧收场（done＝正常/
  挂起收束，error＝排空异常——00 §6.1 流内异常不发 HTTP 错误包）。

error 帧只出稳定话术（specs/transport.md 行为 9／14：原始异常文本不进帧）——
排空异常原文留在 `RunStream.error` 内部字段（对外留痕归 persistence／audit
其块），帧载荷定形恰二键 `{code, message}`。

游标语义（行为约定 8「断线凭游标续传」）：缓冲位 p 的帧号＝p＋1（session
首帧占 0）；Last-Event-ID＝客户端最后收到的帧号 L → 重放缓冲位 ≥ L 的事件，
不重复不遗漏。重放流自 L＋1 续枚举帧号（重放帧号与原流不对齐——能补的是
缓冲内容而非原流帧序，V1 重放同形，如实登记）。**帧号与游标的收口面**＝
transport 的出帧面（`EventBus.stream(cursor)`／`SseEvent.seq`——specs/
transport.md 行为 3／4／5「一处编号＋重放不位移」）——本层该处编号随运行时
出帧面（`RunHandle.stream`／`cursor`）改接一并移交，现形如实为响应内自编号。

进程内边界（如实声明）：缓冲存活于本进程——跨进程重放与缓冲淘汰归
ADR-0003 RunCommand seam 的队列消费者形态（执行器换 Redis Stream 消费者时
接口零改动，modules.md runtime 卡在案）；本票范围＝单进程开发态全量可用。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from appv2.api.errors import CODE_STREAM_FAILED
from appv2.api.wire import FRAME_DONE, FRAME_ERROR, FRAME_SESSION, render_frame
from appv2.runtime import RunEvent, RunHandle

# 帧内稳定话术（specs/transport.md 行为 9：`error` 帧 `message` 为稳定话术、
# `code` 为稳定错误码；行为 14：任何帧不得携带内部堆栈／模块路径／SQL 文本）。
ERROR_FRAME_MESSAGE = "本次回答中断——请重新提问"


class RunStream:
    """单 run 事件缓冲（api 层唯一排空点——游标续传的多消费者面）。"""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._events: list[RunEvent] = []
        self._condition = asyncio.Condition()
        self._error: str | None = None
        self._tasks: set[asyncio.Task[None]] = set()
        self._active = 0  # 在挂段数（>0＝流活着——ask/resume 各占一段）

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def closed(self) -> bool:
        return self._active == 0

    @property
    def error(self) -> str | None:
        """排空异常（None＝正常收束——帧渲染面据此选 error/done 保留帧）。"""
        return self._error

    def attach(self, handle: RunHandle) -> int:
        """挂接一段事件流（ask/resume 各一段续拼同缓冲）；返回挂接前缓冲长度
        （resume 段的起点游标——段响应只出本段新增事件）。"""
        mark = len(self._events)
        self._active += 1
        task = asyncio.create_task(self._drain(handle))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return mark

    async def follow(self, cursor: int = 0) -> AsyncIterator[RunEvent]:
        """按游标消费缓冲（cursor＝最后收到帧号 L → 供缓冲位 ≥ L 的事件；
        流未收束且无新事件时等待——断线重放可尾随 running run）。"""
        index = max(cursor, 0)
        while True:
            if index < len(self._events):
                yield self._events[index]
                index += 1
                continue
            if self._active == 0:
                return
            async with self._condition:
                # 闭包读当前 index 是本处本意——谓词每次唤醒重估（等待期间无新
                # 消费，index 不漂移；B023 的循环误捕模式在此不成立）。
                await self._condition.wait_for(
                    lambda: index < len(self._events) or self._active == 0  # noqa: B023
                )

    # ---------- 内部位 ----------

    async def _drain(self, handle: RunHandle) -> None:
        try:
            async for event in handle.stream:
                async with self._condition:
                    self._events.append(event)
                    self._condition.notify_all()
        except Exception as exc:  # 流内异常如实留痕——error 帧收场（不静默）
            self._error = str(exc)
        finally:
            async with self._condition:
                self._active -= 1
                self._condition.notify_all()


class RunStreamRegistry:
    """run → 事件缓冲注册表（api 层进程内面——ask/resume 挂线、重放取回）。"""

    def __init__(self) -> None:
        self._streams: dict[str, RunStream] = {}

    def register(self, handle: RunHandle) -> tuple[RunStream, int]:
        """挂接 run 事件流（同 run 二段＝续拼）；返回（流, 本段起点游标）。"""
        stream = self._streams.get(handle.run_id)
        if stream is None:
            stream = RunStream(handle.run_id)
            self._streams[handle.run_id] = stream
        return stream, stream.attach(handle)

    def get(self, run_id: str) -> RunStream | None:
        return self._streams.get(run_id)


async def sse_frames(
    stream: RunStream,
    *,
    first_frame_id: int,
    follow_cursor: int,
    session: dict[str, Any] | None,
) -> AsyncIterator[str]:
    """事件缓冲 → 信封帧流：首帧 session[可选] → 事件帧 → 保留帧收场
    （done＝正常/挂起；error＝排空异常，载荷定形恰二键 {code,message} 的稳定话术）。

    first_frame_id＝本响应首帧号（新流 0；重放＝断点＋1——V1 重放续枚举同形）；
    follow_cursor＝事件消费起点（新段＝挂接游标；重放＝断点帧号）。
    """
    idx = first_frame_id
    try:
        if session is not None:
            yield render_frame(idx, FRAME_SESSION, session)
            idx += 1
        async for event in stream.follow(cursor=follow_cursor):
            yield render_frame(idx, event.event, event.data)
            idx += 1
        if stream.error is not None:
            yield render_frame(
                idx,
                FRAME_ERROR,
                {"code": CODE_STREAM_FAILED, "message": ERROR_FRAME_MESSAGE},
            )
        else:
            yield render_frame(idx, FRAME_DONE, {"run_id": stream.run_id})
    except Exception:  # 渲染面异常——error 帧收场后关流（00 §6.1；只用稳定话术）
        yield render_frame(
            idx,
            FRAME_ERROR,
            {"code": CODE_STREAM_FAILED, "message": ERROR_FRAME_MESSAGE},
        )
