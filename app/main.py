"""Petro-Agent 主平台应用入口。

装配（P0-04 起）：lifespan 建立 ConnectionManager（config/database.yaml，
99 §4.2「config 装载、infra.config 供给」）与 security 服务面，并对 primary
引擎建审计表（ensure_audit_table，幂等 checkfirst——P0-08 前无 Alembic，
真实入口对空库可写审计/读 audit-logs）；P0-05 起 gateway 服务面入装配
（infra.llm_client 为 B6 唯一 SDK 接触点，gateway 是其唯一消费方）并对
primary 引擎建网关三表（spend 账本/演练/预算单例）；统一错误包（00 §3）
与 D3/D1 路由挂载。端点随票落地（tickets/phase0/）。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import install_error_handlers
from app.api.gateway import router as gateway_router
from app.api.security import router as security_router
from app.domains.gateway import GatewayService
from app.domains.gateway.store import ensure_gateway_tables
from app.domains.security import SecurityService
from app.domains.security.store import ensure_audit_table
from app.infra.config import load_database_specs
from app.infra.db import ConnectionManager
from app.infra.llm_client import LlmClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    manager = ConnectionManager(load_database_specs())
    await ensure_audit_table(manager.engine())  # 幂等（checkfirst）——空库首次写审计不 500
    await ensure_gateway_tables(manager.engine())  # 同上——网关三表（99 §2.13）
    app.state.db = manager
    app.state.security = SecurityService(manager)
    app.state.gateway = GatewayService(manager, LlmClient())
    yield
    await manager.dispose()


app = FastAPI(title="petro-agent-platform", version="0.1.0", lifespan=lifespan)
install_error_handlers(app)
app.include_router(security_router)
app.include_router(gateway_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
