"""execution.plan_face —— 计划面确定性规则（问句指标接地闸＋「前 N」→排名归一）。

真源＝`specs/execution.md` 行为 15（2026-10-17 EB3 D4 补）；规则语义真源＝`specs/query.md`
行为约定 1「条数/排名词面消歧按 V1 `domain.py` 合同值」——本模块**照 V1 行为重落**（只照行为
不照代码；V1 `app/domains/chat/domain.py` 为备份只读参考）。两条规则：

1. **问句指标接地闸（L04-23 fail-closed，EB3-D4.1）**：data 链计划的 `metric_slot` 必须落在
   **问句的台账注册面**上（问句里逐字出现的台账可见面——槽位／指标名／别名键，与
   `understanding` 名录面同源：`tools.ledger_facts` 的 `keys`＝「slot ∪ 名 ∪ 别名」）；
   **问句未含台账注册指标**（问句指标在册无绑定／未注册，如「日产水量」）＝该计划是**回落相近
   列**（模型把问句问及的指标换成了在册的相近代用品，如 `liquid_output`）→ **fail-closed 拒投**
   （不执行工具、无 SQL 产出），拒因回喂模型换链（检索问答链如实说明）或如实拒答。
   「问句注册面在场但计划指标不在其中」同判拒（回落面更直接）。

2. **「前 N」→排名归一（L04-18，EB3-D4.2）**：问句**显式「前 N」／「TOP N」**（V1
   `_LIMIT_TOP_RE` 同形词面：数字或汉字数字）＋计划指标**已注册**＋计划非汇总型（`aggregate`
   ——V2-71 `QueryPlan` 互斥把守，本块不造 aggregate∧ranking 违例）→ **归一为
   `ranking=true` ＋ 方向按 V1 `parse_ranking_direction` 词面（「最低/最小/最少」→升序，其余
   →降序）＋ `limit=N`**。归一**不改写模型原话、不加缺省**：只在问句词面显式给出条数时落值。

**承载位说明（R6／AST 隔断的字面承载，登记见票面回报）**：本模块的两条规则在语义上属**计划面**
（真源件＝`appv2.query.domain` 的 `build_query_plan`／`is_ranking_question`／`parse_row_limit`／
`parse_ranking_direction`，V1 合同值的 V2 移植件）——但 runtimev2 各块**不得直引 `appv2.query`**
（边界闸 **R6**），且 `execution` 面受「程序不判语义（无词表／正则）」机检约束（验收行
`::no_lexicon_or_regex_in_execution`）。故本模块按同仓既有「**隔断两处各持字面**」体例（先例＝
`orchestration` 回炉判据与 `prompts` 两部分持同一档字面）以**形态处理面**承载：词面标记＝具名
常量（非词表集合）、数字取字＝字符形判定（`str.isdigit`／汉字数字映射）、集合成员判定＝台账可见面。
**与真源件的漂移由测试看守**（`tests/domains/test_v2_eb3_d4_defects.py` 以同一题面电池对
`appv2.query.domain` 的参考函数逐点对读：词面判据不漂移）。

**零 LLM、零 I/O、零状态写入**：纯函数面；入参全部显式注入（问句／计划草案／台账可见面）。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from appv2.runtimev2.execution.constants import (
    PLAN_DIRECTION_ASC,
    PLAN_DIRECTION_DESC,
    PLAN_FACE_PASS,
    PLAN_FACE_REASON_MISMATCH_TEMPLATE,
    PLAN_FACE_REASON_UNGROUNDED_TEMPLATE,
    PLAN_FACE_REFUSE_MISMATCH,
    PLAN_FACE_REFUSE_UNGROUNDED,
)

# ── 词面标记（形态处理面：数量与排名标记——具名常量，非词表集合）──────────────────
MARK_FRONT = "前"  # 「前 N」条数标记
MARK_TOPN_UPPER = "TOP"  # 「TOP N」（V1 同形）
MARK_TOPN_LOWER = "top"
MARK_ASC_MIN = "最低"  # 升序方向标记（V1 `_ASC_RANKING_RE` 同形）
MARK_ASC_SMALL = "最小"
MARK_ASC_FEW = "最少"
MARK_NUMERAL_JOIN = " 　"  # 标记与数字之间允许出现的空白（半角空格／全角空格）

# 汉字数字（形态处理面：数量字面——V1 `_CN_NUMERALS` 同值；字数映射不是语义词表）
_CN_NUMERALS: dict[str, int] = {
    "一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}

_EXPLICIT_LIMIT_MARKS: tuple[str, ...] = (MARK_FRONT, MARK_TOPN_UPPER, MARK_TOPN_LOWER)
_ASC_MARKS: tuple[str, ...] = (MARK_ASC_MIN, MARK_ASC_SMALL, MARK_ASC_FEW)


def _numeral_at(question: str, index: int) -> tuple[int | None, int]:
    """`index` 起的数字字面（跳过空白）→（值, 命中长度）；无数字＝（None, 0）。

    数字形判定＝**字符形函数**（`str.isdigit`／汉字数字映射——规格验收行「豁免面＝形态处理」
    明列面），不做数值解析、不跨标记取数。
    """
    cursor = index
    while cursor < len(question) and question[cursor] in MARK_NUMERAL_JOIN:
        cursor += 1
    digits = ""
    while cursor < len(question) and question[cursor].isdigit():
        digits += question[cursor]
        cursor += 1
    if digits:
        return int(digits), cursor - index
    if cursor < len(question):
        value = _CN_NUMERALS.get(question[cursor])
        if value is not None:
            return value, cursor - index + 1
    return None, 0


def explicit_row_limit(question: str) -> int | None:
    """问句显式条数（「前 N」／「TOP N」——V1 `parse_row_limit` 的 TOP 族同语义）。

    只在**显式标记**在场时取值（不做默认、不猜）；值 ≤0／无数字＝未给（None）。V1 的「N 口」
    独立形（「三口井」）不在本规则触发面（EB3-D4.2 钉面＝显式「前 N」），故本函数不读该形。
    """
    for mark in _EXPLICIT_LIMIT_MARKS:
        start = 0
        while (found := question.find(mark, start)) >= 0:
            value, _length = _numeral_at(question, found + len(mark))
            if value is not None and value > 0:
                return value
            start = found + len(mark)
    return None


def ranking_direction(question: str) -> str:
    """排名方向（V1 `parse_ranking_direction` 同语义：升序标记在场→asc，其余→desc）。"""
    for mark in _ASC_MARKS:
        if mark in question:
            return PLAN_DIRECTION_ASC
    return PLAN_DIRECTION_DESC


def question_metric_slots(
    question: str, ledger_keys: Mapping[str, str]
) -> frozenset[str]:
    """问句的台账注册面（槽位集）：台账可见面里**逐字出现在问句**者 → 其槽位。

    `ledger_keys`＝`tools.ledger_facts` 的键映射（可见面→槽位：slot ∪ 名 ∪ 别名——与
    `understanding` 名录面同源）。判据＝**集合成员判定**（形态处理豁免面）：名字取自台账面、
    本模块不自建第二份词表。
    """
    slots: set[str] = set()
    for surface, slot in ledger_keys.items():
        if surface and surface in question:
            slots.add(slot)
    return frozenset(slots)


@dataclass(frozen=True, slots=True)
class PlanFaceVerdict:
    """计划面判定（两态互斥：`pass` 携归一后计划草案；`refuse` 携拒因——不执行工具）。"""

    decision: str  # PLAN_FACE_PASS ｜ PLAN_FACE_REFUSE_*
    plan: Mapping[str, Any]
    reason: str = ""

    @property
    def rejected(self) -> bool:
        return self.decision != PLAN_FACE_PASS


def plan_face_rules(
    *,
    question: str,
    plan: Mapping[str, Any],
    ledger_keys: Mapping[str, str],
    metric_registered: bool,
) -> PlanFaceVerdict:
    """两条规则一次判（接地闸先行、通过后做「前 N」归一）——纯函数、幂等。

    退化世界（台账可见面为空＝注入缺缝）→ **闸静默**（只做「前 N」归一；同 `preconditions`
    「空台账不硬拒全量」先例）；计划指标不在台账（`metric_registered=False`）→ 本闸不接（判拒
    归既有台账校验面：引擎「不在目录不代答」）。
    """
    slot = str(plan.get("metric_slot") or "")
    if ledger_keys and metric_registered:
        registered = question_metric_slots(question, ledger_keys)
        if slot and slot not in registered:
            if registered:
                return PlanFaceVerdict(
                    decision=PLAN_FACE_REFUSE_MISMATCH,
                    plan=plan,
                    reason=PLAN_FACE_REASON_MISMATCH_TEMPLATE.format(
                        slot=slot, slots="／".join(sorted(registered))
                    ),
                )
            return PlanFaceVerdict(
                decision=PLAN_FACE_REFUSE_UNGROUNDED,
                plan=plan,
                reason=PLAN_FACE_REASON_UNGROUNDED_TEMPLATE.format(slot=slot),
            )
    limit = explicit_row_limit(question)
    if limit is not None and not bool(plan.get("aggregate", False)):
        normalized = dict(plan)
        normalized["ranking"] = True
        normalized["direction"] = ranking_direction(question)
        normalized["limit"] = limit
        return PlanFaceVerdict(decision=PLAN_FACE_PASS, plan=normalized)
    return PlanFaceVerdict(decision=PLAN_FACE_PASS, plan=plan)


__all__ = [
    "MARK_FRONT",
    "MARK_TOPN_LOWER",
    "MARK_TOPN_UPPER",
    "PlanFaceVerdict",
    "explicit_row_limit",
    "plan_face_rules",
    "question_metric_slots",
    "ranking_direction",
]
