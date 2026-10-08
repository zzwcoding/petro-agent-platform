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
    LINEAGE_KEY_CLOSING,
    LINEAGE_KEY_WATERMARK,
    OUTCOME_EXTERNAL_TABLE_APPROVAL,
    OUTCOME_FRESHNESS_BLOCK,
    OUTCOME_NEED_CLARIFY,
    OUTCOME_REFUSE,
    OUTCOME_ROWS,
    OUTCOME_UNBOUND_DEGRADE,
    CsvSnapshotExecutor,
    QueryEngine,
    QueryPlan,
    WatermarkFace,
    build_query_plan,
    resolve_askback_window,
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
