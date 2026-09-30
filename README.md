# Petro-Agent 平台（真实实现仓）

> 单仓聚合三分区：**后端 `app/`（Python 3.12 + uv · FastAPI）· 前端 `web/`（React18+antd5，由 teach-petro-agent/prototype fork 改造）· 嵌套独立仓 `ontology/`（本体资产）· `data-plane/`（数据面服务）**。
> 两子仓＝文件夹内的独立 git（2026-09-30 改判，ADR-0008 子模块注册退除）：git 各归各文件夹，平台仓 .gitignore 排除、不记录其版本；**整个 petro-agent-platform 文件夹拷走＝全量备份**（三份 .git 都在内）。

## 克隆/备份

```bash
git clone <本仓地址>          # 平台仓本体（app/web/tickets…）；ontology/ 与 data-plane/ 需从各自仓另行获取（独立 git，不随平台仓克隆）
备份：整个文件夹直接拷贝即可（三份 .git 全在内）
```

## 设计真源（不复制进本仓）

| 设计件 | 位置 |
|---|---|
| 21 册 API 合同 + 98 模块划分 + 99 数据库设计 | `teach-petro-agent/specs/api/` |
| 架构图 v1（已过审 ADR-0006） | `teach-petro-agent/docs/architecture-v1.md` |
| 前端底座设计 | `teach-petro-agent/specs/frontend-foundation.md` |
| 阶段规划 | `teach-petro-agent/docs/roadmap.md` |
| ADR 链 0003–0008 | `teach-petro-agent/docs/adr/` |

## 快速开始

```bash
git clone --recurse-submodules <本仓地址>     # 或事后：git submodule update --init
cp .env.example .env                          # 填入 LLM 凭证（Owner 提供测试 key）
uv sync                                  # 后端依赖（Python 3.12 由 uv 管理）
docker compose up -d                     # 中间件：PG(+pgvector)/Redis/MinIO/Neo4j（Langfuse 见 observe profile）
uv run uvicorn app.main:app --reload     # 开发服 :8000
```

## 模型注册表（调用别名制）

`config/models.yaml` 进 git（只记别名不记密钥，密钥经 `.env` 注入）。当前：主模型 **MiniMax-M3**（petro-main）、备用/降级 **glm-5.3-flash**（petro-lite），双端点均为 Anthropic 兼容协议（2026-09-29 curl 实测通过，调用形状见文件头注释）。价格已裁决：两模型统一 百万输入 1 元/百万输出 3 元（prices.default）。

## 结构纪律（98 册四层 + B1–B16 边界规则）

```
app/api/       接口层：20 个路由族薄壳，只调 domains 公开接口（B2），唯一框架接触面
app/domains/   14 模块（3 组）：service.py 薄 + domain.py 厚；模块间只走公开接口+领域事件（B11）
app/infra/     11 adapter：db/graph_store/object_storage/queue/sse_channel/eventbus/clock/
               scheduler/crypto/config/llm_client——唯一经允许的底层接触面（B3/B6）
ontology/      子仓：本体资产（Git+YAML 真源，all-agent 纪律见其 AGENTS.md；语义闸 ci.sh）
data-plane/    子仓：数据面服务（进料→清洗→出汇总→质检→报水位，纪律见其 AGENTS.md）
```

## 子仓纪律（submodule 三铁律）

1. 子仓内容**回各自仓提交推送**（cd ontology && git commit…），父仓只更新指针提交；
2. 子仓在父仓默认 detached HEAD，开发前先 `git -C <子仓> checkout <分支>`；
3. 改子仓内容必伴随父仓指针提交，否则克隆者拿到旧版本。

层间依赖单向向下（B16），边界规则逐条进 `import-linter`（见 pyproject），CI 四门禁：lint/类型/测试/边界闸。

## 开发期身份

`X-Dev-User` 请求头＝身份桩（OAuth2.0 预留切换，时点未拍板——ADR-0003）。生产前所有端点默认信任此头。

## 双库纪律

开发 PostgreSQL / 生产金仓——SQL 一律经 `infra.db` 连接层（B3），方言切换唯一缝；禁止裸驱动（psycopg/asyncpg）散落业务代码。
