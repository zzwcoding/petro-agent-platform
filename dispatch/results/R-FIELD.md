# R-FIELD fieldforge 真产物实弹接入数据面 · 调研回报（只读拍）

## 产物
- 本回报文件（零代码改动、零仓内写入；预演脚本全部落 /tmp：/tmp/check_gate.py、/tmp/check_bundle.py）。
- 调研对象：fieldforge=/Users/divh/Downloads/fieldforge（v0.1.0，HEAD c2cfc48）；data-plane=/Users/divh/Downloads/petro-agent-platform/data-plane/（嵌套独立仓）；主仓消费面 app/domains/dataops/quality + migrations/versions/0014/0015 + web/src/pages。
- 方法：逐文件读源＋两轮 /tmp 只读预演（把 data-plane 的 S1 进料闸规则与 bundle 规则 1–12 对干净 out-tpa 实弹空跑），全部结论带 file:line 或实测数字。

## 闸门实跑
- 本票为只读调研拍，不涉 pytest/ruff/合同闸（无代码产物）。实测预演＝S1 闸规则对 out-tpa 干净产物：rule-1/2/3/5/16 全 0 命中；bundle 规则 1–12 中仅 rule-12 命中 36（详见第二节/第四节）。

## 偏差
- 无施工偏差（零改动）。调研发现与任务书预期的偏差逐条列「疑点」节。

## 疑点（待 L0/Owner 裁决，不动手）
1. **规则 12 结构性挂**：干净 out-tpa 上 36/36 区块月全命中（注入/产液比 0.37–1.94）。fieldforge 对注入与产量独立建模、无物质平衡勾稽；且 transform.py:300-302 有意分歧注记（fieldforge r12 对"结算 vs 产量"、本仓对"注入 vs 产液"）——两头都没对齐。实弹接入后 E2 必显 36 告警单，需 Owner 预告口径或裁决处置（保留如实显示/对合成数据停用 12）。
2. **扫描面 ≠ raw 8 表（漂移点）**：quality_store.py:45-48 的扫描面 8 表含 sensor_reading_subdaily、不含 well_measures；而 001 迁移的 as-is 8 表含 well_measures。quality_store.py:50-53 注释自称「受检表＝001 八张 as-is 源表」与实际集合不符；worker/scheduler.py:66-70 的 _SCAN_TABLES 字面同漂移。
3. **well_measures 无任何规则**：0015 种子 1–12、执行体 RULES_FULL（transform.py:438-459）均无措施台账规则；该表连扫描面都不在。B 档扩表时规则判据归属要 Owner 定（新规则号或挂"完整性"）。
4. **open_days 单位口径漂移**：合同 fieldforge/schemas/tpa-contract-v0.1.yaml:194-197 写 unit h（0–24 小时）；data-plane/migrations/001_lake_schemas.up.sql:88 注释写「天」。值域同 0–24、rule-5 不受影响，展示语义有出入。
5. **layer_split 分隔符漂移**：合同 :235 描述「P1:60,P2:40 式」；fieldforge 实际产出 `P2:35:P3:65`（层间也是冒号，冒号双义不可直接 split 解析），DDL :104 注释示例亦为逗号形。
6. **well_overhaul.affected_output 类型分叉**：合同 :264 为 float；DDL :118 为 VARCHAR(32)（as-is 文本纪律，样本含「约210吨」）。fieldforge 干净产物是纯数值文本，落 VARCHAR 兼容；但与 DDL 预期的脏文本形态不同域。
7. **equip_status 缺时间戳列**：DDL :153-155/165 已登记（字典粒度=设备号+时间戳，供给无时间戳列）——fieldforge 同样无此列，逻辑键退化 equip_id（lake_store.py:83）。补列需 fieldforge 先定名，禁止本仓发明业务列名。
8. **脏版 stop code 命中口径**：dirty 版 rule-8 实际只挂 1 行（LEGACY-OLD）；另 4 行 legacy 形是 R3/R5——在平台 _KNOWN_CODES（transform.py:224）内属「映射表命中」通过态。manifest 记 legacy_rows:4+unknown_rows:1，按单口径与挂行口径差 4 倍，验收预期要按 1 写。

---

# 一、fieldforge 侧产物盘点

## 1.1 out-tpa/ 全文件逐个盘点（15 CSV + manifest.json + evaluation.json + narration/）

生成参数（out-tpa/manifest.json）：tool fieldforge 0.1.0 · python 3.14.7 · generated_at 2026-09-27T16:09:11Z · schema tpa-contract 0.1.0 · recipe tpa_s1_demo · seed 20260927 · period 2025-09-01+365d · output csv · conformance pass（4,603,081 cells）· gate overall pass（pass 19 / warn 0 / fail 0 / skipped 6，enforce true）· freshness offline / T-1 / as_of 2026-08-31 · 合成数据声明在位。

**8 张 tpa 合同表**（行数=数据行，不含表头；表头为 CSV 逐列实测）：

| 表 | 数据行 | 表头（逐列） | manifest 记账行数 | 实测行数 | 空值 |
|---|---|---|---|---|---|
| well_info | 120 | well_id, well_name, well_type, first_prod_date, platform, block_name, field_name, current_status, remarks | 120 | 121 行含头 | 仅 remarks 全空（120/120） |
| oil_production_daily ★ | 31,390 | well_id, prod_date, oil_output, liquid_output, water_cut, plan_output, open_days, oil_pressure, report_shift | 31,390 | 31,391 行含头（任务书「31,391」即含表头的 wc -l 口径） | 0 |
| water_injection_daily | 12,410 | well_id, prod_date, inj_volume, pump_pressure, layer_split | 12,410 | 12,411 含头 | 0 |
| well_overhaul | 19 | well_id, overhaul_start, overhaul_end, overhaul_type, affected_output, batch_id | 19 | 20 含头 | 0；batch_id 全 -T1 |
| well_measures | 59 | well_id, measure_type, job_date, effective_from, effective_to, incr_oil_annual | 59 | 60 含头 | 0（干净版效期全在） |
| fluid_test | 987 | well_id, sample_date, water_cut_lab, density, api_gravity | 987 | 988 含头 | 0；density 实测域 [0.849, 0.924] |
| equip_status | 86 | equip_id, equip_type, load, current, stop_reason_code | 86 | 87 含头 | 0；stop codes＝RUNNING 67/BELT 10/PUMP 6/MOTOR 3（全在平台已知码表） |
| monthly_settlement | 36 | block_name, settle_date, net_weight | 36 | 37 含头 | 0；settle_date=2025-09..2026-08 每月首日×3 区块 |

日期域实测：oil_production_daily prod_date 2025-09-01 → 2026-08-31（整 365 天）。

**manifest 声明（血缘/评估）**：manifest.json 无跨表血缘图（血缘在 data-plane 侧进料时自建，ingest.py `_lineage_manifest`）；fieldforge manifest 记账的是 seed/schema 版本/单位表（units 14 表全量）/conformance 细胞数/gate 结论/freshness 档位/合成声明。out-tpa/evaluation.json 为 evaluate 闸门报告件；out-tpa/narration/ 为班报语料样例目录（P2-T4）。

**非 8 表产物定性（6 件，全部有合同实体定义——属其他数据族/辅助实体，非废料）**：

| 件 | 行数 | 定性 | data-plane 消费现状 |
|---|---|---|---|
| wellbore.csv | 120 | 井筒辅助实体（合同 tpa-contract-v0.1.yaml:56-84，每井 1 主井筒） | 无 raw 表、无规则、无消费面 |
| sensor_channel.csv | 360 | 传感器通道字典（:85-117，120 井×3 通道） | 同上 |
| sensor_reading.csv | 131,400 | 传感器日度读数（:461-479） | 同上 |
| sensor_reading_subdaily.csv | 210,240 | 15 分钟档亚日读数（:379-400；**在质检扫描面内，规则 11 的判据源**） | 扫描面有它、湖里无表（lake_bundle KeyError 诚实跳过，scheduler.py:213-215） |
| well_log_curve.csv | 288,120 | 测井曲线（:402-459，FORCE 2020 记忆码+12 类岩性；服务 identify_lithology 工具的数据前提） | 无 |
| injection_connection.csv | 65 | 注采受效关系（:354-377，合同注明「本体域硬要求」，劈分 Σ=1） | 无 raw 表；本体要求但数据面无落点 |

## 1.2 out-tpa-dirty/ 与 out-tpa/ 的差异性质

- **性质**：同 schema（tpa-contract 0.1.0）同种子（20260927）同骨架，注入器家族（injection v2.0.0，注入种子 20263928）产出的**脏特征交付物**——闸门 report-only（manifest 无 gate 键＝null），conformance 只跑 884,117 cells（dirty_mode 跳过 fk/enum 符合性）。是质检规则的挂样本生产线，不是"坏数据事故"。
- **文件差**：dirty 只有 11 CSV——比 out-tpa 少 well_log_curve / injection_connection / sensor_reading_subdaily 三件（其配方/生成路径未再生 P2/M5 亚日与测井产物）。
- **行数差（逐表实测）**：oil_production_daily 31,774（+384＝40 班次重复＋344 配产双值，与 manifest counts 对账）；其余 7 表行数与干净版全同。
- **病灶→平台规则对照**（recipes/tpa_s1_dirty.yaml:20-32 全配方 ＋ manifest counts ＋ 逐表抽样实测）：

| 注入器 | manifest 计数 | 对应平台规则 | 实测抽样 |
|---|---|---|---|
| shift_duplicate 班报重复 | 40 | rule-1 | opd 同键重复行实测 383（含配产双值行的同键叠加） |
| plan_dual_value 配产双值 | 344 行 | rule-1 | 同键双行 plan_output ×1.1（如 22.65→24.91） |
| unit_misentry 单位误录 | 12 | rule-3 | **数值形**（漏折算密度→折算密度越上界 / ×6.29 方桶混淆），非「12.40方」文本；cell 级 diff 992 处 |
| well_id_legacy 旧井号 | 25 | rule-7 | 实测 21 行（N02/N-4/X-6 形） |
| stale_constant 恒值30日 | 3 井×30 日 | rule-10 | 3 frozen_windows |
| late_batch T-3 补录 | 6 批 | rule-6 | well_overhaul batch_id 实测 6 个 -T3（20251001-T3…20260719-T3） |
| status_lag 状态滞后 | 3 井 | rule-9 | well_info current_status 分布 110/6/3/1 |
| legacy_stop_code 新旧编码 | 4+1 | rule-8 | 实测 R3×1＋R5×2＋LEGACY-OLD×1；R3/R5 在平台已知码表内→**rule-8 实际只挂 LEGACY-OLD 1 行** |
| measure_missing 措施缺效期 | 15 | （无对应规则，纯完整性） | well_measures 15/59 缺 effective_from/to |
| lab_conflict 化验打架 | 15 | rule-4 | fluid_test 同行数、15 行含水与计量偏差 >5pp |

## 1.3 schemas/tpa-contract-v0.1.yaml × data-plane/migrations/001_lake_schemas.up.sql 逐表逐列对照

**8 表列名与列序全部一致（零缺列零改名）**；差异集中在类型/单位/注释口径：

| # | 位置 | 差异 | 定性 |
|---|---|---|---|
| 1 | 合同全表 float ↔ DDL NUMERIC(p,s) | 等效映射（fieldforge 产出 ≤3 位小数，均在 DDL scale 内：oil_output NUMERIC(10,2)、water_cut NUMERIC(5,1)、density NUMERIC(5,3)、open_days NUMERIC(4,1) 实测不截断） | 兼容 |
| 2 | well_overhaul.affected_output | 合同 float（:264）↔ DDL VARCHAR(32) as-is 文本（:118，样本含「约210吨」） | 类型分叉（疑点 6） |
| 3 | open_days | 合同 unit h（:196）↔ DDL 注释「天」（:88） | 单位口径漂移（疑点 4） |
| 4 | equip_status | 合同/DDL 均无时间戳列；DDL 注释登记「字典粒度＝设备号+时间戳，供给无时间戳列」（:153-155,165） | 供给缺口（疑点 7） |
| 5 | well_overhaul 湖技术列 | DDL 用 _src_batch_id 避让业务 batch_id（:121-124）；lake_store.py:413-414 已按列名让位处理 | 已闭环 |
| 6 | 三技术列 _snapshot_id/_batch_id/_ingested_at | DDL 独有（合同不管湖技术列）；lake_store._cast（:529-553）按列族显式定型，失败 LakeTypeError 不静默 | 机制齐 |
| 7 | sensor_reading_subdaily | 合同有实体；DDL 无 raw 表（001 只有 as-is 8 表） | 结构缺口（B 档边界：该表不进湖） |

DDL as-is 纪律要点（:4-7）：不设业务主键/唯一约束——A/B 班重复行、配产双值行是原始层合法内容，质检闸在进料前拦截。这与 C 档「脏批整批拒收」语义吻合。

---

# 二、data-plane 侧消费能力现状

## 2.1 进料规则注册表现状

- **rules dict 硬编码两表**：worker/scheduler.py:143-144——`Ingest(..., rules={"oil_production_daily": RULES_OIL_DAILY, "well_info": RULES_WELL_INFO})`。
- RULES_OIL_DAILY＝rule-1（(well_id,prod_date) 唯一）/rule-2（oil_output 非空，行级严格版）/rule-3（折算密度带）/rule-5（water_cut/open_days 值域）——transform.py:115-120。
- RULES_WELL_INFO＝rule-16 行级半边（well_type/current_status 枚举）——transform.py:123-139。
- **fail-closed**：表不在 rules dict＝UnruledTableRejected 拒绝入湖（ingest.py:35-41,115-117）；任何规则命中＝整批 BatchRejected（ingest.py:119-121——注意 validate_batch 的「坏行剔除」路径只在闸通过后才有意义，**闸一票否决形态下剔除路径对拒批不可达**，scheduler.py:176-192 拒批记 summary["rejected"] 零落库）。
- CSV 进料通路已真身化：run_csv_load 全列文本读入（ingest.py:97-111）→ validate → LakeCatalog.append（PG raw 逐行 INSERT＋MinIO 留原始批＋lake_snapshot 快照账，lake_store.py:394-440）→ freshness 登记 as_of=快照 committed_at（ingest.py:134-139）。

**其余 6 表入湖各缺什么（每表：规则实现/判据源/工作量定性）**：

| 表 | 进料规则集 | 可复用判据源 | 工作量定性 |
|---|---|---|---|
| water_injection_daily | 无 | 合同量程 inj_volume [0,500]/pump_pressure [0,25]（yaml:224-233）；layer_split Σ=100（实测域 P2:35:P3:65 形，**解析格式先定**——疑点 5）；bundle 侧 rule-12/15 已有但为跨表/序列判据不宜作行级闸 | 小：一个 RULES_* ≈30-40 行＋钉子测试 |
| well_overhaul | 无 | rule-6 行级半边（-T3 挂）已在 bundle（transform.py:210-213）；可加 overhaul_end≥start 日期序 | 小 |
| well_measures | 无（且不在扫描面） | 本体 M3 无专条（0015 种子 1–12 无措施规则）；合同 effective_from/to nullable | 小但**规则归属要 Owner 定**（疑点 3） |
| fluid_test | 无 | density∈[0.82,0.98]（合同 :323-327）；api_gravity=141.5/SG−131.5 折算一致 | 小 |
| equip_status | 无 | rule-8 行级半边（码表 _KNOWN_CODES）已有（transform.py:224-231）；load/current 量程 | 小 |
| monthly_settlement | 无 | rule-19 为跨表钩稽不宜作行级闸；行级可用 net_weight≥0＋settle_date 月首形状 | 小 |

## 2.2 质检 bundle 的规则分派机制

- 分派链：run_quality_task（quality_store.py:322-386）读 quality_rule **启用集**（enabled_rules :183-189，只读——启停写口归主平台 E2）→ evaluate_enabled（:139-152）按 `rule-N ↔ quality_rule.no` **同号映射**到 transform.RULES_FULL → 每规则 `check_batch(bundle)`（跨表规则收多表打包 dict）→ 命中按 `_RULE_TABLE` 主表落隔离（action=隔离/整批拒收）或仅计 hits（action=告警，不产隔离行 :352-365）。
- 启用集＝0015 种子（migrations/versions/20261004_0015_quality_waterline.py:56-107）：**1–12 enabled，13–20 仅登记 enabled=false**。action 分布：2/3/7/8/9=隔离；1/4/5/6/10/11/12=告警。
- bundle 缺表＝规则空跑如实（transform.py:178-179 `bundle.get(table, [])`）——扫描面与规则分派天然解耦；报告 range 按实扫表数动态生成（quality_store.py:369-371）。
- 拾取面：run_pickup_once 湖 as-of 视图组 bundle（scheduler.py:206-216）——**sensor_reading_subdaily 无 raw 表，拾取复扫永远扫不到它**（KeyError 诚实跳过），只能从 run 目录扫描面（run_pipeline_once :149-154）覆盖。

## 2.3 DP_PIPELINE_TABLES / DP_SCAN_TABLES 现语义与扩表改法

- 现语义（DP-07 F-01 解耦后，scheduler.py:64-70,122-131）：
  - `DP_PIPELINE_TABLES`（缺省 `oil_production_daily,well_info`＝agg 两源）＝**进料面**：逐表 run_csv_load 过闸入湖；
  - `DP_SCAN_TABLES`（缺省全受检 8 表，与 quality_store.SCAN_TABLES 同域）＝**质检/拾取扫描面**：从 run 目录收 CSV 组 bundle 跑规则。
- **扩进料表改法**：只改 env 不够——rules dict 是代码硬编码；正确动法＝transform.py 增 RULES_* ＋ scheduler.py:143-144 dict 扩表（env 可选同步扩）。只扩 env 会得到 UnruledTableRejected 诚实跳过（fail-closed 不崩周期，scheduler.py:190-192）——安全但零效果。
- 扫描面已全 8 表，扩扫描面只需 env；但注意其 8 表集合与 raw 8 表的差异（疑点 2）。
- 钉子测试在 tests/worker/（字面一致性看守，scheduler.py:66-67 注释点名）。

## 2.4 AggStarWriter 在真产物量级（31,391 行）下的适配点

- 链路：refresh_from_catalog（agg.py:178-199）＝湖 as-of 视图全表 scan（RANK 窗口 per 业务键，lake_store.py:168-181）→ build_agg 纯函数（防御折叠 O(N)）→ AggStarWriter.write 逐行 upsert 三表（agg.py:137-168，单连接单事务，dim_well 120＋dim_date 365＋fct 31,390）。
- 适配点（均可过、无阻塞，但无余量文档化）：
  1. fct 31,390 次逐行 INSERT…ON CONFLICT（无 executemany/copy）——本地估计 10s 量级；每周期全量重刷（幂等 by 组合 PK＋rule-1 双保险）；
  2. as-of RANK 窗口对 raw.oil_production_daily 全表扫——31,390 行 PG 无压力，×10 前需优化；
  3. dim_date 覆盖 fct prod_date 全域 365 天；
  4. quality_flag 恒 NULL（值域无合同枚举，零发明——agg.py:18-19）；
  5. 汇总层水位 data_date=fct 最大 prod_date（2026-08-31）。
- 消费对边：主仓问数链（app/domains/chat/chains.py:6,1104-1116 选表＝agg 星型注册面）与 A1Chat 页；agg 直写限写账号 AGG_DATABASE_URL（agg_writer.sql），未配＝显式跳过不静默。

---

# 三、差距与方案分档

## A 档（最小实弹：仅 agg 两源真产物；其余表质检扫描照跑不入湖）——**推荐先行**

- **改什么**：零代码。前置＝部署面：四连接串（DATABASE_URL/MINIO_*/AGG_DATABASE_URL/QUALITY_DATABASE_URL）＋主仓迁移 up（0014 agg＋0015 quality 已在链上）＋data-plane 001 湖迁移＋限写账号建立（agg_writer.sql/quality_writer.sql）；把 out-tpa **复制**为 run 目录（建议部署侧路径，如 /data/runs/out-tpa-20260927，不引 fieldforge 仓内路径）；`DP_PIPELINE_RUN_DIR` 指向之；`python -m worker.scheduler --once` 干跑验证后常驻。
- 跑什么（单周期六件事，scheduler.py:134-203）：质检 bundle＝run 目录 8 张扫描表（含 subdaily 210k 行，rule-11 空跑如实在）→ QT 任务落库；进料闸 RULES_OIL_DAILY/RULES_WELL_INFO 实弹（**预演已证干净产物全过**）→ 两表落湖；agg 三表 31,390 行直写；水位三 tier 回写 2026-08-31。
- **测试怎么写**：沿用 tests/dp2/test_ingest_real.py 模式加一个 env 门控的真产物集成测试（TEST_FIELDFORGE_OUT 指向产物目录，断言行数 31,390/120＋rule-12 hits=36 常数锚）；不新增单元面。
- **风险**：规则 12 必挂 36（疑点 1，预告口径）；水位红/黄属预期（第四节）。
- **规模**：0.5 天（部署＋干跑证据）。

## B 档（全 8 表进湖：扩进料规则工作量逐表列）

- **改什么**：
  1. transform.py 增 6 个 RULES_*（water_injection_daily/well_overhaul/well_measures/fluid_test/equip_status/monthly_settlement，判据源见 2.1 表；well_measures 规则归属先过 Owner）；
  2. scheduler.py:143-144 rules dict 扩 6 表（DP_PIPELINE_TABLES env 缺省同步或部署时显式传）；
  3. 无 DDL 改动（raw 8 表已在 001）；lake_store 对 well_overhaul._src_batch_id/equip_status 键退化已闭环；
  4. water_line：_DATE_KEY 已覆盖 5 表（quality_store.py:58-63），well_measures 无日期键＝不产水位主张（宁缺不虚标，诚实）。
- **测试怎么写**：每 RULES_* 一组钉子测试（过样本取 out-tpa 真行＋挂样本自造/取 out-tpa-dirty 对应行）；tests/worker 字面一致性钉子同步扩；真产物 8 表集成测试（行数锚 120/31,390/12,410/19/59/987/86/36）。
- **风险**：layer_split 解析格式先定（疑点 5）；6 表进湖后 as-of 视图按业务键覆盖——equip_status 键退化 equip_id（86 键），重复进同批数据幂等无害；well_measures 键退化 well_id（lake_store.py:81）——**同井多措措施行在 as-of 视图只可见最新批全量，跨批旧版被覆盖**，同批内并列全保留（RANK），现状无害但要写进票面。
- **规模**：2–4 天（6 规则集＋测试＋干跑）。

## C 档（全 8 表＋out-tpa-dirty 对照跑：质检闸实战）

- **改什么**：无新代码（依赖 A 或 B 的部署面）。dirty 目录复制为第二 run 目录，对** scratch 库**（或接受 as-of 覆盖的演示库）单次 `--once` 干跑。
- **预期实战（预演值，标注「推断·已实弹空跑验证」）**：
  - 进料闸：oil_production_daily 脏批 rule-1 命中（383 重复行）→ **整批 BatchRejected 零落库**（fail-closed 实战证据，summary.rejected=["oil_production_daily"]）；well_info 脏版枚举全合法→照常落库（status_lag 是跨表判据 rule-9 的事，行级闸不拦）。
  - 质检任务：启用 12 条全跑，hits 单数预期 ≈ rule-1 383＋rule-3 12＋rule-4 15＋rule-6 6＋rule-7 21＋rule-8 1＋rule-9 3＋rule-10 3＋rule-12 36 ≈ **480 单**；隔离行（action=隔离的 2/3/7/8/9）≈ 12＋21＋1＋3＝**37 行**（rule-2 批级阈值版 12/31,774≤0.5% 过，0 行）。
- **测试怎么写**：env 门控集成测试断言上述常数锚（reject 事件＋QT 报告 hits/隔离行数），常数来自预演、落地后以实跑为准回填。
- **风险**：同库先 A 后 C 会把 dirty well_info 按 well_id 覆盖进 as-of 视图（dim_well 变脏版）——演示库一次性用，或 C 档先跑；整批拒收语义 vs「坏行剔除」的预期差要写进票面（见 2.1 fail-closed 注）。
- **规模**：1–2 天。

## 推荐档位与理由

**A 档先行，C 档（dirty 单目录干跑形态）紧随，B 档随独立票走。**
理由：A 档零代码、当周可落地，真产物贯通「进料→质检落库→agg→水位→UI」全链且预演已证两表过闸零意外（唯一预期差 rule-12 36 告警已量化）；C 档的质检闸实战不依赖 B（进料面本来就是两表），dirty 干跑即得拒批＋隔离区实战证据；B 档的 6 表规则判据有两个 Owner 裁决前置（well_measures 规则归属、layer_split 解析格式），不宜绑在本批。

---

# 四、风险与前置

1. **日期域与 water_line/freshness**：真产物 prod_date 域 2025-09-01→2026-08-31（静态快照）。水位三 tier 将推进到 2026-08-31 后**恒定**；E2 端点 8 的 T-1 判定（domain.py:229-250，基准日−data_date）以今天 2026-10-04 算＝落后 34 天，水位卡红/黄是**如实展示不是故障**；freshness_registry.as_of＝入库时刻（快照 committed_at）与数据业务日期是两回事。需 Owner 预告口径（合成数据冻结在 as_of 2026-08-31）。
2. **脏数据边界**：out-tpa 是干净基线（gate enforce=true pass；实测 8 表除 rule-12 外零违例、零空值行、零重复键）；脏的全部在 out-tpa-dirty（注入器配方化、计数入 manifest）。唯一例外＝rule-12 物质平衡在干净版结构性挂 36/36（注入与产量独立生成，fieldforge 无勾稽建模；且与平台 r12 判据「注入 vs 产液」本就不同向——transform.py:297-302 有意分歧注记）。
3. **31,391 行量级性能**：append 逐行 INSERT 31,390＋agg 逐行 upsert 31,390＋RANK 窗口全表扫，本地合计估 O(10s)；周期内最大头是质检 bundle 每轮 DictReader 读 subdaily 210,240 行 CSV＋rule-11 O(N)（估秒级，内存 ~百 MB）。worker 单飞（max_instances=1，misfire_grace_time 3600）无超时风险；**无分页/批写机制，量级 ×10 前需 executemany/copy 与 bundle 流式化**（挂后续票，不阻塞本批）。
4. **CSV↔raw 类型兼容**：通路＝全列文本→_cast 按列族显式转换（LakeTypeError 不静默，lake_store.py:529-553）。实测：8 表仅 well_info.remarks 全空（→NULL 合法）；日期全 ISO 直落；数值小数位全在 DDL scale 内不截断；well_id 'N-01'/'Z-01' 合 VARCHAR(8)；equip_id 'EQ-N-01' 合 VARCHAR(32)；well_overhaul.affected_output 数值文本落 VARCHAR(32) 兼容。残留风险＝fieldforge 未来版本若产出超 scale 小数或非 ISO 日期，_cast 显式报错（as-is 纪律，可接受）。
5. **版本漂移**：fieldforge v0.1.0 活跃演进中（HEAD c2cfc48 learning S1 课含「表头保真回补」）；本次产物由 manifest 钉死 schema 0.1.0＋seed 20260927。接入应以**该 manifest 描述的字节快照为合同物**（产物入库后 provenance 留 schema 版本可对账）；fieldforge 升级后重生成→须重跑 1.3 对照表＋行数锚点（120/31,390/12,410/19/59/987/86/36）再进料。
6. **部署前置清单**：DATABASE_URL＋MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY（湖）、AGG_DATABASE_URL（agg 直写）、QUALITY_DATABASE_URL（质检落库/报水位/拾取）四串齐——任一缺＝对应步显式 skipped（scheduler.py:157-160,195-197，不静默装成功）；主仓迁移 0014/0015 与 data-plane 001 up；限写账号两模板建号；E2/问数链路由已在 main.py:53-104 挂载。

---

# 五、验收判据草案（可执行清单）

**① 行数对账（SQL，进料后）**
- `SELECT count(*) FROM raw.oil_production_daily WHERE _batch_id='<B>'` = 31,390；`raw.well_info` 同批 = 120；
- `SELECT rows_added FROM data_plane.lake_snapshot WHERE table_name IN ('oil_production_daily','well_info') AND batch_id='<B>'` = 31,390/120；
- MinIO `tpa-raw/<table>/<B>/data.csv` 在且行数一致（test_ingest_real.py:77-82 同款断言）。

**② 质检命中预期（E2 质检台＋SQL）**
- A 档：当日 QT 任务 status=done、report.rules_run=12、hits=36 且 hits[] 全部 rule_no=12（hit_count 按 12 个区块月×3 区块＝36 单）、quarantined_rows=0、rejected_batches=0；
- C 档（dirty 干跑）：summary.rejected 含 oil_production_daily 且 raw 该表本批零行；QT 报告 hits≈480（按 ② 预演表逐规则对账）、quarantine_row 落 ≈37 行（rule_no∈{3,7,8,9}）、E2 隔离区页可见。

**③ agg 对账（SQL）**
- `agg.fct_daily_metering` = 31,390 行；`agg.dim_well` = 120；`agg.dim_date` = 365（2025-09-01..2026-08-31）；
- 全等抽核：`agg` 每井每日 oil_output/liquid_output/oil_pressure 与湖 as-of 视图逐值相等（含 NULL）；
- 钩稽交叉验证（rule-19 disabled，改手工跑）：`monthly_settlement.net_weight` = 0.98 × 区块月 oil 合计（预演 36/36 比值恰 0.98，dev=0）。

**④ 水位推进（SQL＋E2）**
- `water_line` 三行：原始层/清洗层/汇总层 data_date 全 = 2026-08-31；重复跑周期不回退不翻倍；
- `data_plane.freshness_registry` 两源表 as_of=入库快照 committed_at；E2 端点 8 水位卡显示三 tier＋「落后 N 天」如实标注（红/黄＝预期）。

**⑤ UI 三页可见**
- E2 质检台：任务卡（QT 号/hits/规则数）、命中明细（规则 12 的 36 单按「区块·月」展示）、隔离区（C 档后）、水位卡；
- A1Chat 问数：例句问数（如「渤南区 2026 年 8 月日产油合计」）经 agg 星型出数，数值与 ③ 手工 SQL 对账相等，AnswerBundle 带 snapshot_id/质量状态；
- D6 数据建模页：agg 星型三表口径引用可见（该页为口径知识页——硬判据以 E2+A1 为准，D6 作观察项）。

**⑥ 确定性再生（可选加分）**
- 同 seed 重生成 out-tpa 字节级一致（fieldforge README 特性承诺）→ 进料重放同批行数对账不变。
