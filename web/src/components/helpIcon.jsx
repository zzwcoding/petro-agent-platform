/**
 * helpIcon —— 说明收束共享件（UI-00；方案-阶段1交互优化-20261004 §3.3 定死）：
 * 字段解释/口径与规则/操作步骤/演示性说明四类内容的唯一收束形态（「?」图标）。
 * 抽取母本＝B1.jsx:43-50 现形原样（五页同构副本的删除与 import 切换属
 * UI-01…UI-06 各页票任务，本票只落共享件本体）。
 * fieldLabel 不抽——仅 B1 一处消费（方案 §3.3 定死，留 B1）。
 */

import { Tooltip } from 'antd'
import { QuestionCircleOutlined } from '@ant-design/icons'

/**
 * 「?」说明图标：Tooltip 包 QuestionCircleOutlined（placement topLeft、
 * 内容 12px/1.8 行高、图标 4px 左距灰字可悬停——B1.jsx:43-47 同形）。
 * @param {string | any} content Tooltip 内容（string | node；单条 ≤120 字，
 *   确需超长允许多行，但一条 ? 只讲一件事）
 * @returns {JSX.Element}
 */
export const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: 'var(--pa-text-tertiary)', cursor: 'help' }} />
  </Tooltip>
)

/** 弱化说明文字样式（12px 灰字——五页同构常量，母本 B1.jsx:50 同值）。 */
export const dim = { fontSize: 12, color: 'var(--pa-text-tertiary)' }
