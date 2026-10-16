"""黑匣子的回放面（框架无关）：通道投影＋旧记录如实读入。

真源＝`specs/persistence.md` 行为 12（旧 run **黑匣子回放**如实——本块**唯一**挂断言的面；
「检查点状态字段读入」面挂 `specs/state.md` 行为 8，两处对象不同）＋`recon/J` 黑匣子两清单
（R-J-02 蒸馏白名单 20 键／R-J-04 回放曲面通道白名单 26 元素＝20 键超集＋六通道）＋
R-J-50 身份面四键。

旧条目如实空显：v1 旧条目的 `dialogue` 只有 `{role, content}`、无来源标签（`recon/I2b`）——
**补标即伪造历史**，故回放面不承接（对话通道空显），且**不改写落盘原文**（本模块只读投影，
零写入路径）。
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from appv2.runtimev2.persistence.models import BLACKBOX_IDENTITY_KEYS, BLACKBOX_RECORD_KEYS
from appv2.runtimev2.state import DIALOGUE_ORIGINS

DIALOGUE_CHANNEL = "dialogue"

# ── 回放面通道白名单（真源 recon/J R-J-04 26 元素＝20 蒸馏键＋六通道；另并身份面 R-J-50
#    ——回放视图须能自证属于哪个 run，身份四键中 `question`／`status`／`error` 已在 26 内，
#    `run_id` 为本次并入的唯一新元素）──────────────────────────────────────────────
REPLAY_EXTRA_CHANNELS: tuple[str, ...] = (
    "question",
    "understanding",
    "tool_matches",
    "subtask_results",
    "error",
    "status",
)
REPLAY_CHANNELS: frozenset[str] = (
    frozenset(BLACKBOX_RECORD_KEYS)
    | frozenset(REPLAY_EXTRA_CHANNELS)
    | frozenset(BLACKBOX_IDENTITY_KEYS)
)

# v2 对话条目形态＝固定三键 `{role, content, origin}`（`specs/state.md` 行为 6）
V2_DIALOGUE_ENTRY_KEYS: frozenset[str] = frozenset({"role", "content", "origin"})


def is_v2_dialogue_entry(entry: Any) -> bool:
    """v2 条目判据：固定三键 ＋ `origin` 落来源闭世界（缺来源标签的旧条目＝非 v2 条目）。"""
    return (
        isinstance(entry, dict)
        and set(entry) == V2_DIALOGUE_ENTRY_KEYS
        and entry["origin"] in DIALOGUE_ORIGINS
    )


def dialogue_channel(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """对话通道回放投影：只承接 v2 三键条目；旧条目／非列表**如实空显**（不伪造补写）。"""
    entries = record.get(DIALOGUE_CHANNEL, [])
    if not isinstance(entries, list):
        return []
    return [deepcopy(entry) for entry in entries if is_v2_dialogue_entry(entry)]


def replay_channels(record: Mapping[str, Any]) -> dict[str, Any]:
    """回放面通道投影：键只取回放白名单（`REPLAY_CHANNELS`＝R-J-04 曲面 26 元素＋身份面
    `run_id`，越界键不回放）；缺键不炸；`dialogue` 通道**如实空显**（旧条目无来源标签，不承接、
    不补标）。"""
    channels: dict[str, Any] = {}
    for key in [*BLACKBOX_IDENTITY_KEYS, *BLACKBOX_RECORD_KEYS, *REPLAY_EXTRA_CHANNELS]:
        if key not in record:
            continue
        channels[key] = (
            dialogue_channel(record) if key == DIALOGUE_CHANNEL else deepcopy(record[key])
        )
    return channels
