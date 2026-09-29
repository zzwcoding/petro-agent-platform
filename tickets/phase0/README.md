# 阶段 0 开发票（地基 · 上线页面 D1）

> 拆票依据：roadmap.md 阶段 0 节 + 98 册 + 99 册 + ADR-0003/0006/0007 + frontend-foundation.md。
> 验收基线：21 册合同（teach-petro-agent/specs/api/）；每票一提交。

## P0-01 CI 四门禁 + 仓骨架 ✅（随建仓批落地）

- 四层骨架（app/api · app/domains 14 模块包 · app/infra）+ uv + pyproject（ruff/mypy strict/pytest/import-linter B16+B1）+ GitHub workflow。
- 验收：本地四闸全绿（ruff/mypy/pytest/lint-imports）。

## P0-02 中间件 compose（本票已随建仓批落地，验收=拉起验证）

- PG(+pgvector)/Redis/MinIO/Neo4j 四件 + Langfuse（profile observe，阶段 0 不依赖）。
- 验收：`docker compose up -d` 四件 healthy；`docker compose --profile observe up -d` Langfuse 可登录。

## P0-03 infra 底座：db 连接层 + config + clock ✅（2026-09-29）

- `infra/db.py`：SQLAlchemy 2.0 异步引擎、嵌套 SAVEPOINT、readonly 双保险（99 册）、`EncryptedField`（SM4 TypeDecorator 骨架）。
- `infra/config.py`（config.yaml 装载热加载）、`infra/clock.py`（冻结时钟 seam，B14）。
- 附带 `infra/crypto.py`（SM4/SM3，gmssl——ADR-0003 裁决 6，`EncryptedField` 的 crypto 回调供给方）。
- 验收 ✅：PG 集成 36 passed 零跳过（临时 PG16@5433 实跑）+ 无 TEST_DATABASE_URL 时 33 passed 4 skipped；四门禁绿；断言钉的是 transaction_read_only（真闸）而非 GUC（已退役）。

> **与 99 册的差异点登记（现实约束按现实落地，语义不私改）**：
> 1. **异步化**：99 §4.2 雏形为同步 `create_engine`/`Session`；本仓依赖定型 sqlalchemy[asyncio]+asyncpg（ADR-0003 裁决 3），落 `create_async_engine`/`AsyncSession`/`async_sessionmaker`——`session()/transaction()/readonly()` 三公开面、嵌套 SAVEPOINT、意图级 flush 守卫＋postgresql_readonly（每事务 BEGIN READ ONLY）双保险、慢查询钩子、`with_row_filter` 行级注入点、健康探活、`Repository`/`ReadOnlyRepository` 基类语义逐条保持（方法带 await）。
> 2. **驱动注册表**：`postgresql → postgresql+asyncpg`（99 雏形写 psycopg；仅键值改动，结构不动）；另登记 `sqlite+aiosqlite` 作单测底座驱动（99 §4.1 测试替身策略的落点，非生产角色）。
> 3. **DB 级只读兜底＝方言连接特性 postgresql_readonly**（只读会话工厂 execution_options，每事务 BEGIN READ ONLY）。连接级 `SET default_transaction_read_only` 方案**退役**——集成实测：①asyncpg 方言每事务显式 BEGIN READ WRITE 覆盖 GUC，单靠它拦不住 Core 直写；②裸 SET 与该特性并存反而使后者失效（probe 实证 2026-09-29）。PG/金仓生效，SQLite 底座靠意图级 flush 守卫。
> 4. **端口避让**：compose 宿主端口 5432→5433（demo-backend 的 petro-demo-pg 占 5432）；config/database.yaml 与 .env.example 默认同步。
> 5. **SM4 实现落位 `infra/crypto.py`**：`EncryptedField` 保持 99 的回调注入 seam（db.py 不 import 国密）；gmssl SM4-CBC＋随机 IV 前置 base64（同明文不同密文），SM3 摘要供 P0-04 审计 digest。
> 6. **事件挂载点**：引擎事件挂 `engine.sync_engine`、flush 守卫挂 `session.sync_session`（SQLAlchemy 2.1 异步事件未实现的官方路径），语义同 99。
> 7. **config 载体**：模型注册表 `config/models.yaml`（D1 真源）＋新增 `config/database.yaml`（`DatabaseSpec` 供给——99 §4.2「config.yaml 装载，infra.config 供给」）；凭证经 `${VAR:-默认}` 占位符由环境变量/.env 注入（.env 不进 git）。

## P0-04 security 模块：身份桩 + 审计写口 ✅（2026-09-29）

- `X-Dev-User` 请求头解析 → `resolve_actor()`（OAuth2.0 替换缝）；横切审计唯一写口 `security.audit`（B12，append-only 表按 99 册）。
- 验收 ✅：D3 合同身份/审计相关端点骨架过（端点 14 `audit-logs`：身份桩依赖＋默认角色过组闸＋401/403 错误包＋分页读面真库往返）；B1/B2 不红（lint-imports 3 契约 KEPT）。
- 落地：`app/domains/security/`（domain 厚：五角色注册表照抄 roles.js/resolve_actor/authorize 组闸/四槽 AuditRow＋SM3 digest；store：`audit_log` 99 §2.1 逐字段＋append-only 仓储＋`ensure_audit_table` 建表函数；service 薄：`SecurityService.audit/audit_logs`）＋ `app/api/`（deps：`current_actor` 依赖＋`get_db/get_security` 定位；errors：00 §3 统一错误包装配；security.py：端点 14 骨架）＋ `app/main.py` lifespan 装配（ConnectionManager＋security 服务）。
- 测试：身份桩三态（有头/无头→默认角色/非法值→401）＋组闸 403＋digest 确定性；audit 往返 sqlite 单测＋PG 集成（bigserial/jsonb/timestamp 真库断言＋SM3 复算）；B12 唯一写口结构断言（service 公开面仅 audit/audit_logs，store 无 update/delete 出口、不继承 Repository）。四门禁绿；无 TEST_DATABASE_URL 66 passed 8 skipped，带 PG16@5433 74 passed 零跳过。

> **与合同的差异点登记（现实约束按现实落地，语义不私改）**：
> 1. **infra.db 增设共享 ORM 基座 `Base`**（DeclarativeBase）：99 §4.2 雏形未含 Base、P0-03 未落；各域模型共用一个 MetaData 是 P0-08 Alembic 迁移分组单一 autogenerate 源与跨域 FK 共图的前提——模型文件仍归各域包（99 §4.3 归属不变），B16/B1 不红。
> 2. **建表走 `ensure_audit_table`**（store.py，checkfirst）：P0-08 前无 Alembic（票面约定）；表结构与 99 §2.1 逐字段一致（id bigserial/time/who/action/content/digest/meta jsonb＋基线列 created_at/updated_at＋idx(time desc)），PG 集成按 information_schema 逐列断言。
> 3. **digest 哈希输入口径（合同悬置处的本仓拍板）**：99/D3 只定「SM3 摘要指纹、应用层写入、永不落正文」，未定输入串——落 `SM3("ISO时间|who|action|content")`（canonical，`domain.audit_digest` 单点持有；变更口径即换指纹空间）。
> 4. **`audit(row)` 增可选 `session` 参数**：98 卡签名为 `audit(row: AuditRow) -> None`——真实落位加 `session=None`（传入＝调用方事务内同事务追加，B12「随各聚合事务落库」形状；缺省自管会话独立提交）。返回值仍 None，照卡。
> 5. **authorize 本票只落 PageGroup 组闸分支**：六组级 roles 照抄 roles.js MENU（00 §9.2「运行时以 roles.js 为准」）；Capability（五层能力闸）分支随 D3 权限矩阵批扩展。页级细分（A3/C2/C3/F1 等）随各页票。
> 6. **业务错误码新立三值**（00 §3.3 只定 `<域>_<语义>` 蛇形规则、未冻结字符串）：`security_unauthenticated`（401 身份解析失败）/`security_forbidden`（403 直调越权）/`request_invalid`（400 入参形状非法——FastAPI 缺省 422 与 00 §3.2「请求还没进门＝400」冲突，统一收口映射 400）。系统级 400 码归口待设计仓下一版冻结，暂用 `request_invalid` 挂账。
> 7. **D3 audit-logs 直接落 snake_case**：R1 裁决「接线批 mock→真实切换时一次性改字段名（值、语义、路径均不变）」——本端点即真实接线，按 R1 指定时序落 `page_size`（query 参数 `page/pageSize` 保留现拼写）；D3 册正文的 camelCase→snake 迁移行仍欠登记（设计仓下一版义务，本仓不代改）。
> 8. **审计 time 出 ISO 8601 机器时间戳**（00 §1.4 判据：参与排序、idx(time desc)）；D3 册未冻结该项示例值。
> 9. **sys_user 未落**：本票身份解析走静态角色注册表（roles.js 冻结值；默认角色＝aqiang，docs/prd.md 拍板回执），`sys_user` 种子装载随 D3 整页票/OAuth 账号映射批落库——五角色键/label 与 roles.js 逐字一致，语义无出入。
> 10. **AuditFilter 预留 who/action 两槽**：D3 册端点 14 未冻结筛选参数，读面留 `who/action` 可选槽（空＝全量倒序）。
> 11. **`audit_logs` 与 98 卡签名偏差**：卡面 `audit_logs(filter: AuditFilter, page: int, page_size: int) -> AuditLogPage`——实现为 `audit_logs(filter: AuditFilter | None = None, *, page=1, page_size=20) -> Page[AuditLogView]`：filter 可选（None＝全量倒序，衔接差异 10），返回类型复用 infra R3 分页信封 `Page[T]` 而非另立 `AuditLogPage` 包装名（信封形状归接口层公共件，items 投影 `AuditLogView`）。

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
