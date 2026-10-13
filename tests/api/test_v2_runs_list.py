"""V2-73 会话历史读口钉测——GET /api/v2/chat/runs?limit=N（最近任务面）。

被测件（V2-73 新增，只读零写面）：
- RunStore.list_runs(limit=20)：agent_v2_run 按 created_at 降序截 N；
- GET /api/v2/chat/runs → [{run_id,question,status,answer,created_at,updated_at}]
  （RunListItem 合同形——answer 全文随行，时间为 ISO 字符串）；
- limit 夹取 1..100 静默（越界不 400——只读面宽容）。

接口级测试（modules.md api 卡 Seam 行——FastAPI TestClient，不起真实端口）；
runtime 装配与 run 驱动照抄 tests/api/test_v2_asks.py（sqlite 底座＋
ScriptedCompleter 剧本＋QueueQueryEngine 出数——剧本末位驻留，一问一答
可重复驱动多轮）；时间用 infra.clock.set_clock 冻结缝（B14——两问定序，
免依赖真实时钟微秒差）。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from appv2.api import create_app
from appv2.api.wire import FRAME_SESSION
from appv2.infra import clock
from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.query import (
    LINEAGE_KEY_CALIBER,
    LINEAGE_KEY_WATERMARK,
    LineageLine,
    QueryOutcome,
)
from appv2.runtime import ScriptedCompleter, ensure_agent_v2_tables
from appv2.tools import FakeKnowledgeStore, FakeQueryEngine, FakeRetrievalEngine, ToolRegistry

ACTOR = {"X-Dev-User": "aqiang"}  # 身份桩（同 test_v2_asks——五角色键）

# 最短完成剧本（test_v2_asks 同款——问数出数一轮收口；末位驻留可重复驱动）。
UNDERSTAND_DATA = "理解：问 2025 年 9 月上旬的日产油量。\n指标候选：日产油量"
CLARIFY_WINDOWED = (
    '{"thought": "台账命中＋窗已定——分解", "action": "decompose", '
    '"question_group": {"subtasks": [{"id": "s1", '
    '"question": "2025-09-01 到 09-03 各井日产油量", '
    '"ledger_notes": "日产油量｜bound｜窗 2025-09-01~09-03", "chain": "data", '
    '"tool": "data_query"}]}}'
)
TOOLMATCH_WINDOWED = (
    '{"matches": [{"id": "s1", "chain": "data", "tool": "data_query", "plan": '
    '{"metric_slot": "日产油量", "ranking": false, "window_start": "2025-09-01", '
    '"window_end": "2025-09-03", "limit": 5}}]}'
)
ANSWER_DRAFT_CITED = "N-01 井 2025-09-01 日产油量 21.16 吨[1]。"
HAPPY_QUESTION = "2025 年 9 月 1 日到 3 日的日产油量"

HAPPY_SCRIPT = {
    "v2.runtime.understand": [UNDERSTAND_DATA],
    "v2.runtime.decision": [CLARIFY_WINDOWED, TOOLMATCH_WINDOWED],
    "v2.runtime.answer": [ANSWER_DRAFT_CITED],
}


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
    """剧本化按次出列引擎（末位驻留——多轮驱动同款，test_v2_asks 装配照抄）。"""

    def __init__(self, outcomes: list[QueryOutcome]) -> None:
        super().__init__()
        self._queue = list(outcomes)

    def run(
        self, plan: Any, *, approved_tables: tuple[str, ...] = ()
    ) -> QueryOutcome:
        self.run_calls += 1
        if len(self._queue) > 1:
            return self._queue.pop(0)
        return self._queue[0]


@pytest.fixture
async def env(tmp_path: Any) -> AsyncIterator[tuple[TestClient, ConnectionManager]]:
    """接口级装配（sqlite 底座＋剧本 runtime＋真 api 层——test_v2_asks 同款）。"""
    registry = ToolRegistry(
        knowledge=FakeKnowledgeStore(),
        query=QueueQueryEngine([_rows_outcome()]),
        retrieval=FakeRetrievalEngine(),
    )
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "v2-runs-list.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    db = ConnectionManager([spec])
    await ensure_agent_v2_tables(db.engine())
    completer = ScriptedCompleter(HAPPY_SCRIPT)
    app: FastAPI = create_app(db=db, registry=registry, completer=completer)
    with TestClient(app) as test_client:
        yield test_client, db
    await db.dispose()


def _parse_frames(text: str) -> list[tuple[str, dict[str, Any]]]:
    """SSE 正文 → (event, data) 帧序列（test_v2_asks 同款解析）。"""
    frames: list[tuple[str, dict[str, Any]]] = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        event = data = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        assert event is not None and data is not None
        frames.append((event, data))
    return frames


def _post_ask(
    client: TestClient, question: str = HAPPY_QUESTION
) -> list[tuple[str, dict[str, Any]]]:
    resp = client.post("/api/v2/chat/asks", json={"question": question}, headers=ACTOR)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    return _parse_frames(resp.text)


# ---------- 空库：零 run → [] ----------


def test_empty_store_returns_empty_list(env: Any) -> None:
    """空库 GET /api/v2/chat/runs → 200 且恰好 []（只读面零 run 合法空态）。"""
    client, _db = env
    resp = client.get("/api/v2/chat/runs", headers=ACTOR)
    assert resp.status_code == 200
    assert resp.json() == []


# ---------- 一问收口：列表含该 run（合同形逐字段） ----------


def test_list_contains_completed_run(env: Any) -> None:
    """跑一问到完成 → 列表恰含该 run：六键合同形、question 逐字、status=completed、
    answer 非空、created_at/updated_at 为 ISO 字符串（fromisoformat 可解析）。"""
    client, _db = env
    frames = _post_ask(client)
    run_id = frames[0][1]["run_id"]
    assert frames[0][0] == FRAME_SESSION and run_id.startswith("run-")

    resp = client.get("/api/v2/chat/runs", headers=ACTOR)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]
    assert set(item) == {
        "run_id", "question", "status", "answer", "created_at", "updated_at",
    }  # RunListItem 合同形（接口定义节）
    assert item["run_id"] == run_id
    assert item["question"] == HAPPY_QUESTION  # question 逐字
    assert item["status"] == "completed"
    assert item["answer"] and item["answer"].strip()  # answer 非空（全文随行）
    for stamp in (item["created_at"], item["updated_at"]):
        assert isinstance(stamp, str)
        datetime.fromisoformat(stamp)  # ISO 形可解析
        assert len(stamp) >= 19 and stamp[10] == "T"  # YYYY-MM-DDTHH:MM:SS 前缀形


# ---------- limit 行为：截 N 取最新；越界静默夹取不 400 ----------


def test_limit_one_returns_newest_and_large_limit_clamps(env: Any) -> None:
    """两问两 run（时钟冻结定序：08:00 → 09:00）——limit=1 恰 1 条且为最新；
    limit=500 静默夹取（200 不 400）且两条全在；缺省降序（最新在前）。"""
    client, _db = env
    previous = clock.set_clock(lambda: datetime(2026, 10, 12, 8, 0, 0))
    try:
        _post_ask(client, "第一问：9 月上旬日产油量")
        clock.set_clock(lambda: datetime(2026, 10, 12, 9, 0, 0))
        _post_ask(client, "第二问：9 月中旬日产油量")
    finally:
        clock.set_clock(previous)

    everything = client.get("/api/v2/chat/runs", headers=ACTOR)
    assert everything.status_code == 200
    assert [i["question"] for i in everything.json()] == [
        "第二问：9 月中旬日产油量",  # created_at 降序——最新在前
        "第一问：9 月上旬日产油量",
    ]
    assert [i["created_at"] for i in everything.json()] == [
        "2026-10-12T09:00:00", "2026-10-12T08:00:00",
    ]

    one = client.get("/api/v2/chat/runs", params={"limit": 1}, headers=ACTOR)
    assert one.status_code == 200
    body = one.json()
    assert len(body) == 1  # 恰 1 条
    assert body[0]["question"] == "第二问：9 月中旬日产油量"  # 且为最新

    large = client.get("/api/v2/chat/runs", params={"limit": 500}, headers=ACTOR)
    assert large.status_code == 200  # 越界静默夹取——不 400
    assert len(large.json()) == 2  # 夹到上限内全量仍在
