"""V2-19 组合根——create_app 生产装配＋DE-16 消费点两向行为测试（票面任务 4）。

组合根语义：create_app 的 registry 缺省（None）＝生产组合——三引擎生产读面
（PgKnowledgeStore／PgQueryExecutor／PgFragmentLibrary）真装配＋DE-16 翻板
从 config 进组合根（gate_freshness(waterline, enabled=ChatSettings.
freshness_gate_enabled)——V2-06 接线项②的消费点落位，生产主链新鲜度闸真生效）。

装配：sqlite 测试底座。主库承载 water_line（public 表）＋agent_v2/gateway
lifespan 表＋sem_* 台账（PgKnowledgeStore 指标命中消费）；agg 星型三表经
sqlite ATTACH '<file>' AS agg 出 schema 限定名（Core 渲染 agg.fct_daily_
metering 原样解析——峰测在案）。生产读面逐调用新建会话管理器——ATTACH 钩子
经 Engine 类级 connect 事件随 fixture 生命周期全域挂/摘（非 sqlite 连接的
ATTACH 报错静默跳过——PG 集成件同进程不受扰）。agg 行值只灌水位前窗
（≤2026-08-31），查询窗 2026-09-01..09-15：
- 闸开（freshness_gate_enabled=true，缺省现状）：窗整体晚于水位——
  freshness_block 拦停话术进事件流，零数值（不冒充）；
- 闸关（false）：不读水位不拦停——执行缝放行，窗内 0 行＝「查无数据」
  如实拒答（不冒充出数）。
剧本 completer（ScriptedCompleter 按 caller 分流——零 LLM 依赖）；执行日
钉 2026-10-08（不吃墙上时钟）。
"""

import asyncio
import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, text

from appv2.api import create_app
from appv2.infra.config import ChatSettings
from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.runtime import ScriptedCompleter

TODAY = date(2026, 10, 8)
ACTOR = {"X-Dev-User": "aqiang"}  # 身份桩（五角色键——非键名 401）

_UNDERSTAND = "理解：问 9 月上旬的日产油量。\n指标候选：日产油量"
_PLAN = (
    '{"metric_slot": "日产油量", "ranking": false, '
    '"window_start": "2026-09-01", "window_end": "2026-09-15"}'
)
_ANSWER = "答案：见闸依据。"
_SCRIPT: dict[str, Sequence[str]] = {
    "v2.runtime.understand": [_UNDERSTAND],
    "v2.runtime.plan": [_PLAN],
    "v2.runtime.answer_draft": [_ANSWER],
}

_SEM_METRIC_DDL = (
    "CREATE TABLE sem_metric (id INTEGER PRIMARY KEY, name TEXT NOT NULL,"
    " slot_name TEXT NOT NULL, def TEXT NOT NULL, grain TEXT NOT NULL,"
    " unit TEXT NOT NULL, status TEXT NOT NULL, dispute TEXT,"
    " version INTEGER NOT NULL, calibers TEXT NOT NULL, default_caliber TEXT)"
)
_SEM_EMPTY_DDL = (
    # 其余三账（PgKnowledgeStore 直读全集——本测只消费指标命中，空表即可）。
    "CREATE TABLE sem_term (id INTEGER PRIMARY KEY, term TEXT NOT NULL,"
    " type TEXT NOT NULL, def TEXT NOT NULL, status TEXT NOT NULL,"
    " status_key TEXT NOT NULL, version INTEGER NOT NULL, expires_at DATE)",
    "CREATE TABLE sem_object (id INTEGER PRIMARY KEY, obj TEXT NOT NULL,"
    " attr TEXT, status TEXT NOT NULL, version INTEGER)",
    "CREATE TABLE sem_relation (id INTEGER PRIMARY KEY, rel TEXT NOT NULL,"
    " read TEXT NOT NULL)",
)
_SEM_METRIC_ROW = (
    "INSERT INTO sem_metric VALUES (201, '日产油量（吨）', '日产油量',"
    " '日产计量的日产油量——源 oil_production_daily.oil_output。', '日/井', '吨',"
    " '[\"生效中\"]', NULL, 1, '[{\"key\": \"A\", \"name\": \"班次合计日口径\","
    " \"default\": true}]', 'A')"
)


def _specs(main_db: Path) -> tuple[DatabaseSpec, ...]:
    return (
        DatabaseSpec(
            name="primary", role="primary", driver="sqlite", host="", port=0,
            database=str(main_db), user="", password="", pool_size=2, max_overflow=1,
        ),
    )


@pytest.fixture
def agg_db(tmp_path: Path) -> Path:
    """ATTACH 全域钩子（Engine 类级 connect）——生产读面逐调用新建的会话管理器
    同样出 agg schema；fixture 摘钩后零残留。非 sqlite 连接静默跳过。"""
    agg_file = tmp_path / "agg.db"

    def _attach(dbapi_conn: Any, _record: Any) -> None:
        try:
            cursor = dbapi_conn.cursor()
            cursor.execute(f"ATTACH DATABASE '{agg_file}' AS agg")
            cursor.close()
        except Exception:  # 非 sqlite 驱动（asyncpg 等）无 ATTACH 语义——测试钩子跳过
            pass

    event.listen(Engine, "connect", _attach)
    yield agg_file
    event.remove(Engine, "connect", _attach)


async def _seed(main_db: Path, agg_db: Path) -> None:
    """主库（water_line＋sem_metric）与 ATTACH 侧（agg 三表）行值——只灌水位前窗。"""
    db = ConnectionManager(_specs(main_db))
    try:
        async with db.session() as session:
            await session.execute(text(
                "CREATE TABLE water_line (layer TEXT PRIMARY KEY, data_date DATE,"
                " promise TEXT NOT NULL)"
            ))
            await session.execute(text(
                "INSERT INTO water_line VALUES ('汇总层', '2026-08-31', 'T-1')"
            ))
            await session.execute(text(_SEM_METRIC_DDL))
            await session.execute(text(_SEM_METRIC_ROW))
            for ddl in _SEM_EMPTY_DDL:
                await session.execute(text(ddl))
            for ddl in (
                "CREATE TABLE agg.dim_well (well_id TEXT PRIMARY KEY,"
                " block_name TEXT, field_name TEXT)",
                "CREATE TABLE agg.dim_date (date DATE PRIMARY KEY, month TEXT,"
                " quarter TEXT)",
                "CREATE TABLE agg.fct_daily_metering (well_id TEXT, prod_date DATE,"
                " oil_output NUMERIC(10,2), liquid_output NUMERIC(10,2),"
                " oil_pressure NUMERIC(6,2), batch_id TEXT, quality_flag TEXT,"
                " PRIMARY KEY (well_id, prod_date))",
            ):
                await session.execute(text(ddl))
            await session.execute(text(
                "INSERT INTO agg.dim_well VALUES ('N-01', '渤中', '渤中')"
            ))
            await session.execute(text(
                "INSERT INTO agg.dim_date VALUES ('2026-08-31', '2026-08', '2026-Q3')"
            ))
            await session.execute(text(
                "INSERT INTO agg.fct_daily_metering"
                " VALUES ('N-01', '2026-08-31', 21.16, NULL, NULL,"
                " 'b-a1a61db9f458', NULL)"
            ))
    finally:
        await db.dispose()


def _composition_client(tmp_path: Path, agg_db: Path, *, enabled: bool) -> TestClient:
    """生产组合（registry=None）＋sqlite 底座——DE-16 开关两向的装配点。"""
    main_db = tmp_path / "main.db"
    asyncio.run(_seed(main_db, agg_db))
    app = create_app(
        db=ConnectionManager(_specs(main_db)),
        completer=ScriptedCompleter(_SCRIPT),
        specs=_specs(main_db),
        chat_settings=ChatSettings(freshness_gate_enabled=enabled),
        today=lambda: TODAY,
    )
    return TestClient(app)


def _parse_frames(payload: str) -> list[tuple[str, dict[str, Any]]]:
    frames: list[tuple[str, dict[str, Any]]] = []
    for block in payload.split("\n\n"):
        if not block.strip():
            continue
        name: str | None = None
        data: dict[str, Any] | None = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line.removeprefix("event: ")
            elif line.startswith("data: "):
                data = json.loads(line.removeprefix("data: "))
        assert name is not None and data is not None
        frames.append((name, data))
    return frames


def _ask(client: TestClient) -> list[tuple[str, dict[str, Any]]]:
    resp = client.post(
        "/api/v2/chat/asks", json={"question": "9 月上旬的日产油量"}, headers=ACTOR
    )
    assert resp.status_code == 200
    return _parse_frames(resp.text)


# ---------- DE-16 两向（生产主链——registry=None 组合根真装配） ----------


def test_de16_enabled_freshness_block_stops(tmp_path: Path, agg_db: Path) -> None:
    """闸开（缺省现状）：窗整体晚于水位——水位拦停在（零数值，不冒充出数）。"""
    with _composition_client(tmp_path, agg_db, enabled=True) as client:
        frames = _ask(client)
        # 六步走完（拦停不炸链——tool ok→observe→verify 闸依据如实转答）。
        assert [d["step"] for n, d in frames if n == "step"] == [
            "understand", "plan", "tool", "observe", "verify", "answer",
        ]
        # 拦停 notice 在场：水位 2026-08-31＋窗标签——零数值行。
        blocked = [
            d for n, d in frames if n == "notice" and d.get("type") == "freshness_block"
        ]
        assert blocked, "新鲜度闸拦停 notice 未发出"
        content = blocked[0]["content"]
        assert "新鲜度闸拦停" in content
        assert "2026-08-31" in content
        assert "21.16" not in content  # 零数值（拦停不冒充）
        # run 状态机收口。
        run_id = frames[0][1]["run_id"]
        status = client.get(f"/api/v2/chat/runs/{run_id}", headers=ACTOR).json()
        assert status["status"] == "completed"


def test_de16_disabled_zero_rows_refused(tmp_path: Path, agg_db: Path) -> None:
    """闸关：不读水位不拦停——执行缝放行，窗内 0 行＝查无数据如实拒答。"""
    with _composition_client(tmp_path, agg_db, enabled=False) as client:
        frames = _ask(client)
        # 闸拒直达收口（runtime refused 转答不进观察/核验——graph._apply_result）。
        assert [d["step"] for n, d in frames if n == "step"] == [
            "understand", "plan", "tool", "answer",
        ]
        assert not [
            d for n, d in frames if n == "notice" and d.get("type") == "freshness_block"
        ]
        refused = [d for n, d in frames if n == "notice" and d.get("type") == "refused"]
        assert refused, "0 行如实拒答 notice 未发出"
        assert "查无数据" in refused[0]["content"]  # 0 行如实拒答——不冒充出数
        run_id = frames[0][1]["run_id"]
        status = client.get(f"/api/v2/chat/runs/{run_id}", headers=ACTOR).json()
        assert status["status"] == "completed"
