import { useEffect, useRef, useState } from 'react'
import {
  Button, Card, Empty, Input, InputNumber, Select, Skeleton, Space, Steps, Switch, Table, Tabs, Tag, Tooltip
} from 'antd'
import { QuestionCircleOutlined, ThunderboltOutlined } from '@ant-design/icons'

window.__guides = Object.assign(window.__guides || {}, {
  D5: [
    '顶部「环境健康」带＝原「系统状态」页撤并（票 109）：数据库（开发/生产）、缓存、对象存储四枚只读状态灯；连接参数在部署配置文件里改，界面不改。',
    '「链路记录」页签点任一行展开逐步耗时与 token——先找"最慢"琥珀标，排障先看它；问数据记录按六站逐站计时。',
    '点开"熔断降级"那条——单笔花费顶破上限自动改路由降级组 petro-lite：改路由不拒绝，在途照跑完。',
    '「延迟面板」页签悬浮 p95 列头 ?——均值会撒谎，备用组 5% 请求抖到 8 秒只有 p95 抓得住；点别名行看最近成功样本。',
    '「追踪对照」页签——平台字段与行业标准一一对应，平台特有项如实标注；两个追踪开关也在这页。',
    '「预算熔断」页签改两个上限点"保存阈值"——单笔/累计触顶后熔断位置位，后续调用改走降级组。',
    '点"模拟单笔超限"——第 3 步变红（¥0.08 顶破 ¥0.05），熔断降级记进链路；跑的过程中按钮不可重入，跑完可再点。',
    '底部「runtime 五信号」卡＝六站环第①站发现：miss/ambiguous/rewrite/error/feedback 计数达阈值自动归一进 C2 提案池——生产侧质量哨兵（PRD F15⑩）。'
  ]
})
window.__traces = Object.assign(window.__traces || {}, {
  D5: 'F29 OTel 映射 · F12 性能花费 · m12 可观测 · lessons/06 ＋ 环境健康带（原 D4 撤并·票 109：F3/F4/F5/F11 · m3/m4/m5/m11 · lessons/02-05）'
})

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

// ===== 链路记录：前三条＝页面既有三条 run（数字照旧）；第四条＝熔断降级样本，
// 花费沿用本页熔断流程既有数字（单笔 ¥0.08 / 上限 ¥0.05 / 降级组 petro-lite），耗时量级沿用既有问数记录 =====
const STATUS_META = {
  normal: { label: '正常', color: 'green' },
  done: { label: '已完成', color: 'green' },
  fused: { label: '熔断降级', color: 'red' }
}

const STEP_COLS = [
  {
    title: (<span>步骤{helpIcon(<>
      <b>「六站」＝一次问数从听懂到回答经过的六站处理</b><br />
      ① 意图澄清 → ② 检索选表 → ③ SQL 生成 → ④ 安全校验 → ⑤ 执行查询 → ⑥ 结果核对，逐站计时；徽标「六站口径」即此口径。<br />
      做汇报类任务按动作分步，不走六站；早期记录（run-0909-02 / run-0908-07）为七步口径留档。<br />
      琥珀「最慢」标＝这条记录里耗时最长的一步，排障先看它。
    </>)}</span>),
    dataIndex: 'step', width: 170,
    render: (v, r) => (r.slow ? <Space size={6}><b>{v}</b><Tag color="gold">最慢</Tag></Space> : v)
  },
  { title: '耗时', dataIndex: 'time', width: 90, render: (v, r) => (r.slow ? <b>{v}</b> : v) },
  {
    title: (<span>token 花费{helpIcon(<>token＝模型计费的计算量单位；不走模型调用的步骤记 0 或「—」。</>)}</span>),
    dataIndex: 'tok', width: 110,
    render: (v, r) => (r.slow ? <b>{v}</b> : v)
  },
  { title: '说明', dataIndex: 'note' }
]

const RUNS = [
  {
    key: 'run-0909-01', id: 'run-0909-01', q: '「上个月产量最高的三口井」',
    type: '问数据', time: '1833ms', cost: '¥0.0042', status: 'normal', sixStation: true,
    steps: [
      { key: 1, step: '意图澄清', time: '80ms', tok: '—', note: '复用上一步问句理解的结果，只补查缺没缺参数（第 1 站）' },
      { key: 2, step: '检索选表', time: '120ms', tok: '—', note: <>从全库裁剪到候选表，命中<a href="#/D6">日产计量表</a>＋井档案表（第 2 站）</> },
      { key: 3, step: 'SQL 生成', time: '1420ms', tok: '—', note: '内嵌网关调用 1400ms＋本地拼装 20ms——这步最慢，占了全长近 80%（第 3 站）', slow: true },
      { key: 4, step: 'SQL 安全校验', time: '3ms', tok: '0', note: <>安全规则逐条检查，不走模型（第 4 站，详见<a href="#/D3">安全与权限</a>）</> },
      { key: 5, step: '执行查询', time: '210ms', tok: '0', note: '只读沙箱里执行，返回 3 行（第 5 站）' },
      { key: 6, step: '结果核对', time: '<1ms', tok: '0', note: '行数/值域/口径核对——耗时 <1ms，已舍入进全长（第 6 站）' },
      { key: 7, step: <b>合计</b>, time: <b>1833ms</b>, tok: '—', note: <b>全长 1833ms · cost ¥0.0042（网关记账口径）· 口径＝问数六站流程。</b> }
    ]
  },
  {
    key: 'run-0909-02', id: 'run-0909-02', q: '「为什么 N-02 产量下滑」',
    type: '问数据', time: '5.2 秒', cost: '¥0.34', status: 'normal',
    steps: [
      { key: 1, step: '意图识别', time: '0.4 秒', tok: '310', note: '命中分析工作流《产量下滑归因》' },
      { key: 2, step: '拉完成率与构成', time: '0.9 秒', tok: '620', note: '产油/开井数/时率三件套' },
      { key: 3, step: '查检修台账', time: '0.7 秒', tok: '540', note: 'N-02 无检修记录' },
      { key: 4, step: '组织回答', time: '1.8 秒', tok: '1,410', note: '归因结论＋证据链——这步最慢，token 也最多', slow: true },
      { key: 5, step: '（其余步骤略）', time: '1.4 秒', tok: '660', note: '安全检查/执行/核对等合计' }
    ]
  },
  {
    key: 'run-0909-03', id: 'run-0909-03', q: '「对比 N-02 和 N-05 近两年产量走势」',
    type: '问数据', time: '4.6 秒', cost: '¥0.13', status: 'fused',
    steps: [
      { key: 1, step: '意图识别', time: '0.3 秒', tok: '280', note: '多井对比，进入问数反思流程' },
      { key: 2, step: '反思生成 · 第 1 轮', time: '0.8 秒', tok: '520', note: '先出初稿并自查一遍' },
      { key: 3, step: '反思生成 · 第 2 轮', time: '0.9 秒', tok: '560', note: '口径存疑，重写一遍' },
      { key: 4, step: '反思生成 · 第 3 轮', time: '1.1 秒', tok: '640', note: '核算本轮单笔花费 ¥0.08，顶破单次上限 ¥0.05', slow: true },
      { key: 5, step: '改路由降级组 petro-lite', time: '1.5 秒', tok: '420', note: '熔断位置位——后续调用改走降级组，在途照跑完；链路记一笔「熔断降级」' }
    ]
  },
  {
    key: 'run-0908-07', id: 'run-0908-07', q: '「做一份月度汇报 PPT」',
    type: '做汇报', time: '41 秒', cost: '¥1.86', status: 'done',
    steps: [
      { key: 1, step: '听懂需求', time: '0.5 秒', tok: '340', note: '识别成"生成文件"任务，后台排队' },
      { key: 2, step: '写大纲', time: '2.1 秒', tok: '1,280', note: '按月度汇报模板出大纲' },
      { key: 3, step: '生成 PPT 文件', time: '36 秒', tok: '2,050', note: '逐页生成——生成文件类任务天然最慢；期间用户可关页面，做完通知', slow: true },
      { key: 4, step: '转存文件', time: '0.6 秒', tok: '0', note: '成品落入文件存储，出下载直链' },
      { key: 5, step: '通知', time: '<0.1 秒', tok: '0', note: '给用户发完成消息' }
    ]
  }
]

const RUN_COLS = [
  {
    title: '运行', dataIndex: 'id',
    render: (v, r) => (
      <Space size={6} wrap>
        <span style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12 }}>{v}</span>
        <span>{r.q}</span>
        {r.sixStation && <Tag color="geekblue">六站口径</Tag>}
      </Space>
    )
  },
  { title: '类型', dataIndex: 'type', width: 96, render: v => <Tag>{v}</Tag> },
  { title: '总耗时', dataIndex: 'time', width: 90 },
  { title: '总花费', dataIndex: 'cost', width: 90 },
  { title: '状态', dataIndex: 'status', width: 110, render: v => <Tag color={STATUS_META[v].color}>{STATUS_META[v].label}</Tag> }
]

// ===== 延迟面板：两个别名＝D1 配置既有主备（petro-llm / deepseek-backup）；
// 最近样本为仿真：耗时量级沿用各别名 p50/p95/TTFT 既有值，窗口只记成功样本（8.0s＝成功但慢的跨网抖动样本）=====
const ALIASES = [
  {
    key: 'petro-llm', alias: 'petro-llm', role: '主用组', roleColor: 'green',
    win: '最近 500 个成功样本（滑动窗口）', p50: '1.1s', p95: '1.8s', ttft: '0.9s',
    samples: [
      { key: 1, t: '09:52', dur: '1.2s', first: '0.9s', note: '成功' },
      { key: 2, t: '09:50', dur: '1.0s', first: '0.8s', note: '成功' },
      { key: 3, t: '09:47', dur: '1.4s', first: '1.0s', note: '成功' },
      { key: 4, t: '09:45', dur: '1.1s', first: '0.9s', note: '成功' },
      { key: 5, t: '09:43', dur: '0.9s', first: '0.8s', note: '成功' },
      { key: 6, t: '09:40', dur: '1.3s', first: '1.0s', note: '成功' },
      { key: 7, t: '09:38', dur: '1.1s', first: '0.9s', note: '成功' },
      { key: 8, t: '09:35', dur: '1.0s', first: '0.8s', note: '成功' }
    ]
  },
  {
    key: 'deepseek-backup', alias: 'deepseek-backup', role: '备用组', roleColor: 'default',
    win: '最近 500 个成功样本（滑动窗口）', p50: '1.3s', p95: '8.0s', ttft: '1.0s', spike: true,
    samples: [
      { key: 1, t: '09:52', dur: '1.4s', first: '1.0s', note: '成功' },
      { key: 2, t: '09:50', dur: '1.3s', first: '1.0s', note: '成功' },
      { key: 3, t: '09:47', dur: '8.0s', first: '1.1s', note: '成功但慢：跨网抖动', spike: true },
      { key: 4, t: '09:45', dur: '1.6s', first: '1.1s', note: '成功' },
      { key: 5, t: '09:43', dur: '1.2s', first: '1.0s', note: '成功' },
      { key: 6, t: '09:40', dur: '1.5s', first: '1.0s', note: '成功' },
      { key: 7, t: '09:38', dur: '1.3s', first: '1.0s', note: '成功' },
      { key: 8, t: '09:35', dur: '1.4s', first: '1.1s', note: '成功' }
    ]
  }
]

const ALIAS_COLS = [
  {
    title: (<span>模型别名{helpIcon(<>调用别名＝业务代码里统一叫的名字，背后接哪家模型由网关决定；主用/备用与自动切换在<a href="#/D1">模型与线路</a>页配置。</>)}</span>),
    dataIndex: 'alias', width: 240,
    render: (v, r) => (
      <Space size={6}>
        <span style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12 }}>{v}</span>
        <Tag color={r.roleColor}>{r.role}</Tag>
      </Space>
    )
  },
  {
    title: (<span>样本窗口{helpIcon(<>窗口只记成功样本（每别名最近 500 个，滑动窗口）——失败请求不计入；排障时失败计数要与 p95 并排看。</>)}</span>),
    dataIndex: 'win', width: 250
  },
  { title: 'p50', dataIndex: 'p50', width: 80, align: 'right' },
  {
    title: (<span>p95{helpIcon(<>p95＝95% 的请求都比这个值快——看长尾用。<br /><b>均值会撒谎：</b>备用组 5% 的请求跨网抖到 8 秒，均值只从 1.2s 涨到 1.4s，几乎看不出异常；p95 直接跳到 8s，一眼看出备用线路在抖。</>)}</span>),
    dataIndex: 'p95', width: 80, align: 'right',
    render: (v, r) => (r.spike ? <b style={{ color: '#d4380d' }}>{v}</b> : v)
  },
  {
    title: (<span>TTFT 均值{helpIcon(<>TTFT＝首字延迟：从发出请求到蹦出第一个字的时间。</>)}</span>),
    dataIndex: 'ttft', width: 110, align: 'right'
  }
]

const SAMPLE_COLS = [
  { title: '时间', dataIndex: 't', width: 90 },
  { title: '总耗时', dataIndex: 'dur', width: 100, render: (v, r) => (r.spike ? <b style={{ color: '#d4380d' }}>{v}</b> : v) },
  { title: '首字延迟', dataIndex: 'first', width: 100 },
  {
    title: '结果', dataIndex: 'note',
    render: (v, r) => (r.spike ? <span style={{ color: '#d4380d' }}>{v}</span> : <span style={{ color: '#8a94a3' }}>{v}</span>)
  }
]

// ===== 追踪对照（行业标准 OTel 生成式 AI 字段族 gen_ai.*；平台特有项如实标注）=====
const OTEL_ROWS = [
  { key: 1, f: '模型供应商 / 模型名', s: <><code>gen_ai.system</code> / <code>gen_ai.request.model</code></>, d: '哪个模型答的' },
  { key: 2, f: '输入 / 输出 token', s: <><code>gen_ai.usage.input_tokens</code> / <code>gen_ai.usage.output_tokens</code></>, d: '每步花多少计算量' },
  { key: 3, f: '结束原因', s: <code>gen_ai.response.finish_reasons</code>, d: '答完了还是被截断' },
  { key: 4, f: '链路节点耗时', s: '行业标准节点时长', d: '哪步慢一目了然' },
  { key: 5, f: '指标口径版本 / 解释链', s: <><b>平台特有</b>（行业标准无对应，显式标注）</>, d: '数从哪个口径算来——行业标准没有这项，如实标注、不硬套也不丢掉' }
]

const OTEL_COLS = [
  { title: '平台记的字段', dataIndex: 'f', width: 200 },
  {
    title: (<span>行业标准叫法{helpIcon(<>对齐行业标准 OTel 的生成式 AI 字段族（gen_ai.*）——有对应的按标准命名；没有对应的平台特有项如实标注：不硬套也不丢掉。</>)}</span>),
    dataIndex: 's', width: 340
  },
  { title: '说明', dataIndex: 'd' }
]

// runtime 五信号（票 102 §三反馈行发现机制）：m18 SuggestionPool 的 runtime 源——
// 六站环第①站「发现」的生产侧质量哨兵（PRD F15⑩）。计数为确定性 mock，标「演示数据」。
const SIGNALS = [
  { key: 'miss', label: 'miss', zh: '检索落空', n: 12 },
  { key: 'ambiguous', label: 'ambiguous', zh: '多候选澄清', n: 7 },
  { key: 'rewrite', label: 'rewrite', zh: '改写重问', n: 5 },
  { key: 'error', label: 'error', zh: '报错', n: 3 },
  { key: 'feedback', label: 'feedback', zh: '用户反馈', n: 9 }
]
const SIGNALS_HELP = (
  <>
    <b>五信号＝m18 SuggestionPool 的 runtime 源</b>：miss（检索落空）/ ambiguous（多候选澄清）/
    rewrite（改写重问）/ error（报错）/ feedback（用户反馈）。<br />
    <b>发现机制（票 102 §三反馈行）</b>：各信号计数达阈值，自动归一成统一诊断 schema 进 C2 提案池——
    「自动」的机制＝阈值触发→归一（机器归一代码做、语义理解 LLM 做，票 92 schema）。<br />
    <b>六站环定位</b>：第①站「发现」的 runtime 源——生产侧质量哨兵（PRD F15⑩）。
  </>
)

// 预算熔断回放：问数反思第 3 轮单笔 ¥0.08 顶破 ¥0.05 → 熔断位单向置位 → 后续调用改路由降级组 petro-lite（在途照跑完）
const FUSE_NODES = ['问数反思 · 第 3 轮生成', '核算本轮单笔花费 ¥0.08', '单笔 ¥0.08 顶破单次上限 ¥0.05', '熔断位单向置位：后续调用改路由降级组 petro-lite', '在途调用照跑完 · 链路记一笔「熔断降级」']
const sleep = ms => new Promise(r => setTimeout(r, ms))

export default function D5Observe() {
  const [ready, setReady] = useState(false)
  const [tab, setTab] = useState('runs')
  const [typeF, setTypeF] = useState('全部类型')
  const [statusF, setStatusF] = useState('全部状态')
  const [kw, setKw] = useState('')
  const [openRuns, setOpenRuns] = useState([])
  const [openAlias, setOpenAlias] = useState([])
  const [otelOn, setOtelOn] = useState(true)
  const [vendorOn, setVendorOn] = useState(false)
  const [budget, setBudget] = useState(800)
  const [perCall, setPerCall] = useState(0.05)
  const [saved, setSaved] = useState('')
  const [cur, setCur] = useState(-1)
  const running = useRef(false)

  useEffect(() => {
    const t = setTimeout(() => setReady(true), 500)
    return () => clearTimeout(t)
  }, [])

  async function runFuse() {
    if (running.current) return
    running.current = true
    setCur(0)
    for (let i = 1; i < FUSE_NODES.length; i++) { await sleep(650); setCur(i) }
    running.current = false
  }

  const nodeState = i => {
    if (cur < 0 || i > cur) return 'wait'
    if (i === cur) return i === 2 ? 'error' : 'process'
    return i === 2 ? 'error' : 'finish'
  }

  const runsFiltered = RUNS.filter(r => {
    const okType = typeF === '全部类型' || r.type === typeF
    const okStatus = statusF === '全部状态' || STATUS_META[r.status].label === statusF
    const q = kw.trim().toLowerCase()
    return okType && okStatus && (!q || (r.id + r.q).toLowerCase().includes(q))
  })

  return (
    <div>
      {/* 原「系统状态」页（D4）撤并分流（票 109）：环境健康只读带——连接参数属部署配置文件，界面不承载编辑 */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
        <span style={{ fontSize: 12, color: '#8a94a3' }}>环境健康</span>
        <Tag color="green" style={{ marginInlineEnd: 0 }}>生产库 · 金仓 · 已连接</Tag>
        <Tag color="green" style={{ marginInlineEnd: 0 }}>开发库 · PostgreSQL · 已连接</Tag>
        <Tag color="green" style={{ marginInlineEnd: 0 }}>Redis 缓存 · 已连接</Tag>
        <Tag color="green" style={{ marginInlineEnd: 0 }}>MinIO 对象存储 · 已连接（两桶）</Tag>
        {helpIcon(<>原「系统状态」页撤并至此（只读，票 109）。<br />
          · 连接串、缓存与桶配置属<b>部署配置文件</b>（docker-compose / .env），界面不承载编辑——改配置走部署流程；<br />
          · 方言差异：金仓兼容模式建库时一次性固化，安全检查按"近似 PostgreSQL 口音"解析；<br />
          · 国产化：金仓官方驱动、麒麟 OS + Docker 离线镜像交付、SM4 加密 / SM3 留痕（加密清单见「安全与权限」）；<br />
          · 服务异常先看「链路记录」，存储容量水位见「数据质量台 · 数据到哪天」。</>)}
      </div>
      <Card
        title={
          <Tabs
            activeKey={tab} size="small" onChange={setTab}
            items={[
              { key: 'runs', label: `链路记录（${RUNS.length}）` },
              { key: 'latency', label: `延迟面板（${ALIASES.length}）` },
              { key: 'otel', label: `追踪对照（${OTEL_ROWS.length}）` },
              { key: 'budget', label: '预算熔断（2）' }
            ]}
          />
        }
        extra={
          <Space size={4}>
            <span style={{ color: '#8a94a3', fontSize: 12 }}>哪步慢一目了然 · 花超了自动改路由降级（不拒绝） · 双阈值触顶才熔断</span>
            {helpIcon(<>
              本页管运行追踪与花费：一次提问从听懂到回答走了哪些步、哪步慢、每步花多少，点开链路记录看全。<br />
              花费双阈值——单次 0.05 元＋累计 GATEWAY_BUDGET——任一触顶，后续调用自动改路由到降级组 petro-lite：改路由不拒绝，在途照跑完，链路记一笔「熔断降级」。
            </>)}
          </Space>
        }
      >
        {!ready ? <Skeleton active paragraph={{ rows: 9 }} /> : (
          <>
            {tab === 'runs' && (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <Space wrap size={8}>
                    <Select size="small" style={{ width: 120 }} value={typeF} onChange={setTypeF}
                      options={['全部类型', '问数据', '做汇报'].map(v => ({ value: v, label: v }))} />
                    <Select size="small" style={{ width: 130 }} value={statusF} onChange={setStatusF}
                      options={['全部状态', '正常', '已完成', '熔断降级'].map(v => ({ value: v, label: v }))} />
                    <Input size="small" allowClear style={{ width: 220 }} value={kw}
                      onChange={e => setKw(e.target.value)} placeholder="搜运行号 / 问题…" />
                  </Space>
                  <span style={{ color: '#8a94a3', fontSize: 12 }}>{`筛选结果 ${runsFiltered.length} / ${RUNS.length} 条`}</span>
                </div>
                <Table
                  size="small" columns={RUN_COLS} dataSource={runsFiltered} pagination={false} rowKey="key"
                  expandable={{
                    expandRowByClick: true,
                    expandedRowKeys: openRuns,
                    onExpandedRowsChange: setOpenRuns,
                    expandedRowRender: r => (
                      <Table size="small" pagination={false} columns={STEP_COLS} dataSource={r.steps} rowKey="key" />
                    )
                  }}
                  rowClassName={r => (openRuns.includes(r.key) ? 'ant-table-row-selected' : '')}
                  locale={{ emptyText: <Empty description="没有匹配的运行记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                />
              </>
            )}

            {tab === 'latency' && (
              <Table
                size="small" columns={ALIAS_COLS} dataSource={ALIASES} pagination={false} rowKey="key"
                expandable={{
                  expandRowByClick: true,
                  expandedRowKeys: openAlias,
                  onExpandedRowsChange: setOpenAlias,
                  expandedRowRender: r => (
                    <div>
                      <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 4 }}>最近成功样本（窗口只记成功，失败不计入）</div>
                      <Table size="small" pagination={false} columns={SAMPLE_COLS} dataSource={r.samples} rowKey="key" />
                    </div>
                  )
                }}
                rowClassName={r => (openAlias.includes(r.key) ? 'ant-table-row-selected' : '')}
              />
            )}

            {tab === 'otel' && (
              <>
                <Table size="small" pagination={false} columns={OTEL_COLS} dataSource={OTEL_ROWS} />
                <Space wrap size={32} style={{ marginTop: 12 }}>
                  <Space size={6}>
                    <Switch size="small" checked={otelOn} onChange={setOtelOn} />
                    <span>行业标准映射：{otelOn ? '开' : '关'}</span>
                    {helpIcon(<>关掉＝只留平台自己看得懂的记录；开着＝追踪字段按行业标准对齐命名，平台特有项仍如实标注。</>)}
                  </Space>
                  <Space size={6}>
                    <Switch size="small" checked={vendorOn} onChange={setVendorOn} />
                    <span>挂接第三方追踪平台：{vendorOn ? '开' : '关'}</span>
                    {helpIcon(<>挂接位已留——接好第三方追踪平台后，链路记录可以在对方界面回看。</>)}
                  </Space>
                </Space>
              </>
            )}

            {tab === 'budget' && (
              <>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
                  花费上限（双阈值）
                  {helpIcon(<>单笔管一次调用、累计管全月总额；任一触顶：熔断位置位——后续调用自动改路由到降级组 petro-lite，改路由不拒绝，在途照跑完，链路记一笔「熔断降级」。</>)}
                </div>
                <Space wrap size={24}>
                  <div>
                    <div style={{ fontSize: 12, marginBottom: 4 }}>累计预算 GATEWAY_BUDGET（元/月）</div>
                    <InputNumber size="small" style={{ width: 160 }} min={0} value={budget} onChange={setBudget} />
                  </div>
                  <div>
                    <div style={{ fontSize: 12, marginBottom: 4 }}>单次调用成本上限（元 · 默认 ¥0.05）</div>
                    <InputNumber size="small" style={{ width: 160 }} min={0} step={0.01} value={perCall} onChange={setPerCall} />
                  </div>
                </Space>
                <Space style={{ marginTop: 12 }} wrap>
                  <Button type="primary" size="small"
                    onClick={() => setSaved('已生效：单笔/累计触顶后熔断位置位——后续调用自动改路由到降级组（petro-lite），在途照跑完，链路记一笔「熔断降级」。')}>
                    保存阈值
                  </Button>
                  {saved && <span style={{ fontSize: 12, color: '#389e0d' }}>{saved}</span>}
                </Space>
                <div style={{ fontSize: 13, fontWeight: 600, margin: '20px 0 8px' }}>
                  熔断过程回放
                  {helpIcon(<>回放单笔 ¥0.08 顶破 ¥0.05 的处理过程：第 3 步红色标出破限时刻，随后熔断位置位、后续调用改路由降级组 petro-lite；跑的过程中按钮不可重入，跑完可再点复位重跑。</>)}
                </div>
                <Space wrap>
                  <Button type="primary" size="small" icon={<ThunderboltOutlined />} onClick={runFuse}>
                    模拟单笔超限 → 熔断改路由
                  </Button>
                </Space>
                {cur >= 0 ? (
                  <Steps
                    size="small" style={{ marginTop: 16 }} current={cur}
                    items={FUSE_NODES.map((t, i) => ({ title: <span style={{ fontSize: 12 }}>{t}</span>, status: nodeState(i) }))}
                  />
                ) : (
                  <Empty
                    style={{ marginTop: 16 }} image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="还没有模拟记录——点上面按钮，看单笔超限怎么触发熔断位、后续调用怎么改路由降级。"
                  />
                )}
              </>
            )}
          </>
        )}
      </Card>

      <Card
        size="small" className="runtime-signals" style={{ marginTop: 16 }}
        title={<span>runtime 五信号 · 生产侧质量哨兵（PRD F15⑩）{helpIcon(SIGNALS_HELP)}</span>}
        extra={<Tag color="orange">演示数据</Tag>}
      >
        <Space wrap size={12}>
          {SIGNALS.map(s => (
            <div key={s.key} className={`signal-card signal-${s.key}`}
              style={{ width: 168, border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, padding: '10px 12px' }}>
              <div style={{ fontSize: 12, color: '#8a94a3' }}>
                <code>{s.label}</code> · {s.zh}
              </div>
              <div className="signal-count" style={{ fontSize: 26, fontWeight: 700, lineHeight: '34px' }}>{s.n}</div>
              <a href="#/C2" className="signal-to-c2">进 C2 →</a>
            </div>
          ))}
        </Space>
        <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 10 }}>
          计数达阈值自动归一成诊断 schema 进 C2 提案池（机制注记见标题 ? 悬浮）；五信号是发现源，不是告警器——归一后的提案仍走 C2/C3 人审。
        </div>
      </Card>
    </div>
  )
}
