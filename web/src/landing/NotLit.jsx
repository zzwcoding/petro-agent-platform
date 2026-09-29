/**
 * 落地树未点亮占位（双树共存，P0-06）——hash 直达未落地页时的出路指引：
 * 跳同名原型树页对照（frontend-foundation §4「一键切树」）。
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
