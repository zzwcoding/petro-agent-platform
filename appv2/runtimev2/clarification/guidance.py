"""`finalize` 打回的三段带路（`specs/clarification.md` 行为 18——拒因载荷必带、零模型调用）。

三段（机器已知事实说全、段缺则跳、「；」连接成单段文本）：

1. ①有绑定拒／换链提议的前置判定 →「该指标材料走报告检索：分解时 chain=knowledge、
   tool=doc_retrieve」；
2. ②已空手探查清单 →「已空手探查：{tools}——禁再试同名同参」；
3. ③兜底句**恒在**「先 discover 取得条目（精确名单词），或 decompose 分解走 doc_retrieve
   检索执行。」

①的触发面＝**结构化判据（V2-88／A14 改判）**：读 `state.precondition_verdicts` 的**生产投影键**
（`preconditions.SubtaskVerdict.as_payload()`＝`subtask_id`／`decision`／`hit_rule`／`notes`／
`reason`，**无 `state` 键**），零文案子串、零语义判断：

- `decision="refuse"` 且 `reason.rule_id` ∈ 换链/未绑定闭世界（台账外／换链终局拒）；
- `decision="allow"` 且 `notes` 含换链重入注记（换链**首次触发**＝放行＋注记＋新计点——纯换链
  回炉的真实路径；2026-10-18 主窗授权并入本条判据）。

本模块**零模型调用、零 IO、零语义判断**：只读 `state` 的两个结构化面（`precondition_verdicts`
的结构化判定键／`state.empty_probes` 的空手指纹）拼装文本——逐字稿载体＝迁移前
`appv2/runtime/graph.py` `_shallow_probe_feedback`（承载位换、文本不变；本模块不复制其载体）。
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from appv2.runtimev2.clarification.constants import (
    EMPTY_PROBES_JOIN,
    GUIDANCE_EMPTY_PROBES,
    GUIDANCE_FALLBACK,
    GUIDANCE_JOIN,
    GUIDANCE_PRECONDITION,
    NOTE_CHAIN_SWITCH_REENTRY,
    REROUTE_RULE_IDS,
)
from appv2.runtimev2.state import RunState

# 判定取值（三态闭世界的值引用——`refuse`／`allow` 真源＝`preconditions.constants.DECISION_*`；
# 本块不 import 其它相位（R1），故按值落字面，与闭世界同值）。
_DECISION_REFUSE = "refuse"
_DECISION_ALLOW = "allow"


def _has_binding_refusal(state: RunState) -> bool:
    """①触发面：结构化判据（decision+reason.rule_id／换链重入注记）——零文案子串。

    两形（见模块 docstring）：`refuse`×换链/未绑定 rule_id；`allow`×换链重入注记。
    """
    for verdict in state.precondition_verdicts:
        if not isinstance(verdict, Mapping):
            continue
        decision = verdict.get("decision")
        if decision == _DECISION_REFUSE:
            reason = verdict.get("reason")
            if isinstance(reason, Mapping) and reason.get("rule_id") in REROUTE_RULE_IDS:
                return True
        elif decision == _DECISION_ALLOW:
            notes = verdict.get("notes")
            if isinstance(notes, (list, tuple)) and NOTE_CHAIN_SWITCH_REENTRY in notes:
                return True
    return False


def _empty_probe_tools(state: RunState) -> list[str]:
    """②触发面：已空手探查的工具名（读 `state.empty_probes` 的指纹还原、去重排序）。"""
    names: set[str] = set()
    for fingerprint in state.empty_probes:
        if not isinstance(fingerprint, str):
            continue
        parsed = json.loads(fingerprint)
        if isinstance(parsed, Mapping):
            name = parsed.get("tool")
            if isinstance(name, str) and name:
                names.add(name)
    return sorted(names)


def rejection_guidance(state: RunState) -> str:
    """三段拼装（行为 18）：段缺则跳、「；」连接；③兜底句恒在。"""
    segments: list[str] = []
    if _has_binding_refusal(state):
        segments.append(GUIDANCE_PRECONDITION)
    tools = _empty_probe_tools(state)
    if tools:
        segments.append(GUIDANCE_EMPTY_PROBES.format(tools=EMPTY_PROBES_JOIN.join(tools)))
    segments.append(GUIDANCE_FALLBACK)
    return GUIDANCE_JOIN.join(segments)
