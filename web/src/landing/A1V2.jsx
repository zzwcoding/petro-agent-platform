/**
 * 落地树 · A1V2 问一问V2（对接 V2 后端 /api/v2/*——specs/agent-loop.md 三端点＋V2-73/74 读口）。
 *
 * 页面骨架与问一问V1（landing/A1.jsx）同构三栏（Owner 拍板：逻辑/样式统一，V2 只换芯）；
 * 对话任务模型对齐 ZCode 会话面（Owner 2026-10-13 拍板：一个多轮追问链＝一个对话任务）：
 * 左栏＝对话列表（V2-74 followup_of 链分组——一链一行，行＝链根问句标题＋最新轮状态/轮数/时间，
 * 最近活跃在前）；中栏＝对话流（选中对话＝全轮次连续呈现＋新轮流式追加；未选中＝实时流）；
 * 右栏＝思考过程（实时回合过程帧 ↔ 选中对话最新轮 steps 两态切换）。
 *
 * 对话任务状态机（V2-74；前拍 R1-R4 演进而来）：
 * - 打开对话（左栏整行点击）：中栏呈现该链全部轮次（问＋答＋状态；挂起轮出批准/驳回卡、
 *   失败轮出告警），右栏拉最新轮过程步（getRunV2）；实时流清零，行高亮（data-selected）。
 * - 续聊（输入默认追问本对话）：锚武装到对话内最新 completed 轮（后端 _seed_history 只认
 *   completed——不存在 404／未收口 409；不变量：followup.runId 恒指向已收口 run）；发送后
 *   新轮流式追加在轮次之后，收口即成为该对话新轮（列表行轮数＋1——loadRuns 复拉重分组）。
 *   追问回合收口态闸四形枚举：
 *   · done 且本腿无 ask 帧且无 run_failed notice＝新 run 已收口 → 锚推进到它（链式追问
 *     历史不断链——前轮线程历史含此前全部轮次）；
 *   · ask 帧在场＝挂起 → 立即拆锚（续推走挂起卡，续推收口后锚随回武装）；
 *   · 引擎异常腿：executor 落库 failed 后 bus 干净收束、桥面 stream.error 为空照发 done
 *     （appv2/runtime/executor.py:380-385 → api/bridge.py:149-156）——run_failed notice 在场
 *     → 锚保持原 completed run（失败轮不入锚链；卡面 Alert 如实告警）；
 *   · 流内失败/传输断 → 锚保持原 completed run（重试仍打同一线程）。边界缝如实登记：
 *     传输断若发生在服务端已实际收口之后，该成功轮不入锚链——后续追问播种史缺该轮；
 *     单端主链不可达，多端边界现形，暂不硬修。
 * - 新会话（左栏「＋新会话」＝唯一显式退出对话入口）：清对话选中＋实时流＋锚；输入＝
 *   独立新问（followup_of 空串＝新链根）。
 * - 刷新现场恢复（V2-78——Owner 拍板「刷新后两对话仍在同一对话链」）：线程锚＋对话
 *   选中进 sessionStorage——刷新后追问仍并原链；挂起轮经 GET run 的 pending_ask 还原
 *   反问选项/审批面（点选项即续推该轮）。发送时锚兜底推导：对话开着而无锚（挂起拆过/
 *   恢复态）＝锚到对话内最新收口轮——输入永远并入当前对话。
 * - 后端硬约束（appv2/runtime/executor.py _seed_history）：前轮须 completed；waiting_ask
 *   轮走挂起卡批准/驳回续推。链根不在列表窗内＝该轮自成一对话行（分组窗界兜底，如实呈现）。
 * V1 专属面不设——DEBT(V2-00)：@资产（V1 端点 6）不在 V2 合同内；逐帧回放随会话面票补。
 * 挂起判定铁律：ask 帧在场＝等人工（ask 帧后照发 done——挂起看 ask 帧不看 done）。
 *
 * 答案面（EB2-D4 答案友好化）：模型答案是 Markdown（真机答案真形＝**粗体**当小标题＋
 * `- ` 清单＋逐行引标 [n]），正文由 landing/AnswerView.jsx（marked lexer→React 元素）
 * 渲染，不再 pre-wrap 显示记号；正文 [n] 点击＝开引用抽屉并高亮/滚动到对应 index 条目。
 * 历史轮次（DB 行 answer）无引用数据可查，不传 onCite＝引标不切分（纯文本原样）。
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
  getRunV2, listRunsV2, postAskV2, postResumeV2, resumeBodyFromAskFrame
} from '../api/chatV2.js'
import { helpIcon, dim } from '../components/helpIcon.jsx'
import DecisionTreeV2, { V2_SCENARIOS } from '../pages/DecisionTreeV2.jsx'
import AnswerView from './AnswerView.jsx'
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

// 状态文案（词表单源：左栏行/轮次卡/徽标同用一套词）
const STATUS_TEXT = {
  running: '运行中', waiting_ask: '待确认', completed: '已完成', failed: '失败'
}

function statusTag(status) {
  const color = status === 'completed' ? 'green'
    : status === 'waiting_ask' ? 'gold'
      : status === 'failed' ? 'red' : 'blue'
  return <Tag color={color} style={{ fontSize: 10, flexShrink: 0 }}>{STATUS_TEXT[status] ?? status}</Tag>
}

/** ISO 时间戳 → 「MM-DD HH:mm」（列表行 2／轮次卡时间）。 */
function fmtTime(iso) {
  return (iso || '').replace('T', ' ').slice(5, 16)
}

/**
 * runs → 对话任务分组（V2-74 对话任务面）：followup_of 链上溯定链根；链根不在
 * 列表窗内＝该轮自成一对话行（分组窗界兜底——如实呈现，不虚构归属）。
 * 返回 [{rootId, title, rounds（created_at 升序）, latest}]，按最新轮时间降序。
 */
function buildThreads(runs) {
  const byId = new Map(runs.map(r => [r.run_id, r]))
  const rootCache = new Map()
  const rootOf = r => {
    if (rootCache.has(r.run_id)) return rootCache.get(r.run_id)
    const seen = new Set()
    let cur = r
    while (cur.followup_of && byId.has(cur.followup_of) && !seen.has(cur.run_id)) {
      seen.add(cur.run_id)
      cur = byId.get(cur.followup_of)
    }
    rootCache.set(r.run_id, cur.run_id)
    return cur.run_id
  }
  const groups = new Map()
  for (const r of runs) {
    const root = rootOf(r)
    if (!groups.has(root)) groups.set(root, [])
    groups.get(root).push(r)
  }
  const threads = [...groups.values()].map(rs => {
    rs.sort((a, b) => (a.created_at < b.created_at ? -1 : 1))
    return { rootId: rs[0].run_id, title: rs[0].question || rs[0].run_id, rounds: rs, latest: rs[rs.length - 1] }
  })
  threads.sort((a, b) => (a.latest.created_at < b.latest.created_at ? 1 : -1))
  return threads
}

const SESSION_KEY = 'a1v2.session' // V2-78 刷新现场恢复键（rootId＋线程锚）

export default function A1V2Landing() {
  const [items, setItems] = useState([]) // 实时回合流 {type:'user'|'assistant', text?, turn?}
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [runs, setRuns] = useState([]) // 左栏最近任务（V2-73 读口——V2-74 按链分组）
  const [runsReady, setRunsReady] = useState(false) // 列表数据在位旗标——失败态≠空库（计数行只在数据在位时渲染）
  // V2-78 刷新现场恢复：初始值从 sessionStorage 还原（本页会话级——新标签页＝新会话态）
  const [thread, setThread] = useState(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null')
      return saved?.rootId ? { rootId: saved.rootId } : null
    } catch { return null }
  }) // 选中的对话任务 {rootId}——null＝未选（新会话态）
  const [process, setProcess] = useState(null) // 右栏历史过程 {runId,steps,stepsLoading,stepsError}（选中对话＝最新轮）
  const [askFrames, setAskFrames] = useState({}) // 挂起轮帧 {runId: AskFrame}——GET run pending_ask 还原（V2-78）
  const [citeTurn, setCiteTurn] = useState(null)
  const [citeFocus, setCiteFocus] = useState(null) // 引标联动定位态 {index}（正文 [n] 点击——抽屉高亮/滚动；本体化让重复点同一条也重走滚动）
  const [treeOpen, setTreeOpen] = useState(false)
  const [active, setActive] = useState(null)
  const [followup, setFollowup] = useState(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null')
      return saved?.followup?.runId ? saved.followup : null
    } catch { return null }
  }) // 输入线程锚 {runId,label}——恒指向已收口 run（收口态闸见头注）；刷新恢复
  const busyRef = useRef(false)
  const convRef = useRef(null)

  // V2-78 现场持久化：对话选中＋线程锚随变随存（刷新后 restore 初始化器读回）
  useEffect(() => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({
      rootId: thread?.rootId ?? null, followup
    }))
  }, [thread, followup])

  // 引标联动（EB2-D4）：正文 [n] 点击后抽屉已开——把对应条目滚进视野（高亮由 citeFocus 出态）。
  // scrollIntoView 在 jsdom 缺实现（?.）——测试面不因环境桩缺失而炸。
  useEffect(() => {
    if (!citeTurn || !citeFocus) return
    const el = document.getElementById(`cite-${citeFocus.index}`)
    if (el?.scrollIntoView) el.scrollIntoView({ block: 'center' })
  }, [citeTurn, citeFocus])

  const threads = buildThreads(runs)
  const openThreadObj = thread ? (threads.find(t => t.rootId === thread.rootId) ?? null) : null
  // 选中高亮：选中对话优先；否则锚 run 所属对话（独立新问成链后高亮跟随）
  const rootByRun = new Map()
  for (const t of threads) for (const r of t.rounds) rootByRun.set(r.run_id, t.rootId)
  const selectedThreadId = thread?.rootId ?? (followup ? (rootByRun.get(followup.runId) ?? null) : null)
  // 轮次去重：流式新轮在场期间以其为准（DB 侧同 run 行不重复渲染）
  const liveRunIds = new Set(
    items.filter(it => it.type === 'assistant' && it.turn?.runId).map(it => it.turn.runId)
  )

  const loadRuns = () => {
    listRunsV2(20).then(r => { setRuns(r); setRunsReady(true) })
      .catch(() => { setRunsReady(false) }) // 失败不销毁已有行（V1 T7 韧性同款）；撤计数行——不把失败呈现成空库
  }
  useEffect(() => { loadRuns() }, [])

  // V2-78 恢复拍：刷新还原的对话在列表落位后补拉右栏过程步（process 在手即跳过）
  useEffect(() => {
    if (!runsReady || !thread || process) return
    const t = threads.find(x => x.rootId === thread.rootId)
    if (t) fetchProcess(t.latest.run_id)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 恢复拍一次性（threads 后续变化不重取）
  }, [runsReady, thread])

  /** 回合收束统一出口：解忙＋左栏复拉（成功/失败/传输断/预流错误全腿同闸——
   * 失败 run 已落库，恰是最需回看过程步的对象；V1 runStream finally 同口径）。 */
  function settleTurn() {
    busyRef.current = false
    setBusy(false)
    loadRuns()
  }

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

  function handlers(opts = {}) {
    let askSeen = false // 本腿流挂起帧在场（挂起看 ask 帧不看 done——收口推进的判据）
    let runFailed = false // 引擎异常腿判据：run_failed notice 随行、流尾照发 done（bridge.py:149-156）
    return {
      onFrame: f => {
        setLastTurn(t => reduceV2Frame(t, f)); scrollBottom()
        if (f.event === 'session' && f.data?.run_id && opts.onSessionRunId) {
          opts.onSessionRunId(f.data.run_id)
        }
        if (f.event === 'ask') {
          askSeen = true
          if (opts.onSuspended) opts.onSuspended()
        }
        if (f.event === 'notice' && f.data?.type === 'run_failed') {
          runFailed = true // 判据字面量与归约器同源（a1v2Reducer done 三分）
        }
        // 收口推进（仅追问形注册）：done 且本腿无挂起且非引擎异常腿＝新 run 已收口——
        // 锚推进到它；挂起腿不推进（onSuspended 已拆锚），引擎异常腿不推进（否则下一发追问必 409）
        if (f.event === 'done' && !askSeen && !runFailed && opts.onRunCompleted) {
          opts.onRunCompleted()
        }
      },
      onDone: () => { settleTurn() },
      onError: d => {
        setLastTurn(t => ({ ...t, closed: 'error', runStatus: 'failed', errMsg: d?.message || '流内错误' }))
        settleTurn()
      },
      onReplayTruncated: d => {
        setLastTurn(t => ({ ...t, closed: 'replay_truncated', errMsg: d?.message || '重放截断' }))
        settleTurn()
      },
      onTransportError: err => {
        setLastTurn(t => ({ ...t, closed: 'transport', errMsg: errText(err) }))
        settleTurn()
      }
    }
  }

  /** 右栏历史过程（选中对话＝最新轮 steps；getRunV2 失败内联告警可重拉）。 */
  function fetchProcess(runId) {
    setProcess({ runId, steps: [], stepsLoading: true, stepsError: '' })
    getRunV2(runId).then(
      d => {
        setProcess(p => (p && p.runId === runId ? { ...p, steps: d.steps || [], stepsLoading: false } : p))
        setAskFrames(m => ({ ...m, [runId]: d.pending_ask ?? null })) // V2-78 挂起帧随行还原
      },
      err => setProcess(p => (p && p.runId === runId
        ? { ...p, stepsLoading: false, stepsError: err instanceof ApiError ? errText(err) : String(err) } : p))
    )
  }

  /** 左栏整行点击＝打开该对话任务（V2-74）：中栏全轮次＋右栏最新轮过程步＋行高亮；
   * 实时流清零（轮次以 DB 行呈现，新轮流式追加其后）；锚武装到对话内最新 completed 轮
   * （后端 followup 前轮须 completed——全链无收口轮＝不武装，输入区如实说明）。
   * 已知代价（注记非必修）：打开期间该链他端变化（如另一标签页续推收口）不自动刷新
   * ——跨端边界才现，单端主链不可达（本端续推路径都经 loadRuns 复拉）。 */
  /** 对话内最新收口轮 → 线程锚（无收口轮＝null——发送时兜底推导用）。 */
  function latestCompletedAnchor(t) {
    if (!t) return null
    const c = [...t.rounds].reverse().find(r => r.status === 'completed')
    return c ? { runId: c.run_id, label: c.question || '' } : null
  }

  function openThread(t) {
    if (busyRef.current) return
    setThread({ rootId: t.rootId })
    setItems([])
    setFollowup(latestCompletedAnchor(t))
    fetchProcess(t.latest.run_id)
    // V2-78：挂起轮逐一取挂起帧（通常 ≤1 轮）——反问选项/审批面还原
    for (const r of t.rounds) {
      if (r.status !== 'waiting_ask' || askFrames[r.run_id] !== undefined) continue
      getRunV2(r.run_id).then(
        d => setAskFrames(m => ({ ...m, [r.run_id]: d.pending_ask ?? null })),
        () => setAskFrames(m => ({ ...m, [r.run_id]: null }))
      )
    }
  }

  /** ＋新会话（唯一显式退出对话入口）：清对话选中＋历史过程＋实时流＋锚。 */
  function startNewSession() {
    setThread(null)
    setProcess(null)
    setItems([])
    setFollowup(null)
    setInput('')
  }

  function ask(text) {
    const question = (text || '').trim()
    if (!question || busyRef.current) return
    setActive(routeOf(question))
    // 发送时刻的线程锚：显式锚优先；对话开着而无锚（挂起拆过/刷新恢复态）＝
    // 兜底推导到对话内最新收口轮——输入永远并入当前对话（V2-78）。
    const threadAnchor = followup ?? latestCompletedAnchor(openThreadObj)
    const turn = newTurnV2('ask', question)
    setItems(prev => [...prev,
      { type: 'user', text: question, key: `u-${prev.length}` },
      { type: 'assistant', turn, key: `a-${prev.length}` }
    ])
    setInput('')
    busyRef.current = true; setBusy(true)
    let streamedRunId = ''
    Promise.resolve(postAskV2(
      { question, ...(threadAnchor ? { followupRunId: threadAnchor.runId } : {}) },
      // V2-78 链连续（独立首问也武装）：收口推进回调对所有提问注册——独立首问
      // 收口后锚随之武装，下一发并入本对话（否则每段对话的第一问永远是断链根，
      // 真机 19:31→19:32「查一下井的数据→查一下 日常油」分家实录）。
      handlers({
        onSessionRunId: id => { streamedRunId = id },
        // 收口态闸：挂起＝锚不得停未收口 run——回锚到本问的锚（standalone＝null）
        onSuspended: () => setFollowup(threadAnchor),
        // done 且本腿无挂起＝新 run 已收口——锚推进到它（链式追问历史不断链）
        onRunCompleted: () => { if (streamedRunId) setFollowup({ runId: streamedRunId, label: question }) }
      })
    )).catch(err => {
      setLastTurn(t => ({
        ...t, closed: 'error', runStatus: 'failed',
        errMsg: err instanceof ApiError ? errText(err) : String(err)
      }))
      settleTurn()
    })
  }

  /** 挂起续推：同回合续写（实时挂起卡的澄清选项/审批按钮）。 */
  function resumeLive(chosen) {
    const item = [...items].reverse().find(it => it.type === 'assistant')
    const turn = item?.turn
    if (!turn?.askFrame || !turn.runId || busyRef.current) return
    const body = resumeBodyFromAskFrame(turn.askFrame, chosen)
    setLastTurn(t => ({ ...t, askFrame: null }))
    busyRef.current = true; setBusy(true)
    Promise.resolve(postResumeV2(turn.runId, body, handlers({
      // 续推收口 → 锚随回武装（对话连续——挂起轮收口后输入继续追问该对话）；
      // 续推再挂起（澄清 r2 等）→ 锚回对话内最新收口轮（不落未收口 run）。
      onSuspended: () => setFollowup(latestCompletedAnchor(openThreadObj)),
      onRunCompleted: () => setFollowup({ runId: turn.runId, label: turn.question || '' })
    })))
      .catch(err => {
        setLastTurn(t => ({
          ...t, closed: 'error', runStatus: 'failed',
          errMsg: err instanceof ApiError ? errText(err) : String(err)
        }))
        settleTurn()
      })
  }

  /** 对话视图中挂起轮的批准/驳回——续推转实时新轮（轮次卡让位流式卡，对话视图驻留）。 */
  /** 对话视图中挂起轮的续推（V2-78 两形）：clarify＝点反问选项；approval＝批准/驳回。
   * 续推转实时新轮（轮次卡让位流式卡，对话视图驻留）；收口锚武装到该轮。 */
  function resumeRound(r, body) {
    if (busyRef.current) return
    const turn = newTurnV2('resume', r.question)
    turn.runId = r.run_id
    turn.resumed = true
    setItems(prev => [...prev,
      { type: 'user', text: `（续推历史任务）${r.question}`, key: `u-${prev.length}` },
      { type: 'assistant', turn, key: `a-${prev.length}` }
    ])
    busyRef.current = true; setBusy(true)
    Promise.resolve(postResumeV2(r.run_id, body, handlers({
      onSuspended: () => setFollowup(latestCompletedAnchor(openThreadObj)),
      onRunCompleted: () => setFollowup({ runId: r.run_id, label: r.question || '' })
    })))
      .catch(err => {
        setLastTurn(t => ({
          ...t, closed: 'error', runStatus: 'failed',
          errMsg: err instanceof ApiError ? errText(err) : String(err)
        }))
        settleTurn()
      })
  }

  /** 中栏条目渲染（实时回合壳）。 */
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

  /** 打开引用抽屉（EB2-D4）：index 传自正文 [n] 引标＝高亮并滚动到该条；无 index（「引用材料（n）」按钮）＝不高亮。 */
  function openCitation(turn, index) {
    setCiteTurn(turn)
    setCiteFocus(index == null ? null : { index }) // 每次点击出新对象＝重复点同一条也重走滚动拍
  }

  function renderTurn(turn) {
    const failing = turn.closed === 'error' || turn.closed === 'transport'
    // 引擎异常腿：run_failed notice 随行、流尾照发 done——run 已落库 failed，
    // 卡面如实告警（该腿无 error 帧 errMsg 空，告警文案取 notice content）
    const runFailedNotice = turn.notices.find(n => n.type === 'run_failed')
    const engineFailed = turn.closed === 'done' && turn.runStatus === 'failed'
    return (
      <div>
        {turn.resumed && <Tag style={{ marginBottom: 6 }}>续推</Tag>}
        {failing && <Alert type="error" showIcon message={turn.errMsg || '请求失败'} style={{ margin: '6px 0' }} />}
        {engineFailed && (
          <Alert type="error" showIcon
            message={runFailedNotice?.content || '运行失败——任务已落库，可在左侧对话回看过程步。'}
            style={{ margin: '6px 0' }} />
        )}
        {turn.notices.map((n, i) => <NoticeRow key={i} n={n} />)}
        {/* V2-77 理解旁白灰条（B 项）：理解步叙述独立折叠——中间栏答案面只剩真回答 */}
        {turn.understanding && (
          <Collapse size="small" style={{ margin: '6px 0' }} items={[{
            key: 'understanding',
            label: <span style={dim}>系统理解</span>,
            children: <div style={dim}>{turn.understanding}</div>
          }]} />
        )}
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
          <AnswerView content={turn.answerText} onCite={idx => openCitation(turn, idx)} />
        )}
        {!turn.answerText && !failing && turn.runStatus === 'running' && <Spin size="small" />}
        {turn.citations.length > 0 && (
          <Button size="small" type="link" style={{ paddingLeft: 0, marginTop: 6 }}
            onClick={() => openCitation(turn, null)}>
            {`引用材料（${turn.citations.length}）`}
          </Button>
        )}
      </div>
    )
  }

  /** 挂起轮续推卡（V2-78 按帧分形）：clarify＝反问＋选项（点选续推——刷新后还原）；
   * external_table_approval＝批准/驳回；帧未取到＝退回批准/驳回形（旧行为）。 */
  function renderSuspendCard(r) {
    const af = askFrames[r.run_id]
    if (af?.kind === 'clarify') {
      return (
        <Card size="small" style={{ margin: '8px 0 0', borderColor: '#4a9dff' }} title={
          <span>系统反问{helpIcon('该轮挂起等你确认口径或补充信息——点选项即续推本轮')}</span>}>
          <div style={{ marginBottom: 8 }}>{af.prompt}</div>
          <Space wrap>
            {(af.options || []).map(op => (
              <Button key={op} size="small" type="primary" ghost disabled={busy}
                onClick={() => resumeRound(r, { kind: 'clarify', choice: op })}>{op}</Button>
            ))}
          </Space>
        </Card>
      )
    }
    return (
      <Card size="small" style={{ margin: '8px 0 0', borderColor: '#e8b339' }} title={
        <span>{af?.kind === 'external_table_approval' ? '越集审批' : '该轮挂起待确认'}{helpIcon('批准/驳回即转实时续推，收口后可继续追问本对话')}</span>}>
        {af?.kind === 'external_table_approval' && af.detail?.tables && (
          <div style={dim}>外部表：{af.detail.tables.join('、')}</div>
        )}
        <Space wrap>
          <Button size="small" type="primary" disabled={busy}
            onClick={() => resumeRound(r, { kind: 'approval', decision: 'approve' })}>批准</Button>
          <Button size="small" danger disabled={busy}
            onClick={() => resumeRound(r, { kind: 'approval', decision: 'reject' })}>驳回</Button>
        </Space>
      </Card>
    )
  }

  /** 对话轮次卡（DB 行——打开对话时的既有轮；挂起轮按帧出续推卡，失败轮出告警）。 */
  function renderRound(r) {
    return (
      <div key={r.run_id}>
        <Card size="small" style={{ background: 'rgba(22,119,255,0.12)', marginBottom: 8 }}>
          <b>我：</b>{r.question}
        </Card>
        <Card size="small" style={{ marginBottom: 8 }}>
          <div style={{ marginBottom: 6 }}>
            {statusTag(r.status)}<span style={dim}>{` · ${fmtTime(r.created_at)}`}</span>
          </div>
          <AnswerView content={r.answer || (r.status === 'completed' ? '（无答案正文）' : '（未收口——无答案文本）')} />
          {r.status === 'waiting_ask' && renderSuspendCard(r)}
          {r.status === 'failed' && (
            <Alert type="error" showIcon message="该轮运行失败——过程步见右侧；可继续追问重试。"
              style={{ margin: '8px 0 0' }} />
          )}
        </Card>
      </div>
    )
  }

  /** 右栏过程帧源（实时回合优先；选中对话且无实时回合＝最新轮 steps——两态切换）。 */
  const lastTurn = items.length > 0
    ? [...items].reverse().find(it => it.type === 'assistant')?.turn ?? null
    : null

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'stretch', height: '100%' }}>
      {/* ── 左栏 · 对话（V2-74 对话任务面——followup_of 链分组，一链一行） ── */}
      <Card
        title={<span>对话{helpIcon('一个多轮追问链＝一个对话任务：行＝链根问句，行 2＝最新轮状态/轮数/时间；整行点击打开对话——中栏全轮次、输入默认继续本对话（上下文自动继承）')}</span>}
        extra={(
          <Button size="small" type="text" disabled={busy} onClick={startNewSession}>＋新会话</Button>
        )}
        size="small"
        style={{ width: 250, flexShrink: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 0, overflowY: 'auto' } }}>
        {/* UI-14 同位纪律：计数行只在数据在位时渲染——拉取失败≠空库（不撒「共 0 条」的谎） */}
        {runsReady && <div style={{ ...dim, marginBottom: 4 }}>{`共 ${threads.length} 个对话`}</div>}
        <List size="small" dataSource={threads} locale={{ emptyText: '暂无数据' }}
          renderItem={t => {
            const sel = selectedThreadId === t.rootId
            return (
              <List.Item data-selected={sel ? 'true' : 'false'}
                style={{
                  cursor: busy ? 'wait' : 'pointer', padding: '4px 6px', borderRadius: 6,
                  background: sel ? 'rgba(22,119,255,0.18)' : 'transparent' // 选中行高亮（与未选中可辨）
                }}
                onClick={() => openThread(t)}>
                <div>
                  <div style={{ fontSize: 13 }}>
                    {t.latest.status === 'waiting_ask' && (
                      <QuestionCircleOutlined style={{ color: '#e8b339', marginRight: 6 }} />
                    )}
                    {(t.title || '').slice(0, 18)}
                  </div>
                  <div style={dim}>
                    {`${STATUS_TEXT[t.latest.status] ?? t.latest.status} · ${t.rounds.length} 轮 · ${fmtTime(t.latest.created_at)}`}
                  </div>
                </div>
              </List.Item>
            )
          }} />
      </Card>

      {/* ── 中栏 · 对话流（选中对话＝全轮次＋新轮流式追加；未选＝实时流） ── */}
      <Card size="small" style={{ flex: 1, minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 320, display: 'flex', flexDirection: 'column' } }}>
        <div ref={convRef} style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: 4 }}>
          {openThreadObj ? (
            <>
              <div style={{ ...dim, marginBottom: 8 }}>
                {`对话 · ${openThreadObj.rounds.length} 轮 —— 输入默认继续本对话`}
              </div>
              {openThreadObj.rounds.map(r => (liveRunIds.has(r.run_id) ? null : renderRound(r)))}
              {renderItems(items)}
            </>
          ) : (
            <>
              {items.length === 0 && (
                <div style={{ ...dim, textAlign: 'center', marginTop: 80 }}>
                  输入问题开始（挂起后在本栏确认；左侧点对话可接着聊）
                </div>
              )}
              {renderItems(items)}
            </>
          )}
        </div>
        <div style={{ marginTop: 10 }}>
          {/* 对话内全链无收口轮＝锚无从武装（后端 409）——如实说明当前输入＝新会话 */}
          {openThreadObj && !followup && (
            <div style={{ ...dim, marginBottom: 6 }}>
              本对话暂无已收口轮——追问不可用；当前输入＝新会话。
            </div>
          )}
          <Space.Compact style={{ width: '100%' }}>
            <Input placeholder={followup ? '追问此对话（Enter 发送）' : '输入问题（Enter 发送）'}
              value={input} disabled={busy}
              onPressEnter={e => { if (e.nativeEvent.isComposing) return; ask(input) }}
              onChange={e => setInput(e.target.value)} />
            <Button type="primary" icon={<SendOutlined />} loading={busy} onClick={() => ask(input)}>发送</Button>
          </Space.Compact>
        </div>
      </Card>

      {/* ── 右栏 · 思考过程（实时回合过程帧 ↔ 选中对话最新轮 steps 两态） ── */}
      <Card title={<>思考过程 <ApartmentOutlined style={{ color: '#8a94a3' }} /></>} size="small"
        extra={<Button size="small" icon={<ApartmentOutlined />} onClick={() => setTreeOpen(true)}>决策树</Button>}
        style={{ width: 330, flexShrink: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' } }}>
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: 4 }}>
          {!lastTurn && process ? (
            <>
              <div style={{ ...dim, marginBottom: 4 }}>{`历史过程 · ${process.runId}`}</div>
              {process.stepsLoading && <Spin size="small" />}
              {/* 步数只在加载落定后出——加载中不显假「0 步」（先假后真不诚实） */}
              {!process.stepsLoading && !process.stepsError && (
                <div style={{ ...dim, marginBottom: 4 }}>{`${process.steps.length} 步`}</div>
              )}
              {process.stepsError && (
                <Alert type="error" showIcon message={process.stepsError} style={{ margin: '6px 0' }} />
              )}
              {process.steps.map(s => (
                <div key={s.seq} style={{ fontSize: 12, marginBottom: 3 }}>
                  <Tag style={{ marginRight: 6 }}>{s.seq}</Tag>{s.title}
                  {s.step && <span style={dim}>{` · ${s.step}`}</span>}
                </div>
              ))}
            </>
          ) : (
            <>
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
            </>
          )}
        </div>
      </Card>

      {/* 引用抽屉（EB2-D4：正文 [n] 引标点击＝开此抽屉＋高亮/滚动到对应 index 条目） */}
      <Drawer title="引用材料" width={480} open={Boolean(citeTurn)}
        onClose={() => { setCiteTurn(null); setCiteFocus(null) }}>
        {(citeTurn?.citations || []).map(c => {
          const mat = (citeTurn.materials || []).find(m => m.index === c.index)
          const focused = citeFocus?.index === c.index // 正文引标联动定位的高亮态
          return (
            <Card key={c.index} id={`cite-${c.index}`} size="small"
              style={{
                marginBottom: 8,
                ...(focused ? { borderColor: '#4a9dff', boxShadow: '0 0 0 2px rgba(74,157,255,0.25)' } : {})
              }}
              title={(
                <span>
                  [{c.index}] {c.source}<Tag style={{ marginLeft: 6 }}>{c.trust}</Tag>
                  {focused && <Tag color="blue" style={{ marginLeft: 6 }}>已定位</Tag>}
                </span>
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
