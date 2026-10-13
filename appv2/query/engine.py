"""query.engine —— QueryEngine（validate＋run；specs/query.md 接口定义节）。

V1 六站链（M-06 N7.1–N7.6）移植为确定性引擎：输入计划，输出权威表＋血缘卡
或六类闸结果之一。问数组 A~H 族行为逐族钉死不回归（specs/query.md「目标」）。

run() 闸序（本票定稿；V1 语义逐闸保留，闸序一处有意修复）：
1. 台账绑定校验（N7.1）——未注册→refuse；在册未绑定→unbound_degrade
   （Evidence 依据经 knowledge 取——query→knowledge 为 modules.md 登记的
   唯一互引例外，MEASURE_COLUMNS 判定单点在 knowledge 不造第二份）；
2. 缺参反问（N7.1）——模糊时间窗（window 两槽 None）→need_clarify 三选一；
3. 窗界校验（V1 R6-03 移植）——窗尾不落未来＋窗长 ≤366 天，越界 refuse；
4. 外表越集审批（N7.4c）——**先于新鲜度闸＝Q11 病灶修复点**：V1 闸序
   N7.4a 先于 N7.4c，默认窗问句必被新鲜度拦停，「井位台账」interrupt 双重
   掩蔽不可达（eval/results/Q11-评测报告.md 问题 3）；V2 越集审批前置，
   别名「井位台账」→erp_well_register 进选表命中集→ASK 素材齐可达；
5. 新鲜度闸（N7.4a）——窗整体晚于水位→freshness_block（水位/窗标签/默认窗
   标注如实携带，零数值）；窗尾越过水位→改绑最近可用日＋注记（不冒充）；
   水位未回写→血缘④如实缺行（不造达标假象）；
6. 只读执行（N7.5）——经 QueryExecutor 缝（白名单 Schema INV-2/INV-3；
   生产适配器走 appv2.infra.db readonly）；
7. 结果核验（N7.6）——0 行如实 refuse（不编数）；有行→rows＋血缘卡五要素
   （INV-5 口径依据——血缘卡随结果必出）。

依赖只许 appv2.infra 公开接口（时钟 B14）＋appv2.knowledge 公开接口；不
import app.**（V1 domain.py 逻辑以行为为准重实现——specs/query.md 边界）。
validate/run 均同步纯确定性（零模型调用——N5 判型/路由语义不进本模块，
specs/query.md「不做什么」）。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import date, timedelta

from appv2.infra import clock
from appv2.knowledge import (
    BINDING_BOUND,
    MEASURE_COLUMNS,
    Evidence,
    KnowledgeStore,
)
from appv2.query.domain import (
    ASKBACK_TIME_CHOICES,
    ASKBACK_TIME_QUESTION,
    FRESHNESS_CLAMP_NOTE_TEMPLATE,
    FRESHNESS_REJECT_TEMPLATE,
    LINEAGE_KEY_CALIBER,
    LINEAGE_KEY_CLOSING,
    LINEAGE_KEY_FILTER,
    LINEAGE_KEY_PERMISSION,
    LINEAGE_KEY_SOURCE,
    LINEAGE_KEY_WATERMARK,
    LineageLine,
    PlanCheck,
    QueryOutcome,
    QueryPlan,
    SqlPlan,
    TimeWindow,
    build_extable_ask,
    check_plan_window_bounds,
    effective_limit,
    fill_window_label,
    lineage_caliber_line,
    lineage_closing_line,
    lineage_filter_line,
    lineage_permission_line,
    lineage_source_line,
    lineage_watermark_line,
)
from appv2.query.executor import QueryExecutor

WaterlineLoader = Callable[[], "WatermarkFace | None"]

_ONE_DAY = timedelta(days=1)


class WatermarkFace:
    """汇总层水位面（V1 M-05a 水位读面投影同形——chat 不触 water_line 表，B3/B9）。

    tag/late_days 由供给方经 E2 freshness_judgment 单源计算随面携入（T-1 判定
    不在本引擎重算——新鲜度闸只消费）；缺行时 loader 返回 None。
    """

    __slots__ = ("data_date", "late_days", "layer", "promise", "tag")

    def __init__(
        self,
        *,
        data_date: date,
        promise: str = "T-1",
        tag: str = "—",
        late_days: int = 0,
        layer: str = "agg",
    ) -> None:
        self.layer = layer
        self.data_date = data_date
        self.promise = promise
        self.tag = tag
        self.late_days = late_days


class QueryEngine:
    """问数确定性引擎（validate＝白名单/一致性/窗界；run＝六站闸链）。

    四缝注入（specs/modules.md query 卡 Seam——KnowledgeStore/SQL 执行器/
    水位读缝/时钟）：knowledge＝台账绑定判定与降级 Evidence（公开接口）；
    executor＝只读执行缝（测试＝CsvSnapshotExecutor，生产走 infra.db）；
    waterline＝水位读缝（None＝未接线——血缘④如实缺行，V1 同语义）；today＝
    时钟缝（缺省 infra.clock——B14 时间唯一出口，测试注入固定执行日）。
    """

    def __init__(
        self,
        *,
        knowledge: KnowledgeStore,
        executor: QueryExecutor,
        waterline: WaterlineLoader | None = None,
        today: Callable[[], date] | None = None,
    ) -> None:
        self.knowledge = knowledge
        self.executor = executor
        self.waterline = waterline
        self._today = today if today is not None else (lambda: clock.now().date())

    # ---------- validate：白名单/指标一致性（FX-13）/窗界 ----------

    def validate(
        self, plan: QueryPlan, *, candidates: Iterable[str] | None = None
    ) -> PlanCheck:
        """计划确定性校验（tools 层 data_query 草案先经本面——零模型）。

        - 指标槽位 ∈ 指标台账（不在目录不代答）；
        - FX-13 指标替换封堵：candidates 给定时槽位必须 ∈ 问句指标候选集
          （LLM 把问句问及之外的指标换成在册可出数近似指标＝「给差不多」
          通道——封堵；对齐纪律：宁可查不到，不给差不多）；
        - 窗界（V1 R6-03）：窗尾不落未来＋窗长 ≤366 天；
        - window 两槽 None（模糊时间）＝合法草案——缺参反问是 run 的联合态，
          不是校验失败。
        """
        evidence = self.knowledge.metric_by_name(plan.metric_slot)
        if evidence is None:
            return PlanCheck(
                ok=False,
                reason=(
                    f"metric_slot {plan.metric_slot!r} 不在指标台账——"
                    "不在目录不代答（台账绑定校验）"
                ),
            )
        if candidates is not None:
            allowed = frozenset(candidates)
            if plan.metric_slot not in allowed:
                return PlanCheck(
                    ok=False,
                    reason=(
                        f"metric_slot {plan.metric_slot!r} 不在问句指标候选集 "
                        f"{sorted(allowed)}——指标替换封堵（FX-13）：不代问句外指标出数"
                    ),
                )
        window = plan.window
        if window is not None:
            try:
                check_plan_window_bounds(window, today=self._today())
            except ValueError as exc:
                return PlanCheck(ok=False, reason=str(exc))
        return PlanCheck(ok=True, reason=None)

    # ---------- run：六站闸链（六联合态逐一产出） ----------

    def run(
        self, plan: QueryPlan, *, approved_tables: tuple[str, ...] = ()
    ) -> QueryOutcome:
        """执行计划（六联合态——权威表＋血缘卡或闸结果，零模型调用）。

        approved_tables＝外表放行态（V2-52 越集续跑全通道——runtime 批准落点
        经 ToolContext 随行传入；缺省空＝闸语义零漂移）：plan 申报外表集对放行
        态比对，已批表放行、未批子集照旧挂审批（批准即续跑——放行态进引擎后
        出数收口，审批不再二循环）。
        """
        evidence = self.knowledge.metric_by_name(plan.metric_slot)
        if evidence is None:
            return QueryOutcome.refuse(
                reason=(
                    f"指标 {plan.metric_slot!r} 不在指标台账——不在目录不代答"
                    "（台账绑定校验）"
                )
            )
        if evidence.binding_state != BINDING_BOUND:
            return self._unbound_outcome(evidence)
        if plan.window is None:
            # 缺参反问（askback 时间窗三选一照抄——缺的是用户事实，无默认项）。
            return QueryOutcome.need_clarify(
                question=ASKBACK_TIME_QUESTION, choices=ASKBACK_TIME_CHOICES,
            )
        window = plan.window
        try:
            check_plan_window_bounds(window, today=self._today())
        except ValueError as exc:
            return QueryOutcome.refuse(reason=str(exc))
        # 外表越集审批（N7.4c）——先于新鲜度闸（Q11 闸序修复：默认窗拦停
        # 不再掩蔽 interrupt；模型与流程都无权自批——挂起等人工）。
        # V2-52 续跑全通道：放行态比对——已批表放行，仅未批子集挂审批。
        pending_tables = tuple(
            t for t in plan.external_tables if t not in set(approved_tables)
        )
        if pending_tables:
            approval_id = (
                f"APP-{self._today():%m%d}-{'-'.join(pending_tables)}"
            )
            return QueryOutcome.external_table_approval(
                tables=pending_tables,
                ask=build_extable_ask(
                    replace(plan, external_tables=pending_tables),
                    approval_id=approval_id,
                ),
            )
        # 新鲜度闸（N7.4a——超窗拦停/改绑，E2 T-1 语义渲染面）。
        waterline = self.waterline() if self.waterline is not None else None
        rebind_notice: str | None = None
        if waterline is not None:
            if window.start > waterline.data_date:
                # 窗整体在水位之后——无已出数数据：闸拦停（不返回空数冒充）。
                # 空标签填实（V2-22——拦停话术零空串；按拦停窗区间机械补标）。
                blocked = fill_window_label(window)
                return QueryOutcome.freshness_block(
                    watermark_date=waterline.data_date,
                    window_label=blocked.label,
                    is_default=blocked.is_default,
                    message=FRESHNESS_REJECT_TEMPLATE.format(
                        data_date=waterline.data_date.isoformat(),
                        tag=waterline.tag,
                        label=blocked.label,
                    ),
                )
            if window.end - _ONE_DAY > waterline.data_date:
                # 窗口后半段未出数——改绑最近可用日＋标注（V1 clamp 同语义）。
                window = TimeWindow(
                    start=window.start,
                    end=waterline.data_date + _ONE_DAY,
                    label=window.label,
                    is_default=window.is_default,
                )
                rebind_notice = FRESHNESS_CLAMP_NOTE_TEMPLATE.format(
                    data_date=waterline.data_date.isoformat(), tag=waterline.tag,
                )
        # 空标签窗填实（V2-22——P-013 疑点 4：真模型草案不带 window_label 时
        # 血缘③/零行拒答话术零空串；放闸后＝改绑窗按改绑后区间补标，标签与
        # 区间不矛盾；有标签原样返回——fixture 链与模型词面标签零影响）。
        window = fill_window_label(window)
        # 只读执行（N7.5——SqlPlan 派生字段单源重推导，草案值零直信）。
        column, unit = MEASURE_COLUMNS[plan.metric_slot]
        sql = SqlPlan(
            metric_slot=plan.metric_slot,
            measure_column=column,
            unit=unit,
            window=window,
            limit_effective=effective_limit(plan.limit),
            ranking=plan.ranking,
            aggregate=plan.aggregate,
            direction=plan.direction,
            actor=plan.actor,
        )
        result = self.executor.execute(sql)
        if not result.rows:
            # 结果核验（N7.6）：0 行如实回报不编数。
            return QueryOutcome.refuse(
                reason=(
                    f"查询执行成功但无数据行（时间窗「{window.label}」内查无数据）"
                    "——如实回报，不编数。"
                )
            )
        lineage = self._build_lineage(
            plan=plan, unit=unit, evidence=evidence, window=window,
            waterline=waterline, batch_id=result.batch_id,
        )
        return QueryOutcome.rows_with_lineage(
            columns=result.columns,
            rows=result.rows,
            lineage=lineage,
            rebind_notice=rebind_notice,
        )

    # ---------- 联合态装配件（血缘卡五要素——F13 keys 合同值不可改） ----------

    def _build_lineage(
        self,
        *,
        plan: QueryPlan,
        unit: str,
        evidence: Evidence,
        window: TimeWindow,
        waterline: WatermarkFace | None,
        batch_id: str | None,
    ) -> tuple[LineageLine, ...]:
        """血缘卡六行（五要素＋权限注入独立行——V1 lineage 帧同序同键）。"""
        # 血缘①口径：Evidence.value 机械投影（knowledge 公开接口——value 首段
        # ＝台账原名、「：」后至「｜」前＝口径定义段；value 格式由
        # tests/domains/test_v2_knowledge.py 钉死，同仓内单源）。
        metric_name, _, rest = evidence.value.partition("：")
        def_text = rest.split("｜", 1)[0]
        watermark_line = lineage_watermark_line(
            data_date=waterline.data_date if waterline is not None else None,
            promise=waterline.promise if waterline is not None else None,
            tag=waterline.tag if waterline is not None else None,
            batch_id=batch_id,
        )
        return (
            LineageLine(
                key=LINEAGE_KEY_CALIBER,
                value=lineage_caliber_line(
                    metric_name=metric_name, unit=unit, def_text=def_text,
                ),
            ),
            LineageLine(key=LINEAGE_KEY_SOURCE, value=lineage_source_line()),
            LineageLine(key=LINEAGE_KEY_FILTER, value=lineage_filter_line(window)),
            LineageLine(
                key=LINEAGE_KEY_PERMISSION, value=lineage_permission_line(plan.actor),
            ),
            LineageLine(key=LINEAGE_KEY_WATERMARK, value=watermark_line),
            LineageLine(
                key=LINEAGE_KEY_CLOSING,
                value=lineage_closing_line(
                    limit_requested=plan.limit, limit_effective=effective_limit(plan.limit),
                ),
            ),
        )

    def _unbound_outcome(self, evidence: Evidence) -> QueryOutcome:
        """在册未绑定降级（不冒充审定口径直出数——Evidence 依据如实携带）。"""
        metric_name = evidence.value.split("：", 1)[0]
        return QueryOutcome.unbound_degrade(
            evidence=evidence,
            basis=(
                f"指标「{metric_name}」在册但未绑定汇总层（agg）计量列——"
                "模板只认绑定 agg 计量列的指标，不自由生成 SQL（不冒充审定口径）、"
                "零数值。台账依据：" + evidence.value
            ),
        )
