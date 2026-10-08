"""query.executor —— SQL 执行缝与题册绑定快照假执行器（specs/modules.md query 卡）。

Seam（specs/modules.md query 卡「Seam 与测试」）：QueryExecutor＝「SQL 执行这一
可替换面」——生产适配器（只读账号＋白名单 Schema 走 appv2.infra.db，INV-2/INV-3）
随接线票落位；本文件另载测试适配器 CsvSnapshotExecutor（specs/query.md「Seam
与测试」点名的假执行器——fixture 行集）。

CsvSnapshotExecutor＝agg 三表查询语义在题册绑定 CSV 快照上的确定性投影：
- 明细型：井×日粒度行，ORDER BY prod_date, well_id（V1 注册合同值），LIMIT 收口；
- 排名型：GROUP BY 井合计，ORDER BY 合计随方向二值分派（并列以井号定序——
  快照适配器的确定性缝，不改合同值），LIMIT 收口；
- 数值 Decimal 承载（agg DDL Numeric(10,2) 精度——V1 query_store 同精度口径）。

fixture＝题册绑定 CSV 快照（appv2/query/fixtures/oil_production_daily_sample.csv），
抽样规则（机械可从真源重现，行值逐字零改动）：
- 真源：~/Downloads/fieldforge/out-tpa/oil_production_daily.csv（31,390 行——
  eval/answers/问数组-题目与答案.md「数据真源与版本绑定」节钉死的进料）；
- 行集＝{r | 2025-09-01 ≤ r.prod_date ≤ 2025-12-31}（题册「去年窗」全量
  122 天×86 井＝10,492 行——排名合计与明细窗数值的判分依据全在此窗）
  ∪ {r | r.prod_date == 2026-01-01}（题册「今年窗」首日 86 行——改绑注记题
  首 50 行判分依据）；合计 10,578 行、九列名逐字（含未绑定列 water_cut/
  plan_output——绑定判定归 MEASURE_COLUMNS，快照不做列裁剪）。

快照与 agg 星型读模型的已知差异（假执行器适配边界，零业务发明）：
- 无 dim_well 区块列（CSV 快照无此数据）——表卡省「区块」列；展示 SQL 模板
  （render_plan_sql）仍全形（生产执行缝落 agg.dim_well）；
- 无 batch_id 列——QueryResult.batch_id 恒 None（血缘④不带批次前缀，水位
  日期由水位读缝供给）。

只读纪律（INV-2）：行集载入即冻结为不可变 tuple，本类零写路径——execute 之外
只有 records() 只读投影。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from appv2.query.domain import DIRECTION_ASC, QueryResultColumn, SqlPlan

# 题册绑定 CSV 快照（随本票入仓——抽样规则见模块 docstring）。
FIXTURE_CSV = Path(__file__).resolve().parent / "fixtures" / "oil_production_daily_sample.csv"

# 台账指标槽位 → 快照数值列（V1 MEASURE_COLUMNS 冻结三绑定的物理列名——
# 判定真源单点在 appv2.knowledge，本表只做「绑定列名→CSV 列名」的取数投影，
# 值域即三绑定列，零第二份绑定目录）。
_MEASURE_TO_COLUMN: dict[str, str] = {
    "oil_output": "oil_output",
    "liquid_output": "liquid_output",
    "oil_pressure": "oil_pressure",
}

_DECIMAL_COLUMNS: tuple[str, ...] = (
    "oil_output", "liquid_output", "water_cut", "plan_output", "open_days", "oil_pressure",
)


@dataclass(frozen=True, slots=True)
class AggRow:
    """oil_production_daily 行投影（九列逐字——快照不可变行）。"""

    well_id: str
    prod_date: date
    oil_output: Decimal | None
    liquid_output: Decimal | None
    water_cut: Decimal | None
    plan_output: Decimal | None
    open_days: Decimal | None
    oil_pressure: Decimal | None
    report_shift: str


class QueryResult:
    """执行结果（执行缝投影——列序＋行集＋批次水位；血缘卡④/表卡消费形）。"""

    __slots__ = ("batch_id", "columns", "rows")

    def __init__(
        self,
        columns: tuple[QueryResultColumn, ...],
        rows: tuple[dict[str, Any], ...],
        batch_id: str | None = None,
    ) -> None:
        self.columns = columns
        self.rows = rows
        self.batch_id = batch_id


class QueryExecutor(Protocol):
    """SQL 执行缝（specs/modules.md query 卡——可替换面；生产适配器走 infra.db 只读）。"""

    def execute(self, plan: SqlPlan) -> QueryResult:
        """执行可执行计划（只读——SELECT＋LIMIT 语义；INV-2 零写副作用）。"""


class CsvSnapshotExecutor:
    """题册绑定快照假执行器（specs/query.md「Seam 与测试」点名的假执行器适配）。

    agg 三表查询语义在 CSV 快照上的确定性投影（语义对位见模块 docstring）；
    构造即载入冻结（INV-2——快照零写路径）。
    """

    def __init__(self, csv_path: Path = FIXTURE_CSV) -> None:
        self._rows: tuple[AggRow, ...] = tuple(self._load(csv_path))

    @staticmethod
    def _load(csv_path: Path) -> list[AggRow]:
        def dec(raw: dict[str, str], key: str) -> Decimal | None:
            value = raw[key]
            return Decimal(value) if value else None

        rows: list[AggRow] = []
        with csv_path.open(newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                rows.append(
                    AggRow(
                        well_id=raw["well_id"],
                        prod_date=date.fromisoformat(raw["prod_date"]),
                        oil_output=dec(raw, "oil_output"),
                        liquid_output=dec(raw, "liquid_output"),
                        water_cut=dec(raw, "water_cut"),
                        plan_output=dec(raw, "plan_output"),
                        open_days=dec(raw, "open_days"),
                        oil_pressure=dec(raw, "oil_pressure"),
                        report_shift=raw["report_shift"],
                    )
                )
        return rows

    def records(self) -> tuple[AggRow, ...]:
        """快照只读投影（INV-2 断言观测面——不可变 tuple 原样返回）。"""
        return self._rows

    def execute(self, plan: SqlPlan) -> QueryResult:
        """执行可执行计划（明细/排名两形——V1 QueryStore.build_statement 同语义）。"""
        column = _MEASURE_TO_COLUMN[plan.measure_column]
        start, end = plan.window.start, plan.window.end
        in_window = [row for row in self._rows if start <= row.prod_date < end]
        if plan.ranking:
            return self._execute_ranking(plan, column, in_window)
        return self._execute_detail(plan, column, in_window)

    def _execute_detail(
        self, plan: SqlPlan, column: str, rows: list[AggRow]
    ) -> QueryResult:
        """明细型：井×日粒度行，ORDER BY prod_date, well_id（V1 注册合同值）。"""
        measure_col = f"{plan.metric_slot}（{plan.unit}）"
        ordered = sorted(rows, key=lambda row: (row.prod_date, row.well_id))
        kept = ordered[: plan.limit_effective]
        out_rows: list[dict[str, Any]] = []
        for row in kept:
            out_rows.append({
                "well_id": row.well_id,
                "prod_date": row.prod_date,
                measure_col: getattr(row, column),
            })
        columns: tuple[QueryResultColumn, ...] = (
            ("well_id", "井号"),
            ("prod_date", "日期"),
            (measure_col, measure_col),
        )
        return QueryResult(columns=columns, rows=tuple(out_rows))

    def _execute_ranking(
        self, plan: SqlPlan, column: str, rows: list[AggRow]
    ) -> QueryResult:
        """排名型：GROUP BY 井合计，方向二值分派（并列以井号定序——确定性缝）。"""
        total_col = f"{plan.metric_slot}合计（{plan.unit}）"
        sums: dict[str, Decimal] = {}
        for row in rows:
            value = getattr(row, column)
            if value is None:
                continue
            sums[row.well_id] = sums.get(row.well_id, Decimal("0")) + value
        # 并列以井号定序（稳定两段排序——先井号后合计方向，合同值不改）。
        ordered = sorted(sums.items(), key=lambda item: item[0])
        ordered.sort(key=lambda item: item[1], reverse=plan.direction != DIRECTION_ASC)
        kept = ordered[: plan.limit_effective]
        out_rows = [
            {"well_id": well_id, total_col: total} for well_id, total in kept
        ]
        columns: tuple[QueryResultColumn, ...] = (
            ("well_id", "井号"),
            (total_col, total_col),
        )
        return QueryResult(columns=columns, rows=tuple(out_rows))
