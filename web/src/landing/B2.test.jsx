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
 * - locator 消费（B2 册对账 10）：sessionStorage chunk → 跨报告扫描定位 →
 *   打开详情弹窗＋行高亮 class。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import B2Landing from './B2.jsx'
import { B2_LOCATOR_KEY } from './registry.js'

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

describe('B2 落地页 · locator 消费（B2 册对账 10）', () => {
  it('#/B2?chunk= 定位：sessionStorage chunk → 跨报告扫描 → 打开详情＋行高亮', async () => {
    const calls = apiRouter()
    sessionStorage.setItem(B2_LOCATOR_KEY, 'f3') // 目标在第二卷报告（NotLit 桥交接）
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
    // 消费即清除（幂等——同会话二次进入不重复定位）
    expect(sessionStorage.getItem(B2_LOCATOR_KEY)).toBeNull()
  })

  it('locator 指向不存在片段：静默回退默认报告，不阻塞台账', async () => {
    apiRouter()
    sessionStorage.setItem(B2_LOCATOR_KEY, 'f-none')
    render(<B2Landing />)
    expect(await screen.findByText(/N-02（渤中28-1-N2）于 2019-06-15 投产。/)).toBeTruthy()
    expect(screen.queryByText('片段详情')).toBeNull()
    expect(sessionStorage.getItem(B2_LOCATOR_KEY)).toBeNull()
  })
})
