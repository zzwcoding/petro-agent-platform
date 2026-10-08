# V2-05 · tools 工具层

状态: done（2026-10-08，P-005 验收通过·收尾报告在案）
Touches modules: `tools`
阻塞: V2-02、V2-03、V2-04｜被阻塞: V2-06

## 任务

实现 `appv2/tools/`：ToolRegistry＋四工具（semantic_query/data_query/doc_retrieve/graph_query），
统一 ToolResult/Observation/错误三分类/AskFrame；data_query 内部先经 query.validate。

先读: specs/tools.md 全文；specs/modules.md `tools` 卡与「边界规则」节；上游三 spec 的接口定义节

框架红线: 无点名框架
边界红线: 只许建 `appv2/tools/**`；依赖 `appv2.knowledge/query/retrieval`（只许公开接口）＋`appv2.infra`；
不得 import `app.**`、runtime

验收: 以下逐条对应 specs/tools.md「验收测试」表——
- specs/tools.md「验收测试」五条全绿：
  descriptors_readonly（INV-2 工具层落点）/ bad_args_notouch_engine / error_taxonomy /
  query_outcome_mapping / observation_provenance
- ToolDescriptor/ToolContext/ToolResult/AskFrame 四 schema 随本票定稿（票面点名）
- query 联合态→ToolResult 映射表逐态测试（query_outcome_mapping）
- 假引擎 adapter 就位（后续 runtime 票复用）

回报: 完成后回总窗口："V2-05 完成，产物 appv2/tools/，偏差: 有/无，测试: pytest 输出摘要"
