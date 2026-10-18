"""orchestration.explore —— 作答侧有界再探的**执行与回链**（V2-96 D5；真源 §五·5.2／5.3）。

本模块只做三件事（业务语义在相位块内）：

1. **执行**（`run_explore`）：逐请求过闸（指纹拒重／`fetch_*` 只许已见来源）→ 经 `tools` 公开面
   派遣（`doc_retrieve` 走 L0→L1 新召回；`fetch_section`／`fetch_report` 走 KB 只读）→ 新观察并入
   L2（`fragment_id` 去重、`[n]` 序号续排、`observation` 帧复用既有帧型）；
2. **回链**：追加一条 user 增量（头部「补充检索（第 k/2 次，还剩 m 次）」＋模型上一轮 requests
   原文＋新入选材料经 L3 选席）→ `explore_rounds += 1` → 意图回 `answer`；
3. **硬停止**（`hard_stop`）：轮数到顶仍出 `explore` → 追加「只能如实作答」指令并交回**程序
   确定性缺口正文**（正文含「已试 N 次检索（列出）、仍缺 X」）——**不判 failed**。

留痕：每轮一条 step（`kind=observe`）payload 携 `explore` 面（requests 原文／执行／命中／追加／
token）；`retrieval_calls` 行由 `doc_retrieve` handler 既有单点落（本模块不重复记账）。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from appv2.runtimev2.answering import PAYLOAD_EXPLORE_KEY, answer_anchors
from appv2.runtimev2.bookkeeping import (
    append_message,
    note,
    record_step,
    result_projection,
    set_intent,
    tool_context,
)
from appv2.runtimev2.context import render_materials, trust_of
from appv2.runtimev2.execution import EVENT_OBSERVATION, PAYLOAD_INDEX
from appv2.runtimev2.state import INTENT_ANSWER, MAX_EXPLORE_ROUNDS, STEP_OBSERVE, RunState
from appv2.runtimev2.transport import EventBus
from appv2.tools import (
    DOC_RETRIEVE,
    FETCH_REPORT,
    FETCH_SECTION,
    ToolRegistry,
)

# 过程档案相位标记与步标题（本块自有文案；步型引 `state.STEP_OBSERVE` 真源）。
EXPLORE_PHASE = "explore"
EXPLORE_STEP_TITLE = "补充检索"
# 拒因原文（机读回喂面——增量消息逐条照抄）。
REJECT_REPEAT = "重复请求（同参指纹已检索过——不重复派遣）"
REJECT_UNSEEN = "只能对已见来源要更多（该来源未在材料里出现过）"
# 观察帧载荷键名（键名真源＝`execution.constants` 的 `PAYLOAD_*` 族——本处只作帧形装配；
# orchestration 非 R2 源，故按取值指针落此，不引其深层子模块）。
_OBSERVATION_SOURCE = "source"
_OBSERVATION_CONTENT = "content"
_OBSERVATION_TRUST = "trust"
_OBSERVATION_PAYLOAD = "payload"

# 增量消息头（真源 §五·5.2 逐字「补充检索（第 k/2 次，还剩 m 次）」）。
INCREMENT_HEAD = "补充检索（第 {k}/{cap} 次，还剩 {left} 次）"
INCREMENT_REQUESTS_HEAD = "上一轮检索请求（原文）："
INCREMENT_REJECTED_HEAD = "以下请求被拒（不派遣）："
INCREMENT_EXECUTED_HEAD = "执行结果："
# 硬停止指令（真源 §五·5.3「强制作答；正文须含『已试 N 次检索（列出）、仍缺 X』」）。
FORCED_INSTRUCTION_HEAD = (
    "补充检索预算已用尽（已试 {rounds} 次，每轮 ≤2 请求）——只能如实作答，"
    "不得再发射 explore 检索意图。"
)
FORCED_INSTRUCTION_BODY = (
    "答案正文必须写明：已试 {rounds} 次检索（逐条列出已尝试的请求）、仍缺什么（原因）。"
)
FORCED_BODY = "已试 {rounds} 次补充检索（{tried}），仍缺：{reason}。"


def request_fingerprint(request: Mapping[str, Any]) -> str:
    """请求指纹（真源 §五·5.1「`tool`＋`query` 或 `report_id+section`」）——拒重判据单点。"""
    tool = str(request.get("tool") or "")
    if tool == DOC_RETRIEVE:
        return f"{tool}|{str(request.get('query') or '').strip()}"
    section = str(request.get("section") or "").strip()
    return f"{tool}|{str(request.get('report_id') or '').strip()}|{section}"


def tool_args(request: Mapping[str, Any]) -> dict[str, Any]:
    """explore 请求 → 工具 args（逐工具 schema 面；缺省键不造）。"""
    tool = str(request.get("tool") or "")
    if tool == DOC_RETRIEVE:
        args: dict[str, Any] = {"question": str(request.get("query") or "")}
        anchors = request.get("anchors")
        if isinstance(anchors, list):
            kept = [str(item).strip() for item in anchors if str(item).strip()]
            if kept:
                args["anchors"] = kept
        return args
    args = {"report_id": str(request.get("report_id") or "").strip()}
    if tool == FETCH_SECTION:
        section = str(request.get("section") or "").strip()
        if section:
            args["section"] = section
        return args
    max_chars = request.get("max_chars")
    if isinstance(max_chars, int) and not isinstance(max_chars, bool) and max_chars > 0:
        args["max_chars"] = max_chars
    return args


def seen_sources(state: RunState) -> set[str]:
    """L2 窗口已见来源集（观察行的 `source` ＋ `locator.report`——报告名口径）。

    `fetch_*` 的 `report_id` 只许落在此集内（真源 §五·5.1「必须是 L2/L3 窗口里出现过的来源」）。
    """
    seen: set[str] = set()
    for row in state.observations:
        if not isinstance(row, Mapping):
            continue
        source = str(row.get("source") or "").strip()
        if source:
            seen.add(source)
        locator = row.get("locator")
        if isinstance(locator, Mapping):
            report = str(locator.get("report") or "").strip()
            if report:
                seen.add(report)
    return seen


def _fragment_ids(state: RunState) -> set[str]:
    """已入 L2 的片段身份集（`locator.fragment_id`——去重判据）。"""
    found: set[str] = set()
    for row in state.observations:
        if not isinstance(row, Mapping):
            continue
        locator = row.get("locator")
        if isinstance(locator, Mapping):
            fragment_id = str(locator.get("fragment_id") or "").strip()
            if fragment_id:
                found.add(fragment_id)
    return found


def absorb_observations(
    state: RunState, bus: EventBus, result: Any
) -> list[dict[str, Any]]:
    """工具结果 → 新观察并入 L2（`fragment_id` 去重、`[n]` 序号续排、`observation` 帧复用）。

    出处必带由 `tools` 面保证（INV-1）；空来源行如实跳过（不猜、不补）。
    """
    projection = result_projection(result)
    rows = [
        row for row in (projection.get("observations") or []) if isinstance(row, Mapping)
    ]
    existing = _fragment_ids(state)
    appended: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        locator = row.get("locator")
        locator = dict(locator) if isinstance(locator, Mapping) else {}
        fragment_id = str(locator.get("fragment_id") or "").strip()
        if fragment_id and fragment_id in existing:
            continue
        row[PAYLOAD_INDEX] = len(state.observations) + 1  # 全局 [n] 序续排
        row[_OBSERVATION_TRUST] = trust_of(row)
        state.observations.append(row)
        appended.append(row)
        if fragment_id:
            existing.add(fragment_id)
        frame: dict[str, Any] = {
            PAYLOAD_INDEX: row[PAYLOAD_INDEX],
            _OBSERVATION_SOURCE: str(row.get("source") or ""),
            _OBSERVATION_CONTENT: str(row.get("content") or ""),
            _OBSERVATION_TRUST: row[_OBSERVATION_TRUST],
        }
        slot = locator.get(_OBSERVATION_PAYLOAD)
        if isinstance(slot, Mapping):
            frame[_OBSERVATION_PAYLOAD] = dict(slot)
        bus.emit(EVENT_OBSERVATION, frame)
    return appended


async def run_explore(
    state: RunState,
    *,
    bus: EventBus,
    registry: ToolRegistry,
    max_observations: int,
) -> dict[str, Any]:
    """执行一轮再探：过闸 → 派遣 → 新观察并入 L2 → 追加 user 增量 → 意图回 `answer`。"""
    exp = state.pending_explore if isinstance(state.pending_explore, dict) else {}
    requests = [
        dict(item) for item in (exp.get("requests") or []) if isinstance(item, Mapping)
    ]
    seen = seen_sources(state)
    context = tool_context(state)
    executed: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    appended: list[dict[str, Any]] = []
    for request in requests:
        fingerprint = request_fingerprint(request)
        if fingerprint in state.explore_fingerprints:
            rejected.append({"request": dict(request), "reason": REJECT_REPEAT})
            continue
        tool = str(request.get("tool") or "")
        if tool in (FETCH_SECTION, FETCH_REPORT) and (
            str(request.get("report_id") or "").strip() not in seen
        ):
            rejected.append({"request": dict(request), "reason": REJECT_UNSEEN})
            continue
        args = tool_args(request)
        state.explore_fingerprints.append(fingerprint)
        result = await registry.call(tool, args, context)
        rows = absorb_observations(state, bus, result) if result.status == "ok" else []
        appended.extend(rows)
        error = result.error
        executed.append(
            {
                "tool": tool,
                "args": args,
                "status": result.status,
                "observations": len(rows),
                "reject_reason": error.message if error is not None else None,
            }
        )
    content = explore_increment(
        state,
        exp=exp,
        requests=requests,
        executed=executed,
        rejected=rejected,
        appended=appended,
        max_observations=max_observations,
    )
    append_message(state, role="user", content=content)
    state.explore_rounds += 1
    state.pending_explore = None
    set_intent(state, INTENT_ANSWER)
    face: dict[str, Any] = {
        "round": state.explore_rounds,
        "requests": [dict(item) for item in requests],
        "executed": executed,
        "rejected": rejected,
        # `hits`＝实质新料（非 notice 声明支——同 `execution` 的 fresh_material 口径）；
        # `appended`＝本轮追加的 user 增量条数（恰 1）；`token`＝增量文本 token 估算。
        "hits": sum(
            1
            for row in appended
            if str((row.get("locator") or {}).get("kind")) != "notice"
        ),
        "appended": 1,
        "token": _estimate_tokens(content),
    }
    record_step(
        state,
        kind=STEP_OBSERVE,
        title=EXPLORE_STEP_TITLE,
        payload={PAYLOAD_EXPLORE_KEY: face},
    )
    note(
        state,
        phase=EXPLORE_PHASE,
        title=f"补充检索：第 {state.explore_rounds} 轮",
        digest=json.dumps(
            {"executed": executed, "rejected": rejected, "hits": len(appended)},
            ensure_ascii=False,
        ),
    )
    return face


def explore_increment(
    state: RunState,
    *,
    exp: Mapping[str, Any],
    requests: Sequence[Mapping[str, Any]],
    executed: Sequence[Mapping[str, Any]],
    rejected: Sequence[Mapping[str, Any]],
    appended: Sequence[Mapping[str, Any]],
    max_observations: int,
) -> str:
    """增量 user 消息：头部＋requests 原文（照抄）＋拒因/执行如实＋新入选材料（[n]，经 L3）。"""
    k = state.explore_rounds + 1
    left = max(0, MAX_EXPLORE_ROUNDS - k)
    lines = [INCREMENT_HEAD.format(k=k, cap=MAX_EXPLORE_ROUNDS, left=left)]
    raw = str(exp.get("raw") or "").strip()
    if not raw:
        raw = json.dumps([dict(item) for item in requests], ensure_ascii=False)
    lines.append(INCREMENT_REQUESTS_HEAD)
    lines.append(raw)
    if rejected:
        lines.append(INCREMENT_REJECTED_HEAD)
        lines.extend(
            f"- {json.dumps(dict(item['request']), ensure_ascii=False)}——{item['reason']}"
            for item in rejected
        )
    if executed:
        lines.append(INCREMENT_EXECUTED_HEAD)
        lines.extend(
            f"- {item['tool']}：{item['status']}，新观察 {item['observations']} 条"
            for item in executed
        )
    if appended:
        materials_text, _meta = render_materials(
            [dict(row) for row in appended],
            max_observations=max_observations,
            anchors=answer_anchors(state),
        )
        lines.append(materials_text)
    return "\n".join(lines)


def hard_stop(state: RunState) -> str:
    """硬停止（轮数到顶仍出 `explore`）：追加「只能如实作答」指令 ＋ 交回程序确定性缺口正文。

    指令进链（模型据此作答）；正文是**兜底**（模型仍出 explore 时由作答相位直接采用）——
    含「已试 N 次检索（列出）、仍缺 X」，**不判 failed**（真源 §五·5.3）。
    """
    exp = state.pending_explore if isinstance(state.pending_explore, dict) else {}
    rounds = state.explore_rounds
    tried = "；".join(_tried_texts(state)) or "（无）"
    append_message(
        state,
        role="user",
        content=(
            FORCED_INSTRUCTION_HEAD.format(rounds=rounds)
            + "\n"
            + FORCED_INSTRUCTION_BODY.format(rounds=rounds)
            + "\n已尝试："
            + tried
        ),
    )
    reason = str(exp.get("reason") or "").strip() or "材料不足说明不可用"
    return FORCED_BODY.format(rounds=rounds, tried=tried, reason=reason)


def _tried_texts(state: RunState) -> list[str]:
    """已尝试请求列（从再探轮步 payload 的 `explore.executed` 逐条取——零第二套簿记）。"""
    texts: list[str] = []
    for step in state.steps:
        if not isinstance(step, Mapping):
            continue
        payload = step.get("payload")
        if not isinstance(payload, Mapping):
            continue
        face = payload.get(PAYLOAD_EXPLORE_KEY)
        if not isinstance(face, Mapping) or "round" not in face:
            continue
        for item in face.get("executed") or ():
            if not isinstance(item, Mapping):
                continue
            texts.append(_tried_text(str(item.get("tool") or ""), item.get("args")))
    return texts


def _tried_text(tool: str, args: Any) -> str:
    """单条尝试的文本形（工具＋定位面；`report_id`／`question` 逐字照抄）。"""
    body = args if isinstance(args, Mapping) else {}
    if tool == DOC_RETRIEVE:
        return f"{tool}（{body.get('question', '')}）"
    if tool == FETCH_SECTION:
        section = str(body.get("section") or "")
        return f"{tool}（{body.get('report_id', '')}·{section}）"
    return f"{tool}（{body.get('report_id', '')}）"


def _estimate_tokens(text: str) -> int:
    """token 估算＝chars/4（同 `context.compaction` 与网关兜底口径；本块无分词器，如实估算）。"""
    return len(text) // 4
