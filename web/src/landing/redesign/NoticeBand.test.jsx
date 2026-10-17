/**
 * NoticeBand 钉测（notice 三级带——设计稿 §3.6 ＋ 调研 §3 分级表）。
 *
 * 守什么：
 * - A 级（材料截断/拒答…）＝antd Alert，content 直接可见（不折叠）；
 * - B 级（窗口注记等过程说明）＝灰折叠条，默认收起、点开见原文；
 * - C 级（核验删改/分列/决策驳回…）＝默认收起，点开见原文；标签中性（**纯透传 content，
 *   前端不硬编码白话摘要**——Owner 拍板第 3 条）；
 * - 未知 type＝通用灰条兜底，原文照给（不静默丢弃）；
 * - 空态（无 notice）＝整带不渲染。
 *
 * 素材：真机帧 notice 原文（redesign/mockTurns.js 内已注明来源帧）。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import NoticeBand, { noticeLevel } from './NoticeBand.jsx'
import { MOCK_TURNS } from './mockTurns.js'

if (!window.matchMedia) {
  window.matchMedia = query => ({
    matches: false, media: query, onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn()
  })
}
if (!window.ResizeObserver) {
  window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }
}

afterEach(() => cleanup())

const FULL = MOCK_TURNS.find(t => t.id === 't-full')
const MT = FULL.notices.find(n => n.type === 'material_truncated')
const WN = FULL.notices.find(n => n.type === 'window_note')
const UC = FULL.notices.find(n => n.type === 'unsupported_claim')

describe('NoticeBand · 三级分级', () => {
  it('分级表：A/B/C 三档各归其位，未登记 type＝unknown', () => {
    expect(noticeLevel('material_truncated')).toBe('A')
    expect(noticeLevel('refused')).toBe('A')
    expect(noticeLevel('window_note')).toBe('B')
    expect(noticeLevel('unsupported_claim')).toBe('C')
    expect(noticeLevel('brand_new_type')).toBe('unknown')
  })

  it('A 级＝Alert 且 content 直接可见（真机材料截断原文）', () => {
    render(<NoticeBand notices={[MT]} />)
    expect(screen.getByText(MT.content)).toBeTruthy()
    expect(document.querySelector('.ant-alert')).toBeTruthy()
  })

  it('B 级＝灰折叠条：标签可见、原文默认收起；点开见原文', () => {
    render(<NoticeBand notices={[WN]} />)
    expect(screen.getByText('说明（window_note）')).toBeTruthy()
    expect(screen.queryByText(WN.content)).toBeNull() // 默认收起
    fireEvent.click(screen.getByText('说明（window_note）'))
    expect(screen.getByText(WN.content)).toBeTruthy()
  })

  it('C 级＝默认收起、点开见原文（前端不加白话摘要——只做中性标签）', () => {
    render(<NoticeBand notices={[UC]} />)
    expect(screen.getByText('系统注记（unsupported_claim）· 点开看原文')).toBeTruthy()
    expect(screen.queryByText(UC.content)).toBeNull()
    fireEvent.click(screen.getByText('系统注记（unsupported_claim）· 点开看原文'))
    expect(screen.getByText(UC.content)).toBeTruthy()
  })

  it('未知 type＝通用灰条兜底（原文照给，不静默丢弃）', () => {
    const unknown = { type: 'brand_new_type', gates: [], content: '演示用未登记类型提示原文' }
    render(<NoticeBand notices={[unknown]} />)
    const label = screen.getByText('系统提示（brand_new_type）· 点开看原文')
    expect(label).toBeTruthy()
    expect(screen.queryByText(unknown.content)).toBeNull()
    fireEvent.click(label)
    expect(screen.getByText(unknown.content)).toBeTruthy()
  })

  it('三条同级 notice 各出一条（同 type 不合并、不互相顶掉）', () => {
    render(<NoticeBand notices={[UC, { ...UC, content: '第二条同型原文' }]} />)
    expect(screen.getAllByText(/系统注记（unsupported_claim）/)).toHaveLength(2)
  })

  it('空态（无 notice）＝整带不渲染', () => {
    const { container } = render(<NoticeBand notices={[]} />)
    expect(container.firstChild).toBeNull()
  })
})
