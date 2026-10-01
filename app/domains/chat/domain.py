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
  ③意图裁决（骨架期＝确定性路由；真实裁决唯一真源＝D2 模型，随 P1-08b 接线）
  ④执行链分发（17 链闭世界枚举；三链分派缝 08b 填，未实现链回未开通话术）

B1：本文件不 import fastapi/starlette/DB——帧构造、安检模式、澄清有界循环、
候选截断、建议池都是纯语义；IO 归 store（PG）/service（编排）。
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Awaitable, Callable
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
SKELETON_ROUTE_CONFIDENCE = "中（骨架期确定性路由——D2 模型裁决随 P1-08b 接线）"
CLARIFY_CONFIDENCE = "低（一词两译未消歧）"

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
    """报告索引命中面（kb 检索读面投影——chat 只见 callable，B9 同款）。"""

    fragment_id: str
    report_id: str
    report: str
    section: str | None
    snippet: str
    score: float
    leg: str  # vector | keyword（trigram 缝——P1-04 裁决）


@dataclass(frozen=True, slots=True)
class GraphHitFace:
    """图谱命中面（图存储检索读缝投影——票面「图谱〔08b 前落空〕」的候选源；
    08b 图谱问答链接线时由组合根注入真 Neo4j 检索——B9 同款只见 callable）。"""

    entity: str
    relation: str
    evidence: str | None = None


@dataclass(frozen=True, slots=True)
class FaqHitFace:
    """FAQ 索引命中面（faq.match_index 读口投影——98 §3.3 运行时读）。"""

    entry_id: str
    question: str
    answer: str


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
    """装配块（assembly 帧载荷源：anchor_line/slots/terms/candidates/chains）。"""

    anchor_line: str | None
    slots: str
    terms: list[str]
    candidates: list[Candidate]
    lanes: list[LaneResult]
    ambiguous_metric: MetricFace | None = None  # 口径两译澄清触发源（骨架期确定性触发）


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


# ---------- 执行链分发（F56④——17 链闭世界枚举；三链分派缝 08b 填） ----------


@dataclass(frozen=True, slots=True)
class ChainContext:
    """链执行上下文（链内闸门代码值守的入参快照——08b 链体消费）。"""

    run_id: str
    question: str
    actor_who: str
    assembly: AssemblyResult
    clarified_caliber: str | None = None  # 澄清锁定的口径支名（默认口径/人选）


@dataclass(frozen=True, slots=True)
class ChainOutcome:
    """链收场（answer 帧载荷——六种 kind DTO；notices＝answer 前置 notice 行）。"""

    answer: dict[str, Any]
    notices: list[str] = field(default_factory=list)


class ChainHandler(Protocol):
    """链体缝（分派缝注册面——08b 三链填肉入口；测试注桩同缝）。"""

    async def __call__(self, ctx: ChainContext) -> ChainOutcome: ...


class ChainDispatcher:
    """17 链分派器（闭世界枚举——超出即无效，F56④）。

    - 17 链全注册（枚举登记＝「未实现链话术逐链核对」的核对面）；
    - 三链分派缝（SEAM_CHAINS）占 ChainHandler 注册位——08a 缝内暂回未开通话术，
      08b 以 register() 填入链体；
    - 未注册 handler 的链（含其余 14 链）一律回未开通话术——骨架期不发明链行为。
    """

    def __init__(self) -> None:
        self._handlers: dict[str, ChainHandler] = {}

    def register(self, chain: str, handler: ChainHandler) -> None:
        if chain not in CHAIN17:
            raise ChatParamError(f"链不在 17 链枚举内：{chain}（闭世界——超出即无效）")
        self._handlers[chain] = handler

    def registered(self) -> tuple[str, ...]:
        return tuple(self._handlers)

    async def dispatch(self, chain: str, ctx: ChainContext) -> ChainOutcome:
        if chain not in CHAIN17:
            raise ChatParamError(f"链不在 17 链枚举内：{chain}（闭世界——超出即无效）")
        handler = self._handlers.get(chain)
        if handler is not None:
            return await handler(ctx)
        return ChainOutcome(
            answer={"kind": "alert", "alert_type": "info", "text": unopened_chain_text(chain)}
        )


# ---------- 域读缝（组合根注入——生产＝retrieval/semantics/faq/kb 公开读面） ----------


@dataclass(frozen=True, slots=True)
class QaBehaviorFace:
    """问答行为面（D2 qa_behavior 五字段投影——本域消费 faq_direct_hit/clarify_strategy；
    refuse_threshold/confidence_thresholds/faq_expand_rounds 随 08b 检索链消费）。"""

    faq_direct_hit: bool
    refuse_threshold: float
    clarify_strategy: str
    confidence_high: float
    confidence_low: float
    faq_expand_rounds: int


QaConfigLoader = Callable[[], Awaitable[QaBehaviorFace]]
MetricsLoader = Callable[[], Awaitable[list[MetricFace]]]
TermsLoader = Callable[[], Awaitable[list[TermFace]]]
FaqMatcher = Callable[[str], Awaitable[FaqHitFace | None]]
IndexSearcher = Callable[[str], Awaitable[list[IndexHitFace]]]
GraphSearcher = Callable[[str], Awaitable[list[GraphHitFace]]]
