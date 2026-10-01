"""api.gateway —— /api/gateway 路由族（D1-模型与线路.md 合同，8 条路由）。

形状注记：
- 响应字段按 00 §14-R1 裁决统一 snake_case（D1 册现 camelCase，本端点即
  真实接线，直接落 snake；query 参数 page/pageSize 保留现拼写——R1 原文）。
  演练 result 内的 ledgerRow 同批落 ledger_row（同 spend-logs item 形）。
- 权限：D 组页面仅「平台运维」可见（D1 权限行）——组闸复用 SettingsActor
  （设置中心组）；未认证 401、无权 403（错误包 00 §3.1，装配在 errors.py）。
- 数据形状红线（D1 端点 4/8）：token 两个整数、耗时毫秒整数、花费元数值——
  禁返回拼接好的展示串，格式化一律前端做。
- 演练节奏（~600ms/步）由服务端任务驱动，前端只轮询（00 §5.2：演示动画
  不入合同）。
- 端点 8（D5 撤页归并批）：聚合/趋势读面＝账本聚合投影，sums 为窗口全量
  合计不随分页截断；caller/model 降序分页，day/month 时序升序全量。
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import GatewayDep, SecurityDep, SettingsActor
from app.domains.gateway import (
    BudgetThresholds,
    GatewayParams,
    SpendFilter,
    SpendStatsFilter,
    SpendView,
)
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


# ---------- 端点 2/3：GET · PUT /config（D1 v0.2：params 并入预算双阈值六件） ----------


class GatewayParamsBody(BaseModel):
    """调用参数六件（四 yaml 参数＋预算双阈值；数值边界校验在域——400 错误体带字段与区间）。"""

    allowed_fails: int
    cooldown_seconds: int
    num_retries: int
    request_timeout: int
    per_call_cost_limit_yuan: float  # 单次调用成本上限（元）——>=0，默认 0.05（F2 改注）
    gateway_budget_yuan_per_month: float  # 累计预算 GATEWAY_BUDGET（元/月）——>=0


class ConfigSaveBody(BaseModel):
    params: GatewayParamsBody


class ConfigResponse(BaseModel):
    params: GatewayParamsBody
    yaml: str


def _params_body(view: Any) -> GatewayParamsBody:
    """服务端快照 → DTO（yaml 四参数＋预算双阈值六件同框——D1 v0.2 形状）。"""
    return GatewayParamsBody(
        allowed_fails=view.params.allowed_fails,
        cooldown_seconds=view.params.cooldown_seconds,
        num_retries=view.params.num_retries,
        request_timeout=view.params.request_timeout,
        per_call_cost_limit_yuan=view.budget.per_call_cost_limit_yuan,
        gateway_budget_yuan_per_month=view.budget.gateway_budget_yuan_per_month,
    )


@router.get("/config", response_model=ConfigResponse)
async def get_config(
    service: GatewayDep,
    _actor: SettingsActor,
) -> ConfigResponse:
    """读取调用参数＋预算双阈值＋配置文件全文（密钥保持 ${VAR} 占位符不落明文）。"""
    view = await service.gateway_config()
    return ConfigResponse(params=_params_body(view), yaml=view.yaml)


@router.put("/config", response_model=ConfigResponse)
async def save_config(
    body: ConfigSaveBody,
    service: GatewayDep,
    security: SecurityDep,
    actor: SettingsActor,
) -> ConfigResponse:
    """保存调用参数＋预算双阈值（档①直改即生效——写回 models.yaml 并热加载；快照为唯一真值）。

    预算双阈值＝熔断判据输入（F2 改注）：直接保存即生效、对后续调用生效不回溯；
    熔断语义不变（触顶改路由降级组 petro-lite、改路由不拒绝、单向置位）。
    """
    view = await service.save_gateway_config(
        GatewayParams(
            allowed_fails=body.params.allowed_fails,
            cooldown_seconds=body.params.cooldown_seconds,
            num_retries=body.params.num_retries,
            request_timeout=body.params.request_timeout,
        ),
        BudgetThresholds(
            per_call_cost_limit_yuan=body.params.per_call_cost_limit_yuan,
            gateway_budget_yuan_per_month=body.params.gateway_budget_yuan_per_month,
        ),
    )
    await security.audit(  # B12 横切留痕（写操作）——经唯一写口，gateway 不依赖 security
        AuditRow(
            who=actor.who,
            action="gateway.config.saved",
            content=(
                f"网关调用参数保存：allowed_fails={view.params.allowed_fails}, "
                f"cooldown_seconds={view.params.cooldown_seconds}, "
                f"num_retries={view.params.num_retries}, "
                f"request_timeout={view.params.request_timeout}, "
                f"per_call_cost_limit_yuan={view.budget.per_call_cost_limit_yuan}, "
                f"gateway_budget_yuan_per_month={view.budget.gateway_budget_yuan_per_month}"
            ),
        )
    )
    return ConfigResponse(params=_params_body(view), yaml=view.yaml)


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
    caller: str | None = None  # 调用方归因（D1 v0.2；存量行可空）


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
        caller=view.caller,
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


# ---------- 端点 8：GET /spend-stats（D5 撤页归并批——聚合/趋势读面） ----------


class SpendStatsResponse(BaseModel):
    """聚合读面（items 行形状随 group_by 切换：caller 值/model_key＋alias/day/month；

    response_model_exclude_none 剥未用维度键——合同 DTO 只携带本维度分组键）。
    """

    group_by: str
    range: str
    items: list[dict[str, Any]]
    sums: dict[str, Any]
    total: int
    page: int
    page_size: int


def _stats_row(view: Any, group_by: str) -> dict[str, Any]:
    """聚合行 → DTO（维度分组键名照合同：caller/model_key＋alias/day/month）。"""
    row: dict[str, Any] = {
        "calls": view.calls,
        "fallback_calls": view.fallback_calls,
        "input_tokens": view.input_tokens,
        "output_tokens": view.output_tokens,
        "cost_yuan": view.cost_yuan,
    }
    if group_by == "caller":
        row["caller"] = view.bucket
    elif group_by == "model":
        row["model_key"] = view.bucket
        row["alias"] = view.alias
    elif group_by == "day":
        row["day"] = view.bucket
    else:
        row["month"] = view.bucket
    return row


@router.get("/spend-stats", response_model=SpendStatsResponse, response_model_exclude_none=True)
async def get_spend_stats(
    service: GatewayDep,
    _actor: SettingsActor,
    group_by: Annotated[str, Query()] = "caller",
    range: Annotated[str, Query()] = "all",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, alias="pageSize")] = DEFAULT_PAGE_SIZE,
) -> SpendStatsResponse:
    """花费聚合/趋势读面（caller/model 花费降序分页；day/month 升序全量；sums 不截断）。"""
    result = await service.spend_stats(
        SpendStatsFilter(group_by=group_by, range=range), page=page, page_size=page_size
    )
    return SpendStatsResponse(
        group_by=result.group_by,
        range=result.range,
        items=[_stats_row(v, result.group_by) for v in result.items],
        sums={
            "calls": result.sums.calls,
            "fallback_calls": result.sums.fallback_calls,
            "cost_yuan": result.sums.cost_yuan,
        },
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
    security: SecurityDep,
    actor: SettingsActor,
) -> DrillStartResponse:
    """启动故障演练（202 受理；重入 409；演练即真实流量——真切换一次模型留痕）。

    演练窗口校验（D1 行为规则 2「预留，403 语义」）挂演练窗口配置批。
    98 卡 `start_drill(actor: Actor)` 的 actor 槽（破坏性操作 who 留痕）在
    接口层兑现：受理即写一条 B12 审计（唯一写口；gateway 域不反向依赖
    security——同 save_config 先例，差异登记 README P0-05 第 10 条）。
    """
    handle = await service.start_drill()
    await security.audit(
        AuditRow(
            who=actor.who,
            action="gateway.drill.started",
            content=f"故障演练受理：{handle.drill_id}（演练即真实流量，真切换一次模型留痕）",
        )
    )
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
