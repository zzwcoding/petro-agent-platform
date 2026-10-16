"""指标名录取值面（行为 8 的闭世界集合）——只经 `tools` 公开面，不直引引擎。

真源＝`specs/understanding.md` 行为 8：「候选须出自名录：`metric_candidates` 出现名录外名字 →
判**违约**并如实上报（红线）；名录经 `tools` 的 `semantic_query` 取得、不直引引擎」；框架红线
「**只经 `tools` 公开面**接触世界」＝边界闸 **R6**（`tools/importlinter_v2.toml`）。

取值面（本块实现口径，登记见票面回报）：台账投影键集＝`slot ∪ 指标名 ∪ 别名`——由 `tools` 的
**台账面公开函数** `appv2.tools.ledger_facts`（纯投影、零 I/O，同 `semantic_query` 与
`_resident_block` 共用的词典层 dump 族）解析 `state.ledger_dump`。`ledger_dump` 本身由
`context` 经 `tools` 公开面装载进 state（`specs/prompts.md` 行为 5 同源）；本块**零引擎接触**
（不 import `knowledge`／`query`／`retrieval`）、**零 I/O**、零名称归一（判据＝**集合成员判定**，
属形态处理豁免面——`specs/understanding.md` 风险 2）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from appv2.runtimev2.state import RunState
from appv2.tools import ledger_facts


def _projection(state: RunState) -> Mapping[str, Any]:
    """台账投影（缝缺省归一空投影——`None`／旧形按空投影计，同 V1-59 缝缺省口径）。"""
    dump = state.ledger_dump
    return dump if isinstance(dump, Mapping) else {}


def metric_roster(state: RunState) -> frozenset[str]:
    """指标名录集合（闭世界）：台账键＝`slot ∪ 指标名 ∪ 别名`，经 `tools` 公开台账面解析。

    空投影 → 空集合（「无名录」是合法态：任何候选都不在其中——判据面不降级、不网开一面）。
    """
    return frozenset(ledger_facts(_projection(state)).keys)
