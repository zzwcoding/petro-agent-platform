"""appv2.api.app —— appv2 自有 app 工厂（V2-07 票面红线：挂线路由注册进
appv2 工厂，V1 app/main.py 路由零改动）。

组合缝（modules.md 边界规则「api 只依赖 runtime 公开接口＋infra」的落法）：
本工厂只 import appv2.runtime＋appv2.infra——引擎侧组合根（knowledge/query/
retrieval → ToolRegistry）与 completer（生产＝GatewayService，测试＝剧本件）
由调用方注入，不在 api 层 import 引擎模块。真实入口（演示/生产 main）点亮
时在此工厂之上传入生产组合（V1 main.py 同位）；本票自带的生产装配样例见
tests/api/test_v2_runtime_smoke_real.py（R14 真网关冒烟）。

装配面：GraphRunExecutor（六步图＋PG checkpointer）→ AgentRuntime；
RunStreamRegistry（SSE 事件桥缓冲）＋RunStore（run 簿记读面）入 app.state
（deps 定位消费）；lifespan 幂等建表（agent_v2 五表＋gateway 三表——
ensure 双轨约定，P0-08 先例）。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI

from appv2.api.bridge import RunStreamRegistry
from appv2.api.chat import router as chat_router
from appv2.api.errors import install_error_handlers
from appv2.infra.db import ConnectionManager
from appv2.infra.gateway.store import ensure_gateway_tables
from appv2.runtime import (
    CALLER_PREFIX,
    AgentRuntime,
    Budget,
    GatewayChatModel,
    PgCheckpointer,
    RunStore,
    ensure_agent_v2_tables,
)
from appv2.runtime.executor import GraphRunExecutor
from appv2.runtime.llm import Completer

# 六步图模型键闭世界（appv2.runtime.graph 装配契约——executor.models 字典键
# ＝caller 去前缀短名；graph.py「模型 caller 名闭世界」节同源）。
MODEL_KEYS: tuple[str, ...] = ("understand", "plan", "plan_repair", "answer_draft")


def create_app(
    *,
    db: ConnectionManager,
    registry: Any,
    completer: Completer,
    budget: Budget | None = None,
) -> FastAPI:
    """构建 appv2 应用（三端点挂线＋runtime 生产装配——依赖注入面）。

    registry＝ToolRegistry 实例（组合根注入——类型真源在 appv2.tools，本层
    按 modules.md api 卡边界「只依赖 runtime＋infra」不 import，经 runtime
    executor 的签名面消费）。
    """
    models = {
        key: GatewayChatModel(
            completer=completer, caller=f"{CALLER_PREFIX}.{key}", alias=""
        )
        for key in MODEL_KEYS
    }
    executor = GraphRunExecutor(
        registry=registry,
        models=models,
        db=db,
        saver=PgCheckpointer(db),
        budget=budget,
    )
    app = FastAPI(title="Petro-Agent V2", version="2.0", lifespan=lifespan)
    install_error_handlers(app)
    app.include_router(chat_router)
    app.state.db = db
    app.state.agent_runtime = AgentRuntime(executor)
    app.state.stream_registry = RunStreamRegistry()
    app.state.run_store = RunStore(db)
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
