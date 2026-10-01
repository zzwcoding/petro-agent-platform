"""domains.chat.domain —— A1 问一问域语义层（厚：帧集/安检/装配/裁决/澄清/分派语义在此闭环）。

合同真源（只读引用，不复制正文）：teach-petro-agent/specs/api/A1-问一问.md v0.1
· 00-系统级API.md §6（SSE 帧信封＋三保留帧＋断线三收场）· PRD F56（统一入口
决策链——六路匹配器全扫全收集/候选上限 4 支/落空进建议池/澄清帧有界循环/
confidence 档位）· prototype flows/common.jsx（SEC_CHECKS/MATCHERS/CHAIN17 合
同常量照抄）· prototype A1Chat.jsx（拦截话术/澄清 choices 形状）· D2 v0.2
qa_behavior 消费口径（faq_direct_hit/clarify_strategy——本域消费）。

四层流水线（F56①→④，全服务端、前端零编排）：
  ①统一安检（注入扫描/禁用词索引/身份与数据域——字面规则，任一 ✗ 拦截出终局）
  ②知识装配（@ 前门直取＋六路匹配器并行查表共池——词级全扫全收集）
  ③意图裁决（置信度真实计算＝检索得分＋装配信号；D2 当前生效配置驱动路由）
  ④执行链分发（17 链闭世界枚举；检索/FAQ 秒回/图谱问答三链 P1-08b 链体填入）

B1：本文件不 import fastapi/starlette/DB——帧构造、安检模式、澄清有界循环、
候选截断、建议池都是纯语义；IO 归 store（PG）/service（编排）。
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

# ---------- 19 类事件帧（A1 合同值照抄——帧类型集不可改，A1 行为规则 2） ----------

FRAME_SESSION = "session"
FRAME_STAGE = "stage"
FRAME_SEC_CHECK = "sec_check"
FRAME_MATCH = "match"
FRAME_ASSEMBLY = "assembly"
FRAME_VERDICT = "verdict"
FRAME_NODE = "node"
FRAME_NODE_LINE = "node_line"
FRAME_TOKEN = "token"
FRAME_TOOL_CALL = "tool_call"
FRAME_CITATION = "citation"
FRAME_LINEAGE = "lineage"
FRAME_ANSWER = "answer"
FRAME_CLARIFY = "clarify"
FRAME_APPROVAL = "approval"
FRAME_NOTICE = "notice"
# 三保留帧（00 §6.2——全通道复用；api.chat 同名常量自此单源引用本模块）。
FRAME_DONE = "done"
FRAME_ERROR = "error"
FRAME_REPLAY_TRUNCATED = "replay_truncated"

FRAME_NAMES: tuple[str, ...] = (
    FRAME_SESSION, FRAME_STAGE, FRAME_SEC_CHECK, FRAME_MATCH, FRAME_ASSEMBLY,
    FRAME_VERDICT, FRAME_NODE, FRAME_NODE_LINE, FRAME_TOKEN, FRAME_TOOL_CALL,
    FRAME_CITATION, FRAME_LINEAGE, FRAME_ANSWER, FRAME_CLARIFY, FRAME_APPROVAL,
    FRAME_NOTICE, FRAME_DONE, FRAME_ERROR, FRAME_REPLAY_TRUNCATED,
)

# 00 §6.2 收场②合同话术原文（重连形态骨架判据——P0-08 登记不动）。
REPLAY_TRUNCATED_MESSAGE = "会话中断较久，中间漏了一段（超出缓冲窗口），请重新提问。"

# ---------- F56 合同常量（照抄 flows/common.jsx——不可改） ----------

SEC_CHECKS: tuple[str, ...] = ("注入扫描", "禁用词索引", "身份与数据域")
MATCHERS: tuple[str, ...] = (
    "FAQ 索引", "指标卡台账", "术语台账", "工具清单", "分析工作流", "报告索引",
)
CHAIN17: tuple[str, ...] = (
    "统一安检链", "状态机六站链", "指标卡直出链", "FAQ直出链", "工具执行链",
    "工作流执行链", "检索问答链", "图谱问答链", "汇报生成链", "大结果落盘链",
    "Action合同链", "外发拦截链", "澄清反问链", "口径消歧链", "新鲜度闸链",
    "行级权限链", "上下文注入链",
)

# 三链分派缝（票面：检索链/FAQ 秒回/图谱问答三链接口留缝，08b 填）——
# 三链在分派器占注册位（ChainHandler 缝），08a 缝内暂回未开通话术。
SEAM_CHAINS: tuple[str, ...] = ("检索问答链", "FAQ直出链", "图谱问答链")

# 澄清帧候选上限（F56：候选上限 4 支，超截断标「另有 N 支未列出」）。
CLARIFY_CANDIDATE_CAP = 4
OVERFLOW_NOTE_TEMPLATE = "候选 {total} 支，仅列前 {cap}——另有 {rest} 支未列出。"
# 澄清帧有界循环（F56：最多弹一次、两跳到终态防卡死；99 chat_run.clarify_count CHECK 0–1）。
CLARIFY_MAX_POPUPS = 1
# 口径两译类澄清恒带默认口径项（primary；CONTEXT「默认口径」——按修饰词最少的
# 基础口径出数并标注）。缺参反问类无默认项（缺的是用户事实，不是口径）。
DEFAULT_CALIBER_CHOICE_LABEL = "不选了，按默认口径出数并标注"

# ---------- 安检层（F56① 字面规则——注入特征/禁用词，零理解成本） ----------

# 注入特征字面模式库（A1 行为规则 4：与 promptfoo 红队用例同源——骨架期收录
# 「忽略指令」特征族；红队用例库沉淀回流随 C3/D3 批扩条）。
INJECTION_PATTERNS: tuple[str, ...] = (
    "忽略之前", "忽略你之前的", "无视之前", "ignore previous", "ignore all previous",
)
# 禁用词索引（W-F19 0 号位先于一切解析——设定书 §6 废弃口径登记；台账化随 C1 批）。
BANNED_TERMS: tuple[str, ...] = ("老完成率",)

# 拦截话术（照抄 A1Chat.jsx SCENARIOS——行为规则 4「话术照抄 SCENARIOS」）。
BAN_ANSWER_TEMPLATE = (
    "「{term}」是 2024 年已废弃的旧口径，平台不再按它出数。"
    "请改用「产量完成率」（Σ实际产油 ÷ Σ计划配产，Owner：开发室）。"
)
INJECTION_ANSWER_TEMPLATE = (
    "我注意到这句话包含「{feature}」——这类要求不会被执行，"
    "平台规则不可能被对话内容覆盖。"
)

# ---------- 话术常量（骨架期服务端组装——演示资产不进合同，运行时同语义产出） ----------

UNOPENED_CHAIN_TEMPLATE = "该能力暂未开通：「{chain}」尚未接线（骨架期——随后续票开放）。"
ANCHOR_MISS_TEMPLATE = (
    "@ 锚定「{token}」未命中任何注册表——取不到即落空拒答（@ 资产服务端直取，不猜）。"
)
ANCHOR_LOCK_NOTICE_TEMPLATE = "★ 已按你的选择锁定：{token}"
SUGGESTION_NOTICE_TEMPLATE = "这个词没有直接命中台账——已登记进建议池， Owner 复核后会补上。"

# 骨架期裁决标注（confidence 档位值＋页面标注后缀——A1 合同允许形状）。
FAQ_ROUTE_CONFIDENCE = "高（FAQ 精确命中——直出）"
GRAPH_ROUTE_CONFIDENCE = "高（图谱命中——确定性关系事实）"
CLARIFY_CONFIDENCE = "低（一词两译未消歧）"
CLARIFY_LOCKED_CONFIDENCE = "中（澄清锁定——直连执行）"

# 建议池晋升闸（F60：孤例不进池——独立问句频次 ≥2 才晋升；faQ 扫库 SCAN_MIN_FREQ 同源）。
SUGGESTION_PROMOTION_THRESHOLD = 2
# 会话料源读口上限（B3 扫库消费 A1 历史会话——最近 N 组问答；实施值可调）。
RECENT_QA_LIMIT = 50


# ---------- 错误族（00 §3.3 <域>_<语义>；api.errors 统一映射错误包） ----------


class ChatParamError(Exception):
    """400 族（question 为空且非重连/续跑模式等入参形状——A1 错误码草案）。"""

    def __init__(self, message: str, *, code: str = "chat_param_invalid") -> None:
        super().__init__(message)
        self.code = code


class ChatRunNotFoundError(Exception):
    """404 族（run/session 不存在或已过期——A1 错误码草案）。"""


class ChatRunStateError(Exception):
    """409 族（run 非 interrupt 挂起态：对已终态 resume/二次澄清/重入 clarify——
    A1 错误码草案「状态机约束（澄清帧最多弹一次）」）。"""


# ---------- SSE 事件（域内最小单位 {event, data}——信封渲染归 api 层） ----------


@dataclass(frozen=True, slots=True)
class SseEvent:
    """事件帧（CONTEXT「事件帧」）——00 §6.1 信封 `id/event/data` 的流内最小单位。"""

    event: str
    data: dict[str, Any]


# ---------- 装配层值对象（六路共池——F56②） ----------


@dataclass(frozen=True, slots=True)
class MetricFace:
    """指标台账面（semantics 读接口投影——chat 不触 sem_* 表，B5 边界规则）。"""

    metric_id: int
    name: str
    slot_name: str
    ambiguous: bool
    calibers: list[dict[str, Any]]
    default_caliber: str | None


@dataclass(frozen=True, slots=True)
class TermFace:
    """术语台账面（semantics 读接口投影——同上）。"""

    term_id: int
    term: str
    type: str
    def_text: str


@dataclass(frozen=True, slots=True)
class IndexHitFace:
    """报告索引命中面（kb 检索读面投影——chat 只见 callable，B9 同款）。

    text＝生成上下文用较长文本（P1-08b——snippet 80 字不够作答依据）。
    """

    fragment_id: str
    report_id: str
    report: str
    section: str | None
    snippet: str
    score: float
    leg: str  # vector | keyword（trigram 缝——P1-04 裁决）
    text: str = ""


@dataclass(frozen=True, slots=True)
class GraphHitFace:
    """图谱命中面（图存储检索读缝投影——P1-08b 图谱问答链候选源＋边出处；
    08a 票面「图谱〔08b 前落空〕」的缝——08b 组合根注入真 Neo4j 邻域检索）。"""

    entity: str
    relation: str
    evidence: str | None = None
    source_chunk_id: str | None = None  # 依据闸留存的原文片段 id（B5 边出处列）
    source_report_id: str | None = None  # 立边来源报告 id（B1 台账同域）


@dataclass(frozen=True, slots=True)
class FaqHitFace:
    """FAQ 索引命中面（faq.match_index 读口投影——98 §3.3 运行时读）。

    score＝相似问扩检命中分（match_index 精确命中＝确定性 1.0 由链体赋值；
    search_similar 扩检路携余弦分）。
    """

    entry_id: str
    question: str
    answer: str
    score: float = 0.0


@dataclass(frozen=True, slots=True)
class Candidate:
    """装配候选（六路共池降级为装配候选——F56②；澄清帧候选上限 4 支在此池取）。"""

    matcher: str
    name: str
    confidence: str  # high | low（match 帧 confidence 值域）
    kind: str  # metric | term | faq | report
    note: str | None = None


@dataclass(frozen=True, slots=True)
class LaneResult:
    """单路匹配结果（match 帧载荷源——六路逐条翻 ★/○/·）。"""

    matcher: str
    status: str  # hit | miss
    confidence: str | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class AssemblyResult:
    """装配块（assembly 帧载荷源：anchor_line/slots/terms/candidates/chains）。

    faq_hit/index_hits/graph_hits 为裁决置信度与三链链体的随行材料（wire 帧不带
    ——装配帧只发 candidates）。
    """

    anchor_line: str | None
    slots: str
    terms: list[str]
    candidates: list[Candidate]
    lanes: list[LaneResult]
    ambiguous_metric: MetricFace | None = None  # 口径两译澄清触发源（确定性触发）
    faq_hit: FaqHitFace | None = None  # FAQ 索引精确命中（秒回闸/检索链 FAQ 路消费）
    index_hits: list[IndexHitFace] = field(default_factory=list)  # 报告索引命中（置信度/检索链）
    graph_hits: list[GraphHitFace] = field(default_factory=list)  # 图谱缝命中（图谱问答链路由）


# ---------- 安检（字面规则——命中即拦截终局，A1 行为规则 4） ----------


def scan_injection(question: str) -> str | None:
    """注入特征扫描（字面模式库）——返回命中的特征词，未命中 None。"""
    folded = question.casefold()
    for pattern in INJECTION_PATTERNS:
        if pattern.casefold() in folded:
            return pattern
    return None


def check_banned(question: str) -> str | None:
    """禁用词索引（W-F19 0 号位先于一切解析）——返回命中禁用词，未命中 None。"""
    for term in BANNED_TERMS:
        if term in question:
            return term
    return None


def ban_answer_text(term: str) -> str:
    return BAN_ANSWER_TEMPLATE.format(term=term)


def injection_answer_text(feature: str) -> str:
    return INJECTION_ANSWER_TEMPLATE.format(feature=feature)


def unopened_chain_text(chain: str) -> str:
    return UNOPENED_CHAIN_TEMPLATE.format(chain=chain)


# ---------- @ 前门直取（S1 显式锚定——倾向≠直通；被 @ 的一路不过匹配器） ----------

_ANCHOR_TYPES = ("指标卡", "术语", "FAQ", "工具", "工作流", "报告")


def parse_anchor_token(token: str) -> tuple[str, str] | None:
    """@ token 解析（「类型·名称」结晶体——A1 端点 6 pickAsset 形状）。"""
    cleaned = token.removeprefix("@").strip()
    if "·" not in cleaned:
        return None
    asset_type, name = cleaned.split("·", 1)
    asset_type = asset_type.strip()
    name = name.strip()
    if asset_type not in _ANCHOR_TYPES or not name:
        return None
    return asset_type, name


def normalize_query(text: str) -> str:
    """装配比对归一化（NFKC 折叠＋casefold＋剥空白——faq.normalize 同构轻量版）。"""
    folded = unicodedata.normalize("NFKC", text or "").casefold()
    return re.sub(r"\s+", "", folded)


# ---------- 澄清帧（有界循环——最多弹一次、两跳到终态） ----------


@dataclass(frozen=True, slots=True)
class ClarifyChoice:
    """澄清选项（clarify 帧 choices 行——primary＝默认项）。"""

    value: str
    label: str
    primary: bool = False


@dataclass(frozen=True, slots=True)
class ClarifyFrame:
    """澄清帧载荷（interrupt 挂起——交出控制权等人）。"""

    frame_id: str
    question: str
    choices: list[ClarifyChoice]


def cap_choices(
    choices: list[ClarifyChoice], *, cap: int = CLARIFY_CANDIDATE_CAP
) -> tuple[list[ClarifyChoice], int]:
    """候选上限截断（F56：超 4 支截断——溢出数交调用方标「另有 N 支未列出」）。"""
    if len(choices) <= cap:
        return choices, 0
    return choices[:cap], len(choices) - cap


def overflow_note(total: int, rest: int, *, cap: int = CLARIFY_CANDIDATE_CAP) -> str:
    return OVERFLOW_NOTE_TEMPLATE.format(total=total, cap=cap, rest=rest)


def build_caliber_clarify(
    metric: MetricFace, *, frame_id: str
) -> ClarifyFrame | None:
    """口径两译澄清帧（骨架期确定性触发源——sem_metric.ambiguous＋calibers 同源消费，
    A1 澄清场景 verdict 示例「有效产量 → A 开井日历折算 or B 剔除检修？」同形）。

    choices＝各口径支＋默认口径项（primary，恒带——口径两译类合同值）；
    候选超 4 支截断（溢出数随 AssemblyResult.notice 通道提示）。
    """
    calibers = metric.calibers
    if not metric.ambiguous or len(calibers) < 2:
        return None
    names = [str(c.get("name", "")) for c in calibers]
    question = f"{metric.slot_name} → " + " or ".join(
        f"{c.get('key', '')} {name}".strip() for c, name in zip(calibers, names, strict=True)
    ) + "？"
    choices = [
        ClarifyChoice(
            value=f"{c.get('key', '')} · {name}".strip(" ·"),
            label=f"选 {c.get('key', '')}：{name}" + (
                f"（{c['desc']}）" if c.get("desc") else ""
            ),
        )
        for c, name in zip(calibers, names, strict=True)
        if name
    ]
    default_key = metric.default_caliber
    default = next((c for c in calibers if str(c.get("key", "")) == str(default_key)), None)
    if default is not None:
        choices.append(
            ClarifyChoice(
                value=f"默认口径 {default.get('key', '')}".strip(),
                label=DEFAULT_CALIBER_CHOICE_LABEL,
                primary=True,
            )
        )
    kept, _ = cap_choices(choices)
    return ClarifyFrame(frame_id=frame_id, question=question, choices=kept)


def caliber_choice_value(choice: str | None, frame: ClarifyFrame) -> str | None:
    """澄清回流通配：点选 value 或直接点默认项——归一为口径支 key（A/B）。"""
    if not choice:
        primary = next((c for c in frame.choices if c.primary), None)
        return primary.value if primary else None
    for c in frame.choices:
        if c.value == choice:
            return c.value
    return None


def caliber_name_from_value(value: str, metric: MetricFace) -> str:
    """口径选项值 → 口径支名（「A · 开井日历折算」/「默认口径 A」→「开井日历折算」）。"""
    for caliber in metric.calibers:
        key = str(caliber.get("key", ""))
        name = str(caliber.get("name", ""))
        if value == f"{key} · {name}".strip(" ·") or value == f"默认口径 {key}".strip():
            return name
    return value


# ---------- 建议池（F56 落空信号进建议池——F60 晋升闸：孤例不进池） ----------


@dataclass
class SuggestionSignal:
    """落空信号（matcher×归一问句去重攒频次；频次过晋升闸→进池待治理闭环消费）。"""

    matcher: str
    query: str
    freq: int = 1
    promoted: bool = False


class SuggestionPool:
    """落空信号收集面（F56②「落空信号进建议池」的骨架期承载）。

    治理闭环（攒频次→聚簇→提案→Owner 审→登记）的消费方＝C2 语义修订提案池——
    该域未上线，本池为进程内缓冲（孤例缓冲、过晋升闸晋升）；持久化与 sg- 发号
    权归 C2 落地批（差异登记于票面）。
    """

    def __init__(self, *, promotion_threshold: int = SUGGESTION_PROMOTION_THRESHOLD) -> None:
        self._signals: dict[tuple[str, str], SuggestionSignal] = {}
        self._promotion_threshold = promotion_threshold

    def record_miss(self, matcher: str, query: str) -> SuggestionSignal:
        key = (matcher, normalize_query(query))
        signal = self._signals.get(key)
        if signal is None:
            signal = SuggestionSignal(matcher=matcher, query=query)
            self._signals[key] = signal
            return signal
        signal.freq += 1
        if signal.freq >= self._promotion_threshold:
            signal.promoted = True
        return signal

    def promoted(self) -> list[SuggestionSignal]:
        """已进池信号（晋升闸过线——治理闭环输入）。"""
        return [s for s in self._signals.values() if s.promoted]

    def buffered(self) -> list[SuggestionSignal]:
        """孤例缓冲（未过闸——不进池，F60「孤例不进池防噪声淹没真问题」）。"""
        return [s for s in self._signals.values() if not s.promoted]


# ---------- 执行链分发（F56④——17 链闭世界枚举；三链 08b 填肉） ----------


@dataclass(frozen=True, slots=True)
class ChainContext:
    """链执行上下文（链内闸门代码值守的入参快照——链体消费）。"""

    run_id: str
    question: str
    actor_who: str
    assembly: AssemblyResult
    clarified_caliber: str | None = None  # 澄清锁定的口径支名（默认口径/人选）


# 链体缝（分派注册面——链内逐帧产出 node_line/token/citation/answer 等 SSE 事件，
# answer 帧必须最后出现；测试注桩同缝）。
ChainHandler = Callable[[ChainContext], AsyncIterator[SseEvent]]


class ChainDispatcher:
    """17 链分派器（闭世界枚举——超出即无效，F56④）。

    - 17 链全注册（枚举登记＝「未实现链话术逐链核对」的核对面）；
    - 三链（SEAM_CHAINS）已由 P1-08b 链体填入；未注册 handler 的链（其余 14 链）
      一律回未开通话术——不发明链行为。
    """

    def __init__(self) -> None:
        self._handlers: dict[str, ChainHandler] = {}

    def register(self, chain: str, handler: ChainHandler) -> None:
        if chain not in CHAIN17:
            raise ChatParamError(f"链不在 17 链枚举内：{chain}（闭世界——超出即无效）")
        self._handlers[chain] = handler

    def registered(self) -> tuple[str, ...]:
        return tuple(self._handlers)

    async def dispatch(self, chain: str, ctx: ChainContext) -> AsyncIterator[SseEvent]:
        if chain not in CHAIN17:
            raise ChatParamError(f"链不在 17 链枚举内：{chain}（闭世界——超出即无效）")
        handler = self._handlers.get(chain)
        if handler is not None:
            async for event in handler(ctx):
                yield event
            return
        yield SseEvent(
            FRAME_ANSWER,
            {"kind": "alert", "alert_type": "info", "text": unopened_chain_text(chain)},
        )


# ---------- 检索链语义件（P1-08b——D2 当前生效配置驱动的纯语义） ----------

# RRF 固定推荐值（D2 开放问题 8 裁决：加权参数 k/路权页面不暴露、不入合同——
# 真实实施先固定推荐值；R24 加权 RRF 锚）。
RRF_K = 60

# 来源分（compound 档 0.1 权重成分——实施批实施值，常量集中 Owner 可调；台账/
# 锚定/图谱＝确定性来源最高，检索文本次之）。
SOURCE_SCORES: dict[str, float] = {
    "anchor": 1.0, "ledger": 1.0, "faq": 0.9, "graph": 0.9,
    "vector": 0.6, "keyword": 0.6,
}

# 复合分权重（F34③ 合同值不可改：0.6×模型分＋0.3×检索基础分＋0.1×来源分）。
COMPOUND_WEIGHTS = (0.6, 0.3, 0.1)
# 多样性参数（F34③ 合同值：λ=0.7——MMR 防前几名全是同一份报告的近重复段落）。
MMR_LAMBDA = 0.7

# FAQ 路扩检（W-F35-4）：检索执行硬顶 5 轮（合同冻结——不无限空转）；每轮候选数
# 翻倍；过线相似度下限＝实施值（低于此分的相似问不进证据）。
FAQ_EXPAND_HARD_CAP = 5
FAQ_EXPAND_FLOOR = 0.5

# S6 资格裁决送生成上下文的上限（票面「4 支上限」——超出的截断标「另有 N 支未列出」）。
EVIDENCE_CAP = 4

# 生成上下文 token 帧切片长度（SSE 流式呈现节奏——实施值，常量可调）。
TOKEN_CHUNK_CHARS = 24

# 引用别名解析（[cN]——模型上下文低熵代号；服务端流式展开＋fail-closed 删除）。
# 引用别名解析（[cN]——模型上下文低熵代号；服务端流式展开＋fail-closed 删除；
# 容忍全角括号变体［cN］——中文模型输出的常见形态，展开/删除同权）。
REF_PATTERN = re.compile(r"[\[［](c\d+)[\]］]")

# 关系问句信号（图谱问答链路由——确定性信号：问句涉及关系词）。
RELATION_SIGNAL_RE = re.compile(r"受效|隶属|承载|作用于|关系|影响|连通|关联|哪些井")

# fail-closed 拦截话术（伪造/失锚引用——绝不带病出帧）。
UNANCHORED_CITATION_NOTE = "已拦截 {n} 条失锚/伪造引用（fail-closed）——绝不带病出帧。"
# D2 兜底 free 态合同标注（「未依据报告库」）。
FREE_ANSWER_TAG = "（未依据报告库）"


@dataclass(frozen=True, slots=True)
class Evidence:
    """检索证据（生成上下文与 citation 帧的单源行——ref 编号在送生成前分配）。"""

    ref: str
    kind: str  # 报告引用 | 台账条目 | 图谱（A1 citation kind 值域）
    label: str
    locator: dict[str, Any]
    snippet: str
    score: float
    source: str  # anchor | ledger | faq | graph | vector | keyword（SOURCE_SCORES 键）
    fragment_id: str | None = None
    report_id: str | None = None
    metric_slot: str | None = None  # 指标证据携槽位名——S7 权威源回读消费


def is_relation_question(question: str) -> bool:
    """关系问句信号（图谱问答链路由——受效/隶属/承载/作用于等关系词面）。"""
    return RELATION_SIGNAL_RE.search(question) is not None


def rrf_merge(
    vector: list[IndexHitFace], keyword: list[IndexHitFace], *, k: int = RRF_K
) -> list[tuple[IndexHitFace, float]]:
    """RRF 按名次融合（m6 Retriever.search 锚——1/(k+rank) 逐路累加，按融合分倒序）。"""
    fused: dict[str, float] = {}
    hits: dict[str, IndexHitFace] = {}
    for leg in (vector, keyword):
        for rank, hit in enumerate(leg, start=1):
            fused[hit.fragment_id] = fused.get(hit.fragment_id, 0.0) + 1.0 / (k + rank)
            hits.setdefault(hit.fragment_id, hit)
    return sorted(
        ((hits[fid], score) for fid, score in fused.items()),
        key=lambda pair: pair[1],
        reverse=True,
    )


def concat_merge(
    vector: list[IndexHitFace], keyword: list[IndexHitFace]
) -> list[tuple[IndexHitFace, float]]:
    """简单拼接（D2 merge=concat——「谁排前用谁」，向量路在前、关键词路在后）。"""
    return [(hit, hit.score) for hit in [*vector, *keyword]]


def compound_score(model_score: float, retrieval_score: float, source: str) -> float:
    """复合分＝0.6×模型分＋0.3×检索基础分＋0.1×来源分（F34③ 合同值，逐候选
    三成分拆账可解释——W-F34-1）。"""
    w_model, w_retrieval, w_source = COMPOUND_WEIGHTS
    return (
        w_model * model_score
        + w_retrieval * retrieval_score
        + w_source * SOURCE_SCORES.get(source, 0.5)
    )


def _text_trigrams(text: str) -> set[str]:
    folded = re.sub(r"\s+", "", text or "")
    if len(folded) < 3:
        return {folded} if folded else set()
    return {folded[i : i + 3] for i in range(len(folded) - 2)}


def snippet_similarity(a: str, b: str) -> float:
    """片段相似度（MMR 多样性用——trigram Jaccard，确定性零成本）。"""
    ta, tb = _text_trigrams(a), _text_trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def mmr_select(
    ranked: list[tuple[Any, float]], *, text_of: Callable[[Any], str], lam: float = MMR_LAMBDA
) -> list[tuple[Any, float]]:
    """MMR 多样性挑选（F34③ λ=0.7——λ×相关 −(1−λ)×与已选最大相似，贪心；
    text_of 取候选行的相似度文本）。"""
    if len(ranked) <= 1:
        return list(ranked)
    remaining = list(ranked)
    selected: list[tuple[Any, float]] = [remaining.pop(0)]
    while remaining:
        best_index, best_value = 0, float("-inf")
        for index, (item, score) in enumerate(remaining):
            diversity = max(
                (
                    snippet_similarity(text_of(item), text_of(done_item))
                    for done_item, _ in selected
                ),
                default=0.0,
            )
            value = lam * score - (1 - lam) * diversity
            if value > best_value:
                best_index, best_value = index, value
        selected.append(remaining.pop(best_index))
    return selected


def compute_confidence(
    *, anchored: bool, ledger_hit: bool, faq_hit: bool, best_index_score: float
) -> float:
    """置信度真实计算（P1-08b——检索得分＋装配信号的确定性合成）。

    基础＝报告索引最高证据分（0–1）；台账精确命中≥0.9（确定性先于相似度）；
    @ 前门直取≥0.95（A1「@倾向」信号）；FAQ 精确命中＝1.0（秒回闸直出）。
    """
    value = max(0.0, min(1.0, best_index_score))
    if ledger_hit:
        value = max(value, 0.9)
    if anchored:
        value = max(value, 0.95)
    if faq_hit:
        value = 1.0
    return value


def confidence_label(
    value: float, *, high: float, low: float, best_score: float,
    anchored: bool, ledger_hit: bool,
) -> str:
    """confidence 档位值＋来源标注后缀（A1 合同允许形状——档位阈值在服务端）。

    高 ≥high 直连执行；中 high–low 直连但页面标注；低 <low 必弹澄清帧（F56 拍板）。
    """
    if value >= high:
        if anchored:
            return "高（@ 倾向——锚定直取）"
        if ledger_hit:
            return "高（台账精确命中）"
        return f"高（检索证据分 {best_score:.2f}）"
    if value >= low:
        return f"中（检索证据分 {best_score:.2f}——直连执行）"
    return f"低（证据不足——低于低分线 {low:.2f}）"


def parse_refs(text: str) -> list[str]:
    """答案正文中的 [cN] 引用（按出现序去重——fail-closed 校验的输入面）。"""
    seen: list[str] = []
    for match in REF_PATTERN.finditer(text):
        if match.group(1) not in seen:
            seen.append(match.group(1))
    return seen


def strip_ref(text: str, ref: str) -> str:
    """从正文剥除某引用别名（fail-closed 删除——未知/失锚别名绝不外发）。"""
    return re.sub(rf"[\[［]{re.escape(ref)}[\]］]", "", text)


def rewrite_citations(
    text: str, evidence_by_ref: dict[str, Evidence], citation_format: str
) -> str:
    """引用呈现层切换（D2「引用格式切换语义」——生成链恒走 cN＋fail-closed，
    开关只切呈现）：page → 正文角标展开为 [label]；code → 保持 [cN] 编号呈现
    （真实出处收敛进引用清单）。"""
    if citation_format != "page":
        return text
    for ref, evidence in evidence_by_ref.items():
        text = re.sub(rf"[\[［]{re.escape(ref)}[\]］]", f"[{evidence.label}]", text)
    return text


def citation_wire(evidence: Evidence) -> dict[str, Any]:
    """citation 帧载荷（A1 冻结形状 {ref, kind, label, locator}）。"""
    return {
        "ref": evidence.ref,
        "kind": evidence.kind,
        "label": evidence.label,
        "locator": dict(evidence.locator),
    }


def token_chunks(text: str, *, size: int = TOKEN_CHUNK_CHARS) -> list[str]:
    """答案文本 → token 帧切片（SSE 流式呈现——gateway.complete 为整段应答，
    切片下发；真上游流式随 B6 流式接口批）。"""
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def build_candidate_clarify(
    candidates: list[Candidate], *, frame_id: str
) -> ClarifyFrame | None:
    """多候选澄清帧（S6 资格裁决——低置信且候选在场时弹；缺参反问类无默认项，
    缺的是用户意图聚焦）。候选超 4 支截断并注记。"""
    usable = [c for c in candidates if c.kind in ("metric", "term", "report", "faq", "graph")]
    if not usable:
        return None
    choices = [ClarifyChoice(value=c.name, label=f"{c.matcher}：{c.name}") for c in usable]
    kept, rest = cap_choices(choices)
    question = "这个问题命中了多个候选——你想问哪一个？"
    if rest:
        question += "（" + OVERFLOW_NOTE_TEMPLATE.format(
            total=len(choices), cap=CLARIFY_CANDIDATE_CAP, rest=rest
        ).replace(f"候选 {len(choices)} 支，仅列前 {CLARIFY_CANDIDATE_CAP}——", "") + "）"
    return ClarifyFrame(frame_id=frame_id, question=question, choices=kept)


# ---------- 域读缝（组合根注入——生产＝retrieval/semantics/faq/kb/gateway 公开读面） ----------


@dataclass(frozen=True, slots=True)
class RetrievalConfigFace:
    """D2 当前生效配置投影（六配置节全量——检索链全链消费；组合根从
    retrieval.ConfigSnapshot 投影，B9 同款运行期只见 callable）。"""

    order_levels: tuple[bool, bool, bool]  # 三级开关（L1 锚定/L2 词表/L3 双路）
    early_stop: bool
    semantic_top_k: int
    keyword_top_k: int
    merge: str  # rrf_rank | concat
    top_n: int
    rerank: str  # fast | llm | compound
    citation_format: str  # page | code
    fallback_strategy: str  # fixed | free
    fallback_text: str
    faq_direct_hit: bool
    refuse_threshold: float
    clarify_strategy: str
    confidence_high: float
    confidence_low: float
    faq_expand_rounds: int


@dataclass(frozen=True, slots=True)
class FragmentAnchorFace:
    """片段锚面（fail-closed 校验读缝——fragment_id 必须真实存在且属于命中报告）。"""

    fragment_id: str
    report_id: str
    report: str
    section: str | None


ConfigLoader = Callable[[], Awaitable[RetrievalConfigFace]]
MetricsLoader = Callable[[], Awaitable[list[MetricFace]]]
TermsLoader = Callable[[], Awaitable[list[TermFace]]]
FaqMatcher = Callable[[str], Awaitable[FaqHitFace | None]]
FaqSearcher = Callable[[str, int], Awaitable[list[FaqHitFace]]]
IndexSearcher = Callable[[str], Awaitable[list[IndexHitFace]]]
IndexSearcherDual = Callable[
    [str, int, int], Awaitable[tuple[list[IndexHitFace], list[IndexHitFace]]]
]
GraphSearcher = Callable[[str], Awaitable[list[GraphHitFace]]]
FragmentAnchorLoader = Callable[[str], Awaitable[FragmentAnchorFace | None]]


class Completer(Protocol):
    """LLM 出口缝（生产装配＝GatewayService——B6 唯一出口；测试注桩）。"""

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any: ...
