/**
 * A1V2R · 问一问V2 **真流页**（落地树 `#/A1V2`——FE-05 临时路由转正，见 registry.js）。
 *
 * 形态：整页一条垂直追加时间线（Owner 2026-10-17 拍板的串行链条模型），每轮三个串行块：
 *   1) **用户输入块**（问句气泡）
 *   2) **系统执行流水线块**（ExecutionPipeline：typed 事件流，运行中默认展开、答案一开始流
 *      就自动收起成一行摘要，可点开回看全程）
 *   3) **系统回答块**（A 级 notice 紧凑 Alert → 正文流 AnswerView → 血缘卡 LineageCard →
 *      追加面 SupplementBlocks → 核验/档案小字 RunMetaLine）；运行中此块＝「正在作答…」占位
 *
 * 中栏三来源一统（FE-05 去夹具轮后）：**本会话提问流**（send→SSE→链条追加，含刷新重连推入轮）
 * ／**选中链**（左栏点行的历史链——FE-04 L3，选中即切换视图）。新提问＝退出链视图回本会话流。
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
 * 选中链最后一轮（点正文 [n] 切轮定位机制不变）。
 *
 * 边界（未变部分）：右栏 CitationPanel（人话面板）与右栏宽度 360、决策树入口均不动
 * （Owner 2026-10-17 拍板「4 宽度你看着办, 决策树留着」）。
 * 空态纪律：各项无数据＝该位不渲染（组件内实现，本页只透传）。
 */
import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Card, Input, Space } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import { ApiError, errText } from '../../api/client.js'
import { getRunV2, postAskV2, postResumeV2, resumeBodyFromAskFrame } from '../../api/chatV2.js'
import { dim, helpIcon } from '../../components/helpIcon.jsx'
import { newTurnV2, phaseOf, reduceV2Frame } from '../a1v2Reducer.js'
import AnswerView from '../AnswerView.jsx'
import CitationPanel from './CitationPanel.jsx'
import CiteHoverCard from './CiteHoverCard.jsx'
import ExecutionPipeline from './ExecutionPipeline.jsx'
import { adaptHistoryTurn } from './historyAdapter.js'
import LineageCard from './LineageCard.jsx'
import { NoticeAlerts } from './NoticeBand.jsx'
import RunMetaLine from './RunMetaLine.jsx'
import SupplementBlocks from './SupplementBlocks.jsx'
import ThreadList from './ThreadList.jsx'
import { useRunningRun } from './useRunningRun.js'

/** 空轮（无会话轮时的右栏空态载体——citations/materials 全空，面板出「本回合无引用」）。 */
const EMPTY_TURN = newTurnV2('ask', '')

/** 链条节点（时间轴视觉——左侧竖线＋圆点，把三轮三块串成一条）。 */
function ChainBlock({ testid, dot = '#4a9dff', children }) {
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
 * @param defaultLineageOpen 血缘卡初态是否展开（页面给完整轮开的版面糖）
 */
export function TurnChain({ id, turn, durationS = null, onCite = null, onResume = null, defaultLineageOpen = false }) {
  const phase = phaseOf(turn)
  // 挂起轮（askFrame 在场）＝等人工——不出「正在作答…」占位（挂起看 ask 帧不看 done）
  const answering = phase === 'running' && !turn.answerText && !turn.askFrame
  const lineagePayload = lineagePayloadOf(turn)
  // 旧版历史轮（legacy=true）：正文内嵌旧式「引用：」块——原样渲染不解析，无引用数据可查
  // ＝不切锚点、不弹悬停卡（新 history 行 legacy=false，引标行为与 live 同路——无引用帧不弹）。
  const citeClick = turn.legacy ? undefined : onCite
  const hoverCard = turn.legacy ? undefined : (index => {
    const cite = turn.citations.find(c => c.index === index)
    if (!cite) return null // 无引用帧＝不弹（不空弹）
    return <CiteHoverCard cite={cite} material={turn.materials.find(m => m.index === index)} />
  })
  return (
    <div data-testid={`round-${id}`} style={{ marginBottom: 18 }}>
      {/* ① 用户输入块 */}
      <ChainBlock testid="block-question" dot="#1677ff">
        <Card size="small" style={{ background: 'rgba(22,119,255,0.12)' }}>
          <b>我：</b>{turn.question}
        </Card>
      </ChainBlock>

      {/* ② 系统执行流水线块（typed 事件流——归约器直出到达序） */}
      <ChainBlock testid="pipeline-block" dot={phase === 'running' ? '#e8b339' : '#8a94a3'}>
        <ExecutionPipeline turn={turn} durationS={durationS} />
      </ChainBlock>

      {/* ③ 系统回答块 */}
      <ChainBlock testid={`turn-${id}`} dot="#52c41a">
        <Card size="small">
          {/* errorFrame 渲染位（FE-03 R3——对账 D-2 闭环错误契约的安放位；A 级 notice Alert 之前） */}
          {turn.errorFrame && (
            <Alert type="error" data-testid="error-frame-alert"
              message={turn.errorFrame.message} style={{ margin: '6px 0' }} />
          )}
          {/* 挂起卡（FE-03 R4——askFrame 在场＝等人工；选项点击＝onResume 续答通路） */}
          {turn.askFrame && turn.runStatus === 'waiting_ask' && onResume && (
            <Card size="small" data-testid="suspend-card" style={{ margin: '8px 0', borderColor: '#4a9dff' }}
              title={<span>{turn.askFrame.kind === 'external_table_approval' ? '越集审批' : '系统反问'}</span>}>
              <div style={{ marginBottom: 8 }}>{turn.askFrame.prompt}</div>
              {turn.askFrame.kind === 'external_table_approval' && turn.askFrame.detail?.tables && (
                <div style={dim}>外部表：{turn.askFrame.detail.tables.join('、')}</div>
              )}
              <Space wrap>
                {(turn.askFrame.options || []).map(op => (
                  <Button key={op} size="small" type="primary" ghost onClick={() => onResume(op)}>{op}</Button>
                ))}
              </Space>
            </Card>
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
          {/* 链条后续节点：血缘卡 → 追加面（空态各自不出）。
              血缘两源（对账 D-5）：结构化源＝materials[].payload（优先）；文本兜底＝supplements.lineage */}
          <LineageCard lineage={lineagePayload?.lineage ?? null} limit={lineagePayload?.limit ?? null}
            text={turn.supplements?.lineage ?? ''} defaultOpen={defaultLineageOpen} />
          <SupplementBlocks split={turn.supplements?.split ?? null}
            attribution={turn.supplements?.attribution ?? null} />
          {/* 旧版历史轮降级说明（supplements=null 的旧轮——如实说不清，不假装有明细） */}
          {turn.legacy && (
            <div style={{ ...dim, marginTop: 6 }} data-testid="legacy-note">
              本轮为旧版记录，无引用/口径明细。
            </div>
          )}
          {/* ⑦ 核验徽标行 ＋ ⑧ 档案小字行（run 号/步数/材料数/档案 KB/本地计时）——
              运行中未收口＝无核验无档案，时长已在流水线摘要行，此处不重复出。
              verdict 仍取 verify 形（verdicts[0]——verify 帧先于 final 帧到达且本字段只消费
              verify 形计数）；verdictFinal 的消费在 FE-05 接真流时补「收口 manifest_digest」位 */}
          {phase !== 'running' && (
            <RunMetaLine runId={turn.runId} verdict={turn.verdicts[0] ?? null} blackbox={turn.blackbox}
              durationS={durationS} />
          )}
        </Card>
      </ChainBlock>
    </div>
  )
}

/**
 * 选中行拉链（FE-04 L3）——链收集（分组语义与原现状页 buildThreads 同源）：
 * rootOf 沿 followup_of 上溯，followup_of 空串或指向窗口外＝到顶（链根不在列表窗内＝最老
 * 窗内成员自成一链——分组窗界兜底，如实呈现不虚构归属）；链成员＝窗口内与选中行同根的行
 * （followup_of 逐跳可达），按 created_at 升序（轮次顺序）。
 */
function collectChain(row, runs) {
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
  const rootId = rootOf(row)
  return runs
    .filter(r => rootOf(r) === rootId)
    .sort((a, b) => (a.created_at < b.created_at ? -1 : 1))
}

export default function A1V2RLanding() {
  // 会话流（FE-05：初值空数组——提问腿 pushAskEntry 追加；重连/挂起还原推入的轮排其后）。
  // 本会话流＝中栏「未选中链」时渲染的轮次（真流页的主面）。
  const {
    entries, restoredRef, restoreRunning, resumeEntry, pushAskEntry, dispatchEntryFrame, legHandlers
  } = useRunningRun()
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
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
  const selectSeqRef = useRef(0) // 选中竞窗护栏（异步拉链期间再点他行——旧响应丢弃不覆盖新选择）
  const panelEntry = entries.find(e => e.id === panelTurnId) ?? entries.at(-1)
  // 右栏联动（FE-04 L3）：选中链＝链内选中轮（点正文 [n] 切轮定位机制不变；缺省＝当前选中链
  // 的最后一轮）；未选链＝本会话流最新轮（无轮＝空轮——面板出空态「本回合无引用」）
  const panelTurn = chain
    ? (chain.turns.find(t => t.runId === panelTurnId) ?? chain.turns.at(-1))
    : (panelEntry?.turn ?? EMPTY_TURN)
  const panelLineage = lineagePayloadOf(panelTurn)

  // 追问锚＝当前视图里最新的**已收口**轮 run（链视图取链、否则取本会话流；后端前轮须 completed，
  // 无收口轮＝不带键＝独立新问）
  const followupAnchor = [...(chain ? chain.turns : entries.map(e => e.turn))]
    .reverse().find(t => t.runStatus === 'completed')?.runId ?? ''

  const openCite = id => index => {
    setPanelTurnId(id)
    setFocus(f => ({ index, nonce: f.nonce + 1 }))
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
   * 会话流（并退出链视图——中栏回本会话流）；postAskV2 流式帧直进 FE-01 reducer 归一出
   * TurnShape 同轮追加；收口（done/error/transport）＝记本地计时＋清 running run 键（清键判据
   * 在 legHandlers）。流内 error 帧先过 onFrame 落 errorFrame；传输断＝closed='transport'。
   * 流开前错误（追问锚 409 等）＝输入区 Alert 透传 message ＋该轮落 errorFrame（不静默——如实
   * 呈现失败轮，不伪造答案）。
   */
  const send = () => {
    const question = input.trim()
    if (!question || sending) return
    setSending(true)
    setAskError('')
    setInput('')
    askStartRef.current = Date.now()
    streamRunIdRef.current = ''
    setSelectedRunId('')
    setChain(null) // 新提问＝退出选中链视图（三来源一统：提问/重连/选中链同处一条链条流）
    const anchor = followupAnchor
    const entryId = pushAskEntry(question)
    const leg = legHandlers({ entryId, question }, () => recordDuration(streamRunIdRef.current))
    Promise.resolve(postAskV2(
      { question, ...(anchor ? { followupRunId: anchor } : {}) },
      {
        ...leg,
        onFrame: f => {
          if (f.event === 'session' && f.data?.run_id) streamRunIdRef.current = f.data.run_id
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
   * 键；开流前错误（409 非挂起等）落 errorFrame 灰条如实呈现。
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
      onDone: () => {},
      onError: () => {},
      onTransportError: () => apply(t => (t.closed ? t : { ...t, closed: 'transport' }))
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

  /** 左栏行点击（FE-04 L3 选中拉链）：collectChain 取窗内同链行 → 每轮 getRunV2（顺序）→
   *  adaptHistoryTurn 归一 → 中栏切该链。404（进程重启丢行）轮降级：adaptHistoryTurn(r, null)
   *  ＋errorFrame{run_unreachable}（文案与 useRunningRun R3 合成轮同词）；其他读口错误同形
   *  降级——单轮缺明细不炸整链。 */
  const onSelect = async row => {
    setSelectedRunId(row.run_id)
    selectSeqRef.current += 1
    const seq = selectSeqRef.current
    const chainRows = collectChain(row, runs)
    const turns = []
    for (const r of chainRows) {
      try {
        turns.push(adaptHistoryTurn(r, await getRunV2(r.run_id)))
      } catch (err) {
        turns.push({
          ...adaptHistoryTurn(r, null),
          errorFrame: err instanceof ApiError && err.status === 404
            ? { code: 'run_unreachable', message: '本轮已结束或不可达' }
            : { code: err instanceof ApiError ? err.code : 'run_unreachable', message: errText(err) }
        })
      }
    }
    if (seq !== selectSeqRef.current) return // 竞窗：已有更新的选择在途——旧响应丢弃
    setChain({ runId: row.run_id, turns })
  }

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
        style={{ width: 250, flexShrink: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 0, overflow: 'hidden' } }}>
        <ThreadList selectedId={selectedRunId} onSelect={onSelect} onRuns={setRuns} />
      </Card>

      {/* 中栏 · 串行链条（垂直时间线：每轮＝问句块→流水线块→回答块）。
          三来源一统：选中链（FE-04 L3——真链轮次，adaptHistoryTurn 归一，升序）／本会话流
          （提问腿与重连还原推入的轮，真流归约器输出） */}
      <Card size="small" style={{ flex: 1, minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 320, display: 'flex', flexDirection: 'column' } }}>
        {chain ? (
          <>
            <div style={{ ...dim, marginBottom: 8 }}>
              {`对话 · ${chain.turns.length} 轮（选中链——created_at 升序）`}
            </div>
            <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: 4 }}>
              <div style={{ borderLeft: '2px solid rgba(127,127,127,0.22)', paddingLeft: 14 }}>
                {chain.turns.map(t => (
                  <TurnChain key={t.runId} id={t.runId} turn={t} durationS={durationByRun[t.runId] ?? null}
                    onCite={openCite(t.runId)} onResume={chosen => resumeChainTurn(t, chosen)} />
                ))}
              </div>
            </div>
          </>
        ) : (
          <>
            {entries.length === 0 && (
              <div style={{ ...dim, textAlign: 'center', marginTop: 60 }} data-testid="flow-empty">
                输入问题开始（挂起后在本栏确认；左侧点历史对话可回看该链）
              </div>
            )}
            <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: 4 }}>
              <div style={{ borderLeft: '2px solid rgba(127,127,127,0.22)', paddingLeft: 14 }}>
                {entries.map(entry => (
                  <TurnChain key={entry.id} id={entry.id} turn={entry.turn}
                    durationS={durationByRun[entry.turn.runId] ?? null}
                    onCite={openCite(entry.id)} onResume={chosen => resumeEntry(entry, chosen)} />
                ))}
              </div>
            </div>
          </>
        )}
        {/* 输入区（FE-05 已接线：Enter/发送＝真提问——追问带 followupRunId） */}
        <div style={{ marginTop: 10 }}>
          {askError && (
            <Alert type="error" showIcon data-testid="ask-error-alert"
              message={askError} style={{ marginBottom: 6 }} />
          )}
          {followupAnchor && (
            <div style={{ ...dim, marginBottom: 6 }} data-testid="followup-hint">
              {`继续本会话（追问 ${followupAnchor}）`}
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
          血缘两源（对账 D-5）同回答块：lineage/limit 从 materials[].payload 取，
          文本兜底 lineageText/splitText/attributionText 读 turn.supplements.* */}
      <CitationPanel
        citations={panelTurn.citations} materials={panelTurn.materials}
        lineage={panelLineage?.lineage ?? null} limit={panelLineage?.limit ?? null}
        lineageText={panelTurn.supplements?.lineage ?? ''}
        splitText={panelTurn.supplements?.split ?? null}
        attributionText={panelTurn.supplements?.attribution ?? null}
        focusIndex={focus.index} focusNonce={focus.nonce}
        running={panelTurn.runStatus === 'running'} />
    </div>
  )
}
