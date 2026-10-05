/**
 * B4 报告百科页面组件测试（W-B4 接线票）——fetch 级 mock（真 api 层＋真页面代码）：
 * - 目录空态渲染（验收项④：wiki_page 表无种子——空态即验收态，R-WIRE §3.2）；
 * - 目录行服务端字段消费（R-WIRE B4-1/2/3：id/source_report/current_version/status
 *   服务端直返——本地 statusTagOf/CUR_VER 退役）；
 * - 目录筛选参数化（B4-4：lib/keyword 服务端筛选——本地 filter 退役，输入防抖）；
 * - 读页异步化＋字段映射（B4-5/6/7：openPage 拉 GET /pages/{id}；元数据条
 *   generation_source/operator/slug 服务端字段；related_objects links 消费 DTO）；
 * - 正文五族标记渲染（B4-8：Md/renderInline 原样——[[well:]]/[[route:]]/
 *   [[claim:]]/[[term:]]/[[flag:]]）；
 * - 证据弹层懒加载（B4-9：展开时 B2 端点 1/2——kb.js 复用件；无锚论断不渲染
 *   [证]、锚失效弹层空态——fail-closed 不伪造回链）；
 * - 台账挂接 chip（B4-10：glossary_terms[].card 投影映射）；
 * - 404 错误态（wiki_not_found——inline errText 三段＋重试）。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import B4 from '../B4.jsx'
import { setApiNotifier } from '../../api/client.js'

// 注：测试落 pages/__tests__/ 子目录（pages/ 直下会被 Shell.jsx 的单层动态导入
// glob 切进 dist——E2.test.jsx 同款惯例位）。

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

// ── 合同形状夹具（teach B4 v0.4 DTO——app/api/wiki.py 响应模型同形 snake_case） ──

const W1_ROW = {
  id: 'wiki-n02-completion',
  title: '《N-02 井完井报告》',
  lib: '完井报告库',
  source_report: { id: 'rpt-n02-completion', doc: '《N-02 井完井报告（英文 · 200 页）》' },
  current_version: 3,
  updated: '2026-09-20',
  status: '字段待核对'
}
const W2_ROW = {
  id: 'wiki-bz281-monthly-202608',
  title: '《渤中28-1 区块月度生产月报》',
  lib: '生产月报库',
  source_report: { id: 'rpt-bz281-monthly-202608', doc: '《渤中28-1 区块月度生产月报（2026-08）》' },
  current_version: 1,
  updated: '2026-09',
  status: '正常'
}
const PAGES_TWO = { items: [W1_ROW, W2_ROW], total: 2 }
const PAGES_EMPTY = { items: [], total: 0 }

// 端点 2 夹具：五族标记俱全的正文节选（w1-c9＝无锚论断——fail-closed 断言锚）
const DETAIL = {
  id: 'wiki-n02-completion',
  title: '《N-02 井完井报告》',
  lib: '完井报告库',
  slug: 'wiki-n02-completion',
  digest: 'N-02 井完井报告：渤南区块 CEP-A 平台采油井，2019-06-15 投产，状态生产中。',
  source_report: { id: 'rpt-n02-completion', doc: '《N-02 井完井报告（英文 · 200 页）》' },
  current_version: 3,
  updated: '2026-09-20',
  status: '字段待核对',
  generation_source: '自动重建',
  operator: '系统（入库管线）',
  related_objects: [
    { type: 'well', id: 'N-02', summary: '井名 渤中28-1-N2 · 井别 采油（EW）· 状态 生产中', links: ['#/A2', '#/B5'] }
  ],
  content: [
    '## 概述',
    '',
    '本报告为 [[well:N-02]] 井完井报告：井位于渤南区块 CEP-B 平台[[flag:与井档案不符，待核对]]，状态生产中[[claim:w1-c1]]，另见[[claim:w1-c9]]。',
    '',
    '涉及指标 [[term:综合含水率]]；全文回 [[route:B1|报告库]]。'
  ].join('\n'),
  claims: [
    { claim_id: 'w1-c1', text: '井别采油，2019-06-15 投产，状态生产中', evidence_chunk_ids: ['f1'] },
    { claim_id: 'w1-c9', text: '无锚论断', evidence_chunk_ids: [] }
  ],
  glossary_terms: [
    { word: '综合含水率', kind: 'metric', ref_id: 5, card: { slot_name: '综合含水率', def: 'Q_w ÷（Q_o＋Q_w）× 100%', grain: '月', unit: '%', status: ['生效中'], owner: '开发室', source: 'A.2 日产计量＋A.6 化验' } }
  ]
}

const FRAGMENTS = {
  items: [
    { id: 'f1', report_id: 'rpt-n02-completion', report: '《N-02 井完井报告（英文 · 200 页）》', well: 'N-02', section: '章节 01 井基本情况 ＞ 1.2 投产信息', type: '原文块', hit: 0 }
  ],
  total: 1
}
const F1_CTX = { id: 'f1', type: '原文块', hit: 0, context: 'N-02（渤中28-1-N2）于 2019-06-15 投产。' }

const json = (status, body) => ({ ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) })

/** fetch 级 mock 路由（/api/wiki/* 两端点＋/api/kb/fragments 证据懒加载两件）。 */
function apiRouter(overrides = {}) {
  fetchMock.mockImplementation(async url => {
    const u = String(url)
    if (u.startsWith('/api/wiki/pages?')) return overrides.pages ? overrides.pages() : json(200, PAGES_TWO)
    if (/\/api\/wiki\/pages\/[^/]+$/.test(u)) return overrides.detail ? overrides.detail() : json(200, DETAIL)
    if (u.startsWith('/api/kb/fragments?')) return overrides.fragments ? overrides.fragments() : json(200, FRAGMENTS)
    if (u.endsWith('/api/kb/fragments/f1/context')) return json(200, F1_CTX)
    return json(404, { code: 'test_unrouted', message: `unexpected ${u}` })
  })
}

const wikiListCalls = () => fetchMock.mock.calls.map(c => String(c[0])).filter(u => u.startsWith('/api/wiki/pages?'))

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

async function openReadPage() {
  apiRouter()
  render(<B4 />)
  fireEvent.doubleClick(await screen.findByText('《N-02 井完井报告》'))
  await screen.findByText(/词条口径卡|当前版：v3/)
}

describe('B4 目录 · 空库空态（R-WIRE §3.2——wiki_page 无种子即验收态）', () => {
  it('空目录渲染：页签计数 0／筛选结果 0 / 0 条／空态文案', async () => {
    apiRouter({ pages: () => json(200, PAGES_EMPTY) })
    render(<B4 />)
    expect(await screen.findByText(/百科页（0）/)).toBeTruthy()
    expect(screen.getByText(/筛选结果 0 \/ 0 条/)).toBeTruthy()
    expect(await screen.findByText(/暂无百科页/)).toBeTruthy()
  })
})

describe('B4 目录 · 服务端字段消费与筛选参数化（R-WIRE B4-1/2/3/4）', () => {
  it('目录行：来源副行/所属库/当前版 vN/updated/status 全部服务端直返', async () => {
    apiRouter()
    render(<B4 />)
    expect(await screen.findByText(/百科页（2）/)).toBeTruthy()
    expect(screen.getByText(/筛选结果 2 \/ 2 条/)).toBeTruthy()
    expect(screen.getByText('来源：《N-02 井完井报告（英文 · 200 页）》')).toBeTruthy()
    expect(screen.getByText('v3')).toBeTruthy()
    expect(screen.getByText('v1')).toBeTruthy()
    expect(screen.getByText('2026-09-20')).toBeTruthy()
    expect(screen.getAllByText('字段待核对').length).toBe(1)
    expect(screen.getAllByText('正常').length).toBe(1)
  })

  it('所属库切换→服务端 lib 参数；关键词输入→防抖后 keyword 参数（本地筛选退役）', async () => {
    apiRouter()
    const { container } = render(<B4 />)
    await screen.findByText(/百科页（2）/)
    fireEvent.mouseDown(container.querySelector('.ant-select-selector'))
    fireEvent.click(await screen.findByText('完井报告库', { selector: '.ant-select-item-option-content' }))
    await waitFor(() => {
      const last = wikiListCalls().at(-1)
      expect(new URL(last, 'http://localhost').searchParams.get('lib')).toBe('完井报告库')
    })
    fireEvent.change(screen.getByPlaceholderText('搜百科页 / 来源报告…'), { target: { value: 'N-02' } })
    await waitFor(() => expect(wikiListCalls().some(u => u.includes('keyword=N-02'))).toBe(true), { timeout: 2000 })
    const last = wikiListCalls().at(-1)
    const qs = new URL(last, 'http://localhost').searchParams
    expect(qs.get('lib')).toBe('完井报告库')
    expect(qs.get('keyword')).toBe('N-02')
  })
})

describe('B4 读页 · 异步化与服务端字段映射（R-WIRE B4-5/6/7/8）', () => {
  it('打开读页：GET /pages/{id}；元数据条/关联对象 links/正文标记族全接真', async () => {
    apiRouter()
    render(<B4 />)
    fireEvent.doubleClick(await screen.findByText('《N-02 井完井报告》'))
    expect(await screen.findByText(/当前版：v3/)).toBeTruthy()
    expect(fetchMock.mock.calls.some(c => String(c[0]) === '/api/wiki/pages/wiki-n02-completion')).toBe(true)
    expect(screen.getByText(/《N-02 井完井报告》 · 百科页/)).toBeTruthy()
    expect(screen.getByText('《N-02 井完井报告（英文 · 200 页）》')).toBeTruthy() // 来源报告链 B1
    expect(screen.getAllByText('自动重建').length).toBeGreaterThanOrEqual(1) // generation_source 服务端字段
    expect(screen.getByText(/操作人 系统（入库管线）/)).toBeTruthy()
    expect(screen.getAllByText('字段待核对').length).toBeGreaterThanOrEqual(1) // status 服务端直返
    expect(screen.getByText('wiki-n02-completion')).toBeTruthy() // slug
    // 展开→关联对象行：label「井 N-02」前端拼装；summary/links 消费 DTO
    fireEvent.click(screen.getByText('展开'))
    expect(await screen.findByText(/井 N-02/)).toBeTruthy()
    expect(screen.getByText(/井名 渤中28-1-N2 · 井别 采油（EW）· 状态 生产中/)).toBeTruthy()
    expect(screen.getByText('井档案').closest('a').getAttribute('href')).toBe('#/A2')
    expect(screen.getByText('关系图谱').closest('a').getAttribute('href')).toBe('#/B5')
    // 正文五族标记：well/flag/claim/term/route
    expect(screen.getByText('N-02').closest('a')).toBeTruthy() // [[well:]]
    expect(screen.getByText(/⚠ 与井档案不符，待核对/)).toBeTruthy() // [[flag:]]
    expect(screen.getByText('综合含水率')).toBeTruthy() // [[term:]]
    const routeLink = screen.getByText('报告库').closest('a') // [[route:]]
    expect(routeLink.getAttribute('href')).toBe('#/B1')
  })

  it('台账挂接 chip：glossary_terms[].card 投影（口径卡字段映射，R-WIRE B4-10）', async () => {
    await openReadPage()
    fireEvent.click(screen.getByText('综合含水率'))
    expect(await screen.findByText('词条口径卡 · 综合含水率')).toBeTruthy()
    expect(screen.getAllByText('指标口径').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Q_w ÷（Q_o＋Q_w）× 100%')).toBeTruthy()
    expect(screen.getByText(/指标台账 #5/)).toBeTruthy()
    expect(screen.getByText(/统计粒度：月 · 单位 %/)).toBeTruthy()
    expect(screen.getByText(/A\.2 日产计量＋A\.6 化验/)).toBeTruthy()
  })
})

describe('B4 证据弹层 · 懒加载 B2 端点 1/2（R-WIRE B4-9——mock 更正清单⑨）', () => {
  it('点「证」展开时才拉切片台账＋父块回捞；弹层显论断句与切片投影', async () => {
    await openReadPage()
    expect(fetchMock.mock.calls.some(c => String(c[0]).startsWith('/api/kb/fragments'))).toBe(false) // 未展开零请求
    fireEvent.click(screen.getByText('证'))
    expect(await screen.findByText('证据来源（切片回链）')).toBeTruthy()
    expect(fetchMock.mock.calls.some(c => String(c[0]).includes('report_id=rpt-n02-completion'))).toBe(true)
    expect(fetchMock.mock.calls.some(c => String(c[0]) === '/api/kb/fragments/f1/context')).toBe(true)
    expect(screen.getByText(/论断：/)).toBeTruthy()
    expect(screen.getByText(/井别采油，2019-06-15 投产，状态生产中/)).toBeTruthy()
    expect(screen.getByText('f1')).toBeTruthy()
    expect(screen.getByText(/章节 01 井基本情况 ＞ 1\.2 投产信息/)).toBeTruthy()
    expect(screen.getByText('N-02（渤中28-1-N2）于 2019-06-15 投产。')).toBeTruthy()
  })

  it('无锚论断不渲染「证」；锚切片不在台账→弹层空态不伪造回链（fail-closed）', async () => {
    apiRouter({ fragments: () => json(200, { items: [], total: 0 }) })
    render(<B4 />)
    fireEvent.doubleClick(await screen.findByText('《N-02 井完井报告》'))
    await screen.findByText(/当前版：v3/)
    expect(screen.getAllByText('证').length).toBe(1) // w1-c9（空锚）不渲染——fail-closed
    fireEvent.click(screen.getByText('证'))
    expect(await screen.findByText(/锚失效/)).toBeTruthy()
    expect(screen.queryByText('f1')).toBeNull() // 不伪造证据条目
  })
})

describe('B4 读页 · 404 错误态（wiki_not_found）', () => {
  it('直调未知页：inline errText 三段＋重试（client 已 toast 不重复弹）', async () => {
    apiRouter({
      detail: () => json(404, {
        code: 'wiki_not_found',
        message: '百科页不存在（含 wiki 开关关未生成）：wiki-n02-completion',
        trace_id: 'tr-x1'
      })
    })
    render(<B4 />)
    fireEvent.doubleClick(await screen.findByText('《N-02 井完井报告》'))
    expect(await screen.findByText(/百科页不存在（含 wiki 开关关未生成）/)).toBeTruthy()
    expect(screen.getByText(/code wiki_not_found/)).toBeTruthy()
    expect(screen.getByText(/trace tr-x1/)).toBeTruthy()
    expect(notify).toHaveBeenCalledTimes(1) // client 层弹一次
    fireEvent.click(screen.getByRole('button', { name: /重\s*试/ })) // antd 两字按钮自动插空格（重 试）
    expect(fetchMock.mock.calls.filter(c => String(c[0]) === '/api/wiki/pages/wiki-n02-completion').length).toBe(2)
  })
})
