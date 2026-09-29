import { useEffect, useRef, useState } from 'react'
import { Graph } from '@antv/g6'
import { Button, Card, Col, Empty, Row, Select, Space, Switch, Table, Tabs, Tag, Tooltip } from 'antd'
import { QuestionCircleOutlined } from '@ant-design/icons'

window.__guides = Object.assign(window.__guides || {}, {
  B5: [
    '「关系网」页签：点图上任一节点（或用"查看节点"下拉）——相连的关系在图和清单里高亮，右栏逐条列出。',
    '点"问：哪些井受过 N-06 注水影响？"——沿受效关系走一步直接出答案，不翻报告；图上自动选中 N-06。',
    '关掉图例"井（3）"——井节点和相关关系全部隐去，右栏同步；再点恢复。',
    '切「抽取设置」页签——实体类型、关系标签示例、自定义指令在这里配置，保存后下次入库生效。',
    '切「建图方式（5）」页签——对比五种建图做法何时选谁。',
    '切「三道检查（3）」页签——建图时、入库前、查询时各有一道检查。'
  ]
})
window.__traces = Object.assign(window.__traces || {}, {
  B5: 'F40 抽取图谱 · F41 B/C/E 派速览 · F42 五流派擂台 · F55 图谱三接入点 · m6/m16 卡'
})

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

// —— 图谱数据（全部取自报告与台账的既有事实；节点 9 个 · 关系 10 条）——
const NODES = [
  { id: 'N-06', label: 'N-06（注水井）', type: '井', short: 'N-06', sub: '注水井' },
  { id: 'N-02', label: 'N-02（采油井）', type: '井', short: 'N-02', sub: '采油井' },
  { id: 'N-11', label: 'N-11（采油井）', type: '井', short: 'N-11', sub: '采油井' },
  { id: '渤南', label: '区块：渤南', type: '区块', short: '渤南', sub: '区块' },
  { id: '渤中', label: '区块：渤中', type: '区块', short: '渤中', sub: '区块' },
  { id: 'CEP-A', label: '平台 CEP-A', type: '平台', short: 'CEP-A', sub: '平台' },
  { id: 'CEP-B', label: '平台 CEP-B', type: '平台', short: 'CEP-B', sub: '平台' },
  { id: '渤海油田', label: '渤海油田', type: '油田', short: '渤海油田', sub: '油田' },
  { id: '检泵', label: '措施：检泵（N-11）', type: '措施', short: '检泵', sub: '措施（N-11）' }
]
const NAME = Object.fromEntries(NODES.map(n => [n.id, n.label]))
const TYPE_OF = Object.fromEntries(NODES.map(n => [n.id, n.type]))
const TYPE_COLOR = { 井: 'blue', 区块: 'green', 平台: 'purple', 油田: 'gold', 措施: 'orange' }
const TYPE_HEX = { 井: '#3b8dff', 区块: '#52c41a', 平台: '#9254de', 油田: '#faad14', 措施: '#fa8c16' }
const REL_HEX = { 隶属: '#57a75f', 承载: '#a78bde', 受效: '#4aa3ff', 作用于: '#e8a23d' }
const REL_TAG = { 隶属: 'green', 承载: 'purple', 受效: 'blue', 作用于: 'orange' }

// bend＝贝塞尔控制点（绕开中途节点）；lt＝关系名标签在线上的位置（0–1）
const EDGES = [
  { from: 'N-02', rel: '隶属', to: '渤南', lt: 0.32 },
  { from: 'N-06', rel: '隶属', to: '渤南', bend: [60, 210], lt: 0.36 },
  { from: 'N-11', rel: '隶属', to: '渤中', lt: 0.75 },
  { from: '渤南', rel: '隶属', to: '渤海油田', lt: 0.5 },
  { from: '渤中', rel: '隶属', to: '渤海油田', lt: 0.5 },
  { from: 'CEP-A', rel: '承载', to: 'N-02', lt: 0.5 },
  { from: 'CEP-A', rel: '承载', to: 'N-06', lt: 0.5 },
  { from: 'CEP-B', rel: '承载', to: 'N-11', lt: 0.5 },
  { from: 'N-06', rel: '受效', to: 'N-02', lt: 0.5, note: '劈分系数合计＝1 · 响应起始日随台账' },
  { from: '检泵', rel: '作用于', to: 'N-11', lt: 0.5, note: '批次 20260911-T3' }
]

const LEGEND = [
  { type: '井', count: 3 },
  { type: '区块', count: 2 },
  { type: '平台', count: 2 },
  { type: '油田', count: 1 },
  { type: '措施', count: 1 }
]

const NODE_OPTIONS = LEGEND.map(l => ({
  label: `${l.type}（${l.count}）`,
  options: NODES.filter(n => n.type === l.type).map(n => ({ value: n.id, label: n.label }))
}))

// —— 抽取设置：实体类型清单 / 关系标签示例（示例与说明取自当前图与对象关系台账）——
const ENTITY_ROWS = LEGEND.map(l => ({
  key: l.type, type: l.type, count: l.count,
  members: NODES.filter(n => n.type === l.type).map(n => n.short).join('、')
}))
const REL_ROWS = [
  { key: '隶属', rel: '隶属', eg: 'N-02 —隶属→ 渤南', desc: '井属于哪个区块，区块属于哪个油田' },
  { key: '承载', rel: '承载', eg: '平台 CEP-A —承载→ N-02', desc: '井装在哪个平台上' },
  { key: '受效', rel: '受效', eg: 'N-06 —受效→ N-02', desc: '哪口注水井的注水，效果落在哪口油井上（劈分系数合计＝1）' },
  { key: '作用于', rel: '作用于', eg: '措施：检泵（N-11）—作用于→ N-11', desc: '压裂 / 酸化等措施做在哪口井上' }
]

// —— 建图方式（5 种）与三道检查（建图时 / 入库前 / 查询时）——
const WAY_ITEMS = [
  { key: 'D', label: 'D 抽取图谱（本库在用）', text: '逐段抽"谁—什么关系→谁"，类型清单与关系标签逐一对号把关；应用顺手、上手快。要上生产的域，建议再配 A 治理仓。' },
  { key: 'A', label: 'A 治理仓', text: '先有受治理的术语与关系仓（每条带负责人、版本），抽取照仓对号入座；上生产选它。' },
  { key: 'B', label: 'B 聚类', text: '不知道有哪些类型时先自由发现：抽名词→自动聚类→给组起名；新域探路用，探完收编进治理仓。' },
  { key: 'C', label: 'C 两步走', text: '先列概念清单、再排层次结构，快速出第一版验证想法；层次易铺平是它的坑。' },
  { key: 'E', label: 'E 直给', text: '一个提示词端到端，半小时出活——但措辞敏感、两次跑两样，适合先试想法，不用于正式环境。' }
]
const GATE_ITEMS = [
  { key: 'build', label: '建图时', text: '抽取哪些类型由库里的类型清单说了算：清单与领域术语表逐一对号，对不上的类型不自创——避免同一个词在不同地方指不同的东西。' },
  { key: 'gate', label: '入库前', text: '抽出来的关系先做入库检查，再进关系网：类型对不上的不建边、原文里没有依据的不建边。被拦下的边不进图，图和台账始终对得上。' },
  { key: 'query', label: '查询时', text: '提问先精确锚定（如 @N-06）直达相关节点，再沿关系网找答案，图检索兜底；黑话和禁用词（如"躺井"）按术语库拦下；超出业务范围的问题先拒答。' }
]

const edgeText = e => `${NAME[e.from]} —${e.rel}→ ${NAME[e.to]}`
const edgeKey = e => `${e.from}|${e.rel}|${e.to}`

// —— AntV G6 5.x 关系图：层次布局自动排布（油田→区块/平台→井，新增实体只需加数据行）；
//    点节点高亮相邻、其余淡化；图例关掉的节点变虚影，两端被隐的关系从图上隐藏 ——
const toG6Node = n => ({ id: n.id, data: { type: n.type, short: n.short, sub: n.sub } })
const toG6Edge = e => ({
  id: edgeKey(e),
  source: e.from,
  target: e.to,
  type: e.bend ? 'quadratic' : 'line',
  data: { rel: e.rel, note: e.note || '', from: e.from, to: e.to },
  style: e.bend ? { curveOffset: 42 } : undefined
})

function GraphG6({ sel, visible, onPick }) {
  const boxRef = useRef(null)
  const graphRef = useRef(null)
  const pickRef = useRef(onPick)
  pickRef.current = onPick
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const graph = new Graph({
      container: boxRef.current,
      autoFit: 'view',
      padding: 24,
      autoResize: true,
      background: '#161b22',
      theme: 'dark',
      animation: false,
      data: { nodes: NODES.map(toG6Node), edges: EDGES.map(toG6Edge) },
      layout: { type: 'antv-dagre', rankdir: 'BT', nodesep: 40, ranksep: 48 },
      node: {
        type: 'rect',
        style: {
          size: [96, 40],
          radius: 9,
          fill: d => TYPE_HEX[d.data.type],
          fillOpacity: 0.12,
          stroke: d => TYPE_HEX[d.data.type],
          lineWidth: 1.4,
          cursor: 'pointer',
          iconText: d => d.data.short,
          iconFontSize: 12,
          iconFontWeight: 600,
          iconFill: '#e6edf3',
          labelText: d => d.data.sub,
          labelPlacement: 'bottom',
          labelOffsetY: 6,
          labelFill: d => TYPE_HEX[d.data.type],
          labelFontSize: 10,
          labelFontWeight: 600
        },
        state: {
          highlight: {
            lineWidth: 2,
            stroke: '#4a9dff',
            fillOpacity: 0.28,
            halo: true,
            haloStroke: '#4a9dff',
            haloLineWidth: 12,
            haloStrokeOpacity: 0.35
          },
          active: {
            lineWidth: 2,
            stroke: '#7ab3ff'
          },
          dim: { iconOpacity: 0.55, labelFillOpacity: 0.5, strokeOpacity: 0.5 },
          ghost: { lineDash: [4, 3], strokeOpacity: 0.3, fillOpacity: 0.05, iconOpacity: 0.25, labelFillOpacity: 0.25 }
        }
      },
      edge: {
        style: {
          stroke: d => REL_HEX[d.data.rel],
          strokeOpacity: 0.35,
          lineWidth: 1.3,
          endArrow: true,
          endArrowSize: 8,
          labelText: d => d.data.rel,
          labelFill: '#8a94a3',
          labelFontSize: 10.5,
          labelFontWeight: 600,
          labelBackground: true,
          labelBackgroundFill: '#161b22',
          labelBackgroundOpacity: 0.85,
          labelBackgroundRadius: 3,
          labelBackgroundLineWidth: 0,
          labelPadding: [1, 3]
        },
        state: {
          highlight: d => ({
            stroke: REL_HEX[d.data.rel],
            strokeOpacity: 1,
            lineWidth: 2.3,
            labelFill: REL_HEX[d.data.rel],
            labelFontWeight: 700
          }),
          active: d => ({ stroke: REL_HEX[d.data.rel], strokeOpacity: 0.9, lineWidth: 2 }),
          dim: d => ({ stroke: REL_HEX[d.data.rel], strokeOpacity: 0.15, labelFillOpacity: 0.4 })
        }
      },
      behaviors: [
        'zoom-canvas',
        'drag-canvas',
        'drag-element',
        { type: 'hover-activate', degree: 1, direction: 'both', state: 'active' }
      ],
      plugins: [{
        type: 'tooltip',
        trigger: 'hover',
        getContent: (evt, items) => {
          const d = items && items[0]
          if (!d) return ''
          if (evt.targetType === 'edge') {
            const note = d.data && d.data.note
            return `<b>${NAME[d.data.from]} —${d.data.rel}→ ${NAME[d.data.to]}</b>${note ? `<div style="color:#8a94a3;margin-top:2px">${note}</div>` : ''}`
          }
          return `<b>${NAME[d.id]}</b>`
        },
        style: {
          background: '#1c2128',
          border: '1px solid #30363d',
          borderRadius: 6,
          color: '#e6edf3',
          fontSize: 12,
          padding: '6px 10px',
          boxShadow: '0 6px 16px rgba(0,0,0,0.45)'
        }
      }]
    })

    graphRef.current = graph
    window.__b5graph = graph // 暴露实例供控制台/自动化检查（节点 9 · 关系 10）
    graph.on('node:click', evt => pickRef.current(String(evt.target.id)))
    let alive = true
    graph.render().then(() => { if (alive) setReady(true) })
    return () => {
      alive = false
      if (window.__b5graph === graph) window.__b5graph = undefined
      graphRef.current = null
      graph.destroy()
    }
  }, [])

  // 选中/图例变化 → 批量落图：sel 与相邻 highlight、其余 dim；图例关掉的节点 ghost、相关边 visibility hidden
  useEffect(() => {
    const graph = graphRef.current
    if (!graph || !ready) return
    const shown = id => visible[TYPE_OF[id]]
    const shownEdges = EDGES.filter(e => shown(e.from) && shown(e.to))
    const states = {}
    NODES.forEach(n => {
      if (!shown(n.id)) { states[n.id] = ['ghost']; return }
      if (sel === n.id) { states[n.id] = ['highlight']; return }
      const adj = shownEdges.some(e => (e.from === sel || e.to === sel) && (e.from === n.id || e.to === n.id))
      states[n.id] = adj ? [] : ['dim']
    })
    EDGES.forEach(e => { states[edgeKey(e)] = sel && (e.from === sel || e.to === sel) ? ['highlight'] : ['dim'] })
    graph.setElementState(states, false)
    const vis = {}
    EDGES.forEach(e => { vis[edgeKey(e)] = shown(e.from) && shown(e.to) ? 'visible' : 'hidden' })
    graph.setElementVisibility(vis, false)
  }, [sel, visible, ready])

  return (
    <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 8 }}>
      <div ref={boxRef} style={{ width: '100%', height: 400 }} />
    </div>
  )
}

export default function B5() {
  const [tab, setTab] = useState('net') // net | extract | ways | gates
  const [sel, setSel] = useState('N-06')
  const [visible, setVisible] = useState({ 井: true, 区块: true, 平台: true, 油田: true, 措施: true })
  const [answered, setAnswered] = useState(false)
  const [saved, setSaved] = useState(false)

  const isShown = id => visible[TYPE_OF[id]]
  const shownNodes = NODES.filter(n => isShown(n.id))
  const shownEdges = EDGES.filter(e => isShown(e.from) && isShown(e.to))
  const adjEdges = sel ? shownEdges.filter(e => e.from === sel || e.to === sel) : []

  function ask() {
    setAnswered(true)
    setSel('N-06')
  }

  const edgeCols = [
    { title: '起点', dataIndex: 'from', width: 150, render: (v, e) => <span style={{ opacity: e._act ? 1 : 0.5 }}>{NAME[v]}</span> },
    { title: '关系', dataIndex: 'rel', width: 88, render: (v, e) => <Tag color={REL_TAG[v]} style={{ marginInlineEnd: 0, opacity: e._act ? 1 : 0.5 }}>{v}</Tag> },
    { title: '终点', dataIndex: 'to', width: 150, render: (v, e) => <span style={{ opacity: e._act ? 1 : 0.5 }}>{NAME[v]}</span> },
    { title: '注记', dataIndex: 'note', render: (v, e) => v
      ? <span style={{ fontSize: 12, color: '#8a94a3', opacity: e._act ? 1 : 0.5 }}>{v}</span>
      : <span style={{ fontSize: 12, color: '#8a94a3', opacity: e._act ? 0.6 : 0.3 }}>—</span> }
  ]
  const edgeRows = shownEdges.map(e => ({ ...e, key: edgeKey(e), _act: sel && (e.from === sel || e.to === sel) }))

  return (
    <div>
      <Card
        title={
          <Tabs
            activeKey={tab} size="small" onChange={setTab}
            items={[
              { key: 'net', label: `关系网（${EDGES.length}）` },
              { key: 'extract', label: '抽取设置' },
              { key: 'ways', label: `建图方式（${WAY_ITEMS.length}）` },
              { key: 'gates', label: `三道检查（${GATE_ITEMS.length}）` }
            ]}
          />
        }
        extra={
          <Space size={4}>
            <span style={{ color: '#8a94a3', fontSize: 12 }}>关系必须原文有依据 · 类型对不上不建边 · 拿不准的宁可不建</span>
            {helpIcon(<>
              把报告与台账里"谁—什么关系→谁"连成关系网：井—隶属→区块、平台—承载→井、注水井—受效→油井。<br />
              关系入库前先做检查：类型对不上的不建边、原文里没有依据的不建边，拿不准的宁可不建；被拦下的边不进图，图和台账始终对得上。<br />
              当前库装配 3 口样本井（全油田 120 口在产井），节点与关系全部来自报告与台账。
            </>)}
          </Space>
        }
      >
        {tab === 'net' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Space wrap size={16}>
                <Space size={2}>
                  <span style={{ fontSize: 12, color: '#8a94a3' }}>图例</span>
                  {helpIcon(<>点类型开关隐去/显示该类节点；两端任一被隐去的关系同步隐去，右侧相邻关系面板同步刷新。</>)}
                </Space>
                {LEGEND.map(l => (
                  <Space key={l.type} size={6}>
                    <Switch size="small" checked={visible[l.type]}
                      onChange={v => setVisible(p => ({ ...p, [l.type]: v }))} />
                    <span style={{ fontSize: 13 }}>
                      <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: TYPE_HEX[l.type], marginRight: 6 }} />
                      {l.type}（{l.count}）
                    </span>
                  </Space>
                ))}
                <Space size={4}>
                  <span style={{ fontSize: 12, color: '#8a94a3' }}>查看节点</span>
                  <Select size="small" showSearch optionFilterProp="label" style={{ width: 210 }}
                    value={sel} onChange={setSel} options={NODE_OPTIONS} />
                </Space>
              </Space>
              <span style={{ color: '#8a94a3', fontSize: 12 }}>
                {`显示 ${shownNodes.length} / ${NODES.length} 节点 · ${shownEdges.length} / ${EDGES.length} 关系`}
              </span>
            </div>
            <Row gutter={16} align="top">
              <Col span={14}>
                <GraphG6 sel={sel} visible={visible} onPick={setSel} />
                <div style={{ display: 'flex', alignItems: 'center', margin: '14px 0 8px' }}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>关系清单</span>
                  {helpIcon(<>只收通过入库检查的关系：类型对不上、原文里没有依据的边不会出现在这里。点上方图例开关可整类隐去/恢复；选中节点后，与它相连的关系在这里高亮。</>)}
                  <span style={{ marginLeft: 'auto', fontSize: 12, color: '#8a94a3' }}>{`共 ${shownEdges.length} 条`}</span>
                </div>
                <Table
                  size="small" columns={edgeCols} dataSource={edgeRows} pagination={false}
                  rowClassName={e => (e._act ? 'ant-table-row-selected' : '')}
                  locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前图例下没有可见关系。" /> }}
                />
              </Col>
              <Col span={10}>
                <Card size="small" title={`所选节点的相邻关系（${adjEdges.length}）`}>
                  {sel && <Tag color={TYPE_COLOR[TYPE_OF[sel]]}>{NAME[sel]}</Tag>}
                  {adjEdges.length > 0 ? (
                    <div style={{ marginTop: 8 }}>
                      {adjEdges.map(e => (
                        <Card key={edgeKey(e)} size="small" style={{ marginBottom: 8, background: 'rgba(255,255,255,0.04)' }}>
                          <b style={{ fontSize: 13 }}>{edgeText(e)}</b>
                          {e.note && <div style={{ fontSize: 12, color: '#8a94a3' }}>{e.note}</div>}
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <Empty description={<span style={{ fontSize: 13 }}>该节点暂无可见关系：若相关类型被图例开关隐去，打开开关即可恢复。</span>} />
                  )}
                </Card>
                <Card
                  size="small" style={{ marginTop: 16 }}
                  title={<span>走关系回答问题（不翻全文）{helpIcon(<>沿关系网走一步就能回答的问题，不用翻报告全文；回答后图上自动选中相关节点。</>)}</span>}
                >
                  <Button type="primary" size="small" onClick={ask}>问：哪些井受过 N-06 注水影响？</Button>
                  {answered && (
                    <Card size="small" style={{ marginTop: 12, background: 'rgba(255,255,255,0.04)' }}>
                      <Tag color="blue">图谱问答</Tag>
                      答：沿"受效"关系走一步：N-02（受效油井，劈分系数随台账）。当前库装配 3 口样本井（全油田 120 口在产井）；正式环境沿关系网遍历，返回全部受效井。
                    </Card>
                  )}
                </Card>
              </Col>
            </Row>
          </>
        )}

        {tab === 'extract' && (
          <>
            <Row gutter={24} align="top">
              <Col span={11}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
                  实体类型清单{helpIcon(<>抽取哪些实体类型按库配置：默认 11 类通用实体，也可换成领域术语表逐一对号；对不上的类型不自创。</>)}
                </div>
                <Table size="small" pagination={false} rowKey="key"
                  columns={[
                    { title: '类型', dataIndex: 'type', render: v => (
                      <span><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: TYPE_HEX[v], marginRight: 8 }} />{v}</span>
                    ) },
                    { title: '图中节点', dataIndex: 'count', width: 90 },
                    { title: '节点清单', dataIndex: 'members' }
                  ]}
                  dataSource={ENTITY_ROWS} />
              </Col>
              <Col span={13}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
                  关系标签与示例{helpIcon(<>示例取自当前图里已入库的关系；关系标签按库配置，抽取时照标签对号，清单之外的标签不立边。</>)}
                </div>
                <Table size="small" pagination={false} rowKey="key"
                  columns={[
                    { title: '关系标签', dataIndex: 'rel', width: 90, render: v => <Tag color={REL_TAG[v]} style={{ marginInlineEnd: 0 }}>{v}</Tag> },
                    { title: '示例（取自当前图）', dataIndex: 'eg' },
                    { title: '说明', dataIndex: 'desc', width: 260, render: v => <span style={{ fontSize: 12, color: '#8a94a3' }}>{v}</span> }
                  ]}
                  dataSource={REL_ROWS} />
              </Col>
            </Row>
            <div style={{ fontWeight: 600, fontSize: 13, margin: '16px 0 8px' }}>
              自定义指令{helpIcon(<>随抽取任务生效的硬规则：原文里找不到依据的关系不建边，宁可少建、不建错；类型清单之外的类型不许自创。</>)}
            </div>
            <div className="code-block">自定义指令：关系必须原文有依据；拿不准宁可跳过，不许创造新类型</div>
            <Space style={{ marginTop: 12 }}>
              <Button type="primary" size="small" onClick={() => setSaved(true)}>保存抽取设置</Button>
              {saved && <span style={{ fontSize: 12, color: '#8a94a3' }}>已保存——设置在下次入库时生效。</span>}
            </Space>
          </>
        )}

        {tab === 'ways' && (
          <Tabs
            size="small" defaultActiveKey="D"
            items={WAY_ITEMS.map(w => ({ key: w.key, label: w.label, children: <div style={{ fontSize: 13 }}>{w.text}</div> }))}
          />
        )}

        {tab === 'gates' && (
          <Tabs
            size="small" defaultActiveKey="build"
            items={GATE_ITEMS.map(g => ({ key: g.key, label: g.label, children: <div style={{ fontSize: 13 }}>{g.text}</div> }))}
          />
        )}
      </Card>
    </div>
  )
}
