"""appv2.api.app —— appv2 自有 app 工厂（V2-07 票面红线：挂线路由注册进
appv2 工厂，V1 app/main.py 路由零改动）。

组合缝（modules.md 边界规则「api 只依赖 runtime 公开接口＋infra」的落法）：
本工厂只 import appv2.runtime＋appv2.infra——引擎侧组合根（knowledge/query/
retrieval → ToolRegistry）与 completer（生产＝GatewayService，测试＝剧本件）
由调用方注入；**registry 缺省（None）＝生产组合**（V2-19 票面任务 4——三引擎
生产读面真装配＋DE-16 消费点，compose_production_registry 局部 import 引擎与
tools 包装配，属 modules.md api 卡注记的组合根例外延伸——create_app 装配
真引擎替换 fixture 组合，对齐拍回写归属在案）。fixture 组合（测试）照旧经
registry 参数显式注入。真实入口（演示/生产 main）点亮时在此工厂之上传入
生产组合（V1 main.py 同位）。

装配面：GraphRunExecutor（六步图＋PG checkpointer）→ AgentRuntime；
RunStreamRegistry（SSE 事件桥缓冲）＋RunStore（run 簿记读面）入 app.state
（deps 定位消费）；lifespan 幂等建表（agent_v2 五表＋gateway 三表——
ensure 双轨约定，P0-08 先例）。
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from datetime import date
from typing import Any, cast

from fastapi import FastAPI

from appv2.api.bridge import RunStreamRegistry
from appv2.api.chat import router as chat_router
from appv2.api.errors import install_error_handlers
from appv2.api.ontology_guide import OntologyGuideProvider
from appv2.infra.config import ChatSettings
from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.infra.gateway.store import ensure_gateway_tables
from appv2.runtime import (
    CALLER_PREFIX,
    AgentRuntime,
    Budget,
    GatewayChatModel,
    PgCheckpointer,
    RunStore,
    ensure_agent_v2_tables,
    gate_freshness,
)
from appv2.runtime.executor import GraphRunExecutor
from appv2.runtime.llm import Completer

# ReAct 图模型键闭世界（appv2.runtime.graph 装配契约——executor.models 字典键
# ＝caller 去前缀短名；graph.py「模型 caller 桶闭世界」节同源。V2-31：三桶
# 无 repair）。
MODEL_KEYS: tuple[str, ...] = ("understand", "decision", "answer")


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
      production_waterline（water_line 汇总层直读＋T-1 判定随面）经
      **gate_freshness 翻板**——enabled＝ChatSettings.freshness_gate_enabled
      （config/database.yaml chat 段，DE-16），false＝不供给水位（N7.4a 关：
      不拦停不改绑）；行级权限/外表审批零触碰）；
    - retrieval＝RetrievalEngine（片段库＝PgFragmentLibrary kb_* 直读；
      embedder＝RemoteEmbedder——B6 embedding 唯一出口 infra.llm_client；
      图谱源未接线＝graph 面空集回退，Neo4j 适配器随落位批）。

    局部 import＝组合根例外（modules.md api 卡注记的延伸——本函数是 api 层
    唯一触引擎/tools 的位置；测试 fixture 组合不走此处，经 registry 注入）。
    """
    from appv2.infra.config import load_chat_settings, load_database_specs
    from appv2.infra.llm_client import LlmClient
    from appv2.knowledge import PgKnowledgeStore
    from appv2.query import PgQueryExecutor, QueryEngine, production_waterline
    from appv2.retrieval import PgFragmentLibrary, RemoteEmbedder, RetrievalEngine
    from appv2.tools import ToolRegistry

    resolved = tuple(specs) if specs is not None else tuple(load_database_specs())
    settings = chat_settings if chat_settings is not None else load_chat_settings()
    knowledge = PgKnowledgeStore(resolved, today=None if today is None else today())
    query = QueryEngine(
        knowledge=knowledge,
        executor=PgQueryExecutor(resolved),
        # DE-16 消费点（V2-19 票面任务 4）：翻板从 config 进组合根——
        # enabled=True 原样透传水位供给（现状拦停/改绑）；False＝不供给。
        waterline=gate_freshness(
            production_waterline(resolved, today=today),
            enabled=settings.freshness_gate_enabled,
        ),
        today=today,
    )
    retrieval = RetrievalEngine(
        library=PgFragmentLibrary(resolved),
        embedder=embedder if embedder is not None else RemoteEmbedder(LlmClient()),
    )
    return ToolRegistry(knowledge=knowledge, query=query, retrieval=retrieval)


def compose_production_ledger_dump(
    *,
    specs: Sequence[DatabaseSpec] | None = None,
    today: Callable[[], date] | None = None,
) -> Any:
    """词典层全量投影缝（V2-34 任务 6——拍板 a「第 1 轮全量注入」的生产装配）。

    PgKnowledgeStore 公开读面（evidence 浏览态＋aliases＋families——INV-2 只读）
    → tools.dump_from_store 全量 dump；运行期每次澄清取一次现行态（零缓存，
    与台账直读同纪律）。局部 import＝组合根例外（同 compose_production_registry
    注记——api 装配面消费 tools 公开接口）。
    """
    from appv2.infra.config import load_database_specs
    from appv2.knowledge import PgKnowledgeStore
    from appv2.tools import dump_from_store

    resolved = tuple(specs) if specs is not None else tuple(load_database_specs())
    store = PgKnowledgeStore(resolved, today=None if today is None else today())
    return lambda: dump_from_store(store)


def compose_production_watermark(
    *,
    specs: Sequence[DatabaseSpec] | None = None,
    today: Callable[[], date] | None = None,
) -> Any:
    """水位读缝（V2-34 前置条件机新鲜度窗照实判定的生产装配——water_line
    汇总层直读＋T-1 判定，与 QueryEngine 水位读缝同源单点）。局部 import＝
    组合根例外（同上注记）。"""
    from appv2.infra.config import load_database_specs
    from appv2.query import production_waterline

    resolved = tuple(specs) if specs is not None else tuple(load_database_specs())
    return production_waterline(resolved, today=today)


def create_app(
    *,
    db: ConnectionManager,
    completer: Completer,
    registry: Any | None = None,
    budget: Budget | None = None,
    specs: Sequence[DatabaseSpec] | None = None,
    chat_settings: ChatSettings | None = None,
    today: Callable[[], date] | None = None,
    embedder: Any | None = None,
    guide: Any | None = None,
    four_phase: bool = True,
    ledger_dump: Any | None = None,
    watermark: Any | None = None,
) -> FastAPI:
    """构建 appv2 应用（三端点挂线＋runtime 生产装配——依赖注入面）。

    registry＝ToolRegistry 实例（组合根注入——类型真源在 appv2.tools，本层
    按 modules.md api 卡边界「只依赖 runtime＋infra」不 import，经 runtime
    executor 的签名面消费）；**None（缺省）＝生产组合**——compose_production_
    registry 真装配三引擎（V2-19 票面任务 4；specs/chat_settings/today/
    embedder 只在该路径生效）。
    guide＝处理指南（V2-34 任务 10 真指南接线——None＝OntologyGuideProvider
    缺省构造：ontology 资产 §A 装载切面＋DECISION_CONTRACT 拼接；占位
    DefaultGuideProvider 已退役，不设双真源）。
    four_phase＝V2-34 四相位装配开关（ADR-0005；缺省 True——P-033b 缺省翻转：
    生产装配四相位真跑，既有 ReAct 七节点图经 four_phase=False 显式装配保留；
    RUNTIME_SMOKE ②步序钉随四相位更新）。生产路径（registry 缺省）同时接词典层
    全量投影缝与水位读缝（clarify 注入＋前置条件机新鲜度窗）。
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
            watermark = compose_production_watermark(specs=specs, today=today)
    if guide is None:
        guide = OntologyGuideProvider(
            today=None if today is None else today(),
            # 四相位装配：legacy 决策合同不进指南面（相位合同在 runtime 消费缝
            # 前置——防双合同并存真模型跟随 legacy 四动作，P033SK1 实证）。
            include_decision_contract=not four_phase,
        )
    models = {
        key: GatewayChatModel(
            completer=completer, caller=f"{CALLER_PREFIX}.{key}", alias=""
        )
        for key in MODEL_KEYS
    }
    executor = GraphRunExecutor(
        registry=registry,  # type: ignore[arg-type]  # 组合根例外（生产缺省路径上非 None）
        models=models,
        db=db,
        saver=PgCheckpointer(db),
        budget=budget,
        guide=guide,
        four_phase=four_phase,
        ledger_dump=ledger_dump,
        watermark=watermark,
    )
    app = FastAPI(title="Petro-Agent V2", version="2.0", lifespan=lifespan)
    install_error_handlers(app)
    app.include_router(chat_router)
    app.state.db = db
    app.state.agent_runtime = AgentRuntime(executor)
    app.state.stream_registry = RunStreamRegistry()
    app.state.run_store = RunStore(db)
    app.state.production_composition = production
    return app


async def ensure_app_tables(db: ConnectionManager) -> None:
    """幂等建表（lifespan 消费——agent_v2 五表＋gateway 三表）。"""
    await ensure_agent_v2_tables(db.engine())
    await ensure_gateway_tables(db.engine())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """建表 lifespan（真实入口挂本 lifespan——sqlite 接口测试底座同形幂等）。"""
    await ensure_app_tables(cast(ConnectionManager, app.state.db))
    yield
