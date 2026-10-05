# R-MAIN 全量审查回报（阶段 2 收官·批 2/3——主仓后端合并态）

PROTOCOL 骨架：
- **审查对象**：主仓 `/Users/divh/Downloads/petro-agent-platform` master 合并态（任务指定 HEAD=5a6027e；实际 HEAD=**398ba20**＝5a6027e 之上仅一件 gitignore 提交「补根级 node_modules 排除」，审查范围内代码状态与 5a6027e 等价——登记备查）。范围＝阶段 1 修复批＋阶段 2 十四票全合入的 `app/`＋`migrations/`，七节（见下）。
- **审查方式**：全程只读，永不改代码；测试/闸独立复跑（PG16@5433 在场——docker `petro-agent-platform-pg-1`，库 petro）；dev 主库取证全部经 `docker exec … psql` 只读 SELECT/\d；teach 真源（specs/api/A2 v0.2、B4 v0.4）只读引用未复制正文；工作区 Owner 私产（eval/、dispatch/、tickets/）与并行 UI 已提交件零接触（本回报文件为任务指定的唯一写入物）。
- **零修复声明**：本审查未对主仓做任何代码/配置/数据变更（末节重申）。

---

## 0. 环境与复跑记录（交付闸面）

| 项 | 结果 | 判定 |
|---|---|---|
| `uv run pytest -q`（未设 TEST_DATABASE_URL） | **870 passed, 75 skipped** in 22.18s | ✅ 与基线一致 |
| `TEST_DATABASE_URL=postgresql+asyncpg://petro:petro@localhost:5433/petro uv run pytest -q` | **941 passed, 4 skipped** in 53.94s | ✅ 与 941+4 基线一致 |
| `uv run python tools/contract_coverage.py check` | 合同覆盖率闸绿：169 条合同端点双向对账通过 | ✅ |
| `uv run python tools/debt_markers.py check` | 债务标记闸绿（web 源码 32 条全携可解析 DEBT 标签） | ✅ |
| `uv run lint-imports` | Analyzed 114 files, 533 dependencies——**5 kept, 0 broken** | ✅ |
| `uv run mypy app`（strict） | Success: no issues found in 76 source files | ✅ |
| `uv run ruff check app tests tools migrations` | All checks passed! | ✅ |
| `uv run ruff check .`（根全仓） | **26 errors——全部在 `ontology/tools/*.py`**（见发现 F-04） | ⚠️ 归属缝隙 |
| alembic heads / history | 单头 **0017**；线性 base→0001(空)→…→0013→**0016**→**0014**→**0015**→**0017** | ✅ |

---

## 1. 第 1 节 chat 域 17 链整体回归面——通过（P1F 四语义在阶段 2 改动后全部成立；两接缝专项核过；发现 F-01/F-03/F-05/F-06）

**阶段 1 修复批语义逐条复核**：

| 修复项 | 复核证据 | 判定 |
|---|---|---|
| P1F-01 接线回退 | `_verify_chain_wiring`（service.py:1421–1434）单源，ask 主路径（:377–380）、resume 重判（:727–730）、审批回流（:860–863）三路共用——「已注册四链绝不覆写」由构造保证；注册面＝分派器 dict（service.py:188–191 四链） | ✅ 成立 |
| P1F-02 词条卡 | 装卡单源 `_assemble`（service.py:1065–1099，@ 锚定序补卡＋匹配器行装卡＋term/metric 双去重）；生成窗材料块前置（chains.py:476–482）；兜底诚实判定 `_ledger_entries`（chains.py:952–974）；状态标注串经 `term_card_status_note`→`semantics.term_expiry` 单源（domain.py:425–447） | ✅ 成立 |
| P1F-03 早停收窄 | S3 台账命中不停下级（chains.py:217–241——命中只进 evidence、S4/S5 照跑）；S1 锚定早停跳 S3/S4/S5 各出归因 skip 帧（:239–241/:275–277/:291–293——每级一帧对称）；S0/S2/S6/S7 不受早停影响（S6/S7 无 skip 分支）；出口配置核对行明义「早停＝开（@锚定级命中即跳）· S3 命中不停下级」（chains.py:553–559） | ✅ 成立 |
| P1F-06 低分带 | 判定单源 `in_rescore_band`（domain.py:799–810，下沿 0.30 固定/上沿随 D2 refuse_threshold）；第一道放宽重评纯代码（chains.py:635–656，topK×2 封顶 64，重评路不触发精排打分）；第二道 LLM 改写仅一次（caller=chat.query.rewrite，chains.py:659–672）；额度用完自动按优化句作答＋写死标注（:397–413、:519–525）；skip_rescore 回流跳过（service.py:466–477→:739） | ✅ 成立 |

**接缝专项一：P2-03 分池 × M-06 问数链 query_store——共用常量且互不干扰，确认**：
- 分池常量单源 chat/domain.py:786–791（`EVIDENCE_CAP=4`／`LEDGER_EVIDENCE_CAP=2`／`LEDGER_EVIDENCE_SOURCES={faq,anchor,ledger}`）；唯一实施点 `chains._cap_evidence`（chains.py:606–632——两池各自截各自上限、保持分池前全局序只丢不重排、溢出 notice 报告类在前）。
- M-06 问数链全链（chains.py:1037–1355）**零消费分池常量**——其限量族独立（`QUERY_DEFAULT_LIMIT=50`/`QUERY_LIMIT_CAP=200`，domain.py:1121–1122）；query_store.py（agg 三表只读执行）只消费 plan 与 M-01 两步缝，无证据池概念。互不干扰成立。
- S6 注记/重评注记/配置核对行三处帧面文案全部 f-string 引用同一常量（chains.py:351–353/:410–411/:434–437/:558）——跨票口径单源无第二份字面值。

**接缝专项二：P1F-06 澄清额度设施 × M-06 extable interrupt 挂起状态机互斥——无冲突面，确认**：
- 状态机互斥第一层：`chat_run.status` 二态分立（`interrupt_clarify`/`interrupt_approval`，store.py:45 RUN_STATUSES＋CHECK 冻结）；`resume_preflight`（service.py:395–425）对 kind=approval 要求 status=interrupt_approval（否则 409）、对 kind=clarify 要求 interrupt_clarify（否则 409）——交叉回流双向 409。
- 共用字段判别：`pending_interrupt` jsonb 以 `kind` 键分族（clarify/approval，service.py:1516–1529 vs 1543–1551）；replay 分支同样按 status＋kind 判别（service.py:786–802）。
- 额度隔离：`clarify_count` CHECK 0–1（store.py:100 存储强制）只由 `_suspend_clarify` 增（service.py:1511–1515，二次拒绝 409）；审批挂起/回流零触碰 clarify_count——两类 interrupt 无共享可变配额。
- 顺序面穷举：clarify→approval 可达（缺参反问在 N7.1 先于 N7.4c 挂起，补参回流续跑再遇外表→审批挂起，各自挂起字段整写不互踩）；approval→clarify **不可达**——审批回流整节点重跑（F7 幂等）对**同一问句**确定性重推导，首跑能到 N7.4c 即 N7.1 已非 vague，重跑不可能再弹缺参反问；rewrite 澄清只存在于检索链，审批只存在于问数链，同一 run 链在挂起帧携 `chain` 锁定（service.py:1526–1528）。即便构造出 `_suspend_clarify` 二次触发，域内异常（409 族）在流内拦截不炸链。

## 2. 第 2 节 quality 表族四写手接缝——通过（写面矩阵列级切分无冲突；B12 审计覆盖完整；发现 F-02）

**写面矩阵（主仓 app/ 侧逐写点取证；数据面半边据其仓 DP-05/DP-06 提交文与 quality_writer.sql 授权面交叉核对）**：

| 表 | M-05a（管理面） | M-05b（执行通道） | DP-05（产出编排·数据面仓） | DP-06（拾取自愈·数据面仓） | 冲突面 |
|---|---|---|---|---|---|
| quality_rule | `set_rule_enabled` 唯一写口（store.py:237–244——本域唯一 quality_rule 写出口） | 无写 | 只读（启用集） | 只读 | 无——唯一写口两侧声明一致 |
| quality_task | 受理行 INSERT（running/step=0/rules_count/time，store.py:405–412）；`accept_task` 撤单 DELETE 族（:424–456） | `claim_task_followup` 条件 UPDATE step 2→3（:475–491）＋`finish_task_followup` 3→4（:493–501） | 自建行（step=1 不入拾取候选）＋执行写 report/hits/status=done/step 1→2 | claim 0→1 条件 UPDATE＋heal 重置 running∧step=1→0（超阈 RETURNING） | 无——step 数轴分段占用：主仓 0／2→3→4，数据面 0→1→1→2／自建 1；status 分段：主仓写 running、数据面写 done；heal 只触 step=1（主仓 claim 闸 done∧step=2 不相交） |
| quarantine_row | `attach_quarantine_rows` 唯一 UPDATE=issue_id 回挂（store.py:373–384）＋撤单 issue_id 置 None（:443–447） | 同上（_followup 内 qrow.issue_id 直挂，service.py:452–459） | append-only 仅 INSERT（payload 原样） | 幂等 INSERT（寻址键先查后插——DP-06 F1；quality_writer.sql 附 SELECT 授权，UPDATE/DELETE 仍零授权） | 无——「唯一 UPDATE 列＝issue_id」双仓同约，payload 零触碰两侧一致 |
| quality_issue / quality_issue_transition | 建单/挂单（register_hit＋FOR UPDATE 行锁＋IntegrityError 单次重试自愈，service.py:289–343）；流转 lane＋留痕行同事务（:232–241）；复扫回填 verify（:258–261）；撤单 DELETE（d 前缀∧lane 0） | 建单复用 `_register_hit_locked`（:443–449） | 无写 | 无写 | 无——两写口共用同一会话内体（单源） |
| water_line | 只读（freshness＋chat 水位缝） | 只读 | 三 tier 写（单调不回退） | 无写 | 无 |
| B12 审计 | rule_toggled / issue_transitioned / issue_rescanned（api/quality.py:128–137/:414–423/:404–412） | task_started / task_followup（api/quality.py:199–209/:233–242）——「服务成功返回后落笔、失败路径不达审计行」纪律一致 | —（数据面自带 data_plane.audit_record 双轨，非 B12 口） | — | ✅ 五动作齐＋流转双留痕（transition 行同事务＋审计行） |

## 3. 第 3 节 A2/B4 接口 vs 合同 DTO——通过（逐字段抽查零反证）

**A2 四端点 vs teach A2 v0.2**（抽查每端点 5 字段反证）：
- 端点 1 `GET /api/wells`（api/wells.py:62–80）：well_id/well_name/well_kind_code/block_name/current_status/remark＋total——七字段逐一对上合同端点 1 DTO；well_name 空缺以 null 返回（合同注记）；排序 well_id 升序（store.py list_wells `order_by(well_id.asc())`）。
- 端点 2 `GET /api/wells/{well_id}`（api/wells.py:100–115）：first_prod_date/platform/quality_notes/foot_note＋8 字段——quality_notes 冻结文案仅 N-11 两条逐字对上（domain.py:103–111）；foot_note 注水井派生文案逐字对上（domain.py:92）。
- 端点 3 `GET /api/wells/{well_id}/chain`（api/wells.py:202–243）：counts 五键/measure_types/device_types/measure_foot（N-06 前缀变体逐字对上 domain.py:124）/devices（v0.2 设备状态三枚举值域，domain.py:41）/events（date_end 仅检修行携带——双响应体类型承载 api/wells.py:154–185）/tail（N-06 受效未装配/N-11 追溯结论冻结文案逐字对上 domain.py:141–144）/changes 与端点 4 total 同源同值（service.py:206/:221–228——V1 恒 0 如实）。
- 端点 4 `GET /api/wells/{well_id}/change-tickets`（api/wells.py:264–287）：六字段行形＋well_id＋total；V1 A3 主单未建＝壳返空列表＋如实注记（合同「主单在 A3、只读投影」约定，不 mock 假单）。
- 错误码面：404 well_not_found（errors.py:377–380）、403 ForbiddenError 既有映射（:189–190）、归一化 N2/N-2→N-02（domain.py:50–59）——行为规则 1/7 落实。

**B4 两端点 vs teach B4 v0.4**（抽查每端点 5 字段反证）：
- 端点 1 `GET /api/wiki/pages`（api/wiki.py:55–79）：id/title/lib/source_report{id,doc}/current_version/updated/status＋total——七字段对上；**total＝全量计数（筛选前先数）**（count_pages 在 filter 前，api/wiki.py:65——合同注记原样）；lib/keyword 三字段模糊入参在位。
- 端点 2 `GET /api/wiki/pages/{pageId}`（api/wiki.py:123–144）：slug/digest/generation_source/operator/related_objects{type,id,summary,links}/content/claims{claim_id,text,evidence_chunk_ids}/glossary_terms{word,kind,ref_id,card}——逐字段对上 w1 形状。
- v0.4 撤除语义落实：无端点 3/4、无 `?version=N`（恒当前版）、generation_source/operator 按 v0.4 单态派生不落列（derivatives/service.py:407–426 `SOURCE_AUTO`/`OPERATOR_SYSTEM`）；status 服务端按当前版正文 `[[flag:]]` 判定（service.py:398/:424）；404 含 wiki 开关关未生成（service.py:410）；零写操作、读面零审计挂（模块 docstring 注记 00 §8 写口纪律）——撤除批（P2-04）语义干净。

## 4. 第 4 节 迁移链与主库结构完整性——通过

- **单头链**：`alembic history` 线性无分叉——0001（刻意空迁移）→0002→…→0012→0013→**0016**→**0014**→**0015**→**0017**（head 唯一）；文件名日期序与链序在 0013→0016 处 intentionally 交叉（0014 down=0016、0015 down=0014、0017 down=0015，逐文件 grep 证），Alembic 按链执行正确。
- **dev 主库重建后完整性**（psql 只读取证）：public schema **43 表**与「迁移∪ensure」覆盖集恰合（逐表清点：audit_log 1＋gateway 3＋infra_outbox 1＋sem 9＋kb 8＋wiki 2＋faq 4＋retrieval 2＋chat 3＋quality 5＋water_line 1＋well_status_log 1＋quality_task 1＝43）；agg（3 表）/raw（8 表）/data_plane（5 表）三 schema 在位（中台同实例分 schema——DP-03 拍板）。
- **逐票抽查**：`alembic_version`=0017 单行；**种子 20 行**＝quality_rule 20 行（1–12 启用、13–20 仅登记——`select count(*) where enabled`=12，与 E2 v0.5 实施范围注记吻合）；0014 agg.fct_daily_metering oil/liquid_output＝NUMERIC(10,2)（M-06 R3 轻声明对齐——query_store.py:59–60 注记与实库一致）、oil_pressure NUMERIC(6,2)；0016 wiki_page content/claims/glossary_terms 三列在位；0017 well_status_log 列形（id bigserial/well_id/occurred_on/title/outcome/source_batch/时间戳＋(well_id,occurred_on) 索引）在位；0015 quality_task CHECK(status IN running,done)＋idx_quality_task_time_desc 在位；chat_run 两 CHECK（status 六值/clarify_count 0–1）在位且与迁移 0009 定义一致。

## 5. 第 5 节 B16/B9/B3 边界——通过

- **lint-imports 复跑**：5 contracts 全 KEPT（B16 层间单向、B16 infra 禁咬上层、B1 领域禁框架、B9 kb 禁直调 derivatives、B6 litellm 唯一接触点）。
- **domains 互引现状（chat→semantics 先例未扩面）**：全仓跨域 import 清点（grep 全量）仅六条边——chat→semantics（**仍只 `term_expiry` 一个纯函数**，domain.py:36）、chat/faq/semantics→security（AuditRow/Actor/ROLE_REGISTRY——B12/身份横切族）、kb→gateway（Completion——B6 出口）、wells→security（Actor/ForbiddenError）。dataops/quality、retrieval、derivatives 零出域 import。**无新扩边**。
- **零直建引擎**：`create_async_engine` 全 app/ 唯一出现＝infra/db.py:186（ConnectionManager 内部）；chat.QueryStore/wells.WellsStore/quality.QualityStore 全部持 ConnectionManager 走 `readonly()`/`session()`；问数链与 wells 中台读均消费 M-01 两步缝（`with_row_filter(actor, table)`→`ConnectionManager.with_row_filter`，db.py:331/:428）——形状冻结未动。

## 6. 第 6 节 观测面与审计——通过（发现 F-03 登记）

- **notice/帧语义跨票一致性**：①P1F-03 观测面——出口配置核对行早停表述与收窄语义一致（chains.py:553–559）；②P2-03 分池口径——S6 收束/重评过闸/配置核对三处帧面共用 domain 常量插值（chains.py:351/:410/:434/:558），溢出 notice「另有 N 支未列出」与澄清帧 OVERFLOW_NOTE_TEMPLATE 同族话术单源；③M-06 六站帧——TREE_NODES 注册 N7.1–N7.6＋N7.4a/b/c 九键（domain.py:91–121），链体 node 帧键全部在册；notice level 惯例一致（warning＝拦截/拒答/失锚，info＝放行/批准/锁定）。
- **B12 审计动作族留痕矩阵**（全仓 35 个 action 字符串盘点）：受理族＝chat.ask.received＋quality.task_started；拦截族＝chat.ask.blocked；审批族＝chat.ask.approval（批准/驳回两义在 content 分义）；启停族＝quality.rule_toggled；流转族＝quality.issue_transitioned（＋quality_issue_transition 同事务双留痕）；接续族＝quality.task_followup；复扫族＝quality.issue_rescanned；接线回退（P1F-01）＝**无独立审计行**（发现 F-03）。chat 三动作经 service `_audit_*` 全部走注入 AuditSink（main.py:424 security 注入——B12 唯一写口 security.audit）。

## 7. 第 7 节 事故重建残留——无功能残留（双轨现状如实登记，发现 F-08 为现状非缺陷）

- **双轨现状**：main.py lifespan 11 个 ensure_*（:141–155）与 Alembic 并行存活——其中 **5 表无迁移覆盖**（audit_log/gateway_spend_record/gateway_drill_run/gateway_budget_config/infra_outbox；0001 为刻意空基线），其余 38 表迁移与 ensure 双向 checkfirst 共管。
- **重建后无漂移实据**：alembic_version=0017 单头说明重建走迁移优先；ensure 全 checkfirst 跳过（幂等不重播、种子 ORM 侧不重播——quality/store.py:9–10 单一来源纪律）；抽查两侧 DDL 同构（chat_run 两 CHECK＋索引与 0009 逐项一致；quality_task CHECK 随迁移承载、ORM 不重复声明与 docstring 纪律一致）。
- **孤儿表清点**：public 43 表恰为「迁移∪ensure」覆盖集，无迁移外 ensure 外的孤儿表；data_plane.audit_record/freshness_registry 属数据面自有表非主仓残留。

---

## 发现清单（逐条：位置＋影响评级＋建议处置）

### F-01（中）澄清/审批回流不持久 @ 锚定上下文——锚定发起的问句回流后续推可降级
- **位置**：service.py:638（clarify 回流 `_assemble(question, [])`）、service.py:869（`_resume_approval` 同形）、`_suspend_clarify`/`_suspend_approval` 载荷均无 anchors 键（service.py:1516–1529/:1543–1551）。
- **影响**：@锚定候选是路由与 `_metric_card_for_plan`（chains.py:1026–1034）的重要来源——当问句正文**不含指标名**（指标仅由 @ 锚定携带）且带外表点名时：首跑可到 N7.4c 挂审批，但批准回流后重装配拿不到指标卡 → N7.1 走降级解释链「未命中注册指标声明——不冒充审定口径出数」（chains.py:1051–1074），**已批准的审批出不了数**；缺参反问回流同理。检索链侧回流则丢 S1 锚定证据与「★ 已按你的选择锁定」观测。演示主路径问句通常含指标名故不可达；测试面无 anchors×resume 用例（grep 证）。
- **建议处置**：挂起载荷增携 `anchors` 并回流重装配时带回（形状 additive、pending_interrupt jsonb 可容）；或 Owner 裁决「锚定为一次性输入」并登记差异。开票属 chat 域小票。

### F-02（低）`_advance_issue` 并发流转丢更新——无行锁无复检
- **位置**：service.py:217–241（闸前 readonly 读 issue 计算 target；写会话内 `session.get` 后直写 `managed.lane = target`，无 `with_for_update`、无 current 复检）。
- **影响**：两并发流转同读 lane=2 → 双写 lane=3＋两张 2→3 留痕行——丢一次推进且留痕失真；同域 `register_hit` 已有 FOR UPDATE＋重试自愈先例（F4 义务），本写点未对齐。
- **建议处置**：写会话内行锁复检（`find_by_dedupe_key` 同款 `with_for_update` 形）或乐观条件 UPDATE（`WHERE lane=:current` rowcount 说话）。开票随 quality 域下次进场均可。

### F-03（低）P1F-01 接线回退无 B12 审计行——留痕只在帧面与 run.verdict
- **位置**：service.py:1421–1434（回退覆写）；全仓 audit action 盘点无对应动作。
- **影响**：回退事实可经 `chat_run.verdict`（覆写后 chain 持久）＋N5b 帧 note 追溯，但 00 §8.2「拦截也是审计事件」同族的**路由改写**不留审计痕迹；「已接线链内部注桩缺陷安全网」若真触发（缺陷发生），审计面缺一环。
- **建议处置**：Owner 裁决是否补 `chat.ask.rerouted` 审计（回退发生时落笔，正常路径零开销）；属小票。

### F-04（低）根目录 `ruff check .` 红 26 处——全部在 ontology/tools/，两侧 CI 均不管
- **位置**：ontology/tools/*.py（schema_check/semantic_service_core/test_schema_check/fixture_run/proposal_check/onboard_check/graph_index）；ontology/ci.sh 三闸（unittest/fixture_run/schema_check）**不含 ruff**；主仓闸 `ruff check app tests tools migrations` 绿。
- **影响**：AGENTS.md 硬纪律 0 要求「改动 ontology 提交前跑 ontology/ci.sh」，但该 CI 无 lint 维度；根级 ruff 全仓扫描永远红——「根绿」不可作为任何交付判据，lint 归属缝隙。
- **建议处置**：二选一——ontology/ci.sh 补 ruff 闸，或主仓 pyproject ruff 显式 `extend-exclude ontology/` 并在 AGENTS.md 登记（现状是无人认领的红）。

### F-05（信息）`_run_chain` 澄清哨兵 subtype 缺省值方向存疑
- **位置**：service.py:1466 `subtype = str(event.data.get("subtype") or "rewrite")`。
- **影响**：现两处发送方（rewrite/missing）均显式传 subtype，无实际路径踩中；但缺省落到 "rewrite" 意味着未来链体漏传时会被误归 rewrite 族（走优化问句回流语义）而非显式失败。
- **建议处置**：缺省改为抛错（哨兵合同字段缺失＝链体缺陷 fail-fast），或维持现状登记。

### F-06（信息）图谱链边证据上限沿用 EVIDENCE_CAP——常量名在 v0.4 后有语义漂移
- **位置**：chains.py:1454 `hits[: d.EVIDENCE_CAP]`；domain.py:783–785 注记已登记「图谱链非分池对象——v0.4 分池条文只改 S6 生成窗」。
- **影响**：无行为问题；EVIDENCE_CAP 语义已收窄为「报告类池上限」，图谱边证据（source=graph）借用同名常量，未来调分池参数会静默带动图谱链。
- **建议处置**：拆独立 `GRAPH_EDGE_CAP` 常量（值可同 4），注释已登记可维持至下次进场。

### F-07（信息）同 run 并发 resume 无乐观锁——双写者竞窗登记备案
- **位置**：store.py:260–265（`save_run` merge 直写，无版本条件）；resume_preflight 状态校验与后续写之间无锁。
- **影响**：同 run 双并发 resume 皆可过 preflight、双链重跑（演示单人场景不可达；与 accept_task「残余竞窗登记备案」同口径）。
- **建议处置**：维持登记；真分权批（D3）进场时统一评估。

### F-08（信息）双轨现状——5 表无迁移覆盖＋11 个 ensure_* 与 Alembic 长期并存
- **位置**：main.py:141–155（ensure 族）；0001 空基线；audit_log/gateway 三表/infra_outbox 仅 ensure 承载。
- **影响**：非缺陷（各域切迁移属各域票——P0-08 票面惯例，docstring 全量登记）；重建已证迁移优先路径完整可重建。风险在「新库先 boot 后 migrate」会因 op.create_table 无 checkfirst 而炸迁移——现操作序纪律（迁移先行）为约定非机检。
- **建议处置**：各域退役票按既定挂账推进；可考虑给部署序加一条机检（alembic current 对照）。

---

## 测试与闸复跑汇总（独立取证）

1. 无 PG 基线：`uv run pytest -q` → 870 passed / 75 skipped（22.18s）✅
2. PG 基线：`TEST_DATABASE_URL=postgresql+asyncpg://petro:petro@localhost:5433/petro uv run pytest -q` → **941 passed / 4 skipped**（53.94s）✅
3. 合同覆盖率闸绿（169 条双向对账）；债务标记闸绿（32 条全携可解析 DEBT）
4. lint-imports 5 kept / 0 broken；mypy strict 76 文件零错；ruff 主仓范围零错（根全仓红见 F-04）
5. alembic 单头 0017、链序 0013→0016→0014→0015→0017 无分叉

## 零修复动作声明

本次审查全程只读：主仓代码/配置/迁移/数据**零写入、零修复、零提交**；dev 主库取证全部经只读 psql；测试与闸为复跑非修改；唯一落盘物＝本回报文件（任务指定产物）。发现清单 F-01～F-08 全部留给后续票处置，未做任何预防性修补。

---

## 处置行（M-07.fix 追加，2026-10-05）

- **F-01〔中〕已修复**＝主仓 commit **`ef0fe56`**（fix/m-06-query-chain 追加拍，父＝d413bad）：`_suspend_clarify`/`_suspend_approval` 挂起载荷增携 `anchors`（additive 键——存量帧无此键＝空表兜底，`_pending_anchors` 单源回读防形状漂移）；澄清回流与审批回流两处重装配携锚（原 `service.py:638`/`:869` 的 `_assemble(question, [])`）——@ 锚定发起且正文不含指标名的问句，补参/批准回流后 N7.1 仍锚定命中不出降级，已批准审批可出数。测试：`TestAnchoredResume` 两用例（@ 锚定＋缺参反问→补参 resume→table 出数＋assembly 帧锚线在；@ 锚定＋extable 审批→approve resume→extable 批准出数），红先证据＝挂起载荷 `KeyError: 'anchors'`。
- **F-02〔低〕已修复**＝同 commit（quality 域 service.py——票面 F-02 项点名「同域 register_hit 先例」）：`_advance_issue` 守卫与复检全部挪入写会话——`session.get(..., with_for_update=True)` 行锁（同域 `find_by_dedupe_key` 先例，M-05a rev F4 义务在流转写点落地）＋锁内复检（锁内 lane ≠ 受理快照 lane → 409 拒绝；不双写 lane、不留同距留痕行）。测试：sqlite 确定性复检用例（旧快照进写点被拒、lane/留痕不失真）＋PG 并发用例（两路同窗 gather——修复前实测双收 lane=1 双留痕复现丢更新，修复后恰一成功一 409）。
- **F-03〔低〕已修复**＝同 commit：`_verify_chain_wiring` 返回 `(note, 回退原链)`，回退发生时三路共用调用点（ask 主路径/澄清回流重判/审批回流）落 B12 审计行 action=`chat.ask.rerouted`（content 携原裁决链名＋run 号——动作语义照 chat.ask 审计族惯例；回退发生才落笔，正常路径零开销）。测试：`TestRerouteAudit` 两用例（回退恰一行留痕＋已注册链零回退审计行、受理审计不受影响），红先证据＝回退发生而审计 0 行。
- **未处置（不在本修复拍票面）**：F-04（ontology/tools ruff 归属缝隙——二选一处置待 Owner）、F-05～F-08（信息级登记项）——维持原登记不动，归属待 L0/后续票。
- 修复拍证据：`dispatch/results/M-07.fix.md`（TDD 三件红先原文；无 PG 875 passed+76 skipped／带 PG 947 passed+4 skipped；ruff/mypy strict/lint-imports 5 kept/两闸全绿输出原文）。
