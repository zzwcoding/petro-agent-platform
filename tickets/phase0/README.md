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

## P0-05 gateway 模块 + D1 页面后端 ✅（2026-09-30）

- `app/infra/llm_client.py`：LiteLLM SDK 内嵌 adapter（B6 唯一 SDK 接触点；`litellm.acompletion` 同头注释已验证形状的异步形式；SDK 重试恒关 num_retries=0——W-F2-4 重试只走网关层）；上游异常单点归类椒图判据（网络错/超时/5xx＝UpstreamUnavailable 可切备，4xx/429＝UpstreamRejected 不切）。
- `app/domains/gateway/`（domain 厚）：complete（运行时唯一 LLM 出口——别名路由/fallback 状态机 allowed_fails+cooldown/同别名 num_retries 重试/预算双阈值熔断单向置位→降级组 standard→lite 改路由不拒绝/调用粒度记账 Owner 公式/演练状态机）＋ store（gateway_spend_record/gateway_drill_run/gateway_budget_config 三表按 99 §2.13 逐字段，ensure_gateway_tables 沿 P0-04 惯例）＋ service 薄。B6 升机检：import-linter 第 4 契约（litellm 在 app/ 内只许 infra.llm_client import；tests 直连打桩不在契约内）。
- `app/api/gateway.py`：D1 路由族 7 条（models/config 读写/spend-logs/drills 三连）全落，组闸复用 SettingsActor（设置中心＝平台运维，D1 权限行）；错误码四新值 gateway_param_invalid/gateway_drill_not_found/gateway_drill_conflict/gateway_config_write_failed。
- 验收 ✅：四门禁绿（ruff/mypy strict 34 文件/lint-imports 4 契约 KEPT/无 PG 123 passed 12 skipped）；PG16@5433 135 passed 零跳过；真装配冒烟两件——①真 complete 走 petro-main 记账落库（call-64ef2c41，168/2 token，¥0.000174），②真演练一次：注入 2 次失败→主用冷却→**真切换 petro-lite 应答留痕**（drill-84054290，账本 +1 条 fallback=true 行 ¥0.001382），轮询页徽标 degraded、演练历史/keyword 检索全过。litellm 进主依赖（uv add，1.75 系传递闭包）。

> **与合同的差异点登记（现实约束按现实落地，语义不私改）**：
> 1. **「8 端点」口径**：票面 8＝98 卡 D1 面 8 方法（含 complete 运行时出口）；HTTP 路由 98 §7 登记表冻结 7 条——本票落 7 条路由＋complete()。
> 2. **响应字段 snake_case（R1 接线批一次性改）**：D1 册 camelCase（drillId/inputTokens/modelKey/allowedFails…）→ 本端点即真实接线直接落 snake（drill_id/input_tokens/model_key/allowed_fails…）；query `page/pageSize` 保留现拼写（R1 原文）；演练 result 内 `ledgerRow`→`ledger_row`。D1 册正文的 camelCase→snake 迁移行挂设计仓下一版义务（本仓不代改，同 P0-04 差异 7 先例）。
> 3. **models.yaml 增补**（D1 真源文件内，业务事实零新增）：①models 条目补 name/access/note 三展示字段（D1 端点 1 列形；note/name 取注释原话，access 为按 provider 推导的展示值）；②文件尾新立 `gateway:` 段承载四参数（"表单里每个数字对应文件里的一行"的真源落位；缺省 2/60/3/30＝D1 合同示例值）；③PUT 写回＝gateway 段原位重写（行内注释保留、重复保存幂等不重段），其余字节逐字不动、${VAR} 占位符永不落明文——冒烟实证（重复 PUT 两次文件仍恰一段）；④写回落盘走同目录临时文件＋os.replace 原子替换（写前渲染文本内存校验，并发读无半截 yaml、写一半崩旧文件无损——P0-05 审查收口）。
> 4. **first_ms 口径**：非流式调用 TTFT 不可观测——账本 first_ms 落 total_ms 同值（数据形状红线已满足：整数毫秒）；真 TTFT 随 chat SSE 流式批再分列。
> 5. **演练机制**：ADR"演练＝平台侧开关临时摘主模型路由"落 gateway 域内 fault 开关——注入步不产生上游流量（直驱 allowed_fails 状态机直至冷却），最后一步是真实备用调用（演练即真实流量，D1 行为规则 3）；节点步进缺省 0.6s/步、构造参数可注（演示节奏不入合同，00 §5.2）；备用也应答失败时按 R4 双态合同收口 done（人话 summary＋result 空），不发明第三态。
> 6. **演练窗口 403 校验未落**：D1 行为规则 2 自标"预留"——挂演练窗口配置批（端点侧组闸 403 已有）。
> 7. **budget 判据先于 D5 页落位**：D5 面 budget/save_budget 端点未动（阶段 1），但判据消费方在本域 complete——gateway_budget_config 表已建、首次读取自动种子合同默认值（单次 0.05 元/月度 800 元，D5 §8＝F2 改注）；熔断位进程内存单向置位不自动恢复（F2 改注原文"进程生命周期内"），无 DB 持久化。
> 8. **4xx/429 重试语义拍板**：椒图蓝本只定"4xx/429 不切备"；是否同别名重试合同未冻结——本仓拍板不重试、直抛调用方；网络错/超时/5xx 同别名重试 num_retries 次全败才计一次别名失败再切备（Router 口径，W-F2-4/5）。429 退避重试挂实施批。
> 9. **spend-logs keyword 内存过滤**：演示量级下取回后内存匹配调用号/备注，不走 SQL LIKE（索引不背 keyword）；量级增长换 pgTrgm 挂实施批。备注缺省＝caller 标识（keyword 可检索；显式 note 优先）。
> 10. **98 卡 actor 槽差异（save_gateway_config / start_drill）**：卡面两签名均带 `actor: Actor`——本票配置真源为文件、域内无 who 落点，且 gateway 卡依赖行明示"无业务模块依赖"（不 import security.Actor）；接口层以组闸控权，两操作均经 security.audit 写 B12 审计（api 层编排，gateway 域不反向依赖 security）：config 保存＝`gateway.config.saved`、演练受理＝`gateway.drill.started`（演练是破坏性操作，who 留痕——P0-05 审查收口补齐）。
> 11. **新立业务错误码四值**（00 §3.3 只定 `<域>_<语义>` 规则、未冻结字符串；登记同 P0-04 差异 6 惯例）：`gateway_param_invalid`/`gateway_drill_not_found`/`gateway_drill_conflict`/`gateway_config_write_failed`。
> 12. **椒图蓝本变体：「每次切换恰一条审计」**——以账本注记列变体落地：切换留痕随记账行走（`served_model`/`attempted_fallbacks` 两注记列，99 §2.13），不另立审计行（账本一行即一次调用的完整留痕，切换事实不脱离账本单独存在）。
> 13. **椒图蓝本变体：「条件 UPDATE 记账防竞态」不适用**——本仓账本纯 INSERT 追加（append-only，记账不删改），无 UPDATE 语义可条件化；幂等由调用号 PK（call- 机器短 id）唯一承担。
> 14. **演练任务驱动＝进程内 asyncio task，非 infra.queue**：98 §4 说 gateway 演练是 queue 消费方——infra.queue P0-08 才建，先手搓（受理 202＋轮询＋重入 409 双保险照 00 §5 形）；并发后果＝进程崩溃重启遗留 running 僵尸行，由 lifespan 启动收口为 done（summary「进程中断收口」，幂等；双态合同不新增第三态），P0-08 落 queue 后可换装（stuck 巡检钩子接 infra.queue 惯例）。

## P0-06 前端底座（web/ fork + 五件）✅（2026-09-29）

- prototype/app → web/ fork（snapshot）；去 singlefile；vite proxy→:8000；eslint 进 CI。
- 双树路由：落地 #/X · 原型 #/proto/*；菜单角标。
- api/client（错误包解包/信封/X-Dev-User 注入/useTaskPolling）+ sse 客户端 + zustand 三槽 + 组件库首批（四态徽标/产物卡骨架）。
- 验收：web/ dev 起服；原型树全页可点（对照基线截图无漂移）；client 单测过。
- 落地 ✅：fork 快照 21 页面组件 + shell 五件零搬迁（`src/pages|flows|data` 原样）；工程形态去 singlefile（`vite.config.js` server.proxy `/api→:8000`，base `/`）；双树共存（`shell/Shell.jsx` parseHash 落地/原型、`shell/SideMenu.jsx` 落地项＋原型项并列带「原型」角标 21 枚、`landing/registry.js` 按阶段点亮）；底座五件：`api/client.js`（fetch 封装/X-Dev-User 默认 aqiang 读 localStorage 可改/错误包解包→antd message＋抛 ApiError/分页信封归一化/useTaskPolling＋pollTaskUntilDone，JSDoc）、`api/sse.js`（EventSource 帧分发/三帧语义/Last-Event-ID 接线说明，骨架＋单测桩不接 A1）、`store/app.js`（zustand 三槽：角色接 Shell/语义徽标占位/会话缓存占位）、`components/`（StateBadge 四态徽标 C3 合同色 + ArtifactCard 骨架 A1 端点 7/8 DTO）、eslint 平面配置 + CI frontend job（node 20：npm ci＋lint＋test＋build）；落地 D1 冒烟骨架页（仅接 GET /api/gateway/models，全页落地归 P0-07）。
- 验收自证 ✅：npm install/dev/build 三通；vitest 19 passed（client 11 + sse 8）；eslint 0 error（2 warning 均为原型快照存量 exhaustive-deps，不动）；后端 uvicorn :8000 起（PG16@5433）＋ vite proxy 真往返——playwright 抽查 #/proto/{A1,D1,C3,F1,INDEX} 5 页全渲染 0 pageerror，落地 #/D1 真数据 2 行（petro-main/petro-lite）＋页头「运行中」徽标＋菜单一键切树。
- 四门禁回归 ✅：ruff 全过 / mypy strict 34 文件零错 / pytest 带 PG 143 passed / lint-imports 4 契约 KEPT。

> **与设计/票面的差异点登记（现实约束按现实落地，语义不私改）**：
> 1. **shot.mjs 不随 fork**：单文件截图工具依赖 file://＋dist 单文件形态，随 singlefile 退役留在 prototype 仓（fork 是复制非引用，teach-petro-agent 原件零改动）；POLISH-SPEC.md 留档随 fork。
> 2. **快照机械 lint 修 6 文件**（eslint 门禁所迫，全部未用 import/变量级、行为零变化）：flows/dataClean 去 MatchList、flows/scenarios/stateBack 去 NCode、pages/E1 去 dayjs/ThunderboltOutlined、pages/B1 `fixRow→_fixRow`、shell/HeaderBar 去 Space、shell/TraceBar 去 Layout。
> 3. **eslint no-unused-vars args:'none'**：原型快照统一渲染签名占位参（chosen/onChoose/sc 等 30+ 处）不拦——改名反搅快照；未用声明/import 仍 error。
> 4. **no-irregular-whitespace 关**：原型页全角空格为中文排版刻意用字（契约溯源条等）。
> 5. **落地页注册表＝显式 map（LANDING_MODULES）**：`import(\`./${key}.jsx\`)` 自目录变量导入 Vite 无法分析（dev 实跑 warning 实证）；LANDING_LIT 改由 map keys 派生保持单源。
> 6. **菜单落地项只列已点亮页**：设计 §4「落地页按阶段点亮」落地为菜单＝LANDING_LIT（当前仅 D1）＋全部原型页带角标；未点亮页 hash 直达 #/X 落 NotLit 占位（出路指引一键跳 #/proto/X）。
> 7. **CI frontend job 增 test 步**：票面写 npm ci＋lint＋build，验收另要求 client 单测过——vitest 一并进 job。
> 8. **client.js 不静态 import antd**：错误提示器走 dynamic import＋`setApiNotifier` 替换缝——node 测试环境（vitest 无 DOM）可加载，生产提示路径不变。
> 9. **useTaskPolling 终态判定＝白名单进行中集**（queued/accepted/pending/processing/running/generating＝00 §5.1 全部 11 处先例并集），不在集内即终态 fail-safe——后端新增状态默认按终态收场，不挂死轮询。
> 10. **页面组件数口径：设计 §1 原文「22 个页面组件」vs 本票「21」**：prototype pages/ 实有 23 文件＝21 可路由菜单页（roles.js 菜单 21 键＝Shell 路由面）＋DecisionTree 弹窗件（页内开窗、不占菜单路由）＋Stub 占位件（未路由兜底）——菜单 21 角标与 fork 零搬迁口径均按 21，成立（P0-06 审查补注）。
> 11. **组件库首批 2/6**：设计 §2.4 六组件已交 StateBadge 四态徽标＋Artifact 产物卡 2 件；Voucher 取货凭证卡/答案卡＋cN 引用/解释链五要素/审批抽屉 4 件未交——按设计 §5 阶段 1-4「按需抽组件进库」随各页落地批抽取；阶段 0 行「底座五件全建」指 client/sse/zustand/组件库缝/工程形态五件，非组件六件（P0-06 审查补登记）。

## P0-07 D1 页面落地（首个真 API 页面）

- D1.jsx 数据源从 mock 切 api/client；页头徽标/配置读写/spend 流水/演练工具栏全接线。
- 验收：D1 合同 8 端点真实往返；与 #/proto/D1 对比行为一致（除数据真假）。

## P0-08 预留件：chat SSE 骨架 + eventbus + 迁移分组

- /api/chat 路由族空壳 + SSE 信封（00 册 §6 三帧语义）；eventbus（Redis Streams+outbox 表）接口缝；Alembic 迁移分组（sem_/kb_ 等按 99 册前缀）。
- 验收：事件发布-订阅内存实现测试过；Alembic upgrade/downgrade 空迁移过。

## 阶段 0 收官验收

四门禁全绿 + D1 八端点真跑 + 前端双树对比可用 + B1–B16 边界闸在真实代码上绿。
