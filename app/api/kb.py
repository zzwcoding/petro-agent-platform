"""api.kb —— /api/kb 路由族（B1-报告库.md v0.3 合同 15 条路由，P1-02a/P1-02b；
B2-答案出处.md v0.3 合同 6 条路由，P1-04——/api/kb 同域片段子域，98 §7.1）。

形状注记：
- 响应字段 snake_case（00 §14-R1——本端点即真实接线，同 D1/D3 先例）；
  query 参数 pageSize 保留现拼写。
- 权限：B1 页全员可见（roles.js MENU B1 无 roles 限制）——组闸不做，身份桩
  依赖（CurrentActor）只解析身份（未认证 401）；审计 who 服务端解析不信任前端。
- 任务受理（端点 6 confirm）＝200 同步特例（00 §5.2：B1 受理同步返回 200）；
  建库（端点 15）＝201（B1 端点 15 冻结）。
- 筛选（00 §4.5）：tasks.source 值域合同冻结（all|上传入库|片段修正|重跑定型）、
  libs.graph（all|on|off）、reports.lib（all|现有库名——B1 端点 1 入参照抄）、
  keyword 模糊匹配；越界 400（code=kb_param_invalid，errors.py 登记）。
- 端点 4 片段修正＝P1-02b 激活（乐观锁＋记版＋重建折算任务＋wiki 重铸联动）。
- B2（P1-04）：GET /fragments（两读法分派——report_id 携带按报告整组取数，
  缺省全库扁平清单分页必带缺 400）/ GET /fragments/{id}/context（父块回捞）/
  POST /fragments/{id}/issue-reports（标记入队）/ GET /issue-reports（队列，
  state 筛在途态）/ POST /issue-reports/{id}/review（confirm|reject，驳回必带
  理由 400）/ POST /issue-reports/{id}/close（销记）；B12 审计三写口
  kb.fragment.marked / kb.issue.reviewed / kb.issue.closed。
- B12 平台审计（P1-02a 收尾裁决指令①，P0-05 gateway 同款）：api 层编排关键
  写操作——建库/停用启用/配置保存/修正确认——经 security.audit 写平台审计
  （kb 域不反向依赖 security）；域内 F62 活动流留痕照旧双轨。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import CurrentActor, KbDep, SecurityDep
from app.domains.kb import (
    AdditionsView,
    CreateLibReceipt,
    LibraryConfigView,
    LibraryView,
    ReportDetail,
    ReportLedgerRow,
    SaveReceipt,
    TaskProgress,
    TaskView,
)
from app.domains.security.domain import AuditRow

router = APIRouter(prefix="/api/kb", tags=["kb"])


# ---------- 端点 1：GET /reports 台账 ----------


class ReportLedgerItem(BaseModel):
    id: str
    doc: str
    lib_id: str
    lib: str
    refs: int | None
    wiki: str | None
    status: str


class ReportsResponse(BaseModel):
    items: list[ReportLedgerItem]
    total: int


def _ledger_item(row: ReportLedgerRow) -> ReportLedgerItem:
    return ReportLedgerItem(
        id=row.id, doc=row.doc, lib_id=row.lib_id, lib=row.lib,
        refs=row.refs, wiki=row.wiki, status=row.status,
    )


@router.get("/reports", response_model=ReportsResponse)
async def list_reports(
    service: KbDep,
    _actor: CurrentActor,
    lib: Annotated[str, Query()] = "all",
    keyword: Annotated[str, Query()] = "",
) -> ReportsResponse:
    """报告台账（服务端筛选：所属库＋关键词；「入库中」状态标直出——端点 1）。"""
    rows = await service.list_reports(lib=lib, keyword=keyword or None)
    return ReportsResponse(items=[_ledger_item(r) for r in rows], total=len(rows))


# ---------- 端点 2：GET /reports/{id} 详情 ----------


class FragmentVersionItem(BaseModel):
    v: int
    text: str
    note: str


class ActivityRowBody(BaseModel):
    time: str
    who: str
    action: str
    target: str


class FragmentItem(BaseModel):
    id: str
    type: str
    path: str
    text: str
    version: int
    versions: list[FragmentVersionItem]


class ReportDetailResponse(BaseModel):
    id: str
    doc: str
    lib_id: str
    lib: str
    subject: str | None
    refs: int | None
    wiki: str | None
    status: str
    related_objects: list[dict[str, str]]
    fragments: list[FragmentItem]


@router.get("/reports/{report_id}", response_model=ReportDetailResponse)
async def report_detail(
    report_id: str,
    service: KbDep,
    _actor: CurrentActor,
) -> ReportDetailResponse:
    """报告详情（片段预览含版本——F30 增补：每个片段恒有 v1）。"""
    view = await service.report_detail(report_id)
    return _detail_response(view)


def _detail_response(view: ReportDetail) -> ReportDetailResponse:
    return ReportDetailResponse(
        id=view.id, doc=view.doc, lib_id=view.lib_id, lib=view.lib,
        subject=view.subject, refs=view.refs, wiki=view.wiki, status=view.status,
        related_objects=view.related_objects,
        fragments=[
            FragmentItem(
                id=f.id, type=f.type, path=f.path, text=f.text, version=f.version,
                versions=[
                    FragmentVersionItem(v=ver.v, text=ver.text, note=ver.note)
                    for ver in f.versions
                ],
            )
            for f in view.fragments
        ],
    )


# ---------- 端点 3：POST /reports/{id}/download-url ----------


class DownloadUrlResponse(BaseModel):
    id: str
    download_url: str
    expires_at: str
    ttl: str


@router.post("/reports/{report_id}/download-url", response_model=DownloadUrlResponse)
async def download_url(
    report_id: str,
    service: KbDep,
    _actor: CurrentActor,
) -> DownloadUrlResponse:
    """下载原件直链（预签名 GET——小时级有效、上限 7 天；00 §7.2）。"""
    url, expires_at = await service.download_url(report_id)
    return DownloadUrlResponse(id=report_id, download_url=url, expires_at=expires_at, ttl="小时级")


# ---------- 端点 4：POST /reports/{id}/fragments/{fragId}/revisions（P1-02b 激活） ----------


class ReviseBody(BaseModel):
    base_version: int
    text: str


class RebuildInfoBody(BaseModel):
    triggered: bool
    hint: str


class ReviseResponse(BaseModel):
    id: str
    version: int
    versions: list[FragmentVersionItem]
    rebuild: RebuildInfoBody
    activity_row: ActivityRowBody
    task_id: str


@router.post("/reports/{report_id}/fragments/{fragment_id}/revisions",
             response_model=ReviseResponse)
async def revise_fragment(
    report_id: str,
    fragment_id: str,
    body: ReviseBody,
    service: KbDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> ReviseResponse:
    """片段人工修正（F30 增补——P1-02b 激活）：乐观锁（base_version 落后 409）
    ＋逐次记版（v1 原始不可变）＋重建折算「片段修正」任务（向量重嵌该片段＋
    问题块重生）＋FragmentRevised 事件（wiki 重铸联动，B9）。"""
    receipt = await service.revise_fragment(
        report_id, fragment_id, body.base_version, body.text, actor.who
    )
    await security.audit(  # B12 横切留痕（裁决指令①）——经唯一写口，kb 不依赖 security
        AuditRow(
            who=actor.who,
            action="kb.fragment.revised",
            content=(
                f"片段修正确认：{receipt.id} v{body.base_version}→v{receipt.version}"
                f"（报告 {report_id}；重建任务 {receipt.task_id}）"
            ),
        )
    )
    return ReviseResponse(
        id=receipt.id,
        version=receipt.version,
        versions=[
            FragmentVersionItem(v=ver.v, text=ver.text, note=ver.note)
            for ver in receipt.versions
        ],
        rebuild=RebuildInfoBody(triggered=receipt.rebuild.triggered,
                                hint=receipt.rebuild.hint),
        activity_row=ActivityRowBody(
            time=receipt.activity_row.time, who=receipt.activity_row.who,
            action=receipt.activity_row.action, target=receipt.activity_row.target,
        ),
        task_id=receipt.task_id,
    )


# ---------- 端点 5：POST /uploads 直传受理 ----------


class UploadInitBody(BaseModel):
    filename: str
    size: int
    lib_id: str | None = None
    suggested_topic: str | None = None  # 入库路由话题（阶段 1 实施项——B1 v0.3）


class RouteSuggestionBody(BaseModel):
    mode: str | None
    topic: str | None = None
    lib_id: str | None = None
    lib_name: str | None = None
    template: str | None = None
    reason: str | None = None
    confidence: float | None = None


class UploadReceiptResponse(BaseModel):
    upload_id: str
    lib_id: str | None
    lib_name: str | None
    dup_warning: str | None
    put_url: str
    expires_at: str
    bucket: str
    routing: RouteSuggestionBody | None


def _route_body(suggestion: object) -> RouteSuggestionBody | None:
    if suggestion is None:
        return None
    data = suggestion.as_dict()  # type: ignore[attr-defined]
    return RouteSuggestionBody(**data)


@router.post("/uploads", response_model=UploadReceiptResponse)
async def upload_init(
    body: UploadInitBody,
    service: KbDep,
    actor: CurrentActor,
) -> UploadReceiptResponse:
    """直传受理（两拍第一拍）：登记＋预签名 PUT 凭证；停用库 400 带码；
    dup_warning 非阻断；lib_id 缺省走入库路由（LLM 只建议、人确认后执行）。"""
    receipt = await service.upload_init(
        body.filename, body.size, body.lib_id, actor.who,
        suggested_topic=body.suggested_topic,
    )
    return UploadReceiptResponse(
        upload_id=receipt.upload_id,
        lib_id=receipt.lib_id,
        lib_name=receipt.lib_name,
        dup_warning=receipt.dup_warning,
        put_url=receipt.put_url,
        expires_at=receipt.expires_at,
        bucket=receipt.bucket,
        routing=_route_body(receipt.routing),
    )


# ---------- 端点 6：POST /uploads/{uploadId}/confirm 确认入库 ----------


class ConfirmBody(BaseModel):
    """路由确认通道（入库路由专节：路由确认并入 confirm 定型链路）——
    缺省空体＝沿用受理已定目标库（v0.2 直传流形状不变）。"""

    lib_id: str | None = None


class ConfirmResponse(BaseModel):
    task_id: str
    upload_id: str
    doc: str
    lib_id: str
    lib_name: str
    source: str
    state: str
    current_step: int
    config_snapshot: dict[str, object]


@router.post("/uploads/{upload_id}/confirm", response_model=ConfirmResponse)
async def upload_confirm(
    upload_id: str,
    service: KbDep,
    actor: CurrentActor,
    body: ConfirmBody | None = None,
) -> ConfirmResponse:
    """确认入库（核实落桶→建任务，config_snapshot 定型——配置定型点在受理确认时刻）。"""
    receipt = await service.upload_confirm(
        upload_id, actor.who, lib_id=(body.lib_id if body else None)
    )
    return ConfirmResponse(
        task_id=receipt.task_id,
        upload_id=receipt.upload_id,
        doc=receipt.doc,
        lib_id=receipt.lib_id,
        lib_name=receipt.lib_name,
        source=receipt.source,
        state=receipt.state,
        current_step=receipt.current_step,
        config_snapshot=receipt.config_snapshot,
    )


# ---------- 端点 7：GET /tasks 任务列表 ----------


class TaskItem(BaseModel):
    id: str
    doc: str
    lib_id: str
    lib_name: str
    source: str
    state: str
    current_step: int
    stop_at: str | None
    reason: str | None


class TasksResponse(BaseModel):
    items: list[TaskItem]
    total: int


@router.get("/tasks", response_model=TasksResponse)
async def list_tasks(
    service: KbDep,
    _actor: CurrentActor,
    source: Annotated[str, Query()] = "all",
) -> TasksResponse:
    """入库任务列表（来源筛参 source——v0.2 拍板；创建时间倒序）。"""
    rows: list[TaskView] = await service.list_ingest_tasks(source)
    return TasksResponse(
        items=[
            TaskItem(
                id=r.id, doc=r.doc, lib_id=r.lib_id, lib_name=r.lib_name,
                source=r.source, state=r.state, current_step=r.current_step,
                stop_at=r.stop_at, reason=r.reason,
            )
            for r in rows
        ],
        total=len(rows),
    )


# ---------- 端点 8：GET /tasks/{id} 轮询 ----------


class TaskNodeItem(BaseModel):
    key: str
    label: str
    state: str
    note: str | None


class TaskProgressResponse(BaseModel):
    id: str
    state: str
    source: str
    current_step: int
    stop_at: str | None
    reason: str | None
    nodes: list[TaskNodeItem]
    config_snapshot: dict[str, object]


def _progress_response(view: TaskProgress) -> TaskProgressResponse:
    return TaskProgressResponse(
        id=view.id, state=view.state, source=view.source,
        current_step=view.current_step, stop_at=view.stop_at, reason=view.reason,
        nodes=[
            TaskNodeItem(key=n.key, label=n.label, state=n.state, note=n.note)
            for n in view.nodes
        ],
        config_snapshot=view.config_snapshot,
    )


@router.get("/tasks/{task_id}", response_model=TaskProgressResponse)
async def get_task(
    task_id: str,
    service: KbDep,
    _actor: CurrentActor,
) -> TaskProgressResponse:
    """轮询处理进度（五步节点＋服务端组装说明——前端零拼装业务文案）。"""
    return _progress_response(await service.ingest_task(task_id))


# ---------- 端点 9：GET /tasks/{id}/additions 产物 ----------


class AdditionsResponse(BaseModel):
    task_id: str
    doc: str
    summary: dict[str, object] | None
    questions: dict[str, object] | None


@router.get("/tasks/{task_id}/additions", response_model=AdditionsResponse)
async def task_additions(
    task_id: str,
    service: KbDep,
    _actor: CurrentActor,
) -> AdditionsResponse:
    """索引期加法产物（摘要块＋问题块——done 后可读，未 done 409）。"""
    view: AdditionsView = await service.ingest_additions(task_id)
    return AdditionsResponse(
        task_id=view.task_id, doc=view.doc, summary=view.summary, questions=view.questions
    )


# ---------- 端点 10：POST /tasks/{id}/retry 重试/重跑 ----------


@router.post("/tasks/{task_id}/retry", response_model=TaskProgressResponse)
async def retry_task(
    task_id: str,
    service: KbDep,
    actor: CurrentActor,
) -> TaskProgressResponse:
    """重试/重跑（stuck 内含停止；重跑＝按当前待生效配置重新定型；来源转「重跑定型」）。"""
    return _progress_response(await service.retry_ingest(task_id, actor.who))


# ---------- 端点 11：GET /libs 库列表 ----------


class LastIngestionBody(BaseModel):
    doc: str
    switches: dict[str, bool]


class LibraryItem(BaseModel):
    id: str
    name: str
    biz_template: str
    status: str
    last_ingestion: LastIngestionBody | None
    annotations: dict[str, str]


class LibrariesResponse(BaseModel):
    items: list[LibraryItem]
    total: int


@router.get("/libs", response_model=LibrariesResponse)
async def list_libraries(
    service: KbDep,
    _actor: CurrentActor,
    graph: Annotated[str, Query()] = "all",
    keyword: Annotated[str, Query()] = "",
) -> LibrariesResponse:
    """库列表（最近入库＋开关快照；图谱筛——两态分离：快照≠待生效配置）。"""
    rows: list[LibraryView] = await service.list_libraries(graph=graph, keyword=keyword or None)
    return LibrariesResponse(
        items=[
            LibraryItem(
                id=r.id, name=r.name, biz_template=r.biz_template, status=r.status,
                last_ingestion=(
                    LastIngestionBody(doc=r.last_ingestion["doc"],
                                      switches=r.last_ingestion["switches"])
                    if r.last_ingestion
                    else None
                ),
                annotations=r.annotations,
            )
            for r in rows
        ],
        total=len(rows),
    )


# ---------- 端点 12：GET /libs/{id}/config 库配置读 ----------


class SwitchesBody(BaseModel):
    semantic: bool
    keyword: bool
    wiki: bool
    graph: bool


class LibraryConfigResponse(BaseModel):
    id: str
    name: str
    switches: SwitchesBody
    mode: str
    add_summary: bool
    add_questions: bool
    saved_at: str | None
    saved_by: str | None


@router.get("/libs/{lib_id}/config", response_model=LibraryConfigResponse)
async def get_library_config(
    lib_id: str,
    service: KbDep,
    _actor: CurrentActor,
) -> LibraryConfigResponse:
    """库配置读取（上传确认弹窗只读预览/配置弹窗回填——双消费）。"""
    view: LibraryConfigView = await service.library_config(lib_id)
    return LibraryConfigResponse(
        id=view.id, name=view.name,
        switches=SwitchesBody(**view.switches),
        mode=view.mode, add_summary=view.add_summary, add_questions=view.add_questions,
        saved_at=view.saved_at, saved_by=view.saved_by,
    )


# ---------- 端点 13：PUT /libs/{id}/config 保存（＋v0.3 status 停用/启用） ----------


class LibraryConfigSaveBody(BaseModel):
    switches: SwitchesBody
    mode: str
    add_summary: bool
    add_questions: bool
    status: str | None = None  # v0.3 建库批：可选——缺省不动库状态


class ConfigSaveResponse(BaseModel):
    id: str
    saved_at: str
    saved_by: str
    status: str
    hint: str
    activity_row: ActivityRowBody


def _save_response(view: SaveReceipt) -> ConfigSaveResponse:
    return ConfigSaveResponse(
        id=view.id, saved_at=view.saved_at, saved_by=view.saved_by,
        status=view.status, hint=view.hint,
        activity_row=ActivityRowBody(
            time=view.activity_row.time, who=view.activity_row.who,
            action=view.activity_row.action, target=view.activity_row.target,
        ),
    )


@router.put("/libs/{lib_id}/config", response_model=ConfigSaveResponse)
async def save_library_config(
    lib_id: str,
    body: LibraryConfigSaveBody,
    service: KbDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> ConfigSaveResponse:
    """保存本库配置（写入待生效配置——下次入库定型、不做运行时热切换；同事务记 F62；
    v0.3 可选 status 承载停用/启用）。"""
    view = await service.save_library_config(
        lib_id,
        switches=body.switches.model_dump(),
        mode=body.mode,
        add_summary=body.add_summary,
        add_questions=body.add_questions,
        status=body.status,
        actor_who=actor.who,
    )
    await security.audit(  # B12 横切留痕（裁决指令①）——经唯一写口，kb 不依赖 security
        AuditRow(
            who=actor.who,
            action="kb.config.saved",
            content=(
                f"库配置保存：{lib_id}（下次入库生效；开关 "
                f"{body.switches.model_dump()}，mode={body.mode}，"
                f"摘要/问题加法 {body.add_summary}/{body.add_questions}"
                + (
                    f"；库状态：{body.status}"
                    if body.status is not None
                    else ""
                )
                + "）"
            ),
        )
    )
    return _save_response(view)


# ---------- 端点 14：GET /libs/{id}/activities 活动流 ----------


class ActivitiesResponse(BaseModel):
    items: list[ActivityRowBody]
    total: int


@router.get("/libs/{lib_id}/activities", response_model=ActivitiesResponse)
async def library_activities(
    lib_id: str,
    service: KbDep,
    _actor: CurrentActor,
) -> ActivitiesResponse:
    """库活动流（F62 只读——只记录，不改任何数据；时间倒序）。"""
    rows = await service.library_activities(lib_id)
    return ActivitiesResponse(
        items=[
            ActivityRowBody(time=r.time, who=r.who, action=r.action, target=r.target)
            for r in rows
        ],
        total=len(rows),
    )


# ---------- 端点 15：POST /libs 建库（201） ----------


class CreateLibraryBody(BaseModel):
    lib_name: str
    biz_template: str


class CreateLibraryResponse(BaseModel):
    lib_id: str
    lib_name: str
    biz_template: str
    status: str
    config: dict[str, object]
    activity_row: ActivityRowBody


def _create_response(view: CreateLibReceipt) -> CreateLibraryResponse:
    return CreateLibraryResponse(
        lib_id=view.lib_id, lib_name=view.lib_name, biz_template=view.biz_template,
        status=view.status, config=view.config,
        activity_row=ActivityRowBody(
            time=view.activity_row.time, who=view.activity_row.who,
            action=view.activity_row.action, target=view.activity_row.target,
        ),
    )


@router.post("/libs", response_model=CreateLibraryResponse, status_code=201)
async def create_library(
    body: CreateLibraryBody,
    service: KbDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> CreateLibraryResponse:
    """建库（业务模板带出默认配置档案——模板只定初始档、建后可调；空名 400/重名 409）。"""
    view = await service.create_library(body.lib_name, body.biz_template, actor.who)
    await security.audit(  # B12 横切留痕（裁决指令①）——经唯一写口，kb 不依赖 security
        AuditRow(
            who=actor.who,
            action="kb.lib.created",
            content=(
                f"建库：{view.lib_name}（业务模板：{body.biz_template}，"
                f"默认配置已生成；库号 {view.lib_id}）"
            ),
        )
    )
    return _create_response(view)


# ---------- B2 端点 1：GET /fragments 片段台账（两读法分派） ----------


class FragmentLedgerItem(BaseModel):
    id: str
    report_id: str
    report: str
    well: str | None
    section: str | None
    type: str
    hit: str


class FragmentsResponse(BaseModel):
    items: list[FragmentLedgerItem]
    total: int
    page: int | None = None
    page_size: int | None = None


@router.get("/fragments", response_model=FragmentsResponse)
async def list_fragments(
    service: KbDep,
    _actor: CurrentActor,
    report_id: Annotated[str | None, Query()] = None,
    type: Annotated[str, Query()] = "all",
    keyword: Annotated[str, Query()] = "",
    page: Annotated[int | None, Query(ge=1)] = None,
    pageSize: Annotated[int | None, Query(ge=1, alias="pageSize")] = None,
) -> FragmentsResponse:
    """片段台账列表（B2 端点 1）：携带 report_id＝按报告整组取数（整表返回）；
    缺省＝全库扁平清单（分页必带缺任一 400——B3 slice_ref 下拉数据源）；
    type 五类型标筛＋keyword 搜命中句/井号/章节路径；列表只给子块（INV）。"""
    result = await service.list_fragments(
        report_id, type=type, keyword=keyword or None, page=page, page_size=pageSize
    )
    return FragmentsResponse(
        items=[
            FragmentLedgerItem(
                id=i.id, report_id=i.report_id, report=i.report, well=i.well,
                section=i.section, type=i.type, hit=i.hit,
            )
            for i in result.items
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


# ---------- B2 端点 2：GET /fragments/{id}/context 父块回捞 ----------


class FragmentContextResponse(BaseModel):
    id: str
    type: str
    hit: str
    context: str


@router.get("/fragments/{fragment_id}/context", response_model=FragmentContextResponse)
async def fragment_context(
    fragment_id: str,
    service: KbDep,
    _actor: CurrentActor,
) -> FragmentContextResponse:
    """命中句 → 完整上下文段（F30 父块回捞与 F36 子块回读同端点会师；
    摘要块/问题块＝产物说明行——无父块的唯一例外）。"""
    view = await service.fragment_context(fragment_id)
    return FragmentContextResponse(
        id=view.id, type=view.type, hit=view.hit, context=view.context
    )


# ---------- B2 端点 3：POST /fragments/{id}/issue-reports 标记问题片段 ----------


class IssueReportItem(BaseModel):
    id: str
    fragment_id: str
    report_id: str
    fragment_label: str
    state: str
    marked_by: str
    marked_at: str
    reject_reason: str | None = None
    hint: str | None = None


@router.post("/fragments/{fragment_id}/issue-reports", response_model=IssueReportItem)
async def mark_fragment_issue(
    fragment_id: str,
    service: KbDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> IssueReportItem:
    """标记问题片段（F30 票 104 增补——只标记不直改）：进质检复核队列＋同事务
    记 F62「标记问题片段」；待质检复核态重复 409；已驳回态重标＝旧单转已销记。"""
    view = await service.report_fragment_issue(fragment_id, actor.who)
    await security.audit(  # B12 横切留痕（票面指令——标记写口经唯一审计出口）
        AuditRow(
            who=actor.who,
            action="kb.fragment.marked",
            content=f"标记问题片段：{view.fragment_label}（标记单 {view.id}）",
        )
    )
    return IssueReportItem(
        id=view.id, fragment_id=view.fragment_id, report_id=view.report_id,
        fragment_label=view.fragment_label, state=view.state,
        marked_by=view.marked_by, marked_at=view.marked_at,
        reject_reason=view.reject_reason, hint=view.hint,
    )


# ---------- B2 端点 4：GET /issue-reports 质检复核队列列表 ----------


class IssueReportsResponse(BaseModel):
    items: list[IssueReportItem]
    total: int


@router.get("/issue-reports", response_model=IssueReportsResponse)
async def list_issue_reports(
    service: KbDep,
    _actor: CurrentActor,
    state: Annotated[str, Query()] = "all",
) -> IssueReportsResponse:
    """质检复核队列（v0.3 增设）：state=all|待质检复核|已驳回——终态默认不出列；
    标记时间倒序；fragment_label 与端点 3 同源同构。"""
    rows = await service.list_issue_reports(state)
    return IssueReportsResponse(
        items=[
            IssueReportItem(
                id=v.id, fragment_id=v.fragment_id, report_id=v.report_id,
                fragment_label=v.fragment_label, state=v.state,
                marked_by=v.marked_by, marked_at=v.marked_at,
                reject_reason=v.reject_reason, hint=v.hint,
            )
            for v in rows
        ],
        total=len(rows),
    )


# ---------- B2 端点 5：POST /issue-reports/{id}/review 复核确认/驳回 ----------


class ReviewBody(BaseModel):
    action: str  # confirm | reject
    reason: str | None = None


@router.post("/issue-reports/{issue_id}/review", response_model=IssueReportItem)
async def review_issue_report(
    issue_id: str,
    body: ReviewBody,
    service: KbDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> IssueReportItem:
    """复核确认/驳回（v0.3——驳回必带理由回标记人；确认转修正流＝B1 端点 4 修正）。"""
    view = await service.review_issue_report(issue_id, body.action, body.reason, actor.who)
    await security.audit(  # B12 横切留痕（复核写口）
        AuditRow(
            who=actor.who,
            action="kb.issue.reviewed",
            content=(
                f"复核{'确认' if body.action == 'confirm' else '驳回'}：{view.fragment_label}"
                f"（标记单 {view.id} → {view.state}"
                + (f"；理由：{view.reject_reason}" if view.reject_reason else "")
                + "）"
            ),
        )
    )
    return IssueReportItem(
        id=view.id, fragment_id=view.fragment_id, report_id=view.report_id,
        fragment_label=view.fragment_label, state=view.state,
        marked_by=view.marked_by, marked_at=view.marked_at,
        reject_reason=view.reject_reason, hint=view.hint,
    )


# ---------- B2 端点 6：POST /issue-reports/{id}/close 驳回后销记 ----------


class IssueCloseResponse(BaseModel):
    id: str
    state: str


@router.post("/issue-reports/{issue_id}/close", response_model=IssueCloseResponse)
async def close_issue_report(
    issue_id: str,
    service: KbDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> IssueCloseResponse:
    """驳回后销记（v0.3——标记人主动关闭，队列零悬挂；仅已驳回态可销记）。"""
    view = await service.close_issue_report(issue_id, actor.who)
    await security.audit(  # B12 横切留痕（销记写口）
        AuditRow(
            who=actor.who,
            action="kb.issue.closed",
            content=f"销记：{view.fragment_label}（标记单 {view.id} → 已销记）",
        )
    )
    return IssueCloseResponse(id=view.id, state=view.state)
