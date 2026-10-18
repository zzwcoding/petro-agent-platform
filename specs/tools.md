# V2 工具层（ToolRegistry 与在册工具）

状态: 已定稿
来源: specs/modules.md `tools` 卡、docs/prd.md §③、ADR-0001
变更: 2026-10-15 行为 6 由「一句话用途」扩为**三件套**（Owner 裁定「要」；真源 `walk/11` §七 Q-A；配套 `specs/tool_matching.md` 的工具描述三件套条）；2026-10-17 接口定义节补 **`table_schema` 井号名录卡注记**（dim_well 卡携【井号名录】·discover 现读·非常驻；`well` 查值走 `RULE-PETRO-005` 归一比对）；2026-10-18 接口定义节补 **`graph_query` 摘除注记**（V2-97／D7——注册面摘除、代码保留、恢复条件在案）；2026-10-18 接口定义节补 **两新工具注记**（V2-96／D5——`fetch_section`／`fetch_report` 只读、按已见来源取节/取篇、截断＋披露）

## 目标

把 knowledge/query/retrieval 三个引擎包装成 agent 可发现的**只读工具**：
统一 Observation 结构、错误三分类、ASK 帧形态——agent 与世界的唯一接触面。

## 不做什么

不实现任何引擎逻辑（只转发到引擎公开接口）；不做工具并行调度（本期串行）；
不做工具级权限差异（全部只读，权限差异在数据层）。

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| tools | 新增 | ToolRegistry＋在册工具（含 V2-96 D5 两新工具）＋Observation/ToolResult schema |

## 接口定义

```python
class ToolRegistry:
    def descriptors(self) -> list[ToolDescriptor]: ...
    async def call(self, name: str, args: dict, ctx: ToolContext) -> ToolResult: ...

# ToolDescriptor = {name, description, args_schema(jsonschema), readonly: True}
# ToolResult = {status: ok|failed|ask, observations: list[Observation],
#               ask: AskFrame|None, error: ToolError|None}
# ToolError = {category: retryable|bad_args|refused, message, hint}
# AskFrame  = {kind: clarify|external_table_approval, prompt, options}
# Observation = {content, source, source_id, version, freshness, scope, locator}
```

在册工具（注册面）：`semantic_query`（args: question 或 element_name）；
`data_query`（args: plan_draft）——内部先调 query.validate，不过则返 failed(bad_args, 校验理由)；
`doc_retrieve`（args: question, anchors?, family_hints?）；
`table_schema`（args: area 或 table 或 well——V2-31 发现工具）。

- **两新工具注记（V2-96 D5——作答侧有界再探；真源 `docs/runtime-refactor/接手-召回全链路最终决议与运行流程-20261018.md` §五·5.4）**：在册名单新增两件**只读**工具——`fetch_section`（args: `report_id`〔必填〕, `section?`〔空＝该报告代表节，表格承载优先〕）与 `fetch_report`（args: `report_id`〔必填〕, `max_chars?`〔缺省＝`appv2/tools/schema.py` 的 `FETCH_CAP_CHARS` 单点〕）。两工具经 `RetrievalFace` 的 additive 两面（`fetch_section`／`fetch_report`）取料：`doc_retrieve` 走 L0→L1 新召回，两件走 **KB 只读**（按 `report_id`＝**已见来源标识（报告名）**取节／取篇；无该报告／无该节＝空集＋如实 window_note，不代取他节）。**截断＋披露**：超 `cap_chars` 必截断（正文尾可见截断标记 `FETCH_TRUNCATION_MARK`）并在 window_note 逐字披露（`NOTE_FETCH_TRUNCATED`＝「母报告全文 {total} 字，本次交付前 {kept} 字（截断显式）」；`fetch_report` 是**最后手段**）。工具返回结构复用既有 Observation 形（locator 带 `report`／`section`／`fragment_id`；直读取料腿标记 `leg="kb"`，非召回腿）。**权限谓词沿用 INV-3**：`report_id` 须落在当前 actor 可见库内（越权＝拒，不静默）；**「只许已见来源」的判据在编排侧**（工具面只做「该来源不存在／无该节」的如实空集）。注册面名单随之＝`semantic_query`／`data_query`／`doc_retrieve`／`fetch_section`／`fetch_report`／`table_schema`（＋faq 读缝提供时的 `faq_lookup`）。判据：`tests/domains/test_v2_v296_explore.py::test_fetch_report_truncates_and_discloses`。

- **`graph_query` 摘除注记**（V2-97／D7；真源 `docs/runtime-refactor/接手-召回全链路最终决议与运行流程-20261018.md` §二 D7）：`graph_query`（args: question, anchors?）**已从工具注册面摘除**——生产装配 `RetrievalEngine` 构造无 `graph=`（`appv2/api/app.py`），该工具恒返「图谱缝空集回退」，在册只令模型白耗一次匹配/执行。**摘除范围＝注册面**：`appv2/tools/handlers.py` 的 `build_tools` 在册名单＝`semantic_query`／`data_query`／`doc_retrieve`／`table_schema`（＋faq 读缝提供时的 `faq_lookup`）；`GRAPH_QUERY` 常量、`graph_query` handler、`_GRAPH_DESCRIPTION`／`_GRAPH_SCHEMA`、`GraphSource` 协议与 compound 精排件（`appv2/retrieval/engine.py`）**全部保留**，模块注携 `DEBT(V2-97)`（去向＝接线决策票）。**恢复条件**（两条同时满足才可重新在册）：①接线决策票落定并实施——生产装配给出 `GraphSource` 实现（Neo4j 邻域适配器或等价只读读面）且 `RetrievalEngine` 构造注入 `graph=`；②该装配面有端到端判据（图谱面非空集可达，如现有 `tests/domains/test_v2_tools.py::anchors_contract` 的真引擎锚名可达支在生产同形装配下可复现）。**恢复动作**＝`build_tools` 重挂 `graph_query` 注册项＋本注记撤除＋注册面名单测试同步；**2026-10-18 补（V2-97）**——additive 摘除面零改代码（判据：`tests/domains/test_v2_tools.py::graph_query_not_registered`／`::graph_leg_code_kept`）。

- **前置条件机闸件公开面注记**（`appv2/tools/precondition.py`）：`Verdict.hit_rule: str`——**命中的判定位标识**，闭世界八位——`ban`／`fuzzy_window`／`ask`／`unregistered_metric`／`normalized_slot`／`chain_switch`／`freshness_window`／`single_well`（命名以 `specs/preconditions.md` 判定序明文表位次为准逐字）；**非 `allow` 支必携一位**（可解释性——`preconditions` 单点取结构化判定位，不复制语义、不文案反推），`allow` 支（pass／note）＝空串（fail-closed：拒支漏填即成空串，双向对账可检）。**2026-10-16 补（流水 56）**；additive——既有判定行为零回归。
- **askback 候选窗常量公开面注记**（`appv2/tools/__init__.py` 经包根转出，真源 `appv2/query/domain.py` 第 78–84 行）：`ASKBACK_TIME_QUESTION`（缺参反问问句逐字）／`ASKBACK_TIME_CHOICES`（三候选「近 3 天／近 30 天／本月至今」，无默认项）——`runtimev2` 各块经 `appv2.tools` 包根消费，不直引引擎（守边界规则 R6：agent 与世界的唯一接触面＝工具注册表）。**2026-10-16 补（流水 58）**；additive——既有行为零回归。
- **`table_schema` 井号名录卡注记**（`appv2/tools/handlers.py`＋`appv2/tools/well_ids.py`＋`appv2/query/pg_wells.py`）：**dim_well 卡携【井号名录】**——discover 响应里现读 `agg.dim_well`（按区块分组、全角分隔、注明「共 N 口·dim_well」；超限截断＋计数照报）；名录**只在 discover 响应**注入（**非常驻**——台账常驻块/结构卡集合真源 `tools.ALL_SCHEMA_CARDS` 逐字不动，常驻块零增重）。`table_schema` 参数面三形互斥：`area`／`table`（卡面）／`well`（井号查值）；`well` 查值走本体 `RULE-PETRO-005` 井号归一（真源 `ontology/petro/m3-rule-model.yaml`）后比对名录——变体形（去连字符／乱连字符／空白污染／大小写混写，如 `w-11`／`W011`）判同一口井；命中＝观察（`locator.kind=well_lookup`）、**不在册＝notice `no_hit`**（不猜最近井、不做近似匹配）；名录不可得（读缝未接线／现读失败）＝notice `well_roster_unavailable`（如实告知，不静默冒充空名录）；名录每次调用现读恰一次（卡面名录段与判据同源同一行集，零缓存）。**2026-10-17 补（流水 70·审计）**；additive——既有行为零回归（判据：`tests/domains/test_v2_well_roster_card.py`）。
- **`doc_retrieve` 缺位名单停发注记**（`appv2/tools/handlers.py`——`_missing_sources_segment`／`_strip_missing_sources`／`_bundle_to_result`）：未纳入来源段（window_note 载 `NOTE_MISSING_SOURCES`）**不再**作为独立观察（原 V2-46 的 `locator.kind=window_miss`「检索窗注记（缺位名单）」）追加进 `state.observations`——**停发理由**：该名单按**单轮检索**算，与实际「多子问题并集＋材料选择」后的送窗不一致（模型会照它说「某来源未纳入」而该来源实已在窗）。保留面：①window_note 主段（recalled/sent 计数＋差额＋同窗声明＋扩席实录）逐字照旧走 notice 通道；②材料渲染披露行（`context/materials.py`，按实投窗算）零改；③审计机读面——名单原文只落 `tools.handlers` 模块日志（**不进模型材料、不进引擎注记**）。**「按实投窗重算的缺位名单」登记为后续能力**（不在本票恢复；V2-46 缺位回捞白场随名单停发而无在场信号）。**2026-10-18 补（流水 V2-91）**；判据：`tests/domains/test_v2_v291_missing_sources_stop.py`。

- **`doc_retrieve` 留痕身份与扩席归因注记**（V2-89b；真源 `appv2/tools/schema.py` `ToolContext`＋`appv2/tools/retrieval_calllog.py`）：`ToolContext` 补 `run_id`／`sub_question_id` 两字段（**只从状态取**——`runtimev2.bookkeeping.projection.tool_context` 注入，签名仍只有 `state`；`run_id`＝`state.run_id`，`sub_question_id`＝恰一支问题组时其子问题 id，多支/无组**如实空串**，不发明归属；缺省空串＝旧构造零漂移）。`retrieval_calls` 行键闭世界补七键：`snippet`（首支入窗候选正文前 **40** 字，`SNIPPET_CHARS`——其余候选仍只留字符数、全文/密钥不落）／`anchor_seated`／`rowset_added`／`summary_expanded`（三通道实际入窗席数，值源＝`RetrievalBundle` 同名 additive 计数）／`budget`（送窗预算 M）／`sent`（实走支数）／`over_budget`（追加席候选因预算被丢——D3 真封顶机读位；语义真源 `specs/retrieval.md` 行为 2 补记）。**2026-10-18 补（V2-89b）**；additive——既有键零改（判据：`tests/domains/test_v2_retrieval_calllog.py`）。

## 行为约定

1. 全部工具 readonly=True 且不得产生任何写副作用（INV-2）；registry 拒绝注册 readonly!=True 的工具。
2. 参数先经 args_schema 校验：不合→failed(bad_args) 不触引擎。
3. 引擎异常统一分类：超时/上游抖动→retryable；计划或参数错（4xx 族除 429 外）→bad_args；**429 限流单列 retryable**（临时性，与 gateway 层重试分层不冲突）；闸拒（无据/越权口径）→refused。
4. query 引擎返回的联合态映射：rows+lineage→observations(权威表,scope=agg)；freshness_block/unbound_degrade
   →observations(闸依据 Evidence/水位)+notice 素材；need_clarify/external_table_approval→status=ask＋AskFrame。
5. 每个 Observation 必须带来源链（台账行/fragment→report→library/表名），locator 可机读（INV-1 的输入）。
6. **工具描述写全并给模型看**：`descriptors()` 的 `description` 须含**何时用／不能做什么／参数示例**三项（真源 `walk/11-匹配-工具阀.md` §七 Q-A——选得准的**第一因**，靠写清描述而非加规则）；仍保持渐进披露（不展开引擎内部细节）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 在册工具 descriptors 齐、全 readonly（INV-2） | `tests/domains/test_v2_tools.py::descriptors_readonly` |
| schema 校验失败→failed(bad_args) 引擎零调用 | `tests/domains/test_v2_tools.py::bad_args_notouch_engine` |
| 引擎超时→retryable；4xx 除 429 外→bad_args；429→retryable；闸拒→refused | `tests/domains/test_v2_tools.py::error_taxonomy` |
| query 联合态四类映射正确（含 AskFrame 形态） | `tests/domains/test_v2_tools.py::query_outcome_mapping` |
| Observation 来源链完整（fragment 到 library） | `tests/domains/test_v2_tools.py::observation_provenance` |
| 每个工具 `description` 含「何时用／不能做什么／参数示例」三项 | `tests/domains/test_v2_tools.py::descriptor_covers_three_parts` |
| dim_well 卡携井号名录（按区块分组＋共 N 口·dim_well；常驻面零增重） | `tests/domains/test_v2_well_roster_card.py::test_dim_well_card_carries_roster_grouped_by_block` |
| 井号查值走 RULE-PETRO-005 归一（变体形命中；不在册如实 no_hit 不猜最近井） | `tests/domains/test_v2_well_roster_card.py::test_well_lookup_variant_forms_hit_canonical` |
| 留痕行携身份两键（run_id/sub_question_id）与扩席计数/预算面 | `tests/domains/test_v2_retrieval_calllog.py::test_retrieval_calllog_carries_run_id_and_counts` |
| 留痕 `snippet`＝首支前 40 字（≤40 且不落全文） | `tests/domains/test_v2_retrieval_calllog.py::test_snippet_40_chars_no_full_text` |
| `graph_query` 不在工具注册面（descriptors 零该名；调用判未知工具 bad_args、图谱引擎零调用） | `tests/domains/test_v2_tools.py::graph_query_not_registered` |
| 图谱腿/compound 精排代码保留（GraphSource＋精排件 AST 存在性）＋模块注携 `DEBT(V2-97)` | `tests/domains/test_v2_tools.py::graph_leg_code_kept` |
| 两新工具在册（`fetch_section`／`fetch_report` 只读、args schema 齐、描述含三件套） | `tests/domains/test_v2_tools.py::descriptors_readonly` |
| `fetch_report` 截断＋披露逐字（受 `fetch_cap`；Observation 形带 report/section/fragment_id；空节如实空集） | `tests/domains/test_v2_v296_explore.py::test_fetch_report_truncates_and_discloses` |

## 依赖与风险

- 依赖：`knowledge`/`query`/`retrieval` 接口定稿（各自 spec）；假引擎 adapter。
- 风险：args_schema 与 plan_draft 校验两处规则漂移——plan_draft 的 schema 真源在 query 卡，工具层只引用。
