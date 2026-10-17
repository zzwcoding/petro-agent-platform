"""组合图装配与路由表（H2）——**一处集中**：节点注册、条件边、路由表都在本模块。

规格原文（`specs/agent-loop.md:155`）：「**组合图装配与路由表（H2）**：节点注册、条件边、路由表
在本块**一处集中**——**业务相位不得自行决定跳转**」。三条纪律：

1. **图状态＝`RunState` 自有 dataclass 全字段**（`StateGraph(RunState)`；**无 reducer／无通道
   并入**——框架只当 schema 消费，节点就地改同一状态对象后返回空更新；框架类型不出本模块）；
2. **路由＝意图字段 ＋ 本模块的映射表**：`_route` 只读 `state.next_intent`（`bookkeeping.set_intent`
   是唯一写口），`_ROUTES` 是「当前节点 × 意图 → 下一节点」的集中映射——相位侧零跳转决策；
3. **节点＝薄适配层**：每个节点只做「调相位公开入口 → 把返回位翻译成路由意图 → 落帧」三件事，
   业务语义一律在相位块内（本块不复制其判据、不做语义判断）。

入边（`START`）是**条件入口**：新 run 从 `understand` 进；挂起恢复按 `state.pending_ask.kind`
回原节点（clarify 反问 → 澄清入口；越集审批 → 前置条件机重判；工具缺参 → 批量执行入口）——
恢复面不新起第二套形状，只选入口。
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Hashable, Mapping, Sequence
from dataclasses import dataclass, field, fields
from datetime import date
from typing import Any

from langgraph.graph import END, START, StateGraph

from appv2.runtimev2.answering import answer
from appv2.runtimev2.bookkeeping import converge, set_intent
from appv2.runtimev2.clarification import ClarifyAsk, ClarifyFinal, clarify
from appv2.runtimev2.clarification.constants import PAYLOAD_ASK_FRAME
from appv2.runtimev2.context import DEFAULT_MAX_OBSERVATIONS
from appv2.runtimev2.execution import ERROR_BAD_ARGS, ERROR_RETRYABLE, execute
from appv2.runtimev2.orchestration.constants import (
    ASK_KEY_DETAIL,
    ASK_KEY_KIND,
    ASK_KEY_OPTIONS,
    ASK_KEY_PROMPT,
    DRAFT_KIND_DIRECT,
    EVENT_ASK,
    EVENT_NOTICE,
    EVENT_STEP,
    EVENT_SUPPLEMENT,
    EVENT_TEXT,
    NODE_ANSWER,
    NODE_BATCH,
    NODE_CLARIFY,
    NODE_DISCOVER,
    NODE_PRECONDITION,
    NODE_TOOLMATCH,
    NODE_UNDERSTAND,
    NODE_VERIFY,
    PAYLOAD_SEQ_KEY,
    PAYLOAD_STEP_KEY,
    PAYLOAD_TEXT_CONTENT_KEY,
    PAYLOAD_TITLE_KEY,
    assert_frame_names,
)
from appv2.runtimev2.parsing import Understanding
from appv2.runtimev2.preconditions import (
    DECISION_ALLOW,
    DECISION_ASK,
    FRAME_KIND_BY_ASK_KIND,
    PAYLOAD_DECISION_KEY,
    AskReason,
    SubtaskVerdict,
    gate_all,
)
from appv2.runtimev2.prompts import PHASE_CLARIFY
from appv2.runtimev2.state import (
    INTENT_ANSWER,
    INTENT_BATCH,
    INTENT_DECISION,
    INTENT_DISCOVER,
    INTENT_END,
    INTENT_PRECONDITION,
    INTENT_TOOLMATCH,
    INTENT_VERIFY,
    RUN_WAITING_ASK,
    RunState,
    check_limits,
)
from appv2.runtimev2.tool_matching import ToolMatchRejection, match
from appv2.runtimev2.transport import EventBus
from appv2.runtimev2.understanding import interpret
from appv2.runtimev2.verification import verify
from appv2.tools import ToolRegistry

# ── 路由表（H2 的唯一真源）：当前节点 → {意图 → 下一节点} ────────────────────────
_ROUTES: dict[str, dict[Hashable, str]] = {
    NODE_UNDERSTAND: {
        INTENT_DECISION: NODE_CLARIFY,  # 完整流程 → 四相位第一相位
        INTENT_ANSWER: NODE_ANSWER,  # 直答（route=direct 的收口旁路）
        INTENT_END: END,
    },
    NODE_CLARIFY: {
        INTENT_DECISION: NODE_CLARIFY,  # 拒因回喂自环／澄清回收再决策
        INTENT_DISCOVER: NODE_DISCOVER,  # 钻取（不占轮、受发现预算闸）
        INTENT_TOOLMATCH: NODE_TOOLMATCH,
        INTENT_PRECONDITION: NODE_PRECONDITION,  # 审批恢复重判入口
        INTENT_ANSWER: NODE_ANSWER,  # 到顶截断／全拒直答
        INTENT_END: END,
    },
    NODE_DISCOVER: {
        INTENT_DECISION: NODE_CLARIFY,  # 观察回流后回决策（模型自主再轮或分解）
        INTENT_BATCH: NODE_BATCH,
        INTENT_ANSWER: NODE_ANSWER,
        INTENT_END: END,
    },
    NODE_TOOLMATCH: {
        INTENT_TOOLMATCH: NODE_TOOLMATCH,  # 匹配拒因回喂自环
        INTENT_PRECONDITION: NODE_PRECONDITION,
        INTENT_ANSWER: NODE_ANSWER,
        INTENT_END: END,
    },
    NODE_PRECONDITION: {
        INTENT_BATCH: NODE_BATCH,  # 放行支批量执行
        INTENT_DECISION: NODE_CLARIFY,  # 换链回炉（回①澄清改链重决策）
        INTENT_ANSWER: NODE_ANSWER,
        INTENT_END: END,
    },
    NODE_BATCH: {
        INTENT_DECISION: NODE_CLARIFY,  # 失败子集回炉①（占一轮）
        INTENT_ANSWER: NODE_ANSWER,
        INTENT_END: END,
    },
    NODE_VERIFY: {
        INTENT_ANSWER: NODE_ANSWER,  # 核验后回作答相位收口
        INTENT_END: END,
    },
    NODE_ANSWER: {
        INTENT_VERIFY: NODE_VERIFY,  # 起草后交核验
        INTENT_ANSWER: NODE_ANSWER,
        INTENT_END: END,  # 收口（引用块＋citation 帧＋链尾同批）
    },
}

RESUME_ENTRY_BY_ASK_KIND: dict[str, str] = {
    "clarify": NODE_CLARIFY,
    "external_table_approval": NODE_PRECONDITION,
}


@dataclass(slots=True)
class LoopDeps:
    """图运行依赖（编排块持有、随图注入——相位侧签名实参形一律不改）。"""

    bus: EventBus
    registry: ToolRegistry
    store: Any  # persistence.RunStore（大结果引用载体）
    window_candidates: Sequence[str] | None = None
    watermark: date | None = None
    data_wells: Collection[str] | None = None
    # §A 指南段全文（流水 63）：相位侧 `clarify`／`match` 的文本注入参——装配面（启动快照）
    # 归 api 组合根，本块只经 `deps` 下传（缺省空串＝空段头）。**落链次数归本块**（2026-10-17
    # 补·真机消重批）：随 `_shared_context_pending` 的判定同 §A 段与台账常驻块一并只注一次。
    guide_text: str = ""
    max_observations: int = DEFAULT_MAX_OBSERVATIONS
    emitted_steps: int = field(default=0)
    emitted_notices: int = field(default=0)
    # 增补面收集列表（2026-10-17 EB3 D2）：相位（`verification`／`answering`）把程序追加块
    # （分源／归属／引用／血缘）按产出序入列，**帧由本块收口处发射**（EB3 D1 的发射点）。列表
    # 由本块持有（执行器逐腿建；相位侧只追加、不读状态、不发帧）。
    supplements: list[dict[str, Any]] = field(default_factory=list)
    emitted_supplements: int = field(default=0)
    # 段内已用时读数（秒）：动作者＝组合根（受理腿取起点、`infra.clock` 读数差——B14 唯一时间出口；
    # 挂起等人工不计时、跨段不累计，故由组合根按腿现算）。无注入＝`None`（该键不判定）。
    elapsed_seconds: Callable[[], float] | None = None


def _flush_steps(deps: LoopDeps, state: RunState) -> None:
    """步帧发射（本块职责：`state.steps` 新增逐条发 `step` 帧——相位只写状态不发步帧）。"""
    new = state.steps[deps.emitted_steps :]
    for entry in new:
        if not isinstance(entry, dict):
            continue
        deps.bus.emit(
            EVENT_STEP,
            {
                PAYLOAD_STEP_KEY: entry.get("step", ""),
                PAYLOAD_SEQ_KEY: entry.get("seq", 0),
                PAYLOAD_TITLE_KEY: entry.get("title", ""),
            },
        )
    deps.emitted_steps = len(state.steps)


def _updates_of(state: RunState) -> dict[str, Any]:
    """节点返回面＝**全部通道字段的现值**（框架只当 schema 消费——无 reducer／无通道并入）。

    LangGraph 的 dataclass schema 下，节点拿到的是**按通道值重建的状态对象**：列表字段
    （`steps`／`messages`／…）因共享同一列表对象而「就地追加可见」，而**标量字段的重新绑定
    （`state.next_intent = …`）会被丢弃**。故本块的节点一律把当前全字段作为更新交回框架——
    语义＝「就地改、整份交回」，既是本块唯一的通道形态，也免去「哪些字段能就地改」的隐式清单。
    """
    return {field.name: getattr(state, field.name) for field in fields(state)}


def _flush_notices(deps: LoopDeps, state: RunState) -> None:
    """通知帧发射（本块职责：相位只经唯一写口落 `state.notices`、**帧面归本块**）。

    例外＝`verification`：该相位自产 `notice` 帧（其规格「通知双落」），故核验节点在调用后
    把已发计数对齐，避免同一通知出两帧。
    """
    for entry in state.notices[deps.emitted_notices :]:
        if not isinstance(entry, dict):
            continue
        deps.bus.emit(EVENT_NOTICE, dict(entry))
    deps.emitted_notices = len(state.notices)


def _flush_supplements(deps: LoopDeps) -> None:
    """增补面帧发射（2026-10-17 EB3 D1／D2——**编排收口处一处发**）。

    相位侧只把程序追加块（`{block, text}`）按产出序入 `deps.supplements`；帧面归本块，
    在作答收口（`verification` 改写后的 draft 定稿）之后逐条发 `supplement`。跨腿只发本腿
    新增（`emitted_supplements` 计数——恢复腿重入不重发旧条目）。载荷定形与块型闭世界由
    `transport` 构造期把守（**越界即抛错、不静默丢弃**——故本处不做条目形态过滤，缺陷照实爆）。
    """
    for entry in deps.supplements[deps.emitted_supplements :]:
        deps.bus.emit(EVENT_SUPPLEMENT, dict(entry))
    deps.emitted_supplements = len(deps.supplements)


def _ask_frame(
    kind: str, prompt: str, options: Sequence[str], detail: dict[str, Any]
) -> dict[str, Any]:
    """ask 帧形状（真源 `synth/S6` §一 ask 行——`{kind, prompt, options, detail}` 四键齐备）。"""
    return {
        ASK_KEY_KIND: kind,
        ASK_KEY_PROMPT: prompt,
        ASK_KEY_OPTIONS: [str(item) for item in options],
        ASK_KEY_DETAIL: dict(detail),
    }


def _suspend(state: RunState, deps: LoopDeps, frame: dict[str, Any]) -> None:
    """挂起：`pending_ask` 落帧投影 ＋ 状态转 `waiting_ask` ＋ 发 `ask` 帧 ＋ 收束本腿。

    挂起铁律（`specs/transport.md` 行为 8）：`ask` 帧之后照发 `done`——`done` 由开流段（`api`）
    发；本块只保证挂起态与 `ask` 帧同批落定。
    """
    state.pending_ask = dict(frame)
    state.status = RUN_WAITING_ASK
    set_intent(state, INTENT_END)
    deps.bus.emit(EVENT_ASK, {"frame": dict(frame), "run_id": state.run_id})


def _precondition_frame(state: RunState, verdict: SubtaskVerdict) -> dict[str, Any]:
    """前置条件机 `ask` 支 → ask 帧（`AskReason.kind` → `frame.kind` 用相位侧唯一映射表）。"""
    reason = verdict.reason
    if not isinstance(reason, AskReason):
        raise ValueError("前置条件机 ask 支缺 AskReason（相位契约违例——fail-closed）")
    kind = FRAME_KIND_BY_ASK_KIND[reason.kind]
    detail: dict[str, Any] = {}
    if kind != "clarify" and reason.kind == "external_table_approval":
        detail = {
            "approval_id": f"precond-{verdict.subtask_id}",
            "tables": _external_tables_of(state, verdict.subtask_id),
        }
    return _ask_frame(kind, reason.prompt, reason.options, detail)


def _external_tables_of(state: RunState, subtask_id: str) -> list[str]:
    """越集外表名集（比对面：`tool_matches[sid].plan.external_tables`——原样取，缺位空集）。"""
    for item in state.tool_matches:
        if not isinstance(item, dict) or str(item.get("id") or "") != subtask_id:
            continue
        plan = item.get("plan")
        if not isinstance(plan, dict):
            return []
        return [str(name) for name in (plan.get("external_tables") or ()) if str(name).strip()]
    return []


# ── 八节点（薄适配：调相位 → 翻路由意图 → 落帧）────────────────────────────────


def _make_understand(deps: LoopDeps) -> Any:
    async def node(state: RunState) -> dict[str, Any]:
        result = interpret(state, bus=deps.bus, watermark=_watermark_text(deps))
        if isinstance(result, Understanding):
            set_intent(state, INTENT_DECISION)  # 完整流程 → 四相位第一相位
        # `Direct` 分派已由相位经 `bookkeeping.direct_answer` 落 `next_intent=answer`。
        _flush_notices(deps, state)
        _flush_steps(deps, state)
        return _updates_of(state)

    return node


# 预算闸入口的判定键集（行为 7）：轮数／段时长／连续反问三闸在本入口收敛。
# 发现／执行两键（`discovers_per_round`／`executes_per_round`／`discovers_per_run`）的用量面属
# **发射级拒因回喂**（相位侧报价拒＋回炉占轮——`clarification` 的发现预算闸与 `execution` 的空手
# 探查闸），其用量到顶**不等于**本 run 该收敛（仍可回炉／换链／作答交付），故不进本入口收敛面。
_ENTRY_LIMIT_KEYS: frozenset[str] = frozenset({"rounds", "seconds", "ask_cap"})


def _make_clarify(deps: LoopDeps) -> Any:
    async def node(state: RunState) -> dict[str, Any]:
        # 预算闸入口（行为 7「触界即收敛」）：本入口判**三闸**——轮数／段时长／连续反问（时长与连续
        # 反问的用量不在状态形状内，由组合根注入；判定归 `state.check_limits`，本块不复制其判据与
        # 数值）。命中即**触界收敛**（材料如实交付＋ notice——行为 7／「触界不得静默」）：落地归
        # `bookkeeping.converge`（含命中项分叉注记），不再发起模型调用（免无界自旋；拒因回喂与失败
        # 子集回炉两路都经本入口收敛）。发现／执行两键的用量面由相位侧拒因回喂机理管（本入口不收敛，
        # 见 `_ENTRY_LIMIT_KEYS`）。
        elapsed = None if deps.elapsed_seconds is None else deps.elapsed_seconds()
        asks = _consecutive_asks(state)
        convergence = check_limits(state, elapsed_seconds=elapsed, consecutive_asks=asks)
        if any(hit.limit in _ENTRY_LIMIT_KEYS for hit in convergence.hit):
            converge(state, elapsed_seconds=elapsed, consecutive_asks=asks)
            set_intent(state, INTENT_ANSWER)
            _flush_notices(deps, state)
            _flush_steps(deps, state)
            return _updates_of(state)
        outcome = clarify(
            state,
            guide_text=deps.guide_text,
            shared_context=_shared_context_pending(state),
        )
        if isinstance(outcome, ClarifyAsk):
            _suspend(
                state,
                deps,
                _ask_frame(outcome.kind, outcome.prompt, outcome.options, {}),
            )
        elif isinstance(outcome, ClarifyFinal):
            set_intent(state, INTENT_TOOLMATCH)
        # `ClarifyRejection`／`None` 两形的意图由相位经 `set_intent` 交出（回喂／钻取／截断）。
        _flush_notices(deps, state)
        _flush_steps(deps, state)
        return _updates_of(state)

    return node


def _consecutive_asks(state: RunState) -> int:
    """连续反问计数（`ask_cap` 键用量）：**口径照澄清相位既有实现**（`clarification._ask_count`
    ——run 生命期内**已发射的 ask** 计步数，计数载体＝步记录 payload 携 ask 帧标记
    `PAYLOAD_ASK_FRAME`；「run 生命期内计数、任何路径不清零」＝防环语义，真源 `recon/K` R-K-77）。

    本处只按同一口径数数，**不新造计数载体**（`consecutive_asks` 状态字段已随流水 49① 取消，
    键名与上限值归 `state.Budget`）。非映射行／缺 payload 行如实不计。
    """
    total = 0
    for entry in state.steps:
        if not isinstance(entry, dict):
            continue
        payload = entry.get("payload")
        if isinstance(payload, Mapping) and payload.get(PAYLOAD_ASK_FRAME):
            total += 1
    return total


def _shared_context_pending(state: RunState) -> bool:
    """本 run 的**共享上下文**（§A 指南段＋台账常驻块）是否尚未注入——决策装配的下传判定。

    判据＝**澄清相位首入包尚未落链**（`state.contracts_appended` 的相位标记，pin-24 记账面）：
    澄清相位是四相位决策链的首站，其首入包即共享上下文在**本 run 的唯一挂载点**。已落 → 本次
    不注（`shared_context=False`）：链为追加形（pin-22），模型从链首可见前文，语义零损失；重复
    注入的两份＝纯重复 token（真机 `docs/runtime-refactor/ladder/L3/07` run-919ed881：末轮 answer
    prompt 19359 tokens 里 §A 与台账全量块各两遍）。

    **判定落在本块**（「只注一次」的判定／下传归编排；`prompts` 只按标志拼文本——装配面与注入
    面的分工，`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W5 行注）；消重**不动任何
    已有消息**，两段文本字节级不变（只改出现次数）。
    """
    return PHASE_CLARIFY not in state.contracts_appended


def _make_discover(deps: LoopDeps) -> Any:
    async def node(state: RunState) -> dict[str, Any]:
        outcome = execute(state, bus=deps.bus, registry=deps.registry, store=deps.store)
        if state.pending_ask:
            state.status = RUN_WAITING_ASK
            set_intent(state, INTENT_END)
        elif outcome.subtasks:
            set_intent(state, _route_after_batch(state))
        else:
            set_intent(state, INTENT_DECISION)  # 观察回流 → 回决策（模型自主再轮）
        _flush_notices(deps, state)
        _flush_steps(deps, state)
        return _updates_of(state)

    return node


def _make_toolmatch(deps: LoopDeps) -> Any:
    async def node(state: RunState) -> dict[str, Any]:
        # run 级共享上下文（§A 指南段＋台账常驻块）只注一次——本相位是同一 run 的第二次决策
        # 装配，澄清轮首入包已注时本次整段缺席（判定＝`_shared_context_pending`）。
        outcome = match(
            state,
            guide_text=deps.guide_text,
            shared_context=_shared_context_pending(state),
        )
        if isinstance(outcome, ToolMatchRejection):
            set_intent(state, INTENT_TOOLMATCH)  # 拒因回喂自环（`decision_error` 由相位写）
        else:
            # 相位②产物落状态（工具匹配支投影——`SubtaskMatch.as_payload`；下游三块按
            # `state.tool_matches` 取支：前置条件机闭世界、批量执行辖域、作答排名判据）。
            state.tool_matches = [item.as_payload() for item in outcome.matches]
            set_intent(state, INTENT_PRECONDITION)
        _flush_notices(deps, state)
        _flush_steps(deps, state)
        return _updates_of(state)

    return node


def _make_precondition(deps: LoopDeps) -> Any:
    async def node(state: RunState) -> dict[str, Any]:
        marks_before = len(state.chain_switch_marks)
        verdicts = gate_all(
            state,
            window_candidates=deps.window_candidates,
            watermark=deps.watermark,
            data_wells=deps.data_wells,
        )
        # 换链回炉判定＝**计点是否新落**（相位侧「一次为界」的簿记面：首次触发落一笔
        # `chain_switch_marks`，第二次同参起相位侧自行转终局拒答——本块只按有无新计点路由）。
        reentry = len(state.chain_switch_marks) > marks_before
        for verdict in verdicts:
            if verdict.decision == DECISION_ASK:
                _suspend(state, deps, _precondition_frame(state, verdict))
                break
        else:
            set_intent(state, _route_after_precondition(state, reentry=reentry))
        _flush_notices(deps, state)
        _flush_steps(deps, state)
        return _updates_of(state)

    return node


def _make_batch(deps: LoopDeps) -> Any:
    async def node(state: RunState) -> dict[str, Any]:
        execute(state, bus=deps.bus, registry=deps.registry, store=deps.store)
        if state.pending_ask:
            state.status = RUN_WAITING_ASK
            set_intent(state, INTENT_END)
        else:
            set_intent(state, _route_after_batch(state))
        _flush_notices(deps, state)
        _flush_steps(deps, state)
        return _updates_of(state)

    return node


def _make_answer(deps: LoopDeps) -> Any:
    async def node(state: RunState) -> dict[str, Any]:
        answer(
            state,
            bus=deps.bus,
            max_observations=deps.max_observations,
            supplements=deps.supplements,
        )
        _emit_direct_text(deps, state)
        # 增补面收口发射（EB3 D1／D2）：作答收口后（核验改写后的 draft 已定稿）逐条发帧——
        # 本 run 全部四类块在此处一次出流（verification 与 answering 的产出同列按原序）。
        _flush_supplements(deps)
        _flush_notices(deps, state)
        _flush_steps(deps, state)
        return _updates_of(state)

    return node


def _emit_direct_text(deps: LoopDeps, state: RunState) -> None:
    """直答旁路收口后的交付正文帧（一帧）——免起草旁路的 text 帧面单点。

    直答旁路（`route="direct"` 直答／拒答／闸拒／收敛转答——`bookkeeping.direct_answer` 与
    `converge` 同落 `draft_kind="direct"`）**免起草**：本块下游 `answering` 的 text 帧只在**起草段**
    发（一段一帧），收口段只发 `citation` 帧——故该旁路的交付正文在流上**零 text 帧**，用户端读到
    空（真机证据 `docs/runtime-refactor/ladder/L0/01`：六帧无 text、runs 读口无答案正文）。

    补发规则（本处＝编排面收口之后、`answer` 步各路径共用）：
    - **判据只认 `draft_kind="direct"`**——起草路径（`draft_kind=""`）的帧面归 `answering` 起草段，
      本处零动作（不重复推、顺序不变）；
    - 一帧一正文，content＝交付正文（`state.draft`，收敛转答形回退 `state.answer`）；帧形照
      `answering` 起草段＝`{content}` **不带 kind**（`kind="understanding"` 是理解步专名——本处
      不新造第二值）；
    - 正文为空（空稿收口）→ **不发空帧**（同 `answering` 行为 9「不推空答案」）。
    """
    if state.draft_kind != DRAFT_KIND_DIRECT:
        return
    text = str(state.draft or state.answer)
    if not text.strip():
        return
    deps.bus.emit(EVENT_TEXT, {PAYLOAD_TEXT_CONTENT_KEY: text})


def _make_verify(deps: LoopDeps) -> Any:
    async def node(state: RunState) -> dict[str, Any]:
        verify(state, bus=deps.bus, supplements=deps.supplements)
        deps.emitted_notices = len(state.notices)  # 本相位自产 notice 帧（不重复出帧）
        _flush_steps(deps, state)
        return _updates_of(state)

    return node


# ── 路由判据（两处「该不该回炉」的机械面——判据只读状态，不做语义判断）──────────


def _route_after_precondition(state: RunState, *, reentry: bool) -> str:
    """前置条件机之后：换链回炉待办 → 回①澄清（占一轮）；放行支非空 → 批量执行；全拒 → 收口。"""
    if reentry:
        return INTENT_DECISION
    allowed = [
        item
        for item in state.precondition_verdicts
        if isinstance(item, dict)
        and item.get(PAYLOAD_DECISION_KEY) == DECISION_ALLOW
    ]
    return INTENT_BATCH if allowed else INTENT_ANSWER


def _route_after_batch(state: RunState) -> str:
    """批量执行之后：批次含**重跑档**失败支且在轮预算内 → 回炉①；轮预算用尽 → 作答收口（流水 59）。

    回炉判据＝批次含 `bad_args`（参数错——修参回炉）／`retryable`（超时／上游抖动／限流——
    只重跑此档）支（真源＝execution 失败分类闭世界 `ERROR_CATEGORIES`，字面经 `execution` 包根
    引；与 `prompts.decision_round` 的回炉条判据同档，R1／R3 隔断其互引故两处各持字面）。全 `ok`
    与**全 `refused`**（前置闸拒＝终局不回炉、回炉条为空）两形皆直落作答收口——`refused` 的拒因
    面由 answering 降级簇如实交付；旧「非 ok 即回炉」判据令全 `refused` 批次白烧一轮澄清。
    """
    reworkable = [
        item
        for item in state.subtask_results
        if isinstance(item, dict)
        and str(item.get("status") or "") in (ERROR_BAD_ARGS, ERROR_RETRYABLE)
    ]
    if reworkable and int(state.rounds) < int(state.budget.rounds):
        return INTENT_DECISION
    return INTENT_ANSWER


def _watermark_text(deps: LoopDeps) -> str:
    """水位注入形（`understanding.interpret` 收 isoformat 串；无水位＝空串注入）。"""
    return deps.watermark.isoformat() if isinstance(deps.watermark, date) else ""


# ── 装配 ─────────────────────────────────────────────────────────────────────


def _route(state: RunState) -> str:
    """条件边的唯一判据：读唯一写口写的 `next_intent`（未设态兜底＝作答收口）。"""
    return state.next_intent or INTENT_ANSWER


def _entry(state: RunState) -> str:
    """入口判据（`START` 条件边）：挂起恢复按 ask 帧 `kind` 回原节点，新 run 进读题。

    恢复面**不新起第二套形状**，只选入口（挂起帧 `kind` → 入口的映射表＝
    `RESUME_ENTRY_BY_ASK_KIND`）。判形取值两处（帧在场优先，帧已被受理段消费时取
    `resume_choices` 末条）：澄清回收帧由澄清相位自消费（故帧留场），越集审批帧在受理段即
    消费完毕（`approved_ids` 落定）——两种情形都要能选对入口。
    """
    kind = _resume_ask_kind(state)
    if kind is None:
        return NODE_UNDERSTAND
    entry = RESUME_ENTRY_BY_ASK_KIND.get(kind)
    return NODE_BATCH if entry is None else entry


def _resume_ask_kind(state: RunState) -> str | None:
    """恢复面的 ask `kind`（无恢复选择＝新 run，返 `None`）。"""
    if not state.resume_choices:
        return None
    frame = state.pending_ask if isinstance(state.pending_ask, dict) else {}
    kind = str(frame.get(ASK_KEY_KIND) or "")
    if kind:
        return kind
    pending_choice = state.resume_choices[-1]
    if isinstance(pending_choice, Mapping):
        return str(pending_choice.get(ASK_KEY_KIND) or "")
    return None


def _node_of(fn: Any) -> Any:
    """`add_node` 形参面（恒等转换——框架类型限制收口在此，运行时零行为差）。"""
    return fn


def build_graph(deps: LoopDeps, *, checkpointer: Any = None) -> Any:
    """编译四相位组合图（`StateGraph(RunState)`＋集中路由表；checkpointer 由调用方注入）。

    `four_phase` 不做开关：V2 只有一条链路（ADR-0005 四相位终态）——旧码的 legacy 七节点图
    随重写退役（本块不承载第二套装配）。
    """
    assert_frame_names()
    builder = StateGraph(RunState)
    builder.add_node(NODE_UNDERSTAND, _node_of(_make_understand(deps)))
    builder.add_node(NODE_CLARIFY, _node_of(_make_clarify(deps)))
    builder.add_node(NODE_DISCOVER, _node_of(_make_discover(deps)))
    builder.add_node(NODE_TOOLMATCH, _node_of(_make_toolmatch(deps)))
    builder.add_node(NODE_PRECONDITION, _node_of(_make_precondition(deps)))
    builder.add_node(NODE_BATCH, _node_of(_make_batch(deps)))
    builder.add_node(NODE_ANSWER, _node_of(_make_answer(deps)))
    builder.add_node(NODE_VERIFY, _node_of(_make_verify(deps)))
    builder.add_conditional_edges(
        START,
        _entry,
        {
            NODE_UNDERSTAND: NODE_UNDERSTAND,
            NODE_CLARIFY: NODE_CLARIFY,
            NODE_PRECONDITION: NODE_PRECONDITION,
            NODE_BATCH: NODE_BATCH,
        },
    )
    for name, mapping in _ROUTES.items():
        builder.add_conditional_edges(name, _route, mapping)
    return builder.compile(checkpointer=checkpointer)
