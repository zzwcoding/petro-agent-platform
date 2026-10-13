# V2-71 · 聚合下推数据库（求和/排名题在库内算完只回少量行）

状态: 已完工（2026-10-13——代码/白名单/指南/钉测全绿；真机路由随机性见尾注）｜ 优先级: P1 ｜ 来源: 场景对照报告瑕疵③（data-clean/bigresult）

## Owner 裁决（2026-10-13）

原方案「聚合行上限另档 200」作废。Owner 拍板：**聚合在数据库里直接算**
（SQL SUM/GROUP BY/ORDER BY），只回计算结果几行——原始明细大列表永远不进模型
（「不想返回一个超级大列表把 LLM 挤爆」）。原始行 LIMIT 50 不动（它挡的是拉明细，
不挡数据库算数）。

## 改动面（改向后的两段）

1. **计划面**：QueryPlan 增聚合形（aggregate: sum/avg/max/min＋group_by 维度）——
   澄清相位发射判据/指南补一句：总量/合计/排名形问题提议聚合计划（库内算），
   不拉原始明细；
2. **引擎面**：pg_executor 按聚合计划生成 SUM/GROUP BY SQL（只读、参数化），
   结果行数天然少（≤区块数×窗口数），不受原始行 LIMIT 50 约束；执行台账与
   血缘照常落（口径/窗口/水位注记不丢）。

## 验收（场景覆盖：data-clean）

- 「渤南区块本月产油量」→ 库内 SUM 返回少量行（全月合计数值可达）＋口径/水位注记；
- 明细形问题零漂移（bigresult 拉明细仍 50 上限＋如实截断——大结果落盘另票）；
- `test_v2_query.py` 增钉：聚合计划→SUM SQL 形＋少量行返回；明细→50 不变。

## 边界红线

- 原始行 LIMIT 50 本体不动；聚合 SQL 只读参数化（INV-2）；
- 排名形（top N）仍走原始行排序取前 N（N≤50 内），不新增上限。

## 依赖与分工

无前置。施工排：V2-69（坏引标）之后、A1V2 前端切回之前。


## 施工取证（2026-10-13——缝已探明，分段施工）

四面改动点（排名型＝现成先例，逐处镜像）：
1. `appv2/query/domain.py` QueryPlan（:302）增 `aggregate: bool = False`（纯汇总型：
   整窗 SUM 一行，无 GROUP BY 无明细；ranking=True 语义不变）；
2. 发射键白名单：plan 键闭世界校验处（data_query 工具 argscheck/schema.py——
   未知键即拒的闭世界）放行 `aggregate`；parse_decision 草案透传；
3. `appv2/query/engine.py`（:253 SqlPlan 装配）透传 aggregate；
4. `appv2/query/pg_executor.py`（:201 _statement_with_scope）增汇总分支：
   `SELECT SUM(<measure>) FROM … WHERE 窗` 单行——镜像既有 ranking 分支的
   GROUP BY/ORDER BY 先例；结果列命名「合计（口径）」；
5. 指南资产一句（总量/合计/排名形提议聚合计划）——施工时定位指南真源
   （OntologyGuideProvider 装载的 ontology 资产）加注。

验收钉测：聚合计划→单行 SUM＋无 LIMIT 约束；明细/ranking 零漂移；
真机验收＝data-clean 题（渤南本月产油量→全月合计可达）。

## 完工记录（2026-10-13）

- 六处改动：QueryPlan/SqlPlan 增 `aggregate: bool = False`；engine SqlPlan 装配透传；
  pg_executor `_statement` 汇总分支（整窗 SUM＋batch MAX 随行，无 GROUP BY 无 LIMIT）
  ＋`_result_columns` 单合计列；handlers `_DATA_SCHEMA.plan_draft.properties` 放行
  `aggregate`（boolean）＋`_plan_from_draft` 透传；guide.py TOOLMATCH_CONTRACT 计划键
  教学句（求和/合计/总量类 true——数据库整窗 SUM 只回一行合计）。
- 钉测（子代理实施，tests/domains/test_v2_query.py 追加 5 钉）：构造/缺省零漂移锚、
  引擎端到端单行合计（钉值 312100.16±0.1）、SQL 形状（SUM 在场/无 GROUP BY/无 LIMIT）、
  ranking/detail 形状不变锚、白名单放行；test_v2_tools.py 陈旧九键钉补 aggregate。
- 全量 1713 过零跌；ruff/mypy/lint-imports 绿。
- 真机首抽注记：data-clean 题（渤南本月产油量）本轮模型路由至知识链（如实答未找到＋
  请指明对象）——链路选择为模型语义判断（随机性）；聚合机器已由钉测锁死，
  「模型选汇总模板」的真机到达率随 23 条回归继续观察；如到达率不足，后续票强化
  澄清相位对求和形的路由偏置。
