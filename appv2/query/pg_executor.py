"""query.pg_executor —— PgQueryExecutor（agg 星型读模型生产执行器——V2-19，
specs/modules.md query 卡外部依赖「PG agg 三表＋湖表（只读账号）」的落位件）。

specs/query.md「Seam 与测试」：生产适配器（只读账号＋白名单 Schema 走
appv2.infra.db，INV-2/INV-3）——本文件落位后 CsvSnapshotExecutor 退役至
测试位（fixture 行集）。真 SQL＝agg 星型三表 join（A1 解释链②冻结——99 册
§2.12/D6 star_model 合同值）：事实表组合 PK well_id+prod_date 挂两维 PK 连；
dim_well 区块列（block_name）随行；batch_id 回血缘④（数据截至批次——明细型
随行首个非空、排名型组内 MAX 聚合，V1 query_store 同口径），剥离后只随血缘卡
不进答案表卡。

同步缝桥（QueryExecutor.execute 为 specs/modules.md query 卡同步签名；DB 面经
infra.db ConnectionManager 为异步会话）：与 knowledge.pg_store._run_sync 同款
两态桥——无运行环本线程 asyncio.run 直跑；已在运行环内落专用单线程池另起环。
逐调用新建专用 ConnectionManager 的理由：连接池绑定创建它的事件循环（asyncpg
连接不可跨环复用）——随调用建/拆（finally dispose）保证池连接与当次环同源；
会话获取仍唯一经 infra.db（B3 红线不破），readonly() 只读守卫恒挂（INV-2/
「只读账号执行，生产库未动」）。

行级注入（M-01 两步缝——99 §4.2 冻结形状原样消费）：
    scope = with_row_filter(actor, "agg.fct_daily_metering")
    stmt  = ConnectionManager.with_row_filter(stmt, scope.predicates)
预埋期谓词恒空＝WHERE 恒真；真分权只换谓词生产实现，本文件零改动。

表访问＝Core 轻声明（独立 MetaData——读模型＝加工产物，DDL 真源＝Alembic
0014，不入 ORM Base.metadata；V1 agg 同款纪律）。
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from sqlalchemy import (
    Column,
    Date,
    MetaData,
    Numeric,
    String,
    Table,
    func,
    select,
)

from appv2.infra.db import ConnectionManager, DatabaseSpec, with_row_filter
from appv2.query.domain import (
    DIRECTION_ASC,
    QueryResultColumn,
    SqlPlan,
)
from appv2.query.executor import QueryResult


def _run_sync[T](awaitable: Coroutine[Any, Any, T]) -> T:
    """同步缝→异步 DB 桥（无环本线程直跑；有环专用线程另起环——见模块 docstring）。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(awaitable)).result()


# ---------- agg 星型读模型轻声明（schema="agg"——DDL 真源＝Alembic 0014） ----------

_AGG_META = MetaData()

_DIM_WELL = Table(
    "dim_well", _AGG_META,
    Column("well_id", String(8)),
    Column("block_name", String(16)),
    Column("field_name", String(32)),
    schema="agg",
)
_DIM_DATE = Table(
    "dim_date", _AGG_META,
    Column("date", Date),
    Column("month", String(7)),
    Column("quarter", String(7)),
    schema="agg",
)
_FCT_DAILY_METERING = Table(
    "fct_daily_metering", _AGG_META,
    Column("well_id", String(8)),
    Column("prod_date", Date),
    Column("oil_output", Numeric(10, 2)),  # 精度照 DDL 真源 0014（V1 同注——R3 对账）
    Column("liquid_output", Numeric(10, 2)),
    Column("oil_pressure", Numeric(6, 2)),
    Column("batch_id", String(64)),
    Column("quality_flag", String(16)),
    schema="agg",
)


def _measure_column(plan: SqlPlan) -> Any:
    """计划计量列 → Core 列（绑定白名单＝MEASURE_COLUMNS——模板装配已核）。"""
    return _FCT_DAILY_METERING.c[plan.measure_column]


def _result_columns(plan: SqlPlan) -> tuple[QueryResultColumn, ...]:
    """答案表卡列序（dataIndex, title——dim_well 区块列随行；排名型合计列）。"""
    if plan.ranking:
        total = f"{plan.metric_slot}合计（{plan.unit}）"
        return (
            ("well_id", "井号"),
            ("block_name", "区块"),
            (total, total),
        )
    measure = f"{plan.metric_slot}（{plan.unit}）"
    return (
        ("well_id", "井号"),
        ("block_name", "区块"),
        ("prod_date", "日期"),
        (measure, measure),
    )


class PgQueryExecutor:
    """agg 星型真 SQL 执行器（纯读——无写出口；ranking/detail 两形同源装配）。"""

    def __init__(self, specs: Sequence[DatabaseSpec]) -> None:
        self._specs = tuple(specs)

    def execute(self, plan: SqlPlan) -> QueryResult:
        """执行可执行计划（只读——SELECT＋LIMIT 语义；INV-2 零写副作用）。"""
        return _run_sync(self._execute(plan))

    async def _execute(self, plan: SqlPlan) -> QueryResult:
        stmt, _predicates = self._statement_with_scope(plan)
        db = ConnectionManager(self._specs)
        try:
            async with db.readonly() as session:
                rows = (await session.execute(stmt)).all()
        finally:
            await db.dispose()
        dict_rows = [dict(row._mapping) for row in rows]
        # batch_id＝结果行携带的批次水位（排名型组内 MAX 随行）——回血缘④，
        # 剥离后不进答案表卡（V1 query_store 同口径）。
        batch_id = next(
            (str(row["batch_id"]) for row in dict_rows if row.get("batch_id")), None
        )
        display_keys = {key for key, _title in _result_columns(plan)}
        for row in dict_rows:
            for key in [k for k in row if k not in display_keys]:
                row.pop(key)
        return QueryResult(
            columns=_result_columns(plan),
            rows=tuple(dict_rows),
            batch_id=batch_id,
        )

    # ---------- 语句装配（agg 星型 join 即注册合同值——A1 解释链②） ----------

    def _statement(self, plan: SqlPlan) -> Any:
        """语句装配（不含行级注入——注入由两步缝第二步补并；测试观测面）。"""
        measure = _measure_column(plan)
        joins = [
            (_DIM_WELL, _DIM_WELL.c.well_id == _FCT_DAILY_METERING.c.well_id),
            (_DIM_DATE, _DIM_DATE.c.date == _FCT_DAILY_METERING.c.prod_date),
        ]
        bounds = (
            _FCT_DAILY_METERING.c.prod_date >= plan.window.start,
            _FCT_DAILY_METERING.c.prod_date < plan.window.end,
        )
        if plan.ranking:
            total = func.sum(measure).label(f"{plan.metric_slot}合计（{plan.unit}）")
            batch_max = func.max(_FCT_DAILY_METERING.c.batch_id).label("batch_id")
            # R1：方向白名单二值分派（asc/desc）——「最低/最小/最少」升序，默认降序。
            order = total.asc() if plan.direction == DIRECTION_ASC else total.desc()
            return (
                select(
                    _DIM_WELL.c.well_id.label("well_id"),
                    _DIM_WELL.c.block_name.label("block_name"),
                    total,
                    batch_max,
                )
                .join(*joins[0])
                .join(*joins[1])
                .where(*bounds)
                .group_by(_DIM_WELL.c.well_id, _DIM_WELL.c.block_name)
                .order_by(order)
                .limit(plan.limit_effective)
            )
        return (
            select(
                _FCT_DAILY_METERING.c.well_id.label("well_id"),
                _DIM_WELL.c.block_name.label("block_name"),
                _FCT_DAILY_METERING.c.prod_date.label("prod_date"),
                measure.label(f"{plan.metric_slot}（{plan.unit}）"),
                _FCT_DAILY_METERING.c.batch_id.label("batch_id"),
            )
            .join(*joins[0])
            .join(*joins[1])
            .where(*bounds)
            .order_by(_FCT_DAILY_METERING.c.prod_date, _FCT_DAILY_METERING.c.well_id)
            .limit(plan.limit_effective)
        )

    def _statement_with_scope(self, plan: SqlPlan) -> tuple[Any, tuple[Any, ...]]:
        """两步缝全式（M-01——99 §4.2 冻结形状原样消费；测试/执行共用单源）。"""
        scope = with_row_filter(plan.actor, "agg.fct_daily_metering")
        stmt = ConnectionManager.with_row_filter(self._statement(plan), scope.predicates)
        return stmt, scope.predicates
