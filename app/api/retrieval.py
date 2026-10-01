"""api.retrieval —— /api/retrieval 路由族（D2-搜索与回答.md 合同，2 条路由）。

形状注记：
- 响应字段按 00 §14-R1 裁决统一 snake_case（D2 册主体 camelCase——本端点即
  真实接线直接落 snake：semanticTopK→semantic_top_k、earlyStop→early_stop、
  citationFormat→citation_format、pendingChange→pending_change、
  changeRequestId→change_request_id；qa_behavior 五字段合同已 snake 照抄）。
  query 参数无（两端点零分页）。
- version.updated_at 为展示列（R2 空格分隔「YYYY-MM-DD HH:mm」——D2 示例
  「2026-09-25 10:12」同形；机器时间在域层，展示串接口层拼装）。
- 权限：D 组页面仅「平台运维」可见（D2 权限行）——组闸复用 SettingsActor
  （设置中心组）；未认证 401、无权 403（错误包 00 §3.1，装配在 errors.py）。
- 阶段 1 过渡＝提交即生效（D2 端点 2 生效链注记）：服务端记审计＋版本推进，
  无 A3/C3 落点；pending_change 恒 null（无审批等待期——驳回清空/批准后保留
  至生效的两态语义挂 A3 接入批兑现，票面差异登记）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import RetrievalDep, SecurityDep, SettingsActor
from app.domains.retrieval import ConfigSnapshot
from app.domains.security import AuditRow
from app.infra.clock import DISPLAY_FMT

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])


# ---------- 响应模型（六配置节＋version 元信息节——合同「七个配置节」计数含 version） ----------


class OrderLevelItem(BaseModel):
    level: int
    enabled: bool


class OrderSectionBody(BaseModel):
    levels: list[OrderLevelItem]
    early_stop: bool


class ParamsSectionBody(BaseModel):
    semantic_top_k: int
    keyword_top_k: int
    merge: str
    top_n: int


class FallbackSectionBody(BaseModel):
    strategy: str
    text: str


class ConfidenceThresholdsBody(BaseModel):
    high: float
    low: float


class QaBehaviorBody(BaseModel):
    faq_direct_hit: bool
    refuse_threshold: float
    clarify_strategy: str
    confidence_thresholds: ConfidenceThresholdsBody
    faq_expand_rounds: int


class ConfigSectionsBody(BaseModel):
    """六配置节（端点 1 响应主体＝端点 2 响应 config 段同形）。"""

    order: OrderSectionBody
    params: ParamsSectionBody
    rerank: str
    citation_format: str
    fallback: FallbackSectionBody
    qa_behavior: QaBehaviorBody


class VersionInfo(BaseModel):
    no: str
    updated_at: str  # 展示串（R2——D2 示例「2026-09-25 10:12」同形）
    updated_by: str
    via: str | None  # 生效变动单号；种子版本 None（非变更产生）


class PendingChangeInfo(BaseModel):
    """在途变更摘要（A3 接入批投影 #CFG 在途单——阶段 1 恒 null，形状预留）。"""

    id: str
    sections: list[str]
    submitted_at: str


class ConfigResponse(ConfigSectionsBody):
    """端点 1：全量生效配置（七节＝version＋六配置节；待审 patch 不进响应）。"""

    version: VersionInfo
    pending_change: PendingChangeInfo | None = None  # 阶段 1 恒 null（提交即生效）


class ChangeRequestBody(BaseModel):
    """端点 2 入参（patch＝变更后的配置节映射；校验在域——400 带字段与允许区间）。"""

    patch: dict[str, Any]


class ChangeRequestResponse(BaseModel):
    """端点 2：合同冻结字段（changeRequestId/state）＋票面追加的新配置与版本。"""

    change_request_id: str
    state: str
    config: ConfigSectionsBody
    version: VersionInfo


def _sections_body(snapshot: ConfigSnapshot) -> ConfigSectionsBody:
    qa = snapshot.qa_behavior
    return ConfigSectionsBody(
        order=OrderSectionBody(
            levels=[
                OrderLevelItem(level=lv.level, enabled=lv.enabled)
                for lv in snapshot.order.levels
            ],
            early_stop=snapshot.order.early_stop,
        ),
        params=ParamsSectionBody(
            semantic_top_k=snapshot.params.semantic_top_k,
            keyword_top_k=snapshot.params.keyword_top_k,
            merge=snapshot.params.merge,
            top_n=snapshot.params.top_n,
        ),
        rerank=snapshot.rerank,
        citation_format=snapshot.citation_format,
        fallback=FallbackSectionBody(
            strategy=snapshot.fallback.strategy, text=snapshot.fallback.text
        ),
        qa_behavior=QaBehaviorBody(
            faq_direct_hit=qa.faq_direct_hit,
            refuse_threshold=qa.refuse_threshold,
            clarify_strategy=qa.clarify_strategy,
            confidence_thresholds=ConfidenceThresholdsBody(
                high=qa.confidence_thresholds.high, low=qa.confidence_thresholds.low
            ),
            faq_expand_rounds=qa.faq_expand_rounds,
        ),
    )


def _version_info(no: str, updated_at: str, updated_by: str, via: str | None) -> VersionInfo:
    return VersionInfo(no=no, updated_at=updated_at, updated_by=updated_by, via=via)


# ---------- 端点 1：GET /config ----------


@router.get("/config", response_model=ConfigResponse)
async def get_config(
    service: RetrievalDep,
    _actor: SettingsActor,
) -> ConfigResponse:
    """读取当前生效配置全量快照（七节；首次读取自动落种子——合同默认值 v1）。"""
    snapshot = await service.effective_config()
    return ConfigResponse(
        **_sections_body(snapshot).model_dump(),
        version=_version_info(
            no=snapshot.version.no,
            updated_at=snapshot.version.updated_at.strftime(DISPLAY_FMT),
            updated_by=snapshot.version.updated_by,
            via=snapshot.version.via,
        ),
        pending_change=None,  # 阶段 1 恒 null（提交即生效——两态语义挂 A3 接入批）
    )


# ---------- 端点 2：POST /change-requests ----------


@router.post("/change-requests", response_model=ChangeRequestResponse, status_code=202)
async def submit_change_request(
    body: ChangeRequestBody,
    service: RetrievalDep,
    security: SecurityDep,
    actor: SettingsActor,
) -> ChangeRequestResponse:
    """提交变更申请（阶段 1＝受理即生效：版本推进＋via 回链；在途单 409）。

    受理＝校验（节键白名单/数值域——400 retrieval_param_invalid 带区间）→
    新版本落库 → 生效指针切换；B12 审计（retrieval.config_changed）在服务
    成功返回后落笔（P0-05 gateway 先例——失败路径不达审计行）。
    """
    receipt = await service.submit_change_request(body.patch, updated_by=actor.who)
    await security.audit(
        AuditRow(
            who=actor.who,
            action="retrieval.config_changed",
            content=(
                f"检索配置变更受理并生效：{receipt.change_request_id}，"
                f"推进版本 {receipt.version.no}，变更节 {'、'.join(receipt.sections)}"
            ),
        )
    )
    return ChangeRequestResponse(
        change_request_id=receipt.change_request_id,
        state=receipt.state,
        config=_sections_body(receipt.config),
        version=_version_info(
            no=receipt.version.no,
            updated_at=receipt.version.updated_at.strftime(DISPLAY_FMT),
            updated_by=receipt.version.updated_by,
            via=receipt.version.via,
        ),
    )
