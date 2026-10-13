/**
 * 落地树 · A1V2 问一问V2（对接 V2 后端 /api/v2/*——specs/agent-loop.md 三端点＋V2-73 列表读口）。
 *
 * 页面骨架与问一问V1（landing/A1.jsx）同构三栏（Owner 拍板：逻辑/样式统一，V2 只换芯）：
 * 左栏＝历史对话（V2-73 runs 列表——点击中栏回放，waiting_ask 态出审批按钮）；
 * 中栏＝对话流（回放 viewing 态/实时回合/挂起卡/notice 三级/引用抽屉）；
 * 右栏＝思考过程（最近回合过程帧——步时间线/工具行/材料计数；extra 决策树）。
 * V1 专属面不设——DEBT(V2-00)：@资产（V1 端点 6）不在 V2 合同内；逐帧回放随会话面票补。
 * 挂起判定铁律：ask 帧在场＝等人工（挂起腿 done 只收束本腿流，不以 done 判完局）。
 */
import { useEffect, useRef, useState } from 'react'
import {
  Alert, Button, Card, Collapse, Drawer, Input, List, Modal, Space, Spin, Tag
} from 'antd'
import {
  ApartmentOutlined, QuestionCircleOutlined, SendOutlined
} from '@ant-design/icons'
import { ApiError, errText } from '../api/client.js'
import {
  listRunsV2, postAskV2, postResumeV2, resumeBodyFromAskFrame
} from '../api/chatV2.js'
import { helpIcon, dim } from '../components/helpIcon.jsx'
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

const NOTICE_ALERT = new Set(['refused', 'budget_converged'])
const NOTICE_FOLD = new Set(['window_note', 'no_hit', 'material_truncated'])
function NoticeRow({ n }) {
  if (NOTICE_ALERT.has(n.type)) {
    return <Alert type="warning" showIcon message={n.content} style={{ margin: '6px 0' }} />
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

// 状态文案（V1 列内两行式——行2 dim 文本；waiting_ask 行1 前缀金色询问图标）
const STATUS_TEXT = {
  running: '运行中', waiting_ask: '待确认', completed: '已完成', failed: '失败'
}

function statusTag(status) {
  const color = status === 'completed' ? 'green'
    : status === 'waiting_ask' ? 'gold'
      : status === 'failed' ? 'red' : 'blue'
  return <Tag color={color} style={{ fontSize: 10, flexShrink: 0 }}>{status}</Tag>
}

export default function A1V2Landing() {
  const [items, setItems] = useState([]) // 实时会话回合流 {type:'user'|'assistant', text?, turn?}
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [runs, setRuns] = useState([]) // 左栏最近任务（V2-73）
  const [viewing, setViewing] = useState(null) // {run}——中栏回放态
  const [citeTurn, setCiteTurn] = useState(null)
  const [treeOpen, setTreeOpen] = useState(false)
  const [active, setActive] = useState(null)
  const [followupRunId, setFollowupRunId] = useState('')
  const busyRef = useRef(false)
  const convRef = useRef(null)

  const loadRuns = () => {
    listRunsV2(20).then(setRuns).catch(() => { /* 列表失败静默——不拦主链路 */ })
  }
  useEffect(() => { loadRuns() }, [])

  const setLastTurn = updater => setItems(prev => {
    const next = prev.slice()
    for (let i = next.length - 1; i >= 0; i -= 1) {
      if (next[i].type === 'assistant') {
        next[i] = { ...next[i], turn: updater(next[i].turn) }
        break
      }
    }
    return next
  })

  const scrollBottom = () => {
    requestAnimationFrame(() => {
      if (convRef.current) convRef.current.scrollTop = convRef.current.scrollHeight
    })
  }

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
    setViewing(null) // 新提问＝退出回放（V1 同口径）
    const turn = newTurnV2('ask', question)
    setItems(prev => [...prev,
      { type: 'user', text: question, key: `u-${prev.length}` },
      { type: 'assistant', turn, key: `a-${prev.length}` }
    ])
    setInput('')
    busyRef.current = true; setBusy(true)
    setFollowupRunId('')
    Promise.resolve(postAskV2(
      { question, ...(followupRunId ? { followupRunId } : {}) }, handlers()
    )).catch(err => {
      setLastTurn(t => ({
        ...t, closed: 'error', runStatus: 'failed',
        errMsg: err instanceof ApiError ? errText(err) : String(err)
      }))
      busyRef.current = false; setBusy(false)
    })
  }

  /** 挂起续推：同回合续写。 */
  function resumeLive(chosen) {
    const item = [...items].reverse().find(it => it.type === 'assistant')
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

  /** 历史挂起态的审批按钮（中栏回放可见）——续推即转实时回合（新回合收流）。 */
  function resumeFromHistory(run, decision) {
    if (busyRef.current) return
    const turn = newTurnV2('resume', run.question)
    turn.runId = run.run_id
    turn.resumed = true
    setItems(prev => [...prev,
      { type: 'user', text: `（续推历史任务）${run.question}`, key: `u-${prev.length}` },
      { type: 'assistant', turn, key: `a-${prev.length}` }
    ])
    setViewing(null)
    busyRef.current = true; setBusy(true)
    Promise.resolve(postResumeV2(run.run_id, { kind: 'approval', decision }, handlers()))
      .catch(err => {
        setLastTurn(t => ({
          ...t, closed: 'error', runStatus: 'failed',
          errMsg: err instanceof ApiError ? errText(err) : String(err)
        }))
        busyRef.current = false; setBusy(false)
      })
  }

  /** 中栏条目渲染（实时与回放共用壳）。 */
  function renderItems(list) {
    return list.map(it => it.type === 'user' ? (
      <Card key={it.key} size="small" style={{ background: 'rgba(22,119,255,0.12)', marginBottom: 8 }}>
        <b>我：</b>{it.text}
      </Card>
    ) : (
      <Card key={it.key} size="small" style={{ marginBottom: 8 }}>
        {renderTurn(it.turn)}
      </Card>
    ))
  }

  function renderTurn(turn) {
    const failing = turn.closed === 'error' || turn.closed === 'transport'
    return (
      <div>
        {turn.resumed && <Tag style={{ marginBottom: 6 }}>续推</Tag>}
        {failing && <Alert type="error" showIcon message={turn.errMsg || '请求失败'} style={{ margin: '6px 0' }} />}
        {turn.notices.map((n, i) => <NoticeRow key={i} n={n} />)}
        {turn.askFrame && turn.runStatus === 'waiting_ask' && (
          <Card size="small" style={{ margin: '8px 0', borderColor: '#4a9dff' }} title={(
            <span>{turn.askFrame.kind === 'external_table_approval' ? '越集审批' : '系统反问'}{helpIcon(
              turn.askFrame.kind === 'external_table_approval'
                ? '子问题取数计划引用了平台外的数据表——批准后该表进白名单，不重排计划'
                : '系统需要你确认口径或补充信息后才能继续')}</span>
          )}>
            <div style={{ marginBottom: 8 }}>{turn.askFrame.prompt}</div>
            {turn.askFrame.kind === 'external_table_approval' && turn.askFrame.detail?.tables && (
              <div style={dim}>外部表：{turn.askFrame.detail.tables.join('、')}</div>
            )}
            <Space wrap>
              {(turn.askFrame.options || []).map(op => (
                <Button key={op} size="small" type="primary" ghost disabled={busy}
                  onClick={() => resumeLive(op)}>{op}</Button>
              ))}
            </Space>
          </Card>
        )}
        {turn.answerText && (
          <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7 }}>{turn.answerText}</div>
        )}
        {!turn.answerText && !failing && turn.runStatus === 'running' && <Spin size="small" />}
        {turn.citations.length > 0 && (
          <Button size="small" type="link" style={{ paddingLeft: 0, marginTop: 6 }}
            onClick={() => setCiteTurn(turn)}>
            {`引用材料（${turn.citations.length}）`}
          </Button>
        )}
      </div>
    )
  }

  /** 右栏过程帧源（最近实时回合；回放态右栏空态提示）。 */
  const lastTurn = viewing ? null
    : [...items].reverse().find(it => it.type === 'assistant')?.turn ?? null

  /** 中栏回放体（历史 run：问＋答案＋挂起态审批按钮）。 */
  function renderViewing() {
    const r = viewing.run
    return (
      <div>
        <Card size="small" style={{ background: 'rgba(22,119,255,0.12)', marginBottom: 8 }}>
          <b>我：</b>{r.question}
        </Card>
        <Card size="small" style={{ marginBottom: 8 }}>
          <div style={{ marginBottom: 6 }}>{statusTag(r.status)}<span style={dim}>{` · ${r.created_at?.replace('T', ' ').slice(0, 19) ?? ''}`}</span></div>
          <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7 }}>
            {r.answer || '（未收口——无答案文本）'}
          </div>
          {r.status === 'waiting_ask' && (
            <Card size="small" style={{ margin: '8px 0 0', borderColor: '#e8b339' }} title={
              <span>该任务挂起待确认{helpIcon('V2 任务在挂起态——批准/驳回即转实时续推')}</span>}>
              <Space wrap>
                <Button size="small" type="primary" disabled={busy}
                  onClick={() => resumeFromHistory(r, 'approve')}>批准</Button>
                <Button size="small" danger disabled={busy}
                  onClick={() => resumeFromHistory(r, 'reject')}>驳回</Button>
              </Space>
            </Card>
          )}
        </Card>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'stretch', height: '100%' }}>
      {/* ── 左栏 · 历史对话（V2-73 runs 列表——点击中栏回放；追问按钮挂会话线程） ── */}
      <Card
        title={<span>历史对话{helpIcon('V2 任务档案（agent_v2_runs）——点击在中栏回看问答；「追问此任务」把该任务作为会话线程前轮')}</span>}
        size="small"
        style={{ width: 250, flexShrink: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 0, overflowY: 'auto' } }}>
        <div style={{ ...dim, marginBottom: 4 }}>共 {runs.length} 条</div>
        <List size="small" dataSource={runs} locale={{ emptyText: '暂无数据' }}
          renderItem={r => (
            <List.Item style={{ cursor: busy ? 'wait' : 'pointer', padding: '4px 0' }}
              onClick={() => !busy && setViewing({ run: r, loading: false, error: null })}>
              <div>
                <div style={{ fontSize: 13 }}>
                  {r.status === 'waiting_ask' && (
                    <QuestionCircleOutlined style={{ color: '#e8b339', marginRight: 6 }} />
                  )}
                  {(r.question || '').slice(0, 18) || r.run_id}
                </div>
                <div style={{ ...dim, display: 'flex', justifyContent: 'space-between' }}>
                  <span>{STATUS_TEXT[r.status] ?? r.status}{r.created_at ? ` · ${r.created_at.replace('T', ' ').slice(5, 16)}` : ''}</span>
                  <a style={{ fontSize: 11 }}
                    onClick={e => { e.stopPropagation(); if (!busy) setFollowupRunId(r.run_id) }}>
                    追问此任务
                  </a>
                </div>
              </div>
            </List.Item>
          )} />
        {followupRunId && (
          <div style={{ marginTop: 6 }}>
            <Tag color="geekblue" closable onClose={() => setFollowupRunId('')}>
              追问中——下一条问题带会话线程
            </Tag>
          </div>
        )}
      </Card>

      {/* ── 中栏 · 对话流（回放 viewing 态／实时回合） ── */}
      <Card size="small" style={{ flex: 1, minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 320, display: 'flex', flexDirection: 'column' } }}>
        <div ref={convRef} style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: 4 }}>
          {viewing ? (
            <>
              <div style={{ ...dim, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>正在查看历史任务——只读回放。</span>
                <Button type="link" size="small" style={{ padding: 0 }} onClick={() => setViewing(null)}>返回当前</Button>
              </div>
              {renderViewing()}
            </>
          ) : (
            <>
              {items.length === 0 && (
                <div style={{ ...dim, textAlign: 'center', marginTop: 80 }}>
                  输入问题开始（挂起后在本栏确认；历史任务见左侧）
                </div>
              )}
              {renderItems(items)}
            </>
          )}
        </div>
        <div style={{ marginTop: 10 }}>
          {followupRunId && (
            <div style={{ marginBottom: 6 }}>
              <Tag color="geekblue" closable onClose={() => setFollowupRunId('')}>
                {`追问线程：${followupRunId}`}
              </Tag>
            </div>
          )}
          <Space.Compact style={{ width: '100%' }}>
            <Input placeholder="输入问题（Enter 发送）" value={input} disabled={busy}
              onPressEnter={e => { if (e.nativeEvent.isComposing) return; ask(input) }}
              onChange={e => setInput(e.target.value)} />
            <Button type="primary" icon={<SendOutlined />} loading={busy} onClick={() => ask(input)}>发送</Button>
          </Space.Compact>
        </div>
      </Card>

      {/* ── 右栏 · 思考过程（最近实时回合过程帧） ── */}
      <Card title={<>思考过程 <ApartmentOutlined style={{ color: '#8a94a3' }} /></>} size="small"
        extra={<Button size="small" icon={<ApartmentOutlined />} onClick={() => setTreeOpen(true)}>决策树</Button>}
        style={{ width: 330, flexShrink: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' } }}>
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: 4 }}>
          {!lastTurn && <div style={dim}>提问后这里逐步长出过程帧（步/工具/材料/提示）。</div>}
          {lastTurn && (
            <>
              <div style={{ ...dim, marginBottom: 4 }}>
                {`${lastTurn.steps.length} 步 · ${lastTurn.tools.length} 次工具 · ${lastTurn.materials.length} 支材料 · ${lastTurn.citations.length} 引`}
              </div>
              {lastTurn.steps.map(s => (
                <div key={s.seq} style={{ fontSize: 12, marginBottom: 3 }}>
                  <Tag style={{ marginRight: 6 }}>{s.seq}</Tag>{s.title}
                </div>
              ))}
              {lastTurn.tools.map((tl, i) => (
                <div key={i} style={{ fontSize: 12, color: '#8b949e', marginLeft: 30 }}>
                  └ {tl.tool}：{tl.status}{tl.message ? `（${tl.message}）` : ''}
                </div>
              ))}
              {lastTurn.notices.map((n, i) => <NoticeRow key={i} n={n} />)}
            </>
          )}
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
                {mat?.content || '（材料未在回合内渲染）'}
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
  )
}
