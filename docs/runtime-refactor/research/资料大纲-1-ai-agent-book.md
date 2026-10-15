# 资料大纲 1 —— ai-agent-book（深入理解 AI Agent：设计原理与工程实践）

## 0. 覆盖范围

本大纲覆盖 `/Users/divh/Downloads/资料/技术书籍/ai-agent-book/ai-agent-book/`（该书仓库根目录）下的全部 `.md` / `.txt` 文件，共 1261 个（`.md` 930 + `.txt` 331，不含 `.git`）；其中排除中译多语言 README、法律语料（`chapter3/agentic-rag/laws/`）、实验运行产物（runs/validation/outputs 等）与第三方复现源码自带文档后，实质文档约 429 个。正文为 `book/chapter1.md ~ chapter10.md`，配套实验在 `chapter1 ~ chapter10/` 各子目录。外层 `实验/ai-agent-book/` 目录内无 `.md`/`.txt` 文件，未纳入。本大纲只列与「运行时重写」10 个主题相关的部分，非全量清单。

> 说明：本书已升级到 2.0 版，正文 `book/chapterN.md` 与 `chapterN/` 实验目录一致采用新编号（第 6 章＝交互、第 7 章＝评估、第 9 章＝持续进化）；仓库 `index.md` 是旧编号，勿以它为准。以下「相对路径」均从 `ai-agent-book/` 根起算。

---

## 1. 智能体流程编排（谁先谁后、自主循环 vs 线性流水线）

- `book/chapter1.md` — 讲清 Agent = LLM + 上下文 + 工具、ReAct 循环、Harness 五要素，并专节对比「编排模式：工作流与自主」（第 370 行起）与「从提示工程到 Loop 工程」；本仓运行时分层与循环设计的首要对照材料 — 高
- `book/chapter10.md` — 多 Agent 协作的分类框架（上下文是否共享、协作拓扑：对等 / 管理者 / 去中心化）与失败模式，适合评估「单 Agent 流水线 vs 多子 Agent」的取舍 — 中（亦相关主题 9）
- `chapter1/README.md` — 第 1 章实验索引与正文指针，快速定位本章可跑示例 — 中
- `chapter1/context/README.md` — 上下文感知 Agent 与消融实验，演示去掉某组件后编排行为如何变化 — 中
- `chapter10/book-translation/README.md` — 图书翻译 Agent 的编排模式实例（orchestration pattern 端到端串接） — 中
- `chapter10/staged-system-prompt/README.md` — 按「执行阶段」切换系统提示词的归档示例，与「9 段流水线分段控制」思路直接对应 — 中
- `chapter10/parallel-web-research/README.md` — 并行研究任务的分发/汇总编排示例 — 低
- `chapter10/multi-role-transfer/README.md` — 多角色切换的两种实现（分角色 Agent vs 单 Agent 换提示）对比 — 低

## 2. 路由 / 意图判定（一句话该不该走完整流程）

- `book/chapter1.md` — 「如何选择模型」（第 353 行）与「编排模式：工作流与自主」（第 370 行）给出「先用最小流程、必要时才升级」的判定思路 — 高
- `chapter7/model-action-threshold/README.md` — 固定 harness 下测「模型在什么阈值才该行动/该直接回答」，是「该不该走完整流程」的可量化判定实验 — 高
- `book/chapter4.md` — 「工具太多怎么办：层次化组织与主动工具发现」（第 133 行）讲工具路由与按需加载 — 中（亦相关主题 5）
- `chapter4/active-tool-selection/README.md` — 主动工具选择实验，对应「给子问题配工具」的匹配段 — 中（亦相关主题 5）
- `book/chapter7.md` — 「评估驱动的模型选型」（第 558 行）与「模型的行为策略」（第 583 行）可用于路由模型/策略的选型依据 — 中（亦相关主题 10）

## 3. 入口安全拦截（注入 / 越权 / 只读不变量）

- `book/chapter2.md` — 「提示注入：上下文安全的核心威胁」（第 722 行），注入如何绕过系统提示与工具权限 — 高
- `chapter2/prompt-injection/README.md` — 提示注入攻防实验，可直接复现攻击/防御基线 — 高
- `book/chapter1.md` — 「护栏与安全性」（第 456 行）讲 Agent 护栏设计（对应本仓「安全闸」段） — 高
- `chapter9/harness-safety-gate/README.md` — 由用户反馈触发的高风险操作确认门禁，正对应「要不要审批」的前置检查 — 高
- `chapter5/permission-embedded-data-objects/README.md` — 权限内嵌的数据对象（把权限放进数据本身），防止越权读写的可借鉴模式 — 中（亦相关主题 5）
- `chapter3/log-sanitization/README.md` — 日志脱敏，涉及留痕时如何避免泄露敏感字段 — 中（亦相关主题 8）
- `.local/security-scan/SECURITY-EXPERIMENTS.md` — 该书全部实验的安全扫描总览，可作安全实验地图 — 低

## 4. 上下文与记忆管理（对话历史、长对话压缩、缓存）

- `book/chapter2.md` — 本主题主教材：KV Cache 友好的上下文设计（第 435 行）、上下文压缩策略（第 983 行，含「分层压缩」与「隔离优于压缩：子 Agent 上下文隔离」） — 高
- `chapter2/context-compression/README.md` — 多种上下文压缩策略的对比实验 — 高
- `chapter2/kv-cache/README.md` — KV Cache 与错误上下文管理模式的演示（缓存作为架构约束） — 中
- `book/chapter3.md` — 「用户记忆系统」（第 15 行）与「RAG 基础：构建知识获取管道」（第 243 行），跨会话记忆与外部知识接入 — 高
- `chapter3/user-memory/README.md` — 用户记忆系统实现，跨轮次记住用户与偏好 — 高
- `chapter3/user-memory-evaluation/README.md` — 用户记忆评估框架（记忆是否被正确使用） — 中（亦相关主题 10）
- `chapter3/mem0/README.md`、`chapter3/memobase/README.md` — 两套记忆中间件方案与手写记忆的对照 — 中
- `chapter3/agentic-rag/README.md` — Agentic RAG 系统（检索由 Agent 自主驱动而非固定流水线） — 中
- `chapter3/structured-index/README.md` — 结构化索引（RAPTOR 与 GraphRAG），长文档/层级知识的组织与检索 — 中
- `chapter3/retrieval-pipeline/README.md` — 混合检索流水线与神经重排序 — 中（亦相关主题 6）
- `chapter3/contextual-retrieval/README.md` — 上下文感知检索（切片时补上下文），提升检索命中 — 中
- `chapter3/dense-embedding/README.md`、`chapter3/sparse-embedding/` — 稠密/稀疏向量检索服务实现 — 低

## 5. 工具调用与受控执行

- `book/chapter4.md` — 本主题主教材：工具分类、设计通用原则、工具生态（MCP 与 Skill Hub）、层次化组织与主动工具发现、感知/执行/协作三类工具 — 高
- `chapter4/README.md` — 第 4 章实验索引 — 中
- `chapter4/execution-tools/README.md` — 执行工具 MCP 服务器（受控执行的参考实现） — 中
- `chapter4/active-tool-discovery/README.md` — 主动工具发现（模型原生按需发现工具） — 中
- `chapter4/perception-tools/README.md`、`chapter4/collaboration-tools/README.md` — 感知工具、协作工具 MCP 服务器示例 — 低
- `book/chapter5.md` — 「代码：通用 Agent 的元能力」（第 351 行），把代码当工具执行复杂逻辑 — 中
- `chapter5/erp-agent/README.md` — 自然语言交互的 ERP Agent（NL → SQL，artifact 模式），与「查数」段落最接近的实例 — 中（亦相关主题 3）
- `chapter5/code-for-logic/README.md`、`chapter5/code-for-math/README.md` — 用代码生成工具替代模型直算，降低推理错误 — 低

## 6. 答案核验 / 接地（防编造）

- `book/chapter7.md` — LLM-as-a-Judge：自动化评估的核心（第 304 行）、失败归因「从整条轨迹定位首个错误」（第 434 行）、验证器（第 222 行），是「逐句核对有没有依据」的方法论来源 — 高
- `chapter9/trajectory-verifier/README.md` — 客服 Agent 的三层轨迹验证器，逐层核对行为链是否有依据 — 高
- `book/chapter2.md` — 「上下文学习的内部机制：检索而非推理」（第 999 行）解释模型为何会「记错/编造」，是设计核验的理论支点 — 中（亦相关主题 4）
- `book/chapter3.md` — RAG 基础与「知识的组织与检索」，接地到外部知识的做法 — 中（亦相关主题 4）
- `chapter9/ai-style-skill/README.md` — 开放式提炼 + LLM-as-a-judge 的打分范式 — 低

## 7. 状态与存储（可恢复、checkpoint）

- `book/chapter2.md` — 「Agent 状态栏：通过元信息增强 Agent 轨迹管理」（第 849 行）含状态栏构成、在上下文中的位置、状态更新与缓存代价，是把运行时状态显式外置的方法 — 高
- `chapter2/system-hint/README.md` — Agent 状态栏（System Hint）实验实现，可直接对照「进度/上下文/待办」外置写法 — 高
- `chapter9/gaia-experience/README.md` — 从 GAIA 轨迹提炼经验知识文档；其 `AWorld/aworld/checkpoint` 提供可恢复 checkpoint 机制（标题/目录推断） — 中
- `book/chapter6.md` — 「异步与事件驱动：当世界主动找上门」（第 29 行）涉及长期运行任务的状态与打断恢复 — 中（亦相关主题 9）
- `chapter6/async-agent/README.md` — 带并行执行和打断能力的异步 Agent 实现 — 中（亦相关主题 9）
- `chapter2/local_llm_serving/README.md` — 本地 LLM 服务部署与工具调用，涉及会话状态维持 — 低

## 8. 模型网关（限流 / 重试 / 留痕）

- `chapter5/provider-failover/README.md` — 跨厂商的轨迹接管、输出中断后的接续（重试与故障转移的核心参考） — 高
- `book/chapter7.md` — 「Agent 系统的成本分析」（第 599 行）给出端到端 token/成本核算视角 — 中（亦相关主题 10）
- `chapter7/agent-cost-analysis/README.md` — Agent 任务端到端成本分析实验 — 中（亦相关主题 10）
- `book/chapter1.md` — 「如何选择模型」（第 353 行）涉及多供应商/多模型切换 — 中（亦相关主题 2）
- `book/chapter2.md` — 「Chat Template」（第 502 行）与 KV/Prompt Cache（第 556 行），网关层请求构造与缓存可复用 — 低（亦相关主题 4）
- `chapter2/local_llm_serving/README.md` — 本地服务与工具调用的接入方式 — 低

## 9. 多轮对话与追问

- `book/chapter2.md` — 「带工具调用的多轮交互：Agent 的核心循环」（第 95 行）与「用代码实现 Agent 的核心循环」（第 251 行），多轮消息结构教材 — 高
- `book/chapter7.md` — 「人机交互型与工具调用型评估环境」（第 182 行），多轮澄清/交互的可评测定义 — 中（亦相关主题 10）
- `chapter7/tau2-bench-eval/README.md` — τ²-bench telecom 评测，典型多轮人机交互任务 — 中（亦相关主题 10）
- `chapter5/conversational-ui/README.md` — 对话式界面定制系统，追问/澄清的交互形态参考 — 中
- `book/chapter6.md` — 语音与实时交互（第 301 行起）中的认知时序（实时交互 vs 深度思考） — 中（亦相关主题 7）
- `chapter6/live-audio/README.md`、`chapter6/phone-agent/README.md` — 实时语音对话端到端示例 — 低

## 10. 评测与回归

- `book/chapter7.md` — 本主题主教材：一条评估任务的解剖、评估指标（Pass@k / Pass^k）、评估环境、自动化评估、统计显著性、可观测性、从 Benchmark 到系统改进、生产级内部评估基础设施 — 高
- `chapter7/README.md` — 第 7 章评估实验索引 — 中
- `chapter7/tau2-bench-eval/README.md` — τ²-bench telecom 评估复现（含轨迹与验证器） — 高
- `chapter7/model-benchmark/README.md` — 多维度模型性能基准 — 中
- `chapter7/elo-leaderboard/README.md` — 基于两两配对的 Elo 排名（评估驱动选型） — 中
- `chapter7/public-health-reporting-eval/README.md` — 面向领域报告的 Agent 评估 — 中
- `chapter7/user-memory-policy-eval/README.md`、`chapter7/user-memory-system-evaluation/README.md` — 用户记忆的边界行为与系统评估 — 中
- `chapter9/self-evolution-eval/README.md` — 评估 Agent 是否在持续进化（回归视角） — 中
- `book/chapter9.md` — 「构建可长期运行的持续进化闭环」（第 265 行）、「可验证闭环的边界：当『完成』不等于『进步』」（第 308 行），防止评测被钻空子 — 中
- `chapter2/prompt-engineering/README.md` — 提示工程消融实验（τ-bench），可复用的回归对比方法 — 中
- `chapter1/context/README.md` — 组件消融实验，理解每个特性的真实贡献 — 中
- `README.md`（仓库根） — 全书章节＋实验总索引，定位实验的入口 — 中

---

## 与石油问答平台的对照点

1. **编排：默认线性工作流，开放任务才给自主循环**——chapter1「编排模式：工作流与自主」与 chapter7「model-action-threshold」支持「先用最小流程，判定需要时才升级」的分层策略，正合本仓 9 段流水线 + 局部自主的设计取舍。
2. **上下文分层压缩 + 子 Agent 隔离**——chapter2「分层压缩机制」「隔离优于压缩」为长对话/长报告场景提供「压缩 vs 隔离」两条路线，可作为记忆段的技术底座。
3. **状态外置成「状态栏」**——chapter2「Agent 状态栏」把进度/待办/已用上下文显式写进系统提示，比隐式记忆更可审计，适合可恢复与可回放的运行时。
4. **只读/越权不变量做进数据对象**——chapter5「权限内嵌的数据对象」把权限绑在数据本身而非只靠入口校验，可加固「只读不变量」这类硬约束。
5. **高风险操作确认门禁**——chapter9「harness-safety-gate」是「查数前/审批前」确认门的现成范式，可直接对照前置检查段的「要不要审批」。
6. **核验落成三层轨迹验证器**——chapter9「三层轨迹验证器」＋chapter7「失败归因定位首个错误」，为「逐句核对有没有依据」提供可实现的校验结构。
7. **工具按需发现与层次化组织**——chapter4「层次化组织与主动工具发现」「Skills 按需查阅」，可直接支撑「给子问题配工具」的匹配段。
8. **评测区分能力上限与业务可靠性**——chapter7 用 Pass@k（能力上限）vs Pass^k（业务可靠性）＋配对比较/Elo，适合本仓建立回归与选型基线。
9. **网关故障转移**——chapter5「跨厂商轨迹接管、输出中断接续」是多供应商网关重试/接管的最直接参考。

---

## 疑点 / 缺口

- **模型网关的完整工程实践缺失**：仅 `chapter5/provider-failover` 直接讲重试/接管；**限流、配额、并发控制、审计留痕的完整网关设计**在本书基本没有专章（审计留痕只旁及 `chapter3/log-sanitization`），需另找资料。
- **运行时 checkpoint/恢复缺系统化方法**：状态相关只有「上下文内的 Agent 状态栏」与第三方框架 `AWorld/checkpoint`（标题/目录推断），缺少「运行时状态机 + 持久化恢复」的独立工程方法，需另找。
- **企业级权限 / RBAC / 只读不变量**：只有 `chapter5/permission-embedded-data-objects` 一处，缺少多角色、行列级权限与「只读 SQL」防护的系统论述。
- **澄清式主动追问（反问策略）缺专章**：本书讲多轮人机交互及其评测，但没有专门讲「何时该反问、问什么、问到什么程度」的澄清策略设计。
- **结构化查询安全（NL→SQL 只读护栏）**：`chapter5/erp-agent` 给了 NL→SQL 实现，但没有 SQL 注入 / 越权写入护栏的专门内容。
- **答案引用溯源（引用回原文段落/数据行）**：chapter7 讲评审与归因，但「答案逐句附带可点击引用」的生产级做法本书未展开。
- **线上回归 / 灰度发布工程**：chapter7 有评估方法论，但缺「生产环境线上回归、A/B 灰度、回滚」的落地流程。
