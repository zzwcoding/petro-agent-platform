/**
 * NoticeRow / NoticeAlerts 钉测（notice 在串行链条模型下的两处落点）。
 *
 * 守什么：
 * - **流水线内小行**（`NoticeRow`）：A 级＝红/黄**彩条**小行（原文直给，样式不动）；
 *   B/C/未登记 type＝**灰纯文本紧凑行**（「⚙ 系统注记（type）· 点开看原文」，点开原文内联、
 *   再点收起——Owner 打磨批⑥：antd Collapse 边框盒退场；未登记型照旧兜底，不静默丢弃）；
 * - **隐藏型**（material_truncated/emission_strip——打磨批⑧）：两处都不出，原数据不动；
 * - **回答块顶部**（`NoticeAlerts`）：**只有 A 级**出 Alert（折叠态流水线下也能感知可信度），
 *   B/C 级不在此处重复占位、隐藏型滤掉；
 * - Owner 拍板：content **纯透传后端**，前端不硬编码白话摘要——标签中性、原文照给；
 * - 空态：无 A 级＝Alert 带不渲染。
 *
 * 素材：真机帧 notice 原文（来源帧注于 __fixtures__/turns.js 头注——借入帧随到达序入流）。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import { NoticeAlerts, NoticeRow } from './NoticeBand.jsx'
import { FIXTURE_TURNS } from './__fixtures__/turns.js'

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

const FULL = FIXTURE_TURNS.find(t => t.id === 't-full').turn
// A 级可见型＝合成 refused（真机夹具里唯一的 A 级 material_truncated 已按打磨批⑧隐藏）
const A_REFUSED = { type: 'refused', gates: [], content: '这一问没法按清单作答——域外问题。' }
const MT_HIDDEN = FULL.notices.find(n => n.type === 'material_truncated') // A 级但隐藏型
const WN = FULL.notices.find(n => n.type === 'window_note') // B 级
const UC = FULL.notices.find(n => n.type === 'unsupported_claim') // C 级

describe('NoticeRow · 流水线内小行', () => {
  it('A 级＝彩条小行：原文直给（不折叠、不必点击）', () => {
    render(<NoticeRow n={A_REFUSED} />)
    const row = screen.getByTestId('notice-row-a')
    expect(row.textContent).toBe(A_REFUSED.content)
    expect(row.style.borderLeft).toContain('3px')
    expect(document.querySelector('.ant-collapse')).toBeNull() // 不是折叠形
  })

  it('B 级＝灰纯文本行（无 Collapse 盒）：标签可见、原文默认收起、点开内联、再点收起', () => {
    render(<NoticeRow n={WN} />)
    expect(screen.getByTestId('notice-row-plain').textContent)
      .toBe('⚙ 系统注记（window_note）· 点开看原文')
    expect(document.querySelector('.ant-collapse')).toBeNull() // 边框盒退场（打磨批⑥）
    expect(screen.queryByText(WN.content)).toBeNull()
    fireEvent.click(screen.getByText('⚙ 系统注记（window_note）· 点开看原文'))
    expect(screen.getByTestId('notice-plain-body').textContent).toBe(WN.content)
    fireEvent.click(screen.getByText('⚙ 系统注记（window_note）· 点开看原文'))
    expect(screen.queryByTestId('notice-plain-body')).toBeNull()
  })

  it('C 级＝同一灰纯文本行（中性标签，前端不自造白话摘要）', () => {
    render(<NoticeRow n={UC} />)
    expect(screen.getByText('⚙ 系统注记（unsupported_claim）· 点开看原文')).toBeTruthy()
    expect(screen.queryByText(UC.content)).toBeNull()
    fireEvent.click(screen.getByText('⚙ 系统注记（unsupported_claim）· 点开看原文'))
    expect(screen.getByText(UC.content)).toBeTruthy()
  })

  it('未登记 type＝同形兜底（原文照给，不静默丢弃）', () => {
    const unknown = { type: 'brand_new_type', gates: [], content: '未登记类型提示原文' }
    render(<NoticeRow n={unknown} />)
    const label = screen.getByText('⚙ 系统注记（brand_new_type）· 点开看原文')
    expect(label).toBeTruthy()
    fireEvent.click(label)
    expect(screen.getByText(unknown.content)).toBeTruthy()
  })

  it('隐藏型（material_truncated）＝本件仍照型给行，隐藏由渲染方过滤（本件只作分级/渲染）', () => {
    // 展示口径的隐藏单点在 events.js::noticeVisible＋两处渲染方过滤——本件不重复判隐藏
    render(<NoticeRow n={MT_HIDDEN} />)
    expect(screen.getByTestId('notice-row-a').textContent).toBe(MT_HIDDEN.content)
  })
})

describe('NoticeAlerts · 回答块顶部（仅 A 级）', () => {
  it('A 级＝antd Alert 原文直给；B/C 级不在此处占位', () => {
    render(<NoticeAlerts notices={[A_REFUSED, WN, UC]} />)
    expect(screen.getByText(A_REFUSED.content)).toBeTruthy()
    expect(document.querySelector('.ant-alert')).toBeTruthy()
    expect(screen.queryByText(WN.content)).toBeNull()
    expect(screen.queryByText(/unsupported_claim/)).toBeNull()
  })

  it('隐藏型不过带（material_truncated/emission_strip——打磨批⑧）', () => {
    const { container } = render(<NoticeAlerts notices={[MT_HIDDEN, { type: 'emission_strip', content: '剥离发射 JSON' }]} />)
    expect(container.firstChild).toBeNull()
    expect(screen.queryByText(/只用到检索到的 24\/37 条材料/)).toBeNull()
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
