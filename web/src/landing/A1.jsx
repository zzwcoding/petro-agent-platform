/**
 * 落地树 · A1 问一问（P1-09 全页真 API——P1-08a/b/c SSE 主链＋树叙事帧消费）。
 *
 * 合同：teach-petro-agent/specs/api/A1-问一问.md（端点 4 asks＝统一入口无旁路/
 * 端点 5 resume＝interrupt 决策回流/端点 2 sessions/端点 6 assets）＋ 00 §6
 * （帧信封＋三保留帧）。视觉与交互形态对照原型终稿 #/proto/A1
 * （web/src/pages/A1Chat.jsx 快照——三栏：历史会话/对话流/思考过程树）。
 *
 * 接线差异（相对原型页，登记票面）：
 * - 前端零编排（A1 行为规则 1）：思考树完全由 SSE 帧驱动「长出来的」——
 *   node 帧按 key 原位升更新（process→finish 两拍同键，00 §5.3 节点步进），
 *   链内 S 级/GEN 缩进挂链执行节点之下；token 自首帧后与树帧分区分渲染
 *   （服务端时序保证：首个 token 前是全部树帧——P1-08c 金样本断言）。
 * - @ 点名提示：端点 6 chat/assets 真接线（P1-11——各注册表现取投影：
 *   指标卡/术语/FAQ/工作流/报告；工具注册表未建投影为空），token 形状照抄
 *   端点 6「类型·名称」结晶体；anchors 随 asks 上送（服务端 S1 前门直取）。
 * - 历史会话：端点 2 真接线（P1-11——服务端列表 available 才渲染）；本机
 *   最近运行（页面级缓存）可点开＝端点 4 重连形态真恢复（resume_run_id 重放
 *   持久帧——P1-08c），非原型「点历史＝整条流程重跑」。
 * - 消息回放读口（端点 3 sessions/{id}/messages）真接线（P1-12）：点服务端
 *   会话＝中栏只读回放消息与答案卡（answer 与 SSE answer 帧同形直出——
 *   citations 可点开出处抽屉）；过程帧逐帧回放不在本版合同（A1 开放问题 2，
 *   随 D5 产品化批）；回放中发送新问题＝开启新会话（诚实提示）。 DEBT(P1-12)
 * - 断线提示：replay_truncated 收场话术帧直出（不静默丢帧）；POST 流传输
 *   断＝「从断点恢复」按钮（resume_run_id＋Last-Event-ID 手动续推——
 *   EventSource 自动重连仅 GET 形态，api/chat.js 选型注记）。
 * - 拦截/兜底/置信度标注全按帧直出：verdict.confidence 档位徽标（高/中/低）、
 *   answer.no_model FAQ 直出标注、（未依据报告库）兜底标注徽标——文本零改写。
 */

import { useEffect, useRef, useState } from 'react'
import {
  Alert, Badge, Button, Card, Collapse, Descriptions, Drawer, Empty, Input, List,
  Space, Spin, Tag, Tooltip
} from 'antd'
import { ApartmentOutlined, SendOutlined } from '@ant-design/icons'
import { ApiError } from '../api/client.js'
import {
  listAssets, listMessages, listSessions, postAsk, postResume, reconnectRun
} from '../api/chat.js'
import { useAppStore } from '../store/app.js'

const dim = { fontSize: 12, color: '#8a94a3' }

// ---------- 帧归约（纯函数——单测直喂帧序列，不经渲染） ----------

/** 空回合（一次问答/一次续推/一次重放＝一个 assistant 回合的帧容器）。 */
export function newTurn(kind, question) {
  return {
    kind, // ask | resume | replay
    question,
    runId: '',
    sessionId: '',
    replay: false, // session.resume=true（续推/重放标识）
    stage: null, // 0 发起 | 1 装配 | 2 裁决 | 3 链内
    secChecks: [],
    matches: [],
    assembly: null,
    verdict: null,
    nodes: [], // [{key,name,state,note,tag,skipped}]——按 key 原位升更新
    nodeLines: {}, // key → [{mark,text}]
    notices: [],
    answerText: '', // token 拼贴（answer 帧到达前的流式预览）
    citations: [],
    answer: null, // answer 帧载荷（收口真源）
    clarify: null,
    approval: null,
    chosenLabel: '',
    closed: null, // done | error | replay_truncated | transport
    errMsg: '',
    truncMsg: '',
    lastEventId: ''
  }
}

/** node 帧按 key 原位升更新（同键两拍 process→finish 不新增行）。 */
function upsertNode(nodes, data) {
  const node = {
    key: data.key,
    name: data.name || data.label || data.key,
    state: data.state || 'wait',
    note: data.note ?? null,
    tag: data.tag ?? null,
    skipped: Boolean(data.skipped)
  }
  const at = nodes.findIndex(n => n.key === node.key)
  if (at < 0) return [...nodes, node]
  const next = nodes.slice()
  next[at] = { ...next[at], ...node }
  return next
}

function upsertBy(list, keyField, item) {
  const at = list.findIndex(x => x[keyField] === item[keyField])
  if (at < 0) return [...list, item]
  const next = list.slice()
  next[at] = { ...next[at], ...item }
  return next
}

/** citation 帧载荷（A1 冻结形状 {ref,kind,label,locator}）。 */
function upsertCitation(list, data) {
  if (!data || !data.ref) return list
  return upsertBy(list, 'ref', {
    ref: data.ref, kind: data.kind || '', label: data.label || '',
    locator: data.locator || {}
  })
}

/**
 * 单帧归约进回合（19 类帧全集——未发帧（tool_call/lineage/approval）按合同
 * 形状注册消费，零发不冒充有）。
 * @param {object} turn 回合
 * @param {{id: string, event: string, data: any}} f 帧
 * @returns {object} 新回合
 */
export function applyFrame(turn, f) {
  const d = f.data ?? {}
  switch (f.event) {
    case 'session':
      return { ...turn, runId: d.run_id || turn.runId, sessionId: d.thread_id || turn.sessionId, replay: Boolean(d.resume) }
    case 'stage':
      return { ...turn, stage: d.stage }
    case 'sec_check':
      return { ...turn, secChecks: upsertBy(turn.secChecks, 'seq', d) }
    case 'match':
      return { ...turn, matches: upsertBy(turn.matches, 'matcher', d) }
    case 'assembly':
      return { ...turn, assembly: d }
    case 'verdict':
      return { ...turn, verdict: d }
    case 'node':
      return { ...turn, nodes: upsertNode(turn.nodes, d) }
    case 'node_line': {
      const lines = turn.nodeLines[d.key] || []
      return { ...turn, nodeLines: { ...turn.nodeLines, [d.key]: [...lines, { mark: d.mark, text: d.text }] } }
    }
    case 'token':
      return { ...turn, answerText: turn.answerText + String(d.delta ?? '') }
    case 'citation':
      return { ...turn, citations: upsertCitation(turn.citations, d) }
    case 'tool_call':
      return { ...turn, toolCall: d }
    case 'lineage':
      return { ...turn, lineage: d }
    case 'answer':
      // answer 帧＝收口真源：拼贴预览换正式文本（同一文本——金样本同值）
      return { ...turn, answer: d, answerText: typeof d.text === 'string' ? d.text : turn.answerText }
    case 'clarify':
      return { ...turn, clarify: d }
    case 'approval':
      return { ...turn, approval: d }
    case 'notice':
      return { ...turn, notices: [...turn.notices, { level: d.level || 'info', text: d.text || '' }] }
    case 'done':
      return { ...turn, closed: 'done' }
    case 'error':
      return { ...turn, closed: 'error', errMsg: d.message || '服务端异常' }
    case 'replay_truncated':
      return { ...turn, closed: 'replay_truncated', truncMsg: d?.message || '会话中断，已出内容保留——请重新提问。' }
    default:
      return turn
  }
}

// ---------- 视图小件 ----------

const STAGE_LABELS = ['发起', '装配', '裁决', '链内']

const CONF_COLOR = { 高: 'green', 中: 'orange', 低: 'red' }

/** 置信度档位徽标（verdict.confidence＝档位值＋标注后缀，档位判定在服务端）。 */
export function confidenceTag(label) {
  if (!label) return null
  const tone = CONF_COLOR[String(label).trim()[0]] || 'default'
  return <Tag color={tone} style={{ marginInlineEnd: 0 }}>置信度 {label}</Tag>
}

/** D2 兜底 free 态合同标注（服务端把「（未依据报告库）」拼进答案尾——识别出徽标，文本不改写）。 */
const FREE_ANSWER_TAG = '（未依据报告库）'

const NODE_BADGE = {
  wait: 'default',
  process: 'processing',
  finish: 'success',
  error: 'error'
}
const MARK_COLOR = { '✓': '#52c41a', '✗': '#ff4d4f', '→': '#3b8dff', '○': '#8a94a3', '·': '#8a94a3' }

/** 思考树节点行（00 §5.3 四态＋skipped 灰显＋note 小字＋tag 徽标）。 */
function NodeRow({ node, lines }) {
  const gray = node.skipped
  return (
    <div data-node-key={node.key} data-node-state={node.state}
      style={{ opacity: gray ? 0.55 : 1, margin: '2px 0' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
        <Badge status={NODE_BADGE[node.state] || 'default'} />
        <span style={{ fontSize: 13, color: gray ? '#8a94a3' : '#d7dce3' }}>
          {node.name}
          {gray && <span style={{ marginLeft: 6 }}>（已跳过）</span>}
        </span>
        {node.tag && <Tag style={{ marginInlineEnd: 0, fontSize: 11, lineHeight: '16px' }}>{node.tag}</Tag>}
      </div>
      {node.note && <div style={{ ...dim, marginLeft: 16, marginTop: 1 }}>{node.note}</div>}
      {(lines || []).map((l, i) => (
        <div key={i} style={{ ...dim, marginLeft: 16 }}>
          <span style={{ color: MARK_COLOR[l.mark] || '#8a94a3' }}>{l.mark}</span> {l.text}
        </div>
      ))}
    </div>
  )
}

/** citation 出处族 → 回跳链路（报告→B2 定位／图谱→B5／其余族读面预留）。 */
export function citationJump(citation) {
  const kind = citation.kind || ''
  const fid = citation.locator?.fragment_id
  if (kind === '报告引用') return fid ? { hash: `/B2?chunk=${encodeURIComponent(fid)}`, label: '去切片管理定位' } : { hash: '/B2', label: '去切片管理' }
  if (kind === '图谱') return { hash: '/B5', label: '去关系图谱' }
  return null // 台账条目/数据证据——wiki/台账读面随对应页接线预留（抽屉内注记） DEBT(阶段2-B4页)
}

/** citation 角标行（点击开出处抽屉）。 */
function CitationBadges({ citations, onOpen }) {
  if (!citations.length) return null
  return (
    <Space size={4} wrap style={{ marginTop: 8 }}>
      {citations.map(c => (
        <Tooltip key={c.ref} title={`${c.kind} · ${c.label}`}>
          <Tag color="blue" style={{ cursor: 'pointer', marginInlineEnd: 0 }} data-citation={c.ref}
            onClick={() => onOpen(c)}>
            证 {c.ref}
          </Tag>
        </Tooltip>
      ))}
    </Space>
  )
}

/** 答案卡（answer 帧六种 kind 合同渲染——三链现产 text/alert，其余注册待产）。 */
function AnswerCard({ turn, onOpenCitation }) {
  const a = turn.answer
  const body = a ? a : { kind: 'text', text: turn.answerText }
  const free = (body.text || '').includes(FREE_ANSWER_TAG)
  return (
    <Card size="small" style={{ background: 'rgba(255,255,255,0.04)', marginTop: 10 }}>
      {body.kind === 'alert' ? (
        <Alert type={body.alert_type === 'warning' ? 'warning' : body.alert_type || 'info'} showIcon message={body.text} />
      ) : (
        <div style={{ fontSize: 14, lineHeight: 1.9, whiteSpace: 'pre-wrap' }}>{body.text}{!a && <Spin size="small" style={{ marginLeft: 8 }} />}</div>
      )}
      {body.kind !== 'text' && body.kind !== 'alert' && (
        <div className="code-block" style={{ marginTop: 8 }}>{JSON.stringify(body, null, 2)}</div>
      )}
      {a?.no_model && (
        <Alert style={{ marginTop: 8 }} type="success" showIcon message="本条命中 FAQ 直出——未调用模型，无生成过程。" />
      )}
      <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        {confidenceTag(turn.verdict?.confidence)}
        {free && <Tag color="orange" style={{ marginInlineEnd: 0 }}>未依据报告库</Tag>}
        <CitationBadges citations={turn.citations.length ? turn.citations : a?.citations || []} onOpen={onOpenCitation} />
      </div>
    </Card>
  )
}

  // ---------- 本机最近运行（页面级缓存——与端点 2 并行的本机快照读面） ----------

const RUN_HISTORY = []
function pushRunHistory(entry) {
  const at = RUN_HISTORY.findIndex(e => e.runId === entry.runId)
  if (at >= 0) RUN_HISTORY.splice(at, 1)
  RUN_HISTORY.unshift(entry)
  if (RUN_HISTORY.length > 20) RUN_HISTORY.length = 20
}

// ---------- 页面 ----------

/**
 * 落地 A1 问一问页。
 * @returns {JSX.Element}
 */
export default function A1Landing() {
  const [input, setInput] = useState('')
  const [items, setItems] = useState([]) // [{type:'user',text,key} | {type:'assistant',turn,key}]
  const [busy, setBusy] = useState(false)
  const [atOpen, setAtOpen] = useState(false)
  const [atList, setAtList] = useState([])
  const [atLoaded, setAtLoaded] = useState(false)
  const [serverSessions, setServerSessions] = useState({ items: [], available: false })
  const [viewing, setViewing] = useState(null) // 历史回放（端点 3）：{sessionId,title,loading,error,messages}
  const [drawer, setDrawer] = useState(null) // citation 抽屉
  const [rejectReason, setRejectReason] = useState('')
  const busyRef = useRef(false)
  const turnRef = useRef(null) // 当前回合镜像（帧归约单源——收场后 registerRun 消费）
  const convRef = useRef(null)
  const treeRef = useRef(null)

  // 服务端会话读口（端点 2——available 才渲染；读失败静默空态＝网络韧性）
  useEffect(() => { listSessions().then(setServerSessions) }, [])
  // @ 资产面板（端点 6——输入 @ 时懒加载一次）
  useEffect(() => {
    if (!atOpen || atLoaded) return
    listAssets().then(list => { setAtList(list); setAtLoaded(true) })
  }, [atOpen, atLoaded])

  useEffect(() => { // 树推进自动滚底
    const el = treeRef.current
    if (el?.scrollTo) el.scrollTo({ top: el.scrollHeight })
  }, [items])
  useEffect(() => {
    const el = convRef.current
    if (el?.scrollTo) el.scrollTo({ top: el.scrollHeight })
  }, [items])

  /** 当前回合写回对话流（帧归约单源 turnRef → 最后一个 assistant 槽位）。 */
  function syncTurn() {
    setItems(prev => {
      const at = prev.map(x => x.type).lastIndexOf('assistant')
      if (at < 0) return prev
      const next = prev.slice()
      next[at] = { ...next[at], turn: turnRef.current }
      return next
    })
  }

  /** 回合收场注册：会话槽（store A1 预留槽）＋本机运行史（重连真恢复入口）。 */
  function registerRun(turn, question) {
    if (!turn?.runId) return
    pushRunHistory({ runId: turn.runId, sessionId: turn.sessionId, title: question, at: Date.now() })
    const sid = turn.sessionId
    if (sid) {
      const store = useAppStore.getState()
      const deduped = [{ session_id: sid, title: question },
        ...store.sessions.filter(s => s.session_id !== sid)]
      store.setSessions(deduped.slice(0, 20))
    }
  }

  /** streamChat 五回调组装（ask/resume/reconnect 共用——帧都折进当前回合）。 */
  function handlers() {
    return {
      onFrame: f => {
        // 断点帧号随帧捕获（Last-Event-ID 依据——api/sse.js getLastEventId 同语义）
        turnRef.current = { ...turnRef.current, lastEventId: f.id || turnRef.current.lastEventId }
        turnRef.current = applyFrame(turnRef.current, f)
        syncTurn()
      },
      onDone: () => {
        turnRef.current = { ...turnRef.current, closed: turnRef.current.closed || 'done' }
        syncTurn()
      },
      onError: pkg => {
        turnRef.current = { ...turnRef.current, closed: 'error', errMsg: pkg.message || '服务端异常' }
        syncTurn()
      },
      onReplayTruncated: data => {
        turnRef.current = {
          ...turnRef.current, closed: 'replay_truncated',
          truncMsg: data?.message || '会话中断，已出内容保留——请重新提问。'
        }
        syncTurn()
      },
      onTransportError: () => {
        turnRef.current = { ...turnRef.current, closed: turnRef.current.closed || 'transport' }
        syncTurn()
      }
    }
  }

  async function runStream(streamFn, question) {
    setBusy(true); busyRef.current = true
    try {
      await streamFn()
    } catch (err) {
      // 流开前非 2xx（400/401/404——00 §3.1）：ApiError 内联进回合，不弹全局 toast
      const msg = err instanceof ApiError ? `${err.message}（${err.code || `HTTP ${err.status}`}）` : String(err)
      if (turnRef.current) {
        turnRef.current = { ...turnRef.current, closed: turnRef.current.closed || 'error', errMsg: turnRef.current.errMsg || msg }
        syncTurn()
      }
    } finally {
      setBusy(false); busyRef.current = false
      registerRun(turnRef.current, question)
    }
  }

  function ask(text) {
    const question = (text || '').trim()
    if (!question || busyRef.current) return
    setAtOpen(false)
    setViewing(null) // 新提问＝新会话（回放中提问即退出回放——诚实口径）
    const anchors = [...question.matchAll(/@([^\s@]+)/g)].map(m => m[1])
    turnRef.current = newTurn('ask', question)
    setItems(prev => [...prev,
      { type: 'user', text: question, key: `u-${prev.length}` },
      { type: 'assistant', turn: turnRef.current, key: `a-${prev.length}` }
    ])
    runStream(() => postAsk(
      { question, anchors },
      handlers()
    ), question)
  }

  /** 澄清点选 → 端点 5 回流续推（同一回合续写——interrupt 挂起后接续）。 */
  function chooseClarify(choice) {
    if (busyRef.current) return
    const turn = turnRef.current
    if (!turn?.runId || !turn.clarify) return
    const chosen = turn.clarify.choices.find(c => c.value === choice)
    turnRef.current = { ...turn, chosenLabel: chosen ? chosen.label : choice }
    syncTurn()
    runStream(() => postResume(turn.runId, { kind: 'clarify', choice }, handlers()), turn.question)
  }

  /** 审批回流（批准/驳回——帧族合同注册；后端现无审批挂起，resume 即 409 内联）。 */
  function decideApproval(decision) {
    if (busyRef.current) return
    const turn = turnRef.current
    if (!turn?.runId || !turn.approval) return
    const body = { kind: 'approval', decision }
    if (decision === 'reject') {
      const reason = rejectReason.trim()
      if (!reason) return // N12「须写理由的驳回」——后端 400，前端先挡
      body.reason = reason
    }
    runStream(() => postResume(turn.runId, body, handlers()), turn.question)
  }

  /** 断点手动续推（端点 4 重连形态——resume_run_id＋Last-Event-ID，不重新执行）。 */
  function resumeRun(resumeTurn) {
    if (busyRef.current || !resumeTurn.runId) return
    turnRef.current = newTurn('replay', resumeTurn.question)
    setItems(p => [...p,
      { type: 'user', text: `〔重连续推〕${resumeTurn.question}`, key: `r-${p.length}` },
      { type: 'assistant', turn: turnRef.current, key: `a-${p.length}` }
    ])
    runStream(() => reconnectRun(resumeTurn.runId, resumeTurn.lastEventId, handlers()), resumeTurn.question)
  }

  /** 历史会话回放（端点 3）：拉服务端消息折进中栏（只读——answer 与 SSE
   * answer 帧同形直出；失败内联提示，显式点击动作不走静默韧性）。 */
  async function openHistory(sess) {
    if (busyRef.current) return
    setViewing({ sessionId: sess.id, title: sess.title, loading: true, error: '', messages: [] })
    try {
      const messages = await listMessages(sess.id)
      setViewing(v => (v && v.sessionId === sess.id ? { ...v, loading: false, messages } : v))
    } catch (err) {
      setViewing(v => (v && v.sessionId === sess.id
        ? { ...v, loading: false, error: err.message || '历史会话读取失败' } : v))
    }
  }

  /** 回放消息 → 对话流条目（assistant 回合合成：answer 帧载荷收口＋done 收场）。 */
  function historyItems(v) {
    return v.messages.map(m => m.role === 'user'
      ? { type: 'user', text: m.text, key: m.id }
      : {
          type: 'assistant',
          key: m.id,
          turn: {
            ...newTurn('replay', m.text),
            answer: m.answer,
            answerText: typeof m.answer?.text === 'string' ? m.answer.text : m.text,
            citations: m.answer?.citations || [],
            closed: 'done',
            runId: m.runId || '',
            sessionId: v.sessionId,
            replay: true
          }
        })
  }

  /** 对话流条目渲染（实时会话与历史回放共用一套渲染件）。 */
  function renderItems(list) {
    return list.map(it => it.type === 'user' ? (
      <Card key={it.key} size="small" style={{ background: 'rgba(22,119,255,0.12)', marginBottom: 8 }}>
        <b>我：</b>{it.text}
      </Card>
    ) : (
      <AssistantBubble key={it.key} turn={it.turn} busy={busy}
        onOpenCitation={setDrawer}
        onClarify={chooseClarify}
        onApproval={decideApproval}
        rejectReason={rejectReason}
        onRejectReason={setRejectReason}
        onResume={() => resumeRun(it.turn)} />
    ))
  }

  function onInputChange(e) {
    const v = e.target.value
    setInput(v)
    setAtOpen(/@([^\s@]*)$/.test(v))
  }

  function pickAsset(asset) {
    setInput(v => v.replace(/@[^\s@]*$/, `@${asset.token} `))
    setAtOpen(false)
  }

  const atFiltered = atList.filter(a => {
    const m = input.match(/@([^\s@]*)$/)
    if (!m || !m[1]) return true
    return a.token.toLowerCase().includes(m[1].toLowerCase())
  })

  const lastTurn = lastAssistantTurn(items)
  const tree = lastTurn // 右栏＝最近回合的思考树（原型「随场景切换」同位）

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'stretch' }}>
      {/* ── 左栏 · 历史会话（端点 2 available 才显＋本机运行真恢复） ── */}
      <Card title="历史会话" size="small" style={{ width: 250, flexShrink: 0, alignSelf: 'flex-start' }}>
        {serverSessions.available && (
          <>
            <div style={{ ...dim, marginBottom: 4 }}>服务端会话（端点 2）</div>
            <List size="small" dataSource={serverSessions.items} locale={{ emptyText: '暂无服务端会话' }}
              renderItem={s => (
                <List.Item style={{ cursor: busy ? 'wait' : 'pointer', padding: '4px 0' }}
                  onClick={() => !busy && openHistory(s)}>
                  <div>
                    <div style={{ fontSize: 13 }}>{s.title}</div>
                    <div style={dim}>{s.group}{s.updatedAt ? ` · ${s.updatedAt}` : ''}</div>
                  </div>
                </List.Item>
              )} />
            {/* DEBT(P1-12)：过程帧回放随 D5 产品化批（票面差异登记②） */}
            <div style={{ ...dim, margin: '8px 0 4px' }}>
              点会话＝回放消息与答案卡（端点 3）；过程帧逐帧回放随 D5 产品化批。
            </div>
          </>
        )}
        <div style={{ ...dim, marginBottom: 4 }}>本机最近运行（点开＝断点重连，已出内容不丢）</div>
        {RUN_HISTORY.length === 0 && <div style={dim}>本次进入还没有问答记录。</div>}
        <List size="small" dataSource={[...RUN_HISTORY]}
          renderItem={e => (
            <List.Item style={{ cursor: busy ? 'wait' : 'pointer', padding: '4px 0' }}
              onClick={() => !busy && resumeRun({ runId: e.runId, lastEventId: '', question: e.title })}>              <div style={{ fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {e.title}
              </div>
            </List.Item>
          )} />
        <div style={{ ...dim, marginTop: 8 }}>
          会话在服务端留存：连接中断后重新进入，可从历史会话继续，已生成的内容不丢。
        </div>
      </Card>

      {/* ── 中栏 · 对话流（消息/答案流式/citation/澄清帧） ── */}
      <Card size="small" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 320, display: 'flex', flexDirection: 'column' } }}>
        <div ref={convRef} style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: 4 }}>
          {viewing ? (
            <>
              <Alert style={{ marginBottom: 8 }} type="info" showIcon
                message={`正在查看历史会话：${viewing.title}`}
                description={viewing.loading
                  ? '读取中…'
                  : viewing.error
                    ? `读取失败：${viewing.error}`
                    : '只读回放——发送新问题将开启新会话。'}
                action={<Button size="small" onClick={() => setViewing(null)}>返回当前</Button>} />
              {viewing.loading && <Spin size="small" style={{ margin: 16 }} />}
              {!viewing.loading && !viewing.error && historyItems(viewing).length === 0 && (
                <div style={{ ...dim, padding: '20px 4px' }}>该会话还没有落库消息。</div>
              )}
              {!viewing.loading && !viewing.error && renderItems(historyItems(viewing))}
            </>
          ) : (
            <>
              {items.length === 0 && (
                <div style={{ ...dim, padding: '20px 4px' }}>
                  输入问题开始提问；支持 @指标卡·… / @术语·… 点名（服务端按当前身份装配）。
                  右侧思考过程由服务端事件帧逐节点点亮。
                </div>
              )}
              {renderItems(items)}
            </>
          )}
        </div>
        <div style={{ position: 'relative', marginTop: 10 }}>
          {atOpen && (
            <div style={{
              position: 'absolute', bottom: '100%', left: 0, right: 0, marginBottom: 6, zIndex: 20,
              background: '#161b22', border: '1px solid #30363d', borderRadius: 8,
              padding: '6px 8px', maxHeight: 240, overflowY: 'auto'
            }}>
              <div style={{ ...dim, marginBottom: 4 }}>@ 呼唤现成资产（端点 6 投影——指标卡/术语/FAQ/工作流/报告；被 @ 的资产服务端前门直取）：</div>
              {atFiltered.map(a => (
                <div key={a.token} style={{ cursor: 'pointer', fontSize: 13, padding: '4px 6px', borderRadius: 4 }}
                  data-asset={a.token}
                  onMouseEnter={e => { e.currentTarget.style.background = '#1f242c' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                  onClick={() => pickAsset(a)}>
                  <Tag style={{ marginRight: 6 }}>{a.type}</Tag>{a.name}
                  {a.hint && <span style={{ ...dim, marginLeft: 8 }}>{a.hint.slice(0, 40)}</span>}
                </div>
              ))}
              {atLoaded && atFiltered.length === 0 && <div style={dim}>没有命中的资产。</div>}
            </div>
          )}
          <Space.Compact style={{ width: '100%' }}>
            <Input placeholder="输入问题，或 @指标卡 / @术语 点名…" value={input}
              disabled={busy} onChange={onInputChange}
              onPressEnter={() => ask(input)} />
            <Button type="primary" icon={<SendOutlined />} loading={busy} onClick={() => ask(input)}>发送</Button>
          </Space.Compact>
        </div>
        <div style={{ ...dim, marginTop: 8 }}>
          单一入口：全部问答走 POST /api/chat/asks——安检→装配→裁决→链内四层全在服务端，前端零编排。
        </div>
      </Card>

      {/* ── 右栏 · 思考过程树（node 帧流式推进——「长出来的」） ── */}
      <Card title={<>思考过程 <ApartmentOutlined style={{ color: '#8a94a3' }} /></>} size="small"
        style={{ width: 330, flexShrink: 0, alignSelf: 'flex-start' }}>
        <div ref={treeRef} style={{ maxHeight: 'calc(100vh - 220px)', overflowY: 'auto', paddingRight: 4 }}>
          {/* DEBT(P1-12)：过程帧回放随 D5 产品化批（票面差异登记②） */}
          {!tree && viewing && (
            <div style={dim}>历史回放只还原消息与答案卡——过程帧逐帧回放随 D5 产品化批（A1 开放问题 2）。</div>
          )}
          {!tree && !viewing && <div style={dim}>输入问题或点开历史运行，这里逐帧展示完整处理过程。</div>}
          {tree && <ThinkingTree turn={tree} />}
        </div>
      </Card>

      {/* ── 出处抽屉（citation 点击 → 出处三件套＋回跳链路） ── */}
      <Drawer title="出处" placement="right" width={480} open={!!drawer} onClose={() => setDrawer(null)}>
        {drawer && (
          <>
            <Descriptions size="small" column={1} colon>
              <Descriptions.Item label="引用别名">{drawer.ref}</Descriptions.Item>
              <Descriptions.Item label="出处族">{drawer.kind}</Descriptions.Item>
              <Descriptions.Item label="label">{drawer.label}</Descriptions.Item>
              {Object.entries(drawer.locator || {}).map(([k, v]) => (
                <Descriptions.Item key={k} label={k}>{String(v)}</Descriptions.Item>
              ))}
            </Descriptions>
            {(() => {
              const jump = citationJump(drawer)
              return jump ? (
                <Button type="primary" size="small" style={{ marginTop: 12 }}
                  onClick={() => { setDrawer(null); location.hash = jump.hash }}>
                  {jump.label}（{jump.hash.startsWith('/B2?') ? '#/B2?chunk=…' : `#${jump.hash.slice(1)}`}）
                </Button>
                ) : (
                  <div style={{ ...dim, marginTop: 12 }}>
                    {/* DEBT(阶段2-B4页)：wiki/台账读面跳转随 B4 页票（P1-09 疑点 3 登记） */}
                    该出处族（{drawer.kind}）的读面（百科/台账读面）随对应页接线预留——出处要素见上。
                  </div>
                )
            })()}
          </>
        )}
      </Drawer>
    </div>
  )
}

function lastAssistantTurn(items) {
  for (let i = items.length - 1; i >= 0; i--) {
    if (items[i].type === 'assistant') return items[i].turn
  }
  return null
}

/** 单个 assistant 气泡（答案/澄清/审批/收场四态）。 */
function AssistantBubble({
  turn, busy, onOpenCitation, onClarify, onApproval, rejectReason, onRejectReason, onResume
}) {
  return (
    <Card size="small" style={{ marginBottom: 8 }}>
      <div style={{ marginBottom: 6 }}>
        <Tag color="blue">智能助手</Tag>
        {turn.replay && <Tag color="purple">续推/重放</Tag>}
        {turn.runId && <span style={dim}>run {turn.runId}</span>}
      </div>

      {turn.notices.map((n, i) => (
        <Alert key={i} style={{ marginBottom: 6 }} type={n.level === 'warning' ? 'warning' : 'info'}
          showIcon message={n.text} />
      ))}

      {(turn.answerText || turn.answer) && <AnswerCard turn={turn} onOpenCitation={onOpenCitation} />}

      {turn.answer == null && !turn.answerText && turn.closed == null && turn.stage != null && (
        <div style={dim}>正在处理——过程在右侧逐帧展开。</div>
      )}

      {turn.clarify && (
        <Card size="small" style={{ marginTop: 8, borderColor: '#3b8dff' }}
          title={<span>澄清帧 · interrupt 挂起（最多弹一次，两跳到终态）</span>}>
          <div style={{ fontSize: 13, marginBottom: 8 }}>{turn.clarify.question}</div>
          <Space direction="vertical" size={6} style={{ width: '100%' }}>
            {turn.clarify.choices.map(c => (
              <Button key={c.value} type={c.primary ? 'primary' : 'default'} size="small"
                block disabled={busy || turn.closed === 'done' || !!turn.chosenLabel} data-clarify={c.value}
                onClick={() => onClarify(c.value)}>
                {c.label}
              </Button>
            ))}
          </Space>
          {turn.chosenLabel && <div style={{ ...dim, marginTop: 8 }}>已选：{turn.chosenLabel}——回流续推中…</div>}
        </Card>
      )}

      {turn.approval && (
        <Card size="small" style={{ marginTop: 8, borderColor: '#faad14' }}
          title={<span>审批 interrupt · {turn.approval.title || turn.approval.scene}</span>}>
          <div style={{ fontSize: 13 }}>{turn.approval.reason}</div>
          {turn.approval.impact && <div style={{ ...dim, marginTop: 4 }}>影响：{turn.approval.impact}</div>}
          <Input size="small" style={{ marginTop: 8 }} placeholder="驳回必写理由（N12）" value={rejectReason}
            onChange={e => onRejectReason(e.target.value)} />
          <Space style={{ marginTop: 8 }}>
            <Button type="primary" size="small" disabled={busy} onClick={() => onApproval('approve')}>批准 · 续跑</Button>
            <Button danger size="small" disabled={busy} onClick={() => onApproval('reject')}>驳回</Button>
          </Space>
        </Card>
      )}

      {turn.closed === 'error' && (
        <Alert style={{ marginTop: 8 }} type="error" showIcon message={turn.errMsg || '服务端异常'} />
      )}
      {turn.closed === 'replay_truncated' && (
        <Alert style={{ marginTop: 8 }} type="warning" showIcon message={turn.truncMsg}
          description={turn.runId ? '可尝试从断点恢复（服务端只重放已持久化的内容——补不出的部分不假装续传）。' : undefined}
          action={turn.runId && <Button size="small" onClick={onResume}>从断点恢复</Button>} />
      )}
      {turn.closed === 'transport' && (
        <Alert style={{ marginTop: 8 }} type="warning" showIcon
          message="网络断开了——链路可从断点恢复，已生成的内容不丢。"
          action={turn.runId && <Button size="small" onClick={onResume}>从断点恢复</Button>} />
      )}
    </Card>
  )
}

/** 右栏思考树（五路渐进：stage 总闸→安检三道→六路→装配块→裁决→节点树）。 */
function ThinkingTree({ turn }) {
  const chainNodes = turn.nodes.filter(n => !/^(S\d|GEN)/.test(n.key))
  const innerNodes = turn.nodes.filter(n => /^(S\d|GEN)/.test(n.key))
  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        {STAGE_LABELS.map((label, i) => (
          <Tag key={label} color={turn.stage != null && turn.stage >= i ? 'blue' : 'default'}
            style={{ marginInlineEnd: 4 }}>{label}</Tag>
        ))}
      </div>

      {turn.secChecks.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          {turn.secChecks.map(s => (
            <div key={s.seq} style={{ fontSize: 13 }}>
              <span style={{ color: s.result === 'pass' ? '#52c41a' : '#ff4d4f' }}>
                {s.result === 'pass' ? '✓' : '✗'}
              </span> {s.name}
              {s.note && <span style={dim}> · {s.note}</span>}
              {s.result === 'blocked' && <Tag color="red" style={{ marginLeft: 6 }}>拦截，链路终止</Tag>}
            </div>
          ))}
        </div>
      )}

      {turn.matches.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          {turn.matches.map(m => (
            <div key={m.matcher} style={{ fontSize: 13 }}>
              <span style={{ color: m.status === 'hit' ? '#52c41a' : '#8a94a3' }}>
                {m.status === 'hit' ? '★' : '○'}
              </span> {m.matcher}
              {m.confidence && <span style={dim}> · {m.confidence}</span>}
            </div>
          ))}
        </div>
      )}

      {turn.assembly && (
        <Collapse size="small" ghost style={{ marginBottom: 8 }} items={[{
          key: 'asm', label: '装配块（给裁决的呈堂材料）',
          children: (
            <div style={dim}>
              <div>slots：{turn.assembly.slots || '—'}</div>
              {turn.assembly.anchor_line && <div>锚定：{turn.assembly.anchor_line}</div>}
              {turn.assembly.terms?.length > 0 && <div>术语：{turn.assembly.terms.join(' / ')}</div>}
              <div>候选 {turn.assembly.candidates?.length || 0} 支 · 17 链枚举随卷</div>
            </div>
          )
        }]} />
      )}

      {turn.verdict && (
        <div style={{ marginBottom: 8, fontSize: 13 }}>
          <b>裁决</b>：{turn.verdict.chain || '（澄清挂起——裁决未定）'}
          <div>{confidenceTag(turn.verdict.confidence)}{turn.verdict.slots && <span style={dim}> {turn.verdict.slots}</span>}</div>
        </div>
      )}

      <div>
        {chainNodes.map(n => <NodeRow key={n.key} node={n} lines={turn.nodeLines[n.key]} />)}
        {innerNodes.length > 0 && (
          <div style={{ marginLeft: 16, borderLeft: '2px solid rgba(255,255,255,0.12)', paddingLeft: 8 }}>
            {innerNodes.map(n => <NodeRow key={n.key} node={n} lines={turn.nodeLines[n.key]} />)}
          </div>
        )}
      </div>

      {treeEmpty(turn) && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="等待事件帧…" />}
    </div>
  )
}

function treeEmpty(turn) {
  return !turn.nodes.length && !turn.secChecks.length && !turn.matches.length && turn.stage == null
}
