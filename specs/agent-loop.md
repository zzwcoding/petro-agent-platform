# V2 问答主链路（agent loop＝ReAct＋四相位子任务图终态）

状态: 已定稿
来源: docs/prd.md §③、specs/modules.md `orchestration`/`understanding`/`clarification`/`tool_matching`/`preconditions`/`execution`/`answering`/`verification`/`context`/`persistence`/`api`/`tools` 卡、ADR-0004（ReAct 重构）、ADR-0005（子任务图＋前置条件机，含增补）、ADR-0006（多轮对话上下文）、ADR-0007（重写运行时 17 块划分，本表模块名随阶段 2 改名）
> 本文为 V2-36 终态重写（2026-10-09），取代前版「六步流水线」条款（repair 链／max_steps 8
> 预算／understand-plan-tool-observe-verify-answer 六类型——旧测试标识随旧语义一并退役，
> 现行测试标识见验收表）。现行实现真源：`appv2/runtime/graph.py`（节点与路由）、
> `appv2/tools/precondition.py`（前置条件机）、`appv2/runtime/subtask.py`（QuestionGroup）。

## 目标

用户向 `/api/v2/chat/asks` 提一个问题，系统以**有界自主循环**推理作答：
一轮＝四相位（业务澄清→工具匹配→前置条件机→批量执行＋汇总），整循环每用户输入
周期 ≤3 轮——轮 1 得部分答案，轮 2/3 只带失败/缺失子问题回炉；LLM 出语义
（澄清/分解/提议），代码出判定（前置条件机零 LLM）；全程事件可见、答案带
fail-closed 引用、中途可澄清/审批挂起并可恢复。替代 V1 十七站瀑布＋无状态
LLM 判断孤岛。

## 不做什么

不做 Memory/跨会话个性化（追问续会话除外——ADR-0006 会话线程承接，非个性化记忆）；
不做自进化；不做写操作；不做 V1 端点的任何改动；
核验不替代引擎侧 citation fail-closed 校验（那是确定性 Middleware，本 spec 之上叠加）；
schema 校验失败不做自动 repair——拒因回喂 LLM 重发射（ADR-0004 拍板 2）。

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| orchestration | 新增 | 四相位循环与路由/命令受理与挂起恢复（LangGraph 实现） |
| preconditions | 新增 | 前置条件机调度（闸件本体在 `tools` 侧） |
| context | 新增 | Context Builder＋消息历史簿记 |
| verification | 新增 | Verifier 核验收口 |
| persistence | 新增 | run／step 持久化与恢复 |
| api | 新增 | 三端点＋SSE 事件桥（asks 三形态：提问/重连/追问续会话） |
| tools | 新增 | loop 经 ToolRegistry 调五工具（本 spec 只消费其公开接口） |

## 接口定义

```python
# runtime 公开接口（真源在 modules.md runtime 卡，此处细化）
class AgentRuntime:
    async def ask(self, q: AskRequest) -> RunHandle: ...
    async def resume(self, run_id: str, choice: AskChoice) -> RunHandle: ...
# AskRequest = {question: str, actor: Actor}
# RunHandle = {run_id: str, stream: AsyncIterator[SseEvent]}
# 事件枚举: step/text/tool/observation/ask/verdict/citation/notice（八类闭世界）

POST /api/v2/chat/asks                 200 → text/event-stream（首帧 run_id）
    入参三形态：question 提问｜resume_run_id 重连｜question＋followup_run_id 追问续会话
POST /api/v2/chat/runs/{run_id}/resume 200 → text/event-stream
GET  /api/v2/chat/runs/{run_id}        200 → {status, steps, manifest_digest, pending_ask?}（pending_ask＝挂起帧投影，仅 waiting_ask 在场——V2-78 刷新还原面）
GET  /api/v2/chat/runs?limit=N        200 → [{run_id,question,status,answer,followup_of,created_at,updated_at}]（V2-73 最近任务读口，created_at 降序；followup_of＝追问链前轮——V2-74 对话任务分组，空串＝链根）
错误：400 参数非法｜401 身份缺失｜404 run 不存在｜409 run 非挂起态不可 resume（重连/追问互斥同 409）
```

## 行为约定

1. **四相位循环**（ADR-0005，生产装配 `four_phase=True`）：每问新建 run，
   understand 理解后进四相位——
   ①**业务澄清（clarify）**：LLM 带 Skill 指南发射三动作闭世界 `discover｜decompose｜ask`；
   discover＝钻取（semantic_query/doc_retrieve/table_schema），decompose 产出
   **QuestionGroup**（subtasks[{id/question/ledger_notes/tool/chain}]，子问题上限 ≤4，
   ledger_notes 必填——从词典层注入块逐字转抄的台账注释）；ask＝反问挂起；
   ②**工具匹配（toolmatch）**：LLM 逐子问题提议工具/链（data→data_query、
   knowledge→doc_retrieve，data 链必带 plan、knowledge 链必带 retrieval_need），
   与问题组**闭世界对账**（组内每子问题恰一条匹配，缺/多/未知 id 均拒）；
   ③**前置条件机（precondition）**：纯固定代码零 LLM（铁律——LLM 无权判定），
   逐子问题过闸判四态：`pass｜blocked_ask→ASK 挂起｜blocked_refuse→子问题如实拒答｜
   note 注记随行`；闸项＝V1 语义移植：禁用词（带替代词）、新鲜度窗、在册绑定态、
   外表越集、单井支持性、合法口径（caliber_key 三态，见约定 6）；其中「data 链＋
   指标在册（F7 归一后）＋绑定闸拒（在册未绑定 agg）」自 V2-43 起＝**换链回炉态**：
   不直答不执行——携拒因＋改链 hint＋「换链提议」标记回炉①澄清相位（复用失败子集
   回炉机制，占一轮、不占 ask 预算/不挂起），一次为界——坚持 data 链同参再触发＝
   blocked_refuse 直答终局（不环，同参指纹在 chain_switch_marks 簿记）；
   ④**批量执行＋汇总（batch）**：子问题组执行＋观察汇聚，LLM 整合全组子结果
   （逐子问题引用）→ verify 核验收口。
   每步落 step 记录（类型六值闭世界 decision/discover/execute/observe/verify/answer；
   相位以 payload.phase=clarify/toolmatch/precondition/batch 标注——过程态簿记留痕
   agent_v2_step；INV-5 责任账唯一写口 security.audit，见 specs/infra.md 行为约定 3）。
2. 模型每次调用前经 Context Builder 确定性编译（**多轮消息历史簿记**——ADR-0006；
   **V2-79a 三层分离修订**（tickets/v2/V2-79-对话状态重构方案.md；ADR-0006 增补
   修订随设计仓，本行为真源以方案为准）：混装消息历史退役，对话状态＝`dialogue`
   （自然对话层——user 原话/assistant 终稿/澄清审批回收原文；禁任务书/指令/
   过程原话/注记前缀）＋`process_notes`（过程档案层——[{phase,title,digest}]
   有界摘要每条 ≤200 字）双字段；编译契约＝[system]＋dialogue 截断＋当前轮，
   任务书/指令/材料**现拼现用、用完即弃、不入史**；执行台账以
   「参数 → 结果：N 行／闸拒（拒因）」形落 process_notes；历史增长带 token
   预算/截断显式进 Manifest）。词典层**每轮常驻注入**（拍板 a 的
   C2 追认落法）：clarify/toolmatch 相位把台账全量＋别名＋结构卡直接编进上下文
   （Manifest 记 ledger_dump 族来源行），常驻块随当轮渲染、不入史防 token 放大——
   "开局已给全台账，禁猜词敲门"，semantic_query 定位转为钻取。
   调用产出 Manifest（source_type/source_id/version/trust_level/selected_reason/
   token_count/transform）随 step 存档。
3. **发射判据**（治"数据路径退化/犹豫空转"——ADR-0005 立项根因）：窗可锚定＝禁 ask；
   时间词按窗词锚定表可解析即锚定发射，无时间词→默认近 30 天＋注记；台账命中＋窗
   已定＝禁再 discover（直发分解）；ask 仅限两种白场——无场景词＋阈值判断形的口径
   反问、目标/对象/口径真歧义（澄清合同收窄）；越集→审批。schema 校验失败＝拒因
   回喂重发射，**无 repair**；decision 出口同参重投闸保留，定位降为确定性兜底
   （主力是过程摘要渲染——V2-79c；V2-79a 三层分离后原「消息历史簿记」承载面
   退役）。
4. 工具只经 ToolRegistry.call；返回 status=ask 时 run 转 waiting_ask 挂起，事件流发
   ask 帧后正常收束；resume 带选择续跑（INV-2：全程只读）。外表越集审批态落
   **ToolContext.approved_tables**（不走引擎 approved_tables、不重排计划——A2 裁决）；
   前置条件机 blocked_ask（越集审批/口径反问）与引擎侧 ask 同走挂起—恢复链。
5. 核验收口（verify）：逐条检查阐述草稿的断言有 Observation 支撑；无支撑断言改写为
   "未找到/材料未披露"并出 notice——禁止无据断言进答案（INV-1、INV-4；表格行/
   血缘卡/fragment 承载豁免随 P-024b 口径继承）。
6. **caliber_key 三态**（B5 裁决）：场景词（月报/正式/化验）→确定性匹配口径支；
   无场景词＋取数形→双口径并列（血缘卡两支同载）；无场景词＋阈值判断形→ASK 反问
   （用户已答才代选）。plan 带 caliber_key 做合法口径校验，QueryPlan 域面零改动。
7. 预算闸（触界即收敛——交付已取得观察材料（未核实的直排标注"未及核验"，非断言
   不违反 INV-1）＋notice 明示未完成项，不得静默截断）：
   - **轮数**：每用户输入周期 ≤3 轮（轮＝LLM 决策周期；clarify 发射 discover 钻取
     不占轮，decompose 占轮；ASK 挂起等人工不计轮；澄清回收（resume）重置轮预算
     合法——rounds=0）；轮 2/3 只带失败/缺失子问题＋拒因回炉①，成功子问题结果
     保留不重跑（subtask_results 簿记）。
   - **发现预算**：全 run discover ≤10（Owner 拍板放宽原 3-4）；预算拒免轮例外
     只留首次——连续第 2 次起转占轮（自旋收敛闸）。
   - **单段时限 300s**（挂起等人工不计时、不累计跨段——计步计时均按段）；
   - **单工具超时 30s**；
   - **discover 计数埋点**：每次钻取落 step payload（次数/查询词指纹/命中数/命中
     形态 no_hit|rows:N|empty）供跑批分析（no_hit 循环回归判定面）。
8. run 状态机：running→waiting_ask→（resume）→running→completed/failed；
   引擎事件外置持久化，断线凭游标续传，进程重启后可恢复 waiting_ask 态（resume
   可达）；追问（followup_run_id）＝会话线程新轮——前轮消息历史（含问答/执行台账）
   随追问进新 run 上下文，前轮须 completed（404/409 开流前错误包）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 四相位路由拓扑（clarify/toolmatch/precondition/batch 入图、回决策边重定向） | `tests/domains/test_v2_four_phase.py::test_four_phase_routing_topology` |
| QuestionGroup schema（子问题 ≤4 上限/ledger_notes 必填/chain-tool 一致） | `tests/domains/test_v2_four_phase.py::test_question_group_schema_happy_and_caps` |
| 工具匹配与问题组闭世界对账（缺/多/未知 id 拒） | `tests/domains/test_v2_four_phase.py::test_tool_match_closes_world_against_group` |
| 前置条件机四态分支（pass/blocked_ask/blocked_refuse/note） | `tests/domains/test_v2_four_phase.py::test_precondition_four_states_reachable` |
| 前置条件机零 LLM（AST＋import 双证扫描） | `tests/domains/test_v2_four_phase.py::test_precondition_and_parse_layers_are_zero_llm` |
| caliber_key 三态（场景词/双口径并列/阈值反问） | `tests/domains/test_v2_four_phase.py::test_precondition_caliber_three_forms` |
| 澄清合同收窄（窗可锚定＝禁 ask，直发分解零挂起） | `tests/domains/test_v2_four_phase.py::test_four_phase_anchorable_window_skips_ask_delivers_degrade` |
| 阈值判断形口径反问仍挂起→resume 回喂→续跑收口 | `tests/domains/test_v2_four_phase.py::test_four_phase_clarify_ask_threshold_form_still_suspends_and_resumes` |
| 失败子集回炉（成功子结果不重跑断言） | `tests/domains/test_v2_four_phase.py::test_four_phase_refurnace_carries_failed_subset_only` |
| 3 轮部分续找语义（轮 1 部分答案→轮 2/3 带失败子集） | `tests/domains/test_v2_four_phase.py::test_four_phase_three_rounds_partial_answers` |
| discover 全 run ≤10＋计数埋点落 payload | `tests/domains/test_v2_four_phase.py::test_four_phase_discover_budget_ten_and_taps` |
| 预算拒免轮例外只留首次（连续第 2 次转占轮） | `tests/domains/test_v2_four_phase.py::test_four_phase_clarify_budget_reject_spin_gate` |
| 词典层台账常驻注入（ledger_dump 族 Manifest 可查） | `tests/domains/test_v2_four_phase.py::test_four_phase_ledger_dump_round1_injection` |
| 越集审批挂起→批准→前置条件机重判→批量执行 | `tests/domains/test_v2_four_phase.py::test_four_phase_extable_approval_resume_precondition_chain` |
| 引擎侧 ask 挂起→resume→批量续跑收口 | `tests/domains/test_v2_four_phase.py::test_four_phase_engine_ask_resume_batch_chain` |
| 四相位端到端剧本（澄清→分解→过闸→批量→汇总收口） | `tests/domains/test_v2_four_phase.py::test_four_phase_end_to_end_scripted` |
| 提问→事件流步序（understand→四相位→answer 次序） | `tests/api/test_v2_asks.py::test_loop_step_sequence` |
| 每个模型调用 step 落 Manifest（来源/版本/token） | `tests/api/test_v2_asks.py::test_manifest_present_each_call` |
| run 内消息历史簿记（第二轮调用携带首轮历史） | `tests/domains/test_v2_multi_turn_context.py::test_second_decision_context_carries_first_round_history` |
| 追问续会话（前轮问答/执行台账随追问进上下文） | `tests/domains/test_v2_multi_turn_context.py::test_followup_context_carries_prior_qa_history` |
| 闸拒拒因（负信息）在历史中可见不消失 | `tests/domains/test_v2_multi_turn_context.py::test_gate_refused_line_visible_across_followup` |
| 工具返回 ask→run 挂起→GET 状态 waiting_ask→resume 完成 | `tests/api/test_v2_asks.py::test_ask_suspend_resume` |
| 断言无 Observation 支撑→verify 改写为"未找到"＋notice | `tests/domains/test_v2_agent_verify.py::test_unsupported_claim_rewritten` |
| 矛盾两来源→答案分源列明各带 citation（INV-4） | `tests/domains/test_v2_agent_verify.py::test_contradiction_split_source` |
| 预算触界→收敛答案＋未完成项 notice，无静默截断 | `tests/domains/test_v2_agent_loop.py::test_budget_termination` |
| 断线游标重连→事件不重复不遗漏 | `tests/api/test_v2_asks.py::test_sse_cursor_resume` |
| run 挂起态跨进程恢复（checkpoint 落 PG） | `tests/domains/test_v2_agent_loop.py::test_run_recover_after_restart` |
| resume/追问错误路径（404/409/互斥 409） | `tests/api/test_v2_asks.py::test_resume_error_paths` |
| 追问端点会话线程延展（新 run 播种前轮历史） | `tests/api/test_v2_asks.py::test_followup_asks_extend_session` |
| 全程业务事实零写（run 簿记表 agent_v2_* 除外，INV-2） | `tests/domains/test_v2_agent_loop.py::test_readonly_inv2` |

## 依赖与风险

- 依赖：`tools` 五工具接口（specs/tools.md）；Skill 指南＝ontology 资产
  （OntologyGuideProvider——含发射判据与澄清合同；DefaultGuideProvider 已退役，
  create_app 组合根接正式指南）；infra 复制票（gateway completer/时钟/db）。
- 风险：LangGraph checkpointer 的 PG saver 与 V1 表共存（新表前缀 agent_v2_ 隔离）；
  剧本化 completer 按消息历史形态驱动（多轮 replay）；历史 token 预算截断策略
  失当会挤占词典层常驻块（截断显式进 Manifest 可查）。
