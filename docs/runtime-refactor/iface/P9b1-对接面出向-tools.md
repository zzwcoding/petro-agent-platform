# P9b1·对接面调研（出向·runtime → tools）

- 范围：runtime 调外部（出向）中 **runtime → appv2.tools 包**的全部接触点——ToolRegistry 调出口契约、六工具输入/输出形、包公开符号名单（runtime 允许 import 的名单）、runtime 侧现有消费面（调用单点/结果投影/上下文构造/注入缝）。
- 不含：工具内部实现细节（仅函数签名与返回结构；引擎内部逻辑归 recon/ 分片）、appv2.knowledge/query/retrieval 引擎内部、api 层的非工具装配（归 P9a2）。
- 行号约定：全文路径相对仓根 `/Users/divh/Downloads/petro-agent-platform`；行号锚定本文写作时工作区状态（非提交号锚定）。
- 编号命名：规则＝`T-P9b1-NN`（01 起递增，稳定不复用）；疑点＝`D-P9b1-NN`（只列不判）。
- 合同真源指针：`specs/tools.md`、`specs/modules.md`（tools 卡）——本文未实读正文，仅作对照指针。

## 范围与文件清单

实读（13 个）：

| # | 文件 | 读法 |
|---|---|---|
| 1 | appv2/tools/__init__.py | 全文（196 行，公开面/导出清单） |
| 2 | appv2/tools/registry.py | 全文（173 行，ToolRegistry.call 契约） |
| 3 | appv2/tools/schema.py | 全文（233 行，四 schema＋伴生件＋闭世界常量） |
| 4 | appv2/tools/handlers.py | 全文（891 行，只看签名/args_schema/返回结构，不深读实现） |
| 5 | appv2/tools/ledger.py | 全文（182 行，dump 投影与渲染件） |
| 6 | appv2/tools/argscheck.py | 全文（94 行，校验器与 ArgsError） |
| 7 | appv2/tools/precondition.py | 片段（30-320、595-663：公开符号定义/签名） |
| 8 | appv2/tools/anchors.py | 片段（35-140：三公开函数） |
| 9 | appv2/tools/table_scan.py | 片段（45-110：类与两函数） |
| 10 | appv2/tools/fake.py | 片段（1-80：四假件签名） |
| 11 | appv2/runtime/graph.py | 片段（135-172、245-265、343-390、1134-1200、1237-1273、2142-2151、3297 周边：消费面） |
| 12 | appv2/runtime/executor.py | 片段（40-60、138-170、340-362、570-580：注入面） |
| 13 | appv2/api/app.py | 片段（100-142：生产装配面） |

清单（2 个，非实读源）：`specs/tools.md`、`specs/modules.md`（tools 卡）——合同真源，仅引用。

---

## 一、工具注册表契约（规则条目）

### 1.1 注册表本体

- **T-P9b1-01 装配与构造单点**：`ToolRegistry(*, knowledge: KnowledgeStore, query: QueryFace, retrieval: RetrievalFace, faq: FaqLookupFace | None = None)`——构造期内部调 `build_tools` 把全部工具注册进册，外部不逐个 register（`appv2/tools/registry.py:115-127`）。生产装配在 `appv2/api/app.py:116-121`；runtime 经 `LoopDeps.registry` 接收成品（`appv2/runtime/graph.py:358,370`；`appv2/runtime/executor.py:143,160`）。
- **T-P9b1-02 register 纪律**：`register(tool: Tool)`——`descriptor.readonly is not True`→抛 `ValueError`（INV-2 只收只读工具）；重名→抛 `ValueError`（`registry.py:129-138`）。注册期错误即刻上抛，不走 ToolResult 通道。
- **T-P9b1-03 descriptors() 发现面**：`descriptors() -> list[ToolDescriptor]`，注册序返回，只透四字段（`registry.py:140-142`）。**runtime 现无调用点**（全仓仅测试调用；见 D-P9b1-11）。
- **T-P9b1-04 call 三段流程**：`async call(name: str, args: Mapping[str, Any], ctx: ToolContext) -> ToolResult`（`registry.py:144-172`）——①寻工具（未知名即返回）→②argscheck schema 校验→③执行 handler。registry 公开面仅 `register/descriptors/call` 三方法，零数据写出口。
- **T-P9b1-05 未知工具形**：返回 `ToolResult.failed(bad_args, "未知工具：{name}（可用：{known}）", hint="按 descriptors() 列表选择工具名")`（`registry.py:149-155`）。
- **T-P9b1-06 schema 校验**：args 先经 `validate_args(args_schema, args)`（argscheck 子集：type/properties/required/additionalProperties/items/enum/minLength/minimum；boolean 不冒充 integer；只判形不改值，返回 dict 副本）；不合→`ArgsError`→`failed(bad_args, …)`，**引擎零调用**（`registry.py:156-163`；`argscheck.py:23-45`）。六工具 args_schema 全部 `additionalProperties=false`。
- **T-P9b1-07 执行期异常封套**：handler 抛 `ArgsError`→`failed(bad_args, str(exc), hint="按拒因修参后重试")`（`registry.py:166-169`）；其余 `Exception`→`classify_exception` 三分类封套（`registry.py:170-172`）。
- **T-P9b1-08 classify_exception 映射（单点）**：`classify_exception(exc) -> (category, message, hint)`（`registry.py:50-109`）。判序与映射：

| 判序 | 判据（字段级） | category | hint 要点 |
|---|---|---|---|
| 1 | `isinstance(exc, TimeoutError)`（3.12 含 asyncio 超时） | `retryable` | 同参重调一次 |
| 2 | `isinstance(exc, PermissionError)` | `refused` | 不重试 |
| 3 | `isinstance(exc, UpstreamUnavailable)` | `retryable` | 同参重调一次 |
| 4 | `UpstreamRejected` 且 `reason` 前缀 `"上游拒绝 429:"` | `retryable` | 429 限流（`_HINT_429`） |
| 5 | 其余 `UpstreamRejected` | `bad_args` | 修参后重试 |
| 6 | duck 型 `exc.status_code == 429` | `retryable` | 429 限流 |
| 7 | duck 型 `400 <= status_code < 500` | `bad_args` | 修参后重试 |
| 8 | `isinstance(exc, ValueError)` | `bad_args` | 修 plan/参数 |
| 9 | 兜底 | `retryable` | 同参重调一次 |

- **T-P9b1-09 超时责任归属（runtime 侧）**：registry.call **无** timeout 参数；超时闸在 runtime 单点 `_invoke_tool`——`asyncio.wait_for(registry.call(...), timeout=state.budget["tool_timeout_seconds"]（缺省 30.0）)`，超时→本地构造 `failed(retryable, "工具 {name} 超 {t}s 未返回（单工具超时闸）")`（`appv2/runtime/graph.py:2142-2151`、`1150-1161`）。工具层不实现超时。
- **T-P9b1-10 ToolContext 字段（逐调用上下文）**：`ToolContext`＝四字段（`schema.py:69-94`）：`actor: str = ""`（身份只从 ctx 进、进 data_query→plan.actor）、`budget: int = 4`（检索送窗预算 M；`__post_init__` 校验非 bool 整数且 ≥1）、`metric_candidates: tuple[str, ...] | None = None`（FX-13 候选集，None＝不启用）、`approved_tables: tuple[str, ...] = ()`（外表放行态）。runtime 单点构造 `_ctx_of`：actor=state.actor、budget=resolve_send_budget(问题组子问题数)、metric_candidates=tuple(state.metric_candidates) or None、approved_tables=tuple(state.approved_ids)（`graph.py:1135-1148`）。
- **T-P9b1-11 ToolResult 结构与不变式**：`ToolResult{status, observations: tuple[Observation, ...], ask: AskFrame|None, error: ToolError|None}`；构造即定型不变式（`schema.py:186-196`）：ok 无 ask/error；failed 必携 error；ask 必携 ask。构造器：`ToolResult.ok(observations=())`、`.failed(category, message, *, hint=None, observations=())`、`.ask_frame(frame, *, observations=())`（`schema.py:198-220`）。
- **T-P9b1-12 status 闭世界**：`STATUS_OK="ok"`、`STATUS_FAILED="failed"`、`STATUS_ASK="ask"`；`STATUS_ALL` frozenset 三值（`schema.py:38-41`）。
- **T-P9b1-13 category 闭世界**：`CATEGORY_RETRYABLE="retryable"`（超时/上游抖动）、`CATEGORY_BAD_ARGS="bad_args"`（计划/参数错）、`CATEGORY_REFUSED="refused"`（闸拒）；`CATEGORY_ALL` frozenset（`schema.py:45-50`）。runtime 措辞映射：bad_args→「校验拒」、retryable→「暂不可用」、refused→「闸拒」（`graph.py:1237-1273` `_tool_note`）。
- **T-P9b1-14 AskFrame 与 ask kind 闭世界**：`AskFrame{kind, prompt, options: tuple[str, ...] = (), detail: Mapping[str, Any] | None = None}`；`kind ∈ {ASK_CLARIFY="clarify", ASK_EXTERNAL_TABLE_APPROVAL="external_table_approval"}`（`ASK_KINDS` 闭世界，构造即校验）（`schema.py:54-56, 137-154`）。
- **T-P9b1-15 Observation 字段与 locator 分型**：`Observation{content, source, source_id, version: str|None, freshness, scope, locator: Mapping[str, str], well: str|None = None}`（`schema.py:157-174`）。locator 恒机读，`kind` 键分型值（handlers 装配面）：台账卡 `kind=evidence.kind`（metric/term/object/relation/family）＋element_id/source/binding_state；`agg_row`（table/well_id[/prod_date]）；`lineage`；`notice`（notice_type 子型：no_hit/schema_not_allowed/freshness_block/unbound_degrade/rebind/window_note）；`schema`（area=whitelist）；检索支 `fragment|graph`；`window_miss`；`faq_aux`（`handlers.py:514-529, 644-692, 699-719, 338-391, 844-890, 798-810`）。
- **T-P9b1-16 ToolDescriptor/Tool 与 handler 型**：`ToolDescriptor{name, description, args_schema: Mapping, readonly: bool = True}`（`schema.py:59-66`）；`Tool{descriptor, handler}`；`ToolHandler = Callable[[dict[str, Any], ToolContext], Awaitable[ToolResult]]`（`schema.py:223-232`）。

### 1.2 工具名与注册序

- **T-P9b1-17 工具名常量闭世界**（`handlers.py:77-82`）：`SEMANTIC_QUERY="semantic_query"`、`DATA_QUERY="data_query"`、`DOC_RETRIEVE="doc_retrieve"`、`GRAPH_QUERY="graph_query"`、`SCHEMA_PROBE="table_schema"`、`FAQ_LOOKUP="faq_lookup"`。runtime 另有调用面闭世界 `DISCOVER_TOOLS = {SEMANTIC_QUERY, SCHEMA_PROBE, FAQ_LOOKUP}`（discover 节点专用，`graph.py:254-258`）。
- **T-P9b1-18 注册序（确定性）**：semantic_query→data_query→doc_retrieve→graph_query→table_schema→（faq 提供时殿后）faq_lookup（`handlers.py:424-480`）。
- **T-P9b1-19 faq 可选注册**：`build_tools(..., faq=None)` 时 faq_lookup **不在册**（注册表只有 5 个工具；`handlers.py:397-408, 466-480`）；此时调 faq_lookup 落 T-P9b1-05 未知工具路径。

### 1.3 runtime 侧消费面（重写必须保形的接触点）

- **T-P9b1-20 唯一调用单点**：一切工具调用经 `_invoke_tool`（`graph.py:2142-2151`）→`deps.registry.call`；调用点 3 处：discover 节点（`graph.py:2167`）、execute 节点（`graph.py:2250`）、batch 节点（`graph.py:3297`）。
- **T-P9b1-21 结果投影（字段级）**：ToolResult 对象经 `_result_dict`（`graph.py:1164-1200`）投影为 dict 后全 run 使用——`status`；`observations[]`＝{content, source, source_id, version, freshness, scope, locator, well}；`ask`＝{kind, prompt, options(list), detail(dict|None)}|None；`error`＝{category, message, hint}|None。**runtime 不 import ToolResult/Observation/AskFrame/ToolError 类本身**（只经属性访问鸭子型消费）。
- **T-P9b1-22 data_query 六联合态→ToolResult 映射（`handlers.py:578-641`）**：

| outcome.kind（query 域） | ToolResult 形 |
|---|---|
| `rows` | ok：agg_row 观察（scope=agg）＋血缘卡＋rebind notice |
| `freshness_block` | ok：notice（notice_type=freshness_block，extra=watermark_date/window_label/is_default） |
| `unbound_degrade` | ok：evidence 卡＋依据 notice（unbound_degrade） |
| `need_clarify` | ask(clarify)：prompt=clarify_question，options=choices |
| `external_table_approval` | ask(external_table_approval)：prompt=ask_card.reason，options=("批准","驳回")，detail=ask_card |
| `refuse` | failed(refused, reason) |

  data_query 另在 handler 内先 `query.validate(plan, candidates=ctx.metric_candidates)`，不过→failed(bad_args, check.reason)（`handlers.py:543-550`）；plan 由 plan_draft 装配、actor 只从 ctx 进（`handlers.py:554-575`）；`ctx.approved_tables` 随行传 `query.run`（`handlers.py:551`）。
- **T-P9b1-23 审批帧 detail 形状**：detail=引擎 ask 卡原样（合同形状 approval_id/scene/title/reason/impact/audit_hint，`schema.py:141-143`）＋ additive 键 `tables=[外表名]`（越集续跑机读面，`handlers.py:621-634`）；runtime resume 侧按 `kind == ASK_EXTERNAL_TABLE_APPROVAL` 收口（`executor.py:577`）；批准落 state.approved_ids→下一轮 ToolContext.approved_tables（T-P9b1-10）。
- **T-P9b1-24 ledger dump schema（runtime↔tools 另一条数据通路）**：`dump_from_store(knowledge) -> dict`（`ledger.py:79-144`），键级：`metrics[{slot,name,binding_state,calibers[{key,name,default}],default_caliber,value,source_id,version}]`、`terms[{term,banned,freshness,value,source_id}]`、`objects[{obj,value,source_id}]`、`relations[{rel,value,source_id}]`、`families[{name,value,source_id}]`、`aliases{dict}`、`families_map{dict}`、`cards[list]`（列表真源＝`ALL_SCHEMA_CARDS`）。接线：api `compose_production_ledger_dump` 返回 lambda（每次澄清取现行态，`api/app.py:122-142`）→`LoopDeps.ledger_dump`（`graph.py:364`；`executor.py:153,167,356`）→首轮调用即取一次存 `state.ledger_dump`（`graph.py:1432-1433`）。blackbox 快照排除 `ledger_dump` 键（`blackbox.py:8-9`）。
- **T-P9b1-25 上下文渲染件（runtime 直接调用）**：`render_ledger_rows(dump)`／`render_aliases(dump)`／`render_cards(dump)` 纯函数返回 str；常驻注入块包裹标记 `RESIDENT_BLOCK_BEGIN/END` 由 runtime 拼接（`ledger.py:151-181`；`graph.py:1345-1346`）。
- **T-P9b1-26 送窗预算单点**：`resolve_send_budget(subtask_count) = min(24, 6×max(1, count))`（常量 `SEND_BUDGET_PER_SUBTASK=6`／`SEND_BUDGET_CAP=24`，`schema.py:102-118`）；runtime 在 `_ctx_of` 按问题组子问题数赋值；消费方＝doc_retrieve/graph_query（→`RetrievalNeed.budget`），data_query 不消费。
- **T-P9b1-27 前置条件机面（runtime 消费的纯函数族）**：`judge(SubtaskInput, LedgerFacts, *, approved_tables=(), watermark=None, window_resolved=False, data_wells=None) -> Verdict`（`precondition.py:264-272`）；四态 `STATE_PASS/BLOCKED_ASK/BLOCKED_REFUSE/NOTE`；`Verdict` 字段 subtask_id/state/reason/notes/normalized_slot/chain_switch_trigger/chain_switch_kind/fuzzy_window_rewrite＋`as_payload()`（`precondition.py:97-139`）；事实源 `ledger_facts(dump)`（消费 T-P9b1-24 同一 dump，`precondition.py:181`）。
- **T-P9b1-28 边界与零 LLM**：tools 包依赖只许 appv2.knowledge/query/retrieval 公开接口＋appv2.infra（importlinter V2 契约）；不 import app.**／runtime；本包零 LLM 调用（`__init__.py:12-14`）；全部工具 readonly=True 且零写副作用（INV-2）。

---

## 二、工具清单（表格）

| 工具名常量 | 值 | 输入形（args 字段级） | 输出形（observations/ask/error） | 实现文件 |
|---|---|---|---|---|
| `SEMANTIC_QUERY` | `semantic_query` | `question?: str(minLength1)` 与 `element_name?: str(minLength1)` 二选一（同给同缺＝handler 抛 ArgsError→bad_args，schema 层仅描述）；additionalProperties=false（`handlers.py:117-133`） | 无 ask。ok：每条 evidence 卡→观察（content=value、source_id=element_id、locator={kind=evidence.kind, element_id, source, binding_state}）＋`metric_by_name` 补取并列（去重）；零命中＝notice(no_hit)。error：bad_args（二选一违反） | handlers.py:487-511（注册 425-432） |
| `DATA_QUERY` | `data_query` | `plan_draft`（必，object，additionalProperties=false）：`metric_slot: str(必)`、`ranking: bool(必)`、`window_start?: str(ISO)\|null`、`window_end?: str(ISO)\|null`、`limit?: int≥1\|null`、`aggregate?: bool`、`direction?: "asc"\|"desc"`、`window_label?: str`、`is_default?: bool`、`external_tables?: [str(minLength1)]`（`handlers.py:135-168`） | 六态全量（T-P9b1-22 表）：ok＝行观察＋血缘卡＋notice 族；ask＝clarify｜external_table_approval；error＝bad_args（validate 拒/装配拒）｜refused（引擎闸拒） | handlers.py:535-551＋578-641（注册 433-440） |
| `DOC_RETRIEVE` | `doc_retrieve` | `question: str(必)`、`anchors?: [str(minLength1)]`、`family_hints?: [str ∈ FAMILY_ALL＝completion/monthly/dynamic/blank]`；additionalProperties=false（`handlers.py:170-186`） | 无 ask。ok：每条检索观察→出处链（content=obs.text、source=report、source_id=fragment_id、scope=family、locator＋kind=fragment|graph、well 透传）＋window_note notice（截断显式）＋（window_note 载缺位段时）`window_miss` 补充观察。error：仅异常封套 | handlers.py:725-735（注册 441-448） |
| `GRAPH_QUERY` | `graph_query` | `question: str(必)`、`anchors?: [str(minLength1)]`；additionalProperties=false；anchors 拼入问针（`f"{question} {' '.join(anchors)}"`）（`handlers.py:188-200, 738-746`） | 同 doc_retrieve（共用 `_bundle_to_result`）；edge 出处 fail-closed 锚校验在引擎 | handlers.py:738-746（注册 449-456） |
| `SCHEMA_PROBE` | `table_schema` | `area?: enum["agg","sem","kb"]` 与 `table?: str(minLength1)` 二选一（同给＝handler 抛 ArgsError→bad_args）；additionalProperties=false（`handlers.py:202-218`） | 无 ask、零 IO。ok：白名单结构卡观察（locator={kind:schema, area:whitelist}）或 schema_not_allowed notice（白名单外表如实告知）。error：bad_args（二选一违反） | handlers.py:752-761（注册 457-464；**同步函数**） |
| `FAQ_LOOKUP` | `faq_lookup` | `question: str(必)`；additionalProperties=false（`handlers.py:220-231`）；**仅 faq 读缝注入时在册**（T-P9b1-19） | 无 ask。ok：命中＝faq_aux 观察（content=`Q：{标准问} / A：{答案}`、source=`faq_entry`、source_id=`faq_entry:{entry_id}`、scope=`faq`、locator={kind:faq_aux, entry_id}；阈值 score≥`FAQ_AUX_THRESHOLD=1.0`、剔 disabled、top=`FAQ_TOP_N=3`）；未命中＝notice(no_hit) 空集不阻断。error：bad_args（缺 question） | handlers.py:767-810（注册 466-480） |

---

## 三、公共符号（runtime 允许 import 的名单）

名单真源＝`appv2/tools/__init__.py` 的 `__all__`（75 个符号，`__init__.py:119-195`）。**runtime 现状实引 37 个**（graph.py:135-172 引 35 个包面符号＋ledger 子模块 2 个；executor.py:49 引 2 个，均 ⊂ 上述 35）。

### 3.1 schema.py（19 个，`appv2/tools/schema.py`）

| 符号 | 用途 | 来源文件 |
|---|---|---|
| `STATUS_OK` | ToolResult.status 值 `"ok"` | schema.py:38 |
| `STATUS_FAILED` | ToolResult.status 值 `"failed"` | schema.py:39 |
| `STATUS_ASK` | ToolResult.status 值 `"ask"` | schema.py:40 |
| `STATUS_ALL` | status 三值闭世界 frozenset | schema.py:41 |
| `CATEGORY_RETRYABLE` | ToolError.category 值 `"retryable"` | schema.py:45 |
| `CATEGORY_BAD_ARGS` | ToolError.category 值 `"bad_args"` | schema.py:46 |
| `CATEGORY_REFUSED` | ToolError.category 值 `"refused"` | schema.py:47 |
| `CATEGORY_ALL` | category 三值闭世界 frozenset | schema.py:48 |
| `ASK_CLARIFY` | AskFrame.kind 值 `"clarify"` | schema.py:54 |
| `ASK_EXTERNAL_TABLE_APPROVAL` | AskFrame.kind 值 `"external_table_approval"` | schema.py:55 |
| `ASK_KINDS` | ask kind 两值闭世界 frozenset | schema.py:56 |
| `ToolDescriptor` | 工具描述卡 {name, description, args_schema, readonly} | schema.py:59 |
| `ToolContext` | 逐调用上下文 {actor, budget, metric_candidates, approved_tables} | schema.py:69 |
| `ToolError` | 工具错误 {category, message, hint}（构造即校验 category 闭世界） | schema.py:121 |
| `AskFrame` | ASK 帧 {kind, prompt, options, detail}（构造即校验 kind 闭世界） | schema.py:137 |
| `Observation` | 统一观察 {content, source, source_id, version, freshness, scope, locator, well} | schema.py:157 |
| `ToolResult` | 工具统一出口 {status, observations, ask, error}＋ok/failed/ask_frame 构造器 | schema.py:177 |
| `resolve_send_budget` | 送窗预算 M 计算（6×n，上限 24） | schema.py:106 |
| `Tool` | 注册项 {descriptor, handler} | schema.py:227 |

### 3.2 registry.py / argscheck.py（3 个）

| 符号 | 用途 | 来源文件 |
|---|---|---|
| `ToolRegistry` | 只读工具注册表与统一调出口（register/descriptors/call） | registry.py:112 |
| `classify_exception` | 引擎异常→(category, message, hint) 三分类单点 | registry.py:50 |
| `ArgsError` | 参数校验/装配失败（ValueError 子类；registry 捕获转 bad_args） | argscheck.py:19 |

### 3.3 handlers.py（13 个，`appv2/tools/handlers.py`）

| 符号 | 用途 | 来源文件 |
|---|---|---|
| `SEMANTIC_QUERY` | 工具名常量 `"semantic_query"` | handlers.py:77 |
| `DATA_QUERY` | 工具名常量 `"data_query"` | handlers.py:78 |
| `DOC_RETRIEVE` | 工具名常量 `"doc_retrieve"` | handlers.py:79 |
| `GRAPH_QUERY` | 工具名常量 `"graph_query"` | handlers.py:80 |
| `SCHEMA_PROBE` | 工具名常量 `"table_schema"` | handlers.py:81 |
| `FAQ_LOOKUP` | 工具名常量 `"faq_lookup"` | handlers.py:82 |
| `QueryFace` | 问数引擎缝 Protocol（validate/run） | handlers.py:95 |
| `RetrievalFace` | 检索引擎缝 Protocol（retrieve/graph） | handlers.py:107 |
| `FaqLookupFace` | FAQ 读缝 Protocol（similar） | handlers.py:87 |
| `build_tools` | 五工具装配单点（faq 提供时六工具）→list[Tool] | handlers.py:397 |
| `faq_lookup` | 工具六实现函数（六工具中唯一包面导出的实现函数） | handlers.py:767 |
| `recall_relevant` | 缺位回捞相关面判定（问句资产 token 命中缺位注记） | handlers.py:829 |
| `FAQ_AUX_THRESHOLD` | FAQ 消费阈值 `1.0` | handlers.py:274 |

### 3.4 ledger.py（7 个，`appv2/tools/ledger.py`）

| 符号 | 用途 | 来源文件 |
|---|---|---|
| `ALL_SCHEMA_CARDS` | 发现面白名单结构卡全量（agg 三表＋sem 五账＋kb 清单） | ledger.py:44 |
| `RESIDENT_BLOCK_BEGIN` | 常驻注入块起始标记 | ledger.py:151 |
| `RESIDENT_BLOCK_END` | 常驻注入块结束标记 | ledger.py:152 |
| `dump_from_store` | KnowledgeStore 读面→词典层全量 dump dict（T-P9b1-24 键级契约） | ledger.py:79 |
| `render_ledger_rows` | dump→台账行渲染 str | ledger.py:155 |
| `render_aliases` | dump→别名表渲染 str | ledger.py:173 |
| `render_cards` | dump→结构卡渲染 str | ledger.py:179 |

### 3.5 precondition.py（23 个，`appv2/tools/precondition.py`）

| 符号 | 用途 | 来源文件 |
|---|---|---|
| `STATE_PASS` | 判定四态值 `"pass"` | precondition.py:41 |
| `STATE_BLOCKED_ASK` | 判定四态值 `"blocked_ask"` | precondition.py:42 |
| `STATE_BLOCKED_REFUSE` | 判定四态值 `"blocked_refuse"` | precondition.py:43 |
| `STATE_NOTE` | 判定四态值 `"note"` | precondition.py:44 |
| `SUBTASK_STATES` | 四态闭世界 frozenset | precondition.py:45 |
| `CHAIN_SWITCH_HINT` | 换链建议文案（data 链拦停拒因尾部逐字追加） | precondition.py:73 |
| `CHAIN_SWITCH_KIND_UNBOUND` | 换链分型值 `""`（绑定闸） | precondition.py:79 |
| `CHAIN_SWITCH_KIND_DOMAIN` | 换链分型值 `"domain"`（域闸） | precondition.py:80 |
| `FUZZY_TIME_MARKERS` | 模糊时间词表（最近/近期/前段时间） | precondition.py:66 |
| `META_QUESTION_MARKERS` | 元问句词面（旧称/以前叫/现在叫/还叫/原名） | precondition.py:602 |
| `BAN_EXEMPT_QUOTE_PAIRS` | 引用形豁免引号对四形 | precondition.py:597 |
| `BAN_EXEMPT_SENTENCE_BREAKS` | 元问同句分句符闭世界 | precondition.py:604 |
| `SubtaskInput` | 判定输入 {subtask_id, question, chain, plan?, retrieval_need?} | precondition.py:86 |
| `Verdict` | 判定输出（含 normalized_slot/chain_switch_trigger/chain_switch_kind/fuzzy_window_rewrite＋as_payload） | precondition.py:97 |
| `MetricFact` | 指标事实 {slot, name, binding_state, calibers, default_caliber} | precondition.py:145 |
| `BannedFact` | 禁用词事实 {term, status, replacement} | precondition.py:156 |
| `LedgerFacts` | 判定事实集 {metrics, banned, keys} | precondition.py:165 |
| `ledger_facts` | dump→LedgerFacts 投影（零 I/O） | precondition.py:181 |
| `normalize_metric_name` | 指标名归一键（剥装饰符/收空白/小写） | precondition.py:226 |
| `resolve_metric_slot` | 发射槽位→台账 slot 解析（keys 精确＋名归一扫描） | precondition.py:238 |
| `judge` | 逐子问题过闸判四态（纯函数，T-P9b1-27 签名） | precondition.py:264 |
| `is_ban_exempt` | 禁用词豁免判定（引用形/元问形） | precondition.py:628 |
| `ban_exempt_notice_text` | 豁免机读 notice 文案 | precondition.py:655 |

### 3.6 anchors.py / table_scan.py / fake.py（10 个）

| 符号 | 用途 | 来源文件 |
|---|---|---|
| `normalize_anchor_text` | 锚文本规范形（剥非字母数字汉字＋casefold） | anchors.py:41 |
| `entity_anchor_tokens` | 问句实体锚集提取（井号/油田名/报告号，闭世界匹配） | anchors.py:68 |
| `inject_retrieval_anchors` | retrieval_need 锚确定性注入（注入项不可被模型清空，返回副本） | anchors.py:107 |
| `TableScanFindings` | 实扫结论 {declared_tables, detected_tables, unapproved, miss_declared} | table_scan.py:52 |
| `extract_external_table_refs` | 问句外表引用提取（别名面＋schema.table 词面） | table_scan.py:72 |
| `scan_unapproved_tables` | 执行前白名单比对（申报∪实扫对开放集） | table_scan.py:94 |
| `FakeKnowledgeStore` | 假台账读面（应答罐头＋调用计数） | fake.py:36 |
| `FakeQueryEngine` | 假问数引擎（validate 合同拒因模拟＋run 罐头/异常注入） | fake.py:73 |
| `FakeRetrievalEngine` | 假检索引擎（RetrievalNeed 全量捕获） | fake.py:138 |
| `FakeUpstreamRejection` | 上游拒绝桩（status_code 属性，classify_exception 同判对象） | fake.py:28 |

### 3.7 runtime 现状实引名单（37 个，重写基线）

`graph.py:135-171` 引：ASK_CLARIFY、ASK_EXTERNAL_TABLE_APPROVAL、CATEGORY_BAD_ARGS、CATEGORY_REFUSED、CATEGORY_RETRYABLE、CHAIN_SWITCH_HINT、CHAIN_SWITCH_KIND_DOMAIN、CHAIN_SWITCH_KIND_UNBOUND、DATA_QUERY、DOC_RETRIEVE、FAQ_LOOKUP、SCHEMA_PROBE、SEMANTIC_QUERY、STATE_BLOCKED_ASK、STATE_BLOCKED_REFUSE、STATE_NOTE、STATE_PASS、STATUS_ASK、STATUS_FAILED、STATUS_OK、SubtaskInput、ToolContext、ToolRegistry、ban_exempt_notice_text、entity_anchor_tokens、inject_retrieval_anchors、is_ban_exempt、judge、ledger_facts、normalize_anchor_text、recall_relevant、render_aliases、render_cards、render_ledger_rows、resolve_send_budget；`graph.py:172` 直引子模块两符：RESIDENT_BLOCK_BEGIN、RESIDENT_BLOCK_END；`executor.py:49` 引：ASK_EXTERNAL_TABLE_APPROVAL、ToolRegistry。

---

## 四、关键保证

- **唯一出口**：agent 与世界的唯一接触面＝ToolRegistry（`__init__.py:3`）；runtime 一切工具调用只经 `registry.call`（禁用直调 handler——唯一消费形为 ToolHandler 签名）。
- **只读不变式（INV-2）**：register 拒绝 readonly!=True；六工具全 readonly=True、零写副作用；registry 零数据写出口；渲染件与投影件返回副本容器。
- **零 LLM**：tools 包内零 LLM 调用（精排/嵌入在引擎缝内，B6 出口已收口）；runtime 不持引擎引用（引擎面由 build_tools 闭包捕获）。
- **错误三分类单点**：一切引擎异常经 classify_exception 映射（T-P9b1-08 表）；429 双面判定（duck status_code∨reason 前缀）单源。
- **结果通道唯一**：ToolResult 三态定型不变式在构造期成立；runtime 侧只做字段级 dict 投影（T-P9b1-21）。
- **超时在 runtime**：工具层无超时语义；单工具超时闸（wait_for＋工具级 budget 键）是 runtime 责任（T-P9b1-09）。
- **两条数据通路**：①调用通路 registry.call↔ToolResult；②词典层通路 ledger_dump dict（tools.ledger 投影、precondition/runtime 消费，T-P9b1-24）——两者形状独立，重写须同时保形。
- **确定性顺序**：注册序固定（T-P9b1-18）；dump 装配序固定（metrics 装配序＝resolve_metric_slot 首命中判据）。
- **边界**：tools 依赖只 knowledge/query/retrieval 公开接口＋infra，不 import app.**/runtime（importlinter V2 契约在案）。

### 疑点（只列不判）

- D-P9b1-01：runtime 直引子模块 `appv2.tools.ledger`（graph.py:172，绕包公开面；两符号包面已再导出）——重写锁「只经 appv2.tools 公开面」时需决定子模块直引是否保留。
- D-P9b1-02：五工具实现函数（semantic_query/data_query/doc_retrieve/graph_query/table_schema）**不在**包 `__all__`（六工具中仅 faq_lookup 在册）——「工具入口函数」公开度无明文。
- D-P9b1-03：registry.call 无 timeout 参数；超时真源在 runtime 的 `state.budget["tool_timeout_seconds"]`（缺省 30.0 硬编码于 graph.py:2146）——契约文本对超时零表达。
- D-P9b1-04：classify_exception 的 429 类型面依赖字符串前缀 `"上游拒绝 429:"` 与 duck 属性 status_code——与 llm_client 措辞耦合（码内声明单源）；上游错误措辞变更需同步。
- D-P9b1-05：faq 未接线时在册 5 工具，而 runtime `DISCOVER_TOOLS` 常量恒含 FAQ_LOOKUP（graph.py:256-258）——该装配下调 faq_lookup 落 T-P9b1-05 未知工具路径。
- D-P9b1-06：ToolContext.budget 缺省 4（schema.py:86）与生产赋值 resolve_send_budget（≥6，graph.py:1139）两个真源并存；data_query 不消费该值。
- D-P9b1-07：table_schema 为同步 def（handlers.py:752），经 build_tools 内 async 闭包（handlers.py:421-422）包装后满足 ToolHandler 异步形——直接函数调用面与注册面异步性不一致。
- D-P9b1-08：ledger dump 是包与 precondition/runtime 之间的隐式机读契约（module docstring 声明界面，无类型载体）——键名/形状变更无编译期保护。
- D-P9b1-09：ToolResult.failed/ask_frame 构造器允许携 observations（schema.py:202-220），不变式只校验 ask/error 互斥，不校验 failed 场景 observations 语义；runtime 投影全字段。
- D-P9b1-10：审批帧 detail 的 additive 键 `tables`（handlers.py:621-634，V2-52）与合同 A1 帧 15 形状（approval_id/scene/title/reason/impact/audit_hint，schema.py:141-143）分属两层——重写须并保两形状。
- D-P9b1-11：descriptors() 无 runtime 消费点（仅测试调用与未知工具 hint 文案提及）；工具目录进模型 prompt 的通路是 runtime 文案字面量（如 graph.py:250、2372），非发现面——重写前定义面真源需另定。
- D-P9b1-12：runtime 对结果的消费是「先投影成 dict、再全 run 使用」（graph.py:1164-1200）；ToolResult 不变式只在到达 runtime 前成立——重写若改流式/增量结果需重建不变式位置。

## 覆盖自检

- 来源文件：13 个实读（6 全文＋7 片段/检索读）／2 个清单（specs/tools.md、specs/modules.md，未实读仅指针）；规则区间 T-P9b1-01..28；疑点区间 D-P9b1-01..12；工具数 6；公共符号 75（runtime 现状实引 37）。
