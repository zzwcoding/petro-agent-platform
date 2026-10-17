/**
 * A1V2R · 问一问V2 重设计 **mock 静态页**（临时路由 `#/A1V2R`）——串行链条模型。
 *
 * Owner 2026-10-17 否掉「卡内堆叠」形态，新模型＝**整页一条垂直追加时间线**，每轮三个串行块：
 *   1) **用户输入块**（问句气泡）
 *   2) **系统执行流水线块**（ExecutionPipeline：typed 事件流，运行中默认展开、答案一开始流
 *      就自动收起成一行摘要，可点开回看全程）
 *   3) **系统回答块**（A 级 notice 紧凑 Alert → 正文流 AnswerView → 血缘卡 LineageCard →
 *      追加面 SupplementBlocks → 核验/档案小字 RunMetaLine）；运行中此块＝「正在作答…」占位
 *
 * 四轮（mockTurns.js——真帧夹具经归约器/historyAdapter 产出 TurnShape）：①运行中（流水线
 * 展开态——真机流式前缀）②完整轮（done，流水线收起可展开）③分列轮（done，长 split 限高）
 * ④旧版降级轮（无流水线无引用——空态静默降级）。
 * 三场景归一（H5 零分支）：`TurnChain` 是页面与 `one_shape_three_scenarios` 测试共用的唯一
 * 轮渲染件——live/replay（归约器输出）与 history（historyAdapter 输出）同 props 路径，
 * 不判 kind；phase 渲染期 phaseOf(turn) 派生（FE-01 导出，turn 不携带 phase 字段）。
 *
 * 边界（未变）：**不接后端**（零 SSE、零 `/api/v2/*`）／不覆盖现状页 A1V2.jsx／左栏静态假列表／
 * 右栏 CitationPanel（人话面板）与右栏宽度、决策树入口均不动。
 * 空态纪律：各项无数据＝该位不渲染（组件内实现，本页只透传）。
 *
 * DEBT(docs/runtime-refactor/frontend-redesign-设计.md)：整页连同 redesign/ 与临时路由
 * （registry.REDESIGN_MODULES／roles.js 菜单项／Shell.jsx 懒加载项）只服务施工顺序第 1 步
 * 「mock 静态页对版面」；第 2 步接归约器后本页删除（或按 Owner 裁决替换现状页）。
 */
import { useState } from 'react'
import { Button, Card, Input, Space, Tag } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import { dim, helpIcon } from '../../components/helpIcon.jsx'
import { phaseOf } from '../a1v2Reducer.js'
import AnswerView from '../AnswerView.jsx'
import CitationPanel from './CitationPanel.jsx'
import CiteHoverCard from './CiteHoverCard.jsx'
import ExecutionPipeline from './ExecutionPipeline.jsx'
import LineageCard from './LineageCard.jsx'
import { NoticeAlerts } from './NoticeBand.jsx'
import RunMetaLine from './RunMetaLine.jsx'
import SupplementBlocks from './SupplementBlocks.jsx'
import ThreadList from './ThreadList.jsx'
import { MOCK_RUNS, MOCK_TURNS } from './mockTurns.js'

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
 * @param defaultLineageOpen 血缘卡初态是否展开（页面给完整轮开的版面糖）
 */
export function TurnChain({ id, turn, durationS = null, onCite = null, defaultLineageOpen = false }) {
  const phase = phaseOf(turn)
  const answering = phase === 'running' && !turn.answerText
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

export default function A1V2RLanding() {
  // 右栏联动轮次（mock：默认＝完整轮；正文引标一点即切到该轮并定位）
  const [panelTurnId, setPanelTurnId] = useState('t-full')
  const [focus, setFocus] = useState({ index: null, nonce: 0 })
  const [selectedRunId, setSelectedRunId] = useState(MOCK_RUNS[0]?.run_id ?? '')
  const panelEntry = MOCK_TURNS.find(e => e.id === panelTurnId) ?? MOCK_TURNS[0]
  const panelTurn = panelEntry.turn
  const panelLineage = lineagePayloadOf(panelTurn)

  const openCite = id => index => {
    setPanelTurnId(id)
    setFocus(f => ({ index, nonce: f.nonce + 1 }))
  }

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'stretch', height: '100%' }}>
      {/* 左栏 · 历史对话（上拉加载 + 搜索——真接口形态见 ThreadList.jsx 头注；mock 数据 120 条） */}
      <Card size="small" title={<span>对话{helpIcon('左侧是历史对话：往下滑看更早的，或在上方搜索框里找问过的题。一次最多回看最近 100 个对话。')}</span>}
        style={{ width: 250, flexShrink: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 0, overflow: 'hidden' } }}>
        <ThreadList runs={MOCK_RUNS} selectedId={selectedRunId} onSelect={r => setSelectedRunId(r.run_id)} />
      </Card>

      {/* 中栏 · 串行链条（垂直时间线：每轮＝问句块→流水线块→回答块） */}
      <Card size="small" style={{ flex: 1, minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 320, display: 'flex', flexDirection: 'column' } }}>
        <div style={{ ...dim, marginBottom: 8 }}>
          <Tag color="orange">mock 数据 · 静态版面</Tag>
          串行链条（真机帧假数据，未接后端）：①运行中 ②完整轮 ③分列轮 ④旧版降级。
        </div>
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: 4 }}>
          <div style={{ borderLeft: '2px solid rgba(127,127,127,0.22)', paddingLeft: 14 }}>
            {MOCK_TURNS.map(entry => (
              <TurnChain key={entry.id} id={entry.id} turn={entry.turn} durationS={entry.durationS}
                onCite={openCite(entry.id)} defaultLineageOpen={entry.id === 't-full'} />
            ))}
          </div>
        </div>
        {/* 输入区（版面位——mock 页不接线发送，按钮如实禁用） */}
        <div style={{ marginTop: 10 }}>
          <Space.Compact style={{ width: '100%' }}>
            <Input placeholder="（mock 页——输入与发送不接线）" disabled />
            <Button type="primary" icon={<SendOutlined />} disabled>发送</Button>
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
