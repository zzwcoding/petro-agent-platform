/**
 * 落地树未点亮占位（双树共存，P0-06）——hash 直达未落地页时的出路指引：
 * 跳同名原型树页对照（frontend-foundation §4「一键切树」）。
 *
 * 注：locator 桥已退役（P1-11 收口）——`#/B2?chunk=` 的 hash query 由
 * Shell.parseHash 剥离挪到 location.search（replaceState），B2 落地页直读
 * location.search 消费；本组件回归纯「未点亮出路指引」单职责。
 */

import { Button, Result } from 'antd'
import { PAGE_NAMES } from '../roles.js'

/**
 * @param {{pageKey: string}} props
 * @returns {JSX.Element}
 */
export default function NotLit({ pageKey }) {
  return (
    <Result
      status="info"
      title={`${PAGE_NAMES[pageKey] || pageKey} · 落地页待阶段点亮`}
      subTitle="该页真实开发轨版本未到施工阶段（阶段落位见 frontend-foundation §5）；可先看原型树对照 mock 行为。"
      extra={<Button type="primary" onClick={() => { location.hash = `/proto/${pageKey}` }}>去原型树看 #/proto/{pageKey}</Button>}
    />
  )
}
