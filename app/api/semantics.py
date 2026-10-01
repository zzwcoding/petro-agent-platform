"""api.semantics —— /api/semantics 路由族（C1 册合同 v0.1；P1-01b 读面三件套）。

98 §5 模块归属：C1 指标与业务术语库＝semantics 模块（`/api/semantics/*`）——
本票新建本路由族挂 main（此前该前缀无路由）。纯读面（C1 第一合同）：全 GET、
零写端点——写请求由框架对 GET-only 路由的 405 兜底（合同「无对应路由 405」
路由级同构）；变更唯一入口 C2（本仓不落）。

形状注记：
- 分页（00 §4.1）：page≥1＋pageSize（缺省 20——D5 先例；量级 3–15 条/清单，
  整表返回为常态、page/pageSize 为预留参数）；响应回显 page/page_size（00
  §14-R1 响应字段 snake——D3 端点 14 本仓先例）。
- 筛选（00 §4.5）：keyword/status（逗号分隔多值）/owner；值域照 C1 合同冻结
  （status 六枚举/owner 四三枚举/指标 status 两值）、越界 400（C1 错误码草案
  「筛选枚举越界 400」；code=semantics_param_invalid——errors.py 新立登记）。
  「all」＝不过滤（C1「全部状态/全部负责人」＝all）。
- 读侧派生不落列（00 R2 先例——P1-01 差异 5/差异 2 的本票裁决）：
  terms `expired`/`expires_display`（F60 到日即标——infra.clock 现算）；
  metrics `grain_display`（C1 页签列形「粒度 · 单位」——sem_metric 存 M3 真源
  值不动，裁决 e；domain.metric_grain_display 拼装）。
- C1 端点 2 入参合同名 `status_key` 与 00 §4.5（P1-00b 补冻）`status` 冲突，
  票面指定照 00 §4.5——差异登记 tickets/phase1/README.md P1-01b 差异清单。
- 台账序＝id 升序（C1 台账序合同常量，无排序参数）。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import CurrentActor, SemanticsDep
from app.api.errors import CODE_SEMANTICS_PARAM_INVALID, ApiError
from app.domains.semantics import metric_grain_display, term_expiry
from app.infra.clock import now

router = APIRouter(prefix="/api/semantics", tags=["semantics"])

DEFAULT_PAGE = 1  # 00 §4.1
DEFAULT_PAGE_SIZE = 20  # D5 先例（00 §4.1）

# 筛选值域（C1 合同常量照抄：术语筛选枚举/指标筛选枚举/指标状态数组）。
TERM_STATUS_KEYS = (
    "有效", "禁用词", "有效（限作业区语境）", "有效（待联席裁决）",
    "有效（引用马涛）", "有效（已届满）",
)
TERM_OWNERS = ("开发室", "采油工艺所", "地质研究所", "语义 Owner")
METRIC_STATUS_VALUES = ("生效中", "待联席裁决")
METRIC_OWNERS = ("开发室", "采油工艺所", "销售计量站")

_FILTER_ALL = "all"  # C1「全部状态/全部负责人」＝all


def _parse_multi(name: str, raw: str | None, allowed: tuple[str, ...]) -> list[str] | None:
    """逗号分隔多值筛（00 §4.5）——越界 400 带允许值（C1 错误码草案）。"""
    if raw is None:
        return None
    values = [part.strip() for part in raw.split(",") if part.strip()]
    invalid = [value for value in values if value != _FILTER_ALL and value not in allowed]
    if invalid:
        raise ApiError(
            status_code=400,
            code=CODE_SEMANTICS_PARAM_INVALID,
            message=f"{name} 筛选值越界：{'、'.join(invalid)}",
            detail={"field": name, "invalid": invalid, "allowed": list(allowed)},
        )
    if any(value == _FILTER_ALL for value in values):
        return None  # all＝不过滤（合同「全部状态」语义）
    return values


def _parse_single(name: str, raw: str | None, allowed: tuple[str, ...]) -> str | None:
    """单值筛（owner 精确等值——C1 筛选语义；联席/复合行仅「全部负责人」可见）。"""
    if raw is None:
        return None
    value = raw.strip()
    if value != _FILTER_ALL and value not in allowed:
        raise ApiError(
            status_code=400,
            code=CODE_SEMANTICS_PARAM_INVALID,
            message=f"{name} 筛选值越界：{value}",
            detail={"field": name, "invalid": [value], "allowed": list(allowed)},
        )
    return None if value == _FILTER_ALL else value


# ---------- DTO（C1 端点 2/3/5/6 列形照抄；def 列名照抄合同 DTO——alias 承载） ----------


class TermItem(BaseModel):
    """术语行（C1 端点 2 DTO＋读侧派生 expired/expires_display——F60 现算）。

    def 列名照抄合同 DTO（99 §1.1「DTO 字段同名的照抄」）——属性名 def_（Python
    关键字避让），serialization_alias 承载出门形状（R1 响应字段照抄合同）。
    """

    id: int
    term: str
    type: str
    def_: str = Field(serialization_alias="def")
    status: str
    status_key: str
    owner: str
    source: str
    version: int
    expires_at: str | None
    expires_display: str
    expired: bool


class TermListResponse(BaseModel):
    items: list[TermItem]
    total: int
    grand_total: int
    page: int
    page_size: int


class MetricItem(BaseModel):
    """指标行（C1 端点 3 DTO＋读侧 grain_display——存储值不动，裁决 e；def 同 TermItem）。"""

    id: int
    name: str
    mark: str | None
    slot_name: str
    def_: str = Field(serialization_alias="def")
    grain: str
    unit: str
    grain_display: str
    status: list[str]
    owner: str
    source: str
    dispute: str | None


class MetricListResponse(BaseModel):
    items: list[MetricItem]
    total: int
    grand_total: int
    page: int
    page_size: int


class ObjectItem(BaseModel):
    """对象行（C1 端点 5 DTO——owner/version null 前端渲染「—（未落）」）。"""

    id: int
    obj: str
    attr: str | None
    status: str
    owner: str | None
    source: str
    version: int | None


class ObjectListResponse(BaseModel):
    items: list[ObjectItem]
    total: int
    grand_total: int
    page: int
    page_size: int


class RelationItem(BaseModel):
    """关系行（C1 端点 6 DTO——对象读面的关系账引用行）。"""

    id: int
    rel: str
    read: str
    source: str


class RelationListResponse(BaseModel):
    items: list[RelationItem]
    total: int
    grand_total: int
    page: int
    page_size: int


# ---------- 端点（C1 端点 2/3/5/6；全员可见——CurrentActor 身份桩无组闸） ----------


@router.get("/terms", response_model=TermListResponse)
async def list_terms(
    service: SemanticsDep,
    _actor: CurrentActor,
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    page_size: Annotated[int, Query(ge=1, alias="pageSize")] = DEFAULT_PAGE_SIZE,
    keyword: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    owner: Annotated[str | None, Query()] = None,
) -> TermListResponse:
    """业务术语清单（C1 端点 2；别名命中＝keyword 扫类型展示串「别名 → X」族）。"""
    result = await service.list_terms(
        keyword=keyword, status=_parse_multi("status", status, TERM_STATUS_KEYS),
        owner=_parse_single("owner", owner, TERM_OWNERS), page=page, page_size=page_size,
    )
    today = now().date()
    items = []
    for row in result.items:
        expired, expires_display = term_expiry(row.status_key, row.expires_at, today)
        items.append(
            TermItem(
                id=row.id, term=row.term, type=row.type, def_=row.def_,
                status=row.status, status_key=row.status_key, owner=row.owner,
                source=row.source, version=row.version,
                expires_at=row.expires_at.isoformat() if row.expires_at else None,
                expires_display=expires_display, expired=expired,
            )
        )
    return TermListResponse(
        items=items, total=result.total, grand_total=result.grand_total,
        page=result.page, page_size=result.page_size,
    )


@router.get("/metrics", response_model=MetricListResponse)
async def list_metrics(
    service: SemanticsDep,
    _actor: CurrentActor,
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    page_size: Annotated[int, Query(ge=1, alias="pageSize")] = DEFAULT_PAGE_SIZE,
    keyword: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    owner: Annotated[str | None, Query()] = None,
) -> MetricListResponse:
    """指标口径清单（C1 端点 3；grain_display＝C1 页签列形读侧拼装）。"""
    result = await service.list_metrics(
        keyword=keyword, status=_parse_multi("status", status, METRIC_STATUS_VALUES),
        owner=_parse_single("owner", owner, METRIC_OWNERS), page=page, page_size=page_size,
    )
    items = [
        MetricItem(
            id=row.id, name=row.name, mark=row.mark, slot_name=row.slot_name,
            def_=row.def_, grain=row.grain, unit=row.unit,
            grain_display=metric_grain_display(row.grain, row.unit),
            status=list(row.status), owner=row.owner, source=row.source,
            dispute=row.dispute,
        )
        for row in result.items
    ]
    return MetricListResponse(
        items=items, total=result.total, grand_total=result.grand_total,
        page=result.page, page_size=result.page_size,
    )


@router.get("/objects", response_model=ObjectListResponse)
async def list_objects(
    service: SemanticsDep,
    _actor: CurrentActor,
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    page_size: Annotated[int, Query(ge=1, alias="pageSize")] = DEFAULT_PAGE_SIZE,
    keyword: Annotated[str | None, Query()] = None,
) -> ObjectListResponse:
    """业务对象清单（C1 端点 5——对象与关系账的对象表）。"""
    result = await service.list_objects(keyword=keyword, page=page, page_size=page_size)
    return ObjectListResponse(
        items=[
            ObjectItem(
                id=row.id, obj=row.obj, attr=row.attr, status=row.status,
                owner=row.owner, source=row.source, version=row.version,
            )
            for row in result.items
        ],
        total=result.total, grand_total=result.grand_total,
        page=result.page, page_size=result.page_size,
    )


@router.get("/relations", response_model=RelationListResponse)
async def list_relations(
    service: SemanticsDep,
    _actor: CurrentActor,
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    page_size: Annotated[int, Query(ge=1, alias="pageSize")] = DEFAULT_PAGE_SIZE,
    keyword: Annotated[str | None, Query()] = None,
) -> RelationListResponse:
    """对象关系清单（C1 端点 6——对象读面的关系账引用行）。"""
    result = await service.list_relations(keyword=keyword, page=page, page_size=page_size)
    return RelationListResponse(
        items=[
            RelationItem(id=row.id, rel=row.rel, read=row.read, source=row.source)
            for row in result.items
        ],
        total=result.total, grand_total=result.grand_total,
        page=result.page, page_size=result.page_size,
    )
