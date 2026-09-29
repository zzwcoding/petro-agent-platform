import { useEffect, useRef, useState } from 'react'
import {
  Button, Card, Collapse, Empty, Input, InputNumber, Radio, Select, Skeleton, Space, Switch, Table, Tabs, Tag, Tooltip
} from 'antd'
import { PlayCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons'

window.__guides = Object.assign(window.__guides || {}, {
  D2: [
    '六个页签管全平台怎么找资料、怎么组织答案；页头一行写明规矩管到哪、改动怎么生效。',
    '「检索顺序」页签：三级从准到粗，每级可单独开关；"命中即停"开着，上级查到就不往下查。',
    '同一页展开"完整处理链 S0–S7"——从身份确认到权威回读，一次提问的每一步都在这。',
    '「找候选参数」页签改每路条数、合并方式、送精排条数，点"提交变更申请"送 A3 审批——批准前当前配置不变。',
    '「精排档位」页签三选一：快 / 准但贵 / 防同质，选哪档下方就显示哪档的算法与适用场景。',
    '「引用格式」页签二选一：人读友好的报告页码 vs 防伪造的编号引用，选中的卡高亮，点卡即选。',
    '「兜底话术」页签选策略、改固定文案——搜不到就明说，不编造。',
    '「检索试跑」页签点"试跑一次"：问 @指标 产量完成率，第 1 步命中即停，后两级虚线跳过。'
  ]
})
window.__traces = Object.assign(window.__traces || {}, {
  D2: 'F21 检索瀑布 · F34 复合精排 · F33 引用编号 · m6 问答管道 / m21 语义运行时'
})

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

// 三级检索顺序（公开口径：逐级升级、可单独开关）
const ORDER_ROWS = [
  { key: 1, name: '精确点名', what: '@指标 / @井号 直接点名', desc: '问法里带了「@产量完成率」「@N-02」这类点名，直接命中，不走后面的模糊搜索' },
  { key: 2, name: '确定性查表', what: '台账完全一致才命中', desc: '同义词、别名在账上完全对上才命中——宁可查不到，不给"差不多"的结果' },
  { key: 3, name: '语义搜索＋关键词搜索，两路一起查', what: '两路并发', desc: '一路按意思找（换了说法也能命中），一路按字面找（专有名词一个字都不差）' }
]

// 完整处理链 S0–S7：同一条链的逐级细拆（各步机制与数字沿用既有口径）
const WATERFALL_ROWS = [
  { key: 'S0', lv: 'S0 · 身份四要素', what: '身份 / 会话 / 口径版本 / 权限——一次确认，后面各步直接沿用', cost: '花一次解析；省每轮重复认证与口径对不上' },
  { key: 'S1', lv: 'S1 · 显式锚定', what: '@指标 / @对象 / 编号前缀匹配——对上就停在检索这几级（S3~S5 跳过），轻装配、资格审、权威回读照走', cost: '花一次前缀比对；省整级检索调用' },
  { key: 'S2', lv: 'S2 · 轻装配', what: '把点到的对象、术语解释、候选清单随问题一起交给模型——只提供材料，不当裁判', cost: '花少量整理开销；省"模型裸猜"的编造与返工' },
  { key: 'S3', lv: 'S3 · 词表四级', what: <>禁用词 0 号位 → 术语精确 → 同义词对照 → 模糊层（<b>Jaccard≥0.75</b>）——差一两个字符的变体才过线（"月产液→月产液量"）</>, cost: '花本地计算（毫秒级、不走模型）；省小错问句整路白找的钱' },
  { key: 'S4', lv: 'S4 · 两路找候选', what: '语义一路＋关键词一路，各取前 5 条，按名次融合成总排名——整批送资格审，不做"够像就停"的提前截断', cost: '花两路查询；宁多勿漏——提前截断是漏答案的头号原因' },
  { key: 'S5', lv: 'S5 · 图扩展', what: <span><Tag>未启用</Tag>这一级当前没开：请求直接跳过、不花开销，过程记录里写明这一级是直通跳过；将来接入知识图谱扩展时在这里开闸</span>, cost: '当前零成本' },
  { key: 'S6', lv: 'S6 · 资格裁决', what: '多候选 / 缺参数 → 反问澄清；候选上限 4 支，超出的截断并标"另有 N 支未列出"', cost: '花一轮澄清交互；省拿不准还硬答的返工' },
  { key: 'S7', lv: 'S7 · 权威源回读', what: <>回答用的指标，现场回指标台账核对——已正式发布、且版本与第 0 步确认的一致才放行；编号敲错在这里拦下：<b>"不在现行指标目录，不代答"</b></>, cost: '花一次台账回读；省按旧口径出数' }
]

// 精排三档（三选一；算式与参数沿用既有口径）
const TIERS = [
  { key: 'fast', name: '模型精排（快）', how: '用一个小而快的排序模型，把两路合并的候选一次性重新打分排队。', pro: '一次调用排完一批，延迟低、花费小', fit: '日常问答——界面响应要快，问题以「查报告找说法」为主' },
  { key: 'llm', name: '大模型逐个打分（准但贵）', how: '用主力大模型对前 N 条候选逐条打分——打 20 条就是 20 次模型调用，一条都不能少。', pro: '判断最准；但每条都花一次调用，慢且贵', fit: '重要汇报材料、口径核对——宁可慢点贵点也要准', extra: '打分解析失败时按原顺序放行，不影响整条链路。' },
  { key: 'compound', name: '复合分＋多样性（防同质）', how: '复合分＝0.6×模型分 ＋ 0.3×检索基础分 ＋ 0.1×来源分，每条候选的得分都能拆开看；再按多样性参数（λ=0.7）挑选，避免前几名全是同一份报告的近重复段落。', pro: '结果覆盖面广、来源多样，得分可解释', fit: '「各区块产量对比」这类要覆盖面的汇总问题——防止答案全从同一篇报告抄近重复段' }
]

// 引用格式两选项（示例沿用既有口径）
const CITES = [
  {
    key: 'page', title: '格式一：[报告名 p.页码]', tag: <Tag color="blue">人读友好</Tag>,
    help: '谁都能看懂指向哪份报告哪一页，核查方便。',
    sample: '渤中 28-1 油田 2019 年 6 月投产 [渤中28-1 完井报告 p.34]',
    radio: '[报告名 p.页码]（人读友好）'
  },
  {
    key: 'code', title: '格式二：编号引用 [c3]', tag: <Tag>防伪造</Tag>,
    help: '编号表里没有的编号（含被塞进报告里的假编号）直接删掉、绝不显示——想编引用都编不出来。',
    sample: '渤中 28-1 油田 2019 年 6 月投产 [c3]——模型只看到编号表，答完再展开成真实出处。',
    radio: '[c3] 编号引用（防伪造）'
  }
]

const DEMO_NODES = ['第0步 · 意图识别（谁在问/口径版本）', '第1步 · 精确点名', '第2步 · 确定性查表', '第3步 · 语义＋关键词两路']
const sleep = ms => new Promise(r => setTimeout(r, ms))

export default function D2Retrieval() {
  const [ready, setReady] = useState(false)
  const [tab, setTab] = useState('order')
  const [orderOn, setOrderOn] = useState([true, true, true])
  const [earlyStop, setEarlyStop] = useState(true)
  const [saved, setSaved] = useState('')
  const [topK1, setTopK1] = useState(20)
  const [topK2, setTopK2] = useState(20)
  const [merge, setMerge] = useState('两路合并排名（推荐）')
  const [topN, setTopN] = useState(20)
  const [tier, setTier] = useState('fast')
  const [fmt, setFmt] = useState('page')
  const [fallback, setFallback] = useState('fixed')
  const [fallbackText, setFallbackText] = useState('报告库里没有找到能回答这个问题的内容。我不能凭空编——请换个问法，或联系资料员补充报告。')
  const [demoCur, setDemoCur] = useState(-1)
  const [demoDone, setDemoDone] = useState(false)
  const [runs, setRuns] = useState(0)
  const running = useRef(false)

  useEffect(() => {
    const t = setTimeout(() => setReady(true), 500)
    return () => clearTimeout(t)
  }, [])

  async function runDemo() {
    if (running.current) return
    running.current = true
    setDemoDone(false); setDemoCur(0)
    await sleep(700); setDemoCur(1)
    await sleep(700); setDemoCur(2); setDemoDone(true)
    setRuns(n => n + 1)
    running.current = false
  }

  const nodeCls = i => {
    if (demoCur < 0) return { border: '1px solid rgba(255,255,255,0.16)', color: '#8a94a3', opacity: 1 }
    if (i < demoCur || (demoDone && i <= 1)) return { border: '1px solid #4a9dff', color: '#4a9dff', background: 'rgba(74,157,255,0.18)' }
    if (i === demoCur && !demoDone) return { border: '1px solid #4a9dff', color: '#4a9dff', background: 'rgba(74,157,255,0.18)' }
    if (demoDone && i >= 2) return { border: '1px dashed rgba(255,255,255,0.2)', color: '#8a94a3', opacity: 0.55 }
    return { border: '1px solid rgba(255,255,255,0.16)', color: '#8a94a3', opacity: 1 }
  }

  const curTier = TIERS.find(t => t.key === tier)
  const tierRows = [
    { k: '怎么算', v: curTier.how },
    { k: '优点 / 代价', v: curTier.pro },
    { k: '适用场景', v: curTier.fit },
    ...(curTier.extra ? [{ k: '出错怎么办', v: curTier.extra }] : [])
  ]

  return (
    <div>
      <Card
        title={
          <Tabs
            activeKey={tab} size="small" onChange={setTab}
            items={[
              { key: 'order', label: `检索顺序（${ORDER_ROWS.length}）` },
              { key: 'params', label: '找候选参数（4）' },
              { key: 'rerank', label: `精排档位（${TIERS.length}）` },
              { key: 'cite', label: `引用格式（${CITES.length}）` },
              { key: 'fallback', label: '兜底话术（2）' },
              { key: 'demo', label: `检索试跑（${runs}）` }
            ]}
          />
        }
        extra={
          <Space size={4}>
            <span style={{ color: '#8a94a3', fontSize: 12 }}>
              规矩管 <a href="#/A1">问一问</a> 的问报告与问数据 · 引用格式管回答的展示 · 各库索引开关在 <a href="#/B1">报告库</a> 按库配 · 改动过 <a href="#/C3">发布前安检</a> 批准后才生效
            </span>
            {helpIcon(<>
              <b>本页是检索与回答的总规矩</b><br />
              · 问一问的问报告、问数据两条路，都按这里的顺序找；引用格式管回答的展示。<br />
              · 各报告库自己的语义 / 关键词 / 百科 / 图谱四个索引开关，在报告库按库配。<br />
              · 改这里不走直接保存：点「提交变更申请」送数据变动审批（A3），批准前当前配置不变；批准后还要过发布前安检，考核成绩不降级才发布——改坏答案规矩会被第五道检查拦下。
            </>)}
          </Space>
        }
      >
        {!ready ? <Skeleton active paragraph={{ rows: 8 }} /> : (
          <>
            {tab === 'order' && (
            <>
              <Table
                size="small" pagination={false} rowKey="key"
                columns={[
                  { title: '次序', dataIndex: 'name', width: 260, render: v => <b>{v}</b> },
                  { title: '这一步查什么', dataIndex: 'what', width: 200 },
                  {
                    title: (<span>开关{helpIcon(<>从准到粗逐级往下找；关掉某一级就跳过它，直接看下一级。</>)}</span>),
                    width: 80, render: (_, r) => (
                      <Switch
                        size="small" checked={orderOn[r.key - 1]}
                        onChange={v => setOrderOn(s => s.map((x, j) => (j === r.key - 1 ? v : x)))}
                      />
                    )
                  },
                  { title: '说明', dataIndex: 'desc' }
                ]}
                dataSource={ORDER_ROWS}
              />
              <Space style={{ marginTop: 12 }}>
                <Switch size="small" checked={earlyStop} onChange={setEarlyStop} />
                <b>命中即停：{earlyStop ? '开' : '关'}</b>
                {helpIcon(<>上级查到就不往下查，省时省钱。</>)}
              </Space>
              <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 6 }}>
                两个答案拿不准时：宁可不答、反问澄清，不瞎猜——固定铁律，不设开关。
              </div>
              <Collapse
                style={{ marginTop: 12 }}
                items={[{
                  key: 'wf',
                  label: (
                    <span>
                      完整处理链 S0–S7（8 级）
                      <span onClick={e => e.stopPropagation()}>
                        {helpIcon(<>
                          与上面的三级顺序是同一条链的细拆：S0–S2 一次备料，S3–S5 逐级找，S6 定资格，S7 回读核验；上面的三级开关管的是 S3 之后的检索动作，条数等参数口径与本页一致。
                        </>)}
                      </span>
                    </span>
                  ),
                  children: (
                    <Table
                      size="small" pagination={false} rowKey="key"
                      columns={[
                        { title: '级别', dataIndex: 'lv', width: 150, render: v => <b>{v}</b> },
                        { title: '这一级干什么', dataIndex: 'what' },
                        { title: '花什么 / 省什么', dataIndex: 'cost', width: 320 }
                      ]}
                      dataSource={WATERFALL_ROWS}
                    />
                  )
                }]}
              />
            </>
            )}

            {tab === 'params' && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                <div>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>语义搜索取多少条{helpIcon(<>按意思找的这一路，一次最多带回多少条候选。</>)}</div>
                  <InputNumber size="small" style={{ width: '100%' }} min={1} value={topK1} onChange={setTopK1} />
                </div>
                <div>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>关键词搜索取多少条{helpIcon(<>按字面找的这一路，专有名词一个字都不差；一次最多带回多少条候选。</>)}</div>
                  <InputNumber size="small" style={{ width: '100%' }} min={1} value={topK2} onChange={setTopK2} />
                </div>
                <div>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>两路结果怎么合并{helpIcon(<>合并排名＝按两路的名词次融合成总排名（推荐）；简单拼接＝谁排前用谁，快但可能一路占满。</>)}</div>
                  <Select
                    size="small" style={{ width: '100%' }} value={merge}
                    options={['两路合并排名（推荐）', '谁排前用谁（简单拼接）'].map(o => ({ value: o, label: o }))}
                    onChange={setMerge}
                  />
                </div>
                <div>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>送精细排序的条数（前 N）{helpIcon(<>合并出总排名后，只有前 N 条进入精排重排。</>)}</div>
                  <InputNumber size="small" style={{ width: '100%' }} min={1} value={topN} onChange={setTopN} />
                </div>
              </div>
              <Space style={{ marginTop: 16 }}>
                <Button type="primary" size="small" onClick={() => setSaved('已提交变更申请，送数据变动审批（A3）待批准；批准前当前配置不变。')}>提交变更申请</Button>
                {saved && <span style={{ fontSize: 12, color: '#52c41a' }}>{saved}</span>}
              </Space>
            </>
            )}

            {tab === 'rerank' && (
            <>
              <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 8 }}>
                合并后的候选怎么排座次，三选一{helpIcon(<>日常要快选模型精排；重要汇报要准选逐个打分；要覆盖面选复合分＋多样性。当前选中的档位全平台统一生效。</>)}
              </div>
              <Radio.Group
                value={tier} onChange={e => setTier(e.target.value)}
                options={TIERS.map(t => ({ value: t.key, label: t.name }))}
              />
              <Table
                style={{ marginTop: 12 }} size="small" pagination={false} rowKey="k"
                columns={[{ title: '项', dataIndex: 'k', width: 110 }, { title: '内容', dataIndex: 'v' }]}
                dataSource={tierRows}
              />
            </>
            )}

            {tab === 'cite' && (
            <>
              <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 8 }}>
                回答里的出处怎么标，二选一{helpIcon(<>这边选哪种，问一问的回答就按哪种展示。</>)}
              </div>
              {CITES.map(c => (
                <Card
                  key={c.key} size="small" style={{
                    marginBottom: 8, cursor: 'pointer',
                    background: fmt === c.key ? 'rgba(74,157,255,0.18)' : 'rgba(255,255,255,0.04)'
                  }}
                  onClick={() => setFmt(c.key)}
                  title={<Space>{c.title}{c.tag}{helpIcon(c.help)}</Space>}
                >
                  <div className="code-block">{c.sample}</div>
                </Card>
              ))}
              <Radio.Group
                value={fmt} onChange={e => setFmt(e.target.value)}
                options={CITES.map(c => ({ value: c.key, label: c.radio }))}
              />
            </>
            )}

            {tab === 'fallback' && (
            <>
              <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 8 }}>
                搜不到时的应对，二选一{helpIcon(<>搜不到不报错、更不编造：固定文案或自由回答＋明确标注，两条路二选一。</>)}
              </div>
              <Radio.Group
                value={fallback} onChange={e => setFallback(e.target.value)}
                options={[
                  { value: 'fixed', label: '说固定文案（推荐）' },
                  { value: 'free', label: '允许自由回答，但必须标注「未依据报告库」' }
                ]}
              />
              <div style={{ fontSize: 12, marginBottom: 4, marginTop: 12 }}>固定文案{helpIcon(<>选"说固定文案"时，搜不到就原样回复这段话；可以改成你们自己的口吻。</>)}</div>
              <Input.TextArea size="small" rows={3} value={fallbackText} onChange={e => setFallbackText(e.target.value)} />
            </>
            )}

            {tab === 'demo' && (
            <>
              <Space wrap>
                <Button type="primary" size="small" icon={<PlayCircleOutlined />} onClick={runDemo}>
                  试跑一次：问「@指标 产量完成率 的口径是什么」
                </Button>
                {helpIcon(<>带 @点名的提问走最短路径：第 1 步点名命中就停（命中即停），后面步骤直接跳过。</>)}
              </Space>
              {demoCur >= 0 ? (
                <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                  {DEMO_NODES.map((t, i) => (
                    <div key={t} style={{ ...nodeCls(i), flex: 1, borderRadius: 6, padding: '8px 10px', fontSize: 12 }}>{t}</div>
                  ))}
                </div>
              ) : (
                <Empty
                  style={{ marginTop: 16 }} image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="还没有试跑记录——点上面按钮，看带 @点名的提问怎么在第一级命中。"
                />
              )}
              {demoDone && (
                <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: 8, padding: 12, marginTop: 12, fontSize: 13 }}>
                  结果：第 1 步「精确点名」直接命中《产量完成率》指标卡——<b>早停</b>：第 2、3 步不跑了，省时省钱；命中后回读指标账本核验版本，不是缓存旧影子。
                </div>
              )}
            </>
            )}
          </>
        )}
      </Card>
    </div>
  )
}
