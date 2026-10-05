# 生产建号 runbook——三账号＋环境变量＋口令纪律＋MinIO 清理策略

> 来源：DEP-01 部署准备批（阶段 2 移交清单）。账号模板真源＝data-plane 仓
> `migrations/`（midplatform_readonly.sql／agg_writer.sql／quality_writer.sql）；
> 表结构真源＝主仓 Alembic 迁移链（`uv run alembic upgrade head`，勿用应用进程
> 建生产表）。本文是操作手册，不是合同——业务语义疑问查 teach-petro-agent
> docs/business-setting.md 与合同册。

## 1. 三账号逐步建号流程（生产实例）

三个账号全部走「模板替换占位符 → 密管注入口令 → 超级用户执行 → 三分法验证」
四步，逐账号如下。共同前置：

1. 表结构先行：目标库先跑完主仓迁移链（`alembic upgrade head`）——账号授权的
   表必须已存在（agg 三表＝0014、quality 表族＝0015、gateway 三表＝0018）。
2. 口令生成：密管（部署环境的 secret 管理）生成随机口令，**不经聊天记录/工单
   明文传递**（注入方式见 §3）。
3. 模板执行身份：以目标库超级用户（或持 CREATEROLE＋可授权身份）执行。

### 1.1 midplatform——中台源只读账号（平台侧读中台 8 表）

- 模板：data-plane 仓 `migrations/midplatform_readonly.sql`。
- 执行实例：**中台库**生产实例（8 张 as-is 源表所在库；生产＝独立实例，
  ADR-0003 拍板 2——中台库归数据面全权）。
- 占位符替换：`<SET_ME>`（CREATE ROLE PASSWORD 一处）→ 密管口令。
- 步骤：
  1. `CREATE ROLE midplatform LOGIN PASSWORD '<密管口令>';`
  2. `GRANT USAGE ON SCHEMA raw`＋8 源表 `SELECT`（照模板逐行，模板即闭世界——
     clean/data_plane schema 与湖元数据两表零授权）。
  3. `ALTER ROLE midplatform SET default_transaction_read_only = on;`（连接级只读兜底）。
- 平台侧配套：主仓 `config/database.yaml` midplatform 段经
  `MIDPLATFORM_PG_HOST/PORT/DB/USER/PASSWORD` 注入；`app/main.py` 启动即校验
  （`verify_midplatform_route`——缺配置/规格未只读/写探针未被拒＝拒绝启动，
  无静默降级）。

### 1.2 tpa_agg_writer——agg 限写三表专用账号（数据面直写汇总层）

- 模板：data-plane 仓 `migrations/agg_writer.sql`。
- 执行实例：承载 **agg schema** 的主平台库实例（agg DDL＝主仓 Alembic 0014）。
  模板内另有 clean 层只读段——dev 期与 agg 同实例（compose 拓扑）；生产若按
  ADR-0003 裁决 2 拆独立中台实例，该段归属随部署批按实际拓扑核对后裁剪
  （本行是登记的核对点，不是授权变更）。
- 占位符替换：`${AGG_WRITER_PASSWORD}` → 密管口令。
- 步骤：照模板逐句执行（`CREATE ROLE`＋6 句 GRANT——USAGE agg＋恰三表
  SELECT/INSERT/UPDATE/DELETE＋USAGE clean＋clean 全表 SELECT）。闭世界：raw/
  data_plane/public 零授权、无 CREATE/ALTER、不设 ALTER DEFAULT PRIVILEGES。
- 数据面配套：`AGG_DATABASE_URL` 指向本账号；未配＝worker agg 步显式跳过
  （日志 warning，不静默装成功）。

### 1.3 tpa_quality_writer——质检限写＋rule 只读账号

- 模板：data-plane 仓 `migrations/quality_writer.sql`。
- 执行实例：主平台库（quality 表族＋water_line 落主平台库 public——同源裁决，
  DP-05；启停＝主平台 E2 独写，M-05a PATCH 唯一写口）。
- 占位符替换：`${QUALITY_WRITER_PASSWORD}` → 密管口令。
- 步骤：照模板逐句执行（`CREATE ROLE`＋7 句 GRANT——quality_rule 只读；
  quarantine_row 仅 INSERT＋序列 USAGE＋SELECT（DP-06.fix F1 幂等寻址）；
  quality_task/water_line 写读）。闭世界：其余 schema/表零授权。
- 数据面配套：`QUALITY_DATABASE_URL` 指向本账号；未配＝质检落库/报水位显式
  跳过、拾取作业不装配。

### 1.4 GRANT 验证三分法（每账号必过三关）

1. **正向**（应通的通）：以该账号连接，做模板授予的操作——
   `SELECT has_table_privilege('<role>','<table>','<priv>')` 逐表为 true，或直接
   跑一条真 SELECT/INSERT 冒烟。
2. **负向**（应拒的拒）：以该账号连接，做模板未授的操作——写 public 其他表、
   `CREATE TABLE`、`ALTER`、跨 schema 读（如 agg_writer 读 raw）——每项预期
   `InsufficientPrivilege`（psycopg 侧机判先例＝data-plane
   `tests/pg/test_agg_star.py::TestRestrictedWriterAccount`、
   `tests/pg/test_quality_store.py` 限写账号测试同款）。
3. **闭世界对账**（授权面恰如模板）：
   ```sql
   SELECT table_name, privilege_type FROM information_schema.role_table_grants
   WHERE grantee = '<role>' ORDER BY 1, 2;
   ```
   结果集与模板 GRANT 句逐一对照：midplatform＝8 表 SELECT；tpa_agg_writer＝
   恰 6 句 GRANT 的展开面；tpa_quality_writer＝恰 7 句的展开面。多出的任何一行
   都是越权，按事故处理。

## 2. 环境变量清单表

| 变量 | 用途 | 示例 | 缺省行为 |
|---|---|---|---|
| `DATABASE_URL` | 数据面湖底座 PG 连接（raw schema＋data_plane 元数据；`LakeCatalog.from_env`） | `postgresql://<湖账号>:***@mid-prod:5432/petro` | 未配＝`ValueError` 拒装配（不静默起湖） |
| `MINIO_ENDPOINT` | 湖原始批文件对象存储端点 | `http://minio-prod:9000` | 未配＝同上 `ValueError` |
| `MINIO_ACCESS_KEY` | 对象存储访问键 | `***`（密管注入） | 未配＝同上 |
| `MINIO_SECRET_KEY` | 对象存储访问密钥 | `***`（密管注入） | 未配＝同上 |
| `AGG_DATABASE_URL` | agg 星型三表直写连接（tpa_agg_writer；`AggStarWriter.from_env`） | `postgresql://tpa_agg_writer:***@platform-prod:5432/petro` | 未配＝worker agg 步显式跳过（日志 warning） |
| `QUALITY_DATABASE_URL` | 质检落库/水位/拾取连接（tpa_quality_writer；`QualityStore.from_env`） | `postgresql://tpa_quality_writer:***@platform-prod:5432/petro` | 未配＝质检落库/报水位显式跳过、拾取作业不装配 |
| `MIDPLATFORM_PG_HOST` | 平台中台只读路由——主机（主仓 `config/database.yaml` midplatform 段 `${VAR:-默认}`） | `mid-prod.internal` | 缺省回落 `localhost`（dev 演示态） |
| `MIDPLATFORM_PG_PORT` | 同上——端口 | `5432` | 缺省回落 `5433` |
| `MIDPLATFORM_PG_DB` | 同上——库名 | `petro` | 缺省回落 `petro` |
| `MIDPLATFORM_PG_USER` | 同上——账号（§1.1 建号产物） | `midplatform` | 缺省回落 `midplatform` |
| `MIDPLATFORM_PG_PASSWORD` | 同上——口令（密管注入） | `***` | 缺省回落 `midplatform`（**开发默认，生产禁用**——§3） |
| `PG_HOST` / `PG_PORT` / `PG_DB` / `PG_USER` / `PG_PASSWORD` | 平台主库 primary 段（同 `${VAR:-默认}` 机制；Alembic 迁移与应用同源推导） | `prod-db.internal` / `5432` / `petro` / `<主库账号>` / `***` | 缺省回落 `localhost:5433/petro`＋`petro/petro`（**开发默认，生产禁用**——§3） |

> 表内前六行＝数据面装配（data-plane 仓消费）；`MIDPLATFORM_PG_*` 与 `PG_*` ＝
> 主仓 `config/database.yaml` 占位符（`app/infra/config.load_database_specs`
> 解析，`tests/infra/test_config.py` 机判「环境量在位覆盖默认／缺省回落默认」
> 两半边）。

## 3. 口令纪律：生产口令经环境注入，禁止默认口令上生产

1. **机制**：`config/database.yaml` 只进结构与开发默认，凭证一律 `${VAR:-默认}`
   占位符——环境量在位时覆盖默认、缺省回落默认（`app/infra/config.resolve_placeholders`：
   os.environ 优先、`.env` 兜底、再回落 yaml 默认）。
2. **禁止默认口令上生产**：本仓一切开发默认口令——`petro/petro`（primary）、
   `midplatform/midplatform`（中台只读）、compose 内 `petro12345`（MinIO/Neo4j
   root）——落到生产即事故。生产口令唯一合法来源＝密管生成、经 §2 表内环境量注入。
3. **凭证不进 git、不入日志**：账号模板内 `<SET_ME>`/`${..._PASSWORD}` 占位符由
   部署环境替换后执行；执行方式优先密管注入（如 `psql` 读环境量拼装），避免把
   替换后的明文 SQL 落 shell history 与工单。
4. **验证钩子**：§1.4 三分法的负向关同时是口令面验证——账号口令只该被对应
   服务持有，其余任何凭证连不上。

## 4. MinIO 清理策略（安全优先——只列不删是现状）

- **对象面**：湖桶（dev＝`tpa-raw`）按 `{table}/{batch_id}/data.csv` 键存原始批
  文件；`data_plane.lake_snapshot.data_object_key` 是引用真源（湖写序＝先留桶后
  落账——PG 侧失败会遗留**孤儿对象**：有文件、无快照账行）。
- **保留期建议**：隔离/拒收相关批文件保留 **≥90 天**（质检复核、审计追溯的
  取证窗；90 为建议值非裁决——真删除策略与开关归 Owner 部署批拍板）。
- **先列后删两步制**：
  1. **列**（已交付）：data-plane worker `gc_orphans`（`python -m worker.gc` 人工
     触发）——列出「桶内存在但快照账无引用、且 LastModified 早于保留期」的
     孤儿对象清单，**仅日志与返回值，不删除**；超期阈值
     `DP_GC_RETENTION_DAYS`（缺省 90）。`gc_orphans` **默认不注册调度作业**
     （`build_scheduler` 不装配——防自动删除；清单即人工复核的输入）。
  2. **删**（未交付，归 Owner 部署批拍板）：人工复核清单后另行执行；仓内现状
     **零删除实现**——任何删除能力落仓前必须先过 Owner 裁决并带负向测试。
- **红线**：有快照账引用的对象永不清（湖 append-only 教义——expire 只清时间
  旅行可见性，不清当前视图数据）；清理操作本身须留痕（清单输出存档）。

## 5. dev 容器已执行的授权动作与生产差异

| 项 | dev（compose 容器）现状 | 生产要求（本 runbook） |
|---|---|---|
| 账号 | 仅 `midplatform` 已建（容器内实跑 midplatform_readonly.sql，口令＝开发默认 `midplatform`，演示态）；agg/quality 两账号**未建** | 三账号全建，口令全部密管注入（§3） |
| 数据面连接 | 直连 `petro` 开发账号（`AGG/QUALITY_DATABASE_URL` 指向 petro——限写语义靠应用侧白名单承载） | 限写语义账号级＋应用侧双层承载（模板 GRANT＋写面白名单） |
| 模板 GRANT 的执行 | 仅测试内实装验证（data-plane `tests/pg/` 限写账号测试：建号→三分法探针→DROP OWNED→DROP ROLE 清场，库零残留） | 生产实例人工执行＋三分法全过（§1.4） |
| 表结构 | 应用启动 ensure_*（幂等）＋Alembic 并行存活 | 迁移链先行（`alembic upgrade head`，gateway 表族已入链＝0018）；ensure 仅启动兜底 |
| 网络与传输 | 本机端口映射、无 TLS | 传输/网络层加固归部署批（本仓模板未覆盖——登记项） |
