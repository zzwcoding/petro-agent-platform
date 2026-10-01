import { useEffect, useRef, useState } from 'react'
import {
  Button, Card, Col, Descriptions, Drawer, Empty, Modal, Row, Select, Skeleton, Space, Steps, Table, Tabs, Tag, Tooltip
} from 'antd'
import { FileSearchOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import { TICKETS } from '../data/changeTickets.jsx'

window.__traces = Object.assign(window.__traces || {}, {
  C1: 'F19 语义层四域 · F23 通用格式导出 · F26 评分卡选表 · F39 治理本体仓 · m16 语义层与指标注册 · m24 治理本体仓'
})

const TERM_STATUS = ['全部状态', '有效', '禁用词', '有效（限作业区语境）', '有效（待联席裁决）', '有效（引用马涛）', '有效（已届满）']
const TERM_OWNERS = ['全部负责人', '开发室', '采油工艺所', '地质研究所', '语义 Owner']

// 票 93：命名导出，E1 槽位选项同源引用（禁止两页各维护一份拷贝）
export const TERMS = [
  { key: 1, term: '老完成率', type: '禁用词', def: 'v1 口径（不含自用油折算），2024 年废弃', status: '禁用（替代：产量完成率）', st: '禁用词', owner: '开发室', src: '设定书 §6', ver: 'v1', exp: '—（已禁用）' },
  { key: 2, term: '剔检产量', type: '别名 → 净产量', def: '剔除检修井口径', status: '有效', st: '有效', owner: '开发室', src: '设定书 §6', ver: 'v1', exp: '2027-12-31' },
  { key: 3, term: '有效产量', type: '一词两译', def: '需修饰词消歧（开井日历 / 剔检）', status: '有效', st: '有效', owner: '开发室', src: '设定书 §6', ver: 'v1', exp: '2027-06-30' },
  { key: 4, term: '躺井', type: '黑话 → 停产待检泵', def: '作业区口语', status: '有效（限作业区语境）', st: '有效（限作业区语境）', owner: '采油工艺所', src: '设定书 §6', ver: 'v1', exp: '2026-12-31' },
  { key: 5, term: '时率', type: '缩写 → 抽油机时率', def: '见指标 14', status: '有效', st: '有效', owner: '采油工艺所', src: '设定书 §6', ver: 'v1', exp: '2027-06-30' },
  { key: 6, term: '水淹层', type: '术语', def: '驱替前沿到达的高含水层段', status: '有效', st: '有效', owner: '地质研究所', src: '设定书 §6', ver: 'v1', exp: '2028-12-31' },
  { key: 7, term: '递减增油', type: '术语', def: '见指标 10（含口径争议注记）', status: '有效（待联席裁决）', st: '有效（待联席裁决）', owner: '采油工艺所', src: '设定书 §6', ver: 'v1', exp: '2027-03-31' },
  { key: 8, term: '存水率', type: '术语', def: '注入水留存地层比例（物质平衡用）', status: '有效', st: '有效', owner: '开发室', src: '设定书 §6', ver: 'v1', exp: '长期' },
  { key: 9, term: '配注合格率', type: '术语', def: '分层实注 / 配注 达标井次占比', status: '有效', st: '有效', owner: '采油工艺所', src: '设定书 §6', ver: 'v1', exp: '2027-12-31' },
  { key: 10, term: '三多四难', type: '治理热词', def: '数据库多、平台多、孤立应用多 / 共享难、复用难、开发难、协同难', status: '有效（引用马涛）', st: '有效（引用马涛）', owner: '语义 Owner', src: '设定书 §6', ver: 'v1', exp: '长期（引用类）' },
  { key: 11, term: '日产液', type: '别名 → 日产液量', def: '作业区口语缩写', status: '有效（已届满 · 命中带漂移标注）', st: '有效（已届满）', owner: '开发室', src: '设定书 §6', ver: 'v1', exp: '2026-06-30（已届满）' }
]

const STATUS_COLORS = {
  有效: 'green',
  禁用词: 'red',
  '有效（限作业区语境）': 'green',
  '有效（待联席裁决）': 'orange',
  '有效（引用马涛）': 'green',
  '有效（已届满）': 'gold'
}

const METRIC_OWNERS = ['全部负责人', '开发室', '采油工艺所', '销售计量站']

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

// —— 原「指标口径详情」页（C4，票 110 撤并）搬入的增量字段与澄清交互 ——
// 修饰词为台账未单列的增量字段；其余字段全部取自上方 METRICS
const MODS = { 2: '开井日历折算 / 剔检（修饰词消歧）' }
const modsOf = key => MODS[key] || '—（未登记修饰词）'
// C1 台账 grain 为「粒度 · 单位」合并字段，拆开展示（拆法：最后一个「·」之后为单位）
const grainUnit = g => {
  const i = g.lastIndexOf('·')
  return i < 0 ? [g, '—'] : [g.slice(0, i).trim(), g.slice(i + 1).trim()]
}
const isAmbiguousName = name => name.includes('两支口径')
const CALLOUT_TEXTS = {
  A: '出数口径：开井日历折算。按开井日历折算出数，跨月检修各月照实计入。答案标注：口径＝开井日历折算。',
  B: '出数口径：剔除检修。把检修井剔除后算净产量（别名「剔检产量」）。答案标注：口径＝剔除检修。',
  D: '你没有选——按默认口径「开井日历折算」出数。答案已自动标注「默认口径」，明示没让你猜着算。'
}
const LINK_FLOW = [
  { t: <span>提案进<a href="#/C2">语义修订提案池</a></span> },
  { t: <span>过<a href="#/C3">发布前安检</a>（五道检查）</span> },
  { t: <span>Owner 批准 → 生效（可回滚）</span> }
]
const REL_TERMS = TERMS.filter(t => t.type === '一词两译' || t.type.startsWith('别名'))
const relTermColumns = [
  { title: '术语', dataIndex: 'term', render: v => <b>{v}</b> },
  { title: '类型', dataIndex: 'type' },
  { title: '定义', dataIndex: 'def' },
  { title: '状态', dataIndex: 'st', render: v => <Tag color={v === '有效' ? 'green' : 'orange'}>{v}</Tag> },
  { title: '负责人', dataIndex: 'owner' },
  { title: '有效期', dataIndex: 'exp', width: 130 }
]

// 票 93：命名导出，E1 指标槽选项同源引用
export const METRICS = [
  { key: 1, name: '★产量完成率', def: 'Σ实际产油 ÷ Σ计划配产 × 100%', grain: '月（按区块 / 油田）· %', detail: true, status: ['生效中'], owner: '开发室', src: 'A.2 日产计量＋配产表', dispute: '计划版本切换日双值' },
  { key: 2, name: '★有效产量（两支口径）', def: '开井日历折算 / 检修剔除', grain: '月 · 吨', detail: true, status: ['生效中'], owner: '开发室', src: 'A.2 日产计量＋A.4 检修台账', dispute: '跨月检修切割' },
  { key: 3, name: '☆自然递减率', def: '月：1 − q_t / q_(t−1)（扣新井与措施增油）；年化：指数拟合 q(t)=q_i·e^(−Dt)', grain: '月 · 年 · %', status: ['生效中'], owner: '开发室', src: 'A.2 日产计量', dispute: '措施扣除口径' },
  { key: 4, name: '☆综合递减率', def: '不扣措施的对比期递减', grain: '月 · 年 · %', status: ['生效中'], owner: '开发室', src: 'A.2 日产计量', dispute: '与自然递减率混用事故' },
  { key: 5, name: '☆综合含水率', def: 'Q_w ÷（Q_o＋Q_w）× 100%', grain: '月 · %', status: ['生效中'], owner: '开发室', src: 'A.2 日产计量＋A.6 化验', dispute: '化验 vs 计量打架' },
  { key: 6, name: '☆注采比 β', def: '月注水量 ÷ 月产液量（体积折算）', grain: '月 · 无量纲', status: ['生效中'], owner: '采油工艺所', src: 'A.3 注水日报＋A.2 日产计量', dispute: '折算系数按区块' },
  { key: 7, name: '☆累积亏空', def: 'Σ注水 − Σ产液', grain: '累计 · 方', status: ['生效中'], owner: '开发室', src: 'A.3 注水日报＋A.2 日产计量', dispute: '—' },
  { key: 8, name: '☆措施有效率 η', def: 'N_y ÷ N_z × 100%（有效井次 ÷ 总井次）', grain: '批次 · %', status: ['生效中'], owner: '采油工艺所', src: 'A.5 措施台账', dispute: '"有效"判据' },
  { key: 9, name: '☆措施有效期 T', def: 't₂ − t₁（天）', grain: '单井 · 措施 · 天', status: ['生效中'], owner: '采油工艺所', src: 'A.5 措施台账', dispute: '30% 行缺失' },
  { key: 10, name: '☆递减增油', def: '受效油井实际产油 − 按 d_a 拟合基线 q₀(1−d_a)^t；多井受效按劈分系数（Σ=1）分摊；多措施叠加以主要措施为主', grain: '井组 · 年 · 吨', status: ['生效中', '待联席裁决'], owner: '采油工艺所（开发室联席）', src: 'A.2＋A.5＋受效关系', dispute: '一数多源争议之最（事故 7）' },
  { key: 11, name: '★商品量', def: '脱水稳定后净重（扣自用油输差）', grain: '月 · 吨', status: ['生效中'], owner: '销售计量站', src: 'A.8 月度结算', dispute: '与井口口径天然不等' },
  { key: 12, name: '☆机采系统能效', def: '系统级 / 单元级 / 设备级三级＋统计限值（优良 / 合格）', grain: '月 · %', status: ['生效中'], owner: '采油工艺所', src: 'A.7 设备状态', dispute: '分组限值' },
  { key: 13, name: '☆检泵周期', def: '本次检泵日 − 上次检泵日', grain: '单井 · 天', status: ['生效中'], owner: '采油工艺所', src: 'A.4 检修台账', dispute: '—' },
  { key: 14, name: '☆抽油机时率', def: 'Σ开井天数 ÷ Σ日历天 × 100%', grain: '月 · %', status: ['生效中'], owner: '采油工艺所', src: 'A.2 日产计量', dispute: '—' },
  { key: 15, name: '☆桶油增产成本', def: '措施总投入 ÷ 折算增油量（桶，6.29 桶/m³）', grain: '批次 · 元/桶', status: ['生效中'], owner: '采油工艺所＋财务', src: 'A.5 措施台账＋ERP', dispute: '经营 × 技术联席' }
]

// 票 93：指标台账名剥常用标记（★/☆）与口径注记后缀（"（两支口径）"等）得槽位用纯名；
// E1 指标槽与 C2 处方段「变更对象」同源引用，禁止各页自留剥法拷贝
export const metricLabel = name => name.replace(/^[★☆]/, '').replace(/（[^）]*）$/, '').replace(/\s+[ηT]$/, '')

// 实体名册＝对象与关系台账的实例名册（设定书 §A.1）：E1 实体槽与 C2 处方段「变更对象」（对象与关系）同源引用；
// 井组为 demo 装配 3 口，册子口径共 12 口
export const ENTITY_GROUPS = [
  { label: '区块', options: ['渤南', '渤中'] },
  { label: '平台', options: ['CEP-A', 'CEP-B'] },
  { label: '井（demo 装配，册子口径共 12 口 · 设定书 §A.1）', options: ['N-02', 'N-06', 'N-11'] }
]

const OBJECTS = [
  { key: 1, obj: '井', attr: '井号 / 井别 / 投产日 / 状态机' },
  { key: 2, obj: '井筒', attr: '段 / 射孔 / 防砂' },
  { key: 3, obj: '区块', attr: '§5 未列属性' },
  { key: 4, obj: '油田', attr: '§5 未列属性' },
  { key: 5, obj: '平台', attr: '§5 未列属性' },
  { key: 6, obj: '设备', attr: '§5 未列属性' },
  { key: 7, obj: '措施', attr: '§5 未列属性' },
  { key: 8, obj: '化验样', attr: '§5 未列属性' },
  { key: 9, obj: '受效关系', attr: '注水井 → 受效油井，多对多；属性＝劈分系数（Σ=1）、响应起始日——系数劈分是强制要求，设定书 §5' },
  { key: 10, obj: '配注层', attr: '§5 未列属性' }
]

const RELATIONS = [
  { key: 1, rel: '井 —隶属→ 区块 —隶属→ 油田', read: '井属于哪个区块，区块属于哪个油田' },
  { key: 2, rel: '平台 —承载→ 井', read: '井装在哪个平台上' },
  { key: 3, rel: '注水井 —受效→ 油井', read: '哪口注水井的注水，效果落在哪口油井上' },
  { key: 4, rel: '措施 —作用于→ 井', read: '压裂 / 酸化等措施做在哪口井上' },
  { key: 5, rel: '化验样 —取样自→ 井', read: '化验的水样取自哪口井' }
]

const WHITELIST = [
  { key: 1, ok: '可以', tables: '日产计量 oil_production_daily ⋈ 井档案 well_info', how: '用井号连' },
  { key: 2, ok: '可以', tables: '日产计量 oil_production_daily ⋈ 日期维表 date_dim', how: '按日期连' },
  { key: 3, ok: '默认不给', tables: '日产计量 oil_production_daily ⋈ 化验样 fluid_test', how: '须井号＋取样日期双键＋时间容差，经清洗层视图中转' },
  { key: 4, ok: '默认不给', tables: '日产计量 oil_production_daily ⋈ 注水日报 water_injection_daily（直连）', how: '须经"受效关系"这个对象中转，不许硬拼' }
]

const SCRIPT_STEPS = ['定口径（递减增油）', '有效性判定', '技术指标计算（指标 8–10）', '受效判断', '劈分系数', '增油核算', '桶油成本', '归档进"已验证指标"证据']

const NA = <span style={{ color: '#8a94a3' }}>未登记（待 Owner 补登）</span>

// 工作流登记列表：与 A3 数据变动审批的「工作流&账号」对齐（A3 引用 8 条 + 本页 2 条 = 10 条）
// 票 93：命名导出，E1「关联工作流」选项同源引用
export const WORKFLOWS = [
  {
    key: 'wf1', name: '《产量下滑归因》', account: '产量分析', status: '登记', src: '设定书 §7',
    trigger: '听到"为什么下滑"类问题开工。',
    steps: (
      <ol style={{ paddingLeft: 20, margin: 0 }}>
        <li>拉完成率与构成（产油 / 开井数 / 时率）</li>
        <li>分解：新井贡献 / 老井递减 / 措施增油 / 停产影响（用指标 3 / 8 / 10）</li>
        <li>归因分支：地质——含水上升？工程——检泵停产？管理——配产调整？</li>
        <li>下钻受效关系与检修台账</li>
        <li>生成归因报告</li>
      </ol>
    ),
    defaults: '时间窗默认最近 30 天、范围默认全区块，并明确标注"默认"。',
    confirm: '置信度高→少问人；低→必须人工确认档位（设定书 §7）。',
    contract: '结论＋证据链＋数据版本，三样齐才算答完。',
    meta: '未落（如实标注）· 草案（待 Owner 审定）· v1。'
  },
  {
    key: 'wf2', name: '《注水井措施评估》', account: '未绑定', src: '报告《注水井措施评估》· 设定书 §7',
    trigger: null,
    steps: <span>{SCRIPT_STEPS.join(' → ')}</span>,
    defaults: null, confirm: null,
    contract: '第⑧步归档进"已验证指标"证据（半截登记，待补全）。',
    meta: '未落（如实标注）· 草案（待 Owner 审定）· v1。'
  },
  {
    key: 'wf3', name: '《档案质量体检》', account: '未绑定', src: null,
    trigger: '周期体检 + 问答人工指令承接（低风险自动档）。', steps: null, defaults: null, confirm: null,
    contract: '低风险类：不碰计量数字，自动执行并留审计。',
    meta: '未落（如实标注）· 草案 · —。'
  },
  {
    key: 'wf4', name: '《复产确认检查》', account: '未绑定', src: null,
    trigger: '表间矛盾监控：检修完成＋产量表有行＋档案状态停产。', steps: null, defaults: null, confirm: null,
    contract: '高风险：出变动单挂起，等人工终审。',
    meta: '未落（如实标注）· 草案 · —。'
  },
  { key: 'wf5', name: '《低产井措施筛查》', account: '未绑定', src: null, trigger: null, steps: null, defaults: null, confirm: null, contract: null, meta: '未落（如实标注）· 草案 · —。' },
  { key: 'wf6', name: '《机采井工况诊断》', account: '未绑定', src: null, trigger: null, steps: null, defaults: null, confirm: null, contract: null, meta: '未落（如实标注）· 草案 · —。' },
  { key: 'wf7', name: '《区块注采平衡评估》', account: '未绑定', src: null, trigger: null, steps: null, defaults: null, confirm: null, contract: null, meta: '未落（如实标注）· 草案 · —。' },
  {
    key: 'wf8', name: '《幻觉拦截周报》', account: '未绑定', src: null,
    trigger: '周期回放：幻觉误放率超阈值 → 出配置变动单。', steps: null, defaults: null, confirm: null, contract: null,
    meta: '未落（如实标注）· 草案 · —。'
  },
  { key: 'wf9', name: '《平台运行周报》', account: '未绑定', src: null, trigger: null, steps: null, defaults: null, confirm: null, contract: null, meta: '未落（如实标注）· 草案 · —。' },
  { key: 'wf10', name: '《月度统计对账》', account: '未绑定', src: null, trigger: null, steps: null, defaults: null, confirm: null, contract: null, meta: '未落（如实标注）· 草案 · —。' }
]

const regCount = w => [w.trigger, w.steps, w.defaults, w.confirm, w.contract].filter(Boolean).length

// Action 合同既有事实清单（源 lessons/61 · 票 92 引用主位）：注册名＋业务名，C2 处方段「变更对象」（Action 合同）选项同源引用
export const ACTIONS = [
  'update_well_remark 更新井备注',
  'adjust_production_plan 调整配产',
  'adjust_injection_volume 配注上调'
]

const termColumns = [
  { title: '术语', dataIndex: 'term', render: v => <b>{v}</b> },
  { title: '类型', dataIndex: 'type' },
  { title: '定义', dataIndex: 'def' },
  { title: '状态', dataIndex: 'status', render: (v, r) => <Tag color={STATUS_COLORS[r.st]}>{v}</Tag> },
  { title: '有效期', dataIndex: 'exp', width: 140, render: (v, r) => r.st === '有效（已届满）' ? <b style={{ color: '#d4380d' }}>{v}</b> : v },
  { title: '负责人', dataIndex: 'owner' },
  { title: '来源', dataIndex: 'src' },
  { title: '版本', dataIndex: 'ver' }
]

const metricColumns = [
  { title: '#', dataIndex: 'key', width: 40 },
  { title: '指标', dataIndex: 'name', render: v => <b>{v}</b> },
  { title: '定义与公式', dataIndex: 'def' },
  { title: '粒度 · 单位', dataIndex: 'grain' },
  {
    title: '状态', dataIndex: 'status',
    render: v => <span>{v.map((s, i) => <Tag key={i} color={s === '生效中' ? 'green' : 'orange'}>{s}</Tag>)}</span>
  },
  { title: '负责人', dataIndex: 'owner' },
  { title: '数据源', dataIndex: 'src' },
  { title: '争议注记', dataIndex: 'dispute' }
]

const objColumns = [
  { title: '对象', dataIndex: 'obj', render: v => <b>{v}</b> },
  { title: '属性·说明', dataIndex: 'attr' },
  { title: '状态', render: () => <Tag>草案</Tag> },
  { title: '负责人', render: () => '—（未落）' },
  { title: '来源', render: () => '设定书 §5' },
  { title: '版本', render: () => '—（未落）' }
]

const relColumns = [
  { title: '关系', dataIndex: 'rel', render: v => <b>{v}</b> },
  { title: '读法', dataIndex: 'read' },
  { title: '来源', render: () => '设定书 §5' }
]

const wlColumns = [
  {
    title: '能否关联', dataIndex: 'ok', width: 110,
    render: v => <Tag color={v === '可以' ? 'green' : 'orange'}>{v}</Tag>
  },
  { title: '两张表', dataIndex: 'tables' },
  { title: '说明', dataIndex: 'how' }
]

const emptyText = <Empty description="没有符合筛选条件的条目" image={Empty.PRESENTED_IMAGE_SIMPLE} />

export default function C1Assets() {
  const [loading, setLoading] = useState(true)
  const [tStatus, setTStatus] = useState('全部状态')
  const [tOwner, setTOwner] = useState('全部负责人')
  const [mOwner, setMOwner] = useState('全部负责人')
  const [wfOpen, setWfOpen] = useState(null)
  const wf = WORKFLOWS.find(w => w.key === wfOpen)
  // 原「指标口径详情」页（C4）撤并进抽屉（票 110）：详情 / 澄清窗 / 联动提示
  const [mDetail, setMDetail] = useState(null)
  const [clarifyOpen, setClarifyOpen] = useState(false)
  const [picked, setPicked] = useState(null)
  const [showLinkage, setShowLinkage] = useState(false)
  const linkageRef = useRef(null)
  const metric = METRICS.find(m => m.key === mDetail)
  const [mGrain, mUnit] = metric ? grainUnit(metric.grain) : ['', '']
  const ambiguous = metric ? isAmbiguousName(metric.name) : false

  function submitChange() {
    setClarifyOpen(false)
    setShowLinkage(true)
    setTimeout(() => linkageRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
  }

  const wfColumns = [
    { title: '工作流', dataIndex: 'name', render: v => <b>{v}</b> },
    { title: '状态', width: 76, render: (_, w) => w.status === '登记' ? <Tag color="blue">登记</Tag> : <Tag>草案</Tag> },
    { title: '登记项', width: 80, align: 'center', render: (_, w) => `${regCount(w)} / 5` },
    { title: '账号', dataIndex: 'account', render: v => v === '未绑定' ? <span style={{ color: '#8a94a3' }}>未绑定</span> : v },
    { title: '来源', dataIndex: 'src', render: v => v || <span style={{ color: '#8a94a3' }}>未登记</span> },
    {
      title: '操作', width: 86, align: 'center',
      render: (_, w) => <Button size="small" onClick={e => { e.stopPropagation(); setWfOpen(w.key) }}>详情</Button>
    }
  ]

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 600)
    return () => clearTimeout(t)
  }, [])

  const termRows = TERMS.filter(r =>
    (tStatus === '全部状态' || r.st === tStatus) && (tOwner === '全部负责人' || r.owner === tOwner))
  const metricRows = METRICS.filter(r => mOwner === '全部负责人' || r.owner === mOwner)

  const termsTab = (
    <div>
      <Row gutter={8} align="middle" style={{ marginBottom: 12 }}>
        <Col>
          <Select value={tStatus} onChange={setTStatus} style={{ width: 200 }}
            options={TERM_STATUS.map(v => ({ value: v, label: v }))} />
        </Col>
        <Col>
          <Select value={tOwner} onChange={setTOwner} style={{ width: 160 }}
            options={TERM_OWNERS.map(v => ({ value: v, label: v }))} />
        </Col>
        <Col><span style={{ fontSize: 12, color: '#8a94a3' }}>筛选结果 {termRows.length} / {TERMS.length} 条</span></Col>
      </Row>
      <Table size="small" columns={termColumns} dataSource={termRows} pagination={false}
        locale={{ emptyText }} rowKey="key" />
      <Card size="small" style={{ marginTop: 12, background: 'rgba(250,173,20,0.10)' }} title="过期术语命中时（演示态 · 源 U09 A1.13-A1.15）">
        <div className="code-block">{`问：「上月日产液多少？」——命中已届满术语「日产液」（有效期 2026-06-30）
答：渤南 8 月日产液量 1,6xx 方。
　（漂移标注：术语「日产液」有效期已届满，定义待 Owner 复核——本次按现行解析照答，命中解析照常。）`}</div>
        <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 8 }}>
          过期机器判（到日即标）、废弃人判（禁用/替代需人裁定）；过期不自动失效、只打标——硬切换走审批改文件、版本加一（<a href="#/C2">语义修订提案池</a>），不悄悄改。
        </div>
      </Card>
    </div>
  )

  const metricsTab = (
    <div>
      <Row gutter={8} align="middle" style={{ marginBottom: 12 }}>
        <Col>
          <Select value={mOwner} onChange={setMOwner} style={{ width: 160 }}
            options={METRIC_OWNERS.map(v => ({ value: v, label: v }))} />
        </Col>
        <Col><span style={{ fontSize: 12, color: '#8a94a3' }}>筛选结果 {metricRows.length} / {METRICS.length} 条</span></Col>
      </Row>
      <Table size="small" pagination={false}
        locale={{ emptyText }} rowKey="key" dataSource={metricRows}
        columns={[...metricColumns, {
          title: '操作', width: 70, align: 'center',
          render: (_, r) => (
            <Tooltip title="查看口径详情">
              <Button size="small" icon={<FileSearchOutlined />}
                onClick={e => { e.stopPropagation(); setMDetail(r.key) }} />
            </Tooltip>
          )
        }]} />
    </div>
  )

  const objectsTab = (
    <div>
      <Table size="small" columns={objColumns} dataSource={OBJECTS} pagination={false} rowKey="key"
        title={() => '业务对象（10 个）'} />
      <Table size="small" style={{ marginTop: 16 }} columns={relColumns} dataSource={RELATIONS} pagination={false} rowKey="key"
        title={() => '对象之间的关系（5 条）'} />
      <Card size="small" style={{ marginTop: 16 }} title="哪些表能关联（白名单，不在单子上的默认不给连）">
        <Table size="small" columns={wlColumns} dataSource={WHITELIST} pagination={false} rowKey="key" />
      </Card>
      <Card size="small" style={{ marginTop: 16, borderColor: '#ffa39e' }} title="被拒绝时用户看到什么（演示帧 · 源 U09 A1.23/A1.24）">
        <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 6 }}>
          演示：问「产量和含水对一下」→ 平台想拼<b>产液表 × 化验表</b>，白名单无此组合——拒帧给三样，不给一堵墙：
        </div>
        <div style={{ fontSize: 13, padding: '3px 0' }}>
          <b>① 为什么拒（一句业务原因）：</b>产液按「井＋日」记、化验按「井＋取样日＋批次」记，两张表没有共同主键语义，硬拼会把化验样错配到产液行——数对了也是错数。
        </div>
        <div style={{ fontSize: 13, padding: '3px 0' }}>
          <b>② 全部合法路径清单：</b>产液表只能连<b>井档案</b>（按井号）或<b>日期维表</b>（按日期）；注水分析请经<b>受效关系</b>实体改道——不走表直连，走对象关系。
        </div>
        <div style={{ fontSize: 13, padding: '3px 0' }}>
          <b>③ 扩容指引（无临时豁免，只有正门）：</b>补登记事实（双键＋时间容差）→ 冲突检测 → Owner 审批（<a href="#/C2">语义修订提案池</a>）→ 白名单扩条目 → 过发布前 CI（<a href="#/C3">C3</a>）。
        </div>
      </Card>
    </div>
  )

  const scriptsTab = (
    <div>
      <Table size="small" columns={wfColumns} dataSource={WORKFLOWS} pagination={false} rowKey="key"
        onRow={w => ({ onDoubleClick: () => setWfOpen(w.key), style: { cursor: 'pointer' } })} />
      <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 8 }}>
        「登记」＝已绑定运行账号、可被调用（正式发布走语义修订提案池）；「草案」＝账号未绑定，不可用。双击行查看登记卡，补登走语义修订提案池。草案转正 = 行为族汇入合同 B1（提案池 → 五道安检 → Owner 签字 → 编译进子图注册表）；《产量下滑归因》的"登记"态即 B1 已汇入状态。
      </div>
      <Modal
        title={wf && <Space>{wf.name}{wf.status === '登记' ? <Tag color="blue">登记</Tag> : <Tag>草案</Tag>}</Space>}
        open={!!wfOpen} onCancel={() => setWfOpen(null)} width={720} footer={null}
      >
        {wf && (
          <>
            <Table size="small" pagination={false}
              columns={[{ title: '项', dataIndex: 'label', width: 140 }, { title: '内容', dataIndex: 'body' }]}
              dataSource={[
                { key: 'trigger', label: '开工条件', body: wf.trigger || NA },
                { key: 'steps', label: '步骤', body: wf.steps || NA },
                { key: 'default', label: '缺参策略', body: wf.defaults || NA },
                { key: 'confirm', label: '人工确认点', body: wf.confirm || NA },
                { key: 'contract', label: '输出合同', body: wf.contract || NA },
                { key: 'src', label: '来源', body: wf.src || NA },
                { key: 'meta', label: '负责人 / 状态 / 版本', body: wf.meta }
              ]} />
            <div style={{ margin: '16px 0 8px', fontWeight: 600 }}>本工作流提出的变动单</div>
            {(() => {
              const mine = TICKETS.filter(t => t.proposer.startsWith(wf.name))
              return mine.length
                ? (
                  <div>
                    {mine.map(t => (
                      <div key={t.id} style={{ fontSize: 12, marginBottom: 4 }}>
                        <b>{t.id}</b> · {t.short}
                      </div>
                    ))}
                    <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 6 }}>
                      <a href="#/A3" style={{ color: '#4a9dff' }}>去数据变动审批看状态与审批</a>
                    </div>
                  </div>
                )
                : <div style={{ fontSize: 12, color: '#8a94a3' }}>暂无关联变动单</div>
            })()}
          </>
        )}
      </Modal>
    </div>
  )

  if (loading) {
    return (
      <Card><Skeleton active paragraph={{ rows: 10 }} /></Card>
    )
  }

  return (
    <div>
      <Card>
        <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 8 }}>
          先提案（<a href="#/C2">语义修订提案池</a>）→ 过五道检查（<a href="#/C3">发布前安检</a>）→ 负责人批准才发布，且可回滚（<a href="#/C2">语义修订提案池</a>）。
        </div>
        <Tabs
          defaultActiveKey="terms"
          items={[
            { key: 'terms', label: `业务术语（${TERMS.length}）`, children: termsTab },
            { key: 'metrics', label: `指标口径（${METRICS.length}）`, children: metricsTab },
            { key: 'objects', label: `对象与关系（${OBJECTS.length}＋${RELATIONS.length}）`, children: objectsTab },
            { key: 'scripts', label: `分析工作流（${WORKFLOWS.length}）`, children: scriptsTab }
          ]}
        />
      </Card>

      {/* 指标口径详情抽屉（原 C4 撤并 · 票 110） */}
      <Drawer
        title={metric && <Space>{metric.name}{metric.status.map((t, i) => <Tag key={i} color={t === '生效中' ? 'green' : 'orange'}>{t}</Tag>)}</Space>}
        open={!!metric} onClose={() => { setMDetail(null); setShowLinkage(false) }} width={640}
      >
        {metric && (
          <>
            <Descriptions size="small" column={1} bordered>
              <Descriptions.Item label="定义 · 公式">{metric.def}</Descriptions.Item>
              <Descriptions.Item label="单位">{mUnit}</Descriptions.Item>
              <Descriptions.Item label="统计粒度">{mGrain}</Descriptions.Item>
              <Descriptions.Item label="修饰词">{modsOf(metric.key)}</Descriptions.Item>
              <Descriptions.Item label="负责人">{metric.owner}</Descriptions.Item>
              <Descriptions.Item label="版本">v3</Descriptions.Item>
              <Descriptions.Item label="数据源">{metric.src}</Descriptions.Item>
              <Descriptions.Item label="争议注记">{metric.dispute}</Descriptions.Item>
            </Descriptions>
            {ambiguous && (
              <Card size="small" style={{ marginTop: 12, background: 'rgba(250,173,20,0.10)', borderColor: '#ffe58f' }}>
                <div>
                  这个词有两个算法（一词两译）：<b>开井日历折算 / 剔除检修（剔检产量）</b>。
                  问「有效产量」时平台会先反问要哪支口径；不选则按默认口径出数并标注。
                </div>
                <Button size="small" style={{ marginTop: 8 }} onClick={() => setClarifyOpen(true)}>预览澄清窗</Button>
              </Card>
            )}
            {ambiguous && (
              <Card size="small" style={{ marginTop: 12 }}
                title={`相关术语登记（${REL_TERMS.length} 条 · 与业务术语账同源）`}>
                <Table size="small" columns={relTermColumns} dataSource={REL_TERMS} pagination={false} rowKey="key" />
              </Card>
            )}
            {showLinkage && (
              <div ref={linkageRef}>
                <Card size="small" style={{ marginTop: 12, background: 'rgba(250,173,20,0.10)', borderColor: '#ffe58f' }}
                  title={<span style={{ color: '#e8b339' }}>改口径前，先看联动提示{helpIcon(<>
                    指标不是独立数字：注采比 β、综合含水率、压力恢复速度与产量由物质平衡互相咬合——<br />
                    修改任一口径，都必须检查联动指标。
                  </>)}</span>}>
                  <div>
                    产量一动，这三个数要一起核对：<b>注采比 β、综合含水率、压力恢复速度</b>——
                    它们和产量由物质平衡互相咬着，改任一口径都必须检查联动指标。本次变更已按流程打包成提案。
                  </div>
                  <Steps size="small" style={{ marginTop: 12 }} items={LINK_FLOW.map(f => ({ title: f.t }))} />
                  <div style={{ fontSize: 12, color: '#874d00', marginTop: 8 }}>
                    提案会自动带上这条联动提示作为影响说明，给审批人看。
                  </div>
                </Card>
              </div>
            )}
          </>
        )}
      </Drawer>

      {/* 一词两译澄清窗（原 C4 澄清交互整体搬迁） */}
      <Modal
        open={clarifyOpen}
        onCancel={() => setClarifyOpen(false)}
        width={720}
        zIndex={1050}
        title="平台反问：你指哪支口径？"
        footer={null}
      >
        <div style={{ marginBottom: 12 }}><b>用户问：「上个月有效产量是多少？」——平台反问：你指哪支口径？</b></div>
        <Row gutter={12}>
          <Col span={12}>
            <Card size="small" title="口径一 · 开井日历折算"
              style={picked === 'A' ? { borderColor: '#4a9dff' } : null}
              extra={picked === 'A' ? <Tag color="blue">已选</Tag> : null}>
              按开井日历折算出数。跨月检修的井（例：N-11 检泵 2026-08-28→09-06）在 8 月、9 月各按开井情况计入——两支口径的分歧点就是「跨月检修切割」。
              <div style={{ marginTop: 8 }}>
                <Button size="small" type={picked === 'A' ? 'primary' : 'default'}
                  onClick={() => setPicked('A')}>按这支口径出数</Button>
              </div>
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small" title="口径二 · 剔除检修"
              style={picked === 'B' ? { borderColor: '#4a9dff' } : null}
              extra={picked === 'B' ? <Tag color="blue">已选</Tag> : null}>
              把检修井剔除后再算净产量——别名「剔检产量」。同一口 N-11，在 9 月的数里不计入检修这段。
              <div style={{ marginTop: 8 }}>
                <Button size="small" type={picked === 'B' ? 'primary' : 'default'}
                  onClick={() => setPicked('B')}>按这支口径出数</Button>
              </div>
            </Card>
          </Col>
        </Row>
        <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Button size="small" type={picked === 'D' ? 'primary' : 'default'} onClick={() => setPicked('D')}>
            不选，按默认口径出数
          </Button>
          <span style={{ fontSize: 12, color: '#8a94a3' }}>
            默认口径暂取「开井日历折算」（两支口径排序第一支）；正式指定默认值走<a href="#/C2">语义修订提案池</a>提案裁决。
          </span>
        </div>
        <div style={{ marginTop: 12 }}>
          {picked ? (
            <Card size="small" style={{ background: 'rgba(255,255,255,0.04)' }}>{CALLOUT_TEXTS[picked]}</Card>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={'（还没选口径——点上面任意一支，或选「不选」看默认标注。）'} />
          )}
        </div>
        <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button type="primary" size="small" onClick={submitChange}>提交口径变更……</Button>
          <span style={{ fontSize: 12, color: '#8a94a3' }}>
            想改口径（含改默认口径）？先看平台给的联动提示——产量一动，好几个数要一起核对。
          </span>
        </div>
      </Modal>
    </div>
  )
}
