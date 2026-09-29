import { useState } from 'react'
import {
  Alert, Button, Card, Checkbox, Input, message, Modal, Radio, Select, Space, Table, Tag, Tooltip
} from 'antd'
import {
  ClusterOutlined, ExportOutlined, FileSearchOutlined, ImportOutlined, MergeOutlined,
  PauseCircleOutlined, PlayCircleOutlined, PlusOutlined, QuestionCircleOutlined,
  RobotOutlined, SettingOutlined, SyncOutlined
} from '@ant-design/icons'
// 台账同源纪律（票 93）：关联口径与起草源选项来自 C1 命名导出，切片来源来自 B2 命名导出，禁止另抄
import { METRICS, TERMS, metricLabel } from './C1.jsx'
import { REPORTS } from './B2.jsx'

window.__guides = Object.assign(window.__guides || {}, {
  B3: [
    '顶部"状态"筛：全部 / 服务中 / 负例 / 已停用；红色"负例 · 不参与回答"的行永不参与回答。',
    '看"老完成率"那行——灰色"已停用"：口径改版后旧条目先停用待审（"老完成率"已登记为禁用词），行尾可再启用。',
    '点"完成率公式"行尾的合并图标——它并入「产量完成率怎么算」，列表少一条，两种问法命中同一条答案。',
    '工具栏「从问句挖掘」开候选问题库：候选来自用户真实提问（簇频次过晋升闸）。「扫库」是异步长任务——关掉弹窗也在跑，重开看结果；候选点比对（向量去重）再点起草——草稿自动填入「新增问答」，人改后入库。',
    '点"新增问答"——引用知识（台账口径/切片，可组合）→ 点"LLM 起草"形成草稿 → 改完入库；不选知识手填也行。',
    '把问题改成已有问答的同义问法（如"完成率公式是什么"）再点入库：出现"疑似重复"警告，不阻断、建议合并。',
    '勾上"登记为负例"再入库——新行标红、不参与回答。',
    '行尾"详情"或双击行——相似问法可逐条增删；底部看维护人与版本。',
    '工具栏"导入"——选合并重复/替换全部模式，可勾"仅校验不入库"先试校验，出结果统计；"导出"把全库带走线下编辑后再导回。',
    '工具栏"检索配置"——扩检轮数（每轮翻倍最多 5 轮）等规则，弹窗里改、保存生效；页头 ? 悬浮看本库与考核题库怎么分账。'
  ]
})
window.__traces = Object.assign(window.__traces || {}, {
  B3: 'F35 FAQ/管理面（停用启停·导入导出·重复校验·相似问增删，票 104）· m6 卡'
})

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

const SERVE_TAG = <Tag color="green">服务中</Tag>
const NEG_TAG = <Tag color="red">负例 · 不参与回答</Tag>
const DISABLED_TAG = <Tag>已停用 · 不参与回答</Tag>
const stateTag = r => (r.neg ? NEG_TAG : r.disabled ? DISABLED_TAG : SERVE_TAG)

const SIMILAR_HELP = '相似问法＝同一个问题的其他问法，已并入本条目——换这些问法来问，命中同一条答案；详情里可逐条增删，导入历史问答时也会自动按语义合并重复条目。'
const STATUS_HELP = '服务中＝正常参与回答，命中即秒回；已停用＝暂不参与回答（口径改版等场景先停用待审），可随时启用；负例＝登记在案的"不该答的问题"，不参与回答，检索也找不到。'
const POSITION_HELP = (
  <>
    本库收"用户常问、答案明确"的问答，是<b>服务资产</b>：命中直接秒回，不走报告检索；答案由小李维护、审核后生效。<br />
    给平台打分用的标准问答是另一本账——考核题库（<b>评估资产</b>）：标准问法＋人工算好的标准答案，只用于给平台打分、不直接服务用户。两本账分开维护、可互转不混用。<br />
    考核题库入口：<a href="#/E1">答题考核（评估集）</a>。
  </>
)

// 轻归一化：去首尾空白、忽略大小写/全半角标点差异后比对（入库前重复校验用）
const norm = s => (s || '').trim().toLowerCase().replace(/\s+/g, '').replace(/[？?！!。.,，]/g, '')

// 库内问答：内容全部取自平台既有业务事实（完成率口径 / 躺井 / 投产日期 / 原油密度折算 / N-11 状态 / 递减增油 / 油价预测负例 / 禁用词"老完成率"停用条目）
const INITIAL_ROWS = [
  { key: 1, q: '产量完成率怎么算？', a: 'Σ实际产油 ÷ Σ计划配产 × 100%（按月、按区块或油田；负责人：开发室）', sims: ['「月度完成率口径」（主任常问）'], neg: false, disabled: false },
  { key: 2, q: '完成率公式是什么？', a: 'Σ实际产油 ÷ Σ计划配产 × 100%（与上一条同义，待合并）', sims: [], neg: false, disabled: false },
  { key: 3, q: '"躺井"是什么意思？', a: '停产待检泵，作业区口语（限作业区语境；Owner：采油工艺所）', sims: ['「躺井啥意思」'], neg: false, disabled: false },
  { key: 4, q: 'N-02 井是什么时候投产的？', a: '2019-06-15 投产。', sims: [], neg: false, disabled: false },
  { key: 5, q: '渤中区块的原油密度按多少折算？', a: '0.89 t/m³；吨↔方换算＝质量÷密度（渤南 0.86 / 渤西 0.91）。', sims: [], neg: false, disabled: false },
  { key: 6, q: 'N-11 井现在什么状态？', a: '停产：2026-08-30 起检泵。', sims: [], neg: false, disabled: false },
  { key: 7, q: '递减增油怎么算？', a: '按「递减增油」口径模板计算；多井受效时按劈分系数（Σ=1）分摊。', sims: [], neg: false, disabled: false },
  { key: 8, q: '"老完成率"是什么口径？', a: '旧口径条目，已随口径改版停用——"老完成率"已登记为禁用词，现行口径见「产量完成率怎么算」。', sims: [], neg: false, disabled: true },
  { key: 9, q: '帮我预测明年油价', a: '（负例：不回答。库里登记为"不该答的问题"）', sims: ['「油价预测」'], neg: true, disabled: false }
]

// 待合并对：把「完成率公式」并入「产量完成率怎么算」
const MERGE_FROM = 2
const MERGE_TO = 1

export default function B3() {
  const [rows, setRows] = useState(INITIAL_ROWS)
  const [statusF, setStatusF] = useState('all') // all | serve | neg | disabled
  const [kw, setKw] = useState('')
  const [sel, setSel] = useState(null)
  const [openKey, setOpenKey] = useState(null)
  const [cfgOpen, setCfgOpen] = useState(false)

  // 新增问答（含负例登记 + 重复校验 + 引用知识→LLM 起草）
  const [addOpen, setAddOpen] = useState(false)
  const [q, setQ] = useState('配注合格率是什么？')
  const [a, setA] = useState('分层实注÷配注，达标井次占比（Owner：采油工艺所）')
  const [neg, setNeg] = useState(false)
  const [tip, setTip] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [refLedger, setRefLedger] = useState(null) // 引用知识：台账口径
  const [refSlice, setRefSlice] = useState(null) // 引用知识：切片原文
  const [draftLdg, setDraftLdg] = useState(false)
  const [hook, setHook] = useState('') // 关联口径/术语（''＝不挂接）

  const LEDGER_OPTIONS = [
    ...METRICS.map(m => ({ value: 'm' + m.key, label: `指标卡 · ${metricLabel(m.name)}` })),
    ...TERMS.map(t => ({ value: 't' + t.key, label: `术语 · ${t.term}` }))
  ]
  const HOOK_OPTIONS = [
    { value: '', label: '不挂接' },
    ...METRICS.map(m => ({ value: metricLabel(m.name), label: `指标 · ${metricLabel(m.name)}` })),
    ...TERMS.map(t => ({ value: t.term, label: `术语 · ${t.term}` }))
  ]
  // 切片引用扁平清单（B2 命名导出同源）
  const ALL_SLICES = REPORTS.flatMap(r => r.chunks.map((c, i) => ({
    value: `${r.key}-${i}`, label: `${r.doc}｜${c.type}｜${c.hit.slice(0, 14)}…`, chunk: c, doc: r.doc
  })))

  async function llmDraft() {
    if (!refLedger && !refSlice) return
    setDraftLdg(true)
    await new Promise(r => setTimeout(r, 800))
    const parts = []
    const m = METRICS.find(x => 'm' + x.key === refLedger)
    const t = TERMS.find(x => 't' + x.key === refLedger)
    if (m) {
      parts.push(`${m.def}${m.grain ? `——粒度 ${m.grain}` : ''}。（来源：C1 指标卡「${metricLabel(m.name)}」）`)
      setHook(metricLabel(m.name))
    } else if (t) {
      parts.push(`${t.def}。（来源：C1 术语台账「${t.term}」）`)
      setHook(t.term)
    }
    if (refSlice) {
      const s = ALL_SLICES.find(x => x.value === refSlice)
      if (s) parts.push(`${s.chunk.ctx}（来源：${s.doc} ${s.chunk.path}）`)
    }
    setA(parts.join('\n'))
    setDraftLdg(false)
  }

  // ── 候选问题挖掘（半自动管线：扫库异步→候选库→向量比对→LLM 起草→对接新增弹窗→人审核入库）──
  const [mineOpen, setMineOpen] = useState(false)
  const [cands, setCands] = useState([
    { key: 'c1', q: '产量完成率咋算的', variants: ['「完成率咋算的」', '「完成率怎么计算」'], freq: 23, status: 'pending' },
    { key: 'c2', q: '自然递减率怎么算', variants: ['「递减率公式」'], freq: 11, status: 'pending' },
    { key: 'c3', q: '时率是什么意思', variants: [], freq: 6, status: 'pending' }
  ])
  const [mineF, setMineF] = useState('all') // all | pending | dup | ok | drafted | published
  const [scanning, setScanning] = useState(false)
  const [scanMsg, setScanMsg] = useState(null)
  const [cmpOf, setCmpOf] = useState({}) // key → {dup, sim, onto, verdict}
  const [draftOf, setDraftOf] = useState({}) // key → 草稿文本（对接新增弹窗填入）
  const [draftKey, setDraftKey] = useState(null) // 比对/起草进行中的候选
  const [mineHook, setMineHook] = useState({}) // key → 关联口径
  const [pendingCand, setPendingCand] = useState(null) // 起草来源候选——新增弹窗入库后回写状态

  const CMP_RESULT = {
    c1: { dup: '产量完成率怎么算？', sim: '0.87', onto: '指标卡 · 产量完成率', verdict: 'dup' },
    c2: { dup: null, sim: null, onto: '指标卡 · 自然递减率', verdict: 'ok' },
    c3: { dup: null, sim: null, onto: '术语 · 时率', verdict: 'ok' },
    c4: { dup: null, sim: null, onto: '井对象 · N-02', verdict: 'ok' }
  }
  const DRAFT_RESULT = {
    c1: '（疑似重复——不建议新增，请改用清单里的合并相似问。）',
    c2: '月：1 − q_t / q_(t−1)（扣新井与措施增油）；年化：指数拟合 q(t)=q_i·e^(−Dt)——粒度 月 · 年 · %。（来源：C1 指标卡「自然递减率」· LLM 基于历史回答归纳，请人工核实）',
    c3: '「时率」＝"抽油机时率"的缩写，具体口径见指标卡 14。（来源：C1 术语台账「时率」· LLM 基于历史回答归纳，请人工核实）',
    c4: 'N-02 井的完井方式详见《N-02 井完井报告》章节 01——历史回答均引导至该报告原文。（来源：切片管理 · LLM 基于历史回答归纳，请人工核实）'
  }
  const MINE_HOOK = { c2: '自然递减率', c3: '时率', c4: '' }

  async function runScan() {
    setScanning(true)
    setScanMsg(null)
    await new Promise(r => setTimeout(r, 3000))
    setCands(cs => cs.some(c => c.key === 'c4') ? cs : [
      ...cs,
      { key: 'c4', q: 'N-02 的完井方式是啥', variants: ['「完井方式是啥」'], freq: 15, status: 'pending' }
    ])
    setScanning(false)
    setScanMsg('扫描完成：本次新增 1 个候选簇——「N-02 的完井方式是啥」（15 次 / 近30天）。')
  }

  async function runCompare(key) {
    setDraftKey(key) // 借用为比对 loading 位
    await new Promise(r => setTimeout(r, 700))
    setCmpOf(s => ({ ...s, [key]: CMP_RESULT[key] }))
    setCands(cs => cs.map(c => (c.key === key ? { ...c, status: 'compared' } : c)))
    setDraftKey(null)
  }

  async function runMineDraft(c) {
    setDraftKey(c.key)
    await new Promise(r => setTimeout(r, 900))
    setDraftOf(s => ({ ...s, [c.key]: DRAFT_RESULT[c.key] }))
    setMineHook(s => ({ ...s, [c.key]: MINE_HOOK[c.key] || '' }))
    setCands(cs => cs.map(x => (x.key === c.key ? { ...x, status: 'drafted' } : x)))
    setDraftKey(null)
    // 对接新增问答弹窗：草稿自动填入，人改后入库
    setPendingCand(c.key)
    setQ(c.q + '？')
    setA(DRAFT_RESULT[c.key])
    setHook(MINE_HOOK[c.key] || '')
    setTip(null)
    setMineOpen(false)
    setAddOpen(true)
    message.info('草稿已填入「新增问答」——请人工修改后入库。')
  }

  function openAddWithDraft(c) {
    setPendingCand(c.key)
    setQ(c.q + '？')
    setA(draftOf[c.key])
    setHook(mineHook[c.key] || '')
    setTip(null)
    setMineOpen(false)
    setAddOpen(true)
  }

  // 相似问合并 / 检索配置
  const [merged, setMerged] = useState(false)
  const [mergeMsg, setMergeMsg] = useState(null)
  const [rounds, setRounds] = useState(5)
  const [saved, setSaved] = useState(false)

  // 批量导入 / 导出
  const [impOpen, setImpOpen] = useState(false)
  const [impMode, setImpMode] = useState('append')
  const [impDry, setImpDry] = useState(false)
  const [impResult, setImpResult] = useState(null)

  // 详情内相似问增删
  const [newSim, setNewSim] = useState('')

  const filtered = rows.filter(r => {
    if (statusF === 'serve' && (r.neg || r.disabled)) return false
    if (statusF === 'neg' && !r.neg) return false
    if (statusF === 'disabled' && (!r.disabled || r.neg)) return false
    const s = kw.trim().toLowerCase()
    return !s || (r.q + r.a + r.sims.join('')).toLowerCase().includes(s)
  })

  const cur = rows.find(r => r.key === openKey)

  // 入库前重复校验（非阻断）：归一化后与既有问题/相似问比对
  const dupHit = (() => {
    const nq = norm(q)
    if (!nq) return null
    return rows.find(r => norm(r.q) === nq || r.sims.some(s => norm(s) === nq)) || null
  })()

  function submit() {
    setSubmitting(true)
    setTimeout(() => {
      const question = q.trim() || '（未填问题）'
      const answer = a.trim() || '（未填答案）'
      setRows(rs => [...rs, { key: Date.now(), q: question, a: answer, sims: [], neg, disabled: false }])
      if (pendingCand) {
        setCands(cs => cs.map(c => (c.key === pendingCand ? { ...c, status: 'published' } : c)))
        setTip({ kind: 'ok', text: `已入库：「${question}」——候选问题「${cands.find(c => c.key === pendingCand)?.q}」同步标记已发布。` })
      } else {
        setTip(neg
          ? { kind: 'neg', text: `已登记负例：「${question}」——永不参与回答，检索也不可达。` }
          : { kind: 'ok', text: `已入库：「${question}」——命中即秒回，不走报告检索。` })
      }
      setPendingCand(null)
      setSubmitting(false)
    }, 400)
  }

  function merge() {
    setRows(rs => rs.map(r => r.key === MERGE_TO
      ? { ...r, sims: [...r.sims, '「完成率公式」'] }
      : r).filter(r => r.key !== MERGE_FROM))
    setMerged(true)
    setSel(s => (s === MERGE_FROM ? MERGE_TO : s))
    setMergeMsg('已合并：2 条 → 1 条——「完成率公式」并入「产量完成率怎么算」，两种问法现在命中同一条答案。')
  }

  function toggleEnable(key) {
    setRows(rs => rs.map(r => (r.key === key ? { ...r, disabled: !r.disabled } : r)))
  }

  function removeSim(key, s) {
    setRows(rs => rs.map(r => (r.key === key ? { ...r, sims: r.sims.filter(x => x !== s) } : r)))
  }
  function addSim(key) {
    const v = newSim.trim()
    if (!v) return
    setRows(rs => rs.map(r => (r.key === key ? { ...r, sims: [...r.sims, v] } : r)))
    setNewSim('')
  }

  function runImport() {
    setImpResult({
      dry: impDry,
      text: impDry
        ? '试校验通过（未入库）：可新增 12 · 合并 3 · 跳过 2 · 失败 1（失败原因：1 行缺答案列——模板列必填）。'
        : '导入完成：新增 12 · 合并 3 · 跳过 2 · 失败 1（失败原因：1 行缺答案列——模板列必填）。'
    })
  }

  const cols = [
    { title: '问题', dataIndex: 'q', width: 240, render: v => <b style={{ fontSize: 13 }}>{v}</b> },
    { title: '答案', dataIndex: 'a', render: v => <span style={{ fontSize: 13 }}>{v}</span> },
    {
      title: <span>相似问法{helpIcon(SIMILAR_HELP)}</span>, dataIndex: 'sims', width: 250,
      render: (_, r) => <span style={{ color: '#8a94a3', fontSize: 12 }}>{r.sims.length ? r.sims.join(' · ') : '—'}</span>
    },
    {
      title: <span>状态{helpIcon(STATUS_HELP)}</span>, width: 150,
      render: (_, r) => stateTag(r)
    },
    {
      title: '操作', width: 118, align: 'center',
      render: (_, r) => (
        <Space size={4}>
          {r.key === MERGE_FROM && !merged && (
            <Tooltip title="合并相似问：并入「产量完成率怎么算」">
              <Button size="small" icon={<MergeOutlined />}
                onClick={e => { e.stopPropagation(); merge() }} />
            </Tooltip>
          )}
          {!r.neg && (
            r.disabled ? (
              <Tooltip title="启用：恢复参与回答，命中即秒回">
                <Button size="small" icon={<PlayCircleOutlined />}
                  onClick={e => { e.stopPropagation(); toggleEnable(r.key) }} />
              </Tooltip>
            ) : (
              <Tooltip title="停用：暂不参与回答、可再启用（口径改版等场景先停用待审）">
                <Button size="small" icon={<PauseCircleOutlined />}
                  onClick={e => { e.stopPropagation(); toggleEnable(r.key) }} />
              </Tooltip>
            )
          )}
          <Tooltip title="问答详情">
            <Button size="small" icon={<FileSearchOutlined />}
              onClick={e => { e.stopPropagation(); setSel(r.key); setOpenKey(r.key) }} />
          </Tooltip>
        </Space>
      )
    }
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card
        title={<span>问答清单（{rows.length}）</span>}
        extra={
          <Space size={4}>
            <span style={{ color: '#8a94a3', fontSize: 12 }}>常问问题直接秒回 · 不该答的登记负例永不参与 · 服务问答与考核题库分开两本账</span>
            {helpIcon(POSITION_HELP)}
          </Space>
        }
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <Space wrap size={8}>
            <Button type="primary" size="small" icon={<PlusOutlined />}
              onClick={() => { setTip(null); setPendingCand(null); setAddOpen(true) }}>新增问答</Button>
            <Button size="small" icon={<ClusterOutlined />}
              onClick={() => setMineOpen(true)}>从问句挖掘</Button>
            <Button size="small" icon={<ImportOutlined />}
              onClick={() => { setImpResult(null); setImpOpen(true) }}>导入</Button>
            <Button size="small" icon={<ExportOutlined />}
              onClick={() => message.success('已导出 FAQ 全库（含相似问/负例列）——可线下编辑后重新导入。')}>导出</Button>
            <Tooltip title="检索配置（扩检轮数 / 相似问合并 / 负例登记入口）">
              <Button size="small" icon={<SettingOutlined />} onClick={() => { setSaved(false); setCfgOpen(true) }} />
            </Tooltip>
            <Select size="small" style={{ width: 128 }} value={statusF} onChange={setStatusF}
              options={[
                { value: 'all', label: '状态：全部' },
                { value: 'serve', label: '服务中' },
                { value: 'neg', label: '负例' },
                { value: 'disabled', label: '已停用' }
              ]} />
            <Input size="small" allowClear style={{ width: 220 }} value={kw}
              onChange={e => setKw(e.target.value)} placeholder="搜问题 / 答案 / 相似问法…" />
          </Space>
          <span style={{ color: '#8a94a3', fontSize: 12 }}>{`筛选结果 ${filtered.length} / ${rows.length} 条`}</span>
        </div>
        <Table
          size="small" columns={cols} dataSource={filtered} pagination={false} rowKey="key"
          rowClassName={r => (r.key === sel ? 'ant-table-row-selected' : '')}
          onRow={r => ({
            onClick: () => setSel(r.key),
            onDoubleClick: () => { setSel(r.key); setOpenKey(r.key) },
            style: { cursor: 'pointer' }
          })}
        />
        {mergeMsg && <Alert style={{ marginTop: 12 }} type="success" showIcon message={mergeMsg} />}
      </Card>

      {/* 检索配置（按钮弹窗） */}
      <Modal
        title={<span>检索配置{helpIcon(<>问句没找到合适的候选时自动扩检：每轮候选数翻倍，最多 5 轮后停——不无限空转。</>)}</span>}
        open={cfgOpen} onCancel={() => setCfgOpen(false)} footer={null} width={520}
      >
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 13, marginBottom: 6 }}>候选不足时扩检轮数</div>
          <Space size={6}>
            <Input size="small" style={{ width: 64 }} value={rounds}
              onChange={e => setRounds(e.target.value.replace(/\D/g, ''))} />
            <span style={{ color: '#8a94a3', fontSize: 12 }}>每轮候选翻倍，最多 5 轮后停。</span>
          </Space>
        </div>
        <div style={{ marginBottom: 12 }}>
          <Space size={6}>
            <span style={{ fontSize: 13 }}>相似问合并</span>
            <Tag color="green">开</Tag>
            {helpIcon(<>自动按语义聚类把重复问法归到一条，合并前人工确认。</>)}
          </Space>
        </div>
        <div style={{ marginBottom: 4 }}>
          <Space size={6}>
            <span style={{ fontSize: 13 }}>负例登记入口</span>
            <Tag color="green">已开</Tag>
            {helpIcon(<>在"新增问答"里勾选"登记为负例"即可登记。</>)}
          </Space>
        </div>
        <Space style={{ marginTop: 12 }}>
          <Button type="primary" size="small" onClick={() => setSaved(true)}>保存配置</Button>
          {saved && <span style={{ fontSize: 12, color: '#8a94a3' }}>已保存。</span>}
        </Space>
      </Modal>

      <Modal
        title={<span>新增问答{helpIcon(<>常见问题一问一答直接入库：一条问答不走报告检索，命中即秒回；答案由小李维护，审核后生效。答案从来源起草、人改后入库——平台不自动生成 FAQ（不做自动挖掘）。问题或答案留空时按（未填问题）/（未填答案）登记。</>)}</span>}
        open={addOpen} onCancel={() => setAddOpen(false)} footer={null} width={620}
      >
        <Input size="small" value={q} onChange={e => setQ(e.target.value)} placeholder="问题" />
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 6 }}>
            引用知识（可组合、可留空）
            {helpIcon(<>答案不从空框里凭记忆写：选取台账口径/切片原文，LLM 基于所选知识起草，人改后入库——答案有据、错了能追溯到源。都不选则手填。</>)}
          </div>
          <Space wrap size={8}>
            <Select size="small" style={{ width: 230 }} placeholder="台账口径（可选）" allowClear
              value={refLedger} onChange={v => setRefLedger(v ?? null)} options={LEDGER_OPTIONS} />
            <Select size="small" style={{ width: 290 }} placeholder="切片原文（可选）" allowClear
              value={refSlice} onChange={v => setRefSlice(v ?? null)} options={ALL_SLICES} />
            <Button size="small" icon={<RobotOutlined />} loading={draftLdg}
              disabled={!refLedger && !refSlice}
              onClick={llmDraft}>LLM 起草</Button>
          </Space>
        </div>
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 4 }}>答案（草稿可改——确认权在人）</div>
          <Input.TextArea size="small" rows={3} value={a}
            onChange={e => setA(e.target.value)} placeholder="答案" />
        </div>
        <div style={{ marginTop: 8 }}>
          <Space size={6}>
            <span style={{ fontSize: 12, color: '#8a94a3' }}>关联口径</span>
            <Select size="small" style={{ width: 200 }} value={hook} onChange={setHook}
              options={HOOK_OPTIONS} />
            {helpIcon(<>挂上口径/术语后：口径修订生效时自动定位本条提示停用待审；答案命中过期术语时带漂移标注——秒回答案与报告答案一个标准。</>)}
          </Space>
        </div>
        {dupHit && (
          <Alert style={{ marginTop: 8 }} type="warning" showIcon message={
            <span>与既有问答「{dupHit.q}」疑似重复（系统忽略大小写、全角半角差异后比对）：建议改用合并相似问，或确认继续入库。</span>} />
        )}
        <div style={{ marginTop: 8 }}>
          <Checkbox checked={neg} onChange={e => setNeg(e.target.checked)}>
            登记为负例（"不该答的问题"，不参与回答）
          </Checkbox>
        </div>
        <Button type="primary" size="small" style={{ marginTop: 12 }} loading={submitting} onClick={submit}>
          入库
        </Button>
        {tip && (
          <Alert style={{ marginTop: 12 }} showIcon
            type={tip.kind === 'neg' ? 'warning' : 'success'} message={tip.text} />
        )}
      </Modal>

      {/* 批量导入（合并重复/替换全部 + 试校验） */}
      <Modal
        title={<span>导入问答{helpIcon(<>按模板批量导入历史答疑记录：模板列＝标准问 / 相似问法（多值） / 负例问法 / 答案；系统忽略大小写、全角半角差异后归一化去重。</>)}</span>}
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
        <Button type="primary" size="small" style={{ marginTop: 12 }} onClick={runImport}>
          {impDry ? '开始校验' : '开始导入'}
        </Button>
        {impResult && (
          <Alert style={{ marginTop: 12 }} showIcon
            type={impResult.dry ? 'info' : 'success'} message={impResult.text} />
        )}
      </Modal>

      {/* 候选问题库（半自动管线：扫库异步→候选库→向量比对→LLM 起草→对接新增弹窗→人审核入库） */}
      <Modal
        title={<span>候选问题库{helpIcon(<>候选来自用户真实提问的聚类（统计周期：近 30 天）；簇频次过阈值才进候选（晋升闸）。「扫库」是异步长任务——关掉弹窗它也在跑，重开看结果。LLM 只起草，入库永远人点。</>)}</span>}
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
          <span style={{ color: '#8a94a3', fontSize: 12 }}>候选 {cands.length} 簇 · 按频次排序</span>
        </div>
        {scanning && (
          <Alert style={{ marginBottom: 12 }} type="info" showIcon
            message="正在扫描用户问句库（聚类＋频次统计）……可关闭弹窗继续其他操作，扫描不会中断；重开弹窗看结果。" />
        )}
        {!scanning && scanMsg && (
          <Alert style={{ marginBottom: 12 }} type="success" showIcon message={scanMsg} />
        )}
        <Table
          size="small" pagination={false} rowKey="key"
          dataSource={cands.filter(c => {
            if (mineF === 'pending') return c.status === 'pending'
            if (mineF === 'dup') return c.status !== 'pending' && cmpOf[c.key]?.dup
            if (mineF === 'ok') return (c.status === 'compared' || c.status === 'drafted') && !cmpOf[c.key]?.dup
            if (mineF === 'drafted') return c.status === 'drafted'
            if (mineF === 'published') return c.status === 'published'
            return true
          })}
          expandable={{
            rowExpandable: c => !!cmpOf[c.key], // 没有比对结果就不显示展开按钮
            expandIcon: ({ expandable: can, onExpand, record }) =>
              can ? (
                <span role="button" tabIndex={0} aria-label="展开行"
                  className="ant-table-row-expand-icon"
                  onClick={e => onExpand(record, e)} />
              ) : (
                <span style={{ display: 'inline-block', width: 17 }} />
              ),
            expandedRowRender: c => {
              const cmp = cmpOf[c.key]
              return (
                <Alert type={cmp.dup ? 'warning' : 'success'} showIcon message={
                  <span>向量比对：{cmp.dup ? `与「${cmp.dup}」相似度 ${cmp.sim}——高于合并线，建议改用合并相似问，不新增条目。` : '与既有问答无重复。'}本体命中：{cmp.onto}。</span>} />
              )
            }
          }}
          columns={[
            {
              title: '候选问题', dataIndex: 'q',
              render: (v, c) => (
                <div>
                  <b style={{ fontSize: 13 }}>{v}</b>
                  <div style={{ fontSize: 12, color: '#8a94a3' }}>{c.variants.length ? `同簇变体：${c.variants.join('、')}` : '无同簇变体'}</div>
                </div>
              )
            },
            {
              title: '频次', width: 90,
              render: (_, c) => <span>{c.freq} 次 <span style={{ color: '#8a94a3', fontSize: 12 }}>近30天</span></span>
            },
            {
              title: '状态', width: 104,
              render: (_, c) => c.status === 'published' ? <Tag color="green">已发布</Tag>
                : c.status === 'drafted' ? <Tag color="blue">草稿待入库</Tag>
                : c.status === 'pending' ? <Tag>待比对</Tag>
                : cmpOf[c.key]?.dup ? <Tag color="orange">疑似重复</Tag>
                : <Tag color="green">可入库</Tag>
            },
            {
              title: '操作', width: 190, align: 'center',
              render: (_, c) => (
                <Space size={4}>
                  <Tooltip title="向量比对：对既有问答/知识库/本体三面去重">
                    <Button size="small" icon={<ClusterOutlined />}
                      disabled={c.status !== 'pending'} loading={draftKey === c.key}
                      onClick={() => runCompare(c.key)} />
                  </Tooltip>
                  {c.status === 'drafted' ? (
                    <Button size="small" type="primary" onClick={() => openAddWithDraft(c)}>填入新增</Button>
                  ) : (
                    <Tooltip title="LLM 起草（分析该问题的历史回答）→ 草稿自动填入「新增问答」">
                      <Button size="small" icon={<RobotOutlined />}
                        disabled={c.status !== 'compared'} loading={draftKey === c.key}
                        onClick={() => runMineDraft(c)} />
                    </Tooltip>
                  )}
                </Space>
              )
            }
          ]}
        />
      </Modal>

      <Modal
        title={cur && <Space>{cur.q}{stateTag(cur)}</Space>}
        open={!!cur} onCancel={() => setOpenKey(null)} width={640} footer={null}
      >
        {cur && (
          <>
            <Table size="small" pagination={false} rowKey="k"
              columns={[{ title: '项', dataIndex: 'k', width: 90 }, { title: '内容', dataIndex: 'v' }]}
              dataSource={[
                { k: '问题', v: <b style={{ fontSize: 13 }}>{cur.q}</b> },
                { k: '答案', v: <span style={{ fontSize: 13 }}>{cur.a}</span> },
                {
                  k: '状态',
                  v: (
                    <Space size={8}>
                      {stateTag(cur)}
                      {cur.neg && <span style={{ color: '#8a94a3', fontSize: 12 }}>登记为"不该答的问题"：不参与回答，检索也不可达。</span>}
                      {cur.disabled && !cur.neg && <span style={{ color: '#8a94a3', fontSize: 12 }}>暂不参与回答，可随时启用。</span>}
                    </Space>
                  )
                }
              ]}
            />
            <div style={{ marginTop: 14, fontWeight: 600, fontSize: 13 }}>
              相似问法
              {helpIcon(<>每个相似问法是独立检索项：逐条增删即时生效，删掉的问法不再命中本条。</>)}
            </div>
            <div style={{ marginTop: 6 }}>
              {(cur.sims.length ? cur.sims : []).map(s => (
                <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 0' }}>
                  <span style={{ fontSize: 13, flex: 1 }}>{s}</span>
                  <Button size="small" type="text" danger
                    onClick={() => removeSim(cur.key, s)}>删除</Button>
                </div>
              ))}
              {!cur.sims.length && <span style={{ color: '#8a94a3', fontSize: 12 }}>暂无相似问法。</span>}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6 }}>
                <Input size="small" style={{ flex: 1 }} value={newSim}
                  onChange={e => setNewSim(e.target.value)}
                  onPressEnter={() => addSim(cur.key)}
                  placeholder="添加相似问法（如主任的另一种问法）…" />
                <Button size="small" onClick={() => addSim(cur.key)}>添加</Button>
              </div>
            </div>
            <div style={{ marginTop: 14, color: '#8a94a3', fontSize: 12 }}>
              维护人：小李（审核后生效） · 更新时间：2026-09-26 · 版本 v2（每次更新自增）
            </div>
          </>
        )}
      </Modal>
    </div>
  )
}
