/**
 * A1V2R 页面钉测（问一问V2 重设计 mock 静态版面页——临时路由）。
 *
 * 守什么（本页红线，机器可验）：
 * - **零请求**：全页数据来自 redesign/mockTurns.js——不接 SSE、不调 `/api/v2/*`
 *   （stub fetch 断言零次）；
 * - 四轮覆盖全形态：①加载中（「正在分析问题…」占位）②完整轮（notice 三级带/理解旁白/
 *   正文/血缘卡/追加面/核验行）③分列轮（长 split 限高）④旧版降级（灰字说明＋ [n] 死文本）；
 * - 引标联动：点正文 [n] ＝ 右栏面板切到该轮并「已定位」（重设计 §2 方案 A 的联动）；
 * - 旧版轮的 [n] 不可点（无 onCite/无悬停卡＝旧行为，正文单文本节点）；
 * - 右栏「决策树」入口在位（mock 点开说明 Modal）。
 */
/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'

import A1V2R from './A1V2R.jsx'

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
beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('A1V2R · mock 静态版面页', () => {
  it('四轮全形态在位：加载占位／完整轮／分列轮／旧版降级；零请求（不接 SSE、不调接口）', () => {
    render(<A1V2R />)
    for (const id of ['t-loading', 't-full', 't-split', 't-legacy']) {
      expect(screen.getByTestId(`turn-${id}`)).toBeTruthy()
    }
    const full = within(screen.getByTestId('turn-t-full'))
    expect(screen.getAllByText('正在分析问题…')).toHaveLength(1) // ① 加载态占位
    expect(full.getByTestId('notice-band')).toBeTruthy() // ② complete 轮的 notice 三级带
    expect(full.getByTestId('lineage-card')).toBeTruthy() // ② 血缘卡（右栏另有一份）
    expect(full.getByTestId('run-meta-line').textContent).toContain('已核验：有据 51 条')
    const split = within(screen.getByTestId('turn-t-split'))
    fireEvent.click(split.getByText('各来源说法不一 · 点开对照'))
    expect(split.getAllByText(/展开看全文/).length).toBeGreaterThan(0) // ③ 长 split 限高
    expect(screen.getByTestId('legacy-note').textContent).toContain('本轮为旧版记录，无引用/口径明细')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('每条答案正文都渲染（旧版轮含内嵌旧式「引用：」块文本——原样，不解析）', () => {
    render(<A1V2R />)
    expect(screen.getAllByTestId('answer-view')).toHaveLength(3)
    expect(screen.getByText(/引用：/)).toBeTruthy()
  })

  it('旧版轮 [n] 是死文本（无锚点、无悬停卡——旧轮无引用数据可查）', () => {
    render(<A1V2R />)
    const legacyCard = screen.getByTestId('turn-t-legacy')
    expect(legacyCard.querySelector('[data-cite]')).toBeNull()
    expect(legacyCard.textContent).toContain('「躺井」是作业区口语')
    expect(legacyCard.textContent).toContain('[1]') // 引标原样在正文里
  })

  it('点正文 [n] ＝右栏切到该轮并定位（「已定位」＋该条材料原文）', () => {
    render(<A1V2R />)
    const fullCard = screen.getByTestId('turn-t-full')
    const cite = fullCard.querySelector('[data-cite="51"]')
    expect(cite).toBeTruthy()
    fireEvent.click(cite)
    const item = screen.getByTestId('cite-item-51')
    expect(item.textContent).toContain('已定位')
    expect(item.textContent).toContain('日产液量（方）')
  })

  it('右栏默认＝完整轮（2 处来源）；点某轮「引用与口径」＝切到该轮（分列轮 5 处来源）', () => {
    render(<A1V2R />)
    expect(screen.getByText('共 51 支引用 · 来自 2 处来源')).toBeTruthy()
    const splitCard = screen.getByTestId('turn-t-split')
    fireEvent.click(splitCard.querySelector('button'))
    expect(screen.getByText('共 16 支引用 · 来自 5 处来源')).toBeTruthy()
    expect(screen.getByText('《Y-21井完井工程报告》')).toBeTruthy()
  })

  it('旧版轮无引用＝右栏空态「本回合无引用。」（切换后不残留上轮引用）', () => {
    render(<A1V2R />)
    fireEvent.click(screen.getByTestId('turn-t-legacy').querySelector('button'))
    expect(screen.getByText('本回合无引用。')).toBeTruthy()
  })

  it('右栏决策树入口在位（mock 点开说明 Modal——真树接线在后）', () => {
    render(<A1V2R />)
    fireEvent.click(screen.getByRole('button', { name: /决策树/ }))
    expect(screen.getByText('决策树（mock 占位）')).toBeTruthy()
  })

  it('中栏过程折叠条可展开（完整轮＝12 步树状时间线）', () => {
    render(<A1V2R />)
    const bar = screen.getAllByTestId('process-timeline-bar')[1] // ① 加载轮的条不可展开
    expect(bar.textContent).toContain('引用了 2 篇文档')
    fireEvent.click(bar)
    expect(screen.getByTestId('process-timeline-body').textContent).toContain('分析问题')
  })
})
