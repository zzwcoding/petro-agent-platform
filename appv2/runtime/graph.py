"""runtime.graph —— LangGraph StateGraph ReAct 自主循环（V2-31 拍板七条＝设计合同）。

节点按 ReAct 周期（每步落 step 记录——过程态簿记留痕；INV-5 审计责任账经
security.audit 唯一写口落，见 runtime/audit.py）：

    understand → decision ⇄（discover／execute → observe）→ answer → verify → answer收口

V2-34 四相位叠加（ADR-0005，build_graph(four_phase=True)——一轮＝四相位）：

    understand → clarify ⇄ discover（钻取，全 run ≤10＋计数埋点）
               → toolmatch（工具匹配，schema 收口）
               → precondition（前置条件机——纯固定代码零 LLM，判四态）
               → batch（批量执行＋观察汇聚）→ answer（LLM 汇总）→ verify → 收口

- 轮＝LLM 决策周期（≤3 轮）：clarify 发射 discover 钻取不占轮（受全 run ≤10
  发现预算闸）；decompose 占轮；轮 2/3 只带失败子问题＋拒因回炉①（成功子问题
  结果保留不重跑——subtask_results 簿记）。ASK 挂起不占轮。
- 前置条件机（precondition 节点）＝纯固定代码：逐子问题判四态
  pass｜blocked_ask→ASK 挂起帧｜blocked_refuse→如实拒答｜note 注记随行；
  LLM 无权判定（tools.precondition——AST/import 零 LLM 双证有钉）。
- 词典层第 1 轮全量注入（拍板 a）：clarify/toolmatch 上下文经 extra_sources
  常驻注入台账全量＋别名＋结构卡（Manifest 记 ledger_dump 族来源行；常驻块
  不重复入史——token 防放大）。
- 铁律：LLM 出语义（澄清/分解/提议），代码出判定（前置条件机零 LLM——V1
  十七站瀑布教训的落点）。

V2-31 原语义（保留件——legacy 路径＝默认装配，四相位经 four_phase=True 装配）：

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
- 处理指南经 GuideProvider 缝消费（拍板⑦——ontology 资产件注入；V2-34 起
  占位 DefaultGuideProvider 退役，生产唯一指南源＝OntologyGuideProvider）。

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
from collections.abc import Callable, Coroutine, Hashable, Sequence
from dataclasses import dataclass, replace
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from appv2.infra import clock
from appv2.runtime.budget import (
    MAX_DISCOVERS_PER_ROUND_CONTRACT,
    MAX_DISCOVERS_PER_RUN_CONTRACT,
    MAX_EXECUTES_PER_ROUND_CONTRACT,
    MAX_ROUNDS_CONTRACT,
    budget_gate_hit,
    material_rows,
    unfinished_notice,
)
from appv2.runtime.context import CompiledContext, ContextBuilder, trust_of
from appv2.runtime.events import EventBus
from appv2.runtime.guide import (
    CLARIFY_CONTRACT,
    SUMMARY_CONTRACT,
    TOOLMATCH_CONTRACT,
    GuideProvider,
)
from appv2.runtime.llm import CALLER_PREFIX, GatewayChatModel
from appv2.runtime.state import (
    INTENT_ANSWER,
    INTENT_BATCH,
    INTENT_DECISION,
    INTENT_DISCOVER,
    INTENT_END,
    INTENT_EXECUTE,
    INTENT_OBSERVE,
    INTENT_PRECONDITION,
    INTENT_TOOLMATCH,
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
from appv2.runtime.subtask import (
    BUDGET_REJECT_MARK,
    CLARIFY_DECOMPOSE,
    CLARIFY_DISCOVER,
    CLARIFY_FINALIZE,
    MAX_SUBTASKS_CONTRACT,
    QuestionGroup,
    Subtask,
    extract_plan_json,
    parse_question_group,
    parse_tool_match,
)
from appv2.tools import (
    ASK_CLARIFY,
    ASK_EXTERNAL_TABLE_APPROVAL,
    CATEGORY_BAD_ARGS,
    CATEGORY_REFUSED,
    CATEGORY_RETRYABLE,
    CHAIN_SWITCH_HINT,
    CHAIN_SWITCH_KIND_DOMAIN,
    CHAIN_SWITCH_KIND_UNBOUND,
    DATA_QUERY,
    DOC_RETRIEVE,
    FAQ_LOOKUP,
    RESIDENT_BLOCK_BEGIN,
    RESIDENT_BLOCK_END,
    SCHEMA_PROBE,
    SEMANTIC_QUERY,
    STATE_BLOCKED_ASK,
    STATE_BLOCKED_REFUSE,
    STATE_NOTE,
    STATE_PASS,
    STATUS_ASK,
    STATUS_FAILED,
    STATUS_OK,
    SubtaskInput,
    ToolContext,
    ToolRegistry,
    ban_exempt_notice_text,
    entity_anchor_tokens,
    inject_retrieval_anchors,
    is_ban_exempt,
    judge,
    ledger_facts,
    normalize_anchor_text,
    recall_relevant,
    render_aliases,
    render_cards,
    render_ledger_rows,
    resolve_send_budget,
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
# V2-52 辅助模式：faq_lookup 进闭世界（附 B 消费规则——辅助材料 discover 面）。
DISCOVER_TOOLS: frozenset[str] = frozenset(
    {SEMANTIC_QUERY, SCHEMA_PROBE, FAQ_LOOKUP}
)

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
# 答案起草合同（引标断言——verify 确定性核验的素材面）。V2-48 追加 JSON 通道
# 隔离句（finalize/ask 发射 JSON 不进答案面——确定性剥离是 enforcement，此句
# 只降首发泄漏率省重试）。V2-51 追加台账卡非数据源句（C-正4 台账词面拼凑形：
# 台账定义卡只作口径注记，不得拼装成点名对象的数据答案）。
_ANSWER_INSTRUCTION = (
    "起草答案：逐条事实断言必须带 [n] 引标（n＝观察材料序号）；材料未覆盖的部分"
    "不得断言；多来源不一致时逐源列明。答案只出交付正文——finalize/ask 等发射"
    " JSON（含围栏形）不得出现在答案中。台账卡（指标/术语定义面）只承载口径与"
    "定义，不是井/对象的取数面——点名具体井、报告或对象的数据题，结论必须取自"
    "该对象自己的观察材料本体，不得以台账定义卡拼装该对象的数据答案；材料未"
    "覆盖该对象时如实说明未覆盖。"
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
# V2-34 四相位节点（four_phase=True 装配时入图——相位③零 LLM、相位④批量执行；
# 汇总相位复用 answer 节点（SUMMARY_CONTRACT 指令）＋verify 收口不变）。
NODE_CLARIFY = "clarify"
NODE_TOOLMATCH = "toolmatch"
NODE_PRECONDITION = "precondition"
NODE_BATCH = "batch"


class LoopDeps:
    """ReAct 节点共享依赖（registry/models/builder/store/bus/guide——per-run bus 注入）。

    guide 必填（V2-34 任务 10——占位 DefaultGuideProvider 退役，不设双真源：
    生产＝OntologyGuideProvider，测试＝剧本/标记指南）。ledger_dump＝词典层
    全量投影缝（澄清相位第 1 轮注入真源——tools.dump_from_store 装配）；watermark
    ＝水位读缝（前置条件机新鲜度窗照实判定——组合根经 production_waterline 供给）；
    data_wells＝数据链井闭世界读缝（V2-51 软失败域闸——组合根经
    production_data_wells 供给 agg.dim_well 井号集；缺省 None＝域闸静默零漂移）。
    """

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        models: dict[str, GatewayChatModel],
        builder: ContextBuilder,
        store: RunStore,
        bus: EventBus,
        guide: GuideProvider,
        ledger_dump: Callable[[], dict[str, Any]] | None = None,
        watermark: Callable[[], Any] | None = None,
        data_wells: Callable[[], Any] | None = None,
        today: Any = None,
    ) -> None:
        self.registry = registry
        self.models = models
        self.builder = builder
        self.store = store
        self.bus = bus
        # 处理指南缝（拍板⑦）：必填——ontology 资产件注入（占位退役）。
        self.guide: GuideProvider = guide
        self.ledger_dump = ledger_dump
        self.watermark = watermark
        self.data_wells = data_wells
        self.today = today if today is not None else clock.now().date()

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


# extract_plan_json 已迁 appv2.runtime.subtask（本模块顶部 import re-export——
# 决策发射/understand 降级形与四相位两道 schema 共用一个平衡块提取单点）。


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


# ---------- 起草面 JSON 通道隔离（V2-48 族 A——发射围栏不进答案面） ----------

# 裸发射 JSON 令牌（单行平面形）：action 值 ∈ ACTION_KINDS 闭世界才判泄漏
# （域外 JSON 零误伤——非发射形围栏/对象原样保留）。
_EMISSION_TOKEN_RE = re.compile(r'\{\s*"action"\s*:\s*"([^"]+)"[^{}]*\}')
# 围栏块（```info\n body```）——body 解析为发射形 JSON 对象才剥。
_FENCE_RE = re.compile(r"```[^\n]*\n?(.*?)```", re.DOTALL)


def _parses_as_json(text: str) -> bool:
    try:
        payload = json.loads(text)
    except ValueError:
        return False
    return isinstance(payload, (dict, list))


def _fence_is_json(body: str) -> bool:
    """围栏体是否 JSON 段（整段可解／前缀噪声形首个 { 到末个 } 可解——P047AD
    NQ-D7 帧形：汇总相位重发 matches JSON 围栏，答案面是散文交付面，围栏 JSON
    段一律属协议残留）。"""
    candidate = body.strip()
    if _parses_as_json(candidate):
        return True
    start = candidate.find("{")
    end = candidate.rfind("}")
    return start != -1 and end > start and _parses_as_json(candidate[start : end + 1])


def strip_emission_fences(text: str) -> tuple[str, bool]:
    """JSON 通道确定性剥离（V2-48 族 A——发射围栏/裸 JSON 段不进答案面）。

    finalize/ask 发射通道与答案文本通道分离的确定性收口（Q14 族 A 帧形全辖：
    NQ-D10 纯围栏零交付／NQ-D1·D7 围栏裹载荷／数-闸2 相位提示回声行内裸发射
    对象／系统-届满 正文尾挂围栏／P047AD-NQ-D7 汇总相位重发 matches JSON
    围栏——非发射形 JSON 段同属协议残留）：

    - 围栏块：body 为 JSON 段（整段或前缀噪声形可解析为 JSON 对象/数组）→
      整块剥除（发射形与否都剥——答案面零裸 JSON 段）；
    - 裸发射行：行内含裸发射 JSON 令牌（action ∈ ACTION_KINDS）→整行剥除
      （回声行余文＝提示原文，同属泄漏承载——一并离场）；整行就是一个可解析
      JSON 对象/数组的行→剥除（无围栏裸 JSON 行）；
    - 纯散文围栏（无 JSON 段）与散文行内非发射花括号片段零误伤原样保留。

    返回（剥离后文本, 是否检出 JSON 通道残留）。纯格式隔离零语义判定——剥离
    不计数进 INV-1 改写（协议残片非断言）。
    """
    leaked = False

    def _drop(m: re.Match[str]) -> str:
        nonlocal leaked
        if _fence_is_json(m.group(1)):
            leaked = True
            return ""
        return m.group(0)

    text = _FENCE_RE.sub(_drop, text)
    kept: list[str] = []
    for line in text.splitlines():
        token = _EMISSION_TOKEN_RE.search(line)
        if token is not None and token.group(1) in ACTION_KINDS:
            leaked = True
            continue
        stripped = line.strip()
        if stripped.startswith(("{", "[")) and _parses_as_json(stripped):
            leaked = True
            continue
        kept.append(line)
    return "\n".join(kept), leaked


# ---------- 核验步确定性规则（INV-1/INV-4 骨架版——保留件；V2-48 入口增发射
# 剥除一道（strip_emission_fences——改写面无裸 JSON 段），其余零改动） ----------


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
    draft: str,
    observations: list[dict[str, Any]],
    *,
    anchors: Sequence[str] = (),
) -> tuple[str, int, list[int], bool]:
    """草稿逐行断言级核验：返回（核验后文本, 改写数, 被引序号列, 是否分源）。

    - 逐引标抽取其辖断言文本做支撑判定：全部断言有据＝行保留（引标收进引用集）；
      无引标数字行/越界引标/断言与被引观察无关（材料数值未被复述）＝无据断言，
      整行改写「未找到（材料未披露）」（INV-1——禁止无据断言进答案）。改写只管
      自由文本断言行：无引标且无数字的行（标题/表格头/分隔线等结构承载）不属
      断言，原样保留（V2-23）；表格行/血缘卡/kb 片段引挂豁免「全数值复述」（见
      _supported——零重叠仍改写，R9 反例不回退）；
    - 被引观察中同一 subject（台账卡内容首段名称）≥2 支且值不同→追加分源列明块
      （INV-4——禁止无出处调和；agg_row 行级事实按 井@日 独立键，不入矛盾池）；
    - V2-48 入口发射剥除：draft 先过 strip_emission_fences（核验步改写面无裸
      JSON 段——NQ-D10 形围栏不进答案面；剥除不计改写数——发射残片非断言）；
    - V2-50 归属审（②）：anchors 非空时对被引**检索片段**（locator.kind ∈
      fragment/graph）做引标源↔题眼一致性审——出处名（source/locator.report）
      与内容均不含任一题眼锚＝跨源引用，追加「跨源归属审——分源列明」块（对齐
      源/跨源逐支带出处列出；对齐材料在窗未引或窗内无对齐材料如实注记）。无锚
      （无实体题）＝零追加（不误伤钉）；数据链行级观察（agg_row/lineage）不入
      辖域；归属审不改写行、不计 INV-1 改写数（数值支撑判定语义不变）。
    """
    by_index = {int(obs["index"]): obs for obs in observations}
    draft = strip_emission_fences(draft)[0]
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
    if anchors:
        block = _attribution_block(anchors, cited, observations)
        if block:
            text += "\n\n" + block
    return text, rewritten, sorted(cited), split


# ---------- 归属审（V2-50 族 C ②——引标源↔题眼一致性审） ----------

# 归属审辖域（检索家族观察承载——fragment/graph；数据链行级 agg_row/lineage 与
# 元信息 notice/window_miss 不入辖域：行级事实按 井@日 独立键、元信息无出处面）。
_ATTRIBUTION_CARRIER_KINDS = frozenset({"fragment", "graph"})
# 在窗未引对齐支的列名上限（分源列明 bounded——超出计数注记，不无限拉长答案）。
_ATTRIBUTION_LIST_CAP = 4


def _observation_aligns(obs: dict[str, Any], needles: tuple[str, ...]) -> bool:
    """观察与题眼锚对齐判定：任一锚规范形出现在（出处名＋内容）规范形中。

    出处名＝source＋locator.report（报告名/油田/井号承载）；内容对齐保住
    「出处名不含锚但行文点名题眼实体」的正当引用（B-正3 形月报行文——零误伤）。
    """
    haystack = normalize_anchor_text(
        str(obs.get("source", ""))
        + " "
        + str((obs.get("locator") or {}).get("report", ""))
        + " "
        + str(obs.get("content", ""))
    )
    return any(needle in haystack for needle in needles)


def _attribution_conflicts(
    anchors: Sequence[str], cited: set[int], observations: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """归属审二分（被引检索片段——对齐列，跨源列；序＝观察序确定性）。

    返回（对齐支, 跨源支）。cited 之外零消费；无锚＝空空（审静默）。
    """
    needles = tuple(
        normalized
        for normalized in (normalize_anchor_text(a) for a in anchors)
        if normalized
    )
    if not needles:
        return [], []
    aligned: list[dict[str, Any]] = []
    crossed: list[dict[str, Any]] = []
    for obs in observations:
        index = int(obs["index"])
        if index not in cited:
            continue
        if str((obs.get("locator") or {}).get("kind", "")) not in _ATTRIBUTION_CARRIER_KINDS:
            continue
        (aligned if _observation_aligns(obs, needles) else crossed).append(obs)
    return aligned, crossed


def _attribution_block(
    anchors: Sequence[str], cited: set[int], observations: list[dict[str, Any]]
) -> str:
    """跨源归属审块（分源列明或如实说无——票面钉的两支出场形）。

    - 跨源支在场才出块（全对齐＝零追加——不误伤钉）；逐支带 [n] 出处列出；
    - 对齐面三分：被引对齐支全列；在窗未引对齐支列前 4 支＋余量计数（A-正1 形
      的「对齐材料在场而消费错源」——对齐源与跨源逐支并立才是分源列明的本义）；
      全窗无对齐材料→「如实说无」声明（跨源材料不作题眼归属断言）。
    """
    aligned, crossed = _attribution_conflicts(anchors, cited, observations)
    if not crossed:
        return ""
    needles = tuple(
        normalized
        for normalized in (normalize_anchor_text(a) for a in anchors)
        if normalized
    )
    cited_ids = set(cited)
    uncited_aligned = [
        obs
        for obs in observations
        if int(obs["index"]) not in cited_ids
        and str((obs.get("locator") or {}).get("kind", ""))
        in _ATTRIBUTION_CARRIER_KINDS
        and _observation_aligns(obs, needles)
    ]
    needles_text = "、".join(str(a) for a in anchors)
    lines = [f"跨源归属审——分源列明（题眼锚：{needles_text}；禁止无出处调和）："]
    if aligned or uncited_aligned:
        if aligned:
            lines.append("对齐题眼锚：")
            lines.extend(
                f"[{obs['index']}] {obs.get('source', '')}：{obs.get('content', '')}"
                for obs in aligned
            )
        if uncited_aligned:
            lines.append("对齐题眼锚的材料（在窗未进答案引用——按出处核对）：")
            lines.extend(
                f"[{obs['index']}] {obs.get('source', '')}：{obs.get('content', '')}"
                for obs in uncited_aligned[:_ATTRIBUTION_LIST_CAP]
            )
            if len(uncited_aligned) > _ATTRIBUTION_LIST_CAP:
                lines.append(
                    f"……另 {len(uncited_aligned) - _ATTRIBUTION_LIST_CAP} 支对齐"
                    "材料从略（按出处核对）。"
                )
    else:
        lines.append(
            f"窗内无对齐题眼锚（{needles_text}）的材料——所引均为跨源材料，"
            "如实列明，不作题眼归属断言。"
        )
    lines.append("跨源引用（引标源与题眼锚不一致——按出处如实区分，不得并入题眼断言）：")
    lines.extend(
        f"[{obs['index']}] {obs.get('source', '')}：{obs.get('content', '')}"
        for obs in crossed
    )
    return "\n".join(lines)


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
    # 送窗预算动态化（V2-45 R1a——「装得下」）：缺省 4 → 按调用上下文赋值——
    # 问题组子问题数 ×每子问题基线 6、上限 24（batch 相位逐支执行各自调用，
    # 组尺寸是逐支共享上下文；无组/legacy 单发射按 1 支计＝基线 6，≥ 旧缺省
    # 只扩不缩）。data 链不消费此值零扰；表类整行集与锚保底席位在检索供给层
    # 解锁（题面词面判定——retrieval.domain），不占本数值配额。
    return ToolContext(
        actor=state.actor,
        budget=resolve_send_budget(len(_group_subtasks(state))),
        metric_candidates=tuple(state.metric_candidates) or None,
        # 外表放行态（A2 裁决落点——审批态随上下文走，不进 args、不重排计划）。
        approved_tables=tuple(state.approved_ids),
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
    """执行台账段（V2-38 任务 2——「参数 → 结果：N 行／分型拒因」形落历史）。

    ok＝参数 → 结果：N 行；ask＝参数 → 结果：0 行（挂起：审批）；failed 按
    ToolError 三分类分型措辞（P-032b C2——措辞如实：bad_args＝参数校验未过、
    引擎未执行，非闸拒；闸拒仅指引擎 refused 面）：bad_args→「校验拒（拒因）」
    修参重投／retryable→「暂不可用（拒因）」可恢复（引擎侧同参重试一次）／
    refused→「闸拒（拒因）」不重试不改写。负信息如实落（同参重投由模型读
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
    error = result.get("error") or {}
    reason = str(error.get("message", "校验未过"))
    category = str(error.get("category", ""))
    if category == CATEGORY_BAD_ARGS:
        return _user_turn(f"{tool_name} 参数：{params} → 校验拒（拒因：{reason}）")
    if category == CATEGORY_RETRYABLE:
        return _user_turn(f"{tool_name} 参数：{params} → 暂不可用（拒因：{reason}）")
    return _user_turn(f"{tool_name} 参数：{params} → 闸拒（拒因：{reason}）")


# ---------- 词典层常驻注入（V2-34 拍板 a——第 1 轮全量＋历史收窄） ----------


def _slim_resident(text: str) -> str:
    """常驻注入块历史收窄（D 类挂账方向——常驻材料不重复入史，防 token 放大）。

    入史轮把 〖台账全量·常驻注入…〗…〖/常驻注入〗 整块替换为一句占位注记
    （当前轮每步重新注入，模型面常驻在场；历史只留「曾注入」的痕迹）。
    """
    pattern = re.escape(RESIDENT_BLOCK_BEGIN) + r".*?" + re.escape(RESIDENT_BLOCK_END)
    return re.sub(
        pattern, "（常驻注入块不重复入史——台账全量见当轮注入）", text, flags=re.DOTALL
    )


def _resident_sources(dump: dict[str, Any]) -> list[dict[str, str]]:
    """dump→extra_sources 三块（台账/别名/结构卡——Manifest 各记一行来源）。"""
    return [
        {
            "source_type": "ledger_dump",
            "source_id": "ledger_full_dump",
            "label": "台账全量（指标/术语/对象/关系/族标注）",
            "content": render_ledger_rows(dump),
        },
        {
            "source_type": "alias_dump",
            "source_id": "ledger_aliases",
            "label": "别名表",
            "content": render_aliases(dump),
        },
        {
            "source_type": "schema_card",
            "source_id": "schema_cards",
            "label": "数据资产结构卡",
            "content": render_cards(dump),
        },
    ]


def reseed_approval_id(run_id: str, engine_seed: str) -> str:
    """审批单号 run 前缀重种子（接线③——V2-03 偏差 7：引擎表名种子保留可溯）。"""
    return f"{run_id}#{engine_seed}"


# ---------- N1 禁用词代码前置安全闸（V2-52 附 C——唯一前置例外；P-051b 返工） ----------


def _n1_code_first_gate(
    state: RunState, deps: LoopDeps
) -> tuple[str | None, Any]:
    """understand 入口禁用词闸分类（附 C 语义——词面闭世界零 LLM，先于一切
    解析；V1 W-F19 0 号位语义的 ReAct 形承载）。

    返回（kind, payload）：
    - ("refused", updates)——非豁免命中：硬终止收口 updates（understand 立即
      返回——零执行零模型，notice type="refused"＝审计同源面 agent_v2.refused）；
    - ("exempt", BannedFact)——元问/引用形豁免命中（is_ban_exempt——审查②
      等效补齐）：understand 出豁免 notice/步后照常解析（豁免＝放行非直出，
      executor 据 notice 落 agent_v2.ban_exempt 审计行——豁免必留痕）；
    - (None, None)——闸静默（未命中/词典层缝缺省＝零漂移；快车道词条卡/FAQ
      直出形已随 P-051b 拆除，本闸只辖禁用词）。
    """
    dump = state.ledger_dump
    if dump is None and deps.ledger_dump is not None:
        dump = deps.ledger_dump()
    if dump is None:
        return None, None
    question = state.question
    for item in ledger_facts(dump).banned:
        if not (item.term and item.term in question):
            continue
        if is_ban_exempt(question, item.term):
            return "exempt", item
        # 非豁免＝硬终止（拒因带替代词——零执行不冒充）。
        replacement = f"替代：{item.replacement}" if item.replacement else "见台账"
        reason = (
            f"禁用词「{item.term}」已废弃——如实拒答，不代答废弃口径（{replacement}）"
        )
        notice = {"type": "refused", "gates": [], "content": reason}
        deps.bus.emit("notice", dict(notice))
        seq = _next_seq(state)
        record = _step_record(
            seq, STEP_DECISION, "N1 禁用词硬终止", None,
            payload={"phase": "understand", "n1_gate": "refused", "term": item.term},
        )
        deps.bus.emit("step", {"step": STEP_DECISION, "seq": seq, "title": record["title"]})
        updates: dict[str, Any] = {
            "notices": [*state.notices, notice],
            "steps": [*state.steps, record],
        }
        if state.ledger_dump is None:
            updates["ledger_dump"] = dump
        _direct_answer(updates, reason)
        return "refused", updates
    return None, None


def _ban_exempt_preflight(
    state: RunState, deps: LoopDeps, item: Any
) -> tuple[dict[str, Any], dict[str, Any]]:
    """豁免命中出流（notice＋步记录）——understand 照常解析前的簿记位。

    返回（notice, record）：notice 携 term 机读键（executor 审计逐行消费；
    SSE 出流面只带 type/gates/content 三键——机读分型约定形状不变）。
    """
    notice = {
        "type": "ban_exempt",
        "gates": [],
        "content": ban_exempt_notice_text(item.term, item.replacement),
        "term": item.term,
    }
    deps.bus.emit("notice", {key: notice[key] for key in ("type", "gates", "content")})
    record = _step_record(
        _next_seq(state), STEP_DECISION, "N1 禁用词豁免放行（元问/引用形）", None,
        payload={"phase": "understand", "n1_gate": "ban_exempt", "term": item.term},
    )
    deps.bus.emit(
        "step", {"step": STEP_DECISION, "seq": record["seq"], "title": record["title"]}
    )
    return notice, record


# ---------- 节点一：understand（理解——caller understand；记 decision 类步） ----------


def _make_understand(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    async def understand_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            return converged
        # ——N1 禁用词代码前置安全闸（V2-52 附 C——唯一前置例外，零 LLM）：
        # 词面闭世界命中→豁免判定（元问/引用形）→豁免放行照常解析/硬终止拒答；
        # 先于一切解析（V1 W-F19 0 号位语义）。缝缺省（词典层缺）＝闸静默
        # 零漂移。快车道（词条卡/FAQ 直出）已随 P-051b 辅助模式返工拆除。——
        gate_kind, gate_payload = _n1_code_first_gate(state, deps)
        if gate_kind == "refused":
            assert isinstance(gate_payload, dict)
            return gate_payload
        exempt_notice: dict[str, Any] | None = None
        exempt_step: dict[str, Any] | None = None
        if gate_kind == "exempt":
            # 豁免放行（元问/引用形——V1 DE-03 等效补齐）：豁免 notice/步先落，
            # understand 照常解析（放行路＝原问句进完整管线，非直出非拦停）。
            assert gate_payload is not None
            exempt_notice, exempt_step = _ban_exempt_preflight(
                state, deps, gate_payload
            )
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
        # 豁免步已占 seq（0 号位簿记先行）——本步 seq 顺延一位。
        seq = _next_seq(state) + (1 if exempt_step is not None else 0)
        record = _step_record(
            seq, STEP_DECISION, understanding or "理解未产出", context.manifest,
            payload={"phase": "understand"},
        )
        deps.bus.emit(
            "step", {"step": STEP_DECISION, "seq": seq, "title": record["title"]}
        )
        if understanding:
            deps.bus.emit("text", {"content": understanding})
        steps = [*state.steps, record]
        if exempt_step is not None:
            steps = [*state.steps, exempt_step, record]  # 豁免步在前（seq 序）
        updates: dict[str, Any] = {
            "understanding": understanding,
            "metric_candidates": candidates,
            "history": history,
            "manifests": [*state.manifests, context.manifest.as_dict()],
            "steps": steps,
            "next_intent": INTENT_DECISION,
        }
        if exempt_notice is not None:
            updates["notices"] = [*state.notices, exempt_notice]
        return updates

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
        if emission.retrieval_need is not None:
            # V2-50 族 C ①anchors 确定性注入：问句实体词（井号/油田名/报告号——
            # 本体对象闭世界匹配）由代码解析注入，模型可增补不可清空（注入在
            # 同参指纹之前——注入随发射载荷定型，重投闸比对面一致）。
            emission = replace(
                emission,
                retrieval_need=inject_retrieval_anchors(emission.retrieval_need),
            )
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


async def _handle_choice(
    state: RunState, deps: LoopDeps, *, four_phase: bool = False
) -> dict[str, Any]:
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
        # 用户输入重置轮预算（新信息＝新周期——旧 repairs_since_input 重置同义，
        # C3 追认落字：轮预算按「每用户输入周期 3 轮」计）；预算拒免轮例外
        # 计数同周期清零。
        updates["user_hint"] = value
        updates["rounds"] = 0
        updates["budget_reject_streak"] = 0
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
        if four_phase:
            # 四相位（A2 裁决落点＋V2-52 续跑全通道）：放行名单＝帧 detail.tables
            # （表名集——前置条件机越集闸与引擎 F14 闸共同的比对面）随审批单号
            # 一并进 approved_ids（ToolContext 随行），回前置条件机重判（放行后
            # pass/note），不重排计划、不走 last_execute 重投通道。前置闸与引擎
            # 侧闸（V2-44 实扫/F14）两道审批共用本通道——批准即续跑（前置重判
            # →批量重执行；引擎 run 按放行态放行已批表，出数收口）。
            tables = [
                str(t)
                for t in ((frame.get("detail") or {}).get("tables") or ())
                if str(t).strip()
            ]
            updates["approved_ids"] = [
                *state.approved_ids,
                str(approval_id or ""),
                *tables,
            ]
            updates["extable_rounds"] = state.extable_rounds + 1
            updates["next_intent"] = INTENT_PRECONDITION
        else:
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
                updates["approved_ids"] = [
                    *state.approved_ids,
                    str(approval_id or ""),
                ]
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
    分型拒因（校验拒／暂不可用／闸拒）」，负信息如实落，模型面可见）。
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
        # 发现计数埋点（V2-34 任务 5/R5）：次数/查询词/命中形态落 step payload——
        # 供跑批分析（no_hit 循环回归为零的判定面）。
        incoming_tap = _observations_of(result)
        tap_notices = [
            obs
            for obs in incoming_tap
            if str((obs.get("locator") or {}).get("notice_type", "")) == "no_hit"
        ]
        discover_used = int(state.discover_used) + 1
        tap = {
            "index": discover_used,
            "tool": tool_name,
            "query": _payload_fingerprint(args),
            "hits": len(incoming_tap),
            "shape": (
                "no_hit"
                if tap_notices
                else (f"rows:{len(incoming_tap)}" if incoming_tap else "empty")
            ),
        }
        updates = _apply_result(
            state,
            deps,
            result,
            seq,
            kind=STEP_DISCOVER,
            tool_name=tool_name,
            args=args,
            record_payload={
                "tool": tool_name,
                "status": result["status"],
                "discover_tap": tap,
            },
            retry_state={"pending_discovers": [call, *queue[1:]]},
        )
        updates["discover_used"] = discover_used
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


# ---------- V2-34 四相位节点（ADR-0005——①澄清分解／②工具匹配／③前置条件机／④批量执行） ----------


def _group_subtasks(state: RunState) -> list[dict[str, Any]]:
    """问题组子问题投影（question_group dict → dict 列——恢复段读面）。"""
    group = state.question_group or {}
    return [st for st in (group.get("subtasks") or []) if isinstance(st, dict)]


def _group_of(state: RunState) -> QuestionGroup | None:
    """问题组 schema 形重建（相位②闭合世界对账的输入面）。"""
    subtasks = _group_subtasks(state)
    if not subtasks:
        return None
    return QuestionGroup(
        subtasks=tuple(
            Subtask(
                id=str(st.get("id") or ""),
                question=str(st.get("question") or ""),
                ledger_notes=str(st.get("ledger_notes") or ""),
                chain=str(st.get("chain") or ""),
                tool=str(st.get("tool") or ""),
            )
            for st in subtasks
        )
    )


def _make_clarify(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    """相位①业务澄清（caller decision——分解问题组／钻取 discover／反问 ask）。

    轮语义（Owner 拍板）：decompose 占轮（轮＝回炉循环周期）；discover 钻取与
    拒因回喂不占轮（受全 run ≤10 发现预算闸——两套预算各守其界）；ask 挂起不
    占轮（用户输入重置轮预算，与 decision 节点同款）。词典层第 1 轮全量注入
    （拍板 a）——常驻块随每轮澄清在场，入史轮收窄防 token 放大。
    """

    async def clarify_node(state: RunState) -> dict[str, Any]:
        # 挂起恢复路径：interrupt 返回用户选择（ clarify 入口为四相位唯一挂起点）。
        if state.pending_ask is not None:
            return await _handle_choice(state, deps, four_phase=True)
        if (converged := _gate_or_none(state, deps, rounds_gate=True)) is not None:
            return converged
        dump = state.ledger_dump
        if dump is None and deps.ledger_dump is not None:
            dump = deps.ledger_dump()
        contract = (
            CLARIFY_CONTRACT
            .replace("{max_subtasks}", str(MAX_SUBTASKS_CONTRACT))
            .replace("{discover_used}", str(state.discover_used))
        )
        # 指南消费缝消歧：相位发射合同前置（本相位唯一有效合同——真模型对
        # 首位合同的跟随最稳，P033SK1 实证双合同并存会照抄 legacy 动作）；
        # 指南正文随后只作业务规则参考（窗词锚定/单井红线/名册——其动作类
        # 措辞由本合同取代；资产零触碰，消歧在本消费缝）。
        instruction = (
            "【相位①·业务澄清——本相位唯一有效发射合同（.action 只许 "
            "discover|decompose|ask|finalize；指南正文中出现的 execute 动作"
            "归后续相位，本相位发射它＝非法）】\n"
            + contract
            + "\n\n【业务规则参考（ontology 指南 §A——窗词锚定/单井红线/"
            "指标名册适用；其中发射判据/收口硬规则的动作面以上方合同为准）】\n"
            + deps.guide.guide()
            # P-051b 真批修正（P051BW 术语躺井/数-降1/数-降2 零交付形——真模型
            # 把台账常驻注入当「材料足够」零观察定稿）：finalize 交付面边界句。
            + "\n\n【finalize 交付面边界——台账常驻注入不进交付面（不计入"
            "「材料足够」）：仅凭注入就能回答的术语/口径定义问，先 discover "
            "semantic_query 取条目卡再定稿；零探查观察时禁 finalize。】"
        )
        failed = [dict(r) for r in state.subtask_results if r.get("status") == "failed"]
        if failed:
            lines = "\n".join(
                f"- [{r.get('id')}] {r.get('question', '')}——拒因：{r.get('reason', '')}"
                for r in failed
            )
            instruction += (
                "\n\n回炉：只分解以下失败/缺失子问题（成功子问题结果已保留，"
                f"禁止重复分解执行）：\n{lines}"
            )
        if state.user_hint:
            instruction += f"\n用户已补充：{state.user_hint}——请把它落进本轮分解。"
        if state.decision_error:
            # 拒因回喂（拍板②同款——无 repair，修正后重新输出 JSON）。
            instruction += (
                f"\n上次发射被拒：{state.decision_error}——修正后重新输出 JSON。"
            )
        context = deps.builder.compile(
            state,
            step=STEP_DECISION,
            instruction=instruction,
            extra_sources=_resident_sources(dump) if dump else None,
        )
        content = await _complete(deps.model(MODEL_DECISION), context)
        history = _history_with(
            state,
            {
                "role": "user",
                "content": _slim_resident(str(context.messages[-1]["content"])),
            },
            _assistant_turn(content),
        )
        parsed = parse_question_group(
            content,
            max_discovers=int(
                state.budget.get("max_discovers_per_round", MAX_DISCOVERS_PER_ROUND_CONTRACT)
            ),
            discover_budget_left=MAX_DISCOVERS_PER_RUN_CONTRACT - int(state.discover_used),
        )
        seq = _next_seq(state)
        if isinstance(parsed, str):
            # 拒因回喂（无 repair）＋轮照耗（V2-31 同款语义——被拒发射也是一次
            # 决策周期，轮数闸收敛兜底，顽投不环）；例外＝发现预算驱动的
            # discover 拒（钻取面由 ≤10 预算闸自守，不占回炉轮）。S2 落闸
            # （P-033 中途审查）：免轮例外只留首次——连续预算拒自第 2 次起
            # 转占轮，轮数闸确定性收敛（免轮面不重开 SK2 同形无界自旋洞）。
            budget_reject = parsed.startswith(BUDGET_REJECT_MARK)
            streak = int(state.budget_reject_streak) + 1 if budget_reject else 0
            rnd = (
                (state.rounds if streak < 2 else state.rounds + 1)
                if budget_reject
                else state.rounds + 1
            )
            record = _step_record(
                seq, STEP_DECISION, f"澄清 r{rnd} 被拒：{parsed}",
                context.manifest,
                payload={"phase": "clarify", "rejection": parsed},
            )
            deps.bus.emit(
                "step", {"step": STEP_DECISION, "seq": seq, "title": record["title"]}
            )
            return {
                "rounds": rnd,
                "decision_error": parsed,
                "budget_reject_streak": streak,
                "ledger_dump": dump,
                "history": history,
                "manifests": [*state.manifests, context.manifest.as_dict()],
                "steps": [*state.steps, record],
                "next_intent": INTENT_DECISION,
            }
        emission = parsed
        base: dict[str, Any] = {
            "decision_error": "",
            "user_hint": "",
            "budget_reject_streak": 0,  # 非预算拒结局——免轮例外计数清零
            "ledger_dump": dump,
            "history": history,
            "manifests": [*state.manifests, context.manifest.as_dict()],
        }
        payload: dict[str, Any] = {"phase": "clarify", "emission": emission.as_payload()}
        if emission.kind == CLARIFY_DECOMPOSE:
            rnd = state.rounds + 1  # 分解占轮——轮 2/3 只带失败子集回炉
            count = len(emission.group.subtasks) if emission.group is not None else 0
            record = _step_record(
                seq, STEP_DECISION, f"澄清 r{rnd}：分解 {count} 子问题",
                context.manifest, payload,
            )
            deps.bus.emit(
                "step", {"step": STEP_DECISION, "seq": seq, "title": record["title"]}
            )
            if emission.note:
                notice = {
                    "type": "decision_note", "gates": [], "content": emission.note,
                }
                deps.bus.emit("notice", dict(notice))
                base["notices"] = [*state.notices, notice]
            return {
                **base,
                "rounds": rnd,
                "question_group": emission.group.as_payload() if emission.group else None,
                "precondition_verdicts": [],  # 新轮问题组——旧判定作废（判定随组走）
                "steps": [*state.steps, record],
                "next_intent": INTENT_TOOLMATCH,
            }
        if emission.kind == CLARIFY_DISCOVER:
            names = "、".join(str(item.get("tool", "?")) for item in emission.discovers)
            record = _step_record(
                seq, STEP_DECISION,
                f"澄清钻取 ×{len(emission.discovers)}（{names}）",
                context.manifest, payload,
            )
            deps.bus.emit(
                "step", {"step": STEP_DECISION, "seq": seq, "title": record["title"]}
            )
            return {
                **base,
                "pending_discovers": [dict(item) for item in emission.discovers],
                "steps": [*state.steps, record],
                "next_intent": INTENT_DISCOVER,
            }
        if emission.kind == CLARIFY_FINALIZE:
            # V2-52 辅助模式消费规则（附 B）：faq 等辅助材料足够时模型判
            # sufficiency 直答（秒答形——路由起草面按观察材料出带引用答案；
            # 代码不干预判定）。不占轮（与 discover 同——轮＝回炉循环周期）。
            record = _step_record(
                seq, STEP_DECISION, "澄清定稿：材料足够——直答收口",
                context.manifest, payload,
            )
            deps.bus.emit(
                "step", {"step": STEP_DECISION, "seq": seq, "title": record["title"]}
            )
            if emission.note:
                notice = {
                    "type": "decision_note", "gates": [], "content": emission.note,
                }
                deps.bus.emit("notice", dict(notice))
                base["notices"] = [*state.notices, notice]
            return {
                **base,
                "steps": [*state.steps, record],
                "next_intent": INTENT_ANSWER,
            }
        # ask——连续澄清 cap（≥2 不再挂起带材料直答，与 decision 节点同款）。
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
            base["notices"] = [*state.notices, notice]
            _direct_answer(base, _clarify_capped_answer(state))
            return base
        frame = {
            "kind": ASK_CLARIFY,
            "prompt": emission.ask_prompt,
            "options": list(emission.ask_options),
            "detail": None,
        }
        record = _step_record(
            seq, STEP_DECISION,
            f"澄清 r{state.rounds + 1}：反问（{emission.ask_prompt[:24]}）",
            context.manifest, payload,
        )
        deps.bus.emit(
            "step", {"step": STEP_DECISION, "seq": seq, "title": record["title"]}
        )
        deps.bus.emit("ask", {"frame": frame, "run_id": state.run_id})
        base["consecutive_asks"] = consecutive
        base["pending_ask"] = frame
        base["steps"] = [*state.steps, record]
        base["next_intent"] = INTENT_DECISION  # 自环进 interrupt（挂起不占轮）
        return base

    return clarify_node


def _make_toolmatch(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    """相位②工具匹配（caller decision——子问题→工具/链提议；独立 schema 收口点）。

    matches 与问题组闭合世界对账（parse_tool_match——缺/多/未知 id 均拒）；
    拒因回喂自环（不占轮）；定案就地合并进 question_group（批量执行输入面）。
    """

    async def toolmatch_node(state: RunState) -> dict[str, Any]:
        # 轮闸不对称（轮语义：一轮＝完整相位周期）：本相位允许当前轮跑完
        # （rounds == max 合法），只拦「第 max+1 个决策周期」（被拒烧轮后的
        # 顽投自环）——clarify 入口闸（>= max）守新轮回炉。
        if (converged := _gate_or_none(state, deps)) is not None:
            return converged
        max_rounds = int(state.budget.get("max_rounds", MAX_ROUNDS_CONTRACT))
        if int(state.rounds) > max_rounds:
            return _converge(state, deps, gates=["max_rounds"])
        group = _group_of(state)
        if group is None:  # 恢复段边界兜底（无组＝回澄清）
            return {"next_intent": INTENT_DECISION}
        dump = state.ledger_dump
        instruction = (
            "【相位②·工具匹配——本相位唯一有效发射合同（只许输出 matches JSON）】\n"
            + TOOLMATCH_CONTRACT
            + "\n\n【业务规则参考（ontology 指南 §A——窗词锚定/单井红线/"
            "指标名册适用；动作类措辞以上方合同为准）】\n"
            + deps.guide.guide()
            + "\n\n问题组：\n"
            + json.dumps(group.as_payload(), ensure_ascii=False)
        )
        context = deps.builder.compile(
            state,
            step=STEP_DECISION,
            instruction=instruction,
            extra_sources=_resident_sources(dump) if dump else None,
        )
        content = await _complete(deps.model(MODEL_DECISION), context)
        history = _history_with(
            state,
            {
                "role": "user",
                "content": _slim_resident(str(context.messages[-1]["content"])),
            },
            _assistant_turn(content),
        )
        seq = _next_seq(state)
        parsed = parse_tool_match(content, group)
        if isinstance(parsed, str):
            # 拒因回喂（无 repair）＋轮照耗（被拒发射也是一次决策周期——轮数闸
            # 在本节点入口收敛兜底，顽投不环；P033SK2 实证无界自旋教训）。
            rnd = state.rounds + 1
            record = _step_record(
                seq, STEP_DECISION, f"工具匹配 r{rnd} 被拒：{parsed}", context.manifest,
                payload={"phase": "toolmatch", "rejection": parsed},
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
                "next_intent": INTENT_TOOLMATCH,  # 拒因回喂自环
            }
        # V2-50 族 C ①anchors 确定性注入（四相位半边）：knowledge 链匹配定案的
        # retrieval_need 逐支注入问句实体锚（模型可增补不可清空）——注入随定案
        # 落 question_group 与 tool_matches 双面（批量执行输入面同源零漂移）。
        injected = tuple(
            (
                replace(
                    match,
                    retrieval_need=inject_retrieval_anchors(match.retrieval_need),
                )
                if match.retrieval_need is not None
                else match
            )
            for match in parsed
        )
        by_id = {m.id: m for m in injected}
        merged: list[dict[str, Any]] = []
        for st in _group_subtasks(state):
            item = dict(st)
            match = by_id.get(str(st.get("id") or ""))
            if match is not None:
                item.update(
                    {
                        "chain": match.chain,
                        "tool": match.tool,
                        "plan": dict(match.plan) if match.plan is not None else None,
                        "retrieval_need": (
                            dict(match.retrieval_need)
                            if match.retrieval_need is not None
                            else None
                        ),
                        "caliber_key": match.caliber_key,
                    }
                )
            merged.append(item)
        record = _step_record(
            seq, STEP_DECISION, f"工具匹配：{len(injected)} 条定案", context.manifest,
            payload={
                "phase": "toolmatch",
                "emission": {"matches": [m.as_payload() for m in injected]},
            },
        )
        deps.bus.emit(
            "step", {"step": STEP_DECISION, "seq": seq, "title": record["title"]}
        )
        # FX-13 候选集随问题组闭世界刷新：当前组 data 链指标槽位＝本轮候选集
        # （回炉轮新支不被首轮 understand 候选集误伤；台账面校验仍归引擎）。
        slots = tuple(
            dict.fromkeys(
                str((m.plan or {}).get("metric_slot") or "")
                for m in parsed
                if m.chain == "data" and (m.plan or {}).get("metric_slot")
            )
        )
        return {
            "rounds": state.rounds,
            "decision_error": "",
            "question_group": {"subtasks": merged},
            "tool_matches": [m.as_payload() for m in injected],
            "metric_candidates": list(slots) if slots else list(state.metric_candidates),
            "history": history,
            "manifests": [*state.manifests, context.manifest.as_dict()],
            "steps": [*state.steps, record],
            "next_intent": INTENT_PRECONDITION,
        }

    return toolmatch_node


def _make_precondition(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    """相位③前置条件机（纯固定代码零 LLM——逐子问题判四态；LLM 无权判定）。"""

    async def precondition_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            return converged
        subtasks = _group_subtasks(state)
        if not subtasks:  # 恢复段边界兜底（无组＝回澄清）
            return {"next_intent": INTENT_DECISION}
        facts = ledger_facts(state.ledger_dump or {})
        watermark = _watermark_date_of(deps)
        data_wells = _data_wells_set(deps)
        # 用户已答窗（V2-51 词面门零误伤面）：run 内有 clarify resume 留痕＝窗经
        # 用户锚定——词面门静默（机械改判会与用户答案打架）。
        window_resolved = any(
            isinstance(choice, dict) and choice.get("kind") == ASK_CLARIFY
            for choice in state.resume_choices
        )
        matches_by_id = {
            str(m.get("id")): m for m in state.tool_matches if isinstance(m, dict)
        }
        judged: list[Any] = []
        plan_prints: dict[str, str] = {}  # 子问题 id → 判定面计划载荷指纹（同参比对面）
        for st in subtasks:
            sid = str(st.get("id") or "")
            match = matches_by_id.get(sid) or {}
            judged.append(judge(
                SubtaskInput(
                    subtask_id=sid,
                    question=str(st.get("question") or ""),
                    chain=str(match.get("chain") or st.get("chain") or "data"),
                    plan=match.get("plan"),
                    retrieval_need=match.get("retrieval_need"),
                ),
                facts,
                approved_tables=tuple(state.approved_ids),
                watermark=watermark,
                window_resolved=window_resolved,
                data_wells=data_wells or None,
            ))
            plan_prints[sid] = _payload_fingerprint(
                {"plan": dict(match.get("plan") or {}), "retrieval_need": None}
            )
        # —— V2-43 换链回炉闸（Owner 方案 A——P-039 疑点 3 拍板）：data 链＋指标
        # 在册（F7 归一后）＋绑定闸拒（未绑定 agg）＝不直答不执行——携拒因＋改链
        # hint＋「换链提议」标记回炉①澄清相位（复用现有失败子集回炉机制；占一轮，
        # 不占 ask 预算/不挂起）。一次为界：标记在册后同支（同 id 或同参指纹）再
        # 触发＝blocked_refuse 直答终局（不环——同参指纹在本簿记；V2-37 执行面
        # executed_payloads 簿记同向互替）。其余拒因四态语义一字不动。
        # V2-51 同轨扩面：软失败域闸（题眼井全外于数据链井闭世界——chain_switch_
        # kind="domain"）同轨同簿记，仅拒因/通知措辞随型分叉（轨道语义零改动）。
        marks = dict(state.chain_switch_marks)
        chain_pending: set[str] = set()
        chain_kinds: dict[str, str] = {}
        for index, verdict in enumerate(judged):
            if not verdict.chain_switch_trigger:
                continue
            sid = verdict.subtask_id
            fingerprint = plan_prints.get(sid, "")
            kind = verdict.chain_switch_kind or CHAIN_SWITCH_KIND_UNBOUND
            if sid in marks or fingerprint in marks.values():
                terminal_tail = (
                    "未绑定口径如实拒答，不代答"
                    if kind == CHAIN_SWITCH_KIND_UNBOUND
                    else "题眼井不在数据链井闭世界——域错如实拒答，不代答"
                )
                judged[index] = replace(
                    verdict,
                    state=STATE_BLOCKED_REFUSE,
                    reason=(
                        "换链回炉已用尽（一次为界）：坚持 data 链同参"
                        f"（指纹 {fingerprint[:12]}…在簿）——{terminal_tail}"
                    ),
                )
                continue
            marks[sid] = fingerprint
            chain_pending.add(sid)
            chain_kinds[sid] = kind
        verdicts: list[dict[str, Any]] = [v.as_payload() for v in judged]
        seq = _next_seq(state)
        title = "前置条件机：" + "｜".join(
            f"{v['subtask_id']}={v['state']}" for v in verdicts
        )
        deps.bus.emit("step", {"step": STEP_DECISION, "seq": seq, "title": title})
        # F7 名归一落载（P-039 附 4）：命中归一的子问题把 plan.metric_slot 改写为
        # 台账 slot（后续闸与批量执行对 slot 判定——引擎 metric_by_name 精确命
        # 中）。V2-51 词面门落载：fuzzy_window_rewrite 的子问题把 plan 窗双槽
        # 确定性改写 None（引擎缺参反问兜底——数-反1 形）。两类改写随
        # precondition_verdicts 一并落 state（tool_matches 执行面＋question_group
        # 记录面同改，防双面漂移）。
        normalized_slots = {
            str(v["subtask_id"]): str(v["normalized_slot"])
            for v in verdicts
            if v.get("normalized_slot")
        }
        fuzzy_ids = {
            str(v["subtask_id"]) for v in verdicts if v.get("fuzzy_window_rewrite")
        }
        if normalized_slots or fuzzy_ids:
            rewritten_matches: list[dict[str, Any]] = []
            for item in state.tool_matches:
                entry = dict(item)
                sid = str(entry.get("id") or "")
                plan_item = entry.get("plan")
                if isinstance(plan_item, dict) and (sid in fuzzy_ids or normalized_slots.get(sid)):
                    if sid in fuzzy_ids:
                        plan_item = {
                            **plan_item, "window_start": None, "window_end": None,
                        }
                    slot = normalized_slots.get(sid)
                    if slot:
                        plan_item = {**plan_item, "metric_slot": slot}
                    entry["plan"] = plan_item
                rewritten_matches.append(entry)
            rewritten_group: list[dict[str, Any]] = []
            for st in _group_subtasks(state):
                entry = dict(st)
                sid = str(entry.get("id") or "")
                plan_item = entry.get("plan")
                if isinstance(plan_item, dict) and (sid in fuzzy_ids or normalized_slots.get(sid)):
                    if sid in fuzzy_ids:
                        plan_item = {
                            **plan_item, "window_start": None, "window_end": None,
                        }
                    slot = normalized_slots.get(sid)
                    if slot:
                        plan_item = {**plan_item, "metric_slot": slot}
                    entry["plan"] = plan_item
                rewritten_group.append(entry)
        else:
            rewritten_matches = list(state.tool_matches)
            rewritten_group = _group_subtasks(state)
        # FX-13 候选集随归一刷新（改写后的 data 链 slot 才是引擎候选面——原始
        # 发射名滞留候选集会把归一 slot 误判成「指标替换」）。
        canonical_slots = tuple(
            dict.fromkeys(
                str((m.get("plan") or {}).get("metric_slot") or "")
                for m in rewritten_matches
                if m.get("chain") == "data" and (m.get("plan") or {}).get("metric_slot")
            )
        )
        updates: dict[str, Any] = {
            "precondition_verdicts": verdicts,
            "tool_matches": rewritten_matches,
            "question_group": {"subtasks": rewritten_group},
            "metric_candidates": (
                list(canonical_slots)
                if canonical_slots
                else list(state.metric_candidates)
            ),
            "steps": [
                *state.steps,
                _step_record(
                    seq, STEP_DECISION, title, None,
                    payload={
                        "phase": "precondition",
                        "pure_code": True,
                        "verdicts": verdicts,
                        # 换链回炉指纹簿记（V2-43——不环钉的 step payload 断言面）。
                        **({"chain_switch_marks": dict(marks)} if marks else {}),
                    },
                ),
            ],
        }
        questions = {str(st.get("id") or ""): str(st.get("question") or "") for st in subtasks}
        refusals = [
            {
                "id": v["subtask_id"],
                "status": "refused",
                "reason": v["reason"],
                "question": questions.get(v["subtask_id"], ""),
                "obs_count": 0,
                "fingerprint": "",
                "chain": "data",
            }
            for v in verdicts
            if v["state"] == STATE_BLOCKED_REFUSE
        ]
        # 换链回炉触发支＝回炉面失败条目（非终局——status=failed 供澄清相位
        # 失败子集回炉消费；拒因携 hint＋「换链提议」标记随行）。
        chain_entries = [
            {
                "id": v["subtask_id"],
                "status": "failed",
                "reason": (
                    str(v["reason"]) + "（换链提议：回炉①改链重决策——一次为界）"
                ),
                "question": questions.get(v["subtask_id"], ""),
                "obs_count": 0,
                "fingerprint": marks.get(str(v["subtask_id"]), ""),
                "chain": "data",
                "chain_switch": True,
            }
            for v in verdicts
            if str(v["subtask_id"]) in chain_pending
        ]
        if refusals or chain_entries:
            # 同 id 只留最新判定（refused/回炉面 failed 取代旧条目——后续轮若转
            # pass 由批量 upsert 接管，结果面不残留双行）。
            results = list(state.subtask_results)
            for block in (refusals, chain_entries):
                block_ids = {r["id"] for r in block}
                results = [
                    r for r in results if str(r.get("id")) not in block_ids
                ]
                results.extend(block)
            updates["subtask_results"] = results
        extra_notices: list[dict[str, Any]] = []
        if chain_pending:
            # 分型措辞（V2-51）：绑定闸拒型保持 V2-43 原文逐字；域闸型携域错措辞
            # ——同轨同通知类型（chain_switch_reentry），一次为界语义零改动。
            unbound_ids = sorted(
                sid for sid in chain_pending
                if chain_kinds.get(sid, CHAIN_SWITCH_KIND_UNBOUND)
                == CHAIN_SWITCH_KIND_UNBOUND
            )
            domain_ids = sorted(
                sid for sid in chain_pending
                if chain_kinds.get(sid, CHAIN_SWITCH_KIND_UNBOUND)
                == CHAIN_SWITCH_KIND_DOMAIN
            )
            segments = ""
            if unbound_ids:
                segments += (
                    "子问题 " + "、".join(unbound_ids)
                    + " 绑定闸拒（data 链在册未绑定 agg）"
                )
            if domain_ids:
                if segments:
                    segments += "；"
                segments += (
                    "子问题 " + "、".join(domain_ids)
                    + " 题眼井不在数据链井闭世界（data 链域错成功返回——软失败域闸）"
                )
            header = (
                "换链回炉闸（V2-43）：" if not domain_ids else "换链回炉闸（V2-43/V2-51）："
            )
            notice = {
                "type": "chain_switch_reentry",
                "gates": [],
                "content": (
                    header + segments
                    + "——携拒因＋改链 hint 回炉①澄清相位（一次为界；坚持原链同参"
                    "再触发＝直答终局，不环）"
                ),
            }
            deps.bus.emit("notice", dict(notice))
            extra_notices.append(notice)
            updates["notices"] = [*state.notices, *extra_notices]
            updates["chain_switch_marks"] = marks
        asks = [v for v in verdicts if v["state"] == STATE_BLOCKED_ASK]
        executable = [
            v for v in verdicts
            if v["state"] in (STATE_PASS, STATE_NOTE)
            and str(v["subtask_id"]) not in chain_pending
        ]
        if asks and executable:
            # 可执行子问题先进批量（部分结果先行）；blocked_ask 由批量段收尾挂起。
            updates["next_intent"] = INTENT_BATCH
            return updates
        if asks:
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
                updates["notices"] = [*state.notices, *extra_notices, notice]
                _direct_answer(updates, _clarify_capped_answer(state))
                return updates
            updates["consecutive_asks"] = consecutive
            frame = dict(asks[0].get("ask") or {})
            updates["pending_ask"] = frame
            updates["next_intent"] = INTENT_DECISION  # 挂起：interrupt 在 clarify 入口
            deps.bus.emit("ask", {"frame": frame, "run_id": state.run_id})
            return updates
        if chain_pending and not executable:
            # 纯触发组（V2-43 语义变更点）：不直答——回炉①澄清相位（占一轮；
            # 失败子集回炉是发射回喂非 ASK——零挂起零 ask 预算）。
            updates["next_intent"] = INTENT_DECISION
            return updates
        if not executable:
            # 全部如实拒答——零执行零冒充，直答收口。（附 3：blocked_refuse 直答
            # 路径不带改链 hint——直答是终局；hint 只给可回炉重决策的路径面。）
            lines = "\n".join(
                f"- [{r['id']}] {r['question']}——拒因："
                f"{str(r['reason']).removesuffix(CHAIN_SWITCH_HINT)}"
                for r in refusals
            )
            _direct_answer(
                updates,
                "子问题前置条件判定全部拦截——如实回报，不编造：\n"
                + (lines or "（无可执行子问题。）"),
            )
            updates["next_intent"] = INTENT_ANSWER
            return updates
        updates["next_intent"] = INTENT_BATCH
        return updates

    return precondition_node


def _watermark_date_of(deps: LoopDeps) -> Any:
    """水位读缝→水位日期（WatermarkFace.data_date 投影；None＝缺行/未接线——
    新鲜度窗注记跳过，引擎闸仍权威）。运行策略面归 runtime（类型真源在
    query 引擎侧——防环不直接 import，duck 读 data_date 属性）。"""
    if deps.watermark is None:
        return None
    try:
        face = deps.watermark()
    except Exception:
        return None
    if face is None:
        return None
    return getattr(face, "data_date", face)


def _data_wells_set(deps: LoopDeps) -> frozenset[str]:
    """数据链井闭世界读缝→井号集（V2-51 软失败域闸判定输入——agg.dim_well
    投影；读缝缺省/异常/空＝空集——域闸静默零漂移，不误伤）。运行策略面归
    runtime（类型真源在 query 引擎侧——防环不直接 import，duck 迭代）。"""
    if deps.data_wells is None:
        return frozenset()
    try:
        world = deps.data_wells()
    except Exception:
        return frozenset()
    if not world:
        return frozenset()
    return frozenset(str(well) for well in world)


def _subtask_result(
    subtask_id: str,
    question: str,
    chain: str,
    *,
    status: str,
    reason: str = "",
    obs_count: int = 0,
    fingerprint: str = "",
) -> dict[str, Any]:
    return {
        "id": subtask_id,
        "status": status,  # ok | failed | refused（failed＝可回炉；refused＝终局拒答）
        "reason": reason,
        "question": question,
        "obs_count": obs_count,
        "fingerprint": fingerprint,
        "chain": chain,
    }


def _make_batch(
    deps: LoopDeps,
) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]:
    """相位④批量执行（固定代码——子问题组逐支执行＋观察汇聚；汇总归 answer 节点）。

    回炉不重跑（R4）：status=ok 的子问题跳过（subtask_results 簿记＋执行指纹
    实录）；失败子集在轮预算内回炉①澄清（带拒因）；refused 终局进汇总如实
    陈述。每次执行落执行台账轮（P-032 簿记主干复用）＋执行步记录
    （payload 携 subtask_id/fingerprint——R4 断言面）。
    """

    async def batch_node(state: RunState) -> dict[str, Any]:
        if (converged := _gate_or_none(state, deps)) is not None:
            return converged
        subtasks = _group_subtasks(state)
        if not subtasks:  # 恢复段边界兜底（无组＝回澄清）
            return {"next_intent": INTENT_DECISION}
        matches_by_id = {
            str(m.get("id")): m for m in state.tool_matches if isinstance(m, dict)
        }
        verdicts_by_id = {
            str(v.get("subtask_id")): v
            for v in state.precondition_verdicts
            if isinstance(v, dict)
        }
        results: list[dict[str, Any]] = list(state.subtask_results)
        results_by_id = {str(r.get("id")): r for r in results}
        observations = list(state.observations)
        steps = list(state.steps)
        history = list(state.history)
        executed = list(state.executed_payloads)
        pending_frame: dict[str, Any] | None = None
        aggregated = 0
        # 缺位回捞簿记与门帧（V2-46 R1c——marks 随 state 更新；门帧机读 notice）。
        marks = dict(state.window_miss_marks)
        recall_notices: list[dict[str, Any]] = []
        max_rounds = int(state.budget.get("max_rounds", MAX_ROUNDS_CONTRACT))
        for st in subtasks:
            sid = str(st.get("id") or "")
            question = str(st.get("question") or "")
            verdict = verdicts_by_id.get(sid) or {}
            if verdict.get("state") not in (STATE_PASS, STATE_NOTE):
                continue  # 前置未放行（blocked_*——非批量辖域）
            if (
                verdict.get("state") == STATE_NOTE
                and verdict.get("chain_switch_trigger")
                and sid in state.chain_switch_marks
            ):
                continue  # V2-43 换链回炉标记面：触发支本轮不执行——回炉①改链重决策
            prior = results_by_id.get(sid)
            if prior is not None and prior.get("status") == "ok":
                continue  # 成功子问题不重跑（R4——执行指纹零重复）
            match = matches_by_id.get(sid) or {}
            chain = str(match.get("chain") or "")
            if chain == "data":
                tool_name = DATA_QUERY
                plan_exec = {
                    k: v
                    for k, v in dict(match.get("plan") or {}).items()
                    if k != "caliber_key"  # caliber_key 消费点＝前置条件机（域面零漂移）
                }
                args: dict[str, Any] = {"plan_draft": plan_exec}
                fingerprint = _payload_fingerprint(
                    {"plan": plan_exec, "retrieval_need": None}
                )
            else:
                tool_name = DOC_RETRIEVE
                args = dict(match.get("retrieval_need") or {})
                fingerprint = _payload_fingerprint(
                    {"plan": None, "retrieval_need": args}
                )
            raw = await _invoke_tool(deps, state, tool_name, args)
            timeout = float(state.budget.get("tool_timeout_seconds", 30.0))
            result = (
                _timeout_result(tool_name, timeout) if raw is None else _result_dict(raw)
            )
            status = result["status"]
            incoming = _observations_of(result)
            indexed: list[dict[str, Any]] = []
            for offset, obs in enumerate(incoming, start=1):
                entry = dict(obs)
                entry["index"] = len(observations) + offset
                entry["trust"] = trust_of(entry)
                indexed.append(entry)
            aggregated += len(indexed)
            # 缺位回捞信号面（V2-46 R1c）：window_miss 观察在场＝缺位来源名单非空。
            miss_obs = next(
                (
                    obs
                    for obs in indexed
                    if (obs.get("locator") or {}).get("kind") == "window_miss"
                ),
                None,
            )
            seq = len(steps) + 1
            error_message = (
                (result.get("error") or {}).get("message")
                if status == STATUS_FAILED
                else None
            )
            deps.bus.emit(
                "tool",
                {"tool": tool_name, "status": status, "seq": seq,
                 "message": error_message},
            )
            title = f"{tool_name}：{status}（子问题 {sid}）"
            deps.bus.emit("step", {"step": STEP_EXECUTE, "seq": seq, "title": title})
            steps.append(
                _step_record(
                    seq, STEP_EXECUTE, title, None,
                    payload={
                        "subtask_id": sid,
                        "chain": chain,
                        "tool": tool_name,
                        "status": status,
                        "fingerprint": fingerprint,
                        # 缺位注记随行（V2-46 R1c——回捞触发帧证据面；无缺位零键）。
                        **(
                            {"window_miss": str(miss_obs.get("content", ""))}
                            if miss_obs is not None
                            else {}
                        ),
                    },
                )
            )
            history = [*history, _ledger_turn(tool_name, args, result)]
            if status == STATUS_OK:
                observations.extend(indexed)
                executed.append(fingerprint)
                # —— V2-46 R1c 缺位回捞（「够得着」）：window_miss 观察在场＝缺位
                # 来源名单非空（模型面已可见）。三分支：回捞已用尽（同 id 或同参
                # 指纹在簿——V2-37 簿记同向）＝直答如实终局（ok＋终局注记，不环）；
                # 首遇缺位＋轮预算有余＋名单与题面表面相关（recall_relevant——
                # 合同条件「本问题组相关报告/章节在列」的确定性机读）＝开回捞门
                # （转回炉面 failed——拒因携检索窗注记，clarify 回炉重发带 anchors
                # 的 knowledge 链检索，每子问题限一次、消耗一轮、不挂起不占 ask）；
                # 轮预算无余或名单与题面无表面关联＝门不开（ok 原形——注记照常
                # 在窗）。无缺位＝原形零漂移。
                results = [r for r in results if str(r.get("id")) != sid]
                if miss_obs is not None and (
                    sid in marks or fingerprint in marks.values()
                ):
                    results.append(
                        _subtask_result(
                            sid, question, chain, status="ok",
                            obs_count=len(indexed), fingerprint=fingerprint,
                            reason=(
                                "缺位回捞已用尽（一次为界）：缺位来源仍未进窗"
                                "——按现有材料如实作答，不再重发检索"
                            ),
                        )
                    )
                elif (
                    miss_obs is not None
                    and int(state.rounds) < max_rounds
                    # 回捞白场合同条件「本问题组相关报告/章节在列」的确定性机读
                    # （recall_relevant——零模型词面判定）：名单与题面无表面关联
                    # ＝门不开（机器不为噪声名单消耗回炉轮——名单可见性照常）。
                    and recall_relevant(question, str(miss_obs.get("content", "")))
                ):
                    marks[sid] = fingerprint
                    results.append(
                        _subtask_result(
                            sid, question, chain, status="failed",
                            reason=(
                                f"{miss_obs.get('content', '')}"
                                "（缺位回捞白场：可经回炉对该子问题重发带 anchors"
                                "（报告名/章节锚）的 knowledge 链检索——一次为界）"
                            ),
                            fingerprint=fingerprint,
                        )
                    )
                    notice = {
                        "type": "window_miss_reentry",
                        "gates": [],
                        "content": (
                            f"缺位回捞闸（V2-46）：子问题 {sid} 检索窗载缺位来源"
                            "（名单已以 window_miss 观察进模型面）——回炉回捞："
                            "重发带 anchors（报告名/章节锚）的 knowledge 链检索"
                            "（每子问题限一次；再触发＝直答终局不环）"
                        ),
                    }
                    deps.bus.emit("notice", dict(notice))
                    recall_notices.append(notice)
                else:
                    # 同 id 只留最新结果（R4 簿记面：失败条目被成功条目取代——
                    # 旧 failed 滞留会造出假回炉环）。
                    results.append(
                        _subtask_result(
                            sid, question, chain, status="ok",
                            obs_count=len(indexed), fingerprint=fingerprint,
                        )
                    )
                for obs in indexed:
                    if (obs.get("locator") or {}).get("kind") == "notice":
                        deps.bus.emit(
                            "notice",
                            {
                                "type": str(
                                    (obs.get("locator") or {}).get(
                                        "notice_type", "notice"
                                    )
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
            elif status == STATUS_ASK:
                frame = dict(result.get("ask") or {})
                if frame.get("kind") == ASK_EXTERNAL_TABLE_APPROVAL:
                    detail = dict(frame.get("detail") or {})
                    engine_seed = str(detail.get("approval_id", ""))
                    if engine_seed:
                        detail["approval_id"] = reseed_approval_id(
                            state.run_id, engine_seed
                        )
                        frame["detail"] = detail
                deps.bus.emit("ask", {"frame": frame, "run_id": state.run_id})
                pending_frame = frame
                break  # 挂起不占轮——余下子问题待恢复后随批重入
            else:
                category = str((result.get("error") or {}).get("category") or "")
                reason = str(
                    (result.get("error") or {}).get("message") or "执行失败"
                )
                final = category == CATEGORY_REFUSED
                results = [r for r in results if str(r.get("id")) != sid]
                results.append(
                    _subtask_result(
                        sid, question, chain,
                        status="refused" if final else "failed", reason=reason,
                    )
                )
                deps.bus.emit(
                    "notice",
                    {
                        "type": "subtask_refused" if final else "subtask_failed",
                        "gates": [],
                        "content": (
                            f"子问题 {sid} {'闸拒（如实转答）' if final else '执行失败（回炉面）'}"
                            f"：{reason}"
                        ),
                    },
                )
                continue  # 失败子集回炉／refused 终局进汇总——批量继续余下子问题
        # 汇聚记录（观察回流批量形——observe 类步 payload.phase=batch）
        seq = len(steps) + 1
        title = f"批量汇聚 {aggregated} 支"
        deps.bus.emit("step", {"step": STEP_OBSERVE, "seq": seq, "title": title})
        steps.append(
            _step_record(seq, STEP_OBSERVE, title, None,
                         payload={"phase": "batch", "count": aggregated})
        )
        updates: dict[str, Any] = {
            "observations": observations,
            "steps": steps,
            "history": history,
            "executed_payloads": executed,
            "subtask_results": results,
        }
        if marks != state.window_miss_marks:
            updates["window_miss_marks"] = marks
        if recall_notices:
            updates["notices"] = [*state.notices, *recall_notices]
        if pending_frame is not None:
            updates["pending_ask"] = pending_frame
            updates["next_intent"] = INTENT_DECISION  # 挂起：interrupt 在 clarify 入口
            return updates
        unresolved = [
            v for v in state.precondition_verdicts
            if isinstance(v, dict) and v.get("state") == STATE_BLOCKED_ASK
        ]
        if unresolved:
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
                return updates
            updates["consecutive_asks"] = consecutive
            frame = dict(unresolved[0].get("ask") or {})
            updates["pending_ask"] = frame
            updates["next_intent"] = INTENT_DECISION
            deps.bus.emit("ask", {"frame": frame, "run_id": state.run_id})
            return updates
        failed = [r for r in results if r.get("status") == "failed"]
        if failed and int(state.rounds) < max_rounds:
            # 失败子集回炉①（轮 2/3 只带失败子问题＋拒因——成功不重跑）；
            # 轮预算耗尽＝带部分结果如实收口（3 轮部分续找语义）。
            updates["next_intent"] = INTENT_DECISION
            return updates
        updates["next_intent"] = INTENT_ANSWER
        return updates

    return batch_node


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
        # V2-50 族 C ②归属审锚面：题眼锚＝问句实体词（闭世界解析，确定性零模型）
        # ——无实体题＝空锚，审全静默（不误伤钉）。
        anchors = entity_anchor_tokens(state.question)
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
                state.draft, state.observations, anchors=anchors
            )
        _aligned, crossed = _attribution_conflicts(
            anchors, set(cited), state.observations
        )
        attribution = {
            "anchors": list(anchors),
            "cross": sorted(int(obs["index"]) for obs in crossed),
        }
        verdict = {
            "supported": len(cited),
            "rewritten": rewritten,
            "split": split,
            "cited": cited,
            "attribution": attribution,
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
        if crossed:
            deps.bus.emit(
                "notice",
                {
                    "type": "attribution_split",
                    "gates": [],
                    "content": (
                        "跨源归属审（V2-50）：答案被引检索片段 "
                        + "、".join(f"[{obs['index']}]" for obs in crossed)
                        + " 的引标源与题眼锚（"
                        + ("、".join(anchors) if anchors else "")
                        + "）不一致——答案面分源列明（跨源引用按出处如实区分）"
                    ),
                },
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
    by_index = {int(obs["index"]): obs for obs in state.observations}
    answer = state.draft or state.answer or "（未取得可交付答案——如实回报，不编造。）"
    # 收口注记确定性随行（V2-23——LIMIT 截断披露不靠模型自觉；草稿已自带则不重复）。
    closing = _lineage_closing_note(state.observations)
    if closing and "收口注记" not in answer:
        answer += "\n\n" + closing
    # V2-48 citation 落账：答案面 [n] ↔ citation 帧同步（悬空形清零——答案有
    # [n] 而 citation 帧零支的 ⚠20 宽口径形收口）。帧集＝核验支撑集 ∪ 答案文本
    # 携带的合法 [n]（观察在界）；引用块仍只列核验支撑集（R9「无支撑引标不收
    # 进引用集」语义不变——悬空 [n] 只落帧不进引用块）。
    supported: list[int] = sorted({int(n) for n in verdict.get("cited") or []})
    if supported:
        lines = [
            f"[{index}] {by_index[index].get('source', '')} · "
            f"{by_index[index].get('source_id', '')}（{by_index[index].get('trust', '')}）"
            for index in supported
            if index in by_index
        ]
        answer += "\n\n引用：\n" + "\n".join(lines)
    cited: list[int] = sorted(
        set(supported)
        | {int(n) for n in _CITE_RE.findall(answer) if int(n) in by_index}
    )
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
            # 四相位汇总（相位④后半）：问题组在场＝逐子问题整合全组子结果。
            instruction = _ANSWER_INSTRUCTION
            if state.question_group:
                marks = {"ok": "完成", "refused": "已拒答", "failed": "失败"}
                # plan 支配标记（V2-51 数-排2 形——drafting 指令面）：排名型子问题
                # 在清单行标注「结论必须从本子问题排名观察支取值」，明细型零标记
                # （零噪声）。
                plans_by_id = {
                    str(m.get("id")): dict(m.get("plan") or {})
                    for m in state.tool_matches
                    if isinstance(m, dict)
                }
                lines = []
                for r in state.subtask_results:
                    if not isinstance(r, dict):
                        continue
                    plan = plans_by_id.get(str(r.get("id", ""))) or {}
                    dominance = (
                        "（排名型——结论必须从本子问题排名观察支（合计行口径）取值，"
                        "不得从其他子问题的明细行切片换算或跨子问题取值）"
                        if plan.get("ranking") is True
                        else ""
                    )
                    lines.append(
                        "- [{id}] {question}——{mark}{reason}{dominance}".format(
                            id=r.get("id", ""),
                            question=r.get("question", ""),
                            mark=marks.get(str(r.get("status")), str(r.get("status"))),
                            reason=f"（{r.get('reason')}）" if r.get("reason") else "",
                            dominance=dominance,
                        )
                    )
                instruction = (
                    SUMMARY_CONTRACT
                    + "\n子问题结果清单：\n" + ("\n".join(lines) or "（无）")
                    + "\n\n"
                    + _ANSWER_INSTRUCTION
                )
            context = deps.builder.compile(
                state, step="answer", instruction=instruction
            )
            first_content = await _complete(deps.model(MODEL_ANSWER), context)
            # V2-48 JSON 通道隔离：发射围栏确定性剥离校验——泄漏→剥离（有余量
            # 直接交付）；零余量→同相位重试一次→交付重试草稿；再泄/再零→如实
            # 收口注记（发射围栏在任何路径下不进答案面）。
            draft, leaked = strip_emission_fences(first_content.strip())
            retry_content: str | None = None
            if not draft.strip():
                retry_content = await _complete(deps.model(MODEL_ANSWER), context)
                draft, retry_leaked = strip_emission_fences(retry_content.strip())
                leaked = leaked or retry_leaked
            if not draft.strip():
                draft = (
                    "（模型草稿为 JSON 通道残留——剥离重试仍未取得有效草稿，"
                    "如实收口。）"
                    if leaked
                    else "（模型未产出草稿——如实收口。）"
                )
            if leaked:
                deps.bus.emit(
                    "notice",
                    {
                        "type": "emission_strip",
                        "gates": [],
                        "content": (
                            "起草面检出 JSON 通道残留（发射围栏/裸 JSON 段）"
                            "——确定性剥离"
                            + ("＋同相位重试一次" if retry_content is not None else "")
                            + "（V2-48 JSON 通道隔离——不进答案面）"
                        ),
                    },
                )
            history_turns = [dict(context.messages[-1]), _assistant_turn(first_content)]
            if retry_content is not None:
                # 消息历史簿记（ADR-0006）：重试调用与两拍输出均如实入史。
                history_turns.append(_assistant_turn(retry_content))
            seq = _next_seq(state)
            title = "起草答案"
            deps.bus.emit("step", {"step": STEP_ANSWER, "seq": seq, "title": title})
            return {
                # 消息历史簿记（ADR-0006）：起草调用与草稿输出入簿。
                "history": _history_with(state, *history_turns),
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


def build_graph(deps: LoopDeps, *, checkpointer: Any = None, four_phase: bool = False) -> Any:
    """编译 ReAct 图（checkpointer 由 executor 注入——挂起/恢复的存储机制）。

    four_phase=True＝V2-34 四相位装配（ADR-0005）：clarify/toolmatch/precondition/
    batch 四相位真节点入图，understand 与全部「回决策」边重定向 clarify（INTENT_
    DECISION 值复用——语义＝回第一决策相位）；False＝V2-31 现行七节点图（默认，
    骨架期既有装配零漂移——缺省翻转随续作拍）。
    """
    builder = StateGraph(RunState)
    builder.add_node(NODE_UNDERSTAND, _node_of(_make_understand(deps)))
    builder.add_node(NODE_DECISION, _node_of(_make_decision(deps)))
    builder.add_node(NODE_DISCOVER, _node_of(_make_discover(deps)))
    builder.add_node(NODE_EXECUTE, _node_of(_make_execute(deps)))
    builder.add_node(NODE_OBSERVE, _node_of(_make_observe(deps)))
    builder.add_node(NODE_VERIFY, _node_of(_make_verify(deps)))
    builder.add_node(NODE_ANSWER, _node_of(_make_answer(deps)))
    routes = {name: dict(mapping) for name, mapping in _ROUTES.items()}
    if four_phase:
        builder.add_node(NODE_CLARIFY, _node_of(_make_clarify(deps)))
        builder.add_node(NODE_TOOLMATCH, _node_of(_make_toolmatch(deps)))
        builder.add_node(NODE_PRECONDITION, _node_of(_make_precondition(deps)))
        builder.add_node(NODE_BATCH, _node_of(_make_batch(deps)))
        for mapping in routes.values():
            if INTENT_DECISION in mapping:
                mapping[INTENT_DECISION] = NODE_CLARIFY
        routes[NODE_CLARIFY] = {
            INTENT_DECISION: NODE_CLARIFY,  # 拒因回喂自环／ask 挂起恢复入口
            INTENT_DISCOVER: NODE_DISCOVER,
            INTENT_TOOLMATCH: NODE_TOOLMATCH,
            # 审批恢复边（B1，P-033 中途审查）：_handle_choice 批准分支设
            # INTENT_PRECONDITION（前置条件机重判——A2 裁决落点），clarify
            # 路由表缺此键＝KeyError「两条审批恢复链全断」——前置条件机越集
            # 审批与批量引擎侧审批的恢复都从 clarify 入口回场，补边全通。
            INTENT_PRECONDITION: NODE_PRECONDITION,
            INTENT_ANSWER: NODE_ANSWER,
            INTENT_END: END,
        }
        routes[NODE_TOOLMATCH] = {
            INTENT_TOOLMATCH: NODE_TOOLMATCH,  # 匹配拒因回喂自环
            INTENT_PRECONDITION: NODE_PRECONDITION,
            INTENT_ANSWER: NODE_ANSWER,
            INTENT_END: END,
        }
        routes[NODE_PRECONDITION] = {
            INTENT_BATCH: NODE_BATCH,
            INTENT_DECISION: NODE_CLARIFY,  # blocked_ask 挂起恢复→clarify interrupt
            INTENT_ANSWER: NODE_ANSWER,
            INTENT_END: END,
        }
        routes[NODE_BATCH] = {
            INTENT_DECISION: NODE_CLARIFY,  # 引擎 ask 挂起／失败子集回炉①
            INTENT_ANSWER: NODE_ANSWER,
            INTENT_END: END,
        }
    builder.add_edge(START, NODE_UNDERSTAND)
    for name, mapping in routes.items():
        builder.add_conditional_edges(name, _route, mapping)
    return builder.compile(checkpointer=checkpointer)
