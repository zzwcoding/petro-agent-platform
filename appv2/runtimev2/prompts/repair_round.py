"""回炉修复轮装配（V2-125 从 `orchestration/repair.py` 迁入）——回炉请求面与缺位说明请求面。

真源＝`tickets/v2/V2-115-核验失败动作回炉修复.md` 收票回写「待办：`prompts/` 迁移与归因桶
`CALLER_REPAIR` 另立小票」；本模块即那半张（V2-125）。回炉环本体仍归编排侧
`orchestration/repair.py`（`run_repair`——检测→改写→复检→留痕），本块**只出文本**：
两装配函数＝合同常量与调用方注入文本的确定性拼接（行为 14／15），零判断、零 I/O、零时钟。

**承载位分工**（同 H 批先例）：规章段（`REPAIR_SYSTEM_CONTRACT`）由调用方经
`bookkeeping.call_model(system=…)` 随本次请求走（不入链）；请求面正文（逐行标红原句＋本轮
窗内材料段＋应答合同／缺位说明合同）＝本模块两装配函数的输出，作 user 条发出。

**材料段不在本块渲染**（真源 `context.render_materials`——材料渲染归 `context`）：两装配函数
只收调用方注入的 `materials_text`，故本块零 `context` 依赖（R3：prompts 只许依赖 state）。

**合同常量与携槽模板分家**（pin-24 要求合同常量无格式槽）：无槽三件
（`REPAIR_SYSTEM_CONTRACT`／`REPAIR_MATERIALS_HEAD`／`REPAIR_OUTPUT_CONTRACT`）落
`prompts/constants.py` 族 `repair_request`；携槽三件（`REPAIR_REQUEST_HEAD`／
`REPAIR_LINE_TEMPLATE`／`REPAIR_GAP_HEAD`）落本模块（先例＝`task_book.RECOMMENDATION_TEMPLATE`）。

**逐字零改**：迁入的六件文本逐字照抄 `orchestration/repair.py` 迁出前字面（V2-115 收票面
逐字），两装配函数输出与迁出前 `_repair_prompt`／`_gap_prompt` **字节级相同**（回归看守＝
`tests/domains/test_v2_v2115_repair.py` 的留痕 prompt 断言）。
"""

from __future__ import annotations

from collections.abc import Sequence

from appv2.runtimev2.prompts.constants import (
    REPAIR_MATERIALS_HEAD,
    REPAIR_OUTPUT_CONTRACT,
)

# 携槽模板三件（本模块自有——合同常量族不收携槽件，pin-24）。
REPAIR_REQUEST_HEAD = (
    "【回炉修复】以下 {count} 行在核验中标红（无据／引标不可解析／归属对不上）——"
    "只重写这些行，其余行一字不动。"
)
REPAIR_LINE_TEMPLATE = "[{index}] {line}"
REPAIR_GAP_HEAD = (
    "【缺位说明】以下行经 {rounds} 轮回炉仍无材料支撑——只输出一段**缺位说明**"
    "（已试什么、仍缺什么），不得复述任何未在材料里出现的数值。"
)


def assemble_repair_prompt(flagged: Sequence[str], *, materials_text: str) -> str:
    """回炉请求面：标红逐行原句（编号＝应答 `index`）＋本轮窗内材料段＋应答合同。

    `flagged`＝检测面标红的逐行原句（`verification.detect_intended` 的 `RewriteRecord.line`
    投影——保序）；`materials_text`＝调用方渲染的本轮窗内材料段（真源 `context.render_materials`）。
    输出＝user 条正文（恒 `str`，不抛业务错）。
    """
    lines = [REPAIR_REQUEST_HEAD.format(count=len(flagged))]
    lines.extend(
        REPAIR_LINE_TEMPLATE.format(index=index, line=line)
        for index, line in enumerate(flagged, start=1)
    )
    lines.append(REPAIR_MATERIALS_HEAD)
    lines.append(materials_text)
    lines.append(REPAIR_OUTPUT_CONTRACT)
    return "\n".join(lines)


def assemble_repair_gap_prompt(
    rounds: int, flagged: Sequence[str], *, materials_text: str
) -> str:
    """缺位说明请求面：改写轮到顶后的说明请求（标红逐行原句＋窗内材料＋缺位说明合同）。

    `rounds`＝已用改写轮数（`RunState.repair_rounds`——填进合同首行）；`flagged`／
    `materials_text` 同 `assemble_repair_prompt`。输出＝user 条正文（恒 `str`）。
    """
    lines = [REPAIR_GAP_HEAD.format(rounds=rounds)]
    lines.extend(
        REPAIR_LINE_TEMPLATE.format(index=index, line=line)
        for index, line in enumerate(flagged, start=1)
    )
    lines.append(REPAIR_MATERIALS_HEAD)
    lines.append(materials_text)
    return "\n".join(lines)
