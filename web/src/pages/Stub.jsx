import { Result } from 'antd'
import { PAGE_NAMES } from '../roles.js'

export default function Stub({ pageKey }) {
  return (
    <Result
      status="404"
      title={`${PAGE_NAMES[pageKey] || pageKey} · V2 施工中`}
      subTitle="该页面的 V2 版本将在后续批次交付，当前为占位页。"
    />
  )
}
