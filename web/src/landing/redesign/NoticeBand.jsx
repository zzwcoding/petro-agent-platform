/**
 * NoticeBand · notice 行渲染（Owner 2026-10-17 串行链条模型下的降级形态）。
 *
 * 旧形态「答案卡顶部一条 notice 带」已废：notice 现在按到达序长在**执行流水线**里，每条
 * 一个**小行**（`NoticeRow`）；A 级另在**系统回答块顶部**留一条紧凑 Alert（`NoticeAlerts`），
 * 让折叠态流水线下也能一眼看到可信度相关告警。
 *
 * 分级只按 `type`（`gates` 实测恒空，不能当判据）：
 * - **A 级**：拒答/失败/截断/域外降级/写档失败——流水线里红/黄小行，回答块顶部 antd Alert；
 * - **B 级**：过程说明（重绑/窗注记/无命中/批准留痕…）——灰折叠小行，默认收起；
 * - **C 级**：回喂面工序腔（决策驳回/同参重放/核验删改…）——默认收起，点开见原文；
 * - **未登记 type**：通用灰条兜底，原文照给（闭世界会增补，不静默丢弃）。
 *
 * Owner 拍板（设计 §6 第 3 条）：content **纯透传后端**——前端不硬编码白话摘要模板，
 * 只做展开/收起与中性标签；白话化归后端 EB5 文案批（research/最佳实践-3a §3.2）。
 * 空态：无 notice ＝ 两处都不渲染。
 */
import { Alert, Collapse } from 'antd'
import { CloseCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { dim } from '../../components/helpIcon.jsx'
import { NOTICE_LEVEL_A, noticeLevel } from './events.js'

/** A 级里按「硬失败」用 error 色（其余 A 级用 warning 色）。 */
const A_ERROR = new Set(['refused', 'run_failed', 'blackbox_write_failed', 'audit_write_failed'])

/** 折叠行（B/C/未登记共用——默认收起，点开见原文）。 */
function foldItem(n, label, key) {
  return {
    key,
    label: <span style={dim}>{label}</span>,
    children: <div style={{ ...dim, whiteSpace: 'pre-wrap' }}>{n.content}</div>
  }
}

/**
 * 流水线内的单条 notice 小行。
 * A 级＝红/黄小行（原文直给）；B/C/未登记＝灰折叠小行（默认收起）。
 * @param n    notice 帧 {type, gates, content}
 * @param seq  行内序号（同型多条不互相顶掉——key 用）
 */
export function NoticeRow({ n, seq = 0 }) {
  const level = noticeLevel(n?.type)
  const key = `${n?.type || 'unknown'}-${seq}`
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
  const label = level === 'B' ? `说明（${n.type}）`
    : level === 'C' ? `系统注记（${n.type}）· 点开看原文`
      : `系统提示（${n?.type || '未登记类型'}）· 点开看原文`
  return (
    <Collapse size="small" style={{ margin: '2px 0' }}
      items={[foldItem(n, label, key)]} />
  )
}

/**
 * 系统回答块顶部的 A 级 Alert 带（仅 A 级——B/C 级只留在流水线里，不重复占位）。
 * @param notices notice 帧数组（本件自行筛 A 级）
 */
export function NoticeAlerts({ notices = [] }) {
  const alerts = notices.filter(n => NOTICE_LEVEL_A.has(n?.type))
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
