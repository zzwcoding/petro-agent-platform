/**
 * events.js 钉测（执行流水线纯逻辑——串行链条模型）。
 *
 * 守什么（FE-02 起 deriveEvents 退役——事件流真源＝归约器直出的 turn.events 到达序）：
 * - **reducer 事件断言**（真帧夹具归约产出）：理解旁白首个 → 步按到达序（tool(seq7) 先于承载
 *   step(seq7) 的真机序原样保留——不补排序）→ 材料聚合单行 → verify 事件先于核验步 →
 *   引用逐条殿后；借入 notice 随拼接位入流；
 * - **类型映射**：相位/工具白话映射（未登记值原样回显，不吞）；
 * - **摘要计数**：步/工具/材料/**可见提示**数（隐藏型不计——打磨批⑧）＋状态词（running/
 *   answering/done——渲染期 phaseOf 派生，runStatus 兜底分支按 FE-02 字面替换保留）；
 * - **显示折叠**（foldEvents——打磨批④⑤⑥）：连续 citation 段→一条（计数＋去重来源数）、
 *   连续同（相位＋标题）step 段→一条（＋count）、连续 materials 段→一条（逐次份数）；
 *   不跨段（被别的事件隔开就断）、单条不添标记、其余事件原序透传；
 * - 空态：无事件（旧版降级轮）＝空数组。
 *
 * 素材：__fixtures__/turns.js 真帧夹具（归约器输出——条目＝{id, turn, durationS}）。
 */
import { describe, expect, it } from 'vitest'

import {
  foldEvents, NOTICE_LEVEL_HIDE, noticeLevel, noticeVisible, phaseText, summarizePipeline, toolText
} from './events.js'
import { FIXTURE_TURNS } from './__fixtures__/turns.js'

const LIVE = FIXTURE_TURNS.find(e => e.id === 't-live').turn
const FULL = FIXTURE_TURNS.find(e => e.id === 't-full').turn
const SPLIT = FIXTURE_TURNS.find(e => e.id === 't-split').turn
const LEGACY = FIXTURE_TURNS.find(e => e.id === 't-legacy').turn

describe('turn.events · 到达序（归约器直出——deriveEvents 退役后的事件断言）', () => {
  it('运行中轮（真机流式前缀）：理解打头 → 真机序 tool(seq7) 先于承载 step(seq7)；材料聚合单行 16', () => {
    expect(LIVE.events[0]).toEqual({ type: 'understanding', text: '理解：问 W-11 井生产套管的尺寸与下深。' })
    const toolAt = LIVE.events.findIndex(e => e.type === 'tool')
    const step7At = LIVE.events.findIndex(e => e.type === 'step' && e.seq === 7)
    expect(toolAt).toBeLessThan(step7At) // G4 真机到达序原样（不补排序）
    expect(LIVE.events.find(e => e.type === 'materials')).toEqual({ type: 'materials', count: 16 })
    expect(LIVE.events.filter(e => e.type === 'step')).toHaveLength(7)
    expect(LIVE.events.every(e => e.type === 'step' ? e.seq : true)).toBe(true)
    expect(LIVE.events.some(e => e.type === 'verify')).toBe(false)
    expect(LIVE.events.some(e => e.type === 'citation')).toBe(false)
  })

  it('完整轮：借入 A/B/C 级 notice 随拼接位入流；verify 事件先于核验步；引用 51 条、收口步末位', () => {
    const types = FULL.events.map(e => e.type)
    expect(types[0]).toBe('understanding')
    expect(FULL.events[1]).toMatchObject({ type: 'notice', notice: { type: 'unsupported_claim' } })
    expect(FULL.events.filter(e => e.type === 'materials')).toHaveLength(1) // 聚合恒单行
    expect(FULL.events.find(e => e.type === 'materials').count).toBe(51)
    // 借入四条 notice（拼接位＝各帧在原流中的同部位——见 __fixtures__/turns.js 头注）：到达序
    expect(FULL.events.filter(e => e.type === 'notice').map(e => e.notice.type))
      .toEqual(['unsupported_claim', 'window_note', 'material_truncated', 'contradiction_split'])
    // 真机序：verify verdict 帧先于其承载核验步（seq11）
    const verifyAt = types.indexOf('verify')
    const step11At = FULL.events.findIndex(e => e.type === 'step' && e.seq === 11)
    expect(verifyAt).toBe(step11At - 1)
    expect(FULL.events.filter(e => e.type === 'citation')).toHaveLength(51)
    expect(FULL.events[types.lastIndexOf('step')]).toMatchObject({ type: 'step', seq: 12 }) // 收口步＝末事件
  })

  it('分列轮：自有 unsupported_claim 随核验段到达（notice 在 verify verdict 前一位）；材料聚合 18、引用 16', () => {
    const types = SPLIT.events.map(e => e.type)
    expect(SPLIT.events.find(e => e.type === 'materials')).toMatchObject({ type: 'materials', count: 18 })
    expect(SPLIT.events.filter(e => e.type === 'notice').map(e => e.notice.type))
      .toEqual(['unsupported_claim']) // EB3 自有帧（id=33——真机到达位）
    const verifyAt = types.indexOf('verify')
    expect(SPLIT.events[verifyAt - 1].type).toBe('notice')
    expect(SPLIT.events.filter(e => e.type === 'citation')).toHaveLength(16)
  })

  it('旧版降级轮：无事件（空数组——读口无此面，流水线整块不渲染）', () => {
    expect(LEGACY.events).toEqual([])
  })
})

describe('events · 白话映射（未登记值原样回显）', () => {
  it('六相位→白话；未登记相位原样', () => {
    expect(phaseText('decision')).toBe('分析问题')
    expect(phaseText('discover')).toBe('检索资料')
    expect(phaseText('execute')).toBe('取数')
    expect(phaseText('observe')).toBe('查看材料')
    expect(phaseText('verify')).toBe('核验')
    expect(phaseText('answer')).toBe('作答')
    expect(phaseText('weird_phase')).toBe('weird_phase')
  })

  it('五工具→白话；未登记工具原样', () => {
    expect(toolText('doc_retrieve')).toBe('查文档库')
    expect(toolText('semantic_query')).toBe('查指标台账')
    expect(toolText('data_query')).toBe('取数')
    expect(toolText('faq_lookup')).toBe('查常见问题')
    expect(toolText('table_schema')).toBe('查表结构')
    expect(toolText('weird_tool')).toBe('weird_tool')
  })

  it('notice 三级 + 未登记', () => {
    expect(noticeLevel('material_truncated')).toBe('A')
    expect(noticeLevel('window_note')).toBe('B')
    expect(noticeLevel('unsupported_claim')).toBe('C')
    expect(noticeLevel('brand_new')).toBe('unknown')
  })
})

describe('summarizePipeline · 折叠摘要计数', () => {
  it('完整轮：执行完成 · 12 步 · 1 次工具 · 51 份材料 · 3 条可见提示（隐藏型不计）；时长不入 turn（null）', () => {
    expect(summarizePipeline(FULL)).toEqual({
      state: 'done', stateWord: '执行完成', steps: 12, tools: 1, materials: 51, notices: 3, durationS: null
    })
    // 原数据不动（4 条）——隐藏只是展示口径（打磨批⑧）
    expect(FULL.notices).toHaveLength(4)
    expect(FULL.notices.filter(n => n.type === 'material_truncated')).toHaveLength(1)
  })

  it('运行中：状态词「执行中」；作答中（首字已到未收口——phaseOf 派生）：状态词「作答中」', () => {
    expect(summarizePipeline(LIVE).stateWord).toBe('执行中')
    expect(summarizePipeline({ ...FULL, closed: null }).stateWord).toBe('作答中')
  })

  it('状态＝phaseOf 派生（closed/answerText 面）；runStatus 兜底分支按字面替换保留；时长缺省 null（不猜）', () => {
    expect(summarizePipeline({ runStatus: 'running' })).toMatchObject({ state: 'running', durationS: null })
    expect(summarizePipeline({ closed: 'done' })).toMatchObject({ state: 'done' })
    expect(summarizePipeline({})).toMatchObject({ state: 'running' }) // 无 closed 无正文＝在跑形
    expect(summarizePipeline(LEGACY).durationS).toBeNull()
  })
})

describe('NOTICE_LEVEL_HIDE · 展示口径隐藏型（打磨批⑧）', () => {
  it('material_truncated／emission_strip 不可见；其余型可见（分级表不动）', () => {
    expect([...NOTICE_LEVEL_HIDE].sort()).toEqual(['emission_strip', 'material_truncated'])
    expect(noticeVisible({ type: 'material_truncated' })).toBe(false)
    expect(noticeVisible({ type: 'emission_strip' })).toBe(false)
    expect(noticeVisible({ type: 'window_note' })).toBe(true)
    expect(noticeVisible({ type: 'brand_new_type' })).toBe(true) // 未登记型照旧兜底出（不静默丢）
    expect(noticeVisible(null)).toBe(true)
    // 分级仍是「A 级」（隐藏只作用在展示面，分类不变）
    expect(noticeLevel('material_truncated')).toBe('A')
    expect(noticeLevel('emission_strip')).toBe('A')
  })
})

describe('fold_events · 事件流显示折叠（打磨批④⑤⑥——纯函数）', () => {
  const step = (seq, phase, title) => ({ type: 'step', seq, phase, title })
  const cite = (index, source) => ({ type: 'citation', cite: { index, source } })

  it('连续 citation 段折成一条：计数＝段长、来源＝去重（保首见序）', () => {
    const folded = foldEvents([
      cite(1, '甲'), cite(2, '甲'), cite(3, '乙'), cite(4, '甲'), cite(5, '丙')
    ])
    expect(folded).toEqual([{ type: 'citations', count: 5, sources: ['甲', '乙', '丙'] }])
  })

  it('不跨段：被别的事件隔开的两段 citation 各折各的一行', () => {
    const folded = foldEvents([
      cite(1, '甲'), cite(2, '甲'),
      step(9, 'verify', '核验：支撑 2｜改写 0｜分源 否'),
      cite(3, '乙')
    ])
    expect(folded.map(x => x.type)).toEqual(['citations', 'steps', 'citations'])
    expect(folded[0]).toMatchObject({ count: 2, sources: ['甲'] })
    expect(folded[2]).toMatchObject({ count: 1, sources: ['乙'] })
  })

  it('连续同（相位＋标题）的步折成一条 ＋count；单条不添标记（count=1）', () => {
    const folded = foldEvents([
      step(1, 'decision', '模型调用：decision'),
      step(2, 'decision', '模型调用：decision'),
      step(3, 'decision', '模型调用：decision'),
      step(4, 'decision', '模型调用：understand'),
      step(5, 'execute', '模型调用：decision') // 标题同、相位不同＝另一条
    ])
    expect(folded.map(x => [x.phase, x.title, x.count]))
      .toEqual([
        ['decision', '模型调用：decision', 3],
        ['decision', '模型调用：understand', 1],
        ['execute', '模型调用：decision', 1]
      ])
    expect(folded[0].seq).toBe(1) // seq/ev＝段首事件（其余段内事件不再出行）
    expect(folded[0].ev.seq).toBe(1)
  })

  it('单条步/单次材料不折出多余标记；连续 materials 段记逐次份数（保序）', () => {
    const folded = foldEvents([
      step(1, 'decision', 't'),
      { type: 'materials', count: 16 }
    ])
    expect(folded).toEqual([
      { type: 'steps', count: 1, phase: 'decision', title: 't', seq: 1, ev: step(1, 'decision', 't') },
      { type: 'materials', counts: [16] }
    ])
    expect(foldEvents([
      { type: 'materials', count: 32 }, { type: 'materials', count: 36 },
      { type: 'materials', count: 38 }, { type: 'materials', count: 32 }
    ])).toEqual([{ type: 'materials', counts: [32, 36, 38, 32] }])
    // 不跨段：材料段被步隔开＝两条
    expect(foldEvents([
      { type: 'materials', count: 32 }, step(1, 'execute', 't'), { type: 'materials', count: 36 }
    ]).map(x => x.type)).toEqual(['materials', 'steps', 'materials'])
  })

  it('其余事件原序透传（未登记型也带着原事件走，不静默丢）；空流＝空数组', () => {
    const evs = [
      { type: 'understanding', text: '理解：x' },
      { type: 'tool', seq: 7, tool: 'doc_retrieve', status: 'ok' },
      { type: 'verify', verdict: { supported: 1 } },
      { type: 'weird_type', a: 1 },
      null
    ]
    expect(foldEvents(evs)).toEqual([
      { type: 'understanding', ev: evs[0] },
      { type: 'tool', ev: evs[1] },
      { type: 'verify', ev: evs[2] },
      { type: 'weird_type', ev: evs[3] },
      { type: undefined, ev: null }
    ])
    expect(foldEvents([])).toEqual([])
    expect(foldEvents(undefined)).toEqual([])
  })

  it('真机完整轮：51 条连续引用折一行（2 处来源）；步/材料/notice 原序不折（12 步各不相同）', () => {
    const folded = foldEvents(FULL.events)
    expect(folded.filter(x => x.type === 'citations')).toEqual([
      { type: 'citations', count: 51, sources: ['agg.fct_daily_metering', 'agg.fct_daily_metering ⋈ agg.dim_well ⋈ agg.dim_date'] }
    ])
    expect(folded.filter(x => x.type === 'steps')).toHaveLength(12) // 标题各不相同＝零折叠
    // 引用段紧跟 verify（真机序：verify 步之后 51 条引用连发）
    expect(folded[folded.findIndex(x => x.type === 'citations') - 1].type).toBe('steps')
  })

  it('隐藏型 notice 不在本件过滤（流形折叠与展示口径两件事）——notice 事件恒独占一条', () => {
    const folded = foldEvents([{ type: 'notice', notice: { type: 'material_truncated', content: 'c' } }])
    expect(folded).toEqual([{ type: 'notice', ev: { type: 'notice', notice: { type: 'material_truncated', content: 'c' } } }])
  })
})
