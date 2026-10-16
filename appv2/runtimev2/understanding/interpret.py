"""读题相位本体（`interpret`）：任务书装配 → 模型读题 → 严格解析 → 按 `route` 机械分派。

真源＝`specs/understanding.md` 接口定义（卡面签名 `interpret(state: RunState) -> Understanding |
Direct`）与行为 1–12；`specs/modules.md` `## understanding` 卡（职责：读题——装配任务书 →
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
   字段／类型不符／`route` 越界）→ **拒因回喂重试恰一次（行为 13）**：向链尾追加拒因载荷
   （`_append_schema_feedback`——【拒因】取 `parsing.understanding_schema_feedback` 的具体不合项、
   【期望形】＋尾行见 `feedback`）→ 同相位再读一次；**仍拒**才 **抛 `UnderstandingParseError`**
   （携原始应答片段），**不静默降级**、无两行式回退。上限**恰一次**（结构化无环）；两次调用各记
   一条步（`call_model` 单点）；回喂只入链与过程档案（`dialogue` 零写入）；**不补默认、不改写
   原话**。
5. **分派（行为 4／6／8／12）**：**只按 `route` 取值**（闭世界 `full`｜`direct`）——
   `full` → 理解字段双出口（`state.understanding`／`state.metric_candidates` ＋ `text` 事件
   `kind=understanding`）＋ 候选出自名录对账（违约即如实上报，不静默丢弃）；
   `direct` → **先过直答结构核验（行为 5）**：命中闭世界（数值形／名录内指标名／结构卡内表名）
   ＝判不合格 → **退回 `route="full"` 的 `Understanding`＋过程档案一条「直答退回」注记**（不抛错、
   不静默、不直答收口）；未命中 → 直答收口旁路（`bookkeeping.direct_answer` 三键）。**单出口互斥**：
   一次调用只回两形之一。**「去哪」的路由决策不归本块**（写字段≠做路由决策——`orchestration` 读
   `next_intent` 定跳转）。**路由默认倾向 fail-closed（行为 11）是给模型的判断原则**（交付面＝
   指令区合同与题干段收束句，随任务书装配；真源 `walk/05-理解-定路由.md` §七 第 3 条）——程序侧
   不判相关性（零词面词表）：确定无关的寒暄直答由结构核验把口（命中即退回），拿不准／可能有关／
   灰区归完整流程由模型按该原则判、程序按 `route` 分派。

**接缝纪律（本块自立的调用面约定，登记见票面回报）**：`bus`（per-run 总线，编排块持有、注入各
相位——`specs/modules.md` `## transport` 卡）为**必给**注入面：未注入＝调用方断线，入口即
fail-closed 抛错（同 `gateway_adapter._configured_completer` 先例——「无出口不静默兜底」）；
`watermark`（水位文本，B14：时间量只经入参注入，本块零时钟接触）。二者皆为关键词注入，不改卡面
签名 `interpret(state)` 的实参形（同 `prompts.assemble_task_book` 的 `watermark` 注入先例）。
"""

from __future__ import annotations

from appv2.runtimev2.bookkeeping import append_message, call_model, direct_answer, note
from appv2.runtimev2.parsing import (
    ROUTE_FULL,
    Direct,
    Understanding,
    parse_understanding,
    understanding_schema_feedback,
)
from appv2.runtimev2.state import RunState
from appv2.runtimev2.transport import EventBus
from appv2.runtimev2.understanding.assembly import ensure_task_book
from appv2.runtimev2.understanding.closure import direct_assertion_hits
from appv2.runtimev2.understanding.constants import (
    DIRECT_REJECT_NOTE_TITLE,
    MODEL_CALLER,
    PHASE,
    READ_NOTE_TITLE,
    RETRY_NOTE_TITLE,
    ROLE_ASSISTANT,
    ROLE_USER,
    TEXT_EVENT,
    TEXT_EVENT_KIND,
)
from appv2.runtimev2.understanding.errors import UnderstandingParseError
from appv2.runtimev2.understanding.feedback import schema_feedback
from appv2.runtimev2.understanding.reporting import (
    report_candidate_violation,
    report_direct_rejected,
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
_DIRECT_REJECT_DIGEST = (
    "直答文本命中闭世界（{hits}）——判不合格：退回 route=\"full\" 走完整流程"
    "（不抛错、不静默、不直答收口）"
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
    之一；应答不合 schema／`route` 越界 → 抛 `UnderstandingParseError`（行为 7：不返回半成品）；
    直答文本命中闭世界（行为 5）→ **退回 `route="full"` 的 `Understanding`**（不抛错、不静默、
    不直答收口——退回归 `_reject_direct`）。
    **schema 拒回喂重试恰一次（行为 13，2026-10-16 补·流水 67）**：首读不合 schema **不当场判死**
    ——向链尾追加拒因载荷（`feedback.schema_feedback`：【拒因】＋【期望形】＋尾行；不合项取
    `parsing.understanding_schema_feedback` 的唯一诊断出口）→ **同相位再读一次**；仍拒才抛
    `UnderstandingParseError`（编排收 `failed` 不变）。**拒因回喂＝修参、非降级**：不补默认、不改写
    模型原话、不降级提取；上限**恰一次**（结构化——无环，钉死）。
    过程态一律经 `bookkeeping` 唯一写口落（步／链／过程档案／通知／意图），本块零直写。
    """
    channel = _require_bus(bus)
    ensure_task_book(state, watermark=watermark)
    parsed, raw = _read_and_parse(state)
    if parsed is None:
        _append_schema_feedback(state, raw)
        parsed, raw = _read_and_parse(state)
    if parsed is None:
        report_parse_failure(state, raw)
        raise UnderstandingParseError(_PARSE_FAILURE_REASON, raw=raw)
    if isinstance(parsed, Direct):
        hits = direct_assertion_hits(state, parsed.text)
        if hits:
            return _reject_direct(state, parsed, hits, channel)
        return _dispatch_direct(state, parsed)
    return _dispatch_full(state, parsed, channel)


def _read_and_parse(state: RunState) -> tuple[Understanding | Direct | None, str]:
    """一次读题（模型调用单点发起 ＋ 链尾留痕 ＋ 过程档案留痕）→ 解析三态。

    首读与重试**同形复用**（重试＝同相位再读一次，非另开路径）：整条链送模型（`pin-22` 只追加）、
    应答追加链尾（`ROLE_ASSISTANT`）、模型原话入过程档案（行为 3／9）；调用记账归
    `bookkeeping.call_model` 单点——**两次调用各记一条步**（本支不另记步）。
    """
    raw = call_model(state, MODEL_CALLER, list(state.messages))
    append_message(state, role=ROLE_ASSISTANT, content=raw)
    note(state, phase=PHASE, title=READ_NOTE_TITLE, digest=raw)
    return parse_understanding(raw), raw


def _append_schema_feedback(state: RunState, raw: str) -> None:
    """schema 拒回喂载荷追加链尾（行为 13）：`messages` 追加一条 ＋ 过程档案一条注记。

    载荷＝【拒因】（`parsing.understanding_schema_feedback`——schema 单点出的「哪一条」）＋【期望形】
    ＋尾行；**追加形**（拒因落链尾、前置内容逐字不动）＝前缀延伸不破（`pin-22`）。角色取 `ROLE_USER`
    （回喂＝系统侧给模型的指令条，同澄清面增量条体例）；**`dialogue` 零写入**（过程记录不混层——
    行为 9／钉 `pin-26` 渲染面）。本支**不发 notice、不记步、不落任何判定字段**：回喂失败的如实
    上报归 `report_parse_failure`、调用记账归 `call_model` 单点——副作用面**零增**（不重复上报、
    不翻倍）。
    """
    payload = schema_feedback(understanding_schema_feedback(raw))
    append_message(state, role=ROLE_USER, content=payload)
    note(state, phase=PHASE, title=RETRY_NOTE_TITLE, digest=payload)


def _reject_direct(
    state: RunState, direct: Direct, hits: tuple[tuple[str, str], ...], bus: EventBus
) -> Understanding:
    """直答结构核验不合格 → 退回 `route="full"` 的 `Understanding`（行为 5；唯一合法回退口径）。

    **不抛错（不借 `UnderstandingParseError` 表达）、不静默、不直答收口**——三步固定序：

    1. **注记**：过程档案记一条「直答退回」（`bookkeeping.note`——钉 `pin-26` 渲染面：过程记录入
       档案、`dialogue` 零写入；本块零直写）；
    2. **如实上报**：机读信号两件套（报告步 payload 携逐条命中项 ＋ notice——「不降级与静默禁令」
       节的「直答退回」类）；
    3. **走 `full` 分派**：返回定型 `Understanding`（`text`＝模型原话如实，**候选不发明**——直答应答
       本无候选，故 `metric_candidates` 为空）——理解双出口与 `text` 事件随 full 分派同形出场。
    """
    note(state, phase=PHASE, title=DIRECT_REJECT_NOTE_TITLE, digest=_reject_digest(hits))
    report_direct_rejected(state, direct.text, hits)
    escalated = Understanding(text=direct.text, metric_candidates=[], route=ROUTE_FULL)
    return _dispatch_full(state, escalated, bus)


def _reject_digest(hits: tuple[tuple[str, str], ...]) -> str:
    """退回注记正文（命中的闭世界逐条点名——注记与上报同一次判定产物）。"""
    names = "、".join(f"{kind}:{token}" for kind, token in hits)
    return _DIRECT_REJECT_DIGEST.format(hits=names)


def _dispatch_direct(state: RunState, direct: Direct) -> Direct:
    """`route="direct"` 分派：直答收口旁路（行为 6 单出口的直答形）。

    经 `bookkeeping.direct_answer` 落三键（`draft`／`draft_kind="direct"`／`next_intent="answer"`）
    ——免起草免核验的**同一出口**（收口旁路单点；本块不另写收口面）。

    **入口把守（行为 5，RT-W4-01b 落地）**：本函数只接**已过直答结构核验**的直答（`interpret` 在
    此处之前判 `direct_assertion_hits`——命中即改走 `_reject_direct` ＋ `full` 分派）；本函数自身
    零判据（行为 4：程序只按 `route` 分派，不在此重判）。
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
