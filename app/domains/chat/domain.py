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
  ③意图裁决（P1-11 起＝petro-main 分类裁决（caller=chat.intent.verdict）＋
    确定性信号路由兜底——合同硬闸（FAQ 直出闸/口径两译澄清/低置信澄清）恒先
    行；confidence 来源双值 llm/deterministic 在 verdict.source 承载）
  ④执行链分发（17 链闭世界枚举；检索/FAQ 秒回/图谱问答三链 P1-08b 链体填入）

思考树叙事（P1-08c）：node 帧族沿本次运行实时路径逐帧流式推进（A1「节点渐进
出现」——node 帧的节点键序列是本次运行的实时路径·服务端真源）；node_line 保留
为节点内内容行（配置核对／模型第 N 次调用标注族——A1 帧 8）。

B1：本文件不 import fastapi/starlette/DB——帧构造、安检模式、澄清有界循环、
候选截断、建议池都是纯语义；IO 归 store（PG）/service（编排）。
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from typing import Any, Protocol

# 纯派生函数复用（P1F-02——状态标注串复用 C1 展示串规则单源，不重写；非运行期读缝）
from app.domains.semantics.domain import term_expiry

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
# 00 §6.2/A1 断线恢复收场③合同话术原文（生成已被取消——replay_truncated 帧收场；
# P1-08c：run 恢复重放补不出答案余量时的诚实收场话术）。
REPLAY_CANCELLED_MESSAGE = "回答生成已被取消——以上为重连前的内容，请重新提问。"

# ---------- 思考树节点（node 帧族——P1-08c 树叙事） ----------

# 节点状态四态（00 §5.3 节点步进形状——wait|process|finish|error，与 antd Steps
# 语义对齐；error 为协议登记态：本域设计内收场〔拦截/落空/兜底〕一律 finish＋
# note 明示，error 留给真实异常步）。
NODE_WAIT = "wait"
NODE_PROCESS = "process"
NODE_FINISH = "finish"
NODE_ERROR = "error"

# 全景树节点注册表（node 帧键与名——A1 帧 7「key 与全景树 41 节点键一致」）。
# 键/名照抄 learning-records/2026-09-27-业务执行全景树.md 总树＋prototype
# DecisionTree.jsx（41 节点版）；S 级键＝D2 瀑布级合同键（A1 行为规则 3——链内
# 节点行内容照抄各源；08b node_line 同键归位 node 帧）；GEN＝链内生成步实施键
# （41 树无生成节点——N8 答案组装由 answer 帧驱动，差异登记挂 Owner 复核）；
# N7 系六站＋三闸键＝M-06 问数链接入（全景树 N7.1–N7.6 主干＋N7.4a/b/c 分支闸，
# 键/名照抄全景树「状态机六站链」节）。
TREE_NODES: dict[str, str] = {
    "N1": "统一安检",
    "N2a": "注入拦截",
    "N2b": "禁用词替代",
    "N3": "轻装配",
    "N4": "装配块",
    "N5": "意图裁决",
    "N5a": "澄清帧",
    "N5b": "裁决核验",
    "N6": "链路分派",
    "N7.1": "意图识别",
    "N7.2": "语义检索",
    "N7.3": "SQL 生成",
    "N7.4": "执行前安检",
    "N7.4a": "新鲜度闸",
    "N7.4b": "行级权限",
    "N7.4c": "外表审批",
    "N7.5": "查询执行",
    "N7.6": "结果核验",
    "N13": "关系追溯",
    "N17": "检索问答",
    "N18": "预制问答",
    "S0": "身份四要素",
    "S1": "显式锚定",
    "S3": "词表四级",
    "S4": "双路召回",
    "S5": "图扩展",
    "S6": "资格裁决",
    "S7": "权威源回读",
    "GEN": "限定作答＋引用登记",
}

# 17 链 → 全景树执行节点（已接线四链；未接线链在 N5b 裁决核验即回退检索问答链
# ——P1F-01，不会进分派、不出未开通话术；分派器话术仅作链内注桩缺陷安全网）。
CHAIN_TREE_NODES: dict[str, str] = {
    "状态机六站链": "N7.1",
    "检索问答链": "N17",
    "FAQ直出链": "N18",
    "图谱问答链": "N13",
}


def node_frame(
    key: str,
    *,
    state: str,
    note: str | None = None,
    tag: str | None = None,
    skipped: bool = False,
) -> SseEvent:
    """node 帧（思考树节点逐帧流式推进——P1-08c 树叙事）。

    载荷＝A1 帧 7 合同字段 {key, name, tag?}∪00 §5.3 节点步进形状 {key, label,
    state, note, skipped}（additive 并集——A1 冻结字段保留、§5.3 形状承载状态
    推进；name/label 同值双承载）。skipped=true 恒配 state=wait（00 §5.3/§14-R6
    ①：流程级跳过不扩 state 枚举——D2 裁决推广形，早停跳过/开关关跳过/S5 未启用
    直通跳过同用此形，差异登记）。
    """
    name = TREE_NODES.get(key, key)
    data: dict[str, Any] = {"key": key, "name": name, "label": name, "state": state}
    if note is not None:
        data["note"] = note
    if tag is not None:
        data["tag"] = tag
    if skipped:
        data["skipped"] = True
    return SseEvent(FRAME_NODE, data)


def node_skip(key: str, note: str) -> SseEvent:
    """跳过级节点帧（state=wait＋skipped:true——00 §5.3 ①流程级跳过表达）。"""
    return node_frame(key, state=NODE_WAIT, note=note, skipped=True)

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
# M-06 起状态机六站链接入（问数链——N7.1–N7.6＋安检三闸），注册面扩为四链：
# 四链在分派器占注册位（ChainHandler 缝）；其余 13 链不注册＝
# 未接线（is_registered 查询面），N5b 接线核验（service 层，P1F-01）对未注册
# 裁决回退检索问答链——分派器「未开通」话术仅作已接线链内部注桩缺陷安全网。
SEAM_CHAINS: tuple[str, ...] = ("状态机六站链", "检索问答链", "FAQ直出链", "图谱问答链")

# 澄清帧候选上限（F56：候选上限 4 支，超截断标「另有 N 支未列出」）。
CLARIFY_CANDIDATE_CAP = 4
OVERFLOW_NOTE_TEMPLATE = "候选 {total} 支，仅列前 {cap}——另有 {rest} 支未列出。"
# 澄清帧有界循环（F56：最多弹一次、两跳到终态防卡死；99 chat_run.clarify_count CHECK 0–1）。
CLARIFY_MAX_POPUPS = 1
# 口径两译类澄清恒带默认口径项（primary；CONTEXT「默认口径」——按修饰词最少的
# 基础口径出数并标注）。缺参反问类无默认项（缺的是用户事实，不是口径）。
DEFAULT_CALIBER_CHOICE_LABEL = "不选了，按默认口径出数并标注"

# rewrite 澄清选项值（P1F-06——低分带 LLM 改写过闸、澄清额度在时弹帧的两支；
# value 用稳定判别值，优化问法本体走 pending_interrupt 携行不入 value）。
REWRITE_CHOICE_ACCEPT = "rewrite_accept"  # 按优化问法作答
REWRITE_CHOICE_KEEP = "rewrite_keep"      # 坚持原问法（选否/不选＝诚实兜底）

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

# —— 禁用词命中窄豁免（DE-03——E9：N1 误拦「问词本身」收口；只改命中后的处置，
# 禁用词表本体零改动；W-F19 位次不变——豁免判定发生在 check_banned 命中点之后，
# 不新增解析面）——
# 引号对（闭世界枚举：「」/“”/‘’/'四形——命中词全部处于引号内＝引用形）。
BAN_EXEMPT_QUOTE_PAIRS: tuple[tuple[str, str], ...] = (
    ("「", "」"), ("“", "”"), ("‘", "’"), ("'", "'"),
)
# 元问句词面（闭世界常量枚举——词面与命中词**同句**共现＝在问旧称现状的合法元问题；
# FX-03/R1-07 收窄：同句以 BAN_EXEMPT_SENTENCE_BREAKS 分句判定，跨句拼接形不放行）。
META_QUESTION_MARKERS: tuple[str, ...] = ("旧称", "以前叫", "现在叫", "还叫", "原名")
# 元问形同句分句符（闭世界枚举——FX-03/R1-07：元问词面须与命中词同句才豁免，
# 「老完成率的 3 月值是多少？顺便问下这词原名是啥」的跨句拼接形回到拦停）。
BAN_EXEMPT_SENTENCE_BREAKS: tuple[str, ...] = ("。", "！", "？", "；", "…")
# Owner 知情项（FX-03/R1-07 残余风险登记，交 Owner 拍板留档）：豁免放行路不做口径
# 两译复检——检索直接消费含禁用词的原问句，缓解仅随答提示带现行口径＋
# chat.ask.ban_exempt 审计留痕；引用形的构造滥用（引号内引用＋引号外真口径诉求，
# 如「按「老完成率」口径给我出数」）为已知行为（正例测试钉死）。放行＋随答提示为
# 当前档，强化复检归后续票。
# 豁免提示替代口径映射（闭世界——FX-02/R1-06：禁用词→现行口径。首条与拦截话术
# BAN_ANSWER_TEMPLATE 内嵌的「老完成率→产量完成率」同源取数（设定书 §6 废弃口径
# 登记），该话术为本票边界外未动、扩条时两处须同步。对账责任：设定书 §6 是登记制
# 真源——禁用词表扩条前必须先在 §6 登记并补本映射；缺映射的词回落 FALLBACK 形提示
# （不带现行口径句），不许向用户编造口径映射（硬纪律 7 业务事实零发明）。
BAN_EXEMPT_REPLACEMENTS: dict[str, str] = {"老完成率": "产量完成率"}
# 豁免随答提示文案（降级形态：放行＋答案尾部附一句——「问句涉及旧称谓 X，现行口径
# 为 Y」形）。有映射词渲染 TEMPLATE（{replacement} 取自 BAN_EXEMPT_REPLACEMENTS）；
# 无映射词回落 FALLBACK 形——只陈述「已登记为禁用词」这个闭世界事实，不带现行口径句。
BAN_EXEMPT_NOTICE_TEMPLATE = (
    "——提示：问句涉及旧称谓「{term}」，该口径 2024 年已废弃，现行口径为「{replacement}」。"
)
BAN_EXEMPT_NOTICE_FALLBACK_TEMPLATE = "——提示：问句涉及旧称谓「{term}」，该词已登记为禁用词。"

# ---------- 话术常量（骨架期服务端组装——演示资产不进合同，运行时同语义产出） ----------

# 「未开通」话术（P1F-01 起不再是主路径行为——未接线链在 N5b 裁决核验回退检索
# 问答链，分派不到这里；保留为已接线链内部注桩缺陷安全网，同 _run_chain 的
# answer=None 兜底分支族）。
UNOPENED_CHAIN_TEMPLATE = "该能力暂未开通：「{chain}」尚未接线（骨架期——随后续票开放）。"
ANCHOR_MISS_TEMPLATE = (
    "@ 锚定「{token}」未命中任何注册表——取不到即落空拒答（@ 资产服务端直取，不猜）。"
)
ANCHOR_LOCK_NOTICE_TEMPLATE = "★ 已按你的选择锁定：{token}"
SUGGESTION_NOTICE_TEMPLATE = "这个词没有直接命中台账——已登记进建议池， Owner 复核后会补上。"

# 拒答终态文案（P-004 修复拍④——resume 候选未选的收场话术独立成文案，不再借
# D2 fallback_text：该路径拿不到装配物（_suspend_clarify 不持久化装配），
# 「报告库里没有找到」对澄清收场不诚实——宁可不答、不瞎猜的如实表述）。
REFUSE_TERMINAL_TEXT = "已按您的选择拒答：未选定候选，不作答"

# 骨架期裁决标注（confidence 档位值＋页面标注后缀——A1 合同允许形状）。
FAQ_ROUTE_CONFIDENCE = "高（FAQ 精确命中——直出）"
GRAPH_ROUTE_CONFIDENCE = "高（图谱命中——确定性关系事实）"
CLARIFY_CONFIDENCE = "低（一词两译未消歧）"
CLARIFY_LOCKED_CONFIDENCE = "中（澄清锁定——直连执行）"

# 裁决来源双值（P1-11 LLM 意图裁决接线——骨架期「skeleton」标注退役）：
# llm＝petro-main 分类裁决生效；deterministic＝合同硬闸/确定性信号路由（含 LLM
# 失败/超时/解析坏兜底——不许问挂）。verdict 帧 source 键＝additive（A1 冻结
# 字段 chain/slots/confidence/need_clarify 全保留）。
VERDICT_SOURCE_LLM = "llm"
VERDICT_SOURCE_DETERMINISTIC = "deterministic"

# LLM 意图裁决预算（常量集中可调）：单次分类调用超时秒——超时即兜底，不许问挂。
INTENT_VERDICT_TIMEOUT_SECONDS = 8.0
# LLM#plan 数据意图精解析单问超时秒（L-02 票内定案：与 verdict 同值——超时即兜底
# 确定性快路，不许问挂）。
INTENT_PLAN_TIMEOUT_SECONDS = 8.0
# LLM 意图裁决 caller（D1 记账归因——与 chat.retrieval.* 同族点分形）。
CALLER_INTENT_VERDICT = "chat.intent.verdict"
# LLM#plan caller（L-02——D6：归因记账经 gateway 落列，同时是跨问熔断的数据源）。
CALLER_INTENT_PLAN = "chat.intent.plan"

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


class ChatSessionNotFoundError(Exception):
    """404 族（A1 端点 3 回放对象——会话不存在或非当前身份，不泄漏存在性）。"""


# ---------- SSE 事件（域内最小单位 {event, data}——信封渲染归 api 层） ----------


@dataclass(frozen=True, slots=True)
class SseEvent:
    """事件帧（CONTEXT「事件帧」）——00 §6.1 信封 `id/event/data` 的流内最小单位。"""

    event: str
    data: dict[str, Any]


# ---------- 装配层值对象（六路共池——F56②） ----------


@dataclass(frozen=True, slots=True)
class MetricFace:
    """指标台账面（semantics 读接口投影——chat 不触 sem_* 表，B5 边界规则）。

    status＝状态投影（C1 徽标列透传——装卡消费，P1F-02；sem_metric.status 为
    jsonb 数组故接受 list[str] 或 str 两形态——装卡经 metric_card_status_note
    归一，禁 str() 直透；组合根未携入时为空串＝不标注，不发明状态）。
    """

    metric_id: int
    name: str
    slot_name: str
    ambiguous: bool
    calibers: list[dict[str, Any]]
    default_caliber: str | None
    status: str | list[str] = ""


@dataclass(frozen=True, slots=True)
class TermFace:
    """术语台账面（semantics 读接口投影——同上）。

    status/status_key/expires_at＝状态三字段投影（C1 端点 2 同款——词条卡状态
    标注串的派生源，P1F-02；组合根未携入时全空＝不标注，不发明状态）。
    """

    term_id: int
    term: str
    type: str
    def_text: str
    status: str = ""
    status_key: str = ""
    expires_at: date | None = None


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
class TermCard:
    """词条卡（术语台账一等材料投影——P1F-02 方案 B：常驻装配材料，「要解释还
    是要数」由生成端判，意图判断不进路由层）。

    status_note＝状态标注串（C1 读端点同款派生口径——term_card_status_note 单源
    派生，如「有效（限作业区语境）」「2026-06-30（已届满）」「—（已禁用）」；
    台账未携状态字段时为空串＝不标注）。
    """

    term: str
    type: str
    def_text: str
    status_note: str = ""


@dataclass(frozen=True, slots=True)
class MetricCard:
    """指标卡（指标台账一等材料投影——同上；兜底诚实性文案消费）。

    calibers＝口径支行（原样投影）；status_note＝状态标注串（C1 徽标列透传）。
    """

    slot_name: str
    name: str
    calibers: list[dict[str, Any]] = field(default_factory=list)
    status_note: str = ""


def term_card_status_note(
    *, status: str, status_key: str, expires_at: date | None, today: date
) -> str:
    """词条卡状态标注串（P1F-02——C1 读端点同款派生口径，term_expiry 单源复用）。

    分支序（票面两例全覆盖，不重写 C1 展示串规则；实际优先序＝禁用词＞已届满
    ——term_expiry 禁用词先行、禁用词行恒返回 expired=False，P-004 修复拍⑤
    按实际序正 docstring）：
    - 三值全空 → 空串（台账未携状态字段——不发明标注）；
    - 禁用词 → 「—（已禁用）」（压过已届满——即便 expires_at 已过）；
    - 已届满（expires_at <= today，F60 到日即标）→ 「2026-06-30（已届满）」
      （日产液例）；
    - 其余状态展示串优先（躺井「有效（限作业区语境）」例——语境限定随卡带出），
      缺省回 term_expiry 展示串（「长期」族）。
    """
    if not (status or status_key or expires_at):
        return ""
    expired, expires_display = term_expiry(status_key, expires_at, today)
    if expired:
        return expires_display
    if status_key == "禁用词":
        return expires_display
    return status or expires_display


def metric_card_status_note(status: str | list[str]) -> str:
    """指标卡状态标注串（P-004 修复拍②——sem list 形态归一，审查③中）。

    sem_metric.status 为 jsonb 数组（['生效中']／['生效中','待联席裁决'] 双徽标
    形态）：list 以「／」join、str 原样——禁 str() 直透（产出「['生效中']」
    垃圾串直入兜底文案）；空值空串。
    """
    if isinstance(status, list):
        return "／".join(str(item) for item in status if str(item))
    return status


@dataclass(frozen=True, slots=True)
class AssemblyResult:
    """装配块（assembly 帧载荷源：anchor_line/slots/terms/candidates/chains）。

    faq_hit/index_hits/graph_hits 为裁决置信度与三链链体的随行材料（wire 帧
    不带——装配帧只发 candidates）；term_cards/metric_cards 为词条卡一等材料
    （P1F-02——生成层定义先行与兜底诚实性的随行材料，同样不进 wire 帧）。
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
    term_cards: list[TermCard] = field(default_factory=list)  # 词条卡（P1F-02——不进 wire）
    metric_cards: list[MetricCard] = field(default_factory=list)  # 指标卡（P1F-02——不进 wire）


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


def _inside_quotes(question: str, pos: int) -> bool:
    """pos 位置是否处于任一引号对内（平面判内外：开引号计数＞闭引号计数；
    对称引号按出现次数奇偶——BAN_EXEMPT_QUOTE_PAIRS 闭世界四形）。"""
    for open_q, close_q in BAN_EXEMPT_QUOTE_PAIRS:
        if open_q == close_q:
            if question.count(open_q, 0, pos) % 2 == 1:
                return True
        elif question.count(open_q, 0, pos) > question.count(close_q, 0, pos):
            return True
    return False


def _sentence_segments(question: str) -> list[str]:
    """按 BAN_EXEMPT_SENTENCE_BREAKS 闭世界分句（FX-03/R1-07——元问形同句邻接的
    切句面；纯函数，不在安检位次上加解析面）。"""
    segments = [question]
    for sep in BAN_EXEMPT_SENTENCE_BREAKS:
        segments = [part for seg in segments for part in seg.split(sep)]
    return segments


def is_ban_exempt(question: str, term: str) -> bool:
    """禁用词命中豁免判定（DE-03 窄豁免——元问句/引用形，任一形即降级放行）。

    - 引用形：该禁用词在问句中的**每次出现**都处于引号内（一次裸写即不豁免——
      窄豁免不放松）；
    - 元问形：元问词面与命中词**同句**共现（FX-03/R1-07 收窄——按
      BAN_EXEMPT_SENTENCE_BREAKS 分句后逐句判定；跨句拼接形
      「老完成率的 3 月值是多少？顺便问下这词原名是啥」不再放行，回到拦停）。

    Owner 知情项（R1-07 残余风险，豁免常量旁同文登记）：放行路不做口径两译复检，
    缓解仅随答提示带现行口径＋chat.ask.ban_exempt 审计留痕；引用形构造滥用为已知
    行为（正例测试钉死）。放行＋随答提示为当前档，强化复检归后续票。

    其余命中照旧拦停；W-F19「先于一切解析」位次不变——本判定只对 check_banned
    已命中的词做处置，不是新的前置解析面。
    """
    for segment in _sentence_segments(question):
        if term in segment and any(marker in segment for marker in META_QUESTION_MARKERS):
            return True
    start = question.find(term)
    if start < 0:
        return False  # 未命中不豁免（豁免判定只对已命中词）
    while start >= 0:
        if not _inside_quotes(question, start):
            return False
        start = question.find(term, start + len(term))
    return True


def ban_exempt_notice_text(term: str) -> str:
    """豁免随答提示文案（答案尾部附一句）——FX-02/R1-06 闭世界映射：有映射词带
    现行口径句（BAN_EXEMPT_REPLACEMENTS 取值）；无映射词回落 FALLBACK 形
    （不带现行口径句——词表扩条映射未补时不编造口径映射）。"""
    replacement = BAN_EXEMPT_REPLACEMENTS.get(term)
    if replacement is None:
        return BAN_EXEMPT_NOTICE_FALLBACK_TEMPLATE.format(term=term)
    return BAN_EXEMPT_NOTICE_TEMPLATE.format(term=term, replacement=replacement)


def with_ban_exempt_note(answer: dict[str, Any], note: str) -> dict[str, Any]:
    """答案尾部附豁免提示（纯函数——返回新 dict，不改 kind/citations；已附不重复）。"""
    merged = dict(answer)
    text = str(merged.get("text", ""))
    if note in text:
        return merged
    merged["text"] = f"{text}\n{note}" if text else note
    return merged


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
    """链执行上下文（链内闸门代码值守的入参快照——链体消费）。

    clarify_available/skip_rescore（P1F-06）：澄清额度与重评跳过旗标——额度由
    service 依 run.clarify_count 注入（rewrite 弹帧资格），skip_rescore 供 rewrite
    选否/不选回流续推（用户坚持原问法——低分带双重重评整段跳过，诚实兜底）。
    extable_decision/extable_approval_id（M-06 外表审批 interrupt 回流）：审批
    挂起的决策与留痕单号——链体恢复时整节点重跑（F7 节点幂等），N7.4c 以
    decision 判别批准续跑/驳回终局；首跑（无回流）双值 None。
    data_fallback_note（W-AUX③ 问数链降级接续）：非空＝本 ctx 是问数链出不了
    数后的接续路——检索链生成答案时把标注原文前置进正文（token 流与答案帧
    同文）；直接进检索链恒 None＝既有行为不变。
    """

    run_id: str
    question: str
    actor_who: str
    assembly: AssemblyResult
    clarified_caliber: str | None = None  # 澄清锁定的口径支名（默认口径/人选）
    clarify_available: bool = True  # 澄清额度在（clarify_count < 上限）——rewrite 弹帧资格
    skip_rescore: bool = False  # 用户坚持原问法——低分带双重重评跳过（rewrite 选否回流）
    extable_decision: str | None = None  # 审批回流决策 approve|reject（M-06——N7.4c 判据）
    extable_approval_id: str | None = None  # 审批留痕单号（挂起时生成、回流带回）
    data_fallback_note: str | None = None  # 问数链降级接续标注（W-AUX③——接续路消费）


# 链体缝（分派注册面——链内逐帧产出 node_line/token/citation/answer 等 SSE 事件，
# answer 帧必须最后出现；测试注桩同缝）。
ChainHandler = Callable[[ChainContext], AsyncIterator[SseEvent]]


class ChainDispatcher:
    """17 链分派器（闭世界枚举——超出即无效，F56④）。

    - 17 链清单＝闭世界枚举（dispatch 入口的域校验边界，也是「未实现链话术
      逐链核对」的核对底册）——不是注册面：注册面（register() 写入的 dict）
      ＝接线事实，仅接线链在册（见下条）；
    - 三链（SEAM_CHAINS）已由 P1-08b 链体填入；注册面（register() 写入的
      dict）＝接线事实，is_registered 是其查询面——N5b 接线核验（service 层，
      P1F-01）对未注册裁决先回退检索问答链，未注册链不进分派；
    - 未注册 handler 的链回「该能力暂未开通」话术——不再是面向用户的主路径
      行为，保留为已接线链内部注桩缺陷安全网（同 service._run_chain 的
      answer=None 兜底分支族——不发明链行为）。
    """

    def __init__(self) -> None:
        self._handlers: dict[str, ChainHandler] = {}

    def register(self, chain: str, handler: ChainHandler) -> None:
        if chain not in CHAIN17:
            raise ChatParamError(f"链不在 17 链枚举内：{chain}（闭世界——超出即无效）")
        self._handlers[chain] = handler

    def registered(self) -> tuple[str, ...]:
        return tuple(self._handlers)

    def is_registered(self, chain: str) -> bool:
        """链接线查询面（P1F-01）——注册表键即接线事实：register() 写入的 dict。"""
        return chain in self._handlers

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

# S6 资格裁决生成窗分池上限（D2 v0.4——2026-10-04 Owner 拍板分池案：原单池
# 「候选上限 4 支」废止——同池竞争时满分台账材料挤出真数据片段，评测复测窗
# 挤占组 D-诱5/15/8/12、A-正5 §6.2）：**报告类池**＝S4/S5 检索片段证据，上限
# 4 支（原单池值，语义收窄为报告类）；**台账类池**＝装配层一等材料满分档
# （词条卡/指标卡/@ 锚定直取/FAQ 精确命中并入），上限 2 支——两池互不占位，
# 各池内超出的截断并标「另有 N 支未列出」（chains._cap_evidence 单点实施）。
# 注：图谱问答链 N13 边证据上限同值沿用 EVIDENCE_CAP（图谱链非分池对象——
# v0.4 分池条文只改 S6 生成窗）。
EVIDENCE_CAP = 4
LEDGER_EVIDENCE_CAP = 2
# llm 档文档置信度配额（A9——窗口席位按来源置信度分配，替代固定均分压制）
DOC_CONF_FLOOR = 3.0    # 置信度无关线（0–10 制）——低于此线的来源不占生成窗席位
DOC_CONF_MAX_SEATS = 3  # 单来源席位居量——目标来源至多 3 席（其余来源竞争余席）
# 台账类材料来源集（Evidence.source 键域——chains.py 满分档三来源：faq＝FAQ
# 精确命中并入、anchor＝@ 前门直取、ledger＝S3 台账精确命中；其余 source
# （vector/keyword/graph…）＝报告类池）。
LEDGER_EVIDENCE_SOURCES = frozenset({"faq", "anchor", "ledger"})

# 低分带重评（P1F-06，评测报告 §4.10/§6 建议 5——refuse_threshold 对问法长度边际
# 敏感：同链同库原句 0.37 拒答 vs 换问法 0.71 全对）。RESCORE_BAND 语义＝
# RESCORE_BAND_FLOOR ≤ score < refuse_threshold：**下沿用 0.30 固定**（常量在此），
# **上沿随 D2 现值**（RetrievalConfigFace.refuse_threshold，本仓不复制配置值——
# 判定经 in_rescore_band 单源）。落带不直接兜底：先确定性放宽重评（纯代码），仍低
# 则 LLM 改写双句评分、给用户选择（rewrite 澄清帧）。
RESCORE_BAND_FLOOR = 0.30
# 放宽窗口倍率与封顶（重评路 topK＝max(semantic_top_k, keyword_top_k)×倍率，
# 封顶防失控——实施值，常量集中 Owner 可调）。
RESCORE_RELAX_FACTOR = 2
RESCORE_RELAX_MAX_TOPK = 64
# 额度已用完（N5 已弹过一次）时的自动作答标注（写死路径——不弹第二帧）。
RESCORED_ANSWER_TAG = "（已按优化问法检索）"


def in_rescore_band(score: float, refuse_threshold: float) -> bool:
    """低分带判定（P1F-06 单源）——RESCORE_BAND_FLOOR ≤ score < refuse_threshold。"""
    return RESCORE_BAND_FLOOR <= score < refuse_threshold

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


def confidence_label_llm(value: float, *, high: float, low: float) -> str:
    """LLM 裁决置信度的档位值＋标注（P1-11——档位阈值同 D2 confidence_thresholds）。

    值域夹逼 0–1 后按阈值判档；来源后缀恒「模型意图裁决」——与确定性信号路由
    的「检索证据分」族标注区分（confidence 来源双值在 verdict.source 键承载）。
    """
    value = max(0.0, min(1.0, value))
    if value >= high:
        return f"高（模型意图裁决 {value:.2f}）"
    if value >= low:
        return f"中（模型意图裁决 {value:.2f}——直连执行）"
    return f"低（模型意图裁决 {value:.2f}——低于低分线 {low:.2f}）"


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


def build_rewrite_clarify(optimized: str, *, frame_id: str) -> ClarifyFrame:
    """改写澄清帧（P1F-06——低分带 LLM 改写过闸且澄清额度在时弹，链内 S6 产出）。

    选项两支＝「按优化问法『…』作答」／「坚持原问法」；无 primary 默认项（缺的
    是用户取舍，不代选——同 candidates 惯例）：选是→优化句上下文走生成；选否/
    不选→诚实兜底（两跳到终态防卡死）。"""
    question = (
        "原问法在报告库里检索把握不足——要不要按优化问法再查一次？\n"
        f"优化问法：{optimized}"
    )
    choices = [
        ClarifyChoice(
            value=REWRITE_CHOICE_ACCEPT, label=f"按优化问法「{optimized}」作答",
        ),
        ClarifyChoice(value=REWRITE_CHOICE_KEEP, label="坚持原问法"),
    ]
    return ClarifyFrame(frame_id=frame_id, question=question, choices=choices)


def chain_clarify_signal(
    frame: ClarifyFrame, *, subtype: str, optimized_question: str
) -> SseEvent:
    """链内澄清挂起哨兵（P1F-06——链体弹澄清帧的域内事件）。

    service._run_chain 拦截本哨兵：转 _suspend_clarify 挂起＋clarify 帧 wire
    （subtype 透传）下发、流收束不发 done；哨兵本体（携 ClarifyFrame 对象与
    优化问句）不出域——wire 帧由拦截方按 A1 帧 14 冻结形状重建。"""
    return SseEvent(FRAME_CLARIFY, {
        "_chain_signal": True,
        "subtype": subtype,
        "frame": frame,
        "optimized_question": optimized_question,
    })


# ---------- 问数链语义件（M-06 状态机六站链——F7 三要素/F14 LIMIT 收口/F13 血缘五要素） ----------
#
# 站定义真源＝业务执行全景树 N7.1–N7.6（learning-records/2026-09-27-业务执行全景
# 树.md「状态机六站链」节）＋PRD F7 票 94 注记：站 1 意图识别＝复用 D2 slots 做
# 确定性校验（三要素齐不齐查表即判，零模型调用，缺参才反问——一次理解、多处复用）；
# 站 3 SQL 生成＝模板化（注册指标声明口径先行——自由生成只允许降级解释链并如实
# 标注，不冒充审定口径）；站 4 执行前安检＝三闸（N7.4a 新鲜度/N7.4b 行级权限/
# N7.4c 外表审批——F14）；血缘卡五要素＝F13 票 80/85（keys 合同值不可改）。
# 本节全是纯语义（B1——不咬框架不触 IO；IO 归 query_store/service 编排）。

# 排名方向（R1 修复——问句「最低/最小/最少」→升序、「最高/最大/最多」与未识别
# →降序保持现行为；白名单二值，执行侧按二值分派 ORDER BY，非字符串拼接）。
DIRECTION_ASC = "asc"
DIRECTION_DESC = "desc"


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """问数时间窗（半开区间 [start, end)——SQL 装配与血缘卡③共用的单源形状）。"""

    start: date
    end: date
    label: str  # 人话标签（「上个月」「近 30 天」——血缘卡③/答案注记消费）
    is_default: bool = False  # 无显式时间词的默认窗（答案与血缘卡必须标注「默认」）


@dataclass(frozen=True, slots=True)
class QueryPlan:
    """问数查询计划（N7.3 模板装配产物——执行器/血缘卡/审批比对共用的单源）。

    全字段由确定性解析产出（零模型调用）；window 为半开区间；external_tables
    ＝问句点名、选表命中集之外的外表（F14 外表引用比对触发源——N7.4c 消费）。
    """

    metric_slot: str  # 剥法纯名（C1 台账槽位——注册指标声明）
    metric_name: str  # 台账原名（含 ★☆ 与括注尾缀——血缘卡①照抄）
    measure_column: str  # agg 计量列（99 §2.12 沿源口径 §A.2）
    unit: str
    window: TimeWindow
    limit_requested: int | None  # 问句显式条数（None＝没写）
    limit_effective: int  # LIMIT 收口后值（F14——只封顶不抬底）
    ranking: bool  # 排名型（GROUP BY 井＋ORDER BY 合计——方向随 direction）｜明细型
    direction: str = DIRECTION_DESC  # 排名方向（asc/desc 白名单二值——R1：最低类问句升序）
    external_tables: tuple[str, ...] = ()  # 选表命中集之外的外表（越集比对触发源）
    actor: str = ""  # 行级注入 actor（两步缝第一步——executor 消费）


# F14 LIMIT 收口合同值（票 79/85：没写补默认 50、超 200 截到 200、只封顶不抬底）。
QUERY_DEFAULT_LIMIT = 50
QUERY_LIMIT_CAP = 200

# 注册指标声明 → agg 计量列绑定（99 §2.12：物理列名沿源口径——设定书 §A.2
# oil_output 吨/liquid_output 方/oil_pressure MPa；0014 迁移同注记）。
# 台账行未绑定计量列的指标（完成率/递减率等派生比值）不走模板——降级解释链。
MEASURE_COLUMNS: dict[str, tuple[str, str]] = {
    "日产油量": ("oil_output", "吨"),
    "日产液量": ("liquid_output", "方"),
    "油压": ("oil_pressure", "MPa"),
}

# agg 星型读模型三表（99 §2.12/D6 star_model 合同值——问数链 SELECT 唯一落点；
# join 结构即注册合同值：事实表组合 PK well_id+prod_date 挂两维 PK 连）。
STAR_TABLES: tuple[str, ...] = (
    "agg.fct_daily_metering", "agg.dim_well", "agg.dim_date",
)
STAR_SOURCE_NOTE = (
    "agg.fct_daily_metering（agg 星型读模型 · 即汇总层「日产计量表」"
    "——99 册 §2.12/D6 star_model，机器名＝A1 解释链②冻结）"
    "⋈ agg.dim_well（井维度·按井号）⋈ agg.dim_date（日期维度·按日期）"
)

# 外表别名 → 表名（F14 唯一 interrupt 触发场景＝erp_well_register 越集审批——
# A1 行为规则 9「D3 白名单演示」照抄；外表登记册随 D3 白名单批落，本表只收
# 合同演示样本，不新增业务事实）。
EXTERNAL_TABLE_ALIASES: dict[str, str] = {
    "erp_well_register": "erp_well_register",
    "井位台账": "erp_well_register",
}

# extable 审批卡与收场话术（A1 帧 15/answer kind=extable 合同形状——话术照抄
# prototype stateGates.jsx ExtableFlow 原文）。
EXTABLE_SCENE = "extable"
EXTABLE_TITLE = "外表引用审批"
EXTABLE_REASON_TEMPLATE = "查询引用选表命中集之外的外表：{tables}（执行前表引用比对命中——F14）"
EXTABLE_IMPACT = "批准＝链恢复续跑（只读执行，生产库未动）；驳回＝权限拒答零重试（不自动改写 SQL）"
EXTABLE_REJECT_NOTICE_TEMPLATE = (
    "不予执行，且不自动改写 SQL 重试。处理方式：请数据 Owner 先将 {table} "
    "登记进可用表白名单（安全与权限设置），再重新提问。"
)
EXTABLE_APPROVED_FOOTNOTE_TEMPLATE = (
    "审批留痕（单号 {approval_id}，可回溯）；只读执行，生产库未动。"
)

# 缺参反问（askback 时间窗三选一——A1 澄清场景「缺参反问类 choices＝补参候选，
# 照抄 askback 时间窗三选一，无默认项——缺的是用户事实，不是口径」；候选与问句
# 照抄 prototype blocked.jsx AskbackFlow 原文）。
MISSING_SUBTYPE = "missing"
ASKBACK_TIME_QUESTION = (
    "「最近」指哪个时间窗？① 近 3 天 ② 近 30 天 ③ 本月至今——选好后我按审定口径取数。"
)
ASKBACK_TIME_CHOICES: tuple[str, ...] = ("近 3 天", "近 30 天", "本月至今")

# —— 确定性数据问句词族（时间/条数两词表——L-02 提示词台账投影的导出面）——
# 词表常量是 DATA_QUESTION_RE 的拼装源（同源不造第二份时间/条数词源——L-02 票内
# 定案）；展示词表把模式形以样例展开（「近 N 天」→「近 3 天」等）。改一词两处同步
# 由回归测试钉死（tests/domains/chat/test_chat_plan_prompt_wiring.py 词表同源例）。
PLAN_TIME_WORDS: tuple[str, ...] = (
    "昨天", "前天", "今天", "本月", "这个月", "上月", "上个月", "今年", "去年", "最近",
)
PLAN_COUNT_WORDS: tuple[str, ...] = (
    "最高", "最低", "最大", "最小", "排名", "TOP", "top",
)
_PLAN_NEAR_N_PATTERN = r"近[0-9一二两三四五六七八九十]"
_PLAN_FRONT_N_PATTERN = r"前\s*[0-9一二两三四五六七八九十]"
_PLAN_MOUTH_N_PATTERN = r"[0-9一二两三四五六七八九十]+\s*口"
PLAN_TIME_WORDS_DISPLAY: tuple[str, ...] = (*PLAN_TIME_WORDS, "近3天", "近30天")
PLAN_COUNT_WORDS_DISPLAY: tuple[str, ...] = (*PLAN_COUNT_WORDS, "前 10", "三口", "TOP 3")

# 确定性数据问句信号（意图路由——指标台账命中＋时间/数量/排名词面才入六站链；
# 零模型调用。纯检索/释义问法不劫走——维持检索问答链主路径）。
DATA_QUESTION_RE = re.compile(
    "|".join((
        *PLAN_TIME_WORDS, _PLAN_NEAR_N_PATTERN,
        *PLAN_COUNT_WORDS, _PLAN_FRONT_N_PATTERN, _PLAN_MOUTH_N_PATTERN,
    ))
)
DATA_ROUTE_CONFIDENCE = "高（指标台账命中——数据问句走状态机六站链）"

_CN_NUMERALS: dict[str, int] = {
    "一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}
_RECENT_N_RE = re.compile(r"(?:最近|近)\s*([0-9]+|[一二两三四五六七八九十]+)\s*天")
_VAGUE_TIME_RE = re.compile(r"最近|近期|近日")
_LIMIT_TOP_RE = re.compile(r"(?:前|TOP|top)\s*([0-9]+|[一二两三四五六七八九十]+)")
_LIMIT_MOUTH_RE = re.compile(r"([0-9]+|[一二两三四五六七八九十]+)\s*口")
_RANKING_RE = re.compile(r"最高|最低|最大|最小|排名|TOP|top|前\s*[0-9一二两三四五六七八九十]")
_ASC_RANKING_RE = re.compile(r"最低|最小|最少")

# 血缘解释链五要素键（A1 lineage DTO——F13 票 80/85「五要素与『（权限注入）』
# 独立成行是合同值不可改」）。
LINEAGE_KEY_CALIBER = "① 口径"
LINEAGE_KEY_SOURCE = "② 来源表"
LINEAGE_KEY_FILTER = "③ 过滤条件"
LINEAGE_KEY_PERMISSION = "　└（权限注入）"
LINEAGE_KEY_WATERMARK = "④ 数据截至批次"
LINEAGE_KEY_CLOSING = "⑤ 收口注记"

# 行级权限预埋期注记（M-01 两步缝消费面——「无权的数据查不出来，不是打码」；
# 真分权只换谓词生产实现，注入点形状冻结）。
ROW_FILTER_PREEMBEDDED_NOTE = (
    "数据域＝全量——行级注入经 M-01 两步缝拼入 WHERE，不靠模型自觉"
    "（预埋期谓词恒空＝恒真；真分权只换谓词生产实现，注入点形状冻结）"
)

# 新鲜度闸 E2 语义（消费 M-05a 水位读面——承诺 T-1 判定在组合根经 E2
# freshness_judgment 单源计算随面携入；本域只渲染不重算）。
FRESHNESS_UNKNOWN_NOTE = "汇总层水位未回写——批次截至未知（如实标注，不造达标假象）"
FRESHNESS_REJECT_TEMPLATE = (
    "新鲜度闸拦停：汇总层数据水位＝{data_date}（{tag}）——查询窗「{label}」"
    "尚无已出数数据，不返回空数冒充。催办：源表催办走「考核与质量 → 问题单」。"
)
FRESHNESS_CLAMP_NOTE_TEMPLATE = (
    "比对：数据水位 {data_date} 早于查询窗上沿——已按最近可用日改绑出数"
    "（数据截至 {data_date}，{tag}；其后日期未出数，不冒充新数据）"
)
# DE-16 新鲜度闸配置开关（false 态跳过帧的 additive 注记——照 chunk_check additive
# 先例：帧内文字，不改帧枚举；键名＝database.yaml chat 段 freshness_gate_enabled，
# env 覆盖 FRESHNESS_GATE_ENABLED——infra.config ChatSettings 单源装载）。
FRESHNESS_GATE_OFF_NOTE = (
    "新鲜度闸已按配置关闭（freshness_gate_enabled=false）——跳过新鲜度比对，"
    "不拦停不改绑（N7.4b 行级权限、N7.4c 外表审批照走，零触碰）"
)

# 问数链降级接续（W-AUX③——主路出不了数自动接续检索问答链，消二选一漏答）：
# 答案帧正文前置标注（票面规定原文——如实声明非权威数值）与接续提示行单源。
DATA_CHAIN_FALLBACK_NOTE = "【数据库口径未能出数，以下为报告库检索结果（非权威数值）】"
DATA_CHAIN_FALLBACK_NOTICE = (
    "数据库口径未能出数——已自动接续检索问答链：以下为报告库检索结果（非权威数值），"
    "数值请以权威数据口径为准。"
)


def is_data_question(question: str) -> bool:
    """确定性数据问句信号（意图路由兜底面——时间/数量/排名词面＋指标命中才入链）。"""
    return DATA_QUESTION_RE.search(question) is not None


def resolve_measure(metric_slot: str) -> tuple[str, str] | None:
    """注册指标声明 → agg 计量列绑定（未绑定＝None——调用方走降级解释链）。"""
    return MEASURE_COLUMNS.get(metric_slot)


def _cn_int(raw: str) -> int | None:
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    return _CN_NUMERALS.get(raw)


def parse_row_limit(question: str) -> int | None:
    """问句显式条数解析（确定性——「前3/TOP3/三口」；没写返回 None＝默认 50）。

    只解析不收口：>200 的截断在 effective_limit（F14 收口注记要区分「没写」与
    「写了超限」两态）。
    """
    for pattern in (_LIMIT_TOP_RE, _LIMIT_MOUTH_RE):
        match = pattern.search(question)
        if match is not None:
            value = _cn_int(match.group(1))
            if value is not None and value > 0:
                return value
    return None


def effective_limit(requested: int | None) -> int:
    """LIMIT 收口（F14 合同值：没写补默认 50、超 200 截到 200、只封顶不抬底）。"""
    value = QUERY_DEFAULT_LIMIT if requested is None else requested
    return min(value, QUERY_LIMIT_CAP)


def is_ranking_question(question: str) -> bool:
    """排名型问句信号（「最高/TOP/前N」——模板走 GROUP BY 井合计排序）。"""
    return _RANKING_RE.search(question) is not None


def parse_ranking_direction(question: str) -> str:
    """排名方向解析（R1——「最低/最小/最少」词面→升序；其余含未识别→降序默认）。

    底向问句曾被倒序模板接客（「最低三井」实拿最高 TOP-N）——方向自此随问句
    单点产出进计划，展示 SQL 与执行 Core 同源消费。
    """
    if _ASC_RANKING_RE.search(question) is not None:
        return DIRECTION_ASC
    return DIRECTION_DESC


def parse_time_window(
    question: str, *, today: date
) -> tuple[str, TimeWindow | None]:
    """时间窗解析（确定性时间词函数——N7.1 三要素之时间槽位）。

    - ("ok", window)：显式时间词命中；
    - ("vague", None)：「最近/近期/近日」无量化——缺参反问（askback 时间窗
      三选一，不猜数）；
    - ("missing", None)：无时间词——调用方走默认窗（最近 30 天）并标注「默认」
      （照 prototype rowlevel「无显式时间走默认窗」语义；D2 查询策略配置面挂阶段 3）。
    """
    recent = _RECENT_N_RE.search(question)
    if recent is not None:
        value = _cn_int(recent.group(1))
        if value is not None and value > 0:
            return "ok", TimeWindow(
                start=today - timedelta(days=value), end=today,
                label=f"近 {value} 天",
            )
    if _VAGUE_TIME_RE.search(question) is not None:
        return "vague", None
    if "上个月" in question or "上月" in question:
        start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        end = today.replace(day=1)
        return "ok", TimeWindow(start, end, "上个月")
    if "本月" in question or "这个月" in question:
        start = today.replace(day=1)
        return "ok", TimeWindow(start, today, "本月至今")
    if "昨天" in question:
        day = today - timedelta(days=1)
        return "ok", TimeWindow(day, today, "昨天")
    if "前天" in question:
        day = today - timedelta(days=2)
        return "ok", TimeWindow(day, day + timedelta(days=1), "前天")
    if "今天" in question:
        return "ok", TimeWindow(today, today + timedelta(days=1), "今天")
    if "今年" in question:
        start = today.replace(month=1, day=1)
        return "ok", TimeWindow(start, today, "今年")
    if "去年" in question:
        start = today.replace(month=1, day=1).replace(year=today.year - 1)
        end = today.replace(month=1, day=1)
        return "ok", TimeWindow(start, end, "去年")
    return "missing", None


def default_time_window(*, today: date) -> TimeWindow:
    """默认时间窗（最近 30 天——无显式时间词时；is_default 驱动答案标注「默认」）。"""
    return TimeWindow(
        start=today - timedelta(days=30), end=today,
        label="最近 30 天（默认）", is_default=True,
    )


def resolve_askback_window(choice: str, *, today: date) -> TimeWindow | None:
    """askback 选项 → 时间窗（回流补参的确定性落点；未知选项 None）。"""
    if choice == "近 3 天":
        return TimeWindow(today - timedelta(days=3), today, "近 3 天")
    if choice == "近 30 天":
        return TimeWindow(today - timedelta(days=30), today, "近 30 天")
    if choice == "本月至今":
        return TimeWindow(today.replace(day=1), today, "本月至今")
    return None


def detect_external_tables(question: str) -> tuple[str, ...]:
    """问句点名的选表命中集之外外表（F14 外表引用比对触发源——确定性别名比对）。"""
    seen: list[str] = []
    for alias, table in EXTERNAL_TABLE_ALIASES.items():
        if alias.casefold() in question.casefold() and table not in seen:
            seen.append(table)
    return tuple(seen)


def build_query_plan(
    *,
    metric_slot: str,
    metric_name: str,
    question: str,
    window: TimeWindow,
    today: date,
    actor: str = "",
) -> QueryPlan:
    """N7.3 模板装配（前提＝resolve_measure 已命中＋时间窗已定——链体先核后调）。"""
    column, unit = MEASURE_COLUMNS[metric_slot]
    requested = parse_row_limit(question)
    return QueryPlan(
        metric_slot=metric_slot,
        metric_name=metric_name,
        measure_column=column,
        unit=unit,
        window=window,
        limit_requested=requested,
        limit_effective=effective_limit(requested),
        ranking=is_ranking_question(question),
        direction=parse_ranking_direction(question),
        external_tables=detect_external_tables(question),
        actor=actor,
    )


def clamp_plan_window(plan: QueryPlan, window: TimeWindow) -> QueryPlan:
    """新鲜度闸改绑后的计划（dataclasses.replace 同形——窗口单点替换）。"""
    return replace(plan, window=window)


def plan_to_wire(plan: QueryPlan) -> dict[str, Any]:
    """计划 → 挂起持久载荷（jsonb 安全形——日期 isoformat、元组转列表）。"""
    return {
        "metric_slot": plan.metric_slot,
        "metric_name": plan.metric_name,
        "measure_column": plan.measure_column,
        "unit": plan.unit,
        "window": {
            "start": plan.window.start.isoformat(),
            "end": plan.window.end.isoformat(),
            "label": plan.window.label,
            "is_default": plan.window.is_default,
        },
        "limit_requested": plan.limit_requested,
        "limit_effective": plan.limit_effective,
        "ranking": plan.ranking,
        "direction": plan.direction,
        "external_tables": list(plan.external_tables),
        "actor": plan.actor,
    }


def plan_from_wire(payload: dict[str, Any]) -> QueryPlan:
    """挂起持久载荷 → 计划（审批回流整节点重跑的上下文恢复）。"""
    window = payload["window"]
    return QueryPlan(
        metric_slot=str(payload["metric_slot"]),
        metric_name=str(payload["metric_name"]),
        measure_column=str(payload["measure_column"]),
        unit=str(payload["unit"]),
        window=TimeWindow(
            start=date.fromisoformat(str(window["start"])),
            end=date.fromisoformat(str(window["end"])),
            label=str(window["label"]),
            is_default=bool(window.get("is_default", False)),
        ),
        limit_requested=payload.get("limit_requested"),
        limit_effective=int(payload["limit_effective"]),
        ranking=bool(payload["ranking"]),
        direction=(
            direction
            if (direction := str(payload.get("direction") or DIRECTION_DESC))
            in (DIRECTION_ASC, DIRECTION_DESC)
            else DIRECTION_DESC  # 白名单外/存量载荷——clamp 回默认降序
        ),
        external_tables=tuple(payload.get("external_tables") or ()),
        actor=str(payload.get("actor") or ""),
    )


# ---------- 问数入口精解析影子观测件（L-01——方案 v2.1 应用线阶段 A） ----------
#
# 架构主张（方案-LLM问数演进-20261005 §0/§2.3 D2/D4，拍板记录 2026-10-05 第 2 条）：
# LLM#plan 只把自然语言问句翻译成受约束的「源槽位」意图草案（QueryPlanDraft），
# 计量列/单位/身份/LIMIT 收口/外表集等派生字段一律服务端单源重推导；SQL 仍由装配器
# 唯一产出。影子期（阶段 A）：产物只落日志不进任何生效路——真实 gateway 接线归
# L-02，生效路与 pinned_plan 归 L-05。本节全是纯语义（B1——不咬框架不触 IO）。

# Draft 准产白名单（五源槽位——LLM 只填问句里才有的信息；方案 §2.1 D2 槽位闭世界）。
DRAFT_ALLOWED_KEYS: tuple[str, ...] = (
    "metric_slot", "window", "limit_requested", "ranking", "direction",
)

# Draft 六禁区键 → 禁因（出现即拒，逐键报明——机制 1/2：防自由文本漂移、身份冒充、
# 直索引物理列与幻觉外表名；键不在准产白名单，与携带值无关）。
DRAFT_FORBIDDEN_REASONS: dict[str, str] = {
    "actor": "身份字段恒服务端注入（生产调用点恒传 ctx.actor_who）——Draft 携带即冒充身份通道",
    "metric_name": "台账原名由服务端经注册名重推导——LLM 不产展示名",
    "measure_column": "agg 计量列由 metric_slot 经 MEASURE_COLUMNS 单源重推导"
    "——禁止 LLM 直索引物理列",
    "unit": "单位随 MEASURE_COLUMNS 绑定重推导——LLM 不产",
    "limit_effective": "LIMIT 收口由服务端收口纯函数（50/200 只封顶不抬底）重推导"
    "——LLM 只产显式条数",
    "external_tables": "外表集唯一产源＝detect_external_tables 词面比对——LLM 提名即幻觉外表风险",
}


@dataclass(frozen=True, slots=True)
class QueryPlanDraft:
    """LLM#plan 源槽位意图草案（影子观测件——五源槽位白名单，六禁区键出现即拒）。

    构造统一走 from_payload（载荷校验＋禁区键即拒都在那条路）；window 半开区间
    [start, end) 与 TimeWindow 同形（label/is_default 是展示注记——比对算子记日志
    不判分歧）；limit_requested 是问句显式条数的 LLM 声明（None＝没写），收口值
    不得由 LLM 产出。影子期本草案只进 validator→比对→日志，零生效。
    """

    metric_slot: str
    window: TimeWindow
    limit_requested: int | None
    ranking: bool
    direction: str = DIRECTION_DESC

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> QueryPlanDraft:
        """LLM JSON 载荷 → 草案（字段白名单双向收窄——禁区键出现即拒，逐键报禁因）。"""
        if not isinstance(payload, Mapping):
            raise ValueError(
                f"Draft 载荷必须是 JSON 对象，得到 {type(payload).__name__}"
            )
        forbidden = [key for key in DRAFT_FORBIDDEN_REASONS if key in payload]
        if forbidden:
            detail = "；".join(
                f"{key}——{DRAFT_FORBIDDEN_REASONS[key]}" for key in forbidden
            )
            raise ValueError(
                f"Draft 携带禁区键（出现即拒——字段白名单双向收窄）：{detail}"
            )
        unknown = sorted(set(payload) - set(DRAFT_ALLOWED_KEYS))
        if unknown:
            raise ValueError(
                f"Draft 载荷含准产白名单外键 {unknown}"
                f"（闭世界——只收五源槽位 {list(DRAFT_ALLOWED_KEYS)}）"
            )
        slot = payload.get("metric_slot")
        if not isinstance(slot, str) or not slot.strip():
            raise ValueError(f"Draft metric_slot 必须是非空字符串，得到 {slot!r}")
        window = _draft_window_from_payload(payload.get("window"))
        requested = payload.get("limit_requested")
        if requested is not None:
            if isinstance(requested, bool) or not isinstance(requested, int):
                raise ValueError(
                    f"Draft limit_requested 必须是 [1, 200] 整数或 null，得到 {requested!r}"
                )
            if not 1 <= requested <= QUERY_LIMIT_CAP:
                raise ValueError(
                    f"Draft limit_requested 超出 [1, {QUERY_LIMIT_CAP}]：{requested}"
                    "（收口由服务端 effective_limit 做——LLM 只产显式条数）"
                )
        ranking = payload.get("ranking", False)
        if not isinstance(ranking, bool):
            raise ValueError(f"Draft ranking 必须是布尔值，得到 {ranking!r}")
        direction = payload.get("direction", DIRECTION_DESC)
        if direction not in (DIRECTION_ASC, DIRECTION_DESC):
            raise ValueError(
                f"Draft direction 必须是 {DIRECTION_ASC}/{DIRECTION_DESC} 二值，得到 {direction!r}"
            )
        return cls(
            metric_slot=slot.strip(),
            window=window,
            limit_requested=requested,
            ranking=ranking,
            direction=direction,
        )


def _draft_window_from_payload(raw: Any) -> TimeWindow:
    """Draft window 载荷校验（半开区间 [start, end)——start≥end 即拒）。"""
    if not isinstance(raw, Mapping):
        raise ValueError(f"Draft window 必须是含 start/end 的对象，得到 {raw!r}")
    extra = set(raw) - {"start", "end", "label", "is_default"}
    if extra:
        raise ValueError(
            f"Draft window 含白名单外键 {sorted(extra)}"
            "（只收 start/end/label/is_default）"
        )
    try:
        start = date.fromisoformat(str(raw.get("start")))
        end = date.fromisoformat(str(raw.get("end")))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Draft window start/end 必须是 ISO 日期（YYYY-MM-DD）：{exc}"
        ) from exc
    if start >= end:
        raise ValueError(
            f"Draft window 非半开区间（start={start} ≥ end={end}）"
            "——半开区间 [start, end) 要求 start < end"
        )
    label = raw.get("label", "")
    is_default = raw.get("is_default", False)
    if not isinstance(label, str):
        raise ValueError(f"Draft window label 必须是字符串，得到 {label!r}")
    if not isinstance(is_default, bool):
        raise ValueError(f"Draft window is_default 必须是布尔值，得到 {is_default!r}")
    return TimeWindow(start=start, end=end, label=label, is_default=is_default)


def validate_query_plan_draft(
    draft: QueryPlanDraft, *, question: str, actor: str = ""
) -> QueryPlan:
    """validator（L-01 交付物②——以 metric_slot 为唯一锚重推导，禁区字段零采信）。

    measure_column/unit←MEASURE_COLUMNS[metric_slot]（resolve_measure 同源——
    禁止第二份映射表）；metric_name←注册名（MEASURE_COLUMNS 键即注册名）；
    limit_effective←effective_limit 收口纯函数（50/200）；external_tables←
    detect_external_tables(问句) 词面比对；actor←函数参数注入（生产调用点恒传
    ctx.actor_who——影子期恒为测试替身值）。metric_slot 不在注册目录即拒
    （不在目录不代答——机制 3 台账绑定校验）。
    """
    bound = resolve_measure(draft.metric_slot)
    if bound is None:
        raise ValueError(
            f"metric_slot {draft.metric_slot!r} 不在 MEASURE_COLUMNS 注册目录"
            "——不在目录不代答（台账绑定校验）"
        )
    column, unit = bound
    return QueryPlan(
        metric_slot=draft.metric_slot,
        metric_name=draft.metric_slot,
        measure_column=column,
        unit=unit,
        window=draft.window,
        limit_requested=draft.limit_requested,
        limit_effective=effective_limit(draft.limit_requested),
        ranking=draft.ranking,
        direction=draft.direction,
        external_tables=detect_external_tables(question),
        actor=actor,
    )


# 双路比对三态（L-01 交付物③——一致／分歧（列明差异字段）／不可比（缺确定性解析））。
PLAN_COMPARE_MATCH = "一致"
PLAN_COMPARE_DIVERGE = "分歧"
PLAN_COMPARE_INCOMPARABLE = "不可比"

# 执行语义字段集（方案 §2.3 D3/评审意见 3——比对范围即此六字段；window.label/
# is_default 是展示注记，记差异日志不判分歧）。
PLAN_COMPARE_FIELDS: tuple[str, ...] = (
    "metric_slot", "window.start", "window.end", "limit_effective", "ranking", "direction",
)


@dataclass(frozen=True, slots=True)
class PlanComparison:
    """双路比对结果（LLM 解析 vs 确定性解析——分歧列明字段，注记不判分歧）。"""

    status: str  # PLAN_COMPARE_* 三态
    divergent_fields: tuple[str, ...] = ()  # 分歧字段名（PLAN_COMPARE_FIELDS 子集）
    notes: tuple[str, ...] = ()  # 记日志不判分歧的注记（window.label/is_default 差异）


def _plan_compare_values(plan: QueryPlan) -> dict[str, object]:
    """计划 → 执行语义字段值投影（PLAN_COMPARE_FIELDS 单源枚举驱动）。"""
    return {
        "metric_slot": plan.metric_slot,
        "window.start": plan.window.start,
        "window.end": plan.window.end,
        "limit_effective": plan.limit_effective,
        "ranking": plan.ranking,
        "direction": plan.direction,
    }


def compare_query_plans(
    draft_plan: QueryPlan | None, deterministic_plan: QueryPlan | None
) -> PlanComparison:
    """比对算子（L-01 交付物③——执行语义字段集逐字段等值；任一侧缺＝不可比）。"""
    if draft_plan is None or deterministic_plan is None:
        side = (
            "draft 侧（未产出或被 validator 拒）"
            if draft_plan is None
            else "确定性解析侧（快路缺件未产出计划）"
        )
        return PlanComparison(
            status=PLAN_COMPARE_INCOMPARABLE,
            notes=(f"{side}缺解析——不可比",),
        )
    draft_values = _plan_compare_values(draft_plan)
    det_values = _plan_compare_values(deterministic_plan)
    divergent = tuple(
        field for field in PLAN_COMPARE_FIELDS if draft_values[field] != det_values[field]
    )
    notes: list[str] = []
    if draft_plan.window.label != deterministic_plan.window.label:
        notes.append(
            f"window.label 差异（draft={draft_plan.window.label!r}，"
            f"确定性={deterministic_plan.window.label!r}）——记日志不判分歧"
        )
    if draft_plan.window.is_default != deterministic_plan.window.is_default:
        notes.append(
            f"window.is_default 差异（draft={draft_plan.window.is_default}，"
            f"确定性={deterministic_plan.window.is_default}）——记日志不判分歧"
        )
    if divergent:
        return PlanComparison(PLAN_COMPARE_DIVERGE, divergent, tuple(notes))
    return PlanComparison(PLAN_COMPARE_MATCH, (), tuple(notes))


# 触发原因标签（影子日志 trigger 字段值——触发谓词命中原因，对照方案 §2.2 慢路触发式）。
PLAN_TRIGGER_LEXICAL_GAP = "词面不齐"
PLAN_TRIGGER_PARSE_GAP = "解析缺件"


def data_route_signal(question: str, candidates: Iterable[Candidate]) -> bool:
    """确定性数据问句路由信号（M-06 单源——指标台账命中＋DATA_QUESTION_RE 词面）。

    从 service._verdict_signals 兜底路由抽出复用（不复制第二份）：service 兜底
    路由与 L-01 影子触发谓词同源消费。
    """
    return any(c.kind == "metric" for c in candidates) and is_data_question(question)


def plan_parse_trigger_reasons(
    *, question: str, metric_slot: str | None
) -> tuple[str, ...]:
    """快路缺件原因集（L-01 触发谓词核心——空集＝快路可解不触发）。

    - 词面不齐：DATA_QUESTION_RE（时间/数量/排名词面）不命中——is_data_question
      单源复用，不复制第二份正则；
    - 解析缺件：确定性解析缺 metric 锚（无指标候选，或候选槽位未绑定计量列——
      build_query_plan 前提不成立）。时间窗缺不在此列：「最近」类模糊窗走缺参
      反问（缺的是用户事实——LLM#plan 不代猜），无显式时间走默认窗。
    """
    reasons: list[str] = []
    if not is_data_question(question):
        reasons.append(PLAN_TRIGGER_LEXICAL_GAP)
    if metric_slot is None or resolve_measure(metric_slot) is None:
        reasons.append(PLAN_TRIGGER_PARSE_GAP)
    return tuple(reasons)


def should_trigger_plan_parse(
    *, verdict_chain: str | None, question: str, metric_slot: str | None
) -> bool:
    """L-01 触发谓词（交付物④）：verdict 判「状态机六站链」∧（词面不齐 ∨ 解析缺件）。

    链名＝CHAIN17 成员字面（闭世界 17 链——与 service 兜底路由同串）。入口裁决层
    （verdict dict 在场处）由 L-02 消费本谓词接线；链内影子观测点（裁决已判六站链、
    项恒真）直接用 plan_parse_trigger_reasons。
    """
    if verdict_chain != "状态机六站链":
        return False
    return bool(plan_parse_trigger_reasons(question=question, metric_slot=metric_slot))


# LLM#plan 调用缝类型（照 WaterlineLoader 注入缝同款形状——ChainDeps 可空 callable；
# 入参＝问句，出参＝schema 校验后的草案或 None（超时/坏 JSON/白名单外/validator 拒
# 的兜底归 drafter 实现——L-02 照 _verdict_llm 三重兜底模式填生产实现）。
PlanDrafter = Callable[[str], Awaitable[QueryPlanDraft | None]]


# ---------- L-02 提示词构建与影子接线——域内共享语义件（B1 纯语义，IO 归 service） ----------
#
# 方案 v2.1 应用线 L-02（tickets/phase3/L-02-提示词构建与影子接线.md）：构建器入参
# 投影、影子日志增强记录、触发双分桶口径、调用遥测与落盘缝类型在此单源；构建器纯
# 函数、生产 drafter、熔断器与 JSONL 落盘载体在 service.py（同址 INTENT_VERDICT
# 提示词先例），链内观测点消费在 chains.py。


@dataclass(frozen=True, slots=True)
class PlanPromptProjection:
    """LLM#plan 提示词·C1 台账投影（构建器入参②——三源票内定案零第二份）。

    可出数指标＝MEASURE_COLUMNS 键集（注册目录即投影，不造第二份可出数清单）；
    时间/条数词表＝DATA_QUESTION_RE 词族常量导出（PLAN_TIME_WORDS_DISPLAY/
    PLAN_COUNT_WORDS_DISPLAY——词表即正则拼装源，改一词两处同步由回归测试钉死）。
    """

    metrics: tuple[str, ...] = field(default_factory=lambda: tuple(MEASURE_COLUMNS))
    time_words: tuple[str, ...] = field(default_factory=lambda: PLAN_TIME_WORDS_DISPLAY)
    count_words: tuple[str, ...] = field(default_factory=lambda: PLAN_COUNT_WORDS_DISPLAY)


def default_plan_projection() -> PlanPromptProjection:
    """现行台账投影（常量每次现取——随注册目录与词族演进同步，无快照漂移）。"""
    return PlanPromptProjection()


# 触发双分桶观测口径（L-02 票内定案——L-03 影子报告直接消费；口径可由实跑后调、
# 偏差记回报）：过宽＝触发谓词 True 且比对三态「一致」（确定性解析本可解——LLM
# 调用本可省）；过窄＝触发谓词 False 且本问最终落降级解释链或缺参澄清（快路信号
# 判齐但快路没真正出数——谓词放过了该触发的问句）。
PLAN_BUCKET_OVERWIDE = "过宽：触发但快路可解"
PLAN_BUCKET_OVERNARROW = "过窄：该触发未触发"


@dataclass(frozen=True, slots=True)
class PlanCallTelemetry:
    """单次 LLM#plan 调用遥测（drafter 产出→链内影子观测消费——影子日志增强字段源）。

    token 值从 completer 返回对象属性读取，缺属性记 null——不因取数失败断流。
    """

    latency_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    breaker_tripped: bool = False  # 本次调用被熔断短路（影子行标 breaker=tripped）


@dataclass(frozen=True, slots=True)
class ShadowPlanRecord:
    """影子日志一行记录（L-01 四要素超集——只增不删向后兼容；LOGGER 行与 JSONL 双写共用）。"""

    run_id: str
    trigger: str  # 触发原因（"+" 连接——空＝谓词未触发的过窄桶观测行）
    draft_state: str  # 比对三态（一致/分歧/不可比）
    elapsed_ms: int  # 影子观测总耗时（drafter 调用＋validator＋比对）
    divergent: str = ""  # 分歧字段（"," 连接）
    note: str = ""  # 注记（label/is_default 差异＋validator 拒因＋桶说明等）
    question: str = ""  # 原问句（JSONL 消费——LOGGER 行不携）
    latency_ms: int | None = None  # LLM 调用本身延迟（裸替身/无调用＝null）
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    bucket: str | None = None  # 触发双分桶标记（PLAN_BUCKET_*——未入桶＝null）
    breaker_tripped: bool = False  # 熔断短路标记（影子行标 breaker=tripped）


def shadow_plan_log_line(record: ShadowPlanRecord) -> str:
    """影子行文本渲染（单行结构化——[shadow-plan] 前缀＋L-01 原六字段保留＋L-02 附尾）。"""
    latency = "-" if record.latency_ms is None else str(record.latency_ms)
    prompt_tokens = "-" if record.prompt_tokens is None else str(record.prompt_tokens)
    completion_tokens = (
        "-" if record.completion_tokens is None else str(record.completion_tokens)
    )
    return (
        f"[shadow-plan] run_id={record.run_id}"
        f" trigger={record.trigger or '-'}"
        f" draft_state={record.draft_state}"
        f" elapsed_ms={record.elapsed_ms}"
        f" divergent={record.divergent or '-'}"
        f" note={record.note or '-'}"
        f" latency_ms={latency}"
        f" prompt_tokens={prompt_tokens}"
        f" completion_tokens={completion_tokens}"
        f" bucket={record.bucket or '-'}"
        f" breaker={'tripped' if record.breaker_tripped else '-'}"
    )


def shadow_plan_json(record: ShadowPlanRecord, *, ts: str) -> dict[str, Any]:
    """JSONL 载荷（字段超集——L-03 影子报告直接消费；ts 由落盘侧经 infra.clock 注入）。"""
    return {
        "ts": ts,
        "run_id": record.run_id,
        "question": record.question,
        "trigger": record.trigger or None,
        "draft_state": record.draft_state,
        "elapsed_ms": record.elapsed_ms,
        "divergent": record.divergent or None,
        "note": record.note or None,
        "latency_ms": record.latency_ms,
        "prompt_tokens": record.prompt_tokens,
        "completion_tokens": record.completion_tokens,
        "bucket": record.bucket,
        "breaker": "tripped" if record.breaker_tripped else None,
    }


class ShadowLogSinkFace(Protocol):
    """影子日志落盘缝（生产＝service.ShadowLogSink JSONL＋logger 行双写；测试注桩）。"""

    def write(self, record: ShadowPlanRecord) -> None: ...


def render_plan_sql(plan: QueryPlan) -> str:
    """计划 → 展示 SQL（N7.3 node_line/审批卡核对用——执行走参数化 Core，
    展示串才用字面日期；两处同源自 plan 单点渲染）。"""
    measure = f"m.{plan.measure_column}"
    window_cond = (
        f"m.prod_date >= '{plan.window.start.isoformat()}' "
        f"AND m.prod_date < '{plan.window.end.isoformat()}'"
    )
    joins = (
        "FROM agg.fct_daily_metering m\n"
        "  JOIN agg.dim_well w ON w.well_id = m.well_id\n"
        "  JOIN agg.dim_date d ON d.date = m.prod_date"
    )
    if plan.ranking:
        order = "ASC" if plan.direction == DIRECTION_ASC else "DESC"  # 白名单二值分派
        total = f"SUM({measure}) AS {plan.metric_slot}合计（{plan.unit}）"
        return (
            f"SELECT w.well_id AS 井号, w.block_name AS 区块, {total}\n"
            f"{joins}\n"
            f"WHERE {window_cond}\n"
            "GROUP BY w.well_id, w.block_name\n"
            f"ORDER BY SUM({measure}) {order}\n"
            f"LIMIT {plan.limit_effective}"
        )
    return (
        f"SELECT m.well_id AS 井号, w.block_name AS 区块, m.prod_date AS 日期, "
        f"{measure} AS {plan.metric_slot}（{plan.unit}）\n"
        f"{joins}\n"
        f"WHERE {window_cond}\n"
        f"ORDER BY m.prod_date, m.well_id\n"
        f"LIMIT {plan.limit_effective}"
    )


def lineage_caliber_line(
    plan: QueryPlan, *, def_text: str, clarified_caliber: str | None = None
) -> str:
    """血缘卡①口径（注册指标声明先行——C1 台账 def/unit 照抄，口径随答案标注；
    R4：台账行无口径声明→占位句如实标注，不出「声明：，」空腔）。"""
    body = def_text.strip() if def_text else ""
    if not body:
        body = "台账未登记口径声明"
    line = f"{plan.metric_name}（单位：{plan.unit}）——指标台账注册声明：{body}，口径随答案标注"
    if clarified_caliber:
        line += f"（澄清锁定：{clarified_caliber}）"
    return line


def lineage_source_line() -> str:
    """血缘卡②来源表（照抄 A1 lineage DTO 示例句式——机器名冻结）。"""
    return STAR_SOURCE_NOTE


def lineage_filter_line(plan: QueryPlan) -> str:
    """血缘卡③过滤条件主体（只声明真实下推的过滤——时间窗；区块过滤随
    行级权限批，本票不虚列）。"""
    line = (
        f"时间＝{plan.window.label} "
        f"[{plan.window.start.isoformat()}, {plan.window.end.isoformat()})"
    )
    if plan.window.is_default:
        line += "（默认窗——问句无显式时间，已标注）"
    return line


def lineage_watermark_line(
    *, data_date: date | None, promise: str | None, tag: str | None, batch_id: str | None
) -> str:
    """血缘卡④数据截至批次（M-05a 水位读面消费——水位未回写如实缺行）。"""
    if data_date is None:
        return "—（水位未回写——如实缺行，不造达标假象）"
    body = f"汇总层水位 {data_date.isoformat()}（承诺 {promise or 'T-1'} · {tag or '—'}）"
    if batch_id:
        body = f"批次 {batch_id} · {body}"
    return body


def lineage_closing_line(plan: QueryPlan) -> str:
    """血缘卡⑤收口注记（F14 LIMIT 收口——区分「没写默认」与「显式/超限截断」）。"""
    line = (
        f"LIMIT {plan.limit_effective}"
        "——强制限量纪律：没写补默认 50、超 200 截到 200，只封顶不抬底"
    )
    if plan.limit_requested is not None and plan.limit_requested > QUERY_LIMIT_CAP:
        line += f"（问句条数 {plan.limit_requested}——已按上限截到 {QUERY_LIMIT_CAP}）"
    elif plan.limit_requested is not None:
        line += f"（问句显式条数 {plan.limit_requested}——只封顶不抬底）"
    return line


def build_askback_time_clarify(*, frame_id: str) -> ClarifyFrame:
    """缺参反问帧（askback 时间窗三选一照抄——无默认项：缺的是用户事实）。"""
    return ClarifyFrame(
        frame_id=frame_id,
        question=ASKBACK_TIME_QUESTION,
        choices=[ClarifyChoice(value=choice, label=choice) for choice in ASKBACK_TIME_CHOICES],
    )


def chain_approval_signal(payload: dict[str, Any]) -> SseEvent:
    """链内审批挂起哨兵（M-06——extable 触发；链体弹审批帧的域内事件）。

    service._run_chain 拦截本哨兵：approval 帧 wire（A1 帧 15 冻结形状）下发＋
    interrupt_approval 挂起（pending_approval_id 落列）、流收束不发 done；哨兵
    本体（携计划/选项全量）不出域——wire 只携 {approval_id, scene, title,
    reason, impact?, audit_hint?} 合同形状。
    """
    return SseEvent(FRAME_APPROVAL, {"_chain_signal": True, "payload": payload})


def build_extable_approval(
    plan: QueryPlan, *, run_id: str, approval_id: str
) -> dict[str, Any]:
    """extable 审批卡载荷（A1 帧 15 合同形状＋域内随行键——wire 前剥除面）。"""
    tables = "、".join(plan.external_tables)
    return {
        "approval_id": approval_id,
        "scene": EXTABLE_SCENE,
        "title": EXTABLE_TITLE,
        "reason": EXTABLE_REASON_TEMPLATE.format(tables=tables),
        "impact": EXTABLE_IMPACT,
        "audit_hint": f"run {run_id} · 外表 {tables}",
        # —— 域内随行键（挂起持久化消费；wire 剥除）——
        "_plan": plan_to_wire(plan),
        "_tables": list(plan.external_tables),
    }


def approval_wire(payload: dict[str, Any]) -> dict[str, Any]:
    """审批帧 wire 形（A1 帧 15 冻结形状——剥 `_` 前缀域内随行键）。"""
    return {k: v for k, v in payload.items() if not k.startswith("_")}


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
    rerank: str  # fast | llm（文档置信度＋置信度配额＋批量精排三段式） | compound
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


@dataclass(frozen=True, slots=True)
class WaterlineFace:
    """汇总层水位面（M-05a 水位读面投影——chat 不触 water_line 表，B3/B9）。

    tag/late_days 由组合根经 E2 freshness_judgment 单源计算随面携入（T-1 判定
    不在本域重算——新鲜度闸照 E2 语义渲染）；缺行时 loader 返回 None。
    """

    layer: str
    data_date: date
    promise: str
    tag: str
    late_days: int


@dataclass(frozen=True, slots=True)
class QueryResult:
    """问数执行结果（执行缝投影——行集＋行级注入回执；answer 表卡直接消费形）。

    columns＝(dataIndex, title) 序；rows＝dict 行（dataIndex 键）；batch_id＝
    结果行携带的批次水位（血缘卡④）；row_filter_predicates＝实际 AND 进语句的
    行级谓词数（0＝预埋恒真形状——N7.4b 注记依据）。
    """

    columns: tuple[tuple[str, str], ...]
    rows: list[dict[str, Any]]
    batch_id: str | None = None
    row_filter_predicates: int = 0


QueryExecutor = Callable[[QueryPlan], Awaitable[QueryResult]]
WaterlineLoader = Callable[[], Awaitable[WaterlineFace | None]]

# A1 端点 6 assets 读缝（P1-11 真接线——panel_view 投影的各域清单面；B9 同款
# 运行期只见 callable）：FAQ 服务中条目问题/工作流（名,状态）/报告 doc 清单。
FaqLister = Callable[[], Awaitable[list[str]]]
WorkflowLister = Callable[[], Awaitable[list[tuple[str, str]]]]
ReportLister = Callable[[], Awaitable[list[str]]]

# A1 端点 6 type 枚举（合同六类照抄——工具注册表未建投影为空）。
ASSET_TYPES: tuple[str, ...] = ("指标卡", "术语", "FAQ", "工具", "工作流", "报告")


@dataclass(frozen=True, slots=True)
class AssetItem:
    """@ 资产条目（A1 端点 6 合同形状 {type, name, token}——token＝「类型·名称」结晶体）。"""

    type: str
    name: str
    token: str


@dataclass(frozen=True, slots=True)
class SessionItem:
    """历史会话行（A1 端点 2 合同形状——updated_at 为 isoformat 秒级展示串）。"""

    id: str
    title: str
    group: str | None
    scenario_id: str | None
    updated_at: str


@dataclass(frozen=True, slots=True)
class SessionMessageItem:
    """会话消息行（A1 端点 3 合同形状——answer 与 SSE answer 帧同形，一份两处消费）。"""

    id: str
    role: str
    text: str
    run_id: str | None
    answer: dict[str, Any] | None


class Completer(Protocol):
    """LLM 出口缝（生产装配＝GatewayService——B6 唯一出口；测试注桩）。"""

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any: ...
