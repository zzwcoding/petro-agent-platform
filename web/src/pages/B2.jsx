import { useState } from 'react'
import { Button, Card, Input, Modal, Select, Space, Table, Tag, Tooltip } from 'antd'
import { FileSearchOutlined, QuestionCircleOutlined } from '@ant-design/icons'

window.__guides = Object.assign(window.__guides || {}, {
  B2: [
    '在"报告"下拉切一份报告——片段列表整组换数据（完井报告 5 条 / 生产月报 3 条）。',
    '点行首箭头展开任一片段——看命中句带出的完整上下文段；行尾"详情"或双击行看出处三件套。',
    '筛选行按"类型"筛、按关键词搜——比如筛"图片说明块"，看没有文字的图怎么也能被检索命中。',
    '悬浮"类型""章节路径"列头的 ?——五类片段各是什么、出处三件套怎么用。',
    '片段详情里点"标记问题片段"——核查员只标记不直改：进质检复核队列，复核确认后由管理员修正片段并重建索引。'
  ]
})
window.__traces = Object.assign(window.__traces || {}, {
  B2: 'F6 RAG 管道 · F30 大小段配合/片段质检修正流 · F31 出处标签 · F36 图片说明块 · m6/m14 卡'
})

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

const TYPE_COLORS = {
  原文块: 'blue',
  图片说明块: 'purple',
  图片文字块: 'cyan',
  摘要块: 'green',
  问题块: 'orange'
}

const TYPE_HELP = (
  <>入库切段时片段分五类：原文块＝报告正文切出的小段；图片说明块＝图内没有文字时系统自动生成的说明，命中后回读它所在章节的正文；图片文字块＝系统识别出的图内文字（图例、标注），图片本体不进索引、文字与说明进；摘要块＝入库时自动生成的全文档摘要，每份 ×1；问题块＝每 20 段自动生成一批"可能被问的问题"。</>
)
const HIT_HELP = '搜索命中的永远是小段，完整段落永远不直接出现在搜索结果里；点行首箭头展开，把它所在的完整上下文段带出来。'
const SRC_HELP = '出处三件套＝报告名＋井号＋章节路径，AI 回答引用时原样带给用户，一眼知道出处在哪；当前按报告浏览，报告名见左侧"报告"下拉。'

// 两份报告与各自入库切出的片段（报告名 · 井号 · 章节路径＝出处三件套）
// 命名导出（票 93 同源纪律）：B3 新增问答"切片原文"起草源直接引用本清单，禁止另抄
export const REPORTS = [
  {
    key: 'r1',
    doc: '《N-02 井完井报告（英文 · 200 页）》',
    lib: '完井报告库',
    chunks: [
      {
        type: '原文块', well: 'N-02', path: '章节 01 井基本情况 ＞ 1.2 投产信息',
        hit: 'N-02（渤中28-1-N2）于 2019-06-15 投产。',
        ctx: '1.2 投产信息：N-02 井位于渤南区块、CEP-A 平台；井别采油（EW）；2019-06-15 投产；截至本期状态：生产中。'
      },
      {
        type: '图片说明块', well: 'N-02', path: '章节 03 图件 ＞ 图 3-7',
        hit: '图 3-7 岩性柱状图：按深度展示该井段岩性分布（图内无文字，本说明为系统自动生成）。',
        ctx: '3.2 岩性：见图 3-7 岩性柱状图。'
      },
      {
        type: '图片文字块', well: 'N-02', path: '章节 03 图件 ＞ 图 3-7',
        hit: '图 3-7 图内文字（系统识别）：砂岩 / 泥岩 / 灰岩（图例）。',
        ctx: '图 3-7 岩性柱状图（图片本体不进索引，文字与说明进）。'
      },
      {
        type: '摘要块', well: 'N-02', path: '全文档',
        hit: '本报告为 N-02 井（渤中28-1-N2）完井报告：位于渤南区块 CEP-A 平台，井别采油，2019-06-15 投产，状态生产中。',
        ctx: '全文档摘要 ×1，入库时自动生成。'
      },
      {
        type: '问题块', well: 'N-02', path: '全文档',
        hit: '本报告可能被问：N-02 井的完井方式是什么？',
        ctx: '每 20 段自动生成一批"可能被问的问题"块。'
      }
    ]
  },
  {
    key: 'r2',
    doc: '《渤中28-1 区块月度生产月报（2026-08）》',
    lib: '生产月报库',
    chunks: [
      {
        type: '原文块', well: 'N-11', path: '章节 02 检修与停产 ＞ 2.1 检泵',
        hit: 'N-11 井检泵：2026-08-28 → 2026-09-06，影响产量约 210 吨。',
        ctx: '2.1 检泵：N-11 井检泵作业，起止 2026-08-28 → 2026-09-06（跨月），影响产量约 210 吨；该检修为事后补录，批次号 20260911-T3（T-3 补录）。'
      },
      {
        type: '原文块', well: 'N-11', path: '章节 04 计量与折算 ＞ 4.2 单位换算',
        hit: '渤中区块原油密度按 0.89 t/m³ 折算，吨↔方换算＝质量÷密度。',
        ctx: '4.2 单位换算：原油密度按区块——渤南 0.86 / 渤中 0.89 / 渤西 0.91（t/m³）。本月 N-11 一行日产油误录单位"方"（12.40 方），已按密度折算为约 11.04 吨。'
      },
      {
        type: '原文块', well: 'N-11', path: '章节 01 井基本情况',
        hit: 'N-11 井 2026-08-30 起检泵停产。',
        ctx: '01 井基本情况：N-11（EW 采油），2020-02-20 投产，CEP-B 平台，渤中区块；状态：停产（2026-08-30 起检泵）。台账存在状态滞后特征——"已停仍挂生产中"的行要靠质检规则抓。'
      }
    ]
  }
]

const TOTAL = REPORTS.reduce((n, r) => n + r.chunks.length, 0)
// 全部片段带报告归属，供详情弹窗跨筛选取数
const ALL_CHUNKS = REPORTS.flatMap(r => r.chunks.map((c, i) => ({ ...c, key: `${r.key}-${i}`, doc: r.doc, lib: r.lib })))

export default function B2() {
  const [report, setReport] = useState('r1')
  const [typeF, setTypeF] = useState('all')
  const [kw, setKw] = useState('')
  const [loading, setLoading] = useState(false)
  const [sel, setSel] = useState(null)
  const [openKey, setOpenKey] = useState(null)
  const [markedKey, setMarkedKey] = useState(null) // 已标记问题片段（F30 片段质检修正流）

  function pickReport(key) {
    if (key === report) return
    setLoading(true)
    setTimeout(() => { setReport(key); setLoading(false) }, 350)
  }

  const rep = REPORTS.find(r => r.key === report)
  const chunks = rep.chunks.map((c, i) => ({ ...c, key: `${report}-${i}` }))
  const filtered = chunks.filter(c => {
    if (typeF !== 'all' && c.type !== typeF) return false
    const q = kw.trim().toLowerCase()
    return !q || (c.hit + c.path + c.well).toLowerCase().includes(q)
  })
  const cur = ALL_CHUNKS.find(c => c.key === openKey)

  const cols = [
    {
      title: <span>类型{helpIcon(TYPE_HELP)}</span>, dataIndex: 'type', width: 96,
      render: t => <Tag color={TYPE_COLORS[t]}>{t}</Tag>
    },
    {
      title: <span>命中句{helpIcon(HIT_HELP)}</span>, dataIndex: 'hit',
      render: h => <b style={{ fontSize: 13 }}>{h}</b>
    },
    { title: '井', dataIndex: 'well', width: 66 },
    {
      title: <span>章节路径{helpIcon(SRC_HELP)}</span>, dataIndex: 'path', width: 280,
      render: p => <span style={{ color: '#8a94a3', fontSize: 12 }}>{p}</span>
    },
    {
      title: '操作', width: 60, align: 'center',
      render: (_, c) => (
        <Tooltip title="片段详情（出处三件套＋命中句＋完整上下文段）">
          <Button size="small" icon={<FileSearchOutlined />}
            onClick={e => { e.stopPropagation(); setSel(c.key); setOpenKey(c.key) }} />
        </Tooltip>
      )
    }
  ]

  return (
    <Card
      title={<span>片段清单（{TOTAL}）{helpIcon(<>入库时把报告切成片段，这里按报告建台账：浏览、筛选、核对内容；AI 回答引用的就是这些片段（引用号对不上的一律删掉、不渲染）。发现切坏了的片段就"标记问题片段"，复核确认后由管理员修正并重建索引。</>)}</span>}
      extra={
        <Space size={4}>
          <span style={{ color: '#8a94a3', fontSize: 12 }}>命中的是小段，完整段落不直接进搜索结果</span>
        </Space>
      }
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <Space wrap size={8}>
          <Select size="small" style={{ width: 400 }} value={report} onChange={pickReport}
            options={REPORTS.map(r => ({ value: r.key, label: `${r.doc} · ${r.lib}` }))} />
          <Select size="small" style={{ width: 140 }} value={typeF} onChange={setTypeF}
            options={[{ value: 'all', label: '类型：全部' }, ...Object.keys(TYPE_COLORS).map(t => ({ value: t, label: t }))]} />
          <Input size="small" allowClear style={{ width: 220 }} value={kw} onChange={e => setKw(e.target.value)}
            placeholder="搜命中句 / 井号 / 章节…" />
        </Space>
        <span style={{ color: '#8a94a3', fontSize: 12 }}>{`筛选结果 ${filtered.length} / ${chunks.length} 条`}</span>
      </div>
      <Table
        size="small" columns={cols} dataSource={filtered} pagination={false} rowKey="key"
        loading={loading}
        rowClassName={c => (c.key === sel ? 'ant-table-row-selected' : '')}
        onRow={c => ({
          onClick: () => setSel(c.key),
          onDoubleClick: () => { setSel(c.key); setOpenKey(c.key) },
          style: { cursor: 'pointer' }
        })}
        expandable={{
          expandedRowRender: c => (
            <div style={{ fontSize: 13, lineHeight: 1.8 }}>
              <span style={{ color: '#8a94a3', fontSize: 12, marginRight: 8 }}>完整上下文段</span>
              {c.ctx}
            </div>
          )
        }}
      />

      <Modal
        title={cur && <Space><span>片段详情</span><Tag color={TYPE_COLORS[cur.type]}>{cur.type}</Tag></Space>}
        open={!!cur} onCancel={() => setOpenKey(null)} width={640}
        footer={cur ? (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#8a94a3', fontSize: 12 }}>
              {markedKey === cur.key
                ? '已标记 · 待质检复核——复核确认后由管理员修正片段并重建索引。'
                : '发现这段切坏了（错字/断句/归属错）？标记给质检复核。'}
            </span>
            <Button size="small" disabled={markedKey === cur.key}
              onClick={() => setMarkedKey(cur.key)}>
              {markedKey === cur.key ? '已标记 · 待质检复核' : '标记问题片段'}
              {markedKey !== cur.key && helpIcon(<>标记后进入质检复核队列；复核确认后由管理员修正片段并重建索引，核查员不直接改原文。</>)}
            </Button>
          </div>
        ) : null}
      >
        {cur && (
          <Table size="small" pagination={false} rowKey="k"
            columns={[{ title: '项', dataIndex: 'k', width: 110 }, { title: '内容', dataIndex: 'v' }]}
            dataSource={[
              { k: '报告', v: <>{cur.doc}<br /><span style={{ color: '#8a94a3', fontSize: 12 }}>{cur.lib}</span></> },
              { k: '井号', v: cur.well },
              { k: '章节路径', v: <span style={{ color: '#8a94a3', fontSize: 12 }}>{cur.path}</span> },
              { k: '命中句', v: <b style={{ fontSize: 13 }}>{cur.hit}</b> },
              { k: '完整上下文段', v: <span style={{ fontSize: 13 }}>{cur.ctx}</span> }
            ]}
          />
        )}
      </Modal>
    </Card>
  )
}
