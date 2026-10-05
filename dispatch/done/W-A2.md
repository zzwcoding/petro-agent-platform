# W-A2 接线票：A2 井档案页面切真后端四端点（接线批 2/3）

任务：A2 页面内嵌种子退役、切真后端四端点〔来源：dispatch/results/R-WIRE.md §2 接线差异清单（B 类）〕。后端四端点已实装（M-02）并在 localhost:8000 运行；**中台 raw 8 表当前无业务数据——空态渲染验收**（真数据灌入归演示批，执行台 fixture 灌入后另复核）。

施工方案：

1. **api/wells.js 新建**（经 client.js 惯例）：GET /api/wells（选井列表）/​{well_id}（档案明细）/chain（关系链）/change-tickets（变动壳）。
2. **R-WIRE 字段映射**：`from/to`→`date_start/date_end`；`measureEnum/deviceEnum`→`measure_foot/device_foot`；`ok` 布尔→真 DTO 无（色映射改状态字段驱动）；**buildEvents 前端合并整体退役**（服务端已合并 events）；变动页签切端点 4（V1 恒空列表——空态注记照合同，撤 mock 的 CH_STATUS/planeOf/字符串过滤）。
3. **合同常量**：设备状态三枚举/措施效果列照 A2 v0.2 常量表（页面显示用）——R-WIRE 已核与内嵌种子零冲突。
4. **空态与真数据双态**：空列表渲染验收（当前 raw 空）；`well_status_log` 写通道悬置→状态变更警示行不出现（R-WIRE 登记项）。
5. **测试适配**：A2 相关 vitest 若有 mock 断言改适配（不压制）；web 三连绿；curl spot check 附回报。

先读：teach A2 v0.2 册（DTO/常量/开放问题节）；dispatch/results/R-WIRE.md §2；web/src/pages/A2.jsx 现状；M-02 交付（master 1633b64→）。

框架红线：无。

边界红线：只动 web/src/api/wells.js（新建）与 web/src/pages/A2.jsx 及对应测试；分支 `fix/wire-a2` 单提交（worktree 作业）；禁止 git add -A/.；Owner 私产不碰。

验收：web 三连绿；curl spot check（四端点连通＋空态形状）；R-WIRE §2 差异清单逐条处置表。

回报：按 PROTOCOL 写 `dispatch/results/W-A2.dev.md`。
