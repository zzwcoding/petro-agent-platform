"""api.faq —— /api/faq 路由族（B3 常见问题库 17 端点，P1-06）。

合同真源（只读引用）：teach-petro-agent/specs/api/B3-常见问题库.md v0.2——
问答清单/详情/新增（负例·空值占位·关联口径·候选回写）/入库前重复校验（非阻断）/
相似问增删（独立检索项即时生效）/合并/停用启用/审核发布（v0.2 增设）/候选问题库/
扫库异步长任务（202＋轮询）/向量比对（三面去重）/候选起草/引用知识起草/
批量导入（两模式＋试校验＋四计数——00 §4.4）/导出（预签名直链）。

鉴权（B3 权限行）：页面全员可见（MENU B3 无 roles）——CurrentActor 身份桩，
无页面组闸；未认证 401（resolve_actor）。B12 审计（关键写端点 api 层留痕——
新增/发布/停用/合并/导入/导出直链签发，faq.* 命名）。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.api.deps import CurrentActor, FaqDep, SecurityDep
from app.api.errors import ApiError
from app.domains.faq import (
    CandidateDraft,
    CandidateItem,
    CandidateList,
    CompareResult,
    DownloadHandle,
    DraftResult,
    FaqCreated,
    FaqList,
    FaqReviewed,
    FaqStateView,
    Hook,
    ImportStats,
    LedgerRef,
    MergeResult,
    ScanHandle,
    ScanProgress,
    SliceRef,
    VersionBumped,
)
from app.domains.security.domain import AuditRow

router = APIRouter(prefix="/api/faq", tags=["faq"])


# ---------- 端点 1：GET /items 问答清单 ----------


class HookBody(BaseModel):
    kind: str
    name: str


class ItemBody(BaseModel):
    id: str
    question: str
    answer: str
    similar_questions: list[str]
    status: str
    hook: HookBody | None


class ItemsResponse(BaseModel):
    items: list[ItemBody]
    total: int
    grand_total: int


def _hook_out(hook: Hook | None) -> HookBody | None:
    return HookBody(kind=hook.kind, name=hook.name) if hook else None


@router.get("/items", response_model=ItemsResponse)
async def list_items(
    service: FaqDep,
    _actor: CurrentActor,
    status: Annotated[str, Query()] = "all",
    keyword: Annotated[str, Query()] = "",
) -> ItemsResponse:
    """问答清单（状态筛＋关键词搜问题/答案/相似问法；创建时间正序——端点 1）。"""
    rows: FaqList = await service.list_entries(status=status, keyword=keyword)
    items = [
        ItemBody(
            id=r.id, question=r.question, answer=r.answer,
            similar_questions=r.similar_questions, status=r.status, hook=_hook_out(r.hook),
        )
        for r in rows.items
    ]
    return ItemsResponse(items=items, total=rows.total, grand_total=rows.grand_total)


# ---------- 端点 2：GET /items/{id} 详情 ----------


class SimilarBody(BaseModel):
    id: str
    text: str


class DetailResponse(BaseModel):
    id: str
    question: str
    answer: str
    status: str
    hook: HookBody | None
    similar_questions: list[SimilarBody]
    maintainer: str
    updated_at: str
    version: int


@router.get("/items/{entry_id}", response_model=DetailResponse)
async def entry_detail(
    entry_id: str,
    service: FaqDep,
    _actor: CurrentActor,
) -> DetailResponse:
    """问答详情（相似问含 id 寻址键＋维护人/更新日期/版本——端点 2）。"""
    row = await service.entry_detail(entry_id)
    return DetailResponse(
        id=row.id, question=row.question, answer=row.answer, status=row.status,
        hook=_hook_out(row.hook),
        similar_questions=[SimilarBody(id=s.id, text=s.text) for s in row.similar_questions],
        maintainer=row.maintainer, updated_at=row.updated_at, version=row.version,
    )


# ---------- 端点 3：POST /items 新增问答 ----------


class CreateBody(BaseModel):
    question: str = ""
    answer: str = ""
    is_negative: bool = False
    hook: HookBody | None = None
    source_candidate_id: str | None = None


class CandidateRefBody(BaseModel):
    id: str
    status: str


class CreateResponse(BaseModel):
    id: str
    status: str
    version: int
    hint: str
    candidate: CandidateRefBody | None


@router.post("/items", response_model=CreateResponse)
async def create_entry(
    body: CreateBody,
    service: FaqDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> CreateResponse:
    """新增问答入库（负例登记/空值占位/关联口径/候选回写——端点 3）。

    v0.2 审核流：恒先进「待审核」，审核发布（端点 17）后才被 A1 消费。
    """
    created: FaqCreated = await service.create_entry(
        body.question,
        body.answer,
        is_negative=body.is_negative,
        hook=Hook(kind=body.hook.kind, name=body.hook.name) if body.hook else None,
        source_candidate_id=body.source_candidate_id,
        actor_who=actor.who,
    )
    await security.audit(  # B12 横切留痕——经唯一写口，faq 不依赖 security
        AuditRow(
            who=actor.who,
            action="faq.entry.created",
            content=f"新增问答「{body.question.strip() or '（未填问题）'}」→ {created.id}"
            f"（{'负例意向，' if body.is_negative else ''}待审核）",
        )
    )
    return CreateResponse(
        id=created.id, status=created.status, version=created.version, hint=created.hint,
        candidate=CandidateRefBody(id=created.candidate.id, status=created.candidate.status)
        if created.candidate
        else None,
    )


# ---------- 端点 4：POST /dup-checks 入库前重复校验 ----------


class DupCheckBody(BaseModel):
    question: str


class DupHitBody(BaseModel):
    id: str
    question: str


class DupCheckResponse(BaseModel):
    hit: DupHitBody | None
    hint: str | None


@router.post("/dup-checks", response_model=DupCheckResponse)
async def dup_check(
    body: DupCheckBody,
    service: FaqDep,
    _actor: CurrentActor,
) -> DupCheckResponse:
    """入库前重复校验（归一化比对、非阻断——端点 4）。"""
    hit, hint = await service.dup_check(body.question)
    return DupCheckResponse(
        hit=DupHitBody(id=hit.id, question=hit.question) if hit else None,
        hint=hint,
    )


# ---------- 端点 5/6：相似问增删 ----------


class SimilarAddBody(BaseModel):
    text: str


class SimilarAddResponse(BaseModel):
    id: str
    text: str
    version: int


@router.post("/items/{entry_id}/similar-questions", response_model=SimilarAddResponse)
async def add_similar(
    entry_id: str,
    body: SimilarAddBody,
    service: FaqDep,
    _actor: CurrentActor,
) -> SimilarAddResponse:
    """添加相似问法（独立检索项，即时生效——端点 5）。"""
    row = await service.add_similar(entry_id, body.text, actor_who=_actor.who)
    return SimilarAddResponse(id=row.id, text=row.text, version=row.version)


class SimilarDeleteResponse(BaseModel):
    version: int
    hint: str


@router.delete("/items/{entry_id}/similar-questions/{sim_id}",
               response_model=SimilarDeleteResponse)
async def remove_similar(
    entry_id: str,
    sim_id: str,
    service: FaqDep,
    _actor: CurrentActor,
) -> SimilarDeleteResponse:
    """删除相似问法（删掉即不再命中——端点 6）。"""
    row: VersionBumped = await service.remove_similar(entry_id, sim_id, actor_who=_actor.who)
    return SimilarDeleteResponse(version=row.version, hint=row.hint)


# ---------- 端点 7：POST /items/{id}/merge 合并相似问 ----------


class MergeBody(BaseModel):
    target_id: str


class MergeTargetBody(BaseModel):
    id: str
    similar_questions_count: int


class MergeResponse(BaseModel):
    from_id: str
    target_id: str
    merged_count: str
    target: MergeTargetBody
    hint: str


@router.post("/items/{entry_id}/merge", response_model=MergeResponse)
async def merge_entry(
    entry_id: str,
    body: MergeBody,
    service: FaqDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> MergeResponse:
    """合并相似问（并入目标条目；被并入条目删除——端点 7）。"""
    row: MergeResult = await service.merge_entries(entry_id, body.target_id, actor_who=actor.who)
    await security.audit(  # B12 横切留痕
        AuditRow(
            who=actor.who,
            action="faq.entry.merged",
            content=f"合并相似问：{row.from_id} 并入 {row.target_id}（{row.merged_count}）",
        )
    )
    return MergeResponse(
        from_id=row.from_id, target_id=row.target_id, merged_count=row.merged_count,
        target=MergeTargetBody(id=row.target_id,
                               similar_questions_count=row.target_similar_questions_count),
        hint=row.hint,
    )


# ---------- 端点 8：POST /items/{id}/state 停用/启用 ----------


class StateBody(BaseModel):
    action: str


class StateResponse(BaseModel):
    id: str
    status: str
    version: int


@router.post("/items/{entry_id}/state", response_model=StateResponse)
async def toggle_state(
    entry_id: str,
    body: StateBody,
    service: FaqDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> StateResponse:
    """停用/启用（口径改版先停用待审；负例行 409——端点 8）。"""
    row: FaqStateView = await service.toggle_state(entry_id, body.action, actor_who=actor.who)
    await security.audit(  # B12 横切留痕
        AuditRow(
            who=actor.who,
            action="faq.entry.state_changed",
            content=f"问答 {entry_id} {'停用' if body.action == 'disable' else '启用'}"
                    f"→ {row.status}（v{row.version}）",
        )
    )
    return StateResponse(id=row.id, status=row.status, version=row.version)


# ---------- 端点 17：POST /items/{id}/review 审核发布/驳回 ----------


class ReviewBody(BaseModel):
    action: str


class ReviewResponse(BaseModel):
    id: str
    status: str
    version: int
    hint: str


@router.post("/items/{entry_id}/review", response_model=ReviewResponse)
async def review_entry(
    entry_id: str,
    body: ReviewBody,
    service: FaqDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> ReviewResponse:
    """审核发布/驳回（v0.2 增设——发布后转 serve/negative 并被 A1 消费；端点 17）。"""
    row: FaqReviewed = await service.review_entry(entry_id, body.action, actor_who=actor.who)
    await security.audit(  # B12 横切留痕（审核发布闸）
        AuditRow(
            who=actor.who,
            action="faq.entry.reviewed",
            content=f"审核{'发布' if body.action == 'publish' else '驳回'}：{entry_id}"
                    f"→ {row.status}（v{row.version}）",
        )
    )
    return ReviewResponse(id=row.id, status=row.status, version=row.version, hint=row.hint)


# ---------- 端点 9：GET /candidates 候选问题库 ----------


class CompareBody(BaseModel):
    verdict: str
    dup_question: str | None
    similarity: float | None
    onto_hit: str | None
    hint: str


class CandidateBody(BaseModel):
    id: str
    question: str
    variants: list[str]
    freq: int
    window: str
    status: str
    compare: CompareBody | None
    draft: str | None
    hook: HookBody | None


class ScanPanelBody(BaseModel):
    running_task_id: str | None
    last_hint: str | None


class CandidatesResponse(BaseModel):
    items: list[CandidateBody]
    total: int
    scan: ScanPanelBody


def _compare_out(row: CandidateItem) -> CompareBody | None:
    cmp: CompareResult | None = row.compare
    if cmp is None:
        return None
    return CompareBody(
        verdict=cmp.verdict, dup_question=cmp.dup_question, similarity=cmp.similarity,
        onto_hit=cmp.onto_hit, hint=cmp.hint,
    )


@router.get("/candidates", response_model=CandidatesResponse)
async def list_candidates(
    service: FaqDep,
    _actor: CurrentActor,
    status: Annotated[str, Query()] = "all",
) -> CandidatesResponse:
    """候选问题库（状态筛＋扫库态随行；频次倒序——端点 9）。"""
    rows: CandidateList = await service.candidates(status=status)
    items = [
        CandidateBody(
            id=c.id, question=c.question, variants=c.variants, freq=c.freq,
            window=c.window, status=c.status, compare=_compare_out(c), draft=c.draft,
            hook=_hook_out(c.hook),
        )
        for c in rows.items
    ]
    return CandidatesResponse(
        items=items, total=rows.total,
        scan=ScanPanelBody(
            running_task_id=rows.scan.running_task_id, last_hint=rows.scan.last_hint
        ),
    )


# ---------- 端点 10/11：扫库异步长任务 ----------


class ScanCreateResponse(BaseModel):
    task_id: str
    status: str
    hint: str


@router.post("/scan-tasks", response_model=ScanCreateResponse, status_code=202)
async def start_scan(
    service: FaqDep,
    _actor: CurrentActor,
) -> ScanCreateResponse:
    """扫库受理（异步长任务，202；重入 409；关弹窗不中断——端点 10）。"""
    row: ScanHandle = await service.start_scan(actor_who=_actor.who)
    return ScanCreateResponse(task_id=row.task_id, status=row.status, hint=row.hint)


class NewClusterBody(BaseModel):
    id: str
    question: str
    freq: int


class ScanProgressResponse(BaseModel):
    task_id: str
    status: str
    new_cluster_count: int
    new_clusters: list[NewClusterBody]
    hint: str | None


@router.get("/scan-tasks/{task_id}", response_model=ScanProgressResponse)
async def scan_progress(
    task_id: str,
    service: FaqDep,
    _actor: CurrentActor,
) -> ScanProgressResponse:
    """扫库轮询（关闭弹窗不中断、重开看结果——端点 11）。"""
    row: ScanProgress = await service.scan_progress(task_id)
    return ScanProgressResponse(
        task_id=row.task_id, status=row.status, new_cluster_count=row.new_cluster_count,
        new_clusters=[NewClusterBody(id=c.id, question=c.question, freq=c.freq)
                      for c in row.new_clusters],
        hint=row.hint,
    )


# ---------- 端点 12：POST /candidates/{id}/compare 向量比对 ----------


class CompareResponse(BaseModel):
    id: str
    status: str
    compare: CompareBody


@router.post("/candidates/{candidate_id}/compare", response_model=CompareResponse)
async def compare_candidate(
    candidate_id: str,
    service: FaqDep,
    _actor: CurrentActor,
) -> CompareResponse:
    """向量比对（三面去重：既有问答/知识库/本体——人工触发，端点 12）。"""
    row: CandidateItem = await service.compare_candidate(candidate_id, actor_who=_actor.who)
    cmp = _compare_out(row)
    if cmp is None:  # pragma: no cover —— compare 后 compare 恒非空（状态机保证）
        raise ApiError(status_code=500, code="faq_compare_missing", message="比对结论缺失")
    return CompareResponse(id=row.id, status=row.status, compare=cmp)


# ---------- 端点 13：POST /candidates/{id}/draft 候选起草 ----------


class CandidateDraftResponse(BaseModel):
    id: str
    status: str
    draft: str
    hook_suggestion: HookBody | None


@router.post("/candidates/{candidate_id}/draft", response_model=CandidateDraftResponse)
async def draft_candidate(
    candidate_id: str,
    service: FaqDep,
    _actor: CurrentActor,
) -> CandidateDraftResponse:
    """候选 LLM 起草（分析历史回答，溯源后缀＋挂接建议——端点 13）。"""
    row: CandidateDraft = await service.draft_candidate(candidate_id, actor_who=_actor.who)
    return CandidateDraftResponse(
        id=row.id, status=row.status, draft=row.draft,
        hook_suggestion=_hook_out(row.hook_suggestion),
    )


# ---------- 端点 14：POST /drafts 引用知识起草 ----------


class LedgerRefBody(BaseModel):
    kind: str
    id: int


class SliceRefBody(BaseModel):
    report_id: str
    fragment_id: str


class DraftsBody(BaseModel):
    ledger_ref: LedgerRefBody | None = None
    slice_ref: SliceRefBody | None = None


class DraftsResponse(BaseModel):
    draft: str
    hook_suggestion: HookBody | None


@router.post("/drafts", response_model=DraftsResponse)
async def draft_from_refs(
    body: DraftsBody,
    service: FaqDep,
    _actor: CurrentActor,
) -> DraftsResponse:
    """引用知识起草（台账口径/切片原文两选可组合；服务端直取——端点 14）。"""
    row: DraftResult = await service.draft_from_refs(
        LedgerRef(kind=body.ledger_ref.kind, id=body.ledger_ref.id) if body.ledger_ref else None,
        SliceRef(report_id=body.slice_ref.report_id, fragment_id=body.slice_ref.fragment_id)
        if body.slice_ref
        else None,
    )
    return DraftsResponse(draft=row.draft, hook_suggestion=_hook_out(row.hook_suggestion))


# ---------- 端点 15：POST /import 批量导入 ----------


class ImportFailureBody(BaseModel):
    row: int
    reason: str


class ImportResponse(BaseModel):
    dry_run: bool
    added: int
    merged: int
    skipped: int
    failed: int
    failures: list[ImportFailureBody]
    hint: str


@router.post("/import", response_model=ImportResponse)
async def import_library(
    request: Request,
    service: FaqDep,
    security: SecurityDep,
    actor: CurrentActor,
    mode: Annotated[str, Query()],
    dry_run: Annotated[bool, Query()] = False,
    filename: Annotated[str, Query()] = "import.csv",
) -> ImportResponse:
    """批量导入（append/replace 两模式＋试校验＋四计数——端点 15；文件落 MinIO）。

    传输形态（合同悬置「结合实际框架定」落点）：上传件走 raw body（application/
    octet-stream），mode/dry_run/filename 走 query 参数——python-multipart 不在
    平台依赖清单（本票不动 pyproject），multipart 形态归依赖落位批再切。
    """
    file_bytes = await request.body()
    if not file_bytes:
        raise ApiError(status_code=400, code="faq_import_file_empty",
                       message="上传件为空——请携带 CSV 模板文件")
    row: ImportStats = await service.import_library(
        mode=mode, dry_run=dry_run, filename=filename, file_bytes=file_bytes,
        actor_who=actor.who,
    )
    await security.audit(  # B12 横切留痕（导入件落对象存储不过期）
        AuditRow(
            who=actor.who,
            action="faq.library.imported",
            content=f"{'试校验' if row.dry_run else '导入'}：文件 {filename}——"
                    f"新增 {row.added} · 合并 {row.merged} · 跳过 {row.skipped}"
                    f" · 失败 {row.failed}",
        )
    )
    return ImportResponse(
        dry_run=row.dry_run, added=row.added, merged=row.merged, skipped=row.skipped,
        failed=row.failed,
        failures=[ImportFailureBody(row=f.row, reason=f.reason) for f in row.failures],
        hint=row.hint,
    )


# ---------- 端点 16：POST /export 导出全库 ----------


class ExportResponse(BaseModel):
    download_url: str
    expires_at: str
    columns: list[str]
    hint: str


@router.post("/export", response_model=ExportResponse)
async def export_library(
    service: FaqDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> ExportResponse:
    """导出全库（模板列对称；预签名 GET 直链小时级有效——端点 16）。"""
    row: DownloadHandle = await service.export_library()
    await security.audit(  # B12 横切留痕（直链签发安全敏感——P1-05b 审查先例同族）
        AuditRow(
            who=actor.who,
            action="faq.library.exported",
            content=f"签发 FAQ 全库导出直链（小时级有效，至 {row.expires_at}）",
        )
    )
    return ExportResponse(
        download_url=row.download_url, expires_at=row.expires_at,
        columns=row.columns, hint=row.hint,
    )
