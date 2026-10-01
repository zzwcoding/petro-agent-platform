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
- **P1-01b 收尾裁决（主窗口，c6c7402＋teach d3ac6e3）**：疑点 2 收口＝权威名「开井日历折算/检修剔除」（设定书 §3 证据），三处统一、同步零告警、看守闸测试（再漂移仍红）；疑点 3 收口＝读面四端点 `/api/semantics/{terms,metrics,objects,relations}`，grain_display 读侧拼装照 C1 列形。两条挂账：①别名检索现阶段走展示串投影，结构化别名列需 99/同步器联合变更（挂 C1 后续批）；②C1 端点 11 slots 投影读面未落（挂后续票）。
- 落地 ✅（2026-10-01）：
  - **疑点 2 口径名统一**：权威名定谳＝设定书 §3 指标 2 卡原文「开井日历折算 / 检修剔除」（§6 剔检产量条为别名术语非口径名）。三处现值对照：ontology M3 RULE-PETRO-019 calibers「剔检口径/开井日历口径」（不符→改本体）、C1 口径卡 B「剔除检修」（词序变体→改册）、平台种子常量照抄 C1（随册改）。改动：①`ontology/petro/m3-rule-model.yaml` calibers→`[开井日历折算, 检修剔除]`（`bash ontology/ci.sh` 改前改后全绿）；②teach C1 册两行（澄清说明卡三态选 B 文案＋端点 4 calibers DTO 例「剔除检修」→「检修剔除」）＋变更记录一行（**teach 仓改动未提交**——其仓有无关脏文件，留 Owner 按其节奏提交）；③平台种子常量 `_CALIBER_B` 随 C1 改；④同步器告警逻辑由「两处同在即告警」改为**名字集比对**（一致零告警/真漂移仍告警不静默）——SyncReport.warnings 消除且幂等重跑零告警，看守闸单测（模拟再漂移仍红）。
  - **疑点 3 C1 读面三件套**（98 §5 模块归属＝semantics 模块 `/api/semantics/*`，新建路由族挂 main）：`GET /api/semantics/terms`（端点 2：page/pageSize＋keyword＋status 多值＋owner；keyword 命中面＝术语名＋类型展示串「别名 → X」族＋定义——GLS 别名的台账载体即别名命中；expired/expires_display 读侧现算——F60 到日即标，infra.clock）；`GET /api/semantics/metrics`（端点 3：同上＋`grain_display` 读侧拼装——**拼装公式＝C1 合同冻结 `grain + ' · ' + unit`**；M3 斜杠分维形「月/区块·油田」读侧转括注族「月（按区块 / 油田）」；sem_metric.grain/unit 存储值不动＝裁决 e；status 数组命中读侧过滤——jsonb 包含谓词跨方言无统一写法，量级 15 行）；`GET /api/semantics/objects`＋`GET /api/semantics/relations`（端点 5/6——对象读面含关系账引用行，照 C1 两表分立形状落两端点）。全 GET 零写端点（纯读面 405 框架兜底）；响应信封 items/total/grand_total/page/page_size（00 §4.1 回显＋§4.2）；筛选越界 400 code=`semantics_param_invalid`（新立登记）；C1 全员可见（身份桩依赖无组闸）。
  - **测试**：`tests/api/test_semantics_read_api.py` 11 条（分页回显/keyword 别名命中/status 多值与越界 400/owner 精确等值联席行排除/过期派生族/grain_display 列形/对象固定值/写 405/五角色可读）＋种子单测 3 条新增（口径名漂移看守闸/grain_display/expires_display 派生族）＋2 条零告警断言。
  - **四门禁**：ruff 0 错 / mypy strict 41 文件零错 / pytest 带 PG16@5433 **201 passed 零跳过** / lint-imports 4 契约 KEPT；`ontology/ci.sh` 全绿。
- **差异登记（现实约束按现实落地，语义不私改）**：
  1. **术语 status 筛参数名**：C1 册端点 2 冻结 `status_key=`（2026-09-29），00 §4.5 筛选命名批（2026-10-01）统一 `status`——本票照 00 §4.5 落 `status`（票面指定）；值域仍为 C1 六枚举 status_key 值。C1 册该参数名未随改（票面授权范围仅疑点 2 两行）——挂 C1 后续批收口。
  2. **grain_display 间隔符**：票面例「月（按区块 / 油田）· %」括注后无空格；照 C1 合同冻结拼装公式 `grain + ' · ' + unit` 恒「 · 」间隔（合同常量例「月 · 年 · %」同式）。
  3. **别名命中的载体**：sem_term 无别名列（99 §2.8 冻结列形不改）——keyword 命中类型展示串「别名/缩写/黑话 → X」族（GLS aliases 的台账展示投影），不另建别名存储。
  4. **metrics status 筛读侧过滤**：status 为 jsonb 数组列，跨方言包含谓词无统一写法——SQL 筛 keyword/owner、status 命中与分页读侧完成（量级 15 行，C1「量级 3–15 条」）；terms/objects/relations 全 SQL 筛选分页。
  5. **teach 仓 C1 册改动未提交**（如上）；**对象读面拆两端点**（objects＋relations）照 C1 端点 5/6 冻结形状，「三件套」＝术语/指标/对象与关系两面三族。

## P1-02a kb 底座后端（B1 合同 v0.3 主体）✅（2026-10-01）

- **目标**：报告入库全链后端——建库/路由/直传两拍/五步/任务/台账/配置/活动流。
- **先读**：teach `B1-报告库.md` v0.3（15 端点逐条＋入库路由节）；99 册 kb_library/kb_upload/kb_ingest_task DDL（含本批新列）；00 册 §5（任务轮询）；平台 `app/domains/gateway/`（complete 出口记账先例）、`infra/db.py`。
- **范围**：端点 15 建库（biz_template 四枚举默认配置生成）＋停用/启用（status 落端点 13）；入库路由（端点 5 `suggested_topic` 可选→LLM+本体建议/人确认；端点 6 confirm 落 `routed_lib_id`/`route_confirmed_by`）；直传两拍＋`dup_warning` 非阻断重复提示＋`config_snapshot` 定型；五步管线＋任务（source 字段/筛选，stuck 收口）；台账（入库中状态）；库配置读写（四开关/切段 mode/两复选，下次入库定型）；活动流（action 值域含新建库/停用库/启用库）；向量（pgvector）＋倒排两管线。
- **验收**：15 端点行为规则逐条；真装配冒烟（真传演示 PDF→五步→台账/任务/两索引落库）；路由闭环（LLM 建议→确认→按库定型入库）；四门禁绿＋PG 集成零跳过。
- 落地 ✅：
  - **kb 域**（`app/domains/kb/`，domain 厚/service 编排/store 三件——gateway 先例同构）：`domain.py`（合同常量冻结照抄：五步机器键/label/步短名、四开关、三切段、任务四态、source 三值、模板四枚举＋默认配置档〔completion 图谱开/其余关＝页面 LIB_TEMPLATES 同值〕、五步 note 服务端组装〔步 1/3 固定文案、步 2 随 mode、步 4 随快照 ✓/✗、步 5 无说明行〕、三切段器〔smart 256–1024 字＋10–20% 回带／fixed 512 硬切／mixed 父子分块 F30〕、确定性分词、`LocalHashEmbedder` 向量占位＋`EmbeddingBackend` 换模型唯一缝、路由建议解析〔宽容 JSON、库名归一、模板越界/未知库→mode=None 不硬凑〕、错误族/id 族）；`store.py`（kb_* 八表 ORM——99 §2.5 逐字段＋CHECK 六处＋idx 五处＋基线列；`PgVectorType` pgvector `vector(384)` 列〔sqlite JSON 近似〕；**多写方法显式 flush 排序**——无 relationship 的 UOW 不保证 FK 插序，冒烟实证修正）；`service.py`（16 方法照 98 §3.4 卡＋管线任务体 asyncio——受理即落行开跑、失败按阶段定位 stop_at＋人话原因〔不发明错误码数字〕＋failed current_step＝stop_at 序号〔更正项⑪〕、跳过＝配置性支路不跑不花钱、富化子任务失败不阻塞整卷、重跑＝新任务行 source=重跑定型按当前配置重新定型、stuck 重试内含停止〔取消旧任务体〕、sweep_stuck 收口、IngestCompleted 经 eventbus 发布〔B9——derivatives 订阅缝〕）。
  - **infra 增件**：`infra/object_storage.py`（对象存储 seam＋**真 MinIO adapter**——选型理由：占位无法兑现「服务端核实落桶」409 判据与「GET 直链小时级」两条合同行为，compose 五件已含 MinIO＋minio 依赖已在；物理桶 `reports`＝F5 桶规划、响应 `bucket` 落显示名「报告原文」照抄；PUT TTL 30min/GET 1h；sync SDK 全部 to_thread 卸载）；`infra/config.py` 增 minio_* 凭证槽（.env 注入）＋`load_entity_type_names`（entity_types.json 词表装载——路由话题分析辅助消费）。
  - **路由族**（`app/api/kb.py`，15 条路由；`deps.py` 增 KbDep、`errors.py` 增 kb 400/404/409/501 映射、`main.py` lifespan 装配 ensure_kb_tables＋KbService＋InMemoryEventBus＋启动 stuck 收口）：全员可见不做组闸（roles.js MENU B1 无 roles——身份桩依赖只解析身份）；confirm＝200 同步特例（00 §5.2）；建库 201。
  - **入库路由（B1 v0.3 专节逐字）**：端点 5 可选 `suggested_topic`/缺省文件名兜底→`gateway.complete(petro-main)`＋entity_types.json 词表话题分析（全局默认能力不依赖库配置）→建议归现有库（lib_id＋理由＋置信度）或建议新建库（必带模板推荐）；**LLM 只建议、人确认后执行**——建议归库随受理登记、confirm 即确认执行（路由定型落 `routed_lib_id`/`route_confirmed_by`）；分析不可用→受理照常（建议 mode=None「请手动指定」），空体 confirm 409（kb_route_unresolved）、confirm 可选体带 `lib_id` 人直指定即跳过分析。
  - **Alembic 首执行**（照 P0-08/P1-01 操作序）：env.py 登记区补挂 kb store → autogenerate `20261001_0003_kb_baseline.py`（跨域误报 drop 已人工剔除——P1-01 同款）→ **upgrade head/downgrade base 双向实跑过**（PG16@5433：0002→0003→0002→0003→base→0001→0002→0003 终态 0003 head）；upgrade 先 `CREATE EXTENSION IF NOT EXISTS vector`（downgrade 不撤扩展——库级资产）；双向实跑清掉的 sem_* 种子已重跑同步器补种（counts 11/15/10/5/4/10/3，零告警）。
  - **测试**：`tests/domains/kb/test_kb_domain_unit.py` 13 条（切段三模式带内断言/分词/向量占位确定性＋归一/模板档/路由解析五态/归一化）；`test_kb_service_unit.py` 34 条（建库 400/409/201／两拍 409 族〔未落桶/凭证已用〕/dup_warning 非阻断／五步 done＋向量落库＋产物两卡／**定型语义**〔改配置→快照不变→重跑重新定型〕/失败步序对齐〔stop_at＝解析、current_step=0〕/stuck 收口＋台账「入库中」/source 筛/库列表快照两态分离/graph 筛/活动流/停用启用 400 带码恢复受理/配置校验/路由两拍闭环〔建议归库→空体 confirm 定型；分析失败→空体 409→带 lib_id 确认〕）；`test_kb_tables_pg.py` 6 条（八表逐列＋CHECK/idx 断言＋**pgvector 真库往返**＋路由三列可空＋活动流）；`tests/api/test_kb_api.py` 12 条（15 路由往返/错误包形状/401 身份闸/端点 4 壳 501）。
  - **真装配冒烟**（`tests/test_kb_smoke_real.py`，KB_SMOKE=1 门控——真 PG/MinIO/真 gateway.complete）：建库→受理→**HTTP PUT 直传真 MinIO**（平台不经手字节）→confirm 定型→五步全 finish done→真 LLM 摘要卡＋10 问卡→台账 refs=5/详情 v1/任务/活动流〔新建库/上传报告/入库完成〕→**pgvector 向量 5 片段落库**直查可查。证据：task-34817dc4（终态 done 五节点 finish）、rpt-1988b90a（refs 5）、lib-c88ac307（completion 模板快照 graph=true）。
- 验收自证 ✅：四门禁——ruff（app+tests+migrations）0 错 / mypy strict **46 文件零错** / pytest 带 PG16@5433 **267 passed 零跳过**（含 KB_SMOKE=1 冒烟；不带冒烟 266 passed 1 skipped＝门控冒烟自身；无 PG 底座 243 passed 24 skipped）/ lint-imports 4 契约 KEPT；`ontology/ci.sh` 全绿（ontology/ 零改动）。

> **与合同/票面的差异点登记（现实约束按现实落地，语义不私改）**：
> 1. **confirm（端点 6）增可选体 `{lib_id?}`**（v0.2 合同「请求体为空」形状保留——空体合法）：入库路由专节定谳「路由确认并入 confirm 定型链路」，人确认需要一个选择通道——空体＝沿用受理已定目标库（建议归库随受理登记，confirm 即「人确认后执行」）；带 lib_id＝人改选/直指定；两者与 v0.2 直传流（受理已带 lib_id→空体 confirm）全兼容。**待 Owner 复核**（备选方案：确认改选须重新受理带 lib_id——实现可切换，不改表）。
> 2. **kb_upload.lib_id 可空**（99 DDL 未标 NOT NULL）：路由流受理时目标库未定（「库未定时防鸡生蛋」原文）——confirm 定型 routed_lib_id；直指定流 lib_id/routed_lib_id 同值。
> 3. **kb_fragment.embedding 维度占位 384**（99 注记「维度待 embedding 模型选定后回填＝待办」）：本票以 `LocalHashEmbedder`（确定性哈希向量，非语义向量）打通 pgvector 全链，`EmbeddingBackend` Protocol 为换真实 embedding 模型唯一缝——**embedding 模型选型挂后续批**（疑似疑点清单登记）。
> 4. **关键词倒排不落第二份存储**（99 §6-5「BM25/关键词路落法悬置」）：index 步对非父块片段确定性分词（ASCII 词＋CJK 二元组）但不建倒排存储——落法随 99 收口批对齐；语义半边向量已落 pgvector（冒烟可查）。
> 5. **台账 `status` 两态为读侧派生不落列**：99 `kb_report.status` CHECK 单值「已入库」；端点 1「入库中」＝存在 running/stuck 任务即标（B1 v0.2 裁决原文「存在运行/疑似卡住任务同报告即标，完成转已入库标自动消失」）——列存恒「已入库」，两态由最近任务状态派生。failed 任务对应报告按字面落「已入库」（合同只有两态），失败可见性由任务页签承载。
> 6. **fixed 切段档位落 512 字**（B1 开放问题 6「维持实施批定档」）：本票以 `FIXED_CHUNK_CHARS=512` 占位实现，非合同冻结值；mixed 父块上限 2048/子块 512 同为实施参数（常量集中 domain.py，Owner 可调）。
> 7. **直传 PUT 凭证 TTL＝30 分钟**（合同未冻结期限；B1 端点 5 示例 expires_at 约 25–30 分钟量级；GET 直链 1 小时＝00 §7.2 小时级冻结值）——挂疑点清单待 Owner 拍板。
> 8. **演示注记不入真实实现**：端点 11 `annotations.graph`「省抽取费」为制度文件库演示注记（mock 本地数据，无派生规则）——真实实现恒返回 `{}`；`subject`/`related_objects` 派生归 F31 增补批（本票缺省 null/[]——B1 端点 2 注记「演示缺省为未回填」同象）；`refs`＝非父块片段数（含摘要/问题块——F37 入索引带类型标；与 B2 报告过滤的同源一致性归 B2 票接线时对账）。
> 9. **端点 4 片段修正＝端点壳 501**（票面指定「只立端点壳+表」）：乐观锁列（`current_version`）就位、路由挂载，修正动作＋问题块重生＋wiki 重铸归 P1-02b；501 非 00 §3.2 状态码集（差异登记）——错误包 code=`kb_fragment_revise_deferred`。
> 10. **stuck 收口＝启动巡检单次**（lifespan 惯例，gateway 先例同构）：`sweep_stuck()` 幂等收口 running 且 updated_at 早于 20 分钟（演示阈值量级）的任务；周期巡检循环未挂 lifespan（00 §5.2-6「阈值结合实际框架定」+调度器 infra.batch 挂后续批）——`sweep_stuck()` 公开面已就绪可挂。
> 11. **kb 写端点未接 B12 平台审计**：B1 页留痕面＝F62 库活动流（合同专设），域内写入均「同事务记 F62」；平台级审计（security.audit）对 B1 写操作未挂——是否双轨留痕待 Owner 裁决（gateway 页是 D1 合同有审计要求，B1 合同无此要求）。
> 12. **重跑的片段整卷置换**：重跑＝一次新入库，同名报告片段随重建被整卷置换（含旧向量）；片段修正历史（v1 永存/逐次记版）的跨重跑保留策略归 P1-02b/B2 批（本票修正功能未开，无历史可失）。

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
