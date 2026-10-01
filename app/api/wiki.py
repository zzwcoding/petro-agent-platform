"""api.wiki —— /api/wiki 路由族（B4-报告百科.md v0.3 合同，4 条路由；P1-02b）。

形状注记：
- 响应字段 snake_case（00 §14-R1——同 D1/D3/B1 先例）。
- 权限：B4 页全员可见（roles.js MENU B4 无 roles 限制）——组闸不做，身份桩
  依赖（CurrentActor）只解析身份（未认证 401）；回滚 operator 由服务端会话
  解析，不信任前端（B4 行为规则 7）。
- 只读三件（目录/全文/版本列表）＋唯一写操作回滚（F52）；diff 不实现（v0.3
  已撤）——版本对比由 ?version=N 查看任意版全文承接。
- B12：回滚写操作经 security.audit 留痕（api 层编排——P0-05 gateway 同款；
  版本行 operator 为 B4 内嵌留痕，双轨不冲突）。
- 端点 2 `?version=N`＝查看任意版全文快照（同 DTO 形状；版本不存在 404）。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import CurrentActor, SecurityDep, WikiDep
from app.domains.derivatives import (
    RelatedObjectView,
    RollbackReceipt,
    WikiPageDetail,
    WikiPageListItem,
    WikiVersionItem,
)
from app.domains.security.domain import AuditRow

router = APIRouter(prefix="/api/wiki", tags=["wiki"])


# ---------- 端点 1：GET /pages 目录 ----------


class SourceReportBody(BaseModel):
    id: str
    doc: str


class WikiPageListItemBody(BaseModel):
    id: str
    title: str
    lib: str
    source_report: SourceReportBody
    current_version: int
    version_count: int
    updated: str
    status: str


class WikiPagesResponse(BaseModel):
    items: list[WikiPageListItemBody]
    total: int


@router.get("/pages", response_model=WikiPagesResponse)
async def list_pages(
    service: WikiDep,
    _actor: CurrentActor,
    lib: Annotated[str, Query()] = "all",
    keyword: Annotated[str, Query()] = "",
) -> WikiPagesResponse:
    """百科页目录（所属库＋关键词筛选——keyword 匹配题名/来源报告/所属库三字段；
    按 updated 倒序；开关关未生成的报告不出现）。"""
    rows: list[WikiPageListItem] = await service.list_pages(lib=lib, keyword=keyword or None)
    return WikiPagesResponse(
        items=[
            WikiPageListItemBody(
                id=r.id, title=r.title, lib=r.lib,
                source_report=SourceReportBody(id=r.source_report_id,
                                               doc=r.source_report_doc),
                current_version=r.current_version, version_count=r.version_count,
                updated=r.updated, status=r.status,
            )
            for r in rows
        ],
        total=len(rows),
    )


# ---------- 端点 2：GET /pages/{pageId} 全文（?version=N 任意版快照） ----------


class ClaimBody(BaseModel):
    claim_id: str
    text: str
    evidence_chunk_ids: list[str]


class GlossaryTermBody(BaseModel):
    word: str
    kind: str
    ref_id: int
    card: dict[str, object]


class RelatedObjectBody(BaseModel):
    type: str
    id: str
    summary: str
    links: list[str]


class WikiPageDetailResponse(BaseModel):
    id: str
    title: str
    lib: str
    slug: str
    digest: str | None
    source_report: SourceReportBody
    current_version: int
    version_count: int
    updated: str
    status: str
    generation_source: str
    operator: str | None
    related_objects: list[RelatedObjectBody]
    content: str
    claims: list[ClaimBody]
    glossary_terms: list[GlossaryTermBody]


@router.get("/pages/{page_id}", response_model=WikiPageDetailResponse)
async def page_detail(
    page_id: str,
    service: WikiDep,
    _actor: CurrentActor,
    version: Annotated[int | None, Query()] = None,
) -> WikiPageDetailResponse:
    """百科页全文（元数据＋自由 markdown 正文＋claims[]＋glossary_terms[]）；
    可选 ?version=N＝查看任意版全文快照（content/claims/glossary_terms/updated/
    generation_source/operator/status 取该版固化值）。"""
    view: WikiPageDetail = await service.page_detail(page_id, version=version)
    return _detail_response(view)


def _detail_response(view: WikiPageDetail) -> WikiPageDetailResponse:
    return WikiPageDetailResponse(
        id=view.id, title=view.title, lib=view.lib, slug=view.slug,
        digest=view.digest,
        source_report=SourceReportBody(id=view.source_report_id,
                                       doc=view.source_report_doc),
        current_version=view.current_version, version_count=view.version_count,
        updated=view.updated, status=view.status,
        generation_source=view.generation_source, operator=view.operator,
        related_objects=[_related_object(r) for r in view.related_objects],
        content=view.content,
        claims=[ClaimBody(**c) for c in view.claims],
        glossary_terms=[GlossaryTermBody(**g) for g in view.glossary_terms],
    )


def _related_object(r: RelatedObjectView) -> RelatedObjectBody:
    return RelatedObjectBody(type=r.type, id=r.id, summary=r.summary, links=r.links)


# ---------- 端点 3：GET /pages/{pageId}/versions 版本列表 ----------


class WikiVersionItemBody(BaseModel):
    v: int
    date: str
    source: str
    desc: str
    operator: str | None
    task_no: str | None
    current: bool


class WikiVersionsResponse(BaseModel):
    items: list[WikiVersionItemBody]
    total: int


@router.get("/pages/{page_id}/versions", response_model=WikiVersionsResponse)
async def page_versions(
    page_id: str,
    service: WikiDep,
    _actor: CurrentActor,
) -> WikiVersionsResponse:
    """版本列表（来源四态/更新时间/操作人/经由单号/说明/当前版标；版本号升序）。"""
    rows: list[WikiVersionItem] = await service.versions(page_id)
    return WikiVersionsResponse(
        items=[
            WikiVersionItemBody(
                v=r.v, date=r.date, source=r.source, desc=r.desc,
                operator=r.operator, task_no=r.task_no, current=r.current,
            )
            for r in rows
        ],
        total=len(rows),
    )


# ---------- 端点 4：POST /pages/{pageId}/rollback 一键回滚 ----------


class RollbackBody(BaseModel):
    target_version: int


class RollbackResponse(BaseModel):
    page_id: str
    current_version: int
    new_version: WikiVersionItemBody
    status: str
    banner: str


@router.post("/pages/{page_id}/rollback", response_model=RollbackResponse)
async def rollback(
    page_id: str,
    body: RollbackBody,
    service: WikiDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> RollbackResponse:
    """一键回滚（＝追加「回滚」来源新版本，可指定任意目标版——F52 ①③；
    历史版本只追加、永不变改，回滚本身也可再回滚；防呆 409）。"""
    receipt: RollbackReceipt = await service.rollback(
        page_id, body.target_version, actor.who
    )
    await security.audit(  # B12 横切留痕——经唯一写口，derivatives 不依赖 security
        AuditRow(
            who=actor.who,
            action="wiki.page.rolled_back",
            content=(
                f"百科页回滚：{page_id} → 恢复 v{body.target_version}"
                f"（记为新版本 v{receipt.current_version}，来源「回滚」）"
            ),
        )
    )
    return RollbackResponse(
        page_id=receipt.page_id,
        current_version=receipt.current_version,
        new_version=WikiVersionItemBody(
            v=receipt.new_version.v, date=receipt.new_version.date,
            source=receipt.new_version.source, desc=receipt.new_version.desc,
            operator=receipt.new_version.operator,
            task_no=receipt.new_version.task_no, current=receipt.new_version.current,
        ),
        status=receipt.status,
        banner=receipt.banner,
    )
