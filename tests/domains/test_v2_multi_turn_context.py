"""V2-38 多轮对话上下文验收钉测（ADR-0006——消息历史簿记＋执行台账段＋追问续会话
＋token 预算截断；Owner 2026-10-09 拍板）。

票面验收逐条落钉（tickets/v2/V2-38-多轮对话上下文.md）：
- 多轮钉测：第 2 轮决策上下文含第 1 轮决策 JSON＋执行台账（参数/结果）逐字可查；
- 闸拒负信息钉测：被拒执行在历史留分型拒因行，模型面可见（P-032b C2 分型如实：
  bad_args＝「校验拒（拒因）」非闸拒／refused＝「闸拒（拒因）」——bad_args 同
  run 内回喂面；refused 跨 run 面＝追问续会话钉测共担）；
- 追问钉测：追问进会话后上下文含前轮问答历史（前轮问句＋前轮终稿轮——V2-78 普通对话形）；
- 同参重投场景对照：有历史簿记后模型自主改参（剧本形），零 V2-37 闸触发；
- token 截断策略钉测：超预算显式注记进 Manifest.selected_reason（首问轮与当前
  轮保留——确定性截断）。

行为断言锁在消息历史形态（ScriptedCompleter.messages_of 观测面）与决策出口，
不锁模型原话；[n] 引标体系与 verify INV-1 语义零漂移（不在本文件断言面——
test_v2_agent_loop/test_v2_agent_verify 原钉守）。
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from appv2.query import (
    LINEAGE_KEY_CALIBER,
    LINEAGE_KEY_WATERMARK,
    LineageLine,
    QueryOutcome,
)
from appv2.runtime import (
    AskRequest,
    ContextBuilder,
    RunState,
    RunStore,
)
from appv2.runtime.graph import _ledger_turn
from appv2.tools import FakeQueryEngine
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    ANSWER_DRAFT_CITED,
    DECISION_FINALIZE,
    DECISION_WINDOWED,
    UNDERSTAND_DATA,
    QueueQueryEngine,
    drain,
    make_runtime,
)

# 改参罐头（同参对照钉测——换窗＝携新参，闸不拦）。
DECISION_WINDOWED_ALT = (
    '{"thought": "台账显示已查过 9 月 1 日——改窗取 9 月 2 日起", "action": "execute", '
    '"task_type": "data", "plan": {"metric_slot": "日产油量", "ranking": false, '
    '"window_start": "2025-09-02", "window_end": "2025-09-05", "limit": 5}}'
)
# 校验拒罐头（采出程度不在台账——bad_args 拒因回喂通道）。
DECISION_BAD_METRIC = (
    '{"action": "execute", "task_type": "data", '
    '"plan": {"metric_slot": "采出程度", "ranking": false, '
    '"window_start": "2025-09-01", "window_end": "2025-09-03"}}'
)

QUESTION_A = "2025 年 9 月 1 日到 3 日的日产油量"


def _rows_outcome() -> QueryOutcome:
    return QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
        lineage=(
            LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量（单位：吨）——口径声明"),
            LineageLine(key=LINEAGE_KEY_WATERMARK, value="汇总层水位 2026-08-31"),
        ),
    )


def _notices(events: list[Any]) -> list[dict[str, Any]]:
    return [e.data for e in events if e.event == "notice"]


def _joined(messages: list[dict[str, str]]) -> str:
    return "\n---\n".join(str(m.get("content", "")) for m in messages)


# ---------- 验收①：多轮钉测——第 2 轮决策上下文含第 1 轮决策 JSON＋执行台账 ----------


async def test_second_decision_context_carries_first_round_history(
    tmp_path: Path,
) -> None:
    """r1 决策（execute data）→执行→r2 决策（finalize）：第 2 轮决策的 messages
    含第 1 轮决策 JSON（assistant 轮逐字）＋执行台账轮（参数→结果：N 行逐字）——
    消息历史簿记的多轮形态（非每步全新两条消息）。"""
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_WINDOWED, DECISION_FINALIZE],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=QUESTION_A, actor=ACTOR))
        await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "21.16" in (run.answer or "")
        rounds = completer.messages_of("v2.runtime.decision")
        assert len(rounds) == 2
        first, second = rounds
        # 多轮形态：第 1 轮＝system＋首问轮＋理解轮（understand 调用与输出已入簿）
        # ＋当前轮；第 2 轮在完整历史上续写（更长）。
        assert first[0]["role"] == "system"
        assert len(first) == 4
        assert first[1]["role"] == "user"
        assert f"【待解构的题干】\n{QUESTION_A}" in first[1]["content"]
        assert first[2]["role"] == "assistant" and "理解" in first[2]["content"]
        assert len(second) == 7  # system＋首问＋理解＋r1 调用＋r1 输出＋台账＋当前轮
        assert second[0]["role"] == "system"
        # 首问轮逐字保留在历史（对话源头不丢）。
        assert any(
            m["role"] == "user" and f"【待解构的题干】\n{QUESTION_A}" in m["content"]
            for m in second
        )
        # 第 1 轮决策 JSON 逐字可查（assistant 轮＝模型当时输出的原话）。
        assert any(
            m["role"] == "assistant" and m["content"] == DECISION_WINDOWED
            for m in second
        )
        # 执行台账段逐字可查：「参数 → 结果：N 行」（参数含计划载荷原值）。
        ledgers = [
            m["content"]
            for m in second
            if m["role"] == "user" and "data_query 参数：" in m["content"]
        ]
        assert len(ledgers) == 1
        assert "日产油量" in ledgers[0] and "2025-09-01" in ledgers[0]
        assert "→ 结果：2 行" in ledgers[0]  # 1 权威行＋1 随行血缘卡
        # 理解产出也在历史（understand 调用与输出入簿）。
        assert any(
            m["role"] == "assistant" and "问 2025 年 9 月上旬的日产油量" in m["content"]
            for m in second
        )
    finally:
        await db.dispose()


# ---------- 验收②：闸拒负信息钉测——被拒执行留分型拒因行，模型面可见（C2 分型） ----------


async def test_bad_args_ledger_wording_is_validation_reject_not_gate(
    tmp_path: Path,
) -> None:
    """C2 分型钉（P-032b）：bad_args（参数校验未过——引擎未执行）执行台账行措辞
    ＝「校验拒（拒因：…）」，不标「闸拒」（闸拒仅指引擎 refused 面——措辞如实
    分型，模型不把可修参路径读成永久数据闸）；拒因回喂 instruction 行与机读
    notice 面既有语义零漂移。"""
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_BAD_METRIC, DECISION_FINALIZE],
        "v2.runtime.answer": ["观察材料未覆盖该问题，无法给出结论。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=FakeQueryEngine(), script=script,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=QUESTION_A, actor=ACTOR))
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        # 拒因回喂 instruction 行（既有语义零漂移）＋历史台账行（簿记面）。
        second = completer.messages_of("v2.runtime.decision")[1]
        assert "上次决策被拒" in second[-1]["content"]
        joined = _joined(second)
        assert "不在指标台账" in joined
        # 台账行是独立 user 轮：bad_args＝「校验拒（拒因：…）」，逐字不含「闸拒」。
        ledger_turns = [
            m for m in second
            if m["role"] == "user" and "data_query 参数：" in m["content"]
        ]
        assert len(ledger_turns) == 1
        assert "→ 校验拒（拒因：" in ledger_turns[0]["content"]
        assert "不在指标台账" in ledger_turns[0]["content"]
        assert "闸拒" not in ledger_turns[0]["content"]
        # 机读 notice 面不回退（decision_rejected 分型在案）。
        assert [
            n for n in _notices(events) if n.get("type") == "decision_rejected"
        ]
    finally:
        await db.dispose()


def test_ledger_turn_wording_is_typed_by_error_category() -> None:
    """C2 分型钉（P-032b）：_ledger_turn 按 ToolError 三分类如实分型——
    bad_args＝「校验拒（拒因）」（校验未过引擎未执行）、retryable＝「暂不可用
    （拒因）」（可恢复）、refused＝「闸拒（拒因）」（闸拒仅指本面）；ok/ask
    两形原样（结果 N 行／挂起审批）。"""
    args = {"metric_slot": "日产油量", "window_start": "2025-09-01"}
    ok = _ledger_turn("data_query", args, {
        "status": "ok", "observations": [{}, {}], "ask": None, "error": None,
    })
    assert ok["content"] == (
        'data_query 参数：{"metric_slot":"日产油量","window_start":"2025-09-01"}'
        " → 结果：2 行"
    )
    ask = _ledger_turn("data_query", args, {
        "status": "ask", "observations": [], "ask": {"kind": "clarify"},
        "error": None,
    })
    assert "→ 结果：0 行（挂起：审批）" in ask["content"]
    bad_args = _ledger_turn("data_query", args, {
        "status": "failed", "observations": [], "ask": None,
        "error": {"category": "bad_args", "message": "不在指标台账", "hint": ""},
    })
    assert "→ 校验拒（拒因：不在指标台账）" in bad_args["content"]
    assert "闸拒" not in bad_args["content"]
    retryable = _ledger_turn("data_query", args, {
        "status": "failed", "observations": [], "ask": None,
        "error": {"category": "retryable", "message": "上游超时", "hint": ""},
    })
    assert "→ 暂不可用（拒因：上游超时）" in retryable["content"]
    assert "闸拒" not in retryable["content"]
    refused = _ledger_turn("data_query", args, {
        "status": "failed", "observations": [], "ask": None,
        "error": {"category": "refused", "message": "越权口径", "hint": ""},
    })
    assert "→ 闸拒（拒因：越权口径）" in refused["content"]


# ---------- 验收③：追问钉测——追问进会话后上下文含前轮问答历史 ----------


async def test_followup_context_carries_prior_qa_history(tmp_path: Path) -> None:
    """前轮 completed 后追问（followup_of）：新 run 上下文含前轮问句轮＋前轮最终
    答案轮（V2-78 普通对话形）——会话线程承接，run 状态机零改动（追问＝新 run 行）。"""
    script_a: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_WINDOWED, DECISION_FINALIZE],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    runtime_a, _completer_a, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_a,
    )
    store = RunStore(db)
    run_id_a = ""
    try:
        handle_a = await runtime_a.ask(AskRequest(question=QUESTION_A, actor=ACTOR))
        await drain(handle_a)
        run_a = await store.get_run(handle_a.run_id)
        assert run_a is not None and run_a.status == "completed"
        assert "21.16" in (run_a.answer or "")
        run_id_a = handle_a.run_id
    finally:
        await db.dispose()

    script_b: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_WINDOWED, DECISION_FINALIZE],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    runtime_b, completer_b, db_b = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_b,
    )
    store_b = RunStore(db_b)
    try:
        handle_b = await runtime_b.ask(
            AskRequest(
                question="那 N-01 井 9 月 2 日的日产油量呢？",
                actor=ACTOR,
                followup_of=run_id_a,
            )
        )
        events_b = await drain(handle_b)
        run_b = await store_b.get_run(handle_b.run_id)
        assert run_b is not None and run_b.status == "completed"
        assert "21.16" in (run_b.answer or "")
        # 追问 run 的 understand 消息含前轮问答历史：
        # ①前轮问句轮逐字；②前轮最终答案轮（终稿以普通 assistant 轮落——含值与引用块）。
        understand_msgs = completer_b.messages_of("v2.runtime.understand")[0]
        joined = _joined(understand_msgs)
        assert f"【待解构的题干】\n{QUESTION_A}" in joined
        # V2-78：「上轮答案：」伪标注轮不再播种（assistant 消息里的系统注记被模型
        # 照抄进回答＋逐轮累积——真机复现实锤）；前轮终稿＝普通对话轮。
        assert "上轮答案：" not in joined
        assert "21.16" in joined and "引用：" in joined
        # 前轮决策 JSON／执行台账同样随线程可见（多轮簿记跨 run 延续）。
        decision_msgs = completer_b.messages_of("v2.runtime.decision")[0]
        joined_d = _joined(decision_msgs)
        assert DECISION_WINDOWED in joined_d
        assert "data_query 参数：" in joined_d and "→ 结果：" in joined_d
        # 追问问句本身以新一轮入上下文（续写形态）。
        assert any(
            m["role"] == "user" and "那 N-01 井 9 月 2 日的日产油量呢？" in m["content"]
            for m in understand_msgs
        )
        assert not [n for n in _notices(events_b) if n.get("type") == "run_failed"]
    finally:
        await db_b.dispose()


async def test_gate_refused_line_visible_across_followup(tmp_path: Path) -> None:
    """闸拒（refused——真闸拒通道）负信息跨轮可见：前轮执行被闸拒（拒因如实转答
    收口），追问 run 的上下文含「闸拒（拒因：…）」行——模型面在续会话中仍能读到
    被拒事实（P-026 病灶「被拒尝试彻底消失」的跨轮反面钉）。"""
    script_a: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_WINDOWED],
    }
    runtime_a, _completer_a, db = await make_runtime(
        tmp_path,
        engine=FakeQueryEngine(run_error=PermissionError("越权口径：无据出数")),
        script=script_a,
    )
    store = RunStore(db)
    run_id_a = ""
    try:
        handle_a = await runtime_a.ask(AskRequest(question=QUESTION_A, actor=ACTOR))
        await drain(handle_a)
        run_a = await store.get_run(handle_a.run_id)
        assert run_a is not None and run_a.status == "completed"
        assert "越权拒绝" in (run_a.answer or "")
        run_id_a = handle_a.run_id
    finally:
        await db.dispose()

    script_b: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_FINALIZE],
    }
    runtime_b, completer_b, db_b = await make_runtime(
        tmp_path, engine=FakeQueryEngine(), script=script_b,
    )
    try:
        handle_b = await runtime_b.ask(
            AskRequest(
                question="换口径再问一次：2025 年 9 月 1 日到 3 日的日产液量",
                actor=ACTOR,
                followup_of=run_id_a,
            )
        )
        await drain(handle_b)
        # 追问 run 的决策上下文含前轮「闸拒（拒因）」行（负信息模型面可见）。
        decision_msgs = completer_b.messages_of("v2.runtime.decision")[0]
        joined = _joined(decision_msgs)
        assert "→ 闸拒（拒因：" in joined
        assert "越权拒绝" in joined
    finally:
        await db_b.dispose()


# ---------- 验收④：同参重投场景对照——有历史后模型自主改参，零 V2-37 闸触发 ----------


async def test_history_ledger_lets_model_change_param_without_gate(
    tmp_path: Path,
) -> None:
    """r1 执行出数（台账落「参数 → 结果：N 行」）→r2 模型读到台账后自主改参
    （剧本形）→照常执行，零 same_param_replay 闸触发（V2-37 降格兜底的对照钉）。"""
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [
            DECISION_WINDOWED, DECISION_WINDOWED_ALT, DECISION_FINALIZE,
        ],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    engine = QueueQueryEngine([_rows_outcome(), _rows_outcome()])
    runtime, completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=QUESTION_A, actor=ACTOR))
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "21.16" in (run.answer or "")
        assert engine.run_calls == 2  # 改参发射照常执行（两轮各一次）
        assert not [n for n in _notices(events) if n.get("type") == "same_param_replay"]
        # r2 的上下文含 r1 决策 JSON＋r1 执行台账——模型「看得见自己做过的事」，
        # 同参避免由历史簿记承载（闸不再需要出场）。
        second = completer.messages_of("v2.runtime.decision")[1]
        joined = _joined(second)
        assert DECISION_WINDOWED in joined
        assert "data_query 参数：" in joined and "→ 结果：" in joined
        assert completer.counts()["v2.runtime.decision"] == 3
    finally:
        await db.dispose()


# ---------- 验收⑤：token 截断策略钉测（超预算显式注记进 Manifest） ----------


def _big_history(turns: int) -> list[dict[str, str]]:
    """合成历史（首问＋N 轮决策/台账——触发预算截断的形）。"""
    history = [{"role": "user", "content": "问题：合成首问（截断钉测）"}]
    for index in range(turns):
        history.append({
            "role": "user",
            "content": f"data_query 参数：{{\"window_start\":\"2025-01-{index:02d}\"}} "
                       f"→ 结果：若干行（第 {index} 轮执行台账——截断钉测填充行）",
        })
        history.append({
            "role": "assistant",
            "content": f'{{"action": "execute", "task_type": "data", "round": {index}}}',
        })
    return history


def test_compile_keeps_full_history_within_budget() -> None:
    """预算内：全历史续写（system＋全部历史轮＋当前轮），Manifest 无截断注记。"""
    builder = ContextBuilder(max_context_tokens=100000)
    state = RunState(question="合成首问（截断钉测）", history=_big_history(3))
    context = builder.compile(
        state, step="decision", instruction="任务：输出本轮决策 JSON。", with_material=True,
    )
    assert context.messages[0]["role"] == "system"
    assert len(context.messages) == 1 + len(state.history) + 1
    assert context.messages[-1]["content"].startswith("任务：输出本轮决策 JSON。")
    assert "观察材料：" in context.messages[-1]["content"]
    assert "截断" not in context.manifest.selected_reason
    assert context.manifest.token_count == (
        sum(len(str(m["content"])) for m in context.messages) // 4
    )


def test_compile_truncates_history_over_budget_with_manifest_note() -> None:
    """超预算：确定性截断（首问轮与当前轮保留、最旧中间轮先弃），截断显式注记进
    Manifest.selected_reason（轮数前后账＋token 预算值），token_count 为截断后实量。"""
    builder = ContextBuilder(max_context_tokens=600)
    state = RunState(question="合成首问（截断钉测）", history=_big_history(30))
    context = builder.compile(
        state, step="decision", instruction="任务：输出本轮决策 JSON。", with_material=False,
    )
    manifest = context.manifest
    # 显式注记进 Manifest（票面验收——超预算形态钉测）。
    assert "token 预算" in manifest.selected_reason
    assert "截断" in manifest.selected_reason
    assert f"{len(state.history) + 1} 轮" in manifest.selected_reason  # 轮数账（历史＋当前轮）
    assert f"轮→{len(context.messages) - 1} 轮" in manifest.selected_reason  # 保留数对账
    # 截断形态：首问轮保留（对话源头）＋当前轮保留（本轮任务），中间最旧先弃。
    assert context.messages[1]["content"].startswith("问题：")
    assert context.messages[-1]["content"].startswith("任务：")
    assert len(context.messages) < 1 + len(state.history) + 1
    # token_count＝截断后消息实量（chars/4 口径）。
    assert manifest.token_count == (
        sum(len(str(m["content"])) for m in context.messages) // 4
    )
    # 保留轮均为合法消息形（role 闭世界——user/assistant）。
    assert all(m["role"] in ("user", "assistant") for m in context.messages[1:])


async def test_followup_zero_material_finalizes_as_not_found(tmp_path: Path) -> None:
    """V2-72 b 案钉（V2-77 演进）：追问旁路保留（零探查定稿不拒回——直答能力
    不动），起草段对追问轮放开（历史可答面）后，模型仍可依历史起草；本钉钉
    「模型放弃起草（空答案腿）」的兜底面——零实质材料收口＝如实说明无依据
    （V2-77 C 项人话文案，不以 no_hit 文本冒充答案面）＋decision_note 机读
    notice 随行；有实质材料的追问零漂移（execute 形见上一钉）。"""
    script_a: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_WINDOWED, DECISION_FINALIZE],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    runtime_a, _completer_a, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_a,
    )
    run_id_a = ""
    try:
        handle_a = await runtime_a.ask(AskRequest(question=QUESTION_A, actor=ACTOR))
        await drain(handle_a)
        run_id_a = handle_a.run_id
    finally:
        await db.dispose()

    # 追问零探查（decision 直接收稿定稿）＋零执行；模型放弃起草（空答案腿）
    # ——兜底壳面（历史也覆盖不了时的如实说明形）。
    script_b: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_FINALIZE],
        "v2.runtime.answer": [""],
    }
    runtime_b, _completer_b, db_b = await make_runtime(
        tmp_path, engine=QueueQueryEngine([]), script=script_b,
    )
    store_b = RunStore(db_b)
    try:
        handle_b = await runtime_b.ask(
            AskRequest(question="那递减风险呢？", actor=ACTOR, followup_of=run_id_a)
        )
        events_b = await drain(handle_b)
        run_b = await store_b.get_run(handle_b.run_id)
        assert run_b is not None and run_b.status == "completed"
        answer = run_b.answer or ""
        assert answer.startswith("这个问题在本对话的材料和前轮问答里都没有找到依据")
        assert "不能编造答案" in answer
        notes = [n for n in _notices(events_b) if n.get("type") == "decision_note"]
        assert any("无依据" in str(n.get("content", "")) for n in notes)
    finally:
        await db_b.dispose()


async def test_followup_history_answerable_drafts_not_shell(tmp_path: Path) -> None:
    """V2-77 A 项钉（Owner 2026-10-13）：追问零实质材料时历史可答——起草段对
    追问轮放开（followup_of 例外），模型依前轮问答史起草的答案原样交付（零材料
    面不核验改写），不得空手落兜底壳（新文案也不得出现）。"""
    script_a: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_WINDOWED, DECISION_FINALIZE],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    runtime_a, _completer_a, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_a,
    )
    run_id_a = ""
    try:
        handle_a = await runtime_a.ask(AskRequest(question=QUESTION_A, actor=ACTOR))
        await drain(handle_a)
        run_id_a = handle_a.run_id
    finally:
        await db.dispose()

    # 追问轮：零探查 finalize（追问旁路放行）＋历史可答草稿——复述前轮问句
    # （草稿含数字也无碍——零材料面走 state.draft 直通，不经断言核验改写）。
    history_draft = f"你上一轮问的是：「{QUESTION_A}」。"
    script_b: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_FINALIZE],
        "v2.runtime.answer": [history_draft],
    }
    runtime_b, completer_b, db_b = await make_runtime(
        tmp_path, engine=QueueQueryEngine([]), script=script_b,
    )
    store_b = RunStore(db_b)
    try:
        handle_b = await runtime_b.ask(
            AskRequest(question="我刚问了什么问题？", actor=ACTOR, followup_of=run_id_a)
        )
        events_b = await drain(handle_b)
        run_b = await store_b.get_run(handle_b.run_id)
        assert run_b is not None and run_b.status == "completed"
        answer = run_b.answer or ""
        assert "你上一轮问的是" in answer and QUESTION_A in answer  # 历史复述原样交付
        assert "没有找到依据" not in answer  # 兜底壳不得出现（历史可答面）
        # 起草指令带 V2-77 追问条款（历史合法来源面——模型可见）。
        answer_msgs = completer_b.messages_of("v2.runtime.answer")[0]
        assert "本轮是会话追问" in "\n".join(
            str(m.get("content", "")) for m in answer_msgs
        )
        assert not [n for n in _notices(events_b) if n.get("type") == "decision_note"]
    finally:
        await db_b.dispose()
