"""答案轮装配（题面件→子问题结果清单）＋答案环节规章段（动词钉死＋答案要求＋白话表＋汇总＋起草合同）。

段序真源＝`specs/prompts.md` 行为 12（迁移照抄 V1 `assemble_answer_instruction`）；三件套与
动词钉死句真源＝V1 `orientation.py` `answer_turn_preamble`（行为 13、钉 `pin-13` 合同侧：
动词钉死句＋答案要求⑦两字面在场，提示词侧不注入回声形指令）。

**2026-10-17 H 批（角色分家·system 承载位）**：原一条 user 包拆两路——**规章段**（动词钉死句＋
【答案要求】＋清单全文＋术语白话表＋汇总合同＋起草答案合同）＝`answer_system_contract()`，经
`bookkeeping.call_model(system=…)` 随本次请求走（不入链）；**动态段**（题面件＋子问题结果清单）＝
`assemble_answer_prompt()`，仍作 user 条入链（材料段由调用方追加于尾）。文本零改、段内相对序零改。

**术语白话表（族⑥示例区，2026-10-17 EB4a）**：`constants.JARGON_PLAIN_GLOSSARY` 静态块在规章段内
**恰一次**（`answer_system_contract`；静态文本置前、投影段在后，字节级稳定——KV 追加形纪律不破）；
文本单点＝`constants`，消费方只引不复制。

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
    ANSWER_EXPLORE_CONTRACT,
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
    """答案轮三件套的**题面件**（动态段·user 承载位——2026-10-17 H 批）。

    三件套（V1 `answer_turn_preamble`：行 1 用户问题／行 2 动词钉死句／行 3 答案要求）随 H 批
    拆两路：行 2／行 3 属**规章段**（`answer_system_contract`，system 位）；本函数只出**行 1**
    题面件（`{question}` 随 run 变，属动态段）。
    """
    return _QUESTION_ANCHOR.format(question=question)


def answer_system_contract() -> str:
    """答案环节**规章段**（system 承载位——2026-10-17 H 批）：动词钉死句＋答案要求＋白话表＋
    汇总合同＋起草答案合同。

    构成件逐字引既有常量（零新写）；段内相对序照原装配序（动词钉死句→【答案要求】→术语白话表→
    汇总合同→起草合同收尾）。与动态段的分工＝**规章＝system、题面与清单＝user**：用户问题行与
    子问题结果清单留 `assemble_answer_prompt`（材料段由调用方追加——渲染归 `context`）。
    纯文本进出、确定性；`state` 零写入。
    """
    return (
        _VERB_PIN
        + "\n"
        + _REQUIREMENTS_HEAD
        + ANSWER_REQUIREMENTS
        + "\n"
        + JARGON_PLAIN_GLOSSARY
        + "\n"
        + "\n"
        + SUMMARY_CONTRACT
        + "\n"
        + "\n"
        + ANSWER_EXPLORE_CONTRACT
        + "\n"
        + "\n"
        + ANSWER_DRAFT_CONTRACT
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
    """答案轮**动态段**装配（题面件→子问题结果清单）——user 承载位（2026-10-17 H 批）。

    段序照原装配序的**动态件**：用户问题行（三件套行 1）→ 子问题结果清单；**规章段**（动词钉死句／
    【答案要求】内嵌清单全文／术语白话表／汇总合同／起草答案合同收尾）改走 `answer_system_contract`
    的调用级 system 注入参、不入链（真源 `specs/prompts.md` 2026-10-17 H 批注）。

    纯函数：只读 `state` 投影，零 IO／零时钟／零随机；材料段不在输出内（调用方追加于尾）。

    **术语白话表（族⑥示例区）**：随规章段入 system 位（`JARGON_PLAIN_GLOSSARY` 静态块、字节级
    稳定——两跑／异状态逐字同源；文本单点＝`constants`）。
    """
    return answer_round_preamble(state.question) + _SUBTASK_LIST_HEAD + "\n" + subtask_result_list(
        state
    )
