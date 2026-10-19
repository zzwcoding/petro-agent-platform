"""V2-73 会话历史读口钉测——GET /api/v2/chat/runs?limit=N（最近任务面）。

被测件（V2-73 新增，只读零写面；V2-141 改行集来源；V2-142 列表项瘦身＋详情补偿读口）：

- **列表行集与行投影的装配形状（RT-W5-02）**：V2-73 原形＝run 号集取本进程 SSE 帧桥注册表
  （`RunStreamRegistry.run_ids`）＋逐个 `RunStore.run`；**V2-141 改为端口侧 limit 下推**——
  行集与排序都在 persistence 端口完成（`RunStore.scan_recent(wanted)` →
  `Tables.scan_recent(limit)` 按 `created_at` 降序只读 limit 条），api 层只做行投影
  （不再全量 `registry.run_ids()`、不再 Python 排序、不自造 SQL）；
- GET /api/v2/chat/runs → [{run_id,question,status,followup_of,created_at,updated_at}＋supplements]
  （RunListItem 合同形——**V2-142 列表项瘦身：全文 answer 不再随行**，时间为 ISO 字符串；
  正文由 `GET /runs/{id}` 补偿读口 `RunView.answer` 供给——`test_get_run_returns_answer` 钉）；
- limit 夹取 1..100 静默（越界不 400——只读面宽容）。

接口级测试（modules.md api 卡 Seam 行——FastAPI TestClient，不起真实端口）；
runtime 装配照抄 tests/api/test_v2_asks.py（内存簿记表＋台账投影端口＋剧本 completer＋
假引擎——runtimev2 真链）；时间用 infra.clock.set_clock 冻结缝（B14——两问定序，
免依赖真实时钟微秒差）。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import asdict
from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from appv2.api.bridge import RunStreamRegistry
from appv2.api.wire import FRAME_SESSION
from appv2.infra import clock
from appv2.infra.db import ConnectionManager
from appv2.runtimev2.persistence import (
    TABLE_RUN,
    MemoryTables,
    RowOp,
    RunRecord,
    current_tables,
)
from tests.api.test_v2_asks import (
    ACTOR,
    HAPPY_QUESTION,
    _make_client,
    _parse_frames,
    _post_ask,
    _rows_outcome,
    _v2,
)


@pytest.fixture
async def env(tmp_path: Any) -> AsyncIterator[tuple[TestClient, ConnectionManager]]:
    """接口级装配（sqlite 底座＋runtimev2 真链＋真 api 层——两轮剧本可连续驱动两问）。"""
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


# ---------- 空库：零 run → [] ----------


def test_empty_store_returns_empty_list(env: Any) -> None:
    """空库 GET /api/v2/chat/runs → 200 且恰好 []（只读面零 run 合法空态）。"""
    client, _db = env
    resp = client.get("/api/v2/chat/runs", headers=ACTOR)
    assert resp.status_code == 200
    assert resp.json() == []


# ---------- 一问收口：列表含该 run（合同形逐字段） ----------


def test_list_contains_completed_run(env: Any) -> None:
    """跑一问到完成 → 列表恰含该 run：**六键＋supplements**（V2-142 去 answer 后 wire 形）、
    question 逐字、status=completed、followup_of=空串、created_at/updated_at 为 ISO 字符串
    （fromisoformat 可解析）。

    正文（answer）已不在列表行（V2-142 列表项瘦身）——正文零程序块与全文在场改由详情补偿口
    `GET /runs/{id}` 核（同批见 `test_get_run_returns_answer`）。
    """
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
        "run_id", "question", "status", "followup_of", "created_at", "updated_at",
        "supplements",
    }  # V2-142：六键核心（answer 已去）＋本批保留的 supplements 增补面列（EB3 D1）
    assert "answer" not in item  # 全文不随列表行（V2-142）
    assert item["run_id"] == run_id
    assert item["question"] == HAPPY_QUESTION  # question 逐字
    assert item["status"] == "completed"
    # 增补面随行（EB3 D1＋EB5c①）：血缘在场⇒lineage 块保底，引用清单走 citations
    blocks = [entry["block"] for entry in item["supplements"]]
    assert blocks == ["lineage", "citations"]
    assert "引用：" in item["supplements"][1]["text"]
    # 正文零程序块（引用块不进正文）——改由详情补偿口核（V2-142）
    detail = client.get(f"/api/v2/chat/runs/{run_id}", headers=ACTOR).json()
    assert detail["answer"] and "引用：" not in detail["answer"]
    assert item["followup_of"] == ""  # 独立新问＝链根（空串）
    for stamp in (item["created_at"], item["updated_at"]):
        assert isinstance(stamp, str)
        datetime.fromisoformat(stamp)  # ISO 形可解析
        assert len(stamp) >= 19 and stamp[10] == "T"  # YYYY-MM-DDTHH:MM:SS 前缀形


# ---------- V2-142 列表项瘦身与补偿读口 ----------


def test_list_item_has_no_answer(env: Any) -> None:
    """V2-142 列表项瘦身：wire 键集**逐字**＝
    `{run_id, question, status, followup_of, created_at, updated_at}`（六键核心）
    ＋本批**保留**的 `supplements`（打磨批⑨引用面回读承载，另案评估）。

    `answer` 键不在行内（全文不再随行）；列表项零正文——正文由详情补偿口供给。
    """
    client, _db = env
    frames = _post_ask(client)
    run_id = frames[0][1]["run_id"]

    items = client.get("/api/v2/chat/runs", headers=ACTOR).json()
    assert len(items) == 1
    item = items[0]
    # 六键逐字（V2-142 任务 1——supplements 另列保留，故先剥出再逐字比对）
    assert set(item) - {"supplements"} == {
        "run_id", "question", "status", "followup_of", "created_at", "updated_at",
    }
    assert "supplements" in item  # 本批保留（引用面回读承载）
    assert "answer" not in item  # 全文不随行（瘦身本体）
    assert item["run_id"] == run_id


def test_get_run_returns_answer(env: Any) -> None:
    """V2-142 补偿读口（**反向判据：历史链正文不空**）：列表项去 `answer` 后，正文由
    `GET /runs/{id}` 的 `answer` 面供给——取值源＝`store.run(run_id).answer`（既有行投影，
    零新 SQL）。详情 `answer` 与运行期交付正文同源、非空；此面缺位＝历史链正文整段空（回归）。
    """
    client, _db = env
    frames = _post_ask(client)
    run_id = frames[0][1]["run_id"]

    detail = client.get(f"/api/v2/chat/runs/{run_id}", headers=ACTOR)
    assert detail.status_code == 200
    body = detail.json()
    assert "answer" in body  # 补偿口在场
    assert body["answer"] and body["answer"].strip()  # 非空——历史链正文由此供给
    # 同批对照：列表行确无正文（瘦身与补偿口同批在场）
    assert "answer" not in client.get("/api/v2/chat/runs", headers=ACTOR).json()[0]


def test_list_response_under_32kb_at_limit_100(env: Any) -> None:
    """V2-142 体积判据：`limit=100` 响应体 ≤32KB（现状 247KB／253,198 B）。

    合成量级取真实样本 top-100 的 answer 均值（≈2.2KB/行——真源
    `logs/old-runs-backup-20261014.json`，该件 gitignore 不入库，故按同量级合成）；
    前后对照在用例内算：含 answer 的旧形 >32KB（本判据有区分力）／新形 ≤32KB。
    """
    client, _db = env
    tables = current_tables()
    answer = "答案：" + "日产油量 21.16 吨 [1]；" * 80  # ≈2.3KB/行（样本 top-100 均值量级）
    for index in range(100):
        run_id = f"run-slim-{index:03d}"
        row = asdict(
            RunRecord(
                run_id=run_id,
                question=f"第 {index} 问：2025 年 9 月上旬各井日产油量",
                actor="aqiang",
                status="completed",
                answer=answer,
                error=None,
                manifest_digest="2e1263d5802ec26d",
                followup_of="",
                created_at=datetime(2026, 10, 12, 8, index % 60, 0),
                updated_at=datetime(2026, 10, 12, 8, index % 60, 0),
            )
        )
        tables.write([RowOp(TABLE_RUN, (run_id,), row, "put")])

    resp = client.get("/api/v2/chat/runs", params={"limit": 100}, headers=ACTOR)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 100
    after = len(resp.content)
    # 前后对照：旧形（列表项含 answer）体积
    before = len(
        json.dumps(
            [{**item, "answer": answer} for item in items],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
    )
    assert before > 32 * 1024  # 旧形（含全文）确实越线——判据有区分力
    assert after <= 32 * 1024  # 新形（去 answer）≤32KB
    assert after < before  # 瘦身方向为正
    assert all("answer" not in item for item in items)


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


# ---------- V2-141 limit 下推：读口只读 limit 条（端口侧 scan_recent） ----------


def test_list_applies_limit_at_read_port(env: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """直插 limit+5 行 → 响应恰 limit 条且为 created_at 降序前 limit。

    行集**不经注册表登记**（直插簿记表 run 行）——行集来源已换到持久读口
    （`RunStore.scan_recent`），故响应必须来自端口侧 LIMIT 读；
    下推反证＝全量扫描口（`MemoryTables.scan`）与旧行集来源
    （`RunStreamRegistry.run_ids`）双双 monkeypatch 抛错仍绿；
    越界仍静默夹取 1..100（limit=0 → 夹到 1；limit=500 → 夹到 100，行不足则全量）。
    """
    client, _db = env
    tables = current_tables()
    for index in range(8):  # limit(3) + 5 行
        run_id = f"run-seed-{index:02d}"
        row = asdict(
            RunRecord(
                run_id=run_id,
                question=f"第 {index} 问：9 月上旬日产油量",
                actor="aqiang",
                status="completed",
                answer=None,
                error=None,
                manifest_digest=None,
                followup_of="",
                created_at=datetime(2026, 10, 12, 8, index, 0),
                updated_at=datetime(2026, 10, 12, 8, index, 0),
            )
        )
        tables.write([RowOp(TABLE_RUN, (run_id,), row, "put")])

    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("全量扫描被调用——limit 未在端口侧下推")

    monkeypatch.setattr(MemoryTables, "scan", _boom)  # 全量扫描口（下推反证）
    monkeypatch.setattr(RunStreamRegistry, "run_ids", _boom)  # 旧行集来源（V2-141 已弃）

    resp = client.get("/api/v2/chat/runs", params={"limit": 3}, headers=ACTOR)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3  # 恰 limit 条
    assert [item["run_id"] for item in items] == [
        "run-seed-07", "run-seed-06", "run-seed-05",  # created_at 降序前 limit
    ]
    assert [item["created_at"] for item in items] == [
        "2026-10-12T08:07:00", "2026-10-12T08:06:00", "2026-10-12T08:05:00",
    ]

    floor = client.get("/api/v2/chat/runs", params={"limit": 0}, headers=ACTOR)
    assert floor.status_code == 200  # 越界静默夹取——不 400
    assert [item["run_id"] for item in floor.json()] == ["run-seed-07"]  # 夹到 1

    ceiling = client.get("/api/v2/chat/runs", params={"limit": 500}, headers=ACTOR)
    assert ceiling.status_code == 200  # 越界静默夹取——不 400
    assert [item["run_id"] for item in ceiling.json()] == [
        f"run-seed-{index:02d}" for index in range(7, -1, -1)
    ]  # 夹到 100：8 行全在且降序


# ---------- 追问链：followup_of 落 run 行并随列表读口带出（V2-74 对话任务面） ----------


def test_followup_run_carries_followup_of(env: Any) -> None:
    """追问 run（question＋followup_run_id）→ 列表项 followup_of＝前轮 run_id；
    前轮（链根）followup_of＝空串——前端按此把两 run 归入同一对话任务。"""
    client, _db = env
    root_frames = _post_ask(client, "链根问：9 月上旬日产油量")
    root_id = root_frames[0][1]["run_id"]

    resp = client.post(
        "/api/v2/chat/asks",
        json={"question": "追问：那中旬呢？", "followup_run_id": root_id},
        headers=ACTOR,
    )
    assert resp.status_code == 200
    follow_frames = _parse_frames(resp.text)
    follow_id = follow_frames[0][1]["run_id"]

    items = client.get("/api/v2/chat/runs", headers=ACTOR).json()
    by_id = {i["run_id"]: i for i in items}
    assert by_id[follow_id]["followup_of"] == root_id  # 追问轮指向链根
    assert by_id[root_id]["followup_of"] == ""  # 链根＝空串
