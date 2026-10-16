"""读题相位本体（`interpret`）：任务书装配 → 模型读题 → 严格解析 → 按 `route` 机械分派。

真源＝`specs/understanding.md` 接口定义（卡面签名 `interpret(state: RunState) -> Understanding |
Direct`）与行为 1–4／6–9／12；`specs/modules.md` `## understanding` 卡（职责：读题——装配任务书 →
模型读 → 解析；定路由）。**语义判断交模型，程序只按结论机械分派**：

1. **装配（行为 1／2／9）**：任务书经 `assembly.ensure_task_book` **每 run 只装配一次**（三区文本
   单点在 `prompts`，数据区从活体投影现取）；
2. **模型读题（框架红线）**：经 `bookkeeping.call_model` **单点发起**（`caller`＝理解桶）——
   **本块不直引 `gateway_adapter`、不直引 `appv2.infra.llm_client`、不自建模型客户端**（R7 ＋
   「无旁路」行为断言）；整条对话链送进模型（`state.messages` 只追加——钉 `pin-22`）；
3. **留痕（行为 9／钉 `pin-26` 渲染面）**：模型应答以类型正确的消息**追加链尾**（对话链只追加——
   `specs/agent-loop.md` 行为 2 的追加式；模型原话只进过程档案与链上留痕），**`dialogue` 零写入**
   （过程记录不混层；「模型原话不进对话层」的对话层＝`state.dialogue`——`specs/state.md` 行为 6）；
4. **严格解析（行为 7）**：`parsing.parse_understanding(content)`；返 `None`（非合法 JSON／缺必填
   字段／类型不符／`route` 越界）→ **抛 `UnderstandingParseError`**（携原始应答片段），**不静默
   降级**、无两行式回退；
5. **分派（行为 4／6／8／12）**：**只按 `route` 取值**（闭世界 `full`｜`direct`）——
   `full` → 理解字段双出口（`state.understanding`／`state.metric_candidates` ＋ `text` 事件
   `kind=understanding`）＋ 候选出自名录对账（违约即如实上报，不静默丢弃）；
   `direct` → 直答收口旁路（`bookkeeping.direct_answer` 三键）。**单出口互斥**：一次调用只回两形
   之一。**「去哪」的路由决策不归本块**（写字段≠做路由决策——`orchestration` 读 `next_intent` 定
   跳转）。

**接缝纪律（本块自立的调用面约定，登记见票面回报）**：`bus`（per-run 总线，编排块持有、注入各
相位——`specs/modules.md` `## transport` 卡）为**必给**注入面：未注入＝调用方断线，入口即
fail-closed 抛错（同 `gateway_adapter._configured_completer` 先例——「无出口不静默兜底」）；
`watermark`（水位文本，B14：时间量只经入参注入，本块零时钟接触）。二者皆为关键词注入，不改卡面
签名 `interpret(state)` 的实参形（同 `prompts.assemble_task_book` 的 `watermark` 注入先例）。
"""

from __future__ import annotations

from appv2.runtimev2.bookkeeping import append_message, call_model, direct_answer, note
from appv2.runtimev2.parsing import Direct, Understanding, parse_understanding
from appv2.runtimev2.state import RunState
from appv2.runtimev2.transport import EventBus
from appv2.runtimev2.understanding.assembly import ensure_task_book
from appv2.runtimev2.understanding.constants import (
    MODEL_CALLER,
    PHASE,
    READ_NOTE_TITLE,
    ROLE_ASSISTANT,
    TEXT_EVENT,
    TEXT_EVENT_KIND,
)
from appv2.runtimev2.understanding.errors import UnderstandingParseError
from appv2.runtimev2.understanding.reporting import (
    report_candidate_violation,
    report_parse_failure,
)
from appv2.runtimev2.understanding.roster import metric_roster

_PARSE_FAILURE_REASON = (
    "读题应答不合 schema（非合法 JSON／缺必填字段／字段类型不符／route 越界闭世界 "
    '{"full","direct"}）——不猜、不取默认、不降级'
)
_BUS_MISSING = (
    "理解相位总线未注入（per-run 总线由编排块持有并注入）——理解旁白事件无出口，"
    "fail-closed：不静默丢弃（行为 12）"
)


def _require_bus(bus: EventBus | None) -> EventBus:
    """总线把守（fail-closed）：未注入即抛错——不做「无出口静默跳过」的降级。"""
    if bus is None:
        raise RuntimeError(_BUS_MISSING)
    return bus


def interpret(
    state: RunState,
    *,
    bus: EventBus | None = None,
    watermark: str = "",
) -> Understanding | Direct:
    """读题一步：装配 → 模型读 → 严格解析 → 按 `route` 机械分派（返回值＝定型载荷）。

    单出口互斥（行为 6）：返回 `Understanding`（`route="full"`）或 `Direct`（`route="direct"`）
    之一；应答不合 schema／`route` 越界 → 抛 `UnderstandingParseError`（行为 7：不返回半成品）。
    过程态一律经 `bookkeeping` 唯一写口落（步／链／过程档案／通知／意图），本块零直写。
    """
    channel = _require_bus(bus)
    ensure_task_book(state, watermark=watermark)
    raw = call_model(state, MODEL_CALLER, list(state.messages))
    append_message(state, role=ROLE_ASSISTANT, content=raw)
    note(state, phase=PHASE, title=READ_NOTE_TITLE, digest=raw)
    parsed = parse_understanding(raw)
    if parsed is None:
        report_parse_failure(state, raw)
        raise UnderstandingParseError(_PARSE_FAILURE_REASON, raw=raw)
    if isinstance(parsed, Direct):
        return _dispatch_direct(state, parsed)
    return _dispatch_full(state, parsed, channel)


def _dispatch_direct(state: RunState, direct: Direct) -> Direct:
    """`route="direct"` 分派：直答收口旁路（行为 6 单出口的直答形）。

    经 `bookkeeping.direct_answer` 落三键（`draft`／`draft_kind="direct"`／`next_intent="answer"`）
    ——免起草免核验的**同一出口**（收口旁路单点；本块不另写收口面）。

    〔接缝注〕`specs/understanding.md` 行为 5 的**直答结构核验（闭世界判据）**与「不合格退回
    `route="full"`」归 RT-W4-01b 承接：-B 在本函数**之前**插入核验面（命中 → 走 `full` 分派），
    本半面不预先落任何词面／形态判据（行为 4：程序只按 `route` 分派）。
    """
    direct_answer(state, direct.text)
    return direct


def _dispatch_full(state: RunState, understanding: Understanding, bus: EventBus) -> Understanding:
    """`route="full"` 分派：理解双出口（状态字段 ＋ `text` 事件）＋ 候选名录对账（行为 8／12）。

    候选**原样落状态**（如实，不静默丢弃）；名录外者经「如实上报」两件套（报告步 payload ＋
    notice）点名。事件载荷＝`{content, kind}`（真源 `synth/S6-事件与帧目录.md` §一 text 行）。
    """
    offenders = [
        name for name in understanding.metric_candidates if name not in metric_roster(state)
    ]
    state.understanding = understanding.text
    state.metric_candidates = list(understanding.metric_candidates)
    bus.emit(TEXT_EVENT, {"content": understanding.text, "kind": TEXT_EVENT_KIND})
    if offenders:
        report_candidate_violation(state, offenders, understanding.metric_candidates)
    return understanding
