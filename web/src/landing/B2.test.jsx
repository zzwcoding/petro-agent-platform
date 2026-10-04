/**
 * 落地 B2 页组件测试（P1-04）——fetch 级 mock（挡 window.fetch 边界），client/kb
 * 接口层与页面全部真代码：
 * - 渲染：两页签（片段清单/复核队列）＋卡头总数＝refs 求和（B1 端点 1 同源）；
 * - 筛参：类型/关键词经端点 1 query 服务端筛（report_id 携带按报告读法）；
 * - 展开行/详情弹窗懒加载父块回捞（端点 2）；
 * - 标记问题片段（端点 3）：hint 回显＋按钮禁用＋已标记态派生自队列在途态；
 *   409 重复标记兜底（服务端唯一真源）；
 * - 复核队列（端点 4/5/6）：确认转修正流跳 #/B1；驳回空理由禁用＋必填提交；
 *   已驳回单重新标记（新单入队）与销记（端点 6）；
 * - locator 消费（B2 册对账 10；P1-11 桥退役）：location.search 直读 → 跨报告扫描定位 →
 *   打开详情弹窗＋行高亮 class；
 * - UI-03（阶段 1 交互优化）：两表 PagedTable 分页/resetKey、计数读信封 total、
 *   ? 移出标记按钮、未选报告空态分叉、队列竞态守卫（序号丢弃＋同参一次赋值）、
 *   关键词 300ms 防抖（fake timers）、locator 未命中轻提示、报告重试、弹窗内滚、
 *   列头「井号」。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import B2Landing from './B2.jsx'

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

// ── 合同形状夹具（后端 R1 snake_case，同 app/api/kb.py B2 响应模型） ──

const REPORTS = {
  items: [
    { id: 'rpt-1', doc: '《N-02 井完井报告（英文 · 200 页）》', lib_id: 'lib-1', lib: '完井报告库', refs: 5, wiki: 'v1', status: '已入库' },
    { id: 'rpt-2', doc: '《渤中28-1 区块月度生产月报（2026-08）》', lib_id: 'lib-2', lib: '生产月报库', refs: 3, wiki: null, status: '已入库' }
  ],
  total: 2
}
const FRAGS_RPT1 = {
  items: [
    { id: 'f1', report_id: 'rpt-1', report: REPORTS.items[0].doc, well: 'N-02', section: '章节 01 井基本情况 ＞ 1.2 投产信息', type: '原文块', hit: 'N-02（渤中28-1-N2）于 2019-06-15 投产。' },
    { id: 'f2', report_id: 'rpt-1', report: REPORTS.items[0].doc, well: 'N-02', section: '章节 03 图件 ＞ 图 3-7', type: '图片说明块', hit: '图 3-7 岩性柱状图：按深度展示该井段岩性分布。' },
    { id: 'f6', report_id: 'rpt-1', report: REPORTS.items[0].doc, well: 'N-02', section: '全文档', type: '摘要块', hit: '本报告为 N-02 井完井报告摘要。' }
  ],
  total: 3
}
const FRAGS_RPT2 = {
  items: [
    { id: 'f3', report_id: 'rpt-2', report: REPORTS.items[1].doc, well: 'N-11', section: '章节 02 检修与停产 ＞ 2.1 检泵', type: '原文块', hit: 'N-11 井检泵：2026-08-28 → 2026-09-06，影响产量约 210 吨。' }
  ],
  total: 1
}
const CONTEXT = { id: 'f1', type: '原文块', hit: FRAGS_RPT1.items[0].hit, context: '1.2 投产信息：N-02 井位于渤南区块、CEP-A 平台。' }
const ISSUE_PENDING = {
  id: 'iss-1', fragment_id: 'f3', report_id: 'rpt-2',
  fragment_label: '《渤中28-1 区块月度生产月报（2026-08）》 · 章节 02 检修与停产 ＞ 2.1 检泵',
  state: '待质检复核', marked_by: '小李 · 地质/质检', marked_at: '2026-09-29 15:10', reject_reason: null
}
const ISSUES_PENDING = { items: [ISSUE_PENDING], total: 1 }
const MARK_RESP = {
  id: 'iss-2', fragment_id: 'f1', report_id: 'rpt-1',
  fragment_label: '《N-02 井完井报告（英文 · 200 页）》 · 章节 01 井基本情况 ＞ 1.2 投产信息',
  state: '待质检复核', marked_by: '阿强 · 平台运维', marked_at: '2026-10-01 10:00',
  reject_reason: null, hint: '已标记 · 待质检复核——复核确认后由管理员修正片段并重建索引。'
}
const REVIEW_REJECT_RESP = { ...ISSUE_PENDING, state: '已驳回', reject_reason: '检泵日期与台账对不上，请核对 §A.4 后重新标记' }

const json = (status, body) => ({ ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) })

/** fetch 级 mock 路由（/api/kb B2 六端点；有状态队列——标记入队后随 queue 可见）。 */
function apiRouter(overrides = {}) {
  const calls = { fragQueries: [], contexts: 0, marks: [], reviews: [], closes: 0, issueStates: [] }
  const pendingRows = [ISSUE_PENDING] // 在途态（标记成功后追加——服务端唯一真源）
  const rejectedRows = []
  fetchMock.mockImplementation(async (url, init) => {
    const u = String(url)
    const method = init?.method || 'GET'
    if (/\/api\/kb\/fragments\/[^/]+\/context$/.test(u)) {
      calls.contexts += 1
      return overrides.context ? overrides.context() : json(200, CONTEXT)
    }
    if (/\/api\/kb\/fragments\/[^/]+\/issue-reports$/.test(u)) {
      calls.marks.push(u)
      if (overrides.mark) return overrides.mark()
      pendingRows.push(MARK_RESP)
      return json(200, MARK_RESP)
    }
    if (/\/api\/kb\/issue-reports\/[^/]+\/review$/.test(u)) {
      calls.reviews.push({ u, body: JSON.parse(init.body) })
      return overrides.review ? overrides.review() : json(200, ISSUE_PENDING)
    }
    if (/\/api\/kb\/issue-reports\/[^/]+\/close$/.test(u)) {
      calls.closes += 1
      return overrides.close ? overrides.close() : json(200, { id: 'iss-1', state: '已销记 · 不修正' })
    }
    if (u.includes('/api/kb/issue-reports')) {
      calls.issueStates.push(u)
      const state = new URLSearchParams(u.split('?')[1] || '').get('state')
      if (overrides.issues) return overrides.issues(state)
      const rows = state === '已驳回' ? rejectedRows : pendingRows // all/待质检复核＝在途出列
      return json(200, { items: rows, total: rows.length })
    }
    if (u.includes('/api/kb/fragments')) {
      calls.fragQueries.push(u)
      const rid = new URLSearchParams(u.split('?')[1] || '').get('report_id')
      return overrides.fragments ? overrides.fragments(rid) : json(200, rid === 'rpt-2' ? FRAGS_RPT2 : FRAGS_RPT1)
    }
    if (u.includes('/api/kb/reports')) {
      return overrides.reports ? overrides.reports() : json(200, REPORTS)
    }
    return json(404, { code: 'test_unrouted', message: `unexpected ${method} ${u}` })
  })
  return calls
}

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  localStorage.clear()
  sessionStorage.clear()
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('B2 落地页 · 片段清单（端点 1/2）', () => {
  it('两页签渲染：卡头总数＝refs 求和（8）＋台账行＋队列在途计数', async () => {
    apiRouter()
    render(<B2Landing />)

    expect(await screen.findByText('片段清单（8）')).toBeTruthy() // 5 + 3（refs 求和——合同同源）
    expect(await screen.findByText(/N-02（渤中28-1-N2）于 2019-06-15 投产。/)).toBeTruthy()
    expect(screen.getByText('原文块')).toBeTruthy()
    expect(screen.getByText(/复核队列（\d）/)).toBeTruthy()
    // 身份桩注入
    const call = fetchMock.mock.calls.find(c => String(c[0]).includes('/api/kb/reports'))
    expect(call[1].headers['X-Dev-User']).toBe('aqiang')
  })

  it('类型筛带 type 筛参重拉（端点 1 服务端筛）', async () => {
    apiRouter()
    render(<B2Landing />)
    await screen.findByText(/N-02（渤中28-1-N2）于 2019-06-15 投产。/)
    fireEvent.mouseDown(await screen.findByText('类型：全部'))
    await waitFor(() => {
      const typeOpt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '摘要块')
      expect(typeOpt).toBeTruthy()
      fireEvent.click(typeOpt)
    })
    await waitFor(() => {
      const last = fetchMock.mock.calls.filter(c => String(c[0]).includes('/api/kb/fragments?')).pop()
      expect(decodeURIComponent(last[0])).toContain('type=摘要块')
    })
  })

  it('展开行懒加载父块回捞（端点 2）——展开即请求 context', async () => {
    const calls = apiRouter()
    render(<B2Landing />)
    await screen.findByText(/N-02（渤中28-1-N2）于 2019-06-15 投产。/)
    fireEvent.click(document.querySelector('.ant-table-row-expand-icon')) // 展开首行
    await waitFor(() => expect(calls.contexts).toBe(1))
    expect(await screen.findByText('完整上下文段')).toBeTruthy()
    expect(await screen.findByText('1.2 投产信息：N-02 井位于渤南区块、CEP-A 平台。')).toBeTruthy()
  })

  it('报告清单拉取失败：内联 Alert（失败态≠空态）', async () => {
    apiRouter({ reports: () => json(500, { code: 'kb_internal', message: '台账读取失败', trace_id: 'call-r2' }) })
    render(<B2Landing />)
    expect(await screen.findByText('报告下拉拉取失败——不能按报告浏览')).toBeTruthy()
    expect(screen.getByText(/台账读取失败 · code kb_internal · trace call-r2/)).toBeTruthy()
  })
})

describe('B2 落地页 · 标记问题片段（端点 3）', () => {
  it('详情弹窗（双击行）→ 标记成功：hint 回显＋按钮转已标记禁用', async () => {
    const calls = apiRouter()
    render(<B2Landing />)
    fireEvent.doubleClick(await screen.findByText(/N-02（渤中28-1-N2）于 2019-06-15 投产。/))
    expect(await screen.findByText('片段详情')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /标记问题片段/ }))
    expect(await screen.findByText('已标记 · 待质检复核——复核确认后由管理员修正片段并重建索引。')).toBeTruthy()
    await waitFor(() => expect(calls.marks.length).toBe(1))
    expect(screen.getByRole('button', { name: /已标记 · 待质检复核/ })).toBeTruthy()
  })

  it('重复标记 409：内联兜底提示（服务端唯一真源）', async () => {
    apiRouter({ mark: () => json(409, { code: 'kb_issue_duplicate', message: '该片段已有标记单在待质检复核', trace_id: 'call-m1' }) })
    render(<B2Landing />)
    fireEvent.doubleClick(await screen.findByText(/N-02（渤中28-1-N2）于 2019-06-15 投产。/))
    await screen.findByText('片段详情')
    fireEvent.click(screen.getByRole('button', { name: /标记问题片段/ }))
    expect(await screen.findByText('该片段已有标记单在待质检复核——勿重复标记。')).toBeTruthy()
    expect(screen.getByText(/code kb_issue_duplicate/)).toBeTruthy()
  })
})

describe('B2 落地页 · 复核队列（端点 4/5/6）', () => {
  it('队列列表：状态筛带 state 筛参＋驳回单行渲染（驳回理由随行）', async () => {
    const calls = apiRouter({
      issues: state => {
        if (state === '待质检复核') return json(200, ISSUES_PENDING)
        if (state === '已驳回') return json(200, { items: [REVIEW_REJECT_RESP], total: 1 })
        return json(200, { items: [ISSUE_PENDING, REVIEW_REJECT_RESP], total: 2 })
      }
    })
    render(<B2Landing />)
    fireEvent.click(await screen.findByText(/复核队列（\d）/))
    expect((await screen.findAllByText(/小李 · 地质\/质检/)).length).toBeGreaterThanOrEqual(1)
    // state 筛切到已驳回（下拉 option 由 rc-virtual-list 异步渲染——waitFor 后 title 定位）
    fireEvent.mouseDown(await screen.findByText('状态：全部'))
    await waitFor(() => {
      const opt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '已驳回')
      expect(opt).toBeTruthy()
      fireEvent.click(opt)
    })
    expect(await screen.findByText(/驳回理由：检泵日期与台账对不上/)).toBeTruthy()
    await waitFor(() => {
      // 切换筛参带 state=已驳回 重拉（队列加载后另有待质检复核派生调用——取存在性）
      expect(calls.issueStates.some(u => u.includes(encodeURIComponent('已驳回')))).toBe(true)
    })
  })

  it('复核确认转修正流：POST review {action:confirm} → 跳 #/B1 修正入口', async () => {
    const calls = apiRouter()
    render(<B2Landing />)
    fireEvent.click(await screen.findByText(/复核队列（\d）/))
    fireEvent.click(await screen.findByRole('button', { name: /确认 · 转修正流/ }))
    await waitFor(() => expect(calls.reviews.length).toBe(1))
    expect(calls.reviews[0].body).toEqual({ action: 'confirm', reason: null })
    expect(calls.reviews[0].u).toContain('/api/kb/issue-reports/iss-1/review')
    expect(window.location.hash).toBe('#/B1')
  })

  it('驳回：空理由按钮禁用；填理由后 POST review {action:reject, reason}', async () => {
    const calls = apiRouter()
    render(<B2Landing />)
    fireEvent.click(await screen.findByText(/复核队列（\d）/))
    fireEvent.click(await screen.findByRole('button', { name: /驳\s*回/ }))
    // 弹窗内提交钮与行内驳回钮同名且同为 danger——取 modal 容器内的
    const dialogSubmit = [...screen.getAllByRole('button', { name: /驳\s*回/ })]
      .find(b => b.closest('.ant-modal'))
    expect(dialogSubmit).toBeTruthy()
    expect(dialogSubmit.disabled).toBe(true) // 空理由禁用
    fireEvent.change(screen.getByPlaceholderText(/驳回理由（必填）/), {
      target: { value: '检泵日期与台账对不上，请核对 §A.4 后重新标记' }
    })
    expect(dialogSubmit.disabled).toBe(false)
    fireEvent.click(dialogSubmit)
    await waitFor(() => expect(calls.reviews.length).toBe(1))
    expect(calls.reviews[0].body).toEqual({
      action: 'reject', reason: '检泵日期与台账对不上，请核对 §A.4 后重新标记'
    })
  })

  it('已驳回单：重新标记（端点 3 新单入队）与销记（端点 6）', async () => {
    const calls = apiRouter({
      issues: state => {
        if (state === '待质检复核') return json(200, { items: [], total: 0 })
        if (state === 'all') return json(200, { items: [REVIEW_REJECT_RESP], total: 1 })
        return json(200, { items: [], total: 0 })
      }
    })
    render(<B2Landing />)
    fireEvent.click(await screen.findByText(/复核队列（\d）/))
    expect(await screen.findByText('重新标记')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '重新标记' }))
    await waitFor(() => expect(calls.marks.length).toBe(1))
    expect(calls.marks[0]).toContain('/api/kb/fragments/f3/issue-reports') // 对原片段再发新单
    // 销记（队列刷新后驳回单仍在列——mock 队列不迁移状态，销记按钮持续可点）
    fireEvent.click(await screen.findByRole('button', { name: /销\s*记/ }))
    await waitFor(() => expect(calls.closes).toBe(1))
  })
})

describe('B2 落地页 · locator 消费（B2 册对账 10——P1-11 桥退役收口）', () => {
  it('#/B2?chunk= 定位：location.search 直读 → 跨报告扫描 → 打开详情＋行高亮＋消费后清 search', async () => {
    const calls = apiRouter()
    window.history.replaceState(null, '', '/?chunk=f3#/B2') // Shell 剥 query 后的形态（目标在第二卷）
    render(<B2Landing />)

    // 跨报告扫描：先扫 rpt-1 未命中、再扫 rpt-2 命中
    await waitFor(() => {
      const q = calls.fragQueries.filter(u => u.includes('report_id=rpt-2'))
      expect(q.length).toBeGreaterThanOrEqual(1)
    })
    // locator 片段详情弹窗自动打开（命中句在表格行与弹窗两处出现——用 findAll）
    expect((await screen.findAllByText(/N-11 井检泵：2026-08-28 → 2026-09-06/)).length).toBeGreaterThanOrEqual(1)
    // 高亮 class 挂在定位行上（滚动定位锚）
    await waitFor(() => {
      expect(document.querySelector('.b2-locate-flash')).toBeTruthy()
    })
    // 消费即清除（幂等——同 URL 二次进入不重复定位）
    expect(window.location.search).toBe('')
  })

  it('#/B2?chunk= 原始形态（hash query 未剥——兜底读法）：同样定位消费', async () => {
    apiRouter()
    window.history.replaceState(null, '', '/#/B2?chunk=f3') // 剥链未发生的兜底形态
    render(<B2Landing />)
    expect((await screen.findAllByText(/N-11 井检泵：2026-08-28 → 2026-09-06/)).length).toBeGreaterThanOrEqual(1)
  })

  it('locator 指向不存在片段：回退默认报告＋message.info 轻提示，不阻塞台账（UI-03 T12 同步）', async () => {
    apiRouter()
    window.history.replaceState(null, '', '/?chunk=f-none#/B2')
    render(<B2Landing />)
    expect(await screen.findByText(/N-02（渤中28-1-N2）于 2019-06-15 投产。/)).toBeTruthy()
    expect(screen.queryByText('片段详情')).toBeNull()
    expect(window.location.search).toBe('')
    expect(await screen.findByText('未找到对应片段，可能已修正重建')).toBeTruthy() // 未命中轻提示（单卷失败仍静默续扫）
  })
})

describe('B2 落地页 · UI-03 交互优化（PagedTable/竞态/防抖/空态/轻提示）', () => {
  it('T1 分页＋resetKey：片段表翻到第 2 页后类型筛变自动回页 1（不出现超界空表）', async () => {
    let filtered = false
    const rows = n => ({
      items: Array.from({ length: n }, (_, i) => ({
        id: `f-${i + 1}`, report_id: 'rpt-1', report: REPORTS.items[0].doc,
        well: 'N-02', section: `章节 ${String(i + 1).padStart(2, '0')}`,
        type: filtered ? '摘要块' : '原文块', hit: `命中句 ${i + 1}`
      })),
      total: n
    })
    apiRouter({ fragments: () => json(200, filtered ? rows(3) : rows(25)) })
    render(<B2Landing />)
    expect(await screen.findByText('共 25 条')).toBeTruthy() // PagedTable 分页条统计（client 当前行数，单页也显示）
    fireEvent.click(document.querySelector('.ant-pagination-item-2')) // 翻到第 2 页（21–25 行）
    expect(await screen.findByText('命中句 21')).toBeTruthy()
    expect(screen.queryByText('命中句 1')).toBeNull()
    filtered = true // 类型筛变 → resetKey（report|typeF|kw）变化 → 页码归 1
    fireEvent.mouseDown(await screen.findByText('类型：全部'))
    await waitFor(() => {
      const typeOpt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '摘要块')
      expect(typeOpt).toBeTruthy()
      fireEvent.click(typeOpt)
    })
    expect(await screen.findByText('命中句 1')).toBeTruthy()
    expect(screen.queryByText('命中句 21')).toBeNull()
    expect(await screen.findByText('共 3 条')).toBeTruthy()
  })

  it('T2 分页＋resetKey：复核队列翻到第 2 页后状态筛变自动回页 1', async () => {
    let filtered = false
    const rows = n => ({
      items: Array.from({ length: n }, (_, i) => ({
        id: `iss-${i + 1}`, fragment_id: `f-${i + 1}`, report_id: 'rpt-1',
        fragment_label: `压舱标记单 ${i + 1}`, state: filtered ? '已驳回' : '待质检复核',
        marked_by: '小李 · 地质/质检', marked_at: '2026-09-29 15:10', reject_reason: null
      })),
      total: n
    })
    apiRouter({
      issues: state => (state === '待质检复核'
        ? json(200, { items: [], total: 0 })
        : json(200, filtered ? rows(3) : rows(25)))
    })
    render(<B2Landing />)
    fireEvent.click(await screen.findByText(/复核队列（\d）/))
    expect(await screen.findByText('共 25 条')).toBeTruthy()
    fireEvent.click(document.querySelector('.ant-pagination-item-2'))
    expect(await screen.findByText('压舱标记单 21')).toBeTruthy()
    expect(screen.queryByText('压舱标记单 1')).toBeNull()
    filtered = true // 状态筛变 → resetKey（issueF）变化 → 页码归 1
    fireEvent.mouseDown(await screen.findByText('状态：全部'))
    await waitFor(() => {
      const opt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '已驳回')
      expect(opt).toBeTruthy()
      fireEvent.click(opt)
    })
    expect(await screen.findByText('压舱标记单 1')).toBeTruthy()
    expect(screen.queryByText('压舱标记单 21')).toBeNull()
  })

  it('T3 计数读信封 total（与 items.length 解耦——UI-07 server 分页后仍成立）', async () => {
    apiRouter({
      fragments: () => json(200, { items: FRAGS_RPT1.items, total: 9 }), // total=9 ≠ items.length=3
      issues: () => json(200, { items: [ISSUE_PENDING], total: 7 }) // total=7 ≠ items.length=1
    })
    render(<B2Landing />)
    expect(await screen.findByText('筛选结果 9 条')).toBeTruthy() // 行内计数读信封 total
    expect(await screen.findByText('共 3 条')).toBeTruthy() // 表内分页统计＝client 当前行数
    expect(await screen.findByText(/复核队列（7）/)).toBeTruthy() // 页签计数读 pending 信封 total
    fireEvent.click(screen.getByText(/复核队列（7）/))
    expect(await screen.findByText(/标记单 7 条 · 待质检复核 7 段/)).toBeTruthy() // 队列计数读 total
    expect(await screen.findByText('共 1 条')).toBeTruthy()
  })

  it('T4 弹窗 ? 移出标记按钮：点击不触发端点 3，Tooltip 仍在（doMark 行为不变）', async () => {
    const calls = apiRouter()
    render(<B2Landing />)
    fireEvent.doubleClick(await screen.findByText(/N-02（渤中28-1-N2）于 2019-06-15 投产。/))
    await screen.findByText('片段详情')
    const icon = document.querySelector('.ant-modal-footer .anticon-question-circle')
    expect(icon).toBeTruthy() // ? 仍在 footer（hint span 尾部）
    expect(icon.closest('button')).toBeNull() // 不再嵌在标记按钮内（说明热区与提交动作分离）
    fireEvent.mouseEnter(icon)
    expect(await screen.findByText(/标记后进入/)).toBeTruthy() // Tooltip 悬停仍在
    fireEvent.click(icon)
    await act(async () => {}) // 放一个微任务拍——若 ? 有点击副作用会在此暴露
    expect(calls.marks.length).toBe(0) // 点击 ? 不触发标记请求（服务端事务写入）
  })

  it('T5 未选报告（报告清单失败）：片段表空态分叉，不出现业务空态断言', async () => {
    apiRouter({ reports: () => json(500, { code: 'kb_internal', message: '台账读取失败', trace_id: 'call-r5' }) })
    render(<B2Landing />)
    expect(await screen.findByText('报告下拉拉取失败——不能按报告浏览')).toBeTruthy()
    expect(await screen.findByText('未选择报告或报告清单不可用——恢复后自动加载')).toBeTruthy()
    expect(screen.queryByText('该报告暂无片段：入库完成后这里按报告建台账。')).toBeNull()
    expect(document.querySelector('.ant-empty')).toBeTruthy() // Empty 形态（内联 Alert 另挂——失败态≠空态）
  })

  it('T6 竞态守卫：快速连切 issueF，过期响应不覆盖最后一次筛选结果', async () => {
    let releaseAll // 首拍 state=all 响应挂起（制造过期响应）
    apiRouter({
      issues: state => {
        if (state === 'all') return new Promise(resolve => { releaseAll = () => resolve(json(200, { items: [ISSUE_PENDING], total: 1 })) })
        if (state === '待质检复核') return Promise.resolve(json(200, { items: [ISSUE_PENDING], total: 1 }))
        return Promise.resolve(json(200, { items: [REVIEW_REJECT_RESP], total: 1 }))
      }
    })
    render(<B2Landing />)
    fireEvent.click(await screen.findByText(/复核队列（\d）/))
    // 连切：all（在途挂起）→ 已驳回（立即返回）
    fireEvent.mouseDown(await screen.findByText('状态：全部'))
    await waitFor(() => {
      const opt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '已驳回')
      expect(opt).toBeTruthy()
      fireEvent.click(opt)
    })
    expect(await screen.findByText(/驳回理由：检泵日期与台账对不上/)).toBeTruthy()
    // 旧 all 响应此刻才到——请求序号守卫必须丢弃（不回写旧结果）
    await act(async () => { releaseAll() })
    expect(screen.queryByRole('button', { name: /确认 · 转修正流/ })).toBeNull() // 待质检复核行未回写
    expect(screen.getByText(/驳回理由：检泵日期与台账对不上/)).toBeTruthy() // 最终渲染最后一次筛选结果
  })

  it('T6 待质检复核态：主请求与派生请求同参——只发一次（Promise.all 一次赋值）', async () => {
    const calls = apiRouter()
    render(<B2Landing />)
    await waitFor(() => expect(calls.issueStates.length).toBe(2)) // 首拍：all＋待质检复核派生
    fireEvent.click(await screen.findByText(/复核队列（\d）/))
    fireEvent.mouseDown(await screen.findByText('状态：全部'))
    await waitFor(() => {
      const opt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '待质检复核')
      expect(opt).toBeTruthy()
      fireEvent.click(opt)
    })
    await waitFor(() => {
      const pendingCalls = calls.issueStates.filter(u => u.includes(encodeURIComponent('待质检复核')))
      expect(pendingCalls.length).toBe(2) // 首拍派生 1 次＋切后主请求 1 次（同参不重发）
    })
  })

  it('T7 关键词 300ms 防抖：击键窗口内多次输入只发一次请求（fake timers）', async () => {
    const calls = apiRouter()
    render(<B2Landing />)
    await screen.findByText(/N-02（渤中28-1-N2）于 2019-06-15 投产。/) // 首拍数据到位（真计时器）
    const before = calls.fragQueries.length
    vi.useFakeTimers()
    try {
      const input = screen.getByPlaceholderText('搜命中句 / 井号 / 章节…')
      await act(async () => {
        fireEvent.change(input, { target: { value: '检' } })
        vi.advanceTimersByTime(100)
        fireEvent.change(input, { target: { value: '检泵' } })
        vi.advanceTimersByTime(100)
        fireEvent.change(input, { target: { value: '检泵日期' } })
        vi.advanceTimersByTime(299) // 仍在 300ms 防抖窗口内
      })
      expect(calls.fragQueries.length).toBe(before) // 窗口内零请求
      await act(async () => { vi.advanceTimersByTime(1) }) // 防抖到点
      expect(calls.fragQueries.length).toBe(before + 1) // 只发一次
      expect(decodeURIComponent(calls.fragQueries[calls.fragQueries.length - 1])).toContain('keyword=检泵日期')
    } finally {
      vi.useRealTimers()
    }
  })

  it('T8 卡头 extra 删除：「命中句」列头 ? 保留；T15 列头统一「井号」', async () => {
    apiRouter()
    render(<B2Landing />)
    await screen.findByText(/N-02（渤中28-1-N2）于 2019-06-15 投产。/)
    expect(screen.queryByText('命中的是小段，完整段落不直接进搜索结果')).toBeNull() // extra 已删（同义重复收束）
    expect(screen.getByText('井号')).toBeTruthy() // 列头统一「井号」（合同三件套口径——B2 册 §0）
    const hitHeader = screen.getByText('命中句').closest('span')
    expect(hitHeader.querySelector('.anticon-question-circle')).toBeTruthy() // HIT_HELP ? 收束保留一处
  })

  it('T9 队列空态分支＋Empty 形态：全部空「还没有标记单」；筛选空「没有符合条件的标记单。」', async () => {
    apiRouter({ issues: () => json(200, { items: [], total: 0 }) })
    render(<B2Landing />)
    fireEvent.click(await screen.findByText(/复核队列（0）/))
    expect(await screen.findByText('还没有标记单')).toBeTruthy()
    expect(document.querySelector('.ant-empty')).toBeTruthy() // Empty 形态（PRESENTED_IMAGE_SIMPLE）
    fireEvent.mouseDown(await screen.findByText('状态：全部'))
    await waitFor(() => {
      const opt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '已驳回')
      expect(opt).toBeTruthy()
      fireEvent.click(opt)
    })
    expect(await screen.findByText('没有符合条件的标记单。')).toBeTruthy()
    expect(screen.queryByText('还没有标记单')).toBeNull()
  })

  it('T10 详情弹窗 body 内滚：maxHeight calc(100vh - 300px)＋overflowY auto', async () => {
    apiRouter()
    render(<B2Landing />)
    fireEvent.doubleClick(await screen.findByText(/N-02（渤中28-1-N2）于 2019-06-15 投产。/))
    const title = await screen.findByText('片段详情')
    const body = title.closest('.ant-modal').querySelector('.ant-modal-body')
    expect(body).toBeTruthy()
    expect(body.style.maxHeight).toBe('calc(100vh - 300px)') // 滚动收进弹窗体（长 context 标题页脚不随滚出视野）
    expect(body.style.overflowY).toBe('auto')
  })

  it('T13 报告拉取失败：Alert 带重试按钮——点击后恢复下拉与台账', async () => {
    let fail = true
    apiRouter({ reports: () => (fail ? json(500, { code: 'kb_internal', message: '台账读取失败', trace_id: 'call-r13' }) : json(200, REPORTS)) })
    render(<B2Landing />)
    expect(await screen.findByText('报告下拉拉取失败——不能按报告浏览')).toBeTruthy()
    fail = false
    fireEvent.click(screen.getByRole('button', { name: /重\s*试/ })) // antd 两字按钮自动插空格（驳\s*回同例）
    expect(await screen.findByText(/N-02（渤中28-1-N2）于 2019-06-15 投产。/)).toBeTruthy()
    expect(await screen.findByText('片段清单（8）')).toBeTruthy()
    expect(screen.queryByText('报告下拉拉取失败——不能按报告浏览')).toBeNull()
  })
})
