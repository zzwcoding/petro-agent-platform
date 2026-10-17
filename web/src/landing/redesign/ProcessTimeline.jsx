/**
 * ProcessTimeline · 过程折叠条（设计稿 §3.1——重设计核心件）。
 *
 * 形态（Wekenora 同形）：折叠态一行摘要「🔍 检索完成 · 引用了 N 篇文档 · 11 步 · 2 次工具 ·
 * 38s ▾」；展开态 antd Timeline 树状——步＝白话标题（相位映射）＋状态图标（ok✓/failed✗/
 * 进行中 Spin），工具挂到同 `data.seq` 的步下（工具名白话映射），**C 级 notice 收进对应步下**
 * （调研 §3 的 C 级＝工序腔原文，默认收起在展开面内）。
 *
 * 纪律与如实标注：
 * - 引用数＝**去重来源数**（cites.citeSourceCount——切片数不是篇数）。
 * - 无引用（N=0）时退「N 步 · M 次工具」（调研 §5 空态栏）。
 * - 时长**只能本地计时**（后端无耗时字段）——摘要里带「?」注解明说，不冒充权威耗时。
 * - 相位/工具白话映射未登记值＝原样回显（闭世界会增补，不静默丢）。
 * - 步状态：live 帧无 status 键（历史接口才有）——本件按「该步挂的工具有则取工具 status，
 *   无工具＝过程注记按 ok，进行中回合的最后一步＝running」的显示口径推导（接归约器时若
 *   step 带 status 应改直读，见 DEBT）。
 * - 空态：无步无工具（且非加载中）＝整行不渲染。
 *
 * DEBT(docs/runtime-refactor/frontend-redesign-设计.md)：步状态推导与 notice→步 挂靠属 mock
 * 期显示口径，接归约器（施工顺序第 2 步）后应改为直读帧字段。
 */
import { useState } from 'react'
import { Spin, Timeline } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined, DownOutlined, SearchOutlined, UpOutlined } from '@ant-design/icons'
import { dim, helpIcon } from '../../components/helpIcon.jsx'
import { citeSourceCount } from './cites.js'

/** 六相位 → 白话（设计稿 §3.1 映射表；未登记相位原样回显）。 */
export const PHASE_TEXT = {
  decision: '分析问题',
  discover: '检索资料',
  execute: '取数',
  observe: '查看材料',
  verify: '核验',
  answer: '作答'
}

/** 工具名 → 白话（设计稿 §3.1 映射表；未登记工具原样回显）。 */
export const TOOL_TEXT = {
  doc_retrieve: '查文档库',
  semantic_query: '查指标台账',
  data_query: '取数',
  faq_lookup: '查常见问题',
  table_schema: '查表结构'
}

/** C 级 notice type → 归属相位（收进对应步下；未登记＝挂最后一步，不丢）。 */
const NOTICE_PHASE = {
  decision_rejected: 'decision',
  same_param_replay: 'decision',
  decision_note: 'decision',
  chain_switch_reentry: 'decision',
  tool_unavailable: 'execute',
  subtask_failed: 'execute',
  subtask_refused: 'execute',
  unsupported_claim: 'verify',
  contradiction_split: 'verify',
  attribution_split: 'verify',
  emission_quote_repair: 'verify'
}

/** 末步后的兜底：无相位匹配的 notice 挂最后一步（无步＝整行不出）。 */
function attachNotices(steps, notices) {
  const C = (notices || []).filter(n => NOTICE_PHASE[n?.type])
  return steps.map((s, i) => {
    const mine = C.filter(n => NOTICE_PHASE[n.type] === s.station)
    const last = i === steps.length - 1
    const orphan = last ? C.filter(n => !steps.some(x => x.station === NOTICE_PHASE[n.type])) : []
    return { ...s, stepNotices: [...mine, ...orphan] }
  })
}

/** 单步状态：有工具＝取工具 status；进行中末步＝running；其余＝ok（显示口径，见头注）。 */
function stepStatus(s, tool, running, isLast) {
  if (tool) return tool.status || 'ok'
  if (running && isLast) return 'running'
  return 'ok'
}

function StatusIcon({ status }) {
  if (status === 'running') return <Spin size="small" style={{ marginLeft: 6 }} />
  if (status === 'failed') return <CloseCircleOutlined style={{ color: '#ff7875', marginLeft: 6 }} />
  return <CheckCircleOutlined style={{ color: '#52c41a', marginLeft: 6 }} />
}

/**
 * @param steps      归约器步数组 [{seq, station, title}]（保到达序；本件按 seq 升序展示）
 * @param tools      工具数组 [{seq, tool, status, message}]（挂到同 seq 步下）
 * @param notices    notice 数组（只取 C 级收进步下；A/B 级由 NoticeBand 出，本件不重复）
 * @param citations  引用数组（只用来算去重来源数）
 * @param running    回合进行中（无步时出「正在分析问题…」占位）
 * @param durationS  本地计时秒数（null＝不显示，不猜）
 */
export default function ProcessTimeline({
  steps = [], tools = [], notices = [], citations = [], running = false, durationS = null
}) {
  const [open, setOpen] = useState(false)
  const ordered = [...steps].sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0))
  const loading = running && ordered.length === 0

  // 空态：无步无工具且非加载中＝整行不渲染（空态纪律——无数据不渲染该位）
  if (!loading && ordered.length === 0 && tools.length === 0) return null

  const toolBySeq = new Map(tools.map(t => [t.seq, t]))
  const nSources = citeSourceCount(citations)
  const summary = [
    running ? '检索中' : '检索完成',
    nSources > 0 ? `引用了 ${nSources} 篇文档` : null,
    `${ordered.length} 步`,
    `${tools.length} 次工具`,
    durationS == null ? null : `${durationS}s`
  ].filter(Boolean)

  return (
    <div style={{ border: '1px solid #e0e4e8', borderRadius: 6, marginBottom: 8, background: 'rgba(127,127,127,0.06)' }}>
      <div
        role="button" tabIndex={0} aria-expanded={open} data-testid="process-timeline-bar"
        onClick={() => { if (!loading) setOpen(o => !o) }}
        onKeyDown={e => { if (!loading && (e.key === 'Enter' || e.key === ' ')) setOpen(o => !o) }}
        style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', cursor: loading ? 'default' : 'pointer', fontSize: 12 }}>
        {loading ? (
          <>
            <Spin size="small" />
            <span style={dim}>正在分析问题…</span>
          </>
        ) : (
          <>
            <SearchOutlined style={{ color: '#8a94a3' }} />
            <span>{summary.join(' · ')}</span>
            {helpIcon((
              <>
                「篇数」＝检索到的候选文档篇数（同一份文档的多支切片按 1 篇计）。
                <br />
                时长是本地计时（后端不提供耗时字段）——只作参考，不是权威耗时。
              </>
            ))}
            <span style={{ marginLeft: 'auto', ...dim }}>
              {open ? <>收起 <UpOutlined style={{ fontSize: 10 }} /></> : <>展开过程 <DownOutlined style={{ fontSize: 10 }} /></>}
            </span>
          </>
        )}
      </div>

      {open && !loading && (
        <div style={{ padding: '4px 10px 2px' }} data-testid="process-timeline-body">
          <Timeline
            items={attachNotices(ordered, notices).map((s, i) => {
              const tool = toolBySeq.get(s.seq)
              const status = stepStatus(s, tool, running, i === ordered.length - 1)
              return {
                key: `${s.seq}-${i}`,
                color: status === 'failed' ? 'red' : status === 'running' ? 'blue' : 'green',
                children: (
                  <div style={{ fontSize: 12 }}>
                    <div>
                      <b>{PHASE_TEXT[s.station] ?? s.station}</b><StatusIcon status={status} />
                      {(s.title || '') && <span style={dim}>{` · ${s.title}`}</span>}
                    </div>
                    {tool && (
                      <div style={{ ...dim, paddingLeft: 12 }}>
                        {`└ ${TOOL_TEXT[tool.tool] ?? tool.tool}：${tool.status === 'failed' ? '失败' : tool.status === 'ok' ? '完成' : tool.status}`}
                        {tool.message ? `（${tool.message}）` : ''}
                      </div>
                    )}
                    {s.stepNotices.map((n, k) => (
                      <div key={k} style={{ ...dim, paddingLeft: 12, marginTop: 2 }}>{`系统注记（${n.type}）：${n.content}`}</div>
                    ))}
                  </div>
                )
              }
            })} />
        </div>
      )}
    </div>
  )
}
