/**
 * ExecutionPipeline · 系统执行流水线块（Owner 2026-10-17 串行链条模型的中段）。
 *
 * 形态：一个可折叠容器——**展开态＝typed 事件流**，事件按到达序**向下追加**，每种类型
 * 有自己的行渲染器（图标＋白话文案＋状态）；**折叠态＝一行摘要**（状态词 · 步数 · 工具数 ·
 * 材料数 · ⚠提示数 · 本地计时）。
 *
 * 状态机（渲染期 `phaseOf(turn)` 派生驱动——FE-01 导出，turn 不携带 phase 字段）：
 * - `running`：**默认展开**（流在长），尾部一颗 Spin「继续处理中…」；无事件时出「正在分析问题…」占位；
 * - `answering`：**自动收起**（首条答案正文到达＝流水线让位给正文）；
 * - `done`：链条完整，默认收起，点摘要行可再展开回看全程。
 * 用户点过摘要行后以用户态为准（`userOpen ?? 默认`）——手动展开的运行中回合不会被强收。
 *
 * 行渲染映射（白话；映射表在 events.js，未登记值原样回显）：
 * - understanding → 💭「理解为：…」
 * - step 段 → 相位白话（分析问题/检索资料/取数/查看材料/核验/作答）＋原标题小字；
 *   连续同（相位＋标题）的步折叠成一行并挂「×N」（真机实录「分析问题 · 模型调用：decision」连出 3-4 条）
 * - tool → 缩进行「查文档库/查指标台账/取数/查常见问题/查表结构」＋状态 ok✓/failed✗/ask⏸
 * - materials 段 → 聚合行「📄 检索到材料 51 份」（多次子检索＝「… 32 · 36 份（2 次子检索）」；
 *   明细在右栏，不进流水线）
 * - notice → 小行（NoticeRow：A 红/黄彩条、B/C/未登记＝灰纯文本行「⚙ 系统注记（type）· 点开看原文」）；
 *   隐藏型（material_truncated/emission_strip——打磨批⑧）整行不出
 * - verify → 「✅ 核验完成：有据 N 条 · 改写 M 条（· 分列 K 条）」
 * - citation 段 → 轻行「🔖 落账引标 N 条 · 来自 M 处来源」（M＝去重来源数；不跨别的事件类型）
 * supplement 不单独出行（血缘卡是回答块下挂的链条节点）。
 *
 * 事件流＝归约器直出的 `turn.events`（按帧到达序追加，G4——本件不排序不派生；显示折叠
 * `foldEvents` 只并连续段，不改序）；FE-02 起 deriveEvents 退役，各轮（真流/夹具/历史）皆为
 * reducer/historyAdapter 产出、events 恒为数组，过渡期 `?? []` 兜底按票面判定去除）。
 * 时长 `durationS` 由页面传入（本地计时，不入 turn）。
 * 空态：非运行中且无事件＝整块不渲染（旧版降级轮即此形）。
 */
import { useState } from 'react'
import { Spin } from 'antd'
import {
  CheckCircleOutlined, CloseCircleOutlined, DownOutlined, PauseCircleOutlined, UpOutlined
} from '@ant-design/icons'
import { dim, helpIcon } from '../../components/helpIcon.jsx'
import { NoticeRow } from './NoticeBand.jsx'
import { foldEvents, phaseText, summarizePipeline, toolText, noticeVisible } from './events.js'

const TOOL_STATUS = { ok: '完成', failed: '失败', ask: '待确认' }

/** 工具状态图标（ok✓ / failed✗ / ask⏸；未登记＝原样文字）。 */
function ToolStatus({ status }) {
  if (status === 'failed') return <CloseCircleOutlined style={{ color: 'var(--pa-danger)', marginLeft: 6 }} />
  if (status === 'ask') return <PauseCircleOutlined style={{ color: 'var(--pa-warning)', marginLeft: 6 }} />
  if (status === 'ok') return <CheckCircleOutlined style={{ color: 'var(--pa-success)', marginLeft: 6 }} />
  return null
}

function Row({ testid, children }) {
  return <div data-testid={testid} style={{ fontSize: 12, lineHeight: 1.8, marginBottom: 2 }}>{children}</div>
}

/** 单条显示项 → 行（项形状＝foldEvents 产出）。 */
function EventRow({ item, i }) {
  const ev = item.ev
  switch (item.type) {
    case 'understanding':
      return (
        <Row testid="ev-understanding">
          <span style={dim}>💭 理解为：</span>
          <span style={{ whiteSpace: 'pre-wrap' }}>{String(ev.text).replace(/^理解：/, '')}</span>
        </Row>
      )
    case 'steps':
      return (
        <Row testid={`ev-step-${item.seq}`}>
          <b>{phaseText(item.phase)}</b>
          {item.title && <span style={dim}>{` · ${item.title}`}</span>}
          {item.count > 1 && <span style={dim}>{` ×${item.count}`}</span>}
        </Row>
      )
    case 'tool':
      return (
        <Row testid={`ev-tool-${ev.seq}`}>
          <span style={{ paddingLeft: 14 }}>
            {`└ ${toolText(ev.tool)}`}
            <ToolStatus status={ev.status} />
            {ev.status && <span style={dim}>{` · ${TOOL_STATUS[ev.status] ?? ev.status}`}</span>}
            {ev.message && <span style={dim}>{`（${ev.message}）`}</span>}
          </span>
        </Row>
      )
    case 'materials':
      return (
        <Row testid="ev-materials">
          {`📄 检索到材料 ${item.counts.join(' · ')} 份`}
          {item.counts.length > 1 && <span style={dim}>{`（${item.counts.length} 次子检索）`}</span>}
          <span style={dim}>（材料明细在右侧「引用与口径」）</span>
        </Row>
      )
    case 'notice':
      return <div data-testid={`ev-notice-${i}`}><NoticeRow n={ev.notice} /></div>
    case 'verify':
      return (
        <Row testid="ev-verify">
          {`✅ 核验完成：有据 ${ev.verdict?.supported ?? 0} 条 · 改写 ${ev.verdict?.rewritten ?? 0} 条`
            + ((ev.verdict?.split ?? 0) > 0 ? ` · 分列 ${ev.verdict.split} 条` : '')}
        </Row>
      )
    case 'citations':
      return (
        <Row testid="ev-citations">
          <span style={dim}>{`🔖 落账引标 ${item.count} 条 · 来自 ${item.sources.length} 处来源`}</span>
        </Row>
      )
    default: // 未登记事件类型＝原样兜底（不静默丢）
      return <Row testid={`ev-unknown-${i}`}>{JSON.stringify(ev)}</Row>
  }
}

/**
 * @param turn      单轮（TurnShape——events 为归约器直出的到达序事件流）
 * @param durationS 本地计时秒数（页面临时面传入，不入 turn；null＝摘要行不出时长）
 */
export default function ExecutionPipeline({ turn, durationS = null }) {
  const events = turn.events
  const sum = summarizePipeline(turn)
  const [userOpen, setUserOpen] = useState(null) // null＝跟随状态机；true/false＝用户定态
  const running = sum.state === 'running'
  const open = userOpen ?? running // running 默认展开；answering/done 默认收起

  // 空态：非运行中且无事件＝整块不渲染（旧版降级轮即此形——不伪造流水线）
  if (events.length === 0 && !running) return null

  // 显示项＝到达序折叠后的连续段，再滤掉隐藏型 notice 行（打磨批⑧——展示口径，原数据不动）
  const items = foldEvents(events).filter(it => it.type !== 'notice' || noticeVisible(it.ev?.notice))

  const stateIcon = running ? <Spin size="small" /> : <CheckCircleOutlined style={{ color: 'var(--pa-success)' }} />
  const shownDuration = durationS ?? sum.durationS // 页面传入优先（时长不入 turn——页面临时面）
  const summary = [
    sum.stateWord,
    `${sum.steps} 步`,
    `${sum.tools} 次工具`,
    `${sum.materials} 份材料`,
    `⚠ ${sum.notices} 条提示`,
    shownDuration == null ? null : `${shownDuration}s`
  ].filter(Boolean)

  return (
    <div style={{ borderRadius: 6, marginBottom: 8, background: 'rgba(127,127,127,0.05)' }}
      data-testid="pipeline">
      <div
        role="button" tabIndex={0} aria-expanded={open} data-testid="pipeline-bar"
        onClick={() => setUserOpen(!open)}
        onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setUserOpen(!open) }}
        style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', cursor: 'pointer', fontSize: 12 }}>
        {stateIcon}
        <span>{summary.join(' · ')}</span>
        {helpIcon((
          <>
            这是系统的执行过程：每一步（分析问题→检索资料→取数→查看材料→核验→作答）与每次工具调用
            都按发生的先后往下长。材料明细在右侧「引用与口径」，这里只记总数。
            <br />
            时长是本地计时（后端不提供耗时字段）——只作参考，不是权威耗时。
          </>
        ))}
        <span style={{ marginLeft: 'auto', ...dim }}>
          {open ? <>收起过程 <UpOutlined style={{ fontSize: 12 }} /></> : <>展开过程 <DownOutlined style={{ fontSize: 12 }} /></>}
        </span>
      </div>

      {open && (
        <div style={{ padding: '4px 10px 6px' }} data-testid="pipeline-body">
          {events.length === 0
            ? <div style={dim} data-testid="pipeline-waiting"><Spin size="small" /> 正在分析问题…</div>
            : items.map((it, i) => <EventRow key={`${it.type}-${it.seq ?? i}`} item={it} i={i} />)}
          {running && events.length > 0 && (
            <div style={{ ...dim, marginTop: 4 }} data-testid="pipeline-tail">
              <Spin size="small" /> 继续处理中…
            </div>
          )}
        </div>
      )}
    </div>
  )
}
