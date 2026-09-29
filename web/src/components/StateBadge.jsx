/**
 * StateBadge —— 四态徽标（全局组件库首批，P0-06）。
 *
 * 合同形状来源：frontend-foundation.md §2.4 表「四态徽标（过/拦下/不涉及/未跑）
 * ← C3 合同常量」；C3-发布流水线.md：结果标记四态 过|拦下|不涉及|未跑，
 * 短路语义＝按顺序执行、任一阶段「拦下」即停、后续一律「未跑」。
 *
 * 配色与原型页 C3.jsx RESULT_COLOR 一致（§2.4：原型页与落地页共用，
 * 对比时视觉一致，差异只来自数据真假）。原型页暂不强制改用。
 */

import { Tag } from 'antd'

/** C3 合同四态（冻结值，勿增删——新增状态走 C3 册修合同）。 */
export const RESULT_STATES = /** @type {const} */ (['过', '拦下', '不涉及', '未跑'])

/** 四态 → antd Tag color（与原型 C3 页 RESULT_COLOR 同值）。 */
export const RESULT_COLORS = { 过: 'green', 拦下: 'red', 不涉及: 'default', 未跑: 'default' }

/**
 * 四态徽标。
 * @param {{state: string, title?: string}} props state∈RESULT_STATES；title 悬浮说明
 *   （如短路原因「前面拦下短路不查」）
 * @returns {JSX.Element}
 */
export default function StateBadge({ state, title }) {
  return (
    <Tag color={RESULT_COLORS[state] || 'default'} title={title}>{state}</Tag>
  )
}
