"""runtime.graph —— LangGraph StateGraph ReAct 自主循环（V2-31 拍板七条＝设计合同）。

节点按 ReAct 周期（每步落 step 记录——过程态簿记留痕；INV-5 审计责任账经
security.audit 唯一写口落，见 runtime/audit.py）：

    understand → decision ⇄（discover／execute → observe）→ answer → verify → answer收口

- 轮＝LLM 决策周期（≤3 轮）；decision 发射结构化 JSON（task_type
  data|knowledge|mixed＋plan/retrieval_need），经 parse_decision schema 校验进
  固定代码执行（discover/execute 节点——工具只经 ToolRegistry.call 受控行动链）；
  观察回流后模型自主决策再轮或 finalize 定稿（ReAct：模型在循环里、工具在手边、
  观察回流转）。
- schema 校验失败取消自动 repair（拍板②）——拒因写进 decision_error 回喂
  LLM 由它重决策（同 caller 复用，无 repair 桶）；轮预算随拒回照耗。
- verify 节点保留零 LLM（拍板③）——INV-1/4 机器底线；P-020/V2-23 表格豁免
  继承（_supported 豁免域 agg_row/lineage 原样）。答案草稿由 answer 节点
  （caller answer）按引标合同起草，verify 只做确定性断言级核验。
- 澄清分级（拍板⑥）：时间窗歧义→模型按指南自动默认（近 30 天）＋note 注记；
  目标/对象/口径歧义→decision 发射 ask（合成 clarify 帧挂起，用户输入重置轮
  预算）；外表越集→data_query 引擎 ask 帧→审批挂起（不变，resume 批准重跑受
  骨架上限 1 轮约束）。
- 处理指南经 GuideProvider 缝消费（拍板⑦——V2-32 ontology 资产件整替注入，
  runtime/guide.py）。

StateGraph＋条件边承载全部回环（ADR-0002：StateGraph 真承载 loop）；
红线自守：langgraph 只在本包 import（红线①）；模型调用全部经 GatewayChatModel
（红线②，caller 桶＝understand/decision/answer 三值闭世界）；图状态 RunState
自有（红线③）。核验步确定性规则见 verify_draft（细化批可换更强实现，语义不破）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Callable, Coroutine, Hashable
from dataclasses import dataclass, replace
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from appv2.infra import clock
from appv2.runtime.budget import (
    MAX_DISCOVERS_PER_ROUND_CONTRACT,
    MAX_EXECUTES_PER_ROUND_CONTRACT,
    budget_gate_hit,
    material_rows,
    unfinished_notice,
)
from appv2.runtime.context import CompiledContext, ContextBuilder, trust_of
from appv2.runtime.events import EventBus
from appv2.runtime.guide import DefaultGuideProvider, GuideProvider
from appv2.runtime.llm import CALLER_PREFIX, GatewayChatModel
from appv2.runtime.state import (
    INTENT_ANSWER,
    INTENT_DECISION,
    INTENT_DISCOVER,
    INTENT_END,
    INTENT_EXECUTE,
    INTENT_OBSERVE,
    INTENT_VERIFY,
    STEP_ANSWER,
    STEP_DECISION,
    STEP_DISCOVER,
    STEP_EXECUTE,
    STEP_OBSERVE,
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
    DOC_RETRIEVE,
    SCHEMA_PROBE,
    SEMANTIC_QUERY,
    STATUS_ASK,
    STATUS_FAILED,
    STATUS_OK,
    ToolContext,
    ToolRegistry,
)

# ---------- 决策发射合同（结构化发射的运行时校验——拍板①②单点） ----------

ACTION_DISCOVER = "discover"
ACTION_EXECUTE = "execute"
ACTION_ASK = "ask"
ACTION_FINALIZE = "finalize"
ACTION_KINDS: frozenset[str] = frozenset(
    {ACTION_DISCOVER, ACTION_EXECUTE, ACTION_ASK, ACTION_FINALIZE}
)

# 任务型闭世界（结构化发射 task_type 三值——data|knowledge|mixed）。
TASK_DATA = "data"
TASK_KNOWLEDGE = "knowledge"
TASK_MIXED = "mixed"
TASK_KINDS: frozenset[str] = frozenset({TASK_DATA, TASK_KNOWLEDGE, TASK_MIXED})

# 同参重投机器闸（V2-37——P-026 复测残余 9/16 题同参重复执行耗 3 轮→形态收敛
# 堆叠的机器收口）：decision 出口对主执行载荷（plan/retrieval_need）的同参二次
# 发射确定性拦截——不再触工具，拒因回喂 LLM 由它重决策（finalize 带结果直答或
# 改参）。拦截只针对同参二次发射：改参／跨支新信息路径零误伤（_is_same_param_
# replay）；审批重投（last_execute 通道）与 retryable 同参重试不经 decision 出口，
# 不受闸辖（语义零漂移）。
GATE_SAME_PARAM_REPLAY = "same_param_replay"
SAME_PARAM_REPLAY_REASON = (
    "同参已执行（同参重执行零新信息）——带结果直答或改参"
    "（finalize 按观察材料作答，或换参数后再发射），不要重复发射同一计划"
)

# 发现工具闭世界（拍板④白名单的调用面——registry.call 兜底拒未知名）。
DISCOVER_TOOLS: frozenset[str] = frozenset({SEMANTIC_QUERY, SCHEMA_PROBE})

_CITE_RE = re.compile(r"\[(\d+)\]")
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_CANDIDATE_LINE = "指标候选"
# 权威观察承载（V2-23 豁免域＋P-024b 审查 S2 扩 fragment）：表格行/血缘卡/kb 检索
# 片段是权威观察本身——断言级「全数值复述」只辖自由文本断言，不辖对它们的转述
# （kb 长片段数值 token 十余个，全数值复述形同必吞——run-a2961c64 实测支撑
# 0｜改写 10；豁免仍有底：任一数值 token 重叠即支撑、零重叠照改，见 _supported）。
_CARRIER_KINDS = frozenset({"agg_row", "lineage", "fragment"})
# few-shot 样张（V2-09——L-04 golden 少样本同款形态「例：〈问句〉\n输出：〈合同样
# 张〉」）：样例问句取问数组数-明1 原句（eval/results/golden/plan-golden-v1.json
# L04-02 同源）；理解样张窗端点按「去年」锚 2026 年（golden anchor 2026-10-08 同值，
# anchor_scope=year 年内有效——跨年需随 golden 重锚同步更新）。
_SHUMING1_QUESTION = "去年各井每天的日产油量是多少？"
_UNDERSTAND_INSTRUCTION = (
    "识别问句：输出两行。第一行「理解：〈一句话〉」；"
    "第二行「指标候选：〈逗号分隔的指标名〉」（无可出数指标写：指标候选：无）。"
    f"例：{_SHUMING1_QUESTION}\n"
    "输出：理解：问去年全年各井逐日的日产油量明细。\n"
    "指标候选：日产油量"
)
# 答案起草合同（引标断言——verify 确定性核验的素材面）。
_ANSWER_INSTRUCTION = (
    "起草答案：逐条事实断言必须带 [n] 引标（n＝观察材料序号）；材料未覆盖的部分"
    "不得断言；多来源不一致时逐源列明。"
)
# 审批卡批准后的答复基础＝引擎卡 impact 原文（零二次创作——合同值不出引擎侧）。
_EXTABLE_REJECT_BASIS_KEY = "impact"

# 模型 caller 桶闭世界（B6 归因段——三桶无 repair；网关账本按此归因到步）＋
# 模型键（executor 装配的 models 字典键＝caller 去前缀短名）。
CALLER_UNDERSTAND = f"{CALLER_PREFIX}.understand"
CALLER_DECISION = f"{CALLER_PREFIX}.decision"
CALLER_ANSWER = f"{CALLER_PREFIX}.answer"
MODEL_UNDERSTAND = "understand"
MODEL_DECISION = "decision"
MODEL_ANSWER = "answer"
MODEL_KEYS: tuple[str, ...] = (MODEL_UNDERSTAND, MODEL_DECISION, MODEL_ANSWER)

# 图节点名（LangGraph 拓扑名——与 step 类型闭世界分立：understand 段记
# decision 类步 payload.phase=understand，六值闭世界不破）。
NODE_UNDERSTAND = "understand"
NODE_DECISION = "decision"
NODE_DISCOVER = "discover"
NODE_EXECUTE = "execute"
NODE_OBSERVE = "observe"
NODE_VERIFY = "verify"
NODE_ANSWER = "answer"


class LoopDeps:
    """ReAct 节点共享依赖（registry/models/builder/store/bus/guide——per-run bus 注入）。"""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        models: dict[str, GatewayChatModel],
        builder: ContextBuilder,
        store: RunStore,
        bus: EventBus,
        guide: GuideProvider | None = None,
        today: Any = None,
    ) -> None:
        self.registry = registry
        self.models = models
        self.builder = builder
        self.store = store
        self.bus = bus
        # 处理指南缝（拍板⑦）：缺省＝内置指南（V2-32 ontology 资产件可整替注入）。
        self.guide: GuideProvider = guide or DefaultGuideProvider(
            today=today if today is not None else clock.now().date()
        )

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
    两行全缺时降级 JSON 子串提取（裸产/围栏产/散文包裹产同路——围栏容错承决策侧
    平衡块提取器），逐合同键取值、缺键不编造；两级全空＝（""·空集）如实上报——
    下游照走决策轮（真非法产不误解析）。"""
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
    """JSON 子串提取单点（首个平衡 {...} 块）：决策发射与 understand 降级形共用——
    围栏产/散文包裹产同路（提取失败＝None——决策走拒因回喂，understand 保持空产出）。"""
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


# ---------- 决策发射 schema 校验（拍板①②：拒因回喂、无 repair 的闸单点） ----------


@dataclass(frozen=True, slots=True)
class DecisionEmission:
    """决策出口（结构化发射的定型形——行为断言锁在决策出口的机读投影）。"""

    action: str  # ACTION_* 四值闭世界
    thought: str = ""
    note: str = ""
    discovers: tuple[dict[str, Any], ...] = ()  # discover 发射（≤轮内上限）
    task_type: str = ""  # TASK_* 三值（execute 发射）
    plan: dict[str, Any] | None = None  # data_query plan_draft（data|mixed）
    retrieval_need: dict[str, Any] | None = None  # doc_retrieve args（knowledge|mixed）
    ask_prompt: str = ""  # ask 发射（澄清分级②——目标/对象/口径歧义）
    ask_options: tuple[str, ...] = ()

    def as_payload(self) -> dict[str, Any]:
        """决策出口投影（step 记录 payload——剧本钉测的断言面）。"""
        payload: dict[str, Any] = {"action": self.action}
        if self.thought:
            payload["thought"] = self.thought
        if self.note:
            payload["note"] = self.note
        if self.discovers:
            payload["discovers"] = [dict(item) for item in self.discovers]
        if self.task_type:
            payload["task_type"] = self.task_type
        if self.plan is not None:
            payload["plan"] = dict(self.plan)
        if self.retrieval_need is not None:
            payload["retrieval_need"] = dict(self.retrieval_need)
        if self.ask_prompt:
            payload["ask"] = {
                "prompt": self.ask_prompt,
                "options": list(self.ask_options),
            }
        return payload


# ---------- 同参重投机器闸（V2-37——载荷指纹与同参判定的单点） ----------


def _payload_fingerprint(payload: dict[str, Any]) -> str:
    """载荷规范指纹（键序归一的紧凑 JSON——同参判定的比较面）。"""
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _emission_fingerprints(
    plan: dict[str, Any] | None, retrieval_need: dict[str, Any] | None
) -> tuple[str, ...]:
    """发射载荷的按支执行指纹（单支单形——execute 侧实录同形，两面对得上）。

    data/knowledge 单支发射＝一支指纹；mixed＝两支各一。execute 侧按实际调用
    逐支实录（{"plan": …} 或 {"retrieval_need": …} 单键形）——故此处按支拆算，
    不算整发射混合形（那会永不匹配，闸空转）。
    """
    prints: list[str] = []
    if plan is not None:
        prints.append(_payload_fingerprint({"plan": plan, "retrieval_need": None}))
    if retrieval_need is not None:
        prints.append(_payload_fingerprint({"plan": None, "retrieval_need": retrieval_need}))
    return tuple(prints)


def _is_same_param_replay(emission: DecisionEmission, executed: list[str]) -> bool:
    """同参二次发射判定：发射载荷的全部已执行支都已在实录（mixed＝两支都已执行
    才算同参——任一支携新参＝有新信息，放行不拦，改参零误伤）。"""
    prints = _emission_fingerprints(emission.plan, emission.retrieval_need)
    return bool(prints) and all(item in executed for item in prints)


def parse_decision(
    content: str,
    *,
    max_discovers: int = MAX_DISCOVERS_PER_ROUND_CONTRACT,
    max_executes: int = MAX_EXECUTES_PER_ROUND_CONTRACT,
) -> DecisionEmission | str:
    """决策应答解析＋schema 校验（裸产/围栏产/散文包裹产同路——平衡块提取单点）。

    返回 DecisionEmission（合法发射）或 str（拒因——回喂 LLM 重决策，无 repair）。
    校验只判结构与闭世界（action/task_type/工具名/必填载荷/轮内上限）；载荷深形
    （plan 字段细节）归工具层 args_schema（bad_args 同路回喂——两道闸一个去处）。
    """
    payload = extract_plan_json(content)
    if payload is None:
        return "决策不可解析（未产出 JSON 对象）——只输出一个 JSON 决策"
    action = payload.get("action")
    if action not in ACTION_KINDS:
        return (
            f"action 缺失或越界（{'/'.join(sorted(ACTION_KINDS))} 四值）：{action!r}"
        )
    emission = DecisionEmission(
        action=str(action),
        thought=str(payload.get("thought") or ""),
        note=str(payload.get("note") or ""),
    )
    if emission.action == ACTION_DISCOVER:
        raw_discovers = payload.get("discovers")
        if not isinstance(raw_discovers, list) or not raw_discovers:
            return "action=discover 缺 discovers（非空数组，1~2 支）"
        if len(raw_discovers) > max_discovers:
            return f"discovers 超出轮内上限（≤{max_discovers} 支）"
        items: list[dict[str, Any]] = []
        for raw in raw_discovers:
            if not isinstance(raw, dict) or "tool" not in raw:
                return "discovers 支缺 tool（{'tool': 名, 'args': {...}}）"
            tool = str(raw["tool"])
            if tool not in DISCOVER_TOOLS:
                return (
                    f"未知发现工具 {tool!r}（{'/'.join(sorted(DISCOVER_TOOLS))}）"
                )
            args = raw.get("args") or {}
            if not isinstance(args, dict):
                return f"发现工具 {tool} 的 args 须为对象"
            items.append({"tool": tool, "args": dict(args)})
        return replace(emission, discovers=tuple(items))
    if emission.action == ACTION_EXECUTE:
        task_type = payload.get("task_type")
        if task_type not in TASK_KINDS:
            return (
                f"task_type 缺失或越界（{'/'.join(sorted(TASK_KINDS))} 三值）："
                f"{task_type!r}"
            )
        plan = payload.get("plan")
        need = payload.get("retrieval_need")
        if task_type in (TASK_DATA, TASK_MIXED):
            if not isinstance(plan, dict):
                return f"task_type={task_type} 缺 plan（data_query 计划草案对象）"
            if not str(plan.get("metric_slot") or "").strip():
                return "plan 缺 metric_slot（必填非空）"
        if task_type in (TASK_KNOWLEDGE, TASK_MIXED):
            if not isinstance(need, dict):
                return (
                    f"task_type={task_type} 缺 retrieval_need（doc_retrieve 参数对象）"
                )
            if not str(need.get("question") or "").strip():
                return "retrieval_need 缺 question（必填非空）"
        executes = 2 if task_type == TASK_MIXED else 1
        if executes > max_executes:
            return f"task_type=mixed 超出轮内主执行上限（≤{max_executes} 支）"
        return replace(
            emission,
            task_type=str(task_type),
            plan=dict(plan) if isinstance(plan, dict) else None,
            retrieval_need=dict(need) if isinstance(need, dict) else None,
        )
    if emission.action == ACTION_ASK:
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
    return emission  # finalize——零附加载荷


# ---------- 核验步确定性规则（INV-1/INV-4 骨架版——保留件零改动） ----------


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
    恒过，语义充分性由确定性规则边界如实声明（细化批可换更强实现）。
    V2-23 豁免＋P-024b S2 扩域：表格行/血缘卡/kb 片段（locator.kind ∈
    agg_row/lineage/fragment）是权威观察承载而非断言素材——只须复述任一数值
    token（行内容含日期/区块等随行数值、长片段含十余数值 token，「全数值
    复述」会把 LIMIT 截断下的整张明细表/整段 kb 片段吞成「未找到」——P-015
    数-明1 与 run-a2961c64 实测；豁免仍有底：零重叠＝引标贴无关行，照改——
    R9 反例不回退）。"""
    obs = by_index.get(citation)
    if obs is None:
        return False
    tokens = _NUMBER_RE.findall(str(obs.get("content", "")))
    if str((obs.get("locator") or {}).get("kind", "")) in _CARRIER_KINDS:
        return not tokens or any(token in assertion for token in tokens)
    return all(token in assertion for token in tokens)


def verify_draft(
    draft: str, observations: list[dict[str, Any]]
) -> tuple[str, int, list[int], bool]:
    """草稿逐行断言级核验：返回（核验后文本, 改写数, 被引序号列, 是否分源）。

    - 逐引标抽取其辖断言文本做支撑判定：全部断言有据＝行保留（引标收进引用集）；
      无引标数字行/越界引标/断言与被引观察无关（材料数值未被复述）＝无据断言，
      整行改写「未找到（材料未披露）」（INV-1——禁止无据断言进答案）。改写只管
      自由文本断言行：无引标且无数字的行（标题/表格头/分隔线等结构承载）不属
      断言，原样保留（V2-23）；表格行/血缘卡/kb 片段引挂豁免「全数值复述」（见
      _supported——零重叠仍改写，R9 反例不回退）；
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
        if not chunks and not _NUMBER_RE.search(stripped):
            # 非断言行（标题/表格头/分隔线/无数字纯文本——结构承载）不属改写辖域
            # （INV-1 管断言不管结构——V2-23：改写只管自由文本断言行）。
            out_lines.append(line)
            continue
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


def _lineage_closing_note(observations: list[dict[str, Any]]) -> str:
    """血缘卡⑤收口注记行（V2-23——LIMIT 收口披露确定性随答案：截断不静默）。
    引权威观察原文，零二次创作；无血缘卡（闸拦停/拒答链）＝空串不追加。"""
    for obs in observations:
        if (obs.get("locator") or {}).get("kind") != "lineage":
            continue
        for line in str(obs.get("content", "")).splitlines():
            stripped = line.strip()
            if stripped.startswith("⑤"):
                return stripped
    return ""


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


def _converge(state: RunState, deps: LoopDeps, *, gates: list[str]) -> dict[str, Any]:
    """触界收敛（有界终止）：已取得材料如实交付＋notice 明示未完成项——不静默截断。"""
    notice = unfinished_notice(state, gates)
    raw = material_rows(state)
    if raw:
        body = "\n".join(f"- {obs.get('content', '')}" for obs in raw)
        answer = f"（轮预算触界收敛——已取得材料未及核验，如实原样交付）\n{body}"
    else:
        answer = "（轮预算触界收敛——未取得可交付观察材料，如实回报，不编造。）"
    deps.bus.emit("notice", dict(notice))
    return {
        "budget_hit": [*state.budget_hit, *gates],
        "notices": [*state.notices, notice],
        "answer": answer,
        "draft_kind": "direct",
        "status": "completed",
        "next_intent": INTENT_ANSWER,
    }


def _gate_or_none(
    state: RunState, deps: LoopDeps, *, rounds_gate: bool = False
) -> dict[str, Any] | None:
    """节点入口预算闸：触界返回收敛更新，未触界返回 None。

    rounds_gate＝轮数闸开关（只 decision 入口开——轮内执行/定稿后段不受轮数闸
    拦；时长闸全节点守）。收敛幂等（P-006b·R1，多入口单点）：budget_hit 非空＝
    收敛已发生——不再二次收敛（notice 恰 1 条、机读 gates 不重复追加）；已收敛
    run 经 next_intent=answer 进 answer 节点正常收口（收敛答案落 answer 步＋
    文本出流）。
    """
    if state.budget_hit:
        return None
    gates = budget_gate_hit(state, include_rounds=rounds_gate)
    if not gates:
        return None
    return _converge(state, deps, gates=gates)


# CompiledContext.messages 的 role → langchain 消息类（多轮形态全消息映射——
# ADR-0006：历史轮含 assistant/user 交错，不再限定两条件形）。
_MESSAGE_CLS: dict[str, type] = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


async def _complete(
    model: GatewayChatModel, context: CompiledContext
) -> str:
    """模型调用（CompiledContext.messages 全量 → ChatModel——红线②唯一路径）。"""
    messages = [
        _MESSAGE_CLS[m["role"]](content=m["content"]) for m in context.messages
    ]
    reply = await model.ainvoke(messages)
    return str(reply.content)


def _observations_of(result: dict[str, Any]) -> list[dict[str, Any]]:
    return list(result.get("observations") or [])


def _ctx_of(state: RunState) -> ToolContext:
    return ToolContext(
        actor=state.actor,
        budget=4,
        metric_candidates=tuple(state.metric_candidates) or None,
    )


def _timeout_result(tool_name: str, timeout: float) -> dict[str, Any]:
    """单工具超时闸（三闸之三）——retryable 通道（同参重试一次）。"""
    return {
        "status": STATUS_FAILED,
        "observations": [],
        "ask": None,
        "error": {
            "category": CATEGORY_RETRYABLE,
            "message": f"工具 {tool_name} 超 {timeout:g}s 未返回（单工具超时闸）",
            "hint": "可重试——同参重调一次",
        },
    }


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


def _direct_answer(updates: dict[str, Any], text: str) -> None:
    """确定性直答标记（拒因/闸拒/收敛转答——answer 节点免起草免核验直接收口）。"""
    updates["draft"] = text
    updates["draft_kind"] = "direct"
    updates["next_intent"] = INTENT_ANSWER


def _clarify_capped_answer(state: RunState) -> str:
    """连环澄清截断的直答文本（P-024b 疑点2——带材料如实交付形，_converge 材料
    面同构；独立于预算三闸——不落 budget_hit，机读分型走 clarify_capped notice）。"""
    raw = material_rows(state)
    if raw:
        body = "\n".join(f"- {obs.get('content', '')}" for obs in raw)
        return f"（连续澄清截断——已取得材料如实交付，不再挂起）\n{body}"
    return "（连续澄清截断——未取得可交付观察材料，如实回报，不编造。）"


# ---------- 消息历史簿记（ADR-0006/V2-38——调用与输出/台账/回收的轮次落史单点） ----------


def _user_turn(content: str) -> dict[str, str]:
    return {"role": "user", "content": content}


def _assistant_turn(content: str) -> dict[str, str]:
    return {"role": "assistant", "content": content}


def _history_with(state: RunState, *turns: dict[str, str]) -> list[dict[str, str]]:
    """历史续写单点（只追加不改写——后续每步在完整历史上续写）。"""
    return [*state.history, *turns]


def _ledger_turn(
    tool_name: str, args: dict[str, Any], result: dict[str, Any]
) -> dict[str, str]:
    """执行台账段（V2-38 任务 2——「参数 → 结果：N 行／闸拒（拒因）」形落历史）。

    ok＝参数 → 结果：N 行；ask＝参数 → 结果：0 行（挂起：审批）；非 ok（校验拒/
    retryable/闸拒）＝参数 → 闸拒（拒因：…）——负信息如实落（同参重投由模型读
    台账自主避免，V2-37 机器闸降格兜底）。参数 JSON＝键序归一紧凑形（与 V2-37
    载荷指纹同规范）。
    """
    params = _payload_fingerprint(args)
    status = result["status"]
    if status == STATUS_OK:
        lines = len(result.get("observations") or [])
        return _user_turn(f"{tool_name} 参数：{params} → 结果：{lines} 行")
    if status == STATUS_ASK:
        return _user_turn(f"{tool_name} 参数：{params} → 结果：0 行（挂起：审批）")
    reason = str((result.get("error") or {}).get("message", "校验未过"))
    return _user_turn(f"{tool_name} 参数：{params} → 闸拒（拒因：{reason}）")


def reseed_approval_id(run_id: str, engine_seed: str) -> str:
    """审批单号 run 前缀重种子（接线③——V2-03 偏差 7：引擎表名种子保留可溯）。"""
    return f"{run_id}#{engine_seed}"


# ---------- 节点一：understand（理解——caller understand；记 decision 类步） ----------


def _make_understand(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    async def understand_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            return converged
        # 消息历史簿记（ADR-0006）：首问轮＝问题＋理解任务（追问 run 的前轮线程
        # 历史已在 state.history——executor 播种，此处续写新问轮）。
        context = deps.builder.compile(
            state,
            step="understand",
            instruction=(
                f"问题：{state.question}\n\n任务：{_UNDERSTAND_INSTRUCTION}"
            ),
            with_material=False,
        )
        content = await _complete(deps.model(MODEL_UNDERSTAND), context)
        understanding, candidates = parse_understanding(content)
        # 调用与输出入簿（当前轮原样＋模型原话——后续步在完整历史上续写）。
        history = _history_with(
            state,
            dict(context.messages[-1]),
            _assistant_turn(content),
        )
        seq = _next_seq(state)
        record = _step_record(
            seq, STEP_DECISION, understanding or "理解未产出", context.manifest,
            payload={"phase": "understand"},
        )
        deps.bus.emit(
            "step", {"step": STEP_DECISION, "seq": seq, "title": record["title"]}
        )
        if understanding:
            deps.bus.emit("text", {"content": understanding})
        return {
            "understanding": understanding,
            "metric_candidates": candidates,
            "history": history,
            "manifests": [*state.manifests, context.manifest.as_dict()],
            "steps": [*state.steps, record],
            "next_intent": INTENT_DECISION,
        }

    return understand_node


# ---------- 节点二：decision（ReAct 决策——caller decision；轮＝决策周期） ----------


def _decision_title(emission: DecisionEmission, rnd: int) -> str:
    if emission.action == ACTION_DISCOVER:
        names = "、".join(str(item.get("tool", "?")) for item in emission.discovers)
        return f"决策 r{rnd}：发现×{len(emission.discovers)}（{names}）"
    if emission.action == ACTION_EXECUTE:
        return f"决策 r{rnd}：执行 {emission.task_type}"
    if emission.action == ACTION_ASK:
        return f"决策 r{rnd}：澄清（{emission.ask_prompt[:24]}）"
    return f"决策 r{rnd}：定稿"


def _make_decision(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    async def decision_node(state: RunState) -> dict[str, Any]:
        # ——挂起恢复路径：interrupt 返回用户选择（恢复后节点重入，此分支先于
        #  闸与模型调用——挂起等人工不计预算）。——
        if state.pending_ask is not None:
            return await _handle_choice(state, deps)
        if (converged := _gate_or_none(state, deps, rounds_gate=True)) is not None:
            return converged
        max_discovers = int(
            state.budget.get(
                "max_discovers_per_round", MAX_DISCOVERS_PER_ROUND_CONTRACT
            )
        )
        max_executes = int(
            state.budget.get(
                "max_executes_per_round", MAX_EXECUTES_PER_ROUND_CONTRACT
            )
        )
        instruction = deps.guide.guide()
        instruction += "\n\n任务：输出本轮决策 JSON。"
        if state.decision_error:
            # 拍板②拒因回喂：schema/工具校验拒因进上下文——LLM 重决策（无 repair）。
            instruction += (
                f"\n上次决策被拒：{state.decision_error}——修正后重新输出 JSON。"
            )
        if state.user_hint:
            instruction += f"\n用户已补充：{state.user_hint}——请把它落进本轮决策。"
        context = deps.builder.compile(
            state, step=STEP_DECISION, instruction=instruction
        )
        content = await _complete(deps.model(MODEL_DECISION), context)
        # 消息历史簿记（ADR-0006）：本轮调用与输出入簿——无论发射合法与否，
        # 模型原话（含被拒 JSON）如实落史，拒因回喂由 decision_error 承担。
        history = _history_with(
            state,
            dict(context.messages[-1]),
            _assistant_turn(content),
        )
        rnd = state.rounds + 1
        seq = _next_seq(state)
        parsed = parse_decision(
            content, max_discovers=max_discovers, max_executes=max_executes
        )
        if isinstance(parsed, str):
            # 拒因回喂（无 repair）：轮照耗；轮数闸在下一入口收敛兜底。
            record = _step_record(
                seq, STEP_DECISION, f"决策 r{rnd} 被拒：{parsed}", context.manifest,
                payload={"phase": "decision", "rejection": parsed},
            )
            deps.bus.emit(
                "step", {"step": STEP_DECISION, "seq": seq, "title": record["title"]}
            )
            return {
                "rounds": rnd,
                "decision_error": parsed,
                "history": history,
                "manifests": [*state.manifests, context.manifest.as_dict()],
                "steps": [*state.steps, record],
                "next_intent": INTENT_DECISION,
            }
        emission = parsed
        if emission.action == ACTION_EXECUTE and _is_same_param_replay(
            emission, state.executed_payloads
        ):
            # 同参重投机器闸（V2-37）：同参二次发射确定性拦截——不再触工具，
            # 拒因回喂 LLM 由它重决策（带结果直答或改参）。轮照耗（LLM 决策
            # 周期已真实消耗——轮数闸在后续入口收敛兜底，顽投不环）。
            reason = SAME_PARAM_REPLAY_REASON
            record = _step_record(
                seq, STEP_DECISION, f"决策 r{rnd} 同参重投被拦：{reason}",
                context.manifest,
                payload={
                    "phase": "decision",
                    "rejection": reason,
                    "gate": GATE_SAME_PARAM_REPLAY,
                },
            )
            deps.bus.emit(
                "step", {"step": STEP_DECISION, "seq": seq, "title": record["title"]}
            )
            notice = {
                "type": GATE_SAME_PARAM_REPLAY,
                "gates": [],
                "content": f"同参重投机器闸：{reason}",
            }
            deps.bus.emit("notice", dict(notice))
            return {
                "rounds": rnd,
                "decision_error": reason,
                "history": history,
                "notices": [*state.notices, notice],
                "manifests": [*state.manifests, context.manifest.as_dict()],
                "steps": [*state.steps, record],
                "next_intent": INTENT_DECISION,
            }
        record = _step_record(
            seq, STEP_DECISION, _decision_title(emission, rnd), context.manifest,
            payload={"phase": "decision", "emission": emission.as_payload()},
        )
        deps.bus.emit(
            "step", {"step": STEP_DECISION, "seq": seq, "title": record["title"]}
        )
        updates: dict[str, Any] = {
            "rounds": rnd,
            "decision_error": "",
            "user_hint": "",
            "history": history,
            "manifests": [*state.manifests, context.manifest.as_dict()],
            "steps": [*state.steps, record],
            "task_type": emission.task_type,
        }
        if emission.note:
            notice = {
                "type": "decision_note",
                "gates": [],
                "content": emission.note,
            }
            deps.bus.emit("notice", dict(notice))
            updates["notices"] = [*state.notices, notice]
        if emission.action == ACTION_DISCOVER:
            updates["pending_discovers"] = [dict(item) for item in emission.discovers]
            updates["next_intent"] = INTENT_DISCOVER
        elif emission.action == ACTION_EXECUTE:
            updates["pending_plan"] = (
                dict(emission.plan) if emission.plan is not None else None
            )
            updates["pending_retrieval"] = (
                dict(emission.retrieval_need)
                if emission.retrieval_need is not None
                else None
            )
            updates["next_intent"] = INTENT_EXECUTE
        elif emission.action == ACTION_ASK:
            # 连续澄清计数（P-024b 疑点2）＝run 生命期内 ask 发射次数：任何路径
            # 不清零（澄清回收不重置、执行轮不清零——run-69517e02 实测「恢复→
            # 执行→再澄清」若执行清零则环永不封口，挂起等人工不计轮预算）。
            # 第 2 次 ask 即截断：不再挂起，带已取得材料如实直答。
            consecutive = state.consecutive_asks + 1
            if consecutive >= 2:
                notice = {
                    "type": "clarify_capped",
                    "gates": [],
                    "content": (
                        "连续澄清已达上限（连续 ask ≥2）——不再挂起，"
                        "带已取得材料如实直答。"
                    ),
                }
                deps.bus.emit("notice", dict(notice))
                updates["notices"] = [*state.notices, notice]
                _direct_answer(updates, _clarify_capped_answer(state))
            else:
                updates["consecutive_asks"] = consecutive
                frame = {
                    "kind": ASK_CLARIFY,
                    "prompt": emission.ask_prompt,
                    "options": list(emission.ask_options),
                    "detail": None,
                }
                updates["pending_ask"] = frame
                updates["next_intent"] = INTENT_DECISION  # 自环进 interrupt（挂起）
                deps.bus.emit("ask", {"frame": frame, "run_id": state.run_id})
        else:  # finalize
            updates["next_intent"] = INTENT_ANSWER
        return updates

    return decision_node


# ---------- 挂起恢复（clarify 回喂 / 外表审批——接线①③） ----------


async def _handle_choice(state: RunState, deps: LoopDeps) -> dict[str, Any]:
    frame = dict(state.pending_ask or {})
    payload = interrupt(
        {"kind": frame.get("kind"), "frame": frame, "run_id": state.run_id}
    )
    choice = payload if isinstance(payload, dict) else {"value": str(payload)}
    value = str(choice.get("value", ""))
    approval_id = choice.get("approval_id")
    resume_record = {
        "kind": frame.get("kind"),
        "value": value,
        "approval_id": approval_id,
    }
    updates: dict[str, Any] = {
        "pending_ask": None,
        "resume_choices": [*state.resume_choices, resume_record],
        "next_intent": INTENT_DECISION,
    }
    if frame.get("kind") == ASK_CLARIFY:
        # 澄清回收：用户选择回喂决策（user_hint——决策下轮消费后清空）；
        # 用户输入重置轮预算（新信息＝新周期——旧 repairs_since_input 重置同义）。
        updates["user_hint"] = value
        updates["rounds"] = 0
        # 消息历史簿记（ADR-0006）：用户选择作为对话轮次落史（user 侧真轮——
        # 非只进 instruction 附注），后续决策在完整对话上续写。
        updates["history"] = _history_with(state, _user_turn(f"用户补充：{value}"))
        deps.bus.emit(
            "step",
            {"step": STEP_DECISION, "seq": _next_seq(state),
             "title": f"澄清回收：{value}"},
        )
        updates["steps"] = [
            *state.steps,
            _step_record(_next_seq(state), STEP_DECISION, f"澄清回收：{value}",
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
            _direct_answer(
                updates,
                f"外表引用审批已通过（单号 {approval_id}）；权威引擎侧闸未放行续跑，"
                "如实收口不冒充。",
            )
        else:
            updates["approved_ids"] = [*state.approved_ids, str(approval_id or "")]
            updates["extable_rounds"] = state.extable_rounds + 1
            # 末次主执行载荷原样重投（ask 帧侧未执行工具——批准后才真正调用）。
            last = dict(state.last_execute or {})
            updates["pending_plan"] = last.get("plan")
            updates["pending_retrieval"] = last.get("retrieval_need")
            if updates["pending_plan"] is None and updates["pending_retrieval"] is None:
                updates["next_intent"] = INTENT_DECISION  # 无载荷可重投＝回决策
            else:
                updates["next_intent"] = INTENT_EXECUTE
    else:
        impact = str((frame.get("detail") or {}).get(_EXTABLE_REJECT_BASIS_KEY, ""))
        _direct_answer(updates, f"外表引用审批驳回：{impact}")
    # 消息历史簿记（ADR-0006）：审批决定作为对话轮次落史（批准/驳回都留痕——
    # clarify 分支已在上方提前 return，此处只达审批路径）。
    approval_note = (
        f"外表引用审批决定：{value}"
        + (f"（审批单号 {approval_id}）" if approval_id else "")
    )
    updates["history"] = _history_with(state, _user_turn(approval_note))
    deps.bus.emit(
        "step",
        {"step": STEP_DECISION, "seq": _next_seq(state), "title": f"审批回收：{value}"},
    )
    updates["steps"] = [
        *state.steps,
        _step_record(_next_seq(state), STEP_DECISION, f"审批回收：{value}",
                     None, payload={"resume": resume_record}),
    ]
    return updates


# ---------- 节点三/四：discover／execute（固定代码执行——工具只经 registry.call） ----------


def _apply_result(
    state: RunState,
    deps: LoopDeps,
    result: dict[str, Any],
    seq: int,
    *,
    kind: str,
    tool_name: str,
    args: dict[str, Any],
    record_payload: dict[str, Any],
    retry_state: dict[str, Any],
) -> dict[str, Any]:
    """工具结果→状态更新与路由（ReAct 语义：bad_args 拒因回喂重决策、无 repair）。

    - ok → observe（观察回流）；ask → 挂起（自环进 decision 入口 interrupt）；
    - bad_args → 拒因写 decision_error 回喂 LLM 重决策（拍板②——取消自动 repair）；
    - retryable → 同参重试一次（retry_state＝重投载荷更新＋自环意图由节点补）；
      耗尽→如实收敛；
    - refused（闸拒）→ 拒因原样如实转答，不重试不改写。

    每次执行（含被拒）都留执行台账轮进消息历史（V2-38——「参数 → 结果：N 行／
    闸拒（拒因）」，负信息如实落，模型面可见）。
    """
    status = result["status"]
    title = f"{tool_name}：{status}"
    error_message = (
        (result.get("error") or {}).get("message") if status == STATUS_FAILED else None
    )
    deps.bus.emit(
        "tool",
        {"tool": tool_name, "status": status, "seq": seq, "message": error_message},
    )
    deps.bus.emit("step", {"step": kind, "seq": seq, "title": title})
    updates: dict[str, Any] = {
        "steps": [
            *state.steps,
            _step_record(seq, kind, title, None, payload=dict(record_payload)),
        ],
        # 执行台账段落史（ok/拒/挂起全形态——被拒执行不再从模型面消失）。
        "history": _history_with(state, _ledger_turn(tool_name, args, result)),
    }
    if status == STATUS_OK:
        updates["last_result"] = result
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
        updates["next_intent"] = INTENT_DECISION  # 挂起：interrupt 在 decision 入口
        # ask 帧＝挂起信号（行为约定 4：事件流发 ask 帧后正常收束——V2-07 SSE 出口）。
        deps.bus.emit("ask", {"frame": frame, "run_id": state.run_id})
    elif (result.get("error") or {}).get("category") == CATEGORY_BAD_ARGS:
        # 拍板②：取消自动 repair——拒因回喂 LLM 由它重决策（轮预算照耗）。
        reason = str((result.get("error") or {}).get("message", "校验未过"))
        notice = {
            "type": "decision_rejected",
            "gates": [],
            "content": f"工具校验拒因回喂重决策：{reason}",
        }
        deps.bus.emit("notice", dict(notice))
        updates["decision_error"] = reason
        updates["notices"] = [*state.notices, notice]
        updates["pending_plan"] = None
        updates["pending_retrieval"] = None
        updates["pending_discovers"] = []
        updates["next_intent"] = INTENT_DECISION
    elif (result.get("error") or {}).get("category") == CATEGORY_RETRYABLE:
        # 同参重试一次按工具名计数（P-024b C2——discover 链上的重试不挤占 execute
        # 的重试份额；每工具名各得一次）。
        retried = state.tool_retries.get(tool_name, 0)
        if retried < 1:
            updates.update(retry_state)
            updates["tool_retries"] = {**state.tool_retries, tool_name: retried + 1}
            updates["next_intent"] = (
                INTENT_DISCOVER if kind == STEP_DISCOVER else INTENT_EXECUTE
            )
        else:
            notice = {
                "type": "tool_unavailable",
                "gates": [],
                "content": f"工具 {tool_name} 重试后仍不可用——如实收敛。"
                           f"（{(result.get('error') or {}).get('message', '')}）",
            }
            deps.bus.emit("notice", dict(notice))
            updates["notices"] = [*state.notices, notice]
            updates["pending_plan"] = None
            updates["pending_retrieval"] = None
            updates["pending_discovers"] = []
            _direct_answer(updates, "（工具重试后仍不可用——如实收敛，不编造。）")
    else:  # refused（闸拒）——拒因原样如实转答，不重试不改写
        reason = str((result.get("error") or {}).get("message", "口径/数据闸拒"))
        # 机读 notice（P-006b·R3）——与 bad_args 回喂/tool_unavailable 通道同形，
        # V2-05 闸态机读分型在 runtime 侧对齐（按 notice 类型消费的面不漏直接闸拒）。
        notice = {
            "type": "refused",
            "gates": [],
            "content": f"口径/数据闸拒——拒因如实转答：{reason}",
        }
        deps.bus.emit("notice", dict(notice))
        updates["notices"] = [*state.notices, notice]
        updates["pending_plan"] = None
        updates["pending_retrieval"] = None
        updates["pending_discovers"] = []
        _direct_answer(updates, reason)
    return updates


async def _invoke_tool(
    deps: LoopDeps, state: RunState, tool_name: str, args: dict[str, Any]
) -> Any:
    """统一调出口＋单工具超时闸（wait_for——超时转 retryable 通道）。"""
    timeout = float(state.budget.get("tool_timeout_seconds", 30.0))
    try:
        return await asyncio.wait_for(
            deps.registry.call(tool_name, args, _ctx_of(state)), timeout=timeout
        )
    except TimeoutError:
        return None


def _make_discover(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    async def discover_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            return converged
        queue = list(state.pending_discovers)
        if not queue:  # 恢复段边界兜底（队列空＝回决策）
            return {"next_intent": INTENT_DECISION}
        call = dict(queue[0])
        tool_name = str(call.get("tool", ""))
        args = dict(call.get("args") or {})
        raw = await _invoke_tool(deps, state, tool_name, args)
        timeout = float(state.budget.get("tool_timeout_seconds", 30.0))
        result = (
            _timeout_result(tool_name, timeout) if raw is None else _result_dict(raw)
        )
        seq = _next_seq(state)
        updates = _apply_result(
            state,
            deps,
            result,
            seq,
            kind=STEP_DISCOVER,
            tool_name=tool_name,
            args=args,
            record_payload={"tool": tool_name, "status": result["status"]},
            retry_state={"pending_discovers": [call, *queue[1:]]},
        )
        if result["status"] == STATUS_OK:
            updates["pending_discovers"] = queue[1:]  # 本支已消费（观察回流后续投）
        return updates

    return discover_node


def _make_execute(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    async def execute_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            return converged
        if state.pending_plan is not None:
            tool_name = DATA_QUERY
            args: dict[str, Any] = {"plan_draft": dict(state.pending_plan)}
            executed: dict[str, Any] = {"plan": dict(state.pending_plan)}
            consume: dict[str, Any] = {"pending_plan": None}
        elif state.pending_retrieval is not None:
            tool_name = DOC_RETRIEVE
            args = dict(state.pending_retrieval)
            executed = {"retrieval_need": dict(state.pending_retrieval)}
            consume = {"pending_retrieval": None}
        else:  # 恢复段边界兜底（无待执行载荷＝回决策）
            return {"next_intent": INTENT_DECISION}
        raw = await _invoke_tool(deps, state, tool_name, args)
        timeout = float(state.budget.get("tool_timeout_seconds", 30.0))
        result = (
            _timeout_result(tool_name, timeout) if raw is None else _result_dict(raw)
        )
        seq = _next_seq(state)
        updates = _apply_result(
            state,
            deps,
            result,
            seq,
            kind=STEP_EXECUTE,
            tool_name=tool_name,
            args=args,
            record_payload={"tool": tool_name, "status": result["status"], **executed},
            retry_state={},  # 载荷仍在位（pending_plan/retrieval 未清）——自环重投
        )
        if result["status"] in (STATUS_OK, STATUS_ASK):
            # ok＝本支已消费（观察回流后续投）；ask＝载荷留 last_execute 供审批重投。
            updates.update(consume)
            updates["last_execute"] = executed
            # 主执行实录（V2-37 同参重投机器闸的簿记面）：ok/ask 才算已执行
            # （bad_args 拒＝引擎未执行，不记——修正后重发不被误拦）。
            updates["executed_payloads"] = [
                *state.executed_payloads,
                *_emission_fingerprints(
                    executed.get("plan"), executed.get("retrieval_need")
                ),
            ]
        return updates

    return execute_node


# ---------- 节点五：observe（观察回流——回喂决策） ----------


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
        title = f"观察回流 {len(indexed)} 支"
        deps.bus.emit("step", {"step": STEP_OBSERVE, "seq": seq, "title": title})
        for obs in indexed:
            if (obs.get("locator") or {}).get("kind") == "notice":
                # 闸依据/截断声明＝notice 信号（机读分型——拦停非数据）。
                deps.bus.emit(
                    "notice",
                    {
                        "type": str(
                            (obs.get("locator") or {}).get("notice_type", "notice")
                        ),
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
        # 回流路由：待投载荷在位→继续执行；否则回决策（模型自主再轮或定稿）。
        if state.pending_discovers:
            intent = INTENT_DISCOVER
        elif state.pending_plan is not None or state.pending_retrieval is not None:
            intent = INTENT_EXECUTE
        else:
            intent = INTENT_DECISION
        return {
            "observations": [*state.observations, *indexed],
            "steps": [*state.steps, record],
            "next_intent": intent,
        }

    return observe_node


# ---------- 节点六：verify（零 LLM——INV-1/4 机器底线；拍板③保留件） ----------


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
        else:
            text, rewritten, cited, split = verify_draft(
                state.draft, state.observations
            )
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
                 "content": f"核验步改写无据断言 {rewritten} 行"
                            "（INV-1——禁止无据断言进答案）"},
            )
        if split:
            deps.bus.emit(
                "notice",
                {"type": "contradiction_split", "gates": [],
                 "content": "多来源不一致——答案分源列明（INV-4——禁止无出处调和）"},
            )
        return {
            "draft": text,
            "verdict": verdict,
            "steps": [*state.steps, _step_record(seq, STEP_VERIFY, title, None,
                                                       payload={"zero_llm": True})],
            "next_intent": INTENT_ANSWER,
        }

    return verify_node


# ---------- 节点七：answer（起草[caller answer]→verify→收口——两段一节点） ----------


def _finalize(state: RunState, deps: LoopDeps) -> dict[str, Any]:
    """答案收口（引用块＋血缘⑤注记＋摘要——确定性装配，零二次创作）。"""
    verdict = state.verdict or {}
    cited: list[int] = list(verdict.get("cited") or [])
    by_index = {int(obs["index"]): obs for obs in state.observations}
    answer = state.draft or state.answer or "（未取得可交付答案——如实回报，不编造。）"
    # 收口注记确定性随行（V2-23——LIMIT 截断披露不靠模型自觉；草稿已自带则不重复）。
    closing = _lineage_closing_note(state.observations)
    if closing and "收口注记" not in answer:
        answer += "\n\n" + closing
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
        "steps": [*state.steps, _step_record(seq, STEP_ANSWER, title, None,
                                                   payload={"phase": "finalize"})],
        "next_intent": INTENT_END,
    }


def _make_answer(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    async def answer_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            converged["next_intent"] = INTENT_END  # 收敛路由终点（防 answer→answer 环）
            return converged
        if (
            not state.answer
            and state.verdict is None
            and state.draft_kind != "direct"
            and not state.draft
            and any(  # 有实质材料才起草（零材料——闸依据/拒答如实转答，不烧模型）
                (obs.get("locator") or {}).get("kind") != "notice"
                for obs in state.observations
            )
        ):
            # ——起草段（caller answer——引标断言合同；核验素材面）——
            context = deps.builder.compile(
                state, step="answer", instruction=_ANSWER_INSTRUCTION
            )
            content = await _complete(deps.model(MODEL_ANSWER), context)
            draft = content.strip() or "（模型未产出草稿——如实收口。）"
            seq = _next_seq(state)
            title = "起草答案"
            deps.bus.emit("step", {"step": STEP_ANSWER, "seq": seq, "title": title})
            return {
                # 消息历史簿记（ADR-0006）：起草调用与草稿输出入簿。
                "history": _history_with(
                    state,
                    dict(context.messages[-1]),
                    _assistant_turn(content),
                ),
                "draft": draft,
                "manifests": [*state.manifests, context.manifest.as_dict()],
                "steps": [
                    *state.steps,
                    _step_record(seq, STEP_ANSWER, title, context.manifest,
                                 payload={"phase": "draft"}),
                ],
                "next_intent": INTENT_VERIFY,
            }
        if state.verdict is None and state.draft_kind != "direct" and not state.answer:
            # 零材料且未核验——先过 verify（闸依据如实转答由 verify 确定性装配）。
            return {"next_intent": INTENT_VERIFY}
        # ——收口段（verdict 在场／确定性直答／收敛答案——引用块＋注记＋摘要出流）——
        return _finalize(state, deps)

    return answer_node


# ---------- 图装配（七节点＋条件边——StateGraph 真承载 loop） ----------

_ROUTES: dict[str, dict[Hashable, str]] = {
    NODE_UNDERSTAND: {
        INTENT_DECISION: NODE_DECISION,
        INTENT_ANSWER: NODE_ANSWER,
        INTENT_END: END,
    },
    NODE_DECISION: {
        INTENT_DECISION: NODE_DECISION,
        INTENT_DISCOVER: NODE_DISCOVER,
        INTENT_EXECUTE: NODE_EXECUTE,
        INTENT_ANSWER: NODE_ANSWER,
        INTENT_END: END,
    },
    NODE_DISCOVER: {
        INTENT_OBSERVE: NODE_OBSERVE,
        INTENT_DISCOVER: NODE_DISCOVER,
        INTENT_DECISION: NODE_DECISION,
        INTENT_ANSWER: NODE_ANSWER,
        INTENT_END: END,
    },
    NODE_EXECUTE: {
        INTENT_OBSERVE: NODE_OBSERVE,
        INTENT_EXECUTE: NODE_EXECUTE,  # retryable 同参重试自环（P-024b C2 修补——骨架缺此路）
        INTENT_DECISION: NODE_DECISION,
        INTENT_ANSWER: NODE_ANSWER,
        INTENT_END: END,
    },
    NODE_OBSERVE: {
        INTENT_DISCOVER: NODE_DISCOVER,
        INTENT_EXECUTE: NODE_EXECUTE,
        INTENT_DECISION: NODE_DECISION,
        INTENT_ANSWER: NODE_ANSWER,
        INTENT_END: END,
    },
    NODE_VERIFY: {INTENT_ANSWER: NODE_ANSWER, INTENT_END: END},
    NODE_ANSWER: {
        INTENT_VERIFY: NODE_VERIFY,
        INTENT_ANSWER: NODE_ANSWER,
        INTENT_END: END,
    },
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
    运行时零行为差；节点签名仍受本模块 Callable 注记约束。
    """
    return fn


def build_graph(deps: LoopDeps, *, checkpointer: Any = None) -> Any:
    """编译 ReAct 图（checkpointer 由 executor 注入——挂起/恢复的存储机制）。"""
    builder = StateGraph(RunState)
    builder.add_node(NODE_UNDERSTAND, _node_of(_make_understand(deps)))
    builder.add_node(NODE_DECISION, _node_of(_make_decision(deps)))
    builder.add_node(NODE_DISCOVER, _node_of(_make_discover(deps)))
    builder.add_node(NODE_EXECUTE, _node_of(_make_execute(deps)))
    builder.add_node(NODE_OBSERVE, _node_of(_make_observe(deps)))
    builder.add_node(NODE_VERIFY, _node_of(_make_verify(deps)))
    builder.add_node(NODE_ANSWER, _node_of(_make_answer(deps)))
    builder.add_edge(START, NODE_UNDERSTAND)
    for name, mapping in _ROUTES.items():
        builder.add_conditional_edges(name, _route, mapping)
    return builder.compile(checkpointer=checkpointer)
