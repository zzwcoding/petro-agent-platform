# W-LAND 审查拍回报（T1 关票前独立审查）：fix/w-land 单 commit a63808a——双树归位六节审查

- 被审对象：commit **a63808a**（全 SHA a63808a2878f6775c2646829f110fbba667b6b41，分支 `fix/w-land`，父＝f908326＝**master 当前 HEAD**——单 commit、零分叉、FF 可合并；恰 12 文件 +1915/−536，`git diff --name-status f908326 a63808a` 逐文件核实：M api/e2.js、A api/quality.js、R097 api/e2.test.js→quality.test.js、A landing/A2.jsx、A landing/B4.jsx、A landing/E2.jsx、R097 pages/__tests__/E2.test.jsx→landing/E2.test.jsx、R098 pages/__tests__/B4.test.jsx→landing/B4.test.jsx、M landing/registry.js、M pages/A2.jsx、M pages/B4.jsx、M pages/E2.jsx——**12 文件全部限 web/src**）。
- 作业方式：**全程只读**。被审树内容一律 `git show a63808a:<path>`／blob hash 取证。**派发前提修正**：dispatch 称「主树当前在该分支上携 Owner 私产未提交改动」，实测主树检出在 **master（f908326）**、工作树未提交面仅 dispatch 三项 Owner 私产（journal.jsonl 修改＋pending/＋W-LAND.dev.md）——主树 checkout 禁令下，独立复跑改走 `git archive a63808a | tar -x -C /tmp/w-land-rev` **提交树提取**（比 worktree 更严格：`.git` 元数据亦零写入），npm ci 后三连＋双闸＋自制冒烟 7 例（跑后删）全部在提取树内完成。主仓零 checkout/零 restore/零 commit/零 stage；收工 `git status --porcelain` 与开工逐项一致。本文件为本次作业对主仓的唯一写入。
- 判据真源：`web/src/landing/registry.js` 头注（双树纪律：落地树＝真 API #/X × 原型树＝mock #/proto/X 自包含；新页落地流程＝landing/ 建 <KEY>.jsx → LANDING_LIT 加入）——a63808a 版全文读毕，头注未被本票改动。原型对照第二真源：teach 原型真源 `/Users/divh/Downloads/teach-petro-agent/prototype/app/src/`（该仓 HEAD 已前移 4aa37e1，但 E2/A2/B4 三页＋api/e2.js 四件 `git hash-object` 实测与 3c2d63a 同步点 blob **零漂移**，见三节对照表）。对账底册：W-E2/W-A2/W-B4 三份 dev 回报。
- **独立复跑数字（/tmp/w-land-rev 提取树内实跑原文，非转抄 dev）**：`npx eslint .` → **✖ 2 problems (0 errors, 2 warnings)**（存量两条 pages/D3.jsx:96 / pages/INDEX.jsx:85 react-hooks/exhaustive-deps，非本票十二文件——逐条复核与 dev 回报一致）；`npx vitest run` → **Test Files 17 passed (17) · Tests 266 passed (266)**（12.99s，与 dev 同数）；单列 `npx vitest run src/api/{quality,wells,b4}.test.js` → **10＋14＋13＝37 passed**；`npx vite build` → **✓ built in 3.98s**（dist 零 *.test.* chunk；E2-DSbWn3ga/E2-o2N_KlVY、A2-7BhDHftP/A2-rrFm8ZmN、B4-BJFlKW0_/B4-CiP55SB8 **三对双 chunk 与 dev 回报逐字同 hash**——同内容确定性旁证）；`python3 tools/debt_markers.py check` → **绿（33 条盘点）**、`python3 tools/contract_coverage.py check` → **绿（169 条双向对账）**；自制双树冒烟 `rev-dual-tree-smoke.test.jsx` 7 例 → **7 passed**（跑后即删，不属被审提交）。

---

## 一、diff 全量嗅探

### 结论：〔通过——12 文件零夹带，逐块定性与票面六工序一一对应；后端/chat 既有链零触碰〕

1. 〔通过〕**文件面严格限界**：恰 12 文件全在 web/src（票面边界红线「只动 web/src」兑现）；app/、alembic、compose、config、package.json/lockfile、Shell.jsx、SideMenu.jsx、roles.js、data/、flows/ 零触碰（`git diff --name-status` 全量核对）；Owner 私产零收编。
2. 〔通过〕**逐块定性（票面工序 → 文件）**：
   - **工序 1 E2 落地化**：`landing/E2.jsx`（A，501 行）vs `f908326:pages/E2.jsx` diff **恰一行**——`} from '../api/e2.js'` → `'../api/quality.js'`（:12；pages/ 与 landing/ 同为 src 一级子目录，`'../api/…'` 深度不变，其余 500 行逐字不动）；`api/quality.js`（A，66 行）vs `f908326:api/e2.js` diff **空**（纯更名零语义变，见二节）；`api/quality.test.js`（R097）diff 仅头注模块名＋import 行两处（it() 计数 10＝10）；`landing/E2.test.jsx`（R097）diff 仅 import 同层化（`'../E2.jsx'`→`'./E2.jsx'`、`'../../api/client.js'`→`'../api/client.js'`）＋落位注释五行改写（断言零改动，it() 11＝11）。
   - **工序 2 E2 原型还原**：`pages/E2.jsx`、`api/e2.js` 两处 M——blob hash 与 3c2d63a 全同（三节表）。
   - **工序 3/4 A2**：`landing/A2.jsx`（A）vs `f908326:pages/A2.jsx` diff **空**（字节级迁移）；`pages/A2.jsx` 还原态 blob＝04f9606（三节表）。
   - **工序 5/6 B4**：`landing/B4.jsx`（A）vs `f908326:pages/B4.jsx` diff **空**；`landing/B4.test.jsx`（R098）diff 仅 import＋落位注释两行改写（it() 8＝8）；`pages/B4.jsx` 还原态 blob＝3c2d63a。
   - **注册点亮**：`registry.js` diff 恰 +3 行——`A2/B4/E2: () => import('./X.jsx')` 追加在既有六键后，形态照 B1/B3 条目逐字同构；`LANDING_LIT`＝Object.keys 派生、`DEFAULT_LANDING_KEY='A1'` 未动。
3. 〔通过〕**pages/__tests__ 清空自证**：`git ls-tree a63808a web/src/pages/__tests__/` 空（两测试 R 走，无残留文件）。
4. 〔通过〕**零夹带独立 grep**：分支树全 web/src 内 `api/e2` 引用仅两处且皆合法——`pages/E2.jsx:10`（还原原型页 import 还原 mock，文件在位）＋`api/quality.test.js:2`（头注历史表述）；`quality.js` 引用恰两处（landing/E2.jsx＋quality.test.js）——**零断链**。

## 二、落地化核验

### 结论：〔通过——三页迁移等价性 A2/B4 字节级/E2 单行 import；注册形态照既例；Shell/SideMenu 零改动自动双列；更名全引用闭环〕

1. 〔通过〕**迁移等价性**：landing/A2.jsx、landing/B4.jsx 与迁移前 pages 版 **diff 空字节级全等**（超过票面「仅 import 路径」验收线）；landing/E2.jsx 仅 :12 import 行差（e2→quality 更名随迁，唯一必改点）。
2. 〔通过〕**registry 注册形态**：三新条目 `() => import('./X.jsx')` 与 B1/B2/B5/B3 既有形态逐字同构；`LANDING_LIT = Object.keys(LANDING_MODULES)` 派生点亮（无需手工双写）；键序追加尾部仅影响注册表可读序，菜单序由 roles.js 组内序决定（dev 偏差 5 复核属实，零行为影响——冒烟第 1 例实证 LANDING_LIT 全序 `['A1','D1','B1','B2','B5','B3','A2','B4','E2']`）。
3. 〔通过〕**Shell/SideMenu 零改动自证**：两文件不在 12 文件清单（`git diff f908326 a63808a -- web/src/shell/` 空）。SideMenu 既有逻辑＝每组先列 `LANDING_LIT.includes(key)` 落地裸键、再并列全量 `proto/<KEY>`＋「原型」角标——三键入 LANDING_LIT 后菜单自动呈三对「落地裸键×原型灰标」并存（roles.js:14 A2 井档案/:21 B4 报告百科/:36 E2 数据质量台 三键本在组内）；Shell 页头 `treeTag`（落地绿/原型灰）＋面包屑（落地树·真 API/原型树·mock）按 tree 推导自动生效。
4. 〔通过〕**api 更名全引用闭环**：quality.js 内容与旧 wired e2.js **diff 空**——纯文件名更名，九函数签名/路径（`/quality/rules|tasks|issues|transitions|freshness`，client 统一出口拼 `/api` 前缀）/方法零变，**W-E2 对 E2 合同册 v0.5 的端点级核验原样承继**（后端 app/api/quality.py 同名前缀在位）；引用面闭环见一节 4 条。

## 三、原型还原逐字核验（主查）

### 结论：〔通过——四处 blob hash 级 diff 全零，且与 teach 原型真源工作树四件全同；原型树自包含闭环实证〕

**blob-hash 对照表（本审查独立 `git rev-parse`/`git hash-object` 实测）**：

| 被审文件（a63808a） | 参照 | blob hash | 判定 |
|---|---|---|---|
| web/src/pages/E2.jsx | 3c2d63a:web/src/pages/E2.jsx | 8383903e7d8d4fdda1bffea11ab9723795d8c317 | **IDENTICAL** |
| web/src/api/e2.js | 3c2d63a:web/src/api/e2.js | 3aa23a077c0f73131024781424028c609db46e80 | **IDENTICAL** |
| web/src/pages/B4.jsx | 3c2d63a:web/src/pages/B4.jsx | 6e8e693ada6ec5cd781ee09350f6eb05fc08775a | **IDENTICAL** |
| web/src/pages/A2.jsx | 04f9606:web/src/pages/A2.jsx | 529dcc8311644c3a0f989ac6fa4a177edf2859c4 | **IDENTICAL** |

- 四组 hash 与 dev 回报所载逐一相符（dev 无虚报）；blob 全同即 commit-to-commit diff 空的强证明，票面验收 3「diff 空」以更强证据达成。
- **teach 原型真源交叉对照**：`/Users/divh/Downloads/teach-petro-agent/prototype/app/src/` 下 pages/E2.jsx、api/e2.js、pages/B4.jsx、pages/A2.jsx 四件 `git hash-object` 实测 = 上表四 hash 逐字相同（teach HEAD 4aa37e1，三页自 3c2d63a 同步点零漂移；A2 在 teach 侧从未被接线，与 04f9606 前态同）——还原源正确性双真源印证。
- 〔通过〕**原型树自包含闭环**：pages/E2.jsx 唯一局部 import＝`'../api/e2.js'`（还原 mock，其自身 **0 import**——种子内聚无 fetch）；pages/A2.jsx 局部 import 仅 `'../shell/TraceBar.jsx'`（DEV 旗）＋`'../data/changeTickets.jsx'`（TICKETS 种子）——04f9606 原态即如此，属原型快照自带 data/shell 资产、非 api 层（dev 疑点 3 复核属实，「零 api import」语义下闭环成立，冒烟 stub fetch 零调用实证）；pages/B4.jsx 局部 import 仅 react/antd/icons（**零**本地模块 import）。
- 〔通过〕**原型 E2 复扫按钮在位**（票面验收 1 后半）：pages/E2.jsx:348 行内「复扫」按钮（`flowCard(c.id,'rescan')`）随 blob 逐字还原在位——dev 冒烟第 5 例交互实证＋blob 等价双证。

## 四、双树渲染与菜单

### 结论：〔通过——自制冒烟 7/7：落地三页真端点形状消费×原型三页 mock 零 fetch 并存；NotLit 不可达；build 双 chunk 三对且零 test chunk〕

1. 〔通过〕**自制冒烟（提取树内独立编写，跑后即删）7 例全过**：①LANDING_LIT 九键全序在册（既有六页不丢）；②落地 E2 render 后 `/api/quality/rules|tasks|issues|freshness` 四拉取 URL 实发＋规则行渲染；③落地 A2 `/api/wells` 列表＋`/api/wells/N-02`（profile/chain/change-tickets）实发＋「渤中28-1-N2」渲染；④落地 B4 `/api/wiki/pages` 实发＋「暂无百科页」空态渲染；⑤⑥⑦原型 E2（规则种子文本）/A2（内嵌 WELLS「渤中28-1-N2」）/B4（目录种子「N-02 井完井报告」）渲染且 **stub fetch 断言零调用**——两树行为面与票面验收 1 全符。
2. 〔通过〕**NotLit 不出现**：三键 ∈ LANDING_LIT → Shell `LANDING_LAZY` 命中三键 → 落地树三 hash 均渲染真页（NotLit 仅对其余未点亮键可达）；原型树三键经 Shell LAZY glob（硬编码清单含 A2/B4/E2）渲染。
3. 〔通过〕**build 产物双树共存**：三页各产落地×原型双 chunk（chunk 名与 dev 回报逐字同 hash）；dist 内 *.test.*/__tests__ chunk **0** 个（assets 全列复核）。

## 五、测试与回归

### 结论：〔通过——266 例零跌且迁移零断言改动独立复核；wells/quality/b4 三件不跌；双闸绿〕

1. 〔通过〕**计数与断言**：全量 vitest **17 文件 266 例全过**（12.99s）；三份随迁测试 it() 计数迁移前后 **11/8/10＝11/8/10**（`git show` 逐文件 grep 计数），且 diff 仅 import＋注释——**断言零改动**成立。
2. 〔通过〕**三件 API 测试不跌**：quality 10 / wells 14 / b4 13 全过（单列实跑 37 passed）——票面验收 4 后半锁定。
3. 〔通过〕**eslint**：0 error / 2 warning，两条均为存量（pages/D3.jsx:96、pages/INDEX.jsx:85，本票十二文件零告警——逐条定位复核）。
4. 〔通过〕**双闸独立复跑（提取树内）**：debt_markers check 绿（33 条盘点）；contract_coverage check 绿（169 条）。
5. 〔登记〕uv 系 Python 全量闸未复跑：本票零 Python 改动（12 文件全 web/src——一节实证），提取树无 .venv；与 dev 同口径由合并前执行台全量复跑兜底。

## 六、接线成果保全（与 W-E2/W-A2/W-B4 dev 回报交付清单对账）

### 结论：〔通过——保全由字节级等价构造性成立：三落地页与迁移前接线版 diff 全零/仅更名行，R-WIRE 三份处置表逐字承继；九/四/两端点消费逐一在位〕

1. 〔通过〕**E2 九端点**（对账 W-E2 dev §产物＋R-WIRE E2-1~E2-13 处置表）：landing/E2.jsx 与 f908326 接线版仅 :12 更名行差 → 全部处置逐字承继。消费面独立定位：首屏四拉取 `Promise.all([getQualityRules(), listQualityTasks(), listQualityIssues(), getFreshness()])`（:59）、规则启停 `setQualityRuleEnabled`（:115）、受理 `startQualityTask()` 202（:129）、轮询 `useTaskPolling(taskId,{path:'/quality/tasks'})`（:80-81）、流转 `transitionQualityIssue`（:140）——第 9 函数 `getQualityTask` 按轮询底座设计（E2-8）由 useTaskPolling 经 client 消费，api 层导出＋quality.test.js 10 例覆盖不缺。
2. 〔通过〕**A2 四端点**（对账 W-A2 dev＋R-WIRE A2-1~15）：landing/A2.jsx **字节级全等**迁移 → 处置全承继。消费面：`listWells`（:131）＋`Promise.all([getWellProfile, getWellChain, listWellChangeTickets])`（:154）＋`wellOptionLabel`（:175）——四端点＋文案拼装全在位。
3. 〔通过〕**B4 两端点＋证据弹层**（对账 W-B4 dev＋R-WIRE B4-1~11）：landing/B4.jsx **字节级全等**迁移 → 处置全承继。消费面：`listWikiPages({lib,keyword})`（:270）＋`getWikiPage`（openPage :291）＋`loadClaimEvidence` 懒加载复用 kb.js（:52）＋`glossaryChipView`（:107）。
4. 〔通过〕**api 层零动**：api/wells.js、api/b4.js、api/kb.js、api/client.js 本票零触碰（不在 12 文件清单）——接线批 api 层资产原样。

## 发现清单（每条带 file:line＋影响评级＋建议处置；行号实测于 a63808a 树）

| # | 位置 | 发现 | 影响 | 建议处置 |
|---|---|---|---|---|
| F1 | （流程面）dispatch 前提 | dispatch 称「主树当前在 fix/w-land 分支检出」，实测主树在 **master（f908326）**、工作树仅 dispatch 三项 Owner 私产——本审查改走 `git archive` 提取树复跑（.git 元数据亦零写入，严于 worktree 先例） | 流程登记（无代码影响） | 执行台合并工序知悉即可 |
| F2 | web/src/api/wells.js:4-5；web/src/api/b4.js:4-5 | 两处 api 层头注括号注「内嵌种子原型（pages/A2.jsx WELLS 常量…／pages/B4.jsx 的 PAGES/EVIDENCE…——本批在页面侧退役）」：W-A2/W-B4 时点陈述（当时 pages/ 下即被接线页），W-LAND 还原后 pages/ 下种子已回归，退役对象实为 landing/A2.jsx、landing/B4.jsx——注释出现**树别歧义**（对比语义「api 层不持数据 vs 内嵌种子原型」在双树纪律下反而更贴切，仅「本批在页面侧退役」半句过时） | 低（纯注释漂移，零行为影响；不阻塞关票） | 随下次触碰顺带把两处括号注改指 landing/<KEY>.jsx，或 L0 登记豁免（历史陈述） |
| F3 | web/src/landing/E2.jsx:14 vs web/src/pages/E2.jsx:12；A2/B4 同构 | `window.__traces` 三键双树各注册一次（dev 疑点 2）——本审查逐键比对：E2/A2/B4 两树字符串**逐字相同**，TraceBar 仅原型树消费（Shell traceText 原型树才取值），同键同串下无可见影响 | 极低（登记性质） | 维持 dev「如实登记不收口」；若日后两树 trace 语义分叉再立票收口 |
| F4 | web/src/pages/A2.jsx:6-7 | 原型 A2 import `../shell/TraceBar.jsx`＋`../data/changeTickets.jsx`（dev 疑点 3）——04f9606 原态即如此，属原型快照自带共享资产，「零 api import」自包含语义成立（冒烟零 fetch 实证）；「data/ 是否原型树专属资产」属盘点口径 | 疑点延续（登记性质） | 口径裁决归 L0；本票按「还原逐字」红线原样保留正确 |
| F5 | （票面疑点延续）双树冒烟常驻化 | dev 疑点 1（7 例冒烟升格常驻回归件/树别 lint 闸）——本审查自制 7 例独立复现同结论，实证该防线可低成本的落地；「防再次直接改原型树」目前无机器闸（本次靠 blob hash 对照人工把守） | 建议级（非缺陷） | 归 L0 裁决：另立票落常驻测试（如 LANDING_LIT 九键断言＋原型树禁 api import lint）或维持人工闸 |

无缺陷级（高/中）发现；无阻塞关票项。五条发现中仅 F2 为代码注释面微瑕，余为流程登记与疑点延续。

## 零修复动作声明

**本审查全程零修复动作已执行**：未改任何被审代码/配置/合同/测试；主仓工作树零 checkout/零 restore/零 commit/零 stage，Owner 私产三项（dispatch/journal.jsonl 改动、dispatch/pending/、W-LAND.dev.md）全程零接触且收工 `git status --porcelain` 复核与开工逐项一致；teach 原型真源零写入（仅 `git hash-object` 只读取证）；独立复跑（三连＋双闸＋自制冒烟 7 例）全部在 `/tmp/w-land-rev` 提取树内完成，冒烟临时件跑后已删，提取树不属主仓且可随时整体清除。本文件为本次作业对主仓的唯一写入。所有发现均为登记性质，修复/裁决动作归后续票或 L0/Owner。
