"""V2-37 同参重投机器闸验收钉测（P-031——decision 出口确定性拦截＋拒因回喂）。

P-026 复测残余（9/16 题同参重复执行耗 3 轮→形态收敛堆叠）的机器收口：decision
出口对主执行载荷（plan/retrieval_need）的**同参二次发射**确定性拦截——不再触工具，
拒因（「同参已执行，带结果直答或改参」）回喂 LLM 由它重决策（finalize 直答或改参）。

票面验收①钉测面（语义零漂移——四条边界各一钉）：
- 二次同参发射被拦＋拒因回喂＋带材料直答形（钉测①）；
- 改参不误伤：新窗/新参发射照常执行（钉测②）；
- 跨支不误伤＋mixed 全支已执行才拦（钉测③——单支新参＝有新信息，不拦）；
- 顽投兜底：轮轮同参重投——执行恰一次，预算收敛材料交付（钉测④，堆叠消失）；
- 审批重跑合法同参不误伤：resume 批准重投走 last_execute 通道不经 decision 出口
  （test_v2_runtime_wiring.test_ask_detail_resume_wire 既有钉守此面）。

行为断言锁在决策出口（step payload gate 标记）与工具调用计数，不锁模型原话。
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
from appv2.retrieval import (
    Observation as RetrievalObservation,
)
from appv2.retrieval import RetrievalBundle
from appv2.runtime import (
    AskRequest,
    RunStore,
)
from appv2.tools import FakeRetrievalEngine
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

# 同参罐头＝DECISION_WINDOWED 原样重发（JSON 逐字相同）；改参罐头＝换窗。
DECISION_WINDOWED_ALT = (
    '{"thought": "材料只覆盖单日——改窗取多日", "action": "execute", '
    '"task_type": "data", "plan": {"metric_slot": "日产油量", "ranking": false, '
    '"window_start": "2025-09-02", "window_end": "2025-09-05", "limit": 5}}'
)
DECISION_MIXED = (
    '{"action": "execute", "task_type": "mixed", '
    '"plan": {"metric_slot": "日产油量", "ranking": false, '
    '"window_start": "2025-09-01", "window_end": "2025-09-03", "limit": 5}, '
    '"retrieval_need": {"question": "日产油量 口径 单位"}}'
)
DECISION_KNOWLEDGE = (
    '{"thought": "口径叙述题——走检索", "action": "execute", '
    '"task_type": "knowledge", "retrieval_need": {"question": '
    '"日产油量 口径 单位", "family_hints": ["completion"]}}'
)

_CALIBER_TEXT = "口径说明：日产油量为班次合计日口径，单位吨。"


def _rows_outcome() -> QueryOutcome:
    return QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
        lineage=(
            LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量（单位：吨）——口径声明"),
            LineageLine(key=LINEAGE_KEY_WATERMARK, value="汇总层水位 2026-08-31"),
        ),
    )


def _fragment_obs(text: str, fragment_id: str) -> RetrievalObservation:
    return RetrievalObservation(
        kind="fragment",
        text=text,
        snippet=text[:80],
        score=0.9,
        leg="keyword",
        family="completion",
        fragment_id=fragment_id,
        report_id="rep-w111",
        report="W-111 井完井报告",
        library_id="lib-completion",
        library="完井工程库",
        section="第一章",
        locator={"library": "完井工程库", "report": "W-111 井完井报告"},
    )


def _retrieval_with(*obs: RetrievalObservation) -> FakeRetrievalEngine:
    return FakeRetrievalEngine(
        bundle=RetrievalBundle(
            observations=list(obs), window_note=f"召回 {len(obs)} 支/送窗 {len(obs)} 支"
        )
    )


def _step_kinds(events: list[Any]) -> list[str]:
    return [e.data["step"] for e in events if e.event == "step"]


def _notices(events: list[Any]) -> list[dict[str, Any]]:
    return [e.data for e in events if e.event == "notice"]


def _replay_steps(steps: list[Any]) -> list[Any]:
    return [s for s in steps if (s.payload or {}).get("gate") == "same_param_replay"]


# ---------- 钉测①：二次同参发射被拦＋拒因回喂＋带材料直答形 ----------


async def test_same_param_second_emission_intercepted(tmp_path: Path) -> None:
    """r1 执行出数（观察回流）→r2 原样重发同参计划→确定性拦截（工具零重复执行）
    ＋拒因回喂（「同参已执行，带结果直答或改参」进下轮决策消息）→r3 finalize→
    材料走起草→核验→引用收口（带材料直答形——非收敛原样罗列）。"""
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_WINDOWED, DECISION_WINDOWED, DECISION_FINALIZE],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    engine = QueueQueryEngine([_rows_outcome()])
    runtime, completer, db = await make_runtime(tmp_path, engine=engine, script=script)
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        # 二次同参发射被拦：data_query 恰 1 次（零重复执行）。
        assert engine.run_calls == 1
        # 拦截步在案（决策出口机读 gate 标记＋拒因原文）。
        replay_steps = _replay_steps(await store.list_steps(handle.run_id))
        assert len(replay_steps) == 1
        assert "同参已执行" in replay_steps[0].payload["rejection"]
        assert "带结果直答或改参" in replay_steps[0].payload["rejection"]
        # 机读 notice 恰 1 条（type=same_param_replay）。
        replay_notices = [
            n for n in _notices(events) if n.get("type") == "same_param_replay"
        ]
        assert len(replay_notices) == 1
        assert "同参已执行" in replay_notices[0]["content"]
        # 拒因回喂：第 3 次决策调用消息携「上次决策被拒」＋拒因原文。
        third_round = completer.messages_of("v2.runtime.decision")[2]
        assert "上次决策被拒" in third_round[1]["content"]
        assert "同参已执行" in third_round[1]["content"]
        # 带材料直答形：finalize 后起草→核验→引用收口（非预算收敛罗列形）。
        assert _step_kinds(events) == [
            "decision", "decision", "execute", "observe", "decision",
            "decision", "answer", "verify", "answer",
        ]
        assert "21.16 吨[1]" in (run.answer or "")
        verdicts = [
            e.data for e in events
            if e.event == "verdict" and e.data.get("rewritten") is not None
        ]
        assert verdicts and verdicts[0]["cited"] == [1]
        assert not [n for n in _notices(events) if n.get("type") == "budget_converged"]
        # 三 caller 桶（decision 3 次＝r1 发射＋r2 被拦＋r3 finalize；无 repair）。
        assert completer.counts() == {
            "v2.runtime.understand": 1,
            "v2.runtime.decision": 3,
            "v2.runtime.answer": 1,
        }
    finally:
        await db.dispose()


# ---------- 钉测②：改参不误伤 ----------


async def test_changed_param_not_intercepted(tmp_path: Path) -> None:
    """r1 执行→r2 改窗（新参）发射→照常执行（拦截只针对同参二次发射——
    改参路径零误伤），两次执行都回流后 finalize。"""
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [
            DECISION_WINDOWED, DECISION_WINDOWED_ALT, DECISION_FINALIZE,
        ],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    engine = QueueQueryEngine([_rows_outcome(), _rows_outcome()])
    runtime, _completer, db = await make_runtime(tmp_path, engine=engine, script=script)
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert engine.run_calls == 2  # 改参发射照常执行
        assert not [n for n in _notices(events) if n.get("type") == "same_param_replay"]
        assert not _replay_steps(await store.list_steps(handle.run_id))
        assert "21.16" in (run.answer or "")
    finally:
        await db.dispose()


# ---------- 钉测③：跨支不误伤＋mixed 全支已执行才拦 ----------


async def test_cross_branch_not_intercepted(tmp_path: Path) -> None:
    """r1 执行 data→r2 发射 knowledge（另一支）→照常执行（跨支＝新信息，
    零误伤）。"""
    retrieval = _retrieval_with(_fragment_obs(_CALIBER_TEXT, "frag-caliber-1"))
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [
            DECISION_WINDOWED, DECISION_KNOWLEDGE, DECISION_FINALIZE,
        ],
        "v2.runtime.answer": [
            "N-01 井 2025-09-01 日产油量 21.16 吨[1]；口径：班次合计日口径[3]。",
        ],
    }
    engine = QueueQueryEngine([_rows_outcome()])
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script, retrieval=retrieval,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量及口径", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert engine.run_calls == 1  # data 支执行一次
        assert retrieval.retrieve_calls == 1  # knowledge 支照常执行
        assert not [n for n in _notices(events) if n.get("type") == "same_param_replay"]
        assert not _replay_steps(await store.list_steps(handle.run_id))
        assert "21.16 吨[1]" in (run.answer or "")
    finally:
        await db.dispose()


async def test_mixed_replay_intercepted_only_when_both_branches_executed(
    tmp_path: Path,
) -> None:
    """mixed（data＋knowledge 一轮双执行）同参二次发射：两支都已执行＝整发射同参
    ——拦截（工具零重复执行）；单支新参不拦（钉测②③面——有新信息即放行）。"""
    retrieval = _retrieval_with(_fragment_obs(_CALIBER_TEXT, "frag-caliber-1"))
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_MIXED, DECISION_MIXED, DECISION_FINALIZE],
        "v2.runtime.answer": [
            "N-01 井 2025-09-01 日产油量 21.16 吨[1]；口径：班次合计日口径[3]。",
        ],
    }
    engine = QueueQueryEngine([_rows_outcome()])
    runtime, completer, db = await make_runtime(
        tmp_path, engine=engine, script=script, retrieval=retrieval,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量及口径", actor=ACTOR)
        )
        await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        # 二次 mixed 同参发射被拦：两工具各恰 1 次（零重复执行）。
        assert engine.run_calls == 1
        assert retrieval.retrieve_calls == 1
        assert len(_replay_steps(await store.list_steps(handle.run_id))) == 1
        assert completer.counts()["v2.runtime.decision"] == 3
        assert "21.16 吨[1]" in (run.answer or "")
    finally:
        await db.dispose()


# ---------- 钉测④：顽投兜底——执行恰一次，预算收敛材料交付（堆叠消失） ----------


async def test_stubborn_replay_converges_with_single_execution(tmp_path: Path) -> None:
    """模型轮轮原样重投（P026W 残余形态的极端化）：闸逐轮拦＋拒因回喂，data_query
    恰 1 次；3 轮耗尽预算收敛——已取得材料如实交付（同参堆叠的机器收口形态：
    重复执行消失，材料面守恒）。"""
    engine = QueueQueryEngine([_rows_outcome()])
    runtime, completer, db = await make_runtime(
        tmp_path,
        engine=engine,
        script={
            "v2.runtime.understand": [UNDERSTAND_DATA],
            "v2.runtime.decision": [DECISION_WINDOWED],  # 末条驻留——轮轮同参重投
        },
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        # 执行恰一次（P026W 同位形态 3 次——堆叠消失的机器语义）。
        assert engine.run_calls == 1
        # r2/r3 两轮同参发射被拦（机读 notice 恰 2 条）；第 4 入口轮数闸收敛。
        replay_notices = [
            n for n in _notices(events) if n.get("type") == "same_param_replay"
        ]
        assert len(replay_notices) == 2
        converged = [n for n in _notices(events) if n.get("type") == "budget_converged"]
        assert len(converged) == 1 and converged[0]["gates"] == ["max_rounds"]
        # 收敛材料直答形：已取得权威行材料原样交付（不静默截断）。
        assert "21.16" in (run.answer or "")
        kinds = _step_kinds(events)
        assert kinds.count("execute") == 1 and kinds.count("observe") == 1
        assert completer.counts() == {
            "v2.runtime.understand": 1,
            "v2.runtime.decision": 3,
        }
    finally:
        await db.dispose()
