/**
 * ThreadList 钉测（左侧历史对话——FE-04 真接 listRunsV2＋上拉加载 + 搜索）。
 *
 * 守什么（specs/frontend-redesign.md「验收测试」表第 14/15 行＋行为约定 L1/L2）：
 * - 真接形态（::live_limit_step_cap_100）：数据源＝内部态＋fetchRuns 注入（默认 listRunsV2，
 *   测试注桩零网络）——初始 limit=20；「加载更早」＝limit+20 重拉全量替换（后端无 offset——
 *   真源 appv2/api/chat.py list_runs，limit 夹 1..100），20→40→…→100 封顶；封顶后不再调
 *   读口、「已到最早」在场；桩返回 120 条时列表只渲染 100（maxRows clamp）。
 * - 搜索（::search_client_side_no_fetch）：对当前已加载窗口前端过滤、零请求（搜索期触发
 *   loadMore/滚动，读口调用次数不变）；无命中出「无匹配对话」空态。
 * - 读口失败≠空库（UI-14 同位纪律）：失败＝计数行撤下＋「暂无数据」失败空态；
 *   读口如实返回空列＝「暂无历史对话」。
 * - mock 期 10 条行为测试等价改造保留（数据源 props 喂数换注入桩，行为钉不松）。
 *
 * 素材：redesign/mockTurns.js 的 MOCK_RUNS（120 条 RunListItem 形态——FE-04 起为测试夹具，
 * 页面已不直喂）。
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

/** fetchRuns 桩：忽略 limit 返回全量 120 条（复刻 mock 期数据源形态——窗口裁剪归组件 slice）。 */
const stubFullRuns = () => vi.fn(async () => MOCK_RUNS)

describe('ThreadList · 数据源与初始窗口（真接）', () => {
  it('夹具 120 条（RunListItem 形态）；初始拉取 limit=20 只渲染前 20 条', async () => {
    expect(MOCK_RUNS).toHaveLength(120)
    expect(Object.keys(MOCK_RUNS[0]).sort())
      .toEqual(['created_at', 'followup_of', 'question', 'run_id', 'status', 'updated_at'])
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    expect(rowsIn()).toHaveLength(20)
    expect(screen.getByTestId('load-more').textContent).toContain('已载入 20 / 100')
    expect(fetchRuns).toHaveBeenCalledTimes(1)
    expect(fetchRuns).toHaveBeenCalledWith(20) // 初始 limit=20（规格第 14 行）
    // 行内＝问句＋状态白话＋时间（MM-DD HH:mm）
    const first = screen.getByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    expect(first.textContent).toContain('W-11 井生产套管的尺寸与下深是多少？'.slice(0, 18))
    expect(first.textContent).toContain('运行中 · 10-17 09:20')
  })
})

describe('ThreadList · 上拉加载（limit 步进＝后端无 offset 的映射）', () => {
  it('「加载更早」一次＝limit+20 重拉全量（20 → 40）', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    fireEvent.click(screen.getByTestId('load-more'))
    await screen.findByTestId(`thread-row-${MOCK_RUNS[39].run_id}`)
    expect(rowsIn()).toHaveLength(40)
    expect(screen.getByTestId('load-more').textContent).toContain('已载入 40 / 100')
    expect(fetchRuns).toHaveBeenLastCalledWith(40)
  })

  it('滚到列表顶部＝同一 handler（jsdom 无真滚动；scrollTop 0 触发 +20 重拉）', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    fireEvent.scroll(screen.getByTestId('thread-scroll'), { target: { scrollTop: 0 } })
    await screen.findByTestId(`thread-row-${MOCK_RUNS[39].run_id}`)
    expect(rowsIn()).toHaveLength(40)
  })

  it('连续加载到 100 封顶：不再增长，入口让位「已到最早」（不出无限 Spin）', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    for (let want = 40; want <= 100; want += 20) {
      fireEvent.click(screen.getByTestId('load-more'))
      await screen.findByTestId(`thread-row-${MOCK_RUNS[want - 1].run_id}`)
    }
    expect(rowsIn()).toHaveLength(100)
    expect(screen.queryByTestId('load-more')).toBeNull()
    expect(screen.getByTestId('earliest-tip').textContent).toBe('已到最早')
    // 再触发（滚动）也不越界
    fireEvent.scroll(screen.getByTestId('thread-scroll'), { target: { scrollTop: 0 } })
    expect(rowsIn()).toHaveLength(100)
  })

  it('上限可配（maxRows）——步进语义与后端 clamp 同形', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} maxRows={40} pageStep={20} />)
    await screen.findByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    fireEvent.click(screen.getByTestId('load-more'))
    await screen.findByTestId(`thread-row-${MOCK_RUNS[39].run_id}`)
    expect(rowsIn()).toHaveLength(40)
    expect(screen.getByTestId('earliest-tip')).toBeTruthy()
  })
})

describe('ThreadList · 规格钉测（specs「验收测试」表第 14/15 行）', () => {
  it('live_limit_step_cap_100：初始 20、步进 40…100 封顶「已到最早」；封顶后不再调读口；120 条只渲染 100', async () => {
    const fetchRuns = stubFullRuns() // 桩记录每次 limit；返回 120 条——窗口裁剪归组件（maxRows clamp）
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    expect(fetchRuns).toHaveBeenCalledWith(20) // 初始 limit=20
    for (let want = 40; want <= 100; want += 20) {
      fireEvent.click(screen.getByTestId('load-more'))
      await screen.findByTestId(`thread-row-${MOCK_RUNS[want - 1].run_id}`)
      expect(fetchRuns).toHaveBeenLastCalledWith(want)
    }
    expect(rowsIn()).toHaveLength(100) // 桩返回 120 条——maxRows clamp 只渲染 100
    expect(fetchRuns).toHaveBeenCalledTimes(5) // 20/40/60/80/100——封顶后不再调读口
    expect(screen.queryByTestId('load-more')).toBeNull()
    expect(screen.getByTestId('earliest-tip').textContent).toBe('已到最早')
    // 第 6 次触发（滚动——按钮已让位）不越界、不调读口
    fireEvent.scroll(screen.getByTestId('thread-scroll'), { target: { scrollTop: 0 } })
    expect(fetchRuns).toHaveBeenCalledTimes(5)
    expect(rowsIn()).toHaveLength(100)
  })

  it('search_client_side_no_fetch：搜索期触发 loadMore/滚动 → 读口调用次数不变；无匹配→「无匹配对话」', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: 'zzz-不存在的问句' } })
    expect(rowsIn()).toHaveLength(0)
    expect(screen.getByText('无匹配对话')).toBeTruthy() // 无匹配空态
    expect(screen.queryByTestId('load-more')).toBeNull() // 加载入口让位
    fireEvent.scroll(screen.getByTestId('thread-scroll'), { target: { scrollTop: 0 } }) // 滚动亦不加载
    expect(fetchRuns).toHaveBeenCalledTimes(1) // 读口只有初载一次——搜索零请求
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '' } })
    expect(screen.getByTestId('load-more')).toBeTruthy() // 清空搜索＝回到加载语义
  })
})

describe('ThreadList · 搜索（前端过滤已加载窗口）', () => {
  it('命中：只留匹配行，并如实说明匹配口径（已载入 20 条中匹配 N 条）', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '含水率' } })
    const matched = MOCK_RUNS.slice(0, 20).filter(r => r.question.includes('含水率'))
    expect(rowsIn()).toHaveLength(matched.length)
    expect(matched.length).toBeGreaterThan(0)
    expect(screen.getByTestId('search-scope').textContent).toBe(`已载入 20 条中匹配 ${matched.length} 条`)
  })

  it('无命中＝「无匹配对话」空态（不报错、不伪造行）', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: 'zzz-不存在的问句' } })
    expect(rowsIn()).toHaveLength(0)
    expect(screen.getByText('无匹配对话')).toBeTruthy()
  })

  it('搜索中不触发上拉加载（入口让位；滚动亦不加载）', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '井' } })
    expect(screen.queryByTestId('load-more')).toBeNull()
    fireEvent.scroll(screen.getByTestId('thread-scroll'), { target: { scrollTop: 0 } })
    await Promise.resolve() // 让微任务落地——确认无新请求进入
    expect(rowsIn().length).toBeLessThanOrEqual(20) // 窗口未扩大
    expect(fetchRuns).toHaveBeenCalledTimes(1) // 读口未再调
    // 清空搜索＝回到加载语义
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '' } })
    expect(screen.getByTestId('load-more')).toBeTruthy()
  })
})

describe('ThreadList · 选中与空态（含读口失败态分离）', () => {
  it('选中行高亮（data-selected）并回调该行', async () => {
    const onSelect = vi.fn()
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} selectedId={MOCK_RUNS[1].run_id} onSelect={onSelect} />)
    const sel = await screen.findByTestId(`thread-row-${MOCK_RUNS[1].run_id}`)
    expect(sel.dataset.selected).toBe('true')
    expect(sel.style.background).toContain('rgba(22, 119, 255')
    expect(screen.getByTestId(`thread-row-${MOCK_RUNS[0].run_id}`).dataset.selected).toBe('false')
    fireEvent.click(sel)
    expect(onSelect).toHaveBeenCalledWith(MOCK_RUNS[1])
  })

  it('读口返回空列＝「暂无历史对话」（空库态不报错；封顶前加载入口仍在）', async () => {
    const fetchRuns = vi.fn(async () => [])
    render(<ThreadList fetchRuns={fetchRuns} />)
    expect(await screen.findByText('暂无历史对话')).toBeTruthy()
    expect(screen.getByTestId('load-more')).toBeTruthy() // 入口仍在（封顶前）
    expect(within(screen.getByTestId('thread-list')).queryAllByTestId(/^thread-row-/)).toHaveLength(0)
  })

  it('读口失败≠空库：计数行撤下＋「暂无数据」失败空态（UI-14 同位纪律）', async () => {
    const fetchRuns = vi.fn(async () => { throw new Error('boom') })
    render(<ThreadList fetchRuns={fetchRuns} />)
    expect(await screen.findByText('暂无数据')).toBeTruthy() // 失败空态（≠空库文案）
    expect(screen.queryByTestId('load-more')).toBeNull() // 计数行撤下
    expect(screen.queryByTestId('earliest-tip')).toBeNull()
    expect(within(screen.getByTestId('thread-list')).queryAllByTestId(/^thread-row-/)).toHaveLength(0)
  })
})
