# bohai 本体 ↔ 平台七域对齐矩阵（轨道 0 首任务产物）

> **定位**：分析件——bohai 渤海域本体（本仓 `bohai/`，7 文件对齐底稿）与 Petro-Agent 平台七域合同（主仓 C1 台账 + E2/B5/A2/D3 + 99 册）的元素级对账。**不开建七域模型 YAML**——按矩阵结论走下一步 fork+增补+过闸（`petro/` 保持空仓，语义闸 CI 跳过中）。
> **上位依据**：主仓 `docs/adr/0004-本体真源回归与all-agent衔接.md` 裁决 1/6-① + `docs/roadmap.md` 轨道 0 第 1 步（"八模型 schema ↔ 平台七域对齐设计，对齐表落 ontology/manifest"——本文件即该对齐表，manifest 登记待 fork 批随行）。
> **真源声明**：A 侧 = 本仓 `bohai/` 7 YAML（逐元素读全，无抽样）；B 侧 = 主仓 `specs/api/C1-指标与业务术语库.md`（七域合同）+ `prototype/app/src/pages/C1.jsx`（种子实值，568 行读全）+ `specs/api/E2-数据质量台.md`（20 条质检规则）+ `specs/api/B5-关系图谱.md`（类型闸/11 类抽取实体）+ `specs/api/A2-井档案.md`（井档案 8 字段/映射卡）+ `specs/api/D3-安全与权限.md`（禁用词/加密/权限面）+ `specs/api/99-数据库与连接层设计.md` §2.8（sem_* 台账投影形状——同步器目标；任务派单写 §2.4，实为 §2.8 semantics 域 9 表，§2.4 是 approval 域，本矩阵按实际章节引用）+ 主仓 `CONTEXT.md`（映射卡/账号绑定两态/断言观等术语）。
> **注源纪律**：每个对账行注源三元组（bohai 元素 id / 合同册锚 / 设定书 §）。bohai 裁决记录（PROP-BOHAI-\*）**只引用不重写**；bohai 元素内的 R5·§ 锚随元素迁移保真，本矩阵不复述。**禁发明业务事实**：平台有 bohai 无的元素一律进增补清单并注缺口来源，不硬建。
> **状态标签**：[复用-direct]（直接迁 `petro/`，保留下裁决引用）/ [增补-bohai无]（平台有 bohai 无，须新建）/ [不迁]（bohai 有但平台不需要，留 All-agent 上游仓）/ [裁决-形状冲突]（两侧都有但形状对不上，见 §4 裁决项）。
> 日期：2026-09-29 · 依据本仓 AGENTS.md 改动纪律 2/3/5（逐元素注源 / schema 契约 / 每项工作一提交）。

---

## 0. 元素清点（A 侧全集，逐文件读全的登记底账）

| bohai 文件 | 元素 | 计数 |
|---|---|---|
| m1-object-model.yaml | 聚合根 AGG-BOHAI-001～010 + 聚合关联 ASSOC-BOHAI-001～007（无 data_dictionaries——字典无字典表声明，值集以 enumValues 承载） | 10+7 |
| m2-behavior-model.yaml | BH-BOHAI-RecordDailyOutput / RecordFluidTest / RecordOverhaul / RunDailyQualityCheck（4 COMMAND）+ QueryWellDailyOutput / QueryBlockMonthlyCompletion / QueryBlockWaterCut / QueryMonthlySettlement（4 QUERY） | 8 |
| m3-rule-model.yaml | RULE-BOHAI-001～020、022～035、038（无 021/036/037——号码有跳空，非缺漏） | 35 |
| m5-actor-model.yaml | ACTOR-BOHAI-001～003（3）+ ROLE-BOHAI-001～008（8）+ PERM-BOHAI-\*（8） | 19 |
| m6-flow-model.yaml | FLOW-BOHAI-001～003（含 22 个活动 ACT-BOHAI-101～106/201～208/301～308＝6+8+8，活动为流程内嵌结构非独立元素） | 3 |
| m7-report-model.yaml | QR-BOHAI-001～004（含 COND-BOHAI-001～006 条件内嵌） | 4 |
| glossary-model.yaml | GLS-BOHAI-001～010 | 10 |
| **合计** | | **96 元素**（+1 invariant、3 处 M1 refRules 内嵌约束——AGG-002.waterCut/openDays 值域＋AGG-009.splitCoefficient 值域） |

---

## 1. 总覆盖矩阵（平台七域 × bohai 模型）

覆盖度判据：**全**=平台域清单全量有 bohai 承载；**部分**=有承载但非全量（分数=直配数/平台条目数）；**无**=零直配。引用面（跨模型 ref 指到该模型）不计入承载。

| bohai 模型 ↓ / 平台七域 → | 术语（11） | 指标（15） | 对象（10） | 关系（5） | 白名单（4） | 工作流（10） | Action（3） |
|---|---|---|---|---|---|---|---|
| **M1 对象** | 无 | 部分（14/15 的事实源承载属性） | **部分 6/10** | **部分 3/5** | **部分 3/4** | 无（businessObjectRefs 引用面） | 无 |
| **M2 行为** | 无 | 部分 4/15（QUERY 出口，M7 一对一） | 无（ownerEntity 引用面） | 无 | 无 | 无（BEHAVIOR_CALL 引用面） | 无（0/3，形状不同源） |
| **M3 规则** | 无（仅描述级术语注记） | **部分 14/15**（13 规则直配+1 事实承载） | 无（sourceField 引用面） | 无（splitCoefficient 引用面） | 部分 1/4（#3 双键容差判据） | 无（ruleRef 引用面） | 无 |
| **M5 主体** | 无 | 部分（3/3 负责人枚举值的 Owner 承载） | 无 | 无 | 无 | 无（roleRefs 引用面） | 无（平台受控写入权限面在 D3/m8） |
| **M6 流程** | 无 | 无（步骤内指标引用面） | 无 | 无 | 无 | **部分 2/10** | 无 |
| **M7 报表** | 无 | 部分 4/15（指标 1/2/5/11 查询出口） | 无（objectRef 引用面） | 无 | 无 | 无 | 无 |
| **GLS 术语** | **全 10/11** | 无 | 无（relatedObjectRefs 引用面） | 无 | 无 | 无 | 无 |

读法：对角线集中——M1↔对象/关系/白名单、M3↔指标、GLS↔术语、M6↔工作流、M2/M7↔指标出口、M5↔指标 Owner 面；M2↔Action 是唯一**形状不同源**的域对（不是缺口是异族，见 §4 裁决项前注）。九张业务表台账聚合（AGG-BOHAI-002～008）不占 C1 对象账行——它们由 A2 映射卡/99 §2.0 中台只读路由消费（平台侧不建镜像表），属对齐而非缺口。

---

## 2. 元素级对账（逐域展开）

每行三元组：平台合同锚 / bohai 元素 id / 设定书 §。bohai 侧裁决引用以 PROP-\* 标注（只引不重写）。

### 2.1 术语域（平台 11 条 ↔ GLS 10 条）

| # | 平台（C1 端点 2 TERMS） | bohai | 设定书 § | 状态 | 注记 |
|---|---|---|---|---|---|
| 1 | 老完成率（禁用词） | GLS-BOHAI-001 | §6 | [复用-direct] | 平台 status 串「禁用（替代：产量完成率）」＝GLS status 原文；GLS banned-term 闸（schema §11）即平台 sem_term `status_key='禁用词'` 的本体执行面 |
| 2 | 剔检产量（别名→净产量） | GLS-BOHAI-002（aliases:[净产量]） | §6 | [复用-direct] | 平台 type 串「别名 → 净产量」＝GLS termType+aliases 的展示拼装（可逆投影） |
| 3 | 有效产量（一词两译） | GLS-BOHAI-003 | §6 | [复用-direct] | 一词两译的**指标侧**结构化（calibers）在指标域，术语侧 GLS definition 已注两支口径并列 |
| 4 | 躺井（黑话→停产待检泵） | GLS-BOHAI-004 | §6 | [复用-direct] | 「限语境」机器判定面未建——GLS notes 已如实标注，迁移保真 |
| 5 | 时率（缩写→抽油机时率） | GLS-BOHAI-005 | §6 | [复用-direct] | 公式锚 RULE-BOHAI-017 随迁 |
| 6 | 水淹层（术语） | GLS-BOHAI-006（relatedObjectRefs:[]） | §6 | [复用-direct] | 空挂不硬挂纪律保真（地质层段未扩域） |
| 7 | 递减增油（术语，待联席裁决） | GLS-BOHAI-007 | §6+§8 事故 7 | [复用-direct] | status 原文「有效（待联席裁决）」两侧一致 |
| 8 | 存水率（术语） | GLS-BOHAI-008 | §6 | [复用-direct] | 指标化未建注记随迁（RULE-BOHAI-008 描述承载） |
| 9 | 配注合格率（术语） | GLS-BOHAI-009 | §6 | [复用-direct] | 同上（分母/目标双侧缺注记） |
| 10 | 三多四难（治理热词） | GLS-BOHAI-010 | §6 | [复用-direct] | 语义 Owner 域外热词，C1 术语账有行——迁 |
| 11 | 日产液（别名→日产液量，已届满） | **无** | §6 **无此条**（页面增补行，真实源 PRD F60/U09 A1.13-A1.15；C1 出入对账 4 已如实标注） | [增补-bohai无] | **裁决项 c**：无设定书锚不建，先裁内容侧 |
| 结构差 | `status_key` 六值枚举 / `expires_at`（F60 机器判）/ `expired` 派生 / version v1 | GLS 有 status 串+元素级 version 预留位；**无 expires_at 字段** | — | [增补-bohai无] | 六值可由 status 串映射；expires_at 是结构缺口（联动裁决项 e/g） |

### 2.2 指标域（平台 15 条 ↔ M3 指标规则 13 直配 + 事实承载 1 + 无 1）

| # | 平台（C1 端点 3/4 METRICS） | bohai | 设定书 § | 状态 | 注记 |
|---|---|---|---|---|---|
| 1 | ★产量完成率 | RULE-BOHAI-009（+RULE-BOHAI-022 配产取版联动） | §3 指标 1 | [复用-direct] | 分母口径 PROP-BOHAI-009=A 随规则迁 |
| 2 | ★有效产量（两支口径） | RULE-BOHAI-019（剔检支+开井日历支双口径） | §3 指标 2+§A.4 | [复用-direct] | 平台 calibers A/B 两支与 RULE-019 双口径同构——平台 `calibers`/`default_caliber` 的 bohai 真源就是本规则 |
| 3 | ☆自然递减率 | RULE-BOHAI-013 | §3 指标 3 | [复用-direct] | 年化支 PROP-BOHAI-030 已裁对数线性回归 |
| 4 | ☆综合递减率 | RULE-BOHAI-014 | §3 指标 4 | [复用-direct] | |
| 5 | ☆综合含水率 | RULE-BOHAI-010（+RULE-BOHAI-029 取样前置） | §3 指标 5 | [复用-direct] | Q_w 换算 PROP-BOHAI-031=B′ 化验校正已落 |
| 6 | ☆注采比 β | RULE-BOHAI-011 | §3 指标 6 | [复用-direct] | 剥法留 β——bohai 规则 name 为纯名「注采比」，平台台账名带 β 尾缀（联动裁决项 e） |
| 7 | ☆累积亏空 | RULE-BOHAI-012 | §3 指标 7 | [复用-direct] | 累计口径起点待 Owner 注记随迁 |
| 8 | ☆措施有效率 η | RULE-BOHAI-034 | §3 指标 8 | [复用-direct] | PROP-BOHAI-024 判据已补 |
| 9 | ☆措施有效期 T | RULE-BOHAI-015 | §3 指标 9 | [复用-direct] | 缺失行不入分母 PROP-BOHAI-017 |
| 10 | ☆递减增油 | RULE-BOHAI-018 | §3 指标 10+§8 事故 7 | [复用-direct] | 基线参数 PROP-BOHAI-018、使用边界（限井组·年内部评估）随迁；平台双徽标（生效中+待联席裁决）＝GLS-BOHAI-007 同源状态 |
| 11 | ★商品量 | AGG-BOHAI-008.netWeight + QR-BOHAI-003（**事实承载型：无计算规则**）+ RULE-BOHAI-031 对账容差 | §3 指标 11+§A.8 | [复用-direct·形状注记] | 口径仲裁 PROP-BOHAI-020（井口/商品量并存披露）；同步器投影 sem_metric 行需支持"事实承载型"指标（def 取对象属性语义而非规则公式） |
| 12 | ☆机采系统能效 | RULE-BOHAI-035 | §3 指标 12 | [复用-direct] | 三级公式 PROP-BOHAI-025；档值=规则参数待 Owner（不进本体，随迁注记） |
| 13 | ☆检泵周期 | RULE-BOHAI-016（+RULE-BOHAI-024 跨月切割） | §3 指标 13+§A.4 | [复用-direct] | |
| 14 | ☆抽油机时率 | RULE-BOHAI-017（+RULE-BOHAI-023 联动） | §3 指标 14 | [复用-direct] | |
| 15 | ☆桶油增产成本 | **无** | §3 指标 15（分子=措施总投入，ERP 无承载字段——bohai step5-fidelity 未建，FLOW-BOHAI-002 步骤 7 停在建注记） | [增补-bohai无] | 6.29 桶/m³ 换算系数已随 RULE-BOHAI-018 注记在仓；缺的是分子承载——建规则待 ERP 源素材（同 FLOW-002 停建条件） |
| 结构差 | `mark`(★☆)/`slot_name` 剥法/`grain`/`unit`/`modifiers`/`ambiguous`/`calibers`/`default_caliber`/`dispute`/`version v3` | M3 规则无上述口径登记字段（name 纯名、公式在 expression、Owner 在 M5 角色） | §3 指标卡原文有修饰词/粒度/单位栏 | [增补-bohai无] | **裁决项 e**（slots 剥法与字段落位）；指标 Owner 三值↔M5 三角色（见 2.2 尾注）；version v3 为演示种子值（C1 如实标注，无设定书锚） |

尾注：C1 `METRIC_OWNERS` 三值（开发室/采油工艺所/销售计量站）与 M5 ROLE-BOHAI-003/004/005（业务 Owner 产量/措施/经营口径）一一对应——指标 Owner 字段的本体承载位在 M5，[复用-direct]。联席/复合负责人两行（#10 联席、#15 ＋财务）在 bohai 侧＝RULE-BOHAI-018 描述「联席」与 GLS-BOHAI-007「待联席裁决」注记，结构化多值 Owner 平台侧未裁（C1 开放问题 2，不在本矩阵裁决）。

### 2.3 对象域（平台 10 个 ↔ M1 10 聚合）

| # | 平台（C1 端点 5 OBJECTS，全草案态） | bohai | 设定书 § | 状态 | 注记 |
|---|---|---|---|---|---|
| 1 | 井 | AGG-BOHAI-001 | §5+§A.1 | [复用-direct] | A2 端点 2 档案 8 字段与 AGG-001 属性一一对应（well_id/well_name/well_type EW·IW/first_prod_date/platform/block_name/current_status/remark）；井状态四枚举两侧同源（§A.1） |
| 2 | 井筒（段/射孔/防砂） | **无** | §5 实体清单 | [增补-bohai无] | 属性素材 §5 原文有（段/射孔/防砂）；bohai 未建因 8 表无源表——维形位可建（裁决项 b 同批） |
| 3 | 区块 | AGG-BOHAI-010（维形位） | §5+§2.2 | [复用-direct] | PROP-BOHAI-013 族首补建；densityBenchmark（渤南 0.86/渤中 0.89/渤西 0.91）随迁 |
| 4 | 油田 | **无**（D8 裁不提升——fieldName 保持行内冗余） | §5 | [增补-bohai无] | **裁决项 b**：平台对象账需行，bohai 有明示裁决不建——需 Owner 重裁或维形位 |
| 5 | 平台 | **无**（AGG-001.platform String 属性已够用裁决） | §5 | [增补-bohai无] | **裁决项 b**：同上；现值样本 CEP-A/CEP-B（§A.1/B5） |
| 6 | 设备 | AGG-BOHAI-007 设备状态记录 | §5+§A.7 | [复用-direct·形状注记] | §5 实体「设备」vs bohai 台账记录聚合（时点状态）——A2 拍板 2026-09-27「设备/措施不升级为对象类型，保持台账类型枚举承载」，C1 对象行与 bohai 聚合的台账面承载自洽 |
| 7 | 措施 | AGG-BOHAI-005 井措施记录 | §5+§A.5 | [复用-direct·形状注记] | 同上；措施类型四枚举两侧同源（§A.5） |
| 8 | 化验样 | AGG-BOHAI-006 流体化验记录 | §5+§A.6 | [复用-direct] | |
| 9 | 受效关系 | AGG-BOHAI-009 | §5 | [复用-direct] | 平台 attr 描述（注水井→受效油井多对多；劈分系数 Σ=1、响应起始日）与 AGG-009 属性+invariant 逐字对上；99 §2.3 已预留 `well_effect_relation` 待装配表（与 PROP-BOHAI-021 无源虚拟实体裁决互补，见 §6 发现 4） |
| 10 | 配注层 | **无**（同族裁不建） | §5（未列属性） | [增补-bohai无] | **裁决项 b**；§5 未列属性，建行即空壳 |
| 反向 | 平台对象账无行的 6 聚合：日产计量/注水日计量/井检修记录/井措施记录/流体化验记录/区块月度结算 | AGG-BOHAI-002～008 | §A.2～A.8 | [复用-direct] | 不占 C1 对象账行——消费面＝A2 映射卡 8 表落点 + 99 §2.0 中台只读路由（平台不建镜像），非缺口 |

### 2.4 关系域（平台 5 条 ↔ M1 关联/关系实体）

| # | 平台（C1 端点 6 RELATIONS） | bohai | 设定书 § | 状态 | 注记 |
|---|---|---|---|---|---|
| 1 | 井 —隶属→ 区块 —隶属→ 油田 | 区块段＝AGG-BOHAI-001.blockName 属性承载（引用化待影响分析，M1 头注悬置）；油田段＝**无** | §5 | [裁决-形状冲突] | 平台关系账需显式两段；bohai 区块段是属性非边——**裁决项 b** 联动（对象提升后 blockName→blockRef 改造走影响分析） |
| 2 | 平台 —承载→ 井 | **无**（platform String 属性） | §5 | [增补-bohai无] | **裁决项 b** 联动 |
| 3 | 注水井 —受效→ 油井 | AGG-BOHAI-009 受效关系（多对多经 ASSOC-BOHAI-006/007 两条一对多展开） | §5 | [复用-direct] | B5 受效边 note「劈分系数合计＝1·响应起始日随台账」＝AGG-009 invariant+responseStartDate；A2 tail「受效井清单未装配」与 99 `well_effect_relation` 待装配同义 |
| 4 | 措施 —作用于→ 井 | ASSOC-BOHAI-004（井 1..\* 井措施记录，wellRef） | §5+§A.5 | [复用-direct] | B5 边 note「批次 20260911-T3」注源 §A.4 |
| 5 | 化验样 —取样自→ 井 | ASSOC-BOHAI-005 | §5+§A.6 | [复用-direct] | B5 演示配置未收录本标签（出入对账 3 如实标注）——本体侧有承载，缺口在抽取配置侧 |
| 反向 | 平台关系账无行：井 1..\* 日产计量/注水日计量/井检修/井措施/化验（ASSOC-001～003/004/005 的事实表关联） | ASSOC-BOHAI-001～005 | §5 Join 白名单 | [复用-direct] | 消费面＝映射卡/Join 判据，非 §5 实体关系清单——非缺口 |

### 2.5 白名单域（平台 4 行 ↔ M1/M3 承载）

| # | 平台（C1 端点 7 WHITELIST） | bohai | 设定书 § | 状态 | 注记 |
|---|---|---|---|---|---|
| 1 | 日产计量 ⋈ 井档案 可以·用井号连 | ASSOC-BOHAI-001（referenceField: wellRef） | §5 ✓ | [复用-direct] | ASSOC.referenceField 即 join_key 的本体语义位（联动裁决项 f） |
| 2 | 日产计量 ⋈ 日期维表 date_dim 可以·按日期连 | **无**（无日期维对象） | §5 ✓ | [增补-bohai无] | date_dim 是中台维表，非 8 表业务实体——对象账亦无此行；本体承载两案见裁决项 f |
| 3 | 日产计量 ⋈ 化验样 默认不给·双键+时间容差经清洗层视图 | AGG-BOHAI-006 description + RULE-BOHAI-002 描述 | §5 ✗ | [复用-direct] | 「须井号＋取样日期双键＋时间容差经中间视图」判据已在 RULE-002 description 逐字承载 |
| 4 | 日产计量 ⋈ 注水日报（直连）默认不给·经受效关系中转 | AGG-BOHAI-003 description + AGG-BOHAI-009 | §5 ✗ | [复用-direct] | 「oil ⋈ 注水直连禁止须 AGG-009」在两侧 description/裁决注记同文 |
| 结构差 | `left_table`/`right_table` 机器键 + `verdict` 两值（99 §2.8 sem_join_whitelist） | bohai 白名单语义散在 description/ASSOC，无结构化登记 | — | [增补-bohai无] | 同步器投影需结构化行——登记位见裁决项 f |

### 2.6 工作流域（平台 10 条 ↔ M6 3 流程）

| # | 平台（C1 端点 8/9 WORKFLOWS） | bohai | 设定书 § | 状态 | 注记 |
|---|---|---|---|---|---|
| wf1 | 《产量下滑归因》登记·账号「产量分析」 | FLOW-BOHAI-001 | §7 剧本 1 | [复用-direct] | 登记卡五要件（开工条件/步骤/缺参策略/人工确认点/输出合同）与 FLOW-001 trigger+activities+description 逐项对上；步骤「用指标 3/8/10」＝activities 内 ruleRef **RULE-013** 直挂（指标 3，ACT-103；指标 8/10 为步骤语义引用面，规则真源 RULE-034/018 在 M3——RULE-018 的 ruleRef 挂 FLOW-002 非 001） |
| wf2 | 《注水井措施评估》草案 | FLOW-BOHAI-002 | §7 剧本 2 | [复用-direct] | 平台 SCRIPT_STEPS 八步＝FLOW-002 activities 序（王飞 11 步教学压缩两侧同构）；「归档进已验证指标证据」=ACT-BOHAI-207（落库行为二期补注记随迁） |
| wf3 | 《档案质量体检》草案 | **无直配**（FLOW-BOHAI-003 质量问题单闭环为语义近邻但不同流程） | 无设定书直锚（F19 触发三路页面落位值，C1 如实标注） | [增补-bohai无] | FLOW-003 的分发→认领→整改→复核→关闭闭环由 E2 问题单五态状态机承接（E2 端点 7/99 §2.12 quality_issue）——流程本体迁 petro 后消费锚在 E2 非 C1 工作流域 |
| wf4 | 《复产确认检查》草案 | **无** | 无直锚（F19 触发三路落位值；A3 变动单 #WB-20260926-05 提出人） | [增补-bohai无] | |
| wf5–wf7、wf9、wf10 | 低产井措施筛查/机采井工况诊断/区块注采平衡评估/平台运行周报/月度统计对账（全项未登记占位行） | **无** | 无直锚（占位行） | [增补-bohai无] | 建行即空壳登记卡（五要件全 null），同步器种子照 C1 占位语义如实导入 |
| wf8 | 《幻觉拦截周报》草案 | **无** | 无直锚（F19 周期回放落位值） | [增补-bohai无] | |
| 结构差 | `status`（登记/草案账号绑定两态）/`account`/`registered_items` n/5/`card.meta` 展示串 | M6 无账号绑定/登记态字段（trigger 只分 MANUAL/BEHAVIOR/SCHEDULE/SUB_FLOW） | — | [裁决-形状冲突] | **裁决项 d**：schema 不承载则同步器投影层装配 |
| 反向 | 平台工作流域无条目：质量问题单闭环 | FLOW-BOHAI-003 | §1 问题单工作流+§4 质量闭环 | [复用-direct] | 消费锚＝E2 端点 7 五态状态机 + 99 §2.12 `quality_issue`——迁 petro M6，属质量域非 C1 工作流域 |

### 2.7 Action 域（平台 3 条 ↔ M2 COMMAND 零直配——形状不同源）

| # | 平台（C1 端点 10 ACTIONS，源 lessons/61·票 92） | bohai | 设定书 § | 状态 | 注记 |
|---|---|---|---|---|---|
| 1 | update_well_remark 更新井备注 | **无**（AGG-BOHAI-001 无「更新备注」行为；remarks 属性在档案 8 字段内） | 无 § 直锚（主仓 lessons/61 引用主位） | [增补-bohai无] | 平台 Action＝受控写入合同（m26 propose/execute、F47/A3 变动单执行链）——非 bohai M2 的源侧业务动作 |
| 2 | adjust_production_plan 调整配产 | **无**（planOutput 是录入面字段非调整行为） | 无 § 直锚 | [增补-bohai无] | 同上；配产取版语义已有 RULE-BOHAI-022（消费面在指标域） |
| 3 | adjust_injection_volume 配注上调 | **无**（注水录入行为未建——RULE-BOHAI-028 narrative 如实注记） | 无 § 直锚 | [增补-bohai无] | 同上 |
| 反向 | 平台 Action 域无条目的 4 COMMAND | BH-BOHAI-RecordDailyOutput / RecordFluidTest / RecordOverhaul（3 条源侧录入）+ RunDailyQualityCheck | §2.1+A.2/A.4/A.6+§4 | [复用-direct·执行面不迁] | 录入行为的**本体迁**（M3 reusedBy/M5 PERM 引用闭合不可断、E2 责任岗与脏数据来源语义消费），**执行面不迁**——平台无源侧录入面（Action 受控写入 3 条不含），执行归源系统/中台 ETL（PROP-BOHAI-011(b) 同款位置逻辑）；RunDailyQualityCheck 的平台消费面＝E2 端点 3 质检任务（POST /api/quality/tasks 四步流水），非 C1 Action 域 |

---

## 3. 三清单（核心交付物）

### 3a. 复用清单——直接迁 `petro/` 平台域的元素（保留裁决引用 PROP-BOHAI-\*）

**共 96 元素**：M1 17（10 聚合+7 关联）· M2 8 · M3 35 · M5 19（3 actor+8 role+8 perm）· M6 3 · M7 4 · GLS 10。内嵌结构随元素走（M1 refRules/invariants、M6 activities、M7 conditions、GLS aliases）。

| 模型 | 元素（id 全列） | 迁移去向锚 |
|---|---|---|
| M1 | AGG-BOHAI-001～010（属性/refRules/invariants 随行）；ASSOC-BOHAI-001～007 | C1 对象账（001/007/005/006/009/010 六行投影）· A2 档案 8 字段与映射卡 8 表 · 99 §2.0 中台只读路由 · B5 受效边语义 |
| M2 | BH-BOHAI-RecordDailyOutput/RecordFluidTest/RecordOverhaul/RunDailyQualityCheck/QueryWellDailyOutput/QueryBlockMonthlyCompletion/QueryBlockWaterCut/QueryMonthlySettlement | E2 质检任务（RunDailyQualityCheck）· M7 一对一查询出口（P1 一致性对）· 录入三条＝源侧语义登记（执行面不迁，见 2.7 反向行） |
| M3 | RULE-BOHAI-001～020、022～035、038（35 条全列） | E2 规则库（1～12 直配 9 条+提取件二 R-13～R-20 对总册族 5 条）· C1 指标 15 条中 13 条的口径真源 · 白名单 #3/#4 判据 |
| M5 | ACTOR-BOHAI-001～003 · ROLE-BOHAI-001～008 · PERM-BOHAI-RecordDailyOutput/RecordFluidTest/RecordOverhaul/RunDailyQualityCheck/QueryWellDailyOutput/QueryBlockMonthlyCompletion/QueryBlockWaterCut/QueryMonthlySettlement | C1 指标 Owner 三值（ROLE-003/004/005）· E2 责任岗（采集管理员/质量管理员）· P2 权限回指一致性对 |
| M6 | FLOW-BOHAI-001～003 | C1 工作流 wf1/wf2（登记卡五要件）· E2 问题单五态（FLOW-003） |
| M7 | QR-BOHAI-001～004 | A1 verified metric 固定 SQL 模板种子（指标 1/2/5/11 出口）· 问数解释链 |
| GLS | GLS-BOHAI-001～010 | C1 术语账 10 行 · banned-term 拦截面（平台侧消费＝问数链禁用词拦截） |

### 3b. 增补清单——平台有 bohai 无，须新建（元素级 20 + 结构级字段组）

| # | 缺口 | 平台锚 | 缺口明细（设定书侧素材状态） | 建议落点 |
|---|---|---|---|---|
| 1 | 术语「日产液」 | C1 TERMS #11 | **无设定书锚**（§6 实为 10 条；真实演示源 PRD F60/U09）——先裁内容侧再建（裁决项 c） | GLS-BOHAI-011（add 提案） |
| 2 | 指标「桶油增产成本」 | C1 METRICS #15 | §3 指标 15 原文在案；分子（措施总投入）无承载字段——ERP 源素材缺（FLOW-002 步骤 7 同停建条件）；6.29 桶/m³ 换算系数已有注记 | M3 计算规则（素材到再建）+ 同步器种子先以 dispute「经营×技术联席」如实投影 |
| 3 | 对象「井筒」 | C1 OBJECTS #2 | §5 属性素材有（段/射孔/防砂）；8 表无源表 | M1 维形位（属性登 §5 原文） |
| 4 | 对象「油田」 | C1 OBJECTS #4 | §5 未列属性；bohai D8 裁不提升（fieldName 行内冗余） | **裁决项 b** |
| 5 | 对象「平台」 | C1 OBJECTS #5 | §5 未列属性；bohai 裁 String 属性已够用 | **裁决项 b** |
| 6 | 对象「配注层」 | C1 OBJECTS #10 | §5 未列属性；同族裁不建 | **裁决项 b**（建行即空壳） |
| 7 | 关系「区块 —隶属→ 油田」段 | C1 RELATIONS #1 后段 | 对象 4 未建故边无从立 | **裁决项 b** 联动 |
| 8 | 关系「平台 —承载→ 井」 | C1 RELATIONS #2 | 对象 5 未建故边无从立 | **裁决项 b** 联动 |
| 9 | 白名单 #2「oil ⋈ date_dim」 | C1 WHITELIST #2 | date_dim 中台维表非业务实体，对象账亦无行 | 白名单结构化登记（裁决项 f；不建 DICT/对象） |
| 10–17 | 工作流 wf3–wf10 八条 | C1 WORKFLOWS | wf3/wf4 有开工条件+输出合同、wf8 仅开工条件（页面 regCount 演示值：wf1=5、wf2/3/4=2、wf8=1、wf5/6/7/9/10=0——C1 册行为规则 10「wf3/4/8 开工条件与输出合同」与其常量表 regCount 演示值相抵，按页面现值为准，C1.jsx wf8 contract=null；F19 触发三路落位值，无 § 直锚）；wf5/6/7/9/10 全占位 | M6 新流程（有素材两条）或登记占位（五条）——种子照 C1 如实导入 |
| 18–20 | Action 三条 | C1 ACTIONS | 注册名+业务名（lessons/61·票 92 引用主位，无 § 直锚） | 平台 Action 合同独立登记（**裁决项 f 尾注**：不进 M2 行为模型——受控写入与源侧动作两族） |
| 结构级 | `mark`/`slot_name`/`grain`/`unit`/`modifiers`/`ambiguous`/`calibers`/`default_caliber`/`dispute` | C1 端点 3/4 + 99 sem_metric 列 | 指标口径卡八项的结构化登记位 | **裁决项 e** |
| 结构级 | `status_key` 六值/`expires_at`/`expired` | C1 端点 2 + 99 sem_term 列 | GLS 有 status 串可映射六值；expires_at 无承载（F60 机器判需日期） | **裁决项 e/g** 联动 |
| 结构级 | `status` 登记草案/`account`/`registered_items`/`card` 七项 | C1 端点 8/9 + 99 sem_workflow 列 | M6 trigger/activities/description 可映射 card 大半；账号绑定两态无承载 | **裁决项 d** |
| 结构级 | 白名单 `left_table`/`right_table`/`verdict` 机器键 | C1 端点 7 + 99 sem_join_whitelist | bohai 语义散在 description | **裁决项 f** |
| 结构级 | 映射卡 join_key 四件套（ingest_mapping.mapping jsonb） | 99 §2.12 ingest_mapping + CONTEXT「映射卡」 | ASSOC.referenceField 已承载一跳直连语义位 | **裁决项 f** |
| 结构级 | ENTITY_GROUPS 实例名册（区块/平台/井实例值） | C1 端点 11 domain=entities | **实例层数据**（渤南/渤中/CEP-A/CEP-B/N-02…）——本体=模式层，实例名册不进本体仓（CONTEXT「本体 vs 知识图谱」） | 平台侧装配（B5 图谱/数据面种子），同步器不投影 entities domain |

### 3c. 不迁清单——bohai 有但平台不需要，留 All-agent 上游仓

| # | 项 | 级别 | 理由 |
|---|---|---|---|
| 1 | M1 九处事实聚合的 `wellId` 冗余键属性（与 wellRef 双表示的转写残留，M1 头注原文「是否以 wellRef 吸收待 Owner 确认」） | 属性级 | 平台侧引用结构＝wellRef 语义引用（99 §2.0 归一化主键路由）；冗余键是「键结构保真」转写残留，**不迁冗余**——以 wellRef 承担引用，清理属 ID/键变更逐处过影响分析（M1 头注纪律），不是删元素 |
| 2 | M2 三条源侧录入行为的 USER_ACTION 执行语义 | 执行语义级 | 元素本体迁（引用闭合+质检消费面），但「平台执行该写入」不成立——平台无源侧录入面（Action 合同 3 条不含、生产域 8 表 as-is 在中台不建镜像）；执行归源系统/中台 ETL（PROP-BOHAI-011(b) 同款位置逻辑） |
| 3 | ACTOR-BOHAI-003 的 `cadence: 15 分钟级闭环调度` 属性值 | 注记级 | 15 分钟级是**源系统 ETL 调度事实**（§2.1 原文）；平台质检触发形态＝数据面 dp3 进料管道自动触发+手动补扫（E2 端点 3 真实实现注记），非 15 分钟跑批——actor 本体迁，cadence 值留源侧语义注记不接平台运行面 |
| 4 | GLS 各条 notes 内的 All-agent 仓对账路径（step5-fidelity/lessons/41 等） | 注记级 | notes 字段本身随元素迁（人读追溯用），但仓内路径指向 All-agent 上游仓工件——迁入 petro/ 时改写为上游引用或保留原文加「上游仓」前缀，不当成本仓真源路径 |
| 元素级合计 | **0 条硬不迁** | — | bohai 与平台合同同源（同一设定书 R5），96 元素全部有平台消费面或引用闭合需求——「不迁」实际发生在属性级/执行语义级/注记级，无整元素弃置 |

---

## 4. 单独裁决项（每项两案+建议倾向，**不拍板**——Owner 裁决后进 fork 批）

**前注（M2↔Action 域对）**：这不是缺口是异族——bohai M2 COMMAND=源侧业务动作（行为证据注源 §2/A.x），平台 Action=受控写入合同（m26/F47/A3，注册名+业务名两段）。CONTEXT「本体双通道」已定分界：消费通道执行 action 写数据（受控写入），管理通道改类型定义。两族并立，不互迁。

### a. F40 的 11 类抽取实体类型与本体模式层的边界

- **现状**：F40 默认 11 类通用实体（Person/Organization/Location/Product/Event/Date/Work/Concept/Resource/Category/Operation）＝ExtractConfig 出厂默认（B5 合同常量冻结原文）；演示库已换 5 类领域类型（井/区块/平台/油田/措施）；B5 铁律类型闸「抽取类型清单对不上领域术语表的不立边」；CONTEXT「抽取式图谱」条目原文把 11 类定位为 WeKnora 式弱模式层（通用、无规则、改 prompt 无审）。
- **案 1**：11 类不进本体仓——类型闸对号面只用领域类型清单（C1 对象账＝petro M1 投影 + B5 对号表），11 类留平台侧 ExtractConfig 出厂默认资产。
- **案 2**：11 类作为清单登记进本体仓（GLS 术语或独立模式件 patterns/ 素材区），治理对号表连通用类型一起管。
- **倾向：案 1**。11 类是抽取配置出厂值非领域本体内容；「宪法先行 vs 人口先行」的分界（CONTEXT）不应被弱模式层污染；B5 开放问题 7（对号表治理）的对号面以 C1 对象账为唯一领域面即可。patterns/ 素材区可放对号说明素材（不经语义闸域扫描），不建模型。

### b. 区块/平台/油田对象提升后的属性来源

- **现状**：区块已建维形位（AGG-BOHAI-010，PROP-BOHAI-013，属性=blockName+densityBenchmark）；油田/平台/井筒/配注层四实体 bohai 有明示裁决不建（PROP-BOHAI-013 同族：无源表无属性素材，建即空壳，素材到时另立 add 提案）；平台 C1 对象账 10 行全量需要这四行（全草案态、attr 多为「§5 未列属性」）。
- **案 1**：按 PROP-BOHAI-013 先例建维形位——油田（油田名=渤海油田，§1 渤海油田分公司唯一原文锚）/平台（platformName 属性，现值样本 CEP-A/CEP-B 注源 §A.1 不当值域枚举）/井筒（段/射孔/防砂三属性登 §5 原文）/配注层（无属性空壳）；关系账「隶属油田/平台承载」两段随之立 ASSOC；井/结算的 blockName→blockRef 引用改造走影响分析另提案（M1 头注悬置项）。
- **案 2**：本体不建，C1 对象账四行由同步器种子直插平台侧（草案态照抄），本体仓 manifest 注记差集——对象账维持「§5 草案」纯页面态。
- **倾向：案 1（限维形位+显式空壳）**。判据 ①「bohai 本体对齐平台七域」要求对象域 10/10 有本体承载；维形位属性只登设定书原文有的，值域样本（CEP-A/B 两平台、12 口井）不当枚举不发明；草案态/未落语义由同步器投影保持（C1 对象行固定值合同常量不变）。风险注记：case 1 会把「建即空壳」从裁决例外变成常规操作——须在 add 提案里逐个注明「平台对象账行需要」这一业务驱动，防空壳蔓延。

### c. GLS 术语 10 条 vs 平台 11 条的差集定位

- **现状**：差集＝平台第 11 行「日产液」（别名→日产液量，有效（已届满），expires 2026-06-30）。C1 出入对账 4：页面 src 照抄「设定书 §6」但 §6 实为 10 条，真实演示源＝PRD F60/U09 A1.13-A1.15，「是否给设定书补条目＝内容侧决策」。
- **案 1**：设定书内容侧先补条目（日产液，别名，已届满有效期）→ add 提案进 GLS（GLS-BOHAI-011）→ 台账 11 条全量仓内同源。
- **案 2**：本体仓不建；同步器首跑种子导入后，该行由平台侧种子补丁直插 sem_term，manifest 注记「术语域 11-10 差集=平台演示行」。
- **倾向：案 1（前置条件=Owner 先裁设定书内容侧）**。判据 ②「台账种子零手养」要求 11/11 全量来自仓——案 2 的种子补丁是「台账只能经正门改」的旁门变体；但无设定书锚不建是红线（本仓 AGENTS.md 纪律 2），故顺序＝Owner 补设定书 → C2 add 提案进 GLS。Owner 拍板前，fork 批按 10 条迁、manifest 登记差集。

### d. 工作流账号绑定两态/登记项 n/5 等平台字段在 all-agent M6 schema 的表达

- **现状**：平台字段＝status（登记=已绑定运行账号可被调用/草案=未绑定不可用，F19）、account、registered_items（五要件非空数）、card 七项（trigger/steps/defaults/confirm/contract/source/meta）。bohai M6 已承载 card 素材大半（triggerType/activities 步骤化/description 缺参策略与输出合同），未承载账号绑定与登记态；M6 consumers=["build"]（非运行时检索面）。
- **案 1**：M6 schema 不动——账号绑定/登记态属运行期身份治理（F19「账号绑定两态」=运行身份治理，非本体内容），同步器投影层装配 sem_workflow（card 七项从 FLOW trigger/activities/description/roleRefs 映射，account/status 从平台运行账号体系与汇入态取，registered_items 派生）。
- **案 2**：M6 schema 走演进票加可选字段（accountRef/status/cardRef），schemaVersion 升小版本（联动裁决项 g），同步器随批升版。
- **倾向：案 1**。omittedModels/豁免登记（MU 先例）是**模型级**机制（整模型不建才豁免），字段级缺位不适用该机制——学 MU 先例的正确类推是「schema 不承载、投影层表达」，不是加豁免条目；card 的 steps 真源已在 activities 结构化存在，投影映射零发明。若 Owner 判「登记态必须本体承载」再走案 2 演进票。

### e. slots 剥法（η/T/β 保留、★☆ 标记）在 YAML 的表达位置

- **现状**：C1 剥法合同＝剥首 ★/☆ → 剥尾括注（…）→ 剥尾部 η/T（β 保留），slot_name 服务端单点执行（票 93 禁止下游自留拷贝）；mark=★|☆|null；grain/unit 结构化（粒度·单位双形态）；ambiguous/calibers/default_caliber 仅 #2 登记。bohai M3 name 为纯名（「注采比」无 β、「措施有效期」无 T），无 mark/grain/unit/modifiers/dispute 字段；C1 台账原名含 β/η/T 尾缀与 ★☆。
- **案 1**：YAML 不动——mark/slot_name/grain/unit 等全在同步器投影层执行与查表；查表源＝对齐矩阵附表（本文件 §2.2 注记）或 C1 种子。
- **案 2**：走 schema 演进票（票 10 GLS 先例「元模型错→框架版本演进」路由）给 M3 规则加可选口径登记字段（grain/unit/modifiers/dispute/mark；slot_name 不存——由剥法从 name/mark 派生），name 对齐 C1 台账原名（含 β/η/T 尾缀照抄页面现值）。
- **倾向：案 2（限口径内容字段）**。F13 契约来源原文就是「指标口径 YAML 注册表——定义/修饰词/同义词/单位/owner/版本/SQL 模板」——粒度/单位/修饰词/争议注记是**指标口径的本体内容**，不是运行期派生；判据 ② 零手养要求它们在仓内有真源，案 1 会把真源逼到投影层查表（漂移风险，违「下游禁止自留拷贝」同款逻辑）。★☆ mark 是展示标记（C1 出入对账 8：非推荐位机制）可作可选字段或投影常量；slot_name 一律派生不落仓。版本号 v1/v3 为演示种子值如实标注（C1 已声明），不进本体。

### f. 映射卡 join_key 的模型归属（M2 行为 or 独立）

- **现状**：CONTEXT「映射卡」＝边↔台账表固定落点（8 张业务表全覆盖、join_key 固定、平台与中台两边共同维护）；99 §2.12 `ingest_mapping`（table_name/object_type/mapping jsonb 四件套/version）已落表；A2 关系链消费。bohai 侧：ASSOC-BOHAI-001～005 的 referenceField（wellRef）就是一跳直连 join_key 的语义位；#3 双键+时间容差、#4 中转条件在 AGG-006/003 description 与 RULE-BOHAI-002。
- **案 1**：映射卡不进八模型——join_key 语义位＝M1 ASSOC.referenceField（一跳直连），默认不给行的中转/容差条件由白名单结构化登记（sem_join_whitelist 的 how+机器键）与 M3 规则承载；平台 ingest_mapping 由同步器从 M1 ASSOC 投影装配。
- **案 2**：映射卡独立 YAML（alignment/ 附属件或新模型）承载 8 表四件套全集。
- **倾向：案 1**。all-agent 一期已裁 MM 映射模型不建（schema §0：v9 同款裁剪）；ASSOC.referenceField 与白名单 join_key 是同一事实（§5 Join 白名单）的两个登记位，独立模型会造第二真源。风险注记：#2 date_dim 与 #3 双键容差无 ASSOC 承载——案 1 下它们落在白名单结构化登记与 description，四件套完整形状由 ingest_mapping 落表侧保证（平台 dataops 投影，不倒灌本体）。

### g. schemaVersion 1.0.0 契约：all-agent schema 升级的兼容策略

- **现状**：域 manifest schemaVersion "1.0.0" 被主平台同步器钉住（本仓 AGENTS.md 纪律 4：schema 升级须与主仓联合变更——先改这里登记 CHANGELOG，再改同步器）；model-registry version 已演进至 1.2.0（GLS 票 10/必填票 13 等演进在案）；「元素级运行期预留字段存在即放行」机制保证老文件零改动兼容。
- **案 1**：1.0.0 冻结——一期全部增补走 schema 外表达（投影层/manifest 注记/素材区），裁决项 d/e 均按案 1 收敛；演进需求积累到 CHANGELOG 待联合变更批。
- **案 2**：受控升级——裁决项 e（M3 口径字段）与 c（GLS-011）以**只加可选字段**的向后兼容小版本演进（1.0.1/1.1.0），与主仓同步器联合变更批一次过（roadmap 阶段 3 合同修订批可搭车：C2 v0.2 生效链后移同批）。
- **倾向：案 2（范围收紧为可选字段小版本）**。判据 ② 零手养要求口径内容（grain/unit/modifiers/expires_at）在仓内有真源，全部推给投影层会重演「下游自留拷贝」；GLS 进 schema 先例证明版本演进路由已铺好；「存在即放行」预留闸保证 bohai 存量 96 元素零改动过闸。前提：与主仓同步器联合变更一次过、先仓后同步器（纪律 4 原文）；凡涉必填结构/换义锁定字段的演进一律不做（非向后兼容）。

### h. E2 质检规则种子与 bohai Owner 裁决的判据冲突组（本矩阵新发现，追加裁决项）

- **现状**：E2 规则种子注源设定书 §4 原文（20 条），bohai 侧同源规则已有更新 Owner 素材裁决（2026-09-21 PROP 系列）。四处冲突：

| E2 规则（种子值） | bohai（Owner 裁决） | 冲突点 |
|---|---|---|
| 规则 1：A/B 班手抄重复行即命中，去重保首条（autoFix=true·隔离） | PROP-BOHAI-007=A：行粒度=班次，各班真实产量**非重复录入**；RULE-BOHAI-030 键完整性三元组唯一、「缺失或重复行进问题单**不静默去重**」 | E2 把班次行当重复，bohai 裁为合法粒度 |
| 规则 6：批次水位 ≤T-1，超窗 reject（整批拒收） | RULE-BOHAI-025（PROP-BOHAI-016）：T-5 窗口，超窗**不拒收**、收单转问题单闭环（管理依据=月度结算关账冻结预备期） | 阈值 T-1/T-5 + 处置拒收/不拒收 双冲突 |
| 规则 11：传感器零值连续 2 小时告警（实时窗口） | RULE-BOHAI-038（PROP-BOHAI-028）：批面近似——当日批内 current 全零即告警，实时域另案 | 判据窗口形态（2 小时实时 vs 当日批面） |
| 规则 5：越界即不合格隔离（停井日矛盾行「也拦」） | 值域下沉 M1 refRules；矛盾行 RULE-BOHAI-023（PROP-BOHAI-010）：**出清单交业务核实，不拦不归零** | 矛盾行处置（隔离 vs 清单制） |

- **案 1**：bohai Owner 裁决为准——PROP-\* 是 Owner 素材确认件（时点更新、带管理依据），E2 种子是 §4 原文演绎值；同步器种子导入用 bohai 判据，E2 合同走变更记录修订（四条）。
- **案 2**：E2 冻结合同为准——bohai 四条规则走 C2 提案改判据。
- **倾向：案 1（仍须 Owner 逐条确认）**。四处 bohai 侧均为 Owner 确认裁决且附管理依据（E2 规则 1 的「去重保首条」恰是 PROP-BOHAI-007 裁决明文否定的处置）；但 E2 是 v0.3 冻结合同，本矩阵只登记冲突不擅改——修订动议交 Owner，E2 侧走变更记录，bohai 侧零改动。

---

## 5. 开放问题（Owner 裁决项汇总）

1. **裁决项 b**：油田/平台/井筒/配注层四维形位是否建（PROP-BOHAI-013 的「素材到时 add 提案」触发点是否就是 fork 批）；油田名「渤海油田」是否作维形位身份属性（§1 唯一原文锚）。
2. **裁决项 b 联动**：井/结算的 blockName→blockRef 引用改造是否随对象提升一并走影响分析（M1 头注悬置项）。
3. **裁决项 c 前置**：设定书 §6 是否补「日产液」条目（内容侧决策，C1 出入对账 4 悬置）——决定术语域 11/11 还是 10/11 同源。
4. **裁决项 d**：工作流账号绑定两态是否本体承载（案 1 投影层 vs 案 2 演进票）。
5. **裁决项 e**：M3 口径登记字段（grain/unit/modifiers/dispute/mark）演进票范围与 name 是否对齐 C1 台账原名（β/η/T/★☆ 尾缀）。
6. **裁决项 g**：schemaVersion 小版本升级时点——是否与主仓阶段 3 合同修订批（C2 v0.2）搭车一次过。
7. **裁决项 h**：E2 四处判据冲突的归一边（倾向 bohai Owner 裁决，须逐条确认后 E2 走变更记录）。
8. **AGG-BOHAI-009 ↔ 99 `well_effect_relation` 待装配表**：装配时点与中台协同（映射卡扩条目）——PROP-BOHAI-021「物理落表属源系统工程决策」与 99「列待装配、装配批启用」两条注记的接线顺序。
9. **E2 规则 13–20 通用族对账粒度**：总册规则（引用完整/跨表一致/枚举合法/正则格式/极值/波动率/钩稽/洗数规则 8 条）与 bohai 提取件二 R-13～R-20 已建 5 条（RULE-027/028/031/032/033 对其中 5 槽——波动率/极值/钩稽/枚举合法/正则格式；RULE-026 恒值滑窗对 E2 规则 10 具体规则非总册族、RULE-029 取样前置挂指标 5、RULE-030 键完整性属冲突组 h）之外的 3 条（引用完整/跨表一致/洗数规则）是否逐条进 petro M3，还是留总册文本不本体化。
10. **M7 ↔ A1 verified metric 种子形态**：QR-001～004 无 referenceSql（v9 降可选）——固定 SQL 模板种子由同步器从 M7 resultColumns/joins 派生还是补 referenceSql，阶段 1 问数链接线前裁。
11. **banned-term 拦截面投影**：GLS 禁用词闸（本仓 L4）→ 平台问数链禁用词拦截（消费侧行为）的投影面（sem_term.status_key='禁用词'）是否需在同步器输出专用禁用词清单（B5 图谱查询时三道之一；A1 统一安检三道·禁用词 0 号位先于一切解析＋ban 拦截终局场景——A1 无关 A2，A2 无术语拦截面）。
12. **指标 Owner 多值结构化**：联席/复合负责人（#10 联席、#15 ＋财务）在 M5 角色（ROLE-003/004 双挂）与 C1 owner 串（「采油工艺所（开发室联席）」）之间的映射口径——C1 开放问题 2 的本体侧表达。
13. **裁决项 a**：F40 的 11 类通用实体是否进本体仓（倾向案 1 不进——ExtractConfig 出厂默认非领域本体内容；patterns/ 素材区放不放对号说明随 fork 批定）。
14. **裁决项 f**：映射卡 join_key 的模型归属（倾向案 1——ASSOC.referenceField＋白名单结构化登记承载，独立映射模型与 schema §0「一期不做 MM 映射」裁剪裁决相抵；#2 date_dim/#3 双键容差的登记位随批定）。

---

## 6. 关键发现与对账方法注记

### 关键发现

1. **对齐度高出乎预料**：bohai 与平台七域合同同源（同一设定书 R5），96 元素**零整元素不迁**——「不迁」只发生在属性级（wellId 冗余）/执行语义级（源侧录入）/注记级（仓内路径）三处。对齐工作量集中在**结构级字段组**（指标口径卡八项、术语有效期、工作流账号绑定、白名单机器键）而非业务事实缺口。
2. **四处 E2 判据冲突**（裁决项 h）是本矩阵最大新发现：E2 种子注源设定书 §4 原文，而 bohai 侧同源规则已有更新的 Owner 素材裁决（班次粒度/T-5 不拒收/批面零值/清单制）——若不先归一，同步器种子导入会与 E2 冻结合同值打架。
3. **指标 11 商品量是「事实承载型」指标**：无计算规则，承载＝AGG-BOHAI-008.netWeight + QR-BOHAI-003 出口——同步器投影 sem_metric 行需支持 def 取对象属性语义的形态，M3 规则不是指标的唯一承载位。
4. **99 册已为受效关系预留落表位**：`well_effect_relation`（待装配，split_coefficient Σ=1 强制/response_start_date）与 bohai PROP-BOHAI-021「无源虚拟实体」裁决互补——本体概念位+平台补位表一一对应，A2 tail「未装配」如实语义两侧同构。
5. **M6 consumers=["build"]**：流程模型不在运行时检索面（semantic-service 只索引 business-core 且 M6 消费者标 build）——C1 工作流读面走同步器投影而非检索，与裁决项 d 案 1 自洽。
6. **E2 规则 13–20 通用族与 bohai 提取件二 R-13～R-20 部分重叠**（5/8 槽已有本体承载）——「总册规则本体化」已有先例，开放问题 9 顺势可裁。
7. **GLS banned-term 闸是禁用词治理的现成本体执行面**：平台 sem_term.status_key='禁用词' 的机读真源可直接由 GLS status 承载词面映射，无需新机制。

### 对账方法与局限

- 本矩阵逐元素读全 bohai 7 YAML（1696 行，wc 实测 108+266+134+624+128+208+228）与 C1.jsx（568 行）、C1/E2/B5/A2/D3/99/CONTEXT 合同全文，无抽样；每对账行注源三元组，bohai PROP-\* 只引不重写。
- 平台侧「种子实值以 C1.jsx 现值为准」（C1 合同首要裁决基准声明）已遵循；C1 如实标注的无设定书直锚演示值（版本号 v1/v3、wf3/4/8 落位值、占位行、ENTITY_GROUPS 计数）在增补清单按原语义承接，不洗白。
- 任务派单所写「99 §2.4（sem_ledger_\* 台账投影形状）」实为 **99 §2.8 semantics 域**（sem_term/sem_metric/sem_object/sem_relation/sem_join_whitelist/sem_workflow/sem_action/sem_ledger_revision/sem_version 九表；§2.4 是 approval 域）——本矩阵按实际章节引用，台账投影形状以 §2.8 为准。
- 本文件为分析件，不触发语义闸（bohai/ 不闸、petro/ 空仓跳过）；下一步＝按三清单+裁决结果 fork `petro/` 七域模型 YAML，逐元素过闸（CI 三闸全绿后成同步器拉取目标）。

---

## 7. 校核修复（独立校核批，2026-09-29）

> 校核方法：与原作者无沟通，A 侧 bohai 7 YAML 逐元素重读（id 全集 grep 对账）＋ B 侧 C1.jsx（568 行）/C1 册/E2 册＋e2.js 种子/B5/A2/D3/99/CONTEXT/设定书全文重读，与上矩阵逐行对账；E2 四处冲突逐对回查两侧原文。行内修复 8 处（§0 计数×2、§2.6 wf1 注记、§3b wf8、§5 问题 9/11、§5 补 a/f、§6 行数），其余维度零红；三清单计数经复核**不变**。

### 7.1 修复清单（行内已改）

1. §0 M6 活动 **25→22**（ACT-BOHAI-101～106/201～208/301～308＝6+8+8，grep 实测 unique activityId）；M1「7 处 refRules」→**3 处**（AGG-002.waterCut/openDays＋AGG-009.splitCoefficient 值域；invariant 1 处不变）。
2. §6 对账方法「3392 行」→**1696 行**（7 YAML wc 实测 108+266+134+624+128+208+228；3392 恰为其 2 倍，疑转写翻倍）。
3. §2.6 wf1 注记：FLOW-001 的 ruleRef 仅 **RULE-013**（指标 3，ACT-103 直挂）；RULE-018 挂在 FLOW-002（ACT-202 定口径/ACT-205 增油核算），指标 8（RULE-034）为步骤语义引用未进流程 ruleRef——原注「RULE-013/018 面」误植。
4. §3b #10–17：**wf8 仅开工条件、无输出合同**（C1.jsx wf8 contract=null；regCount 演示值 wf8=1）——C1 册行为规则 10「wf3/4/8 开工条件与输出合同」与其自身常量表 regCount 演示值相抵，按「页面现值为首要裁决基准」改为 wf3/wf4 两件全、wf8 仅 trigger。
5. §5 问题 9：对总册族 5 槽的 bohai 规则更正为 **RULE-027/028/031/032/033**（波动率/极值/钩稽/枚举合法/正则格式）——原列 RULE-026 系恒值滑窗细化（对 E2 规则 10 具体规则非总册族），且「6 个 id 对 5 槽」计数自相矛盾。
6. §5 问题 11：「A2 黑话拦下」→**A1**（问一问统一安检三道·禁用词 0 号位＋ban 拦截终局场景；grep 证实 A2 无黑话/禁用词拦截面）。
7. §5 补登**裁决项 a/f** 两行（§4 八项裁决项原汇总漏登两项，补齐 14 条）。
8. 覆盖矩阵与对账行其余抽查（术语 11 行逐行、指标 15 行逐行、对象 10/关系 5/白名单 4、 Action 3、M7 出口 4 指标、注源三元组 10 行抽核、99 §2.4=approval/§2.8=semantics 九表/§2.12=dataops 归位、A2 拍板 2026-09-27、B5 出入对账 3/受效边 note、C1 出入对账 4/8）**全部对上，零修改**。

### 7.2 E2 四处冲突逐对裁定（校核独立回查，维持原判）

| 对 | E2 侧原文（e2.js 种子/E2 册） | bohai 侧原文 | 裁定 |
|---|---|---|---|
| 规则 1 ↔ PROP-BOHAI-007（RULE-030） | 「同一口井同一天只能有一条日产记录——A/B 班手抄重复行即命中」·crit 行数＝去重后行数·autoFix=true（去重保首条） | 「行粒度=班次（PROP-BOHAI-007=A）…A/B 班各行各含当班真实产量，非重复录入」·「缺失或重复行进问题单，不静默去重」 | **冲突真实，判据相反**——键粒度（井+日 vs 井+日+班次）与处置（去重 vs 问题单）双重相反 |
| 规则 6 ↔ PROP-BOHAI-016（RULE-025） | 「≤T-1，超窗 reject」·整批拒收（§4 规则 6 原文「超窗的批次拒绝」） | 「T-5 日（管理依据：月度结算次月 5 个工作日关账，关账前 5 日数据冻结预备期）…超窗不拒收、收单转问题单闭环」 | **冲突真实，阈值＋处置双冲突** |
| 规则 11 ↔ PROP-BOHAI-028（RULE-038） | 「连续 2 小时零值告警」（实时窗口；§4 规则 11 原文即「2 小时…教学演绎」） | 「批面近似——当日批内 current 全零即告警入清单（不发明 N）…实时域另案」 | **冲突真实，判据窗口形态不同**（两侧同为告警级，非处置相反；粒度不同被误读为处置冲突的风险不存在） |
| 规则 5 ↔ PROP-BOHAI-010（RULE-023） | 「越界即不合格…停井日开井小时数仍大于 0 的矛盾行也拦」·隔离 | 值域 [0,100]/[0,24] 下沉 M1 refRules（**阈值两侧一致**）；矛盾行「标注出清单交业务核实，不归零不直改」 | **冲突真实但仅限矛盾行处置**（隔离 vs 清单制）；值域面两侧同判据，原矩阵表述「值域下沉＋矛盾行清单制」准确 |

**时效裁决**：E2 合同（v0.3，2026-09-28，票 105/107）文档时点晚于 bohai 裁决（2026-09-21），但其规则种子**内容**注源设定书 §4 原文（E2 册契约来源栏「设定书 §4（20 条）」在案，规则 6 且自注「规则原文」），未吸收 2026-09-21 Owner 素材裁决（owner-materials-2026-09-21，带管理依据）——内容新旧以素材时点论而非合同发文时点，bohai 侧更新；「倾向 bohai Owner 裁决为准＋Owner 逐条确认后 E2 走变更记录修订、bohai 侧零改动」的建议**成立**，维持原判（裁决项 h）。

### 7.3 三清单计数复核（不变）与结论

- **复用 96**：M1 17（10 聚合+7 关联）·M2 8（4 COMMAND+4 QUERY）·M3 35（001–020/022–035/038，无 021/036/037）·M5 19（3+8+8）·M6 3 ·M7 4 ·GLS 10——逐文件 grep 全集对账无误。
- **增补 20（元素级）**：术语 1＋指标 1＋对象 4＋关系 2＋白名单 1＋工作流 8＋Action 3＝20；结构级 6 组不变。
- **不迁 4**：属性级 1（wellId 冗余）/执行语义级 1（源侧录入）/注记级 2（cadence、仓内路径）——元素级 0 不变。
- **结论**：修复后本矩阵可作为 fork `petro/` 七域模型的蓝本——元素清点、注源三元组、99 §2.8 归位、八项裁决项两案与倾向经独立校核零余红；fork 批开工前待 Owner 过 §5 十四项裁决。
