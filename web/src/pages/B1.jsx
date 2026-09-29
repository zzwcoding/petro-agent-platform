import { useEffect, useRef, useState } from 'react'
import {
  Alert, Button, Card, Checkbox, Descriptions, Drawer, Empty, Input, message, Modal, Select,
  Skeleton, Space, Steps, Switch, Table, Tabs, Tag, Tooltip
} from 'antd'
import {
  BookOutlined, DownloadOutlined, FileTextOutlined, FormOutlined, HistoryOutlined,
  QuestionCircleOutlined, RedoOutlined, SettingOutlined, UploadOutlined
} from '@ant-design/icons'

window.__guides = Object.assign(window.__guides || {}, {
  B1: [
    '「报告台账」是在库报告的总账：所属库、出处片段数、中文百科页一眼看全。《N-02 井完井报告》与《2026-08 月报》资料最全；行尾图标看出处（B2）/看百科（B4）/下载原件（直链小时级有效）；双击行开报告详情。',
    '详情抽屉底部「片段预览」——点"修正"可改解析错字：保存后重建索引；别人已改过时会提示刷新后再改（历史版本回看，第一期不回写）。',
    '切「入库任务」点"上传报告（直传）"——先弹确认框：选目标库、预览该库将采用的索引配置，确认后才建任务开跑。',
    '任务列表里有一条"失败"（停在切段，扫描件图像质量差）和一条"疑似卡住"（20 多分钟没进展）——展开看红色/黄色提示条，点"重试"重跑管线。',
    '管线走完——状态变"已完成"，展开区产物卡给出全文档摘要和"可能被问的 10 个问题"；点管线任意处可重跑。',
    '切「库管理」点行尾"配置"——四个索引开关逐个试：关掉即出现黄色后果提示，再开就消失；「入库任务」里"建索引"一步的 ✓/✗ 跟着所选库的开关同步变。',
    '配置里切"切段方式"三个页签——同一段原文三种切法对照立刻换。',
    '点行尾"活动"——这个库的操作留痕：谁传了报告、谁改了配置、哪次入库失败，只记录不改数据。'
  ]
})
window.__traces = Object.assign(window.__traces || {}, {
  B1: 'F5 对象存储 · F6 RAG 管道 · F30 大小段配合/分块人工修正与版本 · F32 四开关/入库失败与重试 · F37 索引期加法 · F61 库活动流 · m5/m6/m14 卡'
})

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

const fieldLabel = { fontSize: 12, color: '#8a94a3', marginBottom: 4 }
const dim = { fontSize: 12, color: '#8a94a3' }

// 三个报告库与各自的开关状态（最近一次入库所用）——开关按库配置，保存后在下次入库时生效
const LIBS = [
  { key: 1, name: '完井报告库', doc: '《N-02 井完井报告（英文 · 200 页）》', sw: ['语义 ✓', '关键词 ✓', '百科 ✓', '图谱 ✓'] },
  { key: 2, name: '生产月报库', doc: '《渤中28-1 区块月度生产月报（2026-08）》', sw: ['语义 ✓', '关键词 ✓', '百科 ✓', '图谱 ✗'] },
  { key: 3, name: '制度文件库', doc: '《平台管理制度文件（示例）》', sw: ['语义 ✓', '关键词 ✓', '百科 ✓', '图谱 ✗（省抽取费）'] }
]
const TASK_DOC = '《N-02 井完井报告（英文 · 200 页）》'

// 报告台账：3 份具名报告（与出处页/百科页同源）＋ 同源派生补行
// （完井报告按井档案井号 N-06/N-11、月报按月份序列）——refs＝出处页能定位的片段数，wiki＝百科当前版
const LEDGER = [
  { key: 1, doc: '《N-02 井完井报告（英文 · 200 页）》', lib: '完井报告库', refs: 5, wiki: 'v3' },
  { key: 2, doc: '《N-06 井完井报告（英文 · 200 页）》', lib: '完井报告库', refs: null, wiki: null },
  { key: 3, doc: '《N-11 井完井报告（英文 · 200 页）》', lib: '完井报告库', refs: null, wiki: null },
  { key: 4, doc: '《渤中28-1 区块月度生产月报（2026-08）》', lib: '生产月报库', refs: 3, wiki: 'v1' },
  { key: 5, doc: '《渤中28-1 区块月度生产月报（2026-07）》', lib: '生产月报库', refs: null, wiki: null },
  { key: 6, doc: '《渤中28-1 区块月度生产月报（2026-06）》', lib: '生产月报库', refs: null, wiki: null },
  { key: 7, doc: '《平台管理制度文件（示例）》', lib: '制度文件库', refs: null, wiki: null }
]

// 台账详情：井号/月份从报告名拆出（既有事实）；片段预览＝出处页同源命中句（B2 REPORTS）
const LEDGER_EXTRA = {
  1: { subject: '井号 N-02', frags: [
    { key: 'f1', path: '章节 01 井基本情况 ＞ 1.2 投产信息', text: 'N-02（渤中28-1-N2）于 2019-06-15 投产。' },
    { key: 'f2', path: '章节 03 图件 ＞ 图 3-7（图片说明块）', text: '图 3-7 岩性柱状图：按深度展示该井段岩性分布（图内无文字，本说明为系统自动生成）。' }
  ] },
  4: { subject: '月份 2026-08', frags: [
    { key: 'f3', path: '章节 02 检修与停产 ＞ 2.1 检泵', text: 'N-11 井检泵：2026-08-28 → 2026-09-06，影响产量约 210 吨。' },
    { key: 'f4', path: '章节 04 计量与折算 ＞ 4.2 单位换算', text: '渤中区块原油密度按 0.89 t/m³ 折算，吨↔方换算＝质量÷密度。' }
  ] }
}
const subjectOf = r => (LEDGER_EXTRA[r.key]?.subject) || '—'

// 库活动流（F61）：操作人＝平台既有五角色；只记录不改数据
const ACTIVITIES = {
  1: [
    { time: '2026-09-26 16:48', who: '小李 · 地质/质检', action: '上传报告', target: '《N-02 井完井报告（英文 · 200 页）》' },
    { time: '2026-09-25 10:12', who: '阿强 · 平台运维', action: '开启图谱开关', target: '完井报告库 · 下次入库生效' },
    { time: '2026-09-24 09:30', who: '阿强 · 平台运维', action: '修改库配置', target: '切段方式：智能切段（256–1024 字）' },
    { time: '2026-09-22 15:40', who: '小李 · 地质/质检', action: '上传报告', target: '《N-11 井完井报告（英文 · 200 页）》' }
  ],
  2: [
    { time: '2026-09-26 11:20', who: '小李 · 地质/质检', action: '上传报告', target: '《渤中28-1 区块月度生产月报（2026-08）》' },
    { time: '2026-09-21 14:05', who: '阿强 · 平台运维', action: '修改库配置', target: '索引期加法：两项保持勾选' }
  ],
  3: [
    { time: '2026-09-20 10:00', who: '阿强 · 平台运维', action: '修改库配置', target: '关系图谱保持关闭（省抽取费）' }
  ]
}

const FLOW = ['解析（读出文字和图）', '切段', '向量化', '建索引', '索引期加法（摘要＋问题）']

// 四个索引开关：note 收进 ? 悬浮；off＝关掉时的后果提示（黄色警示卡）
const SWITCHES = [
  {
    key: 'semantic', name: '语义索引',
    note: '换种说法也能搜到——语义搜索的底子。',
    off: '关掉后：只剩关键词精确命中，问法一换就可能搜不到。'
  },
  {
    key: 'keyword', name: '关键词索引',
    note: '按字面精确搜：井号、编号一搜一个准。',
    off: '关掉后：换个说法的问句仍能靠语义索引命中，但精确编号（如 N-02）搜不到。'
  },
  {
    key: 'wiki', name: '百科页',
    note: '入库后顺手生成中文百科页——如 200 页英文完井报告 → 一页中文。',
    off: <span>关掉后：不生成中文百科页，英文原版只能整本翻；需要时去<a href="#/B4">「报告百科」页</a>人工翻。</span>
  },
  {
    key: 'graph', name: '关系图谱',
    note: '逐段抽"谁—什么关系→谁"，费用较高；没有关系的库（如制度文件库）建议关。',
    off: '（图谱已关）本次入库不做关系抽取，省下费用；"哪些井受过 N-06 注水影响"这类问题将答不了。想开 → 点上方开关。'
  }
]

const MODE_TEXT = {
  smart: '智能切段——按章节和语义边界切，一段 256–1024 字，相邻段重叠 10–20%。',
  fixed: '固定大小——每段等长，句子可能被拦腰斩断。',
  mixed: '大小段配合——小段进索引负责被找到，大段入库负责被读懂。'
}
const RAW_TEXT = '3. N-02 井完井情况。3.1 基本数据：N-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，井别采油（EW），2019-06-15 投产。3.2 完井段：详见射孔与防砂参数表。'

// 索引期加法自动产出的 10 个问题（来自这份报告的正文与插图）
const QUESTIONS = [
  'N-02 井是什么时候投产的？',
  'N-02 井在哪个平台、哪个区块？',
  'N-02 井的完井方式是什么？',
  'N-02 是采油井还是注水井？',
  'N-02 井的日产油、含水率是多少？',
  '报告里的岩性柱状图说了什么？',
  '报告提到哪几类措施？（压裂 / 酸化 / 补孔 / 调剖）',
  'N-06 注水影响哪些井？',
  '这份报告的中文百科页长什么样？',
  '这份报告适合回答哪类问题？'
]

const SUMMARY_TEXT = '本报告为 N-02 井（渤中28-1-N2）完井报告：井位于渤南区块 CEP-A 平台，井别采油，2019-06-15 投产，状态生产中；正文含完井段与投产信息，插图含岩性柱状图等。'

// 库配置初始值：语义/关键词/百科开、图谱关（省抽取费）；切段默认智能；索引期加法默认都做
const DEFAULT_CONFIG = { semantic: true, keyword: true, wiki: true, graph: false, mode: 'smart', addSummary: true, addQuestions: true }
const initConfigs = () => Object.fromEntries(LIBS.map(l => [l.key, { ...DEFAULT_CONFIG }]))

// 入库任务种子两行（失败/疑似卡住样例，Owner 拍板文案）：失败原因不写数字
const SEED_TASKS = [
  { key: 'tf', doc: '《N-11 井完井报告（英文 · 200 页）》', libKey: 1, state: 'failed', cur: 0, stopAt: '切段', reason: '扫描件某页图像质量差，无法识别' },
  { key: 'ts', doc: '《渤中28-1 区块月度生产月报（2026-07）》', libKey: 2, state: 'stuck', cur: 3, stopAt: null }
]

const sleep = ms => new Promise(r => setTimeout(r, ms))

// 切段对照面板：同一段报告原文，三种切法切出来不一样
function chunkPanel(mode) {
  return (
    <div>
      <div className="code-block">{RAW_TEXT}</div>
      <div style={{ marginTop: 8, fontSize: 13, lineHeight: 1.9 }}>
        {mode === 'smart' && (<>
          <div><Tag color="blue">小段 1</Tag>3. N-02 井完井情况。3.1 基本数据：N-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，井别采油（EW）。</div>
          <div><Tag color="blue">小段 2</Tag>……井别采油（EW），2019-06-15 投产。3.2 完井段：详见射孔与防砂参数表。</div>
        </>)}
        {mode === 'fixed' && (<>
          <div><Tag color="blue">小段 1</Tag>3. N-02 井完井情况。3.1 基本数据：N-02 井（渤中28-1-N2）位于渤</div>
          <div><Tag color="blue">小段 2</Tag>南区块 CEP-A 平台，井别采油（EW），2019-06-15 投产。3.2 完井段：详见……</div>
        </>)}
        {mode === 'mixed' && (<>
          <div><Tag color="blue">小段</Tag>（进索引，负责被找到）</div>
          <div style={{ marginLeft: 8 }}>① N-02 井（渤中28-1-N2）2019-06-15 投产。</div>
          <div style={{ marginLeft: 8 }}>② 井别采油（EW），位于 CEP-A 平台。</div>
          <div style={{ marginTop: 6 }}><Tag color="purple">大段</Tag>（只入库、不进索引，负责被读懂）</div>
          <div style={{ marginLeft: 8 }}>3. N-02 井完井情况。3.1 基本数据：……（整段全文）。</div>
        </>)}
      </div>
    </div>
  )
}

// 片段版本记录（F30 增补）：原始解析不可变，人工修正记新版本；第一期回看不回写
const initVersions = () => Object.fromEntries(
  Object.entries(LEDGER_EXTRA).flatMap(([k, v]) => v.frags.map(f => [f.key, [{ v: 1, text: f.text, note: '原始解析' }]]))
)

export default function B1() {
  const [libsLoading, setLibsLoading] = useState(true)
  const [tab, setTab] = useState('ledger') // ledger | tasks | libs

  // 报告台账筛选
  const [libF, setLibF] = useState('all')
  const [lkw, setLkw] = useState('')

  // 入库任务列表（上传追加，种子含失败/卡住样例）
  const [tasks, setTasks] = useState(SEED_TASKS)
  const nextTask = useRef(1)
  const runningRef = useRef(new Set())

  // 上传确认弹窗（目标库 + 该库配置只读预览）
  const [upOpen, setUpOpen] = useState(false)
  const [upLib, setUpLib] = useState(1)

  // 报告详情抽屉（台账行双击）
  const [detailKey, setDetailKey] = useState(null)

  // 片段人工修正（详情抽屉内）＋版本回看
  const [versions, setVersions] = useState(initVersions)
  const [fixFrag, setFixFrag] = useState(null) // {ledgerKey, fragKey}
  const [fixText, setFixText] = useState('')

  // 库管理（原库列表）：筛选 + 选中 + 按库配置 + 活动
  const [graphF, setGraphF] = useState('all')
  const [kw, setKw] = useState('')
  const [sel, setSel] = useState(null)
  const [configs, setConfigs] = useState(initConfigs)
  const [cfgLib, setCfgLib] = useState(null)
  const [saved, setSaved] = useState(false)
  const [actLib, setActLib] = useState(null)

  useEffect(() => {
    const id = setTimeout(() => setLibsLoading(false), 500)
    return () => clearTimeout(id)
  }, [])

  async function runTask(key) {
    if (runningRef.current.has(key)) return
    runningRef.current.add(key)
    const patch = p => setTasks(ts => ts.map(t => (t.key === key ? { ...t, ...p } : t)))
    patch({ state: 'running', cur: 0, done: false, stopAt: null, reason: null })
    for (let i = 1; i < FLOW.length; i++) { await sleep(650); patch({ cur: i }) }
    patch({ state: 'done', done: true })
    runningRef.current.delete(key)
  }
  function confirmUpload() {
    const key = nextTask.current++
    const lib = LIBS.find(l => l.key === upLib)
    setTasks(ts => [{ key, doc: TASK_DOC, libKey: upLib, libName: lib.name, state: 'running', cur: -1, done: false }, ...ts])
    setUpOpen(false)
    runTask(key)
  }

  function openCfg(key) {
    setSaved(false)
    setCfgLib(key)
  }
  function setCfg(key, patch) {
    setConfigs(s => ({ ...s, [key]: { ...s[key], ...patch } }))
    setSaved(false)
  }

  const mark = on => (on ? '✓' : '✗')

  // 任务展开区：逐步点亮的说明行（步 2 随切段方式联动；步 4 随该库四开关实时联动）
  function taskStepRows(t) {
    if (t.cur < 0) return []
    const cfg = configs[t.libKey]
    const libName = LIBS.find(l => l.key === t.libKey)?.name || ''
    const rows = [{ key: 's1', step: '步 1 · 解析', text: '读出正文和插图；报告原文原样存进文件库（桶：报告原文），一个字不动——以后任何引用都能翻回原文。' }]
    if (t.cur >= 1 && t.state !== 'failed') rows.push({ key: 's2', step: '步 2 · 切段', text: `切段方式：${MODE_TEXT[cfg.mode]} 三种切法的对照在「库管理」页签点"配置"现场切换。` })
    if (t.cur >= 2 && t.state !== 'failed') rows.push({ key: 's3', step: '步 3 · 向量化', text: '把每段换成一串"语义坐标"：意思相近的段坐标就相近——问句换个说法也能搜到。' })
    if (t.cur >= 3 && t.state !== 'failed') rows.push({
      key: 's4', step: '步 4 · 建索引',
      text: `按${libName}的四开关写入索引：语义 ${mark(cfg.semantic)} · 关键词 ${mark(cfg.keyword)} · 百科页 ${mark(cfg.wiki)} · 关系图谱 ${mark(cfg.graph)}。关掉的支路不跑、不产生抽取费用。`
    })
    return rows
  }

  const ledgerFiltered = LEDGER.filter(l =>
    (libF === 'all' || l.lib === libF) &&
    (!lkw.trim() || (l.doc + l.lib).toLowerCase().includes(lkw.trim().toLowerCase())))

  const ledgerColumns = [
    { title: '报告', dataIndex: 'doc', render: v => <b>{v}</b> },
    { title: '所属库', dataIndex: 'lib', width: 116 },
    {
      title: (<span>出处片段{helpIcon(<>切片管理中该报告的片段数——小段负责被找到，大段负责被读懂。未建检索切片的报告如实标"—"。</>)}</span>),
      dataIndex: 'refs', width: 92,
      render: v => (v ? `${v} 段` : <span style={dim}>—</span>)
    },
    {
      title: (<span>中文百科{helpIcon(<>入库时勾选"百科页"开关的报告，处理完自动生成中文结构化百科页（当前版本号随重建递增）。未生成的标"—"。</>)}</span>),
      dataIndex: 'wiki', width: 92,
      render: v => (v ? v : <span style={dim}>—</span>)
    },
    {
      title: '操作', width: 128, align: 'center',
      render: (_, r) => (
        <Space size={4}>
          <Tooltip title="下载原件——报告原件直链下载，链接小时级有效">
            <Button size="small" icon={<DownloadOutlined />}
              onClick={e => { e.stopPropagation(); message.success(`已生成${r.doc}下载直链——链接小时级有效`) }} />
          </Tooltip>
          {r.refs != null && (
            <Tooltip title="看切片——去切片管理页按报告浏览切出的片段">
              <Button size="small" icon={<FileTextOutlined />}
                onClick={e => { e.stopPropagation(); location.hash = '/B2' }} />
            </Tooltip>
          )}
          {r.wiki != null && (
            <Tooltip title="看百科——去报告百科页看中文结构化页">
              <Button size="small" icon={<BookOutlined />}
                onClick={e => { e.stopPropagation(); location.hash = '/B4' }} />
            </Tooltip>
          )}
        </Space>
      )
    }
  ]

  const TASK_STATE = {
    running: <Tag color="orange">处理中</Tag>,
    done: <Tag color="green">已完成</Tag>,
    failed: <Tag color="red">失败</Tag>,
    stuck: <Tag>疑似卡住</Tag>
  }

  const taskColumns = [
    { title: '报告', dataIndex: 'doc', render: (v, t) => <b>{v}{t.state === 'stuck' && <span style={{ ...dim, fontWeight: 'normal', marginLeft: 8 }}>已 20 多分钟没有进展</span>}</b> },
    { title: '目标库', width: 116, render: (_, t) => (t.libName || LIBS.find(l => l.key === t.libKey)?.name || '—') },
    { title: '状态', width: 96, render: (_, t) => TASK_STATE[t.state] },
    {
      title: '操作', width: 64, align: 'center',
      render: (_, t) => (
        <Tooltip title="重试/重跑入库管线">
          <Button size="small" icon={<RedoOutlined />} disabled={runningRef.current.has(t.key)}
            onClick={e => { e.stopPropagation(); runTask(t.key) }} />
        </Tooltip>
      )
    }
  ]

  const libFiltered = LIBS.filter(l => {
    if (graphF !== 'all' && l.sw[3].includes('✓') !== (graphF === 'on')) return false
    const q = kw.trim().toLowerCase()
    return !q || (l.name + l.doc).toLowerCase().includes(q)
  })

  const libColumns = [
    { title: '库', dataIndex: 'name', width: 120, render: v => <b>{v}</b> },
    { title: '最近入库', dataIndex: 'doc' },
    {
      title: (<span>索引开关{helpIcon(<>该库最近一次入库所用的四个索引开关：语义 / 关键词 / 百科页 / 关系图谱。下次入库用哪几个，在行尾"配置"里按库调整，保存后下次入库生效。</>)}</span>),
      dataIndex: 'sw', width: 320,
      render: sw => (
        <Space size={4} wrap>
          {sw.map(x => <Tag key={x} color={x.includes('✓') ? 'green' : 'default'} style={{ marginInlineEnd: 0 }}>{x}</Tag>)}
        </Space>
      )
    },
    {
      title: '操作', width: 96, align: 'center',
      render: (_, l) => (
        <Space size={4}>
          <Tooltip title="库配置（索引开关 / 切段方式 / 索引期加法）">
            <Button size="small" icon={<SettingOutlined />}
              onClick={e => { e.stopPropagation(); openCfg(l.key) }} />
          </Tooltip>
          <Tooltip title="活动——这个库的操作留痕">
            <Button size="small" icon={<HistoryOutlined />}
              onClick={e => { e.stopPropagation(); setActLib(l.key) }} />
          </Tooltip>
        </Space>
      )
    }
  ]

  const helpTop = helpIcon(
    <>在库报告的总账与入库管理：上传后平台自动切段、建索引，处理到哪步亮哪步；每个库可单独配四个索引开关和切段方式；处理完自动产出全文档摘要和"可能被问的 10 个问题"。</>
  )

  const cfgLibRow = LIBS.find(l => l.key === cfgLib)
  const detailRow = LEDGER.find(l => l.key === detailKey)
  const upCfg = configs[upLib]
  const _fixRow = fixFrag ? LEDGER.find(l => l.key === fixFrag.ledgerKey) : null
  const fixFragRow = fixFrag ? LEDGER_EXTRA[fixFrag.ledgerKey]?.frags.find(f => f.key === fixFrag.fragKey) : null

  if (libsLoading) {
    return (
      <Card><Skeleton active paragraph={{ rows: 6 }} /></Card>
    )
  }

  return (
    <div>
      <Card
        title={
          <Tabs
            activeKey={tab} size="small" onChange={setTab}
            items={[
              { key: 'ledger', label: `报告台账（${LEDGER.length}）` },
              { key: 'tasks', label: `入库任务（${tasks.length}）` },
              { key: 'libs', label: `库管理（${LIBS.length}）` }
            ]}
          />
        }
        extra={
          <Space size={4}>
            <span style={{ color: '#8a94a3', fontSize: 12 }}>原文一个字不动存档 · 索引按库配置、下次入库生效 · 关掉的支路不跑不花钱</span>
            {helpTop}
          </Space>
        }
      >
        {tab === 'ledger' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Space wrap size={8}>
                <Select size="small" style={{ width: 136 }} value={libF} onChange={setLibF}
                  options={[
                    { value: 'all', label: '所属库：全部' },
                    { value: '完井报告库', label: '完井报告库' },
                    { value: '生产月报库', label: '生产月报库' },
                    { value: '制度文件库', label: '制度文件库' }
                  ]} />
                <Input size="small" allowClear style={{ width: 240 }} value={lkw} onChange={e => setLkw(e.target.value)}
                  placeholder="搜报告名 / 所属库…" />
              </Space>
              <span style={{ color: '#8a94a3', fontSize: 12 }}>{`筛选结果 ${ledgerFiltered.length} / ${LEDGER.length} 份 · 双击行看详情`}</span>
            </div>
            <Table
              size="small" columns={ledgerColumns} dataSource={ledgerFiltered} pagination={false} rowKey="key"
              onRow={l => ({
                onDoubleClick: () => setDetailKey(l.key),
                style: { cursor: 'pointer' }
              })}
            />
            <div style={{ marginTop: 10, ...dim }}>
              新报告入库 → 切「入库任务」上传；索引与百科等产物的生成规则按库配置，见「库管理」。
            </div>
          </>
        )}

        {tab === 'tasks' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Space wrap size={8}>
                <Button type="primary" size="small" icon={<UploadOutlined />} onClick={() => setUpOpen(true)}>上传报告（直传）</Button>
                {helpIcon(<>报告从客户端直接传进文件库，不绕平台服务；解析、切段、建索引由平台在入库时自动完成。上传后先确认目标库与该库将采用的配置，确认后开跑。</>)}
              </Space>
              <span style={{ color: '#8a94a3', fontSize: 12 }}>{tasks.length ? `任务 ${tasks.length} 条` : ''}</span>
            </div>
            <Table
              size="small" columns={taskColumns} dataSource={tasks} pagination={false} rowKey="key"
              expandable={{
                expandRowByClick: true,
                expandedRowRender: t => (
                  <div style={{ padding: '4px 2px' }}>
                    {t.state === 'failed' && (
                      <Alert style={{ marginBottom: 12 }} type="error" showIcon message={
                        <span>停在「{t.stopAt}」阶段：{t.reason}——可重试；仍失败请报修。
                          <Button size="small" style={{ marginLeft: 8 }} icon={<RedoOutlined />}
                            onClick={e => { e.stopPropagation(); runTask(t.key) }}>重试</Button>
                        </span>} />
                    )}
                    {t.state === 'stuck' && (
                      <Alert style={{ marginBottom: 12 }} type="warning" showIcon message={
                        <span>已 20 多分钟没有进展：已没有任务在推进——可停止后重试。
                          <Button size="small" style={{ marginLeft: 8 }} icon={<RedoOutlined />}
                            onClick={e => { e.stopPropagation(); runTask(t.key) }}>重试</Button>
                        </span>} />
                    )}
                    <div onClick={() => runTask(t.key)} style={{ cursor: 'pointer' }}>
                      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>处理进度</span>
                        {helpIcon(<>五步依次点亮：解析 → 切段 → 向量化 → 建索引 → 索引期加法。点管线任意处可重跑一遍；关掉的索引支路直接跳过、不跑不花钱。</>)}
                        <span style={{ marginLeft: 'auto', fontSize: 12, color: '#8a94a3' }}>点管线任意处可重跑</span>
                      </div>
                      <Steps size="small" current={t.cur} status={t.state === 'done' ? 'finish' : 'process'}
                        items={FLOW.map(x => ({ title: x }))} />
                      <Table
                        style={{ marginTop: 14 }} size="small" pagination={false}
                        columns={[{ title: '步骤', dataIndex: 'step', width: 130 }, { title: '说明', dataIndex: 'text' }]}
                        dataSource={taskStepRows(t)} rowKey="key"
                        locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="管线启动后，每亮一步这里多一行说明。" /> }}
                      />
                    </div>
                    {t.state === 'done' && (
                      <div style={{ marginTop: 14 }}>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                          <span style={{ fontWeight: 600, fontSize: 13 }}>索引期加法产物</span>
                          {helpIcon(<>处理完自动多做两件事：全文档摘要 ×1；每 20 段生成一批"可能被问的问题"。是否生成在「库管理」的配置里勾选，保存后下次入库生效。</>)}
                        </div>
                        <Card size="small" style={{ marginBottom: 8 }}
                          title={<span><Tag color="green">摘要块</Tag>全文档摘要（自动生成）</span>}>
                          <span style={{ fontSize: 13 }}>{SUMMARY_TEXT}</span>
                        </Card>
                        <Card size="small"
                          title={<span><Tag color="orange">问题块</Tag>这份报告可能被问的 10 个问题（自动生成）</span>}>
                          <ol style={{ margin: 0, paddingLeft: 20, fontSize: 13, lineHeight: 2 }}>
                            {QUESTIONS.map((q, i) => <li key={i}>{q}</li>)}
                          </ol>
                        </Card>
                      </div>
                    )}
                  </div>
                )
              }}
              locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有入库任务：点上方「上传报告（直传）」发起一次入库。" /> }}
            />
          </>
        )}

        {tab === 'libs' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Space wrap size={8}>
                <Select size="small" style={{ width: 136 }} value={graphF} onChange={setGraphF}
                  options={[{ value: 'all', label: '图谱开关：全部' }, { value: 'on', label: '图谱已开' }, { value: 'off', label: '图谱已关' }]} />
                <Input size="small" allowClear style={{ width: 220 }} value={kw} onChange={e => setKw(e.target.value)}
                  placeholder="搜库名 / 最近入库…" />
              </Space>
              <span style={{ color: '#8a94a3', fontSize: 12 }}>{`筛选结果 ${libFiltered.length} / ${LIBS.length} 条`}</span>
            </div>
            <Table
              size="small" columns={libColumns} dataSource={libFiltered} pagination={false} rowKey="key"
              rowClassName={l => (l.key === sel ? 'ant-table-row-selected' : '')}
              onRow={l => ({
                onClick: () => setSel(l.key),
                onDoubleClick: () => { setSel(l.key); openCfg(l.key) },
                style: { cursor: 'pointer' }
              })}
            />
          </>
        )}
      </Card>

      {/* 上传确认：目标库 + 该库将采用的配置（只读预览） */}
      <Modal title="上传报告（直传）" open={upOpen} onCancel={() => setUpOpen(false)} footer={null} width={520}>
        <div style={fieldLabel}>目标库</div>
        <Select style={{ width: '100%' }} value={upLib} onChange={setUpLib}
          options={LIBS.map(l => ({ value: l.key, label: l.name }))} />
        <div style={{ ...fieldLabel, marginTop: 14 }}>
          本次入库将采用「{LIBS.find(l => l.key === upLib)?.name}」的库配置
          {helpIcon(<>配置在「库管理」页签按库维护，保存后下次入库生效——上传时不做单次覆盖，正在处理的报告不受影响。</>)}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 13 }}>
          <Space size={4} wrap>
            <Tag color={upCfg.semantic ? 'green' : 'default'}>语义 {mark(upCfg.semantic)}</Tag>
            <Tag color={upCfg.keyword ? 'green' : 'default'}>关键词 {mark(upCfg.keyword)}</Tag>
            <Tag color={upCfg.wiki ? 'green' : 'default'}>百科页 {mark(upCfg.wiki)}</Tag>
            <Tag color={upCfg.graph ? 'green' : 'default'}>关系图谱 {mark(upCfg.graph)}</Tag>
          </Space>
          <span>切段方式：{MODE_TEXT[upCfg.mode].split('——')[0]}</span>
          <span>索引期加法：摘要 {upCfg.addSummary ? '生成' : '不生成'} · 可能被问的问题 {upCfg.addQuestions ? '生成' : '不生成'}</span>
        </div>
        <div style={{ ...dim, marginTop: 10 }}>配置在「库管理」维护，保存后下次入库生效。</div>
        <Button type="primary" style={{ marginTop: 14 }} onClick={confirmUpload}>开始入库</Button>
      </Modal>

      {/* 报告详情（台账行双击） */}
      <Drawer title={detailRow ? '报告详情' : ''} placement="right" width={520}
        open={detailKey != null} onClose={() => setDetailKey(null)}>
        {detailRow && (
          <>
            <Descriptions size="small" column={1} colon labelStyle={{ width: 110, color: '#8a94a3' }}>
              <Descriptions.Item label="报告名">{detailRow.doc}</Descriptions.Item>
              <Descriptions.Item label="所属库">{detailRow.lib}</Descriptions.Item>
              <Descriptions.Item label="井号 / 月份">{subjectOf(detailRow)}</Descriptions.Item>
              <Descriptions.Item label="出处片段">{detailRow.refs != null ? `${detailRow.refs} 段` : '—'}</Descriptions.Item>
              <Descriptions.Item label="中文百科">{detailRow.wiki || '—'}</Descriptions.Item>
              <Descriptions.Item label="入库状态">已入库</Descriptions.Item>
            </Descriptions>
            <div style={{ marginTop: 16, fontWeight: 600, fontSize: 13 }}>
              片段预览
              {helpIcon(<>原文片段（与「切片管理」页同源）；发现解析错字可点"修正"——保存后重建索引，别人已改过时会提示刷新后再改。</>)}
            </div>
            {(LEDGER_EXTRA[detailRow.key]?.frags || []).map(f => {
              const ver = versions[f.key] || []
              const cur = ver[ver.length - 1]
              return (
                <div key={f.key} style={{ border: '1px solid rgba(255,255,255,0.12)', borderRadius: 6, padding: '8px 12px', marginTop: 8 }}>
                  <div style={{ ...dim, marginBottom: 4 }}>{f.path}{cur && ver.length > 1 ? ` · 已修正（v${cur.v}）` : ''}</div>
                  <div style={{ fontSize: 13 }}>{cur ? cur.text : f.text}</div>
                  <div style={{ marginTop: 6 }}>
                    <Button size="small" icon={<FormOutlined />}
                      onClick={() => { setFixFrag({ ledgerKey: detailRow.key, fragKey: f.key }); setFixText(cur ? cur.text : f.text) }}>修正</Button>
                  </div>
                </div>
              )
            })}
            {!LEDGER_EXTRA[detailRow.key] && (
              <div style={{ ...dim, marginTop: 8 }}>该报告的片段暂未收录，入库处理后可预览。</div>
            )}
          </>
        )}
      </Drawer>

      {/* 片段人工修正（F30 增补）：编辑＋版本回看（第一期不回写） */}
      <Modal title={fixFragRow ? '修正片段' : ''} open={!!fixFrag} onCancel={() => setFixFrag(null)} footer={null} width={560}>
        {fixFragRow && (
          <>
            <div style={dim}>{fixFragRow.path}</div>
            <Input.TextArea style={{ marginTop: 8 }} rows={4} value={fixText} onChange={e => setFixText(e.target.value)} />
            <div style={{ ...dim, marginTop: 8 }}>保存后重建检索索引；若别人已改过这段，保存时会提示你刷新后再改。</div>
            <Button type="primary" style={{ marginTop: 10 }}
              onClick={() => {
                setVersions(v => ({ ...v, [fixFrag.fragKey]: [...(v[fixFrag.fragKey] || []), { v: (v[fixFrag.fragKey]?.length || 1) + 1, text: fixText.trim() || fixFragRow.text, note: '人工修正' }] }))
                message.success('已保存——将重建检索索引。')
                setFixFrag(null)
              }}>保存修正</Button>
            <div style={{ marginTop: 16, fontWeight: 600, fontSize: 13 }}>版本记录（第一期只回看，不回写）</div>
            <Table style={{ marginTop: 8 }} size="small" pagination={false} rowKey="v"
              columns={[
                { title: '版本', dataIndex: 'v', width: 70, render: (v, r) => (r.note === '人工修正' ? `v${v}（当前）` : `v${v}`) },
                { title: '来源', dataIndex: 'note', width: 90 },
                { title: '内容', dataIndex: 'text', render: (t, r) => <span style={{ fontSize: 12 }}>{t}{(versions[fixFrag.fragKey] || [])[0]?.v === r.v && r.note === '原始解析' && versions[fixFrag.fragKey].length > 1 ? '（已修正，见新版）' : ''}</span> }
              ]}
              dataSource={versions[fixFrag.fragKey] || []} />
          </>
        )}
      </Modal>

      {/* 库活动流（F61） */}
      <Drawer title={actLib ? `活动 · ${LIBS.find(l => l.key === actLib)?.name}` : ''} placement="right" width={520}
        open={actLib != null} onClose={() => setActLib(null)}>
        <Table size="small" pagination={false} rowKey="time"
          columns={[
            { title: '时间', dataIndex: 'time', width: 140 },
            { title: '操作人', dataIndex: 'who', width: 130 },
            { title: '动作', dataIndex: 'action', width: 100 },
            { title: '对象', dataIndex: 'target' }
          ]}
          dataSource={actLib ? ACTIVITIES[actLib] || [] : []} />
        <div style={{ ...dim, marginTop: 10 }}>只记录，不改任何数据。</div>
      </Drawer>

      <Modal
        title={<span>库配置 · {cfgLibRow ? cfgLibRow.name : ''}{helpIcon(<>四个索引开关、切段方式、索引期加法都按库单独配置；保存后在下次入库时生效，正在处理的报告不受影响。</>)}</span>}
        open={cfgLib != null} onCancel={() => setCfgLib(null)} footer={null} width={680}
      >
        {cfgLib != null && (() => {
          const cfg = configs[cfgLib]
          return (
            <>
              <div style={fieldLabel}>入库索引开关（按库配置）</div>
              {SWITCHES.map(s => (
                <div key={s.key} style={{ marginBottom: 12 }}>
                  <Space align="start">
                    <Switch size="small" checked={cfg[s.key]} onChange={v => setCfg(cfgLib, { [s.key]: v })} />
                    <b>{s.name}</b>
                    {helpIcon(s.note)}
                  </Space>
                  {!cfg[s.key] && (
                    <Alert style={{ marginTop: 6 }} type="warning" showIcon message={s.off} />
                  )}
                </div>
              ))}

              <div style={{ ...fieldLabel, marginTop: 4 }}>
                切段方式（三选一）
                {helpIcon(<>同一段报告原文，三种切法切出来不一样：智能切段一段 256–1024 字、相邻段重叠 10–20%；固定大小每段等长；大小段配合＝小段进索引被找到、大段入库被读懂。</>)}
              </div>
              <Tabs
                size="small" activeKey={cfg.mode} onChange={k => setCfg(cfgLib, { mode: k })}
                items={[
                  { key: 'smart', label: '智能切段（256–1024 字）', children: chunkPanel('smart') },
                  { key: 'fixed', label: '固定大小', children: chunkPanel('fixed') },
                  { key: 'mixed', label: '大小段配合', children: chunkPanel('mixed') }
                ]}
              />

              <div style={{ ...fieldLabel, marginTop: 4 }}>
                索引期加法（处理完自动多做两件事）
                {helpIcon(<>全文档摘要 ×1；每 20 段自动生成一批"可能被问的问题"。处理完随"索引期加法"一步一起产出，见「入库任务」展开区。</>)}
              </div>
              <Checkbox checked={cfg.addSummary} onChange={e => setCfg(cfgLib, { addSummary: e.target.checked })}>自动生成全文档摘要 ×1</Checkbox>
              <div style={{ marginTop: 6 }}>
                <Checkbox checked={cfg.addQuestions} onChange={e => setCfg(cfgLib, { addQuestions: e.target.checked })}>每 20 段自动生成"可能被问的问题"一批</Checkbox>
              </div>

              <Space style={{ marginTop: 16 }}>
                <Button type="primary" size="small" onClick={() => setSaved(true)}>保存本库配置</Button>
                {saved && <span style={{ fontSize: 12, color: '#8a94a3' }}>已保存——开关在下次入库时生效，正在处理的报告不受影响。</span>}
              </Space>
            </>
          )
        })()}
      </Modal>
    </div>
  )
}
