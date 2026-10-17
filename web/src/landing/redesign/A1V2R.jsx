/**
 * A1V2R · 问一问V2 重设计（方案 A）**mock 静态版面页**（临时路由 `#/A1V2R`）。
 *
 * 干什么：按设计稿 §3 的答案卡布局，用**真机帧抽出的假数据**（redesign/mockTurns.js）把
 * 新版版面渲出来与现状页 `A1V2.jsx` **并排对比**——Owner 对完版面再谈接归约器。
 *
 * 边界（本轮纪律）：
 * - **不接后端**：零 SSE、零 `/api/v2/*` 调用（全部数据来自 mockTurns.js；本页不发任何请求）。
 * - **不覆盖现状页**：A1V2.jsx 一字未动，本页是新增的临时路由。
 * - 四轮覆盖全形态：①加载中（过程条「正在分析问题…」占位＋Spin）②完整轮（过程条／notice
 *   三级带／理解旁白／正文含 [n]／血缘卡／追加面／核验行／档案小字）③分列轮（长 split 条
 *   限高折叠）④旧版历史轮（正文＋灰字说明，[n] 为死文本）。
 * - 左栏＝静态假列表（不接 `/api/v2/chat/runs`——真列表逻辑留在 A1V2.jsx）。
 * - 右栏＝CitationPanel（引用与口径，宽度 360 ← Owner 拍板区间 340–380）。
 * - 空态纪律：各项无数据＝该位不渲染（组件内实现，本页只透传）。
 *
 * DEBT(docs/runtime-refactor/frontend-redesign-设计.md)：整页连同 redesign/ 与临时路由
 * （registry.REDESIGN_MODULES／roles.js 菜单项／Shell.jsx 懒加载项）只服务施工顺序第 1 步
 * 「mock 静态页对版面」；第 2 步接归约器后本页删除（或按 Owner 裁决替换现状页）。
 */
import { useState } from 'react'
import { Button, Card, Collapse, Input, List, Space, Tag } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import { dim, helpIcon } from '../../components/helpIcon.jsx'
import AnswerView from '../AnswerView.jsx'
import CitationPanel from './CitationPanel.jsx'
import CiteHoverCard from './CiteHoverCard.jsx'
import LineageCard from './LineageCard.jsx'
import NoticeBand from './NoticeBand.jsx'
import ProcessTimeline from './ProcessTimeline.jsx'
import RunMetaLine from './RunMetaLine.jsx'
import SupplementBlocks from './SupplementBlocks.jsx'
import { MOCK_THREADS, MOCK_TURNS } from './mockTurns.js'

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

  function renderTurn(turn) {
    return (
      <div key={turn.id}>
        <Card size="small" style={{ background: 'rgba(22,119,255,0.12)', marginBottom: 8 }}>
          <b>我：</b>{turn.question}
        </Card>
        <Card size="small" style={{ marginBottom: 12 }} data-testid={`turn-${turn.id}`}
          extra={(
            // 版面联动入口：把右栏切到本轮（真接线＝当前实时轮自动联动，见设计稿 §2）
            <Button size="small" type="link" style={{ padding: 0 }}
              onClick={() => { setPanelTurnId(turn.id); setFocus({ index: null, nonce: 0 }) }}>
              引用与口径
            </Button>
          )}>
          {/* ① 过程折叠条（进行中＝「正在分析问题…」占位；完成＝一行摘要，可展开树状时间线） */}
          <ProcessTimeline
            steps={turn.steps} tools={turn.tools} notices={turn.notices} citations={turn.citations}
            running={turn.runStatus === 'running'} durationS={turn.durationS} />
          {/* ② notice 三级带（A 级 Alert／B 级灰折叠条／C 级默认收起） */}
          <NoticeBand notices={turn.notices} />
          {/* ③ 理解旁白（灰折叠条——思考素材，不进正文） */}
          {turn.understanding && (
            <Collapse size="small" style={{ margin: '6px 0' }} items={[{
              key: 'understanding',
              label: <span style={dim}>系统理解</span>,
              children: <div style={{ ...dim, whiteSpace: 'pre-wrap' }}>{turn.understanding}</div>
            }]} />
          )}
          {/* ④ 答案正文（引标 [n]：悬停出材料切片；点击＝右栏定位。旧版轮两样都不传＝死文本） */}
          {turn.answerText
            ? (
              <AnswerView
                content={turn.answerText}
                onCite={turn.legacy ? undefined : openCite(turn)}
                citeHoverCard={turn.legacy ? undefined : hoverCard(turn)} />
            )
            : (turn.runStatus === 'running' ? null : <div style={dim}>本次未产出答案正文。</div>)}
          {/* ⑤ 血缘／查询口径卡（非数据题不出）＋ ⑥ 程序追加面（无块不出） */}
          <LineageCard lineage={turn.lineage} limit={turn.limit} text={turn.supplement.lineage}
            defaultOpen={turn.id === 't-full'} />
          <SupplementBlocks split={turn.supplement.split} attribution={turn.supplement.attribution} />
          {/* 旧版历史轮降级说明（supplements=null 的旧轮——如实说不清，不假装有明细） */}
          {turn.legacy && (
            <div style={{ ...dim, marginTop: 6 }} data-testid="legacy-note">
              本轮为旧版记录，无引用/口径明细。
            </div>
          )}
          {/* ⑦ 核验徽标行 ＋ ⑧ 档案小字行（run 号/步数/材料数/档案 KB/本地计时） */}
          <RunMetaLine runId={turn.runId} verdict={turn.verdicts[0] ?? null} blackbox={turn.blackbox}
            durationS={turn.durationS} />
        </Card>
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

      {/* 中栏 · 对话流（每轮＝过程条→notice 带→理解旁白→正文→血缘卡→追加面→核验行） */}
      <Card size="small" style={{ flex: 1, minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 320, display: 'flex', flexDirection: 'column' } }}>
        <div style={{ ...dim, marginBottom: 8 }}>
          <Tag color="orange">mock 数据 · 静态版面</Tag>
          新版答案卡版面（真机帧假数据，未接后端）：①加载中 ②完整轮 ③分列轮 ④旧版降级。
        </div>
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: 4 }}>
          {MOCK_TURNS.map(renderTurn)}
        </div>
        {/* 输入区（版面位——mock 页不接线发送，按钮如实禁用） */}
        <div style={{ marginTop: 10 }}>
          <Space.Compact style={{ width: '100%' }}>
            <Input placeholder="（mock 页——输入与发送不接线）" disabled />
            <Button type="primary" icon={<SendOutlined />} disabled>发送</Button>
          </Space.Compact>
        </div>
      </Card>

      {/* 右栏 · 引用与口径（人话面板——机器腔过程只留在答案卡折叠条展开态里） */}
      <CitationPanel
        citations={panelTurn.citations} materials={panelTurn.materials}
        lineage={panelTurn.lineage} limit={panelTurn.limit} lineageText={panelTurn.supplement.lineage}
        splitText={panelTurn.supplement.split} attributionText={panelTurn.supplement.attribution}
        focusIndex={focus.index} focusNonce={focus.nonce}
        running={panelTurn.runStatus === 'running'} />
    </div>
  )
}
