"""V2-03 query 六站链验收——specs/query.md「验收测试」表十条逐条落测（数值钉死）。

十条对应（票面验收表，1:1 同名；问数组关键数值判分唯一依据）：
- detail_window_50：去年窗明细 50 行截断＝2025-09-01 当日前 50 井
  （N-01～N-27＋X-01～X-23），首行 N-01 21.16 吨／第 50 行 X-23 34.21 吨，
  LIMIT 收口注记「默认 50」在场，零改绑注记（窗全在水位前）。
- rebind_notice：今年窗首行 N-01 36.97 方＋改绑注记（水位 2026-08-31 早于
  窗上沿——按最近可用日改绑）＋血缘④=2026-08-31。
- ranking_values：排名降序 Z-16 5839.6 吨；升序「最低两口」＝Z-22 1784.7、
  N-09 1851.5（升序即此序）；液量冠军 N-15 8824.4 方（与油量冠军 Z-16 不同井）。
- explicit_limit_30：「排名前 30」→恰 30 行（默认 50 不顶替），首行 Z-16。
- freshness_blocks：本月／近 7 天／默认窗三形态→freshness_block＋水位
  2026-08-31＋窗标签＋默认窗标注（is_default）齐、零数值行。
- vague_time_clarify：「最近」→need_clarify 三选一（近 3 天/近 30 天/本月至今，
  askback 合同原文），零数值；resume 补参面 resolve_askback_window 确定性落窗。
- unbound_degrade：含水率／配产量在册未绑定→降级＋Evidence 依据
  （binding_state=unbound、台账行 id 203/204），零数值。
- external_table_ask：「井位台账」外表别名进选表命中集→external_table_approval
  可达（Q11 病灶修复点——V1 闸序 N7.4a 先于 N7.4c 双重掩蔽，V2 越集审批
  先于新鲜度闸），ASK 素材齐（approval_id/scene/title/reason/impact），不出数。
- metric_switch_blocked：计划指标槽不在问句指标候选集（油压↔日产油量替换）
  →validate 拒（FX-13 一致性闸），原计划同候选集过。
- readonly_inv2：六联合态全形态跑遍后执行器快照深比对零变＋执行面无写方法
  （INV-2 只读断言）；越界窗/未注册指标→refuse 联合态（六态最小复现随本条收口）。

fixture＝题册绑定 CSV 快照（appv2/query/fixtures/oil_production_daily_sample.csv，
10,578 行＝去年窗全量 122 天×86 井 10,492 行＋今年窗首日 2026-01-01 86 行，
逐字取自 ~/Downloads/fieldforge/out-tpa/oil_production_daily.csv 真产物，
行值零改动）；SQL 执行面走假执行器 seam（CsvSnapshotExecutor——agg 三表语义
在快照上的确定性投影）。台账面＝问数组台账态快照（appv2.knowledge 公开接口
——query→knowledge 为 modules.md 登记唯一互引例外）。时钟注入固定执行日
2026-10-08（题册窗口锚定表执行月），水位注入 2026-08-31（题册版本绑定声明）。
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot
from appv2.query import (
    ASKBACK_TIME_CHOICES,
    DIRECTION_DESC,
    LINEAGE_KEY_CLOSING,
    LINEAGE_KEY_FILTER,
    LINEAGE_KEY_WATERMARK,
    OUTCOME_EXTERNAL_TABLE_APPROVAL,
    OUTCOME_FRESHNESS_BLOCK,
    OUTCOME_NEED_CLARIFY,
    OUTCOME_REFUSE,
    OUTCOME_ROWS,
    OUTCOME_UNBOUND_DEGRADE,
    CsvSnapshotExecutor,
    PgQueryExecutor,
    QueryEngine,
    QueryOutcome,
    QueryPlan,
    QueryResult,
    SqlPlan,
    TimeWindow,
    WatermarkFace,
    build_query_plan,
    resolve_askback_window,
)
from appv2.tools import (
    CATEGORY_REFUSED,
    DATA_QUERY,
    FakeKnowledgeStore,
    FakeQueryEngine,
    FakeRetrievalEngine,
    ToolContext,
    ToolRegistry,
)

# 执行日钉 2026-10-08（题册窗口锚定表执行月；水位 2026-08-31＝题册版本绑定）。
TODAY = date(2026, 10, 8)
WATERMARK = date(2026, 8, 31)

OIL_COL = "日产油量（吨）"
OIL_TOTAL_COL = "日产油量合计（吨）"
LIQ_COL = "日产液量（方）"
LIQ_TOTAL_COL = "日产液量合计（方）"

# 题册判分口径（问数组「关键数值」节——判分唯一依据）：窗合计数值按 ±0.1 钉值
# （题册数值＝脚本自 CSV 复核的 1 位小数显示口径；执行器合计按 agg Numeric(10,2)
# 精度承载 2 位小数精确值——单行明细值不受此影响，逐字相等）。
PIN_TOLERANCE = Decimal("0.1")


def _assert_pinned(actual: Decimal, pinned: str) -> None:
    assert abs(actual - Decimal(pinned)) <= PIN_TOLERANCE, (
        f"钉值 {pinned} 越界：实得 {actual}"
    )


def _engine() -> QueryEngine:
    return QueryEngine(
        knowledge=InMemoryKnowledgeStore(question_array_snapshot(), today=TODAY),
        executor=CsvSnapshotExecutor(),
        waterline=lambda: WatermarkFace(
            data_date=WATERMARK, promise="T-1", tag="落后 38 天（超期）",
        ),
        today=lambda: TODAY,
    )


def _plan(metric_slot: str, question: str) -> QueryPlan:
    return build_query_plan(metric_slot=metric_slot, question=question, today=TODAY)


# ---------- 验收①：去年窗明细 50 行截断——首行 N-01 21.16／第 50 行 X-23 34.21 ----------


def test_detail_window_50() -> None:
    outcome = _engine().run(_plan("日产油量", "去年各井每天的日产油量是多少？"))
    assert outcome.kind == OUTCOME_ROWS
    assert outcome.rows is not None
    assert len(outcome.rows) == 50  # 窗内实有 10,492 行——LIMIT 默认 50 截断
    # 首 50 行＝2025-09-01 当日按井号序前 50 井（无 09-02 及以后的行混入）。
    assert all(row["prod_date"] == date(2025, 9, 1) for row in outcome.rows)
    assert outcome.rows[0]["well_id"] == "N-01"
    assert outcome.rows[0][OIL_COL] == Decimal("21.16")
    assert outcome.rows[49]["well_id"] == "X-23"
    assert outcome.rows[49][OIL_COL] == Decimal("34.21")
    # 截断收口注记（F14 两态：没写条数→默认 50 并标注「默认」）。
    assert outcome.lineage is not None
    closing = next(line for line in outcome.lineage if line.key == LINEAGE_KEY_CLOSING)
    assert "LIMIT 50" in closing.value
    assert "默认" in closing.value
    # 窗全在水位前——零改绑注记。
    assert outcome.rebind_notice is None


# ---------- 验收②：今年窗改绑注记——首行 N-01 36.97 方＋血缘④=2026-08-31 ----------


def test_rebind_notice() -> None:
    outcome = _engine().run(_plan("日产液量", "今年各井的日产液量按天列出来"))
    assert outcome.kind == OUTCOME_ROWS
    assert outcome.rows is not None
    assert len(outcome.rows) == 50
    assert outcome.rows[0]["well_id"] == "N-01"
    assert outcome.rows[0]["prod_date"] == date(2026, 1, 1)
    assert outcome.rows[0][LIQ_COL] == Decimal("36.97")
    # 改绑注记在位：水位 2026-08-31 早于窗上沿——按最近可用日改绑出数。
    assert outcome.rebind_notice is not None
    assert "2026-08-31" in outcome.rebind_notice
    assert "改绑" in outcome.rebind_notice
    assert "不冒充新数据" in outcome.rebind_notice
    # 血缘④数据截至批次＝2026-08-31。
    assert outcome.lineage is not None
    watermark = next(line for line in outcome.lineage if line.key == LINEAGE_KEY_WATERMARK)
    assert "2026-08-31" in watermark.value


# ---------- 验收③：排名三向数值——降序 Z-16／升序末两位 Z-22、N-09／液量 N-15 ----------


def test_ranking_values() -> None:
    engine = _engine()
    # 降序：去年日产油量最高→Z-16 5839.6 吨（全窗合计，非全年 16723.6）。
    high = engine.run(_plan("日产油量", "去年日产油量最高的井是哪口？"))
    assert high.kind == OUTCOME_ROWS
    assert high.rows is not None
    assert high.rows[0]["well_id"] == "Z-16"
    _assert_pinned(high.rows[0][OIL_TOTAL_COL], "5839.6")
    # 升序：「最低的两口井」→asc 方向＋「两口」显式条数 2——Z-22 1784.7、N-09 1851.5。
    low = engine.run(_plan("日产油量", "去年日产油量最低的两口井是哪两口？"))
    assert low.kind == OUTCOME_ROWS
    assert low.rows is not None
    assert [row["well_id"] for row in low.rows] == ["Z-22", "N-09"]
    _assert_pinned(low.rows[0][OIL_TOTAL_COL], "1784.7")
    _assert_pinned(low.rows[1][OIL_TOTAL_COL], "1851.5")
    # 液量：冠军与油量不同井——N-15 8824.4 方。
    liquid = engine.run(_plan("日产液量", "去年日产液量最高的井是哪口？"))
    assert liquid.kind == OUTCOME_ROWS
    assert liquid.rows is not None
    assert liquid.rows[0]["well_id"] == "N-15"
    _assert_pinned(liquid.rows[0][LIQ_TOTAL_COL], "8824.4")


# ---------- 验收④：显式条数「前 30」→恰 30 行（默认 50 不顶替） ----------


def test_explicit_limit_30() -> None:
    plan = _plan("日产油量", "去年日产油量排名前 30")
    assert plan.limit == 30  # 问句显式条数进计划（与默认 50 可区分）
    outcome = _engine().run(plan)
    assert outcome.kind == OUTCOME_ROWS
    assert outcome.rows is not None
    assert len(outcome.rows) == 30  # 86 井 > 30——显式条数生效，恰 30 行
    assert outcome.rows[0]["well_id"] == "Z-16"
    _assert_pinned(outcome.rows[0][OIL_TOTAL_COL], "5839.6")
    assert outcome.lineage is not None
    closing = next(line for line in outcome.lineage if line.key == LINEAGE_KEY_CLOSING)
    assert "问句显式条数 30" in closing.value


# ---------- 验收⑤：本月／近 7 天／默认窗三形态→freshness_block＋标注齐、零数值 ----------


def test_freshness_blocks() -> None:
    engine = _engine()
    # 本月：窗 2026-10-01～→整体晚于水位 2026-08-31——拦停。
    month = engine.run(_plan("日产油量", "本月各井日产油量是多少？"))
    assert month.kind == OUTCOME_FRESHNESS_BLOCK
    assert month.watermark_date == WATERMARK
    assert month.window_label == "本月至今"
    assert month.is_default is False
    assert month.message is not None and "2026-08-31" in month.message
    assert month.rows is None  # 零数值——不返回空数冒充
    # 近 7 天：窗标签「近 7 天」→拦停。
    week = engine.run(_plan("日产液量", "近 7 天各井日产液量是多少？"))
    assert week.kind == OUTCOME_FRESHNESS_BLOCK
    assert week.watermark_date == WATERMARK
    assert week.window_label == "近 7 天"
    assert week.rows is None
    # 默认窗：无时间词→「最近 30 天（默认）」＋默认窗标注可见（is_default）。
    default = engine.run(_plan("日产油量", "各井日产油量排名"))
    assert default.kind == OUTCOME_FRESHNESS_BLOCK
    assert default.window_label == "最近 30 天（默认）"
    assert default.is_default is True
    assert default.rows is None


# ---------- 验收⑥：「最近」→need_clarify 三选一（零数值） ----------


def test_vague_time_clarify() -> None:
    outcome = _engine().run(_plan("日产油量", "最近各井日产油量怎么样？"))
    assert outcome.kind == OUTCOME_NEED_CLARIFY
    assert outcome.choices == ASKBACK_TIME_CHOICES
    assert len(outcome.choices or ()) == 3
    assert outcome.clarify_question is not None
    assert "最近" in outcome.clarify_question
    assert "① 近 3 天 ② 近 30 天 ③ 本月至今" in outcome.clarify_question
    assert outcome.rows is None  # 不出数
    # resume 补参面：选项→时间窗确定性落点（未知选项 None 不猜）。
    window = resolve_askback_window("近 30 天", today=TODAY)
    assert window is not None
    assert (window.start, window.end) == (date(2026, 9, 8), TODAY)
    assert resolve_askback_window("随便", today=TODAY) is None


# ---------- 验收⑦：含水率／配产量在册未绑定→unbound_degrade＋Evidence 依据 ----------


def test_unbound_degrade() -> None:
    engine = _engine()
    for slot, element_id in (("含水率", "203"), ("配产量", "204")):
        outcome = engine.run(_plan(slot, f"去年各井{slot}是多少？"))
        assert outcome.kind == OUTCOME_UNBOUND_DEGRADE
        assert outcome.evidence is not None
        assert outcome.evidence.element_id == element_id
        assert outcome.evidence.binding_state == "unbound"
        # 依据＝Evidence 依据在场（源列在湖表、agg 读模型未落该列——如实说明）。
        assert outcome.basis is not None
        assert "agg" in outcome.basis
        assert outcome.rows is None  # 零数值——不可从别处抄数充数


# ---------- 验收⑧：「井位台账」别名进选表命中集→external_table_approval 可达 ----------


def test_external_table_ask() -> None:
    plan = _plan("日产油量", "井位台账里日产油量最高的井是哪口？")
    # Q11 病灶修复点：外表别名「井位台账」→erp_well_register 进越集比对触发源。
    assert plan.external_tables == ("erp_well_register",)
    outcome = _engine().run(plan)
    assert outcome.kind == OUTCOME_EXTERNAL_TABLE_APPROVAL
    assert outcome.external_tables == ("erp_well_register",)
    # ASK 素材齐（审批卡合同形状）。
    ask = outcome.ask
    assert ask is not None
    assert ask["scene"] == "extable"
    assert ask["title"] == "外表引用审批"
    assert "erp_well_register" in str(ask["reason"])
    assert "越集" in str(ask["reason"]) or "命中集之外" in str(ask["reason"])
    assert "批准" in str(ask["impact"])
    assert str(ask["approval_id"]).startswith("APP-")
    assert outcome.rows is None  # 挂起等审批——不直接出数


# ---------- V2-52/P-051b 审查④清偿（S4）：真引擎放行态闸函数级直钉 ----------


def test_external_table_approved_state_direct() -> None:
    """放行态直钉（真 QueryEngine——非替身旁路）：已批表全放行→出数不再挂
    审批（续跑通道的引擎侧权威闸语义）；零放行→审批帧（既有语义）；部分
    放行→审批只挂未批子集。窗钉历史区间（显式窗——默认窗会先撞新鲜度闸，
    混淆本钉的放行态语义面）。"""
    plan = replace(
        _plan("日产油量", "井位台账里日产油量最高的井是哪口？"),
        window_start=date(2025, 9, 1),
        window_end=date(2025, 9, 3),
    )
    assert plan.external_tables == ("erp_well_register",)
    # 全放行→出数（批准后重执行零二次挂审批——Q14W 数-察2 骨架收口形根治）。
    approved = _engine().run(plan, approved_tables=("erp_well_register",))
    assert approved.kind == OUTCOME_ROWS
    assert approved.rows is not None and approved.rows
    # 零放行→审批帧（未批照挂）。
    bare = _engine().run(plan)
    assert bare.kind == OUTCOME_EXTERNAL_TABLE_APPROVAL
    assert bare.external_tables == ("erp_well_register",)
    # 部分放行→审批只携未批子集（放行态逐表比对——engine run 放行态缝语义）。
    widened = replace(
        plan, external_tables=("erp_well_register", "erp_well_monthly")
    )
    partial = _engine().run(widened, approved_tables=("erp_well_register",))
    assert partial.kind == OUTCOME_EXTERNAL_TABLE_APPROVAL
    assert partial.external_tables == ("erp_well_monthly",)


# ---------- V2-22：血缘③窗标签空串填实（真模型草案不带 window_label 三形态） ----------


def test_lineage_filter_label_filled_for_bare_drafts() -> None:
    """V2-22 钉测（P-013 疑点 4 裁决）：真模型计划草案不带 window_label（schema
    可选键）时血缘③/拦停话术不得渲染空标签——显式窗/默认窗/改绑窗三形态按
    半开区间含端日期填实（不猜词面——词面归规划步），「时间＝ 」空标签形状绝迹。"""
    engine = _engine()

    def lineage_filter(outcome):
        assert outcome.lineage is not None
        return next(
            line for line in outcome.lineage if line.key == LINEAGE_KEY_FILTER
        ).value

    # 显式窗：草案只带日期无标签——「时间＝2025-09-01～2025-09-02」填实。
    explicit = engine.run(
        QueryPlan(
            metric_slot="日产油量",
            window_start=date(2025, 9, 1),
            window_end=date(2025, 9, 3),
            limit=None,
            ranking=False,
        )
    )
    assert explicit.kind == OUTCOME_ROWS
    line = lineage_filter(explicit)
    assert "时间＝2025-09-01～2025-09-02" in line
    assert "[2025-09-01, 2025-09-03)" in line
    assert "时间＝ " not in line  # 空标签形状（标签位空串带多余空格）绝迹
    # 默认窗：is_default=True 无标签——填实＋「默认窗」标注随 is_default 在场。
    default = engine.run(
        QueryPlan(
            metric_slot="日产油量",
            window_start=date(2026, 1, 1),
            window_end=date(2026, 1, 31),
            limit=None,
            ranking=False,
            is_default=True,
        )
    )
    assert default.kind == OUTCOME_ROWS
    line = lineage_filter(default)
    assert "时间＝2026-01-01～2026-01-30" in line
    assert "默认窗" in line
    assert "时间＝ " not in line
    # 改绑窗：窗跨水位改绑后标签仍非空（改绑 rebuild 不丢填实标签）。
    rebind = engine.run(
        QueryPlan(
            metric_slot="日产油量",
            window_start=date(2026, 1, 1),
            window_end=TODAY,
            limit=None,
            ranking=False,
        )
    )
    assert rebind.kind == OUTCOME_ROWS
    assert rebind.rebind_notice is not None and "改绑" in rebind.rebind_notice
    line = lineage_filter(rebind)
    assert "时间＝2026-01-01～2026-08-31" in line  # 改绑后含端日期（end＝水位＋1 天）
    assert "[2026-01-01, 2026-09-01)" in line
    assert "时间＝ " not in line
    # 拦停话术同根（P-013 疑点 2）：整窗晚于水位的无标签草案——窗标签非空在场。
    blocked = engine.run(
        QueryPlan(
            metric_slot="日产油量",
            window_start=date(2026, 9, 8),
            window_end=TODAY,
            limit=None,
            ranking=False,
            is_default=True,
        )
    )
    assert blocked.kind == OUTCOME_FRESHNESS_BLOCK
    assert blocked.window_label == "2026-09-08～2026-10-07"
    assert blocked.message is not None
    assert "2026-09-08～2026-10-07" in blocked.message


# ---------- 验收⑨：换指标出数被 FX-13 一致性闸拦（validate 拒） ----------


def test_metric_switch_blocked() -> None:
    engine = _engine()
    plan = _plan("日产油量", "去年各井日产油量是多少？")
    switched = replace(plan, metric_slot="油压")  # 问句问油量、计划换油压——给差不多通道
    check = engine.validate(switched, candidates=frozenset({"日产油量"}))
    assert check.ok is False
    assert check.reason is not None
    assert "候选集" in check.reason
    assert "油压" in check.reason
    # 原计划同候选集过（FX-13 只拦替换，不误伤在集计划）。
    assert engine.validate(plan, candidates=frozenset({"日产油量"})).ok is True


# ---------- 验收⑩：只读断言——执行后库表零变化（INV-2）＋六联合态全形态收口 ----------


def test_readonly_inv2() -> None:
    engine = _engine()
    executor = engine.executor  # 公开 seam 观测面：只读断言用
    before = executor.records()
    # 六联合态全形态各跑一枪（rows/freshness_block/need_clarify/unbound_degrade/
    # external_table_approval/refuse——refuse 两路：未注册指标＋越界窗）。
    plans = [
        _plan("日产油量", "去年各井每天的日产油量是多少？"),
        _plan("日产油量", "本月各井日产油量是多少？"),
        _plan("日产油量", "最近各井日产油量怎么样？"),
        _plan("含水率", "去年各井含水率是多少？"),
        _plan("日产油量", "井位台账里日产油量最高的井是哪口？"),
        _plan("不存在的指标", "去年各井不存在的指标是多少？"),
        QueryPlan(
            metric_slot="日产油量",
            window_start=date(2026, 10, 1),
            window_end=date(2027, 10, 1),  # 窗尾落未来＋窗长超 366 天——窗界越界
            limit=None,
            ranking=False,
        ),
    ]
    kinds = {engine.run(plan).kind for plan in plans}
    assert kinds == {
        OUTCOME_ROWS,
        OUTCOME_FRESHNESS_BLOCK,
        OUTCOME_NEED_CLARIFY,
        OUTCOME_UNBOUND_DEGRADE,
        OUTCOME_EXTERNAL_TABLE_APPROVAL,
        OUTCOME_REFUSE,
    }
    # 执行后库表零变化：快照深比对零变。
    assert executor.records() == before
    # 执行面无写方法（INV-2——只读面零写出口）。
    public = {name for name in vars(CsvSnapshotExecutor) if not name.startswith("_")}
    assert public == {"execute", "records"}


# ---------- V2-71：聚合下推数据库（汇总型 aggregate——整窗 SUM 库内算单行） ----------


class _V271AggregateSnapshotExecutor(CsvSnapshotExecutor):
    """V2-71 端到端缝替身——CsvSnapshotExecutor 补汇总形投影（不改既有假执行器）。

    pg_executor 汇总分支（整窗 SUM 单行、无 GROUP BY 无 LIMIT）在题册快照上的
    对位：窗内行计量列求和（None 跳过——排名形同口径），单行单合计列返回；
    明细/排名两形照旧走 super() 原语义（零漂移）。last_plan＝执行缝入参观测面
    （引擎 SqlPlan 装配透传 aggregate 的断言依据）。
    """

    def __init__(self) -> None:
        super().__init__()
        self.last_plan: SqlPlan | None = None

    def execute(self, plan: SqlPlan) -> QueryResult:
        self.last_plan = plan
        if not plan.aggregate:
            return super().execute(plan)
        values = [
            getattr(row, plan.measure_column)
            for row in self.records()
            if plan.window.start <= row.prod_date < plan.window.end
        ]
        total = sum((value for value in values if value is not None), Decimal("0"))
        total_col = f"{plan.metric_slot}合计（{plan.unit}）"
        return QueryResult(columns=((total_col, total_col),), rows=({total_col: total},))


def _v271_sql_plan(*, ranking: bool, aggregate: bool) -> SqlPlan:
    """三形同参数 SQL 计划（同窗/同 LIMIT 收口值——形状隔离对照面）。"""
    return SqlPlan(
        metric_slot="日产油量",
        measure_column="oil_output",
        unit="吨",
        window=TimeWindow(start=date(2025, 9, 1), end=date(2026, 1, 1), label="去年"),
        limit_effective=50,
        ranking=ranking,
        direction=DIRECTION_DESC,
        aggregate=aggregate,
        actor="dev-u1",
    )


def _v271_compiled_sql(plan: SqlPlan) -> str:
    """SqlPlan → 编译 SQL 文本（PgQueryExecutor._statement 测试观测面——零连库）。"""
    statement = PgQueryExecutor(())._statement(plan)
    return str(statement.compile(compile_kwargs={"literal_binds": True})).upper()


def test_v271_query_plan_aggregate_flag_and_zero_drift_default() -> None:
    """构造面：aggregate=True 合法；缺省 False——既有计划装配零漂移锚。"""
    plan = QueryPlan(
        metric_slot="日产油量",
        window_start=date(2025, 9, 1),
        window_end=date(2026, 1, 1),
        limit=None,
        ranking=False,
        aggregate=True,
    )
    assert plan.aggregate is True
    # 不传 aggregate 的计划（既有明细/排名形）缺省 False——零漂移。
    bare = QueryPlan(
        metric_slot="日产油量",
        window_start=date(2025, 9, 1),
        window_end=date(2026, 1, 1),
        limit=None,
        ranking=False,
    )
    assert bare.aggregate is False
    # 既有装配链（build_query_plan）不产汇总形——明细问句/排名问句照旧。
    assert _plan("日产油量", "去年各井每天的日产油量是多少？").aggregate is False
    assert _plan("日产油量", "去年日产油量最高的井是哪口？").aggregate is False


def test_v271_engine_aggregate_single_row_window_total() -> None:
    """引擎端到端：aggregate=True 计划 → SqlPlan 透传 → 整窗合计单行返回。

    期望值＝fixture 数据源（题册绑定 CSV 快照）去年窗 [2025-09-01, 2026-01-01)
    全量 10,492 行 oil_output 逐行求和＝312100.16（题册口径 ±0.1）——
    明细 50 截断/排名分组形在此都不可能出现该数值（单行整窗合计专属）。
    """
    executor = _V271AggregateSnapshotExecutor()
    engine = QueryEngine(
        knowledge=InMemoryKnowledgeStore(question_array_snapshot(), today=TODAY),
        executor=executor,
        waterline=lambda: WatermarkFace(
            data_date=WATERMARK, promise="T-1", tag="落后 38 天（超期）",
        ),
        today=lambda: TODAY,
    )
    plan = QueryPlan(
        metric_slot="日产油量",
        window_start=date(2025, 9, 1),
        window_end=date(2026, 1, 1),
        limit=None,
        ranking=False,
        aggregate=True,
    )
    outcome = engine.run(plan)
    assert outcome.kind == OUTCOME_ROWS
    # 引擎装配透传：汇总形进执行缝（ranking=False 纯汇总——不混排名形）。
    assert executor.last_plan is not None
    assert executor.last_plan.aggregate is True
    assert executor.last_plan.ranking is False
    # 答案表卡只有一列「{指标}合计（{单位}）」，恰单行。
    assert outcome.columns == ((OIL_TOTAL_COL, OIL_TOTAL_COL),)
    assert outcome.rows is not None
    assert len(outcome.rows) == 1
    assert set(outcome.rows[0]) == {OIL_TOTAL_COL}
    # 数值＝fixture 数据源去年窗合计（既有数据源现算＋题册钉值双锚）。
    window_rows = [
        row for row in executor.records()
        if date(2025, 9, 1) <= row.prod_date < date(2026, 1, 1)
    ]
    expected = sum(
        (row.oil_output for row in window_rows if row.oil_output is not None),
        Decimal("0"),
    )
    assert outcome.rows[0][OIL_TOTAL_COL] == expected
    _assert_pinned(outcome.rows[0][OIL_TOTAL_COL], "312100.16")
    # 窗全在水位前——零改绑注记；血缘照常落（口径/窗口/水位注记不丢）。
    assert outcome.rebind_notice is None
    assert outcome.lineage is not None
    assert any(line.key == LINEAGE_KEY_WATERMARK for line in outcome.lineage)
    filter_line = next(line for line in outcome.lineage if line.key == LINEAGE_KEY_FILTER)
    assert "2025-09-01" in filter_line.value


def test_v271_statement_aggregate_sum_without_limit() -> None:
    """SQL 形状：汇总形 → SUM 在场、无 GROUP BY 无 LIMIT（明细 50 上限不挡库内算）。"""
    sql = _v271_compiled_sql(_v271_sql_plan(ranking=False, aggregate=True))
    assert "SUM(" in sql
    assert "GROUP BY" not in sql
    assert "LIMIT" not in sql
    # 窗界半开区间下推在场（[2025-09-01, 2026-01-01)）。
    assert "2025-09-01" in sql
    assert "2026-01-01" in sql


def test_v271_statement_ranking_detail_shapes_unchanged() -> None:
    """零漂移锚：同参数 ranking/明细形 SQL 与改前一致（LIMIT 在场、各自形状不变）。"""
    ranking_sql = _v271_compiled_sql(_v271_sql_plan(ranking=True, aggregate=False))
    assert "SUM(" in ranking_sql
    assert "GROUP BY" in ranking_sql
    assert "ORDER BY" in ranking_sql
    assert "DESC" in ranking_sql
    assert "LIMIT 50" in ranking_sql
    detail_sql = _v271_compiled_sql(_v271_sql_plan(ranking=False, aggregate=False))
    assert "SUM(" not in detail_sql
    assert "GROUP BY" not in detail_sql
    assert "ORDER BY" in detail_sql
    assert "LIMIT 50" in detail_sql


async def test_v271_data_query_whitelist_accepts_aggregate_draft() -> None:
    """白名单：data_query args 校验放行 plan_draft.aggregate=true（V2-71 发射键）。

    schema 拒＝bad_args 引擎零触——本钉走通到引擎（validate_calls==1）且计划
    带 aggregate=True，即键在闭世界白名单并透传装配（_plan_from_draft）。
    """
    engine = FakeQueryEngine(outcome=QueryOutcome.refuse(reason="V2-71 白名单钉测罐头"))
    registry = ToolRegistry(
        knowledge=FakeKnowledgeStore(), query=engine, retrieval=FakeRetrievalEngine(),
    )
    result = await registry.call(
        DATA_QUERY,
        {
            "plan_draft": {
                "metric_slot": "日产油量",
                "ranking": False,
                "aggregate": True,
                "window_start": "2025-09-01",
                "window_end": "2026-01-01",
            }
        },
        ToolContext(actor="dev-u1", budget=4),
    )
    # schema 放行且草案透传：引擎收到 aggregate=True 计划。
    assert engine.validate_calls == 1
    assert engine.plans
    assert engine.plans[0].aggregate is True
    assert engine.plans[0].ranking is False
    # 罐头 refuse 原样回（非 bad_args——schema/装配两闸都没拦）。
    assert result.error is not None
    assert result.error.category == CATEGORY_REFUSED
    # schema 面自钉：plan_draft.properties 增 aggregate（boolean 类型）。
    descriptor = next(d for d in registry.descriptors() if d.name == DATA_QUERY)
    plan_props = descriptor.args_schema["properties"]["plan_draft"]["properties"]
    assert plan_props["aggregate"]["type"] == "boolean"
