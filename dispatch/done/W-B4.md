# W-B4 接线票：B4 报告百科页面切真后端两端点（接线批 3/3）

任务：B4 页面数据源切真后端两端点〔来源：dispatch/results/R-WIRE.md §3 接线差异清单（B 类）〕。后端已实装（P2-04 覆盖语义 v0.4）并在 localhost:8000 运行；**wiki_page 表无种子——目录空态验收**（真数据需 B1 报告入库管线，归演示批）。

施工方案：

1. **数据源切真**：目录 GET /api/wiki/pages（lib/keyword 筛选参数化、status 服务端字段、撤本地 statusTagOf/CUR_VER/本地筛选）；全文 GET /api/wiki/pages/{pageId}（content/claims/glossary_terms/related_objects 页内存直出字段）；api 层经 client.js 惯例（api/b4.js 新建或并入现有结构——以仓内最小改动为准）。
2. **R-WIRE 语义差异**：撤版本族零残留确认（两页签、无回滚/?version——mock 造版工艺随种子退役）；`Md/renderInline` 解析器五族 `[[…]]` 标记原样保留（R-WIRE 证实与真后端 content 兼容）。
3. **证据弹层懒加载**：R-WIRE 最大工作量件——复用 web/src/api/kb.js 既有 `listFragments`/`getFragmentContext`（P1-02 已接线面），接 B2 证据弹层（mock 更正清单⑨）。
4. **空态**：目录空态渲染验收。
5. **测试适配**：B4 相关 vitest 改适配（不压制）；web 三连绿；curl spot check 附回报。

先读：teach B4 v0.4 册（端点/DTO/变更记录）；dispatch/results/R-WIRE.md §3；web/src/pages/B4.jsx 现状；P2-04 交付（master）；web/src/api/kb.js（证据弹层复用件）。

框架红线：无。

边界红线：只动 web/src/pages/B4.jsx＋api 层（b4 消费）＋对应测试；分支 `fix/wire-b4` 单提交（worktree 作业）；禁止 git add -A/.；Owner 私产不碰。

验收：web 三连绿；curl spot check（两端点连通＋空态形状）；R-WIRE §3 差异清单逐条处置表。

回报：按 PROTOCOL 写 `dispatch/results/W-B4.dev.md`。
