# W-LAND 审查拍（T1 关票前审查——双树纪律修复票；只产发现清单，零修复动作）

任务：对主仓分支 `fix/w-land` 单 commit `a63808a`（12 文件 +1915/−536——三页落地化＋原型树还原＋registry 点亮）做关票前独立审查，设计意图核验优先：双树共存纪律是否完整恢复（registry.js 头注为判据真源）＋原型还原逐字性＋落地页真 API 消费不回归〔来源：票面 W-LAND 任务节＋Owner 指出的树别错改〕。

审查六节：

1. **diff 全量嗅探**：12 文件逐块定性（landing 新增三页两测试/pages 三页还原/api 更名与还原/registry）；零夹带（后端/chat 既有链零触碰）。
2. **落地化核验**：landing/E2·A2·B4 三页＝接线版原样迁移（与迁移前 pages 版 diff 应为空或仅 import 路径）；registry.js LANDING_MODULES/LANDING_LIT 注册形态照 B1/B3 条目；Shell/SideMenu 零改动自动双列（落地绿标＋原型灰标并存）；真 API 模块更名 api/e2.js→quality.js 的全引用闭环（零断链）。
3. **原型还原逐字核验（主查）**：pages/E2.jsx＋api/e2.js vs 3c2d63a、pages/B4.jsx vs 3c2d63a、pages/A2.jsx vs 04f9606——blob hash 级 diff 全零；原型树自包含闭环（E2 import mock 服务层路径闭环/A2·B4 零 api import）。
4. **双树渲染与菜单**：落地 #/E2·#/A2·#/B4（绿标真 API）与原型 #/proto/ 三页（灰标 mock）并存；NotLit 不出现；build 零 test chunk。
5. **测试与回归**：vitest 266 例不跌（迁移后零断言改动）；wells/quality/b4 API 测试不跌；web 三连独立复跑。
6. **接线成果保全**：W 票的接线语义（E2 九端点消费/A2 四端点 DTO/B4 两端点＋证据弹层）在落地版中零丢失——与 W-E2/W-A2/W-B4 dev 回报交付清单对账。

先读：dev 回报 `dispatch/results/W-LAND.dev.md`；registry.js 全文（判据真源）；`git show a63808a` 全 diff；3c2d63a/04f9606 历史原型态。

框架红线：无。

边界红线：全程只读＋独立复跑（web 三连），主树分支零写入；零修复动作；全新实例。

验收：以下全达才算过。
1. 六节结论逐项（通过/发现）；原型还原 blob-hash 对照表在回报。
2. 发现清单每条带 file:line＋影响评级＋建议处置。
3. 独立复跑数字附回报。
4. "零修复动作已执行"声明在末节。

回报：按 PROTOCOL 写 `dispatch/results/W-LAND.rev.md`。
