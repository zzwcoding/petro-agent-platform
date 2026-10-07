"""DE-02 wells 三端点当前快照过滤——多批 fixture PG16 回归（票面交付物 4）。

约定（同 test_wells_snapshot_pg.py）：TEST_DATABASE_URL 未配置即 skip；测试
自动落 <库名>_test 独立库；专属角色 midplatform_test（M-08——dev 共享角色
midplatform 零触碰）；DP-03 两份交付物只读消费；账本/源表清理只动 DE02-
前缀自留地（跨文件共存——DE01 前缀账本行不碰）。

fixture＝well_info/well_measures/well_overhaul 各两批（``_snapshot_id`` 指向
真账本行实发 id）＋data_plane.lake_snapshot 账本行（DE02- 前缀）；服务装配
＝生产同款（LakeSnapshotReader.current_snapshot 注入 WellsService——DE-02
生产缝形状，取数走 primary 只读路由读账本）。

断言（票面验收——E10 多批重复行收口，合同「一口井一份档案」读语义）：
- 端点 1 列表：每井恰 1 行、内容＝最新批（旧批行不出现）；
- 端点 2 档案：只出最新批内容；
- 端点 3 关系链：措施/检修台账只出最新批（台账表同是 append-only 湖表，
  多批叠加同病同修；状态变更行为平台补位表不过滤）；
- 账本无记录态回落全量（DE-01 三态语义）：单表无记录→该表两批都出行；
  三表账本全空→列表回落全量（每井两行）。

本地跑法（PG16＝主仓 compose pg 容器，宿主 5433；data-plane 交付物需在位）：
    export TEST_DATABASE_URL=postgresql+asyncpg://petro:petro@localhost:5433/petro
    uv run pytest tests/domains/wells/test_wells_snapshot_filter_pg.py -q
"""

import os
import re
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
    LakeSnapshotReader,
    WellsService,
    ensure_wells_tables,
)
from app.infra.db import ConnectionManager, DatabaseSpec

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")
MIDPLATFORM_DEV_ROLE = "midplatform"  # dev 共享角色——测试禁碰（M-08 根治点）
MIDPLATFORM_TEST_ROLE = "midplatform_test"  # 测试专属角色——DP-03 模板渲染目标
MIDPLATFORM_TEST_PASSWORD = "midplatform-de02-pw"  # 测试口令（模板 <SET_ME> 替换值）

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DATA_PLANE_MIGRATIONS = _REPO_ROOT / "data-plane" / "migrations"
LAKE_SCHEMA_SQL = _DATA_PLANE_MIGRATIONS / "001_lake_schemas.up.sql"
ROLE_SQL = _DATA_PLANE_MIGRATIONS / "midplatform_readonly.sql"

HEADERS = {"X-Dev-User": "aqiang"}
_WELL_IDS = ("N-02", "N-06")

# ---------- fixture：两批井数据（旧批应被当前版过滤；新批对齐合同样本值） ----------

_FIXTURE_WELLS: dict[str, tuple[tuple[str | None, ...], ...]] = {
    "B1": (  # 旧批（DE02-B1）——业务值除井主键外为测试造数，标注应被过滤
        ("N-02", "渤中28-1-N2", "EW", "2019-06-15", "CEP-A", "渤南", "生产中",
         "旧批备注（应被当前版过滤）"),
        ("N-06", None, "IW", "2019-08-01", "CEP-A", "渤南", "生产中",
         "旧批备注（应被当前版过滤）"),
    ),
    "B2": (  # 最新批（DE02-B2）——备注等对齐 A2 合同样本值
        ("N-02", "渤中28-1-N2", "EW", "2019-06-15", "CEP-A", "渤南", "生产中", "正常"),
        ("N-06", None, "IW", "2019-08-01", "CEP-A", "渤南", "生产中", "分层注水（3 层）"),
    ),
}

# (well_id, measure_type, job_date)——措施台账两批各一行（不同类型不同日）
_FIXTURE_MEASURES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "M1": (("N-02", "调剖", "2022-01-10"),),
    "M2": (("N-02", "酸化", "2026-03-01"),),
}

# (well_id, start, end, type, impact, batch_id)——检修台账两批各一行
_FIXTURE_OVERHAULS: dict[str, tuple[tuple[str, str, str, str, str, str], ...]] = {
    "O1": (("N-02", "2022-01-05", "2022-01-07", "洗井（旧批造数）",
            "影响产量约 1 吨", "20220108-T0"),),
    "O2": (("N-02", "2026-02-10", "2026-02-12", "检泵",
            "影响产量约 9 吨", "20260213-T9"),),
}

# FX-06 增量批场景（well_info）：批 1 两井全量导出，批 2 增量只含 N-02 的更新
# （N-06 未再导出）——per-key as-of 对齐湖 scan 后 N-06 仍以批 1 数据可见；
# 旧过滤（全局最新批等值）下 N-06 静默消失即本场景红。
_FIXTURE_INCREMENTAL: dict[str, tuple[tuple[str, str], ...]] = {
    "I1": (  # 批 1（全量导出）：两井各一行
        ("N-02", "增量批 B1 备注（N-02 旧版）"),
        ("N-06", "增量批 B1 备注（N-06 未再导出）"),
    ),
    "I2": (  # 批 2（增量导出）：只含 N-02 的更新——N-06 不在批 2
        ("N-02", "增量批 B2 备注（N-02 独更）"),
    ),
}


# ---------- 底座（照 test_wells_snapshot_pg.py 惯例——DP-03 SQL 实建） ----------


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


def _render_role_sql() -> str:
    """DP-03 模板 → 专属测试角色版（先换名后换 <SET_ME>——口令串含角色名前缀）。"""
    rendered = re.sub(
        rf"\b{MIDPLATFORM_DEV_ROLE}\b",
        MIDPLATFORM_TEST_ROLE,
        ROLE_SQL.read_text(encoding="utf-8"),
    )
    return rendered.replace("<SET_ME>", MIDPLATFORM_TEST_PASSWORD)


async def _apply_dp03(conn: Any) -> None:
    """湖 schema DDL 幂等落库＋专属测试角色实建（幂等——已在则只归一口令）。"""
    for statement in _split_statements(LAKE_SCHEMA_SQL.read_text(encoding="utf-8")):
        await conn.execute(text(statement))
    template = _render_role_sql()
    role_exists = (
        await conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :role"),
            {"role": MIDPLATFORM_TEST_ROLE},
        )
    ).scalar()
    for statement in _split_statements(template):
        if _first_effective_code(statement).upper().startswith("CREATE ROLE"):
            if role_exists:
                await conn.execute(
                    text(
                        f"ALTER ROLE {MIDPLATFORM_TEST_ROLE} WITH LOGIN PASSWORD "
                        f"'{MIDPLATFORM_TEST_PASSWORD}'"
                    )
                )
            else:
                await conn.execute(text(statement))
            continue
        await conn.execute(text(statement))


def _d(value: str) -> date:
    """ISO 串 → date（asyncpg DATE 列要真 date 对象，不吃字符串）。"""
    return date.fromisoformat(value)


async def _load_multi_batch_fixture(url: URL) -> None:
    """两批 raw 行＋真账本行（``_snapshot_id`` 指向账本实发 id）。

    先清后插幂等（raw 按井清、账本按 DE02- 前缀清——DE01 前缀不碰）；账本
    snapshot_id＝BIGSERIAL 跨跑单调，插入序 B1→B2 保证「最新批」＝id 最大
    （DE-01 判据——追加序即版本序）。"""
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            ids = ", ".join(f"'{w}'" for w in _WELL_IDS)
            await conn.execute(
                text(f"DELETE FROM raw.well_measures WHERE well_id IN ({ids})")
            )
            await conn.execute(
                text(f"DELETE FROM raw.well_overhaul WHERE well_id IN ({ids})")
            )
            await conn.execute(
                text(f"DELETE FROM raw.well_info WHERE well_id IN ({ids})")
            )
            await conn.execute(
                text(f"DELETE FROM well_status_log WHERE well_id IN ({ids})")
            )
            await conn.execute(
                text("DELETE FROM data_plane.lake_snapshot WHERE batch_id LIKE 'DE02-%'")
            )
            for batch, ledger_batch in (
                ("B1", "DE02-B1"), ("B2", "DE02-B2"),
                ("M1", "DE02-M1"), ("M2", "DE02-M2"),
                ("O1", "DE02-O1"), ("O2", "DE02-O2"),
            ):
                table = {
                    "B1": "well_info", "B2": "well_info",
                    "M1": "well_measures", "M2": "well_measures",
                    "O1": "well_overhaul", "O2": "well_overhaul",
                }[batch]
                snapshot_id = (
                    await conn.execute(
                        text(
                            "INSERT INTO data_plane.lake_snapshot "
                            "(table_name, batch_id, data_object_key, manifest) "
                            "VALUES (:t, :b, :k, '{}'::jsonb) RETURNING snapshot_id"
                        ),
                        {
                            "t": table, "b": ledger_batch,
                            "k": f"tpa-raw/{table}/{ledger_batch}/data.csv",
                        },
                    )
                ).scalar_one()
                for row in _FIXTURE_WELLS.get(batch, ()):
                    await conn.execute(
                        text(
                            "INSERT INTO raw.well_info (well_id, well_name, well_type, "
                            "first_prod_date, platform, block_name, current_status, "
                            "remarks, _snapshot_id, _batch_id) "
                            "VALUES (:w, :n, :t, :d, :p, :b, :s, :r, :sid, :lb)"
                        ),
                        {"w": row[0], "n": row[1], "t": row[2], "d": _d(row[3]),
                         "p": row[4], "b": row[5], "s": row[6], "r": row[7],
                         "sid": snapshot_id, "lb": ledger_batch},
                    )
                for row in _FIXTURE_MEASURES.get(batch, ()):
                    await conn.execute(
                        text(
                            "INSERT INTO raw.well_measures (well_id, measure_type, "
                            "job_date, _snapshot_id, _batch_id) "
                            "VALUES (:w, :m, :d, :sid, :lb)"
                        ),
                        {"w": row[0], "m": row[1], "d": _d(row[2]),
                         "sid": snapshot_id, "lb": ledger_batch},
                    )
                for row in _FIXTURE_OVERHAULS.get(batch, ()):
                    await conn.execute(
                        text(
                            "INSERT INTO raw.well_overhaul (well_id, overhaul_start, "
                            "overhaul_end, overhaul_type, affected_output, batch_id, "
                            "_snapshot_id, _src_batch_id) "
                            "VALUES (:w, :s, :e, :t, :i, :b, :sid, :lb)"
                        ),
                        {"w": row[0], "s": _d(row[1]), "e": _d(row[2]), "t": row[3],
                         "i": row[4], "b": row[5], "sid": snapshot_id, "lb": ledger_batch},
                    )
    finally:
        await admin.dispose()


async def _load_incremental_scenario(url: URL) -> None:
    """FX-06 增量批场景（well_info）：批 1 两井全量导出、批 2 增量只含 N-02。

    先清后插（只动两 fixture 井的 well_info 行与 DE02-I 前缀账本行）；账本
    插入序 I1→I2 保证 snapshot_id 递增＝「最新批」判据（追加序即版本序）。
    """
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            ids = ", ".join(f"'{w}'" for w in _WELL_IDS)
            await conn.execute(
                text(f"DELETE FROM raw.well_info WHERE well_id IN ({ids})")
            )
            await conn.execute(
                text(
                    "DELETE FROM data_plane.lake_snapshot "
                    "WHERE batch_id LIKE 'DE02-I%'"
                )
            )
            for batch in ("I1", "I2"):
                snapshot_id = (
                    await conn.execute(
                        text(
                            "INSERT INTO data_plane.lake_snapshot "
                            "(table_name, batch_id, data_object_key, manifest) "
                            "VALUES ('well_info', :b, :k, '{}'::jsonb) "
                            "RETURNING snapshot_id"
                        ),
                        {
                            "b": f"DE02-{batch}",
                            "k": f"tpa-raw/well_info/DE02-{batch}/data.csv",
                        },
                    )
                ).scalar_one()
                for well_id, remark in _FIXTURE_INCREMENTAL[batch]:
                    await conn.execute(
                        text(
                            "INSERT INTO raw.well_info (well_id, well_name, "
                            "well_type, first_prod_date, platform, block_name, "
                            "current_status, remarks, _snapshot_id, _batch_id) "
                            "VALUES (:w, :n, 'EW', :d, 'CEP-A', '渤南', '生产中', "
                            ":r, :sid, :lb)"
                        ),
                        {"w": well_id, "n": "渤中28-1-N2",
                         "d": date.fromisoformat("2019-06-15"), "r": remark,
                         "sid": snapshot_id, "lb": f"DE02-{batch}"},
                    )
    finally:
        await admin.dispose()


async def _delete_ledger(url: URL, table_name: str | None) -> None:
    """账本行删除（回落全量态制造）——table_name None＝三表全清。

    清理不分前缀：回落态的前提是「该表账本零行」（DE-01 三态语义查的是
    真账本），共享测试库里他票前缀（DE01-%）的同表行同样构成「有记录」，
    必须一并清掉；他票测试各自 fixture 先清后插，互不依赖遗留行。
    """
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            if table_name is None:
                await conn.execute(
                    text(
                        "DELETE FROM data_plane.lake_snapshot WHERE table_name IN "
                        "('well_info', 'well_measures', 'well_overhaul')"
                    )
                )
            else:
                await conn.execute(
                    text(
                        "DELETE FROM data_plane.lake_snapshot WHERE table_name = :t"
                    ),
                    {"t": table_name},
                )
    finally:
        await admin.dispose()


def _spec(
    url: URL, role: str, *, user: str, password: str, readonly: bool
) -> DatabaseSpec:
    return DatabaseSpec(
        name=role, role=role,  # type: ignore[arg-type]
        driver=url.drivername.split("+", 1)[0],
        host=url.host or "localhost", port=url.port or 5433,
        database=url.database or "", user=user, password=password,
        pool_size=2, max_overflow=1, readonly=readonly,
    )


@pytest.fixture
async def url() -> URL:
    """测试库地址（回落态测试直接对账本造无记录态——管理连接自建自毁）。"""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL 未配置——PG 集成测试跳过（约定见票面）")
    return _isolated_url()


@pytest.fixture
async def client() -> AsyncIterator[TestClient]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL 未配置——PG 集成测试跳过（约定见票面）")
    missing = [p for p in (LAKE_SCHEMA_SQL, ROLE_SQL) if not p.is_file()]
    if missing:
        raise RuntimeError(f"DP-03 交付物缺失（data-plane 仓未就位）: {missing}")
    url = _isolated_url()
    await _ensure_test_database(url)
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            await _apply_dp03(conn)
    finally:
        await admin.dispose()
    await _load_multi_batch_fixture(url)

    manager = ConnectionManager(
        [
            _spec(url, "primary", user=url.username or "", password=url.password or "",
                  readonly=False),
            _spec(url, "midplatform", user=MIDPLATFORM_TEST_ROLE,
                  password=MIDPLATFORM_TEST_PASSWORD, readonly=True),
        ]
    )
    await ensure_wells_tables(manager.engine())  # 幂等——补位表读面承载（chain 查询）
    # fixture 期连接建于 pytest-asyncio 夹具循环，TestClient 每请求独立 portal
    # 循环——跨循环复用 asyncpg 连接必炸；dispose 弃掉夹具期池连接（同 M-02 先例）。
    await manager.dispose()
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(wells_router)
    # 生产同款装配（DE-02 接线形状）：LakeSnapshotReader.current_snapshot 注入
    app.dependency_overrides[get_wells] = lambda: WellsService(
        manager, snapshot_loader=LakeSnapshotReader(manager).current_snapshot
    )
    try:
        with TestClient(app) as test_client:  # 持久 portal——多请求共用一循环
            yield test_client
    finally:
        # 自留地账本行清场（他票前缀不碰）——DE01 账本对账测试按表名取最新，
        # 本票遗留行会改写其「最新批」判据（跨文件共存纪律，见模块 docstring）
        await manager.dispose()
        await _clean_own_ledger(url)


async def _clean_own_ledger(url: URL) -> None:
    """只清 DE02- 前缀自留地账本行（teardown——DE01 前缀与账本其余行不碰）。"""
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            await conn.execute(
                text("DELETE FROM data_plane.lake_snapshot WHERE batch_id LIKE 'DE02-%'")
            )
    finally:
        await admin.dispose()


# ---------- 端点 1：列表每井恰 1 行、内容＝最新批 ----------


async def test_list_each_well_exactly_one_row_from_latest_batch(
    client: TestClient,
) -> None:
    body: dict[str, Any] = client.get("/api/wells", headers=HEADERS).json()
    well_ids = [i["well_id"] for i in body["items"]]
    # fixture 井各恰 1 行（4 行 raw 叠加 → 每井 1 行——E10 现象收口；共享测试
    # 库可能残留他票 fixture 井，断言按本票 fixture 井计数，不做全局 total）
    assert well_ids.count("N-02") == 1 and well_ids.count("N-06") == 1
    by_id = {i["well_id"]: i for i in body["items"]}
    # 内容＝最新批（B2）——旧批备注（B1）不出现
    assert by_id["N-02"]["remark"] == "正常"
    assert by_id["N-06"]["remark"] == "分层注水（3 层）"
    assert all("旧批备注" not in (i["remark"] or "") for i in body["items"])


# ---------- 端点 2：档案只出最新批内容 ----------


async def test_profile_returns_latest_batch_content(client: TestClient) -> None:
    body: dict[str, Any] = client.get("/api/wells/N-02", headers=HEADERS).json()
    assert body["well_id"] == "N-02"
    assert body["well_name"] == "渤中28-1-N2"
    assert body["remark"] == "正常"  # B2 值；B1 的「旧批备注」被当前版过滤
    assert body["first_prod_date"] == "2019-06-15"
    assert body["current_status"] == "生产中"


# ---------- 端点 3：关系链台账只出最新批 ----------


async def test_chain_ledgers_only_latest_batch(client: TestClient) -> None:
    body: dict[str, Any] = client.get("/api/wells/N-02/chain", headers=HEADERS).json()
    # 措施台账：只 B2 的酸化行（B1 调剖行被过滤）——key 序号重排 m1
    assert body["measures"] == [
        {"key": "m1", "date": "2026-03-01", "type": "酸化",
         "content": None, "result": None},
    ]
    # 检修台账：只 B2 的检泵行（B1 洗井行被过滤）
    assert body["overhauls"] == [
        {"key": "o1", "date_start": "2026-02-10", "date_end": "2026-02-12",
         "job": "检泵", "impact": "影响产量约 9 吨", "batch": "批次 20260213-T9"},
    ]
    # 五页签计数联动（devices＝合同冻结演示快照 2 行；status log 无行）
    assert body["counts"] == {
        "events": 2, "measures": 1, "devices": 2, "overhauls": 1, "changes": 0,
    }
    assert [e["key"] for e in body["events"]] == ["m1", "o1"]
    assert not any("旧批造数" in (e.get("title") or "") for e in body["events"])


# ---------- 账本无记录态回落全量（DE-01 三态语义——DE-02 消费侧） ----------


async def test_ledger_missing_table_falls_back_to_full(
    client: TestClient, url: URL
) -> None:
    """well_overhaul 账本行清空 → 该表回落不过滤（两批都出行）；其余表仍过滤。"""
    await _delete_ledger(url, "well_overhaul")
    body: dict[str, Any] = client.get("/api/wells/N-02/chain", headers=HEADERS).json()
    assert [o["job"] for o in body["overhauls"]] == ["检泵", "洗井（旧批造数）"]
    assert body["counts"]["overhauls"] == 2
    assert body["counts"]["measures"] == 1  # 措施账本仍在——仍只出最新批
    assert [m["type"] for m in body["measures"]] == ["酸化"]


async def test_ledger_empty_falls_back_to_full_everywhere(
    client: TestClient, url: URL
) -> None:
    """三表账本全空 → 全量回落（每井两批两行——DE-01 缺省态读面行为）。"""
    await _delete_ledger(url, None)
    body: dict[str, Any] = client.get("/api/wells", headers=HEADERS).json()
    well_ids = [i["well_id"] for i in body["items"]]
    # 2 井 × 2 批＝各 2 行——不过滤即全量（旧批行重新可见＝回落实证）
    assert well_ids.count("N-02") == 2 and well_ids.count("N-06") == 2
    n02 = [i for i in body["items"] if i["well_id"] == "N-02"]
    assert any(i["remark"] == "旧批备注（应被当前版过滤）" for i in n02)
    assert any(i["remark"] == "正常" for i in n02)


# ---------- FX-01：账本表本身不存在（数据面未 boot）→ 三端点回落全量不 500 ----------


async def test_ledger_table_dropped_falls_back_not_500(
    client: TestClient, url: URL
) -> None:
    """drop data_plane.lake_snapshot（数据面从未 boot 态——平台侧不建账本）→
    reader 对 undefined_table（SQLSTATE 42P01）捕获归 None：三端点 200 回落
    全量，不再 500（R1-02 行为回归收口）。finally 用幂等湖 DDL 复原账本表
    （_apply_dp03 与 fixture 同款）——teardown 的 _clean_own_ledger 要对它
    DELETE，跨测试零残留。"""
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            await conn.execute(text("DROP TABLE data_plane.lake_snapshot"))
    finally:
        await admin.dispose()
    try:
        # 端点 1 列表：200＋全量（每井两批 2 行——不过滤回落）
        body: dict[str, Any] = client.get("/api/wells", headers=HEADERS).json()
        well_ids = [i["well_id"] for i in body["items"]]
        assert well_ids.count("N-02") == 2 and well_ids.count("N-06") == 2
        # 端点 2 档案：200（回落全量下两批行皆在，不 500、不 404）
        profile = client.get("/api/wells/N-02", headers=HEADERS)
        assert profile.status_code == 200
        assert profile.json()["well_id"] == "N-02"
        # 端点 3 关系链：200（两台账两批全出——回落全量）
        chain = client.get("/api/wells/N-02/chain", headers=HEADERS)
        assert chain.status_code == 200
        assert chain.json()["counts"]["measures"] == 2
        assert chain.json()["counts"]["overhauls"] == 2
    finally:
        restore = create_async_engine(url, isolation_level="AUTOCOMMIT")
        try:
            async with restore.connect() as conn:
                await _apply_dp03(conn)
        finally:
            await restore.dispose()


# ---------- FX-06：增量批场景——per-key as-of 对齐湖 scan（旧批井不静默消失） ----------


async def test_incremental_batch_keeps_old_batch_wells(
    client: TestClient, url: URL
) -> None:
    """批 2 增量只含一口井的更新（N-02）→ 旧批井 N-06 仍以批 1 数据可见、
    N-02 出批 2 数据、每井恰 1 行（湖 scan as-of 语义：每业务键取 ≤N 最新版）。

    旧过滤（``_snapshot_id = 全局最新批`` 等值）下 N-06 静默消失（列表无行、
    档案 404）即本例红——R1-01 裁决修复的机判在案。"""
    await _load_incremental_scenario(url)
    # 端点 1 列表：每井恰 1 行——N-06（不在批 2）以批 1 行可见
    body: dict[str, Any] = client.get("/api/wells", headers=HEADERS).json()
    well_ids = [i["well_id"] for i in body["items"]]
    assert well_ids.count("N-02") == 1 and well_ids.count("N-06") == 1
    by_id = {i["well_id"]: i for i in body["items"]}
    # 被更新井出批 2 数据；旧批井保批 1 数据（不被新批清场）
    assert by_id["N-02"]["remark"] == "增量批 B2 备注（N-02 独更）"
    assert by_id["N-06"]["remark"] == "增量批 B1 备注（N-06 未再导出）"
    # 端点 2 档案：旧批井不 404（当前版世界仍在——一口井一份档案读语义）
    profile = client.get("/api/wells/N-06", headers=HEADERS)
    assert profile.status_code == 200
    assert profile.json()["remark"] == "增量批 B1 备注（N-06 未再导出）"
