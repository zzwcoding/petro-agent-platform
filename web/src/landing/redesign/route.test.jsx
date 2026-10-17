/**
 * 旧页下线与路由转正钉测（specs/frontend-redesign.md「验收测试」表第 18 行 a1v2_replaced）。
 *
 * 守什么：
 * - **注册面**：LANDING_LIT 仍为阶段十键；A1V2 键的懒加载器解析出**真流页**
 *   （landing/redesign/A1V2R.jsx——命名导出 TurnChain 为凭，旧现状页无此导出）；
 * - **菜单面**：roles.js 工作台组 A1V2 文案＝「问一问V2」；临时菜单项「问一问V2·新版(mock)」已删
 *   （PAGE_NAMES 无 A1V2R 键）；PROTO_EXCLUDED 只剩 A1V2；
 * - **文件面**：旧现状页 `landing/A1V2.jsx` 与其测试已删（glob 键集无此文件——删没删机判）；
 *   V1 `landing/A1.jsx` 与其测试原样保留；
 * - **路由面**：hash `#/A1V2` → 落地树 page=A1V2，Shell 端到端渲染真流页（懒加载＋Suspense
 *   真路径，输入区已接线）；旧 `#/A1V2R` 已无对应页＝未点亮占位。
 */
/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'

import { LANDING_LIT, PROTO_EXCLUDED, loadLandingPage } from '../registry.js'
import { MENU, PAGE_NAMES, menuForRole } from '../../roles.js'
import { parseHash } from '../../shell/Shell.jsx'

// antd v5 在 jsdom 下的两个环境桩（同 landing/A1.test.jsx）
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

/** landing/ 顶层源文件键集（glob 只列在场文件——旧页文件删没删由此机判）。 */
const LANDING_FILES = import.meta.glob('../*.jsx')

const fetchMock = vi.fn()

beforeEach(() => {
  // 真流页左栏读口走真接口（chatV2）——桩成 404 不触网（读口失败态＝「暂无数据」）
  fetchMock.mockImplementation(async () => ({ ok: false, status: 404, json: async () => ({}) }))
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.history.replaceState(null, '', '/')
})

describe('旧 A1V2 下线 · 转正路由接线', () => {
  it('a1v2_replaced：A1V2 注册行替换为真流页、阶段十键不变、临时键与菜单项全链下线', async () => {
    // 注册面：十键不变（A1V2 仍在册——内容换成真流页）
    expect(LANDING_LIT).toEqual(['A1', 'A1V2', 'D1', 'B1', 'B2', 'B5', 'B3', 'A2', 'B4', 'E2'])
    const mod = await loadLandingPage('A1V2')
    expect(typeof mod.default).toBe('function')
    expect(typeof mod.TurnChain).toBe('function') // 真流页命名导出——注册行确已替换

    // 菜单面：工作台组 A1V2＝问一问V2；A1V2R 无键、无菜单项、无原型排除残留
    const workbench = MENU.find(g => g.group === '工作台')
    expect(workbench.items.map(i => i.key)).toEqual(['A1', 'A1V2', 'A2', 'A3'])
    expect(workbench.items.find(i => i.key === 'A1V2').label).toBe('问一问V2')
    expect(PAGE_NAMES.A1V2).toBe('问一问V2')
    expect(PAGE_NAMES.A1V2R).toBeUndefined()
    expect(PROTO_EXCLUDED).toEqual(['A1V2'])
    expect(menuForRole('shixi').find(g => g.group === '工作台').items.map(i => i.key))
      .not.toContain('A1V2R')

    // 文件面：旧页与其测试已删；V1 A1 页与测试原样保留
    expect(Object.keys(LANDING_FILES)).not.toContain('../A1V2.jsx')
    expect(Object.keys(LANDING_FILES)).not.toContain('../A1V2.test.jsx')
    expect(Object.keys(LANDING_FILES)).toContain('../A1.jsx')
    expect(Object.keys(LANDING_FILES)).toContain('../A1.test.jsx')
  })

  it('#/A1V2 → 落地树 page=A1V2（真流页渲染）；旧 #/A1V2R 已无对应页（未点亮占位）', async () => {
    window.history.replaceState(null, '', '/#/A1V2')
    expect(parseHash()).toEqual({ tree: 'landing', page: 'A1V2' })
    const { default: Shell } = await import('../../shell/Shell.jsx')
    render(<Shell />)
    // 真流页端到端：输入区在位且已接线（Enter 发送）
    expect(await screen.findByPlaceholderText(/Enter 发送/)).toBeTruthy()
    cleanup()

    window.history.replaceState(null, '', '/#/A1V2R')
    expect(parseHash()).toEqual({ tree: 'landing', page: 'A1V2R' })
    render(<Shell />)
    expect(await screen.findByText(/A1V2R · 落地页待阶段点亮/)).toBeTruthy()
  })
})
