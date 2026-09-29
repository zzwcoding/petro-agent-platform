"""Petro-Agent 主平台应用入口。

装配（P0-04 起）：lifespan 建立 ConnectionManager（config/database.yaml，
99 §4.2「config 装载、infra.config 供给」）与 security 服务面；统一错误包
（00 §3）与 D3 审计骨架路由挂载。端点随票落地（tickets/phase0/）。
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import install_error_handlers
from app.api.security import router as security_router
from app.domains.security import SecurityService
from app.infra.config import load_database_specs
from app.infra.db import ConnectionManager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    manager = ConnectionManager(load_database_specs())
    app.state.db = manager
    app.state.security = SecurityService(manager)
    yield
    await manager.dispose()


app = FastAPI(title="petro-agent-platform", version="0.1.0", lifespan=lifespan)
install_error_handlers(app)
app.include_router(security_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
