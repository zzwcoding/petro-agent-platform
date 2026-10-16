# V2 工具层（ToolRegistry 与四工具）

状态: 已定稿
来源: specs/modules.md `tools` 卡、docs/prd.md §③、ADR-0001
变更: 2026-10-15 行为 6 由「一句话用途」扩为**三件套**（Owner 裁定「要」；真源 `walk/11` §七 Q-A；配套 `specs/tool_matching.md` 的工具描述三件套条）；2026-10-17 接口定义节补 **`table_schema` 井号名录卡注记**（dim_well 卡携【井号名录】·discover 现读·非常驻；`well` 查值走 `RULE-PETRO-005` 归一比对）

## 目标

把 knowledge/query/retrieval 三个引擎包装成 agent 可发现的**只读工具**：
统一 Observation 结构、错误三分类、ASK 帧形态——agent 与世界的唯一接触面。

## 不做什么

不实现任何引擎逻辑（只转发到引擎公开接口）；不做工具并行调度（本期串行）；
不做工具级权限差异（全部只读，权限差异在数据层）。

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| tools | 新增 | ToolRegistry＋四工具＋Observation/ToolResult schema |

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

四工具：`semantic_query`（args: question 或 element_name）；
`data_query`（args: plan_draft）——内部先调 query.validate，不过则返 failed(bad_args, 校验理由)；
`doc_retrieve`（args: question, anchors?, family_hints?）；
`graph_query`（args: question, anchors?）。

- **前置条件机闸件公开面注记**（`appv2/tools/precondition.py`）：`Verdict.hit_rule: str`——**命中的判定位标识**，闭世界八位——`ban`／`fuzzy_window`／`ask`／`unregistered_metric`／`normalized_slot`／`chain_switch`／`freshness_window`／`single_well`（命名以 `specs/preconditions.md` 判定序明文表位次为准逐字）；**非 `allow` 支必携一位**（可解释性——`preconditions` 单点取结构化判定位，不复制语义、不文案反推），`allow` 支（pass／note）＝空串（fail-closed：拒支漏填即成空串，双向对账可检）。**2026-10-16 补（流水 56）**；additive——既有判定行为零回归。
- **askback 候选窗常量公开面注记**（`appv2/tools/__init__.py` 经包根转出，真源 `appv2/query/domain.py` 第 78–84 行）：`ASKBACK_TIME_QUESTION`（缺参反问问句逐字）／`ASKBACK_TIME_CHOICES`（三候选「近 3 天／近 30 天／本月至今」，无默认项）——`runtimev2` 各块经 `appv2.tools` 包根消费，不直引引擎（守边界规则 R6：agent 与世界的唯一接触面＝工具注册表）。**2026-10-16 补（流水 58）**；additive——既有行为零回归。
- **`table_schema` 井号名录卡注记**（`appv2/tools/handlers.py`＋`appv2/tools/well_ids.py`＋`appv2/query/pg_wells.py`）：**dim_well 卡携【井号名录】**——discover 响应里现读 `agg.dim_well`（按区块分组、全角分隔、注明「共 N 口·dim_well」；超限截断＋计数照报）；名录**只在 discover 响应**注入（**非常驻**——台账常驻块/结构卡集合真源 `tools.ALL_SCHEMA_CARDS` 逐字不动，常驻块零增重）。`table_schema` 参数面三形互斥：`area`／`table`（卡面）／`well`（井号查值）；`well` 查值走本体 `RULE-PETRO-005` 井号归一（真源 `ontology/petro/m3-rule-model.yaml`）后比对名录——变体形（去连字符／乱连字符／空白污染／大小写混写，如 `w-11`／`W011`）判同一口井；命中＝观察（`locator.kind=well_lookup`）、**不在册＝notice `no_hit`**（不猜最近井、不做近似匹配）；名录不可得（读缝未接线／现读失败）＝notice `well_roster_unavailable`（如实告知，不静默冒充空名录）；名录每次调用现读恰一次（卡面名录段与判据同源同一行集，零缓存）。**2026-10-17 补（流水 70·审计）**；additive——既有行为零回归（判据：`tests/domains/test_v2_well_roster_card.py`）。

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
| 四工具 descriptors 齐、全 readonly（INV-2） | `tests/domains/test_v2_tools.py::descriptors_readonly` |
| schema 校验失败→failed(bad_args) 引擎零调用 | `tests/domains/test_v2_tools.py::bad_args_notouch_engine` |
| 引擎超时→retryable；4xx 除 429 外→bad_args；429→retryable；闸拒→refused | `tests/domains/test_v2_tools.py::error_taxonomy` |
| query 联合态四类映射正确（含 AskFrame 形态） | `tests/domains/test_v2_tools.py::query_outcome_mapping` |
| Observation 来源链完整（fragment 到 library） | `tests/domains/test_v2_tools.py::observation_provenance` |
| 每个工具 `description` 含「何时用／不能做什么／参数示例」三项 | `tests/domains/test_v2_tools.py::descriptor_covers_three_parts` |
| dim_well 卡携井号名录（按区块分组＋共 N 口·dim_well；常驻面零增重） | `tests/domains/test_v2_well_roster_card.py::test_dim_well_card_carries_roster_grouped_by_block` |
| 井号查值走 RULE-PETRO-005 归一（变体形命中；不在册如实 no_hit 不猜最近井） | `tests/domains/test_v2_well_roster_card.py::test_well_lookup_variant_forms_hit_canonical` |

## 依赖与风险

- 依赖：`knowledge`/`query`/`retrieval` 接口定稿（各自 spec）；假引擎 adapter。
- 风险：args_schema 与 plan_draft 校验两处规则漂移——plan_draft 的 schema 真源在 query 卡，工具层只引用。
