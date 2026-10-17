"""块头模式族与块剥除（2026-10-17 EB5c）——「程序块不进正文」的**文本形态单点**。

真源＝`specs/transport.md` 行为 17（块头模式族与块剥除单点）＋`specs/answering.md` 行为 13
（起草面块剥除）＋`specs/verification.md` 行为 1（核验剥除拍）。动因（真机帧形）＝
`docs/runtime-refactor/proposals/EB3-交付面分层与缺陷修复.md` D1／D2 的「四类块不进正文」在
**模型自身把块写进草稿**时漏网：模型把引用清单写成 markdown 加粗变体 `**引用**`（真机帧
`eval/results/frames/EB3-NQ-M7.json` 的 text 帧），按**固定字面**（`"\\n\\n引用：\\n"`）的剥除
判据不命中，块随正文交付（EB3 全量复跑唯一泄漏题）。

**两相位共用本单点**：`answering`（起草面，text 帧发出前）与 `verification`（剥除拍）各有一处
块剥除，判据面（族取值 ＋ 块头条判据 ＋ 段剥离）**同源在本模块**——两相位互不 import（R1），
故单点落块型闭世界所在的 `transport`（本模块＝该闭世界的**文本面**，只做形态处理：装饰归一、
行首／行内记号命中、段界切分——零正则、零词表、零语义判定、零 IO）。

**判据两条**（`block_head_kind`）：引用／分源／归属三族＝「装饰归一后整行恰为族中记号」；
血缘族＝「行内**含**记号」（2026-10-17 EB3 D2 逐字判据，逐字文稿面见 `specs/verification.md`
行为 1）。**剥除面**＝`SUPPLEMENT_STRIPPABLE_BLOCKS`（引用清单／血缘五要素）——分源／归属两族
只作「同族块头在场」判据，不剥（依据见该常量注）。
"""

from __future__ import annotations

import unicodedata

from appv2.runtimev2.transport.constants import (
    SUPPLEMENT_BLOCK_HEAD_MARKS,
    SUPPLEMENT_BLOCK_LINEAGE,
    SUPPLEMENT_HEAD_DECORATIONS,
    SUPPLEMENT_LINEAGE_HEAD_MARKS,
    SUPPLEMENT_LINEAGE_KEEP_MAX_LINES,
    SUPPLEMENT_STRIPPABLE_BLOCKS,
)

_OPEN_BRACKET = "["
_CLOSE_BRACKET = "]"
_DIGITS = "0123456789"


def _lines(text: str) -> list[str]:
    """正文逐行（非字符串入参＝空段——本块不做 `str()` 折叠：静默字符串化会掩盖调用方缺陷）。

    AST 闸（`tests/domains/test_v2_transport.py::no_internal_leak_in_frames` 行 15）禁本块
    出现 `str(` 调用（字符串化＝内部痕迹文本的构造位点）——故此处以 `isinstance` 把守。
    """
    return text.splitlines() if isinstance(text, str) else []


def undecorated_head(line: str) -> str:
    """块头行装饰归一（去 markdown 强调／标题记号与首尾空白——**加粗变体的归一面**）。

    `**引用**`／`## 引用：` → `引用`／`引用：`；非块头行照原样归一（不做其它改写）。
    """
    return line.strip().strip(SUPPLEMENT_HEAD_DECORATIONS).strip()


def block_head_kind(line: str) -> str | None:
    """行 → 块型（块头条判据；无命中＝`None`；取值 ∈ `SUPPLEMENT_BLOCKS`）。

    引用／分源／归属三族：装饰归一后**整行恰为**族中记号＝块头条（行内续写的散文不作数——
    「引用《月报》的数据说明…」零命中）；血缘族：**行内**含要素键记号（EB3 D2 逐字判据）。
    """
    head = undecorated_head(line)
    for block, marks in SUPPLEMENT_BLOCK_HEAD_MARKS.items():
        if block == SUPPLEMENT_BLOCK_LINEAGE:
            if any(mark in line for mark in marks):
                return block
            continue
        if head in marks:
            return block
    return None


def split_block_sections(text: str) -> tuple[str, str]:
    """正文 →（去除程序块段后的正文, 血缘族段文本）——**块剥除单点**（两相位同判据同语义）。

    段界＝空行界（连续非空行为一段）。命中判据与归属：

    - 段内任一行命中血缘族（行内判据）且**不是**口径说明例外 → 该段**整段离场**，原文进返回值
      第二项（调用方按 `lineage` 增补面发射——EB3 D2「整段入增补面、零二次创作」）；
    - 否则段首行命中剥除面块型（`SUPPLEMENT_STRIPPABLE_BLOCKS`）→ 该段整段离场（引用清单是
      程序机械再生产物，被引集由正文引标与核验支撑集确定）；
    - 其余段落原样保留（含分源／归属族段落——它们可能承载模型逐源作答正文）。

    **口径说明例外**（EB3 D2 逐字）：血缘族段行数 ≤ `SUPPLEMENT_LINEAGE_KEEP_MAX_LINES` 且段内
    携 `[n]` 引标 → 保留正文（口径说明不是血缘卡）。剥出段之间以空行连接（原文照抄）。
    """
    lines = _lines(text)
    keep: list[str] = []
    stripped: list[str] = []
    index = 0
    total = len(lines)
    while index < total:
        if not lines[index].strip():
            keep.append(lines[index])
            index += 1
            continue
        end = index
        while end < total and lines[end].strip():
            end += 1
        paragraph = lines[index:end]
        if _lineage_paragraph(paragraph):
            stripped.append("\n".join(paragraph))
        elif (
            block_head_kind(paragraph[0]) in SUPPLEMENT_STRIPPABLE_BLOCKS
            and not any(
                block_head_kind(line) == SUPPLEMENT_BLOCK_LINEAGE for line in paragraph
            )
        ):
            pass  # 剥除面块段：整段离场（原文零留存——程序块由交付面机械再生）
        else:
            keep.extend(paragraph)
        index = end
    return "\n".join(keep), "\n\n".join(stripped)


def _lineage_paragraph(paragraph: list[str]) -> bool:
    """血缘族段判定：段内任一行含要素键记号 且 非口径说明例外（例外保留正文）。"""
    if not any(
        block_head_kind(line) == SUPPLEMENT_BLOCK_LINEAGE for line in paragraph
    ):
        return False
    if len(paragraph) > SUPPLEMENT_LINEAGE_KEEP_MAX_LINES:
        return True
    return not any(_has_citation_marker(line) for line in paragraph)


def _has_citation_marker(line: str) -> bool:
    """行内是否有 `[n]` 引标（纯字符扫描：NFKC 归一后 `[` ＋ 至少一位数字 ＋ `]`——形态判定）。

    归一口径与判定面同族（`specs/verification.md` 行为 7「全角先归一」——`［２］` 亦算引标）。
    """
    text = unicodedata.normalize("NFKC", line)
    cursor = 0
    while True:
        start = text.find(_OPEN_BRACKET, cursor)
        if start < 0:
            return False
        end = text.find(_CLOSE_BRACKET, start + 1)
        if end < 0:
            return False
        body = text[start + 1 : end]
        if body and all(char in _DIGITS for char in body):
            return True
        cursor = end + 1


def same_family_head_in(text: str, block: str) -> bool:
    """正文是否已携该族块头行（**同族块头在场判据**——answering 收口幂等面用）。

    与块剥除同族判据：三族按「整行恰为记号」、血缘族按「行内含记号」；加粗变体同族。
    """
    marks = SUPPLEMENT_BLOCK_HEAD_MARKS.get(block)
    if not marks:
        raise ValueError(f"块型越界（闭世界 SUPPLEMENT_BLOCKS）：{block!r}")
    if block == SUPPLEMENT_BLOCK_LINEAGE:
        return any(mark in line for line in _lines(text) for mark in marks)
    return any(undecorated_head(line) in marks for line in _lines(text))


__all__ = [
    "SUPPLEMENT_LINEAGE_HEAD_MARKS",
    "block_head_kind",
    "same_family_head_in",
    "split_block_sections",
    "undecorated_head",
]
