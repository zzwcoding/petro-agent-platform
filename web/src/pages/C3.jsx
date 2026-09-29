import { useEffect, useRef, useState } from 'react'
import {
  Alert, Button, Card, Collapse, Empty, Input, Modal, Select, Space, Steps, Table, Tag, Tooltip
} from 'antd'
import {
  CheckCircleOutlined, FileSearchOutlined, PlayCircleOutlined, QuestionCircleOutlined,
  SafetyCertificateOutlined, StopOutlined
} from '@ant-design/icons'
import {
  GATE_SHORT, getCiOverview, listReleases, listDryRunCandidates, startCiDrill, getCiDrill, listCiDrills,
  getRedteamCases, startRedteamRun, getRedteamRun
} from '../api/c3.js'

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

// 结果标记（合同：过/拦下/不涉及/未跑——按阶段顺序执行，任一阶段"拦下"即停）
const RESULT_COLOR = { 过: 'green', 拦下: 'red', 不涉及: 'default', 未跑: 'default' }
const TARGET_COLORS = { 业务术语: 'purple', 指标口径: 'blue' }

// 流水线顺序 + 结果标记图例（台账标题 ? 收敛位）
const PIPELINE_HELP = (
  <>
    <b>流水线五阶段（按顺序执行，任一阶段"拦下"即停，绝不带病往下走）</b><br />
    格式检查（配置装载）→ 引用一致性 → 查询安全（只读 · 粒度 · 零分母）→ 治理合规（负责人 · 敏感字段 · 高影响审批）→ 行为回归（考核基准逐槽比对）<br />
    <b>结果标记</b>：过＝本阶段通过 · 拦下＝踩线到此为止 · 不涉及＝本变更无此类内容 · 未跑＝前面拦下短路不查<br />
    行为回归拿 E1 固化的当前基准（票 99）逐题逐槽重跑：基准判对的题全部仍判对才放行，不比评分；比对要求同配置（票 100）——配置不同属模型对比，不构成降级（<a href="#/E1">答题考核</a>）。<br />
    每条记录＝一次正式送检的流水线执行记录；主工单在语义修订提案池（C2），本页是它的检查执行视图。
  </>
)

const MONO = { fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12 }

export default function C3Ci() {
  const [overview, setOverview] = useState(null)
  const [query, setQuery] = useState({ status: 'all', gate: 0, keyword: '' })
  const [releases, setReleases] = useState({ items: [], total: 0, counts: { all: 0, published: 0, blocked: 0 } })
  const [releaseLoading, setReleaseLoading] = useState(true)
  const [openId, setOpenId] = useState(null)

  // 试运行（Dry run，服务端检查链任务流）
  const [dryRunOpen, setDryRunOpen] = useState(false)
  const [candidates, setCandidates] = useState([])
  const [dryTarget, setDryTarget] = useState(undefined)
  const [drill, setDrill] = useState(null)
  const [drillLogs, setDrillLogs] = useState([])
  const drillPoll = useRef(null)

  // 安全用例试跑
  const [cases, setCases] = useState(null)
  const [rt, setRt] = useState(null)
  const rtPoll = useRef(null)

  useEffect(() => {
    let on = true
    Promise.all([getCiOverview(), listCiDrills(), getRedteamCases(), listDryRunCandidates()]).then(([ov, dl, rc, dc]) => {
      if (!on) return
      setOverview(ov)
      setDrillLogs(dl)
      setCases(rc)
      setCandidates(dc)
    })
    return () => {
      on = false
      if (drillPoll.current) clearInterval(drillPoll.current)
      if (rtPoll.current) clearInterval(rtPoll.current)
    }
  }, [])

  useEffect(() => {
    let on = true
    setReleaseLoading(true)
    listReleases(query).then(d => { if (on) { setReleases(d); setReleaseLoading(false) } })
    return () => { on = false }
  }, [query])

  function runDrill(proposalId) {
    if (drillPoll.current || !proposalId) return
    startCiDrill(proposalId).then(({ runId }) => {
      setDrill({ status: 'running', nodes: null, result: null })
      drillPoll.current = setInterval(async () => {
        const d = await getCiDrill(runId)
        setDrill({ status: d.status, nodes: d.nodes, result: d.result })
        if (d.status === 'done') {
          clearInterval(drillPoll.current)
          drillPoll.current = null
          listCiDrills().then(setDrillLogs)
        }
      }, 300)
    })
  }

  function runRt() {
    if (rtPoll.current) return
    startRedteamRun('rt-01').then(({ runId }) => {
      setRt({ status: 'running', checks: [], conclusion: null })
      rtPoll.current = setInterval(async () => {
        const d = await getRedteamRun(runId)
        setRt({ status: d.status, checks: d.checks || [], conclusion: d.conclusion || null })
        if (d.status === 'done') {
          clearInterval(rtPoll.current)
          rtPoll.current = null
        }
      }, 300)
    })
  }

  const rec = releases.items.find(r => r.id === openId)
  const sem = overview?.semantic

  const recordCols = [
    {
      title: '变更', dataIndex: 'name', render: (v, r) => (
        <div>
          <b>{v}</b>
          <div style={{ fontSize: 12, color: '#8a94a3' }}>{r.summary}</div>
        </div>
      )
    },
    { title: '类型', dataIndex: 'target', width: 90, render: v => <Tag color={TARGET_COLORS[v]}>{v}</Tag> },
    {
      title: <span>版本{helpIcon('语义层全量版本：发布成功即从 from 升到 to，全平台问答按新版本作答。')}</span>,
      width: 120, dataIndex: 'version',
      render: (_, r) => <span style={MONO}>{r.version.from} → {r.version.to}</span>
    },
    {
      title: <span>提案单{helpIcon('主工单在语义修订提案池（C2）：提案点「送检」＝创建一条流水线执行记录；全部通过回写「已过安检」，人工批准后发布生效；拦下回写提案并附报告，改完可再次送检。')}</span>,
      dataIndex: 'proposal', width: 200,
      render: (_, r) => (
        <div>
          <span style={MONO}>{r.proposal.id}</span>
          <div style={{ fontSize: 12, color: '#8a94a3' }}>{r.proposal.name} · {r.proposal.state}</div>
        </div>
      )
    },
    { title: '时间', dataIndex: 'id', width: 100, render: v => <span style={{ fontSize: 12, color: '#8a94a3' }}>{`${v.slice(0, 4)}-${v.slice(5, 7)}-${v.slice(7, 9)}`}</span> },
    {
      title: '状态', dataIndex: 'blocked', width: 160,
      render: (_, r) => (r.blocked
        ? <Tag color="red">被「{GATE_SHORT[r.blocked - 1]}」拦下</Tag>
        : <Tag color="green">已发布 · {r.version.to}</Tag>)
    },
    {
      title: '操作', width: 76, align: 'center',
      render: (_, r) => (
        <Tooltip title="查看流水线明细">
          <Button size="small" icon={<FileSearchOutlined />} onClick={e => { e.stopPropagation(); setOpenId(r.id) }} />
        </Tooltip>
      )
    }
  ]

  const detailColumns = [
    { title: '阶段', dataIndex: 'gate', width: 260 },
    { title: '结果', dataIndex: 'result', width: 90, render: v => <Tag color={RESULT_COLOR[v]}>{v}</Tag> },
    { title: '为什么', dataIndex: 'why' }
  ]

  const casesTable = (
    <Table
      size="small" loading={!cases} pagination={false} rowKey="key" dataSource={cases || []}
      columns={[
        { title: '用例号', dataIndex: 'key', width: 76, render: v => <code>{v}</code> },
        { title: '藏刀位置', dataIndex: 'pos', width: 230 },
        { title: '触发问法', dataIndex: 'ask', width: 220 },
        { title: <span>期望断言{helpIcon('放行前逐条核对的检查点——断言不成立即拦。')}</span>, dataIndex: 'assert' },
        { title: '防线落点', dataIndex: 'line', width: 170, render: v => <Tag color="volcano">{v}</Tag> }
      ]}
    />
  )

  const rtChecksBlock = rt && (
    <>
      {rt.checks?.length > 0 && (
        <Table
          style={{ marginTop: 10 }} size="small" pagination={false} rowKey="name" dataSource={rt.checks}
          columns={[
            { title: '放行核对', dataIndex: 'name' },
            {
              title: '结果', dataIndex: 'state', width: 100,
              render: v => (v === 'done' ? <Tag color="green">成立</Tag> : v === 'running' ? <Tag color="processing">核对中…</Tag> : <Tag>待核对</Tag>)
            },
            { title: '说明', dataIndex: 'note' }
          ]}
        />
      )}
      {rt.status === 'done' && rt.conclusion && (
        <Alert style={{ marginTop: 8 }} type="success" showIcon message={rt.conclusion} />
      )}
    </>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ marginBottom: -8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ fontSize: 18, fontWeight: 600 }}>发布流水线</span>
          {helpIcon('指标口径、业务术语、查询模板与安全策略是平台回答问题的生产定义——修改走提案（C2）→ 流水线检查 → 人工批准发布，全程留痕、可回滚。')}
          {overview && (
            <Tooltip title={`${overview.lastBatch.time} · 最近批次 ${overview.lastBatch.id} · ${overview.lastBatch.result}`}>
              <Tag color="success" style={{ marginInlineEnd: 0, marginLeft: 8 }}><SafetyCertificateOutlined /> 安检引擎运行中 · 最近批次 {overview.lastBatch.id}</Tag>
            </Tooltip>
          )}
        </div>
        {sem && (
          <div style={{ marginTop: 6, fontSize: 13 }}>
            语义层当前生效版本 <b style={{ fontSize: 15 }}>{sem.current}</b>
            <span style={{ fontSize: 12, color: '#8a94a3', marginLeft: 8 }}>
              最近发布 {sem.lastRelease.time}（发布 #{sem.lastRelease.id}）· 累计发布 {releases.counts.published} 次 · 拦下 {releases.counts.blocked} 次
            </span>
          </div>
        )}
      </div>

      <Card
        size="small"
        title={<span>发布记录{helpIcon(PIPELINE_HELP)}</span>}
        extra={
          <Button size="small" icon={<PlayCircleOutlined />} onClick={() => setDryRunOpen(true)}>
            试运行（Dry run）
          </Button>
        }
      >
        <Space wrap style={{ marginBottom: 12 }}>
          <Select size="small" style={{ width: 130 }} value={query.status}
            onChange={v => setQuery(q => ({ ...q, status: v }))}
            options={[
              { value: 'all', label: '状态：全部' },
              { value: 'published', label: '已发布' },
              { value: 'blocked', label: '已拦下' }
            ]} />
          <Select size="small" style={{ width: 150 }} value={query.gate}
            onChange={v => setQuery(q => ({ ...q, gate: v }))}
            options={[
              { value: 0, label: '拦下阶段：全部' },
              ...GATE_SHORT.map((s, i) => ({ value: i + 1, label: `「${s}」拦下` }))
            ]} />
          <Input size="small" allowClear style={{ width: 240 }} value={query.keyword}
            onChange={e => setQuery(q => ({ ...q, keyword: e.target.value }))}
            placeholder="搜发布单号 / 变更对象…" />
          <span style={{ fontSize: 12, color: '#8a94a3' }}>筛选结果 {releases.total} 条</span>
        </Space>
        <Table
          size="small" columns={recordCols} dataSource={releases.items} pagination={false} rowKey="id"
          loading={releaseLoading}
          onRow={r => ({ onDoubleClick: () => setOpenId(r.id), style: { cursor: 'pointer' } })}
          locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有匹配的发布记录" /> }}
        />
      </Card>

      <Modal
        title={rec && (
          <Space wrap>
            {`发布 #${rec.id}`}
            <Tag color={TARGET_COLORS[rec.target]}>{rec.target}</Tag>
            <Tag color={rec.blocked ? 'red' : 'green'}>
              {rec.blocked ? `被「${GATE_SHORT[rec.blocked - 1]}」拦下` : `已发布 · ${rec.version.to}`}
            </Tag>
          </Space>
        )}
        open={!!openId} onCancel={() => setOpenId(null)} width={760} footer={null}
      >
        {rec && (
          <>
            <div style={{ fontSize: 13, marginBottom: 10 }}>
              变更：<b>{rec.name}</b>
              <span style={{ color: '#8a94a3', fontSize: 12, marginLeft: 8 }}>{`${rec.id.slice(0, 4)}-${rec.id.slice(5, 7)}-${rec.id.slice(7, 9)}`}</span>
            </div>
            <div style={{ fontSize: 13, marginBottom: 10, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <span>版本 <b style={MONO}>{rec.version.from} → {rec.version.to}</b>{rec.version.released && <Tag style={{ marginLeft: 6 }} color="green">已生效</Tag>}</span>
              <span>提交人：{rec.submitter}</span>
            </div>
            <div style={{ margin: '0 0 8px', fontWeight: 600 }}>流水线明细</div>
            <Table size="small" columns={detailColumns} pagination={false} rowKey="gate" dataSource={rec.detail} />
            <div style={{ marginTop: 12, borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: 12 }}>
              {rec.blocked ? (
                <span style={{ fontSize: 12, color: '#ff4d4f' }}>
                  <StopOutlined /> 被「{GATE_SHORT[rec.blocked - 1]}」拦下——整包退回<a href="#/C2">语义修订提案池</a>，改法提示附在提案上；改完重新提交、五阶段重过。
                </span>
              ) : (
                <span style={{ fontSize: 12, color: '#52c41a' }}>
                  <CheckCircleOutlined /> 已发布——五阶段全部通过，语义层版本升至 {rec.version.to}。
                </span>
              )}
            </div>
            {rec.detail[2]?.result !== '不涉及' && (
              <Collapse
                style={{ marginTop: 12 }}
                items={[{
                  key: 'rt',
                  label: '安全回归用例（注入防线 8 条）',
                  children: (
                    <>
                      {casesTable}
                      <Space style={{ marginTop: 10 }} wrap>
                        <Button size="small" icon={<PlayCircleOutlined />} loading={rt?.status === 'running'} onClick={runRt}>
                          试跑 rt-01 · 报告藏刀
                        </Button>
                        {rt?.status === 'running' && <span style={{ fontSize: 12, color: '#8a94a3' }}>放行核对执行中…</span>}
                      </Space>
                      {rtChecksBlock}
                    </>
                  )
                }]}
              />
            )}
          </>
        )}
      </Modal>

      <Modal
        title="试运行（Dry run）" open={dryRunOpen} onCancel={() => setDryRunOpen(false)} width={640} footer={null}
      >
        <Space wrap style={{ marginBottom: 12 }}>
          <span>变更包：</span>
          <Select
            style={{ minWidth: 300 }} placeholder="选择变更包（提案池「待审」清单）"
            value={dryTarget} onChange={v => { setDryTarget(v); setDrill(null) }}
            options={(candidates || []).map(c => ({ value: c.proposalId, label: `${c.proposalId} · ${c.name}` }))}
          />
          <Button type="primary" size="small" icon={<PlayCircleOutlined />} disabled={!dryTarget}
            loading={drill?.status === 'running'} onClick={() => runDrill(dryTarget)}>
            开始试运行
          </Button>
          {drill?.status === 'running' && <span style={{ fontSize: 12, color: '#8a94a3' }}>流水线执行中…</span>}
        </Space>
        {drill?.nodes ? (
          <div style={{ maxWidth: 480 }}>
            <Steps
              size="small" direction="vertical"
              items={drill.nodes.map(n => ({ title: n.label, description: n.note, status: n.state }))}
            />
            {drill.status === 'done' && drill.result && (
              <>
                <Alert style={{ marginTop: 12 }} type="error" showIcon message={drill.result.reason} />
                <Alert style={{ marginTop: 8 }} type="warning" showIcon message={drill.result.conclusion} />
              </>
            )}
          </div>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚未试运行——开始后按五阶段顺序执行，任一阶段不过即停。" />
        )}
        <div style={{ marginTop: 16 }}>
          <b style={{ fontSize: 13 }}>试运行记录{helpIcon('每次试运行留一行：哪个阶段拦的、结果如何——试运行与真实发布走同一条流水线，但不产生正式发布、不推进版本号。')}</b>
          <Table
            style={{ marginTop: 8 }} size="small" pagination={false} rowKey="id" dataSource={drillLogs}
            columns={[
              { title: '时间', dataIndex: 'time', width: 100 },
              { title: '变更包', dataIndex: 'script', width: 190 },
              { title: '拦下阶段', dataIndex: 'gate' },
              { title: '结果', dataIndex: 'result', width: 80, render: v => <Tag color="red">{v}</Tag> }
            ]}
            locale={{ emptyText: <Empty description="暂无试运行记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          />
        </div>
      </Modal>
    </div>
  )
}
