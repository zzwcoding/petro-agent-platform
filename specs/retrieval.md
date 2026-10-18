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
| text_tokens | 新增 | 题眼 token 边界／数字全等判据单点（V2-100 D-a——L1 直引；`_anchor_score` 分层加权留 L3） |
| tools | 只消费 | V2-100：`RetrievalBundle.quota_dropped` 经 `tools.handlers.doc_retrieve` 落 `retrieval_calls` 行键（L0 授权扩张；字段语义见行为 2 补记） |

## 接口定义

```python
class RetrievalEngine:
    def retrieve(self, need: RetrievalNeed) -> RetrievalBundle: ...
    def graph(self, need: RetrievalNeed) -> RetrievalBundle: ...   # 图谱面

# RetrievalNeed = {question, anchors?, family_hints?, budget}
# RetrievalBundle = {observations: list[Observation], window_note: str,
#                    recalled, sent, over_budget, anchor_seated, rowset_added,
#                    summary_expanded, quota_dropped}
#                    # 后四键＝V2-89b additive 归因机读面；quota_dropped＝V2-100 additive
#                    # （配额丢席族——与 over_budget 并列、互不并入）
# Observation 带出处链 fragment→report→library＋family 标注；
# window_note = "召回 N 支/送窗 M 支"＋矛盾来源同窗声明或缺位枚举
```

## 行为约定

1. 双路召回（向量＋关键词）→融合→精排（LLM 批量序＋来源置信度，失败回退 V1 确定性配额，不炸链）。
   **V2-97（D7）**：精排**未接线**（生产装配无 `completer=`）——本行为描述的是引擎保留面，
   现网恒走融合序；未接线登记与接线去向见「不做什么」节。
2. 供给分池按 family_hints/来源指纹：同主题矛盾来源（同型报告/跨油田同指标）必须同窗并立；
   **V2-117 补记（主体提权——下游加权之「检索排序」，2026-10-18）**：融合序（`rrf_merge` 公式零改）
   之后、供给分池之前加一道**主体命中提权** `domain.promote_subject_hits`——**分池序内**提权：
   池＝族（`fragment.family`，出场序＝融合序首现序），逐族把命中**题面主体 token** 的候选前移、
   族内其余候选保持原相对序（**族与族之间的出场序不动**）；命中判据＝三面任一（正文 ∪ 报告名 ∪
   油田标签，复用题眼锚保底同判据单点 `_anchor_hits`；判据本体仍＝`appv2.text_tokens` 边界／数字
   全等）；题面主体 token 面＝题面资产编号（井号／报告号／油田号——`anchor_seat_tokens` 单点，
   与题眼席保底同面）。`tokens` 空／无命中／`ranked` 空 ⇒ **原样返回**（零漂移面）。纯函数、零 IO、
   零模型。断言＝`tests/domains/test_v2_v117_subject_reflection.py::test_retrieval_promote_subject_hits_within_family_pool`。

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
   **V2-100 补记（L1 席序重排，D9／D-h）**：`supply_window` 席序改为
   **① 题眼锚/表格/原文候选先占预算 → ② 族配额（用剩余预算）→ ③ 表类整行集 → ④ 节内展开
   → ⑤ 余量补给**（余量步保留——D-h 明确不许丢）：
   - ① 三通道**只对「锚命中来源」生效**（命中面＝text ∪ report ∪ well，V2-82d）；`anchors`
     为空时三通道零动作 ⇒ 席序与旧序**逐字等价**（零漂移面）：锚席＝逐锚取融合序最优命中支
     （V2-45 锚保底）；表席＝锚命中来源的表格承载支且**表文命中锚**（复用行集目标判据，防无关
     高位表格误占）；原文席＝锚命中来源尚无 `node_kind=slice` 原文席时取其首个原文切片
     （摘要不得顶替同源原文——D9）；
   - **去重粒度＝片段级**（`picked_ids`——取代旧「来源级」去重）：同源多锚可各占一席；同源
     **题眼席上界＝`max(1, budget//2)`**（量纲复用 `source_diversify` 的「同报告至多半额」规则；
     **不**引 L3 常量 `ANCHOR_SEATS`／`MAX_REPORT_SEATS_PER_SOURCE`、不新增数值常量）——防同源
     多锚把预算吃干（旧来源级去重已废，取代关系＝本补记）；
   - **新丢席族 `WindowSupply.quota_dropped`**（additive，整数计数）＝族配额候选因剩余预算不足
     被丢的支数；**不得**并入 `over_budget`（后者语义冻结为「追加席候选（锚/行集/展开三通道）
     被丢」——保 EB10 已登记区分度）；两者各有独立值源、可分别判读；
   - 判据单点（D-a）：锚命中判定＝`appv2.text_tokens.boundary_hit`／`num_token_hit`（L1 直引，
     `_anchor_text_hit` 只做「纯数字→全等／其余→边界」形分派，边界/全等本体零副本）。
3. 截断显式：召回>送窗时 window_note 写"召回 N/送窗 M"——agent 据此如实区分"没有"与"没送"。
   **V2-122 补记（注记改写为对作答面的范围指令＋计数如实，S2＋S5）**：`domain.build_window_note`
   在既有各段（主段／差额段／同窗段／缺位段／extra——逐字零改）**串尾按序尾接**两条指令
   （逐字稿＝`tickets/v2/V2-122-材料范围限定与计数如实.md` §逐字稿；措辞单点＝本文件
   `NOTE_SCOPE_DIRECTIVE`／`NOTE_COUNT_TRUTHFUL`，段间仍以「；」连接）：
   `NOTE_SCOPE_DIRECTIVE`＝**断言/否定只锚已见材料**（不得因「未见」断言材料中不存在；说
   「本次材料未覆盖」，不得升格「报告/资料库未载」）——治 `A-正6`／`Q41` 池级否定（`EB11`
   交付面「没有任何一条材料提及」）；`NOTE_COUNT_TRUTHFUL`＝注记「检索到 N 条／用进 M 条」
   必须与实际一致。计数**值源单点不变**（`RetrievalBundle.recalled/sent`——注记产文与
   机读键同源）；`tools.handlers._bundle_to_result` 把该两数透传至 window_note notice 的
   locator 键 `window_note_counts`（**并键登记、禁第三真源**：与 `window_materials.rendered/
   total`〔窗面〕、`Verdict.delivered_rows/obs_rows`〔行集交付面〕并列，三者各表不同物），
   答案步 payload 同名落键（消费方 `answering`——见 `specs/answering.md` 行为 24）。
   **L1 `budget` vs L3 帽同源裁定**（设计 §六-7 悬空项，本票登记）：两值**同源单点**
   ＝`appv2/tools/schema.py`，但**非同物**——L1 `ToolContext.budget`＝per-call 送窗预算
   `resolve_send_budget(count)`＝`min(SEND_BUDGET_CAP, SEND_BUDGET_PER_SUBTASK × count)`
   （单支＝6、上限即帽 24）；L3 帽 `context.DEFAULT_MAX_OBSERVATIONS`＝`SEND_BUDGET_CAP`
   的**导入别名**（V2-93 D2）。故登记为「**同源单点＋两值不同物**」：L1 预算的**上界**＝
   L3 帽值，但单支题 L1 预算（6）≠ L3 帽（24）；两值各一处定义、无第三副本。
   断言＝`tests/domains/test_v2_v122_material_scope_counts.py::
   test_l1_l3_budget_same_source_two_values_registered`。
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
| V2-100 席序重排：题眼锚命中来源先占预算（`anchor_seated>0`——旧序族配额吃干⇒0） | `tests/domains/test_v2_retrieval.py::test_supply_window_topic_anchor_seated_before_family_quota` |
| V2-100 题眼表保底席：锚命中来源的表格承载支先占预算（摘要不顶替） | `tests/domains/test_v2_retrieval.py::test_supply_window_topic_table_seat_keeps_detail_row` |
| V2-100 题眼原文保底席：同源摘要群挤占下原文切片必进窗（NQ-C9 形） | `tests/domains/test_v2_retrieval.py::test_supply_window_topic_original_seat_keeps_section` |
| V2-100 片段级去重＋同源上界 `max(1, budget//2)`（同源多锚可占多席但不吃干预算） | `tests/domains/test_v2_retrieval.py::test_supply_window_topic_fragment_dedup_and_source_bound` |
| V2-100 新丢席族：`quota_dropped`（配额候选被丢）与 `over_budget`（追加席候选被丢）互斥可判、互不并入 | `tests/domains/test_v2_retrieval.py::test_quota_dropped_and_over_budget_disjoint` |
| V2-100 可观测链：`WindowSupply.quota_dropped` → `RetrievalBundle` → `retrieval_calls` 行键（真引擎端到端透传，两丢席族行上各自可判） | `tests/domains/test_v2_retrieval_calllog.py::test_retrieval_calllog_quota_dropped_end_to_end` |
| V2-100 余量补给步保留（题眼先占后仍不满预算→按融合序补齐） | `tests/domains/test_v2_retrieval.py::test_supply_window_remainder_supply_still_fills_budget` |
| D-诱12 不回退（L1 面）：`W-11≠W-111`／`22≠2200` 边界/全等判据（V2-100 D-a 单点） | `tests/domains/test_v2_retrieval.py::test_supply_window_l1_anchor_boundary_no_substring` |
| V2-122 注记尾接两条范围指令（逐字照抄；旧段逐字零改；与 V2-101 首句互斥不重复） | `tests/domains/test_v2_v122_material_scope_counts.py::test_note_scope_and_count_directives_verbatim_tail`／`::test_note_legacy_segments_verbatim_before_tail`／`::test_note_directives_single_source_in_domain`／`::test_v122_texts_mutually_exclusive_with_v101` |
| V2-122 计数如实：`A-正6`（45/6）／`Q41`（63/6）／`A-正2`（48/6）三形——注记数字＝实际＋答案步 payload `window_note_counts` 同源 | `tests/domains/test_v2_v122_material_scope_counts.py::test_count_truthful_a_zheng6_shape`／`::test_count_truthful_q41_shape`／`::test_count_truthful_a_zheng2_shape`／`::test_window_note_counts_single_source_registration` |
| V2-122 库级否定消除：`A-正6`／`Q41` 形交付「本次材料未覆盖」、零「没有任何一条材料提及」；旧注记对照仍出库级否定（红→绿由注记文本唯一决定） | `tests/domains/test_v2_v122_material_scope_counts.py::test_a_zheng6_shape_library_negation_eliminated`／`::test_q41_shape_library_negation_eliminated`／`::test_library_negation_control_when_directive_absent` |
| V2-122 L1 `budget`(6) vs L3 帽(24)：同源单点＋两值不同物登记 | `tests/domains/test_v2_v122_material_scope_counts.py::test_l1_l3_budget_same_source_two_values_registered` |

## 依赖与风险

- 依赖：infra 复制票（embedder/gateway completer）；kb fixture（V1 片段库快照）。
- 风险：精排 prompt 与"矛盾同窗"策略的交互——同窗是供给层硬规则，不依赖 LLM 自觉（防 Q11 式失守）。
