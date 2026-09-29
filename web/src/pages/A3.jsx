import { useEffect, useState } from 'react'
import {
  Button, Card, Empty, Input, Modal, Select, Skeleton, Space, Table, Tabs, Tag
} from 'antd'
import { CheckOutlined, FileSearchOutlined, LockOutlined, StopOutlined, ThunderboltOutlined, UndoOutlined } from '@ant-design/icons'
import { TICKETS } from '../data/changeTickets.jsx'

window.__guides = Object.assign(window.__guides || {}, {
  A3: [
    '左上 Tab 按状态筛单：全部 / 待审批 / 已执行 / 已驳回 / 已撤回，计数实时联动。',
    '表头下拉按 风险 / 面 / 工作流 过滤；搜索框按变动单号或对象模糊搜。',
    '单号前缀即类别：WB 井务 / MS 措施作业 / CFG 平台配置 / ACC 权限——「面」列标出改的是数据面 / 配置面 / 语义面；语义面修订走 C2 语义修订提案池，不进本页。',
    '列头「工作流&账号」标出哪条工作流、哪个账号发起；点行尾「详情」或双击行看合同 + 本单审计记录。',
    '#WB-20260922-16 是提出方主动撤回的：与 -23-01 重复，合并重报——对比两张单。',
    '#ACC-20260922-15 是语义面的权限申请被驳回：语义面修订不走本页，转角色权限流程。',
    '#CFG-20260924-09 是平台自身配置变更（置信度阈值），注意它的合同栏是"当前值→建议值 / 影响范围 / 回滚方式"。'
  ]
})
window.__traces = Object.assign(window.__traces || {}, {
  A3: 'F47 受控写入 · m17 校验链 / m8 权限 / m3 持久化'
})

const AUDIT_COLUMNS = [
  { title: '时间', dataIndex: 'when', width: 150 },
  { title: '审批者', dataIndex: 'who', width: 210 },
  { title: '工作流', dataIndex: 'agent', width: 190 },
  { title: '改动内容', dataIndex: 'what' }
]

const REJECT_PLACEHOLDER = '例如：影响测算没覆盖含水上升风险，补测算后再议'
const REJECT_DEFAULT = '影响测算不足'
const now = () => new Date().toISOString().slice(0, 16).replace('T', ' ')
const agentOf = t => t.proposer.split('（')[0]
const WORKFLOWS = [...new Set(TICKETS.map(t => agentOf(t)))]

const RISK_TAG = { high: <Tag color="red">高风险</Tag>, low: <Tag>低风险</Tag> }
const planeOf = t => t.id.includes('CFG-') ? '配置面' : t.id.includes('ACC-') ? '语义面' : '数据面'
const PLANE_TAG = { 数据面: <Tag color="blue">数据面</Tag>, 配置面: <Tag color="orange">配置面</Tag>, 语义面: <Tag color="purple">语义面</Tag> }
function statusTagOf(s) {
  return s === 'pending' ? <Tag>待审批</Tag>
    : s === 'approved' || s === 'auto' ? <Tag color="green">已执行</Tag>
    : s === 'rejected' ? <Tag color="red">已驳回</Tag>
    : <Tag>已撤回</Tag>
}

export default function A3Action() {
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState(() => Object.fromEntries(TICKETS.map(t => [t.id, t.status])))
  const [rejectReasons, setRejectReasons] = useState(() => Object.fromEntries(TICKETS.filter(t => t.reason).map(t => [t.id, t.reason])))
  const [audit, setAudit] = useState(() =>
    Object.fromEntries(TICKETS.filter(t => t.audit0).map(t => [t.id, [{ key: 'a0', agent: agentOf(t), ...t.audit0 }]]))
  )
  const [tab, setTab] = useState('all')
  const [riskF, setRiskF] = useState('all')
  const [planeF, setPlaneF] = useState('all')
  const [wfF, setWfF] = useState('all')
  const [kw, setKw] = useState('')
  const [selected, setSelected] = useState(TICKETS[0].id)
  const [openId, setOpenId] = useState(null)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [reason, setReason] = useState('')

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 500)
    return () => clearTimeout(t)
  }, [])

  const ticket = TICKETS.find(t => t.id === openId)
  const cur = openId ? status[openId] : null

  function approve(id) {
    const t = TICKETS.find(x => x.id === id)
    setStatus(s => ({ ...s, [id]: 'approved' }))
    setAudit(a => ({
      ...a,
      [id]: [...(a[id] || []), {
        key: `ap${(a[id]?.length || 0) + 1}`, when: now(), who: '阿强（当前角色 · 高风险终审）',
        agent: agentOf(t), what: `${t.short} —— 写入变更记录区 ${id}；生产原表未动`
      }]
    }))
    setOpenId(null)
  }
  function submitReject() {
    const r = reason.trim() || REJECT_DEFAULT
    const t = TICKETS.find(x => x.id === selected)
    setStatus(s => ({ ...s, [selected]: 'rejected' }))
    setRejectReasons(m => ({ ...m, [selected]: `${r}（${now()} 驳回）` }))
    setAudit(a => ({
      ...a,
      [selected]: [...(a[selected] || []), {
        key: `rj${(a[selected]?.length || 0) + 1}`, when: now(),
        who: '阿强（当前角色 · 高风险终审）', agent: agentOf(t),
        what: `驳回：${r}；生产侧无任何改动`
      }]
    }))
    setReason('')
    setRejectOpen(false)
    setOpenId(null)
  }

  const counts = {
    pending: Object.values(status).filter(s => s === 'pending').length,
    done: Object.values(status).filter(s => s === 'approved' || s === 'auto').length,
    rejected: Object.values(status).filter(s => s === 'rejected').length,
    withdrawn: Object.values(status).filter(s => s === 'withdrawn').length
  }

  const filtered = TICKETS.filter(t => {
    const inTab = tab === 'all' ? true
      : tab === 'done' ? (status[t.id] === 'approved' || status[t.id] === 'auto')
      : status[t.id] === tab
    const q = kw.trim().toLowerCase()
    return inTab
      && (riskF === 'all' || t.risk === riskF)
      && (planeF === 'all' || planeOf(t) === planeF)
      && (wfF === 'all' || agentOf(t) === wfF)
      && (!q || (t.id + t.object + t.short).toLowerCase().includes(q))
  })

  const queueCols = [
    { title: '变动单', dataIndex: 'id', width: 150 },
    { title: '风险', width: 70, render: (_, t) => RISK_TAG[t.risk] },
    { title: '状态', width: 90, render: (_, t) => statusTagOf(status[t.id]) },
    { title: '面', width: 76, render: (_, t) => PLANE_TAG[planeOf(t)] },
    { title: '对象 / 工作流&账号', render: (_, t) => <span>{t.object}<br /><span style={{ color: '#8a94a3', fontSize: 12 }}>{t.proposer} · {t.time}</span></span> },
    {
      title: '操作', width: 90, align: 'center',
      render: (_, t) => <Button size="small" icon={<FileSearchOutlined />} onClick={e => { e.stopPropagation(); setSelected(t.id); setOpenId(t.id) }}>详情</Button>
    }
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card
        title={
          <Tabs
            activeKey={tab} size="small" onChange={setTab}
            items={[
              { key: 'all', label: '全部' },
              { key: 'pending', label: `待审批（${counts.pending}）` },
              { key: 'done', label: `已执行（${counts.done}）` },
              { key: 'rejected', label: `已驳回（${counts.rejected}）` },
              { key: 'withdrawn', label: `已撤回（${counts.withdrawn}）` }
            ]}
          />
        }
        extra={<span style={{ color: '#8a94a3', fontSize: 12 }}>低风险自动执行 · 高风险必须人工终审 · 批准后只写变更记录区，生产原表不动 · 全程审计</span>}
      >
        <Space wrap style={{ marginBottom: 12 }}>
          <Select size="small" style={{ width: 112 }} value={riskF} onChange={setRiskF}
            options={[{ value: 'all', label: '风险：全部' }, { value: 'high', label: '高风险' }, { value: 'low', label: '低风险' }]} />
          <Select size="small" style={{ width: 124 }} value={planeF} onChange={setPlaneF}
            options={[{ value: 'all', label: '面：全部' }, { value: '数据面', label: '数据面' }, { value: '配置面', label: '配置面' }, { value: '语义面', label: '语义面' }]} />
          <Select size="small" style={{ width: 220 }} value={wfF} onChange={setWfF} showSearch
            options={[{ value: 'all', label: '工作流：全部' }, ...WORKFLOWS.map(w => ({ value: w, label: w }))]} />
          <Input size="small" allowClear style={{ width: 240 }} value={kw} onChange={e => setKw(e.target.value)}
            placeholder="搜变动单号 / 对象…" />
        </Space>
        <Skeleton loading={loading} active paragraph={{ rows: 4 }}>
          <Table
            size="small" columns={queueCols} dataSource={filtered} pagination={false}
            rowClassName={t => (t.id === selected ? 'ant-table-row-selected' : '')}
            onRow={t => ({
              onClick: () => setSelected(t.id),
              onDoubleClick: () => { setSelected(t.id); setOpenId(t.id) },
              style: { cursor: 'pointer' }
            })}
          />
        </Skeleton>
      </Card>

      <Modal
        title={ticket && <Space>{ticket.id}{RISK_TAG[ticket.risk]}{PLANE_TAG[planeOf(ticket)]}{statusTagOf(cur)}</Space>}
        open={!!openId} onCancel={() => setOpenId(null)} width={720} footer={null}
      >
        {ticket && (
          <>
            <div style={{ fontSize: 13, marginBottom: 12, color: '#8a94a3' }}>{ticket.proposer} · {ticket.time}</div>
            <Table size="small" pagination={false}
              columns={[{ title: '项', dataIndex: 'label', width: 100 }, { title: '内容', dataIndex: 'body' }]}
              dataSource={ticket.rows} />

            <div style={{ margin: '16px 0 8px', fontWeight: 600 }}>本单审计记录</div>
            {audit[ticket.id]?.length
              ? <Table size="small" columns={AUDIT_COLUMNS} dataSource={audit[ticket.id]} pagination={false} />
              : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无审计记录" />}

            <div style={{ marginTop: 16, borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 12 }}>
              {cur === 'pending' && (
                <Space>
                  <Button type="primary" danger icon={<LockOutlined />} onClick={() => approve(ticket.id)}>批准（高风险，必须人点）</Button>
                  <Button icon={<StopOutlined />} onClick={e => { e.stopPropagation(); setReason(''); setRejectOpen(true) }}>驳回（须写理由）</Button>
                </Space>
              )}
              {cur === 'approved' && (
                <span style={{ fontSize: 12, color: '#52c41a' }}>
                  <CheckOutlined /> 已写入变更记录区 {ticket.id}；批准后只写变更记录，生产原表不动。
                </span>
              )}
              {cur === 'auto' && (
                <span style={{ fontSize: 12, color: '#52c41a' }}>
                  <ThunderboltOutlined /> 低风险自动执行（{ticket.executedAt}），无需人工点击；全程留审计行。
                </span>
              )}
              {cur === 'rejected' && (
                <span style={{ fontSize: 12, color: '#ff4d4f' }}>
                  <StopOutlined /> 已驳回 · 理由：{rejectReasons[ticket.id]}（退回提出方，生产侧无任何改动）
                </span>
              )}
              {cur === 'withdrawn' && (
                <span style={{ fontSize: 12, color: '#8a94a3' }}>
                  <UndoOutlined /> 已撤回 · 原因：{rejectReasons[ticket.id]}（生产侧无任何改动）
                </span>
              )}
            </div>
          </>
        )}
      </Modal>

      <Modal
        title="驳回（须写理由）" open={rejectOpen} onCancel={() => setRejectOpen(false)} footer={null} width={520}
      >
        <Input.TextArea
          rows={3} value={reason} placeholder={REJECT_PLACEHOLDER}
          onChange={e => setReason(e.target.value)}
        />
        <Button type="primary" danger style={{ marginTop: 12 }} onClick={submitReject}>提交驳回</Button>
      </Modal>
    </div>
  )
}
