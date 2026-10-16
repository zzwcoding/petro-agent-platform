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

import ast
import json
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
    from appv2.runtime.events import EventBus
    from appv2.runtime.graph import build_graph

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
        assert run.manifest_digest  # 收口摘要面（过程态簿记）
        # V2-80h 对话链：只追加——终态链形＝[system, user 任务书, assistant 理解,
        # user 决策包, assistant r1 JSON, user 台账行, assistant r2 JSON,
        # user 作答指令＋材料, assistant 最终答案]（9 条；类型正确性红线）。
        graph_ref = build_graph(
            runtime._executor._deps(EventBus(), run_id=handle.run_id),
            checkpointer=runtime._executor._saver,
        )
        snap = await graph_ref.aget_state({"configurable": {"thread_id": handle.run_id}})
        chain = snap.values["messages"]
        # V2-80h 追加式实态（10 条）：system／任务书→理解／指南包→已做段→
        # r1 JSON→已做段→r2 JSON→作答指令＋材料→最终答案（相邻 user 连发合法）。
        assert [m["role"] for m in chain] == [
            "system", "user", "assistant", "user", "user",
            "assistant", "user", "assistant", "user", "assistant",
        ]
        assert "21.16" in chain[-1]["content"]  # 终答案在链尾
        steps = await store.list_steps(handle.run_id)
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


# ---------- 验收①：预算触界收敛＋未完成项 notice（行 25——runtimev2 编排收口） ----------


async def test_budget_termination() -> None:
    """行 25｜预算触界→收敛答案＋未完成项 notice，无静默截断（runtimev2 编排块收口面）。

    两形（判据只引 `state.budget` 的限额键——本件不写字面预算数值）：

    - **（a）有材料触界**（轮数闸）：轮 1 一支成功、一支被引擎拒（`bad_args` 回炉档）→ 回炉①入口
      即触轮数闸 → 收敛交付**已取得材料逐条**＋notice 明示未完成项（`converge` 的六键落地在
      `bookkeeping`，判定在 `state.check_limits`）；收敛幂等（notice 恰一条）。
    - **（b）零材料触界**（轮预算＝0）：首相位入口即触界 → 如实说明「未取得可交付材料」，
      **不冒充「已交付」**（文案与材料面同源）；零模型决策调用、零执行。

    触界即**有界终止**（不是降级）：run 照常收口为 `completed`，答案面就是收敛正文。
    """
    from appv2.infra.clock import freeze
    from appv2.runtimev2.persistence import RunStore
    from appv2.runtimev2.state import Budget
    from tests.domains import test_v2_four_phase as v2

    # ——（a）有材料触界：轮 1 部分成功 → 回炉轮拒因回喂照耗 → 回炉入口触轮数闸 ——
    dump = v2.v2_ledger_dump()
    note_oil = v2.v2_ledger_note(dump, "日产油量")
    note_liquid = v2.v2_ledger_note(dump, "日产液量")
    engine = v2.V2QueueEngine([v2._rows_outcome()])
    engine.ledger_metric_slots = {"日产油量"}  # 日产液量恒不在槽位集——该支引擎校验拒（回炉档）
    rejected = '{"action": "fly"}'  # 澄清发射越界——拒因回喂轮照耗（收敛钉用）
    understand = json.dumps(
        {"route": "full", "text": "既要数值也要报告佐证。",
         "metric_candidates": ["日产油量", "日产液量"]},
        ensure_ascii=False,
    )
    script = {
        "understand": [understand],
        "decision": [
            json.dumps(
                {
                    "action": "decompose",
                    "question_group": {
                        "subtasks": [
                            {"id": "s1", "question": "2025-09-01 到 09-03 各井日产油量",
                             "ledger_notes": note_oil, "chain": "data"},
                            {"id": "s2", "question": "各井日产液量",
                             "ledger_notes": note_liquid, "chain": "data"},
                        ]
                    },
                },
                ensure_ascii=False,
            ),
            v2.v2_matches(
                v2.v2_data_match(subtask_id="s1", slot="日产油量",
                                 start="2025-09-01", end="2025-09-03"),
                v2.v2_data_match(subtask_id="s2", slot="日产液量",
                                 start="2025-09-01", end="2025-09-03"),
            ),
            rejected,  # 轮 2：拒因回喂照耗（占轮）→ 轮 3 入口触轮数闸
        ],
        "answer": ["（预算触界前无草稿——本用例只测触界收敛面）"],
    }
    v2.wire_ledger_projection(v2.V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2.v2_runtime(
            script=script,
            registry=v2.v2_registry(engine=engine),
            budget=Budget(rounds=2),
        )
        events = await v2.v2_run(runtime, "预算触界综合题")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    row = RunStore().run(run_id)
    assert row is not None and row.status == "completed"
    state = RunStore().load(run_id)
    assert int(state.rounds) == int(state.budget.rounds) == 2  # 轮数闸到顶
    assert state.budget_hit == ["rounds"]  # 机读信号（命中项如实落状态）
    # 已取得材料逐条如实交付（不静默截断）：收敛正文携材料正文与同源清单
    answer = row.answer or ""
    assert "21.16" in answer
    assert "材料清单" in answer
    notices = [event.data for event in events if event.event == "notice"]
    converged = [item for item in notices if item.get("type") == "budget_converged"]
    assert len(converged) == 1  # 收敛幂等：notice 恰一条
    assert converged[0]["gates"] == ["rounds"]
    assert "未完成项" in converged[0]["content"]
    # 触界收敛后不再发模型调用（轮 1 澄清＋匹配、轮 2 澄清照耗——轮 3 入口即收敛）
    assert completer.counts() == {"understand": 1, "decision": 3}

    # ——（b）零材料触界：轮预算 0 → 首相位入口即收敛（如实说明，不冒充已交付） ——
    dump0 = v2.v2_ledger_dump()
    v2.wire_ledger_projection(v2.V2LedgerPort(dump0))
    engine0 = v2.V2QueueEngine([v2._rows_outcome()])
    with freeze("2026-10-08T09:00:00"):
        runtime0, completer0 = v2.v2_runtime(
            script={"understand": [v2.V2_UNDERSTAND], "decision": [], "answer": []},
            registry=v2.v2_registry(engine=engine0),
            budget=Budget(rounds=0),
        )
        events0 = await v2.v2_run(runtime0, "零预算触界题")
    assert events0[-1].event == "blackbox" and events0[-1].data["status"] == "completed"
    run_id0 = events0[-1].data["run_id"]
    answer0 = RunStore().run(run_id0).answer or ""
    assert "未取得可交付材料" in answer0
    assert "已取得材料" not in answer0  # 零材料不冒充「已交付」（文案与材料面同源）
    notices0 = [event.data for event in events0 if event.event == "notice"]
    converged0 = [item for item in notices0 if item.get("type") == "budget_converged"]
    assert len(converged0) == 1
    assert "未完成项" in converged0[0]["content"]
    assert engine0.run_calls == 0  # 触界在首相位：零执行
    assert completer0.counts() == {"understand": 1}  # 零决策调用（收敛不发模型）


# ---------- 验收②：挂起态跨进程恢复（行 27——checkpoint 落表，行为 9） ----------


async def test_run_recover_after_restart() -> None:
    """行 27｜run 挂起态跨进程恢复（checkpoint 落 PG——本件以簿记表件承载「PG」面）。

    两段真跨实例（模拟进程重启）：进程 A 提问 → 引擎侧 ask → run 挂 `waiting_ask`（检查点行落
    `agent_v2_checkpoint*` 三表：执行器状态快照行 ＋ 本块 saver 的分步检查点行）；**进程 B＝全新
    `RunExecutor`／`AgentRuntime` 实例（同一份簿记表）** → 凭 `run_id` resume 续跑收口——总线缺席
    分支（-b 留下的「缺席／已封口回落新起一条」）在此在案，状态重建走检查点读回。
    """
    from appv2.infra.clock import freeze
    from appv2.query import QueryOutcome
    from appv2.runtimev2.orchestration.checkpointer import PgCheckpointer
    from appv2.runtimev2.persistence import (
        CHECKPOINT_KIND_STATE,
        MemoryTables,
        RunStore,
        checkpoint_rows,
    )
    from appv2.runtimev2.state import AskChoice
    from tests.domains import test_v2_four_phase as v2

    dump = v2.v2_ledger_dump()
    note = v2.v2_ledger_note(dump, "日产油量")
    clarify, toolmatch = v2.v2_decision_turn(
        clarify=v2.v2_decompose(
            subtask_id="s1",
            question="2025-09-01 到 09-03 各井日产油量",
            ledger_notes=note,
            chain="data",
        ),
        toolmatch=v2.v2_matches(
            v2.v2_data_match(
                subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03"
            )
        ),
    )
    engine = v2.V2QueueEngine(
        [
            QueryOutcome.need_clarify(
                question=ASKBACK_TIME_QUESTION, choices=ASKBACK_TIME_CHOICES
            ),
            v2._rows_outcome(),
        ]
    )
    tables = MemoryTables()  # 跨实例共享的簿记表（「同库」面）
    v2.wire_ledger_projection(v2.V2LedgerPort(dump))

    # ——进程 A：提问 → 工具侧 ask → 挂起（检查点落表）——
    with freeze("2026-10-08T09:00:00"):
        runtime_a, _completer_a = v2.v2_runtime(
            script={"understand": [v2.V2_UNDERSTAND], "decision": [clarify, toolmatch]},
            registry=v2.v2_registry(engine=engine),
            tables=tables,
        )
        events_a = await v2.v2_run(runtime_a, "最近的日产油量")
    asks = v2.v2_ask_frames(events_a)
    assert asks and asks[-1]["frame"]["kind"] == "clarify"
    run_id = asks[-1]["run_id"]
    assert events_a[-1].event == "verdict" and events_a[-1].data["status"] == "waiting_ask"
    assert RunStore(tables).run(run_id).status == "waiting_ask"
    rows = checkpoint_rows(run_id, tables=tables)
    assert rows, "挂起态检查点未落表"
    assert any(row.kind == CHECKPOINT_KIND_STATE for row in rows)  # 状态快照行（恢复载体）
    assert any(row.kind != CHECKPOINT_KIND_STATE for row in rows)  # saver 分步行（框架面）
    assert await PgCheckpointer().aget_tuple({"configurable": {"thread_id": run_id}}) is not None
    # 检查点 saver 组合契约（本块专责）：只在本块、组合行级口、不直连表（AST 半面）
    _assert_checkpoint_saver_composes_port()

    # ——进程 B：全新实例（同表）凭 run_id resume 续跑收口——
    with freeze("2026-10-08T09:00:00"):
        runtime_b, _completer_b = v2.v2_runtime(
            script={
                "understand": [v2.V2_UNDERSTAND],
                "decision": [clarify, toolmatch],
                "answer": ["答案：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
            },
            registry=v2.v2_registry(engine=engine),
            tables=tables,
        )
        assert RunStore(tables).run(run_id).status == "waiting_ask"  # 挂起态跨实例可见
        resumed, handle_b = await v2.v2_resume(
            runtime_b, run_id, AskChoice(kind="clarify", choice="近 3 天")
        )
    assert resumed[-1].event == "blackbox" and resumed[-1].data["status"] == "completed"
    row = RunStore(tables).run(run_id)
    assert row is not None and row.status == "completed"
    assert "21.16" in (row.answer or "")
    assert not [event for event in resumed if event.event == "ask"]
    # 总线缺席分支（新实例无活体总线）：回落新起一条续编，游标从流首起（回执如实交出）
    assert handle_b.cursor == 0
    assert [event.seq for event in resumed] == list(range(len(resumed)))
    assert engine.run_calls == 2  # 首投挂起（引擎未出数）＋选择后恰补跑一次


# ---------- 验收③：全程业务事实零写（INV-2；行 30） ----------


async def test_readonly_inv2() -> None:
    """行 30｜全程业务事实零写（run 簿记表 agent_v2_* 除外，INV-2）。

    两处机检：①**业务数据面**——真问数引擎（CSV 快照）逐字节零变 ＋ 台账读面零变；②**写面闭世界**
    ——本 run 的全部落行都落在 `agent_v2_*` 簿记表（端口层拒收任何非簿记表写入＝INV-2 的机器面）。
    """
    from appv2.infra.clock import freeze
    from appv2.runtimev2.persistence import BOOKKEEPING_TABLE_PREFIX, MemoryTables, RunStore
    from tests.domains import test_v2_four_phase as v2

    csv_bytes_before = FIXTURE_CSV.read_bytes()
    knowledge = InMemoryKnowledgeStore(question_array_snapshot(), today=TODAY)
    probe_before = knowledge.metric_by_name("日产油量")
    engine = QueryEngine(
        knowledge=knowledge,
        executor=CsvSnapshotExecutor(),
        waterline=None,
        today=lambda: TODAY,
    )
    dump = v2.v2_ledger_dump()
    note = v2.v2_ledger_note(dump, "日产油量")
    script = {
        "understand": [v2.V2_UNDERSTAND],
        "decision": [
            v2.v2_decompose(
                subtask_id="s1",
                question="2025-09-01 到 09-03 各井日产油量",
                ledger_notes=note,
                chain="data",
            ),
            v2.v2_matches(
                v2.v2_data_match(
                    subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03"
                )
            ),
        ],
        "answer": ["答案：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    tables = MemoryTables()
    v2.wire_ledger_projection(v2.V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2.v2_runtime(
            script=script,
            registry=v2.v2_registry(engine=engine, knowledge=knowledge),
            tables=tables,
        )
        events = await v2.v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    assert "21.16" in (RunStore(tables).run(run_id).answer or "")
    # ① 业务数据零写：CSV 快照逐字节零变＋台账读面零变
    assert FIXTURE_CSV.read_bytes() == csv_bytes_before
    assert knowledge.metric_by_name("日产油量") == probe_before
    # ② 写面闭世界：全部落行都在簿记前缀内（业务表零写——INV-2 的端口层把守面）
    assert tables.writes, "零落行＝本用例未覆盖写面（假绿）"
    assert all(
        table.startswith(BOOKKEEPING_TABLE_PREFIX) for table, _key, _op in tables.writes
    )


# ---------- 行 31：三态落库（runtimev2 编排收口面） ----------


async def test_three_terminal_states_persisted() -> None:
    """行 31｜三态落库（completed／failed／waiting_ask 写 run 表）。

    三态各跑一遍真链：①`completed`——四相位走完收口（`answer`／`manifest_digest` 随终态落）；
    ②`failed`——相位链路中断（台账装载失败＝fail-fast）→ fail-closed 收束为 `failed`
    （**不产出半成品答案**）；③`waiting_ask`——工具侧 ask 挂起（本腿收束但 run 未收口）。三态的
    **值域**由 `persistence` 侧把守（`RunRecord.status` ∈ `RUN_STATUS_KINDS` 四值），本块只决定写
    哪个终态；run／步／黑匣子／审计四类记录都携同一 `run_id`（钉 `pin-28` 的**全盖章面**——
    落盘面同钉由 `tests/domains/test_v2_persistence.py::run_id_stamped_across_records` 承载）。
    """
    from appv2.infra.clock import freeze
    from appv2.query import QueryOutcome
    from appv2.runtimev2.persistence import MemoryTables, RunStore, StepRecord
    from appv2.runtimev2.state import RUN_STATUS_KINDS
    from tests.domains import test_v2_four_phase as v2

    dump = v2.v2_ledger_dump()
    note = v2.v2_ledger_note(dump, "日产油量")
    clarify, toolmatch = v2.v2_decision_turn(
        clarify=v2.v2_decompose(
            subtask_id="s1",
            question="2025-09-01 到 09-03 各井日产油量",
            ledger_notes=note,
            chain="data",
        ),
        toolmatch=v2.v2_matches(
            v2.v2_data_match(
                subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03"
            )
        ),
    )
    tables = MemoryTables()

    # ① completed：四相位走完
    v2.wire_ledger_projection(v2.V2LedgerPort(dump))
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2.v2_runtime(
            script={"understand": [v2.V2_UNDERSTAND], "decision": [clarify, toolmatch],
                    "answer": ["答案：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"]},
            registry=v2.v2_registry(engine=v2.V2QueueEngine([v2._rows_outcome()])),
            tables=tables,
        )
        completed_events = await v2.v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    completed_id = completed_events[-1].data["run_id"]
    completed = RunStore(tables).run(completed_id)
    assert completed is not None and completed.status == "completed"
    assert completed.answer and completed.manifest_digest  # 随终态落

    # ② failed：台账装载失败（外部依赖中断）→ fail-closed，不产出半成品答案
    class _BrokenLedger:
        async def fetch(self) -> dict[str, Any]:
            raise RuntimeError("台账投影端口中断")

    v2.wire_ledger_projection(_BrokenLedger())
    with freeze("2026-10-08T09:00:00"):
        runtime_f, _completer_f = v2.v2_runtime(
            script={"understand": [v2.V2_UNDERSTAND], "decision": [clarify, toolmatch]},
            registry=v2.v2_registry(engine=v2.V2QueueEngine([v2._rows_outcome()])),
            tables=tables,
        )
        failed_events = await v2.v2_run(runtime_f, "台账装载失败题")
    failed_id = failed_events[-1].data["run_id"]
    failed = RunStore(tables).run(failed_id)
    assert failed is not None and failed.status == "failed"
    assert failed.error  # 失败如实留痕
    assert not (failed.answer or ""), "非法降级：失败不得产出半成品答案"
    assert any(
        event.data.get("type") == "run_failed"
        for event in failed_events
        if event.event == "notice"
    )

    # ③ waiting_ask：工具侧 ask 挂起（本腿收束、run 未收口）
    dump_ask = v2.v2_ledger_dump()
    note_ask = v2.v2_ledger_note(dump_ask, "日产油量")
    v2.wire_ledger_projection(v2.V2LedgerPort(dump_ask))
    ask_engine = v2.V2QueueEngine(
        [
            QueryOutcome.need_clarify(
                question=ASKBACK_TIME_QUESTION, choices=ASKBACK_TIME_CHOICES
            )
        ]
    )
    with freeze("2026-10-08T09:00:00"):
        runtime_ask, _completer_ask = v2.v2_runtime(
            script={
                "understand": [v2.V2_UNDERSTAND],
                "decision": [
                    v2.v2_decompose(subtask_id="s1", question="最近的日产油量",
                                    ledger_notes=note_ask, chain="data"),
                    v2.v2_matches(
                        v2.v2_data_match(subtask_id="s1", slot="日产油量",
                                         start="2025-09-01", end="2025-09-03")
                    ),
                ],
            },
            registry=v2.v2_registry(engine=ask_engine),
            tables=tables,
        )
        ask_events = await v2.v2_run(runtime_ask, "最近的日产油量")
    asks = v2.v2_ask_frames(ask_events)
    assert asks
    ask_id = asks[-1]["run_id"]
    suspended = RunStore(tables).run(ask_id)
    assert suspended is not None and suspended.status == "waiting_ask"
    assert suspended.answer is None, "挂起态不落答案（run 未收口）"

    # 三态取值全落在闭世界内（值域把守归 persistence 侧）
    assert {completed.status, failed.status, suspended.status} <= RUN_STATUS_KINDS
    # 钉 pin-28 的全盖章面：run／步／黑匣子／审计四类记录都携同一 run_id
    store = RunStore(tables)
    for row in (completed, failed, suspended):
        assert row.run_id in {completed_id, failed_id, ask_id}
        for record in store.steps(row.run_id):
            assert isinstance(record, StepRecord) and record.run_id == row.run_id
    assert store.blackbox(completed_id) is not None
    audits = v2.v2_audit_records()  # ③那一段的审计写口收集（本 run 受理留痕）
    assert audits and {record.run_id for record in audits} == {ask_id}


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


# ---------- 编排面钉（RT-W5-01a 行 34：图装配与路由表集中） ----------


def test_routing_table_centralized() -> None:
    """行 34｜图装配与路由表集中（业务相位不自行跳转）。

    两处机检：①**AST／grep**——`StateGraph`／条件边只出现在 `orchestration` 一处（其余 16 块零
    命中：相位不得自建图、不得自建路由）；②**黑盒观测**——本块装配出的图确有四相位节点与
    「回决策」条件边（节点集合与边集合来自本块集中装配，不由相位决定）。
    """
    import pathlib as _pathlib

    root = _pathlib.Path("appv2/runtimev2")
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts or path.parent.name == "orchestration":
            continue
        text = path.read_text(encoding="utf-8")
        assert "StateGraph" not in text, f"相位自建图（路由分散）：{path}"
        assert "add_conditional_edges" not in text, f"相位自建条件边（路由分散）：{path}"

    orchestrator = (root / "orchestration" / "graph.py").read_text(encoding="utf-8")
    assert "StateGraph" in orchestrator and "add_conditional_edges" in orchestrator
    assert "_ROUTES" in orchestrator  # 路由表＝本块单点

    from appv2.runtimev2.orchestration.graph import LoopDeps, build_graph
    from appv2.runtimev2.persistence import MemoryTables, RunStore, configure_tables
    from appv2.runtimev2.transport import EventBus
    from appv2.tools import FakeKnowledgeStore, FakeQueryEngine, FakeRetrievalEngine, ToolRegistry

    configure_tables(MemoryTables())
    deps = LoopDeps(
        bus=EventBus(),
        registry=ToolRegistry(
            knowledge=FakeKnowledgeStore(),
            query=FakeQueryEngine(),
            retrieval=FakeRetrievalEngine(),
        ),
        store=RunStore(),
    )
    view = build_graph(deps).get_graph()
    nodes = {str(node) for node in view.nodes}
    assert {"understand", "clarify", "toolmatch", "precondition", "batch"} <= nodes
    edges = {
        (str(getattr(edge, "source", edge[0])), str(getattr(edge, "target", edge[1])))
        for edge in view.edges
    }
    assert ("clarify", "toolmatch") in edges and ("precondition", "batch") in edges


# ---------- 行 32：审计留痕经唯一写口（action 闭世界七值） ----------


async def test_audit_wiring_action_closed_world() -> None:
    """行 32｜审计留痕经 `security.audit` 唯一写口（**action 闭世界七值**，计数只此一个口径）。

    落地面＝本块 `orchestration.audit`（`RT-W5-01c`）：受理／三态收口／拒答收口／外表审批决定／
    禁用词豁免五处留痕都构造 `persistence.AuditRecord` 交给 `persistence.audit`（唯一写口＝
    `security.audit` 桥，B12）。三处机检：

    ①**口径单点**——`AUDIT_PLACES`（五处 → action 取值）摊平后恰等于 `persistence.AUDIT_ACTIONS`
      七值（本块零字面量、不写类数）；
    ②**行为**——真链跑出受理／审批决定／收口的 action 行，拒答轮落 `refused` 行，全部落在七值内且
      恒 `agent_v2.` 前缀、四要素齐备（守门在 `persistence` 侧）；
    ③**唯一写口**——本块只 import `persistence` 的写口（AST），不直引审计存储／不另开第二写路。
    """

    from appv2.infra.security import Actor
    from appv2.runtimev2.orchestration.audit import AUDIT_PLACES
    from appv2.runtimev2.persistence import (
        AUDIT_ACTION_EXTABLE_APPROVED,
        AUDIT_ACTION_PREFIX,
        AUDIT_ACTION_REFUSED,
        AUDIT_ACTION_RUN_COMPLETED,
        AUDIT_ACTION_RUN_CREATED,
        AUDIT_ACTIONS,
        AUDIT_REQUIRED_FIELDS,
        MemoryTables,
        RunStore,
    )
    from appv2.runtimev2.state import AskChoice as V2AskChoice
    from appv2.runtimev2.state import AskRequest as V2AskRequest
    from tests.domains import test_v2_four_phase as v2

    # 身份桩（五角色键注册表内的角色——恢复腿的 who 槽经唯一身份缝重解析，故须用已登记身份）
    actor = Actor(user_id="aqiang", display="阿强 · 平台运维")

    # ① 计数口径单点：五处留痕摊平后恰为七值闭世界
    placed = {action for actions in AUDIT_PLACES.values() for action in actions}
    assert placed == AUDIT_ACTIONS
    assert all(action.startswith(AUDIT_ACTION_PREFIX) for action in placed)
    assert set(AUDIT_PLACES) == {"受理", "三态收口", "拒答收口", "外表审批决定", "禁用词豁免"}

    # ② 行为：越集审批挂起 → 批准 → 收口（受理／决定／收口三处留痕同源可聚合）
    dump = v2.v2_ledger_dump()
    note = v2.v2_ledger_note(dump, "日产油量")
    match = v2.v2_data_match(
        subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03"
    )
    match["plan"]["external_tables"] = ["erp_well_register"]
    v2.wire_ledger_projection(v2.V2LedgerPort(dump))
    tables = MemoryTables()
    from appv2.infra.clock import freeze

    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2.v2_runtime(
            script={
                "understand": [v2.V2_UNDERSTAND],
                "decision": [
                    v2.v2_decompose(subtask_id="s1", question="井位台账关联的日产油量",
                                    ledger_notes=note, chain="data"),
                    v2.v2_matches(match),
                ],
                "answer": ["s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
            },
            registry=v2.v2_registry(engine=v2.V2QueueEngine([v2._rows_outcome()])),
            tables=tables,
        )
        handle = await runtime.ask(V2AskRequest(question="外表越集审批恢复题", actor=actor))
        events = [event async for event in handle.stream]
        frame = v2.v2_ask_frames(events)[-1]["frame"]
        run_id = v2.v2_ask_frames(events)[-1]["run_id"]
        await v2.v2_resume(
            runtime,
            run_id,
            V2AskChoice(
                kind="external_table_approval",
                decision="approve",
                approval_id=frame["detail"]["approval_id"],
            ),
        )
    records = v2.v2_audit_records()
    actions = [record.action for record in records]
    assert actions == [
        AUDIT_ACTION_RUN_CREATED,
        AUDIT_ACTION_EXTABLE_APPROVED,
        AUDIT_ACTION_RUN_COMPLETED,
    ]
    for record in records:
        assert record.action in AUDIT_ACTIONS  # 七值闭世界
        assert record.run_id == run_id  # 范围键（四类记录同源可聚合）
        assert all(getattr(record, name) for name in AUDIT_REQUIRED_FIELDS)  # 四要素齐备
    assert RunStore(tables).run(run_id).status == "completed"

    # ②b 拒答收口：引擎闸拒（终局）→ 终态留痕为 `refused`（与正常收口互斥）
    dump_refused = v2.v2_ledger_dump()
    note_refused = v2.v2_ledger_note(dump_refused, "日产油量")
    v2.wire_ledger_projection(v2.V2LedgerPort(dump_refused))
    refused_reason = "口径/数据闸拒：所问口径无据——不代答"
    with freeze("2026-10-08T09:00:00"):
        runtime_r, _completer_r = v2.v2_runtime(
            script={
                "understand": [v2.V2_UNDERSTAND],
                "decision": [
                    v2.v2_decompose(subtask_id="s1", question="2025-09-01 到 09-03 各井日产油量",
                                    ledger_notes=note_refused, chain="data"),
                    v2.v2_matches(
                        v2.v2_data_match(subtask_id="s1", slot="日产油量",
                                         start="2025-09-01", end="2025-09-03")
                    ),
                ],
                "answer": ["所问井日产油量的取数被闸拒，拒因见缺口面——不代答。"],
            },
            registry=v2.v2_registry(
                engine=v2.V2QueueEngine([QueryOutcome.refuse(reason=refused_reason)])
            ),
            tables=tables,
        )
        refused_handle = await runtime_r.ask(V2AskRequest(question="全拒批次题", actor=actor))
        refused_events = [event async for event in refused_handle.stream]
    refused_id = refused_events[-1].data["run_id"]
    refused_actions = [record.action for record in v2.v2_audit_records()]
    assert AUDIT_ACTION_RUN_CREATED in refused_actions
    assert AUDIT_ACTION_REFUSED in refused_actions
    assert AUDIT_ACTION_RUN_COMPLETED not in refused_actions  # 两值互斥（终态恰一行）
    assert any(
        event.data.get("type") == "subtask_refused"
        for event in refused_events
        if event.event == "notice"
    )
    assert RunStore(tables).run(refused_id).status == "completed"

    # ③ 唯一写口：本块只经 `persistence.audit`（AST——不直引审计存储／不引 security 写口件）
    _assert_audit_single_write_port()


# ---------- 行 33：身份缝单一入口（身份解析只经 resolve_actor） ----------


async def test_identity_seam_single_entry() -> None:
    """行 33｜身份缝单一入口（身份解析只经 `resolve_actor`）。

    规格原文（`specs/agent-loop.md:154`）：「请求身份经 `infra.security.resolve_actor` 解析（开发期
    身份桩；正式接 OAuth2.0 **只换该函数实现**，其余零改动）」。四处机检：

    ①**受理腿**——`who` 槽取入口点已解析的 `Actor` 全名（本块**不重解析**：非注册 id 也照用其
      `display`），空身份经 `resolve_actor` 落缺省角色；
    ②**行级投影单点**——`AskRequest.actor`（对象面）→ `state.actor`／run 行的行级身份串（＝
      `user_id`）的转换点唯一在受理段；
    ③**恢复腿**——run 行只有行级身份串，`who` 槽经唯一身份缝 `resolve_actor` 重解析（不猜全名、
      不自建角色表）；
    ④**AST**——runtimev2 全树零身份解析复制（无请求头字面 `X-Dev-User`、无角色注册表复制），
      身份缝消费点在编排块单点。
    """
    from appv2.infra.security import Actor, resolve_actor
    from appv2.query import QueryOutcome
    from appv2.runtimev2.persistence import MemoryTables, RunStore
    from appv2.runtimev2.state import AskChoice as V2AskChoice
    from appv2.runtimev2.state import AskRequest as V2AskRequest
    from tests.domains import test_v2_four_phase as v2

    # ① 受理腿两形：入口点已解析的全名照用；空身份经唯一缝落缺省角色
    dump = v2.v2_ledger_dump()
    v2.wire_ledger_projection(v2.V2LedgerPort(dump))
    note = v2.v2_ledger_note(dump, "日产油量")
    tables = MemoryTables()
    from appv2.infra.clock import freeze

    script = {
        "understand": [v2.V2_UNDERSTAND],
        "decision": [
            v2.v2_decompose(subtask_id="s1", question="2025-09-01 到 09-03 各井日产油量",
                            ledger_notes=note, chain="data"),
            v2.v2_matches(
                v2.v2_data_match(subtask_id="s1", slot="日产油量",
                                 start="2025-09-01", end="2025-09-03")
            ),
        ],
        "answer": ["答案：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2.v2_runtime(
            script=script,
            registry=v2.v2_registry(engine=v2.V2QueueEngine([v2._rows_outcome()])),
            tables=tables,
        )
        named = Actor(user_id="dev-u1", display="开发用户")  # 非注册 id：本块不重解析，照用 display
        handle = await runtime.ask(V2AskRequest(question="身份缝题", actor=named))
        events = [event async for event in handle.stream]
        named_id = events[-1].data["run_id"]
        anonymous = await runtime.ask(V2AskRequest(question="空身份题", actor=None))  # type: ignore[arg-type]
        anon_events = [event async for event in anonymous.stream]
        anon_id = anon_events[-1].data["run_id"]
    records = {record.run_id: record for record in v2.v2_audit_records()}
    assert records[named_id].who == "开发用户"  # 入口点已解析的全名（零重解析）
    assert records[anon_id].who == resolve_actor(None).who  # 空身份 → 唯一缝落缺省角色

    # ② 行级投影单点：对象面 → 行级身份串（user_id），run 行与状态同源
    named_row = RunStore(tables).run(named_id)
    assert named_row is not None
    assert named_row.actor == "dev-u1" == RunStore(tables).load(named_id).actor
    anon_row = RunStore(tables).run(anon_id)
    assert anon_row is not None and anon_row.actor == ""

    # ③ 恢复腿：行级身份串经唯一身份缝重解析（跨实例 resume → 收口审计 who）
    audit_dump = v2.v2_ledger_dump()
    audit_note = v2.v2_ledger_note(audit_dump, "日产油量")
    v2.wire_ledger_projection(v2.V2LedgerPort(audit_dump))
    engine = v2.V2QueueEngine(
        [
            QueryOutcome.need_clarify(
                question=ASKBACK_TIME_QUESTION, choices=ASKBACK_TIME_CHOICES
            ),
            v2._rows_outcome(),
        ]
    )
    ask_actor = Actor(user_id="aqiang", display="阿强 · 平台运维")
    resume_tables = MemoryTables()
    with freeze("2026-10-08T09:00:00"):
        runtime_a, _completer_a = v2.v2_runtime(
            script={
                "understand": [v2.V2_UNDERSTAND],
                "decision": [
                    v2.v2_decompose(subtask_id="s1", question="最近的日产油量",
                                    ledger_notes=audit_note, chain="data"),
                    v2.v2_matches(
                        v2.v2_data_match(subtask_id="s1", slot="日产油量",
                                         start="2025-09-01", end="2025-09-03")
                    ),
                ],
            },
            registry=v2.v2_registry(engine=engine),
            tables=resume_tables,
        )
        suspend = await runtime_a.ask(V2AskRequest(question="最近的日产油量", actor=ask_actor))
        suspend_events = [event async for event in suspend.stream]
    run_id = v2.v2_ask_frames(suspend_events)[-1]["run_id"]
    assert RunStore(resume_tables).run(run_id).actor == "aqiang"  # 行级串＝user_id（非全名）
    with freeze("2026-10-08T09:00:00"):
        runtime_b, _completer_b = v2.v2_runtime(
            script={
                "understand": [v2.V2_UNDERSTAND],
                "decision": [
                    v2.v2_decompose(subtask_id="s1", question="2025-09-01 到 09-03 各井日产油量",
                                    ledger_notes=audit_note, chain="data"),
                    v2.v2_matches(
                        v2.v2_data_match(subtask_id="s1", slot="日产油量",
                                         start="2025-09-01", end="2025-09-03")
                    ),
                ],
                "answer": ["答案：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
            },
            registry=v2.v2_registry(engine=engine),
            tables=resume_tables,
        )
        resumed, _handle_b = await v2.v2_resume(
            runtime_b, run_id, V2AskChoice(kind="clarify", choice="近 3 天")
        )
    assert resumed[-1].data["status"] == "completed"
    terminal = {
        record.action: record for record in v2.v2_audit_records() if record.run_id == run_id
    }
    assert terminal["agent_v2.run_completed"].who == resolve_actor("aqiang").who

    # ④ AST：runtimev2 全树零身份解析复制；身份缝消费点在编排块单点
    _assert_identity_seam_single_entry()


# ---------- AST 扫描件（同步件——不进 async 测试体，避 ASYNC240） ----------


def _scan_sources(root: str) -> list[tuple[str, ast.Module]]:
    """按源码树解析全部模块（返回 (路径, AST) 序列）。"""
    return [
        (str(path), ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(Path(root).rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def _assert_audit_single_write_port() -> None:
    """行 32 的 AST 半面：审计只经 `persistence.audit` 唯一写口（不直引审计存储／写口件）。"""
    seen_audit_import = False
    for name, tree in _scan_sources("appv2/runtimev2/orchestration"):
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if node.module == "appv2.runtimev2.persistence":
                seen_audit_import = seen_audit_import or any(
                    alias.name == "audit" for alias in node.names
                )
            assert node.module != "appv2.infra.security.store", f"直引审计存储：{name}"
            assert not (
                node.module == "appv2.infra.security"
                and any(alias.name in {"SecurityService", "AuditRow"} for alias in node.names)
            ), f"直引审计写口件（应经 persistence.audit 唯一写口）：{name}"
    assert seen_audit_import, "未经唯一写口 persistence.audit 落痕（假绿）"


def _assert_identity_seam_single_entry() -> None:
    """行 33 的 AST 半面：runtimev2 全树零身份解析复制；身份缝消费点在编排块单点。"""
    seam_importers: set[str] = set()
    for name, tree in _scan_sources("appv2/runtimev2"):
        text = Path(name).read_text(encoding="utf-8")
        assert "X-Dev-User" not in text, f"runtimev2 出现请求头字面（身份解析越界）：{name}"
        assert "ROLE_REGISTRY" not in text, f"runtimev2 复制角色注册表（第二套身份真源）：{name}"
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "appv2.infra.security":
                if any(alias.name == "resolve_actor" for alias in node.names):
                    seam_importers.add(name)
    assert seam_importers == {"appv2/runtimev2/orchestration/audit.py"}, (
        f"身份缝消费点不唯一：{sorted(seam_importers)}"
    )


def _assert_checkpoint_saver_composes_port() -> None:
    """行 27 的「saver 组合契约」AST 半面（`RT-W5-01c` 验收节逐字面）。

    三处机检：① **框架类型只在本块**——`langgraph.checkpoint`（`BaseCheckpointSaver` 一族）在
    runtimev2 全树（17 块）里只在 `appv2/runtimev2/orchestration/` 出现（R5b 的 AST 面；旧码
    `appv2/runtime/` 为 ADR-0007 备份面、不在 R5b 的 source 集内）；② **组合而非直连**——本块只经
    `persistence` 的五个框架无关行级口读写检查点，零表级直连符号（不 import
    `persistence.tables`，不出现 DB driver）；③ **表前缀隔离**——写面落在 `agent_v2_*` 簿记表
    （由 `persistence` 端口把守，见 `::test_readonly_inv2` 的写面断言）。
    """
    framework_importers: set[str] = set()
    for name, tree in _scan_sources("appv2/runtimev2"):
        for node in ast.walk(tree):
            for module in (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            ):
                if module and (
                    module == "langgraph" or module.startswith("langgraph.")
                ):
                    framework_importers.add(name)
    assert framework_importers, "未发现框架 saver 落点（假绿）"
    assert all("orchestration" in name for name in framework_importers), (
        f"框架类型越界（R5b：只许 orchestration）：{sorted(framework_importers)}"
    )

    saver = Path("appv2/runtimev2/orchestration/checkpointer.py")
    assert saver.is_file()
    tree = ast.parse(saver.read_text(encoding="utf-8"))
    ports = {
        "put_checkpoint_rows",
        "checkpoint_rows",
        "checkpoint_blobs",
        "checkpoint_writes",
        "delete_thread",
    }
    imported_ports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "appv2.runtimev2.persistence":
            imported_ports |= {alias.name for alias in node.names}
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(
                    (
                        "sqlalchemy",
                        "asyncpg",
                        "psycopg",
                        "aiosqlite",
                        "appv2.runtimev2.persistence.tables",
                    )
                ), f"saver 直连表／DB driver：{alias.name}"
    assert ports <= imported_ports, (
        f"saver 未组合全部行级口：{sorted(ports - imported_ports)}"
    )
    # 全块零表级直连符号（表名常量与行操作面不经本块）
    for name, tree in _scan_sources("appv2/runtimev2/orchestration"):
        for node in ast.walk(tree):
            for module in (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else ([node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            ):
                assert not (module or "").startswith(
                    ("sqlalchemy", "asyncpg", "psycopg", "aiosqlite")
                ), f"本块出现裸 DB driver：{name} -> {module}"
                assert module != "appv2.runtimev2.persistence.tables", (
                    f"本块直引表名／行操作面（应经行级口）：{name}"
                )
