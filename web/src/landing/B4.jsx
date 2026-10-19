import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button, Card, Empty, Input, Modal, Popover, Select, Space, Spin, Table, Tabs, Tag, Tooltip, theme
} from 'antd'
import {
  ArrowLeftOutlined, FileTextOutlined, QuestionCircleOutlined
} from '@ant-design/icons'
import { errText } from '../api/client.js'
import { getWikiPage, glossaryChipView, listWikiPages, loadClaimEvidence } from '../api/b4.js'
import ClampCell from '../components/ClampCell.jsx'  // 共享件（表格单元格长文本截断）

window.__traces = Object.assign(window.__traces || {}, {
  B4: 'F50 百科页 · F51 台账挂接 · F52 论断回链 · m6 卡'
})

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: 'var(--pa-text-tertiary)', cursor: 'help' }} />
  </Tooltip>
)

// —— 元数据条「关联对象」展开联动（词条链接点击 → 展开元数据条并滚动到位）——
let __metaExpand = () => {}

// ── 展示映射（值全部来自服务端——色映射/链名属前端展示层职责，R-WIRE B4-1/3/7） ──
const LIB_COLORS = { 完井报告库: 'blue', 生产月报库: 'purple' }
// 状态两态由服务端按当前版正文 [[flag:]] 有无判定直返（行为规则 5 服务端组装
// ——本地 statusTagOf 正文扫描退役，R-WIRE B4-3）；未知值兜底 default。
const STATUS_COLOR = { 字段待核对: 'orange', 正常: 'green' }
// 关联对象 links[] 由 DTO 携带（硬编码 #/A2·#/B5 退役，R-WIRE B4-7）——
// 站内链名映射为展示层选择，未知链原样展示。
const LINK_LABELS = { '#/A2': '井档案', '#/B5': '关系图谱' }

// 词条自动链接：点页内词条 → 展开元数据条「关联对象」行并滚动到位
function WellLink({ id }) {
  return <a href="#meta" onClick={e => { e.preventDefault(); __metaExpand(id) }}>{id}</a>
}

// —— F52 论断回链：证据条目细节（report/section/type/text）不在 B4 端点 2——
//    展开时懒加载 B2 端点 1/2 只读投影（api/b4.loadClaimEvidence，复用 kb.js；
//    合同 mock 更正清单⑨）；论断句 claims[].text 真 DTO 有，弹层补显。——
function EvidenceMark({ claim, sourceReportId }) {
  const [open, setOpen] = useState(false)
  const [lazy, setLazy] = useState({ loading: false, chunks: null, error: '' })
  const loadingRef = useRef(false) // 同 tick 在途守卫——闭包 lazy.loading 未及更新前重复点「证」不重发（W-B4.rev F3）

  if (!claim || !claim.evidenceChunkIds.length) return null // 无锚论断不渲染——fail-closed，不伪造回链

  function toggle(next) {
    setOpen(next)
    // 首次展开才拉证据（chunks===null＝未加载；失败后重开弹层即重试）；未展开零请求
    if (next && lazy.chunks === null && !loadingRef.current) {
      loadingRef.current = true
      setLazy({ loading: true, chunks: null, error: '' })
      loadClaimEvidence(sourceReportId, claim.evidenceChunkIds)
        .then(chunks => {
          loadingRef.current = false
          setLazy({ loading: false, chunks, error: '' })
        })
        .catch(err => {
          loadingRef.current = false // 失败即解除在途——重开弹层仍可重试（语义不变）
          setLazy({ loading: false, chunks: null, error: errText(err) })
        })
    }
  }

  return (
    <>
      <Tooltip title={`论断可回链证据：来源切片 ${claim.evidenceChunkIds.join('、')}——点击定位`}>
        <a className="ev-mark" href="#/B2" onClick={e => { e.preventDefault(); toggle(true) }}
          style={{
            fontSize: 12, marginLeft: 4, padding: '0 5px', borderRadius: 3,
            border: '1px solid var(--pa-primary)', color: 'var(--pa-primary)', lineHeight: '16px',
            display: 'inline-block', verticalAlign: '1px'
          }}>证</a>
      </Tooltip>
      <Modal
        title="证据来源（切片回链）" open={open} onCancel={() => toggle(false)} width={640}
        footer={[
          <Button key="close" onClick={() => toggle(false)}>关闭</Button>,
          <Button key="go" type="primary" onClick={() => { toggle(false); window.location.hash = '/B2' }}>
            在切片管理中定位
          </Button>
        ]}
      >
        <div style={{ color: 'var(--pa-text-tertiary)', fontSize: 12, marginBottom: 12 }}>
          本页论断由入库切片重写生成，点击「证」可回链生成来源；下列切片可在「切片管理」中逐条核对。
        </div>
        <div style={{ fontSize: 12, marginBottom: 12 }}><b>论断：</b>{claim.text}</div>
        {lazy.loading && <Spin size="small" />}
        {lazy.error && <div style={{ color: 'var(--pa-danger)', fontSize: 12 }}>{lazy.error}</div>}
        {lazy.chunks && !lazy.chunks.length && (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="证据切片不在切片台账（锚失效）——按 fail-closed 口径不伪造回链" />
        )}
        {(lazy.chunks || []).map(c => (
          <div key={c.id} style={{ marginBottom: 12 }}>
            <Space size={6}>
              <Tag color="blue" style={{ marginInlineEnd: 0 }}>{c.id}</Tag>
              <Tag style={{ marginInlineEnd: 0 }}>{c.type}</Tag>
              <span style={{ fontSize: 12 }}>{c.report}</span>
            </Space>
            <div style={{ fontSize: 12, color: 'var(--pa-text-tertiary)', margin: '4px 0' }}>{c.section}</div>
            <div style={{ fontSize: 12, background: 'rgba(74,157,255,0.06)', borderLeft: '3px solid var(--pa-primary)', padding: '6px 10px' }}>{c.text}</div>
          </div>
        ))}
      </Modal>
    </>
  )
}

// —— F51 台账挂接：词表＝C1 台账名册＋别名，台账没有的词不挂（防误链）；卡内容＝
//    glossary_terms[].card 生成时固化投影（C1 端点 2/3 行同形——服务端直取不建仓，
//    展示映射见 api/b4.glossaryChipView）——
function GlossChip({ term }) {
  const g = glossaryChipView(term)
  return (
    <Popover
      trigger="click" placement="top"
      title={<span>词条口径卡 · {g.word}</span>}
      content={
        <div style={{ width: 320 }}>
          <Space size={6} style={{ marginBottom: 8 }}>
            <Tag color="purple" style={{ marginInlineEnd: 0 }}>{g.kindLabel}</Tag>
            <Tag color={g.statusColor} style={{ marginInlineEnd: 0 }}>{g.status}</Tag>
          </Space>
          <div style={{ fontSize: 12, marginBottom: 6 }}><b>定义：</b>{g.def ?? '—'}</div>
          <div style={{ fontSize: 12, color: 'var(--pa-text-tertiary)', lineHeight: 1.8 }}>
            负责人：{g.owner ?? '—'}{g.extra ? ` · ${g.extra}` : ''}<br />
            来源：{g.source ? `${g.source}（${g.ref}）` : g.ref}
          </div>
        </div>
      }
    >
      <a className="g-chip" onClick={e => e.preventDefault()}
        style={{ color: 'var(--pa-primary)', borderBottom: '1px dashed var(--pa-primary)', cursor: 'pointer' }}>{g.word}</a>
    </Popover>
  )
}

// —— 自由 markdown 正文渲染（合同 [[…]] 标记族原样内嵌解析：well/route/claim/term/flag；
//    五族解析器与 R-WIRE §3.1 B4-8 证实的服务端 content 兼容——原样保留，前端不改写业务文案）——
function renderInline(text, keyBase, ctx) {
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
      else if (type === 'claim') {
        nodes.push(<EvidenceMark key={`${keyBase}-${i}`} claim={ctx.claims.get(arg)} sourceReportId={ctx.sourceReportId} />)
      }
      else if (type === 'term') {
        const g = ctx.glossary.get(arg)
        nodes.push(g
          ? <GlossChip key={`${keyBase}-${i}`} term={g} />
          : arg) // 词表（台账名册＋别名）没有的词不挂——台账闸防误链
      }
      else if (type === 'flag') nodes.push(
        <span key={`${keyBase}-${i}`} className="wiki-flag"
          style={{
            fontSize: 12, marginLeft: 4, padding: '1px 6px', borderRadius: 3,
            background: ctx.token.colorWarningBg, border: `1px solid ${ctx.token.colorWarningBorder}`, color: ctx.token.colorWarning,
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

// 正文表格/小节分隔线配色一律取 antd 主题 token（colorBorderSecondary/colorFillAlter/colorSplit
// ——暗色算法下自动映射深色值）；不许硬编码浅色 hex（暗底上白底白字不可读的根源）。
function Md({ text, ctx }) {
  const { token } = theme.useToken()
  const tctx = { ...ctx, token } // renderInline 的 flag 徽标同源取主题色
  const TD_STYLE = { border: `1px solid ${token.colorBorderSecondary}`, padding: '6px 12px', fontSize: 12 }
  const TH_STYLE = { ...TD_STYLE, background: token.colorFillAlter, fontWeight: 600, textAlign: 'left', whiteSpace: 'nowrap' }
  const lines = (text || '').trim().split('\n')
  const out = []
  let i = 0, key = 0
  while (i < lines.length) {
    const line = lines[i]
    if (!line.trim()) { i++; continue }
    if (line.startsWith('### ')) {
      out.push(<h4 key={key++} style={{ fontSize: 12, fontWeight: 600, margin: '12px 0 6px' }}>{renderInline(line.slice(4), `h${key}`, tctx)}</h4>)
      i++; continue
    }
    if (line.startsWith('## ')) {
      out.push(<h3 key={key++} style={{ fontSize: 14, fontWeight: 600, margin: '18px 0 10px', paddingBottom: 6, borderBottom: `1px solid ${token.colorSplit}` }}>{renderInline(line.slice(3), `h${key}`, tctx)}</h3>)
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
            <thead><tr>{head.map((c, j) => <th key={j} style={TH_STYLE}>{renderInline(c, `th${key}-${j}`, tctx)}</th>)}</tr></thead>
            <tbody>{body.map((r, ri) => (
              <tr key={ri}>{r.map((c, ci) => <td key={ci} style={TD_STYLE}>{renderInline(c, `td${key}-${ri}-${ci}`, tctx)}</td>)}</tr>
            ))}</tbody>
          </table>
        )
      }
      continue
    }
    if (line.startsWith('- ')) {
      const items = []
      while (i < lines.length && lines[i].startsWith('- ')) { items.push(lines[i].slice(2)); i++ }
      out.push(<ul key={key++} style={{ margin: '4px 0 14px', paddingLeft: 20, fontSize: 12, lineHeight: 1.9 }}>{items.map((t, j) => <li key={j}>{renderInline(t, `li${key}-${j}`, tctx)}</li>)}</ul>)
      continue
    }
    const para = [line]
    i++
    while (i < lines.length && lines[i].trim() && !/^(#{2,3} |\||- )/.test(lines[i])) { para.push(lines[i].trim()); i++ }
    out.push(<p key={key++} style={{ margin: '0 0 12px', fontSize: 12, lineHeight: 1.9 }}>{renderInline(para.join(''), `p${key}`, tctx)}</p>)
  }
  if (!out.length) return <Empty description="当前版无正文内容。" />
  return <div className="wiki-md">{out}</div>
}

const META_HELP = '页面由报告全文自动重写成一篇自由 Markdown 文档（模板约束在生成提示词里，不设固定节）；slug 稳定——报告重新解析后沿用原页原地更新，不会另建新页、旧链接不断。'

const LIST_LIB_OPTIONS = [
  { value: 'all', label: '所属库：全部' },
  { value: '完井报告库', label: '完井报告库' },
  { value: '生产月报库', label: '生产月报库' }
]

export default function B4() {
  const { token } = theme.useToken()
  const [tab, setTab] = useState('catalog') // catalog | read（v0.4 两页签——版本历史页签随撤除退役）
  // 目录：服务端数据（wiki_page 表无种子——空库空态即验收态，R-WIRE §3.2）
  const [pages, setPages] = useState(null)      // null＝目录未加载；[]＝空态
  const [total, setTotal] = useState(0)         // 全量计数（筛选前先数——「筛选结果 X / Y 条」拼装）
  const [listLoading, setListLoading] = useState(false)
  const [listError, setListError] = useState('')
  // 筛选：服务端参数化（lib/keyword——本地 filter 退役，R-WIRE B4-4；输入防抖可选件）
  const [libF, setLibF] = useState('all')
  const [kw, setKw] = useState('')
  const [debouncedKw, setDebouncedKw] = useState('')
  const [selRow, setSelRow] = useState(null)
  // 读页：端点 2 全文快照（openPage 异步化——R-WIRE B4-5）
  const [pageId, setPageId] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [metaOpen, setMetaOpen] = useState(false)
  const seqRef = useRef(0)

  __metaExpand = () => { setMetaOpen(true); requestAnimationFrame(() => document.getElementById('meta-bar')?.scrollIntoView({ behavior: 'smooth', block: 'start' })) }

  // 关键词防抖（250ms——避免逐键打服务端；可选项，R-WIRE B4-4「输入防抖可选」）
  useEffect(() => {
    const t = setTimeout(() => setDebouncedKw(kw), 250)
    return () => clearTimeout(t)
  }, [kw])

  // 端点 1：目录（lib/keyword 服务端筛选；total＝全量计数；client 已 toast
  // 错误包——页面内联失败态＋重试，不再重复弹）
  const loadPages = useCallback(() => {
    let on = true
    setListLoading(true)
    listWikiPages({ lib: libF, keyword: debouncedKw })
      .then(res => {
        if (!on) return
        setPages(res.items)
        setTotal(res.total)
        setListError('')
        setListLoading(false)
      })
      .catch(err => {
        if (!on) return
        setPages([])
        setListError(errText(err))
        setListLoading(false)
      })
    return () => { on = false }
  }, [libF, debouncedKw])

  useEffect(() => loadPages(), [loadPages])

  // 端点 2：打开读页（异步化＋404 态 wiki_not_found——含 wiki 开关关未生成）；
  // seq 竞窗守卫——快速连开两页旧响应不回写。
  function openPage(pid) {
    setPageId(pid)
    setTab('read')
    const seq = ++seqRef.current
    setDetailLoading(true)
    setDetailError('')
    setDetail(null)
    getWikiPage(pid)
      .then(d => {
        if (seq !== seqRef.current) return
        setDetail(d)
        setDetailLoading(false)
      })
      .catch(err => {
        if (seq !== seqRef.current) return
        setDetailError(errText(err))
        setDetailLoading(false)
      })
  }

  const catalogColumns = [
    {
      title: '百科页', dataIndex: 'title',
      render: (v, p) => (
        <div>
          {/* 字重 700＝与本表同族的「问题」列（B3）一致——原为 <b>（≈700），此处还原 */}
          <div style={{ fontWeight: 700, fontSize: 12 }}><ClampCell text={v} /></div>
          <div style={{ fontSize: 12, color: 'var(--pa-text-tertiary)' }}>来源：{p.sourceReport.doc}</div>
        </div>
      )
    },
    {
      title: '所属库', dataIndex: 'lib', width: 120,
      render: v => <Tag color={LIB_COLORS[v] || 'default'}>{v}</Tag>
    },
    {
      title: '当前版', width: 110,
      render: (_, p) => <span>v{p.currentVersion}</span>
    },
    { title: '最近更新', dataIndex: 'updated', width: 110 },
    {
      title: <span>状态{helpIcon(<>最近一次重建后的核对结果：百科页字段与井档案对不上时标"字段待核对"；人工修源头重入库重铸后重新核对。核对出的对不上项暂不做认领闭环（挂治理批）。</>)}</span>,
      width: 120, render: (_, p) => <Tag color={STATUS_COLOR[p.status] || 'default'}>{p.status}</Tag>
    },
    {
      title: '操作', width: 64, align: 'center',
      render: (_, p) => (
        <Tooltip title="打开百科页">
          <Button size="small" type="text" icon={<FileTextOutlined />}
            onClick={e => { e.stopPropagation(); openPage(p.id) }} />
        </Tooltip>
      )
    }
  ]

  // 正文标记解析上下文：claims 按 claim_id、glossary 按 word 建索引（[[claim:]]/
  // [[term:]] 标记 → 端点 2 同页投影；无锚论断/词表外词由解析器 fail-closed 处置）
  const claimsById = new Map((detail?.claims || []).map(c => [c.claimId, c]))
  const glossaryByWord = new Map((detail?.glossaryTerms || []).map(g => [g.word, g]))
  const mdCtx = { claims: claimsById, glossary: glossaryByWord, sourceReportId: detail?.sourceReport.id }

  return (
    <Card
      title={
        <Tabs
          activeKey={tab} size="small" onChange={setTab}
          items={[
            { key: 'catalog', label: `百科页（${total}）` },
            { key: 'read', label: '页面内容' }
          ]}
        />
      }
      extra={
        <Space size={4}>
          <span style={{ color: 'var(--pa-text-tertiary)', fontSize: 12 }}>报告入库自动重写成中文百科页 · 页内词条自动挂链接 · 与井档案对不上自动标出</span>
          {helpIcon(<>百科页是报告的可读版：把入库切好的段拼回全文（重叠去重、图片说明回读），再按 wiki 模板重写成一篇自由 Markdown 页——小节、段落、表格随内容长出，模板约束在生成提示词里、不设固定节；每个库一个目录。页内井号、区块名自动挂链接；论断带「证」角标，点击定位生成来源切片；台账名册内的术语与指标自动挂口径卡，台账没有的词不挂。每次重建覆盖当前版——不留历史版本；与井档案对不上的内容自动标出，修源头报告重新入库后重铸覆盖。</>)}
        </Space>
      }
    >
      {tab === 'catalog' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Space wrap size={8}>
              <Select size="small" style={{ width: 150 }} value={libF} onChange={setLibF} options={LIST_LIB_OPTIONS} />
              <Input size="small" allowClear style={{ width: 240 }} value={kw}
                onChange={e => setKw(e.target.value)} placeholder="搜百科页 / 来源报告…" />
            </Space>
            <span style={{ color: 'var(--pa-text-tertiary)', fontSize: 12 }}>{`筛选结果 ${pages ? pages.length : 0} / ${total} 条`}</span>
          </div>
          <Table
            size="small" columns={catalogColumns} dataSource={pages || []} pagination={false} rowKey="id"
            loading={listLoading}
            rowClassName={p => (p.id === selRow ? 'ant-table-row-selected' : '')}
            locale={{
              emptyText: listError
                ? (
                  <Empty description={<span>目录加载失败——{listError}</span>}>
                    <Button size="small" onClick={loadPages}>重试</Button>
                  </Empty>
                )
                : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无百科页——报告入库且库配置开启 wiki 支路后自动生成" />
            }}
            onRow={p => ({
              onClick: () => setSelRow(p.id),
              onDoubleClick: () => { setSelRow(p.id); openPage(p.id) },
              style: { cursor: 'pointer' }
            })}
          />
        </>
      )}

      {tab === 'read' && (
        detailLoading ? (
          <div style={{ textAlign: 'center', padding: 48 }}><Spin tip="加载百科页…" /></div>
        ) : detailError ? (
          <Empty description={<span>读页加载失败——{detailError}</span>}>
            <Button size="small" onClick={() => openPage(pageId)}>重试</Button>
          </Empty>
        ) : detail ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Space size={8}>
                <Button size="small" icon={<ArrowLeftOutlined />} onClick={() => setTab('catalog')}>返回目录</Button>
                <span style={{ fontSize: 16, fontWeight: 600 }}>{detail.title} · 百科页</span>
                <Tag color="blue">当前版：v{detail.currentVersion}</Tag>
              </Space>
              {helpIcon(META_HELP)}
            </div>

            <div id="meta-bar" style={{ border: `1px solid ${token.colorBorderSecondary}`, borderRadius: 6, padding: '8px 12px', marginBottom: 16, background: token.colorFillQuaternary }}>
              <Space size={16} wrap style={{ fontSize: 12.5 }}>
                <span>来源报告：<a href="#/B1">{detail.sourceReport.doc}</a></span>
                <span>生成来源：<Tag style={{ marginInlineEnd: 0 }} color="default">{detail.generationSource}</Tag></span>
                <span>当前版本：<b>v{detail.currentVersion}</b> · 更新于 {detail.updated} · 操作人 {detail.operator ?? '—'}</span>
                <span>状态：<Tag style={{ marginInlineEnd: 0 }} color={STATUS_COLOR[detail.status] || 'default'}>{detail.status}</Tag></span>
                <span style={{ color: 'var(--pa-text-tertiary)' }}>slug：<code style={{ fontSize: 12 }}>{detail.slug}</code></span>
                <a onClick={() => setMetaOpen(o => !o)}>{metaOpen ? '收起' : '展开'}</a>
              </Space>
              {metaOpen && (
                <div style={{ marginTop: 8, paddingTop: 8, borderTop: `1px dashed ${token.colorSplit}`, fontSize: 12.5 }}>
                  <Space size={16} wrap>
                    <span>所属库：<Tag color={LIB_COLORS[detail.lib] || 'default'} style={{ marginInlineEnd: 0 }}>{detail.lib}</Tag></span>
                    <span>
                      关联对象：{detail.relatedObjects.length
                        ? detail.relatedObjects.map((o, i) => (
                          <span key={o.id || i}>
                            <b>{o.type === 'well' ? `井 ${o.id}` : o.id}</b>（{o.summary}）——{' '}
                            {o.links.map((l, j) => (
                              <span key={l}><a href={l}>{LINK_LABELS[l] || l}</a>{j < o.links.length - 1 ? ' · ' : ''}</span>
                            ))}
                          </span>
                        ))
                        : '—'}
                    </span>
                  </Space>
                </div>
              )}
            </div>

            <Md text={detail.content} ctx={mdCtx} />
          </>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="从目录选择一篇百科页" />
        )
      )}
    </Card>
  )
}
