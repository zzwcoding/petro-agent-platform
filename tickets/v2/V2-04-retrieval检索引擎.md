# V2-04 · retrieval 检索引擎

状态: 实现中（2026-10-08，P-003 已派发）
Touches modules: `retrieval`
阻塞: V2-01｜被阻塞: V2-05

## 任务

实现 `appv2/retrieval/`：RetrievalEngine（retrieve＋graph 两面）＋RetrievalBundle，
供给策略本体化——矛盾来源同窗并立、截断显式（window_note 带召回/送窗数字）、出处链完整。

先读: specs/retrieval.md 全文；specs/modules.md `retrieval` 卡；Q11 报告 eval/results/Q11-评测报告.md「Top 问题」节（P0-2 病灶背景）

框架红线: 无点名框架
边界红线: 只许建 `appv2/retrieval/**`；依赖只许 `appv2.infra`；不得 import `app.**`、knowledge/query

验收: 以下逐条对应 specs/retrieval.md「验收测试」表——
- specs/retrieval.md「验收测试」六条全绿：
  rerank_fallback / contradiction_same_window / window_note_explicit / provenance_chain / family_supply / graph_surface
- RetrievalNeed/RetrievalBundle 两 schema 随本票定稿（票面点名）
- 同窗规则在供给层硬编码实现——不依赖 LLM 自觉（评审批次核对）
- kb fixture 用 V1 片段库抽样（含同型双报告 A-W11/Y-21 对）

回报: 完成后回总窗口："V2-04 完成，产物 appv2/retrieval/，偏差: 有/无，测试: pytest 输出摘要"
