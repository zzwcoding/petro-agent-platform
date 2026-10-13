# Petro-Agent 平台（真实实现仓）

> 单仓聚合：**后端 `app/`（Python 3.12 + uv · FastAPI）· 前端 `web/`（React18+antd5）· 本体 `ontology/`（平台仓普通目录，全部历史已并入）· 数据面 `data-plane/`（嵌套独立 git）**。
> 本体资产随本仓一起提交管理（改动前跑 `bash ontology/ci.sh` 语义闸——all-agent 纪律）；数据面为独立服务保留独立 git（.gitignore 排除）；**整个文件夹拷走＝全量备份**。


## 克隆/备份

```bash
git clone https://github.com/zzwcoding/petro-agent-platform.git   # 平台仓全量（app/web/tickets/ontology…）
git clone https://github.com/zzwcoding/tpa-data-plane.git         # 数据面仓（本地嵌套于 data-plane/，平台仓 .gitignore 排除——两仓齐即全量）
备份：整个文件夹直接拷贝也可（两份 .git 全在内：平台仓 + data-plane）；云端＝GitHub 两仓（本体已并入平台仓）
```

## 项目地图（同一项目的各部分 GitHub 仓）

本项目按「设计真源 → 平台实现 → 数据面 → 合成数据」分仓协作，各仓独立 git，GitHub 平级发布：

| 仓库 | 角色 | 可见性 |
|---|---|---|
| **本仓** [petro-agent-platform](https://github.com/zzwcoding/petro-agent-platform) | 平台实现仓：后端 `app/`＋`appv2/` · 前端 `web/` · 本体 `ontology/`（已并入） | 公开 |
| [teach-petro-agent](https://github.com/zzwcoding/teach-petro-agent) | 设计/教学真源仓：合同册 · ADR · 业务设定 · 场景课 | 公开 |
| [teach-petro-agent-public](https://github.com/zzwcoding/teach-petro-agent-public) | 教学仓公开向副本（架构设计项目形态） | 公开 |
| [tpa-data-plane](https://github.com/zzwcoding/tpa-data-plane) | 数据面仓：独立数据服务（进料→清洗→出汇总→质检→报水位） | 公开 |
| [fieldforge](https://github.com/zzwcoding/fieldforge) | 油气领域合成数据生成工作台 | 公开 |

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
git clone https://github.com/zzwcoding/petro-agent-platform.git   # data-plane 为独立仓（github.com/zzwcoding/tpa-data-plane），需要时另行 clone
cp .env.example .env                          # 填入 LLM 凭证（Owner 提供测试 key）
uv sync                                  # 后端依赖（Python 3.12 由 uv 管理）
docker compose up -d                     # 中间件：PG(+pgvector)/Redis/MinIO/Neo4j（Langfuse 见 observe profile）
uv run uvicorn app.main:app --reload     # 开发服 :8000
```

## 模型注册表（调用别名制）

`config/models.yaml` 进 git（只记别名不记密钥，密钥经 `.env` 注入）。当前：主模型 **MiniMax-M3**（petro-main）、备用/降级 **glm-5.3-flash**（petro-lite），双端点均为 Anthropic 兼容协议（2026-09-29 curl 实测通过，调用形状见文件头注释）。价格已裁决：两模型统一 百万输入 1 元/百万输出 3 元（prices.default）。向量化 **embo-01**（petro-embed，2026-10-02 选型接线）——`/v1/embeddings`· 1536 维已归一化，kb/faq 专用、只经 `infra.llm_client.embeddings`（非 gateway.complete 面）；价格档 0.0005 元/千 token（历史定价页，以账单为准）。

## 结构纪律（98 册四层 + B1–B16 边界规则）

```
app/api/       接口层：9 个路由族薄壳（全量按阶段点亮），只调 domains 公开接口（B2），唯一框架接触面
app/domains/   14 模块（3 组）：service.py 薄 + domain.py 厚；模块间只走公开接口+领域事件（B11）
app/infra/     8 在 3 预留 adapter：db/graph_store/object_storage/eventbus/clock/crypto/
               config/llm_client 在，queue/sse_channel/scheduler 预留——唯一经允许的底层接触面（B3/B6）
ontology/      平台仓目录：本体资产（Git+YAML 真源，all-agent 纪律；改动前跑 bash ontology/ci.sh）
data-plane/    独立仓：数据面服务（进料→清洗→出汇总→质检→报水位，纪律见其 AGENTS.md）
```

## 嵌套仓纪律（data-plane）

1. data-plane 内容**回 data-plane 仓提交推送**（cd data-plane && git commit…，远程 https://github.com/zzwcoding/tpa-data-plane），平台仓 .gitignore 排除之，不记版本；
2. 改动守 data-plane 仓自己的 AGENTS.md（ADR 链）；
3. ontology/ 已并入平台仓普通目录（2026-09-30 子树合并，历史随合并提交可溯）——本体改动直接提交本仓，提交前跑 `bash ontology/ci.sh` 语义闸。

层间依赖单向向下（B16），边界规则逐条进 `import-linter`（见 pyproject），CI 五闸：lint/类型/测试/边界闸/合同覆盖率闸（`tools/contract_coverage.py`——合同册端点 × 实现路由双向对账，AGENTS.md 硬纪律 8）。

## 开发期身份

`X-Dev-User` 请求头＝身份桩（OAuth2.0 预留切换，时点未拍板——ADR-0003）。生产前所有端点默认信任此头。

## 双库纪律

开发 PostgreSQL / 生产金仓——SQL 一律经 `infra.db` 连接层（B3），方言切换唯一缝；禁止裸驱动（psycopg/asyncpg）散落业务代码。
