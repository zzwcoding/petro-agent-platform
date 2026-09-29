import { useEffect, useRef, useState } from 'react'
import {
  Alert, Button, Card, Col, Input, message, Progress, Row, Select, Skeleton, Space, Spin, Steps, Table, Tabs, Tag, Tooltip, Typography
} from 'antd'
import { QuestionCircleOutlined } from '@ant-design/icons'
// 数据与操作全部走 api 层（mock）：契约见 specs/api/E3-知识体检.md，页面组件不持有业务数据
import { RUN_STEPS, getCheckupObjects, getCheckupStatus, startCheckupRun, getCheckupRun, confirmSuggestion } from '../api/e3.js'

window.__guides = Object.assign(window.__guides || {}, {
  E3: [
    '「对象体检」页签默认选中 N-11——右侧出四维分数条，总评"需补课"标红。',
    '看 N-11 的短板——逻辑维度 62 分，"档案状态滞后"等 3 条建议。',
    '表格上方按 类型 / 总评 筛选，搜索框按对象名或建议文字模糊搜；灰字实时显示「筛选结果 n / 10 个」。',
    '点表格一行换对象（如区块渤中）——右侧报告切换，"孤儿关系"被体检抓出来。',
    '换选指标递减增油——两作业区算法不一致挂"口径待裁决"。',
    '每条建议都标了缺什么类型——缺来源 / 缺负责人 / 口径待裁决 / 逻辑打架 / 孤儿关系 / 资料缺项（悬浮「补全建议」旁 ? 看说明）。',
    '建议可「确认 · 转提案」——确认后归一体检发现单进 C2（已有提案的建议预置为已确认，绿色标出）；确认只归一不改正，平台不自己改。',
    '「立即体检」是真任务：四步流水（扫描四本账→逐对象评分→生成建议→归一发现单），跑完"上次体检"回填；周期调度才是主入口。',
    '切「体检发现示例」页签——一条体检发现归一成体检发现单：来源 / 对象坐标 / 现象 / 证据 / 证据形态 L1 / 去向；机器初诊、负责人确诊。',
    '看顶部灰字——建议经人确认才进语义修订提案池，平台不自己改。'
  ]
})
window.__traces = Object.assign(window.__traces || {}, { E3: 'F24 三源提案池+体检 · m16/m18 卡' })

const E_TABS = [
  { key: 'E1', label: '答题考核' },
  { key: 'E2', label: '数据质量台' },
  { key: 'E3', label: '知识体检' }
]

// 体检发现单（五字段）：取值全部来自既有内容——渤中区块的孤儿关系建议（断边类 · L1 结构差集）
const FINDING_ROWS = [
  { k: 'source', item: '来源', text: '自动体检发现' },
  { k: 'object_ref', item: '对象坐标', text: '渤中区块（区块 · 对象与关系台账）' },
  { k: 'symptom', item: '现象', text: '有井没挂上"井—隶属→区块"关系——按区块汇总时会漏井' },
  { k: 'evidence', item: '证据', text: '四维评分「关系健全不健全」82 分（总评：亚健康）；建议原文：有井没挂上"井—隶属→区块"关系——按区块汇总时会漏井' },
  { k: 'evidence_class', item: '证据形态', text: 'L1' },
  { k: 'target', item: '去向', text: '对象与关系（语义修订提案池收这一类：业务术语 ✓ 指标口径 ✓ 对象与关系 ✓；工作流 / Action 合同不收）' }
]
const FINDING_COLS = [
  { title: '项', dataIndex: 'item', width: 92 },
  {
    title: '内容', dataIndex: 'text',
    render: (v, r) => (r.k === 'evidence_class'
      ? <Tag color="blue">{v} 结构差集</Tag>
      : <span style={{ fontSize: 13 }}>{v}</span>)
  }
]

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

const DIM_SHORT = ['资料', '逻辑', '覆盖', '关系']
const GRADE_COLOR = { 健康: 'green', 亚健康: 'gold', 需补课: 'red' }
const AMBER_TAGS = ['口径待裁决', '逻辑打架']

// 票 102 §五 体检触发三路（补空白）：周期调度（主）／人工立即跑／变更触发（汇入 Verify 站内嵌）
const TRIGGER_HELP = (
  <>体检触发三路（票 102 §五）：<br />
  · <b>周期调度（主入口）</b>——调度器 cron，每日 02:00 全量四本账四维体检，产出归一成体检发现单进 C2（source＝自动体检发现）；<br />
  · <b>人工立即跑</b>——发布前 / 大改后点「立即体检」（本次演示走这路）；<br />
  · <b>变更触发</b>——台账单据生效后增量体检受影响对象（汇入合同 Verify 站内嵌，票 102 §六）。<br />
  状态行当前为演示数据；真实接调度器后接真值。</>
)

export default function E3Checkup() {
  const [tab, setTab] = useState('objects')
  const [loading, setLoading] = useState(true)
  const [objects, setObjects] = useState([])
  const [dims, setDims] = useState([])
  const [sel, setSel] = useState('N-11')
  const [typeF, setTypeF] = useState('all')
  const [gradeF, setGradeF] = useState('all')
  const [kw, setKw] = useState('')
  const [lastCheckup, setLastCheckup] = useState('')
  const [statusInfo, setStatusInfo] = useState({ nextPlanned: '', totalFindingsToC2: 7 })
  const [running, setRunning] = useState(false)
  const [runStep, setRunStep] = useState(0)
  const [checkupAlert, setCheckupAlert] = useState(false)
  const runningRef = useRef(false)

  useEffect(() => {
    Promise.all([getCheckupObjects(), getCheckupStatus()])
      .then(([rs, st]) => {
        setObjects(rs.items)
        setDims(rs.dims)
        setLastCheckup(st.lastCheckup)
        setStatusInfo({ nextPlanned: st.nextPlanned, totalFindingsToC2: st.totalFindingsToC2 })
        setLoading(false)
      })
  }, [])

  const objMap = Object.fromEntries(objects.map(o => [o.key, o]))
  const obj = objMap[sel]

  function pick(key) {
    setSel(key)
  }

  async function runCheckupNow() {
    if (runningRef.current) return
    runningRef.current = true
    setRunning(true)
    setRunStep(0)
    try {
      const { runId } = await startCheckupRun()
      for (;;) {
        const r = await getCheckupRun(runId)
        if (r.status === 'done') {
          setLastCheckup(r.finishedAt)
          setCheckupAlert(true)
          break
        }
        setRunStep(r.step)
        await new Promise(res => setTimeout(res, 250))
      }
    } catch (e) {
      message.warning(e.message)
    } finally {
      setRunning(false)
      runningRef.current = false
    }
  }

  async function confirmAndPropose(objectKey, idx) {
    try {
      const res = await confirmSuggestion(objectKey, idx)
      setObjects(prev => prev.map(o => (o.key === objectKey
        ? { ...o, sugg: o.sugg.map((s, i) => (i === idx ? { ...s, confirmed: res.confirmed } : s)) }
        : o)))
      message.success('已确认并归一体检发现单进 C2')
    } catch (e) {
      message.warning(e.message)
    }
  }

  const filtered = objects.filter(o => {
    const q = kw.trim().toLowerCase()
    return (typeF === 'all' || o.type === typeF)
      && (gradeF === 'all' || o.grade === gradeF)
      && (!q || (o.name + o.sugg.map(s => s.tag + s.text).join('')).toLowerCase().includes(q))
  })

  const objectColumns = [
    { title: '对象', dataIndex: 'name', render: (v, r) => <b style={{ fontSize: 13 }}>{r.label}</b> },
    {
      title: (<span>四维分数{helpIcon(<>四个维度按序：资料全不全 / 逻辑顺不顺 / 数据覆盖够不够 / 关系健全不健全；低于 70 分标黄。</>)}</span>),
      width: 210,
      render: (_, r) => (
        <span style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
          {r.scores.map((s, i) => (
            <span key={i} style={{ color: s < 70 ? '#faad14' : undefined }}>
              {i > 0 && ' · '}{DIM_SHORT[i]} {s}
            </span>
          ))}
        </span>
      )
    },
    { title: '总评', dataIndex: 'grade', width: 78, render: v => <Tag color={GRADE_COLOR[v]}>{v}</Tag> },
    { title: '建议', width: 52, align: 'center', render: (_, r) => `${r.sugg.length} 条` }
  ]

  const objectsPanel = (
    <Row gutter={16} align="top">
      <Col span={10}>
        <Card
          size="small"
          title={<span>体检对象{helpIcon(<>对象清单来自平台的四本账（业务术语 / 指标口径 / 对象与关系 / 分析工作流 → C1 指标与术语库）；点一行选中，右侧出该对象的体检报告。</>)}</span>}
        >
          <Space wrap size={8} style={{ marginBottom: 8 }}>
            <Select
              size="small" style={{ width: 100 }} value={typeF} onChange={setTypeF}
              options={[{ value: 'all', label: '类型：全部' }, { value: '井', label: '井' }, { value: '区块', label: '区块' }, { value: '指标', label: '指标' }]}
            />
            <Select
              size="small" style={{ width: 116 }} value={gradeF} onChange={setGradeF}
              options={[{ value: 'all', label: '总评：全部' }, { value: '健康', label: '健康' }, { value: '亚健康', label: '亚健康' }, { value: '需补课', label: '需补课' }]}
            />
            <Input size="small" allowClear style={{ width: 150 }} value={kw}
              onChange={e => setKw(e.target.value)} placeholder="搜对象 / 建议…" />
            <span style={{ fontSize: 12, color: '#8a94a3' }}>
              筛选结果 {filtered.length} / {objects.length} 个
            </span>
          </Space>
          <Table
            size="small"
            columns={objectColumns}
            dataSource={filtered}
            rowKey="key"
            pagination={false}
            scroll={{ y: 320 }}
            rowClassName={r => (r.key === sel ? 'ant-table-row-selected' : '')}
            onRow={r => ({
              onClick: () => pick(r.key),
              style: { cursor: 'pointer' }
            })}
          />
        </Card>
      </Col>
      <Col span={14}>
        <Card
          size="small"
          title={<span>四维体检报告{helpIcon(<>
            四个维度：① 资料全不全——该有的档案、说明在不在；② 逻辑顺不顺——说法之间打不打架；③ 数据覆盖够不够——底下的数齐不齐；④ 关系健全不健全——跟别的对象连没连上。<br />
            低于 70 分的维度分数条标黄；每条补全建议标注缺什么类型。
          </>)}</span>}
        >
          {loading || !obj ? (
            <Skeleton active paragraph={{ rows: 6 }} />
          ) : (
            <>
              <div style={{ marginBottom: 4 }}>
                <Typography.Title level={4} style={{ margin: 0, display: 'inline' }}>{obj.name}</Typography.Title>
                <Tag style={{ marginLeft: 8 }}>{obj.type}</Tag>
                <Tag color={GRADE_COLOR[obj.grade]} style={{ marginLeft: 4 }}>总评：{obj.grade}</Tag>
              </div>
              <div style={{ marginTop: 12 }}>
                {dims.map((d, i) => (
                  <div key={d} style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
                    <span style={{ width: 140, flexShrink: 0, fontSize: 13 }}>{d}</span>
                    <Progress
                      percent={obj.scores[i]}
                      format={v => `${v} 分`}
                      strokeColor={obj.scores[i] < 70 ? '#faad14' : undefined}
                      style={{ flex: 1, margin: 0 }}
                    />
                  </div>
                ))}
              </div>
              <div style={{ fontWeight: 600, marginTop: 12, marginBottom: 8 }}>
                补全建议（{obj.sugg.length} 条）
                {helpIcon(<>每条建议标注缺什么类型：缺来源 / 缺负责人 / 口径待裁决 / 逻辑打架 / 孤儿关系 / 资料缺项；「口径待裁决 / 逻辑打架」用黄色标出。<br />建议经人确认才进语义修订提案池——平台只归一，不自己改。</>)}
              </div>
              {obj.sugg.length === 0 ? (
                <div style={{ color: '#8a94a3' }}>暂无缺项。</div>
              ) : (
                obj.sugg.map((s, i) => (
                  <div
                    key={i}
                    style={{ marginBottom: 8, padding: '6px 10px', background: 'rgba(255,255,255,0.04)', borderRadius: 6 }}
                  >
                    <Tag color={AMBER_TAGS.includes(s.tag) ? 'gold' : 'default'} style={{ marginRight: 8 }}>{s.tag}</Tag>
                    <span style={{ fontSize: 13 }}>{s.text}</span>
                    <span style={{ float: 'right' }}>
                      {s.confirmed ? (
                        <span style={{ fontSize: 12 }}>
                          <Tag color="green" style={{ marginInlineEnd: 4 }}>{s.confirmed}</Tag>
                          <Button size="small" type="link" style={{ padding: 0 }} onClick={() => { location.hash = '/C2' }}>去提案池查看</Button>
                        </span>
                      ) : (
                        <Button size="small" onClick={() => confirmAndPropose(obj.key, i)}>确认 · 转提案</Button>
                      )}
                    </span>
                  </div>
                ))
              )}
            </>
          )}
        </Card>
      </Col>
    </Row>
  )

  const findingPanel = (
    <Card
      size="small"
      title={<span>体检发现单 · 渤中区块{helpIcon(<>
        体检产出的是结构证据（断边清单、缺字段率这类），可直接支撑提案池的改动。<br />
        一条体检发现归一成一张体检发现单：来源 / 对象坐标 / 现象 / 证据 / 证据形态 / 去向——与语义修订提案池（C2）提案卡的诊断段同构。<br />
        证据形态 L1＝结构差集（如断边清单），可直接成提案；机器初诊、负责人确诊。
      </>)}</span>}
    >
      <Table size="small" columns={FINDING_COLS} dataSource={FINDING_ROWS} pagination={false} rowKey="k" />
    </Card>
  )

  return (
    <div>
      <Tabs activeKey="E3" items={E_TABS} onChange={k => { location.hash = '/' + k }} style={{ marginBottom: 16 }} />
      <Card
        title={
          <Tabs
            activeKey={tab} size="small" onChange={setTab}
            items={[
              { key: 'objects', label: `对象体检（${objects.length}）` },
              { key: 'finding', label: '体检发现示例（1）' }
            ]}
          />
        }
        extra={
          <Space size={4}>
            <span style={{ color: '#8a94a3', fontSize: 12 }}>
              体检只出评分与建议 · 建议经人确认才进语义修订提案池 · 平台不自己改
            </span>
            {helpIcon(<>
              给平台的知识底子做体检：每口井、每个区块、每个指标按四个维度打分，缺什么、哪里断了关系，列出补全建议。<br />
              · 对象清单来自平台的四本账（业务术语 / 指标口径 / 对象与关系 / 分析工作流 → C1 指标与术语库）；<br />
              · 补全建议经人确认后进 C2 语义修订提案池——「自动体检发现」是提案池三个来源之一，另两个是考核没通过和用户反馈；<br />
              · 体检只出评分与建议，改不改由人在提案池定，平台不自己改。
            </>)}
          </Space>
        }
      >
        {loading ? (
          <Skeleton active paragraph={{ rows: 10 }} />
        ) : (
          <>
            {/* 票 102 §五：体检触发三路状态行 ＋「立即体检」异步任务（人工路） */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, marginBottom: 12 }}>
              <Space size={6} wrap>
                <span style={{ fontSize: 12 }}>
                  {`上次体检：${lastCheckup}｜下次计划：${statusInfo.nextPlanned}｜累计发现：${statusInfo.totalFindingsToC2} 条进 C2`}
                </span>
                <Tag style={{ marginInlineEnd: 0 }}>演示数据</Tag>
                {helpIcon(TRIGGER_HELP)}
              </Space>
              <Space size={8}>
                {running && <Spin size="small" />}
                <Button size="small" disabled={running} onClick={runCheckupNow}>立即体检</Button>
              </Space>
            </div>
            {running && (
              <Steps
                size="small" current={runStep}
                status="process"
                items={RUN_STEPS.map(t => ({ title: t }))}
                style={{ marginBottom: 12, maxWidth: 760 }}
              />
            )}
            {checkupAlert && (
              <Alert
                style={{ marginBottom: 12 }} type="success" showIcon closable
                message="全量体检任务已完成——发现将归一成体检发现单进 C2（同库同数，评分与建议不变；演示：周期调度为主入口）"
                onClose={() => setCheckupAlert(false)}
              />
            )}
            {tab === 'objects' && objectsPanel}
            {tab === 'finding' && findingPanel}
          </>
        )}
      </Card>
    </div>
  )
}
