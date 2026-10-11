"""V2-31 ReAct 循环 runtime 验收（runtime 侧）——V2-06 原六步验收经 ReAct 重构
迁移（V2-31 拍板七条＝设计合同；六步线性流水线 → ReAct 自主循环）：

- budget_termination：轮数/时长预算收敛＋未完成项 notice（有界终止——ReAct 语义：
  轮＝LLM 决策周期 ≤3 轮，拍板①）；
- run_recover_after_restart：挂起态跨进程恢复——checkpointer 落库（PgCheckpointer），
  新 runtime 实例（新 ConnectionManager 同库文件）凭 run_id resume 续跑完成
  （行为约定 8）；
- readonly_inv2：全程无任何写操作落库（INV-2）——真问数引擎（CsvSnapshotExecutor）
  快照逐字节零变＋台账读面零变；
- react_happy_path（骨架钉测）：ReAct 周期步序 understand(decision)→decision→
  execute→observe→decision(finalize)→answer(起草)→verify→answer(收口)，
  每个模型调用 step 落 Manifest（过程态簿记留痕）；
- resume_error_paths（骨架钉测）：resume 到不存在 run／非挂起 run 的错误路径
  （V2-07 api 404/409 映射的 runtime 侧异常源）。

剧本化 completer（ScriptedCompleter，按 caller 分流、多轮 replay——三 caller 桶
understand/decision/answer，无 repair 桶）即 modules.md runtime 卡点名的测试
adapter——V2-31 剧本升级：counts()/messages_of() 观测面。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from appv2.api.ontology_guide import OntologyGuideProvider
from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.infra.security import Actor
from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot
from appv2.query import (
    ASKBACK_TIME_CHOICES,
    ASKBACK_TIME_QUESTION,
    FIXTURE_CSV,
    LINEAGE_KEY_CALIBER,
    LINEAGE_KEY_WATERMARK,
    CsvSnapshotExecutor,
    LineageLine,
    QueryEngine,
    QueryOutcome,
)
from appv2.runtime import (
    AgentRuntime,
    AskChoice,
    AskRequest,
    Budget,
    PgCheckpointer,
    RunEvent,
    RunNotFoundError,
    RunNotSuspendedError,
    RunStore,
    ScriptedCompleter,
    ensure_agent_v2_tables,
)
from appv2.runtime.executor import GraphRunExecutor
from appv2.runtime.llm import GatewayChatModel
from appv2.tools import FakeKnowledgeStore, FakeQueryEngine, FakeRetrievalEngine, ToolRegistry

# 执行日钉 2026-10-08、水位 2026-08-31（V2-03/04/05 验收底座同款——不吃墙上时钟）。
TODAY = date(2026, 10, 8)
WATERMARK = date(2026, 8, 31)
ACTOR = Actor(user_id="dev-u1", display="开发用户")

# 剧本（ScriptedCompleter 按 caller 分流；决策发射＝结构化 JSON——拍板①）：
UNDERSTAND_DATA = "理解：问 2025 年 9 月上旬的日产油量。\n指标候选：日产油量"
DECISION_WINDOWED = (
    '{"thought": "问数题——直接执行权威问数", "action": "execute", '
    '"task_type": "data", "plan": {"metric_slot": "日产油量", "ranking": false, '
    '"window_start": "2025-09-01", "window_end": "2025-09-03", "limit": 5}}'
)
DECISION_VAGUE = (
    '{"action": "execute", "task_type": "data", '
    '"plan": {"metric_slot": "日产油量", "ranking": false}}'
)
DECISION_FINALIZE = '{"thought": "材料已足够", "action": "finalize"}'
ANSWER_DRAFT_CITED = "N-01 井 2025-09-01 日产油量 21.16 吨[1]。"

HAPPY_SCRIPT: dict[str, Sequence[str]] = {
    "v2.runtime.understand": [UNDERSTAND_DATA],
    "v2.runtime.decision": [DECISION_WINDOWED, DECISION_FINALIZE],
    "v2.runtime.answer": [ANSWER_DRAFT_CITED],
}
HAPPY_QUESTION = "2025 年 9 月 1 日到 3 日的日产油量"

# ReAct 钉步序（骨架）：understand 段记 decision 类步（payload.phase=understand）。
HAPPY_STEP_KINDS = [
    "decision", "decision", "execute", "observe", "decision",
    "answer", "verify", "answer",
]


def _rows_outcome() -> QueryOutcome:
    return QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
        lineage=(
            LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量（单位：吨）——口径声明"),
            LineageLine(key=LINEAGE_KEY_WATERMARK, value="汇总层水位 2026-08-31"),
        ),
    )


class QueueQueryEngine(FakeQueryEngine):
    """剧本化按次出列引擎（前 N-1 次逐个弹出，末位驻留——挂起/恢复两段剧本）。"""

    def __init__(self, outcomes: Sequence[QueryOutcome]) -> None:
        super().__init__()
        self._queue = list(outcomes)

    def run(
        self, plan: Any, *, approved_tables: tuple[str, ...] = ()
    ) -> QueryOutcome:  # QueryOutcome 联合态
        self.run_calls += 1
        if len(self._queue) > 1:
            return self._queue.pop(0)
        return self._queue[0]


async def make_runtime(
    tmp_path: Path,
    *,
    engine: Any,
    script: dict[str, Sequence[str]],
    budget: Budget | None = None,
    knowledge: Any = None,
    completer: ScriptedCompleter | None = None,
    guide: Any = None,
    retrieval: Any = None,
    four_phase: bool = False,
    ledger_dump: Any = None,
    watermark: Any = None,
    data_wells: Any = None,
    faq: Any = None,
) -> tuple[AgentRuntime, ScriptedCompleter, ConnectionManager]:
    """标准装配：registry＋剧本 completer＋sqlite 库＋PgCheckpointer＋ReAct 图。

    knowledge＝registry 的台账缝（真引擎测试传 InMemoryKnowledgeStore，
    假引擎测试缺省 FakeKnowledgeStore）；engine＝QueryFace 缝（真/假问数引擎）；
    retrieval＝RetrievalFace 缝（缺省 FakeRetrievalEngine）；completer＝显式
    注入缝（闸门/爆炸 completer 等剧本变体——缺省按 script 现建
    ScriptedCompleter）；guide＝处理指南缝（拍板⑦——缺省 OntologyGuideProvider：
    占位 DefaultGuideProvider 已随 V2-34 退役，生产唯一指南源＝ontology 资产
    装载件）；four_phase/ledger_dump/watermark＝V2-34 四相位装配三缝；
    data_wells＝数据链井闭世界读缝（V2-51 软失败域闸——缺省 None＝闸静默）；
    faq＝FaqLookupFace 缝（V2-52 faq_lookup 发现工具读面——缺省 None＝工具
    不在册）。
    """
    registry = ToolRegistry(
        knowledge=knowledge if knowledge is not None else FakeKnowledgeStore(),
        query=engine,
        retrieval=retrieval if retrieval is not None else FakeRetrievalEngine(),
        faq=faq,
    )
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "v2-runtime.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    db = ConnectionManager([spec])
    await ensure_agent_v2_tables(db.engine())
    completer = completer if completer is not None else ScriptedCompleter(script)
    models = {
        name: GatewayChatModel(
            completer=completer, caller=f"v2.runtime.{name}", alias=""
        )
        for name in ("understand", "decision", "answer")
    }
    executor = GraphRunExecutor(
        registry=registry,
        models=models,
        db=db,
        saver=PgCheckpointer(db),
        budget=budget or Budget(),
        guide=(
            guide
            if guide is not None
            else OntologyGuideProvider(
                today=TODAY,
                # C6（P-033 中途审查）：测试装配随 four_phase 切换指南合同面——
                # 四相位装配不拼 legacy 决策合同（与生产接线 app.py 的
                # include_decision_contract=not four_phase 同形，消 SK1
                # 双合同隐患形态）；legacy 装配照旧拼接。
                include_decision_contract=not four_phase,
            )
        ),
        today=TODAY,
        four_phase=four_phase,
        ledger_dump=ledger_dump,
        watermark=watermark,
        data_wells=data_wells,
    )
    return AgentRuntime(executor), completer, db


async def drain(handle: Any) -> list[RunEvent]:  # RunHandle
    return [event async for event in handle.stream]  # stream 即 AsyncIterator（接口定义节原形）


def _step_kinds(events: list[RunEvent]) -> list[str]:
    return [e.data["step"] for e in events if e.event == "step"]


def _notices(events: list[RunEvent]) -> list[dict[str, Any]]:
    return [e.data for e in events if e.event == "notice"]


# ---------- 骨架钉测①：ReAct 周期步序＋每模型调用落 Manifest（过程态簿记） ----------


async def test_react_happy_path(tmp_path: Path) -> None:
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=HAPPY_SCRIPT
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        events = await drain(handle)
        assert _step_kinds(events) == HAPPY_STEP_KINDS
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "21.16" in (run.answer or "")
        assert run.manifest_digest  # Manifest 随 step 存档的摘要面（过程态簿记）
        # 每个模型调用 step（understand 段/decision r1/decision r2/answer 起草）
        # 落 Manifest（七字段合同形）；verify 零 LLM 不落（拍板③保留件语义）。
        steps = await store.list_steps(handle.run_id)
        with_manifest = [s for s in steps if s.manifest is not None]
        assert [s.step_type for s in with_manifest] == [
            "decision", "decision", "decision", "answer",
        ]
        for step in with_manifest:
            assert set(step.manifest) == {
                "source_type", "source_id", "version", "trust_level",
                "selected_reason", "token_count", "transform",
            }
            assert step.manifest["token_count"] > 0
            assert step.manifest["transform"] == "filter→rank→budget→cite"
        # 决策出口（拍板任务 5——行为断言锁在决策出口）：r1＝execute data、
        # r2＝finalize，emission 投影随 step payload 在案。
        decisions = [s for s in steps if s.step_type == "decision"
                     and (s.payload or {}).get("phase") == "decision"]
        assert decisions[0].payload["emission"]["action"] == "execute"
        assert decisions[0].payload["emission"]["task_type"] == "data"
        assert decisions[1].payload["emission"]["action"] == "finalize"
        # 引用事件带出处链（答案 fail-closed 引用的 runtime 侧素材）。
        citations = [e.data for e in events if e.event == "citation"]
        assert citations and citations[0]["source"] == "agg.fct_daily_metering"
    finally:
        await db.dispose()


# ---------- 验收①：预算触界收敛＋未完成项 notice（轮数/时长两闸——ReAct 语义） ----------


async def test_budget_termination(tmp_path: Path) -> None:
    # （a）轮数闸：max_rounds=2——r1/r2 两轮执行后 decision 入口收敛；已取得观察
    # 原样交付（非静默截断）＋notice 明示未完成项。收敛幂等（R1）：notice 恰 1 条、
    # 机读 gates 不重复追加；已收敛 run 不再起草/核验（零 verify 判定）。
    runtime, completer, db = await make_runtime(
        tmp_path,
        engine=QueueQueryEngine([_rows_outcome()]),
        script={
            "v2.runtime.understand": [UNDERSTAND_DATA],
            "v2.runtime.decision": [DECISION_WINDOWED],  # 末条驻留——轮轮重执行
        },
        budget=Budget(max_rounds=2),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "21.16" in (run.answer or "")  # 已取得材料交付——不静默截断
        # 三 caller 桶：decision 恰 2 轮（上限 2）——第 3 入口闸收敛，零起草。
        assert completer.counts() == {
            "v2.runtime.understand": 1,
            "v2.runtime.decision": 2,
        }
        notices = _notices(events)
        converged = [n for n in notices if n.get("type") == "budget_converged"]
        assert len(converged) == 1  # R1 收敛幂等：notice 恰 1 条
        assert converged[0]["gates"] == ["max_rounds"]  # 机读 gates 不重复追加
        assert "未完成" in converged[0]["content"]
        verdicts = [e.data for e in events if e.event == "verdict"]
        assert not [v for v in verdicts if v.get("rewritten") is not None]  # 零 verify 判定
    finally:
        await db.dispose()

    # （b）时长闸：total_seconds=0——首个节点入口即收敛（零材料情形），notice
    # 明示全链未完成；文案与答案同口径（R2：零材料不冒充「已交付」）。
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=HAPPY_SCRIPT,
        budget=Budget(total_seconds=0.0),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        notices = _notices(events)
        converged = [n for n in notices if n.get("type") == "budget_converged"]
        assert len(converged) == 1  # R1 收敛幂等：notice 恰 1 条
        assert converged[0]["gates"] == ["total_seconds"]
        assert "未完成" in converged[0]["content"]
        # R2 零材料分叉：notice 与答案同一口径（「未取得可交付观察材料」族）。
        assert "未取得可交付观察材料" in converged[0]["content"]
        assert "已交付" not in converged[0]["content"]
        assert "未取得可交付观察材料" in (run.answer or "")
    finally:
        await db.dispose()


# ---------- 验收①补（R3）：直接 refused（闸拒）路径的机读 notice ----------


async def test_refused_gate_notice(tmp_path: Path) -> None:
    # 直接 refused（三分类闸拒——非 bad_args 回喂/retryable 耗尽通道）：
    # 拒因原样如实转答＋机读 notice type="refused"（与 V2-05 闸态分型对齐，
    # 按 notice 类型消费的机读面不漏直接闸拒）；零数值——闸拒不冒充出数。
    engine = FakeQueryEngine(run_error=PermissionError("越权口径：无据出数"))
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_WINDOWED],
    }
    runtime, _completer, db = await make_runtime(tmp_path, engine=engine, script=script)
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        assert "越权拒绝" in answer  # 拒因原样转答（registry 三分类封套消息）
        assert "21.16" not in answer  # 零数值（闸拒不冒充）
        notices = _notices(events)
        refused = [n for n in notices if n.get("type") == "refused"]
        assert len(refused) == 1  # 机读分型恰一条
        assert refused[0]["gates"] == []
        assert "越权拒绝" in refused[0]["content"]
    finally:
        await db.dispose()


# ---------- 验收②：挂起态跨进程恢复（checkpointer 落库，行为约定 8） ----------


async def test_run_recover_after_restart(tmp_path: Path) -> None:
    engine = QueueQueryEngine(
        [
            QueryOutcome.need_clarify(
                question=ASKBACK_TIME_QUESTION,
                choices=ASKBACK_TIME_CHOICES,
            ),
            _rows_outcome(),
        ]
    )
    # 剧本按段分装（ScriptedCompleter 按 caller FIFO——A 段模糊计划出 clarify，
    # B 段起带窗计划＋定稿）。
    script_a: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_VAGUE],
    }
    script_b: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [UNDERSTAND_DATA],
        "v2.runtime.decision": [DECISION_WINDOWED, DECISION_FINALIZE],
        "v2.runtime.answer": [ANSWER_DRAFT_CITED],
    }
    # 进程 A：提问→模糊计划→引擎 need_clarify ASK 挂起（waiting_ask）。
    runtime_a, _completer, db = await make_runtime(tmp_path, engine=engine, script=script_a)
    store = RunStore(db)
    run_id = ""
    try:
        handle = await runtime_a.ask(AskRequest(question="最近的日产油量", actor=ACTOR))
        events = await drain(handle)
        run_id = handle.run_id
        ask_events = [e for e in events if e.event == "ask"]
        assert ask_events, "ASK 帧未发出"
        frame = ask_events[0].data["frame"]
        assert frame["kind"] == "clarify" and frame["options"] == list(ASKBACK_TIME_CHOICES)
        run = await store.get_run(run_id)
        assert run is not None and run.status == "waiting_ask"
        # checkpointer 已落库（挂起前的图状态持久在案——跨进程恢复的物理载体）。
        assert await store.count_checkpoints(run_id) > 0
    finally:
        await db.dispose()

    # 进程 B：全新 ConnectionManager/runtime 实例（同库文件）——凭 run_id resume 续跑完成。
    runtime_b, _completer, db_b = await make_runtime(tmp_path, engine=engine, script=script_b)
    store_b = RunStore(db_b)
    try:
        run_b = await store_b.get_run(run_id)
        assert run_b is not None and run_b.status == "waiting_ask"  # 挂起态跨进程可见
        handle_b = await runtime_b.resume(run_id, AskChoice(value="近 3 天"))
        events_b = await drain(handle_b)
        assert any(e.event == "citation" for e in events_b)  # 恢复段完成出引用
        run_b = await store_b.get_run(run_id)
        assert run_b is not None and run_b.status == "completed"
        assert "21.16" in (run_b.answer or "")
        assert engine.run_calls == 2  # 澄清前零执行（need_clarify 不触 run）＋选择后执行
    finally:
        await db_b.dispose()


# ---------- 验收③：全程无任何写操作落库（INV-2 只读断言） ----------


async def test_readonly_inv2(tmp_path: Path) -> None:
    csv_bytes_before = FIXTURE_CSV.read_bytes()
    knowledge = InMemoryKnowledgeStore(question_array_snapshot(), today=TODAY)
    probe_before = knowledge.metric_by_name("日产油量")
    engine = QueryEngine(
        knowledge=knowledge,
        executor=CsvSnapshotExecutor(),
        waterline=None,
        today=lambda: TODAY,
    )
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=HAPPY_SCRIPT, knowledge=knowledge,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "21.16" in (run.answer or "")
        # INV-2：业务数据零写——CSV 快照逐字节零变＋台账读面零变。
        assert FIXTURE_CSV.read_bytes() == csv_bytes_before
        assert knowledge.metric_by_name("日产油量") == probe_before
    finally:
        await db.dispose()


# ---------- 骨架钉测②：resume 错误路径（V2-07 404/409 的 runtime 异常源） ----------


async def test_resume_error_paths(tmp_path: Path) -> None:
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=HAPPY_SCRIPT
    )
    try:
        # 404 源：resume 到不存在的 run。
        try:
            await runtime.resume("run-not-exist", AskChoice(value="近 3 天"))
        except RunNotFoundError:
            pass
        else:
            raise AssertionError("不存在的 run 未拒绝 resume")
        # 409 源：非挂起态 run 不可 resume（先跑完一个，再 resume 它）。
        handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        await drain(handle)
        try:
            await runtime.resume(handle.run_id, AskChoice(value="近 3 天"))
        except RunNotSuspendedError:
            pass
        else:
            raise AssertionError("非挂起态 run 未拒绝 resume")
    finally:
        await db.dispose()
