"""恢复时重取易变量（`specs/clarification.md` 行为 13／风险 3）。

清单（规格原文：数据水位／新鲜度／地基／落库新数据）＝`constants.VOLATILE_KEYS` 四键；
**每次调用现取、本块零缓存**——挂起期间可能变了的量必须从**活体投影**重取一遍
（治「等待期环境失效拿旧结论续跑」；真源 `docs/runtime-refactor/walk/10-澄清-澄清反问挂起.md`
§七 Q-B「要」）。

逐键读数面（皆**结构化**、零语义判断，读点单点在本模块）：

- `watermark`＝台账投影自带的水位值（缺位**如实空串**，不编造）；
- `freshness`＝台账投影各术语条的时效串集合（去重排序）；
- `foundation`＝台账投影本体三块（对象／关系／族标注）的行数——「地基」的行数面；
- `new_rows`＝已入栈观察（`state.observations`）条数——「落库新数据」的计数面。

同模块另持**台账名录读面** `ledger_name_rows`（名→行原文，指标／对象／关系／术语四类）——三段
槽位对账（行为 8，流水 64）的段一判据面与【台账相关行】取值面；与 `ledger_projection` 同源
（与常驻注入块同一投影，不新造第二名录源）。

**上游刷新义务不在本块**（本块只可及 `state` 投影）：真正向数据面重取水位／新鲜度并在恢复前
写回投影的调用链归 `orchestration` 的 `resume` 入口（`specs/clarification.md` 挂起契约：
「恢复经 `orchestration` 的 `resume` 入口」）——本块负责**重读**并把它落成机读信号
（步骤 payload 的 `volatile` 键），使「重取」可机检。登记项（呈主窗）：水位读写缝未落定
（与 `context` 的台账装载同族待核定）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from appv2.runtimev2.clarification.constants import VOLATILE_KEYS
from appv2.runtimev2.state import RunState

_FOUNDATION_BLOCKS: tuple[str, ...] = ("objects", "relations", "families")


def ledger_projection(state: RunState) -> Mapping[str, Any]:
    """台账活体投影（`state.ledger_dump`；缺位／非映射＝空投影，不编造）。

    读点单点：本模块的四项读数与「台账命中」机械半句（`core._rediscover_blocked`）同引此函数。
    """
    dump = state.ledger_dump
    return dump if isinstance(dump, Mapping) else {}


def _rows(collection: Any) -> list[Mapping[str, Any]]:
    """投影块的行集（只认映射行——旧检查点残形不计）。"""
    if not isinstance(collection, list):
        return []
    return [row for row in collection if isinstance(row, Mapping)]


# 名录名列（投影块 → 名键）：指标 slot／对象 obj／关系 rel／术语 term——三段槽位对账的段一
# 判据面（流水 64 裁：指标/对象/关系名集合；**术语条亦台账条目行**——2026-10-16 微批补入，
# 真机日志有术语名作段一的形；族标注名仍不在名录，登记项呈主窗）。
_NAME_COLUMNS: tuple[tuple[str, str], ...] = (
    ("metrics", "slot"),
    ("objects", "obj"),
    ("relations", "rel"),
    ("terms", "term"),
)


def ledger_name_rows(state: RunState) -> dict[str, str]:
    """台账名录面：名 → 行原文（三段槽位对账的段一判据面＋【台账相关行】取值面）。

    名取投影行结构列（`_NAME_COLUMNS`），行原文取同一行的 `value` 串（注入块渲染**逐字**用它
    ——本函数与 `render_ledger_resident_block` **同源**：皆自本模块的 `ledger_projection` 单点
    投影取数，**不新造第二名录源**）。缺列／非串／空串行如实跳过（不编造）；空投影＝空名录
    （判据侧 fail-closed：一切槽位皆判「不在台账名录」）。
    """
    dump = ledger_projection(state)
    rows: dict[str, str] = {}
    for block, key in _NAME_COLUMNS:
        for row in _rows(dump.get(block)):
            name = row.get(key)
            value = row.get("value")
            if isinstance(name, str) and name and isinstance(value, str):
                rows.setdefault(name, value)
    return rows


def _watermark_of(dump: Mapping[str, Any]) -> str:
    """数据水位读数（投影自带值；缺位＝如实空串）。"""
    value = dump.get("watermark")
    return value if isinstance(value, str) else ""


def _freshness_of(dump: Mapping[str, Any]) -> list[str]:
    """新鲜度读数：术语条时效串集合（去重排序）。"""
    values = {
        freshness
        for term in _rows(dump.get("terms"))
        if isinstance(freshness := term.get("freshness"), str) and freshness
    }
    return sorted(values)


def _foundation_of(dump: Mapping[str, Any]) -> int:
    """地基读数：本体三块（对象／关系／族标注）的行数。"""
    return sum(len(_rows(dump.get(block))) for block in _FOUNDATION_BLOCKS)


def read_volatile(state: RunState) -> dict[str, Any]:
    """四项易变量现取（行为 13）——键集恒为 `VOLATILE_KEYS`（越界即拒，fail-closed）。"""
    readings: dict[str, Any] = {
        "watermark": _watermark_of(ledger_projection(state)),
        "freshness": _freshness_of(ledger_projection(state)),
        "foundation": _foundation_of(ledger_projection(state)),
        "new_rows": len(state.observations),
    }
    unknown = sorted(set(readings) - set(VOLATILE_KEYS))
    if unknown:
        keys = "／".join(VOLATILE_KEYS)
        raise ValueError(f"易变量读数键越界（闭世界＝{keys}）：{unknown}")
    return readings
