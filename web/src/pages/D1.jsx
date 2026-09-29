import { useEffect, useRef, useState } from 'react'
import {
  Alert, Button, Card, Col, Descriptions, Drawer, Empty, Input, InputNumber,
  Row, Segmented, Select, Space, Steps, Switch, Table, Tabs, Tag, Tooltip
} from 'antd'
import { CopyOutlined, PlayCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import {
  MODELS, getModels, getGatewayConfig, saveGatewayConfig,
  getSpendLogs, startDrill, getDrill, listDrills
} from '../api/d1.js'

// E1 的答题/裁判模型选项与本页 MODELS 同源（LiteLLM 网关别名，禁止消费页另抄一份），故在此 re-export
export { MODELS }

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

const PARAM_FIELDS = [
  { key: 'allowedFails', label: '连续失败几次判为故障', min: 1, max: 10 },
  { key: 'cooldownSeconds', label: '故障后冷却多少秒不用主用', min: 10, max: 600 },
  { key: 'numRetries', label: '失败自动重试几次', min: 0, max: 5 },
  { key: 'requestTimeout', label: '单次调用最多等多久（秒）', min: 5, max: 120 }
]

const MONO = { fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12 }
const fmtInt = n => n.toLocaleString('en-US')
const fmtSec = ms => `${(ms / 1000).toFixed(1)} 秒`
const fmtCost = yuan => `¥${yuan.toFixed(4)}`
const fmtTime = iso => iso.replace('T', ' ').slice(5, 16)
const MODEL_TAG = {
  main: <Tag color="green">工业LLM（主用）</Tag>,
  backup: <Tag>DeepSeek（备用）</Tag>
}

export default function D1Gateway() {
  const [gateway, setGateway] = useState(null)
  const [tab, setTab] = useState('models')

  // 调用参数：cfg=服务端已保存值，form=表单编辑值
  const [cfg, setCfg] = useState(null)
  const [form, setForm] = useState(null)
  const [yaml, setYaml] = useState('')
  const [saving, setSaving] = useState(false)
  const [savedTip, setSavedTip] = useState('')
  const [copied, setCopied] = useState(false)
  const dirty = !!cfg && !!form && JSON.stringify(form) !== JSON.stringify(cfg)

  // 记账流水
  const [query, setQuery] = useState({ model: 'all', range: 'all', keyword: '', page: 1, pageSize: 15 })
  const [ledger, setLedger] = useState({ items: [], total: 0 })
  const [ledgerLoading, setLedgerLoading] = useState(true)
  const [detail, setDetail] = useState(null)

  // 故障演练
  const [drillAllowed, setDrillAllowed] = useState(false)
  const [drill, setDrill] = useState(null)
  const [drillLogs, setDrillLogs] = useState([])
  const pollRef = useRef(null)

  useEffect(() => {
    let on = true
    getModels().then(d => on && setGateway(d.gateway))
    getGatewayConfig().then(d => { if (on) { setCfg(d.params); setForm(d.params); setYaml(d.yaml) } })
    listDrills().then(d => on && setDrillLogs(d))
    return () => { on = false; if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  useEffect(() => {
    let on = true
    setLedgerLoading(true)
    getSpendLogs(query).then(d => { if (on) { setLedger(d); setLedgerLoading(false) } })
    return () => { on = false }
  }, [query])

  async function doSave() {
    setSaving(true)
    try {
      const res = await saveGatewayConfig(form)
      setCfg(res.params)
      setForm(res.params)
      setYaml(res.yaml)
      setSavedTip('已保存 · 配置写回网关并热加载，全平台生效')
      setTimeout(() => setSavedTip(''), 3000)
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

  function runDrill() {
    if (pollRef.current) return
    startDrill().then(({ drillId }) => {
      setDrill({ status: 'running', nodes: null, result: null })
      pollRef.current = setInterval(async () => {
        const d = await getDrill(drillId)
        setDrill({ status: d.status, nodes: d.nodes, result: d.result })
        if (d.status === 'done') {
          clearInterval(pollRef.current)
          pollRef.current = null
          listDrills().then(setDrillLogs)
          setQuery(q => ({ ...q, page: 1 })) // 服务端刚落一条流水，回到第一页可见
        }
      }, 300)
    })
  }

  const modelColumns = [
    { title: '模型', dataIndex: 'name', width: 110, render: v => <b>{v}</b> },
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
    { title: '接入方式', dataIndex: 'access', width: 210 },
    { title: '说明', dataIndex: 'note' }
  ]

  const ledgerColumns = [
    { title: '时间', dataIndex: 'time', width: 115, render: fmtTime },
    { title: '调用号', dataIndex: 'id', width: 95, render: v => <span style={MONO}>{v}</span> },
    { title: '模型', dataIndex: 'modelKey', width: 130, render: v => MODEL_TAG[v] },
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
    {
      key: 'models',
      label: `模型线路（${MODELS.length}）`
    },
    {
      key: 'params',
      label: `调用参数（${PARAM_FIELDS.length}）`
    },
    {
      key: 'ledger',
      label: `记账流水（${ledger.total}）`
    },
    {
      key: 'drill',
      label: `故障演练（${drillLogs.length}）`
    }
  ]
  const tabContent = {
    models: (
      <>
        <Table size="small" columns={modelColumns} dataSource={MODELS} pagination={false} rowKey="key" />
        <div style={{ marginTop: 12, fontSize: 13 }}>
          <b>适用范围</b>
          <span style={{ marginLeft: 8, color: '#8a94a3' }}>
            问一问、报告库回答、问数 —— 平台所有用到模型的动作，都从这一个口出去。
          </span>
        </div>
      </>
    ),
    params: form && (
      <>
        <Row gutter={12}>
          {PARAM_FIELDS.map(p => (
            <Col span={6} key={p.key}>
              <div style={{ fontSize: 12, marginBottom: 4 }}>{p.label}</div>
              <InputNumber
                size="small" style={{ width: '100%' }} min={p.min} max={p.max}
                value={form[p.key]} onChange={v => setForm(f => ({ ...f, [p.key]: v }))}
              />
            </Col>
          ))}
        </Row>
        <Space style={{ marginTop: 12 }}>
          <Button type="primary" size="small" disabled={!dirty} loading={saving} onClick={doSave}>保存设置</Button>
          {dirty && <Button size="small" onClick={() => setForm(cfg)}>放弃更改</Button>}
          {dirty && <span style={{ fontSize: 12, color: '#faad14' }}>有未保存的更改</span>}
          {!dirty && savedTip && <span style={{ fontSize: 12, color: '#52c41a' }}>{savedTip}</span>}
        </Space>

        <div style={{ marginTop: 20, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 8 }}>
          <b style={{ fontSize: 13 }}>配置文件预览</b>
          <span style={{ fontSize: 12, color: '#8a94a3' }}>由上方参数生成 · 保存后更新</span>
          <Button size="small" type="text" icon={<CopyOutlined />} onClick={copyYaml}>{copied ? '已复制' : '复制'}</Button>
        </div>
        <pre className="code-block" style={{ margin: 0 }}>{yaml}</pre>
      </>
    ),
    ledger: (
      <>
        <Space wrap size={8} style={{ marginBottom: 12 }}>
          <Select
            size="small" style={{ width: 150 }} value={query.model}
            onChange={v => setQuery(q => ({ ...q, model: v, page: 1 }))}
            options={[
              { value: 'all', label: '模型：全部' },
              { value: 'main', label: '主用 · 工业LLM' },
              { value: 'backup', label: '备用 · DeepSeek' }
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
        <Table
          size="small" loading={ledgerLoading} columns={ledgerColumns} dataSource={ledger.items} rowKey="id"
          scroll={{ x: 980 }}
          pagination={{
            current: query.page, pageSize: query.pageSize, total: ledger.total, showSizeChanger: false,
            showTotal: t => `共 ${t} 条`,
            onChange: (p, ps) => setQuery(q => ({ ...q, page: p, pageSize: ps }))
          }}
          onRow={r => ({ onClick: () => setDetail(r), style: { cursor: 'pointer' } })}
          locale={{ emptyText: <Empty description="没有匹配的调用记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
        />
      </>
    ),
    drill: (
      <>
        <Space wrap>
          <Switch size="small" checked={drillAllowed} onChange={setDrillAllowed} />
          <span>允许演练</span>
          <Tooltip title="演练会短暂关停主用模型，属破坏性操作，仅限演练窗口内开启执行。">
            <QuestionCircleOutlined style={{ color: '#8a94a3', cursor: 'help' }} />
          </Tooltip>
          <Button
            type="primary" size="small" icon={<PlayCircleOutlined />}
            disabled={!drillAllowed || drill?.status === 'running'} onClick={runDrill}
          >
            开始故障演练（关停主用 {cfg?.cooldownSeconds ?? 60} 秒）
          </Button>
          {drill?.status === 'running' && <span style={{ fontSize: 12, color: '#8a94a3' }}>演练执行中…</span>}
        </Space>
        {drill?.nodes && (
          <Steps
            size="small" style={{ marginTop: 16 }}
            items={drill.nodes.map(n => ({ title: n.label, status: n.state }))}
          />
        )}
        {drill?.status === 'done' && drill.result && (
          <>
            <Alert style={{ marginTop: 12 }} type="info" showIcon message={drill.result.conclusion} />
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
    <div>
      <div style={{ marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 18, fontWeight: 600 }}>模型与线路</span>
          {gateway?.status === 'running' && <Tag color="success" style={{ marginInlineEnd: 0 }}>网关运行中</Tag>}
          <span style={{ color: '#8a94a3', fontSize: 12 }}>主用 工业LLM · 备用 DeepSeek 待命</span>
        </div>
        <span style={{ color: '#8a94a3', fontSize: 13 }}>
          平台所有模型调用的唯一出口：主用故障自动切备用、冷却期满自动切回；改配置即对全平台生效，问数的人不用管。
        </span>
      </div>
      <Card title={<Tabs activeKey={tab} size="small" onChange={setTab} items={tabItems} />}>
        {tabContent[tab]}
      </Card>

      <Drawer
        open={!!detail} onClose={() => setDetail(null)} width={420}
        title={detail && (
          <Space>
            <span style={MONO}>{detail.id}</span>
            {MODEL_TAG[detail.modelKey]}
          </Space>
        )}
      >
        {detail && (
          <Descriptions
            column={1} size="small" bordered
            items={[
              { key: 'time', label: '调用时间', children: detail.time.replace('T', ' ') },
              { key: 'alias', label: '调用别名', children: <span style={MONO}>{MODELS.find(m => m.key === detail.modelKey)?.alias}</span> },
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
