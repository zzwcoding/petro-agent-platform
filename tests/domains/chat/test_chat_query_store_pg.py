"""chat 问数执行器——agg 星型读模型 PG16 集成（M-06 票面测试 c 之真库半边）。

约定（同 tests/infra/test_db_midplatform_pg.py）：TEST_DATABASE_URL 未配置即
skip；测试自动落 <库名>_test 独立库。agg 三表 DDL＝Alembic 0014 照抄（本文件
内联直句——迁移按链由部署批跑，测试独立库自建自删）；fixture 行＝设定书 §A
样本量级（业务事实零发明——行值只服务断言，不注源为业务数字）。覆盖：
execute_plan 排名型（GROUP BY 井合计倒序＋LIMIT 收口＋batch 水位随行）/明细型
（井×日稳定序）/行级注入两步缝（预埋恒真回执计 0）。
"""

import os
from collections.abc import AsyncIterator
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.chat import domain as d
from app.domains.chat.query_store import QueryStore
from app.infra.db import ConnectionManager, DatabaseSpec

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL 未配置——PG 集成测试跳过"
)

# agg 三表 DDL（Alembic 0014 upgrade 直句照抄——测试独立库自建，随库销毁）。
_AGG_DDL = (
    "CREATE SCHEMA IF NOT EXISTS agg",
    """CREATE TABLE IF NOT EXISTS agg.dim_well (
        well_id    VARCHAR(8)  NOT NULL,
        block_name VARCHAR(16),
        field_name VARCHAR(32),
        PRIMARY KEY (well_id)
    )""",
    """CREATE TABLE IF NOT EXISTS agg.dim_date (
        date    DATE       NOT NULL,
        month   VARCHAR(7) NOT NULL,
        quarter VARCHAR(7) NOT NULL,
        PRIMARY KEY (date)
    )""",
    """CREATE TABLE IF NOT EXISTS agg.fct_daily_metering (
        well_id       VARCHAR(8)   NOT NULL,
        prod_date     DATE         NOT NULL,
        oil_output    NUMERIC(10,2),
        liquid_output NUMERIC(10,2),
        oil_pressure  NUMERIC(6,2),
        batch_id      VARCHAR(64),
        quality_flag  VARCHAR(16),
        PRIMARY KEY (well_id, prod_date)
    )""",
    "CREATE INDEX IF NOT EXISTS idx_agg_fct_prod_date ON agg.fct_daily_metering (prod_date)",
)

# fixture 行（量级样本——数值只服务排序/截断断言；batch 水位两批并存验证随行）。
_FIXTURE_WELLS = [("N-02", "渤南", "渤中"), ("N-11", "渤中", "渤中"), ("N-06", "渤西", "渤西")]
_FIXTURE_DATES = [date(2026, 9, 10), date(2026, 9, 11)]
_FIXTURE_FACTS = [  # (well_id, prod_date, oil_output, liquid_output, batch_id)
    ("N-02", _FIXTURE_DATES[0], "100.10", "500.00", "B20260911-T3"),
    ("N-02", _FIXTURE_DATES[1], "120.20", "510.00", "B20260911-T3"),
    ("N-11", _FIXTURE_DATES[0], "80.30", "400.00", "B20260912-T1"),
    ("N-11", _FIXTURE_DATES[1], "60.40", "390.00", "B20260912-T1"),
    ("N-06", _FIXTURE_DATES[0], "40.50", "300.00", "B20260912-T1"),
]


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


async def _load_fixture(url: URL) -> None:
    engine = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.begin() as conn:
            for statement in _AGG_DDL:
                await conn.execute(text(statement))
            for well_id, block, field in _FIXTURE_WELLS:
                await conn.execute(
                    text("INSERT INTO agg.dim_well (well_id, block_name, field_name) "
                         "VALUES (:w, :b, :f) ON CONFLICT DO NOTHING"),
                    {"w": well_id, "b": block, "f": field},
                )
            for day in _FIXTURE_DATES:
                month = f"{day.year}-{day.month:02d}"
                quarter = f"{day.year}-Q{(day.month - 1) // 3 + 1}"
                await conn.execute(
                    text("INSERT INTO agg.dim_date (date, month, quarter) "
                         "VALUES (:d, :m, :q) ON CONFLICT DO NOTHING"),
                    {"d": day, "m": month, "q": quarter},
                )
            for well_id, day, oil, liquid, batch in _FIXTURE_FACTS:
                await conn.execute(
                    text(
                        "INSERT INTO agg.fct_daily_metering "
                        "(well_id, prod_date, oil_output, liquid_output, "
                        "oil_pressure, batch_id, quality_flag) "
                        "VALUES (:w, :d, :o, :l, NULL, :b, NULL) ON CONFLICT DO NOTHING"
                    ),
                    {"w": well_id, "d": day, "o": oil, "l": liquid, "b": batch},
                )
    finally:
        await engine.dispose()


@pytest.fixture
async def pg_db() -> AsyncIterator[ConnectionManager]:
    url = _isolated_url()
    await _ensure_test_database(url)
    await _load_fixture(url)
    spec = DatabaseSpec(
        name="primary", role="primary", driver="postgresql", host=url.host or "",
        port=url.port or 5432, database=url.database or "", user=url.username or "",
        password=url.password or "", pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    yield manager
    await manager.dispose()


def _plan(*, ranking: bool) -> d.QueryPlan:
    return d.QueryPlan(
        metric_slot="日产油量", metric_name="★日产油量", measure_column="oil_output",
        unit="吨",
        window=d.TimeWindow(start=date(2026, 9, 1), end=date(2026, 10, 1), label="上个月"),
        limit_requested=2 if ranking else None, limit_effective=2 if ranking else 50,
        ranking=ranking, actor="aqiang",
    )


class TestQueryStorePg:
    async def test_ranking_plan_orders_and_limits(self, pg_db: ConnectionManager) -> None:
        """排名型：井合计倒序＋LIMIT 收口（N=2 只取前 2）＋batch 水位随行。"""
        store = QueryStore(pg_db)
        result = await store.execute_plan(_plan(ranking=True))
        assert [row["well_id"] for row in result.rows] == ["N-02", "N-11"]
        assert result.batch_id == "B20260911-T3"  # 行序首个非空 batch（首名行组内 MAX）
        assert result.row_filter_predicates == 0  # 预埋恒真——回执如实计 0
        assert set(result.rows[0]) == {"well_id", "block_name", "日产油量合计（吨）"}

    async def test_detail_plan_stable_order(self, pg_db: ConnectionManager) -> None:
        """明细型：井×日粒度（fixture 5 行全量——LIMIT 50 不截）＋日期稳定序。"""
        store = QueryStore(pg_db)
        result = await store.execute_plan(_plan(ranking=False))
        assert len(result.rows) == 5
        dates = [row["prod_date"] for row in result.rows]
        assert dates == sorted(dates)
        assert result.rows[0]["well_id"] == "N-02"
        assert "batch_id" not in result.rows[0]  # 水位只随血缘卡——不进答案表卡

    async def test_window_bounds_apply(self, pg_db: ConnectionManager) -> None:
        """窗口半开区间下推（[start, end)——越界行不进结果集）。"""
        store = QueryStore(pg_db)
        plan = d.QueryPlan(
            metric_slot="日产油量", metric_name="★日产油量", measure_column="oil_output",
            unit="吨",
            window=d.TimeWindow(start=date(2026, 9, 11), end=date(2026, 10, 1), label="窗口"),
            limit_requested=None, limit_effective=50, ranking=False, actor="aqiang",
        )
        result = await store.execute_plan(plan)
        assert len(result.rows) == 2  # 仅 09-11 两行（N-02/N-11——N-06 无当日行）
        assert result.batch_id == "B20260911-T3"  # 行序首个非空 batch（明细型随行口径）
