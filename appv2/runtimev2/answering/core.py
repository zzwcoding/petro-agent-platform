"""作答相位本体（`answer`）：材料面显式 → 起草（真流式逐段推）→ 收口（引用块＋citation 帧＋链尾）。

真源＝`specs/answering.md`（已定稿）＋卡 `specs/modules.md` `## answering`（签名以卡为准：
`answer(state) -> AnswerDraft`）。一句话：把前面查到的**全部子问题结果**整理成**一份答案**
——**一段段推给页面（真流式）**、**每句带出处**、**缺口如实交代**。

一次调用的固定序（行为 1–11；语义不变、承载位在 V2）：

1. **材料面显式**（行为 4）：材料面 Manifest 经 `context.compile_manifest` 编译（**本块只消费、
   零自取**；作答轮零常驻来源行）；材料段经 `context.render_materials` 渲染（帽为注入参数、
   数值单点仍在 `context`）；指令文本经 `prompts.assemble_answer_prompt` 装配（材料段不在装配
   输出内——调用方追加于尾）。截断态**必披露**：`material_truncated` notice 在场（未截断零通知）；
2. **起草**：作答指令＋材料段一条 user 消息追加链尾（`bookkeeping.append_message`）→ 经
   `bookkeeping.call_model` **单点发起**模型调用（本块不直引 `gateway_adapter`、不直引
   `appv2.infra.llm_client`、不自建模型客户端——R7 ＋「无旁路」行为断言）；
3. **发射剥离**（行为 11，钉 `pin-04`）：应答先过 `strip_emission_fences`（`emission` 单点），
   发射 JSON 不进答案面（泄漏=0）；检出即发 `emission_strip` notice（机读面）；
4. **分段与引标**（行为 1／2／3）：草稿按空行分**段**，逐段取本段 `citation_seqs`（`[n]` 序）；
   **引标必须真实存在于观察序列**——出现不存在的引标号即抛 `DanglingCitationError`（判失败，
   fail-closed），**且校验先于发帧**（坏引标不得上帧面）；
5. **真流式推出**（行为 1）：逐段发 `text` 帧（一段一帧）——**不是收口时一次性推全量**；模型原话
   **只进过程档案**（`bookkeeping.note` 留痕——行为 8：模型原话不进对话层），草稿另落
   `state.draft` 供核验消费；答案面步落 `payload` 的 `citations`／`gaps` 机读字段（「不降级与
   静默禁令」节）＋**材料面 Manifest**（见下「步面接缝」）；
6. **结构化缺口**（行为 5）：被拒子问题→`Gap(kind="refused")`、其余失败／缺料→
   `Gap(kind="missing")`、零实质材料（无非 notice 观察）→`Gap(kind="unverified")`——三档齐由
   同一确定性分派产生，**不静默截断**；空稿（剥离后）→ **不推空答案**（零 text 帧、`state.draft`
   保持空），按缺口如实收口（行为 9）；
7. **收口**（行为 7，核验后重入面）：`verdict` 在场／直答态／已有起草标记＝**收口段**——引用块
   生成、`citation` 帧逐支发射、终稿一条 assistant 消息追加链尾，**同批落定**。`verdict` 帧本体
   是**消费方信号**（批次落定归 `orchestration`，行为 7 明写），本块不产。

**步面接缝（登记呈主窗）**：模型调用步由 `bookkeeping.call_model` **单点记账**（用量与归因面＋
`token_count`），本块**不为同一调用再记模型调用步**；本块的答案面步（`起草答案`／`答案收口`）
承载**材料面 Manifest**（`context.compile_manifest` 产物）与 `citations`／`gaps` 机读字段——
`call_model` 的签名（`call_model(state, caller, messages)`）无 manifest 注入面，故材料面 Manifest
只能落本块步面；该接缝为**登记项**（跨块对账面＝`specs/agent-loop.md` 行 18「每个模型调用 step
落 Manifest」）。

**接缝纪律**：`bus`（per-run 总线，编排块持有、注入各相位）为**必给**注入面——未注入＝调用方断线，
入口即 fail-closed 抛错（同 `understanding.interpret` 先例）；`max_observations`（材料帽）为注入
参数（缺省引 `context.DEFAULT_MAX_OBSERVATIONS` 单点、无裸字面）。

**合法降级路径＝无**：闭世界越界即抛错；起草原话不完整时走结构化缺口，**不改写事实**。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from appv2.runtimev2.answering.constants import (
    CITATION_BLOCK_HEAD,
    CITATION_EVENT,
    CITATION_PAYLOAD_INDEX,
    CITATION_PAYLOAD_SOURCE,
    CITATION_PAYLOAD_SOURCE_ID,
    CITATION_PAYLOAD_TRUST,
    DRAFT_KIND_DIRECT,
    DRAFT_NOTE_TITLE,
    DRAFT_STEP_KIND,
    DRAFT_STEP_TITLE,
    EMISSION_STRIP_CONTENT,
    EMPTY_DRAFT_REASON,
    FINALIZE_STEP_KIND,
    FINALIZE_STEP_TITLE,
    MATERIAL_TRUNCATED_CONTENT,
    MODEL_CALLER,
    NOTICE_EMISSION_STRIP,
    NOTICE_MATERIAL_TRUNCATED,
    PAYLOAD_CITATIONS_KEY,
    PAYLOAD_GAP_KIND_KEY,
    PAYLOAD_GAP_REASON_KEY,
    PAYLOAD_GAP_SUBTASK_KEY,
    PAYLOAD_GAPS_KEY,
    PAYLOAD_PHASE_DRAFT,
    PAYLOAD_PHASE_FINALIZE,
    PAYLOAD_PHASE_KEY,
    PHASE,
    ROLE_ASSISTANT,
    ROLE_USER,
    SUBTASK_MISSING_REASON,
    SUBTASK_STATUS_OK,
    SUBTASK_STATUS_REFUSED,
    TEXT_EVENT,
    TEXT_PAYLOAD_CONTENT,
    ZERO_MATERIAL_REASON,
)
from appv2.runtimev2.answering.emission import strip_emission_fences
from appv2.runtimev2.answering.models import (
    GAP_MISSING,
    GAP_REFUSED,
    GAP_UNVERIFIED,
    AnswerDraft,
    AnswerSegment,
    Citation,
    Gap,
)
from appv2.runtimev2.bookkeeping import (
    append_message,
    call_model,
    note,
    notice,
    record_step,
    set_intent,
)
from appv2.runtimev2.context import (
    DEFAULT_MAX_OBSERVATIONS,
    compile_manifest,
    render_materials,
    trust_of,
)
from appv2.runtimev2.persistence import STEP_STATUS_FAILED, STEP_STATUS_OK
from appv2.runtimev2.prompts import assemble_answer_prompt
from appv2.runtimev2.state import INTENT_END, INTENT_VERIFY, Manifest, RunState
from appv2.runtimev2.transport import EventBus

_BUS_MISSING = (
    "作答相位总线未注入（per-run 总线由编排块持有并注入）——增量文本事件无出口，"
    "fail-closed：不静默丢弃（行为 1／2）"
)
_CITATION_BLOCK_LINE = "[{seq}] {source} · {source_id}（{trust}）"
_ASCII_DIGITS = "0123456789"


class DanglingCitationError(ValueError):
    """坏引标（引标号不存在于观察序列）——接口定义节「引标必须真实存在」＋验收行 3 的判失败出口。

    引标与增量必须同步（行为 2）：悬空引标＝答案面指向不存在的观察，**不猜、不补、不静默丢弃**；
    抛出即「不返回半成品」（规格「接口定义」错误契约），由 `orchestration` 承接收口。
    """

    def __init__(self, dangling: tuple[int, ...]) -> None:
        self.dangling = dangling
        names = "、".join(str(seq) for seq in dangling)
        super().__init__(
            f"坏引标：引标号 {names} 不存在于观察序列（引标编号＝观察序号，行为 2／验收行 3）"
            "——判失败，不返回半成品"
        )


def answer(
    state: RunState,
    *,
    bus: EventBus | None = None,
    max_observations: int = DEFAULT_MAX_OBSERVATIONS,
) -> AnswerDraft:
    """作答一步：起草（真流式逐段推）或收口（引用块＋citation 帧＋链尾同批）。

    两段式入口（同 V1 answer 节点的两拍）：**未起草** → 起草段（模型调用、剥离、分段引标、
    逐段发 `text` 帧、落 `state.draft`，意图转 `verify` 交核验）；**已起草**（`verdict` 在场／
    直答态／起草标记在场）→ 收口段（引用块＋`citation` 帧＋终稿链尾，意图收 `end`）。
    灌进模型的是整条对话链（`state.messages` 只追加——钉 `pin-22`）；过程态一律经 `bookkeeping`
    唯一写口落（步／链／过程档案／通知／意图），本块零直写共享写面字段。
    """
    channel = _require_bus(bus)
    if _drafted(state):
        return _finalize(state, channel)
    return _draft(state, channel, max_observations=max_observations)


def _require_bus(bus: EventBus | None) -> EventBus:
    """总线把守（fail-closed）：未注入即抛错——不做「无出口静默跳过」的降级。"""
    if bus is None:
        raise RuntimeError(_BUS_MISSING)
    return bus


def _drafted(state: RunState) -> bool:
    """起草是否已发生（本块自立的机读判据）：直答态／`verdict` 在场／过程档案起草标记在场。

    起草标记＝过程档案里的一条标题条目（先例＝`understanding.assembly` 的「任务书已装配」标记
    ——任务书与草稿都是不能再算的活体文本，故不以文本相等为判据）。
    """
    if state.draft_kind == DRAFT_KIND_DIRECT or state.verdict is not None:
        return True
    return any(
        isinstance(entry, Mapping) and entry.get("title") == DRAFT_NOTE_TITLE
        for entry in state.process_notes
    )


# ── 起草段（行为 1／2／3／4／5／8／9／11）─────────────────────────────────────


def _draft(state: RunState, bus: EventBus, *, max_observations: int) -> AnswerDraft:
    """起草段：材料面显式 → 单点发起模型调用 → 剥离 → 分段引标 → 逐段推帧。"""
    manifest = compile_manifest(
        state.observations, step=PHASE, max_observations=max_observations
    )
    materials_text, meta = render_materials(
        state.observations, max_observations=max_observations
    )
    if meta[MATERIAL_TRUNCATED_KEY]:
        notice(
            state,
            type=NOTICE_MATERIAL_TRUNCATED,
            content=MATERIAL_TRUNCATED_CONTENT.format(
                rendered=meta[MATERIAL_RENDERED_KEY], total=meta[MATERIAL_TOTAL_KEY]
            ),
        )
    append_message(
        state,
        role=ROLE_USER,
        content=assemble_answer_prompt(state) + materials_text,
    )
    raw = call_model(state, MODEL_CALLER, list(state.messages))
    draft_text, leaked = strip_emission_fences(raw)
    if leaked:
        notice(state, type=NOTICE_EMISSION_STRIP, content=EMISSION_STRIP_CONTENT)
    # 模型原话只进过程档案与留痕（行为 8；对话层零写入）——本条同时是「已起草」机读标记。
    note(state, phase=PHASE, title=DRAFT_NOTE_TITLE, digest=raw)
    by_index = _observation_index(state)
    segments = _draft_segments(draft_text, by_index)
    gaps = _draft_gaps(state, manifest=manifest, draft_text=draft_text)
    record_step(
        state,
        kind=DRAFT_STEP_KIND,
        title=DRAFT_STEP_TITLE,
        status=STEP_STATUS_OK if draft_text.strip() else STEP_STATUS_FAILED,
        payload=_citations_gaps_payload(PAYLOAD_PHASE_DRAFT, segments, gaps),
        manifest=manifest,
    )
    if not draft_text.strip():
        # 空稿不推（行为 9）：零 text 帧、`state.draft` 保持空——按结构化缺口如实收口。
        set_intent(state, INTENT_END)
        return AnswerDraft(segments=[], citations=[], gaps=gaps)
    state.draft = draft_text
    set_intent(state, INTENT_VERIFY)
    for segment in segments:
        bus.emit(TEXT_EVENT, {TEXT_PAYLOAD_CONTENT: segment.text})  # 一段一帧（真流式）
    return AnswerDraft(
        segments=segments, citations=_citations_of(segments, by_index), gaps=gaps
    )


# ── 收口段（行为 7）─────────────────────────────────────────────────────────


def _finalize(state: RunState, bus: EventBus) -> AnswerDraft:
    """收口段：引用块＋`citation` 帧＋终稿链尾**同批落定**（`verdict` 帧归编排协调，本块不产）。

    终稿文本＝核验后的草稿（`state.draft`）或直答/收敛正文（`state.answer`）；引用块与 `citation`
    帧取**同一序集**（答案面实际携带的合法引标 ∪ 核验支撑集）——两处同源不脱节（行为 2／7）。
    无稿可收口（空稿路径重入／直答空文本）→ **不推空答案**，按结构化缺口如实收口（行为 9）。
    """
    by_index = _observation_index(state)
    text = state.draft or state.answer
    if not text.strip():
        gaps = [Gap(GAP_MISSING, None, EMPTY_DRAFT_REASON)]
        record_step(
            state,
            kind=FINALIZE_STEP_KIND,
            title=FINALIZE_STEP_TITLE,
            status=STEP_STATUS_FAILED,
            payload=_citations_gaps_payload(PAYLOAD_PHASE_FINALIZE, [], gaps),
        )
        set_intent(state, INTENT_END)
        return AnswerDraft(segments=[], citations=[], gaps=gaps)
    segments = _final_segments(text, by_index)
    cited = _cited_seqs(state, text, by_index)
    citations = [Citation(seq=seq, locator=_locator_of(by_index[seq])) for seq in cited]
    final_text = text + _citation_block(cited, by_index)
    for seq in cited:
        bus.emit(CITATION_EVENT, _citation_payload(seq, by_index[seq]))
    append_message(state, role=ROLE_ASSISTANT, content=final_text)  # 链尾（同批）
    state.answer = final_text
    record_step(
        state,
        kind=FINALIZE_STEP_KIND,
        title=FINALIZE_STEP_TITLE,
        payload=_citations_gaps_payload(PAYLOAD_PHASE_FINALIZE, segments, []),
    )
    set_intent(state, INTENT_END)
    return AnswerDraft(segments=segments, citations=citations, gaps=[])


# ── 分段与引标（行为 1／2／3）────────────────────────────────────────────────


def _split_segments(text: str) -> list[str]:
    """草稿分段（空行分段、逐段 `strip`、空段跳过）——一段一帧的呈现单元。"""
    return [part.strip() for part in text.split("\n\n") if part.strip()]


def _citation_seqs(text: str) -> list[int]:
    """文本内的引标序号列（`[n]`，ASCII 数字形；出现序、含重复）——**形态扫描，零语义**。"""
    seqs: list[int] = []
    cursor = 0
    while True:
        start = text.find("[", cursor)
        if start < 0:
            return seqs
        end = text.find("]", start + 1)
        if end < 0:
            return seqs
        token = text[start + 1 : end]
        if token and all(char in _ASCII_DIGITS for char in token):
            seqs.append(int(token))
        cursor = end + 1


def _draft_segments(text: str, by_index: Mapping[int, Mapping[str, Any]]) -> list[AnswerSegment]:
    """起草段分段：逐段取 `citation_seqs` 并**校验引标可解析**（悬空即抛错——判失败）。"""
    segments: list[AnswerSegment] = []
    for part in _split_segments(text):
        seqs = _citation_seqs(part)
        dangling = tuple(seq for seq in dict.fromkeys(seqs) if seq not in by_index)
        if dangling:
            raise DanglingCitationError(dangling)
        segments.append(AnswerSegment(text=part, citation_seqs=seqs))
    return segments


def _final_segments(text: str, by_index: Mapping[int, Mapping[str, Any]]) -> list[AnswerSegment]:
    """收口段分段：域内引标逐段保留（核验后的终稿——越界引标由核验面收口，此处零判定）。"""
    segments: list[AnswerSegment] = []
    for part in _split_segments(text):
        seqs = [seq for seq in _citation_seqs(part) if seq in by_index]
        segments.append(AnswerSegment(text=part, citation_seqs=seqs))
    return segments


def _citations_of(
    segments: list[AnswerSegment], by_index: Mapping[int, Mapping[str, Any]]
) -> list[Citation]:
    """引用块条目（起草面）：全段引标去重升序 → `Citation(seq, locator)`。"""
    seqs = sorted({seq for segment in segments for seq in segment.citation_seqs})
    return [Citation(seq=seq, locator=_locator_of(by_index[seq])) for seq in seqs]


def _cited_seqs(
    state: RunState, text: str, by_index: Mapping[int, Mapping[str, Any]]
) -> list[int]:
    """收口序集＝终稿文本携带的合法引标 ∪ 核验支撑集（`verdict.cited`；两处同源在界者）。"""
    seqs = {seq for seq in _citation_seqs(text) if seq in by_index}
    for seq in _verdict_cited(state.verdict):
        if seq in by_index:
            seqs.add(seq)
    return sorted(seqs)


def _verdict_cited(verdict: dict[str, Any] | None) -> tuple[int, ...]:
    """核验支撑集（`Verdict.cited`）的读取面：只认整数形成员（形态判定，非语义）。"""
    if not isinstance(verdict, Mapping):
        return ()
    cited = verdict.get("cited")
    if not isinstance(cited, (list, tuple)):
        return ()
    values: list[int] = []
    for item in cited:
        try:
            values.append(int(item))
        except (TypeError, ValueError):
            continue
    return tuple(values)


def _observation_index(state: RunState) -> dict[int, Mapping[str, Any]]:
    """观察序列索引（`index` → 观察行）——引标解析与引用块的查表面。"""
    index: dict[int, Mapping[str, Any]] = {}
    for observation in state.observations:
        if not isinstance(observation, Mapping):
            continue
        try:
            seq = int(observation["index"])
        except (KeyError, TypeError, ValueError):
            continue
        index[seq] = observation
    return index


# ── 缺口（行为 5）───────────────────────────────────────────────────────────


def _draft_gaps(
    state: RunState, *, manifest: Manifest, draft_text: str
) -> list[Gap]:
    """结构化缺口三档齐的确定性分派（行为 5：被拒／缺失／未及核验——不静默截断）。

    - 子问题结果态 `refused`（前置闸拒／闸拒终局）→ `refused`（拒因原文）；
    - 其余非 `ok` 态（失败／重试耗尽／修参）→ `missing`（缺料，拒因原文）；
    - 零实质材料（材料面 Manifest 的 `material_total`＝0，notice 不计）→ `unverified`；
    - 空稿（剥离后）→ `missing`（起草未产出——「不推空答案，按缺口如实收口」）。
    """
    gaps: list[Gap] = []
    for result in state.subtask_results:
        if not isinstance(result, Mapping):
            continue
        status = str(result.get("status", ""))
        if status in ("", SUBTASK_STATUS_OK):
            continue
        subtask_id = str(result.get("id", "")) or None
        reason = str(result.get("reason") or "") or SUBTASK_MISSING_REASON
        kind = GAP_REFUSED if status == SUBTASK_STATUS_REFUSED else GAP_MISSING
        gaps.append(Gap(kind=kind, subtask_id=subtask_id, reason=reason))
    if manifest.material_total == 0:
        gaps.append(Gap(kind=GAP_UNVERIFIED, subtask_id=None, reason=ZERO_MATERIAL_REASON))
    if not draft_text.strip():
        gaps.append(Gap(kind=GAP_MISSING, subtask_id=None, reason=EMPTY_DRAFT_REASON))
    return gaps


# ── 引用块与帧载荷（行为 2／7；帧载荷键真源 `synth/S6` §一）────────────────────────


def _locator_of(observation: Mapping[str, Any]) -> str:
    """可机读出处（台账行／片段→报告→库／表名）：观察自带 `locator` 的键值形，回退 `source`。"""
    locator = observation.get("locator")
    if isinstance(locator, Mapping):
        parts = [
            f"{key}={locator[key]}"
            for key in sorted(locator, key=str)
            if _scalar(locator[key])
        ]
        if parts:
            return "；".join(parts)
    source = observation.get("source")
    return source.strip() if isinstance(source, str) else ""


def _scalar(value: Any) -> bool:
    """JSON 原语形且非空（引用出处的逐字段可取面——集合／空值不作数）。"""
    if isinstance(value, (str, int, float, bool)):
        return str(value).strip() != ""
    return False


def _source_of(observation: Mapping[str, Any]) -> str:
    source = observation.get("source")
    return source if isinstance(source, str) else ""


def _source_id_of(observation: Mapping[str, Any]) -> str:
    source_id = observation.get("source_id")
    return source_id if isinstance(source_id, str) else ""


def _trust_of(observation: Mapping[str, Any]) -> str:
    trust = observation.get("trust")
    if isinstance(trust, str) and trust:
        return trust
    return trust_of(dict(observation))


def _citation_payload(seq: int, observation: Mapping[str, Any]) -> dict[str, Any]:
    """`citation` 帧载荷（真源 `synth/S6` §一 citation 行四键）。"""
    return {
        CITATION_PAYLOAD_INDEX: seq,
        CITATION_PAYLOAD_SOURCE: _source_of(observation),
        CITATION_PAYLOAD_SOURCE_ID: _source_id_of(observation),
        CITATION_PAYLOAD_TRUST: _trust_of(observation),
    }


def _citation_block(cited: list[int], by_index: Mapping[int, Mapping[str, Any]]) -> str:
    """引用块（迁移照抄 V1 `_finalize` 形：段头「引用：」＋逐支「[n] 出处 · id（信任）」）。"""
    if not cited:
        return ""
    lines = [
        _CITATION_BLOCK_LINE.format(
            seq=seq,
            source=_source_of(by_index[seq]),
            source_id=_source_id_of(by_index[seq]),
            trust=_trust_of(by_index[seq]),
        )
        for seq in cited
    ]
    return CITATION_BLOCK_HEAD + "\n".join(lines)


def _citations_gaps_payload(
    phase: str, segments: list[AnswerSegment], gaps: list[Gap]
) -> dict[str, Any]:
    """答案面步 payload：`phase` ＋ `citations`（去重升序）＋ `gaps`（逐条三键）机读字段。"""
    return {
        PAYLOAD_PHASE_KEY: phase,
        PAYLOAD_CITATIONS_KEY: sorted(
            {seq for segment in segments for seq in segment.citation_seqs}
        ),
        PAYLOAD_GAPS_KEY: [
            {
                PAYLOAD_GAP_KIND_KEY: gap.kind,
                PAYLOAD_GAP_SUBTASK_KEY: gap.subtask_id,
                PAYLOAD_GAP_REASON_KEY: gap.reason,
            }
            for gap in gaps
        ],
    }


# `context.render_materials` 元数据键（真源 `specs/context.md` 行为 5／6——本块只读三键指针）。
MATERIAL_TRUNCATED_KEY = "material_truncated"
MATERIAL_RENDERED_KEY = "material_rendered"
MATERIAL_TOTAL_KEY = "material_total"
