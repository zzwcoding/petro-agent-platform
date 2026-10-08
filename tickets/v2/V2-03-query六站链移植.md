# V2-03 · query 六站链移植

状态: done（2026-10-08，P-004 验收通过·收尾报告在案）
Touches modules: `query`
阻塞: V2-01、V2-02｜被阻塞: V2-05

## 任务

实现 `appv2/query/`：QueryEngine（validate＋run）＋QueryPlan/QueryOutcome 六联合态，
V1 六站链确定性行为移植——三闸/新鲜度改绑/未绑定降级/缺参反问/越集审批/血缘卡。

先读: specs/query.md 全文（验收数值逐条钉死）；eval/answers/问数组-题目与答案.md「关键数值」节；
specs/knowledge.md（Evidence 依赖）

框架红线: 无点名框架
边界红线: 只许建 `appv2/query/**`；依赖 `appv2.infra`、`appv2.knowledge`（公开接口）；
不得 import `app.**`——V1 domain.py 的逻辑以行为为准重实现，禁止整文件搬运

验收: 以下逐条对应 specs/query.md「验收测试」表——
- specs/query.md「验收测试」十条全绿（数值钉死：21.16/36.97/5839.6/1784.7/8824.4/恰30行）：
  detail_window_50 / rebind_notice / ranking_values / explicit_limit_30 / freshness_blocks /
  vague_time_clarify / unbound_degrade / external_table_ask / metric_switch_blocked / readonly_inv2
- 六联合态各自的最小复现测试在场（随上十条覆盖）
- Q11 病灶修复点落实："井位台账"外表别名进选表命中集→external_table_approval 可达（external_table_ask 红→绿）
- agg fixture 用题册绑定 CSV 快照（~/Downloads/fieldforge/out-tpa/oil_production_daily.csv 抽样入仓 fixtures）

回报: 完成后回总窗口："V2-03 完成，产物 appv2/query/，偏差: 有/无，测试: pytest 输出摘要"
