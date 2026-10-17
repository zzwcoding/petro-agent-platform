/**
 * CitationPanel · 右栏「引用与口径」（设计稿 §2 方案 A、§3.3）——人话辅助面板。
 *
 * 位置：右栏（宽度 360，Owner 拍板区间 340–380）；机器腔过程**不在本栏**（只留在答案卡
 * 过程折叠条的展开态里）。
 *
 * 内容自顶向下：
 * 1. **引用清单**——按 `source` 去重分组（同文档多支切片归一组，组头给来源＋条数），
 *    trust 白话徽标（权威台账/台账/报告/系统注记）；点某条＝该条高亮＋「已定位」并出材料
 *    原文（无配对＝如实写「材料未在回合内渲染」，不虚构）；`trust=notice` 的按**程序声明**
 *    渲染，点明「系统生成的声明，不是文档原文」。
 * 2. **血缘／查询口径卡**（LineageCard——非数据题不出）。
 * 3. **程序追加面**（SupplementBlocks——无块不出）。
 * 空态：无引用＝「本回合无引用」；无血缘/无追加面＝各自不出（不报错不伪造）。
 *
 * 决策树入口保留（Owner 拍板第 4 条）：本页是 mock 静态页，点开只出一个说明性 Modal，
 * 真决策树（`pages/DecisionTreeV2.jsx`）接线在接归约器那步（设计 §5 第 2/3 步）。
 */
import { useEffect, useState } from 'react'
import { Button, Card, Modal, Tag } from 'antd'
import { ApartmentOutlined } from '@ant-design/icons'
import { dim, helpIcon } from '../../components/helpIcon.jsx'
import { groupCitations, trustLabel } from './cites.js'
import LineageCard from './LineageCard.jsx'
import SupplementBlocks from './SupplementBlocks.jsx'

/**
 * @param citations      引用帧数组（按 index 升序）
 * @param materials      材料帧数组（citation↔observation 按 index 配对）
 * @param lineage/limit  observation.payload 的结构化血缘（无＝null）
 * @param lineageText    supplement{block:'lineage'}.text（纯文本兜底）
 * @param splitText      supplement{block:'split'}.text
 * @param attributionText supplement{block:'attribution'}.text
 * @param focusIndex     外部联动定位（正文引标点击传入的 index；null＝无）
 * @param focusNonce     外部定位拍号（同 index 重复点也重走一次定位/滚动）
 * @param running        回合进行中（空态文案换「检索中」）
 */
export default function CitationPanel({
  citations = [], materials = [], lineage = null, limit = null, lineageText = '',
  splitText = null, attributionText = null, focusIndex = null, focusNonce = 0, running = false
}) {
  const [picked, setPicked] = useState(null)
  const [treeOpen, setTreeOpen] = useState(false)

  // 正文引标点击＝面板联动（外部定位优先，接管本地面板态；nonce 变＝重走一拍）
  useEffect(() => {
    if (focusIndex != null) setPicked(focusIndex)
  }, [focusIndex, focusNonce])

  // 定位后把该条滚进视野（jsdom 无 scrollIntoView 实现——`?.` 兜底，同 A1V2.jsx 惯例）
  useEffect(() => {
    if (picked == null) return
    document.getElementById(`cite-${picked}`)?.scrollIntoView?.({ block: 'nearest' })
  }, [picked])

  const groups = groupCitations(citations)
  const materialOf = idx => materials.find(m => m.index === idx)

  return (
    <Card
      size="small"
      title={<span>引用与口径{helpIcon('这一栏回答「答案里的说法出自哪里」：按来源分组的引用清单、查询口径（这数哪来的）、程序追加的对照说明。点清单里一条＝定位到那支材料。')}</span>}
      extra={(
        <Button size="small" icon={<ApartmentOutlined />} onClick={() => setTreeOpen(true)}>决策树</Button>
      )}
      style={{ width: 360, flexShrink: 0, minHeight: 0, display: 'flex', flexDirection: 'column' }}
      styles={{ body: { flex: 1, minHeight: 0, overflowY: 'auto', paddingRight: 4 } }}
      data-testid="citation-panel">

      {groups.length === 0 ? (
        <div style={dim}>{running ? '检索中——材料到位后这里出引用清单。' : '本回合无引用。'}</div>
      ) : (
        <>
          <div style={{ ...dim, marginBottom: 6 }}>
            {`共 ${citations.length} 支引用 · 来自 ${groups.length} 处来源`}
          </div>
          {groups.map(g => (
            <div key={g.source} style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 12, marginBottom: 4 }}>
                <Tag style={{ fontSize: 10 }}>{trustLabel(g.trust)}</Tag>
                <span>{g.source || '来源未标注'}</span>
                <span style={dim}>{` · ${g.items.length} 支`}</span>
              </div>
              {g.items.map(c => {
                const active = picked === c.index
                const mat = materialOf(c.index)
                const isNotice = c.trust === 'notice'
                return (
                  <div key={c.index} id={`cite-${c.index}`} data-testid={`cite-item-${c.index}`}
                    onClick={() => setPicked(c.index)}
                    style={{
                      cursor: 'pointer', padding: '4px 6px', borderRadius: 4, marginBottom: 2,
                      border: active ? '1px solid #4a9dff' : '1px solid transparent',
                      background: active ? 'rgba(22,119,255,0.14)' : 'transparent'
                    }}>
                    <div style={{ fontSize: 12 }}>
                      <Tag style={{ fontSize: 10 }}>{`[${c.index}]`}</Tag>
                      <span style={dim}>{c.source_id || '（无出处编号）'}</span>
                      {active && <Tag color="blue" style={{ marginLeft: 6, fontSize: 10 }}>已定位</Tag>}
                    </div>
                    {active && (
                      <div style={{ ...dim, marginTop: 4, whiteSpace: 'pre-wrap' }}>
                        {isNotice && <div>这一条是系统生成的声明，不是文档原文。</div>}
                        {mat?.content || '（材料未在回合内渲染）'}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </>
      )}

      <LineageCard lineage={lineage} limit={limit} text={lineageText} />
      <SupplementBlocks split={splitText} attribution={attributionText} />

      <Modal open={treeOpen} footer={null} onCancel={() => setTreeOpen(false)} title="决策树（mock 占位）">
        <div style={{ fontSize: 13, lineHeight: 1.9 }}>
          本页是版面 mock——这里只展示入口位置。完整决策树（按问句点亮主链路径）在后续接线中接回。
        </div>
      </Modal>
    </Card>
  )
}
