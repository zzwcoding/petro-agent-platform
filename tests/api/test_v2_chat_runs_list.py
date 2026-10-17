"""BE-01 历史读口空列语义钉测——GET /api/v2/chat/runs 的 supplements 三态投影（对账 D-4）。

票面逐字稿（D-4 裁决）：「空列如实出 `[]`、`null` 仅旧行」。三态：

- 列默认 []：经 store 建 run（不写 supplements——`RunRecord` 缺省空列）→ 投影 `[]` 非 null；
- 旧行 null 保留：布景直插 supplements=null 行（照 persistence 测试既有布景惯例——
  `tables.write` RowOp 直插，不经 store 投影）→ 投影 `is None`；
- 有块行块数组原样：布景写 `[{block, text}]` → 投影逐字相等。

接口级测试（modules.md api 卡 Seam 行——FastAPI TestClient，不起真实端口）；布景照抄
tests/api/test_v2_runs_list.py（内存簿记表＋runtimev2 真链＋剧本 completer）。run 号进列表
读口的登记缝＝SSE 帧桥注册表（`RunStreamRegistry.run_ids`——list_runs 行集来源），本件经
一次真实问句挂线取得登记号，再按各例布景整形该行（store.save 缺省形／tables 直插 null 行）。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import asdict, replace
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from appv2.infra.db import ConnectionManager
from appv2.runtimev2.persistence import (
    TABLE_RUN,
    RowOp,
    RunRecord,
    current_tables,
)
from tests.api.test_v2_asks import (
    ACTOR,
    _make_client,
    _post_ask,
    _rows_outcome,
    _v2,
)


def _record(run_id: str) -> RunRecord:
    """布景基行（不写 supplements——新建行缺省形＝空列）。"""
    return RunRecord(
        run_id=run_id,
        question="2025-09-01 到 09-03 各井日产油量",
        actor="aqiang",
        status="completed",
        answer="答案：N-01 井 2025-09-01 日产油量 21.16 吨。",
        error=None,
        manifest_digest=None,
        followup_of="",
        created_at=datetime(2026, 10, 12, 8, 0, 0),
        updated_at=datetime(2026, 10, 12, 8, 0, 0),
    )


def _registered_run_id(client: TestClient, question: str) -> str:
    """一问挂线取得登记号（session 首帧——帧桥注册表登记缝，list_runs 行集来源）。"""
    frames = _post_ask(client, question)
    return frames[0][1]["run_id"]


def _item_of(items: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    return next(item for item in items if item["run_id"] == run_id)


@pytest.fixture
async def env(tmp_path: Any) -> AsyncIterator[tuple[TestClient, ConnectionManager]]:
    """接口级装配（照抄 test_v2_runs_list 布景——本票例不消费剧本内容，双轮剧本够用）。"""
    v2 = _v2()
    note = v2.v2_ledger_note(v2.v2_ledger_dump(), "日产油量")
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
        ] * 2,
        "answer": ["答案：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    async for pair in _make_client(
        tmp_path,
        engine=v2.V2QueueEngine([_rows_outcome(), _rows_outcome()]),
        script=script,
    ):
        yield pair


# ---------- 票面对象 1：列默认 []——新建 run 行（不写 supplements）读回 [] 非 null ----------


def test_supplements_empty_list_not_null(env: Any) -> None:
    """经 store 建 run（不写 supplements）→ 投影 `[]`（空列如实——不再 `or None` 折 null）。"""
    client, _db = env
    run_id = _registered_run_id(client, "列默认：9 月上旬日产油量")
    client.app.state.run_store.save(_record(run_id))  # 不写 supplements——缺省空列（新行形）

    resp = client.get("/api/v2/chat/runs", headers=ACTOR)
    assert resp.status_code == 200
    item = _item_of(resp.json(), run_id)
    assert item["supplements"] == []  # 空列如实出 []——非 null


# ---------- 票面对象 2：旧行 null 保留——迁移前已存在的 null 行投影仍为 null ----------


def test_legacy_row_stays_null(env: Any) -> None:
    """布景直插 supplements=null 行（旧行形）→ 投影 `is None`（null 仅旧行——机读判据）。"""
    client, _db = env
    run_id = _registered_run_id(client, "旧行形：9 月上旬日产油量")
    row = asdict(_record(run_id))
    row["supplements"] = None  # 迁移前已存在的旧行形——列 null
    current_tables().write([RowOp(TABLE_RUN, (run_id,), row, "put")])

    resp = client.get("/api/v2/chat/runs", headers=ACTOR)
    assert resp.status_code == 200
    item = _item_of(resp.json(), run_id)
    assert item["supplements"] is None  # 旧行 null 保留——不折 []


# ---------- 票面对象 3：有块行块数组原样——EB3 型行投影逐字 ----------


def test_blocks_pass_through(env: Any) -> None:
    """布景写 `[{block, text}]` → 投影块数组逐字相等（有块→块数组）。"""
    client, _db = env
    run_id = _registered_run_id(client, "血缘块：9 月上旬日产油量")
    blocks = [{"block": "lineage", "text": "血缘：表 wells_daily · 台账A · 窗 2025-09-01~09-03"}]
    client.app.state.run_store.save(replace(_record(run_id), supplements=blocks))

    resp = client.get("/api/v2/chat/runs", headers=ACTOR)
    assert resp.status_code == 200
    item = _item_of(resp.json(), run_id)
    assert item["supplements"] == blocks  # 逐字（条目序与文本原样）
