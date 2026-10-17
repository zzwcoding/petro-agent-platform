/**
 * NoticeBand · notice 三级带（设计稿 §3.6 ＋ 调研 §3 分级表）。
 *
 * 分级只按 `type`（`gates` 实测恒空，不能当判据）：
 * - **A 级（醒目）**：antd Alert——拒答/失败/截断/域外降级/写档失败这类影响答案可信的事。
 * - **B 级（灰）**：灰折叠条——过程说明（重绑/窗注记/无命中/批准留痕…），默认收起。
 * - **C 级（回喂面）**：默认收起，点开见原文——工序腔（决策驳回/同参重放/核验删改…）。
 * - **未知 type**：通用灰条兜底，**不静默丢弃**（闭世界会增补）。
 *
 * Owner 拍板（设计 §6 第 3 条）：content **纯透传后端**，前端不硬编码白话摘要模板——
 * 故 C 级不再出「核验时删去了 N 条没有依据的说法」类前端自造文案，只做展开/收起与
 * 中性标签；白话化归后端 EB5 文案批（`docs/runtime-refactor/research/最佳实践-3a-白话化与受众适配.md` §3.2）。
 * 空态：无 notice＝整带不渲染。
 */
import { Alert, Collapse } from 'antd'
import { dim } from '../../components/helpIcon.jsx'

/** A 级：醒目告警（Alert）。 */
export const NOTICE_LEVEL_A = new Set([
  'refused', 'run_failed', 'freshness_block', 'unbound_degrade', 'schema_not_allowed',
  'material_truncated', 'emission_strip', 'blackbox_write_failed', 'audit_write_failed'
])

/** B 级：灰折叠条（过程说明）。 */
export const NOTICE_LEVEL_B = new Set([
  'rebind', 'window_note', 'no_hit', 'approval_recorded', 'ban_exempt',
  'clarify_capped', 'budget_converged', 'window_miss_reentry'
])

/** C 级：默认收起（工序腔——点开见原文）。 */
export const NOTICE_LEVEL_C = new Set([
  'decision_rejected', 'same_param_replay', 'emission_quote_repair', 'decision_note',
  'chain_switch_reentry', 'subtask_failed', 'subtask_refused', 'tool_unavailable',
  'unsupported_claim', 'contradiction_split', 'attribution_split'
])

/** A 级里按「硬失败」用 error 色（其余 A 级用 warning 色）。 */
const A_ERROR = new Set(['refused', 'run_failed', 'blackbox_write_failed', 'audit_write_failed'])

/** 单条 notice → 级别（未登记 type＝'unknown'，走通用灰条）。 */
export function noticeLevel(type) {
  if (NOTICE_LEVEL_A.has(type)) return 'A'
  if (NOTICE_LEVEL_B.has(type)) return 'B'
  if (NOTICE_LEVEL_C.has(type)) return 'C'
  return 'unknown'
}

function foldItem(n, label, key) {
  return {
    key,
    label: <span style={dim}>{label}</span>,
    children: <div style={{ ...dim, whiteSpace: 'pre-wrap' }}>{n.content}</div>
  }
}

function NoticeRow({ n, i }) {
  const level = noticeLevel(n.type)
  if (level === 'A') {
    return (
      <Alert type={A_ERROR.has(n.type) ? 'error' : 'warning'} showIcon message={n.content}
        style={{ margin: '6px 0' }} />
    )
  }
  const key = `${n.type || 'unknown'}-${i}`
  if (level === 'B') {
    return (
      <Collapse size="small" style={{ margin: '6px 0', background: 'rgba(127,127,127,0.06)' }}
        items={[foldItem(n, `说明（${n.type}）`, key)]} />
    )
  }
  if (level === 'C') {
    return (
      <Collapse size="small" style={{ margin: '6px 0' }}
        items={[foldItem(n, `系统注记（${n.type}）· 点开看原文`, key)]} />
    )
  }
  // 未知 type：通用灰条（不静默丢弃——原文照给，标签点明未登记）
  return (
    <Collapse size="small" style={{ margin: '6px 0', background: 'rgba(127,127,127,0.06)' }}
      items={[foldItem(n, `系统提示（${n.type || '未登记类型'}）· 点开看原文`, key)]} />
  )
}

/**
 * @param notices 归约器 notice 数组 [{type, gates, content}]（顺序＝到达序）
 */
export default function NoticeBand({ notices = [] }) {
  if (notices.length === 0) return null
  return (
    <div data-testid="notice-band">
      {notices.map((n, i) => <NoticeRow key={`${n.type || 'n'}-${i}`} n={n} i={i} />)}
    </div>
  )
}
