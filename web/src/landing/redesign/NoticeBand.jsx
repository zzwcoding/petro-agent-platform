/**
 * NoticeBand · notice 行渲染（Owner 2026-10-17 串行链条模型下的降级形态）。
 *
 * 旧形态「答案卡顶部一条 notice 带」已废：notice 现在按到达序长在**执行流水线**里，每条
 * 一个**小行**（`NoticeRow`）；A 级另在**系统回答块顶部**留一条紧凑 Alert（`NoticeAlerts`），
 * 让折叠态流水线下也能一眼看到可信度相关告警。
 *
 * 分级只按 `type`（`gates` 实测恒空，不能当判据）：
 * - **A 级**：拒答/失败/截断/域外降级/写档失败——流水线里红/黄**彩条小行**（样式不动）；
 * - **B/C 级与未登记 type**：**灰纯文本紧凑行**（打磨批⑥：原 antd Collapse 边框盒退场）——
 *   标签「⚙ 系统注记（type）· 点开看原文」，点击在该行下**内联**原文，再点收起（自管理 useState）；
 * - **隐藏型**（`NOTICE_LEVEL_HIDE`——material_truncated/emission_strip，打磨批⑧）：两处都不出，
 *   展示口径而已，`turn.notices` 原数据不动。
 *
 * Owner 拍板（设计 §6 第 3 条）：content **纯透传后端**——前端不硬编码白话摘要模板，
 * 只做展开/收起与中性标签；白话化归后端 EB5 文案批（research/最佳实践-3a §3.2）。
 * 空态：无可见 notice ＝ 两处都不渲染。
 */
import { useState } from 'react'
import { Alert } from 'antd'
import { CloseCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { dim } from '../../components/helpIcon.jsx'
import { NOTICE_LEVEL_A, noticeLevel, noticeVisible } from './events.js'

/** A 级里按「硬失败」用 error 色（其余 A 级用 warning 色）。 */
const A_ERROR = new Set(['refused', 'run_failed', 'blackbox_write_failed', 'audit_write_failed'])

/**
 * 流水线内的单条 notice 小行。
 * A 级＝红/黄彩条小行（原文直给）；B/C/未登记＝灰纯文本行（点开内联原文、再点收起）。
 * @param n  notice 帧 {type, gates, content}
 */
export function NoticeRow({ n }) {
  const [plainOpen, setPlainOpen] = useState(false)
  const level = noticeLevel(n?.type)
  if (level === 'A') {
    const color = A_ERROR.has(n.type) ? '#ff7875' : '#e8b339'
    return (
      <div data-testid="notice-row-a" style={{
        display: 'flex', gap: 6, alignItems: 'flex-start', fontSize: 12, lineHeight: 1.7,
        padding: '3px 8px', margin: '2px 0', borderRadius: 4,
        background: A_ERROR.has(n.type) ? 'rgba(255,120,117,0.12)' : 'rgba(232,179,57,0.14)',
        borderLeft: `3px solid ${color}`
      }}>
        {A_ERROR.has(n.type)
          ? <CloseCircleOutlined style={{ color, marginTop: 3 }} />
          : <ExclamationCircleOutlined style={{ color, marginTop: 3 }} />}
        <span>{n.content}</span>
      </div>
    )
  }
  // B/C/未登记＝灰纯文本行（无边框盒；点击内联原文，再点收起）
  return (
    <div data-testid="notice-row-plain" style={{ fontSize: 12, lineHeight: 1.8 }}>
      <span role="button" tabIndex={0} aria-expanded={plainOpen} style={{ ...dim, cursor: 'pointer' }}
        onClick={() => setPlainOpen(o => !o)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setPlainOpen(o => !o) }}>
        {`⚙ 系统注记（${n?.type || '未登记类型'}）· 点开看原文`}
      </span>
      {plainOpen && (
        <div data-testid="notice-plain-body" style={{ ...dim, whiteSpace: 'pre-wrap', paddingLeft: 12 }}>
          {n?.content}
        </div>
      )}
    </div>
  )
}

/**
 * 系统回答块顶部的 A 级 Alert 带（仅 A 级——B/C 级只留在流水线里，不重复占位；
 * 隐藏型滤掉——打磨批⑧）。
 * @param notices notice 帧数组（本件自行筛 A 级＋非隐藏型）
 */
export function NoticeAlerts({ notices = [] }) {
  const alerts = notices.filter(n => NOTICE_LEVEL_A.has(n?.type) && noticeVisible(n))
  if (alerts.length === 0) return null
  return (
    <div data-testid="notice-alerts">
      {alerts.map((n, i) => (
        <Alert key={`${n.type}-${i}`} showIcon
          type={A_ERROR.has(n.type) ? 'error' : 'warning'}
          message={<span style={{ fontSize: 12 }}>{n.content}</span>}
          style={{ margin: '6px 0', padding: '3px 10px' }} />
      ))}
    </div>
  )
}
