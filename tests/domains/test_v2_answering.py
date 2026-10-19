"""answering 块验收（RT-W4-06a：骨架＋接口＋交付行为簇 ｜ RT-W4-06b：降级与引用簇）。

**-A 票**（`RT-W4-06a`）票面对象＝`specs/answering.md`「验收测试」表 :100–:110 的 **10 行**
（`#` 列保留规格表行序 1–6、8–11，逐字照票面；测试标识同规格列——`test_` 前缀为本仓 pytest
收集口径，其余逐字一致）：

- 行 1 `::streaming_segments`：答案一段段推（多段 `text` 帧），非一次性推全量；
- 行 2 `::segment_citations_resolve`：每段自带 `citation_seqs`，且序号真实存在于观察序列；
- 行 3 `::dangling_citation_rejected`：出现不存在的引标号 → **剥除**该记号（坏引标——2026-10-17
  EB5b 改判：剥除族第二形，不判失败；留痕＝起草步 payload `dangling_citation_seqs`）；
- 行 4 `::manifest_and_ref_only`：每次模型调用都有 Manifest；大结果只以引用进窗口；
- 行 5 `::structured_gaps_all_kinds`：被拒／缺失／未及核验 → 产出结构化 `Gap`（三档闭世界）；
- 行 6 `::gap_kind_closed_world`：`Gap.kind` 越界取值 → 判失败；
- 行 8 `::finalize_atomic`：收口同批落定（引用块＋citation 帧＋verdict 帧＋链尾）；
- 行 9 `::empty_draft_not_pushed`：空稿／全无据 → 不推空答案，按缺口如实收口；
- 行 10 `::raw_not_in_dialogue`：模型原话不进对话层；
- 行 11 `::emission_strip_zero_leak`：发射 JSON 不进答案面（确定性剥离，泄漏=0）。

**-B 票**（`RT-W4-06b`）票面对象＝同表 **12 行**（第 7、12–22 行，`#` 列同一行序不重编）：

- 行 7 `::contradiction_split_not_merged`：矛盾来源分列且标「互不一致」，不调和；
- 行 12 `::rowset_full_delivery`：明细行集题交付行数＝引擎返回行数（50 行全交付，丢行=0）；
- 行 13 `::truncation_disclosed`：材料截断必披露（`material_truncated` notice＋
  「没用上的部分不作答」声明在场——逐字＝2026-10-17 EB4b 白话化后文案；未截断零 notice）；
- 行 14 `::placeholder_marker_not_in_answer`：答案面无字面占位符 `[n]`；
- 行 15 `::echo_flag_zero`：起草回声=0（`echo_flag` 恒 0——观测字段只记不拦）；
- 行 16 `::no_hit_degraded_delivery_three_part`：台账 no_hit → 降级交付三段形且零逐井数值冒充；
- 行 17 `::ranking_answer_consumes_ranking_obs`：排名型子问题消费排名观察支（序信息一致）；
- 行 18 `::cross_oilfield_attribution_paired`：多油田题分源列明归属配对＋「某区块」含糊归属零命中；
- 行 19 `::no_lexicon_or_regex_in_answering`：程序侧无词表／正则语义判断（AST 扫描；豁免面＝
  形态处理／集合成员判定）；
- 行 20 `::answering_signal_present`：流式、缺口、截断披露的机读信号在场；
- 行 21 `::boundary_single_seg_zero_material_conflict_bad_cite`：【边界集】四形各落对应分支；
- 行 22 `::retention_plain_answer_unchanged`：【保留集】无矛盾、无缺口的普通答案行为不变。

测试网钉＝**`pin-04`**（P0「发射 JSON 不得进答案面」——对应用例＝行 11 的
`::emission_strip_zero_leak`）＋ **-B 六钉**：`pin-08`（行 12 交付侧）／`pin-09`（行 13）／
`pin-13`（行 15）／`pin-20`（行 16）／`pin-19`（行 17）／`pin-03`（行 18，P0）。

两票各自的自有面（非规格表行）：-A 的 `::card_signature_and_five_shapes`／
`::no_bypass_on_public_faces`／`::model_call_goes_through_bookkeeping_single_point`／
`::material_face_explicit_on_truncation`；-B 零自有面（12 行逐行落网——形态层两单点的直测
并入行 14／15 两例）。

**V2-82g 热修面（2026-10-17，非规格表行）**：`::extract_finalize_answer_whole_object_only`／
`::finalize_json_answer_recovered`／`::non_finalize_json_not_recovered`／
`::finalize_json_blank_answer_not_recovered`——整枚 finalize 发射 JSON 的**输入侧提取**
（真机 `run-9d1c5267` 空答案热修：剥离前取回交付字段；机读痕迹复用 `emission_strip` 通知，
闭世界零扩、合同零新增）。

接缝（`core` 模块注）：`bus`（`transport.EventBus`——本块自产 `text`／`citation` 帧的唯一出口）
与 `max_observations`（材料帽）两处关键词注入面；Seam＝起草出口（增量文本 → 事件帧），
Adapter＝剧本化 completer。对逐字稿任何一行偏离即停报 L0——本件照抄、未改一字。
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

import appv2.runtimev2.answering as answering
from appv2.runtimev2.answering import (
    CITATION_EVENT,
    CONTRADICTION_SECTION_HEAD,
    ECHO_CANDIDATE_MARK,
    ECHO_HEAD,
    EMPTY_DRAFT_REASON,
    GAP_KINDS,
    MODEL_CALLER,
    NOTICE_EMISSION_STRIP,
    PAYLOAD_CONTRADICTION_SEQS_KEY,
    PAYLOAD_DELIVERED_ROWS_KEY,
    PAYLOAD_ECHO_FLAG_KEY,
    PAYLOAD_ENGINE_NOTES_KEY,
    PAYLOAD_ENGINE_ROWS_KEY,
    PAYLOAD_RANKING_ORDER_OK_KEY,
    PAYLOAD_RANKING_SEQS_KEY,
    ROWSET_OBSERVATION_KINDS,
    SOURCE_SECTION_HEAD,
    TAIL_CLOSE_BARE_HEADING,
    TAIL_CLOSE_LEAD_IN,
    TAIL_CLOSE_TABLE_HEADER,
    AnswerDraft,
    AnswerSegment,
    Citation,
    Gap,
    answer,
    dangling_tail_closing,
    echo_flag,
    extract_finalize_answer,
    strip_emission_fences,
    strip_placeholders,
)
from appv2.runtimev2.answering import constants as answering_constants
from appv2.runtimev2.context import DEFAULT_MAX_OBSERVATIONS, render_materials
from appv2.runtimev2.gateway_adapter import ScriptedCompleter, set_completer
from appv2.runtimev2.prompts import answer_system_contract
from appv2.runtimev2.state import INTENT_END, INTENT_VERIFY, RunState
from appv2.runtimev2.transport import EventBus, SseEvent

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ANSWERING_DIR = _REPO_ROOT / "appv2" / "runtimev2" / "answering"

_QUESTION = "渤中34-8 油田 2026 年日产油量是多少？"

# 答案面步 payload 键（本块自有常量；此处只作断言字面面——真源 `answering.constants`）。
_PAYLOAD_PHASE_KEY = "phase"
_PAYLOAD_PHASE_DRAFT = "draft"
_PAYLOAD_PHASE_FINALIZE = "finalize"
_PAYLOAD_CITATIONS_KEY = "citations"
_PAYLOAD_GAPS_KEY = "gaps"
_PAYLOAD_GAP_KEYS = {"kind", "subtask_id", "reason"}
# `citation` 帧载荷键（真源 `synth/S6-事件与帧目录.md` §一 citation 行）。
_CITATION_FRAME_KEYS = {"index", "source", "source_id", "trust"}


def _obs(
    index: int,
    kind: str,
    *,
    content: str = "日产油量 10 吨",
    source: str = "台账",
    well: str = "",
    source_id: str = "",
    version: str | None = None,
    ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """观察 fixture（材料面字段形：`index`／`locator.kind`／`content`／出处／可选 `ref`）。"""
    row: dict[str, Any] = {
        "index": index,
        "locator": {"kind": kind},
        "content": content,
        "source": source,
        "well": well,
        "source_id": source_id,
        "version": version,
    }
    if ref is not None:
        row["ref"] = dict(ref)
    return row


def _state(**overrides: Any) -> RunState:
    values: dict[str, Any] = {
        "run_id": "run-ans-01",
        "question": _QUESTION,
        "actor": "laowang",
    }
    values.update(overrides)
    return RunState(**values)


@dataclass
class _Session:
    """一次相位会话（注入剧本化 completer ＋ per-run 总线；逐次 `call` 走 `answer`）。

    `supplements`＝增补面收集列表（2026-10-17 EB3 D2——收口三块不进正文，入该列由编排层发帧）。
    """

    bus: EventBus
    completer: ScriptedCompleter
    max_observations: int = DEFAULT_MAX_OBSERVATIONS
    supplements: list[dict[str, Any]] = field(default_factory=list)

    def call(self, state: RunState) -> AnswerDraft:
        return answer(
            state,
            bus=self.bus,
            max_observations=self.max_observations,
            supplements=self.supplements,
        )


@contextmanager
def _phase(*replies: str, max_observations: int = DEFAULT_MAX_OBSERVATIONS) -> Any:
    """剧本化 completer（同面替身，离线零触网）＋ per-run 总线（成对恢复注入缝）。"""
    completer = ScriptedCompleter({MODEL_CALLER: list(replies)})
    previous = set_completer(completer)
    try:
        yield _Session(bus=EventBus(), completer=completer, max_observations=max_observations)
    finally:
        set_completer(previous)


async def _frames(bus: EventBus) -> list[SseEvent]:
    """读尽一条已收束总线的帧（先 `close`——未收束会等待新帧）。"""
    bus.close()
    return [frame async for frame in bus.stream(0)]


def _of(frames: list[SseEvent], event: str) -> list[dict[str, Any]]:
    return [frame.data for frame in frames if frame.event == event]


def _payloads(state: RunState, phase: str) -> list[dict[str, Any]]:
    """答案面步 payload（按 `phase` 取值面筛——模型调用步的 payload 无该键，天然排除）。"""
    found: list[dict[str, Any]] = []
    for step in state.steps:
        payload = step.get("payload")
        if isinstance(payload, Mapping) and payload.get(_PAYLOAD_PHASE_KEY) == phase:
            found.append(dict(payload))
    return found


def _supplement_text(supplements: Sequence[Mapping[str, Any]], block: str) -> str:
    """增补面条目文本（按块型取——EB3 D2 载荷形 `{block, text}`；缺位即判失败）。"""
    texts = [
        str(entry.get("text", ""))
        for entry in supplements
        if entry.get("block") == block
    ]
    assert len(texts) == 1, f"增补面条目不唯一／缺席：block={block!r} texts={texts!r}"
    return texts[0]


def _supplement_blocks(supplements: Sequence[Mapping[str, Any]]) -> list[str]:
    """增补面条目块型序（按产出序——「按原序」判据面）。"""
    return [str(entry.get("block", "")) for entry in supplements]


def _answer_face(draft: AnswerDraft, frames: list[SseEvent]) -> str:
    """答案面文本（片段 ＋ `text` 帧增量——发射剥离的判据面须两处都清）。"""
    texts = [str(item.get("content", "")) for item in _of(frames, "text")]
    return "\n".join([segment.text for segment in draft.segments] + texts)


def _citing(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """观察序号索引（引标解析面）。"""
    return {int(row["index"]): row for row in observations}


def _unmarked(text: str) -> str:
    """剥去引标记号 `[数字]`（**测试面**形态扫描——数字来源判据用）。"""
    out: list[str] = []
    cursor = 0
    while True:
        start = text.find("[", cursor)
        if start < 0:
            out.append(text[cursor:])
            return "".join(out)
        end = text.find("]", start + 1)
        if end < 0:
            out.append(text[cursor:])
            return "".join(out)
        body = text[start + 1 : end]
        if body and body.isdigit():
            out.append(text[cursor:start])
        else:
            out.append(text[cursor : end + 1])
        cursor = end + 1


def _digits(text: str) -> list[str]:
    """文本内数字记号列（**测试面**形态扫描：连续 ASCII 数字／小数点段）——零冒充判据用。"""
    found: list[str] = []
    current = ""
    for char in text:
        if char in "0123456789.":
            current += char
        elif current:
            found.append(current)
            current = ""
    if current:
        found.append(current)
    return found


def _number_tokens(text: str) -> list[str]:
    """答案面数字记号列（先剥引标——判据面＝交付正文，记号本身不作数）。"""
    return _digits(_unmarked(text))


def _without_wells(text: str, observations: list[dict[str, Any]]) -> str:
    """剥去窗口观察自带井号（`well` 字段`——井号内含数字，属对象标识不属数值）。"""
    for row in observations:
        well = str(row.get("well") or "")
        if well:
            text = text.replace(well, "")
    return text


# ---------- 1 答案一段段推（多段 text 帧），非一次性推全量 ----------


async def test_streaming_segments() -> None:
    """行 1｜答案**一段段推**（多段 `text` 帧），非收口时一次性推全量（行为 1）。"""
    observations = [_obs(1, "agg_row"), _obs(2, "fragment", content="检索片段正文", source="报告")]
    state = _state(observations=observations)
    reply = "第一段：日产油量 10 吨[1]。\n\n第二段：检索片段佐证[2]。\n\n第三段：建议复核口径[1]。"
    with _phase(reply) as session:
        draft = session.call(state)
    frames = await _frames(session.bus)

    texts = [str(item["content"]) for item in _of(frames, "text")]
    assert len(draft.segments) == 3
    assert len(texts) == 3, texts  # 多段帧（不是一帧推全量）
    assert texts == [segment.text for segment in draft.segments]  # 一段一帧、顺序即呈现顺序
    assert reply not in texts  # 无「一次性推全量」的单帧形
    # 起草段零收口批：citation 帧与终稿都不在本轮（收口是另一拍）
    assert _of(frames, CITATION_EVENT) == []
    assert state.answer == ""
    assert state.next_intent == INTENT_VERIFY
    assert state.draft == reply  # 草稿落状态供核验消费（核验面改写归 `verification`）


# ---------- 2 每段自带 citation_seqs，且序号真实存在于观察序列 ----------


async def test_segment_citations_resolve() -> None:
    """行 2｜每段自带 `citation_seqs`，且序号**真实存在于观察序列**（行为 2）。"""
    observations = [_obs(1, "agg_row"), _obs(3, "fragment", content="片段", source="报告")]
    state = _state(observations=observations)
    reply = "结论一[1]。\n\n结论二[3][1]。"
    with _phase(reply) as session:
        draft = session.call(state)
    frames = await _frames(session.bus)

    assert [segment.citation_seqs for segment in draft.segments] == [[1], [3, 1]]
    index = _citing(observations)
    for segment in draft.segments:
        assert segment.citation_seqs  # 每段自带引标（段与引用不脱节）
        for seq in segment.citation_seqs:
            assert seq in index, f"引标 {seq} 不在观察序列"
    # 引用块（引标 → 观察序号）与段引标同源，且每条都有可机读出处
    assert [citation.seq for citation in draft.citations] == [1, 3]
    for citation in draft.citations:
        assert citation.locator  # 可机读出处在场（写了找不回＝静默丢材料）
        assert str(index[citation.seq]["locator"]["kind"]) in citation.locator
    # 段引标同步落机读 payload（答案面步 `citations` 字段）
    assert _payloads(state, _PAYLOAD_PHASE_DRAFT)[0][_PAYLOAD_CITATIONS_KEY] == [1, 3]
    # 帧面逐段可核：帧内容与段逐字一致（帧不另起第二套文本）
    assert [str(item["content"]) for item in _of(frames, "text")] == [
        segment.text for segment in draft.segments
    ]


# ---------- 3 出现不存在的引标号 → 剥除该记号（坏引标——不判失败） ----------


async def test_dangling_citation_rejected() -> None:
    """行 3｜出现不存在的引标号 → **剥除**（2026-10-17 EB5b 改判）。

    剥除族第二形（同行为 13 占位符剥除）：界外引标号整枚离场、正文其余字面零改、材料照常
    带引标交付（`completed`，不判失败、不 run_failed）；留痕＝起草步 payload 的
    `dangling_citation_seqs`（不静默）；该行失去引标即由 `verification` 按无据断言既有处置收口。
    """
    from appv2.runtimev2.answering import PAYLOAD_DANGLING_SEQS_KEY

    state = _state(observations=[_obs(1, "agg_row")])
    with _phase("结论成立[9]。域内结论另有其数[1]。") as session:
        draft = session.call(state)
    # 界外记号离场、正文其余字面零改：段文本里「[9]」已不在（域内 [1] 原样）
    assert [segment.text for segment in draft.segments] == ["结论成立。域内结论另有其数[1]。"]
    assert [segment.citation_seqs for segment in draft.segments] == [[1]]
    assert [citation.seq for citation in draft.citations] == [1]
    # 草稿落状态＝带材料直答（无半成品问题：交付面完整）
    assert state.draft == "结论成立。域内结论另有其数[1]。"
    # 留痕：起草步 payload 的坏引标序号列（不静默）
    payload = _payloads(state, _PAYLOAD_PHASE_DRAFT)[0]
    assert payload[PAYLOAD_DANGLING_SEQS_KEY] == [9]
    # 帧面：剥除后文本照常逐段出流（一段一帧）
    frames = await _frames(session.bus)
    assert [str(item["content"]) for item in _of(frames, "text")] == [
        segment.text for segment in draft.segments
    ]
    # 反向：域内引标不触发（零剥除——判据只在界外）
    in_scope = _state(observations=[_obs(1, "agg_row")])
    with _phase("结论成立[1]。") as session:
        draft = session.call(in_scope)
    assert [segment.citation_seqs for segment in draft.segments] == [[1]]
    assert _payloads(in_scope, _PAYLOAD_PHASE_DRAFT)[0][PAYLOAD_DANGLING_SEQS_KEY] == []


# ---------- 4 每次模型调用都有 Manifest；大结果只以引用进窗口 ----------


async def test_manifest_and_ref_only() -> None:
    """行 4｜每次模型调用都有 Manifest；大结果只以引用进窗口（行为 4——材料面显式）。"""
    big_body = "\n".join(f"明细行 {number}" for number in range(1, 51))
    summary = "（摘要）共 50 行——原文已落引用载体"
    observations = [
        _obs(
            1,
            "fragment",
            content=summary,
            source="报告",
            source_id="report-1",
            ref={"handle": "blob-1", "summary": summary, "row_count": 50},
        ),
        _obs(2, "agg_row", content="日产油量 10 吨", source="台账", source_id="metric-1"),
    ]
    state = _state(observations=observations)
    with _phase("结论一[1]，结论二[2]。") as session:
        draft = session.call(state)

    # ① 每次模型调用都有 Manifest 在场（模型调用步由 `bookkeeping.call_model` 单点记账）
    calls = [step for step in state.steps if str(step.get("title", "")).startswith("模型调用：")]
    assert len(calls) == 1, [step.get("title") for step in state.steps]
    assert calls[0]["manifest"] is not None  # 缺失＝判失败

    # ② 材料面 Manifest（`context.compile_manifest` 编译出口）随答案面步落地
    faces = _payloads(state, _PAYLOAD_PHASE_DRAFT)
    assert len(faces) == 1
    face_step = next(
        step
        for step in state.steps
        if isinstance(step.get("payload"), Mapping)
        and step["payload"].get(_PAYLOAD_PHASE_KEY) == _PAYLOAD_PHASE_DRAFT
    )
    manifest = face_step["manifest"]
    assert manifest is not None and manifest["material_total"] == 2
    assert manifest["material_rendered"] == 2
    assert manifest["material_truncated"] is False
    assert str(manifest["selected_reason"]).startswith("步骤 answer：")

    # ③ 大结果只以引用进窗口：全文不在窗口、摘要与引用条目在场、材料段＝context 渲染产物原样
    window = str(state.messages[-1]["content"])
    assert big_body not in window
    assert summary in window
    rendered, _meta = render_materials(
        state.observations, max_observations=DEFAULT_MAX_OBSERVATIONS
    )
    assert window.endswith(rendered)  # 本块材料渲染＝消费 context 编译产物、零自取
    # 引用可达（`seq → observation.ref`）：引标指向的观察自带稳定引用句柄
    index = _citing(observations)
    assert [citation.seq for citation in draft.citations] == [1, 2]
    assert index[1]["ref"]["handle"] == "blob-1"


# ---------- 5 被拒／缺失／未及核验 → 产出结构化 Gap（三档闭世界） ----------


async def test_structured_gaps_all_kinds() -> None:
    """行 5｜被拒／缺失／未及核验 → 产出结构化 `Gap`（三档闭世界）——不静默截断（行为 5）。"""
    state = _state(
        observations=[_obs(1, "notice", content="引擎注记：口径未定", source="引擎")],
        subtask_results=[
            {"id": "s1", "question": "q1", "status": "refused", "reason": "前置闸拒：越集"},
            {"id": "s2", "question": "q2", "status": "retryable", "reason": "工具超时"},
            {"id": "s3", "question": "q3", "status": "ok", "reason": ""},
        ],
    )
    with _phase("本轮未取得可核材料，如实说明。") as session:
        draft = session.call(state)

    kinds = sorted(gap.kind for gap in draft.gaps)
    assert kinds == ["missing", "refused", "unverified"]
    refused = next(gap for gap in draft.gaps if gap.kind == "refused")
    assert refused.subtask_id == "s1" and "前置闸拒" in refused.reason  # 哪个子问题／为什么
    missing = next(gap for gap in draft.gaps if gap.kind == "missing")
    assert missing.subtask_id == "s2" and "工具超时" in missing.reason
    unverified = next(gap for gap in draft.gaps if gap.kind == "unverified")
    assert unverified.subtask_id is None and unverified.reason  # 未及核验：零实质材料
    assert "ok" not in [gap.subtask_id for gap in draft.gaps]  # 成功支不出缺口

    # 机读面同源：答案面步 payload 的 `gaps` 字段逐条三键，与返回的 `Gap` 一致
    gaps_field = _payloads(state, _PAYLOAD_PHASE_DRAFT)[0][_PAYLOAD_GAPS_KEY]
    assert len(gaps_field) == len(draft.gaps)
    for entry, gap in zip(gaps_field, draft.gaps, strict=True):
        assert set(entry) == _PAYLOAD_GAP_KEYS
        assert (entry["kind"], entry["subtask_id"], entry["reason"]) == (
            gap.kind,
            gap.subtask_id,
            gap.reason,
        )


# ---------- 6 Gap.kind 越界取值 → 判失败 ----------


def test_gap_kind_closed_world() -> None:
    """行 6｜`Gap.kind` 越界取值 → 判失败（闭世界三档——不猜、不取默认）。"""
    assert GAP_KINDS == {"refused", "missing", "unverified"}
    for kind in sorted(GAP_KINDS):
        assert Gap(kind=kind, subtask_id=None, reason="r").kind == kind
    for build in (
        lambda: Gap(kind="unverified_note", subtask_id=None, reason="r"),
        lambda: Gap(kind="", subtask_id=None, reason="r"),
    ):
        with pytest.raises(ValueError):
            build()


# ---------- 8 收口同批落定（引用块＋citation 帧＋verdict 帧＋链尾） ----------


async def test_finalize_atomic() -> None:
    """行 8｜收口同批落定：引用块＋`citation` 帧＋链尾（`verdict` 帧为消费方信号——归编排）。

    规格行为 7 原文：「**`verdict` 帧的批次落定由 `orchestration` 协调**，本块只保证自产部分
    （引用块／`citation` 帧）就位」——故本例断言本块自产三件**同一次调用**内齐落，并断言本块
    **不产** `verdict` 帧（该帧的批次落定不在本块作用面）。
    """
    observations = [
        _obs(1, "agg_row", content="日产油量 10 吨", source="台账", source_id="metric-1"),
        _obs(2, "fragment", content="片段正文", source="报告", source_id="report-1"),
    ]
    state = _state(
        observations=observations,
        draft="结论一：日产油量 10 吨[1]。\n\n结论二：报告佐证[2]。",
        verdict={"cited": [1, 2], "ok": True},
    )
    with _phase() as session:  # 收口段零模型调用（剧本空——模型调用即当场暴露）
        final = session.call(state)
    frames = await _frames(session.bus)

    bodies = _of(frames, CITATION_EVENT)
    assert [body["index"] for body in bodies] == [1, 2]
    for body in bodies:
        assert set(body) == _CITATION_FRAME_KEYS  # 帧载荷形（S6 §一 citation 行）
        assert body["source"] and body["trust"]
    # 正文＝模型稿（引用块不入正文——EB3 D2）；引用块入增补面按「引用：」块形
    draft = "结论一：日产油量 10 吨[1]。\n\n结论二：报告佐证[2]。"
    assert state.answer == draft
    assert state.messages[-1] == {"role": "assistant", "content": state.answer}
    assert [citation.seq for citation in final.citations] == [1, 2]
    citation_block = _supplement_text(session.supplements, "citations")
    assert citation_block.endswith(
        "引用：\n[1] 台账 · metric-1（authoritative）\n[2] 报告 · report-1（report）"
    )
    assert "引用：" not in state.answer  # 正文零程序块
    # 收口不再推全量（增量早在起草段发过）；`verdict` 帧不由本块产（消费方信号）
    assert _of(frames, "text") == []
    assert _of(frames, "verdict") == []
    assert state.next_intent == INTENT_END
    # 收口步机读字段（citations／gaps）
    finalize_payload = _payloads(state, _PAYLOAD_PHASE_FINALIZE)[0]
    assert finalize_payload[_PAYLOAD_CITATIONS_KEY] == [1, 2]
    assert finalize_payload[_PAYLOAD_GAPS_KEY] == []


# ---------- 9 空稿／全无据 → 不推空答案，按缺口如实收口 ----------


async def test_empty_draft_not_pushed() -> None:
    """行 9｜空稿 → **不推空答案**，按结构化缺口如实收口（行为 9）。"""
    state = _state(observations=[_obs(1, "agg_row")])
    with _phase("   \n\n  ") as session:
        draft = session.call(state)
    frames = await _frames(session.bus)

    assert draft.segments == []
    assert _of(frames, "text") == []  # 零 text 帧——一个空答案都不推
    assert [gap.kind for gap in draft.gaps] == ["missing"]
    assert draft.gaps[0].reason == EMPTY_DRAFT_REASON
    assert draft.gaps[0].subtask_id is None
    assert state.draft == ""  # 空答案不入答案面（核验面无空稿可读）
    assert [message for message in state.messages if message["role"] == "assistant"] == []
    assert state.answer == ""
    assert state.next_intent == INTENT_END  # 按缺口如实收口
    # 起草失败如实态（不恒 ok）＋缺口落机读 payload
    face = next(
        step
        for step in state.steps
        if isinstance(step.get("payload"), Mapping)
        and step["payload"].get(_PAYLOAD_PHASE_KEY) == _PAYLOAD_PHASE_DRAFT
    )
    assert face["status"] == "failed"
    assert face["payload"][_PAYLOAD_GAPS_KEY][0]["kind"] == "missing"


# ---------- 10 模型原话不进对话层 ----------


async def test_raw_not_in_dialogue() -> None:
    """行 10｜模型原话不进对话层（行为 8：中间原话只进过程档案与留痕）。"""
    raw = "（模型中间原话：结论一[1]——本句是过程产物，不该进对话层。）"
    state = _state(observations=[_obs(1, "agg_row")])
    with _phase(raw) as session:
        session.call(state)

    assert state.dialogue == []  # 对话层零写入
    digests = [
        str(entry.get("digest", ""))
        for entry in state.process_notes
        if isinstance(entry, Mapping)
    ]
    assert any(raw in digest for digest in digests)  # 留痕在场（过程档案）
    assert not [
        message for message in state.messages if message["role"] == "assistant"
    ]  # 中间原话不追加为链上轮（终稿由收口单点追加）
    # 对话层纯度不变量：任何条目都不得是模型原话（本块根本不写该层）
    assert all(raw not in str(entry.get("content", "")) for entry in state.dialogue)


# ---------- 11 发射 JSON 不进答案面（泄漏=0；pin-04） ----------


def test_emission_strip_deterministic_contract() -> None:
    """剥离判据单点（行 11 的规则面）：围栏 JSON 段剥、裸发射行剥、散文围栏与域外 JSON 零误伤。"""
    text = (
        "结论一[1]。\n"
        "```json\n"
        '{"action": "finalize", "payload": {"answer": "嵌套"}}\n'
        "```\n"
        "```\n"
        "这是围栏里的散文，不是 JSON 段——原样保留\n"
        "```\n"
        '提示回声 {"action": "ask"} 余文一并离场\n'
        "域外片段 {\"preference\": \"保留\"} 在同一散文行上\n"
    )
    stripped, leaked = strip_emission_fences(text)
    assert leaked is True
    assert '"action"' not in stripped
    assert "嵌套" not in stripped
    assert "余文一并离场" not in stripped
    assert "结论一[1]。" in stripped
    assert "这是围栏里的散文，不是 JSON 段——原样保留" in stripped  # 纯散文围栏零误伤
    assert '{"preference": "保留"}' in stripped  # 域外 JSON 零误伤（R-A2-06）
    # 未检出 → 原样（零漂移；同入参两跑逐字相等）
    clean = "结论一[1]。\n\n结论二[2]。"
    assert strip_emission_fences(clean) == (clean, False)
    assert strip_emission_fences(clean) == strip_emission_fences(clean)


async def test_emission_strip_zero_leak() -> None:
    """行 11＋钉 `pin-04`（P0）｜发射 JSON 不进答案面：确定性剥离，泄漏=0。

    emission_strip 确定性剥离＝**已根治态**（`eval/results/Q15-对账报告.md`:38——Q14 6 题→0）；
    判据面＝`AnswerDraft` 片段与其 `text` 帧增量**两处都不得**出现发射 JSON 残留。
    """
    state = _state(observations=[_obs(1, "agg_row")])
    reply = (
        "结论一：日产油量 10 吨[1]。\n"
        "```json\n"
        '{"action": "finalize", "payload": {"answer": "不该进答案面"}}\n'
        "```\n"
        '提示回声 {"action": "ask", "question": "也不该进"} 余文\n'
        "域外片段 {\"preference\": \"保留\"} 在同一散文行上\n"
        "结论二：口径待复核[1]。"
    )
    with _phase(reply) as session:
        draft = session.call(state)
    frames = await _frames(session.bus)
    face = _answer_face(draft, frames)

    assert face, "答案面为空——判据面失效"
    assert '"action"' not in face  # 泄漏=0（发射 JSON 零残留）
    assert "```" not in face
    assert "不该进答案面" not in face
    assert "余文" not in face
    assert "结论一：日产油量 10 吨[1]。" in face  # 散文正文保留
    assert "结论二：口径待复核[1]。" in face
    assert '{"preference": "保留"}' in face  # 域外 JSON 零误伤
    # 剥离行为面机读信号在场（类型取自通知闭世界）
    assert [note for note in state.notices if note["type"] == NOTICE_EMISSION_STRIP]
    # 逐段帧同样干净（帧面与片段面同源——两处都不泄漏）
    for body in _of(frames, "text"):
        assert '"action"' not in str(body["content"])
    # 未检出 → 零通知（未截断/未检出零残留）
    clean_state = _state(observations=[_obs(1, "agg_row")])
    with _phase("结论一[1]。") as clean_session:
        clean_session.call(clean_state)
    assert clean_state.notices == []


# ---------- 11a2 剥离空稿 notice 文案如实（V2-85／挂账 A2③） ----------


async def test_emission_strip_notice_honest_on_empty_draft() -> None:
    """剥离把草稿剥成空稿时，notice 不得再称「答案不受影响」（V2-85）。"""
    state = _state(observations=[_obs(1, "agg_row")])
    with _phase('{"action": "discover", "query": "古近系"}') as session:
        draft = session.call(state)
    frames = await _frames(session.bus)

    notes = [note for note in state.notices if note["type"] == NOTICE_EMISSION_STRIP]
    assert len(notes) == 1
    assert notes[0]["content"] == answering_constants.EMISSION_STRIP_EMPTY_CONTENT
    assert notes[0]["content"] != answering_constants.EMISSION_STRIP_CONTENT
    assert draft.segments == [] and state.draft == ""
    assert _of(frames, "text") == []


async def test_emission_strip_notice_unchanged_when_draft_survives() -> None:
    """剥后仍有正文 → 保留原文案（此时「答案不受影响」如实）。"""
    state = _state(observations=[_obs(1, "agg_row")])
    reply = '结论一：日产油量 10 吨[1]。\n\n{"action": "discover", "query": "x"}'
    with _phase(reply) as session:
        draft = session.call(state)

    notes = [note for note in state.notices if note["type"] == NOTICE_EMISSION_STRIP]
    assert len(notes) == 1
    assert notes[0]["content"] == answering_constants.EMISSION_STRIP_CONTENT
    assert draft.segments and state.draft.strip()


# ---------- 11b 输入侧提取（V2-82g：整枚 finalize JSON → 交付字段作草稿） ----------


_RECOVERED_ANSWER = "你好！我是「问一问」助手。\n\n请说出你想看的井号或区块。"


def _finalize_reply(answer: Any) -> str:
    """整枚 finalize 发射 JSON（真机 `run-9d1c5267` 形：`{"action":"finalize","answer":…}`）。"""
    return json.dumps({"action": "finalize", "answer": answer}, ensure_ascii=False)


def test_extract_finalize_answer_whole_object_only() -> None:
    """单点判据（V2-82g）：只认**整应答恰一枚** finalize 对象——散文包裹／数组／标量不作数。"""
    reply = _finalize_reply(_RECOVERED_ANSWER)
    assert extract_finalize_answer(reply) == _RECOVERED_ANSWER
    assert extract_finalize_answer("```json\n" + reply + "\n```") == _RECOVERED_ANSWER  # 围栏形
    assert extract_finalize_answer("  \n" + reply + "\n  ") == _RECOVERED_ANSWER  # 两侧空白
    assert extract_finalize_answer("前言 " + reply) is None  # 散文包裹不作数
    assert extract_finalize_answer(reply + " 尾巴") is None
    assert extract_finalize_answer("[" + reply + "]") is None  # JSON 数组不作数
    assert extract_finalize_answer('"你好"') is None  # JSON 标量不作数
    assert extract_finalize_answer("你好") is None
    assert extract_finalize_answer("") is None
    assert extract_finalize_answer("```json\n" + reply) is None  # 无闭合围栏（单行退化形）不作数


async def test_finalize_json_answer_recovered() -> None:
    """V2-82g（真机 `run-9d1c5267`）｜整枚 finalize 发射 JSON → 提取交付字段作草稿并真交付。

    提取属**恢复非放行**：发射 JSON 外壳零进答案面（泄漏=0 判据不翻方向），提取后文本走既有
    剥除管线与分段发帧，`state.draft` 落提取后文本、机读痕迹走 `emission_strip` notice。
    """
    for reply in (
        _finalize_reply(_RECOVERED_ANSWER),
        "```json\n" + _finalize_reply(_RECOVERED_ANSWER) + "\n```",  # 围栏形同辖
    ):
        state = _state(observations=[_obs(1, "agg_row")])
        with _phase(reply) as session:
            draft = session.call(state)
        frames = await _frames(session.bus)

        assert draft.segments, "零片段——提取未生效（空稿热修未落地）"
        assert [segment.text for segment in draft.segments] == _RECOVERED_ANSWER.split("\n\n")
        assert state.draft == _RECOVERED_ANSWER  # 落 draft 的是提取后文本
        assert [item["content"] for item in _of(frames, "text")] == [
            segment.text for segment in draft.segments
        ]  # 分段发帧照旧（帧面与片段面同源）
        face = _answer_face(draft, frames)
        assert '"action"' not in face and "```" not in face  # 发射 JSON 外壳零进答案面
        assert draft.gaps == []  # 非空交付：零「未产出草稿」缺口
        assert [note["type"] for note in state.notices] == [NOTICE_EMISSION_STRIP]  # 机读留痕
        # 模型原话仍进过程档案（行为 8 可回溯面——digest 留原应答，含发射 JSON 原文）
        digests = [str(entry.get("digest", "")) for entry in state.process_notes]
        assert any('"action"' in digest for digest in digests)


async def test_non_finalize_json_not_recovered() -> None:
    """V2-82g｜非交付动作的整枚发射 JSON（decompose／discover／ask）→ 零提取，照旧空稿不推。"""
    for action in ("decompose", "discover", "ask"):
        reply = json.dumps({"action": action, "answer": "不该当草稿"}, ensure_ascii=False)
        state = _state(observations=[_obs(1, "agg_row")])
        with _phase(reply) as session:
            draft = session.call(state)
        frames = await _frames(session.bus)

        assert draft.segments == [] and state.draft == ""  # 零提取（照旧空稿）
        assert _of(frames, "text") == []  # 不推空答案（零 text 帧）
        assert [gap.kind for gap in draft.gaps] == ["missing"]  # 按缺口如实收口
        assert [note["type"] for note in state.notices] == [NOTICE_EMISSION_STRIP]  # 照旧剥离留痕


async def test_finalize_json_blank_answer_not_recovered() -> None:
    """V2-82g｜finalize 但交付字段空串／空白／缺失／非字符串 → 不提取（照旧空稿不推）。"""
    for payload in (
        {"action": "finalize", "answer": "   "},
        {"action": "finalize", "answer": ""},
        {"action": "finalize"},
        {"action": "finalize", "answer": 3},
    ):
        reply = json.dumps(payload, ensure_ascii=False)
        state = _state(observations=[_obs(1, "agg_row")])
        with _phase(reply) as session:
            draft = session.call(state)
        frames = await _frames(session.bus)

        assert draft.segments == [] and state.draft == ""
        assert _of(frames, "text") == []
        assert [gap.kind for gap in draft.gaps] == ["missing"]


# ---------- 自有面一：卡面签名与五形状 ----------


def test_card_signature_and_five_shapes() -> None:
    """骨架与公开面按卡面签名（`answer(state) -> AnswerDraft`）＋五形状齐（规格 :37–:60）。"""
    signature = inspect.signature(answer)
    # EB3 D2：增补面收集列表 `supplements` 为第三处 kw-only 注入面；
    # V2-96 D5：硬停止兜底正文 `forced_text` 为第四处 kw-only 注入面（缺省空串＝旧行为零漂移）；
    # V2-123：执行日注入参 `execution_date` 为第五处 kw-only 注入面（缺省空串＝材料头无执行日段）。
    assert list(signature.parameters) == [
        "state",
        "bus",
        "max_observations",
        "supplements",
        "forced_text",
        "execution_date",
    ]
    assert signature.parameters["state"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    for name in ("bus", "max_observations", "supplements", "forced_text", "execution_date"):
        assert signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
    assert (
        signature.return_annotation == "AnswerDraft"
        or signature.return_annotation is AnswerDraft
    )

    assert [field.name for field in dataclasses.fields(AnswerDraft)] == [
        "segments",
        "citations",
        "gaps",
    ]
    assert [field.name for field in dataclasses.fields(AnswerSegment)] == ["text", "citation_seqs"]
    assert [field.name for field in dataclasses.fields(Citation)] == ["seq", "locator"]
    assert [field.name for field in dataclasses.fields(Gap)] == ["kind", "subtask_id", "reason"]
    # `Citation` 不另设 `handle` 字段（与 `specs/execution.md` 字段口径显式对齐）
    assert "handle" not in {field.name for field in dataclasses.fields(Citation)}
    assert GAP_KINDS == {"refused", "missing", "unverified"}

    # 形状越界判失败（fail-closed，不猜、不取默认）
    for build in (
        lambda: Citation(seq=0, locator="台账行"),
        lambda: Citation(seq=1, locator="   "),
        lambda: Gap(kind="unknown", subtask_id=None, reason="r"),
    ):
        with pytest.raises(ValueError):
            build()
    assert answering.__all__ and "answer" in answering.__all__


# ---------- 自有面二：材料面显式（截断态；规格行 13 的用例归 -06b） ----------


async def test_material_face_explicit_on_truncation() -> None:
    """材料面显式（行为 4）在**截断态**的落地：`material_truncated` notice＋Manifest 三字段同源。

    票注：截断披露的**规格行 13 用例**（`::truncation_disclosed`）归 `RT-W4-06b-answering.md`；
    本案只保「材料进上下文必须显式」这一面在本票交付面已兑现（不许静默），不占规格表行序。
    """
    observations = [
        _obs(index, "fragment", content=f"检索片段{index}", source="报告")
        for index in range(1, 6)
    ]
    state = _state(observations=observations)
    with _phase("结论[1]。", max_observations=2) as session:
        session.call(state)

    truncated = [note for note in state.notices if note["type"] == "material_truncated"]
    assert len(truncated) == 1
    assert set(truncated[0]) == {"type", "gates", "content"}
    assert "2/5" in truncated[0]["content"]  # 实渲支数／候选支数 两计数
    face = next(
        step
        for step in state.steps
        if isinstance(step.get("payload"), Mapping)
        and step["payload"].get(_PAYLOAD_PHASE_KEY) == _PAYLOAD_PHASE_DRAFT
    )
    manifest = face["manifest"]
    assert manifest["material_truncated"] is True
    assert manifest["material_rendered"] == 2
    assert manifest["material_total"] == 5
    # 未截断零通知（零残留）
    clean_state = _state(observations=[_obs(1, "agg_row")])
    with _phase("结论[1]。") as clean_session:
        clean_session.call(clean_state)
    assert clean_state.notices == []


async def test_window_materials_payload_shape() -> None:
    """V2-93：答案步 payload 携 additive `window_materials`（四键 `selected`／`cap`／`rendered`／
    `total`）——入选逐支 `index`／`source`／`reason`，与材料段 `[n]` 同源同序；截断态 `rendered`
    按实渲检索席计、`total` 仍为候选总数（三机检字段口径零改）。"""
    observations = [
        _obs(index, "fragment", content=f"检索片段{index}", source="报告")
        for index in range(1, 4)
    ]
    state = _state(observations=observations)
    with _phase("结论[1]。") as session:
        session.call(state)
    payload = _payloads(state, _PAYLOAD_PHASE_DRAFT)[0]
    face = payload["window_materials"]
    assert set(face) == {"selected", "cap", "rendered", "total"}
    assert face["cap"] == DEFAULT_MAX_OBSERVATIONS
    assert face["total"] == 3
    assert face["rendered"] == len(face["selected"]) == 3
    assert [entry["index"] for entry in face["selected"]] == [1, 2, 3]
    assert all(set(entry) == {"index", "source", "reason"} for entry in face["selected"])
    assert all(entry["source"] == "报告" and entry["reason"] for entry in face["selected"])

    # 截断态：rendered 按实渲检索席计、total 仍为候选总数
    cut_state = _state(observations=observations)
    with _phase("结论[1]。", max_observations=2) as cut_session:
        cut_session.call(cut_state)
    cut = _payloads(cut_state, _PAYLOAD_PHASE_DRAFT)[0]["window_materials"]
    assert cut["cap"] == 2 and cut["rendered"] == 2 and cut["total"] == 3
    assert len(cut["selected"]) == 2


# ---------- 自有面三：模型调用发起面单点（无旁路） ----------


def test_no_bypass_on_public_faces() -> None:
    """模型调用发起面单点：只经 `bookkeeping.call_model`；零 `gateway_adapter`／模型供应商面。

    验收写法（票面「验收」节）：模型调用发起点只出现在 `bookkeeping.call_model`，本块零
    `gateway_adapter` import、零 `appv2.infra.llm_client`、零自建模型客户端（＋不引框架／引擎／
    旧码／其它相位）。
    """
    sources = sorted(_ANSWERING_DIR.glob("*.py"))
    assert sources, "扫描面为空——看守失效"
    modules: set[str] = set()
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
    assert "appv2.runtimev2.bookkeeping" in modules  # 模型调用发起面＝包根单点
    assert "appv2.runtimev2.context" in modules  # 材料面只消费其编译出口
    assert "appv2.runtimev2.prompts" in modules  # 指令装配文本单点
    forbidden = (
        "appv2.gateway_adapter",
        "appv2.infra",
        "appv2.runtime.",  # 旧码（R5）
        "appv2.knowledge",
        "appv2.query",
        "appv2.retrieval",
        "appv2.runtimev2.understanding",
        "appv2.runtimev2.clarification",
        "appv2.runtimev2.tool_matching",
        "appv2.runtimev2.verification",
        "appv2.runtimev2.orchestration",
    )
    assert not [module for module in modules if module.startswith(forbidden)], sorted(modules)
    assert not [module for module in modules if module.startswith("langchain")]
    assert "langgraph" not in modules
    # 程序侧零正则语义判断（形态扫描实现——纯字符串；豁免面＝形态处理）
    assert "re" not in modules and "regex" not in modules
    # 无直连模型出口调用点（自建客户端／第二出口）
    calls = [
        node.func.attr
        for path in sources
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert not [name for name in calls if name in {"complete", "acomplete", "embeddings", "create"}]


async def test_model_call_goes_through_bookkeeping_single_point() -> None:
    """「无旁路」行为断言：一次起草恰一个模型调用、归因桶＝作答桶、记账步由 `call_model` 落。"""
    state = _state(observations=[_obs(1, "agg_row")])
    with _phase("结论一[1]。") as session:
        session.call(state)
    assert session.completer.counts() == {MODEL_CALLER: 1}  # 同面替身观测：恰一次、同桶
    # 模型调用步＝`call_model` 单点记账的一条（含用量与归因面；本块不为同一调用重复记步）
    calls = [step for step in state.steps if str(step.get("title", "")).startswith("模型调用：")]
    assert len(calls) == 1
    payload = calls[0]["payload"]
    assert payload["caller"] == MODEL_CALLER and payload["run_id"] == state.run_id
    assert calls[0]["seq"] == 1  # 首步＝模型调用步（本块答案面步在其后，序号续接）
    assert state.steps[1]["seq"] == 2
    # 送进模型的是整条链（末条＝本块追加的作答轮 user 首入包＝规章段＋动态段＋材料段）；
    # V2-134（承载位回链）：请求＝整链、**零前置 system**，作答规章段**并入**该 user 首入包
    messages = session.completer.messages_of(MODEL_CALLER)[0]
    assert messages == state.messages[: len(messages)]  # 请求＝整链（零前置 system）
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"].startswith(answer_system_contract())  # 规章段并入包首
    assert "【答案要求】" in messages[-1]["content"]
    assert "观察材料：" in messages[-1]["content"]  # 材料段随 user 动态段（调用方追加）
    assert messages[-1]["content"].count(answer_system_contract()) == 1  # 并入恰一次

# ══════════════ RT-W4-06b：降级与引用簇（规格表行 7、12–22）══════════════════


# ---------- 7 矛盾来源分列且标「互不一致」，不调和 ----------


async def test_contradiction_split_not_merged() -> None:
    """行 7｜矛盾数据**分源列明、不强调和**（行为 6；EB3 D2：块入增补面不进正文）。

    形态逐字迁移真源＝`recon/A2-核验规则与归属审.md` R-A2-29／R-A2-30（同 subject 异值 ≥2 支
    → 全组成员列明；行级事实与元信息不入池）。本块在收口段**确定性装配**（不靠模型自觉），
    装配结果进增补面（正文只留模型稿）。
    """
    observations = [
        _obs(1, "fragment", content="日产油量：10 吨", source="报告A", source_id="A-1"),
        _obs(2, "fragment", content="日产油量：12 吨", source="报告B", source_id="B-1"),
        _obs(3, "fragment", content="日产液量：30 吨", source="报告A", source_id="A-2"),
    ]
    draft = "结论：日产油量两来源互有出入[1][2]。\n\n补充：日产液量另计[3]。"
    state = _state(
        observations=observations,
        draft=draft,
        verdict={"cited": [1, 2, 3], "ok": True},
    )
    with _phase() as session:
        final = session.call(state)
    await _frames(session.bus)

    face = _supplement_text(session.supplements, "split")
    assert "互不一致" in face and CONTRADICTION_SECTION_HEAD.strip() in face  # 标出「互不一致」
    # 分源列明：逐支原文照抄、各带出处（不调和＝无合并值、无取其一）
    assert "[1] 报告A · A-1：日产油量：10 吨" in face
    assert "[2] 报告B · B-1：日产油量：12 吨" in face
    assert "11 吨" not in face  # 零调和（不取中值）
    assert "[3] 报告A · A-2：日产液量：30 吨" not in face  # 县成组才列明（同 subject 才入池）
    assert state.answer == draft  # 正文零程序块（EB3 D2）
    assert [citation.seq for citation in final.citations] == [1, 2, 3]
    # 机读面同源（收口步 payload 的 `contradiction_seqs`）
    finalize = _payloads(state, _PAYLOAD_PHASE_FINALIZE)[0]
    assert finalize[PAYLOAD_CONTRADICTION_SEQS_KEY] == [1, 2]

    # 反向：同 subject **同值** → 不入池（不误判矛盾）；单支 → 不成组
    same = _state(
        observations=[
            _obs(1, "fragment", content="日产油量：10 吨", source="报告A"),
            _obs(2, "fragment", content="日产油量：10 吨", source="报告B"),
        ],
        draft="结论：两来源一致[1][2]。",
        verdict={"cited": [1, 2], "ok": True},
    )
    with _phase() as session2:
        session2.call(same)
    assert "split" not in _supplement_blocks(session2.supplements)


# ---------- 12 明细行集题交付行数＝引擎返回行数（丢行=0） ----------


async def test_rowset_full_delivery() -> None:
    """行 12｜明细行集题**全量交付**：交付行数＝引擎返回行数（50 行全交付，丢行=0）。

    钉 **`pin-08`**（P0；**交付侧**落点＝本行——执行侧落点＝`specs/execution.md` 行为 4，见
    `RT-W4-05a-execution.md` 行 4 `::big_result_ref_only`）。与 `specs/execution.md` 行为 4
    同一界线（逐字一致）：行集族观察逐行一观察、不落引用、不受检索族帽；答案面逐行带 `[n]`
    引标交付；交付行数对账落机读 payload（`engine_rows`／`delivered_rows`——差额如实，拦截与
    补注记归 `verification` 行为 11）。非行集大结果只以引用进窗口（摘要＋行数，`ref` 可达）。
    """
    observations = [
        _obs(
            index, "agg_row", content=f"井{index} 日产油量 {index} 吨", source="台账",
            source_id=f"well-{index}",
        )
        for index in range(1, 51)
    ]
    summary = "（摘要）共 50 行——原文已落引用载体"
    observations.append(
        _obs(
            51, "fragment", content=summary, source="报告", source_id="report-9",
            ref={"handle": "blob-9", "summary": summary, "row_count": 50},
        )
    )
    state = _state(observations=observations)
    reply = "\n\n".join(f"井{index} 日产油量 {index} 吨[{index}]。" for index in range(1, 51))
    with _phase(reply, max_observations=3) as session:  # 帽只辖检索族（行集族恒全量）
        draft = session.call(state)
    frames = await _frames(session.bus)

    # ① 材料面：行集族 50 行全渲染（帽不咬）、零截断 notice
    window = str(state.messages[-1]["content"])
    rendered = [
        index
        for index in range(1, 51)
        if f"[{index}]（authoritative｜台账）井{index} 日产油量 {index} 吨" in window
    ]
    assert len(rendered) == 50
    assert state.notices == []
    assert summary in window  # 非行集大结果只以引用进窗口（全文不在窗口）
    assert state.observations[50]["ref"]["row_count"] == 50  # `seq → observation.ref` 可达

    # ② 交付面：一段一行、行行带引标；交付行数＝引擎返回行数
    assert len(draft.segments) == 50
    assert [str(item["content"]) for item in _of(frames, "text")] == [
        segment.text for segment in draft.segments
    ]
    cited = {seq for segment in draft.segments for seq in segment.citation_seqs}
    assert cited == set(range(1, 51))
    face = _answer_face(draft, frames)
    assert all(f"[{index}]" in face for index in range(1, 51))
    payload = _payloads(state, _PAYLOAD_PHASE_DRAFT)[0]
    assert (payload[PAYLOAD_ENGINE_ROWS_KEY], payload[PAYLOAD_DELIVERED_ROWS_KEY]) == (50, 50)
    assert ROWSET_OBSERVATION_KINDS == {"agg_row"}

    # ③ 差额不静默：只交付一行时两数如实显差（丢行⇒机读面可判）
    short = _state(observations=observations)
    with _phase("共 50 行明细，行集从略[1]。", max_observations=3) as session2:
        session2.call(short)
    short_payload = _payloads(short, _PAYLOAD_PHASE_DRAFT)[0]
    assert (
        short_payload[PAYLOAD_ENGINE_ROWS_KEY],
        short_payload[PAYLOAD_DELIVERED_ROWS_KEY],
    ) == (50, 1)


# ---------- 13 材料截断必披露（未截断零 notice） ----------


async def test_truncation_disclosed() -> None:
    """行 13｜材料截断**必披露**：`material_truncated` notice＋「没用上的部分不作答」声明在场。

    钉 **`pin-09`**（P1）；真源＝`tickets/v2/V2-61-材料承载分形渲染.md` 附 D。截断只可能落
    检索族（权威行集与台账卡恒全量渲染——`specs/context.md` 行为 4）。
    """
    observations = [
        _obs(index, "fragment", content=f"检索片段{index}", source="报告")
        for index in range(1, 6)
    ]
    state = _state(observations=observations)
    with _phase("结论[1]。", max_observations=2) as session:
        session.call(state)

    truncated = [note for note in state.notices if note["type"] == "material_truncated"]
    assert len(truncated) == 1
    assert set(truncated[0]) == {"type", "gates", "content"}
    assert "2/5" in truncated[0]["content"]  # 渲染支数／候选支数两计数
    assert "没用上的部分不作答" in truncated[0]["content"]  # 不作答声明在场（EB4b 白话化逐字）

    # 未截断 → 零 notice（零残留）
    clean = _state(observations=[_obs(1, "agg_row")])
    with _phase("结论[1]。") as clean_session:
        clean_session.call(clean)
    assert clean.notices == []


# ---------- 14 答案面无字面占位符 `[n]` ----------


async def test_placeholder_marker_not_in_answer() -> None:
    """行 14｜答案面不得出现字面占位引标 `[n]`：含 `[n]` 的行以剥占位符形交付。

    行为 13；真源＝`eval/results/Q16-判分报告-G3.md`（:56 D-诱15 形）＋
    `tickets/v2/V2-69-坏引标修复.md`（「禁止占位符 [n] 进答案」指令纪律）。剥离单点在
    `degradation.strip_placeholders`（方括号形态扫描，零正则）；真引标 `[1]` 原样保留。
    """
    state = _state(observations=[_obs(1, "agg_row", content="日产油量 10 吨")])
    reply = "结论：日产油量 10 吨[n] 已复核[1]。\n\n[n]\n\n另注：口径以台账为准[n]。"
    with _phase(reply) as session:
        draft = session.call(state)
    frames = await _frames(session.bus)
    face = _answer_face(draft, frames)

    assert "[n]" not in face and "[N]" not in face  # 字面占位符零命中（片段与帧两处都清）
    assert [segment.text for segment in draft.segments] == [
        "结论：日产油量 10 吨 已复核[1]。",
        "另注：口径以台账为准。",
    ]  # 含 `[n]` 的行以剥占位符形交付；仅 `[n]` 的行不成段（不以占位符形式交付）
    assert [segment.citation_seqs for segment in draft.segments] == [[1], []]
    assert "[1]" in face  # 真引标原样保留
    assert all("[n]" not in str(item["content"]) for item in _of(frames, "text"))
    # 单点直测（形态判据：字母体剥、数字体留、空体留）
    assert strip_placeholders("[n]与[1]与[N]") == "与[1]与"
    assert strip_placeholders("[]保留[2]") == "[]保留[2]"


# ---------- 15 起草回声=0（echo_flag 恒 0；观测字段只记不拦） ----------


async def test_echo_flag_zero() -> None:
    """行 15｜起草回声＝0：草稿首行不以「理解：」开头／前 100 字不含「指标候选」。

    钉 **`pin-13`**（P1，观测面）；判据字面真源＝`arch/P4b-票堆V2-56至65.md` A-P4b-61。
    **观测字段只记不拦**：签名只进机读 payload，零拦截、零改写（交付面照常）。
    """
    clean = _state(observations=[_obs(1, "agg_row")])
    with _phase("结论：日产油量 10 吨[1]。") as session:
        clean_draft = session.call(clean)
    assert _payloads(clean, _PAYLOAD_PHASE_DRAFT)[0][PAYLOAD_ECHO_FLAG_KEY] is False
    assert clean_draft.segments  # 正常稿照常交付

    # 首行「理解：」开头 → 签名 True；**只记不拦**（交付面逐段不变）
    head = _state(observations=[_obs(1, "agg_row")])
    head_reply = f"{ECHO_HEAD}用户问的是日产油量。\n\n结论：10 吨[1]。"
    with _phase(head_reply) as session2:
        head_draft = session2.call(head)
    assert _payloads(head, _PAYLOAD_PHASE_DRAFT)[0][PAYLOAD_ECHO_FLAG_KEY] is True
    assert [segment.text for segment in head_draft.segments] == [
        "理解：用户问的是日产油量。",
        "结论：10 吨[1]。",
    ]

    # 前 100 字含「指标候选」→ True；落在 100 字窗外 → False（窗口判据）
    inside = _state(observations=[_obs(1, "agg_row")])
    with _phase("字" * 96 + f"{ECHO_CANDIDATE_MARK}：日产油量[1]。") as session3:
        session3.call(inside)
    assert _payloads(inside, _PAYLOAD_PHASE_DRAFT)[0][PAYLOAD_ECHO_FLAG_KEY] is True

    outside = _state(observations=[_obs(1, "agg_row")])
    with _phase("字" * 101 + f"{ECHO_CANDIDATE_MARK}：日产油量[1]。") as session4:
        outside_draft = session4.call(outside)
    assert _payloads(outside, _PAYLOAD_PHASE_DRAFT)[0][PAYLOAD_ECHO_FLAG_KEY] is False
    assert outside_draft.segments  # 窗外字样不改交付（签名只记不拦）
    # 单点直测（两判据字面同源常量）
    assert echo_flag(f"{ECHO_HEAD}说明") is True
    assert echo_flag("结论：无回声") is False


# ---------- 16 台账 no_hit → 降级交付三段形（零逐井数值冒充） ----------


async def test_no_hit_degraded_delivery_three_part() -> None:
    """行 16｜台账 no_hit（agg 未落列 notice 在场）→ 降级交付**三段齐**。

    钉 **`pin-20`**（P1；落点＝行为 15）；满分形真源＝`eval/results/Q16-判分报告-G1.md`（:39
    数-降2 判语：油田级邻近可得引用＋逐井「未找到」明示＋指路，零逐井数值——轴④封尺满分形）。

    程序面（本块可确定性保证的半面，**零业务事实发明**）＝**不静默**：引擎注记（`locator.kind
    == notice`，`context` 材料段整体排除面）以**原文**送入窗口（`prompts` 合同④「引擎的降级／
    未绑定／拦停注记必须如实转述」的材料侧承接）＋落机读 `engine_notes` 字段。三段形的**业务面
    枚举**（邻近可得量取哪支、逐井点名、指路措辞）属模型面义务（`prompts` 答案要求③／④）。
    """
    no_hit_content = "台账未命中：配产量（精确名与别名归一均未命中——请核对要素名）"
    observations = [
        {
            "index": 1,
            "locator": {"kind": "notice", "notice_type": "no_hit"},
            "content": no_hit_content,
            "source": "sem_* 台账读面",
            "source_id": "no_hit",
            "well": "",
            "version": None,
        },
        _obs(
            2, "fragment", content="计划配产 8.10 万吨，完成率 101.9%",
            source="《C-月度分析》", source_id="frag-9",
        ),
        _obs(3, "agg_row", content="Z-16 日产油量 5839.6 吨", source="台账", well="Z-16"),
        _obs(4, "agg_row", content="N-09 日产油量 1851.5 吨", source="台账", well="N-09"),
    ]
    state = _state(
        observations=observations,
        subtask_results=[
            {"id": "s1", "question": "去年各井配产量是多少？", "status": "ok", "reason": ""}
        ],
    )
    reply = (
        "① 油田级邻近可得：计划配产 8.10 万吨、完成率 101.9%[2]"
        f"（{no_hit_content}）。\n\n"
        "② 逐井明细：Z-16：未找到；N-09：未找到（本轮未取得逐井配产量）。\n\n"
        "③ 如需逐井配产量，请指明具体井或改用产量口径复核。"
    )
    with _phase(reply) as session:
        draft = session.call(state)
    frames = await _frames(session.bus)
    face = _answer_face(draft, frames)

    # 三段齐：①邻近可得带引用 ②逐井「未找到」明示 ③指路
    aggregate_line = next(line for line in face.splitlines() if "8.10" in line)
    assert "[2]" in aggregate_line  # ①带引用交付
    per_well = sorted({line for line in face.splitlines() if "未找到" in line})
    assert len(per_well) == 1
    assert "Z-16：未找到" in per_well[0] and "N-09：未找到" in per_well[0]  # ②逐井明示
    assert "请指明具体井" in face  # ③指路

    # 零逐井数值冒充：逐井行零数值（井号自身的数字除外）；答案面数值全部可溯到被引观察
    assert _number_tokens(_without_wells(per_well[0], observations)) == []
    cited = {seq for segment in draft.segments for seq in segment.citation_seqs}
    evidence = "".join(
        str(observations[seq - 1]["content"]) for seq in sorted(cited)
    )
    body = _without_wells("".join(segment.text for segment in draft.segments), observations)
    for token in _number_tokens(body):
        assert token in evidence, token

    # 不静默：引擎注记原文送入窗口 ＋ 落机读 payload（显式可判）
    window = str(state.messages[-1]["content"])
    assert no_hit_content in window
    payload = _payloads(state, _PAYLOAD_PHASE_DRAFT)[0]
    assert payload[PAYLOAD_ENGINE_NOTES_KEY] == [no_hit_content]


# ---------- 17 排名型子问题强制消费排名观察支 ----------


async def test_ranking_answer_consumes_ranking_obs() -> None:
    """行 17｜排名型子问题的答案必须从**排名观察支**取值（排名序对与排名支序信息一致）。

    钉 **`pin-19`**（P1；落点＝行为 16）；病形真源＝`arch/P4a2-票堆V2-51至55.md` A-P4a2-04
    （数-排2 形，帧证 obs[52]/[53] 曾弃）。本块落**序信息面**的结构对账（`ranking_seqs`＝排名
    观察支序号／`ranking_order_ok`＝交付序与支序一致——只记不判罚；数值复述面归 `verification`）。
    """
    observations = [
        _obs(1, "agg_row", content="Z-22 1784.7 吨", source="台账", source_id="rank-1"),
        _obs(2, "agg_row", content="N-09 1851.5 吨", source="台账", source_id="rank-2"),
        _obs(3, "agg_row", content="X-14 1873.4 吨", source="台账", source_id="rank-3"),
        _obs(4, "fragment", content="明细切片：Z-22 1784.7；N-09 1851.5", source="报告",
             source_id="frag-1"),
    ]
    matches = [{"id": "s1", "plan": {"ranking": True, "direction": "asc"}}]
    results = [{"id": "s1", "question": "去年日产油量最低的两口井", "status": "ok", "reason": ""}]

    state = _state(observations=observations, tool_matches=matches, subtask_results=results)
    ordered_reply = "去年日产油量最低的两口井：Z-22（1784.7 吨）[1]、N-09（1851.5 吨）[2]。"
    with _phase(ordered_reply) as session:
        draft = session.call(state)
    face = _answer_face(draft, await _frames(session.bus))

    assert "Z-22" in face and "N-09" in face  # 交付排名序对来自排名支
    assert [citation.seq for citation in draft.citations] == [1, 2]  # 引标锚在排名支行上
    payload = _payloads(state, _PAYLOAD_PHASE_DRAFT)[0]
    assert payload[PAYLOAD_RANKING_SEQS_KEY] == [1, 2, 3]  # 排名观察支在册（行集族序）
    assert payload[PAYLOAD_RANKING_ORDER_OK_KEY] is True  # 排名序对与支序一致

    # 反向（弃支他拼／序反形）：交付序与支序不一致——如实落机读面（不静默）
    reversed_state = _state(
        observations=observations, tool_matches=matches, subtask_results=results
    )
    with _phase("最低两口：N-09（1851.5 吨）[2]、Z-22（1784.7 吨）[1]。") as session2:
        session2.call(reversed_state)
    assert (
        _payloads(reversed_state, _PAYLOAD_PHASE_DRAFT)[0][PAYLOAD_RANKING_ORDER_OK_KEY] is False
    )

    # 非排名题：排名支面零在册（保留集：普通答案的取值行为不变）
    plain = _state(observations=observations, subtask_results=results)
    with _phase("结论：Z-22 为 1784.7 吨[1]。") as session3:
        session3.call(plain)
    plain_payload = _payloads(plain, _PAYLOAD_PHASE_DRAFT)[0]
    assert plain_payload[PAYLOAD_RANKING_SEQS_KEY] == []
    assert plain_payload[PAYLOAD_RANKING_ORDER_OK_KEY] is True


# ---------- 18 多油田题分源列明归属配对（「某区块」形零命中） ----------


async def test_cross_oilfield_attribution_paired() -> None:
    """行 18｜跨油田题的答案面**分源列明归属配对**（油田名↔数值／结论）在场。

    钉 **`pin-03`**（P0；落点＝行为 17）；禁形真源＝`eval/results/Q16-判分报告-G3.md`（:32
    C-正6 判语：「34-8 侧 −42.6 被无据框成『某区块／小范围结算序列』、不认列渤中34-8 油田归属」）。
    本块在收口段**确定性装配**逐源配对块（逐支原文照抄——不靠模型自觉、零业务发明）；含糊归属形
    与无据归属不由本块产出；单出处＝零追加（保留集）。
    """
    observations = [
        _obs(1, "fragment", content="渤中34-8 油田累积亏空 −42.6 万吨",
             source="《渤中34-8油田季报》", source_id="BZ34-8-Q3"),
        _obs(2, "fragment", content="渤中34-5 油田累积亏空 −128.6 万吨",
             source="《渤中34-5油田注水分析》", source_id="BZ34-5-Q3"),
    ]
    state = _state(
        observations=observations,
        draft="累积亏空分别约 −42.6 与 −128.6 万吨，口径见来源[1][2]。",  # 含糊归属的模型稿
        verdict={"cited": [1, 2], "ok": True},
    )
    with _phase() as session:
        session.call(state)
    face = _supplement_text(session.supplements, "attribution")

    assert SOURCE_SECTION_HEAD.strip() in face  # 分源列明块在场（增补面）
    assert "[1] 《渤中34-8油田季报》：渤中34-8 油田累积亏空 −42.6 万吨" in face
    assert "[2] 《渤中34-5油田注水分析》：渤中34-5 油田累积亏空 −128.6 万吨" in face
    attribution = face.split(SOURCE_SECTION_HEAD.strip())[1]  # 归属块面（逐源配对行）
    for line in attribution.splitlines():  # 归属配对：每条数值与自己的油田名同行
        if "−42.6" in line:
            assert "渤中34-8" in line
        if "−128.6" in line:
            assert "渤中34-5" in line
    assert "某区块" not in face  # 含糊归属形零命中（C-正6 形禁现）
    assert "小范围结算序列" not in face
    assert state.answer == "累积亏空分别约 −42.6 与 −128.6 万吨，口径见来源[1][2]。"  # 正文零程序块

    # 单出处（普通答案）＝零分源块（保留集：分源行为不变）
    plain = _state(
        observations=[_obs(1, "metric", content="日产油量口径：开井日历折算", source="台账")],
        draft="口径为开井日历折算[1]。",
        verdict={"cited": [1], "ok": True},
    )
    with _phase() as session2:
        session2.call(plain)
    assert "attribution" not in _supplement_blocks(session2.supplements)
    assert "split" not in _supplement_blocks(session2.supplements)


# ---------- 19 程序侧无词表／正则语义判断（AST 扫描） ----------

_CASE_FOLD_METHODS = {"lower", "upper", "casefold"}
_WORD_FACE_METHODS = {"startswith", "endswith", "partition", "count"}
# 扫描面＝本块全部正则面（`re`）与**语义词表**两类；豁免面＝形态处理／集合成员判定（规格行 19）：
# 方括号／空白／信任级／JSON 首字符等**结构字符集**的成员判定与**闭世界取值**判定不算词表，
# `strip`／`split`／`find` 等**形态切分与形态扫描**不算词面判。被咬三形＝①含汉字串的字面集合
# （语义词表形）；②非 ASCII 字面成员判定（拿中文词当判据）；③**词面判**——大小写折叠（无条件）
# 与「以中文词起止／切分／计数」的字符串方法（结构字符集参数不咬：-A 的 JSON 首字符判定即此面）。


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _has_cjk_argument(node: ast.Call) -> bool:
    """调用是否以**汉字串字面**为参（词面判据的形态面——结构字符集参数不算）。"""
    for arg in (*node.args, *(keyword.value for keyword in node.keywords)):
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and _has_cjk(arg.value):
            return True
        if isinstance(arg, (ast.Tuple, ast.List, ast.Set)):
            for item in arg.elts:
                if (
                    isinstance(item, ast.Constant)
                    and isinstance(item.value, str)
                    and _has_cjk(item.value)
                ):
                    return True
    return False


def _lexicon_violations(tree: ast.Module) -> list[str]:
    """词表／正则面探测（`re` 面＋含汉字串的字面集合＋非 ASCII 字面成员判定＋词面判方法）。"""
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            for name in names:
                if name.split(".")[0] in {"re", "regex"}:
                    findings.append(f"L{node.lineno} 引入正则面：{name}")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in {"re", "regex"}:
                findings.append(f"L{node.lineno} 使用正则面：{node.value.id}.{node.attr}")
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            for item in node.elts:
                if (
                    isinstance(item, ast.Constant)
                    and isinstance(item.value, str)
                    and _has_cjk(item.value)
                ):
                    findings.append(f"L{node.lineno} 字面集合含汉字串（语义词表形）")
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if isinstance(op, (ast.In, ast.NotIn)):
                    for operand in (node.left, *node.comparators):
                        if (
                            isinstance(operand, ast.Constant)
                            and isinstance(operand.value, str)
                            and not operand.value.isascii()
                        ):
                            findings.append(
                                f"L{node.lineno} 非结构字符集的成员判据：{operand.value!r}"
                            )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in _CASE_FOLD_METHODS:
                findings.append(f"L{node.lineno} 词面判方法：{attr}")
            elif attr in _WORD_FACE_METHODS and _has_cjk_argument(node):
                findings.append(f"L{node.lineno} 词面判方法（中文词参）：{attr}")
    return findings


def _membership_sites(tree: ast.Module) -> list[int]:
    """集合成员判定位点（豁免面的实际出现面——扫描面非空转的判据）。"""
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Compare)
        and any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops)
    ]


def test_no_lexicon_or_regex_in_answering() -> None:
    """行 19｜程序侧**无词表／正则语义判断**（AST 扫描本模块；豁免面＝形态处理／集合成员判定）。

    「答没答上原问题」交模型与 `verification`（`walk/00-设计总纲.md` §二）；本块只做结构判据。
    豁免面两半的实际出现＝集合成员判定（`Gap.kind`／发射动作／行集族／矛盾池豁免面闭世界取值）
    与形态处理（方括号记号扫描、空行分段、JSON 形判定——零正则实现，见 `emission` 模块注）。
    """
    sources = sorted(_ANSWERING_DIR.glob("*.py"))
    assert len(sources) >= 5, f"扫描面可疑（文件数 {len(sources)}）"
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert _lexicon_violations(tree) == [], f"{path.name}: {_lexicon_violations(tree)}"

    # 豁免面非空转：本块确有闭世界集合成员判定位点（形态处理／集合成员判定）
    membership = [line for path in sources for line in _membership_sites(_tree_of(path))]
    assert membership, "集合成员判定缺席——扫描面空转"
    # 闭世界取值面全 ASCII（结构取值，非语义词表）；回声签名两字面是**规格逐字给定的形态签名**
    # （A-P4b-61，只记不拦）——以单值常量承载、不入任何字面集合（故不被词表探测咬）。
    assert all(value.isascii() for value in ROWSET_OBSERVATION_KINDS | GAP_KINDS)
    assert _defined(sources, "strip_placeholders") and _defined(sources, "echo_flag")
    assert _defined(sources, "citation_seqs"), "形态扫描单点（引标／占位符同面）缺席"
    # 两判据字面以单值常量承载（非集合形）——回声签名的字面不被词表探测咬，是豁免面的**显式**面
    assert not _lexicon_violations(ast.parse(f'MARK = "{ECHO_CANDIDATE_MARK}"\n'))
    assert _lexicon_violations(ast.parse(f'MARKS = ["{ECHO_CANDIDATE_MARK}"]\n'))

    # 探测器非空转：词表／正则／词面判方法／汉字串成员判据四形各被咬
    assert _lexicon_violations(ast.parse('WORDS = ["提及", "执行"]\n'))
    assert _lexicon_violations(ast.parse('import re\nre.search("理解", text)\n'))
    assert _lexicon_violations(ast.parse('if "谢谢" in text:\n    pass\n'))
    assert _lexicon_violations(ast.parse('text.startswith("理解：")\n'))
    assert _lexicon_violations(ast.parse('names.count("日产油量")\n'))
    assert _lexicon_violations(ast.parse('if text.lower() == "no_hit":\n    pass\n'))
    # 豁免不是漏网：结构字符集起止判与闭世界取值成员判（-A `emission` 的 JSON 首字符判定面）不被咬
    assert not _lexicon_violations(ast.parse('line.startswith(("{", "["))\n'))
    assert not _lexicon_violations(ast.parse('kind in {"agg_row", "lineage"}\n'))


def _tree_of(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _defined(sources: list[Path], name: str) -> bool:
    """形态层函数在场判据（`degradation` 单点：占位符剥离／回声签名／引标扫描）。"""
    return any(
        isinstance(node, ast.FunctionDef) and node.name == name
        for path in sources
        for node in ast.walk(_tree_of(path))
    )


# ---------- 20 流式、缺口、截断披露的机读信号在场 ----------


async def test_answering_signal_present() -> None:
    """行 20｜流式、缺口、截断披露的机读信号在场（`text`／`citation` 帧＋`material_truncated`
    notice＋step payload；`verdict` 为消费方信号——批次落定归 `orchestration`）。
    """
    observations = [
        _obs(index, "fragment", content=f"检索片段{index}", source="报告")
        for index in range(1, 6)
    ]
    state = _state(
        observations=observations,
        subtask_results=[
            {"id": "s1", "question": "q1", "status": "refused", "reason": "前置闸拒：越集"}
        ],
    )
    with _phase("第一段[1]。\n\n第二段[2]。", max_observations=2) as session:
        session.call(state)  # 起草拍
        state.verdict = {"cited": [1, 2], "ok": True}
        session.call(state)  # 收口拍
    frames = await _frames(session.bus)

    assert len(_of(frames, "text")) == 2  # 流式增量机读信号（多段帧）
    assert [body["index"] for body in _of(frames, CITATION_EVENT)] == [1, 2]  # 引标落账信号
    truncated = [note for note in state.notices if note["type"] == "material_truncated"]
    assert len(truncated) == 1 and "没用上的部分不作答" in truncated[0]["content"]  # 截断披露信号
    draft_payload = _payloads(state, _PAYLOAD_PHASE_DRAFT)[0]
    assert draft_payload[_PAYLOAD_CITATIONS_KEY] == [1, 2]
    assert [entry["kind"] for entry in draft_payload[_PAYLOAD_GAPS_KEY]] == ["refused"]  # 缺口信号
    finalize_payload = _payloads(state, _PAYLOAD_PHASE_FINALIZE)[0]
    assert finalize_payload[_PAYLOAD_CITATIONS_KEY] == [1, 2]
    assert finalize_payload[_PAYLOAD_GAPS_KEY] == []
    assert _of(frames, "verdict") == []  # verdict 帧＝消费方信号（本块不产）


# ---------- 21 【边界集】四形各落对应分支 ----------


async def test_boundary_single_seg_zero_material_conflict_bad_cite() -> None:
    """行 21｜【边界集】单段答案／零材料／矛盾双源／坏引标 → 各自落到对应分支。"""
    # ① 单段答案：恰一段、恰一帧；零分源块（单支不成组）
    single = _state(observations=[_obs(1, "metric", content="口径：开井日历折算", source="台账")])
    with _phase("结论：口径为开井日历折算[1]。") as session:
        single_draft = session.call(single)
    single_frames = await _frames(session.bus)
    assert len(single_draft.segments) == 1 and len(_of(single_frames, "text")) == 1
    assert "互不一致" not in _answer_face(single_draft, single_frames)

    # ② 零材料：零实质材料 → `unverified` 缺口（材料段逐字「（无）」；有稿仍交付）
    empty = _state(observations=[])
    with _phase("本轮未取得材料，如实说明。") as session2:
        empty_draft = session2.call(empty)
    assert [gap.kind for gap in empty_draft.gaps] == ["unverified"]
    assert empty_draft.segments
    assert "观察材料：\n（无）" in str(empty.messages[-1]["content"])
    assert _payloads(empty, _PAYLOAD_PHASE_DRAFT)[0][PAYLOAD_ENGINE_ROWS_KEY] == 0

    # ③ 矛盾双源：分源列明＋「互不一致」进增补面（不调和；正文零程序块）
    conflict = _state(
        observations=[
            _obs(1, "fragment", content="日产油量：10 吨", source="报告A"),
            _obs(2, "fragment", content="日产油量：12 吨", source="报告B"),
        ],
        draft="结论：两来源有出入[1][2]。",
        verdict={"cited": [1, 2], "ok": True},
    )
    with _phase() as session3:
        session3.call(conflict)
    assert "互不一致" in _supplement_text(session3.supplements, "split")
    assert "互不一致" not in conflict.answer

    # ④ 坏引标：剥除（2026-10-17 EB5b——界外记号离场、材料照常交付，不判失败）
    bad = _state(observations=[_obs(1, "agg_row")])
    with _phase("结论成立[9]。[1]") as session4:
        bad_draft = session4.call(bad)
    assert [segment.text for segment in bad_draft.segments] == ["结论成立。[1]"]
    assert bad.draft == "结论成立。[1]"
    assert _payloads(bad, _PAYLOAD_PHASE_DRAFT)[0]["dangling_citation_seqs"] == [9]


# ---------- 22 【保留集】无矛盾、无缺口的普通答案：引标与分源行为不变 ----------


async def test_retention_plain_answer_unchanged() -> None:
    """行 22｜【保留集】无矛盾、无缺口的普通答案：引标与分源行为不变（零新增块／零新增信号）。"""
    observations = [
        _obs(1, "metric", content="日产油量口径：开井日历折算", source="台账", source_id="metric-1")
    ]
    results = [{"id": "s1", "question": "口径是什么", "status": "ok", "reason": ""}]

    # ① 起草拍：机读面零新增信号（回声签名 False、引擎注记空、矛盾池空、行集族零在册）
    drafting = _state(observations=observations, subtask_results=results)
    with _phase("口径为开井日历折算[1]。") as session:
        draft = session.call(drafting)
    assert draft.gaps == []  # 无缺口
    payload = _payloads(drafting, _PAYLOAD_PHASE_DRAFT)[0]
    assert payload[PAYLOAD_ECHO_FLAG_KEY] is False
    assert payload[PAYLOAD_ENGINE_NOTES_KEY] == []
    assert payload[PAYLOAD_CONTRADICTION_SEQS_KEY] == []
    assert (payload[PAYLOAD_ENGINE_ROWS_KEY], payload[PAYLOAD_DELIVERED_ROWS_KEY]) == (0, 0)
    assert payload[PAYLOAD_RANKING_SEQS_KEY] == []
    assert payload[PAYLOAD_RANKING_ORDER_OK_KEY] is True
    assert drafting.notices == []

    # ② 收口拍：引标行为不变（段引标／引用块／citation 帧／链尾逐字同 -A 形）
    state = _state(
        observations=observations,
        subtask_results=results,
        draft="口径为开井日历折算[1]。",
        verdict={"cited": [1], "ok": True},
    )
    with _phase() as session2:
        final = session2.call(state)
    frames = await _frames(session2.bus)
    assert final.gaps == []
    assert [segment.citation_seqs for segment in final.segments] == [[1]]
    assert [citation.seq for citation in final.citations] == [1]
    assert [body["index"] for body in _of(frames, CITATION_EVENT)] == [1]
    # 正文＝模型稿；引用块入增补面（EB3 D2）；单出处＝零分源／归属块
    assert state.answer == "口径为开井日历折算[1]。"
    assert "引用：" not in state.answer
    assert _supplement_text(session2.supplements, "citations").endswith(
        "引用：\n[1] 台账 · metric-1（ledger）"
    )
    assert _supplement_blocks(session2.supplements) == ["citations"]  # 单出处：零分源／归属块
    assert _of(frames, "verdict") == []
    assert state.answer == state.messages[-1]["content"]


# ---------- 23 【EB3 D2】四类块不在正文、按产出序入增补面 ----------


async def test_supplements_carry_blocks_out_of_body() -> None:
    """EB3 D2｜四类块**不进正文**：正文＝模型稿；分源／归属／引用三块按产出序入增补面。

    真源方案 `docs/runtime-refactor/proposals/EB3-交付面分层与缺陷修复.md` D2（answering 收口段）：
    「互不一致——各来源说法如下…」块 → `split`；分源归属块 → `attribution`；「引用：」块 →
    `citations`；剥除后 `state.answer`／链尾不再含这些块。条目为 `{block, text}`（块型闭世界
    四值由 `transport` 把守——本件另钉条目的键形）。
    """
    observations = [
        _obs(1, "fragment", content="日产油量：10 吨", source="报告A", source_id="A-1"),
        _obs(2, "fragment", content="日产油量：12 吨", source="报告B", source_id="B-1"),
    ]
    draft = "结论：日产油量两来源互有出入[1][2]。"
    state = _state(
        observations=observations, draft=draft, verdict={"cited": [1, 2], "ok": True}
    )
    with _phase() as session:
        session.call(state)
    await _frames(session.bus)

    assert state.answer == draft  # 正文＝模型稿（零程序块）
    for mark in ("互不一致", SOURCE_SECTION_HEAD.strip(), "引用："):
        assert mark not in state.answer
    assert state.messages[-1] == {"role": "assistant", "content": draft}  # 链尾同源
    # 按产出序入增补面：分源 → 归属 → 引用（块型闭世界四值之内）
    assert _supplement_blocks(session.supplements) == ["split", "attribution", "citations"]
    for entry in session.supplements:
        assert set(entry) == {"block", "text"}  # 载荷形恰二键（空文本零入列）
        assert entry["text"].strip()
    split_text = _supplement_text(session.supplements, "split")
    assert "互不一致" in split_text  # 行为 6 的「互不一致」标随块走（不入正文）


# ══════════ 2026-10-17 F1 件三：残尾护栏（定稿前悬空结构 → 诚实收口）══════════════
#
# 真机证据＝`eval/results/frames/EB4-D-诱12.json`（run-c6fd52c7）：删句误伤后交付答案断在裸标题
# 「**两口井教训的差异**」（其下段落整段被删）。护栏是**兜底**（误伤本体已由 verification 侧 F1
# 件一／件二修掉）——命中即程序补一句诚实收口（白话、具名常量），正文其余字面零改、零拦截。


async def test_dangling_tail_guard_closes_honestly() -> None:
    """F1 件三｜悬空结构三形（悬空引导句／光表头／裸标题）命中 → 定稿补诚实收口短句
    （`degradation.dangling_tail_closing` 判据单点；正文其余字面零改、不拦不重试）。"""
    observations = [_obs(1, "fragment", content="W-22 井检泵周期 295 天", source="报告A")]
    body = "W-22 井检泵周期 295 天[1]。"

    # ① 悬空引导句（末行以全角「：」收尾）
    lead_in = _state(
        observations=observations,
        draft=body + "\n\n两井教训差异如下：",
        verdict={"cited": [1], "ok": True},
    )
    with _phase() as session:
        session.call(lead_in)
    assert lead_in.answer == body + "\n\n两井教训差异如下：\n\n" + TAIL_CLOSE_LEAD_IN
    assert lead_in.answer[: len(body)] == body  # 正文其余字面零改
    assert lead_in.messages[-1] == {"role": "assistant", "content": lead_in.answer}

    # ② 光表头（markdown 表头行后无数据行）
    table_head = _state(
        observations=observations,
        draft=body + "\n\n| 井号 | 船日 |\n|---|---|",
        verdict={"cited": [1], "ok": True},
    )
    with _phase() as session:
        session.call(table_head)
    assert table_head.answer.endswith(TAIL_CLOSE_TABLE_HEADER)

    # ③ 裸标题：真机帧形（整行加粗）＋独立短行
    for tail in ("**两口井教训的差异**", "两口井教训的差异"):
        bare = _state(
            observations=observations,
            draft=body + "\n\n" + tail,
            verdict={"cited": [1], "ok": True},
        )
        with _phase() as session:
            session.call(bare)
        assert bare.answer == body + "\n\n" + tail + "\n\n" + TAIL_CLOSE_BARE_HEADING

    # 重入幂等：同一收口再跑一次，收口短句只在场一份（正文不重复落）
    with _phase() as session:
        session.call(bare)
    assert bare.answer.count(TAIL_CLOSE_BARE_HEADING) == 1

    # 【保留集】完整正文（句读收尾／完整表／单行短答）零追加——护栏不误伤
    for draft in (
        body,
        body + "\n\n| 井号 | 船日 |\n|---|---|\n| W-22 | 5.0 |",
        "该井日产油量 21.16 吨",
    ):
        intact = _state(observations=observations, draft=draft, verdict={"cited": [1], "ok": True})
        with _phase() as session:
            session.call(intact)
        assert intact.answer == draft
        assert dangling_tail_closing(draft) == ""
