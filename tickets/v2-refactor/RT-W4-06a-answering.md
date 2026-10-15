# RT-W4-06a · answering——V2 作答（-A：骨架＋接口＋交付行为簇）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/answering.md`（状态「已定稿」——前置满足）
Touches modules: `answering`（本票只建 answering 本体；规格「触及的模块」表另声明 context／prompts／bookkeeping／gateway_adapter／state／transport 六关联侧，归各自票承接）
波次: W4 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W4 行三列原文：块列「七个业务相位（understanding → clarification → tool_matching → preconditions → execution → answering → verification）」；理由列「互零依赖，**建议按业务链序施工**（便于走查 narrative 与测试网逐块加厚），不禁止并行」；出口判据列「每相位配属规格十节版式定稿＋新规格钉绿＋触及该相位的特征钉绿」
复审强度: 100%（eng/03 §五 更新行原文：「B 列六块＝质量关键块施工后 100% 复审，A 列抽 50%，交界归消费者验证」——W4 行 B 列含 `answering`；双队制已废止，A/B 分配只余复审强度语义，波序与块归属不变。复审网在 L0 直派、报告直送主窗）
前置: ① 规格定稿（`specs/answering.md` 已定稿——已满足）；② 波次前置：**W3 全收波**（eng/03 §一依赖图原文「answering → context + prompts + gateway_adapter + state」——context 归 W3，prompts／gateway_adapter 归 W2、state 归 W1）；③ 业务链序便利位：本块序前的 `execution`（RT-W4-05a／-05b）已收——**非硬阻塞**（eng/03 §一原文：「七个业务相位**互相零依赖**（R1 禁互引）——它们之间没有施工先后约束」）；④ W4 硬前置＝本块触及的特征钉已钉好（eng/03 §四）
阻塞: W3 全收波（bookkeeping／context／gate 三票，票号以主窗 manifest 为准）｜被阻塞: `RT-W4-06b-answering.md`（同包顺序施工——-06b 前置＝-06a 收票）、W5 `orchestration`

## 任务

在阶段 2 占位骨架上落地 `appv2/runtimev2/answering/`（现为 `__init__.py` 占位骨架）：把前面查到的**全部子问题结果**整理成**一份答案**——**一段段推给页面（真流式）**、**每句带出处**、**缺口如实交代**（`specs/answering.md`「目标」节原文）。

**本票＝answering 的 -A 票（骨架＋接口＋交付行为簇）**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **22 行**，超 15 行上限 → 切 -A／-B 两票（两票各 ≤15 行，一子代理一次吃完）。本票收 **10 行**＝规格表第 1–6、8–11 行（真流式起草／引标与坏引标／材料面与 Manifest／结构化缺口／收口原子性／发射剥离）；剩余 **12 行**＝规格表第 7、12–22 行（矛盾分源／行集全交付／截断披露／占位符／回声／no_hit 降级／排名支／跨油田归属／零语义判断／机读信号／边界·保留集）归 `RT-W4-06b-answering.md`（降级与引用簇）。两票同包**顺序施工**（同包不并行）：本票出骨架、公开面与答案面主干，-06b 只填降级与引用簇、不另立第二套形状。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/answering.md` 全文（十节版式）；`specs/modules.md` `## answering` 卡（签名以卡为准——`answer(state) -> AnswerDraft`）；`specs/context.md`（材料段与 Manifest 编译出口——本块只消费、零自取）；`specs/prompts.md`（答案轮指令装配文本与**答案要求唯一真源**）；`specs/bookkeeping.md`（`call_model` 单点发起面）；`specs/transport.md`（`text`／`citation` 帧增量发射面）。eng/04 §三 关联行与 eng/04a pin-04 已在本票「织网义务」「测试网钉」两节逐字转抄，施工期不必另开。

框架红线: 无点名框架（`langgraph`／`langchain` 只许活在 `orchestration`）——对应闸 R5b 契约（`tools/importlinter_v2.toml` :100–:105）
边界红线: ① **模型调用发起面＝`bookkeeping.call_model`（单点发起）**，其内部唯一出口＝`gateway_adapter`：本块不直引 `gateway_adapter`、不直引 `appv2.infra.llm_client`——R7（:113–:117）＋ R2（import 落点＝包根 `appv2.runtimev2.bookkeeping`，禁深层子模块 :73–:78）；② 只经 `transport` 公开面发帧：不自行拼 wire 帧、不直连 SSE 通道——「只经包根」半面由 R2 覆盖，另一半**无专属闸→人审**（规格「与闸的挂钩表」:141）；③ 不直引引擎（`appv2.knowledge`／`appv2.query`／`appv2.retrieval`）——R6（:107–:111）；④ 七个业务相位互不 import——R1（:66–:71）；⑤ 不引旧 `appv2.runtime`——R5（:94–:98）；⑥ **禁手写替代**：不得自建模型客户端、不得自建帧通路（自建旁路的验收写法＝「无旁路」行为断言：模型调用发起点只出现在 `bookkeeping.call_model`）；⑦ 材料渲染零自取：只消费 `context` 编译产物（本块不实现材料段编译）

## 票面对象（specs/answering.md「验收测试」表逐行转抄——本票 10 行：规格表第 1–6、8–11 行）

〔来源：specs/answering.md「验收测试」表 :100–:110（本票取自 :100–:105、:107–:110），逐行原文；`#` 列＝规格表行序，-B 票续用同一行序不重编〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | 答案**一段段推**（多段 `text` 帧），非一次性推全量 | `tests/domains/test_v2_answering.py::streaming_segments` | specs/answering.md:100 |
| 2 | 每段自带 `citation_seqs`，且序号**真实存在于观察序列** | `tests/domains/test_v2_answering.py::segment_citations_resolve` | specs/answering.md:101 |
| 3 | 出现不存在的引标号 → 判失败（坏引标） | `tests/domains/test_v2_answering.py::dangling_citation_rejected` | specs/answering.md:102 |
| 4 | 每次模型调用都有 Manifest；大结果只以引用进窗口 | `tests/domains/test_v2_answering.py::manifest_and_ref_only` | specs/answering.md:103 |
| 5 | 被拒／缺失／未及核验 → 产出结构化 `Gap`（三档闭世界） | `tests/domains/test_v2_answering.py::structured_gaps_all_kinds` | specs/answering.md:104 |
| 6 | `Gap.kind` 越界取值 → 判失败 | `tests/domains/test_v2_answering.py::gap_kind_closed_world` | specs/answering.md:105 |
| 8 | 收口同批落定（引用块＋citation 帧＋verdict 帧＋链尾） | `tests/domains/test_v2_answering.py::finalize_atomic` | specs/answering.md:107 |
| 9 | 空稿／全无据 → 不推空答案，按缺口如实收口 | `tests/domains/test_v2_answering.py::empty_draft_not_pushed` | specs/answering.md:108 |
| 10 | 模型原话不进对话层 | `tests/domains/test_v2_answering.py::raw_not_in_dialogue` | specs/answering.md:109 |
| 11 | 发射 JSON 不进答案面（发射围栏／JSON 形确定性剥离，泄漏=0） | `tests/domains/test_v2_answering.py::emission_strip_zero_leak` | specs/answering.md:110 |

> 测试文件归属（票注，非规格引文）：本块验收测试绑**新建** `tests/domains/test_v2_answering.py`（`answering` 是阶段 2 新划的相位块 `appv2/runtimev2/answering/`，与旧码 `appv2/runtime/` 里的作答实现测试形状不同）；旧码测试本批不改。
> 行序缺口说明（票注）：本票行序跳过第 7 行，第 7 行（矛盾分源）归 -06b——`#` 列两票共用规格表行序，便于 manifest 逐行对账。

## 测试网钉（specs/answering.md「与闸的挂钩表」pin 行逐行转抄——本块 7 行，本票承载『交付面』1 行，余 6 行归 -06b）

〔来源：specs/answering.md「与闸的挂钩表」:146，逐行原文；列名同规格「本规格的硬要求｜挂钩｜现状」〕

| 本规格的硬要求（原文） | 挂钩（原文） | 现状（原文） |
|---|---|---|
| 发射 JSON 不进答案面（确定性剥离，泄漏=0） | 钉 **`pin-04`**（P0） | 待织网（阶段 5） |

- 分票注（防两处漂移，逐字稿纪律）：本块另 6 条 pin 行（pin-08 行集全交付、pin-09 截断披露、pin-13 起草回声、pin-20 no_hit 降级、pin-19 排名支、pin-03 跨油田归属）对应行为全在**降级与引用簇**，逐字转抄落 `RT-W4-06b-answering.md`「测试网钉」节，本票不重复转抄。本块 7 条 pin 行无一为「骨架面」，故 -A／-B 的钉分布为 **1／6**（与 execution 两票的 3／0 分布不同——分布随行为簇落点走，不按票号硬摊）。
- 规格「与闸的挂钩表」其余行（R7／R5b／R2 三条边界闸、一条人审、十余条 `测试 ::...` 现状行）非 pin 行，按各自「挂钩」列由上述闸与用例承接，本票不转抄。

## 施工要点（specs/answering.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/answering.md:72 | 行为 1 真流式 | 答案**一段段推**（`text` 帧随增量发射），不是收口时一次性推全量（本块最大缺口、易复发——规格「依赖与风险」风险 1） |
| specs/answering.md:73 | 行为 2 引标与增量同步 | 每段自带 `citation_seqs`，引标编号＝**观察序号**（全局同一套），段与引用不脱节 |
| specs/answering.md:74 | 行为 3 逐句可核 | 每个事实断言都带引标；无据的话不写进答案（无据改写归 `verification`，本块不产出无据句） |
| specs/answering.md:75 | 行为 4 材料面显式 | 每次模型调用**必须有 Manifest 在场**（缺失＝判失败，Manifest 编译归 `context`）；大结果只以引用进窗口、本块不重复落 |
| specs/answering.md:76 | 行为 5 结构化缺口 | 被拒／缺失／未及核验必须给 `Gap`（哪个子问题、哪一类、为什么、还差什么），**不静默截断** |
| specs/answering.md:78 | 行为 7 链尾同步 | 收口时引用块／`citation` 帧／`verdict` 帧／对话链尾同批落定；**`verdict` 帧批次落定由 `orchestration` 协调**，本块只保证自产部分就位 |
| specs/answering.md:79 | 行为 8 模型原话不进对话层 | 模型中间原话只进过程档案与留痕 |
| specs/answering.md:80 | 行为 9 空稿不推 | 空稿或全部无据 → 不推空答案，按结构化缺口如实收口 |
| specs/answering.md:81 | 行为 10 答案要求唯一真源 | 答案要求以 `prompts` 合同文本为唯一真源；本规格**只引不复述**（条数现状真源＝`recon/L2b`，V2 条数以 `prompts` 合同定稿为准） |
| specs/answering.md:82 | 行为 11 发射剥离（钉 pin-04，P0） | 模型应答进答案面前经**发射围栏／JSON 形确定性剥离**——发射 JSON 不得进答案面（泄漏=0） |

结构锚：specs/answering.md:37–:60 接口定义（`answer`／`AnswerDraft`／`AnswerSegment`／`Citation`／`Gap` 五形状签名；`citation_seqs` 每个序号必须真实存在、`Citation` 不另设 `handle` 字段——与 `specs/execution.md` 字段口径显式对齐）；:62–:68 框架与依赖红线；:90–:94 不降级与静默禁令（**合法降级路径＝无**；流式增量／缺口／截断披露／收口必产机读信号；`verdict` 为消费方信号）。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单（本块无明写归块行，下列为逐字转抄的关联行）〕

> | B5 | 帧协议级时序（step/text/ask/verdict/done/error 序与 data 形） | 从 `eval/results/frames/` 真帧流转离线 golden 回放钉 | 中 |

- 归块注（呈主窗对账）：§三 表内**无一行明写「对应 runtimev2 `answering`」**；上引行是**关联行**——其帧序里的 `text` 帧（本块自产增量）与 `verdict` 帧（消费方信号，批次落定归 `orchestration`，见行为 7）即为本块在 B5 上的两面；钉法真源＝`eval/results/frames/` 真帧流转离线 golden 回放钉。
- 关联行（已转抄处）：B1（公共位与结果归一，明写归 `bookkeeping`）与 B3（限额上限）非本块行；本块只经 `bookkeeping.call_model` 消费其记账面，不另立钉。
- 本票织网义务＝① B5 关联行的 L3 回放钉（织网工序第 3 步「盲区补钉」，与 W1–W4 施工可并行——eng/04 头注）；②「测试网钉」pin-04 行对应用例落网；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」10 行逐行实现为 `tests/domains/test_v2_answering.py` 用例并全绿，测试标识与规格列逐字一致（`#` 保留规格表行序 1–6、8–11）；
- 「测试网钉」pin-04 行对应用例在场且绿（P0；泄漏=0 断言），另 6 条 pin 行的用例归属 -06b；
- 骨架与公开面按卡面签名（`answer(state) -> AnswerDraft`）＋五形状齐（规格 :37–:60）；
- 模型调用发起面单点：「无旁路」行为断言绿——模型调用发起点只出现在 `bookkeeping.call_model`，本块零 `gateway_adapter` import；
- 边界闸 R1／R2／R5b／R6／R7 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W4-06a 完成，产物 `appv2/runtimev2/answering/`（骨架＋接口＋交付行为簇），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
