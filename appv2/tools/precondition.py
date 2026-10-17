"""tools.precondition —— 前置条件机（V2-34 票面任务 3——纯固定代码，LLM 无权判定）。

V1 闸语义移植（ADR-0005：禁用词/新鲜度窗/在册绑定态/外表越集/单井支持性）：
逐子问题过闸判四态——

- pass：干净放行；
- blocked_ask → ASK 挂起帧（真接 interrupt 挂起，非只返回字符串）：外表越集
  审批帧（ASK_EXTERNAL_TABLE_APPROVAL）＋无场景词阈值判断形的口径反问帧
  （ASK_CLARIFY——B5 裁决：用户已答才代选，否则反问）；
- blocked_refuse → 子问题如实拒答：禁用词（N1——带替代词）＋非法 caliber_key
  （合法口径校验）；
- note → 注记随行照常执行：单井支持性（照常发射全井计划）、水位窗（照实判定
  不造达标假象——票面任务 7）、外表已放行、双口径并列（血缘卡两支同载
  ——PROP-BOHAI-008=C）；在册未绑定自 V2-43 起＝换链回炉闸触发面（判定仍是
  note——runtime 前置条件节点拦下执行面，携拒因＋hint 回炉①澄清相位一次为界）。

铁律（ADR-0005）：LLM 出语义，代码出判定——本模块零 LLM（R1 红线：AST＋import
双证扫描见 tests/domains/test_v2_four_phase.py）。放行态落点（A2 裁决——P-051b
审查③注记改型随实现同步）：外表审批态放 ToolContext.approved_tables，
并随执行进引擎 approved_tables（data_query 传参——已批表放行续跑、批准后
重执行零二次挂审批；未批子集照挂），不重排计划。

输入：SubtaskInput（问题组子问题＋工具链定案）＋LedgerFacts（词典层 dump 的
结构化事实，由 ledger_facts(dump) 构建）＋放行名单/水位（调用方供给）。
零 I/O：纯函数判定（水位/放行态由 runtime 节点从状态与接线读出后传入）。
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from appv2.tools.schema import ASK_CLARIFY, ASK_EXTERNAL_TABLE_APPROVAL, AskFrame
from appv2.tools.table_scan import scan_unapproved_tables

# ---------- 四态枚举（R1 判定面——闭世界） ----------

STATE_PASS = "pass"
STATE_BLOCKED_ASK = "blocked_ask"
STATE_BLOCKED_REFUSE = "blocked_refuse"
STATE_NOTE = "note"
SUBTASK_STATES: frozenset[str] = frozenset(
    {STATE_PASS, STATE_BLOCKED_ASK, STATE_BLOCKED_REFUSE, STATE_NOTE}
)

# ---------- hit_rule 闭世界（2026-10-16 补（流水 56）裁②——judge() 单点产） ----------
# 命名以 specs/preconditions.md 判定序明文表位次为准逐字取名（八位）：
#   位 1 闸1 禁用词 → ban；位 2 闸1b 时间窗门 → fuzzy_window；位 3 闸2 外表越集
#   → ask；位 4 闸3 合法口径（＋前置台账闭世界）→ unregistered_metric；名归一闸
#   （F7——闸3 前置键归一）→ normalized_slot；位 5 闸4 在册绑定态 ＋ 位 6 闸4b
#   软失败域闸（同轨换链面）→ chain_switch；位 7 闸5 新鲜度窗 → freshness_window；
#   位 8 闸6 单井支持 → single_well。
# 非 allow 支（blocked_ask／blocked_refuse）必携闭世界一位——可解释性契约
# （specs/preconditions.md 行为 8「任一非 allow 必带 hit_rule」）：供 preconditions
# 单点取结构化判定位，不复制语义、不文案反推；allow 支（pass／note——注记并入
# 放行）＝HIT_RULE_NONE 空串（fail-closed：拒支漏填即成空串，双向对账可检）。
HIT_RULE_BAN = "ban"
HIT_RULE_FUZZY_WINDOW = "fuzzy_window"
HIT_RULE_ASK = "ask"
HIT_RULE_UNREGISTERED_METRIC = "unregistered_metric"
HIT_RULE_NORMALIZED_SLOT = "normalized_slot"
HIT_RULE_CHAIN_SWITCH = "chain_switch"
HIT_RULE_FRESHNESS_WINDOW = "freshness_window"
HIT_RULE_SINGLE_WELL = "single_well"
# allow 支形（pass／note——注记并入放行，无判定位命中）。
HIT_RULE_NONE = ""
# 八位闭世界（次序＝上列位次；非 allow 支的 hit_rule 必属本集）。
HIT_RULES: tuple[str, ...] = (
    HIT_RULE_BAN,
    HIT_RULE_FUZZY_WINDOW,
    HIT_RULE_ASK,
    HIT_RULE_UNREGISTERED_METRIC,
    HIT_RULE_NORMALIZED_SLOT,
    HIT_RULE_CHAIN_SWITCH,
    HIT_RULE_FRESHNESS_WINDOW,
    HIT_RULE_SINGLE_WELL,
)

# ---------- 闸词表（业务事实零发明——词面来源见各闸注） ----------

# 场景词（B5 裁决 2026-10-09：月报/正式/化验→确定性匹配口径支）。
SCENE_WORDS: tuple[str, ...] = ("月报", "正式", "化验")
# 场景词→口径支名同义词（口径支名承载「月度/正式」字样——月报↔月度同义映射）。
_SCENE_SYNONYMS: dict[str, tuple[str, ...]] = {"月报": ("月度",)}
# 阈值判断形词面（B5：无场景词＋阈值判断形→ASK 反问口径）。
THRESHOLD_MARKERS: tuple[str, ...] = (
    "是否", "超过", "超出", "达标", "达到", "高于", "低于", "大于", "小于", "突破",
)
# 单井点名词面（井号族 N-01/Z-16/W-111——题册井号形）。
_WELL_RE = re.compile(r"\b[A-Z]{1,3}-\d{1,4}\b")
# 禁用词替代提示（term value「禁用（替代：产量完成率）」段——替代词提取）。
_REPLACEMENT_RE = re.compile(r"替代：([^）]+)")

# 模糊时间词词表（V2-51 数-反1 形——CLARIFY_CONTRACT「模糊时间词（最近/近期/
# 前段时间类）＝窗双 null 发射」的确定性机读词面；词源＝合同逐字，零发明）。
FUZZY_TIME_MARKERS: tuple[str, ...] = ("最近", "近期", "前段时间")

# ---------- 改链建议（P-039 附 3——拒因模板逐字） ----------

# data 链被在册闸/绑定闸拦停时拒因尾部追加的 knowledge 备选提示——回炉重决策
# 路径可据此换链；blocked_refuse 直答路径不加（直答是终局——runtime 前置条件
# 节点在全部拦截直答收口时剥除本 hint）。
CHAIN_SWITCH_HINT = "——或改走 knowledge 链检索文档所载（本指标口径/数值可能载于文档）"

# 换链回炉触发面分型（V2-51）：""＝V2-43 绑定闸拒（在册未绑定 agg——既有轨道，
# 措辞零漂移）；"domain"＝软失败域闸（题眼井全外于数据链井闭世界——A-正8 形）。
# 两型同轨（chain_switch_trigger→回炉①一次为界→坚持同参＝直答终局），仅拒因/
# 通知措辞随型分叉。
CHAIN_SWITCH_KIND_UNBOUND = ""
CHAIN_SWITCH_KIND_DOMAIN = "domain"


# ---------- 输入/输出形 ----------


@dataclass(frozen=True, slots=True)
class SubtaskInput:
    """子问题判定输入（问题组子问题＋工具链定案的投影）。"""

    subtask_id: str
    question: str
    chain: str  # data|knowledge
    plan: Mapping[str, Any] | None = None
    retrieval_need: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class Verdict:
    """四态判定（step payload 断言面——blocked_ask 携真 AskFrame）。"""

    subtask_id: str
    state: str  # STATE_* 四值闭世界
    # 命中的判定位标识（HIT_RULES 八位闭世界——非 allow 支必携一位；allow 支
    # ＝HIT_RULE_NONE 空串）。2026-10-16 补（流水 56）裁②：judge() 单点产，
    # preconditions 直取结构化判定位（不复制语义、不文案反推）。
    hit_rule: str
    reason: str = ""
    notes: tuple[str, ...] = ()
    ask: AskFrame | None = None
    normalized_slot: str = ""  # F7 名归一：非空＝发射名经名归一闸命中该台账 slot
    # V2-43 换链回炉闸触发面：data 链＋在册（F7 归一后）＋绑定闸拒（未绑定 agg）
    # ＝True——runtime 前置条件节点据此拦下执行面，携拒因＋hint＋「换链提议」
    # 标记回炉①澄清相位（一次为界；其余闸此值恒 False，四态语义一字不动）。
    chain_switch_trigger: bool = False
    # 换链触发面分型（V2-51）：""＝V2-43 绑定闸拒（既有轨道措辞零漂移）；
    # "domain"＝软失败域闸（题眼井全外于数据链井闭世界——A-正8 形）。
    chain_switch_kind: str = CHAIN_SWITCH_KIND_UNBOUND
    # 模糊时间词词面门（V2-51 数-反1 形）：True＝问句携模糊时间词而计划窗非空
    # ——runtime 前置条件节点据此把 plan 窗双槽确定性改写为 None（引擎缺参
    # 反问兜底）；判定四态语义不变（仍是 note/pass——改写只在 runtime 消费）。
    fuzzy_window_rewrite: bool = False

    def as_payload(self) -> dict[str, Any]:
        return {
            "subtask_id": self.subtask_id,
            "state": self.state,
            "hit_rule": self.hit_rule,
            "reason": self.reason,
            "notes": list(self.notes),
            "ask": (
                {
                    "kind": self.ask.kind,
                    "prompt": self.ask.prompt,
                    "options": list(self.ask.options),
                    "detail": dict(self.ask.detail) if self.ask.detail else None,
                }
                if self.ask is not None
                else None
            ),
            "normalized_slot": self.normalized_slot,
            "chain_switch_trigger": self.chain_switch_trigger,
            "chain_switch_kind": self.chain_switch_kind,
            "fuzzy_window_rewrite": self.fuzzy_window_rewrite,
        }


# ---------- 词典层事实（dump dict → 结构化判定面） ----------


@dataclass(frozen=True, slots=True)
class MetricFact:
    """指标事实（绑定态/口径支——台账行投影）。"""

    slot: str
    name: str
    binding_state: str
    calibers: tuple[dict[str, Any], ...]
    default_caliber: str | None


@dataclass(frozen=True, slots=True)
class BannedFact:
    """禁用词事实（N1 闸——term status_key=禁用词 行投影）。"""

    term: str
    status: str
    replacement: str  # 替代词（台账「替代：X」注记；缺＝空串如实）


@dataclass(frozen=True, slots=True)
class LedgerFacts:
    """前置条件机判定事实（ledger_facts(dump) 产物）。"""

    metrics: Mapping[str, MetricFact]  # slot → 事实
    banned: tuple[BannedFact, ...]
    # 台账键闭世界（slot∪指标名∪别名键 → slot）——与引擎 metric_by_name 的
    # 两段命中（精确 slot/名 → 别名归一）同构的确定性解析面（C5 闸与绑定态
    # 闸共用的归一真源；键序优先级＝引擎同款：slot > 名 > 别名）。
    keys: Mapping[str, str]

    @property
    def banned_terms(self) -> tuple[str, ...]:
        return tuple(item.term for item in self.banned)


def ledger_facts(dump: Mapping[str, Any]) -> LedgerFacts:
    """词典层 dump（tools.ledger.dump_from_store 产物）→判定事实（零 I/O 纯投影）。"""
    metrics: dict[str, MetricFact] = {}
    for row in dump.get("metrics") or []:
        slot = str(row.get("slot") or "")
        if not slot:
            continue
        metrics[slot] = MetricFact(
            slot=slot,
            name=str(row.get("name") or ""),
            binding_state=str(row.get("binding_state") or ""),
            calibers=tuple(dict(c) for c in (row.get("calibers") or ())),
            default_caliber=row.get("default_caliber"),
        )
    # 键闭世界（slot/名/别名——引擎 metric_by_name 同构：精确两形→别名归一）。
    keys: dict[str, str] = {}
    for slot, fact in metrics.items():
        keys[slot] = slot
        if fact.name:
            keys.setdefault(fact.name, slot)
    for alias, canonical in (dump.get("aliases") or {}).items():
        target = keys.get(str(canonical))
        if target is not None:
            keys.setdefault(str(alias), target)
    banned: list[BannedFact] = []
    for row in dump.get("terms") or []:
        value = str(row.get("value") or "")
        term_name = str(row.get("term") or "")
        freshness = str(row.get("freshness") or "")
        if not bool(row.get("banned")):
            continue
        replacement_match = _REPLACEMENT_RE.search(value)
        banned.append(
            BannedFact(
                term=term_name,
                status=freshness or "已禁用",
                replacement=replacement_match.group(1).strip() if replacement_match else "",
            )
        )
    return LedgerFacts(metrics=metrics, banned=tuple(banned), keys=keys)


# ---------- F7 名归一闸（P-039 附 4——确定性定义） ----------


def normalize_metric_name(name: str) -> str:
    """附 4 名归一（确定性）：删除装饰符号（★☆※*＊等非字母数字汉字字符——
    空白除外，作 token 分隔承载）→去首尾空白→连续空白收 1→小写拉丁。

    「☆注采比 β」→「注采比 β」（装饰符删除、单空格保留）；「★产量完成率」→
    「产量完成率」。空白保留是附 4 真值对的承载面——token 集按空白切分，
    「注采比」的 token 集 {注采比} ⊆ {注采比, β} 才得以成立。
    """
    kept = "".join(ch for ch in name if ch.isalnum() or ch.isspace())
    return " ".join(kept.split()).lower()


def resolve_metric_slot(facts: LedgerFacts, raw_slot: str) -> str | None:
    """台账键解析单点（F7）：先精确命中（keys 映射——slot/名/别名，引擎
    metric_by_name 两段命中同构），未命中再名归一扫描（附 4 命中判定：
    normalize(查询) == normalize(slot 名/指标名)，或查询的 token 集 ⊆ 后者
    token 集）；全未命中＝None（blocked_refuse「不在台账全量」语义不变）。
    扫描序＝facts.metrics 装配序（确定性——首命中即断）。"""
    exact = facts.keys.get(raw_slot)
    if exact is not None:
        return exact
    query = normalize_metric_name(raw_slot)
    if not query:
        return None
    query_tokens = frozenset(query.split())
    for slot, metric in facts.metrics.items():
        for candidate in (slot, metric.name):
            normalized = normalize_metric_name(candidate)
            if not normalized:
                continue
            if query == normalized or query_tokens <= frozenset(normalized.split()):
                return slot
    return None


# ---------- 闸机（逐子问题过闸——判定序见各闸注释） ----------


def judge(
    subtask: SubtaskInput,
    facts: LedgerFacts,
    *,
    approved_tables: tuple[str, ...] = (),
    watermark: date | None = None,
    window_resolved: bool = False,
    data_wells: Collection[str] | None = None,
    entry_question: str = "",
) -> Verdict:
    """逐子问题过闸判四态（纯函数——零 LLM、零 I/O）。

    判定序：N1 禁用词 → 外表越集（放行态）→ 合法口径校验/三态触发（data 链）→
    在册绑定态 → 软失败域闸 → 新鲜度窗 → 单井支持性。blocked_* 即刻返回（首个
    命中闸定态）；其余闸命中累积为注记（全注记＝note 态，零注记＝pass）。

    V2-51 两新增面（判定四态语义不变——都随注记走）：
    - window_resolved＝用户已答窗（run 内有 clarify resume 留痕）——True 时词面
      门静默（用户答案锚定的窗不机械改判，零误伤）；
    - data_wells＝数据链井闭世界（agg.dim_well 井号集，调用方接线供给）——缺省
      None/空集＝域闸静默（不发明域语义）。

    2026-10-17 EB5b 新增面：
    - `entry_question`＝**入口问句原文**（`state.question`）——位 1 禁用词闸的
      旧叫法面**看题干原件**（子问题问句是模型产出、旧名归一在内：真机 EB3
      `run-d1de7df7` 把「老完成率是多少？」的子问题问句归一成「产量完成率是
      多少？」，词面命中面随之消失、拦停未触发）。缺省空串＝只看子问题问句
      与计划指标槽（既有行为零漂移）。
    """
    question = subtask.question
    plan = subtask.plan or {}
    notes: list[str] = []

    # —— 闸 1：N1 禁用词（两链同辖——语义红线不因链型豁免） ——
    # 豁免词面（P-051b 审查②等效补齐——is_ban_exempt，V1 DE-03 同构）：
    # 元问/引用形命中降级放行（注记随行照常执行；豁免 audit 行由 understand
    # 入口闸统一落账——本判定面零 I/O）。一次裸写/跨句拼接形照旧拦停；计划
    # 指标槽命中（非问句词面）不豁免。
    # 2026-10-17 EB5b：命中面＝子问题问句 ∪ 计划指标槽 ∪ **入口问句原文**（三面任一
    # 命中即判）；豁免面同片适用（命中哪一面就按哪一面判元问/引用形）。
    for item in facts.banned:
        if not item.term:
            continue
        hit_faces = [text for text in (question, entry_question) if item.term in text]
        if not hit_faces and item.term != str(plan.get("metric_slot") or ""):
            continue
        excused = [text for text in hit_faces if is_ban_exempt(text, item.term)]
        if hit_faces and len(excused) == len(hit_faces):
            notes.append(
                f"禁用词「{item.term}」命中但元问/引用形豁免放行——照常执行"
                f"（现行口径：{item.replacement or '见台账'}；豁免留痕见 run 审计）"
            )
            continue
        replacement = f"替代：{item.replacement}" if item.replacement else "见台账"
        return Verdict(
            subtask_id=subtask.subtask_id,
            state=STATE_BLOCKED_REFUSE,
            hit_rule=HIT_RULE_BAN,
            reason=(
                f"禁用词「{item.term}」已废弃——如实拒答，不代答废弃口径"
                f"（{replacement}）"
            ),
        )

    if subtask.chain != "data":
        if notes:
            return Verdict(
                subtask_id=subtask.subtask_id, state=STATE_NOTE,
                hit_rule=HIT_RULE_NONE,
                reason="；".join(notes), notes=tuple(notes),
            )
        # knowledge 链无取数闸面——检索链直接放行（检索引擎出处链与供给窗自守）。
        return Verdict(
            subtask_id=subtask.subtask_id, state=STATE_PASS, hit_rule=HIT_RULE_NONE
        )

    unbound_binding = False  # V2-43 换链回炉闸触发面（绑定闸在册未绑定置位）
    domain_mismatch = False  # V2-51 软失败域闸触发面（题眼井全外于井闭世界置位）
    fuzzy_rewrite = False  # V2-51 词面门改判标记（模糊时间词＋非空窗置位）
    metric_slot = str(plan.get("metric_slot") or "")

    # —— 闸 1b：模糊时间词词面门（数-反1 形——合同「窗双 null 发射」的确定性
    # 执行面）：问句携模糊时间词而计划窗任一槽非空＝模型默认窗直发违约形——
    # 标记改判（runtime 节点把窗双槽改写 None，引擎缺参反问兜底）。用户已答窗
    # （window_resolved）不改判；窗已双 null（合同面已跟）不改判。 ——
    if (
        not window_resolved
        and any(marker in question for marker in FUZZY_TIME_MARKERS)
        and (plan.get("window_start") is not None or plan.get("window_end") is not None)
    ):
        fuzzy_rewrite = True
        notes.append(
            "模糊时间词＋计划窗非空——确定性改判窗双 null（引擎缺参反问三选一兜底；"
            "「最近」类不解析不默认——词面门）"
        )
    # 键归一（引擎 metric_by_name 同构——slot/名/别名三形归到 slot；绑定态闸
    # 与口径闸因此对名形/别名形发射同样生效）。F7 名归一闸（P-039 附 4）：
    # 精确键未命中时按名归一扫描兜底——命中归一到该指标 slot 再进后续闸
    # （绑定/口径闸对 slot 判定）；全未命中维持 C5 拒（语义不变）。
    raw_slot = metric_slot
    resolved = resolve_metric_slot(facts, metric_slot)
    metric = facts.metrics.get(resolved) if resolved is not None else None
    normalized_slot = ""
    if metric is not None and facts.keys.get(metric_slot) is None:
        normalized_slot = metric.slot
        metric_slot = metric.slot  # 后续闸（绑定/口径）对归一 slot 判定
        notes.append(
            f"指标名「{raw_slot}」归一→台账 slot「{metric.slot}」（名归一闸命中）"
        )

    # —— 闸 2：外表越集（V2-44 申报/实扫双闸并存——越集后置确定性扫描） ——
    # 申报面现语义逐字保留（计划申报 external_tables 对放行名单——拦停措辞/
    # 帧形/resume 通道零改动；引擎 N7.4c 申报闸同零改动）；实扫兜底面
    # （table_scan 单源）不看申报——问句词面外表引用（别名＋schema 限定全解析）
    # 对审定开放集（放行名单＋agg 三表基座）执行前比对：未审定＝同形拦停挂
    # 审批（漏报也拦——P039BW run-afbe7aad 高危形根治）；计划未申报而实扫命中
    # ＝漏报捕获机读留痕（notes＋审批卡 detail 双落——审计可溯）。
    scan = scan_unapproved_tables(question, plan, approved_tables=approved_tables)
    unapproved = list(scan.unapproved)
    if unapproved:
        miss = list(scan.miss_declared)
        return Verdict(
            subtask_id=subtask.subtask_id,
            state=STATE_BLOCKED_ASK,
            hit_rule=HIT_RULE_ASK,
            reason=(
                f"计划引用外部表 {unapproved}——越集审批（模型与流程无权自批）"
                + (
                    f"；漏报捕获：{'、'.join(miss)} 未在计划申报——执行前实扫命中"
                    "（越集后置确定性闸，申报/实扫双闸并存）"
                    if miss
                    else ""
                )
            ),
            ask=AskFrame(
                kind=ASK_EXTERNAL_TABLE_APPROVAL,
                prompt=(
                    f"子问题 {subtask.subtask_id} 的取数计划引用外部表 "
                    f"{'、'.join(unapproved)}——是否批准越集查询？"
                ),
                options=("批准", "驳回"),
                detail={
                    "approval_id": f"precond-{subtask.subtask_id}",
                    "tables": unapproved,
                    "reason": "外表越集审批（前置条件机判定——放行态落 ToolContext）",
                    "impact": "批准后该表进放行名单（ToolContext），不重排计划",
                    # V2-44 审计面（additive——resume 通道只读 tables/approval_id/
                    # impact，零剥除负担）：表名集在场＋漏报捕获机读标记。
                    "declared_tables": list(scan.declared_tables),
                    "detected_tables": list(scan.detected_tables),
                    "miss_declared": miss,
                },
            ),
            notes=(
                (
                    f"漏报捕获：外表 {'、'.join(miss)} 未在计划申报——执行前实扫"
                    "命中（越集后置确定性闸，申报/实扫双闸并存）",
                )
                if miss
                else ()
            ),
        )
    external = [
        *scan.declared_tables,
        *(t for t in scan.detected_tables if t not in scan.declared_tables),
    ]
    if external:
        notes.append(
            f"外部表 {'、'.join(external)} 已放行（ToolContext 审批态）——不重排计划"
        )
        if scan.miss_declared:
            notes.append(
                f"漏报捕获：外表 {'、'.join(scan.miss_declared)} 未在计划申报——"
                "实扫命中已审定放行（照常执行，留痕不静默）"
            )

    # —— 闸 3：合法口径校验＋caliber_key 三态（B5 裁决） ——
    if metric is not None:
        calibers = metric.calibers
        caliber_keys = [str(c.get("key") or "") for c in calibers]
        caliber_key = str(plan.get("caliber_key") or "").strip()
        scene = next((w for w in SCENE_WORDS if w in question), "")
        if caliber_key and caliber_keys and caliber_key not in caliber_keys:
            return Verdict(
                subtask_id=subtask.subtask_id,
                state=STATE_BLOCKED_REFUSE,
                hit_rule=HIT_RULE_UNREGISTERED_METRIC,
                reason=(
                    f"caliber_key {caliber_key!r} 不在指标「{metric_slot}」口径支"
                    f" {caliber_keys}——合法口径校验拒（非法口径不代答）"
                ),
            )
        if scene:
            synonyms = (scene, *_SCENE_SYNONYMS.get(scene, ()))
            matched = next(
                (
                    c
                    for c in calibers
                    if any(word in str(c.get("name") or "") for word in synonyms)
                ),
                None,
            )
            if matched is not None:
                matched_key = str(matched.get("key") or "")
                if caliber_key and caliber_key != matched_key:
                    return Verdict(
                        subtask_id=subtask.subtask_id,
                        state=STATE_BLOCKED_REFUSE,
                        hit_rule=HIT_RULE_UNREGISTERED_METRIC,
                        reason=(
                            f"场景词「{scene}」确定性匹配口径支 {matched_key}"
                            f"（{matched.get('name')}），与 caliber_key {caliber_key!r}"
                            "矛盾——不代用户改选"
                        ),
                    )
                notes.append(
                    f"场景词「{scene}」落定口径支 {matched_key}"
                    f"（{matched.get('name')}）——确定性匹配（用户已答）"
                )
            else:
                notes.append(
                    f"场景词「{scene}」未命中口径支名——按默认口径出数"
                    f"（{metric.default_caliber or '台账默认'}）"
                )
        elif len(calibers) >= 2:
            if any(marker in question for marker in THRESHOLD_MARKERS):
                # 无场景词＋阈值判断形→ASK 反问口径（B5：用户已答才代选）。
                return Verdict(
                    subtask_id=subtask.subtask_id,
                    state=STATE_BLOCKED_ASK,
                    hit_rule=HIT_RULE_ASK,
                    reason=(
                        f"「{metric_slot}」有 {'、'.join(caliber_keys)} 双口径支"
                        "且问句为阈值判断形——口径反问"
                    ),
                    ask=AskFrame(
                        kind=ASK_CLARIFY,
                        prompt=f"「{metric_slot}」按哪一口径支判断？",
                        options=tuple(
                            f"{c.get('key')} {c.get('name')}" for c in calibers
                        ),
                    ),
                )
            notes.append(
                f"「{metric_slot}」双口径并列（{'、'.join(caliber_keys)}）——血缘卡"
                "两支同载（PROP-BOHAI-008=C 并存分场景），按默认口径出数"
            )

        # —— 闸 4：在册绑定态（引擎降级解释链权威——注记随行不代判） ——
        # V2-43（Owner 方案 A）：此闸命中＝换链回炉闸触发面——runtime 前置条件
        # 节点拦下执行面，携拒因＋hint＋「换链提议」标记回炉①澄清相位（一次为
        # 界；坚持 data 链同参再触发＝blocked_refuse 直答终局，不环）。判定面
        # 四态语义不变（仍是 note——触发只在 runtime 消费）。
        if metric.binding_state == "unbound":
            unbound_binding = True
            notes.append(
                f"「{metric_slot}」在册未绑定——agg 汇总层无承载列，引擎将走降级"
                "解释链（零数值不冒充）" + CHAIN_SWITCH_HINT
            )

        # —— 闸 4b：软失败域闸（V2-51 R4·A-正8 形——链路域↔题眼域一致性） ——
        # data 链题眼井全部不在数据链井闭世界（agg.dim_well——链路域真源）＝
        # 域错预判：该链成功出数也必不含题眼井（N 系井域答 W 系井问的「成功返回
        # 但域错」软失败面——Q14 帧证）。同轨 V2-43：note＋换链触发面（分型
        # domain），runtime 前置条件节点拦下执行面回炉①换 knowledge 链（一次
        # 为界）。零误伤面：单源域对（题眼井在册——数-界1 形）/混合域（部分在
        # 册）/无题眼井/闭世界未接线（None/空集）＝闸静默。V2-43 触发面已点亮时
        # 本闸不重复注记（同支同轨——触发布尔或聚，分型以先命中闸为准）。
        named_wells = sorted(set(_WELL_RE.findall(question)))
        if (
            not unbound_binding
            and data_wells
            and named_wells
            and all(well not in data_wells for well in named_wells)
        ):
            domain_mismatch = True
            notes.append(
                f"题眼井 {'、'.join(named_wells)} 不在数据链井闭世界"
                f"（{len(set(data_wells))} 口井域）——data 链成功出数也必不含题眼井"
                "（域错成功返回软失败面——软失败域闸）" + CHAIN_SWITCH_HINT
            )

    elif facts.metrics:
        # —— 闸 3 前置（C5，FX-13 闸力恢复——P-033 中途审查）：台账闭世界
        # 确定性校验（零 LLM）：data 链指标键 ∈ 台账键闭世界（slot∪指标名∪
        # 别名键——引擎 metric_by_name 两段命中的同构世界）——全未命中
        # ＝blocked_refuse（不在目录不代答）。候选集随问题组刷新后（FX-13
        # 「替换封堵」的语义弱化面），台账闭世界是确定性底闸；退化世界
        # （空台账＝注入缺缝）不硬拒全量，引擎台账校验仍权威（注记如实）。
        # 拒因尾部携改链 hint（P-039 附 3）——回炉重决策路径可据此换链；
        # 直答终局面由 runtime 前置条件节点剥除（附 3：直答是终局）。
        return Verdict(
            subtask_id=subtask.subtask_id,
            state=STATE_BLOCKED_REFUSE,
            hit_rule=HIT_RULE_UNREGISTERED_METRIC,
            reason=(
                f"指标 {metric_slot!r} 不在台账全量——确定性校验拒"
                "（不在目录不代答；台账闭世界校验）" + CHAIN_SWITCH_HINT
            ),
            normalized_slot=normalized_slot,
        )
    else:
        notes.append(
            f"指标 {metric_slot!r} 未在台账全量命中——引擎台账校验将判"
            "（校验拒拒因回喂）"
        )

    # —— 闸 5：新鲜度窗（水位真源照实判定——不造达标假象，票面任务 7） ——
    window_end = str(plan.get("window_end") or "").strip()
    if watermark is not None and window_end:
        try:
            end = date.fromisoformat(window_end[:10])
        except ValueError:
            end = None
        if end is not None and end > watermark:
            notes.append(
                f"窗上沿 {window_end[:10]} 晚于汇总层水位 {watermark.isoformat()}"
                "——引擎新鲜度闸将拦停/改绑并注记（照实判定）"
            )

    # —— 闸 6：单井支持性（QueryPlan 暂无井槽位——照常发射全井＋注记） ——
    if _WELL_RE.search(question):
        notes.append(
            "单井过滤未支持——照常发射全井计划，答案如实注记（读该井行），"
            "不作单井断言"
        )

    if notes:
        return Verdict(
            subtask_id=subtask.subtask_id, state=STATE_NOTE,
            hit_rule=HIT_RULE_NONE,
            reason="；".join(notes), notes=tuple(notes),
            normalized_slot=normalized_slot,
            chain_switch_trigger=unbound_binding or domain_mismatch,
            chain_switch_kind=(
                CHAIN_SWITCH_KIND_DOMAIN
                if domain_mismatch and not unbound_binding
                else CHAIN_SWITCH_KIND_UNBOUND
            ),
            fuzzy_window_rewrite=fuzzy_rewrite,
        )
    return Verdict(
        subtask_id=subtask.subtask_id, state=STATE_PASS, hit_rule=HIT_RULE_NONE,
        fuzzy_window_rewrite=fuzzy_rewrite,
    )


# ---------- N1 禁用词闸豁免词面（V2-52 附 C——唯一代码前置例外；P-051b 审查②等效补齐） ----------
# 豁免族＝V1 DE-03 既有 Owner 已批行为的等效承载（app/domains/chat/domain.py
# is_ban_exempt 同构移植——词面闭世界零 LLM；快车道词条卡豁免形随 P-051b 拆除，
# 豁免只改命中后的处置，禁用词闸本体零改动）。豁免放行必留 audit 行
# （agent_v2.ban_exempt——runtime/audit.py；V1 同位留痕 chat.ask.ban_exempt）。

# 引号对（闭世界枚举：「」/“”/‘’/'四形——命中词全部处于引号内＝引用形）。
BAN_EXEMPT_QUOTE_PAIRS: tuple[tuple[str, str], ...] = (
    ("「", "」"), ("“", "”"), ("‘", "’"), ("'", "'"),
)
# 元问句词面（闭世界常量枚举——词面与命中词**同句**共现＝在问旧称现状的合法元问题；
# FX-03/R1-07 收窄：同句以 BAN_EXEMPT_SENTENCE_BREAKS 分句判定，跨句拼接形不放行）。
META_QUESTION_MARKERS: tuple[str, ...] = ("旧称", "以前叫", "现在叫", "还叫", "原名")
# 元问形同句分句符（闭世界枚举——跨句拼接形回到拦停）。
BAN_EXEMPT_SENTENCE_BREAKS: tuple[str, ...] = ("。", "！", "？", "；", "…")


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
    """按 BAN_EXEMPT_SENTENCE_BREAKS 闭世界分句（元问形同句邻接的切句面——
    纯函数，不在安检位次上加解析面）。"""
    segments = [question]
    for sep in BAN_EXEMPT_SENTENCE_BREAKS:
        segments = [part for seg in segments for part in seg.split(sep)]
    return segments


def is_ban_exempt(question: str, term: str) -> bool:
    """禁用词命中豁免判定（V1 DE-03 窄豁免等效——元问句/引用形，任一形即降级
    放行；审查②等效补齐）。

    - 引用形：该禁用词在问句中的**每次出现**都处于引号内（一次裸写即不豁免——
      窄豁免不放松）；
    - 元问形：元问词面与命中词**同句**共现（按 BAN_EXEMPT_SENTENCE_BREAKS
      分句后逐句判定；跨句拼接形「老完成率的 3 月值是多少？顺便问下这词原名
      是啥」不放行，回到拦停）。

    其余命中照旧拦停；W-F19「先于一切解析」位次不变——本判定只对已命中的词
    做处置，不是新的前置解析面。豁免放行路 runtime 必留 audit 行
    （agent_v2.ban_exempt）。
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


def ban_exempt_notice_text(term: str, replacement: str) -> str:
    """豁免机读 notice 文案（禁用标注＋现行口径随行——替代词取台账
    「替代：X」注记，缺映射回落如实形不编造）。"""
    if replacement:
        return (
            f"禁用词豁免放行（元问/引用形）：「{term}」为已废弃旧口径，"
            f"现行口径为「{replacement}」"
        )
    return f"禁用词豁免放行（元问/引用形）：「{term}」已登记为禁用词"
