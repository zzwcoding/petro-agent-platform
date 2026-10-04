"""api.wells —— /api/wells 路由族（A2-井档案.md v0.2 合同，4 条读路由；M-02）。

形状注记：
- 响应字段 snake_case（00 §14-R1）；字段名对齐设定书 §A.1（first_prod_date/
  block_name 原名沿用——合同端点 2 注）。
- 路由声明取「无 prefix router＋装饰器全路径」形：端点 1 落在前缀根
  （GET /api/wells——合同端点清单），FastAPI 的 APIRoute 禁空路径段，
  前缀式声明（prefix＋"/"）会 307 重定向且合同覆盖率闸扫描器对不上——
  本模块即闸扫描器（tools/contract_coverage.parse_implemented）对
  前缀根端点的首个先例，后续 C2/A3/E2 同形端点照此办理。
- 权限：A2 页全员可见（roles.js MENU A2 无 roles 限制——工作台组全员）——
  require 式声明一行（CurrentActor）按 Owner 拍板口径预埋（全员可读预埋期）；
  行级语义双向分清（合同行为规则 1）：①列表路径走服务端过滤不报 403（无权
  井不出现——F48）；②直调越权 403（域内 resolve_visible_well 抛
  ForbiddenError，security 同源异常既有映射）；③井不存在 404（well_not_found
  ——错误码草案；预埋期 403 分支不可达，形状照写——开放问题 6 裁决）。
- 端点 3 枚举尾注（measure_foot/device_foot）服务端按井派生全文（页面以 foot
  全文渲染，前端不自行拼装业务文案）；events[].date_end 仅检修行携带——
  检修行与措施/状态变更行用两个响应体类型承载（措施/状态变更行无 date_end 键）。
- 端点 4＝A3 只读投影端点壳（V1 阶段 A3 主单未建——照合同形状返空列表＋
  如实注记，不 mock 假单；本页无任何变动单写操作端点）。
- F4 去问一问不立新端点——前端跳转 A1 复用 POST /api/chat/asks 的
  page_context（合同「去问一问」节；本路由族不承载）。
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentActor, WellsDep
from app.domains.wells import (
    ChainCounts,
    ChainView,
    ChangeTicketProjection,
    EventView,
    WellProfile,
    WellSummary,
)

router = APIRouter(tags=["wells"])  # 无 prefix——端点 1 落前缀根（形状注记）


# ---------- 端点 1：GET /api/wells 选井下拉列表 ----------


class WellListItemBody(BaseModel):
    well_id: str
    well_name: str | None
    well_kind: str | None
    well_kind_code: str | None
    block_name: str | None
    current_status: str | None
    remark: str | None


class WellListResponse(BaseModel):
    items: list[WellListItemBody]
    total: int


@router.get("/api/wells", response_model=WellListResponse)
async def list_wells(
    service: WellsDep,
    _actor: CurrentActor,  # 权限预埋一行（A2 全员可见——Owner 拍板口径）
) -> WellListResponse:
    """选井下拉列表（服务端按当前角色数据域过滤——无权限的井不在响应里，
    前端不做打码不做二次过滤；排序按 well_id 升序；total＝过滤后计数）。"""
    rows: list[WellSummary] = await service.wells_visible(_actor)
    return WellListResponse(
        items=[
            WellListItemBody(
                well_id=r.well_id, well_name=r.well_name, well_kind=r.well_kind,
                well_kind_code=r.well_kind_code, block_name=r.block_name,
                current_status=r.current_status, remark=r.remark,
            )
            for r in rows
        ],
        total=len(rows),
    )


# ---------- 端点 2：GET /api/wells/{well_id} 档案明细 ----------


class WellProfileResponse(BaseModel):
    well_id: str
    well_name: str | None
    well_kind: str | None
    well_kind_code: str | None
    first_prod_date: str | None
    platform: str | None
    block_name: str | None
    current_status: str | None
    remark: str | None
    quality_notes: list[str]
    foot_note: str | None


@router.get("/api/wells/{well_id}", response_model=WellProfileResponse)
async def well_profile(
    well_id: str,
    service: WellsDep,
    _actor: CurrentActor,  # 权限预埋一行（A2 全员可见——Owner 拍板口径）
) -> WellProfileResponse:
    """档案明细（8 字段＋质量备注红字数组＋卡底注记；路径参数按归一化主键
    解析——N2/N-2→N-02，未归一化形态服务端归一处理不另设错误码）。"""
    view: WellProfile = await service.well_profile(well_id, _actor)
    return WellProfileResponse(
        well_id=view.well_id, well_name=view.well_name, well_kind=view.well_kind,
        well_kind_code=view.well_kind_code, first_prod_date=view.first_prod_date,
        platform=view.platform, block_name=view.block_name,
        current_status=view.current_status, remark=view.remark,
        quality_notes=list(view.quality_notes), foot_note=view.foot_note,
    )


# ---------- 端点 3：GET /api/wells/{well_id}/chain 关系链 ----------


class ChainCountsBody(BaseModel):
    events: int
    measures: int
    devices: int
    overhauls: int
    changes: int


class MeasureBody(BaseModel):
    key: str
    date: str
    type: str | None
    content: str | None
    result: str | None


class DeviceBody(BaseModel):
    key: str
    type: str
    status: str
    since: str
    note: str


class OverhaulBody(BaseModel):
    key: str
    date_start: str | None
    date_end: str | None
    job: str | None
    impact: str | None
    batch: str | None


class MeasureEventBody(BaseModel):
    """措施/状态变更纪录行（date_end 仅检修行携带——本体无该键）。"""

    key: str
    kind: str
    date: str | None
    title: str | None
    outcome: str | None


class OverhaulEventBody(BaseModel):
    """检修纪录行（date_end 携带——排序键＝完工日）。"""

    key: str
    kind: str
    date: str | None
    date_end: str | None
    title: str | None
    outcome: str | None


def _event_body(event: EventView) -> MeasureEventBody | OverhaulEventBody:
    """纪录行 → 响应体（检修行带 date_end 键，其余行不携带——合同逐字段）。"""
    if event.date_end is not None:
        return OverhaulEventBody(
            key=event.key, kind=event.kind, date=event.date, date_end=event.date_end,
            title=event.title, outcome=event.outcome,
        )
    return MeasureEventBody(
        key=event.key, kind=event.kind, date=event.date,
        title=event.title, outcome=event.outcome,
    )


class ChainResponse(BaseModel):
    well_id: str
    counts: ChainCountsBody
    measure_types: list[str]
    device_types: list[str]
    measure_foot: str
    device_foot: str
    events: list[MeasureEventBody | OverhaulEventBody]
    measures: list[MeasureBody]
    devices: list[DeviceBody]
    overhauls: list[OverhaulBody]
    tail: str | None


@router.get("/api/wells/{well_id}/chain", response_model=ChainResponse)
async def well_chain(
    well_id: str,
    service: WellsDep,
    _actor: CurrentActor,  # 权限预埋一行（A2 全员可见——Owner 拍板口径）
) -> ChainResponse:
    """关系链（纪录合并视图＋措施/设备/检修三台账＋五页签计数＋类型枚举＋
    随井尾注——合并排序与计数拼装服务端完成，前端零编排零拼算）。"""
    view: ChainView = await service.well_chain(well_id, _actor)
    counts: ChainCounts = view.counts
    return ChainResponse(
        well_id=view.well_id,
        counts=ChainCountsBody(
            events=counts.events, measures=counts.measures, devices=counts.devices,
            overhauls=counts.overhauls, changes=counts.changes,
        ),
        measure_types=list(view.measure_types),
        device_types=list(view.device_types),
        measure_foot=view.measure_foot,
        device_foot=view.device_foot,
        events=[_event_body(e) for e in view.events],
        measures=[
            MeasureBody(
                key=m.key, date=m.date, type=m.type, content=m.content, result=m.result
            )
            for m in view.measures
        ],
        devices=[
            DeviceBody(
                key=d.key, type=d.type, status=d.status, since=d.since, note=d.note
            )
            for d in view.devices
        ],
        overhauls=[
            OverhaulBody(
                key=o.key, date_start=o.date_start, date_end=o.date_end,
                job=o.job, impact=o.impact, batch=o.batch,
            )
            for o in view.overhauls
        ],
        tail=view.tail,
    )


# ---------- 端点 4：GET /api/wells/{well_id}/change-tickets 变动页签（A3 投影壳） ----------


class ChangeTicketItemBody(BaseModel):
    id: str
    status: str
    plane: str
    short: str
    proposer: str
    time: str


class ChangeTicketsResponse(BaseModel):
    well_id: str
    items: list[ChangeTicketItemBody]
    total: int


@router.get("/api/wells/{well_id}/change-tickets", response_model=ChangeTicketsResponse)
async def well_change_tickets(
    well_id: str,
    service: WellsDep,
    _actor: CurrentActor,  # 权限预埋一行（A2 全员可见——Owner 拍板口径）
) -> ChangeTicketsResponse:
    """涉及本井的变动单只读投影（主单在 A3，A2 无审批操作端点）。

    V1 阶段 A3 主单未建——端点壳照合同形状返空列表（items=[]＋total=0，
    空态文案「本井暂无变动单」由前端照抄渲染）＋如实注记：不 mock 假单；
    装配批接 A3 对象实体引用过滤（不做字符串包含匹配），响应形状零改动。
    """
    view: ChangeTicketProjection = await service.well_change_tickets(well_id, _actor)
    return ChangeTicketsResponse(
        well_id=view.well_id,
        items=[
            ChangeTicketItemBody(
                id=i.id, status=i.status, plane=i.plane, short=i.short,
                proposer=i.proposer, time=i.time,
            )
            for i in view.items
        ],
        total=view.total,
    )
