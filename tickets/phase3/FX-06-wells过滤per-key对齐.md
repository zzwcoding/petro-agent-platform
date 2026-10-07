# FX-06 wells 当前版过滤改 per-key as-of 对齐（R1-01）

> 状态：✅ 完工 ｜ 依赖：R1 裁决
> 来源：审查 R1（reports/审查R1-批12-20261007.md）L0 裁决——审查-修复链修复拍（审查子代理只产清单，本票为裁决后的修复执行）。

任务: 现过滤谓词＝`_snapshot_id = 全局最新批`，与湖底座 scan 的「每业务键取 ≤N 最新版」语义在
增量批下分叉（不在最新批的井会静默消失）。修法：三查询（well_info/well_measures/well_overhaul）
过滤改 per-key 最新版半连接（每 well_id 取其自身最大 _snapshot_id 的行——SQL 形态票内定案，窗口
函数或相关子查询），与 data-plane lake_store.py:152-175 scan as-of 原文对齐；PG 回归 fixture 增
**增量批场景**（第二批只含一口井的更新）断言：旧批井仍可见（批 1 数据）、被更新井出批 2 数据、
每井恰 1 行。既有全量批场景回归零跌。

先读:
- tickets/phase3/reports/审查R1-批12-20261007.md 对应发现条目与裁决节
- 所在分支上对应 DE 票的收尾报告（tickets/phase3/reports/DE-0X.收尾.md）

验收:
- [x] 对应发现条目的修复断言测试红先绿后
- [x] 既有测试零跌（所在分支基线）
- [x] 全量闸：`uv run ruff check app tests migrations tools && uv run mypy app && uv run pytest -q && uv run lint-imports && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check` 全绿（回报附输出原文含通过数数字）

回报: 写 tickets/phase3/reports/FX-06-wells过滤per-key对齐.收尾.md——产物清单（文件＋SHA）/闸输出原文摘要/偏差逐条。git 纪律：在既有票分支上续提交（**不拉新分支**），只 add 本修复票文件，严禁 git add -A。

框架红线: 零新依赖；修复范围严格限于裁决条目，不顺手改其他。
边界红线: 只许触碰对应发现涉及的文件与测试位。
〔来源：审查R1-批12-20261007 L0 裁决节；票册总表-统一开票-20261007 修复拍〕
