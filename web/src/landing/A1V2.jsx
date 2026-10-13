/**
 * 落地树 · A1V2 问一问V2（对接 V2 后端 /api/v2/*——specs/agent-loop.md 三端点）。
 *
 * 与问一问V1（landing/A1.jsx）同壳不同芯：双列＋回合流一致；过程面换 V2 事件
 * （步骤时间线/工具行/材料卡/引用角标/notice 三级/挂起卡）。V1 端点专属面不设——
 * DEBT(V2-00)：会话历史/@资产/逐帧回放（V1 端点 2/4/6）不在 V2 合同内，随 V2
 * 会话面票补。挂起判定铁律：ask 帧在场＝等人工（挂起腿 done 只收束本腿流）。
 */
import { useEffect, useRef, useState } from 'react'
import {
  Alert, Button, Card, Collapse, Drawer, Input, Modal, Space, Spin, Tag
} from 'antd'
import { ApartmentOutlined, SendOutlined } from '@ant-design/icons'
import { ApiError, errText } from '../api/client.js'
import { listRunsV2, postAskV2, postResumeV2, resumeBodyFromAskFrame } from '../api/chatV2.js'
// UI-00 共享件——helpIcon/dim 唯一定义点
import { helpIcon, dim } from '../components/helpIcon.jsx'
// 决策树（V2 主链版——pages/DecisionTreeV2；场景 kw 词面匹配同构 V1）
import DecisionTreeV2, { V2_SCENARIOS } from '../pages/DecisionTreeV2.jsx'
import { newTurnV2, reduceV2Frame } from './a1v2Reducer.js'

const TREE_BY_KEY = Object.fromEntries(V2_SCENARIOS.map(s => [s.key, s]))
function routeOf(text) {
  const t = (text || '').toLowerCase()
  let best = null, bestPri = Infinity
  for (const s of V2_SCENARIOS) {
    if (!s.kw.some(k => t.includes(k.toLowerCase()))) continue
    if (s.pri < bestPri) { best = s; bestPri = s.pri }
  }
  return best ? best.key : null
}

// notice 三级（对接包约定）：refused＝显式 Alert；window_note/no_hit/material_truncated
// ＝折叠弱化；其余（核验/预算/归属等机读分型）＝灰条。
const NOTICE_ALERT = new Set(['refused', 'budget_converged'])
const NOTICE_FOLD = new Set(['window_note', 'no_hit', 'material_truncated'])
function NoticeRow({ n }) {
  if (NOTICE_ALERT.has(n.type)) {
    return <Alert type="warning" showIcon message={n.content}
      style={{ margin: '6px 0' }} />
  }
  if (NOTICE_FOLD.has(n.type)) {
    return (
      <Collapse size="small" style={{ margin: '6px 0' }} items={[{
        key: n.type,
        label: <span style={dim}>{`说明（${n.type}）`}</span>,
        children: <div style={dim}>{n.content}</div>
      }]} />
    )
  }
  return <div style={{ ...dim, margin: '4px 0' }}>{n.content}</div>
}

/** 挂起卡：澄清（选项点选）／审批（批准·驳回）。resume 回流同回合续写。 */
function AskCard({ frame, busy, onChoose }) {
  const isApproval = frame.kind === 'external_table_approval'
  return (
    <Card size="small" style={{ margin: '8px 0', borderColor: '#4a9dff' }} title={(
      <span>{isApproval ? '越集审批' : '系统反问'}{helpIcon(isApproval
        ? '子问题取数计划引用了平台外的数据表——批准后该表进白名单，不重排计划'
        : '系统需要你确认口径或补充信息后才能继续')}</span>
    )}>
      <div style={{ marginBottom: 8 }}>{frame.prompt}</div>
      {isApproval && frame.detail?.tables && (
        <div style={dim}>外部表：{frame.detail.tables.join('、')}</div>
      )}
      <Space wrap>
        {(frame.options || []).map(op => (
          <Button key={op} size="small" type="primary" ghost disabled={busy}
            onClick={() => onChoose(op)}>{op}</Button>
        ))}
      </Space>
    </Card>
  )
}

export default function A1V2Landing() {
  const [items, setItems] = useState([]) // {role:'user'|'assistant', text?, turn?}
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [treeOpen, setTreeOpen] = useState(false)
  const [active, setActive] = useState(null)
  const [citeTurn, setCiteTurn] = useState(null) // 引用抽屉当前回合
  const [runs, setRuns] = useState([]) // 最近任务（V2-73 会话历史读口）
  const [expandedRun, setExpandedRun] = useState(null)
  const [followupRunId, setFollowupRunId] = useState('') // 追问线程前轮
  const busyRef = useRef(false)
  const listRef = useRef(null)

  const setLastTurn = updater => setItems(prev => {
    const next = prev.slice()
    for (let i = next.length - 1; i >= 0; i -= 1) {
      if (next[i].role === 'assistant') {
        next[i] = { ...next[i], turn: updater(next[i].turn) }
        break
      }
    }
    return next
  })

  const scrollBottom = () => {
    requestAnimationFrame(() => {
      if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
    })
  }

  function loadRuns() {
    listRunsV2(20).then(setRuns).catch(() => { /* 列表失败静默——不拦主链路 */ })
  }
  useEffect(() => { loadRuns() }, [])

  function handlers() {
    return {
      onFrame: f => { setLastTurn(t => reduceV2Frame(t, f)); scrollBottom() },
      onDone: () => { busyRef.current = false; setBusy(false); loadRuns() },
      onError: d => {
        setLastTurn(t => ({ ...t, closed: 'error', runStatus: 'failed', errMsg: d?.message || '流内错误' }))
        busyRef.current = false; setBusy(false)
      },
      onReplayTruncated: d => {
        setLastTurn(t => ({ ...t, closed: 'replay_truncated', errMsg: d?.message || '重放截断' }))
        busyRef.current = false; setBusy(false)
      },
      onTransportError: err => {
        setLastTurn(t => ({ ...t, closed: 'transport', errMsg: errText(err) }))
        busyRef.current = false; setBusy(false)
      }
    }
  }

  function ask(text) {
    const question = (text || '').trim()
    if (!question || busyRef.current) return
    setActive(routeOf(question))
    const turn = newTurnV2('ask', question)
    setItems(prev => [...prev,
      { role: 'user', text: question, key: `u-${prev.length}` },
      { role: 'assistant', turn, key: `a-${prev.length}` }
    ])
    setInput('')
    busyRef.current = true; setBusy(true)
    setFollowupRunId('')
    Promise.resolve(postAskV2(
      { question, ...(followupRunId ? { followupRunId } : {}) }, handlers()
    ))
      .catch(err => {
        setLastTurn(t => ({
          ...t, closed: 'error', runStatus: 'failed',
          errMsg: err instanceof ApiError ? errText(err) : String(err)
        }))
        busyRef.current = false; setBusy(false)
      })
  }

  /** 挂起续推：同回合续写（reduce 进同一 turn——askFrame 清空待新挂起）。 */
  function resume(chosen) {
    const item = [...items].reverse().find(it => it.role === 'assistant')
    const turn = item?.turn
    if (!turn?.askFrame || !turn.runId || busyRef.current) return
    const body = resumeBodyFromAskFrame(turn.askFrame, chosen)
    setLastTurn(t => ({ ...t, askFrame: null }))
    busyRef.current = true; setBusy(true)
    Promise.resolve(postResumeV2(turn.runId, body, handlers()))
      .catch(err => {
        setLastTurn(t => ({
          ...t, closed: 'error', runStatus: 'failed',
          errMsg: err instanceof ApiError ? errText(err) : String(err)
        }))
        busyRef.current = false; setBusy(false)
      })
  }

  /** 回合渲染（assistant）：挂起卡／错误条／过程折叠／正文／引用。 */
  function renderTurn(turn) {
    const failing = turn.closed === 'error' || turn.closed === 'transport'
    return (
      <div>
        {turn.resumed && <Tag style={{ marginBottom: 6 }}>续推</Tag>}
        {failing && <Alert type="error" showIcon message={turn.errMsg || '请求失败'} style={{ margin: '6px 0' }} />}
        {turn.notices.map((n, i) => <NoticeRow key={i} n={n} />)}
        {turn.askFrame && turn.runStatus === 'waiting_ask' && (
          <AskCard frame={turn.askFrame} busy={busy} onChoose={resume} />
        )}
        {turn.steps.length > 0 && (
          <Collapse size="small" style={{ margin: '6px 0' }} items={[{
            key: 'proc',
            label: <span style={dim}>{`过程（${turn.steps.length} 步·${turn.tools.length} 次工具·${turn.materials.length} 支材料）`}</span>,
            children: (
              <div style={{ maxHeight: 260, overflowY: 'auto' }}>
                {turn.steps.map(s => (
                  <div key={s.seq} style={{ fontSize: 12, marginBottom: 2 }}>
                    <Tag style={{ marginRight: 6 }}>{s.seq}</Tag>{s.title}
                  </div>
                ))}
                {turn.tools.map((tl, i) => (
                  <div key={i} style={{ fontSize: 12, color: '#8b949e' }}>
                    └ {tl.tool}：{tl.status}{tl.message ? `（${tl.message}）` : ''}
                  </div>
                ))}
              </div>
            )
          }]} />
        )}
        {turn.answerText && (
          <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7 }}>
            {turn.answerText}
          </div>
        )}
        {!turn.answerText && !failing && turn.runStatus === 'running' && <Spin size="small" />}
        {turn.citations.length > 0 && (
          <div style={{ marginTop: 6 }}>
            <Button size="small" type="link" style={{ paddingLeft: 0 }}
              onClick={() => setCiteTurn(turn)}>
              {`引用材料（${turn.citations.length}）`}
            </Button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 56px)' }}>
      {/* 最近对话栏（V2-73 会话历史读口——点击回显问答，追问按钮挂会话线程） */}
      <div style={{ width: 264, flexShrink: 0, borderRight: '1px solid #21262d', overflowY: 'auto', padding: 8 }}>
        <div style={{ ...dim, marginBottom: 6 }}>最近对话{helpIcon('V2 任务档案（agent_v2_runs）——点击回显答案；「追问此任务」把该任务作为会话线程前轮，下一条问题带完整历史')}</div>
        {runs.map(r => (
          <div key={r.run_id} style={{ borderBottom: '1px solid #21262d', padding: '6px 4px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
              <a style={{ fontSize: 12, cursor: 'pointer', color: '#79b8ff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                onClick={() => setExpandedRun(expandedRun === r.run_id ? null : r.run_id)}>
                {(r.question || '').slice(0, 22) || r.run_id}
              </a>
              <Tag color={r.status === 'completed' ? 'green' : r.status === 'waiting_ask' ? 'gold' : r.status === 'failed' ? 'red' : 'blue'}
                style={{ fontSize: 10, flexShrink: 0 }}>{r.status}</Tag>
            </div>
            {expandedRun === r.run_id && (
              <div style={{ fontSize: 12, whiteSpace: 'pre-wrap', marginTop: 4, maxHeight: 220, overflowY: 'auto', color: '#c9d1d9' }}>
                {r.answer || '（未收口——无答案文本）'}
              </div>
            )}
            <Button size="small" type="link" style={{ padding: 0, fontSize: 11 }}
              onClick={() => setFollowupRunId(r.run_id)}>追问此任务</Button>
            {followupRunId === r.run_id && (
              <Tag color="geekblue" style={{ fontSize: 10 }}>追问中——下一条问题带会话线程</Tag>
            )}
          </div>
        ))}
        {runs.length === 0 && <div style={dim}>暂无任务。</div>}
      </div>
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
      <Card title={<>问一问V2{helpIcon('V2 问答主链：意图澄清→工具阀→前置条件阀→查询执行→核验收口；全程只读')}<Tag style={{ marginLeft: 8 }} color="geekblue">V2 后端</Tag></>}
        extra={<Button size="small" icon={<ApartmentOutlined />} onClick={() => setTreeOpen(true)}>决策树</Button>}
        styles={{ body: { flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', padding: '12px 16px' } }}
        style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div ref={listRef} style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: 4 }}>
          {items.length === 0 && (
            <div style={{ ...dim, textAlign: 'center', marginTop: 80 }}>
              输入问题开始（支持追问续会话与断线重连——挂起后按 ask 帧续推）
            </div>
          )}
          {items.map(it => it.role === 'user' ? (
            <div key={it.key} style={{ textAlign: 'right', margin: '10px 0' }}>
              <span style={{
                display: 'inline-block', padding: '6px 12px', borderRadius: 10,
                background: '#1f3a5f', color: '#c9d1d9', fontSize: 13, whiteSpace: 'pre-wrap'
              }}>{it.text}</span>
            </div>
          ) : (
            <Card key={it.key} size="small" style={{ margin: '10px 0' }}>
              {renderTurn(it.turn)}
            </Card>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8, paddingTop: 10 }}>
          <Input value={input} onChange={e => setInput(e.target.value)}
            placeholder="向 V2 提问（Enter 发送）" disabled={busy}
            onPressEnter={() => ask(input)} allowClear />
          <Button type="primary" icon={<SendOutlined />} disabled={busy || !input.trim()}
            onClick={() => ask(input)}>发送</Button>
        </div>
      </Card>

      {/* 引用抽屉 */}
      <Drawer title="引用材料" width={480} open={Boolean(citeTurn)} onClose={() => setCiteTurn(null)}>
        {(citeTurn?.citations || []).map(c => {
          const mat = (citeTurn.materials || []).find(m => m.index === c.index)
          return (
            <Card key={c.index} size="small" style={{ marginBottom: 8 }} title={(
              <span>[{c.index}] {c.source}<Tag style={{ marginLeft: 6 }}>{c.trust}</Tag></span>
            )}>
              <div style={{ fontSize: 12, whiteSpace: 'pre-wrap' }}>
                {mat?.content || '（材料未在回合内渲染——重连可回放）'}
              </div>
            </Card>
          )
        })}
        {!citeTurn?.citations?.length && <div style={dim}>本回合无引用。</div>}
      </Drawer>

      {/* 决策树（V2 主链版） */}
      <Modal footer={null} width="100%" open={treeOpen} onCancel={() => setTreeOpen(false)}
        style={{ top: 0, maxWidth: '100vw', height: '100vh', paddingBottom: 0 }}
        styles={{ body: { height: 'calc(100vh - 110px)', overflow: 'auto' } }}
        title={(
          <span>
            决策树（V2 主链）
            {(() => {
              const sc = active ? TREE_BY_KEY[active] : null
              return sc
                ? <Tag style={{ marginLeft: 8 }} color={sc.tag.color}>当前命中：{sc.hist}</Tag>
                : <Tag style={{ marginLeft: 8 }}>当前没有命中的场景（输入问句后，按关键词点亮对应路径）</Tag>
            })()}
          </span>
        )}
      >
        <div style={{ overflowX: 'auto' }}>
          <DecisionTreeV2 byKey={TREE_BY_KEY} active={active} />
        </div>
      </Modal>
      </div>
    </div>
  )
}
