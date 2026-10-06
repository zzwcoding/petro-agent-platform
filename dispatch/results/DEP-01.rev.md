# DEP-01 审查拍 回报（T1 关票前独立审查）：主仓 2b03fc0＋data-plane 6a38f56 双仓六节审查

- **被审对象**：主仓分支 `fix/dep-01-deploy-prep` 单 commit **`2b03fc0`**（全 SHA 2b03fc0c6ba06057314ddfb948ab42bd9a5a1c0e，父＝f5e1677，9 文件 +717/−2，`git show --stat` 逐文件核实：0018 迁移 +165／0011 链位改 9 行(−2)／runbook +143／prototype_guard.py +115／manifest +16／闸看守测试 +86／config 测试 +29／冒烟常驻 +153／ci.yml +3——**无 app/ 路径**）；data-plane `main` 顶端 **`6a38f56`**（全 SHA 6a38f5613b4673610a046fe23c4e22e3ece1eed4，父＝6fceeb9，恰 2 文件 +238：worker/gc.py 105＋tests/worker/test_gc.py 133——`git show --stat` 核实零夹带）。
- **环境修正兑现**：master 已前进至 5123d74（含 S-01 改号件 0019_sem_ledger_seed，down_revision="0017" 实读）。审查按**合并后形态**推演：`git archive master` 提取提交树至 /tmp，`git diff 2b03fc0^ 2b03fc0` 补丁 `git apply` **零冲突**应用——提取树即合并后形态（0010→0018→0011→…→0017→0019）。
- **作业方式**：全程只读＋独立复跑。被审树内容一律 `git show 2b03fc0:<path>`／`git archive` 取证；主仓**零 checkout／零 switch／零 stage**；alembic 双向用 docker 容器 petro-agent-platform-pg-1 内临时库（dep01_rev_fresh／ensure／dp／base 四库，**用毕全 DROP**，收工 `pg_database` 复核 0）；原型闸篡改演示全部在提取树内（真仓原型树零触碰）；data-plane `git clone` 至 /tmp/dp-rev 复跑（嵌套仓零写入）。
- **独立复跑数字（本审查实测原文，非转抄 dev）**：

| 闸 | 实测 | dev 回报 | 判 |
|---|---|---|---|
| 主仓 pytest（合并形态提取树） | **881 passed, 83 skipped** | 881/77 | passed 同；skip 差=master 新增 S-01 PG 门控 6 测跳过（见下基线行） |
| 主仓 pytest 基线（纯 master 提取树） | **876 passed, 83 skipped** | 876/77 | **恰 +5 passed**＝本票新测试（闸看守 4＋config 注入 1），skip 持平归因成立 |
| ruff／mypy／lint-imports | All passed／76 files 0 issues／5 kept 0 broken | 同 | 逐字符 |
| contract_coverage／debt_markers | 169 条绿／33 条盘点绿 | 169/33 | 逐字符 |
| 原型闸 CLI check | **GREEN rc=0**（4 文件与清单一致） | GREEN | 符 |
| config＋闸看守测试单列 | 16 passed | （含于 881） | 符 |
| web vitest run | **279 passed**（基线 272 恰 +7＝冒烟 7 例） | 279（基线 272） | 逐字符 |
| 冒烟单列 dual-tree-smoke | 7 passed | 7 | 符 |
| web eslint | 0 error, 2 warning（存量 D3.jsx:96／INDEX.jsx:85） | 同 | 符 |
| **alembic 全新库 upgrade head**（dep01_rev_fresh） | **19 步全过**，链序 0001→…→0010→**0018**→0011→…→0017→**0019**；current=heads=**0019 单头** | 18 步至 0017 | 合并后形态多 0019 尾段，单头成立 |
| alembic downgrade 0010→base→head 复原 | 穿越段 0011→0018→0010 过、三表删净、base 后 public 仅剩 alembic_version（count=1）、复原到 0019 | 同款 | 符 |
| alembic 幂等（dep01_rev_ensure：ensure 先建→全链迁移） | 0018/0011 两腿 IF NOT EXISTS 跳过过、current=0019、**两库 gateway 31 列 information_schema 逐列 diff＝空** | 列形全同 | 符（实测更强：31 行全列串接 diff 空并留存） |
| **断链反证**（dep01_rev_base＝纯 master 无补丁） | upgrade head 于 **0010→0011 炸 `UndefinedTableError: relation "gateway_spend_record" does not exist`** | （dev 未做反证） | **断链缺陷实锤，0018 链位手术即修复** |
| data-plane `bash ci.sh`（hermetic，/tmp 克隆） | spec gate PASS＋**130 passed, 57 skipped**＋TESTS PASS＋CI PASS | 130 passed, **6** skipped | passed 同；**skip 数 57≠6**——见发现 F1 |
| data-plane test_gc.py 单列 | **8 passed** | 8 passed | 符 |
| data-plane PG 全量（TEST_DATABASE_URL 指**临时库** dep01_rev_dp＋先施主仓全链迁移） | **181 passed, 6 failed**（6 失败全在两 TestRestrictedWriterAccount 类，归因见 F2/F3） | 187 passed 0 skipped（指 dev petro 库） | 181+6=187 集合一致；失败全部归因**既有测试基建 wart**（非本票产物） |
| data-plane 两受限类复跑（指 dev petro 库，归因闭环） | 9 例 8 过 1 挂（唯 F3 状态依赖例）；`pg_roles tpa_%`=0、QT-probe-01/quarantine/water_line 探针残留**全 0**——dev 库零残留 | 187/0 | dev 数字在其环境可复现 |

---

## 一、diff 双仓嗅探

### 结论：〔通过——主仓 9 文件零夹带、app/ 零触碰复核属实；data-plane 2 文件零夹带、scheduler 零 gc 引用〕

1. 〔通过〕**主仓逐块定性**（票面件①~⑤一一对应）：件②＝0018 迁移 +165 新建＋**0011 链位一行手术**（`down_revision: "0010"→"0018"`＋头注一段登记，diff 逐行核实恰此一处语义改动）；件①＝runbook +143；件③＝config 测试 +29；件④＝guard +115＋manifest +16＋看守测试 +86；件④冒烟常驻＝dual-tree-smoke.test.jsx +153；件④CI＝ci.yml frontend job +3（guard 步）。文件清单无 app/、无 dispatch/、无 tickets/、无 eval/ 路径——**业务域零触碰、Owner 私产零收编**复核属实。
2. 〔通过〕**CI 步位置正确**：guard 步在 checkout 后、`npm ci` 前；`working-directory: .` 覆盖 frontend job 默认 `web`（ci.yml job defaults 实读）；脚本纯标准库（hashlib/json/argparse/pathlib）——CI ubuntu python3 零依赖可跑成立。
3. 〔通过〕**data-plane 零夹带**：恰 worker/gc.py＋tests/worker/test_gc.py 两文件；`grep gc data-plane/worker/scheduler.py`＝**零匹配**（「默认不注册作业」的静态机证——不是「注册了但关掉」，是装配面根本不存在 gc 键）；模块零顶层 app 依赖（import 只在 main() 内，worker 纪律同 scheduler）。

## 二、0018 vs ORM 逐列对照（主查）

### 结论：〔通过——三表 31 列逐列全符＋PK/索引/CHECK 全符；链位手术合并后单头实跑过＋无补丁反证必断；幂等并存两库逐列 diff 空〕

**逐表逐列对照表**（ORM 真源＝`app/domains/gateway/store.py`；DDL＝`migrations/versions/20261005_0018_gateway_tables.py`；行号实测于 2b03fc0 树）：

**gateway_spend_record（17 列，ORM :58-87 / DDL upgrade 第一段）**

| 列 | ORM 声明 | DDL | 判 |
|---|---|---|---|
| id | String(32) PK | VARCHAR(32) NOT NULL, PRIMARY KEY | ✓ |
| time | Mapped[datetime] NN | TIMESTAMP NOT NULL | ✓ |
| model_key | String(16) NN | VARCHAR(16) NOT NULL | ✓ |
| alias | String(64) NN | VARCHAR(64) NOT NULL | ✓ |
| input_tokens/output_tokens/first_ms/total_ms | Mapped[int] NN ×4 | INTEGER NOT NULL ×4 | ✓ |
| cost_yuan | Numeric(12,6) NN（sqlite variant 不涉 DDL） | NUMERIC(12,6) NOT NULL | ✓ |
| fallback | Boolean NN, default Python 侧 | BOOLEAN NOT NULL（无 server default） | ✓ |
| note | Text NN, default "" | TEXT NOT NULL | ✓ |
| caller | String(64) 可空 | VARCHAR(64)（无 NOT NULL） | ✓ |
| run_id | String(32) 可空 | VARCHAR(32) | ✓ |
| served_model | Text 可空 | TEXT | ✓ |
| attempted_fallbacks | JSONB 可空（sqlite JSON variant） | JSONB | ✓ |
| created_at/updated_at | datetime NN, default=now Python 侧 | TIMESTAMP NOT NULL ×2 | ✓ |

索引：ix_gateway_spend_time_desc(time DESC)／ix_gateway_spend_model_time(model_key, time DESC)／ix_gateway_spend_run(run_id) 三枚逐枚同形 ✓（ORM `__table_args__` :61-65）。

**gateway_drill_run（9 列，ORM :92-109）**：id String(32) PK／status String(16) NN＋**CHECK `ck_drill_status` IN ('running','done') 同名同域**／nodes JSONB NN／result JSONB 可空／summary Text 可空／started_at TS NN／finished_at TS 可空／created_at/updated_at TS NN——逐列 ✓。

**gateway_budget_config（5 列，ORM :113-123）**：id String(16) PK（default "singleton" 为 Python 侧，DDL 无 server default——**与 ensure 直建完全同形的承诺成立**）／两阈值 NUMERIC(12,6) NN／created_at/updated_at TS NN ✓。

交叉实证：①临时库实形＝17/9/5 列、8 索引（3 pkey＋3 基础＋2 trgm）、ck_drill_status、表/列 COMMENT 在位且 `budget.id` 注释渲染「恒 'singleton'」（0018 头注 ''singleton'' 双写转义正确）；②迁移建 vs ensure 建两库 information_schema 31 行逐列 diff＝空；③downgrade 分工正确（三基索引＋三表归 0018 撤、trgm 两索引＋caller 列归 0011 撤、pg_trgm 扩展不撤同 0010 惯例）；④链位手术＝0011 原指 0010 改指 0018（diff 一行），纯 Alembic 全新库全链不断（19 步实跑），且**反证**：无补丁的 master 同一跑法恰断于 0011 UndefinedTable——手术确为修复而非摆设。

## 三、原型闸误报面（票面点名专查）

### 结论：〔通过——GREEN 判据成立且合并后仍绿；七段红绿/零误伤/幂等演示全过；再生流程三处写明〕

1. 〔通过〕**GREEN 判据**：manifest 四文件 SHA-256 与提取树实算一致（check rc=0）；四 hash 与 W-LAND.rev 三节表 blob 等证表逐一相符（22d55acde0…/4d74f7eb89…/848e770f19…/2702c039f6…）；`git diff f5e1677 master -- 四文件`＝空（**master 前进零漂移机证**）——合并后闸不红。
2. 〔通过〕**误报面七段演示**（全在提取树）：篡改受监控页 B4→RED rc=1 点名文件＋处置语（含 `update` 再生指引）；复原→GREEN；**改非清单文件 landing/E2.jsx→GREEN 零误伤**；删受监控文件→RED 缺失；复原→GREEN；`update` 于内容未变时清单**字节级不变**（md5 与提交版同——再生不产伪 diff）；合法同步批全流程（改页→RED→update→GREEN→还原清单一并还原→GREEN＋清单复原）过。
3. 〔通过〕**保护面边界如实**：闸只盯 manifest 四文件——pages/ 其余原型页不在清单（dev 疑点 4，扩面节奏归 L0——复核属实，维持转 L0，非缺陷）；落地树接线/flows/CI/后端零触碰清单路径不误红（演示 3 实证）。
4. 〔通过〕**再生流程写明面**：脚本 docstring「update＝合法原型同步批专用」＋RED 处置语＋manifest note 三处同文（命令＋「同票提交」）；runbook 不涉及闸（其范围＝建号/口令/MinIO，分工合理）。

## 四、双树冒烟常驻化

### 结论：〔通过——7 例断言强度逐一复核成立；272+7=279 实测符〕

1. 〔通过〕**断言强度**：落地三页真端点实发断言——A2 四 URL **精确等值**（`=== ep`）、E2 四端点 includes＋**X-Dev-User='aqiang' 头断言**＋规则行文案渲染、B4 空态文案＋URL 前缀；原型三页 **stub fetch 零调用断言**（`allow()` 全 404 兜底使漏网 fetch 必被计数＋`expect(fetchMock).not.toHaveBeenCalled()`）＋种子内容断言（E2 规则种子/p7 流转「复核」后「复 扫」按钮在位/A2「渤中28-1-N2」/B4「《N-02 井完井报告》」）；registry 九键全序断言。票面「stub fetch 零调用断言/真端点 URL 断言」兑现。
2. 〔通过〕**增量归因**：master 提取树基线 272（W-LAND 时点 266→master 前进中的合法中间增量）＋7＝279 实测；冒烟单列 7/7；jsdom 环境桩与 landing/E2.test.jsx 同款零新依赖。
3. 〔极低·登记〕E2 例端点匹配用 `includes` 子串（A2 例为精确等值）——冒烟用途足够，见发现 F6。

## 五、口令机制测试

### 结论：〔通过——两半边独立断言实跑过；runbook §2 与实际键逐键对账无漏键无幻键；一条建议级注记见 F4〕

1. 〔通过〕**两半边机判**：`test_load_database_specs_env_injection_overrides_repo_defaults`——覆盖半边（setenv PG_HOST/PG_PASSWORD/MIDPLATFORM_PG_HOST→断言 primary.host/password 与 midplatform.host 生效）与回落半边（delenv→断言 localhost/petro/midplatform 开发默认）两段独立断言；`.env` 兜底源以 DOTENV 指向不存在路径隔离。实跑绿（含于 16 passed）。
2. 〔通过〕**无幻键**：runbook §2 数据面六键全实存——DATABASE_URL＋MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY（lake_store.py:348-351 与 :568-571）、AGG_DATABASE_URL（agg.py:124）、QUALITY_DATABASE_URL（quality_store.py:71）；`DP_GC_RETENTION_DAYS` 于 §4 有（gc.py:98 实读，缺省 90）。主仓 PG_HOST/PORT/DB/USER/PASSWORD＋MIDPLATFORM_PG_* 五键与 config/database.yaml 占位符**逐键逐默认值**相符（localhost/5433/petro/petro·midplatform）。
3. 〔建议级〕runbook §2 未含 models.yaml LLM 密钥占位符（MINIMAX_API_KEY/GLM_API_KEY 等）与 `Settings.sm4_key`（config.py:57 **硬编码开发默认**）——见发现 F4。

## 六、MinIO gc 安全性

### 结论：〔通过——只列不删三重机证；默认不注册双机证；判定口径边界一致；一条收窄建议归 Owner 部署批〕

1. 〔通过〕**只列不删**：gc.py 全文仅 `list_objects_v2` 调用面（**delete 面不存在**——非「存在但没调」）；测试替身 `delete_object`/`put_object` 即 raise（test_gc.py:26-30）；跑完桶原样断言（:99）。8 测实跑全绿。
2. 〔通过〕**默认不注册**：scheduler.py 零 gc 引用（grep 机证）＋`build_scheduler` 管道/拾取全配齐时 `job_ids == {"dp-pipeline", PICKUP_JOB_ID}` 精确断言（:114-124）；人工入口 `python -m worker.gc` 单次清点退出；缺环境变量 ValueError 不静默起湖（:126-133）。
3. 〔通过〕**判定口径**：孤儿＝键不在 `lake_snapshot.data_object_key` 引用集 ∧ LastModified < now−retention（**边界一致**：==cutoff 不列，与 docstring「早于」同语义）；升序最老在前；分页 ContinuationToken 走完（5 对象 3 页机判）；有主超期（120 天）不列、孤儿未超期（3 天）不动——两半边各有专测。「先留桶后落账」的在途对象由保留期窗保护（新写对象 age≈0 < 90）。
4. 〔登记〕清单口径＝**全桶无前缀过滤**——桶内任何非快照账对象（人工误放文件等）到期即入清单；因删除面不存在＋删归 Owner 两步制，风险被流程兜住。真删除实现落仓时应考虑键形（`{table}/{batch_id}/data.csv`）校验收窄清单面——归 Owner 部署批（与「零删除实现」现状不冲突）。GcCatalog 借 `_fetch`/`_s3` 私有名的 duck-typed 窄投影——Protocol 形态可行，登记不处置。

## 七、发现清单（每条带位置＋影响评级＋建议处置）与合并序建议

| # | 位置 | 发现 | 影响 | 建议处置 |
|---|---|---|---|---|
| F1 | dispatch/results/DEP-01.dev.md §闸门实跑⑤ | dev 回报 hermetic 为「130 passed, **6 skipped**」，本审查同命令同提交实测「130 passed, **57 skipped**」——57 全为 TEST_DATABASE_URL 门控的 PG 实跑面（-rs 逐条核实），passed 面逐字同、CI PASS 判定不变；dev 系历史回报（DP-04~07）skip 数恒 5→6 与实测机制不符 | 低（数字登记失真，无判定影响） | 执行台登记勘误；后续回报 skip 数以实测为准（hermetic 130+57／PG 全量见本表） |
| F2 | data-plane tests/pg/test_quality_store.py `writer_role` fixture（yield 语句，约 :189）＋tests/pg/test_agg_star.py:185-186 | 两受限账号 fixture 的探针 DSN 把**库名硬编码为 `/petro`**（仅从 TEST_DATABASE_URL 截取 host:port）——TEST_DATABASE_URL 指向任何其他库名时 GRANT 建在测试库、探针连 petro 库，错位致 6 例失败（本审查临时库全量跑 181+6 的全部失败来源）；**既有测试基建 wart，非 6a38f56 产物**（该提交仅 gc 两文件） | 低（测试可移植性；dev 标准环境不受影响） | 库名段改从 TEST_DSN 取（同 host:port 截取方式）；归 data-plane 测试基建小票，不阻本票 |
| F3 | data-plane tests/pg/test_agg_star.py `test_write_agg_three_tables_allowed` | 探针向 `agg.dim_date` 插**固定日期 '2025-09-01'**，遇既有日历行即 UniqueViolation——对脏库/部分复跑不幂等（全量套件执行序下恰好先插先过＝dev 187 可复现的环境）；本审查对 petro 库复跑两受限类时即踩中（8 过 1 挂）。同 F2 既有基建、非本票产物 | 低 | 探针日期改唯一值（如 2099-01-01）或 ON CONFLICT DO NOTHING＋用后清理；归同一测试基建小票 |
| F4 | docs/deploy/db-accounts-runbook.md §2/§3 | §2 环境变量表未含主仓 models.yaml LLM 密钥占位符（MINIMAX_API_KEY/GLM_API_KEY/MINIMAX_BASE_URL/GLM_BASE_URL 等）与 `app/infra/config.py:57` sm4_key（**硬编码开发默认 '00112233…'**）——表自身声明范围＝数据库/湖连接面故不算错，但被当「生产全量清单」消费会漏；§3「禁默认上生产」清单（petro/petro、midplatform/midplatform、petro12345）未点名 SM4 默认密钥 | 建议级 | 随下次触碰补两行：§2 末加范围声明（或 LLM 密钥/SM4_KEY 注记行）；§3 清单顺带点名 SM4 开发默认密钥 |
| F5 | migrations/versions/20261005_0018_gateway_tables.py（COMMENT 段） | 表/列 COMMENT 仅迁移路径有——ensure 单独直建的库（不跑链）无注释元数据；链跑过后幂等覆盖、终态一致（本审查两临时库对照：列形 diff 空，注释差异不涉 information_schema.columns 比对面） | 极低（元数据面；运行纪律已定「迁移链先行」runbook §5） | 无需处置（登记） |
| F6 | web/src/landing/dual-tree-smoke.test.jsx（例 2 落地 E2 端点断言） | URL 匹配用 `includes` 子串（A2 例为精确等值）——冒烟用途足够，理论上有子串误配面 | 极低 | 可不处置；求严格时改精确等值 |
| F7 | （流程面）dev 疑点 1 撞号 | **0018 撞号 S-01 已化解**：S-01 改号 0019（down=0017）先行合入 master，与本票 0018（down=0010，链中段）集合不相交——本审查以合并形态补丁零冲突＋全链 19 步单头实跑证毕。**合并序建议＝2b03fc0 直接合入 master，无遗留改号/重排动作**；dev 偏差 2~5、疑点 2~5（agg clean 段生产归属、90 天建议值非裁决、清单扩面节奏、中台连接串归集）照旧转 L0/后续票 | 登记 | 执行台按上述合并序收口 |

**无高/中影响发现；无阻塞关票项。** F1~F3 为数字登记与 data-plane 既有测试基建登记（后者非本票产物），F4 为建议级补注记，F5/F6 极低登记，F7 为合并序确认。

## 零修复动作声明

**本审查全程零修复动作已执行**：未改、未提交、未合并任何被审代码/配置/合同/测试；主仓零 checkout/零 switch/零 stage/零 commit，被审树内容一律 `git show`/`git archive` 只读取证，Owner 私产与并行窗口未提交改动零接触（开工/收工 `git status --porcelain` 复核：dispatch/journal.jsonl 修改与 dispatch 未跟踪件原样；开工时在册的 eval/README.md 修改与 eval/answers/ 未跟踪件于收工时消失——**并行窗口动作，非本审查所为，本审查全程未触碰 eval/**）；data-plane 嵌套仓零写入（复跑在 /tmp 克隆内）。独立复跑全部落位：alembic 双向用容器内四个临时库（fresh/ensure/dp/base）**用毕全 DROP**（pg_database 复核 0）；dev petro 库仅按 dev 同款程序复跑受限账号两测试类，探针行/角色收工复核零残留（QT-probe-01=0、quarantine 探针=0、water_line 探针=0、pg_roles tpa_%=0）；原型闸篡改演示全在 /tmp 提取树，真仓原型树零触碰；/tmp 全部作业件（提取树×2、克隆、补丁、替身备份、清单备份）已清除。本文件为本次作业对主仓的唯一写入。
