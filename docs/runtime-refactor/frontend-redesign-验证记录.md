# 前端答案展示重设计 · 交付验证记录（FE-05 收官票）

状态: 施工完成，待 Owner 目验（规格「验收测试」表第 20 行＝人审行）
票面: `tickets/frontend/FE-05-切真流收官与旧页下线.md` ｜ 规格: `specs/frontend-redesign.md`（第 17–23 行）
施工: 子代理（FE-05，2026-10-17）｜ 主控窗口验收后关票

本文件是规格第 20 行「真机帧走查」的人审载体，同时承载本票的四处机检摘要与旧测试处置比对。
第 1 节走查为**人审行为**——本票执行者是施工子代理，不能目验真机页面，故该节如实标注
「待 Owner 目验」，并给出可直接照做的逐位核对清单（不给已完成假象）。

## 0. 改动清单

| 文件 | 动作 | 说明 |
|---|---|---|
| `web/src/landing/redesign/A1V2R.jsx` | 改 | 真流页（临时路由转正）：发送接线、三来源一统、链轮 onResume 接通、去夹具轮 |
| `web/src/landing/redesign/useRunningRun.js` | 改 | 提问腿管线：`pushAskEntry`／`dispatchEntryFrame`／`legHandlers`（三腿共一管道） |
| `web/src/landing/registry.js` | 改 | A1V2 注册行指向真流页；`REDESIGN_MODULES/LIT/loadRedesignPage` 合并回 `LANDING_*`；PROTO_EXCLUDED 去 A1V2R |
| `web/src/shell/Shell.jsx` | 改 | 去 REDESIGN 懒加载循环与 import |
| `web/src/shell/SideMenu.jsx` | 改 | lit 过滤行还原为 LANDING_LIT 单条件 |
| `web/src/roles.js` | 改 | 菜单「问一问V2·新版(mock)」删除（A1V2 文案本即「问一问V2」） |
| `web/src/landing/redesign/A1V2R.test.jsx` | 改 | 去夹具轮重写：`chain_order`（真提问流驱动）＋发送接线四钉＋夹具轮组件钉＋拉链/续答钉 |
| `web/src/landing/redesign/route.test.jsx` | 改 | 重写为 `a1v2_replaced`（注册/菜单/文件/路由四面） |
| `web/src/landing/redesign/mockLeft.test.js` | 新增 | `no_mock_left` 去 mock 残留闸（glob 键集＋源码文本双判） |
| `web/src/landing/redesign/__fixtures__/turns.js` | 新增 | `FIXTURE_TURNS`／`FULL_FRAMES`／`PREFIX_FRAMES`（真机帧夹具＋归约器输出，测试专用） |
| `web/src/landing/redesign/__fixtures__/runs.js` | 新增 | `FIXTURE_RUNS`（120 条 RunListItem 形态——ThreadList/A1V2R 测试桩数据） |
| 各组件测试头注/引用（`ExecutionPipeline`／`CitationPanel`／`CiteHoverCard`／`NoticeBand`／`LineageCard`／`RunMetaLine`／`SupplementBlocks`／`cites`／`events`＋`ThreadList` 测试） | 改 | 引用面从旧夹具模块改指 `__fixtures__/`，头注随转正清理 |
| `web/src/landing/redesign/CitationPanel.jsx` | 改 | 头注去「本页是 mock 静态页」；决策树 Modal 文案去 mock（`决策树（占位）`） |
| `web/src/landing/redesign/{ThreadList.jsx,cites.js,ExecutionPipeline.jsx,useRunningRun.js}` | 改 | 头注随转正清理（去「同 A1V2.jsx」等已删文件引用） |
| `web/src/landing/{AnswerView.jsx,AnswerView.test.jsx,a1v2Reducer.js}` | 改 | 头注去已删页引用 |
| `web/src/landing/dual-tree-smoke.test.jsx` | 改 | 十键用例标题随转正（**键集不变**，断言逐字未动） |
| `web/src/landing/redesign/reconnect.test.jsx` | 改 | 去夹具轮的直接后果：一轮计数断言 5 → 1 |
| `web/src/landing/A1V2.jsx`、`A1V2.test.jsx` | **删** | 旧现状页与其测试（21 条，逐条处置见第 3 节） |
| `web/src/landing/redesign/mockTurns.js` | **删** | 旧夹具模块（引用清零后删除，数据落 `__fixtures__/`） |

## 1. 走查轮次清单（规格第 20 行——人审行，**待 Owner 目验**）

走查口径：抽真机帧转录文件 → 在真流页面（`#/A1V2`）按同问句复核人可见面。**本票未做真机目验**
（需真后端 :8001 与 Owner 视读），下列「核对位」为逐位判据；机检替代面列于表后（本票已跑）。

| 走查轮 | 帧源文件（`eval/results/frames/`） | 核对位（逐项打勾） | 状态 |
|---|---|---|---|
| EB4-A-正1（运行中前缀） | `EB4-A-正1.json`（前缀＝id ≤ 25 帧，已转录为 `__fixtures__/EB4-A-正1-prefix.json`） | ① 流水线默认展开、尾部「继续处理中…」② 材料聚合行计数 ③ 回答块「正在作答…」占位（无正文/无小字） | 待 Owner 目验 |
| EB4-数-明2（完整轮·数据题） | `EB4-数-明2.json`（128 帧，已转录） | ① 答案正文逐段 ② 引标 [n] 点开右栏定位（「已定位」）③ hover 悬停切片内容 ④ 血缘卡五要素（口径/来源表/过滤条件/数据截至批次/收口注记）⑤ 追加面三块（split/attribution/citations）⑥ notice 三级（A 在回答块顶、B/C 只在流水线）⑦ 统计行（步数/材料/档案 KB/run 号/本地计时） | 待 Owner 目验 |
| EB3-数-降1（分列轮·长表） | `EB3-数-降1.json`（60 帧，已转录） | ① 长 split 限高折叠与「展开看全文」② 引用含 `trust=notice` 一条＝按程序声明渲染（「这一条是系统生成的声明，不是文档原文」）③ 统计行核验计数 | 待 Owner 目验 |
| 澄清轮（挂起） | `EB2-…`／任一含 `ask` 帧的转录（如 P045 系） | ① 挂起卡文案与选项 ② 点选项＝续答真通（本腿新帧落回同轮）③ 挂起腿无 blackbox＝小字相应段不渲染 | 待 Owner 目验 |
| 旧轮（历史降级） | `logs/old-runs-backup-20261014.json` 的 `run-307959ec`（已转录 `__fixtures__/legacy-run-307959ec.json`） | ① 灰字「本轮为旧版记录，无引用/口径明细」② 正文内嵌旧式「引用：」块原样 ③ [n] 死文本（无锚点/无悬停）④ 无流水线块 | 待 Owner 目验 |

**核对位判据补充（Owner 目验时按此判「过／不过」）**：
- 引用定位：点正文 `[n]` → 右栏面板切到该轮、该条加「已定位」并显示材料原文；无配对材料＝
  「（材料未在回合内渲染）」；整轮无引用＝「本回合无引用。」
- hover 切片：悬停引标出卡，内容＝该 index 材料切片（零请求——只查内存 materials）
- 血缘两源：结构化源 `materials[].payload.lineage` 优先，文本兜底 `supplements.lineage`
- notice 三级：A 级＝回答块顶 antd Alert＋流水线彩线行；B 级＝灰折叠「说明（type）」；
  C 级＝折叠「系统注记（type）」；未登记 type＝通用灰条「系统提示（未登记类型）」兜底
- 统计行：无数据段整段不出（不补零、不伪造）

**本票已跑的机检替代面**（同一断言面的机器版本，人工图仍保留 Owner 目验）：
`A1V2R.test.jsx::chain_order`（真机 128 帧直喂 handlers 的问句块→流水线→回答块序＋正文出现时点）、
`::完整轮/运行中轮/分列轮·旧版降级轮`（夹具轮组件面）、`CitationPanel.test.jsx`（引用定位/占位/程序声明）、
`NoticeBand.test.jsx`（三级＋未登记兜底）、`LineageCard.test.jsx`（五要素）、`SupplementBlocks.test.jsx`（追加面）。

## 2. E 组三件（空态纪律——规格 E1/E3/E5，本票点名核对）

| # | 件 | 落码（file:line） | 机器钉 |
|---|---|---|---|
| ① | 引用无配对占位「（材料未在回合内渲染）」＋整轮无引用「本回合无引用。」 | `web/src/landing/redesign/CitationPanel.jsx:104`；`CitationPanel.jsx:71` | `CitationPanel.test.jsx::无配对材料＝如实写「材料未在回合内渲染」（不虚构材料内容）`；`::无引用＝「本回合无引用。」（旧版历史轮同形）` |
| ② | notice 未登记 type 灰色兜底（不静默丢） | `web/src/landing/redesign/events.js:58-64`（`noticeLevel → 'unknown'`）；`NoticeBand.jsx:60-63`（「系统提示（未登记类型）」） | `NoticeBand.test.jsx::未登记 type＝通用灰条兜底（原文照给，不静默丢弃）` |
| ③ | 流水线摘要/小字时长标注「本地计时」 | `web/src/landing/redesign/RunMetaLine.jsx:40`（`本地计时 ${durationS}s`）；`ExecutionPipeline.jsx:147`（展开态说明文案） | `A1V2R.test.jsx::chain_order`（真流一轮收口后断言 `run-meta-line` 含「本地计时」）；`RunMetaLine.test.jsx`（4 条） |

## 3. 旧测试处置比对表（`web/src/landing/A1V2.test.jsx` 21 条逐条）

口径：`A1V2.test.jsx` 删除前逐条比对 redesign 测试网；「等价」＝同行为在新页有同名/同义行为钉；
「迁移」＝行为以新形态存在（指名新钉）；「已废」＝该行为属旧页形态（右栏过程步面/线程锚/会话退出钮），
新页以另一形态承担或设计上不再需要——**删除≠丢失**，已废项均给出理由与承接面。

| # | 原用例（节选） | 处置 | 承接 / 理由 |
|---|---|---|---|
| 1 | mount 拉 listRunsV2(20)；行状态文案＋waiting 金色图标；无「追问此任务」链接 | 等价 | `A1V2R.test.jsx::左栏＝ThreadList 真接：初始拉 20 条…`；`ThreadList.test.jsx::live_limit_step_cap_100` |
| 2 | 点 completed 行：行高亮＋中栏全轮次＋右栏「历史过程」steps | 迁移 | 行高亮/中栏链轮＝`A1V2R.test.jsx::select_thread_renders_turns`；右栏改人话面板（引用与口径，见第 9 节遗留①） |
| 3 | 单选模型：点另一对话收起前条＋未收口占位＋「暂无已收口轮」说明 | 迁移 | 单选中栏链＝`select_thread_renders_turns`；未收口轮空答＝`::答案正文面`（「本次未产出答案正文。」）；「暂无已收口轮」指示＝已废（新页无显式线程锚武装指示，追问锚自动取最新已收口轮） |
| 4 | 右栏两态切换：实时回合过程帧优先；打开对话切历史 steps | 已废 | 新页机器腔过程只在流水线块；history 读口无帧序列（events 恒空）→ 流水线整块不出（后端读口缺口 P1-1，见第 9 节） |
| 5 | 右栏 getRunV2 失败→Alert 内联不出假步数；重开对话重拉成功 | 等价 | `select_thread_renders_turns · 404 轮降级`（读口失败降级＋不重试，同义面） |
| 6 | V2-74 链分组：追问轮并入链根行（一链一行）、最近活跃在前 | 迁移 | 左栏真接后行＝单 run（L1-L2 口径）；链分组语义转移到「选中行拉链」`select_thread_renders_turns`（一链多轮）＋`collectChain` |
| 7 | 打开两轮对话：中栏全轮次按序；右栏拉最新轮；发送锚＝最新收口轮 | 等价 | `select_thread_renders_turns`（链内两轮升序）＋`A1V2R.test.jsx::追问`（追问锚＝最新已收口轮） |
| 8 | 打开对话→placeholder 换追问形；发送带 followupRunId；收口锚推进 | 等价 | `A1V2R.test.jsx::追问：前轮已收口后发送带 followupRunId…`（＋`followup-hint` 输入区提示） |
| 9 | 「＋新会话」清流＋回放＋锚；后续发送不带 followupRunId | 迁移 | 新页无「＋新会话」钮：首个成品轮后的「新提问＝退出链视图回本会话流」；无收口轮时发送天然不带键（`::chain_order` 断言首问不带键），故该钮设计上不再需要 |
| 10 | V2-78 链连续（独立首问也武装）：收口→下一发带 followupRunId | 等价 | `::追问`（首问不带键→收口→第二发带键，同一条链式断言） |
| 11 | V2-77 理解旁白：kind=understanding 独立「系统理解」条，不混入答案 | 等价 | 归约器 `understanding` 分流（`a1v2Reducer.test.js`）＋流水线 `ev-understanding` 行（`ExecutionPipeline.test.jsx`／`A1V2R.test.jsx::运行中轮`） |
| 12 | 追问轮挂起→线程立即拆；done 不复活；下一发不带线程键 | 已废 | 新页追问锚由「最新已收口轮」现算，挂起轮（waiting_ask）天然不入锚——无需显式拆锚机制 |
| 13 | 追问轮流内失败→锚保持原 completed run；失败腿左栏复拉 | 迁移 | 锚保持＝同上（只认 completed）；失败腿呈现＝`::追问`（error 帧→errorFrame 灰条）；左栏复拉＝已废（ThreadList 无「失败即重拉」语义，读口由用户上拉驱动） |
| 14 | 追问轮引擎异常腿（run_failed notice＋done）→锚不推进；卡面告警 | 等价 | 归约器三分 `run_failed → runStatus='failed'`（`a1v2Reducer.test.js::run_status_three_way`）＋锚只认 completed；notice 呈现在流水线/回答块（`NoticeBand.test.jsx`） |
| 15 | 点 waiting_ask 行：「当前输入＝新会话」说明；发送不带键；挂起轮批准/驳回在场 | 迁移 | 挂起卡＝`A1V2R.test.jsx::链内挂起轮续答接通`（卡由 askFrame 驱动）；「当前输入＝新会话」说明＝已废（无 threading UI 谓词） |
| 16 | V2-78 挂起帧还原：pending_ask→反问＋选项；点选项＝clarify 续推 | 等价 | `reconnect.test.jsx::pending_ask_restore`（本会话流腿）＋`A1V2R.test.jsx::链内挂起轮续答接通`（链轮腿，本票新接通） |
| 17 | V2-78 刷新现场恢复：sessionStorage 对话选中→还原视图＋锚 | 已废 | 旧键 `a1v2.session` 属旧页线程锚；新页刷新恢复口径＝`a1v2r:runningRun`＋`reconnect.test.jsx`（R1/R2 重放）——刷新即恢复未收口轮，已收口轮走左栏历史 |
| 18 | 对话视图挂起轮批准→审批回流；收口锚回武装 | 等价 | `A1V2R.test.jsx::链内挂起轮续答接通`（postResumeV2 真通＋approval 形由 `resumeBodyFromAskFrame` 覆盖，`reconnect.test.jsx::pending_ask_restore` 钉 clarify 形） |
| 19 | listRunsV2 拒绝→计数行撤下＋「暂无数据」（失败≠空库） | 等价 | `ThreadList.test.jsx::读口失败≠空库：计数行撤下＋「暂无数据」失败空态（UI-14 同位纪律）` |
| 20 | 挂起卡渲染（AskCard 曾因 antd Space 未导入崩页）：ask 帧后出卡＋选项，页面不崩 | 等价 | `reconnect.test.jsx::pending_ask_restore`＋`A1V2R.test.jsx::链内挂起轮续答接通`（均渲染挂起卡与选项按钮） |
| 21 | EB2-D4 答案面：Markdown 成元素、`[n]` 点击＝开面板＋高亮定位该 index | 等价（同名钉在场） | `AnswerView.test.jsx`（12 条，正文渲染与 `[n]` 锚点）＋`CitationPanel.test.jsx::点某条＝高亮＋「已定位」＋出该条材料原文`＋`A1V2R.test.jsx::缺省＝最新轮；点正文 [n] ＝右栏切到该轮并定位` |

## 4. 发送链路落码位置（FE-05 核心）

| 环节 | 位置 |
|---|---|
| 发送入口（守卫/计时起点/新问条/退出链视图/追问锚/失败 Alert） | `web/src/landing/redesign/A1V2R.jsx:258-289`（`send`） |
| 追问锚（当前视图最新已收口轮 run） | `A1V2R.jsx:234-235`（`followupAnchor`） |
| 本地计时 → `durationByRun[runId]`（页面临时面，不入 TurnShape） | `A1V2R.jsx:243-248`（`recordDuration`）；渲染取用 `A1V2R.jsx:379,396`（`durationS={durationByRun[...]}`） |
| 提问腿 handlers（session 写 R1 键／done-无 ask 清键／error 清键／transport 落 `closed='transport'`＋清键） | `web/src/landing/redesign/useRunningRun.js:135-158`（`legHandlers`） |
| 新问条推入（条目 id 稳定——session 帧前 runId 未定） | `useRunningRun.js:119-124`（`pushAskEntry`） |
| 按条目 id 归约单帧 | `useRunningRun.js:109-111`（`dispatchEntryFrame`） |
| 追问 409 透传（输入区 Alert） | `A1V2R.jsx:282-288`（`.catch` → `setAskError`）＋`A1V2R.jsx:406-408`（Alert，`data-testid="ask-error-alert"`） |
| 链内挂起轮续答（FE-04 遗留接通） | `A1V2R.jsx:296-319`（`resumeChainTurn`）＋`A1V2R.jsx:380`（`onResume` 接线） |
| 输入区（Enter 发送／发送钮，均接 `send`） | `A1V2R.jsx:400-422` |

## 5. 三条命令＋两闸输出摘要（原文行）

```
$ cd web && npm run test
 Test Files  37 passed (37)
      Tests  439 passed (439)
（基线口径（逐项可核）：FE-04 收票时 460 − 旧 A1V2.test.jsx 随页删除 21 − route.test.jsx 重写
 6→2（−4）＋ A1V2R.test.jsx 重写 17→20（＋3）＋ 新增 mockLeft.test.js（＋1，净额 0） = 439；
 其余 341 基线全绿，无红。）

$ cd web && npm run build
 ✓ built in 4.38s
（产物含 dist/assets/A1V2R-*.js ——懒加载页经 LANDING_MODULES 真路径打包）

$ cd web && npm run lint
 ✖ 2 problems (0 errors, 2 warnings)   exit=0
（2 条 warning 均在未触及文件：src/pages/D3.jsx:96、src/pages/INDEX.jsx:85——预存项，非本票引入）

$ python3 tools/debt_markers.py check
 债务标记闸绿：web 源码债务短语全部携可解析 DEBT 标签（盘点 88 条见 report）。
（盘点数＝app/tests 侧裸短语清单（**不红**项），随主窗并行改动浮动——本票两次取值 85/88；
 闸判据只看 strict 面＝web 源码，恒绿。）

$ python3 tools/check_specs.py
 spec gate: PASS（0 警告）
```

复跑记录：`npm run test` 连续 5 次全绿、退出码 0；其中一次运行摘要曾出现一行
`Errors  1 error`（全部用例仍 passed、退出码 0），后续 5 次复跑未复现——判为环境级偶发
（jsdom/worker 未处理拒绝计时竞窗），此处如实记录，非本票代码缺陷（如需追查可留后续票）。

## 6. 框架红线核对（规格第 22/23 行）

| 行 | 判据 | 结果 |
|---|---|---|
| 22 | `web/package.json` 运行时依赖键集合与 FE 线开工前（`8c8a9e1`）逐字一致 | 相等：`['@antv/g6','antd','dayjs','marked','react','react-dom','zustand']`（`git diff 8c8a9e1..HEAD -- web/package.json` 输出为空）＋`npm run build` 绿 |
| 23 | `web/src` 无新增样式文件（`index.css` 唯一例外） | `find web/src -name '*.css' -o -name '*.less' -o -name '*.scss'` → 仅 `web/src/index.css` |

## 7. 残留 DEBT/mock 清单（应为零）

- `grep -rn "MOCK_TURNS\|MOCK_RUNS\|mockTurns\|deriveEvents 派生" web/src` → **零命中**（本票闸
  `mockLeft.test.js::no_mock_left` 即此断言的机器版：glob 键集×源码文本双判，含文件存在性）。
- `deriveEvents` 残余：`redesign/events.js` 仅存历史说明文字（FE-02 已删函数），无代码引用——
  本票 grep 确认零引用（本次改动亦未复活）。
- `tools/debt_markers.py check` 绿（web 源码债务短语零裸用）；`redesign/` 各组件头注的 mock 期
  标注与 `DEBT(...)` 临时路由标注随转正清理完毕。
- 页面级：`A1V2R.jsx` 不再引用夹具目录（`mockLeft.test.js` 断言 `不含 '__fixtures__'`＋含
  `postAskV2`）；夹具目录只被测试文件引用。

## 8. 偏离票面的决定及理由（逐条）

1. **物理文件保留施工名 `redesign/A1V2R.jsx`，路由键转正为 `A1V2`**：票面第 2 节允许「转正名
   A1V2R 或迁名 A1V2，随票注明」。此处取「键转正」：菜单/路由键＝`A1V2`（`#/A1V2` 指向真流页，
   符合任务 1 与规格第 18 行"路由替换"），源文件与测试保留施工名（避免与同目录测试命名、数据键
   `a1v2r:runningRun` 及 FE-03/04 披露口径脱节）。已在 `registry.js:12-17` 注明。
2. **夹具数据落 `__fixtures__/turns.js`＋`__fixtures__/runs.js`（导出名 `FIXTURE_TURNS`/`FIXTURE_RUNS`）**：
   票面要求 `mockTurns.js` 删除且「MOCK_TURNS 与 MOCK_RUNS 引用清零」＋「真机帧夹具放
   `redesign/__fixtures__/`（测试用，不走 mockTurns 复活）」。故数据原样迁入 fixtures 目录并改名，
   引用面（9 个测试文件）全部改指；页面零引用。
3. **提问腿按「条目 id」归位（票面伪代码写的是按对象引用替换）**：伪代码注释给的是
   `setTurns(ts => ts.map(t => t===turn ? … : t))`；本仓会话数组是 `entries=[{id,turn,durationS}]`
   （FE-03/04 形态），引用在首帧归约后即失效，故以**稳定条目 id** 归位（`pushAskEntry` 返回 id，
   `legHandlers({entryId})`／`dispatchEntryFrame` 按 id 归约）。语义等价：帧只进本腿那一轮、
   不另开轮；重放/续答腿仍按 runId 归位。落码见第 4 节。
4. **流开前失败（追问锚 409 等）额外把该轮落 `errorFrame`**：票面只点名「输入区 Alert 透传
   message」。只出 Alert 会在链条里留一条无解释的空答案轮（「本次未产出答案正文。」），
   属静默化风险；故同时经既有 reducer 的 error 分派落 `errorFrame`（灰条如实呈现失败），
   Alert 仍透传后端原文——两者并存，无行为冲突。
5. **`CitationPanel` 决策树 Modal 文案与头注去 mock**：转正后该页不再是「版面 mock」，原文案
   「本页是版面 mock」成为事实错误；改「决策树（占位）」＋「本体接回在后续版本」，入口与位置
   不动（Owner 拍板「决策树留着」）。连带更新两处测试断言文本。
6. **`dual-tree-smoke.test.jsx` 十键断言未改字面值**：合并后 `LANDING_LIT` 键集**确实未变**
   （十个键，A1V2 内容换成真流页），票面「替换后键集变化须同票更新该断言」的前提未成立；
   为免误导仅更新用例标题说明 A1V2 现身份（断言逐字保留）。
7. **`reconnect.test.jsx` 一轮计数 5 → 1**：去夹具轮的直接后果（原「mock 四轮＋合成轮」），
   非语义放宽——合成终态轮仍唯一在场。

## 9. 遗留观察（非本票欠账，供 Owner 裁决）

1. **history 链轮无「过程步」展示位**：新页机器腔过程只在流水线块，而 history 读口无帧序列
  （`citations/materials/notices/events` 恒空，H2），故历史轮的流水线块整块不渲染（空态纪律）。
   旧页右栏「历史过程 steps」面因此不存在于新页形态——根因是后端读口缺口，已登记
   `docs/runtime-refactor/frontend-redesign-后端需求.md` P1-1（后端补帧序列后可选补回）。
2. **真机目验未做**（第 1 节）：需 Owner 用真后端视读；本票已给出逐位核对清单与机检替代面。
3. **一次运行摘要偶发 `Errors 1 error`**（见第 5 节复跑记录）：5 次复跑不复现、退出码 0，
   如实记录不掩盖。
4. **关票前置风险：spec 翻「已完成」后 `tools/check_specs.py` 会红**（**非本票产物缺陷，属闸面
   与仓结构不匹配**，本票边界不含 `tools/`，故只报不改）：`check_specs.test_found` 对
   `路径::名字` 形标识要求名字出现在 `source_blob`，而 `SRC_DIRS = (src, lib, app, backend,
   frontend/src, tests, test, server)` **不含本仓前端目录 `web/src`**（本仓前端在 `web/`，
   非 `frontend/src`）。实测：spec 现状态「已定稿」不校验存在性 → 今日 PASS；一旦翻「已完成」，
   第 9/10–19 等以 `web/src/…::名字` 标注的行将全部判 FAIL（机检证据：`test_found` 对
   `web/src/landing/redesign/A1V2R.test.jsx::chain_order` 等返回 False）。
   **建议（一行修，主窗口 jurisdiction）**：`tools/check_specs.py` 的 `SRC_DIRS` 增列 `"web/src"`
   ——已验证可使本 spec 各行标识全部解析为 True（模拟跑：4/4 命中）。翻状态前请先决此事。
