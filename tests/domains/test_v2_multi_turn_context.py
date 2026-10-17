"""对话上下文验收钉测（V2-79a 三层分离 → V2-80h 对话链追加式改写——本文件
各钉已按链形更新：对话链（messages，只追加）即上下文，compile 已退役）。

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
    AskChoice,
    AskRequest,
    ContextBuilder,
    RunState,
    RunStore,
)
from appv2.runtime.executor import extract_dialogue_from_legacy_history
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
from tests.domains.test_v2_four_phase import (
    V2_ACTOR,
    V2_UNDERSTAND,
    V2LedgerPort,
    V2QueueEngine,
    V2RunStore,
    v2_data_match,
    v2_decompose,
    v2_ledger_dump,
    v2_ledger_note,
    v2_matches,
    v2_registry,
    v2_run,
    v2_runtime,
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


async def test_decision_chain_prefix_extends_across_rounds(
    tmp_path: Path,
) -> None:
    """V2-80h 追加链（79a「对话层纯度」的演进形——本钉改写）：r1 决策→执行→
    r2 决策两轮上下文＝前缀延伸（相邻调用互为前缀——KV 缓存本源形态）；r1 决策
    JSON 以 assistant 轮、已做段以 user 轮在链（模型可见自己的历史输出）；执行
    台账照旧落 process_notes（黑匣子蒸馏面——承载面不变）。"""
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
        # r1 链形：system／任务书（嵌原话）／理解应答／指南包／已做段。
        assert first[0]["role"] == "system"
        assert [m["role"] for m in first] == [
            "system", "user", "assistant", "user", "user",
        ]
        assert QUESTION_A in first[1]["content"]
        assert "任务：输出本轮决策 JSON。" in first[3]["content"]
        assert "本 run 已做" in first[4]["content"]
        # r2＝r1 前缀零改动延长＋[r1 决策 JSON（assistant），已做段（user）]。
        assert second[: len(first)] == first
        assert [m["role"] for m in second[len(first):]] == ["assistant", "user"]
        assert DECISION_WINDOWED in second[len(first)]["content"]
        assert "[decision] 决策｜决策 r1：执行 data" in second[-1]["content"]
        # 执行台账照旧落过程档案（黑匣子蒸馏面——分型措辞零漂移）。
        record = await store.get_blackbox(handle.run_id)
        assert record is not None
        phases = [n.get("phase") for n in record.get("process_notes") or []]
        assert {"understand", "decision", "tool", "draft", "verify"} <= set(phases)
        tool_notes = [
            n for n in record.get("process_notes") or [] if n.get("phase") == "tool"
        ]
        assert len(tool_notes) == 1
        assert "→ 结果：2 行" in tool_notes[0]["digest"]  # 1 权威行＋1 随行血缘卡
        # 终态链（黑匣子蒸馏面）：10 条追加形——终稿（含引用块）在链尾。
        chain = record.get("messages") or []
        assert [m["role"] for m in chain] == [
            "system", "user", "assistant", "user", "user",
            "assistant", "user", "assistant", "user", "assistant",
        ]
        assert "21.16" in chain[-1]["content"] and "引用：" in chain[-1]["content"]
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
        # 拒因回喂行在链（V2-80h——增量 user 轮；r1 被拒 JSON 以 assistant 轮同链
        # 在场——模型看得见自己被拒的原输出）。
        second = completer.messages_of("v2.runtime.decision")[1]
        assert any("上次决策被拒" in m.get("content", "") for m in second)
        assert any(
            m.get("role") == "assistant" and "采出程度" in str(m.get("content", ""))
            for m in second
        )
        # 对话层零台账轮（承载面改造；台账摘要在当前指令面——V2-79c）。
        assert not any("data_query 参数：" in m["content"] for m in second[1:-1])
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


def test_legacy_history_field_is_gone() -> None:
    """v1 混装史字段清账钉（V2-79e）：history 字段已删除——V2-80h 起 schema 面
    ＝对话链（messages，只追加）＋过程档案（process_notes）；dialogue 保留为
    v2 快照读兼容死字段（新代码零写入）；schema_version=3 为新旧判据；v1 旧
    checkpoint 的 history 通道由 LangGraph 按未知通道忽略（读兼容抽取面在
    extract_dialogue_from_legacy_history——golden 钉测守）。"""
    assert "history" not in RunState.__dataclass_fields__
    assert "messages" in RunState.__dataclass_fields__
    assert "process_notes" in RunState.__dataclass_fields__
    assert "dialogue" in RunState.__dataclass_fields__  # v2 快照兼容死字段（零写入）
    assert RunState().schema_version == 3


# ---------- 验收③：追问播种最小形——对话层承载前轮问答 ----------


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


def test_compile_retired_chain_is_the_context() -> None:
    """V2-80h：compile() 退役——对话链即上下文（只追加，相邻调用互为前缀）。
    79a 的逐轮重排装配与 79d 的视图截断压缩随之退役（链内轮数受轮预算约束，
    跨 run 前缀延伸是继承形非重排形）；ContextBuilder 只余材料渲染配置面
    （render_materials——作答轮全量观察 [n] 渲染，模块级函数）。"""
    from appv2.runtime.context import render_materials

    builder = ContextBuilder()
    assert not hasattr(builder, "compile")
    assert callable(render_materials)


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
        # V2-80h：追问轮链＝前链整链承接＋本轮问答（裸问句 user 轮在链中段，
        # 作答指令＋终稿在链尾）。
        record = await store_b.get_blackbox(handle_b.run_id)
        assert record is not None
        chain = record.get("messages") or []
        assert chain[0]["role"] == "system"
        assert {
            "role": "user", "content": "我刚问了什么问题？",
        } in chain  # 本轮追问原话（裸 user 轮）
        assert "你上一轮问的是" in chain[-1]["content"]  # 本轮终稿在链尾
        # 前轮问答承接在链（前轮任务书嵌前问＋前轮终稿 assistant 轮）。
        assert QUESTION_A in chain[1]["content"]
        assert any(
            m.get("role") == "assistant" and "21.16" in str(m.get("content", ""))
            for m in chain
        )
    finally:
        await db_b.dispose()


# ---------- V2-79b：播种新形（checkpoint 级全量传承）＋v1 读兼容抽取 golden ----------

CLARIFY_ASK_TARGET = (
    '{"action": "ask", "ask": {"prompt": "您想问哪口井的日产油量？", '
    '"options": ["N-01 井", "Z-16 井"]}}'
)


def test_extract_legacy_v1_golden_greeting_shape() -> None:
    """golden①（真实库 run-4435a7ce 样形逐字）：v1 混装史＝任务书×2＋「直接回答：」
    原话×2＋播种轮——抽取后只剩自然对话（问＋终稿），任务书/模型原话/伪标注全不进。"""
    question = "我能问什么"
    answer = "您好，我是油田数据问答助手，可以帮您查询生产动态。"
    task_book = (
        "【场景】你是油田数据问答系统的读题环节。\n【待解构的题干】\n"
        + question
        + "\n（无关业务的输入按上面的例外单行直答；其余现在输出两行。）"
    )
    values = {
        "history": [
            {"role": "user", "content": task_book},
            {"role": "assistant", "content": f"直接回答：{answer}"},
            {"role": "assistant", "content": answer},  # 79a 前播种的终稿轮
            {"role": "user", "content": task_book.replace(question, "我刚刚问了什么")},
            {"role": "assistant", "content": "直接回答：您好，看起来您的上一条消息没有成功发送。"},
        ]
    }
    turns = extract_dialogue_from_legacy_history(
        values, question=question, answer=answer
    )
    assert turns == [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]


def test_extract_legacy_v1_golden_clarify_recycle_shape() -> None:
    """golden②：v1 澄清回收轮「用户补充：X」→user 轮 X（去系统前缀——对话纯度）。"""
    values = {
        "history": [
            {"role": "user", "content": "【场景】理解任务书……【待解构的题干】\n日产油量"},
            {"role": "assistant", "content": "理解：问日产油量\n指标候选：日产油量"},
            {"role": "user", "content": "用户补充：N-01 井"},
            {"role": "assistant", "content": '{"action": "execute"}'},
            {
                "role": "user",
                "content": 'data_query 参数：{"window_start":"2025-09-01"} → 结果：2 行',
            },
        ]
    }
    turns = extract_dialogue_from_legacy_history(
        values, question="日产油量", answer="N-01 井 21.16 吨[1]。"
    )
    assert turns == [
        {"role": "user", "content": "日产油量"},
        {"role": "user", "content": "N-01 井"},
        {"role": "assistant", "content": "N-01 井 21.16 吨[1]。"},
    ]


def test_extract_legacy_v1_golden_approval_recycle_shape() -> None:
    """golden③：v1 审批回收轮「外表引用审批决定：批准（审批单号 …）」→user 轮
    「批准」（单号细节不入对话层）。"""
    values = {
        "history": [
            {"role": "user", "content": "任务书……【待解构的题干】\n首问"},
            {
                "role": "user",
                "content": "外表引用审批决定：批准（审批单号 eng-abc123）",
            },
        ]
    }
    turns = extract_dialogue_from_legacy_history(
        values, question="首问", answer="终稿。"
    )
    assert turns == [
        {"role": "user", "content": "首问"},
        {"role": "user", "content": "批准"},
        {"role": "assistant", "content": "终稿。"},
    ]


def test_extract_legacy_v1_fail_closed_on_unclassifiable() -> None:
    """golden④ fail-closed：决策指令轮/澄清合同轮等不可分类 user 轮与全部
    assistant 轮不进抽取面（宁可少传不可错传——不编造对话）。"""
    values = {
        "history": [
            {"role": "user", "content": "任务：输出本轮决策 JSON。上次决策被拒：x"},
            {"role": "assistant", "content": '{"action": "finalize"}'},
            {"role": "user", "content": "随便什么指令轮"},
        ]
    }
    turns = extract_dialogue_from_legacy_history(values, question="Q", answer="")
    assert turns == [{"role": "user", "content": "Q"}]  # answer 空＝省终稿轮


async def test_followup_seeds_full_checkpoint_dialogue(tmp_path: Path) -> None:
    """V2-79b 传承 e2e（v2 直读）：run A 澄清挂起→resume→completed（dialogue＝
    [问, 补充, 答] 三轮）→追问 run B 的 understand 上下文含全三轮——checkpoint
    级全量传承（非 runs 行两轮最小形）。"""
    script_a: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [CLARIFY_ASK_TARGET, DECISION_WINDOWED, DECISION_FINALIZE],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    runtime_a, completer_a, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script_a,
    )
    store = RunStore(db)
    run_id_a = ""
    try:
        handle_a = await runtime_a.ask(
            AskRequest(question="日产油量是多少？", actor=ACTOR)
        )
        events = await drain(handle_a)
        assert [e for e in events if e.event == "ask"], "澄清 ASK 帧未发出"
        run_a = await store.get_run(handle_a.run_id)
        assert run_a is not None and run_a.status == "waiting_ask"
        handle_r = await runtime_a.resume(handle_a.run_id, AskChoice(value="N-01 井"))
        await drain(handle_r)
        run_a = await store.get_run(handle_a.run_id)
        assert run_a is not None and run_a.status == "completed"
        assert "21.16" in (run_a.answer or "")
        run_id_a = handle_a.run_id
        # 前轮终态链形（黑匣子蒸馏面——V2-80h 追加链）：澄清回收轮 user 轮在链。
        record_a = await store.get_blackbox(run_id_a)
        assert record_a is not None
        chain_a = record_a.get("messages") or []
        assert any(
            m.get("role") == "user" and m.get("content") == "N-01 井"
            for m in chain_a
        )
        assert any(
            m.get("role") == "assistant" and "21.16" in str(m.get("content", ""))
            for m in chain_a
        )
        # V2-79c：resume 后的决策轮指令带「本 run 已做」段（澄清回收在案）。
        resume_round = completer_a.messages_of("v2.runtime.decision")[1]
        resume_current = resume_round[-1]["content"]
        assert "本 run 已做" in resume_current
        assert "[clarify] 澄清回收｜N-01 井" in resume_current
        assert "[decision] 决策｜决策 r1：澄清（您想问哪口井的日产油量？" in resume_current
    finally:
        await db.dispose()

    script_b: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_FINALIZE],
        "v2.runtime.answer": ["承接前轮。"],
    }
    runtime_b, completer_b, db_b = await make_runtime(
        tmp_path, engine=QueueQueryEngine([]), script=script_b,
    )
    try:
        handle_b = await runtime_b.ask(
            AskRequest(question="那 Z-16 井呢？", actor=ACTOR, followup_of=run_id_a)
        )
        await drain(handle_b)
        # V2-80h 整链承接：understand 上下文＝前链全量（任务书/澄清回收/终稿）
        # ＋本轮问（裸 user 轮尾随）＋本轮任务书。
        understand_msgs = completer_b.messages_of("v2.runtime.understand")[0]
        assert understand_msgs[0]["role"] == "system"
        assert "日产油量是多少？" in understand_msgs[1]["content"]  # 前轮任务书嵌前问
        assert any(
            m.get("role") == "user" and m.get("content") == "N-01 井"
            for m in understand_msgs
        )
        assert any(
            m.get("role") == "assistant" and "21.16" in str(m.get("content", ""))
            for m in understand_msgs
        )
        assert understand_msgs[-2] == {"role": "user", "content": "那 Z-16 井呢？"}
        assert "【待解构的题干】" in understand_msgs[-1]["content"]
    finally:
        await db_b.dispose()


async def test_followup_degraded_run_row_without_checkpoint(tmp_path: Path) -> None:
    """V2-79b 降级 e2e：run 行在库（completed＋answer）但 checkpoint 缺（v1 前
    存量形）→_seed_dialogue 走 v1 抽取支＝[问, 答]（fail-closed——不编造对话）。"""
    script_orphan_followup: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_FINALIZE],
        "v2.runtime.answer": ["承接前轮。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([]), script=script_orphan_followup,
    )
    store = RunStore(db)
    orphan_id = "run-orphan0"
    try:
        await store.create_run(run_id=orphan_id, question="前轮问句", actor="dev-u1")
        await store.finish_run(orphan_id, status="completed", answer="前轮终稿答案。")
        handle = await runtime.ask(
            AskRequest(question="追问一句", actor=ACTOR, followup_of=orphan_id)
        )
        await drain(handle)
        run_b = await store.get_run(handle.run_id)
        assert run_b is not None and run_b.status == "completed"
        # 播种面＝v1 抽取支输出（[问, 答]——无 checkpoint 可读，fail-closed）。
        understand_msgs = completer.messages_of("v2.runtime.understand")[0]
        assert understand_msgs[1] == {"role": "user", "content": "前轮问句"}
        assert understand_msgs[2] == {"role": "assistant", "content": "前轮终稿答案。"}
    finally:
        await db.dispose()


# ---------- V2-79c：过程档案摘要渲染（决策/澄清/匹配指令「本 run 已做」段） ----------


def test_render_process_notes_bounded_with_disclosure() -> None:
    """有界纪律（V2-79c）：零档案＝零段；多条长档案渲染 ≤ 预算＋披露行，
    截断带条数前后账（不静默）。"""
    from appv2.runtime.graph import _render_process_notes

    assert _render_process_notes(RunState()) == ""  # 零档案零段（首轮零噪声）
    state = RunState()
    state.process_notes = [
        {"phase": "tool", "title": f"工具{i}", "digest": "行" * 120}
        for i in range(10)
    ]
    segment = _render_process_notes(state)
    assert segment.startswith("【本 run 已做")
    assert "有界截断" in segment
    assert len(segment) <= 460  # 头 26＋预算 400＋披露行（截断必披露不越界）


async def test_decision_instruction_carries_process_notes_digest(
    tmp_path: Path,
) -> None:
    """「本 run 已做」段（V2-79c）：r1 决策指令带理解档案条目（零工具条目）；
    r2 带 r1 决策摘要＋执行台账行——「已探查/已执行」接回模型面（V2-37 闸
    保持机器兜底双保险）。"""
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
        rounds = completer.messages_of("v2.runtime.decision")
        first_current = rounds[0][-1]["content"]
        assert "本 run 已做" in first_current
        assert "[understand] 理解｜" in first_current
        assert "- [tool]" not in first_current  # r1 时工具未执行
        second_current = rounds[1][-1]["content"]
        assert "[decision] 决策｜决策 r1：执行 data" in second_current
        tool_lines = [
            line for line in second_current.splitlines()
            if line.startswith("- [tool]")
        ]
        assert len(tool_lines) == 1 and "→ 结果：2 行" in tool_lines[0]
    finally:
        await db.dispose()


# ---------- 编排面三钉（RT-W5-01a：行 19／20／21，runtimev2 编排块黑盒） ----------

ASYNC_MULTI_TURN_TESTS = True


async def _v2_e2e_run(
    *, question: str, followup_of: str = "", tables: Any = None
) -> tuple[Any, Any, str, Any]:
    """跑一个四相位 run（收口完成）——返回 (events, 剧本 completer, run_id)。"""
    dump = v2_ledger_dump()
    note = v2_ledger_note(dump, "日产油量")
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            v2_decompose(
                subtask_id="s1",
                question="2025-09-01 到 09-03 各井日产油量",
                ledger_notes=note,
                chain="data",
            ),
            v2_matches(
                v2_data_match(subtask_id="s1", slot="日产油量",
                              start="2025-09-01", end="2025-09-03")
            ),
        ],
        "answer": ["答案：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    from appv2.infra.clock import freeze
    from appv2.runtimev2.context import wire_ledger_projection
    from appv2.runtimev2.state import AskRequest

    wire_ledger_projection(V2LedgerPort(dump))
    engine = V2QueueEngine([_rows_outcome()])
    from appv2.runtimev2.persistence import MemoryTables

    shared = tables if tables is not None else MemoryTables()
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(
            script=script, registry=v2_registry(engine=engine), tables=shared
        )
        handle = await runtime.ask(
            AskRequest(question=question, actor=V2_ACTOR, followup_run_id=followup_of or None)
        )
        events = [event async for event in handle.stream]
    return events, completer, events[-1].data["run_id"], shared


async def test_second_decision_context_carries_first_round_history() -> None:
    """行 19｜run 内对话状态簿记（`dialogue`＋`process_notes` 双字段，第二轮调用携带首轮对话）。

    两处机检面：①**链上**——第 2 次决策调用＝第 1 次的**前缀延长**（钉 `pin-22`：只追加、
    任意相邻调用互为前缀延伸），且第 1 轮澄清发射原话（assistant 轮）逐字在链上；②**状态**——
    `process_notes` 双字段条目形 `{phase,title,digest}` 齐备、`dialogue` 条目（若有）来源落在
    闭世界内（钉 `pin-26` 的字段面）。
    """
    events, completer, run_id, _tables = await _v2_e2e_run(
        question="2025 年 9 月 1 日到 3 日的日产油量"
    )
    assert events[-1].data["status"] == "completed"

    calls = completer.messages_of("decision")
    assert len(calls) >= 2
    first, second = calls[0], calls[1]
    # 2026-10-17 H 批（角色分家）：请求首条＝**本环节规章段**（system 承载位）——跨环节前缀必然不同
    # （澄清规章 → 匹配规章；真源 `specs/prompts.md` H 批注「KV 缓存代价明示接受：跨环节首调用
    # 前缀重算一次」）；**链本体仍前缀延伸**（pin-22 的只追加面）——按链段比对
    assert first[0]["role"] == "system" and second[0]["role"] == "system"
    assert first[0]["content"] != second[0]["content"]  # 两环节规章各异（本环节规章随请求走）
    first_chain, second_chain = first[1:], second[1:]
    assert second_chain[: len(first_chain)] == first_chain  # 前缀延伸（pin-22）
    assert any(
        message.get("role") == "assistant" and "question_group" in str(message.get("content", ""))
        for message in second
    )  # 首轮决策原话随第 2 轮调用进上下文

    state = V2RunStore().load(run_id)
    assert state.process_notes and all(
        set(entry) == {"phase", "title", "digest"} for entry in state.process_notes
    )
    assert all(
        entry.get("origin") in {"user_verbatim", "assistant_final", "clarify_approval_replay"}
        for entry in state.dialogue
    )
    from appv2.runtimev2.state import RunState as _V2State

    assert isinstance(state, _V2State)


async def test_followup_context_carries_prior_qa_history() -> None:
    """行 20｜追问续会话：前轮问答（＋执行台账）随追问进上下文（钉 `pin-23` 的编排动作面）。"""
    events1, _completer1, run1, tables = await _v2_e2e_run(
        question="2025 年 9 月 1 日到 3 日的日产油量"
    )
    assert events1[-1].data["status"] == "completed"
    chain1 = V2RunStore().load(run1).messages
    answer1 = V2RunStore().run(run1).answer or ""

    events2, completer2, run2, _ = await _v2_e2e_run(
        question="那 W-111 井呢？（接着上一问）", followup_of=run1, tables=tables
    )
    assert events2[-1].data["status"] == "completed"
    assert V2RunStore().run(run2).followup_of == run1

    seeded = "\n".join(
        str(message.get("content", ""))
        for message in completer2.messages_of("decision")[0]
    )
    assert "2025 年 9 月 1 日到 3 日的日产油量" in seeded  # 前轮问句在上下文
    assert answer1.strip() and answer1.splitlines()[0][:12] in seeded  # 前轮答案终稿在上下文
    chain2 = V2RunStore().load(run2).messages
    assert chain2[: len(chain1)] == chain1  # 整链承接（跨 run 前缀延伸）
    # 2026-10-17 H 批：链首背景块**每链恰一条**（追问链承前轮链首，**不重挂**）
    from appv2.runtimev2.prompts import SYSTEM_BACKGROUND

    assert chain1[0] == {"role": "system", "content": SYSTEM_BACKGROUND}
    assert [str(m["role"]) for m in chain2].count("system") == 1
    assert chain2[0] == {"role": "system", "content": SYSTEM_BACKGROUND}


async def test_gate_refused_line_visible_across_followup() -> None:
    """行 21｜闸拒拒因（负信息）在历史中可见不消失。

    **承重面（本票实得）**：闸拒拒因经 `bookkeeping` 唯一写口落**历史面**（步记录 ＋ 过程档案
    ＋ 通知），跨追问不消失——追问 run 的链以**前轮终链整链**为前缀（钉 `pin-23`），前轮链上
    的问／答／台账逐字在场。
    **登记（呈主窗，未自造）**：拒因行进入**下一轮模型视图**的注入点＝「已做段」渲染
    （`context.render_process_notes` → `prompts.assemble_decision_increment(done_text=…)`），
    而该装配调用点在相位内部（`clarification._open_round` 自调、不接编排入参）——W5 接线清单④
    的注入面在相位侧无落点，本票如实登记、不私改相位签名实参形。
    """
    from appv2.infra.clock import freeze
    from appv2.runtimev2.context import wire_ledger_projection
    from appv2.runtimev2.state import AskRequest

    dump = v2_ledger_dump()
    # 禁用词题（题面提「老完成率」）：台账注释载其**替代现行指标**名录名（旧形抄术语行首名——
    # 流水 64 判据段一须 ∈ 名录＝指标/对象/关系名，术语名不在名录；登记项呈主窗）
    note = v2_ledger_note(dump, "产量完成率")
    refused = v2_decompose(
        subtask_id="s1",
        question="各井老完成率",
        ledger_notes=note,
        chain="data",
    )
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [
            refused,
            v2_matches(
                v2_data_match(subtask_id="s1", slot="采出程度",
                              start="2025-09-01", end="2025-09-03")
            ),
        ],
        "answer": ["未能取得权威数值，如实说明材料未披露的情况。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script=script, registry=v2_registry(engine=V2QueueEngine([]))
        )
        events1 = await v2_run(runtime, "各井老完成率")
        run1 = events1[-1].data["run_id"]
        state1 = V2RunStore().load(run1)
        refusal_lines = [
            str(entry.get("digest", "")) for entry in state1.process_notes
        ] + [str(entry.get("content", "")) for entry in state1.notices]
        assert any("拒" in line for line in refusal_lines)  # 闸拒拒因入历史（负信息不丢）

        handle = await runtime.ask(
            AskRequest(question="换个说法再问一次", actor=V2_ACTOR, followup_run_id=run1)
        )
        [event async for event in handle.stream]
        run2 = V2RunStore().run(run1)
        assert run2 is not None
        chain2 = V2RunStore().load(run2.run_id).messages
        chain1 = state1.messages
        assert chain2[: len(chain1)] == chain1  # 前轮历史跨追问逐字承接（不接受裁剪）
