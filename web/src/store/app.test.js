/**
 * store/app 单测（P0-06 审查 P2 修复配套）——switchRole 角色切换双写合同：
 * 切角色必须先落 X-Dev-User 身份桩（localStorage，后续请求头随新角色）、
 * 再写 zustand 角色槽（页头/菜单随新角色）——页头显示与数据权限不脱钩。
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'

// node 测试环境无 localStorage——Map 桩替身（client.js getDevUser/setDevUser 的读写缝）
const kv = vi.hoisted(() => {
  const m = new Map()
  return {
    getItem: k => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => { m.set(String(k), String(v)) },
    clear: () => m.clear()
  }
})
vi.stubGlobal('localStorage', kv)

import { DEFAULT_DEV_USER, getDevUser } from '../api/client.js'
import { switchRole, useAppStore } from './app.js'

describe('switchRole 角色切换双写（X-Dev-User 桩 + zustand 角色槽）', () => {
  beforeEach(() => {
    kv.clear()
    useAppStore.setState({ role: DEFAULT_DEV_USER })
  })

  it('切换后角色槽与 X-Dev-User 桩同步指向新角色', () => {
    switchRole('zhuren')
    expect(useAppStore.getState().role).toBe('zhuren')
    expect(getDevUser()).toBe('zhuren')
  })

  it('双写次序合同：先落身份桩再写角色槽（两写都发生，请求头与页头不脱钩）', () => {
    const order = []
    const spy = vi.spyOn(kv, 'setItem').mockImplementation((k, v) => { order.push(`stub:${v}`) })
    const unsubscribe = useAppStore.subscribe(s => order.push(`slot:${s.role}`))
    switchRole('shixi')
    unsubscribe()
    spy.mockRestore()
    expect(order).toEqual(['stub:shixi', 'slot:shixi'])
  })
})
