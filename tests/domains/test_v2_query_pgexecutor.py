"""V2-19 query 生产执行器——PgQueryExecutor agg 星型真 SQL PG16 集成。

约定（同 tests/domains/chat/test_chat_query_store_pg.py）：TEST_DATABASE_URL
未配置即 skip（PG 集成件不进常规门禁——冒烟门控同款纪律）；测试自动落
<库名>_test 独立库。agg 三表 DDL＝Alembic 0014 照抄（本文件内联直句——
测试独立库自建自删）；fixture 行＝量级样本（业务事实零发明——行值只服务
排序/截断/水位断言）。覆盖：
- 排名型：GROUP BY 井＋区块合计倒序＋LIMIT 收口＋block_name 在场＋批次
  水位随行（组内 MAX 聚合——行序首个非空）；
- 升序（R1 二值分派真库向）；明细型：井×日稳定序＋区块列＋batch 剥离
  （水位只随血缘卡——不进答案表卡）；窗口半开区间下推。
"""

import os
from collections.abc import AsyncIterator
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from appv2.infra.db import DatabaseSpec
from appv2.query import DIRECTION_ASC, DIRECTION_DESC, SqlPlan, TimeWindow

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL 未配置——PG 集成测试跳过"
)

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
)

_WELLS = [("N-02", "渤南", "渤中"), ("N-11", "渤中", "渤中"), ("N-06", "渤西", "渤西")]
_DAYS = [date(2026, 9, 10), date(2026, 9, 11)]
_FACTS = (  # (well_id, prod_date, oil_output, batch_id)——两批并存验证随行。
    ("N-02", _DAYS[0], "100.10", "b-aaaa"),
    ("N-02", _DAYS[1], "120.20", "b-aaaa"),
    ("N-11", _DAYS[0], "80.30", "b-bbbb"),
    ("N-11", _DAYS[1], "60.40", "b-bbbb"),
    ("N-06", _DAYS[0], "40.50", "b-bbbb"),
)


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
            for well_id, block, field in _WELLS:
                await conn.execute(
                    text("INSERT INTO agg.dim_well (well_id, block_name, field_name)"
                         " VALUES (:w, :b, :f) ON CONFLICT DO NOTHING"),
                    {"w": well_id, "b": block, "f": field},
                )
            for day in _DAYS:
                month = f"{day.year}-{day.month:02d}"
                quarter = f"{day.year}-Q{(day.month - 1) // 3 + 1}"
                await conn.execute(
                    text("INSERT INTO agg.dim_date (date, month, quarter)"
                         " VALUES (:d, :m, :q) ON CONFLICT DO NOTHING"),
                    {"d": day, "m": month, "q": quarter},
                )
            for well_id, day, oil, batch in _FACTS:
                await conn.execute(
                    text("INSERT INTO agg.fct_daily_metering (well_id, prod_date,"
                         " oil_output, liquid_output, oil_pressure, batch_id,"
                         " quality_flag) VALUES (:w, :d, :o, NULL, NULL, :b, NULL)"
                         " ON CONFLICT DO NOTHING"),
                    {"w": well_id, "d": day, "o": oil, "b": batch},
                )
    finally:
        await engine.dispose()


@pytest.fixture
async def specs() -> AsyncIterator[tuple[DatabaseSpec, ...]]:
    url = _isolated_url()
    await _ensure_test_database(url)
    await _load_fixture(url)
    yield (
        DatabaseSpec(
            name="primary", role="primary", driver="postgresql",
            host=url.host or "", port=url.port or 5432, database=url.database or "",
            user=url.username or "", password=url.password or "",
            pool_size=2, max_overflow=1,
        ),
    )


def _plan(*, ranking: bool, direction: str = DIRECTION_DESC) -> SqlPlan:
    return SqlPlan(
        metric_slot="日产油量", measure_column="oil_output", unit="吨",
        window=TimeWindow(start=date(2026, 9, 1), end=date(2026, 10, 1), label="上个月"),
        limit_effective=2 if ranking else 50, ranking=ranking, direction=direction,
        actor="aqiang",
    )


def test_ranking_desc_block_column_and_batch(specs: tuple[DatabaseSpec, ...]) -> None:
    """排名型：合计倒序＋LIMIT 2＋区块列在场＋批次随行（组内 MAX——行序首个）。"""
    from appv2.query import PgQueryExecutor

    result = PgQueryExecutor(specs).execute(_plan(ranking=True))
    assert [row["well_id"] for row in result.rows] == ["N-02", "N-11"]  # 220.30 > 140.70
    assert result.rows[0]["block_name"] == "渤南"
    assert float(result.rows[0]["日产油量合计（吨）"]) == pytest.approx(220.30, abs=0.01)
    assert result.batch_id == "b-aaaa"
    assert set(result.rows[0]) == {"well_id", "block_name", "日产油量合计（吨）"}


def test_ranking_asc_lowest_first(specs: tuple[DatabaseSpec, ...]) -> None:
    """升序（R1 二值分派）：最低合计首行——真库执行序与展示 SQL 同向。"""
    from appv2.query import PgQueryExecutor

    result = PgQueryExecutor(specs).execute(_plan(ranking=True, direction=DIRECTION_ASC))
    assert [row["well_id"] for row in result.rows] == ["N-06", "N-11"]  # 40.50 < 140.70


def test_detail_stable_order_and_batch_stripped(
    specs: tuple[DatabaseSpec, ...],
) -> None:
    """明细型：井×日稳定序＋区块列在场；batch 只随血缘卡——不进行集表卡。"""
    from appv2.query import PgQueryExecutor

    result = PgQueryExecutor(specs).execute(_plan(ranking=False))
    assert len(result.rows) == 5  # LIMIT 50 不截
    dates = [row["prod_date"] for row in result.rows]
    assert dates == sorted(dates)
    assert result.rows[0]["well_id"] == "N-02"
    assert result.rows[0]["block_name"] == "渤南"
    assert "batch_id" not in result.rows[0]
    assert result.batch_id == "b-aaaa"  # 行序首个非空 batch


def test_window_half_open(specs: tuple[DatabaseSpec, ...]) -> None:
    """窗口半开区间下推（[start, end)——越界行不进结果集）。"""
    from appv2.query import PgQueryExecutor

    plan = SqlPlan(
        metric_slot="日产油量", measure_column="oil_output", unit="吨",
        window=TimeWindow(start=date(2026, 9, 11), end=date(2026, 10, 1), label="窗口"),
        limit_effective=50, ranking=False, direction=DIRECTION_DESC, actor="aqiang",
    )
    result = PgQueryExecutor(specs).execute(plan)
    assert len(result.rows) == 2  # 仅 09-11 两行（N-02/N-11——N-06 无当日行）
    assert result.batch_id == "b-aaaa"
