# ADR-0004 · ReAct 重构：六节点线性流水线 → 自主循环（Owner 拍板 2026-10-09）

- 日期：2026-10-09
- 背景：Q12 对账实证检索域 81 题整域失效——根因是流水线设计（模型当三工位、输出合同
  closed-world、校验失败兜底一刀切），非模型能力。ZCode 证据链还原：模型理解全对，
  死于"指标候选"无台账可看/plan schema 无检索字段。
- 决策：**ReAct 自主循环**取代六节点线性 loop（understand→decision⇄(discover/execute→
  observe)→answer→verify 收口）。Owner 十条拍板（全按 L0 推荐）：
  1. 预算：≤3 轮 × 轮内（发现≤2＋主执行≤2）＋单段 300s＋单工具 30s
  2. schema 校验失败取消自动 repair——拒因回喂 LLM 重决策
  3. verify 节点保留（零 LLM，INV-1/4 机器底线；表格/血缘/fragment 承载豁免）
  4. 发现工具探查范围＝agg 三表＋sem 五账＋kb 片段清单；raw/lake 湖表不开放
  5. SSE wire 允许演进（subtype 在位）；V1 超集兼容保留到 web V2 批完成后放宽
  6. 澄清分级：时间窗歧义→自动默认近 30 天＋注记；目标/对象/口径→ASK；越集→审批
  7. Skill 处理指南＝ontology 资产（与台账同治理）
  8. LangGraph prebuilt ToolNode 不用（与"工具只经 ToolRegistry.call 受控链"冲突），自有节点承载
  9. 答案起草挪 answer 节点（verify 拆为纯核验，caller 三桶 understand/decision/answer）
  10. P-022/P-023 补丁撤回（本重构使其作废）
- 后果：specs/agent-loop.md 行为约定 3/7 等条款失效（由 V2-36 重写）；数据路径退化分析
  （犹豫空转）催生发射判据与 ADR-0005。
