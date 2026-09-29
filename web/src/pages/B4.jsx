import { useState } from 'react'
import {
  Alert, Button, Card, Col, Descriptions, Empty, Input, Row, Select, Space, Table, Tabs, Tag, Tooltip
} from 'antd'
import {
  ArrowLeftOutlined, DiffOutlined, FileTextOutlined, QuestionCircleOutlined, RollbackOutlined
} from '@ant-design/icons'

window.__guides = Object.assign(window.__guides || {}, {
  B4: [
    '「百科页」页签是全部百科页的目录：点《N-02 井完井报告》行尾的打开图标（或双击行）进入页面内容。',
    '「页面内容」里点摘要中的"N-02"——跳到井对象卡，看词条自动变链接。',
    '看关键参数"平台"行——CEP-B 带红标：与井档案对不上，是 v3 自动重建时把井链错的。',
    '切「版本历史」页签，点 v2——看 v1→v2 差异（新增"表格摘录"）；再点"回滚"——当前版变 v2，平台恢复 CEP-A（回「页面内容」页签可见），回滚本身也记成一次新提交。',
    '目录里另一页《渤中28-1 区块月度生产月报》——只有 1 版、各字段正常，与上一页对比着看。'
  ]
})
window.__traces = Object.assign(window.__traces || {}, {
  B4: 'F50 百科页 · F51 自动链接 · F52 版本回滚 · m6 卡'
})

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

// —— 百科页目录（每个开了百科开关的库自动生成首页目录；内容全部取自页面既有事实）——
const PAGES = [
  {
    key: 'w1',
    title: '《N-02 井完井报告》',
    lib: '完井报告库',
    src: '《N-02 井完井报告（英文 · 200 页）》',
    updated: '2026-09-20'
  },
  {
    key: 'w2',
    title: '《渤中28-1 区块月度生产月报》',
    lib: '生产月报库',
    src: '《渤中28-1 区块月度生产月报（2026-08）》',
    updated: '2026-09'
  }
]
const LIB_COLORS = { 完井报告库: 'blue', 生产月报库: 'purple' }

// 词条自动链接：点页内词条 → 页面滚动到本页的井对象卡
function WellLink({ id }) {
  return <a href="#wellcard" onClick={e => {
    e.preventDefault()
    document.getElementById('wellcard')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }}>{id}</a>
}

// —— 页面内容：摘要 / 关键参数 / 表格摘录 / 井对象卡（w1 平台行随版本联动，dyn 标记）——
const CONTENT = {
  w1: {
    summary: (
      <>本报告为 <WellLink id="N-02" /> 井（<WellLink id="渤中28-1" />-N2）完井报告：井位于渤南区块 CEP-A 平台，井别采油，2019-06-15 投产，状态生产中；正文含完井段与投产信息，插图含岩性柱状图等。</>
    ),
    summaryHelp: '摘要由报告全文自动浓缩；带链接的词条（井号、区块名）由平台识别后自动挂上，点击跳到本页下方的井对象卡。报告重新解析后，词条链接沿用原词条页原地更新——不会另建新页、旧链接不断。',
    paramsHelp: '参数值取自报告原文与井档案；与井档案对不上的字段会就地标红提示。',
    params: [
      { k: '井号', v: 'N-02' },
      { k: '井名', v: '渤中28-1-N2' },
      { k: '井别', v: '采油（EW）' },
      { k: '投产日期', v: '2019-06-15' },
      { k: '平台', dyn: 'platform' },
      { k: '区块', v: '渤南' },
      { k: '状态', v: '生产中' }
    ],
    excerptHelp: '摘自报告附表并已中文化；吨↔方换算＝质量÷密度，原油密度按区块：渤南 0.86 / 渤中 0.89 / 渤西 0.91（t/m³）。',
    excerptColumns: [
      { title: '井号', dataIndex: 'well', width: 80 },
      { title: '日期', dataIndex: 'date', width: 110 },
      { title: '日产油（吨）', dataIndex: 'oil' },
      { title: '日产液（方）', dataIndex: 'liquid', width: 120 },
      { title: '备注', dataIndex: 'note' }
    ],
    excerptRows: [
      { key: 1, well: 'N-02', date: '2026-09-14', oil: '48.60', liquid: '165.30', note: '样本日' },
      { key: 2, well: 'N-11', date: '2026-09-14', oil: '12.40（误录"方"，折算约 11.04 吨）', liquid: '96.00', note: '油量单位误录，按渤中密度 0.89 折算' }
    ],
    cardTitle: '对象卡：井 N-02',
    cardRows: () => [
      <Descriptions.Item key="a" label="井号">N-02</Descriptions.Item>,
      <Descriptions.Item key="b" label="井名">渤中28-1-N2</Descriptions.Item>,
      <Descriptions.Item key="c" label="井别">采油（EW）</Descriptions.Item>,
      <Descriptions.Item key="d" label="投产">2019-06-15</Descriptions.Item>,
      <Descriptions.Item key="e" label="平台">CEP-A</Descriptions.Item>,
      <Descriptions.Item key="f" label="区块">渤南</Descriptions.Item>,
      <Descriptions.Item key="g" label="状态">生产中</Descriptions.Item>,
      <Descriptions.Item key="h" label="关联注水井" span={2}>
        N-06（受效关系见 → <a href="#/B5">关系图谱</a>）
      </Descriptions.Item>
    ]
  },
  w2: {
    summary: (
      <>本报告为渤中28-1 区块 2026-08 月度生产月报：本月 <WellLink id="N-11" /> 井检泵停产（2026-08-28 起，跨月至 09-06），影响产量约 210 吨；渤中区块原油密度按 0.89 t/m³ 折算。</>
    ),
    summaryHelp: '摘要由月报全文自动浓缩；带链接的词条（井号）由平台识别后自动挂上，点击跳到本页下方的井对象卡。报告重新解析后，词条链接沿用原词条页原地更新——不会另建新页、旧链接不断。',
    paramsHelp: '参数值取自月报原文与井档案。',
    params: [
      { k: '报告期', v: '2026-08' },
      { k: '所属区块', v: '渤中28-1' },
      { k: '所属库', v: '生产月报库' },
      { k: '涉及井', v: <WellLink id="N-11" /> },
      { k: '本月检修', v: 'N-11 检泵（2026-08-28 → 2026-09-06，跨月）' },
      { k: '影响产量', v: '约 210 吨' },
      { k: '折算口径', v: '渤中区块密度 0.89 t/m³' },
      { k: '补录批次', v: '20260911-T3（事后补录）' }
    ],
    excerptHelp: '摘自月报正文与附表；吨↔方换算＝质量÷密度，渤中区块按 0.89 t/m³。',
    excerptColumns: [
      { title: '摘录项', dataIndex: 'item', width: 110 },
      { title: '内容', dataIndex: 'what' },
      { title: '数值', dataIndex: 'num', width: 110 },
      { title: '说明', dataIndex: 'note', width: 240 }
    ],
    excerptRows: [
      { key: 1, item: '检修影响产量', what: 'N-11 井检泵：2026-08-28 → 2026-09-06（跨月）', num: '约 210 吨', note: '事后补录，批次 20260911-T3' },
      { key: 2, item: '日产油折算', what: 'N-11 一行日产油误录单位"方"（报出 12.40 方）', num: '约 11.04 吨', note: '按渤中密度 0.89 t/m³ 折算（吨↔方＝质量÷密度）' }
    ],
    cardTitle: '对象卡：井 N-11',
    cardRows: () => [
      <Descriptions.Item key="a" label="井号">N-11</Descriptions.Item>,
      <Descriptions.Item key="b" label="井别">采油（EW）</Descriptions.Item>,
      <Descriptions.Item key="c" label="投产">2020-02-20</Descriptions.Item>,
      <Descriptions.Item key="d" label="平台">CEP-B</Descriptions.Item>,
      <Descriptions.Item key="e" label="区块">渤中</Descriptions.Item>,
      <Descriptions.Item key="f" label="状态">停产（2026-08-30 起检泵）</Descriptions.Item>
    ]
  }
}

// —— 版本历史与差异对比（每次重建落一版）——
const VERSIONS = {
  w1: [
    { v: 1, date: '2026-09-15', desc: '首次生成（报告入库自动建页）' },
    { v: 2, date: '2026-09-18', desc: '报告重新解析后自动重建（新增"表格摘录"）' },
    { v: 3, date: '2026-09-20', desc: '自动重建（链错了井）' }
  ],
  w2: [
    { v: 1, date: '2026-09', desc: '首次生成（报告入库自动建页）' }
  ]
}

const DIFF_COLUMNS = [
  { title: '位置', dataIndex: 'pos', width: 160 },
  { title: '上一版', dataIndex: 'from' },
  { title: '该版', dataIndex: 'to' }
]

const DIFFS = {
  w1: {
    1: {
      title: 'v0 → v1（首次生成）',
      body: '首次生成，无上一版可比。重建只取文字块拼回，重叠部分去重后全文通顺。'
    },
    2: {
      title: 'v1 → v2',
      rows: [{ pos: '表格摘录', from: '（无）', to: '新增：报告附表中文化摘录 1 张' }],
      tail: '其余内容逐字未变。'
    },
    3: {
      title: 'v2 → v3（引入错误的一版）',
      rows: [{
        pos: '关键参数 · 平台', from: 'CEP-A',
        to: <span>CEP-B <Tag color="error">错——自动重建时把井链错了（井档案：N-02 平台为 CEP-A）</Tag></span>
      }],
      tail: '其余内容逐字未变。'
    }
  },
  w2: {
    1: {
      title: 'v0 → v1（首次生成）',
      body: '首次生成，无上一版可比。重建只取文字块拼回，重叠部分去重后全文通顺。'
    }
  }
}

const VER_HELP = '每次重建都落一个版本：点任一版看它与上一版的逐字差异；发现改错点"回滚"恢复到上一版，回滚本身也记成一次新提交、可再滚回。'

export default function B4() {
  const [tab, setTab] = useState('catalog') // catalog | read | versions
  const [pageKey, setPageKey] = useState('w1')
  const [verCur, setVerCur] = useState({ w1: 3, w2: 1 }) // 各页当前版
  const [verSel, setVerSel] = useState({ w1: 3, w2: 1 }) // 各页差异面板选中版
  const [banner, setBanner] = useState(null)
  const [libF, setLibF] = useState('all')
  const [kw, setKw] = useState('')
  const [selRow, setSelRow] = useState(null)

  const page = PAGES.find(p => p.key === pageKey)
  const content = CONTENT[pageKey]

  function openPage(key) {
    setPageKey(key)
    setBanner(null)
    setTab('read')
  }

  function rollback() {
    if (pageKey === 'w1') {
      if (verCur.w1 === 3) {
        setVerCur(s => ({ ...s, w1: 2 })); setVerSel(s => ({ ...s, w1: 2 }))
        setBanner({ kind: 'success', text: '已回滚：当前版 = v2，平台恢复 CEP-A。注意：回滚本身也记成一次新提交（可再滚回）。' })
      } else {
        setBanner({ kind: 'info', text: '当前已是回滚后的版本（v2）。回滚本身也记成一次新提交，可继续回滚到更早版本。' })
      }
    }
  }

  const q = kw.trim().toLowerCase()
  const filtered = PAGES.filter(p =>
    (libF === 'all' || p.lib === libF)
    && (!q || (p.title + p.src + p.lib).toLowerCase().includes(q)))

  function statusTagOf(key) {
    if (key === 'w1' && verCur.w1 === 3) return <Tag color="orange">字段待核对</Tag>
    return <Tag color="green">正常</Tag>
  }

  const catalogColumns = [
    {
      title: '百科页', dataIndex: 'title',
      render: (v, p) => (
        <div>
          <b style={{ fontSize: 13 }}>{v}</b>
          <div style={{ fontSize: 12, color: '#8a94a3' }}>来源：{p.src}</div>
        </div>
      )
    },
    {
      title: '所属库', dataIndex: 'lib', width: 120,
      render: v => <Tag color={LIB_COLORS[v]}>{v}</Tag>
    },
    {
      title: '当前版', width: 110,
      render: (_, p) => <span>v{verCur[p.key]}（共 {VERSIONS[p.key].length} 版）</span>
    },
    { title: '最近更新', dataIndex: 'updated', width: 110 },
    {
      title: <span>状态{helpIcon(<>最近一次重建后的核对结果：百科页字段与井档案对不上时标"字段待核对"；回滚恢复后转回"正常"。核对出的对不上项由相关负责人认领处理后消除标红。</>)}</span>,
      width: 120, render: (_, p) => statusTagOf(p.key)
    },
    {
      title: '操作', width: 64, align: 'center',
      render: (_, p) => (
        <Tooltip title="打开百科页">
          <Button size="small" icon={<FileTextOutlined />}
            onClick={e => { e.stopPropagation(); openPage(p.key) }} />
        </Tooltip>
      )
    }
  ]

  // w1 的「平台」参数行随当前版联动（v3＝CEP-B＋红标；回滚后＝CEP-A）
  const platformNode = pageKey === 'w1'
    ? (verCur.w1 === 2
      ? <span>CEP-A <span style={{ fontSize: 12, color: '#8a94a3' }}>（已随回滚恢复）</span></span>
      : <span>CEP-B <Tag color="error">与井档案对不上（井档案：CEP-A）——v3 自动重建时把井链错了</Tag></span>)
    : null

  const diff = (DIFFS[pageKey] || {})[verSel[pageKey]]

  const verColumns = [
    {
      title: '版本', dataIndex: 'v', width: 110,
      render: v => (
        <Space size={6}>
          <b>v{v}</b>
          {verCur[pageKey] === v && <Tag color="blue" style={{ marginInlineEnd: 0 }}>当前版</Tag>}
        </Space>
      )
    },
    { title: '更新时间', dataIndex: 'date', width: 100 },
    {
      title: <span>来源{helpIcon(<>每版的改动来源：自动重建 / 人工编辑 / 回滚。回滚产生的版本来源记为回滚，因此回滚本身也可再回滚。</>)}</span>,
      width: 96, render: () => <Tag color="default">自动重建</Tag>
    },
    { title: '说明', dataIndex: 'desc' },
    {
      title: '操作', width: 64, align: 'center',
      render: (_, v) => (
        <Tooltip title="看此版与上一版的差异">
          <Button size="small" icon={<DiffOutlined />}
            onClick={e => { e.stopPropagation(); setVerSel(s => ({ ...s, [pageKey]: v.v })) }} />
        </Tooltip>
      )
    }
  ]

  return (
    <Card
      title={
        <Tabs
          activeKey={tab} size="small" onChange={setTab}
          items={[
            { key: 'catalog', label: `百科页（${PAGES.length}）` },
            { key: 'read', label: '页面内容' },
            { key: 'versions', label: `版本历史（${VERSIONS[pageKey].length}）` }
          ]}
        />
      }
      extra={
        <Space size={4}>
          <span style={{ color: '#8a94a3', fontSize: 12 }}>报告入库自动重写成中文百科页 · 页内词条自动挂链接 · 每次重建留版本，改错一键回滚</span>
          {helpIcon(<>百科页是报告的可读版：把入库切好的段拼回全文（重叠去重、图片说明回读），再重写成结构化中文页（摘要 / 关键参数 / 表格摘录）；每个库一个目录，最近更新一目了然；页内井号、区块名自动挂链接，点击跳到对应对象卡，报告重新解析后词条沿用原页原地更新、旧链接不断；每次重建都落一个版本，改错了随时一键回滚，回滚也留痕。</>)}
        </Space>
      }
    >
      {tab === 'catalog' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Space wrap size={8}>
              <Select size="small" style={{ width: 150 }} value={libF} onChange={setLibF}
                options={[{ value: 'all', label: '所属库：全部' }, { value: '完井报告库', label: '完井报告库' }, { value: '生产月报库', label: '生产月报库' }]} />
              <Input size="small" allowClear style={{ width: 240 }} value={kw}
                onChange={e => setKw(e.target.value)} placeholder="搜百科页 / 来源报告…" />
            </Space>
            <span style={{ color: '#8a94a3', fontSize: 12 }}>{`筛选结果 ${filtered.length} / ${PAGES.length} 条`}</span>
          </div>
          <Table
            size="small" columns={catalogColumns} dataSource={filtered} pagination={false} rowKey="key"
            rowClassName={p => (p.key === selRow ? 'ant-table-row-selected' : '')}
            onRow={p => ({
              onClick: () => setSelRow(p.key),
              onDoubleClick: () => { setSelRow(p.key); openPage(p.key) },
              style: { cursor: 'pointer' }
            })}
          />
        </>
      )}

      {tab === 'read' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Space size={8}>
              <Button size="small" icon={<ArrowLeftOutlined />} onClick={() => setTab('catalog')}>返回目录</Button>
              <span style={{ fontSize: 15, fontWeight: 600 }}>{page.title} · 百科页</span>
              <Tag color="blue">当前版：v{verCur[pageKey]}</Tag>
            </Space>
            {helpIcon(content.summaryHelp)}
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.9, marginBottom: 16 }}>摘要：{content.summary}</div>

          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontWeight: 600, fontSize: 13 }}>关键参数</span>
            {helpIcon(content.paramsHelp)}
          </div>
          <Descriptions size="small" bordered column={2}>
            {content.params.map(p => (
              <Descriptions.Item key={p.k} label={p.k}>
                {p.dyn === 'platform' ? platformNode : p.v}
              </Descriptions.Item>
            ))}
          </Descriptions>

          <div style={{ display: 'flex', alignItems: 'center', margin: '16px 0 8px' }}>
            <span style={{ fontWeight: 600, fontSize: 13 }}>表格摘录（报告附表 · 中文化）</span>
            {helpIcon(content.excerptHelp)}
          </div>
          <Table size="small" columns={content.excerptColumns} dataSource={content.excerptRows} pagination={false} />

          <Card size="small" style={{ marginTop: 16 }} title={content.cardTitle} id="wellcard">
            <Descriptions size="small" bordered column={3}>
              {content.cardRows()}
            </Descriptions>
          </Card>
        </>
      )}

      {tab === 'versions' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Space size={4}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>版本历史与差异对比</span>
              <span style={{ color: '#8a94a3', fontSize: 12 }}>当前阅读：{page.title}</span>
              {helpIcon(VER_HELP)}
            </Space>
            {pageKey === 'w1' ? (
              <Button type="primary" size="small" icon={<RollbackOutlined />} onClick={rollback}>
                {verCur.w1 === 3 ? '回滚（恢复到上一版 v2）' : '回滚到上一版'}
              </Button>
            ) : (
              <Tooltip title="只有一版，无可回滚">
                <Button size="small" icon={<RollbackOutlined />} disabled>回滚</Button>
              </Tooltip>
            )}
          </div>
          <Row gutter={16}>
            <Col span={10}>
              <Table
                size="small" columns={verColumns} rowKey="v"
                dataSource={VERSIONS[pageKey]} pagination={false}
                rowClassName={v => (v.v === verSel[pageKey] ? 'ant-table-row-selected' : '')}
                onRow={v => ({
                  onClick: () => setVerSel(s => ({ ...s, [pageKey]: v.v })),
                  style: { cursor: 'pointer' }
                })}
              />
            </Col>
            <Col span={14}>
              {diff ? (
                <div>
                  <b>{diff.title}</b>
                  {diff.rows && (
                    <Table size="small" style={{ marginTop: 8 }} columns={DIFF_COLUMNS}
                      dataSource={diff.rows.map((r, i) => ({ key: i, ...r }))} pagination={false} />
                  )}
                  {diff.body && <div style={{ marginTop: 8, fontSize: 13 }}>{diff.body}</div>}
                  {diff.tail && <div style={{ marginTop: 8, fontSize: 12, color: '#8a94a3' }}>{diff.tail}</div>}
                </div>
              ) : (
                <Empty description="点左边版本列表任意一版，这里展开它与上一版的逐字差异。" />
              )}
            </Col>
          </Row>
          {banner && (
            <Alert style={{ marginTop: 16 }} showIcon type={banner.kind} message={banner.text} />
          )}
        </>
      )}
    </Card>
  )
}
