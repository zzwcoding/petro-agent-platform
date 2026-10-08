# V2 语义资产读面（knowledge）

状态: 已定稿
来源: specs/modules.md `knowledge` 卡、docs/prd.md §③（"LLM 消费本体"核心问题）

## 目标

sem_* 台账（指标/术语/对象/关系/族标注/别名）以 **Knowledge Evidence** 形态供 agent 现场消费：
agent 查得到、看得懂口径、知道能不能出数——本体利用率从两张词表到全要素。

## 不做什么

不写语义管理面（增删改审沿用 V1 端点与治理线）；不做语义推理/规则引擎（ontology ci 语义闸仍在构建期）；
不做缓存层（本期直读 PG，量级允许）。

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| knowledge | 新增 | KnowledgeStore＋Evidence schema |

## 接口定义

```python
class KnowledgeStore:
    def evidence(self, q: SemanticQuery) -> list[Evidence]: ...
    def metric_by_name(self, name: str) -> Evidence | None: ...   # 经别名八键归一后精确命中
    def aliases(self) -> dict[str, str]: ...
    def families(self) -> dict[str, list[str]]: ...               # ASSOC/报告族标注

# SemanticQuery = {text, kinds?: set[metric|term|object|relation|family]}
# Evidence = {element_id, kind, value, source, version, freshness, scope, binding_state}
# binding_state ∈ bound | unbound | expired   —— V1 语义原样承载：
#   bound=绑定 agg 计量列可出数；unbound=在册未绑定（走降级）；expired=届满漂移
```

## 行为约定

1. 只读 sem_* 现行行（草案态整体呈现沿用 V1 语义）；零写副作用（INV-2）。
2. `metric_by_name` 命中顺序：精确名→别名八键归一→None；别名命中时 Evidence.source 如实注"经别名归一"。
3. binding_state 由台账绑定关系推导（V1 MEASURE_COLUMNS 冻结三绑定的判定逻辑原样移植），不得臆造。
4. expired（届满）必须带届满日期与现口径指引（V1 漂移标注语义）。
5. families 返回 ontology 导出物的族标注（completion/monthly/dynamic＋relation group），供 doc_retrieve 供给策略与 plan 语境使用。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 指标精确命中→Evidence 带口径/binding_state=bound | `tests/domains/test_v2_knowledge.py::metric_exact_hit` |
| 别名（如 CEP-D 修饰形）归一命中且 source 注明 | `tests/domains/test_v2_knowledge.py::alias_canonicalize` |
| 在册未绑定指标（含水率/配产量）→binding_state=unbound | `tests/domains/test_v2_knowledge.py::unbound_flagged` |
| 届满术语→expired＋日期＋指引 | `tests/domains/test_v2_knowledge.py::expired_flagged` |
| families 覆盖三族标注＋relation group 透传 | `tests/domains/test_v2_knowledge.py::families_complete` |
| 全程只读（INV-2 断言） | `tests/domains/test_v2_knowledge.py::readonly_inv2` |

## 依赖与风险

- 依赖：infra 复制票（db 只读会话）；sem_* fixture（问数组台账态：20 指标/11 术语/10 对象/5 关系）。
- 风险：V1 绑定判定逻辑散在 domain.py——移植时以问数组题册数值行为为准（复测 A/H 族），不靠逐行搬运。
