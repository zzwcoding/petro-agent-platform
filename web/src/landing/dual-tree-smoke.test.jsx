/**
 * 双树渲染冒烟·常驻回归件（DEP-01 件④——W-LAND 临时冒烟 7 例升格，W-LAND.rev F5 收口）。
 *
 * 守什么：双树纪律的行为面——落地树三页（landing/E2·A2·B4）消费真端点
 * （fetch 实发 URL 断言），原型树三页（pages/E2·A2·B4）自包含零 api 调用
 * （stub fetch 断言零次）。原型树被直接改写或落地页断链时本套红灯。
 *
 * 原型树文件级防改另有机器闸 tools/prototype_guard.py（hash ×
 * web/prototype-manifest.json 比对，CI 前端 job 同岗）——本件守渲染行为，
 * 两者互补。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import { LANDING_LIT } from './registry.js'
import E2Landing from './E2.jsx'
import A2Landing from './A2.jsx'
import B4Landing from './B4.jsx'
import E2Proto from '../pages/E2.jsx'
import A2Proto from '../pages/A2.jsx'
import B4Proto from '../pages/B4.jsx'

// antd v5 在 jsdom 下的两个环境桩（同 landing/E2.test.jsx）
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

const json = (status, body) => ({ ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) })
const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

/** 落地树 404 兜底路由：只应答登记过的 URL，未登记端点一律 404（防漏断言）。 */
function allow(...prefixes) {
  fetchMock.mockImplementation(async url => {
    const u = String(url)
    return prefixes.some(p => u.startsWith(p))
      ? json(200, {})
      : json(404, { code: 'smoke_unrouted', message: `unexpected ${u}` })
  })
}

describe('双树冒烟 · 注册表（例 1）', () => {
  it('LANDING_LIT 十键在册：A1/A1V2/D1/B1/B2/B5/B3/A2/B4/E2——既有九页不丢、A1V2＝问一问V2 对接基线页', () => {
    expect(LANDING_LIT).toEqual(['A1', 'A1V2', 'D1', 'B1', 'B2', 'B5', 'B3', 'A2', 'B4', 'E2'])
  })
})

describe('双树冒烟 · 落地树真端点消费（例 2-4）', () => {
  it('落地 E2 首屏四拉取实发 /api/quality/{rules,tasks,issues,freshness}＋规则行渲染＋X-Dev-User 桩', async () => {
    fetchMock.mockImplementation(async (url, init) => {
      const u = String(url)
      if (u.includes('/api/quality/rules')) {
        return json(200, { items: [{ no: 1, kind: '重复', rule: '同一口井同一天每个班次只能有一条日产记录', crit: '班次三元组唯一', enabled: true, action: '告警', autoFix: false }] })
      }
      if (u.includes('/api/quality/tasks')) return json(200, { items: [] })
      if (u.includes('/api/quality/issues')) return json(200, { lanes: ['分发', '认领', '整改', '复核', '关闭'], items: [], page: 1, page_size: 500, total: 0 })
      if (u.includes('/api/quality/freshness')) return json(200, { items: [] })
      return json(404, { code: 'smoke_unrouted', message: `unexpected ${u}` })
    })
    render(<E2Landing />)

    expect(await screen.findByText(/规则库（1）/)).toBeTruthy()
    expect(screen.getByText(/同一口井同一天每个班次只能有一条日产记录/)).toBeTruthy()
    for (const ep of ['/api/quality/rules', '/api/quality/tasks', '/api/quality/issues', '/api/quality/freshness']) {
      expect(fetchMock.mock.calls.some(c => String(c[0]).includes(ep))).toBe(true)
    }
    const call = fetchMock.mock.calls.find(c => String(c[0]).includes('/api/quality/rules'))
    expect(call[1].headers['X-Dev-User']).toBe('aqiang') // client 统一出口身份桩
  })

  it('落地 A2 消费 /api/wells 四端点（列表＋profile＋chain＋change-tickets）＋「渤中28-1-N2」渲染', async () => {
    fetchMock.mockImplementation(async url => {
      const u = String(url)
      if (u === '/api/wells' || u.startsWith('/api/wells?')) {
        return json(200, { items: [{ well_id: 'N-02', well_name: '渤中28-1-N2', well_kind: '采油', well_kind_code: 'EW', block_name: '渤南', current_status: '生产中', remark: null }], total: 1 })
      }
      if (u === '/api/wells/N-02') {
        return json(200, { well_id: 'N-02', well_name: '渤中28-1-N2', well_kind: '采油', well_kind_code: 'EW', first_prod_date: '2019-06-15', platform: 'CEP-A', block_name: '渤南', current_status: '生产中', remark: null, quality_notes: [], foot_note: null })
      }
      if (u === '/api/wells/N-02/chain') {
        return json(200, { well_id: 'N-02', counts: { events: 0, measures: 0, devices: 0, overhauls: 0, changes: 0 }, measure_foot: null, device_foot: null, events: [], measures: [], devices: [], overhauls: [], tail: null })
      }
      if (u === '/api/wells/N-02/change-tickets') return json(200, { well_id: 'N-02', items: [], total: 0 })
      return json(404, { code: 'smoke_unrouted', message: `unexpected ${u}` })
    })
    render(<A2Landing />)

    expect(await screen.findByText('渤中28-1-N2')).toBeTruthy() // 档案明细井名
    for (const ep of ['/api/wells', '/api/wells/N-02', '/api/wells/N-02/chain', '/api/wells/N-02/change-tickets']) {
      expect(fetchMock.mock.calls.some(c => String(c[0]) === ep)).toBe(true)
    }
  })

  it('落地 B4 消费 /api/wiki/pages——空库空态即验收态「暂无百科页」', async () => {
    fetchMock.mockImplementation(async url => (
      String(url).startsWith('/api/wiki/pages')
        ? json(200, { items: [], page: 1, page_size: 20, total: 0 })
        : json(404, { code: 'smoke_unrouted', message: `unexpected ${url}` })
    ))
    render(<B4Landing />)

    expect(await screen.findByText(/暂无百科页——报告入库且库配置开启 wiki 支路后自动生成/)).toBeTruthy()
    expect(fetchMock.mock.calls.some(c => String(c[0]).startsWith('/api/wiki/pages'))).toBe(true)
  })
})

describe('双树冒烟 · 原型树自包含零 api 调用（例 5-7）', () => {
  it('原型 E2 mock 规则种子渲染＋问题单 p7 流转「复核」后「复扫」按钮在位——全程零 fetch', async () => {
    allow() // 全部 404——原型页若发 fetch 立即被计数
    render(<E2Proto />)

    expect(await screen.findByText(/同一口井同一天每个班次只能有一条日产记录——A\/B 班手抄重复行即命中/)).toBeTruthy()
    fireEvent.click(screen.getByText(/问题单（\d）/))
    expect(await screen.findByText('规则 7 · 井号未归一（N2 → N-02）')).toBeTruthy() // p7 在整改（lane 2）
    fireEvent.click(screen.getAllByRole('button', { name: /流转/ }).find(b => b.closest('tr')?.textContent.includes('规则 7')))
    expect(await screen.findByRole('button', { name: '复 扫' })).toBeTruthy() // lane 2→3 复核——v0.5 人工触发复扫
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('原型 A2 内嵌 WELLS 种子渲染（N-02 默认选中「渤中28-1-N2」）——零 fetch', async () => {
    allow()
    render(<A2Proto />)

    expect(await screen.findAllByText(/渤中28-1-N2/).then(nodes => expect(nodes.length).toBeGreaterThan(0))).toBeTruthy()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('原型 B4 mock 目录种子渲染（「《N-02 井完井报告》」）——零 fetch', async () => {
    allow()
    render(<B4Proto />)

    expect(await screen.findByText('《N-02 井完井报告》')).toBeTruthy()
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
