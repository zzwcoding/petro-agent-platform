# 本体仓 Schema · 七模型精简版 + GLS 术语扩展（v9 蓝本 + 运行期字段预留）

> 本文是本体 YAML 的 schema 文档（人读）；机读消费方两份：
> `model-registry.json`（模型注册表：camp/consumers/profiles/dependsOn）、`model-deps.json`（类型层依赖白名单 + ID 前缀表）。
> 执行闸：`tools/schema_check.py`（语义 CI L1–L4 + 票 41 L3 确定性子集，断言表 `specs/schema_check.md` AC1–7 + 票 10 GLS-AC1–4 + 票 11 一致性对 §14 + 票 13 必填闸 REQ-AC1–6 + 票 16 禁用词拦截面 BAN-AC1–4 + 票 38 重复 id DUP-AC1–2 + 票 41 L3 确定性闸 L3-AC1a–d）。
> 蓝本：OMF v9 七模型（references/omf-spec-digest.md §0/§16，下注 `v9 §x`）；裁剪决定均注明出处。
> GLS 术语模型为本仓自定义扩展（OMF v6/v9 均无，票 10 走"元模型错→框架版本演进"路由进 schema，演进账见 CHANGELOG.md）。

## 0. 定位与裁剪总则

- 一模型一 YAML、固定文件名、文件内 `model_type/version/domain` 三公共字段——照搬 OMF 文件约定（digest §16 第 1 条）。
- 一期不做 ME 事件/M4 场景/MM 映射/MI 接口（v9 同款裁剪：先同步世界，异步需求实证后回加，PRD F1；digest §16 第 6 条）。
- 字段换义宁可新增字段不复用旧名（digest §16 第 10 条）；被换义退役的字段名进 `model-registry.json` 各模型的 `lockedFields`，闸在 L4 强制（AC7）。
- 字典项停用不删除（digest §16 第 9 条）：`enabled: false` 保留行，删除走影响分析。

## 1. 公共字段与文件约定

每个模型元文件第一层必须有：

| 字段 | 必填 | 说明 |
|---|---|---|
| `model_type` | ✓ | 模型类型标签，取值见 model-registry.json 各模型 `modelType`（OBJECT/BEHAVIOR/RULE/ACTOR/FLOW/REPORT/UI/GLOSSARY） |
| `version` | ✓ | 模型元文件版本（语义化三段，引号包裹） |
| `domain` | ✓ | 所属域标识，与域 manifest.json 的 `domain` 一致 |

文件命名固定：`m1-object-model.yaml` / `m2-behavior-model.yaml` / `m3-rule-model.yaml` / `m5-actor-model.yaml` / `m6-flow-model.yaml` / `m7-report-model.yaml` / `mu-ui-model.yaml` / `glossary-model.yaml`（v9 §10.3；GLS 照 `mu-ui-model.yaml` 非数字先例，票 10）。文件名与 `model_type` 的对应真源 = model-registry.json 各模型 `yamlFile`，错挂 = L1 违规（票 10 AC4）。

每个域一个目录（`ontology/<域>/`），目录内必须有 `manifest.json`：

```json
{"domain": "bohai", "label": "渤海油田产量域", "profile": "v9-full", "schemaVersion": "1.0.0"}
```

`profile` 引用 model-registry.json 的 profile 组合名；未启用的模型文件出现 = L4 违规（AC6）。反向同理（票 13）：**profile 启用的模型缺文件且 manifest 无豁免 = L4 `missing-model-file` 违规**。豁免走 manifest 可选清单 `omittedModels: [{"model": "MU", "reason": "…"}]`——条目必须带非空 reason（无理由 = 无效豁免照红），引用未注册模型 = L1 红。适用场景：素材证据不支撑某模型、经裁决有意不建（如 bohai 的 MU，理由引裁决记录）。

**素材目录约定（票 34，2026-09-20）**：`patterns/` = 建模素材区，不作为域扫描——schema_check 域发现对名为 `patterns` 的子目录整体排除（排除只按目录名，不按内容：其下将来出现含 manifest 的真域结构也不作为域扫）；模式件是素材不是域，**不补 manifest**（manifest=域声明，素材目录补=撒谎）。patterns/ 下模式件的结构纪律由出厂集 `fixtures/pattern-library/` 与归档闸 ontology-pattern 类（specs/archive-registry.json）承载，不经语义闸域扫描。

**元素级运行期预留字段（全模型可选，一期只定义不消费，PRD F1「运行期四外衣」）**：
- 元素级 `version`（String）：元素独立版本，供运行期消费方做兼容判断。
- 元素级 `validFrom`（ISO 日期）：有效期起点，供运行期判断"当前可消费版本"。
- 预留字段闸只做"存在即放行"，不做语义消费——防止 schema 二次断裂（R7、digest §16 第 10 条）。正例实测承载：出厂集 `req-ac4-reserved-fields`（元素级 version/validFrom + M2 contract/riskLevel/idempotent + M3 narrative，票 13 REQ-AC4）。

**元素级结构性必填（票 13，机读真源 = model-registry.json 各模型 `requiredElementFields`）**：口径 = 身份（id/name，含各模型具名 ID 键）+ 类型判别（behaviorType 等）+ 检查锚点（一致性对/引用扫描依赖、缺失即静默跳过的字段）+ 载荷容器（attributes/activities 等空壳即红的容器）；闸 = schema_check L1 `required-field`（含空壳文件判定）。schema.md 全字段集（preconditions 等）**不在**必填闸（缺口清单留后续演进票）；逐模型推导表与证据见 `lessons/13-机读必填字段闸.md`。

**违规语义注记（票 27，2026-09-19）：元素枚举去 id 锚定**——`required-field` 闸对模型文件主集合（aggregates/behaviors/rules/actors/roles/permissions/flows/query_reports/screens/terms 等顶层 list-of-dicts 集合键）内的**每个字典**按元素枚举，不再以「有 id 键」为枚举前提：无 id 元素报缺必填身份字段（id 已在各模型必填集首位；M5=actorId/roleId/permissionId、MU=screenId 同判），修掉「无 id 元素混入合法元素即静默逃逸」盲区。**空壳判定随之收窄**为「主集合键缺失或集合为空」——集合里有字典就逐元素报缺 id，空壳不再兜底；纯空集合（`terms: []`）语义不变仍报空壳。嵌套子结构（attributes[]/refRules[]/activities[] 等）不是元素、不进枚举（由 ref 扫描与字段检查覆盖，其字典无 id 合法）。负变体出厂集：`mid-ac1-mixed-missing-id`（混入形态）/ `mid-ac2-pure-missing-id`（纯无 id 域），断言 MID-AC1/2。

**同域元素 id 唯一（票 38，2026-09-20）：`duplicate-id`，L1 身份族**——**唯一性判定键 = manifest 域值**：同一 domain 值之下，元素 id（`id`/`*Id` 定义键——非 ref 键、值带注册前缀，口径同悬空引用的定义收集；M5 的 actorId/roleId/permissionId 跨键同值同判）不得重复；**跨域不判**（fixture 各域合法复用同形 ID 是合法现状，两目录同域值 = 同一命名空间照判）。实现挂在票 27 元素枚举产物上：建 域值→id→(file,line,键,名) 索引，撞即报且报文含**双位置**（先出现+后出现 file:line 与元素名）——票 27 前重复 id 曾静默（枚举以 id 为锚，后者被先出现者吞）、票 27 后双双枚举但无重复判定，本票补齐；重复≠悬空（ref 指向重复 id 照常解析，dangling-ref 不重复追责）。文件名错挂的文件跳过本闸（红因纯净，沿票 13/16 先例）。负变体出厂集：`dup-ac1-same-domain-duplicate-id`，断言 DUP-AC1/2。

## 2. ID 前缀与 ref 命名约定

**前缀即类型标签**：所有元素 ID 必须带模型前缀，使 ref 无需 schema 外知识即可机械校验指向（digest §16 第 2 条）。该条并注明双向一致对详见 digest §12.1/§12.2——**一致对清单权威出处=digest §12.2**（本仓落点见 §14；票 11 曾误引 §16.4，勘误 2026-09-19，见 docs/reviews/2026-09-19-phase2-batch1-tickets10-12.md）。前缀→模型映射的真源在 `model-deps.json` 的 `idPrefixes`：

| 模型 | ID 前缀 | 元素 |
|---|---|---|
| M1 | `AGG-` / `ASSOC-` / `DICT-` | 聚合根 / 聚合关联 / 数据字典 |
| M2 | `BH-` | 行为（本仓约定 `BH-{域}-{动宾}`；OMF 的 `{EntityAlias}_{ActionName}` 无前缀不可机械校验，此为本仓对 OMF 的显式偏差） |
| M3 | `RULE-` | 规则（`RULE-{域}-{Seq}`） |
| M5 | `ACTOR-` / `ROLE-` / `PERM-` | 参与者 / 角色 / 权限（`PERM-{域}-{Action}`） |
| M6 | `FLOW-` | 流程 |
| M7 | `QR-` / `RPT-` | 查询 / 报表 |
| MU | `SCR-` | 屏幕（OMF 建议 `frmXxx`；同理改用可校验前缀，此为第二处显式偏差） |
| GLS | `GLS-` | 术语（`GLS-{域}-{Seq}`，票 10） |

**ref 字段约定**：
- 跨模型引用一律稳定 ID 引用，字段名统一 `xxxRef` / `xxxRefs` 后缀；少数沿用 OMF 原名（`targetAggregate`、`sourceAggregate`、`ownerEntity`、`appliedRules`、`requiredPermissions`、`inheritsFrom`、`roles`、`permissions`、`dictionaryId`、`dataSource`）——全集见 `model-deps.json` 的 `refKeys`。
- 禁止"只在 description 里写引用"：`AggregateRootRef` 类型属性必须显式 `targetAggregate`（digest §16 第 4 条）。
- 引用不得通过名称猜测；ID 变更必须过影响分析（v6 §8.6）。
- **依赖方向单向登记**：M7 与 M2 的严格一对一，依赖边只登记 M7→M2（M7.behaviorRef），M2 侧不设 `queryReportRef` 依赖边——本仓 M2 元素不写 `queryReportRef`，写了即 L2 依赖白名单违规（AC5 的判定依据）。一对一的双向一致性核验属 L2 一致性对清单（§14，票 11 落地 `consistency-*` 检查），反向经 ref 反查、无需 M2 侧字段。

## 3. 四层规则下沉判定（照搬，digest §16 第 3 条）

约束放哪，按判定逐级下沉，不许上跳：

1. 内置字段约束（`required`/`unique`）→ 2. 只依赖当前属性值 → `Attribute.refRules` → 3. 只依赖同聚合内部 → `Aggregate.invariants` → 4. 跨对象/跨行为/复用 → M3 规则。

## 4. M1 对象模型（OBJECT）

顶层：`aggregates[]`、`data_dictionaries[]`、`aggregate_associations[]`（v9 §2.4）。

**聚合根 AggregateRoot**：

| 字段 | 必填 | 说明 |
|---|---|---|
| id | ✓ | `AGG-{域}-{NNN}` |
| name / alias | ✓ | 中文名 / 英文标识符（代码映射用） |
| aggregateType | ✓ | 固定 `AGGREGATE_ROOT` |
| description | 可选 | |
| lifecycle | 可选 | 生命周期状态列表 |
| attributes | ✓ | 属性表（见下） |
| entities / valueObjects | 可选 | 子实体 / 值对象（组合） |
| invariants | 可选 | 聚合不变性：`name/expression/violationMessage/enforcedAt(ON_CREATE/ON_UPDATE/ON_DELETE/ALWAYS)` |
| version / validFrom | 可选 | 运行期预留 |

**属性 Attribute**（v9 §2.3.4）：

| 字段 | 必填 | 说明 |
|---|---|---|
| name / label | ✓ | 英文 camelCase / 中文展示名 |
| type | ✓ | `String/Integer/Decimal/Date/DateTime/Boolean/Enum/Money/ValueObject/AggregateRootRef/DictionaryRef` |
| required / unique / defaultValue | 可选 | `unique` 仅聚合根属性有效 |
| enumValues | type=Enum 时 | 不得与 dictionaryRef 并存 |
| valueObjectRef | type=ValueObject 时 | 引用值对象名称（对象内，不走全局 ID） |
| targetAggregate | type=AggregateRootRef 时**必填** | 指向目标聚合根 ID |
| dictionaryRef | type=DictionaryRef 时**必填** | `{dictionaryId, typeCode}`；dictionaryId 指向 DICT- |
| refRules | 可选 | 局部规则：`name/expression(用 value 指当前属性值)/violationMessage/enforcedAt` |

**数据字典**：`id(DICT-)/name/types[]`；DictionaryType `typeCode/typeName/items[]`；DictionaryItem `code(稳定存储值)/label(可改)/enabled(停用置 false，不删除)/sortOrder`。平级结构不定义 parentCode（v6 §2.3.5）。

**聚合关联 AggregateAssociation**：`id(ASSOC-)/sourceAggregate/targetAggregate(M1)/associationType(REFERENCE/DEPENDENCY)/sourceRole/targetRole/cardinality(ONE_TO_ONE/ONE_TO_MANY/MANY_TO_ONE/MANY_TO_MANY)/referenceField`。

## 5. M2 行为模型（BEHAVIOR）

顶层：`behaviors[]`（v9 §3.2）。

| 字段 | 必填 | 说明 |
|---|---|---|
| id | ✓ | `BH-{域}-{动宾}`（本仓前缀约定，见 §2） |
| name | ✓ | 中文动宾短语 |
| ownerEntity | ✓ | 所属 M1 聚合根 ID |
| behaviorType | ✓ | `COMMAND / QUERY`（v9 收敛） |
| triggerType | ✓ | `USER_ACTION / SYSTEM`（v9 收敛） |
| preconditions | ✓ | 谓词表达式列表，全部满足才可执行 |
| postconditions | ✓ | `{field, setValue}` 状态变更 |
| appliedRules | ✓ | 调用的 M3 规则 ID 列表（可为空列表） |
| requiredPermissions | ✓ | 引用 M5 权限 ID 列表（可为空列表） |
| syncTriggers | 可选 | v9 跨对象同步联动载体（见下） |
| **contract** | 可选 | **运行期预留**：行为对外契约描述（一期不消费） |
| **riskLevel** | 可选 | **运行期预留**：风险级（一期不消费） |
| **idempotent** | 可选 | **运行期预留**：幂等标记（一期不消费） |
| version / validFrom | 可选 | 运行期预留 |

**SyncTrigger**（v9 §3.2.2）：`ruleRef`（可选，规则只判断不改状态）、`behaviorRef`（**必填**，同步调用的下游行为）、`description`。硬约束：下游行为必须作用于**另一个独立聚合**（禁止同聚合自我联动）；查询行为 `syncTriggers` 必须为空；联动失败语义必须在 postconditions 或 M6 明确，禁止隐含吞异常。

语义边界：**规则只答条件是否满足、行为只答改变什么状态**，不可合并表达（v9 §1.4）。

## 6. M3 规则模型（RULE）

顶层：`rules[]`（v9 §4.3）。

| 字段 | 必填 | 说明 |
|---|---|---|
| id | ✓ | `RULE-{域}-{Seq}` |
| name | ✓ | |
| ruleType | ✓ | `VALIDATION / CALCULATION / DERIVATION / TRANSFORMATION / RISK`（v9 移除 EVENT_DRIVEN） |
| description | 可选 | |
| inputParams | 可选 | Param：`name/type/sourceField(如 dailyProduction.outputVolume)/required/description` |
| outputType | ✓ | DataType，校验类通常 Boolean |
| **expression** | 二选一 | 伪代码/DSL，不限定语言 |
| **narrative** | 二选一 | **运行期预留**：叙述式写法（自然语言规则文本）——与 expression 双写法，为运行期 Agent 消费预留"人话口径"（PRD F1） |
| reusedBy | 可选 | 引用本规则的行为 ID 列表（反向追踪） |
| externalEngine | 可选 | 外部规则引擎名 |
| **mark** | 可选 | 指标展示标记（`★`/`☆`，C1 指标卡徽标原样登记；展示标记非推荐位机制，C1 出入对账 8） |
| **grain** | 可选 | 统计粒度（沿 R5·§3 指标卡原文，如 `月/区块`） |
| **unit** | 可选 | 计量单位（沿指标卡原文，如 `%`/`吨`/`方`） |
| **modifiers** | 可选 | 修饰词列表（一词多义消歧，如 有效产量 的 剔检/开井日历） |
| **calibers** | 可选 | 口径支列表（多口径并列结构化登记，成员=口径名，如 有效产量 两支） |
| **defaultCaliber** | 可选 | 默认口径标识（calibers 多支在场时有意义；C1 仅指标 #2 登记，种子现值待素材） |
| **ambiguous** | 可选 | 歧义标记（Boolean；如 有效产量 一词两译） |
| **dispute** | 可选 | 口径争议注记（沿真源原文，如 递减增油 待联席裁决） |
| version / validFrom | 可选 | 运行期预留 |

**指标口径字段组（1.3.0，对齐矩阵 §3b 结构级/裁决项 e，Owner 2026-09-29）**：上表 mark～dispute 八项为 C1 指标口径卡的结构化登记位——粒度/单位/修饰词/口径支/争议注记是指标口径的**本体内容**（判据②零手养要求仓内有真源），非运行期派生；全部可选，存量文件零改动兼容。**`slot_name` 不落仓**：slots 剥法（剥首 ★/☆ → 剥尾括注 → 剥尾 η/T、β 保留）由服务端单点执行（票 93 禁止下游自留拷贝），`slot_name` 一律由 `name`+`mark` 派生，域文件不得存储该派生值。schema 契约 schemaVersion 1.0.0→1.1.0 受控小版本（裁决项 e/g：只加可选字段，必填结构与锁定字段不动），演进账见 CHANGELOG.md 1.3.0。

规则无副作用（只判断），被 MU 用作校验的规则必须无副作用（v6 §4.7.2 残余约束）。

## 7. M5 主体模型（ACTOR）

顶层：`actors[]`、`roles[]`、`permissions[]`（v9 §5.3）。

**参与者 Actor**：`actorId(ACTOR-)/name/actorType(HUMAN|SYSTEM，v9 移除 EXTERNAL)/roles(ROLE- 列表)/attributes(ABAC 条件用 Map)/version/validFrom(预留)`。

**角色 Role**：`roleId(ROLE-)/name/inheritsFrom(ROLE- 列表，多继承)/permissions(PERM- 列表)`。角色是 M6 人工任务的唯一参与人类型；删除/重命名前必须分析 M6 的 roleRefs。

**权限 Permission**：`permissionId(PERM-{域}-{Action})/targetType(BEHAVIOR|ENTITY)/targetRef(行为或实体 ID)/dataScope(ALL/OWN/DEPT/CUSTOM)/abacCondition(可选)`。权限不进 M7，由 M2 requiredPermissions 承载（v6 §9.6.7）。

## 8. M6 流程模型（FLOW）

顶层：`flows[]`（v9 §6.3，同步编排）。

| 字段 | 必填 | 说明 |
|---|---|---|
| id | ✓ | `FLOW-{域}-{NNN}` |
| name / description | ✓ / 可选 | |
| flowType | ✓ | `COLLABORATION / APPROVAL` |
| businessObjectRefs | ✓ | 涉及的 M1 聚合根 |
| roleRefs | ✓ | 流程允许承担人工活动的角色集合 |
| trigger | ✓ | `triggerType(MANUAL/BEHAVIOR/SCHEDULE/SUB_FLOW)` + 配套字段（v9 移除 EVENT） |
| startActivity | ✓ | **有且仅有一个**（活动 ID） |
| endActivities | ✓ | ≥1，必须指向 END 活动 |
| activities | ✓ | 活动列表 |
| version / validFrom | 可选 | 运行期预留 |

**活动 FlowActivity**：`activityId/name/activityType(START/END/USER_TASK/APPROVAL_TASK/SYSTEM_TASK/BEHAVIOR_CALL/SUB_FLOW_CALL/GATEWAY)/roleRef(USER_TASK/APPROVAL_TASK 必填，只能引用 ROLE- 且 ∈ 流程 roleRefs)/behaviorRef(BEHAVIOR_CALL)/subFlowRef(禁止成环)/ruleRef(可选，进入/完成/网关判断)/conditionExpression(流程局部条件)/approvalOutcomes(APPROVE/REJECT/RETURN)/nextActivities`。

## 9. M7 查询统计与报表模型（REPORT）

顶层：`query_reports[]`（v9 §7.4）。

| 字段 | 必填 | 说明 |
|---|---|---|
| id | ✓ | `QR-{域}-{NNN}` / `RPT-{域}-{NNN}` |
| name / alias / description | ✓ / ✓ / 可选 | alias 为 lowerCamelCase 稳定英文别名 |
| objectType | ✓ | `DETAIL_QUERY/LIST_QUERY/STATISTICAL_QUERY/REPORT` |
| behaviorRef | ✓ | 必须指向 M2 `behaviorType=QUERY` 行为；严格一对一（依赖边单向 M7→M2，见 §2） |
| sourceObjects | ✓ | `{objectRef(M1), alias(查询内唯一), primary(有且仅有一个 true), entityPath?, preAggregation?}` |
| joins / parameters / conditions | 可选 | QueryJoin/QueryParameter/QueryCondition 同 v9 §7.4 |
| resultColumns | ✓ | `{name/label/dataType/sourceExpression/aggregateFunction(NONE/COUNT/COUNT_DISTINCT/SUM/AVG/MIN/MAX)/...}` |
| groupBy / having / orderBy / pagination | 可选 | 同 v9 §7.4 |
| reportOptions | objectType=REPORT 必填 | 其他类型应为空；layout 仅 TABLE |
| referenceSql | 可选 | **v9 降为可选**：语义定义是稳定层，SQL 是实现层，不进真源（digest §16 第 7 条） |
| version / validFrom | 可选 | 运行期预留 |

M7 不是 BI 指标模型（无事实表/维度/Cube/ETL）；多个一对多来源同时聚合必须 preAggregation，禁止 `SUM(DISTINCT amount)`。

## 10. MU UI 模型（UI，v9 重定义版）

顶层：`application{}` + `screens[]`（v9 §8.2）。

**Application**：`name/menus[]`；Menu：`menuId/name/children[]（二级菜单强制至少一个）/screenRef(只有二级菜单挂屏幕，与屏幕一对一)`。

**Screen**：`screenId(SCR-)/name/screenType(SINGLE_FORM/LIST_MAINTENANCE/MASTER_DETAIL_FORM/QUERY_LIST)/layout(ASCII)/elements[]/actions[]`。

**Element**：`id/type(10 类：TEXTBOX/TEXTAREA/COMBO/DATEPICKER/POPUP_SELECT/NUMBER/CHECKBOX/BUTTON/GRID/LABEL)/label/io/required/dataBinding(M1 属性路径)/dataSource(M7 对象)/refRules[]`。控件映射强制：Date→DATEPICKER、Enum/DictionaryRef→COMBO、AggregateRootRef→POPUP_SELECT、长文本→TEXTAREA、Boolean→CHECKBOX（v9 §8.3）。

**ActionPoint**：`actionId/name/behaviorRef(对应 M2 行为)/actionType(BUTTON/SUBMIT/DRAFT/APPROVE/REJECT/RETURN)/permissionRef[](M5)`。审批双按钮规则：带审批流的屏幕必须同时含 DRAFT 与 SUBMIT 两个独立功能点（v9 §8.5）。

## 11. GLS 术语模型（GLOSSARY，本仓自定义扩展，票 10）

OMF v6/v9 均无术语模型（digest §0/§16）。术语 = 业务概念的定义/别名/解释，与 M1 的 DICT（值域字典，承载枚举值域）不是一回事——本仓自定义扩展，走"元模型错→框架版本演进"路由进 schema（CHANGELOG.md + 机读表 version 1→1.1.0，本节即迁移票正文）。

顶层：`terms[]`。

| 字段 | 必填 | 说明 |
|---|---|---|
| id | ✓ | `GLS-{域}-{Seq}` |
| term | ✓ | 术语词面（业务真源原文，不改动） |
| aliases | 可选 | 同指异名（全称/标准名/别称），可空列表 |
| termType | 可选 | 术语分类，沿业务真源原文（如 禁用词/别名/一词两译/黑话/缩写/术语/治理热词），不做枚举收敛——真源说什么是什么 |
| definition | ✓ | 定义/解释；口径争议、禁用替代等注记逐字保真 |
| relatedObjectRefs | 可选 | 关联 M1 聚合根 ID 列表。**只挂真实存在的对象，可空留空不硬挂**；依赖边 GLS→M1 单向登记（model-deps.json edges），指向悬空 = L2 红（GLS-AC3） |
| status | 可选 | 状态/有效期（沿业务真源原文，如 `禁用（替代：×）`/`有效`/`有效（待联席裁决）`） |
| owner | 可选 | 术语 Owner（业务部门） |
| source | ✓ | 注源（如 `R5·设定书 §6`）——术语必须可溯源，无源不落仓 |
| notes | 可选 | 补充注记（承载落点/未建原因等，人读追溯用，机器不检） |

- camp=business-core、consumers=[runtime, build]：自动进 semantic-service 检索面（划界只看 camp）与生成器在场校验，无需改任何消费方。
- **profile 组合：入 v9-full 与 headless，不入 v9-core**（v9-core = M1/M2/M3/M5 四模型最小核保持原样，术语属增强件；"未启用"因此可测——GLS-AC2 负变体）。
- 旧域无 glossary-model.yaml 不红：缺在场不校验是既定行为（AC6 同款语义），旧域零改动兼容。
- GLS→GLS（术语见术语）**不设专用依赖边**：当前业务面无此需求（最小够用）。若模型里出现指 GLS- 的 `xxxRef(s)` 形态字段，会落"未登记 edges 字段按 dependsOn 兜底"的判定路径（兜底集含自身，不白名单红；悬空检查仍然生效）——真要规模化再用时再显式登记边。
- **禁用词拦截面（票 16，L4 `banned-term`）**：`status` 值包含「禁用」子串的术语条目（如 `禁用（替代：产量完成率）`）为机读禁用真源——其 `term` 与 `aliases` 成员构成域内禁用词表；全域元素 **name/alias** 键的字符串值子串命中即红（闸在 schema_check，真源唯一=GLS；运行时拒答是消费侧行为）。**description/notes 不扫**——文档提及合法（RULE-BOHAI-009 描述注记「禁用旧称老完成率」即活体证明），这是拦截面与文档自由的分界线。GLS 条目以 `term` 键承载词面、不在 name/alias 匹配面，禁用词表不自匹配。负变体/正例：出厂集 `ban-ac1/ac2/ac4`（BAN-AC1–4）。

## 12. 换义锁定字段（lockedFields，AC7 的机读真源）

OMF 的 M6/M7 在 v4 换义造成过沟通成本（digest §14/§16 第 10 条）。本仓把"退役字段名"登记在 model-registry.json 各模型 `lockedFields`，schema_check 在 L4 强制：**模型文件内出现锁定字段名 = 兼容性违规**（新义必须新增字段名）。现行锁定表：

| 模型 | 锁定字段 | 旧义（禁止复用的理由） |
|---|---|---|
| M2 | `producedEvents` | v6 事件异步引用（ME 载体）；v9 由 syncTriggers 承载 |
| M3 | `subscribedEvents` / `triggeredBehaviors` | v6 事件驱动规则专属；v9 移除 EVENT_DRIVEN |
| M5 | `externalContract` | v6 外部实体契约；v9 移除 EXTERNAL |
| M6 | `eventRef` | v6 EVENT_WAIT/事件触发残留；v9 流程为同步编排 |
| MU | `callChain` | v6 屏幕调用链；v9 以 actions 操作功能点替代 |

## 13. 模型注册表与依赖白名单（机读）

- `model-registry.json`：每模型 `camp`（business-core/integration/build-contract；一期 integration 空，MI 未引入）、`consumers`（runtime/build）、`profiles`（可用组合：v9-full/v9-core/headless）、`dependsOn`（类型层依赖白名单摘要）、`requiredElementFields`（票 13：逐元素结构性必填字段机读表，前缀→字段键列表；闸 L1 required-field）。消费方：profile 裁剪、必填闸、检索面划界（semantic-service 只索引 business-core）、生成器在场校验四件事共用（PRD F1）。
- `model-deps.json`：`idPrefixes`（ID 前缀→模型）+ `refKeys`（ref 字段名全集）+ `edges`（from 模型 × ref 字段 → 允许目标模型集）。AC4/AC5 的判定真源；与 registry 的 dependsOn 做一致性核对，冲突 = L1 违规。
- 依赖白名单要点：M2 不得依赖 M7（AC5 例证，见 §2）；M1 零依赖；M6 依赖 M1/M2/M3/M5；MU 依赖 M1/M2/M3/M5/M7；GLS 只依赖 M1（relatedObjectRefs 单向边，票 10）。

## 14. 一致性对清单（L2 consistency-*，票 11）

OMF 规范声明的"双向一致"对（源：digest §12.2；勘误 2026-09-19：票 11 曾误引 §16.4，权威出处 digest §12.2，见 docs/reviews/2026-09-19-phase2-batch1-tickets10-12.md）是现成的 lint 清单；本仓按"每对一条 L2 违规码"落进 `tools/schema_check.py`（行前缀 `consistency-`，报文含对名/涉事 ID/依据字段/期望值，--json 每对一行可机读；确定性、零 LLM）。涉事 ID 的**存在性**由悬空引用检查（`dangling-ref`）承载——ref 扫描面 = refKeys ∪ `*Ref/*Refs` 后缀 ∪ edges 三源并集（真源 model-deps.json）；本组只补**语义闭合向**，不重复扫存在性（红因不混：指向不存在的 ID 报 dangling-ref，存在但语义断裂才报 consistency-*）。

| # | 一致性对 | 违规码 | 状态 |
|---|---|---|---|
| P1 | M7 `behaviorRef` → M2 查询行为：**M7 侧单射 + 指向合法**——behaviorRef 必指向存在且 `behaviorType=QUERY` 的行为（`consistency-redirection`）；同一 M2 查询行为不得被第二个 M7 绑定（`consistency-not-one-to-one`，依赖边单向 M7→M2，反向经 ref 反查，见 §2。注：不查"QUERY 行为必被 M7 绑定"——反向在 OMF 语境未必成立，避免逼出假报表） | `consistency-redirection` / `consistency-not-one-to-one` | **已实现**（票 11） |
| P2 | M2 `requiredPermissions` 每项指向存在的 `PERM-*`，且该权限 `targetRef` 回指此行为（双向闭合。锚定 M2.requiredPermissions 面：M5 侧单面登记权限以承载岗位职责、而行为侧 requiredPermissions 留空，不判红——权限面是角色的职责登记，见 §7） | `consistency-permission` | **已实现**（票 11） |
| P3 | M6 活动 `roleRef` ∈ 流程 `roleRefs`（活动级角色是流程角色集子集；USER_TASK/APPROVAL_TASK 承载 roleRef，见 §8） | `consistency-flow-role` | **已实现**（票 11） |
| P4 | M3 `triggeredBehaviors` ↔ 下游行为 | — | **回加条件制**：`triggeredBehaviors` 为 v6 事件驱动专属，v9 移除 EVENT_DRIVEN，已列 §12 换义锁定字段——仅当事件驱动回加、字段解锁时随新字段名实现本对 |
| P5 | M2 `producedEvents` ↔ ME `producerBehaviorRef` | — | **ME 回加时启用**（一期无 ME 事件模型，§0；`producedEvents` 已锁定，见 §12） |
| P6 | M3 `subscribedEvents` ↔ ME `subscribers` | — | **ME 回加时启用**（同上；`subscribedEvents` 已锁定，见 §12） |

正例承载：`ontology/bohai` 全域（P1 四个查询出口一对一、P2 行为侧权限全回指、P3 三流程活动角色全闭合）与出厂集 `valid-domain`；负变体：出厂集 `cons-ac1/2/3` 三个最小域（断言标签 CONS-AC1–3，真源 = tickets/11-一致性对核验.md AC 表）。新增一致对 = 本章加行 + schema_check 加同款判定 + 出厂集配负变体，三件同步。

**对账注记（2026-09-19，票 14）**：PRD F2 所称「8 组一致对」经 digest 全文核查仅得 **6 对**（§12.2，即上表 P1–P6 的规范出处；§16 第 2 条亦回指 §12.1/§12.2），第 7/8 组出处未找到。全仓按 **6 对**执行；Owner 若找到第 7/8 组出处，走演进票回加（加行进本表 + 检查器同款判定 + 出厂集负变体）。互指注记见 docs/prd.md F2 行。

## 15. 语义 CI 分级全景与 L3 确定性闸（票 41，2026-09-20）

PRD F2 五级闸全景：**L1 schema 合法 → L2 引用与一致性对（§14）→ L3 指标/SQL/安全 → L4 权限/兼容（§12/§13）→ L5 行为回归（Golden 集，LLM 评分）**。本仓现行确定性执行面覆盖 L1/L2/L4 + 必填 + 一致性对 + 禁用词；票 41 把 L3 的**确定性可判子集**落进 schema_check（报告计数行与 --json 增 L3，违规码 `l3-*` 前缀，断言 L3-AC1a–d，真源=tickets/41 可机判子集清单 L0 裁决）：

| # | 检查 | 判定 | 违规码 |
|---|---|---|---|
| L3-1 | M3 规则 sourceField 字段存在性 | 双段（对象.属性）形态才判（非双段=无承载字段注记，不判）：对象段按匹配序 id→alias→name→**别名驼峰词唯一包含**（`L3_OBJECT_MATCH_ORDER` 可配置；末层兼容本表 §6 sourceField 示例「dailyProduction」式自造短名——与聚合 alias 非直配，bohai 存量即此形态），字段段在该聚合 attributes[].name 中；sourceField 值容忍中文注记后缀（「oilOutput（区块月合计）」截断于首个括号） | `l3-source-field` |
| L3-2 | M7 口径表达式引用可解析 | resultColumns[].sourceExpression 内「别名.字段」token（正则提取，运算符/字面量/函数名跳过）：别名须在该报表 sourceObjects[].alias 声明集，字段须在别名所指聚合（objectRef）的 attributes 中；objectRef 悬空归 dangling-ref（红因不混） | `l3-expression-ref` |
| L3-3 | M7 referenceSql 只读性 | 可选字段（§9 v9 降为可选）在场才扫：DML/DDL 黑名单词 INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/CREATE/GRANT，大小写不敏感 + `\b` 词边界（updated_at 式列名不误伤；纯词扫描不解析 SQL 注释——注释含独立黑名单词照红，确定性取舍） | `l3-sql-readonly` |
| L3-4 | M3 规则形态完备性 | 落地形态二选一（§6）：ruleType=EXPRESSION → expression 在场且非空；其余型（值集实读=VALIDATION/CALCULATION/DERIVATION/TRANSFORMATION/RISK，无 EXPRESSION/NARRATIVE ruleType）→ expression/narrative 至少一者在场且非空；ruleType 本身缺失归 L1 required-field，不叠红因 | `l3-rule-form` |
| L3-5 | 口径登记确定性机检（联合变更批二 2026-09-29，schema.md §6 指标口径字段组 1.3.0） | 只扫 M3 规则文件、字段全可选缺省不触发：mark 值域 ★/☆（其他值＝杜撰展示标记）；defaultCaliber 在场须命中本条 calibers 名单（默认口径悬空指针即红）；ambiguous=true 须 calibers ≥2 支（一词两译多支并列语义）；slot_name 落仓禁令（snake/camel 双形态——票 93 slots 剥法由服务端单点执行，仓内存储即第二份真源）。依据：主仓 fork 终审发现「闸全绿而登记失真」3 处笔误，内容面收进机检 | `l3-caliber-mark` · `l3-caliber-default` · `l3-caliber-ambiguous` · `l3-slot-name-banned` |

**明示不收**（防子集蔓延，防踩坑 L0 裁决）：SQL 语义正确性（需执行环境）、指标公式数学正确性（Owner 裁决域）、安全敏感度分级（需口径）、任何需 LLM 判断的项——归 L5 评分框架设计案（第三期 B 线批次三方案 1），L3 本表加行即可继续收确定性子集。存量首跑裁决：bohai 两处红（RULE-BOHAI-003 sourceField 虚挂 dailyProduction.batchRowCount/batchNullRowCount）=真缺陷已修域（数据集级派生量无行级承载，沿无承载字段注记惯例改写，裁决记录 lessons/41）。
