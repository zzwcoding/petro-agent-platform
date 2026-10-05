"""domains.chat.query_store —— 问数链取数执行器（agg 星型读模型只读——M-06）。

边界（票面红线）：
- 99 册 §3 模块↔表映射「读（声明）」列：chat＝``agg.fct_daily_metering``/
  ``agg.dim_*`` 问数链 SELECT 唯一消费方（经 D3 安检＋行级注入）——本文件是
  唯一执行落点；链体只见注入缝（chains.ChainDeps.query_executor，B1）。
- agg 三表物理在主平台库（DP-04：数据面按 99 DDL 直写——ADR-0003 裁决 15），
  只读会话走 primary readonly（B3——只经 infra.db，不直建引擎、不落镜像）。
- agg 三表不建 ORM（读模型＝加工产物，DDL 真源＝Alembic 0014——wells 中台源
  表同款纪律：独立 MetaData Core 轻声明只服务 select 装配，不入 Base.metadata）。
- 行级注入：M-01 两步缝——``with_row_filter(actor, "agg.fct_daily_metering")``
  产 RowDomainScope（预埋期谓词恒空＝WHERE 恒真）→
  ``ConnectionManager.with_row_filter(stmt, predicates)`` 物理装配（99 §4.2
  冻结形状原样消费；真分权只换谓词生产实现，本文件零改动）。
- 只读语义：语句恒 SELECT＋LIMIT（计划由 N7.3 模板装配——零自由生成），会话
  走 readonly 只读守卫（「只读账号执行，生产库未动」——A1 行为规则 7）。
"""

from __future__ import annotations

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

from app.domains.chat import domain as d
from app.infra.db import ConnectionManager, with_row_filter

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
    Column("oil_output", Numeric(12, 2)),
    Column("liquid_output", Numeric(12, 2)),
    Column("oil_pressure", Numeric(6, 2)),
    Column("batch_id", String(64)),
    Column("quality_flag", String(16)),
    schema="agg",
)


def _measure_column(plan: d.QueryPlan) -> Any:
    """计划计量列 → Core 列（绑定白名单＝MEASURE_COLUMNS——模板装配已核）。"""
    return _FCT_DAILY_METERING.c[plan.measure_column]


class QueryStore:
    """问数取数执行器（纯读——无写出口；ranking/detail 两形同源 plan 装配）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def execute_plan(self, plan: d.QueryPlan) -> d.QueryResult:
        """执行查询计划（M-01 两步缝注入行级谓词；readonly 只读会话）。

        - 排名型：GROUP BY 井＋区块，合计倒序取前 N（LIMIT 收口值已收）；
        - 明细型：井×日粒度行，按日期＋井号稳定序，LIMIT 收口值收口；
        - 行级注入：谓词 AND 进语句（预埋期恒空——回执如实计数）；
        - batch_id＝结果行携带的批次水位（排名型取 MAX 聚合随行）。
        """
        stmt, predicates = self.build_statement_with_scope(plan)
        async with self._db.readonly() as session:
            rows = (await session.execute(stmt)).all()
        dict_rows = [dict(row._mapping) for row in rows]
        batch_id = next(
            (str(r["batch_id"]) for r in dict_rows if r.get("batch_id")), None
        )
        display_keys = {key for key, _title in _result_columns(plan)}
        for row in dict_rows:
            for key in [k for k in row if k not in display_keys]:
                row.pop(key)  # batch_id 只作批次水位随行（血缘卡④）——不进答案表卡
        return d.QueryResult(
            columns=_result_columns(plan),
            rows=dict_rows,
            batch_id=batch_id,
            row_filter_predicates=len(predicates),
        )

    def build_statement(self, plan: d.QueryPlan) -> Any:
        """语句装配（不含行级注入——注入由两步缝第二怕补并；测试观测面）。"""
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
            stmt = (
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
                .order_by(total.desc())
                .limit(plan.limit_effective)
            )
        else:
            stmt = (
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
        return stmt

    def build_statement_with_scope(
        self, plan: d.QueryPlan,
    ) -> tuple[Any, tuple[Any, ...]]:
        """两步缝全式（M-01——99 §4.2 冻结形状原样消费；测试/执行共用单源）：

            scope = with_row_filter(actor, "agg.fct_daily_metering")
            stmt  = ConnectionManager.with_row_filter(stmt, scope.predicates)
        """
        scope = with_row_filter(plan.actor, "agg.fct_daily_metering")
        stmt = ConnectionManager.with_row_filter(self.build_statement(plan), scope.predicates)
        return stmt, scope.predicates


def _result_columns(plan: d.QueryPlan) -> tuple[tuple[str, str], ...]:
    """answer 表卡列序（dataIndex, title——演示表卡同形；排名型带序号列）。"""
    if plan.ranking:
        return (
            ("well_id", "井号"),
            ("block_name", "区块"),
            (f"{plan.metric_slot}合计（{plan.unit}）", f"{plan.metric_slot}合计（{plan.unit}）"),
        )
    return (
        ("well_id", "井号"),
        ("block_name", "区块"),
        ("prod_date", "日期"),
        (f"{plan.metric_slot}（{plan.unit}）", f"{plan.metric_slot}（{plan.unit}）"),
    )
