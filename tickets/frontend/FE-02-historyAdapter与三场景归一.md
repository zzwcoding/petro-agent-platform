# FE-02 · historyAdapter 与三场景归一（deriveEvents 退役）

状态: **待派工** ｜ 所属规格: `specs/frontend-redesign.md`（已定稿——前置满足）
Touches modules: `web`
前置: **FE-01 收票**（TurnShape 含 events/supplements 键后方可归一）
阻塞: `tickets/frontend/FE-01-归约层扩面.md` ｜ 被阻塞: FE-04／FE-05

## 任务

1. 新增 `web/src/landing/redesign/historyAdapter.js`：`(listItem, runView?) → TurnShape`（投影规则＝spec 行为约定 H2–H4 逐字：answer→answerText；supplements 按 block 分四槽；runView.steps→steps（station←step、title 原样）；citations/materials/notices/events/understanding 恒空；phase='done'、closed='done'、runStatus←listItem.status；supplements 为 null→`legacy=true`，否则 false）。
2. **deriveEvents 退役**：`web/src/landing/redesign/events.js` 的 deriveEvents 派生逻辑删除（其事件顺序是「显示口径」非真机到达序——头注自承），ExecutionPipeline 改吃 reducer 直出的 `turn.events`；events.js 保留相位/工具白话映射表与 notice 三级集合（纯常量，真源地位不变）。deriveEvents 头注的 DEBT(Owner) 标记随删除清理。
3. mockTurns.js 改造：四轮 mock 形状对齐 FE-01 reducer 输出（events 直写、supplements 四槽），保证 mock 页继续可用且 `one_shape_three_scenarios` 可钉。

「三场景零分支」是 Owner 拍板契约：〔来源：2026-10-17 Owner 要求「对话中进行中，刷新页面之后 查看已完成的对话，需要保持一致的设计」＋设计稿 §7「组件只认归约后的形状」〕。

先读: （5 份）`specs/frontend-redesign.md`（「行为约定」H1–H5）；`web/src/landing/redesign/events.js`（退役对象＋保留常量清单）；`web/src/landing/redesign/mockTurns.js`；`web/src/landing/A1V2.jsx` 的 `buildThreads`（followup_of 分组语义——FE-04 拉链要对齐，本票只需知悉）；`appv2/api/chat.py:142-221`（RunListItem 真形，禁改）。

框架红线: 无点名框架（无新增 npm 依赖）
边界红线: 只许动 `web/src/landing/redesign/` 内文件与其测试；**不碰** reducer（FE-01 的形状唯一真源，发现形状问题停下回报 L0，不回改）、`A1V2.jsx`、`appv2/`。

## 票面对象（specs/frontend-redesign.md「验收测试」表逐行转抄——本票 3 行：第 7–9 行）

〔来源：specs/frontend-redesign.md「验收测试」表〕

| # | 验收标准（原文） | 对应测试（原文） |
|---|---|---|
| 7 | historyAdapter：RunListItem(+RunView)→TurnShape 投影 | `web/src/landing/redesign/historyAdapter.test.js::list_item_to_turn` |
| 8 | history 轮 citations/materials/notices/events 恒空+legacy 标记 | `web/src/landing/redesign/historyAdapter.test.js::history_legacy_flag` |
| 9 | 同一组件渲染 live/replay/history 三形状零分支（结构快照一致） | `web/src/landing/redesign/A1V2R.test.jsx::one_shape_three_scenarios` |

## 施工要点

- H5 零分支的测试形态：同一 ExecutionPipeline（及答案块）分别喂 live 形 reducer 输出与 historyAdapter 输出，DOM 结构快照一致（history 缺的展示位是「不渲染」，不是「渲染占位」——E 组空态纪律在展示件内，不在适配器内造数据）。
- events.js 保留导出：`PHASE_TEXT`／`TOOL_TEXT`／notice 三级集合——ExecutionPipeline 的白话映射消费方不变，只换事件来源。

## 验收：票面对象 3 行逐条对应测试存在且通过；mock 页四轮场景测试（A1V2R.test.jsx 既有 13 条）全绿；`npm run test` 全绿。

## 回报：

完成后回总窗口说「FE-02 完成，产物在 web/src/landing/redesign/，偏差: <有/无>，测试: <npm run test 输出摘要——通过数/失败数>」。L0 先核测试输出，再关票。
