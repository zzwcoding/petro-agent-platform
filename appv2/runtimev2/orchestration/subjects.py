"""主体反思（V2-117）：材料到手后逐来源核「是否属题面点名主体」——确定性比对、零语义。

真源＝`tickets/v2/V2-117-主体反思与下游加权.md` 任务 1（逐字：材料到手后（L2 并集池），逐来源核
「是否属题面点名主体」——判据面＝来源的报告名／油田标签／井号与题面主体的一致性（确定性比对，
零语义）；结果落 `state` 与 step payload（逐来源：属／不属／未知））＋「Kimi 评审修正」1
（**调用点不得跨相位直引**：`execution` 不得 import `clarification`
（R1 `allow_indirect_imports=false`）⇒ 反思函数落 **orchestration**、消费 clarification 抽取面
写下的 `state.subjects`）。

**为什么落在本块**（调用点纪律）：R1 七相位互不 import——若把反思挂在 `execution` 并调
`clarification` 即破 R1。本块是唯一被允许「调相位公开入口 + 读全状态」的组合面；反思函数在此
落点、由 `graph` 节点在材料到手后调用（先例：`graph._program_subjects` 的读面绑定同在本块）。

**零语义、零 CJK 词表**（票面逐字）：判据本体＝既有单点——`appv2.text_tokens` 的边界／数字全等
（L1/L3 同源判据）＋`appv2.tools` 的实体／井号取词单点（`entity_anchor_tokens`，闭世界名录）。
本模块不新建第二份词表、不做语义蕴含判定。

三值判据（逐来源聚合：属 ＞ 不属 ＞ 未知——同源多支取最强命中）：

- **属**：该来源的任一支在（正文 ∪ 出处名 ∪ 报告名 ∪ 油田标签）四面上命中任一题面主体 token；
- **不属**：四面上**没有任何**题面主体 token 命中，却**自带**其它主体类 token（井号／油田名——
  取词单点 `entity_anchor_tokens`）——即「材料讲的是另一个主体」；
- **未知**：四面既无题面主体命中、也不自带任何主体类 token（泛制度／口径类来源）——**审静默**，
  下游不得据此拒收（不误伤）。

题面主体 token 面＝`state.subjects`（clarification 抽取面写下的归一形）逐项过 `entity_anchor_tokens`
（取不到＝原形自兜底）；`state.subjects` 空或为「都要（分源对比）」哨兵（＝多主体并列、无单一
主体面）时回退程序候选单点 `tools.subject_candidates`（与 `clarification` 的程序回填同一抽取面）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from appv2.runtimev2.orchestration.constants import PAYLOAD_SUBJECT_REFLECTION_KEY
from appv2.runtimev2.state import (
    ALL_FIELDS_SENTINEL,
    SUBJECT_FOREIGN,
    SUBJECT_MATCH,
    SUBJECT_UNKNOWN,
    RunState,
)
from appv2.text_tokens import boundary_hit, num_token_hit
from appv2.tools import (
    entity_anchor_tokens,
    normalize_anchor_text,
    subject_candidates,
)
from appv2.tools.anchors import entity_closed_world, well_tokens

# 主体类两值（`_token_classes` 的类键——ASCII 结构取值，非语义词表）：
# `well`＝井号 token（`tools.anchors.well_tokens` 单点）；`entity`＝闭世界油田/平台规范名
# （`tools.anchors.entity_closed_world` 单点）。**同类才判「不属」**——题面主体是井号时，
# 只把「另一口井」判不属（来源只带另一油田名、却无井号 ⇒ 未知：井可能就属该油田，判不了）。
_CLASS_WELL = "well"
_CLASS_ENTITY = "entity"

# 逐来源聚合的强度序（同源多支取最强命中——「属」优先于「不属」优先于「未知」）。
_VERDICT_RANK: dict[str, int] = {
    SUBJECT_UNKNOWN: 0,
    SUBJECT_FOREIGN: 1,
    SUBJECT_MATCH: 2,
}


def subject_needles(state: RunState) -> tuple[str, ...]:
    """题面主体 token 面（判据面单点——`state.subjects` 归一形逐项过取词单点）。

    哨兵「都要（分源对比）」（`ALL_FIELDS_SENTINEL`）＝多主体并列、无单一主体面，与空
    `state.subjects` 同处置：回退程序候选抽取面 `tools.subject_candidates`（与澄清相位的
    程序回填同源）。两路皆空 ⇒ 空元组（下游审静默——不误伤跨主体对照题）。
    """
    subjects = tuple(str(item).strip() for item in state.subjects if str(item).strip())
    if not subjects or ALL_FIELDS_SENTINEL in subjects:
        subjects = tuple(
            subject_candidates(str(state.question or ""), state.ledger_dump or {})
        )
    needles: list[str] = []
    for subject in subjects:
        tokens = entity_anchor_tokens(subject) or (subject,)
        for token in tokens:
            if token not in needles:
                needles.append(token)
    return tuple(needles)


def _haystacks(observation: Mapping[str, Any]) -> tuple[str, ...]:
    """来源的判据四面（正文 ∪ 出处名 ∪ 报告名 ∪ 油田标签——票面逐字「报告名／油田标签／井号」）。"""
    locator = observation.get("locator")
    report = str(locator.get("report") or "") if isinstance(locator, Mapping) else ""
    return (
        str(observation.get("content") or ""),
        str(observation.get("source") or ""),
        report,
        str(observation.get("well") or ""),
    )


def _token_hit(token: str, haystacks: Sequence[str]) -> bool:
    """token 对四面的命中（判据本体＝`appv2.text_tokens`——纯数字 token 走数字全等，其余走边界）。"""
    folded = str(token).casefold()
    if not folded:
        return False
    numeric = folded.isdigit()
    for haystack in haystacks:
        text = str(haystack).casefold()
        if not text:
            continue
        hit = num_token_hit(text, folded) if numeric else boundary_hit(text, folded)
        if hit:
            return True
    return False


def _token_classes(tokens: Sequence[str]) -> frozenset[str]:
    """token 的主体类集（`well`／`entity` 两值——取词单点，零第二份词表）。

    井号类＝`tools.anchors.well_tokens` 命中；油田/平台类＝闭世界规范名（`entity_closed_world`
    归一后成员判定）。数字核等两不属者零类（无类针不判「不属」——保守）。
    """
    world = {normalize_anchor_text(name) for name in entity_closed_world()}
    classes: set[str] = set()
    for token in tokens:
        if well_tokens(str(token)):
            classes.add(_CLASS_WELL)
        if normalize_anchor_text(str(token)) in world:
            classes.add(_CLASS_ENTITY)
    return frozenset(classes)


def _verdict_of(observation: Mapping[str, Any], needles: Sequence[str]) -> str:
    """单支来源的主体反思判值（属／不属／未知——三值闭世界，零语义）。

    「不属」＝**同类**不一致：来源自带的主体类 token（井号／油田名）与题面主体的**类**有交集、
    却无一支命中题面主体——如题面点名井号 `Y-41` 而来源只讲 `W-41`。来源只带**别类**主体
    （题面点井号、来源只带另一油田名）⇒ 未知（井可能就属该油田，形态面判不了——审静默）。
    """
    if not needles:
        return SUBJECT_UNKNOWN
    haystacks = _haystacks(observation)
    if any(_token_hit(needle, haystacks) for needle in needles):
        return SUBJECT_MATCH
    needle_classes = _token_classes(needles)
    if not needle_classes:
        return SUBJECT_UNKNOWN
    foreign = [
        token
        for token in entity_anchor_tokens(" ".join(haystacks))
        if not _token_hit(token, needles)
    ]
    if any(_token_classes([token]) & needle_classes for token in foreign):
        return SUBJECT_FOREIGN
    return SUBJECT_UNKNOWN


def reflect_subjects(
    state: RunState, observations: Sequence[Mapping[str, Any]] | None = None
) -> dict[str, str]:
    """逐来源主体反思（L2 并集池 → `{来源名: 属／不属／未知}`；确定性、零模型、零 IO）。

    `observations` 缺省＝`state.observations` 现值（材料到手后的并集池）。逐来源聚合（同源多支
    取最强命中）；无出处名（`source` 空）的行如实跳过（不发明来源键）。
    """
    rows = list(state.observations if observations is None else observations)
    needles = subject_needles(state)
    result: dict[str, str] = {}
    for observation in rows:
        if not isinstance(observation, Mapping):
            continue
        source = str(observation.get("source") or "").strip()
        if not source:
            continue
        verdict = _verdict_of(observation, needles)
        previous = result.get(source)
        if previous is None or _VERDICT_RANK[verdict] > _VERDICT_RANK[previous]:
            result[source] = verdict
    return result


def _attach_step_payload(state: RunState, result: Mapping[str, str]) -> None:
    """把反思结果落到**最近一条步记录**的 payload（additive 键——`state.steps[-1]`）。

    材料到手时最近一步恒为刚落的执行／作答步（执行相位 `_consume` 的步记录、作答相位的
    `answer` 步）；无步／形态不合＝如实跳过（不发明步、不新增步型——`STEP_KINDS` 六值闭世界不动）。
    """
    if not state.steps:
        return
    entry = state.steps[-1]
    if not isinstance(entry, dict):
        return
    payload = entry.get("payload")
    if not isinstance(payload, dict):
        return
    payload[PAYLOAD_SUBJECT_REFLECTION_KEY] = dict(result)


def reflect_and_record(state: RunState) -> dict[str, str]:
    """主体反思单点调用面：算 → 落 `state.subject_reflection` → 落最近一步 payload。

    `graph` 的调用点（材料到手后）只调本函数——判据、状态位与留痕一处收口（禁第二份调用形）。
    """
    result = reflect_subjects(state)
    state.subject_reflection = dict(result)
    _attach_step_payload(state, result)
    return result
