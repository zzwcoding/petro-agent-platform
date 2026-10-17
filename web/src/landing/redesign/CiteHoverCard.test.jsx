/**
 * 引标悬停预览钉测（设计稿 §3.2 引标 hover 切片预览——零请求）。
 *
 * 守什么：
 * - `CiteHoverCard` 自带面：出处（[n] 来源＋trust 白话徽标＋出处编号）＋材料切片内容；
 *   无配对材料＝如实写「（材料未在回合内渲染）」；`trust=notice` 点明是程序声明；
 * - AnswerView **可选 prop** `citeHoverCard` 的接线：传了＝引标外包受控 Popover，
 *   悬停出卡（内容＝该 index 材料切片，零 fetch）；不传＝行为与旧版逐字一致
 *   （正文单文本节点、无可点锚点、无 Popover）——V1 与现 A1V2 不受影响。
 *
 * 注：AnswerView 既有 12 条钉测在 landing/AnswerView.test.jsx（未改动），本件只从
 * **新增 prop** 一侧补测。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import AnswerView from '../AnswerView.jsx'
import CiteHoverCard from './CiteHoverCard.jsx'
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

const fetchMock = vi.fn()
vi.stubGlobal('fetch', fetchMock)

afterEach(() => {
  cleanup()
  fetchMock.mockReset()
})

const FULL = MOCK_TURNS.find(t => t.id === 't-full')
const SPLIT = MOCK_TURNS.find(t => t.id === 't-split')

describe('CiteHoverCard · 卡片本体', () => {
  it('出处三行＋材料切片内容（零请求）', () => {
    const cite = FULL.citations[0]
    const material = FULL.materials.find(m => m.index === cite.index)
    render(<CiteHoverCard cite={cite} material={material} />)
    const card = screen.getByTestId('cite-hover-card')
    expect(card.textContent).toContain('[1]')
    expect(card.textContent).toContain('agg.fct_daily_metering')
    expect(card.textContent).toContain('权威台账') // trust 白话徽标
    expect(screen.getByTestId('cite-hover-body').textContent)
      .toContain('井号=N-01；区块=渤南；日期=2026-01-01；日产液量（方）=36.97')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('无配对材料＝如实写「材料未在回合内渲染」（不虚构切片）', () => {
    render(<CiteHoverCard cite={SPLIT.citations[0]} material={null} />)
    expect(screen.getByTestId('cite-hover-body').textContent).toBe('（材料未在回合内渲染）')
  })

  it('trust=notice ＝点明是程序声明（不伪装文档原文）', () => {
    const cite = SPLIT.citations.find(c => c.trust === 'notice')
    render(<CiteHoverCard cite={cite} material={SPLIT.materials.find(m => m.index === cite.index)} />)
    expect(screen.getByTestId('cite-hover-card').textContent).toContain('不是文档原文')
    expect(screen.getByTestId('cite-hover-card').textContent).toContain('系统注记')
  })

  it('无 cite ＝不渲染（调用方不该空弹）', () => {
    const { container } = render(<CiteHoverCard cite={null} material={null} />)
    expect(container.firstChild).toBeNull()
  })
})

describe('AnswerView · citeHoverCard 可选 prop 接线', () => {
  const CONTENT = '今年各井日产液量如下 [1]。'

  it('传 citeHoverCard＝引标切分并悬停出卡（内容＝该 index 材料切片，零请求）', async () => {
    render(
      <AnswerView
        content={CONTENT}
        citeHoverCard={index => (
          <CiteHoverCard cite={FULL.citations.find(c => c.index === index)}
            material={FULL.materials.find(m => m.index === index)} />
        )} />
    )
    const anchor = document.querySelector('[data-cite="1"]')
    expect(anchor).toBeTruthy()
    expect(screen.queryByTestId('cite-hover-card')).toBeNull() // 未悬停不弹
    fireEvent.mouseEnter(anchor)
    // antd Popover 悬停有 mouseEnterDelay（默认 0.1s）——出卡要等一拍
    expect(await screen.findByTestId('cite-hover-card')).toBeTruthy()
    expect(screen.getByTestId('cite-hover-body').textContent).toContain('日产液量（方）=36.97')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('citeHoverCard 返回空（无该 index 材料）＝引标不弹（不空弹）', () => {
    render(<AnswerView content={CONTENT} citeHoverCard={() => null} />)
    const anchor = document.querySelector('[data-cite="1"]')
    expect(anchor).toBeTruthy()
    fireEvent.mouseEnter(anchor)
    expect(screen.queryByTestId('cite-hover-card')).toBeNull()
  })

  it('不传 citeHoverCard＝旧版行为逐字一致（正文单文本节点、无锚点、无 Popover）', () => {
    const { container } = render(<AnswerView content={CONTENT} />)
    expect(container.querySelector('[data-cite]')).toBeNull()
    expect(container.textContent).toBe(CONTENT)
  })

  it('只传 citeHoverCard 不传 onCite＝引标仍切分（只悬停不点击）', () => {
    render(<AnswerView content={CONTENT} citeHoverCard={() => <span>看这里</span>} />)
    expect(document.querySelector('[data-cite="1"]')).toBeTruthy()
  })
})
