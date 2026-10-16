"""批量执行相位本体（`execute`）：发现步 → 过闸子问题批量执行 → 观察回流（只读并行）。

真源＝`specs/execution.md`（已定稿）＋卡 `specs/modules.md` `## execution`（签名以卡为准：
`execute(state) -> ExecutionOutcome`）。一句话：把过闸后的子问题**真去执行**（查数／搜报告），
把结果收成**带出处的观察**——**只读并行、成功不重跑、失败只重做失败的**。

一次 `execute` 的固定序（行为 1–14；承载位换、语义不变）：

1. **恢复守卫**（行为 6 的恢复半面）：挂起后重入（`state.resume_choices` 在场）→ **重取易变
   环境量**——逐项从活体状态现取（`bookkeeping.tool_context`，本块零缓存），重取读数落机读
   信号（步 payload 的 `volatile` 键）；**不重放已完成部分**（已完成子问题不二次执行）；
2. **发现步**（行为 11，发射单元 M5）：`state.pending_discovers` 各支只读调用——**同参空手闸**
   （行为 13）先行：任一支同参已空手 → **整发射拒**（不执行工具、不占探查预算）；空手判定＝
   失败／重试耗尽，或成功但本次新增非 notice 观察为 0 → 记同参指纹（`state.empty_probes`）；
3. **批量执行**（行为 1）：`state.question_group` × `state.tool_matches` ×
   `state.precondition_verdicts` 定辖域（**过闸后的子问题**才真去执行），**只读并行**派遣
   （`asyncio.gather`）；**观察编号按子问题定序分配**、与完成顺序解耦（同一输入两次运行同序）；
   派遣前过**同参重投闸**（行为 14）——全支皆在实录＝拦、任一支新参＝放行；
4. **失败分类**（行为 3）：`retryable`／`bad_args`／`refused` 写明文，**只重跑 `retryable`**
   （同参一次、按工具名计数）；`refused`（闸拒）＝终局不回炉；任一子问题失败不阻断其余
   （行为 10）；
5. **大结果落引用**（行为 4／12）：**行集题全量交付、丢行＝0**（永不落引用）；非行集大结果
   超阈才落引用（窗口只留摘要＋稳定引用＋行数，原文落 `persistence` 公开面、可寻址读回），
   截断与落引用必披露；
6. **观察回流**（行为 9）：逐条带出处落 `state.observations`（全局 `[n]` 序）并发射
   `observation` 帧；缺出处＝判失败（fail-closed，不猜不补）。

**机读信号单点**（「不降级与静默禁令」节）：本块写的**每一步** payload 恒携三键
`row_count`／`ref.handle`／`error.reason`（单点＝`_signal_payload`；**键恒在场、值诚实**——
缺值≠缺键）。落引用＝`ref.handle` 可寻址（同一 handle 亦回落到 `state.observations` 行与子问题
账）；失败＝`error.reason` 如实（`error` 与 `SubtaskExec.error` **同档语义**：缺参／发射级拒＝
`None`，失败／闸拒＝`{category, reason}`）；缺参＝`ask` 帧＋`state.pending_ask`。`error.reason` 与
记账面 `reject_reason` 出自**同一变量、同一写入点**——不构第二套语义。

**接缝纪律（本块自立的调用面约定，登记见票面回报）**：`bus`（per-run 总线）／`registry`
（`tools` 公开面——工具调用唯一入口）为**必给**注入面，未注入＝调用方断线，入口即 fail-closed
抛错（同 `understanding.interpret` 的 `bus` 先例）；`store`（`persistence` 公开面＝大结果原文的
引用载体）**按需必给**——出现非行集大结果却未注入＝fail-closed 抛错（**不静默交付全文**：
「窗口只留摘要＋引用＋行数」是行为 4 的硬要求）。三者皆关键词注入，不改卡面签名
`execute(state)` 的实参形。

**零 LLM 面**（R8）：本块不调模型、不引 `gateway_adapter`；**只经 `tools` 公开面接触世界**
（R6）；**模型调用步记录不在本块作用面**（W4 通用须知：模型调用由 `bookkeeping.call_model`
单点记账）——本块的步记录＝**工具调用一条**（工具调用不由 `bookkeeping` 记账，无重复面）。
**帧面**只发 `tool`／`observation`／`ask`（`ask`＝工具侧缺参／审批挂起帧——S6 §一 的 ask 行
发射单元列为 M2／M4，工具侧第三发射点在 V1 同族节点内、本块承接，**登记呈主窗**）；
`notice` 经唯一写口落状态、帧面归 `transport`／`orchestration`（`specs/bookkeeping.md` 口径）。

〔登记（呈主窗）〕两处与 `synth/S5` 旧码写手矩阵的差异，皆为**流水 30②「闸归 execution」**
的机械后果：① `state.rounds`／`state.decision_error` 的写点（旧码 M2／M3）随两闸迁入本块；
② `state.executed_payloads` 只在 `ok` 时记账（旧码 `ok/ask` 皆记——旧码的审批重投走
`last_execute` 通道不受闸辖，V2 批量执行是**唯一派遣路径**，记 ask 载荷会把恢复后的同参重投
误拦，故按实义收窄为「成功实录」）。
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from appv2.runtimev2.bookkeeping import (
    note,
    notice,
    record_step,
    result_projection,
    tool_context,
)
from appv2.runtimev2.context import trust_of
from appv2.runtimev2.execution.constants import (
    BIG_RESULT_THRESHOLD_CHARS,
    CONTENT_DECISION_REJECTED_TEMPLATE,
    CONTENT_EMPTY_PROBE_NOTICE_PREFIX,
    CONTENT_REF_DISCLOSURE_TEMPLATE,
    CONTENT_REPLAY_NOTICE_PREFIX,
    CONTENT_SUBTASK_FAILED_TEMPLATE,
    CONTENT_SUBTASK_REFUSED_TEMPLATE,
    CONTENT_TOOL_UNAVAILABLE_TEMPLATE,
    EMPTY_PROBE_FEEDBACK_TEMPLATE,
    ERROR_BAD_ARGS,
    ERROR_REFUSED,
    ERROR_RETRYABLE,
    EVENT_ASK,
    EVENT_OBSERVATION,
    EVENT_TOOL,
    EXEC_STATUS_FAILED,
    EXEC_STATUS_NEED_INPUT,
    EXEC_STATUS_OK,
    GATE_EMPTY_PROBE,
    GATE_SAME_PARAM_REPLAY,
    LEDGER_NOTE_PHASE,
    MISSING_SOURCE_REASON,
    NOTICE_DECISION_REJECTED,
    NOTICE_MATERIAL_TRUNCATED,
    NOTICE_SAME_PARAM_REPLAY,
    NOTICE_SUBTASK_FAILED,
    NOTICE_SUBTASK_REFUSED,
    NOTICE_TOOL_UNAVAILABLE,
    PAYLOAD_ARGS_FINGERPRINT_KEY,
    PAYLOAD_ARGS_KEY,
    PAYLOAD_ATTEMPTS_KEY,
    PAYLOAD_CHAIN_KEY,
    PAYLOAD_CONSUMES_ROUND_KEY,
    PAYLOAD_CONTENT,
    PAYLOAD_ERROR_CATEGORY_KEY,
    PAYLOAD_ERROR_KEY,
    PAYLOAD_ERROR_REASON_KEY,
    PAYLOAD_FINGERPRINTS_KEY,
    PAYLOAD_FRAME,
    PAYLOAD_GATE_KEY,
    PAYLOAD_HANDLE_KEY,
    PAYLOAD_INDEX,
    PAYLOAD_MESSAGE,
    PAYLOAD_PHASE_KEY,
    PAYLOAD_REF_KEY,
    PAYLOAD_REJECT_REASON_KEY,
    PAYLOAD_REJECTED_KEY,
    PAYLOAD_ROW_COUNT_KEY,
    PAYLOAD_RUN_ID,
    PAYLOAD_SEQ,
    PAYLOAD_SOURCE,
    PAYLOAD_STATUS,
    PAYLOAD_SUBTASK_ID_KEY,
    PAYLOAD_SUMMARY_KEY,
    PAYLOAD_TOOL,
    PAYLOAD_TRUST,
    PAYLOAD_VOLATILE_KEY,
    PHASE,
    ROWSET_OBSERVATION_KINDS,
    SAME_PARAM_REPLAY_REASON,
    TITLE_ADMISSION_REJECTED_TEMPLATE,
    TITLE_DISCOVER_TEMPLATE,
    TITLE_EMPTY_PROBE_REJECTED_TEMPLATE,
    TITLE_EXECUTE_TEMPLATE,
    TITLE_REPLAY_REJECTED_TEMPLATE,
    TITLE_RESUME_GUARD,
)
from appv2.runtimev2.execution.models import (
    ErrorClass,
    ExecutionOutcome,
    MaterialRef,
    Observation,
    SubtaskExec,
)
from appv2.runtimev2.parsing import (
    CHAIN_DATA,
    CHAIN_KINDS,
    discover_fingerprint,
    emission_fingerprints,
    is_same_param_replay,
    payload_fingerprint,
)
from appv2.runtimev2.persistence import (
    STEP_STATUS_FAILED,
    STEP_STATUS_OK,
    STEP_STATUS_REFUSED,
    RunStore,
    head,
)
from appv2.runtimev2.state import STEP_DISCOVER, STEP_EXECUTE, RunState
from appv2.runtimev2.transport import EventBus
from appv2.tools import (
    DATA_QUERY,
    DOC_RETRIEVE,
    ToolContext,
    ToolRegistry,
    ToolResult,
    classify_exception,
)

# 前置判定三态闭世界（真源 `specs/preconditions.md` 接口定义：allow｜refuse｜ask）。
_DECISION_ALLOW = "allow"
_DECISION_REFUSE = "refuse"
_DECISION_ASK = "ask"
_DECISIONS: frozenset[str] = frozenset({_DECISION_ALLOW, _DECISION_REFUSE, _DECISION_ASK})

# 工具结果三态（真源 `appv2/tools` 的 ToolResult.status 闭世界；此处只作读面字面）。
_STATUS_OK = "ok"
_STATUS_FAILED = "failed"
_STATUS_ASK = "ask"

_BUS_MISSING = (
    "执行相位总线未注入（per-run 总线由编排块持有并注入）——工具／观察事件无出口，"
    "fail-closed：不静默丢弃（「不降级与静默禁令」节）"
)
_REGISTRY_MISSING = (
    "执行相位工具面未注入（`tools` 公开面的 ToolRegistry 是工具调用唯一入口）——"
    "fail-closed：不自建工具调用旁路（「框架与依赖红线」末条）"
)
_STORE_MISSING = (
    "大结果落引用未注入 `persistence` 公开面（引用载体）——fail-closed："
    "不静默把超阈全文留在窗口（行为 4「窗口只留摘要＋引用＋行数」）"
)
_DEFAULT_FAILURE_REASON = "执行失败（拒因文本缺失——如实兜底，不编造分类）"


def _require_bus(bus: EventBus | None) -> EventBus:
    """总线把守（fail-closed）：未注入即抛错——不做「无出口静默跳过」的降级。"""
    if bus is None:
        raise RuntimeError(_BUS_MISSING)
    return bus


def _require_registry(registry: ToolRegistry | None) -> ToolRegistry:
    """工具面把守（fail-closed）：未注入即抛错——不自建工具调用旁路。"""
    if registry is None:
        raise RuntimeError(_REGISTRY_MISSING)
    return registry


# ── 步 payload 的机读信号三键（规格「不降级与静默禁令」节单点）─────────────────────


def _signal_payload(
    *,
    row_count: int | None = None,
    ref: MaterialRef | None = None,
    category: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """机读信号三键（规格 :96 逐字：`row_count`／`ref.handle`／`error.reason`）。

    **键恒在场、值诚实**（缺值≠缺键——机检可判「本块写的每一步 payload 恒携三键」）：
    `row_count`＝本次派遣回来的**观察行数**（行为 7 记账面）；`ref`＝大结果引用投影
    （`ref.row_count` 是被落引用**原文**的行数——`MaterialRef.row_count` 原义，与观察行数两回事），
    未落引用＝`None`；`error`＝**与 `SubtaskExec.error` 同档语义**（缺参／发射级拒＝`None`；
    失败／闸拒＝`{category, reason}`），非失败档＝`None`。

    单一变量面：`error.reason` 与记账面 `reject_reason` 出自**同一变量、同一写入点**——本函数
    不引入第二套语义（行为 7 的拒因面与不降级节的机读信号面同源）；拒因文本缺失时两处同引
    `_DEFAULT_FAILURE_REASON`（如实兜底、不编造分类）。
    """
    return {
        PAYLOAD_ROW_COUNT_KEY: row_count,
        PAYLOAD_REF_KEY: (
            None
            if ref is None
            else {
                PAYLOAD_HANDLE_KEY: ref.handle,
                PAYLOAD_SUMMARY_KEY: ref.summary,
                PAYLOAD_ROW_COUNT_KEY: ref.row_count,
            }
        ),
        PAYLOAD_ERROR_KEY: (
            None
            if category is None
            else {
                PAYLOAD_ERROR_CATEGORY_KEY: category,
                PAYLOAD_ERROR_REASON_KEY: reason or _DEFAULT_FAILURE_REASON,
            }
        ),
    }


# ── 派遣载荷（发现步／批量执行共用同一调用形）─────────────────────────────────────


@dataclass(slots=True)
class _Call:
    """一次工具派遣（两路同形：工具名＋参数＋该发射的指纹）。"""

    tool: str
    args: dict[str, Any]
    fingerprints: tuple[str, ...]
    subtask_id: str = ""
    chain: str = ""
    question: str = ""


@dataclass(slots=True)
class _Returned:
    """派遣回执（含超时／抛错的合成面——两形皆归失败三档，不炸整批）。"""

    call: _Call
    result: ToolResult | None
    limit_seconds: float
    failure: tuple[str, str] | None = None  # （category, message）——超时／工具调用抛错
    retries: int = 0  # 本次结果之前已同参重跑的次数（首投账另记——行为 7 每次记账）


@dataclass(slots=True)
class _Consumed:
    """一次派遣的落地读数（回流段与逐子问题账共用）。"""

    call: _Call
    status: str
    category: str | None
    message: str | None
    rows: list[Observation] = field(default_factory=list)
    fresh_material: int = 0
    ref: MaterialRef | None = None
    row_count: int | None = None
    answered: bool = False


@dataclass(slots=True)
class _Entry:
    """执行辖域内的一个子问题（问题组 × 工具匹配 × 前置判定三面投影）。"""

    subtask_id: str
    question: str
    chain: str
    verdict: Mapping[str, Any]
    fingerprints: tuple[str, ...] = ()
    call: _Call | None = None


# ── 相位入口（卡面签名 `execute(state)` ＋ 三处关键词注入面）───────────────────────


def execute(
    state: RunState,
    *,
    bus: EventBus | None = None,
    registry: ToolRegistry | None = None,
    store: RunStore | None = None,
) -> ExecutionOutcome:
    """批量执行一步：发现步 → 过闸子问题只读并行执行 → 观察回流（返回定型载荷）。

    单出口：恒回 `ExecutionOutcome`（观察序列 ＋ 逐子问题账）；结构违约（缺问题组／过闸却缺
    匹配／闭世界越界／观察缺出处）＝ fail-closed 抛错，**不返回半成品、不静默降级**
    （「不降级与静默禁令」节：合法降级路径＝无）。
    """
    channel = _require_bus(bus)
    tools = _require_registry(registry)
    context = tool_context(state)
    if state.resume_choices:
        _reread_volatile_environment(state, context)
    observations: list[Observation] = []
    if state.pending_discovers:
        observations.extend(_run_discovers(state, channel, tools, context, store))
    scope = _execution_scope(state)
    subtasks: list[SubtaskExec] = []
    if scope:
        batch_observations, subtasks = _run_batch(
            state, channel, tools, context, store, scope
        )
        observations.extend(batch_observations)
    return ExecutionOutcome(observations=observations, subtasks=subtasks)


# ── 恢复守卫（行为 6 的恢复半面：重取易变环境量、不重放已完成部分）────────────────


def _reread_volatile_environment(state: RunState, context: ToolContext) -> None:
    """恢复时**重取易变环境量**（等待期间可能变了的量必须重校验——真源 `walk/裁决表.md` §10-B）。

    本块可及面＝**工具调用环境**四项（身份／送窗预算／候选集／外表放行态）——皆由
    `bookkeeping.tool_context` 从**活体状态**现取（本块零缓存、不沿用挂起前的值）；重取读数落
    机读信号（步 payload 的 `volatile` 键）使「重取」可机检。

    〔登记（呈主窗）〕`specs/clarification.md` 行为 13 的「易变环境量」另有**台账面**四项读数
    （水位／新鲜度／地基／落库新数据，读点在其 `volatile` 子模块）——该件属业务相位（R1／R2
    禁相位互引），本块**不复制其读数公式**，只重取本块工具调用面依赖的活体量（切分面登记见
    票面回报）。
    """
    readings: dict[str, Any] = {
        "actor": context.actor,
        "budget": context.budget,
        "metric_candidates": list(context.metric_candidates or ()),
        "approved_tables": list(context.approved_tables),
    }
    record_step(
        state,
        kind=STEP_EXECUTE,
        title=TITLE_RESUME_GUARD,
        status=STEP_STATUS_OK,
        # 统一字段面：本块写的每一步 payload 恒携机读信号三键
        # （本步无落地结果／非失败档＝值诚实的 None）
        payload={PAYLOAD_PHASE_KEY: PHASE, PAYLOAD_VOLATILE_KEY: readings, **_signal_payload()},
    )


# ── 派遣（只读并行：单次 `asyncio.run` 内 gather；单工具超时闸在派遣处）────────────


def _dispatch(
    state: RunState,
    registry: ToolRegistry,
    context: ToolContext,
    calls: Sequence[_Call],
) -> list[_Returned]:
    """只读并行派遣（全部工具只读无副作用，故并行安全——行为 1）。"""
    limit = float(state.budget.tool_timeout)
    return _run_sync(_gather(registry, context, calls, limit))


async def _gather(
    registry: ToolRegistry,
    context: ToolContext,
    calls: Sequence[_Call],
    limit_seconds: float,
) -> list[_Returned]:
    return list(
        await asyncio.gather(
            *(_invoke(registry, context, call, limit_seconds) for call in calls)
        )
    )


async def _invoke(
    registry: ToolRegistry,
    context: ToolContext,
    call: _Call,
    limit_seconds: float,
) -> _Returned:
    """单次工具调用：超时＝retryable 档（V1 同款「超时转 retryable 通道」）。

    工具调用**抛错不炸整批**（规格「接口定义」错误契约）：异常经 `tools` 公开面的分类单点
    `classify_exception` 三档归一后回该子问题，其余子问题照常。
    """
    try:
        result = await asyncio.wait_for(
            registry.call(call.tool, call.args, context), timeout=limit_seconds
        )
    except TimeoutError:
        return _Returned(
            call=call,
            result=None,
            limit_seconds=limit_seconds,
            failure=(ERROR_RETRYABLE, f"上游超时：单工具超时 {limit_seconds:g}s"),
        )
    except Exception as exc:  # 分类单点兜底（不吞：三档归一后如实上报该子问题）
        category, message, _hint = classify_exception(exc)
        return _Returned(
            call=call,
            result=None,
            limit_seconds=limit_seconds,
            failure=(category, message),
        )
    return _Returned(call=call, result=result, limit_seconds=limit_seconds)


def _run_sync(
    awaitable: Coroutine[Any, Any, list[_Returned]],
) -> list[_Returned]:
    """同步签名面 → 异步派遣的**两态桥**（本块唯一一处事件循环接触）。

    无运行环 → 本线程 `asyncio.run` 直跑；已在运行环内 → 落专用单线程池另起环（不阻塞事件
    循环）——同 `bookkeeping.closing._run_sync`／`appv2/query/pg_executor.py` 的既有桥形。
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(awaitable)).result()


def _retry_retryable(
    state: RunState,
    registry: ToolRegistry,
    context: ToolContext,
    returned: Sequence[_Returned],
    *,
    kind: str,
) -> list[_Returned]:
    """`retryable` 同参重跑**一次**（按工具名计数——真源 `state.tool_retries`）。

    只重跑 `retryable` 档（行为 3）：`bad_args`＝修参回炉（不原地重投）、`refused`＝终局。
    首投失败的那次调用**单独留一条账**（行为 7「每次工具调用记参数／行数／拒因」——可事后复算）。
    """
    scheduled: list[tuple[int, _Call]] = []
    for index, item in enumerate(returned):
        if _category_of(item) != ERROR_RETRYABLE:
            continue
        spent = int(state.tool_retries.get(item.call.tool, 0))
        if spent >= 1:
            continue
        state.tool_retries[item.call.tool] = spent + 1
        scheduled.append((index, item.call))
    if not scheduled:
        return list(returned)
    retried = _dispatch(state, registry, context, [call for _, call in scheduled])
    updated = list(returned)
    for (index, _call), outcome in zip(scheduled, retried, strict=True):
        outcome.retries = 1
        updated[index] = outcome
    return updated


def _record_retry_attempt(state: RunState, item: _Returned, *, kind: str) -> None:
    """同参重跑前的首投账目（行为 7：每次工具调用一条账——参数／拒因／行数如实）。"""
    _status, _category, message = _status_of(item)
    payload: dict[str, Any] = {
        PAYLOAD_PHASE_KEY: PHASE,
        PAYLOAD_TOOL: item.call.tool,
        PAYLOAD_STATUS: _STATUS_FAILED,
        PAYLOAD_ARGS_KEY: dict(item.call.args),
        PAYLOAD_ARGS_FINGERPRINT_KEY: payload_fingerprint(item.call.args),
        PAYLOAD_REJECT_REASON_KEY: message,
        PAYLOAD_ATTEMPTS_KEY: 1,
        **_signal_payload(category=_category, reason=message),
    }
    if item.call.subtask_id:
        payload[PAYLOAD_SUBTASK_ID_KEY] = item.call.subtask_id
        payload[PAYLOAD_CHAIN_KEY] = item.call.chain
    record_step(
        state,
        kind=kind,
        title=_title_of(kind, item.call, _STATUS_FAILED),
        status=STEP_STATUS_FAILED,
        payload=payload,
    )


# ── 发现步（行为 11）：只读调用 ＋ `tool` 事件发射（发射单元 M5）＋ 空手闸 ──────────


def _run_discovers(
    state: RunState,
    bus: EventBus,
    registry: ToolRegistry,
    context: ToolContext,
    store: RunStore | None,
) -> list[Observation]:
    """发现步各支只读并行执行；**同参空手重发＝整发射拒**（行为 13——不执行工具、不占预算）。"""
    calls: list[_Call] = []
    for queued in state.pending_discovers:
        if not isinstance(queued, Mapping):
            raise ValueError(f"待执行发现步支须为对象（state.pending_discovers）：{queued!r}")
        tool = str(queued.get("tool") or "").strip()
        args = dict(queued.get("args") or {})
        calls.append(
            _Call(tool=tool, args=args, fingerprints=(discover_fingerprint(tool, args),))
        )
    state.pending_discovers = []  # 各支本轮皆已尝试（执行或发射级拒）——队列消费
    if not calls:
        return []
    duplicates = [call for call in calls if call.fingerprints[0] in state.empty_probes]
    if duplicates:  # 整发射拒：任一支同参已空手即不执行（门只在换参时开着——Owner 拍板）
        _reject_emission(state, GATE_EMPTY_PROBE, duplicates, STEP_DISCOVER)
        return []
    returned = _dispatch(state, registry, context, calls)
    returned = _retry_retryable(state, registry, context, returned, kind=STEP_DISCOVER)
    observations: list[Observation] = []
    for outcome in returned:
        state.discover_used = int(state.discover_used) + 1  # 探查预算（发射级拒时不增）
        consumed = _consume(state, bus, outcome, store, kind=STEP_DISCOVER)
        observations.extend(consumed.rows)
        if _is_empty_probe(consumed):
            state.empty_probes.append(outcome.call.fingerprints[0])
    return observations


def _is_empty_probe(consumed: _Consumed) -> bool:
    """空手判定（行为 13）：失败（含 `refused`／重试耗尽）或成功但新增非 notice 观察为 0。"""
    if consumed.status == _STATUS_FAILED:
        return True
    return consumed.status == _STATUS_OK and consumed.fresh_material == 0


# ── 批量执行（行为 1／3／4／5／10／14）───────────────────────────────────────────


def _run_batch(
    state: RunState,
    bus: EventBus,
    registry: ToolRegistry,
    context: ToolContext,
    store: RunStore | None,
    scope: Sequence[_Entry],
) -> tuple[list[Observation], list[SubtaskExec]]:
    """逐支定账 → 只读并行派遣 → 按子问题定序回流（观察编号与完成顺序解耦）。"""
    prior = _prior_results(state)
    settled: list[SubtaskExec | None] = []
    calls: list[_Call] = []
    for entry in scope:
        decision = str(entry.verdict.get("decision") or "")
        if decision == _DECISION_REFUSE:
            settled.append(_record_admission_refusal(state, entry))
            continue
        if decision == _DECISION_ASK:
            settled.append(_record_admission_ask(state, entry))
            continue
        carried = _carry_forward(entry, prior)
        if carried is not None:
            settled.append(carried)
            continue
        terminal = _terminal_forward(state, entry, prior)
        if terminal is not None:
            settled.append(terminal)
            continue
        if is_same_param_replay(
            entry.fingerprints, state.executed_payloads
        ) or _same_param_failed(entry, prior):
            settled.append(_reject_replay(state, entry))
            continue
        if entry.call is None:  # 结构违约（构造面已保证）——fail-closed，不静默跳支
            raise ValueError(f"执行辖域支缺派遣载荷（内部失序）：{entry.subtask_id!r}")
        calls.append(entry.call)
        settled.append(None)

    observations: list[Observation] = []
    filled: dict[str, SubtaskExec] = {}
    if calls:
        returned = _retry_retryable(
            state,
            registry,
            context,
            _dispatch(state, registry, context, calls),
            kind=STEP_EXECUTE,
        )
        for item in returned:
            consumed = _consume(state, bus, item, store, kind=STEP_EXECUTE)
            observations.extend(consumed.rows)
            filled[item.call.subtask_id] = _subtask_exec(
                state, _entry_for_call(scope, item.call), consumed
            )

    subtasks: list[SubtaskExec] = []
    for entry, outcome in zip(scope, settled, strict=True):
        subtasks.append(filled[entry.subtask_id] if outcome is None else outcome)
    return observations, subtasks


def _entry_for_call(scope: Sequence[_Entry], call: _Call) -> _Entry:
    """按派遣载荷回取辖域条目（观察回流段的账目面）。"""
    for entry in scope:
        if entry.subtask_id == call.subtask_id:
            return entry
    raise ValueError(f"派遣载荷不在执行辖域内（内部失序）：{call.subtask_id!r}")


def _execution_scope(state: RunState) -> list[_Entry]:
    """执行辖域＝问题组 × 工具匹配 × 前置判定（**过闸后的子问题**才真去执行）。"""
    group = state.question_group
    raw_subtasks = group.get("subtasks") if isinstance(group, Mapping) else None
    if not isinstance(raw_subtasks, list) or not raw_subtasks:
        return []  # 无问题组＝不在批量辖域（上游未产组——本块不猜、不补、不静默造支）
    matches: dict[str, Mapping[str, Any]] = {
        str(item.get("id") or ""): item
        for item in state.tool_matches
        if isinstance(item, Mapping)
    }
    verdicts: dict[str, Mapping[str, Any]] = {
        str(item.get("subtask_id") or ""): item
        for item in state.precondition_verdicts
        if isinstance(item, Mapping)
    }
    entries: list[_Entry] = []
    for item in raw_subtasks:
        if not isinstance(item, Mapping):
            raise ValueError(f"问题组支须为对象（state.question_group.subtasks）：{item!r}")
        subtask_id = str(item.get("id") or "").strip()
        if not subtask_id:
            raise ValueError("问题组支缺 id（执行辖域比对面必填——fail-closed，不猜）")
        verdict = verdicts.get(subtask_id)
        if verdict is None:
            continue  # 未过闸——不在执行辖域
        decision = str(verdict.get("decision") or "")
        if decision not in _DECISIONS:
            values = "／".join(sorted(_DECISIONS))
            raise ValueError(
                f"前置判定 decision 越界（三态闭世界＝{values}）：{decision!r}——不猜、不取默认"
            )
        question = str(item.get("question") or "")
        match = matches.get(subtask_id)
        if match is None:
            if decision == _DECISION_ALLOW:
                raise ValueError(
                    f"子问题 {subtask_id} 已过闸却缺工具匹配（state.tool_matches）："
                    "fail-closed——不猜工具、不跳过子问题"
                )
            entries.append(
                _Entry(
                    subtask_id=subtask_id,
                    question=question,
                    chain="",
                    verdict=verdict,
                )
            )
            continue
        entries.append(_entry_of(subtask_id, question, match, verdict))
    return entries


def _entry_of(
    subtask_id: str,
    question: str,
    match: Mapping[str, Any],
    verdict: Mapping[str, Any],
) -> _Entry:
    """匹配支 → 派遣载荷（按链取工具与参数——链闭世界，越界 fail-closed）。"""
    chain = str(match.get("chain") or "").strip()
    if chain not in CHAIN_KINDS:
        values = "／".join(sorted(CHAIN_KINDS))
        raise ValueError(f"匹配支 chain 越界（闭世界＝{values}）：{chain!r}")
    raw_plan = match.get("plan")
    raw_need = match.get("retrieval_need")
    plan = (
        {
            key: value
            for key, value in dict(raw_plan).items()
            if key != "caliber_key"  # caliber_key 消费点＝前置条件机（域面零漂移）
        }
        if isinstance(raw_plan, Mapping)
        else None
    )
    retrieval_need = dict(raw_need) if isinstance(raw_need, Mapping) else None
    if chain == CHAIN_DATA:
        tool = DATA_QUERY
        args: dict[str, Any] = {"plan_draft": dict(plan or {})}
    else:
        tool = DOC_RETRIEVE
        args = dict(retrieval_need or {})
    fingerprints = emission_fingerprints(plan, retrieval_need)
    return _Entry(
        subtask_id=subtask_id,
        question=question,
        chain=chain,
        verdict=verdict,
        fingerprints=fingerprints,
        call=_Call(
            tool=tool,
            args=args,
            fingerprints=fingerprints,
            subtask_id=subtask_id,
            chain=chain,
            question=question,
        ),
    )


# ── 前置判定三态的非执行支（拒＝终局不回炉；等用户＝挂起）─────────────────────────


def _record_admission_refusal(state: RunState, entry: _Entry) -> SubtaskExec:
    """前置闸拒（`refused`＝**终局、不回炉**）——如实留痕、进账、不派遣。"""
    reason = _refusal_text(entry.verdict)
    record_step(
        state,
        kind=STEP_EXECUTE,
        title=TITLE_ADMISSION_REJECTED_TEMPLATE.format(subtask=entry.subtask_id),
        status=STEP_STATUS_REFUSED,
        payload={
            PAYLOAD_PHASE_KEY: PHASE,
            PAYLOAD_SUBTASK_ID_KEY: entry.subtask_id,
            PAYLOAD_STATUS: ERROR_REFUSED,
            PAYLOAD_REJECT_REASON_KEY: reason,
            **_signal_payload(category=ERROR_REFUSED, reason=reason),
        },
    )
    notice(
        state,
        type=NOTICE_SUBTASK_REFUSED,
        content=CONTENT_SUBTASK_REFUSED_TEMPLATE.format(subtask=entry.subtask_id, reason=reason),
    )
    _store_subtask_result(
        state, entry, status=ERROR_REFUSED, reason=reason, obs_count=0, ref=None
    )
    return SubtaskExec(
        subtask_id=entry.subtask_id,
        exec_status=EXEC_STATUS_FAILED,
        answered=False,
        error=ErrorClass(category=ERROR_REFUSED, reason=reason),
        row_count=None,
        ref=None,
    )


def _record_admission_ask(state: RunState, entry: _Entry) -> SubtaskExec:
    """前置式等用户（`ask`）——本块只出 `need_input` 账；**发帧归 `orchestration`**
    （`AskReason.kind` → `frame.kind` 映射表在 `specs/preconditions.md` 接口定义）。"""
    reason = _ask_text(entry.verdict)
    record_step(
        state,
        kind=STEP_EXECUTE,
        title=f"子问题 {entry.subtask_id} 待用户（前置闸 ask）",
        status=STEP_STATUS_OK,
        payload={
            PAYLOAD_PHASE_KEY: PHASE,
            PAYLOAD_SUBTASK_ID_KEY: entry.subtask_id,
            PAYLOAD_STATUS: EXEC_STATUS_NEED_INPUT,
            PAYLOAD_REJECT_REASON_KEY: reason,
            # 挂起不是失败（`SubtaskExec.error` 同档语义）——`error` 留 None，缺参信号由 `ask` 帧承接
            **_signal_payload(),
        },
    )
    return SubtaskExec(
        subtask_id=entry.subtask_id,
        exec_status=EXEC_STATUS_NEED_INPUT,
        answered=False,
        error=None,
        row_count=None,
        ref=None,
    )


def _refusal_text(verdict: Mapping[str, Any]) -> str:
    """闸拒人话（真源 `preconditions.RefusalReason`：`human_text` 优先、`rule_id` 兜底）。"""
    reason = verdict.get("reason")
    if isinstance(reason, Mapping):
        human = str(reason.get("human_text") or "").strip()
        if human:
            return human
        rule = str(reason.get("rule_id") or "").strip()
        if rule:
            return rule
    return "前置闸拒（拒因缺失——如实兜底，不编造）"


def _ask_text(verdict: Mapping[str, Any]) -> str:
    """等用户提示（真源 `preconditions.AskReason`：`prompt` 优先、`kind` 兜底）。"""
    reason = verdict.get("reason")
    if isinstance(reason, Mapping):
        prompt = str(reason.get("prompt") or "").strip()
        if prompt:
            return prompt
        kind = str(reason.get("kind") or "").strip()
        if kind:
            return kind
    return "等用户输入（提示缺失——如实兜底，不编造）"


# ── 成功不重跑（行为 2：指纹命中）──────────────────────────────────────────────


def _prior_results(state: RunState) -> dict[str, Mapping[str, Any]]:
    """逐子问题产物簿记（`state.subtask_results`；同 id 只留最新——V1 同款）。"""
    return {
        str(item.get("id") or ""): item
        for item in state.subtask_results
        if isinstance(item, Mapping)
    }


def _carry_forward(
    entry: _Entry, prior: Mapping[str, Mapping[str, Any]]
) -> SubtaskExec | None:
    """已成功子问题**不重发工具调用**（行为 2：指纹簿记命中即跳过——不重放已完成部分）。"""
    record = prior.get(entry.subtask_id)
    if record is None or str(record.get("status") or "") != _STATUS_OK:
        return None
    recorded = str(record.get("fingerprint") or "")
    if not recorded or recorded not in entry.fingerprints:
        return None  # 指纹未命中（参数已变）＝新尝试——重跑
    obs_count = int(record.get("obs_count") or 0)
    return SubtaskExec(
        subtask_id=entry.subtask_id,
        exec_status=EXEC_STATUS_OK,
        answered=obs_count > 0,
        error=None,
        row_count=obs_count,
        ref=_ref_of(record),
    )


def _terminal_forward(
    state: RunState, entry: _Entry, prior: Mapping[str, Mapping[str, Any]]
) -> SubtaskExec | None:
    """前置闸拒＝**终局**（不回炉、不再投——行为 3）：重入时如实复述，零新调用。

    拒因取产物账里的原话（可复算）；本函数只补一条如实账目步，不再发通知（首次判定时已披露）。
    """
    record = prior.get(entry.subtask_id)
    if record is None or str(record.get("status") or "") != ERROR_REFUSED:
        return None
    reason = str(record.get("reason") or "").strip() or "前置闸拒（终局不回炉）"
    record_step(
        state,
        kind=STEP_EXECUTE,
        title=f"子问题 {entry.subtask_id} 终局不回炉（前置闸拒）",
        status=STEP_STATUS_REFUSED,
        payload={
            PAYLOAD_PHASE_KEY: PHASE,
            PAYLOAD_SUBTASK_ID_KEY: entry.subtask_id,
            PAYLOAD_STATUS: ERROR_REFUSED,
            PAYLOAD_REJECT_REASON_KEY: reason,
            **_signal_payload(category=ERROR_REFUSED, reason=reason),
        },
    )
    return SubtaskExec(
        subtask_id=entry.subtask_id,
        exec_status=EXEC_STATUS_FAILED,
        answered=False,
        error=ErrorClass(category=ERROR_REFUSED, reason=reason),
        row_count=None,
        ref=None,
    )


def _same_param_failed(entry: _Entry, prior: Mapping[str, Mapping[str, Any]]) -> bool:
    """同参 `bad_args` 失败＝**零新信息**（行为 14 的实义：先修参再投）——归同参重投闸拦。

    `retryable` 不在此列——行为 3 明文「只重跑 `retryable`」（同参重跑一次仍由 `tool_retries`
    计数额度）；`refused` 由 `_terminal_forward` 先接走。
    """
    record = prior.get(entry.subtask_id)
    if record is None or str(record.get("status") or "") != ERROR_BAD_ARGS:
        return False
    recorded = str(record.get("fingerprint") or "")
    return bool(recorded) and recorded in entry.fingerprints


def _ref_of(record: Mapping[str, Any]) -> MaterialRef | None:
    """簿记条目里的引用投影 → `MaterialRef`（缺项如实 None——不编造）。"""
    raw = record.get(PAYLOAD_REF_KEY)
    if not isinstance(raw, Mapping):
        return None
    handle = str(raw.get(PAYLOAD_HANDLE_KEY) or "")
    if not handle:
        return None
    return MaterialRef(
        handle=handle,
        summary=str(raw.get(PAYLOAD_SUMMARY_KEY) or ""),
        row_count=int(raw.get(PAYLOAD_ROW_COUNT_KEY) or 0),
    )


# ── 两闸的发射级拒（行为 13／14——不执行工具；首拒免轮、第 2 次起占轮）─────────────


def _reject_emission(
    state: RunState,
    gate: str,
    calls: Sequence[_Call],
    kind: str,
) -> None:
    """发射级**整发射拒**（两闸共用落地）：不执行工具 ＋ 拒因回喂 ＋ 轮语义如实。

    零帧面（工具**未执行**——不发 `tool` 帧；拒因与账目走步 payload ＋ notice ＋ 回喂通道）。

    轮语义（行为 13／14 原文「首拒免轮、第 2 次起占轮」）：同一指纹的**既有拦截次数**为 0 →
    本次为首次拦截（免轮，不落 `rounds`）；≥1 → 连续第 2 次起（`rounds` 递增 `1`）。判定面
    只读**本块自己的步记录**（`state.steps` 里 `gate` ＋ `fingerprints` 两键同现者），不新增
    状态字段、不占 `budget_reject_streak`（该字段是发现预算拒的免轮例外计数）。
    """
    fingerprints = sorted({value for call in calls for value in call.fingerprints})
    consumes_round = _rejection_streak(state, gate, fingerprints) >= 1
    if consumes_round:
        state.rounds = int(state.rounds) + 1
    tool = calls[0].tool
    if gate == GATE_EMPTY_PROBE:
        reason = EMPTY_PROBE_FEEDBACK_TEMPLATE.format(tool=tool)
        title = TITLE_EMPTY_PROBE_REJECTED_TEMPLATE.format(tool=tool)
        content = CONTENT_EMPTY_PROBE_NOTICE_PREFIX + reason
        for call in calls:  # 空手探查记指纹（同参空手重发的判定键）
            for fingerprint in call.fingerprints:
                state.empty_probes.append(fingerprint)
    else:
        reason = SAME_PARAM_REPLAY_REASON
        title = TITLE_REPLAY_REJECTED_TEMPLATE.format(tool=tool)
        content = CONTENT_REPLAY_NOTICE_PREFIX + reason
    state.decision_error = reason  # 拒因回喂（既有通道）——模型据此重决策
    record_step(
        state,
        kind=kind,
        title=title,
        status=STEP_STATUS_REFUSED,
        payload={
            PAYLOAD_PHASE_KEY: PHASE,
            PAYLOAD_TOOL: tool,
            PAYLOAD_STATUS: "rejected",
            PAYLOAD_REJECTED_KEY: True,
            PAYLOAD_GATE_KEY: gate,
            PAYLOAD_FINGERPRINTS_KEY: fingerprints,
            PAYLOAD_ARGS_FINGERPRINT_KEY: fingerprints[0] if fingerprints else "",
            # 记账面参数：本次发射**各支参数逐字**（整发射拒的发射单元＝整批——行为 7 的「记参数」）
            # （`args_fingerprint` 仍＝发射指纹——两闸语义照 -05a 原样，本票不改）
            PAYLOAD_ARGS_KEY: [dict(call.args) for call in calls],
            PAYLOAD_CONSUMES_ROUND_KEY: consumes_round,
            PAYLOAD_REJECT_REASON_KEY: reason,
            # 发射级拒＝**工具未执行**（非失败档——`error` 与 `SubtaskExec.error` 同档语义留 None）；
            # 拒因经 `reject_reason` 机读在场；被拦子问题的结论档由 `_reject_replay` 落 `bad_args`
            **_signal_payload(),
        },
    )
    notice(state, type=NOTICE_SAME_PARAM_REPLAY, content=content)


def _rejection_streak(state: RunState, gate: str, fingerprints: Sequence[str]) -> int:
    """同一指纹的既有拦截次数（只读本块步记录——同指纹再次被拦即连续，自旋收敛）。"""
    wanted = list(fingerprints)
    count = 0
    for entry in state.steps:
        payload = entry.get("payload") if isinstance(entry, Mapping) else None
        if not isinstance(payload, Mapping) or payload.get(PAYLOAD_GATE_KEY) != gate:
            continue
        recorded = payload.get(PAYLOAD_FINGERPRINTS_KEY)
        if isinstance(recorded, list) and list(recorded) == wanted:
            count += 1
    return count


def _reject_replay(state: RunState, entry: _Entry) -> SubtaskExec:
    """同参重投闸（行为 14）：全支皆在实录＝拦——不执行工具，拒因回喂模型重决策。

    拦下支的账目形：`exec_status="failed"` ＋ `category="bad_args"`——拒因指令是**改参**
    （`refused` 是前置闸拒的终局档、`retryable` 是抖动档，两档皆不适用），故落修参档（回炉面）。
    """
    if entry.call is None:
        raise ValueError(f"同参重投闸失序：支缺派遣载荷 {entry.subtask_id!r}")
    _reject_emission(state, GATE_SAME_PARAM_REPLAY, [entry.call], STEP_EXECUTE)
    _store_subtask_result(
        state, entry, status=ERROR_BAD_ARGS, reason=SAME_PARAM_REPLAY_REASON, obs_count=0, ref=None
    )
    return SubtaskExec(
        subtask_id=entry.subtask_id,
        exec_status=EXEC_STATUS_FAILED,
        answered=False,
        error=ErrorClass(category=ERROR_BAD_ARGS, reason=SAME_PARAM_REPLAY_REASON),
        row_count=None,
        ref=None,
    )


# ── 一次派遣的落地（`tool` 帧 → 步 → 观察回流 → 记账 → 指纹）──────────────────────


def _consume(
    state: RunState,
    bus: EventBus,
    item: _Returned,
    store: RunStore | None,
    *,
    kind: str,
) -> _Consumed:
    """一次派遣的完整落地：结果归一（`result_projection`）→ 观察回流 → 步／帧／通知。"""
    call = item.call
    if item.retries:
        _record_retry_attempt(state, item, kind=kind)  # 首投如实留账（可事后复算）
    status, category, message = _status_of(item)
    materials: list[tuple[dict[str, Any], Observation]] = []
    fresh_material = 0
    ref: MaterialRef | None = None
    row_count: int | None = None
    answered = False
    projection: dict[str, Any] | None = None
    if status == _STATUS_OK and item.result is not None:
        projection = result_projection(item.result)
        raw_rows = [
            row for row in (projection.get("observations") or []) if isinstance(row, Mapping)
        ]
        fresh_material = sum(
            1 for row in raw_rows if str((row.get("locator") or {}).get("kind")) != "notice"
        )
        for raw in raw_rows:
            row, observation = _material(state, store, raw)
            state.observations.append(row)
            materials.append((row, observation))
            if observation.ref is not None and ref is None:
                ref = observation.ref
        state.last_result = projection
        row_count = len(materials)
        answered = any(
            (observation.content or "") != "" or observation.ref is not None
            for _row, observation in materials
        )
    payload: dict[str, Any] = {
        PAYLOAD_PHASE_KEY: PHASE,
        PAYLOAD_TOOL: call.tool,
        PAYLOAD_STATUS: status,
        PAYLOAD_ARGS_KEY: dict(call.args),
        PAYLOAD_ARGS_FINGERPRINT_KEY: payload_fingerprint(call.args),
        PAYLOAD_REJECT_REASON_KEY: message if status != _STATUS_OK else None,
        # 机读信号三键（落引用／失败／缺参三面）：`category` 仅失败档非空（ok／ask 档＝None，
        # 挂起不是失败）——`error.reason` 与上方 `reject_reason` 同变量、同写入点
        **_signal_payload(
            row_count=row_count, ref=ref, category=category, reason=message
        ),
    }
    if call.subtask_id:
        payload[PAYLOAD_SUBTASK_ID_KEY] = call.subtask_id
        payload[PAYLOAD_CHAIN_KEY] = call.chain
    record_step(
        state,
        kind=kind,
        title=_title_of(kind, call, status),
        status=_step_status(status),
        payload=payload,
    )
    bus.emit(
        EVENT_TOOL,
        {
            PAYLOAD_TOOL: call.tool,
            PAYLOAD_STATUS: status,
            PAYLOAD_SEQ: int(state.steps[-1][PAYLOAD_SEQ]),  # 步序号（record_step 内置取号）
            PAYLOAD_MESSAGE: message,
        },
    )
    for row, observation in materials:
        bus.emit(
            EVENT_OBSERVATION,
            {
                PAYLOAD_INDEX: observation.seq,
                PAYLOAD_SOURCE: observation.source,
                PAYLOAD_CONTENT: (
                    observation.content
                    if observation.content is not None
                    else (observation.ref.summary if observation.ref is not None else "")
                ),
                PAYLOAD_TRUST: row[PAYLOAD_TRUST],
            },
        )
        if observation.ref is not None:
            notice(
                state,
                type=NOTICE_MATERIAL_TRUNCATED,
                content=CONTENT_REF_DISCLOSURE_TEMPLATE.format(
                    source=observation.source,
                    row_count=observation.ref.row_count,
                    handle=observation.ref.handle,
                ),
            )
    if status == _STATUS_ASK and item.result is not None:
        _absorb_ask(state, bus, result_projection(item.result))
    if status == _STATUS_FAILED:
        _report_failure(state, call, category, message, subtask=bool(call.subtask_id))
    note(
        state,
        phase=LEDGER_NOTE_PHASE,
        title=f"{call.tool}：{status}",
        digest=_ledger_digest(call, status, row_count, category, message),
    )
    return _Consumed(
        call=call,
        status=status,
        category=category,
        message=message,
        rows=[observation for _row, observation in materials],
        fresh_material=fresh_material,
        ref=ref,
        row_count=row_count,
        answered=answered,
    )


def _status_of(item: _Returned) -> tuple[str, str | None, str | None]:
    """派遣回执 →（status, category, message）；三态闭世界越界／定型违约＝fail-closed。"""
    if item.failure is not None:  # 超时／抛错的合成面（分类已归一）
        category, message = item.failure
        return _STATUS_FAILED, category, message
    result = item.result
    if result is None:
        raise ValueError("派遣回执既非超时亦无结果（内部失序）——fail-closed")
    if result.status == _STATUS_OK:
        return _STATUS_OK, None, None
    if result.status == _STATUS_ASK:
        return _STATUS_ASK, None, None
    if result.status != _STATUS_FAILED:
        raise ValueError(f"工具结果 status 越界（三态闭世界 ok｜failed｜ask）：{result.status!r}")
    error = result.error
    if error is None:  # ToolResult 定型不变式（failed 必携 error）——违约即 fail-closed
        raise ValueError("工具结果 status=failed 却无 error（定型不变式违约）")
    return _STATUS_FAILED, error.category, error.message


def _material(
    state: RunState, store: RunStore | None, raw: Mapping[str, Any]
) -> tuple[dict[str, Any], Observation]:
    """一条工具观察 → （材料行，窗口侧观察）：出处必带；非行集超阈才落引用。"""
    content = raw.get(PAYLOAD_CONTENT)
    text = content if isinstance(content, str) else ""
    source = str(raw.get(PAYLOAD_SOURCE) or "").strip()
    if not source:
        raise ValueError(MISSING_SOURCE_REASON)
    kind = str((raw.get("locator") or {}).get("kind") or "")
    row = dict(raw)
    row[PAYLOAD_INDEX] = len(state.observations) + 1  # 全局 [n] 序（＝规格 Observation.seq）
    row[PAYLOAD_TRUST] = trust_of(row)
    if kind in ROWSET_OBSERVATION_KINDS or len(text) <= BIG_RESULT_THRESHOLD_CHARS:
        return row, Observation(
            seq=int(row[PAYLOAD_INDEX]), content=text, ref=None, source=source
        )
    ref = _put_ref(store, text)
    row[PAYLOAD_CONTENT] = ref.summary  # 窗口只留摘要（不留全文——行为 4）
    row[PAYLOAD_REF_KEY] = {
        PAYLOAD_HANDLE_KEY: ref.handle,
        PAYLOAD_SUMMARY_KEY: ref.summary,
        PAYLOAD_ROW_COUNT_KEY: ref.row_count,
    }
    return row, Observation(
        seq=int(row[PAYLOAD_INDEX]), content=None, ref=ref, source=source
    )


def _put_ref(store: RunStore | None, text: str) -> MaterialRef:
    """原文落 `persistence` 公开面（可寻址 handle）＋窗口侧摘要（截断单点在 `persistence`）。"""
    if store is None:
        raise RuntimeError(_STORE_MISSING)
    blob = store.put_ref(text.encode("utf-8"))
    return MaterialRef(
        handle=blob.handle, summary=head(text), row_count=_row_count(text)
    )


def _row_count(text: str) -> int:
    """被落引用原文的行数（非空行计数，至少 1——空原文不得报 0 行）。"""
    return sum(1 for line in text.splitlines() if line.strip()) or 1


def _absorb_ask(state: RunState, bus: EventBus, projection: Mapping[str, Any]) -> None:
    """工具侧缺参／审批 → `need_input` 挂起：落 `pending_ask` ＋ 发 `ask` 帧（挂起信号）。

    `pending_ask` 取 `result_projection` 的 `ask` 投影（逐字段原样、空值与缺省可区分）；
    `ask` 帧载荷＝`{frame, run_id}`（真源 `synth/S6` §一 ask 行），使恢复入口可从此帧接续。
    """
    frame = projection.get("ask")
    state.pending_ask = dict(frame) if isinstance(frame, Mapping) else None
    bus.emit(EVENT_ASK, {PAYLOAD_FRAME: state.pending_ask, PAYLOAD_RUN_ID: state.run_id})


def _report_failure(
    state: RunState,
    call: _Call,
    category: str | None,
    message: str | None,
    *,
    subtask: bool,
) -> None:
    """失败如实披露（「不降级与静默禁令」节）：分型通知；`bad_args` 并落拒因回喂面。"""
    reason = message or _DEFAULT_FAILURE_REASON
    if category == ERROR_REFUSED:
        if subtask:
            notice(
                state,
                type=NOTICE_SUBTASK_REFUSED,
                content=CONTENT_SUBTASK_REFUSED_TEMPLATE.format(
                    subtask=call.subtask_id, reason=reason
                ),
            )
        else:
            notice(state, type=ERROR_REFUSED, content=f"口径/数据闸拒——拒因如实转答：{reason}")
        return
    if category == ERROR_BAD_ARGS:
        state.decision_error = reason  # 拒因回喂——修参重决策（行为 3）
        notice(
            state,
            type=NOTICE_DECISION_REJECTED,
            content=CONTENT_DECISION_REJECTED_TEMPLATE.format(reason=reason),
        )
        return
    if subtask:
        notice(
            state,
            type=NOTICE_SUBTASK_FAILED,
            content=CONTENT_SUBTASK_FAILED_TEMPLATE.format(
                subtask=call.subtask_id, reason=reason
            ),
        )
        return
    notice(
        state,
        type=NOTICE_TOOL_UNAVAILABLE,
        content=CONTENT_TOOL_UNAVAILABLE_TEMPLATE.format(tool=call.tool, reason=reason),
    )


def _title_of(kind: str, call: _Call, status: str) -> str:
    if kind == STEP_DISCOVER:
        return TITLE_DISCOVER_TEMPLATE.format(tool=call.tool, status=status)
    return TITLE_EXECUTE_TEMPLATE.format(
        tool=call.tool, status=status, subtask=call.subtask_id
    )


def _step_status(status: str) -> str:
    """步态如实：失败＝`failed`（挂起与成功＝`ok`——挂起不是失败，闭世界三值之内）。"""
    return STEP_STATUS_FAILED if status == _STATUS_FAILED else STEP_STATUS_OK


def _ledger_digest(
    call: _Call,
    status: str,
    row_count: int | None,
    category: str | None,
    message: str | None,
) -> str:
    """执行台账摘要（「参数 → 结果：N 行／分型拒因」形——迁移照抄，承载位换、文本不变）。"""
    params = payload_fingerprint(call.args)
    if status == _STATUS_OK:
        return f"{call.tool} 参数：{params} → 结果：{row_count or 0} 行"
    if status == _STATUS_ASK:
        return f"{call.tool} 参数：{params} → 结果：0 行（挂起：审批）"
    reason = message or "校验未过"
    if category == ERROR_BAD_ARGS:
        return f"{call.tool} 参数：{params} → 校验拒（拒因：{reason}）"
    if category == ERROR_RETRYABLE:
        return f"{call.tool} 参数：{params} → 暂不可用（拒因：{reason}）"
    return f"{call.tool} 参数：{params} → 闸拒（拒因：{reason}）"


def _category_of(item: _Returned) -> str | None:
    return _status_of(item)[1]


# ── 逐子问题账（`SubtaskExec` ＋ `subtask_results` 簿记）─────────────────────────


def _subtask_exec(state: RunState, entry: _Entry, consumed: _Consumed) -> SubtaskExec:
    """派遣支的账目并 `subtask_results` 簿记（成功实录指纹／失败如实留痕）。"""
    call = consumed.call
    if consumed.status == _STATUS_OK:
        exec_status = EXEC_STATUS_OK
        error: ErrorClass | None = None
        _store_subtask_result(
            state,
            entry,
            status=_STATUS_OK,
            reason="",
            obs_count=consumed.row_count or 0,
            ref=consumed.ref,
        )
        # 主执行实录（同参重投闸的比对面）：**成功执行**才算已执行（升级/拒不改线，
        # 修正后重发不被误拦——V1 同款注释；V1 的 ask 记账面按上注收窄见模块注）。
        state.executed_payloads.extend(call.fingerprints)
    elif consumed.status == _STATUS_ASK:
        exec_status = EXEC_STATUS_NEED_INPUT
        error = None  # 挂起不是失败；恢复后同参重入（不记实录、不记产物——不重放已完成部分）
    else:
        exec_status = EXEC_STATUS_FAILED
        error = ErrorClass(
            category=consumed.category or ERROR_RETRYABLE,
            reason=consumed.message or _DEFAULT_FAILURE_REASON,
        )
        _store_subtask_result(
            state,
            entry,
            status=str(consumed.category or ERROR_RETRYABLE),
            reason=consumed.message or _DEFAULT_FAILURE_REASON,
            obs_count=0,
            ref=None,
        )
    return SubtaskExec(
        subtask_id=call.subtask_id,
        exec_status=exec_status,
        answered=consumed.answered,
        error=error,
        row_count=consumed.row_count,
        ref=consumed.ref,
    )


def _store_subtask_result(
    state: RunState,
    entry: _Entry,
    *,
    status: str,
    reason: str,
    obs_count: int,
    ref: MaterialRef | None,
) -> None:
    """逐子问题产物簿记（同 id 只留最新——V1 同款；`ref`＝引用投影，供恢复面读回）。"""
    record: dict[str, Any] = {
        "id": entry.subtask_id,
        "status": status,
        "reason": reason,
        "question": entry.question,
        "obs_count": obs_count,
        "fingerprint": entry.fingerprints[0] if entry.fingerprints else "",
        "chain": entry.chain,
        PAYLOAD_REF_KEY: (
            None
            if ref is None
            else {
                PAYLOAD_HANDLE_KEY: ref.handle,
                PAYLOAD_SUMMARY_KEY: ref.summary,
                PAYLOAD_ROW_COUNT_KEY: ref.row_count,
            }
        ),
    }
    state.subtask_results = [
        item
        for item in state.subtask_results
        if not (isinstance(item, Mapping) and str(item.get("id")) == entry.subtask_id)
    ]
    state.subtask_results.append(record)
