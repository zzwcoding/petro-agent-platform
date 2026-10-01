import { useState } from 'react'
import {
  Alert, Button, Card, Empty, Input, Modal, Popover, Select, Space, Table, Tabs, Tag, Tooltip
} from 'antd'
import {
  ArrowLeftOutlined, EyeOutlined, FileTextOutlined, QuestionCircleOutlined, RollbackOutlined
} from '@ant-design/icons'

window.__traces = Object.assign(window.__traces || {}, {
  B4: 'F50 百科页 · F51 台账挂接 · F52 版本回滚·论断回链 · m6 卡'
})

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

// —— 元数据条「关联对象」展开联动（词条链接点击 → 展开元数据条并滚动到位）——
let __metaExpand = () => {}

// —— 百科页目录（每个开了百科开关的库自动生成首页目录；内容全部取自页面既有事实）——
const PAGES = [
  {
    key: 'w1',
    title: '《N-02 井完井报告》',
    lib: '完井报告库',
    src: '《N-02 井完井报告（英文 · 200 页）》',
    slug: 'wiki-n02-completion',
    updated: '2026-09-20'
  },
  {
    key: 'w2',
    title: '《渤中28-1 区块月度生产月报》',
    lib: '生产月报库',
    src: '《渤中28-1 区块月度生产月报（2026-08）》',
    slug: 'wiki-bz281-monthly-202608',
    updated: '2026-09'
  }
]
const LIB_COLORS = { 完井报告库: 'blue', 生产月报库: 'purple' }

// 词条自动链接：点页内词条 → 展开元数据条「关联对象」行并滚动到位
function WellLink({ id }) {
  return <a href="#meta" onClick={e => { e.preventDefault(); __metaExpand(id) }}>{id}</a>
}

// —— F52 论断回链：论断 → 证据切片（chunk id 与切片管理片段台账同域；形状照抄切片管理端点 1/2）——
const EVIDENCE = {
  f1: { report: '《N-02 井完井报告（英文 · 200 页）》', section: '章节 01 井基本情况 ＞ 1.2 投产信息', type: '原文块', text: 'N-02（渤中28-1-N2）于 2019-06-15 投产。' },
  f2: { report: '《N-02 井完井报告（英文 · 200 页）》', section: '章节 03 图件 ＞ 图 3-7', type: '图片说明块', text: '图 3-7 岩性柱状图：按深度展示该井段岩性分布（图内无文字，本说明为系统自动生成）。' },
  f3: { report: '《渤中28-1 区块月度生产月报（2026-08）》', section: '章节 02 检修与停产 ＞ 2.1 检泵', type: '原文块', text: 'N-11 井检泵作业，起止 2026-08-28 → 2026-09-06（跨月），影响产量约 210 吨；该检修为事后补录，批次号 20260911-T3。' },
  f4: { report: '《渤中28-1 区块月度生产月报（2026-08）》', section: '章节 04 计量与折算 ＞ 4.2 单位换算', type: '原文块', text: '原油密度按区块——渤南 0.86 / 渤中 0.89 / 渤西 0.91（t/m³）。本月 N-11 一行日产油误录单位"方"（12.40 方），已按密度折算为约 11.04 吨。' }
}

const CLAIMS = {
  'w1-c1': { ids: ['f1'] },
  'w1-c2': { ids: ['f2'] },
  'w1-c3': { ids: ['f1'] },
  'w1-c4': { ids: ['f4'] },
  'w2-c1': { ids: ['f3'] },
  'w2-c2': { ids: ['f4'] },
  'w2-c3': { ids: ['f3'] }
}

function EvidenceMark({ claim }) {
  const [open, setOpen] = useState(false)
  const ids = CLAIMS[claim]?.ids || []
  const chunks = ids.map(id => ({ id, ...EVIDENCE[id] })).filter(c => c.report)
  if (!chunks.length) return null // 锚失效/无锚论断不渲染——fail-closed，不伪造回链
  return (
    <>
      <Tooltip title={`论断可回链证据：来源切片 ${ids.join('、')}——点击定位`}>
        <a className="ev-mark" href="#/B2" onClick={e => { e.preventDefault(); setOpen(true) }}
          style={{
            fontSize: 12, marginLeft: 4, padding: '0 5px', borderRadius: 3,
            border: '1px solid #91caff', color: '#4a9dff', lineHeight: '16px',
            display: 'inline-block', verticalAlign: '1px'
          }}>证</a>
      </Tooltip>
      <Modal
        title="证据来源（切片回链）" open={open} onCancel={() => setOpen(false)} width={640}
        footer={[
          <Button key="close" onClick={() => setOpen(false)}>关闭</Button>,
          <Button key="go" type="primary" onClick={() => { setOpen(false); window.location.hash = '/B2' }}>
            在切片管理中定位
          </Button>
        ]}
      >
        <div style={{ color: '#8a94a3', fontSize: 12, marginBottom: 12 }}>
          本页论断由入库切片重写生成，点击「证」可回链生成来源；下列切片可在「切片管理」中逐条核对。
        </div>
        {chunks.map(c => (
          <div key={c.id} style={{ marginBottom: 12 }}>
            <Space size={6}>
              <Tag color="blue" style={{ marginInlineEnd: 0 }}>{c.id}</Tag>
              <Tag style={{ marginInlineEnd: 0 }}>{c.type}</Tag>
              <span style={{ fontSize: 13 }}>{c.report}</span>
            </Space>
            <div style={{ fontSize: 12, color: '#8a94a3', margin: '4px 0' }}>{c.section}</div>
            <div style={{ fontSize: 13, background: 'rgba(74,157,255,0.06)', borderLeft: '3px solid #4a9dff', padding: '6px 10px' }}>{c.text}</div>
          </div>
        ))}
      </Modal>
    </>
  )
}

// —— F51 台账挂接：识别词表＝C1 台账名册＋别名，台账没有的词不挂（防误链）；卡内容＝C1 台账同源投影 ——
const GLOSSARY = {
  综合含水率: { kind: '指标口径', ref: '指标台账 #5', def: 'Q_w ÷（Q_o＋Q_w）× 100%', status: '生效中', statusColor: 'green', owner: '开发室', extra: '统计粒度：月 · 单位 %', src: '指标台账（数据源：A.2 日产计量＋A.6 化验）' },
  递减增油: { kind: '业务术语', ref: '术语台账 #7', def: '见指标 10（含口径争议注记）', status: '有效（待联席裁决）', statusColor: 'orange', owner: '采油工艺所', extra: '有效期至 2027-03-31', src: '业务术语台账（设定书 §6）' },
  剔检产量: { kind: '业务术语', ref: '术语台账 #2', def: '剔除检修井口径', status: '有效', statusColor: 'green', owner: '开发室', extra: '有效期至 2027-12-31', src: '业务术语台账（设定书 §6）' }
}

function GlossChip({ word }) {
  const g = GLOSSARY[word]
  if (!g) return word // 词表（台账名册＋别名）没有的词不挂——台账闸防误链
  return (
    <Popover
      trigger="click" placement="top"
      title={<span>词条口径卡 · {word}</span>}
      content={
        <div style={{ width: 320 }}>
          <Space size={6} style={{ marginBottom: 8 }}>
            <Tag color="purple" style={{ marginInlineEnd: 0 }}>{g.kind}</Tag>
            <Tag color={g.statusColor} style={{ marginInlineEnd: 0 }}>{g.status}</Tag>
          </Space>
          <div style={{ fontSize: 13, marginBottom: 6 }}><b>定义：</b>{g.def}</div>
          <div style={{ fontSize: 12, color: '#8a94a3', lineHeight: 1.8 }}>
            负责人：{g.owner} · {g.extra}<br />来源：{g.src}（{g.ref}）
          </div>
        </div>
      }
    >
      <a className="g-chip" onClick={e => e.preventDefault()}
        style={{ color: '#4a9dff', borderBottom: '1px dashed #4a9dff', cursor: 'pointer' }}>{word}</a>
    </Popover>
  )
}

// —— 自由 markdown 正文渲染（合同 [[…]] 标记族原样内嵌解析：well/route/claim/term/flag；前端零拼装业务文案）——
function renderInline(text, keyBase) {
  const nodes = []
  const re = /(\[\[[^\]]+\]\]|\*\*[^*]+\*\*)/g
  let last = 0, m, i = 0
  while ((m = re.exec(text))) {
    if (m.index > last) nodes.push(text.slice(last, m.index))
    const tok = m[0]
    if (tok.startsWith('**')) {
      nodes.push(<b key={`${keyBase}-${i}`}>{tok.slice(2, -2)}</b>)
    } else {
      const inner = tok.slice(2, -2)
      const ci = inner.indexOf(':')
      const type = ci < 0 ? '' : inner.slice(0, ci)
      const arg = ci < 0 ? inner : inner.slice(ci + 1)
      if (type === 'well') nodes.push(<WellLink key={`${keyBase}-${i}`} id={arg} />)
      else if (type === 'route') {
        const [pg, ...label] = arg.split('|')
        nodes.push(<a key={`${keyBase}-${i}`} href={`#/${pg}`}>{label.join('|')}</a>)
      }
      else if (type === 'claim') nodes.push(<EvidenceMark key={`${keyBase}-${i}`} claim={arg} />)
      else if (type === 'term') nodes.push(<GlossChip key={`${keyBase}-${i}`} word={arg} />)
      else if (type === 'flag') nodes.push(
        <span key={`${keyBase}-${i}`} className="wiki-flag"
          style={{
            fontSize: 12, marginLeft: 4, padding: '1px 6px', borderRadius: 3,
            background: '#fff7e6', border: '1px solid #ffd591', color: '#d46b08',
            display: 'inline-block', verticalAlign: '1px'
          }}>⚠ {arg}</span>
      )
      else nodes.push(tok)
    }
    last = m.index + tok.length
    i++
  }
  if (last < text.length) nodes.push(text.slice(last))
  return nodes
}

const TD_STYLE = { border: '1px solid #e0e4e8', padding: '6px 12px', fontSize: 13 }
const TH_STYLE = { ...TD_STYLE, background: '#f7f8fa', fontWeight: 600, textAlign: 'left', whiteSpace: 'nowrap' }

function Md({ text }) {
  const lines = (text || '').trim().split('\n')
  const out = []
  let i = 0, key = 0
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) { i++; continue }
    if (line.startsWith('### ')) {
      out.push(<h4 key={key++} style={{ fontSize: 13, fontWeight: 600, margin: '12px 0 6px' }}>{renderInline(line.slice(4), `h${key}`)}</h4>)
      i++; continue
    }
    if (line.startsWith('## ')) {
      out.push(<h3 key={key++} style={{ fontSize: 14, fontWeight: 600, margin: '18px 0 10px', paddingBottom: 6, borderBottom: '1px solid #f0f0f0' }}>{renderInline(line.slice(3), `h${key}`)}</h3>)
      i++; continue
    }
    if (line.startsWith('|')) {
      const tbl = []
      while (i < lines.length && lines[i].startsWith('|')) { tbl.push(lines[i]); i++ }
      const rows = tbl.filter(l => !/^\|\s*[-:]/.test(l)).map(l => l.split('|').slice(1, -1).map(c => c.trim()))
      if (rows.length) {
        const [head, ...body] = rows
        out.push(
          <table key={key++} style={{ borderCollapse: 'collapse', margin: '4px 0 16px' }}>
            <thead><tr>{head.map((c, j) => <th key={j} style={TH_STYLE}>{renderInline(c, `th${key}-${j}`)}</th>)}</tr></thead>
            <tbody>{body.map((r, ri) => (
              <tr key={ri}>{r.map((c, ci) => <td key={ci} style={TD_STYLE}>{renderInline(c, `td${key}-${ri}-${ci}`)}</td>)}</tr>
            ))}</tbody>
          </table>
        )
      }
      continue
    }
    if (line.startsWith('- ')) {
      const items = []
      while (i < lines.length && lines[i].startsWith('- ')) { items.push(lines[i].slice(2)); i++ }
      out.push(<ul key={key++} style={{ margin: '4px 0 14px', paddingLeft: 20, fontSize: 13, lineHeight: 1.9 }}>{items.map((t, j) => <li key={j}>{renderInline(t, `li${key}-${j}`)}</li>)}</ul>)
      continue
    }
    const para = [line]
    i++
    while (i < lines.length && lines[i].trim() && !/^(#{2,3} |\||- )/.test(lines[i])) { para.push(lines[i].trim()); i++ }
    out.push(<p key={key++} style={{ margin: '0 0 12px', fontSize: 13, lineHeight: 1.9 }}>{renderInline(para.join(''), `p${key}`)}</p>)
  }
  if (!out.length) return <Empty description="本版无正文内容。" />
  return <div className="wiki-md">{out}</div>
}

// —— 关联对象（井对象卡收进元数据条展开区，链 A2 / B5；逐字段 §A.1）——
const RELATED = {
  w1: {
    label: '井 N-02',
    detail: '井名 渤中28-1-N2 · 井别 采油（EW）· 投产 2019-06-15 · 平台 CEP-A · 区块 渤南 · 状态 生产中 · 关联注水井 N-06（受效关系）'
  },
  w2: {
    label: '井 N-11',
    detail: '井别 采油（EW）· 投产 2020-02-20 · 平台 CEP-B · 区块 渤中 · 状态 停产（2026-08-30 起检泵）'
  }
}

// —— 各版本正文快照（自由 markdown；[[]] 标记族由服务端生成时固化、照版本走）——
const W1_V1 = `## 概述

本报告为 [[well:N-02]] 井（[[well:渤中28-1]]-N2）完井报告：井位于渤南区块 CEP-A 平台，井别采油，2019-06-15 投产，状态生产中[[claim:w1-c1]]。

## 完井段与投产信息

正文含完井段与投产信息；插图含岩性柱状图等[[claim:w1-c2]]，插图说明由系统自动生成回读。

## 基本参数

| 井号 | 井名 | 井别 | 投产日期 | 平台 | 区块 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| N-02 | 渤中28-1-N2 | 采油（EW） | 2019-06-15[[claim:w1-c3]] | CEP-A | 渤南 | 生产中 |`

const W1_V2 = `${W1_V1}

## 生产样本日摘录

摘自报告附表并已中文化；吨↔方换算＝质量÷密度，原油密度按区块：渤南 0.86 / 渤中 0.89 / 渤西 0.91（t/m³）。

| 井号 | 日期 | 日产油（吨） | 日产液（方） | 备注 |
| --- | --- | --- | --- | --- |
| N-02 | 2026-09-14 | 48.60 | 165.30 | 样本日 |
| N-11 | 2026-09-14 | 12.40（误录"方"，折算约 11.04 吨） | 96.00 | 油量单位误录，按渤中密度 0.89 折算[[claim:w1-c4]] |`

const W1_V3 = W1_V2
  .replace('井位于渤南区块 CEP-A 平台，井别采油', '井位于渤南区块 CEP-B 平台[[flag:与井档案不符，待核对]]，井别采油')
  .replace('| 2019-06-15[[claim:w1-c3]] | CEP-A |', '| 2019-06-15[[claim:w1-c3]] | CEP-B[[flag:与井档案不符，待核对]] |')

const W2_V1 = `## 概述

本报告为渤中28-1 区块 2026-08 月度生产月报：本月 [[well:N-11]] 井检泵停产（2026-08-28 起，跨月至 09-06），影响产量约 210 吨[[claim:w2-c1]]。

## 检修情况

- N-11 井检泵：2026-08-28 → 2026-09-06（跨月），影响产量约 210 吨[[claim:w2-c3]]；
- 该检修为事后补录，批次号 20260911-T3。

## 计量与折算

N-11 一行日产油误录单位"方"（报出 12.40 方），按渤中区块密度 0.89 t/m³ 折算为约 11.04 吨——吨↔方换算＝质量÷密度[[claim:w2-c2]]。

## 涉及指标与术语

本报告涉及指标 [[term:综合含水率]]、[[term:递减增油]]，涉及术语 [[term:剔检产量]]。`

// —— 版本历史（只追加：每次重建/回滚落一版；diff 已撤，三件套＝列表 / 查看任一版全文 / 回滚）——
const INIT_VERSIONS = {
  w1: [
    { v: 1, date: '2026-09-15', source: '自动重建', desc: '首次生成（报告入库自动建页）', operator: '系统（入库管线）', task: 'task-1042', bad: false, content: W1_V1 },
    { v: 2, date: '2026-09-18', source: '自动重建', desc: '报告重新解析后自动重建（新增"生产样本日摘录"）', operator: '系统（入库管线）', task: 'task-1046', bad: false, content: W1_V2 },
    { v: 3, date: '2026-09-20', source: '自动重建', desc: '自动重建（链错了井）', operator: '系统（入库管线）', task: 'task-1047', bad: true, content: W1_V3 }
  ],
  w2: [
    { v: 1, date: '2026-09', source: '自动重建', desc: '首次生成（报告入库自动建页）', operator: '系统（入库管线）', task: 'task-1051', bad: false, content: W2_V1 }
  ]
}

const SOURCE_COLORS = { 自动重建: 'default', 智能体: 'purple', 人工: 'blue', 回滚: 'orange' }

const VER_HELP = '每次重建都落一个版本：点「查看全文」看任一版的全文快照；发现改错点「回滚」恢复到目标版，回滚本身也记成一次新提交、可再滚回。'
const META_HELP = '页面由报告全文自动重写成一篇自由 Markdown 文档（模板约束在生成提示词里，不设固定节）；slug 稳定——报告重新解析后沿用原页原地更新，不会另建新页、旧链接不断。'
const TASK_HELP = '产生该版本的经由单据：自动重建＝入库/重跑任务号；回滚版无单号记 —。'
const OPERATOR_HELP = '该版本的操作者：自动重建记系统（入库管线），人工/回滚记操作人。'

export default function B4() {
  const [tab, setTab] = useState('catalog') // catalog | read | versions
  const [pageKey, setPageKey] = useState('w1')
  const [vers, setVers] = useState(INIT_VERSIONS) // 各页版本序列（只追加）
  const [viewVer, setViewVer] = useState(null) // 正在查看的历史版（null＝当前版）
  const [metaOpen, setMetaOpen] = useState(false)
  const [banner, setBanner] = useState(null)
  const [libF, setLibF] = useState('all')
  const [kw, setKw] = useState('')
  const [selRow, setSelRow] = useState(null)

  __metaExpand = () => { setMetaOpen(true); requestAnimationFrame(() => document.getElementById('meta-bar')?.scrollIntoView({ behavior: 'smooth', block: 'start' })) }

  const page = PAGES.find(p => p.key === pageKey)
  const list = vers[pageKey]
  const cur = list[list.length - 1]
  const viewing = viewVer ? list.find(x => x.v === viewVer) : null

  function openPage(key) {
    setPageKey(key)
    setBanner(null)
    setViewVer(null)
    setTab('read')
  }

  function viewVersion(v) {
    setViewVer(v)
    setTab('read')
  }

  function rollback() {
    const target = list.find(x => x.v === cur.v - 1)
    Modal.confirm({
      title: `确认回滚到 v${target.v}？`,
      content: `当前版内容将恢复为 v${target.v} 快照，并记为来源「回滚」的新版本（v${cur.v + 1}）；历史版本保持不变——回滚本身也可再回滚。`,
      okText: '确认回滚',
      cancelText: '取消',
      onOk: () => {
        const nv = {
          v: cur.v + 1, date: '2026-09-29 14:40', source: '回滚',
          desc: `回滚：恢复到 v${target.v}`, operator: '小李 · 地质/质检', task: '—',
          bad: target.bad, content: target.content
        }
        setVers(s => ({ ...s, [pageKey]: [...s[pageKey], nv] }))
        setViewVer(null)
        setBanner({ kind: 'success', text: `已回滚：当前版 = v${nv.v}（内容恢复自 v${target.v}），平台恢复 CEP-A。注意：回滚本身也记成一次新提交（可再滚回）。` })
      }
    })
  }

  const q = kw.trim().toLowerCase()
  const filtered = PAGES.filter(p =>
    (libF === 'all' || p.lib === libF)
    && (!q || (p.title + p.src + p.lib).toLowerCase().includes(q)))

  function statusTagOf(key) {
    const l = vers[key]
    return (l[l.length - 1].bad
      ? <Tag color="orange">字段待核对</Tag>
      : <Tag color="green">正常</Tag>)
  }

  const catalogColumns = [
    {
      title: '百科页', dataIndex: 'title',
      render: (v, p) => (
        <div>
          <b style={{ fontSize: 13 }}>{v}</b>
          <div style={{ fontSize: 12, color: '#8a94a3' }}>来源：{p.src}</div>
        </div>
      )
    },
    {
      title: '所属库', dataIndex: 'lib', width: 120,
      render: v => <Tag color={LIB_COLORS[v]}>{v}</Tag>
    },
    {
      title: '当前版', width: 110,
      render: (_, p) => <span>v{vers[p.key].length ? vers[p.key][vers[p.key].length - 1].v : 1}（共 {vers[p.key].length} 版）</span>
    },
    { title: '最近更新', dataIndex: 'updated', width: 110 },
    {
      title: <span>状态{helpIcon(<>最近一次重建后的核对结果：百科页内容与井档案对不上时标"字段待核对"；回滚恢复后转回"正常"。核对出的对不上项由相关负责人认领处理后消除标红。</>)}</span>,
      width: 120, render: (_, p) => statusTagOf(p.key)
    },
    {
      title: '操作', width: 64, align: 'center',
      render: (_, p) => (
        <Tooltip title="打开百科页">
          <Button size="small" icon={<FileTextOutlined />}
            onClick={e => { e.stopPropagation(); openPage(p.key) }} />
        </Tooltip>
      )
    }
  ]

  const verColumns = [
    {
      title: '版本', width: 120,
      render: (_, v) => (
        <Space size={6}>
          <b>v{v.v}</b>
          {cur.v === v.v && <Tag color="blue" style={{ marginInlineEnd: 0 }}>当前版</Tag>}
          {v.bad && <Tag color="orange" style={{ marginInlineEnd: 0 }}>含待核对项</Tag>}
        </Space>
      )
    },
    {
      title: <span>来源{helpIcon(<>每版的改动来源（F52 四态）：自动重建 / 智能体 / 人工 / 回滚。回滚产生的版本来源记为回滚，因此回滚本身也可再回滚。</>)}</span>,
      width: 96, dataIndex: 'source',
      render: s => <Tag color={SOURCE_COLORS[s]}>{s}</Tag>
    },
    { title: '更新时间', dataIndex: 'date', width: 110 },
    {
      title: <span>操作人{helpIcon(OPERATOR_HELP)}</span>,
      dataIndex: 'operator', width: 140
    },
    {
      title: <span>经由单号{helpIcon(TASK_HELP)}</span>,
      dataIndex: 'task', width: 110,
      render: t => <code style={{ fontSize: 12 }}>{t}</code>
    },
    { title: '说明', dataIndex: 'desc' },
    {
      title: '操作', width: 96, align: 'center',
      render: (_, v) => (
        <Button size="small" icon={<EyeOutlined />} onClick={e => { e.stopPropagation(); viewVersion(v.v) }}>
          查看全文
        </Button>
      )
    }
  ]

  const related = RELATED[pageKey]
  const bodyContent = viewing ? viewing.content : cur.content

  return (
    <Card
      title={
        <Tabs
          activeKey={tab} size="small" onChange={setTab}
          items={[
            { key: 'catalog', label: `百科页（${PAGES.length}）` },
            { key: 'read', label: '页面内容' },
            { key: 'versions', label: `版本历史（${list.length}）` }
          ]}
        />
      }
      extra={
        <Space size={4}>
          <span style={{ color: '#8a94a3', fontSize: 12 }}>报告入库自动重写成中文百科页 · 页内词条自动挂链接 · 每次重建留版本，改错一键回滚</span>
          {helpIcon(<>百科页是报告的可读版：把入库切好的段拼回全文（重叠去重、图片说明回读），再按 wiki 模板重写成一篇自由 Markdown 页——小节、段落、表格随内容长出，模板约束在生成提示词里、不设固定节；每个库一个目录。页内井号、区块名自动挂链接；论断带「证」角标，点击定位生成来源切片；台账名册内的术语与指标自动挂口径卡，台账没有的词不挂。每次重建都落一个版本，版本历史可查看任一版全文，改错了随时一键回滚，回滚也留痕。</>)}
        </Space>
      }
    >
      {tab === 'catalog' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Space wrap size={8}>
              <Select size="small" style={{ width: 150 }} value={libF} onChange={setLibF}
                options={[{ value: 'all', label: '所属库：全部' }, { value: '完井报告库', label: '完井报告库' }, { value: '生产月报库', label: '生产月报库' }]} />
              <Input size="small" allowClear style={{ width: 240 }} value={kw}
                onChange={e => setKw(e.target.value)} placeholder="搜百科页 / 来源报告…" />
            </Space>
            <span style={{ color: '#8a94a3', fontSize: 12 }}>{`筛选结果 ${filtered.length} / ${PAGES.length} 条`}</span>
          </div>
          <Table
            size="small" columns={catalogColumns} dataSource={filtered} pagination={false} rowKey="key"
            rowClassName={p => (p.key === selRow ? 'ant-table-row-selected' : '')}
            onRow={p => ({
              onClick: () => setSelRow(p.key),
              onDoubleClick: () => { setSelRow(p.key); openPage(p.key) },
              style: { cursor: 'pointer' }
            })}
          />
        </>
      )}

      {tab === 'read' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Space size={8}>
              <Button size="small" icon={<ArrowLeftOutlined />} onClick={() => { setTab('catalog'); setViewVer(null) }}>返回目录</Button>
              <span style={{ fontSize: 15, fontWeight: 600 }}>{page.title} · 百科页</span>
              {viewing
                ? <Tag color="orange">正在查看 v{viewing.v}</Tag>
                : <Tag color="blue">当前版：v{cur.v}</Tag>}
            </Space>
            {helpIcon(META_HELP)}
          </div>

          {viewing && (
            <Alert style={{ marginBottom: 12 }} type="warning" showIcon message={
              <Space size={12}>
                <span>正在查看 v{viewing.v}（历史版本快照，{viewing.date} 由{viewing.source}生成）——当前版为 v{cur.v}。</span>
                <Button size="small" onClick={() => setViewVer(null)}>返回当前版</Button>
              </Space>
            } />
          )}

          <div id="meta-bar" style={{ border: '1px solid #f0f0f0', borderRadius: 6, padding: '8px 12px', marginBottom: 16, background: '#fafafa' }}>
            <Space size={16} wrap style={{ fontSize: 12.5 }}>
              <span>来源报告：<a href="#/B1">{page.src}</a></span>
              <span>生成来源：<Tag style={{ marginInlineEnd: 0 }} color={SOURCE_COLORS[cur.source]}>{cur.source}</Tag></span>
              <span>当前版本：<b>v{cur.v}</b>（共 {list.length} 版）· 更新于 {cur.date} · 操作人 {cur.operator}</span>
              <span>状态：{statusTagOf(pageKey)}</span>
              <span style={{ color: '#8a94a3' }}>slug：<code style={{ fontSize: 12 }}>{page.slug}</code></span>
              <a onClick={() => setMetaOpen(o => !o)}>{metaOpen ? '收起' : '展开'}</a>
            </Space>
            {metaOpen && (
              <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px dashed #e8e8e8', fontSize: 12.5 }}>
                <Space size={16} wrap>
                  <span>所属库：<Tag color={LIB_COLORS[page.lib]} style={{ marginInlineEnd: 0 }}>{page.lib}</Tag></span>
                  <span>
                    关联对象：<b>{related.label}</b>（{related.detail}）—— <a href="#/A2">井档案</a> · <a href="#/B5">关系图谱</a>
                  </span>
                </Space>
              </div>
            )}
          </div>

          <Md text={bodyContent} />
        </>
      )}

      {tab === 'versions' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Space size={4}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>版本历史</span>
              <span style={{ color: '#8a94a3', fontSize: 12 }}>当前阅读：{page.title}</span>
              {helpIcon(VER_HELP)}
            </Space>
            {list.length > 1 ? (
              <Button type="primary" size="small" icon={<RollbackOutlined />} onClick={rollback}>
                回滚（恢复到上一版 v{cur.v - 1}）
              </Button>
            ) : (
              <Tooltip title="只有 1 版，无可回滚">
                <Button size="small" icon={<RollbackOutlined />} disabled>回滚</Button>
              </Tooltip>
            )}
          </div>
          <Table
            size="small" columns={verColumns} rowKey="v"
            dataSource={list} pagination={false}
          />
          {banner && (
            <Alert style={{ marginTop: 16 }} showIcon type={banner.kind} message={banner.text} />
          )}
        </>
      )}
    </Card>
  )
}
