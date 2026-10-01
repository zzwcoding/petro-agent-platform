import { useEffect, useState } from 'react'
import { Button, Card, Empty, Input, message, Modal, Select, Skeleton, Space, Table, Tag, Tooltip } from 'antd'
import { ExclamationCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons'
// 票 93：处方段「变更对象」选项与 C1 台账同源（指标/术语/实体名册），禁止本地第二份拷贝
// （票 103：工作流 / Action 两行为族目标下线，处方段不再引用 WORKFLOWS / ACTIONS）
import { ENTITY_GROUPS, METRICS, TERMS, metricLabel } from './C1.jsx'

window.__traces = Object.assign(window.__traces || {}, {
  C2: 'F24 三源提案池+体检 · F25 只提 MR · m16 语义层与指标注册 · m18 评估证据链'
})

const RULES = [
  '不直接改主干——建议先进池子；正式定义谁也不能伸手就改。',
  '只提建议不自己合并——平台只能提，合不合并必须人点批准。',
  '不改自动生成的文件——百科页、索引这类自动产物不手改——要改就改源头定义，自动产物随后自己刷新。',
  '大改动必须人工批——产量口径这类高影响变更，必须 Owner / 治理领导组签字。'
]

// 四条铁律收进标题旁 ! 图标的 Tooltip（原置顶大卡下线）
const RULES_TIP = (
  <div style={{ fontSize: 12, lineHeight: 1.9, maxWidth: 420 }}>
    <b>四条铁律 · 置顶 · 永不违反</b>
    {RULES.map((r, i) => {
      const parts = r.split('——')
      return <div key={i}><b>{i + 1}. {parts[0]}</b>——{parts.slice(1).join('——')}</div>
    })}
  </div>
)
const rulesIcon = (
  <Tooltip title={RULES_TIP} placement="bottomRight">
    <ExclamationCircleOutlined style={{ marginLeft: 4, color: '#faad14', cursor: 'help' }} />
  </Tooltip>
)

const FLOW = [
  { t: '提案进池', d: '三个来源统一收口' },
  { t: '过安检', d: <span><a href="#/C3">发布前安检 · 五道检查</a></span> },
  { t: '负责人批准 🛡', d: '人工点' },
  { t: '生效', d: '版本 +1，正式定义更新' },
  { t: '发现不对？', d: '随时可回滚' }
]

const TARGETS = ['业务术语', '指标口径', '对象与关系']

// 来源 × 去向 准入矩阵：1=收  tri=证据不直接支撑、转人工分诊  0=拒收指路
// 判据：该来源产出的证据形态能否直接支撑此去向的改动
// 票 103：行为族两目标（分析工作流 / Action 合同）下线备查——矩阵收敛 3×3，原 ✗/△ 判据随目标退出
const ADMIT = {
  '考核没通过': { 业务术语: 1, 指标口径: 1, 对象与关系: 'tri' },
  '自动体检发现': { 业务术语: 1, 指标口径: 1, 对象与关系: 1 },
  '用户反馈': { 业务术语: 1, 指标口径: 1, 对象与关系: 1 }
}

// ── 票 102 §七 C2 投影（定义族范围生效 · 票 103 收敛）───────────────────────
// 硬杠（票 102 §八）：元素答得出六站环哪一站；自动/闭环必带机制注记；
// LLM 标角色（归一/起草）、代码标角色（校验/生效/审计/回归）。
// 行为族汇入路径步骤条（汇入合同 B 六步）随目标下线移除（票 103）。

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

// 汇入后验证计划（六站环第⑥站 Verify · 票 102 §六）：生效后自动回归的确定性投影——
// 目标只剩三类定义族（票 103），单一文案
function verifyPlan(row) {
  const ids = [...new Set(((row.evidence || '') + ' ' + (row.rx?.content || '')).match(/E1-\d+/g) || [])]
  const exam = ids.length ? ids.join('、') : '—（未登记）'
  return `验证计划：关联金标考题重跑（E1：${exam}）＋体检复扫（E3）；失败＝台账版本回滚`
}
const VERIFY_TIP = '六站环第⑥站（Verify）· 生效≠结束：生效动作自动触发回归（代码·回归：E1 考题重跑 / E3 体检复扫 / runtime 信号回读），失败即回滚＋新提案——闭环收口。'

// 起草质量小统计（票 102 B3 · 池顶）：确定性演示常量，真实度量落 m3 后接真值
const DRAFT_QUALITY = { compileRate: '87%', humanDiff: '0.14' }

// 命名导出（票 93/100 同源先例）：本池种子数据集中在此，下游同源读取、禁止另抄
// （票 102 §六「改版待重跑」角标随行为族目标下线移除 · 票 103）
export const PROPOSALS = [
  {
    key: 1,
    name: '递减增油口径模板修订',
    title: '修订「递减增油」口径模板：补上"多井受效按劈分系数（Σ=1）分摊"（设定书 §3 指标 10）',
    source: '考核没通过',
    target: '指标口径',
    evidence: '考核用例「递减增油怎么算」判不通过——平台答案漏了劈分规则；两作业区算法本就不一致（事故 7 · 设定书 §A.5）',
    evidenceClass: 'L1',
    confidence: '高（人工算的标准答案比对）', priority: '高', state: 'wait',
    rx: { object: '递减增油', change: '补充口径要点', content: '补上"多井受效按劈分系数（Σ=1）分摊"' }
  },
  {
    key: 2,
    name: '措施有效期标注',
    title: '给「措施有效期」指标卡加"台账缺行"标注（设定书 §3 指标 9）',
    source: '自动体检发现',
    target: '指标口径',
    evidence: '体检四维评分：数据覆盖不足——措施台账的起止日期字段 30% 缺行（设定书 §A.5）',
    evidenceClass: 'L1',
    confidence: '中', priority: '中', state: 'checked',
    rx: { object: '措施有效期', change: '加数据质量标注', content: '标注"台账缺行：起止日期字段 30% 缺行（设定书 §A.5）"' }
  },
  {
    key: 3,
    name: '递减增油联席裁决',
    title: '「递减增油」条目状态"待联席裁决"挂起——提请数据治理领导组联席会议裁决（设定书 §6）',
    source: '自动体检发现',
    target: '业务术语',
    evidence: '术语台账状态栏原文："有效（待联席裁决）"；指标侧注记"一数多源争议之最"（设定书 §3 指标 10 / §6）',
    evidenceClass: 'L2',
    confidence: '高（条款原文）', priority: '高', state: 'checked',
    rx: { object: '递减增油', change: '一词两译消歧', content: '提请数据治理领导组联席会议裁决，指标侧注记"一数多源争议之最"' }
  },
  {
    key: 4,
    name: '有效产量默认口径',
    title: '把「有效产量」默认口径正式定为"开井日历折算"，用户不选时按默认出数并标注（设定书 §3 指标 2）',
    source: '用户反馈',
    target: '指标口径',
    evidence: '运行信号：多候选澄清频繁＋老王反馈"别每次都反问我"；契约本就要求"不选按默认口径出数并标注"',
    evidenceClass: 'L3',
    confidence: '中', priority: '中', state: 'wait',
    rx: { object: '有效产量', change: '指定默认口径', content: '默认口径定为"开井日历折算"，用户不选时按默认出数并标注' }
  },
  {
    key: 5,
    name: '有效产量口径卡发布',
    title: '「有效产量」指标卡补充修饰词说明（开井日历折算 / 剔检）——已走完全流程的样例（设定书 §3 指标 2 / §6）',
    source: '考核没通过',
    target: '指标口径',
    evidence: '考核曾因"一词两译没消歧"答错——修订后同题重跑通过',
    evidenceClass: 'L1',
    confidence: '高', priority: '高', state: 'live',
    rx: { object: '有效产量', change: '补充口径要点', content: '修饰词说明：开井日历折算 / 剔检' }
  },
  {
    key: 6,
    name: '受效关系装配补全',
    title: '为 N-06 装配受效井清单（关系链尾部"受效井清单未装配"）——△ 组合演示：证据不直接支撑，先分诊',
    source: '考核没通过',
    target: '对象与关系',
    evidence: '考核归因题「渤南下滑主因」答错——疑与受效关系未装配有关（A2 关系链尾部原文）；答错只是症状，先人工查明是检索漏还是关系断',
    evidenceClass: 'L4',
    confidence: '中（症状级）', priority: '高', state: 'triage',
    rx: { object: 'N-06', change: '装配缺失关系', content: '装配受效井清单（关系链尾部"受效井清单未装配"）' }
  },
  {
    key: 8,
    name: '渤中孤儿关系补全',
    title: '为渤中区块补全孤儿关系（Join 白名单扩条目·正门五步）——体检发现单直通提案（E3 页样张同源）',
    source: '自动体检发现',
    target: '对象与关系',
    evidence: '四维评分「关系健全不健全」82 分（总评：亚健康）；建议原文：有井没挂上"井—隶属→区块"关系——按区块汇总时会漏井（E3 体检发现单 · 断边清单 · 结构差集）',
    evidenceClass: 'L1',
    confidence: '高（断边清单）', priority: '中', state: 'checked',
    rx: { object: '渤中', change: '扩白名单条目', content: '补全"井—隶属→区块"关系（渤中区块孤儿关系，Join 白名单扩条目走正门五步，映射卡双边同步）' }
  }
]

// 处方段选项与 C1 台账同源（票 92/93 口径）：台账没有的选不到——
// 指标口径＝METRICS 剥常用标记与口径注记后缀的纯名（label 可带台账原名）；
// 业务术语＝TERMS 的 term；对象与关系＝ENTITY_GROUPS 分组展开
// （票 103：行为族两目标下线，不再提供 WORKFLOWS / ACTIONS 选项）
const METRIC_RX_OPTIONS = METRICS.map(m => {
  const pure = metricLabel(m.name)
  return { value: pure, label: pure === m.name ? pure : `${pure}（台账名：${m.name}）` }
})
const TERM_RX_OPTIONS = TERMS.map(t => ({ value: t.term, label: t.term }))
const ENTITY_RX_OPTIONS = ENTITY_GROUPS.map(g => ({
  label: g.label,
  options: g.options.map(v => ({ value: v, label: v }))
}))

const RX_OBJECT_OPTIONS = {
  指标口径: METRIC_RX_OPTIONS,
  业务术语: TERM_RX_OPTIONS,
  对象与关系: ENTITY_RX_OPTIONS
}
// 变更类型按目标枚举（照票 92/93 口径）
const RX_CHANGE_TYPES = {
  指标口径: ['修订定义', '补充口径要点', '指定默认口径', '加数据质量标注'],
  业务术语: ['修订定义', '一词两译消歧', '禁用替代登记'],
  对象与关系: ['装配缺失关系', '扩白名单条目']
}
// 展开区证据形态 Tag 用色（L1 结构差集 → L4 症状，等级越低越要警惕）
const CLASS_COLORS = { L1: 'blue', L2: 'purple', L3: 'orange', L4: 'red' }
const CLASS_GLOSS = {
  L1: '结构差集（要点差集 / 断边清单）——直接成提案',
  L2: '条款引用——可成提案（联席裁决类）',
  L3: '运行信号——可成提案，方向需人工确认',
  L4: '症状（答错 / 抱怨）——必须先分诊'
}

const STATE_META = {
  triage: { label: '待分诊', color: 'purple', btn: '查明转派', primary: false },
  wait: { label: '待审', color: 'orange', btn: '送检', primary: false },
  checked: { label: '已过安检', color: 'blue', btn: '批准', tip: '负责人签字生效', primary: true },
  live: { label: '已生效（v3）', color: 'green', btn: '回滚', primary: false },
  rejected: { label: '已驳回', color: 'red', btn: null, primary: false }
}
const NEXT = { triage: 'wait', wait: 'checked', checked: 'live', live: 'checked' }

// 流转记录：种子按提案当前状态推演（演示时间轴 2026-09），页面操作实时追加；
// 「待分诊」还没进流转路线 → 无记录，展开区不显示该区块
const POOL_TS = {
  1: '2026-09-24T10:12', 2: '2026-09-22T15:40', 3: '2026-09-21T09:05', 4: '2026-09-25T11:36',
  5: '2026-09-18T14:22', 6: '2026-09-26T16:48', 8: '2026-09-23T10:31'
}
const DAY = 86400000
const fmtTs = ms => {
  const d = new Date(ms)
  const p = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}
function stepLog(r) {
  const ts = Date.parse(POOL_TS[r.key] || '2026-09-25T10:00')
  const pool = { time: fmtTs(ts), step: '提案进池', detail: `来源「${r.source}」收口进池 · 证据形态 ${r.evidenceClass}` }
  if (r.state === 'wait') return [pool]
  if (r.state === 'checked') return [pool, { time: fmtTs(ts + DAY), step: '通过安检', detail: '发布前安检五道检查通过（见 C3），待负责人批准' }]
  if (r.state === 'live') return [pool,
    { time: fmtTs(ts + DAY), step: '通过安检', detail: '发布前安检五道检查通过（见 C3）' },
    { time: fmtTs(ts + 2 * DAY), step: '批准生效', detail: '负责人批准 · 台账版本 +1（v3），正式定义更新，派生物自动刷新' }]
  if (r.state === 'rejected') return [pool, { time: fmtTs(ts + DAY), step: '驳回', detail: r.rejectReason || '驳回留痕，可查' }]
  return []
}
const LOG_COLS = [
  { title: '时间', dataIndex: 'time', width: 150 },
  { title: '环节', dataIndex: 'step', width: 110 },
  { title: '说明', dataIndex: 'detail' }
]

function resultCard(name, from, to) {
  if (from === 'triage' && to === 'wait') {
    return `「${name}」已查明并转派：人工确认证据链与去向后转入待审（△ 组合不当场转正，先分诊）。`
  }
  if (to === 'checked' && from === 'wait') {
    return `「${name}」已通过发布前安检（五道检查明细见 C3）——等负责人点批准，平台不会自己合并（铁律 2）。`
  }
  if (to === 'live') {
    return `「${name}」已生效：版本 +1，正式定义更新；自动生成的百科页、索引等派生物随后自动刷新（不手改 · 铁律 3）。`
  }
  return `「${name}」已回滚：版本回退，正式定义与各处显示恢复一致。`
}

export default function C2Proposals() {
  const [loading, setLoading] = useState(true)
  const [src, setSrc] = useState('全部来源')
  const [rows, setRows] = useState(PROPOSALS)
  const [logs, setLogs] = useState({})
  const logOf = r => logs[r.key] || stepLog(r)
  const [editKey, setEditKey] = useState(null)
  const [editRx, setEditRx] = useState({ object: '', change: '', content: '' })
  const [rejectKey, setRejectKey] = useState(null)
  const [rejectReason, setRejectReason] = useState('')

  const columns = [
    // 提案列只留短名（name 本身短，单行不截断）——全文进展开区
    { title: '提案', dataIndex: 'name', width: 170,
      render: v => <span style={{ whiteSpace: 'nowrap' }}>{v}</span> },
    { title: (<span>来源{helpIcon(<>
      <b>四个来源 · 各自怎么填写</b><br />
      · 出题：按槽位写金标（指标 / 术语 / 数值容差 / 判分要点）<br />
      · 考核：逐槽比对，产出失败槽位与要点差集<br />
      · 体检：结构证据（断边清单 / 缺字段率）<br />
      · 反馈：自由文本轻分类，归一成诊断卡
    </>)}</span>), dataIndex: 'source', width: 112 },
    {
      title: (<span>目标{helpIcon(<>
        <b>来源 × 去向 准入矩阵</b>（进池闸校验）<br />
        ✓ 收　△ 转分诊　✗ 拒收指路<br />
        考核没通过：术语✓ 指标✓ 对象关系△<br />
        自动体检发现：术语✓ 指标✓ 对象关系✓<br />
        用户反馈：全部 ✓<br />
        判据：该来源产出的证据形态能否直接支撑此去向的改动。<br />
        （原五类目标中的分析工作流 / Action 合同已下线备查——票 103，矩阵收敛 3×3）
      </>)}</span>),
      dataIndex: 'target', width: 104 },
    {
      title: (<span>证据形态{helpIcon(<>
        <b>证据形态四级</b>（判据：证据形态能否直接支撑去向的改动）<br />
        · <b>L1</b> 结构差集（要点差集 / 断边清单）——直接成提案<br />
        · <b>L2</b> 条款引用——可成提案（联席裁决类）<br />
        · <b>L3</b> 运行信号——可成提案，方向需人工确认<br />
        · <b>L4</b> 症状（答错 / 抱怨）——必须先分诊
      </>)}</span>),
      dataIndex: 'evidenceClass', width: 80,
      render: v => <span style={{ fontSize: 12, color: '#8a94a3' }}>{v}</span>
    },
    {
      title: (<span>可信度{helpIcon(<>
        <b>置信度档位</b>（池规则透明）<br />
        · 金标 fail 档：<b>0.95</b>（考核标准答案比对不过）<br />
        · 线上未命中：按簇规模升档，<b>封顶 0.70</b><br />
        档位有上限，机器不自封"确凿"。
      </>)}</span>),
      dataIndex: 'confidence', width: 180
    },
    {
      title: (<span>优先级{helpIcon(<>
        <b>优先级算式</b><br />
        分数 = 影响对象数 × 2 + 频次 × 0.5 + owner 缺位 + 1<br />
        ≥ 6 分 → P0<br />
        示例：sg-0003 检修产量 ＝ 对象 2×2 ＋ 频次 40×0.5 ＋ 0 ＝ <b>24 分 → P0</b>
      </>)}</span>),
      dataIndex: 'priority', width: 86
    },
    {
      title: (<span>状态{helpIcon(<>
        <b>一张建议的流转路线</b><br />
        {FLOW.map((f, i) => <span key={i}>{i + 1}．{f.t}——{f.d}<br /></span>)}
        △ 组合（证据不直接支撑去向）先入「待分诊」，人工查明转派后才进本路线。<br />
        待审 / 已过安检途中可被「改写」（改写结构化处方槽位，诊断段随卡留痕）或「驳回」（附理由留痕）。<br />
        汇入口径：批准后走汇入合同（定义族）——台账行版本 +1；对象与关系附加 Join 白名单扩条目·正门五步。<br />
        （行为族汇入合同随目标下线备查 · 票 103）
      </>)}</span>),
      dataIndex: 'state', width: 128,
      render: v => STATE_META[v].label
    },
    {
      title: '操作', width: 190,
      render: (_, r) => {
        const meta = STATE_META[r.state]
        if (r.state === 'rejected') return <span style={{ fontSize: 12, color: '#8a94a3' }}>—（留痕可查）</span>
        const editable = r.state === 'wait' || r.state === 'checked'
        const actBtn = (
          <Button size="small" type={meta.primary ? 'primary' : 'default'}
            onClick={e => { e.stopPropagation(); act(r.key) }}>{meta.btn}</Button>
        )
        return (
          <Space size={4}>
            {editable && <Button size="small" onClick={e => { e.stopPropagation(); setEditKey(r.key); setEditRx({ ...r.rx }) }}>改写</Button>}
            {editable && <Button size="small" danger onClick={e => { e.stopPropagation(); setRejectKey(r.key); setRejectReason('') }}>驳回</Button>}
            {meta.tip ? <Tooltip title={meta.tip}>{actBtn}</Tooltip> : actBtn}
          </Space>
        )
      }
    }
  ]

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 600)
    return () => clearTimeout(t)
  }, [])

  function pushLog(key, row, rec) {
    setLogs(prev => ({ ...prev, [key]: [...(prev[key] || stepLog(row)), rec] }))
  }

  function act(key) {
    const row = rows.find(r => r.key === key)
    if (!row) return
    const from = row.state
    const to = NEXT[from]
    const step = { triage: '查明转派', wait: '通过安检', checked: '批准生效', live: '回滚' }[from]
    setRows(prev => prev.map(r => (r.key === key ? { ...r, state: to } : r)))
    pushLog(key, row, { time: fmtTs(Date.now()), step, detail: resultCard(row.name, from, to) })
  }

  function saveEdit() {
    const rx = { object: editRx.object.trim(), change: editRx.change.trim(), content: editRx.content.trim() }
    const missing = [
      !rx.object && '变更对象',
      !rx.change && '变更类型',
      !rx.content && '变更内容'
    ].filter(Boolean)
    if (missing.length) {
      message.warning(`处方段缺项：${missing.join('、')}——请补全后再保存`)
      return
    }
    const row = rows.find(r => r.key === editKey)
    const title = `【${row.target}·${rx.change}】${rx.object}：${rx.content}`
    setRows(prev => prev.map(r => (r.key === editKey ? { ...r, rx, title } : r)))
    pushLog(editKey, row, { time: fmtTs(Date.now()), step: '改写', detail: '改写处方段（结构化槽位，诊断段随卡留痕）' })
    setEditKey(null)
  }

  function submitReject() {
    const reason = rejectReason.trim() || '理由未填写'
    const row = rows.find(r => r.key === rejectKey)
    setRows(prev => prev.map(r => (r.key === rejectKey ? { ...r, state: 'rejected', rejectReason: reason } : r)))
    pushLog(rejectKey, row, { time: fmtTs(Date.now()), step: '驳回', detail: `${reason}——不进安检不生效，诊断留痕可查（也许金标本年该改的是考卷）。` })
    setRejectKey(null)
    setRejectReason('')
  }

  const pills = ['全部来源', '考核没通过', '自动体检发现', '用户反馈']
  const [tgt, setTgt] = useState('全部目标')
  const admissible = t => src === '全部来源' || ADMIT[src][t] !== 0
  const filtered = rows.filter(r =>
    (src === '全部来源' || r.source === src) && (tgt === '全部目标' || r.target === tgt))

  function pickSource(p) {
    setSrc(p)
    if (p !== '全部来源' && tgt !== '全部目标' && !ADMIT[p][tgt]) setTgt('全部目标')
  }

  const pillStyle = (active, disabled) => disabled
    ? { border: '1px solid rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.22)', cursor: 'not-allowed' }
    : active
      ? { background: '#1677ff', color: '#fff' }
      : { border: '1px solid rgba(255,255,255,0.2)', color: 'rgba(255,255,255,0.55)' }

  if (loading) {
    return (
      <div>
        <Card><Skeleton active paragraph={{ rows: 3 }} /></Card>
        <Card style={{ marginTop: 12 }}><Skeleton active paragraph={{ rows: 8 }} /></Card>
      </div>
    )
  }

  return (
    <div>
      <Card size="small"
        title={<span>提案池（三个来源 × 语义资产统一收口）{helpIcon(<>
          <b>晋升闸（什么才配进池）</b><br />
          · 独立会话数 ≥ 2，或<br />
          · 簇频次过阈值<br />
          孤例不进池——单问一句答不上不开提案，防噪声淹没真问题。
        </>)}{rulesIcon}</span>}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 12, color: '#8a94a3' }}>起草质量</span>
          <Tag color="gold" style={{ marginRight: 0 }}>演示数据</Tag>
          <span style={{ fontSize: 12 }}>
            近 30 天可编译率 <b>{DRAFT_QUALITY.compileRate}</b>
            {helpIcon(<>
              <b>可编译率（起草器量化）</b><br />
              ＝CI 一次通过率（L1–L5 跑批过闸率）——草案过五级语义 CI 的一次通过率（代码·校验，CI 报告即打分报表，错误清单即改进清单）。<br />
              度量的是 AI 起草器的产出质量（AI 角色＝起草，产结构化 diff 草案）。<br />
              真实度量落审计库（分＋版本＋输入快照）；一次通过率退化自动成运行信号进本池报警。当前为演示常量，接真值后替换。
            </>)}
          </span>
          <span style={{ fontSize: 12 }}>
            人改幅度（diff-of-diff）<b>{DRAFT_QUALITY.humanDiff}</b>
            {helpIcon(<>
              <b>人改幅度（起草器量化）</b><br />
              ＝人确诊改写时相对机器草案的修改量（diff-of-diff，诊断段只读随卡留痕）——改得少＝初诊可信，改得多＝起草模板该修。<br />
              真实度量落审计库，退化自动成运行信号报警。当前为演示常量，接真值后替换。
            </>)}
          </span>
          <span style={{ fontSize: 12, color: '#8a94a3' }}>
            ——六站环第④站（处方）起草产出的质量度量
          </span>
        </div>
        <div style={{ marginBottom: 12 }}>
          <span style={{ fontSize: 12, color: '#8a94a3', marginRight: 6 }}>来源</span>
          {pills.map(p => (
            <Tag.CheckableTag key={p} checked={src === p} style={pillStyle(src === p)}
              onClick={() => pickSource(p)}>{p}</Tag.CheckableTag>
          ))}
          <span style={{ fontSize: 12, color: '#8a94a3', margin: '0 6px 0 16px' }}>目标</span>
          {['全部目标', ...TARGETS].map(t => {
            const disabled = t !== '全部目标' && !admissible(t)
            return (
              <Tag.CheckableTag key={t} checked={tgt === t} style={pillStyle(tgt === t, disabled)}
                onClick={() => !disabled && setTgt(t)}>{t}</Tag.CheckableTag>
            )
          })}
          <span style={{ fontSize: 12, color: '#8a94a3', marginLeft: 8 }}>
            筛选结果 {filtered.length} / {rows.length} 条
          </span>
        </div>
        <Table size="small" columns={columns} dataSource={filtered} pagination={false} rowKey="key"
          expandable={{
            expandRowByClick: true,
            expandedRowRender: r => {
              const section = { background: 'rgba(255,255,255,0.04)', borderRadius: 6, padding: '12px 14px' }
              const sectionTitle = { fontSize: 12, fontWeight: 'bold', color: '#8a94a3', marginBottom: 6 }
              const log = logOf(r).map((x, i) => ({ ...x, key: i }))
              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <div style={section}>
                    <div style={sectionTitle}>提案详情</div>
                    <div style={{ fontSize: 13, fontWeight: 'bold', color: 'rgba(255,255,255,0.88)' }}>{r.name}</div>
                    <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.75)', marginTop: 4 }}>{r.title}</div>
                    {r.state === 'rejected' && (
                      <div style={{ fontSize: 12, color: '#ff4d4f', marginTop: 6 }}>驳回理由：{r.rejectReason}</div>
                    )}
                  </div>
                  <div style={section}>
                    <div style={sectionTitle}>证据</div>
                    <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.75)' }}>
                      <Tag color={CLASS_COLORS[r.evidenceClass]} style={{ marginRight: 8 }}>{r.evidenceClass}</Tag>{r.evidence}
                    </div>
                    <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 6 }}>
                      证据形态说明：{r.evidenceClass}——{CLASS_GLOSS[r.evidenceClass] || '—'}
                    </div>
                  </div>
                  {log.length > 0 && (
                    <div style={section}>
                      <div style={sectionTitle}>流转记录{helpIcon(<>
                        <b>流转记录怎么来</b><br />
                        · 按该提案当前状态生成的留痕（演示数据按状态推演）<br />
                        · 点行上操作按钮（查明转派 / 送检 / 批准 / 回滚 / 改写 / 驳回）会追加记录<br />
                        · 「待分诊」的提案还没进流转路线——不显示本区块
                      </>)}</div>
                      <Table size="small" columns={LOG_COLS} dataSource={log} pagination={false} />
                    </div>
                  )}
                </div>
              )
            }
          }}
          locale={{ emptyText: <Empty description="该来源暂无提案" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }} />
      </Card>

      <Modal title="改写提案 · 机器初诊 → 人确诊" open={!!editKey}
        onCancel={() => setEditKey(null)} footer={null} width={640}>
        {editKey != null && (() => {
          const row = rows.find(r => r.key === editKey)
          if (!row) return null
          return (
            <>
              <Card size="small" style={{ background: 'rgba(255,255,255,0.04)' }}
                title={<span style={{ fontSize: 12, color: '#8a94a3' }}>诊断段（机器诊断，不可改写）</span>}>
                <div style={{ fontSize: 13, lineHeight: 2 }}>
                  <div><b>来源：</b>{row.source}
                    <b style={{ marginLeft: 12 }}>目标：</b>{row.target}
                    <b style={{ marginLeft: 12 }}>证据形态：</b>{row.evidenceClass}</div>
                  <div><b>证据：</b>{row.evidence}</div>
                </div>
              </Card>
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 4 }}>
                  处方段（可编辑 · 结构化槽位）
                  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>机器开初诊，人确诊：批准后走汇入合同（定义族）＝台账行版本 +1；对象与关系附加 Join 白名单扩条目·正门五步。（行为族汇入合同随目标下线备查 · 票 103）原始诊断随卡留痕。</div>}>
                    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
                  </Tooltip>
                </div>
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 4 }}>
                    变更对象
                    <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>选项与 C1 台账同源，台账没有的选不到。</div>}>
                      <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
                    </Tooltip>
                  </div>
                  <Select size="small" style={{ width: '100%' }} value={editRx.object}
                    options={RX_OBJECT_OPTIONS[row.target]}
                    onChange={v => setEditRx(s => ({ ...s, object: v }))} />
                </div>
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 4 }}>
                    变更类型
                    <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>选项与 C1 台账同源，台账没有的选不到；枚举按目标资产分类。</div>}>
                      <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
                    </Tooltip>
                  </div>
                  <Select size="small" style={{ width: '100%' }} value={editRx.change}
                    options={(RX_CHANGE_TYPES[row.target] || []).map(o => ({ value: o, label: o }))}
                    onChange={v => setEditRx(s => ({ ...s, change: v }))} />
                </div>
                <div>
                  <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 4 }}>变更内容</div>
                  <Input.TextArea size="small" rows={3} value={editRx.content}
                    onChange={e => setEditRx(s => ({ ...s, content: e.target.value }))} />
                </div>
                <div style={{ marginTop: 10, fontSize: 12, color: '#8a94a3' }}>
                  {verifyPlan(row)}
                  {helpIcon(VERIFY_TIP)}
                </div>
                <Button type="primary" style={{ marginTop: 12 }} onClick={saveEdit}>保存改写</Button>
              </div>
            </>
          )
        })()}
      </Modal>

      <Modal title="驳回（须写理由）" open={!!rejectKey}
        onCancel={() => setRejectKey(null)} footer={null} width={520}>
        <Input.TextArea size="small" rows={3} value={rejectReason}
          placeholder="例如：该要点属作业区算法差异，不该进统一口径；或金标本身过时，该改考卷"
          onChange={e => setRejectReason(e.target.value)} />
        <Button type="primary" danger style={{ marginTop: 12 }} onClick={submitReject}>提交驳回</Button>
      </Modal>
    </div>
  )
}
