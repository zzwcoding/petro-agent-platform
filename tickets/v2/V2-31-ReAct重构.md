# V2-31 · ReAct 重构：自主循环 loop 取代六节点线性流水线（P0）

状态: done（2026-10-09，P-024 三线验收通过·S3 基线实证指南主因） 已派发·预挂中途审查）
Touches modules: `runtime`、`tools`、`api`
阻塞: 无（P-022/P-023 已撤回由本票取代）｜被阻塞: V2-28 重做/Q13 复测/teach 原型改版

## 背景（Owner 2026-10-09 拍板四项）

Q12 对账实证：检索域 81 题整域失效的根因是**流水线设计反了**——模型被当作三个工位
（understand/plan/answer），输出合同 closed-world（指标候选无台账可看/plan schema 无检索
字段）、校验失败兜底一刀切。重构为 ReAct 自主循环（参照 Kimi CLI/ZCode 的"模型在循环里、
工具在手边、观察回流转"机制）。P-022/P2-023 补丁随本票作废撤回。

## 拍板结论（票面生效，Owner 全按 L0 推荐）

1. 循环结构：≤3 轮 × 轮内（发现≤2＋主执行≤2）＋单段总时长 300s；轮＝LLM 决策周期
2. schema 校验失败取消自动 repair——拒因回喂 LLM 由它重决策
3. verify 节点保留（零 LLM，INV-1/4 机器底线；P-020 表格豁免继承）
4. 发现工具探查范围＝agg 三表＋sem 五账＋kb 片段清单；**raw/lake 湖表不开放**
5. SSE wire 允许演进（subtype 在位）；V1 超集兼容承诺保留到 web V2 批完成后放宽
6. 澄清分级：时间窗歧义→模型按指南自动默认（近 30 天）＋注记；目标/对象/口径歧义→ASK；
   外表越集→审批挂起（不变）
7. Skill 处理指南＝ontology 资产（V2-32 并行起草，本票消费其接口）

## 任务

1. **loop 改造**：understand/plan 两线性节点 → ReAct 决策节点（LangGraph ToolNode 承载
   工具调用）；结构化发射（task_type data|knowledge|mixed＋plan/retrieval_need）经
   schema 校验进固定代码执行；观察回流后模型自主决策再轮或终稿
2. **发现工具扩展**：semantic_query 升一等发现工具＋新增表结构探查工具（白名单⑥范围）
3. **保留件全不动**：Context Builder/Manifest、预算闸（按新语义）、ASK 挂起/审批、
   checkpointer、PgCheckpointer、RunAuditor（审计四事件）、三红线（GatewayChatModel 单点/
   langgraph 只许 runtime/state 自有）、tools 只读边界
4. **wire 演进**：step 事件形态按 ReAct 周期重定（decision/discover/execute/observe/
   verify/answer），subtype 机制沿用；V1 兼容超集面断言保留
5. **剧本 completer 升级**：按轮/决策分支 replay（ReAct 非确定性增大，行为断言锁在
   决策出口与观察流形，不锁模型原话）

## 验收: 以下逐条——

- 剧本钉测：知识型问句 LLM 自主选 doc_retrieve（零台账校验触碰）；数证结合一轮双执行；
  发现→发射→执行→再决策全链各分支；3 轮上限收敛兜底
- 拒因回喂重决策（无 repair 调用）钉测：调用计数断言 understand/decision/answer 三 caller 桶
- 澄清分级钉测：时间窗自动默认＋注记／目标歧义 ASK／越集审批
- 问数组 16 题回归零跌（数据型路径不回归）；verify 表格豁免不回退
- 全量串联闸 exit=0＋三红线扫描绿
- **中途审查拍**：骨架可跑后停一轮审查再继续（V2-06 先例）

回报: results/P-024.dev.md（骨架版）→审查→续作。
