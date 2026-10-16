"""preconditions 本体（`gate_all`）：逐子问题过固定判定位序 → 三态结论 → 留痕。

真源＝`specs/preconditions.md`（已定稿）＋卡 `specs/modules.md` `## preconditions`（签名以卡为准：
`gate_all(state, *, window_candidates=None) -> list[SubtaskVerdict]`）。一句话：每个子问题在**真去查
之前**过一串**固定检查**，出**三态**之一——**放行／拒答／等用户**；**纯程序零 LLM**。

**八位判定序（次序＝执行序，命中即停；规格 :84–:93 明文表——位次／标识逐字，不增不减不乱序）**：
本块**单点调** `tools` 闸件公开面 `judge()` 取结构化判定位（`Verdict.hit_rule` 八位闭世界——
位 1 禁用词／位 3 外表越集／位 4 合法口径＋前置台账闭世界／位 5／6 换链回炉面／位 7 新鲜度窗／
位 8 单井支持），并补两位**结构判据**在相位侧的落点：

1. **位 1 闸1 禁用词**：**结构分派（消费模型结论）**——`SubtaskMatch.mention_mode`（「提及 vs
   执行」，判断在 `tool_matching`／Owner 裁决 #12）＝`mentioned_only` → 放行（不按废弃口径出数）；
   其余照闸件判（禁用户语命中 → 拒答，`hit_rule=ban`）。
2. **位 2 闸1b 模糊时间词门**：**结构判据**＝模型发射载荷窗槽双 null＝不能确定（**不写词面门**，
   裁决 #13＝流水 56 裁①）→ `ask`（`caliber_clarify` → 帧 `clarify`；候选窗＝注入参
   `window_candidates`，producer＝`orchestration`，本块不直引 query）；位 1 命中则不进位 2。
3–8. 位 3–8 照闸件判（`judge()` 内部同序、命中即停；位 5／6 的换链回炉面按行为 7 一次为界收口）。

**行为 7（换链回炉一次为界，pin-16）**：闸件置 `chain_switch_trigger` 的子问题——
`state.chain_switch_marks`（计数面真源在 `state`／B3，本块**消费**、不复制数值、不新增限额）
未在册 → 放行＋写入标记＋机读回炉
信号（notice `chain_switch_reentry`；回炉路由归 `orchestration`）；已在册（同 id 或同参指纹）→ 转
`refuse`（`hit_rule=chain_switch`，不给第三次）。

**行为 6（外表审批申报面）**：`ask` 支的 `approved_ids` 消费面＝`state.approved_ids` → 闸件
`approved_tables`（恢复后重判放行；「执行前再扫」归引擎执行面）。

**错误契约（fail-closed）**：闸件抛错／台账面不可用 → **不着 `allow`**，转 `refuse` 并带拒因
（`hit_rule=gate_unavailable`）；本块**合法降级路径＝无**。

**写口面（行为 10）**：每个 `SubtaskVerdict` 落 step 记录（步 payload 携 `hit_rule`／`decision`／
`notes`）＋非 `allow`／带注记的 `allow` 落 notice——两者皆经 `bookkeeping` **唯一写口**
（`record_step`／`notice`），本块不直写共享写面字段；判定结果本身落 `state.precondition_verdicts`
（本相位产物面，`execution` 已收票按 mapping 读 `decision`／`reason.*`）。

**注入面（关键词注入，不改卡面实参形 `gate_all(state)`；先例＝`understanding.interpret` 的
`bus`／`watermark` 与 `execution.execute` 的 `bus`／`registry`／`store` 缝）**：

- `window_candidates`：位 2 ask 支候选窗（卡面既有注入参；producer＝`orchestration`）；
- `watermark`：位 7 新鲜度窗的水位读数（未注入＝闸静默，不造达标假象）；
- `data_wells`：位 6 软失败域闸的数据链井闭世界（未注入／空＝域闸静默，不发明域语义）。

三者缺省皆可用：缺注入只影响对应判定位的可得性，**不改变**其余位的判定与三态语义。
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from datetime import date
from typing import Any

from appv2.runtimev2.bookkeeping import notice, record_step
from appv2.runtimev2.parsing import CHAIN_DATA, payload_fingerprint
from appv2.runtimev2.persistence import STEP_STATUS_OK, STEP_STATUS_REFUSED
from appv2.runtimev2.preconditions.constants import (
    ASK_KIND_CALIBER_CLARIFY,
    ASK_KIND_EXTERNAL_TABLE_APPROVAL,
    CHAIN_SWITCH_TERMINAL_TAIL_DOMAIN,
    CHAIN_SWITCH_TERMINAL_TAIL_UNBOUND,
    CHAIN_SWITCH_TERMINAL_TEXT_TEMPLATE,
    DECISION_ALLOW,
    DECISION_ASK,
    DECISION_REFUSE,
    GATE_UNAVAILABLE_TEXT,
    HIT_RULE_NONE,
    MENTION_MENTIONED_ONLY,
    NOTE_CHAIN_SWITCH_REENTRY,
    NOTE_MENTION_ONLY,
    NOTICE_ASK_APPROVAL,
    NOTICE_ASK_TEMPLATE,
    NOTICE_CHAIN_SWITCH,
    NOTICE_CHAIN_SWITCH_TEMPLATE,
    NOTICE_NOTE_TEMPLATE,
    NOTICE_REFUSED_TEMPLATE,
    NOTICE_SUBTASK_REFUSED,
    NOTICE_VERDICT_NOTE,
    PAYLOAD_DECISION_KEY,
    PAYLOAD_HIT_RULE_KEY,
    PAYLOAD_NOTES_KEY,
    PAYLOAD_PHASE_KEY,
    PAYLOAD_REENTRY_KEY,
    PAYLOAD_SUBTASK_ID_KEY,
    PHASE,
    RULE_GATE_UNAVAILABLE,
    STEP_KIND,
    TITLE_RULE_TEMPLATE,
    TITLE_TEMPLATE,
    WINDOW_ASK_PROMPT_TEMPLATE,
)
from appv2.runtimev2.preconditions.models import (
    AskReason,
    RefusalReason,
    SubtaskVerdict,
)
from appv2.runtimev2.state import RunState
from appv2.tools import (
    ASK_CLARIFY,
    ASK_EXTERNAL_TABLE_APPROVAL,
    CHAIN_SWITCH_KIND_DOMAIN,
    HIT_RULE_BAN,
    HIT_RULE_CHAIN_SWITCH,
    HIT_RULE_FUZZY_WINDOW,
    STATE_BLOCKED_ASK,
    STATE_BLOCKED_REFUSE,
    LedgerFacts,
    SubtaskInput,
    Verdict,
    judge,
    ledger_facts,
    resolve_metric_slot,
)


def gate_all(
    state: RunState,
    *,
    window_candidates: Sequence[str] | None = None,
    watermark: date | str | None = None,
    data_wells: Collection[str] | None = None,
) -> list[SubtaskVerdict]:
    """逐子问题过固定判定位序出三态（**每子问题恰一条** ——行为 1；越界／缺契约＝fail-closed）。

    返回条数与 `state.question_group.subtasks` 一一对应（顺序同组序；`subtask_id` 逐条对上）；
    本函数只出结论与留痕，**不做**路由、不直答、不发帧（归 `orchestration`／`answering`）。
    """
    subtasks = _subtasks_of(state)
    matches = _matches_by_id(state)
    facts = _facts_of(state)
    approved = tuple(str(item) for item in state.approved_ids)
    resolved = _window_resolved(state)
    moment = _watermark_of(watermark)
    wells = None if data_wells is None else tuple(str(item) for item in data_wells)
    candidates = () if window_candidates is None else tuple(str(item) for item in window_candidates)

    marks = dict(state.chain_switch_marks)
    verdicts: list[SubtaskVerdict] = []
    for item in subtasks:
        subtask_id = str(item.get("id") or "").strip()
        try:
            verdict, reentry = _one(
                subtask_id=subtask_id,
                question=str(item.get("question") or ""),
                subtask=item,
                match=matches.get(subtask_id),
                facts=facts,
                approved=approved,
                moment=moment,
                resolved=resolved,
                wells=wells,
                candidates=candidates,
                marks=marks,
            )
        except Exception:  # 闸件抛错／闸内契约违例 → fail-closed（不静默放行、不炸整批）
            verdict, reentry = _unavailable(subtask_id), False
        _record(state, verdict, reentry=reentry)
        verdicts.append(verdict)

    state.precondition_verdicts = [verdict.as_payload() for verdict in verdicts]
    if marks != state.chain_switch_marks:
        state.chain_switch_marks = marks
    return verdicts


# ── 逐子问题判定（八位判定序——命中即停）─────────────────────────────────────────


def _one(
    *,
    subtask_id: str,
    question: str,
    subtask: Mapping[str, Any],
    match: Mapping[str, Any] | None,
    facts: LedgerFacts | None,
    approved: tuple[str, ...],
    moment: date | None,
    resolved: bool,
    wells: tuple[str, ...] | None,
    candidates: tuple[str, ...],
    marks: dict[str, str],
) -> tuple[SubtaskVerdict, bool]:
    """单子问题判定（返回结论 ＋ 「换链回炉提议首次触发」标记）。"""
    if facts is None:
        raise ValueError("台账面不可用（闸件判定输入缺失）——fail-closed，不静默放行")
    payload = match or {}
    if str(payload.get("mention_mode") or "") == MENTION_MENTIONED_ONLY:
        # 位 1：模型结论「仅提及」→ 放行（机械分派；判断在 tool_matching——pin-31）。
        return _allow(subtask_id, notes=(NOTE_MENTION_ONLY,)), False

    chain = str(payload.get("chain") or subtask.get("chain") or CHAIN_DATA)
    plan = payload.get("plan") if isinstance(payload.get("plan"), Mapping) else None
    need = (
        payload.get("retrieval_need")
        if isinstance(payload.get("retrieval_need"), Mapping)
        else None
    )
    gate = judge(
        SubtaskInput(
            subtask_id=subtask_id,
            question=question,
            chain=chain,
            plan=plan,
            retrieval_need=need,
        ),
        facts,
        approved_tables=approved,
        watermark=moment,
        window_resolved=resolved,
        data_wells=wells,
    )

    if gate.hit_rule == HIT_RULE_BAN:
        return _refusal_of(subtask_id, gate, facts, plan), False  # 位 1 命中先于位 2
    if chain == CHAIN_DATA and _window_undetermined(plan):
        return _window_ask(subtask_id, candidates, notes=gate.notes), False  # 位 2（结构判据）
    if gate.state == STATE_BLOCKED_ASK:
        return _ask_of(subtask_id, gate), False  # 位 3（外表越集）／位 4（口径反问）
    if gate.state == STATE_BLOCKED_REFUSE:
        return _refusal_of(subtask_id, gate, facts, plan), False  # 位 4（口径／台账闭世界）
    return _allow_of(subtask_id, gate, fact_plan=plan, marks=marks)


def _allow_of(
    subtask_id: str,
    gate: Verdict,
    *,
    fact_plan: Mapping[str, Any] | None,
    marks: dict[str, str],
) -> tuple[SubtaskVerdict, bool]:
    """放行支（pass／note）——含行为 7 换链回炉一次为界的收口（位 5／6 触发面）。"""
    notes = tuple(gate.notes)
    if not gate.chain_switch_trigger:
        return _allow(subtask_id, notes=notes), False
    fingerprint = payload_fingerprint({"plan": dict(fact_plan or {}), "retrieval_need": None})
    if subtask_id in marks or fingerprint in marks.values():
        tail = (
            CHAIN_SWITCH_TERMINAL_TAIL_DOMAIN
            if gate.chain_switch_kind == CHAIN_SWITCH_KIND_DOMAIN
            else CHAIN_SWITCH_TERMINAL_TAIL_UNBOUND
        )
        return (
            _refuse(
                subtask_id,
                rule_id=HIT_RULE_CHAIN_SWITCH,
                human_text=CHAIN_SWITCH_TERMINAL_TEXT_TEMPLATE.format(
                    fingerprint=fingerprint[:12], tail=tail
                ),
                notes=notes,
            ),
            False,
        )
    marks[subtask_id] = fingerprint
    return _allow(subtask_id, notes=(*notes, NOTE_CHAIN_SWITCH_REENTRY)), True


# ── 三态构造（单点）─────────────────────────────────────────────────────────────


def _allow(subtask_id: str, *, notes: tuple[str, ...]) -> SubtaskVerdict:
    return SubtaskVerdict(
        subtask_id=subtask_id,
        decision=DECISION_ALLOW,
        notes=notes,
        hit_rule=HIT_RULE_NONE,
    )


def _refuse(
    subtask_id: str,
    *,
    rule_id: str,
    human_text: str,
    alternatives: tuple[str, ...] = (),
    notes: tuple[str, ...] = (),
) -> SubtaskVerdict:
    return SubtaskVerdict(
        subtask_id=subtask_id,
        decision=DECISION_REFUSE,
        notes=notes,
        reason=RefusalReason(rule_id=rule_id, human_text=human_text, alternatives=alternatives),
        hit_rule=rule_id,
    )


def _refusal_of(
    subtask_id: str,
    gate: Verdict,
    facts: LedgerFacts,
    plan: Mapping[str, Any] | None,
) -> SubtaskVerdict:
    """闸件拒支 → 本块拒答（`hit_rule`／人话／替代项三面齐——行为 8）。"""
    return _refuse(
        subtask_id,
        rule_id=gate.hit_rule,
        human_text=gate.reason,
        alternatives=_alternatives_of(facts, plan),
        notes=tuple(gate.notes),
    )


def _ask_of(subtask_id: str, gate: Verdict) -> SubtaskVerdict:
    """闸件等用户支 → 本块 `ask`（`kind` 两形映射：帧侧映射表见 `constants`）。"""
    frame = gate.ask
    if frame is None:
        raise ValueError("闸件 ask 支缺挂起帧（AskReason 无承载）——fail-closed，不静默放行")
    if frame.kind == ASK_EXTERNAL_TABLE_APPROVAL:
        kind = ASK_KIND_EXTERNAL_TABLE_APPROVAL
    elif frame.kind == ASK_CLARIFY:
        kind = ASK_KIND_CALIBER_CLARIFY
    else:
        raise ValueError(f"闸件 ask 帧 kind 越界（两形闭世界）：{frame.kind!r}")
    return SubtaskVerdict(
        subtask_id=subtask_id,
        decision=DECISION_ASK,
        notes=tuple(gate.notes),
        reason=AskReason(
            kind=kind,
            prompt=frame.prompt,
            options=tuple(str(option) for option in frame.options),
        ),
        hit_rule=gate.hit_rule,
    )


def _window_ask(
    subtask_id: str, candidates: tuple[str, ...], *, notes: tuple[str, ...]
) -> SubtaskVerdict:
    """位 2 结构判据命中 → `ask`（三选一反问帧；候选窗＝注入参，缺注入＝选项如实为空）。"""
    return SubtaskVerdict(
        subtask_id=subtask_id,
        decision=DECISION_ASK,
        notes=notes,
        reason=AskReason(
            kind=ASK_KIND_CALIBER_CLARIFY,
            prompt=WINDOW_ASK_PROMPT_TEMPLATE.format(subtask=subtask_id),
            options=candidates,
        ),
        hit_rule=HIT_RULE_FUZZY_WINDOW,
    )


def _unavailable(subtask_id: str) -> SubtaskVerdict:
    """闸件不可用／闸内契约违例 → fail-closed 转 `refuse`（**不着 `allow`**，不静默放行）。"""
    return _refuse(
        subtask_id,
        rule_id=RULE_GATE_UNAVAILABLE,
        human_text=GATE_UNAVAILABLE_TEXT,
    )


# ── 判定位输入面 ────────────────────────────────────────────────────────────────


def _window_undetermined(plan: Mapping[str, Any] | None) -> bool:
    """位 2 结构判据：模型发射载荷**窗槽双 null**（缺槽同判）＝时间窗不能确定（裁决 #13）。

    **不写词面门**——不认「最近／近期」类词面，只看载荷窗槽（`window_start`／`window_end`）；
    非 data 链无窗面（调用点按链把关）；无 plan（上游契约违例）不在此判（交闸件判）。
    """
    if plan is None:
        return False
    return plan.get("window_start") is None and plan.get("window_end") is None


def _alternatives_of(facts: LedgerFacts, plan: Mapping[str, Any] | None) -> tuple[str, ...]:
    """替代项（行为 8 的口径类承载面）——台账面结构化派生，**不按文案反推**：

    指标在台账命中 → 该指标的口径支 keys（替代口径）；未命中 → 台账名录（指标 slot 集，
    即「可查询的指标名录」）。台账为空＝空元组（如实空，不编造）。
    """
    raw_slot = str((plan or {}).get("metric_slot") or "")
    resolved = resolve_metric_slot(facts, raw_slot) if raw_slot else None
    metric = facts.metrics.get(resolved) if resolved is not None else None
    if metric is not None:
        keys = tuple(
            str(caliber.get("key") or "")
            for caliber in metric.calibers
            if str(caliber.get("key") or "")
        )
        if keys:
            return keys
    return tuple(facts.metrics)


# ── 上游投影面（问题组／工具匹配／恢复态／注入参）─────────────────────────────────


def _subtasks_of(state: RunState) -> list[Mapping[str, Any]]:
    """问题组支列（上游澄清相位产物）；缺组／缺 id ＝上游契约违例 → fail-closed 抛错。"""
    payload = state.question_group
    raw = payload.get("subtasks") if isinstance(payload, Mapping) else None
    if not isinstance(raw, list) or not raw:
        raise ValueError(
            "前置条件机缺问题组（state.question_group 无 subtasks——上游澄清相位未产组）："
            "fail-closed，不猜、不补、不跳过子问题"
        )
    subtasks: list[Mapping[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError(f"问题组支须为对象（state.question_group.subtasks）：{item!r}")
        if not str(item.get("id") or "").strip():
            raise ValueError("问题组支缺 id（逐子问题判定的比对面必填——fail-closed，不猜）")
        subtasks.append(item)
    return subtasks


def _matches_by_id(state: RunState) -> dict[str, Mapping[str, Any]]:
    """工具匹配支投影（`state.tool_matches`——相位②产物，按子问题 id 取；缺支＝照缺判）。"""
    return {
        str(item.get("id") or ""): item
        for item in state.tool_matches
        if isinstance(item, Mapping)
    }


def _facts_of(state: RunState) -> LedgerFacts | None:
    """台账判定事实（`tools.ledger_facts(state.ledger_dump)`——只经 `tools` 公开面）。"""
    try:
        return ledger_facts(state.ledger_dump or {})
    except Exception:  # 台账面不可用 → 逐子问题 fail-closed（`_one` 抛错口径一致）
        return None


def _window_resolved(state: RunState) -> bool:
    """用户已答窗留痕（run 内 clarify 恢复项在场）——闸件词面门零误伤面的透传。"""
    return any(
        isinstance(choice, Mapping) and str(choice.get("kind") or "") == ASK_CLARIFY
        for choice in state.resume_choices
    )


def _watermark_of(value: date | str | None) -> date | None:
    """水位读数归一（形态处理——注入可能给日期或 ISO 文本；不可解析＝ None，不编造）。"""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


# ── 写口面（行为 10：step payload ＋ notice——皆经 bookkeeping 唯一写口）───────────


def _record(state: RunState, verdict: SubtaskVerdict, *, reentry: bool) -> None:
    """单条结论的机读信号：步记录（payload 携 `hit_rule`／`decision`／`notes`）＋ notice。

    静默放行是已知失败模式：非 `allow` **与**任何带注记的 `allow` 必有 notice；无注记的普通
    放行零额外信号（保留集行为——不产空 notice）。
    """
    record_step(
        state,
        kind=STEP_KIND,
        title=_title_of(verdict),
        status=STEP_STATUS_REFUSED if verdict.decision == DECISION_REFUSE else STEP_STATUS_OK,
        payload={
            PAYLOAD_PHASE_KEY: PHASE,
            PAYLOAD_SUBTASK_ID_KEY: verdict.subtask_id,
            PAYLOAD_DECISION_KEY: verdict.decision,
            PAYLOAD_HIT_RULE_KEY: verdict.hit_rule or "",
            PAYLOAD_NOTES_KEY: list(verdict.notes),
            PAYLOAD_REENTRY_KEY: reentry,
        },
    )
    notice_type = _notice_type_of(verdict, reentry=reentry)
    if notice_type is not None:
        notice(state, type=notice_type, content=_notice_text(verdict, reentry=reentry))


def _title_of(verdict: SubtaskVerdict) -> str:
    if verdict.hit_rule:
        return TITLE_RULE_TEMPLATE.format(
            subtask=verdict.subtask_id, decision=verdict.decision, rule=verdict.hit_rule
        )
    return TITLE_TEMPLATE.format(subtask=verdict.subtask_id, decision=verdict.decision)


def _notice_type_of(verdict: SubtaskVerdict, *, reentry: bool) -> str | None:
    """notice 类型（取值真源＝`transport.NOTICE_TYPES` 闭世界）；普通放行＝无通知（零额外信号）。"""
    if reentry:
        return NOTICE_CHAIN_SWITCH
    if verdict.decision == DECISION_REFUSE:
        return NOTICE_SUBTASK_REFUSED
    if verdict.decision == DECISION_ASK:
        assert isinstance(verdict.reason, AskReason)  # 形状把守已在模型层（fail-closed）
        if verdict.reason.kind == ASK_KIND_EXTERNAL_TABLE_APPROVAL:
            return NOTICE_ASK_APPROVAL
        return NOTICE_VERDICT_NOTE
    if verdict.notes:
        return NOTICE_VERDICT_NOTE
    return None


def _notice_text(verdict: SubtaskVerdict, *, reentry: bool) -> str:
    if verdict.decision == DECISION_REFUSE:
        assert isinstance(verdict.reason, RefusalReason)  # 形状把守已在模型层（fail-closed）
        return NOTICE_REFUSED_TEMPLATE.format(
            subtask=verdict.subtask_id,
            rule=verdict.reason.rule_id,
            human=verdict.reason.human_text,
        )
    if verdict.decision == DECISION_ASK:
        assert isinstance(verdict.reason, AskReason)  # 形状把守已在模型层（fail-closed）
        return NOTICE_ASK_TEMPLATE.format(
            subtask=verdict.subtask_id,
            kind=verdict.reason.kind,
            prompt=verdict.reason.prompt,
        )
    digest = "；".join(verdict.notes)
    if reentry:
        return NOTICE_CHAIN_SWITCH_TEMPLATE.format(subtask=verdict.subtask_id, digest=digest)
    return NOTICE_NOTE_TEMPLATE.format(
        subtask=verdict.subtask_id, count=len(verdict.notes), digest=digest
    )
