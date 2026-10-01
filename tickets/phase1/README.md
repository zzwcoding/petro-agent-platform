# 阶段 1 开发票（知识问答 · 上线页面 B1 B2 B3 B5 A1）

> 拆票依据：teach-petro-agent/docs/roadmap.md 阶段 1 节 + 21 册合同（2026-10-01 Owner 全天拍板批后状态）+ 98/99 册 + 轨道 0 对账结论。
> 验收基线：四门禁（ruff/mypy strict/pytest/lint-imports）+ PG16@5433 集成 + 真装配冒烟；每票一提交；**后端票先行、前端票随后**（阶段 0 D1 验证过的两拍制）；施工遇合同歧义停线回 Owner 拍板，不私改语义。
> 分工铁律（2026-10-01 Owner 固化）：拆票/方案=主窗口，实施派发=子代理；派工单必须给足先读（合同文件精确到节+端点号+拍板结论原文）。

## 拍板基线（全票共用，不再逐票重复）

- 权限：阶段 1 单一角色「系统管理员」全权；所有写功能照做；D3 权限矩阵设计先行（P1-00b）。
- D2 配置：阶段 1 过渡＝提交即生效（记审计+版本推进），A3/C3 接入批切审批链；A1 问答全链按 D2 当前生效配置执行。
- 模型：起草/挖掘/生成一律走 `gateway.complete`（B6，别名 petro-main/petro-lite）；提取/重试判据照椒图蓝本。
- 本体：ontology/petro/ 为真源（语义闸绿）；B5 对号强校接线时点＝P1-01 导出物就绪；接线前弱校照跑。
- 一页一报告一库：入库路由只建议、人确认；一报告＝一库＝一 wiki 页；跨话题页内分节。

---

## P1-00a 前端快照同步（前置，先决）

- **目标**：web/ 原型快照从阶段 0 fork 旧版升级为 teach 原型终稿（2026-10-01 全部拍板批后状态）。
- **先读**：teach `prototype/app/src/`（pages/flows/data/shell 全量）；平台 `web/README.md`；AGENTS.md 第 0 条（快照同步节奏）。
- **范围**：pages|flows|data 全量覆盖（19 页+D5 stub 形态照原型）；核对 `web/src/landing` 与原型路由表；不动底座五件（client/sse/store/组件库）。
- **验收**：web 三连绿（eslint 0 error/vitest 全过/build 过）；`#/proto/*` 抽查五页 0 pageerror；落地树 `#/D1` 回归无恙。

## P1-00b D3 权限矩阵设计稿＋接口横切面补全（只设计不施工）

- **目标**：把"系统管理员全权→未来分权"的图纸画出来，接口横切缺口补成文。
- **先读**：teach `specs/api/D3-安全与权限.md`（v0.1＋开放问题）；`00-系统级API.md`（错误包/任务轮询/id 族）；平台 `app/domains/security/`（resolve_actor/组闸现状）。
- **范围**：①RBAC 设计稿——权限点＝**合同端点粒度**（D3 矩阵＝端点×角色打勾表，五角色初稿：系统管理员/阿强·平台运维/小李·地质/核查员/老王）；deny-by-default；服务端统一校验层设计（FastAPI dependency，B12 越权留痕）；前端按权限渲染（灰/藏，不做真闸）。②横切面补全三缺口：排序参数（`sort_by`/`sort_order` 冻结）、批量操作部分成功口径、列表筛选通用命名——落 00 册增补。
- **验收**：设计稿过 Owner 过目；00 册变更记录加行；**零施工**（不改平台代码）。

## P1-01 semantics 底座＋Alembic 操作序首执行 ✅（2026-10-01）

- **目标**：轨道 0 缺口清零——同步器首跑零手养导入＋模式派生物落位＋迁移操作序首执行。
- **先读**：`ontology/petro/`（7 模型 YAML，schemaVersion 1.1.0）；`ontology/manifest.json`（deferredAdditions：wf3–wf10/白名单#2/Action 三条）；98 册 §sync_from_ontology_repo 行；99 册 sem_* 九表 DDL；平台 `app/domains/semantics/`（空包）；`migrations/env.py`「域模型登记区」；tickets/phase0/README.md P0-08（操作序登记）。
- **范围**：①同步器实现（ref/actor/schema_version 入参，petro/ YAML→sem_* 九表投影）＋占位行种子源（十来行，照 C1 现值口径）。②模式派生导出器（YAML→实体类型/关系清单 JSON，B5 对号表＋A2 白名单消费形态）。③**Alembic 操作序首执行**：域模型 import 挂 env.py 登记区→autogenerate→票面登记 ensure_* 退役拍板（本票即首执行点，操作序照 P0-08 登记）。
- **验收**：PG16 集成逐列断言九表；同步器首跑后 C1 读端点有数（种子零手养）；导出器 JSON 与 petro/ YAML 双向一致；`ontology/ci.sh` 保持绿；四门禁绿。
- 落地 ✅：
  - **semantics 域**（`app/domains/semantics/`）：`store.py`（sem_* 九表 ORM——sem_term/sem_metric/sem_object/sem_relation/sem_join_whitelist/sem_workflow/sem_action/sem_ledger_revision/sem_version，99 §2.8 逐字段＋基线列；枚举落 CHECK 五处（99 §1.4 裁决：status_key 六值/mark ★☆/verdict 两值/workflow status 两值/revision domain 七值）；jsonb 列照 §1.5 裁决清单（metric.status/calibers/modifiers、workflow.card、revision.payload）；uq slot_name、uq(domain,row_id,version)；`ensure_semantics_tables` 幂等 checkfirst 沿 P0-04 惯例）＋ `domain.py`（投影模型/占位行种子常量/钉版契约校验/剥法单点 metric_slot_name/M3 口径字段组 enricher）＋ `service.py`（薄：`sync_from_ontology_repo(ref, actor, schema_version="1.1.0")`——98 §3.7 卡签名；幂等可重跑：未变行零写/新行 INSERT＋revision v1/变行 UPDATE＋revision v+1；B12 审计动作 `semantics.ontology_synced` 经 SecurityService 注入）＋ `exporter.py`（模式派生导出器）。
  - **同步器投影口径**（零手养）：本体承载字段从 petro/ YAML 读出投影（指标 mark/grain/unit/modifiers/ambiguous 口径字段组——schema 1.3.0 裁决 e；M1/M3/M6/GLS 元素锚逐行校验，锚不上即 OntologyDriftError 不静默）；台账展示串照抄 C1 合同现值（种子常量逐条注源——11 术语/15 指标/10 对象/5 关系/4 白名单/10 工作流/3 Action＝对齐矩阵 §2 B 侧真源）；占位行种子：wf3–wf10 八条＋白名单 #2（date_dim）＋Action 三条（manifest deferredAdditions）＋M3 指标 15 桶油增产成本占位（dispute「经营 × 技术联席」）＋M3 指标 11 商品量事实承载型行；钉版契约：低于/高于 1.1 均拒同步、manifest 与请求逐字一致才放行；sem_version 单例行种子 v37（C1/C3 演示值同源，同步器不推全量版本——版本推进归 C3 治理链）。
  - **模式派生导出器**：落 **app 侧**（`app/domains/semantics/exporter.py`，运维入口 `uv run python -m app.domains.semantics.exporter`）；产物落 **config/**（entity_types.json/relation_types.json 进 git）——落位理由：①本票 ontology/ 只读纪律优先（导出器进 ontology/tools/ 即改本体目录）；②导出物是平台消费面（B5 对号强校 P1-05/A2 白名单），消费方 import 在 app 侧最短；③ontology/fixtures/ 是语义闸出厂集区（schema-check-self），不混平台消费产物。消费形照 B5 v0.2 端点 3 对号强校：id/name/ref（实体含 ontology_name 如实标注 §5 短名 vs M1 聚合名差）；关系含 from/to 类型约束（M1 聚合 id 承载，direct/reversed 双口径与 ASSOC 两端核对）。
  - **Alembic 操作序首执行**（照 P0-08 登记）：env.py 域模型登记区补挂 `from app.domains.semantics import store` → `alembic revision --autogenerate -m "sem_baseline" --rev-id 0002` 出 **`migrations/versions/20261001_0002_sem_baseline.py`**（autogenerate 对 env.py 未挂模型的既有 ensure_* 表误报「removed table」已人工剔除——本迁移只触 sem_* 九表，跨域追溯建表归各域票）→ **upgrade head / downgrade base 双向实跑过**（PG16@5433：空→0001→0002→0002→0001→空→0001→0002，终态 0002 head）。数据影响评估：迁移仅新增 sem_* 九张空表、不触碰任何既有表与数据（audit_log/gateway 三表/infra_outbox 零影响）。
  - **同步器首跑**（PG16@5433 演示库实跑）：counts＝term 11/metric 15/object 10/relation 5/whitelist 4/workflow 10/action 3，行版本轴 58 行（version 1，payload 全行快照，changed_by＝调用 actor），重放一遍 0 写；后续 C1 读端点票（阶段 1）直读即有数。
- 验收自证 ✅：PG16 集成逐列断言九表（information_schema 列名/类型/可空 89 列＋CHECK/uq/索引五表六约束三索引，`tests/domains/semantics/test_semantics_pg.py` 3 条）；同步器幂等（跑两遍 0 写）＋占位行种子断言＋钉版拒同步＋B12 审计动作（sqlite 单测 11 条）；导出器 JSON 与 committed config/*.json 字节级一致＋B5 演示配置五类实体/四族关系标签全对号（3 条）。四门禁：ruff（app+tests+migrations）0 错 / mypy strict 40 文件零错 / pytest 带 PG16@5433 **186 passed 零跳过**（无 PG 底座 169 passed 17 skipped——PG 组按约 skip）/ lint-imports 4 契约 KEPT；**`ontology/ci.sh` 全绿**（ontology/ 零改动）。

> **与合同/票面的差异点登记（现实约束按现实落地，语义不私改）**：
> 1. **本体无承载、C1 演示值如实标注的行值照抄 C1**：术语 expires_at（对齐矩阵裁决项 g：本体仓无承载，F60 机器判消费面在平台侧——C1 合同术语表逐行日期）、术语/指标版本号 v1/v3（C1 已声明演示种子值）、term/metric/object/relation 的 name/def/status/owner/source 展示串——全部为 C1 合同逐条冻结的 B 侧现值（对齐矩阵 §2 逐行对账），不属发明；YAML 侧承载 term/type/status/owner 语义与展示串一致性由锚校验保证（术语名 ∈ GLS term∪aliases、工作流名与 FLOW 名称对齐、指标锚 ruleType=CALCULATION）。
> 2. **grain/unit 存 M3 真源值**：sem_metric.grain/unit 从 M3 口径字段组投影（如 #1「月/区块·油田」/#3「月·年」）——与 C1 页面合并串「月（按区块 / 油田）· %」表述有差（可逆投影差异）；C1 读端点票渲染时按其合同「粒度 · 单位」拼装口径处理（或按 99 §1.1 照抄列值拼装——该票裁决）；M3 口径支名（剔检口径/开井日历口径）与 C1 口径卡名（开井日历折算/剔除检修）不一致已如实告警（SyncReport.warnings），台账 calibers 照抄 C1 现值（A1 澄清帧同源消费）。
> 3. **C1 对象账 10 行 ≠ M1 全量 14 聚合**：按对齐矩阵 §2.3/§41 裁决——日产计量/注水日计量/井检修/区块月度结算四台账聚合不占 C1 对象账行（消费面＝A2 映射卡/99 §2.0 中台只读路由），sem_object 只投影 §5 实体十行（对齐映射在导出器与种子常量，AGG id 锚逐行校验）；同源差异 §2.3「设备↔设备状态记录」等三条以 ontology_name 如实标注。
> 4. **M3 指标 11 商品量本体无 CALCULATION 规则**（真源疑点，不改本体）：对齐矩阵 §6 发现 3 明示「事实承载型指标——无计算规则，承载＝AGG-PETRO-008.netWeight＋QR-PETRO-003 出口」，同步器按 C1 现值投影（def/grain/unit 来自 C1），M3 是否补 RULE 行归本体仓 add 提案（Owner 裁决），本仓不动 ontology/。
> 5. **sem_term.expires_display 不落列**：99 §2.8 只冻结 expires_at（expired 到日现算派生不落列——F60）；C1 DTO 的 expires_display 展示串（「长期/—（已禁用）/2026-06-30（已届满）」）由读侧按 expires_at＋status 拼装（R2 展示串不入库），C1 页票接线时注意。
> 6. **whitelist/workflow 的 version 种子值**：C1 未冻结两账版本展示；sem_join_whitelist.version 首版＝1（99 冻结 int 非空）；sem_workflow.version 由 card.meta 展示串「v1/—」派生（wf1/wf2＝1，wf3–wf10＝null）。两值为投影决定，如 C1 后续冻结版本语义随变更记录对齐。
> 7. **导出器落 app 侧、产物落 config/**（票面允许自定的两项，理由见上「落地」节）；config/*.json 为生成物但进 git（B5 对号强校/A2 消费方直接读仓内文件，P1-05 接线不依赖运行时导出）——真源变更后重跑导出器提交，字节级一致性有测试看守（漂移即红）。
> 8. **「P1-01 同步器 ref 参数语义」**：98 卡 ref＝MR 合入事件标识；本仓实现消费工作区 ontology/petro/ 目录（本体已子树并入平台仓，AGENTS.md 第 0 条），ref 作为留痕标识进审计与 SyncReport（首跑 ref＝"workspace:ontology/petro@HEAD (P1-01 首跑)"）——阶段 3 C2→MR 回流接线时 ref 改携真实 MR 标识，签名不动。
> 9. **sem_relation.read 列名照抄合同 DTO**：`read` 在 PG 为非保留关键字、可直用作列名（99 §1.1「DTO 字段同名的照抄」）；SQLAlchemy ORM 属性同名，无避让必要。
> 10. **ensure_* 与迁移并行存活的退役拍未落**（本票登记原话：仅登记并行存活事实）——sem_* 九表自本票起由 lifespan ensure_semantics_tables 建表＋迁移 0002 双轨承载；全平台 ensure_*（audit/gateway/outbox/sem）何时退役切纯迁移，挂后续域票统一拍板（P0-08 交接关系原话「各域切换属各域票」的收口点）。

## P1-01b 挂账修复票（P1-01 疑点 2/3 收口）

- **目标**：P1-01 回报六疑点中两条真问题的修复——口径名不一致消除＋C1 读端点缺口补齐。
- **疑点 2（真不一致）**：M3 `RULE-PETRO-019` calibers「剔检口径/开井日历口径」vs C1 口径卡「开井日历折算/剔除检修」——**先读 teach `docs/business-setting.md` 定权威名**，统一另一边（改 semantics 种子常量或 ontology M3 YAML——改 ontology/ 必跑 `bash ontology/ci.sh` 绿）；同步告警消除；测试更新。
- **疑点 3（真缺口）**：C1 台账读端点三件套（teach `C1-指标与业务术语库.md` v0.1 端点 2/3/11 即术语/指标/对象读面——B3 下拉与 A1 澄清帧的消费者）在 16 票中无归属，随本票补：semantics 域读面（分页/keyword/状态筛，00 §4.5 命名）；**grain 渲染口径本票裁决**：sem_metric 存 M3 真源值不变（裁决 e 不动），读端点响应带 `grain_display` 读侧拼装串（00 R2 先例：expires_display 同款不落列）；格式照 C1 合同页签列形。
- **验收**：同步零告警；C1 读端点三件套行为规则过；四门禁绿；ontology/ci.sh 绿（若动 ontology/）。
- **同时登记**（P1-01 六疑点全量裁决结论，Owner 2026-10-01 过目无异议）：疑点 1/4/5＝已有裁决本设如此（关闭）；疑点 6＝**ensure_* 与 Alembic 双轨维持至 P1-11 收官票切纯迁移**（lifespan 改 upgrade head＋ensure 退役，Owner 采纳）。

## P1-02a kb 底座后端（B1 合同 v0.3 主体）

- **目标**：报告入库全链后端——建库/路由/直传两拍/五步/任务/台账/配置/活动流。
- **先读**：teach `B1-报告库.md` v0.3（15 端点逐条＋入库路由节）；99 册 kb_library/kb_upload/kb_ingest_task DDL（含本批新列）；00 册 §5（任务轮询）；平台 `app/domains/gateway/`（complete 出口记账先例）、`infra/db.py`。
- **范围**：端点 15 建库（biz_template 四枚举默认配置生成）＋停用/启用（status 落端点 13）；入库路由（端点 5 `suggested_topic` 可选→LLM+本体建议/人确认；端点 6 confirm 落 `routed_lib_id`/`route_confirmed_by`）；直传两拍＋`dup_warning` 非阻断重复提示＋`config_snapshot` 定型；五步管线＋任务（source 字段/筛选，stuck 收口）；台账（入库中状态）；库配置读写（四开关/切段 mode/两复选，下次入库定型）；活动流（action 值域含新建库/停用库/启用库）；向量（pgvector）＋倒排两管线。
- **验收**：15 端点行为规则逐条；真装配冒烟（真传演示 PDF→五步→台账/任务/两索引落库）；路由闭环（LLM 建议→确认→按库定型入库）；四门禁绿＋PG 集成零跳过。

## P1-02b 百科生成支路＋修正重铸闭环

- **目标**：B1 百科开关支路全建（wiki 生成＋F52 锚＋台账挂接），片段修正→三重重铸联动闭环。
- **先读**：teach `B4-报告百科.md` v0.3（端点 2 的 content/claims/glossary_terms DTO＋版本四态＋slug 稳定性）；`B1-报告库.md` v0.3 端点 4＋联动登记；PRD F50（模板提示词约束/32K 截断/续写三轮）；P1-01 导出物（挂接词表）；R24（WeKnora 对标）。
- **范围**：拼回全文（重叠去重）→图片块回读→LLM 模板重写（模板＝按库 WikiConfig 的**提示词约束**，产出自由 markdown，零固定节 schema）→`claims[]`（论断锚→切片 id，fail-closed：无锚不渲染[证]）＋`glossary_terms[]`（词表＝C1 台账名册+别名，无账不挂，生成时固化不回溯）→slug 稳定＋版本快照（来源四态：自动重建/人工编辑/回滚）；片段修正（端点 4：乐观锁+记版+索引重建+**问题块重生**）→FragmentRevised 事件→本支路消费重铸（版本+1 来源自动重建，失败不阻塞修正）。
- **验收**：真报告→wiki 页落库（content/锚/挂接逐字段断言）；修正一片段→索引重建+问题块重生+wiki v+1 三联动真跑；截断纪律单测；四门禁绿。

## P1-03 B1 前端

- **先读**：平台快照 `#/proto/B1`（P1-00a 后）；teach B1 册出入对账；`web/src/api/client.js`。
- **范围**：库管理（新建库弹窗/停用启用/来源列+筛选/入库中标）＋报告台账＋入库任务（五步轮询）＋活动流；对接 P1-02a 后端。
- **验收**：web 三连绿＋headless 全流程（建库→传报告→任务五步→台账→活动流）。

## P1-04 B2 前后端（切片管理＋复核队列）

- **先读**：teach `B2-答案出处.md` v0.3（端点 1 扁平清单/2 父块回捞/3 标记/4/5/6 队列＋驳回闭环＋对账 10 URL locator）。
- **范围**：后端六端点（队列：标记入队/复核确认转修正流/驳回带理由回标记人/重标/销记）；前端照终稿＋**#/B2?chunk= 定位消费**（接线时 query 定位滚动）。
- **验收**：队列闭环真跑（标记→驳回→重标→确认→B1 修正）；locator 跳转定位；四门禁绿。

## P1-05 derivatives 后端＋B5 前端（关系图谱）

- **先读**：teach `B5-关系图谱.md` v0.2（4 端点＋对号强校过渡两态＋被拦边端点＋namespace=库）；99 册图谱存储节；平台 compose neo4j（已就绪）；`infra/`（adapter 先例：eventbus/llm_client）。
- **范围**：`infra/graph_store`（Neo4j adapter，B3 出口唯一图接触面）；端点 1 net 整图读/2 配置读/3 保存（**对号强校接线 P1-01 导出物**，对不上拒存 400 带对号明细；事务记 B1 活动流）/4 blocked-edges（reason_code 三值）；图谱支路供 P1-02a 入库调用；B5 前端照终稿（左图右清单/可交互抽取设置/三源示例接真数据）。
- **验收**：抽取设置保存强校两态（接线前弱校/接线后拒存）；被拦边清单真留痕；图入库联动真跑；四门禁绿。

## P1-06 faq 后端＋B3 前端（常见问题库）

- **先读**：teach `B3-常见问题库.md` v0.2（17 端点＋审核流＋⚙改版＋挖掘管线）；D2 册 qa_behavior（扩检已收敛）；98 册 LedgerMerged 事件行。
- **范围**：问答三态+**待审核发布流**（新增/修改先进待审核，发布才可被 A1 消费；种子直发）；挖掘管线（LLM 看 A1 历史会话挖候选→扫库异步任务→向量比对三面去重→LLM 起草 petro-main→人审发布）；导入导出（MinIO 不过期）；⚙（合并阈值 0.87 归本页）；LedgerMerged 消费（术语修订→检出受影响条目→起草→进审核流）；前端照终稿。
- **验收**：审核流闭环（新增→待审核→发布→A1 可见）；挖掘五拍真跑；术语联动单测；四门禁绿。

## P1-07 retrieval 后端（D2 配置面）

- **先读**：teach `D2-搜索与回答.md` v0.2（端点 1 config 读含 qa_behavior 五字段/端点 2 change-requests；提交即生效过渡；出入对账 13 项已清）。
- **范围**：两端点＋qa_behavior 段（faq_direct_hit/refuse_threshold/clarify_strategy/confidence_thresholds/faq_expand_rounds）；阶段 1 过渡＝提交即生效（审计+版本推进，无 A3/C3 落点）；读口供 P1-08。
- **验收**：配置读真返五字段；变更留痕+版本推进；四门禁绿。

## P1-08a chat 装配骨架后端（A1 主链第一拍）

- **先读**：teach `A1-问一问.md`（四层流水线/六路装配 F56/澄清帧）；`D2` v0.2（qa_behavior 消费口径）；00 册 §6（SSE 帧协议＋三保留帧）；平台 `app/api/chat.py`（阶段 0 骨架）/ `infra/eventbus.py`。
- **范围**：SSE 骨架填肉（19 类业务帧注册＋done/error/replay_truncated）；安检层；**六路装配**（F56 全扫全收集/候选上限 4 支/落空进建议池）；意图裁决；**三链分派缝**（检索/FAQ/图谱链位接口留缝，缝内暂回"该能力暂未开通"——17 链枚举全注册）；澄清帧有界循环（缺参反问策略，qa_behavior.clarify_strategy）。
- **验收**：帧协议真跑（提问→done 占位→帧序断言）；装配层六路真扫；未开通话术逐链核对；四门禁绿。

## P1-08b chat 三链后端（A1 主链第二拍）

- **先读**：teach `D2` v0.2（检索瀑布/命中即停/双路合并/精排三档/兜底两策——本拍消费方）；`B3` v0.2（已发布消费面）；`B5` v0.2（图谱问答链）；`B2`（citation/locator）；A1 册（引用 fail-closed 节）。
- **范围**：**检索链**（D2 当前生效配置驱动：三级顺序/早停/两路并发+合并/前 N 精排/兜底 fixed/free）；**FAQ 秒回**（只消费已发布，直出开关 faq_direct_hit）；**图谱问答链**（B5 图遍历+出处）；**cN 引用 fail-closed 完整实现**（伪造/失锚引用拦截，B2 回跳锚生成）。
- **验收**：三链各真跑且 D2 配置改动可见行为变化；fail-closed 单测（编造引用被拦）；四门禁绿。

## P1-08c SSE 树叙事后端（A1 主链第三拍）

- **先读**：teach A1 册（思考过程树节/19 帧语义）；00 册 §6.2（收场判据）；`web/src/api/sse.js`（前端底座帧清单——对齐消费）。
- **范围**：思考过程树帧序列（节点状态流式推进/节点 note 服务端组装）；19 类业务帧完整装配时序；断线重连语义（骨架期 replay_truncated 话术→本拍接缓冲前保持骨架判据，接线留注）。
- **验收**：树叙事时序断言（节点逐帧点亮序列）；断线重连两形态；四门禁绿。

## P1-09 A1 前端（问一问）

- **先读**：`#/proto` A1 终稿；`web/src/api/sse.js`（阶段 0 底座）；B2/B4/B5 locator 形态。
- **范围**：对话页＋SSE 帧渲染＋思考过程树＋出处回跳（切片/wiki 锚/图谱节点）；对接 P1-08b（三链数据）与 P1-08c（树叙事帧）。
- **验收**：headless 全流程（提问→流式帧→树叙事→引用点开回跳 B2 定位）。

## P1-10 D1 增强批（D5 归并落地）

- **先读**：teach `D1-模型与线路.md` v0.2（端点 8 spend-stats＋caller 归因＋观测入口/五信号口径）；99 册 gateway_spend_record.caller 列；平台 `app/domains/gateway/`（阶段 0 全量）。
- **范围**：端点 8 聚合（group_by caller/model/day/month，sums 不随分页）＋caller 归因（unattributed 兜底）；预算双阈值并入 config 族；**pgTrmq 一开始就上**（Owner 拍板：不等阈值）；观测入口外链＋五信号心跳采集（complete 出口）→运行态徽标；前端流水/聚合页签＋观测按钮；演练窗口不做（Owner 拍板：任何时间可按）。
- **验收**：聚合三维度真数；pgTrgm 索引在（\d 断言）；观测入口可达；四门禁绿。

## P1-11 联调收官

- **范围**：17 链冒烟（未实现链话术核对）；五页双树对照（#/proto 终稿 vs 落地，行为一致）；PG 集成全量零跳过；文档计数同步（README/票面粉笔数）。
- **收官验收节**（照 phase0 格式）：五页真跑证据链／端到端问答演示（提问→三链分派→引用回跳）／D2 配置改动驱动行为变化实证／轨道 0 验证闭环①（同步器首跑+强校接线）记录。

## 杂项尾账（不阻塞，随票登记）

- 验证报告第一篇（roadmap 轨道 0 第 4 承诺，建模工序+语义 CI 走通记录）——未动，挂账待 Owner 安排窗口。
- 429 退避重试：不做（维持直抛）；演练窗口：不做；OAuth：阶段 4 前；sys_user：阶段 2；配置模板化：同类库>5 触发（roadmap 已登记）。
