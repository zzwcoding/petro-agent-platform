/**
 * CitationPanel 钉测（右栏「引用与口径」——设计稿 §2 方案 A、§3.3）。
 *
 * 守什么：
 * - 引用**按 source 分组**（组头＝trust 白话徽标＋来源＋支数）；
 * - 点某条＝该条高亮＋「已定位」并出材料原文；`trust=notice` 的按**程序声明**渲染
 *   （点明不是文档原文）；无配对材料＝如实写「材料未在回合内渲染」；
 * - 外部联动（正文引标点击传 focusIndex）＝面板自动定位该条；
 * - 面板内含血缘卡与追加面（该轮有就给）；决策树入口在位（mock 点开说明 Modal）；
 * - 空态＝「本回合无引用」；进行中＝「检索中…」。
 *
 * 素材：EB3-数-降1（16 支引用 5 处来源，含一条 trust=notice）／EB4-数-明2（含血缘与追加面）。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import CitationPanel from './CitationPanel.jsx'
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
const SPLIT = MOCK_TURNS.find(t => t.id === 't-split')
const LEGACY = MOCK_TURNS.find(t => t.id === 't-legacy')

describe('CitationPanel · 分组与 trust 白话徽标', () => {
  it('按 source 分组：组头＝来源＋支数＋trust 白话（报告/系统注记）', () => {
    render(<CitationPanel citations={SPLIT.citations} materials={SPLIT.materials} />)
    expect(screen.getByText('共 16 支引用 · 来自 5 处来源')).toBeTruthy()
    expect(screen.getByText('《A-W11井完井工程报告》')).toBeTruthy()
    expect(screen.getByText('检索供给窗声明（截断显式）')).toBeTruthy()
    expect(screen.getAllByText('报告').length).toBeGreaterThan(0)
    expect(screen.getByText('系统注记')).toBeTruthy()
  })

  it('点某条＝高亮＋「已定位」＋出该条材料原文（citation↔observation 按 index 配对）', () => {
    render(<CitationPanel citations={FULL.citations} materials={FULL.materials} />)
    expect(screen.queryByText('已定位')).toBeNull()
    fireEvent.click(screen.getByTestId('cite-item-2'))
    expect(screen.getByTestId('cite-item-2').textContent).toContain('已定位')
    expect(screen.getByTestId('cite-item-2').textContent).toContain('井号=N-02；区块=渤南；日期=2026-01-01；日产液量（方）=48.72')
  })

  it('trust=notice 的条目按程序声明渲染（点明不是文档原文）', () => {
    render(<CitationPanel citations={SPLIT.citations} materials={SPLIT.materials} />)
    fireEvent.click(screen.getByTestId('cite-item-17'))
    const item = screen.getByTestId('cite-item-17')
    expect(item.textContent).toContain('系统生成的声明，不是文档原文')
    expect(item.textContent).toContain('矛盾来源同窗并立') // 该条材料＝检索供给窗声明原文
    expect(screen.getByText('系统注记')).toBeTruthy() // 组头 trust 白话徽标
  })

  it('无配对材料＝如实写「材料未在回合内渲染」（不虚构材料内容）', () => {
    render(<CitationPanel citations={[SPLIT.citations[0]]} materials={[]} />)
    fireEvent.click(screen.getByTestId('cite-item-1'))
    expect(screen.getByTestId('cite-item-1').textContent).toContain('（材料未在回合内渲染）')
  })

  it('外部联动：focusIndex 传入＝该条自动定位（正文引标点击的落点）', () => {
    const { rerender } = render(<CitationPanel citations={FULL.citations} materials={FULL.materials} />)
    rerender(<CitationPanel citations={FULL.citations} materials={FULL.materials} focusIndex={51} />)
    expect(screen.getByTestId('cite-item-51').textContent).toContain('已定位')
  })

  it('面板内含血缘卡与追加面（该轮有就给——非数据题/无块时各组件自不出）', () => {
    render(<CitationPanel citations={FULL.citations} materials={FULL.materials} lineage={FULL.lineage}
      limit={FULL.limit} lineageText={FULL.supplement.lineage} splitText={FULL.supplement.split}
      attributionText={FULL.supplement.attribution} />)
    expect(screen.getByTestId('lineage-card')).toBeTruthy()
    expect(screen.getByText('按来源列出（每条结论标明出处）')).toBeTruthy()
    expect(screen.getByText('各来源说法不一 · 点开对照')).toBeTruthy()
  })

  it('决策树入口在位（mock 点开说明 Modal）', () => {
    render(<CitationPanel citations={[]} materials={[]} />)
    fireEvent.click(screen.getByRole('button', { name: /决策树/ }))
    expect(screen.getByText('决策树（mock 占位）')).toBeTruthy()
  })
})

describe('CitationPanel · 空态', () => {
  it('无引用＝「本回合无引用。」（旧版历史轮同形）', () => {
    render(<CitationPanel citations={LEGACY.citations} materials={LEGACY.materials} />)
    expect(screen.getByText('本回合无引用。')).toBeTruthy()
    expect(screen.queryByTestId('lineage-card')).toBeNull()
  })

  it('进行中＝「检索中——材料到位后这里出引用清单。」', () => {
    render(<CitationPanel citations={[]} materials={[]} running />)
    expect(screen.getByText('检索中——材料到位后这里出引用清单。')).toBeTruthy()
  })
})
