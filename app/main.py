"""Petro-Agent 主平台应用入口。

装配（P0-04 起）：lifespan 建立 ConnectionManager（config/database.yaml，
99 §4.2「config 装载、infra.config 供给」）与 security 服务面，并对 primary
引擎建审计表（ensure_audit_table，幂等 checkfirst——P0-08 前无 Alembic，
真实入口对空库可写审计/读 audit-logs）；P0-05 起 gateway 服务面入装配
（infra.llm_client 为 B6 唯一 SDK 接触点——complete 面 gateway 唯一出口、
embedding 面经 llm_client.embeddings）并对
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
（B9 同款——faq 运行期只见 callable）＋遗留 running 扫库行启动收口。P1-07 起
retrieval 域点亮：retrieval 两表入装配（ensure_retrieval_tables——99 §2.10，
Alembic 0008 并行）＋/api/retrieval 路由族挂载（D2 两端点——配置读＋变更单，
阶段 1 提交即生效：版本推进＋via 回链＋B12 审计；首次读取自动落种子）。P1-08a
起 chat 域点亮（A1 主链第一拍）：chat 三表入装配（ensure_chat_tables——
99 §2.2，Alembic 0009 并行）＋/api/chat 路由族填肉（asks 四层流水线 SSE＋
runs resume 澄清续推）＋域读缝经组合根注入（qa 配置/指标台账/术语台账/FAQ
索引/报告索引——B9 同款运行期只见 callable）＋A1 会话料源缝收口（faq
session_loader 注入 chat.recent_qa_pairs——P1-06 疑点 6，装配即通）。P1-08b
起三链链体点亮（A1 主链第二拍）：检索瀑布链（D2 生效配置驱动 S0–S7 全链——
三级开关/命中即停/双路并发/RRF/精排三档/资格裁决/权威回读/citation
fail-closed/兜底两策）＋FAQ 秒回链（直出＋no_model）＋图谱问答链（真 Neo4j
邻域检索——graph_searcher 缝填入）；kb 增 index_search_dual/fragment_anchor
读面与 hit_text pg_trgm GIN 索引（Alembic 0010 并行），faq 增 search_similar
扩检读面；chat 链内 LLM 只走注入 completer（B6——gateway.complete 别名
petro-main）。P1-11 收口批：embedding 真模型接线（petro-embed＝MiniMax
embo-01 1536 维——infra.llm_client.embeddings B6 单点，kb/faq db/query 分型
两缝；Alembic 0012 列形迁移＋reembed 重嵌脚本）；LLM 意图裁决接线
（caller=chat.intent.verdict，失败/超时/解析坏兜底确定性信号路由）；A1 端点
2/6 会话与 @ 资产读端点；C1 端点 11 slots 投影读端点；B3 导入 multipart 落位。
P2-M-02 起 wells 域点亮（A2 井档案四端点）：midplatform 只读路由启动校验接线
（M-01 交付的 verify_midplatform_route——缺依赖拒绝启动）＋well_status_log
补位表入装配（99 §2.3，Alembic 0017 并行；写入通道挂 99 开放问题 2，本批只落
读面）＋/api/wells 路由族挂载（行级过滤预埋缝消费——M-01 with_row_filter 两步缝）。
M-05a 起 dataops/quality 域点亮（E2 质检台管理面半边）：quality 表族入
装配（ensure_quality_tables——99 §2.12，Alembic 0015 并行；种子随迁移承载）
＋/api/quality 路由族挂载（规则读面/启停、问题单五态状态机、水位 T-1 判定、
隔离区读面）。M-05b 起 E2 执行通道点亮（任务表轮询形态——DP-04 交付适配，
接口合同＝quality_task 行形零共享库）：quality_task 第六表入装配（M-05a
留注兑现——任务受理/轮询/接续/历史消费面）＋端点 3/4/5 接通（受理落行即
触发面；done 接续建单/挂单/隔离行回挂 step→4；历史倒序）＋复扫执行缝生产
装配（DataPlaneChannelRescanExecutor 经组合根两段绑定——数据面质检通道
适配器，B9 运行期只见 callable）。

建表与迁移的交接（P0-08 票面）：ensure_*_table 与 Alembic 并行存活，
本票不切换——各域切换迁移属各域票（基线空迁移见 migrations/versions/0001）。
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.errors import install_error_handlers
from app.api.faq import router as faq_router
from app.api.gateway import router as gateway_router
from app.api.graph import router as graph_router
from app.api.kb import router as kb_router
from app.api.quality import router as quality_router
from app.api.retrieval import router as retrieval_router
from app.api.security import router as security_router
from app.api.semantics import router as semantics_router
from app.api.wells import router as wells_router
from app.api.wiki import router as wiki_router
from app.domains.chat import (
    ChatService,
    FaqHitFace,
    FragmentAnchorFace,
    GraphHitFace,
    IndexHitFace,
    MetricFace,
    RetrievalConfigFace,
    TermFace,
)
from app.domains.chat.store import ensure_chat_tables
from app.domains.dataops.quality import (
    QualityService,
    bind_channel_rescan,
    ensure_quality_tables,
)
from app.domains.derivatives import DerivativesService
from app.domains.derivatives.service import load_extract_config_snapshot
from app.domains.derivatives.store import ensure_derivatives_tables
from app.domains.faq import FaqService
from app.domains.faq.store import ensure_faq_tables, seed_demo_if_empty
from app.domains.gateway import GatewayService
from app.domains.gateway.store import ensure_gateway_tables
from app.domains.kb import KbService
from app.domains.kb.domain import RemoteEmbedder
from app.domains.kb.store import ensure_kb_tables
from app.domains.retrieval import RetrievalService
from app.domains.retrieval.store import ensure_retrieval_tables
from app.domains.security import SecurityService
from app.domains.security.store import ensure_audit_table
from app.domains.semantics import SemanticsService
from app.domains.semantics.store import ensure_semantics_tables
from app.domains.wells import WellsService, ensure_wells_tables
from app.infra.config import load_database_specs
from app.infra.db import ConnectionManager
from app.infra.eventbus import InMemoryEventBus, ensure_outbox_table
from app.infra.graph_store import Neo4jGraphStore
from app.infra.llm_client import LlmClient
from app.infra.object_storage import MinioObjectStorage

LOGGER = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    manager = ConnectionManager(load_database_specs())
    # midplatform 只读路由启动校验（M-01 交付——接线随消费票 M-02 带上）：
    # 缺配置/规格未只读/写探针未被拒即 MidplatformRouteError 拒启动（生产缺
    # 依赖拒绝启动，禁静默降级——M-01 反数据面静默降级病灶）。
    await manager.verify_midplatform_route()
    await ensure_audit_table(manager.engine())  # 幂等（checkfirst）——空库首次写审计不 500
    await ensure_gateway_tables(manager.engine())  # 同上——网关三表（99 §2.13）
    await ensure_outbox_table(manager.engine())  # 同上——infra 技术表（99 §6-4 outbox 兜底缝）
    await ensure_semantics_tables(manager.engine())  # 同上——sem_* 九表（99 §2.8；P1-01 起
    #   与 Alembic 0002_sem_baseline 并行存活——各域切迁移属各域票，操作序照 P0-08 登记）
    await ensure_kb_tables(manager.engine())  # 同上——kb 八表（99 §2.5；PG 先建 pgvector 扩展）
    await ensure_derivatives_tables(manager.engine())  # 同上——wiki 表族（99 §2.7；P1-02b）
    await ensure_faq_tables(manager.engine())  # 同上——faq 四表（99 §2.6；P1-06，Alembic 0007 并行）
    await ensure_retrieval_tables(manager.engine())  # 同上——retrieval 两表（99 §2.10；P1-07 并行）
    await ensure_chat_tables(manager.engine())  # 同上——chat 三表（99 §2.2；P1-08a 并行）
    await ensure_wells_tables(manager.engine())  # 同上——well_status_log 补位表（99 §2.3；M-02，
    #   Alembic 0017 并行——写入通道挂 99 开放问题 2，本批只落读面承载）
    await ensure_quality_tables(manager.engine())  # 同上——quality 表族六表（99 §2.12；
    #   Alembic 0015 并行——种子（20 条规则）随迁移 0015 承载，ORM 侧不重播；
    #   quality_task 第六表 M-05b 起随任务通道消费面登记）
    await seed_demo_if_empty(manager.engine())  # 演示种子（合同 DTO 九条问答＋四簇候选——幂等）
    app.state.db = manager
    app.state.security = SecurityService(manager)
    app.state.wells = WellsService(manager)  # A2 井档案读模型（M-02——纯读域）
    # E2 质检台（M-05a 管理面＋M-05b 执行通道）：复扫执行缝生产装配＝数据面
    # 质检通道适配器（任务表轮询——channel.py；组合根两段绑定消解服务环，
    # B9 同款运行期只见 callable；缺省未接＝501 诚实壳——测试底座形态）。
    quality = QualityService(manager)
    bind_channel_rescan(quality, manager)
    app.state.quality = quality
    app.state.gateway = GatewayService(manager, LlmClient())
    app.state.semantics = SemanticsService(manager, app.state.security)  # B12 审计写口注入
    app.state.retrieval = RetrievalService(manager)  # D2 配置面（P1-07——B12 审计在 api 层编排）
    # 事件总线（98 §4——IngestCompleted 由 derivatives 订阅，B9 不直调；进程内
    # 实现＝单进程演示底座，Redis Streams 通道接线属后续接线批，P0-08 同口径）
    app.state.eventbus = InMemoryEventBus()
    storage = MinioObjectStorage()  # 对象存储 seam（B1 直传/B3 导入导出共用——98 §4 adapter）
    # 向量真模型（P1-11 选型接线——petro-embed＝MiniMax embo-01 1536 维，B6
    # 单点 infra.llm_client.embeddings；query/db 分型两实例禁混——kb 检索探针/
    # faq 扩检走 query 型，语料/入库走 db 型。测试底座 LocalHash 只在测试装配）。
    llm = LlmClient()
    kb_embedder = RemoteEmbedder(llm, input_type="db")
    kb_query_embedder = RemoteEmbedder(llm, input_type="query")
    faq_embedder = kb_embedder  # kb/faq 同源同实现（99 同一款向量缝）
    faq_query_embedder = kb_query_embedder
    app.state.kb = KbService(
        manager,
        app.state.gateway,  # B6：LLM 只走 gateway.complete
        storage,
        embedder=kb_embedder,
        query_embedder=kb_query_embedder,
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
    # A1 历史会话料源缝（session_loader）P1-08a 起注入 chat.recent_qa_pairs。
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

    # chat 域读缝（P1-08a 立缝、P1-08b 三链填肉——B9 同款：运行期只见 callable，
    # 不 import 各域）：D2 生效配置（retrieval.effective_config 全量投影——检索链
    # 六配置节消费）/指标台账/术语台账（semantics 读接口——B5 边界：六路匹配器
    # 必须走 semantics 读口）/FAQ 索引（faq.match_index 精确路＋search_similar
    # 扩检路——lazy 绑定，faq 在本域之后装配）/报告索引（kb.index_search 装配
    # 合并路＋index_search_dual 双路——向量＋trigram 两腿，P1-08b 检索链 S4）/
    # 图谱缝（08b 起真图检索：图开关开启的库逐座读整图、问句实体匹配一跳邻域）/
    # 片段锚校验（kb.fragment_anchor——citation fail-closed）。
    async def retrieval_config_loader() -> RetrievalConfigFace:
        snapshot = await app.state.retrieval.effective_config()
        order, params, qa = snapshot.order, snapshot.params, snapshot.qa_behavior
        return RetrievalConfigFace(
            order_levels=(
                order.levels[0].enabled, order.levels[1].enabled, order.levels[2].enabled,
            ),
            early_stop=order.early_stop,
            semantic_top_k=params.semantic_top_k,
            keyword_top_k=params.keyword_top_k,
            merge=params.merge,
            top_n=params.top_n,
            rerank=snapshot.rerank,
            citation_format=snapshot.citation_format,
            fallback_strategy=snapshot.fallback.strategy,
            fallback_text=snapshot.fallback.text,
            faq_direct_hit=qa.faq_direct_hit,
            refuse_threshold=qa.refuse_threshold,
            clarify_strategy=qa.clarify_strategy,
            confidence_high=qa.confidence_thresholds.high,
            confidence_low=qa.confidence_thresholds.low,
            faq_expand_rounds=qa.faq_expand_rounds,
        )

    async def metrics_loader() -> list[MetricFace]:
        page = await app.state.semantics.list_metrics(page_size=1000)
        return [
            MetricFace(
                metric_id=int(row.id),
                name=str(row.name),
                slot_name=str(row.slot_name),
                ambiguous=bool(row.ambiguous),
                calibers=list(row.calibers or []),
                default_caliber=row.default_caliber,
                # P-004 修复拍二①（授权触界）：status 透传——指标卡状态标注生产
                # 非空；sem jsonb 数组形态原样携入（装卡侧 metric_card_status_note
                # 已备归一——list「／」join、禁 str() 直透垃圾串）。
                status=list(row.status),
            )
            for row in page.items
        ]

    async def terms_loader() -> list[TermFace]:
        page = await app.state.semantics.list_terms(page_size=1000)
        return [
            TermFace(
                term_id=int(row.id),
                term=str(row.term),
                type=str(row.type),
                def_text=str(row.def_),
                # P-004 修复拍①（授权触界一次）：状态三字段透传——词条卡状态标注
                # 生产非空；「已届满」标注依赖 expires_at（三字段一组投影）。
                status=str(row.status),
                status_key=str(row.status_key),
                expires_at=row.expires_at,
            )
            for row in page.items
        ]

    async def faq_matcher(text: str) -> FaqHitFace | None:
        hit = await app.state.faq.match_index(text)
        if hit is None:
            return None
        return FaqHitFace(entry_id=hit.entry_id, question=hit.question, answer=hit.answer)

    async def faq_searcher(text: str, top_k: int) -> list[FaqHitFace]:
        hits = await app.state.faq.search_similar(text, top_k)
        return [
            FaqHitFace(entry_id=h.entry_id, question=h.question, answer=h.answer, score=h.score)
            for h in hits
        ]

    async def faq_lister() -> list[str]:
        questions: list[str] = list(await app.state.faq.served_questions())
        return questions

    async def workflow_lister() -> list[tuple[str, str]]:
        rows = await app.state.semantics.list_workflows()
        return [(str(row.name), str(row.status)) for row in rows]

    async def report_lister() -> list[str]:
        rows = await app.state.kb.list_reports()
        return [str(row.doc) for row in rows]

    async def index_searcher(question: str) -> list[IndexHitFace]:
        hits = await app.state.kb.index_search(question)
        return [
            IndexHitFace(
                fragment_id=h.fragment_id, report_id=h.report_id, report=h.report,
                section=h.section, snippet=h.snippet, score=h.score, leg=h.leg,
                text=h.text,
            )
            for h in hits
        ]

    async def index_searcher_dual(
        question: str, vector_top_k: int, keyword_top_k: int
    ) -> tuple[list[IndexHitFace], list[IndexHitFace]]:
        vector, keyword = await app.state.kb.index_search_dual(
            question, vector_top_k=vector_top_k, keyword_top_k=keyword_top_k
        )
        def _face(h: Any) -> IndexHitFace:
            return IndexHitFace(
                fragment_id=h.fragment_id, report_id=h.report_id, report=h.report,
                section=h.section, snippet=h.snippet, score=h.score, leg=h.leg,
                text=h.text,
            )
        return [_face(h) for h in vector], [_face(h) for h in keyword]

    async def fragment_anchor_loader(fragment_id: str) -> FragmentAnchorFace | None:
        anchor = await app.state.kb.fragment_anchor(fragment_id)
        if anchor is None:
            return None
        return FragmentAnchorFace(
            fragment_id=anchor.fragment_id, report_id=anchor.report_id,
            report=anchor.report, section=anchor.section,
        )

    async def graph_searcher(question: str) -> list[GraphHitFace]:
        """图谱缝真检索（P1-08b——图谱问答链候选源＋边出处）：图开关开启的库逐
        座读整图，问句中出现的实体取一跳邻域边（F45 遍历深度 1 跳——阶段 1 演示
        量级）。图存储不可用记告警不阻断问答（B5 端点语义不变——管理面显式抛错）。"""
        needle = question
        faces: list[GraphHitFace] = []
        try:
            for lib in await app.state.kb.list_libraries(graph="on"):
                net = await app.state.graph.read_net(lib.id)
                matched = {
                    str(node.get("id", ""))
                    for node in net.get("nodes", [])
                    if str(node.get("id", "")) in needle
                    or str(node.get("short", "")) in needle
                    or str(node.get("label", "")) in needle
                }
                matched.discard("")
                for edge in net.get("edges", []):
                    if edge.get("from") in matched:
                        faces.append(GraphHitFace(
                            entity=str(edge.get("from", "")),
                            relation=f"{edge.get('rel', '')} → {edge.get('to', '')}",
                            evidence=str(edge.get("evidence") or "") or None,
                            source_chunk_id=str(edge.get("chunk_id") or "") or None,
                            source_report_id=str(edge.get("report_id") or "") or None,
                        ))
                    elif edge.get("to") in matched:
                        faces.append(GraphHitFace(
                            entity=str(edge.get("to", "")),
                            relation=f"{edge.get('rel', '')} ← {edge.get('from', '')}",
                            evidence=str(edge.get("evidence") or "") or None,
                            source_chunk_id=str(edge.get("chunk_id") or "") or None,
                            source_report_id=str(edge.get("report_id") or "") or None,
                        ))
        except Exception:  # 图存储不可用不阻断问答（告警留痕）
            LOGGER.warning("chat 图谱缝检索不可用——按落空处理（B9 缝）", exc_info=True)
        return faces[:8]

    app.state.chat = ChatService(
        manager,
        audit=app.state.security,  # B12：chat.ask.received/blocked（受理/拦截留痕）
        config_loader=retrieval_config_loader,
        metrics_loader=metrics_loader,
        terms_loader=terms_loader,
        faq_matcher=faq_matcher,
        faq_searcher=faq_searcher,
        index_searcher=index_searcher,
        index_searcher_dual=index_searcher_dual,
        graph_searcher=graph_searcher,  # 08b 起真图检索（B9 同款只见 callable）
        anchor_loader=fragment_anchor_loader,  # citation fail-closed 校验缝
        completer=app.state.gateway,  # B6：链内生成/打分/意图裁决只走 gateway.complete
        faq_lister=faq_lister,  # A1 端点 6 assets 投影（lazy 绑定——faq 在本域之后装配）
        workflow_lister=workflow_lister,
        report_lister=report_lister,
    )

    app.state.faq = FaqService(
        manager,
        app.state.gateway,
        storage,
        embedder=faq_embedder,
        query_embedder=faq_query_embedder,
        eventbus=app.state.eventbus,
        audit=app.state.security,  # B12（LedgerMerged 联动建议稿留痕）
        ledger_loader=ledger_loader,
        slice_loader=slice_loader,
        ontology_names_loader=ontology_names_loader,
        kb_corpus_loader=kb_corpus_loader,
        # session_loader：A1 历史会话料源（B3-5 拍板）——P1-08a 会话域点亮即注入
        # （chat.recent_qa_pairs，P1-06 疑点 6 收口：装配即通，扫库不再空态）。
        session_loader=app.state.chat.recent_qa_pairs,
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
app.include_router(retrieval_router)  # D2 搜索与回答·配置面（P1-07——retrieval 模块，98 §5）
app.include_router(wells_router)  # A2 井档案（M-02——wells 模块，98 §5；纯读域）
# E2 数据质量台（M-05a 管理面＋M-05b 任务执行通道——dataops/quality 模块）
app.include_router(quality_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
