# V2 检索引擎（retrieval）

状态: 已定稿
来源: specs/modules.md `retrieval` 卡、docs/prd.md §③、Q11 病灶（生成窗截断/同型张冠李戴）

## 目标

V1 S4 双路召回＋精排＋图谱链移植为确定性引擎；供给策略本体化——
**矛盾来源同窗并立、截断显式**（window_note 如实声明"召回 N/送窗 M"），治"材料未披露"虚答与同型抢锚。

## 不做什么

不做生成（GEN 是 runtime 阐述步的事）；不做 LLM 逐条打分 O(N)（V1 compound 档旧形态不带入）。
**V2-97（D7）精排「未接线」登记**：批量排序＋来源置信度两件精排（**原「精排最多两次 LLM
调用」表述**）代码保留**未接线**——生产装配 `RetrievalEngine` 构造无 `completer=`
（`appv2/api/app.py`），恒走确定性融合序放行；接线另立决策票（同批 `specs/tools.md`
「`graph_query` 摘除注记」）。**2026-10-18 补（V2-97）**；不改 V1 切片/索引产物。

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
# RetrievalBundle = {observations: list[Observation], window_note: str,
#                    recalled, sent, over_budget, anchor_seated, rowset_added,
#                    summary_expanded}   # 后四键＝V2-89b additive 归因机读面
# Observation 带出处链 fragment→report→library＋family 标注；
# window_note = "召回 N 支/送窗 M 支"＋矛盾来源同窗声明或缺位枚举
```

## 行为约定

1. 双路召回（向量＋关键词）→融合→精排（LLM 批量序＋来源置信度，失败回退 V1 确定性配额，不炸链）。
   **V2-97（D7）**：精排**未接线**（生产装配无 `completer=`）——本行为描述的是引擎保留面，
   现网恒走融合序；未接线登记与接线去向见「不做什么」节。
2. 供给分池按 family_hints/来源指纹：同主题矛盾来源（同型报告/跨油田同指标）必须同窗并立；
   送窗预算内每来源至少留代表支，缺位在 window_note 枚举。
   **V2-89b 补记（L1 预算真封顶，D3）**：锚保底／表类整行集／节内展开三通道的追加席
   **计入 `budget`**——超预算不再追加，`WindowSupply.window` 支数恒 ≤ `budget`（旧行为
   「追加席不计配额」实测 17/17 行 `returned > budget`，席次不可归因）。追加席候选因预算
   被丢时落机读位 `RetrievalBundle.over_budget = True`（**不是**「召回池大于预算」的普通
   截断——后者由 `recalled > sent`／window_note 差额段表达）；节内展开通道另守总补席上界
   `appv2/retrieval/domain.py::SECTION_EXPAND_CAP`（每摘要席展开同节切片，一次检索补席总数
   ≤ 该值且 ≤ 剩余预算——RC18「按节全量追加→窗支数翻倍」的治理面）。三通道实际入窗席数落
   `anchor_seated`／`rowset_added`／`summary_expanded` 三个 additive 计数（`retrieval_calls`
   留痕行同名字段的值源，见 `specs/tools.md`）。
3. 截断显式：召回>送窗时 window_note 写"召回 N/送窗 M"——agent 据此如实区分"没有"与"没送"。
   **V2-91 注（缺位名单停发）**：行为 2 末句的未纳入来源枚举**按单轮检索算**，与实际
   「多子问题并集＋材料选择」后的送窗不一致——`doc_retrieve` **不再**把该段作为独立观察
   （`locator.kind=window_miss` 的「检索窗注记（缺位名单）」）送入 `state.observations`／
   模型材料／引擎注记；window_note 主段（计数＋差额）逐字照旧走 notice 通道，名单原文只落
   审计机读面（`tools.handlers` 模块日志）。**「按实投窗重算的缺位名单」登记为后续能力**
   （不在本票恢复）；详注与判据见 `specs/tools.md`「`doc_retrieve` 缺位名单停发注记」。
4. 同型文档来源标注：每支 Observation 的 locator 带 library/报告名，锚错（A-W11 vs Y-21）可被核验步发现。
   **V2-93 补记（表格承载机读位）**：片段观察的 locator 在**表格承载**时追加 `table_bearing: True`
   （判据单点＝`appv2/retrieval/domain.py::_is_table_bearing`——缩进数字行 ≥2 的确定性版式词面，
   本引擎只调该单点、不另立第二份判定；非表格支不带此键，旧形零漂移）。该位供 L3 渲染窗
   「表格保底席」判据只读消费（`specs/context.md` 行为 4——L3 只读标记、零语义判断）；
   `node_kind`（`slice`／`section_summary`）机读位同面（V2-47 票）供「同源原文保底席」判据。
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
| L1 预算真封顶：扩席三通道候选齐备 → 窗支数恒 ≤ budget | `tests/domains/test_v2_retrieval.py::test_supply_window_never_exceeds_budget` |
| 追加席被预算丢 → `over_budget=True`（预算有余 → False） | `tests/domains/test_v2_retrieval.py::test_over_budget_flag_true_when_dropped` |
| 节内展开加上界（≤ `SECTION_EXPAND_CAP` 且 ≤ 剩余预算） | `tests/domains/test_v2_retrieval.py::test_section_expansion_capped_by_budget_and_upper_bound` |

## 依赖与风险

- 依赖：infra 复制票（embedder/gateway completer）；kb fixture（V1 片段库快照）。
- 风险：精排 prompt 与"矛盾同窗"策略的交互——同窗是供给层硬规则，不依赖 LLM 自觉（防 Q11 式失守）。
