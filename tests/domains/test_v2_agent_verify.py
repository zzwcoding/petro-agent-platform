"""V2-06 runtime 核验步验收——specs/agent-loop.md「验收测试」表 verify 侧两条 1:1 同名落测。

- unsupported_claim_rewritten：核验步逐条检查阐述草稿的断言有 Observation 支撑；
  无支撑断言改写为「未找到（材料未披露）」＋notice——禁止无据断言进答案（INV-1）；
- contradiction_split_source：多来源矛盾时答案必须分源列明（各标出处）或显式声明
  歧义；禁止无出处调和（INV-4）。

骨架版核验规则（确定性，细化批可换更强实现——语义不破）：
- 草稿逐行核验：行内引标 [n]（n＝观察全局序号）存在且在界＝有据保留；无引标或
  越界引标行＝无据断言，整行改写「未找到（材料未披露）：〈原文〉」＋notice；
- 矛盾判定：被引观察中，同一 subject（台账卡取内容首段「名称」；agg_row 行级
  事实按 井@日 键独立，不入跨源矛盾池）出现 ≥2 支且值不同→强制分源列明块
  （逐支带 [n] 出处）＋notice——禁止无出处调和。
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from appv2.knowledge import Evidence
from appv2.query import (
    LINEAGE_KEY_CALIBER,
    LINEAGE_KEY_WATERMARK,
    LineageLine,
    QueryOutcome,
)
from appv2.runtime import (
    AskRequest,
    RunEvent,
    RunStore,
)
from appv2.tools import FakeKnowledgeStore
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    QueueQueryEngine,
    drain,
    make_runtime,
)


def _rows_outcome() -> QueryOutcome:
    return QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
        lineage=(
            LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量（单位：吨）——口径声明"),
            LineageLine(key=LINEAGE_KEY_WATERMARK, value="汇总层水位 2026-08-31"),
        ),
    )

# 台账证据（同一要素名两套口径——吨 vs 方，跨源矛盾的被控源）。
_EVIDENCE_TON = Evidence(
    element_id="201",
    kind="metric",
    value="日产油量：21 吨/日（口径卡）",
    source="sem_metric#201",
    version="1",
    freshness="",
    scope="日",
    binding_state="bound",
)
_EVIDENCE_CUBIC = Evidence(
    element_id="301",
    kind="metric",
    value="日产油量：8824.4 方/日（口径卡）",
    source="sem_metric#301",
    version="2",
    freshness="",
    scope="日",
    binding_state="bound",
)


def _semantic_script(draft: str) -> dict[str, Sequence[str]]:
    return {
        "v2.runtime.understand": ["理解：问日产油量口径。\n指标候选：无"],
        "v2.runtime.plan": ['{"tool": "semantic_query", "args": {"element_name": "日产油量"}}'],
        "v2.runtime.answer_draft": [draft],
    }


def _notices(events: list[RunEvent]) -> list[dict[str, Any]]:
    return [e.data for e in events if e.event == "notice"]


# ---------- 验收④：无据断言改写「未找到」＋notice（INV-1） ----------


async def test_unsupported_claim_rewritten(tmp_path: Path) -> None:
    rows = _rows_outcome()
    draft = (
        "N-01 井 2025-09-01 日产油量 21.16 吨[1]。\n"
        "全油田 86 口井昨日均超产 50 吨。"
    )
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问日产油量。\n指标候选：日产油量"],
        "v2.runtime.plan": [
            '{"metric_slot": "日产油量", "ranking": false, '
            '"window_start": "2025-09-01", "window_end": "2025-09-03", "limit": 5}'
        ],
        "v2.runtime.answer_draft": [draft],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([rows]), script=script
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        # 有据行保留（引标 [1] 在界—— Observation 支撑）。
        assert "21.16 吨[1]" in answer
        # 无据行改写为「未找到（材料未披露）」——禁止无据断言进答案（INV-1）。
        assert "86 口井" in answer
        assert "未找到（材料未披露）" in answer
        # notice 出场（verify 步拦截的机读信号）。
        notices = _notices(events)
        assert any(n.get("type") == "unsupported_claim" for n in notices)
        # verdict 事件载核验结论（改写计数在场）。
        verdicts = [e.data for e in events if e.event == "verdict"]
        assert verdicts and verdicts[0]["rewritten"] == 1
    finally:
        await db.dispose()


# ---------- 验收⑤：矛盾两来源→答案分源列明各带 citation（INV-4） ----------


async def test_contradiction_split_source(tmp_path: Path) -> None:
    knowledge = FakeKnowledgeStore(evidence_hits=[_EVIDENCE_TON, _EVIDENCE_CUBIC])
    draft = "日产油量口径为 21 吨/日[1]；另一口径卡记 8824.4 方/日[2]。"
    runtime, _completer, db = await make_runtime(
        tmp_path,
        engine=FakeQueryEngineStub(),
        script=_semantic_script(draft),
        knowledge=knowledge,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question="日产油量的口径是什么", actor=ACTOR))
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        # 分源列明块出场（INV-4：各标出处，禁止无出处调和）。
        assert "分源列明" in answer
        assert "sem_metric#201" in answer and "sem_metric#301" in answer
        assert "[1]" in answer and "[2]" in answer
        # 矛盾 notice 出场（机读信号）。
        notices = _notices(events)
        assert any(n.get("type") == "contradiction_split" for n in notices)
        # verdict 事件载 split 结论。
        verdicts = [e.data for e in events if e.event == "verdict"]
        assert verdicts and verdicts[0]["split"] is True
    finally:
        await db.dispose()


class FakeQueryEngineStub:
    """semantic 路径占位引擎（data_query 不被触——plan 选了 semantic_query）。"""

    def validate(self, plan: Any, *, candidates: Any = None) -> Any:
        raise AssertionError("semantic 路径不得触 data_query")

    def run(self, plan: Any) -> Any:
        raise AssertionError("semantic 路径不得触 data_query")
