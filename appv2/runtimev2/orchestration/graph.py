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
from appv2.runtimev2.clarification import (
    ClarifyAsk,
    ClarifyFinal,
    clarify,
    object_ambiguity_ask,
)
from appv2.runtimev2.clarification.constants import (
    ASK_DETAIL_SLOT_KEY,
    ASK_SLOT_CALIBER,
    ASK_SLOT_WINDOW,
    PAYLOAD_ASK_FRAME,
)
from appv2.runtimev2.clarification.guidance import rejection_guidance
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
from appv2.runtimev2.orchestration.explore import hard_stop, run_explore
from appv2.runtimev2.orchestration.repair import run_repair
from appv2.runtimev2.orchestration.subjects import reflect_and_record
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
    INTENT_EXPLORE,
    INTENT_PRECONDITION,
    INTENT_REPAIR,
    INTENT_TOOLMATCH,
    INTENT_VERIFY,
    MAX_EXPLORE_ROUNDS,
    RUN_WAITING_ASK,
    Convergence,
    RunState,
    check_limits,
)
from appv2.runtimev2.tool_matching import ToolMatchRejection, match
from appv2.runtimev2.transport import EventBus
from appv2.runtimev2.understanding import interpret
from appv2.runtimev2.verification import verify
from appv2.tools import (
    HIT_RULE_FUZZY_WINDOW,
    ToolRegistry,
    metric_requires_subject,
    oilfield_instances,
    subject_candidates,
)

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
        # 回炉自环（V2-115——镜像 V2-96 explore 环）：核验标红 ⇒ 本节点入口先执行回炉
        # （`_make_verify` 入口的 `INTENT_REPAIR` 支）再复检重入核验。
        INTENT_REPAIR: NODE_VERIFY,
        INTENT_END: END,
    },
    NODE_ANSWER: {
        INTENT_VERIFY: NODE_VERIFY,  # 起草后交核验
        INTENT_ANSWER: NODE_ANSWER,
        INTENT_EXPLORE: NODE_ANSWER,  # 作答第二出口（V2-96 D5）：再探自环——执行后重入作答
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
    # 执行日时间量（V2-123——材料头「执行日」段与期错位比对的注入值；L0 裁定 D-g：
    # 时间量经注入参、`context` 不读时钟）。装配面＝组合根解析**一次** `today`
    # （eval＝`gateway_adapter.frozen_date`／生产＝`infra.clock`，B14）随 `RunExecutor` 下传；
    # 缺省空串＝材料头无「执行日」段（本批前行为零漂移）。
    execution_date: str = ""
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
    # 油田实例读缝（V2-82b——对象歧义门的数据源）：`Callable[[], Sequence[str]]`＝
    # `agg.dim_well.field_name` 现值集（生产＝`query.production_field_instances` 的 loader）。
    # 未注入＝门不出声（零漂移，同 `data_wells` 域闸的缺省纪律）；**现读**由读缝自身保证。
    field_instances: Callable[[], Sequence[str]] | None = None


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
    """ask 帧形状（真源 `synth/S6` §一 ask 行——`{kind, prompt, options, detail}` 四键齐备）。

    V2-118：槽位标签落 `detail` 内（键＝`ASK_DETAIL_SLOT_KEY`）——**顶层四键零增删**
    （`transport.frames._check_ask` 恰四键把守），故本函数签名不变，只由调用方把标签并入
    `detail`（零帧闭世界变更）。
    """
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
    """前置条件机 `ask` 支 → ask 帧（`AskReason.kind` → `frame.kind` 用相位侧唯一映射表）。

    V2-118：`detail` 携**槽位标签**（`ASK_DETAIL_SLOT_KEY`）——口径反问＝`ASK_SLOT_CALIBER`、
    时间窗反问（同 kind、命中位 2 结构判据）＝`ASK_SLOT_WINDOW`；外表越集审批帧＝既有
    `approval_id`／`tables` 两键（审批面的回答落位是 `approved_ids`，本票零改）。恢复腿据此把
    用户回答落进 `state.answer_slots` 对应槽位并回喂后续决策轮。
    """
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
    elif reason.kind == "caliber_clarify":
        # 口径反问与时间窗反问同为 `caliber_clarify` 一形（真源 `preconditions.core._window_ask`
        # 与 `appv2/tools/precondition.py` 的 AskFrame 两处发射点）——按 **hit_rule** 区分：
        # 位 2 结构判据（`HIT_RULE_FUZZY_WINDOW`）＝时间窗问；
        # 其余（`HIT_RULE_ASK` 口径反问）＝口径问。
        detail = {
            ASK_DETAIL_SLOT_KEY: (
                ASK_SLOT_WINDOW
                if verdict.hit_rule == HIT_RULE_FUZZY_WINDOW
                else ASK_SLOT_CALIBER
            )
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
# 轮数键名（`LimitHit.limit` 闭世界成员——真源 `state.LimitKind`；本处只作比较，不复述语义）——
# **零材料兜底轮**判据（2026-10-17 F2）按名取它，不另立第二套键名。
_LIMIT_ROUNDS = "rounds"
_ENTRY_LIMIT_KEYS: frozenset[str] = frozenset({_LIMIT_ROUNDS, "seconds", "ask_cap"})


def _make_clarify(deps: LoopDeps) -> Any:
    async def node(state: RunState) -> dict[str, Any]:
        # 预算闸入口（行为 7「触界即收敛」）：本入口判**三闸**——轮数／段时长／连续反问（时长与连续
        # 反问的用量不在状态形状内，由组合根注入；判定归 `state.check_limits`，本块不复制其判据与
        # 数值）。命中即**触界收敛**（材料如实交付＋ notice——行为 7／「触界不得静默」）：落地归
        # `bookkeeping.converge`（含命中项分叉注记），不再发起模型调用（免无界自旋；拒因回喂与失败
        # 子集回炉两路都经本入口收敛）。发现／执行两键的用量面由相位侧拒因回喂机理管（本入口不收敛，
        # 见 `_ENTRY_LIMIT_KEYS`）。
        # **零材料兜底轮**（2026-10-17 F2，判据见 `_material_round_due`）：到顶那一次若收敛只能出
        # 「未取得可交付材料」纯话术（本 run 零材料），则让位恰一轮——见该函数 docstring 的真机病灶。
        elapsed = None if deps.elapsed_seconds is None else deps.elapsed_seconds()
        asks = _consecutive_asks(state)
        convergence = check_limits(state, elapsed_seconds=elapsed, consecutive_asks=asks)
        if any(hit.limit in _ENTRY_LIMIT_KEYS for hit in convergence.hit):
            if not _material_round_due(state, convergence):
                converge(state, elapsed_seconds=elapsed, consecutive_asks=asks)
                set_intent(state, INTENT_ANSWER)
                _flush_notices(deps, state)
                _flush_steps(deps, state)
                return _updates_of(state)
            # 兜底轮：本入口**不收敛**（零模型调用之余也零落地），落到下方澄清相位——带着
            # `decision_error` 的拒因回喂重决策恰一次；材料到手后回本入口即收敛（带材料直答）。
        # 对象歧义门（V2-82b——流水 88 裁决⑥；V2-82 批 EB6 修 1 加程序候选回退）：**澄清 LLM 之前的
        # 程序判定点**——题面无主体 ∧ 术语/指标命中 ∧ 指标粒度要求主体 ∧ 系统内油田实例≥2 ⇒ 直接弹
        # ask（判据全归 `clarification.object_ambiguity_ask`，本块只做「调相位 → 挂起 → 收束」
        # 三件事；三件纯素材由本块绑定：grain 判据＝tools 纯函数、实例读面＝读缝 + 归一、
        # 程序候选读面＝tools 抽件 + 当场问句/投影〔问句读点在本块——门内零问句读点红线〕）。
        subject_ask = object_ambiguity_ask(
            state,
            grain_requires_subject=metric_requires_subject,
            subject_instances=_subject_instances(deps),
            program_subjects=_program_subjects(state),
        )
        if subject_ask is not None:
            _suspend(
                state,
                deps,
                _ask_frame(
                    subject_ask.kind, subject_ask.prompt, subject_ask.options, {}
                ),
            )
            _flush_notices(deps, state)
            _flush_steps(deps, state)
            return _updates_of(state)
        outcome = clarify(
            state,
            guide_text=deps.guide_text,
            shared_context=_shared_context_pending(state),
        )
        if isinstance(outcome, ClarifyAsk):
            # V2-118：**帧面沿用相位已落的投影**（`_on_ask` 把槽位标签写进 `pending_ask.detail`
            # ——`state.pending_ask` 即待挂起帧）；本块不再自建第二份帧（同源零漂移：槽位标签
            # 与「回答落进哪个状态位」按同一份帧对账）。缺位（相位未落）→ 照实空映射，不编造标签。
            frame = state.pending_ask
            _suspend(
                state,
                deps,
                frame if isinstance(frame, dict) else _ask_frame(
                    outcome.kind, outcome.prompt, outcome.options, {}
                ),
            )
        elif isinstance(outcome, ClarifyFinal):
            set_intent(state, INTENT_TOOLMATCH)
        # `ClarifyRejection`／`None` 两形的意图由相位经 `set_intent` 交出（回喂／钻取／截断）。
        _flush_notices(deps, state)
        _flush_steps(deps, state)
        return _updates_of(state)

    return node


def _subject_instances(deps: LoopDeps) -> Callable[[], Sequence[str]] | None:
    """油田实例名单读面（V2-82b 对象歧义门的数据源）——读缝 ＋ tools 侧归一的绑定。

    读缝（`deps.field_instances`——`agg.dim_well.field_name` 现值集）由组合根注入；归一
    （去空／去重保序／封顶）归 tools 侧 `subject_terms.oilfield_instances`（**判据不复制**，
    本块只按现有读口拼装）。读缝未接线＝`None` ⇒ 门不出声（同 `data_wells` 缺省纪律）。

    **调用时机**＝门内判据通过之后（每次调用现读、零缓存）——本处只交读面，不预取。
    """
    if deps.field_instances is None:
        return None
    face = deps.field_instances
    return lambda: oilfield_instances(face())


def _program_subjects(state: RunState) -> Callable[[], Sequence[str]]:
    """题面程序主体候选读面（V2-82 批 EB6 修 1 对象歧义门回退判据的数据源）。

    生产引用＝tools 包根 `subject_candidates`（确定性形态抽取，零模型零 I/O），**问句原文与台账
    投影的读点在本块**——澄清块（`clarification` 包）零问句读点与零工具面 import 两条红线都不破
    （`tests/domains/test_v2_clarification.py::test_no_ask_when_time_resolvable`／
    `::test_discover_routed_not_direct_call`）。

    **调用时机**＝门内 `state.subjects` 为空时（每次调用现算、零缓存）；投影取 `state.ledger_dump`
    现值（tools 侧对空／非法投影自归一，本块不预判）。
    """
    return lambda: subject_candidates(str(state.question or ""), state.ledger_dump or {})


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


def _material_round_due(state: RunState, convergence: Convergence) -> bool:
    """零材料触界的**兜底轮**判据（行为 7 细化·2026-10-17 F2）——到顶那一次是否让位恰一轮。

    **真机病灶**（`eval/results/frames/EB4-A-正8.json`＝`run-13c166e9`／`EB4-D-诱10.json`
    ＝`run-b7df65f5`）：澄清相位的**拒因回炉**每次照耗轮，三发连拒即吃满轮预算（`Budget.rounds`
    ＝3），而 run 尚未执行任何工具——轮闸在**入口**到顶即收敛，材料面为零 ⇒ 交付只剩纯收敛话术
    （「…未取得可交付材料…材料清单：无」），整题空答（同题在 EB3 有交付＝同一 `converge` 在有材料
    时逐条如实交付）。**「预算触界必须带材料直答」** ⇒ 到顶这**一次**不砍当前这一轮。

    四判据（**全中**才让位；任一不中＝照旧收敛）：

    ①**拒因回炉入口**——`state.decision_error` 非空（上一发被拒、回喂文在场）＝这一轮确有可重决策
      的由头；成功发射后该字段由相位清回（`clarification._clear_retry_marks`），故非回炉入口恒不中；
    ②**零材料**——有材料时收敛正文本身即「带材料直答」（票面正面形），不让位；
    ③**上一发是照耗轮的非免轮拒**——`state.budget_reject_streak == 0`：免轮拒（澄清的「首拒免轮」
      三类）本就没占轮，不欠它一轮；此条同时**钉死「恰一轮」**——让位轮的结局只有三种，任一都不再
      触发本判据（再拒＝non-free ⇒ `rounds` 超顶 `used > cap`；免轮拒 ⇒ `streak != 0`；成功 ⇒
      `decision_error` 清空），故触界让位在单点 run 内至多发生一次（防环上界不破）；
    ④**仅轮数键命中且恰好到顶**——段时长／连续反问同命中＝时钟面／人机交互面硬闸，不让位；
      `used > cap`＝本兜底机会已用过，照旧收敛。
    """
    if not state.decision_error:  # ① 非拒因回炉入口
        return False
    if _material_present(state):  # ② 有材料 → 就地收敛（带材料直答）
        return False
    if int(state.budget_reject_streak) != 0:  # ③ 免轮拒不欠轮（兼钉「恰一轮」上界）
        return False
    if len(convergence.hit) != 1:  # ④ 硬闸同命中 → 不让位
        return False
    hit = convergence.hit[0]
    return hit.limit == _LIMIT_ROUNDS and hit.used <= hit.cap


def _material_present(state: RunState) -> bool:
    """本 run 是否已有可交付材料——**口径同** `bookkeeping` 的材料面（已入栈观察 ＋ 末次工具结果自
    带观察；真源＝`bookkeeping.closing._material_rows`）。

    本处只问「有／无」这一是非（收敛正文与注记的材料清单渲染仍**单一真源**在 `bookkeeping`——两处
    不漂移由断言 `::f2_material_face_co_sourced` 钉住）；非映射行（旧检查点残形）如实不计。
    """
    if state.observations:
        return True
    last_result = state.last_result
    if isinstance(last_result, Mapping):
        carried = last_result.get("observations")
        if isinstance(carried, list):
            return any(isinstance(row, Mapping) for row in carried)
    return False


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
        # 主体反思（V2-117）：材料到手后（L2 并集池）逐来源核题面主体——落状态位＋末步 payload
        # （判据单点在 `orchestration.subjects`；本处只作调用点，Kimi 评审修正 1）。
        reflect_and_record(state)
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
        marks_before = frozenset(state.chain_switch_marks)
        verdicts = gate_all(
            state,
            window_candidates=deps.window_candidates,
            watermark=deps.watermark,
            data_wells=deps.data_wells,
        )
        # 换链回炉判定＝**计点是否新落**（相位侧「一次为界」的簿记面：首次触发落一笔
        # `chain_switch_marks`，第二次同参起相位侧自行转终局拒答——本块只按有无新计点路由）。
        # **触发支集**（V1 `chain_pending` 逐字复归）：本次新落计点的子问题——路由的「可执行支」
        # 判据按支排除它们（见 `_route_after_precondition`），故此处交出**集合**而非布尔计数。
        reentry = frozenset(state.chain_switch_marks) - marks_before
        for verdict in verdicts:
            if verdict.decision == DECISION_ASK:
                _suspend(state, deps, _precondition_frame(state, verdict))
                break
        else:
            set_intent(state, _route_after_precondition(state, reentry_ids=reentry))
        _flush_notices(deps, state)
        _flush_steps(deps, state)
        return _updates_of(state)

    return node


def _make_batch(deps: LoopDeps) -> Any:
    async def node(state: RunState) -> dict[str, Any]:
        execute(state, bus=deps.bus, registry=deps.registry, store=deps.store)
        # 主体反思（V2-117）：批量执行后材料到手——同 `_make_discover` 的调用点纪律。
        reflect_and_record(state)
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
        # 作答第二出口（V2-96 D5）：本节点入口若带 `explore` 意图，先执行再探（或硬停止），
        # 再重入起草——「answer→explore→执行→追加→重入作答」环（真源 §五·5.2／5.3）。
        forced_text = ""
        if state.next_intent == INTENT_EXPLORE:
            if int(state.explore_rounds) < MAX_EXPLORE_ROUNDS:
                await run_explore(
                    state,
                    bus=deps.bus,
                    registry=deps.registry,
                    max_observations=deps.max_observations,
                    # V2-123：再探增量材料段同携执行日（期错位注记不因增量腿缺席）
                    execution_date=deps.execution_date,
                )
            else:
                # 硬停止：轮数到顶仍出 explore → 追加「只能如实作答」指令＋程序确定性缺口正文
                # （模型正常作答则本参不用；仍出 explore 时由作答相位以该正文兜底交付）。
                forced_text = hard_stop(state)
                state.pending_explore = None
                set_intent(state, INTENT_ANSWER)
        answer(
            state,
            bus=deps.bus,
            max_observations=deps.max_observations,
            supplements=deps.supplements,
            forced_text=forced_text,
            # V2-123：执行日时间量随 `LoopDeps` 注入作答相位（材料头两字段＋期错位比对——
            # 时间量经注入参、context 不读时钟，L0 裁定 D-g）。
            execution_date=deps.execution_date,
        )
        _emit_direct_text(deps, state)
        # 主体反思（V2-117）：作答收口后复核一次并留痕到**作答步** payload（explore 增量材料已并入
        # L2 并集池；核验相位（下一节点）读 `state.subject_reflection` 做件四主体归属扩面）。
        reflect_and_record(state)
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
        # 回炉环入口（V2-115——镜像 V2-96 explore 环的 `_make_answer` 入口支）：本节点被以
        # `INTENT_REPAIR` 重入时，先执行回炉一步（LLM 只重写标红行＋程序复检＋留痕），再落到
        # 下方 `verify` 复检（判据单点复用）；回炉步意图一律回 `verify`（见 `repair.run_repair`）。
        if state.next_intent == INTENT_REPAIR:
            run_repair(
                state,
                max_observations=deps.max_observations,
                # V2-123：回炉材料段同携执行日（期错位注记不因回炉腿缺席）
                execution_date=deps.execution_date,
            )
            _flush_notices(deps, state)
            _flush_steps(deps, state)
        verify(state, bus=deps.bus, supplements=deps.supplements)
        deps.emitted_notices = len(state.notices)  # 本相位自产 notice 帧（不重复出帧）
        _flush_steps(deps, state)
        return _updates_of(state)

    return node


# ── 路由判据（两处「该不该回炉」的机械面——判据只读状态，不做语义判断）──────────


def _route_after_precondition(state: RunState, *, reentry_ids: Collection[str]) -> str:
    """前置条件机之后：可执行支非空 → 批量执行（部分结果先行）；纯换链触发组 → 回炉①；全拒 → 收口。

    **可执行支判据**（V1 `chain_pending and not executable` 逐字复归；真源
    `docs/runtime-refactor/recon/F-前置条件机.md` §11c／§11e＋R-F-15）：换链触发支**本轮不执行**
    （其 verdict 仍是 `allow`＋回炉注记，**执行与否由本判据给）——可执行支＝`allow` 里排除本次新
    触发者；只要可执行支非空即进批量，**唯「纯触发组」（无别的可执行子问题）才回炉①澄清改链**。

    **真机病灶**（`run-3a5e7dba`／EB6 B-正6，V2-82b 程序 ask 恢复腿）：V2 移植把回炉判据写成
    「本腿有新计点即回炉」，未按支排除触发支——s1（在册未绑定→换链触发）与 s2（knowledge 链
    放行）同场时**整组**回炉①；而回炉轮的模型侧无回炉由头（增量条五件皆空）＋`discover` 被
    `question_group` 在场禁掉＋零观察禁 `finalize` ⇒ 连烧轮预算收零材料空交付。V1 的混合组语义＝
    **可执行支先进批量、触发支抛给后续回炉**（钉面
    `tests/domains/test_v2_p040_chain_switch_refurnace.py::test_p040_mixed_group_executes_and_refurnaces`）。
    """
    allowed = [
        item
        for item in state.precondition_verdicts
        if isinstance(item, Mapping) and item.get(PAYLOAD_DECISION_KEY) == DECISION_ALLOW
    ]
    if reentry_ids:
        executable = [
            item
            for item in allowed
            if str(item.get("subtask_id") or "") not in reentry_ids
        ]
        if executable:
            return INTENT_BATCH
        # 回炉澄清**之前**把「为什么回炉」写进现有拒因回喂通道（行为 16④——V2-88／A14）：
        # 该通道是模型窗可见的唯一由头面（`state.precondition_verdicts`／notice 进不了决策链）；
        # 空串不写（不发明空由头）。行为 18 的判据与文案全归 `clarification.guidance`，本处零改写。
        guidance = rejection_guidance(state)
        if guidance:
            state.decision_error = guidance
        return INTENT_DECISION
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
