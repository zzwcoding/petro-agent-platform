/**
 * ThreadList 钉测（左侧历史对话——FE-04 真接 listRunsV2＋上拉加载 + 搜索）。
 *
 * 守什么（specs/frontend-redesign.md「验收测试」表第 14/15 行＋行为约定 L1/L2；Owner 反馈
 * 打磨批：一链一行／滚到底加载）：
 * - 真接形态（::live_limit_step_cap_100）：数据源＝内部态＋fetchRuns 注入（默认 listRunsV2，
 *   测试注桩零网络）——初始 limit=20；「加载更早」＝limit+20 重拉全量替换（后端无 offset——
 *   真源 appv2/api/chat.py list_runs，limit 夹 1..100），20→40→…→100 封顶；封顶后不再调
 *   读口、「已到最早」在场；桩返回 120 条时窗口只到 100（maxRows clamp）。
 * - **一链一行**（显示粒度＝追问链）：链归属＝followup_of 逐跳上溯取根（根＝followup_of 空串
 *   或指向窗口外），链内 created_at 升序，行＝链内最早轮（title＝该轮问句）、副行＝
 *   `{最新轮状态} · {轮数} 轮 · {时间}`；链序按最新轮时间降序；分组**只作用于显示**——
 *   onRuns 回传的窗口仍是原始行。
 * - **滚到底加载**（列表最新在上、更早在下）：离底 ≤40px 触发 loadMore；离底远（顶滚）不触发；
 *   搜索中/封顶后同样不触发。
 * - 搜索（::search_client_side_no_fetch）：对当前已加载窗口前端过滤、零请求（命中任一链轮＝
 *   该链全部成员保留，链不因搜索残缺）；无命中出「无匹配对话」空态。
 * - 读口失败≠空库（UI-14 同位纪律）：失败＝加载入口撤下＋「暂无数据」失败空态；
 *   读口如实返回空列＝「暂无历史对话」。
 *
 * 素材：__fixtures__/runs.js 的 FIXTURE_RUNS（120 条 RunListItem 形态——FE-04 起为测试夹具，
 * 页面已不直喂）；该夹具的 2 轮链中**最新轮＝链内较晚行**（见「夹具事实」注释下的断言）。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'

import ThreadList from './ThreadList.jsx'
import { FIXTURE_RUNS } from './__fixtures__/runs.js'

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
const stubFullRuns = () => vi.fn(async () => FIXTURE_RUNS)

/**
 * 滚动桩（jsdom 无布局、无真滚动）：scrollHeight/clientHeight 桩化后派发 scroll——
 * `bottom`＝离底 0（900+200 ≥ 1000-40）；`top`＝顶（0+200 ＝ 200 < 960，远未到底）。
 */
function scroll(el, at) {
  Object.defineProperty(el, 'scrollHeight', { configurable: true, value: 1000 })
  Object.defineProperty(el, 'clientHeight', { configurable: true, value: 200 })
  el.scrollTop = at === 'bottom' ? 900 : 0
  fireEvent.scroll(el)
}
const scrollBottom = () => scroll(screen.getByTestId('thread-scroll'), 'bottom')
const scrollTop = () => scroll(screen.getByTestId('thread-scroll'), 'top')

describe('ThreadList · 数据源与初始窗口（真接）', () => {
  it('夹具 120 条；初始 limit=20 → 14 行（20 原始行按链分组：6 条 followup 轮并入其链行）', async () => {
    expect(FIXTURE_RUNS).toHaveLength(120)
    expect(Object.keys(FIXTURE_RUNS[0]).sort())
      .toEqual(['created_at', 'followup_of', 'question', 'run_id', 'status', 'updated_at'])
    const fetchRuns = stubFullRuns()
    const onRuns = vi.fn()
    render(<ThreadList fetchRuns={fetchRuns} onRuns={onRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    expect(rowsIn()).toHaveLength(14)      // 20 原始行 → 14 条链（6 条 followup 轮并入链行）
    expect(screen.getByTestId('load-more').textContent).toContain('已载入 20 / 100')
    expect(fetchRuns).toHaveBeenCalledTimes(1)
    expect(fetchRuns).toHaveBeenCalledWith(20) // 初始 limit=20（规格第 14 行）
    // 分组只作用于显示：onRuns 回传的仍是**原始窗口**（前 20 条——页面拉链按原始行上溯）
    expect(onRuns).toHaveBeenCalledWith(FIXTURE_RUNS.slice(0, 20))

    // 单轮链行＝问句（18 字截断＋省略号）＋状态·轮数·时间
    const single = screen.getByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    expect(single.textContent).toContain('W-11 井生产套管的尺寸与下深是多少？'.slice(0, 18))
    expect(single.textContent).toContain('…') // 截断如实标出
    expect(single.textContent).toContain('运行中 · 1 轮 · 10-17 09:20')
  })

  it('夹具事实：2 轮链（FIXTURE_RUNS[1]/[2]）＝一行——行标签＝链内最早轮问句、副行＝最新轮状态·轮数·时间', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    // 行 testid＝链内 created_at 最早轮（旧页 buildThreads 的行标识口径）
    const row = await screen.findByTestId(`thread-row-${FIXTURE_RUNS[2].run_id}`)
    expect(screen.queryByTestId(`thread-row-${FIXTURE_RUNS[1].run_id}`)).toBeNull() // 同链不另开行
    expect(row.textContent).toContain('去年各井含水率是多少？') // 链内最早轮问句（<18 字不截）
    expect(row.textContent).toContain('已完成 · 2 轮 · 10-17 09:12') // 最新轮（FIXTURE_RUNS[1]）状态与时间
  })
})

describe('ThreadList · 一链一行（分组／点击／链成员高亮）', () => {
  /** 自定义窗口：一条 root＋2 轮 followup（最新轮＝第三轮，状态 waiting_ask）＋一条无关单轮。
   *  按后端位序＝created_at 降序返回。 */
  const CHAIN_RUNS = [
    { run_id: 'run-c3', question: '第三轮追问', status: 'waiting_ask', followup_of: 'run-c2', created_at: '2026-10-17 10:20:00', updated_at: '2026-10-17 10:20:30' },
    { run_id: 'run-c2', question: '第二轮追问', status: 'failed', followup_of: 'run-c1', created_at: '2026-10-17 10:10:00', updated_at: '2026-10-17 10:10:30' },
    { run_id: 'run-c1', question: '链根问句', status: 'completed', followup_of: '', created_at: '2026-10-17 10:00:00', updated_at: '2026-10-17 10:00:30' },
    { run_id: 'run-x', question: '无关单轮', status: 'completed', followup_of: '', created_at: '2026-10-17 09:00:00', updated_at: '2026-10-17 09:00:30' }
  ]

  it('root＋2 轮 followup＝1 行；无关单轮各占一行；链序按最新轮时间降序', async () => {
    render(<ThreadList fetchRuns={vi.fn(async () => CHAIN_RUNS)} />)
    const row = await screen.findByTestId('thread-row-run-c1')
    expect(rowsIn()).toHaveLength(2) // 三轮一链＝一行＋无关单轮一行
    expect(row.textContent).toContain('链根问句')
    expect(row.textContent).toContain('待确认 · 3 轮 · 10-17 10:20') // 状态/时间取链内最新轮（run-c3）
    expect(screen.getByTestId('thread-row-run-x').textContent).toContain('已完成 · 1 轮 · 10-17 09:00')
    expect(rowsIn().map(el => el.dataset.testid)).toEqual(['thread-row-run-c1', 'thread-row-run-x']) // 链序＝最新轮降序
  })

  it('点行＝onSelect(链内最新轮行)——拉链交给页面（本件只回行）', async () => {
    const onSelect = vi.fn()
    render(<ThreadList fetchRuns={vi.fn(async () => CHAIN_RUNS)} onSelect={onSelect} />)
    fireEvent.click(await screen.findByTestId('thread-row-run-c1'))
    expect(onSelect).toHaveBeenCalledWith(CHAIN_RUNS[0]) // run-c3＝链内最新轮
    fireEvent.click(screen.getByTestId('thread-row-run-x'))
    expect(onSelect).toHaveBeenLastCalledWith(CHAIN_RUNS[3])
  })

  it('选中高亮按链成员：selectedId 是链内任一轮 → 该链行高亮；他链不亮', async () => {
    const onSelect = vi.fn()
    render(<ThreadList fetchRuns={vi.fn(async () => CHAIN_RUNS)} selectedId="run-c2" onSelect={onSelect} />)
    const chainRow = await screen.findByTestId('thread-row-run-c1')
    expect(chainRow.dataset.selected).toBe('true')       // 链成员含选中轮（中间轮 run-c2）即高亮
    expect(chainRow.style.background).toContain('rgba(22, 119, 255')
    expect(screen.getByTestId('thread-row-run-x').dataset.selected).toBe('false')
    // 点他行＝回调他链最新轮（选中态由页面写回，本件不内改）
    fireEvent.click(screen.getByTestId('thread-row-run-x'))
    expect(onSelect).toHaveBeenCalledWith(CHAIN_RUNS[3])
  })
})

describe('ThreadList · 上拉加载（滚到底触发；limit 步进＝后端无 offset 的映射）', () => {
  it('「加载更早」一次＝limit+20 重拉全量（20 → 40）；行数随窗口增长（14 → 27）', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    fireEvent.click(screen.getByTestId('load-more'))
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[39].run_id}`) // 新入窗链行（原窗口外的链根）
    expect(screen.queryByTestId(`thread-row-${FIXTURE_RUNS[19].run_id}`)).toBeNull() // 原独立行并入新入窗 followup 链（行标识随链内最早轮改判）
    expect(rowsIn()).toHaveLength(27)
    expect(screen.getByTestId('load-more').textContent).toContain('已载入 40 / 100')
    expect(fetchRuns).toHaveBeenLastCalledWith(40)
  })

  it('滚到列表底部＝同一 handler（离底 ≤40px 触发 +20 重拉）', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    scrollBottom()
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[39].run_id}`)
    expect(rowsIn()).toHaveLength(27)
    expect(fetchRuns).toHaveBeenLastCalledWith(40)
  })

  it('顶滚不触发（离底远超 40px）：窗口不扩、读口不再调', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    scrollTop()
    await Promise.resolve() // 让微任务落地——确认无新请求进入
    expect(rowsIn()).toHaveLength(14)
    expect(fetchRuns).toHaveBeenCalledTimes(1)
  })

  it('上限可配（maxRows）——步进语义与后端 clamp 同形', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} maxRows={40} pageStep={20} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    fireEvent.click(screen.getByTestId('load-more'))
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[39].run_id}`)
    expect(rowsIn()).toHaveLength(27)
    expect(screen.getByTestId('earliest-tip')).toBeTruthy()
  })
})

describe('ThreadList · 规格钉测（specs「验收测试」表第 14/15 行）', () => {
  it('live_limit_step_cap_100：初始 20、步进 40…100 封顶「已到最早」；封顶后不再调读口；120 条只到 100', async () => {
    const fetchRuns = stubFullRuns() // 桩记录每次 limit；返回 120 条——窗口裁剪归组件（maxRows clamp）
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    expect(fetchRuns).toHaveBeenCalledWith(20) // 初始 limit=20
    for (let want = 40; want <= 100; want += 20) {
      fireEvent.click(screen.getByTestId('load-more'))
      await screen.findByTestId(`thread-row-${FIXTURE_RUNS[want - 1].run_id}`)
      expect(fetchRuns).toHaveBeenLastCalledWith(want)
    }
    expect(rowsIn()).toHaveLength(67) // 100 条窗口 → 67 条链行
    expect(fetchRuns).toHaveBeenCalledTimes(5) // 20/40/60/80/100——封顶后不再调读口
    expect(screen.queryByTestId('load-more')).toBeNull()
    expect(screen.getByTestId('earliest-tip').textContent).toBe('已到最早')
    // 窗口止于第 100 条：第 100 条行在内、第 101 条行不在（120 条只到 100）
    expect(screen.getByTestId(`thread-row-${FIXTURE_RUNS[99].run_id}`)).toBeTruthy()
    expect(screen.queryByTestId(`thread-row-${FIXTURE_RUNS[100].run_id}`)).toBeNull()
    // 第 6 次触发（滚到底／顶——按钮已让位）不越界、不调读口
    scrollBottom()
    scrollTop()
    expect(fetchRuns).toHaveBeenCalledTimes(5)
    expect(rowsIn()).toHaveLength(67)
  })

  it('search_client_side_no_fetch：搜索期触发 loadMore/滚动 → 读口调用次数不变；无匹配→「无匹配对话」', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: 'zzz-不存在的问句' } })
    expect(rowsIn()).toHaveLength(0)
    expect(screen.getByText('无匹配对话')).toBeTruthy() // 无匹配空态
    expect(screen.queryByTestId('load-more')).toBeNull() // 加载入口让位
    scrollBottom() // 滚动亦不加载
    expect(fetchRuns).toHaveBeenCalledTimes(1) // 读口只有初载一次——搜索零请求
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '' } })
    expect(screen.getByTestId('load-more')).toBeTruthy() // 清空搜索＝回到加载语义
  })
})

describe('ThreadList · 搜索（前端过滤已加载窗口；链不因搜索残缺）', () => {
  it('命中任一链轮＝该链全部成员保留（1 行 2 轮）；匹配口径如实说明', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '含水率' } })
    expect(rowsIn()).toHaveLength(1) // 窗口内 1 条原始命中（FIXTURE_RUNS[2]）→ 其链整行保留
    const row = screen.getByTestId(`thread-row-${FIXTURE_RUNS[2].run_id}`)
    expect(row.textContent).toContain('去年各井含水率是多少？')
    expect(row.textContent).toContain('2 轮') // 链成员（FIXTURE_RUNS[1]）同留——链不残缺
    expect(screen.getByTestId('search-scope').textContent).toBe('已载入 20 条中匹配 1 个对话')
  })

  it('无命中＝「无匹配对话」空态（不报错、不伪造行）', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: 'zzz-不存在的问句' } })
    expect(rowsIn()).toHaveLength(0)
    expect(screen.getByText('无匹配对话')).toBeTruthy()
  })

  it('搜索中不触发上拉加载（入口让位；滚动亦不加载）', async () => {
    const fetchRuns = stubFullRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '井' } })
    expect(screen.queryByTestId('load-more')).toBeNull()
    scrollBottom()
    await Promise.resolve() // 让微任务落地——确认无新请求进入
    expect(rowsIn().length).toBeLessThanOrEqual(14) // 窗口未扩大（≤ 初始 14 条链行）
    expect(fetchRuns).toHaveBeenCalledTimes(1) // 读口未再调
    // 清空搜索＝回到加载语义
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '' } })
    expect(screen.getByTestId('load-more')).toBeTruthy()
  })
})

describe('ThreadList · 空态（含读口失败态分离）', () => {
  it('读口返回空列＝「暂无历史对话」（空库态不报错；加载入口仍在）', async () => {
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
