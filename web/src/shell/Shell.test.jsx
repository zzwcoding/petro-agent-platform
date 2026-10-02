/**
 * Shell 回归单测（P1-11 locator 桥收口）——parseHash 的 hash query 剥离语义：
 * `#/B2?chunk=x` → 裸 pageKey + query 挪真 location.search（replaceState 无刷
 * 新，B2 直读消费）；裸 hash/proto 树零扰动。NotLit 回归纯出路指引（桥退役
 * 后不再触碰 sessionStorage/query）。
 */

/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import NotLit from '../landing/NotLit.jsx'
import { parseHash } from './Shell.jsx'

function url(path) {
  window.history.replaceState(null, '', path)
}

describe('Shell.parseHash · hash query 剥离（P1-11 桥退役收口）', () => {
  beforeEach(() => {
    url('/')
  })

  afterEach(() => {
    cleanup()
  })

  it('#/B2?chunk=f3 → page=B2 裸键；query 挪 location.search、hash 清裸', () => {
    url('/#/B2?chunk=f3')
    expect(parseHash()).toEqual({ tree: 'landing', page: 'B2' })
    expect(window.location.search).toBe('?chunk=f3')
    expect(window.location.hash).toBe('#/B2')
  })

  it('裸 hash 零扰动；空 hash 落默认页', () => {
    url('/#/D1')
    expect(parseHash()).toEqual({ tree: 'landing', page: 'D1' })
    expect(window.location.search).toBe('')
    expect(window.location.hash).toBe('#/D1')

    url('/')
    expect(parseHash().page).toBeTruthy() // DEFAULT_LANDING_KEY（registry 单源）
    expect(window.location.search).toBe('')
  })

  it('proto 树带 query 同样剥离，树与页键不受扰动', () => {
    url('/#/proto/B2?chunk=f3')
    expect(parseHash()).toEqual({ tree: 'proto', page: 'B2' })
    expect(window.location.search).toBe('?chunk=f3')
    expect(window.location.hash).toBe('#/proto/B2')
  })

  it('hashchange 导航态随剥后的裸 hash 更新（Shell 挂载冒烟）', async () => {
    const { default: Shell } = await import('./Shell.jsx')
    url('/#/B2?chunk=f3')
    render(<Shell />)
    expect(window.location.search).toBe('?chunk=f3')
    expect(window.location.hash).toBe('#/B2')
    fireEvent(window, new Event('hashchange'))
  })
})

describe('NotLit · 桥退役后纯出路指引', () => {
  it('未点亮页渲染指引；不触碰 sessionStorage/location.search', () => {
    url('/#/C1')
    render(<NotLit pageKey="C1" />)
    expect(screen.getByText(/落地页待阶段点亮/)).toBeTruthy()
    expect(window.location.search).toBe('')
    expect(sessionStorage.getItem('petro.b2.locator.chunk')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /去原型树看/ }))
    expect(window.location.hash).toBe('#/proto/C1')
  })
})
