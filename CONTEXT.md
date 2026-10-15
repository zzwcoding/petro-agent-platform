# CONTEXT.md · petro-agent-platform

> 共享术语表（SDD 产物；V1 资产术语以 ontology/ 与 teach 合同册为准，此处只列 V2 新增/变义）。
> 状态：随 V2 阶段 1 逼问持续更新。

## 语义核心（不变量原文唯一出处）

- INV-1 无引用不给数：答案中的每个数/事实断言必须有 fail-closed 校验过的引用，失锚断言剥除并计数。
- INV-2 只读边界：agent 全部工具只读；SQL 经只读账号＋白名单 Schema；无任何写动作。
- INV-3 权限谓词优先：用户筛选条件顶不掉权限/口径谓词（沿用 V1 N7.4b 语义）。
- INV-4 矛盾分源：多来源矛盾数据必须分源列明（各标出处）或显式声明歧义；禁止无出处调和/混写。
- INV-5 审计闭环：每次回答留痕（谁/何时/何输入/何输出/依据口径），审计责任账唯一写口 security.audit（落 audit_log 表，action 恒 `agent_v2.*` 前缀）；run/step 簿记＝过程态留痕，与责任账分工不互替（specs/infra.md 行为约定 3 口径——V2-20 对齐）。

## V2 术语

| 术语 | 定义 |
|---|---|
| **agent loop** | V2 核心执行结构：有界自主循环——一轮＝四相位（业务澄清→工具匹配→前置条件机→批量执行＋汇总），每用户输入周期 ≤3 轮、失败子集回炉部分续找（替代 V1 十七站瀑布） |
| **decision** | step 六值之一：LLM 决策发射步；轮＝LLM 决策周期，模型只许在轮内出语义动作（ReAct 面 discover/execute/answer，四相位面 clarify 的 discover｜decompose｜ask 与 toolmatch 匹配），发射经 schema 校验，失败拒因回喂重发射（无 repair） |
| **discover** | 钻取发现动作：只读探查（semantic_query/doc_retrieve/table_schema），全 run ≤10 次（预算拒不占轮——免轮例外只留首次，连续第 2 次起转占轮）；每次落计数埋点（次数/查询词/命中形态）进 step payload |
| **execute** | 执行动作：子问题过前置条件机后的确定性工具执行；四相位下批量进行（batch 相位汇聚观察），成功子问题结果保留不重跑 |
| **QuestionGroup** | 四相位①业务澄清的发射产物（子任务图）：subtasks[{id/question/ledger_notes/chain}]，子问题上限 ≤4，ledger_notes 必填（从词典层注入块逐字转抄的台账注释）；LangGraph 校验单点（runtime/subtask.py）。**不含 `tool`——选工具由②匹配相位产出**（Owner 2026-10-15 裁定；见 `SubtaskMatch`） |
| **前置条件机** | 纯固定代码闸件（tools/precondition.py，零 LLM）：逐子问题过闸（禁用词/新鲜度窗/在册绑定态/外表越集/单井支持性/合法口径）判四态——pass｜blocked_ask→ASK 挂起｜blocked_refuse→子问题如实拒答｜note 注记随行；铁律＝LLM 出语义，代码出判定 |
| **发射判据** | 澄清相位的发射纪律（Skill 指南承载，治"犹豫空转"数据路径退化）：窗可锚定＝禁 ask（无时间词默认近 30 天＋注记）；台账命中＋窗已定＝禁再 discover；ask 仅限两白场——无场景词阈值判断形的口径反问、目标/对象/口径真歧义 |
| **Skill 指南** | LLM 相位的处理指南＝ontology 资产（与台账同治理）：发射判据/澄清合同/工具边界随指南装载进 clarify/toolmatch 相位；OntologyGuideProvider 供装，DefaultGuideProvider 占位已退役 |
| **Harness 编排层** | 持有任务语义的代码层（model 看到什么/能调什么/何时停/交付前过哪些验证），与 Runtime 解耦 |
| **工具（Tool）** | agent 可调用的确定性能力：semantic_query／data_query／doc_retrieve／graph_query／table_schema（结构卡发现面），全只读 |
| **Skill** | data_query 的定性——V1 六站链降格为可验证方法资产（模板装配＋三闸＋血缘卡封装在工具内） |
| **Observation** | 工具返回的统一结构：值/来源/版本/时效/适用范围（Knowledge Evidence 形） |
| **SubtaskMatch** | 四相位②工具匹配的产物：`{id/tool/chain/plan/retrieval_need/caliber_key}`，与子问题**一一对应**（恰配一条）；`tool`／`chain` 均为闭世界；拒因回喂重配、不自动修补（Owner 2026-10-15 裁定：**选工具归匹配出**） |
| **计划（plan）** | loop 中模型产出的查询意图（指标槽/时间窗/条数/排名…），经确定性校验后成为 Task State；四相位下随子问题在 toolmatch 相位收口（可携 caliber_key 场景口径支） |
| **Context Manifest** | 每次模型调用的输入账目：来源/版本/信任级/选中理由/token/变换——"模型为什么看到这个" |
| **ASK 帧** | 人在回路挂起点：clarify 反问（阈值判断形口径/真歧义白场）或外表越集审批（批准/驳回）；ASK 挂起不占轮 |
| **核验步（Verifier）** | loop 内答案交付前检查：每个断言有 Observation 支撑；无支撑→"未找到"，禁止编造 |
| **Knowledge 化** | sem_* 台账从管理面 CRUD 升级为 agent 可消费的 Knowledge（Evidence 结构读接口） |
| **run / step** | 一次提问的执行实例 / loop 内一步（step 类型六值闭世界 decision/discover/execute/observe/verify/answer，四相位以 payload.phase=clarify/toolmatch/precondition/batch 标注） |

## V1 沿用术语（不变义）

台账（sem_*）、血缘卡（五要素）、新鲜度闸、在册未绑定降级、fail-closed citation、
合同册（teach 真源）、B6 出口、四层边界（B1–B16）。
