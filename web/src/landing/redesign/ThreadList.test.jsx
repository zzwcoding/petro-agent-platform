/**
 * ThreadList 钉测（左侧历史对话——上拉加载 + 搜索）。
 *
 * 守什么（真接口形态见组件头注：`GET /api/v2/chat/runs?limit=N`，limit 夹 1..100、无 offset、
 * 无搜索参数——「上拉加载」＝**扩大 limit 重拉全量** 20→40→60→80→100）：
 * - 初始只出 20 条（数据源 120 条）；「加载更早」＝ limit +20（按钮是滚动触发同一 handler 的
 *   可直调入口——jsdom 无真滚动）；
 * - 到 100 封顶：不再增长、入口让位给「已到最早」小字（不出无限 Spin）；
 * - 搜索＝对**当前已加载窗口**前端过滤（后端无搜索参数）；过滤中不触发加载更多、无命中出空态；
 * - 选中行高亮 + 点击回调；`runs` 空＝「暂无历史对话」。
 *
 * 素材：redesign/mockTurns.js 的 MOCK_RUNS（120 条 RunListItem 形态假数据）。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'

import ThreadList from './ThreadList.jsx'
import { MOCK_RUNS } from './mockTurns.js'

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

const rowsIn = () => screen.queryAllByTestId(/^thread-row-/)

describe('ThreadList · 数据源与初始窗口', () => {
  it('mock 数据源 120 条（RunListItem 形态）；初始只渲染前 20 条', () => {
    expect(MOCK_RUNS).toHaveLength(120)
    expect(Object.keys(MOCK_RUNS[0]).sort())
      .toEqual(['created_at', 'followup_of', 'question', 'run_id', 'status', 'updated_at'])
    render(<ThreadList runs={MOCK_RUNS} />)
    expect(rowsIn()).toHaveLength(20)
    expect(screen.getByTestId('load-more').textContent).toContain('已载入 20 / 100')
    // 行内＝问句＋状态白话＋时间（MM-DD HH:mm）
    const first = screen.getByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    expect(first.textContent).toContain('W-11 井生产套管的尺寸与下深是多少？'.slice(0, 18))
    expect(first.textContent).toContain('运行中 · 10-17 09:20')
  })
})

describe('ThreadList · 上拉加载（limit 步进＝后端无 offset 的映射）', () => {
  it('「加载更早」一次＝+20（20 → 40）', () => {
    render(<ThreadList runs={MOCK_RUNS} />)
    fireEvent.click(screen.getByTestId('load-more'))
    expect(rowsIn()).toHaveLength(40)
    expect(screen.getByTestId('load-more').textContent).toContain('已载入 40 / 100')
  })

  it('滚到列表顶部＝同一 handler（jsdom 无真滚动；scrollTop 0 触发 +20）', () => {
    render(<ThreadList runs={MOCK_RUNS} />)
    fireEvent.scroll(screen.getByTestId('thread-scroll'), { target: { scrollTop: 0 } })
    expect(rowsIn()).toHaveLength(40)
  })

  it('连续加载到 100 封顶：不再增长，入口让位「已到最早」（不出无限 Spin）', () => {
    render(<ThreadList runs={MOCK_RUNS} />)
    for (let i = 0; i < 6; i += 1) {
      const btn = screen.queryByTestId('load-more')
      if (!btn) break
      fireEvent.click(btn)
    }
    expect(rowsIn()).toHaveLength(100)
    expect(screen.queryByTestId('load-more')).toBeNull()
    expect(screen.getByTestId('earliest-tip').textContent).toBe('已到最早')
    // 再触发（滚动）也不越界
    fireEvent.scroll(screen.getByTestId('thread-scroll'), { target: { scrollTop: 0 } })
    expect(rowsIn()).toHaveLength(100)
  })

  it('上限可配（maxRows）——步进语义与后端 clamp 同形', () => {
    render(<ThreadList runs={MOCK_RUNS} maxRows={40} pageStep={20} />)
    fireEvent.click(screen.getByTestId('load-more'))
    expect(rowsIn()).toHaveLength(40)
    expect(screen.getByTestId('earliest-tip')).toBeTruthy()
  })
})

describe('ThreadList · 搜索（前端过滤已加载窗口）', () => {
  it('命中：只留匹配行，并如实说明匹配口径（已载入 20 条中匹配 N 条）', () => {
    render(<ThreadList runs={MOCK_RUNS} />)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '含水率' } })
    const matched = MOCK_RUNS.slice(0, 20).filter(r => r.question.includes('含水率'))
    expect(rowsIn()).toHaveLength(matched.length)
    expect(matched.length).toBeGreaterThan(0)
    expect(screen.getByTestId('search-scope').textContent).toBe(`已载入 20 条中匹配 ${matched.length} 条`)
  })

  it('无命中＝「无匹配对话」空态（不报错、不伪造行）', () => {
    render(<ThreadList runs={MOCK_RUNS} />)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: 'zzz-不存在的问句' } })
    expect(rowsIn()).toHaveLength(0)
    expect(screen.getByText('无匹配对话')).toBeTruthy()
  })

  it('搜索中不触发上拉加载（入口让位；滚动亦不加载）', () => {
    render(<ThreadList runs={MOCK_RUNS} />)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '井' } })
    expect(screen.queryByTestId('load-more')).toBeNull()
    fireEvent.scroll(screen.getByTestId('thread-scroll'), { target: { scrollTop: 0 } })
    expect(rowsIn().length).toBeLessThanOrEqual(20) // 窗口未扩大
    // 清空搜索＝回到加载语义
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '' } })
    expect(screen.getByTestId('load-more')).toBeTruthy()
  })
})

describe('ThreadList · 选中与空态', () => {
  it('选中行高亮（data-selected）并回调该行', () => {
    const onSelect = vi.fn()
    render(<ThreadList runs={MOCK_RUNS} selectedId={MOCK_RUNS[1].run_id} onSelect={onSelect} />)
    const sel = screen.getByTestId(`thread-row-${MOCK_RUNS[1].run_id}`)
    expect(sel.dataset.selected).toBe('true')
    expect(sel.style.background).toContain('rgba(22, 119, 255')
    expect(screen.getByTestId(`thread-row-${MOCK_RUNS[0].run_id}`).dataset.selected).toBe('false')
    fireEvent.click(sel)
    expect(onSelect).toHaveBeenCalledWith(MOCK_RUNS[1])
  })

  it('runs 空＝「暂无历史对话」（空态不报错、不出加载入口）', () => {
    render(<ThreadList runs={[]} />)
    expect(screen.getByText('暂无历史对话')).toBeTruthy()
    expect(screen.getByTestId('load-more')).toBeTruthy() // 入口仍在（封顶前）
    expect(within(screen.getByTestId('thread-list')).queryAllByTestId(/^thread-row-/)).toHaveLength(0)
  })
})
