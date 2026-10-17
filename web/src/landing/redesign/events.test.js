/**
 * events.js 钉测（执行流水线纯逻辑——串行链条模型）。
 *
 * 守什么：
 * - **事件顺序**（真机到达序的显示口径，规则逐条见 events.js 头注）：
 *   理解旁白首个 → 步按 seq 升序 → 材料聚合行紧随材料相位末步 → A/B 级（材料面）提示紧随材料行 →
 *   C 级提示挂其相位末步之后 → verify 在全部步/notice 之后 → citation 逐条殿后；
 * - **类型映射**：相位/工具白话映射（未登记值原样回显，不吞）；
 * - **工具挂在正确步下**：tool 事件紧随同 `seq` 的 step 事件（渲染成缩进行）；
 * - **摘要计数**：步/工具/材料/提示/时长 ＋ 状态词（running/answering/done）；
 * - 空态：无事件（旧版降级轮）＝空数组。
 *
 * 素材：redesign/mockTurns.js（真机帧抽出）。
 */
import { describe, expect, it } from 'vitest'

import { deriveEvents, noticeLevel, phaseText, summarizePipeline, toolText } from './events.js'
import { MOCK_TURNS } from './mockTurns.js'

const RUNNING = MOCK_TURNS.find(t => t.id === 't-running')
const FULL = MOCK_TURNS.find(t => t.id === 't-full')
const SPLIT = MOCK_TURNS.find(t => t.id === 't-split')
const LEGACY = MOCK_TURNS.find(t => t.id === 't-legacy')

const at = (events, pred) => events.findIndex(pred)
const label = ev => (ev.type === 'step' ? `step${ev.seq}:${ev.phase}`
  : ev.type === 'tool' ? `tool${ev.seq}`
    : ev.type === 'citation' ? `citation[${ev.cite.index}]`
      : ev.type === 'notice' ? `notice:${ev.notice.type}` : ev.type)

describe('deriveEvents · 事件顺序（真机到达序显示口径）', () => {
  it('完整轮：理解旁白打头 → 材料聚合行紧随取数步 → verify → 引用殿后', () => {
    const ev = deriveEvents(FULL)
    expect(ev[0].type).toBe('understanding')
    expect(ev[0].text).toContain('理解：问今年各井按天列出的日产液量')

    const stepExecute = at(ev, x => x.type === 'step' && x.phase === 'execute')
    const materials = at(ev, x => x.type === 'materials')
    expect(materials).toBe(stepExecute + 2) // 步 → 工具 → 材料聚合
    expect(ev[materials].count).toBe(51)

    const verify = at(ev, x => x.type === 'verify')
    const firstCite = at(ev, x => x.type === 'citation')
    expect(verify).toBeGreaterThan(at(ev, x => x.type === 'step' && x.seq === 12))
    expect(firstCite).toBe(verify + 1)
    expect(ev.slice(firstCite).every(x => x.type === 'citation')).toBe(true)
  })

  it('A/B 级（材料面）提示紧随材料聚合行；C 级挂其相位（核验）末步之后', () => {
    const ev = deriveEvents(FULL)
    const materials = at(ev, x => x.type === 'materials')
    const noticeIdx = t => at(ev, x => x.type === 'notice' && x.notice.type === t)

    // A 级 material_truncated / B 级 window_note：材料面提示（材料行之后、作答步之前）
    expect(noticeIdx('material_truncated')).toBe(materials + 1)
    expect(noticeIdx('window_note')).toBe(materials + 2)
    expect(noticeIdx('material_truncated')).toBeLessThan(at(ev, x => x.type === 'step' && x.seq === 9))

    // C 级 unsupported_claim / contradiction_split：挂 verify 相位末步（seq 11）之后
    const stepVerify = at(ev, x => x.type === 'step' && x.seq === 11)
    expect(noticeIdx('unsupported_claim')).toBe(stepVerify + 1)
    expect(noticeIdx('contradiction_split')).toBe(stepVerify + 2)
    expect(ev[noticeIdx('contradiction_split')].level).toBe('C')
  })

  it('工具挂到同 seq 步下（tool 事件紧随其 step 事件；seq 一致）', () => {
    const ev = deriveEvents(FULL)
    const tool = at(ev, x => x.type === 'tool')
    expect(ev[tool]).toMatchObject({ type: 'tool', seq: 8, tool: 'data_query', status: 'ok' })
    expect(ev[tool - 1]).toMatchObject({ type: 'step', seq: 8, phase: 'execute' })
    expect(ev.filter(x => x.type === 'step').every(s => s.seq)).toBe(true)
  })

  it('运行中轮（真机流式前缀）：无 verify/引用，材料流水位 16，尾部＝未到相位提示', () => {
    const ev = deriveEvents(RUNNING)
    expect(ev[0].type).toBe('understanding')
    expect(ev.some(x => x.type === 'verify')).toBe(false)
    expect(ev.some(x => x.type === 'citation')).toBe(false)
    expect(ev.find(x => x.type === 'materials').count).toBe(16)
    expect(ev.filter(x => x.type === 'step')).toHaveLength(7)
    expect(ev[ev.length - 1].type).toBe('notice') // 核验相位未到 → 排材料面提示位
    expect(ev[ev.length - 1].notice.type).toBe('unsupported_claim')
  })

  it('分列轮：材料聚合紧随取数步（seq6），引用按 index 升序 16 条', () => {
    const ev = deriveEvents(SPLIT)
    const stepExecute = at(ev, x => x.type === 'step' && x.phase === 'execute')
    expect(ev[stepExecute].seq).toBe(6)
    expect(ev[stepExecute + 2]).toMatchObject({ type: 'materials', count: 18 })
    const cites = ev.filter(x => x.type === 'citation').map(x => x.cite.index)
    expect(cites).toEqual([...cites].sort((a, b) => a - b))
    expect(cites).toHaveLength(16)
  })

  it('旧版降级轮：无事件（空数组——不伪造流水线）', () => {
    expect(deriveEvents(LEGACY)).toEqual([])
  })

  it('逐条顺序快照（完整轮前 20 条——顺序回归一目了然）', () => {
    expect(deriveEvents(FULL).slice(0, 20).map(label)).toEqual([
      'understanding',
      'step1:decision', 'step2:decision', 'step3:decision', 'step4:decision',
      'step5:decision', 'step6:decision', 'step7:decision',
      'step8:execute', 'tool8', 'materials',
      'notice:material_truncated', 'notice:window_note',
      'step9:answer', 'step10:answer',
      'step11:verify', 'notice:unsupported_claim', 'notice:contradiction_split',
      'step12:answer', 'verify'
    ])
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
  it('完整轮：执行完成 · 12 步 · 1 次工具 · 51 份材料 · 4 条提示 · 18.5s', () => {
    expect(summarizePipeline(FULL)).toEqual({
      state: 'done', stateWord: '执行完成', steps: 12, tools: 1, materials: 51, notices: 4, durationS: 18.5
    })
  })

  it('运行中：状态词「执行中」；作答中（answering）：状态词「作答中」', () => {
    expect(summarizePipeline(RUNNING).stateWord).toBe('执行中')
    expect(summarizePipeline({ ...RUNNING, phase: 'answering' }).stateWord).toBe('作答中')
  })

  it('缺 phase 时按 runStatus 推（running→running，其余 done）；时长缺省 null（不猜）', () => {
    expect(summarizePipeline({ runStatus: 'running' })).toMatchObject({ state: 'running', durationS: null })
    expect(summarizePipeline({ runStatus: 'completed' })).toMatchObject({ state: 'done' })
    expect(summarizePipeline(LEGACY).durationS).toBeNull()
  })
})
