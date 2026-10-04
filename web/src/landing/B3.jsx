/**
 * 落地树 · B3 常见问题库（P1-06 全页真 API——B3 合同 v0.2 十七端点消费）。
 *
 * 合同：teach-petro-agent/specs/api/B3-常见问题库.md v0.2。视觉与交互形态对照
 * 原型树 #/proto/B3（原型终稿快照 web/src/pages/B3.jsx）——数据是真、形是原型。
 *
 * 接线差异（相对原型页，登记票面）：
 * - 数据源 = api/faq.js（client 真 HTTP；无任何 mock 种子——清单/候选全量服务端
 *   出，状态筛/关键词走端点 1/9 query，创建时间正序/频次倒序均服务端排序）；
 * - 审核流闭环：新增入库 → 待审核（行标＋筛项）→ 行尾「发布」（端点 17）→
 *   服务中/负例；驳回 → 已停用（留档可再提审）；
 * - 合并入口＝行尾合并图标 → 目标选择弹窗（合同更正项 ⑫——目标由人选）；
 * - 重复校验（端点 4）输入即检（服务端归一化比对——前端零拼装 norm）；
 * - 引用知识起草（端点 14）：台账口径/切片原文两选可组合，LLM 服务端起草，
 *   草稿填入答案框（确认权在人）；切片下拉＝B2 端点 1 全库扁平清单；
 * - 挖掘管线五拍：扫库（端点 10/11，202＋轮询，关弹窗不中断）→ 候选库
 *   （端点 9）→ 向量比对（端点 12，展开行只认比对结论）→ LLM 起草
 *   （端点 13，草稿自动填入新增弹窗）→ 人审核发布（端点 17，候选随发布
 *   事务落已发布）；
 * - 导入（端点 15，两模式＋试校验＋四计数）/导出（端点 16，预签名直链下载）；
 * - ⚙ 检索配置弹窗＝纯只读展示（相似问合并开关＋合并阈值 0.87＋负例入口——
 *   配置端点已撤除登记，B3-6/B3-4；假保存按钮已随 UI-04 T2 清除）。
 *
 * UI-04（阶段 1 交互优化——方案 §5-B3，施工票 tickets/phase1-ui/UI-04.md）：
 * 主表/候选表接 PagedTable client 分页（resetKey 绑筛状态）；补统一页头三件套；
 * 主表失败态内联 Alert 常驻＋错误空态分立；扫库失败（轮询通道/终态行）message
 * 提示；关键词 350ms 防抖＋请求序号守卫；合并目标全库化（不带筛 getItems）；
 * helpIcon/dim/errText 改 UI-00 共享件 import——errText 统一三段（message＋code
 * ＋trace），B3 错误提示多出 trace 段＝方案 §3.2-2 定死接受的行为变化。
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert, Button, Card, Checkbox, Input, message, Modal, Radio, Select, Space,
  Tag, Tooltip, Upload
} from 'antd'
import {
  ClusterOutlined, ExportOutlined, FileSearchOutlined, ImportOutlined, MergeOutlined,
  PauseCircleOutlined, PlayCircleOutlined, PlusOutlined, RobotOutlined, SettingOutlined,
  SyncOutlined
} from '@ant-design/icons'
import { errText } from '../api/client.js'
import { helpIcon, dim } from '../components/helpIcon.jsx'  // UI-00 共享件（UI-04 T11——页内副本删除）
import PagedTable from '../components/PagedTable.jsx'  // UI-00 共享件（UI-04 T1/T7——集合表统一分页）
import {
  addSimilar, compareCandidate, createEntry, dupCheck, exportLibrary, getCandidates,
  getItems, getItemDetail, draftCandidate, draftFromRefs, importLibrary, listLedgerOptions,
  listSliceOptions, mergeEntry, removeSimilar, reviewEntry, startScan, toggleState,
  useFaqScanPolling
} from '../api/faq.js'

// UI-04 T11：helpIcon/dim 页内副本删除——import UI-00 共享件（components/helpIcon.jsx），
// 母本即本页现形、渲染物不变；errText 同批改 client.js 导出（三段统一）。
// fieldLabel 本页自持（方案 §3.3——不抽，仅 B1 消费共享化的取舍与本页无关）。
const fieldLabel = { fontSize: 12, color: '#8a94a3', marginBottom: 4 }

const SERVE_TAG = <Tag color="green">服务中</Tag>
const NEG_TAG = <Tag color="red">负例 · 不参与回答</Tag>
const DISABLED_TAG = <Tag>已停用 · 不参与回答</Tag>
const PENDING_TAG = <Tag color="orange">待审核</Tag>

/** 状态标（合同枚举：待审核/服务中/负例/已停用——四态互斥显示序）。 */
export function stateTag(status) {
  if (status === 'pending_review') return PENDING_TAG
  if (status === 'negative') return NEG_TAG
  if (status === 'disabled') return DISABLED_TAG
  return SERVE_TAG
}

const STATUS_HELP = '服务中＝正常参与回答，命中即秒回；待审核＝新增条目待审核发布，暂不参与回答、不被问一问消费；已停用＝暂不参与回答（口径改版等场景先停用待审），可随时启用；负例＝登记在案的"不该答的问题"，不参与回答，检索也找不到。'
// UI-09：措辞去口语化（票面改造项 10——「秒回消费/另一本账/只用于打分」→「直接命中消费/独立/仅用于打分」）
const POSITION_HELP = (
  <>
    本库问答对供问一问直接命中消费（不走报告检索）；考核题库独立（评估资产，仅用于打分）——见 <a href="#/E1">答题考核（评估集）</a>。
  </>
)

/** 候选状态标（四态机器键＋dup/ok 展示派生态——展开按钮只认比对结论）。 */
function candTag(c) {
  if (c.status === 'published') return <Tag color="green">已发布</Tag>
  if (c.status === 'drafted') return <Tag color="blue">草稿待入库</Tag>
  if (c.status === 'pending') return <Tag>待比对</Tag>
  if (c.compare?.verdict === 'dup') return <Tag color="orange">疑似重复</Tag>
  return <Tag color="green">可入库</Tag>
}

export default function B3() {
  // ── 问答清单（端点 1——状态筛/关键词服务端筛，创建时间正序） ──
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [grandTotal, setGrandTotal] = useState(0)
  const [statusF, setStatusF] = useState('all')
  const [kw, setKw] = useState('')
  const [kwQ, setKwQ] = useState('')  // UI-04 T10：350ms 防抖后的查询值（kw 只即时回显输入框）
  const [loading, setLoading] = useState(false)
  const [itemsError, setItemsError] = useState(null)  // UI-04 T3：失败态≠空态（内联 Alert 常驻＋错误空态分立）
  const [mergeHint, setMergeHint] = useState(null)
  const refreshSeq = useRef(0)

  const refresh = useCallback(async () => {
    const seq = ++refreshSeq.current  // UI-04 T10：请求序号守卫——慢的旧响应到点丢弃，不覆盖新筛选结果
    setLoading(true)
    try {
      const d = await getItems({ status: statusF, keyword: kwQ })
      if (seq !== refreshSeq.current) return
      setRows(d.items)
      setTotal(d.total)  // 信封 total/grandTotal（整表返回也带 total——方案 §1-P3；faq.js:74-75 已归一）
      setGrandTotal(d.grandTotal)
      setItemsError(null)
    } catch (err) {
      if (seq !== refreshSeq.current) return
      setItemsError(err)
      message.error(errText(err))
    } finally {
      if (seq === refreshSeq.current) setLoading(false)
    }
  }, [statusF, kwQ])

  useEffect(() => { refresh() }, [refresh])

  // UI-04 T10：关键词 350ms 防抖（同页 dupCheck :151-162 先例节奏）——击键只回显，停 350ms 才驱动查询
  const kwTimer = useRef(null)
  useEffect(() => {
    if (kwTimer.current) clearTimeout(kwTimer.current)
    kwTimer.current = setTimeout(() => setKwQ(kw), 350)
    return () => clearTimeout(kwTimer.current)
  }, [kw])

  // ── 新增问答弹窗（端点 3/4/14——三源起草＋重复校验＋关联口径） ──
  const [addOpen, setAddOpen] = useState(false)
  const [q, setQ] = useState('')
  const [a, setA] = useState('')
  const [neg, setNeg] = useState(false)
  const [hook, setHook] = useState('')
  const [tip, setTip] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [refLedger, setRefLedger] = useState(null)
  const [refSlice, setRefSlice] = useState(null)
  const [draftLdg, setDraftLdg] = useState(false)
  const [dupHit, setDupHit] = useState(null)
  const [pendingCand, setPendingCand] = useState(null)
  const [ledgerOptions, setLedgerOptions] = useState([])
  const [hookOptions, setHookOptions] = useState([{ value: '', label: '不挂接' }])
  const [sliceOptions, setSliceOptions] = useState([])
  const dupTimer = useRef(null)

  const loadRefOptions = useCallback(async () => {
    try {
      const [ledger, slices] = await Promise.all([listLedgerOptions(), listSliceOptions()])
      setLedgerOptions(ledger.ledgerOptions)
      setHookOptions(ledger.hookOptions)
      setSliceOptions(slices)
    } catch (err) {
      message.error(errText(err))  // 下拉源缺省不阻断手填路径
    }
  }, [])

  const openAdd = () => {
    setTip(null)
    setDupHit(null)
    setPendingCand(null)
    setAddOpen(true)
    loadRefOptions()
  }

  // 输入即检（端点 4——防抖节奏前端定，不入合同）
  useEffect(() => {
    if (!addOpen) return undefined
    if (dupTimer.current) clearTimeout(dupTimer.current)
    if (!q.trim()) { setDupHit(null); return undefined }
    dupTimer.current = setTimeout(async () => {
      try {
        const d = await dupCheck(q)
        setDupHit(d.hit ? { id: d.hit.id, question: d.hit.question, hint: d.hint } : null)
      } catch { /* 校验失败不阻断入库 */ }
    }, 350)
    return () => clearTimeout(dupTimer.current)
  }, [q, addOpen])

  async function llmDraft() {
    if (!refLedger && !refSlice) return
    setDraftLdg(true)
    try {
      const ledgerOpt = ledgerOptions.find(o => o.value === refLedger)
      const sliceOpt = sliceOptions.find(o => o.value === refSlice)
      const d = await draftFromRefs({
        ledgerRef: ledgerOpt ? { kind: ledgerOpt.ref.kind, id: ledgerOpt.ref.id } : null,
        sliceRef: sliceOpt ? { reportId: sliceOpt.reportId, fragmentId: sliceOpt.fragmentId } : null
      })
      setA(d.draft)
      if (d.hookSuggestion) setHook(d.hookSuggestion.name)  // 自动挂接该口径/术语
    } catch (err) {
      message.error(errText(err))
    } finally {
      setDraftLdg(false)
    }
  }

  async function submit() {
    setSubmitting(true)
    try {
      const hookOpt = hookOptions.find(o => o.value === hook)
      const d = await createEntry({
        question: q, answer: a, isNegative: neg,
        hook: hook && hookOpt ? { kind: hookOpt.kind, name: hook } : null,
        sourceCandidateId: pendingCand
      })
      setTip(d.hint)
      setQ('')
      setA('')
      setNeg(false)
      setHook('')
      setPendingCand(null)
      await refresh()
    } catch (err) {
      message.error(errText(err))
    } finally {
      setSubmitting(false)
    }
  }

  // ── 详情弹窗（端点 2/5/6——相似问逐条增删即时生效） ──
  const [detail, setDetail] = useState(null)
  const [newSim, setNewSim] = useState('')

  async function openDetail(id) {
    try {
      setDetail(await getItemDetail(id))
      setNewSim('')
    } catch (err) {
      message.error(errText(err))
    }
  }

  async function addSim() {
    const v = newSim.trim()
    if (!v || !detail) return
    try {
      await addSimilar(detail.id, v)
      setDetail(await getItemDetail(detail.id))
      setNewSim('')
      await refresh()
    } catch (err) {
      message.error(errText(err))
    }
  }

  async function removeSim(simId) {
    try {
      const d = await removeSimilar(detail.id, simId)
      message.info(d.hint)
      setDetail(await getItemDetail(detail.id))
      await refresh()
    } catch (err) {
      message.error(errText(err))
    }
  }

  // ── 合并相似问（端点 7——目标由人选，更正项 ⑫） ──
  const [mergeFrom, setMergeFrom] = useState(null)
  const [mergeTarget, setMergeTarget] = useState(null)
  const [mergeOpen, setMergeOpen] = useState(false)
  const [mergeTargets, setMergeTargets] = useState([])  // UI-04 T12：目标选项数据源（全库，不带筛）

  // UI-04 T12：打开弹窗即独立调用 getItems()（不携状态筛/关键词）——状态筛/关键词
  // 激活时跨状态目标可选（对齐「从库内其余问答中选」承诺）；排除条件在渲染处照抄原行为。
  async function openMerge(r) {
    setMergeFrom(r)
    setMergeTarget(null)
    setMergeOpen(true)
    try {
      const d = await getItems()
      setMergeTargets(d.items)
    } catch (err) {
      setMergeTargets([])  // 拉取失败目标下拉置空——合并按钮因无目标禁用，失败不误合并
      message.error(errText(err))
    }
  }

  async function doMerge() {
    if (!mergeFrom) return
    try {
      const d = await mergeEntry(mergeFrom.id, mergeTarget)
      setMergeHint(d.hint)
      setMergeOpen(false)
      setMergeFrom(null)
      await refresh()
    } catch (err) {
      message.error(errText(err))
    }
  }

  // ── 发布/停用启用（端点 17/8） ──
  async function publish(row) {
    try {
      const d = await reviewEntry(row.id, 'publish')
      message.success(d.hint)
      await refresh()
      if (mineOpen) await refreshCandidates()
    } catch (err) {
      message.error(errText(err))
    }
  }

  async function toggle(row) {
    try {
      await toggleState(row.id, row.status === 'disabled' ? 'enable' : 'disable')
      await refresh()
    } catch (err) {
      message.error(errText(err))
    }
  }

  // ── 候选问题库（端点 9——挖掘 Drawer 弹窗：扫库→比对→起草→回填） ──
  const [mineOpen, setMineOpen] = useState(false)
  const [cands, setCands] = useState([])
  const [candTotal, setCandTotal] = useState(0)
  const [candLoading, setCandLoading] = useState(false)  // UI-04 T13：候选表加载态
  const [mineF, setMineF] = useState('all')
  const [scanTaskId, setScanTaskId] = useState(null)
  const [scanMsg, setScanMsg] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [busyCand, setBusyCand] = useState(null)
  const [lastHint, setLastHint] = useState(null)

  const refreshCandidates = useCallback(async (status = mineF) => {
    setCandLoading(true)  // UI-04 T13：拉取期间候选表渲染 loading（对照主表先例）
    try {
      const d = await getCandidates({ status })
      setCands(d.items)
      setCandTotal(d.total)  // 信封 total（CandidatesResponse 带 total——app/api/faq.py:405-407）
      setLastHint(d.scan.lastHint)
      if (d.scan.runningTaskId) setScanTaskId(d.scan.runningTaskId)  // 重开弹窗恢复轮询
      return d
    } catch (err) {
      message.error(errText(err))
      return null
    } finally {
      setCandLoading(false)
    }
  }, [mineF])

  useEffect(() => {
    if (mineOpen) refreshCandidates()
  }, [mineOpen, mineF, refreshCandidates])

  // 扫库轮询（端点 11——关弹窗不中断，重开经 scan.running_task_id 恢复）
  const { status: pollStatus, data: pollData, error: pollError } = useFaqScanPolling(scanTaskId)
  useEffect(() => {
    if (pollStatus === 'polling') setScanning(true)
    if (pollStatus === 'done' && pollData) {
      setScanning(false)
      setScanMsg(pollData.hint)
      setScanTaskId(null)
      refreshCandidates()
      message.success('扫描完成——候选库已刷新。')
    }
    if (pollStatus === 'failed') {
      setScanning(false)
      setScanTaskId(null)
      // UI-04 T6：扫库失败可感知——轮询通道失败（error 非空）与终态行 failed/stuck
      //（HTTP 200 不触发 client toast）分立提示，两条路都不再静默
      if (pollError) message.error('扫库进度查询失败：' + errText(pollError))
      else {
        message.error('扫库任务未成功（状态：' + (pollData?.status || pollData?.state || 'failed')
          + '）——可在本页重新发起扫库')
      }
    }
  }, [pollStatus, pollData, pollError, refreshCandidates])

  async function runScan() {
    setScanMsg(null)
    try {
      const d = await startScan()
      setScanTaskId(d.task_id)
      setScanning(true)
    } catch (err) {
      message.error(errText(err))
    }
  }

  async function runCompare(c) {
    setBusyCand(c.id)
    try {
      const d = await compareCandidate(c.id)
      await refreshCandidates()
      return d
    } catch (err) {
      message.error(errText(err))
      return null
    } finally {
      setBusyCand(null)
    }
  }

  async function runMineDraft(c) {
    setBusyCand(c.id)
    try {
      const d = await draftCandidate(c.id)
      await refreshCandidates()
      // 草稿自动填入「新增问答」弹窗（前端编排——不入服务端合同）
      setPendingCand(c.id)
      setQ(`${c.question}？`)
      setA(d.draft)
      setHook(d.hookSuggestion ? d.hookSuggestion.name : '')
      setTip(null)
      setMineOpen(false)
      setAddOpen(true)
      loadRefOptions()
      message.info('草稿已填入「新增问答」——请人工修改后入库。')
    } catch (err) {
      message.error(errText(err))
    } finally {
      setBusyCand(null)
    }
  }

  // ── 导入/导出（端点 15/16） ──
  const [impOpen, setImpOpen] = useState(false)
  const [impMode, setImpMode] = useState('append')
  const [impDry, setImpDry] = useState(false)
  const [impFile, setImpFile] = useState(null)
  const [impResult, setImpResult] = useState(null)
  const [impBusy, setImpBusy] = useState(false)

  async function runImport() {
    if (!impFile) { message.warning('请先选择 CSV 模板文件'); return }
    setImpBusy(true)
    try {
      const d = await importLibrary({
        mode: impMode, dryRun: impDry, filename: impFile.name, file: impFile
      })
      setImpResult(d)
      await refresh()
    } catch (err) {
      message.error(errText(err))
    } finally {
      setImpBusy(false)
    }
  }

  async function runExport() {
    try {
      const d = await exportLibrary()
      message.success(d.hint)
      window.open(d.downloadUrl, '_blank')  // 预签名直链——浏览器直下，平台不经手
    } catch (err) {
      message.error(errText(err))
    }
  }

  // ── ⚙ 检索配置（只读展示——配置端点撤除登记 B3-6；UI-04 T2：假保存控件清除） ──
  const [cfgOpen, setCfgOpen] = useState(false)

  const cols = [
    { title: '问题', dataIndex: 'question', width: 240, render: v => <b style={{ fontSize: 13 }}>{v}</b> },
    { title: '答案', dataIndex: 'answer', render: v => <span style={{ fontSize: 13 }}>{v}</span> },
    {
      title: <span>相似问法{helpIcon('相似问法＝同一个问题的其他问法，已并入本条目——换这些问法来问，命中同一条答案；详情里可逐条增删，删掉的问法不再命中本条。')}</span>,
      dataIndex: 'similarQuestions', width: 250,
      render: (_, r) => <span style={dim}>{r.similarQuestions.length ? r.similarQuestions.join(' · ') : '—'}</span>
    },
    {
      title: <span>状态{helpIcon(STATUS_HELP)}</span>, width: 150,
      render: (_, r) => stateTag(r.status)
    },
    {
      title: '操作', width: 150, align: 'center',
      render: (_, r) => (
        <Space size={4}>
          {r.status === 'pending_review' && (
            <Tooltip title="审核发布——发布后转入服务/负例，命中即秒回，供问一问消费">
              <Button size="small" type="primary"
                onClick={e => { e.stopPropagation(); publish(r) }}>发布</Button>
            </Tooltip>
          )}
          {r.status !== 'pending_review' && r.status !== 'negative' && (
            r.status === 'disabled' ? (
              <Tooltip title="启用：恢复参与回答，命中即秒回">
                <Button size="small" icon={<PlayCircleOutlined />} aria-label={`启用：${r.question}`}
                  onClick={e => { e.stopPropagation(); toggle(r) }} />
              </Tooltip>
            ) : (
              <Tooltip title="停用：暂不参与回答、可再启用（口径改版等场景先停用待审）">
                <Button size="small" icon={<PauseCircleOutlined />} aria-label={`停用：${r.question}`}
                  onClick={e => { e.stopPropagation(); toggle(r) }} />
              </Tooltip>
            )
          )}
          {r.status !== 'pending_review' && r.status !== 'negative' && (
            <Tooltip title="合并相似问：并入另一条问答（目标由人选）">
              <Button size="small" icon={<MergeOutlined />} aria-label={`合并：${r.question}`}
                onClick={e => { e.stopPropagation(); openMerge(r) }} />
            </Tooltip>
          )}
          <Tooltip title="问答详情">
            <Button size="small" icon={<FileSearchOutlined />} aria-label={`详情：${r.question}`}
              onClick={e => { e.stopPropagation(); openDetail(r.id) }} />
          </Tooltip>
        </Space>
      )
    }
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, height: '100%' }}>
      {/* UI-04 T5 统一页头＋UI-09 收束：口号副标题删除——POSITION_HELP 移挂页标题旁
          （卡头 extra ? 保留，与标题 ? 同一文案；页根 gap:16 承担与卡片的间距） */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <span style={{ fontSize: 18, fontWeight: 600 }}>常见问题库{helpIcon(POSITION_HELP)}</span>
      </div>
      <Card
        // UI-12：root→Card→body flex 链（无 Tabs）——Card 高度有界，body flex 列
        // overflow:hidden，工具栏行恒在，问答清单 PagedTable fill 内滚、页面级滚动消灭
        style={{ flex: '1 1 auto', minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' } }}
        title={<span>问答清单（{grandTotal}）</span>}
        extra={helpIcon(POSITION_HELP) /* UI-04 T5：卡头 extra 三句口号删除只留 helpIcon（副标题已承载） */}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <Space wrap size={8}>
            <Button type="primary" size="small" icon={<PlusOutlined />}
              onClick={() => { setTip(null); openAdd() }}>新增问答</Button>
            <Button size="small" icon={<ClusterOutlined />}
              onClick={() => { setScanMsg(null); setMineOpen(true) }}>从问句挖掘</Button>
            <Button size="small" icon={<ImportOutlined />}
              onClick={() => { setImpResult(null); setImpFile(null); setImpOpen(true) }}>导入</Button>
            <Button size="small" icon={<ExportOutlined />} onClick={runExport}>导出</Button>
            <Tooltip title="检索配置（相似问合并阈值 / 负例登记入口）">
              <Button size="small" icon={<SettingOutlined />} onClick={() => setCfgOpen(true)} />
            </Tooltip>
            <Select size="small" style={{ width: 128 }} value={statusF} onChange={setStatusF}
              options={[
                { value: 'all', label: '状态：全部' },
                { value: 'serve', label: '服务中' },
                { value: 'pending', label: '待审核' },
                { value: 'neg', label: '负例' },
                { value: 'disabled', label: '已停用' }
              ]} />
            <Input size="small" allowClear style={{ width: 220 }} value={kw}
              onChange={e => setKw(e.target.value)} placeholder="搜问题 / 答案 / 相似问法…" />
          </Space>
          <span style={dim}>{`筛选结果 ${total} / ${grandTotal} 条`}</span>
        </div>
        {/* UI-04 T3：失败态≠空态——内联 Alert 常驻（失败呈现不再伪装成「暂无数据」） */}
        {itemsError && (
          <Alert style={{ marginBottom: 12 }} type="error" showIcon
            message="问答清单拉取失败——下表不是最新数据" description={errText(itemsError)} />
        )}
        {/* UI-04 T1：接 PagedTable client 模式（pageSize 20、hideOnSinglePage=false＋showTotal
            组件内定死——统计恒显）；resetKey 绑 statusF|kwQ（kw 为 T10 防抖后查询值）；
            T4 空态定死话术；T3 失败态经 error prop 切错误空态（内联 Alert 另挂——两件并存）；
            UI-12：fill 表内滚（问答清单长表卡内滚、页面不滚） */}
        <PagedTable
          fill
          size="small" columns={cols} dataSource={rows} rowKey="id" loading={loading}
          onRow={r => ({
            onDoubleClick: () => openDetail(r.id),
            style: { cursor: 'pointer' }
          })}
          emptyText="还没有问答：点「新增问答」录入，或「导入」批量建。"
          error={itemsError}
          errorEmptyText="问答清单拉取失败"
          resetKey={`${statusF}|${kwQ}`}
        />
        {mergeHint && <Alert style={{ marginTop: 12 }} type="success" showIcon
          message={mergeHint} closable onClose={() => setMergeHint(null)} />}
      </Card>

      {/* ⚙ 检索配置（只读展示——配置端点撤除登记，B3-6/B3-4；UI-04 T2：假保存按钮与
          「已保存」本地回执删除，弹窗零写动作；T8：? 工程口吻改业务口吻） */}
      <Modal
        title={<span>检索配置（只读展示）{helpIcon(<>相似问合并阈值：入库与导入去重时，候选与既有问答相似度高于该值判"疑似重复"——建议改用合并相似问，不新增条目；阈值由系统管理员统一校准。</>)}</span>}
        open={cfgOpen} onCancel={() => setCfgOpen(false)} footer={null} width={520}
      >
        <div style={{ marginBottom: 12 }}>
          <Space size={6}>
            <span style={{ fontSize: 13 }}>相似问合并</span>
            <Tag color="green">开</Tag>
            <span style={dim}>合并阈值</span>
            <Input size="small" style={{ width: 72 }} value="0.87" disabled />
            {helpIcon(<>自动按语义聚类把重复问法归到一条，合并前人工确认；高于阈值的候选判"疑似重复"。</>)}
          </Space>
        </div>
        <div style={{ marginBottom: 4 }}>
          <Space size={6}>
            <span style={{ fontSize: 13 }}>负例登记入口</span>
            <Tag color="green">已开</Tag>
            {helpIcon(<>在"新增问答"里勾选"登记为负例"即可登记。</>)}
          </Space>
        </div>
      </Modal>

      {/* 新增问答（端点 3 消费面——三源起草＋重复校验＋待审核提示） */}
      <Modal
        title={<span>新增问答{helpIcon(<>常见问题一问一答直接入库：一条问答不走报告检索，命中即秒回；新增先进「待审核」，审核发布后生效。答案从来源起草、人改后入库——平台不自动生成 FAQ（不做自动挖掘）。问题或答案留空时按（未填问题）/（未填答案）登记。</>)}</span>}
        open={addOpen} onCancel={() => setAddOpen(false)} footer={null} width={620}
      >
        <Input size="small" value={q} onChange={e => setQ(e.target.value)} placeholder="问题" />
        <div style={{ marginTop: 10 }}>
          <div style={fieldLabel}>
            引用知识（可组合、可留空）
            {helpIcon(<>答案不从空框里凭记忆写：选取台账口径/切片原文，LLM 基于所选知识起草，人改后入库——答案有据、错了能追溯到源。都不选则手填。</>)}
          </div>
          <Space wrap size={8}>
            <Select size="small" style={{ width: 230 }} placeholder="台账口径（可选）" allowClear
              value={refLedger} onChange={v => setRefLedger(v ?? null)} options={ledgerOptions} />
            <Select size="small" style={{ width: 290 }} placeholder="切片原文（可选）" allowClear
              value={refSlice} onChange={v => setRefSlice(v ?? null)} options={sliceOptions} />
            <Button size="small" icon={<RobotOutlined />} loading={draftLdg}
              disabled={!refLedger && !refSlice}
              onClick={llmDraft}>LLM 起草</Button>
          </Space>
        </div>
        <div style={{ marginTop: 8 }}>
          <div style={fieldLabel}>答案（草稿可改——确认权在人）</div>
          <Input.TextArea size="small" rows={3} value={a}
            onChange={e => setA(e.target.value)} placeholder="答案" />
        </div>
        <div style={{ marginTop: 8 }}>
          <Space size={6}>
            <span style={dim}>关联口径</span>
            <Select size="small" style={{ width: 200 }} value={hook} onChange={setHook}
              options={hookOptions} />
            {helpIcon(<>挂上口径/术语后：口径修订生效时自动定位本条起草建议稿进待审核（不自动直改）；答案命中过期术语时带漂移标注——秒回答案与报告答案一个标准。</>)}
          </Space>
        </div>
        {dupHit && (
          <Alert style={{ marginTop: 8 }} type="warning" showIcon
            message={<span>与既有问答「{dupHit.question}」疑似重复（系统忽略大小写、全角半角差异后比对）：建议改用合并相似问，或确认继续入库。</span>} />
        )}
        <div style={{ marginTop: 8 }}>
          <Checkbox checked={neg} onChange={e => setNeg(e.target.checked)}>
            登记为负例（"不该答的问题"，不参与回答）
          </Checkbox>
        </div>
        <Button type="primary" size="small" style={{ marginTop: 12 }} loading={submitting} onClick={submit}>
          {pendingCand ? '入库（来自候选草稿）' : '入库'}
        </Button>
        {tip && <Alert style={{ marginTop: 12 }} type="success" showIcon message={tip} />}
      </Modal>

      {/* 合并相似问（端点 7——目标由人选） */}
      <Modal
        title={<span>合并相似问{helpIcon(<>合并语义：2 条 → 1 条——被并入条目删除、其问题进目标条目相似问列，两种问法现在命中同一条答案。</>)}</span>}
        open={mergeOpen} onCancel={() => setMergeOpen(false)} width={480}
        onOk={doMerge} okText="合并" okButtonProps={{ disabled: !mergeTarget }}
      >
        <div style={{ marginBottom: 8, fontSize: 13 }}>
          被并入：<b>{mergeFrom?.question}</b>（合并后删除，其问题进目标相似问列）
        </div>
        <div style={fieldLabel}>并入目标（从库内其余问答中选）</div>
        <Select size="small" style={{ width: '100%' }} placeholder="选择目标问答…"
          value={mergeTarget} onChange={setMergeTarget}
          options={mergeTargets
            /* UI-04 T12：数据源换全库清单（openMerge 不带筛 getItems），排除条件照抄原行为 */
            .filter(r => r.id !== mergeFrom?.id && r.status !== 'pending_review')
            .map(r => ({ value: r.id, label: r.question }))} />
      </Modal>

      {/* 导入问答（端点 15——两模式＋试校验＋四计数） */}
      <Modal
        title={<span>导入问答{helpIcon(<>按模板批量导入历史答疑记录：模板列＝标准问 / 相似问法（多值） / 负例问法 / 答案；系统忽略大小写、全角半角差异后归一化去重；导入文件落对象存储不过期。</>)}</span>}
        open={impOpen} onCancel={() => setImpOpen(false)} footer={null} width={560}
      >
        <div style={{ fontSize: 13 }}>导入模式</div>
        <Radio.Group style={{ marginTop: 6 }} value={impMode} onChange={e => setImpMode(e.target.value)}>
          <Radio value="append">合并重复条目（与库内同义问法自动归并）</Radio>
          <Radio value="replace">替换全部（清空现库后导入，先确认）</Radio>
        </Radio.Group>
        <div style={{ marginTop: 10 }}>
          <Checkbox checked={impDry} onChange={e => setImpDry(e.target.checked)}>仅校验不入库（先试一遍看结果）</Checkbox>
        </div>
        <div style={{ marginTop: 10 }}>
          <Upload maxCount={1} beforeUpload={file => { setImpFile(file); return false }}
            onRemove={() => setImpFile(null)} accept=".csv">
            <Button size="small">选择 CSV 模板文件</Button>
          </Upload>
        </div>
        <Button type="primary" size="small" style={{ marginTop: 12 }} loading={impBusy}
          disabled={!impFile} onClick={runImport}>
          {impDry ? '开始校验' : '开始导入'}
        </Button>
        {impResult && (
          <Alert style={{ marginTop: 12 }} showIcon
            type={impResult.dryRun ? 'info' : 'success'} message={impResult.hint} />
        )}
      </Modal>

      {/* 候选问题库（半自动管线：扫库异步→候选库→向量比对→LLM 起草→对接新增弹窗→人审核入库） */}
      <Modal
        title={<span>候选问题库{helpIcon(<>候选来自 A1 问一问历史会话的 LLM 挖掘（统计周期：近 30 天）；簇频次过阈值才进候选（晋升闸）。「扫库」是异步长任务——关掉弹窗它也在跑，重开看结果。LLM 只起草，入库永远人点。</>)}</span>}
        open={mineOpen} onCancel={() => setMineOpen(false)} footer={null} width={860}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <Space wrap size={8}>
            <Button type="primary" size="small" icon={<SyncOutlined spin={scanning} />}
              disabled={scanning} onClick={runScan}>{scanning ? '正在扫库…' : '扫库'}</Button>
            <Select size="small" style={{ width: 128 }} value={mineF} onChange={setMineF}
              options={[
                { value: 'all', label: '状态：全部' },
                { value: 'pending', label: '待比对' },
                { value: 'dup', label: '疑似重复' },
                { value: 'ok', label: '可入库' },
                { value: 'drafted', label: '草稿待入库' },
                { value: 'published', label: '已发布' }
              ]} />
          </Space>
          <span style={dim}>候选 {candTotal} 簇 · 按频次排序</span>
        </div>
        {scanning && (
          <Alert style={{ marginBottom: 12 }} type="info" showIcon
            message="正在扫描用户问句库（聚类＋频次统计）……可关闭弹窗继续其他操作，扫描不会中断；重开弹窗看结果。" />
        )}
        {!scanning && (scanMsg || lastHint) && (
          <Alert style={{ marginBottom: 12 }} type="success" showIcon message={scanMsg || lastHint} />
        )}
        {/* UI-04 T7：候选表接 PagedTable client 模式（pageSize 20、统计恒显）；自绘
            expandIcon 原样透传（B3.test 钉 .ant-table-row-expand-icon）；resetKey=mineF
            （方案 §2.2 总表）；T13 loading 接线（对照主表先例） */}
        <PagedTable
          size="small" rowKey="id" dataSource={cands} loading={candLoading}
          resetKey={mineF}
          expandable={{
            rowExpandable: c => !!c.compare, // 没有比对结果就不显示展开按钮（合同）
            expandIcon: ({ expandable: can, onExpand, record }) =>
              can ? (
                <span role="button" tabIndex={0} aria-label="展开行"
                  className="ant-table-row-expand-icon"
                  onClick={e => onExpand(record, e)} />
              ) : (
                <span style={{ display: 'inline-block', width: 17 }} />
              ),
            expandedRowRender: c => (
              <Alert type={c.compare.verdict === 'dup' ? 'warning' : 'success'} showIcon
                message={c.compare.hint} />
            )
          }}
          columns={[
            {
              title: '候选问题',
              dataIndex: 'question',
              render: (v, c) => (
                <div>
                  <b style={{ fontSize: 13 }}>{v}</b>
                  <div style={dim}>{c.variants.length ? `同簇变体：${c.variants.join('、')}` : '无同簇变体'}</div>
                </div>
              )
            },
            {
              title: '频次', width: 90,
              render: (_, c) => <span>{c.freq} 次 <span style={dim}>近30天</span></span>
            },
            { title: '状态', width: 104, render: (_, c) => candTag(c) },
            {
              title: '操作', width: 190, align: 'center',
              render: (_, c) => (
                <Space size={4}>
                  <Tooltip title="向量比对：对既有问答/知识库/本体三面去重">
                    <Button size="small" icon={<ClusterOutlined />} aria-label={`比对：${c.question}`}
                      disabled={c.status !== 'pending'} loading={busyCand === c.id}
                      onClick={() => runCompare(c)} />
                  </Tooltip>
                  {c.status === 'drafted' ? (
                    <Button size="small" type="primary"
                      onClick={() => {
                        setPendingCand(c.id)
                        setQ(`${c.question}？`)
                        setA(c.draft || '')
                        setHook(c.hook ? c.hook.name : '')
                        setTip(null)
                        setMineOpen(false)
                        setAddOpen(true)
                        loadRefOptions()
                      }}>填入新增</Button>
                  ) : (
                    <Tooltip title="LLM 起草（分析该问题的历史回答）→ 草稿自动填入「新增问答」">
                      <Button size="small" icon={<RobotOutlined />} aria-label={`起草：${c.question}`}
                        disabled={c.status !== 'compared'} loading={busyCand === c.id}
                        onClick={() => runMineDraft(c)} />
                    </Tooltip>
                  )}
                </Space>
              )
            }
          ]}
        />
      </Modal>

      {/* 详情弹窗（端点 2/5/6——相似问逐条增删＋维护人/版本行） */}
      <Modal
        title={detail && <Space>{detail.question}{stateTag(detail.status)}</Space>}
        open={!!detail} onCancel={() => setDetail(null)} width={640} footer={null}
      >
        {detail && (
          <>
            <div style={{ marginBottom: 8, fontSize: 13 }}>
              <b>答案</b>
              <div style={{ marginTop: 4 }}>{detail.answer}</div>
            </div>
            <div style={{ marginBottom: 4 }}>
              {detail.status === 'pending_review' && <span style={dim}>待审核发布：发布后才被问一问消费。</span>}
              {detail.status === 'negative' && <span style={dim}>登记为"不该答的问题"：不参与回答，检索也不可达。</span>}
              {detail.status === 'disabled' && <span style={dim}>暂不参与回答，可随时启用。</span>}
            </div>
            <div style={{ marginTop: 14, fontWeight: 600, fontSize: 13 }}>
              相似问法
              {helpIcon(<>每个相似问法是独立检索项：逐条增删即时生效，删掉的问法不再命中本条。</>)}
            </div>
            <div style={{ marginTop: 6 }}>
              {detail.similarQuestions.map(s => (
                <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 0' }}>
                  <span style={{ fontSize: 13, flex: 1 }}>{s.text}</span>
                  <Button size="small" type="text" danger
                    onClick={() => removeSim(s.id)}>删除</Button>
                </div>
              ))}
              {!detail.similarQuestions.length && <span style={dim}>暂无相似问法。</span>}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6 }}>
                <Input size="small" style={{ flex: 1 }} value={newSim}
                  onChange={e => setNewSim(e.target.value)}
                  onPressEnter={addSim}
                  placeholder="添加相似问法（如主任的另一种问法）…" />
                <Button size="small" onClick={addSim}>添加</Button>
              </div>
            </div>
            <div style={{ marginTop: 14, color: '#8a94a3', fontSize: 12 }}>
              维护人：{detail.maintainer}（审核后生效） · 更新时间：{detail.updatedAt} · 版本 v{detail.version}（每次更新自增）
            </div>
          </>
        )}
      </Modal>
    </div>
  )
}
