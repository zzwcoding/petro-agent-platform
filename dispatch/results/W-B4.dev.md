# W-B4 开发拍 回报

## 产物

- **提交**：`0b573a4`（分支 `fix/wire-b4`，基于派发时 master `cd9a9c7` **单提交**；**worktree `.scratch/wire-b4` 已验后清理**，分支与提交保留待合并）
- **文件**（票面点名范围，`git show --stat 0b573a4`：4 files changed, 898 insertions(+), 210 deletions(-)）：
  - `web/src/api/b4.js` **新建**（159 行）——B4 两读端点真 API 接口层（经 client.js：`get`＋统一错误包＋X-Dev-User 身份头；wire snake→视图 camel 折回，`api/wells.js` 先例同构）；`loadClaimEvidence` 证据弹层懒加载编排（复用 `api/kb.js` 既有 `listFragments`/`getFragmentContext`）；`glossaryChipView` 台账卡展示映射纯函数
  - `web/src/api/b4.test.js` **新建**（250 行，13 例）——两端点路径/查询参数/身份头/折回映射/空态形状/`wiki_not_found` 透传/懒加载 fail-closed/卡片映射
  - `web/src/pages/B4.jsx` 改写（432 行改动）——内嵌种子全退役（PAGES/EVIDENCE/CLAIMS/GLOSSARY/W1_SEED/W1_CURRENT/W2_CURRENT/CUR_VER/SOURCE_COLORS/GEN_OPERATOR/本地 filter/statusTagOf 全撤），切真后端两端点
  - `web/src/pages/__tests__/B4.test.jsx` **新建**（267 行，8 例）——落 `pages/__tests__/` 惯例位（pages/ 直下会被 Shell.jsx 单层动态导入 glob 切进 dist——票面注意④），fetch 级 mock 走真 api 层＋真页面代码
- **主仓零污染**：派发时 master `cd9a9c7`；Owner 未提交私产（dispatch/journal.jsonl 改动、pending/）零触碰；worktree 已 remove，主树无新增文件
- **环境事实**：真后端 uvicorn :8000 全程在跑（master 最新——票面前提属实，未代启未代改）；wiki_page 表无种子，全程保持空态验收态，业务数据零写入

## 闸门实跑（worktree 内，提交前实跑原文）

```
npx eslint .
  → ✖ 2 problems (0 errors, 2 warnings)
    （两条均存量：pages/D3.jsx:96 / pages/INDEX.jsx:85 react-hooks/exhaustive-deps——
      R-WIRE §四基线同款「既有 warning」，非本票文件；本票四文件零告警）

npx vitest run
  → Test Files  17 passed (17)
    Tests  266 passed (266)        （master 基线 245 例＋本票 21 例＝api 13＋页面 8；
                                     零压制零删除——B4 原无任何测试）

npx vite build
  → ✓ built in 3.97s               （dist/assets/B4-BAvS3Dio.js 14.78 kB 正常产出；
                                     测试落 __tests__ 子目录不进 glob，dist 无死 chunk）

uv run python tools/debt_markers.py check
  → 债务标记闸绿：web 源码债务短语全部携可解析 DEBT 标签（盘点 33 条见 report）。
```

TDD 痕迹：`api/b4.test.js` 首跑红（模块不存在，rollup 解析失败）→ 实现后 13 例绿；`B4.test.jsx` 首跑对旧 mock 页 7 红 1 过 → 新页面后 8 例全绿。

### 版本族零残留复核（B4-11，提交后 grep 原文）

```
$ git show fix/wire-b4:web/src/pages/B4.jsx | grep -n "version\|CUR_VER\|rollback\|回滚\|W1_SEED\|W1_CURRENT\|\.replace("
  （零命中——仅剩 currentVersion 消费服务端字段；页签枚举两枚 catalog/read 实测在位）
$ git show fix/wire-b4:web/src/pages/B4.jsx | grep -nE "挂后续批|挂账|未接线|留后续票|随其票|接线预留|产品化批"
  （无裸债务短语）
```

### curl spot check（两端点连通＋空态形状＋404 探针，`X-Dev-User: aqiang`，原文）

```
=== ① GET /api/wiki/pages（空态——wiki_page 无种子） ===
{"items":[],"total":0}
[HTTP 200]
=== ② GET /api/wiki/pages?lib=完井报告库&keyword=N-02（服务端筛选参数化） ===
{"items":[],"total":0}
[HTTP 200]
=== ③ GET /api/wiki/pages/wiki-n02-completion（读页——404 wiki_not_found） ===
{"code":"wiki_not_found","message":"百科页不存在（含 wiki 开关关未生成）：wiki-n02-completion"}
[HTTP 404]
=== ④ GET /api/wiki/pages/NOPE-404（直调未知 id） ===
{"code":"wiki_not_found","message":"百科页不存在（含 wiki 开关关未生成）：NOPE-404"}
[HTTP 404]
=== ⑤ 无身份头探针 ===
{"items":[],"total":0}
[HTTP 200]
=== ⑥ GET /api/kb/fragments?report_id=rpt-n02-completion&type=all&keyword=（证据弹层复用件 B2 端点 1——报告不在库形状） ===
{"code":"kb_not_found","message":"报告不存在：rpt-n02-completion"}
[HTTP 404]
```

（⑤⑥为取证探针：⑤＝后端身份桩对无头请求按默认角色放行的既有行为，非本票改动面——api 层恒携 `X-Dev-User`（测试锚定），如实登记归疑点 5；⑥＝懒加载链路上源报告行缺失时弹层走内联错误态（诚实不伪造），与「锚切片不在台账」的 fail-closed 空态互补，两路径均有测试。）

## R-WIRE §3 差异清单逐条处置表（票面验收项）

| # | R-WIRE 判定 | 处置 |
|---|---|---|
| B4-1 | A（目录行映射：key←id、src←source_report.doc、slug 不在端点 1） | ✔ 已接端点 1；`listWikiPages` 折回 `sourceReport` 嵌套对象，目录行副行「来源：{sourceReport.doc}」；rowKey 改 `id`（slug 稳定性载体）；目录页未用 slug 与 R-WIRE 判定一致 |
| B4-2 | A（当前版列→`current_version`） | ✔ 目录「当前版」列与读页「当前版：vN」蓝 Tag 全消费 `currentVersion`；`CUR_VER` 常量退役 |
| B4-3 | A（本地 status 判定退役→服务端 status） | ✔ `statusTagOf` 正文扫描整体删除；目录状态列＋读页元数据条两处消费服务端 `status` 直渲（`STATUS_COLOR` 两值色映射保留展示层：字段待核对橙/正常绿，未知值兜底 default——值域即服务端两态，零第三态） |
| B4-4 | B（目录筛选参数化＋计数拼装） | ✔ 本地 filter 退役→`listWikiPages({lib, keyword})`（lib 三选项含 all、keyword 过 trim）；「筛选结果 X / Y 条」＝items.length＋total（total 全量计数服务端先数）；页签「百科页（N）」计数改 total；输入 250ms 防抖（R-WIRE 明示可选件） |
| B4-5 | B（openPage 异步化＋404 态） | ✔ `openPage` 改拉 GET /pages/{pageId}：Spin 加载态＋404 `wiki_not_found` 内联 `errText` 三段（message·code·trace）＋重试按钮＋seq 竞窗守卫（快速连开两页旧响应不回写）；client 已 toast 错误包、页面不重复弹（测试锚定 notify 恰 1 次） |
| B4-6 | A（元数据条字段映射＋常量退役） | ✔ 来源报告←`sourceReport.doc`（链 #/B1）、生成来源←`generationSource`（`SOURCE_COLORS` 常量退役——v0.4 单态直渲）、操作人←`operator`（`GEN_OPERATOR` 常量退役）、slug←`detail.slug`；`digest` api 层携带、页面无消费位（R-WIRE 登记项照旧不消费） |
| B4-7 | A＋小（related_objects 消费 DTO） | ✔ `RELATED` 常量删除；label「井 {id}」前端拼装（type=well 判别）、detail←`summary`、links 改消费 DTO（`#/A2`·`#/B5` 硬编码撤——`LINK_LABELS` 链名映射为展示层选择，未知链原样展示） |
| B4-8 | A（解析器原样保留＋种子退役） | ✔ `Md`/`renderInline` 五族 `[[…]]`（well/route/claim/term/flag）＋bold 解析器**原样保留**（R-WIRE 证实与真后端 content 兼容），仅加 ctx 参数注入 claims/glossary 索引与 sourceReportId；`W1_SEED`/`W1_CURRENT`/`W2_CURRENT`/`.replace` 造版工艺整体退役 |
| B4-9 | B（证据弹层懒加载——复用 kb.js） | ✔ `loadClaimEvidence`（api/b4）：按 `sourceReport.id` 走 `kb.listFragments` reportId 读法过滤锚切片→逐条 `kb.getFragmentContext` 回捞原文；**未展开零请求**（测试锚定）；claims[].text 补显论断句；fail-closed 双层＝无锚论断不渲染「证」（eager）＋锚切片不在台账弹层空态不伪造回链（lazy）；「在切片管理中定位」维持跳 `#/B2` 读面（⑩ locator 归 B2 册出入对账 10——见疑点 1）；⑩未动 |
| B4-10 | B（glossary card→展示字段映射） | ✔ `glossaryChipView`：kind metric→「指标口径」/term→「业务术语」；ref→「指标台账/术语台账 #N」拼装；extra 组装（指标＝统计粒度/单位、术语＝有效期——**后端 term 卡实况无 expires_display 键，如实留空不硬造**，见偏差 3）；指标状态数组折串；状态色映射生效中/有效绿、待联席裁决橙、未知 default；`GLOSSARY` 常量删除，GlossChip 渲染器复用 |
| B4-11 | 无（版本族零残留确认） | ✔ 提交后 grep 复核零残留（输出原文见上）：两页签 catalog/read、无 `?version=`、无回滚/版本页签、CUR_VER/种子双常量/.replace 造版全退役 |

补充：camel 折回 vs R-WIRE 蛇形消费点＝W-A2 偏差 5 同款等价处置（api 层折回 camel、页面消费 camel，折回保真由测试锚定）；空态验收＝目录空态渲染「暂无百科页——报告入库且库配置开启 wiki 支路后自动生成」＋页签（0）＋「筛选结果 0 / 0 条」（页面测试锁定，真后端空态实测见 spot check ①）。

## 偏差

1. **camel 折回 vs R-WIRE 蛇形**：R-WIRE §3 处置表按蛇形（source_report/current_version 等）写消费点；实现按 `api/graph.js`/`api/wells.js` 先例在 api 层折回 camel——同一差异清单的等价处置，见 B4-1～B4-10 各行。
2. **master 派发中前移**：开工时 master＝`cd9a9c7`（分支基点），回报写就时主树 master 已前移三拍（`d7cac8e`/`824dd32`/`4b03ae7`——阶段 3 规划与拍板文档，全部限 tickets/ 文档面；`git diff --name-only cd9a9c7 master -- web/` 零输出，与 web/ 零交集、无冲突面）；FF 前 rebase 与否归执行台合并工序。
3. **后端 term 卡无 expires_display**：合同 B4 v0.4 w2 演示卡带 `expires_display`，后端实装 term 卡仅 type/def/status/owner 四键（app/domains/derivatives/service.py:286-293）、metric 卡七键——chip「有效期至」段按缺省如实留空（`glossaryChipView` 对两形都健壮，合同若补键前端零改）。票面 C 类后端小改清单为「无」，不擅动后端，登记待 L0。
4. **空态文案一句**：目录 Empty 文案「暂无百科页——报告入库且库配置开启 wiki 支路后自动生成」为合同生产/消费边界语义的页面复述（E2 空态文案同款先例），非业务事实新增。
5. **npm ci 装 worktree 依赖**：沿用 W-A2 偏差 4 结论（symlink 方案已被主仓根级 node_modules 破坏 vite 配置解析），worktree 内 `npm ci`（499 包，package-lock 与主树同版）。

## 疑点（待 L0 裁决，不动手）

1. **「在切片管理中定位」locator（mock 更正清单⑩）**：B2 页 `?chunk=` query 定位未落位（B2 册出入对账 10），本票维持纯跳转 `#/B2`。该挂账去向在债务闸下不可解析（非票号/阶段/Owner），故代码内未加 DEBT 标签、仅本回报登记——是否需改挂可解析去向（如折入某票号）请裁决。
2. **落地树注册**（R-WIRE §五共性件③＋UI-13 壳层标题惯例）超出票面边界红线——原型树 B4 接线完成后是否补「B4 落地化」票（同 W-A2 疑点 5，三页落地化宜一并裁决）。
3. **后端 term 卡 expires_display 缺键**（偏差 3）：合同演示形状与 P2-04 实装投影不一致——补键（后端小改）或改合同注记，请裁决归属。
4. **证据弹层 N+1 请求形态**：每锚切片一次 context 回捞（当前每论断 1～2 锚可接受）；报告页规模上来后是否需要批量 context 端点——归 B2/B4 合同演进批，不在本票。
5. **无身份头请求 200**（spot check ⑤）：后端身份桩对无 `X-Dev-User` 请求按默认角色放行——B4 全员可见页面下无实害，但与「未认证 401」合同行（B4 错误码草案）的字面有出入；属后端安全域（require 预埋期口径），归 L0/D3 线裁决，本票前端恒携头不受影响。
