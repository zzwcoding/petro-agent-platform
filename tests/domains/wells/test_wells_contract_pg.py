"""A2 井档案四端点 DTO 逐字段投影——PG16 集成（M-02 票面测试 a/b/c）。

约定（同 tests/infra/test_db_midplatform_pg.py）：TEST_DATABASE_URL 未配置即
skip；测试自动落 <库名>_test 独立库。中台库测试数据＝DP-03 交付物实建
（001_lake_schemas.up.sql 幂等落 raw 8 表＋midplatform_readonly.sql 模板
<SET_ME> 换测试口令实建只读账号），fixture 井数据经管理员连接装载
（设定书 §A 样本＋A2.jsx 种子逐字照抄——业务事实零发明），端点经 midplatform
只读路由实连取行，DTO 与合同逐字段断言（L0 抽查对账面）。

覆盖：端点 1 列表（服务端行级过滤预埋＋排序）；端点 2 档案明细 8 字段＋
quality_notes 红字＋卡底注记；端点 3 关系链（合并视图倒序全序＋三台账＋五页
签计数＋枚举尾注＋收编常量＋tail 待装配标注）；端点 4 变动页签端点壳（V1
A3 主单未建——空列表＋total=0，不 mock 假单）；well_id 归一化（N2/N-2→N-02）；
404（well_not_found 错误包）。
"""

import os
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.deps import get_wells
from app.api.errors import install_error_handlers
from app.api.wells import router as wells_router
from app.domains.wells import (
    DEVICE_STATUS_VALUES,
    WellsService,
    ensure_wells_tables,
)
from app.infra.db import ConnectionManager, DatabaseSpec

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
MIDPLATFORM_TEST_PASSWORD = "midplatform-m02-pw"  # 测试口令（模板 <SET_ME> 替换值）

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DATA_PLANE_MIGRATIONS = _REPO_ROOT / "data-plane" / "migrations"
LAKE_SCHEMA_SQL = _DATA_PLANE_MIGRATIONS / "001_lake_schemas.up.sql"
ROLE_SQL = _DATA_PLANE_MIGRATIONS / "midplatform_readonly.sql"

HEADERS = {"X-Dev-User": "aqiang"}

# ---------- fixture 井数据（设定书 §A 样本＋合同/A2.jsx 种子值逐字照抄） ----------

_FIXTURE_WELLS: tuple[tuple[str | None, ...], ...] = (
    # well_id, well_name, well_type, first_prod_date, platform, block, status, remarks
    ("N-02", "渤中28-1-N2", "EW", "2019-06-15", "CEP-A", "渤南", "生产中", "正常"),
    ("N-06", None, "IW", "2019-08-01", "CEP-A", "渤南", "生产中", "分层注水（3 层）"),
    ("N-11", None, "EW", "2020-02-20", "CEP-B", "渤中", "停产", "2026-08-30 起检泵"),
    ("N-21", None, "IW", "2021-01-01", "CEP-A", "渤南", "生产中", None),  # 非演示井（降级面）
)

_FIXTURE_MEASURES: tuple[tuple[str, str, str], ...] = (
    ("N-02", "调剖", "2026-03-18"),
    ("N-02", "酸化", "2025-09-06"),
    ("N-02", "补孔", "2024-06-12"),
    ("N-02", "压裂", "2023-04-20"),
    ("N-02", "调剖", "2022-08-15"),
    ("N-06", "调剖", "2026-07-22"),
    ("N-06", "调剖", "2025-12-15"),
    ("N-06", "调剖", "2024-09-10"),
    ("N-06", "调剖", "2023-05-18"),
    ("N-21", "酸化", "2026-01-05"),  # 无冻结演示文案行——content/result 如实 None
)

_FIXTURE_OVERHAULS: tuple[tuple[str, str, str, str, str, str], ...] = (
    # well_id, start, end, overhaul_type, affected_output, batch_id
    ("N-02", "2024-10-09", "2024-10-11", "检泵（泵轴更换）", "影响产量约 18 吨", "20241012-T2"),
    (
        "N-06", "2025-03-05", "2025-03-06", "注水泵保养性检修",
        "影响约 0 吨（注水量当日回补）", "20250307-T1",
    ),
    ("N-11", "2026-08-28", "2026-09-06", "检泵", "影响产量约 210 吨", "20260911-T3"),
    ("N-11", "2025-05-12", "2025-05-18", "检泵（皮带更换）", "影响产量约 45 吨", "20250516-T1"),
    ("N-11", "2024-02-19", "2024-02-21", "检泵（机械密封更换）", "影响产量约 15 吨", "20240222-T1"),
    ("N-11", "2023-07-06", "2023-07-09", "洗井（复产前）", "影响产量约 3 吨", "20230710-T2"),
)

_FIXTURE_STATUS_LOG: tuple[tuple[str, str, str, str | None], ...] = (
    # well_id, occurred_on, title, outcome（警示文案）
    ("N-06", "2026-01-08", '注水方式变更为"分层注水（3 层）"', None),
    ("N-11", "2026-08-30", '台账状态变更为"停产"',
     "状态滞后：9-14 产量表仍有开井 6.5 小时记录，已提示数据岗。"),
    ("N-11", "2026-09-07", "检泵结束，作业区申请复产",
     '档案状态仍记"停产"：复产待确认，状态滞后自 9-07 起。'),
)

_ALL_WELL_IDS = ("N-02", "N-06", "N-11", "N-21")


# ---------- 底座（DP-03 SQL 实建＋fixture 装载——照仓内 PG 集成测试惯例） ----------


def _isolated_url() -> URL:
    url = make_url(TEST_DATABASE_URL)
    return url.set(database=f"{url.database}_test")


async def _ensure_test_database(url: URL) -> None:
    admin = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = (
                await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": url.database},
                )
            ).scalar()
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        await admin.dispose()


def _split_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    for line in sql_text.splitlines():
        buffer.append(line)
        if line.split("--", 1)[0].rstrip().endswith(";"):
            statements.append("\n".join(buffer))
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        statements.append(tail)
    return [
        s for s in statements
        if any(
            line.strip() and not line.strip().startswith("--")
            for line in s.splitlines()
        )
    ]


def _first_effective_code(statement: str) -> str:
    for line in statement.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("--"):
            return stripped
    return ""


def _d(value: str | None) -> date | None:
    """ISO 串 → date（asyncpg DATE 列要真 date 对象，不吃字符串）。"""
    return date.fromisoformat(value) if value else None


def _d_required(value: str) -> date:
    parsed = _d(value)
    assert parsed is not None
    return parsed


async def _apply_dp03(url: URL) -> None:
    """DP-03 两份交付物幂等落库（raw 8 表 DDL＋midplatform 只读账号）。"""
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            for statement in _split_statements(LAKE_SCHEMA_SQL.read_text(encoding="utf-8")):
                await conn.execute(text(statement))
            role_exists = (
                await conn.execute(
                    text("SELECT 1 FROM pg_roles WHERE rolname = 'midplatform'")
                )
            ).scalar()
            template = ROLE_SQL.read_text(encoding="utf-8").replace(
                "<SET_ME>", MIDPLATFORM_TEST_PASSWORD
            )
            for statement in _split_statements(template):
                if _first_effective_code(statement).upper().startswith("CREATE ROLE"):
                    if role_exists:  # 幂等：角色已在 → 只对口令归一（ALTER 不吃绑定参数）
                        await conn.execute(
                            text(
                                "ALTER ROLE midplatform WITH LOGIN PASSWORD "
                                f"'{MIDPLATFORM_TEST_PASSWORD}'"
                            )
                        )
                    else:
                        await conn.execute(text(statement))
                    continue
                await conn.execute(text(statement))
    finally:
        await admin.dispose()


async def _load_fixture(url: URL) -> None:
    """fixture 井数据装载（湖行经管理员连接写——midplatform 账号 SELECT-only，
    写不进只读路由；补位表 well_status_log 同理走管理员连接；先清后插幂等）。"""
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            ids = ", ".join(f"'{w}'" for w in _ALL_WELL_IDS)
            await conn.execute(text(f"DELETE FROM raw.well_measures WHERE well_id IN ({ids})"))
            await conn.execute(text(f"DELETE FROM raw.well_overhaul WHERE well_id IN ({ids})"))
            await conn.execute(text(f"DELETE FROM raw.well_info WHERE well_id IN ({ids})"))
            for row in _FIXTURE_WELLS:
                await conn.execute(
                    text(
                        "INSERT INTO raw.well_info (well_id, well_name, well_type, "
                        "first_prod_date, platform, block_name, current_status, "
                        "remarks, _snapshot_id, _batch_id) "
                        "VALUES (:w, :n, :t, :d, :p, :b, :s, :r, 1, 'M02-FIXTURE')"
                    ),
                    {"w": row[0], "n": row[1], "t": row[2], "d": _d(row[3]),
                     "p": row[4], "b": row[5], "s": row[6], "r": row[7]},
                )
            for well_id, measure_type, job_date in _FIXTURE_MEASURES:
                await conn.execute(
                    text(
                        "INSERT INTO raw.well_measures (well_id, measure_type, job_date, "
                        "_snapshot_id, _batch_id) VALUES (:w, :m, :d, 1, 'M02-FIXTURE')"
                    ),
                    {"w": well_id, "m": measure_type, "d": _d_required(job_date)},
                )
            for well_id, start, end, otype, impact, batch in _FIXTURE_OVERHAULS:
                await conn.execute(
                    text(
                        "INSERT INTO raw.well_overhaul (well_id, overhaul_start, "
                        "overhaul_end, overhaul_type, affected_output, batch_id, "
                        "_snapshot_id, _src_batch_id) "
                        "VALUES (:w, :s, :e, :t, :i, :b, 1, 'M02-FIXTURE')"
                    ),
                    {"w": well_id, "s": _d_required(start), "e": _d_required(end),
                     "t": otype, "i": impact, "b": batch},
                )
            # 平台补位表 well_status_log（primary）——fixture 状态变更行
            await conn.execute(
                text(f"DELETE FROM well_status_log WHERE well_id IN ({ids})")
            )
            for well_id, occurred_on, title_, outcome in _FIXTURE_STATUS_LOG:
                await conn.execute(
                    text(
                        "INSERT INTO well_status_log (well_id, occurred_on, title, "
                        "outcome, source_batch, created_at, updated_at) "
                        "VALUES (:w, :d, :t, :o, NULL, now(), now())"
                    ),
                    {"w": well_id, "d": _d_required(occurred_on), "t": title_, "o": outcome},
                )
    finally:
        await admin.dispose()


def _spec(url: URL, role: str, *, user: str, password: str, readonly: bool) -> DatabaseSpec:
    return DatabaseSpec(
        name=role, role=role,  # type: ignore[arg-type]
        driver=url.drivername.split("+", 1)[0],
        host=url.host or "localhost", port=url.port or 5433,
        database=url.database or "", user=user, password=password,
        pool_size=2, max_overflow=1, readonly=readonly,
    )


@pytest.fixture
async def client() -> AsyncIterator[TestClient]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL 未配置——PG 集成测试跳过（约定见票面）")
    missing = [p for p in (LAKE_SCHEMA_SQL, ROLE_SQL) if not p.is_file()]
    if missing:
        raise RuntimeError(f"DP-03 交付物缺失（data-plane 仓未就位）: {missing}")
    url = _isolated_url()
    await _ensure_test_database(url)
    await _apply_dp03(url)

    manager = ConnectionManager(
        [
            _spec(url, "primary", user=url.username or "", password=url.password or "",
                  readonly=False),
            _spec(url, "midplatform", user="midplatform",
                  password=MIDPLATFORM_TEST_PASSWORD, readonly=True),
        ]
    )
    await ensure_wells_tables(manager.engine())  # 幂等——补位表读面承载（fixture 前建）
    await _load_fixture(url)
    # fixture 期连接建于 pytest-asyncio 夹具循环，TestClient 每请求独立 portal
    # 循环——跨循环复用 asyncpg 连接必炸（attached to a different loop）；
    # dispose 弃掉夹具期池连接（引擎可复用，请求期按需重建）。
    await manager.dispose()
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(wells_router)
    app.dependency_overrides[get_wells] = lambda: WellsService(manager)
    with TestClient(app) as test_client:  # 持久 portal——多请求共用一循环（池复用安全）
        yield test_client
    await manager.dispose()


# ---------- 端点 1：选井下拉列表（服务端行级过滤预埋＋well_id 升序） ----------


async def test_endpoint1_list_items_field_by_field(client: TestClient) -> None:
    body: dict[str, Any] = client.get("/api/wells", headers=HEADERS).json()
    assert body["total"] == 4
    assert [i["well_id"] for i in body["items"]] == ["N-02", "N-06", "N-11", "N-21"]
    n02, n06, n11, n21 = body["items"]
    # 合同端点 1 DTO 示例行逐字段（N-02 行）
    assert n02 == {
        "well_id": "N-02", "well_name": "渤中28-1-N2", "well_kind": "采油",
        "well_kind_code": "EW", "block_name": "渤南", "current_status": "生产中",
        "remark": "正常",
    }
    # 空缺井名以 null 返回（页面渲染「—」）；井别码映射
    assert n06["well_name"] is None
    assert n06["well_kind"] == "注水" and n06["well_kind_code"] == "IW"
    assert n06["remark"] == "分层注水（3 层）"
    assert n11["block_name"] == "渤中" and n11["current_status"] == "停产"
    assert n11["remark"] == "2026-08-30 起检泵"
    # 非演示井备注空缺 → null
    assert n21["remark"] is None and n21["well_kind"] == "注水"


# ---------- 端点 2：档案明细（8 字段＋红字＋卡底） ----------


async def test_endpoint2_n11_full_profile(client: TestClient) -> None:
    body: dict[str, Any] = client.get("/api/wells/N-11", headers=HEADERS).json()
    assert body == {
        "well_id": "N-11", "well_name": None, "well_kind": "采油",
        "well_kind_code": "EW", "first_prod_date": "2020-02-20",
        "platform": "CEP-B", "block_name": "渤中", "current_status": "停产",
        "remark": "2026-08-30 起检泵",
        "quality_notes": [
            '台账状态"停产"与产量表 9-14 仍有开井 6.5 小时记录并存（状态滞后，已提示数据岗）。',
            (
                '产量表单位误录：9-14 日产油 12.40"方"'
                "（按渤中密度 0.89 t/m³ 折算 ≈11.04 吨，已提示数据岗）。"
            ),
        ],
        "foot_note": None,
    }


async def test_endpoint2_n06_foot_note_and_empty_notes(client: TestClient) -> None:
    body: dict[str, Any] = client.get("/api/wells/N-06", headers=HEADERS).json()
    assert body["foot_note"] == '注水井无日产油记录，"产量最高"类排名自动排除本井。'
    assert body["quality_notes"] == []
    assert body["first_prod_date"] == "2019-08-01" and body["platform"] == "CEP-A"


async def test_endpoint2_n02_no_red_no_foot(client: TestClient) -> None:
    body: dict[str, Any] = client.get("/api/wells/N-02", headers=HEADERS).json()
    assert body["quality_notes"] == [] and body["foot_note"] is None
    assert body["first_prod_date"] == "2019-06-15"


# ---------- 端点 3：关系链（合并视图＋三台账＋计数＋尾注＋收编常量） ----------


async def test_endpoint3_n02_full_chain(client: TestClient) -> None:
    body: dict[str, Any] = client.get("/api/wells/N-02/chain", headers=HEADERS).json()
    # counts：changes 与端点 4 total 同源同值（V1 A3 主单未建＝0——不 mock 假单）
    assert body["counts"] == {
        "events": 6, "measures": 5, "devices": 2, "overhauls": 1, "changes": 0,
    }
    assert body["measure_types"] == ["压裂", "酸化", "补孔", "调剖"]
    assert body["device_types"] == ["电泵", "螺杆泵", "加热炉"]
    assert body["measure_foot"] == "措施类型枚举：压裂 / 酸化 / 补孔 / 调剖"
    assert body["device_foot"] == "设备类型枚举：电泵 / 螺杆泵 / 加热炉"
    # 措施台账：key 序号＝作业日倒序；content/result＝收编演示文案
    assert body["measures"] == [
        {"key": "m1", "date": "2026-03-18", "type": "调剖",
         "content": "主力层段调剖，调整吸水剖面", "result": "综合含水降 1.2 个点"},
        {"key": "m2", "date": "2025-09-06", "type": "酸化",
         "content": "近井地带解堵酸化", "result": "日增油约 3 吨，三个月后回落"},
        {"key": "m3", "date": "2024-06-12", "type": "补孔",
         "content": "Ⅱ油组补孔", "result": "日增油约 5 吨"},
        {"key": "m4", "date": "2023-04-20", "type": "压裂",
         "content": "主力层重复压裂", "result": "日增油约 8 吨，递减较快"},
        {"key": "m5", "date": "2022-08-15", "type": "调剖",
         "content": "笼统注水条件下调剖", "result": "综合含水降 0.8 个点"},
    ]
    # 设备台账（演示快照——status 落收编三枚举值域）
    assert [d["key"] for d in body["devices"]] == ["d1", "d2"]
    assert body["devices"][0]["type"] == "电泵"
    assert body["devices"][0]["status"] in DEVICE_STATUS_VALUES
    assert body["devices"][0]["note"] == "2021 年换泵更新；上次保养 2026-06-02"
    assert body["devices"][1]["type"] == "加热炉"
    # 检修台账（原名对应；batch＝「批次 」展示拼装）
    assert body["overhauls"] == [
        {"key": "o1", "date_start": "2024-10-09", "date_end": "2024-10-11",
         "job": "检泵（泵轴更换）", "impact": "影响产量约 18 吨", "batch": "批次 20241012-T2"},
    ]
    # 纪录合并视图：倒序全序（合同端点 3 注——m1→m2→o1→m3→m4→m5）
    assert [e["key"] for e in body["events"]] == ["m1", "m2", "o1", "m3", "m4", "m5"]
    assert body["events"][2]["kind"] == "检修"
    assert body["events"][2]["date"] == "2024-10-09"
    assert body["events"][2]["date_end"] == "2024-10-11"  # 仅检修行携带
    assert body["events"][2]["outcome"] == "影响产量约 18 吨 · 批次 20241012-T2"
    assert body["events"][0]["title"] == "调剖 · 主力层段调剖，调整吸水剖面"
    for event in body["events"]:
        if event["kind"] != "检修":
            assert "date_end" not in event
    assert body["tail"] is None


async def test_endpoint3_n06_variant_foot_and_status_event(client: TestClient) -> None:
    body: dict[str, Any] = client.get("/api/wells/N-06/chain", headers=HEADERS).json()
    assert body["counts"] == {
        "events": 6, "measures": 4, "devices": 2, "overhauls": 1, "changes": 0,
    }
    assert body["measure_foot"] == "注水井措施以调剖为主（类型枚举：压裂 / 酸化 / 补孔 / 调剖）"
    assert body["device_foot"] == "设备类型枚举：电泵 / 螺杆泵 / 加热炉"
    assert body["measures"][0]["result"] == "P1 实注占比回落 5 个点"
    assert body["overhauls"][0]["impact"] == "影响约 0 吨（注水量当日回补）"
    # 状态变更行（补位表读面）：kind/date/title＋警示缺省 outcome=null
    status_events = [e for e in body["events"] if e["kind"] == "状态变更"]
    assert len(status_events) == 1
    assert status_events[0]["date"] == "2026-01-08"
    assert status_events[0]["title"] == '注水方式变更为"分层注水（3 层）"'
    assert status_events[0]["outcome"] is None
    assert status_events[0]["key"].startswith("s")  # 源行锚（bigserial id）
    # tail＝受效关系「待装配」如实标注（well_effect_relation 未装配——不洗白）
    assert body["tail"] == "关系：N-06 —受效→ 受效油井（劈分系数 Σ=1）——受效井清单未装配"


async def test_endpoint3_n11_empty_measures_keeps_foot(client: TestClient) -> None:
    body: dict[str, Any] = client.get("/api/wells/N-11/chain", headers=HEADERS).json()
    assert body["counts"] == {
        "events": 6, "measures": 0, "devices": 2, "overhauls": 4, "changes": 0,
    }
    # 措施 0 行页签仍常驻显示枚举尾注（合同端点 3 measures 条）
    assert body["measures"] == []
    assert body["measure_foot"] == "措施类型枚举：压裂 / 酸化 / 补孔 / 调剖"
    assert body["device_foot"] == "检泵作业对象＝抽油设备（类型枚举：电泵 / 螺杆泵 / 加热炉）"
    statuses = {d["status"] for d in body["devices"]}
    assert statuses <= set(DEVICE_STATUS_VALUES)
    assert body["devices"][0]["note"] == "本次检泵作业对象；停机原因编码：新 BELT（旧 R3＝皮带断）"
    assert len(body["overhauls"]) == 4
    assert body["overhauls"][0]["job"] == "检泵"
    assert body["overhauls"][0]["batch"] == "批次 20260911-T3"
    # events 两条状态变更行带警示 outcome（合同 N-11 链上差异）
    status_events = [e for e in body["events"] if e["kind"] == "状态变更"]
    assert [e["date"] for e in status_events] == ["2026-09-07", "2026-08-30"]
    assert status_events[1]["outcome"] == (
        "状态滞后：9-14 产量表仍有开井 6.5 小时记录，已提示数据岗。"
    )
    assert status_events[0]["outcome"] == '档案状态仍记"停产"：复产待确认，状态滞后自 9-07 起。'
    assert [e["kind"] for e in body["events"]].count("检修") == 4
    assert body["tail"] == (
        "追溯结论：本井停产环节＝检泵作业（检修台账）；措施层无在案记录。遍历深度为受控参数"
    )


async def test_endpoint3_non_demo_well_degrades_honestly(client: TestClient) -> None:
    """非演示井降级面：无冻结文案行 content/result 如实 None；设备空、尾注通版、
    tail null——零发明。"""
    body: dict[str, Any] = client.get("/api/wells/N-21/chain", headers=HEADERS).json()
    assert body["counts"] == {
        "events": 1, "measures": 1, "devices": 0, "overhauls": 0, "changes": 0,
    }
    assert body["measures"] == [
        {"key": "m1", "date": "2026-01-05", "type": "酸化", "content": None, "result": None},
    ]
    assert body["devices"] == []
    assert body["measure_foot"] == "措施类型枚举：压裂 / 酸化 / 补孔 / 调剖"
    assert body["device_foot"] == "设备类型枚举：电泵 / 螺杆泵 / 加热炉"
    assert body["events"][0]["title"] == "酸化"  # 内容缺省 → 仅类型
    assert body["tail"] is None


# ---------- 端点 4：变动页签端点壳（V1 A3 主单未建——空列表＋如实注记） ----------


@pytest.mark.parametrize("well_id", ["N-02", "N-06", "N-11"])
async def test_endpoint4_shell_empty(client: TestClient, well_id: str) -> None:
    body: dict[str, Any] = (
        client.get(f"/api/wells/{well_id}/change-tickets", headers=HEADERS).json()
    )
    assert body == {"well_id": well_id, "items": [], "total": 0}


# ---------- 归一化与 404（行为规则 1③/常量表 well_id 行） ----------


@pytest.mark.parametrize("raw_id", ["N2", "N-2"])
async def test_well_id_normalized_path(client: TestClient, raw_id: str) -> None:
    """路径参数按归一化主键解析（N2/N-2→N-02）——响应即归一化后主键。"""
    body: dict[str, Any] = client.get(f"/api/wells/{raw_id}", headers=HEADERS).json()
    assert body["well_id"] == "N-02"


async def test_404_unknown_well_all_endpoints(client: TestClient) -> None:
    for path in ("/api/wells/N-99", "/api/wells/N-99/chain",
                 "/api/wells/N-99/change-tickets"):
        resp = client.get(path, headers=HEADERS)
        assert resp.status_code == 404, path
        assert resp.json()["code"] == "well_not_found"
