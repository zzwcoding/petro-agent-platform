"""V2-118 澄清问答闭环验收（ask 结构化＋回答程序落位＋同问指纹＋降级默认）。

票面＝`tickets/v2/V2-118-澄清问答闭环.md`（含「Kimi 评审修正」节）。四条验收逐条落测：

1. `Q16` 形离线复现（`::test_v118_q16_shape_offline_only_one_ask_no_repeat`）：口径问题只问一次；
   对账不过 → 默认＋注记收口，**不再重抛**（同问第二次起走降级路径，零新挂起帧）；
2. 同问重复计数＝0（`::test_v118_same_slot_second_ask_not_repeated`——构造「同一 slot 二次提问」
   场景：`state.asked_fingerprints` 恰一条、`state.pending_ask` 不被第二次重抛覆盖）；
3. ask 帧新增键为 **additive**（`detail.slot`——顶层四键零增删，
   `::test_v118_ask_frame_detail_slot_additive_zero_frame_change`）且 `specs/transport.md` 已登记；
   既有 transport 测试零回退（`tests/domains/test_v2_transport.py` 本批零改）；
4. 全量闸面在票面回报节，本件只承机读面。

Kimi 评审修正 1＝slot 落 `detail.slot`（零帧闭世界变更，不动 transport 块）；修正 2＝降级路径
**不得过 `_on_ask`**（否则增 `_ask_count`／占 `ask_cap`）——机读面＝
`::test_v118_degrade_path_does_not_consume_ask_cap`。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from appv2.infra.clock import freeze
from appv2.runtimev2.clarification import clarify
from appv2.runtimev2.clarification.constants import (
    ASK_DETAIL_SLOT_KEY,
    ASK_SLOT_CALIBER,
    ASK_SLOT_CLARIFY,
    ASK_SLOT_WINDOW,
    PAYLOAD_ASK_FRAME,
    PAYLOAD_DEGRADED,
    ask_fingerprint,
)
from appv2.runtimev2.clarification.models import ClarifyAsk
from appv2.runtimev2.context import wire_ledger_projection
from appv2.runtimev2.prompts import PHASE_CLARIFY, assemble_decision_increment
from appv2.runtimev2.prompts.decision_round import (
    _DEFAULT_LINE,
    _HINT_SLOT_LINE,
)
from appv2.runtimev2.state import AskChoice as V2AskChoice
from appv2.runtimev2.state import Budget, RunState
from appv2.runtimev2.transport import SseEvent
from tests.domains.test_v2_clarification import _ask, _scripted, _state, _step_payloads
from tests.domains.test_v2_four_phase import (
    V2_UNDERSTAND,
    V2LedgerPort,
    V2QueueEngine,
    V2RunStore,
    v2_ask_frames,
    v2_data_match,
    v2_decompose,
    v2_ledger_dump,
    v2_ledger_note,
    v2_matches,
    v2_registry,
    v2_resume,
    v2_run,
    v2_runtime,
)
from tests.domains.test_v2_react_loop import _rows_outcome

# ── 机读探针 ────────────────────────────────────────────────────────────────

_CALIBER_PROMPT = "「含水率」按哪一口径支判断？"
_CALIBER_OPTIONS = ("A 计量折算（日度监控）", "B 化验实测（月度/正式）")


def _ask_payload(prompt: str, options: tuple[str, ...]) -> str:
    """模型 `ask` 发射 JSON（同 `test_v2_clarification._ask` 形，本件带自定义选项）。"""
    return json.dumps(
        {"action": "ask", "ask": {"prompt": prompt, "options": list(options)}},
        ensure_ascii=False,
    )


def _ask_count_of(state: RunState) -> int:
    """连续反问计数（同 `clarification.core._ask_count` 口径——计数载体＝携 ask 帧的步记录）。"""
    return len(
        [payload for payload in _step_payloads(state) if payload.get(PAYLOAD_ASK_FRAME)]
    )


def _degrade_payloads(state: RunState) -> list[Mapping[str, Any]]:
    """降级步 payload 序列（机读信号面）。"""
    return [payload for payload in _step_payloads(state) if PAYLOAD_DEGRADED in payload]


# ══════════════════════════════════════════════════════════════════════════════
# 1｜ask 结构化：`detail.slot` additive（零帧闭世界变更）
# ══════════════════════════════════════════════════════════════════════════════


def test_v118_state_fields_additive_default_empty() -> None:
    """三字段 additive：默认空＝零漂移；指纹单点纯函数（同（槽位，选项集）→ 同指纹）。"""
    state = RunState()
    assert state.answer_slots == {}
    assert state.asked_fingerprints == []
    assert state.degraded_slots == {}
    assert ask_fingerprint("caliber", ("A", "B")) == ask_fingerprint("caliber", ("A", "B"))
    assert ask_fingerprint("caliber", ("A", "B")) != ask_fingerprint("caliber", ("B", "A"))
    assert ask_fingerprint("caliber", ("A", "B")) != ask_fingerprint("window", ("A", "B"))


def test_v118_ask_frame_detail_slot_additive_zero_frame_change() -> None:
    """验收 3｜ask 帧**顶层四键零增删**（`transport._check_ask` 恰四键把守）＋`detail` 携槽位标签。

    既有 transport 判据逐字在场（构造 `SseEvent(event="ask", ...)` 照常成功——`detail` 内键集
    归发射方）；标签值 ∈ 槽位闭世界三值。
    """
    state = _state()
    with _scripted(_ask(_CALIBER_PROMPT, _CALIBER_OPTIONS)):
        outcome = clarify(state)
    assert isinstance(outcome, ClarifyAsk)
    frame = state.pending_ask
    assert isinstance(frame, Mapping)
    assert set(frame) == {"kind", "prompt", "options", "detail"}  # 顶层四键零增删
    assert frame["detail"] == {ASK_DETAIL_SLOT_KEY: ASK_SLOT_CLARIFY}
    assert ASK_SLOT_CLARIFY in {ASK_SLOT_CLARIFY, ASK_SLOT_CALIBER, ASK_SLOT_WINDOW}
    # 帧面照旧可发（transport 恰四键把守＋载荷透传：detail 内键不改写）
    event = SseEvent(seq=0, event="ask", data={"frame": dict(frame), "run_id": state.run_id})
    assert event.data["frame"]["detail"] == {ASK_DETAIL_SLOT_KEY: ASK_SLOT_CLARIFY}


# ══════════════════════════════════════════════════════════════════════════════
# 2｜回答由程序落位＋回喂行带槽位（端到端：挂起→resume→程序落位→回喂行入链）
# ══════════════════════════════════════════════════════════════════════════════


async def test_v118_answer_placed_by_program_and_hint_line_carries_slot() -> None:
    """验收 1 半面｜用户回答经恢复腿落进 `state.answer_slots[slot]`，并以带槽位回喂行入模型窗。

    剧本：模型先问「「含水率」按哪一口径支判断？」（帧 `detail.slot=clarify`）→ 挂起 → resume
    选「A 计量折算（日度监控）」→ 程序落位 → 下一决策轮增量条携逐字回喂行
    「用户已回答『clarify』＝A 计量折算（日度监控）——请据此继续，不要重复提问。」→ 分解收口。
    """
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    ask = _ask_payload(_CALIBER_PROMPT, _CALIBER_OPTIONS)
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            ask,
            v2_decompose(
                subtask_id="s1",
                question="2025-09-01 到 09-03 各井日产油量",
                ledger_notes=note,
                chain="data",
            ),
            v2_matches(
                v2_data_match(
                    subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03"
                )
            ),
        ],
        "answer": ["答案：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    engine = V2QueueEngine([_rows_outcome()])
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(script=script, registry=v2_registry(engine=engine))
        events = await v2_run(runtime, "含水率是否超过阈值？")
        asks = v2_ask_frames(events)
        assert asks and asks[-1]["frame"]["kind"] == "clarify"
        assert asks[-1]["frame"]["detail"] == {ASK_DETAIL_SLOT_KEY: ASK_SLOT_CLARIFY}
        run_id = asks[-1]["run_id"]
        suspended = V2RunStore().load(run_id)
        assert suspended.answer_slots == {}  # 挂起时零落位（未回答不冒充已回答）
        choice = _CALIBER_OPTIONS[0]
        _resumed, _handle = await v2_resume(
            runtime, run_id, V2AskChoice(kind="clarify", choice=choice)
        )
    state = V2RunStore().load(run_id)
    # ① 程序落位（槽位标签 → 状态位）
    assert state.answer_slots == {ASK_SLOT_CLARIFY: choice}
    assert state.pending_ask is None
    # ② 回喂行带槽位（逐字稿）——入第二决策调用的模型窗
    expected_line = _HINT_SLOT_LINE.format(slot=ASK_SLOT_CLARIFY, value=choice)
    assert expected_line == (
        f"用户已回答『{ASK_SLOT_CLARIFY}』＝{choice}——请据此继续，不要重复提问。"
    )
    calls = completer.messages_of("decision")
    assert len(calls) >= 2
    assert any(
        message.get("role") == "user" and expected_line in str(message.get("content"))
        for message in calls[1]
    )
    # ③ 同问未被重抛（本轮零新挂起帧、零降级）
    assert state.asked_fingerprints == [ask_fingerprint(ASK_SLOT_CLARIFY, _CALIBER_OPTIONS)]
    assert state.degraded_slots == {}
    assert state.pending_ask is None


# ══════════════════════════════════════════════════════════════════════════════
# 3｜同问指纹：同一（slot，选项集）问过一次即不再问
# ══════════════════════════════════════════════════════════════════════════════


def test_v118_same_slot_second_ask_not_repeated() -> None:
    """验收 2｜同问重复计数＝0：同一（槽位，选项集）第二次发射 ⇒ 不重抛（降级路径，零新挂起帧）。

    `state.asked_fingerprints` 恰一条（第二次不落第二枚指纹——降级不是「又问了一次」）；
    `pending_ask` 不被第二次覆盖（不重抛）；返回位不占（`None`——去向 `decision` 继续）。
    """
    state = _state()
    with _scripted(_ask(_CALIBER_PROMPT, _CALIBER_OPTIONS)):
        assert isinstance(clarify(state), ClarifyAsk)
    first_frame = dict(state.pending_ask)
    with _scripted(_ask(_CALIBER_PROMPT, _CALIBER_OPTIONS)):
        second = clarify(state)
    assert second is None  # 不占返回位（不重抛）
    assert state.pending_ask is None  # 同问被消费掉、**不重抛**新帧（零新挂起）
    assert state.asked_fingerprints == [ask_fingerprint(ASK_SLOT_CLARIFY, _CALIBER_OPTIONS)]
    assert _ask_count_of(state) == 1  # 只发射过一次（第二次不落 ask 帧步）
    assert len(_degrade_payloads(state)) == 1
    ask_frames = [p[PAYLOAD_ASK_FRAME] for p in _step_payloads(state) if PAYLOAD_ASK_FRAME in p]
    assert ask_frames == [first_frame]  # 挂起帧恰首问那一枚（零重抛）


def test_v118_same_question_degrades_to_default_with_note() -> None:
    """验收 1 半面｜对账仍不过 → 降级一次性默认＋注记（「用了默认口径」进答案的依据行在场）。

    默认值＝该问选项集首个选项（程序侧唯一可得的结构化候选）；注记行经增量条渲染
    （`_DEFAULT_LINE` 逐字）——答案据此注明「用了默认口径」。
    """
    state = _state()
    with _scripted(_ask(_CALIBER_PROMPT, _CALIBER_OPTIONS)):
        clarify(state)
    with _scripted(_ask(_CALIBER_PROMPT, _CALIBER_OPTIONS)):
        clarify(state)
    assert state.degraded_slots == {ASK_SLOT_CLARIFY: _CALIBER_OPTIONS[0]}
    degrade = _degrade_payloads(state)[-1][PAYLOAD_DEGRADED]
    assert degrade == {ASK_SLOT_CLARIFY: _CALIBER_OPTIONS[0]}
    line = _DEFAULT_LINE.format(slot=ASK_SLOT_CLARIFY, value=_CALIBER_OPTIONS[0])
    assert line == (
        f"用户未确认『{ASK_SLOT_CLARIFY}』——已用默认口径（{_CALIBER_OPTIONS[0]}）："
        "请在答案中注明这一点，不要重复提问。"
    )
    increment = assemble_decision_increment(state, phase=PHASE_CLARIFY)
    assert line in increment


def test_v118_degrade_path_does_not_consume_ask_cap() -> None:
    """Kimi 评审修正 2｜降级路径**不过 `_on_ask`**（不落 `PAYLOAD_ASK_FRAME` 步 ⇒
    `_ask_count` 不增）。

    构造 `ask_cap=2`：首问占 1；同问第二次发射若过挂起面即到顶截断（`ask_cap` 被占），
    降级路径则**继续决策**（零截断通知、零直答、计数恒 1）。
    """
    state = _state(budget=Budget(ask_cap=2))
    with _scripted(_ask(_CALIBER_PROMPT, _CALIBER_OPTIONS)):
        assert isinstance(clarify(state), ClarifyAsk)
    with _scripted(_ask(_CALIBER_PROMPT, _CALIBER_OPTIONS)):
        assert clarify(state) is None
    assert _ask_count_of(state) == 1  # 降级不占 ask_cap
    assert [item["type"] for item in state.notices] == []  # 零到顶截断通知
    assert state.answer == "" and state.draft == ""  # 零直答收口（继续决策）


def test_v118_q16_shape_offline_only_one_ask_no_repeat() -> None:
    """验收 1｜`Q16` 形离线复现：同一口径问**只问一次**；其后每次同问都走降级、**不再重抛**。

    真机 `Q16` 病灶链（`eval/suite-147/results/frames/EB11-C-Q16.json`）：口径问 → 答 → 对账
    不过 r1／r2 被拒 → 分解成功 → **同一口径问再抛** → 答 → … 四轮同问。本件以同一（槽位，
    选项集）连发三次复现「同问重复」场景：发射恰一次、挂起帧恰一枚、降级槽位恰一枚、
    同问重复计数＝0。
    """
    state = _state()
    with _scripted(_ask(_CALIBER_PROMPT, _CALIBER_OPTIONS)):
        assert isinstance(clarify(state), ClarifyAsk)
    ask_frames = [p[PAYLOAD_ASK_FRAME] for p in _step_payloads(state) if PAYLOAD_ASK_FRAME in p]
    assert len(ask_frames) == 1  # 只问一次
    for _ in range(2):  # 其后每次同问：降级、不重抛
        with _scripted(_ask(_CALIBER_PROMPT, _CALIBER_OPTIONS)):
            assert clarify(state) is None
    assert _ask_count_of(state) == 1  # 同问重复计数＝0
    # 每次同问都如实落一条降级步（留痕不静默）；但槽位默认值幂等（不新增槽位、不换默认）
    assert len(_degrade_payloads(state)) == 2
    assert state.degraded_slots == {ASK_SLOT_CLARIFY: _CALIBER_OPTIONS[0]}
    assert state.pending_ask is None  # 同问不再挂起（零重抛）
    after = [p[PAYLOAD_ASK_FRAME] for p in _step_payloads(state) if PAYLOAD_ASK_FRAME in p]
    assert after == ask_frames  # 挂起帧恰首问那一枚（零重抛）


def test_v118_distinct_question_same_slot_still_asks() -> None:
    """保留集｜同槽位**换问法**（选项集不同）照问——指纹按（槽位，选项集）逐字算，不猜等价。"""
    state = _state()
    with _scripted(_ask(_CALIBER_PROMPT, _CALIBER_OPTIONS)):
        assert isinstance(clarify(state), ClarifyAsk)
    other_options = ("A 计量折算", "B 化验实测", "C 台账默认")
    with _scripted(_ask(_CALIBER_PROMPT, other_options)):
        assert isinstance(clarify(state), ClarifyAsk)
    assert state.asked_fingerprints == [
        ask_fingerprint(ASK_SLOT_CLARIFY, _CALIBER_OPTIONS),
        ask_fingerprint(ASK_SLOT_CLARIFY, other_options),
    ]
    assert _ask_count_of(state) == 2
    assert state.degraded_slots == {}
