# DEP-01 开发拍 回报 —— 部署准备批五件收口（runbook／0018 迁移补建／口令注入验证／原型保护闸／MinIO 清理策略）

> 执行依据：`dispatch/pending/DEP-01.md` 原样执行；先读物已读（DP-04.dev.md〔0016 全新库
> 实跑与 gateway 断链发现〕、DP-05/DP-06 交付、W-LAND.dev.md＋W-LAND.rev.md〔冒烟 7 例
> 与 rev F5 常驻化建议〕、P0-06 CI 前端 job 现状（`.github/workflows/ci.yml`）、
> `app/domains/gateway/store.py`（gateway 表 ORM 真源）、`config/database.yaml`＋
> `tests/infra/test_config.py`、P2-04.fix/close（0011 断链挂账原文））。
> 作业方式：**git worktree 隔离**——主树携 Owner 私产与并行窗口作业（作业期间主树由
> master f5e1677 切至 fix/s-01-sem-ledger-seed、journal 推进 d8dbc37、并出现 S-01 未跟踪
> 迁移件——全程零触碰），主仓作业在 `.scratch/dep-01`（分支 `fix/dep-01-deploy-prep`，
> 基线=f5e1677），data-plane 嵌套仓直改（其工作树仅既有未跟踪 uv.lock 一项原样未动）。
> 验后 worktree 已 remove（分支与提交保留）；Owner 私产零收编；**禁 `git add -A/.` 已守**
> （主仓显式路径 add 九文件，data-plane 显式路径 add 两文件）。

## 产物

### 提交（两仓各一）

| 仓 | 分支 | 提交 | 父 | 规模 |
|---|---|---|---|---|
| 主仓 | `fix/dep-01-deploy-prep` | **`2b03fc0`**（全 SHA `2b03fc0c6ba06057314ddfb948ab42bd9a5a1c0e`） | `f5e1677`（开工时 master 头） | 9 files, +717/−2 |
| data-plane | `main` | **`6a38f56`**（全 SHA `6a38f5613b4673610a046fe23c4e22e3ece1eed4`） | `6fceeb9`（DP-07 修复拍） | 2 files, +238 |

主仓 `app/` 一行未动（九文件清单可证：无 app/ 路径）。

### 票面五件 → 落点

| 票面项 | 文件 | 说明 |
|---|---|---|
| ① 三账号建号 runbook | `docs/deploy/db-accounts-runbook.md`（新建） | 三账号（midplatform 只读／tpa_agg_writer 限写三表／tpa_quality_writer 限写＋rule 只读）生产建号四步流程（模板位置 data-plane `migrations/*.sql`／占位符替换 `<SET_ME>`·`${AGG_WRITER_PASSWORD}`·`${QUALITY_WRITER_PASSWORD}`／口令密管注入／执行实例逐账号点名）；**GRANT 验证三分法**（①正向 has_table_privilege／真操作冒烟 ②负向 InsufficientPrivilege 机判——data-plane `tests/pg/` 限写账号测试同款 ③闭世界对账 `information_schema.role_table_grants`＝8 表 SELECT／恰 6 句／恰 7 句展开面）；**环境变量清单表**（DATABASE_URL／AGG_DATABASE_URL／QUALITY_DATABASE_URL／MIDPLATFORM_PG_* 五件／MINIO_* 三件＋PG_* 补充行——每变量用途/示例/缺省行为）；**dev 容器已执行授权动作与生产差异表**（dev 仅 midplatform 已建〔dev 库 pg_roles 实查在位〕且为演示口令、数据面 dev 期直连 petro、模板 GRANT 仅测试内实装验证后清场；生产＝三账号全建＋密管口令＋账号级限写双层＋迁移链先行） |
| ② gateway 表迁移补建 | `migrations/versions/20261005_0018_gateway_tables.py`（新建）＋`20261002_0011_gateway_caller_trgm.py`（链位一行，见偏差 1） | gateway 三表入版本轴——**P2-04.fix 偏差 2／P2-04.close 挂账（0011 断链）收口，0011 docstring 双轨前提的收敛**。表结构逐列照 `app/domains/gateway/store.py` ORM 声明（SpendRecord 17 列／DrillRun 9 列＋ck_drill_status CHECK／BudgetConfigRow 5 列；无 server default——ORM default 均 Python 侧，DDL 与 ensure 直建完全同形）；表/列 COMMENT 全带 99 §2.13 锚；upgrade 全 IF NOT EXISTS（ensure 先建库再跑零冲突）；downgrade drop 三基索引＋三表（trgm 两索引与 pg_trgm 扩展归 0011）；迁移头注登记来源与链位裁决 |
| ③ 口令注入机制验证＋登记 | `tests/infra/test_config.py`（补 1 测）＋runbook §3 | `${VAR:-默认}` 机制两半边机判：PG_HOST/PG_PASSWORD/MIDPLATFORM_PG_HOST 环境量在位覆盖 yaml 默认＋delenv 后回落 yaml 开发默认（`.env` 兜底源在测内隔离）；runbook「口令纪律：生产口令经环境注入，禁止默认口令上生产」节（机制／禁默认口令清单〔petro/petro、midplatform/midplatform、petro12345〕／凭证不进 git 不入日志／负向关即口令面验证钩子） |
| ④ 原型树保护闸＋冒烟常驻＋CI | `tools/prototype_guard.py`（新建）＋`web/prototype-manifest.json`（本票生成首版）＋`web/src/landing/dual-tree-smoke.test.jsx`（新建，7 例常驻）＋`.github/workflows/ci.yml`（frontend job 增 guard 步骤）＋`tests/tools/test_prototype_guard.py`（新建，闸看守 pytest 面——照 contract_coverage/debt_markers 先例） | 闸＝四同步页（pages/E2·A2·B4＋api/e2.js）SHA-256 × 清单比对，漂移/缺失退出码 1 并逐条点名；check/update 双模式（update＝合法原型同步批重生清单随票提交）；首版清单生成前经 blob-hash 对照 **3c2d63a/04f9606 同步点逐字等证**（E2/e2.js/B4=3c2d63a、A2=04f9606，四 hash 与 W-LAND.rev 三节表逐一相符）；**误报面（T1 审查点）**：闸只盯清单内四文件——落地树接线/页面迭代（landing/、api 真客户端、flows/、CI、后端）零触碰清单路径不误红；合法原型同步批属预期漂移走 update 随票提交（脚本 docstring＋RED 输出处置语双登记）。冒烟 7 例常驻化＝W-LAND 临时冒烟升格（W-LAND.rev F5 收口）：①registry LANDING_LIT 九键 ②落地 E2 /api/quality/{rules,tasks,issues,freshness} 四拉取实发＋规则行渲染＋X-Dev-User=aqiang 桩 ③落地 A2 /api/wells 四端点实发＋「渤中28-1-N2」 ④落地 B4 /api/wiki/pages 空态验收文案 ⑤原型 E2 规则种子＋问题单 p7 流转入「复核」后「复扫」按钮在位 ⑥原型 A2 内嵌 WELLS 种子 ⑦原型 B4 目录种子——⑤⑥⑦ stub fetch **断言零调用**（原型树自包含）；CI 接线照 P0-06 前端 job 现状（checkout 后 install 前先跑 `python3 tools/prototype_guard.py check`，`working-directory: .` 覆盖 job 默认） |
| ⑤ MinIO 清理策略（data-plane 仓） | `worker/gc.py`（新建）＋`tests/worker/test_gc.py`（新建，8 测）＋runbook §4 | `gc_orphans`：孤儿＝桶内对象键不在 `data_plane.lake_snapshot.data_object_key` 引用集（湖写序「先留桶后落账」PG 失败遗留／expire 清账遗留）；超期＝LastModified 早于 now−retention_days（`DP_GC_RETENTION_DAYS` 缺省 90＝runbook 保留期建议值）；**仅日志＋返回清单（[{key,last_modified,age_days}] 最老在前），零删除调用面**（替身 delete_object 即 raise 机证）；分页 list_objects_v2 走完；**默认不注册作业**——`build_scheduler` 管道＋拾取配齐仍无 gc 键（机判），人工入口 `python -m worker.gc` 单次清点退出；真删除策略与开关归 Owner 部署批（仓内现状零删除实现）。策略文档＝runbook §4（保留期建议隔离/拒收批 ≥90 天、先列后删两步制、有主永不清红线） |

## 闸门实跑

### ① 0018 alembic 双向实跑（最终提交文件，主仓 worktree；scratch 库验后即删）

**全新库全链 upgrade head（dep01_fresh，18 步全过——含修复前必断链的段）：**

```
$ docker exec petro-agent-platform-pg-1 psql -U petro -d postgres -c "CREATE DATABASE dep01_fresh;"
$ PG_DB=dep01_fresh uv run alembic upgrade head
INFO ... Running upgrade  -> 0001, infra 基线（空迁移）...
INFO ... Running upgrade 0001 -> 0002, sem 域基线...
INFO ... Running upgrade 0002 -> 0003, kb 域基线...
INFO ... Running upgrade 0003 -> 0004, wiki_baseline
INFO ... Running upgrade 0004 -> 0005, kb_issue_report
INFO ... Running upgrade 0005 -> 0006, graph_extract_config
INFO ... Running upgrade 0006 -> 0007, faq 域基线...
INFO ... Running upgrade 0007 -> 0008, retrieval 域基线...
INFO ... Running upgrade 0008 -> 0009, chat 域基线...
INFO ... Running upgrade 0009 -> 0010, kb 关键词路倒排索引...
INFO ... Running upgrade 0010 -> 0018, gateway 表族迁移补建（DEP-01 部署准备批）——网关三表入版本轴。  ★断链修复段
INFO ... Running upgrade 0018 -> 0011, gateway 账本 caller 归因列＋spend-logs keyword pg_trgm 索引...
INFO ... Running upgrade 0011 -> 0012 ... 0015 -> 0017（kb/chat/faq/agg/quality/well_status_log 全链）
$ PG_DB=dep01_fresh uv run alembic current   → 0017 (head)
```

**表结构一致性（fresh=迁移建 vs dev=ensure 建）：**

```
information_schema.columns（三表全列 name/type/len/nullable/precision/scale 逐列串接）diff
  → 列形全同
pg_indexes：gateway_budget_config_pkey / gateway_drill_run_pkey / gateway_spend_record_pkey
  / ix_gateway_spend_id_trgm / ix_gateway_spend_model_time / ix_gateway_spend_note_trgm
  / ix_gateway_spend_run / ix_gateway_spend_time_desc   （8 索引全在位）
pg_constraint：ck_drill_status（CHECK status IN ('running','done')）在位
col_description 抽查：单例行主键（恒 'singleton'）
```

**downgrade 逐步干净＋复原：**

```
$ PG_DB=dep01_fresh uv run alembic downgrade 0010
INFO ... Running downgrade 0017 -> 0015 ... 0012 -> 0011
INFO ... Running downgrade 0011 -> 0018, gateway 账本 caller 归因列...（trgm 两索引＋caller 列撤）
INFO ... Running downgrade 0018 -> 0010, gateway 表族迁移补建...（三基索引＋三表删净）
$ psql to_regclass 三表 → 全空（|||）                              ★穿越段回滚干净
$ PG_DB=dep01_fresh uv run alembic downgrade base   → 10 步全降（Running downgrade ×10）
$ psql information_schema.tables WHERE table_schema='public' → 1（仅 alembic_version）
$ PG_DB=dep01_fresh uv run alembic upgrade head → 复原；current → 0017 (head)
```

**既有库幂等（ensure 与迁移并存现状不破坏——ensure 先建再跑全链）：**

```
$ uv run python（ensure_gateway_tables 对 dep01_ensure 建三表＋trgm 索引）→ ensure 完成
$ PG_DB=dep01_ensure uv run alembic upgrade head
INFO ... Running upgrade 0010 -> 0018, gateway 表族迁移补建...   ← IF NOT EXISTS 全跳过零改写
INFO ... Running upgrade 0018 -> 0011, ...                        ← 同上
$ PG_DB=dep01_ensure uv run alembic current → 0017 (head)；gateway_spend_record 列数=17（原样）
```

**dev 真实既有库（petro@0017）零破坏：** `alembic heads` → 0017 单头；`upgrade head` → 无操作；
`gateway_spend_record` count=0 原样（dev 库无业务行，零触碰）。两个 scratch 库验后 DROP。

### ② 原型闸 GREEN→RED→GREEN 演示（worktree 内，B4 篡改）

```
$ python3 tools/prototype_guard.py update     # 首版清单生成（sha256 与 git hash-object 四文件
  22d55acde0babd32…  web/src/api/e2.js  ← 同步点 3c2d63a       #   对照 W-LAND 同步点 blob 全符）
  4d74f7eb89116377…  web/src/pages/A2.jsx  ← 同步点 04f9606
  848e770f1987f804…  web/src/pages/B4.jsx  ← 同步点 3c2d63a
  2702c039f6e45da9…  web/src/pages/E2.jsx  ← 同步点 3c2d63a
$ python3 tools/prototype_guard.py check
原型闸 GREEN：原型树 4 个关键文件与清单一致（同步点 ['04f9606', '3c2d63a']）。   [rc=0]
$ printf '\n{/* 篡改演示 */}\n' >> web/src/pages/B4.jsx
$ python3 tools/prototype_guard.py check
原型闸 RED：内容漂移——web/src/pages/B4.jsx                                     [rc=1]
处置：原型树禁改（AGENTS.md 硬纪律 0）——还原改动；如属合法原型同步批，
随批 `python3 tools/prototype_guard.py update` 重生成清单并同票提交。
$ cp /tmp/dep01_B4.bak web/src/pages/B4.jsx   # 复原（git diff --stat 该文件＝空）
$ python3 tools/prototype_guard.py check
原型闸 GREEN：原型树 4 个关键文件与清单一致（同步点 ['04f9606', '3c2d63a']）。   [rc=0]
```

### ③ 主仓全量闸（worktree 提交后复跑）

```
$ uv run ruff check app tests migrations tools        → All checks passed!
$ uv run mypy app                                     → Success: no issues found in 76 source files
$ uv run lint-imports                                 → Contracts: 5 kept, 0 broken.
$ uv run python tools/contract_coverage.py check      → 合同覆盖率闸绿：169 条合同端点双向对账通过。
$ uv run python tools/debt_markers.py check           → 债务标记闸绿：web 源码债务短语全部携可解析 DEBT 标签（盘点 33 条见 report）。
$ uv run pytest -q                                    → 881 passed, 77 skipped, 1 warning in 24.97s
$ python3 tools/prototype_guard.py check              → 原型闸 GREEN（提交树复跑）[rc=0]
```

**基线对照（增量全归本票）**：master 树同命令 `pytest -q` → **876 passed, 77 skipped**
——worktree 恰 **+5 passed**（本票新测试：原型闸看守 4＋config 注入 1），**skipped 持平**
（77=77，skip 面漂移为 master 既有，与本票无关）。

### ④ web 三连（worktree 提交后）

```
$ npx eslint .     → ✖ 2 problems (0 errors, 2 warnings)   ← 两条均存量（pages/D3.jsx:96 /
                    pages/INDEX.jsx:85 react-hooks/exhaustive-deps）；本票文件零告警
$ npx vitest run   → Test Files  18 passed (18) / Tests  279 passed (279)
$ npx vite build   → ✓ built in 3.96s；dist/assets *.test.* chunk = 0；
                     E2/A2/B4 落地×原型双 chunk 三对在位
```

**基线对照**：master web `vitest run` → **272 passed**——worktree 恰 **+7**（双树冒烟常驻 7 例）。

### ⑤ data-plane 闸（提交 6a38f56 内容，提交前后各跑一遍同数）

```
$ bash ci.sh                                          → spec gate: PASS（0 警告）
                                                        130 passed, 6 skipped in 0.56s / TESTS PASS / CI PASS
$ TEST_DATABASE_URL=postgresql://petro:petro@localhost:5433/petro \
  .venv/bin/python -m pytest -q                       → 187 passed in 32.73s   （0 skipped 全实跑）
```

**基线对照**：DP-07 基线 hermetic 122+6／PG 179——恰 **+8**＝本票 `tests/worker/test_gc.py` 8 测。
含 gc 测试单跑 `pytest tests/worker/test_gc.py -q` → 8 passed。

## 偏差

1. **0018 链位＝0010 与 0011 之间（0011 down_revision 同批改指 0018，一行＋头注一段）**：
   现象→票面点名文件 `0018_gateway_tables.py`，若按文件名序挂尾（down_revision=0017），
   纯 Alembic 供应的全新库仍断链于 0011（`ALTER TABLE gateway_spend_record`／trgm 索引落在
   ensure-only 表上——P2-04.fix 偏差 2 实证病灶），票面验收「全新库全链 0001→0018 upgrade
   head 成功」不可达。处置→0018 插入 0010 之后、0011 之前（0011 的 down_revision
   `"0010"`→`"0018"` 一行机械改＋头注登记），链保持单头线性（0010→0018→0011→…→0017）；
   **Alembic 按链不按文件名序**（现链 0013→0016→0014→0015→0017 先例、DP-04 偏差 1 同款
   备案），文件名沿用票面点名 0018。若 L0 判须回退链位，改 0018/0011 两行 down_revision 即可
   （但全新库断链随之复发，挂账重新悬置）。
2. **开工期间 master 推进一提交（d8dbc37，仅 dispatch/journal.jsonl）＋主树检出切至
   fix/s-01-sem-ledger-seed**：并行窗口/执行台动作，与本票九文件零交叠；本票分支基线仍
   f5e1677，合并时非 FF 但零冲突面（journal 与本票文件无交集）。全程经 worktree 隔离，
   主树任意切换/推进零影响本票作业与验证。
3. **TDD 红先的如实登记**：本票新面为工具闸/策略验证型（原型闸、gc、config 注入测试），
   测试与实现同批落地，未按红→绿节奏实跑留红；commit 信息中「红先证据＝ImportError 形态」
   为形态登记非实跑留痕。开发过程中两处真实红：①0018 COMMENT 嵌套单引号语法错（全新库
   首跑即炸，修复转义后全链过——红在真实验收面非测试面）；②看守测试 test_update_regen
   两轮构造缺陷红（monkeypatch 空设置污染恢复链／清单按新内容算致起点即绿）——均测试
   自身 bug，修复后绿，实现零返工。
4. **runbook 单文件承载票面三处「runbook」**：件①点名 `docs/deploy/db-accounts-runbook.md`，
   件③「runbook 增口令节」与件⑤「策略文档入 runbook」未另点名文件——按票面语义三节并入
   件①同一文件（§3 口令纪律／§4 MinIO 清理策略），未新建第二 runbook。
5. **`tests/tools/test_prototype_guard.py` 票面未点名**：票面件④只要求脚本＋manifest＋演示；
   仓内 tests/tools/ 已有 contract_coverage/debt_markers 两闸的 pytest 看守先例（闸进
   pytest 门禁）——照惯例补四面看守测试（清单形状/当前仓实判绿/红绿注入/update 复绿；
   注入全程临时根，零触真实原型树）。若 L0 判越界，删该文件不影响其余四件。

## 疑点（待 L0 裁决，不动手）

1. **【高优先·合并前必办】0018 撞号：S-01 并行票同占 0018 号段**——本票收工时主树出现
   未跟踪件 `migrations/versions/20261005_0018_sem_ledger_seed.py`（S-01，pending/ 在票），
   其 `revision="0018"`、`down_revision="0017"`，与本票 `0018_gateway_tables.py`
   （revision="0018"，down_revision="0010"）**revision ID 重复**——两件并存 Alembic 装载即报
   重复 revision 错。处置建议：后合并的一票改号 0019（若 S-01 后合：其文件改名 0019 且
   down_revision 维持 0017 即可——本票 0018 在链中段，与 0017→0019 拼链无冲突；若本票后合
   则需重排本票链位，代价见偏差 1）。两票链位声明已只读取证如上，改号动作归 L0/执行台。
2. **agg_writer.sql 的 clean 层只读段在生产拓扑下的归属**：模板按 dev 同实例拓扑写就
   （agg 与 clean 同库不同 schema）；生产若按 ADR-0003 裁决 2 拆独立中台实例，该段 GRANT
   落哪个实例需部署批核对（runbook §1.2 已登记为核对点，未改模板——模板改动归 data-plane 票）。
3. **MinIO 保留期 90 天为建议值非裁决值**：票面给「≥90 天建议」，`DP_GC_RETENTION_DAYS`
   缺省按 90 落；真删除策略、删除开关、删除执行体（现仓零删除实现）全部归 Owner 部署批拍板
   （票面原文，本票未越）。
4. **原型闸清单扩面节奏**：首版清单恰＝W-LAND 四同步页（blob-hash 等证的最小闭集）；pages/
   下其余原型页（A1/D1/B1/B2/B3/B5 等未回改页）未入清单——后续原型同步批若扩面，改脚本
   `_TRACKED` 后 `update` 即可（机制已留）；是否首版即扩到全 pages/ 归 L0。
5. **中台库生产实例连接串归集**：runbook §2 表中 DATABASE_URL 示例指向独立中台实例
   （ADR-0003 拍板 2），DP-04 疑点 3「dev 同实例/生产独立实例」持续挂——生产部署批拼装
   环境变量清单时与该疑点一并对账。

## 回报落点确认

本文件路径＝`/Users/divh/Downloads/petro-agent-platform/dispatch/results/DEP-01.dev.md`
（派工指令中 `/Users/dispatches/...` 为误写，已按仓内真路径落盘；文件未入提交——两仓
「各一提交」纪律下回报由执行台归档，W-LAND/DP 系先例同款）。
