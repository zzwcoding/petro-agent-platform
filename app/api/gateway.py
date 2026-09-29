"""api.gateway —— /api/gateway 路由族（D1-模型与线路.md 合同，7 条路由）。

形状注记：
- 响应字段按 00 §14-R1 裁决统一 snake_case（D1 册现 camelCase，本端点即
  真实接线，直接落 snake；query 参数 page/pageSize 保留现拼写——R1 原文）。
  演练 result 内的 ledgerRow 同批落 ledger_row（同 spend-logs item 形）。
- 权限：D 组页面仅「平台运维」可见（D1 权限行）——组闸复用 SettingsActor
  （设置中心组）；未认证 401、无权 403（错误包 00 §3.1，装配在 errors.py）。
- 数据形状红线（D1 端点 4）：token 两个整数、耗时毫秒整数、花费元数值——
  禁返回拼接好的展示串，格式化一律前端做。
- 演练节奏（~600ms/步）由服务端任务驱动，前端只轮询（00 §5.2：演示动画
  不入合同）。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import GatewayDep, SecurityDep, SettingsActor
from app.domains.gateway import GatewayParams, SpendFilter, SpendView
from app.domains.security import AuditRow
from app.infra.clock import ISO_FMT

router = APIRouter(prefix="/api/gateway", tags=["gateway"])

DEFAULT_PAGE_SIZE = 15  # D1 册合同值（R9：新增分页默认 20，既有册现值保留）


# ---------- 端点 1：GET /models ----------


class ModelItem(BaseModel):
    """model_list 单行（D1 端点 1 列形；key/role 由 routing 派生）。"""

    key: str
    name: str
    alias: str
    role: str
    access: str
    note: str


class ModelsResponse(BaseModel):
    gateway: dict[str, str]
    models: list[ModelItem]


@router.get("/models", response_model=ModelsResponse)
async def list_models(
    service: GatewayDep,
    _actor: SettingsActor,
) -> ModelsResponse:
    """模型清单＋网关运行态（页头徽标；running|degraded|down）。"""
    view = service.models()
    return ModelsResponse(
        gateway={"status": view.gateway_status},
        models=[
            ModelItem(
                key=m.key,
                name=m.name,
                alias=m.alias,
                role=m.role,
                access=m.access,
                note=m.note,
            )
            for m in view.models
        ],
    )


# ---------- 端点 2/3：GET · PUT /config ----------


class GatewayParamsBody(BaseModel):
    """调用参数四件（数值边界校验在域——400 错误体带字段与允许区间）。"""

    allowed_fails: int
    cooldown_seconds: int
    num_retries: int
    request_timeout: int


class ConfigSaveBody(BaseModel):
    params: GatewayParamsBody


class ConfigResponse(BaseModel):
    params: GatewayParamsBody
    yaml: str


@router.get("/config", response_model=ConfigResponse)
async def get_config(
    service: GatewayDep,
    _actor: SettingsActor,
) -> ConfigResponse:
    """读取调用参数＋配置文件全文（密钥保持 ${VAR} 占位符不落明文）。"""
    view = service.gateway_config()
    return ConfigResponse(params=GatewayParamsBody(**view.params.as_mapping()), yaml=view.yaml)


@router.put("/config", response_model=ConfigResponse)
async def save_config(
    body: ConfigSaveBody,
    service: GatewayDep,
    security: SecurityDep,
    actor: SettingsActor,
) -> ConfigResponse:
    """保存调用参数（档①直改即生效——写回 models.yaml 并热加载；快照为唯一真值）。"""
    view = service.save_gateway_config(
        GatewayParams(
            allowed_fails=body.params.allowed_fails,
            cooldown_seconds=body.params.cooldown_seconds,
            num_retries=body.params.num_retries,
            request_timeout=body.params.request_timeout,
        )
    )
    await security.audit(  # B12 横切留痕（写操作）——经唯一写口，gateway 不依赖 security
        AuditRow(
            who=actor.who,
            action="gateway.config.saved",
            content=(
                f"网关调用参数保存：allowed_fails={view.params.allowed_fails}, "
                f"cooldown_seconds={view.params.cooldown_seconds}, "
                f"num_retries={view.params.num_retries}, "
                f"request_timeout={view.params.request_timeout}"
            ),
        )
    )
    return ConfigResponse(params=GatewayParamsBody(**view.params.as_mapping()), yaml=view.yaml)


# ---------- 端点 4：GET /spend-logs ----------


class SpendLogItem(BaseModel):
    """记账流水单行（数据形状红线：整数毫秒/两整数 token/元数值）。"""

    id: str
    time: str
    model_key: str
    alias: str
    input_tokens: int
    output_tokens: int
    first_ms: int
    total_ms: int
    cost_yuan: float
    fallback: bool
    note: str


class SpendLogsResponse(BaseModel):
    items: list[SpendLogItem]
    total: int
    page: int
    page_size: int


def _to_spend_item(view: SpendView) -> SpendLogItem:
    return SpendLogItem(
        id=view.id,
        time=view.time.strftime(ISO_FMT),
        model_key=view.model_key,
        alias=view.alias,
        input_tokens=view.input_tokens,
        output_tokens=view.output_tokens,
        first_ms=view.first_ms,
        total_ms=view.total_ms,
        cost_yuan=view.cost_yuan,
        fallback=view.fallback,
        note=view.note,
    )


@router.get("/spend-logs", response_model=SpendLogsResponse)
async def list_spend_logs(
    service: GatewayDep,
    _actor: SettingsActor,
    model: Annotated[str, Query()] = "all",
    range: Annotated[str, Query()] = "all",
    keyword: Annotated[str, Query()] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, alias="pageSize")] = DEFAULT_PAGE_SIZE,
) -> SpendLogsResponse:
    """记账流水分页（排序恒 time 倒序；keyword 匹配调用号/备注）。"""
    result = await service.spend_logs(
        SpendFilter(model=model, range=range, keyword=keyword or None),
        page=page,
        page_size=page_size,
    )
    return SpendLogsResponse(
        items=[_to_spend_item(v) for v in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


# ---------- 端点 5/6/7：故障演练三连 ----------


class DrillStartResponse(BaseModel):
    drill_id: str


class DrillNodeItem(BaseModel):
    key: str
    label: str
    state: str
    note: str


class DrillProgressResponse(BaseModel):
    drill_id: str
    status: str
    nodes: list[DrillNodeItem]
    result: dict[str, object] | None


class DrillHistoryItem(BaseModel):
    id: str
    time: str
    summary: str


@router.post("/drills", response_model=DrillStartResponse, status_code=202)
async def start_drill(
    service: GatewayDep,
    _actor: SettingsActor,
) -> DrillStartResponse:
    """启动故障演练（202 受理；重入 409；演练即真实流量——真切换一次模型留痕）。

    演练窗口校验（D1 行为规则 2「预留，403 语义」）挂演练窗口配置批。
    """
    handle = await service.start_drill()
    return DrillStartResponse(drill_id=handle.drill_id)


@router.get("/drills/{drill_id}", response_model=DrillProgressResponse)
async def get_drill(
    drill_id: str,
    service: GatewayDep,
    _actor: SettingsActor,
) -> DrillProgressResponse:
    """轮询演练任务进度与结果（不存在/已过期 404）。"""
    progress = await service.drill(drill_id)
    return DrillProgressResponse(
        drill_id=progress.drill_id,
        status=progress.status,
        nodes=[DrillNodeItem(**node) for node in progress.nodes],
        result=progress.result,
    )


@router.get("/drills", response_model=list[DrillHistoryItem])
async def list_drills(
    service: GatewayDep,
    _actor: SettingsActor,
) -> list[DrillHistoryItem]:
    """演练历史倒序（summary 含阈值与冷却参数）。"""
    return [
        DrillHistoryItem(id=s.id, time=s.time.strftime(ISO_FMT), summary=s.summary)
        for s in await service.drill_history()
    ]
