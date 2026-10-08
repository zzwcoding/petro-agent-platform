# V2-02 · knowledge 语义读面

状态: done（2026-10-08，P-002 验收通过·收尾报告在案）
Touches modules: `knowledge`
阻塞: V2-01｜被阻塞: V2-03、V2-05

## 任务

实现 `appv2/knowledge/`：KnowledgeStore 四接口＋Evidence schema（含 binding_state 三态），
sem_* 台账只读视图＋别名八键归一＋族标注透传。

先读: specs/knowledge.md 全文；specs/modules.md `knowledge` 卡；specs/tools.md 的 Observation 定义节

框架红线: 无点名框架
边界红线: 只许建 `appv2/knowledge/**`；依赖只许 `appv2.infra`；不得 import `app.**`、query/retrieval

验收: 以下逐条对应 specs/knowledge.md「验收测试」表——
- specs/knowledge.md「验收测试」六条实现于 `tests/domains/test_v2_knowledge.py` 全绿：
  metric_exact_hit / alias_canonicalize / unbound_flagged / expired_flagged / families_complete / readonly_inv2
- SemanticQuery/Evidence 两 schema 随本票定稿（票面点名）
- binding_state 判定逻辑与 V1 冻结三绑定语义一致（unbound_flagged 为准）
- fixture 用问数组台账态（20 指标/11 术语/10 对象/5 关系），来源 eval/answers/问数组-题目与答案.md

回报: 完成后回总窗口："V2-02 完成，产物 appv2/knowledge/，偏差: 有/无，测试: pytest 输出摘要"
