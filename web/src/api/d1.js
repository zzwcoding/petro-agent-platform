// D1 模型与线路 —— 接口契约 + mock 实现
// 契约文档：specs/api/D1-模型与线路.md（本文件函数签名 = 后端接口开发依据）
// 约定：mock 只存在于这一层，页面组件不持有业务数据；后端就绪后函数体换 fetch，签名与返回形状不变。

// ── 契约来源：specs/modules.md「网关 m2」（model_list / fallbacks / record_spend / 配置契约）──

export const MODELS = [
  {
    key: 'main', name: '工业LLM', alias: 'petro-llm', role: 'main',
    access: '内网部署 · OpenAI 兼容接口',
    note: '所有业务代码只认「调用别名」，不直接连模型；更换模型供应商只改这一处'
  },
  {
    key: 'backup', name: 'DeepSeek', alias: 'deepseek-backup', role: 'backup',
    access: 'OpenAI 兼容接口',
    note: '主用故障时自动顶上，用户无感知；冷却期满自动切回'
  }
]

export const PARAM_LIMITS = {
  allowedFails: { min: 1, max: 10 },
  cooldownSeconds: { min: 10, max: 600 },
  numRetries: { min: 0, max: 5 },
  requestTimeout: { min: 5, max: 120 }
}

const TOKEN_RATE = 0.000002 // ¥/token —— 沿用本页既有账目量级（3520 token ≈ ¥0.0070）

const DRILL_NODES = [
  { key: 'start', label: '演练开始：主用停机', error: false },
  { key: 'fail1', label: '第 1 次调用失败', error: true },
  { key: 'fail2', label: '第 2 次失败（连续满 2 次）', error: true },
  { key: 'cooldown', label: '主用进入冷却', error: false },
  { key: 'switchover', label: '自动切备用「DeepSeek」', error: false }
]
const DRILL_STEP_MS = 600

// ── mock 服务端状态（模拟持久层） ──
const state = {
  params: { allowedFails: 2, cooldownSeconds: 60, numRetries: 3, requestTimeout: 30 },
  ledger: [],   // 记账流水，演练结束会追加
  drills: [],   // 演练历史
  runningDrill: null
}

const sleep = ms => new Promise(r => setTimeout(r, ms))
const pad = n => String(n).padStart(2, '0')
const isoLocal = d =>
  `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`

let callSeq = 0x8c30
let drillSeq = 9019

function makeRow(modelKey, inputTokens, outputTokens, firstMs, totalMs, when, note = '') {
  callSeq += 7
  return {
    id: `call-${callSeq.toString(16).padStart(4, '0')}`,
    time: isoLocal(when),
    modelKey, // 'main' | 'backup'
    inputTokens, outputTokens, firstMs, totalMs,
    costYuan: Number(((inputTokens + outputTokens) * TOKEN_RATE).toFixed(4)),
    fallback: modelKey === 'backup',
    note
  }
}

// 种子账目：量级沿用本页既有账目（单次 ¥0.002–0.008、总耗时 2.4–4.3 秒），只做时间递推，不发明新量级
;(function seed() {
  const nowMs = Date.now()
  const SAMPLE = [
    [2140, 1380, 1000, 4000, 'main'], [760, 410, 800, 2400, 'main'], [1240, 860, 900, 3200, 'main'],
    [980, 540, 800, 2600, 'main'], [1100, 700, 900, 3000, 'main'], [1330, 920, 1100, 4100, 'main'],
    [860, 470, 800, 2500, 'main'], [1520, 1010, 1000, 3800, 'main'], [920, 530, 800, 2700, 'main'],
    [1080, 640, 900, 3100, 'main'], [790, 430, 800, 2400, 'main'], [1450, 980, 1000, 3700, 'main'],
    [890, 520, 1500, 3900, 'backup'], [1020, 610, 1400, 4100, 'backup'],
    [1610, 890, 900, 3300, 'main'], [1180, 720, 900, 3000, 'main'], [840, 460, 800, 2500, 'main'],
    [1290, 810, 1000, 3400, 'main'], [960, 550, 800, 2600, 'main'], [1730, 1140, 1100, 4300, 'main']
  ]
  SAMPLE.forEach((s, i) => {
    const [inp, out, first, total, key] = s
    const t = new Date(nowMs - (SAMPLE.length - i) * 4.2 * 60000)
    state.ledger.push(makeRow(key, inp, out, first, total, t, key === 'backup' ? '主用冷却期内走备用' : ''))
  })
  const EXTRA = [
    [940, 560, 900, 2900, 'main'], [1310, 840, 1000, 3500, 'backup'], [870, 480, 800, 2500, 'main'],
    [1190, 760, 900, 3100, 'main'], [1580, 1060, 1000, 3900, 'main'], [905, 510, 800, 2600, 'main'],
    [1420, 930, 1000, 3600, 'main'], [980, 540, 800, 2600, 'main'], [1120, 690, 900, 3200, 'backup'],
    [1660, 1090, 1000, 4000, 'main']
  ]
  EXTRA.forEach((s, i) => {
    const [inp, out, first, total, key] = s
    const daysAgo = i < 6 ? 1 : 7
    const t = new Date(nowMs - daysAgo * 86400000 - i * 3600000)
    state.ledger.push(makeRow(key, inp, out, first, total, t, key === 'backup' ? '主用冷却期内走备用' : ''))
  })
  state.ledger.sort((a, b) => (a.time < b.time ? 1 : -1))
  state.drills.push({
    id: 'drill-9018',
    time: isoLocal(new Date(nowMs - 40 * 60000)),
    summary: '主用「工业LLM」连续失败 2 次 → 冷却 60 秒，流量自动切换至备用「DeepSeek」；用户无感知，冷却期满自动切回'
  })
})()

function buildYaml(p) {
  return `# app/gateway/config.yaml —— 由「模型与线路」页参数生成，保存后热加载
model_list:
  - model_name: petro-llm            # 主用别名，业务代码只认别名
    litellm_params:
      model: openai/haineng
      api_base: \${HAINENG_BASE_URL}
  - model_name: deepseek-backup      # 备用
    litellm_params:
      model: openai/deepseek
      api_base: \${DEEPSEEK_BASE_URL}
fallbacks:                           # 主用故障 → 自动切备用
  - petro-llm: [deepseek-backup]
num_retries: ${p.numRetries}         # 重试只走网关层，业务侧不重试
allowed_fails: ${p.allowedFails}     # 连续失败满 N 次 → 判定故障
cooldown_time: ${p.cooldownSeconds}  # 故障冷却（秒），期内不选主用
request_timeout: ${p.requestTimeout} # 单次调用超时（秒）`
}

// ── 接口契约 ──

// GET /api/gateway/models —— 模型清单 + 网关运行状态（页头徽标）
export async function getModels() {
  await sleep(150)
  return { gateway: { status: 'running' }, models: MODELS }
}

// GET /api/gateway/config —— 读取调用参数与配置文件内容
export async function getGatewayConfig() {
  await sleep(150)
  return { params: { ...state.params }, yaml: buildYaml(state.params) }
}

// PUT /api/gateway/config —— 保存参数（写回 config.yaml 并热加载）；越界拒绝（HTTP 400 的 mock 对应物）
export async function saveGatewayConfig(params) {
  await sleep(300)
  for (const [k, lim] of Object.entries(PARAM_LIMITS)) {
    const v = params[k]
    if (!Number.isFinite(v) || v < lim.min || v > lim.max) {
      throw new Error(`参数越界：${k} 允许 ${lim.min}–${lim.max}`)
    }
  }
  state.params = { ...params }
  return { params: { ...state.params }, yaml: buildYaml(state.params) }
}

// GET /api/gateway/spend-logs —— 记账流水分页查询（time 倒序）
// 入参 { model: 'all'|'main'|'backup', range: 'all'|'today'|'7d', keyword, page, pageSize }
export async function getSpendLogs({ model = 'all', range = 'all', keyword = '', page = 1, pageSize = 15 }) {
  await sleep(150)
  const kw = keyword.trim().toLowerCase()
  const startOfToday = new Date(); startOfToday.setHours(0, 0, 0, 0)
  const rows = state.ledger.filter(r => {
    if (model !== 'all' && r.modelKey !== model) return false
    if (range === 'today' && r.time < isoLocal(startOfToday)) return false
    if (range === '7d' && r.time < isoLocal(new Date(Date.now() - 7 * 86400000))) return false
    if (kw && !(r.id + r.note).toLowerCase().includes(kw)) return false
    return true
  })
  return { items: rows.slice((page - 1) * pageSize, page * pageSize), total: rows.length, page, pageSize }
}

// POST /api/gateway/drills —— 启动故障演练；同一时刻最多一个进行中，重入拒绝（HTTP 409 的 mock 对应物）
export async function startDrill() {
  await sleep(200)
  if (state.runningDrill) throw new Error('已有演练进行中')
  const id = `drill-${drillSeq++}`
  state.runningDrill = { id, startAt: Date.now() }
  return { drillId: id }
}

// GET /api/gateway/drills/{id} —— 轮询演练进度；结束时服务端落账（流水追加一行 + 演练历史加一条）
export async function getDrill(drillId) {
  const done = state.drills.find(d => d.id === drillId)
  if (done) return { drillId, status: 'done', nodes: done.nodes, result: done.result }
  const run = state.runningDrill
  if (!run || run.id !== drillId) throw new Error('演练任务不存在')
  const idx = Math.min(Math.floor((Date.now() - run.startAt) / DRILL_STEP_MS), DRILL_NODES.length)
  const nodes = DRILL_NODES.map((n, i) => ({
    key: n.key, label: n.label,
    state: i < idx ? (n.error ? 'error' : 'finish') : i === idx ? (n.error ? 'error' : 'process') : 'wait'
  }))
  if (idx < DRILL_NODES.length) return { drillId, status: 'running', nodes }

  const finishedAt = new Date()
  const ledgerRow = makeRow('backup', 1010, 590, 1300, 3800, finishedAt, '故障自动切换：请求别名 petro-llm → 备用 DeepSeek 应答')
  state.ledger.unshift(ledgerRow)
  const record = {
    id: drillId,
    time: isoLocal(finishedAt),
    summary: `主用「工业LLM」连续失败 ${state.params.allowedFails} 次 → 冷却 ${state.params.cooldownSeconds} 秒，流量自动切换至备用「DeepSeek」；用户无感知，冷却期满自动切回`,
    nodes, result: {
      conclusion: '主用停机期间备用应答正常，用户无感知；主用冷却期满自动切回。',
      fallback: {
        time: isoLocal(finishedAt), event: 'fallback_triggered',
        request_alias: 'petro-llm', failed_deploy: 'openai/haineng',
        failover_target: 'openai/deepseek',
        consecutive_fails: state.params.allowedFails, cooldown_sec: state.params.cooldownSeconds
      },
      ledgerRow
    }
  }
  state.drills.unshift(record)
  state.runningDrill = null
  return { drillId, status: 'done', nodes, result: record.result }
}

// GET /api/gateway/drills —— 演练历史列表
export async function listDrills() {
  await sleep(150)
  return state.drills.map(d => ({ id: d.id, time: d.time, summary: d.summary }))
}

// GET /api/gateway/spend-stats —— 花费聚合/趋势读面（D5 撤页归并批，账本唯一真源＝记账流水，聚合投影不建第二份账本）
// 入参 { groupBy: 'caller'|'model'|'day'|'month', range: 'all'|'7d'|'30d'|'12m', page, pageSize }
// P1-00a 快照同步所必需的新增（teach 原型 2026-10-01 终稿 D1 改版消费此端点）；实现逐字取自 teach api/d1.js，
// 平台账目行暂无 caller 归因字段，聚合时安全归入 unattributed——P1-10 D1 增强票接线时补齐
export async function getSpendStats({ groupBy = 'caller', range = 'all', page = 1, pageSize = 15 }) {
  await sleep(150)
  const RANGE_MS = { '7d': 7, '30d': 30, '12m': 365 }
  const rows = state.ledger.filter(r => {
    if (range === 'all') return true
    return new Date(r.time) >= new Date(Date.now() - RANGE_MS[range] * 86400000)
  })
  const keyOf = {
    caller: r => (r.caller ?? 'unattributed'),
    model: r => r.modelKey,
    day: r => r.time.slice(0, 10),
    month: r => r.time.slice(0, 7)
  }[groupBy]
  const grouped = new Map()
  for (const r of rows) {
    const k = keyOf(r)
    if (!grouped.has(k)) grouped.set(k, { key: k, calls: 0, fallbackCalls: 0, inputTokens: 0, outputTokens: 0, costYuan: 0 })
    const g = grouped.get(k)
    g.calls += 1
    if (r.fallback) g.fallbackCalls += 1
    g.inputTokens += r.inputTokens
    g.outputTokens += r.outputTokens
    g.costYuan = Number((g.costYuan + r.costYuan).toFixed(4))
  }
  const items = [...grouped.values()]
  // caller/model＝花费降序（谁花得多排前面）；day/month＝趋势时序，时间升序
  if (groupBy === 'day' || groupBy === 'month') items.sort((a, b) => (a.key > b.key ? 1 : -1))
  else items.sort((a, b) => b.costYuan - a.costYuan)
  const sums = items.reduce(
    (acc, g) => ({
      calls: acc.calls + g.calls,
      fallbackCalls: acc.fallbackCalls + g.fallbackCalls,
      costYuan: Number((acc.costYuan + g.costYuan).toFixed(4))
    }),
    { calls: 0, fallbackCalls: 0, costYuan: 0 }
  )
  if (groupBy === 'day' || groupBy === 'month') {
    return { groupBy, range, items, sums, total: items.length, page: 1, pageSize }
  }
  return {
    groupBy, range,
    items: items.slice((page - 1) * pageSize, page * pageSize),
    sums, total: items.length, page, pageSize
  }
}
