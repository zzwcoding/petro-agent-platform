# Petro-Agent 平台（真实实现仓）

> 主平台单体实现仓：**后端 `app/`（Python 3.12 + uv · FastAPI）+ 前端 `web/`（React18+antd5，由 teach-petro-agent/prototype fork 改造）**。
> 三仓鼎立：本仓（主平台）· [petro-ontology](../petro-ontology)（本体资产）· [tpa-data-plane](../tpa-data-plane)（数据面）。

## 设计真源（不复制进本仓）

| 设计件 | 位置 |
|---|---|
| 21 册 API 合同 + 98 模块划分 + 99 数据库设计 | `teach-petro-agent/specs/api/` |
| 架构图 v1（已过审 ADR-0006） | `teach-petro-agent/docs/architecture-v1.md` |
| 前端底座设计 | `teach-petro-agent/specs/frontend-foundation.md` |
| 阶段规划 | `teach-petro-agent/docs/roadmap.md` |
| ADR 链 0003–0007 | `teach-petro-agent/docs/adr/` |

## 快速开始

```bash
uv sync                                  # 后端依赖（Python 3.12 由 uv 管理）
docker compose up -d                     # 中间件：PG(+pgvector)/Redis/MinIO/Neo4j（Langfuse 见 observe profile）
uv run uvicorn app.main:app --reload     # 开发服 :8000
```

## 结构纪律（98 册四层 + B1–B16 边界规则）

```
app/api/       接口层：20 个路由族薄壳，只调 domains 公开接口（B2），唯一框架接触面
app/domains/   14 模块（3 组）：service.py 薄 + domain.py 厚；模块间只走公开接口+领域事件（B11）
app/infra/     11 adapter：db/graph_store/object_storage/queue/sse_channel/eventbus/clock/
               scheduler/crypto/config/llm_client——唯一经允许的底层接触面（B3/B6）
```

层间依赖单向向下（B16），边界规则逐条进 `import-linter`（见 pyproject），CI 四门禁：lint/类型/测试/边界闸。

## 开发期身份

`X-Dev-User` 请求头＝身份桩（OAuth2.0 预留切换，时点未拍板——ADR-0003）。生产前所有端点默认信任此头。

## 双库纪律

开发 PostgreSQL / 生产金仓——SQL 一律经 `infra.db` 连接层（B3），方言切换唯一缝；禁止裸驱动（psycopg/asyncpg）散落业务代码。
