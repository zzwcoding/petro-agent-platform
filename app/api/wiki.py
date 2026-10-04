"""api.wiki —— /api/wiki 路由族（B4-报告百科.md v0.4 合同，2 条读路由；P2-04）。

形状注记：
- 响应字段 snake_case（00 §14-R1——同 D1/D3/B1 先例）。
- 权限：B4 页全员可见（roles.js MENU B4 无 roles 限制）——require 式声明
  一行（CurrentActor）按 Owner 拍板口径预埋（全员可读预埋期，角色管理以后
  做；401＝身份解析失败，403 留给基础设施层越权）；身份桩依赖只解析身份。
- v0.4 纯读（Owner 2026-10-04 拍板：版本治理整体撤除）——端点 3（版本列
  表）/端点 4（回滚）删端，端点 2 撤 `?version=N`（恒当前版）；零写操作，
  B12 审计随写面撤除不再挂（读面不留痕——00 §8 写口纪律）。
- status 两态服务端按当前版正文 `[[flag:]]` 有无判定（行为规则 5 服务端
  组装——前端零拼装业务文案）。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import CurrentActor, WikiDep
from app.domains.derivatives import (
    RelatedObjectView,
    WikiPageDetail,
    WikiPageListItem,
)

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
    updated: str
    status: str


class WikiPagesResponse(BaseModel):
    items: list[WikiPageListItemBody]
    total: int


@router.get("/pages", response_model=WikiPagesResponse)
async def list_pages(
    service: WikiDep,
    _actor: CurrentActor,  # 权限预埋一行（B4 全员可读预埋期——Owner 拍板口径）
    lib: Annotated[str, Query()] = "all",
    keyword: Annotated[str, Query()] = "",
) -> WikiPagesResponse:
    """百科页目录（所属库＋关键词筛选——keyword 匹配题名/来源报告/所属库三字段；
    按 updated 倒序；开关关未生成的报告不出现；current_version＝重建计数，
    v0.4 无版本历史语义；total＝全量计数——B4 v0.4 DTO 注记，筛选前先数）。"""
    total = await service.count_pages()
    rows: list[WikiPageListItem] = await service.list_pages(lib=lib, keyword=keyword or None)
    return WikiPagesResponse(
        items=[
            WikiPageListItemBody(
                id=r.id, title=r.title, lib=r.lib,
                source_report=SourceReportBody(id=r.source_report_id,
                                               doc=r.source_report_doc),
                current_version=r.current_version,
                updated=r.updated, status=r.status,
            )
            for r in rows
        ],
        total=total,
    )


# ---------- 端点 2：GET /pages/{pageId} 全文（恒当前版） ----------


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
    _actor: CurrentActor,  # 权限预埋一行（B4 全员可读预埋期——Owner 拍板口径）
) -> WikiPageDetailResponse:
    """百科页全文（元数据字段表＋自由 markdown 正文 content＋claims[]＋
    glossary_terms[]；恒当前版快照——v0.4 撤 ?version=N，无历史版可读）。"""
    view: WikiPageDetail = await service.page_detail(page_id)
    return WikiPageDetailResponse(
        id=view.id, title=view.title, lib=view.lib, slug=view.slug,
        digest=view.digest,
        source_report=SourceReportBody(id=view.source_report_id,
                                       doc=view.source_report_doc),
        current_version=view.current_version,
        updated=view.updated, status=view.status,
        generation_source=view.generation_source, operator=view.operator,
        related_objects=[_related_object(r) for r in view.related_objects],
        content=view.content,
        claims=[ClaimBody(**c) for c in view.claims],
        glossary_terms=[GlossaryTermBody(**g) for g in view.glossary_terms],
    )


def _related_object(r: RelatedObjectView) -> RelatedObjectBody:
    return RelatedObjectBody(type=r.type, id=r.id, summary=r.summary, links=r.links)
