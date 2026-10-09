"""指南 eval-cases AC-G4/G6/G11/G12 剧本行为断言（V2-37/P-031——DefaultGuideProvider
退役前对账钉）。

票面附带任务：ontology/petro/skill-guides/eval-cases.md 的 AC-G4/G6/G11/G12 钉为
剧本行为断言。断言锁**运行时行为**（决策出口 emission／工具调用计数／notice 分型），
不锁指南文本与模型原话——DefaultGuideProvider 内置文案退役、ontology 资产件
（GUIDE-PETRO-001）经 GuideProvider 缝整替注入后，本文件四钉仍是对账基准
（eval-cases.md §S3「V2-31 剧本可引用 AC-G4/G6/G11/G12 做行为断言」的落码面）：

- AC-G4（§3.1＋§A）：时间窗歧义禁 ask、自动默认近 30 天＋注记——零 ask 帧、
  note 注记出流、is_default 进引擎计划；
- AC-G6（§4 发射判据逐字）：台账命中＋窗已定＝必须发射，禁再 discover——数据型
  直接发射运行形状＝零 discover 步＋data_query 恰 1 次；
- AC-G11（§A metric_slot 纪律）：两禁式（复合注记「日产油量（oil_output）」／英文
  列名 oil_pressure）逐式被台账校验拒＋拒因回喂，精确名修正后执行放行；
- AC-G12（§A no_hit 处置）：复合词面 no_hit→改单名重试一次→仍 no_hit 按三链路由
  定案（禁第三次试）——discover 恰 2 支，链收在 execute(knowledge)。
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
    Budget,
    RunStore,
)
from appv2.tools import (
    FakeKnowledgeStore,
    FakeQueryEngine,
    FakeRetrievalEngine,
)
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
from tests.domains.test_v2_react_loop import DECISION_DEFAULT_NOTE

# ---------- 罐头 ----------

_CALIBER_TEXT = "口径说明：日产油量为班次合计日口径，单位吨。"
_FRAGMENT_TEXT = "W-111 井采用酸压完井，投产初期日产油 291 方。"

# AC-G11 两禁式（指南 §A 逐字禁用形）＋精确名修正式。
DECISION_FORBIDDEN_COMPOUND = (
    '{"action": "execute", "task_type": "data", '
    '"plan": {"metric_slot": "日产油量（oil_output）", "ranking": false, '
    '"window_start": "2025-09-01", "window_end": "2025-09-03", "limit": 5}}'
)
DECISION_FORBIDDEN_ENGLISH = (
    '{"action": "execute", "task_type": "data", '
    '"plan": {"metric_slot": "oil_pressure", "ranking": false, '
    '"window_start": "2025-09-01", "window_end": "2025-09-03", "limit": 5}}'
)
# AC-G12：复合词面 discover→单名重试→仍 no_hit 三链路由定案（execute knowledge）。
DECISION_DISCOVER_COMPOUND = (
    '{"action": "discover", "discovers": '
    '[{"tool": "semantic_query", "args": {"element_name": "日产油量（吨）"}}]}'
)
DECISION_DISCOVER_SINGLE = (
    '{"action": "discover", "discovers": '
    '[{"tool": "semantic_query", "args": {"element_name": "日产油量"}}]}'
)
DECISION_KNOWLEDGE = (
    '{"action": "execute", "task_type": "knowledge", '
    '"retrieval_need": {"question": "日产油量 口径 单位", '
    '"family_hints": ["completion"]}}'
)

_ANSWER_MIXED = "N-01 井 2025-09-01 日产油量 21.16 吨[1]；口径：班次合计日口径[3]。"


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


# ---------- AC-G4：时间窗歧义禁 ask、自动默认近 30 天＋注记 ----------


async def test_ac_g4_time_window_auto_default_no_ask(tmp_path: Path) -> None:
    """AC-G4（§3.1＋§A）：无时间词问句——时间窗歧义不挂起（零 ask 帧），按默认近
    30 天自动取数：note 注记出流（机读 decision_note）、plan.is_default 进引擎、
    答案正常出引用。"""
    engine = QueueQueryEngine([_rows_outcome()])
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_DEFAULT_NOTE, DECISION_FINALIZE],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question="最近的日产油量", actor=ACTOR))
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        # 禁 ask：零挂起帧（时间窗歧义不走澄清）。
        assert not [e for e in events if e.event == "ask"]
        # 自动默认注记出流（机读 decision_note——is_default 模板卡语义）。
        notes = [n for n in _notices(events) if n.get("type") == "decision_note"]
        assert len(notes) == 1 and "近 30 天" in notes[0]["content"]
        # is_default 进引擎计划（默认窗机读标注面）。
        assert engine.plans[0].is_default is True
        assert "21.16" in (run.answer or "")
    finally:
        await db.dispose()


# ---------- AC-G6：发射判据——台账命中＋窗已定＝必须发射，禁再 discover ----------


async def test_ac_g6_data_question_fires_execute_without_discover(
    tmp_path: Path,
) -> None:
    """AC-G6（§4 逐字）：数据型问句指标可指认＋窗已定——本轮直接 execute(data)，
    运行形状＝零 discover 步＋data_query 恰 1 次（发射判据的运行时形状钉——
    P-024b S3「犹豫空转」病灶的反面钉）。"""
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_WINDOWED, DECISION_FINALIZE],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    engine = QueueQueryEngine([_rows_outcome()])
    runtime, completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        # 禁再 discover：全 run 零发现步、零语义查询调用。
        assert _step_kinds(events).count("discover") == 0
        # 必须发射：data_query 恰 1 次真执行（r1 即发射）。
        assert engine.run_calls == 1
        # 决策出口锁定：r1 emission＝execute data（行为断言锁在决策出口）。
        steps = await store.list_steps(handle.run_id)
        decisions = [
            s for s in steps
            if s.step_type == "decision"
            and (s.payload or {}).get("phase") == "decision"
        ]
        assert decisions[0].payload["emission"]["action"] == "execute"
        assert decisions[0].payload["emission"]["task_type"] == "data"
        assert "21.16[1]" in (run.answer or "") or "21.16 吨[1]" in (run.answer or "")
        assert completer.counts()["v2.runtime.understand"] == 1
    finally:
        await db.dispose()


# ---------- AC-G11：metric_slot 纪律——两禁式逐式被拒＋拒因回喂 ----------


async def test_ac_g11_metric_slot_forbidden_forms_rejected_then_fixed(
    tmp_path: Path,
) -> None:
    """AC-G11（§A 五指标精确名白名单＋两禁式）：复合注记「日产油量（oil_output）」
    与英文列名 oil_pressure 逐式被台账校验拒（bad_args——不在指标台账）＋拒因回喂
    重决策；精确名修正后放行出数（两禁式各一跑段——三决策轮内闭环）。"""

    async def _one_forbidden_form(decision: str) -> tuple[list[dict[str, Any]], Any, Any]:
        script: dict[str, Sequence[str]] = {
            "v2.runtime.understand": [UNDERSTAND_DATA],
            "v2.runtime.decision": [decision, DECISION_WINDOWED, DECISION_FINALIZE],
            "v2.runtime.answer": [ANSWER_DRAFT_CITED],
        }
        engine = FakeQueryEngine(outcome=_rows_outcome())
        runtime, _completer, db = await make_runtime(
            tmp_path, engine=engine, script=script,
        )
        store = RunStore(db)
        try:
            handle = await runtime.ask(
                AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
            )
            events = await drain(handle)
            run = await store.get_run(handle.run_id)
            rejected = [
                n for n in _notices(events)
                if n.get("type") == "decision_rejected"
            ]
            return rejected, run, engine
        finally:
            await db.dispose()

    # 禁式一：复合注记「日产油量（oil_output）」。
    rejected, run, engine = await _one_forbidden_form(DECISION_FORBIDDEN_COMPOUND)
    assert len(rejected) == 1 and "不在指标台账" in rejected[0]["content"]
    assert engine.validate_calls == 2 and engine.run_calls == 1  # 拒＝引擎未执行
    assert "21.16 吨[1]" in (run.answer or "")  # 精确名修正后放行出数

    # 禁式二：英文列名 oil_pressure。
    rejected, run, engine = await _one_forbidden_form(DECISION_FORBIDDEN_ENGLISH)
    assert len(rejected) == 1 and "不在指标台账" in rejected[0]["content"]
    assert engine.validate_calls == 2 and engine.run_calls == 1
    assert "21.16 吨[1]" in (run.answer or "")


# ---------- AC-G12：no_hit 处置——改单名重试一次，仍 no_hit 按三链路由定案 ----------


async def test_ac_g12_no_hit_single_retry_then_route(tmp_path: Path) -> None:
    """AC-G12（§A）：复合词面 discover no_hit→改单名重试一次→仍 no_hit 按三链
    路由定案（execute knowledge 收链）——禁第三次试：discover 恰 2 支。"""
    retrieval = _retrieval_with(_fragment_obs(_FRAGMENT_TEXT, "frag-w111-1"))
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [
            DECISION_DISCOVER_COMPOUND,  # 复合词面——no_hit
            DECISION_DISCOVER_SINGLE,    # 改单名重试一次——仍 no_hit
            DECISION_KNOWLEDGE,          # 三链路由定案（不再试第三次）
            DECISION_FINALIZE,
        ],
        "v2.runtime.answer": ["口径见报告记载[1]。"],
    }
    knowledge = FakeKnowledgeStore()  # 空台账——两次钻取均 no_hit
    # 剧本轮数放宽到 4（两支 no_hit 钻取＋knowledge 收链＋finalize——合同值 3
    # 不动，Budget 缺省仍 3；仅为剧本完整形状需要）。
    runtime, _completer, db = await make_runtime(
        tmp_path,
        engine=FakeQueryEngine(),
        script=script,
        knowledge=knowledge,
        retrieval=retrieval,
        budget=Budget(max_rounds=4),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="日产油量（吨）的口径是什么", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        # 禁第三次试：discover 恰 2 支（复合→单名各一），semantic_query 恰 2 调。
        kinds = _step_kinds(events)
        assert kinds.count("discover") == 2
        assert knowledge.evidence_calls == 2
        # 三链路由定案：execute knowledge 恰 1 次（doc_retrieve 收链）。
        assert kinds.count("execute") == 1
        assert retrieval.retrieve_calls == 1
        # 两次 no_hit notice 观察回流在案（闸依据如实进材料面）。
        steps = await store.list_steps(handle.run_id)
        discover_steps = [s for s in steps if s.step_type == "discover"]
        assert [s.payload["status"] for s in discover_steps] == ["ok", "ok"]
        assert "口径" in (run.answer or "") and "[1]" in (run.answer or "")
    finally:
        await db.dispose()
