"""澄清相位主体（`specs/clarification.md` 行为 1／8／12–19 与接口定义节）。

一次调用＝一次 LLM 决策周期：**挂起恢复支**（`pending_ask` 在场 → 消费 `AskChoice` 投影、
重置轮预算、重取易变量）→ **轮装配**（首入包一次性＋每轮增量条，经 `bookkeeping` 写口追加）→
**经 `bookkeeping.call_model` 单点发起** → **闭世界对账分派**（四动作；`parsing` 解析＋本块
消费方转换）→ **单出口互斥返回位**（`ClarifyAsk`／`ClarifyFinal`／`ClarifyRejection`；
`discover` 与到顶截断**不占返回位**——路由意图经 `state.next_intent` 交出）。

本块**零工具直调**（`discover` 只以 `next_intent="discover"` 交 `orchestration` 路由出去执行）、
**零落盘**、**零语义判断**（程序只做闭世界 schema 对账与结构判定：动作／条数／注释三段槽位对账／
`chain` 成员／观察计数——豁免面＝形态处理，`specs/clarification.md` 行 16）。

共享写面（`messages`／`steps`／`process_notes`／`notices`／`dialogue`／`next_intent`／
`contracts_appended`）**只经 `bookkeeping` 写口**（`specs/bookkeeping.md` 行为 1）；其余相位私有
字段（`pending_ask`／`rounds`／`user_hint`／`decision_error`／`budget_reject_streak`／
`question_group`／`precondition_verdicts`／`pending_discovers`）由本块如实落值（无写口者不设旁路）。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

import appv2.runtimev2.clarification.constants as clarification_constants
from appv2.infra.clock import now
from appv2.runtimev2.bookkeeping import (
    append_contract,
    append_dialogue,
    append_message,
    call_model,
    direct_answer,
    note,
    notice,
    record_step,
    set_intent,
)
from appv2.runtimev2.clarification.constants import (
    ASK_FRAME_DETAIL_NONE,
    ASK_KIND_CLARIFY,
    BINDING_STATES,
    CALLER_DECISION,
    CAPPED_ANSWER_HEADER,
    CAPPED_NOTE_DIGEST,
    CAPPED_NOTICE_TEMPLATE,
    CAUSE_BINDING_OUT_OF_WORLD,
    CAUSE_SEGMENT_COUNT,
    CAUSE_SLOT_NOT_IN_LEDGER,
    CAUSE_WINDOW_ILLEGAL,
    DIALOGUE_ORIGIN_CLARIFY_REPLAY,
    EMPTY_PROBES_JOIN,
    GUIDANCE_JOIN,
    ISO_DAY_SHAPE,
    MATERIAL_ROW_PREFIX,
    NO_LEDGER_ROW_SHELL,
    NO_MATERIAL_SHELL,
    NOTE_DIGEST_ASK,
    NOTE_DIGEST_DISCOVER,
    NOTE_DIGEST_FINALIZE,
    NOTE_DIGEST_REJECTED,
    NOTE_DIGEST_RESUME,
    NOTE_PHASE,
    NOTE_SEGMENT_BINDING,
    NOTE_SEGMENT_COUNT,
    NOTE_SEGMENT_SLOT,
    NOTE_SEGMENT_WINDOW,
    NOTE_SEGMENTS,
    NOTE_SLOT_SEPARATOR,
    NOTE_TITLE,
    NOTICE_CLARIFY_CAPPED,
    NOTICE_DECISION_NOTE,
    NOTICE_EMISSION_QUOTE_REPAIR,
    NOTICE_LOCATOR_KIND,
    PAYLOAD_ASK_FRAME,
    PAYLOAD_CAPPED,
    PAYLOAD_EMISSION,
    PAYLOAD_PHASE,
    PAYLOAD_REJECTION,
    PAYLOAD_RESUME,
    PAYLOAD_VOLATILE,
    QUOTE_REPAIR_NOTICE_CONTENT,
    REASON_FINALIZE_ZERO_OBSERVATION,
    REASON_LEDGER_NOTES_SLOT_MISMATCH,
    REASON_MARKERS,
    REASON_NO_REDISCOVER,
    REASON_REJECTION_GUIDANCE,
    REASON_SCHEMA_INVALID,
    REJECT_FREE_STREAK,
    STEP_TITLE_ASK,
    STEP_TITLE_CAPPED,
    STEP_TITLE_DECOMPOSE,
    STEP_TITLE_DISCOVER,
    STEP_TITLE_FINALIZE,
    STEP_TITLE_PROMPT_CHARS,
    STEP_TITLE_REJECTED,
    STEP_TITLE_RESUME,
    TEXT_JOIN,
    TEXT_NO_REDISCOVER,
    TEXT_SLOT_MISMATCH_BLOCK,
    TEXT_SLOT_MISMATCH_HEAD,
    TEXT_SLOT_MISMATCH_TAIL,
    TEXT_SLOT_MISMATCH_TITLE,
    TEXT_ZERO_OBSERVATION,
    TOOL_NAME_MISSING,
    WINDOW_LITERALS,
    WINDOW_SEGMENT_TOTAL,
    WINDOW_SEPARATOR,
)
from appv2.runtimev2.clarification.guidance import rejection_guidance
from appv2.runtimev2.clarification.models import (
    ClarifyAsk,
    ClarifyFinal,
    ClarifyOutcome,
    ClarifyReason,
    ClarifyRejection,
)
from appv2.runtimev2.clarification.volatile import (
    ledger_name_rows,
    ledger_projection,
    read_volatile,
)
from appv2.runtimev2.parsing import (
    BUDGET_REJECT_MARK,
    CLARIFY_ASK,
    CLARIFY_DECOMPOSE,
    CLARIFY_DISCOVER,
    CLARIFY_FINALIZE,
    ClarifyEmission,
    parse_question_group,
    parse_with_quote_repair,
)
from appv2.runtimev2.prompts import (
    PHASE_CLARIFY,
    assemble_decision_increment,
    assemble_decision_package,
    render_ledger_resident_block,
)
from appv2.runtimev2.state import (
    INTENT_ANSWER,
    INTENT_DECISION,
    INTENT_DISCOVER,
    INTENT_TOOLMATCH,
    STEP_DECISION,
    RunState,
)


def clarify(state: RunState, *, guide_text: str = "") -> ClarifyOutcome:
    """澄清相位入口（卡面签名逐字：`def clarify(state: RunState) -> ClarifyOutcome`；
    注入参 `guide_text` 见卡级微注——流水 63）。

    单出口互斥三返回位见 `models`；`None` 返＝本次调用不占返回位（`discover`／到顶截断）。

    `guide_text`＝§A 指南段**文本注入参**（流水 63——additive 注入，编排面按启动快照注入全文；
    缺省空串＝空段头，回归面同形）。装载面归 `api` 组合根（`OntologyGuideProvider`
    启动取一次快照，同 `watermark` 先例），本块只下传、不读文件。
    """
    _consume_resume(state)
    _open_round(state, guide_text=guide_text)
    content = call_model(state, CALLER_DECISION, state.messages)
    # 模型原话如实入链（追加式：包／增量／应答三形构成链上本节点簿记；`pin-22` 只追加）。
    append_message(state, role="assistant", content=content)
    return _dispatch(state, content)


def _today() -> date:
    """样例窗锚的时间量（B14：时间只经 `infra.clock`；水位读缝未落定时＝当日）。"""
    return now().date()


# ── 挂起恢复支（行为 12／13）───────────────────────────────────────────────


def _consume_resume(state: RunState) -> bool:
    """挂起恢复支：`pending_ask` 在场即消费恢复选择（行为 12／13），返回是否消费。

    - **等待不计轮**：挂起（`ask` 支）不动 `rounds`——本次进入的轮预算也**重置**（`rounds=0`
      ，V1 语义「用户输入重置轮预算」）；
    - **用户所选原话进对话链**（去空白前缀）：`append_message` 进链 ＋ `append_dialogue`
      以来源 `clarify_approval_replay` 进对话层（`pin-26` 的来源闭世界单点）；
    - **恢复时重取易变量**（行为 13）：`read_volatile` 从**活体投影**重取四项并落步骤 payload
      （机读信号面——「重取」可机检）；
    - 审批帧（`kind="external_table_approval"`）**不归本块**：不消费、不接管（审批面归
      前置条件／审批链）。
    """
    frame = state.pending_ask
    if not isinstance(frame, Mapping) or frame.get("kind") != ASK_KIND_CLARIFY:
        return False
    choice = _resume_choice(state)
    state.pending_ask = None
    state.rounds = 0
    state.budget_reject_streak = 0
    state.user_hint = choice
    if choice:
        append_message(state, role="user", content=choice)
        append_dialogue(
            state, role="user", content=choice, origin=DIALOGUE_ORIGIN_CLARIFY_REPLAY
        )
    readings = read_volatile(state)
    record_step(
        state,
        kind=STEP_DECISION,
        title=STEP_TITLE_RESUME.format(value=choice),
        payload={
            PAYLOAD_PHASE: PHASE_CLARIFY,
            PAYLOAD_RESUME: choice,
            PAYLOAD_VOLATILE: readings,
        },
    )
    note(
        state,
        phase=NOTE_PHASE,
        title=NOTE_TITLE,
        digest=f"{NOTE_DIGEST_RESUME}：{choice}",
    )
    return True


def _resume_choice(state: RunState) -> str:
    """恢复选择面：`state.resume_choices` 末条的 `choice`（`AskChoice` 投影四键之 `choice`）。

    非 `clarify` 类帧（审批）与缺位／非串值 → 如实空串（不猜、不取默认；空选择仍算已消费——
    挂起态由 `pending_ask` 清除表达，不留在场上自旋）。
    """
    if not state.resume_choices:
        return ""
    entry = state.resume_choices[-1]
    if isinstance(entry, Mapping):
        if entry.get("kind") != ASK_KIND_CLARIFY:
            return ""
        value = entry.get("choice")
        return value.strip() if isinstance(value, str) else ""
    if getattr(entry, "kind", None) != ASK_KIND_CLARIFY:
        return ""
    value = getattr(entry, "choice", None)
    return value.strip() if isinstance(value, str) else ""


# ── 轮装配（首入包一次性＋每轮增量条）─────────────────────────────────────


def _open_round(state: RunState, *, guide_text: str = "") -> None:
    """轮装配：首入包（`append_contract` 幂等标记护一次性）＋每轮增量条（非空才追加）。

    装配时序照 V1 `clarify_node`：先算「是否首入」→ 追加首入包（若首入）→ 追加增量条 →
    最后落相位标记——**首入轮不带「探查预算」条**（该条仅非首入轮；V1 `contracts_flag` 语义）。

    两处**装配面入参**（登记项，呈主窗——本块依赖面＝`prompts`／`parsing`／`bookkeeping`／
    `state`，两装载面归 `context`／编排面）：

    - `guide_text`＝§A 指南段**文本经入参注入**（装载面归 `api` 组合根——启动取一次快照，
      流水 63，与 `watermark` 同款注入先例；编排面经 `clarify` 下传，本块不读文件）；
      缺省空串＝空段头（回归面同形）；
    - 增量条的「已做段」（`done_text`）不传：其渲染归 `context.render_process_notes`，注入点
      归编排面（`specs/prompts.md` 行为 16「何时追加＝调用方义务」）。
    """
    first_round = PHASE_CLARIFY not in state.contracts_appended
    if first_round:
        package = assemble_decision_package(
            state,
            phase=PHASE_CLARIFY,
            guide_text=guide_text,
            today=_today(),
            max_subtasks=clarification_constants.MAX_SUBTASKS,
        )
        append_message(state, role="user", content=package)
    increment = assemble_decision_increment(state, phase=PHASE_CLARIFY)
    if increment:
        append_message(state, role="user", content=increment)
    if first_round:
        append_contract(state, PHASE_CLARIFY)


# ── 闭世界对账与单出口分派（行为 1／19）───────────────────────────────────


def _parse_emission(state: RunState) -> Callable[[str], ClarifyEmission | str]:
    """解析入参注入面：限额两参引 `state.budget`（轮内发现／全 run 发现剩余）、条数上限引单点。"""
    max_discovers = int(state.budget.discovers_per_round)
    budget_left = int(state.budget.discovers_per_run) - int(state.discover_used)

    def _parse(content: str) -> ClarifyEmission | str:
        return parse_question_group(
            content,
            max_discovers=max_discovers,
            discover_budget_left=budget_left,
            max_subtasks=clarification_constants.MAX_SUBTASKS,
        )

    return _parse


def _dispatch(state: RunState, content: str) -> ClarifyOutcome:
    """解析（含引号自修受理）→ 三态判→ 四动作闭世界分派（越界值判失败、不猜不取默认）。"""
    parsed, quote_repaired = parse_with_quote_repair(_parse_emission(state), content)
    if quote_repaired:
        notice(
            state,
            type=NOTICE_EMISSION_QUOTE_REPAIR,
            content=QUOTE_REPAIR_NOTICE_CONTENT,
        )
    if isinstance(parsed, str):
        return _reject_from_parsing(state, parsed)
    emission: ClarifyEmission = parsed
    _clear_retry_marks(state)
    if emission.kind == CLARIFY_DISCOVER:
        return _on_discover(state, emission)
    if emission.kind == CLARIFY_DECOMPOSE:
        return _on_decompose(state, emission)
    if emission.kind == CLARIFY_FINALIZE:
        return _on_finalize(state, emission)
    if emission.kind == CLARIFY_ASK:
        return _on_ask(state, emission)
    raise ValueError(
        f"clarify 发射动作越界（parsing 已守四值闭世界——不可达分支，fail-closed）："
        f"{emission.kind!r}"
    )


def code_of_rejection(reason: str) -> str:
    """行为 19 的机械适配面：解析拒文 → 拒因枚举（序查标记表；未命中→残差码）。"""
    for marker, code in REASON_MARKERS:
        if marker in reason:
            return code
    return REASON_SCHEMA_INVALID


def _reject_from_parsing(state: RunState, reason: str) -> ClarifyRejection:
    """parsing 拒文（`str`）→ 结构化 `ClarifyRejection`（str 逐字进 `reason` 字段）。

    预算驱动拒（机读前缀＝`parsing.BUDGET_REJECT_MARK`）走「首拒免轮」；其余拒照耗轮
    （V1 `clarify_node` 分支 3 语义：拒因回喂＋轮数闸收敛兜底）。
    """
    budget_driven = reason[: len(BUDGET_REJECT_MARK)] == BUDGET_REJECT_MARK
    return _record_rejection(
        state,
        reasons=[ClarifyReason(code=code_of_rejection(reason), reason=reason)],
        title_reason=reason,
        error_text=reason,
        first_free=budget_driven,
    )


def _record_rejection(
    state: RunState,
    *,
    reasons: list[ClarifyReason],
    title_reason: str,
    error_text: str,
    first_free: bool,
    emission_payload: dict[str, Any] | None = None,
) -> ClarifyRejection:
    """拒因落地（行为 17／18 的机读信号面）：步记录＋过程档案＋`decision_error` 回喂面。

    `first_free`（预算驱动／浅探查／重复钻取三类）＝首拒免轮、连续第 2 次起占轮
    （V1 `budget_reject_streak` 语义：轮数闸确定性收敛、免轮面不重开自旋洞）；其余拒照耗轮。
    回喂到 `state.decision_error`（增量条的「上次发射被拒」行渲染面）；「去哪」由
    `orchestration` 按 `next_intent=decision` 重定向回本相位（本块只写字段、不做路由决策）。
    """
    rounds_now = int(state.rounds)
    if first_free:
        streak = int(state.budget_reject_streak) + 1
        round_no = rounds_now if streak < REJECT_FREE_STREAK else rounds_now + 1
    else:
        streak = 0
        round_no = rounds_now + 1
    state.rounds = round_no
    state.budget_reject_streak = streak
    state.decision_error = error_text
    payload: dict[str, Any] = {PAYLOAD_PHASE: PHASE_CLARIFY, PAYLOAD_REJECTION: error_text}
    if emission_payload is not None:
        payload[PAYLOAD_EMISSION] = emission_payload
    record_step(
        state,
        kind=STEP_DECISION,
        title=STEP_TITLE_REJECTED.format(round=round_no, reason=title_reason),
        payload=payload,
    )
    note(
        state,
        phase=NOTE_PHASE,
        title=NOTE_TITLE,
        digest=NOTE_DIGEST_REJECTED.format(round=round_no, reason=title_reason),
    )
    set_intent(state, INTENT_DECISION)
    return ClarifyRejection(reasons=list(reasons))


def _clear_retry_marks(state: RunState) -> None:
    """成功结局清回喂面与免轮计数（V1 `base`：回喂文／用户补充／streak 三清）。"""
    state.decision_error = ""
    state.user_hint = ""
    state.budget_reject_streak = 0


def _ship_decision_note(state: RunState, emission: ClarifyEmission) -> None:
    """发射注记出流（行为 3「并注记」的机读信号面）：`note` 非空 → `decision_note` 通知。

    默认值＋注记同批产出（真源 `walk/08` §七 Q-B）：默认窗是**模型侧结论**（本块不造、
    不判——问句原文在程序侧零读点），注记由本块逐字转抄为机读信号。**缺位不产通知**
    （不得凭空产注记，同 `state.Convergence` 的形态互斥纪律）；出流面归通知写口单一
    （`bookkeeping.notice`——恰三键，`type` 值引 `transport.NOTICE_TYPES`）。
    承载位换、文本不变（逐字稿载体＝V1 `appv2/runtime/graph.py` `clarify_node` 两处
    `decision_note` 出流，L2501／L2616）。
    """
    if emission.note:
        notice(state, type=NOTICE_DECISION_NOTE, content=emission.note)


# ── 四动作分派（每支一处；去向只经 `set_intent` 给意图）────────────────────


def _on_discover(state: RunState, emission: ClarifyEmission) -> ClarifyOutcome:
    """`discover`：**不占返回位**——经 `next_intent="discover"` 交 `orchestration` 路由出去执行。

    「禁再 discover」的机械半句先判（见 `_rediscover_blocked`）；通过则把发射支定型进
    `pending_discovers`（执行面归发现步），本块**零工具直调**。
    """
    emission_payload = emission.as_payload()
    if _rediscover_blocked(state):
        return _record_rejection(
            state,
            reasons=[ClarifyReason(code=REASON_NO_REDISCOVER, reason=TEXT_NO_REDISCOVER)],
            title_reason=TEXT_NO_REDISCOVER,
            error_text=TEXT_NO_REDISCOVER,
            first_free=True,
            emission_payload=emission_payload,
        )
    branches = [dict(item) for item in emission.discovers]
    state.pending_discovers = branches
    names = EMPTY_PROBES_JOIN.join(_tool_name_of(item) for item in branches)
    record_step(
        state,
        kind=STEP_DECISION,
        title=STEP_TITLE_DISCOVER.format(count=len(branches), names=names),
        payload={PAYLOAD_PHASE: PHASE_CLARIFY, PAYLOAD_EMISSION: emission_payload},
    )
    note(
        state,
        phase=NOTE_PHASE,
        title=NOTE_TITLE,
        digest=NOTE_DIGEST_DISCOVER.format(count=len(branches)),
    )
    set_intent(state, INTENT_DISCOVER)
    return None


def _rediscover_blocked(state: RunState) -> bool:
    """「台账命中且时间窗已定 → 禁再 `discover`」的**机械半句**（行为 16 后半）。

    两个机械面（零语义判断）：
    ①**台账命中**＝台账活体投影非空（词典层已全量在手——全量注入面）；
    ②**已定案**＝既成问题组在场（`state.question_group`——模型「台账命中且时间窗已定＝
    分解完毕」结论的**动作落点**）。

    「时间窗已定」的判断属模型侧策略判断（真源 `walk/裁决表.md` 项目级裁决 #13），程序只按
    结论的机械落点分派——本块对该半句的落地载体选择＝**登记项（呈主窗）**；驳回是**回喂**
    （非终局），模型可改发 `decompose`／`finalize`。
    """
    return bool(ledger_projection(state)) and _has_question_group(state)


def _has_question_group(state: RunState) -> bool:
    """既成问题组（分解结论的机械载体；空映射＝未定案）。"""
    group = state.question_group
    return isinstance(group, Mapping) and bool(group)


def _tool_name_of(branch: Mapping[str, Any]) -> str:
    """发射支工具名（缺位如实以 `?` 显——V1 事实面，不编造）。"""
    name = branch.get("tool")
    return name if isinstance(name, str) and name else TOOL_NAME_MISSING


def _on_decompose(state: RunState, emission: ClarifyEmission) -> ClarifyOutcome:
    """`decompose`：注释**第二层**机检（三段槽位对账）→ 定案 `ClarifyFinal`。

    `parsing` 只查注释非空；「注释各段合不合台账」在本块校（行为 8；2026-10-16 改·流水 64，
    Owner 裁——判据由「注入块内逐字子串」改「三段槽位对账」）——**判违约不自动修补**：
    返结构化拒因（携段级诊断＋期望形＋台账相关行）由 `orchestration` 回喂重决策。通过则问题组
    落状态、旧前置判定作废（判定随组走）、占一轮、去向 `tool_matching`；发射注记非空时逐字出流
    为 `decision_note` 机读通知（行为 3「并注记」——默认窗等模型侧结论的原话承载）。
    """
    group = emission.group
    emission_payload = emission.as_payload()
    if group is None:
        raise ValueError("decompose 发射缺问题组（parsing 已守——不可达分支，fail-closed）")
    registry = ledger_name_rows(state)
    injection = render_ledger_resident_block(state)
    offenders = [
        (subtask.id, diagnostic)
        for subtask in group.subtasks
        if (
            diagnostic := _note_slot_mismatch(
                subtask.ledger_notes, registry=registry, injection_block=injection
            )
        )
        is not None
    ]
    if offenders:
        reason = _slot_mismatch_reason(offenders)
        ids = EMPTY_PROBES_JOIN.join(subtask_id for subtask_id, _ in offenders)
        return _record_rejection(
            state,
            reasons=[
                ClarifyReason(code=REASON_LEDGER_NOTES_SLOT_MISMATCH, reason=reason)
            ],
            title_reason=TEXT_SLOT_MISMATCH_TITLE.format(ids=ids),
            error_text=reason,
            first_free=False,
            emission_payload=emission_payload,
        )
    state.question_group = group.as_payload()
    state.precondition_verdicts = []
    state.rounds = int(state.rounds) + 1
    record_step(
        state,
        kind=STEP_DECISION,
        title=STEP_TITLE_DECOMPOSE.format(
            round=int(state.rounds), count=len(group.subtasks)
        ),
        payload={PAYLOAD_PHASE: PHASE_CLARIFY, PAYLOAD_EMISSION: emission_payload},
    )
    note(
        state,
        phase=NOTE_PHASE,
        title=NOTE_TITLE,
        digest=STEP_TITLE_DECOMPOSE.format(round=int(state.rounds), count=len(group.subtasks)),
    )
    _ship_decision_note(state, emission)
    set_intent(state, INTENT_TOOLMATCH)
    return ClarifyFinal(subtasks=list(group.subtasks))


@dataclass(frozen=True, slots=True)
class _SlotMismatch:
    """槽位对账诊断单条（段名／段值／不过原因／台账相关行——拒因文案四槽）。"""

    segment: str
    value: str
    cause: str
    row: str


def _note_slot_mismatch(
    note_text: str,
    *,
    registry: Mapping[str, str],
    injection_block: str,
) -> _SlotMismatch | None:
    """三段槽位对账（行为 8 的判据面；**形态处理豁免面**——闭世界集合成员校＋日期形解析，
    零语义词表、零正则、零语义改写）。

    段位次固定「槽位｜绑定态｜窗」（分隔符全角「｜」）：**段数非三 → 拒**（段名「段数」，
    值＝原形）；否则逐段对账——

    ①**槽位**（段一）须**逐字** ∈ 台账名录（`registry` 的键集——指标/对象/关系/术语四类名；
      exact membership，无语义匹配）——不在名录（含名录制空＝空投影的 fail-closed 面）即拒；
    ②**绑定态**（段二）须 ∈ `BINDING_STATES` 闭世界（照台账行「（绑定态：…）」中文形两值）；
    ③**窗**（段三）须为锚定窗（`date.fromisoformat(...[:10])`——窗形读法照
      `appv2/tools/precondition.py`，本块不新造窗面判据）或 `WINDOW_LITERALS` 字面之一
      （「窗未定」／同义形「无时间窗」——knowledge 链检索式问题无窗概念＝合法／双 null 发射形）。

    全过 → `None`；任一不过 → 返该段诊断（拒因文案据它指明「哪一段、哪个值、为什么」）。
    台账相关行＝槽位 exact-match 命中的投影行原文（从**注入块**内逐字取该行——模型所见同形）。
    """
    segments = _split_on(note_text, NOTE_SLOT_SEPARATOR)
    if len(segments) != len(NOTE_SEGMENTS):
        return _SlotMismatch(
            segment=NOTE_SEGMENT_COUNT,
            value=note_text,
            cause=CAUSE_SEGMENT_COUNT,
            row=NO_LEDGER_ROW_SHELL,
        )
    slot, binding, window = segments
    row_text = registry.get(slot)
    if row_text is None:
        return _SlotMismatch(
            segment=NOTE_SEGMENT_SLOT,
            value=slot,
            cause=CAUSE_SLOT_NOT_IN_LEDGER,
            row=NO_LEDGER_ROW_SHELL,
        )
    row = _ledger_row_line(injection_block, row_text)
    if binding not in BINDING_STATES:
        return _SlotMismatch(
            segment=NOTE_SEGMENT_BINDING,
            value=binding,
            cause=CAUSE_BINDING_OUT_OF_WORLD,
            row=row,
        )
    if not _window_legal(window):
        return _SlotMismatch(
            segment=NOTE_SEGMENT_WINDOW,
            value=window,
            cause=CAUSE_WINDOW_ILLEGAL,
            row=row,
        )
    return None


def _slot_mismatch_reason(offenders: list[tuple[str, _SlotMismatch]]) -> str:
    """槽位对账拒因文本（逐字稿＝流水 64 Owner 裁）：头行＋逐子问题三行块＋尾行。

    头行列全部 offender id；每个 offender 一块（【拒因】／【期望形】／【台账相关行】——
    程序已知事实说全、零模型调用）；尾行「——修正后重新输出 JSON。」恒在。
    """
    blocks = [
        TEXT_SLOT_MISMATCH_BLOCK.format(
            id=subtask_id,
            segment=diagnostic.segment,
            value=diagnostic.value,
            cause=diagnostic.cause,
            row=diagnostic.row,
        )
        for subtask_id, diagnostic in offenders
    ]
    return TEXT_JOIN.join(
        [
            TEXT_SLOT_MISMATCH_HEAD.format(
                ids=EMPTY_PROBES_JOIN.join(subtask_id for subtask_id, _ in offenders)
            ),
            *blocks,
            TEXT_SLOT_MISMATCH_TAIL,
        ]
    )


def _split_on(text: str, separator: str) -> list[str]:
    """按字面分隔符切段（`str.find` 手切——本块源码禁用 `split`／`partition` 族方法词面）。

    无分隔符 → 单段原样；分隔符出现 n 次 → n+1 段（**不丢空段**：`a｜｜c`＝三段含空串段，
    空段照判——段值与段数皆为拒因事实面）。
    """
    parts: list[str] = []
    start = 0
    while (index := text.find(separator, start)) >= 0:
        parts.append(text[start:index])
        start = index + len(separator)
    parts.append(text[start:])
    return parts


def _ledger_row_line(injection_block: str, row_text: str) -> str:
    """台账整行原文（注入块内**逐字**取行：以投影行 `value` 串为锚，扩到行界）。

    投影行渲染进常驻块时值串直取零改写，故块内命中即模型所见原行；块缺位或块内求不得
    （投影与块不同源等异常态）→ 退回行原文本身（不编造、不空手）。
    """
    if not injection_block or not row_text:
        return row_text
    start = injection_block.find(row_text)
    if start < 0:
        return row_text
    head = injection_block.rfind(TEXT_JOIN, 0, start)
    tail = injection_block.find(TEXT_JOIN, start)
    return injection_block[head + 1 : tail if tail >= 0 else len(injection_block)]


def _window_legal(window: str) -> bool:
    """窗段合法形（锚定窗＋`WINDOW_LITERALS` 闭世界面：ISO~ISO 锚定窗／「窗未定」／
    同义形「无时间窗」／双 null 发射形）。"""
    if window in WINDOW_LITERALS:
        return True
    bounds = _split_on(window, WINDOW_SEPARATOR)
    if len(bounds) != WINDOW_SEGMENT_TOTAL:
        return False
    return all(_is_iso_day(bound) for bound in bounds)


def _is_iso_day(text: str) -> bool:
    """ISO 日形判定（读法照 `appv2/tools/precondition.py` 的窗形：`[:10]` 截读＋
    `date.fromisoformat`——非日期形串即假；本块不新造日期形判据）。"""
    try:
        date.fromisoformat(text[: len(ISO_DAY_SHAPE)])
    except ValueError:
        return False
    return True


def _on_finalize(state: RunState, emission: ClarifyEmission) -> ClarifyOutcome:
    """`finalize`：**合法性闸**（前置合规，非 schema 违例）——零实质观察禁定稿（钉 `pin-05`）。

    窗内非 notice 实质观察数 ＝ 0 → 结构化拒因「零实质观察禁定稿」＋**三段带路**
    （行为 18：拒因载荷必带、零模型调用）回喂重决策、**不得直答收口**；合规 → 去向 `answer`
    （起草归作答相位，本块零干预）；发射注记非空时逐字出流为 `decision_note` 机读通知
    （行为 3「并注记」同款——注记出流与发射动作无关，只随 `note` 在场）。
    """
    emission_payload = emission.as_payload()
    if not _has_substantive_observation(state):
        guidance = rejection_guidance(state)
        return _record_rejection(
            state,
            reasons=[
                ClarifyReason(
                    code=REASON_FINALIZE_ZERO_OBSERVATION, reason=TEXT_ZERO_OBSERVATION
                ),
                ClarifyReason(code=REASON_REJECTION_GUIDANCE, reason=guidance),
            ],
            title_reason=TEXT_ZERO_OBSERVATION,
            error_text=f"{TEXT_ZERO_OBSERVATION}{GUIDANCE_JOIN}{guidance}",
            first_free=True,
            emission_payload=emission_payload,
        )
    record_step(
        state,
        kind=STEP_DECISION,
        title=STEP_TITLE_FINALIZE,
        payload={PAYLOAD_PHASE: PHASE_CLARIFY, PAYLOAD_EMISSION: emission_payload},
    )
    note(state, phase=NOTE_PHASE, title=NOTE_TITLE, digest=NOTE_DIGEST_FINALIZE)
    _ship_decision_note(state, emission)
    set_intent(state, INTENT_ANSWER)
    return None


def _has_substantive_observation(state: RunState) -> bool:
    """窗内非 notice 实质观察 ≥1（行为 17：**纯结构计数**，属形态处理豁免面）。

    实质观察＝faq 命中卡／台账条目卡／检索片段；空手探查（未命中 notice／工具失败／零观察）
    不算数——判据＝观察的 `locator.kind` 非 `notice`（V1 `_zero_probe_block` 同式）。
    """
    for observation in state.observations:
        if not isinstance(observation, Mapping):
            continue
        locator = observation.get("locator")
        kind = locator.get("kind") if isinstance(locator, Mapping) else None
        if kind != NOTICE_LOCATOR_KIND:
            return True
    return False


def _on_ask(state: RunState, emission: ClarifyEmission) -> ClarifyOutcome:
    """`ask`：反问挂起（`ClarifyAsk`＋`pending_ask` 帧投影）；连续反问到顶 → 截断带材料直答。

    - **挂起**（未到顶）：`pending_ask`＝`{kind: clarify, prompt, options, detail: None}` 帧投影
      （挂起铁律：`ask` 帧之后照发 `done`——发帧归 `transport`／`orchestration`）；**不占轮**
      （等待不计轮、不计时；行为 12／14）。
    - **到顶**（行为 15／钉 `pin-15`）：连续反问计数＋1 达上限（上限值取 `state.budget.ask_cap`
      ——数值零复制）→ **截断＋带已取得材料如实直答**（`direct_answer` 收口）＋`clarify_capped`
      机读注记；**不静默**、不继续环。
    """
    emission_payload = emission.as_payload()
    round_no = int(state.rounds) + 1
    if _ask_count(state) + 1 >= int(state.budget.ask_cap):
        record_step(
            state,
            kind=STEP_DECISION,
            title=STEP_TITLE_CAPPED.format(round=round_no),
            payload={
                PAYLOAD_PHASE: PHASE_CLARIFY,
                PAYLOAD_EMISSION: emission_payload,
                PAYLOAD_CAPPED: True,
            },
        )
        notice(
            state,
            type=NOTICE_CLARIFY_CAPPED,
            content=CAPPED_NOTICE_TEMPLATE.format(cap=int(state.budget.ask_cap)),
        )
        note(
            state,
            phase=NOTE_PHASE,
            title=NOTE_TITLE,
            digest=CAPPED_NOTE_DIGEST.format(cap=int(state.budget.ask_cap)),
        )
        direct_answer(state, _capped_answer(state))
        return None
    frame: dict[str, Any] = {
        "kind": ASK_KIND_CLARIFY,
        "prompt": emission.ask_prompt,
        "options": list(emission.ask_options),
        "detail": ASK_FRAME_DETAIL_NONE,
    }
    state.pending_ask = frame
    record_step(
        state,
        kind=STEP_DECISION,
        title=STEP_TITLE_ASK.format(
            round=round_no, prompt=emission.ask_prompt[:STEP_TITLE_PROMPT_CHARS]
        ),
        payload={
            PAYLOAD_PHASE: PHASE_CLARIFY,
            PAYLOAD_EMISSION: emission_payload,
            PAYLOAD_ASK_FRAME: frame,
        },
    )
    note(state, phase=NOTE_PHASE, title=NOTE_TITLE, digest=NOTE_DIGEST_ASK)
    set_intent(state, INTENT_DECISION)
    return ClarifyAsk(prompt=emission.ask_prompt, options=list(emission.ask_options))


def _ask_count(state: RunState) -> int:
    """连续反问计数（行为 15 的用量面）：run 生命期内**已发射的 ask** 计步数。

    计数载体＝本块 ask 支落的步记录（payload 携 ask 帧标记 `PAYLOAD_ASK_FRAME`）——`consecutive_asks`
    状态字段已随「流水 49①」取消（上限改由 `Budget` 「连续反问上限」键承载），故计数**现取**
    自只追加的步记录；「run 生命期内计数、任何路径不清零」＝防环语义
    （真源 `arch/P5a2` A-P5a2-01／`recon/K` R-K-77）。到顶截断支**不落 ask 帧标记**
    （V1 事实面：截断不增计数）。
    """
    total = 0
    for record in state.steps:
        payload = record.get("payload")
        if isinstance(payload, Mapping) and payload.get(PAYLOAD_ASK_FRAME):
            total += 1
    return total


def _capped_answer(state: RunState) -> str:
    """到顶截断的直答正文（行为 15：带已取得材料如实交付；零材料走如实壳）。"""
    rows = _material_rows(state)
    if not rows:
        return NO_MATERIAL_SHELL
    body = "\n".join(
        f"{MATERIAL_ROW_PREFIX}{_content_of(row)}" for row in rows
    )
    return f"{CAPPED_ANSWER_HEADER}\n{body}"


def _material_rows(state: RunState) -> list[Mapping[str, Any]]:
    """材料面（收敛口径同源）：已入栈观察＋末次工具结果自带观察（V1 `material_rows` 同式）。

    逐条不重排、不去重、不裁剪（「逐条如实交付」）；非映射行（旧检查点残形）不计。
    """
    rows: list[Mapping[str, Any]] = [
        row for row in state.observations if isinstance(row, Mapping)
    ]
    last_result = state.last_result
    if isinstance(last_result, Mapping):
        carried = last_result.get("observations")
        if isinstance(carried, list):
            rows.extend(row for row in carried if isinstance(row, Mapping))
    return rows


def _content_of(row: Mapping[str, Any]) -> str:
    """材料正文（缺键／非串如实空串——不加工、不改写）。"""
    value = row.get("content")
    return value if isinstance(value, str) else ""
