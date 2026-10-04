/**
 * 落地树 · B5 关系图谱（P1-05 全页真 API——B5-关系图谱.md v0.2 四端点消费）。
 *
 * 合同：teach-petro-agent/specs/api/B5-关系图谱.md v0.2（端点 1 net 整图读/
 * 2 extract-config 读/3 保存〔对号强校——对不上拒存 400 带对号明细〕/4
 * blocked-edges〔页面不加 UI——治理/E3 消费〕＋LLM 起草实施端点）。
 * 视觉与交互形态对照原型树 #/proto/B5（prototype 终稿快照 web/src/pages/B5.jsx）
 * ——数据是真、形是原型；mock 简化更正清单（B5 行为规则 10）逐条兑现：
 * ①NODES/EDGES/ENTITY_ROWS/REL_ROWS/保存提示内嵌常量→端点 1/2/3；③「带此节点
 * 提问」＝A1 anchors 机制页面侧消费（A1 落地前 mock 提示＋导航 #/A1）；④库
 * 选择器补齐、lib_id 必传化（演示缺省改选真库）；⑥「自定义指令」前缀由字段
 * 名派生；示例三源辅助（对账 11）：从已抽结果生成/从报告库选句/LLM 起草——
 * 起草走真 gateway.complete（后端 /graph/extract-config/draft-example）。
 *
 * 图数据读取口径（合同裁决）：整图一次给——节点高亮/图例隐显/关系清单邻接
 * 过滤与计数全部为前端本地计算；端点 1 只含过闸入图的边（铁律消费面）。
 *
 * UI-05（阶段 1 落地页交互优化——方案 §5-B5，施工票 tickets/phase1-ui/UI-05.md）：
 * 补统一页头三件套（卡头 extra 大段说明迁入 helpTop，内容不改）；libError/netError
 * 统一 antd Alert（type=error showIcon）并提升 Card 级两页签共享；关系清单/从已抽
 * 结果生成两表接 PagedTable client 分页（resetKey=libId|sel／libId）；两栏行定高
 * 578 使右栏内滚成真；抽取设置三态修复（切库先清 cfg＋cfgLoading Skeleton 占位＋
 * 装载窗口保存/输入不可写——跨库错存杜绝）；实体类型/关系标签删除守卫（装载成功
 * 快照为初始基线，基线项不可删、快照外新增项可删）；实体类型文案如实化（勾选切换
 * 需 DTO 增 enabled＝合同变更，登记 UI-07 提案票，本批零合同变更）；报告下拉携当前
 * 库过滤＋showSearch；选句清单容器内滚；helpIcon/dim/errText 改 UI-00 共享件 import。
 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { Graph } from '@antv/g6'
import {
  Alert, Button, Card, Checkbox, Input, message, Modal, Select, Skeleton, Space,
  Switch, Table, Tabs, Tag, Tooltip
} from 'antd'
import { DeleteOutlined } from '@ant-design/icons'
import { ApiError, errText } from '../api/client.js'
import { helpIcon, dim } from '../components/helpIcon.jsx'  // UI-00 共享件（UI-05 T12——页内副本删除）
import PagedTable from '../components/PagedTable.jsx'  // UI-00 共享件（UI-05 T4/T7——集合表统一分页）
import {
  getExtractConfig, getGraphNet, draftExample, saveExtractConfig
} from '../api/graph.js'
import { getFragmentContext, getReports, getReportDetail, listLibraries }
  from '../api/kb.js'

// 节点类型配色（前端渲染细节不入合同——类型值域随库配置非封闭枚举，未知
// 类型走调色板轮转）
const TYPE_HEX = { 井: '#3b8dff', 区块: '#52c41a', 平台: '#9254de', 油田: '#faad14', 措施: '#fa8c16' }
const PALETTE = ['#3b8dff', '#52c41a', '#9254de', '#faad14', '#fa8c16', '#4aa3ff', '#e8a23d', '#57a75f', '#a78bde', '#eb2f96']
const typeColor = type => TYPE_HEX[type] || PALETTE[Object.keys(TYPE_HEX).length + (type?.length || 0) % PALETTE.length] || '#8a94a3'
const REL_TAG = { 隶属: 'green', 承载: 'purple', 受效: 'blue', 作用于: 'orange' }

const BUILD_GATE_TIP = (
  <>
    <b>建图时的检查</b>：抽取哪些类型由库里的类型清单说了算：清单与领域术语表逐一对号，对不上的类型不自创——避免同一个词在不同地方指不同的东西。保存时对不上会拒存并给出对号明细。
  </>
)
const LIST_GATE_TIP = (
  <>只收通过入库检查的关系——入库前先做检查：类型对不上的不建边、原文里没有依据的不建边，拿不准的宁可不建；被拦下的边不进图，图和台账始终对得上。点左侧图例开关可整类隐去/恢复；选中节点后，这里只列与它相连的关系。</>
)
const QUERY_GATE_TIP = (
  <>
    <b>查询时的检查</b>：提问先精确锚定（如 @N-06）直达相关节点，再沿关系网找答案，图检索兜底；黑话和禁用词（如"躺井"）按术语库拦下；超出业务范围的问题先拒答。<br />
    点击携带此节点信息跳入问一问。
  </>
)
const LEGEND_TIP = '点类型开关隐去/显示该类节点；两端任一被隐去的关系同步隐去，右侧关系清单同步刷新。'
// UI-05 T3：文案如实化——控件为「全量启用」如实展示（Checkbox checked disabled），
// 不落不可持久化的假勾选；勾选切换承载需端点 3 DTO 增 enabled＝合同变更，
// 已登记 UI-07 提案票（本批零合同变更）。
const ENTITY_TIP = '实体类型在抽取时全部启用；本清单可新增自定义类型。'
// UI-05 T8③：REL_TIP 现句无「停用/Switch」承诺字样（grep 核对），保持如实不动；
// 「关系词＋启用 Switch」行形态同样待 DTO 增 enabled（与 T3 同一条目登记 UI-07）。
const REL_TIP = '关系标签按库配置，抽取时照标签对号，清单之外的标签不立边；可新增标签，自定义标签可删除。'
const FEWSHOT_TIP = '每条示例＝报告原句＋应抽出的三元组，抽取时照示例对号；示例质量直接决定抽取准确度。示例可从已抽结果、报告原句或系统起草生成，核对后保存；也可手动添加。'
const INSTRUCTION_TIP = '随抽取任务生效的硬规则：原文里找不到依据的关系不建边，宁可少建、不建错；类型清单之外的类型不许自创。可按库改写。'

// UI-05 T6：页头 helpTop——原卡头 extra 大段说明整体迁入（内容不改）。
const PAGE_HELP = (
  <>
    把报告与台账里"谁—什么关系→谁"连成关系网：井—隶属→区块、平台—承载→井、注水井—受效→油井。<br />
    节点与关系全部来自报告与台账（铁律：对不上的不建边、原文没依据的不建边、拿不准的宁可不建）。
  </>
)

const edgeKey = e => e.key || `${e.from}|${e.rel}|${e.to}`

// ── AntV G6 5.x 关系图（原型 GraphG6 同构——数据由 props 注入）──

function toG6Node(n) {
  return { id: n.id, data: { type: n.type, short: n.short, sub: n.sub } }
}
function toG6Edge(e) {
  return {
    id: edgeKey(e), source: e.from, target: e.to, type: 'line',
    data: { rel: e.rel, note: e.note || '', from: e.from, to: e.to }
  }
}

function GraphG6({ nodes, edges, sel, visible, nameOf, onPick }) {
  const boxRef = useRef(null)
  const graphRef = useRef(null)
  const pickRef = useRef(onPick)
  pickRef.current = onPick
  const [ready, setReady] = useState(false)
  const dataRef = useRef({ nodes, edges })
  dataRef.current = { nodes, edges }
  const typeOf = useMemo(() => Object.fromEntries(nodes.map(n => [n.id, n.type])), [nodes])

  useEffect(() => {
    const graph = new Graph({
      container: boxRef.current,
      autoFit: 'view',
      padding: 24,
      autoResize: true,
      background: '#161b22',
      theme: 'dark',
      animation: false,
      data: { nodes: dataRef.current.nodes.map(toG6Node), edges: dataRef.current.edges.map(toG6Edge) },
      layout: { type: 'antv-dagre', rankdir: 'BT', nodesep: 40, ranksep: 48 },
      node: {
        type: 'rect',
        style: {
          size: [96, 40], radius: 9, cursor: 'pointer',
          fill: d => typeColor(d.data.type), fillOpacity: 0.12,
          stroke: d => typeColor(d.data.type), lineWidth: 1.4,
          iconText: d => d.data.short, iconFontSize: 12, iconFontWeight: 600,
          iconFill: '#e6edf3',
          labelText: d => d.data.sub, labelPlacement: 'bottom', labelOffsetY: 6,
          labelFill: d => typeColor(d.data.type), labelFontSize: 10, labelFontWeight: 600
        },
        state: {
          highlight: { lineWidth: 2, stroke: '#4a9dff', fillOpacity: 0.28, halo: true, haloStroke: '#4a9dff', haloLineWidth: 12, haloStrokeOpacity: 0.35 },
          active: { lineWidth: 2, stroke: '#7ab3ff' },
          dim: { iconOpacity: 0.55, labelFillOpacity: 0.5, strokeOpacity: 0.5 },
          ghost: { lineDash: [4, 3], strokeOpacity: 0.3, fillOpacity: 0.05, iconOpacity: 0.25, labelFillOpacity: 0.25 }
        }
      },
      edge: {
        style: {
          stroke: d => typeColor(d.data.rel), strokeOpacity: 0.35, lineWidth: 1.3,
          endArrow: true, endArrowSize: 8,
          labelText: d => d.data.rel, labelFill: '#8a94a3', labelFontSize: 10.5,
          labelFontWeight: 600, labelBackground: true, labelBackgroundFill: '#161b22',
          labelBackgroundOpacity: 0.85, labelBackgroundRadius: 3,
          labelBackgroundLineWidth: 0, labelPadding: [1, 3]
        },
        state: {
          highlight: { strokeOpacity: 1, lineWidth: 2.3, labelFontWeight: 700 },
          active: { strokeOpacity: 0.9, lineWidth: 2 },
          dim: { strokeOpacity: 0.15, labelFillOpacity: 0.4 }
        }
      },
      behaviors: [
        'zoom-canvas', 'drag-canvas', 'drag-element',
        { type: 'hover-activate', degree: 1, direction: 'both', state: 'active' }
      ],
      plugins: [{
        type: 'tooltip', trigger: 'hover',
        getContent: (evt, items) => {
          const d = items && items[0]
          if (!d) return ''
          if (evt.targetType === 'edge') {
            const note = d.data && d.data.note
            return `<b>${nameOf(d.data.from)} —${d.data.rel}→ ${nameOf(d.data.to)}</b>${note ? `<div style="color:#8a94a3;margin-top:2px">${note}</div>` : ''}`
          }
          return `<b>${nameOf(d.id)}</b>`
        },
        style: {
          background: '#1c2128', border: '1px solid #30363d', borderRadius: 6,
          color: '#e6edf3', fontSize: 12, padding: '6px 10px',
          boxShadow: '0 6px 16px rgba(0,0,0,0.45)'
        }
      }]
    })
    graphRef.current = graph
    graph.on('node:click', evt => pickRef.current(String(evt.target.id)))
    let alive = true
    graph.render().then(() => { if (alive) setReady(true) })
    return () => {
      alive = false
      graphRef.current = null
      graph.destroy()
    }
    // 数据整图一次给（合同裁决）——图实例随挂载建一次；库切换经 key 重挂载
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 选中/图例变化 → 批量落图（原型同构：sel 与相邻 highlight、其余 dim、
  // 图例关掉的节点 ghost、相关边 visibility hidden）
  useEffect(() => {
    const graph = graphRef.current
    if (!graph || !ready) return
    const allNodes = dataRef.current.nodes
    const allEdges = dataRef.current.edges
    const shown = id => visible[typeOf[id]] !== false
    const shownEdges = allEdges.filter(e => shown(e.from) && shown(e.to))
    const states = {}
    allNodes.forEach(n => {
      if (!shown(n.id)) { states[n.id] = ['ghost']; return }
      if (sel === n.id) { states[n.id] = ['highlight']; return }
      const adj = shownEdges.some(e => (e.from === sel || e.to === sel) && (e.from === n.id || e.to === n.id))
      states[n.id] = adj ? [] : ['dim']
    })
    allEdges.forEach(e => { states[edgeKey(e)] = sel && (e.from === sel || e.to === sel) ? ['highlight'] : ['dim'] })
    graph.setElementState(states, false)
    const vis = {}
    allEdges.forEach(e => { vis[edgeKey(e)] = shown(e.from) && shown(e.to) ? 'visible' : 'hidden' })
    graph.setElementVisibility(vis, false)
  }, [sel, visible, ready, typeOf])

  return (
    <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: 8 }}>
      <div ref={boxRef} style={{ width: '100%', height: 560 }} />
    </div>
  )
}

/**
 * 落地 B5 关系图谱页（两页签：关系网 / 抽取设置——端点 1/2/3＋起草端点接线；
 * 端点 4 被拦边清单纯只读、页面不加 UI——合同级声明）。
 * @returns {JSX.Element}
 */
export default function B5Landing() {
  const [tab, setTab] = useState('net')

  // ── 库选择器（B5 更正项④：lib_id 必传化——演示单库形态改真库下拉） ──
  const [libs, setLibs] = useState([])
  const [libId, setLibId] = useState(null)
  const [libError, setLibError] = useState(null)

  // ── 关系网（端点 1：整图一次给——过滤/邻接全前端本地计算） ──
  const [net, setNet] = useState({ nodes: [], edges: [], legend: [], stats: { nodes: 0, edges: 0 }, libName: '' })
  const [netLoading, setNetLoading] = useState(true)
  const [netError, setNetError] = useState(null)
  const [sel, setSel] = useState(null)
  const [visible, setVisible] = useState({})

  // ── 抽取设置（端点 2/3：可交互四段——保存出服务端 hint＋强校拒存对号明细） ──
  const [cfg, setCfg] = useState(null) // {entityTypes, relationTags, fewShotExamples, customInstructions}
  const [cfgLoading, setCfgLoading] = useState(true)
  const [newEntity, setNewEntity] = useState('')
  const [newRel, setNewRel] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(null) // 服务端 hint
  const [mismatches, setMismatches] = useState(null) // 对号明细（400 强校）
  // UI-05 T3③/T8①：删除守卫基线——当前库配置装载成功那一刻的快照（ref 持有，
  // libId 重装载时重取）；仅快照外新增项显示删除钮（对齐原型 e.custom 判定语义，
  // 不发明业务名单）。
  const cfgBaseRef = useRef({ entityTypes: [], relationTags: [] })

  // ── 示例三源辅助弹窗（从已抽结果生成 / 从报告库选句 / LLM 起草） ──
  const [edgeModal, setEdgeModal] = useState(false)
  const [sentModal, setSentModal] = useState(false)
  const [draftModal, setDraftModal] = useState(false)
  const [draftRel, setDraftRel] = useState('')
  const [drafting, setDrafting] = useState(false)
  const [sentReports, setSentReports] = useState([])
  const [sentReportId, setSentReportId] = useState(null)
  const [sentences, setSentences] = useState([])

  const nameOf = useMemo(() => Object.fromEntries(net.nodes.map(n => [n.id, n.label])), [net.nodes])

  // 首次装载：库下拉（默认第一个库）
  useEffect(() => {
    listLibraries().then(d => {
      setLibs(d.items)
      if (d.items.length) setLibId(d.items[0].id)
      else {
        setLibError('暂无知识库——先到报告库建库并入库（图谱开关开启）。')
        setCfgLoading(false) // UI-05 T2：无库可装载——配置装载态落终局（Skeleton 不悬挂）
      }
    }).catch(err => {
      setLibError(errText(err))
      setCfgLoading(false) // UI-05 T2：同上（失败终态由 Card 级 Alert 承接）
    })
  }, [])

  // 库切换：整图＋抽取设置（配置与图现状两态分离——端点 1 join 端点 2）
  useEffect(() => {
    if (!libId) return undefined
    let alive = true
    setNetLoading(true); setNetError(null); setSel(null); setSaved(null); setMismatches(null)
    setCfg(null) // UI-05 T2①：切库先清 cfg——旧库配置不再可编辑/可被新 libId PUT（跨库错存杜绝）
    setCfgLoading(true)
    Promise.all([getGraphNet(libId), getExtractConfig(libId)])
      .then(([n, c]) => {
        if (!alive) return
        setNet(n)
        setVisible(Object.fromEntries(n.legend.map(l => [l.type, true])))
        setCfg({
          entityTypes: c.entityTypes,
          relationTags: c.relationTags,
          fewShotExamples: c.fewShotExamples,
          customInstructions: c.customInstructions
        })
        cfgBaseRef.current = { entityTypes: [...c.entityTypes], relationTags: c.relationTags.map(r => r.rel) }
      })
      .catch(err => { if (alive) setNetError(errText(err)) })
      .finally(() => {
        if (!alive) return
        setNetLoading(false); setCfgLoading(false)
      })
    return () => { alive = false }
  }, [libId])

  // ── 关系网本地计算（图例隐显→清单同步；选中→邻接过滤） ──
  const isShown = id => visible[net.nodes.find(n => n.id === id)?.type] !== false
  const shownEdges = net.edges.filter(e => isShown(e.from) && isShown(e.to))
  const listEdges = sel ? shownEdges.filter(e => e.from === sel || e.to === sel) : shownEdges

  function askWithNode() {
    // 诚实口径（P1-11c 收口）：A1 @ 资产投影六类无图谱节点类——本动作现仅导航不带节点上下文；
    // 图谱节点进 A1 @ 装配挂阶段 2 图谱问答深化批（移交清单第 12 条）。
    message.success(`已带上节点：${nameOf[sel] || sel}——到问一问继续深化接入`)
    location.hash = '/A1'
  }

  // ── 抽取设置编辑动作 ──
  const addEntity = () => {
    const name = newEntity.trim()
    if (!name) return
    if (cfg.entityTypes.some(t => t === name)) { message.warning(`类型「${name}」已在清单中`); return }
    setCfg(p => ({ ...p, entityTypes: [...p.entityTypes, name] }))
    setNewEntity('')
  }
  const addRel = () => {
    const rel = newRel.trim()
    if (!rel) return
    if (cfg.relationTags.some(t => t.rel === rel)) { message.warning(`关系标签「${rel}」已存在`); return }
    setCfg(p => ({ ...p, relationTags: [...p.relationTags, { rel, example: '', desc: '' }] }))
    setNewRel('')
  }
  const addExample = pair => setCfg(p => ({ ...p, fewShotExamples: [...p.fewShotExamples, pair] }))

  async function saveExtract() {
    setSaving(true)
    setMismatches(null)
    try {
      const r = await saveExtractConfig(libId, cfg)
      setSaved(r.hint)
      message.success(r.hint)
    } catch (err) {
      if (err instanceof ApiError && err.code === 'graph_ontology_mismatch' && err.detail?.mismatches) {
        setMismatches(err.detail.mismatches) // 对号明细原样展示（B5 端点 3 注记）
      } else {
        message.error(errText(err))
      }
    } finally {
      setSaving(false)
    }
  }

  // ── 三源①：从已抽结果生成——选当前图已入库的边＋回捞出处句 ──
  async function pickEdge(e) {
    if (!cfg) return // UI-05 T2：装载窗口期（cfg 已清）不写示例——错存窗口不可写
    let src = e.note || ''
    if (e.evidenceChunkId) {
      try {
        const ctx = await getFragmentContext(e.evidenceChunkId)
        src = ctx.hit || ctx.context || src
      } catch { /* 出处句回捞失败不阻塞——落 note 兜底 */ }
    }
    addExample({ sentence: src || `${e.from} —${e.rel}→ ${e.to}`, triple: `${nameOf[e.from] || e.from} —${e.rel}→ ${nameOf[e.to] || e.to}` })
    setEdgeModal(false)
    message.success('已生成示例，请核对后保存。')
  }

  // ── 三源②：从报告库选句——报告下拉→切片原句清单→LLM 预填三元组（人可改） ──
  async function openSentModal() {
    setSentModal(true)
    try {
      const d = await getReports({ lib: libId }) // UI-05 T9：携当前库过滤——不再全库盲选
      setSentReports(d.items)
    } catch (err) { message.error(errText(err)) }
  }
  async function pickReport(reportId) {
    setSentReportId(reportId)
    try {
      const detail = await getReportDetail(reportId)
      const sents = []
      detail.fragments.forEach(f => {
        ;(f.text || '').split(/(?<=[。；;])/).forEach(s => {
          const t = s.trim()
          if (t.length >= 6) sents.push(t)
        })
      })
      setSentences(sents.slice(0, 30))
    } catch (err) { message.error(errText(err)) }
  }
  async function pickSentence(sentence) {
    if (!cfg) return // UI-05 T2：装载窗口期不写示例（同 pickEdge）
    setDrafting(true)
    try {
      const rel = draftRel || cfg.relationTags[0]?.rel || '隶属'
      const d = await draftExample(libId, { rel, sentence })
      addExample({ sentence, triple: d.triple })
      setSentModal(false)
      message.success('已按所选原句预填三元组，请核对后保存。')
    } catch (err) {
      message.error(errText(err))
    } finally {
      setDrafting(false)
    }
  }

  // ── 三源③：LLM 起草——输入关系词，按库配置起草一对示例（真 complete） ──
  async function draftByRel() {
    const w = draftRel.trim()
    if (!w) { message.warning('请先输入关系词'); return }
    if (!cfg) return // UI-05 T2：装载窗口期不写示例（同 pickEdge）
    setDrafting(true)
    try {
      const d = await draftExample(libId, { rel: w })
      addExample({ sentence: d.sentence, triple: d.triple })
      setDraftModal(false)
      setDraftRel('')
      message.success('已生成示例草案，请核对后保存。')
    } catch (err) {
      message.error(errText(err))
    } finally {
      setDrafting(false)
    }
  }

  const nodeOptions = net.legend.map(l => ({
    label: `${l.type}（${l.count}）`,
    options: net.nodes.filter(n => n.type === l.type).map(n => ({ value: n.id, label: n.label }))
  }))

  const edgeCols = [
    { title: '起点', dataIndex: 'from', width: 150, render: v => nameOf[v] || v },
    { title: '关系', dataIndex: 'rel', width: 88, render: v => <Tag color={REL_TAG[v] || 'default'} style={{ marginInlineEnd: 0 }}>{v}</Tag> },
    { title: '终点', dataIndex: 'to', width: 150, render: v => nameOf[v] || v }
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* UI-05 T6 统一页头＋UI-09 收束：口号副标题删除——PAGE_HELP 移挂页标题旁（内容不改） */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <span style={{ fontSize: 18, fontWeight: 600 }}>关系图谱{helpIcon(PAGE_HELP)}</span>
      </div>
      <Card
        title={
          <Space size={12}>
            <span style={{ fontSize: 12, color: '#8a94a3' }}>知识库</span>
            <Select size="small" style={{ minWidth: 200 }} placeholder="选择库"
              value={libId} onChange={setLibId}
              options={libs.map(l => ({ value: l.id, label: l.name }))} />
          </Space>
        }
      >
        <Tabs
          activeKey={tab} size="small" onChange={setTab}
          items={[
            { key: 'net', label: <span>关系网（{net.stats.edges}）</span> },
            { key: 'extract', label: <span>抽取设置{helpIcon(BUILD_GATE_TIP)}</span> }
          ]}
        />

        {/* UI-05 T2④/T5：错误行提升 Card 级两页签共享＋统一 Alert type=error showIcon
            （文案不变仅换包裹件——原 libError 灰字 dim div／netError 彩色字 div 撤除） */}
        {(libError || netError) && (
          <div style={{ marginBottom: 12 }}>
            {libError && <Alert type="error" showIcon message={libError} style={{ marginBottom: 8 }} />}
            {netError && <Alert type="error" showIcon message={netError} />}
          </div>
        )}

        {tab === 'net' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 12 }}>
              <Space wrap size={16}>
                <Space size={2}>
                  <span style={{ fontSize: 12, color: '#8a94a3' }}>图例</span>
                  {helpIcon(LEGEND_TIP)}
                </Space>
                {net.legend.map(l => (
                  <Space key={l.type} size={6}>
                    <Switch size="small" checked={visible[l.type] !== false}
                      onChange={v => setVisible(p => ({ ...p, [l.type]: v }))} />
                    <span style={{ fontSize: 13 }}>
                      <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: typeColor(l.type), marginRight: 6 }} />
                      {l.type}（{l.count}）
                    </span>
                  </Space>
                ))}
              </Space>
              <Space size={4}>
                <span style={{ fontSize: 12, color: '#8a94a3' }}>查看节点</span>
                <Select size="small" showSearch optionFilterProp="label" style={{ width: 210 }}
                  placeholder="选择节点" value={sel ?? undefined} onChange={setSel} options={nodeOptions} />
                <Tooltip title={QUERY_GATE_TIP}>
                  <span>
                    <Button type="primary" size="small" disabled={!sel} onClick={askWithNode}>带此节点提问</Button>
                  </span>
                </Tooltip>
              </Space>
            </div>
            {/* 主区左右两栏（B5 排版二批定稿）：左＝关系图（约 2/3 宽），右＝关系清单面板（固定宽、独立滚动） */}
            {/* UI-05 T1：两栏行定高 578（＝图容器 560＋GraphG6 上下 padding 16＋边框 2，与左图底边对齐）
                ——minHeight:0+overflow:auto 链受约束成真内滚，清单变长不再撑高整页 */}
            <div style={{ display: 'flex', gap: 16, alignItems: 'stretch', height: 578 }}>
              <div style={{ flex: 2, minWidth: 0 }}>
                {netLoading
                  ? <div style={{ ...dim, padding: 40, textAlign: 'center' }}>关系网装载中…</div>
                  : (net.nodes.length
                      ? <GraphG6 key={libId} nodes={net.nodes} edges={net.edges} sel={sel}
                          visible={visible} nameOf={nameOf} onPick={setSel} />
                      : <div style={{ ...dim, border: '1px dashed #30363d', borderRadius: 8, padding: 60, textAlign: 'center' }}>
                          当前库暂无图谱数据——图谱开关开启后入库一次即成图（不抽取即无图）。
                        </div>)}
              </div>
              <div style={{ width: 400, flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
                <div style={{
                  flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column',
                  background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '10px 12px'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>关系清单</span>
                    {helpIcon(LIST_GATE_TIP)}
                  </div>
                  {/* UI-05 T4：接 PagedTable client 分页（pageSize 20 与面板内滚共存——方案 §2.2 表 #9）；
                      resetKey=libId|sel（图例隐显为隐式筛变，由 §2.1 内置超界钳制兜底）；空态话术原话透传。
                      UI-12：清单容器转 flex 链＋PagedTable fill 内滚（表头/分页条恒在面板内）——
                      overflow:auto 保留为无 ResizeObserver 环境的兜底内滚，fill 生效时不再产生第二道滚动 */}
                  <div style={{ flex: 1, minHeight: 0, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
                    <PagedTable
                      fill
                      size="small" columns={edgeCols}
                      dataSource={listEdges.map(e => ({ ...e, key: edgeKey(e) }))}
                      rowKey="key" loading={netLoading} pageSize={20}
                      emptyText={sel ? '该节点暂无可见关系：若相关类型被图例开关隐去，打开开关即可恢复。' : '当前图例下没有可见关系。'}
                      resetKey={`${libId ?? ''}|${sel ?? ''}`}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === 'extract' && (cfgLoading || !cfg ? (
          /* UI-05 T2②：首载/切库 cfg=null 窗口不再白屏——Skeleton 占位；
             「配置装载中…」提示移出 cfg 守卫（原 :587 随 cfg 门被吞，装载期永不可见）；
             装载失败终态由上方 Card 级 Alert 承接（失败态≠空态）。 */
          <div>
            {cfgLoading && <Skeleton active title={false} paragraph={{ rows: 8 }} />}
            {cfgLoading && <div style={{ ...dim, marginTop: 8 }}>配置装载中…</div>}
          </div>
        ) : (
          <div>
            <div style={{ display: 'flex', gap: 24, alignItems: 'top', flexWrap: 'wrap' }}>
              <div style={{ flex: '1 1 380px', minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
                  {/* UI-05 T3①：段标题如实化——「（勾选启用）」承诺撤除（勾选切换承载
                      需 DTO 增 enabled＝合同变更，登记 UI-07） */}
                  实体类型清单{helpIcon(ENTITY_TIP)}
                </div>
                <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '10px 12px' }}>
                  {cfg.entityTypes.map((t, i) => (
                    <div key={t} style={{ display: 'flex', alignItems: 'center', padding: '3px 0' }}>
                      {/* UI-05 T3②：Checkbox checked disabled 保持——现状全量启用语义如实 */}
                      <Checkbox checked style={{ fontSize: 13 }} disabled>
                        <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: typeColor(t), marginRight: 6 }} />
                        {t}
                      </Checkbox>
                      {/* UI-05 T3③：删除守卫——仅装载快照基线外的新增项可删（基线项不可删） */}
                      {!cfgBaseRef.current.entityTypes.includes(t) && (
                        <Button type="text" size="small" danger icon={<DeleteOutlined />}
                          onClick={() => setCfg(p => ({ ...p, entityTypes: p.entityTypes.filter((_, xi) => xi !== i) }))} />
                      )}
                    </div>
                  ))}
                  <Space.Compact style={{ marginTop: 8 }}>
                    <Input size="small" placeholder="新增类型" value={newEntity} disabled={cfgLoading}
                      onChange={ev => setNewEntity(ev.target.value)} onPressEnter={addEntity} style={{ width: 170 }} />
                    <Button size="small" onClick={addEntity}>添加</Button>
                  </Space.Compact>
                </div>
              </div>
              <div style={{ flex: '1 1 380px', minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8 }}>
                  关系标签{helpIcon(REL_TIP)}
                </div>
                <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '10px 12px' }}>
                  {cfg.relationTags.map((r, i) => (
                    <div key={r.rel} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '3px 0' }}>
                      <Tag color={REL_TAG[r.rel] || 'default'} style={{ marginInlineEnd: 0 }}>{r.rel}</Tag>
                      <span style={{ fontSize: 12, color: '#8a94a3', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {r.desc || '—'}
                      </span>
                      {/* UI-05 T8①：删除守卫同 T3③——初始标签不可删，仅新增自定义项可删 */}
                      {!cfgBaseRef.current.relationTags.includes(r.rel) && (
                        <Button type="text" size="small" danger icon={<DeleteOutlined />}
                          onClick={() => setCfg(p => ({ ...p, relationTags: p.relationTags.filter((_, xi) => xi !== i) }))} />
                      )}
                    </div>
                  ))}
                  <Space.Compact style={{ marginTop: 8 }}>
                    <Input size="small" placeholder="新增关系" value={newRel} disabled={cfgLoading}
                      onChange={ev => setNewRel(ev.target.value)} onPressEnter={addRel} style={{ width: 170 }} />
                    <Button size="small" onClick={addRel}>添加</Button>
                  </Space.Compact>
                </div>
              </div>
            </div>
            <div style={{ fontWeight: 600, fontSize: 13, margin: '16px 0 8px', display: 'flex', alignItems: 'center' }}>
              <span>示例（few-shot）{helpIcon(FEWSHOT_TIP)}</span>
              <span style={{ marginLeft: 'auto', fontWeight: 400 }}>
                <Space size={8}>
                  <Button size="small" onClick={() => setEdgeModal(true)}>从已抽结果生成</Button>
                  <Button size="small" onClick={openSentModal}>从报告库选句</Button>
                  <Button size="small" onClick={() => setDraftModal(true)}>LLM 起草</Button>
                </Space>
              </span>
            </div>
            <div style={{ background: '#161b22', border: '1px solid #30363d', borderRadius: 8, padding: '10px 12px' }}>
              {cfg.fewShotExamples.map((ex, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                  <Input size="small" placeholder="报告原句" value={ex.sentence}
                    onChange={ev => setCfg(p => ({ ...p, fewShotExamples: p.fewShotExamples.map((x, xi) => xi === i ? { ...x, sentence: ev.target.value } : x) }))}
                    style={{ flex: 1 }} />
                  <span style={{ color: '#8a94a3', flexShrink: 0 }}>→</span>
                  <Input size="small" placeholder="应抽出三元组" value={ex.triple}
                    onChange={ev => setCfg(p => ({ ...p, fewShotExamples: p.fewShotExamples.map((x, xi) => xi === i ? { ...x, triple: ev.target.value } : x) }))}
                    style={{ flex: 1 }} />
                  <Button type="text" size="small" danger icon={<DeleteOutlined />}
                    onClick={() => setCfg(p => ({ ...p, fewShotExamples: p.fewShotExamples.filter((_, xi) => xi !== i) }))} />
                </div>
              ))}
              <Button size="small" onClick={() => addExample({ sentence: '', triple: '' })}>添加示例</Button>
            </div>
            <div style={{ fontWeight: 600, fontSize: 13, margin: '16px 0 8px' }}>
              自定义指令{helpIcon(INSTRUCTION_TIP)}
            </div>
            <Input.TextArea rows={2} value={cfg.customInstructions}
              onChange={ev => setCfg(p => ({ ...p, customInstructions: ev.target.value }))} />
            <Space style={{ marginTop: 12 }}>
              {/* UI-05 T2③：装载窗口期保存不可用（配合表单撤下，错存窗口期不可写） */}
              <Button type="primary" size="small" loading={saving} disabled={cfgLoading}
                onClick={saveExtract}>保存抽取设置</Button>
              {saved && <span style={{ fontSize: 12, color: '#8a94a3' }}>{saved}</span>}
            </Space>
          </div>
        ))}
      </Card>

      {/* 对号强校拒存明细（B5 端点 3：逐项未收录＋最接近台账词条——前端原样展示） */}
      <Modal title="对号强校不过——拒存" open={!!mismatches} footer={null} width={560}
        onCancel={() => setMismatches(null)}>
        <p style={{ ...dim, marginTop: 0 }}>
          以下实体类型/关系标签未收录进本体对号表，对不上拒存（补全走治理批）。
        </p>
        <Table
          size="small" rowKey="value" pagination={false}
          dataSource={mismatches || []}
          columns={[
            { title: '类别', dataIndex: 'kind', width: 110, render: v => (v === 'entity_type' ? '实体类型' : '关系标签') },
            { title: '未收录词条', dataIndex: 'value' },
            { title: '最接近台账词条', dataIndex: 'nearest' }
          ]}
        />
      </Modal>

      {/* 三源①：从已抽结果生成——出处句经片段回捞端点带出 */}
      <Modal title="从已抽结果生成示例" open={edgeModal} footer={null} width={680}
        onCancel={() => setEdgeModal(false)}>
        <p style={{ ...dim, marginTop: 0 }}>
          选择当前图里已入库的一条关系，自动配好示例（原句＋三元组），核对后保存。
        </p>
        {/* UI-05 T7：弹窗集合表接 PagedTable client 分页（方案 §2.2 表 #10）；
            resetKey=libId（边数据随库切换重载） */}
        <PagedTable
          size="small" rowKey="key"
          dataSource={net.edges.map(e => ({ ...e, key: edgeKey(e) }))}
          emptyText="当前图还没有已入库关系——图谱开关开启后入库一次即成图。"
          resetKey={`${libId ?? ''}`}
          columns={[
            { title: '起点', dataIndex: 'from', width: 130, render: v => nameOf[v] || v },
            { title: '关系', dataIndex: 'rel', width: 80, render: v => <Tag color={REL_TAG[v] || 'default'} style={{ marginInlineEnd: 0 }}>{v}</Tag> },
            { title: '终点', dataIndex: 'to', width: 130, render: v => nameOf[v] || v },
            { title: '注记', dataIndex: 'note', render: v => v || '—' },
            { title: '', key: 'op', width: 64,
              render: (_, r) => <Button type="link" size="small" style={{ padding: 0 }} onClick={() => pickEdge(r)}>选用</Button> }
          ]}
        />
      </Modal>

      {/* 三源②：从报告库选句——报告→原句清单→LLM 预填三元组（人可改） */}
      <Modal title="从报告库选句" open={sentModal} footer={null} width={680}
        onCancel={() => setSentModal(false)}>
        <p style={{ ...dim, marginTop: 0 }}>
          {/* UI-09：去「（LLM 起草走统一出口）」dev 语汇括注——票面改造项 11 */}
          选择报告里的原句，三元组按建议值预填，可修改后保存。
        </p>
        {/* UI-05 T9：Select 开 showSearch（先例：查看节点 Select）——量级下可键入过滤 */}
        <Select size="small" style={{ width: '100%', marginBottom: 8 }} placeholder="选择报告"
          showSearch optionFilterProp="label"
          value={sentReportId ?? undefined} onChange={pickReport}
          options={sentReports.map(r => ({ value: r.id, label: `${r.doc} · ${r.lib}` }))} />
        {/* UI-05 T11：选句清单容器内滚（上限 30 句挑选器——方案 §2.2 豁免分页） */}
        <div style={{ maxHeight: 'calc(100vh - 320px)', overflowY: 'auto' }}>
          {sentences.map((s, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '7px 0', borderBottom: '1px solid #30363d' }}>
              <span style={{ flex: 1, fontSize: 13 }}>{s}</span>
              <Button type="link" size="small" style={{ padding: 0, flexShrink: 0 }}
                disabled={drafting} onClick={() => pickSentence(s)}>选用</Button>
            </div>
          ))}
        </div>
      </Modal>

      {/* 三源③：LLM 起草——输入关系词，按库内实体起草一对示例（真 complete） */}
      <Modal title="LLM 起草示例" open={draftModal} footer={null} width={520}
        onCancel={() => setDraftModal(false)}>
        <p style={{ ...dim, marginTop: 0 }}>
          输入关系词，系统按库配置起草一对示例（走统一模型出口），核对后保存。
        </p>
        <Space.Compact style={{ width: '100%' }}>
          <Input placeholder="输入关系词，如：受效" value={draftRel}
            onChange={ev => setDraftRel(ev.target.value)} onPressEnter={draftByRel} />
          <Button type="primary" loading={drafting} onClick={draftByRel}>生成</Button>
        </Space.Compact>
        <div style={{ marginTop: 12, fontSize: 12, color: '#8a94a3' }}>
          当前关系标签：
          {cfg?.relationTags.map(r => (
            <Tag key={r.rel} style={{ cursor: 'pointer', marginInlineEnd: 6 }} color={REL_TAG[r.rel] || 'default'}
              onClick={() => setDraftRel(r.rel)}>{r.rel}</Tag>
          ))}
        </div>
      </Modal>
    </div>
  )
}
