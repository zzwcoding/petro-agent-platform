/**
 * historyAdapter · history 读回 → TurnShape 投影（specs/frontend-redesign.md 行为约定 H2–H4）。
 *
 * 输入＝后端读口真形（字段以 appv2/api/chat.py 为准——RunListItem{run_id,question,status,
 * answer,followup_of,created_at,updated_at,supplements}＋RunView{status,steps,manifest_digest,
 * pending_ask}）：RunListItem.supplements＝[{block,text}] 增补面条目列（null＝旧版行）；
 * RunView.steps＝StepView{seq,step,status,title,...}。适配器只投影、不补造数据——
 * 读口无此面的键恒空（notices/events/understanding），缺的展示位由展示组件空态纪律
 * 整位不渲染（H5 零分支，不在适配器里造数据）。
 *
 * **引用／材料两面的回读投影**（2026-10-19 修：历史轮正文有 `[n]` 锚点却悬停无卡、右栏恒
 * 「本回合无引用」）：读口没有 `citation`/`observation` 帧，但收口时程序已把同一批数据落成
 * 两块增补面文本——`citations` 块（`[n] 来源 · 出处编号（trust）`）与 `attribution` 块
 * （`[n] 来源：观察正文原文照抄`，仅跨 ≥2 处来源时产出）。本件按行形把这两块投回
 * `citations`/`materials` 帧形：投影的是读口**已有的**面（同源同数据），不是补造。
 * 单来源轮无 attribution 块＝materials 为空，悬停卡正文如实走「材料未在回合内渲染」空态。
 *
 * 三场景归一：live/replay 走归约器（../a1v2Reducer.js），history 走本件——产出同一 TurnShape，
 * 展示组件不判 kind（phase 渲染期 phaseOf(turn) 派生：closed='done' → 'done'）。
 */
import { parseCitations, parseSupplement } from './cites.js'

export function adaptHistoryTurn(listItem, runView = null) {
  const supplements = listItem.supplements == null ? {}
    : Object.fromEntries(listItem.supplements.map(b => [b.block, String(b.text ?? '').trim()]))
                                      // 按 block 分槽；BE-01 修复后：null=旧行、[]=无块新轮
  return {
    kind: 'history',
    question: listItem.question,
    runId: listItem.run_id,
    resumed: false,
    steps: (runView?.steps ?? []).map(s => ({ seq: s.seq, station: s.step ?? '', title: s.title ?? '' })),
    tools: [],
    // 材料＝attribution 块的逐条观察正文（原文照抄面；无块＝空——不伪造切片正文）
    materials: parseSupplement(supplements.attribution).items
      .map(it => ({ index: it.index, source: it.source, content: it.text })),
    notices: [],
    citations: parseCitations(supplements.citations), // 引用＝citations 块逐行回读（四键同帧形）
    understanding: '', answerText: listItem.answer ?? '',
    events: [],                       // H2：读口无此面，恒空（流水线块走空态纪律整块不渲染）
    verdicts: [], verdictFinal: null, blackbox: null,
    askFrame: runView?.pending_ask ?? null,
    runStatus: listItem.status,
    closed: ['completed','failed'].includes(listItem.status) ? 'done' : null,
    errorFrame: null,
    supplements,
    legacy: listItem.supplements == null,
    ignoredCount: 0,
  }
}
