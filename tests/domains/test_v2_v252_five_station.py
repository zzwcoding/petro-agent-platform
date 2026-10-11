"""V2-52 五站缺口迁移批——骨架钉测（P-051 开发拍，TDD 红先绿后）。

五站＝V1 能力在 ReAct/四相位下的行为等效重建（票面：重建非照搬）：
- FAQ 直出链：N18 种子（faq_entry serve）精确命中→直出语义（不走检索执行，
  语义锚定 FAQ 条目，零模型调用）；
- 术语词条卡（含届满标注/争议注记随卡）：术语定义问→词条卡收口（台账行原文
  ＋term_expiry 展示串）；
- N1 禁用词硬终止链：禁用词命中（非元问句形）→硬终止拒答＋审计留痕
  （security.audit 唯一写口 agent_v2.refused）；元问句/引用形豁免＝词条卡收口
  （禁用标注＋替代词随卡，不拦停）；
- 越集 interrupt 续跑通道：V2-44 引擎侧拦停→resume 批准→续跑（前置重判→
  批量重执行→引擎按放行态出数——骨架收口段补齐为全通道）。

判定面全部纯固定代码零 LLM（tools.precondition fast_lane_verdict＋
knowledge.pg_faq 精确匹配）；运行面挂 understand 入口（先于一切解析——
V1 W-F19 0 号位语义的 ReAct 形承载）。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select, text

from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.infra.security.store import AuditLog
from appv2.knowledge import PgFaqStore
from appv2.query import QueryOutcome
from appv2.runtime import AskChoice, AskRequest, RunStore
from appv2.tools import (
    FakeQueryEngine,
    FastLaneClosure,
    fast_lane_verdict,
    ledger_facts,
)
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    QueueQueryEngine,
    drain,
    make_runtime,
)
from tests.domains.test_v2_four_phase import LEDGER_DUMP
from tests.domains.test_v2_react_loop import _rows_outcome

TODAY = date(2026, 10, 8)

# ---------- 词典层底座：系统级台账行（行值誊自 PG sem_term 种子，零业务发明） ----------

_SYS_TERMS: list[dict[str, Any]] = [
    {
        "term": "老完成率", "banned": True, "freshness": "—（已禁用）",
        "value": "老完成率（禁用词 · 禁用（替代：产量完成率））："
                 "v1 口径（不含自用油折算），2024 年废弃",
        "source_id": "1",
    },
    {
        "term": "躺井", "banned": False, "freshness": "2026-12-31",
        "value": "躺井（黑话 → 停产待检泵 · 有效（限作业区语境））：作业区口语",
        "source_id": "4",
    },
    {
        "term": "日产液", "banned": False, "freshness": "2026-06-30（已届满）",
        "value": "日产液（别名 → 日产液量 · 有效（已届满））：作业区口语缩写",
        "source_id": "11",
    },
    {
        "term": "递减增油", "banned": False, "freshness": "2027-03-31",
        "value": "递减增油（术语 · 有效（待联席裁决））：见指标 10（含口径争议注记）",
        "source_id": "7",
    },
]


def _sys_dump() -> dict[str, Any]:
    """问数组台账 dump＋系统级术语行（fast lane 判定输入——行值零发明）。"""
    dump = json.loads(json.dumps(LEDGER_DUMP, ensure_ascii=False))
    dump["terms"] = [dict(row) for row in _SYS_TERMS]
    return dump


def _faq_seam_hit(entry_id: str, question: str, answer: str) -> Any:
    """剧本 FAQ 缝（生产＝PgFaqStore.lookup——测试按同形回罐头）。"""

    class _Hit:
        pass

    hit = _Hit()
    hit.entry_id = entry_id
    hit.question = question
    hit.answer = answer
    return hit


# ---------- 判定面单测：定义形提取＋LedgerFacts terms 投影＋fast_lane_verdict ----------


def test_ledger_facts_terms_projection() -> None:
    """LedgerFacts 增 terms 投影（词典层 dump terms 行→TermFact——additive）。"""
    facts = ledger_facts(_sys_dump())
    assert [item.term for item in facts.terms] == [
        "老完成率", "躺井", "日产液", "递减增油",
    ]
    expired = next(item for item in facts.terms if item.term == "日产液")
    assert expired.freshness == "2026-06-30（已届满）"
    banned = next(item for item in facts.terms if item.banned)
    assert banned.term == "老完成率"


def test_fast_lane_verdict_forms() -> None:
    """fast_lane_verdict 四形：词条卡（届满/语境/争议随卡）／禁用词硬终止／
    元问句豁免（禁用词条卡）／普通问零触发。"""
    facts = ledger_facts(_sys_dump())

    # ① 定义形＋届满术语 → 词条卡（届满标注随卡）。
    out = fast_lane_verdict("什么是日产液？", facts)
    assert isinstance(out, FastLaneClosure)
    assert out.kind == "term_card"
    assert "作业区口语缩写" in out.answer
    assert "2026-06-30（已届满）" in out.answer  # 届满标注随词条卡面

    # ② 定义形＋争议注记术语 → 词条卡（status 注记随卡）。
    out = fast_lane_verdict("递减增油是什么意思？", facts)
    assert out is not None and out.kind == "term_card"
    assert "待联席裁决" in out.answer

    # ③ 禁用词元问句形 → 豁免（词条卡收口——禁用标注＋替代词随卡，不拦停）。
    out = fast_lane_verdict("「老完成率」是什么口径？", facts)
    assert out is not None and out.kind == "term_card"
    assert "禁用" in out.answer and "产量完成率" in out.answer

    # ④ 禁用词非定义形 → N1 硬终止（拒因带替代词）。
    out = fast_lane_verdict("老完成率是多少？", facts)
    assert out is not None and out.kind == "banned"
    assert "老完成率" in out.answer and "产量完成率" in out.answer

    # ⑤ 普通问句零触发（非定义形/无禁用词——fast lane 静默）。
    assert fast_lane_verdict("2025-09-01 到 09-03 各井日产油量", facts) is None
    # ⑥ 定义形但候选不在台账 → 零触发（exact-match 防误伤——躺井率≠躺井）。
    assert fast_lane_verdict("什么是躺井率？", facts) is None


# ---------- FAQ 读面（pg_faq）：serve 精确命中＋相似问＋非 serve 排除 ----------

_FAQ_DDL = (
    """CREATE TABLE faq_entry (
        id VARCHAR(32) PRIMARY KEY, question TEXT NOT NULL,
        answer TEXT NOT NULL, status VARCHAR(16) NOT NULL)""",
    """CREATE TABLE faq_similar_question (
        id INTEGER PRIMARY KEY, entry_id VARCHAR(32) NOT NULL, text TEXT NOT NULL)""",
)

_FAQ_SEED = [
    (
        "faq-3", "「躺井」是什么意思？",
        "停产待检泵，作业区口语（限作业区语境；Owner：采油工艺所）", "serve",
    ),
    ("faq-4", "N-02 井是什么时候投产的？", "2019-06-15 投产。", "serve"),
    ("faq-8", "「老完成率」是什么口径？", "已禁用——现行口径为产量完成率。", "disabled"),
]


async def _faq_db(tmp_path: Path) -> ConnectionManager:
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "faq.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    db = ConnectionManager([spec])
    async with db.session() as session:
        for ddl in _FAQ_DDL:
            await session.execute(text(ddl))
        for entry_id, question, answer, status in _FAQ_SEED:
            await session.execute(
                text("INSERT INTO faq_entry (id, question, answer, status)"
                     " VALUES (:id, :q, :a, :s)"),
                {"id": entry_id, "q": question, "a": answer, "s": status},
            )
        await session.execute(
            text("INSERT INTO faq_similar_question (id, entry_id, text)"
                 " VALUES (1, 'faq-3', '躺井啥意思')"),
        )
    return db


async def test_pg_faq_store_lookup(tmp_path: Path) -> None:
    """PgFaqStore：serve 标准问/相似问精确命中；disabled 排除；未命中 None。"""
    db = await _faq_db(tmp_path)
    try:
        store = PgFaqStore.from_specs(_spec_of(tmp_path))
        hit = store.lookup("N-02 井是什么时候投产的？")
        assert hit is not None and hit.entry_id == "faq-4"
        assert hit.answer == "2019-06-15 投产。"
        hit = store.lookup("躺井啥意思")  # 相似问精确命中
        assert hit is not None and hit.entry_id == "faq-3"
        assert store.lookup("「老完成率」是什么口径？") is None  # disabled 不消费
        assert store.lookup("随便问一句") is None
    finally:
        await db.dispose()


def _spec_of(tmp_path: Path) -> DatabaseSpec:
    return DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "faq.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )


# ---------- 端到端钉测①：FAQ 直出（零模型——直出语义不走检索执行） ----------


async def test_station_faq_direct_zero_model(tmp_path: Path) -> None:
    dump = _sys_dump()
    script: dict[str, Sequence[str]] = {"v2.runtime.understand": [], "v2.runtime.decision": []}
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(dump),
        faq_lookup=lambda q: (
            _faq_seam_hit("faq-4", "N-02 井是什么时候投产的？", "2019-06-15 投产。")
            if q == "N-02 井是什么时候投产的？" else None
        ),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="N-02 井是什么时候投产的？", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "2019-06-15 投产" in (run.answer or "")  # 语义锚定 FAQ 条目直出
        assert "FAQ 直出" in (run.answer or "")  # 未调用模型标注（no_model 语义）
        assert completer.counts() == {}  # 零模型调用（秒回——不走检索执行）
        notices = [e.data for e in events if e.event == "notice"]
        faq_notice = next(n for n in notices if n.get("type") == "faq_direct")
        assert "N-02 井" in faq_notice["content"]
    finally:
        await db.dispose()


# ---------- 端到端钉测②：术语词条卡收口（届满标注随卡——零模型） ----------


async def test_station_term_card_expiry(tmp_path: Path) -> None:
    dump = _sys_dump()
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]),
        script={"v2.runtime.understand": [], "v2.runtime.decision": []},
        four_phase=True, ledger_dump=lambda: dict(dump),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question="什么是日产液？", actor=ACTOR))
        await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        assert "日产液" in answer and "作业区口语缩写" in answer
        assert "2026-06-30（已届满）" in answer  # 届满漂移标注随词条卡
        assert completer.counts() == {}  # 词条卡收口零模型
    finally:
        await db.dispose()


# ---------- 端到端钉测③：N1 硬终止＋审计留痕（agent_v2.refused） ----------


async def test_station_n1_hard_stop_with_audit(tmp_path: Path) -> None:
    dump = _sys_dump()
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]),
        script={"v2.runtime.understand": [], "v2.runtime.decision": []},
        four_phase=True, ledger_dump=lambda: dict(dump),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question="老完成率是多少？", actor=ACTOR))
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        assert "老完成率" in answer and "产量完成率" in answer  # 拒因带替代词
        assert "21.16" not in answer  # 零数值（硬终止不冒充出数）
        assert completer.counts() == {}  # 先于一切解析——零模型调用
        notices = [e.data for e in events if e.event == "notice"]
        refused = [n for n in notices if n.get("type") == "refused"]
        assert len(refused) == 1  # 机读分型恰一条（审计同源面）
        # 审计留痕：拒答收口一行（security.audit 唯一写口——B12）。
        async with db.readonly() as session:
            rows = (
                (await session.execute(select(AuditLog).order_by(AuditLog.id)))
                .scalars()
                .all()
            )
        assert [row.action for row in rows] == ["agent_v2.run_created", "agent_v2.refused"]
    finally:
        await db.dispose()


# ---------- 端到端钉测④：N1 元问句豁免（禁用词条卡——不拦停） ----------


async def test_station_n1_meta_question_exempt(tmp_path: Path) -> None:
    dump = _sys_dump()
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]),
        script={"v2.runtime.understand": [], "v2.runtime.decision": []},
        four_phase=True, ledger_dump=lambda: dict(dump),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="「老完成率」是什么口径？", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        assert "产量完成率" in answer and "禁用" in answer  # 词条卡（禁用标注随卡）
        notices = [e.data for e in events if e.event == "notice"]
        assert not [n for n in notices if n.get("type") == "refused"]  # 豁免不拦停
        assert any(n.get("type") == "term_card" for n in notices)
        assert completer.counts() == {}
    finally:
        await db.dispose()


# ---------- 端到端钉测⑤：fast lane 零误伤（普通问句照常走四相位） ----------


async def test_station_fast_lane_silent_on_plain_question(tmp_path: Path) -> None:
    dump = _sys_dump()
    script = {
        "v2.runtime.understand": ["理解：问日产油量。\n指标候选：日产油量"],
        "v2.runtime.decision": ['{"thought": "定稿", "action": "finalize"}'],
        "v2.runtime.answer": ["按材料如实作答。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(dump),
        faq_lookup=lambda q: None,
    )
    try:
        handle = await runtime.ask(
            AskRequest(question="2025-09-01 到 09-03 各井日产油量", actor=ACTOR)
        )
        await drain(handle)
        assert completer.counts().get("v2.runtime.understand") == 1  # fast lane 静默
    finally:
        await db.dispose()


# ---------- 端到端钉测⑥：越集续跑全通道（双审批→批准→续跑出数） ----------


class ApprovalProbeEngine(FakeQueryEngine):
    """剧本引擎——逐次出列＋捕获 run 收到的放行态（approved_tables 断言面）。"""

    def __init__(self, outcomes: Sequence[QueryOutcome]) -> None:
        super().__init__()
        self._queue = list(outcomes)
        self.approved_seen: list[tuple[str, ...]] = []

    def run(self, plan: Any, *, approved_tables: tuple[str, ...] = ()) -> QueryOutcome:
        self.approved_seen.append(tuple(approved_tables))
        self.run_calls += 1
        return self._queue.pop(0)


async def test_station_extable_resume_full_channel(tmp_path: Path) -> None:
    """数-察2 形全通道钉：前置闸审批→批准→引擎侧闸审批→批准→前置重判→
    批量重执行（放行态进引擎）→出数收口——骨架收口段退役。"""
    ask_outcome = QueryOutcome.external_table_approval(
        tables=("erp_well_register",),
        ask={
            "approval_id": "APP-0831-erp_well_register",
            "reason": (
                "查询引用选表命中集之外的外表：erp_well_register"
                "（执行前表引用比对命中——F14）"
            ),
            "impact": "批准＝链恢复续跑（只读执行，生产库未动）",
            "audit_hint": "外表 erp_well_register",
        },
    )
    engine = ApprovalProbeEngine([ask_outcome, _rows_outcome()])
    dump = _sys_dump()
    clarify = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "井位台账关联的日产油量",
             "ledger_notes": "日产油量｜bound｜外表关联", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch = json.dumps({"matches": [
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03",
            "external_tables": ["erp_well_register"]}},
    ]}, ensure_ascii=False)
    script = {
        "v2.runtime.understand": ["理解：问井位台账关联的日产油量。\n指标候选：日产油量"],
        "v2.runtime.decision": [clarify, toolmatch],
        "v2.runtime.answer": ["各井日产油量 N-01 为 21.16 吨 [1]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(dump),
    )
    store = RunStore(db)
    try:
        events = await _ask(runtime, "外表越集续跑题")
        asks = [e.data for e in events if e.event == "ask"]
        assert len(asks) == 1  # 首段：前置闸审批帧
        precond_approval = asks[-1]["frame"]["detail"]["approval_id"]
        run_id = asks[-1]["run_id"]
        # ——第一次批准 → 前置重判放行 → 批量触发引擎侧闸（第二道审批帧）。——
        handle = await runtime.resume(
            run_id, AskChoice(value="批准", approval_id=precond_approval)
        )
        events2 = await drain(handle)
        asks2 = [e.data for e in events2 if e.event == "ask"]
        assert len(asks2) == 1  # 引擎侧审批帧在场
        engine_frame = asks2[-1]["frame"]
        assert engine_frame["kind"] == "external_table_approval"
        # 审批卡 detail 携表名集（放行名单回填的机读面——handlers additive 键）。
        assert engine_frame["detail"]["tables"] == ["erp_well_register"]
        engine_approval = engine_frame["detail"]["approval_id"]
        run_row = await store.get_run(run_id)
        assert run_row is not None and run_row.status == "waiting_ask"
        # ——第二次批准 → 续跑全通道：前置重判→批量重执行（放行态）→出数收口。——
        handle = await runtime.resume(
            run_id, AskChoice(value="批准", approval_id=engine_approval)
        )
        events3 = await drain(handle)
        final = events3[-1].data
        assert final["status"] == "completed"
        run_row = await store.get_run(run_id)
        assert run_row is not None and "21.16" in (run_row.answer or "")
        assert engine.run_calls == 2  # 首执行挂起＋批准后续跑恰一次
        # 放行态真进引擎（第二次 run 携外表名——续跑通道的机读断言面）。
        assert any("erp_well_register" in seen for seen in engine.approved_seen[1:])
        assert "如实收口不冒充" not in (run_row.answer or "")  # 骨架收口段退役
    finally:
        await db.dispose()


async def _ask(runtime: Any, question: str) -> list[Any]:
    handle = await runtime.ask(AskRequest(question=question, actor=ACTOR))
    return await drain(handle)
