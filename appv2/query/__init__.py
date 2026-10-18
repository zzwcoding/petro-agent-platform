"""appv2.query —— 问数六站链确定性引擎（V2-03；specs/modules.md query 卡公开接口）。

QueryEngine（validate＋run 两面）＝唯一公开行为面；QueryPlan/QueryOutcome
（六联合态）/PlanCheck＝specs/query.md 接口定义节定稿 schema（随本票定稿，
票面点名）；QueryExecutor/QueryResult＝SQL 执行缝（生产适配器走
appv2.infra.db 只读会话，测试＝CsvSnapshotExecutor 假执行器——题册绑定
CSV 快照在 appv2/query/fixtures/）；WatermarkFace/TimeWindow/SqlPlan＝
三内部形状（水位读面/半开时间窗/可执行计划）。

V1 六站链确定性行为移植（问数组 A~H 族逐族钉死）：三闸（新鲜度/行级/外表
越集审批）/新鲜度改绑/未绑定降级/缺参反问/越集审批/血缘卡五要素——闸序
一处有意修复＝外表越集审批先于新鲜度闸（Q11「interrupt 不可达」双重掩蔽
病灶治理，specs/query.md 行为约定 4 票面事项）。

边界（specs/modules.md）：依赖只许 appv2.infra 公开接口（时钟 B14）＋
appv2.knowledge 公开接口（未绑定降级 Evidence——query→knowledge 为
modules.md 登记的唯一互引例外）；不 import app.**（V1 逻辑以行为为准重
实现，禁止整文件搬运）；本包零 LLM 调用（N5 判型/路由不进本模块，
specs/query.md「不做什么」）。
"""

from appv2.query.domain import (
    ASKBACK_TIME_CHOICES,
    ASKBACK_TIME_QUESTION,
    DIRECTION_ASC,
    DIRECTION_DESC,
    EXTERNAL_TABLE_ALIASES,
    LINEAGE_KEY_CALIBER,
    LINEAGE_KEY_CLOSING,
    LINEAGE_KEY_FILTER,
    LINEAGE_KEY_PERMISSION,
    LINEAGE_KEY_SOURCE,
    LINEAGE_KEY_WATERMARK,
    OUTCOME_EXTERNAL_TABLE_APPROVAL,
    OUTCOME_FRESHNESS_BLOCK,
    OUTCOME_KINDS,
    OUTCOME_NEED_CLARIFY,
    OUTCOME_REFUSE,
    OUTCOME_ROWS,
    OUTCOME_UNBOUND_DEGRADE,
    PLAN_WINDOW_MAX_DAYS,
    QUERY_DEFAULT_LIMIT,
    QUERY_LIMIT_CAP,
    RECENT_TIME_WORDS,
    RELATIVE_TIME_WORDS,
    STAR_TABLES,
    WATERMARK_BATCH_PREFIX,
    WINDOW_TOTAL_SCOPE_NOTE,
    LineageLine,
    PlanCheck,
    QueryOutcome,
    QueryPlan,
    QueryResultColumn,
    SqlPlan,
    TimeWindow,
    build_extable_ask,
    build_query_plan,
    check_plan_window_bounds,
    detect_external_tables,
    effective_limit,
    is_ranking_question,
    lineage_filter_window_label,
    parse_ranking_direction,
    parse_row_limit,
    parse_time_window,
    render_plan_sql,
    resolve_askback_window,
)
from appv2.query.engine import QueryEngine, WaterlineLoader, WatermarkFace
from appv2.query.executor import (
    FIXTURE_CSV,
    AggRow,
    CsvSnapshotExecutor,
    QueryExecutor,
    QueryResult,
)
from appv2.query.pg_executor import PgQueryExecutor
from appv2.query.pg_waterline import freshness_judgment, production_waterline
from appv2.query.pg_wells import (
    production_data_wells,
    production_field_instances,
    production_well_roster,
)

__all__ = [
    "ASKBACK_TIME_CHOICES",
    "ASKBACK_TIME_QUESTION",
    "DIRECTION_ASC",
    "DIRECTION_DESC",
    "EXTERNAL_TABLE_ALIASES",
    "FIXTURE_CSV",
    "LINEAGE_KEY_CALIBER",
    "LINEAGE_KEY_CLOSING",
    "LINEAGE_KEY_FILTER",
    "LINEAGE_KEY_PERMISSION",
    "LINEAGE_KEY_SOURCE",
    "LINEAGE_KEY_WATERMARK",
    "OUTCOME_EXTERNAL_TABLE_APPROVAL",
    "OUTCOME_FRESHNESS_BLOCK",
    "OUTCOME_KINDS",
    "OUTCOME_NEED_CLARIFY",
    "OUTCOME_REFUSE",
    "OUTCOME_ROWS",
    "OUTCOME_UNBOUND_DEGRADE",
    "PLAN_WINDOW_MAX_DAYS",
    "QUERY_DEFAULT_LIMIT",
    "QUERY_LIMIT_CAP",
    "RECENT_TIME_WORDS",
    "RELATIVE_TIME_WORDS",
    "STAR_TABLES",
    "WATERMARK_BATCH_PREFIX",
    "WINDOW_TOTAL_SCOPE_NOTE",
    "AggRow",
    "CsvSnapshotExecutor",
    "LineageLine",
    "PgQueryExecutor",
    "PlanCheck",
    "QueryEngine",
    "QueryExecutor",
    "QueryOutcome",
    "QueryPlan",
    "QueryResult",
    "QueryResultColumn",
    "SqlPlan",
    "TimeWindow",
    "WaterlineLoader",
    "WatermarkFace",
    "build_extable_ask",
    "build_query_plan",
    "check_plan_window_bounds",
    "detect_external_tables",
    "effective_limit",
    "freshness_judgment",
    "is_ranking_question",
    "lineage_filter_window_label",
    "parse_ranking_direction",
    "parse_row_limit",
    "parse_time_window",
    "production_data_wells",
    "production_field_instances",
    "production_waterline",
    "production_well_roster",
    "render_plan_sql",
    "resolve_askback_window",
]
