"""三面解析器族（外部文本 → 定型载荷；`specs/parsing.md` 目标节＝卡面 Seam）。

- **理解面** `parse_understanding`：统一 JSON 严格解析（V2 定案，Owner 直令）——合格 →
  `Understanding`（`route="full"`）｜`Direct`（`route="direct"`）两形互斥；不合格 → `None`。
  两行式形与「直接回答：」行通道**不再受理**（旧降级提取零可达，差异点①）。
- **澄清面** `parse_question_group`：四动作闭世界（`discover`／`decompose`／`ask`／`finalize`）
  ＋分派；不合格 → 拒因正文（`str`，回喂）。V2 定案签名＝卡面参数名（`text`）＋**注入制限额**
  （无裸默认值）：`max_discovers` ← `state`「轮内发现」键、`discover_budget_left` ←「全 run
  发现」键剩余；`max_subtasks` 数值真源＝`walk/09` §七 Q-C＋`eng/00` F-14、`state` 承载键
  未落定（风险 7⑤）。
- **匹配面** `parse_tool_match`：闭合世界对账（`matches` ↔ 问题组**恰一一对应**）——不合格 →
  拒因正文（`str`）。返回顺序＝发射顺序（不回排组序）。

返回三态闭世界（`specs/parsing.md` 接口定义节）：**定型载荷**｜**拒因正文**（`str`）｜**`None`**。
本块**不抛业务异常、不吞错**（差异点②：V1 两处裸抛收口——`args` 非对象＝拒（拒文＝
`appv2/runtime/graph.py` L616 字面）；`action` 不可哈希形＝拒）；唯一异常出口＝消费方
`understanding` 对 `None` 转 `UnderstandingParseError`。

判据全是结构判定（存在性／类型／闭世界成员／计数／字符串归一）——零词表零正则语义判定
（行为 14）。拒因文本逐字迁移（行为 7），承载位换、文本不变；逐字稿载体＝
`appv2/runtime/subtask.py` L179-L290（澄清面）／L318-L375（匹配面）。
"""

import json
from dataclasses import replace
from typing import Any

from appv2.runtimev2.parsing.constants import (
    _CHAIN_TOOL,
    BUDGET_REJECT_MARK,
    CHAIN_DATA,
    CHAIN_KINDS,
    CLARIFY_ACTIONS,
    CLARIFY_DECOMPOSE,
    CLARIFY_DISCOVER,
    CLARIFY_FINALIZE,
    ROUTE_DIRECT,
    ROUTE_FULL,
)
from appv2.runtimev2.parsing.helpers import extract_plan_json, json_syntax_feedback
from appv2.runtimev2.parsing.models import (
    ClarifyEmission,
    Direct,
    QuestionGroup,
    Subtask,
    SubtaskMatch,
    Understanding,
)


def parse_understanding(text: str) -> Understanding | Direct | None:
    """理解面＝统一 JSON 严格解析（`specs/parsing.md` 行为 1，V2 定案）。

    合格 → `Understanding`（`route="full"`：`text`／`metric_candidates`）｜`Direct`
    （`route="direct"`：`text`）两形互斥、单出口；`route` 越界／缺必填字段／类型不符 → `None`
    （不猜、不取默认、不做降级提取）。**不受理引号自修、不使用提取件**（接口⑤）。
    """
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    route = payload.get("route")
    if route == ROUTE_FULL:
        body = payload.get("text")
        candidates = payload.get("metric_candidates")
        if not isinstance(body, str):
            return None
        if not isinstance(candidates, list) or not all(
            isinstance(item, str) for item in candidates
        ):
            return None
        return Understanding(text=body, metric_candidates=list(candidates), route=ROUTE_FULL)
    if route == ROUTE_DIRECT:
        body = payload.get("text")
        if not isinstance(body, str):
            return None
        return Direct(text=body, route=ROUTE_DIRECT)
    return None


def _question_group_of(raw: Any, *, max_subtasks: int) -> QuestionGroup | str:
    """`question_group` 载荷校验（subtasks 闭合世界——上限／必填键／提议值域）。

    逐支按序过闸：支须对象／`id` 归一后非空且组内唯一／`question` 非空／`ledger_notes` 非空／
    `chain` 非空时 ∈ 闭世界（真源 recon/L1a R-L1a-16…R-L1a-27）。**`tool` 键＝未知键静默丢弃**
    （Owner 裁决 #10：`tool` 归匹配相位产出）；**本层不做链-工具一致性**（归 `parse_tool_match`）。
    """
    if not isinstance(raw, dict):
        return "decompose 缺 question_group 对象"
    raw_subtasks = raw.get("subtasks")
    if not isinstance(raw_subtasks, list) or not raw_subtasks:
        return "question_group 缺 subtasks（非空数组）"
    if len(raw_subtasks) > max_subtasks:
        return f"subtasks 超出上限（≤{max_subtasks} 个——Owner 认可值）"
    subtasks: list[Subtask] = []
    seen: set[str] = set()
    for item in raw_subtasks:
        if not isinstance(item, dict):
            return "subtasks 支须为对象（{id/question/ledger_notes/...}）"
        subtask_id = str(item.get("id") or "").strip()
        question = str(item.get("question") or "").strip()
        ledger_notes = str(item.get("ledger_notes") or "").strip()
        if not subtask_id:
            return "subtasks 支缺 id（组内唯一标识）"
        if subtask_id in seen:
            return f"subtasks id 重复：{subtask_id!r}"
        if not question:
            return f"subtasks {subtask_id} 缺 question（子问题原文）"
        if not ledger_notes:
            return (
                f"subtasks {subtask_id} 缺 ledger_notes（台账注释必带——从词典层"
                "逐字转抄：〈精确指标 slot 名〉〈绑定态〉〈锚定窗〉）"
            )
        chain = str(item.get("chain") or "").strip()
        if chain and chain not in CHAIN_KINDS:
            return (
                f"subtasks {subtask_id} chain 越界"
                f"（{'/'.join(sorted(CHAIN_KINDS))}）：{chain!r}"
            )
        seen.add(subtask_id)
        subtasks.append(
            Subtask(id=subtask_id, question=question, ledger_notes=ledger_notes, chain=chain)
        )
    return QuestionGroup(subtasks=tuple(subtasks))


def parse_question_group(
    text: str,
    *,
    max_discovers: int,
    discover_budget_left: int | None = None,
    max_subtasks: int,
) -> ClarifyEmission | str:
    """相位①发射解析＋schema 校验（拒因回喂——无 repair）。

    四动作闭世界＋分派（`specs/parsing.md` 行为 2）；`discover_budget_left`＝本 run 剩余发现
    预算（超预算的 discover 发射确定性拦截，不靠模型自律），其拒因以机读前缀「发现预算」开头；
    `finalize` 支零载荷直通（不读 payload）；`thought`／`note` 经字符串归一随定形携带；
    payload 无键白名单（四动作之外的未知键静默忽略——V1 事实面 D-L1a-14）。
    """
    payload = extract_plan_json(text)
    if payload is None:
        return json_syntax_feedback(text, "澄清发射不可解析——只输出一个 JSON")
    action = payload.get("action")
    try:
        action_in_world = action in CLARIFY_ACTIONS
    except TypeError:  # 不可哈希形（对象／数组）——V1 裸抛收口为拒因（差异点②）
        action_in_world = False
    if not action_in_world:
        return f"action 缺失或越界（{'/'.join(sorted(CLARIFY_ACTIONS))} 四值）：{action!r}"
    emission = ClarifyEmission(
        kind=str(action),
        thought=str(payload.get("thought") or ""),
        note=str(payload.get("note") or ""),
    )
    if emission.kind == CLARIFY_DISCOVER:
        raw_discovers = payload.get("discovers")
        if not isinstance(raw_discovers, list) or not raw_discovers:
            return "action=discover 缺 discovers（非空数组）"
        if len(raw_discovers) > max_discovers:
            return f"discovers 超出单次上限（≤{max_discovers} 支）"
        if discover_budget_left is not None and len(raw_discovers) > discover_budget_left:
            return (
                f"{BUDGET_REJECT_MARK}已尽（全 run ≤10，剩余 {discover_budget_left} 支）——"
                "台账全量已在上下文，禁止继续敲门：产出 decompose 问题组或 ask 反问"
            )
        items: list[dict[str, Any]] = []
        for raw in raw_discovers:
            if not isinstance(raw, dict) or "tool" not in raw:
                return "discovers 支缺 tool（{'tool': 名, 'args': {...}}）"
            tool = str(raw["tool"])
            args = raw.get("args") or {}
            if not isinstance(args, dict):  # V1 裸抛收口为拒（差异点②，拒文＝graph.py L616 字面）
                return f"发现工具 {tool} 的 args 须为对象"
            items.append({"tool": tool, "args": dict(args)})
        return replace(emission, discovers=tuple(items))
    if emission.kind == CLARIFY_DECOMPOSE:
        group = _question_group_of(payload.get("question_group"), max_subtasks=max_subtasks)
        if isinstance(group, str):
            return group
        return replace(emission, group=group)
    if emission.kind == CLARIFY_FINALIZE:
        return emission  # 定稿直答无载荷（thought/note 基形已携——sufficiency 模型判）
    # ask——问用户什么＋选项个数闭世界（判据与拒文真源 subtask.py L276-L290）
    raw_ask = payload.get("ask")
    if not isinstance(raw_ask, dict):
        return "action=ask 缺 ask 对象（{'prompt': …, 'options': […]}）"
    prompt = str(raw_ask.get("prompt") or "").strip()
    raw_options = raw_ask.get("options")
    options = (
        [str(item).strip() for item in raw_options if str(item).strip()]
        if isinstance(raw_options, list)
        else []
    )
    if not prompt:
        return "ask 缺 prompt（问用户什么必填）"
    if not 2 <= len(options) <= 4:
        return "ask 缺 options 或个数越界（2~4 个选项）"
    return replace(emission, ask_prompt=prompt, ask_options=tuple(options))


def parse_tool_match(content: str, group: QuestionGroup) -> tuple[SubtaskMatch, ...] | str:
    """相位②发射解析＋闭合世界对账（`matches` ↔ 问题组一一对应——schema 收口单点）。

    逐支按序 fail-fast：支须对象／`id` 归一后非空／`id` 在问题组 id 集内／组内不重复／`chain`
    归一后 ∈ 闭世界／`tool` 非空且＝该链唯一工具／按链必填（`data`→`plan.metric_slot`、
    `knowledge`→`retrieval_need.question`）／`caliber_key` 经 `str().strip()` 归一后零值域校验
    装载；组内存在未见 `id` → 覆盖缺口拒（拒文列缺失 id 全量）。返回顺序＝发射顺序
    （真源 recon/L1b R-L1b-05…R-L1b-21）。
    """
    payload = extract_plan_json(content)
    if payload is None:
        return json_syntax_feedback(content, "工具匹配不可解析——只输出一个 JSON")
    raw_matches = payload.get("matches")
    if not isinstance(raw_matches, list) or not raw_matches:
        return "缺 matches（非空数组——组内每个子问题恰一条）"
    group_ids = [subtask.id for subtask in group.subtasks]
    group_id_set = set(group_ids)
    matches: list[SubtaskMatch] = []
    seen: set[str] = set()
    for raw in raw_matches:
        if not isinstance(raw, dict):
            return "matches 支须为对象（{id/chain/tool/plan|retrieval_need}）"
        match_id = str(raw.get("id") or "").strip()
        if not match_id:
            return "matches 支缺 id"
        if match_id not in group_id_set:
            return f"matches id {match_id!r} 不在问题组内（闭合世界：{group_ids}）"
        if match_id in seen:
            return f"matches id 重复：{match_id!r}（每子问题恰一条匹配）"
        chain = str(raw.get("chain") or "").strip()
        if chain not in CHAIN_KINDS:
            return (
                f"matches {match_id} chain 越界"
                f"（{'/'.join(sorted(CHAIN_KINDS))}）：{chain!r}"
            )
        tool = str(raw.get("tool") or "").strip()
        if not tool:
            return f"matches {match_id} 缺 tool"
        if tool != _CHAIN_TOOL[chain]:
            return f"matches {match_id} chain/tool 不一致（{chain} 链须配 {_CHAIN_TOOL[chain]}）"
        plan: dict[str, Any] | None = None
        need: dict[str, Any] | None = None
        if chain == CHAIN_DATA:
            raw_plan = raw.get("plan")
            if not isinstance(raw_plan, dict):
                return f"matches {match_id} data 链缺 plan（data_query 计划草案对象）"
            if not str(raw_plan.get("metric_slot") or "").strip():
                return f"matches {match_id} plan 缺 metric_slot（必填非空）"
            plan = dict(raw_plan)
        else:
            raw_need = raw.get("retrieval_need")
            if not isinstance(raw_need, dict):
                return f"matches {match_id} knowledge 链缺 retrieval_need（参数对象）"
            if not str(raw_need.get("question") or "").strip():
                return f"matches {match_id} retrieval_need 缺 question（必填非空）"
            need = dict(raw_need)
        caliber_key = str(raw.get("caliber_key") or "").strip()
        seen.add(match_id)
        matches.append(
            SubtaskMatch(
                id=match_id,
                chain=chain,
                tool=tool,
                plan=plan,
                retrieval_need=need,
                caliber_key=caliber_key,
            )
        )
    missing = [group_id for group_id in group_ids if group_id not in seen]
    if missing:
        return f"matches 覆盖缺口（组内子问题缺匹配：{missing}）——每子问题恰一条"
    return tuple(matches)
