# V2-06 · runtime 编排层（LangGraph loop）

状态: 实现中（2026-10-08，P-006 已派发·预挂中途审查）
Touches modules: `runtime`
阻塞: V2-05｜被阻塞: V2-07
（跨域大改票：本票建立 V2 核心执行语义，预挂中途审查拍——骨架可跑后先审一轮再继续细化）

## 任务

实现 `appv2/runtime/`：LangGraph StateGraph 六步 loop（understand/plan/tool/observe/verify/answer）
＋PG checkpointer＋Context Builder/Manifest＋Verifier 核验步＋预算三闸＋RunCommand seam。
〔来源：docs/adr/0002-langgraph框架决策.md 三红线；docs/adr/0003-并发模型不上MQ.md RunCommand seam〕

先读: specs/agent-loop.md 全文；docs/adr/0002、0003；specs/tools.md（ToolResult/AskFrame 契约）

框架红线: **langgraph 必须真引入真使用**——pyproject 依赖出现且 StateGraph 真的承载 loop；
LLM 必经自写 ChatModel adapter 走 appv2 gateway.complete（caller 归因保留），禁止 langchain 自带 provider 直连
边界红线: langgraph/langchain 只许出现在 `appv2/runtime/**`；state schema 自有（checkpointer 仅存储）；
依赖 `appv2.tools`（公开接口）＋`appv2.infra`；不得 import `app.**` 及 knowledge/query/retrieval

验收: 以下逐条对应 specs/agent-loop.md「验收测试」表 runtime 侧条目——
- runtime 侧五条全绿：budget_termination / run_recover_after_restart / unsupported_claim_rewritten /
  contradiction_split_source / readonly_inv2（含 plan_repair_clarify_resume 的端到端六条归 V2-07）
- 本票定稿符号（票面点名）：AgentRuntime.ask/resume、RunHandle、AskRequest、AskChoice、
  ContextBuilder.compile、CompiledContext、RunState
- 剧本化 completer（caller 分流、多轮 replay）就位
- agent_v2_run/agent_v2_step 新表迁移文件（前缀隔离 V1 表）
- 三红线自查：runtime 外零 langgraph import（扫描）／ChatModel adapter 单点／state schema 自定义

回报: 完成后回总窗口："V2-06 完成（含中途审查一轮），产物 appv2/runtime/，偏差: 有/无，测试: pytest 输出摘要"
