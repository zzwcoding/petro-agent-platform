# RT-W3-01b · bookkeeping——V2 公共簿记（-B：触界收敛与收口簇）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/bookkeeping.md`（状态「已定稿」——前置满足）
Touches modules: `bookkeeping`（本票只填 bookkeeping 的触界收敛与收口簇，共享写口九函数与形状以 -01a 落地的为唯一真源；规格「触及的模块」表另声明 state／gateway_adapter／tools／persistence／transport 五关联侧，归各自票承接）
波次: W3（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W3 行：组合件，依赖 W2 的 gateway_adapter——「bookkeeping 单写口是相位开发的共同依赖」；本波出口判据「每模型调用有 Manifest；写口无旁路（AST＋import 双证）；两道闸机械分派」）
施工队: B 队（eng/03 §五 终表 W3 行 B 队列＝「bookkeeping」，分配理由整行原文「唯一写口＝旁路慢漏，AST 双证要写到位」；已按 eng/03 §五 终表对齐；提交前缀＝[B]——eng/03 §五 扣件①）｜复审强度: 100%（主窗裁：B 队施工≠免复审——本票维持 100% 过独立复审，复审网在 L0 直派；eng/03 §五 B 队标准为抽 50%，本票按主窗裁提高）
前置: ① 规格定稿（`specs/bookkeeping.md` 已定稿——已满足）；② **`RT-W3-01a-bookkeeping.md` 收票**（同包顺序施工、同包不并行——共享写口九函数、收敛与收口签名以 -01a 为唯一真源）；③ 波次前置：**W2 全收波**（经 -01a 传递，已满足；eng/03 §一依赖图：bookkeeping → gateway_adapter ＋ state；W2 的 gateway_adapter 测试替身是后续所有相位测试的地基）
阻塞: `RT-W3-01a-bookkeeping.md`（-01b 前置＝-01a 收票）｜被阻塞: `RT-W3-01c-bookkeeping.md`（-01c 前置＝-01b 收票）；W4 七个业务相位（本块是全节点共享唯一写面——相位开发的共同依赖）

## 任务

接 `RT-W3-01a-bookkeeping.md` 落地的骨架与共享写口，填 `appv2/runtimev2/bookkeeping/` 的**触界收敛与收口簇**：`converge(state)` 命中落六键、未命中零副作用、已收敛再调无操作；收敛正文材料与通知未完成项清单**同一材料面**（不漂移）；`direct_answer` 完成收口旁路恒写三键（拒答／闸拒／收敛转答／直答共用同一出口）；`call_model` 调模型单点——只回 `content`、用量与归因面照记步记录与 Manifest（禁裸文本吞掉记账面）。

**本票＝bookkeeping 的 -B 票**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **23 行**，超 15 行上限 → 切 -A／-B／-C 三票。本票收 **5 行**＝规格表第 13–17 行（触界收敛六键／收敛幂等／收敛材料同源／直答旁路三键／调模型记账）；其余 18 行与**本块 5 条 pin 行**（pin-22 写入点单点面归属行／pin-22／pin-24／pin-26／pin-12）全在 -01a，本票**零 pin 行**、不重复转抄。三票同包**顺序施工**（同包不并行）：本票只填行为、**不改 -01a 落地的形状**（共享写口九函数＋收敛与收口签名——改形状＝回 -01a 或回设计仓）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/bookkeeping.md` 全文（十节版式，含行为 12–15 的六键清单与收口三键原文）；`specs/modules.md` `## bookkeeping` 卡（签名以卡为准）；`specs/state.md`（`check_limits` 判定面与 `budget_hit`／`next_intent` 字段面——收敛判定归 state，本块只落地）；`specs/gateway_adapter.md`（`complete` 与 `ModelReply` 十字段——`call_model` 的记账字段来源）；`specs/persistence.md`（`StepRecord` 形状——记账落点）；`specs/transport.md`（`NOTICE_TYPES`——收敛通知的分型闭世界）。eng/04 §三 B1／B3 两行的转抄与指针见「织网义务」节，施工期不必另开。

**小票制自检（流水 48）**：票面对象 5 行 ≤ 15 ✓；先读 6 份 ≤ 6 ✓；聚焦一个行为簇＝收口单链（触界判定结果→落地六键→幂等与同源→收口旁路三键／调模型记账）✓ → 本票不派生。

框架红线: 无点名框架（`_MESSAGE_CLS` 一类 role→框架消息类映射含框架类型，只许活在 `orchestration`——本块只做文本层 `append_message(role, content)`）——对应闸 R5b 契约
边界红线: ① 不直引模型出口（模型只经 `gateway_adapter`）——R7；② 不直引引擎（R6）；③ 运行逻辑只依赖两处（`state` 形状／判定＋`gateway_adapter` 模型出口），类型与常量形状另引三处（`tools` 的 `ToolContext`／`persistence` 的 `StepRecord`／`transport` 的 `NOTICE_TYPES`）且**只许引类型与常量、不许引其行为**——无专属闸→人审＋AST 断言「import 只出现这五块」登记待补；④ 不落盘（本块不写库、不写文件——落盘归 `persistence`）；⑤ 禁手写替代：不得绕过写口直改状态字段（相位侧同禁——测试 `::no_direct_state_write_in_phases`）

## 票面对象（specs/bookkeeping.md「验收测试」表逐行转抄——本票 5 行：规格表第 13–17 行）

〔来源：specs/bookkeeping.md「验收测试」表 :138–:142，逐行原文；`#` 列＝规格表行序（与 -01a／-01c 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 13 | 触界收敛落地六键；未命中零副作用 | `tests/domains/test_v2_bookkeeping.py::converge_lands_six_keys` | specs/bookkeeping.md:138 |
| 14 | 收敛幂等（二次调用不重复追加／不覆盖） | `tests/domains/test_v2_bookkeeping.py::converge_idempotent` | specs/bookkeeping.md:139 |
| 15 | 收敛答案与通知材料面同源（不漂移） | `tests/domains/test_v2_bookkeeping.py::converge_material_same_source` | specs/bookkeeping.md:140 |
| 16 | 直答旁路恒写三键 | `tests/domains/test_v2_bookkeeping.py::direct_answer_three_keys` | specs/bookkeeping.md:141 |
| 17 | 调模型单点：只回 `content`，用量/归因落记账 | `tests/domains/test_v2_bookkeeping.py::call_model_keeps_accounting` | specs/bookkeeping.md:142 |

> 测试文件归属（票注，非规格引文）：本票 5 行与 -01a／-01c 同落**同一个新建文件** `tests/domains/test_v2_bookkeeping.py`（spec :150 节尾原注已在 `RT-W3-01a-bookkeeping.md` 同节照抄，本票不重复转抄，防两处漂移）；旧码测试本批不改。
> 行序缺口说明（票注）：本票行序跳过 1–12、18–23——`#` 列三票共用规格表行序，便于 manifest 逐行对账。

## 测试网钉（本块 5 条 pin 行已在 `RT-W3-01a-bookkeeping.md` 同节全量逐字转抄——本票零 pin 行，不重复转抄）

- 核对关系（防两处漂移）：pin-22 写入点单点面 ↔ 行 1／2、pin-22 写入面 ↔ 行 7、pin-24 写入面 ↔ 行 8／9、pin-26 写入面 ↔ 行 10、pin-12 承接面 ↔ 行 5——五条钉的逐字转抄与机检用例全在 -01a；本票 5 行不承载任何 pin 行。
- 分工注（防两头认）：本票行 16（直答旁路恒写三键）与行 17（调模型单点）产出的账目仍走 -01a 落地的写口与 `StepRecord` 形状——**形状与写口真源在 -01a**，本票只填行为。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 pin 行只落 -01a 一处（先例 `RT-W4-05b-execution.md` 分票理由原文）。

## 施工要点（specs/bookkeeping.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/bookkeeping.md:107 | 行为 12 触界收敛落地（幂等） | `converge(state)` 先调 `state.check_limits`（判定归 `state`）；**命中** → 落地六键（`budget_hit` 追加命中项／通知追加如实注记／答案正文＝已取得材料逐条如实交付／`draft_kind="direct"`／`status="completed"`／`next_intent=answer`）；**未命中** → **零副作用**；**幂等**：已收敛（`budget_hit` 非空）再调 → **无操作** |
| specs/bookkeeping.md:108 | 行为 13 收敛答案与通知材料面同源 | 收敛交付的正文材料与通知里的未完成项清单**取自同一材料面**（不存在两处漂移：答案说交付了 X、通知说未完成 X） |
| specs/bookkeeping.md:109 | 行为 14 完成收口旁路单点 | `direct_answer(state, text)` 恒写三键（`draft=text`／`draft_kind="direct"`／`next_intent=answer`）——拒答、闸拒、收敛转答、直答共用**同一出口**（免起草免核验） |
| specs/bookkeeping.md:110 | 行为 15 调模型单点（桥接） | `call_model(state, caller, messages)` 从状态取 `run_id` → 调 `gateway_adapter.complete` → **向节点只回 `content`**；**回执的用量与归因面（token／`cached_tokens`／`alias`／时长／`caller`／`run_id`）由本块记进步记录与 Manifest**——**禁裸文本吞掉记账面**（真源 `specs/gateway_adapter.md` 行为 1） |

结构锚：specs/bookkeeping.md:52 接口定义（收敛与收口签名——**形状真源＝-01a 已落地的**，本票只加行为、不改形状）；:85–92 框架与依赖红线（不直引模型出口／引擎；类型与常量只许引形状五块）；:115–120 不降级与静默禁令（**触界不静默**：注记必落且正文如实交付已取得材料——红线 `docs/runtime-refactor/arch/P7a-交接包与挂账清单.md`（A-P7a-37「不许静默」）；**记账不丢**；**不许自述完成**——完成由程序侧判定（`state.check_limits` 与核验结论），本块只**落地**它给的结论（行为 12／14））。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三——B3 关联半行＋B1 指针）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单（B1 明写归本块的行逐字转抄落 `RT-W3-01a-bookkeeping.md`；本票承接其收敛半面的关联行）〕

- 关联行（B3「每限额上限/触顶收敛行为钉」，**写明、不重复转抄**）：B3 中「触顶收敛**落地**」半行＝本块的 `converge`（行为 12，本票行 13／14／15）；**键集与数值半行**归 `state`；该关联半行的转抄与承接已在 **`RT-W1-01b-state.md`**（state 包 -B 票，其「织网义务」节承载 B3 行逐字转抄）落定——本票不重复转抄、不冒充覆盖，切分呈主窗对账。
- B1（公共位与结果归一，明写归 `bookkeeping`，严重度「高」）的逐字转抄与《写口侧观测面》义务落 `RT-W3-01a-bookkeeping.md` 同节（指针，防两处真源漂移）；本票行 13–17 是该钉「每步通道值归一形」在**收口步**的输入面。
- L2 新规格钉随本票施工 TDD 生长（eng/04 §五：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。
- 本票织网义务＝① B3 触顶收敛落地半行的 L1 特征钉（钉法＝「每限额上限/触顶收敛行为钉（数值只引预算表）」——数值不在本票；织网工序第 3 步「盲区补钉」，与 W1–W3 施工可并行——eng/04 头注）；② 本票 5 行对应用例落网；③ L2 新规格钉随施工 TDD 生长。

验收: 以下判据逐条全绿为过——
- 「票面对象」5 行逐行实现为 `tests/domains/test_v2_bookkeeping.py` 用例并全绿，测试标识与规格列逐字一致（`#` 保留规格表行序 13–17）；
- 「测试网钉」零 pin 行——本票只写归属指针，不重复转抄（5 行全在 -01a）；
- 收敛三面断言绿：六键落地＋未命中零副作用（行 13）／二次调用幂等不重复追加不覆盖（行 14）／正文材料与通知未完成项同源（行 15）；
- 收口两面断言绿：直答旁路恒写三键（行 16，拒答／闸拒／收敛转答／直答同一出口）／调模型单点只回 `content` 且用量归因落记账（行 17，**禁裸文本吞掉记账面**）；
- 判定与落地分界绿：触界**判定**归 `state.check_limits`（本票不复制其判据与数值）、本块只落地结论；**合法降级路径＝无**（本票不得引入任何静默兜底分支）；
- 形状单点：共享写口九函数／收敛与收口签名仍以 -01a 落地的为唯一真源，本票不改形状（改形状＝回 -01a 或回设计仓）；
- 边界闸 R5b／R6／R7 在 `lint-imports` 双配置下绿；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W3-01b 完成，产物 `appv2/runtimev2/bookkeeping/`（触界收敛与收口簇），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
