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
 * 2. **各来源说法不一**（supplement{block:'split'}——**右栏唯一出现处**；打磨批③：
 *    「按来源列出」（attribution）块按 Owner 拍板整块删掉——它与引用清单同源重复
 *    （引用清单＝正文 [n] 配对材料逐条定位；按来源列出＝同一批 citation 帧的机械文本再生产）；
 *    各来源说法不一＝有独立信息量的矛盾对照，保留）。
 * 3. **血缘／查询口径卡**（LineageCard——非数据题不出）。
 * 空态：无引用＝「本回合无引用」；无血缘/无 split＝各自不出（不报错不伪造）。
 *
 * 决策树入口保留（Owner 拍板第 4 条）：入口常在，点开只出一个说明性 Modal——
 * 真决策树（`pages/DecisionTreeV2.jsx`）本体接回在后续版本（本票不动本入口）。
 */
import { useEffect, useState } from 'react'
import { Button, Card, Collapse, Modal, Tag } from 'antd'
import { ApartmentOutlined, DownOutlined, UpOutlined } from '@ant-design/icons'
import { dim, helpIcon } from '../../components/helpIcon.jsx'
import { groupCitations, parseSupplement, trustLabel } from './cites.js'
import LineageCard from './LineageCard.jsx'

const CLAMP_LINES = 6
/** 限高判定：真行数超限，或单行折行后估计超限（≈6 行 × 40 字/行；jsdom 无排版量测）。 */
const CLAMP_CHARS = 240

/** 单条内容（限高 + 展开看全文——真机 split 单条可至 700+ 字含全角空格表格行）。 */
function ClampedText({ text, testId }) {
  const [open, setOpen] = useState(false)
  const long = String(text ?? '').split('\n').length > CLAMP_LINES || String(text ?? '').length > CLAMP_CHARS
  const clamped = long && !open
  return (
    <div>
      <div data-testid={testId} data-clamped={clamped ? 'true' : 'false'}
        style={{
          fontSize: 12, lineHeight: 1.7, whiteSpace: 'pre-wrap',
          ...(clamped
            ? { display: '-webkit-box', WebkitLineClamp: CLAMP_LINES, WebkitBoxOrient: 'vertical', overflow: 'hidden' }
            : {})
        }}>
        {text}
      </div>
      {long && (
        <Button size="small" type="link" style={{ padding: 0, height: 18 }} onClick={() => setOpen(o => !o)}>
          {open ? <>收起 <UpOutlined style={{ fontSize: 10 }} /></> : <>展开看全文 <DownOutlined style={{ fontSize: 10 }} /></>}
        </Button>
      )}
    </div>
  )
}

/** split 单条（`[n]`＋来源＋原文——程序面不洗白）。 */
function SplitItem({ it }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ fontSize: 12 }}>
        <Tag style={{ fontSize: 10 }}>{`[${it.index}]`}</Tag>
        {it.source && <span>{it.source}</span>}
      </div>
      <ClampedText text={it.text} testId={`supp-item-${it.index}`} />
    </div>
  )
}

/**
 * @param citations      引用帧数组（按 index 升序）
 * @param materials      材料帧数组（citation↔observation 按 index 配对）
 * @param lineage/limit  observation.payload 的结构化血缘（无＝null）
 * @param lineageText    supplement{block:'lineage'}.text（纯文本兜底）
 * @param splitText      supplement{block:'split'}.text
 * @param focusIndex     外部联动定位（正文引标点击传入的 index；null＝无）
 * @param focusNonce     外部定位拍号（同 index 重复点也重走一次定位/滚动）
 * @param running        回合进行中（空态文案换「检索中」）
 */
export default function CitationPanel({
  citations = [], materials = [], lineage = null, limit = null, lineageText = '',
  splitText = null, focusIndex = null, focusNonce = 0, running = false
}) {
  const [picked, setPicked] = useState(null)
  const [treeOpen, setTreeOpen] = useState(false)

  // 正文引标点击＝面板联动（外部定位优先，接管本地面板态；nonce 变＝重走一拍）
  useEffect(() => {
    if (focusIndex != null) setPicked(focusIndex)
  }, [focusIndex, focusNonce])

  // 定位后把该条滚进视野（jsdom 无 scrollIntoView 实现——`?.` 兜底，同页面其余滚动位惯例）
  useEffect(() => {
    if (picked == null) return
    document.getElementById(`cite-${picked}`)?.scrollIntoView?.({ block: 'nearest' })
  }, [picked])

  const groups = groupCitations(citations)
  const materialOf = idx => materials.find(m => m.index === idx)
  const split = splitText ? parseSupplement(splitText) : null

  return (
    <Card
      size="small"
      title={<span>引用与口径{helpIcon('这一栏回答「答案里的说法出自哪里」：按来源分组的引用清单、查询口径（这数哪来的）、各来源说法不一的对照说明。点清单里一条＝定位到那支材料。')}</span>}
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

      {/* 各来源说法不一（split——右栏唯一出现处；无块不出。默认收起：次要位不抢引用清单） */}
      {split && split.items.length > 0 && (
        <Collapse size="small" style={{ margin: '6px 0' }} data-testid="supp-split-block"
          items={[{
            key: 'split',
            label: <span style={dim}>各来源说法不一 · 点开对照</span>,
            children: (
              <div data-testid="supp-split">
                {split.head && <div style={{ ...dim, marginBottom: 4 }}>{split.head}</div>}
                {split.items.map(it => <SplitItem key={it.index} it={it} />)}
              </div>
            )
          }]} />
      )}

      <LineageCard lineage={lineage} limit={limit} text={lineageText} />

      <Modal open={treeOpen} footer={null} onCancel={() => setTreeOpen(false)} title="决策树（占位）">
        <div style={{ fontSize: 13, lineHeight: 1.9 }}>
          完整决策树（按问句点亮主链路径）本体接回在后续版本——此处只展示入口位置。
        </div>
      </Modal>
    </Card>
  )
}
