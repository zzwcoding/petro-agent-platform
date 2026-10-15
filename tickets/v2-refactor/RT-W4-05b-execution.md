# RT-W4-05b · execution——V2 批量执行（-B：闭世界与红线面／记账与机读信号／边界·保留集）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/execution.md`（状态「已定稿」——前置满足）
Touches modules: `execution`（本票只填 execution 剩余行为簇；规格「触及的模块」表另声明 tools／state／transport／persistence 四关联侧，归各自票承接）
波次: W4 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W4 行三列原文：块列「七个业务相位（understanding → clarification → tool_matching → preconditions → execution → answering → verification）」；理由列「互零依赖，**建议按业务链序施工**（便于走查 narrative 与测试网逐块加厚），不禁止并行」；出口判据列「每相位配属规格十节版式定稿＋新规格钉绿＋触及该相位的特征钉绿」
复审强度: 50% 抽查（eng/03 §五 W4 行原 A 列含 `execution`——该表降级保留的规则原文「A 列抽 50%」；双队制已废止，A/B 分配只余复审强度语义，波序与块归属不变）
前置: ① 规格定稿（`specs/execution.md` 已定稿——已满足）；② **`RT-W4-05a-execution.md` 收票**（同包顺序施工、同包不并行——eng/03 §二 W4 纪律）；③ W3 全收波（经 -05a 传递，已满足）
阻塞: `RT-W4-05a-execution.md`（-05b 前置＝-05a 收票）｜被阻塞: W5 `orchestration`

## 任务

接 `RT-W4-05a-execution.md` 落地的骨架，填 `appv2/runtimev2/execution/` 的**剩余行为簇**：两处闭世界的守门、记账与机读信号的对账收口、程序侧零语义判断与零直连存储符号两条红线、以及边界集／保留集两行。

**本票＝execution 的 -B 票**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 19 行，超 15 行上限 → 切 -A／-B；本票收**剩余 7 行**＝规格表第 8、9、11、14、17、18、19 行（闭世界与红线面／记账与机读信号／边界·保留集行）；前 12 行与**本块 3 条 pin 行**（pin-06／pin-08／pin-16）全在 -05a，本票零 pin 行、不重复转抄（同一 pin 行两处转抄＝两处真源必漂移）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/execution.md` 全文（十节版式）；`specs/modules.md` `## execution` 卡（签名以卡为准）；`specs/tools.md`（`ToolResult` 字段面与错误三档「可重试｜修参｜拒答」——记账字段的来源）；`specs/state.md`（闭世界常量族／`Observation`／指纹簿记字段面）；`specs/parsing.md`（行为 13 指纹器材——行为 14 同参重投闸的指纹来源）；`docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-06／pin-08／pin-16 三行，核本票与 -05a 的边界）。eng/04 §三 关联行已在本票「织网义务」节与 -05a 同节逐字转抄，施工期不必另开。

框架红线: 无点名框架（`langgraph`／`langchain` 只许活在 `orchestration`）——对应闸 R5b 契约（`tools/importlinter_v2.toml` :100–:105）
边界红线: ① **零 LLM 面**：本块不调模型、不引 `appv2.runtimev2.gateway_adapter`——R8（:119–:123）＋ R7（不直引 `appv2.infra.llm_client`，本块天然满足）；② 只经 `tools` 公开面接触世界、不直引引擎——R6（:107–:111）；③ 七个业务相位互不 import——R1（:66–:71）；④ 只引公共层包根——R2（:73–:78）；⑤ 不引旧 `appv2.runtime`——R5（:94–:98）；⑥ **程序侧零语义判断**：无词表／正则语义判定（AST 断言 `::no_lexicon_or_regex_in_execution`，豁免面＝形态处理／集合成员判定）；⑦ **大结果落引用只经 `persistence` 公开面**：无对应边界闸→AST 断言 `::no_direct_storage_symbols`（对象存储客户端／裸 DB driver 直连符号零出现）；⑧ **禁手写替代**：不得自建工具调用旁路、不得改 -05a 已定的形状另立第二套

## 票面对象（specs/execution.md「验收测试」表逐行转抄——本票 7 行：规格表第 8、9、11、14、17、18、19 行）

〔来源：specs/execution.md「验收测试」表 :110–:121（本票取自 :110–:111、:113、:116、:119–:121），逐行原文；`#` 列＝规格表行序（与 -05a 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 8 | `exec_status`／`category` 越界取值 → 判失败 | `tests/domains/test_v2_execution.py::enums_closed_world` | specs/execution.md:110 |
| 9 | 程序侧无词表／正则语义判断（AST 扫描本模块；**豁免面＝形态处理／集合成员判定**——不算语义词表／正则） | `tests/domains/test_v2_execution.py::no_lexicon_or_regex_in_execution` | specs/execution.md:111 |
| 11 | 大结果落引用只经 `persistence` 公开面（无直连符号：对象存储客户端／裸 DB driver） | `tests/domains/test_v2_execution.py::no_direct_storage_symbols` | specs/execution.md:113 |
| 14 | 每次记账字段齐（参数／行数／拒因） | `tests/domains/test_v2_execution.py::per_call_accounting` | specs/execution.md:116 |
| 17 | 机读信号在场（落引用／失败／缺参） | `tests/domains/test_v2_execution.py::execution_signal_present` | specs/execution.md:119 |
| 18 | 【边界集】空结果／超大结果／限流失败／缺参 → 各自落到对应分支 | `tests/domains/test_v2_execution.py::boundary_empty_huge_ratelimit_needinput` | specs/execution.md:120 |
| 19 | 【保留集】全成功时无额外信号、无回炉行为不变 | `tests/domains/test_v2_execution.py::retention_all_ok_unchanged` | specs/execution.md:121 |

> 测试文件归属（票注，非规格引文）：本票 7 行与 -05a 的 12 行同落**同一个新建文件** `tests/domains/test_v2_execution.py`；旧码测试本批不改。

## 测试网钉（本块 3 条 pin 行已在 `RT-W4-05a-execution.md` 同节全量逐字转抄——本票零 pin 行，不重复转抄）

- 核对关系（防两处漂移）：pin-06 ↔ 行 15、pin-08 ↔ 行 4、pin-16 ↔ 行 3 承接面——三条钉的机检用例全在 -05a；本票 7 行不承载任何 pin 行。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 pin 行只落 -05a 一处。

## 施工要点（specs/execution.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/execution.md:62 | 接口定义 两处闭世界 | `exec_status`／`category` 越界值判失败（**不猜、不取默认**） |
| specs/execution.md:84 | 行为 7 每次记账 | 每次工具调用记**参数／回来多少行／或被拒原因**（可事后复算） |
| specs/execution.md:73 | 红线 大结果落引用面 | 只经 `persistence` 公开面，不自行写库／不直连对象存储（AST 断言 `::no_direct_storage_symbols`） |
| specs/execution.md:96 | 不降级与静默禁令 机读信号 | 落引用／失败／缺参都必须产机读信号：`observation`／`tool` 事件 ＋ step payload 的 `row_count`／`ref.handle`／`error.reason` |
| specs/execution.md:95 | 不降级与静默禁令 合法降级路径 | **合法降级路径＝无**（本模块不自降级）——本票 7 行不得引入任何静默兜底分支 |
| specs/execution.md:111 | 行 9 零语义判断 | AST 扫描本模块：无语义词表／正则（豁免面＝形态处理／集合成员判定） |
| specs/execution.md:120 | 行 18 边界集 | 空结果／超大结果／限流失败／缺参四形各落对应分支 |
| specs/execution.md:121 | 行 19 保留集 | 全成功时无额外信号、无回炉行为不变 |

结构锚：specs/execution.md:35–:60 接口定义（形状真源＝-05a 已落地的六形状，本票只加行为、不改形状）；:93–:97 不降级与静默禁令（红线原文 `arch/P7a-交接包与挂账清单.md`（A-P7a-37）「不许静默」）；:99–:121 验收测试表（`#` 行序与 -05a 共用）。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单（本块无明写归块行；下列为逐字转抄的关联行）〕

> | B1 | 公共位与结果归一（`_step_record`/`_next_seq`/`_converge` 等 16 个全节点共用符号，零专属覆盖） | 经 checkpoint 快照／帧流钉「每步通道值归一形」（对应 runtimev2 `bookkeeping`） | 高 |

- 归块注（呈主窗对账）：B1 明写归 `bookkeeping`（写口面，`RT-W3-01a/b/c-bookkeeping.md` 承接）；本票只承接其**执行步通道值**半面——本票行 14（记账字段齐）与行 17（机读信号在场）产出的 `row_count`／`ref.handle`／`error.reason` 即该钉「每步通道值归一形」的执行步侧输入，切分呈主窗。
- 关联行（已转抄处）：B3（探查预算半面）与 B5（`tool` 帧半面）两条关联行已在 `RT-W4-05a-execution.md`「织网义务」节逐字转抄，本票不重复（防两处漂移）。
- 本票织网义务＝① B1 执行步半面的 L1 特征钉（织网工序第 3 步「盲区补钉」，与 W1–W4 施工可并行——eng/04 头注）；② 本票 7 行对应用例落网；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」7 行逐行实现为 `tests/domains/test_v2_execution.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行；`#` 保留规格表行序 8、9、11、14、17、18、19）；
- 两条 AST 红线断言绿：`::no_lexicon_or_regex_in_execution`（语义词表／正则零出现，豁免面按规格原文）＋ `::no_direct_storage_symbols`（对象存储客户端／裸 DB driver 直连符号零出现）；
- 闭世界越界即判失败（行 8）＋记账三字段齐（行 14）＋机读信号在场（行 17）；
- 边界闸 R1／R2／R5b／R6／R7／R8 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；
- 形状单点：`ExecutionOutcome` 等六形状仍以 -05a 落地的为唯一真源，本票不改形状（改形状＝回 -05a 或回设计仓）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W4-05b 完成，产物 `appv2/runtimev2/execution/`（剩余行为簇：闭世界与红线面／记账与机读信号／边界·保留集），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
