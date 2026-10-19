/**
 * historyAdapter 钉测（specs/frontend-redesign.md「验收测试」表第 7–8 行——票面对象逐行对应）。
 *
 * 守什么：
 * - `list_item_to_turn`：RunListItem(+RunView)→TurnShape 投影逐键——answer→answerText、
 *   runView.steps→steps（station←step、title 原样、StepView 其余字段不携带）、
 *   supplements 按 block 分四槽（strip 后原文）、runStatus←listItem.status、
 *   closed  completed/failed→'done'（其余 null）、askFrame←runView.pending_ask；
 * - `history_citations_projection`（2026-10-19 修）：读口无 citation/observation 帧，但收口
 *   增补面已落同一批数据——`citations` 块投回 citations 四键（正文 [n] 悬停卡与右栏引用清单
 *   在历史轮上照常可用）、`attribution` 块投回 materials 逐条正文；无块＝空（不补造）；
 * - `history_legacy_flag`：notices/events/understanding 恒空（读口无此面，适配器不补造数据）；
 *   supplements=null→legacy=true（旧版行——BE-01 前真形）、
 *   supplements=[]→legacy=false（BE-01 目标契约：后端空列如实出 []，前端先行）。
 *
 * 素材：RunListItem/RunView 字段形＝appv2/api/chat.py:120-160（StepView/RunView/RunListItem；
 * supplements 条目 [{block,text}]——业务值取真机轮同源片段，构造面仅投影映射所需的最小骨架）。
 */
import { describe, expect, it } from 'vitest'

import { adaptHistoryTurn } from './historyAdapter.js'

/** RunListItem（含 supplements 四块——血缘块带前后空白，钉 trim 投影）。 */
const LIST_ITEM = {
  run_id: 'run-21e45912',
  question: '今年各井的日产液量按天列出来',
  status: 'completed',
  answer: '今年各井按天列出的日产液量如下（口径：日产计量的日产液量）：[1]',
  followup_of: '',
  created_at: '2026-10-17 09:12:41',
  updated_at: '2026-10-17 09:13:00',
  supplements: [
    { block: 'lineage', text: '  ① 口径 日产液量（方）（单位：方）——指标台账注册声明  ' },
    { block: 'split', text: '互不一致——各来源说法如下，按来源分别列出：\n[1] 《源A》：说法一' },
    { block: 'attribution', text: '按来源分别列出（每条结论都标出它来自哪个来源）：\n[1] agg.fct_daily_metering：值' },
    { block: 'citations', text: '引用：\n[1] agg.fct_daily_metering · N-01@2026-01-01（authoritative）' }
  ]
}

/** RunView（steps 3 条——StepView 字段集＝chat.py:118-125，投影只取 seq/step/title）。 */
const RUN_VIEW = {
  status: 'completed',
  steps: [
    { seq: 1, step: 'decision', status: 'ok', title: '模型调用：understand', manifest: null, payload: null },
    { seq: 2, step: 'execute', status: 'ok', title: 'data_query：ok（子问题 s1）', manifest: null, payload: null },
    { seq: 3, step: 'verify', status: 'ok', title: '核验：支撑 51｜改写 0｜分源 否', manifest: null, payload: null }
  ],
  manifest_digest: '2e1263d5802ec26d',
  pending_ask: null
}

describe('historyAdapter · list_item_to_turn（RunListItem(+RunView)→TurnShape 投影）', () => {
  it('逐键投影：answer→answerText、steps→station/title、supplements 四槽（strip）、runStatus/closed', () => {
    const turn = adaptHistoryTurn(LIST_ITEM, RUN_VIEW)
    expect(turn.kind).toBe('history')
    expect(turn.question).toBe('今年各井的日产液量按天列出来')
    expect(turn.runId).toBe('run-21e45912')
    expect(turn.resumed).toBe(false)
    // runView.steps → steps：station←step、title 原样；StepView 其余字段（status/manifest/payload）不携带
    expect(turn.steps).toEqual([
      { seq: 1, station: 'decision', title: '模型调用：understand' },
      { seq: 2, station: 'execute', title: 'data_query：ok（子问题 s1）' },
      { seq: 3, station: 'verify', title: '核验：支撑 51｜改写 0｜分源 否' }
    ])
    expect(turn.answerText).toBe(LIST_ITEM.answer) // answer→answerText 原样
    // supplements 按 block 分四槽——strip 后原文（血缘块前后空白去除、内文不动）
    expect(turn.supplements).toEqual({
      lineage: '① 口径 日产液量（方）（单位：方）——指标台账注册声明',
      split: '互不一致——各来源说法如下，按来源分别列出：\n[1] 《源A》：说法一',
      attribution: '按来源分别列出（每条结论都标出它来自哪个来源）：\n[1] agg.fct_daily_metering：值',
      citations: '引用：\n[1] agg.fct_daily_metering · N-01@2026-01-01（authoritative）'
    })
    expect(turn.runStatus).toBe('completed') // runStatus←listItem.status
    expect(turn.closed).toBe('done') // completed→closed='done'（H3；phase 渲染期 phaseOf 派生）
    // 引用块回读投影：citations 块 → citation 帧四键（与 live 归约器输出同形）
    expect(turn.citations).toEqual([
      { index: 1, source: 'agg.fct_daily_metering', source_id: 'N-01@2026-01-01', trust: 'authoritative' }
    ])
    // attribution 块回读投影：逐条观察正文 → materials（悬停卡正文面）
    expect(turn.materials).toEqual([
      { index: 1, source: 'agg.fct_daily_metering', content: '值' }
    ])
    expect(turn.legacy).toBe(false)
    expect(turn.ignoredCount).toBe(0)
    expect(turn.verdicts).toEqual([])
    expect(turn.verdictFinal).toBeNull()
    expect(turn.blackbox).toBeNull()
    expect(turn.errorFrame).toBeNull()
  })

  it('askFrame←runView.pending_ask（挂起轮刷新还原）；pending 缺省＝null；waiting_ask→closed null', () => {
    const waiting = adaptHistoryTurn(
      { ...LIST_ITEM, status: 'waiting_ask' },
      { ...RUN_VIEW, status: 'waiting_ask', pending_ask: { kind: 'clarify', prompt: '确认范围：', options: ['选项一', '选项二'], detail: null } }
    )
    expect(waiting.askFrame).toEqual({ kind: 'clarify', prompt: '确认范围：', options: ['选项一', '选项二'], detail: null })
    expect(waiting.closed).toBeNull() // 非 completed/failed 不判收口
    expect(adaptHistoryTurn(LIST_ITEM, null).askFrame).toBeNull() // runView 缺省
    expect(adaptHistoryTurn(LIST_ITEM, RUN_VIEW).askFrame).toBeNull() // pending_ask=null
    expect(adaptHistoryTurn({ ...LIST_ITEM, status: 'failed' }, null).closed).toBe('done') // failed 同判收口
  })
})

describe('historyAdapter · history_legacy_flag（读口无此面恒空＋legacy 标记）', () => {
  it('旧版行（supplements=null）：citations/materials 空（无增补面可回读）；notices/events 恒空', () => {
    const turn = adaptHistoryTurn(
      {
        run_id: 'run-307959ec', question: '什么是躺井？', status: 'completed',
        answer: '「躺井」是作业区口语，对应的规范术语为「停产待检泵」[1]。\n\n引用：\n[1] sem_term#4 · 4（ledger）',
        followup_of: '', created_at: '2026-10-13 00:22:53.793441', supplements: null
      },
      null
    )
    expect(turn.citations).toEqual([]) // 无 citations 块＝空（正文内嵌旧式块不解析——不冒充帧面）
    expect(turn.materials).toEqual([])
    expect(turn.notices).toEqual([])
    expect(turn.events).toEqual([])
    expect(turn.understanding).toBe('')
    expect(turn.supplements).toEqual({}) // null→空对象（四槽全缺——键缺席）
    expect(turn.legacy).toBe(true) // 旧版行——正文内嵌旧式块原样渲染不解析
    expect(turn.answerText).toContain('引用：') // 旧式块文本原样保留（不解析不洗白）
  })

  it('supplements=[]→legacy=false（BE-01 目标契约——后端空列如实出 []，前端先行）；无块＝引用/材料空', () => {
    const turn = adaptHistoryTurn(
      { ...LIST_ITEM, supplements: [] }, null
    )
    expect(turn.legacy).toBe(false)
    expect(turn.supplements).toEqual({}) // 无块新轮——键全缺
    expect(turn.citations).toEqual([]) // 无块＝空（空态不造数据）
    expect(turn.materials).toEqual([])
  })

  it('单来源轮（无 attribution 块）＝materials 空、citations 照出——悬停卡正文如实走空态', () => {
    const turn = adaptHistoryTurn({
      ...LIST_ITEM,
      supplements: [{ block: 'citations', text: '引用：\n[1] sem_term#4 · 4（ledger）' }]
    }, null)
    expect(turn.citations).toEqual([{ index: 1, source: 'sem_term#4', source_id: '4', trust: 'ledger' }])
    expect(turn.materials).toEqual([]) // 不补造切片正文
  })
})
