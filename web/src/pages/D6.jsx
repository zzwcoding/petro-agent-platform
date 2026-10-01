import { useEffect, useState } from 'react'
import { Card, Col, Collapse, Empty, Input, Row, Skeleton, Table, Tabs, Tooltip } from 'antd'
import { QuestionCircleOutlined } from '@ant-design/icons'

window.__traces = Object.assign(window.__traces || {}, {
  D6: 'F53 接入落地链路 · F17 维度建模 · m20 数据建模与转换分层 / m22 知识管线枢纽'
})

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

// ===== 接入源（8 个，与原始层表清单同源）=====
const SOURCE_ROWS = [
  { key: 1, name: '生产日报', shape: 'A/B 班手抄汇总（含重复行，原样保留）' },
  { key: 2, name: '注水日报', shape: '分层注水记录' },
  { key: 3, name: '检修台账', shape: '检泵等检修记录（含补录批次）' },
  { key: 4, name: '措施台账', shape: '压裂/酸化等措施' },
  { key: 5, name: '化验单', shape: '含水/密度化验' },
  { key: 6, name: '设备状态', shape: '设备状态流水' },
  { key: 7, name: '月度结算', shape: '经营口径' },
  { key: 8, name: '井档案', shape: '一井一行' }
]

// ===== 三条清洗路径（什么时候用 / 怎么做 / 油田例子 / 防什么错）=====
const PATHS = [
  {
    key: 'p1', label: '路径一 · 规整表格自动识别',
    rows: [
      ['什么时候用', 'Excel / CSV 这类列清楚的表格。'],
      ['怎么做', '平台自动认出每列是什么（井号/日期/产油量…）并挂上单位'],
      ['油田例子（对照）', '日产计量日报'],
      ['防什么错', '单位混写（个别行"吨"误录成"方"）在这里按区块密度统一折算']
    ]
  },
  {
    key: 'p2', label: '路径二 · 嵌套数据炸开',
    rows: [
      ['什么时候用', '一个格子里塞了多条记录的嵌套数据（JSON）。'],
      ['怎么做', '把嵌套摊平：一张大记录拆成两张小表、用编号互相关联——例如一张作业工单含两个作业段，拆成「工单表＋作业段表」'],
      ['油田例子（对照）', (
        <>注水日报的分层字段（P1:60,P2:40）同属"一格多值"，分层口径不一、偶为累计值——同类问题在<a href="#/E2">数据质量台</a>登记规则。</>
      )],
      ['防什么错', '拆开后编号必须对得上，回查不丢行']
    ]
  },
  {
    key: 'p3', label: '路径三 · 扫描件识别＋人工复核',
    rows: [
      ['什么时候用', '扫描件、手抄件——机器认得出来但不敢保证全对。'],
      ['怎么做', (<>机器识别 → 规则校验 → 按把握程度过滤 → <b>抽样人工核对</b>，拿不准的进异常队列</>)],
      ['油田例子（对照）', '班次手抄日报：同井同日 A/B 两班各报一行，平台不会悄悄替人决定哪行算数，走人工复核确认'],
      ['防什么错', (<>人工复核是<b>必选步</b>，不许跳——最容易被跳过的恰恰是这一步</>)]
    ]
  }
]

// ===== 三层加工：各层进/出/防（收敛到层名 ? 悬浮）=====
const LAYER_HELP = {
  raw: (
    <>
      <b>原始层</b><br />
      进：各源系统的原样数据<br />
      出：贴上来源与批次标签的原始明细<br />
      防：漏接、错接（源头丢数先在这发现）
    </>
  ),
  clean: (
    <>
      <b>清洗层</b><br />
      进：原始层明细<br />
      出：去重、统一单位、编码归一后的干净明细<br />
      防：脏数据带病上行——错在这层拦最便宜<br />
      六条规则：1 同井同日去重 · 3 单位折算 · 4 计量与化验偏差核对 · 5 值域核查 · 7 井号归一 · 8 停机原因码归一
    </>
  ),
  agg: (
    <>
      <b>汇总层</b><br />
      进：清洗层的干净明细<br />
      出：问数直接用的星型大表<br />
      防：不先声明"一行是什么"就不许建模型（粒度先行）
    </>
  )
}

const RAW_ROWS = [
  { key: 1, t: '生产日报（原始）', s: 'A/B 班手抄汇总（含重复行，原样保留）' },
  { key: 2, t: '注水日报（原始）', s: '分层注水记录' },
  { key: 3, t: '检修台账（原始）', s: '检泵等检修记录（含补录批次）' },
  { key: 4, t: '措施台账（原始）', s: '压裂/酸化等措施' },
  { key: 5, t: '化验单（原始）', s: '含水/密度化验' },
  { key: 6, t: '设备状态（原始）', s: '设备状态流水' },
  { key: 7, t: '月度结算（原始）', s: '经营口径' },
  { key: 8, t: '井档案（原始）', s: '一井一行' }
]

const CLEAN_ROWS = [
  { key: 1, t: '生产日报（已去重·已统一单位）', s: '同井同日 A/B 重复行按唯一性规则处理；"吨/方"混写按区块密度折算（规则 1/3）' },
  { key: 2, t: '生产日报（值域核查）', s: '含水率 0–100、开井时长 0–24，越界标异常（规则 5）' },
  { key: 3, t: '井档案（井号已归一）', s: 'N2 / N-2 → N-02（规则 7）' },
  { key: 4, t: '设备状态（停机原因码已归一）', s: '新旧编码并存 → 映射表统一（规则 8）' },
  { key: 5, t: '检修台账（批次已标注）', s: '补录批次（如 T-3）标注水位，不静默混入当期' },
  { key: 6, t: '注水日报 / 化验单（已核对）', s: '计量与化验含水率偏差超 5 个百分点标出（规则 4）' }
]

function StarBox({ fact, title, note }) {
  return (
    <div style={{
      flex: 1, border: fact ? '2px solid #4a9dff' : '1px solid rgba(255,255,255,0.2)', borderRadius: 8,
      padding: '10px 12px', background: fact ? 'rgba(74,157,255,0.18)' : 'rgba(255,255,255,0.04)'
    }}>
      <b style={{ fontSize: 13 }}>{title}</b>
      <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 4 }}>{note}</div>
    </div>
  )
}

function ArrowBox({ dir }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', fontSize: 20, color: '#1677ff' }}>{dir}</div>
  )
}

// ===== 表 → 业务对象映射（四件套：表→对象类型 / 行→对象 / 列→属性 / 外键→关系）=====
const MAPPINGS = [
  {
    key: 'well_info', head: (<>井档案 <code>well_info</code> → 对象类型「井」</>),
    rows: [
      ['表 → 对象类型', (<>井档案 → <b>井</b></>)],
      ['行 → 对象', (<>一行＝一口井；井号列当身份：<code>N-02</code> → 井「渤中28-1-N2」</>)],
      ['列 → 属性', '井名 / 井别（采油·注水）/ 投产日 / 平台 / 区块 / 状态'],
      ['外键 → 关系', (<>区块列 → 井 —隶属→ 区块 —隶属→ 油田</>)]
    ]
  },
  {
    key: 'well_measures', head: (<>措施台账 <code>well_measures</code> → 对象类型「措施」</>),
    rows: [
      ['表 → 对象类型', (<>措施台账 → <b>措施</b></>)],
      ['行 → 对象', '一行＝一次措施（井号＋措施次）'],
      ['列 → 属性', '措施类型（压裂/酸化/补孔/调剖）/ 施工日 / 有效期起止 / 年增油'],
      ['外键 → 关系', (<>井号列 → 措施 —作用于→ 井</>)]
    ]
  },
  {
    key: 'fluid_test', head: (<>化验样 <code>fluid_test</code> → 对象类型「化验样」</>),
    rows: [
      ['表 → 对象类型', (<>化验样 → <b>化验样</b></>)],
      ['行 → 对象', '一行＝一个样品（井号＋取样日期）'],
      ['列 → 属性', '化验含水率 / 密度 / API 度'],
      ['外键 → 关系', (<>井号列 → 化验样 —取样自→ 井</>)]
    ]
  },
  {
    key: 'equip_status', head: (<>设备状态 <code>equip_status</code> → 对象类型「设备」</>),
    rows: [
      ['表 → 对象类型', (<>设备状态 → <b>设备</b></>)],
      ['行 → 对象', '一行＝一条设备状态记录（设备号＋时间戳）'],
      ['列 → 属性', '设备类型（电泵/螺杆泵/加热炉）/ 负载 / 电流 / 停机原因码'],
      ['外键 → 关系', '经井号列挂到对应井对象']
    ]
  }
]

// ===== 增量更新与已知风险 =====
const RISK_ROWS = [
  { key: 1, name: '坑一 · 追加模式新旧并存', what: '数据只增不改的接入方式下，同一口井改了状态会出现新旧两条记录并存', how: '按批次取最新，不混用' },
  { key: 2, name: '坑二 · 双源时间差', what: '月度结算与井口日报到账时间不同', how: '对不上先查到账批次，不先怀疑数错了' }
]

// ===== 效率账：冻结段示意 =====
const FROZEN_CODE = `# ── 系统提示词（版本化常量：prompts/sys_v17.md，hash 锁定）──
你是 Petro-Agent……平台规则本轮原样，一字不动
# ── 工具定义（注册表快照，固定排序）──
{ "name": "query_oil_production", … } × 12 件
# ── few-shot 固定前缀（3 条，顺序固化）──
Q: 上个月产量最高的三口井 → A: …（示例 3 组）`

// ===== 效率账：长会话压缩三原则 =====
const COMPRESS_RULES = [
  { k: '触发', v: (<>used &gt; window_tokens × <b>0.8</b> 触发——留两成余量，不顶到墙才压；</>) },
  { k: '摘要替换非截断', v: (<>role:"tool" 结果批量摘要后，按 tool_call_id <b>原位替换</b>——引用链不断，不丢消息结构；</>) },
  { k: '压缩失败原封不动', v: (<>先摘要、后替换；摘要超时则本轮放弃压缩——<b>无半成品</b>进上下文；</>) },
  { k: '透明', v: '界面上对话记录一字不变，压缩只发生在送给模型的那一侧。' }
]

const KV_ROWS = [
  { key: 1, how: '正确装配（冻结头不变）', tok: '10,200', note: '第 2 轮起只追加对话增量，前缀全命中' },
  { key: 2, how: '反例：时间戳进系统提示词', tok: '35,400', bad: true, note: '每轮前缀都变，命中率恒 0%，贵约 3.5 倍（第 20 轮单轮约 9 倍）' }
]

export default function D6Pipeline() {
  const [ready, setReady] = useState(false)
  const [tab, setTab] = useState('sources')
  const [srcKw, setSrcKw] = useState('')
  const [pathTab, setPathTab] = useState('p1')
  const [layerTab, setLayerTab] = useState('raw')

  useEffect(() => {
    const t = setTimeout(() => setReady(true), 500)
    return () => clearTimeout(t)
  }, [])

  const sourceFiltered = SOURCE_ROWS.filter(r => {
    const q = srcKw.trim().toLowerCase()
    return !q || (r.name + r.shape).toLowerCase().includes(q)
  })

  const pathTabs = PATHS.map(p => ({
    key: p.key, label: p.label,
    children: (
      <Table
        size="small" pagination={false}
        columns={[
          { title: '项', dataIndex: 'k', width: 150, render: v => <b>{v}</b> },
          { title: '内容', dataIndex: 'v' }
        ]}
        dataSource={p.rows.map(([k, v], i) => ({ key: i, k, v }))}
      />
    )
  }))

  const layerTabs = [
    {
      key: 'raw',
      label: (
        <span>
          原始层（{RAW_ROWS.length}）
          <span onClick={e => e.stopPropagation()}>{helpIcon(LAYER_HELP.raw)}</span>
        </span>
      ),
      children: (
        <Table
          size="small" pagination={false}
          columns={[{ title: '本层表清单', dataIndex: 't', width: 260 }, { title: '来自', dataIndex: 's' }]}
          dataSource={RAW_ROWS}
        />
      )
    },
    {
      key: 'clean',
      label: (
        <span>
          清洗层（{CLEAN_ROWS.length}）
          <span onClick={e => e.stopPropagation()}>{helpIcon(LAYER_HELP.clean)}</span>
        </span>
      ),
      children: (
        <>
          <Table
            size="small" pagination={false}
            columns={[{ title: '本层表清单', dataIndex: 't', width: 260 }, { title: '在这层做了什么', dataIndex: 's' }]}
            dataSource={CLEAN_ROWS}
          />
          <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 8 }}>
            发现的问题单流转（分发→认领→整改→复核→关闭）在<a href="#/E2">数据质量台</a>。
          </div>
        </>
      )
    },
    {
      key: 'agg',
      label: (
        <span>
          汇总层（3）
          <span onClick={e => e.stopPropagation()}>{helpIcon(LAYER_HELP.agg)}</span>
        </span>
      ),
      children: (
        <>
          <div style={{ display: 'flex', alignItems: 'stretch', gap: 8, margin: '4px 0 12px' }}>
            <StarBox title="井维度表" note="含区块、油田层级——查「渤南」不用再连表" />
            <ArrowBox dir="→" />
            <StarBox fact title="事实表 · 日产计量" note="一行＝一口井 × 一天（统计粒度先定死）；事实数字：产油 / 产液 / 压力" />
            <ArrowBox dir="←" />
            <StarBox title="日期维度表" note="按月/季汇总的对照" />
          </div>
          <div style={{ fontSize: 12, color: '#8a94a3' }}>
            问数页的表选谁，只认汇总层就绪的大表（→ <a href="#/A1">问一问 · 问数据</a>）。
          </div>
        </>
      )
    }
  ]

  const pageTabs = [
    {
      key: 'sources', label: `接入源（${SOURCE_ROWS.length}）`,
      children: (
        <>
          <div style={{ fontSize: 13, marginBottom: 12 }}>
            <b>原样入库：先不改一个字。</b>
            <span style={{ color: '#8a94a3' }}>
              报表上一个数对不上，能一路指回<b>原始文件的某一行</b>——月底对账不扯皮。
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Input
              size="small" allowClear style={{ width: 240 }} value={srcKw}
              onChange={e => setSrcKw(e.target.value)} placeholder="搜数据源 / 说明…"
            />
            <span style={{ color: '#8a94a3', fontSize: 12 }}>筛选结果 {sourceFiltered.length} / {SOURCE_ROWS.length} 个源</span>
          </div>
          <Table
            size="small" pagination={false} rowKey="key"
            columns={[
              { title: '数据源', dataIndex: 'name', width: 180, render: v => <b>{v}</b> },
              { title: (<>原样进来的样子{helpIcon(<>哪怕有重复行、错别字也原样存——先不改一个字，改的动作留给清洗层。</>)}</>), dataIndex: 'shape' }
            ]}
            dataSource={sourceFiltered}
            locale={{ emptyText: <Empty description="没有匹配的数据源" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          />
        </>
      )
    },
    {
      key: 'paths', label: `清洗路径（${PATHS.length}）`,
      children: <Tabs size="small" activeKey={pathTab} onChange={setPathTab} items={pathTabs} />
    },
    {
      key: 'layers', label: '三层加工（3）',
      children: <Tabs size="small" activeKey={layerTab} onChange={setLayerTab} items={layerTabs} />
    },
    {
      key: 'mapping', label: `对象映射（${MAPPINGS.length}）`,
      children: (
        <>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
            一种对象类型只对一张表——几十列的大宽表要先拆小再映射
            {helpIcon(<>
              <b>映射四件套</b>：表→对象类型 / 行→对象 / 列→属性 / 外键→关系。<br />
              点表名展开该表的四件套，再点收起；各面板独立开合。
            </>)}
          </div>
          <Collapse
            size="small"
            items={MAPPINGS.map(m => ({
              key: m.key, label: m.head,
              children: (
                <Table
                  size="small" pagination={false}
                  columns={[{ title: '映射项', dataIndex: 'k', width: 130 }, { title: '内容', dataIndex: 'v' }]}
                  dataSource={m.rows.map(([k, v], i) => ({ key: i, k, v }))}
                />
              )
            }))}
          />
          <Empty
            style={{ marginTop: 16 }} image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span style={{ fontSize: 12 }}>
                其余表（日产计量 / 注水日报 / 检修台账 / 月度结算）目前只进加工统计层、未注册为业务对象——如实标注，不硬造映射。对象清单：井 / 井筒 / 区块 / 油田 / 平台 / 设备 / 措施 / 化验样 / 受效关系 / 配注层。
              </span>
            }
          />
        </>
      )
    },
    {
      key: 'risks', label: `增量与风险（${RISK_ROWS.length}）`,
      children: (
        <>
          <div style={{ fontSize: 13, marginBottom: 12 }}>
            <b>每天只加工新到的行；对象档案只更新变化的部分，不整表重刷。</b>
            <span style={{ color: '#8a94a3' }}>两个已知的坑，各有一条应对口径：</span>
          </div>
          <Table
            size="small" pagination={false} rowKey="key"
            columns={[
              { title: '已知的坑', dataIndex: 'name', width: 200, render: v => <b>{v}</b> },
              { title: '现象', dataIndex: 'what' },
              { title: '应对口径', dataIndex: 'how', width: 280 }
            ]}
            dataSource={RISK_ROWS}
          />
        </>
      )
    },
    {
      key: 'kv',
      label: (
        <span>
          效率账（3）
          <span onClick={e => e.stopPropagation()}>{helpIcon(<>提示词里不变的部分（系统提示词、工具定义、示例）可缓存复用——命中后读价约常规 1/10。这里是装配方式与命中率的对照账，以及长会话的压缩规矩。</>)}</span>
        </span>
      ),
      children: (
        <Row gutter={12} align="top">
          <Col span={8}>
            <Card
              size="small" title="冻结段：系统提示词＋工具定义＋few-shot"
              style={{ height: '100%' }}
            >
              <div className="code-block">{FROZEN_CODE}</div>
              <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 8 }}>
                冻结头合计约 <b>3,800 token</b>，占首轮 4,400 的绝大头；<b>字节级冻结</b>——循环内只追加不重装，对 tools 零排序零改名：任何一次"顺手重排"都让 KV Cache 从头失效。
              </div>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title="KV Cache 命中账对照" style={{ height: '100%' }}>
              <Table
                size="small" pagination={false}
                columns={[
                  { title: '装配方式', dataIndex: 'how', width: 150 },
                  {
                    title: '六轮等效 token', dataIndex: 'tok', align: 'right', width: 120,
                    render: (v, r) => (r.bad ? <b style={{ color: '#d4380d' }}>{v}</b> : <b style={{ color: '#389e0d' }}>{v}</b>)
                  },
                  { title: '说明', dataIndex: 'note' }
                ]}
                dataSource={KV_ROWS}
              />
              <div style={{ fontSize: 12, color: '#8a94a3', marginTop: 8 }}>
                命中读价约 <b>1/10</b>（cache read 单价 ≈ 常规 1/10）；miss 重读全列约 <b>12 倍</b>读题量，且 prefill 随长度平方涨——2 倍长 ≈ 4 倍耗时。
              </div>
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title="长会话压缩三原则" style={{ height: '100%' }}>
              {COMPRESS_RULES.map((r, i) => (
                <div style={{ fontSize: 12, padding: '3px 0' }} key={i}>
                  <b>{r.k}：</b>{r.v}
                </div>
              ))}
            </Card>
          </Col>
        </Row>
      )
    }
  ]

  return (
    <div>
      <Card
        title={
          <Tabs activeKey={tab} size="small" onChange={setTab} items={pageTabs.map(p => ({ key: p.key, label: p.label }))} />
        }
        extra={
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ color: '#8a94a3', fontSize: 12 }}>
              先原样进来不改一个字 · 三条路洗净 · 拼成问数直接用的大表
            </span>
            {helpIcon(<>
              <b>本页管数据从进门到能被问数的全程</b><br />
              · 接入：8 个源一律原样入库——端到端血缘，报表上一个数对不上，能一路指回原始文件的某一行。<br />
              · 清洗：规整表格自动识别 / 嵌套炸开 / 扫描件识别＋人工复核，三条路。<br />
              · 加工：原始 → 清洗 → 汇总（星型模型）；问数只认汇总层就绪的大表。<br />
              · 表→业务对象映射与增量更新口径也在这里配。
            </>)}
          </span>
        }
      >
        {!ready ? (
          <Skeleton active paragraph={{ rows: 8 }} />
        ) : (
          pageTabs.map(p => {
            if (p.key !== tab) return null
            return <div key={p.key}>{p.children}</div>
          })
        )}
      </Card>
    </div>
  )
}
