"""verification 块验收（RT-W4-07a：骨架＋接口＋核心核验簇＋交付记账面）。

票面对象＝`specs/verification.md`「验收测试」表 **11 行**（`#` 列保留规格表行序 1–9、15、16，逐字
照票面；测试标识同规格列——`test_` 前缀为本仓 pytest 收集口径，其余逐字一致）：

- 行 1 `::per_line_check`：逐行核验（多句答案逐句判定，非整段判）；
- 行 2 `::cited_value_must_be_restated`：数值未在断言里复述 → 判无据并改写；
- 行 3 `::unsupported_rewritten_with_notice`：无据句改写成「未找到」＋ notice 在场；
- 行 4 `::conflict_split_not_merged`：矛盾来源分列、各带出处、不调和；
- 行 5 `::attribution_mismatch`：归属对不上 → `attribution=False` ＋ 缺口；
- 行 6 `::verdict_all_keys`：`Verdict` 各字段齐备；缺字段判失败；
- 行 7 `::token_boundary_no_substring_false_positive`：边界记号化（`52` 不命中 `1520`）；
- 行 8 `::fullwidth_normalized_before_split`：全角／半角标点先归一后切分；
- 行 9 `::no_number_assertion_not_auto_pass`：零数值断言不自动判过；
- 行 15 `::verification_signal_present`：机读信号在场（verdict／notice ＋ step payload）；
- 行 16 `::row_reconciliation_bookkeeping`：行集对账两字段入 `Verdict` 与 step payload；差额>0 且
  答案面无行集声明 → 补如实注记（不改写、不拦截）。

测试网钉（全块 6 行，全在本票）落点分布——pin-01／pin-02 为 P0 承重钉：

- `pin-01`（题眼锚定归属审）→ 行 5；`pin-02`（答案面禁现无据差值／无据口径框架）→ 行 2／行 3；
- `pin-10`（citation 落账，不得 `cited=[]` 且数字在场）→ 行 9（＋接口 `Verdict.cited`）；
- `pin-11`（INV-1 前缀只挂无据行，有据行不粘前缀）→ 行 3；
- `pin-12`（对账机读字段入 step payload）→ 行 16（＋接口 `Verdict` 两字段）；
- `pin-03`（跨油田题分源列明归属）：按规格本行自注「本块无独立落点——verify 侧仅行为 5 归属审触发
  面；答案交付面的分源列明属 prompts 合同」**只登记不硬挂**（登记备查，不落本块验收行）——行 5 的
  归属审触发面为其在 verify 侧的承接面。

本票另两条自有面（非规格表行，与 -A 验收节同源）：

- `::card_signature_and_three_shapes`：骨架与公开面按卡面签名（`verify(state) -> Verdict`）
  ＋三形状齐（规格 :32–:51：`Verdict` 九键／`RewriteRecord`／`Gap` 复用 `answering` 口径）；
- `::public_face_and_zero_model_import_contract`：零模型面只核 import 契约（本块不引
  `appv2.runtimev2.gateway_adapter`／不引 `appv2.infra.llm_client`／不引框架；AST 双证用例归
  -07b）。

-B 票（`RT-W4-07b-verification.md`）续用同一行序补第 10–14、17、18 行（确定性／
`RewriteRecord.reason`
闭世界／核验器抛错 fail-closed／零 LLM AST＋import 双证／零词表正则 AST／【边界集】／【保留集】）。
对逐字稿任何一行偏离即停报 L0——本件照抄、未改一字。
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import appv2.runtimev2.verification as verification
from appv2.runtimev2.state import RunState
from appv2.runtimev2.transport import EventBus, SseEvent
from appv2.runtimev2.verification import (
    ATTRIBUTION_CARRIER_KINDS,
    CARRIER_KINDS,
    EVENT_NOTICE,
    EVENT_VERDICT,
    GAP_KINDS,
    GAP_UNVERIFIED,
    NOTICE_ATTRIBUTION_SPLIT,
    NOTICE_CONTRADICTION_SPLIT,
    NOTICE_UNSUPPORTED_CLAIM,
    PAYLOAD_ATTRIBUTION_KEY,
    PAYLOAD_CITED_KEY,
    PAYLOAD_DELIVERED_ROWS_KEY,
    PAYLOAD_GAPS_KEY,
    PAYLOAD_OBS_ROWS_KEY,
    PAYLOAD_OK_KEY,
    PAYLOAD_REWRITES_KEY,
    PAYLOAD_REWRITTEN_KEY,
    PAYLOAD_ROW_NOTE_KEY,
    PAYLOAD_SPLIT_KEY,
    PAYLOAD_SUPPORTED_KEY,
    PHASE,
    REWRITE_CONFLICT,
    REWRITE_NO_MATERIAL,
    REWRITE_PREFIX,
    ROWSET_OBSERVATION_KINDS,
    Gap,
    RewriteRecord,
    Verdict,
    verify,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VERIFICATION_DIR = _REPO_ROOT / "appv2" / "runtimev2" / "verification"

_WELL_QUESTION = "W-11 井生产套管的尺寸与下深是多少？"

# `verdict` 帧载荷键集（真源 `synth/S6-事件与帧目录.md` §一 verdict 行 verify 形——`subtype` 由
# `transport` 注入）
_VERDICT_FRAME_KEYS = {"subtype", "supported", "rewritten", "split", "cited", "attribution"}
# `notice` 帧恰三键（真源 `specs/transport.md` 行为 7）
_NOTICE_FRAME_KEYS = {"type", "gates", "content"}
# 行 15／16 的 step payload 必在场六计数键（「不降级与静默禁令」节逐字）
_SIGNAL_PAYLOAD_KEYS = {
    PAYLOAD_SUPPORTED_KEY,
    PAYLOAD_REWRITTEN_KEY,
    PAYLOAD_SPLIT_KEY,
    PAYLOAD_CITED_KEY,
    PAYLOAD_DELIVERED_ROWS_KEY,
    PAYLOAD_OBS_ROWS_KEY,
}


def _obs(
    index: int,
    kind: str,
    *,
    content: str = "日产油量 21.16 吨",
    source: str = "台账",
    report: str = "",
) -> dict[str, Any]:
    """观察 fixture（材料面字段形：`index`／`locator.kind`／`content`／出处）。"""
    locator: dict[str, Any] = {"kind": kind}
    if report:
        locator["report"] = report
    return {
        "index": index,
        "locator": locator,
        "content": content,
        "source": source,
        "source_id": f"obs-{index}",
    }


def _state(
    *, question: str = "渤中34-8 油田 2026 年日产油量是多少？", draft: str, **over: Any
) -> RunState:
    values: dict[str, Any] = {
        "run_id": "run-ver-01",
        "question": question,
        "actor": "laowang",
        "draft": draft,
    }
    values.update(over)
    return RunState(**values)


async def _frames(bus: EventBus) -> list[SseEvent]:
    """读尽一条已收束总线的帧（先 `close`——未收束会等待新帧）。"""
    bus.close()
    return [frame async for frame in bus.stream(0)]


def _of(frames: list[SseEvent], event: str) -> list[dict[str, Any]]:
    return [frame.data for frame in frames if frame.event == event]


def _step_payload(state: RunState) -> dict[str, Any]:
    """本块步记录 payload（相位标记＝`verify`——本块恰一条步）。"""
    payloads = [
        dict(step["payload"])
        for step in state.steps
        if isinstance(step.get("payload"), Mapping)
        and step["payload"].get("phase") == PHASE
    ]
    assert len(payloads) == 1, f"核验步记录不唯一：{payloads}"
    return payloads[0]


def _notice_types(state: RunState) -> list[str]:
    return [str(entry.get("type")) for entry in state.notices]


# ---------- 行 1：逐行核验（多句答案逐句判定，非整段判） ----------


async def test_per_line_check() -> None:
    """行 1｜逐行核验——多句答案**逐句**判定，非整段判（行为 1）。"""
    observations = [
        _obs(1, "ledger", content="渤中34-8 油田 2026 年日产油量 21.16 吨"),
        _obs(2, "ledger", content="渤中34-8 油田 2026 年日产液量 8824.4 方"),
    ]
    supported_line = "渤中34-8 油田 2026 年日产油量 21.16 吨[1]。"
    other_supported = "渤中34-8 油田 2026 年日产液量 8824.4 方[2]。"
    unsupported_line = "渤中34-8 油田 2026 年日产油量 30 吨[1]。"
    state = _state(
        draft="\n".join(["一、产量概况", supported_line, unsupported_line, other_supported]),
        observations=observations,
    )
    bus = EventBus()
    verdict = verify(state, bus=bus)
    frames = await _frames(bus)

    # 逐句判定：两句有据、一句无据——整段判会把三句一起吞掉
    assert verdict.supported == 2
    assert verdict.rewritten == 1
    assert verdict.cited == [1, 2]
    lines = state.draft.splitlines()
    assert lines[0] == "一、产量概况"  # 结构承载行原样
    assert lines[1] == supported_line  # 有据行逐字不变（未盖前缀）
    assert lines[2] == REWRITE_PREFIX + unsupported_line  # 无据行：整行盖章
    assert lines[3] == other_supported
    assert _of(frames, EVENT_VERDICT)[0][PAYLOAD_SUPPORTED_KEY] == 2


# ---------- 行 2：数值未在断言里复述 → 判无据并改写 ----------


async def test_cited_value_must_be_restated() -> None:
    """行 2｜数值未在断言里复述 → 判无据并改写（行为 2；钉 pin-02 落点）。"""
    observations = [
        _obs(1, "ledger", content="日产油量 21.16 吨"),
        _obs(2, "agg_row", content="井号=N-01；日期=2026-01-01；日产油量（吨）=21.16"),
    ]
    not_restated = "该井日产油量见材料[1]。"            # 引了一个数、断言里零复述 → 无据
    restated = "N-01 井 2026-01-01 日产油量 21.16 吨[2]。"
    carrier_exempt = "N-01 井有产量记录[2]。"            # 承载豁免：任一数值重叠即支撑
    state = _state(
        draft="\n".join([not_restated, restated, carrier_exempt]),
        observations=observations,
    )
    verdict = verify(state, bus=EventBus())

    assert verdict.rewritten == 1
    assert verdict.supported == 2
    lines = state.draft.splitlines()
    assert lines[0] == REWRITE_PREFIX + not_restated  # 未复述 → 改写
    assert lines[1] == restated
    assert lines[2] == carrier_exempt  # `agg_row` 承载豁免（任一数值重叠即支撑）
    assert CARRIER_KINDS == {"agg_row", "lineage", "fragment"}  # 承载豁免域（真源 R-A2-11）


# ---------- 行 3：无据句改写成「未找到」＋ notice 在场 ----------


async def test_unsupported_rewritten_with_notice() -> None:
    """行 3｜无据句改写成「未找到」＋ notice 在场（行为 3；钉 pin-02／pin-11 落点）。"""
    observations = [_obs(1, "ledger", content="日产油量 21.16 吨")]
    supported_line = "该井日产油量为 21.16 吨[1]。"
    unsupported_line = "该井日产油量为 99.5 吨[1]。"
    state = _state(draft="\n".join([supported_line, unsupported_line]), observations=observations)
    bus = EventBus()
    verdict = verify(state, bus=bus)
    frames = await _frames(bus)

    lines = state.draft.splitlines()
    # INV-1（钉 pin-11）：前缀只挂无据行——有据行不粘前缀
    assert lines[0] == supported_line
    assert lines[1] == REWRITE_PREFIX + unsupported_line
    assert supported_line not in lines[1]

    # notice 在场（状态写口 ＋ `notice` 帧恰三键）
    assert NOTICE_UNSUPPORTED_CLAIM in _notice_types(state)
    notice_frames = _of(frames, EVENT_NOTICE)
    assert notice_frames
    assert all(set(frame) == _NOTICE_FRAME_KEYS for frame in notice_frames)
    assert NOTICE_UNSUPPORTED_CLAIM in [frame["type"] for frame in notice_frames]

    # 改写不得静默：原句与原因留痕（`RewriteRecord` → step payload）
    rewrites = _step_payload(state)[PAYLOAD_REWRITES_KEY]
    assert {entry["line"] for entry in rewrites} == {unsupported_line}
    assert {entry["reason"] for entry in rewrites} == {REWRITE_NO_MATERIAL}
    assert verdict.ok is False  # 仍有「无据断言」残留 → 回炉位（行为 9）


# ---------- 行 4：矛盾来源分列、各带出处、不调和 ----------


async def test_conflict_split_not_merged() -> None:
    """行 4｜矛盾来源分列、各带出处、不调和（行为 4）。"""
    observations = [
        _obs(1, "ledger", content="日产油量：21 吨/日", source="口径卡A"),
        _obs(2, "ledger", content="日产油量：8824.4 方/日", source="口径卡B"),
    ]
    draft = "该油田日产油量有 21 吨/日[1]、也有 8824.4 方/日[2]。"
    state = _state(draft=draft, observations=observations)
    bus = EventBus()
    verdict = verify(state, bus=bus)
    frames = await _frames(bus)

    # 两源逐支带出处（不强调和、不取其一）——原断言行不删、分列块追加
    assert verdict.split == 1
    assert draft in state.draft
    assert "多来源不一致——分源列明（禁止无出处调和）：" in state.draft
    assert "[1] 口径卡A：日产油量：21 吨/日" in state.draft
    assert "[2] 口径卡B：日产油量：8824.4 方/日" in state.draft
    assert NOTICE_CONTRADICTION_SPLIT in _notice_types(state)
    assert NOTICE_CONTRADICTION_SPLIT in [frame["type"] for frame in _of(frames, EVENT_NOTICE)]
    # 矛盾改写也留痕（reason＝`conflict`——闭世界另一值）
    rewrites = _step_payload(state)[PAYLOAD_REWRITES_KEY]
    assert {entry["reason"] for entry in rewrites} == {REWRITE_CONFLICT}
    assert _step_payload(state)[PAYLOAD_SPLIT_KEY] == 1
    # 分列不改写行、不计无据改写数（两个维度不强行映射——行为 9 的 `ok` 只看无据残留）
    assert verdict.rewritten == 0
    assert verdict.ok is True


# ---------- 行 5：归属对不上 → attribution=False ＋ 缺口（钉 pin-01） ----------


async def test_attribution_mismatch() -> None:
    """行 5｜归属对不上 → `attribution=False` ＋ 缺口（行为 5；钉 pin-01 落点）。"""
    observations = [
        _obs(
            1,
            "fragment",
            content="1.2 井身结构（实钻）：生产套管下深 2462.0 米",
            source="《A-W11井完井工程报告》",
            report="《A-W11井完井工程报告》",
        ),
        _obs(
            2,
            "fragment",
            content="1.2 井身结构（实钻）：生产套管下深 2680.4 米",
            source="《Y-21井完井工程报告》",
            report="《Y-21井完井工程报告》",
        ),
    ]
    draft = "W-11 井生产套管下深 2680.4 米[2]。"  # 题干点名 W-11、消费的是 Y-21 的源
    state = _state(question=_WELL_QUESTION, draft=draft, observations=observations)
    bus = EventBus()
    verdict = verify(state, bus=bus)
    frames = await _frames(bus)

    assert verdict.attribution is False
    assert verdict.rewritten == 0  # 归属审不改写行、不计改写数（数值支撑判定语义不变）
    # 该情形写进缺口（核验侧只产 `kind="unverified"`）
    assert verdict.gaps
    assert {gap.kind for gap in verdict.gaps} == {GAP_UNVERIFIED}
    assert gap_reason_of(state).strip()
    # 机读信号：notice ＋ 答案面分源列明块（两源各带出处）
    assert NOTICE_ATTRIBUTION_SPLIT in _notice_types(state)
    assert NOTICE_ATTRIBUTION_SPLIT in [frame["type"] for frame in _of(frames, EVENT_NOTICE)]
    assert "跨源归属审——分源列明" in state.draft
    assert "《A-W11井完井工程报告》" in state.draft
    assert "《Y-21井完井工程报告》" in state.draft


def gap_reason_of(state: RunState) -> str:
    """判定卡缺口理由（`state.verdict` 投影面读取——不在场即判失败）。"""
    verdict = state.verdict
    assert isinstance(verdict, Mapping)
    gaps = verdict.get("gaps")
    assert isinstance(gaps, list) and gaps
    return " ".join(str(gap.get("reason", "")) for gap in gaps)


# ---------- 行 6：`Verdict` 各字段齐备；缺字段判失败 ----------


async def test_verdict_all_keys() -> None:
    """行 6｜`Verdict` 各字段齐备；缺字段判失败（行为 6）。"""
    expected = [
        "supported",
        "rewritten",
        "split",
        "cited",
        "delivered_rows",
        "obs_rows",
        "attribution",
        "ok",
        "gaps",
    ]
    assert [field.name for field in dataclasses.fields(Verdict)] == expected
    # 缺键＝判失败：九键无一带缺省（构造缺键即 TypeError）
    assert all(
        field.default is dataclasses.MISSING
        and field.default_factory is dataclasses.MISSING
        for field in dataclasses.fields(Verdict)
    )
    with pytest.raises(TypeError):
        Verdict(  # type: ignore[call-arg]
            supported=0,
            rewritten=0,
            split=0,
            cited=[],
            delivered_rows=0,
            obs_rows=0,
            attribution=True,
            ok=True,
        )

    state = _state(draft="一、概况", observations=[])
    verdict = verify(state, bus=EventBus())
    assert [field.name for field in dataclasses.fields(verdict)] == expected
    assert isinstance(state.verdict, Mapping)
    assert sorted(state.verdict) == sorted(expected)


# ---------- 行 7：边界记号化：`52` 不命中 `1520` ----------


async def test_token_boundary_no_substring_false_positive() -> None:
    """行 7｜边界记号化：`52` 不命中 `1520`（行为 7）。"""
    observations = [_obs(1, "ledger", content="日产油量 52 吨")]
    false_positive = "该井累计产量 1520 吨[1]。"   # 观察 52 不得因「1520 含 52」判有据
    state = _state(draft=false_positive, observations=observations)
    verdict = verify(state, bus=EventBus())
    assert verdict.rewritten == 1
    assert state.draft == REWRITE_PREFIX + false_positive

    true_positive = "该井日产油量 52 吨[1]。"
    other = _state(draft=true_positive, observations=observations)
    other_verdict = verify(other, bus=EventBus())
    assert other_verdict.rewritten == 0
    assert other_verdict.cited == [1]
    assert other.draft == true_positive


# ---------- 行 8：全角／半角标点先归一后切分 ----------


async def test_fullwidth_normalized_before_split() -> None:
    """行 8｜全角／半角标点先归一后切分（行为 7）。"""
    observations = [_obs(1, "ledger", content="日产油量 21.16 吨")]
    draft = "该井日产油量为２１．１６吨［１］。"  # 全角数字／小数点／引标括号
    state = _state(draft=draft, observations=observations)
    verdict = verify(state, bus=EventBus())

    assert verdict.rewritten == 0
    assert verdict.supported == 1
    assert verdict.cited == [1]      # 全角引标归一半角后可解析（先归一后切分）
    assert state.draft == draft      # 输出面保留原句逐字（归一只在判定面）


# ---------- 行 9：零数值断言不自动判过（钉 pin-10 落点） ----------


async def test_no_number_assertion_not_auto_pass() -> None:
    """行 9｜零数值断言不自动判过（行为 8；钉 pin-10 落点）。"""
    observations = [
        _obs(1, "ledger", content="日产油量 21.16 吨"),
        _obs(2, "ledger", content="该井为探井"),
    ]
    structural_line = "一、当日概况"
    zero_number_unsupported = "该井日产油量为二十一点一六吨[1]。"  # 零数值：不得自动判过
    zero_number_supported = "该井为探井[2]。"                       # 有可解析引标支撑
    state = _state(
        draft="\n".join([structural_line, zero_number_unsupported, zero_number_supported]),
        observations=observations,
    )
    verdict = verify(state, bus=EventBus())

    # 零数值断言不恒过：被引观察的数值未复述 → 计入无据；结构行不得自动判过（不计有支撑数）
    assert verdict.supported == 1
    assert verdict.rewritten == 1
    assert verdict.cited == [2]
    lines = state.draft.splitlines()
    assert lines[0] == structural_line
    assert lines[1] == REWRITE_PREFIX + zero_number_unsupported
    assert lines[2] == zero_number_supported

    # pin-10：不得 `cited=[]` 且数字在场——无引标数字行不得以断言形放行
    numeric_no_cite = "该井日产油量 1520 吨。"
    other = _state(draft=numeric_no_cite, observations=observations)
    other_verdict = verify(other, bus=EventBus())
    assert other_verdict.rewritten == 1
    assert other_verdict.cited == []
    for line in other.draft.splitlines():
        if any(char.isdigit() for char in line):
            assert line.startswith(REWRITE_PREFIX)  # 数字在场必为盖章行，不作断言


# ---------- 行 15：机读信号在场（verdict／notice ＋ step payload） ----------


async def test_verification_signal_present() -> None:
    """行 15｜机读信号在场（verdict／notice ＋ step payload）（「不降级与静默禁令」节）。"""
    observations = [_obs(1, "ledger", content="日产油量 21.16 吨")]
    state = _state(draft="该井日产油量为 99.5 吨[1]。", observations=observations)
    bus = EventBus()
    verdict = verify(state, bus=bus)
    frames = await _frames(bus)

    verdict_frames = _of(frames, EVENT_VERDICT)
    assert len(verdict_frames) == 1
    assert set(verdict_frames[0]) == _VERDICT_FRAME_KEYS  # `subtype` 由 transport 注入
    assert verdict_frames[0]["subtype"] == "verify"
    assert verdict_frames[0]["rewritten"] == verdict.rewritten

    notice_frames = _of(frames, EVENT_NOTICE)
    assert notice_frames and all(set(frame) == _NOTICE_FRAME_KEYS for frame in notice_frames)

    payload = _step_payload(state)
    assert _SIGNAL_PAYLOAD_KEYS <= set(payload)
    assert payload[PAYLOAD_SUPPORTED_KEY] == verdict.supported
    assert payload[PAYLOAD_REWRITTEN_KEY] == verdict.rewritten
    assert payload[PAYLOAD_SPLIT_KEY] == verdict.split
    assert payload[PAYLOAD_CITED_KEY] == list(verdict.cited)
    assert payload[PAYLOAD_GAPS_KEY]  # 缺口随步落账（kind="unverified"）
    assert payload[PAYLOAD_REWRITES_KEY]
    assert payload[PAYLOAD_ATTRIBUTION_KEY] is verdict.attribution
    assert payload[PAYLOAD_OK_KEY] is verdict.ok
    # 通知落账与帧面同批（改写／分列／归属失败都必产信号）
    assert NOTICE_UNSUPPORTED_CLAIM in _notice_types(state)


# ---------- 行 16：行集对账（钉 pin-12 落点） ----------


async def test_row_reconciliation_bookkeeping() -> None:
    """行 16｜行集对账：两字段入 `Verdict` 与 step payload；差额>0 且无行集声明 → 补如实注记。"""
    observations = [
        _obs(1, "agg_row", content="井号=N-01；日期=2026-01-01；日产油量（吨）=21.16"),
        _obs(2, "agg_row", content="井号=N-02；日期=2026-01-01；日产油量（吨）=18.4"),
        _obs(3, "ledger", content="日产油量 21.16 吨"),
    ]
    # ① 已交付一行在窗数据行：有行集声明 → 无注记
    delivered = _state(draft="N-01 井 2026-01-01 日产油量 21.16 吨[1]。", observations=observations)
    verdict = verify(delivered, bus=EventBus())
    assert ROWSET_OBSERVATION_KINDS == {"agg_row"}
    assert verdict.obs_rows == 2
    assert verdict.delivered_rows == 1
    payload = _step_payload(delivered)
    assert payload[PAYLOAD_OBS_ROWS_KEY] == 2
    assert payload[PAYLOAD_DELIVERED_ROWS_KEY] == 1
    assert payload[PAYLOAD_ROW_NOTE_KEY] is None

    # ② 一行在窗数据行都没交付（答案面无行集声明）→ 补如实注记；不改写、不拦截
    answer = "检索片段记载日产油量 21.16 吨[3]。"
    silent = _state(draft=answer, observations=observations)
    silent_verdict = verify(silent, bus=EventBus())
    assert silent_verdict.obs_rows == 2
    assert silent_verdict.delivered_rows == 0
    assert silent_verdict.rewritten == 0  # 不改写数值断言
    assert silent_verdict.ok is True      # 不拦截（记账面、非拦截阀门）
    assert silent.draft == answer
    note = _step_payload(silent)[PAYLOAD_ROW_NOTE_KEY]
    assert isinstance(note, str) and "2" in note and "0" in note


# ---------- 本票自有面一：卡面签名与三形状齐 ----------


async def test_card_signature_and_three_shapes() -> None:
    """骨架与公开面按卡面签名（`verify(state) -> Verdict`）＋三形状齐（规格 :32–:51）。"""
    signature = inspect.signature(verify)
    parameters = list(signature.parameters.values())
    assert [parameter.name for parameter in parameters] == ["state", "bus"]
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[1].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.return_annotation in (Verdict, "Verdict")

    assert len(verification.__all__) == len(set(verification.__all__))  # 公开面无重复
    for name in ("Verdict", "RewriteRecord", "Gap", "verify"):
        assert name in verification.__all__
        assert getattr(verification, name) is not None

    # 两处闭世界：`RewriteRecord.reason`／`Gap.kind` 越界即判失败
    with pytest.raises(ValueError):
        RewriteRecord(line="该井产量 1 吨", reason="other")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        Gap(kind="bad", subtask_id=None, reason="越界")  # type: ignore[arg-type]
    assert GAP_KINDS == {"refused", "missing", "unverified"}
    assert GAP_UNVERIFIED == "unverified"

    # 单一判定卡出口：`Verdict` 不吞键、被 verifier 恒返九键
    state = _state(draft="", observations=[])
    assert isinstance(verify(state, bus=EventBus()), Verdict)


# ---------- 本票自有面二：零模型面（import 契约） ----------


async def test_public_face_and_zero_model_import_contract() -> None:
    """零模型面：本块不引 `gateway_adapter`（R8）／不引 `appv2.infra.llm_client`（R7）
    ／不引框架。"""
    sources = sorted(_VERIFICATION_DIR.glob("*.py"))
    assert sources
    modules: set[str] = set()
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
    assert not any(name.startswith("appv2.runtimev2.gateway_adapter") for name in modules)
    assert not any(name.startswith("appv2.infra.llm_client") for name in modules)
    assert not any(
        name.split(".")[0] in {"langgraph", "langchain", "langchain_core"} for name in modules
    )
    # 写口面只经包根（R2：禁深层子模块）
    assert not any(
        name.startswith("appv2.runtimev2.bookkeeping.") for name in modules
    ), sorted(modules)
    assert ATTRIBUTION_CARRIER_KINDS == {"fragment", "graph"}
