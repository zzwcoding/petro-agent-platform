import { useMemo } from 'react'
import { Popover, Tag } from 'antd'

// ===== 业务执行全景树（41 节点 · 23 条场景路径）=====
// 结构权威源：learning-records/2026-09-27-业务执行全景树.md（场景并集法：
// 23 个场景各走一条执行路径，重叠段合并为共享节点，独有段长出新节点）。
// 主干 = 「渤南区块本月产油量」全过程（N0–N10）；其余 22 场景依次补全
// 长出 N7.4a-c / N7.5a / N7.6a-b / N5a-A/B / N11–N20。
// 每个节点弹窗 = 节点字典执行过程（执行/输入/处理/输出/存储）＋复用标注。
// guard=横切/闸（褐虚线）；sc=叶节点对应场景 key
const ROOT = {
  key: 'N0', t: 'N0 发起对话',
  children: [
    { key: 'netdown', t: 'N0x 断线恢复', guard: true, dashed: true },
    { key: 'N1', t: 'N1 统一安检', guard: true, children: [
      { key: 'N2a', t: 'N2a 注入拦截', sc: 'injection' },
      { key: 'N2b', t: 'N2b 禁用词替代', sc: 'ban' },
      { key: 'N3', t: 'N3 轻装配', children: [
        { key: 'N4', t: 'N4 装配块', children: [
          { key: 'N5', t: 'N5 意图裁决', children: [
            { key: 'N5a', t: 'N5a 澄清帧', children: [
              { key: 'N5a-A', t: 'N5a-A 口径两译', sc: 'ambig' },
              { key: 'N5a-B', t: 'N5a-B 缺参反问', sc: 'askback' },
            ] },
            { key: 'N5b', t: 'N5b 裁决核验', children: [
              { key: 'N6', t: 'N6 链路分派', children: [
                { key: 'N7', t: 'N7 状态机六站链', children: [
                  { key: 'N7.1', t: 'N7.1 意图识别', children: [
                    { key: 'N7.2', t: 'N7.2 语义检索', children: [
                      { key: 'N7.3', t: 'N7.3 SQL 生成', children: [
                        { key: 'N7.4', t: 'N7.4 执行前安检', children: [
                          { key: 'N7.4a', t: 'N7.4a 新鲜度闸', sc: 'freshness', guard: true },
                          { key: 'N7.4b', t: 'N7.4b 行级权限', sc: 'rowlevel', guard: true },
                          { key: 'N7.4c', t: 'N7.4c 外表审批', sc: 'extable', guard: true },
                          { key: 'N7.5', t: 'N7.5 查询执行', children: [
                            { key: 'N7.5a', t: 'N7.5a 大结果落盘', sc: 'bigresult' },
                            { key: 'N7.6', t: 'N7.6 结果核验', children: [
                              { key: 'N7.6a', t: 'N7.6a 反思改错', sc: 'data-fix' },
                              { key: 'N7.6b', t: 'N7.6b 熔断转人工', sc: 'fuse' },
                              { key: 'N8', t: 'N8 答案组装', children: [
                                { key: 'N9', t: 'N9 流式推送', children: [
                                  { key: 'N10', t: 'N10 收尾记账' },
                                ] },
                              ] },
                            ] },
                          ] },
                        ] },
                      ] },
                    ] },
                  ] },
                ] },
                { key: 'N11', t: 'N11 外发拦截', sc: 'exfil' },
                { key: 'N12', t: 'N12 受控写入', sc: 'action' },
                { key: 'N13', t: 'N13 关系追溯', sc: 'graph' },
                { key: 'N14', t: 'N14 工具执行', sc: 'lith' },
                { key: 'N15', t: 'N15 工作流编排', sc: 'playbook' },
                { key: 'N16', t: 'N16 汇报生成', sc: 'deck' },
                { key: 'N17', t: 'N17 检索问答', children: [
                  { key: 'N17a', t: 'N17a 提及降权', sc: 'mention' },
                  { key: 'N17b', t: 'N17b 无据拒答', sc: 'reject' },
                ] },
                { key: 'N18', t: 'N18 预制问答', sc: 'faq' },
                { key: 'N19', t: 'N19 指标直出', sc: 'metric' },
                { key: 'N20', t: 'N20 上下文注入', sc: 'context' },
              ] },
            ] },
          ] },
        ] },
      ] },
    ] },
  ],
}

// 节点字典：执行过程（执行/输入/处理/输出/存储）——提炼自
// learning-records/2026-09-27-业务执行全景树.md「节点字典」一节
const N7_COVERS = 'data-clean / data-fix / fuse / bigresult / freshness / rowlevel / extable（7 场景）'
const NODE_EXEC = {
  N0: {
    covers: '全部 23 场景',
    exec: ['执行：用户', '输入：自然语言问句', '处理：建立 SSE 连接 → 问句＋上下文进前门',
      '存储：↑ Redis 事件缓冲（此后每帧先落缓冲）'],
  },
  N1: {
    covers: '全部 23 场景',
    exec: ['执行：代码 · 微秒 · 零模型', '输入：问句',
      '处理：三检查——注入正则 / 禁用词全等（0 号位）/ 身份与数据域',
      '输出：pass 放行；任一 ✗ 拦截出终局（外发判定要理解意图，归 D2 出口）',
      '存储：↓ PG users（验签 SM4 读回）、内存注入库/禁用词'],
  },
  N2a: {
    covers: 'injection',
    exec: ['执行：代码', '输入：命中注入特征的问句', '处理：拦截答复＋留痕（命中哪条规则就明说哪条）',
      '输出：终局——不进任何模型'],
  },
  N2b: {
    covers: 'ban',
    exec: ['执行：代码', '输入：命中废弃叫法的问句',
      '处理：出替代帧——"已废弃，现行叫法 X，是否按现行口径出数？"',
      '输出：用户改口才出数，否则终局'],
  },
  N3: {
    covers: '全部 23 场景',
    exec: ['执行：代码 · 毫秒 · 零模型', '输入：问句',
      '处理：显式 @ / 隐式锚定 → 带出直接关联（图纸房关系边）→ 六路候选（六房各查各库 · 共池）',
      '输出：AnchorSet＋候选池＋装配块', '存储：↓ 内存六房 / Chroma / BM25 快照'],
  },
  N4: {
    covers: '全部 23 场景',
    exec: ['执行：代码', '输入：AnchorSet＋闭包＋候选池（＋倾向行）',
      '处理：拼系统提示词装配段（@ 只是倾向，注入提示词不直通）', '输出：装配完毕的 D2 输入'],
  },
  N5: {
    covers: '全部 23 场景',
    exec: ['执行：LLM#1 · 全场唯一路由判断', '输入：装配块＋17 链清单＋原句', '处理：清单内结构化裁决（超出即无效）',
      '输出：{chain, slots(本体ID), confidence, need_clarify}', '存储：↓ 熔断位（内存）；settle ↑ 记账'],
  },
  N5a: {
    covers: 'ambig / askback',
    exec: ['执行：代码＋LLM 产物', '输入：裁决 need_clarify', '处理：生成帧（选项＝匹配器候选）→ interrupt 挂起等应答',
      '输出：带裁决参数回 N5 重判（≤1 次 · 两跳到终态）'],
  },
  'N5a-A': {
    covers: 'ambig',
    exec: ['实例：一词两译澄清帧', '处理：A/B 口径差异说明＋默认口径按钮', '输出：用户点选后回 N5 重判'],
  },
  'N5a-B': {
    covers: 'askback',
    exec: ['实例：缺参反问帧', '处理：时间窗三选一（近 3 天 / 近 30 天 / 本月）', '输出：用户补参后回 N5 重判'],
  },
  N5b: {
    covers: '全部 23 场景',
    exec: ['执行：代码（程序双验）', '输入：D2 输出的 {chain, slots}',
      '处理：chain 在 17 链注册表？slots 的 ID 对得上图纸房？', '输出：过 → dispatch；不过 → 重判'],
  },
  N6: {
    covers: '全部 23 场景',
    exec: ['执行：代码', '输入：双验通过的 chain', '处理：查静态映射表 → agent_type（qa / text2sql / wenzhi）',
      '输出：链接管', '存储：↓ 内存 ChainRegistry（m13）'],
  },
  N7: {
    covers: N7_COVERS,
    exec: ['执行：代码＋LLM#2', '六站：意图识别 → 选表 → 生成 SQL → GuardChain → 执行 → 结果校验',
      '分支闸下挂：新鲜度/行级权限/外表审批（N7.4）· 大结果落盘（N7.5）· 反思回边/熔断（N7.6）',
      '出口汇入 N8 组装答案'],
  },
  'N7.1': {
    covers: N7_COVERS,
    exec: ['执行：代码 · 零调用', '输入：复用 D2 slots', '处理：三要素齐？', '输出：齐放行 / 不齐反问'],
  },
  'N7.2': {
    covers: N7_COVERS,
    exec: ['执行：代码（m21 单出口）',
      '处理：S0 边界四要素（口径版本快照）→ S1 显式锚定 → S2 对象装配 → S3 词表两段查 → S4 双路+RRF 选表 → S5 图扩展（未实装直通）→ S6 资格审 → S7 回读权威源',
      '输出：SemanticContext', '存储：↓ Chroma/BM25、生效清单快照'],
  },
  'N7.3': {
    covers: N7_COVERS,
    exec: ['执行：LLM#2 · 流式', '输入：冻结前缀（命中 KV）＋表 DDL＋槽位', '输出：SQL 文本（首字 420ms）'],
  },
  'N7.4': {
    covers: N7_COVERS,
    exec: ['执行：代码 · ~3ms',
      '处理：AST 解析 / 只读双保险 / 白名单 → LIMIT 50-200 收口 → 行权限注入 → 新鲜度比对 → 血缘＋审计留痕',
      '输出：放行 / 拒绝（分支闸见子节点 a/b/c）'],
  },
  'N7.4a': {
    covers: 'freshness',
    exec: ['执行：代码', '处理：批次水位 vs 承诺水位', '输出：窗内标注放行（"数据截至 T-3"）/ 超窗拒',
      '存储：↓ PG 批次水位台账'],
  },
  'N7.4b': {
    covers: 'rowlevel',
    exec: ['执行：代码', '处理：全油田 → 数据域谓词 AST 改写，显性化进血缘', '存储：↓ 内存策略表'],
  },
  'N7.4c': {
    covers: 'extable',
    exec: ['执行：代码', '处理：SQL 引用命中集外表（erp_well_register）→ 审批卡 interrupt 挂起',
      '输出：批准续跑 / 驳回拒答（零重试）'],
  },
  'N7.5': {
    covers: N7_COVERS,
    exec: ['执行：代码', '输入：参数化 SQL', '处理：marts 查询（只读账号 · 核心读）', '输出：结果集',
      '存储：↓ PG/金仓 marts'],
  },
  'N7.5a': {
    covers: 'bigresult',
    exec: ['执行：代码',
      '处理：>50 行 → 落桶 → 元数据 → 签 URL → 5 行预览＋统计摘要＋句柄四字段（小时级）',
      '存储：↑ MinIO artifacts、↑ PG 元数据'],
  },
  'N7.6': {
    covers: N7_COVERS,
    exec: ['执行：代码', '处理：行数 / 值域 / 口径核对', '输出：通过 → N8；失败 → 反思回边'],
  },
  'N7.6a': {
    covers: 'data-fix',
    exec: ['执行：代码＋LLM#3..n', '处理：报错原文＋表结构回灌 N7.3 → 重过 GuardChain',
      '输出：试错上限 3 次（1/3 → 2/3 → 3/3）'],
  },
  'N7.6b': {
    covers: 'fuse',
    exec: ['执行：代码', '处理：3/3 试错尽 → 话术附已试轨迹', '输出：正常终局出图（工单 QA-1024）'],
  },
  N8: {
    covers: '全部 23 场景',
    exec: ['执行：代码',
      '处理：表格＋数据来源＋血缘五要素（口径/来源表/过滤含权限注入行/批次/收口）＋出处证据＋图表建议'],
  },
  N9: {
    covers: '全部 23 场景',
    exec: ['执行：代码', '处理：agent → token → tool_call → done 帧，每帧先落 Redis 缓冲',
      '输出：断线 Last-Event-ID 补发 / 缺口明示 / replay_truncated'],
  },
  N10: {
    covers: '全部 23 场景',
    exec: ['执行：代码', '处理：双写库＋缓存 → 网关审计两笔（call_id / token / 钱）→ trace 树落盘（run_id）'],
  },
  N11: {
    covers: 'exfil',
    exec: ['执行：代码＋闸',
      '处理：通道检查 → 三者不同会话判定 → m19.assert_outbound deny → 拦截＋留痕 → 正路指引',
      '注：判定归 D2、闸位在执行前'],
  },
  N12: {
    covers: 'action',
    exec: ['执行：代码＋LLM',
      '处理：四要素合同（改动/理由/影响测算/副作用）→ interrupt 人工批准（须写理由的驳回）',
      '输出：写变更记录区（原表不动）＋审计行'],
  },
  N13: {
    covers: 'graph',
    exec: ['执行：代码＋LLM', '处理：实体解析 → 关系查询（类型闸 · 劈分系数 Σ=1）→ 逐级追溯', '输出：图谱出处作答'],
  },
  N14: {
    covers: 'lith',
    exec: ['执行：代码＋LLM', '处理：双重权限（清单过滤＋执行前复核）→ schema 校验 → 沙箱执行（三闸）',
      '输出：压缩结论＋引用校验'],
  },
  N15: {
    covers: 'playbook',
    exec: ['执行：代码＋LLM', '处理：任务级命中 → 五步编排（工具紧枚举）→ 归因 HITL 挂起',
      '输出：合同三件（结论/证据链/数据版本）'],
  },
  N16: {
    covers: 'deck',
    exec: ['执行：代码＋LLM', '处理：口径锁定 → 取数 → 异步受理（先入队后出帧）→ 生成落盘', '输出：预签名直链（小时级）'],
  },
  N17: {
    covers: 'rag / mention / reject',
    exec: ['执行：代码＋LLM', '处理：双路召回 → RRF → 精排 → 带 [报告名 p.页码] 作答 · 引用逐条核验',
      '实例分支：N17a 提及降权 / N17b 无据拒答闸'],
  },
  N17a: {
    covers: 'mention',
    exec: ['执行：代码', '处理：指标卡命中标"低置信提及" → 按疑问落点路由（提及≠落点）'],
  },
  N17b: {
    covers: 'reject',
    exec: ['执行：代码 · 零模型', '处理：精排首名 < 0.5 → 拒答不编'],
  },
  N18: {
    covers: 'faq',
    exec: ['执行：代码', '处理：同池同闸检索判定 → 策展答案直出（负例行不参与）'],
  },
  N19: {
    covers: 'metric',
    exec: ['执行：代码 · 零模型', '处理：卡命中 → 修饰词消解 → 直出参数化模板（v3 版本标注）'],
  },
  N20: {
    covers: 'context',
    exec: ['执行：代码', '处理：指代解析（会话＋页面背景＝那口井 N-02）→ 确定性注入 → 工具调用 → 递减分析'],
  },
  netdown: {
    covers: '横切 · 全部 23 场景',
    exec: ['SSE 事件缓冲', '断线重连', '从断点续传（已出内容不丢）'],
  },
}

// 场景 → 根(N0)到叶的节点路径（蓝线高亮用）；root 键 N0 由组件自动并入
const FRONT = ['N1', 'N3', 'N4', 'N5', 'N5b', 'N6']
const CLARIFY = ['N1', 'N3', 'N4', 'N5', 'N5a']
const DATACLEAN = [...FRONT, 'N7', 'N7.1', 'N7.2', 'N7.3', 'N7.4', 'N7.5', 'N7.6', 'N8', 'N9', 'N10']
const RAG = [...FRONT, 'N17', 'N8', 'N9', 'N10']
const insertAfter = (arr, after, node) => {
  const i = arr.indexOf(after)
  return [...arr.slice(0, i + 1), node, ...arr.slice(i + 1)]
}
const PATHS = {
  injection: ['N1', 'N2a'],
  ban: ['N1', 'N2b'],
  ambig: [...CLARIFY, 'N5a-A'],
  askback: [...CLARIFY, 'N5a-B'],
  'data-clean': DATACLEAN,
  'data-fix': insertAfter(DATACLEAN, 'N7.6', 'N7.6a'),
  fuse: insertAfter(insertAfter(DATACLEAN, 'N7.6', 'N7.6a'), 'N7.6a', 'N7.6b'),
  bigresult: insertAfter(DATACLEAN, 'N7.5', 'N7.5a'),
  freshness: insertAfter(DATACLEAN, 'N7.4', 'N7.4a'),
  rowlevel: insertAfter(DATACLEAN, 'N7.4', 'N7.4b'),
  extable: insertAfter(DATACLEAN, 'N7.4', 'N7.4c'),
  exfil: [...FRONT, 'N11', 'N8', 'N9', 'N10'],
  action: [...FRONT, 'N12', 'N8', 'N9', 'N10'],
  graph: [...FRONT, 'N13', 'N8', 'N9', 'N10'],
  lith: [...FRONT, 'N14', 'N8', 'N9', 'N10'],
  playbook: [...FRONT, 'N15', 'N8', 'N9', 'N10'],
  deck: [...FRONT, 'N16', 'N8', 'N9', 'N10'],
  rag: RAG,
  mention: insertAfter(RAG, 'N17', 'N17a'),
  reject: insertAfter(RAG, 'N17', 'N17b'),
  faq: [...FRONT, 'N18', 'N8', 'N9', 'N10'],
  metric: [...FRONT, 'N19', 'N8', 'N9', 'N10'],
  context: [...FRONT, 'N20', 'N8', 'N9', 'N10'],
}

const COL_PITCH = 250, NODE_W = 210, NODE_H = 26, ROW = 40, PAD = 16

// 纵向主流布局：单 child 同列下一行（主流竖排 1 进 1 出）；真分叉（>1 子）右展一列、各占新行。
// 主流占列不占宽，树宽=分叉列数；行高 40 给竖排留呼吸。
function computeLayout() {
  const nodes = [], edges = []
  let rowMax = 0
  const walk = (node, x, y, parentKey) => {
    node._x = x; node._y = y
    nodes.push({ ...node, depth: x, parentKey })
    if (parentKey) edges.push({ from: parentKey, to: node.key })
    const kids = node.children
    if (!kids?.length) return
    if (kids.length === 1) {
      walk(kids[0], x, y + 1, node.key)
    } else {
      kids.forEach((c, i) => {
        const ry = i === 0 ? y + 1 : ++rowMax
        if (ry > rowMax) rowMax = ry
        walk(c, x + COL_PITCH, ry, node.key)
      })
    }
  }
  walk(ROOT, 0, 0, null)
  const pos = {}
  for (const n of nodes) pos[n.key] = { x: PAD + n._x, y: PAD + n._y * ROW }
  const maxX = Math.max(...nodes.map(n => n._x))
  return {
    nodes, edges, pos,
    width: PAD * 2 + maxX + NODE_W,
    height: PAD * 2 + rowMax * ROW + NODE_H,
  }
}

// 弹窗：标题=节点业务名＋Tag（sc 场景 tag；N7 系/检索链干带 geekblue 链 tag）
// 正文=节点字典执行过程（执行/输入/处理/输出/存储）＋复用标注
const isN7 = key => key === 'N7' || key.startsWith('N7.')
const reuseCount = key => isN7(key) ? 7 : key === 'N17' ? 3 : (key === 'N5a' || key.startsWith('N5a-')) ? 2 : 0

// 业务定位：一句话"干什么"（与总树 v2 节点块"定位"一致）——标签只放业务名，定位+执行内容进弹窗
const POS = {
  N0: '所有路径的起点', netdown: '横切能力，不占任何路径', N1: '入口安全检查',
  N2a: '注入攻击的终点', N2b: '废弃叫法的纠正', N3: '代码预装配候选知识',
  N4: '提供给模型裁决的材料', N5: '唯一由模型决定路由的节点', N5a: '不确定则反问用户',
  'N5a-A': '两种口径，用户选择', 'N5a-B': '缺少参数，向用户确认', N5b: '核对模型输出的合法性', N6: '按映射表分配执行链',
  N7: '自由问数的主流水线', 'N7.1': '要素齐不齐的把关', 'N7.2': '为出数找依据',
  'N7.3': '把问题翻译成查询', 'N7.4': '查询过五道闸才准执行', 'N7.4a': '旧数据不冒充新数据',
  'N7.4b': '每人只看见自己的数', 'N7.4c': '非常规引用的最后人工闸', 'N7.5': '执行查询',
  'N7.5a': '大结果不进对话', 'N7.6': '结果核对', 'N7.6a': '失败带报错重试',
  'N7.6b': '三次不成转人工', N11: '数据不出生产域', N12: '写入必须人工批准',
  N13: '沿业务关系查询', N14: '专业工具的受控调用', N15: '受控的多步任务',
  N16: '成品异步交付', N17: '从报告里带证据作答', N17a: '沾边不等于问它',
  N17b: '没证据不硬答', N18: '人维护的秒回', N19: '审定的数免生成',
  N20: '接着说不用重复说', N8: '把过程变成看得懂的交付', N9: '逐帧送达', N10: '处处留痕可回查',
}

function popContent(n, byKey) {
  const dict = NODE_EXEC[n.key]
  const sc = n.sc ? byKey[n.sc] : null
  const tags = []
  if (isN7(n.key)) tags.push(<Tag key="chain" color="geekblue">执行链 · 状态机六站链</Tag>)
  else if (n.key === 'N17') tags.push(<Tag key="chain" color="geekblue">执行链 · 检索问答链</Tag>)
  if (sc) tags.push(<Tag key="sc" color={sc.tag.color}>{sc.tag.label}</Tag>)
  const reuse = reuseCount(n.key)
  return {
    title: <span>{n.t}{tags.map(t => <span key={t.key} style={{ marginLeft: 6 }}>{t}</span>)}</span>,
    body: (
      <div style={{ maxHeight: 340, overflowY: 'auto', maxWidth: 430 }}>
        {POS[n.key] && <div style={{ fontSize: 12, color: '#79b8ff', marginBottom: 6 }}>定位：{POS[n.key]}</div>}
        <ol style={{ margin: 0, paddingLeft: 18 }}>
          {(dict?.exec || []).map((e, i) => (
            <li key={i} style={{ fontSize: 12, marginBottom: 4 }}>{e}</li>
          ))}
        </ol>
        {reuse > 0 && (
          <div style={{ fontSize: 12, color: '#79b8ff', marginTop: 4 }}>
            ♻ 本链被 {reuse} 个业务分支共用——业务路径不同，执行节点同一套，改一处全部分支生效。
          </div>
        )}
      </div>
    ),
  }
}

export default function DecisionTree({ byKey, active }) {
  const layout = useMemo(computeLayout, [])
  const { nodes, edges, pos, width, height } = layout
  const pathSet = new Set(['N0', ...(PATHS[active] || [])])

  return (
    <svg width={width} height={height}
      style={{ display: 'block', margin: '0 auto' }}>
      {edges.map(e => {
        const p1 = pos[e.from], p2 = pos[e.to]
        const on = pathSet.has(e.from) && pathSet.has(e.to)
        // 同列（主流竖排）→ 垂直连线：父底中 → 子顶中；分叉 → 横向贝塞尔
        const vertical = Math.abs(p2.x - p1.x) < 1
        const d = vertical
          ? `M ${p1.x + NODE_W / 2} ${p1.y + NODE_H} C ${p1.x + NODE_W / 2} ${p1.y + NODE_H + 16}, ${p2.x + NODE_W / 2} ${p2.y - 16}, ${p2.x + NODE_W / 2} ${p2.y}`
          : `M ${p1.x + NODE_W} ${p1.y + NODE_H / 2} C ${p1.x + NODE_W + 36} ${p1.y + NODE_H / 2}, ${p2.x - 36} ${p2.y + NODE_H / 2}, ${p2.x} ${p2.y + NODE_H / 2}`
        return (
          <path key={e.from + '>' + e.to}
            d={d}
            fill="none"
            stroke={on ? '#4a9dff' : '#30363d'}
            strokeWidth={on ? 2.5 : 1.5} />
        )
      })}
      {nodes.map(n => {
        const p = pos[n.key]
        const on = pathSet.has(n.key)
        const { title, body } = popContent(n, byKey)
        return (
          <foreignObject key={n.key} x={p.x} y={p.y} width={NODE_W} height={NODE_H}>
            <Popover title={title} content={body} placement="right" mouseEnterDelay={0.2}>
              <div style={{
                height: NODE_H - 2, display: 'flex', alignItems: 'center', padding: '0 8px',
                fontSize: 12, borderRadius: 6, boxSizing: 'border-box',
                whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                border: n.dashed ? '1px dashed #8a6d1a'
                  : n.guard ? '1px dashed #574c20'
                  : on ? '1px solid #4a9dff' : '1px solid #30363d',
                background: on ? 'rgba(74,157,255,.14)' : n.guard ? 'rgba(232,179,57,.08)' : '#161b22',
                color: on ? '#79b8ff' : n.guard ? '#e8b339' : '#c9d1d9',
                opacity: pathSet.size > 1 && !on && !n.guard ? 0.55 : 1,
              }}>
                {n.t}
              </div>
            </Popover>
          </foreignObject>
        )
      })}
    </svg>
  )
}
