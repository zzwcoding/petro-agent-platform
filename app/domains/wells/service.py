"""domains.wells.service —— 井档案读模型服务（一口井一份档案——编排纯读面）。

98 §3.2 wells 卡公开接口的本批落地面（context_pack 注入面归 A1 消费批）：
- ``wells_visible``：选井列表——服务端数据域裁剪（无权井不出现，F48）；
- ``well_profile``：档案明细 8 字段＋quality_notes 红字＋卡底注记；
- ``well_chain``：关系链（纪录合并视图服务端编排＋三台账＋五页签计数＋尾注）；
- ``well_change_tickets``：变动页签只读投影（主单在 A3——V1 端点壳返空列表，
  不 mock 假单；装配批接 approval.project_by_object，B10 只允许投影口）。

编排纪律：合并/排序/计数/尾注拼装全部服务端完成，前端零编排零拼算（A2 合同
端点 3 节）；403/404 判别＝resolve_visible_well 纯语义（行为规则 1②③）。
"""

from __future__ import annotations

from datetime import date

from app.domains.security import Actor
from app.domains.wells.domain import (
    DEVICE_TYPES,
    MEASURE_TYPES,
    WELL_KIND_BY_CODE,
    ChainCounts,
    ChainView,
    ChangeTicketProjection,
    DeviceView,
    EventView,
    MeasureView,
    OverhaulView,
    WellProfile,
    WellSummary,
    build_events,
    device_foot_for,
    device_snapshot_for,
    foot_note_for,
    measure_demo_copy,
    measure_foot_for,
    normalize_well_id,
    quality_notes_for,
    resolve_visible_well,
    tail_for,
)
from app.domains.wells.store import (
    MeasureLedgerRow,
    OverhaulLedgerRow,
    StatusLogLedgerRow,
    WellInfoRow,
    WellsStore,
)
from app.infra.db import ConnectionManager


def _iso(value: date | None) -> str | None:
    """date 列 → ISO 串（机器时间入 DTO 的唯一形态——00 §1.4）。"""
    return value.isoformat() if value is not None else None


def _well_kind(well_type: str | None) -> str | None:
    """井别中文名派生（EW=采油/IW=注水——合同常量；未知码/缺省如实 None）。"""
    if well_type is None:
        return None
    return WELL_KIND_BY_CODE.get(well_type)


def _summary(row: WellInfoRow) -> WellSummary:
    return WellSummary(
        well_id=row.well_id,
        well_name=row.well_name,
        well_kind=_well_kind(row.well_type),
        well_kind_code=row.well_type,
        block_name=row.block_name,
        current_status=row.current_status,
        remark=row.remarks,
    )


def _profile(row: WellInfoRow) -> WellProfile:
    return WellProfile(
        well_id=row.well_id,
        well_name=row.well_name,
        well_kind=_well_kind(row.well_type),
        well_kind_code=row.well_type,
        first_prod_date=_iso(row.first_prod_date),
        platform=row.platform,
        block_name=row.block_name,
        current_status=row.current_status,
        remark=row.remarks,
        quality_notes=quality_notes_for(row.well_id),
        foot_note=foot_note_for(row.well_type),
    )


def _measure_views(well_id: str, rows: list[MeasureLedgerRow]) -> list[MeasureView]:
    """措施台账投影：key＝m{n}（作业日倒序——源台账无业务键，读模型序号即标识；
    content/result＝冻结演示文案（收编行②），无冻结值行如实 None——台账列形
    缺口，装配批扩列后改取行值，DTO 零改动）。"""
    views: list[MeasureView] = []
    for index, row in enumerate(rows, start=1):
        job_date = _iso(row.job_date) or ""
        copy = measure_demo_copy(well_id, job_date, row.measure_type)
        content, result = copy if copy is not None else (None, None)
        views.append(
            MeasureView(
                key=f"m{index}", date=job_date, type=row.measure_type,
                content=content, result=result,
            )
        )
    return views


def _overhaul_views(rows: list[OverhaulLedgerRow]) -> list[OverhaulView]:
    """检修台账投影：key＝o{n}（完工日倒序）；batch＝「批次 」+batch_id 展示
    拼装（无批次行＝None）；impact 原名对应照抄（合同端点 3 节——as-is 文本）。"""
    views: list[OverhaulView] = []
    for index, row in enumerate(rows, start=1):
        views.append(
            OverhaulView(
                key=f"o{index}",
                date_start=_iso(row.overhaul_start),
                date_end=_iso(row.overhaul_end),
                job=row.overhaul_type,
                impact=row.affected_output,
                batch=f"批次 {row.batch_id}" if row.batch_id else None,
            )
        )
    return views


def _status_event_views(rows: list[StatusLogLedgerRow]) -> list[EventView]:
    """状态变更行 → events 行（key＝s{id} 源行锚；outcome＝警示文案）。"""
    return [
        EventView(
            key=f"s{row.id}", kind="状态变更", date=_iso(row.occurred_on),
            date_end=None, title=row.title, outcome=row.outcome,
        )
        for row in rows
    ]


class WellsService:
    """井档案读模型服务（纯读域——无写口、无 LLM、时钟无关）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._store = WellsStore(db)

    # ---------- 端点 1：选井列表 ----------

    async def wells_visible(self, actor: Actor) -> list[WellSummary]:
        """选井下拉列表——服务端按当前角色数据域过滤（无权限的井根本不出现；
        列表路径走过滤不报 403——F48「看不到＝世界里没有」）。"""
        return [_summary(row) for row in await self._store.list_wells(actor)]

    # ---------- 直调越权闸（端点 2/3/4 共用） ----------

    async def _require_visible_well(self, well_id: str, actor: Actor) -> str:
        """归一化＋403/404 判别（resolve_visible_well 纯语义）→ 归一化主键。

        预埋期谓词恒空（M-01）→ 403 分支不可达，形状照写（开放问题 6 裁决）。
        """
        normalized = normalize_well_id(well_id)
        filtered = await self._store.get_well(normalized, actor)
        if filtered is None:
            unfiltered = await self._store.get_well_unfiltered(normalized)
            resolve_visible_well(None, unfiltered, normalized)  # 403/404 二分
        return normalized

    # ---------- 端点 2：档案明细 ----------

    async def well_profile(self, well_id: str, actor: Actor) -> WellProfile:
        """档案明细（8 字段＋质量备注红字数组＋卡底注记——页面规格 §A2 F1）。"""
        normalized = await self._require_visible_well(well_id, actor)
        row = await self._store.get_well(normalized, actor)
        assert row is not None  # 闸后必在（与闸同数据同一查询——窄化断言）
        return _profile(row)

    # ---------- 端点 3：关系链 ----------

    async def well_chain(self, well_id: str, actor: Actor) -> ChainView:
        """关系链（纪录合并视图＋三台账＋五页签计数＋类型枚举＋随井尾注）。

        合并与排序服务端完成；changes 计数与端点 4 total 同源同值（V1＝0——
        A3 主单未建，不 mock 假单）。
        """
        normalized = await self._require_visible_well(well_id, actor)
        measures = _measure_views(
            normalized, await self._store.list_measures(normalized)
        )
        overhauls = _overhaul_views(await self._store.list_overhauls(normalized))
        status_events = _status_event_views(
            await self._store.list_status_changes(normalized)
        )
        devices = [
            DeviceView(
                key=d.key, type=d.type, status=d.status, since=d.since, note=d.note
            )
            for d in device_snapshot_for(normalized)
        ]
        events = build_events(measures, overhauls, status_events)
        return ChainView(
            well_id=normalized,
            counts=ChainCounts(
                events=len(events),
                measures=len(measures),
                devices=len(devices),
                overhauls=len(overhauls),
                changes=await self._change_tickets_total(normalized),
            ),
            measure_types=list(MEASURE_TYPES),  # 尾注枚举段结构化字段（恒返回）
            device_types=list(DEVICE_TYPES),
            measure_foot=measure_foot_for(normalized),
            device_foot=device_foot_for(normalized),
            events=events,
            measures=measures,
            devices=devices,
            overhauls=overhauls,
            tail=tail_for(normalized),
        )

    # ---------- 端点 4：变动页签投影（A3 只读投影——V1 端点壳） ----------

    async def _change_tickets_total(self, normalized_well_id: str) -> int:
        """变动页签计数（与端点 4 total 同源同值——合同 counts 节）。

        V1 阶段 A3 主单未建（approval 域未落表）：恒 0＋如实注记，不 mock 假单；
        装配批改接 A3 对象实体引用过滤（object_refs——不做字符串包含匹配），
        两处消费本方法同源。
        """
        return 0

    async def well_change_tickets(
        self, well_id: str, actor: Actor
    ) -> ChangeTicketProjection:
        """涉及本井的变动单只读投影（端点 4——A2 无审批操作端点）。

        V1 端点壳照合同形状返空列表＋如实注记（票面施工方案 1——不 mock 假单）；
        按 time 倒序、对象实体引用过滤、status/plane 直返展示值等投影约定随
        A3 落表批填肉，响应形状零改动（行为规则 4/开放问题 7 已回对）。
        """
        normalized = await self._require_visible_well(well_id, actor)
        total = await self._change_tickets_total(normalized)
        return ChangeTicketProjection(
            well_id=normalized,
            items=[],  # A3 主单未建——空列表如实返（装配批接 approval.project_by_object）
            total=total,
        )
