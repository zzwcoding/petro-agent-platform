"""answering 块验收（RT-W4-06a：骨架＋接口＋交付行为簇）。

票面对象＝`specs/answering.md`「验收测试」表 :100–:110 的 **10 行**（`#` 列保留规格表行序
1–6、8–11，逐字照票面；测试标识同规格列——`test_` 前缀为本仓 pytest 收集口径，其余逐字一致）：

- 行 1 `::streaming_segments`：答案一段段推（多段 `text` 帧），非一次性推全量；
- 行 2 `::segment_citations_resolve`：每段自带 `citation_seqs`，且序号真实存在于观察序列；
- 行 3 `::dangling_citation_rejected`：出现不存在的引标号 → 判失败（坏引标）；
- 行 4 `::manifest_and_ref_only`：每次模型调用都有 Manifest；大结果只以引用进窗口；
- 行 5 `::structured_gaps_all_kinds`：被拒／缺失／未及核验 → 产出结构化 `Gap`（三档闭世界）；
- 行 6 `::gap_kind_closed_world`：`Gap.kind` 越界取值 → 判失败；
- 行 8 `::finalize_atomic`：收口同批落定（引用块＋citation 帧＋verdict 帧＋链尾）；
- 行 9 `::empty_draft_not_pushed`：空稿／全无据 → 不推空答案，按缺口如实收口；
- 行 10 `::raw_not_in_dialogue`：模型原话不进对话层；
- 行 11 `::emission_strip_zero_leak`：发射 JSON 不进答案面（确定性剥离，泄漏=0）。

测试网钉＝**`pin-04`**（P0「发射 JSON 不得进答案面（emission_strip 确定性剥离，泄漏=0 是已根治
态）」）——对应用例＝行 11 的 `::emission_strip_zero_leak`（本票承载『交付面』1 行；另 6 条 pin 行
归 `RT-W4-06b-answering.md`）。

本票另两条自有面（非规格表行，与 -A 验收节同源）：
- `::card_signature_and_five_shapes`：骨架与公开面按卡面签名（`answer(state) -> AnswerDraft`）
  ＋五形状齐（规格 :37–:60）；
- `::no_bypass_on_public_faces`：模型调用发起面单点（只经 `bookkeeping.call_model`；本块零
  `gateway_adapter` import、零 `appv2.infra.llm_client`、零自建模型客户端／帧通路）。

接缝（`core` 模块注）：`bus`（`transport.EventBus`——本块自产 `text`／`citation` 帧的唯一出口）
与 `max_observations`（材料帽）两处关键词注入面；Seam＝起草出口（增量文本 → 事件帧），
Adapter＝剧本化 completer。对逐字稿任何一行偏离即停报 L0——本件照抄、未改一字。
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import appv2.runtimev2.answering as answering
from appv2.runtimev2.answering import (
    CITATION_EVENT,
    EMPTY_DRAFT_REASON,
    GAP_KINDS,
    MODEL_CALLER,
    NOTICE_EMISSION_STRIP,
    AnswerDraft,
    AnswerSegment,
    Citation,
    DanglingCitationError,
    Gap,
    answer,
    strip_emission_fences,
)
from appv2.runtimev2.context import DEFAULT_MAX_OBSERVATIONS, render_materials
from appv2.runtimev2.gateway_adapter import ScriptedCompleter, set_completer
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
    """一次相位会话（注入剧本化 completer ＋ per-run 总线；逐次 `call` 走 `answer`）。"""

    bus: EventBus
    completer: ScriptedCompleter
    max_observations: int = DEFAULT_MAX_OBSERVATIONS

    def call(self, state: RunState) -> AnswerDraft:
        return answer(state, bus=self.bus, max_observations=self.max_observations)


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


def _answer_face(draft: AnswerDraft, frames: list[SseEvent]) -> str:
    """答案面文本（片段 ＋ `text` 帧增量——发射剥离的判据面须两处都清）。"""
    texts = [str(item.get("content", "")) for item in _of(frames, "text")]
    return "\n".join([segment.text for segment in draft.segments] + texts)


def _citing(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """观察序号索引（引标解析面）。"""
    return {int(row["index"]): row for row in observations}


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


# ---------- 3 出现不存在的引标号 → 判失败（坏引标） ----------


async def test_dangling_citation_rejected() -> None:
    """行 3｜出现不存在的引标号 → 判失败（坏引标）——不猜、不补、不静默丢弃（行为 2／4）。"""
    state = _state(observations=[_obs(1, "agg_row")])
    reply = "结论成立[9]。"
    with _phase(reply) as session:
        with pytest.raises(DanglingCitationError) as excinfo:
            session.call(state)
    assert excinfo.value.dangling == (9,)
    assert "9" in str(excinfo.value)
    # 判失败先于发帧：坏引标不上帧面（零半成品）
    frames = await _frames(session.bus)
    assert _of(frames, "text") == []
    assert state.draft == ""  # 不返回半成品（草稿不落状态）
    assert state.answer == ""
    # 反向：域内引标不触发（判据只在界外）
    in_scope = _state(observations=[_obs(1, "agg_row")])
    with _phase("结论成立[1]。") as session:
        draft = session.call(in_scope)
    assert [segment.citation_seqs for segment in draft.segments] == [[1]]


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
    # 引用块（答案面）＋链尾（同批：一次调用内）
    assert state.answer.endswith(
        "\n\n引用：\n[1] 台账 · metric-1（authoritative）\n[2] 报告 · report-1（report）"
    )
    assert state.messages[-1] == {"role": "assistant", "content": state.answer}
    assert [citation.seq for citation in final.citations] == [1, 2]
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


# ---------- 自有面一：卡面签名与五形状 ----------


def test_card_signature_and_five_shapes() -> None:
    """骨架与公开面按卡面签名（`answer(state) -> AnswerDraft`）＋五形状齐（规格 :37–:60）。"""
    signature = inspect.signature(answer)
    assert list(signature.parameters) == ["state", "bus", "max_observations"]
    assert signature.parameters["state"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    for name in ("bus", "max_observations"):
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
    # 送进模型的是整条链（末条＝本块追加的作答轮 user 指令＋材料段）
    messages = session.completer.messages_of(MODEL_CALLER)[0]
    assert messages == state.messages[: len(messages)]
    assert messages[-1]["role"] == "user"
    assert "【答案要求】" in messages[-1]["content"]
    assert "观察材料：" in messages[-1]["content"]
