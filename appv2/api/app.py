"""appv2.api.app —— appv2 自有 app 工厂（V2-07 票面红线：挂线路由注册进
appv2 工厂，V1 app/main.py 路由零改动）。

组合缝（modules.md 边界规则「api 业务面只许走 orchestration 公开接口」的落法）：
本工厂只 import `appv2.runtimev2`（编排包根＝受理三形状＋装配面；persistence 装配缝；
gateway_adapter 注入缝；transport 帧类型）＋`appv2.infra`——引擎侧组合根（knowledge/
query/retrieval → ToolRegistry）与 completer（模型出口同面缝）由调用方注入；
**registry 缺省（None）＝生产组合**（V2-19 票面任务 4——三引擎生产读面真装配＋DE-16
消费点，`compose_production_registry` 局部 import 引擎与 tools 包装配，属 modules.md
api 卡注记的组合根例外延伸）。fixture 组合（测试）照旧经 registry 参数显式注入。

装配面（RT-W5-02 改接后——runtimev2 面）：
`RunExecutor`（orchestration 包根：受理／驱动／三态收口／检查点 saver 由其内部组合）
→ `AgentRuntime`；模型出口经 `set_completer` 注入同面缝（生产＝`gateway_adapter.
GatewayBridge`，测试＝`ScriptedCompleter`）；审计唯一写口经 `persistence.
configure_audit_sink` 注入 `security.audit` 桥（B12）；台账投影端口经 `context.
wire_ledger_projection` 注入本层 dump 缝；`RunStreamRegistry`（SSE 帧桥缓冲）＋
`RunStore`（簿记两读口）入 `app.state`（deps 定位消费）；lifespan 幂等建表（簿记端口
建表清单＋gateway 三表＋富化索引表——P0-08 先例同款）。

**装配形状两处适配（如实登记，见 `tickets/v2-refactor/RT-W5-02-api-v2端点与SSE桥.md`
偏差清单）**：① 编排块注入形是**值**（`watermark`＝水位日 date／`data_wells`＝井闭世界
集合），本层生产缝是 **loader**（`Callable[[], …]`，旧「零缓存逐调用」语义）——本层在
组合根**取一次**（启动快照），逐调用刷新语义有差；② 台账投影端口是**异步**口，本层
dump 缝是同步缝——由 `LedgerProjectionAdapter` 单点适配（端口形状真源＝
`appv2.runtimev2.context.ledger`）。

**§A 指南段注入（流水 63）**：`guide_text`＝编排块 `RunExecutor`／相位 `clarify`／`match`
的**文本注入值**（str）——生产缺省＝启动取一次快照
（`OntologyGuideProvider(...).guide()`，同 ①② 的「取一次」纪律；`{max_rounds}`／
`{max_discovers}`／`{max_executes}` 三占位符取 `Budget` 三键——
`rounds`／`discovers_per_round`／`executes_per_round`，非 provider 缺省值）。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from datetime import date
from typing import Any, cast

from fastapi import FastAPI

from appv2.api.bridge import RunStreamRegistry
from appv2.api.chat import router as chat_router
from appv2.api.errors import install_error_handlers
from appv2.api.ontology_guide import OntologyGuideProvider
from appv2.infra import clock as infra_clock
from appv2.infra.config import ChatSettings
from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.infra.gateway.store import ensure_gateway_tables
from appv2.infra.security import AuditRow, SecurityService
from appv2.runtimev2.context import wire_ledger_projection
from appv2.runtimev2.gateway_adapter import set_completer
from appv2.runtimev2.orchestration import AgentRuntime, Budget, RunExecutor
from appv2.runtimev2.persistence import (
    AuditRecord,
    RunStore,
    configure_audit_sink,
)

_LOGGER = logging.getLogger(__name__)


class LedgerProjectionAdapter:
    """台账投影端口件（`context.LedgerProjectionPort` 形 ← 本层 dump 缝）。

    端口形状真源＝`appv2.runtimev2.context.ledger`（`async def fetch() -> Mapping | None`；
    「真实现形待核定」——本层按端口形状适配**本层既有**的 dump 缝：同步 dump 直接 await 化，
    成功面／失败面不变（异常上抛 → `context.load_ledger_dump` 的 fail-fast 捕获面：
    异常＝装载失败，返回 `None`＝工具面 failed 态）。
    """

    def __init__(self, dump: Callable[[], Mapping[str, Any]]) -> None:
        self._dump = dump

    async def fetch(self) -> Mapping[str, Any] | None:
        return self._dump()


class SecurityAuditSink:
    """审计唯一写口桥（B12）：`persistence` 同步写面 → `security.audit` 异步写口。

    装配点＝本层组合根（`persistence.configure_audit_sink` 的**唯一**替换缝）；真源
    `specs/persistence.md` 接口定义节行原文「`def audit(record: AuditRecord) -> None   # 唯一写口＝
    security.audit（B12）」——写面同步、`SecurityService.audit` 异步，故本桥把落库协程投递到
    **当前事件环**（编排侧五处留痕都在请求／驱动任务内调用，恒有运行环）：

    - 无运行环＝`RuntimeError` 上抛（不静默吞——编排侧发射守卫转 `audit_write_failed` 通知）；
    - 投递后落库失败由任务回调**日志留痕**（`_LOGGER.error`）：同步写面拿不到异步结果，故落库
      失败不进编排的 `audit_write_failed` 通道（该通道只覆盖「写口不可用」这一面——如实登记）。
    """

    def __init__(self, service: SecurityService) -> None:
        self._service = service
        self._tasks: set[asyncio.Task[None]] = set()

    def __call__(self, record: AuditRecord) -> None:
        loop = asyncio.get_running_loop()
        task = loop.create_task(self._service.audit(_audit_row(record)))
        self._tasks.add(task)
        task.add_done_callback(self._settle)

    def _settle(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:  # 落库失败不静默（同步写面拿不到结果——日志留痕面）
            _LOGGER.error("审计落库失败（责任账缺口）：%r", error)


def _audit_row(record: AuditRecord) -> AuditRow:
    """留痕记录 → `security.audit` 入参（四要素逐槽落位单点）。

    - `who` → 操作者槽；`action` → 动作槽（取值已是 `agent_v2.*` 前缀闭世界）；
    - `facts`（人话事实摘要）→ 内容槽（D3 读面只落 digest，正文不入读面）；
    - `run_id`／`scope`（范围键）／`authorization`（授权依据＝审批单号）／`evidence`（结果面）
      → `meta` 预留位（`AuditRow` 四槽不含这四件——槽形真源 `appv2.infra.security.AuditRow`）。
    """
    return AuditRow(
        who=record.who,
        action=record.action,
        content=record.facts,
        meta={
            "run_id": record.run_id,
            "scope": record.scope,
            "authorization": record.authorization,
            "evidence": record.evidence,
        },
    )


def compose_production_registry(
    *,
    specs: Sequence[DatabaseSpec] | None = None,
    chat_settings: ChatSettings | None = None,
    today: Callable[[], date] | None = None,
    embedder: Any | None = None,
) -> Any:
    """生产组合根（V2-19 票面任务 4）——三引擎生产读面真装配＋DE-16 消费点。

    - knowledge＝PgKnowledgeStore（sem_* 直读——specs/knowledge.md「本期直读
      PG」的落位件）；
    - query＝QueryEngine（执行器＝PgQueryExecutor agg 星型真 SQL；水位读缝＝
      production_waterline（water_line 汇总层直读＋T-1 判定随面）经**翻板**——
      enabled＝ChatSettings.freshness_gate_enabled（config/database.yaml chat 段，
      DE-16），false＝不供给水位（N7.4a 关：不拦停不改绑）；行级权限/外表审批零触碰）；
    - retrieval＝RetrievalEngine（片段库＝PgFragmentLibrary kb_* 直读；
      embedder＝RemoteEmbedder——B6 embedding 唯一出口 infra.llm_client；
      图谱源未接线＝graph 面空集回退，Neo4j 适配器随落位批）；
    - faq＝PgFaqStore（V2-52 辅助模式——faq_lookup 发现工具读缝，faq_* 两表
      直读零缓存逐调用现行行）；
    - well_roster＝production_well_roster（井名录取值缝——table_schema 的
      dim_well 卡【井号名录】段与 `well` 查值消费；**传 loader 不传值**：discover
      每次调用现读 agg.dim_well，非装配期快照）。

    局部 import＝组合根例外（modules.md api 卡注记的延伸——本函数是 api 层
    唯一触引擎/tools 的位置；测试 fixture 组合不走此处，经 registry 注入）。
    """
    from appv2.infra.config import load_chat_settings, load_database_specs
    from appv2.infra.llm_client import LlmClient
    from appv2.knowledge import PgFaqStore, PgKnowledgeStore
    from appv2.query import (
        PgQueryExecutor,
        QueryEngine,
        production_waterline,
        production_well_roster,
    )
    from appv2.retrieval import (
        EnrichedFragmentLibrary,
        PgEnrichStore,
        PgFragmentLibrary,
        RemoteEmbedder,
        RetrievalEngine,
    )
    from appv2.tools import ToolRegistry

    resolved = tuple(specs) if specs is not None else tuple(load_database_specs())
    settings = chat_settings if chat_settings is not None else load_chat_settings()
    knowledge = PgKnowledgeStore(resolved, today=None if today is None else today())
    loader = production_waterline(resolved, today=today)
    query = QueryEngine(
        knowledge=knowledge,
        executor=PgQueryExecutor(resolved),
        # DE-16 消费点（V2-19 票面任务 4）：翻板从 config 进组合根——
        # enabled=True 原样透传水位供给（现状拦停/改绑）；False＝不供给水位。
        # 翻板语义单点（`loader if enabled else None`——N7.4a 关）随旧编排件退场，
        # 本层按同一判据内联装配（不跨块复制取名）。
        waterline=loader if settings.freshness_gate_enabled else None,
        today=today,
    )
    retrieval = RetrievalEngine(
        # 富化装配读面（V2-47 R1b）：PgFragmentLibrary 外套 EnrichedFragmentLibrary
        # ——富化向量 overlay 覆写＋节级摘要节点追加入语料；空富化表＝原样透传
        # （未富化态零漂移）。
        library=EnrichedFragmentLibrary(
            PgFragmentLibrary(resolved), PgEnrichStore(resolved)
        ),
        embedder=embedder if embedder is not None else RemoteEmbedder(LlmClient()),
    )
    return ToolRegistry(
        knowledge=knowledge,
        query=query,
        retrieval=retrieval,
        faq=PgFaqStore(resolved),
        well_roster=production_well_roster(resolved),
    )


def compose_production_ledger_dump(
    *,
    specs: Sequence[DatabaseSpec] | None = None,
    today: Callable[[], date] | None = None,
) -> Callable[[], Mapping[str, Any]]:
    """词典层全量投影源（V2-34 任务 6——拍板 a「第 1 轮全量注入」的生产装配）。

    PgKnowledgeStore 公开读面（evidence 浏览态＋aliases＋families——INV-2 只读）
    → tools.dump_from_store 全量 dump；运行期每次澄清取一次现行态（零缓存，
    与台账直读同纪律）。局部 import＝组合根例外（同 compose_production_registry
    注记——api 装配面消费 tools 公开接口）。**消费面**＝`context` 台账投影端口
    （create_app 经 `LedgerProjectionAdapter` 接线——每次装载逐调用现行态）。

    **水位随 dump 携入**：dump 的 `watermark` 键＝数据面真源（water_line 汇总层
    水位——`query.production_waterline` 同源读缝，与编排注入的 `watermark` 同
    一天；台账读面自不携水位，不自造）。缺行（水位未回写）＝空串如实缺位。
    """
    from appv2.infra.config import load_database_specs
    from appv2.knowledge import PgKnowledgeStore
    from appv2.query import production_waterline
    from appv2.tools import dump_from_store

    resolved = tuple(specs) if specs is not None else tuple(load_database_specs())
    store = PgKnowledgeStore(resolved, today=None if today is None else today())
    waterline = production_waterline(resolved, today=today)

    def loader() -> Mapping[str, Any]:
        face = waterline()
        return dump_from_store(
            store,
            watermark="" if face is None else face.data_date.isoformat(),
        )

    return loader


def compose_production_watermark(
    *,
    specs: Sequence[DatabaseSpec] | None = None,
    today: Callable[[], date] | None = None,
) -> Any:
    """水位 loader（water_line 汇总层直读＋T-1 判定，与 QueryEngine 水位读缝同源单点）。

    局部 import＝组合根例外（同上注记）。**返回 loader**（`Callable[[], WatermarkFace | None]`
    ——missing 行＝None，不伪造）；编排块注入形是**水位日**（date），故 create_app 在生产路径
    取一次并取 `data_date` 字段（装配形状适配，见模块 docstring）。
    """
    from appv2.infra.config import load_database_specs
    from appv2.query import production_waterline

    resolved = tuple(specs) if specs is not None else tuple(load_database_specs())
    return production_waterline(resolved, today=today)


def compose_production_data_wells(
    *, specs: Sequence[DatabaseSpec] | None = None
) -> Any:
    """数据链井闭世界 loader（agg.dim_well 井号集直读，与问数执行缝的 dim_well 同源单点）。

    局部 import＝组合根例外（同上注记）。**返回 loader**（`Callable[[], frozenset[str]]`）；
    编排块注入形是**集合**（`Collection[str]`——`specs/preconditions.md` 位 6 注入参），故
    create_app 在生产路径取一次（装配形状适配，见模块 docstring）。
    """
    from appv2.infra.config import load_database_specs
    from appv2.query import production_data_wells

    resolved = tuple(specs) if specs is not None else tuple(load_database_specs())
    return production_data_wells(resolved)


def compose_production_field_instances(
    *, specs: Sequence[DatabaseSpec] | None = None
) -> Any:
    """油田实例 loader（agg.dim_well.field_name 现值集直读——V2-82b 对象歧义门的数据源）。

    局部 import＝组合根例外（同上注记）。**返回 loader**（`Callable[[], tuple[str, ...]]`）
    ——编排块注入形即 loader 本身（`LoopDeps.field_instances`，与 `data_wells` 的「注入值」
    不同：本门**现读**每一次判定，不取启动快照——油田实例随数据面刷新即新，且门判定通过
    之前不触读面；同井名录段的现读纪律）。
    """
    from appv2.infra.config import load_database_specs
    from appv2.query import production_field_instances

    resolved = tuple(specs) if specs is not None else tuple(load_database_specs())
    return production_field_instances(resolved)


def compose_production_guide_text(
    *,
    budget: Budget | None = None,
    today: Callable[[], date] | None = None,
) -> str:
    """§A 指南段全文（生产装配——**启动取一次快照**，流水 63）。

    §A 装载件（`OntologyGuideProvider`——同层 api 读本体资产，组合根例外）产出的文本，
    经 `RunExecutor` → 编排 `LoopDeps` → 相位 `clarify`／`match` 注入。**取一次快照**纪律
    同 `watermark`／`data_wells`（见模块 docstring 装配形状适配）；`{max_rounds}`／
    `{max_discovers}`／`{max_executes}` 三占位符取 `Budget` 三键
    （`rounds`／`discovers_per_round`／`executes_per_round`——真值来源＝装配注入的 budget，
    缺省＝`Budget()` 默认，非 provider 自带缺省）。
    """
    effective = budget if budget is not None else Budget()
    provider = OntologyGuideProvider(
        today=today() if today is not None else None,
        max_rounds=effective.rounds,
        max_discovers=effective.discovers_per_round,
        max_executes=effective.executes_per_round,
    )
    return provider.guide()


def _watermark_date(loader: Callable[[], Any]) -> date | None:
    """水位 loader → 编排注入值（水位日 date；缺行＝None——不伪造、不编造）。

    形态真源＝`specs/preconditions.md` 位 7（`watermark: date | str | None`）＋裁决 L0-3
    （编排全链统一 date 形）；字段名真源＝`appv2.query.pg_waterline.WatermarkFace.data_date`。
    """
    face = loader()
    return None if face is None else cast(date, face.data_date)


def create_app(
    *,
    db: ConnectionManager,
    completer: Any,
    registry: Any | None = None,
    budget: Budget | None = None,
    specs: Sequence[DatabaseSpec] | None = None,
    chat_settings: ChatSettings | None = None,
    today: Callable[[], date] | None = None,
    embedder: Any | None = None,
    ledger_dump: Callable[[], Mapping[str, Any]] | None = None,
    watermark: Any | None = None,
    data_wells: Any | None = None,
    guide_text: str | None = None,
    field_instances: Any | None = None,
    execution_date: str | None = None,
) -> FastAPI:
    """构建 appv2 应用（四端点挂线＋runtimev2 生产装配——依赖注入面）。

    `completer`＝模型出口**同面缝**（签名与回执形状真源＝
    `appv2.runtimev2.gateway_adapter`：生产＝`GatewayBridge(egress=GatewayService(db,
    LlmClient()))`，测试＝`ScriptedCompleter`）——经 `set_completer` 注入（显式注入缝，
    生产路径不读环境变量）。
    `registry`＝ToolRegistry 实例（组合根注入——类型真源在 appv2.tools，本层按
    modules.md api 卡边界不 import，经编排块 RunExecutor 的签名面消费）；**None（缺省）＝
    生产组合**——compose_production_registry 真装配三引擎＋faq_lookup 读缝（V2-19 票面
    任务 4；specs/chat_settings/today/embedder 只在该路径生效）。
    `ledger_dump`＝台账投影源（`Callable[[], Mapping]`；None＋生产＝
    compose_production_ledger_dump）——经 `context.wire_ledger_projection` 接端口；
    `watermark`／`data_wells`＝编排注入值（date／集合；None＋生产＝生产 loader 取一次，
    见模块 docstring 的装配形状两处适配）。
    `field_instances`＝油田实例 loader（V2-82b——对象歧义门数据源；None＋生产＝
    `query.production_field_instances` 的 loader，**现读不取快照**；非生产路径 None＝
    门不出声）。
    `guide_text`＝§A 指南段注入值（str——经 `RunExecutor` 下传 `clarify`／`match`；
    None＋生产＝`compose_production_guide_text` 启动取一次快照；非生产路径 None＝空串）。
    `execution_date`（V2-123——材料头「执行日」段与期错位比对的时间量）＝ISO 日期串注入值
    （经 `RunExecutor` → 编排 `LoopDeps` → `answering` → `context.render_materials` 下传；
    **单一真源**：None＋生产＝本层把 `today` **只解析一次**（`today()`；`today=None` 时取
    `infra.clock`——B14 唯一时间出口），同一值既喂 §A `{today}` 又作 `execution_date` 下传；
    非生产路径 None＝空串＝材料头无执行日段，零漂移）。
    """
    production = registry is None
    if production:
        registry = compose_production_registry(
            specs=specs,
            chat_settings=chat_settings,
            today=today,
            embedder=embedder,
        )
        if ledger_dump is None:
            ledger_dump = compose_production_ledger_dump(specs=specs, today=today)
        if watermark is None:
            watermark = _watermark_date(
                compose_production_watermark(specs=specs, today=today)
            )
        if data_wells is None:
            data_wells = compose_production_data_wells(specs=specs)()
        # V2-123 执行日单一真源：`today` **只解析一次**（缺省 infra.clock，B14）——同一值既填
        # §A `{today}`（指南窗词锚定）又作 `execution_date` 下传（材料头「执行日」段＋期错位比对），
        # 防 §A 与材料头两版并存（EB11 §五-5：执行日 10-08／10-18 两版）。
        resolved_today: date = today() if today is not None else infra_clock.now().date()
        if guide_text is None:
            guide_text = compose_production_guide_text(
                budget=budget, today=lambda: resolved_today
            )
        if execution_date is None:
            execution_date = resolved_today.isoformat()
        if field_instances is None:
            field_instances = compose_production_field_instances(specs=specs)
    set_completer(completer)
    configure_audit_sink(SecurityAuditSink(SecurityService(db)))
    wire_ledger_projection(
        None if ledger_dump is None else LedgerProjectionAdapter(ledger_dump)
    )
    store = RunStore()
    executor = RunExecutor(
        registry=registry,  # type: ignore[arg-type]  # 组合根例外（生产缺省路径上非 None）
        store=store,
        budget=budget,
        watermark=watermark,
        data_wells=data_wells,
        guide_text=guide_text or "",
        execution_date=execution_date or "",
        field_instances=field_instances,
    )
    app = FastAPI(title="Petro-Agent V2", version="2.0", lifespan=lifespan)
    install_error_handlers(app)
    app.include_router(chat_router)
    app.state.db = db
    app.state.agent_runtime = AgentRuntime(executor)
    app.state.stream_registry = RunStreamRegistry()
    app.state.run_store = store
    app.state.production_composition = production
    return app


async def ensure_app_tables(db: ConnectionManager) -> None:
    """幂等建表（lifespan 消费——簿记端口建表清单＋审计责任账表＋gateway 三表＋富化索引表）。"""
    from appv2.infra.security.store import ensure_audit_table
    from appv2.retrieval.pg_enrich import ensure_enrich_tables

    RunStore().ensure_tables()  # 簿记表清单（真件由装配点注入；缺省内存件）
    # 审计责任账表（B12 唯一写口落库面——`SecurityService.audit` 直写 `audit_log`；
    # 空库首次写审计不 500 的 ensure 惯例＝V1 `app/main.py:150` 同款）。
    await ensure_audit_table(db.engine())
    await ensure_gateway_tables(db.engine())
    await ensure_enrich_tables(db.engine())  # V2-47 R1b——检索富化索引（additive）


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """建表 lifespan（真实入口挂本 lifespan——sqlite 接口测试底座同形幂等）。"""
    await ensure_app_tables(cast(ConnectionManager, app.state.db))
    yield
