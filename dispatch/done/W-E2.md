# W-E2 接线票：E2 质检台页面切真后端九端点（接线批 1/3——R-WIRE 对账输入）

任务：E2 页面数据源从浏览器 mock 切真后端〔来源：dispatch/results/R-WIRE.md §1 接线差异清单（B 类）＋单窗口 L0 接线批授权〕。后端九端点已实装并在 localhost:8000 运行（master 最新）。

施工方案：

1. **api/e2.js mock → 真接口**：改经 web/src/api/client.js 惯例调真端点——rules/PATCH 启停/issues/transitions（含 action:"rescan"）/freshness/quarantine/tasks 受理·轮询·历史；撤 mock 内存 store。
2. **R-WIRE 硬伤四处修正**：`report.quarantinedRows/rejectedBatches`→真 snake_case（quarantined_rows/rejected_batches）；`report.rules` 键撤（改读 task 顶键 rules）；`aiNote/closeNote`→`ai_note/close_note`；轮询语义真化（受理 202→轮询 tasks/{id} 至 done/failed，撤 mock 250ms 固定延时）。
3. **错误处理**：启用 13-20 真接口 422（quality_rule_registered_only）→ 错误 toast 收口（client 已弹，页面不重复弹）；409 重入/422 关闭守卫/501 复扫超时同收口。
4. **空态渲染**：真库无预置单/初始任务/水位种子——三页签空态渲染验收（R-WIRE 环境前置：执行台灌数据后另有真数据复核）。
5. **测试适配**：既有 vitest 断言 mock 行为的改断言适配（不压制）；web 三连绿；对 localhost:8000 curl spot check 附回报。

先读：teach E2 v0.5 册（行为约定九条）；dispatch/results/R-WIRE.md §1（差异清单真源）；web/src/api/client.js（接线惯例）；web/src/pages/E2.jsx＋api/e2.js 现状；M-05a/M-05b 交付（master e2c6acc→）。

框架红线：无。

边界红线：只动 web/src/api/e2.js 与 web/src/pages/E2.jsx 及对应测试；不碰其他页面/后端；分支 `fix/wire-e2` 单提交（worktree 作业）；禁止 git add -A/.；Owner 私产不碰。

验收：web 三连绿；curl spot check（真后端九端点连通＋形状）；R-WIRE §1 差异清单逐条处置表。

回报：按 PROTOCOL 写 `dispatch/results/W-E2.dev.md`。
