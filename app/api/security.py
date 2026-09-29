"""api.security —— /api/security 路由族（D3 册合同；本票只落审计相关骨架）。

D3 整页（端点 1–13）属阶段 2 前开工闸，随 D3 整页票另落；本票按 P0-04
只取身份/审计相关部分：端点 14 audit-logs 骨架（身份桩依赖＋B12 写口的
读面往返）。

形状注记：
- 响应字段按 00 §14-R1 裁决统一 snake_case（D3 册现 camelCase，迁移批本
  端点即真实接线，直接落 snake；query 参数 page/pageSize 保留现拼写——R1 原文）。
- items 列形 time/who/action/digest 为 D3 端点 14 合同值；digest＝SM3 指纹，
  正文（content）永不出门（00 §8.1）。
- time 序列化为 ISO 8601 无时区后缀（00 §1.4 机器时间戳——审计 time 是
  排序键，idx(time desc)）。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import SecurityDep, SettingsActor
from app.domains.security import AuditLogView
from app.infra.clock import ISO_FMT

router = APIRouter(prefix="/api/security", tags=["security"])

DEFAULT_PAGE = 1  # 00 §4.1
DEFAULT_PAGE_SIZE = 20  # D5 先例（00 §4.1/R9）


class AuditLogItem(BaseModel):
    """单条留痕（D3 端点 14 items 列形——正文不出门）。"""

    time: str
    who: str
    action: str
    digest: str


class AuditLogsResponse(BaseModel):
    """audit-logs 响应（items/total/page/page_size——R1 snake、R3 total 筛选后）。"""

    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int


def _to_item(view: AuditLogView) -> AuditLogItem:
    return AuditLogItem(
        time=view.time.strftime(ISO_FMT),
        who=view.who,
        action=view.action,
        digest=view.digest,
    )


@router.get("/audit-logs", response_model=AuditLogsResponse)
async def list_audit_logs(
    service: SecurityDep,
    actor: SettingsActor,
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    page_size: Annotated[int, Query(ge=1, alias="pageSize")] = DEFAULT_PAGE_SIZE,
) -> AuditLogsResponse:
    """操作留痕（D3 端点 14：SM3 摘要，分页；设置中心组＝运维角色）。"""
    result = await service.audit_logs(page=page, page_size=page_size)
    return AuditLogsResponse(
        items=[_to_item(view) for view in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )
