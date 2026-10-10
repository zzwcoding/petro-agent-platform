"""tools.precondition —— 前置条件机（V2-34 票面任务 3——纯固定代码，LLM 无权判定）。

V1 闸语义移植（ADR-0005：禁用词/新鲜度窗/在册绑定态/外表越集/单井支持性）：
逐子问题过闸判四态——

- pass：干净放行；
- blocked_ask → ASK 挂起帧（真接 interrupt 挂起，非只返回字符串）：外表越集
  审批帧（ASK_EXTERNAL_TABLE_APPROVAL）＋无场景词阈值判断形的口径反问帧
  （ASK_CLARIFY——B5 裁决：用户已答才代选，否则反问）；
- blocked_refuse → 子问题如实拒答：禁用词（N1——带替代词）＋非法 caliber_key
  （合法口径校验）；
- note → 注记随行照常执行：单井支持性（照常发射全井计划）、在册未绑定（引擎
  降级解释链权威）、水位窗（照实判定不造达标假象——票面任务 7）、外表已放行、
  双口径并列（血缘卡两支同载——PROP-BOHAI-008=C）。

铁律（ADR-0005）：LLM 出语义，代码出判定——本模块零 LLM（R1 红线：AST＋import
双证扫描见 tests/domains/test_v2_four_phase.py）。放行态落点（A2 裁决）：外表
审批态放 ToolContext.approved_tables（不走引擎 approved_tables、不重排计划）。

输入：SubtaskInput（问题组子问题＋工具链定案）＋LedgerFacts（词典层 dump 的
结构化事实，由 ledger_facts(dump) 构建）＋放行名单/水位（调用方供给）。
零 I/O：纯函数判定（水位/放行态由 runtime 节点从状态与接线读出后传入）。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from appv2.tools.schema import ASK_CLARIFY, ASK_EXTERNAL_TABLE_APPROVAL, AskFrame

# ---------- 四态枚举（R1 判定面——闭世界） ----------

STATE_PASS = "pass"
STATE_BLOCKED_ASK = "blocked_ask"
STATE_BLOCKED_REFUSE = "blocked_refuse"
STATE_NOTE = "note"
SUBTASK_STATES: frozenset[str] = frozenset(
    {STATE_PASS, STATE_BLOCKED_ASK, STATE_BLOCKED_REFUSE, STATE_NOTE}
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

# ---------- 改链建议（P-039 附 3——拒因模板逐字） ----------

# data 链被在册闸/绑定闸拦停时拒因尾部追加的 knowledge 备选提示——回炉重决策
# 路径可据此换链；blocked_refuse 直答路径不加（直答是终局——runtime 前置条件
# 节点在全部拦截直答收口时剥除本 hint）。
CHAIN_SWITCH_HINT = "——或改走 knowledge 链检索文档所载（本指标口径/数值可能载于文档）"


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
    reason: str = ""
    notes: tuple[str, ...] = ()
    ask: AskFrame | None = None
    normalized_slot: str = ""  # F7 名归一：非空＝发射名经名归一闸命中该台账 slot

    def as_payload(self) -> dict[str, Any]:
        return {
            "subtask_id": self.subtask_id,
            "state": self.state,
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
        if not row.get("banned"):
            continue
        value = str(row.get("value") or "")
        replacement_match = _REPLACEMENT_RE.search(value)
        banned.append(
            BannedFact(
                term=str(row.get("term") or ""),
                status=str(row.get("freshness") or "已禁用"),
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
) -> Verdict:
    """逐子问题过闸判四态（纯函数——零 LLM、零 I/O）。

    判定序：N1 禁用词 → 外表越集（放行态）→ 合法口径校验/三态触发（data 链）→
    在册绑定态 → 新鲜度窗 → 单井支持性。blocked_* 即刻返回（首个命中闸定态）；
    其余闸命中累积为注记（全注记＝note 态，零注记＝pass）。
    """
    question = subtask.question
    plan = subtask.plan or {}

    # —— 闸 1：N1 禁用词（两链同辖——语义红线不因链型豁免） ——
    for item in facts.banned:
        if item.term and (item.term in question or item.term == str(plan.get("metric_slot") or "")):
            replacement = f"替代：{item.replacement}" if item.replacement else "见台账"
            return Verdict(
                subtask_id=subtask.subtask_id,
                state=STATE_BLOCKED_REFUSE,
                reason=(
                    f"禁用词「{item.term}」已废弃——如实拒答，不代答废弃口径"
                    f"（{replacement}）"
                ),
            )

    if subtask.chain != "data":
        # knowledge 链无取数闸面——检索链直接放行（检索引擎出处链与供给窗自守）。
        return Verdict(subtask_id=subtask.subtask_id, state=STATE_PASS)

    notes: list[str] = []
    metric_slot = str(plan.get("metric_slot") or "")
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

    # —— 闸 2：外表越集（A2 裁决落点——放行态放 ToolContext.approved_tables） ——
    external = [str(t) for t in (plan.get("external_tables") or ()) if str(t).strip()]
    if external:
        unapproved = [t for t in external if t not in approved_tables]
        if unapproved:
            return Verdict(
                subtask_id=subtask.subtask_id,
                state=STATE_BLOCKED_ASK,
                reason=f"计划引用外部表 {unapproved}——越集审批（模型与流程无权自批）",
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
                    },
                ),
            )
        notes.append(f"外部表 {'、'.join(external)} 已放行（ToolContext 审批态）——不重排计划")

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
        if metric.binding_state == "unbound":
            notes.append(
                f"「{metric_slot}」在册未绑定——agg 汇总层无承载列，引擎将走降级"
                "解释链（零数值不冒充）" + CHAIN_SWITCH_HINT
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
            reason="；".join(notes), notes=tuple(notes),
            normalized_slot=normalized_slot,
        )
    return Verdict(subtask_id=subtask.subtask_id, state=STATE_PASS)
