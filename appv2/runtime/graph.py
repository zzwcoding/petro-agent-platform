"""runtime.graph —— LangGraph StateGraph 六步 loop（specs/agent-loop.md 行为约定 1–7）。

六步：understand→plan→tool→observe→verify→answer（每步落 step 记录，INV-5）；
StateGraph＋条件边承载全部回环（ADR-0002：StateGraph 真承载 loop）：
- plan↔tool：计划校验不过→repair 一次→仍不过→need_clarify 转 ASK 帧（约定 3）；
- tool→tool：retryable 同参重试一次；工具 status=ask 自环进 interrupt 挂起
  （约定 4：挂起等人工，resume 带选择续跑——langgraph interrupt/Command）；
- 触界（预算三闸）→answer 收敛：交付已核实部分＋notice 明示未完成项（约定 7）。

红线自守：langgraph 只在本包 import（红线①）；模型调用全部经 GatewayChatModel
（红线②）；图状态 RunState 自有（红线③）。工具只经 ToolRegistry.call（受控行动链）。
核验步为确定性规则（断言级支撑核查——被引观察的数值须被断言文本复述，引标贴
无关行＝无据——＋分源列明），细化批可换更强实现，语义不破（INV-1/4）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Callable, Coroutine, Hashable
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from appv2.runtime.budget import budget_gate_hit, material_rows, unfinished_notice
from appv2.runtime.context import CompiledContext, ContextBuilder, trust_of
from appv2.runtime.events import EventBus
from appv2.runtime.llm import CALLER_PREFIX, GatewayChatModel
from appv2.runtime.state import (
    INTENT_ANSWER,
    INTENT_END,
    INTENT_OBSERVE,
    INTENT_PLAN,
    INTENT_TOOL,
    INTENT_VERIFY,
    STEP_ANSWER,
    STEP_OBSERVE,
    STEP_PLAN,
    STEP_TOOL,
    STEP_UNDERSTAND,
    STEP_VERIFY,
    Manifest,
    RunState,
)
from appv2.runtime.store import RunStore
from appv2.tools import (
    ASK_CLARIFY,
    ASK_EXTERNAL_TABLE_APPROVAL,
    CATEGORY_BAD_ARGS,
    CATEGORY_RETRYABLE,
    DATA_QUERY,
    STATUS_ASK,
    STATUS_FAILED,
    STATUS_OK,
    ToolContext,
    ToolRegistry,
)

# 计划产出工具闭世界（骨架版：plan 只在四工具内选择——registry.call 兜底拒未知名）。
_PLAN_TOOLS: frozenset[str] = frozenset(
    {DATA_QUERY, "semantic_query", "doc_retrieve", "graph_query"}
)

_CITE_RE = re.compile(r"\[(\d+)\]")
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_CANDIDATE_LINE = "指标候选"
# few-shot 样张（V2-09——L-04 golden 少样本同款形态「例：〈问句〉\n输出：〈合同样
# 张〉」）：样例问句取问数组数-明1 原句（eval/results/golden/plan-golden-v1.json
# L04-02 同源）；计划样张窗端点按「去年」锚 2026 年（golden anchor 2026-10-08 同值，
# anchor_scope=year 年内有效——跨年需随 golden 重锚同步更新）。
_SHUMING1_QUESTION = "去年各井每天的日产油量是多少？"
_UNDERSTAND_INSTRUCTION = (
    "识别问句：输出两行。第一行「理解：〈一句话〉」；"
    "第二行「指标候选：〈逗号分隔的指标名〉」（无可出数指标写：指标候选：无）。"
    f"例：{_SHUMING1_QUESTION}\n"
    "输出：理解：问去年全年各井逐日的日产油量明细。\n"
    "指标候选：日产油量"
)
_PLAN_INSTRUCTION = (
    "输出问数计划：只输出一个 JSON 对象。键：metric_slot（必填）、ranking（必填）、"
    "window_start/window_end（ISO 日期或 null——问句时间窗可定时必填，模糊/缺省时两槽均 null）、"
    "limit、direction、external_tables（越集外表名数组，无则省略）。"
    "只输出 JSON，不要解释。\n"
    f"例：{_SHUMING1_QUESTION}\n"
    "输出：{\"metric_slot\": \"日产油量\", \"ranking\": false, "
    "\"window_start\": \"2025-01-01\", \"window_end\": \"2026-01-01\"}"
)
_VERIFY_INSTRUCTION = (
    "起草答案：逐条事实断言必须带 [n] 引标（n＝观察材料序号）；材料未覆盖的部分"
    "不得断言；多来源不一致时逐源列明。"
)
# 审批卡批准后的答复基础＝引擎卡 impact 原文（零二次创作——合同值不出引擎侧）。
_EXTABLE_REJECT_BASIS_KEY = "impact"

# 模型 caller 名闭世界（B6 归因段——网关账本按此归因到步）＋模型键（executor
# 装配的 models 字典键＝caller 去前缀短名）。
CALLER_UNDERSTAND = f"{CALLER_PREFIX}.understand"
CALLER_PLAN = f"{CALLER_PREFIX}.plan"
CALLER_PLAN_REPAIR = f"{CALLER_PREFIX}.plan_repair"
CALLER_ANSWER_DRAFT = f"{CALLER_PREFIX}.answer_draft"
MODEL_UNDERSTAND = "understand"
MODEL_PLAN = "plan"
MODEL_PLAN_REPAIR = "plan_repair"
MODEL_ANSWER_DRAFT = "answer_draft"


class LoopDeps:
    """六节点共享依赖（registry/models/builder/store/bus——per-run bus 注入）。"""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        models: dict[str, GatewayChatModel],
        builder: ContextBuilder,
        store: RunStore,
        bus: EventBus,
    ) -> None:
        self.registry = registry
        self.models = models
        self.builder = builder
        self.store = store
        self.bus = bus

    def model(self, key: str) -> GatewayChatModel:
        model = self.models[key]
        return model


# ---------- 文本解析单点（模型应答合同的最小确定性解析） ----------

# understand JSON 降级形的合同键（V2-09 宽容化：中文主键＋真模型常见英文别名——
# 逐键取值，缺键不编造）。
_UNDERSTANDING_JSON_KEYS: tuple[str, ...] = ("理解", "understanding")
_CANDIDATES_JSON_KEYS: tuple[str, ...] = ("指标候选", "metric_candidates")


def _json_candidates(raw: Any) -> list[str]:
    """JSON 降级形的指标候选值归一（数组/分隔串两形——「无」＝空集，与两行式同口径）。"""
    if isinstance(raw, str):
        items: list[Any] = re.split(r"[、,，]", raw)
    elif isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        return []
    return [text for text in (str(item).strip() for item in items) if text and text != "无"]


def parse_understanding(content: str) -> tuple[str, list[str]]:
    """understand 应答解析（V2-09 两级宽容）：先两行合同式（「理解：／指标候选：」）；
    两行全缺时降级 JSON 子串提取（裸产/围栏产/散文包裹产同路——围栏容错承计划侧
    平衡块提取器），逐合同键取值、缺键不编造；两级全空＝（""·空集）如实上报——
    下游照走 plan 校验/repair→拒答链（真非法产不误解析）。"""
    understanding = ""
    candidates: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith(_CANDIDATE_LINE):
            body = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1]
            candidates = [
                item.strip()
                for item in re.split(r"[、,，]", body)
                if item.strip() and item.strip() != "无"
            ]
        elif line.startswith("理解"):
            understanding = line.split("：", 1)[-1].strip() if "：" in line else line
    if understanding or candidates:
        return understanding, candidates
    payload = extract_plan_json(content)
    if isinstance(payload, dict):
        for key in _UNDERSTANDING_JSON_KEYS:
            if payload.get(key):
                understanding = str(payload[key]).strip()
                break
        for key in _CANDIDATES_JSON_KEYS:
            if key in payload:
                candidates = _json_candidates(payload[key])
                break
    return understanding, candidates


def extract_plan_json(content: str) -> dict[str, Any] | None:
    """JSON 子串提取单点（首个平衡 {...} 块）：plan 应答与 understand 降级形共用——
    围栏产/散文包裹产同路（提取失败＝None——plan 走 repair，understand 保持空产出）。"""
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


# ---------- 核验步确定性规则（INV-1/INV-4 骨架版） ----------


def _assertion_chunks(line: str) -> list[tuple[int, str]]:
    """行→（引标 n, 其辖断言文本）列——辖断言＝行首/上一引标到本引标之间的文本。"""
    matches = list(_CITE_RE.finditer(line))
    chunks: list[tuple[int, str]] = []
    for position, match in enumerate(matches):
        start = matches[position - 1].end() if position else 0
        chunks.append((int(match.group(1)), line[start : match.start()]))
    return chunks


def _supported(
    citation: int, assertion: str, by_index: dict[int, dict[str, Any]]
) -> bool:
    """断言级支撑判定：被引观察 content 中的每个数值 token 须被断言文本复述——
    引标贴无关行（材料数值行内找不到）＝无支撑（P-006b·R9：非行级引标即过）。
    方向取「观察→行」：被引观察的每个数值须在行内被复述；行内来自问句语境的量
    （日期窗等）不作要求——误伤面最小。越界引标判无支撑；零数值观察（纯文本卡）
    恒过，语义充分性由确定性规则边界如实声明（细化批可换更强实现）。"""
    obs = by_index.get(citation)
    if obs is None:
        return False
    return all(token in assertion for token in _NUMBER_RE.findall(str(obs.get("content", ""))))


def verify_draft(
    draft: str, observations: list[dict[str, Any]]
) -> tuple[str, int, list[int], bool]:
    """草稿逐行断言级核验：返回（核验后文本, 改写数, 被引序号列, 是否分源）。

    - 逐引标抽取其辖断言文本做支撑判定：全部断言有据＝行保留（引标收进引用集）；
      无引标行/越界引标/断言与被引观察无关（材料数值未被复述）＝无据断言，整行
      改写「未找到（材料未披露）」（INV-1——禁止无据断言进答案）；
    - 被引观察中同一 subject（台账卡内容首段名称）≥2 支且值不同→追加分源列明块
      （INV-4——禁止无出处调和；agg_row 行级事实按 井@日 独立键，不入矛盾池）。
    """
    by_index = {int(obs["index"]): obs for obs in observations}
    cited: set[int] = set()
    rewritten = 0
    out_lines: list[str] = []
    for line in draft.splitlines():
        stripped = line.strip()
        if not stripped:
            out_lines.append(line)
            continue
        chunks = _assertion_chunks(stripped)
        if chunks and all(_supported(n, chunk, by_index) for n, chunk in chunks):
            cited.update(n for n, _ in chunks)
            out_lines.append(line)
        else:
            rewritten += 1
            out_lines.append(f"未找到（材料未披露）：{stripped}")
    split = False
    text = "\n".join(out_lines)
    split_members = _contradiction_members(cited, observations)
    if split_members:
        split = True
        text += "\n\n多来源不一致——分源列明（禁止无出处调和）：\n" + "\n".join(
            f"[{obs['index']}] {obs.get('source', '')}：{obs.get('content', '')}"
            for obs in split_members
        )
    return text, rewritten, sorted(cited), split


def _contradiction_members(
    cited: set[int], observations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """同 subject 值不同的被引观察（台账/检索卡；agg_row/notice 排除）。"""
    by_subject: dict[str, list[dict[str, Any]]] = {}
    for obs in observations:
        index = int(obs["index"])
        if index not in cited:
            continue
        kind = str((obs.get("locator") or {}).get("kind", ""))
        if kind in ("agg_row", "lineage", "notice"):
            continue  # 行级时序事实与元信息不入跨源矛盾池
        content = str(obs.get("content", ""))
        subject = content.split("：", 1)[0] if "：" in content else ""
        if subject:
            by_subject.setdefault(subject, []).append(obs)
    members: list[dict[str, Any]] = []
    for group in by_subject.values():
        if len(group) < 2:
            continue
        values = {str(obs.get("content", "")).split("：", 1)[-1] for obs in group}
        if len(values) > 1:
            members.extend(group)
    return sorted(members, key=lambda obs: int(obs["index"]))


# ---------- 节点公共位 ----------


def _step_record(
    seq: int,
    kind: str,
    title: str,
    manifest: Manifest | None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "seq": seq,
        "step": kind,
        "status": "ok",
        "title": title,
        "manifest": manifest.as_dict() if manifest is not None else None,
        "payload": payload or {},
    }


def _next_seq(state: RunState) -> int:
    return len(state.steps) + 1


def _converge(state: RunState, deps: LoopDeps) -> dict[str, Any]:
    """触界收敛（约定 7）：已取得材料如实交付＋notice 明示未完成项——不静默截断。"""
    gates = budget_gate_hit(state)
    notice = unfinished_notice(state, gates)
    raw = material_rows(state)
    if raw:
        body = "\n".join(f"- {obs.get('content', '')}" for obs in raw)
        answer = f"（预算触界收敛——已取得材料未及核验，如实原样交付）\n{body}"
    else:
        answer = "（预算触界收敛——未取得可交付观察材料，如实回报，不编造。）"
    deps.bus.emit("notice", dict(notice))
    return {
        "budget_hit": [*state.budget_hit, *gates],
        "notices": [*state.notices, notice],
        "answer": answer,
        "status": "completed",
        "next_intent": INTENT_ANSWER,
    }


def _gate_or_none(state: RunState, deps: LoopDeps) -> dict[str, Any] | None:
    """节点入口预算闸：触界返回收敛更新，未触界返回 None。

    收敛幂等（P-006b·R1，两入口单点）：budget_hit 非空＝收敛已发生——不再二次
    收敛（notice 恰 1 条、机读 gates 不重复追加）；已收敛 run 经 next_intent=
    answer 进 answer 节点正常收口（收敛答案落 answer 步＋文本出流）。
    """
    if state.budget_hit or not budget_gate_hit(state):
        return None
    return _converge(state, deps)


async def _complete(
    model: GatewayChatModel, context: CompiledContext
) -> str:
    """模型调用（CompiledContext.messages → ChatModel——红线②唯一路径）。"""
    messages = [
        SystemMessage(content=context.messages[0]["content"]),
        HumanMessage(content=context.messages[1]["content"]),
    ]
    reply = await model.ainvoke(messages)
    return str(reply.content)


def _observations_of(result: dict[str, Any]) -> list[dict[str, Any]]:
    return list(result.get("observations") or [])


# ---------- 六节点 ----------


def _make_understand(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    async def understand_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            return converged
        context = deps.builder.compile(
            state, step=STEP_UNDERSTAND, instruction=_UNDERSTAND_INSTRUCTION
        )
        content = await _complete(deps.model(MODEL_UNDERSTAND), context)
        understanding, candidates = parse_understanding(content)
        seq = _next_seq(state)
        record = _step_record(seq, STEP_UNDERSTAND, understanding or "理解未产出", context.manifest)
        deps.bus.emit(
            "step", {"step": STEP_UNDERSTAND, "seq": seq, "title": record["title"]}
        )
        if understanding:
            deps.bus.emit("text", {"content": understanding})
        return {
            "understanding": understanding,
            "metric_candidates": candidates,
            "manifests": [*state.manifests, context.manifest.as_dict()],
            "steps": [*state.steps, record],
            "next_intent": INTENT_PLAN,
        }

    return understand_node


def _make_plan(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    async def plan_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            return converged
        hint = state.replan_hint
        repair_reason = state.plan_error
        if not repair_reason and state.last_result is not None:
            error = state.last_result.get("error") or {}
            if (
                state.last_result.get("status") == STATUS_FAILED
                and error.get("category") == CATEGORY_BAD_ARGS
            ):
                repair_reason = str(error.get("message", "计划校验未过"))
        instruction = _PLAN_INSTRUCTION
        if repair_reason:
            instruction += f"\n上次计划被确定性校验拒绝：{repair_reason}——修正后重新只输出 JSON。"
        if hint:
            instruction += f"\n用户已补充：{hint}——请把它落进 plan_draft（时间窗转 ISO 日期）。"
        context = deps.builder.compile(state, step=STEP_PLAN, instruction=instruction)
        model_key = MODEL_PLAN_REPAIR if repair_reason else MODEL_PLAN
        content = await _complete(deps.model(model_key), context)
        plan = extract_plan_json(content)
        seq = _next_seq(state)
        updates: dict[str, Any] = {
            "replan_hint": "",
            "plan_error": "",
            "manifests": [*state.manifests, context.manifest.as_dict()],
            "steps": list(state.steps),
            "next_intent": INTENT_TOOL,
        }
        if plan is None:
            # JSON 不可解析：repair 一次；再败＝收敛（约定 7——不静默截断）。
            updates["steps"] = [*state.steps,
            _step_record(seq, STEP_PLAN, "计划解析失败", context.manifest)
            ]
            if state.repairs_since_input >= 1:
                notice = {
                    "type": "plan_unparsable",
                    "gates": [],
                    "content": "计划两轮均不可解析——如实收敛，未取得数据。",
                }
                deps.bus.emit("notice", dict(notice))
                updates["notices"] = [*state.notices, notice]
                updates["answer"] = "计划未能产出（模型输出两轮不可解析）——如实回报，不编造。"
                updates["next_intent"] = INTENT_ANSWER
            else:
                updates["plan_error"] = "模型输出不可解析（未产出 JSON 计划）"
                updates["repairs_since_input"] = state.repairs_since_input + 1
                updates["plan_repairs"] = state.plan_repairs + 1
                updates["next_intent"] = INTENT_PLAN
        elif "tool" in plan:
            # 通用工具计划形（骨架版合同：{"tool": 名称, "args": {...}}）。
            tool_name = str(plan.get("tool", DATA_QUERY))
            if tool_name not in _PLAN_TOOLS:
                tool_name = DATA_QUERY
            updates["tool_name"] = tool_name
            updates["tool_args"] = dict(plan.get("args") or {})
            updates["steps"] = [*state.steps,
            _step_record(seq, STEP_PLAN, f"计划：{tool_name}", context.manifest,
                             payload={"plan": plan})
            ]
        elif "metric_slot" in plan:
            # 问数计划草案形（plan_draft——schema 真源在 query 卡，runtime 只引用）。
            updates["tool_name"] = DATA_QUERY
            updates["tool_args"] = {"plan_draft": plan}
            updates["steps"] = [*state.steps,
            _step_record(seq, STEP_PLAN, f"计划：{DATA_QUERY}", context.manifest,
                             payload={"plan": plan})
            ]
        else:
            # 缺 metric_slot 的半形计划——按校验拒处理（走 repair/ASK 合同路径）。
            updates["last_result"] = {
                "status": STATUS_FAILED,
                "observations": [],
                "ask": None,
                "error": {
                    "category": CATEGORY_BAD_ARGS,
                    "message": "计划缺 metric_slot",
                    "hint": None,
                },
            }
            updates["steps"] = [*state.steps,
            _step_record(seq, STEP_PLAN, "计划缺 metric_slot", context.manifest)
            ]
        deps.bus.emit(
            "step",
            {"step": STEP_PLAN, "seq": seq, "title": updates["steps"][-1]["title"]},
        )
        return updates

    return plan_node


def _make_tool(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    async def tool_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            return converged
        # ——挂起恢复路径：interrupt 返回用户选择（恢复后节点重入，此分支先于工具执行——
        #  registry.call 全程恰一次，恢复不重跑已挂起的调用）。——
        if state.pending_ask is not None:
            return await _handle_choice(state, deps)
        return await _execute_tool(state, deps)

    return tool_node


async def _handle_choice(state: RunState, deps: LoopDeps) -> dict[str, Any]:
    frame = dict(state.pending_ask or {})
    payload = interrupt({"kind": frame.get("kind"), "frame": frame, "run_id": state.run_id})
    choice = payload if isinstance(payload, dict) else {"value": str(payload)}
    value = str(choice.get("value", ""))
    approval_id = choice.get("approval_id")
    resume_record = {"kind": frame.get("kind"), "value": value, "approval_id": approval_id}
    updates: dict[str, Any] = {
        "pending_ask": None,
        "resume_choices": [*state.resume_choices, resume_record],
        "next_intent": INTENT_PLAN,
    }
    if frame.get("kind") == ASK_CLARIFY:
        updates["replan_hint"] = value
        updates["repairs_since_input"] = 0  # 用户输入重置 repair 配额（合同：每输入一轮一次）
        deps.bus.emit(
            "step",
            {"step": STEP_TOOL, "seq": _next_seq(state), "title": f"澄清回收：{value}"},
        )
        updates["steps"] = [
            *state.steps,
            _step_record(_next_seq(state), STEP_TOOL, f"澄清回收：{value}",
                         None, payload={"resume": resume_record}),
        ]
        return updates
    # ——外表越集审批（接线①/③：choice.approval_id 留痕；批准重跑受骨架上限 1 轮约束）——
    if value == "批准":
        notice = {
            "type": "approval_recorded",
            "gates": [],
            "content": f"审批单号 {approval_id} 已留痕（resume 留痕，可回溯）。",
        }
        deps.bus.emit("notice", dict(notice))
        updates["notices"] = [*state.notices, notice]
        if state.extable_rounds >= 1:
            notice = {
                "type": "approval_gate_pending",
                "gates": [],
                "content": (
                    f"审批已通过并留痕（单号 {approval_id}），但权威引擎侧闸未放行续跑"
                    "——骨架版如实收口，待引擎侧审批放行接线。"
                ),
            }
            deps.bus.emit("notice", dict(notice))
            updates["notices"] = [*state.notices, notice]
            updates["answer"] = (
                f"外表引用审批已通过（单号 {approval_id}）；权威引擎侧闸未放行续跑，"
                "如实收口不冒充。"
            )
            updates["next_intent"] = INTENT_ANSWER
        else:
            updates["approved_ids"] = [*state.approved_ids, str(approval_id or "")]
            updates["extable_rounds"] = state.extable_rounds + 1
            updates["next_intent"] = INTENT_TOOL
    else:
        impact = str((frame.get("detail") or {}).get(_EXTABLE_REJECT_BASIS_KEY, ""))
        updates["draft"] = f"外表引用审批驳回：{impact}"
        updates["next_intent"] = INTENT_ANSWER
    deps.bus.emit(
        "step",
        {"step": STEP_TOOL, "seq": _next_seq(state), "title": f"审批回收：{value}"},
    )
    updates["steps"] = [
        *state.steps,
        _step_record(_next_seq(state), STEP_TOOL, f"审批回收：{value}",
                     None, payload={"resume": resume_record}),
    ]
    return updates


async def _execute_tool(state: RunState, deps: LoopDeps) -> dict[str, Any]:
    tool_name = state.tool_name or ""
    timeout = float(state.budget.get("tool_timeout_seconds", 30.0))
    ctx = ToolContext(
        actor=state.actor,
        budget=4,
        metric_candidates=tuple(state.metric_candidates) or None,
    )
    result: Any = None
    try:
        result = await asyncio.wait_for(
            deps.registry.call(tool_name, state.tool_args, ctx), timeout=timeout
        )
    except TimeoutError:
        result = None
    seq = _next_seq(state)
    if result is None:
        # 单工具超时闸（约定 7 三闸之三）——同参重试一次（retryable 通道）。
        return _apply_result(
            state,
            deps,
            {
                "status": STATUS_FAILED,
                "observations": [],
                "ask": None,
                "error": {
                    "category": CATEGORY_RETRYABLE,
                    "message": f"工具 {tool_name} 超 {timeout:g}s 未返回（单工具超时闸）",
                    "hint": "可重试——同参重调一次",
                },
            },
            seq,
            timed_out=True,
        )
    return _apply_result(state, deps, _result_dict(result), seq)


def _result_dict(result: Any) -> dict[str, Any]:  # ToolResult
    """ToolResult → dict 投影（Observation/AskFrame/ToolError 逐字段原样）。"""
    return {
        "status": result.status,
        "observations": [
            {
                "content": obs.content,
                "source": obs.source,
                "source_id": obs.source_id,
                "version": obs.version,
                "freshness": obs.freshness,
                "scope": obs.scope,
                "locator": dict(obs.locator),
            }
            for obs in result.observations
        ],
        "ask": (
            {
                "kind": result.ask.kind,
                "prompt": result.ask.prompt,
                "options": list(result.ask.options),
                "detail": dict(result.ask.detail) if result.ask.detail else None,
            }
            if result.ask is not None
            else None
        ),
        "error": (
            {
                "category": result.error.category,
                "message": result.error.message,
                "hint": result.error.hint,
            }
            if result.error is not None
            else None
        ),
    }


def _apply_result(
    state: RunState,
    deps: LoopDeps,
    result: dict[str, Any],
    seq: int,
    *,
    timed_out: bool = False,
) -> dict[str, Any]:
    """工具结果→状态更新与路由（bad_args repair/ASK、retryable 重试、refused 如实转答）。"""
    status = result["status"]
    title = f"工具 {state.tool_name or '?'}：{status}" + ("（超时）" if timed_out else "")
    deps.bus.emit(
        "tool",
        {"tool": state.tool_name, "status": status, "seq": seq,
         "message": (
             (result.get("error") or {}).get("message") if status == STATUS_FAILED else None
         )},
    )
    updates: dict[str, Any] = {
        "last_result": result,
        "steps": [*state.steps, _step_record(seq, STEP_TOOL, title, None,
                                                   payload={"tool": state.tool_name,
                                                            "status": status})],
    }
    if status == STATUS_OK:
        updates["next_intent"] = INTENT_OBSERVE
    elif status == STATUS_ASK:
        frame = dict(result.get("ask") or {})
        # 接线③（V2-03 偏差 7）：runtime 换 run 前缀种子——run 可溯＋引擎种子保留。
        if frame.get("kind") == ASK_EXTERNAL_TABLE_APPROVAL:
            detail = dict(frame.get("detail") or {})
            engine_seed = str(detail.get("approval_id", ""))
            if engine_seed:
                detail["approval_id"] = reseed_approval_id(state.run_id, engine_seed)
                frame["detail"] = detail
        updates["pending_ask"] = frame
        updates["next_intent"] = INTENT_TOOL  # 自环进 interrupt（挂起；恢复不重跑调用）
        # ask 帧＝挂起信号（行为约定 4：事件流发 ask 帧后正常收束——V2-07 SSE 出口）。
        deps.bus.emit("ask", {"frame": frame, "run_id": state.run_id})
    elif (result.get("error") or {}).get("category") == CATEGORY_BAD_ARGS:
        if state.repairs_since_input < 1:
            updates["repairs_since_input"] = state.repairs_since_input + 1
            updates["plan_repairs"] = state.plan_repairs + 1
            updates["next_intent"] = INTENT_PLAN  # 约定 3：校验不过→repair 一次
        else:
            # 仍不过（用户未补充新输入）＝不可修复的确定性拒——拒因原样如实转答
            # （骨架裁定：无限澄清循环不合同；可修复/终拒的 richer 契约归细化批
            # 提设计仓——窗界越界类（「今天」）按 V2-03 偏差 4 维持 refuse）。
            reason = str((result.get("error") or {}).get("message", "计划校验未过"))
            updates["draft"] = reason
            notice = {
                "type": "refused",
                "gates": [],
                "content": f"计划校验两轮未过——拒因如实转答：{reason}",
            }
            deps.bus.emit("notice", dict(notice))
            updates["notices"] = [*state.notices, notice]
            updates["next_intent"] = INTENT_ANSWER
    elif (result.get("error") or {}).get("category") == CATEGORY_RETRYABLE:
        if state.tool_retries < 1:
            updates["tool_retries"] = state.tool_retries + 1
            updates["next_intent"] = INTENT_TOOL  # 同参重试一次
        else:
            notice = {
                "type": "tool_unavailable",
                "gates": [],
                "content": f"工具 {state.tool_name} 重试后仍不可用——如实收敛。"
                           f"（{(result.get('error') or {}).get('message', '')}）",
            }
            deps.bus.emit("notice", dict(notice))
            updates["notices"] = [*state.notices, notice]
            updates["next_intent"] = INTENT_ANSWER
    else:  # refused（闸拒）——拒因原样如实转答，不重试不改写
        reason = str((result.get("error") or {}).get("message", "口径/数据闸拒"))
        updates["draft"] = reason
        # 机读 notice（P-006b·R3）——与 bad_args 两轮拒/tool_unavailable 通道同形，
        # V2-05 闸态机读分型在 runtime 侧对齐（按 notice 类型消费的面不漏直接闸拒）。
        notice = {
            "type": "refused",
            "gates": [],
            "content": f"口径/数据闸拒——拒因如实转答：{reason}",
        }
        deps.bus.emit("notice", dict(notice))
        updates["notices"] = [*state.notices, notice]
        updates["next_intent"] = INTENT_ANSWER
    deps.bus.emit(
        "step", {"step": STEP_TOOL, "seq": seq, "title": title}
    )
    return updates


def reseed_approval_id(run_id: str, engine_seed: str) -> str:
    """审批单号 run 前缀重种子（接线③——V2-03 偏差 7：引擎表名种子保留可溯）。"""
    return f"{run_id}#{engine_seed}"


def _make_observe(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    async def observe_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            return converged
        result = state.last_result or {}
        incoming = _observations_of(result)
        base_index = len(state.observations)
        indexed: list[dict[str, Any]] = []
        for offset, obs in enumerate(incoming, start=1):
            entry = dict(obs)
            entry["index"] = base_index + offset
            entry["trust"] = trust_of(entry)
            indexed.append(entry)
        seq = _next_seq(state)
        title = f"观察入栈 {len(indexed)} 支"
        deps.bus.emit("step", {"step": STEP_OBSERVE, "seq": seq, "title": title})
        for obs in indexed:
            if (obs.get("locator") or {}).get("kind") == "notice":
                # 闸依据/截断声明＝notice 信号（机读分型——拦停非数据）。
                deps.bus.emit(
                    "notice",
                    {
                        "type": str((obs.get("locator") or {}).get("notice_type", "notice")),
                        "gates": [],
                        "content": str(obs.get("content", "")),
                    },
                )
            deps.bus.emit(
                "observation",
                {
                    "index": obs["index"],
                    "source": obs.get("source", ""),
                    "content": obs.get("content", ""),
                    "trust": obs.get("trust", ""),
                },
            )
        record = _step_record(seq, STEP_OBSERVE, title, None,
                              payload={"count": len(indexed)})
        return {
            "observations": [*state.observations, *indexed],
            "steps": [*state.steps, record],
            "next_intent": INTENT_VERIFY,
        }

    return observe_node


def _make_verify(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    async def verify_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            return converged
        material = [
            obs
            for obs in state.observations
            if (obs.get("locator") or {}).get("kind") != "notice"
        ]
        if not material:
            # 零实质材料（闸拦停/纯 notice/零观察）——闸依据如实转答，不编不冒充；
            # 拒答话术（refused 直达的 draft）原样过核验（拒绝话术非断言）。
            if state.draft and not state.observations:
                text = state.draft
            else:
                notice_texts = [
                    str(obs.get("content", "")) for obs in state.observations
                ]
                body = "；".join(t for t in notice_texts if t)
                text = (
                    f"{body}（闸依据如实转答——零数值，不冒充出数。）"
                    if body
                    else "（未取得观察材料——如实回报，不编造。）"
                )
            rewritten, cited, split = 0, list[int](), False
            manifest: Manifest | None = None
        else:
            context = deps.builder.compile(
                state, step=STEP_VERIFY, instruction=_VERIFY_INSTRUCTION
            )
            content = await _complete(deps.model(MODEL_ANSWER_DRAFT), context)
            draft = content.strip() or "（模型未产出草稿——如实收口。）"
            text, rewritten, cited, split = verify_draft(draft, state.observations)
            manifest = context.manifest
        verdict = {
            "supported": len(cited),
            "rewritten": rewritten,
            "split": split,
            "cited": cited,
        }
        seq = _next_seq(state)
        title = f"核验：支撑 {len(cited)}｜改写 {rewritten}｜分源 {'是' if split else '否'}"
        deps.bus.emit("step", {"step": STEP_VERIFY, "seq": seq, "title": title})
        deps.bus.emit("verdict", dict(verdict))
        if rewritten:
            deps.bus.emit(
                "notice",
                {"type": "unsupported_claim", "gates": [],
                 "content": f"核验步改写无据断言 {rewritten} 行（INV-1——禁止无据断言进答案）"},
            )
        if split:
            deps.bus.emit(
                "notice",
                {"type": "contradiction_split", "gates": [],
                 "content": "多来源不一致——答案分源列明（INV-4——禁止无出处调和）"},
            )
        updates: dict[str, Any] = {
            "draft": text,
            "verdict": verdict,
            "steps": [*state.steps, _step_record(seq, STEP_VERIFY, title, manifest)],
            "next_intent": INTENT_ANSWER,
        }
        if manifest is not None:
            updates["manifests"] = [*state.manifests, manifest.as_dict()]
        return updates

    return verify_node


def _make_answer(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    async def answer_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            converged["next_intent"] = INTENT_END  # 收敛路由终点（防 answer→answer 环）
            return converged
        verdict = state.verdict or {}
        cited: list[int] = list(verdict.get("cited") or [])
        by_index = {int(obs["index"]): obs for obs in state.observations}
        answer = state.draft or state.answer or "（未取得可交付答案——如实回报，不编造。）"
        if cited:
            lines = [
                f"[{index}] {by_index[index].get('source', '')} · "
                f"{by_index[index].get('source_id', '')}（{by_index[index].get('trust', '')}）"
                for index in cited
                if index in by_index
            ]
            answer += "\n\n引用：\n" + "\n".join(lines)
        digest = hashlib.sha256(
            json.dumps(state.manifests, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        seq = _next_seq(state)
        title = "答案收口"
        deps.bus.emit("step", {"step": STEP_ANSWER, "seq": seq, "title": title})
        for index in cited:
            obs = by_index.get(index)
            if obs is not None:
                deps.bus.emit(
                    "citation",
                    {"index": index, "source": obs.get("source", ""),
                     "source_id": obs.get("source_id", ""), "trust": obs.get("trust", "")},
                )
        deps.bus.emit("text", {"content": answer})
        deps.bus.emit(
            "verdict",
            {"status": "completed", "run_id": state.run_id, "manifest_digest": digest},
        )
        return {
            "answer": answer,
            "status": "completed",
            "manifest_digest": digest,
            "steps": [*state.steps, _step_record(seq, STEP_ANSWER, title, None)],
            "next_intent": INTENT_END,
        }

    return answer_node


# ---------- 图装配（六节点＋条件边——StateGraph 真承载 loop） ----------

_ROUTES: dict[str, dict[Hashable, str]] = {
    STEP_UNDERSTAND: {INTENT_PLAN: STEP_PLAN, INTENT_ANSWER: STEP_ANSWER, INTENT_END: END},
    STEP_PLAN: {
        INTENT_TOOL: STEP_TOOL,
        INTENT_PLAN: STEP_PLAN,
        INTENT_ANSWER: STEP_ANSWER,
        INTENT_END: END,
    },
    STEP_TOOL: {
        INTENT_TOOL: STEP_TOOL,
        INTENT_PLAN: STEP_PLAN,
        INTENT_OBSERVE: STEP_OBSERVE,
        INTENT_ANSWER: STEP_ANSWER,
        INTENT_END: END,
    },
    STEP_OBSERVE: {INTENT_VERIFY: STEP_VERIFY, INTENT_ANSWER: STEP_ANSWER, INTENT_END: END},
    STEP_VERIFY: {INTENT_ANSWER: STEP_ANSWER, INTENT_END: END},
    STEP_ANSWER: {INTENT_END: END},
}


def _route(state: RunState) -> str:
    return state.next_intent or INTENT_ANSWER


def _node_of(
    fn: Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]],
) -> Any:
    """add_node 形参面（恒等转换——形认缝）。

    langgraph add_node 的 `_Node` Protocol（NodeInputT 逆变＋StateLike 上界）在
    mypy 下对「工厂返回的 async callable」解不出泛型（最小复现在案：直接 def
    函数可绑定，Callable 值绑定为 Never）——恒等转换收口这处框架类型限制，
    运行时零行为差；六节点签名仍受本模块 Callable 注记约束。
    """
    return fn


def build_graph(deps: LoopDeps, *, checkpointer: Any = None) -> Any:
    """编译六步图（checkpointer 由 executor 注入——挂起/恢复的存储机制）。"""
    builder = StateGraph(RunState)
    builder.add_node(STEP_UNDERSTAND, _node_of(_make_understand(deps)))
    builder.add_node(STEP_PLAN, _node_of(_make_plan(deps)))
    builder.add_node(STEP_TOOL, _node_of(_make_tool(deps)))
    builder.add_node(STEP_OBSERVE, _node_of(_make_observe(deps)))
    builder.add_node(STEP_VERIFY, _node_of(_make_verify(deps)))
    builder.add_node(STEP_ANSWER, _node_of(_make_answer(deps)))
    builder.add_edge(START, STEP_UNDERSTAND)
    for name, mapping in _ROUTES.items():
        builder.add_conditional_edges(name, _route, mapping)
    return builder.compile(checkpointer=checkpointer)
