# V2 检索引擎（retrieval）

状态: 已定稿
来源: specs/modules.md `retrieval` 卡、docs/prd.md §③、Q11 病灶（生成窗截断/同型张冠李戴）

## 目标

V1 S4 双路召回＋精排＋图谱链移植为确定性引擎；供给策略本体化——
**矛盾来源同窗并立、截断显式**（window_note 如实声明"召回 N/送窗 M"），治"材料未披露"虚答与同型抢锚。

## 不做什么

不做生成（GEN 是 runtime 阐述步的事）；不做 LLM 逐条打分 O(N)（V1 compound 档旧形态不带入，
精排最多两次 LLM 调用：批量排序＋来源置信度）；不改 V1 切片/索引产物。

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| retrieval | 新增 | RetrievalEngine（retrieve＋图谱面） |

## 接口定义

```python
class RetrievalEngine:
    def retrieve(self, need: RetrievalNeed) -> RetrievalBundle: ...
    def graph(self, need: RetrievalNeed) -> RetrievalBundle: ...   # 图谱面

# RetrievalNeed = {question, anchors?, family_hints?, budget}
# RetrievalBundle = {observations: list[Observation], window_note: str}
# Observation 带出处链 fragment→report→library＋family 标注；
# window_note = "召回 N 支/送窗 M 支"＋矛盾来源同窗声明或缺位枚举
```

## 行为约定

1. 双路召回（向量＋关键词）→融合→精排（LLM 批量序＋来源置信度，失败回退 V1 确定性配额，不炸链）。
2. 供给分池按 family_hints/来源指纹：同主题矛盾来源（同型报告/跨油田同指标）必须同窗并立；
   送窗预算内每来源至少留代表支，缺位在 window_note 枚举。
3. 截断显式：召回>送窗时 window_note 写"召回 N/送窗 M"——agent 据此如实区分"没有"与"没送"。
4. 同型文档来源标注：每支 Observation 的 locator 带 library/报告名，锚错（A-W11 vs Y-21）可被核验步发现。
5. 失败回退语义同 V1（回退不炸链）；embedding 失败向量腿按空腿、关键词腿兜底。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 双路召回→融合序；LLM 精排挂→确定性配额兜底结果仍可用 | `tests/domains/test_v2_retrieval.py::rerank_fallback` |
| 同型两报告同主题→矛盾来源同窗（两报告各≥1 支） | `tests/domains/test_v2_retrieval.py::contradiction_same_window` |
| 召回 21 送窗 4→window_note 如实含 N/M 数字 | `tests/domains/test_v2_retrieval.py::window_note_explicit` |
| Observation 出处链完整（fragment→report→library）＋family 标注 | `tests/domains/test_v2_retrieval.py::provenance_chain` |
| family_hints 驱动供给（完井族题不挤占月报族配额） | `tests/domains/test_v2_retrieval.py::family_supply` |
| 图谱面：邻域边证据带出处，失败回退空集不炸 | `tests/domains/test_v2_retrieval.py::graph_surface` |

## 依赖与风险

- 依赖：infra 复制票（embedder/gateway completer）；kb fixture（V1 片段库快照）。
- 风险：精排 prompt 与"矛盾同窗"策略的交互——同窗是供给层硬规则，不依赖 LLM 自觉（防 Q11 式失守）。
