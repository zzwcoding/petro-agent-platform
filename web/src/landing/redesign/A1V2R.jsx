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
 * 四轮（mockTurns.js，真机帧抽出）：①运行中（流水线展开态——真机流式前缀）②完整轮（done，
 * 流水线收起可展开）③分列轮（done，长 split 限高）④旧版降级轮（无流水线无引用——空态静默降级）。
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
import { Button, Card, Input, List, Space, Tag } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import { dim, helpIcon } from '../../components/helpIcon.jsx'
import AnswerView from '../AnswerView.jsx'
import CitationPanel from './CitationPanel.jsx'
import CiteHoverCard from './CiteHoverCard.jsx'
import ExecutionPipeline from './ExecutionPipeline.jsx'
import LineageCard from './LineageCard.jsx'
import { NoticeAlerts } from './NoticeBand.jsx'
import RunMetaLine from './RunMetaLine.jsx'
import SupplementBlocks from './SupplementBlocks.jsx'
import { MOCK_THREADS, MOCK_TURNS } from './mockTurns.js'

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

export default function A1V2RLanding() {
  // 右栏联动轮次（mock：默认＝完整轮；正文引标一点即切到该轮并定位）
  const [panelTurnId, setPanelTurnId] = useState('t-full')
  const [focus, setFocus] = useState({ index: null, nonce: 0 })
  const panelTurn = MOCK_TURNS.find(t => t.id === panelTurnId) ?? MOCK_TURNS[0]

  const openCite = turn => index => {
    setPanelTurnId(turn.id)
    setFocus(f => ({ index, nonce: f.nonce + 1 }))
  }

  const hoverCard = turn => index => {
    const cite = turn.citations.find(c => c.index === index)
    if (!cite) return null // 无引用帧＝不弹（不空弹）
    return <CiteHoverCard cite={cite} material={turn.materials.find(m => m.index === index)} />
  }

  /** 一轮＝用户输入块 → 执行流水线块 → 系统回答块（串行，间不容发）。 */
  function renderTurn(turn) {
    const answering = turn.phase === 'running' && !turn.answerText
    return (
      <div key={turn.id} data-testid={`round-${turn.id}`} style={{ marginBottom: 18 }}>
        {/* ① 用户输入块 */}
        <ChainBlock testid="block-question" dot="#1677ff">
          <Card size="small" style={{ background: 'rgba(22,119,255,0.12)' }}>
            <b>我：</b>{turn.question}
          </Card>
        </ChainBlock>

        {/* ② 系统执行流水线块（typed 事件流；未接后端＝静态假数据） */}
        <ChainBlock testid="pipeline-block" dot={turn.phase === 'running' ? '#e8b339' : '#8a94a3'}>
          <ExecutionPipeline turn={turn} />
        </ChainBlock>

        {/* ③ 系统回答块 */}
        <ChainBlock testid={`turn-${turn.id}`} dot="#52c41a">
          <Card size="small"
            extra={(
              // 版面联动入口：把右栏切到本轮（真接线＝当前实时轮自动联动，见设计稿 §2）
              <Button size="small" type="link" style={{ padding: 0 }}
                onClick={() => { setPanelTurnId(turn.id); setFocus({ index: null, nonce: 0 }) }}>
                引用与口径
              </Button>
            )}>
            {/* A 级 notice 留一条紧凑 Alert（折叠态流水线下也能感知可信度；B/C 只在流水线里） */}
            <NoticeAlerts notices={turn.notices} />
            {answering && <div style={dim} data-testid="answer-placeholder">正在作答…</div>}
            {turn.answerText
              ? (
                <AnswerView
                  content={turn.answerText}
                  onCite={turn.legacy ? undefined : openCite(turn)}
                  citeHoverCard={turn.legacy ? undefined : hoverCard(turn)} />
              )
              : (!answering && <div style={dim}>本次未产出答案正文。</div>)}
            {/* 链条后续节点：血缘卡 → 追加面（空态各自不出） */}
            <LineageCard lineage={turn.lineage} limit={turn.limit} text={turn.supplement.lineage}
              defaultOpen={turn.id === 't-full'} />
            <SupplementBlocks split={turn.supplement.split} attribution={turn.supplement.attribution} />
            {/* 旧版历史轮降级说明（supplements=null 的旧轮——如实说不清，不假装有明细） */}
            {turn.legacy && (
              <div style={{ ...dim, marginTop: 6 }} data-testid="legacy-note">
                本轮为旧版记录，无引用/口径明细。
              </div>
            )}
            {/* ⑦ 核验徽标行 ＋ ⑧ 档案小字行（run 号/步数/材料数/档案 KB/本地计时）——
                运行中未收口＝无核验无档案，时长已在流水线摘要行，此处不重复出 */}
            {turn.phase !== 'running' && (
              <RunMetaLine runId={turn.runId} verdict={turn.verdicts[0] ?? null} blackbox={turn.blackbox}
                durationS={turn.durationS} />
            )}
          </Card>
        </ChainBlock>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'stretch', height: '100%' }}>
      {/* 左栏 · 静态对话列表（mock 占位——真列表走 A1V2.jsx 的 listRunsV2 分组） */}
      <Card size="small" title={<span>对话{helpIcon('本页是版面 mock：左栏是静态假列表（真对话分组逻辑在「问一问V2」现状页）。')}</span>}
        style={{ width: 250, flexShrink: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 0, overflowY: 'auto' } }}>
        <div style={{ ...dim, marginBottom: 4 }}>{`共 ${MOCK_THREADS.length} 个对话`}</div>
        <List size="small" dataSource={MOCK_THREADS}
          renderItem={t => (
            <List.Item data-selected={t.selected ? 'true' : 'false'}
              style={{
                padding: '4px 6px', borderRadius: 6,
                background: t.selected ? 'rgba(22,119,255,0.18)' : 'transparent'
              }}>
              <div>
                <div style={{ fontSize: 13 }}>{(t.title || '').slice(0, 18)}</div>
                <div style={dim}>{t.meta}</div>
              </div>
            </List.Item>
          )} />
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
            {MOCK_TURNS.map(renderTurn)}
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

      {/* 右栏 · 引用与口径（人话面板——机器腔过程只留在流水线展开态里） */}
      <CitationPanel
        citations={panelTurn.citations} materials={panelTurn.materials}
        lineage={panelTurn.lineage} limit={panelTurn.limit} lineageText={panelTurn.supplement.lineage}
        splitText={panelTurn.supplement.split} attributionText={panelTurn.supplement.attribution}
        focusIndex={focus.index} focusNonce={focus.nonce}
        running={panelTurn.runStatus === 'running'} />
    </div>
  )
}
