import { useEffect, useRef, useState } from 'react'
import {
  Button, Card, Descriptions, Empty, Select, Space, Spin, Table, Tabs, Tag, Tooltip
} from 'antd'
import { MessageOutlined } from '@ant-design/icons'
import { errText } from '../api/client.js'
import {
  getWellChain, getWellProfile, listWellChangeTickets, listWells, wellOptionLabel
} from '../api/wells.js'

window.__traces = Object.assign(window.__traces || {}, {
  A2: 'F44 背景注入 · F45 对象查询 · F46 专业函数（递减风险）· F43 AgentOS 总纲 · F48 治理约束（无权限井灰显）· m16 对象关系 / m1 底座'
})

// ── 合同常量展示映射（teach A2 v0.2 常量表——Tag 色改状态字段驱动，R-WIRE A2-3/8/10） ──
// 井状态四枚举（设定书 §A.1）：生产中绿/停产红为合同注记；检修/待弃置二色未冻结——
// 接线票定橙/灰（W-A2 拍板）。未知值兜底 default。
const WELL_STATUS_COLOR = { 生产中: 'green', 停产: 'red', 检修: 'orange', 待弃置: 'default' }
// 设备状态三枚举（v0.2 收编常量）：运行中绿/停机检修红；「随井停用红或灰」展示层
// 二择取灰——停产伴生非故障，与停机检修区分（W-A2 拍板，R-WIRE A2-8）。
const DEVICE_STATUS_COLOR = { 运行中: 'green', 停机检修: 'red', 随井停用: 'default' }
// 纪录合并类型三值（页面规格 §A2 F2）——kind→Tag 色为展示映射保留前端常量（R-WIRE A2-10）。
const EVENT_KIND_COLOR = { 措施: 'default', 检修: 'orange', 状态变更: 'red' }
// 变动单状态四枚举（徽标：橙/绿/红/灰）· 面三枚举（徽标：蓝/橙/紫）——真接口直返
// 展示值，页面零加工渲染徽标（合同端点 4；CH_STATUS 映射与 planeOf 推导退役）。
const TICKET_STATUS_COLOR = { 待审批: 'orange', 已执行: 'green', 已驳回: 'red', 已撤回: 'default' }
const TICKET_PLANE_COLOR = { 数据面: 'blue', 配置面: 'orange', 语义面: 'purple' }

// 禁用占位条目＝前端常量提示（合同端点 1——无权限的井服务端已不进响应，本条只作提示）
const NO_PERMISSION_OPTION = { value: 'na', label: '（无查看权限的井不在此列表）', disabled: true }

const MEASURE_COLS = [
  { title: '日期', dataIndex: 'date', width: 100 },
  { title: '类型', dataIndex: 'type', width: 70, render: t => (t ? <Tag>{t}</Tag> : '—') },
  { title: '内容', dataIndex: 'content', render: v => v ?? '—' },
  { title: '效果', dataIndex: 'result', render: v => v ?? '—' }
]
const DEVICE_COLS = [
  { title: '类型', dataIndex: 'type', width: 90, render: t => <Tag color="blue">{t}</Tag> },
  { title: '状态', dataIndex: 'status', width: 100, render: t => <Tag color={DEVICE_STATUS_COLOR[t] || 'default'}>{t}</Tag> },
  { title: '启用', dataIndex: 'since', width: 110 },
  { title: '备注', dataIndex: 'note' }
]
const OVERHAUL_COLS = [
  { title: '起止', width: 230, render: (_, r) => `${r.dateStart ?? '—'} → ${r.dateEnd ?? '—'}` },
  { title: '作业', dataIndex: 'job', width: 150, render: v => v ?? '—' },
  { title: '影响', dataIndex: 'impact', render: v => v ?? '—' },
  { title: '批次', dataIndex: 'batch', width: 140, render: v => v ?? '—' }
]
const EVENT_COLS = [
  { title: '时间', width: 210, render: (_, r) => (r.dateEnd ? `${r.date} → ${r.dateEnd}` : (r.date ?? '—')) },
  { title: '类型', dataIndex: 'kind', width: 90, render: t => <Tag color={EVENT_KIND_COLOR[t] || 'default'}>{t}</Tag> },
  { title: '事项', dataIndex: 'title', render: v => v ?? '—' },
  { title: '结果 / 影响', dataIndex: 'outcome', render: v => v ?? '—' }
]

const ASK_COL = {
  title: '', width: 46,
  render: () => (
    <Tooltip title="去问一问">
      <Button type="text" size="small" icon={<MessageOutlined />}
        onClick={() => { location.hash = '/A1' }} />
    </Tooltip>
  )
}

const CHANGE_COLS = [
  { title: '变动单', dataIndex: 'id', width: 150 },
  { title: '状态', dataIndex: 'status', width: 90, render: s => <Tag color={TICKET_STATUS_COLOR[s] || 'default'}>{s}</Tag> },
  { title: '面', dataIndex: 'plane', width: 76, render: p => <Tag color={TICKET_PLANE_COLOR[p] || 'default'}>{p}</Tag> },
  { title: '事项', dataIndex: 'short' },
  { title: '提出', width: 250, render: (_, t) => <span style={{ color: 'var(--pa-text-tertiary)', fontSize: 12 }}>{t.proposer} · {t.time}</span> }
]

function ChangeNode({ tickets }) {
  const items = tickets ? tickets.items : []
  return (
    <div>
      {items.length
        ? <Table size="small" columns={CHANGE_COLS} dataSource={items} rowKey="id" pagination={false} />
        : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本井暂无变动单" />}
      <div style={{ fontSize: 12, color: 'var(--pa-text-tertiary)', marginTop: items.length ? 8 : 0 }}>
        只列涉及本井的单 · <a href="#/A3" style={{ color: 'var(--pa-primary)' }}>去数据变动审批看全部</a>
      </div>
    </div>
  )
}

function ChainNode({ rows, cols, empty, foot }) {
  return (
    <div>
      {rows.length
        ? <Table size="small" columns={[...cols, ASK_COL]} dataSource={rows} pagination={false} />
        : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={empty} />}
      {foot && <div style={{ fontSize: 12, color: 'var(--pa-text-tertiary)', marginTop: rows.length ? 8 : 0 }}>{foot}</div>}
    </div>
  )
}

// 五页签（纪录/措施/设备/检修/变动）——计数直接消费服务端 counts（前端零拼算，
// R-WIRE A2-12）；「纪录」页签＝服务端合并 events 原样渲染（前端零编排）；
// 措施/设备页签空数组仍常驻显示枚举尾注全文（合同端点 3——N-11 措施 0 行照显）。
const chainTabs = (chain, tickets) => {
  const counts = chain.counts
  return [
    { key: 'events', label: `纪录（${counts.events}）`,
      children: <ChainNode rows={chain.events} cols={EVENT_COLS} empty="近一年无措施 / 检修 / 状态变更记录" /> },
    { key: 'm', label: `措施（${counts.measures}）`,
      children: <ChainNode rows={chain.measures} cols={MEASURE_COLS} empty="暂无在案措施行" foot={chain.measureFoot} /> },
    { key: 'd', label: `设备（${counts.devices}）`,
      children: <ChainNode rows={chain.devices} cols={DEVICE_COLS} empty="本井无设备行" foot={chain.deviceFoot} /> },
    { key: 'r', label: `检修（${counts.overhauls}）`,
      children: <ChainNode rows={chain.overhauls} cols={OVERHAUL_COLS} empty="无检修记录" /> },
    { key: 'ch', label: `变动（${counts.changes}）`,
      children: <ChangeNode tickets={tickets} /> }
  ]
}

export default function A2Well() {
  const [wells, setWells] = useState(null)      // null＝列表未加载；[]＝空态（raw 8 表无业务数据的验收态）
  const [wellId, setWellId] = useState(null)    // 当前井——默认选中列表首口（合同「端点清单」注记）
  const [archive, setArchive] = useState(null)  // { profile, chain, tickets }——端点 2/3/4 整组原子换数据
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')        // errText 三段（client 已 toast，页面内联不重复弹）
  const seqRef = useRef(0)

  // 端点 1：选井列表（服务端按角色数据域过滤——无权井不在响应里，前端零二次
  // 过滤零打码，F48「看不到＝世界里没有」）。
  useEffect(() => {
    let cancelled = false
    listWells().then(
      res => {
        if (cancelled) return
        setWells(res.items)
        if (res.items.length) setWellId(res.items[0].wellId)
      },
      err => {
        if (cancelled) return
        setWells([])
        setError(errText(err))
      }
    )
    return () => { cancelled = true }
  }, [])

  // 端点 2/3/4 并发拉取（选井切换＝档案明细与关系链整组换数据——合同「端点
  // 清单」注记：真实＝并发拉＋Spin 遮罩）；seq 竞窗守卫——快速切井旧响应不回写。
  useEffect(() => {
    if (!wellId) return undefined
    const seq = ++seqRef.current
    setLoading(true)
    setError('')
    setArchive(null)
    Promise.all([getWellProfile(wellId), getWellChain(wellId), listWellChangeTickets(wellId)])
      .then(([profile, chain, tickets]) => {
        if (seq !== seqRef.current) return
        setArchive({ profile, chain, tickets })
        setLoading(false)
      })
      .catch(err => {
        if (seq !== seqRef.current) return
        setError(errText(err))
        setLoading(false)
      })
    return undefined
  }, [wellId])

  // F4 去问一问＝跳转 A1（不立新端点）；page_context {page:'A2',object_type:'well',
  // object_id} 的携带机制为 R-WIRE A2-16 登记项（拍板悬置，不阻塞读面接线）——
  // 拍板前维持纯跳转现状。
  function goAsk() { location.hash = '/A1' }

  const options = wells
    ? [...wells.map(w => ({ value: w.wellId, label: wellOptionLabel(w) })), NO_PERMISSION_OPTION]
    : []
  const emptyDescription = error
    || (wells === null ? '加载选井列表…' : '暂无可见井')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {!wellId ? (
        <Card size="small">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyDescription} />
        </Card>
      ) : (
        <Spin spinning={loading} tip="加载井档案…">
          {archive ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <Card size="small" title="档案明细"
                extra={
                  <Space>
                    <Select style={{ width: 300 }} value={wellId} options={options} onChange={setWellId} />
                    <Button type="primary" icon={<MessageOutlined />} onClick={goAsk}>问一问</Button>
                  </Space>
                }>
                  <Descriptions size="small" column={3} bordered
                    items={[
                      { key: 'id', label: '井号', children: archive.profile.wellId },
                      { key: 'name', label: '井名', children: archive.profile.wellName ?? '—' },
                      { key: 'kind', label: '井别', children: archive.profile.kindLabel ?? '—' },
                      { key: 'spud', label: '投产', children: archive.profile.firstProdDate ?? '—' },
                      { key: 'platform', label: '平台', children: archive.profile.platform ?? '—' },
                      { key: 'block', label: '区块', children: archive.profile.blockName ?? '—' },
                      { key: 'status', label: '状态', children: archive.profile.currentStatus
                        ? <Tag color={WELL_STATUS_COLOR[archive.profile.currentStatus] || 'default'}>{archive.profile.currentStatus}</Tag>
                        : '—' },
                      { key: 'note', label: '备注', children: archive.profile.remark ?? '—', span: 2 }
                    ]} />
                  {archive.profile.qualityNotes.map((q, i) => (
                    <div key={i} style={{ fontSize: 12, color: 'var(--pa-danger)', marginTop: 8 }}>{q}</div>
                  ))}
                  {archive.profile.footNote && (
                    <div style={{ fontSize: 12, color: 'var(--pa-text-tertiary)', marginTop: 8 }}>{archive.profile.footNote}</div>
                  )}
                </Card>
              <Card size="small" title="关系链">
                <Tabs className="a2-chain-tabs" items={chainTabs(archive.chain, archive.tickets)} />
                {archive.chain.tail && (
                  <div style={{ fontSize: 12, color: 'var(--pa-text-tertiary)', marginTop: 8 }}>{archive.chain.tail}</div>
                )}
              </Card>
            </div>
          ) : (
            <Card size="small">
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={error || '加载井档案…'} />
            </Card>
          )}
        </Spin>
      )}
    </div>
  )
}
