"""appv2.api.bridge —— SSE 事件桥：runtime 帧流（`SseEvent`） ↔ 信封帧文本。

两端职责：

- **RunStream（per-run 帧缓冲）**：api 层是 `RunHandle.stream` 的唯一排空点——`ask`／`resume`
  各段帧流续拼进同一 run 缓冲，多消费者（原响应／断线重放／后连观察者）各凭游标读同一缓冲，
  互不抢占（AsyncIterator 单消费者限制在桥内收口）；
- **sse_frames（帧渲染）**：缓冲 → `id/event/data` 信封帧流——首帧 `session`（可选）→ 事件帧
  （**原样渲染，不重新编号**）→ 保留帧收场（`done`＝正常/挂起收束，`error`＝排空异常——
  00 §6.1 流内异常不发 HTTP 错误包）。

**编号与游标全部归 transport**（`specs/transport.md:154` 行原文「禁手写第二套帧通路」）：帧号
＝`SseEvent.seq`（事件帧＝本帧位次，一处编号、跨段不重启、重放不位移——行为 3）；wire 三帧
（`session`／`done`／`error`）不占号位，其 `seq`＝**最后已消费事件 `seq`**（本响应尚未消费事件
时＝流首 -1——行为 4）。本层**不建帧对象、不编号、不判 subtype**，只把帧渲染成 SSE 文本（渲染缝
单点＝`wire.render_event`／`wire.render_frame`，实现仍是 transport 的 `envelope`）。

游标语义（行为约定 8「断线凭游标续传」＋行为 5「`cursor`＝**下一帧的 `seq`**（排他起点）」）：
重连形态（`resume_run_id` ＋ `Last-Event-ID`）读本进程缓冲——缓冲里 `seq ≥ cursor` 的帧即原流
后缀，**不重复不遗漏**；游标取自客户端回送帧号换算（api 侧换算单点在 `chat.parse_last_event_id`）。
重放帧号与原流对齐（`seq` 原样），治旧自建编号「重放流自 L＋1 续枚举帧号」的历史缺陷。

error 帧只出稳定话术（specs/transport.md 行为 9／14：原始异常文本不进帧）——排空异常原文留在
`RunStream.error` 内部字段（对外留痕归 persistence／audit 其块），帧载荷定形恰二键
`{code, message}`。

进程内边界（如实声明）：缓冲存活于本进程——跨进程重放与缓冲淘汰归 ADR-0003 RunCommand seam 的
队列消费者形态（执行器换 Redis Stream 消费者时接口零改动，modules.md runtime 卡在案）；本层
范围＝单进程开发态全量可用。
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from appv2.api.errors import CODE_STREAM_FAILED
from appv2.api.wire import (
    FRAME_DONE,
    FRAME_ERROR,
    FRAME_SESSION,
    render_event,
    render_frame,
)
from appv2.runtimev2.orchestration import RunHandle
from appv2.runtimev2.transport import SseEvent

# 帧内稳定话术（specs/transport.md 行为 9：`error` 帧 `message` 为稳定话术、
# `code` 为稳定错误码；行为 14：任何帧不得携带内部堆栈／模块路径／SQL 文本）。
ERROR_FRAME_MESSAGE = "本次回答中断——请重新提问"

# wire 帧的流首号值：本响应尚未消费任何事件（行为 4——wire 帧 `seq`＝最后已消费事件 `seq`）。
FIRST_WIRE_SEQ = -1


class RunStream:
    """单 run 帧缓冲（api 层唯一排空点——游标续传的多消费者面）。"""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._frames: list[SseEvent] = []
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

    def attach(self, handle: RunHandle) -> None:
        """挂接一段帧流（ask/resume 各一段续拼同缓冲）——排空任务逐帧入缓冲，
        帧号原样（不重新编号）。"""
        self._active += 1
        task = asyncio.create_task(self._drain(handle))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def follow(self, cursor: int = 0) -> AsyncIterator[SseEvent]:
        """按游标消费缓冲（`cursor`＝下一帧 `seq` 的排他起点——行为 5）：给出 `seq ≥ cursor`
        的帧；流未收束且无新事件时等待——断线重放可尾随 running run。"""
        index = 0
        while True:
            while index < len(self._frames):
                frame = self._frames[index]
                index += 1
                if frame.seq >= cursor:
                    yield frame
            if self._active == 0:
                return
            async with self._condition:
                # 闭包读当前 index 是本处本意——谓词每次唤醒重估（等待期间无新
                # 消费，index 不漂移；B023 的循环误捕模式在此不成立）。
                await self._condition.wait_for(
                    lambda: index < len(self._frames) or self._active == 0  # noqa: B023
                )

    # ---------- 内部位 ----------

    async def _drain(self, handle: RunHandle) -> None:
        try:
            async for frame in handle.stream:
                async with self._condition:
                    self._frames.append(frame)
                    self._condition.notify_all()
        except Exception as exc:  # 流内异常如实留痕——error 帧收场（不静默）
            self._error = str(exc)
        finally:
            async with self._condition:
                self._active -= 1
                self._condition.notify_all()


class RunStreamRegistry:
    """run → 帧缓冲注册表（api 层进程内面——ask/resume 挂线、重放取回、列表面 run 号来源）。"""

    def __init__(self) -> None:
        self._streams: dict[str, RunStream] = {}

    def register(self, handle: RunHandle) -> RunStream:
        """挂接 run 帧流（同 run 二段＝续拼同缓冲）；返回该 run 的缓冲。"""
        stream = self._streams.get(handle.run_id)
        if stream is None:
            stream = RunStream(handle.run_id)
            self._streams[handle.run_id] = stream
        stream.attach(handle)
        return stream

    def get(self, run_id: str) -> RunStream | None:
        return self._streams.get(run_id)

    def run_ids(self) -> list[str]:
        """本进程服务过的 run 号（登记序——`GET /runs` 列表读口的 run 号来源；
        定序归其消费方，本口不定序、不改语义）。"""
        return list(self._streams)


async def sse_frames(
    stream: RunStream,
    *,
    cursor: int,
    session: dict[str, Any] | None,
) -> AsyncIterator[str]:
    """帧缓冲 → 信封帧流：首帧 session[可选] → 事件帧（原样号） → 保留帧收场。

    `cursor`＝本响应的事件消费起点（下一帧 `seq` 的排他起点——新流＝`RunHandle.cursor`，
    重放＝客户端回送帧号换算值）。收场帧号取**最后已消费事件 `seq`**：本响应出过事件帧＝
    其末帧号；一帧未出（客户端已追平）＝`cursor - 1`（客户端回送的那个帧号本身——**不后退**；
    回退会让客户端下一次重连从更早处重放，重复出帧）；流首尚无已消费事件＝-1。
    """
    last = FIRST_WIRE_SEQ if cursor <= 0 else cursor - 1
    try:
        if session is not None:
            yield render_frame(FIRST_WIRE_SEQ, FRAME_SESSION, session)
        async for frame in stream.follow(cursor=cursor):
            yield render_event(frame)
            last = frame.seq
        if stream.error is not None:
            yield render_frame(
                last,
                FRAME_ERROR,
                {"code": CODE_STREAM_FAILED, "message": ERROR_FRAME_MESSAGE},
            )
        else:
            yield render_frame(last, FRAME_DONE, {"run_id": stream.run_id})
    except Exception:  # 渲染面异常——error 帧收场后关流（00 §6.1；只用稳定话术）
        yield render_frame(
            last,
            FRAME_ERROR,
            {"code": CODE_STREAM_FAILED, "message": ERROR_FRAME_MESSAGE},
        )
