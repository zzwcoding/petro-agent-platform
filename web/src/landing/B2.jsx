/**
 * 落地树 · B2 切片管理（P1-04 全页真 API——B2-答案出处.md v0.3 六端点消费）。
 *
 * 合同：teach-petro-agent/specs/api/B2-答案出处.md v0.3（端点 1 片段台账两读法
 * 分派/2 父块回捞/3 标记问题片段/4 复核队列/5 复核确认·驳回/6 驳回后销记）。
 * 视觉与交互形态对照原型树 #/proto/B2（prototype 终稿快照 web/src/pages/B2.jsx）
 * ——数据是真、形是原型；mock 简化更正清单⑧项逐条兑现：
 * ①ctx 不内嵌行数据——展开/详情懒加载端点 2；③REPORTS 本地常量→端点 1＋复用
 * B1 端点 1（refs≠null 进下拉，选项文案「{doc} · {lib}」照抄）；④markedKey
 * 本地 state→端点 3（已标记态持久——队列在途态 fragmentIds 派生，409 兜底）；
 * ⑤卡头总数→B1 端点 1 refs 求和；⑥详情弹窗「报告＋库」两行按 report_id 从
 * 下拉数据联查；⑦复核队列→端点 4/5/6；⑧标记入队→端点 3（事务写入）。
 *
 * locator 消费（B2 册对账 10「URL locator 消费随实施批」即本票；P1-11 桥退役
 * 收口）：支持 `#/B2?chunk=<fragment_id>` 进页定位——Shell.parseHash 剥 hash
 * query 挪到 location.search（replaceState），本页直读 location.search 消费：
 * 跨报告扫描定位片段→选中高亮＋打开详情弹窗；消费后清 search（幂等——同
 * URL 二次进入不重复定位）。
 */

import { useEffect, useRef, useState } from 'react'
import {
  Alert, Button, Card, Input, message, Modal, Select, Space, Table, Tabs, Tag, Tooltip
} from 'antd'
import { FileSearchOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import { ApiError } from '../api/client.js'
import {
  FRAGMENT_TYPES, ISSUE_OPEN_STATES, closeIssueReport, getFragmentContext,
  getReports, listFragments, listIssueReports, markFragmentIssue, reviewIssueReport
} from '../api/kb.js'

/** URL locator 读取（真 search 优先；hash query 兜底——剥链失败的静默补偿）。 */
function readLocatorChunk() {
  const fromSearch = new URLSearchParams(window.location.search || '').get('chunk')
  if (fromSearch) return fromSearch
  const hash = window.location.hash || ''
  const qAt = hash.indexOf('?')
  return qAt >= 0 ? new URLSearchParams(hash.slice(qAt + 1)).get('chunk') : null
}

/** locator 消费后清 search（幂等——防同 URL 二次进入重复定位）。 */
function clearLocatorSearch() {
  try {
    history.replaceState(null, '', window.location.pathname + (window.location.hash || ''))
  } catch { /* jsdom/隐私模式静默 */ }
}

// 合同常量：类型 Tag 色展示映射（B2 常量表照抄——纯前端渲染映射）
const TYPE_COLORS = {
  原文块: 'blue',
  图片说明块: 'purple',
  图片文字块: 'cyan',
  摘要块: 'green',
  问题块: 'orange'
}
const ISSUE_TAG_COLORS = { 待质检复核: 'orange', 已修正: 'green', 已驳回: 'red', 已销记: 'default' }

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)
const dim = { fontSize: 12, color: '#8a94a3' }

const TYPE_HELP = (
  <>入库切段时片段分五类：原文块＝报告正文切出的小段；图片说明块＝图内没有文字时系统自动生成的说明，命中后回读它所在章节的正文；图片文字块＝系统识别出的图内文字（图例、标注），图片本体不进索引、文字与说明进；摘要块＝入库时自动生成的全文档摘要，每份 ×1；问题块＝每 20 段自动生成一批"可能被问的问题"。</>
)
const HIT_HELP = '搜索命中的永远是小段，完整段落永远不直接出现在搜索结果里；点行首箭头展开，把它所在的完整上下文段带出来。'
const SRC_HELP = '出处三件套＝报告名＋井号＋章节路径，AI 回答引用时原样带给用户，一眼知道出处在哪；当前按报告浏览，报告名见"报告"下拉。'
const QUEUE_HELP = '核查员在片段清单"标记问题片段"后进本队列；复核确认转修正流（B1 报告库修正片段并重建索引），驳回必填理由退回标记人——标记人可重新标记或销记，队列不留悬挂单。'

/** 错误包 → 内联展示行（人话 message＋code＋trace_id——D1/B1 先例同构）。 */
function errText(err) {
  if (!(err instanceof ApiError)) return String(err)
  return [err.message, err.code ? `code ${err.code}` : '', err.traceId ? `trace ${err.traceId}` : '']
    .filter(Boolean).join(' · ')
}

/**
 * 落地 B2 切片管理页（两页签：片段清单 / 复核队列——六端点全接线）。
 * @returns {JSX.Element}
 */
export default function B2Landing() {
  const [tab, setTab] = useState('list')

  // ── 报告下拉（复用 B1 端点 1——refs≠null 进下拉，零改动原样消费） ──
  const [reports, setReports] = useState([]) // {id, doc, lib, refs}
  const [reportsLoading, setReportsLoading] = useState(true)
  const [reportsError, setReportsError] = useState(null)
  const [report, setReport] = useState(null)
  const totalRefs = reports.reduce((n, r) => n + (r.refs || 0), 0) // 卡头总数＝refs 求和（同源）

  // ── 片段台账（端点 1 按报告读法）＋类型/关键词筛 ──
  const [frags, setFrags] = useState([])
  const [fragsLoading, setFragsLoading] = useState(false)
  const [fragsError, setFragsError] = useState(null)
  const [typeF, setTypeF] = useState('all')
  const [kw, setKw] = useState('')
  const [sel, setSel] = useState(null)
  const [flashId, setFlashId] = useState(null) // locator 定位高亮

  // ── 父块回捞（端点 2——懒加载缓存）＋详情弹窗＋标记（端点 3） ──
  const [ctxCache, setCtxCache] = useState({}) // fragId → context 串（'…加载中' 占位）
  const [openFrag, setOpenFrag] = useState(null)
  const [markedIds, setMarkedIds] = useState(new Set()) // 待质检复核态片段集（已标记态持久）
  const [markBusy, setMarkBusy] = useState(false)
  const [markError, setMarkError] = useState(null)
  const [markedHint, setMarkedHint] = useState(null) // 端点 3 服务端 hint 回显

  // ── 复核队列（端点 4/5/6）＋驳回弹窗 ──
  const [issues, setIssues] = useState([])
  const [issuesLoading, setIssuesLoading] = useState(true)
  const [issuesError, setIssuesError] = useState(null)
  const [issueF, setIssueF] = useState('all')
  const [rejectOf, setRejectOf] = useState(null) // 待驳回标记单
  const [rejectReason, setRejectReason] = useState('')
  const [rejectError, setRejectError] = useState(null)
  const [rejectBusy, setRejectBusy] = useState(false)

  // ── locator（#/B2?chunk= 消费——B2 册对账 10） ──
  const [locator, setLocator] = useState(null) // {chunk} 或 null
  const pendingLocate = useRef(null) // 定位到的片段行——数据到位后开弹窗＋高亮

  // 首拍：报告下拉（B1 端点 1）＋队列在途态（已标记派生）
  useEffect(() => {
    let on = true
    getReports()
      .then(d => { if (on) { setReports(d.items.filter(r => r.refs != null)); setReportsError(null); setReportsLoading(false) } })
      .catch(err => { if (on) { setReportsError(err); setReportsLoading(false) } })
    return () => { on = false }
  }, [])

  const loadQueue = () => {
    setIssuesLoading(true)
    listIssueReports({ state: issueF })
      .then(d => {
        setIssues(d.items); setIssuesError(null); setIssuesLoading(false)
        // 已标记态持久：待质检复核态单的 fragmentIds（mock 更正④——本地 state 退役）
        return listIssueReports({ state: '待质检复核' })
      })
      .then(d => { if (d) setMarkedIds(new Set(d.items.map(i => i.fragmentId))) })
      .catch(err => { setIssuesError(err); setIssuesLoading(false) })
  }
  useEffect(() => { loadQueue() }, [issueF]) // eslint-disable-line react-hooks/exhaustive-deps

  // 报告下拉就绪 → 默认选第一卷；locator 消费优先（直读 URL query——P1-11 桥退役）
  useEffect(() => {
    if (reportsLoading || !reports.length || report) return
    const chunk = readLocatorChunk()
    if (chunk) {
      clearLocatorSearch() // 消费即清（幂等——同 URL 二次进入不重复定位）
      setLocator({ chunk }) // 跨报告扫描定位
    } else {
      setReport(reports[0].id)
    }
  }, [reports, reportsLoading]) // eslint-disable-line react-hooks/exhaustive-deps

  // locator 消费：逐报告扫描片段清单（演示量级整表读法）定位 chunk
  useEffect(() => {
    if (!locator || reportsLoading) return
    let on = true
    ;(async () => {
      for (const r of reports) {
        try {
          const d = await listFragments({ reportId: r.id })
          const hit = d.items.find(f => f.id === locator.chunk)
          if (hit && on) {
            pendingLocate.current = hit
            setReport(r.id)
            setLocator(null)
            return
          }
        } catch { /* 单卷失败继续扫下一卷 */ }
      }
      if (on) {
        setLocator(null)
        setReport(reports[0].id)
      }
    })()
    return () => { on = false }
  }, [locator, reports, reportsLoading])

  // 片段台账加载（端点 1——report_id 携带按报告整组取数；type/keyword 服务端筛）
  useEffect(() => {
    if (!report) return
    let on = true
    setFragsLoading(true)
    listFragments({ reportId: report, type: typeF, keyword: kw })
      .then(d => {
        if (!on) return
        setFrags(d.items); setFragsError(null); setFragsLoading(false)
        const located = pendingLocate.current
        if (located && d.items.some(f => f.id === located.id)) {
          pendingLocate.current = null
          setSel(located.id)
          setFlashId(located.id) // 定位高亮（滚动＋行高亮）
          setOpenFrag(located) // 进页定位＝打开详情弹窗（回跳锚语义）
        }
      })
      .catch(err => { if (on) { setFragsError(err); setFragsLoading(false) } })
    return () => { on = false }
  }, [report, typeF, kw])

  // locator 高亮滚动（渲染后一次性 scrollIntoView；jsdom 无该 API——守卫）
  useEffect(() => {
    if (!flashId) return
    const el = document.querySelector('.b2-locate-flash')
    if (el && typeof el.scrollIntoView === 'function') el.scrollIntoView({ block: 'center' })
    const t = setTimeout(() => setFlashId(null), 2400)
    return () => clearTimeout(t)
  }, [flashId, frags])

  // ── 父块回捞（端点 2）：展开行/详情弹窗懒加载 ──
  function loadContext(fragId) {
    if (ctxCache[fragId]) return
    setCtxCache(c => ({ ...c, [fragId]: null })) // null＝加载中
    getFragmentContext(fragId)
      .then(d => setCtxCache(c => ({ ...c, [fragId]: d.context })))
      .catch(err => setCtxCache(c => ({ ...c, [fragId]: `上下文段读取失败：${errText(err)}` })))
  }

  function openDetail(frag) {
    setMarkError(null)
    setMarkedHint(null)
    setSel(frag.id)
    setOpenFrag(frag)
    loadContext(frag.id)
  }

  // ── 标记问题片段（端点 3——只标记不直改；409 重复标记兜底） ──
  async function doMark() {
    if (!openFrag) return
    setMarkBusy(true)
    setMarkError(null)
    try {
      const r = await markFragmentIssue(openFrag.id)
      setMarkedHint(r.hint)
      setMarkedIds(s => new Set([...s, openFrag.id]))
      loadQueue() // 新单入队——队列页签与已标记派生集刷新
    } catch (err) {
      setMarkError(err) // 409＝已标记态（服务端为唯一真源——兜底刷新）
      loadQueue()
    } finally {
      setMarkBusy(false)
    }
  }

  // ── 复核确认/驳回（端点 5）/销记（端点 6）/重新标记（端点 3 再发新单） ──
  async function doConfirm(issue) {
    try {
      await reviewIssueReport(issue.id, { action: 'confirm' })
      loadQueue()
      message.success('已复核确认——转修正流：到报告库修正片段并重建索引。')
      location.hash = '/B1' // 确认页面即跳 B1 修正入口（企业化清理批落位同构）
    } catch (err) {
      message.error(errText(err))
    }
  }
  async function doReject() {
    if (!rejectOf) return
    setRejectBusy(true)
    setRejectError(null)
    try {
      await reviewIssueReport(rejectOf.id, { action: 'reject', reason: rejectReason.trim() })
      setRejectOf(null)
      setRejectReason('')
      loadQueue()
    } catch (err) {
      setRejectError(err) // 400 空理由兜底（页面按钮空理由禁用双保险）
    } finally {
      setRejectBusy(false)
    }
  }
  async function doReMark(issue) {
    try {
      await markFragmentIssue(issue.fragmentId) // 新单入队——旧驳回单服务端转已销记
      loadQueue()
      message.success('已重新标记——新标记单入队，原驳回单已转销记。')
    } catch (err) {
      message.error(errText(err))
    }
  }
  async function doClose(issue) {
    try {
      const r = await closeIssueReport(issue.id)
      loadQueue()
      message.success(`已销记（${r.state}）——队列零悬挂。`)
    } catch (err) {
      message.error(errText(err))
    }
  }

  // ── 列定义（照原型终稿） ──
  const fragColumns = [
    {
      title: <span>类型{helpIcon(TYPE_HELP)}</span>, dataIndex: 'type', width: 96,
      render: t => <Tag color={TYPE_COLORS[t]}>{t}</Tag>
    },
    {
      title: <span>命中句{helpIcon(HIT_HELP)}</span>, dataIndex: 'hit',
      render: h => <b style={{ fontSize: 13 }}>{h}</b>
    },
    { title: '井', dataIndex: 'well', width: 66, render: v => v || <span style={dim}>—</span> },
    {
      title: <span>章节路径{helpIcon(SRC_HELP)}</span>, dataIndex: 'section', width: 280,
      render: p => <span style={{ color: '#8a94a3', fontSize: 12 }}>{p || '—'}</span>
    },
    {
      title: '操作', width: 60, align: 'center',
      render: (_, c) => (
        <Tooltip title="片段详情（出处三件套＋命中句＋完整上下文段）">
          <Button size="small" icon={<FileSearchOutlined />}
            onClick={e => { e.stopPropagation(); openDetail(c) }} />
        </Tooltip>
      )
    }
  ]

  const issueColumns = [
    {
      title: '片段', dataIndex: 'fragmentLabel',
      render: v => <b style={{ fontSize: 13 }}>{v}</b>
    },
    { title: '标记人', dataIndex: 'markedBy', width: 130 },
    { title: '标记时间', dataIndex: 'markedAt', width: 140 },
    {
      title: '状态', dataIndex: 'state', width: 150,
      render: (v, x) => (
        <Space size={4} direction="vertical" style={{ rowGap: 2 }}>
          <Tag color={ISSUE_TAG_COLORS[v] || 'default'}>{v}</Tag>
          {x.rejectReason && <span style={{ color: '#8a94a3', fontSize: 12 }}>驳回理由：{x.rejectReason}</span>}
        </Space>
      )
    },
    {
      title: '操作', width: 210, align: 'center',
      render: (_, x) => {
        if (x.state === '待质检复核') {
          return (
            <Space size={4}>
              <Tooltip title="复核确认——转修正流：到报告库（B1）修正片段并重建索引，本单落「已修正」">
                <Button size="small" type="primary" onClick={() => doConfirm(x)}>确认 · 转修正流</Button>
              </Tooltip>
              <Tooltip title="驳回——必填理由，标记单退回标记人处置（重新标记或销记）">
                <Button size="small" danger onClick={() => { setRejectError(null); setRejectOf(x); setRejectReason('') }}>驳回</Button>
              </Tooltip>
            </Space>
          )
        }
        if (x.state === '已驳回') {
          return (
            <Space size={4}>
              <Tooltip title="重新标记——对片段发起新标记单，本驳回单转「已销记」">
                <Button size="small" onClick={() => doReMark(x)}>重新标记</Button>
              </Tooltip>
              <Tooltip title="销记——标记人关闭本单，不再修正">
                <Button size="small" onClick={() => doClose(x)}>销记</Button>
              </Tooltip>
            </Space>
          )
        }
        return <span style={{ color: '#8a94a3', fontSize: 12 }}>—</span>
      }
    }
  ]

  const pendingCount = markedIds.size
  const cur = openFrag ? frags.find(f => f.id === openFrag.id) || openFrag : null
  const curMarked = cur ? markedIds.has(cur.id) : false
  const curCtx = cur ? ctxCache[cur.id] : null

  const listPane = (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <Space wrap size={8}>
          <Select size="small" style={{ width: 400 }} value={report || undefined}
            loading={reportsLoading} onChange={setReport}
            placeholder={reportsError ? '报告清单拉取失败' : '选择报告'}
            options={reports.map(r => ({ value: r.id, label: `${r.doc} · ${r.lib}` }))} />
          <Select size="small" style={{ width: 140 }} value={typeF} onChange={setTypeF}
            options={[{ value: 'all', label: '类型：全部' }, ...FRAGMENT_TYPES.map(t => ({ value: t, label: t }))]} />
          <Input size="small" allowClear style={{ width: 220 }} value={kw} onChange={e => setKw(e.target.value)}
            placeholder="搜命中句 / 井号 / 章节…" />
        </Space>
        <span style={{ color: '#8a94a3', fontSize: 12 }}>{`筛选结果 ${frags.length} 条`}</span>
      </div>
      {reportsError && (
        <Alert style={{ marginBottom: 12 }} type="error" showIcon
          message="报告下拉拉取失败——不能按报告浏览" description={errText(reportsError)} />
      )}
      {fragsError && (
        <Alert style={{ marginBottom: 12 }} type="error" showIcon
          message="片段清单拉取失败——下表不是最新数据" description={errText(fragsError)} />
      )}
      <Table
        size="small" columns={fragColumns} dataSource={frags} pagination={false}
        rowKey="id" loading={fragsLoading}
        rowClassName={c => (c.id === flashId ? 'b2-locate-flash' : (c.id === sel ? 'ant-table-row-selected' : ''))}
        onRow={c => ({
          onClick: () => setSel(c.id),
          onDoubleClick: () => openDetail(c),
          style: { cursor: 'pointer' }
        })}
        expandable={{
          expandedRowRender: c => (
            <div style={{ fontSize: 13, lineHeight: 1.8 }}>
              <span style={{ color: '#8a94a3', fontSize: 12, marginRight: 8 }}>完整上下文段</span>
              {ctxCache[c.id] ?? '读取中……'}
            </div>
          ),
          onExpand: (expanded, c) => { if (expanded) loadContext(c.id) } // 展开即回捞（端点 2 懒加载——mock 更正①）
        }}
        locale={{ emptyText: '该报告暂无片段：入库完成后这里按报告建台账。' }}
      />
    </>
  )

  const reviewPane = (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <Space wrap size={8}>
          <Select size="small" style={{ width: 160 }} value={issueF} onChange={setIssueF}
            options={[
              { value: 'all', label: '状态：全部' },
              ...ISSUE_OPEN_STATES.map(s => ({ value: s, label: s }))
            ]} />
        </Space>
        <span style={{ color: '#8a94a3', fontSize: 12 }}>
          {`标记单 ${issues.length} 条 · 待质检复核 ${pendingCount} 段`}
          {helpIcon(QUEUE_HELP)}
        </span>
      </div>
      {issuesError && (
        <Alert style={{ marginBottom: 12 }} type="error" showIcon
          message="复核队列拉取失败——下表不是最新数据" description={errText(issuesError)} />
      )}
      <Table
        size="small" columns={issueColumns} dataSource={issues} pagination={false}
        rowKey="id" loading={issuesLoading}
        locale={{ emptyText: '没有符合条件的标记单。' }}
      />
    </>
  )

  return (
    <div style={{ maxWidth: 1180 }}>
      <div style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 4 }}>
        <span style={{ fontSize: 18, fontWeight: 600 }}>切片管理</span>
        <span style={{ color: '#8a94a3', fontSize: 13 }}>
          片段清单按报告浏览 · AI 回答引用的就是这些片段 · 发现切坏了就标记给质检复核
          {helpIcon(<>入库时把报告切成片段，这里按报告建台账：浏览、筛选、核对内容；AI 回答引用的就是这些片段（引用号对不上的一律删掉、不渲染）。发现切坏了的片段就"标记问题片段"，复核确认后由管理员修正并重建索引。</>)}
        </span>
      </div>
      <Card
        title={<span>片段清单（{totalRefs}）</span>}
        extra={<span style={{ color: '#8a94a3', fontSize: 12 }}>命中的是小段，完整段落不直接进搜索结果</span>}
      >
        <Tabs
          activeKey={tab} size="small" onChange={setTab}
          items={[
            { key: 'list', label: '片段清单', children: listPane },
            { key: 'review', label: `复核队列（${pendingCount}）`, children: reviewPane }
          ]}
        />
      </Card>

      {/* 片段详情弹窗（三件套＋命中句＋完整上下文段＝端点 2 懒加载；标记＝端点 3） */}
      <Modal
        title={cur && <Space><span>片段详情</span><Tag color={TYPE_COLORS[cur.type]}>{cur.type}</Tag></Space>}
        open={!!cur} onCancel={() => setOpenFrag(null)} width={640}
        footer={cur ? (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#8a94a3', fontSize: 12 }}>
              {curMarked
                ? (markedHint || '已标记 · 待质检复核——复核确认后由管理员修正片段并重建索引。')
                : '发现这段切坏了（错字/断句/归属错）？标记给质检复核。'}
            </span>
            <Button size="small" disabled={curMarked} loading={markBusy} onClick={doMark}>
              {curMarked ? '已标记 · 待质检复核' : '标记问题片段'}
              {!curMarked && helpIcon(<>标记后进入"复核队列"页签；复核确认后由管理员修正片段并重建索引，核查员不直接改原文。</>)}
            </Button>
          </div>
        ) : null}
      >
        {cur && (
          <>
            {markError && (
              <Alert style={{ marginBottom: 8 }} type="warning" showIcon
                message={markError instanceof ApiError && markError.status === 409
                  ? '该片段已有标记单在待质检复核——勿重复标记。'
                  : '标记失败'}
                description={errText(markError)} />
            )}
            <Table size="small" pagination={false} rowKey="k"
              columns={[{ title: '项', dataIndex: 'k', width: 110 }, { title: '内容', dataIndex: 'v' }]}
              dataSource={[
                {
                  k: '报告',
                  v: (
                    <>
                      {cur.report}
                      <br />
                      <span style={{ color: '#8a94a3', fontSize: 12 }}>
                        {reports.find(r => r.id === cur.reportId)?.lib || '—'}
                      </span>
                    </>
                  )
                },
                { k: '井号', v: cur.well || '—' },
                { k: '章节路径', v: <span style={{ color: '#8a94a3', fontSize: 12 }}>{cur.section || '—'}</span> },
                { k: '命中句', v: <b style={{ fontSize: 13 }}>{cur.hit}</b> },
                { k: '完整上下文段', v: <span style={{ fontSize: 13 }}>{curCtx ?? '读取中……'}</span> }
              ]}
            />
          </>
        )}
      </Modal>

      {/* 驳回弹窗（端点 5 reject——理由必填，空理由按钮禁用＋400 服务端兜底） */}
      <Modal
        title={rejectOf ? '驳回标记单' : ''}
        open={!!rejectOf} onCancel={() => setRejectOf(null)} width={480}
        footer={
          <Space>
            <Button size="small" onClick={() => setRejectOf(null)}>取消</Button>
            <Button size="small" type="primary" danger loading={rejectBusy}
              disabled={!rejectReason.trim()} onClick={doReject}>驳回</Button>
          </Space>
        }
      >
        <div style={{ marginBottom: 8, fontSize: 13 }}>
          驳回后本标记单退回标记人（可重新标记或销记）；理由必填。
        </div>
        <Input.TextArea rows={3} value={rejectReason} onChange={e => setRejectReason(e.target.value)}
          placeholder="驳回理由（必填）——如：检泵日期与台账对不上，请核对后重新标记" />
        {rejectError && (
          <Alert style={{ marginTop: 8 }} type="error" showIcon
            message={rejectError instanceof ApiError && rejectError.status === 400
              ? '驳回必须写明理由。'
              : '驳回失败'}
            description={errText(rejectError)} />
        )}
      </Modal>
    </div>
  )
}
