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
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

import appv2.runtimev2.verification as verification
from appv2.runtimev2.answering import CONTRADICTION_SECTION_HEAD
from appv2.runtimev2.state import RunState
from appv2.runtimev2.transport import (
    SUPPLEMENT_BLOCK_ATTRIBUTION,
    SUPPLEMENT_BLOCK_LINEAGE,
    SUPPLEMENT_BLOCK_SPLIT,
    EventBus,
    SseEvent,
)
from appv2.runtimev2.verification import (
    ATTRIBUTION_CARRIER_KINDS,
    CALIBER_KINDS,
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
    PAYLOAD_FIELD_MISMATCH_KEY,
    PAYLOAD_GAPS_KEY,
    PAYLOAD_INTENDED_REWRITES_KEY,
    PAYLOAD_OBS_ROWS_KEY,
    PAYLOAD_OK_KEY,
    PAYLOAD_REWRITES_KEY,
    PAYLOAD_REWRITTEN_KEY,
    PAYLOAD_ROW_NOTE_KEY,
    PAYLOAD_ROWSET_ALIGNED_KEY,
    PAYLOAD_ROWSET_MISSING_KEY,
    PAYLOAD_SPLIT_KEY,
    PAYLOAD_SUPPORTED_KEY,
    PAYLOAD_VERIFY_MODE_KEY,
    PAYLOAD_ZERO_DELIVERY_KEY,
    PHASE,
    REWRITE_CONFLICT,
    REWRITE_NO_MATERIAL,
    ROWSET_OBSERVATION_KINDS,
    VERIFY_ACTION_ENV,
    VERIFY_MODE_DEFAULT,
    VERIFY_MODE_DELETE,
    VERIFY_MODE_OBSERVE,
    VERIFY_MODE_OFF,
    VERIFY_MODE_REPAIR,
    VERIFY_MODE_REPAIR_FALLBACK,
    VERIFY_MODES,
    ZERO_DELIVERY_NOTICE,
    Gap,
    RewriteRecord,
    Verdict,
    verify,
)
from appv2.runtimev2.verification import rules as verification_rules

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


def _supplement_texts(supplements: list[dict[str, Any]], block: str) -> list[str]:
    """增补面条目文本列（按块型筛——`{block, text}` 载荷形，2026-10-17 EB3 D2）。"""
    return [
        str(entry.get("text", ""))
        for entry in supplements
        if entry.get("block") == block
    ]


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
    # 无据行**整行离场**（2026-10-17 EB3 D3：删句不贴前缀）——有据行与结构行逐字不变
    assert lines == ["一、产量概况", supported_line, other_supported]
    assert unsupported_line not in state.draft
    assert _of(frames, EVENT_VERDICT)[0][PAYLOAD_SUPPORTED_KEY] == 2


# ---------- 行 2：数值未在断言里复述 → 判无据并改写 ----------


async def test_cited_value_must_be_restated() -> None:
    """行 2｜数值未在断言里复述 → 判无据并**删句**（行为 2；钉 pin-02 落点；EB3 D3）。

    **2026-10-17 F1 件一注记**：本用例 fixture 随「数值断言只认计量数值」判据同批修正——旧 fixture
    的承载豁免行「N-01 井有产量记录[2]。」是靠**标识符／日期数字**（`N-01`→`01` 命中观察里
    `2026-01-01` 的 `01`）偶然重叠放行的，正是件一（`rules.number_tokens`）要修的假阳；现改以真量值
    重叠（`21.16 吨`）判承载豁免——判据面语义（承载任一数值重叠即支撑）零改。
    """
    observations = [
        _obs(1, "ledger", content="日产油量 21.16 吨"),
        _obs(
            2,
            "agg_row",
            content="井号=N-01；日期=2026-01-01；日产油量（吨）=21.16；日产液量（方）=8824.4",
        ),
    ]
    not_restated = "该井日产油量见材料[1]。"            # 引了一个数、断言里零复述 → 无据
    restated = "N-01 井 2026-01-01 日产油量 21.16 吨[2]。"
    carrier_exempt = "N-01 井有 21.16 吨的产量记录[2]。"  # 承载豁免：任一数值重叠即支撑
    state = _state(
        draft="\n".join([not_restated, restated, carrier_exempt]),
        observations=observations,
    )
    verdict = verify(state, bus=EventBus())

    assert verdict.rewritten == 1
    assert verdict.supported == 2
    lines = state.draft.splitlines()
    assert lines == [restated, carrier_exempt]  # 无据行整行离场（不贴前缀）
    assert not_restated not in state.draft
    assert CARRIER_KINDS == {"agg_row", "lineage", "fragment"}  # 承载豁免域（真源 R-A2-11）


# ---------- 行 3：无据句改写成「未找到」＋ notice 在场 ----------


async def test_unsupported_rewritten_with_notice() -> None:
    """行 3｜无据句**删句**＋ notice 在场（行为 3；钉 pin-02 落点；EB3 D3）。"""
    observations = [_obs(1, "ledger", content="日产油量 21.16 吨")]
    supported_line = "该井日产油量为 21.16 吨[1]。"
    unsupported_line = "该井日产油量为 99.5 吨[1]。"
    state = _state(draft="\n".join([supported_line, unsupported_line]), observations=observations)
    bus = EventBus()
    verdict = verify(state, bus=bus)
    frames = await _frames(bus)

    lines = state.draft.splitlines()
    # EB3 D3：真无据断言删句（不贴前缀、不留残句）——有据行逐字不变
    assert lines == [supported_line]
    assert unsupported_line not in state.draft
    assert "未找到（材料未披露）" not in state.draft

    # notice 在场（状态写口 ＋ `notice` 帧恰三键）
    assert NOTICE_UNSUPPORTED_CLAIM in _notice_types(state)
    notice_frames = _of(frames, EVENT_NOTICE)
    assert notice_frames
    assert all(set(frame) == _NOTICE_FRAME_KEYS for frame in notice_frames)
    assert NOTICE_UNSUPPORTED_CLAIM in [frame["type"] for frame in notice_frames]

    # 改写不得静默：原句与原因留痕（`RewriteRecord` → step payload）＋ verdict 计数如实
    rewrites = _step_payload(state)[PAYLOAD_REWRITES_KEY]
    assert {entry["line"] for entry in rewrites} == {unsupported_line}
    assert {entry["reason"] for entry in rewrites} == {REWRITE_NO_MATERIAL}
    assert verdict.rewritten == 1
    assert _of(frames, EVENT_VERDICT)[0][PAYLOAD_REWRITTEN_KEY] == 1
    assert verdict.ok is False  # 仍有「无据断言」残留 → 回炉位（行为 9）


# ---------- 行 4：矛盾来源分列、各带出处、不调和 ----------


async def test_conflict_split_not_merged() -> None:
    """行 4｜矛盾来源分列、各带出处、不调和（行为 4；EB3 D2：块入增补面不进正文）。"""
    observations = [
        _obs(1, "ledger", content="日产油量：21 吨/日", source="口径卡A"),
        _obs(2, "ledger", content="日产油量：8824.4 方/日", source="口径卡B"),
    ]
    draft = "该油田日产油量有 21 吨/日[1]、也有 8824.4 方/日[2]。"
    state = _state(draft=draft, observations=observations)
    bus = EventBus()
    supplements: list[dict[str, Any]] = []
    verdict = verify(state, bus=bus, supplements=supplements)
    frames = await _frames(bus)

    # 两源逐支带出处（不强调和、不取其一）——原断言行保留、分列块**入增补面不进正文**
    assert verdict.split == 1
    assert state.draft == draft  # 正文＝模型稿逐字（分列块不再写进 draft）
    texts = _supplement_texts(supplements, SUPPLEMENT_BLOCK_SPLIT)
    assert len(texts) == 1
    block = texts[0]
    assert "各来源说法如下，按来源分别列出：" in block  # 2026-10-17 EB2 D3 段头去工程腔
    # 收口段（answering）的「互不一致」分源块同话术（「互不一致」标＝`specs/answering.md`
    # 行为 6 要求，保留在前——两相位 R1 禁互引，故两侧各落字面，此处钉同句不漂移）。
    assert CONTRADICTION_SECTION_HEAD.strip().endswith("各来源说法如下，按来源分别列出：")
    assert "[1] 口径卡A：日产油量：21 吨/日" in block
    assert "[2] 口径卡B：日产油量：8824.4 方/日" in block
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
    """行 5｜归属对不上 → `attribution=False` ＋ 缺口（行为 5；钉 pin-01 落点；块入增补面）。"""
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
    supplements: list[dict[str, Any]] = []
    verdict = verify(state, bus=bus, supplements=supplements)
    frames = await _frames(bus)

    assert verdict.attribution is False
    assert verdict.rewritten == 0  # 归属审不改写行、不计改写数（数值支撑判定语义不变）
    # 该情形写进缺口（核验侧只产 `kind="unverified"`）
    assert verdict.gaps
    assert {gap.kind for gap in verdict.gaps} == {GAP_UNVERIFIED}
    assert gap_reason_of(state).strip()
    # 机读信号：notice ＋ 增补面归属块（两源各带出处）
    assert NOTICE_ATTRIBUTION_SPLIT in _notice_types(state)
    assert NOTICE_ATTRIBUTION_SPLIT in [frame["type"] for frame in _of(frames, EVENT_NOTICE)]
    texts = _supplement_texts(supplements, SUPPLEMENT_BLOCK_ATTRIBUTION)
    assert len(texts) == 1
    block = texts[0]
    assert "按来源归属如下（题眼：" in block  # 2026-10-17 EB2 D3 段头去工程腔
    assert "《A-W11井完井工程报告》" in block
    assert "《Y-21井完井工程报告》" in block
    assert state.draft == draft  # 归属块不进正文（EB3 D2）


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
    assert state.draft == ""  # 无据整行离场（EB3 D3 删句）

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

    # 零数值断言不恒过：被引观察的数值未复述 → 计入无据（删句）；结构行不得自动判过（不计有支撑数）
    assert verdict.supported == 1
    assert verdict.rewritten == 1
    assert verdict.cited == [2]
    lines = state.draft.splitlines()
    assert lines == [structural_line, zero_number_supported]  # 无据行离场、其余逐字不变
    assert zero_number_unsupported not in state.draft

    # pin-10：不得 `cited=[]` 且数字在场——无引标数字行不得以断言形放行（照删）
    numeric_no_cite = "该井日产油量 1520 吨。"
    other = _state(draft=numeric_no_cite, observations=observations)
    other_verdict = verify(other, bus=EventBus())
    assert other_verdict.rewritten == 1
    assert other_verdict.cited == []
    assert other.draft == ""  # 数字在场的无据行整行离场（不留残句）


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
    # 2026-10-17 EB5c 扩面：机读对账两面**恒在场**（与注记面的三态解耦）
    assert payload[PAYLOAD_ROWSET_MISSING_KEY] == [2]
    assert payload[PAYLOAD_ROWSET_ALIGNED_KEY] is True

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
    # 注记携两面（缺行序号列 ＋ 引标序对齐）——一条事实的注记面与机读面同源
    assert "[1]、[2]" in note and "对齐" in note
    silent_payload = _step_payload(silent)
    assert silent_payload[PAYLOAD_ROWSET_MISSING_KEY] == [1, 2]
    assert silent_payload[PAYLOAD_ROWSET_ALIGNED_KEY] is True


async def test_rowset_audit_l0422_offset_caught() -> None:
    """2026-10-17 EB5c｜L04-22 形行数对账：自述声明盖不住的两面——缺行 ＋ 引标 off-by-one。

    真机病灶（`eval/results/frames/EB3G-L04-22.json`，run-0fb0b64b）：引擎 86 行齐在窗（无截断
    披露），答案自述「以上共 86 口井已返回」却只渲染 84 行——第 24／46 号行未交付，且模型自编
    行号整体错位一格（标签 25 引 `[24]`）。自述声明为真为假只能由对账事实判：故**机读对账两面
    恒落账**（`rowset_missing`＝缺行序号列、`rowset_aligned`＝引标序对齐），注记面三态不变
    （有声明→零注记），**正文逐字不变、不拦截、不产通知**（Owner 裁决②：对账只作诚实记账面）。
    """
    obs = [
        _obs(index, "agg_row", content=f"井号=井{index}；日产油量（吨）=1.{index}")
        for index in range(1, 8)
    ]
    # 引擎 7 行；答案交付第 1、2、4、5、6、7 号（缺第 3 号）且引标跳号——模型自编行号「3.」引 [4]
    draft = "\n".join(
        [
            "以上共 7 口井已返回（自述声明在场）：",
            "1. 井1 —— 1.1 [1]",
            "2. 井2 —— 1.2 [2]",
            "3. 井4 —— 1.4 [4]",
            "4. 井5 —— 1.5 [5]",
            "5. 井6 —— 1.6 [6]",
            "6. 井7 —— 1.7 [7]",
        ]
    )
    state = _state(question="去年日产油量排名前 7 的井是哪些？", draft=draft, observations=obs)
    bus = EventBus()
    verdict = verify(state, bus=bus)

    assert (verdict.obs_rows, verdict.delivered_rows) == (7, 6)  # 差额 1 行
    assert verdict.ok is True  # 不拦截（记账面）
    assert state.draft == draft  # 正文逐字不变（不改写、不重试）
    payload = _step_payload(state)
    # 缺行逐号可复算（渲染行数≠引擎行数的面）
    assert payload[PAYLOAD_ROWSET_MISSING_KEY] == [3]
    # 引标序错位（跳号＝off-by-one：模型自编行号与引擎行号不一致）
    assert payload[PAYLOAD_ROWSET_ALIGNED_KEY] is False
    # 答案自述声明在场 → 注记面三态：零注记（附 D 钉；对账事实仍由机读两面落账）
    assert payload[PAYLOAD_ROW_NOTE_KEY] is None
    frames = await _frames(bus)
    assert not _of(frames, EVENT_NOTICE)  # 不产通知（不降级为拦截面）
    assert _of(frames, EVENT_VERDICT)


# ---------- 本票自有面一：卡面签名与三形状齐 ----------


async def test_card_signature_and_three_shapes() -> None:
    """骨架与公开面按卡面签名（`verify(state) -> Verdict`）＋三形状齐（规格 :32–:51）。"""
    signature = inspect.signature(verify)
    parameters = list(signature.parameters.values())
    # EB3 D2：增补面收集列表 `supplements` 为选给注入面（第三参，kw-only）
    assert [parameter.name for parameter in parameters] == ["state", "bus", "supplements"]
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters[1:]
    )
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


# ══════════ -B 票（RT-W4-07b-verification.md）：红线与健壮性簇＋边界·保留集 ══════════
#
# 票面对象＝`specs/verification.md`「验收测试」表第 10–14、17、18 行（`#` 行序与 -A 票共用、不重编；
# 测试标识与规格列逐字一致）。三形状仍以 -A 落地的为唯一真源——本票只补行为断言，不改形状。
#
# - 行 10 `::deterministic_repeatable`：同输入两次运行 `Verdict` 五计数与 `ok` 完全一致；
# - 行 11 `::rewrite_reason_closed_world`：`RewriteRecord.reason` 越界取值 → 判失败；
# - 行 12 `::verifier_error_fail_closed`：核验器抛错 → fail-closed 取 `ok=False`（不静默放行）；
# - 行 13 `::no_model_call_in_verification`：本模块零 LLM（AST＋import 双证）；
#   验收写法＝AST 机检（先例 `test_v2_four_phase.py:446`）＋「无旁路」断言；
# - 行 14 `::no_lexicon_or_regex_in_verification`：无词表／正则语义判断
#   （豁免面＝形态处理／集合成员判定）；
# - 行 17 `::boundary_single_zero_material_conflict_fullwidth`：【边界集】四形各落到对应分支；
# - 行 18 `::retention_clean_answer_unchanged`：【保留集】无矛盾、有支撑的普通答案：各字段取值与
#   `ok=True` 行为不变（与规格行为 9「`Verdict.ok=True` 时不得再改写」成对）。


# ---------- 行 10：确定性（同输入两次运行 verdict 完全一致） ----------


def _determinism_state() -> RunState:
    """确定性 fixture（构造两次即「同一输入」两次运行——行为 1／2／4 混合面）。"""
    observations = [
        _obs(1, "ledger", content="日产油量 21.16 吨"),
        _obs(2, "ledger", content="日产液量 8824.4 方"),
        _obs(3, "ledger", content="日产油量：21 吨/日", source="口径卡A"),
        _obs(4, "ledger", content="日产油量：8824.4 方/日", source="口径卡B"),
    ]
    draft = "\n".join(
        [
            "一、产量概况",
            "渤中34-8 油田 2026 年日产油量 21.16 吨[1]。",
            "渤中34-8 油田 2026 年日产液量 8824.4 方[2]。",
            "该油田日产油量有 21 吨/日[3]、也有 8824.4 方/日[4]。",
            "该井日产油量 99.9 吨[1]。",
        ]
    )
    return _state(
        question="渤中34-8 油田 2026 年日产油量与日产液量是多少？",
        draft=draft,
        observations=observations,
    )


async def test_deterministic_repeatable() -> None:
    """行 10｜同输入两次运行 `Verdict` 五计数与 `ok` 完全一致（零随机、零模型——行为 6 面）。"""
    first_state = _determinism_state()
    first_bus = EventBus()
    first = verify(first_state, bus=first_bus)
    second_state = _determinism_state()
    second_bus = EventBus()
    second = verify(second_state, bus=second_bus)

    counted = ("supported", "rewritten", "split", "cited", "attribution", "ok")
    assert [getattr(first, name) for name in counted] == [
        getattr(second, name) for name in counted
    ]
    # 五计数非全零空转（确定性断言非平凡：三个计数与引标集体在值）
    assert (first.supported, first.rewritten, first.split) == (3, 1, 1)
    assert first.cited == [1, 2, 3, 4]
    assert first.attribution is True and first.ok is False

    # 同输入两次运行：落地面亦逐字一致（答案面文本／判定卡投影／步 payload／帧流）
    assert first_state.draft == second_state.draft
    assert first_state.verdict == second_state.verdict
    assert _step_payload(first_state) == _step_payload(second_state)
    assert await _frames(first_bus) == await _frames(second_bus)


# ---------- 行 11：`RewriteRecord.reason` 越界取值 → 判失败 ----------


async def test_rewrite_reason_closed_world() -> None:
    """行 11｜`RewriteRecord.reason` 闭世界两值；越界取值 → 判失败
    （`specs/verification.md:54`）。
    """
    assert verification.REWRITE_REASONS == {REWRITE_NO_MATERIAL, REWRITE_CONFLICT}
    assert verification.REWRITE_REASONS == {"no_material", "conflict"}
    # 两值各合法
    for reason in (REWRITE_NO_MATERIAL, REWRITE_CONFLICT):
        assert RewriteRecord(line="该井日产油量 99.9 吨[1]。", reason=reason).reason == reason
    # 越界值判失败（fail-closed——不静默归一、不落账）
    for out_of_range in ("other", "", "NO_MATERIAL", "no_material ", "conflict_or_no_material"):
        with pytest.raises(ValueError):
            RewriteRecord(line="该井日产油量 99.9 吨[1]。", reason=out_of_range)  # type: ignore[arg-type]

    # verifier 自产面同样只落闭世界两值（产出点即把守——改写留痕不静默）
    state = _determinism_state()
    verdict = verify(state, bus=EventBus())
    reasons = {entry["reason"] for entry in _step_payload(state)[PAYLOAD_REWRITES_KEY]}
    assert reasons == {REWRITE_NO_MATERIAL, REWRITE_CONFLICT}
    assert reasons <= verification.REWRITE_REASONS
    assert (verdict.rewritten, verdict.split) == (1, 1)


# ---------- 行 12：核验器抛错 → fail-closed 取 `ok=False`（不静默放行） ----------


async def test_verifier_error_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """行 12｜核验器自身抛错 → **不判 `Verdict.ok=True`**（fail-closed）＋缺口（错误契约）。

    `specs/verification.md:58`：转 `Verdict.ok=False` ＋缺口，由 `orchestration` 承接；合法降级
    路径＝无（:85）——故「不静默放行」＝抛错必须落成 `ok=False` 的判定卡，不得返回放行卡、不得
    吞错逸出。两路注入：① 规则单点抛错（monkeypatch，核验器自身抛错）；② 观察形态缺键（输入形）。
    """
    import appv2.runtimev2.verification.core as verification_core

    observations = [_obs(1, "ledger", content="日产油量 21.16 吨")]
    draft = "该井日产油量 21.16 吨[1]。"

    # 对照跑：同形状输入正常收束 → ok=True（下行 fail-closed 由注入的抛错唯一牵出，非输入副作用）
    control_state = _state(draft=draft, observations=observations)
    control = verify(control_state, bus=EventBus())
    assert control.ok is True and control.rewritten == 0

    def _boom(*args: Any, **kwargs: Any) -> tuple[str, ...]:
        raise RuntimeError("核验器自身抛错（测试注入）")

    monkeypatch.setattr(verification_core, "question_anchors", _boom)  # 核验器内部首个调用面
    state = _state(draft=draft, observations=observations)
    verdict = verify(state, bus=EventBus())  # 不抛错逸出——错误契约把守在本块

    assert verdict.ok is False  # 不静默放行
    assert (verdict.supported, verdict.rewritten, verdict.split) == (0, 0, 0)
    assert verdict.cited == [] and verdict.attribution is False
    assert len(verdict.gaps) == 1 and verdict.gaps[0].kind == GAP_UNVERIFIED
    assert "fail-closed" in verdict.gaps[0].reason
    assert "RuntimeError" in verdict.gaps[0].reason  # 抛错如实留痕（不吞错）
    assert isinstance(state.verdict, Mapping) and state.verdict.get("ok") is False

    # 第二路（黑盒输入形）：观察缺 `index` → 核验器内部取键抛错，同走 fail-closed
    monkeypatch.undo()
    malformed = _state(
        draft=draft,
        observations=[{"locator": {"kind": "ledger"}, "content": "日产油量 21.16 吨"}],
    )
    malformed_verdict = verify(malformed, bus=EventBus())
    assert malformed_verdict.ok is False
    assert len(malformed_verdict.gaps) == 1
    assert "KeyError" in malformed_verdict.gaps[0].reason


# ---------- 行 13：本模块零 LLM（AST＋import 双证） ----------


_MODEL_CALL_FORMS = frozenset(
    {
        "complete",
        "acomplete",
        "completion",
        "create_completion",
        "ainvoke",
        "invoke",
        "agenerate",
        "generate",
        "chat",
        "embed",
        "aembed",
        "embeddings",
    }
)
_MODEL_CHANNEL_MODULES = (
    "appv2.runtimev2.gateway_adapter",  # R8（零 LLM 面：本块禁引）
    "appv2.infra.llm_client",  # R7（天然满足：本块不直引该出口）
)
_MODEL_CHANNEL_PACKAGES = ("litellm", "openai", "langchain", "langgraph", "dashscope")
_BYPASS_MODULES = ("importlib",)
_BYPASS_CALLS = frozenset({"__import__", "eval", "exec", "compile", "import_module"})


def _package_sources() -> list[Path]:
    """本块全部源码（AST 扫描面——两条红线共用的非空转判据）。"""
    sources = sorted(_VERIFICATION_DIR.glob("*.py"))
    assert len(sources) >= 5, f"扫描面可疑（文件数 {len(sources)}）"
    return sources


def _tree_of(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _call_names(tree: ast.Module) -> set[str]:
    """调用名集（裸名＋属性调用形同收——`complete(...)` 与 `client.complete(...)` 都不漏）。"""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
            elif isinstance(func, ast.Name):
                names.add(func.id)
    return names


def _imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _bypass_forms(tree: ast.Module) -> set[str]:
    """动态导入／执行旁路形（模型调用不得绕静态名字面走反射——「无旁路」断言）。"""
    found: set[str] = set()
    for name in _imported_modules(tree):
        if name.split(".")[0] in _BYPASS_MODULES:
            found.add(name.split(".")[0])
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in _BYPASS_CALLS:
                found.add(node.func.id)
            elif isinstance(node.func, ast.Attribute) and node.func.attr in _BYPASS_CALLS:
                found.add(node.func.attr)
    return found


def test_no_model_call_in_verification() -> None:
    """行 13｜本模块零 LLM（AST＋import 双证）。

    本块**不调模型、不存在模型调用发起面**（`specs/verification.md:64`）——不引
    `appv2.runtimev2.gateway_adapter`（**R8**）＋不直引 `appv2.infra.llm_client`（R7，天然满足）
    ＋不引框架（R5b）。验收写法＝AST 机检（先例 `tests/domains/test_v2_four_phase.py:446`：裸名＋
    属性调用形双查）＋「无旁路」断言（动态导入／反射形零出现——静态名字面已被双证封死）。
    """
    sources = _package_sources()
    imported: set[str] = set()
    for path in sources:
        tree = _tree_of(path)
        where = path.name
        # 双证①（AST）：模型调用形零出现
        calls = _call_names(tree)
        assert not calls & _MODEL_CALL_FORMS, (
            f"{where}: 出现模型调用形 {sorted(calls & _MODEL_CALL_FORMS)}"
        )
        # 双证②（import）：模型通道零直引（R8／R7／R5b 的源码面）
        modules = _imported_modules(tree)
        imported |= modules
        for name in modules:
            assert not name.startswith(_MODEL_CHANNEL_MODULES), f"{where}: 直引模型通道 {name}"
            assert name.split(".")[0] not in _MODEL_CHANNEL_PACKAGES, (
                f"{where}: 直引供应商 SDK {name}"
            )
        # 「无旁路」：动态导入／执行形零出现
        assert not _bypass_forms(tree), f"{where}: 动态导入旁路 {sorted(_bypass_forms(tree))}"

    # 扫描面非空转：本块确有自产面（写口面／帧面／题眼锚公开面在场）——零 LLM 非「空包」假绿
    assert {"appv2.runtimev2.bookkeeping", "appv2.runtimev2.transport", "appv2.tools"} <= imported
    # 探测器非空转：伪造树即被咬（裸名／属性调用形／直引通道／动态导入旁路）
    assert _call_names(ast.parse("completer.complete(msgs)\n")) & _MODEL_CALL_FORMS
    assert _call_names(ast.parse("complete(msgs)\n")) & _MODEL_CALL_FORMS
    assert "appv2.infra.llm_client" in _imported_modules(
        ast.parse("from appv2.infra.llm_client import embeddings\n")
    )
    assert _bypass_forms(
        ast.parse("import importlib\nimportlib.import_module('appv2.infra.llm_client')\n")
    )


# ---------- 行 14：程序侧无词表／正则语义判断（AST 扫描；豁免面＝形态处理／集合成员判定） ------


_CASE_FOLD_METHODS = frozenset({"lower", "upper", "casefold"})
_WORD_FACE_METHODS = frozenset({"startswith", "endswith", "split", "partition", "count"})
# 扫描面＝本块全部正则面（`re`）与**语义词表**两类；豁免面＝形态处理／集合成员判定
# （规格行 14 原文）：闭世界取值／承载域／行集族／矛盾池排除面的**结构取值集成员判定**
# 与 NFKC 归一、数值记号扫描、引标辖域切分、JSON 形判定等**形态处理**不算词表判。
# 被咬四形＝①含汉字串的字面集合（语义词表形）；②非 ASCII 字面成员判定（拿中文词当判据）；
# ③词面判方法（大小写折叠；「以中文词起止／切分／计数」）；④引入／使用正则面。


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _has_cjk_argument(node: ast.Call) -> bool:
    """调用是否以**汉字串字面**为参（词面判据的形态面——结构字符集参数不算）。"""
    for arg in (*node.args, *(keyword.value for keyword in node.keywords)):
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and _has_cjk(arg.value):
            return True
        if isinstance(arg, (ast.Tuple, ast.List, ast.Set)):
            if any(
                isinstance(item, ast.Constant)
                and isinstance(item.value, str)
                and _has_cjk(item.value)
                for item in arg.elts
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
            for operator in node.ops:
                if isinstance(operator, (ast.In, ast.NotIn)):
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
        and any(isinstance(operator, (ast.In, ast.NotIn)) for operator in node.ops)
    ]


def _defines(sources: list[Path], name: str) -> bool:
    """形态处理单点在场判据（归一／记号化／引标辖域切分等纯形态函数）。"""
    return any(
        isinstance(node, ast.FunctionDef) and node.name == name
        for path in sources
        for node in ast.walk(_tree_of(path))
    )


def test_no_lexicon_or_regex_in_verification() -> None:
    """行 14｜程序侧**无词表／正则语义判断**（AST 扫描本模块；豁免面＝形态处理／集合成员判定）。

    「这句话意思上能不能被材料支持」的**语义蕴含判定不做**（`specs/verification.md:19`「不做什么」
    第三行）；本块只做**确定性断言级核验**。豁免面两半的实际出现＝集合成员判定（闭世界取值／承载域／
    行集族／矛盾池排除面的形态值集判定）与形态处理（NFKC 归一、数值记号扫描、引标辖域切分、JSON 形
    判定——**零正则实现**，见 `rules.py` 模块注）。
    """
    sources = _package_sources()
    for path in sources:
        tree = _tree_of(path)
        where = path.name
        modules = _imported_modules(tree)
        assert "re" not in modules and "regex" not in modules, f"{where} 引入正则面"
        assert not any(
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in {"re", "regex"}
            for node in ast.walk(tree)
        ), f"{where} 使用 re.*"
        assert _lexicon_violations(tree) == [], f"{where}: {_lexicon_violations(tree)}"
        # 豁免面二：形态处理——词面判方法零使用（本块连结构字符集面的起止判都不需要）
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in (_CASE_FOLD_METHODS | _WORD_FACE_METHODS), (
                    f"{where}:{node.lineno} 词面判方法 {node.func.attr}"
                )

    # 闭世界取值面全 ASCII（结构取值集，非语义词表——形态值集／闭世界常量）
    closed_world = (
        CALIBER_KINDS
        | CARRIER_KINDS
        | ATTRIBUTION_CARRIER_KINDS
        | ROWSET_OBSERVATION_KINDS
        | GAP_KINDS
        | verification.REWRITE_REASONS
    )
    assert all(value.isascii() for value in closed_world)
    # 豁免面非空转：集合成员判定位点与形态处理单点真出现
    assert [line for path in sources for line in _membership_sites(_tree_of(path))]
    for name in (
        "normalize_for_match",
        "number_tokens",
        "citation_chunks",
        "without_markers",
        "scope_usable",
        "structural_line",
    ):
        assert _defines(sources, name), f"形态处理单点缺席：{name}"
    # 探测器非空转：词表／正则／汉字串成员判／词面判方法四形各被咬
    assert _lexicon_violations(ast.parse('WORDS = ["明细", "排名"]\n'))
    assert _lexicon_violations(ast.parse('import re\nre.search("产量", text)\n'))
    assert _lexicon_violations(ast.parse('if "谢谢" in text:\n    pass\n'))
    assert _lexicon_violations(ast.parse('if text.lower() == "no_hit":\n    pass\n'))
    assert _lexicon_violations(ast.parse('text.startswith("理解：")\n'))
    assert _lexicon_violations(ast.parse('names.count("日产油量")\n'))
    # 豁免不是漏网：形态切分／扫描与闭世界取值成员判不被咬
    assert not _lexicon_violations(ast.parse('line.strip()\n'))
    assert not _lexicon_violations(ast.parse('text.find("[")\n'))
    assert not _lexicon_violations(ast.parse('kind in {"agg_row", "lineage"}\n'))


# ---------- 行 17：【边界集】四形各落到对应分支 ----------


async def test_boundary_single_zero_material_conflict_fullwidth() -> None:
    """行 17｜【边界集】单句答案／零材料答案／双源矛盾／全角数字 → 各自落到对应分支。"""
    observations = [_obs(1, "ledger", content="日产油量 21.16 吨")]

    # ① 单句答案（仅一行、有据）→ 有支撑分支（逐句判定在单句面上不塌边）
    single = "渤中34-8 油田 2026 年日产油量 21.16 吨[1]。"
    single_state = _state(draft=single, observations=observations)
    single_verdict = verify(single_state, bus=EventBus())
    assert (
        single_verdict.supported,
        single_verdict.rewritten,
        single_verdict.split,
    ) == (1, 0, 0)
    assert single_verdict.cited == [1] and single_verdict.ok is True
    assert single_verdict.gaps == []
    assert single_state.draft == single and single_state.notices == []

    # ② 零材料答案（窗内零材料）→ 无据改写分支（零可解析引标即无据——不自动判过、不静默放行）
    zero_material = _state(
        draft="\n".join(
            [
                "该井日产油量 21.16 吨[1]。",
                "该井日产油量 1520 吨。",
            ]
        ),
        observations=[],
    )
    empty_verdict = verify(zero_material, bus=EventBus())
    assert (
        empty_verdict.supported,
        empty_verdict.rewritten,
        empty_verdict.split,
    ) == (0, 2, 0)
    assert empty_verdict.cited == [] and empty_verdict.ok is False
    assert {gap.kind for gap in empty_verdict.gaps} == {GAP_UNVERIFIED}
    assert zero_material.draft == ""  # 两行皆无据：整行离场（不留前缀残句）

    # ③ 双源矛盾 → 分列分支（组数＋`conflict` 留痕＋通知；不强调和、不取其一；块入增补面）
    conflict_supplements: list[dict[str, Any]] = []
    conflict_state = _state(
        draft="该油田日产油量有 21 吨/日[1]、也有 8824.4 方/日[2]。",
        observations=[
            _obs(1, "ledger", content="日产油量：21 吨/日", source="口径卡A"),
            _obs(2, "ledger", content="日产油量：8824.4 方/日", source="口径卡B"),
        ],
    )
    conflict_verdict = verify(
        conflict_state, bus=EventBus(), supplements=conflict_supplements
    )
    assert (
        conflict_verdict.supported,
        conflict_verdict.rewritten,
        conflict_verdict.split,
    ) == (1, 0, 1)
    assert conflict_verdict.ok is True  # 分列不计无据改写数（两维度不强行映射）
    assert NOTICE_CONTRADICTION_SPLIT in _notice_types(conflict_state)
    assert {
        entry["reason"] for entry in _step_payload(conflict_state)[PAYLOAD_REWRITES_KEY]
    } == {REWRITE_CONFLICT}
    conflict_block = _supplement_texts(conflict_supplements, SUPPLEMENT_BLOCK_SPLIT)[0]
    assert "[1] 口径卡A：日产油量：21 吨/日" in conflict_block
    assert "[2] 口径卡B：日产油量：8824.4 方/日" in conflict_block
    assert conflict_state.draft == "该油田日产油量有 21 吨/日[1]、也有 8824.4 方/日[2]。"

    # ④ 全角数字 → 判据面归一后落有据分支（输出面逐字保留原句）
    fullwidth = "该井日产油量为２１．１６吨［１］。"
    full_state = _state(draft=fullwidth, observations=observations)
    full_verdict = verify(full_state, bus=EventBus())
    assert (full_verdict.supported, full_verdict.rewritten, full_verdict.cited) == (
        1,
        0,
        [1],
    )
    assert full_state.draft == fullwidth

    # 四形各落各支（本行判据）——签名＝（有支撑句数／无据改写句数／分列组数／ok）
    def _signature(card: Verdict) -> tuple[int, int, int, bool]:
        return (card.supported, card.rewritten, card.split, card.ok)

    signatures = {
        "单句答案": _signature(single_verdict),
        "零材料答案": _signature(empty_verdict),
        "双源矛盾": _signature(conflict_verdict),
        "全角数字": _signature(full_verdict),
    }
    assert signatures == {
        "单句答案": (1, 0, 0, True),
        "零材料答案": (0, 2, 0, False),
        "双源矛盾": (1, 0, 1, True),
        "全角数字": (1, 0, 0, True),
    }


# ---------- 行 18：【保留集】无矛盾、有支撑的普通答案：各字段取值与 `ok=True` 行为不变 ----------


def _clean_answer_state() -> RunState:
    """保留集 fixture（无矛盾、有支撑的普通答案——各字段取值与 `ok=True` 行为不变的基线）。"""
    observations = [
        _obs(1, "agg_row", content="井号=N-01；日期=2026-01-01；日产油量（吨）=21.16"),
        _obs(2, "agg_row", content="井号=N-02；日期=2026-01-01；日产油量（吨）=18.4"),
    ]
    draft = "\n".join(
        [
            "一、产量概况",
            "N-01 井 2026-01-01 日产油量 21.16 吨[1]。",
            "N-02 井 2026-01-01 日产油量 18.4 吨[2]。",
        ]
    )
    return _state(
        question="各井 2026-01-01 日产油量是多少？",
        draft=draft,
        observations=observations,
    )


async def test_retention_clean_answer_unchanged() -> None:
    """行 18｜【保留集】无矛盾、有支撑的普通答案：各字段取值与 `ok=True` 行为不变。"""
    state = _clean_answer_state()
    draft = state.draft
    bus = EventBus()
    verdict = verify(state, bus=bus)

    # 各字段取值：无改写、无分列、引标落账、归属过、ok=True、无缺口、行集对账齐
    assert (verdict.supported, verdict.rewritten, verdict.split) == (2, 0, 0)
    assert verdict.cited == [1, 2]
    assert verdict.attribution is True and verdict.ok is True and verdict.gaps == []
    assert (verdict.delivered_rows, verdict.obs_rows) == (2, 2)
    # `ok=True` 时不得再改写（行为 9）：答案面逐字不变
    assert state.draft == draft
    # 零额外信号：无通知、无改写留痕、无行集注记；步 payload 六计数键齐
    assert state.notices == []
    payload = _step_payload(state)
    assert payload[PAYLOAD_REWRITES_KEY] == []
    assert payload[PAYLOAD_ROW_NOTE_KEY] is None
    assert payload[PAYLOAD_OK_KEY] is True
    assert _SIGNAL_PAYLOAD_KEYS <= set(payload)
    frames = await _frames(bus)
    assert _of(frames, EVENT_VERDICT) and not _of(frames, EVENT_NOTICE)

    # 行为不变：同输入重跑，判定卡与答案面逐字一致（保留集基线）
    rerun_state = _clean_answer_state()
    rerun = verify(rerun_state, bus=EventBus())
    assert rerun.as_dict() == verdict.as_dict()
    assert rerun_state.draft == draft
    assert rerun_state.notices == []


# ══════════ EB3 批（2026-10-17）：D2 增补面 ＋ D3 核验前缀三件套 ══════════
#
# 防回归四件（方案 `docs/runtime-refactor/proposals/EB3-交付面分层与缺陷修复.md` D2／D3）：
# - `::rewrite_exempt_disclosure_and_group_head`：豁免两类线不被贴前缀（D3-1）；
# - `::unsupported_deleted_with_verdict_count`：真无据句被删且 verdict 计数在位（D3-2）；
# - `::group_citation_marker_untouched`：组引标不被改（D3-3 的核验侧）；
# - `::lineage_paragraph_stripped_to_supplement`：血缘五要素整段入增补面（D2）。


_DISCLOSURE_OBS = {
    "index": 1,
    "locator": {"kind": "lineage"},
    "content": (
        "② 来源表：台账A · 2025-09-01 ③ 过滤条件：无 ④ 数据截至批次：2025-09-30 "
        "⑤ 收口注记：本窗 LIMIT 50 行封顶，窗 2025-09-01 至 2025-09-30"
    ),
    "source": "台账",
    "source_id": "obs-1",
}
_ROW_OBS = {
    "index": 2,
    "locator": {"kind": "agg_row"},
    "content": "井号=N-01；日期=2025-09-01；日产油量（吨）=21.16",
    "source": "台账",
    "source_id": "obs-2",
}


async def test_rewrite_exempt_disclosure_and_group_head() -> None:
    """EB3 D3-1｜豁免两类线（引擎披露行／组头行）**不被删句、不贴前缀**——原样保留在正文。

    判据（方案 D3 逐字）：(a) 引擎披露行＝行内含窗 ISO 区间或披露标记（封顶／截断／LIMIT／
    未覆盖）且与材料披露行事实一致；(b) 组头行＝行尾「：」或后邻行带引标的数据表头。
    **豁免面只作用于删句一拍**：真无据行仍整行离场（对照在测内）。
    """
    observations = [_DISCLOSURE_OBS, _ROW_OBS]
    disclosure_line = (
        "数据为 2025-09-01 至 2025-09-30 窗内数据（引擎按 LIMIT 50 行封顶，未覆盖部分不作答）。"
    )
    group_head = "各组明细如下："
    unsupported = "全油田 86 口井昨日均超产 50 吨。"
    state = _state(
        draft="\n".join([disclosure_line, group_head, unsupported]),
        observations=observations,
    )
    bus = EventBus()
    verdict = verify(state, bus=bus)

    lines = state.draft.splitlines()
    assert lines == [disclosure_line, group_head]  # 豁免两行原样保留；真无据行离场
    assert "未找到（材料未披露）" not in state.draft  # 前缀不进正文（EB3 D3）
    assert unsupported not in state.draft
    # 豁免不计改写（`rewritten` 只数真无据句）；留痕只留真无据那一句
    assert verdict.rewritten == 1
    assert {entry["line"] for entry in _step_payload(state)[PAYLOAD_REWRITES_KEY]} == {
        unsupported
    }

    # 对照（判据边界）：无 ISO／无披露标记的同样数字句 → 照删（豁免不松闸）
    plain = "全油田 86 口井昨日均超产 50 吨。"
    control = _state(draft=plain, observations=observations)
    control_verdict = verify(control, bus=EventBus())
    assert control_verdict.rewritten == 1
    assert control.draft == ""

    # 对照二：数据表头（含表格列记号）＋后邻行带引标 → 豁免；后邻行零引标 → 照删
    header = "| 序号 | 日产油量 | [1]–[3] |"
    cited_row = "| 1 | 21.16 吨 [2] |"
    with_citation = _state(
        draft="\n".join([header, cited_row]), observations=observations
    )
    verify(with_citation, bus=EventBus())
    assert with_citation.draft.splitlines()[0] == header  # 组头行原样（组引标不被改）
    without_citation = _state(
        draft="\n".join([header, "| 1 | 无引标行 |"]), observations=observations
    )
    verify(without_citation, bus=EventBus())
    assert header not in without_citation.draft  # 后邻行零引标＝非组头 → 照删


async def test_unsupported_deleted_with_verdict_count() -> None:
    """EB3 D3-2｜真无据断言**删句**（不贴前缀）且 `verdict.rewritten` 如实计数在位（不静默）。"""
    observations = [_obs(1, "ledger", content="日产油量 21.16 吨")]
    supported = "该井日产油量 21.16 吨[1]。"
    bad_one = "该井日产油量 99.5 吨[1]。"
    bad_two = "该井昨日产液 888 方。"
    state = _state(
        draft="\n".join([supported, bad_one, bad_two]),
        observations=observations,
    )
    bus = EventBus()
    verdict = verify(state, bus=bus)
    frames = await _frames(bus)

    assert state.draft == supported  # 两无据行整行离场、有据行逐字不变
    assert verdict.rewritten == 2  # 计数如实＝不静默
    assert verdict.ok is False  # 仍有「无据断言」被删 → 回炉位（行为 9）
    assert NOTICE_UNSUPPORTED_CLAIM in _notice_types(state)
    rewrites = _step_payload(state)[PAYLOAD_REWRITES_KEY]
    assert {entry["line"] for entry in rewrites} == {bad_one, bad_two}
    assert {entry["reason"] for entry in rewrites} == {REWRITE_NO_MATERIAL}
    assert _of(frames, EVENT_VERDICT)[0][PAYLOAD_REWRITTEN_KEY] == 2


async def test_group_citation_marker_untouched() -> None:
    """EB3 D3-3｜组引标不被改：组头行的 `[m]–[n]` 组引标原样在场（数据行仍逐行 `[n]`）。"""
    observations = [_DISCLOSURE_OBS, _ROW_OBS]
    group_head = "各组数据如下（[1]–[3]）："
    state = _state(
        draft="\n".join([group_head, "N-01 井 2025-09-01 日产油量 21.16 吨[2]。"]),
        observations=observations,
    )
    verdict = verify(state, bus=EventBus())

    lines = state.draft.splitlines()
    assert lines[0] == group_head  # 组引标 `[1]–[3]` 一字未动（不删、不改写、不贴前缀）
    assert "[1]–[3]" in state.draft
    assert lines[1] == "N-01 井 2025-09-01 日产油量 21.16 吨[2]。"  # 数据行仍逐行 [n]
    assert verdict.rewritten == 0 and verdict.ok is True


async def test_lineage_paragraph_stripped_to_supplement() -> None:
    """EB3 D2｜血缘五要素**整段**入增补面（`lineage`）；单行口径说明（≤2 行、带 `[n]`）留在正文。"""
    observations = [_DISCLOSURE_OBS, _ROW_OBS]
    card = "\n".join(
        [
            "① 口径：开井日历折算",
            "② 来源表：台账A",
            "③ 过滤条件：无",
            "④ 数据截至批次：2025-09-30",
            "⑤ 收口注记：本窗仅台账A",
        ]
    )
    caliber_note = "口径说明：本窗仅台账A、21.16 吨口径开井日历折算（② 来源表：台账A）[2]。"
    body = "N-01 井 2025-09-01 日产油量 21.16 吨[2]。"
    state = _state(
        draft="\n".join([body, "", card, "", caliber_note]),
        observations=observations,
    )
    supplements: list[dict[str, Any]] = []
    bus = EventBus()
    verdict = verify(state, bus=bus, supplements=supplements)

    # 整段剥出正文（五要素连续段不入答案面）；口径说明例外留在正文
    assert card not in state.draft  # 五要素连续段整段离场
    assert "① 口径：" not in state.draft
    assert "⑤ 收口注记：" not in state.draft
    assert caliber_note in state.draft
    assert body in state.draft
    texts = _supplement_texts(supplements, SUPPLEMENT_BLOCK_LINEAGE)
    assert texts == [card]  # 原样照抄（零二次创作）
    assert verdict.supported == 2  # 剥除不计改写、不改支撑面（body ＋ 口径说明两句在）

    # 对照：三行以上血缘卡（>2 行）不适用口径说明例外 → 整段剥（例外不看引标）
    long_note = "口径说明：本窗仅台账A[2]。\n（② 来源表：台账A）\n（补充：单位吨）"
    other = _state(draft=long_note, observations=observations)
    other_supplements: list[dict[str, Any]] = []
    verify(other, bus=EventBus(), supplements=other_supplements)
    assert other.draft == ""
    assert _supplement_texts(other_supplements, SUPPLEMENT_BLOCK_LINEAGE) == [long_note]

# ══════════ 2026-10-17 F1 修复批（核验面四件之件一／件二／件四）══════════════
#
# 真机证据：`eval/results/frames/EB4-D-诱12.json`（run-c6fd52c7——删句误伤使交付答案断在裸标题
# 「**两口井教训的差异**」）与 `eval/results/frames/Q14M-NQ-M4.json`（NQ-M4——题眼井号体系为 Y 系
# 〔渤中34-8〕而交付行引 `《B-渤中34-5油田躺井治理与检泵作业月报-202608》` 的 302／305／22.5 天）。


# ---------- F1 件一：数值断言只认计量数值（标识符／日期不算） ----------


async def test_identifier_and_date_not_numeric_assertion() -> None:
    """F1 件一 × V2-103｜**计量数值**判据：标识符（井号）与日期不算数值断言（`number_tokens`）。

    真机证据＝run-c6fd52c7：草稿「W-22 井教训侧重…／W-24 井教训侧重…」两行（无引标、无别的问题）
    被旧判据（任意数字串＝数值断言）整段删，交付答案断在裸标题。修后：标识符／日期行＝结构承载
    （原样保留、不计有支撑数）；**量值**行（带单位／小数／千分位形）照删（钉 pin-10 不放宽）。

    2026-10-18 V2-103 改判：删句判据面不变（量值行仍入断言面），但**无引标量值行**先过窗内对齐域
    ——窗内含该记号者保留并回填 `cited`（`该井检泵周期 295 天。` 命中窗内 `检泵周期 295 天`）；
    窗内**零命中**者照删（`1,000 吨`／`21.16` 窗内无该记号）。
    """
    observations = [_obs(1, "ledger", content="检泵周期 295 天")]
    identifier_lines = [
        "**两口井教训的差异**",
        "W-22 井教训侧重于定向井段大狗腿度部位的偏磨防控；"
        "W-24 井教训侧重于改层作业后的杆柱组合整体校核。",
        "该井为去年 11 月补孔改层井（2026 年 11 月 1 日投产）。",
        "渤海 302 修井机承担 W-21、W-22、W-24 三口井。",
    ]
    window_backed = "该井检泵周期 295 天。"     # 带单位＝量值断言；窗内有该记号 ⇒ 保留
    window_absent = [
        "该井累计产油 1,000 吨。",  # 千分位形＝量值断言；窗内零命中 ⇒ 照删
        "该井日产油量 21.16。",     # 小数形＝量值断言；窗内零命中 ⇒ 照删
    ]
    state = _state(
        question="W-22 与 W-24 两口井的教训有什么不同？",
        draft="\n".join([*identifier_lines, window_backed, *window_absent]),
        observations=observations,
    )
    bus = EventBus()
    verdict = verify(state, bus=bus)

    # 标识符／日期行逐字保留（不再被当无据断言删）；窗内命中量值行保留、零命中量值行照删
    assert state.draft.splitlines() == [*identifier_lines, window_backed]
    assert verdict.rewritten == len(window_absent)
    assert verdict.supported == 1  # 标识符行＝结构承载不计；窗内命中量值行计一
    assert verdict.cited == [1]    # 命中支回填（pin-10：不得 cited=[] 且数字在场）
    assert verdict.ok is False
    assert NOTICE_UNSUPPORTED_CLAIM in _notice_types(state)
    rewrites = _step_payload(state)[PAYLOAD_REWRITES_KEY]
    assert {entry["line"] for entry in rewrites} == set(window_absent)


# ---------- F1 件二 × V2-103：无引标行窗内比对（比对域＝全窗观测） ----------


async def test_uncited_line_reconciled_with_draft_cited() -> None:
    """F1 件二 × V2-103｜无引标行与**窗内观测**比对（判据单点＝`aligned_indices`），命中即保留且
    计有支撑——综述句重组已引事实不得删；**窗内零命中**＝照删（pin-10「不得 `cited=[]` 且数字在
    场」不放宽）。

    2026-10-18 V2-103 改判（票面 `tickets/v2/V2-103-无引标数字行比对域扩窗.md`；设计
    `docs/runtime-refactor/design/统筹方案-核验澄清评测.md` §2.3）：比对域由「同 draft 已 cited
    观察集」扩为**本轮窗内全观测**——故旧断言「零已引观察＝照删」改为「**窗内零命中**＝照删」。
    """
    observations = [
        _obs(
            1,
            "fragment",
            content="W-22 井检泵周期 295 天",
            source="《B-渤中34-5油田躺井治理与检泵作业月报-202608》",
        ),
        _obs(
            2,
            "fragment",
            content="W-24 井检泵周期 650 天",
            source="《B-渤中34-5油田躺井治理与检泵作业月报-202608》",
        ),
    ]
    detail = "W-22 井检泵周期 295 天[1]。"
    other_detail = "W-24 井检泵周期 650 天[2]。"
    summary = "综述：两口井检泵周期分别为 295 天与 650 天。"          # 无引标但重组已引事实
    unsupported = "该井日产油量 99.5 吨。"                            # 无引标且窗内无对应值 → 照删
    state = _state(
        question="W-22 与 W-24 两口井的检泵周期分别是多少天？",
        draft="\n".join([detail, other_detail, summary, unsupported]),
        observations=observations,
    )
    verdict = verify(state, bus=EventBus())

    assert state.draft.splitlines() == [detail, other_detail, summary]
    assert verdict.supported == 3          # 综述句计有支撑（重组已引事实）
    assert verdict.rewritten == 1
    assert verdict.cited == [1, 2]

    # V2-103 扩域：窗内含该记号（draft 零引标）⇒ 同一综述句保留、按命中支回填 cited
    window_backed = _state(
        question="W-22 与 W-24 两口井的检泵周期分别是多少天？",
        draft=summary,
        observations=observations,
    )
    window_verdict = verify(window_backed, bus=EventBus())
    assert window_backed.draft == summary
    assert window_verdict.supported == 1 and window_verdict.rewritten == 0
    assert window_verdict.cited == [1, 2]

    # 窗内零命中（窗内有观察但无该记号）⇒ 同一综述句照删（pin-10 不放宽）
    alone = _state(
        question="W-22 与 W-24 两口井的检泵周期分别是多少天？",
        draft=summary,
        observations=[_obs(1, "fragment", content="W-22 井检泵周期 880 天")],
    )
    alone_verdict = verify(alone, bus=EventBus())
    assert alone.draft == ""
    assert alone_verdict.rewritten == 1 and alone_verdict.cited == []


# ---------- V2-103 验收：无引标数字行比对域扩到全窗（`数-排1` 形＋真无据仍删） ----------


async def test_uncited_numeric_line_aligned_with_window_observation() -> None:
    """V2-103 验收 1｜`数-排1` 形离线复现：权威观测在窗 ⇒ **不再零交付**。

    真机证据＝EB11 `数-排1`（`eval/suite-147/results/EB11-删句原句.jsonl`：run-098e7ab2，
    `supported` 0／`rewritten` 1；被删原句＝本测 `line`；窗内观察＝`agg.fct_daily_metering` 的
    权威排名行，`井号=Z-16；区块=渤中；日产油量合计（吨）=5839.63`）。旧判据比对域＝「同 draft 已
    cited 观察集」——单句草稿零引标 ⇒ 域空 ⇒ 必删 ⇒ **零交付**；修后域＝全窗观测：命中即保留、按
    命中支回填 `cited`（pin-10「不得 `cited=[]` 且数字在场」不破），**文本零改（不插引标）**。
    """
    line = (
        "去年（2025-01-01 至 2026-01-01）日产油量最高的是 **Z-16 井**（属渤中区块），"
        "合计 5839.63 吨。"
    )
    observations = [
        _obs(
            1,
            "agg_row",
            content="井号=Z-16；区块=渤中；日产油量合计（吨）=5839.63",
            source="agg.fct_daily_metering",
        ),
        _obs(
            2,
            "agg_row",
            content="井号=X-25；区块=渤西；日产油量合计（吨）=5708.15",
            source="agg.fct_daily_metering",
        ),
        _obs(
            3,
            "agg_row",
            content="井号=N-15；区块=渤南；日产油量合计（吨）=5571.49",
            source="agg.fct_daily_metering",
        ),
    ]
    state = _state(
        question="去年日产油量最高的井是哪口？",
        draft=line,
        observations=observations,
    )
    bus = EventBus()
    verdict = verify(state, bus=bus)

    # 不再零交付：行逐字保留、计有支撑、命中支回填 cited；文本不插引标（回填只在 `cited` 落账面）
    assert state.draft == line
    assert verdict.supported == 1
    assert verdict.rewritten == 0
    assert verdict.cited == [1]
    assert verdict.ok is True
    assert verdict.gaps == []
    assert state.notices == []
    assert _step_payload(state)[PAYLOAD_REWRITES_KEY] == []
    assert _of(await _frames(bus), EVENT_VERDICT)[0][PAYLOAD_CITED_KEY] == [1]


async def test_uncited_numeric_line_without_window_hit_still_deleted() -> None:
    """V2-103 验收 2｜真无据形仍删（防蒙混）：窗内确无该记号 ⇒ 照删；数值记号**全等**不放宽
    （`52` 不命中 `1520`——非子串包含，行为 7 边界记号化）。
    """
    observations = [
        _obs(
            1,
            "agg_row",
            content="井号=Z-16；日产油量合计（吨）=5839.63",
            source="agg.fct_daily_metering",
        ),
        _obs(
            2,
            "agg_row",
            content="井号=X-25；日产油量合计（吨）=1520.0",
            source="agg.fct_daily_metering",
        ),
    ]
    fabricated = "该井日产油量 99.5 吨。"   # 窗内无该记号 → 照删
    boundary = "该井日产油量 52 吨。"      # 记号全等：`52` 不得命中 `1520.0`
    state = _state(
        question="去年日产油量最高的井是哪口？",
        draft="\n".join([fabricated, boundary]),
        observations=observations,
    )
    verdict = verify(state, bus=EventBus())

    assert state.draft == ""                # 两行皆真无据：整行离场（不留残句）
    assert verdict.supported == 0
    assert verdict.rewritten == 2
    assert verdict.cited == []
    assert verdict.ok is False
    rewrites = _step_payload(state)[PAYLOAD_REWRITES_KEY]
    assert {entry["line"] for entry in rewrites} == {fabricated, boundary}


# ---------- F1 件四：油田归属对账（另一油田数据且无分源说明 → 行拒收） ----------


async def test_cross_field_line_rejected_without_split_note() -> None:
    """F1 件四｜油田归属对账：被引材料**自带油田名**却不属**题眼所辖油田**、且行内无分源说明 →
    该行拒收（同删句族：留痕＋如实计数）＋机读键 `field_attribution_mismatch`。

    三条收窄面同测（真机帧取证）：①**分源说明**（行内写明该油田名）→ 保留；②**同油田不误伤**
    （题眼井号所在油田的材料片段承载题眼 ⇒ 该油田入题眼所辖面，`EB4-D-诱6.json` 形）；③**混引不
    误伤**（本行另有题眼所辖油田的引标 ⇒ 不拒收，`EB4-D-诱14.json` 形，口径补充行）；④无题眼锚
    ＝审静默。真机证据＝`eval/results/frames/Q14M-NQ-M4.json`（NQ-M4：34-8 题答 34-5 的
    302／305／22.5 天）。
    """
    observations = [
        # 窗内**题眼所辖油田**的材料（题眼井号 Y-21 落在此油田的报告里——NQ-M4 真机帧 obs[1] 形）
        _obs(
            1,
            "fragment",
            content="Y-21 井杆断的直接原因与深层管理原因；本月躺井 3 井次",
            source="《渤中34-8油田躺井治理与检泵作业月报-202701》",
        ),
        # 另一油田的材料（张冠李戴的来源）
        _obs(
            2,
            "fragment",
            content="W-21、W-22、W-24 三口井由渤海 302 修井机承担，月度船日合计 22.5 天",
            source="《B-渤中34-5油田躺井治理与检泵作业月报-202608》",
        ),
    ]
    question = "第五章 1 月修井船日里 Y-21、Y-25 由哪支修井机承担、月度船日合计多少天？"
    heading = "一、修井机与船日"
    cross_field = "- 修井机归属：渤海 302 承担 W-21、W-22、W-24，月度船日合计 22.5 天 [2]。"
    with_split_note = "- 另注（材料为渤中34-5油田月报）：其月度船日合计 22.5 天，非本题油田。[2]"

    state = _state(
        question=question,
        draft="\n".join([heading, cross_field]),
        observations=observations,
    )
    bus = EventBus()
    verdict = verify(state, bus=bus)
    frames = await _frames(bus)

    # 该行拒收（删句族处置）——标题行原样、被拒行离场；计数据实＝不静默
    # 2026-10-18 V2-106：全行拒收**不再零交付**——正文追加「本主体未覆盖＋已试什么」正证据
    # （兜底为追加、不吞标题；`state.draft` 非空断言见 `test_zero_delivery_field_mismatch_*`）。
    assert state.draft.splitlines()[0] == heading
    assert cross_field not in state.draft
    assert "本主体未覆盖" in state.draft
    assert verdict.rewritten == 1
    assert NOTICE_UNSUPPORTED_CLAIM in _notice_types(state)
    rewrites = _step_payload(state)[PAYLOAD_REWRITES_KEY]
    assert {entry["line"] for entry in rewrites} == {cross_field}
    assert {entry["reason"] for entry in rewrites} == {REWRITE_NO_MATERIAL}
    # 机读维度面：归属另一油田的被引序号列（升序去重）
    assert _step_payload(state)[PAYLOAD_FIELD_MISMATCH_KEY] == [2]
    assert _of(frames, EVENT_VERDICT)[0][PAYLOAD_REWRITTEN_KEY] == 1

    # ①分源说明（行内写明该油田名，行为 17 的分源列明）→ 不拒收、机读键空
    noted = _state(
        question=question, draft="\n".join([heading, with_split_note]), observations=observations
    )
    noted_verdict = verify(noted, bus=EventBus())
    assert noted.draft.splitlines() == [heading, with_split_note]
    assert noted_verdict.rewritten == 0
    assert _step_payload(noted)[PAYLOAD_FIELD_MISMATCH_KEY] == []

    # ②同油田不误伤（`EB4-D-诱6.json` 形）：题眼井号所在油田的材料片段承载题眼 ⇒ 该油田入所辖面
    same_field = [
        _obs(
            1,
            "fragment",
            content="W-31 井泵筒磨大，沉砂口袋砂面上升 42 米；对检泵周期低于 350 天的在用井建档",
            source="《B-渤中34-5油田躺井治理与检泵作业月报-202608》",
        )
    ]
    aliased = _state(
        question="8 月检泵作业里 W-31 井的检泵周期是多少天？",
        draft="W-31 井相关记录：沉砂口袋砂面上升 42 米 [1]。",
        observations=same_field,
    )
    aliased_verdict = verify(aliased, bus=EventBus())
    assert aliased.draft.splitlines() == ["W-31 井相关记录：沉砂口袋砂面上升 42 米 [1]。"]
    assert aliased_verdict.rewritten == 0
    assert _step_payload(aliased)[PAYLOAD_FIELD_MISMATCH_KEY] == []

    # ③无题眼锚＝审静默：同一行不拒收（不误伤）
    silent = _state(
        question="修井机与船日的情况如何？",
        draft="\n".join([heading, cross_field]),
        observations=observations,
    )
    silent_verdict = verify(silent, bus=EventBus())
    assert silent_verdict.rewritten == 0
    assert _step_payload(silent)[PAYLOAD_FIELD_MISMATCH_KEY] == []

    # ④混引不误伤（`EB4-D-诱14.json` 形）：本行另有题眼所辖油田的引标 ⇒ 不拒收
    mixed_line = "- 合计：Y-21 井船日 5.0 天 [1]；另注 34-5 侧合计 22.5 天 [2]。"
    mixed = _state(
        question=question,
        draft="\n".join([heading, mixed_line]),
        observations=observations,
    )
    mixed_verdict = verify(mixed, bus=EventBus())
    assert mixed.draft.splitlines() == [heading, mixed_line]
    assert mixed_verdict.rewritten == 0
    assert _step_payload(mixed)[PAYLOAD_FIELD_MISMATCH_KEY] == []


# ══════════ 2026-10-18 V2-106（件四零交付兜底——全行拒收产正证据声明）══════════════
#
# 票面＝`tickets/v2/V2-106-件四零交付兜底.md`（依据＝`design/统筹方案-核验澄清评测.md` §2.6）。
# 现状：件四（跨油田归属）**全行拒收**后 `out_lines` 只剩标题 ⇒ 实质零交付（真机形＝
# `eval/results/frames/Q14M-NQ-M4.json`）。修法：在 `_verify` 收口 `text="\n".join(out_lines)`
# **之前**加零交付兜底闸——件四拒收发生（`field_attribution_mismatch` 非空）且**零有支撑句**
# ⇒ 强制产出「本主体未覆盖＋已试什么」正证据声明（程序确定性、零模型），兜底文本进**正文**
# （`state.draft`，非增补面）＋ `notice`；**不放松** `field_attribution_mismatch` 本身（跨油田
# 混写照拒）。兜底只在 `delete` 档（`off` 不检测、`observe`／`repair` 不离场＝交付面草稿逐字，
# V2-116 红线）；`RewriteRecord.reason` 闭世界两值不动。step payload additive 键
# `zero_delivery_fallback`（兜底已生效）——`Verdict` 九键不动。


async def test_zero_delivery_field_mismatch_fallback_positive_evidence() -> None:
    """V2-106 验收 1／3｜NQ-M4 形离线复现：件四**全行拒收**不再零交付——正文含「本主体未覆盖
    ＋已试什么」正证据声明（进 `state.draft`、非增补面）＋ `notice` 在场；标题行原样留存、
    被拒行本体离场、机读面如实（`field_attribution_mismatch` ＋ `zero_delivery_fallback`）。
    """
    observations = [
        # 窗内**题眼所辖油田**的材料（题眼井号 Y-21 落在此油田的报告里——NQ-M4 真机帧 obs[1] 形）
        _obs(
            1,
            "fragment",
            content="Y-21 井杆断的直接原因与深层管理原因；本月躺井 3 井次",
            source="《渤中34-8油田躺井治理与检泵作业月报-202701》",
        ),
        # 另一油田的材料（张冠李戴的来源）
        _obs(
            2,
            "fragment",
            content="W-21、W-22、W-24 三口井由渤海 302 修井机承担，月度船日合计 22.5 天",
            source="《B-渤中34-5油田躺井治理与检泵作业月报-202608》",
        ),
    ]
    question = "第五章 1 月修井船日里 Y-21、Y-25 由哪支修井机承担、月度船日合计多少天？"
    heading = "一、修井机与船日"
    cross_field = "- 修井机归属：渤海 302 承担 W-21、W-22、W-24，月度船日合计 22.5 天 [2]。"
    draft = "\n".join([heading, cross_field])
    state = _state(question=question, draft=draft, observations=observations)
    bus = EventBus()
    verdict = verify(state, bus=bus)
    frames = await _frames(bus)

    # 验收 1／3：不再零交付——正文非空且携「本主体未覆盖＋已试什么」正证据（题眼所辖主体面
    # ＋已试材料清单），标题行原样留存（兜底为**追加**、不吞正文）
    assert state.draft.strip()
    assert state.draft.splitlines()[0] == heading
    assert "本主体未覆盖" in state.draft
    assert "已试什么" in state.draft
    assert "渤中34-8油田" in state.draft                       # 题眼所辖油田（未见其材料）
    assert "《B-渤中34-5油田躺井治理与检泵作业月报-202608》" in state.draft  # 已试材料出处
    assert cross_field not in state.draft                     # 被拒行本体离场（删句族处置不变）

    # notice 在场（状态写口 ＋ `notice` 帧恰三键）——不静默
    assert NOTICE_UNSUPPORTED_CLAIM in _notice_types(state)
    notice_frames = _of(frames, EVENT_NOTICE)
    assert ZERO_DELIVERY_NOTICE in [frame["content"] for frame in notice_frames]
    assert all(set(frame) == _NOTICE_FRAME_KEYS for frame in notice_frames)

    # 机读面：件四拒收序号列 ＋ 零交付兜底已生效（additive 键）；计数语义不变（如实计改写、
    # 零有支撑、`ok=False` 回炉位、`reason` 闭世界两值）
    payload = _step_payload(state)
    assert payload[PAYLOAD_FIELD_MISMATCH_KEY] == [2]
    assert payload[PAYLOAD_ZERO_DELIVERY_KEY] is True
    assert verdict.rewritten == 1
    assert verdict.supported == 0
    assert verdict.ok is False
    assert {entry["line"] for entry in payload[PAYLOAD_REWRITES_KEY]} == {cross_field}
    assert {entry["reason"] for entry in payload[PAYLOAD_REWRITES_KEY]} == {REWRITE_NO_MATERIAL}

    # 确定性：同输入两次运行正文逐字一致（题眼所辖面为集合——排序单点在渲染面）
    again = _state(question=question, draft=draft, observations=observations)
    assert verify(again, bus=EventBus()).ok is False
    assert again.draft == state.draft


async def test_zero_delivery_fallback_requires_field_mismatch_and_empty_support() -> None:
    """V2-106 验收 2｜红线不回退＋不误伤：①跨油田混写行（整行材料全来自另一油田且无分源说明）
    **仍被拒**；②本 draft 另有题眼所辖油田的支撑行（`supported>0`）⇒ **不触发**兜底（有交付面）；
    ③非件四的零交付（无 `field_attribution_mismatch`）⇒ **不触发**兜底（兜底只对件四全拒成立）。
    """
    observations = [
        _obs(
            1,
            "fragment",
            content="Y-21 井杆断的直接原因与深层管理原因；本月躺井 3 井次",
            source="《渤中34-8油田躺井治理与检泵作业月报-202701》",
        ),
        _obs(
            2,
            "fragment",
            content="W-21、W-22、W-24 三口井由渤海 302 修井机承担，月度船日合计 22.5 天",
            source="《B-渤中34-5油田躺井治理与检泵作业月报-202608》",
        ),
    ]
    question = "第五章 1 月修井船日里 Y-21、Y-25 由哪支修井机承担、月度船日合计多少天？"
    cross_field = "- 修井机归属：渤海 302 承担 W-21、W-22、W-24，月度船日合计 22.5 天 [2]。"
    supported_line = "Y-21 井杆断的直接原因与深层管理原因 [1]。"

    # ①＋②：混写行仍拒（红线）＋同 draft 有支撑行 ⇒ 不兜底（不误伤有交付面）
    mixed = _state(
        question=question,
        draft="\n".join([supported_line, cross_field]),
        observations=observations,
    )
    mixed_verdict = verify(mixed, bus=EventBus())
    assert cross_field not in mixed.draft                  # 跨油田混写行仍被拒
    assert supported_line in mixed.draft
    assert mixed_verdict.supported == 1
    assert mixed_verdict.rewritten == 1
    assert _step_payload(mixed)[PAYLOAD_FIELD_MISMATCH_KEY] == [2]
    assert _step_payload(mixed)[PAYLOAD_ZERO_DELIVERY_KEY] is False

    # ③：非件四零交付（无引标数字行窗内零命中）⇒ 兜底不触发（该形归 V2-103 的删句面）
    no_field = _state(
        question="去年日产油量最高的井是哪口？",
        draft="该井日产油量 99.5 吨。",
        observations=[
            _obs(1, "agg_row", content="井号=Z-16；日产油量合计（吨）=5839.63"),
        ],
    )
    no_field_verdict = verify(no_field, bus=EventBus())
    assert no_field.draft == ""
    assert no_field_verdict.rewritten == 1
    assert _step_payload(no_field)[PAYLOAD_FIELD_MISMATCH_KEY] == []
    assert _step_payload(no_field)[PAYLOAD_ZERO_DELIVERY_KEY] is False


async def test_zero_delivery_fallback_not_in_observe_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-106｜档位红线（V2-116）：`observe` 档下件四检出项**不离场**——交付面逐字等于草稿，
    零交付兜底**不得**触发（否则破「非 `delete` 档交付＝草稿逐字」红线）；机读键如实为 False。
    """
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_OBSERVE)
    observations = [
        _obs(
            1,
            "fragment",
            content="Y-21 井杆断的直接原因与深层管理原因；本月躺井 3 井次",
            source="《渤中34-8油田躺井治理与检泵作业月报-202701》",
        ),
        _obs(
            2,
            "fragment",
            content="W-21、W-22、W-24 三口井由渤海 302 修井机承担，月度船日合计 22.5 天",
            source="《B-渤中34-5油田躺井治理与检泵作业月报-202608》",
        ),
    ]
    heading = "一、修井机与船日"
    cross_field = "- 修井机归属：渤海 302 承担 W-21、W-22、W-24，月度船日合计 22.5 天 [2]。"
    draft = "\n".join([heading, cross_field])
    state = _state(
        question="第五章 1 月修井船日里 Y-21、Y-25 由哪支修井机承担、月度船日合计多少天？",
        draft=draft,
        observations=observations,
    )
    verdict = verify(state, bus=EventBus())

    assert state.draft == draft                            # 交付＝草稿逐字（零加工）
    assert "本主体未覆盖" not in state.draft
    assert verdict.rewritten == 1                          # 检出如实计数（不离场）
    assert _step_payload(state)[PAYLOAD_FIELD_MISMATCH_KEY] == [2]
    assert _step_payload(state)[PAYLOAD_ZERO_DELIVERY_KEY] is False


# ══════════ 2026-10-18 V2-94（核验定性句放行——承载片段断言无量值记号）══════════════
#
# 票面＝`tickets/v2/V2-94-核验定性句放行.md`。真机实证＝`eval/results/EB9-判分.md` D-诱12
# step13：`rewrites` 4 行全 `no_material`（含 W-24 定性断口检查句）——**28 个核验测无覆盖**。
# 修法：承载片段（`fragment`／`agg_row`／`lineage`）的支撑判据放宽一处——**断言辖域无计量数值
# 记号时，引标可解析即保留**（step payload additive 键 `qualitative_kept`）；**有计量数值仍照旧
# 记号比对、对不上照删**（防编造红线不动）；一行多引标按「任一支撑即过」。`rewrites`／
# `Verdict.ok=False` 语义与 `RewriteRecord.reason` 闭世界（两值）不变。

# EB9 D-诱12 真机帧（`eval/results/frames/EB9-D-诱12.json`）窗内两支承载片段原文（逐字照抄）
_EB9_D12_W22_FRAGMENT = (
    "4.1 W-22 井抽油杆断（典型案例）W-22 井基本参数：泵挂 2200 米，φ44 泵，冲程 5 米，"
    "冲次 4.2 次/分，最大井斜 23.6°（位于 1950 米），最大狗腿度 4.2°/30m（位于 2020 米附近）。"
    "作业起管检查：断点位于 1980 米处第 38 根抽油杆杆体（非接头），断口呈典型疲劳磨损特征；"
    "对应位置油管内壁有明显环状磨槽，深度 0.8～1.2 毫米。1900～2100 米井段抽油杆接箍普遍偏磨，"
    "最重处接箍单侧磨掉 2.1 毫米。原因分析：该井段处于狗腿度最大区域，杆柱中性点偏上，下冲程"
    "杆柱弯曲导致杆管偏磨集中；原杆柱设计扶正器间距 8 米，在 4.2°/30m 狗腿度下不足以保持杆柱"
    "居中。上月初该井功图已显示下冲程迟缓（供液不足与偏磨双重特征），但未列入当月检泵计划，"
    "属预测预警跟进不及时。整改措施：①扶正器间距由 8 米加密至 4 米；②泵上 120 米范围下加重杆"
    "（φ38 毫米）使中性点下移；③调整冲次由 4.2 降至 3.8 次/分，预计检泵周期可延长至 650 天以上。"
)
_EB9_D12_W24_FRAGMENT = (
    "4.2 W-24 井杆断（短周期案例）W-24 井检泵周期仅 295 天，为去年 11 月补孔改层井。"
    "断点 1650 米，检查发现为新旧杆混配段（新杆 D 级、旧杆 C 级混用），旧杆强度不足先断。"
    "教训：改层加深泵挂后未按新工况整体校核杆柱，混配段应力超出旧杆许用范围。本次作业已整串"
    "更换 D 级杆，并按加深后的泵挂重新设计杆柱组合（一级杆 18 毫米×520 米＋二级杆 22 毫米×840 米"
    "＋三级杆 19 毫米×840 米，待复算确认）。"
)
_EB9_D12_ROWS_FRAGMENT = (
    "二、躺井原因分类统计　　杆断 3 井次 W-21、W-22、W-24 占 42.9%；泵漏 2 井次 W-23、W-31 占 "
    "28.6%；其他 2 井次占 28.6%；合计 7 井次占 100%。3 口杆断井均发生在井斜大于 18° 的定向井段，"
    "与管杆偏磨历史规律一致。"
)
_EB9_D12_SOURCE = "《B-渤中34-5油田躺井治理与检泵作业月报-202608》"
_EB9_D12_QUESTION = (
    "W-22 和 W-24 两口杆断井的断点分别在多少米？断口检查和根因分析分别怎么说？"
    "两口井的教训有什么不同？"
)


async def test_qualitative_fragment_claim_kept() -> None:
    """V2-94-1｜无数字句引 fragment（有数字的观察）→ 保留 ＋ `qualitative_kept=1`。

    承载片段（`fragment`）的断言辖域**零计量数值记号**时，引标可解析即保留（V2-94 放宽面）；
    该行仍计有支撑数、引标落账，`rewrites` 不产留痕（非无据）。
    """
    observations = [
        _obs(42, "fragment", content=_EB9_D12_W24_FRAGMENT, source=_EB9_D12_SOURCE)
    ]
    heading = "**W-24 井（断口检查）**"
    qualitative_line = (
        "- 断口检查：断点位于新旧杆混配段（新杆 D 级、旧杆 C 级混用），旧杆强度不足先断 [42]。"
    )
    state = _state(
        question="W-24 井断口检查结论是什么？",
        draft="\n".join([heading, qualitative_line]),
        observations=observations,
    )
    bus = EventBus()
    verdict = verify(state, bus=bus)

    assert state.draft.splitlines() == [heading, qualitative_line]  # 定性句保留（不删）
    assert verdict.rewritten == 0
    assert verdict.ok is True
    assert verdict.supported == 1  # 放行行计有支撑数（不是结构承载）
    assert verdict.cited == [42]
    payload = _step_payload(state)
    assert payload["qualitative_kept"] == 1  # 定性句放行计数（additive 键）
    assert payload[PAYLOAD_REWRITES_KEY] == []


async def test_numeric_claim_still_deleted() -> None:
    """V2-94-2｜句含数字、观察无该记号 → 照删（防编造红线不动）。

    承载片段面**有计量数值**时仍照旧记号比对（`2500 米` 不在观察的 `1650 米` 记号集里）——
    零重叠照改、整行离场；`qualitative_kept` 不计。
    """
    observations = [
        _obs(
            42,
            "fragment",
            content="W-24 井检泵周期仅 295 天。断点 1650 米，旧杆强度不足先断。",
            source=_EB9_D12_SOURCE,
        )
    ]
    heading = "**W-24 井（断点）**"
    fabricated = "- 断点深度：2500 米，第 40 根抽油杆杆体断裂 [42]。"
    state = _state(
        question="W-24 井断点深度是多少米？",
        draft="\n".join([heading, fabricated]),
        observations=observations,
    )
    bus = EventBus()
    verdict = verify(state, bus=bus)

    assert state.draft == heading  # 无据行整行离场（不贴前缀、不留残句）
    assert fabricated not in state.draft
    assert verdict.rewritten == 1
    assert verdict.ok is False
    assert _step_payload(state)["qualitative_kept"] == 0
    rewrites = _step_payload(state)[PAYLOAD_REWRITES_KEY]
    assert {entry["line"] for entry in rewrites} == {fabricated}
    assert {entry["reason"] for entry in rewrites} == {REWRITE_NO_MATERIAL}


async def test_multi_citation_any_support() -> None:
    """V2-94-3｜一行引 [7][42]，仅 [7] 支撑 → 保留（任一支撑即过）。

    修前该行三支全不过（`all` 语义 ＋ 窗内对齐因 `300 天` 无命中而落空）→ 整行删；修后承载
    片段任一支撑即过。有数字的辖域仍逐记号比对（本行无 `qualitative_kept`——断言面有量值）。
    """
    observations = [
        _obs(7, "fragment", content=_EB9_D12_W22_FRAGMENT, source=_EB9_D12_SOURCE),
        _obs(42, "fragment", content=_EB9_D12_W24_FRAGMENT, source=_EB9_D12_SOURCE),
    ]
    heading = "**两口井对比**"
    mixed_line = "- 断点深度：1980 米 [7]；检泵周期 300 天 [42]。"
    state = _state(
        question="W-22 与 W-24 两口井的断点深度是多少米？",
        draft="\n".join([heading, mixed_line]),
        observations=observations,
    )
    bus = EventBus()
    verdict = verify(state, bus=bus)

    assert state.draft.splitlines() == [heading, mixed_line]  # [7] 支撑即过（[42] 不支撑不连坐）
    assert verdict.rewritten == 0
    assert verdict.ok is True
    assert verdict.cited == [7, 42]  # 两引标皆落账（本行在场）
    assert _step_payload(state)["qualitative_kept"] == 0  # 断言面有量值：不属定性句放行


async def test_deleted_line_leaves_no_residue() -> None:
    """V2-94-4｜删行后正文无半句残渣（整行离场，不贴前缀、不留半句）。"""
    observations = [
        _obs(
            42,
            "fragment",
            content="W-24 井检泵周期仅 295 天。断点 1650 米，旧杆强度不足先断。",
            source=_EB9_D12_SOURCE,
        )
    ]
    heading = "**W-24 井（断点）**"
    good = "- 断点深度：1650 米 [42]。"
    bad = "- 断点深度：2500 米，第 40 根抽油杆杆体断裂 [42]。"
    state = _state(
        question="W-24 井断点深度是多少米？",
        draft="\n".join([heading, good, bad]),
        observations=observations,
    )
    verdict = verify(state, bus=EventBus())

    assert state.draft.splitlines() == [heading, good]
    assert verdict.rewritten == 1
    # 半句残渣零留存（前缀／断句／后半句皆不在正文）
    for residue in ("2500", "第 40 根", "杆体断裂", "断点深度：2500", "未找到"):
        assert residue not in state.draft


async def test_eb9_d12_shape_qualitative_line_kept() -> None:
    """V2-94-5｜EB9 D-诱12 形复现：4 行不再全删（至少 W-24 定性断口检查句保留）。

    真机帧（`eval/results/frames/EB9-D-诱12.json`，run-5e2e642e）step13 签名＝
    **supported 6／rewritten 4**（四条 `no_material`：W-24 断口检查句／W-24 教训句／共同点句／
    区别要点句，后三句辖域亦零量值记号）。本测按该帧的两支承载片段（4.1／4.2 正文）＋答案稿
    逐字复现该形：修前 4 行全删（含 W-24 定性句）；修后四条定性句放行（`qualitative_kept=4`）。
    """
    observations = [
        _obs(7, "fragment", content=_EB9_D12_W22_FRAGMENT, source=_EB9_D12_SOURCE),
        _obs(8, "fragment", content=_EB9_D12_ROWS_FRAGMENT, source=_EB9_D12_SOURCE),
        _obs(42, "fragment", content=_EB9_D12_W24_FRAGMENT, source=_EB9_D12_SOURCE),
    ]
    draft_lines = [
        "**W-22 井（断点 / 断口检查 / 根因）**",
        "- 断点深度：1980 米，第 38 根抽油杆杆体（非接头）位置断裂 [7]。",
        "- 断口检查：呈典型疲劳磨损特征；同位油管内壁可见深度 0.8～1.2 毫米的环状磨槽；"
        "1900～2100 米井段抽油杆接箍普遍偏磨，最重处接箍单侧磨掉 2.1 毫米 [7]。",
        "- 根因分析：断点位于狗腿度最大区域（最大狗腿度 4.2°/30m，2020 米附近），杆柱中性点偏上，"
        "下冲程弯曲引发杆管偏磨集中；原扶正器 8 米间距在 4.2°/30m 狗腿度下不足以保持杆柱居中 [7]。"
        "上月功图已显示下冲程迟缓（供液不足与偏磨双重特征）但未列入检泵计划，属预测预警跟进"
        "不及时 [7]。",
        "**W-24 井（断点 / 断口检查 / 根因）**",
        "- 断点深度：1650 米 [42]。",
        "- 断口检查：断点位于新旧杆混配段（新杆 D 级、旧杆 C 级混用），旧杆强度不足先断 [42]。",
        "- 根因分析：该井为去年 11 月补孔改层井（检泵周期仅 295 天），改层加深泵挂后未按新工况"
        "整体校核杆柱，混配段应力超出旧杆许用范围 [42]。",
        "**两口井教训的不同**",
        '- W-22 属"设计参数与井斜狗腿度不匹配"——教训指向杆柱与井筒轨迹的匹配：在 4.2°/30m '
        "强狗腿度井段，原 8 米扶正器间距不够，需将间距加密至 4 米并下加重杆下移中性点、冲次由 "
        "4.2 降至 3.8 次/分，预计检泵周期延至 650 天以上 [7]。",
        '- W-24 属"工况变更后未做整体校核"——教训指向改层加深泵挂这类工况变化的管理：旧杆柱'
        "直接延用、新旧杆混配使局部应力超限，须整串更换 D 级杆并按加深后的泵挂重新设计杆柱"
        "组合 [42]。",
        "- 共同点：两口井均属定向井段杆断（井斜大于 18°），与管杆偏磨历史规律一致 [8]；"
        "整改后均纳入杆柱力学复算名单 [7][42]。",
        "- 区别要点：W-22 是杆柱居中能力（扶正器间距/中性点）不足以应对强狗腿度，W-24 是工况"
        "变化（补孔改层、加深泵挂）后杆柱组合未同步重做 [7][42]。",
    ]
    state = _state(
        question=_EB9_D12_QUESTION,
        draft="\n".join(draft_lines),
        observations=observations,
    )
    bus = EventBus()
    verdict = verify(state, bus=bus)

    assert verdict.rewritten == 0  # 修前 4（四条全删）→ 修后 0（不再全删）
    assert verdict.ok is True
    assert verdict.supported == 10  # 修前 6（四条定性句不计支撑）→ 修后 10（四条放行计支撑）
    payload = _step_payload(state)
    assert payload["qualitative_kept"] == 4  # 四条定性句放行
    # 至少 W-24 定性断口检查句保留（票面点名的实证行）
    qualitative_lines = draft_lines[6:7] + draft_lines[10:11] + draft_lines[11:13]
    assert all(line in state.draft for line in qualitative_lines)
    assert "断口检查：断点位于新旧杆混配段" in state.draft
    # 有数字的行照旧逐记号比对（未被定性放行牵连）
    assert "- 断点深度：1980 米，第 38 根抽油杆杆体（非接头）位置断裂 [7]。" in state.draft
    assert 7 in verdict.cited and 42 in verdict.cited


# ---------- V2-105：台账卡／口径卡不入数值断言面（生产实点五 kind）----------
# 票面＝`tickets/v2/V2-105-台账卡不入数值断言面.md`（L0 裁定 **D-d′**）。判据值域＝**生产实点
# 五 kind**（真源 `appv2/knowledge/domain.py:28-32` 的 `KIND_ALL`）——**非**信任级 `ledger`、
# **非** `_KIND_TRUST` 旧键 `family_annotation`（两者与生产 `locator.kind` 永不匹配）。真机证据＝
# EB11 `Q27`（`eval/suite-147/results/EB11-归因.md:83`）：唯一观察 `ledger｜sem_metric#201` 正文
# 含「99 §2.12」⇒ `number_tokens` 回 `('2.12',)` ⇒ 引用该卡的纯定性句（只读声明）被非承载
# 「全须复述」判无据删句。判据＝**kind 值域**（零 CJK 词表——零词表 AST 闸面）。

# 台账／口径卡正文（含册号／节号形——`§` 紧邻的数不入口径数值面）。
_CALIBER_SECTION_BODY = "「配产量」指标在台账中的绑定态为未绑定，agg 读模型（99 §2.12）未落该列"
# Q27 形只读声明句（EB11 删句原句逐字：`eval/suite-147/results/EB11-删句原句.jsonl:124`）。
_Q27_READONLY_LINE = (
    "该诉求属于数据修改（写入），「问一问」仅提供查询服务，不具备数据写入或修改权限 [1]。"
)


def test_caliber_kinds_production_five_match() -> None:
    """V2-105-0｜判据值域＝**生产实点五 kind**（非 `ledger`／非 `family_annotation`）。

    真源 `appv2/knowledge/domain.py:28-32` `KIND_ALL`；本块 R6 禁直引引擎，故以同值字面钉此
    （形态值集，非语义词表）。
    """
    assert CALIBER_KINDS == {"metric", "term", "object", "relation", "family"}
    assert all(value.isascii() for value in CALIBER_KINDS)
    assert "ledger" not in CALIBER_KINDS
    assert "family_annotation" not in CALIBER_KINDS


@pytest.mark.parametrize("kind", ["metric", "term", "object", "relation", "family"])
async def test_caliber_kind_section_number_not_deleted(kind: str) -> None:
    """V2-105-1｜生产五 kind 各 1 测：台账卡定性句**不再**因册号被删（`§` 紧邻的数不入面）。"""
    observations = [_obs(1, kind, content=_CALIBER_SECTION_BODY, source="sem_metric#201")]
    state = _state(draft=_Q27_READONLY_LINE, observations=observations)
    verdict = verify(state, bus=EventBus())

    assert state.draft == _Q27_READONLY_LINE  # 只读声明句保留（修前：`('2.12',)` 全须复述判不过）
    assert verdict.rewritten == 0
    assert verdict.supported >= 1
    assert verdict.ok is True


async def test_caliber_value_still_checkable() -> None:
    """V2-105-2｜口径数值仍可核：口径卡的**计量数值**照旧须复述（对不上照删，防编造不动）。"""
    observations = [
        _obs(1, "metric", content="口径：日产油量 21.16 吨（99 §2.12）", source="口径卡A"),
    ]
    kept = "该井日产油量为 21.16 吨[1]。"
    deleted = "该井日产油量为 30 吨[1]。"
    state = _state(draft="\n".join([kept, deleted]), observations=observations)
    verdict = verify(state, bus=EventBus())

    assert state.draft.splitlines() == [kept]
    assert verdict.rewritten == 1 and verdict.supported == 1
    assert _step_payload(state)[PAYLOAD_REWRITES_KEY] == [
        {"line": deleted, "reason": REWRITE_NO_MATERIAL}
    ]


async def test_q27_shape_readonly_declaration_kept() -> None:
    """V2-105-3｜`Q27` 形离线复现：只读声明句保留（`supported` 0→≥1）。

    真机帧形（`eval/suite-147/results/EB11-删句原句.jsonl:124`，run-85605527）：两条 `no_material`
    ——「无法改为 30 方」句（无引标量值行，照删）＋只读声明句（引台账卡、纯定性，本票救回）。
    """
    observations = [_obs(1, "metric", content=_CALIBER_SECTION_BODY, source="sem_metric#201")]
    refused = "抱歉，N-01 井昨日的日产油量无法改为 30 方。"
    state = _state(draft="\n".join([refused, _Q27_READONLY_LINE]), observations=observations)
    verdict = verify(state, bus=EventBus())

    assert _Q27_READONLY_LINE in state.draft  # 只读声明句保留（票面验收 3）
    assert refused not in state.draft  # 无引标量值行照删（防编造红线不动）
    assert verdict.supported >= 1  # 修前 0（只读声明句被删）
    assert verdict.rewritten == 1


# ---------- V2-104：表格行裸数字入记号面（案 A——不动渲染面）----------
# 票面＝`tickets/v2/V2-104-表格数值可核化.md`（**案 A**：`number_tokens` 认表格行裸数字，判据
# **结构性**；案 B〔表头单位回填〕不动）。真机证据＝EB1 `D-诱1`（`eval/results/frames/
# EB1-D-诱1.json` observation index 10）：表体「　　…　415」的 415 裸数字不入记号面 ⇒ 承载片段
# （`locator.kind="fragment"`）任一数值重叠判不过 ⇒ 草稿「- 2025年8月：415天[10]」整行被删
# （修前 rewritten=3／supported=0／cited=[]）。判据面全为**版式结构**（行首缩进 ＋ 行内列空白
# 分隔的数字列计数 ＋ 全文此类行计数），**零词表、零正则**（零词表 AST 闸 `test_no_lexicon_or_
# regex_in_verification` 咬汉字字面／正则面）。

# `D-诱1` 观察正文逐字（帧 `EB1-D-诱1.json` observation index 10；`\u3000`＝全角空白缩进——
# `normalize_for_match` 的 NFKC 归一为半角空格后入结构判据；表头行数字列不足＝不判表行）。
_D_Y1_TABLE_CONTENT = (
    "八、近三年同期躺井对比━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    "\u3000\u3000年份（8 月）\u3000躺井(井次)\u3000躺井率\u3000杆断占比\u3000平均检泵周期(天)\n"
    "\u3000\u30002024\u3000\u3000\u3000\u3000\u300013\u3000\u3000\u3000\u3000\u30008.3%"
    "\u3000\u300046%\u3000\u3000\u3000386\n"
    "\u3000\u30002025\u3000\u3000\u3000\u3000\u3000 9\u3000\u3000\u3000\u3000\u30005.8%"
    "\u3000\u300044%\u3000\u3000\u3000415\n"
    "\u3000\u30002026\u3000\u3000\u3000\u3000\u3000 7\u3000\u3000\u3000\u3000\u30004.5%"
    "\u3000\u300043%\u3000\u3000\u3000428"
    "三年同比看，躺井井次与杆断占比逐年下降，平均检泵周期三年延长 42 天，与扶正器加密、加重杆推广"
    "两项治理的累计覆盖面扩大正相关。2024 年 8 月为历史最差月（当年高温期地面故障叠加井况集中"
    "暴露），"
    "其治理台账底数不清是主因之一，这也是本年起建立\"一井一策\"档案的由来。"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
)


def test_v2104_table_row_bare_numbers_enter_token_face() -> None:
    """V2-104-0｜表格行裸数字入记号面（结构性判据；既有三形不回退）。"""
    tokens = verification_rules.number_tokens(
        verification_rules.normalize_for_match(_D_Y1_TABLE_CONTENT)
    )
    # 表体三行的裸数字列（修前缺席 ⇒ `D-诱1` 415 行被删）
    for token in ("386", "415", "428", "2024", "2025", "2026", "13", "9", "7"):
        assert token in tokens, token
    # 既有三形（小数／带单位）不回退
    for token in ("8.3", "46", "42"):
        assert token in tokens, token


def test_v2104_non_table_bare_numbers_not_in_token_face() -> None:
    """V2-104-1｜非表格裸数字不入记号面（防误放行）：日期／编号／标识符／节号形。**

    两半证据：①纯 prose 行（无缩进表体）全零；②表格正文内**同行 prose 尾**的日期数字也不入
    （列判据＝数字前紧邻 ≥2 空白——prose 的「2024 年 8 月」前是句号／单空白，不是列分隔）。
    """
    prose = "该井 2026 年 8 月 1 日完井，井号 W-22，编号 302，台账见 99 §2 节。"
    assert verification_rules.number_tokens(verification_rules.normalize_for_match(prose)) == ()

    tokens = verification_rules.number_tokens(
        verification_rules.normalize_for_match(
            _D_Y1_TABLE_CONTENT + "\n完井日期 2026 年 8 月 1 日，编号 302。"
        )
    )
    assert "302" not in tokens  # 追加 prose 行的编号裸数字不入面
    assert "8" not in tokens  # 表行同行 prose 尾「2024 年 8 月」的 8（前紧邻单空白）不入面
    assert "415" in tokens  # 表体列数字仍在面（防收得过狠）


def test_v2104_single_indented_numeric_line_not_table() -> None:
    """V2-104-2｜「缩进数字行 ≥2」为全文级条件：孤行不判表体（防把缩进列表误当表格）。"""
    single = "　　2025　　415\n完井日期 2026 年 8 月 1 日"
    tokens = verification_rules.number_tokens(verification_rules.normalize_for_match(single))
    assert "415" not in tokens


def test_v2104_caliber_face_not_widened() -> None:
    """V2-104-3｜口径面（`caliber_numbers_only`）不收表格行裸数字——V2-105 收窄面不回退。"""
    obs = _obs(1, "metric", content=_D_Y1_TABLE_CONTENT, source="口径卡")
    tokens = verification_rules.caliber_numbers_only(obs)
    assert "415" not in tokens and "386" not in tokens
    assert "8.3" in tokens  # 口径面既有量值三形不动


async def test_v2104_eb_d_y1_shape_415_line_kept() -> None:
    """V2-104-4｜`D-诱1` 形离线复现：415 行不再被删（supported 0→3／rewritten 3→0／cited 10）。

    草稿＝帧 `EB1-D-诱1.json` 步骤 108 的表体三行逐字；观察＝同帧 observation index 10 正文
    逐字（生产 `locator.kind`＝`fragment`——检索切片承载族，任一数值重叠即支撑）。
    """
    observations = [
        _obs(
            10,
            "fragment",
            content=_D_Y1_TABLE_CONTENT,
            source="《B-渤中34-5油田躺井治理与检泵作业月报-202608》",
        )
    ]
    lines = [
        "**② 2024、2025、2026年8月的平均检泵周期数值**",
        "- 2024年8月：386天[10]",
        "- 2025年8月：415天[10]",
        "- 2026年8月：428天[10]",
    ]
    state = _state(
        question="近三年8月平均检泵周期是否一直在变差？",
        draft="\n".join(lines),
        observations=observations,
    )
    verdict = verify(state, bus=EventBus())

    assert state.draft.splitlines() == lines  # 三行逐字保留（修前：三行全删、只剩标题）
    assert verdict.rewritten == 0
    assert verdict.supported == 3
    assert verdict.cited == [10]


# ---------- V2-116：核验动作四档（off／observe／repair／delete）----------
# 票面＝`tickets/v2/V2-116-校对员三档开关.md`（含末尾「Kimi 评审修正」）：配置单点＝环境变量
# `VERIFY_ACTION`；**缺省档＝`delete`**（保既有行为；评审修正 1）；`observe` 另立新测。
# env-pin 机制＝`tests/conftest.py::_pin_verify_action`（评审修正 2）；本节的非 delete 档用例
# 在本例内 `monkeypatch.setenv` 显式覆盖。

_MODE_SUPPORTED_LINE = "该井日产油量为 21.16 吨[1]。"
_MODE_UNSUPPORTED_LINE = "该井日产油量为 99.5 吨[1]。"


def _mode_case() -> tuple[list[dict[str, Any]], str]:
    """四档共用用例：一行有据 ＋ 一行无据（检出恰 1 条 `no_material`）。"""
    observations = [_obs(1, "ledger", content="该井日产油量 21.16 吨")]
    return observations, "\n".join([_MODE_SUPPORTED_LINE, _MODE_UNSUPPORTED_LINE])


def test_verify_action_env_pinned_delete_by_conftest() -> None:
    """V2-116-0｜conftest env-pin 机制在场（评审修正 2）：全测试树缺省钉 `VERIFY_ACTION=delete`。

    本测**不设** env——读到的值只能来自 `tests/conftest.py` 的 autouse 夹具
    （新建机制，非「加一行」）。
    """
    assert os.environ[VERIFY_ACTION_ENV] == VERIFY_MODE_DELETE
    assert VERIFY_MODE_DEFAULT == VERIFY_MODE_DELETE
    assert VERIFY_MODES == {
        VERIFY_MODE_OFF,
        VERIFY_MODE_OBSERVE,
        VERIFY_MODE_REPAIR,
        VERIFY_MODE_DELETE,
    }


async def test_verify_mode_default_delete_when_env_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-116-1｜缺省档＝`delete`：env 未设时行为与现 HEAD 一致（删句＋留痕＋mode 标注）。"""
    monkeypatch.delenv(VERIFY_ACTION_ENV)
    observations, draft = _mode_case()
    state = _state(draft=draft, observations=observations)
    verdict = verify(state, bus=EventBus())

    assert state.draft.splitlines() == [_MODE_SUPPORTED_LINE]  # 无据行整行离场（旧行为）
    assert _MODE_UNSUPPORTED_LINE not in state.draft
    assert verdict.rewritten == 1 and verdict.ok is False
    payload = _step_payload(state)
    assert payload[PAYLOAD_VERIFY_MODE_KEY] == VERIFY_MODE_DELETE
    assert payload[PAYLOAD_INTENDED_REWRITES_KEY] == [
        {"line": _MODE_UNSUPPORTED_LINE, "reason": REWRITE_NO_MATERIAL}
    ]


async def test_verify_mode_delete_explicit_matches_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-116-2｜`delete` 显式档：行为与现 HEAD 一致（删句＋notice＋计数）＋ mode 标注。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_DELETE)
    observations, draft = _mode_case()
    state = _state(draft=draft, observations=observations)
    bus = EventBus()
    verdict = verify(state, bus=bus)

    assert state.draft.splitlines() == [_MODE_SUPPORTED_LINE]
    assert NOTICE_UNSUPPORTED_CLAIM in _notice_types(state)
    assert _step_payload(state)[PAYLOAD_VERIFY_MODE_KEY] == VERIFY_MODE_DELETE
    assert verdict.rewritten == 1


async def test_verify_mode_observe_delivery_verbatim_and_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-116-3｜`observe`：照常检测但不删任何行——交付＝草稿逐字；检出项入 `intended_rewrites`
    （每条含原句 `line` 与 `reason`）＋ `verify_mode`；计数＝检出条数（不静默）。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_OBSERVE)
    observations, draft = _mode_case()
    state = _state(draft=draft, observations=observations)
    bus = EventBus()
    verdict = verify(state, bus=bus)

    assert state.draft == draft  # 交付面零加工：逐字等于草稿
    assert _MODE_UNSUPPORTED_LINE in state.draft
    payload = _step_payload(state)
    assert payload[PAYLOAD_VERIFY_MODE_KEY] == VERIFY_MODE_OBSERVE
    assert payload[PAYLOAD_INTENDED_REWRITES_KEY] == [
        {"line": _MODE_UNSUPPORTED_LINE, "reason": REWRITE_NO_MATERIAL}
    ]
    # 计数语义随档标注：`rewritten`＝**检出条数**（非离场数——行仍在）
    assert verdict.rewritten == 1
    assert payload[PAYLOAD_REWRITTEN_KEY] == 1
    assert verdict.ok is False  # 检出即「无据断言残留」在位（行为 9；不静默）
    # 检出不得静默：`unsupported_claim` notice 在场（类型闭世界不变）
    assert NOTICE_UNSUPPORTED_CLAIM in _notice_types(state)
    notices = [entry for entry in state.notices if entry.get("type") == NOTICE_UNSUPPORTED_CLAIM]
    # 档位诚实：observe 下未删任何行——文案不得称「删去」（只记录不删）
    assert notices and "只记录不删" in str(notices[0].get("content"))


async def test_verify_mode_observe_conflict_detected_not_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-116-4｜`observe` 下矛盾检出同样只记不删：`intended_rewrites` 含 `conflict` 原句。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_OBSERVE)
    observations = [
        _obs(1, "ledger", content="日产油量：21 吨/日", source="口径卡A"),
        _obs(2, "ledger", content="日产油量：8824.4 方/日", source="口径卡B"),
    ]
    draft = "该油田日产油量有 21 吨/日[1]、也有 8824.4 方/日[2]。"
    state = _state(draft=draft, observations=observations)
    supplements: list[dict[str, Any]] = []
    verdict = verify(state, bus=EventBus(), supplements=supplements)

    assert state.draft == draft  # 交付＝草稿逐字
    assert verdict.split == 1
    payload = _step_payload(state)
    assert payload[PAYLOAD_VERIFY_MODE_KEY] == VERIFY_MODE_OBSERVE
    assert {entry["reason"] for entry in payload[PAYLOAD_INTENDED_REWRITES_KEY]} == {
        REWRITE_CONFLICT
    }
    assert payload[PAYLOAD_INTENDED_REWRITES_KEY][0]["line"] == draft


async def test_verify_mode_off_skips_check_delivery_verbatim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-116-5｜`off`：完全跳过逐行核验（不检测、不改写）——交付＝草稿逐字、零检出。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_OFF)
    observations, draft = _mode_case()
    state = _state(draft=draft, observations=observations)
    verdict = verify(state, bus=EventBus())

    assert state.draft == draft
    payload = _step_payload(state)
    assert payload[PAYLOAD_VERIFY_MODE_KEY] == VERIFY_MODE_OFF
    assert payload[PAYLOAD_INTENDED_REWRITES_KEY] == []
    assert payload[PAYLOAD_REWRITES_KEY] == []
    assert (verdict.supported, verdict.rewritten, verdict.cited) == (0, 0, [])
    assert verdict.ok is True
    assert NOTICE_UNSUPPORTED_CLAIM not in _notice_types(state)


async def test_verify_mode_repair_fallback_equals_observe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-116-6｜`repair`：V2-115 未落地 → 等同 `observe` 并记 `verify_mode="repair-fallback"`。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    observations, draft = _mode_case()
    state = _state(draft=draft, observations=observations)
    verdict = verify(state, bus=EventBus())

    assert state.draft == draft  # 等同 observe：交付＝草稿逐字
    payload = _step_payload(state)
    assert payload[PAYLOAD_VERIFY_MODE_KEY] == VERIFY_MODE_REPAIR_FALLBACK
    assert payload[PAYLOAD_INTENDED_REWRITES_KEY] == [
        {"line": _MODE_UNSUPPORTED_LINE, "reason": REWRITE_NO_MATERIAL}
    ]
    assert verdict.rewritten == 1


async def test_verify_mode_invalid_value_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-116-7｜档位闭世界越界 → fail-fast（不静默回落），核验器错误契约转 `ok=False`＋缺口。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, "rewrite")  # 闭世界外
    observations, draft = _mode_case()
    state = _state(draft=draft, observations=observations)
    verdict = verify(state, bus=EventBus())

    assert verdict.ok is False
    assert len(verdict.gaps) == 1
    assert VERIFY_ACTION_ENV in verdict.gaps[0].reason
    assert "非法值" in verdict.gaps[0].reason
    assert state.draft == draft  # 抛错前交付面零加工


async def test_verify_mode_observe_block_strip_still_applies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-116-8｜「交付＝草稿逐字」辖域＝**逐行核验输入**（块剥除后）：档位只停「无据删句」，
    行为 12 的块头模式族段剥除**照常**（真源＝
    `docs/runtime-refactor/design/统筹方案-核验澄清评测.md` §2.1「块剥除仍做」；
    本票边界＝不碰 `transport` 段剥离单点）。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_OBSERVE)
    observations = [
        _obs(1, "ledger", content="N-01 井 2025-09-01 日产油量 21.16 吨"),
        _obs(2, "lineage", content="② 来源表：台账A"),
    ]
    card = "\n".join(
        [
            "① 口径：开井日历折算",
            "② 来源表：台账A",
            "③ 过滤条件：无",
            "④ 数据截至批次：2025-09-30",
            "⑤ 收口注记：本窗仅台账A",
        ]
    )
    body = "N-01 井 2025-09-01 日产油量 21.16 吨[1]。"
    unsupported = "N-01 井 2025-09-01 日产油量 30 吨[1]。"
    state = _state(
        draft="\n".join([body, unsupported, "", card]),
        observations=observations,
    )
    supplements: list[dict[str, Any]] = []
    verdict = verify(state, bus=EventBus(), supplements=supplements)

    # 块剥除照常（五要素整段入增补面，零二次创作）
    assert card not in state.draft
    assert _supplement_texts(supplements, SUPPLEMENT_BLOCK_LINEAGE) == [card]
    # 档位停的是「无据删句」——检出句不离场（行为 3 的删句处置只在 `delete` 档）
    assert body in state.draft and unsupported in state.draft
    assert verdict.rewritten == 1

