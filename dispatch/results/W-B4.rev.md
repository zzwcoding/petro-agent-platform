# W-B4 审查拍回报（T1 关票前独立审查）：fix/wire-b4 单 commit 0b573a4——B4 页面数据源切真后端两端点六节审查

- 被审对象：commit **0b573a4**（全 SHA 0b573a43606f32a6bb649275850956f814400479，分支 `fix/wire-b4`，merge-base＝cd9a9c7 单 commit；恰 4 文件 +898/−210，`git diff-tree --name-only` 逐文件核实＝web/src/api/b4.js＋web/src/api/b4.test.js＋web/src/pages/B4.jsx＋web/src/pages/__tests__/B4.test.jsx）。
- 作业方式：**全程只读**。被审树内容一律 `git show 0b573a4:<path>` 取证；独立复跑以临时 worktree `/tmp/wb4-rev`（`git worktree add --detach` 到 0b573a4）承载——**派发前提修正**：dispatch 称"主树当前在该分支检出"，实测主树在 **master（4b03ae7）**、0b573a4 未合入、主树携 Owner 三项私产未提交改动（dispatch/journal.jsonl 改动＋pending/＋W-B4.dev.md），故主树 checkout 禁令下 worktree 为唯一合规复跑面（dev 拍同款先例）。worktree 用毕 `git worktree remove --force` 清理，**主树零 checkout/零 restore/零 commit**；收工 `git status` 复核与开工时逐项一致（REVERT-VERIFIED），HEAD 仍 4b03ae7。
- 合同真源：teach-petro-agent `specs/api/B4-报告百科.md` **v0.4**（两读端点/DTO 演示/错误码草案/行为规则 12 条/mock 更正清单⑨⑩——240 行全文只读取证）；差异清单真源 `dispatch/results/R-WIRE.md` §3（B4-1~B4-11）；dev 回报 `dispatch/results/W-B4.dev.md`；后端真源＝master `app/api/wiki.py`（P2-04 交付）＋`app/domains/derivatives/service.py` 卡片投影段。
- 独立复跑（/tmp/wb4-rev 内实跑原文，非转抄 dev）：`npm ci` → **499 packages**（与 dev 回报同数）；`npx eslint .` → **✖ 2 problems (0 errors, 2 warnings)**（存量两条 D3.jsx:96 / INDEX.jsx:85 react-hooks/exhaustive-deps，本票四文件零告警）；`npx vitest run` → **Test Files 17 passed (17) · Tests 266 passed (266)**（12.73s）；`npx vite build` → **✓ built in 3.77s**（dist/assets/B4-BAvS3Dio.js——与 dev 回报**同 hash**；dist 内 test/`__tests__` 块 **0** 个）；`python3 tools/debt_markers.py check` → **绿（33 条盘点，与 dev 同数）**；变异验证两例（见四节）皆如预期翻红，用毕还原。

---

## 一、diff 全量嗅探

### 结论：〔通过——4 文件零夹带，退役面/新增面/保留面逐块定性与票面逐一对应〕

1. 〔通过〕**文件面严格限界**：恰 4 文件（票面点名范围）；package.json/lockfile/Shell.jsx/registry/data/flows 零触碰——`npm ci` 以现有 lockfile 成功装 499 包即**零新依赖**的旁证；Owner 私产零收编。
2. 〔通过〕**逐块定性**：
   - `api/b4.js`（159 行新建）：①头注合同锚（B4 v0.4/wells.js 先例同构声明）；②六个 wire(snake)→视图(camel) 纯映射函数（sourceReportToView/listItemToView/relatedObjectToView/claimToView/glossaryTermToView/detailToView）；③两端点 `listWikiPages`(:82)/`getWikiPage`(:95，路径参数 encodeURIComponent)；④`loadClaimEvidence` 证据弹层懒加载编排(:113-124，复用 kb.js)；⑤`glossaryChipView`(:139-159)＋三个展示常量（KIND_LABEL/LEDGER/STATUS_COLOR）。**零业务数据持有**（api/wells.js 先例同构成立）。
   - `api/b4.test.js`（250 行新建，13 例）：5 describe——端点 1×3（路径/身份头/折回/参数化/空态形状）、端点 2×2（全折回/digest 可空＋编码）、glossaryChipView×3、loadClaimEvidence×3（编排/锚失效丢弃/无锚零请求）、错误包×2（wiki_not_found 透传＋网络层 ApiError(0)）。夹具逐字照抄合同 DTO 与 wiki.py 响应模型。
   - `pages/B4.jsx`（445→457 行改写）：**退役面**＝PAGES(旧:23-40)/EVIDENCE(旧:49-55)/CLAIMS(旧:56-65)/GLOSSARY(旧:110-115)/RELATED(旧:232-243)/W1_SEED·W1_CURRENT·W2_CURRENT·.replace 造版工艺(旧:244-289)/CUR_VER(旧:293)/SOURCE_COLORS(旧:296)/GEN_OPERATOR(旧:298)/statusTagOf/本地 filter/pageKey state——12 族全撤；**新增面**＝api 消费 hooks（loadPages useCallback＋on 竞窗旗/250ms 防抖/openPage 异步＋seq 竞窗守卫/errText 内联错误态＋重试/EvidenceMark 懒加载/GlossChip 改消费 glossaryChipView）；**保留面**＝helpIcon/`__metaExpand`·WellLink（与旧版逐字同构——旧:20,45,310 vs 新:22,35,257 diff 实证零变化）/Md＋renderInline（见下）/TD_TH_STYLE/META_HELP/LIB_COLORS/页头定位行/window.\_\_traces。
   - `pages/__tests__/B4.test.jsx`（267 行新建，8 例）：5 describe——空态×1/目录字段与筛选参数化×2/读页异步化×2/证据弹层×2/404 错误态×1；fetch 级 mock 走真 api 层＋真页面代码。
3. 〔通过〕**退役零残留（独立 grep，非转抄 dev）**：W1_SEED/W1_CURRENT/W2_CURRENT/SOURCE_COLORS/GEN_OPERATOR/RELATED 四文件＋全 web/src（分支树）**零命中**；PAGES/EVIDENCE/CLAIMS/GLOSSARY/CUR_VER 命中逐条定性——全为 ①头注/测试头注释（b4.js:4、B4.test.jsx:5）②新测试夹具（PAGES_TWO/PAGES_EMPTY——不同标识符）③新展示常量族（GLOSSARY_KIND_LABEL/LEDGER/STATUS_COLOR——api 层新造映射，非退役种子）④本地 statusTagOf 余 B4.jsx:27/B4.test.jsx:5 两处注释＋A3.jsx:28（**他页同名函数，P2 期既有，本票未触碰**，非残留）；`version` 词在 B4.jsx 仅 `currentVersion`×3（:327 目录列/:414 读页 Tag/:423 元数据条）；`.replace(`/`回滚`/`rollback`/`?version=` **零命中**。
4. 〔通过〕**解析器"原样保留"实证**：`renderInline`/`Md` 新旧逐字 diff——变更仅两族：①签名加 `ctx` 形参；②`claim`/`term` 两分支由常量查表改 `ctx.claims.get(arg)`/`ctx.glossary.get(arg)` 查端点 2 投影（well/route/flag/bold 四族及 Md 各分支零字节变化，Md 行数 46=46）。五族 `[[…]]`＋bold 解析与 R-WIRE §3.1 B4-8 判定一致；term 词表外词 fallback 纯文本（新:199-202）＝台账闸防误链的更显式承载。

## 二、数据源切真核验（两端点消费形状 vs 后端实装＋snake→camel 折回）

### 结论：〔通过——两 DTO 逐键全等、嵌套三投影逐键折回、wells.js 先例同构成立；一项防御性兜底见发现 F1〕

1. 〔通过〕**端点 1**：`listWikiPages` → `GET /wiki/pages?lib&keyword`（恒传 lib、keyword trim 后透传）vs master `app/api/wiki.py:55-77`——响应 `WikiPagesResponse{items[7键], total}`：id/title/lib/source_report{id,doc}/current_version/updated/status 逐键折回为 `sourceReport`/`currentVersion`（listItemToView 全等，测试 toEqual 钉死）；`total` 透传（`?? items.length` 兜底——见 F1）；目录零二次筛选/零排序（`.sort(` 全文零命中——服务端 updated 倒序纪律遵守，合同端点清单注记）；`slug` 不在端点 1 消费（listItemToView 无 slug 键——与 R-WIRE B4-1 判定一致）。
2. 〔通过〕**端点 2**：`getWikiPage(pageId)` → `GET /wiki/pages/{encodeURIComponent(pageId)}` vs `wiki.py:123-152` `WikiPageDetailResponse` **14 键**——detailToView 14 键一一对应（id/title/lib/slug/digest/sourceReport/currentVersion/updated/status/generationSource/operator/relatedObjects/content/claims/glossaryTerms），无多余键无漏键；嵌套三投影逐键折回：`related_objects{type,id,summary,links}`、`claims{claim_id→claimId,text,evidence_chunk_ids→evidenceChunkIds}`、`glossary_terms{word,kind,ref_id→refId,card}`；`digest`/`operator` 可空如实透传（后端 `str | None`——测试钉 `digest:null` 直传）；`digest` 页面零消费（grep 计数 0——R-WIRE B4-6 登记项照旧）。
3. 〔通过〕**wells.js 先例同构**：同 `import { get } from './client.js'`（统一出口——X-Dev-User 身份头/错误包 toast/unwrapEnvelope 全继承，测试锚定 `init.headers['X-Dev-User']` 真值＋notifier 恰 1 次）、同「api 层折回 camel＋页面消费 camel」形态（W-A2 偏差 5 同款等价处置）、同「纯映射不持数据」职责划分——同构成立。`{items,total}` 形状经 client.js `unwrapEnvelope` 归一化（total 保留）。
4. 〔通过〕**卡片投影健壮性**：后端 term 卡实测恰 `{type,def,status,owner}` 四键、metric 卡七键（master service.py:286-297 逐键核对——**dev 偏差 3 属实**：合同 w2 演示卡带 expires_display、实装无此键）；`glossaryChipView` 对两形皆健壮（expires_display 缺省→extra 如实留空，api 测试第三例钉死；合同若补键前端零改——处置正确）。
5. 〔通过〕**空态形状**：`{items:[],total:0}` 原样承载（api 测试第三例＋页面空态渲染断言），与后端 wiki_page 无种子实况（五节探针①）互证。

## 三、R-WIRE §3 差异清单 B4-1~B4-11 逐条处置复核

### 结论：〔通过——11 条处置与 R-WIRE 判定逐条相符，dev 处置表无虚报；无锚/锚失效 fail-closed 双层与解析器保留两项重点全实证〕

| # | R-WIRE 判定 | 复核结论（本审查实证） |
|---|---|---|
| B4-1 | A（key←id、src←source_report.doc、slug 不在端点 1） | ✔ rowKey="id"（B4.jsx:380）；目录行副行「来源：{sourceReport.doc}」（catalogColumns render）；listItemToView 无 slug 键；openPage 消费 `p.id`——处置相符 |
| B4-2 | A（当前版列→current_version） | ✔ `currentVersion` 三消费位（B4.jsx:327 目录列/:414「当前版：vN」蓝 Tag/:423 元数据条）；CUR_VER 零残留（grep 实证）——相符 |
| B4-3 | A（本地 status 判定退役→服务端 status） | ✔ statusTagOf 正文扫描整体删除（唯一提及＝两处注释）；目录状态列＋读页元数据条两处直渲服务端 status；STATUS_COLOR 两值（字段待核对橙/正常绿）＋未知 default 兜底＝展示层映射、零第三态（合同常量表两态相符）——相符 |
| B4-4 | B（筛选参数化＋计数拼装） | ✔ 本地 filter 退役→`listWikiPages({lib, keyword})`（lib 三选项含 all；keyword trim）；「筛选结果 X / Y 条」＝pages.length＋total（B4.jsx:377）；页签「百科页（N）」＝total（:357）；250ms 防抖（:260-263，R-WIRE 明示可选件）——相符 |
| B4-5 | B（openPage 异步化＋404 态） | ✔ openPage 拉 GET /pages/{pageId}（:289-306）：Spin 加载态＋404 内联 errText 三段（errText＝message·code·trace，client.js:113-120 母本）＋重试按钮＋seq 竞窗守卫（seqRef :294，旧响应不回写）；client 已 toast、页面不重复弹（页面测试 notify 恰 1 次锚定）——相符 |
| B4-6 | A（元数据条字段映射＋常量退役） | ✔ 来源报告←sourceReport.doc（链 #/B1）、生成来源←generationSource（SOURCE_COLORS 退役、单态直渲）、操作人←operator（`?? '—'` 兜底，GEN_OPERATOR 退役）、slug←detail.slug；digest api 携带页面零消费（grep 0）——相符 |
| B4-7 | A＋小（related_objects 消费 DTO） | ✔ RELATED 零残留；label「井 {id}」type=well 判别拼装、detail←summary、links 消费 DTO（LINK_LABELS 展示层映射、未知链原样展示——测试断言 href 全等）——相符 |
| B4-8 | A（解析器原样保留＋种子退役） | ✔ 逐字 diff 实证（一节 4 条）；W1_SEED/W1_CURRENT/W2_CURRENT/.replace 零命中；ctx 注入 claims/glossary 索引与 sourceReportId——相符 |
| B4-9 | B（证据弹层懒加载——复用 kb.js） | ✔ `loadClaimEvidence`（b4.js:113-124）：`kb.listFragments({reportId})` 按来源报告整组拉台账（kb.js 注记「reportId 携带＝整表返回」——**无分页漏锚风险**）→Map 索引过滤锚切片→逐条 `getFragmentContext` 回捞；**未展开零请求**（chunks===null 守卫＋页面测试断言 fragments 调用数=0）；claims[].text 补显论断句；**fail-closed 双层实证**：eager＝无锚论断/未知 claim_id 不渲染「证」（B4.jsx:45——`!claim || 空锚` return null 覆盖 Map miss 路径）＋lazy＝锚切片不在台账 filter(Boolean) 丢弃→弹层 Empty「不伪造回链」（两路各有测试）；「在切片管理中定位」维持 `#/B2` 纯跳转（⑩ locator 归 B2 册出入对账 10，未越权补位）——相符 |
| B4-10 | B（glossary card→展示字段映射） | ✔ `glossaryChipView`：kind metric→指标口径/term→业务术语；ref→「指标台账/术语台账 #N」；extra 两族组装（term 缺 expires_display 如实留空——二节 4 条后端实况互证）；指标状态数组折串；状态色两绿一橙＋未知 default；GLOSSARY 零残留、GlossChip 渲染器复用——相符 |
| B4-11 | 无（版本族零残留确认） | ✔ 页签恰两枚 catalog/read（B4.jsx:356-358）；`?version=`/回滚/rollback/CUR_VER/种子双常量/.replace 造版全零命中（一节 3 条 grep 实证）；`version` 仅剩 currentVersion 消费——相符 |

补充复核：dev 偏差 1（camel 折回＝W-A2 偏差 5 同款等价处置）成立；dev 偏差 4（空态文案为合同生产/消费边界语义页面复述——「暂无百科页——报告入库且库配置开启 wiki 支路后自动生成」）与合同「开关关→不生成」节语义相符，非业务事实发明。

## 四、测试咬合力

### 结论：〔通过——13＋8 计数独立复核、反证抽 2 双双翻红、空态断言在位、惯例位合规〕

1. 〔通过〕**计数**：api 恰 13 例（3+2+3+3+2，worktree 实跑 13 通过）；页面恰 8 例（1+2+2+2+1）；全量 266＝既有 16 个测试文件（与 master 逐字节相同——`git diff cd9a9c7 0b573a4 -- web/src` 恰 4 文件，静态算术 266−21＝245 基线成立）＋本票 21。零压制零删除（B4 原无测试，`git ls-tree cd9a9c4` 侧 B4 无测试文件——cd9a9c7 树核实）。
2. 〔通过〕**反证抽 2（worktree 内实做，用毕还原）**：
   - 反证 1：`api/b4.js` 删 `currentVersion: r.current_version` 映射行 → `npx vitest run src/api/b4.test.js` → **1 failed | 12 passed (13)**（端点 1 toEqual 全等断言咬住字段级退役）——撤字段应红 ✔；
   - 反证 2：`pages/B4.jsx` 删 EvidenceMark fail-closed 守卫行（:45）→ `npx vitest run src/pages/__tests__/B4.test.jsx` → **2 failed | 6 passed (8)**（「无锚论断不渲染证」用例＋「未展开零请求/弹层投影」用例双双咬住 fail-closed）——守卫应红 ✔。
3. 〔通过〕**空态断言**：目录空态三断言在位（页签「百科页（0）」/「筛选结果 0 / 0 条」/「暂无百科页」文案）——验收项④锁定。
4. 〔通过〕**惯例位合规（Shell glob 红线）**：测试落 `pages/__tests__/` 子目录（E2.test.jsx 同款先例位）；Shell.jsx:21 动态导入为单层 `../pages/${key}.jsx` glob——子目录不切入；build 实证 dist 内 test 块 0 个、B4-BAvS3Dio.js 正常产出（与 dev 回报同 hash＝产物确定性好）。
5. 〔通过〕**咬合面真实性**：页面测试 fetch 级 mock 走真 api 层＋真页面代码（无组件 mock 短路）；错误包透传用例锚定「client 层恰弹一次＋页面 inline errText 不重复弹」的收口约定；网络层失败 ApiError(0) 用例在位。

## 五、curl 取证真实性（localhost:8000 只读 GET 复核）

### 结论：〔通过——dev 六探针输出逐字复现，取证解读成立〕

| # | 探针 | dev 回报 | 本审查复跑 | 判定 |
|---|---|---|---|---|
| ① | GET /api/wiki/pages（X-Dev-User: aqiang） | `{"items":[],"total":0}` 200 | 同左 | ✔ 一致 |
| ② | GET /api/wiki/pages?lib=完井报告库&keyword=N-02 | `{"items":[],"total":0}` 200 | 同左 | ✔ 一致（服务端筛选参数化连通） |
| ③ | GET /api/wiki/pages/wiki-n02-completion | 404 `wiki_not_found`（message 含「含 wiki 开关关未生成」） | 同左 | ✔ 一致 |
| ④ | GET /api/wiki/pages/NOPE-404 | 404 `wiki_not_found` | 同左 | ✔ 一致（直调未知 id 同码——合同错误码草案行） |
| ⑤ | 无身份头 | `{"items":[],"total":0}` 200 | 同左 | ✔ 复现（dev 取证解读成立：后端身份桩预埋期放行＝既有行为非本票改动面；与合同「未认证 401」字面出入归 L0——见 F5） |
| ⑥ | GET /api/kb/fragments?report_id=rpt-n02-completion&type=all&keyword= | 404 `kb_not_found`「报告不存在」 | 同左 | ✔ 一致（懒加载链上源报告缺失→弹层内联错误态路径＝诚实不伪造，与 fail-closed 空态互补） |

环境前提核实：后端 uvicorn :8000 在跑且为 master 实装（③④错误包 message 与 master errors.py 文案逐字一致）；wiki_page 全程无种子（①②）——「空态即验收态」票面前提属实，业务数据零写入。

## 六、派发中 master 前移合规与 rebase 冲突面

### 结论：〔通过——三 commit 全限 tickets/phase3 文档面、与 web/ 零交集、rebase 无冲突面；dev 偏差 2 属实〕

1. 〔通过〕**逐 commit 文件面**（`git diff-tree --name-only` 实证）：d7cac8e＝tickets/phase3/ 4 文件（README/teach 对齐草案/拍板记录/方案-LLM 问数演进）；824dd32＝tickets/phase3/ 3 文件；4b03ae7＝tickets/phase3/ 3 文件（含 L-01 票面草案-暂缓）——**三 commit 全部限 tickets/phase3/ 文档面**。
2. 〔通过〕**web/ 零输出独立复核**：`git diff --name-only cd9a9c7 master -- web/` 空；cd9a9c7..master 全量文件面恰为上述 tickets/phase3 五个文件——与分支改动面（web/src 4 文件）**交集为空**（comm 实证）→ rebase/merge **零冲突面**。
3. 〔登记〕master（4b03ae7）已越过分支基点 cd9a9c7——合并非纯 FF，rebase+FF 或 merge commit 形态归执行台合并工序（dev 偏差 2 同口径）；本节仅判无冲突面。

## 发现清单（每条带 file:line＋影响评级＋建议处置；行号实测于 0b573a4 树）

| # | 位置 | 发现 | 影响 | 建议处置 |
|---|---|---|---|---|
| F1 | web/src/api/b4.js:86 | `total: res.total ?? (res.items || []).length`——total 缺失时以**筛选后条数**冒充全量计数，「筛选结果 X / Y 条」的 Y 将失真；与合同端点 1 注记「total＝全量计数、前端零二次计数」字面有隙 | 低（后端 `total: int` 必返，现网不可达；纯防御兜底） | 可保留；若 L0 要求合同字面严格则删 fallback（getWikiPage 无同款问题）。不阻塞关票 |
| F2 | web/src/api/b4.test.js:68 | 测试名「keyword 过空省传」与实现不符——listWikiPages 对空 keyword **恒传 `keyword=`**（trim 后空串仍传输，不省传）；断言本体未测省传行为，仅命名措辞失真（后端 `keyword or None` 等价消化，零行为差） | 极低 | 随下次触碰顺手改名（如「keyword trim 后透传」）或登记即可 |
| F3 | web/src/pages/B4.jsx:47-55 | EvidenceMark.toggle 闭包读 `lazy.loading`——同 tick 内连点「证」理论上可重复发起 loadClaimEvidence（批渲染前闭包未更新）；GET 幂等、量级 1~2 请求 | 极低 | 登记；后续收敛可用 useRef 守卫。不阻塞 |
| F4 | web/src/api/b4.js:117 | loadClaimEvidence 不去重 chunkIds（同 claim 锚列表若含重复 id 将重复回捞/重复渲染弹层条目）；服务端 content 现实不产生重复锚 | 极低 | 登记不修 |
| F5 | （后端域——非本票缺陷）app/api/wiki.py `_actor: CurrentActor` | 无身份头请求 200（五节探针⑤复现）vs 合同 B4 错误码草案「未认证 401」字面出入——身份桩预埋期口径，前端 api 层恒携 X-Dev-User 不受影响 | 疑点延续（dev 疑点 5 同项） | 归 L0/D3 安全线裁决；本票零动作 |
| F6 | （后端域——非本票缺陷）app/domains/derivatives/service.py:286-293 | term 卡实装恰 type/def/status/owner 四键、无 expires_display（本审查独立核实），合同 B4 v0.4 w2 演示卡带该键——前端 glossaryChipView 已按缺省如实留空、两形健壮（测试钉死） | 疑点延续（dev 偏差 3 同项） | 补键（后端小改）或改合同注记，归属请 L0 裁决；本票零动作正确 |
| F7 | （流程面）dispatch 前提 | dispatch 称「主树当前在 fix/wire-b4 分支检出」——实测主树在 master（4b03ae7）、携 Owner 三项私产；本审查改走临时 worktree（dev 同款先例）完成复跑，主树零接触 | 流程登记（无代码影响） | 执行台合并工序知悉即可（见六节 3 条） |

无缺陷级（高/中）发现；四条低/极低发现均不阻塞关票，两条疑点延续项归属裁决权在 L0/Owner。

## 零修复动作声明

**本审查全程零修复动作已执行**：未改任何被审代码/配置/合同/测试；主仓工作树零 checkout/零 restore/零 commit/零 stage，Owner 私产三项（dispatch/journal.jsonl 改动、dispatch/pending/、W-B4.dev.md）全程零接触且收工状态复核一致；独立复跑与两例变异验证均在 /tmp/wb4-rev 临时 worktree 内完成，变异用毕 `git checkout --` 还原、worktree 已 remove（主仓 worktree 列表复核仅剩主树一项）；curl 取证全部 GET 类只读。本文件为本次作业对主仓的唯一写入。所有发现均为登记性质，修复/裁决动作归后续票或 L0/Owner。
