/**
 * E2 质检台页面组件测试（W-E2 接线票）——fetch 级 mock（真 api 层＋真页面代码）：
 * - 空库空态渲染（R-WIRE E2-10：任务/问题单/水位三页签空态即验收态）；
 * - snake_case 字段映射（R-WIRE E2-1/2/3：quarantined_rows/rejected_batches、
 *   rules 顶键、ai_note/close_note）＋报告弹窗/详情抽屉；
 * - 轮询语义真化（E2-8：受理 202 → pollTaskUntilDone 轮询 tasks/{id} 至 done，
 *   撤 mock 250ms 固定延时——done 后任务入列＋报告弹窗＋问题单刷新）；
 * - 错误 toast 收口（E2-6：13-20 启停 422 仅登记档——client 层弹一次，页面回退不重复弹）；
 * - 流转请求体形状（E2-5：流转空体；响应 lane/state 回写行）；
 * - 首屏失败态（E2-12：内联失败态≠空态＋重试按钮）。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import E2Quality from './E2.jsx'
import { setApiNotifier } from '../api/client.js'

// 注：本测试随页迁落地树（W-LAND 双树归位）——landing/ 由 registry.js 显式
// 导入（非 Shell.jsx 动态 glob 面），测试与页同目录不给 dist 添 chunk
// （pages/__tests__ 子目录惯例的由来见 W-E2 偏差 2，此约束落地树不适用）。

// antd v5 在 jsdom 下的两个环境桩（matchMedia＝响应式断点；ResizeObserver＝Table 测宽）
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

// ── 合同形状夹具（后端 R1 snake_case，同 app/api/quality.py 响应模型） ──

const RULES = {
  items: [
    { no: 1, kind: '重复', rule: '同一口井同一天每个班次只能有一条日产记录', crit: '班次三元组唯一', enabled: true, action: '告警', autoFix: false },
    { no: 13, kind: '引用完整', rule: '引用的编号要能在关联的表里找到对应记录', crit: '详见规则库总册', enabled: false, action: '—（总册）', autoFix: false }
  ]
}
const TASKS_EMPTY = { items: [] }
const TASK_DONE = {
  id: 'QT-20261004-01', time: '2026-10-04 10:00', rules: 12, hits: 1,
  report: {
    range: '生产库 8 表', scanned: '12,604 行',
    quarantined_rows: 2, rejected_batches: 1,
    hits: ['① 规则 1：N-02 在 2026-09-14 出现 A/B 两行重复日报'],
    verdict: '——已全部开成问题单并按责任岗分发（见「问题单」页签新卡）。'
  }
}
const ISSUES_EMPTY = { lanes: ['分发', '认领', '整改', '复核', '关闭'], items: [], page: 1, page_size: 500, total: 0 }
const DRAFT_ISSUE = {
  id: 'd1', lane: 0, rule_no: 1, hit_count: 2,
  title: '规则 1 · N-02 同日 A/B 两行重复日报', desc: 'A/B 班手抄重复',
  owner: '责任：作业区资料员',
  qrows: [{ loc: null, note: 'A/B 两行重复日报，保留首条，另一行隔离' }],
  ai_note: '规则 1 判据：班次三元组（井,日,班次）唯一', verify: null, close_note: null
}
const CLOSED_ISSUE = {
  id: 'p10', lane: 4, rule_no: 10, hit_count: 1,
  title: '规则 10 · 连续 30 日同值告警', desc: '核实为真实关井',
  owner: '复核通过：小李',
  qrows: [], ai_note: null, verify: null, close_note: '告警类规则核实为真实关井——记录原因后关闭'
}
const ISSUES = {
  lanes: ['分发', '认领', '整改', '复核', '关闭'],
  items: [DRAFT_ISSUE, CLOSED_ISSUE],
  page: 1, page_size: 500, total: 2
}
const ISSUES_AFTER_RUN = {
  lanes: ['分发', '认领', '整改', '复核', '关闭'],
  items: [DRAFT_ISSUE],
  page: 1, page_size: 500, total: 1
}
const FRESHNESS_EMPTY = { items: [] }

const json = (status, body) => ({ ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) })

/**
 * fetch 级 mock 路由（/api/quality/* 九端点子集）。started 模拟「发起任务后」状态：
 * issues 首拉为空、任务 done 后刷新带回动态单——轮询收场链路的页面侧断言锚。
 */
function apiRouter(overrides = {}) {
  const calls = { transitions: [], taskGet: 0 }
  let started = false
  fetchMock.mockImplementation(async (url, init) => {
    const u = String(url)
    const method = init?.method || 'GET'
    if (u.includes('/api/quality/rules') && method === 'PATCH') {
      return overrides.toggle ? overrides.toggle() : json(200, { no: 1, enabled: false })
    }
    if (u.includes('/api/quality/rules')) {
      return overrides.rules ? overrides.rules() : json(200, RULES)
    }
    if (/\/api\/quality\/tasks\/[^/]+$/.test(u)) {
      calls.taskGet += 1
      return overrides.task ? overrides.task() : json(200, { taskId: 'QT-20261004-01', status: 'done', task: TASK_DONE })
    }
    if (u.endsWith('/api/quality/tasks')) {
      if (method === 'POST') {
        started = true
        return overrides.start ? overrides.start() : json(202, { taskId: 'QT-20261004-01' })
      }
      return overrides.tasks ? overrides.tasks() : json(200, started ? { items: [TASK_DONE] } : TASKS_EMPTY)
    }
    if (u.includes('/api/quality/issues/') && method === 'POST') {
      calls.transitions.push(init?.body)
      return json(200, { id: 'd1', lane: 1, state: '认领', verify: null })
    }
    if (u.startsWith('/api/quality/issues')) {
      return overrides.issues ? overrides.issues() : json(200, started ? ISSUES_AFTER_RUN : ISSUES_EMPTY)
    }
    if (u.includes('/api/quality/freshness')) {
      return overrides.freshness ? overrides.freshness() : json(200, FRESHNESS_EMPTY)
    }
    return json(404, { code: 'test_unrouted', message: `unexpected ${method} ${u}` })
  })
  return calls
}

const fetchMock = vi.fn()
const notify = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  notify.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  setApiNotifier(notify)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  setApiNotifier(null)
})

describe('E2 质检台 · 空库空态（R-WIRE E2-10）', () => {
  it('三页签空态渲染：任务/问题单/水位全空——空库即验收态', async () => {
    apiRouter()
    render(<E2Quality />)

    expect(await screen.findByText(/规则库（2）/)).toBeTruthy()
    expect(screen.getByText(/质检任务（0）/)).toBeTruthy()
    expect(screen.getByText(/问题单（0）/)).toBeTruthy()
    expect(screen.getByText(/数据到哪天（0）/)).toBeTruthy()

    fireEvent.click(screen.getByText(/质检任务（0）/))
    expect(await screen.findByText(/暂无质检任务——点上方按钮发起第一遍体检/)).toBeTruthy()

    fireEvent.click(screen.getByText(/数据到哪天（0）/))
    expect(await screen.findByText(/暂无水位数据——水位由入湖\/加工管道回写后呈现/)).toBeTruthy()
    // 身份桩注入
    const call = fetchMock.mock.calls.find(c => String(c[0]).includes('/api/quality/rules'))
    expect(call[1].headers['X-Dev-User']).toBe('aqiang')
  })
})

describe('E2 质检台 · snake_case 字段映射（R-WIRE E2-1/2/3/11）', () => {
  it('任务表「隔离/拒收」列读 quarantined_rows/rejected_batches＋「启用规则」读 rules 顶键', async () => {
    apiRouter({ tasks: () => json(200, { items: [TASK_DONE] }) })
    render(<E2Quality />)
    fireEvent.click(await screen.findByText(/质检任务（1）/))
    expect(await screen.findByText('2 行 / 1 批')).toBeTruthy()
    expect(screen.getByText('12 条')).toBeTruthy()
    expect(screen.getByText('12,604 行')).toBeTruthy()
  })

  it('报告弹窗：隔离/拒收行读 snake_case，「启用规则」行读 task 顶键 rules', async () => {
    apiRouter({ tasks: () => json(200, { items: [TASK_DONE] }) })
    render(<E2Quality />)
    fireEvent.click(await screen.findByText(/质检任务（1）/))
    fireEvent.click(await screen.findByRole('button', { name: /报\s*告/ })) // antd 两字按钮自动插空格（报 告）
    expect(await screen.findByText(/合规报告（质检任务 #QT-20261004-01/)).toBeTruthy()
    expect(screen.getByText(/隔离 2 行 · 整批拒收 1 个批次/)).toBeTruthy()
    expect(screen.getAllByText('12 条').length).toBeGreaterThanOrEqual(1) // 弹窗行＋任务表列同文案并存
    expect(screen.getByText(/不合规 1 项/)).toBeTruthy()
    expect(screen.getByText(/① 规则 1：N-02 在 2026-09-14 出现 A\/B 两行重复日报/)).toBeTruthy()
  })

  it('详情抽屉：诊断说明读 ai_note、关闭原因读 close_note；qrows loc 空值兜底「—」', async () => {
    apiRouter({ issues: () => json(200, ISSUES) })
    render(<E2Quality />)
    fireEvent.click(await screen.findByText(/问题单（2）/)) // 切到问题单页签（表格随页签条件渲染）
    // 免修关闭列读 close_note
    expect(await screen.findByText('免修关闭')).toBeTruthy()
    // 开动态单抽屉：诊断说明＝规则判据说明（v0.5 ai_note 降级投影）
    fireEvent.click(screen.getByText('规则 1 · N-02 同日 A/B 两行重复日报'))
    expect(await screen.findByText('规则 1 判据：班次三元组（井,日,班次）唯一')).toBeTruthy()
    expect(screen.getByText(/隔离 \/ 拦截明细（1）/)).toBeTruthy()
    expect(screen.getByText('A/B 两行重复日报，保留首条，另一行隔离')).toBeTruthy()
    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(1) // loc=null 兜底「—」（复验列同文案并存）
  })

  it('关闭单抽屉：关闭原因读 close_note', async () => {
    apiRouter({ issues: () => json(200, ISSUES) })
    render(<E2Quality />)
    fireEvent.click(await screen.findByText(/问题单（2）/))
    fireEvent.click(await screen.findByText('规则 10 · 连续 30 日同值告警'))
    expect(await screen.findByText('告警类规则核实为真实关井——记录原因后关闭')).toBeTruthy()
  })
})

describe('E2 质检台 · 轮询语义真化与流转（R-WIRE E2-5/8）', () => {
  it('发起质检：202 受理 → 轮询 tasks/{id} 至 done → 任务入列＋报告弹窗＋问题单刷新', async () => {
    const calls = apiRouter()
    render(<E2Quality />)
    fireEvent.click(await screen.findByText(/质检任务（0）/))
    fireEvent.click(screen.getByRole('button', { name: /发起质检任务/ }))

    await waitFor(() => expect(calls.taskGet).toBeGreaterThanOrEqual(1))
    // done 收场：任务记录入列（计数 0→1）＋合规报告弹窗自动打开＋问题单列表刷新
    expect(await screen.findByText(/合规报告（质检任务 #QT-20261004-01/, {}, { timeout: 3000 })).toBeTruthy()
    expect(await screen.findByText(/质检任务（1）/)).toBeTruthy()
    const startCall = fetchMock.mock.calls.find(c => String(c[0]).endsWith('/api/quality/tasks') && c[1]?.method === 'POST')
    expect(startCall[1].body).toBeUndefined() // POST 空体
    expect(await screen.findByText(/问题单（1）/)).toBeTruthy() // 动态单已入列
  }, 15000)

  it('流转：POST 空体 → 响应 lane/state 回写行（分发 → 认领）', async () => {
    apiRouter({ issues: () => json(200, ISSUES) })
    render(<E2Quality />)
    fireEvent.click(await screen.findByText(/问题单（2）/))
    fireEvent.click(await screen.findByText('流转 →'))
    await waitFor(() => expect(fetchMock.mock.calls.some(c => String(c[0]).includes('/issues/d1/transitions'))).toBe(true))
    const tCall = fetchMock.mock.calls.find(c => String(c[0]).includes('/issues/d1/transitions'))
    expect(JSON.parse(tCall[1].body)).toEqual({})
    // 行内环节 Tag 更新
    await waitFor(() => expect(screen.getAllByText('认领').length).toBeGreaterThanOrEqual(1))
  })
})

describe('E2 质检台 · 错误收口（R-WIRE E2-6/7/12）', () => {
  it('13-20 启停 422（quality_rule_registered_only）：client 弹一次，页面乐观回退不重复弹', async () => {
    apiRouter({ toggle: () => json(422, { code: 'quality_rule_registered_only', message: '仅登记规则未实施，不可启用', trace_id: 'call-q1' }) })
    render(<E2Quality />)
    // 规则 1 开关（首行）——状态断言走 aria-checked（rc-switch 两个 children 常驻 DOM，文本不随态变）
    const sw = (await screen.findAllByRole('switch'))[0]
    expect(sw.getAttribute('aria-checked')).toBe('true')
    fireEvent.click(sw)
    await waitFor(() => expect(notify).toHaveBeenCalledTimes(1)) // 错误包只在 client 层弹
    expect(notify.mock.calls[0][0]).toBe('error')
    expect(String(notify.mock.calls[0][1])).toContain('仅登记规则未实施') // 人话 message 随提示带出
    expect(String(notify.mock.calls[0][1])).toContain('trace call-q1') // trace_id 上下文随提示带出
    await waitFor(() => expect(sw.getAttribute('aria-checked')).toBe('true')) // 乐观回退弹回启用态
  })

  it('首屏拉取失败：内联失败态≠空态＋重试按钮', async () => {
    apiRouter({ rules: () => json(500, { code: 'quality_internal', message: '规则库读取失败', trace_id: 'call-e0' }) })
    render(<E2Quality />)
    expect(await screen.findByText(/数据加载失败——/)).toBeTruthy()
    expect(screen.getByText(/规则库读取失败 · code quality_internal · trace call-e0/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /重\s*试/ })).toBeTruthy() // antd 两字按钮自动插空格（重 试）
  })

  it('重试成功：内联失败态翻回数据渲染', async () => {
    let fail = true
    apiRouter({ rules: () => (fail ? json(500, { code: 'quality_internal', message: '规则库读取失败' }) : json(200, RULES)) })
    render(<E2Quality />)
    await screen.findByText(/数据加载失败——/)
    fail = false
    fireEvent.click(screen.getByRole('button', { name: /重\s*试/ }))
    const sw = (await screen.findAllByRole('switch'))[0] // 规则表渲染出开关（两行取首行）
    expect(sw.getAttribute('aria-checked')).toBe('true') // 规则 1 默认启用
  })
})

describe('E2 质检台 · 五态页签（LANES 同源渲染）', () => {
  it('五态页签计数联动＋规则筛选项来自 rule_no', async () => {
    apiRouter({ issues: () => json(200, ISSUES) })
    render(<E2Quality />)
    fireEvent.click(await screen.findByText(/问题单（2）/))
    expect(await screen.findByText('分发（1）')).toBeTruthy()
    expect(screen.getByText('关闭（1）')).toBeTruthy()
    expect(screen.getByText(/整改（0）/)).toBeTruthy() // 五态页签骨架（LANES 同值）
  })
})
