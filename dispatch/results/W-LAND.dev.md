# W-LAND 开发拍 回报 —— 双树归位：三页落地化＋原型树还原

> 作业方式：git worktree `.scratch/w-land`（分支 `fix/w-land`，基线＝master 最新 `f908326` 含接线批三提交）隔离作业；
> 单提交 `a63808a`；验后 worktree 已 remove（分支保留，FF 可合并）。
> 先读件全读：`web/src/landing/registry.js`（双树纪律与新页落地流程真源）、`web/src/shell/Shell.jsx`＋`SideMenu.jsx`
> （双树导航与角标——本票零改动，注册后自动承接）、`git show 3c2d63a/04f9606` 三页原型态、W-E2/W-A2/W-B4 三份 dev 回报。

## 产物

- **提交**：`a63808a`（分支 `fix/w-land`，父 `f908326`＝master 最新，单提交；worktree 已 remove，分支与提交保留待合并）
- **文件**（`git show --stat a63808a`：12 files changed, 1915 insertions(+), 536 deletions(-)）：

  | 票面工序 | 文件 | 说明 |
  |---|---|---|
  | 1 E2 落地化 | `web/src/pages/E2.jsx` → `web/src/landing/E2.jsx` | 现接线版整体迁移（rename 97%），import 随改 `'../api/e2.js'` → `'../api/quality.js'`（landing/ 与 pages/ 同为 src 一级子目录，深度不变） |
  | 1 E2 落地化 | `web/src/api/e2.js` → `web/src/api/quality.js` | 真客户端更名——E2 域域名照 kb.js/faq.js 惯例（后端前缀 /api/quality 同名）；66 行净形 |
  | 1 E2 落地化 | `web/src/api/e2.test.js` → `web/src/api/quality.test.js` | 模块更名的机械随迁（import `'./e2.js'`→`'./quality.js'`，头注「api/e2 单测」→「api/quality 单测」随改）——验收 4「quality 测试不跌」的载体 |
  | 1 E2 落地化 | `web/src/pages/__tests__/E2.test.jsx` → `web/src/landing/E2.test.jsx` | 页测试随迁（import `'../E2.jsx'`→`'./E2.jsx'`、`'../../api/client.js'`→`'../api/client.js'`；断言零改动） |
  | 2 E2 原型还原 | `web/src/pages/E2.jsx` ＋ `web/src/api/e2.js` | ← `git show 3c2d63a:` 逐字写入（P2-05 同步点：mock 页面＋mock 服务层，页面 import '../api/e2.js' 指向已还原 mock，自包含闭环） |
  | 3 A2 落地化 | `web/src/pages/A2.jsx` → `web/src/landing/A2.jsx` | 接线版迁移，import '../api/wells.js' 不变；`api/wells.test.js` 照 landing 惯例留 api 层（未动） |
  | 4 A2 原型还原 | `web/src/pages/A2.jsx` | ← `git show 04f9606:` 逐字写入（W-A2 之前态：内嵌 WELLS 种子自包含，零 api import） |
  | 5 B4 落地化 | `web/src/pages/B4.jsx` → `web/src/landing/B4.jsx` | 接线版迁移，import '../api/b4.js' 不变；`api/b4.test.js` 留 api 层（未动） |
  | 5 B4 落地化 | `web/src/pages/__tests__/B4.test.jsx` → `web/src/landing/B4.test.jsx` | 页测试随迁（import 同层化；断言零改动） |
  | 6 B4 原型还原 | `web/src/pages/B4.jsx` | ← `git show 3c2d63a:` 逐字写入（自包含，零 api import） |
  | 注册点亮 | `web/src/landing/registry.js` | `LANDING_MODULES` 增 `A2/B4/E2: () => import('./X.jsx')`（照 B1/B3 既有条目形态；`LANDING_LIT`＝Object.keys 派生自动点亮，`DEFAULT_LANDING_KEY` 不变 A1） |

- **还原逐字等证（验收 3——blob hash＋diff 双证，提交后 commit-to-commit 复验）**：

  ```
  git hash-object 对比（提交前工作树）：
  IDENTICAL pages/E2.jsx == 3c2d63a:web/src/pages/E2.jsx   (8383903e7d8d4fdda1bffea11ab9723795d8c317)
  IDENTICAL api/e2.js   == 3c2d63a:web/src/api/e2.js       (3aa23a077c0f73131024781424028c609db46e80)
  IDENTICAL pages/A2.jsx == 04f9606:web/src/pages/A2.jsx   (529dcc8311644c3a0f989ac6fa4a177edf2859c4)
  IDENTICAL pages/B4.jsx == 3c2d63a:web/src/pages/B4.jsx   (6e8e693ada6ec5cd781ee09350f6eb05fc08775a)

  提交后 commit-to-commit（a63808a = HEAD）：
  diff 3c2d63a HEAD -- web/src/pages/E2.jsx = 0 bytes
  diff 3c2d63a HEAD -- web/src/api/e2.js    = 0 bytes
  diff 3c2d63a HEAD -- web/src/pages/B4.jsx = 0 bytes
  diff 04f9606 HEAD -- web/src/pages/A2.jsx = 0 bytes
  ```

- **主仓零污染**：master 仍在 `f908326`；`.scratch/w-land` worktree 已 remove（作业残留零）；Owner 私产
  （eval/、tickets/、dispatch/ 作业前既有件含 journal.jsonl）零触碰；显式路径 `git add` 十二文件，未用 git add -A/.
- **Shell/SideMenu 零改动自证**：SideMenu 每组先列 `LANDING_LIT.includes(key)` 的落地裸键、再并列全量
  `proto/<KEY>`＋「原型」角标——E2/A2/B4 入表后菜单自动呈「落地」裸键×「原型」灰标三对并存；
  Shell 页头 `treeTag`（落地绿/原型灰）与面包屑按 tree 推导，既有逻辑自动生效。

## 闸门实跑（worktree 内，HEAD=a63808a 同内容工作树，提交前实跑原文）

### web 三连（最终树——冒烟件跑后已删再跑）

```
npx eslint .
  → ✖ 2 problems (0 errors, 2 warnings)
    （两条均存量：pages/D3.jsx:96 / pages/INDEX.jsx:85 react-hooks/exhaustive-deps——
      R-WIRE §四基线同款「既有 warning」，非本票文件；本票十二文件零告警）

npx vitest run
  → Test Files  17 passed (17)
    Tests  266 passed (266)
    Duration  13.89s
    （接线批收官基线 17 文件 266 例零跌：三份测试随迁不改断言——landing/E2.test.jsx 11 例、
      landing/B4.test.jsx 8 例、api/quality.test.js 10 例、api/wells.test.js 14 例、api/b4.test.js 13 例）

npx vite build
  → ✓ built in 4.04s
    （dist 零 *.test.* chunk；E2/A2/B4 各产出落地×原型双 chunk——
      E2-DSbWn3ga.js/E2-o2N_KlVY.js、A2-7BhDHftP.js/A2-rrFm8ZmN.js、B4-BJFlKW0_.js/B4-CiP55SB8.js，
      双树共存同证于构建产物）
```

### 其他闸

```
python3 tools/debt_markers.py check
  → 债务标记闸绿：web 源码债务短语全部携可解析 DEBT 标签（盘点 33 条见 report）。  [exit 0]

python3 tools/contract_coverage.py check
  → 合同覆盖率闸绿：169 条合同端点双向对账通过。                                  [exit 0]
    （该闸不扫 web/——api/e2→quality 更名与其无关，照 PROTOCOL 快扫单附跑绿）

uv 系 python 全量闸未复跑：本票零 Python 改动＋worktree 无 .venv——合并前执行台全量复跑兜底
  （W-E2/W-A2/W-B4 同款登记）。
```

### 双树渲染冒烟（验收 1——临时 vitest 冒烟 7 例，跑后即删不进提交，P2-05 同款；输出原文）

```
npx vitest run src/landing/dual-tree-smoke.test.jsx   （临时件：落地三页 fetch 级 mock×原型三页 stub 零 fetch）
  → Test Files  1 passed (1)
    Tests  7 passed (7)
    Duration  2.52s

含冒烟的全量复跑（删件前）：Test Files 18 passed (18) / Tests 273 passed (273)

  七例：
  ✓ registry 注册：LANDING_LIT 含 A1/D1/B1/B2/B5/B3/A2/B4/E2 九键（既有六页不丢）
  ✓ 落地 E2 消费真端点形状：/api/quality/{rules,tasks,issues,freshness} 四拉取实发，
    规则行真端点夹具渲染；首拉 init 头 X-Dev-User=aqiang（client 统一出口身份桩）
  ✓ 落地 A2 消费 /api/wells* 四端点（列表＋profile＋chain＋change-tickets），「渤中28-1-N2」渲染
  ✓ 落地 B4 消费 /api/wiki/pages（空态即验收态「暂无百科页——报告入库且库配置开启 wiki 支路后自动生成」）
  ✓ 原型 E2 mock 规则库种子渲染（「同一口井同一天每个班次只能有一条日产记录……」）；问题单页签
    p7 流转入「复核」后「复扫」按钮在位（v0.5 人工触发复扫语义）——全程 stub fetch 断言零调用
  ✓ 原型 A2 内嵌 WELLS 种子渲染（N-02 默认选中「渤中28-1-N2」）——零 fetch
  ✓ 原型 B4 mock 目录种子渲染（「《N-02 井完井报告》」）——零 fetch
```

## 偏差

1. **`api/e2.test.js` 随模块更名迁 `api/quality.test.js`**：票面工序 1 只点名「api/e2.js → api/quality.js」
   与「pages/__tests__/E2.test.jsx → landing/E2.test.jsx」；api 层测试不随迁则 import './e2.js' 断链、
   三连即红——按「更名」语义机械随迁（仅 import 与头注模块名随改，断言零改动），验收 4「wells/quality/b4
   测试不跌」的「quality 测试」即此件。
2. **两份随迁页测试的「落位注释」随迁改写**：E2.test.jsx 五行／B4.test.jsx 两行注释原述「落 pages/__tests__
   子目录避免 Shell 动态 glob 切 chunk」——该约束落地树不适用（landing/ 由 registry.js 显式导入，非 glob 面），
   原文照搬会与新落位自相矛盾；改为「随页迁落地树（W-LAND 双树归位）＋约束不适用缘由（指回 W-E2 偏差 2）」。
   断言与用例零改动。
3. **冒烟件跑后即删**：双树渲染冒烟 7 例为验收证据件，照 P2-05「临时 vitest 冒烟，跑后即删」先例不进提交
   （输出原文已附上节）；最终树三连（266 例）与冒烟（273 例含冒烟）分别留痕。
4. **worktree 依赖用 `npm ci`**（499 包）：沿用 W-A2 偏差 4／W-B4 偏差 5 结论（symlink 方案曾被主仓根级
   node_modules 破坏 vite 配置解析）；随 worktree 清理一并删除，未动主仓 node_modules。
5. **LANDING_MODULES 追加位次**：E2/A2/B4 追加在既有六键之后（键序 A2/B4/E2）——`LANDING_LIT` 序只影响
   注册表可读性，菜单序由 roles.js 组内序决定（SideMenu 按 LANDING_LIT.includes 过滤），落地默认页
   DEFAULT_LANDING_KEY 仍 A1，零行为影响。

## 疑点（待 L0 裁决，不动手）

1. **双树冒烟是否升格为常驻回归件**：本票按先例临时件跑后即删；7 例（registry 点亮断言＋落地三页真端点
   形状消费＋原型三页自包含零 fetch）若要防回归（例如防再次「直接改原型树」），可另立票落 `landing/` 常驻
   测试或 lint 闸（如禁 pages/*.jsx 出现 api import 的树别规则）——请裁决。
2. **`window.__traces` 双注册共存**：landing 三页与原型三页对同键（E2/A2/B4）各注册一次 `window.__traces`
   （同串）；TraceBar 仅原型树消费（landing traceText 恒空），同键同串下无可见影响——如实登记，不另行收口。
3. **原型树自包含边界的既有共享件**：还原后原型 A2 仍 import `../data/changeTickets.jsx` 与
   `../shell/TraceBar.jsx`（3c2d63a/04f9606 原态即如此，属原型树快照自带的 data/shell 资产，非 api 层）——
   「零 api import」验收语义下自包含闭环成立（冒烟 stub fetch 零调用实证）；是否把 data/ 视作原型树专属资产
   属盘点口径问题，请裁决（本票按「还原逐字」红线原样保留）。
