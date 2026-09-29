"""Petro-Agent 主平台应用入口（阶段 0 骨架：健康探活，端点随票落地）。"""

from fastapi import FastAPI

app = FastAPI(title="petro-agent-platform", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
