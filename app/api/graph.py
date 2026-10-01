"""api.graph —— /api/graph 路由族（B5-关系图谱.md v0.2 合同，4 条路由＋LLM
起草 1 条实施端点；P1-05）。

形状注记：
- 响应字段 snake_case（00 §14-R1——同 D1/D3/B1 先例）；端点 1 整图一次给
  （高亮/隐显/邻接过滤全为前端本地计算——B5 合同裁决）。
- `lib_id` 必传（GET 走 query、PUT 走 body 字段）；不建 `/api/graph/libs/{id}`
  资源层级（库资源树唯一归属 /api/kb/libs——B5 命名说明）。
- 权限：B5 页全员可见（roles.js MENU B5 无 roles 限制）——组闸不做，身份桩
  依赖（CurrentActor）只解析身份（未认证 401）；写权限细分已关单（开放问题
  1 裁决：阶段 1 系统管理员全权）。
- 端点 3 保存＝待生效配置（下次入库定型不热切换；hint 固定文案服务端返回）；
  同事务记 B1 庑活动流（F62「修改抽取设置」——derivatives 域内经
  kb.record_activity 例外族写口）＋ B12 平台审计留痕（api 层编排——
  P1-02b/P0-05 同款）。
- 端点 4 被拦边清单纯只读（页面不加 UI——治理复盘/E3 天然消费）。
- POST /extract-config/draft-example＝实施端点（B5 出入对账 11 要求真实实现
  起草走 gateway.complete，端点形状合同未冻结——实施定形，挂差异登记）。
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.deps import CurrentActor, GraphDep, SecurityDep
from app.domains.derivatives import (
    BlockedEdgesPage,
    DraftedExample,
    ExtractConfigSaveReceipt,
    ExtractConfigView,
    GraphEdgeView,
    GraphNet,
)
from app.domains.security.domain import AuditRow

router = APIRouter(prefix="/api/graph", tags=["graph"])


# ---------- 端点 1：GET /net 整图读 ----------


class GraphNodeBody(BaseModel):
    id: str
    label: str
    type: str
    short: str
    sub: str


class GraphEdgeBody(BaseModel):
    # 合同字段名 `from`（Python 保留字）——alias 承载（FastAPI by_alias 序列化）。
    key: str
    from_: str = Field(alias="from")
    rel: str
    to: str
    note: str | None
    evidence_chunk_id: str
    report_id: str


class LegendBody(BaseModel):
    type: str
    count: int


class GraphNetResponse(BaseModel):
    lib_id: str
    lib_name: str
    nodes: list[GraphNodeBody]
    edges: list[GraphEdgeBody]
    legend: list[LegendBody]
    stats: dict[str, int]


def _edge_body(e: GraphEdgeView) -> GraphEdgeBody:
    return GraphEdgeBody(
        key=e.key, **{"from": e.from_},
        rel=e.rel, to=e.to, note=e.note,
        evidence_chunk_id=e.evidence_chunk_id, report_id=e.report_id,
    )


@router.get("/net", response_model=GraphNetResponse)
async def graph_net(
    service: GraphDep,
    _actor: CurrentActor,
    lib_id: Annotated[str, Query()],
) -> GraphNetResponse:
    """关系网整图读（节点/边/图例计数/统计——一次给；edges 只含过闸入图的边；
    图谱开关关闭期间一律空态——既有图数据保留/清理属图存储生命周期批）。"""
    net: GraphNet = await service.graph_net(lib_id)
    return GraphNetResponse(
        lib_id=net.lib_id, lib_name=net.lib_name,
        nodes=[
            GraphNodeBody(id=n.id, label=n.label, type=n.type, short=n.short, sub=n.sub)
            for n in net.nodes
        ],
        edges=[_edge_body(e) for e in net.edges],
        legend=[LegendBody(type=lg.type, count=lg.count) for lg in net.legend],
        stats=dict(net.stats),
    )


# ---------- 端点 2：GET /extract-config 抽取设置读 ----------


class RelationTagBody(BaseModel):
    rel: str
    example: str
    desc: str


class FewShotPairBody(BaseModel):
    sentence: str
    triple: str


class ExtractConfigResponse(BaseModel):
    lib_id: str
    lib_name: str
    entity_types: list[str]
    relation_tags: list[RelationTagBody]
    few_shot_examples: list[FewShotPairBody]
    custom_instructions: str
    saved_at: str | None
    saved_by: str | None


@router.get("/extract-config", response_model=ExtractConfigResponse)
async def get_extract_config(
    service: GraphDep,
    _actor: CurrentActor,
    lib_id: Annotated[str, Query()],
) -> ExtractConfigResponse:
    """抽取设置读取（按库四段——F40；未保存过返回出厂默认＝本体对号表投影）。"""
    view: ExtractConfigView = await service.get_extract_config(lib_id)
    return ExtractConfigResponse(
        lib_id=view.lib_id, lib_name=view.lib_name,
        entity_types=list(view.config.entity_types),
        relation_tags=[
            RelationTagBody(rel=t.rel, example=t.example, desc=t.desc)
            for t in view.config.relation_tags
        ],
        few_shot_examples=[
            FewShotPairBody(sentence=p.sentence, triple=p.triple)
            for p in view.config.few_shot_examples
        ],
        custom_instructions=view.config.custom_instructions,
        saved_at=view.saved_at, saved_by=view.saved_by,
    )


# ---------- 端点 3：PUT /extract-config 保存（对号强校＋B1 活动流＋B12 审计） ----------


class ExtractConfigBody(BaseModel):
    lib_id: str
    entity_types: list[str]
    relation_tags: list[dict[str, Any]]
    custom_instructions: str = ""
    few_shot_examples: list[dict[str, Any]] = []


class ExtractConfigSaveResponse(BaseModel):
    lib_id: str
    saved_at: str
    saved_by: str
    hint: str


@router.put("/extract-config", response_model=ExtractConfigSaveResponse)
async def save_extract_config(
    body: ExtractConfigBody,
    service: GraphDep,
    security: SecurityDep,
    actor: CurrentActor,
) -> ExtractConfigSaveResponse:
    """保存抽取设置（待生效——下次入库定型，正在处理的入库任务不受影响；
    对号强校对不上拒存 400 带对号明细；同事务记 B1 活动流「修改抽取设置」）。"""
    receipt: ExtractConfigSaveReceipt = await service.save_extract_config(
        body.lib_id,
        body.model_dump(exclude={"lib_id"}),
        actor.who,
    )
    await security.audit(  # B12 横切留痕——经唯一写口，derivatives 不依赖 security
        AuditRow(
            who=actor.who,
            action="graph.extract_config.saved",
            content=(
                f"抽取设置保存：{body.lib_id} · 实体类型 {len(body.entity_types)} 类"
                f" · 关系标签 {len(body.relation_tags)} 个（下次入库定型）"
            ),
        )
    )
    return ExtractConfigSaveResponse(
        lib_id=receipt.lib_id, saved_at=receipt.saved_at,
        saved_by=receipt.saved_by, hint=receipt.hint,
    )


# ---------- LLM 起草示例（实施端点——三源辅助③，挂差异登记） ----------


class DraftExampleBody(BaseModel):
    lib_id: str
    rel: str
    sentence: str | None = None


class DraftExampleResponse(BaseModel):
    sentence: str
    triple: str


@router.post("/extract-config/draft-example", response_model=DraftExampleResponse)
async def draft_example(
    body: DraftExampleBody,
    service: GraphDep,
    _actor: CurrentActor,
) -> DraftExampleResponse:
    """LLM 起草 few-shot 示例对（带 sentence＝为报告原句预填三元组建议值；
    只带 rel＝按关系词起草一对——人核对后保存，不直接生效）。"""
    drafted: DraftedExample = await service.draft_example(
        body.lib_id, rel=body.rel, sentence=body.sentence
    )
    return DraftExampleResponse(sentence=drafted.sentence, triple=drafted.triple)


# ---------- 端点 4：GET /blocked-edges 被拦边清单（只读） ----------


class BlockedEdgeBody(BaseModel):
    key: str
    from_: str = Field(alias="from")  # 合同字段名 `from`（Python 保留字——alias）
    from_type: str
    rel: str
    to: str
    to_type: str
    reason_code: str
    reason: str
    report_id: str
    report_title: str
    chunk_id: str | None
    blocked_at: str


class BlockedEdgesResponse(BaseModel):
    lib_id: str
    lib_name: str
    blocked_edges: list[BlockedEdgeBody]
    stats: dict[str, int]


@router.get("/blocked-edges", response_model=BlockedEdgesResponse)
async def blocked_edges(
    service: GraphDep,
    _actor: CurrentActor,
    lib_id: Annotated[str, Query()],
) -> BlockedEdgesResponse:
    """被拦边清单只读（被拦边＋拦下原因 reason_code 三值＋所属报告——
    端点 1 过闸边与本端点相加＝抽取尝试全集，「图和库对得上」可追溯）。"""
    page: BlockedEdgesPage = await service.blocked_edges(lib_id)
    return BlockedEdgesResponse(
        lib_id=page.lib_id, lib_name=page.lib_name,
        blocked_edges=[
            BlockedEdgeBody(
                key=b.key, **{"from": b.from_}, from_type=b.from_type, rel=b.rel,
                to=b.to, to_type=b.to_type, reason_code=b.reason_code,
                reason=b.reason, report_id=b.report_id,
                report_title=b.report_title, chunk_id=b.chunk_id,
                blocked_at=b.blocked_at,
            )
            for b in page.blocked_edges
        ],
        stats=dict(page.stats),
    )
