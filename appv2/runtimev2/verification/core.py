"""核验相位本体（`verify`）：剥结构性残留 → 逐行断言级核验 → 改写／分列／归属审 → 判定卡＋机读信号。

真源＝`specs/verification.md`（已定稿）＋卡 `specs/modules.md` `## verification`（签名以卡为准：
`verify(state) -> Verdict`）。一句话：答案交付前**逐句核对有没有材料撑着**——**纯程序、零模型**
（防编造的机器底线）；没支撑的话**改写掉**，两来源对不上就**分开列**。

一次调用的固定序（行为 1–11；语义真源＝`recon/A2` R-A2-16…R-A2-28，承载位在 V2）：

1. **剥结构性残留**（行为 1）：整行即 JSON 对象／数组＝结构性残片，剥除且**不计改写**（发射围栏／
   裸发射令牌的剥离单点归 `answering`——答案面归属，进核验的草稿已过那道剥离）；
2. **逐行断言级核验**（行为 1／2／7／8）：逐行判定（**不是整段判**）；判定面文本先过全角归一
   （行为 7），引标切辖域、数值取**边界记号**比对；被引观察的数值须在断言文本里复述，承载形式
   （`agg_row`／`lineage`／`fragment`）豁免「全数值复述」（任一数值重叠即支撑、零重叠照改）；
   空壳辖域整行重判（修一）；整行重判仍不过时**窗内对齐放行**（行为 8：零数值断言不放行——仍须
   有可解析引标支撑）；
3. **无据 → 改写**（行为 3）：没支撑的句子改写成「未找到（材料未披露）」＋ `RewriteRecord`
   （`reason="no_material"`）＋发 `notice`；**无引标但有数值**的行＝无据断言，照改（V2：关闭现状
   「无引标数字行经窗内放行」形——钉 `pin-10`「不得 `cited=[]` 且数字在场」）；无引标且无数值的行
   ＝结构承载，原样保留且**不计有支撑数**（行为 8「不得自动判过」）；
4. **矛盾 → 分列**（行为 4）：被引观察同 subject（全角「：」前名）≥2 支且值不同 → 分开列明、各带
   出处、**不强调和**（`RewriteRecord.reason="conflict"`）＋发 `notice`；`Verdict.split`＝**组数**；
5. **归属审**（行为 5）：题眼锚＝问句实体词（`appv2.tools.anchors` 的闭世界解析单点，
   确定性零模型）；
   被引**检索片段**（`fragment`／`graph`）的出处名与内容均不含任何题眼锚＝跨源引用 →
   `attribution=False` ＋缺口留痕＋答案面分源列明块；无锚＝审静默（不误伤）；
6. **判定卡＋机读信号**（行为 6／10／11；「不降级与静默禁令」节）：`Verdict` 九键齐备（缺键＝判
   失败）＋ step payload 六计数键与行集对账两字段 ＋ `verdict`／`notice` 帧（**批次落定归
   `orchestration` 协调**，本块只保证自产部分就位）；行集对账差额>0 且答案面无行集声明 → 补如实
   注记（**不改写数值断言、不重试、不拦截**）。

**写面纪律**：共享写面（步／通知／路由意图）一律经 `bookkeeping` 唯一写口（相位禁直写）；本块自有
字段（`state.draft`＝核验后答案面、`state.verdict`＝判定卡投影）直接落地——`answering` 收口以
`state.draft`／`state.verdict` 为消费面（真源 `specs/answering.md` 行为 7）。

**接缝**：`bus`（per-run 总线，编排块持有、注入各相位）为**必给**注入面——未注入＝调用方断线，
入口即 fail-closed 抛错（同 `answering.answer`／`understanding.interpret` 先例）。

**合法降级路径＝无**：闭世界越界一律 fail-closed 抛错；核验器自身抛错**不判 `ok=True`**——
转 `Verdict.ok=False` ＋缺口（由 `orchestration` 承接），绝不静默放行。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from appv2.runtimev2.bookkeeping import notice, record_step, set_intent
from appv2.runtimev2.state import INTENT_ANSWER, STEP_VERIFY, RunState
from appv2.runtimev2.transport import EventBus
from appv2.runtimev2.verification.constants import (
    EVENT_NOTICE,
    EVENT_VERDICT,
    GAP_ATTRIBUTION_REASON,
    GAP_FAIL_CLOSED_REASON,
    GAP_REWRITE_REASON,
    NOTICE_ATTRIBUTION_CONTENT,
    NOTICE_ATTRIBUTION_SPLIT,
    NOTICE_CONTRADICTION_CONTENT,
    NOTICE_CONTRADICTION_SPLIT,
    NOTICE_UNSUPPORTED_CLAIM,
    NOTICE_UNSUPPORTED_CONTENT,
    PAYLOAD_ATTRIBUTION_KEY,
    PAYLOAD_CITED_KEY,
    PAYLOAD_DELIVERED_ROWS_KEY,
    PAYLOAD_GAP_KIND_KEY,
    PAYLOAD_GAP_REASON_KEY,
    PAYLOAD_GAP_SUBTASK_KEY,
    PAYLOAD_GAPS_KEY,
    PAYLOAD_OBS_ROWS_KEY,
    PAYLOAD_OK_KEY,
    PAYLOAD_PHASE_KEY,
    PAYLOAD_REWRITE_LINE_KEY,
    PAYLOAD_REWRITE_REASON_KEY,
    PAYLOAD_REWRITES_KEY,
    PAYLOAD_REWRITTEN_KEY,
    PAYLOAD_ROW_NOTE_KEY,
    PAYLOAD_SPLIT_KEY,
    PAYLOAD_SUPPORTED_KEY,
    PHASE,
    REWRITE_CONFLICT,
    REWRITE_NO_MATERIAL,
    REWRITE_PREFIX,
    ROW_NOTE_TEMPLATE,
    ROWSET_OBSERVATION_KINDS,
    SPLIT_NO,
    SPLIT_YES,
    STEP_TITLE_TEMPLATE,
)
from appv2.runtimev2.verification.models import GAP_UNVERIFIED, Gap, RewriteRecord, Verdict
from appv2.runtimev2.verification.rules import (
    aligned_indices,
    attribution_block,
    attribution_split,
    citation_chunks,
    contradiction_groups,
    line_numbers_are_asserted,
    locator_kind,
    normalize_for_match,
    number_tokens,
    observation_supported,
    question_anchors,
    resolvable,
    scope_usable,
    split_block,
    structural_line,
    uncited_aligned,
    without_markers,
)

_BUS_MISSING = (
    "核验相位总线未注入（per-run 总线由编排块持有并注入）——裁决／通知事件无出口，"
    "fail-closed：不静默丢弃（行为 6／10）"
)
_INDEX_SEPARATOR = "、"


def verify(state: RunState, *, bus: EventBus | None = None) -> Verdict:
    """核验入口（卡面签名 `verify(state) -> Verdict`；`bus` 为编排块注入的帧出口）。

    返回判定卡 `Verdict`（对外判定，**不是 answer 侧文本**）；同时把核验后的答案面落回
    `state.draft`、判定卡投影落 `state.verdict`、步／通知／意图经 `bookkeeping` 唯一写口落账。
    **核验器自身抛错 → 不判 `ok=True`**（fail-closed：`ok=False` ＋缺口，不静默放行）。
    """
    channel = _require_bus(bus)
    try:
        return _verify(state, channel)
    except Exception as exc:  # 错误契约：核验器自身抛错＝fail-closed 取 ok=False
        return _fail_closed(state, exc)


def _require_bus(bus: EventBus | None) -> EventBus:
    """总线把守（fail-closed）：未注入即抛错——不做「无出口静默跳过」的降级。"""
    if bus is None:
        raise RuntimeError(_BUS_MISSING)
    return bus


def _draft_lines(draft: str) -> list[str]:
    """答案面逐行（**逐行判定**的切分面——行为 1：不是整段判）。"""
    return str(draft or "").splitlines()


def _fail_closed(state: RunState, exc: BaseException) -> Verdict:
    """fail-closed 判定卡：`ok=False` ＋缺口（行为 9／错误契约）——不静默放行、不返回哨兵。"""
    reason = GAP_FAIL_CLOSED_REASON.format(error=f"{type(exc).__name__}: {exc}")
    verdict = Verdict(
        supported=0,
        rewritten=0,
        split=0,
        cited=[],
        delivered_rows=0,
        obs_rows=0,
        attribution=False,
        ok=False,
        gaps=[Gap(kind=GAP_UNVERIFIED, subtask_id=None, reason=reason)],
    )
    state.verdict = verdict.as_dict()
    return verdict


def _verify(state: RunState, bus: EventBus) -> Verdict:
    anchors = question_anchors(state.question)
    observations = list(state.observations)
    by_index = {int(obs["index"]): obs for obs in observations}

    out_lines: list[str] = []
    rewrites: list[RewriteRecord] = []
    cited: set[int] = set()
    cited_lines: list[tuple[str, tuple[int, ...]]] = []
    supported = 0
    for line in _draft_lines(state.draft):
        stripped = line.strip()
        if not stripped:
            out_lines.append(line)
            continue
        if structural_line(stripped):
            continue  # 结构性残片：剥除不计改写（行为 1）
        normalized = normalize_for_match(line)
        chunks = citation_chunks(normalized)
        if chunks and _chunks_supported(chunks, by_index):
            cited.update(seq for seq, _ in chunks)
            cited_lines.append((line, tuple(seq for seq, _ in chunks)))
            supported += 1
            out_lines.append(line)
            continue
        if chunks:
            bare = without_markers(normalized)
            if any(not scope_usable(chunk) for _, chunk in chunks) and _whole_supported(
                chunks, bare, by_index
            ):
                cited.update(seq for seq, _ in chunks)
                cited_lines.append((line, tuple(seq for seq, _ in chunks)))
                supported += 1
                out_lines.append(line)
                continue
            matched = aligned_indices(number_tokens(bare), observations)
            if matched:
                cited.update(matched)
                supported += 1
                out_lines.append(line)
                continue
            out_lines.append(REWRITE_PREFIX + stripped)
            rewrites.append(RewriteRecord(line=line, reason=REWRITE_NO_MATERIAL))
            continue
        if line_numbers_are_asserted(normalized):
            # 无引标但有数值＝无据断言（行为 8 后半；钉 pin-10：不得 cited=[] 且数字在场）
            out_lines.append(REWRITE_PREFIX + stripped)
            rewrites.append(RewriteRecord(line=line, reason=REWRITE_NO_MATERIAL))
            continue
        out_lines.append(line)  # 结构承载（标题／表头／分隔线）——不计有支撑数

    text = "\n".join(out_lines)

    ordered_cited = sorted(cited)
    groups = contradiction_groups(ordered_cited, observations)
    if groups:
        text += "\n\n" + split_block(groups)
        for group in groups:
            members = {int(obs["index"]) for obs in group}
            matched_lines = [
                source for source, seqs in cited_lines if members.intersection(seqs)
            ]
            if matched_lines:
                for source in dict.fromkeys(matched_lines):
                    rewrites.append(RewriteRecord(line=source, reason=REWRITE_CONFLICT))
            else:
                rewrites.append(
                    RewriteRecord(
                        line=str(group[0].get("content", "")), reason=REWRITE_CONFLICT
                    )
                )

    aligned, crossed = attribution_split(anchors, ordered_cited, observations)
    if crossed:
        pending = uncited_aligned(anchors, ordered_cited, observations)
        text += "\n\n" + attribution_block(anchors, aligned, pending, crossed)

    obs_rows = sum(
        1 for obs in observations if locator_kind(obs) in ROWSET_OBSERVATION_KINDS
    )
    delivered_rows = sum(
        1
        for obs in observations
        if locator_kind(obs) in ROWSET_OBSERVATION_KINDS
        and int(obs["index"]) in cited
    )
    delta = obs_rows - delivered_rows
    row_note: str | None = None
    if delta > 0 and delivered_rows == 0:
        # 行为 11：差额>0 且答案面无行集声明 → 补如实注记（不改写、不重试、不拦截）
        row_note = ROW_NOTE_TEMPLATE.format(
            obs_rows=obs_rows, delivered_rows=delivered_rows, delta=delta
        )

    # `rewritten`＝**无据**被改写的句子数（分列改写不计——`split` 另计组数；两维度不强行映射）
    rewritten = sum(1 for record in rewrites if record.reason == REWRITE_NO_MATERIAL)
    gaps: list[Gap] = []
    if rewritten:
        gaps.append(
            Gap(
                kind=GAP_UNVERIFIED,
                subtask_id=None,
                reason=GAP_REWRITE_REASON.format(rewritten=rewritten),
            )
        )
    if crossed:
        gaps.append(
            Gap(
                kind=GAP_UNVERIFIED,
                subtask_id=None,
                reason=GAP_ATTRIBUTION_REASON.format(
                    indices=_index_text([int(obs["index"]) for obs in crossed]),
                    anchors=_anchor_text(anchors),
                ),
            )
        )
    verdict = Verdict(
        supported=supported,
        rewritten=rewritten,
        split=len(groups),
        cited=ordered_cited,
        delivered_rows=delivered_rows,
        obs_rows=obs_rows,
        attribution=not crossed,
        ok=rewritten == 0,
        gaps=gaps,
    )

    _emit_signals(state, bus, verdict, rewrites, anchors, crossed, row_note)
    state.draft = text
    state.verdict = verdict.as_dict()
    set_intent(state, INTENT_ANSWER)
    return verdict


def _chunks_supported(
    chunks: Sequence[tuple[int, str]], by_index: Mapping[int, Mapping[str, Any]]
) -> bool:
    """逐引标辖域支撑判定（引标须可解析——行为 8「仍须有可解析引标支撑」）。"""
    return all(
        resolvable(seq, by_index) and observation_supported(by_index[seq], chunk)
        for seq, chunk in chunks
    )


def _whole_supported(
    chunks: Sequence[tuple[int, str]],
    bare: str,
    by_index: Mapping[int, Mapping[str, Any]],
) -> bool:
    """空壳辖域修一：剥引标后以**整行文本**对各引标逐一重判（引标序号自身不作数——防自证）。"""
    return all(
        resolvable(seq, by_index) and observation_supported(by_index[seq], bare)
        for seq, _ in chunks
    )


def _index_text(indices: Sequence[int]) -> str:
    return _INDEX_SEPARATOR.join(f"[{index}]" for index in indices)


def _anchor_text(anchors: Sequence[str]) -> str:
    return _INDEX_SEPARATOR.join(str(anchor) for anchor in anchors)


def _emit_signals(
    state: RunState,
    bus: EventBus,
    verdict: Verdict,
    rewrites: Sequence[RewriteRecord],
    anchors: Sequence[str],
    crossed: Sequence[Any],
    row_note: str | None,
) -> None:
    """机读信号（「不降级与静默禁令」节）：step payload ＋ `notice`／`verdict` 帧 ＋ 通知落账。

    三类事件的帧面与状态落账同批：改写／分列／归属失败**都必产信号**（不许静默），step payload
    携六计数键与行集对账两字段（行为 6／11）；`verdict` 帧的**批次落定**由 `orchestration` 协调，
    本块只保证自产部分就位（行为 10）。
    """
    title = STEP_TITLE_TEMPLATE.format(
        supported=verdict.supported,
        rewritten=verdict.rewritten,
        split=SPLIT_YES if verdict.split else SPLIT_NO,
    )
    record_step(
        state,
        kind=STEP_VERIFY,
        title=title,
        payload=_step_payload(verdict, rewrites, row_note),
    )
    if verdict.rewritten:
        _notify(
            state,
            bus,
            NOTICE_UNSUPPORTED_CLAIM,
            NOTICE_UNSUPPORTED_CONTENT.format(rewritten=verdict.rewritten),
        )
    if verdict.split:
        _notify(state, bus, NOTICE_CONTRADICTION_SPLIT, NOTICE_CONTRADICTION_CONTENT)
    if not verdict.attribution:
        _notify(
            state,
            bus,
            NOTICE_ATTRIBUTION_SPLIT,
            NOTICE_ATTRIBUTION_CONTENT.format(
                indices=_index_text([int(obs["index"]) for obs in crossed]),
                anchors=_anchor_text(anchors),
            ),
        )
    # `verdict` 帧载荷键集＝`synth/S6-事件与帧目录.md` §一 verdict 行的 `verify` 形
    # （`subtype` 由 `transport` 注入，本模块不写）；行集对账两字段**不入帧**——其落点＝
    # `Verdict` 两字段 ＋ step payload（行为 11／钉 pin-12）。
    bus.emit(
        EVENT_VERDICT,
        {
            PAYLOAD_SUPPORTED_KEY: verdict.supported,
            PAYLOAD_REWRITTEN_KEY: verdict.rewritten,
            PAYLOAD_SPLIT_KEY: verdict.split,
            PAYLOAD_CITED_KEY: list(verdict.cited),
            PAYLOAD_ATTRIBUTION_KEY: verdict.attribution,
        },
    )


def _notify(state: RunState, bus: EventBus, notice_type: str, content: str) -> None:
    """通知双落（状态写口 ＋ `notice` 帧——恰三键 `{type, gates, content}`）。"""
    notice(state, type=notice_type, content=content)
    bus.emit(EVENT_NOTICE, {"type": notice_type, "gates": [], "content": content})


def _step_payload(
    verdict: Verdict, rewrites: Sequence[RewriteRecord], row_note: str | None
) -> dict[str, Any]:
    """步 payload（六计数键 ＋ 行集对账两字段 ＋ 改写／缺口留痕 ＋ 行集注记）。"""
    return {
        PAYLOAD_PHASE_KEY: PHASE,
        PAYLOAD_SUPPORTED_KEY: verdict.supported,
        PAYLOAD_REWRITTEN_KEY: verdict.rewritten,
        PAYLOAD_SPLIT_KEY: verdict.split,
        PAYLOAD_CITED_KEY: list(verdict.cited),
        PAYLOAD_DELIVERED_ROWS_KEY: verdict.delivered_rows,
        PAYLOAD_OBS_ROWS_KEY: verdict.obs_rows,
        PAYLOAD_ATTRIBUTION_KEY: verdict.attribution,
        PAYLOAD_OK_KEY: verdict.ok,
        PAYLOAD_REWRITES_KEY: [
            {
                PAYLOAD_REWRITE_LINE_KEY: record.line,
                PAYLOAD_REWRITE_REASON_KEY: record.reason,
            }
            for record in rewrites
        ],
        PAYLOAD_GAPS_KEY: [
            {
                PAYLOAD_GAP_KIND_KEY: gap.kind,
                PAYLOAD_GAP_SUBTASK_KEY: gap.subtask_id,
                PAYLOAD_GAP_REASON_KEY: gap.reason,
            }
            for gap in verdict.gaps
        ],
        PAYLOAD_ROW_NOTE_KEY: row_note,
    }
