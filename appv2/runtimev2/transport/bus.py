"""per-run 事件总线（编排块持有、注入各相位——**总线不挂在状态上**：`RunState` 必须保持
JSON 原语可投影，见 `specs/state.md` 行为 3）。

一处编号（行为 3／4）：

- **事件帧**（`EVENT_KINDS` 十类）占游标号位——`seq` ＝本总线**事件计数**（0 起、严格递增、
  无跳号；跨段不重启、重放不位移）；「响应内不再另起计数器」治现状「首段／resume 段／重放流
  三套编号互不同源」的历史缺陷（`walk/裁决表.md` §01-A）。
- **wire 三帧**（`session`／`done`／`error`）不推进事件游标、**不占 `seq` 号位**——其 `seq`
  ＝**最后已消费事件 `seq`**（尚未消费任何事件时＝-1）；故 wire 帧 `id` 可与前帧相同、且不改动
  续传位置（行为 4）。`specs/transport.md:110` 与 `docs/runtime-refactor/spec-review/
  transport-回工补写.md` §遗留 2「wire 帧不占 `seq`」同口径。
- 由此信封 `id:` 行对两类帧同式＝`frame.seq`，客户端换算 `cursor = id + 1` 不分型成立
  （行为 5）：断点落在事件帧或 wire 帧，都从**最后已消费事件之后**续传，不漏不重。

断线续推（行为 5）：`cursor` ＝**下一帧的 `seq`**（排他起点，等价 `recon/K` R-K-49「已收最大
`seq` ＋ 1」）；`stream(cursor)` 给出 `seq ≥ cursor` 的**全部帧**（历史里的与后续新到的），
不重复、不遗漏。多消费者各自持有自己的游标（行为 11）——**收束由「已关闭且无新帧」判定，
不依赖一次性哨兵**（治现状「哨兵单发→第二名消费者永久等待」的缺陷）。

wire 帧重放面（归 `api` 开流段——`transport-回工补写.md` §遗留 2「本规格未显名」）：段首
`session` 帧因「尚未消费任何事件」而 `seq`＝-1，落在 `stream(0)` 起点之前，故**不入任何重放
后缀**；开流段的 wire 帧（流首 `session`／流末 `done`／`error`）由发射方以 `emit` 返回值直接
渲染（本块只出帧与信封）。
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from appv2.runtimev2.transport.constants import WIRE_FRAMES
from appv2.runtimev2.transport.frames import SseEvent


class EventBus:
    """per-run 帧总线：`emit` 出帧、`stream` 按游标读帧、`close` 收束（幂等）。"""

    def __init__(self) -> None:
        self._frames: list[SseEvent] = []
        self._event_count = 0
        self._closed = False
        self._waiters: list[asyncio.Future[None]] = []

    def emit(self, name: str, payload: dict[str, Any]) -> SseEvent:
        """出一帧：帧名越界／定形载荷越界在构造期抛错（fail-closed，不留半帧）。

        wire 帧不推进事件游标（`seq` 取最后已消费事件 `seq`）；`close` 之后再 `emit` 抛错
        （不静默丢弃——行为 12）。
        """
        if self._closed:
            raise RuntimeError(
                f"总线已关闭：close 后再 emit 抛错（不静默丢弃，行为 12）——{name!r}"
            )
        seq = self._event_count - 1 if name in WIRE_FRAMES else self._event_count
        frame = SseEvent(seq=seq, event=name, data=payload)  # 越界在此抛错，历史未被改动
        if name not in WIRE_FRAMES:
            self._event_count += 1
        self._frames.append(frame)
        self._wake()
        return frame

    def stream(self, cursor: int = 0) -> AsyncIterator[SseEvent]:
        """读帧：给出 `seq ≥ cursor` 的全部帧（含历史与后续新到），直到「已关闭且无新帧」。

        `cursor` ＝下一帧的 `seq`（排他起点）；负数＝非法 `cursor` → 抛错（错误契约）。
        """
        if cursor < 0:
            raise ValueError(
                f"非法 cursor（cursor＝下一帧 seq，须 ≥ 0——行为 5 排他起点）：{cursor}"
            )
        return self._iterate(cursor)

    def close(self) -> None:
        """收束：幂等（重复 `close` 不重复投递终止信号）；消费者以「已关闭且无新帧」收束。"""
        if self._closed:
            return
        self._closed = True
        self._wake()

    @property
    def closed(self) -> bool:
        return self._closed

    async def _iterate(self, cursor: int) -> AsyncIterator[SseEvent]:
        index = 0
        while True:
            while index < len(self._frames):
                frame = self._frames[index]
                index += 1
                if frame.seq >= cursor:
                    yield frame
            if self._closed:
                return
            await self._wait_new()

    async def _wait_new(self) -> None:
        future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self._waiters.append(future)
        await future

    def _wake(self) -> None:
        """唤醒全部等待者（各自重查状态——无一次性哨兵，行为 11）。"""
        waiters, self._waiters = self._waiters, []
        for future in waiters:
            if not future.done():
                future.set_result(None)


__all__ = ["EventBus"]
