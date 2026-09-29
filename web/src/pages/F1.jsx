import { useEffect, useState } from 'react'
import {
  Alert, Button, Card, Checkbox, Col, Empty, Input, Modal, Popconfirm, Row, Space, Table, Tabs, Tag, Tooltip
} from 'antd'
import { IdcardOutlined, PlusOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import { KEY_SCOPES, listKeys, createKey, rotateKey, revokeKey } from '../api/f1.js'

export const F1_GUIDE = [
  '「调用方式」页签点左边三行——直接调、参数不够时反问、长任务给任务号，右边切出对应的对话示例。',
  '「对外工具」页签——就 3 个查询工具，一件不多、一件不少；悬浮列头 ? 看清单怎么来的、什么才对外放行。',
  '「大结果凭证」页签点"看一张取货凭证"——大结果只给几行预览＋下载直链，句柄四字段齐全，下载直链最长 7 天有效。',
  '「内外同权」页签——外部 AI 和内部用户同一套安检，一道不少；改定义只能提建议＋人工审批。查询安检规则在 D3 配。',
  '「行业复用」页签——三层对照：对象层带走最多，映射层是护城河。',
  '「API 凭证」页签——外部调用方的钥匙：签发时勾能力集（五层），没勾的一律默认拒绝；明文只展示一次，泄露就轮换或停用。',
  '右上角"打开平台名片"——真跳转到 agent-card.html。',
  '悬浮右上角 ?——本页管三件事：对方怎么调、大结果怎么给、权限怎么不松。'
]
export const F1_TRACE = 'F8 工具体系 · F27 大结果句柄 · F28 对外接口 · F49 内外双通道 · F54 行业复用 · 票30 协议化暴露 · m16/m4/m15/m7 卡'

window.__guides = Object.assign(window.__guides || {}, { F1: F1_GUIDE })
window.__traces = Object.assign(window.__traces || {}, { F1: F1_TRACE })

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

// 三种用法 × 平台内对应（对外配置映射位，一表两用）
const WAYS = [
  {
    key: 'tool', way: '直接调工具', maps: '内部工具注册表按可见性过滤后的清单',
    example: `请求：{ 工具："按井查产量", 参数：{ 井号："N-02", 月份："2026-08" } }
返回：{ 产油量：1,4xx 吨，口径：产量完成率口径 v3，出处：汇总层日报表 · 质检通过 }`
  },
  {
    key: 'ask', way: '参数不够时反问', maps: '平台既有缺参澄清问答',
    example: `对方：查一下上个月的产量
平台：缺一个必要参数——你要哪个区块？（渤南 / 渤中 / 渤西）
对方：渤中
平台：好，渤中 2026 年 8 月产油 x,xxx 吨（口径版本 v3 · 出处见附）`
  },
  {
    key: 'task', way: '长任务给任务号', maps: '异步任务队列：受理即回＋凭号取结果',
    example: `对方：把渤南区块月度产量做成汇报材料
平台：已受理，任务号 task-7c2d。完成后可凭号取结果（也可订阅完成通知）。
（稍后）对方：task-7c2d 好了吗？
平台：好了 → 取货凭证见下（大结果不给正文，凭凭证自取）。`
  }
]

const WAY_HELP = {
  tool: '调用的是对外清单里的查询工具，同步返回结果；返回自带口径版本与出处——质检通过的数才出得了门。',
  ask: '缺参数就走"反问"，不做默认猜数——复用平台对内部用户同款的澄清问答。',
  task: '与内部"做汇报"走同一条异步任务链：受理即回＋任务号＋完成可查；大结果不给正文，凭凭证自取——见「大结果凭证」页签。'
}

// 对外工具清单：3 件查询类，只读档
const TOOLS = [
  { key: '1', tool: '按井查产量', desc: '按井 / 区块 / 月查产油产液（审定口径）', type: '查询 · 只读', status: '已放行' },
  { key: '2', tool: '查指标口径', desc: '问"递减率怎么算的"——返回定义、公式、负责人、版本', type: '查询 · 只读', status: '已放行' },
  { key: '3', tool: '查井档案', desc: '井的基本档案、状态、隶属区块', type: '查询 · 只读', status: '已放行' }
]

// 内外同权：外部 AI 过的是和内部用户同一道安检（查询安检四件＝D3 既有规则），改定义是另一扇门
const RIGHTS = [
  { key: '1', item: '查询安检 ①', tag: 'blue', text: '只放行查看类语句' },
  { key: '2', item: '查询安检 ②', tag: 'blue', text: '只认白名单里的表' },
  { key: '3', item: '查询安检 ③', tag: 'blue', text: '按对方身份过滤数据行——外部 AI 不能多看一行' },
  { key: '4', item: '查询安检 ④', tag: 'blue', text: '强制限量' },
  { key: '5', item: '改定义', tag: 'orange', text: '外部对口径/术语只能提修改建议＋人工审批——这条通道碰不到数据；日常能读、能执行动作，但改不了任何定义' },
  { key: '6', item: '例子', tag: 'default', text: '上级单位的 AI 系统问"渤海油田本月递减率"——它读到的是审定口径的数，不是原始表' }
]

const REUSE_COLUMNS = [
  { title: '层', dataIndex: 'layer', width: 120 },
  { title: '是什么', dataIndex: 'what' },
  { title: '换一家油田能带走多少', dataIndex: 'take', width: 260 }
]
const REUSE = [
  { key: '1', layer: '领域对象层', what: '井 / 区块 / 指标 / 受效关系这些对象与口径的定义方式', take: <span>复用 90% 以上</span> },
  { key: '2', layer: '映射层', what: '客户源系统的表怎么对到对象——逐张表的对应规则库', take: <span>复用 70% 以上——<b>护城河所在</b></span> },
  { key: '3', layer: '客户定制层', what: '各家的特殊报表与个性化流程', take: '逐客重做' }
]

const VOUCHER_PREVIEW = `well_id | prod_date  | oil_output(吨) | water_cut(%)
--------|------------|----------------|------------
N-02    | 2026-09-22 | 48.10          | 70.8
N-11    | 2026-09-22 | 11.90（单位误录，质检问题单在办） | 87.3
N-06    | 2026-09-22 | 0.00（注水井）   | 98.2
N-23    | 2026-09-22 | 23.45          | 64.0
N-37    | 2026-09-22 | 5.12           | 91.5
--------|------------|----------------|------------
min/max/均值：oil_output 0.00 ~ 48.10 · 均值 17.71 ｜ water_cut 64.0 ~ 98.2 · 均值 82.36
共 31,390 行（预览 5 行 · 凭句柄自取全量）`

// 句柄四字段（合同：下载直链小时级有效、上限 7 天）
const VOUCHER_FIELDS = [
  { key: 'id', item: 'artifact_id', text: 'art-9f2c7' },
  { key: 'url', item: '下载 URL', text: '/files/art-9f2c7?token=…（GET 预签名 · 小时级有效，上限 7 天）' },
  { key: 'rows', item: '总行数', text: '31,390' },
  { key: 'expire', item: '过期时间 expires_at', text: '2026-09-29T04:30:00Z（签发 2026-09-22 ＋ 7 天）' }
]

const HANDLE_COLUMNS = [
  { title: '句柄字段', dataIndex: 'item', width: 190, render: v => <span style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12 }}>{v}</span> },
  { title: '内容', dataIndex: 'text' }
]

const WAY_COLUMNS = [
  {
    title: (<span>调用方式{helpIcon(<>对方怎么调，平台内就有对应的一套，不另起炉灶：直接调对工具注册表清单、反问对缺参澄清问答、任务号对异步任务队列。</>)}</span>),
    dataIndex: 'way', width: 160, render: v => <b>{v}</b>
  },
  { title: '平台内对应', dataIndex: 'maps' }
]

const TOOL_COLUMNS = [
  {
    title: (<span>对外工具{helpIcon(<>对外清单＝内部工具注册表按可见性过滤的结果：内部能用什么，外部就见什么，一件不多、一件不少——和内部用户同权同闸。</>)}</span>),
    dataIndex: 'tool', width: 150, render: v => <b>{v}</b>
  },
  { title: '说明', dataIndex: 'desc' },
  { title: '类型', dataIndex: 'type', width: 110 },
  {
    title: (<span>对外状态{helpIcon(<>对外放行清单口径：查询类工具放行；写操作与外发类不在对外清单——写操作内部都要人工点批准，对外更不开放。</>)}</span>),
    dataIndex: 'status', width: 100, render: v => <Tag color="green">{v}</Tag>
  }
]

const RIGHT_COLUMNS = [
  { title: '项', dataIndex: 'item', width: 130, render: (v, r) => <Tag color={r.tag}>{v}</Tag> },
  { title: '规矩', dataIndex: 'text' }
]

export default function F1Expose() {
  const [tab, setTab] = useState('ways')
  const [way, setWay] = useState('tool')
  const [voucherOpen, setVoucherOpen] = useState(false)
  const [toolKw, setToolKw] = useState('')

  // API 凭证（PRD F61）
  const [keys, setKeys] = useState([])
  const [keysLoading, setKeysLoading] = useState(true)
  const [keysTip, setKeysTip] = useState('')
  const [issueOpen, setIssueOpen] = useState(false)
  const [issueName, setIssueName] = useState('')
  const [issueScopes, setIssueScopes] = useState([])
  const [issueFull, setIssueFull] = useState(false)
  const [issuing, setIssuing] = useState(false)
  const [issueErr, setIssueErr] = useState('')
  const [plaintext, setPlaintext] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let on = true
    listKeys().then(d => { if (on) { setKeys(d.keys); setKeysLoading(false) } })
    return () => { on = false }
  }, [])

  const flashTip = text => { setKeysTip(text); setTimeout(() => setKeysTip(''), 2500) }
  const refreshKeys = () => listKeys().then(d => setKeys(d.keys))

  async function doIssue() {
    setIssuing(true); setIssueErr('')
    try {
      const res = await createKey({ name: issueName, scopes: issueScopes, fullAccess: issueFull })
      setIssueOpen(false)
      setIssueName(''); setIssueScopes([]); setIssueFull(false)
      setPlaintext({ text: res.plaintext, name: res.key.name })
      await refreshKeys()
    } catch (e) {
      setIssueErr(e.message)
    } finally {
      setIssuing(false)
    }
  }
  async function doRotate(k) {
    const res = await rotateKey(k.id)
    setPlaintext({ text: res.plaintext, name: `${res.key.name} · 新凭证` })
    await refreshKeys()
    flashTip(`已轮换：旧凭证 ${k.id} 立即失效`)
  }
  async function doRevoke(k) {
    await revokeKey(k.id)
    await refreshKeys()
    flashTip(`已停用：${k.name} 立即失效`)
  }
  function copyPlaintext() {
    if (!plaintext || !navigator.clipboard) return
    navigator.clipboard.writeText(plaintext.text).then(() => {
      setCopied(true); setTimeout(() => setCopied(false), 1500)
    })
  }

  const cur = WAYS.find(w => w.key === way)
  const toolFiltered = TOOLS.filter(t => {
    const q = toolKw.trim().toLowerCase()
    return !q || (t.tool + t.desc).toLowerCase().includes(q)
  })

  const pageTabs = [
    { key: 'ways', label: '调用方式（3）' },
    { key: 'tools', label: '对外工具（3）' },
    { key: 'keys', label: `API 凭证（${keys.length}）` },
    {
      key: 'voucher',
      label: (
        <span>
          大结果凭证（1）
          <span onClick={e => e.stopPropagation()}>
            {helpIcon(<>
              对方要"全部在产井一整年的日产量明细"——几万行数据如果原样塞进对话，对方根本装不下。<br />
              平台的做法：<b>大结果落成生成文件，只发一张取货凭证</b>＝几行预览＋一条下载直链，内容由对方凭凭证自取。<br />
              句柄四字段齐全（artifact_id / 下载 URL / 总行数 / expires_at）——对方凭句柄自取全量，内容不进对话正文。
            </>)}
          </span>
        </span>
      )
    },
    {
      key: 'rights',
      label: (
        <span>
          内外同权（6）
          <span onClick={e => e.stopPropagation()}>
            {helpIcon(<>
              外部智能助手走的门，和内部用户是<b>同一扇</b>：查询安全检查一道不少——<b>外部 AI 不能绕安检、不能多看一行。</b><br />
              "改定义"是另一扇门：外部对口径/术语只能<b>提修改建议＋人工审批</b>。<br />
              查询安检规则在 D3 安全与权限设置里配。
            </>)}
          </span>
        </span>
      )
    },
    {
      key: 'reuse',
      label: (
        <span>
          行业复用（3）
          <span onClick={e => e.stopPropagation()}>
            {helpIcon(<>
              核心论断："护城河不是对象清单，而是源系统→对象的对应规则库"。<br />
              落地要配前置部署工程师（懂业务的人判断"200 列宽表拆成哪几个对象"），是行内陪跑、不替代决策的架构师。
            </>)}
          </span>
        </span>
      )
    }
  ]

  const waysPanel = (
    <Row gutter={16} align="top">
      <Col span={10}>
        <Table
          size="small" columns={WAY_COLUMNS} dataSource={WAYS} pagination={false} rowKey="key"
          rowClassName={r => (r.key === way ? 'ant-table-row-selected' : '')}
          onRow={r => ({ onClick: () => setWay(r.key), style: { cursor: 'pointer' } })}
        />
        <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 8 }}>
          点一行看对应对话示例。对外配置＝上面这张映射表：三个映射位与对外放行清单一一对应。
        </div>
      </Col>
      <Col span={14}>
        <Card size="small" title={<span>{cur.way} · 对话示例{helpIcon(WAY_HELP[way])}</span>}>
          <div className="code-block">{cur.example}</div>
        </Card>
      </Col>
    </Row>
  )

  const toolsPanel = (
    <div>
      <Space wrap style={{ marginBottom: 12 }}>
        <Input
          size="small" allowClear style={{ width: 220 }} value={toolKw}
          onChange={e => setToolKw(e.target.value)} placeholder="搜工具 / 说明…"
        />
        <span style={{ fontSize: 12, color: '#8a94a3' }}>筛选结果 {toolFiltered.length} / {TOOLS.length} 件</span>
      </Space>
      <Table
        size="small" columns={TOOL_COLUMNS} dataSource={toolFiltered} pagination={false} rowKey="key"
        locale={{ emptyText: <Empty description="没有匹配的对外工具" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
      />
    </div>
  )

  const voucherPanel = (
    <div>
      <Space wrap style={{ marginBottom: 12 }}>
        <Button size="small" type="primary" onClick={() => setVoucherOpen(v => !v)}>
          {voucherOpen ? '收起取货凭证' : '看一张取货凭证长什么样'}
        </Button>
      </Space>
      {voucherOpen && (
        <Card size="small" style={{ borderColor: '#91caff', maxWidth: 860 }} title="取货凭证（生成文件 art-9f2c7）">
          <div>内容：86 口在产井 2025-09 ~ 2026-09 日产量明细（共 31,390 行 · 约 0.9 MB）</div>
          <div className="code-block" style={{ marginTop: 8 }}>{VOUCHER_PREVIEW}</div>
          <div style={{ fontWeight: 600, fontSize: 13, marginTop: 12, marginBottom: 4 }}>
            句柄四字段{helpIcon(<>句柄四字段齐全——对方凭句柄自取全量，内容不进对话正文；下载直链小时级签发、最长 7 天有效，过期重新申请。</>)}
          </div>
          <Table size="small" columns={HANDLE_COLUMNS} dataSource={VOUCHER_FIELDS} pagination={false} rowKey="key" />
        </Card>
      )}
    </div>
  )

  const rightsPanel = (
    <div>
      <Table size="small" columns={RIGHT_COLUMNS} dataSource={RIGHTS} pagination={false} rowKey="key" />
      <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 8 }}>
        查询安检规则在 <a href="#/D3">D3 安全与权限设置</a> 里配。
      </div>
    </div>
  )

  const reusePanel = (
    <Table size="small" columns={REUSE_COLUMNS} dataSource={REUSE} pagination={false} rowKey="key" />
  )

  const MONO = { fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12 }
  const fmtT = iso => (iso ? iso.replace('T', ' ').slice(5, 16) : '—')
  const KEY_STATUS = {
    active: <Tag color="green">启用中</Tag>,
    rotated: <Tag>已轮换</Tag>,
    revoked: <Tag color="red">已停用</Tag>
  }
  const scopeCell = k => (k.fullAccess
    ? <Tag color="red">full-access（高危）</Tag>
    : k.scopes.map(s => {
      const sc = KEY_SCOPES.find(x => x.key === s)
      return sc ? <Tag key={s} color="green">{sc.name}</Tag> : null
    }))

  const keysPanel = (
    <div>
      <Space wrap style={{ marginBottom: 12 }}>
        <Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => { setIssueOpen(true); setIssueErr('') }}>
          签发凭证
        </Button>
        <span style={{ fontSize: 12, color: '#8a94a3' }}>
          scoped：签发时勾能力集，未声明的能力一律默认拒绝 · 外部调用与内部用户同一套安检（D3 配置）
        </span>
        {keysTip && <span style={{ fontSize: 12, color: '#52c41a' }}>{keysTip}</span>}
      </Space>
      <Table
        size="small" loading={keysLoading} rowKey="id" dataSource={keys} pagination={false}
        columns={[
          {
            title: '凭证', dataIndex: 'name', width: 210,
            render: (v, k) => <div><b>{v}</b><div style={MONO}>{k.id}</div></div>
          },
          {
            title: <span>能力（scoped）{helpIcon('能力集＝五层权限裁剪（PRD F48）：能看/能查/能算/能动/守规矩；未声明的能力一律默认拒绝。')}</span>,
            dataIndex: 'scopes', render: (_, k) => scopeCell(k)
          },
          { title: '凭据', dataIndex: 'hint', width: 110, render: v => <span style={MONO}>{v}</span> },
          { title: '创建时间', dataIndex: 'createdAt', width: 110, render: fmtT },
          { title: '最近使用', dataIndex: 'lastUsedAt', width: 110, render: fmtT },
          { title: '状态', dataIndex: 'status', width: 90, render: v => KEY_STATUS[v] },
          {
            title: '操作', width: 150,
            render: (_, k) => (k.status !== 'active' ? <span style={{ color: '#8a94a3' }}>—</span> : (
              <Space size={4}>
                <Popconfirm
                  title="轮换后旧凭证立即失效，外部方需换新凭证接入。"
                  okText="轮换" cancelText="取消"
                  onConfirm={() => doRotate(k)}
                >
                  <Button size="small">轮换</Button>
                </Popconfirm>
                <Popconfirm
                  title="停用为终态：该凭证立即失效。确认停用？"
                  okText="停用" cancelText="取消" okButtonProps={{ danger: true }}
                  onConfirm={() => doRevoke(k)}
                >
                  <Button size="small" danger>停用</Button>
                </Popconfirm>
              </Space>
            ))
          }
        ]}
      />
    </div>
  )

  return (
    <>
      <Card
        title={
          <Tabs activeKey={tab} size="small" onChange={setTab} items={pageTabs} />
        }
      extra={
        <Space size={8}>
          <span style={{ color: '#8a94a3', fontSize: 12 }}>
            外部 AI 和内部用户同一套安检 · 大结果只给凭证不给正文 · 改定义只能提建议＋人工审批
          </span>
          {helpIcon(<>
            平台的用户不再只有人——上级单位、合作方的智能助手也能用它查数、查口径。这一页管三件事：对方怎么调（三种用法）、大结果怎么给（取货凭证不塞正文）、权限怎么不松（内外同一套安检）。<br />
            对外清单一件不多、一件不少，和内部用户同权同闸。
          </>)}
          <Tooltip
            title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>平台名片＝给别的平台看的自我介绍：我会什么、怎么连我、要什么认证——别的平台读它就知道怎么接入。</div>}
            placement="topRight"
          >
            <Button size="small" type="primary" icon={<IdcardOutlined />} href="../agent-card.html">打开平台名片</Button>
          </Tooltip>
        </Space>
      }
    >
      {tab === 'ways' && waysPanel}
      {tab === 'tools' && toolsPanel}
      {tab === 'keys' && keysPanel}
      {tab === 'voucher' && voucherPanel}
      {tab === 'rights' && rightsPanel}
      {tab === 'reuse' && reusePanel}
    </Card>

      <Modal
        title="签发 API 凭证" open={issueOpen} onCancel={() => setIssueOpen(false)} footer={null} width={560}
      >
        <div style={{ marginBottom: 6 }}>凭证名称</div>
        <Input value={issueName} onChange={e => setIssueName(e.target.value)} placeholder="如：上级单位 · 数据报送" />
        <div style={{ margin: '12px 0 6px' }}>
          能力集（scoped）
          {helpIcon('未勾选的能力一律默认拒绝；外部调用与内部用户走同一套 D3 查询安检。')}
        </div>
        <Checkbox.Group
          style={{ display: 'flex', flexDirection: 'column', gap: 6 }}
          value={issueScopes} onChange={setIssueScopes}
          options={KEY_SCOPES.map(s => ({ value: s.key, label: `${s.name}（${s.full}）—— ${s.desc}` }))}
        />
        <div style={{ marginTop: 12 }}>
          <Checkbox checked={issueFull} onChange={e => setIssueFull(e.target.checked)}>
            <span style={{ color: '#ff4d4f' }}>full-access（高危：等效全能力，签发限治理角色）</span>
          </Checkbox>
        </div>
        {issueFull && (
          <Alert style={{ marginTop: 8 }} type="warning" showIcon
            message="full-access 跳过能力勾选、等效全部能力——仅在确有必要时签发，泄露影响面最大。" />
        )}
        {issueErr && <div style={{ marginTop: 8, color: '#ff4d4f', fontSize: 12 }}>{issueErr}</div>}
        <Space style={{ marginTop: 16 }}>
          <Button type="primary" loading={issuing} onClick={doIssue}
            disabled={issueFull ? !issueName.trim() : !issueName.trim() || issueScopes.length === 0}>
            签发
          </Button>
          <Button onClick={() => setIssueOpen(false)}>取消</Button>
        </Space>
      </Modal>

      <Modal
        title={plaintext && `凭证明文 · ${plaintext.name}`}
        open={!!plaintext} onCancel={() => setPlaintext(null)} footer={null} width={560}
      >
        {plaintext && (
          <>
            <Alert type="warning" showIcon message="明文只展示这一次——关闭后永远只显示脱敏占位，请立即复制保存。" />
            <div className="code-block" style={{ marginTop: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <span style={{ fontFamily: 'ui-monospace, Menlo, monospace' }}>{plaintext.text}</span>
              <Button size="small" onClick={copyPlaintext}>{copied ? '已复制' : '复制'}</Button>
            </div>
            <div style={{ marginTop: 12, fontSize: 12, color: '#8a94a3' }}>
              处置纪律：泄露即轮换（旧凭证立即失效）；下线即停用（终态）。
            </div>
            <div style={{ marginTop: 12, textAlign: 'right' }}>
              <Button type="primary" onClick={() => setPlaintext(null)}>我已保存，关闭</Button>
            </div>
          </>
        )}
      </Modal>
    </>
  )
}
