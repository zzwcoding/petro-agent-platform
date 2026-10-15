# RT-W5-01a · orchestration——V2 编排（-A：骨架＋图装配＋路由表＋命令受理三形态＋四相位链路集成）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/agent-loop.md`（状态「已定稿」——前置满足）
Touches modules: `orchestration`（本票只建 orchestration 本体；规格「触及的模块」表另声明 bookkeeping／preconditions／context／verification／persistence／api／tools 七关联侧，归各自票承接——规格 :33–:42 表 8 行，第 1 行为本块、其余七行为关联侧）
波次: W5（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W5 行三列原文：块列「`orchestration`」；理由列「依赖全部相位＋persistence/transport/bookkeeping，天然最后」；出口判据列「有界终止；挂起恢复；相位顺序只由本块决定」）
复审强度: 100%（eng/03 §五 流水 48 规则，质量关键块全复审——§五 表 W5 行理由列原文：「系统性缺陷藏匿点；在关键路径末端，B 的慢不阻塞人」；§五 头注原文：「**2026-10-16 更新：双队制废止**——改为单窗＋子代理 ≤3 并发、小票制，流水 48；下表 A/B 分配**降级为「复审强度规则」保留**：B 列六块＝质量关键块施工后 100% 复审，A 列抽 50%，交界归消费者验证；波序与块归属不变」；本块在 B 列 → 复审强度 100%。复审网在 L0 直派、报告直送主窗——§五 扣件④原文：「复审网在 L0 直派（复审代理不经过 Kimi-A、报告直送主窗）」）
前置: ① 规格定稿（`specs/agent-loop.md` 已定稿——已满足）；② 波次前置：**W1–W4 全收波**（eng/03 §一依赖图原文「orchestration → 七个相位 + persistence + transport + bookkeeping」——七个相位归 W4、persistence／transport 归 W2、bookkeeping 归 W3）；③ W4 硬前置（eng/03 §四原文：「W4 每相位开工的硬前置＝该相位触及的特征钉已钉好」）随 W4 收波一并满足
阻塞: W1–W4 全收波（W1 `RT-W1-01a/b-state.md`；W2 `RT-W2-01a/b-persistence.md`／`RT-W2-02a/b-transport.md`／`RT-W2-03a/b-gateway_adapter.md`／`RT-W2-04a/b/c-prompts.md`；W3 `RT-W3-01a/b/c-bookkeeping.md`＋context／gate 两票；W4 `RT-W4-01a`～`RT-W4-06b` 各票＋verification 票——票号以主窗 manifest 为准）｜被阻塞: `RT-W5-01b-orchestration.md`（同包顺序施工——-01b 前置＝-01a 收票）、`RT-W5-01c-orchestration.md`（-01c 前置＝-01b 收票；骨架与公开面以 -01a 为唯一真源）｜本块被阻塞侧: 切换（eng/03 §三 切换前提原文：「W1–W5 全绿 ＋ 特征钉全绿 ＋ **重写出口判据达成**（Owner 已裁＝《规划》§八-B 题二 A：Q17 复考检索域 ❌=0、全卷 ❌≤5＋六闸全绿＋合同覆盖率 V2 面无缺口＋真机多轮前缀延伸不回归）＋ 生产冒烟通过」）

## 任务

在阶段 2 占位骨架上落地 `appv2/runtimev2/orchestration/`（现为 `__init__.py` 占位骨架，模块卡职责行原文：「编排与执行——图装配与路由、命令受理与执行器、挂起恢复、**检查点 saver 组合**（LangGraph PG saver 实现——组合 `persistence` 的框架无关行级口，不直连表）」）：把**四相位业务循环接成一张图**并**驱动它跑**——用户的问题进来（`ask`）或挂起的选择回来（`resume`），本块受理命令、按路由表推进相位、把过程与结果发成事件流。**业务相位不得自行决定跳转**（规格行为 8 原文：「**组合图装配与路由表（H2）**：节点注册、条件边、路由表在本块**一处集中**——**业务相位不得自行决定跳转**」）。

**本票＝orchestration 的 -A 票（骨架＋图装配＋路由表＋命令受理三形态＋四相位链路集成＋本块 3 条 pin 行全量）**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **36 行**（`specs/agent-loop.md:177–:212`），远超 15 行上限 → 切 **-A／-B／-C** 三票（各 ≤15 行）。本票收 **15 行**＝规格表第 1–4、6、7、13、16–21、29、34 行（图装配与路由表／四相位链路集成／命令受理三形态／步序与 Manifest／对话状态链）；剩余行归 `RT-W5-01b-orchestration.md`（行 8–12、14、15、22、26、28＝挂起恢复＋事件通路＋帧批次簇）与 `RT-W5-01c-orchestration.md`（行 5、23–25、27、30–33、35、36＝收口与红线收束簇）。三票同包**顺序施工**（同包不并行）：本票出骨架、公开面与路由表，-01b／-01c 只填各自行为簇、不另立第二套形状。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/agent-loop.md` 全文（241 行十节版式——**本块对外规格真源就是这份**，含行为约定 11 条、验收测试 36 行、与闸的挂钩表）；`specs/modules.md` `## orchestration` 卡（公开接口与依赖以卡为准——本票只建卡面公开面）＋`## 边界规则`（R1／R2／R5／R5b／R6／R7）；`specs/state.md`（`RunState`／`AskRequest`／`AskChoice`／`RunHandle` 形状面与常量族——受理载荷与回执的形状真源）；`specs/bookkeeping.md`（`call_model` 单点发起面、`set_intent` 写口、`append_contract` 幂等面与 `append_message` 追加面）；`specs/transport.md`（帧出口与九个事件名闭世界、游标语义——本块只经包根发帧）；`docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-22／pin-23／pin-24 三行——本票「测试网钉」节已逐字转抄，施工期不必另开）。eng/04 §三 B2 行已在本票「织网义务」节逐字转抄，施工期不必另开。

**小票制自检（流水 48）**：票面对象 15 行 ≤ 15 ✓；先读 6 份 ≤ 6 ✓；聚焦一个行为簇＝「命令进、事件流出」（规格 :150–:151 原文）的单链（本块单一 seam `RunCommand → 执行器 → RunEvent`）✓ → 本票不派生。

框架红线: **LangGraph（含 `langchain*`）只许活在本块**——本块是 17 块中**唯一**允许框架的块，其余 16 块禁引；对应闸 **R5b 契约**（`tools/importlinter_v2.toml` :100–:107，`source_modules` 实列其余 16 块、`forbidden_modules` 含 `langgraph`／`langchain`／`langchain_core`／`langchain_community`，`allow_indirect_imports = true`）。规格原文（`specs/agent-loop.md:71`）：「**框架只许本模块内部**：LangGraph（含 `langchain*`）**不得渗漏出本模块**；state schema 自有（`RunState` 为自有 dataclass，框架只当 schema 消费）」。框架类型（图／节点／checkpointer saver 类）**不得出现在本块公开面签名**上（公开面＝卡面 `AgentRuntime.ask/resume`）。
边界红线: ① **模型调用发起面＝`bookkeeping.call_model`（单点发起；其内部唯一出口＝`gateway_adapter`）**：编排层与各相位不直引 `gateway_adapter` 发起模型调用、不自建模型客户端——**R7 契约**（:114–:119，source 含 `appv2.runtimev2.orchestration`）＋「无旁路」行为断言；② 只经 `tools` 公开面接触世界、不直引引擎（`knowledge`／`query`／`retrieval`）——**R6 契约**（:108–:112）；③ 只经 `transport` **包根**发帧（不自行拼 wire 帧）：**R2 契约不覆盖本块**（其 source 只含七个业务相位，不含 `orchestration`——`:74–:79` 亲读属实）→ **如实登记为无专属闸 → 人审**（规格挂钩表 `:234` 行；降维 AST 断言需新增验收行，本批未授权、登记待补）；④ **禁手写替代**：不得自建图执行器旁路、不得自建模型客户端、不得自建帧通路——可降维面＝R5b／R7，余面**人审**（规格挂钩表 `:235` 行）；⑤ 不引旧码 `appv2.runtime`——**R5 契约**（:95–:100）；⑥ 三态落库／审计／身份缝的写口各自单点（审计 `security.audit`、身份 `infra.security.resolve_actor`）——落 c 票「票面对象」行 31–33 承接，本票只读其公开面；⑦ 相位侧只许经 `bookkeeping` 写口改状态（规格原文 `specs/agent-loop.md:171`：「**不许自述完成**：模型只能**申请**完成，**提交完成的是本块**（依据核验结果）」——完成判定归本块，落 c 票行 31）

## 票面对象（specs/agent-loop.md「验收测试」表逐行转抄——本票 15 行：规格表第 1–4、6、7、13、16–21、29、34 行）

〔来源：specs/agent-loop.md「验收测试」表 :177–:212（本票取自 :177–:180、:182–:183、:189、:192–:197、:205、:210），逐行原文；`#` 列＝规格表行序，-B／-C 票续用同一行序不重编〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | 四相位路由拓扑（clarify/toolmatch/precondition/batch 入图、回决策边重定向） | `tests/domains/test_v2_four_phase.py::test_four_phase_routing_topology` | specs/agent-loop.md:177 |
| 2 | QuestionGroup schema（子问题 ≤4 上限/ledger_notes 必填/chain-tool 一致） | `tests/domains/test_v2_four_phase.py::test_question_group_schema_happy_and_caps` | specs/agent-loop.md:178 |
| 3 | 工具匹配与问题组闭世界对账（缺/多/未知 id 拒） | `tests/domains/test_v2_four_phase.py::test_tool_match_closes_world_against_group` | specs/agent-loop.md:179 |
| 4 | 前置条件机**三态**分支（`allow`／`refuse`／`ask`；注记并入放行——Owner 裁决 §12-Q-B）**【该测试标识＝织网② 改写对象：旧四态断言 `test_precondition_four_states_reachable` 待退役、三态版待织——登记 `eng/04` 盲区 B2b】** | `tests/domains/test_v2_four_phase.py::test_precondition_three_states_reachable` | specs/agent-loop.md:180 |
| 6 | caliber_key 三态（场景词/双口径并列/阈值反问） | `tests/domains/test_v2_four_phase.py::test_precondition_caliber_three_forms` | specs/agent-loop.md:182 |
| 7 | 澄清合同收窄（窗可锚定＝禁 ask，直发分解零挂起） | `tests/domains/test_v2_four_phase.py::test_four_phase_anchorable_window_skips_ask_delivers_degrade` | specs/agent-loop.md:183 |
| 13 | 词典层台账常驻注入（ledger_dump 族 Manifest 可查） | `tests/domains/test_v2_four_phase.py::test_four_phase_ledger_dump_round1_injection` | specs/agent-loop.md:189 |
| 16 | 四相位端到端剧本（澄清→分解→过闸→批量→汇总收口） | `tests/domains/test_v2_four_phase.py::test_four_phase_end_to_end_scripted` | specs/agent-loop.md:192 |
| 17 | 提问→事件流步序（understand→四相位→answer 次序） | `tests/api/test_v2_asks.py::test_loop_step_sequence` | specs/agent-loop.md:193 |
| 18 | 每个模型调用 step 落 Manifest（来源/版本/token） | `tests/api/test_v2_asks.py::test_manifest_present_each_call` | specs/agent-loop.md:194 |
| 19 | run 内对话状态簿记（`dialogue`＋`process_notes` 双字段，第二轮调用携带首轮对话） | `tests/domains/test_v2_multi_turn_context.py::test_second_decision_context_carries_first_round_history` | specs/agent-loop.md:195 |
| 20 | 追问续会话（前轮问答/执行台账随追问进上下文） | `tests/domains/test_v2_multi_turn_context.py::test_followup_context_carries_prior_qa_history` | specs/agent-loop.md:196 |
| 21 | 闸拒拒因（负信息）在历史中可见不消失 | `tests/domains/test_v2_multi_turn_context.py::test_gate_refused_line_visible_across_followup` | specs/agent-loop.md:197 |
| 29 | 追问端点会话线程延展（新 run 播种前轮历史） | `tests/api/test_v2_asks.py::test_followup_asks_extend_session` | specs/agent-loop.md:205 |
| 34 | 图装配与路由表集中（业务相位不自行跳转） | `tests/domains/test_v2_agent_loop.py::test_routing_table_centralized` | specs/agent-loop.md:210 |

> 测试文件归属（票注，非规格引文，呈主窗对账）：本票 15 行的测试标识**落既有文件**（`tests/domains/test_v2_four_phase.py`／`tests/domains/test_v2_multi_turn_context.py`／`tests/domains/test_v2_agent_loop.py`／`tests/api/test_v2_asks.py`——`ls` 实测四文件均在册）——与 W1–W4 各票绑新建文件的形态不同：本块验收行是**存量测试改写面**（eng/04 §二原文：「48 个离线文件本质已是特征测试……重写后改接线（import 面从 `appv2.runtime.*` 改指 runtimev2 17 子包）＋ runtimev2 提供等价替身即可复用」＋ §五 织网工序第 2 步「存量改写…… 12 文件黑盒化」）。**旧码测试本批不改**（本批＝阶段 4 拆票；改写属织网②，开工硬条件见「前置」③）。
> 行序缺口说明（票注）：本票行序跳过 5、8–12、14、15、22–28、30–33、35、36——`#` 列三票共用规格表行序，便于 manifest 逐行对账（先例 `RT-W4-06a-answering.md` 行序缺口说明）。
> 跨块登记（票注，呈主窗对账；**不自行增设验收行**）：① 行 17／18／29 的测试标识落 `tests/api/test_v2_asks.py`＝`api` 层文件，而 `api` **不在** eng/03 §二 五波序列的 17 块内（eng/00 §三 原文：17 块＝「业务相位 7 ＋ 公共层 9 ＋ 入口闸族 1」；`api` 是 `specs/modules.md` 既有 7 张卡之一，eng/00 §一 原文：「其余 6 张卡不动」）——「三端点＋SSE 事件桥」（规格 :41 触及表原文）由谁施工、与 `appv2/api/` 存量件（`chat.py`／`bridge.py`／`wire.py`）的关系，呈主窗 manifest 对账；② 规格 :71 原文「state schema 自有（`RunState` 为自有 dataclass，框架只当 schema 消费）」中「框架只当 schema 消费」的**消费形态与框架状态化边界**（哪些字段入图状态、是否经 reducer／通道并入）在本规格无落点——**不可自造**，施工前呈主窗对账。

## 测试网钉（specs/agent-loop.md「与闸的挂钩表」pin 行逐行转抄——本块 5 行，本票承载 3 行，余 2 行归 -01b／-01c）

〔来源：specs/agent-loop.md「与闸的挂钩表」:236–:240，逐行原文；列名同规格「本规格的硬要求｜挂钩｜现状」〕

| 本规格的硬要求（原文） | 挂钩（原文） | 现状（原文） |
|---|---|---|
| 追问播种＝前 run 检查点**终链整链承接**（跨 run 前缀延伸） | 钉 **`pin-23`**（P0） | 待织网（阶段 5） |
| `RunState.messages` 只追加不改写（任意相邻调用互为前缀延伸） | 钉 **`pin-22`**（P0） | 待织网（阶段 5） |
| 相位合同一次性（消费侧重发判定＝追加编排归 `orchestration`＋标记写入归 `bookkeeping.append_contract`——落法真源 `specs/context.md` 挂钩表） | 钉 **`pin-24`**（P1） | 待织网（阶段 5） |

- 分工注（票注，防两头认——三钉各有他块承担的半边，本票只承担**编排面**）：① `pin-23`＝**播种动作面**（本票行 29「追问端点会话线程延展（新 run 播种前轮历史）」）；形状／字段面在 `specs/state.md`（其挂钩表 `:187` 行原文：「追问播种＝前轮终链整链承接（**状态字段面**）」←该块 `::followup_seeds_full_chain`）；检查点读取面在 `specs/persistence.md`。② `pin-22`＝**循环行为面**（本票行 19／20／21 承载：每步整链续写、第二轮携带首轮、前轮台账随追问；`specs/state.md:186` 行原文「循环行为面同钉挂 `specs/agent-loop.md`」）；字段契约面在 `specs/state.md` 行为 4（该块 `::messages_append_only_prefix`）、写入面在 `specs/bookkeeping.md` 行为 7（RT-W3-01a/b/c 行 2／7 已承载）。③ `pin-24`＝**消费侧重发判定面**（追加编排，本票行 16／19 的回路轮承载；`specs/context.md:190` 行原文：「**消费侧重发判定**＝追加编排归 `orchestration`＋标记写入归 `bookkeeping`——context 零合同、零标记、零追加时点」）；标记写入面在 `specs/bookkeeping.md` 行为 8（RT-W3-01a/b/c 行 8 已承载）、常量稳定面在 `specs/prompts.md` 行为 1（RT-W2-04a/b/c 已承载）。
- 本块 pin 行分布（防两处漂移，逐字稿纪律）：本块 5 条 pin 行＝pin-23／pin-22／pin-24（本票 3 行，上表）＋ pin-29（挂起→resume 闭环，落 `RT-W5-01b-orchestration.md`）＋ pin-28（run_id 全盖章／计费对账，落 `RT-W5-01c-orchestration.md`）——**同一 pin 行只在一票逐字转抄**，其余票只写核对关系、不重复转抄（先例 `RT-W4-05b-execution.md` 分票理由原文：「同一 pin 行在两票重复转抄＝两处真源必漂移」）。
- 规格「与闸的挂钩表」其余行（spec gate／人审两行／R5b／R7／R6／R2 人审行／真源引用闸）非 pin 行，按各自「挂钩」列由上述闸与用例承接，本票不转抄。

## 施工要点（specs/agent-loop.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/agent-loop.md:80 | 行为 1 四相位循环 | 每问新建 run：understand 理解后进四相位（clarify→toolmatch→precondition→batch），轮 2/3 只带失败／缺失子问题回炉；每步落 step 记录（类型六值闭世界，相位以 `payload.phase` 标注） |
| specs/agent-loop.md:102 | 行为 2 每步在 `messages` 整链续写 | 每个 LLM 调用发送**整条链**（＝上次链＋尾段）；对话状态双字段＝`dialogue`（自然对话层）＋`process_notes`（过程档案层，有界摘要）；词典层每轮常驻注入、随当轮渲染不入史 |
| specs/agent-loop.md:134 | 行为 6 caliber_key 三态 | 场景词→确定性匹配口径支；无场景词＋取数形→双口径并列（血缘卡两支同载）；无场景词＋阈值判断形→ASK 反问 |
| specs/agent-loop.md:149 | 行为 8 执行器与命令入口（H3）＋图装配与路由（H2） | `ask`／`resume` 是唯一入口、`RunCommand → 执行器 → RunEvent` 为显式接缝；组合图执行由本块驱动（命令进、事件流出），业务相位不自驱；节点注册／条件边／路由表在本块**一处集中** |
| specs/agent-loop.md:157 | 行为 9 run 状态机 | running→waiting_ask→（resume）→running→completed/failed；追问＝会话线程新轮、前轮须 completed（404/409 开流前错误包） |
| specs/agent-loop.md:119 | 行为 3 发射判据（**不入程序验收面**——规格原文「本行为不入程序验收面」） | 「能不能锚定／要不要反问」由模型侧产出，程序只按结论分派；本票不得为其增设断言（增设＝改规格，回设计仓） |
| specs/agent-loop.md:53 | 接口定义 三形态 | `AskRequest` 三形态（②③互斥，同在场＝409）：①仅 question＝提问；②`resume_run_id`＝断线重连；③`question＋followup_run_id`＝追问续会话（前轮须 completed） |
| specs/agent-loop.md:59 | 接口定义 事件枚举 | 九类闭世界 `step/text/tool/observation/ask/verdict/citation/notice/blackbox`（真源 `synth/S6-事件与帧目录.md`）——本块只按闭世界发帧，类型取值真源在 `specs/transport.md` |
| specs/agent-loop.md:168 | 不降级与静默禁令 合法降级路径 | **合法降级路径：无**（编排层不自降级；图执行器不可用时按 fail-closed 收束为 `failed`，**不产出半成品答案**） |

结构锚：specs/agent-loop.md:46–:67 接口定义（`AgentRuntime.ask/resume`＋`AskRequest`／`AskChoice`／`RunHandle` 三形状＋四端点与错误码；`cursor`＝**全流单调**断线游标、重放不位移；公开接口真源在 `specs/modules.md` `## orchestration` 卡，本处只做本功能视角的细化）；:69–:76 框架与依赖红线（框架只许本模块内部／模型调用发起面＝`bookkeeping.call_model` 单点／只经 `tools` 公开面／只经 `transport` 包根发帧——R2 不覆盖本块故登记人审／禁手写替代）；:214–:221 依赖与风险（LangGraph checkpointer 的 PG saver 与 V1 表共存——新表前缀 `agent_v2_` 隔离，归 -01c 行 27；历史 token 预算截断策略失当会挤占词典层常驻块——截断显式进 Manifest 可查，本票行 13 承载）；:166–:171 不降级与静默禁令（三态落库／挂起／预算触界／审计都必须产生机读信号；**不许自述完成**——提交完成的是本块）。规格「与闸的挂钩表」末行（**人审**，:241）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。
本块不涉面（防一头两认，逐条指出归属票）：行 5（前置条件机零 LLM 双证扫描）、行 23–25（verify 改写／矛盾分源／预算触界收敛）、行 27（挂起态跨进程恢复／checkpoint saver 组合）、行 30–33（只读／三态落库／审计／身份缝）、行 35–36（边界集／保留集）归 `RT-W5-01c-orchestration.md`；行 8–12、14、15、22、26、28（挂起恢复／事件通路／帧批次）归 `RT-W5-01b-orchestration.md`。

## 织网义务（eng/04-测试网设计.md §三 归本块行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单——表内明写归本块的行〕

> | B2 | `_ROUTES` 路由表逐项（intent→节点）＋ `observe_node` 回流路由（tests/ 零命中） | 逐 intent→节点钉＋回流边界钉（对应 `orchestration`） | 高 |

- 归块注：B2 是 §三表内**明写**「对应 `orchestration`」的行（严重度「高」）——钉法＝逐 intent→节点钉＋回流边界钉；钉面落本票行 1（四相位路由拓扑）与行 34（图装配与路由表集中）——两张钉子同守同一条规约：路由表一处集中、相位不自行跳转。
- 关联行（逐字转抄落他票，本票不重复）：B5（帧协议级时序）与 B6（挂起恢复多场景）两条关联行逐字转抄落 `RT-W5-01b-orchestration.md`「织网义务」节；B3（H8 预算四限额边界）关联行逐字转抄落 `RT-W5-01c-orchestration.md`（其收敛半面＝该票行 25）；B1（公共位与结果归一，明写归 `bookkeeping`）已由 `RT-W3-01a/b/c-bookkeeping.md` 逐字转抄，本票不另抄。
- 本票织网义务＝① B2 路由表逐项钉（织网工序第 3 步「盲区补钉」，与 W1–W4 施工可并行——eng/04 头注）；②「测试网钉」3 行对应用例落网（pin-23／pin-22 为 P0 承重钉；三钉各有他块半边，本票只落编排面）；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」15 行逐行实现为对应既有测试文件用例并全绿（`tests/domains/test_v2_four_phase.py` 8 行、`tests/domains/test_v2_multi_turn_context.py` 3 行、`tests/api/test_v2_asks.py` 3 行、`tests/domains/test_v2_agent_loop.py` 1 行），测试标识与规格列逐字一致（`#` 保留规格表行序 1–4、6、7、13、16–21、29、34）；
- 「测试网钉」3 行对应用例在场且绿（pin-23／pin-22 为 P0 承重钉；本票不重复转抄 pin-29／pin-28）；
- 骨架与公开面按卡面签名（`AgentRuntime.ask(q: AskRequest) -> RunHandle`／`AgentRuntime.resume(run_id: str, choice: AskChoice) -> RunHandle`）＋四形状齐（规格 :51–:57），框架类型零出现在公开面签名；
- 路由表集中单点：`::test_routing_table_centralized` 绿——跳转决策零散落相位（AST／grep 断言：路由表只在本块一处）；
- 边界闸 R5／R5b／R6／R7 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；「只经 `transport` 包根」与「禁手写替代」两面按规格挂钩表原文走**人审**（本票不设替代闸）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W5-01a 完成，产物 `appv2/runtimev2/orchestration/`（骨架＋图装配＋路由表＋命令受理三形态＋四相位链路集成），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
