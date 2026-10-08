# ADR-0002 · Harness 编排层采用 LangGraph（带三红线）

- 日期：2026-10-08
- 背景：阶段 2/3 间框架决策——自写有界 loop＋中断恢复（约 400~600 行状态机）vs 采用 LangGraph。
- 决策：**采用 LangGraph**，限定为 `appv2/runtime` 模块的实现技术。
- 理由：StateGraph＋条件边正中 loop 原语；interrupt/Command(resume) 正中 ASK 挂起与 /resume 恢复两个硬需求；checkpointer（PG saver）落既有 PostgreSQL，避免自造 Durable Execution 状态机的高危坑（白皮书 8.2）。
- 三条红线（进边界规则与票面验收）：
  1. langgraph/langchain 只许在 `runtime` 内部 import，禁止渗入 api/tools/engines 与 SSE 契约；
  2. 全部 LLM 调用经自写 ChatModel adapter 走 `gateway.complete`（B6 归因/预算/审计保留），禁止 langchain 自带 provider 直连；
  3. run/step 状态 schema 自有（step 类型/Manifest/ASK 帧自定义），checkpointer 仅作存储机制。
- 代价记录：依赖树进 lockfile 与 import-linter 契约，CI 时长略增；框架升级跟随 langgraph 节奏。
