"""读题相位本体（`interpret`）：任务书装配 → 模型读题 → 严格解析 → 按 `route` 机械分派。

真源＝`specs/understanding.md` 接口定义（卡面签名 `interpret(state: RunState) -> Understanding |
Direct`）与行为 1–12；`specs/modules.md` `## understanding` 卡（职责：读题——装配任务书 →
模型读 → 解析；定路由）。**语义判断交模型，程序只按结论机械分派**：

1. **装配（行为 1／2／9）**：任务书经 `assembly.ensure_task_book` **每 run 只装配一次**（三区文本
   单点在 `prompts`，数据区从活体投影现取）；**2026-10-17 H 批（角色分家）**：任务书拆两路——读题
   规章段（指令区＋输出契约区）经 `prompts.understand_system_contract` 走**调用级 system 注入参**
   （`call_model(system=…)`，不入链）；动态段（数据区＋题干段）仍作 user 条入链，**链首先挂背景块
   system 条**（每链恰一条，`assembly.ensure_task_book` 内、链为空时挂）；
2. **模型读题（框架红线）**：经 `bookkeeping.call_model` **单点发起**（`caller`＝理解桶）——
   **本块不直引 `gateway_adapter`、不直引 `appv2.infra.llm_client`、不自建模型客户端**（R7 ＋
   「无旁路」行为断言）；整条对话链送进模型（`state.messages` 只追加——钉 `pin-22`）；首次读与
   回喂重试**同形复用**（`_read_and_parse`），规章段两次同口注入；
3. **留痕（行为 9／钉 `pin-26` 渲染面）**：模型应答以类型正确的消息**追加链尾**（对话链只追加——
   `specs/agent-loop.md` 行为 2 的追加式；模型原话只进过程档案与链上留痕），**`dialogue` 零写入**
   （过程记录不混层；「模型原话不进对话层」的对话层＝`state.dialogue`——`specs/state.md` 行为 6）；
4. **严格解析（行为 7）**：`parsing.parse_understanding(content)`；返 `None`（非合法 JSON／缺必填
   字段／类型不符／`route` 越界）→ **先过确定性引号自修一次（行为 13 首段，2026-10-17 EB5a 补）**：
   `parsing.parse_with_quote_repair`（既有共用件，零模型零占轮）——修好＝受理（`emission_quote_repair`
   notice ＋「读题引号自修」注记），修不好才算拒；**仍拒** → **拒因回喂重试恰一次（行为 13）**：
   向链尾追加拒因载荷（`_append_schema_feedback`——【拒因】取
   `parsing.understanding_schema_feedback` 的具体不合项、【期望形】＋尾行见 `feedback`）→ 同相位
   再读一次（同样过引号自修受理）；**仍拒** → **收敛拒答**（行为 13 尾，2026-10-17 EB3 D4.4 补、
   文案随 EB5a 改）：如实上报两件套（notice ＋ 报告步——`report_parse_failure` 原样）＋
   `direct_answer` 落一条拒答正文（直答旁路三键）＋ 返回该 `Direct`——**run 不判 `failed`、
   不零交付**（旧「抛 `UnderstandingParseError` → 编排收 `failed`」随 D4.4 退役：真机证据
   `eval/results/frames/EB2-NQ-D2.json`——模型两次都在 JSON 字符串里带未转义引号，整 run 零交付；
   EB5a 起该形改由引号自修受理**真交付**，收敛支只承接自修也修不好的残形）。上限**恰一次**
   （结构化无环）；两次调用各记一条步（`call_model` 单点）；回喂只入链与过程档案
   （`dialogue` 零写入）；**不补默认、不改写原话、不降级提取**（引号自修＝**格式层**确定性修复：
   只把字符串值内的裸引号换中文引号，修后须全文可解析才受理——值内容逐字不动，零语义）。
5. **分派（行为 4／6／8／12）**：**只按 `route` 取值**（闭世界 `full`｜`direct`）——
   `full` → 理解字段双出口（`state.understanding`／`state.metric_candidates` ＋ **V2-82a 的
   `state.subjects`／`state.terms`**）＋ `text` 事件
   `kind=understanding`）＋ 候选出自名录对账（违约即如实上报，不静默丢弃）；**2026-10-17
   V2-82a**：模型给出的主体与程序预识别候选集合不一致时另记一条过程档案注记「主体识别分歧」
   （**只留痕不改判**——判定仍归模型，同数据区推荐行的「以你的判断为准」口径）；
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

from collections.abc import Sequence

from appv2.runtimev2.bookkeeping import (
    append_message,
    call_model,
    direct_answer,
    note,
    notice,
)
from appv2.runtimev2.parsing import (
    ROUTE_DIRECT,
    ROUTE_FULL,
    Direct,
    Understanding,
    parse_understanding,
    parse_with_quote_repair,
    understanding_schema_feedback,
)
from appv2.runtimev2.prompts import understand_system_contract
from appv2.runtimev2.state import RunState
from appv2.runtimev2.transport import EventBus
from appv2.runtimev2.understanding.assembly import ensure_task_book, program_candidates
from appv2.runtimev2.understanding.closure import direct_assertion_hits
from appv2.runtimev2.understanding.constants import (
    CONVERGE_DRAFT_TEMPLATE,
    CONVERGE_NOTE_TITLE,
    DIRECT_REJECT_NOTE_TITLE,
    MODEL_CALLER,
    NOTICE_EMISSION_QUOTE_REPAIR,
    PHASE,
    PROGRAM_CANDIDATE_EMPTY,
    PROGRAM_CANDIDATE_SEP,
    QUOTE_REPAIR_NOTE_TITLE,
    QUOTE_REPAIR_NOTICE_CONTENT,
    READ_NOTE_TITLE,
    RETRY_NOTE_TITLE,
    ROLE_ASSISTANT,
    ROLE_USER,
    SUBJECT_DIVERGENCE_DIGEST,
    SUBJECT_DIVERGENCE_LIMIT,
    SUBJECT_DIVERGENCE_NOTE_TITLE,
    TEXT_EVENT,
    TEXT_EVENT_KIND,
    TRUNCATION_MARK,
)
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
    之一；应答不合 schema／`route` 越界 → **回喂拒因重试恰一次，仍拒＝收敛拒答**（行为 13；
    返回 `Direct`——拒答正文，不抛错、不零交付）；
    直答文本命中闭世界（行为 5）→ **退回 `route="full"` 的 `Understanding`**（不抛错、不静默、
    不直答收口——退回归 `_reject_direct`）。
    **schema 拒回喂重试恰一次（行为 13，2026-10-16 补·流水 67）**：首读不合 schema **不当场判死**
    ——**先过确定性引号自修一次**（`parsing.parse_with_quote_repair`，2026-10-17 EB5a 补：修好＝受理
    ＋`emission_quote_repair` notice，零模型零占轮）→ 仍不合格才向链尾追加拒因载荷
    （`feedback.schema_feedback`：【拒因】＋【期望形】＋尾行；不合项取
    `parsing.understanding_schema_feedback` 的唯一诊断出口）→ **同相位再读一次**；仍拒 →
    **收敛拒答**（2026-10-17 EB3 D4.4 改判、EB5a 改文案：拒答正文经 `bookkeeping.direct_answer`
    落直答旁路三键 ＋ 原样返回该 `Direct`——run 不判 `failed`、不零交付；真机证据
    `eval/results/frames/EB2-NQ-D2.json`——模型两次都在 JSON 字符串里带未转义引号，旧形整 run
    零交付）。**拒因回喂＝修参、非降级**：不补默认、不改写模型原话、不降级提取；上限**恰一次**（结构化无环，
    钉死）。过程态一律经 `bookkeeping` 唯一写口落（步／链／过程档案／通知／意图），本块零直写。
    """
    channel = _require_bus(bus)
    ensure_task_book(state, watermark=watermark)
    parsed, raw = _read_and_parse(state)
    if parsed is None:
        _append_schema_feedback(state, raw)
        parsed, raw = _read_and_parse(state)
    if parsed is None:
        return _converge_refusal(state, raw)
    if isinstance(parsed, Direct):
        hits = direct_assertion_hits(state, parsed.text)
        if hits:
            return _reject_direct(state, parsed, hits, channel)
        return _dispatch_direct(state, parsed)
    return _dispatch_full(state, parsed, channel)


def _converge_refusal(state: RunState, raw: str) -> Direct:
    """两读皆不合 schema → **收敛拒答**（行为 13 尾，2026-10-17 EB3 D4.4 补）。

    三步固定序（照直答旁路与「如实上报」两件套的既有体例）：

    1. **如实上报**（既有面，原样）＝`report_parse_failure`：报告步（payload 携原始应答片段）
       ＋ notice（`decision_rejected` 族既有值）——**不静默**；
    2. **过程档案注记**＝一条「读题收敛拒答」（`pin-26` 渲染面：过程记录入档案、
       `dialogue` 零写入）；
    3. **直答旁路三键**＝`bookkeeping.direct_answer`（`draft`／`draft_kind="direct"`／
       `next_intent="answer"`）——run 走收口（`completed`），**不判 `failed`、不零交付**；返回值＝
       该 `Direct`（单出口互斥形的 direct 支）。

    拒答正文＝**程序生成的确定性文案**（不合项取同一诊断出口 `understanding_schema_feedback`——
    两处同一次判定产物，不各自生成）：**不猜、不取默认、不降级提取**；原始应答片段只进报告步与
    notice（机读面），不刷进用户正文。文案按 **2026-10-17 EB5a** 改：收敛句统一为「没能完全读懂
    这道题，请补充说明」＋**材料面如实**（本相位结构上零材料——检索尚未开始；照 `bookkeeping`
    触界收敛正文的零材料形）。
    """
    reason = understanding_schema_feedback(raw)
    report_parse_failure(state, raw)
    refusal = Direct(text=converge_draft(reason), route=ROUTE_DIRECT)
    note(state, phase=PHASE, title=CONVERGE_NOTE_TITLE, digest=refusal.text)
    direct_answer(state, refusal.text)
    return refusal


def converge_draft(reason: str) -> str:
    """收敛拒答正文（同一文案单点：`_converge_refusal` 与测试同源，不各写一份）。"""
    return CONVERGE_DRAFT_TEMPLATE.format(reason=reason or _PARSE_FAILURE_REASON)


def _read_and_parse(state: RunState) -> tuple[Understanding | Direct | None, str]:
    """一次读题（模型调用单点发起 ＋ 链尾留痕 ＋ 过程档案留痕）→ 解析三态。

    首读与重试**同形复用**（重试＝同相位再读一次，非另开路径）：整条链送模型（`pin-22` 只追加）、
    应答追加链尾（`ROLE_ASSISTANT`）、模型原话入过程档案（行为 3／9）；调用记账归
    `bookkeeping.call_model` 单点——**两次调用各记一条步**（本支不另记步）。

    **引号自修受理（行为 13 首段，2026-10-17 EB5a 补）**：严格解析不合格时**先过确定性引号自修
    一次**（既有共用件 `parsing.parse_with_quote_repair`——解析拒→自修→重解析，只重试一次、只做
    引号层修复，零模型零语义）——修好即**受理**（`emission_quote_repair` notice ＋ 过程档案注记；
    **不占回喂上限、不回喂、不占轮**——照澄清相位 `_dispatch` 同款体例）；修不好＝原样返回 `None`
    （交 `interpret` 走拒因回喂恰一次 → 仍拒＝收敛拒答）。
    """
    raw = call_model(
        state,
        MODEL_CALLER,
        list(state.messages),
        system=understand_system_contract(),
    )
    append_message(state, role=ROLE_ASSISTANT, content=raw)
    note(state, phase=PHASE, title=READ_NOTE_TITLE, digest=raw)
    parsed, quote_repaired = parse_with_quote_repair(_parse_or_reason, raw)
    if quote_repaired:
        notice(
            state,
            type=NOTICE_EMISSION_QUOTE_REPAIR,
            content=QUOTE_REPAIR_NOTICE_CONTENT,
        )
        note(state, phase=PHASE, title=QUOTE_REPAIR_NOTE_TITLE, digest=raw)
    return (None if isinstance(parsed, str) else parsed), raw


def _parse_or_reason(content: str) -> Understanding | Direct | str:
    """引号自修受理编排的解析入参注入面（返载荷｜**拒因正文**）——零 schema 重判。

    受理编排件（`parsing.parse_with_quote_repair`）以「返 `str` ＝不合格」为约定；理解面不合格形的
    诊断正文取同一出口 `understanding_schema_feedback`（本块零第二份判定——禁用手写替代）。
    """
    parsed = parse_understanding(content)
    return parsed if parsed is not None else understanding_schema_feedback(content)


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

    **2026-10-17 V2-82a**：额外落 `state.subjects`／`state.terms`（题面主体/术语的结构化槽
    ——原样照抄模型给出，不归一、不清空）；模型给出的主体与**程序预识别候选集合**不一致时，
    过程档案追加一条**有界一句**「主体识别分歧」（`_note_subject_divergence`——只留痕、不改写
    模型判断：与数据区推荐行同一条「以你的判断为准」口径）。
    """
    offenders = [
        name for name in understanding.metric_candidates if name not in metric_roster(state)
    ]
    state.understanding = understanding.text
    state.metric_candidates = list(understanding.metric_candidates)
    state.subjects = tuple(understanding.subjects)
    state.terms = tuple(understanding.terms)
    _note_subject_divergence(state, understanding)
    bus.emit(TEXT_EVENT, {"content": understanding.text, "kind": TEXT_EVENT_KIND})
    if offenders:
        report_candidate_violation(state, offenders, understanding.metric_candidates)
    return understanding


def _divergence_listing(names: Sequence[str]) -> str:
    """分歧留痕的候选展示形（顿号串；空＝「无」——与数据区推荐行同一展示体例）。"""
    return PROGRAM_CANDIDATE_SEP.join(names) or PROGRAM_CANDIDATE_EMPTY


def _note_subject_divergence(state: RunState, understanding: Understanding) -> None:
    """主体识别分歧留痕（V2-82a）：程序候选集合 ≠ 模型给出集合 → 过程档案有界一句。

    集合判（不看序——同一组主体换序不算分歧）；相等＝零留痕（**no-divergence run 的
    `process_notes` 逐字不变**）。digest 预截 `SUBJECT_DIVERGENCE_LIMIT` 字并留可见标记
    （`bookkeeping.note` 写入点另有 200 字上限，本截更严——票面「截断 ≤100 字」）；
    只经唯一写口 `bookkeeping.note`（相位零直写），`dialogue` 零写入。
    """
    program_subjects, _program_terms = program_candidates(state)
    if set(program_subjects) == set(understanding.subjects):
        return
    digest = SUBJECT_DIVERGENCE_DIGEST.format(
        program=_divergence_listing(program_subjects),
        model=_divergence_listing(understanding.subjects),
    )
    if len(digest) > SUBJECT_DIVERGENCE_LIMIT:
        digest = digest[: SUBJECT_DIVERGENCE_LIMIT - len(TRUNCATION_MARK)] + TRUNCATION_MARK
    note(state, phase=PHASE, title=SUBJECT_DIVERGENCE_NOTE_TITLE, digest=digest)
