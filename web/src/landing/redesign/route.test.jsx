/**
 * 临时路由接线钉测（重设计 mock 静态页 A1V2R——并排对比不覆盖现状页）。
 *
 * 守什么：
 * - 注册面：`REDESIGN_LIT` 含 A1V2R 且**不进 LANDING_LIT**（阶段点亮链十键不受污染——
 *   dual-tree-smoke 的十键断言仍绿）；`PROTO_EXCLUDED` 含 A1V2R（不出原型树同名副本）；
 * - 菜单面：`roles.js` MENU 有「问一问V2·新版(mock)」条目（全员可见，与 A1V2 并排）；
 * - 路由面：hash `#/A1V2R` → 落地树 page=A1V2R；懒加载器解析出默认导出组件；
 * - 页头标题来源＝PAGE_NAMES 该键。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'

import {
  LANDING_LIT, PROTO_EXCLUDED, REDESIGN_LIT, loadRedesignPage
} from '../registry.js'
import { MENU, PAGE_NAMES, menuForRole } from '../../roles.js'
import { parseHash } from '../../shell/Shell.jsx'

// antd v5 在 jsdom 下的两个环境桩（同 landing/A1V2.test.jsx）
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

afterEach(() => {
  cleanup()
  window.history.replaceState(null, '', '/')
})

describe('A1V2R 临时路由 · 注册与菜单接线', () => {
  it('REDESIGN_LIT 含 A1V2R；LANDING_LIT 仍为阶段十键（mock 页不混入点亮链）', () => {
    expect(REDESIGN_LIT).toEqual(['A1V2R'])
    expect(LANDING_LIT).toEqual(['A1', 'A1V2', 'D1', 'B1', 'B2', 'B5', 'B3', 'A2', 'B4', 'E2'])
  })

  it('PROTO_EXCLUDED 含 A1V2R（mock 页自身即 mock，不出原型树同名副本）', () => {
    expect(PROTO_EXCLUDED).toEqual(['A1V2', 'A1V2R'])
  })

  it('菜单项「问一问V2·新版(mock)」紧邻 A1V2（工作台组、全员可见）', () => {
    const workbench = MENU.find(g => g.group === '工作台')
    const keys = workbench.items.map(i => i.key)
    expect(keys.indexOf('A1V2R')).toBe(keys.indexOf('A1V2') + 1)
    expect(PAGE_NAMES.A1V2R).toBe('问一问V2·新版(mock)')
    expect(menuForRole('shixi').find(g => g.group === '工作台').items.map(i => i.key)).toContain('A1V2R')
  })

  it('#/A1V2R → 落地树 page=A1V2R（现状页 A1V2 的 hash 不受影响）', () => {
    window.history.replaceState(null, '', '/#/A1V2R')
    expect(parseHash()).toEqual({ tree: 'landing', page: 'A1V2R' })
    window.history.replaceState(null, '', '/#/A1V2')
    expect(parseHash()).toEqual({ tree: 'landing', page: 'A1V2' })
  })

  it('懒加载器解析出页面组件（默认导出＝mock 版面页）', async () => {
    const mod = await loadRedesignPage('A1V2R')
    expect(typeof mod.default).toBe('function')
  })

  it('Shell 端到端：#/A1V2R 渲染出 mock 版面页（懒加载＋Suspense 真路径）', async () => {
    window.history.replaceState(null, '', '/#/A1V2R')
    const { default: Shell } = await import('../../shell/Shell.jsx')
    render(<Shell />)
    expect(await screen.findByText(/新版答案卡版面/)).toBeTruthy()
    expect(screen.getByTestId('turn-t-full')).toBeTruthy()
  })
})
