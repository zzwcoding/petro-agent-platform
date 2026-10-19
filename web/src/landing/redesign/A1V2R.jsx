/**
 * A1V2R · 问一问V2 **真流页**（落地树 `#/A1V2`——FE-05 临时路由转正，见 registry.js）。
 *
 * 形态：整页一条垂直追加时间线（Owner 2026-10-17 拍板的串行链条模型），每轮三个串行块：
 *   1) **用户输入块**（问句气泡）
 *   2) **系统执行流水线块**（ExecutionPipeline：typed 事件流，运行中默认展开、答案一开始流
 *      就自动收起成一行摘要，可点开回看全程）
 *   3) **系统回答块**（A 级 notice 紧凑 Alert → 正文流 AnswerView →
 *      核验/档案小字 RunMetaLine）；运行中此块＝「正在作答…」占位
 *      （打磨批②：追加面 SupplementBlocks 在中栏整个移除；split 只留右栏）
 *      （打磨批⑨：中栏血缘／查询口径框整块移除——同一张 LineageCard 只在右栏
 *      「引用与口径」出一份，中栏不重复；右栏数据源见 CitationPanel.jsx:174）。
 *
 * 中栏三来源一统（FE-05 去夹具轮后）：**本会话提问流**（send→SSE→链条追加，含刷新重连推入轮）
 * ／**选中链**（左栏点行的历史链——FE-04 L3，选中即切换视图）。**追问不清链视图**（Owner
 * 2026-10-19 反馈修：原 `send()` 里 `setChain(null)` 会把屏上已有对话整段抹掉）：选中链后追问＝
 * 中栏＝**链轮次在前 ＋ 该链之后新提问轮在后**同一条时间线（`viewTurns` 单点派生），追问锚＝
 * 该视图里最新已收口轮——链在屏上、新轮接在下方，内容不消失。
 * 发送接线（本票核心）：输入区 send() → postAskV2 → 帧流直进 FE-01 reducer 归一出 TurnShape
 * 追加到本会话流（live 与 replay 同形状，H1）；追问＝带 followupRunId（当前视图最新的**已收口**
 * run——后端前轮须 completed，409 时输入区 Alert 透传 message）。时长＝页面临时面
 * durationByRun[runId]（本地计时，收口时算——TurnShape 无此键）。
 * 三场景归一（H5 零分支）：`TurnChain` 是页面与 `one_shape_three_scenarios` 测试共用的唯一轮
 * 渲染件——live/replay（归约器输出）与 history（historyAdapter 输出）同 props 路径，不判 kind；
 * phase 渲染期 phaseOf(turn) 派生（FE-01 导出，turn 不携带 phase 字段）。
 *
 * 重连接线（FE-03——specs/frontend-redesign.md 行为约定 R1–R4，落码见 useRunningRun.js）：
 * mount 调一次 restoreRunning()——持久化 running run 的全帧重放重连／404 终态灰条／waiting_ask
 * 挂起还原；挂起卡选项点击＝resumeEntry 续答通路（本腿新帧直进同一 reducer）。
 *
 * 历史列真接与选中拉链（FE-04——行为约定 L1–L3）：左栏 ThreadList 数据源切内部态＋listRunsV2
 * （读口注入，真源 appv2/api/chat.py list_runs——无 offset，上拉＝扩大 limit 重拉全量）；选中行＝
 * collectChain 拉链（链分组语义：root＝followup_of 空或指向窗口外、成员＝窗口内逐跳可达、
 * created_at 升序）→ 每轮 getRunV2 → adaptHistoryTurn 归一（404 轮降级 adaptHistoryTurn(r, null)
 * ＋errorFrame{run_unreachable}，文案与 R3 合成轮同词）→ 中栏切该链轮次；链内挂起轮＝
 * resumeChainTurn 续答通路（FE-04 遗留，本票接通——续答帧落回该链轮）。右栏 panelTurn＝当前
 * 视图最新轮（`viewTurns` 末位——链尾或链后新提问轮；点正文 [n] 切轮定位机制不变）。
 *
 * 边界（未变部分）：右栏 CitationPanel（人话面板）内容与右栏展开宽度 360、决策树入口均不动
 * （Owner 2026-10-17 拍板「4 宽度你看着办, 决策树留着」）；**右栏常驻性**于 2026-10-19 打磨批⑫
 * 改为**不展示时完全不可见**：默认整卡不渲染（无竖条无常驻入口），点正文 `[n]` 才出**右侧悬浮面板**
 * （`position: fixed` 覆在内容上、不占版面——中栏恒占满），面板头部「×」关掉。
 * 空态纪律：各项无数据＝该位不渲染（组件内实现，本页只透传）。
 *
 * Owner 反馈回归（旧页 608267b A1V2.jsx 对照）：
 * - **＋新会话**（左栏 Card extra，旧页 :548/:311-317 同义）＝唯一显式退出对话入口：清对话选中
 *   ＋本会话流（clearEntries）＋输入＋流开前错误；不涉 sessionStorage running run 键。
 * - **追问不清链视图**（Owner 2026-10-19 反馈）：选中链后追问，屏上已有对话照旧在场（链轮＋
 *   新轮同一条时间线）；选中行高亮也不清（仍在同一段对话里）。
 * - **收口刷新左栏**（V2-73 原页「onDone 后刷新」的回归）：提问腿受理（session 帧——run 行受理
 *   即落库，左栏当场出现「运行中」新行）与收口各 `refreshThreads()` 一次；挂起续答腿／链内续答
 *   腿收口亦各一次——新轮立刻进左栏。刷新键不动选中态（`selectedRunId`／`chain` 独立）。
 * - **中栏贴底跟随**（旧页 :226-237 每帧 scrollBottom 的柔和版）：发送置 stickRef；滚动离底
 *   ≥80px 即解除跟随（上翻阅读不被拽回）；entries/chain 变化时贴底态才滚到底。
 * - **右栏悬浮面板**（Owner 2026-10-19 打磨批⑫）：不展示时**完全不可见**（整卡不渲染）；点正文
 *   `[n]` 才出**右侧悬浮面板**并定位该条（唯一入口）。关闭三途：面板头部「×」／**点面板之外**
 *   （组件内 `document` mousedown 判——引标 `[n]` 与 Modal 门户豁免）／**切换对话**（点左栏历史行
 *   `onSelect`、＋新会话 `startNewSession` 各显式收一次）。面板浮在内容之上、不占版面（中栏恒占满）。
 *   无 `[n]` 的轮次没有任何入口——其「查询口径」卡随之不可达（如实登记）。
 */
import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Card, Input, Space, Spin } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import { ApiError, errText } from '../../api/client.js'
import { getRunV2, postAskV2, postResumeV2, resumeBodyFromAskFrame } from '../../api/chatV2.js'
import { dim, helpIcon } from '../../components/helpIcon.jsx'
import { newTurnV2, phaseOf, reduceV2Frame } from '../a1v2Reducer.js'
import AnswerView from '../AnswerView.jsx'
import CitationPanel from './CitationPanel.jsx'
import CiteHoverCard from './CiteHoverCard.jsx'
import { chainRootId } from './cites.js'
import ExecutionPipeline from './ExecutionPipeline.jsx'
import { adaptHistoryTurn } from './historyAdapter.js'
import { NoticeAlerts } from './NoticeBand.jsx'
import RunMetaLine from './RunMetaLine.jsx'
import ThreadList from './ThreadList.jsx'
import { useRunningRun } from './useRunningRun.js'

/** 空轮（无会话轮时的右栏空态载体——citations/materials 全空，面板出「本回合无引用」）。 */
const EMPTY_TURN = newTurnV2('ask', '')

/** 链条节点（时间轴视觉——左侧竖线＋圆点，把三轮三块串成一条）。 */
function ChainBlock({ testid, dot = 'var(--pa-primary)', children }) {
  return (
    <div data-testid={testid} style={{ position: 'relative', paddingLeft: 14, marginBottom: 8 }}>
      <span style={{
        position: 'absolute', left: 0, top: 7, width: 8, height: 8, borderRadius: '50%',
        background: dot, boxShadow: '0 0 0 3px rgba(127,127,127,0.12)'
      }} />
      {children}
    </div>
  )
}

/** 血缘结构化源（对账 D-5）：materials[].payload.lineage 在场的首条 payload（无＝null）。 */
export function lineagePayloadOf(turn) {
  return turn.materials.find(m => m.payload?.lineage)?.payload ?? null
}

/**
 * 一轮＝用户输入块 → 执行流水线块 → 系统回答块（串行，间不容发）。
 * 三场景归一的渲染唯一入口（H5 零分支）：不判 kind，缺数据的展示位走空态纪律整位不渲染。
 *
 * @param id                 链条节点 testid 后缀（页面临时面——turn 本身无 id 键）
 * @param turn               TurnShape（live/replay＝归约器输出，history＝historyAdapter 输出）
 * @param durationS          本地计时秒数（页面临时面——不入 turn，传流水线摘要行与 RunMetaLine）
 * @param onCite             正文引标点击回调 (index) => void（右栏切轮定位；null＝不切）
 * @param onResume           挂起卡选项点击回调 (chosen) => void（FE-03 R4 续答通路；
 *                           null＝不渲染卡——turn.askFrame 在场才出卡，数据驱动非场景分支）
 */
export function TurnChain({ id, turn, durationS = null, onCite = null, onResume = null }) {
  const phase = phaseOf(turn)
  // 挂起轮（askFrame 在场）＝等人工——不出「正在作答…」占位（挂起看 ask 帧不看 done）
  const answering = phase === 'running' && !turn.answerText && !turn.askFrame
  // 旧版历史轮（legacy=true）：正文内嵌旧式「引用：」块——原样渲染不解析，无引用数据可查
  // ＝不切锚点、不弹悬停卡（新 history 行 legacy=false：citations/materials 由 historyAdapter
  // 从收口增补面回读投影，引标行为与 live 同路——无对应引用帧仍不弹）。
  const citeClick = turn.legacy ? undefined : onCite
  const hoverCard = turn.legacy ? undefined : (index => {
    const cite = turn.citations.find(c => c.index === index)
    if (!cite) return null // 无引用帧＝不弹（不空弹）
    return <CiteHoverCard cite={cite} material={turn.materials.find(m => m.index === index)} />
  })
  return (
    <div data-testid={`round-${id}`} style={{ marginBottom: 18 }}>
      {/* ① 用户输入块（无边框圆角底块——Owner 反馈：去 Card 框，保留蓝底与内边距） */}
      <ChainBlock testid="block-question" dot="var(--pa-primary)">
        <div style={{ background: 'rgba(74,157,255,0.12)', borderRadius: 6, padding: '6px 10px' }}>
          <b>我：</b>{turn.question}
        </div>
      </ChainBlock>

      {/* ② 系统执行流水线块（typed 事件流——归约器直出到达序） */}
      <ChainBlock testid="pipeline-block" dot={phase === 'running' ? 'var(--pa-warning)' : 'var(--pa-text-tertiary)'}>
        <ExecutionPipeline turn={turn} durationS={durationS} />
      </ChainBlock>

      {/* ③ 系统回答块（无外层框——各展示位直接在链条节点里，空态纪律在展示件内） */}
      <ChainBlock testid={`turn-${id}`} dot="var(--pa-success)">
        {/* errorFrame 渲染位（FE-03 R3——对账 D-2 闭环错误契约的安放位；A 级 notice Alert 之前） */}
        {turn.errorFrame && (
          <Alert type="error" data-testid="error-frame-alert"
            message={turn.errorFrame.message} style={{ margin: '6px 0' }} />
        )}
        {/* 挂起卡（FE-03 R4——askFrame 在场＝等人工；选项点击＝onResume 续答通路）——淡蓝底无框 */}
        {turn.askFrame && turn.runStatus === 'waiting_ask' && onResume && (
          <div data-testid="suspend-card"
            style={{ margin: '8px 0', background: 'rgba(74,157,255,0.10)', borderRadius: 6, padding: '8px 12px' }}>
            <div style={{ marginBottom: 6 }}>
              {turn.askFrame.kind === 'external_table_approval' ? '越集审批' : '系统反问'}
            </div>
            <div style={{ marginBottom: 8 }}>{turn.askFrame.prompt}</div>
            {turn.askFrame.kind === 'external_table_approval' && turn.askFrame.detail?.tables && (
              <div style={dim}>外部表：{turn.askFrame.detail.tables.join('、')}</div>
            )}
            <Space wrap>
              {(turn.askFrame.options || []).map(op => (
                <Button key={op} size="small" type="primary" ghost onClick={() => onResume(op)}>{op}</Button>
              ))}
            </Space>
          </div>
        )}
        {/* A 级 notice 留一条紧凑 Alert（折叠态流水线下也能感知可信度；B/C 只在流水线里） */}
        <NoticeAlerts notices={turn.notices} />
        {answering && <div style={dim} data-testid="answer-placeholder">正在作答…</div>}
        {turn.answerText
          ? (
            <AnswerView
              content={turn.answerText}
              onCite={citeClick}
              citeHoverCard={hoverCard} />
          )
          : (!answering && <div style={dim}>本次未产出答案正文。</div>)}
        {/* 打磨批②：追加面（SupplementBlocks）已从中栏整个移除——中栏只留正文＋小字 */}
        {/* 打磨批⑨：血缘／查询口径框（LineageCard）已从中栏整个移除——同一张卡只在右栏
            「引用与口径」出一份（CitationPanel.jsx:174），中栏不重复出 */}
        {/* 旧版历史轮（legacy=true）：旧式「引用：」块随正文原样渲染；不作任何面向用户的旧版说明
            （Owner 反馈：灰字行去行话——形状保留、话不说） */}
        {/* ⑦ 核验徽标行 ＋ ⑧ 档案小字行（步数/材料数/档案 KB/本地计时）——
            运行中未收口＝无核验无档案，时长已在流水线摘要行，此处不重复出。
            verdict 仍取 verify 形（verdicts[0]——verify 帧先于 final 帧到达且本字段只消费
            verify 形计数）；verdictFinal 的消费在 FE-05 接真流时补「收口 manifest_digest」位 */}
        {phase !== 'running' && (
          <RunMetaLine verdict={turn.verdicts[0] ?? null} blackbox={turn.blackbox}
            durationS={durationS} />
        )}
      </ChainBlock>
    </div>
  )
}

/**
 * 选中行拉链（FE-04 L3）——链收集（根语义＝旧页 buildThreads／左栏分组的同一真源
 * `cites.js::chainRootId`）：followup_of 空串或指向窗口外＝到顶（链根不在列表窗内＝最老
 * 窗内成员自成一链——分组窗界兜底，如实呈现不虚构归属）；链成员＝窗口内与选中行同根的行
 * （followup_of 逐跳可达），按 created_at 升序（轮次顺序）。
 */
function collectChain(row, runs) {
  const byId = new Map(runs.map(r => [r.run_id, r]))
  const cache = new Map()
  const rootId = chainRootId(row, byId, cache)
  return runs
    .filter(r => chainRootId(r, byId, cache) === rootId)
    .sort((a, b) => (a.created_at < b.created_at ? -1 : 1))
}

export default function A1V2RLanding() {
  // 会话流（FE-05：初值空数组——提问腿 pushAskEntry 追加；重连/挂起还原推入的轮排其后）。
  // 本会话流＝中栏「未选中链」时渲染的轮次（真流页的主面）。
  const {
    entries, restoredRef, restoreRunning, resumeEntry, pushAskEntry, dispatchEntryFrame, legHandlers,
    clearEntries
  } = useRunningRun()
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  // 中栏滚动容器（chain/entries 两分支共挂同一个 ref——同时只渲染一个）＋贴底跟随开关：
  // 发送时置 true；用户上翻（离底 > 80px）置 false——流式期间不强拽回底
  const convRef = useRef(null)
  const stickRef = useRef(true)
  // 流开前错误（追问锚 409／形状 400 等）——输入区 Alert 透传后端 message（不静默吞）
  const [askError, setAskError] = useState('')
  // 页面临时面：runId → 本地计时秒数（收口时算；TurnShape 无此键——Owner 拍板无权威耗时）
  const [durationByRun, setDurationByRun] = useState({})
  const askStartRef = useRef(null)  // 本地计时起点（发送时刻）
  const streamRunIdRef = useRef('') // 本腿 session 帧的 run_id（收口记时长按它落位）
  const [focus, setFocus] = useState({ index: null, nonce: 0 })
  // FE-04 历史列真接：runs＝ThreadList 回传的当前窗口（onRuns——collectChain 拉链分组用）；
  // chain＝选中链 { runId, turns }（turns＝created_at 升序 TurnShape[]；null＝未选中——中栏本会话流）
  const [panelTurnId, setPanelTurnId] = useState('')
  const [selectedRunId, setSelectedRunId] = useState('')
  const [runs, setRuns] = useState([])
  const [chain, setChain] = useState(null)
  // 中栏选中链读回在途态（V2-140）：onSelect 进入置 true、setChain 置 false——期间中栏出
  // 「正在读取对话…」（此前 N 轮串行 RTT 期间中栏停在旧内容、零提示，调研 §一-4）。竞窗丢弃
  // 分支**不清**（L0 裁定：spinner 归最新选择所有——旧响应被丢弃时新选择仍在途就该继续显示）。
  const [chainLoading, setChainLoading] = useState(false)
  const selectSeqRef = useRef(0) // 选中竞窗护栏（异步拉链期间再点他行——旧响应丢弃不覆盖新选择）
  // 左栏对话列表收口刷新键（V2-73 原页「onDone 自动刷新」的回归——FE-05 重写后丢失）：
  // 单调计数，ThreadList 据其重拉全量；提问腿受理＋收口、挂起续答腿收口、链内续答腿收口各递增。
  const [threadsNonce, setThreadsNonce] = useState(0)
  const refreshThreads = () => setThreadsNonce(n => n + 1)
  // 右栏「引用与口径」悬浮面板开关（Owner 2026-10-19 打磨批⑫：不展示时完全不可见）——
  // 打开入口＝点正文 [n]（打开＋切轮＋定位该条）；关闭三途：面板头部「×」／点面板之外
  // （组件内 document mousedown 判，引标与 Modal 门户豁免）／切换对话（onSelect、＋新会话）。
  // 状态归本页，组件受控。
  const [panelOpen, setPanelOpen] = useState(false)

  // 中栏视图轮次（**唯一派生点**——链视图＝链轮次在前＋链后新提问轮在后；未选链＝本会话流）。
  // 追问不清链视图（Owner 2026-10-19 反馈修）：`onSelect` 清 entries（链之后的新提问才归本视图），
  // `send()` 不再清 chain——屏上已有对话整段保留，新轮接在下方。fromChain 决定续答落点
  // （链轮→chain 态；会话流轮→entries 态）。
  const viewTurns = [
    ...(chain ? chain.turns.map(t => ({ id: t.runId, turn: t, fromChain: true })) : []),
    ...entries.map(e => ({ id: e.id, turn: e.turn, fromChain: false }))
  ]
  // 右栏联动（FE-04 L3）：命中选中轮（点正文 [n] 切轮）＝该轮；缺省＝视图末位（链尾或链后新轮）；
  // 无轮＝空轮——面板出空态「本回合无引用」
  const panelTurn = viewTurns.find(v => v.id === panelTurnId)?.turn ?? viewTurns.at(-1)?.turn ?? EMPTY_TURN
  const panelLineage = lineagePayloadOf(panelTurn)

  // 追问锚＝当前视图里最新的**已收口**轮 run（后端前轮须 completed，无收口轮＝不带键＝独立新问）
  const followupAnchor = [...viewTurns]
    .reverse().find(v => v.turn.runStatus === 'completed')?.turn.runId ?? ''

  /** 正文引标点击（打磨批⑫）：切面板轮次＋记定位拍号＋**打开悬浮面板**——点 [n] 是唯一入口。 */
  const openCite = id => index => {
    setPanelTurnId(id)
    setFocus(f => ({ index, nonce: f.nonce + 1 }))
    setPanelOpen(true)
  }

  /** 贴底判定（中栏滚动容器 onScroll）：离底 < 80px 视作跟随态；上翻阅读＝解除跟随。 */
  const onConvScroll = e => {
    const el = e.currentTarget
    stickRef.current = (el.scrollHeight - el.scrollTop - el.clientHeight) < 80
  }

  /** 收口记本地计时（durationByRun[runId]——RunMetaLine/流水线摘要行按 runId 取）。 */
  const recordDuration = runId => {
    if (askStartRef.current == null) return
    const secs = Math.round((Date.now() - askStartRef.current) / 1000)
    askStartRef.current = null
    setDurationByRun(m => ({ ...m, [runId ?? '']: secs }))
  }

  /**
   * 发送（FE-05 真流贯通——票面伪代码第 1 节）：空问/在途＝不发；置忙＋起点计时；新问条入本
   * 会话流（**不清链视图**——选中链后追问＝链轮照旧在屏，新轮接在其后，见头注「追问不清链视图」）；
   * postAskV2 流式帧直进 FE-01 reducer 归一出 TurnShape 同轮追加；收口（done/error/transport）＝
   * 记本地计时＋清 running run 键（清键判据在 legHandlers）。流内 error 帧先过 onFrame 落
   * errorFrame；传输断＝closed='transport'。流开前错误（追问锚 409 等）＝输入区 Alert 透传
   * message ＋该轮落 errorFrame（不静默——如实呈现失败轮，不伪造答案）。
   * 左栏刷新两拍：受理（session 帧——run 行受理即落库）＋收口——新对话当场进列，不等浏览器刷新。
   */
  const send = () => {
    const question = input.trim()
    if (!question || sending) return
    setSending(true)
    setAskError('')
    setInput('')
    askStartRef.current = Date.now()
    streamRunIdRef.current = ''
    stickRef.current = true // 自己发的问＝回到贴底跟随（上翻阅读态让位新内容）
    const anchor = followupAnchor
    const entryId = pushAskEntry(question)
    const leg = legHandlers({ entryId, question }, () => {
      recordDuration(streamRunIdRef.current)
      refreshThreads() // 收口刷新（V2-73「onDone 后刷新」）
    })
    Promise.resolve(postAskV2(
      { question, ...(anchor ? { followupRunId: anchor } : {}) },
      {
        ...leg,
        onFrame: f => {
          if (f.event === 'session' && f.data?.run_id) {
            streamRunIdRef.current = f.data.run_id
            refreshThreads() // 受理刷新——run 行已落库（runtime.py:264），新对话当场进左栏
          }
          leg.onFrame(f)
        }
      }
    )).catch(err => {
      const pkg = {
        code: err instanceof ApiError ? err.code : 'ask_failed',
        message: err instanceof ApiError ? errText(err) : String(err)
      }
      setAskError(pkg.message)
      dispatchEntryFrame(entryId, { event: 'error', data: pkg })
      askStartRef.current = null
    }).finally(() => setSending(false))
  }

  /**
   * 链内挂起轮续答（FE-04 遗留，本票接通）：postResumeV2 本腿新帧落回该链轮（同 runId 原位
   * upsert——不另开轮）；卡先让位。链轮来自历史读口（非本进程 running）——不涉 running run
   * 键；开流前错误（409 非挂起等）落 errorFrame 灰条如实呈现。收口三闸各刷新左栏一次
   * （续答腿收口后该轮状态/轮数在列上更新）。
   */
  const resumeChainTurn = (turn, chosen) => {
    if (!turn?.askFrame || !turn.runId) return
    const body = resumeBodyFromAskFrame(turn.askFrame, chosen)
    const apply = updater => setChain(c => (c
      ? { ...c, turns: c.turns.map(t => (t.runId === turn.runId ? updater(t) : t)) }
      : c))
    apply(t => ({ ...t, askFrame: null })) // 卡让位——本腿帧接续同轮
    Promise.resolve(postResumeV2(turn.runId, body, {
      onFrame: f => apply(t => reduceV2Frame(t, f)),
      onDone: () => refreshThreads(),
      onError: () => refreshThreads(),
      onTransportError: () => {
        apply(t => (t.closed ? t : { ...t, closed: 'transport' }))
        refreshThreads()
      }
    })).catch(err => {
      apply(t => (t.closed ? t : {
        ...t,
        closed: 'error',
        runStatus: 'failed',
        errorFrame: {
          code: err instanceof ApiError ? err.code : 'resume_failed',
          message: err instanceof ApiError ? errText(err) : String(err)
        }
      }))
    })
  }

  /** 左栏行点击（FE-04 L3 选中拉链）：collectChain 取窗内同链行 → 每轮 getRunV2（并行（逐项 catch；竞窗护栏在 await 后））→
   *  adaptHistoryTurn 归一 → 中栏切该链。404（进程重启丢行）轮降级：adaptHistoryTurn(r, null)
   *  ＋errorFrame{run_unreachable}（文案与 useRunningRun R3 合成轮同词）；其他读口错误同形
   *  降级——单轮缺明细不炸整链。**清本会话流**（entries）：链视图＝链轮＋**链之后**新提问轮
   *  （viewTurns 语义——上一次会话流的轮不混进本链）。 */
  const onSelect = async row => {
    setSelectedRunId(row.run_id)
    clearEntries()
    setPanelOpen(false) // 切换对话＝自动隐藏悬浮面板（打磨批⑫；键盘激活不走 mousedown，故此处显式收）
    selectSeqRef.current += 1
    const seq = selectSeqRef.current
    setChainLoading(true) // 读回在途（V2-140）：中栏出「正在读取对话…」
    const chainRows = collectChain(row, runs)
    const results = await Promise.all(chainRows.map(async r => {
      try {
        return { turn: adaptHistoryTurn(r, await getRunV2(r.run_id)) }
      } catch (err) {
        return {
          turn: {
            ...adaptHistoryTurn(r, null),
            errorFrame: err instanceof ApiError && err.status === 404
              ? { code: 'run_unreachable', message: '本轮已结束或不可达' }
              : { code: err instanceof ApiError ? err.code : 'run_unreachable', message: errText(err) }
          }
        }
      }
    }))
    if (seq !== selectSeqRef.current) return // 竞窗：已有更新的选择在途——旧响应丢弃（spinner 归新选择所有，此处不清）
    setChain({ runId: row.run_id, turns: results.map(x => x.turn) })
    setChainLoading(false)
  }

  /**
   * ＋新会话（唯一显式退出对话入口——旧页 608267b A1V2.jsx :311-317 同义）：清对话选中
   * （chain/selectedRunId）、本会话流（clearEntries）、输入与流开前错误；followupAnchor/
   * panelTurn 皆派生值随两态自动复位。sessionStorage 的 running run 键不动（旧页亦不
   * 清——服务端 run 照跑，退出的只是本页这段对话）。
   */
  const startNewSession = () => {
    setChain(null)
    setSelectedRunId('')
    clearEntries()
    setPanelOpen(false) // ＋新会话＝自动隐藏悬浮面板（打磨批⑫）
    setInput('')
    setAskError('')
  }

  // 中栏贴底跟随（旧页 608267b A1V2.jsx :226-237 每帧 scrollBottom 的回归，较旧页柔和：
  // 只有 stickRef 为真（贴近底部／自己刚发送）才滚，用户上翻阅读时不被拽回）
  useEffect(() => {
    if (!stickRef.current) return
    const el = convRef.current
    if (!el) return
    // jsdom 无 Element.scrollTo——回退直接置 scrollTop（两条路径语义等价）
    if (typeof el.scrollTo === 'function') el.scrollTo({ top: el.scrollHeight })
    else el.scrollTop = el.scrollHeight
  }, [entries, chain])

  // FE-03 R2/R3/R4：mount 调 restoreRunning() 一次（票面伪代码：useEffect 空依赖；
  // restoredRef 护栏——组件实例内只跑一遍，重连/还原推入的轮不重复）
  useEffect(() => {
    if (restoredRef.current) return
    restoredRef.current = true
    restoreRunning()
  // eslint-disable-next-line react-hooks/exhaustive-deps -- mount 一次（restoreRunning 身份稳定）
  }, [])

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'stretch', height: '100%' }}>
      {/* 左栏 · 历史对话（FE-04 真接：ThreadList 内部态拉 listRunsV2——上拉加载 + 搜索；
          真接口形态见 ThreadList.jsx 头注；当前窗口经 onRuns 回传供拉链分组） */}
      <Card size="small" title={<span>对话{helpIcon('左侧是历史对话：往下滑看更早的，或在上方搜索框里找问过的题。一次最多回看最近 100 个对话。')}</span>}
        extra={(
          <Button size="small" type="text" data-testid="new-session" disabled={sending}
            onClick={startNewSession}>＋新会话</Button>
        )}
        style={{ width: 250, flexShrink: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' } }}>
        <ThreadList selectedId={selectedRunId} onSelect={onSelect} onRuns={setRuns}
          refreshKey={threadsNonce} />
      </Card>

      {/* 中栏 · 串行链条（垂直时间线：每轮＝问句块→流水线块→回答块）。
          三来源一统（viewTurns 单点派生）：选中链轮次（FE-04 L3——adaptHistoryTurn 归一，升序）
          在前＋链之后新提问轮（提问腿与重连还原推入的轮，真流归约器输出）在后——追问不清链视图，
          屏上已有对话整段保留。未选链＝本会话流单段。 */}
      <Card size="small" style={{ flex: 1, minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 320, display: 'flex', flexDirection: 'column' } }}>
        {chain && (
          <div style={{ ...dim, marginBottom: 8 }}>
            {`对话 · ${viewTurns.length} 轮`}
          </div>
        )}
        {/* 选中链读回在途（V2-140）：中栏加载态——最新选择读回落地才撤（旧响应被竞窗丢弃不清，
            spinner 归最新选择所有；此前 N 轮串行期间无提示） */}
        {chainLoading && (
          <div style={dim} data-testid="chain-loading"><Spin size="small" /> 正在读取对话…</div>
        )}
        {viewTurns.length === 0 && (
          <div style={{ ...dim, textAlign: 'center', marginTop: 60 }} data-testid="flow-empty">
            输入问题开始（挂起后在本栏确认；左侧点历史对话可回看该链）
          </div>
        )}
        <div ref={convRef} onScroll={onConvScroll} data-testid="conv-scroll"
          style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: 4 }}>
          <div style={{ borderLeft: '2px solid rgba(127,127,127,0.22)', paddingLeft: 14 }}>
            {viewTurns.map(v => (
              <TurnChain key={v.id} id={v.id} turn={v.turn}
                durationS={durationByRun[v.turn.runId] ?? null}
                onCite={openCite(v.id)}
                onResume={v.fromChain
                  ? chosen => resumeChainTurn(v.turn, chosen)
                  : chosen => resumeEntry(v, chosen, refreshThreads)} />
            ))}
          </div>
        </div>
        {/* 输入区（FE-05 已接线：Enter/发送＝真提问——追问带 followupRunId） */}
        <div style={{ marginTop: 10 }}>
          {askError && (
            <Alert type="error" showIcon data-testid="ask-error-alert"
              message={askError} style={{ marginBottom: 6 }} />
          )}
          {followupAnchor && (
            <div style={{ ...dim, marginBottom: 6 }} data-testid="followup-hint">
              继续本会话（追问上下文自动继承）
            </div>
          )}
          <Space.Compact style={{ width: '100%' }}>
            <Input placeholder={followupAnchor ? '继续本会话追问（Enter 发送）' : '输入问题（Enter 发送）'}
              value={input} disabled={sending}
              onPressEnter={e => { if (e.nativeEvent.isComposing) return; send() }}
              onChange={e => setInput(e.target.value)} />
            <Button type="primary" icon={<SendOutlined />} loading={sending}
              disabled={!input.trim()} onClick={send}>发送</Button>
          </Space.Compact>
        </div>
      </Card>

      {/* 右栏 · 引用与口径（人话面板——机器腔过程只留在流水线展开态里）。
          **不展示时完全不可见**（打磨批⑫）：整卡不渲染、无常驻入口；点正文 [n] 才出悬浮面板
          并定位该条，面板头部「×」关掉——开关归页面 `panelOpen`，组件受控。
          血缘两源（对账 D-5）同回答块：lineage/limit 从 materials[].payload 取，
          文本兜底 lineageText/splitText 读 turn.supplements.*（打磨批③：attributionText 已删——
          「按来源列出」块与引用清单同源重复，整块退场） */}
      <CitationPanel
        citations={panelTurn.citations} materials={panelTurn.materials}
        lineage={panelLineage?.lineage ?? null} limit={panelLineage?.limit ?? null}
        lineageText={panelTurn.supplements?.lineage ?? ''}
        splitText={panelTurn.supplements?.split ?? null}
        focusIndex={focus.index} focusNonce={focus.nonce}
        running={panelTurn.runStatus === 'running'}
        open={panelOpen} onOpenChange={setPanelOpen} />
    </div>
  )
}
