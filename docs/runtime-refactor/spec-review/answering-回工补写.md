# answering 规格回工补写（2026-10-15）

- 依据：独立复审判 `specs/answering.md` **FAIL（两个 P0 真空）**——回工令必修 1–5（下表记为复审发现 R1–R5，编号对应回工令必修序号）。
- 范围：只改 `specs/answering.md`（本文件是修改点台账）；不碰 `specs/agent-loop.md`（另一窗口施工中）。
- 施工纪律：行为约定每条可写成 pytest 断言；数字只引真源；阈值类数值标「阶段 5 待定」但行为归属与披露义务定死；pin-08 交叉面规则与 `specs/execution.md` 行为 4 **逐字一致**（已机比 538 字节相同）。
- 闸验证：`uv run python tools/check_specs.py`＝**PASS（0 警告）**；`uv run python tools/ref_resolvable.py check`＝**绿（13 份规格可解析）**。

## 修改点清单

| # | 落点 file:line | 一句话 | 依据复审发现 |
|---|---|---|---|
| 1 | `specs/answering.md:81`（行为约定 11「发射剥离」新增） | 模型应答进答案面（`AnswerDraft` 片段与 `text` 帧增量）前经发射围栏／JSON 形**确定性剥离**——发射 JSON 不得进答案面（泄漏=0）；真源 `eval/results/Q15-对账报告.md`:38（Q14 6 题→0、V2-48 兑现）＋旧码 `docs/runtime-refactor/recon/L2b-作答装配与回声.md`:58/:101（`strip_emission_fences`） | R1【P0】pin-04 真空 |
| 2 | `specs/answering.md:82`（行为约定 12「行集题交付与落引用界线」新增） | 行集题（明细行集类）全量交付为默认、丢行=0；非行集大结果超阈才落引用＋截断/落引用必披露；阈值数值阶段 5 待定、行为归属与披露义务定死；真源 `tickets/v2/V2-61-材料承载分形渲染.md`:5；与 `specs/execution.md` 行为 4 互指「同一规则、逐字一致」 | R2【P0】pin-08 真空＋与 execution 交叉面 |
| 3 | `specs/answering.md:83`（行为约定 13「占位符不进答案面」新增） | 答案面不得出现字面占位引标 `[n]`、含 `[n]` 行不得以占位符交付；真源 `eval/results/Q16-判分报告-G3.md`:56（D-诱15 形）＋`tickets/v2/V2-69-坏引标修复.md` | R5【P2】pin-10 后半 |
| 4 | `specs/answering.md:84`（行为约定 14「起草回声＝0」新增） | 草稿首行不以「理解：」开头、前 100 字不含「指标候选」（`echo_flag` 恒 0，观测字段只记不拦）；真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-61＋`eval/results/Q16-对账报告.md`:61 | R3【P1】pin-13 按行为语义挂（钉落需要行为锚点，故补行为条目） |
| 5 | `specs/answering.md:89`（不降级与静默禁令·机读信号行重写） | 机读信号清单收窄为**本块自产** `text`／`citation` 事件＋`material_truncated` notice（真源 V2-61 附 D）；`verdict` 事件改标**消费方信号**（批次落定归 `orchestration`，见行为 7）——与行为 7（`:77`）的「本块只保证自产部分」统一为一种说法 | R4【P2】块内两说（:77 vs 旧:85） |
| 6 | `specs/answering.md:106-110`（验收测试表新增 5 行） | `emission_strip_zero_leak`／`rowset_full_delivery`／`truncation_disclosed`／`placeholder_marker_not_in_answer`／`echo_flag_zero` 五个测试标识绑定（阶段 5 承诺，行为 11–14＋pin-09 信号在场断言） | R1/R2/R3/R5 配套验收 |
| 7 | `specs/answering.md:112`（验收表「answering_signal_present」行措辞改写） | 信号在场判据同步改为 text／citation 帧＋material_truncated notice＋step payload，verdict 标消费方信号——消除与不降级节的残留两说 | R4【P2】块内两说收尾 |
| 8 | `specs/answering.md:139-142`（挂钩表新增 4 行钉登记） | pin-04（P0）／pin-08（P0）／pin-09（P1）／pin-13（P1）按行为语义挂，格式照 `specs/agent-loop.md` 挂钩表钉行同款（钉 **`pin-NN`**（P级）｜待织网（阶段 5）） | R3【P1】挂钩表补登记 |
| 9 | `specs/answering.md:143`（挂钩表新增迁移建议行） | 「迁移建议：pin-07/20 归 clarification，待主窗核定」——不硬挂：pin-07 定稿打回带路（finalize 属 clarification 四动作闭世界）、pin-20 台账 no_hit 降级链横跨探查与交付，归属证据不足，留主窗核定 | R3【P1】pin-07/20 处置 |

## pin-08 交叉面规则的最终表述（本规格落点原文）

`specs/answering.md:82`（行为 12）——与 `specs/execution.md:81`（行为 4）冒号后**逐字一致**：

> 行集题（明细行集类：问句要求明细／排名／列举全行集）全量交付为默认——引擎返回的全部数据行逐行交付、丢行＝0；非行集大结果超阈才落引用（窗口只留摘要＋稳定引用＋行数），截断与落引用必披露。阈值数值阶段 5 待定（随真机数据定），行为归属与披露义务即此定死：行集题不得因落引用而丢行。真源：`tickets/v2/V2-61-材料承载分形渲染.md`（:5——24 支一刀切截断废除、改分承载体渲染）。

## 遗留与移交

1. **pin-07/20 归属**：已按迁移建议行登记（`specs/answering.md:143`），待主窗核定——核定后若归 clarification，由 clarification 规格补挂；若判归本块，再补行为条目。
2. **pin-10 前半**（引标必须对应窗内切片、不得 cited=[] 且数字在场）：现有行为 2＋`segment_citations_resolve`／`dangling_citation_rejected` 验收已覆盖引标解析面；「cited=[] 且数字在场」的判分面在 verification 侧（verdict 支撑对账），本批未动（回工令未要求）。
3. **分承载体渲染的装配面**（装配器对行集不再重复封顶）在旧码属 context 装配器（V2-61 附 A）；新架构归属 `context` 块规格，本规格只钉答案交付面——两规格的共享规则已把「行集题不落引用」定为系统界线。
4. 新增测试标识（`:106-110`）均为阶段 5 承诺，`test_v2_answering.py` 尚不存在——与既有 14 行同状态。

---

## 追加记录：pin-20 落块（2026-10-15，主窗已核定）

主窗核定：`eng/04a` **pin-20**（P1，台账 no_hit 降级链）**归本块**（降级交付的如实阐述面）——上一节遗留 1 对 pin-20 的「待核定」就此关闭；pin-07 与本科无关（迁移建议行整体撤销，归属由主窗另行处置）。本轮只改 `specs/answering.md` ＋ 本台账，未 commit。

| # | 落点 file:line | 一句话 | 依据 |
|---|---|---|---|
| 10 | `specs/answering.md:85`（行为约定 15「台账 no_hit 降级交付三段形」新增） | 台账 no_hit（agg 未落列 notice 在场）时降级交付**三段齐**：①油田级邻近可得量带引用交付 ②逐井「未找到」明示 ③指路；且**零逐井数值冒充**——可写成 assert（no_hit 态下三段在场＋逐井数值为零）；真源 `eval/results/Q16-判分报告-G1.md`:39（数-降2 判语「油田级 8.10 万吨邻近可得引用＋逐井明细未找到明示＋指路，零逐井数值——轴第 4 条满分形」）＋`eval/README.md`（「判分轴统一登记」第 4 条——引擎降级解释＋如实标注＝✅ 满分，诚实转述也是正确交付，封尺口径） | 主窗核定 pin-20 归本块（补充任务①） |
| 11 | `specs/answering.md:112`（验收表新增 1 行） | 「台账 no_hit → 降级交付三段形（油田级邻近可得引用＋逐井『未找到』明示＋指路）且零逐井数值冒充」→ `tests/domains/test_v2_answering.py::no_hit_degraded_delivery_three_part`（阶段 5 承诺） | 补充任务② |
| 12 | `specs/answering.md:145`（挂钩表迁移建议行→pin-20 正式登记） | 删除「迁移建议：pin-07/20 归 clarification，待主窗核定」整行，改为钉行：「台账 no_hit 降级交付三段形（…轴④封尺满分形）——落点＝行为 15｜钉 **`pin-20`**（P1）｜待织网（阶段 5）」——格式与其余钉行同款 | 补充任务③（pin-07 与本科无关，不再出现在本表） |

**验证（2026-10-15）**：`uv run python tools/check_specs.py`＝**PASS（0 警告）**；`uv run python tools/ref_resolvable.py check`＝**绿（14 份规格可解析，含新增真源 `Q16-判分报告-G1.md`／`eval/README.md`）**。本规格现登记钉：pin-04/08/09/13/20 共 5 根（另 pin-10 行为/验收落点已备、钉登记随织网统筹）。

---

## 追加记录：pin-19 落块（2026-10-15，主窗已核定）

主窗核定：`eng/04a` **pin-19**（P1，排名型子问题答案强制消费排名观察支——两井对序对）**归本块**（答案消费面的支支配）。本轮只改 `specs/answering.md` ＋ 本台账，未 commit。**真源行号勘正**：`eng/04a` pin-19 来源列标 `P4a2-票堆V2-51至55.md:23`，实际规则原文在 **:24**（A-P4a2-04；:23 是 A-P4a2-03 时间词条）——本规格按 :24 引。

| # | 落点 file:line | 一句话 | 依据 |
|---|---|---|---|
| 13 | `specs/answering.md:86`（行为约定 16「排名型子问题强制消费排名观察支」新增） | 排名型子问题（问句求排名／排序序）的答案必须从**排名观察支**取值——交付的排名序对（对象↔名次／值）须与排名观察支的序信息一致，**不得弃排名支、以他支拼排名**——可写成 assert（答案排名序对＝排名支序对，弃支他拼即失败）；真源 `docs/runtime-refactor/arch/P4a2-票堆V2-51至55.md`:24（A-P4a2-04「排名型子问题答案强制消费排名观察支（数-排2 形，帧证 obs[52]/[53] 曾弃）」） | 主窗核定 pin-19 归本块（补充任务①） |
| 14 | `specs/answering.md:113`（验收表新增 1 行） | 「排名型子问题答案消费排名观察支（排名序对与排名支序信息一致，不弃支他拼）」→ `tests/domains/test_v2_answering.py::ranking_answer_consumes_ranking_obs`（阶段 5 承诺，标识格式照既有行） | 补充任务② |
| 15 | `specs/answering.md:148`（挂钩表新增 pin-19 正式钉行） | 「排名型子问题强制消费排名观察支（排名序对与排名支序信息一致，不弃支他拼）——落点＝行为 16｜钉 **`pin-19`**（P1）｜待织网（阶段 5）」——格式与其余钉行同款 | 补充任务③ |

**验证（2026-10-15）**：`uv run python tools/check_specs.py`＝**PASS（0 警告）**；`uv run python tools/ref_resolvable.py check`＝**绿（14 份规格可解析）**。本规格现登记钉：pin-04/08/09/13/19/20 共 6 根（另 pin-10 行为/验收落点已备、钉登记随织网统筹）。




---

## V1 发起面回改（主窗裁 doctrine）——2026-10-15

- **依据**：复审⑦处置（`docs/runtime-refactor/00-决议与方法.md` 流水 27 第①裁）——相位调模型一律经 `bookkeeping.call_model`（其内部唯一出口 `appv2.runtimev2.gateway_adapter`）。本次只改 `specs/answering.md`（149→150 行）＋本记录，其它文件未动；未 git commit（主窗统一提交）。
- **修改点**（行号指改后文件）：
  1. 「触及的模块」依赖表（:30-32）：新增 `bookkeeping` 行（改动类型＝**新增依赖**；说明＝「模型调用发起面：经 bookkeeping.call_model（单点发起），本块不直引 gateway_adapter」）；同表 `gateway_adapter` 行说明由「模型调用唯一出口（本块只消费）」改为「模型出口（唯一出口仍归它）；本块不直引——经 bookkeeping.call_model 发起」。
  2. 「框架与依赖红线」（:65）：「模型调用唯一出口＝gateway_adapter」改为「**模型调用发起面＝`bookkeeping.call_model`（单点发起）；其内部唯一出口＝`gateway_adapter`**」，补「import 落点＝`appv2.runtimev2.bookkeeping` 包根——R2 禁深层子模块」；R7 括注改准为「禁直引 `appv2.infra.llm_client`——模型出口仍唯一归 `gateway_adapter`」；验收写法改为「模型调用发起点只出现在 `bookkeeping.call_model` ＋ 调用行为测试绿」，并注「发起面收敛为规格层 doctrine，不设闸——主窗 2026-10-15 裁」。
  3. 「框架与依赖红线」禁手写替代条（:68)：R7 括注由「runtimev2 各块只经 `gateway_adapter` 调模型」改为「模型出口唯一归 `gateway_adapter`——发起经 `bookkeeping.call_model`」；「无旁路」断言对象同步改为发起点。
  4. 「依赖与风险」依赖行（:123)：补 `bookkeeping`（模型调用发起面——`call_model` 单点发起）；`gateway_adapter` 括注改为「经 `call_model` 的内部唯一出口，本块不直引」。
  5. 「与闸的挂钩表」（:136)：「模型调用只经 `gateway_adapter`」行改为「模型调用经 `bookkeeping.call_model` 发起（单点发起；其内部唯一出口 `gateway_adapter`）」；挂钩列注「出口面 R7；发起面为规格层 doctrine，不设闸」；现状列不变。
- **不加闸（裁定照录）**：importlinter 边界闸**不随本批加**——R7「只经出口」＋R8 语义不变，doctrine 是规格层不是闸层（主窗 2026-10-15 裁）。
- **契约字面核对（未改 toml）**：逐条实读 `tools/importlinter_v2.toml`——R7（forbidden＝`appv2.infra.llm_client`；source 含 `appv2.runtimev2.bookkeeping`）与 R2（业务相位 forbidden 含 `appv2.runtimev2.bookkeeping.*` 深层子模块、不含包根）均与新 doctrine **无字面冲突**。实现期注意：相位 import 只许 `appv2.runtimev2.bookkeeping` 包根（R2 面）。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（20 份规格）**。均 exit 0（批次一改后实跑）。

---

## 流水 30③ 后续：pin-03 落 answering（主窗裁）——2026-10-16

主窗裁决：`eng/04a` **pin-03**（P0 golden，跨油田题交付必须分源列明油田归属、不得框成「某区块」不认归属——C-正6 形禁现）**落本块**（交付面正主）——窗 B 评审 P-05 指出的「该钉三处登记（`specs/prompts.md` 行为 2 ③承接注记＋挂钩表 :161、`specs/verification.md:141` 备查登记）无一处落验收行」就此闭合。同批修窗 B 点名的 P-11 措辞（`specs/prompts.md` 风险 7③ 登记件的销项面）。本轮只改 `specs/answering.md` ＋ 本台账，未 commit。

| # | 落点 file:line | 一句话 | 依据 |
|---|---|---|---|
| 16 | `specs/answering.md:88`（行为约定 17「跨油田题分源列明油田归属」新增） | 交付面涉**多油田**（或跨区块／跨层系）的题答案必须**分源列明每条结论的归属**（油田名↔数值／结论配对），不得框成「某区块／小范围结算序列」等含糊归属（C-正6 形禁现）；**无据归属不得进答案面**（与行为 3「无据的话不写进答案」同族——`eng/04a` 族面＝pin-02「无据差值/无据口径框架」）；合同侧承接＝prompts 答案要求③（多来源逐个来源分别作答）——可写成 assert（多油田 fixture 下答案面归属配对在场＋「某区块」形零命中）；真源 `eval/results/Q16-判分报告-G3.md`:32（C-正6 判语逐字引）＋`eval/results/Q15-对账报告.md`:167（族 C attribution_split 分源列明块帧证）＋`docs/runtime-refactor/eng/04a-应钉行为清单.md` pin-03（P0 golden） | 主窗裁 pin-03 落 answering（补充任务①） |
| 17 | `specs/answering.md:117`（验收表新增 1 行） | 「多油田题答案面分源列明归属配对（油田名↔数值／结论）在场＋『某区块』含糊归属形零命中」→ `tests/domains/test_v2_answering.py::cross_oilfield_attribution_paired`（阶段 5 承诺，标识格式照既有行） | 补充任务② |
| 18 | `specs/answering.md:152`（挂钩表新增 pin-03 正式钉行） | 「跨油田题分源列明油田归属（油田名↔数值／结论配对；『某区块』含糊归属形禁现——C-正6 形）——落点＝行为 17｜钉 **`pin-03`**（P0）｜待织网（阶段 5）」——格式与其余钉行同款 | 补充任务③ |
| 19 | `specs/answering.md:29`（触及的模块 prompts 行措辞改述） | 「答案轮的指令与材料装配文本（只出文本）」→「答案轮指令装配文本（只出文本；材料段不在装配输出内——材料渲染归 context，本块材料渲染＝消费 context 编译产物、零自取，与 specs/context.md 定界互认）」——消 P-11 两说（对齐 `specs/prompts.md` 行为 12 材料零渗入定界） | 窗 B 点名 P-11（补充任务④，主窗裁口径） |

**真源行号勘正**：`eng/04a` pin-03 来源列标 `Q16-判分报告-G3.md:31`，C-正6 判语实落 **:32**（:31 是 C-正5 行）——本规格按 :32 引（同 pin-19 勘正先例；`eng/04a` 侧勘正待 eng/ 文件随批治理，本批不动 eng/）。

**遗留移交**：① `specs/prompts.md:161` 的「其挂钩表现无 pin-03 行——跨规格债登记交主窗」表述自本批起过时——prompts 侧回提句随其块下批修订对账（单写者纪律，本批不动他块文件）；`specs/verification.md:141` 备查登记照旧（verify 侧无独立落点，答案交付面现落本块行为 17）。② 新增测试标识 `cross_oilfield_attribution_paired` 为阶段 5 承诺，`tests/domains/test_v2_answering.py` 尚不存在——与既有行同状态。

**验证（2026-10-16）**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（22 份规格）**。均 exit 0（本批改后实跑）。本规格现登记钉：pin-03/04/08/09/13/19/20 共 7 根（另 pin-10 行为/验收落点已备、钉登记随织网统筹）。
