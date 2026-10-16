# RT-W3-01c · bookkeeping——V2 公共簿记（-C：装配与归一＋元面＋边界·保留集，收尾票）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/bookkeeping.md`（状态「已定稿」——前置满足）
Touches modules: `bookkeeping`（本票只填 bookkeeping 的装配与归一簇、元面与边界·保留收口行，共享写口九函数与形状以 -01a 落地的为唯一真源；规格「触及的模块」表另声明 state／gateway_adapter／tools／persistence／transport 五关联侧，归各自票承接）
波次: W3（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W3 行：组合件，依赖 W2 的 gateway_adapter——「bookkeeping 单写口是相位开发的共同依赖」；本波出口判据「每模型调用有 Manifest；写口无旁路（AST＋import 双证）；两道闸机械分派」）
施工队: B 队（eng/03 §五 终表 W3 行 B 队列＝「bookkeeping」，分配理由整行原文「唯一写口＝旁路慢漏，AST 双证要写到位」；已按 eng/03 §五 终表对齐；提交前缀＝[B]——eng/03 §五 扣件①）｜复审强度: 100%（主窗裁：B 队施工≠免复审——本票维持 100% 过独立复审，复审网在 L0 直派；eng/03 §五 B 队标准为抽 50%，本票按主窗裁提高）
前置: ① 规格定稿（`specs/bookkeeping.md` 已定稿——已满足）；② **`RT-W3-01b-bookkeeping.md` 收票**（同包顺序施工、同包不并行——全块写口与收口面已由 -01a／-01b 落地，本票只补装配与归一／元面／边界·保留收口）；③ 波次前置：**W2 全收波**（经 -01a／-01b 传递，已满足；eng/03 §一依赖图：bookkeeping → gateway_adapter ＋ state；W2 的 gateway_adapter 测试替身是后续所有相位测试的地基）
阻塞: `RT-W3-01b-bookkeeping.md`（-01c 前置＝-01b 收票）｜被阻塞: W4 七个业务相位（本块是全节点共享唯一写面——相位开发的共同依赖）

## 任务

接 `RT-W3-01a-bookkeeping.md`／`RT-W3-01b-bookkeeping.md` 落地的骨架与收口面，把**装配与归一**做实：`note` 写入点截断且只追加（有界）、`notice` 恰三键＋`type`／`gates` 闭世界、`tool_context` 身份只从状态取／放行态随上下文／送窗预算按子问题数、`result_projection` 逐字段原样投影（空值与缺省读回可区分）；外加本块零判断的 AST 元面与【边界集】／【保留集】两行。

**本票＝bookkeeping 的 -C 票（收尾票）**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **23 行**，超 15 行上限 → 切 -A／-B／-C 三票。本票收 **剩余 7 行**＝规格表第 11、12、18、19、21、22、23 行（`note` 有界只追加／通知三键闭世界／工具上下文装配／结果投影原样／零判断元面／【边界集】／【保留集】）；其余 16 行与**本块 5 条 pin 行**（pin-22 写入点单点面归属行／pin-22／pin-24／pin-26／pin-12）分别在 -01a／-01b，本票**零 pin 行**、不重复转抄。三票同包**顺序施工**（同包不并行）：本票只填行为与收口断言，**不改 -01a／-01b 落地的形状**（改形状＝回 -01a 或回设计仓）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （5 份）`specs/bookkeeping.md` 全文（十节版式，含行为 10／11／16／17 的字段面与截断口径原文）；`specs/modules.md` `## bookkeeping` 卡（签名以卡为准）；`specs/state.md`（`process_notes` 投影面与常量族——`note` 投影来源）；`specs/transport.md`（`NOTICE_TYPES`——通知分型闭世界）；`docs/runtime-refactor/recon/B1-公共位与结果归一.md`（十六项公共位真源——行 19 结果归一投影的旧码对照面）。eng/04 §三 B1 行的逐字转抄在 `RT-W3-01a-bookkeeping.md` 同节，施工期不必另开。

**小票制自检（流水 48）**：票面对象 7 行 ≤ 15 ✓；先读 5 份 ≤ 6 ✓；聚焦一个行为簇＝投影与归一收口（`note` 有界→`notice` 闭世界→工具上下文装配→结果投影原样→元面与边界·保留）✓ → 本票不派生。

框架红线: 无点名框架（`_MESSAGE_CLS` 一类 role→框架消息类映射含框架类型，只许活在 `orchestration`——本块只做文本层 `append_message(role, content)`）——对应闸 R5b 契约
边界红线: ① 不直引模型出口（模型只经 `gateway_adapter`）——R7；② 不直引引擎（R6）；③ 运行逻辑只依赖两处（`state` 形状／判定＋`gateway_adapter` 模型出口），类型与常量形状另引三处（`tools` 的 `ToolContext`／`persistence` 的 `StepRecord`／`transport` 的 `NOTICE_TYPES`）且**只许引类型与常量、不许引其行为**——无专属闸→人审＋AST 断言「import 只出现这五块」登记待补；④ 不落盘（本块不写库、不写文件——落盘归 `persistence`）；⑤ 禁手写替代：不得绕过写口直改状态字段（相位侧同禁——测试 `::no_direct_state_write_in_phases`）

## 票面对象（specs/bookkeeping.md「验收测试」表逐行转抄——本票 7 行：规格表第 11、12、18、19、21、22、23 行）

〔来源：specs/bookkeeping.md「验收测试」表 :136–:137、:143–:144、:146–:148，逐行原文；`#` 列＝规格表行序（与 -01a／-01b 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 11 | 过程档案 `note` 写入点截断且只追加 | `tests/domains/test_v2_bookkeeping.py::note_bounded_append_only` | specs/bookkeeping.md:136 |
| 12 | 通知恰三键＋`type`／`gates` 闭世界 | `tests/domains/test_v2_bookkeeping.py::notice_three_keys_closed_world` | specs/bookkeeping.md:137 |
| 18 | 工具上下文：身份只从状态取、放行态随上下文、预算按子问题数 | `tests/domains/test_v2_bookkeeping.py::tool_context_assembly` | specs/bookkeeping.md:143 |
| 19 | 结果投影原样（空值与缺省可区分） | `tests/domains/test_v2_bookkeeping.py::result_projection_faithful` | specs/bookkeeping.md:144 |
| 21 | 本块零判断（AST 扫描） | `tests/domains/test_v2_bookkeeping.py::no_judgement_in_bookkeeping` | specs/bookkeeping.md:146 |
| 22 | 【边界集】空步列／超长 digest／已收敛再收敛／越界枚举 → 各落对应分支 | `tests/domains/test_v2_bookkeeping.py::boundary_empty_huge_converged_enum` | specs/bookkeeping.md:147 |
| 23 | 【保留集】常规三步流程的记录形状与顺序不变 | `tests/domains/test_v2_bookkeeping.py::retention_normal_three_steps` | specs/bookkeeping.md:148 |

> 测试文件归属（票注，非规格引文）：本票 7 行与 -01a／-01b 同落**同一个新建文件** `tests/domains/test_v2_bookkeeping.py`（spec :150 节尾原注已在 `RT-W3-01a-bookkeeping.md` 同节照抄，本票不重复转抄，防两处漂移）；旧码测试本批不改。
> 行序缺口说明（票注）：本票行序跳过 1–10、13–17、20——`#` 列三票共用规格表行序，便于 manifest 逐行对账。

## 测试网钉（本块 5 条 pin 行已在 `RT-W3-01a-bookkeeping.md` 同节全量逐字转抄——本票零 pin 行，不重复转抄）

- 核对关系（防两处漂移）：pin-22 写入点单点面 ↔ 行 1／2、pin-22 写入面 ↔ 行 7、pin-24 写入面 ↔ 行 8／9、pin-26 写入面 ↔ 行 10、pin-12 承接面 ↔ 行 5——五条钉的逐字转抄与机检用例全在 -01a；本票 7 行不承载任何 pin 行。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 pin 行只落 -01a 一处（先例 `RT-W4-05b-execution.md` 分票理由原文）。

## 施工要点（specs/bookkeeping.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/bookkeeping.md:105 | 行为 10 过程档案有界且只追加 | `note` 在**写入点**截断 `digest`（上限真源＝`synth/S5-RunState字段矩阵.md` 的 `process_notes` 条目口径，本规格不复述数字）；只追加、不改写既有条目 |
| specs/bookkeeping.md:106 | 行为 11 通知恰三键＋分型闭世界 | `notice` 落 `{type, gates, content}` 恰三键；`type` ∈ `NOTICE_TYPES`、`gates` ⊆ `LimitHit.limit` 七限额键名（流水 52-B），越界即拒；**只追加** |
| specs/bookkeeping.md:111 | 行为 16 工具上下文装配 | `tool_context(state)` **身份只从状态取**（不接调用方传身份）；**外表放行态随上下文走**（不进工具参数、不重排计划）；送窗预算按**子问题数**取值（数值与公式真源＝`appv2/tools/schema.py` 的 `resolve_send_budget` 与其配套常量；`ToolContext` 的形状真源＝`specs/modules.md` `## tools` 卡——**本规格不复述数值**） |
| specs/bookkeeping.md:112 | 行为 17 结果归一投影 | `result_projection(result)` 逐字段**原样投影**（无增删改名）；**空值语义统一**——「有该字段但为空」与「无该字段」**读回可区分**（禁真假值归一） |
| specs/bookkeeping.md:113 | 行为 18 本块零判断 | 除 `call_model` 的转发与两侧闭世界分派外，无词表／正则语义判定。断言：AST 扫描本块源码 |
| specs/bookkeeping.md:147 | 行 22 边界集 | 空步列／超长 digest／已收敛再收敛／越界枚举四形各落对应分支（分支本体在 -01a 行 3／4、-01b 行 14、-01a 行 9／10） |
| specs/bookkeeping.md:148 | 行 23 保留集 | 常规三步流程的记录形状与顺序不变（-01a 落地的写口与 -01b 落地的收口面不得因本票改形） |

结构锚：specs/bookkeeping.md:52 接口定义（工具面与归一投影签名——**形状真源＝-01a 已落地的**，本票只加行为、不改形状）；:23–:39 旧码公共位承接对照（`recon/B1` 十六项落点——行 19 结果归一的旧码对照面在本票落地）；:85–92 框架与依赖红线（类型与常量只许引形状五块）；:115–120 不降级与静默禁令（合法降级路径＝无；触界不静默；记账不丢；不许自述完成）。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三——B1 归块行转抄落 -01a；本票只留指针）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单（B1 明写归本块的行逐字转抄落 `RT-W3-01a-bookkeeping.md`；本票承接其结果归一观测面）〕

- **指针（防两处真源漂移）**：B1「公共位与结果归一」（表内明写「对应 runtimev2 `bookkeeping`」，严重度「高」）的逐字转抄与钉法说明落 `RT-W3-01a-bookkeeping.md` 同节——本票**不重复转抄**。
- 本票与 B1 的关系（链关系登记，切分呈主窗对账）：B1 钉法＝「经 checkpoint 快照／帧流钉『每步通道值归一形』」——本票行 19（`result_projection` 原样投影：空值与缺省读回可区分）与该钉「结果归一」半边**同面**，行 11／12（`note` 有界／`notice` 三键）是该钉在通道值上的另两条投影面；**逐字转抄仍只在 -01a 一处**。
- 关联行（B3，**写明、不重复转抄**）：B3「触顶收敛**落地**」半行＝本块 `converge`（行为 12，归 `RT-W3-01b-bookkeeping.md`）；该关联半行的承接已在 **`RT-W1-01b-state.md`**（state 包 -B 票，其「织网义务」节承载 B3 行逐字转抄）落定——本票不重复转抄。本票行 22 的「已收敛再收敛」边界形是 -01b 行 14 幂等面的边界侧断言，不承载 B3 半行。
- L2 新规格钉随本票施工 TDD 生长（eng/04 §五：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。
- 本票织网义务＝① B1 结果归一观测面的 L1 特征钉（经 checkpoint 快照／帧流钉「每步通道值归一形」的结果侧——织网工序第 3 步「盲区补钉」，与 W1–W3 施工可并行——eng/04 头注）；② 本票 7 行对应用例落网（含【边界集】／【保留集】两行）；③ L2 新规格钉随施工 TDD 生长。

验收: 以下判据逐条全绿为过——
- 「票面对象」7 行逐行实现为 `tests/domains/test_v2_bookkeeping.py` 用例并全绿，测试标识与规格列逐字一致（`#` 保留规格表行序 11、12、18、19、21、22、23，含【边界集】／【保留集】两行）；
- 「测试网钉」零 pin 行——本票只写归属指针，不重复转抄（5 行全在 -01a）；
- 装配与归一两面断言绿：`note` 写入点截断且只追加（行 11，上限数值只引 `synth/S5` 口径、本票不复述）＋`notice` 恰三键且 `type`／`gates` 闭世界（行 12）；
- 工具上下文与结果投影两面断言绿：身份只从状态取／放行态随上下文、不进工具参数／预算按子问题数（行 18，数值与公式只引 `appv2/tools/schema.py`）＋逐字段原样投影、空值与缺省读回可区分（行 19）；
- 元面断言绿：本块零判断 AST 扫描（行 21，除 `call_model` 转发与两侧闭世界分派外无语义判定）；
- 边界·保留两面绿：空步列／超长 digest／已收敛再收敛／越界枚举四形各落分支（行 22）＋常规三步流程记录形状与顺序不变（行 23）；
- 形状单点：共享写口九函数／收敛与收口签名仍以 -01a 落地的为唯一真源，本票不改形状（改形状＝回 -01a 或回设计仓）；-01b 的收口簇不因本票改形；
- 边界闸 R5b／R6／R7 在 `lint-imports` 双配置下绿；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W3-01c 完成，产物 `appv2/runtimev2/bookkeeping/`（装配与归一＋元面＋边界·保留集），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
