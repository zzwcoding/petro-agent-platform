"""runtime.subtask —— 子任务图 schema（V2-34 票面任务 2——LangGraph 校验单点）。

四相位的两道 schema 收口（LLM 出语义，本模块出结构判定——零 LLM 纯校验）：

- 相位①业务澄清发射（parse_question_group）：discover｜decompose｜ask 三动作
  闭世界。decompose 产出 QuestionGroup——subtasks[{id/question/ledger_notes/
  chain?/tool?}]，子问题上限 ≤4（Owner 认可值）；ledger_notes 必填非空（台账
  注释纪律：从词典层注入块逐字转抄，前置条件机按注释过闸）。
- 相位②工具匹配发射（parse_tool_match）：matches 与问题组闭合世界对账——组内
  每个子问题恰一条匹配（缺/多/未知 id 均拒）；chain/tool 一致（data→data_query、
  knowledge→doc_retrieve）；data 链必带 plan（metric_slot 非空）、knowledge 链
  必带 retrieval_need（question 非空）；caliber_key 可选（B5——场景词落定的口径
  支，前置条件机做合法口径校验，QueryPlan 域面零改动）。

extract_plan_json（JSON 平衡块提取单点）自 graph.py 迁入本模块——决策发射与
understand 降级形共用（graph 侧 re-export 保持既有名字可用）。

拒因返回 str（回喂 LLM 重发射——无 repair，与 parse_decision 同款契约）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any

# ---------- 子任务图合同常量 ----------

# 子问题上限（Owner 2026-10-09 认可值——ADR-0005「子问题 ≤4」）。
MAX_SUBTASKS_CONTRACT = 4

# chain 闭世界（子问题→工具链两值）。
CHAIN_DATA = "data"
CHAIN_KNOWLEDGE = "knowledge"
CHAIN_KINDS: frozenset[str] = frozenset({CHAIN_DATA, CHAIN_KNOWLEDGE})

# 工具闭世界（chain→tool 一致性收口——与 tools 层工具名同源）。
TOOL_DATA_QUERY = "data_query"
TOOL_DOC_RETRIEVE = "doc_retrieve"
_CHAIN_TOOL: dict[str, str] = {
    CHAIN_DATA: TOOL_DATA_QUERY,
    CHAIN_KNOWLEDGE: TOOL_DOC_RETRIEVE,
}

# 相位①动作闭世界（发现/分解/反问——与 ReAct 决策四动作分立：分解发射进
# 固定代码四相位管线，不再直达 execute）。
CLARIFY_DISCOVER = "discover"
CLARIFY_DECOMPOSE = "decompose"
CLARIFY_ASK = "ask"
CLARIFY_ACTIONS: frozenset[str] = frozenset(
    {CLARIFY_DISCOVER, CLARIFY_DECOMPOSE, CLARIFY_ASK}
)

# 发现预算闸拒因标记（graph 澄清节点消费：预算驱动的 discover 拒不占轮——
# 轮＝回炉循环周期，钻取面由发现预算闸自己守）。
BUDGET_REJECT_MARK = "发现预算"


def extract_plan_json(content: str) -> dict[str, Any] | None:
    """JSON 子串提取单点（首个平衡 {...} 块）：四相位两道 schema 与决策发射、
    understand 降级形共用——围栏产/散文包裹产同路（提取失败＝None）。"""
    start = content.find("{")
    if start < 0:
        return None
    depth = 0
    for position in range(start, len(content)):
        if content[position] == "{":
            depth += 1
        elif content[position] == "}":
            depth -= 1
            if depth == 0:
                try:
                    loaded = json.loads(content[start : position + 1])
                except json.JSONDecodeError:
                    return None
                return loaded if isinstance(loaded, dict) else None
    return None


# ---------- 相位①产物：QuestionGroup（子任务图） ----------


@dataclass(frozen=True, slots=True)
class Subtask:
    """子问题（问题组最小单元——id/问题/台账注释＋工具链提议）。"""

    id: str
    question: str
    ledger_notes: str
    chain: str = ""  # 提议（可空——相位②收口定案）
    tool: str = ""  # 提议（可空——相位②收口定案）

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "question": self.question,
            "ledger_notes": self.ledger_notes,
        }
        if self.chain:
            payload["chain"] = self.chain
        if self.tool:
            payload["tool"] = self.tool
        return payload


@dataclass(frozen=True, slots=True)
class QuestionGroup:
    """问题组（相位①产物——带台账注释的子任务图）。"""

    subtasks: tuple[Subtask, ...]

    def as_payload(self) -> dict[str, Any]:
        return {"subtasks": [st.as_payload() for st in self.subtasks]}


@dataclass(frozen=True, slots=True)
class ClarifyEmission:
    """相位①发射（三动作闭世界的定型形——step payload 断言面）。"""

    kind: str  # discover|decompose|ask
    group: QuestionGroup | None = None
    discovers: tuple[dict[str, Any], ...] = ()
    ask_prompt: str = ""
    ask_options: tuple[str, ...] = ()
    thought: str = ""
    note: str = ""

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"action": self.kind}
        if self.thought:
            payload["thought"] = self.thought
        if self.note:
            payload["note"] = self.note
        if self.group is not None:
            payload["question_group"] = self.group.as_payload()
        if self.discovers:
            payload["discovers"] = [dict(item) for item in self.discovers]
        if self.ask_prompt:
            payload["ask"] = {
                "prompt": self.ask_prompt,
                "options": list(self.ask_options),
            }
        return payload


def _question_group_of(raw: Any, *, max_subtasks: int) -> QuestionGroup | str:
    """question_group 载荷校验（subtasks 闭合世界——上限/必填键/提议值域）。"""
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
            return f"subtasks {subtask_id} chain 越界（{'/'.join(sorted(CHAIN_KINDS))}）：{chain!r}"
        tool = str(item.get("tool") or "").strip()
        if tool and tool not in set(_CHAIN_TOOL.values()):
            return (
                f"subtasks {subtask_id} tool 越界"
                f"（{'/'.join(sorted(_CHAIN_TOOL.values()))}）：{tool!r}"
            )
        seen.add(subtask_id)
        subtasks.append(
            Subtask(
                id=subtask_id, question=question, ledger_notes=ledger_notes,
                chain=chain, tool=tool,
            )
        )
    return QuestionGroup(subtasks=tuple(subtasks))


def parse_question_group(
    content: str,
    *,
    max_discovers: int = 2,
    discover_budget_left: int | None = None,
    max_subtasks: int = MAX_SUBTASKS_CONTRACT,
) -> ClarifyEmission | str:
    """相位①发射解析＋schema 校验（拒因回喂——无 repair）。

    discover_budget_left＝本 run 剩余发现预算（全 run ≤10 合同闸的执行面——
    超预算的 discover 发射确定性拦截，不靠模型自律）。
    """
    payload = extract_plan_json(content)
    if payload is None:
        return "澄清发射不可解析（未产出 JSON 对象）——只输出一个 JSON"
    action = payload.get("action")
    if action not in CLARIFY_ACTIONS:
        return (
            f"action 缺失或越界（{'/'.join(sorted(CLARIFY_ACTIONS))} 三值）：{action!r}"
        )
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
            items.append({"tool": str(raw["tool"]), "args": dict(raw.get("args") or {})})
        return replace(emission, discovers=tuple(items))
    if emission.kind == CLARIFY_DECOMPOSE:
        group = _question_group_of(payload.get("question_group"), max_subtasks=max_subtasks)
        if isinstance(group, str):
            return group
        return replace(emission, group=group)
    # ask——与决策发射 ask 同形
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


# ---------- 相位②产物：工具匹配（独立 schema 收口点——R2） ----------


@dataclass(frozen=True, slots=True)
class SubtaskMatch:
    """子问题→工具链定案（相位②产物——前置条件机与批量执行的输入）。"""

    id: str
    chain: str
    tool: str
    plan: dict[str, Any] | None = None
    retrieval_need: dict[str, Any] | None = None
    caliber_key: str = ""  # B5：场景词落定的口径支 key（可空）

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"id": self.id, "chain": self.chain, "tool": self.tool}
        if self.plan is not None:
            payload["plan"] = dict(self.plan)
        if self.retrieval_need is not None:
            payload["retrieval_need"] = dict(self.retrieval_need)
        if self.caliber_key:
            payload["caliber_key"] = self.caliber_key
        return payload


def parse_tool_match(content: str, group: QuestionGroup) -> tuple[SubtaskMatch, ...] | str:
    """相位②发射解析＋闭合世界对账（matches ↔ 问题组一一对应——schema 收口单点）。"""
    payload = extract_plan_json(content)
    if payload is None:
        return "工具匹配不可解析（未产出 JSON 对象）——只输出一个 JSON"
    raw_matches = payload.get("matches")
    if not isinstance(raw_matches, list) or not raw_matches:
        return "缺 matches（非空数组——组内每个子问题恰一条）"
    group_ids = [st.id for st in group.subtasks]
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
            return f"matches {match_id} chain 越界（{'/'.join(sorted(CHAIN_KINDS))}）：{chain!r}"
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
                id=match_id, chain=chain, tool=tool, plan=plan, retrieval_need=need,
                caliber_key=caliber_key,
            )
        )
    missing = [gid for gid in group_ids if gid not in seen]
    if missing:
        return f"matches 覆盖缺口（组内子问题缺匹配：{missing}）——每子问题恰一条"
    return tuple(matches)
