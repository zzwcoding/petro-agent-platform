import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button, Card, Drawer, Empty, Input, Modal, Select, Skeleton, Space, Spin, Steps, Switch, Table, Tabs, Tag, Tooltip
} from 'antd'
import { FileSearchOutlined, QuestionCircleOutlined, ThunderboltOutlined } from '@ant-design/icons'
// 数据与操作全部走 api 层（真后端接线 W-E2）：契约见 teach-petro-agent specs/api/E2-数据质量台.md v0.5，
// 页面组件不持有业务数据；错误包由 client.request 统一弹 toast——页面 catch 不重复弹
import { useTaskPolling, errText } from '../api/client.js'
import {
  LANES, getQualityRules, setQualityRuleEnabled, startQualityTask,
  listQualityTasks, listQualityIssues, transitionQualityIssue, getFreshness
} from '../api/quality.js'
import ClampCell from '../components/ClampCell.jsx'  // 共享件（表格单元格长文本截断——页内副本已删）

window.__traces = Object.assign(window.__traces || {}, { E2: 'F18 转换测试质量 · 设定书 §4 质检规则与任务 · m20 质量卡' })

const E_TABS = [
  { key: 'E1', label: '答题考核' },
  { key: 'E2', label: '数据质量台' },
  { key: 'E3', label: '知识体检' }
]

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: 'var(--pa-text-tertiary)', cursor: 'help' }} />
  </Tooltip>
)

const ITEM_COLS = [
  { title: '项', dataIndex: 'label', width: 96 },
  { title: '内容', dataIndex: 'body' }
]

export default function E2Quality() {
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null) // 首屏四拉取失败——内联失败态≠空态（client 已弹 toast）
  const [tab, setTab] = useState('rules')
  const [rules, setRules] = useState([])
  const [statusF, setStatusF] = useState('all')
  const [kindF, setKindF] = useState('all')
  const [kw, setKw] = useState('')
  const [step, setStep] = useState(-1)
  const [running, setRunning] = useState(false)
  const [pollFailed, setPollFailed] = useState(null) // 轮询收场 failed（连续两次拉取失败）——步进条 error 态
  const [taskId, setTaskId] = useState(null) // 受理 202 → useTaskPolling 接管轮询（202→tasks/{id} 至 done/failed）
  const [tasks, setTasks] = useState([])
  const [reportKey, setReportKey] = useState(null)
  const [issues, setIssues] = useState([])
  const [issueKey, setIssueKey] = useState(null)
  const [laneF, setLaneF] = useState('all')
  const [ownerF, setOwnerF] = useState('all')
  const [ruleF, setRuleF] = useState('all')
  const [kwIssue, setKwIssue] = useState('')
  const [water, setWater] = useState([])
  const [rescanId, setRescanId] = useState(null) // 复扫在途单 id——busy 态（M-09①）：按钮 disabled＋加载文案
  const runningRef = useRef(false)
  const rescanRef = useRef(null) // 复扫同 tick 守卫——闭包态未及更新前重复触发不重发

  const loadAll = useCallback(() => {
    let on = true
    setLoading(true)
    Promise.all([getQualityRules(), listQualityTasks(), listQualityIssues(), getFreshness()])
      .then(([rs, ts, is, ws]) => {
        if (!on) return
        setRules(rs.items)
        setTasks(ts.items)
        setIssues(is.items)
        setWater(ws.items)
        setLoadError(null)
        setLoading(false)
      })
      .catch(err => {
        if (!on) return
        setLoadError(err) // client 已弹错误包——页面内联失败态＋重试（不再重复 toast）
        setLoading(false)
      })
    return () => { on = false }
  }, [])

  useEffect(() => loadAll(), [loadAll])

  // 受理 202 → 底座轮询 tasks/{id}（1.5s 节奏＋容忍一次瞬时失败；onProgress 实时点亮步进）
  const { status: pollStatus, data: taskDone, error: pollError } = useTaskPolling(taskId, {
    path: '/quality/tasks',
    onProgress: d => {
      if (d.status === 'running') setStep(Math.min(typeof d.step === 'number' ? d.step : 0, 4))
    }
  })

  // 轮询收场：done → 任务记录入列＋开报告弹窗＋问题单刷新；failed → 步进条 error 态
  // （真后端 done 形 {taskId,status,task}——report 键为 snake_case，渲染层映射）
  useEffect(() => {
    if (pollStatus === 'done' && taskDone) {
      setStep(4)
      if (taskDone.task) {
        setTasks(prev => [taskDone.task, ...prev.filter(t => t.id !== taskDone.task.id)])
        setReportKey(taskDone.task.id)
      }
      listQualityIssues()
        .then(d => setIssues(d.items))
        .catch(() => { /* client 已弹错误包——单列表刷新失败不阻断收场，下次进入/重跑再取 */ })
    }
    if (pollStatus === 'failed') setPollFailed(pollError)
    if (pollStatus === 'done' || pollStatus === 'failed') {
      setRunning(false)
      runningRef.current = false
    }
  }, [pollStatus, taskDone, pollError])

  const enabledCount = rules.filter(r => r.enabled).length
  const kinds = [...new Set(rules.map(r => r.kind))]
  const reportTask = tasks.find(t => t.id === reportKey)
  const issueCard = issues.find(c => c.id === issueKey)

  function toggleRule(no) {
    const target = !rules.find(r => r.no === no).enabled
    setRules(prev => prev.map(r => (r.no === no ? { ...r, enabled: target } : r)))
    setQualityRuleEnabled(no, target).catch(() => {
      // client 已弹错误包（422 仅登记档拒启用 / 网络失败）——页面只做乐观回退，不重复 toast
      setRules(prev => prev.map(r => (r.no === no ? { ...r, enabled: !target } : r)))
    })
  }

  async function runTask() {
    if (runningRef.current) return
    runningRef.current = true
    setRunning(true)
    setPollFailed(null)
    setStep(0)
    setTaskId(null)
    try {
      const res = await startQualityTask() // 202 受理；409 重入错误包 client 已弹
      setTaskId(res.taskId) // 轮询至 done/failed——步值 0/2/4（受理/数据面报告回/建单分发完成）
    } catch {
      setRunning(false)
      setStep(-1)
      runningRef.current = false
    }
  }

  async function flowCard(id, action) {
    if (action === 'rescan' && rescanRef.current) return // 复扫在途（通道限时 10s）——不重发
    if (action === 'rescan') {
      rescanRef.current = id
      setRescanId(id)
    }
    try {
      const res = await transitionQualityIssue(id, action)
      setIssues(prev => prev.map(c => (c.id === id ? { ...c, lane: res.lane, verify: res.verify || c.verify } : c)))
    } catch {
      // client 已弹错误包（409 终态/重入 / 422 关闭守卫 / 501 复扫通道超时）——页面无状态需回退
    } finally {
      if (action === 'rescan') {
        rescanRef.current = null // 完成/失败都解除 busy
        setRescanId(null)
      }
    }
  }

  const filteredRules = rules.filter(r => {
    const st = r.enabled ? 'on' : 'off'
    const q = kw.trim().toLowerCase()
    return (statusF === 'all' || st === statusF)
      && (kindF === 'all' || r.kind === kindF)
      && (!q || (String(r.no) + r.kind + r.rule + r.crit).toLowerCase().includes(q))
  })

  const ruleColumns = [
    {
      title: (<span>开关{helpIcon(<>停用＝质检任务跳过它，不删规则；停用后整行置灰，再点开关恢复启用。</>)}</span>),
      dataIndex: 'enabled', width: 110,
      render: (on, rule) => (
        <Switch
          size="small" checked={on}
          checkedChildren="启用中" unCheckedChildren="已停用"
          onChange={() => toggleRule(rule.no)}
        />
      )
    },
    { title: '#', dataIndex: 'no', width: 44 },
    { title: '查什么', dataIndex: 'kind', width: 110 },
    {
      title: '规则', dataIndex: 'rule',
      render: v => <ClampCell text={v} />
    },
    {
      title: (<span>命中动作{helpIcon(<>命中后怎么处理，三档：<br />· <b>隔离</b>——坏行不进湖，落隔离区待整改（可追溯）<br />· <b>整批拒收</b>——批次级故障整批拒绝（schema 级故障专用档）<br />· <b>告警</b>——不拦行，通知人工核实（重复/矛盾/恒值/对账类）<br />规则 13–20 为通用规则族，仅登记不实施（开关不可启用），动作见规则库总册。</>)}</span>),
      dataIndex: 'action', width: 92
    },
    {
      title: (<span>自动修{helpIcon(<>仅"安全类"可自动修复：写法归一 / 枚举映射——只作用于派生层，原始坏行永留隔离区。<br />金额 / 口径 / 歧义类绝不自动修。</>)}</span>),
      dataIndex: 'autoFix', width: 76,
      render: v => (v ? '✓ 安全类' : '—')
    },
    {
      title: (<span>判据 · 阈值{helpIcon(<>
        <b>规则分三层</b>：通用规则 → 挂到具体字段的规则 → 场景专项规则。<br />
        前 12 条挂着具体判据、在生产库 8 张表上跑；第 13–20 条是通用规则族（仅登记不实施——V1 任务只跑 1–12），判据补齐走治理批。
      </>)}</span>),
      dataIndex: 'crit', width: 200,
      render: v => <ClampCell text={v} />
    }
  ]

  const pageTabs = [
    { key: 'rules', label: `规则库（${rules.length}）` },
    { key: 'task', label: `质检任务（${tasks.length}）` },
    {
      key: 'issues',
      label: (
        <span>
          问题单（{issues.length}）
          <span onClick={e => e.stopPropagation()}>
            {helpIcon(<>
              问题单从「分发」一路走到「关闭」：分发 → 认领 → 整改 → 复核 → 关闭；推进到「复核」仅登记待复扫，复扫由人触发、结论回填复验列，复扫全绿才允许关闭。<br />
              表格管理：上方状态页签按五格计数联动，责任岗 / 规则筛选 + 关键字搜索；行内「流转 →」推到下一格，点行开详情抽屉。
            </>)}
          </span>
        </span>
      )
    },
    {
      key: 'water',
      label: (
        <span>
          数据到哪天（{water.length}）
          <span onClick={e => e.stopPropagation()}>
            {helpIcon(<>
              <b>T-1＝昨天的数今天要能看到</b>（示例以 2026-09-15 为今天）。<br />
              原始 / 清洗层水位到 09-14，达标；汇总层是问数用的表——停在 09-11，欠基准水位 3 天的账（09-14 − 09-11），问「最近三天产量」就答不齐。
            </>)}
          </span>
        </span>
      )
    }
  ]

  // 步进条文案：真接口 hits 任务完成才可知（撤 mock 硬编码「命中 3 条」）；
  // current 映射服务端步值 0/2/4＝受理扫描 / 数据面报告回（开单前）/ 建单分发完成
  const flowSteps = [
    '扫描生产库 8 张表',
    `逐条跑规则（${enabledCount} 条启用）`,
    '命中开成问题单',
    '按责任岗自动分发'
  ]

  return (
    <div>
      <Tabs activeKey="E2" items={E_TABS} onChange={k => { location.hash = '/' + k }} style={{ marginBottom: 16 }} />

      <Card
        title={
          <Tabs activeKey={tab} size="small" onChange={setTab} items={pageTabs} />
        }
      >
        {/* 全局规则/治理链：POLISH-SPEC 三-1「一行灰字放 Card 顶部或 extra」。
            改造前它挂在 card 的 extra 里，与卡片标题（页签名）同处一行、同等视觉权重，
            一行 60 字把标题压了下去；现改为独立成行——标题行只留页签名，
            规则链另起一带（组外间距 > 组内间距，§3.6），文字一字未删。 */}
        <div style={{
          display: 'flex', alignItems: 'flex-start', gap: 4,
          marginBottom: 16, color: 'var(--pa-text-tertiary)', fontSize: 12, lineHeight: 1.8,
        }}>
          <span>
            停用规则＝任务跳过、不删 · 命中开成问题单：分发 → 认领 → 整改 → 复核（人工触发复扫）→ 关闭 · 问数看汇总层数据到哪天
          </span>
          {helpIcon(<>
            <b>数据质量岗的日常台面</b><br />
            · 规则库管查什么毛病，开关启停即生效；<br />
            · 质检任务一键体检生产库，出合规报告；<br />
            · 命中的问题自动开成问题单，按责任岗分发、跟到关闭；<br />
            · 数据到哪天一眼看清，问数的表以汇总层为准。
          </>)}
        </div>
        {loading ? (
          <Skeleton active paragraph={{ rows: 9 }} />
        ) : loadError ? (
          <Empty description={<span>数据加载失败——{errText(loadError)}</span>}>
            <Button size="small" onClick={loadAll}>重试</Button>
          </Empty>
        ) : (
          <>
            {tab === 'rules' && (
              <>
                <Space wrap style={{ marginBottom: 12 }}>
                  <Select
                    size="small" style={{ width: 124 }} value={statusF} onChange={setStatusF}
                    options={[
                      { value: 'all', label: '状态：全部' },
                      { value: 'on', label: '启用中' },
                      { value: 'off', label: '已停用' }
                    ]}
                  />
                  <Select
                    size="small" style={{ width: 170 }} showSearch value={kindF} onChange={setKindF}
                    optionFilterProp="label"
                    options={[{ value: 'all', label: '查什么：全部' }, ...kinds.map(k => ({ value: k, label: k }))]}
                  />
                  <Input size="small" allowClear style={{ width: 220 }} value={kw}
                    onChange={e => setKw(e.target.value)} placeholder="搜规则 / 判据…" />
                  <span style={{ fontSize: 12, color: 'var(--pa-text-tertiary)' }}>
                    筛选结果 {filteredRules.length} / {rules.length} 条
                  </span>
                </Space>
                <Table
                  size="small"
                  columns={ruleColumns}
                  dataSource={filteredRules}
                  rowKey="no"
                  pagination={false}
                  onRow={r => (r.enabled ? {} : { style: { opacity: 0.45, background: 'rgba(255,255,255,0.04)' } })}
                />
              </>
            )}

            {tab === 'task' && (
              <>
                <Space wrap style={{ marginBottom: 12 }}>
                  <Button type="primary" size="small" icon={<ThunderboltOutlined />} onClick={runTask}>
                    发起质检任务（跑一遍启用中的 {enabledCount} 条）
                  </Button>
                  {running && <Spin size="small" />}
                  {helpIcon(<>
                    <b>岗位三角</b>：数字化室配置入湖强制规则、出合规性报告；质量管理员（小李）配置质检任务、复检、出报告；采集管理员（作业区资料员）管源头数据。<br />
                    跑完命中的问题自动开成问题单、按责任岗分发；重跑只清「分发未认领」的动态单（处理中的单保留、新命中挂同单）再开新单，历史任务记录保留可回看。
                  </>)}
                </Space>
                <Steps
                  size="small" current={step < 0 ? 0 : step}
                  status={step < 0 ? 'wait' : pollFailed ? 'error' : running ? 'process' : 'finish'}
                  items={flowSteps.map(t => ({ title: t }))}
                />
                {pollFailed && (
                  <div style={{ marginTop: 8, fontSize: 12, color: 'var(--pa-danger)' }}>
                    质检任务收场失败——{errText(pollFailed)}（可重新发起）
                  </div>
                )}
                <Table
                  size="small" style={{ marginTop: 16 }} rowKey="id" pagination={false}
                  dataSource={tasks}
                  locale={{ emptyText: <Empty description="暂无质检任务——点上方按钮发起第一遍体检（空库即验收态）" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                  columns={[
                    { title: '任务号', dataIndex: 'id', width: 170 },
                    { title: '发起时间', dataIndex: 'time', width: 150 },
                    { title: '检查范围', width: 110, render: (_, t) => t.report?.range ?? '—' },
                    { title: '扫描行数', width: 100, render: (_, t) => t.report?.scanned ?? '—' },
                    { title: '启用规则', width: 90, render: (_, t) => `${t.rules ?? '—'} 条` },
                    { title: '命中', width: 70, render: (_, t) => <b>{t.hits ?? '—'}</b> },
                    { title: '隔离/拒收', width: 96, render: (_, t) => (t.report ? `${t.report.quarantined_rows ?? 0} 行 / ${t.report.rejected_batches ?? 0} 批` : '—') },
                    {
                      title: '操作', width: 90, align: 'center',
                      render: (_, t) => (
                        <Button size="small" icon={<FileSearchOutlined />} onClick={() => setReportKey(t.id)}>报告</Button>
                      )
                    }
                  ]}
                />
              </>
            )}

            {tab === 'issues' && (() => {
              const roleOf = o => (o ?? '—').split('：').pop() // owner 可空（DTO str|null）——筛选项兜底
              const owners = [...new Set(issues.map(c => roleOf(c.owner)))]
              const ruleNos = [...new Set(issues.map(c => c.rule_no))].sort((a, b) => a - b)
              const laneCount = li => issues.filter(c => c.lane === li).length
              const q = kwIssue.trim().toLowerCase()
              const filteredIssues = issues.filter(c =>
                (laneF === 'all' || c.lane === laneF)
                && (ownerF === 'all' || roleOf(c.owner) === ownerF)
                && (ruleF === 'all' || c.rule_no === ruleF)
                && (!q || (c.title + c.desc).toLowerCase().includes(q)))
              return (
                <>
                  <Tabs size="small" activeKey={String(laneF)}
                    onChange={k => setLaneF(k === 'all' ? 'all' : Number(k))}
                    items={[
                      { key: 'all', label: `全部（${issues.length}）` },
                      ...LANES.map((l, li) => ({ key: String(li), label: `${l}（${laneCount(li)}）` }))
                    ]} style={{ marginBottom: 8 }} />
                  <Space wrap style={{ marginBottom: 12 }}>
                    <Select size="small" style={{ width: 170 }} value={ownerF} onChange={setOwnerF}
                      options={[{ value: 'all', label: '责任岗：全部' }, ...owners.map(o => ({ value: o, label: `责任岗：${o}` }))]} />
                    <Select size="small" style={{ width: 130 }} value={ruleF} onChange={setRuleF}
                      options={[{ value: 'all', label: '规则：全部' }, ...ruleNos.map(n => ({ value: n, label: `规则 ${n}` }))]}> </Select>
                    <Input size="small" allowClear style={{ width: 220 }} value={kwIssue}
                      onChange={e => setKwIssue(e.target.value)} placeholder="搜问题单 / 描述…" />
                    <span style={{ fontSize: 12, color: 'var(--pa-text-tertiary)' }}>筛选结果 {filteredIssues.length} / {issues.length} 条</span>
                  </Space>
                  <Table size="small" rowKey="id" pagination={false}
                    dataSource={filteredIssues}
                    onRow={c => ({ onClick: () => setIssueKey(c.id), style: { cursor: 'pointer' } })}
                    columns={[
                      { title: '问题单', dataIndex: 'title' },
                      { title: '规则', dataIndex: 'rule_no', width: 64, render: v => `#${v}` },
                      { title: '责任岗', dataIndex: 'owner', width: 160 },
                      {
                        title: '当前环节', dataIndex: 'lane', width: 90,
                        render: l => <Tag color={l === LANES.length - 1 ? 'green' : 'default'}>{LANES[l]}</Tag>
                      },
                      {
                        title: (<span>命中{helpIcon(<>同类失败挂同单：再次命中不重复开单，命中次数 +1。</>)}</span>),
                        dataIndex: 'hit_count', width: 60, render: v => (v > 1 ? <b>{v}</b> : v)
                      },
                      { title: '隔离行', width: 76, render: (_, c) => (c.qrows?.length ? `${c.qrows.length} 行` : '—') },
                      {
                        title: (<span>复验{helpIcon(<>推进到「复核」后点行内「复扫」对修正批次重跑质检，全绿才允许关闭（v0.5 人工触发）</>)}</span>),
                        width: 92, render: (_, c) => (c.verify ? '✓ 已复扫' : c.close_note ? '免修关闭' : '—')
                      },
                      {
                        title: '操作', width: 150, align: 'center',
                        render: (_, c) => (c.lane === LANES.length - 1
                          ? <Button size="small" disabled>已关闭</Button>
                          : (
                            <Space size={4}>
                              {c.lane === 3 && !c.verify && (
                                <Button
                                  size="small" disabled={rescanId === c.id}
                                  onClick={e => { e.stopPropagation(); flowCard(c.id, 'rescan') }}
                                >
                                  {rescanId === c.id ? '复扫中…' : '复扫'}
                                </Button>
                              )}
                              <Button size="small" onClick={e => { e.stopPropagation(); flowCard(c.id) }}>流转 →</Button>
                            </Space>
                          ))
                      }
                    ]}
                    locale={{ emptyText: <Empty description="该状态下暂无问题单" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }} />
                </>
              )
            })()}

            {tab === 'water' && (
              <Table
                size="small" pagination={false} rowKey="layer"
                locale={{ emptyText: <Empty description="暂无水位数据——水位由入湖/加工管道回写后呈现（空库即如实空行）" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                columns={[
                  { title: '层', dataIndex: 'layer', width: 200, render: v => <b>{v}</b> },
                  { title: '数据到', dataIndex: 'to', width: 160 },
                  { title: (<span>承诺水位{helpIcon(<>T-1＝昨天的数今天要能看到；三层同按 T-1 兑现，汇总层落后即标超期。</>)}</span>), dataIndex: 'promise', width: 110 },
                  { title: '状态', dataIndex: 'tag', render: (v, w) => <Tag color={w.color}>{v}</Tag> }
                ]}
                dataSource={water}
              />
            )}
          </>
        )}
      </Card>

      <Modal
        title={reportTask && `合规报告（质检任务 #${reportTask.id} · ${reportTask.time}）`}
        open={!!reportTask} onCancel={() => setReportKey(null)} footer={null} width={680}
      >
        {reportTask && (
          <>
            <Table size="small" pagination={false} columns={ITEM_COLS} rowKey="label"
              dataSource={[
                { label: '检查范围', body: reportTask.report?.range ?? '—' },
                { label: '扫描行数', body: reportTask.report?.scanned ?? '—' },
                { label: '启用规则', body: `${reportTask.rules ?? '—'} 条` },
                {
                  label: '隔离 / 拒收',
                  body: `隔离 ${reportTask.report?.quarantined_rows ?? 0} 行 · 整批拒收 ${reportTask.report?.rejected_batches ?? 0} 个批次——坏数据不进湖，落隔离区可追溯`
                },
                {
                  label: '命中明细',
                  body: <div>{(reportTask.report?.hits ?? []).map(h => <div key={h} style={{ marginTop: 4 }}>{h}</div>)}</div>
                },
                {
                  label: '结论',
                  body: <span><b>不合规 {reportTask.report?.hits?.length ?? 0} 项</b>{reportTask.report?.verdict ?? ''}</span>
                }
              ]} />
            <div style={{ fontSize: 12, color: 'var(--pa-text-tertiary)', marginTop: 8 }}>
              命中问题已按责任岗开成问题单——流转见「问题单」页签。
            </div>
          </>
        )}
      </Modal>

      <Drawer
        title={issueCard && issueCard.title}
        open={!!issueCard} onClose={() => setIssueKey(null)} width={480}
      >
        {issueCard && (
          <>
            <Table size="small" pagination={false} columns={ITEM_COLS} rowKey="label"
              dataSource={[
                { label: '问题描述', body: issueCard.desc ?? '—' },
                { label: '责任岗', body: issueCard.owner ?? '—' },
                ...(issueCard.hit_count > 1 ? [{ label: '命中', body: `${issueCard.hit_count} 次——同类失败挂同单，不重复开单` }] : []),
                {
                  label: '当前环节',
                  body: <Tag color={issueCard.lane === LANES.length - 1 ? 'green' : 'default'}>{LANES[issueCard.lane]}</Tag>
                },
                ...(issueCard.ai_note ? [{ label: '诊断说明', body: <span style={{ color: 'rgba(255,255,255,0.75)' }}>{issueCard.ai_note}</span> }] : []),
                ...(issueCard.verify ? [{ label: '整改与复验', body: `${issueCard.verify.batch} · ${issueCard.verify.note}` }] : []),
                ...(issueCard.close_note ? [{ label: '关闭原因', body: issueCard.close_note }] : [])
              ]} />
            {issueCard.qrows?.length > 0 && (
              <>
                <div style={{ margin: '16px 0 8px', fontWeight: 600 }}>隔离 / 拦截明细（{issueCard.qrows.length}）</div>
                <Table size="small" pagination={false}
                  columns={[
                    { title: '位置', dataIndex: 'loc', width: 210, render: v => v ?? '—' },
                    { title: '说明', dataIndex: 'note', render: v => v ?? '—' }
                  ]}
                  dataSource={issueCard.qrows.map((x, i) => ({ ...x, key: i }))} />
              </>
            )}
            <div style={{ margin: '16px 0 8px', fontWeight: 600 }}>处理链路</div>
            <Steps size="small" direction="vertical" current={issueCard.lane}
              items={LANES.map(l => ({ title: l }))} />
            <div style={{ marginTop: 16 }}>
              {issueCard.lane === LANES.length - 1 ? (
                <Button size="small" disabled>已关闭</Button>
              ) : (
                <Button type="primary" size="small" onClick={() => flowCard(issueCard.id)}>
                  流转 →（推进到「{LANES[issueCard.lane + 1]}」）
                </Button>
              )}
            </div>
          </>
        )}
      </Drawer>
    </div>
  )
}
