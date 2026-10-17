/**
 * events.js 钉测（执行流水线纯逻辑——串行链条模型）。
 *
 * 守什么（FE-02 起 deriveEvents 退役——事件流真源＝归约器直出的 turn.events 到达序）：
 * - **reducer 事件断言**（真帧夹具归约产出）：理解旁白首个 → 步按到达序（tool(seq7) 先于承载
 *   step(seq7) 的真机序原样保留——不补排序）→ 材料聚合单行 → verify 事件先于核验步 →
 *   引用逐条殿后；借入 notice 随拼接位入流；
 * - **类型映射**：相位/工具白话映射（未登记值原样回显，不吞）；
 * - **摘要计数**：步/工具/材料/提示 ＋ 状态词（running/answering/done——渲染期 phaseOf 派生，
 *   runStatus 兜底分支按 FE-02 字面替换保留）；
 * - 空态：无事件（旧版降级轮）＝空数组。
 *
 * 素材：redesign/mockTurns.js（真帧夹具＋归约器输出——FE-02 后条目＝{id, turn, durationS}）。
 */
import { describe, expect, it } from 'vitest'

import { noticeLevel, phaseText, summarizePipeline, toolText } from './events.js'
import { MOCK_TURNS } from './mockTurns.js'

const LIVE = MOCK_TURNS.find(e => e.id === 't-live').turn
const FULL = MOCK_TURNS.find(e => e.id === 't-full').turn
const SPLIT = MOCK_TURNS.find(e => e.id === 't-split').turn
const LEGACY = MOCK_TURNS.find(e => e.id === 't-legacy').turn

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
    // 借入四条 notice（拼接位＝各帧在原流中的同部位——见 mockTurns.js 头注）：到达序
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
  it('完整轮：执行完成 · 12 步 · 1 次工具 · 51 份材料 · 4 条提示；时长不入 turn（null）', () => {
    expect(summarizePipeline(FULL)).toEqual({
      state: 'done', stateWord: '执行完成', steps: 12, tools: 1, materials: 51, notices: 4, durationS: null
    })
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
