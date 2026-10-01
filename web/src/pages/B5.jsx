import { useEffect, useRef, useState } from 'react'
import { Graph } from '@antv/g6'
import { Button, Card, Checkbox, Col, Empty, Input, message, Modal, Row, Select, Space, Switch, Table, Tabs, Tag, Tooltip } from 'antd'
import { DeleteOutlined, QuestionCircleOutlined } from '@ant-design/icons'

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

// —— 抽取设置可交互配置（2026-10-01 Owner 拍板）：初始值＝上述演示常量；改动只存页面内存、刷新还原 ——
// few-shot 示例对初始值：右侧「应抽出三元组」照抄 REL_ROWS.eg（当前图已入库的关系）；
// 左侧「报告原句」为按设定书既有事实（§5/§A.1/§A.4）拟装的演示句，无报告原文直锚
const FEWSHOT_INIT = [
  { in: 'N-02 井隶属于渤南区块。', out: 'N-02 —隶属→ 渤南' },
  { in: 'N-02 井安装在平台 CEP-A 上。', out: '平台 CEP-A —承载→ N-02' },
  { in: 'N-02 井受 N-06 井注水影响（劈分系数合计＝1）。', out: 'N-06 —受效→ N-02' },
  { in: 'N-11 井实施检泵措施（批次 20260911-T3）。', out: '措施：检泵（N-11）—作用于→ N-11' }
]
const INSTRUCTION_INIT = '关系必须原文有依据；拿不准宁可跳过，不许创造新类型'

// —— 示例三源辅助（2026-10-01 Owner 拍板：示例靠系统辅助生成、人审核，手填兜底）——
// 演示边 → 出处句：已有 few-shot 示例句复用对应关系，其余按设定书 §1/§A.1/§A.4 同风格拟装
const EDGE_SRC = {
  'N-02|隶属|渤南': 'N-02 井隶属于渤南区块。',
  'N-06|隶属|渤南': 'N-06 井隶属于渤南区块。',
  'N-11|隶属|渤中': 'N-11 井隶属于渤中区块。',
  '渤南|隶属|渤海油田': '渤南区块隶属于渤海油田。',
  '渤中|隶属|渤海油田': '渤中区块隶属于渤海油田。',
  'CEP-A|承载|N-02': 'N-02 井安装在平台 CEP-A 上。',
  'CEP-A|承载|N-06': 'N-06 井安装在平台 CEP-A 上。',
  'CEP-B|承载|N-11': 'N-11 井安装在平台 CEP-B 上。',
  'N-06|受效|N-02': 'N-02 井受 N-06 井注水影响（劈分系数合计＝1）。',
  '检泵|作用于|N-11': 'N-11 井实施检泵措施（批次 20260911-T3）。'
}
// 报告库原句演示清单（现有 few-shot 句＋同风格扩充；来源标注设定书既有事实口径）
const REPORT_SENTENCES = [
  { text: 'N-02 井隶属于渤南区块。', src: '设定书 §A.1（N-02 采油 · 渤南）', out: 'N-02 —隶属→ 渤南' },
  { text: 'N-02 井安装在平台 CEP-A 上。', src: '设定书 §A.1（N-02 · CEP-A）', out: '平台 CEP-A —承载→ N-02' },
  { text: 'N-02 井受 N-06 井注水影响（劈分系数合计＝1）。', src: '设定书 §5（注水井—受效→油井 · 劈分系数 Σ=1）', out: 'N-06 —受效→ N-02' },
  { text: 'N-06 井隶属于渤南区块。', src: '设定书 §A.1（N-06 注水 · 渤南）', out: 'N-06 —隶属→ 渤南' },
  { text: '渤南区块隶属于渤海油田。', src: '设定书 §1（渤海油田分公司）', out: '渤南 —隶属→ 渤海油田' },
  { text: 'N-11 井实施检泵措施（批次 20260911-T3）。', src: '设定书 §A.4（N-11 检泵 · 批次 20260911-T3）', out: '措施：检泵（N-11）—作用于→ N-11' }
]
// LLM 起草演示模板（按关系词配演示实体对；真实实现起草走 gateway.complete〔B6〕统一 LLM 出口）
const REL_TEMPLATES = {
  隶属: { in: 'N-02 井隶属于渤南区块。', out: 'N-02 —隶属→ 渤南' },
  承载: { in: 'N-11 井安装在平台 CEP-B 上。', out: '平台 CEP-B —承载→ N-11' },
  受效: { in: 'N-06 井对 N-02 井注水见效（劈分系数合计＝1）。', out: 'N-06 —受效→ N-02' },
  作用于: { in: 'N-11 井实施检泵措施（批次 20260911-T3）。', out: '措施：检泵（N-11）—作用于→ N-11' }
}

// —— ? 提示静态文案（操作型帮助；Owner 2026-10-01 企业化清洗批：五流派对照 WAY_TIP 撤除，归产品文档）——
const BUILD_GATE_TIP = (
  <>
    <b>建图时的检查</b>：抽取哪些类型由库里的类型清单说了算：清单与领域术语表逐一对号，对不上的类型不自创——避免同一个词在不同地方指不同的东西。
  </>
)
const QUERY_GATE_TIP = (
  <>
    <b>查询时的检查</b>：提问先精确锚定（如 @N-06）直达相关节点，再沿关系网找答案，图检索兜底；黑话和禁用词（如"躺井"）按术语库拦下；超出业务范围的问题先拒答。<br />
    点击携带此节点信息跳入问一问。
  </>
)

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
      <div ref={boxRef} style={{ width: '100%', height: 560 }} />
    </div>
  )
}

export default function B5() {
  const [tab, setTab] = useState('net') // net | extract
  const [sel, setSel] = useState('N-06')
  const [visible, setVisible] = useState({ 井: true, 区块: true, 平台: true, 油田: true, 措施: true })
  const [saved, setSaved] = useState(false)

  // —— 抽取设置可交互配置（原型态：纯前端内存 state，刷新还原）——
  const [entities, setEntities] = useState(ENTITY_ROWS.map(e => ({ name: e.type, on: true, custom: false })))
  const [newEntity, setNewEntity] = useState('')
  const [rels, setRels] = useState(REL_ROWS.map(r => ({ rel: r.rel, on: true, custom: false })))
  const [newRel, setNewRel] = useState('')
  const [examples, setExamples] = useState(FEWSHOT_INIT.map(f => ({ ...f })))
  const [instruction, setInstruction] = useState(INSTRUCTION_INIT)

  // —— 示例三源辅助弹窗（从已抽结果生成 / 从报告库选句 / LLM 起草；手填「添加示例」兜底）——
  const [edgeModal, setEdgeModal] = useState(false)
  const [sentModal, setSentModal] = useState(false)
  const [draftModal, setDraftModal] = useState(false)
  const [draftRel, setDraftRel] = useState('')

  const addEntity = () => {
    const name = newEntity.trim()
    if (!name) return
    if (entities.some(e => e.name === name)) { message.warning(`类型「${name}」已在清单中`); return }
    setEntities(p => [...p, { name, on: true, custom: true }])
    setNewEntity('')
  }
  const addRel = () => {
    const rel = newRel.trim()
    if (!rel) return
    if (rels.some(r => r.rel === rel)) { message.warning(`关系标签「${rel}」已存在`); return }
    setRels(p => [...p, { rel, on: true, custom: true }])
    setNewRel('')
  }
  function saveExtract() {
    setSaved(true)
    message.success('已保存——下次入库定型，改动已记入活动流。')
  }

  const addExample = pair => {
    setExamples(p => [...p, { in: pair.in, out: pair.out }])
  }
  // 源 1：从已抽结果生成——选当前图已入库的边，出处句＋三元组自动配好
  const pickEdge = key => {
    const e = EDGES.find(x => edgeKey(x) === key)
    if (!e) return
    addExample({ in: EDGE_SRC[key], out: `${NAME[e.from]} —${e.rel}→ ${NAME[e.to]}` })
    setEdgeModal(false)
    message.success('已生成示例，请核对后保存。')
  }
  // 源 2：从报告库选句——三元组侧按建议值预填，人可改
  const pickSentence = i => {
    const s = REPORT_SENTENCES[i]
    addExample({ in: s.text, out: s.out })
    setSentModal(false)
    message.success('已按所选原句预填三元组，请核对后保存。')
  }
  // 源 3：LLM 起草——按关系词配演示实体对，人可改
  const draftExample = () => {
    const w = draftRel.trim()
    if (!w) { message.warning('请先输入关系词'); return }
    const tpl = REL_TEMPLATES[w]
    if (!tpl) { message.warning(`关系词「${w}」暂无起草模板，可改用从已抽结果生成或从报告库选句`); return }
    addExample(tpl)
    setDraftModal(false)
    setDraftRel('')
    message.success('已生成示例草案，请核对后保存。')
  }

  const isShown = id => visible[TYPE_OF[id]]
  const shownEdges = EDGES.filter(e => isShown(e.from) && isShown(e.to))
  const adjEdges = sel ? shownEdges.filter(e => e.from === sel || e.to === sel) : []

  function askWithNode() {
    message.success(`已带上节点：${NAME[sel]}——到问一问提问时将携带此节点上下文`)
    location.hash = '/A1'
  }

  const edgeCols = [
    { title: '起点', dataIndex: 'from', width: 150, render: v => NAME[v] },
    { title: '关系', dataIndex: 'rel', width: 88, render: v => <Tag color={REL_TAG[v]} style={{ marginInlineEnd: 0 }}>{v}</Tag> },
    { title: '终点', dataIndex: 'to', width: 150, render: v => NAME[v] }
  ]
  const edgeRows = (sel ? adjEdges : shownEdges).map(e => ({ ...e, key: edgeKey(e) }))

  return (
    <div>
      <Card
        title={
          <Tabs
            activeKey={tab} size="small" onChange={setTab}
            items={[
              { key: 'net', label: <span>关系网（{EDGES.length}）</span> },
              { key: 'extract', label: <span>抽取设置{helpIcon(BUILD_GATE_TIP)}</span> }
            ]}
          />
        }
        extra={
          helpIcon(<>
            把报告与台账里"谁—什么关系→谁"连成关系网：井—隶属→区块、平台—承载→井、注水井—受效→油井。<br />
            当前库 3 口井，节点与关系全部来自报告与台账。
          </>)
        }
      >
        {tab === 'net' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Space wrap size={16}>
                <Space size={2}>
                  <span style={{ fontSize: 12, color: '#8a94a3' }}>图例</span>
                  {helpIcon(<>点类型开关隐去/显示该类节点；两端任一被隐去的关系同步隐去，右侧关系清单同步刷新。</>)}
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
                  <Tooltip title={QUERY_GATE_TIP}>
                    <span>
                      <Button type="primary" size="small" disabled={!sel} onClick={askWithNode}>带此节点提问</Button>
                    </span>
                  </Tooltip>
                </Space>
              </Space>
            </div>
            {/* 主区左右两栏（2026-10-01 Owner 排版二批）：左＝关系图（约 2/3 宽），右＝关系清单面板（固定宽、独立滚动） */}
            <div style={{ display: 'flex', gap: 16, alignItems: 'stretch' }}>
              <div style={{ flex: 2, minWidth: 0 }}>
                <GraphG6 sel={sel} visible={visible} onPick={setSel} />
              </div>
              <div style={{ width: 400, flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
                <div style={{
                  flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column',
                  background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '10px 12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>关系清单</span>
                    {helpIcon(<>只收通过入库检查的关系——入库前先做检查：类型对不上的不建边、原文里没有依据的不建边，拿不准的宁可不建；被拦下的边不进图，图和台账始终对得上。点左侧图例开关可整类隐去/恢复；选中节点后，这里只列与它相连的关系。</>)}
                  </div>
                  <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
                    <Table
                      size="small" columns={edgeCols} dataSource={edgeRows} pagination={false}
                      locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description={sel ? '该节点暂无可见关系：若相关类型被图例开关隐去，打开开关即可恢复。' : '当前图例下没有可见关系。'} /> }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {tab === 'extract' && (
          <>
            <Row gutter={24} align="top">
              <Col span={11}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
                  实体类型清单（勾选启用）{helpIcon(<>抽取哪些实体类型按库配置：勾选即启用、取消即停用；可新增类型，添加后默认勾选；保存时清单与领域术语表逐一对号，对不上的类型不自创。</>)}
                </div>
                <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '10px 12px' }}>
                  {entities.map((e, i) => (
                    <div key={e.name} style={{ display: 'flex', alignItems: 'center', padding: '3px 0' }}>
                      <Checkbox
                        checked={e.on}
                        onChange={ev => setEntities(p => p.map((x, xi) => xi === i ? { ...x, on: ev.target.checked } : x))}
                        style={{ fontSize: 13 }}
                      >
                        <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: TYPE_HEX[e.name] || '#8a94a3', marginRight: 6 }} />
                        {e.name}
                        {!e.on && <span style={{ fontSize: 11, color: '#8a94a3', marginLeft: 6 }}>停用</span>}
                      </Checkbox>
                      {e.custom && (
                        <Button type="text" size="small" danger icon={<DeleteOutlined />}
                          onClick={() => setEntities(p => p.filter((_, xi) => xi !== i))} />
                      )}
                    </div>
                  ))}
                  <Space.Compact style={{ marginTop: 8 }}>
                    <Input size="small" placeholder="新增类型" value={newEntity}
                      onChange={ev => setNewEntity(ev.target.value)} onPressEnter={addEntity} style={{ width: 170 }} />
                    <Button size="small" onClick={addEntity}>添加</Button>
                  </Space.Compact>
                </div>
              </Col>
              <Col span={13}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
                  关系标签（启用开关）{helpIcon(<>关系标签按库配置，抽取时照标签对号，清单之外的标签不立边；开关停用该标签后暂不参与抽取；可新增标签，自定义标签可删除。</>)}
                </div>
                <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '10px 12px' }}>
                  {rels.map((r, i) => (
                    <div key={r.rel} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '3px 0' }}>
                      <Tag color={REL_TAG[r.rel] || 'default'} style={{ marginInlineEnd: 0 }}>{r.rel}</Tag>
                      <Switch size="small" checked={r.on}
                        onChange={v => setRels(p => p.map((x, xi) => xi === i ? { ...x, on: v } : x))} />
                      <span style={{ fontSize: 12, color: '#8a94a3' }}>{r.on ? '启用' : '停用'}</span>
                      {r.custom && (
                        <Button type="text" size="small" danger icon={<DeleteOutlined />}
                          onClick={() => setRels(p => p.filter((_, xi) => xi !== i))} />
                      )}
                    </div>
                  ))}
                  <Space.Compact style={{ marginTop: 8 }}>
                    <Input size="small" placeholder="新增关系" value={newRel}
                      onChange={ev => setNewRel(ev.target.value)} onPressEnter={addRel} style={{ width: 170 }} />
                    <Button size="small" onClick={addRel}>添加</Button>
                  </Space.Compact>
                </div>
              </Col>
            </Row>
            <div style={{ fontWeight: 600, fontSize: 13, margin: '16px 0 8px', display: 'flex', alignItems: 'center' }}>
              <span>示例（few-shot）{helpIcon(<>每条示例＝报告原句＋应抽出的三元组，抽取时照示例对号；示例质量直接决定抽取准确度。示例可从已抽结果、报告原句或系统起草生成，核对后保存；也可手动添加。</>)}</span>
              <span style={{ marginLeft: 'auto', fontWeight: 400 }}>
                <Space size={8}>
                  <Button size="small" onClick={() => setEdgeModal(true)}>从已抽结果生成</Button>
                  <Button size="small" onClick={() => setSentModal(true)}>从报告库选句</Button>
                  <Button size="small" onClick={() => setDraftModal(true)}>LLM 起草</Button>
                </Space>
              </span>
            </div>
            <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '10px 12px' }}>
              {examples.map((ex, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                  <Input size="small" placeholder="报告原句" value={ex.in}
                    onChange={ev => setExamples(p => p.map((x, xi) => xi === i ? { ...x, in: ev.target.value } : x))}
                    style={{ flex: 1 }} />
                  <span style={{ color: '#8a94a3', flexShrink: 0 }}>→</span>
                  <Input size="small" placeholder="应抽出三元组" value={ex.out}
                    onChange={ev => setExamples(p => p.map((x, xi) => xi === i ? { ...x, out: ev.target.value } : x))}
                    style={{ flex: 1 }} />
                  <Button type="text" size="small" danger icon={<DeleteOutlined />}
                    onClick={() => setExamples(p => p.filter((_, xi) => xi !== i))} />
                </div>
              ))}
              <Button size="small" onClick={() => setExamples(p => [...p, { in: '', out: '' }])}>添加示例</Button>
            </div>
            <div style={{ fontWeight: 600, fontSize: 13, margin: '16px 0 8px' }}>
              自定义指令{helpIcon(<>随抽取任务生效的硬规则：原文里找不到依据的关系不建边，宁可少建、不建错；类型清单之外的类型不许自创。可按库改写。</>)}
            </div>
            <Input.TextArea rows={2} value={instruction}
              onChange={ev => setInstruction(ev.target.value)} />
            <Space style={{ marginTop: 12 }}>
              <Button type="primary" size="small" onClick={saveExtract}>保存抽取设置</Button>
              {saved && <span style={{ fontSize: 12, color: '#8a94a3' }}>已保存——设置在下次入库时生效。</span>}
            </Space>
          </>
        )}
      </Card>

      {/* 示例三源辅助弹窗（原型态本地模拟，交互流程按真实产品设计） */}
      <Modal title="从已抽结果生成示例" open={edgeModal} footer={null} width={680}
        onCancel={() => setEdgeModal(false)}>
        <p style={{ fontSize: 12, color: '#8a94a3', marginTop: 0 }}>
          选择当前图里已入库的一条关系，自动配好示例（原句＋三元组），核对后保存。
        </p>
        <Table
          size="small" rowKey="key" pagination={false}
          dataSource={EDGES.map(e => ({ key: edgeKey(e), from: e.from, rel: e.rel, to: e.to, src: EDGE_SRC[edgeKey(e)] }))}
          columns={[
            { title: '起点', dataIndex: 'from', width: 140, render: v => NAME[v] },
            { title: '关系', dataIndex: 'rel', width: 80, render: v => <Tag color={REL_TAG[v]} style={{ marginInlineEnd: 0 }}>{v}</Tag> },
            { title: '终点', dataIndex: 'to', width: 140, render: v => NAME[v] },
            { title: '出处句', dataIndex: 'src' },
            { title: '', key: 'op', width: 64,
              render: (_, r) => <Button type="link" size="small" style={{ padding: 0 }} onClick={() => pickEdge(r.key)}>选用</Button> }
          ]}
        />
      </Modal>
      <Modal title="从报告库选句" open={sentModal} footer={null} width={680}
        onCancel={() => setSentModal(false)}>
        <p style={{ fontSize: 12, color: '#8a94a3', marginTop: 0 }}>
          选择报告里的原句，三元组按建议值预填，可修改后保存。
        </p>
        {REPORT_SENTENCES.map((s, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '7px 0', borderBottom: '1px solid #30363d' }}>
            <span style={{ flex: 1, fontSize: 13 }}>{s.text}</span>
            <span style={{ flexShrink: 0, fontSize: 11, color: '#8a94a3' }}>{s.src}</span>
            <Button type="link" size="small" style={{ padding: 0, flexShrink: 0 }}
              onClick={() => pickSentence(i)}>选用</Button>
          </div>
        ))}
      </Modal>
      <Modal title="LLM 起草示例" open={draftModal} footer={null} width={520}
        onCancel={() => setDraftModal(false)}>
        <p style={{ fontSize: 12, color: '#8a94a3', marginTop: 0 }}>
          输入关系词，按库内实体自动起草一对示例，核对后保存。
        </p>
        <Space.Compact style={{ width: '100%' }}>
          <Input placeholder="输入关系词，如：受效" value={draftRel}
            onChange={ev => setDraftRel(ev.target.value)} onPressEnter={draftExample} />
          <Button type="primary" onClick={draftExample}>生成</Button>
        </Space.Compact>
        <div style={{ marginTop: 12, fontSize: 12, color: '#8a94a3' }}>
          当前关系标签：
          {rels.filter(r => r.on).map(r => (
            <Tag key={r.rel} style={{ cursor: 'pointer', marginInlineEnd: 6 }} color={REL_TAG[r.rel] || 'default'}
              onClick={() => setDraftRel(r.rel)}>{r.rel}</Tag>
          ))}
        </div>
      </Modal>
    </div>
  )
}
