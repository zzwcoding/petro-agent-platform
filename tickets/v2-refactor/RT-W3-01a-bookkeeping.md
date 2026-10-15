# RT-W3-01a · bookkeeping——V2 公共簿记（-A：骨架＋共享可变写面核心＋全部 5 pin 行）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/bookkeeping.md`（状态「已定稿」——前置满足）
Touches modules: `bookkeeping`（本票只建 bookkeeping 本体与共享可变写面核心；规格「触及的模块」表另声明 state／gateway_adapter／tools／persistence／transport 五关联侧，归各自票承接）
波次: W3（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W3 行：组合件，依赖 W2 的 gateway_adapter——「bookkeeping 单写口是相位开发的共同依赖」；本波出口判据「每模型调用有 Manifest；写口无旁路（AST＋import 双证）；两道闸机械分派」）
施工队: B 队（eng/03 §五 终表 W3 行 B 队列＝「bookkeeping」，分配理由整行原文「唯一写口＝旁路慢漏，AST 双证要写到位」；已按 eng/03 §五 终表对齐；提交前缀＝[B]——eng/03 §五 扣件①）｜复审强度: 100%（主窗裁：B 队施工≠免复审——本票维持 100% 过独立复审，复审网在 L0 直派；eng/03 §五 B 队标准为抽 50%，本票按主窗裁提高）
前置: ① 规格定稿（`specs/bookkeeping.md` 已定稿——已满足）；② 波次前置：**W2 全收波**（eng/03 §一依赖图：bookkeeping → gateway_adapter ＋ state；W2 的 gateway_adapter 测试替身是后续所有相位测试的地基）；③ 票内前置：无（-A 为本块首票；占位骨架 `appv2/runtimev2/bookkeeping/__init__.py` 已随阶段 2 落锤）
阻塞: W2 全收波（W2 面四包 persistence／transport／gateway_adapter／prompts——各包子票＝`RT-W2-01a/b`／`RT-W2-02a/b`／`RT-W2-03a/b`／`RT-W2-04a/b/c`，按子票计；票号以主窗 manifest 为准）｜被阻塞: `RT-W3-01b-bookkeeping.md`（同包顺序施工——-01b 前置＝-01a 收票；共享写口九函数与形状以 -01a 为唯一真源）；W4 七个业务相位（本块是全节点共享唯一写面——相位开发的共同依赖）

## 任务

按 `specs/bookkeeping.md` 新建 `appv2/runtimev2/bookkeeping/`：全节点共享的**唯一写入面**——步记录与序号、对话链与对话层追加、过程档案、通知、触界收敛落地、完成收口旁路、调模型单点、工具上下文装配、工具结果归一投影。**多节点写同一份状态，只有这一个门口**。

**本票＝bookkeeping 的 -A 票（骨架＋共享可变写面核心＋本块全部 5 条 pin 行）**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **23 行**，超 15 行上限 → 切 **-A／-B／-C** 三票（各 ≤15 行）。本票收 **11 行**＝规格表第 1–10、20 行（写口单点与相位侧禁直写／序号单调成对／步记录全字段／`payload` 保真／`manifest` 随步投影／对话链只追加／合同一次性与唯一写口／对话层纯度／`next_intent` 唯一写口）＋ **5 条 pin 行全量**（pin-22 写入点单点面归属行、pin-22、pin-24、pin-26、pin-12，逐字转抄见「测试网钉」节）；剩余行归 `RT-W3-01b-bookkeeping.md`（行 13–17＝触界收敛与收口簇）与 `RT-W3-01c-bookkeeping.md`（行 11、12、18、19、21–23＝装配与归一＋元面＋【边界集】／【保留集】）。三票同包**顺序施工**（同包不并行）：本票出骨架、公开面与共享写口核心，-01b／-01c 只填各自行为簇、不另立第二套形状（改形状＝回本票或回设计仓）。
**骨架/接口归本票**：共享写口九函数＋收敛与收口＋调模型与工具面签名（规格 :52 接口定义）随本票落位；**旧码公共位承接对照十六项落点表（规格 :23–:39）随本票起手逐项对位**（承接／拆分／排除／退役四类——写码前逐项对位）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （5 份）`specs/bookkeeping.md` 全文（十节版式，含「旧码公共位承接对照」十六项落点表）；`specs/modules.md` `## bookkeeping` 卡（签名以卡为准）；`specs/state.md`（形状与判定真源——`RunState`／`Manifest`／`check_limits`／三族常量）；`docs/runtime-refactor/recon/B1-公共位与结果归一.md`（十六项公共位真源）；`docs/runtime-refactor/synth/S5-RunState字段矩阵.md` §四（共享写口无归属）。eng/04 §三 B1 行已在本票「织网义务」节逐字转抄，施工期不必另开。

**小票制自检（流水 48）**：票面对象 11 行 ≤ 15 ✓；先读 5 份 ≤ 6 ✓；聚焦一个行为簇＝共享可变写面单点（写口九函数／序号与步记录／对话链与对话层／`next_intent` 唯一写口——全落一条「相位禁直写」红线）✓ → 本票不派生。

框架红线: 无点名框架（`_MESSAGE_CLS` 一类 role→框架消息类映射含框架类型，只许活在 `orchestration`——本块只做文本层 `append_message(role, content)`）——对应闸 R5b 契约
边界红线: ① 不直引模型出口（模型只经 `gateway_adapter`）——R7；② 不直引引擎（R6）；③ 运行逻辑只依赖两处（`state` 形状／判定＋`gateway_adapter` 模型出口），类型与常量形状另引三处（`tools` 的 `ToolContext`／`persistence` 的 `StepRecord`／`transport` 的 `NOTICE_TYPES`）且**只许引类型与常量、不许引其行为**——无专属闸→人审＋AST 断言「import 只出现这五块」登记待补；④ 不落盘（本块不写库、不写文件——落盘归 `persistence`）；⑤ 禁手写替代：不得绕过写口直改状态字段（相位侧同禁——测试 `::no_direct_state_write_in_phases`）

## 票面对象（specs/bookkeeping.md「验收测试」表逐行转抄——本票 11 行：规格表第 1–10、20 行）

〔来源：specs/bookkeeping.md「验收测试」表 :126–:135、:145，逐行原文；`#` 列＝规格表行序，-01b／-01c 票续用同一行序不重编〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | 共享写面只经本块（相位禁直写） | `tests/domains/test_v2_bookkeeping.py::single_write_port` | specs/bookkeeping.md:126 |
| 2 | 相位侧不得绕过写口直改状态字段（红线「禁手写替代」的相位侧半面——与 `::single_write_port` 同断言集的相位侧扫描） | `tests/domains/test_v2_bookkeeping.py::no_direct_state_write_in_phases` | specs/bookkeeping.md:127 |
| 3 | 序号单调且与步数成对（禁手工偏移） | `tests/domains/test_v2_bookkeeping.py::seq_monotonic_paired` | specs/bookkeeping.md:128 |
| 4 | 步记录 `StepRecord` 全字段（含 `run_id`）＋`status` 如实（失败态可表达） | `tests/domains/test_v2_bookkeeping.py::step_record_all_fields_and_status` | specs/bookkeeping.md:129 |
| 5 | `payload` 原样保真（空与缺失可区分） | `tests/domains/test_v2_bookkeeping.py::payload_faithful` | specs/bookkeeping.md:130 |
| 6 | `manifest` 投影随步且键恒在场 | `tests/domains/test_v2_bookkeeping.py::manifest_projected_or_empty` | specs/bookkeeping.md:131 |
| 7 | 对话链只追加不改写 | `tests/domains/test_v2_bookkeeping.py::messages_append_only` | specs/bookkeeping.md:132 |
| 8 | 相位合同一次性（回炉轮不重发） | `tests/domains/test_v2_bookkeeping.py::contract_once` | specs/bookkeeping.md:133 |
| 9 | `contracts_appended` 唯一写口＝`append_contract`（幂等；越界相位抛错） | `tests/domains/test_v2_bookkeeping.py::append_contract_sole_write_idempotent_closed_world` | specs/bookkeeping.md:134 |
| 10 | 对话层纯度：`origin` 闭世界且过程内容不入层 | `tests/domains/test_v2_bookkeeping.py::dialogue_port_purity` | specs/bookkeeping.md:135 |
| 20 | `next_intent` 唯一写口＋闭世界越界即拒 | `tests/domains/test_v2_bookkeeping.py::set_intent_single_port_closed_world` | specs/bookkeeping.md:145 |

> 测试文件归属（spec :150 节尾原注照抄）：本块验收测试绑**新建** `tests/domains/test_v2_bookkeeping.py`（本块是阶段 2 新划的公共层块 `appv2/runtimev2/bookkeeping/`，与现状 `appv2/runtime/graph.py` 公共位函数的旧码测试形状不同）；旧码测试本批不改。
> 行序缺口说明（票注）：本票行序跳过 11–19、21–23——`#` 列三票共用规格表行序，便于 manifest 逐行对账。
> 本块不涉面（防一头两认）：行 13–17（触界收敛六键／收敛幂等／材料同源／直答三键／调模型记账）归 `RT-W3-01b-bookkeeping.md`；行 11、12、18、19、21–23（`note` 有界／通知三键／工具上下文／结果投影／零判断元面／【边界集】／【保留集】）归 `RT-W3-01c-bookkeeping.md`。

## 测试网钉（specs/bookkeeping.md「与闸的挂钩表」pin 行逐行转抄——全块 5 行，全在本票）

〔来源：specs/bookkeeping.md「与闸的挂钩表」:180–:184，逐行原文——1 行内含 pin-22 写入点单点面归属＋4 条专钉行〕

1. **（pin-22 写入点单点面归属行）**｜共享写口单点、相位禁直写｜测试 `::single_write_port` ＋ `::no_direct_state_write_in_phases`（钉 `pin-22` 的**写入点单点面**；字段面挂 `specs/state.md`）｜现状：待实现
2. **pin-22（P0）**｜对话链只追加不改写（**写入面**）｜测试 `::messages_append_only`｜现状：待织网（阶段 5）
3. **pin-24（P1）**｜相位合同一次性（**写入面落点＝`append_contract`**——`contracts_appended` 唯一写函数，越界相位抛错）｜测试 `::contract_once` ＋ `::append_contract_sole_write_idempotent_closed_world`｜现状：待织网（阶段 5）
4. **pin-26（P1）**｜对话层纯度（**写入面**：`append_dialogue` 的 `origin` 闭世界＋过程内容不入层）——字段面挂 `specs/state.md`、渲染面挂 `specs/understanding.md`｜测试 `::dialogue_port_purity`｜现状：待织网（阶段 5）
5. **pin-12（P1，承接面）**｜`payload` 原样保真（**写入面**）——钉本体落 `specs/persistence.md` 落盘面｜测试 `::payload_faithful`｜现状：待织网（阶段 5）

- 分工注（票注，防两头认）：pin-22＝写入点单点面（本票行 1／2）＋写入面（本票行 7），字段面挂 `specs/state.md`；pin-24＝写入面落点（本票行 8／9），消费侧重发判定挂 `context`／`orchestration`、常量稳定面挂 `specs/prompts.md`；pin-26＝写入面（本票行 10），字段面挂 `specs/state.md`、渲染面挂 `specs/understanding.md`；pin-12＝承接面（本票行 5），**钉本体落 `specs/persistence.md` 落盘面**。
- pin 行分布（防两处漂移，逐字稿纪律）：本块 5 条 pin 行**全在本票**逐字转抄；-01b／-01c 零 pin 行、只写归属指针（先例 `RT-W4-05b-execution.md` 分票理由原文：「同一 pin 行在两票重复转抄＝两处真源必漂移」）。

## 施工要点（specs/bookkeeping.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/bookkeeping.md:96 | 行为 1 写口单点 | 共享可变写面（步记录／对话链／对话层／过程档案／通知）只经本块函数，相位不得直写（AST／grep 扫描——钉 pin-22 写入点单点面） |
| specs/bookkeeping.md:97 | 行为 2 序号单调且与步记录成对 | `next_seq`＝已有步记录数＋1、`record_step` 内部取号，禁调用方手加偏移 |
| specs/bookkeeping.md:98 | 行为 3 步记录形状 | `StepRecord` 七字段（`run_id` 自状态取、不由调用方传）＋`status` 如实三值（显式关键词参，不得恒 `ok`） |
| specs/bookkeeping.md:99 | 行为 4 `payload` 原样保真 | 直写、禁 `payload or {}` 式假值归一（钉 pin-12 承接面） |
| specs/bookkeeping.md:100 | 行为 5 `manifest` 随步投影 | 非空→`Manifest.as_dict()` 投影；为空→写空（不得省略键） |
| specs/bookkeeping.md:101 | 行为 6 `next_intent` 唯一写口 | `set_intent` 取值 ∈ `INTENT` 闭世界；「去哪」决策仍在 orchestration（写字段≠做路由决策） |
| specs/bookkeeping.md:102 | 行为 7 对话链只追加（钉 pin-22，P0 写入面） | `append_message` 只追加、不改写（不替换、不重排、不删除既有条目） |
| specs/bookkeeping.md:103 | 行为 8 相位合同一次性（钉 pin-24 写入面） | `append_contract` 唯一写函数、幂等、越界相位抛错；调用方据此不重发合同文本 |
| specs/bookkeeping.md:104 | 行为 9 对话层纯度 | `append_dialogue` 的 `origin` 越界即拒；过程内容（任务书／指令／注记）不得经该入口（走 `note`） |

结构锚：specs/bookkeeping.md:23–39 旧码公共位承接对照（`recon/B1` 十六项逐条落点——承接／拆分／排除／退役四类，**写码前逐项对位，随本票起手**）；:52 接口定义（共享写口九函数＋收敛与收口＋调模型与工具面签名）；:85–92 框架与依赖红线；:115–120 不降级与静默禁令（合法降级路径＝无；触界不静默；记账不丢；不许自述完成）。收敛与收口簇（行为 12–14）的骨架对齐随本票落位、行为断言在 `RT-W3-01b-bookkeeping.md`；装配与归一簇（行为 16／17）与元面（行为 18）的断言在 `RT-W3-01c-bookkeeping.md`。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三 归本块行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单——表内明写归本块的行〕

> | B1 | 公共位与结果归一（`_step_record`/`_next_seq`/`_converge` 等 16 个全节点共用符号，零专属覆盖） | 经 checkpoint 快照／帧流钉「每步通道值归一形」（对应 runtimev2 `bookkeeping`） | 高 |

- 归块注：B1 是 §三表内唯一**明写**「对应 runtimev2 `bookkeeping`」的行（严重度「高」）——钉法＝经 checkpoint 快照／帧流钉「每步通道值归一形」（L1 特征钉，黑盒化改造路径——eng/04 §二：「不逐符号翻译，改经公开出口（帧流／RunState／checkpoint 回放）断言」）。
- 关联行（落他票，指针）：B3「每限额上限/触顶收敛行为钉」中「触顶收敛**落地**」半行＝本块 `converge`（行为 12，本票行 13 归 `RT-W3-01b-bookkeeping.md`）——该半行的转抄与义务落 -01b，本票不重复；**键集与数值半行**归 `state`、**W1 侧承接**见 `RT-W1-01b`（明细登记在 -01b／-01c 同节，防两处漂移）。
- L2 新规格钉随本票施工 TDD 生长（eng/04 §五：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。
- 本票织网义务＝① B1 特征钉的**写口侧观测面**（写口九函数每步通道值归一形——checkpoint 快照／帧流钉，织网工序第 3 步「盲区补钉」，与 W1–W3 施工可并行——eng/04 头注）；②「测试网钉」5 行对应用例落网（pin-22 为 P0 承重钉）；③ L2 新规格钉随施工 TDD 生长。

验收: 以下判据逐条全绿为过——
- 「票面对象」11 行逐行实现为 `tests/domains/test_v2_bookkeeping.py` 用例并全绿，测试标识与规格列逐字一致（`#` 保留规格表行序 1–10、20）；
- 「测试网钉」5 行对应用例在场且绿（pin-22 为 P0 承重钉；写入点单点面与字段面分载不重复；本票不重复转抄 -01b／-01c 的零 pin 行）；
- 写口无旁路双证绿：`::single_write_port`（本块内）＋ `::no_direct_state_write_in_phases`（相位侧扫描）＋ AST import 白名单断言；
- 骨架与公开面落位：共享写口九函数＋收敛与收口＋调模型与工具面签名齐（规格 :52），旧码公共位承接对照十六项逐条对位（规格 :23–:39）——-01b／-01c 不得另立第二套形状；
- 边界闸 R5b／R6／R7 在 `lint-imports` 双配置下绿；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W3-01a 完成，产物 `appv2/runtimev2/bookkeeping/`（骨架＋共享可变写面核心），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
