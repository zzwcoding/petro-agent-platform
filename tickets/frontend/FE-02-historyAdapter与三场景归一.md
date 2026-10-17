# FE-02 · historyAdapter 与三场景归一（deriveEvents 退役）

状态: done（2026-10-17 收票，验收全勾——见同目录收尾报告）
Status: done
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

## 伪代码（施工基准——L0 亲研，照抄实现，偏离即停报）

**1. `historyAdapter.js`**：
```
export function adaptHistoryTurn(listItem, runView = null) {
  return {
    kind: 'history',
    question: listItem.question,
    runId: listItem.run_id,
    resumed: false,
    steps: (runView?.steps ?? []).map(s => ({ seq: s.seq, station: s.step ?? '', title: s.title ?? '' })),
    tools: [], materials: [], notices: [], citations: [],
    understanding: '', answerText: listItem.answer ?? '',
    events: [],                       // H2：读口无此面，恒空（流水线块走空态纪律整块不渲染）
    verdicts: [], verdictFinal: null, blackbox: null,
    askFrame: runView?.pending_ask ?? null,
    runStatus: listItem.status,
    closed: ['completed','failed'].includes(listItem.status) ? 'done' : null,
    errorFrame: null,
    supplements: listItem.supplements == null ? {}
      : Object.fromEntries(listItem.supplements.map(b => [b.block, String(b.text ?? '').trim()])),
                                      // 按 block 分槽；BE-01 修复后：null=旧行、[]=无块新轮
    legacy: listItem.supplements == null,
    ignoredCount: 0,
  }
}
// phase 渲染期 phaseOf(turn) 派生（FE-01 导出）：closed='done' → 'done'
```

**2. deriveEvents 退役 + 组件换源**：
- `events.js`：删 `deriveEvents`（含其头注 DEBT）；**保留** PHASE_TEXT/TOOL_TEXT/phaseText/toolText/NOTICE_LEVEL_*/noticeLevel/NOTICE_PHASE（NoticeBand 与 ExecutionPipeline 的消费不动）与 `summarizePipeline`（改内部 `t.phase ?? …` 为 `phaseOf(t)`，从 '../a1v2Reducer.js' 导入）。
- `ExecutionPipeline.jsx:109`：`useMemo(() => deriveEvents(turn), [turn])` → `turn.events ?? []`（mock 过渡期兜底空数组；本票收尾时 mockTurns 已改造为 reducer 输出，兜底可去——判定：改造后 `?? []` 去留以 mockTurns 是否还有非 reducer 来源为准，随票注明）。

**3. mockTurns 改造为「真帧夹具 + reducer 输出」**（替换手写 turn 对象）：
```
__fixtures__/EB4-A-正1-prefix.json   // 信封 id≤25 帧数组（jq 抽取，头注来源）
__fixtures__/EB4-数-明2.json          // 全帧（问句/正文/51 引/51 材料/payload/四块/verdict/blackbox）
__fixtures__/EB3-数-降1.json          // 分列轮全帧
__fixtures__/legacy-run-307959ec.json // logs/old-runs-backup 的旧轮（answer 内嵌旧式块——喂 adaptHistoryTurn 的 listItem 形，不走 reducer）
export const MOCK_TURNS = [
  { id:'t-live',  turn: reduceV2Frames(newTurnV2('ask', q1), prefixFrames), durationS: 6.2 },
  { id:'t-full',  turn: reduceV2Frames(newTurnV2('ask', q2), fullFrames2),  durationS: 18.5 },
  { id:'t-split', turn: reduceV2Frames(newTurnV2('ask', q3), fullFrames3),  durationS: 10.5 },
  { id:'t-legacy',turn: adaptHistoryTurn(legacyListItem, null),             durationS: null },
]
// durationS 不入 turn——页面临时面，保持现状由页面传 RunMetaLine/摘要行。
```
**注**：轮 2 的跨帧借入（A/B/C 级 notice、split 块来自 EB4-A-正3 等）以**帧序列拼接**实现（夹具头注标明借入帧来源），不再手改 turn 字段——这是 FE-01 events 到达序的真实数据源。

**4. A1V2R 回答块接线对齐 TurnShape**（现 mock 吃 `turn.supplement` 单数/顶层 `turn.lineage`——D-5 处置）：
```
const lineagePayload = turn.materials.find(m => m.payload?.lineage)?.payload ?? null
<LineageCard lineage={lineagePayload?.lineage ?? null}
            limit={lineagePayload?.limit ?? null}
            text={turn.supplements?.lineage ?? ''} ... />
<SupplementBlocks split={turn.supplements?.split ?? null}
                   attribution={turn.supplements?.attribution ?? null} />
<RunMetaLine verdict={turn.verdictFinal ? /* 核验计数在 verify 形 */ turn.verdicts[0] ?? null : turn.verdicts[0] ?? null}
              blackbox={turn.blackbox} ... />
// 注：RunMetaLine 的 verdict 入参仍取 verify 形（verdicts[0]——verify 帧先于 final 帧到达且本字段只消费 verify 形计数）；
// verdictFinal 的消费在 FE-05 接真流时补「收口 manifest_digest」位，本票只需保证分区落码、RunMetaLine 行为不回归。
```
- `turn.phase` 全部调用点改 `phaseOf(turn)`（renderTurn 的 answering 判定、ExecutionPipeline summarizePipeline）。
- 右栏 CitationPanel 接线：`lineage/limit` 同上从 materials[].payload 取；`lineageText/splitText/attributionText` 改读 `turn.supplements.*`。

**5. 测试草稿**（3 用例）：
- `list_item_to_turn`：RunListItem（含 supplements 四块）+ RunView(steps 3 条) → 投影断言逐键；answer→answerText、steps→station/title。
- `history_legacy_flag`：supplements=null→legacy=true、citations/materials/notices/events 恒空；supplements=[]→legacy=false（BE-01 目标契约——前端先行）。
- `one_shape_three_scenarios`：同一 renderTurn 输出分别喂「reducer 活的 turn」与「adaptHistoryTurn 产物」（materials/notices 留空），DOM 快照一致（history 缺的展示位不渲染）。

## 施工要点

- H5 零分支的测试形态：同一 ExecutionPipeline（及答案块）分别喂 live 形 reducer 输出与 historyAdapter 输出，DOM 结构快照一致（history 缺的展示位是「不渲染」，不是「渲染占位」——E 组空态纪律在展示件内，不在适配器内造数据）。
- events.js 保留导出：`PHASE_TEXT`／`TOOL_TEXT`／notice 三级集合——ExecutionPipeline 的白话映射消费方不变，只换事件来源。

## 验收：票面对象 3 行逐条对应测试存在且通过；mock 页四轮场景测试（A1V2R.test.jsx 既有 13 条）全绿；`npm run test` 全绿。

## 回报：

完成后回总窗口说「FE-02 完成，产物在 web/src/landing/redesign/，偏差: <有/无>，测试: <npm run test 输出摘要——通过数/失败数>」。L0 先核测试输出，再关票。
