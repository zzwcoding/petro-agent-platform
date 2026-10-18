"""V2-113 synth/S6 事件闭世界漂移看守（红先绿后）。

S6（`docs/runtime-refactor/synth/S6-事件与帧目录.md`）仍写「runtime 9 类」＋旧路径
`appv2/runtime/events.py`（V1 码面）；实点为 `appv2/runtimev2/transport/constants.py:19-35`
的 `EVENT_KINDS` **十类**（2026-10-17 EB3 D1 增第十类 `supplement`）。

三条判据（逐条机检）：
1. 「9 类／9 值／九类」零残留，旧路径 `appv2/runtime/events.py` 零残留；
2. §一 事件表逐行取值集合 ＝ 实点 `EVENT_KINDS`（含 `supplement`，恰十类）；
3. S6 引用的行号区间 `constants.py:19-35` 与实点逐行对得上（区间内即 `EVENT_KINDS` 定义）。
"""

from __future__ import annotations

import re
from pathlib import Path

from appv2.runtimev2.transport.constants import EVENT_KINDS

REPO = Path(__file__).resolve().parents[2]
S6 = REPO / "docs" / "runtime-refactor" / "synth" / "S6-事件与帧目录.md"
CONSTANTS = REPO / "appv2" / "runtimev2" / "transport" / "constants.py"

EVENT_ROW = re.compile(r"^\|\s*\d+\s*\|\s*`([a-z_]+)`\s*\|")


def _s6_text() -> str:
    return S6.read_text(encoding="utf-8")


def _section_one_rows() -> list[str]:
    """§一（事件闭世界）小节的表行事件名（按行序）。"""
    text = _s6_text()
    start = text.index("## 一、")
    end = text.index("## 二、")
    return [m.group(1) for line in text[start:end].splitlines() if (m := EVENT_ROW.match(line))]


def test_s6_has_no_nine_kind_or_old_path_residue() -> None:
    """「9 类／9 值／九类」与旧路径 `appv2/runtime/events.py` 零残留；新路径在场。"""
    text = _s6_text()
    for stale in ("9 类", "9类", "九类", "9 值", "appv2/runtime/events.py"):
        assert stale not in text, f"S6 仍残留旧口径 {stale!r}——实点为十类（含 supplement）"
    assert "十类" in text, "S6 未写明事件闭世界十类"
    assert "appv2/runtimev2/transport/constants.py" in text, (
        "S6 未引实点路径 transport/constants.py"
    )


def test_s6_event_table_matches_live_closed_world() -> None:
    """§一 表行取值集合 ＝ 实点 `EVENT_KINDS`（恰十类，含 `supplement`）。"""
    rows = _section_one_rows()
    assert len(rows) == 10, f"S6 §一 事件表 {len(rows)} 行 ≠ 实点十类"
    assert set(rows) == set(EVENT_KINDS), (
        f"S6 §一 表与实点 EVENT_KINDS 不一致：表多 {set(rows) - set(EVENT_KINDS)}／"
        f"表少 {set(EVENT_KINDS) - set(rows)}"
    )
    assert "supplement" in EVENT_KINDS and "supplement" in rows, "第十类 supplement 未入列"
    assert len(EVENT_KINDS) == 10, f"实点 EVENT_KINDS {len(EVENT_KINDS)} 值 ≠ 十类"


def test_s6_cited_line_range_matches_source() -> None:
    """S6 引的 `constants.py:19-35` 区间内即 `EVENT_KINDS` 定义（逐取值在场）。"""
    assert "constants.py:19-35" in _s6_text(), "S6 未引实点行号区间 constants.py:19-35"
    lines = CONSTANTS.read_text(encoding="utf-8").splitlines()
    span = "\n".join(lines[18:35])  # 1-based 19..35
    assert "EVENT_KINDS" in span and "frozenset(" in span, "19-35 区间未含 EVENT_KINDS 定义"
    for kind in EVENT_KINDS:
        assert f'"{kind}"' in span, f"19-35 区间内缺取值字面 {kind!r}"
