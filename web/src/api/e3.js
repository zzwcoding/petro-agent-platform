// E3 知识体检 —— 接口契约 + mock 实现
// 契约文档：specs/api/E3-知识体检.md（本文件函数签名 = 后端接口开发依据）
// 约定：mock 只存在于这一层，页面组件不持有业务数据；后端就绪后函数体换 fetch，签名与返回形状不变。
// 契约来源：specs/modules.md「语义 m16 / 评估 m18」· 设定书 §3 指标 / §6 术语 / §A 样本 · PRD F24（版本 7 增补三，票 108）· 票 102 §五 体检触发三路
// 业界依据：docs/research/2026-09-28-知识体检产品化调研.md（OpenMetadata Data Insights 覆盖率 KPI + 周期报告；差异增量=建议确认转提案闭环）

// 四维（按序）——业务语言版元数据完备度评分：资料全不全 / 逻辑顺不顺 / 数据覆盖够不够 / 关系健全不健全
export const DIMS = ['资料全不全', '逻辑顺不顺', '数据覆盖够不够', '关系健全不健全']

// 体检对象：来自平台四本账（C1 指标与术语库）。分数与建议为演示种子，接真值后替换
// sugg[].confirmed = 已确认转提案（"已进 C2"）——仅种子中已有对应 C2 提案的两条预置
const OBJECTS = {
  'N-02': {
    label: 'N-02 渤中28-1-N2', name: 'N-02 渤中28-1-N2', type: '井',
    scores: [92, 95, 88, 90], grade: '健康',
    sugg: [
      { tag: '缺来源', text: '备注字段里有一段来路不明的旧文本（供应商导入塞入）——建议标注来源或清理' }
    ]
  },
  'N-06': {
    label: 'N-06', name: 'N-06', type: '井',
    scores: [90, 92, 85, 94], grade: '健康',
    sugg: [
      { tag: '缺来源', text: '受效关系的劈分系数、响应起始日没有登记出处（受效关系属性应登记出处）' }
    ]
  },
  'N-11': {
    label: 'N-11', name: 'N-11', type: '井',
    scores: [88, 62, 70, 75], grade: '需补课',
    sugg: [
      { tag: '逻辑打架', text: '档案状态滞后——2026-08-30 起检泵停产，档案仍记"生产中"' },
      { tag: '缺来源', text: '检修影响产量"约 210 吨"来自各作业区估算，口径不一' },
      { tag: '缺负责人', text: '状态变更记录没有认领人' }
    ]
  },
  'bo-nan': {
    label: '渤南', name: '渤南区块', type: '区块',
    scores: [90, 88, 82, 86], grade: '健康',
    sugg: [
      { tag: '缺来源', text: '原油密度 0.86 t/m³（吨方换算用）需挂单位换算表出处' }
    ]
  },
  'bo-zhong': {
    label: '渤中', name: '渤中区块', type: '区块',
    scores: [86, 84, 80, 82], grade: '亚健康',
    sugg: [
      { tag: '孤儿关系', text: '有井没挂上"井—隶属→区块"关系——按区块汇总时会漏井', confirmed: '已进 C2（提案：渤中孤儿关系补全）' },
      { tag: '缺负责人', text: '区块级数据负责人未指定' }
    ]
  },
  'bo-xi': {
    label: '渤西', name: '渤西区块', type: '区块',
    scores: [80, 78, 72, 76], grade: '亚健康',
    sugg: [
      { tag: '缺来源', text: '化验样频次不齐（高产周报 / 低产半月报），缺样插补规则未登记' },
      { tag: '缺负责人', text: '区块级数据负责人未指定' }
    ]
  },
  'm-complete': {
    label: '产量完成率', name: '产量完成率', type: '指标',
    scores: [95, 90, 88, 92], grade: '健康',
    sugg: [
      { tag: '口径待裁决', text: '配产计划版本切换日出现双值行——需明确取哪个版本' }
    ]
  },
  'm-effective': {
    label: '有效产量', name: '有效产量', type: '指标',
    scores: [92, 70, 85, 88], grade: '亚健康',
    sugg: [
      { tag: '口径待裁决', text: '一词两译（开井日历折算 / 剔检）缺默认口径标注——已有提案在语义修订提案池（C2）', confirmed: '已进 C2（提案：有效产量默认口径）' }
    ]
  },
  'm-decline': {
    label: '递减增油', name: '递减增油', type: '指标',
    scores: [85, 52, 75, 80], grade: '需补课',
    sugg: [
      { tag: '口径待裁决', text: '两作业区算法不一致（事故 7），条目挂"待联席裁决"' },
      { tag: '缺来源', text: '劈分系数（Σ=1）的出处未登记' }
    ]
  },
  'm-measure': {
    label: '措施有效期', name: '措施有效期', type: '指标',
    scores: [88, 86, 58, 84], grade: '需补课',
    sugg: [
      { tag: '资料缺项', text: '措施起止日期 30% 行缺失——建议补台账' },
      { tag: '缺负责人', text: '缺失行的补录责任人未指定' }
    ]
  }
}

const GROUPS = [
  { name: '井', keys: ['N-02', 'N-06', 'N-11'] },
  { name: '区块', keys: ['bo-nan', 'bo-zhong', 'bo-xi'] },
  { name: '指标', keys: ['m-complete', 'm-effective', 'm-decline', 'm-measure'] }
]
const OBJECT_KEYS = GROUPS.flatMap(g => g.keys)

// ── mock 服务端状态（模拟持久层）──
const state = {
  objects: Object.fromEntries(OBJECT_KEYS.map(k => [k, JSON.parse(JSON.stringify(OBJECTS[k]))])),
  lastCheckup: '2026-09-28 02:00（周期）',
  runSeq: 0,
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

// 体检四步节奏（演示：0.6s/步）：扫描四本账 → 逐对象四维评分 → 生成补全建议 → 归一体检发现单
const RUN_STEP_MS = 600
export const RUN_STEPS = ['扫描四本账', '逐对象四维评分', '生成补全建议', '归一体检发现单']

const snapshot = k => ({ key: k, ...JSON.parse(JSON.stringify(state.objects[k])) })

// ── 接口契约 ──

// GET /api/checkup/objects —— 体检对象清单（含四维分数 / 总评 / 补全建议及确认状态）
export async function getCheckupObjects() {
  await sleep(150)
  return { dims: DIMS, items: OBJECT_KEYS.map(snapshot) }
}

// POST /api/checkup/runs —— 发起体检（触发三路之"人工立即跑"；周期调度为主入口，不经本端点）
// 同库同数：评分与建议结果不变，运行记录与"上次体检"刷新。同一时刻最多一个运行中（409 的 mock 对应物）
export async function startCheckupRun() {
  await sleep(200)
  if (state.runningTask) throw new Error('已有体检运行中')
  state.runSeq += 1
  const id = `KC-${todayKey()}-${String(state.runSeq).padStart(2, '0')}`
  state.runningTask = { id, startAt: Date.now() }
  return { runId: id }
}

// GET /api/checkup/runs/{id} —— 轮询运行进度；完成时回填"上次体检"
export async function getCheckupRun(runId) {
  const run = state.runningTask
  if (!run || run.id !== runId) {
    throw new Error('体检运行不存在')
  }
  const step = Math.min(Math.floor((Date.now() - run.startAt) / RUN_STEP_MS), 4)
  if (step < 4) return { runId, status: 'running', step }
  state.lastCheckup = `${nowStr()}（人工）`
  state.runningTask = null
  return { runId, status: 'done', finishedAt: state.lastCheckup, totals: { objects: OBJECT_KEYS.length } }
}

// POST /api/checkup/suggestions/confirm —— 建议确认 · 转提案：确认后归一体检发现单进 C2（"自动体检发现"来源）
// 六站环发现→归一的页面闭环；确认留痕（谁/何时），平台只归一不改正（F24/F25 红线）
export async function confirmSuggestion(objectKey, suggIndex) {
  await sleep(150)
  const obj = state.objects[objectKey]
  const sugg = obj && obj.sugg[suggIndex]
  if (!sugg) throw new Error('建议不存在')
  if (sugg.confirmed) throw new Error('该建议已确认进 C2')
  sugg.confirmed = '已进 C2（提案：' + obj.name + ' · ' + sugg.tag + '）'
  return { objectKey, suggIndex, confirmed: sugg.confirmed }
}

// GET 状态行（上次体检 / 下次计划 / 累计发现——下次计划与累计发现为演示常量，真实接调度器后替换）
export async function getCheckupStatus() {
  await sleep(100)
  return { lastCheckup: state.lastCheckup, nextPlanned: '2026-09-29 02:00', totalFindingsToC2: 7 }
}
