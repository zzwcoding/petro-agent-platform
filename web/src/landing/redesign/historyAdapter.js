/**
 * historyAdapter · history 读回 → TurnShape 投影（specs/frontend-redesign.md 行为约定 H2–H4）。
 *
 * 输入＝后端读口真形（字段以 appv2/api/chat.py 为准——RunListItem{run_id,question,status,
 * answer,followup_of,created_at,updated_at,supplements}＋RunView{status,steps,manifest_digest,
 * pending_ask}）：RunListItem.supplements＝[{block,text}] 增补面条目列（null＝旧版行）；
 * RunView.steps＝StepView{seq,step,status,title,...}。适配器只投影、不补造数据——
 * 读口无此面的键恒空（citations/materials/notices/events/understanding），缺的展示位
 * 由展示组件空态纪律整位不渲染（H5 零分支，不在适配器里造数据）。
 *
 * 三场景归一：live/replay 走归约器（../a1v2Reducer.js），history 走本件——产出同一 TurnShape，
 * 展示组件不判 kind（phase 渲染期 phaseOf(turn) 派生：closed='done' → 'done'）。
 */

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
