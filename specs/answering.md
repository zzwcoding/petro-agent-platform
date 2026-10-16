# V2 作答（answering）

状态: 已定稿
来源: `specs/modules.md` `## answering` 卡、`docs/runtime-refactor/walk/14-作答-汇总作答.md`、`walk/裁决表.md` §14、`synth/S1`（M6）
版式: `docs/spec-format.md` ｜ 工序: `docs/spec-process.md`

## 目标

把前面查到的**全部子问题结果**整理成**一份答案**——**一段段推给页面（真流式）**、**每句带出处**、**缺口如实交代**。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 逐句核验「有没有材料撑着」 | `verification` | `specs/modules.md` `## verification` |
| 执行查询、产观察 | `execution` | `specs/modules.md` `## execution` |
| 大结果**原文**的落盘与引用载体 | `execution` 落、`persistence` 为载体（本块**只消费引用**） | `walk/裁决表.md` §14-B；评审 E-10 处置（`docs/runtime-refactor/spec-review/execution-评审.md` E-10） |
| 材料段与 Manifest 的编译 | `context` | `specs/modules.md` `## context` |
| 提示词合同文本与指令装配 | `prompts` | `specs/modules.md` `## prompts` |
| 模型调用出口 | `gateway_adapter` | `specs/modules.md` `## gateway_adapter` |
| 拿词表／正则猜「这句话答没答上原问题」 | 交模型与 `verification`；程序只做结构判据 | `walk/00-设计总纲.md` §二 |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| answering | 新增 | 起草 ＋ 真流式推出 ＋ 引用落账 ＋ 结构化缺口 |
| context | 新增 | 材料段与 Manifest（本块只消费其编译出口） |
| prompts | 新增 | 答案轮指令装配文本（只出文本；材料段不在装配输出内——材料渲染归 `context`，本块材料渲染＝消费 `context` 编译产物、零自取，与 `specs/context.md` 定界互认） |
| bookkeeping | 新增依赖 | 模型调用发起面：经 bookkeeping.call_model（单点发起），本块不直引 gateway_adapter |
| gateway_adapter | 新增 | 模型出口（唯一出口仍归它）；本块不直引——经 bookkeeping.call_model 发起 |
| state | 新增 | 草稿／引用块／缺口的状态形状（本块只消费） |
| transport | 新增 | **`text` 帧的增量发射**（本块只经其公开面） |

## 接口定义

```python
def answer(state: RunState) -> AnswerDraft: ...

class AnswerDraft:
    segments: list[AnswerSegment]     # **增量片段**（流式逐段；顺序即呈现顺序）
    citations: list[Citation]         # 引用块（引标 → 观察序号）
    gaps: list[Gap]                   # **结构化缺口**（被拒／缺失／未及核验）
class AnswerSegment:
    text: str
    citation_seqs: list[int]          # 本段引用的观察序号（[n]；与全局观察同一套序）
class Citation:
    seq: int                          # 引标编号（＝观察序号）
    locator: str                      # 可机读出处（台账行／片段→报告→库／表名）
class Gap:
    kind: Literal["refused", "missing", "unverified"]   # 闭世界
    subtask_id: str | None
    reason: str
```

- **`Gap.kind` 是闭世界**（`refused`｜`missing`｜`unverified`）；越界值判失败。
- **`citation_seqs` 里的每个序号必须真实存在于观察序列**；不存在的引标＝判失败（对应「坏引标」病灶）。
- **大结果引用经 `seq → observation.ref`（`MaterialRef`）可达**：`Citation` 不另设 `handle` 字段，与 `specs/execution.md` 的字段口径显式对齐（真源 `walk/裁决表.md` §14-B）。
- 错误契约：起草失败（模型不可用／空稿超限）→ **不返回半成品**；由 `orchestration` 承接（挂起或如实收口），**不静默推空答案**。
- 真源：`specs/modules.md` `## answering` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本模块不引入任何框架）。
- **模型调用发起面＝`bookkeeping.call_model`（单点发起）；其内部唯一出口＝`gateway_adapter`**：本块不直引 `gateway_adapter`（import 落点＝`appv2.runtimev2.bookkeeping` 包根——R2 禁深层子模块）。验收写法：模型调用发起点只出现在 `bookkeeping.call_model` ＋ 调用行为测试绿。对应闸：`tools/importlinter_v2.toml` 的 **R7 契约**（禁直引 `appv2.infra.llm_client`——模型出口仍唯一归 `gateway_adapter`；**B6 只管 litellm 出 `infra`，不含「绕过 `gateway_adapter` 直引」这一面**）＋ 一条「无旁路」行为断言（写法照 `specs/tool_matching.md` 同款；发起面收敛为规格层 doctrine，不设闸——主窗 2026-10-15 裁）。
- **不得直接 import `langgraph`／`langchain`**（框架只许在 `orchestration`）；对应闸：**R5b 契约**。
- **只经 `transport` 公开面**发帧（不自行拼 wire 帧、不直接接触 SSE 通道）。
- **禁手写替代**：不得自建模型客户端、不得自建帧通路。对应闸：`tools/importlinter_v2.toml` **R7 契约**（模型出口唯一归 `gateway_adapter`——发起经 `bookkeeping.call_model`）；验收写法：「无旁路」行为断言（模型调用发起点只出现在 `bookkeeping.call_model`，无自建旁路）。（**「自建帧通路」一面**：`transport` 的「只经包根」半面由 **R2 契约**覆盖，见「与闸的挂钩表」；另一半无闸。）

## 行为约定

1. **真流式**：答案**一段段推**（`text` 帧随增量发射），**不是收口时一次性推全量**。**免起草旁路例外（2026-10-16 补（L0/L2 三病灶修复批③））**：`draft_kind="direct"`（`route="direct"` 直答／拒答／闸拒／收敛转答——`bookkeeping.direct_answer` 三键与 `converge` 同落该值）**不发起草段**，其交付正文帧由**编排面**在收口后补发一帧（本块零帧：帧面归 `orchestration`，真源 `specs/agent-loop.md` 行为 8——真机证据 `docs/runtime-refactor/ladder/L0/01` 零 `text` 帧＝用户端空白）；本块**起草路径**的帧面与判据不变（判据只认 `draft_kind="direct"`，保留面不回归）。
2. **引标与增量同步**：每段自带 `citation_seqs`；**引标编号＝观察序号**（全局同一套），段与引用不脱节。
3. **逐句可核**：每个事实断言都带引标；**无据的话不写进答案**（无据由 `verification` 改写，本块不产出无据句）。
4. **材料进上下文必须显式（本块只消费 `context` 的编译出口、只断言不实现）**：每次模型调用**必须有 Manifest 在场**（缺失＝判失败；Manifest 的编译归 `context`）；**大结果只以引用形式进窗口**（正文落 `persistence`，见 `execution`），本块不重复落。
5. **结构化缺口**：被拒／缺失／未及核验的部分，除文字外必须给出 `Gap`（哪个子问题、哪一类、为什么、还差什么）；**不静默截断**。
6. **多来源矛盾分开列**：矛盾数据**分源列明、不强调和**；并在 `Gap`／引用块里标出「互不一致」（对应最佳实践的 `refuted_by` 取向）。
7. **链尾同步**：收口时引用块、`citation` 帧、`verdict` 帧、对话链尾**同批落定**，不得只落其一；其中 **`verdict` 帧的批次落定由 `orchestration` 协调**，本块只保证自产部分（引用块／`citation` 帧）就位。
8. **模型原话不进对话层**：模型的中间原话只进过程档案与留痕。
9. **空稿不推**：若起草得到空稿或全部无据，**不推空答案**——按结构化缺口如实收口。
10. **答案要求以 `prompts` 的合同文本为唯一真源**：本规格不复制该清单（避免两处漂移）；条数现状真源＝`docs/runtime-refactor/recon/L2b-作答装配与回声.md`（`_ANSWER_REQUIREMENTS`，现 **8 条**——2026-10-17 EB2 D2 追加第八条「核验元数据不进答案正文」，条数真源随本合同走），**V2 条数以 `prompts` 合同定稿为准**。
11. **发射剥离**：模型应答在进答案面（`AnswerDraft` 片段与其 `text` 帧增量）之前经**发射围栏／JSON 形确定性剥离**——发射 JSON 不得进答案面（泄漏=0）。真源：`eval/results/Q15-对账报告.md`（:38——Q14 6 题→0，V2-48 发射围栏确定性剥离＋通道隔离兑现）；旧码真源 `docs/runtime-refactor/recon/L2b-作答装配与回声.md`（:58 `strip_emission_fences`／:101 剥离后草稿才进答案装配）。
12. **行集题交付与落引用界线**（与 `specs/execution.md` 行为 4 同一规则、逐字一致）：行集题（明细行集类：问句要求明细／排名／列举全行集）全量交付为默认——引擎返回的全部数据行逐行交付、丢行＝0；非行集大结果超阈才落引用（窗口只留摘要＋稳定引用＋行数），截断与落引用必披露。阈值数值阶段 5 待定（随真机数据定），行为归属与披露义务即此定死：行集题不得因落引用而丢行。真源：`tickets/v2/V2-61-材料承载分形渲染.md`（:5——24 支一刀切截断废除、改分承载体渲染）。
13. **占位符不进答案面**：答案面不得出现字面占位引标 `[n]`（确无可引序号时一个引用记号都不写）；含 `[n]` 字面的行不得以占位符形式交付。真源：`eval/results/Q16-判分报告-G3.md`（:56——数字在场而 cited=[] 的 D-诱15 形）；`tickets/v2/V2-69-坏引标修复.md`（占位符串台根因＋「禁止占位符 [n] 进答案」指令纪律）。
14. **起草回声＝0**：草稿首行不得以「理解：」开头、草稿前 100 字不得含「指标候选」（`echo_flag` 恒 0——观测字段只记不拦）。真源：`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`（A-P4b-61——`echo_flag` 形态判据定义）；`eval/results/Q16-对账报告.md`（:61——echo_flag 全批 0，回声形态自 V2-62 后零再现）。
15. **台账 no_hit 降级交付三段形**：台账 no_hit（agg 未落列 notice 在场）时的降级交付必须**三段齐**——①油田级邻近可得量**带引用**交付；②逐井明细**逐井「未找到」明示**；③**指路**（替代出路指引）；且**零逐井数值冒充**（无逐井数据不得以油田级值充当逐井值）。真源：`eval/results/Q16-判分报告-G1.md`（:39 数-降2 判语——「油田级 8.10 万吨邻近可得引用＋逐井明细未找到明示＋指路，零逐井数值——轴第 4 条满分形」）；`eval/README.md`（「判分轴统一登记」第 4 条——引擎降级解释＋如实标注＝✅ 满分，诚实转述也是正确交付，数-降1/数-降2 跷跷板就此封尺）。
16. **排名型子问题强制消费排名观察支**：排名型子问题（问句求排名／排序序）的答案必须从**排名观察支**取值——交付的排名序对（对象↔名次／值）须与排名观察支的序信息一致，**不得弃排名支、以他支拼排名**（数-排2 形——帧证 obs[52]/[53] 曾弃即病形）。真源：`docs/runtime-refactor/arch/P4a2-票堆V2-51至55.md`（A-P4a2-04——「排名型子问题答案强制消费排名观察支（数-排2 形，帧证 obs[52]/[53] 曾弃）」）。
17. **跨油田题分源列明油田归属**：交付面涉**多油田**（或跨区块／跨层系）的题，答案必须**分源列明每条结论的归属**（油田名↔数值／结论配对），**不得框成「某区块／小范围结算序列」等含糊归属**（C-正6 形禁现）；**无据归属不得进答案面**（与行为 3「无据的话不写进答案」同族；`eng/04a` 族面＝pin-02「无据差值/无据口径框架」）。合同侧承接＝`prompts` 答案要求③（多来源逐个来源分别作答，不冲突也要分别列出）。可写成 assert：多油田 fixture 下答案面归属配对在场＋「某区块」形零命中。真源：`eval/results/Q16-判分报告-G3.md`（:32——C-正6 判语逐字：「34-8 侧 −42.6 被无据框成"某区块/小范围结算序列"、不认列渤中34-8 油田归属——跨套混写不分油田档＋无据调和」）；`eval/results/Q15-对账报告.md`（:167——族 C 跨报告归属校验：attribution_split 分源列明块帧证）；`docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-03——「跨油田题交付必须分源列明油田归属，不得框成『某区块』不认归属」，golden，P0）。

## 不降级与静默禁令

- **合法降级路径：无**（本模块不自降级；起草原话不完整时走结构化缺口，不改写事实）。
- 流式增量、缺口、截断披露、收口都必须产生机读信号：本块自产的 `text`／`citation` 事件（类型取自 `synth/S6-事件与帧目录.md`）＋ 材料截断的 `material_truncated` notice（真源 `tickets/v2/V2-61-材料承载分形渲染.md` 附 D）＋ step payload 的 `citations`／`gaps` 字段；`verdict` 事件为**消费方信号**——其批次落定由 `orchestration` 协调（见行为 7），本块只保证自产帧。
- 红线原文：`arch/P7a-交接包与挂账清单.md`（A-P7a-37）「**不许静默**——若任何相位仍发生截断，模型面必须随材料段带明示……收口注记面同步披露」。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 答案**一段段推**（多段 `text` 帧），非一次性推全量 | `tests/domains/test_v2_answering.py::streaming_segments` |
| 每段自带 `citation_seqs`，且序号**真实存在于观察序列** | `tests/domains/test_v2_answering.py::segment_citations_resolve` |
| 出现不存在的引标号 → 判失败（坏引标） | `tests/domains/test_v2_answering.py::dangling_citation_rejected` |
| 每次模型调用都有 Manifest；大结果只以引用进窗口 | `tests/domains/test_v2_answering.py::manifest_and_ref_only` |
| 被拒／缺失／未及核验 → 产出结构化 `Gap`（三档闭世界） | `tests/domains/test_v2_answering.py::structured_gaps_all_kinds` |
| `Gap.kind` 越界取值 → 判失败 | `tests/domains/test_v2_answering.py::gap_kind_closed_world` |
| 矛盾来源分列且标「互不一致」，不调和 | `tests/domains/test_v2_answering.py::contradiction_split_not_merged` |
| 收口同批落定（引用块＋citation 帧＋verdict 帧＋链尾） | `tests/domains/test_v2_answering.py::finalize_atomic` |
| 空稿／全无据 → 不推空答案，按缺口如实收口 | `tests/domains/test_v2_answering.py::empty_draft_not_pushed` |
| 模型原话不进对话层 | `tests/domains/test_v2_answering.py::raw_not_in_dialogue` |
| 发射 JSON 不进答案面（发射围栏／JSON 形确定性剥离，泄漏=0） | `tests/domains/test_v2_answering.py::emission_strip_zero_leak` |
| 明细行集题交付行数＝引擎返回行数（50 行全交付，丢行=0） | `tests/domains/test_v2_answering.py::rowset_full_delivery` |
| 材料截断必披露：`material_truncated` notice＋「未渲染部分不作答」声明在场（未截断零 notice） | `tests/domains/test_v2_answering.py::truncation_disclosed` |
| 答案面无字面占位符 `[n]`（含 `[n]` 行不以占位符交付） | `tests/domains/test_v2_answering.py::placeholder_marker_not_in_answer` |
| 起草回声=0：首行不以「理解：」开头／前 100 字不含「指标候选」（echo_flag 恒 0） | `tests/domains/test_v2_answering.py::echo_flag_zero` |
| 台账 no_hit → 降级交付三段形（油田级邻近可得引用＋逐井「未找到」明示＋指路）且零逐井数值冒充 | `tests/domains/test_v2_answering.py::no_hit_degraded_delivery_three_part` |
| 排名型子问题答案消费排名观察支（排名序对与排名支序信息一致，不弃支他拼） | `tests/domains/test_v2_answering.py::ranking_answer_consumes_ranking_obs` |
| 多油田题答案面分源列明归属配对（油田名↔数值／结论）在场＋「某区块」含糊归属形零命中 | `tests/domains/test_v2_answering.py::cross_oilfield_attribution_paired` |
| 程序侧无词表／正则语义判断（AST 扫描；豁免面＝形态处理／集合成员判定） | `tests/domains/test_v2_answering.py::no_lexicon_or_regex_in_answering` |
| 流式、缺口、截断披露的机读信号在场（text／citation 帧＋material_truncated notice＋step payload；verdict 为消费方信号，批次落定归 orchestration） | `tests/domains/test_v2_answering.py::answering_signal_present` |
| 【边界集】单段答案／零材料／矛盾双源／坏引标 → 各自落到对应分支 | `tests/domains/test_v2_answering.py::boundary_single_seg_zero_material_conflict_bad_cite` |
| 【保留集】无矛盾、无缺口的普通答案：引标与分源行为不变 | `tests/domains/test_v2_answering.py::retention_plain_answer_unchanged` |

## 依赖与风险

- 依赖：`context`（材料与 Manifest）、`prompts`（答案轮指令）、`bookkeeping`（模型调用发起面——`call_model` 单点发起）、`gateway_adapter`（模型出口——经 `call_model` 的内部唯一出口，本块不直引）、`state`（状态形状）、`transport`（`text` 帧）。
- 风险与对策：
  1. **「真流式」退化成「收口一次推全量」**（本块最大缺口、易复发）→ 对策：验收以「多段 `text` 帧」为判据；检测手段＝`streaming_segments`。
  2. **引标与增量脱节**（段出了、引用没跟上）→ 对策：每段自带 `citation_seqs` 且必须可解析；检测手段＝`segment_citations_resolve`／`dangling_citation_rejected`。
  3. **缺口只写文字、不给结构化**（回到旧形态）→ 对策：`Gap` 为必填产物；检测手段＝`structured_gaps_all_kinds`。
  4. **答案要求清单两处漂移**（规格复制一份 vs `prompts` 合同）→ 对策：本规格**只引不复述**；检测手段＝人审（阶段 7 接口契约对账）。**登记（W4 对账批，2026-10-16）——V2 发射动作全量枚举无单点真源**：`parsing.CLARIFY_ACTIONS`（澄清面四动作：`discover`／`decompose`／`ask`／`finalize`）与本块 `EMISSION_ACTIONS`（`discover`／`execute`／`ask`／`finalize`——行为 11 剥离的域内判据，V1 `graph.ACTION_KINDS` 字面迁移）**非同族**；**扩域＝规格变更**（须同批对账两处并回设计仓），本批只登记、不扩、不新立第二闭世界。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 模型调用经 `bookkeeping.call_model` 发起（单点发起；其内部唯一出口 `gateway_adapter`） | 边界闸 **R7**（出口面：禁直引 `appv2.infra.llm_client`；B6 只管 litellm 出 `infra`。发起面为规格层 doctrine，不设闸） | 已真跑 |
| 不直接 import `langgraph`／`langchain` | 边界闸 **R5b** | 已真跑 |
| 只经 `transport` 公开面发帧（**只经包根**半面） | 边界闸 **R2**（业务相位禁引公共层块的**深层子模块**；`forbidden` 含 `appv2.runtimev2.transport.*`） | 已真跑 |
| 不自行拼 wire 帧／不直连 SSE 通道（另一半） | **无专属闸** → **人审** | 原因：R1–R8 无「不许出现直连帧通路符号」一面；降维（AST 断言）需新增验收行，本批未授权，登记待补 |
| 真流式（多段 `text` 帧） | 测试 `::streaming_segments` | 待实现（阶段 5） |
| 引标可解析 | 测试 `::segment_citations_resolve`／`::dangling_citation_rejected` | 待实现 |
| 结构化缺口（三档闭世界） | 测试 `::structured_gaps_all_kinds`／`::gap_kind_closed_world` | 待实现 |
| 程序不判语义 | 测试 `::no_lexicon_or_regex_in_answering` | 待实现 |
| 发射 JSON 不进答案面（确定性剥离，泄漏=0） | 钉 **`pin-04`**（P0） | 待织网（阶段 5） |
| 明细行集题全量交付（交付行数＝引擎返回行数，丢行=0；与 execution 行为 4 同一界线） | 钉 **`pin-08`**（P0） | 待织网（阶段 5） |
| 材料截断必披露（`material_truncated` notice＋「未渲染部分不作答」声明） | 钉 **`pin-09`**（P1） | 待织网（阶段 5） |
| 起草回声=0（`echo_flag` 恒 0） | 钉 **`pin-13`**（P1） | 待织网（阶段 5） |
| 台账 no_hit 降级交付三段形（油田级邻近可得引用＋逐井「未找到」明示＋指路，零逐井数值冒充——轴④封尺满分形）——落点＝行为 15 | 钉 **`pin-20`**（P1） | 待织网（阶段 5） |
| 排名型子问题强制消费排名观察支（排名序对与排名支序信息一致，不弃支他拼）——落点＝行为 16 | 钉 **`pin-19`**（P1） | 待织网（阶段 5） |
| 跨油田题分源列明油田归属（油田名↔数值／结论配对；「某区块」含糊归属形禁现——C-正6 形）——落点＝行为 17 | 钉 **`pin-03`**（P0） | 待织网（阶段 5） |
| 「不做什么」的纯范围排除（不执行查询／不核验等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（相位互不 import）已由边界闸 R1 覆盖 |
