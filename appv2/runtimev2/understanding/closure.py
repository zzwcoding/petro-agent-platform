"""直答结构核验（闭世界判据）——行为 5／11；**只判结构，不猜语义**。

真源＝`specs/understanding.md` 行为 5：「`route="direct"` 时，若 `text` 命中下列**任一闭世界** →
判不合格 → 退回 `route="full"`」：

1. **数值**：**≥1 位**连续阿拉伯数字形（**含全角**；含小数、百分号、千分位分隔一并算命中）；
2. **指标名**：属于**指标名录集合**的名字（经 `tools` 的 `semantic_query` 面取得的名录／别名面）；
3. **表名**：属于**结构卡集合**的名字（真源：`tools` 的 `table_schema` 发现面）。

**闭世界外的生词不算命中**——这是结构判据，不做语义猜测（行为 5 末句）。两处形态处理（**豁免面**
＝形态处理，非语义词表／正则——`specs/understanding.md` 验收行 11 与风险 2）：

- **数值形**：先 NFKC 归一（全角数字→ASCII 数字形），再取 ASCII 数字字符集成员判定——不摘数、
  不做数值解析；小数点／百分号／千分位分隔是**该形态的组成部分**（`12.5%`／`1,000` 的命中由其中的
  数字位判定承载，孤立的标点不是数字形，不命中）；
- **集合成员**：闭世界名字在文本中出现即命中（名字取自名录／结构卡两集合，本块不自建词表）。

**判据外的形态（不命中，如实登记）**：汉字数字（如「百分之五十」）不是阿拉伯数字形——规格原文
只认「阿拉伯数字形（含全角）」，本块不做数值语义归一（形态处理面零语义猜测）。

判据点**唯一**：`direct_assertion_hits` 是本块各面（分派、上报、留痕）共用的同一次判定产物——
命中即「不合格」，退回口径归 `interpret`（`route="full"` 的 `Understanding`，不抛错）。
"""

from __future__ import annotations

import unicodedata
from typing import Final, Literal

from appv2.runtimev2.state import RunState
from appv2.runtimev2.understanding.roster import metric_roster, structure_cards

# 命中项的两轴（kind 闭世界三值——机读上报 payload 的分类键；本块自有常量点）。
KIND_NUMERIC = "numeric_form"
KIND_METRIC = "metric_name"
KIND_TABLE = "table_name"

# 结构字符集（ASCII 数字位）——形态处理面，非语义词表。
_ASCII_DIGITS = "0123456789"
_NFKC: Final[Literal["NFKC"]] = "NFKC"


def numeric_form_hit(text: str) -> str:
    """数值形判据（行为 5 第 1 项）：命中返**原文**首位数字字面、无命中返空串。

    **≥1 位连续阿拉伯数字形**——逐字 NFKC 归一后按 ASCII 数字位取字（全角数字 `２０２６` 与 ASCII
    `2026` 落同一判据）；命中字面取**原文**那一位（如 `２` 而非归一的 `2`——判据点名逐字对应被判
    文本）。含小数／百分号／千分位的数值断言由其中的数字位承载。
    """
    for char in text:
        folded = unicodedata.normalize(_NFKC, char)
        if any(digit in _ASCII_DIGITS for digit in folded):
            return char
    return ""


def _name_hit(text: str, names: frozenset[str]) -> str:
    """集合成员判定（形态处理）：名字在文本中出现即命中——长的名字优先取**首个**命中（确定性）。

    取值序＝名字长度降序、同长按名字序（确定性；长者优先使点名落在更具体的那一名，如
    `日产油量` 先于其子串别名 `产油量`）。空名字不参与（空串恒在文本中——不构成成员判定）；
    无命中返空串。
    """
    for name in sorted(names, key=lambda item: (-len(item), item)):
        if name and name in text:
            return name
    return ""


def direct_assertion_hits(state: RunState, text: str) -> tuple[tuple[str, str], ...]:
    """直答结构核验：命中闭世界的判据项（`(kind, token)` 逐条），**空元组＝合格（可直答）**。

    三闭世界各取自真源面：数值形（形态判定）／指标名录集合（`metric_roster`——名录／别名面）／
    结构卡集合（`structure_cards`——`table_schema` 发现面）。命中即「直答里有数据或事实断言」，
    由调用方退回 `route="full"`——本函数只判、不退回、不抛错、零状态写入。
    """
    hits: list[tuple[str, str]] = []
    digit = numeric_form_hit(text)
    if digit:
        hits.append((KIND_NUMERIC, digit))
    metric = _name_hit(text, metric_roster(state))
    if metric:
        hits.append((KIND_METRIC, metric))
    table = _name_hit(text, structure_cards(state))
    if table:
        hits.append((KIND_TABLE, table))
    return tuple(hits)


__all__ = [
    "KIND_METRIC",
    "KIND_NUMERIC",
    "KIND_TABLE",
    "direct_assertion_hits",
    "numeric_form_hit",
]
