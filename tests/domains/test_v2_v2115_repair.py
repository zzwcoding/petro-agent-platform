"""V2-115 核验失败动作＝回炉修复（程序只检测、模型改写）验收。

票面＝`tickets/v2/V2-115-核验失败动作回炉修复.md`（含末尾「Kimi 评审修正」）；设计真源＝
`docs/runtime-refactor/design/统筹方案-核验澄清评测.md` §2.2。要点（Kimi 修正为准）：

1. **落点编排侧**：回炉节点＝`orchestration/repair.py`＋`INTENT_REPAIR`（镜像 V2-96 explore 环）；
   `verification` 只检测与标红（R8 零 LLM 红线＋`::no_model_call_in_verification` 不破）；
2. **检测（程序，零语义）**：沿用既有判据标出问题行、不删；
3. **回炉（LLM，语义）**：只重写问题行（改引标／改写成缺位／删）——不得新增窗内无据数值；
4. **复检（程序）**：同一 `_verify_lines` 单点；`MAX_REPAIR_ROUNDS` 到顶 → 模型缺位说明；
5. **零交付兜底**：最终无内容 → 程序确定性诚实说明（同 V2-106 形，插入点在 `join` 之前）；
6. **留痕**：回炉请求／模型返回／复检结果全落 step payload（含逐行原句）。

端到端＝脚本化 completer（离线零触网）；`VERIFY_ACTION=repair` 由各例显式指定（conftest 缺省钉
`delete`）。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest

from appv2.infra.clock import freeze
from appv2.runtimev2.gateway_adapter import ScriptedCompleter, set_completer
from appv2.runtimev2.orchestration.constants import (
    PAYLOAD_REPAIR_RECHECK_KEY,
    PAYLOAD_REPAIR_REQUEST_KEY,
    PAYLOAD_REPAIR_RESPONSE_KEY,
    PAYLOAD_REPAIR_ROUNDS_KEY,
)
from appv2.runtimev2.orchestration.repair import run_repair
from appv2.runtimev2.persistence import RunStore as V2RunStore
from appv2.runtimev2.state import (
    INTENT_ANSWER,
    INTENT_REPAIR,
    MAX_REPAIR_ROUNDS,
    RunState,
)
from appv2.runtimev2.transport import EventBus
from appv2.runtimev2.verification import (
    PAYLOAD_INTENDED_REWRITES_KEY,
    PAYLOAD_REPAIR_ZERO_DELIVERY_KEY,
    PAYLOAD_VERIFY_MODE_KEY,
    REPAIR_ZERO_DELIVERY_NOTICE,
    VERIFY_ACTION_ENV,
    VERIFY_MODE_REPAIR,
    detect_intended,
    verify,
)
from tests.domains.test_v2_four_phase import (
    V2_UNDERSTAND,
    V2LedgerPort,
    V2QueueEngine,
    v2_data_match,
    v2_decompose,
    v2_ledger_dump,
    v2_ledger_note,
    v2_matches,
    v2_registry,
    v2_run,
    v2_runtime,
    wire_ledger_projection,
)
from tests.domains.test_v2_react_loop import _rows_outcome
from tests.domains.test_v2_verification import _notice_types, _obs, _state

# ---------- 共用件 ----------

# 回炉轮模型调用归因桶（V2-125：自有第四桶 `repair`——此前复用 `answer`，归因面不可分）。
_MODEL_CALLER = "repair"


def _verify_payloads(state: RunState) -> list[dict[str, Any]]:
    """核验步 payload 列（按产出序——回炉环下核验可多次入账）。"""
    return [
        dict(step["payload"])
        for step in state.steps
        if isinstance(step.get("payload"), Mapping)
        and step["payload"].get("phase") == "verify"
    ]


def _repair_payloads(state: RunState) -> list[dict[str, Any]]:
    """回炉步 payload 列（键面单点＝`PAYLOAD_REPAIR_ROUNDS_KEY`）。"""
    return [
        dict(step["payload"])
        for step in state.steps
        if isinstance(step.get("payload"), Mapping)
        and PAYLOAD_REPAIR_ROUNDS_KEY in step["payload"]
    ]


def _rewrite_reply(index: int, text: str) -> str:
    return json.dumps(
        {"lines": [{"index": index, "action": "rewrite", "text": text}]},
        ensure_ascii=False,
    )


def _drop_reply(index: int) -> str:
    return json.dumps(
        {"lines": [{"index": index, "action": "drop"}]}, ensure_ascii=False
    )


def _ring(state: RunState, replies: list[str]) -> ScriptedCompleter:
    """脚本化 completer 驱动「核验 → 回炉 → 复检」环（同图路由：`INTENT_REPAIR` 自环）。

    有界循环（`2 * MAX_REPAIR_ROUNDS + 6`）——不收敛即判失败（防静默自旋）。
    """
    completer = ScriptedCompleter({_MODEL_CALLER: list(replies)})
    previous = set_completer(completer)
    try:
        bus = EventBus()
        for _ in range(2 * MAX_REPAIR_ROUNDS + 6):
            if state.next_intent == INTENT_REPAIR:
                run_repair(state)
                continue
            verify(state, bus=bus)
            if state.next_intent != INTENT_REPAIR:
                break
        else:
            raise AssertionError("回炉环未收敛（有界循环耗尽）")
    finally:
        set_completer(previous)
    return completer


# ---------- 1 检测口（程序，零 LLM） ----------


def test_detect_intended_is_program_detection_single_point() -> None:
    """V2-115-1｜`detect_intended`＝程序检测口（复用 `_verify_lines` 单点）：只报标红行、
    零写面（不动 `state.draft`／`state.steps`／意图），reason 闭世界仍两值。"""
    observations = [_obs(1, "ledger", content="该井日产油量 21.16 吨")]
    unsupported = "该井日产油量为 99.5 吨[1]。"
    state = _state(draft=unsupported, observations=observations)
    before = (state.draft, list(state.steps), state.next_intent)

    flagged = detect_intended(state)

    assert [record.line for record in flagged] == [unsupported]
    assert {record.reason for record in flagged} == {"no_material"}
    assert (state.draft, list(state.steps), state.next_intent) == before


# ---------- 2 四形单测（票面验收 1） ----------


def test_repair_citation_fixable_rewrites_citation(monkeypatch: pytest.MonkeyPatch) -> None:
    """V2-115-2｜①引标可修正形：数值在窗内**另一支**——模型改引标后复检通过、正文保留该行。

    判据面：定性句引**非承载**台账（观察有量值、断言辖域零计量数值）⇒ 记号比对不过 ⇒ 标红；
    改引到窗内**承载片段**（`qualitative_release`）即过——「数字在窗内另一支 → 改引标」的可修正形。
    """
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    observations = [
        _obs(1, "ledger", content="该井日产油量 21.16 吨"),
        _obs(2, "fragment", content="该井日产液量 8824.4 方", source="月报"),
    ]
    wrong = "该井日产液量处于高位[1]。"
    fixed = "该井日产液量处于高位[2]。"
    state = _state(draft=wrong, observations=observations)
    completer = _ring(state, [_rewrite_reply(1, fixed)])

    # V2-125：回炉调用归因**自有桶** `repair`（不再混入 `answer`）；步记录步型＝`verify`
    assert completer.calls and completer.calls[0][0] == _MODEL_CALLER
    model_steps = [
        step
        for step in state.steps
        if isinstance(step.get("payload"), Mapping)
        and step["payload"].get("caller") == _MODEL_CALLER
    ]
    assert model_steps and model_steps[-1]["step"] == "verify"
    assert state.draft == fixed                       # 只重写问题行、正文其余零改
    assert state.next_intent == INTENT_ANSWER
    assert state.repair_rounds == 1
    assert state.verdict is not None and state.verdict["ok"] is True
    assert state.verdict["cited"] == [2]

    # 留痕：回炉请求／模型返回／复检结果全落 step payload（含逐行原句）
    repairs = _repair_payloads(state)
    assert len(repairs) == 1
    face = repairs[0]
    assert face[PAYLOAD_REPAIR_ROUNDS_KEY] == 1
    assert face[PAYLOAD_REPAIR_REQUEST_KEY]["lines"] == [wrong]
    assert wrong in face[PAYLOAD_REPAIR_REQUEST_KEY]["prompt"]
    assert face[PAYLOAD_REPAIR_RESPONSE_KEY]["raw"].strip()
    assert face[PAYLOAD_REPAIR_RECHECK_KEY] == []      # 复检通过

    # 核验侧如实标注 `repair` 档（非 fallback）
    assert _verify_payloads(state)[-1][PAYLOAD_VERIFY_MODE_KEY] == VERIFY_MODE_REPAIR


def test_repair_truly_unsupported_rewritten_as_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    """V2-115-3｜②真无据形：窗内无该数值——模型改写成「本轮材料未覆盖」后复检通过。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    observations = [_obs(1, "ledger", content="该井日产油量 21.16 吨")]
    unsupported = "该井日产油量为 99.5 吨[1]。"
    gap_line = "本轮材料未覆盖该井日产油量数值。"
    state = _state(draft=unsupported, observations=observations)
    _ring(state, [_rewrite_reply(1, gap_line)])

    assert state.draft == gap_line
    assert "99.5" not in state.draft
    assert state.verdict is not None and state.verdict["ok"] is True
    assert _repair_payloads(state)[0][PAYLOAD_REPAIR_RECHECK_KEY] == []


def test_repair_zero_delivery_forces_honest_statement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-115-4｜③零交付形：模型删行致正文空 ⇒ 程序强制诚实说明（已试什么／仍缺什么），
    不留空白、不静默——插入点在核验收口 `join` 之前（同 V2-106 形）。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    observations = [_obs(1, "ledger", content="该井日产油量 21.16 吨")]
    unsupported = "该井日产油量为 99.5 吨[1]。"
    state = _state(draft=unsupported, observations=observations)
    _ring(state, [_drop_reply(1)])

    assert state.draft.strip()                         # 不留空白
    assert "已试什么" in state.draft and "仍缺" in state.draft
    assert state.next_intent == INTENT_ANSWER
    payload = _verify_payloads(state)[-1]
    assert payload[PAYLOAD_REPAIR_ZERO_DELIVERY_KEY] is True
    assert REPAIR_ZERO_DELIVERY_NOTICE in [
        str(entry.get("content")) for entry in state.notices
    ]
    assert "unsupported_claim" in _notice_types(state)


def test_repair_anti_fabrication_number_not_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    """V2-115-5｜④反编造形：窗内无该数值 ⇒ 模型两轮改写仍保留编造数值 → 复检照咬；
    `MAX_REPAIR_ROUNDS` 到顶 → 模型缺位说明，编造数值**不得**进交付面（记号全等判据不变）。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    observations = [_obs(1, "ledger", content="该井日产油量 21.16 吨")]
    fabricated = "该井日产油量为 99.5 吨[1]。"
    still_dirty = "该井日产油量为 99.5 吨[1]（窗内未覆盖）。"
    honest = "本轮材料未覆盖该井日产油量数值。"
    state = _state(draft=fabricated, observations=observations)
    completer = _ring(
        state,
        [
            _rewrite_reply(1, still_dirty),
            _rewrite_reply(1, still_dirty),
            honest,
        ],
    )

    assert "99.5" not in state.draft
    assert state.draft == honest
    assert state.repair_rounds == MAX_REPAIR_ROUNDS
    assert completer.counts()[_MODEL_CALLER] == 3        # 2 轮改写 ＋ 1 轮缺位说明
    repairs = _repair_payloads(state)
    assert len(repairs) == 3
    # 前两轮复检仍咬（编造数值在窗内零命中）
    assert repairs[0][PAYLOAD_REPAIR_RECHECK_KEY][0]["line"] == still_dirty
    assert repairs[1][PAYLOAD_REPAIR_RECHECK_KEY][0]["line"] == still_dirty
    assert repairs[2][PAYLOAD_REPAIR_REQUEST_KEY]["mode"] == "gap"
    assert repairs[2][PAYLOAD_REPAIR_RECHECK_KEY] == []


def test_repair_gap_statement_dirty_falls_back_to_program_statement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-115-6｜缺位说明自身仍编造（复检照咬）⇒ 交程序确定性诚实说明（防「模型缺位说明」变成
    新的编造面）；仍不落空答。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    observations = [_obs(1, "ledger", content="该井日产油量 21.16 吨")]
    fabricated = "该井日产油量为 99.5 吨[1]。"
    dirty_gap = "本轮材料未覆盖该井日产油量 99.5 吨。"
    state = _state(draft=fabricated, observations=observations)
    _ring(
        state,
        [
            _rewrite_reply(1, fabricated),
            _rewrite_reply(1, fabricated),
            dirty_gap,
        ],
    )

    assert "99.5" not in state.draft
    assert "已试什么" in state.draft
    assert _verify_payloads(state)[-1][PAYLOAD_REPAIR_ZERO_DELIVERY_KEY] is True


# ---------- 3 档位接缝（V2-116 repair 档） ----------


def test_repair_mode_flags_and_routes_to_repair_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-115-7｜`repair` 档落地：检出即标红（交付面＝草稿逐字）＋ `verify_mode="repair"`
    ＋ `next_intent="repair"`（回炉口开启；`repair-fallback` 不再出现）。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    observations = [_obs(1, "ledger", content="该井日产油量 21.16 吨")]
    unsupported = "该井日产油量为 99.5 吨[1]。"
    state = _state(draft=unsupported, observations=observations)
    verify(state, bus=EventBus())

    assert state.draft == unsupported                   # 只检测与标红，不删
    assert state.next_intent == INTENT_REPAIR
    payload = _verify_payloads(state)[0]
    assert payload[PAYLOAD_VERIFY_MODE_KEY] == VERIFY_MODE_REPAIR
    assert payload[PAYLOAD_INTENDED_REWRITES_KEY] == [
        {"line": unsupported, "reason": "no_material"}
    ]


def test_repair_mode_clean_draft_routes_to_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-115-8｜`repair` 档无检出（复检通过形）⇒ 意图仍收 `answer`（回炉口不空转）。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    observations = [_obs(1, "ledger", content="该井日产油量 21.16 吨")]
    supported = "该井日产油量为 21.16 吨[1]。"
    state = _state(draft=supported, observations=observations)
    verify(state, bus=EventBus())

    assert state.next_intent == INTENT_ANSWER
    assert detect_intended(state) == []


# ---------- 4 端到端：`数-排1` / `D-诱1` 形（脚本化 completer，`repair` 档） ----------


def test_repair_mode_shupai1_shape_no_zero_delivery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-115-9｜端到端（脚本化 completer）｜`数-排1` 形：权威观测在窗 ⇒ `repair` 档下
    不再零交付（行逐字保留、回填 `cited`；零回炉调用——无标红即零加工）。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
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
    ]
    state = _state(
        question="去年日产油量最高的井是哪口？", draft=line, observations=observations
    )
    completer = _ring(state, [])

    assert state.draft == line
    assert state.verdict is not None and state.verdict["supported"] == 1
    assert state.verdict["ok"] is True
    assert completer.counts() == {}                     # 零回炉调用（无标红）
    assert _repair_payloads(state) == []


def test_repair_mode_dy1_shape_415_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    """V2-115-10｜端到端（脚本化 completer）｜`D-诱1` 形：415 行不再被删（`repair` 档下
    表格数值可核化判据不变——零标红、零回炉）。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    table_body = (
        "\u3000\u30002024\u3000\u30009\u3000\u30005.8%\u3000\u300044%\u3000\u3000386\n"
        "\u3000\u30002025\u3000\u30009\u3000\u30005.8%\u3000\u300044%\u3000\u3000415\n"
        "\u3000\u30002026\u3000\u300013\u3000\u30007.7%\u3000\u300041%\u3000\u3000428"
    )
    observations = [
        _obs(10, "fragment", content="抽油杆断点统计\n" + table_body, source="月报")
    ]
    draft = "\n".join(
        [
            "- 2024年9月：386天[10]",
            "- 2025年8月：415天[10]",
            "- 2026年13月：428天[10]",
        ]
    )
    state = _state(draft=draft, observations=observations)
    _ring(state, [])

    assert "415" in state.draft
    assert state.draft == draft
    assert state.verdict is not None and state.verdict["rewritten"] == 0


# ---------- 5 端到端：四相位图（脚本化 completer，回炉真跑） ----------


async def test_repair_end_to_end_graph_rewrites_unsupported_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-115-11｜端到端（四相位图＋脚本化 completer）：草稿一行编造数值 → 回炉重写该行 →
    复检通过 → 交付面携正确数值、编造数值零残留；回炉留痕落 run 步。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    clarify = v2_decompose(
        subtask_id="s1",
        question="2025-09-01 到 09-03 各井日产油量",
        ledger_notes=note,
        chain="data",
    )
    fabricated = "N-01 井 2025-09-01 日产油量 99.5 吨 [1]。"
    corrected = "N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            clarify,
            v2_matches(
                v2_data_match(
                    subtask_id="s1",
                    slot="日产油量",
                    start="2025-09-01",
                    end="2025-09-03",
                )
            ),
        ],
        "answer": [fabricated],
        # V2-125：回炉回复归**自有桶** `repair`（此前与作答同桶）
        _MODEL_CALLER: [_rewrite_reply(1, corrected)],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    engine = V2QueueEngine([_rows_outcome()])
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script=script, registry=v2_registry(engine=engine)
        )
        events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    run_id = next(
        event.data["run_id"] for event in reversed(events) if "run_id" in event.data
    )
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"

    state = V2RunStore().load(run_id)
    assert state.status == "completed"
    assert "21.16" in (state.answer or "")
    assert "99.5" not in (state.answer or "")
    assert state.repair_rounds == 1
    repairs = _repair_payloads(state)
    assert len(repairs) == 1
    assert repairs[0][PAYLOAD_REPAIR_REQUEST_KEY]["lines"] == [fabricated]
    assert repairs[0][PAYLOAD_REPAIR_RECHECK_KEY] == []
    # 核验（标红）与回炉（改写）两步都在 run 步账上
    kinds = [row.step for row in V2RunStore().steps(run_id)]
    assert "verify" in kinds


async def test_repair_end_to_end_graph_zero_delivery_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-115-12｜端到端（四相位图）：回炉删行致正文空 → 程序诚实说明兜底交付（非空答案）。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    clarify = v2_decompose(
        subtask_id="s1",
        question="2025-09-01 到 09-03 各井日产油量",
        ledger_notes=note,
        chain="data",
    )
    fabricated = "N-01 井 2025-09-01 日产油量 99.5 吨 [1]。"
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            clarify,
            v2_matches(
                v2_data_match(
                    subtask_id="s1",
                    slot="日产油量",
                    start="2025-09-01",
                    end="2025-09-03",
                )
            ),
        ],
        "answer": [fabricated],
        # V2-125：回炉回复归**自有桶** `repair`（此前与作答同桶）
        _MODEL_CALLER: [_drop_reply(1)],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    engine = V2QueueEngine([_rows_outcome()])
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script=script, registry=v2_registry(engine=engine)
        )
        events = await v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    run_id = next(
        event.data["run_id"] for event in reversed(events) if "run_id" in event.data
    )
    state = V2RunStore().load(run_id)

    assert state.status == "completed"
    assert (state.answer or "").strip()
    assert "已试什么" in (state.answer or "")
    assert "99.5" not in (state.answer or "")


# ---------- 6 确定性 ----------


def test_repair_deterministic_same_input_same_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V2-115-13｜确定性：同输入同剧本两跑，交付面逐字一致（程序侧零随机）。"""
    monkeypatch.setenv(VERIFY_ACTION_ENV, VERIFY_MODE_REPAIR)
    observations = [_obs(1, "ledger", content="该井日产油量 21.16 吨")]
    wrong = "该井日产油量为 99.5 吨[1]。"
    fixed = "本轮材料未覆盖该井日产油量数值。"
    drafts: list[str] = []
    for _ in range(2):
        state = _state(draft=wrong, observations=observations)
        _ring(state, [_rewrite_reply(1, fixed)])
        drafts.append(state.draft)
    assert drafts[0] == drafts[1] == fixed
