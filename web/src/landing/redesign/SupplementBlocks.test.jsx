/**
 * SupplementBlocks 钉测（程序追加面——设计稿 §3.5）。
 *
 * 守什么：
 * - 两块在场：attribution（按来源列出）与 split（各来源说法不一 · 点开对照），默认收起；
 * - attribution 展开＝**按来源分组**（组头＝来源＋条数），条目 `[n]`＋内容；
 * - split 展开＝逐条列出、**单条限高**（真机长条 >6 行/240 字＝限高态，出「展开看全文」，
 *   点开原文全文可见）；
 * - 短条不限高（不出多余开关——不造交互）；
 * - 空态（两块都没有）＝整件不渲染。
 *
 * 素材：__fixtures__/turns.js 真帧夹具——EB4-数-明2（attribution 51 条同源）、EB4-A-正3（split 短条借入）、
 * EB3-数-降1（split 长条）；FE-02 后 FIXTURE_TURNS 条目＝{id, turn, durationS}。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import SupplementBlocks from './SupplementBlocks.jsx'
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
const SPLIT = FIXTURE_TURNS.find(t => t.id === 't-split').turn

describe('SupplementBlocks · 两块默认收起', () => {
  it('两块标签在位、内容默认收起（次要位不抢正文）', () => {
    render(<SupplementBlocks split={FULL.supplements.split} attribution={FULL.supplements.attribution} />)
    expect(screen.getByText('按来源列出（每条结论标明出处）')).toBeTruthy()
    expect(screen.getByText('各来源说法不一 · 点开对照')).toBeTruthy()
    expect(screen.queryByTestId('supp-attribution')).toBeNull()
    expect(screen.queryByTestId('supp-split')).toBeNull()
  })
})

describe('SupplementBlocks · attribution 按来源列出', () => {
  it('展开＝按来源分组（组头＝来源＋条数）＋逐条 [n] 内容', () => {
    render(<SupplementBlocks attribution={FULL.supplements.attribution} />)
    fireEvent.click(screen.getByText('按来源列出（每条结论标明出处）'))
    const box = screen.getByTestId('supp-attribution')
    expect(box.textContent).toContain('agg.fct_daily_metering（50 条）')
    expect(box.textContent).toContain('agg.fct_daily_metering ⋈ agg.dim_well ⋈ agg.dim_date（1 条）')
    expect(box.textContent).toContain('井号=N-01；区块=渤南；日期=2026-01-01；日产液量（方）=36.97')
  })
})

describe('SupplementBlocks · split 限高', () => {
  it('真机长条（340 字）＝限高态（-webkit-line-clamp 6）＋「展开看全文」', () => {
    render(<SupplementBlocks split={SPLIT.supplements.split} />)
    fireEvent.click(screen.getByText('各来源说法不一 · 点开对照'))
    const item = screen.getByTestId('supp-item-9')
    expect(item.dataset.clamped).toBe('true')
    expect(item.style.webkitLineClamp).toBe('6')
    expect(item.textContent).toContain('4.2 防砂方式与参数')
    // 展开后该条放全文（限高解除），但不越权展示别的条
    fireEvent.click(screen.getAllByText(/展开看全文/)[0])
    expect(screen.getByTestId('supp-item-9').dataset.clamped).toBe('false')
    expect(screen.getByTestId('supp-item-13').dataset.clamped).toBe('true')
  })

  it('条目带来源名（真机形 `[n] 《报告》 · f15：…`＝取 ` · ` 前报告名）', () => {
    render(<SupplementBlocks split={SPLIT.supplements.split} />)
    fireEvent.click(screen.getByText('各来源说法不一 · 点开对照'))
    const box = screen.getByTestId('supp-split')
    expect(box.textContent).toContain('《A-W11井完井工程报告》')
    expect(box.textContent).toContain('《Y-21井完井工程报告》')
    expect(box.textContent).toContain('互不一致——各来源说法如下，按来源分别列出：') // 前导说明照录
  })

  it('短条（EB4-A-正3 split）＝不限高、不出「展开看全文」', () => {
    render(<SupplementBlocks split={FULL.supplements.split} />)
    fireEvent.click(screen.getByText('各来源说法不一 · 点开对照'))
    const item = screen.getByTestId('supp-item-22')
    expect(item.dataset.clamped).toBe('false')
    expect(screen.queryByText(/展开看全文/)).toBeNull()
  })
})

describe('SupplementBlocks · 空态', () => {
  it('无 split 无 attribution ＝整件不渲染', () => {
    const { container } = render(<SupplementBlocks split={null} attribution={null} />)
    expect(container.firstChild).toBeNull()
  })
})
