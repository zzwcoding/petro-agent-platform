/**
 * 落地树未点亮占位（双树共存，P0-06）——hash 直达未落地页时的出路指引：
 * 跳同名原型树页对照（frontend-foundation §4「一键切树」）。
 *
 * locator 桥（P1-04）：`#/B2?chunk=<fragment_id>` 形态（B2 册对账 10——B4 证据
 * 弹层「在切片管理中定位」与 A1 引用回跳的 query 定位）。Shell.parseHash 不拆
 * hash query（P1-04 不动 shell/ 纪律），整串落进 pageKey；本桥拆出 query、把
 * chunk 存 sessionStorage 后重定向到裸路由，B2 落地页挂载时消费（滚动＋高亮
 * ＋详情弹窗）。干净收口＝Shell.parseHash 剥 query 直达目标页（一行改动）——
 * 挂差异登记待 Owner 拍板后本桥退役。
 */

import { Button, Result } from 'antd'
import { PAGE_NAMES } from '../roles.js'
import { B2_LOCATOR_KEY, LANDING_LIT } from './registry.js'

/**
 * @param {{pageKey: string}} props
 * @returns {JSX.Element | null}
 */
export default function NotLit({ pageKey }) {
  const qAt = pageKey.indexOf('?')
  if (qAt > 0) {
    const base = pageKey.slice(0, qAt)
    if (LANDING_LIT.includes(base)) {
      const query = new URLSearchParams(pageKey.slice(qAt + 1))
      const chunk = query.get('chunk')
      if (chunk) {
        try { sessionStorage.setItem(B2_LOCATOR_KEY, chunk) } catch { /* 隐私模式静默 */ }
      }
      location.replace(`#/${base}`)
      return null
    }
  }
  return (
    <Result
      status="info"
      title={`${PAGE_NAMES[pageKey] || pageKey} · 落地页待阶段点亮`}
      subTitle="该页真实开发轨版本未到施工阶段（阶段落位见 frontend-foundation §5）；可先看原型树对照 mock 行为。"
      extra={<Button type="primary" onClick={() => { location.hash = `/proto/${pageKey}` }}>去原型树看 #/proto/{pageKey}</Button>}
    />
  )
}
