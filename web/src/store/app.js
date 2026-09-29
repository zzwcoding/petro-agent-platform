/**
 * 全局轻量状态（底座五件之三，P0-06）——zustand，新增唯一前端状态依赖。
 *
 * 设计真源：teach-petro-agent/specs/frontend-foundation.md §2.3：
 * 三槽起步——①当前角色（接 roles.js 唯一真源）；②语义层当前版本徽标
 * （semantic.current，D3 页头策略徽标同源）；③会话列表缓存（A1 预留）。
 * 页面内状态维持 useState 不动（存量 303 处不迁移）。
 *
 * 消费方式：`const role = useAppStore(s => s.role)`（zustand 选择器订阅，
 * 避免整 store 重渲染）。
 */

import { create } from 'zustand'
import { DEFAULT_DEV_USER, setDevUser } from '../api/client.js'

/**
 * @typedef {object} AppState
 * @property {string} role 当前角色 key（roles.js 五角色；默认阿强·平台运维——
 *   与后端身份桩默认一致，过设置中心组闸）
 * @property {(role: string) => void} setRole
 * @property {string | null} semanticVersion 语义层当前版本徽标（semantic.current；
 *   D3 页头策略徽标同源。P0-06 占位 null——C3 发布流水线落地批接线赋值）
 * @property {(v: string | null) => void} setSemanticVersion
 * @property {Array<{session_id: string, title: string}>} sessions 会话列表缓存
 *   （A1 会话域预留；P0-06 恒空数组——阶段 1 A1 落地批接线）
 * @property {(sessions: Array<{session_id: string, title: string}>) => void} setSessions
 */

export const useAppStore = /** @type {any} */ (create)(/** @param {any} set */ set => ({
  role: DEFAULT_DEV_USER,
  setRole: role => { set({ role }) },

  semanticVersion: null,
  setSemanticVersion: semanticVersion => { set({ semanticVersion }) },

  sessions: [],
  setSessions: sessions => { set({ sessions }) }
}))

/**
 * 角色切换唯一入口（Shell 页头角色下拉 onChange）：双写——
 * ①先落 X-Dev-User 身份桩（localStorage；后续请求头随新角色，client.js authHeaders 读此）；
 * ②再写 zustand 角色槽（页头显示/侧菜单随新角色）。
 * 次序不可换、两写不可缺：只写槽不写桩 → 页头已是新角色、数据权限仍带旧身份
 * （页头与数据权限脱钩，P0-06 审查 P2 修复；setDevUser 全仓原先零调用点）。
 * @param {string} roleKey roles.js 五角色 key（laowang/xiaoli/zhuren/aqiang/shixi）
 */
export function switchRole(roleKey) {
  setDevUser(roleKey)
  useAppStore.getState().setRole(roleKey)
}
