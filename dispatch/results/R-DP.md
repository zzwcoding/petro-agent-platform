# R-DP 全量审查回报（阶段 2 收官·批 1/3——data-plane 嵌套独立仓 DP-01~06 合并态）

PROTOCOL 骨架：
- **审查对象**：嵌套独立仓 `/Users/divh/Downloads/petro-agent-platform/data-plane/`，HEAD=**7d109b3**（与任务指定一致；`git status` 工作树干净）＝DP-01 清场→DP-02 归位→DP-03 湖真身+修复拍→DP-04 调度+agg→DP-05 质检落库→DP-06 拾取器+修复拍的六票合并态。六节范围（纪律与迁移链／湖语义／质检表族与水位／拾取与自愈／六票接缝／测试基线与合同漂移）。
- **审查方式**：全程只读，永不改代码；hermetic ci.sh 与 PG16+MinIO（主仓 compose `petro-agent-platform-pg-1`@localhost:5433＋`minio-1`@9000）全量独立复跑；主仓消费面（M-05a/b 行形合同、alembic 0014/0015、infra.clock、domain.hit_identity）只读对照（主仓替身行形断言**未复跑**——零接触红线，改用 data-plane 侧 168 全绿＋冻结字面逐字段比对交叉印证）；teach 真源（99 册 §2.0/§2.12/§4.4、设定书 §A、D6 坑一、E2 册报告 DTO、teach dp1/dp2 卡）只读引用未复制正文；dev 库取证全部经 `docker exec … psql` 只读 SELECT；MinIO 仅列桶清单（`tpa-raw`/`tpa-raw-test` 元数据只读），零对象触碰，测试复跑走 `tpa-raw-test` 临时桶；主仓 Owner 私产与并行 UI 改动零接触。
- **零修复声明**：本审查未对 data-plane 仓做任何代码/配置/数据变更（末节重申）。

---

## 0. 环境与复跑记录（交付闸面）

| 项 | 结果 | 判定 |
|---|---|---|
| `env -u TEST_DATABASE_URL … ./ci.sh`（hermetic，/opt/homebrew/bin/python3＝3.14.7） | spec gate **PASS（0 警告）**＋**113 passed, 6 skipped**（0.54s；6 skip＝模块级 importorskip：boto3×2＋psycopg×4，hermetic 环境 deque 外依不装——skip 语义核过） | ✅ 与 DP-06.fix 申报基线（113+6）一致 |
| `TEST_DATABASE_URL=postgresql://petro:petro@localhost:5433/petro .venv/bin/python -m pytest -q tests/`（PG16＋MinIO，.venv 3.12.13，测试桶 tpa-raw-test） | **168 passed, 0 skipped**（30.56s） | ✅ 与 DP-06.fix 申报基线（168 全绿）一致 |
| 迁移态 | `data_plane.schema_migrations` 恰 1 行（001）；raw/clean/data_plane 三 schema 在位；quality 六表＋agg 三表由主仓 alembic 0017 头供给 | ✅ |
| dev 库残留复核（quality_task/quarantine_row/water_line/lake_snapshot/raw 两表/freshness_registry/agg 三表） | 全部 **0 行** | ✅（audit_record 残 1 行旧探针，见 F-12） |

---

## 1. 第 1 节 仓纪律与迁移链——通过（AGENTS.md 约定遵守；up/down 成对幂等机判在位；三账号模板闭世界逐句核过）

- **纪律面**：AGENTS.md（嵌套仓自有）与主仓硬纪律不冲突——合同引用不复制正文（001 头注只引路径＋锚号）✓；pytest rootdir 由自有 pyproject.toml 锚定阻断向上拾取主仓配置（DP-01 验收项，实测 hermetic 全绿佐证）✓；写面/审计/时钟等统一出口在本仓自洽（本仓无主仓 app 依赖，`git grep` 零交叉 import）✓。
- **migrations/001 up/down 成对＋幂等**：`tools/migrate.py:44-55` `_pairs()` 对 up/down 做对称差校验（未成对即 exit）✓；001 up 全量 `CREATE … IF NOT EXISTS`（含 `idx_lake_snapshot_table`，001:38——湖先 boot（`LakeCatalog._ensure_meta` 同形兜底建同名索引）再跑迁移不炸的 F2 缺口已闭）✓；机判在位且复跑通过：`tests/migrations/test_migration.py:86`（down→up→断言→down→up 往返）＋`:130`（湖先 boot 再 up 幂等）。
- **tools/migrate.py 账本纪律**：账本＝`data_plane.schema_migrations`（version PK）；up 逐文件先执行后记账、两段各自 commit——半途残账由 DDL 幂等兜底可重入 ✓；down **账先行**（先删账再回滚，migrate.py:118-124——001 的 down 会 DROP data_plane schema 连带账本，删账保证回滚失败时账与结构不脱钩、可重入）✓；账本消失＝已到未迁移态不再重建（migrate.py:109-112）✓。
- **midplatform_readonly.sql 闭世界复核**：`CREATE ROLE midplatform`＋`GRANT USAGE ON SCHEMA raw`＋恰 8 张源表 `GRANT SELECT`（逐表点名，与 001 八表一一对应）＋`ALTER ROLE … SET default_transaction_read_only = on` 连接级兜底；clean/data_plane/湖元数据两表零授权、无 `ALTER DEFAULT PRIVILEGES`（新表不自动暴露）✓；机判 `tests/migrations/test_migration.py:157`（8 表全覆盖＋GRANT 行不含 clean/data_plane）。交付位＝部署批执行、不进迁移链（99 §4.4「midplatform 不迁移」的仓内对应）✓。
- **quality_writer.sql 闭世界复核**：GRANT 恰 7 句——①`SELECT quality_rule`（启停只读）②`SELECT,INSERT,UPDATE quality_task` ③④`SELECT`＋`INSERT quarantine_row`（F1 幂等寻址需读权；**UPDATE/DELETE 零授权——账号级 append-only 不松**）⑤`USAGE,SELECT ON SEQUENCE quarantine_row_id_seq`（bigserial 随 INSERT）⑥`SELECT,INSERT,UPDATE water_line`（ON CONFLICT 读旧行需 SELECT）；无 CREATE/ALTER/DEFAULT PRIVILEGES，raw/agg/clean/data_plane/public 其余表零授权 ✓；机判 `tests/pg/test_quality_store.py:265`（恰 7 句逐句字面断言）＋限写账号实装负测试四件（:209 写边界恰集、:224 quality_rule 写拒、:231 quarantine UPDATE/DELETE 拒、:256 越界表/CREATE/ALTER 拒）全绿。
- **agg_writer.sql 闭世界复核**：`USAGE agg`＋恰三表 `SELECT/INSERT/UPDATE/DELETE`＋`USAGE clean`＋`SELECT ON ALL TABLES IN SCHEMA clean`（当前时点授权，不设 DEFAULT PRIVILEGES＝未来 clean 落表不自动暴露，:20-21 注记与 midplatform 同款纪律）✓；实装负测试 `tests/pg/test_agg_star.py:210/229`（raw/data_plane/public 写拒＋CREATE/DROP/ALTER 拒＋闭世界断言）全绿。

## 2. 第 2 节 湖语义——通过（as-of 时点视图/dp1 卡/dp7 replay 契约逐句复核成立；写面三闸＋fail-closed 在位；发现 F-05/F-06）

- **as-of 时点视图（DP-03.fix F1 回贴 D6 坑一）逐句复核**：`lake_store.py:153-198 scan()`——①`snapshot_id=N` 时 `_snapshot_id <= %s` 时点过滤；②每业务键取最新生效版＝`RANK() OVER (PARTITION BY <业务键> ORDER BY _snapshot_id DESC) … WHERE _dp_asof_rk = 1`（**RANK 非 ROW_NUMBER＝同快照并列行全保留**，A/B 班重复行合法内容不吞）；③业务键 `_BUSINESS_KEYS`（:76-85）照抄 001 表 COMMENT 逻辑键零发明，键列与实有列取交集，未登记表退化纯时点过滤；④**谓词在坍缩之后过滤**（:181-183——旧版值不能借谓词翻出），列名白名单＋参数化值防注入；⑤快照账无 N＝`SnapshotGoneError` 绝不静默回退当前快照（:159-160）。四形态机判全绿：`tests/dp1/test_lake_store.py:227`（同键新版覆盖）/`:236`（N 之前时点见旧版）/`:244`（同批并列全保留）/`:257`（**替身与真身逐行相等**——conftest FakeSnapshotCatalog 键控合并对齐真身的语义一致断言）。
- **dp1 卡契约**：schema()＝业务列视图（`_` 前缀湖管道列不外露，:138-146）；snapshots()/SnapshotInfo（committed_at＝DB 真时钟，替身 "now" 字面缺口补齐，测试 `:92`）；门面**故意不暴露** overwrite/delete/upsert（`TestWriteSurface:340` 机判）✓。append＝MinIO 先留桶→PG 单事务（快照账行＋raw 行，:410 注记「PG 失败只留孤儿对象不留悬空快照账」）；`LakeTypeError` 脏值显式拒绝（:529-553「12.40方」类不改写；测试 `:139`）；well_overhaul 业务 `batch_id` 撞名让位 `_src_batch_id`（:413-414，与 001:121 注记互证）。
- **dp7 replay 契约**：`audit.py:111-120 replay` 按记录快照重跑、RF-05 等值归一（arrow→to_pylist 后比较）；实跑链 `tests/dp7/test_retention_real.py:51`（expire 真链路→SnapshotGoneError 沿调用链浮出）＋`:76`（**同快照重放在 as-of 语义下成立**——后续批同键改值，按记录快照重放仍 match=True）✓。
- **写面三闸**：`_WRITE_ALLOWED=("dp2.ingest","dp3.transform")`／`_EXPIRE_ALLOWED=("dp7.retention",)`（:69-70），`begin_caller` 身份声明＋`_require_writer/_require_expire` 越界 `BoundaryViolation`；dp2 进料以 dp2.ingest 身份调 append（ingest.py:119）；dp7 保留以 dp7.retention 驱动 expire（audit.py:94-97 enforce_retention——DP-06 顺带清理的死路 hasattr 残件已不存在）✓。
- **fail-closed（无规则表拒绝入湖）**：`ingest.py:110-112`——表不在规则清单**或规则清单为空**一律 `UnruledTableRejected`，append 不发生；机判 `tests/dp2/test_ingest.py:130`＋`:142`（空清单同拒）✓；闸在编排层（validate 先行→`BatchRejected` 拒批，脏批真身不落库 `tests/dp2/test_ingest_real.py:105`）✓。

## 3. 第 3 节 质检表族与水位——通过（与主仓 M-05a/M-05b 消费面逐字段对账零偏差；发现 F-01/F-02/F-03/F-04）

- **行形合同对账（两仓互证）**：
  - `quality_task`：数据面 `create_task` INSERT (id,status='running',step=1,rules_count,time)、`finish_task` UPDATE status='done'/step/hits/report（quality_store.py:171-192）——与主仓 0015 DDL（migrations/versions/20261004_0015_quality_waterline.py:133-155）列形、CHECK('running','done') 逐列一致；step 语义链（0＝M-05b 受理待拾取→1＝认领/扫描执行中→2＝数据面完→4＝E2 接续建单后）两仓 docstring/注释互证一致（quality_store.py:196-234 ↔ 主仓 service.py:385-399）。
  - **报告恰八键/hits 五键**：`run_quality_task` report＝{range, tables, scanned_rows, rules_run, quarantined_rows, rejected_batches, hits, verdict}、hits 条目＝{rule_no, kind, action, hit_count, sample≤5}（quality_store.py:325-336）——与主仓 M-05b 集成替身冻结字面（tests/domains/dataops/quality/test_quality_task_channel.py:32-59 `_report/_hit`）**逐字段一致**；99 册合同键 quarantined_rows/rejected_batches 必带、单据粒度（规则＋对象＋数据日期去重 `_issue_key`）与数据粒度分开报（E2 册 :86 口径）✓；data-plane 侧机判两处（hermetic `tests/worker/test_pickup.py:145`「恰八键零形状偏差」＋PG `tests/pg/test_quality_store.py:333`）。
  - `quarantine_row`：写 (batch_id, rule_no, action, loc, payload)——0015 列形＋CHECK('隔离','整批拒收')；告警档零隔离行（E2 端点 9，机判 :109）；payload＝原始坏行 as-is（`_payload_row` 定位器交集全等首行）；整批拒收落批次级记录 payload={"locators":[…]}——与主仓 domain.py:124 `HIT_BATCH_LOCATORS_KEY` 消费形一致。
  - `water_line`：`raise_water_line` ON CONFLICT (layer) DO UPDATE … WHERE EXCLUDED.data_date > water_line.data_date（单调不回退，quality_store.py:267-279）；三 tier＋promise=T-1 迁移默认承载（本票只报水位不判达标——E2 端点 8 口径）；机判 `tests/pg/test_quality_store.py:156/170`（三 tier 回写＋旧日期不回退＋无日期键不虚标）。
  - 复扫判绿对位：报告 sample 定位器键集（well_id/equip_id/batch_id/channel_id/block_name/month/code＋日期五键）与主仓 `domain.py:118-123 HIT_IDENT_KEYS/HIT_DATE_KEYS` 白名单投影对得上（rule-8 {equip_id,code}、rule-5 {well_id,prod_date} 两形即主仓测试 EQUIP_HIT/WELL_HIT 同构）✓。
- **启停只读集**：`enabled_rules` 只读 quality_rule WHERE enabled（quality_store.py:155-161）；13-20 种子 enabled=false 仅登记不实施（evaluate_enabled 无执行体如实跳过，:111-124＋机判 `tests/dp3/test_quality_run.py:121`）；启停写口＝主平台 E2 独写（限写账号 UPDATE/INSERT quality_rule 拒，:224 机判）✓。
- **QT 1:1 报告**：任务行与报告 jsonb 一行 1:1（机判 `:94` len(task)==1）；`quarantined_rows`（数据粒度）×物理隔离行数对账机判在位（:108＋pickup 两测）。
- **发现**：扫描面缺口 F-01（本节最大项，详见发现清单）、取号竞窗 F-02、水位日期口径 F-03、幂等键计数边缘 F-04。

## 4. 第 4 节 拾取器与自愈——通过（pending 口径/claim 原子认领/heal DB 钟/R2 注记三处在位；heal 误伤窗复核通过）

- **pending 口径**：`pending_tasks`＝status='running' AND step=0 ORDER BY time,id（FIFO——M-05b 冻结语义 step=0＝待拾取外部任务；管道自建行 step=1 不在候选）；DP-06.fix F3 死参 now 已清（签名机判 `tests/worker/test_pickup.py:273`）✓。
- **claim 原子认领**：条件 UPDATE 单语句 `SET step=1 WHERE id=%s AND status='running' AND step=0`，rowcount 说话（quality_store.py:206-213——M-05b claim_task_followup 先例同构）；PG 实跑单发/防重复拾取机判（`tests/pg/test_quality_store.py:344`＋hermetic `:284`）✓。
- **heal 重置形＋误伤窗复核**：`heal_stale_tasks`＝running∧step=1 且 `time < (now() AT TIME ZONE 'Asia/Shanghai') - (%s * interval '1 second')`（quality_store.py:228-234）——**阈值比较钟＝数据库东八区钟，单语句原子**（DP-06.fix F2）；与外部受理行写入口径同源核过：主仓 `infra/clock.py:36-45` now()＝东八区 naive（new_task time=now()，store.py:404-412）↔ 数据面 `now() AT TIME ZONE 'Asia/Shanghai'` naive——两写方同钟同形成立，宿主机时区零耦合。误伤双半边机判：宿主机慢 8h 残行照常自愈＋宿主机快 1h 在途行不被误重置（`tests/pg/test_quality_store.py:380/396`，monkeypatch 模块 datetime 证 DB 钟实现不可见）✓。
  - 残窗维持观察（**已登记前提非新缺陷**）：time＝行创建钟（0015 无 updated_at），「超阈无更新」以创建钟近似——单任务执行时长>阈值时在途行可被重置；真实双执行需多实例或 worker 重启＋旧进程并存；F1 幂等已封落区副作用、finish_task 无条件 UPDATE 的最坏面＝报告重写（at-least-once 语义内）。docstring 单写者前提＋「多实例需先加租约列（DDL 冻结——挂 DP-06 疑点）」登记在位（quality_store.py:224-227）。
- **R2 假绿注记三处在位**：①模块头登记（worker/scheduler.py:24-27＋:60-63 R2_SAMPLE_NOTE 常量，文案键「R2」「sample」为对账锚）②拾取作业 docstring（:204-206）③拾取产报告 verdict 头续写（run_quality_task verdict_note 形——quality_store.py:333-335 报告键集不变只续写文案）；机判 `tests/worker/test_pickup.py:158`＋PG `:342`（verdict 含 R2/sample）✓。
- **假绿防线**：湖视图空→本周期不拾取（run_pickup_once `if not bundle or not any(bundle.values())` 拒产空扫描报告，行原样 step=0）；执行中断行如实停 step=1 下周期自愈重拾（毒任务两周期回路机判 `test_pickup.py:228`）；未配 QUALITY_DATABASE_URL 拾取作业不装配（build_scheduler :280-287，不静默装空作业）✓。**部分表空不设防**＝F-01 的另一半边。

## 5. 第 5 节 六票接缝——通过（互相消费的接口面无漂移；parquet/问答面退役零活性残留；发现 F-07/F-09）

| 接缝 | 复核结论 |
|---|---|
| DP-01 清场（hermetic）×全仓 | pyproject.toml 锚定 rootdir＋tests/fixtures/fieldforge 合成最小集（9 CSV）在位；hermetic 复跑全绿即基线成立 ✓ |
| DP-02 删除面×存量 | semantic/query_runner/tools_mcp **零活性 import**（仅注释/注记/留档标本）；dp6/dp7 保留标注＋StructuredQuery/TimeWindow 逐字内联落位 audit.py/freshness.py 供 pg_store/dp7/主仓对照消费（pg_store.py:18 一行 import）✓；DEPRECATED 头注三处在位（serve/__init__.py、deploy/Dockerfile、deploy/api-requirements.txt）；410 恒返五路由＋/healthz deprecated 标记（代码逐条核过；计数注记出入见 F-09） |
| DP-03 湖×上下游 | ingest 三步契约接真身（run_csv_load 收编 CSV 输入、batch_id/source 透传、manifest 血缘随 commit）；pg_store freshness/audit 归位 data_plane schema（001 DDL 同形幂等，pg_store._DDL 与 001:43-59 逐列一致）✓ |
| DP-04 agg 管道与调度 | agg 星型三表＝99 §2.12 合同值（grain 一井×一天、dim_date 确定性生成、写面白名单恰三表 upsert 幂等）；APScheduler 真引入＋`--once` 干跑；P4/P6 修复在位（_r2_ratio bundle 签名 transform.py:183-192；as_of＝快照 committed_at ingest.py:128-132）；RULES_WELL_INFO 行级半边进料闸（transform.py:123-139，值域照抄 _r16）✓ |
| DP-05 质检落库×DP-04 管道 | run_pipeline_once 一周期六件事接线（质检 QT 号随 provenance 入湖 quality_report_id；原始/清洗层＋汇总层三 tier 报水位）；transform 内存弃置路径清零（QualityReport 类已不存在，GateVerdict/evaluate_bundle 形）✓ |
| DP-06 拾取×DP-05 落库 | run_quality_task task_id 拾取形（受理行 rules_count/time 原样不动、verdict_note 续写）；隔离行 batch_id=任务号；湖 as-of 当前视图 bundle、缺表诚实跳过 ✓（扫描面缺口归 F-01） |
| parquet 退役零残留 | `build_marts/_MARTS_SQL/BuildResult/parquet 物化路径`零活性代码（grep 全仓仅 docstring/注记/机判反证 `tests/dp3/test_agg.py:84`）；prd.md:145 与 specs/modules.md:62-71 均有退役注记 ✓ |
| 问答面 410 退役零残留 | 五路由恒 410＋留档段标注「永不触达」；`git ls-files` 无 learning/残留；deleted 模块文件不在 tracked 清单 ✓ |

## 6. 第 6 节 测试基线与合同漂移——基线全绿；漂移三项（F-07/F-08/F-11）＋测试卫生 F-12

- **hermetic 复跑**：`/opt/homebrew/bin/python3`（3.14.7，仓内 ci.sh 直接消费）→ spec gate 0 警告＋113 passed 6 skipped——skip 全部为模块级 `pytest.importorskip`（psycopg/boto3 未装环境），hermetic 性质成立（无 PG/MinIO 触达）。
- **PG16+MinIO 复跑**：主仓 compose 容器（PG@5433＋MinIO@9000），`.venv`（3.12.13）→ 168 passed 0 skipped；测试桶＝`tpa-raw-test`（零生产桶接触边界遵守）。
- **teach 真源逐项对账**：99 §2.0（8 表 as-is 中台原始层＋平台侧三件）↔ 001 头注与落表 ✓；99 §2.12（quality 六表/agg 三表列形、quality_task 行形、water_line 行为约定 8）↔ 0015 与数据面写读面逐列一致（唯一出入＝agg 精度技术自选登记 F-08）；99 §4.4（迁移形态/账号建立随部署批不进迁移链/两权分离 2026-10-05 修正）↔ migrate.py docstring 偏差登记＋三模板交付位声明 ✓；设定书 §A 八表字典 ↔ 001 DDL 逐列抽查（类型族/脏特征注记/equip_status 时间戳列缺疑点如实登记）✓；D6 坑一「按批次取最新不混用」↔ as-of 视图实现与测试 ✓；E2 册 v0.4/v0.5 报告 DTO/行为约定 3/4/8/9 ↔ 报告键集/step 链/水位/启停 ✓；teach dp1/dp2 卡签名 ↔ 实现见 F-07。

---

## 发现清单（逐条：位置＋影响评级＋建议处置）

### F-01（中——偏高）拾取复扫与管道质检的扫描面被限死在进料两表——六条启用规则结构性空跑恒绿，M-05b 复扫对其表来源问题单（含预置单）判假绿
- **位置**：worker/scheduler.py:185-194（`lake_bundle(catalog, cfg.tables)`）＋:31（`DP_PIPELINE_TABLES` 缺省 `oil_production_daily,well_info——agg 两源`）＋:227/:147（拾取与管道质检同吃此 bundle）；quality_store.py:326（报告 `"range": "生产库 8 表"` 静态串，实扫 tables 仅 2 键）。
- **影响**：`_RULE_TABLE` 20 条规则映射 8 张表，但 bundle 缺省只含 2 表——规则 6（well_overhaul）/8（equip_status）/11（sensor）/12/15（water_injection_daily）/19（monthly_settlement）按 `bundle.get(表,[])` 空跑恒绿；质检台全系统对这六条规则产不出真命中（报告 range 恒宣称「生产库 8 表」＝覆盖面主张失真）。**M-05b 复扫按单裁决**（channel.py:99-121）：对预置/历史单（如 E2 原型规则 8 设备码单）发起复扫时，拾取扫描面无 equip_status → 该规则永不进报告 hits → 判「全绿」→ 单被假绿关闭——此假绿面**超出 R2 sample 截 5 的登记范围**（R2 注记未覆盖）。另：两面貌合用一个环境变量——扩 `DP_PIPELINE_TABLES` 想补扫描面会先炸进料（scheduler.py:169 只捕 `BatchRejected`，`UnruledTableRejected` 直穿崩周期）。
- **建议处置**：拾取面改用独立表清单（复扫合同需要全 8 表或枚举湖已注册表）；报告 range 改实扫口径或随 R2 合同化批一并登记；`DP_PIPELINE_TABLES` 两面解耦。挂票归数据面（M-05b 判绿可信度缺口与 R2 同批处置或单独小票）。

### F-02（低）create_task 当日取号跨服务竞窗——数据面侧无 PK 碰撞处置，窄窗内管道周期中断
- **位置**：quality_store.py:171-182（`SELECT count(*) … LIKE 'QT-{day}-%'` +1 直插，无 IntegrityError 处理）；对边＝主仓 service.py:347-381 accept_task 同式取号但有 `except IntegrityError → 409 重试`。
- **影响**：E2 受理与数据面管道建任务同刻并发时同号撞 PK——E2 侧自愈（409），数据面侧异常直穿 run_pipeline_once 质检步（无捕获）→ 当周期进料/agg 全部跳过（下周期重试，无脏数据）。前提「worker max_instances 单飞」只封本侧并发，跨服务窄窗未封。
- **建议处置**：create_task 捕 IntegrityError 重取号一次或显式跳过当周期并记账；随数据面下次进场顺手封。

### F-03（低）报水位 data_date 取自进料原始行而非闸后净批——与「原始/清洗层＝闸后净批水位」docstring 口径有差
- **位置**：worker/scheduler.py:163-168（`data_date_of(name, bundle[name])`——bundle 为闸前原始 CSV 行）；quality_store.py:67-73 data_date_of。
- **影响**：最新业务日期行若被进料闸剔除（脏），原始/清洗层水位虚标一天（water_line 单调不回退会**锁死**在虚标值——次日真实水位低于虚标值时不再推进，T-1 判定失真放大）。边缘场景（坏行恰为该批最新日期行）。
- **建议处置**：清洗层水位改用闸后净批日期（原始层可保留 raw 口径）；或 docstring 改口径登记。开票随水位/报告合同化批。

### F-04（低）F1 幂等寻址在「同批完全同键坏行」边缘打破报告计数×物理行数对账
- **位置**：quality_store.py:238-263（append_quarantine 按寻址键 (batch_id,rule_no,action,loc,payload) 先查后插）×quality_store.py:325（`quarantined_rows = len(qrows)`——qrows 为去重前计数）。
- **影响**：同批内两条**完全同值**坏行（如 rule-3 同井同日同密度两行）产生两条同寻址键 qrows → 物理落 1 行、报告计 2——对账断言（report×物理行数）在该边缘失配；at-least-once 重执行语义不受影响（F1 本职成立）。现种子规则下 locator 均含唯一键，实达概率低。
- **建议处置**：qrows 先按寻址键去重再计数（报告=物理，一行不丢——同键同值本就同问题）；归报告合同化批（R2 实质修复批）顺带。

### F-05（低）metrics() 全表聚合不做 as-of 坍缩——旧版行双计，与 scan/schema() 时点语义不一致
- **位置**：lake_store.py:200-221（min/max/null_count 直接聚合全表所有 `_snapshot_id` 行，无 RANK 坍缩、无当前快照界定）。
- **影响**：湖内存在同键多版时 null 计数/min/max 含被覆盖旧版（双计）。现无消费方（dp8 五工具已随 DP-02 归位删除），零现行危害；未来问数/体检面复用时是静默错数源。
- **建议处置**：消费面重建前对齐 as-of 当前视图口径（同 scan 的键控坍缩），先在 docstring 登记限制。

### F-06（低）create_table 列名 f-string 直拼 DDL——CSV 表头路径的标识符未净化
- **位置**：lake_store.py:371-379（`f'"{f.name}" {_ARROW_TO_PG…}'` 直插 CREATE TABLE）；表头源头＝ingest.run_csv_load 嗅探（ingest.py:100-104）。
- **影响**：含 `"` 的列名可逃逸标识符引用（DDL 注入面）。现规范 8 表以迁移 001 为真源、create_table 仅测试触达（worker 管道不调），实际暴露面小。
- **建议处置**：标识符白名单（`^[A-Za-z_][A-Za-z0-9_]*$`）或 `psycopg.sql.Identifier` 组装；随湖面下次触碰批顺手收口。

### F-07（低）specs/modules.md 卡面签名与实现漂移无注记——dp1/dp2/dp3 三卡落后于 DP-03/05/06 改形
- **位置**：specs/modules.md:26（dp1 `load_catalog(backend: Literal["jdbc","rest","federated"], **cfg)`——backend 形参已随拍板 3 删除，实落 lake_store.py:560-563）；:46（dp2 `run_batch_load` 五参——实落增 source/batch_id 透传＋run_csv_load 新增，ingest.py:87-106）；:59-60（dp3 `validate_batch→QualityReport`／`validate_bundle`——实落 GateVerdict／evaluate_bundle，transform.py:147/463，DP-05 改形）。
- **影响**：卡面自称「签名逐字保留」、DP-04 有同款退役注记而 DP-03/05/06 改形未随卡——阶段收官「卡/实现对照」文档面失真（check_specs 不校验签名，闸不红）；新读者按卡面找 QualityReport 会扑空。
- **建议处置**：阶段收官对齐批给三卡补 DP-03/05 改形注记（同 DP-04 注记款）；或卡面加「以实现 docstring 为准」指针。

### F-08（低）teach 99 册 §2.12 agg 行「技术自选登记」值与主仓 0014 实落 DDL 不一致——跨仓裁决项
- **位置**：teach-petro-agent specs/api/99-数据库与连接层设计.md:309（F3 登记于 commit 3e7d6fc，2026-10-05 02:32——「事实 numeric 精度＝Numeric(12,2)/维度名称列＝varchar(64)」）↔ 主仓 migrations/versions/20261004_0014_agg_star_model.py:50-95（ce47e84，02:02——liquid_output NUMERIC(10,2)、oil_pressure NUMERIC(6,2)、block_name VARCHAR(16)、field_name VARCHAR(32)）。
- **影响**：合同登记的 DP-04 技术自选值与 30 分钟前落库的实产 DDL 两处对不上（登记在后却与实现不符）；数据面 agg 直写不受影响（PG 数值域可容、列名/键全一致），但「以册为准回改」纪律下这是未裁决漂移——须一方回改（改 0014 走迁移、或改册登记）。
- **建议处置**：交 Owner 裁决方向后，一侧回改并两仓留痕（本审查不代改）。数据面侧零动作。

### F-09（信息）serve/api.py 410 注记计数不一致——「六端点」实落五路由
- **位置**：serve/api.py:176（注记「六端点恒 410 Gone」）；实落 410 路由＝tables/describe/query/replay/lineage 共 **5** 条（:187-209；/healthz 非 410）；DP-02 commit 消息同句并存「六端点」与「curl 五问答路由全 410」两种口径。
- **影响**：纯文档计数出入，行为无差。
- **建议处置**：注记改「五端点」或说明 /healthz 另计；顺手项。

### F-10（信息）begin_caller 声明制写方身份——同实例身份可迁移、无验证（既有教义登记面）
- **位置**：lake_store.py:310/360-362（`self._caller` 实例态，调用方自报家门）。
- **影响**：持同一 catalog 实例的代码可携他人身份过白名单（「身份自报家门如实交底」为 DP-W-D1-4 既有取舍，单进程单写者前提下成立）；多租户/多写方加固属后续批。
- **建议处置**：维持登记；湖面多写方批进场时改传参式身份。

### F-11（信息）docs/prd.md/architecture-v1.md 湖底座旧表述（PyIceberg+JDBC catalog）未随拍板 3 更新
- **位置**：docs/prd.md:25（G1）/49（技术栈）/163（部署形态）；docs/architecture-v1.md:8/15/27——均为拍板 3 前文本，未加退役/注记。
- **影响**：文档考古面失真（活性面无涉——湖真身、specs、ADR 已按拍板 3 表述）；新读者从 PRD 进入会拿到已废选型。
- **建议处置**：随文档对齐批补一行拍板 3 注记（同 prd.md:145 对 marts 的处理款）。

### F-12（信息）dev 环境残留与测试卫生三则（非本批产物，登记备查）
- **位置/内容**：①dev 库 `data_plane.audit_record` 残 1 行（audit_id=q-1，2026-09-28——早期探针/部署验证残留，非 DP-01~06 产物；DP-06「dev 库零残留」申报限 quality_task/quarantine/water_line，经复核该三表确为 0）；②MinIO `tpa-raw` 桶残 2 对象（b-* 批——早前干跑孤儿对象，down/清场不触桶的既知语义）；③`tpa-raw-test` 残 dp4-agg-e2e 两对象——tests/pg/test_agg_star 清场只清 DB 行不清测试桶对象（test_ingest_real 有清桶先例可对齐）；④tests/dp2/test_ingest_real.py:101 `scan(pred="_batch_id == …")` 探针依赖「表内无更新批数据」——同键后续批落库后该断言会翻红（as-of 坍缩后过滤的正确语义下，批间隔离脆弱＝测试面卫生项）。
- **建议处置**：①部署侧清一次 dev 库探针行；②③test_agg_star 补桶清场（对齐 test_ingest_real wired 先例）；④探针改独立表名/独立 schema。均小票顺带。

---

## 测试与闸复跑汇总（独立取证）

1. hermetic：`env -u TEST_DATABASE_URL … ./ci.sh`（python3.14）→ spec gate PASS 0 警告＋**113 passed / 6 skipped**（6 skip＝boto3/psycopg importorskip 模块级，hermetic 成立）✅
2. PG16+MinIO（主仓 compose@5433/9000，测试桶 tpa-raw-test）：**168 passed / 0 skipped**（30.56s）✅——与 DP-06.fix 申报双基线逐字一致
3. 迁移账本态：schema_migrations 恰 1 行（001）；up/down 幂等机判（往返＋湖先 boot）复跑通过 ✅
4. 三账号模板闭世界：midplatform 8 表恰集／quality_writer 恰 7 句／agg_writer 恰三表——机判＋实装负测试全绿 ✅
5. dev 库残留：quality_task/quarantine_row/water_line/lake_snapshot/raw/freshness/agg 全 0（audit_record 残 1 旧探针行→F-12）✅
6. 主仓消费面对账：M-05b 冻结字面（八键/五键/step 链/hit_identity 白名单）与数据面实现逐字段比对零偏差（主仓测试未复跑——零接触红线，以 data-plane 侧 168 全绿交叉印证）

## 零修复动作声明

本次审查全程只读：data-plane 仓代码/配置/迁移/数据**零写入、零修复、零提交**（工作树保持干净，HEAD 未动）；主仓零接触（源码/迁移/测试仅只读对照，未复跑主仓测试）；dev 库取证全部经只读 psql/docker exec；MinIO 仅桶清单元数据只读、零对象读写删（测试复跑走 tpa-raw-test 临时桶）；测试与闸为复跑非修改；唯一落盘物＝本回报文件（任务指定产物）。发现清单 F-01～F-12 全部留给后续票/Owner 裁决处置，未做任何预防性修补。

---

## rev 处置行（DP-07 修复票追加——全量审查批 1，Owner 授权修复再接线，2026-10-05）

data-plane 仓修复拍单提交 **6fceeb9**（父=7d109b3，DP 系 rev-list 41→42）。逐条处置：

- **F-01（中高）扫描面解耦 → 已修复**（DP-07 修复拍）：拾取复扫与管道质检扫描面独立清单 `DP_SCAN_TABLES`（缺省＝001 全部受检 8 表＝quality_store 新公开 `SCAN_TABLES` 同域，worker 字面保零顶层 app 依赖＋钉子测试看守），进料面 `DP_PIPELINE_TABLES` 原 agg 两源语义不动——规则 6/8/11/12/15/19 不再结构性空跑恒绿，M-05b 复扫对其表来源问题单（含预置单）假绿面封死；报告 range 改按实扫表数动态生成（`f"生产库 {n} 表"`）；扩进料表清单不再 `UnruledTableRejected` 崩周期（逐表捕获诚实跳过记 `summary.unruled_skipped`，闸 fail-closed 不入湖语义不变）。机判：hermetic `TestScanSurface`（湖 8 表六规则真跑命中＋range 串断言＋worker/quality 同域钉子）＋`test_scheduler`（run_dir8 管道质检八键报告＋扩表不崩＋`DP_SCAN_TABLES` 环境缺省/覆盖）。
- **F-02（低）create_task 取号竞窗 → 已修复**（同提交）：`IntegrityError` 单次重试自愈（重读当日计数取下一号，序号连续无空洞——主仓 M-05b accept_task 处置先例同款）；两撞仍败如实上抛（沿拾取执行中断通道行停 step=1 自愈重拾）。机判：pg `TestTaskNumberRace`（竞窗注入光标模拟他服务计数后抢注——UniqueViolation 红先→重试自愈不崩且 -01/-02 连续）。
- **F-03（低）报水位虚标 → 已修复**（同提交）：`Ingest` 新公开 `landed`（表→最近一次成功落位行＝质检通过后实落内容），worker 报水位 data_date 改消费**闸后净批**（不取闸前原始行）；脏批（BatchRejected）不入水位语义原样。机判：`TestWaterLineNetBatch`（落位批裁剪形——被剔最新日期不入水位；＋脏批无水位主张钉）。
- **F-04（低）同批同键坏行对账 → 已修复**（同提交）：`run_quality_task` 隔离行先按寻址键 (batch_id, rule_no, action, loc, payload) 去重再落库计数——完全同值 twin 坏行只计一，**报告=物理**；异键真坏行不吞（append-only 不变）。机判：hermetic 同键 twin 两测＋dp3 twin 计数 3→2＋pg `TestSameKeyQuarantineCount`（物理 1＝报告摘要 1＝报告 jsonb 1）。
- **F-05～F-12 → 未动**（非本票范围：F-05/F-06 挂湖面下次触碰批；F-07 挂阶段收官对齐批；F-08 交 Owner 裁决；F-09/F-10/F-11 顺手项/既有登记面；F-12 测试卫生小票）。
- **复跑证据**：hermetic ci.sh spec gate PASS（0 警告）＋**122 passed 6 skipped**（基线 113+6）；PG16+MinIO（主仓 compose，测试桶 tpa-raw-test）**179 passed 0 skipped**（基线 168）；主仓 M-05b 替身行形断言只读复跑 **14 passed 零偏差**；dev 库残留 quality_task/quarantine_row/water_line 复核全 0；零共享库交叉 grep 零匹配。
