"""直答结构核验（闭世界判据）——行为 5／11；**只判结构，不猜语义**。

真源＝`specs/understanding.md` 行为 5：「`route="direct"` 时，若 `text` 含**数值形** → 判不合格
→ 退回 `route="full"`」：

1. **数值**：**≥1 位**连续阿拉伯数字形（**含全角**；含小数、百分号、千分位分隔一并算命中）。

**2026-10-18 V2-83 判据收窄（挂账 A1）**：指标名／表名单独出现**不再命中**——问候与能力介绍会
自然点名指标名（真机 `run-a11920fb`：「日产油量、产量完成率、抽油机时率」→ 误退 `full`），那是
介绍不是数据断言；只有**数值形**（真正的数据断言）才退回。

**闭世界外的生词不算命中**——这是结构判据，不做语义猜测（行为 5 末句）。形态处理（**豁免面**
＝形态处理，非语义词表／正则——`specs/understanding.md` 验收行 11 与风险 2）：

- **数值形**：先 NFKC 归一（全角数字→ASCII 数字形），再取 ASCII 数字字符集成员判定——不摘数、
  不做数值解析；小数点／百分号／千分位分隔是**该形态的组成部分**（`12.5%`／`1,000` 的命中由其中的
  数字位判定承载，孤立的标点不是数字形，不命中）。

**判据外的形态（不命中，如实登记）**：汉字数字（如「百分之五十」）不是阿拉伯数字形——规格原文
只认「阿拉伯数字形（含全角）」，本块不做数值语义归一（形态处理面零语义猜测）。

判据点**唯一**：`direct_assertion_hits` 是本块各面（分派、上报、留痕）共用的同一次判定产物——
命中即「不合格」，退回口径归 `interpret`（`route="full"` 的 `Understanding`，不抛错）。
"""

from __future__ import annotations

import unicodedata
from typing import Final, Literal

from appv2.runtimev2.state import RunState

# 命中项的 kind（机读上报 payload 的分类键；本块自有常量点）。
KIND_NUMERIC = "numeric_form"

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


def direct_assertion_hits(state: RunState, text: str) -> tuple[tuple[str, str], ...]:
    """直答结构核验：命中数值形的判据项（`(kind, token)` 逐条），**空元组＝合格（可直答）**。

    **2026-10-18 V2-83 判据收窄（挂账 A1）**：只认**数值形**（真正的数据断言）。指标名／表名
    单独出现**不再命中**——问候与能力介绍会自然点名指标名（真机 `run-a11920fb`：「日产油量、
    产量完成率、抽油机时率」→ 误退 `full`），那是介绍不是断言。命中即「直答里有数据断言」，
    由调用方退回 `route="full"`——本函数只判、不退回、不抛错、零状态写入。

    `state` 形参保留（调用面签名兼容）：收窄后判据不再读指标名录／结构卡两集合。
    """
    hits: list[tuple[str, str]] = []
    digit = numeric_form_hit(text)
    if digit:
        hits.append((KIND_NUMERIC, digit))
    return tuple(hits)


__all__ = [
    "KIND_NUMERIC",
    "direct_assertion_hits",
    "numeric_form_hit",
]
