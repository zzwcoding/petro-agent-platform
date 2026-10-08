"""R14 红线②终实证冒烟（RUNTIME_SMOKE=1 门控）——生产装配真网关一轮 ask。

跑法（P-008 票面 R14 条目）：
    RUNTIME_SMOKE=1 uv run pytest tests/api/test_v2_runtime_smoke_real.py -q

真装配含义：create_app 真起（真实 primary PG@5433 演示库——config/database.yaml）
＋真 gateway.complete（B6 唯一出口——GatewayService＋LlmClient，petro-main＝
MiniMax-M3 真调用真计费）＋真问数链（V2 验收底座：InMemory 台账快照＋
CsvSnapshotExecutor——tests/domains/test_v2_agent_loop.py readonly_inv2 同款）。
检索面＝fixture 适配器（真向量服务依赖未在本票范围——如实声明，冒烟问句为
问数题不触检索）。

流程（一轮 ask 走通六步 loop）：
① POST /api/v2/chat/asks（真实 MiniMax 出理解/计划/草稿）→ SSE 流保留帧 done
   收场，终局 verdict subtype=final；
② GET run 状态＝completed（run 状态机收口）；
③ R14 核心断言：caller 归因落 spend 记录——`v2.runtime.*` caller 桶本轮在场
   且 cost>0（GatewayChatModel→gateway.complete 的 B6 归因链真账本实证）。

重跑幂等：每轮新增真流水（演示库量级，GATEWAY_SMOKE/CHAT_SMOKE 同款处置）；
断言只看「本轮桶在场」不看全库计数。
"""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Any

import pytest

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("RUNTIME_SMOKE") != "1",
        reason="R14 真装配冒烟需 RUNTIME_SMOKE=1（真实 PG/LLM 计费——不进常规门禁）",
    )
]

QUESTION = "2025 年 9 月 1 日到 3 日的日产油量"
TODAY = date(2026, 10, 8)
ACTOR = {"X-Dev-User": "aqiang"}


def _parse_frames(text: str) -> list[tuple[str, dict[str, Any]]]:
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


def test_runtime_production_smoke_real_gateway() -> None:
    from fastapi.testclient import TestClient

    from appv2.api import create_app
    from appv2.infra.clock import now
    from appv2.infra.config import load_database_specs
    from appv2.infra.db import ConnectionManager
    from appv2.infra.gateway import GatewayService, SpendFilter
    from appv2.infra.gateway.store import SpendStore
    from appv2.infra.llm_client import LlmClient
    from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot
    from appv2.query import CsvSnapshotExecutor, QueryEngine
    from appv2.tools import FakeRetrievalEngine, ToolRegistry

    db = ConnectionManager(load_database_specs())  # 真实 primary PG（演示库）
    knowledge = InMemoryKnowledgeStore(question_array_snapshot(), today=TODAY)
    registry = ToolRegistry(
        knowledge=knowledge,
        query=QueryEngine(
            knowledge=knowledge,
            executor=CsvSnapshotExecutor(),
            waterline=None,
            today=lambda: TODAY,
        ),
        retrieval=FakeRetrievalEngine(),
    )
    gateway = GatewayService(db, LlmClient())  # B6 唯一出口真件（MiniMax 真引擎）
    app = create_app(db=db, registry=registry, completer=gateway)
    started_at = now()

    with TestClient(app) as client:
        # —— ① 一轮 ask：真实 MiniMax 走六步 loop，SSE 保留帧收场 ——
        resp = client.post("/api/v2/chat/asks", json={"question": QUESTION}, headers=ACTOR)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        frames = _parse_frames(resp.text)
        run_id = frames[0][1]["run_id"]
        assert frames[0][0] == "session" and frames[0][1]["resume"] is False
        assert frames[-1][0] == "done" and frames[-1][1]["run_id"] == run_id
        step_kinds = [d["step"] for n, d in frames if n == "step"]
        assert {"understand", "plan"} <= set(step_kinds)  # loop 真跑（理解＋计划在流）
        finals = [d for n, d in frames if n == "verdict" and d.get("subtype") == "final"]
        assert finals and finals[-1]["run_id"] == run_id  # R10 终局判定（wire 定型形）

        # —— ② run 状态机收口 ——
        status = client.get(f"/api/v2/chat/runs/{run_id}", headers=ACTOR).json()
        assert status["status"] == "completed"
        assert status["manifest_digest"] == finals[-1]["manifest_digest"]

        # —— ③ R14 核心：caller 归因落 spend 记录（红线②真账本实证） ——
        store = SpendStore(db)

        async def _spend_page() -> Any:
            return await store.page(SpendFilter(), page_size=200)

        page = client.portal.call(_spend_page)  # portal＝应用事件循环
        mine = [
            row
            for row in page.items
            if str(row.caller or "").startswith("v2.runtime.") and row.time >= started_at
        ]
        assert mine, "本轮 runtime 调用未落 spend 账本——红线②归因链断裂"
        assert {row.caller for row in mine} >= {"v2.runtime.understand"}
        assert all(row.cost_yuan > 0 for row in mine)  # 真调用真计费（非估算零值）
