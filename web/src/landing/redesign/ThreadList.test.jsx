/**
 * ThreadList 钉测（左侧历史对话——FE-04 真接 listRunsV2＋触底自动加载 + 搜索）。
 *
 * 守什么（specs/frontend-redesign.md「验收测试」表第 14/15 行＋行为约定 L1/L2；Owner 反馈
 * 打磨批⑦：零按钮零提示、纯触底自动加载）：
 * - 真接形态（::live_limit_step_cap_100）：数据源＝内部态＋fetchRuns 注入（默认 listRunsV2，
 *   测试注桩零网络）——初始 limit=20；触底＝limit+20 重拉全量替换（后端无 offset——
 *   真源 appv2/api/chat.py list_runs，limit 夹 1..100），20→40→…→100 封顶；封顶后不再调读口；
 *   桩返回 120 条时窗口只到 100（maxRows clamp）。
 * - **零按钮零提示**（打磨批⑦）：DOM 无「加载更早」按钮、无「已到最早」小字——加载靠触底
 *   自动，到头静默；窗口数与库数不一致时也再没有「已载入 20 / 10」这类自相矛盾计数行。
 * - **触底判定**（列表最新在上、更早在下）：离底 ≤40px 触发；离底远（顶滚）不触发；
 *   搜索中/已 exhausted/到 maxRows 同样不触发。
 * - **exhausted 判定**（拿到响应后）：新行数＝旧行数（没有新内容）或 行数<limit（库比窗口小）
 *   → 此后不再 fetch。
 * - **一链一行**（显示粒度＝追问链）：链归属＝followup_of 逐跳上溯取根（根＝followup_of 空串
 *   或指向窗口外），链内 created_at 升序，行＝链内最早轮（title＝该轮问句）、副行＝
 *   `{最新轮状态} · {轮数} 轮 · {时间}`；链序按最新轮时间降序；分组**只作用于显示**——
 *   onRuns 回传的窗口仍是原始行。
 * - 搜索（::search_client_side_no_fetch）：对当前已加载窗口前端过滤、零请求（命中任一链轮＝
 *   该链全部成员保留，链不因搜索残缺）；无命中出「无匹配对话」空态；搜索中不触发加载。
 * - 读口失败≠空库（UI-14 同位纪律）：失败＝「暂无数据」失败空态；读口如实返回空列＝「暂无历史对话」。
 *
 * 素材：__fixtures__/runs.js 的 FIXTURE_RUNS（120 条 RunListItem 形态——FE-04 起为测试夹具，
 * 页面已不直喂）；该夹具的 2 轮链中**最新轮＝链内较晚行**（见「夹具事实」注释下的断言）。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'

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

/** fetchRuns 桩：按 limit 回窗口（后端语义——limit 夹取后按 created_at 降序回列）。 */
const stubRuns = (rows = FIXTURE_RUNS) => vi.fn(async limit => rows.slice(0, limit))

/** 无视 limit 的桩（行数不随窗口变——「没有新内容」的 exhausted 现场）。 */
const stubSameAlways = (rows = FIXTURE_RUNS) => vi.fn(async () => rows)

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
    const fetchRuns = stubRuns()
    const onRuns = vi.fn()
    render(<ThreadList fetchRuns={fetchRuns} onRuns={onRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    expect(rowsIn()).toHaveLength(14)      // 20 原始行 → 14 条链（6 条 followup 轮并入链行）
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
    const fetchRuns = stubRuns()
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

describe('ThreadList · 触底自动加载（零按钮零提示——打磨批⑦；scroll_auto_load_exhausted）', () => {
  it('零按钮零提示：DOM 无「加载更早」按钮、无「已到最早」小字（未搜索时也不出「已载入 …」）', async () => {
    render(<ThreadList fetchRuns={stubRuns()} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    const box = screen.getByTestId('thread-list')
    expect(screen.queryByTestId('load-more')).toBeNull()
    expect(screen.queryByTestId('earliest-tip')).toBeNull()
    expect(within(box).queryByRole('button')).toBeNull() // 加载入口整块没有按钮
    expect(box.textContent).not.toContain('加载更早')
    expect(box.textContent).not.toContain('已到最早')
    expect(box.textContent).not.toContain('已载入')
  })

  it('滚到底＝limit+20 重拉全量替换（20 → 40）；行数随窗口增长（14 → 27）', async () => {
    const fetchRuns = stubRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    scrollBottom()
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[39].run_id}`) // 新入窗链行（原窗口外的链根）
    expect(screen.queryByTestId(`thread-row-${FIXTURE_RUNS[19].run_id}`)).toBeNull() // 原独立行并入新入窗 followup 链（行标识随链内最早轮改判）
    expect(rowsIn()).toHaveLength(27)
    expect(fetchRuns).toHaveBeenLastCalledWith(40)
  })

  it('顶滚不触发（离底远超 40px）：窗口不扩、读口不再调', async () => {
    const fetchRuns = stubRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    scrollTop()
    await Promise.resolve() // 让微任务落地——确认无新请求进入
    expect(rowsIn()).toHaveLength(14)
    expect(fetchRuns).toHaveBeenCalledTimes(1)
  })

  it('scroll_auto_load_exhausted：无新内容（新行数＝旧行数）→ exhausted，此后触底不再 fetch（静默，无提示）', async () => {
    const fetchRuns = stubSameAlways() // 行数不随窗口变（120 恒 120）
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    scrollBottom()
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[39].run_id}`) // 窗口扩到 40（行数没变＝没有新内容）
    expect(fetchRuns).toHaveBeenCalledTimes(2) // 20 → 40 两次
    scrollBottom()
    scrollBottom()
    await Promise.resolve()
    expect(fetchRuns).toHaveBeenCalledTimes(2) // exhausted 后不再 fetch
    expect(screen.getByTestId('thread-list').textContent).not.toContain('已到最早')
  })

  it('库比窗口小（runs.length < limit）→ exhausted，不再 fetch；窗口仍是全库', async () => {
    const small = FIXTURE_RUNS.slice(0, 30)
    const fetchRuns = stubRuns(small)
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${small[0].run_id}`)
    expect(fetchRuns).toHaveBeenLastCalledWith(20)
    scrollBottom() // limit 40 → 库只 30 条
    await screen.findByTestId(`thread-row-${small[29].run_id}`) // 第 30 条行入窗（全库都在）
    expect(fetchRuns).toHaveBeenLastCalledWith(40)
    scrollBottom()
    await Promise.resolve()
    expect(fetchRuns).toHaveBeenCalledTimes(2) // 库比窗口小＝到头
    expect(rowsIn().length).toBeGreaterThan(14) // 全库 30 条已在窗（比初载 20 条窗口多）
  })

  it('上限可配（maxRows）：步进到 maxRows 后触底不再 fetch（零提示，不假装还能加载）', async () => {
    const fetchRuns = stubRuns()
    render(<ThreadList fetchRuns={fetchRuns} maxRows={40} pageStep={20} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    scrollBottom()
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[39].run_id}`)
    expect(rowsIn()).toHaveLength(27)
    expect(fetchRuns).toHaveBeenLastCalledWith(40)
    scrollBottom() // 到 maxRows＝40 → 不再拉
    scrollBottom()
    await Promise.resolve()
    expect(fetchRuns).toHaveBeenCalledTimes(2)
    expect(screen.queryByTestId('earliest-tip')).toBeNull()
    expect(screen.queryByTestId('load-more')).toBeNull()
  })

  it('回归（Owner 截图怪相）：窗口数 > 库数时不再出「已载入 20 / 10」旧计数行', async () => {
    const small = FIXTURE_RUNS.slice(0, 10) // 库比初始窗口小
    const fetchRuns = stubRuns(small)
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${small[0].run_id}`)
    const box = screen.getByTestId('thread-list')
    expect(box.textContent).not.toMatch(/已载入\s*\d+\s*\/\s*\d+/) // 自相矛盾计数行随按钮删除消失
    expect(screen.queryByTestId('load-more')).toBeNull()
    expect(screen.queryByTestId('earliest-tip')).toBeNull()
  })
})

describe('ThreadList · 收口刷新（refreshKey——V2-137）', () => {
  it('refreshKey 变更＝重拉全量替换：读口再调一次且实参回 20（已触底到 40 也回初始窗）', async () => {
    const fetchRuns = stubRuns()
    const { rerender } = render(<ThreadList fetchRuns={fetchRuns} refreshKey={0} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    expect(fetchRuns).toHaveBeenCalledTimes(1)
    expect(fetchRuns).toHaveBeenLastCalledWith(20)

    scrollBottom() // 上拉到 40（刷新＝回初始窗的对照基线）
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[39].run_id}`)
    expect(fetchRuns).toHaveBeenLastCalledWith(40)

    rerender(<ThreadList fetchRuns={fetchRuns} refreshKey={1} />)
    await waitFor(() => expect(fetchRuns).toHaveBeenCalledTimes(3))
    expect(fetchRuns).toHaveBeenLastCalledWith(20) // 刷新＝limit 回 pageStep（上拉进度不复用）
    expect(rowsIn()).toHaveLength(14)               // 窗口回到 20 条 → 14 条链行
  })

  it('refreshKey 不变＝不重拉（缺省 0 与改动前逐字等价）；搜索态不随刷新清空', async () => {
    const fetchRuns = stubRuns()
    const { rerender } = render(<ThreadList fetchRuns={fetchRuns} refreshKey={0} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    rerender(<ThreadList fetchRuns={fetchRuns} refreshKey={0} />) // 同值重渲＝effect 不重跑
    expect(fetchRuns).toHaveBeenCalledTimes(1)

    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '含水率' } })
    expect(screen.getByTestId('search-scope')).toBeTruthy()
    rerender(<ThreadList fetchRuns={fetchRuns} refreshKey={1} />)
    await waitFor(() => expect(fetchRuns).toHaveBeenCalledTimes(2))
    // 搜索态（query 内部态）不随刷新清空——过滤照旧生效
    expect(screen.getByPlaceholderText('搜索对话').value).toBe('含水率')
    expect(screen.getByTestId('search-scope')).toBeTruthy()
  })
})

describe('ThreadList · 规格钉测（specs「验收测试」表第 14/15 行）', () => {
  it('live_limit_step_cap_100：初始 20、步进 40…100 封顶；封顶后不再调读口；120 条只到 100', async () => {
    const fetchRuns = stubRuns() // 桩按 limit 回窗口；返回行数随窗口增长（120 条库）
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    expect(fetchRuns).toHaveBeenCalledWith(20) // 初始 limit=20
    for (let want = 40; want <= 100; want += 20) {
      scrollBottom()
      await screen.findByTestId(`thread-row-${FIXTURE_RUNS[want - 1].run_id}`)
      expect(fetchRuns).toHaveBeenLastCalledWith(want)
    }
    expect(rowsIn()).toHaveLength(67) // 100 条窗口 → 67 条链行
    expect(fetchRuns).toHaveBeenCalledTimes(5) // 20/40/60/80/100——封顶后不再调读口
    expect(screen.queryByTestId('load-more')).toBeNull() // 零按钮
    expect(screen.queryByTestId('earliest-tip')).toBeNull() // 零提示（打磨批⑦）
    // 窗口止于第 100 条：第 100 条行在内、第 101 条行不在（120 条只到 100）
    expect(screen.getByTestId(`thread-row-${FIXTURE_RUNS[99].run_id}`)).toBeTruthy()
    expect(screen.queryByTestId(`thread-row-${FIXTURE_RUNS[100].run_id}`)).toBeNull()
    // 第 6 次触发（滚到底／顶）不越界、不调读口
    scrollBottom()
    scrollTop()
    expect(fetchRuns).toHaveBeenCalledTimes(5)
    expect(rowsIn()).toHaveLength(67)
  })

  it('search_client_side_no_fetch：搜索期滚动 → 读口调用次数不变；无匹配→「无匹配对话」', async () => {
    const fetchRuns = stubRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: 'zzz-不存在的问句' } })
    expect(rowsIn()).toHaveLength(0)
    expect(screen.getByText('无匹配对话')).toBeTruthy() // 无匹配空态
    scrollBottom() // 滚动亦不加载
    await Promise.resolve()
    expect(fetchRuns).toHaveBeenCalledTimes(1) // 读口只有初载一次——搜索零请求
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '' } })
    scrollBottom() // 清空搜索＝回到触底加载语义
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[39].run_id}`)
    expect(fetchRuns).toHaveBeenLastCalledWith(40)
  })
})

describe('ThreadList · 搜索（前端过滤已加载窗口；链不因搜索残缺）', () => {
  it('命中任一链轮＝该链全部成员保留（1 行 2 轮）；匹配口径如实说明', async () => {
    const fetchRuns = stubRuns()
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
    const fetchRuns = stubRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: 'zzz-不存在的问句' } })
    expect(rowsIn()).toHaveLength(0)
    expect(screen.getByText('无匹配对话')).toBeTruthy()
  })

  it('搜索中不触发触底加载（滚动亦不加载）', async () => {
    const fetchRuns = stubRuns()
    render(<ThreadList fetchRuns={fetchRuns} />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '井' } })
    scrollBottom()
    await Promise.resolve() // 让微任务落地——确认无新请求进入
    expect(rowsIn().length).toBeLessThanOrEqual(14) // 窗口未扩大（≤ 初始 14 条链行）
    expect(fetchRuns).toHaveBeenCalledTimes(1) // 读口未再调
    // 清空搜索＝回到加载语义
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '' } })
    scrollBottom()
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[39].run_id}`)
    expect(fetchRuns).toHaveBeenLastCalledWith(40)
  })
})

describe('ThreadList · 空态（含读口失败态分离）', () => {
  it('读口返回空列＝「暂无历史对话」（空库态不报错；零按钮零提示）', async () => {
    const fetchRuns = stubRuns([])
    render(<ThreadList fetchRuns={fetchRuns} />)
    expect(await screen.findByText('暂无历史对话')).toBeTruthy()
    expect(screen.queryByTestId('load-more')).toBeNull()
    expect(screen.queryByTestId('earliest-tip')).toBeNull()
    scrollBottom() // 空库＝exhausted（响应 0 条＝与上次 0 条相同）——滚动也不再 fetch
    await Promise.resolve()
    expect(fetchRuns).toHaveBeenCalledTimes(1)
    expect(within(screen.getByTestId('thread-list')).queryAllByTestId(/^thread-row-/)).toHaveLength(0)
  })

  it('读口失败≠空库：「暂无数据」失败空态（UI-14 同位纪律）', async () => {
    const fetchRuns = vi.fn(async () => { throw new Error('boom') })
    render(<ThreadList fetchRuns={fetchRuns} />)
    expect(await screen.findByText('暂无数据')).toBeTruthy() // 失败空态（≠空库文案）
    expect(screen.queryByTestId('load-more')).toBeNull()
    expect(screen.queryByTestId('earliest-tip')).toBeNull()
    expect(within(screen.getByTestId('thread-list')).queryAllByTestId(/^thread-row-/)).toHaveLength(0)
  })
})
