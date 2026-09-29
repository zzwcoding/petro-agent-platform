# 阶段 0 开发票（地基 · 上线页面 D1）

> 拆票依据：roadmap.md 阶段 0 节 + 98 册 + 99 册 + ADR-0003/0006/0007 + frontend-foundation.md。
> 验收基线：21 册合同（teach-petro-agent/specs/api/）；每票一提交。

## P0-01 CI 四门禁 + 仓骨架 ✅（随建仓批落地）

- 四层骨架（app/api · app/domains 14 模块包 · app/infra）+ uv + pyproject（ruff/mypy strict/pytest/import-linter B16+B1）+ GitHub workflow。
- 验收：本地四闸全绿（ruff/mypy/pytest/lint-imports）。

## P0-02 中间件 compose（本票已随建仓批落地，验收=拉起验证）

- PG(+pgvector)/Redis/MinIO/Neo4j 四件 + Langfuse（profile observe，阶段 0 不依赖）。
- 验收：`docker compose up -d` 四件 healthy；`docker compose --profile observe up -d` Langfuse 可登录。

## P0-03 infra 底座：db 连接层 + config + clock

- `infra/db.py`：SQLAlchemy 2.0 异步引擎、嵌套 SAVEPOINT、readonly 双保险（99 册）、`EncryptedField`（SM4 TypeDecorator 骨架）。
- `infra/config.py`（config.yaml 装载热加载）、`infra/clock.py`（冻结时钟 seam，B14）。
- 验收：双跑 PG 集成测试过；mypy strict 无红。

## P0-04 security 模块：身份桩 + 审计写口

- `X-Dev-User` 请求头解析 → `resolve_actor()`（OAuth2.0 替换缝）；横切审计唯一写口 `security.audit`（B12，append-only 表按 99 册）。
- 验收：D3 合同身份/审计相关端点骨架过；B1/B2 不红。

## P0-05 gateway 模块 + D1 页面后端（8 端点）

- LiteLLM SDK 内嵌：模型别名路由、fallback（allowed_fails/cooldown）、预算熔断降级组、**调用粒度记账（PG 账本唯一）**。
- D1 合同 8 端点：models/config 读写/spend-logs 分页/drills 三连（202+轮询+历史，409 重入）。
- 调用方式已验证（2026-09-29 curl 实测）：主 MiniMax-M3 / 备 glm-5.3-flash 均走 Anthropic 兼容端点（POST {base}/v1/messages + x-api-key + anthropic-version），凭证落 `.env`、别名注册表 `config/models.yaml`（B6 只认别名）。
- ~~挂账待 Owner：模型价格表~~ 已给（2026-09-29 裁决：两模型统一 百万输入 1 元/百万输出 3 元，prices.default 已落 config/models.yaml）。
- 验收：D1 合同行为规则逐条过 + 演练真切换一次模型留痕。

## P0-06 前端底座（web/ fork + 五件）

- prototype/app → web/ fork（snapshot）；去 singlefile；vite proxy→:8000；eslint 进 CI。
- 双树路由：落地 #/X · 原型 #/proto/*；菜单角标。
- api/client（错误包解包/信封/X-Dev-User 注入/useTaskPolling）+ sse 客户端 + zustand 三槽 + 组件库首批（四态徽标/产物卡骨架）。
- 验收：web/ dev 起服；原型树全页可点（对照基线截图无漂移）；client 单测过。

## P0-07 D1 页面落地（首个真 API 页面）

- D1.jsx 数据源从 mock 切 api/client；页头徽标/配置读写/spend 流水/演练工具栏全接线。
- 验收：D1 合同 8 端点真实往返；与 #/proto/D1 对比行为一致（除数据真假）。

## P0-08 预留件：chat SSE 骨架 + eventbus + 迁移分组

- /api/chat 路由族空壳 + SSE 信封（00 册 §6 三帧语义）；eventbus（Redis Streams+outbox 表）接口缝；Alembic 迁移分组（sem_/kb_ 等按 99 册前缀）。
- 验收：事件发布-订阅内存实现测试过；Alembic upgrade/downgrade 空迁移过。

## 阶段 0 收官验收

四门禁全绿 + D1 八端点真跑 + 前端双树对比可用 + B1–B16 边界闸在真实代码上绿。
