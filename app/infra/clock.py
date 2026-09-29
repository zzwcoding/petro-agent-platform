"""infra.clock —— 全平台时间唯一出口（B14：禁散用 datetime.now()）。

时间两类判据＝specs/api/00-系统级API.md §1.4（服务端/客户端是否参与计算）：
- 机器时间戳：ISO 8601「YYYY-MM-DDTHH:mm:ss」东八区本地时间、不带时区后缀——
  排序/TTL/保留窗口/跨端比对字段（started_at/expires_at/updated_at 等）。
  DB 时间列一律 timestamp 无时区（99 §1.3）——now() 产出东八区本地 naive datetime。
- 展示串时间：「YYYY-MM-DD HH:mm」等各册冻结粒度——直接进页面单元格、服务端
  不做计算；display_now() 拼装，不入库、不参与计算（R2）。

冻结 seam（测试回放）：freeze(at) 语境期内 now()/iso_now()/display_now() 恒返回
冻结时刻；退出语境恢复外层时钟，可嵌套。set_clock() 是低层替换缝（一般测试用
freeze 即可）。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

EAST8 = ZoneInfo("Asia/Shanghai")
ISO_FMT = "%Y-%m-%dT%H:%M:%S"
DISPLAY_FMT = "%Y-%m-%d %H:%M"

Clock = Callable[[], datetime]


def _realtime() -> datetime:
    return datetime.now(tz=EAST8)


_clock: Clock = _realtime


def _to_east8_naive(at: datetime) -> datetime:
    """统一为东八区本地 naive——DB timestamp 无时区（99 §1.3）/00 §1.4 无 Z 后缀。"""
    if at.tzinfo is not None:
        return at.astimezone(EAST8).replace(tzinfo=None)
    return at


def now() -> datetime:
    """机器时间戳：东八区本地 naive datetime——DB 时间列/计算字段的唯一来源。"""
    return _to_east8_naive(_clock())


def iso_now() -> str:
    """机器时间戳 ISO 8601 字符串（不带时区后缀——00 §1.4）。"""
    return now().strftime(ISO_FMT)


def display_now(fmt: str = DISPLAY_FMT) -> str:
    """展示串时间（缺省「YYYY-MM-DD HH:mm」——00 §1.4）；不入库不参与计算。"""
    return now().strftime(fmt)


def set_clock(clock: Clock | None) -> Clock:
    """低层 seam：替换/恢复时钟供给函数，返回先前的时钟（供成对恢复）。"""
    global _clock
    previous = _clock
    _clock = _realtime if clock is None else clock
    return previous


@contextmanager
def freeze(at: datetime | str) -> Iterator[datetime]:
    """冻结时钟回放：语境期内时间恒为 at（str 按 ISO 解析；naive 视为东八区）。

    可嵌套——内层退出恢复外层时钟，非必然回到实时。
    """
    frozen_at = _to_east8_naive(
        datetime.fromisoformat(at) if isinstance(at, str) else at
    )

    def frozen() -> datetime:
        return frozen_at

    previous = set_clock(frozen)
    try:
        yield frozen_at
    finally:
        set_clock(previous)
