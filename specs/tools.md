# V2 工具层（ToolRegistry 与四工具）

状态: 已定稿
来源: specs/modules.md `tools` 卡、docs/prd.md §③、ADR-0001

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

## 行为约定

1. 全部工具 readonly=True 且不得产生任何写副作用（INV-2）；registry 拒绝注册 readonly!=True 的工具。
2. 参数先经 args_schema 校验：不合→failed(bad_args) 不触引擎。
3. 引擎异常统一分类：超时/上游抖动→retryable；计划或参数错→bad_args；闸拒（无据/越权口径）→refused。
4. query 引擎返回的联合态映射：rows+lineage→observations(权威表,scope=agg)；freshness_block/unbound_degrade
   →observations(闸依据 Evidence/水位)+notice 素材；need_clarify/external_table_approval→status=ask＋AskFrame。
5. 每个 Observation 必须带来源链（台账行/fragment→report→library/表名），locator 可机读（INV-1 的输入）。
6. descriptors 渐进披露：只暴露名称/一句话用途/参数 schema/只读声明（书 5.5 三层披露之发现层）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 四工具 descriptors 齐、全 readonly（INV-2） | `tests/domains/test_v2_tools.py::descriptors_readonly` |
| schema 校验失败→failed(bad_args) 引擎零调用 | `tests/domains/test_v2_tools.py::bad_args_notouch_engine` |
| 引擎超时→retryable；上游 4xx 类→bad_args；闸拒→refused | `tests/domains/test_v2_tools.py::error_taxonomy` |
| query 联合态四类映射正确（含 AskFrame 形态） | `tests/domains/test_v2_tools.py::query_outcome_mapping` |
| Observation 来源链完整（fragment 到 library） | `tests/domains/test_v2_tools.py::observation_provenance` |

## 依赖与风险

- 依赖：`knowledge`/`query`/`retrieval` 接口定稿（各自 spec）；假引擎 adapter。
- 风险：args_schema 与 plan_draft 校验两处规则漂移——plan_draft 的 schema 真源在 query 卡，工具层只引用。
