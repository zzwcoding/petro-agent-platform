"""答案轮装配（三件套置顶→术语白话表→汇总合同→子问题结果清单→起草答案合同）——纯文本、零判断。

段序真源＝`specs/prompts.md` 行为 12（迁移照抄 V1 `assemble_answer_instruction`）；三件套与
动词钉死句真源＝V1 `orientation.py` `answer_turn_preamble`（行为 13、钉 `pin-13` 合同侧：
动词钉死句＋答案要求⑦两字面在场，提示词侧不注入回声形指令）。

**术语白话表（族⑥示例区，2026-10-17 EB4a）**：`constants.JARGON_PLAIN_GLOSSARY` 静态块在
答案装配包内**恰一次**入链（`assemble_answer_prompt`；静态文本置前、state 投影段在后，
字节级稳定——KV 追加形纪律不破）；文本单点＝`constants`，消费方只引不复制。

**材料段不在装配输出内**（由调用方按 `context` 渲染产物追加于尾——材料渲染归 `context`）。

子问题结果清单行形＝迁移照抄 V1 `graph.py` answer 节点的清单拼装（`- [id] question——状态
〔原因〕〔排名支配〕`）；**显式差异**＝V1 的 `_refusal_with_hint`／`_humanize_refusal`（正则＋
已知形人话翻译表）不迁移——本块禁语义词表／正则（行为 15），且机器拒因原文零改动
（`arch/P6b` A-P6b-05：回炉／审计消费面不动），故清单携拒因原文。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from appv2.runtimev2.prompts.constants import (
    ANSWER_DRAFT_CONTRACT,
    ANSWER_REQUIREMENTS,
    JARGON_PLAIN_GLOSSARY,
    SUMMARY_CONTRACT,
)
from appv2.runtimev2.state import RunState

# 三件套（迁移照抄 V1 `answer_turn_preamble`——行 1 题目锚、行 2 动词钉死句、行 3 答案要求）。
_QUESTION_ANCHOR = "用户问题：{question}\n"
_VERB_PIN = (
    "现在：写最终答案交付用户。本步是写答案步——不再做任何决策、不再发射任何"
    "动作指令（finalize/decompose 等动作出现即废品）。"
)
_REQUIREMENTS_HEAD = "【答案要求】"

# 子问题结果清单标题行（迁移照抄 V1 `assemble_answer_instruction`）。
_SUBTASK_LIST_HEAD = "子问题结果清单："
# 子问题状态三值（V1 answer 节点闭世界——子问题结果面，非 state 三族取值域，`failed` 系同名
# 巧合）→ 清单标记；闭世界外的取值原样呈现（不编造）。键以常量引用承载：本表不是 state 取值域
# 的第二处定义（`specs/state.md` 单点纪律面）。
_STATUS_OK = "ok"
_STATUS_REFUSED = "refused"
_STATUS_FAILED = "failed"
_SUBTASK_MARKS: Mapping[str, str] = {
    _STATUS_OK: "完成",
    _STATUS_REFUSED: "已拒答",
    _STATUS_FAILED: "失败",
}
# 排名型子问题的消费支配标记（迁移照抄 V1 answer 节点——V2-51 数-排2 形，零改动）。
_RANKING_DOMINANCE = (
    "（排名型——结论必须从本子问题排名观察支（合计行口径）取值，"
    "不得从其他子问题的明细行切片换算或跨子问题取值）"
)
_NO_SUBTASK = "（无）"


def answer_round_preamble(question: str) -> str:
    """答案轮三件套置顶（恒三行拼接、以「\\n」收尾——迁移照抄 V1 同函数）。"""
    return (
        _QUESTION_ANCHOR.format(question=question)
        + _VERB_PIN
        + "\n"
        + _REQUIREMENTS_HEAD
        + ANSWER_REQUIREMENTS
        + "\n"
    )


def _plans_by_id(state: RunState) -> dict[str, Mapping[str, Any]]:
    plans: dict[str, Mapping[str, Any]] = {}
    for match in state.tool_matches:
        if not isinstance(match, Mapping):
            continue
        plan = match.get("plan")
        if isinstance(plan, Mapping):
            plans[str(match.get("id", ""))] = plan
    return plans


def subtask_result_list(state: RunState) -> str:
    """子问题结果清单渲染（逐条一行；无条目走「（无）」——零编造、零截断）。"""
    plans = _plans_by_id(state)
    marks = _SUBTASK_MARKS
    lines: list[str] = []
    for result in state.subtask_results:
        if not isinstance(result, Mapping):
            continue
        status = str(result.get("status", ""))
        mark = marks.get(status, status)
        reason = str(result.get("reason") or "")
        reason_text = f"（{reason}）" if reason else ""
        dominance = ""
        if plans.get(str(result.get("id", "")), {}).get("ranking") is True:
            dominance = _RANKING_DOMINANCE
        lines.append(
            f"- [{result.get('id', '')}] {result.get('question', '')}——{mark}{reason_text}"
            f"{dominance}"
        )
    return "\n".join(lines) or _NO_SUBTASK


def assemble_answer_prompt(state: RunState) -> str:
    """答案轮指令装配（段序：三件套→术语白话表→汇总合同→子问题结果清单→起草答案合同收尾）。

    纯函数：只读 `state` 投影，零 IO／零时钟／零随机；材料段不在输出内（调用方追加于尾）。

    **术语白话表（族⑥示例区）**：`JARGON_PLAIN_GLOSSARY` 静态块随答案包恰一次入链（字节级稳定
    ——两跑／异状态逐字同源；文本单点＝`constants`）；注入形＝前置静态块＋末附「\\n\\n」分隔。
    """
    return (
        answer_round_preamble(state.question)
        + JARGON_PLAIN_GLOSSARY
        + "\n"
        + "\n"
        + SUMMARY_CONTRACT
        + "\n"
        + _SUBTASK_LIST_HEAD
        + "\n"
        + subtask_result_list(state)
        + "\n\n"
        + ANSWER_DRAFT_CONTRACT
    )
