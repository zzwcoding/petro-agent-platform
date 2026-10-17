/**
 * NoticeRow / NoticeAlerts 钉测（notice 在串行链条模型下的两处落点）。
 *
 * 守什么：
 * - **流水线内小行**（`NoticeRow`）：A 级＝红/黄彩线小行（原文直给，不折叠）；
 *   B 级＝灰折叠小行（默认收起、点开见原文）；C 级＝默认收起、点开见原文；
 *   未登记 type＝通用灰条兜底（原文照给，不静默丢弃）；
 * - **回答块顶部**（`NoticeAlerts`）：**只有 A 级**出 Alert（折叠态流水线下也能感知可信度），
 *   B/C 级不在此处重复占位；
 * - Owner 拍板：content **纯透传后端**，前端不硬编码白话摘要——标签中性、原文照给；
 * - 空态：无 A 级＝Alert 带不渲染。
 *
 * 素材：真机帧 notice 原文（redesign/mockTurns.js 内已注明来源帧）。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import { NoticeAlerts, NoticeRow } from './NoticeBand.jsx'
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
const MT = FULL.notices.find(n => n.type === 'material_truncated') // A 级
const WN = FULL.notices.find(n => n.type === 'window_note') // B 级
const UC = FULL.notices.find(n => n.type === 'unsupported_claim') // C 级

describe('NoticeRow · 流水线内小行', () => {
  it('A 级＝彩线小行：原文直给（不折叠、不必点击）', () => {
    render(<NoticeRow n={MT} />)
    const row = screen.getByTestId('notice-row-a')
    expect(row.textContent).toBe(MT.content)
    expect(row.style.borderLeft).toContain('3px')
    expect(document.querySelector('.ant-collapse')).toBeNull() // 不是折叠形
  })

  it('B 级＝灰折叠小行：标签可见、原文默认收起、点开见原文', () => {
    render(<NoticeRow n={WN} />)
    expect(screen.getByText('说明（window_note）')).toBeTruthy()
    expect(screen.queryByText(WN.content)).toBeNull()
    fireEvent.click(screen.getByText('说明（window_note）'))
    expect(screen.getByText(WN.content)).toBeTruthy()
  })

  it('C 级＝默认收起、点开见原文（中性标签，前端不自造白话摘要）', () => {
    render(<NoticeRow n={UC} />)
    expect(screen.getByText('系统注记（unsupported_claim）· 点开看原文')).toBeTruthy()
    expect(screen.queryByText(UC.content)).toBeNull()
    fireEvent.click(screen.getByText('系统注记（unsupported_claim）· 点开看原文'))
    expect(screen.getByText(UC.content)).toBeTruthy()
  })

  it('未登记 type＝通用灰条兜底（原文照给，不静默丢弃）', () => {
    const unknown = { type: 'brand_new_type', gates: [], content: '未登记类型提示原文' }
    render(<NoticeRow n={unknown} />)
    const label = screen.getByText('系统提示（brand_new_type）· 点开看原文')
    expect(label).toBeTruthy()
    fireEvent.click(label)
    expect(screen.getByText(unknown.content)).toBeTruthy()
  })
})

describe('NoticeAlerts · 回答块顶部（仅 A 级）', () => {
  it('A 级＝antd Alert 原文直给；B/C 级不在此处占位', () => {
    render(<NoticeAlerts notices={[MT, WN, UC]} />)
    expect(screen.getByText(MT.content)).toBeTruthy()
    expect(document.querySelector('.ant-alert')).toBeTruthy()
    expect(screen.queryByText(WN.content)).toBeNull()
    expect(screen.queryByText(/unsupported_claim/)).toBeNull()
  })

  it('refused/run_failed＝error 色（硬失败与软告警在色上可辨）', () => {
    render(<NoticeAlerts notices={[{ type: 'refused', content: '这一问没法按清单作答。' }]} />)
    expect(document.querySelector('.ant-alert-error')).toBeTruthy()
  })

  it('空态：无 A 级（或全空）＝Alert 带不渲染', () => {
    const { container } = render(<NoticeAlerts notices={[WN, UC]} />)
    expect(container.firstChild).toBeNull()
    const { container: empty } = render(<NoticeAlerts notices={[]} />)
    expect(empty.firstChild).toBeNull()
  })
})
