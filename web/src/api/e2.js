// E2 数据质量台 —— 接口契约 + mock 实现
// 契约文档：specs/api/E2-数据质量台.md（本文件函数签名 = 后端接口开发依据）
// 约定：mock 只存在于这一层，页面组件不持有业务数据；后端就绪后函数体换 fetch，签名与返回形状不变。
// 契约来源：specs/modules.md「质量 m20」· 设定书 §1 岗位三角 / §4 质检规则与任务 / §A 样本数据 · PRD F18

// ── 契约来源：设定书 §4 质检规则 20 条（前 12 条挂具体判据，13–20 通用规则族）──
// action=命中动作三档（业界 expectations 语义）：隔离=坏行不进湖 / 整批拒收=批次级拒绝（schema 级故障专用）/ 告警=通知人工核实
// autoFix=安全类可自动修复（写法归一/枚举映射——v0.4 去重保首条撤出白名单），只作用派生层，原始坏行永留隔离区
// v0.4 本体对齐批（RULE-BOHAI-030/023/025/038 权威源）：规则 1 重复行不静默去重出问题单 / 规则 5 矛盾行清单制 / 规则 6 T-5 不拒收转问题单 / 规则 11 当日批面
export const RULES = [
  { no: 1, kind: '重复', rule: '同一口井同一天每个班次只能有一条日产记录——A/B 班手抄重复行即命中', crit: '班次三元组（井,日,班次）唯一；重复/缺失行进问题单人工复核，不静默去重', action: '告警', autoFix: false },
  { no: 2, kind: '缺失', rule: '日产油量不许空着', crit: '非空率 ≥ 99.5%', action: '隔离', autoFix: false },
  { no: 3, kind: '准不准', rule: '产油单位要对：按区块密度折算后，密度须落在 0.82–0.98 t/m³——抓住"吨方混写"', crit: '折算密度 ∈ [0.82, 0.98]', action: '隔离', autoFix: false },
  { no: 4, kind: '两本账打架', rule: '含水率：生产日报（计量）vs 化验样，偏差不能太大', crit: '偏差 ≤ 5 个百分点', action: '告警', autoFix: false },
  { no: 5, kind: '超范围', rule: '含水率 0–100、开井小时数 0–24，越界即不合格（停井日开井小时数仍大于 0 的矛盾行：标注出清单交业务核实，不归零不直改）', crit: '越界即 fail；矛盾行清单制', action: '告警', autoFix: false },
  { no: 6, kind: '迟到', rule: '检修台账补录窗口：超 T-5 不拒收（数据不丢是底线），收单转问题单闭环走特批核实——T-3 补录照收但留痕', crit: '≤ T-5；超窗不拒收转问题单', action: '告警', autoFix: false },
  { no: 7, kind: '写法不统一', rule: '井号写法归一：N2 / N-2 都归成 N-02，归一表要全命中', crit: '归一表全命中', action: '隔离', autoFix: true },
  { no: 8, kind: '写法不统一', rule: '设备停机原因码要用新编码表：旧码 R3（皮带断）映射到新码 BELT，全表命中', crit: '映射表全命中', action: '隔离', autoFix: true },
  { no: 9, kind: '重复 / 记账', rule: '井档案一井一行，状态变更要有据可查：生产中→停产 必须有记录——N-11"已停仍记生产中"就是反例', crit: '主键唯一＋迁移合法', action: '隔离', autoFix: false },
  { no: 10, kind: '假数嫌疑', rule: '恒值检测：生产日报连续 30 天是同一个数——要么真停产、要么抄数，告警让人看', crit: '连续 30 日同值 → 告警', action: '告警', autoFix: false },
  { no: 11, kind: '假数嫌疑', rule: '传感器零值：当日批内电流全零即疑似设备/采集异常，出清单交业务核实（批面近似，无实时窗口）', crit: '当日批内全零 → 告警', action: '告警', autoFix: false },
  { no: 12, kind: '账对不上', rule: '物质平衡账：区块月注入量 ≈ 产出量＋存水率变动，偏差大了说明有数不对', crit: '偏差 ≤ 3%', action: '告警', autoFix: false },
  { no: 13, kind: '引用完整', rule: '引用的编号要能在关联的表里找到对应记录', crit: '详见规则库总册', action: '—（总册）', autoFix: false },
  { no: 14, kind: '跨表一致', rule: '两张表记同一件事时，数字要对得上', crit: '详见规则库总册', action: '—（总册）', autoFix: false },
  { no: 15, kind: '枚举合法', rule: '字段取值必须在约定清单里——只许从清单里选', crit: '详见规则库总册', action: '—（总册）', autoFix: false },
  { no: 16, kind: '正则格式', rule: '有固定写法的字段（编号、日期）按格式校验', crit: '详见规则库总册', action: '—（总册）', autoFix: false },
  { no: 17, kind: '极值', rule: '数值超出合理上下限即标出', crit: '详见规则库总册', action: '—（总册）', autoFix: false },
  { no: 18, kind: '波动率', rule: '数值短期内突变即提示', crit: '详见规则库总册', action: '—（总册）', autoFix: false },
  { no: 19, kind: '钩稽', rule: '几处本该相等的数互相核对', crit: '详见规则库总册', action: '—（总册）', autoFix: false },
  { no: 20, kind: '洗数规则', rule: '清洗层的改数动作要有记录、可回查', crit: '详见规则库总册', action: '—（总册）', autoFix: false }
]

// 问题单五态状态机（设定书 §1/§4）：分发 → 认领 → 整改 → 复核 → 关闭（终态锁定）
export const LANES = ['分发', '认领', '整改', '复核', '关闭']

// 合规报告（演示基线 = 任务 QT-20260915-01 的产出；同库同数重跑命中不变）
// quarantinedRows=行级隔离坏行数；rejectedBatches=整批拒收批次数（schema 级故障档——v0.4 起规则 6 超窗不再拒收，转问题单）
const REPORT_0915 = {
  range: '生产库 8 表',
  scanned: '12,604 行',
  quarantinedRows: 2,
  rejectedBatches: 1,
  hits: [
    '① 规则 1：N-02 在 2026-09-14 出现 A/B 两行重复日报',
    '② 规则 3：N-11 产油单位误录（12.40 方，应为吨——吨方混写）',
    '③ 规则 6：N-11 检修批次 20260911-T3 补录超 T-5 窗口——不拒收，收单转问题单走特批核实'
  ],
  verdict: '——已全部开成问题单并按责任岗分发（见「问题单」页签新卡）。'
}

// qrows=隔离/拦截明细（坏行/批次带定位，供责任人整改）；aiNote=LLM 归因草稿（人确认后生效）
const DYNAMIC_ISSUES = [
  {
    id: 'd1', rule_no: 1, hit_count: 1, title: '规则 1 · N-02 同日 A/B 两行重复日报', desc: 'A/B 班手抄重复',
    qrows: [{ loc: '生产日报 · N-02 · 2026-09-14', note: 'A/B 两行重复日报，保留首条，另一行隔离' }],
    aiNote: 'AI 归因（草稿，待责任人确认）：A/B 班交接时段重复录入——建议交接流程加"当日已报"校验。'
  },
  {
    id: 'd3', rule_no: 3, hit_count: 1, title: '规则 3 · N-11 产油单位误录（方 → 吨）', desc: '吨方混写，按区块密度折算',
    qrows: [{ loc: '生产日报 · N-11 · 2026-09-14', note: '日产油 12.40"方"——按渤中密度 0.89 t/m³ 折算 ≈11.04 吨' }],
    aiNote: 'AI 归因（草稿，待责任人确认）：单位"吨/方"混写，疑为录入模板未区分单位——建议折算复核后修正源表。'
  },
  {
    id: 'd6', rule_no: 6, hit_count: 1, title: '规则 6 · N-11 检修批次 T-3 补录超窗', desc: 'batch 20260911-T3 超 T-5 窗口，收单转问题单',
    qrows: [{ loc: '检修台账 · 批次 20260911-T3', note: 'T-3 补录超窗——整批拒绝入湖，待源头更正批次水位后重新进料' }],
    aiNote: 'AI 归因（草稿，待责任人确认）：批次水位晚于承诺 T-1，疑为台账补录滞后——建议更正水位后重报。'
  }
]

// 数据新鲜度（承诺 T-1＝昨天的数今天要能看到；汇总层为问数用表）
const WATER = [
  { layer: '原始层', to: '到 2026-09-14', promise: 'T-1', tag: '达标（承诺 T-1）', color: 'green' },
  { layer: '清洗层', to: '到 2026-09-14', promise: 'T-1', tag: '达标（承诺 T-1）', color: 'green' },
  { layer: '汇总层（问数用）', to: '到 2026-09-11', promise: 'T-1', tag: '落后 3 天 · 超期', color: 'gold' }
]

// ── mock 服务端状态（模拟持久层）──
const state = {
  ruleOn: Object.fromEntries(RULES.map(r => [r.no, r.no <= 12])),
  tasks: [{ id: 'QT-20260915-01', time: '2026-09-15 09:30', rules: 12, hits: 3, report: { ...REPORT_0915, rules: 12 } }],
  issues: [
    {
      id: 'p8', lane: 0, rule_no: 8, hit_count: 1, title: '规则 8 · 停机原因码旧码未映射', desc: 'equip_status 旧码 R3 未按映射表换成 BELT', owner: '责任：作业区资料员',
      qrows: [{ loc: '设备状态 equip_status', note: '停机原因旧码 R3 未按映射表换成 BELT' }]
    },
    {
      id: 'p5', lane: 1, rule_no: 5, hit_count: 1, title: '规则 5 · 停井日开井小时数仍大于 0', desc: '矛盾行：状态停着、open_days 还有数', owner: '认领：作业区资料员',
      qrows: [{ loc: '生产日报 · 停井日', note: '状态停着、开井小时数仍大于 0 的矛盾行，隔离待修正' }]
    },
    {
      id: 'p7', lane: 2, rule_no: 7, hit_count: 2, title: '规则 7 · 井号未归一（N2 → N-02）', desc: '新旧写法并存；按归一表改写', owner: '整改：作业区资料员',
      qrows: [{ loc: '井档案', note: 'N2 / N-2 未归一为 N-02（可自动修安全类——派生层归一，原始行留痕）' }]
    },
    {
      id: 'p4', lane: 3, rule_no: 4, hit_count: 1, title: '规则 4 · 含水率计量 vs 化验差 6 个百分点', desc: '已整改完毕，等质量管理员复检（小李）', owner: '复核：小李',
      verify: { batch: '批次 20260922-T1', note: '修正批次复扫全绿，待质量管理员确认' }
    },
    {
      id: 'p10', lane: 4, rule_no: 10, hit_count: 1, title: '规则 10 · 连续 30 日同值告警', desc: '核实为真实关井——不整改，记录原因后关闭', owner: '复核通过：小李',
      closeNote: '告警类规则核实为真实关井——不涉及隔离行，记录原因后关闭'
    }
  ],
  runningTask: null
}

const sleep = ms => new Promise(r => setTimeout(r, ms))
const pad = n => String(n).padStart(2, '0')
const nowStr = () => {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
const todayKey = () => {
  const d = new Date()
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`
}

// 质检任务四步节奏（演示：0.6s/步，与执行进度条一致）
const TASK_STEP_MS = 600

// ── 接口契约 ──

// GET /api/quality/rules —— 规则列表（含启用状态）
export async function getQualityRules() {
  await sleep(150)
  return { items: RULES.map(r => ({ ...r, enabled: state.ruleOn[r.no] })) }
}

// PATCH /api/quality/rules/{no} —— 启停；停用＝质检任务跳过、不删规则（审计留痕）
export async function setQualityRuleEnabled(no, enabled) {
  await sleep(150)
  if (!(no in state.ruleOn)) throw new Error('规则不存在')
  state.ruleOn[no] = enabled
  return { no, enabled }
}

// POST /api/quality/tasks —— 发起质检任务（异步执行，按当前启用规则跑生产库 8 表）
// 重跑语义（v0.5）：只清「分发未认领」的动态单（lane===0 且 d 前缀）；认领/整改/复核中的在途单保留、新命中挂同单；预置单不受影响；同一时刻最多一个进行中（409）
export async function startQualityTask() {
  await sleep(200)
  if (state.runningTask) throw new Error('已有质检任务进行中')
  state.issues = state.issues.filter(c => !(c.id.startsWith('d') && c.lane === 0))
  const seq = state.tasks.filter(t => t.id.includes(todayKey())).length + 1
  const id = `QT-${todayKey()}-${String(seq).padStart(2, '0')}`
  state.runningTask = { id, startAt: Date.now(), rulesEnabled: Object.values(state.ruleOn).filter(Boolean).length }
  return { taskId: id }
}

// GET /api/quality/tasks/{id} —— 轮询任务进度；完成时落任务记录＋合规报告，命中问题单按责任岗入「分发」列
export async function getQualityTask(taskId) {
  const run = state.runningTask
  if (!run || run.id !== taskId) {
    const done = state.tasks.find(t => t.id === taskId)
    if (done) return { taskId, status: 'done', task: done }
    throw new Error('质检任务不存在')
  }
  const step = Math.min(Math.floor((Date.now() - run.startAt) / TASK_STEP_MS), 4)
  if (step < 4) return { taskId, status: 'running', step }

  const finishedAt = nowStr()
  const task = {
    id: run.id,
    time: finishedAt,
    rules: run.rulesEnabled,
    hits: REPORT_0915.hits.length,
    report: { ...REPORT_0915, rules: run.rulesEnabled }
  }
  state.tasks.unshift(task)
  state.issues = [
    ...state.issues,
    ...DYNAMIC_ISSUES.map(c => ({ ...c, lane: 0, owner: '责任：作业区资料员（本次任务分发）' }))
  ]
  state.runningTask = null
  return { taskId, status: 'done', task }
}

// GET /api/quality/tasks —— 任务记录列表（倒序，历史保留可回看）
export async function listQualityTasks() {
  await sleep(150)
  return { items: state.tasks.map(t => ({ ...t, report: { ...t.report } })) }
}

// GET /api/quality/issues —— 问题单列表（表格管理：五态筛选由前端按 lane 呈现）
export async function listQualityIssues() {
  await sleep(150)
  return { lanes: LANES, items: state.issues.map(c => ({ ...c })) }
}

// POST /api/quality/issues/{id}/transitions —— 流转到下一态；终态「关闭」拒收（409 的 mock 对应物）；流转留痕
// 复扫语义（v0.5 人工触发）：推进到「复核」仅登记待复扫状态（verify 仍空）；请求体可选 action:"rescan"
// 对该单关联的修正批次重跑命中规则、回填 verify——复扫不是流转，lane 不变；v0.2「推进复核即自动复扫」降级挂观察
export async function transitionQualityIssue(id, action) {
  await sleep(150)
  const issue = state.issues.find(c => c.id === id)
  if (!issue) throw new Error('问题单不存在')
  if (action === 'rescan') {
    if (issue.lane !== 3) throw new Error('仅复核态可复扫')
    issue.verify = { batch: `批次 ${todayKey()}-T1`, note: '复扫全绿（mock）' }
    return { id, lane: issue.lane, state: LANES[issue.lane], verify: issue.verify }
  }
  if (issue.lane >= LANES.length - 1) throw new Error('已关闭——终态不可流转')
  if (issue.lane + 1 === 4 && !issue.verify && !issue.closeNote) {
    throw new Error('复验未全绿——修正批次复扫通过（或记录关闭原因）后才可关闭')
  }
  issue.lane += 1
  return { id, lane: issue.lane, state: LANES[issue.lane], verify: issue.verify || null }
}

// GET /api/quality/freshness —— 三层数据新鲜度水位（原始 / 清洗 / 汇总，承诺 T-1）
export async function getFreshness() {
  await sleep(150)
  return { items: WATER.map(w => ({ ...w })) }
}
