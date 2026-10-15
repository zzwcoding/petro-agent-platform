# RT-W5-01b · orchestration——V2 编排（-B：挂起／恢复＋事件通路＋帧批次＋回炉与预算簇）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/agent-loop.md`（状态「已定稿」——前置满足）
Touches modules: `orchestration`（本票只填 orchestration 的挂起／恢复与事件通路簇；规格「触及的模块」表另声明 bookkeeping／preconditions／context／verification／persistence／api／tools 七关联侧，归各自票承接）
波次: W5（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W5 行三列原文：块列「`orchestration`」；理由列「依赖全部相位＋persistence/transport/bookkeeping，天然最后」；出口判据列「有界终止；挂起恢复；相位顺序只由本块决定」）
复审强度: 100%（eng/03 §五 流水 48 规则，质量关键块全复审——§五 W5 行理由列原文：「系统性缺陷藏匿点；在关键路径末端，B 的慢不阻塞人」；§五 头注原文「B 列六块＝质量关键块施工后 100% 复审……波序与块归属不变」；复审网在 L0 直派、报告直送主窗——§五 扣件④原文「复审网在 L0 直派（复审代理不经过 Kimi-A、报告直送主窗）」）
前置: ① 规格定稿（`specs/agent-loop.md` 已定稿——已满足）；② **`RT-W5-01a-orchestration.md` 收票**（同包顺序施工、同包不并行；挂起／恢复挂在 -01a 落地的图与执行器接缝上——本票不另立第二套形状）；③ W1–W4 全收波（经 -01a 传递，已满足）
阻塞: `RT-W5-01a-orchestration.md`（-01b 前置＝-01a 收票）｜被阻塞: `RT-W5-01c-orchestration.md`（-01c 前置＝-01b 收票）

## 任务

接 `RT-W5-01a-orchestration.md` 落地的骨架，把**挂起—恢复闭环**与**事件通路**接实：工具／前置条件机报「等用户」时 run 转 `waiting_ask` 挂起、事件流发 `ask` 帧后正常收束；用户带选择回来（`resume`）把选择回喂、同链续推到收口；断线凭**全流单调游标**重连不重复不遗漏；回炉（失败子集／换链）与预算面（轮数、发现预算、免轮例外）按规格在图上收敛。

**本票＝orchestration 的 -B 票**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **36 行**（`specs/agent-loop.md:177–:212`），超 15 行上限 → 切 -A／-B／-C 三票；本票收 **10 行**＝规格表第 8–12、14、15、22、26、28 行（挂起恢复两形态／回炉与预算／事件通路与断线游标／错误路径）；前 15 行与 3 条 pin 行在 -01a，余 11 行与 1 条 pin 行在 -01c——本票**只承载 1 条 pin 行**（pin-29，逐字转抄见「测试网钉」节），另 4 条 pin 行不重复转抄。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/agent-loop.md` 全文（241 行十节版式）；`specs/transport.md`（`ask` 帧形状与 `kind` 闭世界、**挂起铁律**「`ask` 帧之后照发 `done`」、游标全流单调与断线续推——行 22／26 的帧面真源）；`specs/state.md`（`AskChoice.kind`／`decision` 闭世界、受理三形态互斥、`pending_ask` 形状面）；`specs/persistence.md`（`waiting_ask → running` **唯一合法恢复方向**、检查点与恢复可重放面——挂起态的落库归该块，本块只出调用侧）；`specs/bookkeeping.md`（挂起／恢复／回炉路径上的写面：`append_message`／`notice`／`set_intent`／`converge` 与 `call_model` 单点——本块不直写状态字段）；`specs/clarification.md`（挂起契约原文：「返回 `ClarifyAsk` 即进入挂起态（`pending_ask` 随检查点走）；恢复经 `orchestration` 的 `resume` 入口」——行 8／14／15 的相位侧对接面）。eng/04 §三 B5／B6 两行已在本票「织网义务」节逐字转抄，施工期不必另开。

**小票制自检（流水 48）**：票面对象 10 行 ≤ 15 ✓；先读 6 份 ≤ 6 ✓；聚焦一个行为簇＝挂起—恢复闭环＋事件通路单链（本块 seam 的回归侧：命令进、事件流出）✓ → 本票不派生。

框架红线: **LangGraph（含 `langchain*`）只许活在本块**——本块是 17 块中**唯一**允许框架的块（其余 16 块禁引）；对应闸 **R5b 契约**（`tools/importlinter_v2.toml` :100–:107，`forbidden_modules` 含 `langgraph`／`langchain`／`langchain_core`／`langchain_community`）。规格原文（`specs/agent-loop.md:71`）：「**框架只许本模块内部**：LangGraph（含 `langchain*`）**不得渗漏出本模块**；state schema 自有（`RunState` 为自有 dataclass，框架只当 schema 消费）」。本票的挂起／恢复**只许经本块图与执行器接缝**，框架类型不得出现在公开面签名上。
边界红线: ① **模型调用发起面＝`bookkeeping.call_model`（单点发起；其内部唯一出口＝`gateway_adapter`）**：不直引 `gateway_adapter`、不自建模型客户端——**R7 契约**（:114–:119）＋「无旁路」行为断言；② 只经 `tools` 公开面接触世界、不直引引擎——**R6 契约**（:108–:112）；③ 只经 `transport` **包根**发帧（不自行拼 wire 帧、不直连 SSE 通道）：**R2 契约不覆盖本块**（source 只含七个业务相位）→ **无专属闸 → 人审**（规格挂钩表 :234 行）；④ **禁手写替代**：不得自建帧通路、不得自建挂起态存储（挂起态落库与恢复重放归 `persistence`，本块只出调用侧）、不得绕过 `bookkeeping` 写口直改状态字段——R5b／R7 可降维面＋余面**人审**（:235 行）；⑤ 不引旧码 `appv2.runtime`——**R5 契约**（:95–:100）；⑥ 恢复方向的合法性不在本块：`waiting_ask → running` 是 `persistence` 侧的**结构约束**（`specs/persistence.md:139` 原文「`waiting_ask → running` 是唯一合法的「恢复」迁移方向」），本块只决定「该不该迁移」（该块「不做什么」row 1 原文：「编排逻辑、状态迁移决策、图驱动」→`orchestration`）

## 票面对象（specs/agent-loop.md「验收测试」表逐行转抄——本票 10 行：规格表第 8–12、14、15、22、26、28 行）

〔来源：specs/agent-loop.md「验收测试」表 :184–:204（本票取自 :184–:188、:190–:191、:198、:202、:204），逐行原文；`#` 列＝规格表行序（与 -01a／-01c 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 8 | 阈值判断形口径反问仍挂起→resume 回喂→续跑收口 | `tests/domains/test_v2_four_phase.py::test_four_phase_clarify_ask_threshold_form_still_suspends_and_resumes` | specs/agent-loop.md:184 |
| 9 | 失败子集回炉（成功子结果不重跑断言） | `tests/domains/test_v2_four_phase.py::test_four_phase_refurnace_carries_failed_subset_only` | specs/agent-loop.md:185 |
| 10 | 3 轮部分续找语义（轮 1 部分答案→轮 2/3 带失败子集） | `tests/domains/test_v2_four_phase.py::test_four_phase_three_rounds_partial_answers` | specs/agent-loop.md:186 |
| 11 | discover 全 run ≤10＋计数埋点落 payload | `tests/domains/test_v2_four_phase.py::test_four_phase_discover_budget_ten_and_taps` | specs/agent-loop.md:187 |
| 12 | 预算拒免轮例外只留首次（连续第 2 次转占轮） | `tests/domains/test_v2_four_phase.py::test_four_phase_clarify_budget_reject_spin_gate` | specs/agent-loop.md:188 |
| 14 | 越集审批挂起→批准→前置条件机重判→批量执行 | `tests/domains/test_v2_four_phase.py::test_four_phase_extable_approval_resume_precondition_chain` | specs/agent-loop.md:190 |
| 15 | 引擎侧 ask 挂起→resume→批量续跑收口 | `tests/domains/test_v2_four_phase.py::test_four_phase_engine_ask_resume_batch_chain` | specs/agent-loop.md:191 |
| 22 | 工具返回 ask→run 挂起→GET 状态 waiting_ask→resume 完成 | `tests/api/test_v2_asks.py::test_ask_suspend_resume` | specs/agent-loop.md:198 |
| 26 | 断线游标重连→事件不重复不遗漏 | `tests/api/test_v2_asks.py::test_sse_cursor_resume` | specs/agent-loop.md:202 |
| 28 | resume/追问错误路径（404/409/互斥 409） | `tests/api/test_v2_asks.py::test_resume_error_paths` | specs/agent-loop.md:204 |

> 测试文件归属（票注，非规格引文，呈主窗对账）：本票 10 行的测试标识**落既有文件**（`tests/domains/test_v2_four_phase.py`／`tests/api/test_v2_asks.py`——`ls` 实测在册），属 eng/04 §二／§五 的**存量测试改写面**（改接线：import 面从 `appv2.runtime.*` 改指 runtimev2 17 子包）；**旧码测试本批不改**（本批＝阶段 4 拆票，改写属织网②）。行 22／26／28 落 `tests/api/test_v2_asks.py`＝`api` 层文件，而 `api` 不在 eng/03 §二 五波序列的 17 块内（eng/00 §三 原文：17 块＝「业务相位 7 ＋ 公共层 9 ＋ 入口闸族 1」；`api` 属既有 7 张卡——eng/00 §一 原文「其余 6 张卡不动」）——「三端点＋SSE 事件桥」（规格 :41 触及表原文）的施工归属呈主窗 manifest 对账（-01a 同注）。
> 行序缺口说明（票注）：本票行序跳过 1–7、13、16–21、23–25、27、29–36——`#` 列三票共用规格表行序，便于 manifest 逐行对账。

## 测试网钉（specs/agent-loop.md「与闸的挂钩表」pin 行逐行转抄——本块 5 行，本票承载 1 行，余 4 行归 -01a／-01c）

〔来源：specs/agent-loop.md「与闸的挂钩表」:239，逐行原文；列名同规格「本规格的硬要求｜挂钩｜现状」〕

| 本规格的硬要求（原文） | 挂钩（原文） | 现状（原文） |
|---|---|---|
| 挂起→resume 闭环（clarify 选项／越集审批两形态 ask 帧） | 钉 **`pin-29`**（P0） | 待织网 |

- 分工注（票注，防两头认）：`pin-29`＝**闭环面**（本票行 8／14／15／22／28 承载——挂起→resume 同链续推收口）；**形状面**在 `specs/state.md`（其挂钩表 `:191` 行原文：「`AskChoice` 的 `kind` 判别字段（**形状面**）」←该块 `::ask_payload_shape_closed_world`）；**帧面**在 `specs/transport.md`（其挂钩表 `:158` 行原文：「挂起→resume 的**帧面**（`ask` 帧 kind 闭世界＋挂起后照发 `done`）」，原文明写「**闭环面挂 `specs/agent-loop.md`**」）；挂起态落库面在 `specs/persistence.md`（`waiting_ask → running` 唯一合法恢复方向）。
- 本块 pin 行分布（防两处漂移，逐字稿纪律）：本块 5 条 pin 行＝pin-23／pin-22／pin-24（`RT-W5-01a-orchestration.md`）＋ pin-29（本票）＋ pin-28（`RT-W5-01c-orchestration.md`）——**同一 pin 行只在一票逐字转抄**，其余票只写核对关系（先例 `RT-W4-05b-execution.md` 分票理由原文：「同一 pin 行在两票重复转抄＝两处真源必漂移」）。
- 规格「与闸的挂钩表」其余行（spec gate／人审两行／R5b／R7／R6／R2 人审行／真源引用闸）非 pin 行，本票不转抄。

## 施工要点（specs/agent-loop.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/agent-loop.md:127 | 行为 4 工具 ask 与挂起恢复 | 工具只经 `ToolRegistry.call`；返回 `status=ask` 时 run 转 `waiting_ask` 挂起、事件流发 `ask` 帧后正常收束；resume 带选择续跑；前置条件机的 `ask` 态（等用户：越集审批／口径反问）与引擎侧 ask 同走挂起—恢复链 |
| specs/agent-loop.md:157 | 行为 9 run 状态机 | running→waiting_ask→（resume）→running→completed/failed；断线凭游标续传，进程重启后可恢复 waiting_ask 态（resume 可达） |
| specs/agent-loop.md:137 | 行为 7 预算闸（触界即收敛） | 轮数每用户输入周期 ≤3（clarify 发射 discover 不占轮、decompose 占轮、ASK 挂起等人工不计轮；**澄清回收（resume）重置轮预算合法——rounds=0**）；轮 2/3 只带失败／缺失子问题＋拒因回炉①；发现预算全 run ≤10；预算拒免轮例外只留首次、连续第 2 次起转占轮 |
| specs/agent-loop.md:149 | 行为 8 执行器与命令入口（H3） | **命令受理**：`ask`／`resume` 是唯一入口；**三态落库（H3）**：`completed`／`failed`／`waiting_ask` 三态由本块写 run 表（`answer`／`manifest_digest` 随三态落）——三态写面由 -01c 行 31 承载，本票只保证挂起态被正确置入与恢复 |
| specs/agent-loop.md:164 | 行为 11 `verdict` 帧两形的批次落定（承接条款） | `verdict` 帧有 `verify`／`final` 两形；**两形的发帧时机与批次由本块协调**——`verification`／`answering` 各自只保证自产部分就位，**由本块把它们与链尾收口按同一批落定**；两形缺任一同批判失败 |
| specs/agent-loop.md:59 | 接口定义 事件枚举＋游标 | 九类闭世界 `step/text/tool/observation/ask/verdict/citation/notice/blackbox`；`RunHandle.cursor`＝**全流单调**断线游标（重放不位移） |
| specs/agent-loop.md:66 | 接口定义 错误码 | 400 参数非法｜401 身份缺失｜404 run 不存在｜409 run 非挂起态不可 resume（重连/追问互斥同 409）——行 28 的四条路径即此表 |
| specs/agent-loop.md:168 | 不降级与静默禁令 合法降级路径 | **合法降级路径：无**（编排层不自降级；图执行器不可用时按 fail-closed 收束为 `failed`，**不产出半成品答案**） |

结构锚：specs/agent-loop.md:46–:67 接口定义（`RunHandle = {run_id, stream, cursor}`；`AskChoice = {kind, choice, decision, approval_id}`——`kind` 闭世界 `clarify`｜`external_table_approval`，行 8／14 两形态的受理载荷）；:166–:171 不降级与静默禁令（挂起／预算触界都必须产生机读信号：事件帧九类闭世界＋step payload＋`security.audit` 责任账；**触界不得静默**，红线原文 `docs/runtime-refactor/arch/P7a-交接包与挂账清单.md`（A-P7a-37））；:214–:221 依赖与风险（LangGraph checkpointer 的 PG saver 与 V1 表共存、新表前缀 `agent_v2_` 隔离——saver 组合面归 -01c 行 27）。规格「与闸的挂钩表」末行（**人审**，:241）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。
规格侧缺口登记（票注，呈主窗对账；**不自行增设验收行**——增设＝改规格，回设计仓）：① **行为 11 的本块协调面（`verdict` 帧两形与链尾同批落定）在「验收测试」表无专属验收行**——最近者为行 16（四相位端到端剧本，归 -01a）与行 25（预算触界收敛，归 -01c）；`specs/answering.md` 行 8 `::finalize_atomic`（收口同批落定）与 `specs/verification.md` 行为 10 均只保证**自产部分**、原文明写「批次落定由 `orchestration` 协调」——本块协调面本票只登记事实，不新起验收行。② 行为 4 的「外表越集审批态落 **ToolContext.approved_tables**（不走引擎 approved_tables、不重排计划——A2 裁决）」面与行 14 的批量执行衔接，其 `ToolContext` 载体归 `bookkeeping.tool_context`（RT-W3-01a/b/c 行 18）——本票只做路由与恢复编排、不落其形状。③ 行为 9 的「ask 帧后正常收束」**帧序铁律**取值真源在 `specs/transport.md`（挂起铁律：`ask` 帧之后照发 `done`），本票不复制其实现。
本块不涉面（防一头两认）：行 1–4、6、7、13、16–21、29、34 归 `RT-W5-01a-orchestration.md`；行 5、23–25、27、30–33、35、36 归 `RT-W5-01c-orchestration.md`。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单（下列两行为逐字转抄的关联行；表内明写归本块的行 B2 已由 -01a 逐字转抄）〕

> | B5 | 帧协议级时序（step/text/ask/verdict/done/error 序与 data 形） | 从 `eval/results/frames/` 真帧流转离线 golden 回放钉 | 中 |
> | B6 | 挂起恢复多场景（clarify 二级／越集审批／跨实例） | 专属钉＋回放钉（跨实例条保持门控） | 中 |

- 归块注（呈主窗对账）：① B5 的帧序钉＝本票行 22（`ask` 帧后收束、`GET` 状态 `waiting_ask`）与行 26（断线游标）的钉面；钉法真源＝`eval/results/frames/` 真帧流转离线 golden 回放钉——eng/04 §七 挂账原文：「harness 只辖 leg JSONL；`eval/results/frames/*.json`（单对象 frames 数组）是另一载体，L3 钉若要消费需另加解析形（登记待 L3 开工时定）」，落钉前须先定该解析形。② B6 的三场景中 **clarify 二级**＝本票行 8（阈值判断形口径反问挂起→resume），**越集审批**＝本票行 14（越集审批挂起→批准→重判→批量）、**跨实例**条＝`RT-W5-01c-orchestration.md` 行 27（挂起态跨进程恢复）——原文「跨实例条保持门控」照抄执行（该条按门控处理、本票不冒充覆盖）。
- 关联行（已转抄处，本票不重复）：B2（`_ROUTES` 路由表逐项，明写归 `orchestration`）已由 `RT-W5-01a-orchestration.md` 逐字转抄；B3（H8 预算四限额边界）关联行落 `RT-W5-01c-orchestration.md`（本票行 11／12 的探查预算与免轮例外即其机检面）；B1（公共位与结果归一，明写归 `bookkeeping`）已由 `RT-W3-01a/b/c-bookkeeping.md` 逐字转抄。
- 本票织网义务＝① B5／B6 两关联行的 L1／L3 钉（织网工序第 3 步「盲区补钉」，与 W1–W4 施工可并行——eng/04 头注）；②「测试网钉」1 行（pin-29）对应用例落网；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」10 行逐行实现为对应既有测试文件用例并全绿（`tests/domains/test_v2_four_phase.py` 7 行、`tests/api/test_v2_asks.py` 3 行），测试标识与规格列逐字一致（`#` 保留规格表行序 8–12、14、15、22、26、28）；
- 「测试网钉」pin-29 行对应用例在场且绿（P0 承重钉；本票不重复转抄 pin-23／pin-22／pin-24／pin-28）；
- 挂起—恢复闭环断言绿：`waiting_ask` 置入与恢复同链续推、`ask` 帧后正常收束、断线重连不重复不遗漏（游标＝`cursor = id + 1` 排他起点，语义真源 `specs/transport.md`）；
- 回炉与预算面断言绿：失败子集回炉不重跑成功子结果、轮 2/3 只带失败子集、discover ≤10 与拒免轮例外（**数值只引 `state` 预算表，本票不写字面值**）；
- 边界闸 R5／R5b／R6／R7 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；「只经 `transport` 包根」与「禁手写替代」两面按规格挂钩表原文走**人审**；
- 形状单点：`RunHandle`／`AskChoice`／`RunCommand → 执行器 → RunEvent` 接缝仍以 -01a 落地的为唯一真源，本票不改形状（改形状＝回 -01a 或回设计仓）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W5-01b 完成，产物 `appv2/runtimev2/orchestration/`（挂起／恢复＋事件通路＋回炉与预算簇），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
