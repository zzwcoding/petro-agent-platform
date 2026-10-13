"""V2-79a 对话状态三层分离验收钉测（ADR-0006 修订——dialogue/process_notes 双字段
＋compile 新契约＋播种最小形；总方案 tickets/v2/V2-79-对话状态重构方案.md §5）。

票面验收逐条落钉（tickets/v2/V2-79a-对话状态三层分离核心票.md）：
- 对话层纯度：决策轮上下文＝[system]＋dialogue（只有 user 原话）＋当前轮——任务书/
  决策 JSON/执行台账不再进模型上下文（V2-79 拆除的三大反模式）；
- 台账承载面：执行台账（「参数 → 结果：N 行／分型拒因」五形）落 process_notes
  （P-032b C2 分型措辞零漂移——承载面改，文案不改）；
- 追问播种最小形：追问 run 的 dialogue＝[前轮问, 前轮答]＋本轮问（runs 行权威字段，
  不读 checkpoint；V2-79b 升级 checkpoint 级全量传承）；
- 同参重投场景对照：改参发射照常执行，零 V2-37 闸触发（闸兜底语义零漂移）；
- token 截断策略钉测：超预算显式注记进 Manifest.selected_reason（首问轮与最新轮
  保留——确定性截断；摘要化随 V2-79d）。

行为断言锁在编译消息形态（ScriptedCompleter.messages_of 观测面）、黑匣子蒸馏记录
（RunStore.get_blackbox——dialogue/process_notes 终态投影）与决策出口，不锁模型原话。
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
from appv2.runtime.graph import _tool_note
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


# ---------- 验收①：对话层纯度——决策轮上下文零过程记录（反模式拆除钉） ----------


async def test_decision_context_carries_dialogue_only(
    tmp_path: Path,
) -> None:
    """r1 决策（execute data）→执行→r2 决策（finalize）：两轮决策上下文均为
    [system]＋dialogue（只有 user 原话）＋当前轮——第 1 轮决策 JSON/执行台账/理解
    原话不再进模型上下文（V2-79 拆除「过程记录以助手轮在史」反模式）；上下文长度
    跨轮恒定（过程不膨胀上下文）；台账/决策摘要落 process_notes（黑匣子蒸馏面）。"""
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
        # 两轮决策上下文形态恒定：system＋对话层（user 原话）＋当前轮——无任务书、
        # 无理解原话、无决策 JSON、无台账轮（三层分离）。
        for messages in (first, second):
            assert messages[0]["role"] == "system"
            assert len(messages) == 3
            assert messages[1] == {"role": "user", "content": QUESTION_A}
            assert "【待解构的题干】" not in messages[1]["content"]
        assert DECISION_WINDOWED not in _joined(second)
        assert "data_query 参数：" not in _joined(second)
        assert "问 2025 年 9 月上旬的日产油量" not in _joined(second)
        # 台账/决策/理解/起草/核验全进过程档案（黑匣子蒸馏投影终态）。
        record = await store.get_blackbox(handle.run_id)
        assert record is not None
        phases = [n.get("phase") for n in record.get("process_notes") or []]
        assert {"understand", "decision", "tool", "draft", "verify"} <= set(phases)
        tool_notes = [
            n for n in record.get("process_notes") or [] if n.get("phase") == "tool"
        ]
        assert len(tool_notes) == 1
        assert "→ 结果：2 行" in tool_notes[0]["digest"]  # 1 权威行＋1 随行血缘卡
        # 收口终稿落对话层（唯一写手——收口答案含引用块）。
        dialogue = record.get("dialogue") or []
        assert len(dialogue) == 2
        assert dialogue[0] == {"role": "user", "content": QUESTION_A}
        assert dialogue[1]["role"] == "assistant"
        assert "21.16" in dialogue[1]["content"] and "引用：" in dialogue[1]["content"]
    finally:
        await db.dispose()


# ---------- 验收②：闸拒负信息钉测——台账分型措辞进过程档案（C2 分型） ----------


async def test_bad_args_ledger_wording_is_validation_reject_not_gate(
    tmp_path: Path,
) -> None:
    """C2 分型钉（P-032b）：bad_args（参数校验未过——引擎未执行）执行台账措辞
    ＝「校验拒（拒因：…）」，不标「闸拒」（闸拒仅指引擎 refused 面——措辞如实
    分型，模型不把可修参路径读成永久数据闸）；拒因回喂 instruction 行与机读
    notice 面既有语义零漂移；台账承载面＝process_notes（黑匣子蒸馏面）。"""
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
        # 拒因回喂 instruction 行（既有语义零漂移）。
        second = completer.messages_of("v2.runtime.decision")[1]
        assert "上次决策被拒" in second[-1]["content"]
        # 对话层零台账轮（承载面改造）。
        assert "data_query 参数：" not in _joined(second)
        # 台账措辞在过程档案（分型逐字——bad_args＝「校验拒（拒因：…）」）。
        record = await store.get_blackbox(handle.run_id)
        assert record is not None
        tool_notes = [
            n for n in record.get("process_notes") or [] if n.get("phase") == "tool"
        ]
        assert len(tool_notes) == 1
        assert "→ 校验拒（拒因：" in tool_notes[0]["digest"]
        assert "不在指标台账" in tool_notes[0]["digest"]
        assert "闸拒" not in tool_notes[0]["digest"]
        # 机读 notice 面不回退（decision_rejected 分型在案）。
        assert [
            n for n in _notices(events) if n.get("type") == "decision_rejected"
        ]
    finally:
        await db.dispose()


def test_tool_note_wording_is_typed_by_error_category() -> None:
    """C2 分型钉（P-032b）：_tool_note 按 ToolError 三分类如实分型——
    bad_args＝「校验拒（拒因）」（校验未过引擎未执行）、retryable＝「暂不可用
    （拒因）」（可恢复）、refused＝「闸拒（拒因）」（闸拒仅指本面）；ok/ask
    两形原样（结果 N 行／挂起审批）。承载面＝process_notes 条目（phase/title/
    digest），文案与旧 _ledger_turn 逐字同源。"""
    args = {"metric_slot": "日产油量", "window_start": "2025-09-01"}
    ok = _tool_note("data_query", args, {
        "status": "ok", "observations": [{}, {}], "ask": None, "error": None,
    })
    assert ok["phase"] == "tool" and ok["title"] == "data_query：ok"
    assert ok["digest"] == (
        'data_query 参数：{"metric_slot":"日产油量","window_start":"2025-09-01"}'
        " → 结果：2 行"
    )
    ask = _tool_note("data_query", args, {
        "status": "ask", "observations": [], "ask": {"kind": "clarify"},
        "error": None,
    })
    assert "→ 结果：0 行（挂起：审批）" in ask["digest"]
    bad_args = _tool_note("data_query", args, {
        "status": "failed", "observations": [], "ask": None,
        "error": {"category": "bad_args", "message": "不在指标台账", "hint": ""},
    })
    assert "→ 校验拒（拒因：不在指标台账）" in bad_args["digest"]
    assert "闸拒" not in bad_args["digest"]
    retryable = _tool_note("data_query", args, {
        "status": "failed", "observations": [], "ask": None,
        "error": {"category": "retryable", "message": "上游超时", "hint": ""},
    })
    assert "→ 暂不可用（拒因：上游超时）" in retryable["digest"]
    assert "闸拒" not in retryable["digest"]
    refused = _tool_note("data_query", args, {
        "status": "failed", "observations": [], "ask": None,
        "error": {"category": "refused", "message": "越权口径", "hint": ""},
    })
    assert "→ 闸拒（拒因：越权口径）" in refused["digest"]


def test_note_digest_is_bounded() -> None:
    """过程档案有界纪律单点（V2-79a）：digest >200 字截断（写入点截断——
    方案 §3.2「每条 ≤200 字」）。"""
    note = _note_of_digest("长" * 500)
    assert len(note["digest"]) == 200


def _note_of_digest(digest: str) -> dict[str, str]:
    from appv2.runtime.graph import _note

    return _note("test", "测试", digest)


def test_legacy_history_field_is_dead_but_present() -> None:
    """v1 checkpoint 兼容死字段（V2-79a）：RunState 仍带 history 键（零读写）——
    旧快照（含 history 通道）读入不炸的 schema 面；schema_version=2 为新旧判据
    （方案 §4.1 版本化）；V2-79e 清账删除时本钉随之改写。"""
    assert "history" in RunState.__dataclass_fields__
    assert "dialogue" in RunState.__dataclass_fields__
    assert "process_notes" in RunState.__dataclass_fields__
    assert RunState().schema_version == 2
    assert RunState().history == []  # 死字段零写——新路径无人落值


# ---------- 验收③：追问播种最小形——对话层承载前轮问答 ----------


async def test_followup_context_carries_prior_qa_history(tmp_path: Path) -> None:
    """前轮 completed 后追问（followup_of）：新 run 的 understand 上下文＝
    [system]＋dialogue（[前轮问 user 轮, 前轮答 assistant 轮]）＋当前任务书——
    会话线程承接以自然对话形承载（V2-79a 最小形：runs 行权威字段，不读
    checkpoint）；前轮决策 JSON/执行台账不再播种（过程记录退出对话层——V2-79
    拆除的模仿面；checkpoint 级全量传承随 V2-79b）。"""
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
        # 追问 run 的 understand 消息形态：system＋前轮问＋前轮答＋当前任务书
        # （对话层自然序——「我刚刚问了什么」类问题模型可直读）。
        understand_msgs = completer_b.messages_of("v2.runtime.understand")[0]
        assert understand_msgs[0]["role"] == "system"
        assert understand_msgs[1] == {"role": "user", "content": QUESTION_A}
        assert understand_msgs[2]["role"] == "assistant"
        assert "21.16" in understand_msgs[2]["content"]
        assert "引用：" in understand_msgs[2]["content"]
        # 追问问句以当前轮任务书尾随（【待解构的题干】）＋对话层 user 轮双面在场。
        joined = _joined(understand_msgs)
        assert "那 N-01 井 9 月 2 日的日产油量呢？" in joined
        # 「上轮答案：」伪标注永不出现（对话纯度红线）。
        assert "上轮答案：" not in joined
        # 前轮决策 JSON／执行台账退出播种面（过程记录不再进对话层——V2-79b
        # 才升 checkpoint 级全量传承，本钉显式锁 79a 最小形边界）。
        decision_msgs = completer_b.messages_of("v2.runtime.decision")[0]
        joined_d = _joined(decision_msgs)
        assert DECISION_WINDOWED not in joined_d
        assert "data_query 参数：" not in joined_d
        assert not [n for n in _notices(events_b) if n.get("type") == "run_failed"]
    finally:
        await db_b.dispose()


async def test_gate_refused_answer_visible_across_followup(tmp_path: Path) -> None:
    """闸拒负信息跨轮可见（拒答话术即终稿——对话层承载）：前轮执行被闸拒
    （拒因如实转答收口＝终稿），追问 run 的上下文含前轮拒答话术 assistant 轮
    （P-026 病灶「被拒尝试彻底消失」的跨轮反面钉）；台账行退出播种面（79a
    最小形——如实降级，V2-79b 随 checkpoint 传承补全）。"""
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
        # 追问 run 的决策上下文含前轮拒答话术 assistant 轮（负信息模型面可见）。
        decision_msgs = completer_b.messages_of("v2.runtime.decision")[0]
        joined = _joined(decision_msgs)
        assert "越权拒绝" in joined
        assert any(
            m["role"] == "assistant" and "越权拒绝" in m["content"]
            for m in decision_msgs
        )
        # 台账行退出播种面（79a 最小形边界显式钉——V2-79b 传承升级时改本钉）。
        assert "→ 闸拒（拒因：" not in joined
    finally:
        await db_b.dispose()


# ---------- 验收④：同参重投场景对照——改参发射照常执行，零 V2-37 闸触发 ----------


async def test_history_ledger_lets_model_change_param_without_gate(
    tmp_path: Path,
) -> None:
    """r1 执行出数（台账入过程档案）→r2 模型改参发射（剧本形）→照常执行，
    零 same_param_replay 闸触发；台账在过程档案有案（黑匣子蒸馏面）——同参
    防重的机器闸兜底语义零漂移。"""
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
        assert completer.counts()["v2.runtime.decision"] == 3
        # 两支执行台账都在过程档案（各一条——逐支累积）。
        record = await store.get_blackbox(handle.run_id)
        assert record is not None
        tool_notes = [
            n for n in record.get("process_notes") or [] if n.get("phase") == "tool"
        ]
        assert len(tool_notes) == 2
        assert all("→ 结果：2 行" in n["digest"] for n in tool_notes)
    finally:
        await db.dispose()


# ---------- 验收⑤：token 截断策略钉测（超预算显式注记进 Manifest） ----------


def _big_dialogue(turns: int) -> list[dict[str, str]]:
    """合成对话层（首问＋N 轮问答——触发预算截断的形）。"""
    dialogue = [{"role": "user", "content": "问题：合成首问（截断钉测）"}]
    for index in range(turns):
        dialogue.append({
            "role": "assistant",
            "content": f"第 {index} 轮回答：合成对话轮（截断钉测填充行——内容展开到"
                       f"足够长度以便预算起算）{'细节' * 20}",
        })
        dialogue.append({
            "role": "user",
            "content": f"第 {index} 轮追问：继续（截断钉测填充行）",
        })
    return dialogue


def test_compile_keeps_full_dialogue_within_budget() -> None:
    """预算内：全对话层续写（system＋全部对话轮＋当前轮），Manifest 无截断注记。"""
    builder = ContextBuilder(max_context_tokens=100000)
    state = RunState(question="合成首问（截断钉测）", dialogue=_big_dialogue(3))
    context = builder.compile(
        state, step="decision", instruction="任务：输出本轮决策 JSON。", with_material=True,
    )
    assert context.messages[0]["role"] == "system"
    assert len(context.messages) == 1 + len(state.dialogue) + 1
    assert context.messages[-1]["content"].startswith("任务：输出本轮决策 JSON。")
    assert "观察材料：" in context.messages[-1]["content"]
    assert "截断" not in context.manifest.selected_reason
    assert context.manifest.token_count == (
        sum(len(str(m["content"])) for m in context.messages) // 4
    )


def test_compile_truncates_dialogue_over_budget_with_manifest_note() -> None:
    """超预算：确定性截断（首问轮与最新轮保留、最旧中间轮先弃），截断显式注记进
    Manifest.selected_reason（对话层轮数前后账＋token 预算值），token_count 为
    截断后实量；当前轮不入对话层账（轮数只数 dialogue）。"""
    builder = ContextBuilder(max_context_tokens=600)
    state = RunState(question="合成首问（截断钉测）", dialogue=_big_dialogue(30))
    context = builder.compile(
        state, step="decision", instruction="任务：输出本轮决策 JSON。", with_material=False,
    )
    manifest = context.manifest
    # 显式注记进 Manifest（票面验收——超预算形态钉测）。
    assert "token 预算" in manifest.selected_reason
    assert "截断" in manifest.selected_reason
    assert f"对话层 {len(state.dialogue)} 轮" in manifest.selected_reason
    assert f"轮→{len(context.messages) - 2} 轮" in manifest.selected_reason  # 保留数对账
    # 截断形态：首问轮保留（对话源头）＋当前轮保留（本轮任务），中间最旧先弃。
    assert context.messages[1]["content"].startswith("问题：")
    assert context.messages[-1]["content"].startswith("任务：")
    assert len(context.messages) < 1 + len(state.dialogue) + 1
    # token_count＝截断后消息实量（chars/4 口径）。
    assert manifest.token_count == (
        sum(len(str(m["content"])) for m in context.messages) // 4
    )
    # 保留轮均为合法消息形（role 闭世界——user/assistant）。
    assert all(m["role"] in ("user", "assistant") for m in context.messages[1:-1])


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
        # 收口终稿落对话层（追问轮 dialogue＝前轮问＋前轮答＋本轮问＋本轮答）。
        record = await store_b.get_blackbox(handle_b.run_id)
        assert record is not None
        dialogue = record.get("dialogue") or []
        assert [t.get("role") for t in dialogue] == ["user", "assistant", "user", "assistant"]
        assert dialogue[0]["content"] == QUESTION_A
        assert dialogue[2]["content"] == "我刚问了什么问题？"  # 本轮追问原话
        assert "你上一轮问的是" in dialogue[3]["content"]  # 本轮终稿
    finally:
        await db_b.dispose()
