# 前端答案展示重设计（问一问V2 答案面）

状态: 已完成
来源: `docs/runtime-refactor/frontend-redesign-设计.md`（§6 Owner 四拍板＋串行链条模型反馈两轮）｜`docs/runtime-refactor/frontend-redesign-调研.md`（数据面）｜`docs/runtime-refactor/frontend-redesign-后端需求.md`（读口缺口登记）
版式: `docs/spec-format.md`（十节版式）

## 目标

把问一问V2 的答案面从「纯正文＋机器腔右栏」重设计为**串行链条版面**：每轮＝用户输入→系统执行流水线（可折叠 typed 事件流）→系统回答（正文＋统计小字；**追加面于 2026-10-17 打磨批②从中栏移除**——split 只留右栏；**血缘／查询口径框于 2026-10-19 打磨批⑨从中栏移除**——同一张 LineageCard 只在右栏「引用与口径」出一份），让油田业务用户能看懂系统在干什么、数字从哪来。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 后端任何改动（含补读口） | 主窗口（runtime 重写线），前端只登记需求 | `docs/runtime-refactor/frontend-redesign-后端需求.md` |
| teach 仓原型同步 | 不做——Owner 拍板「只管本仓」 | 〔来源：2026-10-17 Owner 拍板答复「不需要 只管本仓」〕 |
| V1 面（`web/src/landing/A1.jsx`） | 不动 | `web/src/landing/registry.js`（A1 注册行原样保留） |
| Weknora 式「点引标打开原文全文并定位高亮」 | 不做（无切片→原文位置锚点接口） | `docs/runtime-refactor/frontend-redesign-后端需求.md` P1-3 |
| 服务端权威耗时 | 不做，本地计时并标注「本地计时」 | `docs/runtime-refactor/frontend-redesign-后端需求.md` P1-2 |
| 新增 npm 运行时依赖 | 禁——antd/react/zustand/dayjs/marked 已装 | `web/package.json` |
| 后端 notice 白话摘要模板 | 不做——Owner 拍板「等后端」，前端纯透传 | 〔来源：2026-10-17 Owner 拍板答复「等后端」〕 |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| web | 改实现＋新增组件 | reducer 归约扩面（supplement/payload/tool.seq/events 到达序）、historyAdapter、重连接线、ThreadList 真接、新页切真流、旧 A1V2 下线 |

## 接口定义

**轮次形状（TurnShape）**——归约层唯一输出、展示组件唯一输入；三场景（live 帧流／replay 重放／history 读回）归一出同一形状：

```
TurnShape {
  kind:        'ask' | 'resume' | 'replay' | 'history'
  question:    string
  runId:       string
  resumed:     boolean
  phase:       'running' | 'answering' | 'done'        // 派生：无 answerText 且在跑=running；
               // 有 answerText 未收口=answering；收口=done
  steps:       { seq: int, station: string, title: string }[]
  tools:       { tool: string, status: 'ok'|'failed'|'ask', seq: int, message: string }[]
  materials:   { index: int, source: string, trust: 'authoritative'|'ledger'|'report'|'notice',
               content: string, payload?: { lineage: object, limit?: { hit: bool, rows: int } } }[]
  notices:     { type: string（29 值闭世界——真源 transport/constants.py，此处不复述）,
               gates: string[], content: string }[]
  citations:   { index: int, source: string, source_id: string, trust: string }[]
  errorFrame:  { code: string, message: string } | null   // error 帧载荷原样；无则 null
                                                          //（对账 D-2：闭环错误契约的安放位）
  understanding: string          // text 帧 kind='understanding' 拼接
  answerText:  string            // 其余 text 帧拼接（纯模型回复 Markdown）
  events:      // 按帧到达序追加的 typed 事件流——展示组件不自行排序。
               // 元素形状（对账 D-3 落定）：{ type: 'understanding'|'step'|'tool'|
               //   'materials'|'notice'|'verify'|'citation', ...payload }，
               // payload 键集＝phase/step/tool/status/count/cite/verdict/notice/text，
               // 消费真源＝web/src/landing/redesign/ExecutionPipeline.jsx
  verdicts:    object[]          // verify 形（帧原样）——verdict 帧按 subtype 分区
                                // （verify→verdicts；final→verdictFinal。对账 D-6）
  verdictFinal: object | null    // final 形
  blackbox:    object | null     // 收口帧载荷原样；挂起腿/收口前 = null
  askFrame:    object | null     // { kind, prompt, options, detail }；在场即挂起
  runStatus:   'running' | 'waiting_ask' | 'completed' | 'failed'
  closed:      'done' | 'error' | 'transport' | null
  ignoredCount: int              // 未知帧事件/未知 supplement block 计数（G6 机读信号——忽略不炸流）
  supplements: { split?: string, attribution?: string, citations?: string, lineage?: string }
               // supplement 帧按 block 分槽存 text（strip 后原文）；无该块＝键缺席
               // 血缘两源（对账 D-5 落定）：结构化源＝materials[].payload.lineage（优先）；
               // 文本兜底源＝supplements.lineage
  legacy:      boolean           // history 降级形标记：supplements===null→true（仅旧行——
               // 目标契约：后端空列如实出 []、null 仅旧行；对账 D-4，后端修复票排 FE-04 前）
}
```

**history 适配器**：`(listItem: RunListItem, runView?: RunView) → TurnShape`。RunListItem/RunView 字段以 `appv2/api/chat.py` 为准（`web` 卡公开接口节引用，不复述）；适配器只投影、不补造数据。

**组件契约**：`web/src/landing/redesign/` 各组件 props 只接 TurnShape 或其子段；不直接认帧、不发请求（hover 引标预览查 materials 内存）。已有组件契约以 mock 期落地代码为准，本 spec 不重复复述（真源＝组件文件头注）。

## 框架与依赖红线

| 点名 | 验收写法 | 对应闸 |
|---|---|---|
| 无新增框架（antd@5／react@18／zustand@5／dayjs／marked 沿用已装版本） | `web/package.json` dependencies 键集合与 2026-10-17 前一致（一个不多）＋`npm run build` 绿 | 人审＋`npm run build`（原因：依赖集合对比无现成闸，进 FE-05 人工核对项） |
| 不新建样式体系（内联 style 惯例沿用） | `web/src` 无新增 *.css/*.less/*.scss 文件（`index.css` 唯一例外，既有） | 人审（原因：存在性检查可机检但未落闸——登记候选，FE-05 核对） |

## 行为约定

**归约层（G 组）**
- G1 `supplement` 帧按 `block` 值分四槽存 `text`（`strip()` 后原文）；未知 block 忽略并计入 reducer 的忽略计数（不炸流）。〔来源：调研 §6-2「只按 block 值分派，禁硬匹配块头文本」〕
- G2 `observation` 帧 `payload`（含 `lineage`/`limit`）随帧透传进 materials；无 payload 键＝`payload: undefined`。
- G3 `tool` 帧保留 `seq`（与 step.seq 同轴，用于事件挂步）。
- G4 `events` 按**帧到达序**（信封 id 升序）追加；工具事件先于其承载 step 的真机序原样保留（不补排序）。
- G5 `runStatus` 三分：done 且 askFrame 在场→`waiting_ask`；notices 含 `run_failed`→`failed`；否则→`completed`。done 不作完局判据。
- G6 未知帧事件类型：忽略 + 计数，reducer 不抛错（沿用现状容错）。
- G7 **显示折叠**（`events.js::foldEvents`，纯函数；Owner 2026-10-17 打磨批④⑤⑥）：连续 citation 段→一条（计数＋去重来源数）、连续同（相位＋标题）step 段→一条（＋×N）、连续 materials 段→一条（逐次份数）；**只并连续段**（被别的事件隔开即断段，不跨事件类型）、单条不添标记、其余事件按到达序原样透传；不改 `turn.events` 真源、不改摘要行计数口径（摘要总数仍来自 turn 字段）。

**三场景归一（H 组）**
- H1 live 与 replay 走同一 reducer 同一形状（replay 帧序与原流逐字节相同——真源 `specs/transport.md` 行为 13 衔接面，此处只引用）。
- H2 historyAdapter：answer→answerText；supplements 非 null→supplements 四槽（按 block 分派，同 G1）；runView.steps→steps（station←step、title 原样）；**notices/events/understanding 恒为空**（读口无此面——真源 `appv2/api/chat.py` list_runs/RunView）。**citations/materials 不恒空**（2026-10-19 打磨批⑨）：读口无 citation/observation 帧，但收口增补面已落同一批数据——`citations` 块（`[n] 来源 · 出处编号（trust）`，真源 `answering/core.py:209`）按行形投回 citations 四键、`attribution` 块（`[n] 来源：观察正文`，仅跨 ≥2 处来源时产出）投回 materials 逐条正文；**投影读口已有的面，不是补造**（无块＝空；单来源轮无 attribution＝materials 空，悬停卡正文走 E1 占位）。
- H3 history 轮 `phase='done'`、`closed='done'`、runStatus←listItem.status。
- H4 `legacy` 标记：listItem.supplements 为 null→`legacy=true`（旧版轮，正文可能内嵌旧式块文本，原样渲染不解析）；非 null→`legacy=false`。
- H5 展示组件对 TurnShape 渲染**零场景分支**：同一组件同一 props 路径，缺数据走空态纪律（不渲染该展示位），不判 `kind`。

**降级与空态（E 组）**
- E1 引用面板：citation 无配对 observation→「材料未在回合内渲染」占位（不虚构）；整轮无引用→「本回合无引用」。
- E2 血缘卡：`supplements.lineage` 与 materials[].payload.lineage 都无→不渲染（非数据题）。**唯一出现处＝右栏「引用与口径」**（中栏不再出——打磨批⑨）。
- E3 notice 未知 type→兜底行照给，不静默丢弃；B/C/未登记三级的行形＝**灰纯文本紧凑行**（「⚙ 系统注记（type）· 点开看原文」，点开内联原文、再点收起；原 antd Collapse 边框盒按 Owner 2026-10-17 打磨批⑥退场），A 级仍是红/黄彩条行。
- E4 history 轮：notices 带/blackbox 小字无数据源→该展示位不渲染；**引用面板有数据源**（citations/materials 由 H2 回读投影——正文 `[n]` 悬停卡与右栏引用清单在历史轮上与 live 同路）；legacy 形状保留（正文内嵌旧式「引用：」块原样渲染，且该轮不做回读投影——不冒充帧面），**不再出旧版说明句**（原灰字〔「本轮为旧版记录，无引用/口径明细」〕按 Owner 2026-10-17 打磨批去行话撤下——形状留、话不说）。
- E5 流水线摘要时长为本地计时，标注〔原文：「本地计时」〕。
- E6 **隐藏型 notice 不出**（`NOTICE_LEVEL_HIDE`＝material_truncated/emission_strip，Owner 2026-10-17 打磨批⑧）：流水线不出行、回答块 A 级 Alert 带滤掉、摘要行「⚠ N 条提示」不计入；**只是前端展示口径**——`turn.notices` 原数据不动。
- E7 **trust 白话徽标不上屏**（Owner 2026-10-19 打磨批⑩）：右栏引用清单组头只出「来源 · N 支」、悬停卡卡头只出「`[n]` 来源（＋出处编号）」——`authoritative`／`ledger`／`report`／`notice` 四个白话徽标一律不渲染（原「权威台账」徽标撤下）。trust 键**只作机读判据**（`cites.js::TRUST_TEXT` 键集＝引用块回读的尾括号剥取；白话值仅留档），`trust=notice` 的「这是程序声明不是文档原文」仍以**文本句**点明（不靠徽标）。

**重连（R 组）**
- R1 提问受理即把 running run_id 持久化（sessionStorage）；run 收口清除。
- R2 页面加载时若存在持久化 running run_id：先 `GET /runs` 确认该 run 仍在行集 → `resume_run_id` 重连，全帧重放归一（与 live 同形状）；重放后可尾随新帧。
- R3 重连开流前 404（run 不在缓冲）→ 该轮按终态渲染「本轮已结束或不可达」灰条，不悬挂、不重试循环。
- R4 挂起态刷新：`GET /runs/{id}` 的 `pending_ask` 还原挂起卡；resume 只消费本腿新帧（不重启不重放）。

**历史列（L 组）**
- L1 初始 `GET /runs?limit=20`；加载更多＝**滚到列表底部**（离底 ≤40px）触发、limit 步进 +20 重拉全量替换（最新在上、更早在下）。**零按钮零提示**（Owner 2026-10-17 打磨批⑦：原「加载更早」按钮与「已到最早」小字退场；窗口数>库数时的「已载入 N / M」旧计数行随按钮消失）；**exhausted 判据**（拿到响应后）＝新 runs 行数＝旧行数（没有新内容）**或** 行数 < limit（库比窗口小）→ 此后不再 fetch（静默）；limit ≥ maxRows 亦不再 fetch。
  - 后端无 offset——夹取 1..100；真源 `appv2/api/chat.py` 的 list_runs。
- L2 搜索＝对已加载行前端过滤（后端无搜索参数），零请求。
- L3 选中行→拉该链轮次（listItem.followup_of 链对齐现状 buildThreads 分组语义）渲染中栏；**选中即清本会话流**（entries）——中栏视图＝链轮次＋**链之后**新提问轮（见 L5）。
- L4 显示粒度＝**一链一行**（分组只作用于显示——加载与窗口回传仍按原始行）：链归属＝followup_of 逐跳上溯到根（根＝空串或指向窗口外，与 L3 拉链同一 `cites.js::chainRootId`），链序按最新轮 `created_at` 降序；行＝链内最早轮问句（18 字截断），副行＝`{最新轮状态} · {链轮数} 轮 · {MM-DD HH:mm}`；点行＝L3 拉链（回调链内最新轮），选中＝所在链整行高亮。
- L5 **追问不清链视图**（Owner 2026-10-19 反馈修）：选中链后追问，中栏＝**链轮次在前 ＋ 链之后新提问轮在后**同一条时间线（`viewTurns` 单点派生；原 `send()` 的 `setChain(null)` 会把屏上已有对话整段抹掉——本修的红线）；选中行高亮亦不清（仍在同一段对话里）。追问锚＝该视图里最新已收口轮。
- L6 **左栏收口刷新**（V2-137——V2-73 原页「onDone 后刷新」的回归，FE-05 重写后丢失）：`ThreadList` 收 `refreshKey`（变更＝重拉全量替换，limit 回 `pageStep`、`exhausted` 复位、搜索态不清）；页面**受理＋收口两拍**各递增一次——受理（session 帧；run 行受理即落库，真源 `appv2/runtimev2/orchestration/runtime.py:264`）让新对话「运行中」当场进列，收口让状态/轮数在列上更新；挂起续答腿／链内续答腿收口亦各一次。收口回调每腿至多一次（`legHandlers` 幂等护栏）。刷新键不动选中态（`selectedRunId`／`chain` 独立）。

## 不降级与静默禁令

| 禁令 | 合法降级路径 | 机读信号 |
|---|---|---|
| 不静默丢帧/丢事件 | 未知类型进忽略计数（G6）；未知 notice type 出兜底灰条（E3） | reducer 忽略计数断言（`::unknown_event_counted`）；灰条渲染断言 |
| 不伪造数据 | 引用无配对出占位文案（E1）；无血缘不渲染（E2） | 占位文案渲染断言 |
| 不悬挂 | 重连 404→终态灰条（R3）；running 无 blackbox→统计行缺项不渲染 | 灰条/缺项断言 |
| history 不假装有明细 | legacy 轮明细位不渲染，且不出旧版说明句（legacy 形状保留，正文旧块原样） | `legacy` 字段在场＋明细位不渲染断言 |

## 验收测试

| # | 验收标准 | 边界集 | 保留集 | 对应测试 |
|---|---|---|---|---|
| 1 | supplement 帧按 block 分四槽存 strip 后原文；未知 block 忽略+计数 | 未知 block 帧在场 | 既有 17 条归约测试全绿 | `web/src/landing/a1v2Reducer.test.js::supplement_four_slots` |
| 2 | observation payload（lineage/limit）透传 materials | 无 payload 帧→undefined | materials 四字段形状不变 | `web/src/landing/a1v2Reducer.test.js::observation_payload_pass_through` |
| 3 | tool 帧 seq 保留 | — | 既有 tools 形状字段不变 | `web/src/landing/a1v2Reducer.test.js::tool_seq_kept` |
| 4 | events 按帧到达序追加（真机序：tool(seq7) 先于承载 step(seq7)） | EB4-A-正1 真机帧序列转录 | — | `web/src/landing/a1v2Reducer.test.js::events_arrival_order` |
| 5 | runStatus 三分 done/askFrame/run_failed 语义 | 挂起腿 done 后仍 waiting_ask | — | `web/src/landing/a1v2Reducer.test.js::run_status_three_way` |
| 6 | 未知帧事件类型：忽略且计入忽略计数（不炸流，机读信号在场） | 未知 type 帧在场 | 既有「未知事件容错」行为不回归 | `web/src/landing/a1v2Reducer.test.js::unknown_event_counted` |
| 7 | historyAdapter：RunListItem(+RunView)→TurnShape 投影 | supplements 非 null 血缘落槽；citations/attribution 块回读投 citations/materials 四键形 | — | `web/src/landing/redesign/historyAdapter.test.js::list_item_to_turn` |
| 8 | history 轮 notices/events 恒空+legacy 标记；citations/materials 由增补面回读（无块＝空，不补造） | supplements null→legacy=true 且不投影；单来源轮无 attribution→materials 空 | — | `web/src/landing/redesign/historyAdapter.test.js::history_legacy_flag`、`web/src/landing/redesign/cites.test.js::parseCitations` |
| 9 | 同一组件渲染 live/replay/history 三形状零分支（结构快照一致） | history 降级位缺省 | mock 四轮场景不回归 | `web/src/landing/redesign/A1V2R.test.jsx::one_shape_three_scenarios` |
| 10 | running run_id 提问即持久化、收口清除 | 收口后 sessionStorage 无残留 | — | `web/src/landing/redesign/reconnect.test.jsx::persist_running_run_id` |
| 11 | 刷新后重连：GET /runs 发现 running→resume_run_id 重放全帧归一 | 重放后可尾随新帧 | — | `web/src/landing/redesign/reconnect.test.jsx::reconnect_replays_full_stream` |
| 12 | 重连 404→终态灰条「本轮已结束或不可达」 | 不悬挂不重试循环 | — | `web/src/landing/redesign/reconnect.test.jsx::reconnect_404_terminal` |
| 13 | 挂起态刷新 pending_ask 还原、resume 只消费本腿新帧 | — | — | `web/src/landing/redesign/reconnect.test.jsx::pending_ask_restore` |
| 14 | ThreadList 真接：初始 limit=20、步进至 100 封顶（零按钮零提示，到头静默；exhausted 后不再 fetch） | limit 夹取边界（传 120 只到 100）；无新内容／库比窗口小 | mock 期 10 条行为不回归 | `web/src/landing/redesign/ThreadList.test.jsx::live_limit_step_cap_100`、`web/src/landing/redesign/ThreadList.test.jsx::scroll_auto_load_exhausted` |
| 15 | 搜索前端过滤零请求、无匹配空态 | — | — | `web/src/landing/redesign/ThreadList.test.jsx::search_client_side_no_fetch` |
| 16 | 选中行拉链渲染（followup_of 分组对齐 buildThreads） | 单轮链/多轮链 | — | `web/src/landing/redesign/A1V2R.test.jsx::select_thread_renders_turns` |
| 17 | 版面链条顺序：问句→流水线→回答（notice-alerts→正文→小字；中栏无追加面——打磨批②，中栏无血缘框——打磨批⑨） | 无血缘轮缺位不渲染（卡在右栏）；隐藏型 notice 不进警示带 | 既有 13 条页面测试不回归 | `web/src/landing/redesign/A1V2R.test.jsx::chain_order` |
| 18 | 旧 A1V2 下线：路由替换、旧页文件删、旧测试随票处置 | 菜单项名替换 | V1 A1 页与测试原样保留 | `web/src/landing/redesign/route.test.jsx::a1v2_replaced` |
| 19 | mock/DEBT 清理：mockTurns/deriveEvents 删除或转固定夹具，债务短语零残留 | — | — | `tools/debt_markers.py` 全绿＋`web/src/landing/redesign/mockLeft.test.js::no_mock_left` |
| 20 | 真机帧走查：eval/results/frames/ 抽样轮在真流页面人工核对（答案/引用面板/血缘/各来源说法不一对照）——机器面由真机帧夹具驱动全链路测试承载，Owner 目验记录另落 `docs/runtime-refactor/frontend-redesign-验证记录.md` | — | — | `web/src/landing/redesign/A1V2R.test.jsx` |
| 21 | 交付闸：npm run test/build/lint 三绿＋341 基线不红——三绿由 CI 门禁承载，终检集成面钉 route 测试 | — | — | `web/src/landing/redesign/route.test.jsx` |
| 22 | 框架红线：package.json 运行时依赖键集合与 FE 线开工前一致（一个不多）——依赖与样式两红线的人审核对记录见验证记录第 6 节 | — | — | `web/src/landing/redesign/mockLeft.test.js::no_mock_left` |
| 23 | 框架红线：web/src 无新增样式文件（index.css 唯一既有例外） | — | — | `web/src/index.css`（唯一样式文件存在性，人审 FE-05 核对） |
| 24 | 引标悬停按**锚点实例**（同一 index 多处锚点只开悬停那一处；锚点键含 token 路径，平级叶子同 index 同偏移也不撞键） | 同 index 重复引标（同叶子／平级叶子） | 不传 citeHoverCard＝旧行为逐字一致（V1 与真流页不受影响） | `web/src/landing/redesign/CiteHoverCard.test.jsx::cite_hover_per_anchor` |
| 25 | 去重：中栏回答块无追加面；右栏去「按来源列出」（attribution）留 split（右栏唯一出现处）；**血缘／查询口径框去中栏**（右栏唯一出现处） | 有 split/attribution 的轮；有 lineage 的轮 | 正文/引用清单照常；引用清单＝正文 [n] 配对材料定位不变；右栏血缘卡照常 | `web/src/landing/redesign/A1V2R.test.jsx::supplement_dedup_right_panel_only`、`web/src/landing/redesign/CitationPanel.test.jsx::split_only_right_panel`、`web/src/landing/redesign/A1V2R.test.jsx::chain_order` |
| 26 | 流水线折叠四类：连续 citation／同（相位＋标题）step／连续 materials 段各折一行，B/C/未登记 notice 改灰纯文本行，隐藏型两处不出且摘要不计 | 连续段／单条段／不跨段 | 摘要计数口径（步/工具/材料/提示数来自 turn）不回归 | `web/src/landing/redesign/events.test.js::fold_events`、`web/src/landing/redesign/ExecutionPipeline.test.jsx::pipeline_fold_four_kinds`、`web/src/landing/redesign/ExecutionPipeline.test.jsx::pipeline_hidden_notice_absent` |
| 27 | history 轮引用面回读投影：citations 块→右栏引用清单（不再恒「本回合无引用」）＋正文 `[n]` 悬停出引标卡（出处名/编号） | attribution 块在场→卡正文＝观察原文；不在场→「材料未在回合内渲染」占位（不伪造切片） | live 轮 hover 路径不回归（citation 帧同形） | `web/src/landing/redesign/A1V2R.test.jsx::历史轮回读投影`、`web/src/landing/redesign/CiteHoverCard.test.jsx::cite_hover_per_anchor` |
| 28 | 中栏零血缘框：同一轮 LineageCard 只渲染一份（右栏） | 有 lineage 块/无 lineage 块两形 | 右栏 CitationPanel 血缘卡照常（E2 空态不渲染） | `web/src/landing/redesign/A1V2R.test.jsx::history 缺的展示位＝整位不渲染`、`web/src/landing/redesign/CitationPanel.test.jsx` |
| 29 | 追问不清链视图（L5）：选中链后追问＝链轮照旧在屏＋新轮接在其后（`对话 · N 轮` 含两段），追问锚＝视图最新已收口轮 | 链内追问／会话流追问两形 | 未选链时中栏仍是本会话流单段 | `web/src/landing/redesign/A1V2R.test.jsx::追问不清链视图` |
| 30 | 左栏刷新两拍（L6）：受理（session 帧）与收口各重拉一次（limit 回 20）；每腿收口至多一次；挂起续答腿收口亦刷新 | 收口回调重复调（脏流）；已触底到 40 后刷新 | 刷新键不变＝不重拉；搜索态不随刷新清空；选中态不动 | `web/src/landing/redesign/ThreadList.test.jsx::收口刷新`、`web/src/landing/redesign/A1V2R.test.jsx::左栏对话列表刷新` |
| 31 | trust 白话徽标不上屏（E7）：右栏组头只出「来源 · N 支」、悬停卡卡头只出「[n] 来源（＋出处编号）」——四值徽标零渲染 | `trust=notice` 条目仍以文本句点明程序声明 | trust 键仍作机读判据（引用块回读尾括号剥取照常）；点条定位/材料原文照常 | `web/src/landing/redesign/CitationPanel.test.jsx::分组与条数`、`web/src/landing/redesign/CiteHoverCard.test.jsx::卡片本体`、`web/src/landing/redesign/cites.test.js` |

## 依赖与风险

| 依赖/风险 | 检测手段 |
|---|---|
| 后端读口缺口（history 无 citations/materials/notices/blackbox）→ H2/E4 降级形态的根因 | 已登记 `docs/runtime-refactor/frontend-redesign-后端需求.md` P1-1（人审：主窗口定期收取） |
| 主窗口并行施工可能扫走本线未提交文件（10-17 已发生两次：67e9dcf/流水79） | FE-05 核对项：每票完工立即显式路径 `git add` 提交（人审＋commit 信息注明） |
| `runs` 列表仅本进程行集（重启即空）→ 重连发现路径 R2 可能找不到 run | 后端自登记缺口（chat.py 注释）；前端 R3 兜底灰条（测试 ::reconnect_404_terminal） |
| SSE 自动滚底/动画未在 spec 范围（mock 期已声明不做） | 人审：FE-05 后由 Owner 决定是否追加票 |

## 与闸的挂钩表

| 红线/禁令 | 闸/测试/人审 |
|---|---|
| 依赖集合不增（框架红线） | 人审＋`npm run build`（FE-05 核对项，原因见该节） |
| 无新增样式文件（框架红线） | 人审（登记候选闸，原因见该节） |
| 债务短语携可解析 DEBT 标签（临时 mock 路由存续期） | `tools/debt_markers.py check`（CI 挂） |
| 帧归约形状钉真（G1–G6） | `a1v2Reducer.test.js` 新增 5 用例 |
| 三场景零分支（H5） | `A1V2R.test.jsx::one_shape_three_scenarios` |
| 不静默丢帧（未知 type 兜底） | `::unknown_event_counted`（G6 配套）＋E3 渲染断言 |
| 验收测试逐条有标识 | `tools/check_specs.py`（CI 挂；spec 标「已完成」时核验存在性） |
| 交付闸三绿 | `npm run test`/`build`/`lint`（CI 同款命令） |
