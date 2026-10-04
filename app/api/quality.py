"""api.quality —— /api/quality 路由族（E2-数据质量台.md v0.5 合同，9 条路由）。

M-05a 管理面票：端点 1/2/6/7/8/9 全量实现。M-05b 执行通道票：端点 3/4/5 从
501 壳接通任务表轮询通道（受理/轮询接续/历史）＋端点 7 复扫执行缝生产装配
（channel.py 适配器——本路由族零改动，缝在 service/装配层）。

形状注记：
- 响应字段按 00 §14-R1 snake_case，唯 `autoFix` 与任务通道顶键 `taskId` 为
  合同 DTO 冻结 camelCase（照抄示例键名，不归一）。
- 分页（端点 6，v0.5 预留）：page≥1＋pageSize（alias，缺省 20——C1/D5 先例）；
  响应回显 page/page_size＋total（00 §4.1 信封）。
- 问题单流转（端点 7）：请求体可选 ``action:"rescan"``（P2-02 前端已同步同形）；
  响应 {id, lane, state, verify}——rescan 不是流转，lane 不变；关闭守卫 422
  （合同冻结状态码——00 §3.2 常规族外特例，随合同走）；终态再流转 409。
- 权限：E2 页 v0.4 过渡口径（Owner 2026-10-04 拍板推论）——权限预埋期全员
  管理员，接口权限声明预埋（require 式一行 CurrentActor）；真分权（规则启停/
  任务发起＝质量管理员，认领/整改＝采集管理员，复核/关闭＝质量管理员）随 D3
  落闸批恢复，本路由族形状零改动。
- 规则启停（端点 2）档位守卫（M-05a 修复拍——rev F1）：规则 13-20 仅登记
  不实施（E2 v0.5 实施范围注记）——PATCH 置 enabled=true 拒 422（防「已启用
  但 V1 任务只跑 1-12 恒跳过」的静默矛盾，执行侧保证归 M-05b）；enabled=false
  （停用回登记态）恒放行。守卫落 api 层前置（422 错误包走 ApiError——接口层
  自行抛错惯例，chat/faq 先例；域内 422 族错误码归合同批补冻结）。
- B12 审计：启停/流转/复扫/任务受理/任务接续写操作在服务成功返回后落笔
  （P0-05 gateway 先例——失败路径不达审计行）；流转另落 quality_issue_transition
  留痕行（域内事务）。
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import CurrentActor, QualityDep, SecurityDep
from app.api.errors import ApiError
from app.domains.dataops.quality import (
    LANES,
    RESCAN_ACTION,
    TransitionReceipt,
)
from app.domains.security import AuditRow

router = APIRouter(prefix="/api/quality", tags=["quality"])

DEFAULT_PAGE = 1  # 00 §4.1
DEFAULT_PAGE_SIZE = 20  # D5 先例（00 §4.1）

# 端点 2 档位守卫（M-05a 修复拍——rev F1）：规则 13-20 仅登记不实施（E2 v0.5
# 实施范围注记；种子真源＝迁移 0015）——写侧拒启用；停用回登记态恒放行。
REGISTERED_ONLY_RULES = range(13, 21)
CODE_QUALITY_RULE_REGISTERED_ONLY = "quality_rule_registered_only"


# ---------- 端点 1：GET /rules 规则列表 ----------


class RuleItemBody(BaseModel):
    no: int
    kind: str
    rule: str
    crit: str
    enabled: bool
    action: str
    autoFix: bool  # 合同 DTO 冻结 camelCase（00 §14-R1 snake 例外——合同优先）


class RulesResponse(BaseModel):
    items: list[RuleItemBody]


@router.get("/rules", response_model=RulesResponse)
async def list_rules(
    service: QualityDep,
    _actor: CurrentActor,  # 权限预埋一行（E2 v0.4 过渡口径——全员管理员）
) -> RulesResponse:
    """规则列表（20 条种子投影——判据权威源＝本体 M3；13-20 仅登记恒停用）。"""
    rows = await service.list_rules()
    return RulesResponse(
        items=[
            RuleItemBody(
                no=r.no, kind=r.kind, rule=r.rule, crit=r.crit,
                enabled=r.enabled, action=r.action, autoFix=r.auto_fix,
            )
            for r in rows
        ]
    )


# ---------- 端点 2：PATCH /rules/{no} 规则启停 ----------


class RuleToggleBody(BaseModel):
    enabled: bool


class RuleToggleResponse(BaseModel):
    no: int
    enabled: bool


@router.patch("/rules/{no}", response_model=RuleToggleResponse)
async def toggle_rule(
    no: int,
    body: RuleToggleBody,
    service: QualityDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> RuleToggleResponse:
    """规则启停（停用＝质检任务跳过不删；写 quality_rule.enabled——本端点为
    该表唯一写口，数据面限写账号只读；B12 审计留痕操作人）。

    档位守卫（rev F1）：13-20 仅登记档拒启用（422——执行通道接通后放开）；
    enabled=false 恒放行。守卫在服务调用前置——拒绝即无写发生，审计不落笔
    （失败路径不达审计行）。
    """
    if body.enabled and no in REGISTERED_ONLY_RULES:
        raise ApiError(
            status_code=422,
            code=CODE_QUALITY_RULE_REGISTERED_ONLY,
            message=(
                f"仅登记规则未实施，不可启用（规则 {no} 属 13-20 仅登记档）"
                "——归属 M-05b 执行通道接通后放开"
            ),
        )
    receipt = await service.set_rule_enabled(no, body.enabled)
    await security.audit(
        AuditRow(
            who=actor.who,
            action="quality.rule_toggled",
            content=(
                f"质检规则 {no} {'启用' if body.enabled else '停用'}"
                "（停用＝质检任务跳过，规则保留不删）"
            ),
        )
    )
    return RuleToggleResponse(no=receipt.no, enabled=receipt.enabled)


# ---------- 端点 3/4/5：任务执行通道（M-05b 接通——任务表轮询形态） ----------
#
# 通道形态（DP-04 交付适配）：数据面＝APScheduler worker 管道；跨服务通信走
# 任务表轮询（quality_task 行形＝接口合同，零共享库——四耦合点①；HTTP 触发
# 接口 DP-04 未交付）。受理半边：running/step=0 落行即触发面；轮询半边：
# done→服务端接续（建单/挂单/隔离行回挂，step→4）；复扫：channel.py 适配器
# 走同通道（main.py 生产装配——缺省服务仍 501，替身注入归测试底座）。
# DTO 键形照抄合同示例：taskId 顶键为合同端点 3/4 冻结 camelCase（00 §14-R1
# snake 例外——合同优先，autoFix 同款）；task/report 内键逐字段照抄（rules/
# time/report.quarantined_rows…）。


class TaskStartResponse(BaseModel):
    taskId: str  # 合同端点 3 DTO 冻结 camelCase


class TaskReportBody(BaseModel):
    range: str | None
    scanned: str | None  # 展示串「12,604 行」（读侧拼装——机器值 scanned_rows 不出域）
    quarantined_rows: int | None  # 数据粒度（行级隔离坏行数）
    rejected_batches: int | None  # 数据粒度（整批拒收批次数）
    hits: list[str]  # 单据粒度展示行（「① 规则 1：…」形——读侧拼装）
    verdict: str | None


class TaskRecordBody(BaseModel):
    id: str
    time: str  # 展示串「YYYY-MM-DD HH:mm」（R2——合同示例同形）
    rules: int | None  # 合同键 rules（存储侧 rules_count——DP-05 命名注记）
    hits: int | None  # 单据粒度命中数（数据面口径——与隔离/拒收数分口径上报）
    report: TaskReportBody | None


class TaskStatusResponse(BaseModel):
    taskId: str
    status: str
    step: int | None = None  # running 形随行（done 形经 exclude_none 收敛为合同示例形）
    task: TaskRecordBody | None = None


class TaskListResponse(BaseModel):
    items: list[TaskRecordBody]


@router.post("/tasks", status_code=202, response_model=TaskStartResponse)
async def start_quality_task(
    service: QualityDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> TaskStartResponse:
    """发起质检任务（受理——任务表轮询通道：running/step=0 落行即触发面）。

    单任务进行中重入 409（quality_task_running）；重跑语义＝先撤「分发未认领」
    动态单（v0.5——在途单/预置单不触碰）。执行＝数据面质检通道（DP-04
    APScheduler 管道按管道节奏拾取——受理半边不 mock 假进度）。B12 审计
    （行为约定 5「发起」）成功路径落笔。
    """
    receipt = await service.accept_task()
    await security.audit(
        AuditRow(
            who=actor.who,
            action="quality.task_started",
            content=(
                f"质检任务 {receipt.task_id} 受理（启用规则 {receipt.rules_count} 条；"
                f"重跑撤分发未认领动态单 {receipt.cleared} 张）——数据面质检通道"
                "执行（任务表轮询，落行即触发面）"
            ),
        )
    )
    return TaskStartResponse(taskId=receipt.task_id)


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    response_model_exclude_none=True,  # done 形＝合同示例形 {taskId,status,task}
)
async def get_quality_task(
    task_id: str,
    service: QualityDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> TaskStatusResponse:
    """任务进度轮询；完成时返回任务记录＋合规报告并落问题单（合同端点 4）。

    done 且 step=2 → 服务端接续（命中逐条建单/挂单＋隔离行回挂＋step→4——
    认领/建单/步推进同事务原子）；接续实做时 B12 审计落笔（并发轮询输者
    followup=None 不重复审计不重复建单）。
    """
    view = await service.get_task(task_id)
    if view.followup is not None:
        f = view.followup
        await security.audit(
            AuditRow(
                who=actor.who,
                action="quality.task_followup",
                content=(
                    f"任务 {task_id} 接续：建单 {f.created}/挂单 {f.attached}"
                    f"（隔离行回挂 {f.rows_linked}）——step→4 分发完成"
                ),
            )
        )
    task: TaskRecordBody | None = None
    if view.task is not None:
        t = view.task
        task = TaskRecordBody(
            id=t.id,
            time=t.time,
            rules=t.rules,
            hits=t.hits,
            report=(
                TaskReportBody(
                    range=t.report["range"], scanned=t.report["scanned"],
                    quarantined_rows=t.report["quarantined_rows"],
                    rejected_batches=t.report["rejected_batches"],
                    hits=t.report["hits"], verdict=t.report["verdict"],
                )
                if t.report is not None
                else None
            ),
        )
    return TaskStatusResponse(
        taskId=view.task_id,
        status=view.status,
        # step 只随 running 形（合同 done 示形无 step——接续进度是流水细节，
        # exclude_none 收敛两形各自与合同示例同键）。
        step=view.step if view.status != "done" else None,
        task=task,
    )


@router.get("/tasks", response_model=TaskListResponse)
async def list_quality_tasks(
    service: QualityDep,
    _actor: CurrentActor,  # 权限预埋一行（E2 v0.4 过渡口径）
) -> TaskListResponse:
    """任务记录列表（倒序——最新在前，历史保留可回看；running 在途不进历史）。"""
    rows = await service.list_tasks()
    return TaskListResponse(
        items=[
            TaskRecordBody(
                id=t.id, time=t.time, rules=t.rules, hits=t.hits,
                report=TaskReportBody(
                    range=t.report["range"], scanned=t.report["scanned"],
                    quarantined_rows=t.report["quarantined_rows"],
                    rejected_batches=t.report["rejected_batches"],
                    hits=t.report["hits"], verdict=t.report["verdict"],
                )
                if t.report is not None
                else None,
            )
            for t in rows
        ]
    )


# ---------- 端点 6：GET /issues 问题单列表 ----------


class QrowBody(BaseModel):
    loc: str | None
    note: str | None


class VerifyBody(BaseModel):
    batch: str
    note: str


class IssueItemBody(BaseModel):
    id: str
    lane: int
    rule_no: int
    hit_count: int
    title: str | None
    desc: str | None
    owner: str | None
    qrows: list[QrowBody]
    ai_note: str | None  # v0.5：规则判据说明（服务端投影——零 LLM）
    verify: VerifyBody | None
    close_note: str | None


class IssuesResponse(BaseModel):
    lanes: list[str]
    items: list[IssueItemBody]
    page: int  # 分页预留（v0.5——响应回显，00 §4.1 信封）
    page_size: int
    total: int


@router.get("/issues", response_model=IssuesResponse)
async def list_issues(
    service: QualityDep,
    _actor: CurrentActor,  # 权限预埋一行（E2 v0.4 过渡口径）
    lane: Annotated[int | None, Query(ge=0, le=4)] = None,  # 五态筛选（0-4）
    rule_no: Annotated[int | None, Query(ge=1)] = None,  # 规则筛选（v0.3）
    page: Annotated[int, Query(ge=1)] = DEFAULT_PAGE,
    page_size: Annotated[int, Query(ge=1, alias="pageSize")] = DEFAULT_PAGE_SIZE,
) -> IssuesResponse:
    """问题单列表（表格管理：lanes 常量＋五态/规则筛选＋分页预留信封；
    ai_note＝规则判据说明投影，qrows＝隔离区回挂明细）。"""
    result = await service.list_issues(
        lane=lane, rule_no=rule_no, page=page, page_size=page_size
    )
    return IssuesResponse(
        lanes=list(result.lanes),
        items=[
            IssueItemBody(
                id=i.id, lane=i.lane, rule_no=i.rule_no, hit_count=i.hit_count,
                title=i.title, desc=i.desc, owner=i.owner,
                qrows=[QrowBody(loc=q.loc, note=q.note) for q in i.qrows],
                ai_note=i.ai_note,
                verify=VerifyBody(batch=i.verify.batch, note=i.verify.note)
                if i.verify is not None
                else None,
                close_note=i.close_note,
            )
            for i in result.items
        ],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


# ---------- 端点 7：POST /issues/{issue_id}/transitions 五态流转＋复扫 ----------


class TransitionBody(BaseModel):
    action: str | None = None  # 可选 "rescan"（v0.5 人工触发复扫——P2-02 同形）


class TransitionResponse(BaseModel):
    id: str
    lane: int
    state: str
    verify: VerifyBody | None


def _verify_body(receipt: TransitionReceipt) -> VerifyBody | None:
    if receipt.verify is None:
        return None
    return VerifyBody(batch=receipt.verify.batch, note=receipt.verify.note)


@router.post("/issues/{issue_id}/transitions", response_model=TransitionResponse)
async def transition_issue(
    issue_id: str,
    body: TransitionBody,
    service: QualityDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> TransitionResponse:
    """流转到下一态（分发→认领→整改→复核→关闭；终态 409；关闭守卫 422）。

    复扫动作（v0.5）：``action:"rescan"``——仅复核态可复扫（409）；执行缝
    缺省未接＝501（数据面增量复扫通道归 M-05b），接通后回填 verify、lane 不变。
    B12 审计（流转/复扫——行为约定 5）在服务成功返回后落笔。
    """
    receipt = await service.transition_issue(issue_id, actor.who, action=body.action)
    if body.action == RESCAN_ACTION:
        note = receipt.verify.note if receipt.verify is not None else ""
        await security.audit(
            AuditRow(
                who=actor.who,
                action="quality.issue_rescanned",
                content=(
                    f"问题单 {issue_id} 复扫（复核态人工触发，lane 不变）：{note}"
                ),
            )
        )
    else:
        await security.audit(
            AuditRow(
                who=actor.who,
                action="quality.issue_transitioned",
                content=(
                    f"问题单 {issue_id} 流转：{LANES[receipt.lane - 1]}→"
                    f"{LANES[receipt.lane]}"
                ),
            )
        )
    return TransitionResponse(
        id=receipt.issue_id, lane=receipt.lane, state=receipt.state,
        verify=_verify_body(receipt),
    )


# ---------- 端点 8：GET /freshness 三层数据新鲜度水位 ----------


class FreshnessItemBody(BaseModel):
    layer: str
    to: str
    promise: str
    tag: str
    color: str


class FreshnessResponse(BaseModel):
    items: list[FreshnessItemBody]


@router.get("/freshness", response_model=FreshnessResponse)
async def get_freshness(
    service: QualityDep,
    _actor: CurrentActor,  # 权限预埋一行（E2 v0.4 过渡口径）
) -> FreshnessResponse:
    """三层数据新鲜度水位（原始/清洗/汇总；promise=T-1，达标/落后 N 天判定
    后端按 data_date 对 T-1 基准计算——消费 water_line 表）。"""
    return FreshnessResponse(
        items=[
            FreshnessItemBody(
                layer=f.layer, to=f.to, promise=f.promise, tag=f.tag, color=f.color
            )
            for f in await service.freshness()
        ]
    )


# ---------- 端点 9：GET /quarantine 隔离区查询 ----------


class QuarantineItemBody(BaseModel):
    batch_id: str
    rule_no: int
    action: str
    loc: str | None
    payload: dict[str, Any]
    issue_id: str | None
    created_at: str  # 展示串「YYYY-MM-DD HH:mm」（R2——合同示例同形）


class QuarantineResponse(BaseModel):
    items: list[QuarantineItemBody]


@router.get("/quarantine", response_model=QuarantineResponse)
async def list_quarantine(
    service: QualityDep,
    _actor: CurrentActor,  # 权限预埋一行（E2 v0.4 过渡口径）
    batch_id: Annotated[str | None, Query(max_length=64)] = None,
    rule_no: Annotated[int | None, Query(ge=1)] = None,
    issue_id: Annotated[str | None, Query(max_length=32)] = None,
) -> QuarantineResponse:
    """隔离区查询（append-only 读——坏行/被拒批次；batch/rule/issue 三过滤
    可组合；页面问题单详情抽屉按 issue_id 内嵌消费，独立查询页留位）。"""
    rows = await service.list_quarantine(
        batch_id=batch_id, rule_no=rule_no, issue_id=issue_id
    )
    return QuarantineResponse(
        items=[
            QuarantineItemBody(
                batch_id=q.batch_id, rule_no=q.rule_no, action=q.action,
                loc=q.loc, payload=q.payload, issue_id=q.issue_id,
                created_at=q.created_at,
            )
            for q in rows
        ]
    )
