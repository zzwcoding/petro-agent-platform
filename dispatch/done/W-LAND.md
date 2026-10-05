# W-LAND 修复票（接线批归位：三页落地化＋原型树还原——双树共存纪律修正）

任务：修正接线批的树别错改——三页（E2/A2/B4）被直接改在原型树（pages/）上，违反双树共存纪律〔来源：web/src/landing/registry.js 头注「落地树（真 API，#/X）× 原型树（mock，#/proto/X，数据自包含）；新页落地流程＝landing/ 下建 <KEY>.jsx → LANDING_LIT 加入」＋Owner 指出「已实现与原型两种页面同时存在，未区分直接改了」〕。本票归位：接线成果迁入落地树注册点亮，原型树还原为 mock 参照态。

施工方案（六步，全部 web/src 内）：

1. **E2 落地化**：`pages/E2.jsx`（现接线版）迁 `landing/E2.jsx`；真 API 模块 `api/e2.js` → **`api/quality.js`**（更名——E2 域真客户端照 kb.js/faq.js 域名惯例，后端前缀 /api/quality 同名；landing/E2.jsx 与其测试的 import 随改）；`pages/__tests__/E2.test.jsx` → `landing/E2.test.jsx`；registry.js `LANDING_MODULES`/`LANDING_LIT` 注册 E2。
2. **E2 原型还原**：`pages/E2.jsx` 与 `api/e2.js` 从 `git show 3c2d63a:` 还原（P2-05 同步点——mock 页面＋mock 服务层逐字快照，页面 import '../api/e2.js' 路径不变指向已还原的 mock，自包含闭环）。
3. **A2 落地化**：`pages/A2.jsx`（现接线版）迁 `landing/A2.jsx`（import '../api/wells.js' 不变）；registry 注册 A2；`api/wells.test.js` 随 landing 惯例留 api 层。
4. **A2 原型还原**：`pages/A2.jsx` 从 `git show 04f9606:` 还原（W-A2 之前态——内嵌 WELLS 种子自包含，零 api import）。
5. **B4 落地化**：`pages/B4.jsx`（现接线版）迁 `landing/B4.jsx`（import '../api/b4.js' 不变）；registry 注册 B4；`pages/__tests__/B4.test.jsx` → `landing/B4.test.jsx`；`api/b4.test.js` 留 api 层。
6. **B4 原型还原**：`pages/B4.jsx` 从 `git show 3c2d63a:` 还原（自包含，零 api import）。

验收前置事实（已核）：landing 页惯例＝import '../api/<域>.js'（B1→kb.js）；原型页 E2 依赖 mock 服务层（1 个 api import）、A2/B4 自包含（0 api import）——还原后原型树自包含闭环。

先读：web/src/landing/registry.js 全文（双树纪律与新页落地流程真源）；web/src/shell/Shell.jsx＋SideMenu.jsx（双树导航与角标）；git show 3c2d63a/04f9606 的三页原型态；W-E2/W-A2/W-B4 三份 dev 回报（接线成果现状）。

框架红线：无。

边界红线：只动 web/src（landing/ 新增三页＋registry.js＋pages/ 三页还原＋api/e2.js↔api/quality.js 更名＋api 层两测试随迁）；后端零改动；分支 `fix/w-land` 单提交（worktree 作业）；禁止 git add -A/.；Owner 私产不碰。

验收：以下全达才算过。
1. 双树渲染：#/E2、#/A2、#/B4 落地页（真 API）与 #/proto/E2、#/proto/A2、#/proto/B4 原型页（mock）同仓共存——vitest 冒烟或 jsdom 断言两树各自渲染（落地 E2 消费真端点形状、原型 E2 复扫按钮在位）。
2. registry.js：E2/A2/B4 在 LANDING_LIT；菜单/面包屑「落地」绿标三页、「原型」灰标三页并存。
3. 原型还原逐字：pages/E2.jsx＋api/e2.js 与 3c2d63a 版 diff 空；pages/B4.jsx 与 3c2d63a 版 diff 空；pages/A2.jsx 与 04f9606 版 diff 空。
4. web 三连绿（eslint 0 error/vitest 全过含迁移后测试/build 成功）；落地三页真 API 消费不回归（wells/quality/b4 测试不跌）。
5. 单提交 `fix/w-land`。

审查节点：关票前审查拍（T1）——双树纪律修复票，审查专查还原逐字性＋注册点亮＋两树 import 闭环。

回报：按 PROTOCOL 写 `dispatch/results/W-LAND.dev.md`。
