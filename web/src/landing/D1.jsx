/**
 * 落地树 · D1 模型与线路（P0-07 全页落地——首个真 API 页面）。
 *
 * 合同：teach-petro-agent/specs/api/D1-模型与线路.md 端点 1–7（七条路由全接线：
 * 页头徽标 / 配置读写 / spend 流水 / 演练三连）。视觉与交互形态对照原型树
 * #/proto/D1（prototype/app/src/pages/D1.jsx）——数据是真、形是原型；不引 mock。
 *
 * 接线差异（相对原型页，登记票面）：
 * - 数据源 = api/gateway.js（client 真 HTTP；后端 R1 snake_case 在接口层折回
 *   camel，页面列定义与原型同形）；
 * - yaml = 服务端全文回显（原型是前端拼装演示稿；合同「表单里每个数字对应
 *   文件里的一行」由后端生成保证）；
 * - 演练四步进度 = useTaskPolling 300ms 轮询 + onProgress 快照（原型是页面
 *   setInterval；节奏由服务端任务驱动，00 §5.2）；
 * - 错误路径：模型清单失败内联 Alert（错误包 code/trace_id 展示）、配置加载失败/
 *   流水拉取失败内联 Alert（失败态与空态区分——toast 会消散、空态会伪装成
 *   「没有记录」，P0-07 审查补）、保存失败内联 Alert（500 热加载失败需回滚提示
 *   语义）、演练重入 409 兜底禁用＋提示。
 */

import { useEffect, useState } from 'react'
import {
  Alert, Button, Card, Col, Descriptions, Drawer, Empty, Input, InputNumber,
  Row, Segmented, Select, Space, Steps, Switch, Table, Tabs, Tag, Tooltip
} from 'antd'
import { CopyOutlined, PlayCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import { ApiError, useTaskPolling } from '../api/client.js'
import {
  PARAM_LIMITS, getModels, getGatewayConfig, saveGatewayConfig,
  getSpendLogs, startDrill, listDrills, mapDrillSnapshot
} from '../api/gateway.js'

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

// 参数四件（区间唯一来源 = api/gateway.js PARAM_LIMITS＝合同 §2 数值边界）
const PARAM_FIELDS = [
  { key: 'allowedFails', label: '连续失败几次判为故障', limits: PARAM_LIMITS.allowedFails },
  { key: 'cooldownSeconds', label: '故障后冷却多少秒不用主用', limits: PARAM_LIMITS.cooldownSeconds },
  { key: 'numRetries', label: '失败自动重试几次', limits: PARAM_LIMITS.numRetries },
  { key: 'requestTimeout', label: '单次调用最多等多久（秒）', limits: PARAM_LIMITS.requestTimeout }
]

const MONO = { fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12 }
const fmtInt = n => n.toLocaleString('en-US')
const fmtSec = ms => `${(ms / 1000).toFixed(1)} 秒`
const fmtCost = yuan => `¥${Number(yuan).toFixed(4)}`
const fmtTime = iso => String(iso || '').replace('T', ' ').slice(5, 16)

/** 网关运行态徽标（端点 1：running | degraded | down）。 */
const GATEWAY_BADGE = {
  running: { color: 'success', label: '网关运行中' },
  degraded: { color: 'warning', label: '网关降级中（备用承载）' },
  down: { color: 'error', label: '网关不可用' }
}

/** 错误包 → 内联展示行（错误包展示路径：人话 message＋code＋trace_id）。 */
function errText(err) {
  if (!(err instanceof ApiError)) return String(err)
  return [
    err.message,
    err.code ? `code ${err.code}` : '',
    err.traceId ? `trace ${err.traceId}` : ''
  ].filter(Boolean).join(' · ')
}

/**
 * 落地 D1 模型与线路页（七端点全接线）。
 * @returns {JSX.Element}
 */
export default function D1Landing() {
  // ── 页头：模型清单＋网关运行徽标（端点 1） ──
  const [gateway, setGateway] = useState(null)
  const [models, setModels] = useState([])
  const [modelsError, setModelsError] = useState(null)
  const [tab, setTab] = useState('models')

  // ── 配置面：调用参数读写（端点 2/3）。cfg=服务端已保存值，form=表单编辑值 ──
  const [cfg, setCfg] = useState(null)
  const [form, setForm] = useState(null)
  const [yaml, setYaml] = useState('')
  const [saving, setSaving] = useState(false)
  const [savedTip, setSavedTip] = useState('')
  const [saveError, setSaveError] = useState(null)
  const [cfgError, setCfgError] = useState(null) // 配置拉取失败（端点 2）——内联常驻，失败态≠空态
  const [copied, setCopied] = useState(false)
  const dirty = !!cfg && !!form && JSON.stringify(form) !== JSON.stringify(cfg)

  // ── 记账面：spend 流水分页（端点 4） ──
  const [query, setQuery] = useState({ model: 'all', range: 'all', keyword: '', page: 1, pageSize: 15 })
  const [ledger, setLedger] = useState({ items: [], total: 0 })
  const [ledgerLoading, setLedgerLoading] = useState(true)
  const [ledgerError, setLedgerError] = useState(null) // 流水拉取失败（端点 4）——内联常驻，失败态≠空态
  const [detail, setDetail] = useState(null)

  // ── 演练面：故障演练三连（端点 5/6/7）。受理 202 → useTaskPolling 轮询进度 ──
  const [drillAllowed, setDrillAllowed] = useState(false)
  const [drill, setDrill] = useState(null) // {status:'running'|'done'|'failed', nodes, result}
  const [drillLogs, setDrillLogs] = useState([])
  const [drillId, setDrillId] = useState(null)
  const [drillConflict, setDrillConflict] = useState(null) // 409 兜底
  const { status: pollStatus, data: drillDone, error: pollError } = useTaskPolling(drillId, {
    path: '/gateway/drills',
    intervalMs: 300, // 合同 §5：前端 300ms 轮询（节奏由服务端任务驱动）
    onProgress: d => setDrill(mapDrillSnapshot(d)) // 进行中快照实时点亮 Steps
  })

  useEffect(() => {
    let on = true
    getModels()
      .then(d => { if (on) { setGateway(d.gateway); setModels(d.models); setModelsError(null) } })
      .catch(err => { if (on) setModelsError(err) })
    getGatewayConfig()
      .then(d => { if (on) { setCfg(d.params); setForm(d.params); setYaml(d.yaml); setCfgError(null) } })
      .catch(err => { if (on) setCfgError(err) }) // client 已 message；内联常驻（params 页签）
    listDrills().then(d => { if (on) setDrillLogs(d) }).catch(() => {})
    return () => { on = false }
  }, [])

  useEffect(() => {
    let on = true
    setLedgerLoading(true)
    getSpendLogs(query)
      .then(d => { if (on) { setLedger(d); setLedgerError(null); setLedgerLoading(false) } })
      .catch(err => { if (on) { setLedgerError(err); setLedgerLoading(false) } }) // 内联常驻（ledger 页签）
    return () => { on = false }
  }, [query])

  // 轮询收场 done：回显结果＋刷新演练历史＋流水回第一页（done 时服务端落两笔账——合同 §5）
  useEffect(() => {
    if (pollStatus === 'done' && drillDone) {
      setDrill(mapDrillSnapshot(drillDone))
      listDrills().then(setDrillLogs).catch(() => {})
      setQuery(q => ({ ...q, page: 1 }))
    }
  }, [pollStatus, drillDone])

  // 轮询收场 failed（连续两次轮询失败）：inline 错误态
  useEffect(() => {
    if (pollStatus === 'failed') setDrill(d => (d ? { ...d, status: 'failed' } : d))
  }, [pollStatus])

  async function doSave() {
    setSaving(true)
    setSaveError(null)
    try {
      const res = await saveGatewayConfig(form)
      setCfg(res.params) // 以服务端回值为准（合同 §2：返回快照为唯一真值）
      setForm(res.params)
      setYaml(res.yaml)
      setSavedTip('已保存 · 配置写回网关并热加载，全平台生效')
      setTimeout(() => setSavedTip(''), 3000)
    } catch (err) {
      setSaveError(err) // client 已 message；内联常驻（500 热加载失败需回滚提示语义）
    } finally {
      setSaving(false)
    }
  }

  function copyYaml() {
    if (!navigator.clipboard) return
    navigator.clipboard.writeText(yaml).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  async function runDrill() {
    setDrillConflict(null)
    setDrill({ status: 'running', nodes: null, result: null })
    try {
      const { drillId: id } = await startDrill()
      setDrillId(id) // 受理 202 → useTaskPolling 接管轮询
    } catch (err) {
      setDrill(null)
      if (err instanceof ApiError && err.status === 409) {
        // 重入 409：按钮禁用兜底（合同 §5「前端按钮禁用兜底，不依赖此码」）
        setDrillConflict(err)
      }
      // 其余错误 client 已统一 message
    }
  }

  const modelName = key => models.find(m => m.key === key)?.name || key
  const modelTag = key => (
    <Tag color={key === 'main' ? 'green' : 'default'}>{`${modelName(key)}（${key === 'main' ? '主用' : '备用'}）`}</Tag>
  )
  const mainName = models.find(m => m.role === 'main')?.name
  const backupName = models.find(m => m.role === 'backup')?.name
  const badge = GATEWAY_BADGE[gateway?.status] || null
  const drillRunning = drill?.status === 'running' || pollStatus === 'polling'

  const modelColumns = [
    { title: '模型', dataIndex: 'name', width: 140, render: v => <b>{v}</b> },
    {
      title: <span>调用别名{helpIcon('业务代码只认调用别名，不直接连模型；更换模型只改这一处。')}</span>,
      dataIndex: 'alias', width: 150,
      render: v => <span style={MONO}>{v}</span>
    },
    {
      title: <span>角色{helpIcon('主用故障自动切备用，用户无感知；冷却期满自动切回。')}</span>,
      dataIndex: 'role', width: 130,
      render: v => (v === 'main' ? <Tag color="green">主用 · 使用中</Tag> : <Tag>备用</Tag>)
    },
    { title: '接入方式', dataIndex: 'access', width: 230 },
    { title: '说明', dataIndex: 'note' }
  ]

  const ledgerColumns = [
    { title: '时间', dataIndex: 'time', width: 115, render: fmtTime },
    { title: '调用号', dataIndex: 'id', width: 120, render: v => <span style={MONO}>{v}</span> },
    { title: '模型', dataIndex: 'modelKey', width: 150, render: k => modelTag(k) },
    {
      title: <span>输入 token{helpIcon('token＝模型计费的计算量单位')}</span>,
      dataIndex: 'inputTokens', width: 95, align: 'right', render: fmtInt
    },
    { title: '输出 token', dataIndex: 'outputTokens', width: 95, align: 'right', render: fmtInt },
    {
      title: <span>首字延迟{helpIcon('从发起请求到返回第一个字的时间')}</span>,
      dataIndex: 'firstMs', width: 85, render: fmtSec
    },
    { title: '总耗时', dataIndex: 'totalMs', width: 80, render: fmtSec },
    { title: '花费', dataIndex: 'costYuan', width: 90, align: 'right', render: fmtCost },
    {
      title: '切换', dataIndex: 'fallback', width: 80,
      render: v => (v ? <Tag color="orange">故障切换</Tag> : <span style={{ color: '#8a94a3' }}>—</span>)
    },
    { title: '备注', dataIndex: 'note', ellipsis: true, render: v => v || <span style={{ color: '#8a94a3' }}>—</span> }
  ]

  const tabItems = [
    { key: 'models', label: `模型线路（${models.length}）` },
    { key: 'params', label: `调用参数（${PARAM_FIELDS.length}）` },
    { key: 'ledger', label: `记账流水（${ledger.total}）` },
    { key: 'drill', label: `故障演练（${drillLogs.length}）` }
  ]

  const tabContent = {
    models: (
      <>
        <Table size="small" columns={modelColumns} dataSource={models} pagination={false} rowKey="key"
          loading={!modelsError && models.length === 0}
          locale={{ emptyText: <Empty description={modelsError ? '模型清单拉取失败' : '暂无模型'} image={Empty.PRESENTED_IMAGE_SIMPLE} /> }} />
        <div style={{ marginTop: 12, fontSize: 13 }}>
          <b>适用范围</b>
          <span style={{ marginLeft: 8, color: '#8a94a3' }}>
            问一问、报告库回答、问数 —— 平台所有用到模型的动作，都从这一个口出去。
          </span>
        </div>
      </>
    ),
    params: !form && cfgError ? (
      // 配置拉取失败：内联 Alert 常驻（对齐 models/保存/演练错误路径形态）——
      // 失败态与空态区分，不伪装成「配置加载中」。
      <Alert type="error" showIcon
        message="配置加载失败——调用参数暂不可编辑（服务端 models.yaml 全文亦未回显）"
        description={errText(cfgError)} />
    ) : form && (
      <>
        <Row gutter={12}>
          {PARAM_FIELDS.map(p => (
            <Col span={6} key={p.key}>
              <div style={{ fontSize: 12, marginBottom: 4 }}>{p.label}</div>
              <InputNumber
                size="small" style={{ width: '100%' }} min={p.limits.min} max={p.limits.max}
                value={form[p.key]} onChange={v => setForm(f => ({ ...f, [p.key]: v }))}
              />
            </Col>
          ))}
        </Row>
        <Space style={{ marginTop: 12 }}>
          <Button type="primary" size="small" disabled={!dirty} loading={saving} onClick={doSave}>保存设置</Button>
          {dirty && <Button size="small" onClick={() => setForm(cfg)}>放弃更改</Button>}
          {dirty && <span style={{ fontSize: 12, color: '#faad14' }}>有未保存的更改</span>}
          {!dirty && savedTip && !saveError && <span style={{ fontSize: 12, color: '#52c41a' }}>{savedTip}</span>}
        </Space>
        {saveError && (
          <Alert style={{ marginTop: 12 }} type="error" showIcon
            message="保存失败——配置未生效（此前线上配置仍有效，可回退数值后重试）"
            description={errText(saveError)} />
        )}

        <div style={{ marginTop: 20, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
          <b style={{ fontSize: 13 }}>配置文件（models.yaml）</b>
          <span style={{ fontSize: 12, color: '#8a94a3' }}>服务端全文 · 表单里每个数字对应文件里的一行 · 保存后热加载回显</span>
          <Button size="small" type="text" icon={<CopyOutlined />} onClick={copyYaml}>{copied ? '已复制' : '复制'}</Button>
        </div>
        <pre className="code-block" style={{ margin: 0 }}>{yaml || '（配置全文加载中…）'}</pre>
      </>
    ),
    ledger: (
      <>
        <Space wrap size={8} style={{ marginBottom: 12 }}>
          <Select
            size="small" style={{ width: 170 }} value={query.model}
            onChange={v => setQuery(q => ({ ...q, model: v, page: 1 }))}
            options={[
              { value: 'all', label: '模型：全部' },
              { value: 'main', label: `主用 · ${mainName || '主用'}` },
              { value: 'backup', label: `备用 · ${backupName || '备用'}` }
            ]}
          />
          <Segmented
            size="small" value={query.range}
            onChange={v => setQuery(q => ({ ...q, range: v, page: 1 }))}
            options={[{ label: '全部', value: 'all' }, { label: '今天', value: 'today' }, { label: '近 7 天', value: '7d' }]}
          />
          <Input
            size="small" allowClear style={{ width: 200 }} value={query.keyword}
            onChange={e => setQuery(q => ({ ...q, keyword: e.target.value, page: 1 }))}
            placeholder="搜调用号 / 备注…"
          />
        </Space>
        {ledgerError && (
          <Alert style={{ marginBottom: 12 }} type="error" showIcon
            message="记账流水拉取失败——下表不是最新数据"
            description={errText(ledgerError)} />
        )}
        <Table
          size="small" loading={ledgerLoading} columns={ledgerColumns} dataSource={ledger.items} rowKey="id"
          scroll={{ x: 1080 }}
          pagination={{
            current: query.page, pageSize: query.pageSize, total: ledger.total, showSizeChanger: false,
            showTotal: t => `共 ${t} 条`,
            onChange: (p, ps) => setQuery(q => ({ ...q, page: p, pageSize: ps }))
          }}
          onRow={r => ({ onClick: () => setDetail(r), style: { cursor: 'pointer' } })}
          locale={{ emptyText: <Empty description={ledgerError ? '流水拉取失败' : '没有匹配的调用记录'} image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      </>
    ),
    drill: (
      <>
        <Space wrap>
          <Switch size="small" checked={drillAllowed}
            onChange={v => { setDrillAllowed(v); if (!v) setDrillConflict(null) }} />
          <span>允许演练</span>
          <Tooltip title="演练会短暂关停主用模型，属破坏性操作，仅限演练窗口内开启执行。">
            <QuestionCircleOutlined style={{ color: '#8a94a3', cursor: 'help' }} />
          </Tooltip>
          <Button
            type="primary" size="small" icon={<PlayCircleOutlined />}
            disabled={!drillAllowed || drillRunning || !!drillConflict} onClick={runDrill}
          >
            开始故障演练（关停主用 {cfg?.cooldownSeconds ?? '—'} 秒）
          </Button>
          {drillRunning && <span style={{ fontSize: 12, color: '#8a94a3' }}>演练执行中…</span>}
        </Space>
        {drillConflict && (
          <Alert style={{ marginTop: 12 }} type="warning" showIcon
            message="已有演练进行中（网关返回 409）——开始按钮已禁用；等当前演练结束后关闭再打开「允许演练」即可重试。"
            description={errText(drillConflict)} />
        )}
        {drill?.status === 'failed' && (
          <Alert style={{ marginTop: 12 }} type="error" showIcon
            message="演练任务轮询失败"
            description={errText(pollError)} />
        )}
        {drill?.nodes && (
          <Steps
            size="small" style={{ marginTop: 16 }}
            items={drill.nodes.map(n => ({
              title: n.label,
              status: n.state,
              description: n.note ? <span style={{ fontSize: 12, color: '#8a94a3' }}>{n.note}</span> : undefined
            }))}
          />
        )}
        {drill?.status === 'done' && drill.result && (
          <>
            <Alert style={{ marginTop: 12 }} type="info" showIcon message={drill.result.conclusion} />
            {drill.result.ledgerRow && (
              <div style={{ marginTop: 8, fontSize: 12, color: '#8a94a3' }}>
                本次演练落账：<span style={MONO}>{drill.result.ledgerRow.id}</span>
                {' · '}备用应答 {fmtInt(drill.result.ledgerRow.inputTokens)}+{fmtInt(drill.result.ledgerRow.outputTokens)} token
                {' · '}花费 {fmtCost(drill.result.ledgerRow.costYuan)}（流水第一页可见）
              </div>
            )}
            <div style={{ marginTop: 12 }}>
              <b style={{ fontSize: 13 }}>切换结构化日志（Fallback）</b>
              <div className="code-block" style={{ marginTop: 6 }}>{JSON.stringify(drill.result.fallback, null, 2)}</div>
            </div>
          </>
        )}
        <div style={{ marginTop: 16 }}>
          <b style={{ fontSize: 13 }}>演练日志</b>
          <Table
            style={{ marginTop: 8 }} size="small" pagination={false} rowKey="id" dataSource={drillLogs}
            columns={[
              { title: '时间', dataIndex: 'time', width: 150, render: v => fmtTime(v) },
              { title: '摘要', dataIndex: 'summary' }
            ]}
            locale={{ emptyText: <Empty description="暂无演练记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          />
        </div>
      </>
    )
  }

  return (
    <div style={{ maxWidth: 1080 }}>
      <div style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 18, fontWeight: 600 }}>模型与线路</span>
          {badge && <Tag color={badge.color} style={{ marginInlineEnd: 0 }}>{badge.label}</Tag>}
          {(mainName && backupName) && (
            <span style={{ color: '#8a94a3', fontSize: 12 }}>主用 {mainName} · 备用 {backupName} 待命</span>
          )}
        </div>
        <span style={{ color: '#8a94a3', fontSize: 13 }}>
          平台所有模型调用的唯一出口：主用故障自动切备用、冷却期满自动切回；改配置即对全平台生效，问数的人不用管。
        </span>
        {modelsError && (
          <Alert type="error" showIcon style={{ marginTop: 4 }}
            message="模型清单拉取失败（页头徽标与线路表暂不可用）"
            description={errText(modelsError)} />
        )}
      </div>
      <Card title={<Tabs activeKey={tab} size="small" onChange={setTab} items={tabItems} />}>
        {tabContent[tab]}
      </Card>

      <Drawer
        open={!!detail} onClose={() => setDetail(null)} width={420}
        title={detail && (
          <Space>
            <span style={MONO}>{detail.id}</span>
            {modelTag(detail.modelKey)}
          </Space>
        )}
      >
        {detail && (
          <Descriptions
            column={1} size="small" bordered
            items={[
              { key: 'time', label: '调用时间', children: String(detail.time).replace('T', ' ') },
              { key: 'alias', label: '调用别名', children: <span style={MONO}>{detail.alias}</span> },
              { key: 'in', label: '输入 token', children: fmtInt(detail.inputTokens) },
              { key: 'out', label: '输出 token', children: fmtInt(detail.outputTokens) },
              { key: 'first', label: '首字延迟', children: fmtSec(detail.firstMs) },
              { key: 'total', label: '总耗时', children: fmtSec(detail.totalMs) },
              { key: 'cost', label: '花费', children: fmtCost(detail.costYuan) },
              { key: 'fb', label: '故障切换', children: detail.fallback ? '是 —— 主用冷却期内由备用应答' : '否' },
              ...(detail.note ? [{ key: 'note', label: '备注', children: detail.note }] : [])
            ]}
          />
        )}
      </Drawer>
    </div>
  )
}
