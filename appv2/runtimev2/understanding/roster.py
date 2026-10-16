"""闭世界取值面（名录／结构卡两集合）——只经 `tools` 公开面，不直引引擎。

真源＝`specs/understanding.md` 行为 8（候选须出自**指标名录**：「`metric_candidates` 出现名录外
名字 → 判**违约**并如实上报（红线）；名录经 `tools` 的 `semantic_query` 取得、不直引引擎」）与
行为 5（直答结构核验的两集合面：**指标名录集合**／**结构卡集合**）；框架红线「**只经 `tools`
公开面**接触世界」＝边界闸 **R6**（`tools/importlinter_v2.toml`）。

取值面（本块实现口径，登记见票面回报）：
- **名录集合**＝台账投影键集 `slot ∪ 指标名 ∪ 别名`——由 `tools` 的**台账面公开函数**
  `appv2.tools.ledger_facts`（纯投影、零 I/O，同 `semantic_query` 与 `_resident_block` 共用的
  词典层 dump 族）解析 `state.ledger_dump`；
- **结构卡集合**＝投影 `cards` 键（真源＝`tools` 的 `table_schema` 发现面：`appv2.tools` 的卡清单
  经 `dump_from_store` 落进 dump）逐卡头名（全名＋短名两形态，提取口径同 `tools` 的卡名提取）。

`ledger_dump` 由 `context` 经 `tools` 公开面装载进 state（`specs/prompts.md` 行为 5 同源）；
本块**零引擎接触**（不 import `knowledge`／`query`／`retrieval`）、**零 I/O**、零名称归一（判据＝
**集合成员判定**，属形态处理豁免面——`specs/understanding.md` 风险 2）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from appv2.runtimev2.state import RunState
from appv2.tools import ledger_facts

# 卡头形（真源＝`tools` 卡清单的合同形「表/账/库 名（…」；本块只作形态切分，零语义词表）。
_CARD_HEAD_OPEN = "（"
_CARD_HEAD_SEP = " "
_SCHEMA_PREFIX_SEP = "."


def _projection(state: RunState) -> Mapping[str, Any]:
    """台账投影（缝缺省归一空投影——`None`／旧形按空投影计，同 V1-59 缝缺省口径）。"""
    dump = state.ledger_dump
    return dump if isinstance(dump, Mapping) else {}


def metric_roster(state: RunState) -> frozenset[str]:
    """指标名录集合（闭世界）：台账键＝`slot ∪ 指标名 ∪ 别名`，经 `tools` 公开台账面解析。

    空投影 → 空集合（「无名录」是合法态：任何候选都不在其中——判据面不降级、不网开一面）。
    """
    return frozenset(ledger_facts(_projection(state)).keys)


def _card_names(card: Any) -> tuple[str, ...]:
    """结构卡头名提取（全名＋去 schema 前缀短名两形态——口径同 `tools` 的卡名提取）。

    卡头合同形「表/账/库 名（…」：取全角括号前的头段、再去掉前导类名与空格。非字符串卡（旧形／
    残形）一律不计（不抛错、不猜——形态过滤零语义）；无名可提取 → 空元组。
    """
    if not isinstance(card, str):
        return ()
    head = card[: card.find(_CARD_HEAD_OPEN)] if _CARD_HEAD_OPEN in card else card
    sep_at = head.find(_CARD_HEAD_SEP)
    name = (head[sep_at + 1 :] if sep_at >= 0 else head).strip()
    if not name:
        return ()
    if _SCHEMA_PREFIX_SEP in name:
        return (name, name.rsplit(_SCHEMA_PREFIX_SEP, 1)[-1])
    return (name,)


def structure_cards(state: RunState) -> frozenset[str]:
    """结构卡集合（闭世界）：投影 `cards` 键逐卡头名（全名＋短名两形态）。

    卡面真源＝`tools` 的 `table_schema` 发现面（卡清单经 `tools` 落进活体投影，本块只读投影、
    零引擎接触）；空投影／无 `cards` 键 → 空集合（「无结构卡」是合法态：任何名字都不在其中——
    判据面不降级、不网开一面）。
    """
    cards = _projection(state).get("cards")
    if not isinstance(cards, Sequence) or isinstance(cards, str | bytes):
        return frozenset()
    names: set[str] = set()
    for card in cards:
        names.update(_card_names(card))
    return frozenset(names)
