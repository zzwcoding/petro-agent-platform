"""infra.clock 单测——B14 时间唯一出口与冻结 seam（不依赖外部服务）。"""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app.infra import clock

UTC = ZoneInfo("UTC")


def test_now_is_east8_naive() -> None:
    value = clock.now()
    assert value.tzinfo is None  # DB timestamp 无时区（99 §1.3）
    # 东八区本地时间：与 UTC 现刻换算一致（秒级容差）
    utc_now = datetime.now(tz=UTC)
    east8_now = utc_now.astimezone(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
    assert abs((east8_now - value).total_seconds()) < 5


def test_freeze_freezes_now_iso_and_display() -> None:
    with clock.freeze("2026-09-29T12:34:56"):
        assert clock.now() == datetime(2026, 9, 29, 12, 34, 56)
        assert clock.iso_now() == "2026-09-29T12:34:56"
        assert clock.display_now() == "2026-09-29 12:34"
        assert clock.display_now(fmt="%Y/%m/%d") == "2026/09/29"
    assert clock.iso_now() != "2026-09-29T12:34:56"  # 退出恢复实时


def test_freeze_converts_aware_to_east8_naive() -> None:
    # UTC 04:00 ＝ 东八区 12:00——00 §1.4 全平台东八区本地时间
    with clock.freeze(datetime(2026, 9, 29, 4, 0, tzinfo=UTC)):
        assert clock.now() == datetime(2026, 9, 29, 12, 0)


def test_freeze_nested_restores_outer() -> None:
    with clock.freeze("2026-01-01T00:00:00"):
        with clock.freeze("2026-12-31T23:59:59"):
            assert clock.now() == datetime(2026, 12, 31, 23, 59, 59)
        assert clock.now() == datetime(2026, 1, 1)  # 恢复外层，非实时


def test_freeze_restores_on_exception() -> None:
    try:
        with clock.freeze("2026-05-05T05:05:05"):
            assert clock.now() == datetime(2026, 5, 5, 5, 5, 5)
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert clock.now() != datetime(2026, 5, 5, 5, 5, 5)


def test_iso_shape_no_timezone_suffix() -> None:
    value = clock.iso_now()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value)  # 无 Z 后缀（00 §1.4）


def test_set_clock_pair_restore() -> None:
    def fixed() -> datetime:
        return datetime(2020, 2, 2, 2, 2, 2)

    previous = clock.set_clock(fixed)
    assert clock.now() == datetime(2020, 2, 2, 2, 2, 2)
    clock.set_clock(previous)
    assert clock.now() != datetime(2020, 2, 2, 2, 2, 2)
