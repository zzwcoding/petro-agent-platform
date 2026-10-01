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
> **P1-02a 收尾裁决（主窗口，9a40e9f）**：疑点 1（confirm 可选体）＝**采纳**（空体沿用建议库/带 lib_id 人改选，与合同空体兼容）；疑点 4（PUT TTL 30 分钟）＝采纳挂账（合同未冻结，续证随实施批）；疑点 5（fixed 512/mixed 2048）＝采纳（开放问题 6 实施批定档，常量集中可调）；疑点 6（failed 标已入库）＝采纳字面口径（合同两态，失败可见性归任务页签）；疑点 8（stuck 周期巡检未挂 lifespan）＝采纳挂账（sweep_stuck 公开面就绪，调度挂后续批）。**两条修复指令**：①疑点 7（kb 写端点未接 B12 平台审计）＝**裁决补**——照 P0-05 gateway 同款口径，api 层编排关键写操作（建库/停用启用/修正确认/配置保存）经 `security.audit` 写平台审计，**P1-02b 施工顺手补齐**；②疑点 2+3（embedding 占位模型＋倒排不落存储）＝**检索链前置双闸，P1-08b 开工前必须收口**——embedding 模型选型与外发倒排落法（99 §6-5）两单随 P1-05 收尾时由主窗口裁决，Owner 复核。

## P1-02b 百科生成支路＋修正重铸闭环

- **目标**：B1 百科开关支路全建（wiki 生成＋F52 锚＋台账挂接），片段修正→三重重铸联动闭环。
- **先读**：teach `B4-报告百科.md` v0.3（端点 2 的 content/claims/glossary_terms DTO＋版本四态＋slug 稳定性）；`B1-报告库.md` v0.3 端点 4＋联动登记；PRD F50（模板提示词约束/32K 截断/续写三轮）；P1-01 导出物（挂接词表）；R24（WeKnora 对标）。
- **范围**：拼回全文（重叠去重）→图片块回读→LLM 模板重写（模板＝按库 WikiConfig 的**提示词约束**，产出自由 markdown，零固定节 schema）→`claims[]`（论断锚→切片 id，fail-closed：无锚不渲染[证]）＋`glossary_terms[]`（词表＝C1 台账名册+别名，无账不挂，生成时固化不回溯）→slug 稳定＋版本快照（来源四态：自动重建/人工编辑/回滚）；片段修正（端点 4：乐观锁+记版+索引重建+**问题块重生**）→FragmentRevised 事件→本支路消费重铸（版本+1 来源自动重建，失败不阻塞修正）。
- **验收**：真报告→wiki 页落库（content/锚/挂接逐字段断言）；修正一片段→索引重建+问题块重生+wiki v+1 三联动真跑；截断纪律单测；四门禁绿。
- 落地 ✅（2026-10-01）：
  - **derivatives 域**（`app/domains/derivatives/`，98 §3.5 卡——wiki 支路归派生物域而非 kb 域：99 §2.7 wiki 表族归 derivatives 模块、B9 边界 kb 禁直调；图支路归 P1-05）：`domain.py`（来源四态 CHECK 值照抄 F52 ①、`[[well/route/claim/term/flag:]]` 标记族、32K 截断＋哨兵续写纪律常量、操作人/回滚横幅/desc 文案合同值、拼回去重 `reconstruct_content`〔相邻重叠剥除＋图片块「插图说明/插图文字」前缀回读〕、claims fail-closed 校验 `extract_claims`〔失效锚就地剥除、无锚论断不进 claims[]、claim_id 页内唯一 c1…〕、台账挂接 `linkify_glossary`〔词表驱动无账不挂＋单字不挂＋长词优先＋标记内不嵌套〕、状态两态/digest 派生、slug 生成 `page_slug_for_report`〔rpt-n02-completion→wiki-n02-completion〕、按库业务模板提示词取向 `WIKI_TEMPLATE_ORIENTATIONS`——WikiConfig 落地面）、`store.py`（wiki_page〔id slug PK＋uq source_report_id 1:1＋current_version 指针＋digest〕＋wiki_page_version〔content TEXT＋claims/glossary_terms jsonb＋source CHECK 四态＋desc/operator/task_no〕append-only 仓储＋`ensure_derivatives_tables`）、`service.py`（生成支路编排：报告读面→拼回→32K 截断→gateway.complete petro-main〔caller=wiki.gen〕→最多续写 3 轮未完放弃〔哨兵 `<!--WIKI-END-->` 纪律，落库前剥除〕→锚校验→挂接→落版本→B9 投影回写；读面三件＋回滚追加语义＋防呆 409）。
  - **生成触发选型（票面「asyncio 任务族或管线第六步」）＝事件订阅＋asyncio 任务族，不进五步管线**：①五步节点名为 B1 合同冻结值不占步位；②B9——kb 只发事件不直调（import-linter 新立 B9 契约机检：`app.domains.kb` 禁 import `app.domains.derivatives`）；③生成失败不阻塞入库任务（IngestCompleted 已 done）。重铸队列＝进程内按报告去重（在途合并完成后补跑一次）；跨进程队列随接线批。
  - **kb 侧**（`app/domains/kb/`）：端点 4 激活（`revise_fragment`：乐观锁 409 `kb_fragment_version_conflict`/空文本 400/记版 v1 不可变/重建折算「片段修正」任务〔五步节点全跑但 chunk 步不重切——REBUILD_CHUNK_NOTE；embed 步向量重嵌该片段；enrich 步问题块重生＝所属批次整批置换〕＋FragmentRevised 事件发布）＋`publish_wiki_version` 公开投影口（B9 例外族——wiki_current_version 回写，禁直写 kb_report）＋**两处 PG 真库实证修复**：①`replace_report_fragments`/`_replace_derived_chunk` 删片段前先删版本行（FK 强制——sqlite 单测不显，冒烟实证）；②`next_fragment_seq` 由 count+1 改既有 id 最大序号+1（问题块重生删除后 count 口径撞号——冒烟实证）。
  - **路由族**（`app/api/wiki.py`，4 条照 B4 端点清单）：目录（lib/keyword 三字段模糊、updated 倒序）/全文（`?version=N` 同 DTO 快照、版本不存在 404）/版本列表（升序＋current 标）/回滚（追加语义、operator 服务端解析、task_no=null、防呆 409、横幅服务端组装）；`deps.py` 增 WikiDep、`errors.py` 增 wiki 404/400/409 映射（新立 `wiki_not_found/wiki_param_invalid/wiki_conflict`）。
  - **B12 审计补齐（裁决指令①，P0-05 gateway 同款——api 层编排、kb/derivatives 不依赖 security）**：建库 `kb.lib.created`/配置保存（含停用启用状态并一条）`kb.config.saved`/修正确认 `kb.fragment.revised`/wiki 回滚 `wiki.page.rolled_back` 四写口经 `security.audit`；域内 F62 活动流照旧双轨。
  - **Alembic 0004**（env.py 登记区补挂 derivatives store → autogenerate 仅出 wiki 两表零跨域误报）→ **upgrade head/downgrade base 双向实跑过**（0004↔0003 单档往返＋base→head 全链重放；清掉的 sem 种子已重跑同步器补种 counts 11/15/10/5/4/10/3 零告警）；main.py 装配 ensure_derivatives_tables＋事件订阅接线（IngestCompleted/FragmentRevised→derivatives）。
  - **测试**：`tests/domains/derivatives/`——`test_wiki_domain_unit.py` 10 条（重叠去重/图片回读/32K 截断边界/哨兵纪律/伪造锚 fail-closed/多锚纯文本投影/无账不挂＋单字不挂＋标记内不嵌套/状态派生/slug/digest/横幅模板）；`test_wiki_service_unit.py` 10 条（wiki 开→v1 落库字段逐断言/claims fail-closed＋挂接固化/开关关→不生成＋直调 404/重跑→同页 v2 slug 稳定/修正三联动〔乐观锁 409/空文本 400/记版/重建任务 done/重铸 v+1 desc「片段修正后自动重建」task_no=修正任务号/活动流「修正＋触发百科重铸」〕/重铸失败不阻塞修正〔版本不前进＋活动流「百科重铸失败」〕/回滚追加语义＋防呆 409＋可再滚回＋投影回写/?version=N 快照固化/截断纪律 1+3 轮放弃不落半页/提示词承载片段号清单＋哨兵＋取向）；`test_wiki_tables_pg.py` 2 条（逐列＋CHECK 四态/uq 1:1/PK(page_id,v)＋ORM 往返含 `desc` 保留字引号）；`tests/api/test_wiki_api.py` 5 条（401/目录空与生成后/详情 DTO＋快照/版本列表/回滚往返＋B12 审计）；`tests/api/test_kb_api.py` 增修正族 3 条＋B12 断言（14 条）。
  - **真装配冒烟**（`tests/test_kb_smoke_real.py` 增拍，KB_SMOKE=1 门控——真 PG/MinIO/真 gateway.complete）：建库→配置保存→真传→五步 done→**真 LLM wiki 页落库 v1**（slug=wiki-42c6c8bd、content 579 字、task_no=task-26941b92）→修正一片段→重建任务 done（source=片段修正）→**FragmentRevised→重铸真跑 v2**（「片段修正后自动重建」、task_no=task-4c50efc3、content 863 字——真 LLM 两版正文不同）→**回滚 v3**（来源「回滚」、operator 阿强、task_no=null）→活动流「修正片段（修正＋触发百科重铸）」→审计四动作 `kb.lib.created/kb.config.saved/kb.fragment.revised/wiki.page.rolled_back` 全落。
- 验收自证 ✅：四门禁——ruff（app+tests+migrations）0 错 / mypy strict **50 文件零错** / pytest 带 PG16@5433 **298 passed 1 skipped**（skip＝KB_SMOKE 门控冒烟自身；带 KB_SMOKE=1 **299 passed 零跳过**）/ lint-imports **5 契约 KEPT**（新增 B9 机检契约）；`ontology/ci.sh` 全绿（ontology/ 零改动）。

> **与合同/票面的差异点登记（现实约束按现实落地，语义不私改）**：
> 1. **wiki 支路落 derivatives 域而非 kb 域**（票面「挂入 kb 管线」按事件缝落地）：98 §3.5 derivatives 卡承接 `/api/wiki/*` 与 wiki 表族（99 §2.7），B9 冻结 kb→derivatives 禁直调——生成由 IngestCompleted/FragmentRevised 事件订阅触发（kb 管线六步方案的合同替代面），选型理由见上。import-linter B9 契约随票新立。
> 2. **wiki_page_version 落 `content` TEXT＋claims/glossary_terms jsonb 三列**，非 99 §2.7 冻结的 `body` 五段 jsonb——B4 v0.3 拍板「固定节撤除、正文自由 markdown」已实质改版该列形（99 未随批），本票照 B4 v0.3 落（升级合同变更记录批应补 99 册）。
> 3. **`status`/`generation_source`/`operator`/`related_objects` 不落列**：status 按当前版 `[[flag:]]` 派生（99 §2.7 同注）、来源/操作人从当前版本行派生、related_objects 为报告读面投影（票 93 不建仓）；票面「wiki_page 表（…operator…related_objects…）」按 DTO 字段口径理解（读侧全量服务端返回）。
> 4. **`digest` 落页级不落版本级**：B4 端点 2 `?version=N` 取该版固化值的字段清单不含 digest（回滚不动 digest）；值为读侧派生（首段首句≤60 字）不另调 LLM——展示串 R2 派生口径，长度上限常量集中可调。
> 5. **截断纪律的「未完」判定＝结束哨兵缺失**（提示词要求全文结束另起一行输出 `<!--WIKI-END-->`，落库前剥除不入 content）——Completer 无 finish_reason 暴露，哨兵是 WeKnora 截断检测的实现替代面（挂差异登记）；续写 3 轮无缝拼接、未完放弃不落版本（半页不落库）。
> 6. **claims/glossary/挂接卡＝生成时固化投影**：锚校验用报告片段集（parent-only 不对外寻址不入锚集）；glossary 词表＝sem_term.term＋sem_metric.slot_name（P1-01b 差异 3：别名载体＝type 展示串，别名行即台账行故 term 名已覆盖别名）；台账读面不可用→本次不挂（无账不挂降级面）；卡片字段＝C1 端点 2/3 行同形直取。
> 7. **修正重建的 embed 步只重嵌该片段**（票面「向量重嵌该片段」字面口径；重建任务其余片段向量不动——整卷重嵌归重跑定型）；重建任务行无 fragment 列，修正片段号由进程内上下文承载（重启丢失不影响正确性，挂差异登记）。
> 8. **问题块重生＝所属批次整批置换**（每 20 段一批——F37 批口径；批次归属未持久化，按修正片段在原文块序中的批次号现算）；置换语义随整卷重跑置换先例（P1-02a 差异 12），不入片段版本轴。
> 9. **重铸失败「版本标失败」落为版本不追加**：B4 消费面承诺「所见皆完整版」＋半页不落库优先——失败可见性＝B1 活动流「百科重铸失败」（who=系统（入库管线））；手动重跑＝B1 端点 10 重跑管线（重跑定型触发 IngestCompleted→重生成）或下一次 FragmentRevised。
> 10. **wiki 页 title/digest 随自动重建刷新、回滚不回退**（title 取报告 doc；B4 演示 title《N-02 井完井报告》与源报告名《…（英文 · 200 页）》的差异化裁剪未冻结——直接沿用报告展示名，挂疑点清单）；版本行 date 用 `DISPLAY_FMT`（分粒度，与 B4 回滚示例「2026-09-29 14:40」同形）。
> 11. **FragmentRevised 事件时点＝修正定型即发**（与重建任务并行——重铸管线只读片段文本，不依赖重嵌完成；98 §8 事件表语义「修正保存后重建索引＋触发百科重铸」的字面顺序）。


## P1-02b 收尾裁决（主窗口，34614ed）
> 疑点 1（99 册 wiki 表五段 jsonb vs B4 v0.3）＝**真不一致，开文档对齐挂账**——99 册 wiki_page_version 节随 B4 v0.3 改版补登记，并入 P1-05 里程碑文档对齐批（同批处理，不单独立票）；疑点 2（截断哨兵判定）＝采纳（实现替代面，真 LLM 实证）；疑点 3（重铸失败不追加版本）＝采纳＋差异登记（「所见皆完整版」优先于册面「版本标失败」措辞，失败可见性走活动流＋B1 端点 10 手动重跑）；疑点 4（重建任务 fragment 号进程内承载）＝采纳挂账（重启丢失不影响正确性）；疑点 5（title/digest 随重建刷新、回滚不回退）＝采纳；疑点 6（wiki 生成＝事件订阅+任务族而非管线第六步）＝采纳（五步节点名冻结/B9 边界/失败隔离三理由成立），Owner 里程碑复核。

## P1-03 B1 前端

- **先读**：平台快照 `#/proto/B1`（P1-00a 后）；teach B1 册出入对账；`web/src/api/client.js`。
- **范围**：库管理（新建库弹窗/停用启用/来源列+筛选/入库中标）＋报告台账＋入库任务（五步轮询）＋活动流；对接 P1-02a 后端。
- **验收**：web 三连绿＋headless 全流程（建库→传报告→任务五步→台账→活动流）。
- 落地 ✅（2026-10-01）：
  - **接口层**（`web/src/api/kb.js`）：15 端点消费函数（getReports/getReportDetail/getDownloadUrl/reviseFragment〔端点 4 已激活〕/initUpload/confirmUpload/listTasks/getTask/getAdditions/retryTask/listLibraries/getLibraryConfig/saveLibraryConfig〔可选 status 承载停用启用〕/listLibraryActivities/createLibrary）＋`putObjectDirect`（F5 直传第二拍前置——raw fetch 字节直达 MinIO，凭证 URL 非 /api 不走 client JSON 封装）＋`mapTaskSnapshot`（轮询 wire 折 camel，gateway mapDrillSnapshot 先例同构）＋`useKbTaskPolling`/`pollKbTaskUntilDone`（**state 字段适配版轮询**——B1 任务 wire 终态字段为 `state`，client.useTaskPolling 只认 `status`〔D1 drills 形〕；底座不动的约束下在本层落适配，轮询主体复用 client 的 request＋isTerminalStatus——瞬时失败容忍/AbortError 直通/onProgress 保护/终态白名单 fail-safe 语义同源）。R1 snake→camel 折回全在本层，页面列定义与原型同形。
  - **页面**（`web/src/landing/B1.jsx`）：三页签照原型终稿——报告台账（入库中 Tag＝端点 1 status 直出；refs/wiki 列＋下载直链端点 3；双击行开详情抽屉〔端点 2 片段预览含版本〕→修正弹窗〔端点 4 乐观锁——409 内联兜底「这段已被别人修改过」〕）；入库任务（上传按钮→hidden file input→受理〔端点 5，lib_id 缺省走路由〕→**建议库弹窗**〔LLM 建议卡：归现有库/建议新建+模板推荐＋理由＋置信度——可确认/改选/直指定/新建；dup_warning 非阻断 Alert〕→putObjectDirect 直传→confirm〔端点 6 带确认 lib_id——P1-02a 收尾裁决①通道〕→受控展开新任务行）；五步 Steps＝useKbTaskPolling 轮询端点 8（节点/note 服务端组装前端零拼装；done 收场自动读端点 9 产物两卡——add_summary/add_questions=false 按快照跳过如实展示）；failed/stuck 按 stop_at/reason 人话渲染＋重试/重跑〔端点 10，按钮 running 禁用兜底 409〕；来源列＋服务端 source 筛；库管理（新建库弹窗〔库名+模板四枚举+说明卡；409 重名内联〕/行内停用启用〔端点 13 可选 status——先读配置再全量整存整取〕/库配置弹窗〔四开关+切段三选一+索引期加法；切段三法对照演示＝前端静态资产照抄原型〕/活动流抽屉〔端点 14 只读〕/图谱筛+关键词）。看切片/看百科行内跳转落 `#/proto/B2`、`#/proto/B4`（落地树未点亮，先以原型页承接跨页跳转——差异登记）。
  - **注册点亮**：registry.js LANDING_MODULES 加 B1（LANDING_LIT 自动派生单源不动）。
  - **测试**（`web/src/landing/B1.test.jsx`，13 条，jsdom+fetch 级 mock 挡 window.fetch 边界，接口层+轮询全真代码）：三页签渲染＋入库中 Tag＋开关快照/错误包内联/上传两拍全链〔受理建议卡→PUT 直传对象存储边界→confirm 带确认库号〕/建议新建库路径〔端点 15→confirm 带新库号〕/建库 409 重名/来源筛 source 筛参/轮询 running→done 收场读产物两卡/failed stop_at 人话＋重试/停用库 PUT status=disabled/库配置保存 hint 回显/活动流/修正 409 兜底/修正成功 hint＋任务刷新。
- 验收自证 ✅：web 三连——eslint **0 error**（2 warning 均原型快照存量）/vitest **60 passed**（client 25＋sse 8＋store 2＋D1 页 12＋B1 页 13）/vite build 过；headless 全流程（playwright-core+系统 Chrome headless，后端 :8000 真 PG16@5433＋真 MinIO＋真 LLM gateway）——建库→真传演示文本（LLM 路由建议卡→直传→confirm）→五步轮询 done（真 LLM 摘要卡＋问题卡）→台账 refs/wiki→详情抽屉→片段修正保存→「片段修正」任务可见→**wiki 联动 v1→v2**（修正触发重铸真实发生）→活动流抽屉；11 张证据截图留 `.scratch/`（不入库），全程 0 pageerror。
- **差异登记（现实约束按现实落地，语义不私改）**：
  1. **轮询 state 适配落接口层**（useKbTaskPolling——client.useTaskPolling 只认 `status` 字段，B1 wire 为 `state`；备选方案＝client.pollTaskUntilDone 改读 `status ?? state` 一行通改，挂底座变更待 Owner 拍板，本票按「不碰底座」纪律落本层适配）。
  2. **看切片/看百科跳原型树**：落地树 B2/B4 未点亮（阶段 1 后续票），台账行内两按钮先跳 `#/proto/B2`、`#/proto/B4`；B2/B4 落地票接线时改指落地树。
  3. **任务展开为受控展开行**（原型 defaultExpandedRowKeys 首渲染后不追新——上传受理成功后主动展开新任务行，其余行点击展开）。
  4. **停用/启用经端点 13 两跳**（GET 配置→PUT 全量+status——端点 13 入参为配置全量整存整取，无单字段 status 动作形状；两跳对页面不可感知）。
  5. **上传成功提示 doc 名从 confirm 回执取**（`done.doc`——更正项①「按登记文件名」由后端保证，页面不本地拼装）。


## P1-03 收尾裁决（主窗口，ed8153f）
> 疑点 1（轮询 state/status 适配）＝**裁决归宿在底座**——client.js `pollTaskUntilDone` 改认 `status ?? state` 一行向后兼容（消灭每接口层重复适配 hook），**P1-04 顺手改**；疑点 2（看切片/看百科暂跳原型树）＝采纳，B2/B4 落地票接线时改指；疑点 3（受控展开行）＝采纳；疑点 4（停用两跳＝端点 13 形状）＝采纳（合同无单字段动作端点，挂接线批观察）；疑点 5（confirm doc 直出）＝采纳。

## P1-04 B2 前后端（切片管理＋复核队列）

- **先读**：teach `B2-答案出处.md` v0.3（端点 1 扁平清单/2 父块回捞/3 标记/4/5/6 队列＋驳回闭环＋对账 10 URL locator）。
- **范围**：后端六端点（队列：标记入队/复核确认转修正流/驳回带理由回标记人/重标/销记）；前端照终稿＋**#/B2?chunk= 定位消费**（接线时 query 定位滚动）。
- **验收**：队列闭环真跑（标记→驳回→重标→确认→B1 修正）；locator 跳转定位；四门禁绿。
- 落地 ✅（2026-10-01）：
  - **模块归属裁定**：并入既有 **kb 域**（不立新 b2 域）——98 §7.1「B2 | /api/kb/fragments | 6 | kb（片段子域）」＋98 §3.4 kb 卡已冻结七签名（`list_fragments`/`fragment_context`/`report_fragment_issue`/`list_issue_reports`/`review_issue_report`/`close_issue_report`）＋99 §2.5 `kb_issue_report` 归 kb 模块表清单；片段＝B1 入库切片同一份 chunk 契约（同表 kb_fragment/kb_fragment_version 同源，`total` 与 B1 台账 refs 同源由 `count_by_report` 兑现）。
  - **kb 域增件**：`domain.py`（队列状态机四态/在途态、标记两态文案 MARK_HINT、摘要/问题块说明行、`new_issue_id`、B2 DTO 族 FragmentListItem/FragmentList/FragmentContext/IssueReportView）；`store.py`（`IssueReportRow`——99 §2.5 逐字段＋CHECK 四态＋ix state＋**部分唯一索引** `uq_kb_issue_report_pending_fragment`〔fragment_id WHERE state='待质检复核'——差异 2〕＋`IssueStore.mark_fragment` 事务：待质检复核态重复 409＋旧驳回单随新标记转已销记＋标记行＋F62 活动行同事务＋`FragmentStore.list_children`）；`service.py`（六方法照 98 卡＋`FragmentMarked` 事件发布＋修正记版补父块锚携行〔context_text 原来置 None——B2 回捞依赖该锚，顺手修〕）。
  - **路由族**（`app/api/kb.py` 增 6 条；21 条 /api/kb 路由）：端点 1 两读法分派（report_id 携带按报告整组取数整表返回；缺省全库扁平清单 page/pageSize 必带缺 400，回显 page/page_size——00 §4.1）/端点 2 父块回捞（按 type 分派：原文块/图片说明/图片文字块＝父块正文〔mixed 子块经版本行父块锚；无锚原文块＝本块全文 context⊇hit 兜底〕；摘要/问题块＝产物说明行）/端点 3 标记/端点 4 队列（state=all|待质检复核|已驳回，终态不出列）/端点 5 review（confirm|reject，空理由 400）/端点 6 close（仅已驳回态）。错误码：kb_issue_duplicate（409）/kb_issue_state（409）/kb_issue_reject_reason_required（400）——errors.py 登记。**B12 审计三写口** kb.fragment.marked/kb.issue.reviewed/kb.issue.closed（api 层编排，P0-05/P1-02a 同款）。
  - **Alembic 0005**（env.py kb store 已挂——autogenerate 因 ensure 双轨已建表出空壳，正文手工补全）→ **upgrade head/downgrade base 双向实跑过**（0005↔0004 单档往返＋base→head 全链重放，终态 0005 head；清掉的 sem 种子已重跑同步器补种 counts 11/15/10/5/4/10/3 零告警）；main.py 装配零改动（IssueReportRow 入 KB_TABLES 随 ensure_kb_tables）。
  - **前端接口层**（`web/src/api/kb.js`）：B2 组函数六件（listFragments/getFragmentContext/markFragmentIssue/listIssueReports/reviewIssueReport/closeIssueReport）＋FRAGMENT_TYPES/ISSUE_OPEN_STATES 常量；**P1-03 裁决顺手项**：client.js `pollTaskUntilDone` 终态字段改认 `status ?? state` 一行（向后兼容 D1 drills 形不变）＋client 回归测试（state 形轮询收场＋status 优先）＋kb.js 轮询重复适配退役（useKbTaskPolling 退化为带 path 缺省薄壳——B1 页调用点零改动）。
  - **落地页**（`web/src/landing/B2.jsx`）：两页签照原型终稿——片段清单（报告下拉复用 B1 端点 1 refs≠null 过滤、选项文案「{doc} · {lib}」照抄；卡头总数＝refs 求和；五类型 Tag 色映射照抄；type/keyword 服务端筛；展开行懒加载端点 2；详情弹窗三件套＋标记问题片段两态文案＋已标记态派生自队列在途态＋409 内联兜底）＋复核队列（四列列表＋state 筛/确认转修正流跳 #/B1/驳回弹窗理由必填空禁用/重新标记＝端点 3 新单＋销记＝端点 6）；mock 更正清单⑧项逐条兑现（差异 5）。**locator 消费**（B2 册对账 10「随实施批」即本票）：`#/B2?chunk=` 进页定位——NotLit 桥（Shell.parseHash 不拆 query、不动 shell/ 纪律：pageKey 带 query 时拆出 chunk 存 sessionStorage 重定向裸路由，B2 挂载消费后清除；干净收口挂差异 4）→ B2 跨报告扫描定位→选中高亮（.b2-locate-flash scrollIntoView）＋详情弹窗自动打开。
  - **注册点亮**：registry.js LANDING_MODULES 加 B2（LANDING_LIT 自动派生）＋B2_LOCATOR_KEY 单源；B1 落地页「看切片」改指 `#/B2`（P1-03 疑点 2 收口）。
  - **测试**：`tests/domains/kb/test_kb_b2_unit.py` 10 条（两读法分派/分页必带 400/类型·关键词筛/404/回捞分派与父块寻址 404/标记事务活动流/409/队列筛选倒序/复核状态机/销记＋重标闭环）；`tests/api/test_kb_api.py` 增 4 条（清单 INV 形状/分页必带/context 懒加载/队列闭环＋B12 三写口＋401）；`tests/domains/kb/test_kb_tables_pg.py` 增 kb_issue_report 逐列＋部分唯一索引断言；`tests/domains/kb/test_kb_b2_pg.py` 2 条（PG 真库闭环：标记→409→驳回→重标〔旧单销记真查〕→确认→B1 修正→销记腿＋CHECK 强制）；`web/src/landing/B2.test.jsx` 12 条（fetch 级 mock 全真代码：渲染 refs 求和/筛参/context 懒加载/标记 hint＋409/队列状态机/locator 定位高亮＋不存在回退）。
- 验收自证 ✅：四门禁——ruff（app+tests+migrations）0 错 / mypy strict **50 文件零错** / pytest 带 PG16@5433 **315 passed 1 skipped**（skip＝KB_SMOKE 门控冒烟自身；带 KB_SMOKE=1 **316 passed 零跳过**——冒烟证据见下）/ lint-imports **5 契约 KEPT**；web 三连——eslint **0 error**（2 warning 均原型快照存量）/vitest **73 passed**（client 26＋sse 8＋store 2＋D1 12＋B1 13＋B2 12）/vite build 过。
- 真装配冒烟（`tests/test_kb_smoke_real.py` 增拍⑪，KB_SMOKE=1——真 PG/MinIO/真 gateway.complete）：五步 done→wiki 真跑后，B2 队列闭环真跑：标记（hint「已标记 · 待质检复核——…」）→重复标记 409 kb_issue_duplicate→驳回空理由 400→带理由已驳回→重新标记（新单入队、旧驳回单转已销记）→复核确认（已修正）→队列零悬挂 total=0→F62 活动流「标记问题片段」→B12 审计 kb.fragment.marked/kb.issue.reviewed 落审计。

> **与合同/票面的差异点登记（现实约束按现实落地，语义不私改）**：
> 1. **票面速记路径与 B2 册冻结形状不一致，以合同为准**：票面施工范围速记 `POST …/fragments/{id}/issues`、`GET /api/kb/review-queue`、`{issueId}:confirm/:reject`，B2 册 v0.3 冻结为 `POST /api/kb/fragments/{id}/issue-reports`、`GET /api/kb/issue-reports`、`POST …/{id}/review`（action confirm|reject）、`POST …/{id}/close`——合同驱动（AGENTS.md 硬纪律 1），按 B2 册落；票面状态机速记「pending|confirmed|rejected|reissued|closed」对应合同四态「待质检复核/已修正/已驳回/已销记」（reissued＝重新标记行为：新单入队＋旧驳回单转已销记，非独立状态值）。
> 2. **uq fragment_id 落部分唯一索引**：99 注记「uq fragment_id」语义锚＝「待质检复核态重复标记 409」，全列 uq 会卡死驳回后重新标记（同片段须能再发新单）——按注记语义落 `uq_kb_issue_report_pending_fragment` 部分唯一索引（PG WHERE 子句；sqlite_where 同构），PG 集成断言在。
> 3. **端点 5 confirm 即落终态**：合同「确认单在修正保存事务内随 B1 活动流一并落终态」的耦合设计无法跨端点同事务兑现（review 与 B1 端点 4 为两端点）——按合同端点语义 confirm→已修正直落终态，页面「确认 · 转修正流」后跳 B1 修正入口（企业化清理批落位同构）；「确认后未修正即悬挂」由四态约束消解（已修正即终态，修正动作是后续管理动作）。
> 4. **locator 桥（NotLit）为过渡实现**：`#/B2?chunk=` 的 Shell.parseHash 不拆 hash query（本票不动 shell/ 纪律）——NotLit 拆 query 存 sessionStorage 重定向裸路由，B2 挂载消费后清除；干净收口＝Shell.parseHash 剥 query 一行（桥即退役），挂 Owner 拍板。
> 5. **队列 state 筛只出在途态**（合同冻结：state=all 亦只出两在途态，终态查询归后续批）——落地页筛选下拉只有 全部/待质检复核/已驳回（原型页有已修正/已销记选项，照合同收窄）；队列 DTO 不含片段类型标（原型有 Tag——99 kb_issue_report 无冗余列，不硬凑）。
> 6. **端点 6 响应展示串**：close 响应 `state`＝「已销记 · 不修正」（合同示例字面），落库/队列列表值＝CHECK 四态「已销记」（展示串不入状态机——R2 展示串不入库口径）。
> 7. **修正记版补父块锚携行**（P1-02b 遗留顺手修）：`revise_fragment` 新版本 context_text 原置 None 丢父块锚——B2 端点 2 对修正过的 mixed 子块回捞依赖该锚，改为携行前版锚。

## P1-04 收尾裁决（主窗口，91e7144）
> 疑点 1（票面速记 vs 合同形状）＝**合同为准**（AGENTS.md 硬纪律 1，派工单速记不构成分叉——复核无误）；2（部分唯一索引）＝采纳（全列 uq 会卡重标，工程正确）；3（confirm 即终态）＝采纳挂账；4（locator 桥过渡）＝采纳，**干净收口（Shell.parseHash 剥 query）挂 P1-11 收官票**；5/6＝采纳（合同口径）；7（顺手修 P1-02b context_text 丢父锚）＝采纳——B2 回捞依赖，修复正确。**顺带双裁决（P1-02a 指令②前置双闸，现定以保 P1-08b 不卡）**：①**embedding 选型**＝P1-08b 用现有 EmbeddingBackend 缝（LocalHash 功能级跑通链路，质量级真模型候选需先验证供应商 embedding 端点）——**质量选型挂 P1-11 前 Owner 拍板**；②**倒排落法定案**＝**pg_trgm GIN 索引**（与 P1-10 同扩展、中文免分词器；99 §6-5「BM25 排名」语义差登记——阶段 1 关键词路＝trigram 子串匹配，BM25 挂后续批）。

## P1-05 derivatives 后端＋B5 前端（关系图谱）

- **先读**：teach `B5-关系图谱.md` v0.2（4 端点＋对号强校过渡两态＋被拦边端点＋namespace=库）；99 册图谱存储节；平台 compose neo4j（已就绪）；`infra/`（adapter 先例：eventbus/llm_client）。
- **范围**：`infra/graph_store`（Neo4j adapter，B3 出口唯一图接触面）；端点 1 net 整图读/2 配置读/3 保存（**对号强校接线 P1-01 导出物**，对不上拒存 400 带对号明细；事务记 B1 活动流）/4 blocked-edges（reason_code 三值）；图谱支路供 P1-02a 入库调用；B5 前端照终稿（左图右清单/可交互抽取设置/三源示例接真数据）。
- **验收**：抽取设置保存强校两态（接线前弱校/接线后拒存）；被拦边清单真留痕；图入库联动真跑；四门禁绿。
- 落地 ✅（2026-10-01）：
  - **模块归属裁定**：graph 子域归 **derivatives**（不立独立 graph 域）——98 §3.5 derivatives 卡「一卡两子域」（wiki＋graph 两条管线产物共享同一生命周期：四开关派生·入库定型，合卡避免两张薄卡）＋98 §5 页面映射「B5 | /api/graph | derivatives（graph 子域）」；kb_extract_config 表（99 §2.7——仍留 PG）与抽取编排归 derivatives 域，图数据经 `infra.graph_store`（ADR-0003 裁决 2 拍 Neo4j——98 §4 adapter 清单单列行）。
  - **infra/graph_store**（图存储专用接触面——98 §4 adapter 清单独立于 B3 db 出口）：`GraphStore` Protocol seam＋**真 Neo4j adapter**（连接配置进 infra.config InfraSettings `neo4j_*` 槽——minio_* 先例同构，.env 注入，缺省对齐 compose bolt 7687/neo4j·petro12345）；懒建连＋verify_connectivity，探活失败**显式抛 GraphStoreUnavailableError 不静默降级空图**；图模型：节点 `(:GraphNode {lib_id,id,label,type,short,sub})`（namespace=库；type 值域＝该库 ExtractConfig 投影）＋边 `[:REL {lib_id,key,rel,note,evidence,chunk_id,report_id}]`（key=`from|rel|to` 合同冻结唯一键 MERGE 承载；evidence＝原文依据句；出处 chunk＋报告）＋被拦边 `(:BlockedEdge {…reason_code,reason,report_id,report_title,blocked_at})`（对账镜像——拦下的边不进图）。
  - **抽取管线（graph 支路）**：**IngestCompleted 事件订阅触发**（B9——kb 禁直调 derivatives，wiki 支路先例同构；不占五步步位），进程内 asyncio 任务族、失败不阻塞入库任务；ExtractConfig 快照随 B1 **confirm 时刻定型**入 `kb_ingest_task.extract_snapshot`（99 §2.5 列已就位——上传入库/重跑定型两处定型点均重新快照；**main.py 组合根注入** derivatives 提供的 `load_extract_config_snapshot`——B9：kb 只见 callable 禁 import）；chunk 挑选闸（无正文块不送抽取——F40）→ `gateway.complete(petro-main, caller=graph.extract)`（**few-shot 配置进 prompt**——ExtractConfig 四段全进）→ **三道闸**（类型闸：类型/标签对配置清单强校〔type_mismatch〕／依据闸：evidence 必须 chunk 原文逐字摘录〔no_evidence〕／弃权闸：LLM 自报 uncertain〔uncertain〕；顺序照铁律分解，残缺行不属抽取尝试不记）→过闸写 Neo4j＋拦下记 BlockedEdge（reason_code 三值＋所属报告＋chunk＋blocked_at）。
  - **四端点**（`app/api/graph.py`＋deps/errors/main 装配）：`GET /api/graph/net`（**整图一次给**：nodes/edges/legend 服务端聚合/stats；图开关关闭期间一律空态——既有图数据保留属图存储生命周期批）；`GET|PUT /api/graph/extract-config`（F40 四段；保存＝待生效配置下次入库定型不热切换，hint 服务端固定文案；**同事务记 B1 活动流「修改抽取设置」**〔B9 例外族经 kb.record_activity，B5 合同端点 3 原文〕＋B12 平台审计 `graph.extract_config.saved`）；`GET /api/graph/blocked-edges`（只读；**页面不加 UI**——治理/E3 消费）；**对号强校两态**（B5 端点 3 注记「防施工卡死两句都写」）：强校对 **P1-01 导出物**（config/entity_types.json＋relation_types.json）逐一对号，对不上拒存 400 `graph_ontology_mismatch` 带对号明细（逐项 kind/value/nearest 最接近台账词条——SequenceMatcher 相似度）；`strong_check` 参数承载接线前弱校过渡态（生产恒强校——P1-01 已就绪）。
  - **前端**（`web/src/api/graph.js`＋`web/src/landing/B5.jsx`＋registry 点亮 B5）：库选择器（lib_id 必传化——更正项④）＋关系网页签（**左图右清单两栏**排版二批定稿；G6 图例隐显/查看节点/选中邻接过滤/带此节点提问〔选中可用未选中置灰；A1 未落地 mock 提示＋导航 #/A1〕全前端本地计算）＋抽取设置页签（可交互四段＋保存反馈服务端 hint＋**强校 400 对号明细弹窗原样展示**）＋**示例三源辅助接真数据**（①从已抽结果生成——出处句经 B2 片段回捞端点；②从报告库选句——报告→原句清单→LLM 预填三元组；③LLM 起草——**真 gateway.complete**；手填兜底保留）。
  - **Alembic 0006**（graph_extract_config——kb_extract_config 单表零跨域误报）→ **upgrade head/downgrade 双向实跑过**（0006↔0005 单档往返，终态 0006 head；仅新增一表不触既有数据）。
  - **测试**：`tests/domains/derivatives/test_graph_domain_unit.py` 26 条（配置校验 400 族/强校对号＋nearest/三道闸三值与铁律顺序/宽容解析/提示词四段/出厂默认对号自洽＋F40 常量留档/快照往返）；`test_graph_service_unit.py` 15 条（默认配置/保存读回＋B1 活动流/强校拒存明细/弱校过渡态/404/开关空态/net 形状与 namespace 隔离/管线过闸＋拦边三值真跑/graph 关不跑不花钱/extract_snapshot confirm 定型入任务行与事件载荷/起草三态）；`test_graph_tables_pg.py` 2 条（PG 逐列＋FK＋仓储往返——TEST_DATABASE_URL 门控 skip 先例）；`tests/infra/test_graph_store_neo4j.py` 2 条（**compose neo4j 真连**：MERGE 防重/整图读/拦边往返/namespace 隔离——无 Neo4j skip 先例）；`tests/api/test_graph_api.py` 7 条（401/net 404 缺参 400/配置默认＋保存往返＋B12 审计/强校 400 明细/形状 400 族/起草/拦边 DTO 逐字段）；`web/src/landing/B5.test.jsx` 10 条（fetch 级 mock 全真代码＋G6 打桩）。
- 验收自证 ✅：四门禁——ruff（app+tests+migrations）0 错 / mypy strict **52 文件零错** / pytest 带 PG16@5433＋Neo4j **367 passed 1 skipped**（skip＝KB_SMOKE 门控冒烟自身）/ lint-imports **5 契约 KEPT**；web 三连——eslint **0 error**（2 warning 均原型快照存量）/vitest **83 passed**/vite build 过。
- 真装配冒烟（`tests/test_kb_smoke_real.py` 增拍⑫，KB_SMOKE=1——真 PG/MinIO/Neo4j/gateway.complete）：抽取设置保存（hint 服务端返回）→confirm 定型→真 LLM 逐 chunk 抽边→图可查（过闸边带出处 chunk/report、节点类型＝配置投影）→**拦边清单有记录**（reason_code 三值域内＋所属报告）→**强校拒存 400 带对号明细实证**（机灵鬼/管辖着＋nearest）→LLM 起草真跑→活动流「修改抽取设置」＋B12 审计 graph.extract_config.saved。

> **与合同/票面的差异点登记（现实约束按现实落地，语义不私改）**：
> 1. **出厂默认抽取配置＝本体对号表投影而非 F40 通用 11 类**：F40 出厂默认（Person…Operation 11 类）不在 P1-01 对号表内——保存必拒强校，且与「本体消费从第一天可用」（开放问题 7 裁决）矛盾；落 `default_extract_config`＝entity_types.json/relation_types.json 投影（默认值原样保存即过强校），F40 11 类合同常量在 domain.py 留档（`F40_DEFAULT_ENTITY_TYPES`）供对账，挂 Owner 复核。
> 2. **DTO 增 `few_shot_examples` 数组**：B5 v0.2 DTO 以 relation_tags[].example 承载 few-shot；出入对账 9 已把示例拆为独立「原句→三元组」段而 DTO 未随改——端点 2/3 增列 few_shot_examples（合同字段 relation_tags[].example 全保留），票面「few-shot 配置进 prompt」由该段承载。
> 3. **边 DTO 增 `evidence_chunk_id`/`report_id` 溯源列**：票面图模型「边（from/to/rel/出处/过闸标记）」要求出处落边；B5 端点 1 冻结字段（key/from/rel/to/note）全保留——additive 不破坏合同形状；三源①出处句消费即读该列经 B2 端点 2 回捞。
> 4. **节点 label/short/sub 落法**：合同节点 DTO 三列；真实抽取无原型「N-06（注水井）」拟装语义——label=short=实体名、sub=类型（同名不消歧 F40 原判；父节点前缀规则实施批定——开放问题 8）。
> 5. **抽取设置停用语义＝清单内剔除**：原型「勾选停用＋停用项保留展示」为前端内存态；DTO entity_types/relation_tags 即启用清单（类型闸只认清单内——「清单之外的标签不立边」），保存时停用项从清单剔除（不另设 disabled 列——合同 DTO 不动）。
> 6. **LLM 起草立实施端点 `POST /api/graph/extract-config/draft-example`**：出入对账 11 要求真实实现起草走 gateway.complete 而合同未冻结该端点形状——实施定形（{lib_id, rel, sentence?}→{sentence, triple}），挂 Owner 复核。
> 7. **extract_snapshot 经组合根注入而非 kb 内嵌**：B9 禁 kb import derivatives——main.py 组合根把 derivatives.load_extract_config_snapshot 以 callable 注入 KbService（kb 对快照装载零感知）；事件载荷增 extract_snapshot 键（additive）。
> 8. **neo4j 连接配置落 InfraSettings（infra/config.py）而非 config/*.yaml**：object_storage minio_* 先例同构（凭证不进 git）——「compose neo4j 连接配置进 config」按配置装载层落位理解。
> 9. **被拦边 (lib_id,key,report_id) 三元组合并**（MERGE 键）：同报告同边多次被拦（多 chunk/重跑）只保留最新拦下记录——对账镜像不无限增长；逐次拦边历史合同未冻结，挂疑点清单。
> 10. **拦边三闸顺序＝类型闸→依据闸→弃权闸**（铁律分解顺序）；LLM 输出残缺行不属抽取尝试、不进对账镜像（跳过不记）。

## P1-05 收尾裁决（主窗口，6163cb7）＝里程碑①
> 疑点 1（出厂默认＝对号表投影而非 F40 通用 11 类）＝**采纳**——强校已开，F40 通用类保存必被拒，出厂默认用对号表是唯一自洽落地（「本体消费从第一天可用」的正解；F40 常量留档）；疑点 2（DTO 增列 few_shot/evidence）＝采纳（additive，随 teach 对齐批登记）；疑点 3（draft-example 起草端点）＝采纳＋挂登记（三源示例真实实现的必要缝，合同未冻结——随 teach 对齐批在 B5 册补登记）；疑点 4（拦边覆盖合并）＝采纳挂账（合同未冻结）；疑点 5（三闸顺序）＝采纳登记；疑点 6（neo4j 凭证 InfraSettings）＝采纳（minio 先例）。**里程碑①达成**（数据面后端簇 P1-01..05 全绿：367 PG 测试+Neo4j 集成+真冒烟三链），触发：teach 文档对齐批（99 wiki jsonb＋B5 增列/draft 登记）＋全量审查（双轴）。

## P1-05b 审查修复票（里程碑①双轴审查三项发现）✅（2026-10-01）

- **目标**：双轴审查（Standards/Spec）三项发现逐字落地——B12 补四写端点＋术语 version 展示串＋graph 活动流真同事务；附带 teach B5 索引行 4→5（一行）。
- 落地 ✅：
  - **B12 审计补齐四写端点**（Standards【中】——P0-05/P1-02a 同款，api 层编排经 `security.audit`，kb 域不依赖 security）：`POST /api/kb/uploads`→`kb.upload.accepted`、`POST /api/kb/uploads/{id}/confirm`→`kb.upload.confirmed`（**confirm 失败路径不审计**——审计在服务成功返回后落笔，未落桶 409 不达审计行，测试断言）、`POST /api/kb/reports/{id}/download-url`→`kb.download_url.issued`（安全敏感——签发留痕带有效期至）、`POST /api/kb/tasks/{id}/retry`→`kb.task.retried`；graph draft-example 不落库豁免（审查已判）。
  - **术语 version 展示串**（Spec🟡）：`GET /api/semantics/terms` 响应 `version` 出展示串 `"v{n}"`（C1 合同 DTO 冻结「v1」形；00 R2 展示串不入库先例——`sem_term.version` 存储层冻 int 不动，读侧拼装）；新增单测断言 `"v1"` 形＋全员 `v{n}` 形。
  - **graph 活动流真同事务**（Spec🟡——B5 端点 3 合同原文「保存同事务记 B1 活动流 F62」）：`ExtractConfigStore.save` 增可选 `record_activity(session)` callable，配置行与活动行**同一会话/事务** flush 同 commit/同 rollback；kb 侧 `ActivityStore.append`/`KbService.record_activity` 增可选 `session` 参（传入即随调用方事务、缺省自开轻会话原行为不变）。**选型＝session 由调用方经 callable 参数注入**，不取「kb 侧另立 in_tx 变体」：①事务边界归写集所有者（与 kb 自身 save_config_with_activity 同构）；②kb 公开面单写口不加面（in_tx 变体同样要收 session，纯增面）；③B9 不破——callable 仍组合根注入，derivatives 不见 kb 表模型。活动行丢失窗口消除（保存已提交/活动行未及写入的不一致态不复存在）。
  - **测试**：`test_kb_api.py` 增 B12 四断言（含 confirm 失败不审计）；`test_semantics_read_api.py` 增 version 展示串断言；`test_graph_service_unit.py` 增同事务同成败断言（活动行落库后中断→配置行不孤儿＋活动行不孤儿）＋强校拒存反断言（保存未发生→活动流零写入）。
- 验收自证 ✅：四门禁——ruff（app+tests+migrations）0 错 / mypy strict **52 文件零错** / pytest 带 PG16@5433 **370 passed 1 skipped**（skip＝KB_SMOKE 门控冒烟自身；+3＝B12 断言/version 串/同事务）/ lint-imports **5 契约 KEPT**；web 三连绿（eslint 0 error 2 存量 warning/vitest 83 passed/vite build 过——web 零改动）；KB_SMOKE 真装配冒烟未跑（真 LLM 计费，票面验收未列——挂疑点）。
- 附带：teach `specs/api/README.md` B5 索引行端点数 4→5（**teach 提交 5f2a43c**——里程碑①文档对齐批遗留，draft-example 已随 e59ca4c 入 B5 册、索引行计数挂本票）。

## P1-05b 收尾裁决（主窗口，cf738c9＋teach 5f2a43c）
> 三项审查发现全修复（B12 四写端点含 confirm 失败不审计中间断言/terms version 展示串/graph 活动流真同事务双向不孤儿）。疑点 1（冒烟未跑）＝采纳（API 级真 SecurityService 已覆盖，KB_SMOKE 计费门控留 P1-11 收官统一跑）；**疑点 2（metrics DTO 缺 version）＝真缺口，挂账并入"semantics 读面收口批"（与 P1-01b 挂账 slots 读面同批，P1-11 前收口）**；疑点 3（objects version 维持 int|null）＝采纳。

## P1-06 faq 后端＋B3 前端（常见问题库）

- **先读**：teach `B3-常见问题库.md` v0.2（17 端点＋审核流＋⚙改版＋挖掘管线）；D2 册 qa_behavior（扩检已收敛）；98 册 LedgerMerged 事件行。
- **范围**：问答三态+**待审核发布流**（新增/修改先进待审核，发布才可被 A1 消费；种子直发）；挖掘管线（LLM 看 A1 历史会话挖候选→扫库异步任务→向量比对三面去重→LLM 起草 petro-main→人审发布）；导入导出（MinIO 不过期）；⚙（合并阈值 0.87 归本页）；LedgerMerged 消费（术语修订→检出受影响条目→起草→进审核流）；前端照终稿。
- **验收**：审核流闭环（新增→待审核→发布→A1 可见）；挖掘五拍真跑；术语联动单测；四门禁绿。

## P1-06 中期记录（主窗口核验，2026-10-02 00:5x）
> 后端 17 端点已在盘全绿（ruff/mypy 56 文件/pytest 396 passed 未提交）——主窗口逐条核验 vs B3 v0.2 端点清单：**17/17 形状全对**（含审核发布端点 17 占号）；⚙ 无配置读写端点＝**合同正确**（撤端登记：阈值 0.87 展示态，承载随校准批）；LedgerMerged 消费在（service.py:1104）。施工子代理遇配额墙（429，01:31 重置），**余下＝B3 落地页+注册+前端测试+冒烟+提交**，配额恢复后派收尾代理。

## P1-06 收尾段落地 ✅（2026-10-02，收尾代理——前端＋验收＋提交）

- **B12 复核**（收尾首拍）：api 层编排六写口全经 `security.audit`（faq 域不依赖 security，P0-05/P1-02a/P1-05b 同款）——新增 `faq.entry.created`／合并 `faq.entry.merged`／停用启用 `faq.entry.state_changed`／审核发布闸 `faq.entry.reviewed`／导入 `faq.library.imported`／导出直链签发 `faq.library.exported`（安全敏感，P1-05b 同族）；LedgerMerged 联动建议稿经注入 audit 落 `faq.ledger_merged.suggestion`（domain 内写，who=系统）。
- **收尾修复（真库实证）**：`create_entry` 候选回写锚 **FK 插序 bug**——回写锚 UPDATE 先于条目 INSERT 发出即撞 `faq_candidate_source_entry_id_fkey`（无 relationship 的 UOW 不保证 FK 插序，sqlite 单测 FK 默认关不显，P1-02a「多写方法显式 flush 排序」先例同款）；修复＝条目 `insert_entry`（内部 flush）落库后再 dirty `cand.source_entry_id`。真库红绿双向实证＋PG 回归看守 `test_candidate_writeback_fk_order_on_pg`（携 source_candidate_id 入库→锚落库→发布→候选 published 零悬挂）。
- **前端**（`web/src/api/faq.js`＋`web/src/landing/B3.jsx`＋registry 点亮 B3）：接口层 17 端点消费函数全落（wire snake→camel 全在本层；端点 10 扫库轮询＝`useFaqScanPolling` 薄壳复用 client.useTaskPolling；端点 15 导入 raw fetch＋query 参数与后端传输形态对齐；**client.js 增 `del` 便捷式**——端点 6 是平台第一个 DELETE 消费方）。落地页照原型终稿交互形态：问答清单（状态筛/关键词服务端筛＋四态行标＋待审核行尾「发布」＝端点 17；种子直发态照常）／新增弹窗（三源：台账口径下拉＝C1 metrics|terms 读端点、切片原文下拉＝B2 端点 1 全库扁平清单、手填＋LLM 起草＝端点 14；输入即检重复＝端点 4 防抖非阻断；负例复选＋关联口径挂接）／详情弹窗（相似问逐条增删即时生效＝端点 5/6＋维护人/版本行）／合并弹窗（目标由人选——更正项⑫）／挖掘弹窗（扫库 202 受理＋轮询关弹窗不中断→候选库状态筛→向量比对展开行只认比对结论＝端点 12→LLM 起草自动填入新增弹窗＝端点 13→人审核发布）／⚙ 弹窗（相似问合并开关＋阈值 0.87 只读展示＋负例入口 Tag——**无端点展示态**，配置读写端点撤除登记）／导入导出按钮组（端点 15/16，导出预签名直链 window.open 浏览器直下）。
- **前端测试**（`web/src/landing/B3.test.jsx` 14 条，B1/B2 范式 fetch 级 mock 挡 window.fetch 边界，接口层＋页面全真代码）：渲染（卡头 grand_total＋筛选计数＋四态行标）／状态筛走服务端 query／状态标四态互斥／输入即检重复警告→入库「已提交审核」提示／待审核行发布（端点 17 action=publish）／相似问逐条增删／行尾停用（端点 8）／合并目标选择→成功提示（端点 7）／候选库渲染（未比对不显示展开钮——合同）／比对→起草→草稿自动填入新增弹窗（端点 12/13）／扫库 202→轮询 done→空态说明收场／导出直链 window.open（端点 16）／导入 raw fetch＋query 参数＋四计数提示（端点 15）／⚙ 阈值 0.87 只读展示。
- **真装配冒烟**（`tests/test_faq_smoke_real.py`，**FAQ_SMOKE=1** 门控——真 PG/MinIO/真 gateway.complete petro-main；比对向量＝LocalHashEmbedder 占位零 LLM 成本）：①新增→待审核（待审核筛可见）→review publish→serve（清单可见）审核流闭环；②挖掘五拍真跑：候选比对（三面去重真算——既有问答/知识库向量/本体命中）→LLM 起草（真调用，溯源后缀「请人工核实）」恒在）→携 source_candidate_id 入库（先进待审核）→发布→候选回写 published 零悬挂；③扫库异步长任务（A1 历史会话料源未上线——空态说明收场，202→轮询 done）；④B12 审计留痕查证（faq.* 动作族）＋导出直链真预签名（MinIO 真桶）。**重跑幂等改造**：演示库状态不回滚，候选按状态就地取材（pending→全五拍真跑／compared→起草拍／drafted→复用在库草稿携锚／全 published→复用草稿普通入库）——四条路径逐轮真跑全过（含真 LLM 起草三轮证据），冒烟从此可无限重跑。
- **Alembic 0007 双向实跑（收尾段补验）**：0007→0006→0007 单档往返 PG16@5433 实跑（downgrade 只 drop faq_* 四表；upgrade 重建）；往返后 lifespan `seed_demo_if_empty` 自动补种（九条问答＋四簇候选幂等）＋冒烟复验绿。
- 验收自证 ✅：四门禁——ruff（app+tests+migrations）0 错 / mypy strict **56 文件零错** / pytest 带 PG16@5433 **429 passed 2 skipped**（skip＝KB_SMOKE/FAQ_SMOKE 两个门控冒烟自身；无 PG 底座 396 passed 35 skipped）/ lint-imports **5 契约 KEPT**；web 三连——eslint **0 error**（2 warning 均原型快照存量）/vitest **97 passed**（83＋B3 页 14）/vite build 过；`ontology/ci.sh` 不涉（ontology/ 零改动）。
- **差异登记（现实约束按现实落地，语义不私改）**：
  1. **端点 15 传输形态＝raw body（application/octet-stream）＋query 参数**（mode/dry_run/filename）：python-multipart 不在平台依赖清单（本票不动 pyproject），multipart 形态归依赖落位批再切——合同「传输形态结合实际框架定」落点，前端 raw fetch 同构对齐。
  2. **审核驳回落 disabled 而非独立第五态**：合同四态机（待审核/服务中/负例/已停用）无「已驳回」态——reject 语义＝落已停用留档（hint 明示「已驳回」），可改后重新提审（改后回待审核）。
  3. **A1 历史会话料源缝（session_loader）暂缺**：A1 会话域未上线——扫库落空态说明收场（「A1 问一问历史会话尚未上线…」）；A1 装配批注入本缝即通（main.py 组合根留位）。
  4. **is_negative 落列**（99 关键列未列、审核流需要）：待审核行承载负例登记意向，publish 落 negative——迁移 0007 注记，随本票登记。
  5. **种子候选态 scan.last_hint 为 null**：种子态取「未扫库」初态（合同 DTO 示例为扫库后快照——不引入伪任务行），如实在库。
  6. **演示库 FAQ 种子在 0007 往返后重装**：构造轮演示行（含早轮冒烟消费态）随往返清零重种子——冒烟证据以审计行（faq.* 动作族持久）＋本节记录为准。


## P1-06 收尾裁决（主窗口，bd8baf2）
> 验收全绿（带 PG 429 passed＋FAQ_SMOKE 真冒烟）；收尾段修一真 bug（候选回写 FK 插序——PG 红绿双向验证＋回归看守，**沉淀纪律：多写口先 INSERT 后 UPDATE 锚，UOW 通病**）。疑点裁决：1（门控名笔误）＝采纳登记；2＝采纳为全票纪律；3/4（冒烟燃料/种子重装）＝采纳备注；5（python-multipart 依赖缺）＝**挂账：导入传输形态随依赖落位批**（P1-11 前）；6（A1 session 料源缝）＝已路由 08a。

## P1-07 retrieval 后端（D2 配置面）

- **先读**：teach `D2-搜索与回答.md` v0.2（端点 1 config 读含 qa_behavior 五字段/端点 2 change-requests；提交即生效过渡；出入对账 13 项已清）。
- **范围**：两端点＋qa_behavior 段（faq_direct_hit/refuse_threshold/clarify_strategy/confidence_thresholds/faq_expand_rounds）；阶段 1 过渡＝提交即生效（审计+版本推进，无 A3/C3 落点）；读口供 P1-08。
- **验收**：配置读真返五字段；变更留痕+版本推进；四门禁绿。
- 落地 ✅（2026-10-02）：
  - **模块归属**：新域 `app/domains/retrieval/`（domain 厚/service 编排/store 两表——gateway 先例同构）。
  - **配置载体裁定（票面授权自定项）＝DB 表为主（99 §2.10 两表）＋种子合同默认值首次读取自动落库**（gateway_budget_config 单例种子先例），不走 gateway models.yaml 文件真源路线。理由：①99 §2.10 已冻结 retrieval 两表 DDL（config jsonb＋version_no 自然键〔99 自然键注册表〕＋via 生效变动单号回链）——D2 合同语义＝「配置版本化保存」＋版本轴推进＋修改历史（页头「修改历史」弹窗数据源）＋pendingChange 在途态，文件真源无版本轴承载；gateway 的 models.yaml 是 B6 运行时调用参数热加载场景（D1 明示「写回热加载」），D2 是管理面配置——载体随语义分（D2 合同「保存语义三分」同构）；②`faq_expand_rounds` 自 B3 收敛本页（faq_config 撤除）——DB 域配置承载先例同向。
  - **domain.py**（合同常量/校验/号段单源）：六配置节默认值照抄 D2 合同常量（qa_behavior 五字段＝faq_direct_hit=true/refuse_threshold=0.4〔页面演示初值注记〕/clarify_strategy=ask_missing〔现值唯一档〕/confidence_thresholds={high:0.8,low:0.4}〔F56 已拍板口径〕/faq_expand_rounds=3〔1–5，B3 收敛来〕）；patch 校验（节键白名单/整节替换——形状同端点 1 对应节，缺键多键即 400/数值域越界 RetrievalParamError 带字段与允许区间〔D1 400 带区间先例〕；布尔冒充 int 守卫；confidence_thresholds 须 high≥low；标量节 rerank/citation_format 规范化值＝标量）；topK/topN 上限 1–100（D2 开放问题 6「实施批定上限」授权实施值，TOPK_LIMIT 常量集中 Owner 可调）；号段（version_no `v{n}` 推进/#CFG-YYYYMMDD-NN 当日序号递推——种子 via=None 不计）；ConfigSnapshot 家族（读面/落库统一形状——P1-08a/b 消费缝）。
  - **store.py**：`retrieval_config`（生效指针单例行 id='singleton'＋current_version_no FK）＋`retrieval_config_version`（append-only，99 §2.10 逐字段＋基线列；updated_at 即版本生效时刻；via 可空——种子行非变更产生；枚举不落列级 CHECK——jsonb 承载、校验在域层，99 §2.10 未冻结 CHECK）；`ensure_seeded` 首读自动落种子（v1/via=None/updated_by=系统〔00 §2.2〕）幂等；**显式 flush 排序**（版本行 INSERT 先于指针 UPDATE——FK 插序，P1-06 全票纪律）；`ensure_retrieval_tables` 幂等（与 Alembic 0008 双轨——退役拍挂 P1-11 收官票，P1-01 差异 10 同口径）。
  - **service.py**：`effective_config()`（端点 1 读面＋P1-08a/b 运行时消费缝——检索瀑布/FAQ 直出/兜底/作答行为按当前生效配置执行）；`submit_change_request(patch, updated_by)`（受理→生效一体：校验→整节合并→新版本落库〔via=变更单号〕→指针切换同事务；在途闸 check-and-set——并发受理 409 retrieval_conflict，阶段 1 无审批等待期、在途窗口＝受理处理期）；B12 审计在 api 层编排（gateway 先例——域不依赖 security）。
  - **路由族**（`app/api/retrieval.py` 两端点＋deps/errors/main 装配）：`GET /api/retrieval/config`（七节全量＝version{no,updated_at〔R2 展示串〕,updated_by,via}＋六配置节＋pending_change；GET 恒返回生效值、待审 patch 不进响应）；`POST /api/retrieval/change-requests`（202：change_request_id/state〔合同字面 pending〕＋config/version——票面「返回新配置+版本」additive）；SettingsActor 组闸（设置中心组——401/403 语义同 D1）；响应字段 **R1 snake 迁移**（citationFormat→citation_format、pendingChange→pending_change、earlyStop→early_stop、semanticTopK/keywordTopK/topN、changeRequestId→change_request_id——qa_behavior 五字段合同已 snake 照抄）。
  - **B12 审计**：`retrieval.config_changed`（api 层经 security.audit 唯一写口；内容携单号＋推进版本＋变更节；失败路径不达审计行——P0-05 先例，测试断言）。
  - **Alembic 0008**（`20261002_0008_retrieval_baseline.py`；env.py 登记区补挂 retrieval store；两表手写——版本表先建、指针表 FK 引用 version_no）→ **upgrade head/downgrade 单档双向实跑过**（PG16@5433：0007→0008→0007→0008 两轮往返，终态 0008 head；数据影响评估：仅新增 retrieval_* 两空表不触既有表与数据，真装配冒烟产生的演示行随往返清零）；PG 表结构逐列＋FK＋jsonb 实查对表。
  - **测试**：`tests/domains/retrieval/` 27 条——`test_retrieval_domain_unit.py` 19 条（合同常量照抄断言〔qa_behavior 五字段全量〕/patch 白名单·未知节·空 patch·整节替换缺多键/数值域带区间族〔topK 上下限＋布尔冒充/faq_expand_rounds 1–5 边界/refuse_threshold 0–1/thresholds 倒挂/rerank·citation·fallback·clarify 枚举/order 三级顺序冻结〕/号段当日序号/合并整节替换＋标量节/快照往返）；`test_retrieval_service_unit.py` 8 条（首读种子合同默认值＋幂等零写/版本推进＋via 回链/两单序号串行＋版本轴 append-only/越界 400 失败零写〔种子也不落〕/在途闸释放/并发 409〔asyncio.gather——只受理一单〕/空库受理先种子再叠加）；`test_retrieval_tables_pg.py` 4 条（TEST_DATABASE_URL 门控——两表逐列＋FK＋jsonb 真库断言/版本链·via 回链·指针切换真库/越界 400 带区间/并发 409 真库）；`tests/api/test_retrieval_api.py` 10 条（401 两端点/403 组闸〔小李〕/默认快照七节形状＋pending_change 恒 null/202 往返合同字段＋新配置与版本/400 越界带区间 violations/400 未知节·空 patch·缺 patch 三族/B12 审计落痕〔action 筛＋content 直读存储——D3 面不出正文〕/B12 失败路径不落审计）。
- 验收自证 ✅：四门禁——ruff（app+tests+migrations）0 错 / mypy strict **60 文件零错** / pytest 带 PG16@5433 **470 passed 2 skipped**（429＋41；skip＝KB_SMOKE/FAQ_SMOKE 门控冒烟自身；无 PG 底座 433 passed 39 skipped）/ lint-imports **5 契约 KEPT**；真装配冒烟（main.py lifespan 实启、PG16@5433）：首读自动落种子 v1（via=None/updated_by=系统）→202 受理即生效 v2（#CFG-20261002-01，via 回链）→GET 反映新值→小李 403 组闸——冒烟演示行随 0008 往返清零。

> **与合同/票面的差异点登记（现实约束按现实落地，语义不私改）**：
> 1. **配置载体裁定＝DB 表为主＋种子合同默认值**（票面授权自定项，理由见落地节）——gateway 的文件真源惯例不适用于 D2（运行时热加载 vs 管理面版本化两类场景）。
> 2. **「七个配置节」计数注记**：D2 册「七个配置节（order/params/rerank/citationFormat/fallback/qa_behavior）」枚举六键——「七」计数含 version 元信息节（00 R1 证据列「其 version 节」同口径，99 册「节数 6→7」同源）；patch 白名单六节为合同字面照落，version 走列不走 jsonb（99 §2.10 列形即此意）。挂 Owner 复核（如判册面笔误随 teach 对齐批改册，实现零改动）。
> 3. **响应字段 R1 snake 迁移**（00 §14-R1 裁决＋D1「本端点即真实接线直接落 snake」先例）：citationFormat/pendingChange/earlyStop/semanticTopK/keywordTopK/topN/changeRequestId 全部落 snake；version.updated_at 为 R2 展示串（空格分隔「YYYY-MM-DD HH:mm」，D2 示例同形）；节键同迁（patch 白名单 citation_format）。
> 4. **端点 2 响应追加 config/version**（合同冻结字段 changeRequestId/state 全保留——additive 不破坏合同形状）：票面「返回新配置+版本」的承载。**state 维持合同字面 "pending"**（A3 审批链形态值——阶段 1 变动单不落 A3、受理即生效，生效性由 version.via＝本单号回链承载；A3/C3 接入批切回审批链时该字段语义如实化，形状不变）。挂 Owner 复核（如倾向阶段 1 如实值，改 PENDING_STATE 常量一行）。
> 5. **pending_change 恒 null**（票面两态注记兑现）：阶段 1 提交即生效无审批等待期——「驳回清空/批准后保留至生效」两态语义挂 A3 接入批兑现；在途单权威状态届时投影自 approval（99 §2.4 注——不落本域表）。
> 6. **数值域实施值**（合同授权或形状级判定，均带区间 400）：topK/topN 上限 1–100（开放问题 6「实施批定上限」——TOPK_LIMIT 常量可调）；refuse_threshold 值域 0–1（页面控件域；步长 0.05 为页面步进不入合同值域）；confidence_thresholds 须 high≥low（F56 档位语义倒挂即形状非法）；fallback.text 非空白（fixed 空文案无运行时承载；free 态文本仍原样存储不做联动校验——合同注记）；空 patch（零节）400（无变更的变更单无意义——版本推进无承载）。
> 7. **#CFG 单号阶段 1 由本域自铸**（#CFG-YYYYMMDD-NN 当日序号，retrieval_config_version.via 列承载回链——页头「修改历史」弹窗 A3 接入批前的数据源）：A3 缺位，A3 接入批单号主铸权归 approval.submit_config_ticket（B10 单据产生口，99 §2.10 注）；种子行 updated_by＝「系统」（00 §2.2 低风险自动执行）。
> 8. **在途 409 判据＝进程内在途闸**：阶段 1 单进程演示底座——并发受理撞闸 409（受理→生效一体，无审批等待期）；跨进程串行化与 A3 在途单 DB 投影随 A3/C3 接入批。

## P1-07 收尾裁决（主窗口，6e8130d）
> 全绿（带 PG 470 passed＋版本链真冒烟 v1→v2→v3）。配置载体裁定（DB 表＋种子自动落库，不走 yaml）＝**采纳**（版本轴/via 回链/修改历史是文件真源承载不了的语义，理由成立）。疑点 1（六键 vs「七节」计数）＝采纳＋挂 teach 对齐批（枚举无语义歧义，实现零改动）；2（state 维持合同字面 pending、生效性由 version.via 回链承载）＝采纳——硬纪律 1 的正解；3（实施批定值：上限 1–100/high≥low 400/#CFG 自铸随 A3 批）＝采纳挂账。

## P1-08a chat 装配骨架后端（A1 主链第一拍）

- **先读**：teach `A1-问一问.md`（四层流水线/六路装配 F56/澄清帧）；`D2` v0.2（qa_behavior 消费口径）；00 册 §6（SSE 帧协议＋三保留帧）；平台 `app/api/chat.py`（阶段 0 骨架）/ `infra/eventbus.py`。
- **范围**：SSE 骨架填肉（19 类业务帧注册＋done/error/replay_truncated）；安检层；**六路装配**（F56 全扫全收集/候选上限 4 支/落空进建议池）；意图裁决；**三链分派缝**（检索/FAQ/图谱链位接口留缝，缝内暂回"该能力暂未开通"——17 链枚举全注册）；澄清帧有界循环（缺参反问策略，qa_behavior.clarify_strategy）。
- **验收**：帧协议真跑（提问→done 占位→帧序断言）；装配层六路真扫；未开通话术逐链核对；四门禁绿。
- 落地 ✅（2026-10-02）：
  - **chat 域**（`app/domains/chat/`，新域——98 §3.1 卡骨架拍，domain 厚/service 编排/store 三件先例同构）：`domain.py`（合同语义闭环）——**19 类事件帧 `FRAME_NAMES` 全注册**（A1 合同值照抄；`done/error/replay_truncated` 三保留帧名单自此单源在域，api.chat 引用之、P0-08 登记导入名不变）；SEC_CHECKS/MATCHERS/CHAIN17 合同常量照抄（flows/common.jsx 同源）；安检层字面规则（注入特征模式库——「忽略指令」族 promptfoo 红队同源骨架集＋禁用词索引 W-F19「老完成率」〔设定书 §6 废弃口径〕；拦截话术照抄 SCENARIOS——「平台规则不可能被对话内容覆盖」/「产量完成率」出路指引）；@ token 解析（「类型·名称」结晶体）；澄清帧机器（口径两译帧构造〔sem_metric.ambiguous＋calibers 同源消费——A1 澄清场景 verdict 示例同形〕/候选上限 4 支截断＋「另有 N 支未列出」/默认口径项 primary 恒带〔「不选了，按默认口径出数并标注」合同文案〕）；建议池 `SuggestionPool`（落空信号按 matcher×归一问句攒频次——F60 晋升闸孤例不进池）；17 链分派器 `ChainDispatcher`（闭世界枚举越界即拒＋三链分派缝 `SEAM_CHAINS` 注册位＋`register()` 08b 填肉入口）。`store.py`（chat 三表 ORM——99 §2.2 逐字段：chat_session〔`group` 保留字 ORM 自动引号〕/chat_message〔role CHECK＋uq(session_id,seq)＋answer jsonb 与 SSE answer 帧同形〕/chat_run〔status 六值 CHECK＋verdict/pending_interrupt jsonb＋clarify_count smallint CHECK 0–1＝「最多弹一次」存储强制〕；19 帧不落库〔99 §1.5〕；ensure_chat_tables 幂等；会话历史写口 ensure_session/append_message/touch_session＋`recent_qa_pairs` 料源读口）。`service.py`（四层流水线编排，见下）。
  - **四层流水线**（service.py，全服务端前端零编排）：①安检——注入扫描/禁用词索引/身份与数据域三道逐条翻（blocked→answer alert 拦截话术→done 终局＋拦截审计）；②装配——@ 前门直取（取不到＝落空拒答，A1 端点 4 注记；被 @ 一路匹配器让位、候选经前门在场＝倾向≠直通）＋六路匹配器全扫全收集（FAQ 索引＝faq.match_index 读口/指标卡台账＝semantics 指标精确/术语台账＝semantics 术语精确/工具清单＝注册表未建落空/分析工作流＝运行时未建落空/报告索引＝向量＋BM25 两腿）＋图谱缝（08b 前落空）＋落空进建议池＋assembly 帧（anchor_line/slots/terms/candidates/chains＝17 链全文）；③裁决——骨架期确定性路由（FAQ 精确命中＋faq_direct_hit 开→FAQ直出链；口径两译未消歧→need_clarify/chain null/低置信→澄清挂起；其余→检索问答链——真实裁决唯一真源＝D2 模型随 08b 接线，skeleton 标注随 confidence 后缀下发；clarify_strategy=ask_missing 消费）；④分派——17 链闭世界分派，三链分派缝 08b 填，未实现链回「该能力暂未开通」话术（answer alert info 带链名）。
  - **澄清帧有界循环**：挂起帧落 chat_run.pending_interrupt（clarify_count CHECK 0–1）；`resume()` 带参并入原问句上下文（输入严格变多）→重过安检（不免检）→带参重判→续推 done；两跳终态＝回流后再触发澄清不弹第二帧、走默认口径锁定（notice）照常分派；`resume_preflight` 开流前同步校验（404/409/400 走 HTTP 错误包——00 §3.1「SSE 内异常不走 HTTP 错误包」判据）。
  - **SSE 填肉**（`app/api/chat.py`）：P0-08 骨架判据全保持（信封渲染/Last-Event-ID 非整数 400/重连形态 replay_truncated 收场②话术原文）；19 类业务帧由域面产出（SseEvent 流）、api 层枚举帧序渲染信封；流内异常 error 帧收场安全网（00 §6.1）；question 空 400（A1 错误码草案第一行）；端点 5 `POST /api/chat/runs/{run_id}/resume` 挂载。
  - **kb 域增件**：`index_search` 检索读面（98 §3.4 卡运行时读缝——chat 六路报告索引路消费，不经 HTTP）：向量腿（EmbeddingBackend 缝——P1-04 收尾裁决①「P1-08b 用现有 EmbeddingBackend 缝」）＋关键词腿（`trigram_coverage` 子串覆盖率——P1-04 裁决②「阶段 1 关键词路＝trigram 子串匹配」，pg_trgm GIN 索引随 P1-10 上、查询语义不变）；同片段两腿取高分腿、按分倒序 top_k；kb.domain 增 IndexHit/cosine_similarity/trigram_coverage。
  - **装配**（main.py）：ensure_chat_tables 入 lifespan；chat 域读缝组合根注入（qa 配置＝retrieval.effective_config 投影 qa_behavior 五字段/台账＝semantics 读接口〔B5 边界：chat 必须走 semantics 读口〕/FAQ＝faq.match_index/报告索引＝kb.index_search/图谱＝08b 前恒空 stub——B9 同款运行期只见 callable）；**P1-06 疑点 6 收口：faq `session_loader` 注入 `chat.recent_qa_pairs`——装配即通**（B3 扫库料源不再空态说明）。
  - **B12**：`chat.ask.received`（受理——票面）＋`chat.ask.blocked`（拦截——00 §8.2「拦截也是审计事件」）；api 层装配根注入 security.audit，域不依赖 security。
  - **Alembic 0009**（`20261002_0009_chat_baseline.py` 三表手写；env.py 登记区补挂 chat store）→ **upgrade head/downgrade 双向实跑过**（PG16@5433：0009↔0008 单档往返＋base→head 全链重放，终态 0009 head；数据影响：仅新增 chat_* 三空表不触既有表；往返清掉的 sem 种子已重跑同步器补种 counts 11/15/10/5/4/10/3 零告警＋faq 演示种子重装）。
  - **测试**：`tests/domains/chat/` 37 条——`test_chat_domain_unit.py` 16 条（19 帧注册/合同常量照抄/安检字面规则与拦截话术/澄清帧构造·4 支截断·溢出注记·默认口径项/建议池攒频次与晋升闸/17 链逐链未开通话术＋缝注册路由＋闭世界拒越界/@ token 解析）；`test_chat_service_unit.py` 21 条（全帧序列 session→stage→sec_check×3→match×6→assembly→verdict→answer→done/六路真扫〔假缝调用计数〕＋建议池落空/FAQ 直出闸 D2 配置驱动行为变化/澄清挂起-回流-两跳终态-409 族（终态 resume/审批回流/驳回缺理由/404）/安检拦截终局两态/@ 锚定落空拒答与直取锁定/图谱缝落空与填入/会话历史写口与料源读口〔挂起不进料源〕/B12 受理拦截审计）；`tests/api/test_chat_sse.py` 重写 14 条（P0-08 骨架断言全保留：信封/replay_truncated 断点续序/400/401/缺头默认角色＋新增：全帧流/resume 端点往返与错误包族/B12 审计读面）；kb `index_search` 3 条（两腿合并去重/空语料/覆盖率边界）。
- 验收自证 ✅：四门禁——ruff（app+tests+migrations）0 错 / mypy strict **63 文件零错** / pytest 带 PG16@5433 **517 passed 2 skipped**（skip＝KB_SMOKE/FAQ_SMOKE 门控冒烟自身；无 PG 底座 480 passed 39 skipped）/ lint-imports **5 契约 KEPT**；**真装配冒烟（PG16@5433 真库——骨架层零 LLM 依赖，票面「冒烟零成本」兑现）**：lifespan 实启（faq.session_loader 注入实证）→ask 全帧流真跑（真台账命中「产量完成率」→检索问答链→未开通话术→done）→澄清帧真跑（sem_metric #2 calibers「开井日历折算/检修剔除」同源）→resume 两跳终态 done 无第二澄清帧→B12 审计 chat.ask.received 真查 3 行→recent_qa_pairs 2 组真库可见；HTTP 层 uvicorn 实跑 SSE 逐帧实证（session/stage/sec_check×3/match×6 真库命中注记）。

> **与合同/票面的差异点登记（现实约束按现实落地，语义不私改）**：
> 1. **「六路」机制映射**（票面速记「@锚定直取/台账精确/术语/向量/BM25/图谱/FAQ」七机制 vs F56 合同六路匹配器名）：match 帧 matcher 值＝F56 合同六路（FAQ 索引/指标卡台账/术语台账/工具清单/分析工作流/报告索引——合同值不可改）；机制映射——台账精确＝指标卡台账路、术语＝术语台账路、向量＋BM25＝报告索引路两腿（F56 注记「FAQ/报告＝同池 BM25＋向量」）、FAQ match_index＝FAQ 索引路、@锚定直取＝S1 前门装配（非匹配器——D2「两级管辖边界」同款）。**图谱缝落位＝装配池候选源**（非六路匹配器——F56 六路无图谱路；不发 match 帧、落空进建议池、08b 注入真图检索）＋17 链分派缝图谱问答链占位双落点。挂 Owner 复核。
> 2. **被 @ 路的 match 帧形状**：F56「被 @ 的一路不过匹配器」——让位路帧 status=hit＋note「@ 已前门直取——匹配器让位」（候选在场＝倾向≠直通的物质基础，显示为命中而非未到）；合同未冻结该形态，挂 Owner 复核（备选＝不发帧让 UI 留「·未到」）。
> 3. **骨架期裁决为确定性路由非模型裁决**：真实裁决唯一真源＝D2 模型（F56③·A1「真实意图路由唯一真源」）——骨架期以确定性规则占位（FAQ 直出闸/口径两译澄清/检索链缺省），confidence 档位值带「骨架期确定性路由——D2 模型裁决随 P1-08b 接线」标注后缀（合同允许「页面标注后缀」形状）；FAQ 精确命中标「高（FAQ 精确命中）」＝字面索引命中的诚实值。零 LLM 依赖＝票面「冒烟零成本」兑现。
> 4. **澄清触发源＝口径两译**（sem_metric.ambiguous＋calibers——P1-01「台账 calibers 照抄 C1 现值（A1 澄清帧同源消费）」注记的兑现）；qa_behavior.clarify_strategy 消费＝ask_missing 档开闸（现值唯一档，其余档位待实施批定）；缺参反问类（askback 时间窗三选一）需链内槽位检测，随 08b D2 解析接线（挂差异）。
> 5. **建议池为进程内缓冲**：F56「落空信号进建议池」的治理闭环（攒频次→聚簇→提案→Owner 审→登记）消费方＝C2 提案池（域未上线）——chat 只立信号收集面（F60 晋升闸孤例不进池已落），持久化与 sg- 发号权随 C2 落地批（98 卡 chat 聚合无建议池聚合）。
> 6. **page_context 受理不消费**：A1 端点 4 形状全量受理（body 模型），F44 确定性注入随 wells 读模型批接线（98 卡 chat 依赖 wells——context_pack 同源）。
> 7. **断线重连形态保持 P0-08 判据**：resume_run_id/Last-Event-ID 头 → replay_truncated 收场（infra.sse_channel 未建、无事件缓冲）；run 存在性不校验（缓冲补不出任何帧）——P1-08c 接缓冲前保持。
> 8. **错误码新立三值**（A1 错误码草案只冻结 HTTP 码与人话，code 按 00 §3.3 `<域>_<语义>` 落）：`chat_param_invalid`（400：question 空/澄清选项无效/Action 链驳回缺理由）/`chat_run_not_found`（404）/`chat_run_state`（409：非 interrupt 挂起态——对已终态 resume/二次澄清/重入 clarify）＋`chat_stream_failed`（流内异常 error 帧安全网 code）；登记本节。
> 9. **安检评估序＝seq 序**（注入扫描→禁用词索引→身份与数据域，照 SEC_CHECKS 展示序）；合同注「禁用词 0 号位先于一切解析」指其先于语义解析的字面闸属性——前两道同为字面终局闸，序差无语义差，如实照序评估。
> 10. **chat_session.group 索引方向**：99 §2.2「idx (user_id, updated_at desc)」落两列普通索引（desc 方向为性能细节；ORM 与迁移双轨同形）——随 P1-11 收官批对齐；chat_artifact_task/chat_artifact/chat_tool/chat_scenario 四表不属本票（产物任务/工具注册表/场景注册表随其端点票落）。


## P1-08a 收尾裁决（主窗口，dd9739d）
> 全绿（带 PG 517 passed＋零 LLM 冒烟：全帧流/澄清两跳终态/B12/料源缝装配即通）。疑点 1（六路映射：向量+BM25 归报告路两腿/图谱缝双落点）＝采纳（match 帧 matcher 值照抄合同六路——映射忠实），Owner 里程碑复核；2（让位路帧形状）＝采纳 additive 登记；3（骨架裁决＝确定性路由，confidence 带 skeleton 后缀）＝采纳——诚实标注正确，模型裁决 08b 接线；4（建议池进程内）＝采纳挂账（F60 闸已落，持久化+sg- 发号随 C2 批）。

## P1-08b chat 三链后端（A1 主链第二拍）

- **先读**：teach `D2` v0.2（检索瀑布/命中即停/双路合并/精排三档/兜底两策——本拍消费方）；`B3` v0.2（已发布消费面）；`B5` v0.2（图谱问答链）；`B2`（citation/locator）；A1 册（引用 fail-closed 节）。
- **范围**：**检索链**（D2 当前生效配置驱动：三级顺序/早停/两路并发+合并/前 N 精排/兜底 fixed/free）；**FAQ 秒回**（只消费已发布，直出开关 faq_direct_hit）；**图谱问答链**（B5 图遍历+出处）；**cN 引用 fail-closed 完整实现**（伪造/失锚引用拦截，B2 回跳锚生成）。
- **验收**：三链各真跑且 D2 配置改动可见行为变化；fail-closed 单测（编造引用被拦）；四门禁绿。
- 落地 ✅（2026-10-02）：
  - **三链链体**（`app/domains/chat/chains.py` 新建——`ChainDeps` 注入缝集合＋三链 async-generator 链体逐帧产出；ChatService 构造时经 08a 的 `dispatcher.register()` 缝口注册）：
    - **检索问答链**（D2 生效配置驱动 S 级全链）：S0 身份四要素确认→S1 显式锚定（受第 1 级开关管辖）→S3 台账精确（第 2 级）→S4 双路召回（**向量 topK1＋trigram topK2 并发**——kb 新读面 `index_search_dual` asyncio.gather 两腿各自 topK 倒序）→合并（**rrf_rank k=60 固定推荐值**〔D2 开放问题 8 裁决不入合同〕/concat 照配置）→前 N→精排三档→FAQ 路扩检→S5 图扩展（**未启用——直通跳过不花开销**，合同值）→S6 资格裁决（**4 支上限**截断＋「另有 N 支未列出」notice＋refuse_threshold 拒答判定）→S7 权威源回读（指标台账精确核对——不在现行指标目录拦下不代答＋口径在账校验）→生成（**petro-main** 经注入 completer——B6）→**citation fail-closed**（见下）→citation_format 切呈现（**page＝正文角标展开 [label]**／**code＝保持 [cN]** 编号＋真实出处收敛引用清单）→token 流式（切片下发）→citation 帧→answer kind=text。**命中即停**：S1/S3 命中即跳 S3~S5/S4~S5（装配层材料与 S6/S7 不受早停影响——D2 两级管辖边界；关＝逐级全跑）；**兜底两策**：证据空/低于低分线→fixed＝D2 fallback.text 原样（answer kind=alert）／free＝无据生成＋「（未依据报告库）」合同标注。
    - **精排三档**：fast＝融合序放行（档①小而快排序模型未选型——挂批）；llm＝petro-main **逐条打分**（打 N 条就是 N 次调用；任一解析失败整批按原顺序放行——W-F34-2 回退原序不炸链）；compound＝**0.6×模型分＋0.3×检索基础分＋0.1×来源分**（SOURCE_SCORES 实施值常量）＋**MMR λ=0.7**（trigram Jaccard 相似度贪心）。
    - **citation fail-closed**：模型输出 [cN] 解析（容忍全角括号［cN］变体）→每条引用校验 locator——fragment_id 经 kb 新读面 `fragment_anchor` **必须真实存在且报告归属一致**；不在编号表（伪造别名）/锚不上的引用**剥除＋notice「已拦截 N 条失锚/伪造引用——绝不带病出帧」留痕**；幸存引用才发 citation 帧＋answer.citations。
    - **FAQ 秒回链**：match_index 精确命中（只消费服务中——v0.2 审核流闸）→直出答案＋citation（kind=台账条目·locator.section=常见问题库）＋**no_model=true**（零模型调用有测试断言）；`faq_direct_hit=false`→精确命中**并入检索链继续**（装配层材料不受 D2 开关与早停管辖）；命中执行前失效（索引竞变）→兜底不硬答。
    - **图谱问答链**：路由＝图谱缝命中＋（关系问句信号 RELATION_SIGNAL_RE｜报告索引未命中）→graph 缝一跳邻域边证据→生成带图出处 citation（**kind=图谱**、locator 携边出处 chunk/report）→边出处 chunk 锚 fail-closed 同闸；缝内零边→兜底。
  - **模型裁决接线**（08a 骨架确定性裁决升级——票面字面＝confidence 真实计算＋skeleton 标注退役）：`compute_confidence`＝报告索引最高证据分基础分＋台账精确≥0.9＋@ 前门直取≥0.95＋FAQ 精确=1.0（检索得分＋装配信号合成）；`confidence_label`＝D2 confidence_thresholds 阈值判定（高≥0.8/中/低<0.4——阈值可配档位语义不新增）＋来源标注后缀（A1 合同允许形状，「骨架期」后缀退役）；**低 <low 必弹澄清帧**（F56 拍板）——候选在场弹**候选澄清帧**（S6 多候选语义，无默认项、超 4 支截断溢出注记），无候选直派检索链走兜底；澄清挂起帧增 **subtype（caliber｜candidates）**——candidates 回流：带 choice＝焦点并入问句重判续推、**不选＝拒答终态**（宁可不答不瞎猜——缺的是用户意图不代选）、二次触发＝锁定候选两跳终态（有界循环不变，clarify_count CHECK 0–1）。
  - **kb 增件**：`index_search_dual`（S4 双路并发读面）＋`fragment_anchor`（citation fail-closed 锚校验读面——父块不对外寻址同象 None——F30）＋**hit_text 落列修复**（入库/派生块置换/片段修正时写命中句——99 §2.5 列此前恒空、关键词腿读不到文本，08b 双路语义必需；faq dedup_corpus 知识库面同修复）＋**pg_trgm GIN 索引**（hit_text——P1-04 收尾裁决②倒排落法；ensure_kb_tables 与 Alembic 0010 双轨同形，扩展不随 downgrade 撤——vector 同惯例）＋IndexHit 增 `text` 列（500 字——生成上下文用，80 字 snippet 不足以作答）。
  - **faq 增件**：`search_similar`（FAQ 路扩检候选供给面——向量余弦排序、只服务中条目可达；FaqHit 增 score）。
  - **组合根**（main.py）：retrieval_config_loader（effective_config **六节全量投影**——检索链全链消费）＋faq_searcher＋index_searcher_dual＋fragment_anchor_loader＋**graph_searcher 真检索**（图开关开启的库逐座 read_net、问句实体一跳邻域边——GraphHitFace 增 source_chunk_id/source_report_id 边出处；图存储不可用记告警不阻断问答）＋completer（gateway——B6）注入 ChatService；caller 归因＝chat.retrieval.answer/rerank/graph.answer/fallback（记账 note 携带——caller 列随 P1-10）。
  - **Alembic 0010**（`20261002_0010_kb_trgm_index.py`）：pg_trgm 扩展＋hit_text GIN 索引→**upgrade/downgrade 单档双向实跑过**（0010↔0009＋base→head 全链重放，终态 0010 head；数据影响：仅新增一索引；往返清掉的种子已重跑同步器补种 counts 11/15/10/5/4/10/3 零告警＋faq 演示种子重装）。
  - **测试**：`tests/domains/chat/test_chat_chains_unit.py` 新建 **27 条**（早停开/关两态帧序变化实证/三级开关关/topK 驱动/合并两策/精排三档（llm 打分逐条计数·解析失败原序·compound）/4 支上限＋溢出/refuse_threshold 上下两态/free 标注/S7 拦下不代答/**fail-closed 四态**（编造别名 c9 剥除＋notice/失锚 fragment 丢弃/格式两格呈现/报告归属不一致拦截）/faq_expand_rounds 轮次·过线·硬顶/FAQ 直出 no_model＋失效兜底/图谱链 citations·失锚·零边兜底/**qa_behavior 五字段消费矩阵**）；service 单测重写扩充（置信度档位阈值驱动/低置信候选澄清有界循环三态/图谱路由/FAQ 并入检索）；域单测＋检索链纯语义件 10 条（RRF 同秩融合/concat/composite 权重冻结/MMR 近重复让位/引用解析剥除重写/置信度合成与标注/候选澄清帧/token 切片/关系问句信号）；kb＋3（dual 两腿各自倒序/空库/anchor 三态）；faq＋1（search_similar 排序·可达域）；kb PG＋trgm 索引断言（pg_indexes indexdef gin）；`tests/test_chat_smoke_real.py` 新建（**CHAT_SMOKE=1** 门控——真 PG/MinIO/Neo4j/gateway.complete）。
- 验收自证 ✅：四门禁——ruff（app+tests+migrations）0 错 / mypy strict **64 文件零错** / pytest 带 PG16@5433 **566 passed 3 skipped**（skip＝KB_SMOKE/FAQ_SMOKE/CHAT_SMOKE 三个门控冒烟自身；无 PG 底座 529 passed 40 skipped）/ lint-imports **5 契约 KEPT**；ontology/ci.sh 不涉（ontology/ 零改动）。**真装配冒烟**（CHAT_SMOKE=1，真 PG16@5433＋MinIO＋Neo4j＋gateway.complete petro-main）：备料（建库→抽取设置→真传→五步 done→graph 支路真抽取立边）→**FAQ 秒回链**（「N-02 井是什么时候投产的？」→FAQ直出链 no_model=true、零模型调用、citation 常见问题库）→**检索问答链**（真 LLM 生成、token 流式、citation 帧、**锚真值**：locator.fragment_id 与命中报告经 B2 片段台账逐条对账一致）→**图谱问答链**（「N-02 井隶属哪个区块？」→图谱问答链→kind=图谱 citation→边出处锚真值）→B12 chat.ask.received 三轮全留痕＋gateway 记账 note=chat.retrieval.answer/chat.graph.answer（petro-main）真查在案。
- **差异登记（现实约束按现实落地，语义不私改）**：
  1. **精排 fast 档阶段 1＝融合序放行**：档①「小而快的排序模型」未选型（重排模型随 embedding 选型批——P1-04 收尾裁决①同批）；llm/compound 两档真跑（逐条打分真调用、真计费）。三档 key 与档名合同值不动。
  2. **来源分（compound 0.1 成分）＝实施值**：SOURCE_SCORES 常量（anchor/ledger 1.0、faq/graph 0.9、检索文本 0.6）——合同只冻结权重 0.6/0.3/0.1 与 λ=0.7，成分定义未冻结，常量集中 Owner 可调。
  3. **「流式」＝token 帧切片下发**：gateway.complete 为整段应答（B6 无上游流式接口）——服务端 fail-closed 校验**完成后**按 24 字切片发 token 帧（SSE 流式呈现语义、fail-closed 语义完整优先于边生成边出帧）；真上游流式随 B6 流式接口批。
  4. **裁决路由仍为确定性信号序**（FAQ 直出闸→口径两译澄清→图谱关系信号→置信度档位）：真实意图路由唯一真源＝D2 模型（F56③ LLM·结构化输出）——本拍按票面字面落「模型裁决接线＝confidence 真实计算＋骨架标注退役」，LLM 意图裁决随后续批接线（挂 Owner 复核）。
  5. **citation kind 四值枚举无 FAQ 专值**：FAQ 直出 citation 落「台账条目」族（服务资产条目）；图谱落「图谱」（合同值域内）。FAQ 块 chunk_type=faq 双写未实施（P1-02a 差异 4 同源——faq 无 kb 片段行），FAQ citation locator 无 fragment_id、以 section=常见问题库承载出处。
  6. **hit_text 落列修复**（kb——P1-02a 遗留缺口顺手收口）：99 §2.5 列此前入库管线未写（恒空），关键词腿与 faq dedup_corpus 知识库面读不到文本——本票入库/派生块置换/片段修正三处落命中句，双路召回（S4）语义由此成立。
  7. **图谱缝降级**：图存储不可用→告警日志＋按落空处理（问答主链不阻断）；B5 管理面端点「显式抛 GraphStoreUnavailableError 不静默降级」语义不变（管理面/运行面两类语义分立）。
  8. **S 级过程行＝node_line 帧**（key=S0/S1/S3/S4/S5/S6/S7——瀑布级合同键；D2 行为规则 4 检索动作级管辖边界逐行可观察）；node 帧键与全景树 41 节点键对齐归 P1-08c（本拍零 node 帧）。
  9. **图谱问答链路由信号**＝graph 缝命中＋（关系词面｜报告索引未命中）——确定性路由（差异 4 同族），挂 Owner 复核。
  10. **检索范围＝全库**（kb 级检索不带库过滤）——A1 asks 无 lib_id 入参（合同形状），多库报告同池召回；冒烟锚真值对账按「citation 所指报告」逐条核（全库面语义）；按库过滤随 A1/检索范围批（如需）。
  11. **test_config.py 缓存隔离修复**（测试侧）：`test_load_models_config_hot_reload` 残留 m1/m2 全局缓存会让同进程后续真 LLM 消费判 NoAvailableRoute——补 autouse 复位 fixture（gateway/llm_client 测试同款纪律；P0 遗留，chat 冒烟为首个真 LLM 消费方故显形）。

## P1-08b 收尾裁决（主窗口，26e3541）
> 全绿（带 PG 566 passed＋CHAT_SMOKE 真冒烟：三链真跑＋citation 锚逐条对账一致＋记账落账）。裁决：1（fast 档＝融合序放行）＝采纳挂 embedding/重排选型批（P1-11 前 Owner 拍板）；2（SOURCE_SCORES 实施值）＝采纳；3（流式＝整段切片）＝采纳（B6 无上游流式，fail-closed 优先于早期呈现）；4/9（LLM 意图裁决挂批）＝采纳挂账 Owner 里程碑复核；5（citation kind FAQ 无专值）＝采纳挂账（faq 块双写同源批）；6（hit_text 落列修复）＝采纳；7（图存储不可用降级不阻断）＝采纳（管理面显式抛错语义不变，可用性取舍登记）；10（检索范围全库）＝采纳（asks 无 lib 入参合同口径）；11（test_config 缓存隔离）＝采纳（P0 遗留缺口修复）。

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
