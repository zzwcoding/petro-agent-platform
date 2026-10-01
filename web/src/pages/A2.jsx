import { useState } from 'react'
import {
  Button, Card, Descriptions, Empty, Select, Space, Spin, Table, Tabs, Tag, Tooltip
} from 'antd'
import { MessageOutlined } from '@ant-design/icons'
import { DEV } from '../shell/TraceBar.jsx'
import { TICKETS } from '../data/changeTickets.jsx'

window.__traces = Object.assign(window.__traces || {}, {
  A2: 'F44 背景注入 · F45 对象查询 · F46 专业函数（递减风险）· F43 AgentOS 总纲 · F48 治理约束（无权限井灰显）· m16 对象关系 / m1 底座'
})

const WELL_OPTIONS = [
  { value: 'N-02', label: 'N-02 渤中28-1-N2（渤南 · 采油 · 生产中）' },
  { value: 'N-06', label: 'N-06（渤南 · 注水 · 分层注水 3 层）' },
  { value: 'N-11', label: 'N-11（渤中 · 采油 · 停产）' },
  { value: 'na', label: '（无查看权限的井不在此列表）', disabled: true }
]

const WELLS = {
  'N-02': {
    head: { id: 'N-02', name: '渤中28-1-N2', kind: '采油（EW）', spud: '2019-06-15', platform: 'CEP-A', block: '渤南', status: '生产中', ok: true, note: '正常' },
    quality: [],
    infoFoot: null,
    chain: {
      root: '井 N-02（采油 · 生产中 · 渤南 / CEP-A）',
      measures: [
        { key: 'm1', date: '2026-03-18', type: '调剖', content: '主力层段调剖，调整吸水剖面', result: '综合含水降 1.2 个点' },
        { key: 'm2', date: '2025-09-06', type: '酸化', content: '近井地带解堵酸化', result: '日增油约 3 吨，三个月后回落' },
        { key: 'm3', date: '2024-06-12', type: '补孔', content: 'Ⅱ油组补孔', result: '日增油约 5 吨' },
        { key: 'm4', date: '2023-04-20', type: '压裂', content: '主力层重复压裂', result: '日增油约 8 吨，递减较快' },
        { key: 'm5', date: '2022-08-15', type: '调剖', content: '笼统注水条件下调剖', result: '综合含水降 0.8 个点' }
      ],
      devices: [
        { key: 'd1', type: '电泵', status: '运行中', ok: true, since: '2021-04-12', note: '2021 年换泵更新；上次保养 2026-06-02' },
        { key: 'd2', type: '加热炉', status: '运行中', ok: true, since: '2019-09-01', note: '冬季高负荷、夏季低负荷' }
      ],
      overhauls: [
        { key: 'o1', from: '2024-10-09', to: '2024-10-11', job: '检泵（泵轴更换）', impact: '影响产量约 18 吨', batch: '批次 20241012-T2' }
      ],
      statusEvents: [],
      measureEnum: '措施类型枚举：压裂 / 酸化 / 补孔 / 调剖',
      deviceEnum: '设备类型枚举：电泵 / 螺杆泵 / 加热炉',
      tail: null
    }
  },
  'N-06': {
    head: { id: 'N-06', name: '—', kind: '注水（IW）', spud: '2019-08-01', platform: 'CEP-A', block: '渤南', status: '生产中', ok: true, note: '分层注水（3 层）' },
    quality: [],
    infoFoot: '注水井无日产油记录，"产量最高"类排名自动排除本井。',
    chain: {
      root: '井 N-06（注水 · 生产中 · 渤南 / CEP-A）',
      measures: [
        { key: 'm1', date: '2026-07-22', type: '调剖', content: 'P1 层调剖，控制单层突进', result: 'P1 实注占比回落 5 个点' },
        { key: 'm2', date: '2025-12-15', type: '调剖', content: '笼统注水改分层分注前调剖', result: '为 2026-01 三层分注投运做准备' },
        { key: 'm3', date: '2024-09-10', type: '调剖', content: 'P2 层调剖', result: 'P2 吸水剖面改善' },
        { key: 'm4', date: '2023-05-18', type: '调剖', content: '井组调剖', result: '受效油井组见效（响应起始日随台账）' }
      ],
      devices: [
        { key: 'd1', type: '电泵', status: '运行中', ok: true, since: '2020-01-20', note: '注水泵；泵压字段未采录（台账缺口）' },
        { key: 'd2', type: '加热炉', status: '运行中', ok: true, since: '2020-01-20', note: '注水管线伴热' }
      ],
      overhauls: [
        { key: 'o1', from: '2025-03-05', to: '2025-03-06', job: '注水泵保养性检修', impact: '影响约 0 吨（注水量当日回补）', batch: '批次 20250307-T1' }
      ],
      statusEvents: [
        { key: 's1', date: '2026-01-08', title: '注水方式变更为"分层注水（3 层）"', warn: null }
      ],
      measureEnum: '注水井措施以调剖为主（类型枚举：压裂 / 酸化 / 补孔 / 调剖）',
      deviceEnum: '设备类型枚举：电泵 / 螺杆泵 / 加热炉',
      tail: '关系：N-06 —受效→ 受效油井（劈分系数 Σ=1）——受效井清单未装配'
    }
  },
  'N-11': {
    head: { id: 'N-11', name: '—', kind: '采油（EW）', spud: '2020-02-20', platform: 'CEP-B', block: '渤中', status: '停产', ok: false, note: '2026-08-30 起检泵' },
    quality: [
      '台账状态"停产"与产量表 9-14 仍有开井 6.5 小时记录并存（状态滞后，已提示数据岗）。',
      '产量表单位误录：9-14 日产油 12.40"方"（按渤中密度 0.89 t/m³ 折算 ≈11.04 吨，已提示数据岗）。'
    ],
    infoFoot: null,
    chain: {
      root: '井 N-11（采油 · 停产 · 渤中 / CEP-B）',
      measures: [],
      devices: [
        { key: 'd1', type: '螺杆泵', status: '停机检修', ok: false, since: '2020-03-11', note: '本次检泵作业对象；停机原因编码：新 BELT（旧 R3＝皮带断）' },
        { key: 'd2', type: '加热炉', status: '随井停用', ok: false, since: '2020-03-11', note: '停产期间停用，复产后视情况投运' }
      ],
      overhauls: [
        { key: 'o1', from: '2026-08-28', to: '2026-09-06', job: '检泵', impact: '影响产量约 210 吨', batch: '批次 20260911-T3' },
        { key: 'o2', from: '2025-05-12', to: '2025-05-18', job: '检泵（皮带更换）', impact: '影响产量约 45 吨', batch: '批次 20250516-T1' },
        { key: 'o3', from: '2024-02-19', to: '2024-02-21', job: '检泵（机械密封更换）', impact: '影响产量约 15 吨', batch: '批次 20240222-T1' },
        { key: 'o4', from: '2023-07-06', to: '2023-07-09', job: '洗井（复产前）', impact: '影响产量约 3 吨', batch: '批次 20230710-T2' }
      ],
      statusEvents: [
        { key: 's1', date: '2026-08-30', title: '台账状态变更为"停产"',
          warn: '状态滞后：9-14 产量表仍有开井 6.5 小时记录，已提示数据岗。' },
        { key: 's2', date: '2026-09-07', title: '检泵结束，作业区申请复产',
          warn: '档案状态仍记"停产"：复产待确认，状态滞后自 9-07 起。' }
      ],
      measureEnum: '措施类型枚举：压裂 / 酸化 / 补孔 / 调剖',
      deviceEnum: '检泵作业对象＝抽油设备（类型枚举：电泵 / 螺杆泵 / 加热炉）',
      tail: '追溯结论：本井停产环节＝检泵作业（检修台账）；措施层无在案记录。遍历深度为受控参数'
    }
  }
}
if (DEV) {
  WELLS['N-02'].infoFoot = '（m16 对象关系 · W-F45-1）'
}

const MEASURE_COLS = [
  { title: '日期', dataIndex: 'date', width: 100 },
  { title: '类型', dataIndex: 'type', width: 70, render: t => <Tag>{t}</Tag> },
  { title: '内容', dataIndex: 'content' },
  { title: '效果', dataIndex: 'result' }
]
const DEVICE_COLS = [
  { title: '类型', dataIndex: 'type', width: 90, render: t => <Tag color="blue">{t}</Tag> },
  { title: '状态', dataIndex: 'status', width: 100, render: (t, r) => <Tag color={r.ok ? 'green' : 'red'}>{t}</Tag> },
  { title: '启用', dataIndex: 'since', width: 110 },
  { title: '备注', dataIndex: 'note' }
]
const OVERHAUL_COLS = [
  { title: '起止', width: 230, render: (_, r) => `${r.from} → ${r.to}` },
  { title: '作业', dataIndex: 'job', width: 150 },
  { title: '影响', dataIndex: 'impact' },
  { title: '批次', dataIndex: 'batch', width: 140 }
]

const EVENT_COLS = [
  { title: '时间', width: 210, render: (_, r) => (r.to ? `${r.from} → ${r.to}` : r.date) },
  { title: '类型', dataIndex: 'kind', width: 90, render: (t, r) => <Tag color={r.color}>{t}</Tag> },
  { title: '事项', dataIndex: 'title' },
  { title: '结果 / 影响', dataIndex: 'outcome' }
]

function buildEvents(chain) {
  return [
    ...chain.measures.map(m => ({ key: m.key, sort: m.date, date: m.date, kind: '措施', color: 'default',
      title: `${m.type} · ${m.content}`, outcome: m.result })),
    ...chain.overhauls.map(o => ({ key: o.key, sort: o.to, from: o.from, to: o.to, kind: '检修', color: 'orange',
      title: o.job, outcome: `${o.impact} · ${o.batch}` })),
    ...chain.statusEvents.map(s => ({ key: s.key, sort: s.date, date: s.date, kind: '状态变更', color: 'red',
      title: s.title, outcome: s.warn }))
  ].sort((a, b) => (a.sort < b.sort ? 1 : -1))
}

const ASK_COL = {
  title: '', width: 46,
  render: () => (
    <Tooltip title="去问一问">
      <Button type="text" size="small" icon={<MessageOutlined />}
        onClick={() => { location.hash = '/A1' }} />
    </Tooltip>
  )
}

const CH_STATUS = {
  pending: <Tag color="orange">待审批</Tag>,
  auto: <Tag color="green">已执行</Tag>,
  rejected: <Tag color="red">已驳回</Tag>,
  withdrawn: <Tag>已撤回</Tag>
}
const planeOf = t => (t.id.includes('CFG-') ? '配置面' : t.id.includes('ACC-') ? '语义面' : '数据面')
const CH_PLANE = { 数据面: <Tag color="blue">数据面</Tag>, 配置面: <Tag color="orange">配置面</Tag>, 语义面: <Tag color="purple">语义面</Tag> }

const CHANGE_COLS = [
  { title: '变动单', dataIndex: 'id', width: 150 },
  { title: '状态', dataIndex: 'status', width: 90, render: s => CH_STATUS[s] },
  { title: '面', width: 76, render: (_, t) => CH_PLANE[planeOf(t)] },
  { title: '事项', dataIndex: 'short' },
  { title: '提出', width: 250, render: (_, t) => <span style={{ color: '#8a94a3', fontSize: 12 }}>{t.proposer.replace('提出：', '')} · {t.time}</span> }
]

function ChangeNode({ wellId }) {
  const mine = TICKETS.filter(t => t.object.includes(wellId))
  return (
    <div>
      {mine.length
        ? <Table size="small" columns={CHANGE_COLS} dataSource={mine} pagination={false} />
        : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="本井暂无变动单" />}
      <div style={{ fontSize: 12, color: '#8a94a3', marginTop: mine.length ? 8 : 0 }}>
        只列涉及本井的单 · <a href="#/A3" style={{ color: '#4a9dff' }}>去数据变动审批看全部</a>
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
      {foot && <div style={{ fontSize: 12, color: '#8a94a3', marginTop: rows.length ? 8 : 0 }}>{foot}</div>}
    </div>
  )
}

const chainTabs = w => {
  const events = buildEvents(w.chain)
  return [
    { key: 'events', label: `纪录（${events.length}）`,
      children: <ChainNode rows={events} cols={EVENT_COLS} empty="近一年无措施 / 检修 / 状态变更记录" /> },
    { key: 'm', label: `措施（${w.chain.measures.length}）`,
      children: <ChainNode rows={w.chain.measures} cols={MEASURE_COLS} empty="暂无在案措施行" foot={w.chain.measureEnum} /> },
    { key: 'd', label: `设备（${w.chain.devices.length}）`,
      children: <ChainNode rows={w.chain.devices} cols={DEVICE_COLS} empty="本井无设备行" foot={w.chain.deviceEnum} /> },
    { key: 'r', label: `检修（${w.chain.overhauls.length}）`,
      children: <ChainNode rows={w.chain.overhauls} cols={OVERHAUL_COLS} empty="无检修记录" /> },
    { key: 'ch', label: `变动（${TICKETS.filter(t => t.object.includes(w.head.id)).length}）`,
      children: <ChangeNode wellId={w.head.id} /> }
  ]
}

export default function A2Well() {
  const [well, setWell] = useState('N-02')
  const [loading, setLoading] = useState(false)
  const w = WELLS[well]

  function switchWell(v) {
    if (v === well) return
    setLoading(true)
    setTimeout(() => { setWell(v); setLoading(false) }, 400)
  }
  function goAsk() { location.hash = '/A1' }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ flexShrink: 0 }}>
        <Card size="small" title="档案明细"
          extra={
            <Space>
              <Select style={{ width: 300 }} value={well} options={WELL_OPTIONS} onChange={switchWell} />
              <Button type="primary" icon={<MessageOutlined />} onClick={goAsk}>问一问</Button>
            </Space>
          }>
              <Descriptions size="small" column={3} bordered
                items={[
                  { key: 'id', label: '井号', children: w.head.id },
                  { key: 'name', label: '井名', children: w.head.name },
                  { key: 'kind', label: '井别', children: w.head.kind },
                  { key: 'spud', label: '投产', children: w.head.spud },
                  { key: 'platform', label: '平台', children: w.head.platform },
                  { key: 'block', label: '区块', children: w.head.block },
                  { key: 'status', label: '状态', children: <Tag color={w.head.ok ? 'green' : 'red'}>{w.head.status}</Tag> },
                  { key: 'note', label: '备注', children: w.head.note, span: 2 }
                ]} />
              {w.quality.map((q, i) => (
                <div key={i} style={{ fontSize: 12, color: '#ff4d4f', marginTop: 8 }}>{q}</div>
              ))}
              {w.infoFoot && (
                <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 8 }}>{w.infoFoot}</div>
              )}
            </Card>
        </div>

        <div>
          <Card size="small" title="关系链">
            <Spin spinning={loading} tip="加载井档案…" style={{ display: 'contents' }}>
              <Tabs className="a2-chain-tabs" items={chainTabs(w)} />
              {w.chain.tail && (
                <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 8 }}>{w.chain.tail}</div>
              )}
            </Spin>
          </Card>
        </div>
    </div>
  )
}
