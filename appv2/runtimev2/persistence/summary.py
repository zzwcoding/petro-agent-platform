"""截断单点：审计摘要与黑匣子转写文本的长度边界（截断必可见——行为 13）。

真源＝`docs/runtime-refactor/recon/J-存储留痕与网关缝.md`：审计 `facts` 摘要长度 **R-J-06**
（`SUMMARY_LIMIT=120`，空白折叠后按字符数计——R-J-63 全部空白〔含换行〕折叠为单空格）；黑匣子
单行摘要长度 **R-J-60**（换行替换为 `" ⏎ "`，**按替换后的字符数计**）；转写分面长度 **R-J-62**
（title 30〔process_notes〕／60〔steps〕、digest 80、source 40、content 与通用值 96）。

截断**恒留可见标记** `"…"`（不静默截断），且**标记计入长度上限**——真源值即输出上限（
`specs/persistence.md` 行为 13「输出带截断标记且长度受控（判据＝真源值）」，本块口径：输出
`len ≤ limit`；V1 旧码为 `text[:limit] + "…"` 即 limit+1，本块按规格判据取 ≤limit）。

本模块零判断（行为 15）：只有长度边界与空白／换行归一，**无词表、无正则、无语义判定、无模型调用**。
"""

from __future__ import annotations

from collections.abc import Mapping

SUMMARY_LIMIT = 120  # 审计 facts 摘要（R-J-06）
BLACKBOX_LINE_LIMIT = 96  # 黑匣子单行摘要缺省（R-J-60）
TRUNCATION_MARK = "…"  # 截断可见标记（R-J-60／R-J-63）
BLACKBOX_NEWLINE_MARK = " ⏎ "  # 黑匣子转写换行替换（R-J-60）

# 转写分面长度（R-J-62）：title 按族有别（process_notes 30／steps 60）——分面名即族名。
FACET_LIMITS: Mapping[str, int] = {
    "title_process_notes": 30,
    "title_steps": 60,
    "digest": 80,
    "source": 40,
    "content": BLACKBOX_LINE_LIMIT,
}


def clip(text: str, limit: int) -> str:
    """按字符数截断：≤ limit 原样返回；超长 → 内容切至 `limit - 1` ＋可见标记（总长恒 ≤ limit）。"""
    return text if len(text) <= limit else text[: limit - len(TRUNCATION_MARK)] + TRUNCATION_MARK


def summarize(text: str, limit: int = SUMMARY_LIMIT) -> str:
    """审计摘要单点：空白折叠为单空格（R-J-63）＋超长截断可见（R-J-06 长度）。"""
    return clip(" ".join(text.split()), limit)


def head(value: str, limit: int = BLACKBOX_LINE_LIMIT) -> str:
    """黑匣子单行摘要单点：换行替换 `" ⏎ "` 后按字符数计（R-J-60）＋超长截断可见。"""
    return clip(value.replace("\n", BLACKBOX_NEWLINE_MARK), limit)


def facet_head(facet: str, value: str) -> str:
    """转写分面截断（R-J-62 分面长度）；分面未在册 → 按通用单行值（`BLACKBOX_LINE_LIMIT`）。"""
    return head(value, FACET_LIMITS.get(facet, BLACKBOX_LINE_LIMIT))
