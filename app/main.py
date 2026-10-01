"""Petro-Agent 主平台应用入口。

装配（P0-04 起）：lifespan 建立 ConnectionManager（config/database.yaml，
99 §4.2「config 装载、infra.config 供给」）与 security 服务面，并对 primary
引擎建审计表（ensure_audit_table，幂等 checkfirst——P0-08 前无 Alembic，
真实入口对空库可写审计/读 audit-logs）；P0-05 起 gateway 服务面入装配
（infra.llm_client 为 B6 唯一 SDK 接触点，gateway 是其唯一消费方）并对
primary 引擎建网关三表（spend 账本/演练/预算单例）；P0-08 起 infra_outbox
技术表入装配（99 §6-4——eventbus 兜底缝）＋ /api/chat 骨架路由挂载；统一
错误包（00 §3）与 D3/D1 路由挂载。端点随票落地（tickets/phase0/）。
P1-01 起 sem_* 九表入装配（ensure_semantics_tables——sem 域迁移首执行点，
与 Alembic 0002_sem_baseline 并行存活，操作序照 P0-08 登记）。P1-02a 起 kb
八表入装配（ensure_kb_tables——PG 先 CREATE EXTENSION vector）＋ /api/kb
路由族挂载＋入库任务 stuck 收口（启动巡检——00 §5.2-6 超时无进展后台巡检）。
P1-02b 起 wiki 表族入装配（ensure_derivatives_tables）＋/api/wiki 路由族挂载
＋derivatives 事件订阅接线（IngestCompleted→wiki 生成/重建、FragmentRevised
→重铸队列——B9 缝：kb 不直调 derivatives，派生物只经事件）。P1-04 起
kb_issue_report 入 kb 表族（ensure_kb_tables——B2 质检复核队列，六端点挂
api/kb.py）。P1-05 起 graph 子域点亮：kb_extract_config 入 derivatives 表族
（99 §2.7——仍留 PG）＋/api/graph 路由族挂载＋图存储装配（infra.graph_store
→Neo4jGraphStore，ADR-0003 裁决 2——B3 出口之外的图专用接触面）＋抽取设置
定型快照装载经组合根注入 kb（B9：kb 只见 callable，禁 import derivatives）
＋IngestCompleted graph 支路接线（config_snapshot.graph=true→逐 chunk LLM 抽
三元组、过铁律三闸入图、拦下记 blocked-edges）。P1-06 起 faq 域点亮：faq 四表
入装配（ensure_faq_tables＋演示种子——99 §2.6）＋/api/faq 路由族挂载（B3 十七
端点）＋LedgerMerged 事件订阅接线（B3-2 口径修订联动：按 hook 检出→LLM 起草
建议→进待审核，不自动直改）＋台账口径/切片原文/本体/知识库面读缝经组合根注入
（B9 同款——faq 运行期只见 callable）＋遗留 running 扫库行启动收口。

建表与迁移的交接（P0-08 票面）：ensure_*_table 与 Alembic 并行存活，
本票不切换——各域切换迁移属各域票（基线空迁移见 migrations/versions/0001）。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.errors import install_error_handlers
from app.api.faq import router as faq_router
from app.api.gateway import router as gateway_router
from app.api.graph import router as graph_router
from app.api.kb import router as kb_router
from app.api.security import router as security_router
from app.api.semantics import router as semantics_router
from app.api.wiki import router as wiki_router
from app.domains.derivatives import DerivativesService
from app.domains.derivatives.service import load_extract_config_snapshot
from app.domains.derivatives.store import ensure_derivatives_tables
from app.domains.faq import FaqService
from app.domains.faq.store import ensure_faq_tables, seed_demo_if_empty
from app.domains.gateway import GatewayService
from app.domains.gateway.store import ensure_gateway_tables
from app.domains.kb import KbService
from app.domains.kb.domain import LocalHashEmbedder
from app.domains.kb.store import ensure_kb_tables
from app.domains.security import SecurityService
from app.domains.security.store import ensure_audit_table
from app.domains.semantics import SemanticsService
from app.domains.semantics.store import ensure_semantics_tables
from app.infra.config import load_database_specs
from app.infra.db import ConnectionManager
from app.infra.eventbus import InMemoryEventBus, ensure_outbox_table
from app.infra.graph_store import Neo4jGraphStore
from app.infra.llm_client import LlmClient
from app.infra.object_storage import MinioObjectStorage


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    manager = ConnectionManager(load_database_specs())
    await ensure_audit_table(manager.engine())  # 幂等（checkfirst）——空库首次写审计不 500
    await ensure_gateway_tables(manager.engine())  # 同上——网关三表（99 §2.13）
    await ensure_outbox_table(manager.engine())  # 同上——infra 技术表（99 §6-4 outbox 兜底缝）
    await ensure_semantics_tables(manager.engine())  # 同上——sem_* 九表（99 §2.8；P1-01 起
    #   与 Alembic 0002_sem_baseline 并行存活——各域切迁移属各域票，操作序照 P0-08 登记）
    await ensure_kb_tables(manager.engine())  # 同上——kb 八表（99 §2.5；PG 先建 pgvector 扩展）
    await ensure_derivatives_tables(manager.engine())  # 同上——wiki 表族（99 §2.7；P1-02b）
    await ensure_faq_tables(manager.engine())  # 同上——faq 四表（99 §2.6；P1-06，Alembic 0007 并行）
    await seed_demo_if_empty(manager.engine())  # 演示种子（合同 DTO 九条问答＋四簇候选——幂等）
    app.state.db = manager
    app.state.security = SecurityService(manager)
    app.state.gateway = GatewayService(manager, LlmClient())
    app.state.semantics = SemanticsService(manager, app.state.security)  # B12 审计写口注入
    # 事件总线（98 §4——IngestCompleted 由 derivatives 订阅，B9 不直调；进程内
    # 实现＝单进程演示底座，Redis Streams 通道接线属后续接线批，P0-08 同口径）
    app.state.eventbus = InMemoryEventBus()
    storage = MinioObjectStorage()  # 对象存储 seam（B1 直传/B3 导入导出共用——98 §4 adapter）
    faq_embedder = LocalHashEmbedder()  # 占位向量缝（kb/faq 同源同实现——99 维度待办）
    app.state.kb = KbService(
        manager,
        app.state.gateway,  # B6：LLM 只走 gateway.complete
        storage,
        embedder=faq_embedder,
        eventbus=app.state.eventbus,
        # 抽取设置定型快照装载（B5 端点 3 注记——confirm 时刻一并定型；
        # 组合根注入 derivatives 提供的函数——B9：kb 禁 import derivatives）
        extract_snapshot_loader=lambda lib_id: load_extract_config_snapshot(
            manager, lib_id
        ),
    )
    # 图存储（98 §4 adapter 清单——infra.graph_store/Neo4j，ADR-0003 裁决 2）
    app.state.graph = Neo4jGraphStore()
    # derivatives wiki＋graph 支路（B9：订阅 kb 事件，不与 kb 直接互调；semantics
    # 只读接口供台账挂接词表——B5 读接口纪律）
    app.state.derivatives = DerivativesService(
        manager,
        app.state.gateway,
        app.state.kb,
        app.state.semantics,
        graph=app.state.graph,
    )

    # faq 域（P1-06——98 §3.3）：台账口径/切片原文/本体命中/知识库面语料经组合根
    # 注入公开读缝（B9 同款——faq 运行期不 import semantics/kb，只见 callable）；
    # A1 历史会话料源缝（session_loader）暂缺——A1 未上线，扫库空态说明收场。
    async def ledger_loader(kind: str, ref_id: int) -> tuple[str, str, str] | None:
        if kind == "metric":
            row = await app.state.semantics.get_metric(ref_id)
            if row is None:
                return None
            return row.slot_name, row.def_, f"C1 指标卡「{row.slot_name}」"
        row = await app.state.semantics.get_term(ref_id)
        if row is None:
            return None
        return row.term, row.def_, f"C1 术语台账「{row.term}」"

    async def slice_loader(report_id: str, fragment_id: str) -> tuple[str, str] | None:
        listing = await app.state.kb.list_fragments(report_id)
        item = next((f for f in listing.items if f.id == fragment_id), None)
        if item is None:
            return None
        return item.hit, f"《{item.report}》{item.section or ''}"

    async def ontology_names_loader() -> list[tuple[str, str]]:
        metrics = await app.state.semantics.list_metrics(page_size=1000)
        terms = await app.state.semantics.list_terms(page_size=1000)
        objects = await app.state.semantics.list_objects(page_size=1000)
        faces = [("指标卡", str(getattr(m, "slot_name", ""))) for m in metrics.items]
        faces += [("术语", str(getattr(t, "term", ""))) for t in terms.items]
        faces += [("井对象", str(getattr(o, "obj", ""))) for o in objects.items]
        return faces

    async def kb_corpus_loader() -> list[str]:
        corpus: list[str] = list(await app.state.kb.dedup_corpus())
        return corpus

    app.state.faq = FaqService(
        manager,
        app.state.gateway,
        storage,
        embedder=faq_embedder,
        eventbus=app.state.eventbus,
        audit=app.state.security,  # B12（LedgerMerged 联动建议稿留痕）
        ledger_loader=ledger_loader,
        slice_loader=slice_loader,
        ontology_names_loader=ontology_names_loader,
        kb_corpus_loader=kb_corpus_loader,
        # session_loader：A1 历史会话料源（B3-5 拍板）——A1 会话域未上线暂缺，
        # 扫库落空态说明；A1 装配批注入本缝即通。
    )
    await app.state.eventbus.subscribe(
        "IngestCompleted", app.state.derivatives.on_ingest_completed
    )
    await app.state.eventbus.subscribe(
        "FragmentRevised", app.state.derivatives.on_fragment_revised
    )
    await app.state.eventbus.subscribe(  # B3-2 口径修订联动（B3 合同 v0.2）
        "LedgerMerged", app.state.faq.on_ledger_merged
    )
    # 崩溃重启的遗留 running 演练行收口为 done（幂等；否则 has_running 恒真
    # → 所有 start_drill 永久 409——P0-05 审查收口）；kb 任务体同为进程内
    # asyncio task——遗留 running 入库任务收口 stuck（四态合同值，重试内含停止）；
    # faq 扫库行收口 done（双态合同值，可重新发起）。
    await app.state.gateway.close_stale_drills()
    await app.state.kb.sweep_stuck()
    await app.state.faq.close_stale_scans()
    yield
    await app.state.graph.close()
    await manager.dispose()


app = FastAPI(title="petro-agent-platform", version="0.1.0", lifespan=lifespan)
install_error_handlers(app)
app.include_router(security_router)
app.include_router(gateway_router)
app.include_router(chat_router)
app.include_router(semantics_router)  # C1 台账读面（P1-01b——semantics 模块，98 §5）
app.include_router(kb_router)  # B1 报告库（P1-02a——kb 模块，98 §5）
app.include_router(wiki_router)  # B4 报告百科（P1-02b——derivatives 模块，98 §5）
app.include_router(graph_router)  # B5 关系图谱（P1-05——derivatives graph 子域，98 §5）
app.include_router(faq_router)  # B3 常见问题库（P1-06——faq 模块，98 §5）


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
