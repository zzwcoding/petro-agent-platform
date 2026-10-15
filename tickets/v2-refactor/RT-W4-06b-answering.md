# RT-W4-06b · answering——V2 作答（-B：降级与引用簇）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/answering.md`（状态「已定稿」——前置满足）
Touches modules: `answering`（本票只填 answering 的降级与引用行为簇；规格「触及的模块」表另声明 context／prompts／bookkeeping／gateway_adapter／state／transport 六关联侧，归各自票承接）
波次: W4 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W4 行三列原文：块列「七个业务相位（understanding → clarification → tool_matching → preconditions → execution → answering → verification）」；理由列「互零依赖，**建议按业务链序施工**（便于走查 narrative 与测试网逐块加厚），不禁止并行」；出口判据列「每相位配属规格十节版式定稿＋新规格钉绿＋触及该相位的特征钉绿」
复审强度: 100%（eng/03 §五 更新行原文：「B 列六块＝质量关键块施工后 100% 复审，A 列抽 50%，交界归消费者验证」——W4 行 B 列含 `answering`；双队制已废止，A/B 分配只余复审强度语义，波序与块归属不变。复审网在 L0 直派、报告直送主窗）
前置: ① 规格定稿（`specs/answering.md` 已定稿——已满足）；② **`RT-W4-06a-answering.md` 收票**（同包顺序施工、同包不并行——eng/03 §二 W4 纪律）；③ W3 全收波（经 -06a 传递，已满足）
阻塞: `RT-W4-06a-answering.md`（-06b 前置＝-06a 收票）｜被阻塞: W5 `orchestration`

## 任务

接 `RT-W4-06a-answering.md` 落地的骨架，填 `appv2/runtimev2/answering/` 的**降级与引用簇**：矛盾分源、行集全交付与截断披露、答案面引标纪律（占位符／回声）、台账 no_hit 降级三段形、排名支强制消费、跨油田归属配对，以及零语义判断红线、机读信号在场与边界·保留集两行。

**本票＝answering 的 -B 票**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 22 行，超 15 行上限 → 切 -A／-B；本票收**剩余 12 行**＝规格表第 7、12–22 行；-A 的 10 行（真流式起草／引标／材料面／结构化缺口／收口／发射剥离）在 `RT-W4-06a-answering.md`。**本块 7 条 pin 行中 6 条**（pin-08／pin-09／pin-13／pin-20／pin-19／pin-03）对应行为全落本票，逐字转抄见「测试网钉」节；-A 只承载 pin-04（发射剥离）——钉分布 6／1 是行为簇落点的产物，不按票号硬摊。两票同包顺序施工：本票不另立第二套形状，`AnswerDraft`／`AnswerSegment`／`Citation`／`Gap` 仍以 -06a 落地的为唯一真源。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/answering.md` 全文（十节版式）；`specs/modules.md` `## answering` 卡（签名以卡为准）；`specs/execution.md`（行为 4「行集题交付与落引用界线」——与 `specs/answering.md` 行为 12 同一规则、逐字一致；`MaterialRef` 字段口径与 `Citation → seq → observation.ref` 对齐）；`specs/prompts.md`（答案要求合同文本＋「多来源逐个来源分别作答」条款——行为 17 的合同侧承接）；`specs/verification.md`（缺口三档与核验辖域——行为 3／5 的边界：核验归它、本块只产 `Gap`）；`docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-03／04／08／09／13／19／20 七行，核本票与 -06a 的边界）。

框架红线: 无点名框架（`langgraph`／`langchain` 只许活在 `orchestration`）——对应闸 R5b 契约（`tools/importlinter_v2.toml` :100–:105）
边界红线: ① 模型调用发起面＝`bookkeeping.call_model`（单点发起），不直引 `gateway_adapter`、不直引 `appv2.infra.llm_client`——R7（:113–:117）＋ R2（只引包根 :73–:78）；② 只经 `transport` 公开面发帧（不自行拼 wire 帧、不直连 SSE）——「只经包根」半面由 R2 覆盖，另一半**无专属闸→人审**（规格「与闸的挂钩表」:141）；③ 不直引引擎——R6（:107–:111）；④ 七个业务相位互不 import——R1（:66–:71）；⑤ 不引旧 `appv2.runtime`——R5（:94–:98）；⑥ **程序侧零语义判断**：无词表／正则语义判定（AST 断言 `::no_lexicon_or_regex_in_answering`，豁免面＝形态处理／集合成员判定）——「答没答上原问题」交模型与 `verification`；⑦ **禁手写替代**：不得自建模型客户端、不得自建帧通路；⑧ 本票不实现核验与改写（无据改写归 `verification`），不改 -06a 已定的形状

## 票面对象（specs/answering.md「验收测试」表逐行转抄——本票 12 行：规格表第 7、12–22 行）

〔来源：specs/answering.md「验收测试」表 :106–:121（本票取自 :106、:111–:121），逐行原文；`#` 列＝规格表行序（与 -06a 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 7 | 矛盾来源分列且标「互不一致」，不调和 | `tests/domains/test_v2_answering.py::contradiction_split_not_merged` | specs/answering.md:106 |
| 12 | 明细行集题交付行数＝引擎返回行数（50 行全交付，丢行=0） | `tests/domains/test_v2_answering.py::rowset_full_delivery` | specs/answering.md:111 |
| 13 | 材料截断必披露：`material_truncated` notice＋「未渲染部分不作答」声明在场（未截断零 notice） | `tests/domains/test_v2_answering.py::truncation_disclosed` | specs/answering.md:112 |
| 14 | 答案面无字面占位符 `[n]`（含 `[n]` 行不以占位符交付） | `tests/domains/test_v2_answering.py::placeholder_marker_not_in_answer` | specs/answering.md:113 |
| 15 | 起草回声=0：首行不以「理解：」开头／前 100 字不含「指标候选」（echo_flag 恒 0） | `tests/domains/test_v2_answering.py::echo_flag_zero` | specs/answering.md:114 |
| 16 | 台账 no_hit → 降级交付三段形（油田级邻近可得引用＋逐井「未找到」明示＋指路）且零逐井数值冒充 | `tests/domains/test_v2_answering.py::no_hit_degraded_delivery_three_part` | specs/answering.md:115 |
| 17 | 排名型子问题答案消费排名观察支（排名序对与排名支序信息一致，不弃支他拼） | `tests/domains/test_v2_answering.py::ranking_answer_consumes_ranking_obs` | specs/answering.md:116 |
| 18 | 多油田题答案面分源列明归属配对（油田名↔数值／结论）在场＋「某区块」含糊归属形零命中 | `tests/domains/test_v2_answering.py::cross_oilfield_attribution_paired` | specs/answering.md:117 |
| 19 | 程序侧无词表／正则语义判断（AST 扫描；豁免面＝形态处理／集合成员判定） | `tests/domains/test_v2_answering.py::no_lexicon_or_regex_in_answering` | specs/answering.md:118 |
| 20 | 流式、缺口、截断披露的机读信号在场（text／citation 帧＋material_truncated notice＋step payload；verdict 为消费方信号，批次落定归 orchestration） | `tests/domains/test_v2_answering.py::answering_signal_present` | specs/answering.md:119 |
| 21 | 【边界集】单段答案／零材料／矛盾双源／坏引标 → 各自落到对应分支 | `tests/domains/test_v2_answering.py::boundary_single_seg_zero_material_conflict_bad_cite` | specs/answering.md:120 |
| 22 | 【保留集】无矛盾、无缺口的普通答案：引标与分源行为不变 | `tests/domains/test_v2_answering.py::retention_plain_answer_unchanged` | specs/answering.md:121 |

> 测试文件归属（票注，非规格引文）：本票 12 行与 -06a 的 10 行同落**同一个新建文件** `tests/domains/test_v2_answering.py`；旧码测试本批不改。
> 交付面依赖注（票注）：本票行 12／16 依托 `RT-W4-05a-execution.md` 行 4（行集全交付／落引用，pin-08 执行侧）与 `specs/answering.md` 行为 12 的同规则行——两处规则逐字一致，**两票不得各自改口径**。

## 测试网钉（specs/answering.md「与闸的挂钩表」pin 行逐行转抄——本块 7 行的后 6 行；pin-04 行在 `RT-W4-06a-answering.md` 同节）

〔来源：specs/answering.md「与闸的挂钩表」:147–:152，逐行原文；列名同规格「本规格的硬要求｜挂钩｜现状」〕

| 本规格的硬要求（原文） | 挂钩（原文） | 现状（原文） |
|---|---|---|
| 明细行集题全量交付（交付行数＝引擎返回行数，丢行=0；与 execution 行为 4 同一界线） | 钉 **`pin-08`**（P0） | 待织网（阶段 5） |
| 材料截断必披露（`material_truncated` notice＋「未渲染部分不作答」声明） | 钉 **`pin-09`**（P1） | 待织网（阶段 5） |
| 起草回声=0（`echo_flag` 恒 0） | 钉 **`pin-13`**（P1） | 待织网（阶段 5） |
| 台账 no_hit 降级交付三段形（油田级邻近可得引用＋逐井「未找到」明示＋指路，零逐井数值冒充——轴④封尺满分形）——落点＝行为 15 | 钉 **`pin-20`**（P1） | 待织网（阶段 5） |
| 排名型子问题强制消费排名观察支（排名序对与排名支序信息一致，不弃支他拼）——落点＝行为 16 | 钉 **`pin-19`**（P1） | 待织网（阶段 5） |
| 跨油田题分源列明油田归属（油田名↔数值／结论配对；「某区块」含糊归属形禁现——C-正6 形）——落点＝行为 17 | 钉 **`pin-03`**（P0） | 待织网（阶段 5） |

- 分工注（票注，防双头）：pin-08 的**交付侧**落点＝本票行 12；**执行侧**落点＝`specs/execution.md` 行为 4（`RT-W4-05a-execution.md` 行 4，`::big_result_ref_only`）。pin-04（发射剥离，P0）行为面属交付簇，落 -06a。
- 规格「与闸的挂钩表」其余行（R7／R5b／R2 三条边界闸、一条人审、其余 `测试 ::...` 现状行）非 pin 行，按各自「挂钩」列由上述闸与用例承接，本票不转抄。

## 施工要点（specs/answering.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/answering.md:77 | 行为 6 多来源矛盾分开列 | 矛盾数据**分源列明、不强调和**；并在 `Gap`／引用块里标出「互不一致」（对应 `refuted_by` 取向） |
| specs/answering.md:83 | 行为 12 行集题交付与落引用界线（钉 pin-08，P0） | 行集题全量交付为默认、丢行＝0；非行集大结果超阈才落引用（摘要＋稳定引用＋行数），截断与落引用**必披露**；阈值数值阶段 5 待定（行为归属与披露义务已定死） |
| specs/answering.md:84 | 行为 13 占位符不进答案面 | 答案面不得出现字面占位引标 `[n]`（确无可引序号时一个引用记号都不写） |
| specs/answering.md:85 | 行为 14 起草回声＝0（钉 pin-13） | 草稿首行不得以「理解：」开头、前 100 字不得含「指标候选」（`echo_flag` 恒 0——**观测字段只记不拦**） |
| specs/answering.md:86 | 行为 15 台账 no_hit 降级三段形（钉 pin-20） | ①油田级邻近可得量带引用交付；②逐井明细逐井「未找到」明示；③指路；**零逐井数值冒充** |
| specs/answering.md:87 | 行为 16 排名型子问题强制消费排名观察支（钉 pin-19） | 交付的排名序对（对象↔名次／值）须与排名观察支序信息一致，**不得弃排名支、以他支拼排名** |
| specs/answering.md:88 | 行为 17 跨油田题分源列明归属（钉 pin-03，P0） | 交付面涉多油田（或跨区块／跨层系）须分源列明每条结论归属（油田名↔数值／结论配对），「某区块」形禁现；无据归属不得进答案面 |
| specs/answering.md:93 | 不降级与静默禁令 机读信号 | 流式增量／缺口／截断披露／收口必产机读信号：本块自产 `text`／`citation` 事件＋ `material_truncated` notice ＋ step payload 的 `citations`／`gaps` 字段；`verdict` 为消费方信号（批次落定归 `orchestration`） |
| specs/answering.md:94 | 不降级与静默禁令 红线原文 | 红线原文 `arch/P7a-交接包与挂账清单.md`（A-P7a-37）「**不许静默**——若任何相位仍发生截断，模型面必须随材料段带明示……收口注记面同步披露」 |
| specs/answering.md:118 | 行 19 零语义判断 | AST 扫描：无语义词表／正则（豁免面＝形态处理／集合成员判定） |
| specs/answering.md:120 | 行 21 边界集 | 单段答案／零材料／矛盾双源／坏引标四形各落对应分支 |
| specs/answering.md:121 | 行 22 保留集 | 无矛盾、无缺口的普通答案：引标与分源行为不变 |

结构锚：specs/answering.md:37–:60 接口定义（形状真源＝-06a 已落地的五形状，本票只加行为、不改形状）；:90–:94 不降级与静默禁令（**合法降级路径＝无**——起草原话不完整时走结构化缺口，不改写事实）；:96–:121 验收测试表（`#` 行序与 -06a 共用）。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单（本块无明写归块行；唯一关联行已在 -06a 同节逐字转抄）〕

- 归块注（呈主窗对账）：§三 表内**无一行明写「对应 runtimev2 `answering`」**；全块唯一关联行＝ B5「帧协议级时序（step/text/ask/verdict/done/error 序与 data 形）｜从 `eval/results/frames/` 真帧流转离线 golden 回放钉｜中」，该行已在 `RT-W4-06a-answering.md`「织网义务」节**原文照抄**，本票不重复转抄（同一行两处转抄＝两处真源必漂移，逐字稿纪律）。
- 本票在该行的义务面（关系注，非新钉）：B5 的 `text`／`citation` 帧序与 notice 的 data 形，其**降级／披露半面**（`material_truncated` notice 在场、截断与未渲染部分的不作答声明）由本票行 13／20 承载；钉法真源＝`eval/results/frames/` 真帧流转离线 golden 回放钉。
- 关联行（已他归）：B1（公共位与结果归一：`_step_record`／`_next_seq`／`_converge` 等 16 个全节点共用符号）明写归 `bookkeeping`（`RT-W3-01a/b/c-bookkeeping.md` 承接），本块只经 `bookkeeping.call_model` 与 step payload 消费其记账面，不另立钉。
- 本票织网义务＝① B5 关联行的 L3 回放钉（织网工序第 3 步「盲区补钉」，与 W1–W4 施工可并行——eng/04 头注）；②「测试网钉」6 行对应用例落网；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」12 行逐行实现为 `tests/domains/test_v2_answering.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行；`#` 保留规格表行序 7、12–22）；
- 「测试网钉」6 行对应用例在场且绿（pin-03／pin-08 为 P0 承重钉；pin-09／pin-13／pin-19／pin-20 为 P1）；
- AST 红线断言绿：`::no_lexicon_or_regex_in_answering`（语义词表／正则零出现，豁免面按规格原文）；
- 机读信号在场（行 20）＋ 交付面与执行侧同规则（行 12 与 `RT-W4-05a-execution.md` 行 4 口径一致）；
- 边界闸 R1／R2／R5b／R6／R7 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；
- 形状单点：五形状仍以 -06a 落地的为唯一真源，本票不改形状（改形状＝回 -06a 或回设计仓）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W4-06b 完成，产物 `appv2/runtimev2/answering/`（降级与引用簇），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
