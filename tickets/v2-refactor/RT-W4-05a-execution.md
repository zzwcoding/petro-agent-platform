# RT-W4-05a · execution——V2 批量执行（-A：骨架＋接口＋核心执行簇）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/execution.md`（状态「已定稿」——前置满足）
Touches modules: `execution`（本票只建 execution 本体；规格「触及的模块」表另声明 tools／state／transport／persistence 四关联侧，归各自票承接）
波次: W4 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W4 行三列原文：块列「七个业务相位（understanding → clarification → tool_matching → preconditions → execution → answering → verification）」；理由列「互零依赖，**建议按业务链序施工**（便于走查 narrative 与测试网逐块加厚），不禁止并行」；出口判据列「每相位配属规格十节版式定稿＋新规格钉绿＋触及该相位的特征钉绿」
复审强度: 50% 抽查（eng/03 §五 W4 行原 A 列含 `execution`——该表降级保留的规则原文「A 列抽 50%」；双队制已废止，A/B 分配只余复审强度语义，波序与块归属不变）
前置: ① 规格定稿（`specs/execution.md` 已定稿——已满足）；② 波次前置：**W3 全收波**（eng/03 §一依赖图原文「execution → transport + state」；另经 `tools` 公开面接触世界、经 `persistence` 公开面落大结果引用——state／transport／persistence 分归 W1／W2，W3 全收即本块开工条件）；③ W4 硬前置＝本块触及的特征钉已钉好（eng/03 §四原文：「W4 每相位开工的硬前置＝该相位触及的特征钉已钉好」）
阻塞: W3 全收波（bookkeeping／context／gate 三票，票号以主窗 manifest 为准）｜被阻塞: `RT-W4-05b-execution.md`（同包顺序施工——-05b 前置＝-05a 收票）、W5 `orchestration`

## 任务

在阶段 2 占位骨架上落地 `appv2/runtimev2/execution/`（现为 `__init__.py` 占位骨架）：把过闸后的子问题**真去执行**（查数／搜报告），把结果收成**带出处的观察**——**只读并行、成功不重跑、失败只重做失败的**（`specs/execution.md`「目标」节原文）。

**本票＝execution 的 -A 票（骨架＋接口＋核心行为簇＋本块全部 pin 行）**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **19 行**，超 15 行上限 → 切 -A／-B 两票。本票收 **12 行**＝规格表第 1–7、10、12、13、15、16 行（只读并行执行与观察回流／大结果界线／发射闸族三面）＋ **3 条 pin 行全量**（pin-06／pin-08／pin-16，逐字转抄见「测试网钉」节）；剩余 **7 行**＝规格表第 8、9、11、14、17、18、19 行（闭世界与红线面／记账与机读信号／边界·保留集行）归 `RT-W4-05b-execution.md`。两票同包**顺序施工**（同包不并行）：本票出骨架与公开面，-05b 只填剩余行为簇、不另立第二套形状。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/execution.md` 全文（十节版式）；`specs/modules.md` `## execution` 卡（签名以卡为准）；`specs/tools.md`（`ToolRegistry.call`／`ToolContext`／`ToolResult` 与错误三档「可重试｜修参｜拒答」——本块 seam，只许走公开面）；`specs/persistence.md`（大结果引用落盘公开面与 `handle` 可读回）；`specs/state.md`（`Observation`／全局序号／指纹簿记字段面）；`specs/transport.md`（`tool`／`observation` 帧发射面）。eng/04 §三 关联行与 eng/04a 三钉已在本票「织网义务」「测试网钉」两节逐字转抄，施工期不必另开。

框架红线: 无点名框架（`langgraph`／`langchain` 只许活在 `orchestration`）——对应闸 R5b 契约（`tools/importlinter_v2.toml` :100–:105）
边界红线: ① **零 LLM 面**：本块不调模型、不引 `appv2.runtimev2.gateway_adapter`——R8（:119–:123，source 覆盖 `preconditions`／`verification`／`execution`）＋ R7（不直引 `appv2.infra.llm_client`，本块天然满足）；② 只经 `tools` 公开面接触世界、不直引引擎（`appv2.knowledge`／`appv2.query`／`appv2.retrieval`）——R6（:107–:111）；③ 七个业务相位互不 import——R1（:66–:71）；④ 公共层块只引包根（禁 `appv2.runtimev2.transport.*` 一类深层子模块）——R2（:73–:78）；⑤ 不引旧 `appv2.runtime`——R5（:94–:98）；⑥ 大结果落引用只经 `persistence` 公开面——**无对应边界闸**，降维为 AST 断言 `::no_direct_storage_symbols`（对象存储客户端／裸 DB driver 直连符号零出现）；⑦ **禁手写替代**：不得自建工具调用旁路、不得绕过 `tools` 直引引擎（规格「框架与依赖红线」末条原文）

## 票面对象（specs/execution.md「验收测试」表逐行转抄——本票 12 行：规格表第 1–7、10、12、13、15、16 行）

〔来源：specs/execution.md「验收测试」表 :103–:118（本票取自 :103–:109、:112、:114–:115、:117–:118），逐行原文；`#` 列＝规格表行序，-B 票续用同一行序不重编〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | 只读子问题并行执行；观察编号按定序分配（两次运行同序） | `tests/domains/test_v2_execution.py::parallel_and_stable_seq` | specs/execution.md:103 |
| 2 | 已成功子问题不重发工具调用（指纹命中） | `tests/domains/test_v2_execution.py::success_not_rerun` | specs/execution.md:104 |
| 3 | 失败分类（`retryable`／`bad_args`／`refused`）→ **只重跑 `retryable`**；`refused`（前置闸拒）终局不回炉 | `tests/domains/test_v2_execution.py::failure_classified_retry_subset_only` | specs/execution.md:105 |
| 4 | 行集类结果不落引用（全量行随观察交付，丢行=0）；非行集大结果落引用：窗口只留摘要＋引用＋行数（不留全文） | `tests/domains/test_v2_execution.py::big_result_ref_only` | specs/execution.md:106 |
| 5 | 引用可寻址（handle 能读回原文） | `tests/domains/test_v2_execution.py::material_ref_addressable` | specs/execution.md:107 |
| 6 | `exec_status="ok"` 但 `answered=False` 时如实分开记 | `tests/domains/test_v2_execution.py::exec_status_vs_answered_separated` | specs/execution.md:108 |
| 7 | 缺参 → `need_input` ＋ 挂起；恢复时重取易变环境量、不重放已完成部分 | `tests/domains/test_v2_execution.py::need_input_suspend_resume_guard` | specs/execution.md:109 |
| 10 | 发现步（discover）由本块发起只读调用并发射 `tool` 事件（发射单元 M5） | `tests/domains/test_v2_execution.py::discover_tool_event_emitted` | specs/execution.md:112 |
| 12 | 观察缺出处 → 判失败 | `tests/domains/test_v2_execution.py::observation_requires_source` | specs/execution.md:114 |
| 13 | 单子问题失败不阻断其余（不炸整批） | `tests/domains/test_v2_execution.py::one_failure_does_not_abort_batch` | specs/execution.md:115 |
| 15 | 同参空手重发 → 发射级拒（不执行工具、不占探查预算）；首拒免轮、第 2 次起占轮；异参不拒（门开着） | `tests/domains/test_v2_execution.py::empty_probe_fingerprint_emission_reject` | specs/execution.md:117 |
| 16 | 同参重投闸（行为 14）：dispatch 前查同参指纹簿——全支皆在实录＝拦（拒因回喂模型重决策；首拦免轮、连续第 2 次起占轮）、任一支新参＝放行 | `tests/domains/test_v2_execution.py::same_param_replay_dispatch_gate` | specs/execution.md:118 |

> 测试文件归属（票注，非规格引文）：本块验收测试绑**新建** `tests/domains/test_v2_execution.py`（`execution` 是阶段 2 新划的相位块 `appv2/runtimev2/execution/`，与旧码 `appv2/runtime/` 里的相位实现测试形状不同）；旧码测试本批不改。
> 规格侧缺口登记（票注，呈主窗对账）：规格「行为约定」行为 8（缺位回捞）与行为 12（落引用的单一责任方）在「验收测试」表内**无专属验收行**——本票按规格原文处理、不自行增设验收行（增设＝改规格，回设计仓），此处只登记事实。

## 测试网钉（specs/execution.md「与闸的挂钩表」pin 行逐行转抄——全块 3 行，全在本票）

〔来源：specs/execution.md「与闸的挂钩表」:147–:149，逐行原文；列名同规格「本规格的硬要求｜挂钩｜现状」〕

| 本规格的硬要求（原文） | 挂钩（原文） | 现状（原文） |
|---|---|---|
| 空手探查记指纹＋同参空手重发发射级拒（首拒免轮、第 2 次起占轮；不执行工具、不占探查预算） | 钉 **`pin-06`**（P1） | 待织网（阶段 5） |
| 行集全交付为默认、丢行＝0（行为 4「行集题交付与落引用界线」同规则行——交付行为面；与 `specs/answering.md` 行为 12 同一规则互引、逐字一致） | 钉 **`pin-08`**（P0） | 待织网（阶段 5） |
| 软失败域闸换链回炉恰 1 次为界——**承接在 `specs/preconditions.md` 行为 7**，本块提供回炉触发面 | 钉 **`pin-16`**（P1） | 待织网（阶段 5；钉本体＝preconditions 侧 `::rewire_once_then_refuse`） |

- 分工注（票注，防双头）：pin-08 的**执行侧**落点＝本票行 4 `::big_result_ref_only`（丢行=0／窗口只留摘要＋引用＋行数）；**交付侧**落点＝`specs/answering.md` 行为 12（`RT-W4-06b-answering.md` 行 12）。pin-16 钉**本体**在 preconditions 侧（`::rewire_once_then_refuse`），本票只提供**回炉触发面**（行 3 的失败分类不落本档——规格行为 3 原文：绑定闸拒不落本档）；pin-06 为本块专钉（行 15）。
- 规格「与闸的挂钩表」其余行（R6／R5b／R8 三条边界闸、六条 `tests/...` 现状行、末行人审）非 pin 行，按各自「挂钩」列由上述闸与用例承接，本票不转抄。

## 施工要点（specs/execution.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/execution.md:78 | 行为 1 只读并行执行、编号定序 | 全部工具只读无副作用故并行安全；观察编号按**子问题定序**分配、与执行完成顺序解耦（同一输入两次同序） |
| specs/execution.md:79 | 行为 2 成功不重跑 | 指纹簿记命中即不重发工具调用 |
| specs/execution.md:80 | 行为 3 失败分类三档＋只重跑子集 | `retryable`／`bad_args`／`refused` 写明文，只重跑 `retryable`；`refused`＝前置闸拒＝终局不回炉（回炉触发面＝pin-16 承接处） |
| specs/execution.md:81 | 行为 4 大结果落引用＋行集界线 | 超阈原文落 `persistence`（替代旧「渲染帽裁剪」）；行集题全量交付、丢行＝0——与 `specs/answering.md` 行为 12 逐字同规则（钉 pin-08） |
| specs/execution.md:82 | 行为 5 执行状态与业务结果分开 | `exec_status`（过程）与 `answered`（业务）分别落账；`answered` 判据＝可观察事实（非空观察）＝结构判定 |
| specs/execution.md:83 | 行为 6 缺参挂起与恢复 | 工具报缺参 → `exec_status="need_input"` 挂起；恢复时**重取易变环境量**、不重放已完成部分 |
| specs/execution.md:87 | 行为 10 失败不炸整批 | 任一子问题失败不阻断其余子问题的执行与回流 |
| specs/execution.md:88 | 行为 11 发现步归本块 | 发现步的只读调用与 `tool` 事件发射同属本块（发射单元 M5），同受零 LLM 约束 |
| specs/execution.md:86 | 行为 9 观察必带出处 | 每个 `Observation` 带 `source`；缺出处＝判失败（INV-1 输入） |
| specs/execution.md:89 | 行为 12 落引用的单一责任方 | 落引用由本块落、`persistence` 只作载体；`answering` 只消费引用不重复落 |
| specs/execution.md:90 | 行为 13 空手探查闸（钉 pin-06，P1） | 空手（失败／`refused`／重试耗尽，或成功但新增非 notice 观察为 0）记**同参指纹**；同参空手重发发射级整发射拒、不占探查预算；首拒免轮、第 2 次起占轮 |
| specs/execution.md:91 | 行为 14 同参重投闸（第二闸，与行为 13 成对） | dispatch 前查同参指纹簿：**全支皆在实录＝拦**（拒因回喂模型重决策，首拦免轮、连续第 2 次起占轮），任一支新参＝放行 |

结构锚：specs/execution.md:35–:60 接口定义（`execute`／`ExecutionOutcome`／`SubtaskExec`／`ErrorClass`／`MaterialRef`／`Observation` 六形状签名——两处闭世界 `exec_status`／`category` 越界即判失败）；:67–:74 框架与依赖红线；:93–:97 不降级与静默禁令（**合法降级路径＝无**；落引用／失败／缺参必产机读信号；被落引用原文不得静默丢弃——红线原文 `arch/P7a-交接包与挂账清单.md`（A-P7a-37）「不许静默」）。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单（本块无明写归块行，下列两条为逐字转抄的关联行）〕

> | B3 | H8 预算四限额边界（现只钉了 CLARIFY_ASK_CAP=6） | 每限额上限/触顶收敛行为钉（数值只引预算表） | 中 |
> | B5 | 帧协议级时序（step/text/ask/verdict/done/error 序与 data 形） | 从 `eval/results/frames/` 真帧流转离线 golden 回放钉 | 中 |

- 归块注（呈主窗对账）：§三 表内**无一行明写「对应 runtimev2 `execution`」**（该表内唯一明写行为块名者是 B1→`bookkeeping`）。上引两条为**关联行**，逐条给理由：① B3 的「限额上限」半面里，**探查预算**（空手重发「不占探查预算」）＝本行 15 的机检面（键集与数值面归 `state`，切分呈主窗）；② B5 的帧序里 `tool` 帧＝本行 10 的自产帧（发射单元 M5）。
- 关联行（B6 的形态半面，登记呈主窗对账）：本块的**缺参挂起**（`need_input`，行为 6）不在 §三 B6 行所列三形（「clarify 二级／越集审批／跨实例」）之内——本块自钉 `::need_input_suspend_resume_guard`；B6 行不属本块归块行、未逐字转抄于此，此处只登记「该形未被 B6 覆盖」这一事实，切分呈主窗。
- 本票织网义务＝① 上述关联行的 L1／L3 钉（织网工序第 3 步「盲区补钉」，与 W1–W4 施工可并行——eng/04 头注）；②「测试网钉」3 行对应用例落网；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」12 行逐行实现为 `tests/domains/test_v2_execution.py` 用例并全绿，测试标识与规格列逐字一致（`#` 保留规格表行序 1–7、10、12、13、15、16）；
- 「测试网钉」3 行对应用例在场且绿（pin-08 P0 承重钉；pin-06 为本块专钉；pin-16 为承接面，钉本体在 preconditions 侧）；
- 骨架与公开面按卡面签名（`execute(state) -> ExecutionOutcome`）＋六形状齐（规格 :35–:60），两处闭世界越界即判失败；
- 边界闸 R1／R2／R5b／R6／R7／R8 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W4-05a 完成，产物 `appv2/runtimev2/execution/`（骨架＋接口＋核心执行簇），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
