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


