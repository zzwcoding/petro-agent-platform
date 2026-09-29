// D3 安全与权限 —— 接口契约 + mock 实现
// 契约文档：specs/api/D3-安全与权限.md（本文件函数签名 = 后端接口开发依据）
// 约定：mock 只在这一层，页面组件不持有业务数据；后端就绪后函数体换 fetch，签名与返回形状不变。

// ── 契约来源：m17 查询安检 / m19 注入防御 / m8 权限与沙箱 / m11 国密 / m1 认证留痕 ──
// 合同值红线：限量默认 50·上限 200（PRD F14）；三闸 50,000 行/512MB/60 秒（PRD F57）；
// 拒绝三字段 gate/trigger/disposal；四级信任（m19 TaintTag）；五层权限（PRD F48）。均不可改动。

export const TRUST_LEVELS = [
  { key: 1, level: '1 系统设定', src: '平台自己的规则与流程约定' },
  { key: 2, level: '2 开发者设定', src: '建设时写死的配置与说明' },
  { key: 3, level: '3 用户输入', src: '当前提问的人打的字' },
  { key: 4, level: '4 数据内容', src: '报告块、工具查回来的结果（资料，不是命令）' }
]

export const PERMISSION_LAYERS = [
  { key: 'context', name: '背景注入', nick: '能看', help: '不配背景资料，相关入口在他的界面上不出现——不是被拦下。' },
  { key: 'query', name: '自主查询', nick: '能查', help: '不授对象（表），他问数据，平台的世界里就没有那张表。' },
  { key: 'compute', name: '专业计算', nick: '能算', help: '不授专业工具，就算不了。' },
  { key: 'write', name: '写操作', nick: '能动', help: '没有写入口＝界面上没有"改数据"的按钮。' },
  { key: 'governance', name: '治理约束', nick: '守规矩', help: '口径与流程约束：改口径走提案池，责任人 / 终审见各角色行。' }
]

const sleep = ms => new Promise(r => setTimeout(r, ms))
const pad = n => String(n).padStart(2, '0')
const isoLocal = d =>
  `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
const minutesAgo = m => isoLocal(new Date(Date.now() - m * 60000))

// ── mock 服务端状态 ──
const state = {
  overview: { policyVersion: 'v2.3', lastGateCheck: '2026-09-27 18:40 · 发布流水线（C3）通过' },
  queryPolicy: {
    switches: [
      { key: 'readonly_only', name: '只放行查看语句', desc: '改数据、删数据的语句根本不进数据库', enabled: true },
      { key: 'table_whitelist', name: '可用表白名单', desc: '不在单子上的表，查询直接不执行', enabled: true },
      { key: 'row_limit', name: '强制限量', desc: '防止一次捞空大表：只封顶、不抬底', enabled: true },
      { key: 'row_filter', name: '按人过滤数据行', desc: '查询自动带上"只看权限范围内"的条件，并在解释链写明', enabled: true }
    ],
    defaultLimit: 50,
    maxLimit: 200 // 合同上限（PRD F14），只读
  },
  outbound: {
    // 语义固定：会话含外部资料（被污染）时，外发默认拒绝；登记进白名单的通道例外放行（m19 assert_outbound）
    defaultWhenTainted: 'deny',
    channels: [
      {
        id: 'invoke_api', tool: 'invoke_api', target: '任意外部系统',
        what: '通用外发：把数据发往平台之外的系统', registered: false, credentialHint: null
      },
      {
        id: 'send_report', tool: 'send_report', target: 'data-report.cnooc.bs',
        what: '数据报送：月度结算数据报送上级单位（场景见对外接口·内外同权）', registered: true, credentialHint: 'sk-****'
      },
      {
        id: 'send_alert', tool: 'send_alert', target: 'prod-alert.cnooc.bs',
        what: '告警外送：生产告警推送值班系统', registered: false, credentialHint: null
      }
    ]
  },
  sandbox: {
    limits: {
      maxRows: 50000, memoryMb: 512, wallSeconds: 60,
      onReject: ['降级估算并标注"估算口径"', '留白拒答'],
      runtimeNote: '国产化容器运行时 · 麒麟 OS · 单次任务一容器',
      scopeNote: '沙箱不对平台对外的 Agent 接口开放——工作流是治理领导组审批过的资产，要改走语义修订提案池。'
    },
    runs: [
      { id: 'run-1042', time: minutesAgo(96), script: '《产量下滑归因》步骤 2', gate: '读入行数上限（50,000 行）', disposal: '容器终止销毁', onReject: '降级估算' }
    ],
    running: null
  },
  auditLogs: [
    { time: '09:41', who: '阿强', action: '修改强制限量默认 50 行（上限 200）', digest: '77b1…9e' },
    { time: '09:38', who: '阿强', action: '登记外发通道 send_report 白名单放行', digest: 'a3f8…c2' },
    { time: '09:12', who: '阿强', action: '修改精排档位', digest: '5d02…71' },
    { time: '08:55', who: '系统', action: '发布流水线（C3）第 214 批通过', digest: '90ce…33' },
    { time: '08:41', who: '阿强', action: '密钥自检通过（3/3 分项）', digest: '1b7f…a8' },
    { time: '08:22', who: '阿强', action: '表白名单新增 date_dim（对象账关联）', digest: '6c44…d0' },
    { time: '昨 17:48', who: '系统', action: '查询安检策略热加载生效（v2.3）', digest: 'e290…5b' },
    { time: '昨 16:03', who: '阿强', action: '驳回语义修订提案 #PP-0417（口径证据不足）', digest: 'f813…97' }
  ]
}

// ── 接口契约 ──

// GET /api/security/overview —— 页头：策略版本 + 最近发布安检状态
export async function getSecurityOverview() {
  await sleep(120)
  return { ...state.overview }
}

// GET /api/security/query-policy
export async function getQueryPolicy() {
  await sleep(150)
  return JSON.parse(JSON.stringify(state.queryPolicy))
}

// PUT /api/security/query-policy —— 保存；写回后需经发布流水线（C3）生效（服务端语义，前端只透传提示）
export async function saveQueryPolicy(policy) {
  await sleep(300)
  if (!Number.isFinite(policy.defaultLimit) || policy.defaultLimit < 1 || policy.defaultLimit > state.queryPolicy.maxLimit) {
    throw new Error(`defaultLimit 允许 1–${state.queryPolicy.maxLimit}`)
  }
  state.queryPolicy = JSON.parse(JSON.stringify(policy))
  return JSON.parse(JSON.stringify(state.queryPolicy))
}

// GET /api/security/table-whitelist —— 9 张允许表（设定书 §A）+ 默认拒绝；usedBy＝引用方（占用可见性）
export async function getTableWhitelist() {
  await sleep(150)
  return {
    denyDefault: true,
    tables: [
      { cn: '井档案', en: 'well_info', note: '一井一行的基础档案', usedBy: ['井档案页（A2）', '对象账·井'] },
      { cn: '日产计量', en: 'oil_production_daily', note: '核心事实表，问产量都从这来', usedBy: ['工具·按井查产量', '工作流·产量下滑归因'] },
      { cn: '注水日报', en: 'water_injection_daily', note: '分层注水', usedBy: ['工具·按井查产量'] },
      { cn: '检修台账', en: 'well_overhaul', note: '检泵等检修记录', usedBy: ['井档案页（A2）· 关系链'] },
      { cn: '措施台账', en: 'well_measures', note: '压裂/酸化等措施', usedBy: ['井档案页（A2）· 关系链'] },
      { cn: '化验样', en: 'fluid_test', note: '含水/密度化验', usedBy: ['工具·按井查产量'] },
      { cn: '设备状态', en: 'equip_status', note: '电泵/螺杆泵等状态', usedBy: ['对象账·设备'] },
      { cn: '月度结算', en: 'monthly_settlement', note: '经营口径净重', usedBy: ['指标卡·月度结算'] },
      { cn: '日期维表', en: 'date_dim', note: '按月/按季度统计的日期对照（对象账关联白名单）', usedBy: ['对象账·期'] }
    ]
  }
}

// GET /api/security/outbound-policy
export async function getOutboundPolicy() {
  await sleep(150)
  return JSON.parse(JSON.stringify(state.outbound))
}

// PUT /api/security/outbound-policy —— 逐通道登记/撤销登记（占位凭据=保留旧密钥，服务端语义）
export async function saveOutboundPolicy(outbound) {
  await sleep(250)
  state.outbound = JSON.parse(JSON.stringify(outbound))
  return JSON.parse(JSON.stringify(state.outbound))
}

// GET /api/security/sandbox-limits —— 三闸合同值（只读；变更走发布前安检审批，本页不提供编辑）
export async function getSandboxLimits() {
  await sleep(120)
  return { ...state.sandbox.limits }
}

const RUN_STEPS = [
  { key: 'start', label: '工作流《产量下滑归因》步骤 2：拉全油田产量明细（时间窗 30 天）', error: false },
  { key: 'window', label: '时间窗被圈成三年 → 估算读入 131,000 行', error: false },
  { key: 'gate', label: '读到 50,000 行上限 → 第一道闸触发', error: true },
  { key: 'reject', label: '结构化拒绝：闸 / 触发 / 处置三字段留痕', error: false },
  { key: 'onreject', label: 'on_reject 档位：降级估算 ＋ 标注"估算口径"', error: false }
]
const RUN_STEP_MS = 700

// POST /api/security/sandbox-runs —— 启动一次试跑（真实受限执行的服务端语义）；重入拒绝（409 对应物）
export async function startSandboxRun() {
  await sleep(200)
  if (state.sandbox.running) throw new Error('已有试跑进行中')
  const id = `run-${1043 + state.sandbox.runs.length - 1}`
  state.sandbox.running = { id, startAt: Date.now() }
  return { runId: id }
}

// GET /api/security/sandbox-runs/{id} —— 轮询试跑进度；结束时结构化拒绝三字段落历史
export async function getSandboxRun(runId) {
  const done = state.sandbox.runs.find(r => r.id === runId)
  if (done) return { runId, status: 'done', nodes: done.nodes, result: done.result }
  const run = state.sandbox.running
  if (!run || run.id !== runId) throw new Error('试跑任务不存在')
  const idx = Math.min(Math.floor((Date.now() - run.startAt) / RUN_STEP_MS), RUN_STEPS.length)
  const nodes = RUN_STEPS.map((n, i) => ({
    key: n.key, label: n.label,
    state: i < idx ? (n.error ? 'error' : 'finish') : i === idx ? (n.error ? 'error' : 'process') : 'wait'
  }))
  if (idx < RUN_STEPS.length) return { runId, status: 'running', nodes }

  const finishedAt = new Date()
  const result = {
    rejected: {
      gate: '读入行数上限（50,000 行）',
      trigger: '已读 50,000 行（本次任务共 131,000 行）',
      disposal: '容器终止销毁——部分结果绝不冒充完整结果'
    },
    onReject: '降级估算 ＋ 标注"估算口径"',
    conclusion: '拦不拦由代码判据说了算，不靠模型自觉；拒绝三字段落审计留痕。'
  }
  const record = {
    id: runId, time: isoLocal(finishedAt), script: '《产量下滑归因》步骤 2',
    gate: '读入行数上限（50,000 行）', disposal: '容器终止销毁', onReject: '降级估算',
    nodes, result
  }
  state.sandbox.runs.unshift(record)
  state.sandbox.running = null
  return { runId, status: 'done', nodes, result }
}

// GET /api/security/sandbox-runs —— 试跑历史（拒绝也留痕，倒序）
export async function listSandboxRuns() {
  await sleep(120)
  return state.sandbox.runs.map(r => ({ id: r.id, time: r.time, script: r.script, gate: r.gate, disposal: r.disposal, onReject: r.onReject }))
}

// GET /api/security/permission-matrix —— 角色×五层（PRD F48 合同）
// badges: ok=有入口 / none=没有 / constrained=受约束 / partial=部分 / owner=责任人 / final=终审
export async function getPermissionMatrix() {
  await sleep(180)
  return {
    layers: PERMISSION_LAYERS,
    roles: [
      {
        key: 'laowang', name: '老王（油藏工程师）',
        badges: ['ok', 'ok', 'ok', 'none', 'constrained'],
        detail: [
          [{ t: '能看：本岗相关井/区块的背景资料自动带入问答（' }, { a: ['#/A2', '井档案页 · 井 360°'] }, { t: '）' }],
          [{ t: '能查：只读查数（白名单表＋按人过滤＋限量，见「查询安检」页签）' }],
          [{ t: '能算：产量预测、岩性识别等专业工具（只读角色可用）' }],
          [{ t: '能动：无写入口——只读角色，界面上没有"改数据"的按钮' }],
          [{ t: '守规矩：口径一律以语义账为准，个人不能改口径（改口径走' }, { a: ['#/C2', '语义修订提案池'] }, { t: '）' }]
        ]
      },
      {
        key: 'xiaoli', name: '小李（地质 · 质量管理员）',
        badges: ['ok', 'ok', 'ok', 'partial', 'constrained'],
        detail: [
          [{ t: '能看：报告库全量背景（上传与索引见' }, { a: ['#/B1', '报告库'] }, { t: '）' }],
          [{ t: '能查：只读查数（同上）' }],
          [{ t: '能算：专业计算工具' }],
          [{ t: '能动：仅知识资料类（上传报告、维护常见问题库）；生产数据无写入口' }],
          [{ t: '守规矩：质检任务配置受数据管理岗职责约束' }]
        ]
      },
      {
        key: 'zhuren', name: '主任（汇报人）',
        badges: ['ok', 'ok', 'ok', 'none', 'constrained'],
        detail: [
          [{ t: '能看：汇报相关背景资料自动带入' }],
          [{ t: '能查：只读查数（同上）' }],
          [{ t: '能算：分析工作流与成品生成（' }, { a: ['#/A1', '问一问'] }, { t: '「做汇报」）' }],
          [{ t: '能动：无写入口' }],
          [{ t: '守规矩：晨会常问指标以语义账口径为准，同数同源。' }]
        ]
      },
      {
        key: 'aqiang', name: '阿强（运维 · 语义负责人）',
        badges: ['ok', 'ok', 'ok', 'ok', 'owner'],
        detail: [
          [{ t: '能看：全量' }],
          [{ t: '能查：只读查数' }],
          [{ t: '能算：专业计算工具' }],
          [{ t: '能动：平台配置（本区六页）＋语义资产变更——但变更只能' }, { a: ['#/C2', '提提案'] }, { t: '、' }, { a: ['#/C3', '过安检'] }, { t: '，负责人批准才发布' }],
          [{ t: '守规矩：语义 Owner＝本区设置的责任人' }]
        ]
      },
      {
        key: 'owner', name: '治理领导组（Owner）',
        badges: ['ok', 'ok', 'ok', 'ok', 'final'],
        detail: [
          [{ t: '能看/能查/能算：同上全量' }],
          [{ t: '能动：高影响变更终审批准（' }, { a: ['#/A3', '数据变动审批'] }, { t: '高风险终审）' }],
          [{ t: '守规矩：治理领导组＝高影响变更审批与评审会' }]
        ]
      },
      {
        key: 'intern', name: '实习生（未配置权限）',
        badges: ['none', 'none', 'none', 'none', 'none'],
        emptyDetail: true
      }
    ]
  }
}

// GET /api/security/crypto-fields —— 加密字段清单（m3 EncryptedField 元数据口径）
export async function getCryptoFields() {
  await sleep(120)
  return [
    { field: '用户手机号', where: '用户表', method: '国密 SM4（分组加密，随机扰码）', look: 'rW3xK9…（一串密文，无明文；读回时才解密）' }
  ]
}

// POST /api/security/key-selfcheck —— 密钥自检（m11 key_selfcheck）；分项结果，失败也是 200 查 data.ok
export async function runKeySelfcheck() {
  await sleep(700)
  return {
    ok: true,
    checkedAt: isoLocal(new Date()),
    checks: [
      { name: '主密钥在位', ok: true, message: '密钥句柄可读，未检测到轮换残留', latencyMs: 61 },
      { name: '密文抽检可解', ok: true, message: '抽样 16 条密文全部解密成功', latencyMs: 214 },
      { name: '摘要校验通过', ok: true, message: 'SM3 抽样比对一致，无篡改迹象', latencyMs: 118 }
    ]
  }
}

// GET /api/security/audit-logs —— 操作留痕（只记 SM3 摘要指纹，不记正文）；分页
export async function getAuditLogs({ page = 1, pageSize = 8 } = {}) {
  await sleep(150)
  return {
    items: state.auditLogs.slice((page - 1) * pageSize, page * pageSize),
    total: state.auditLogs.length, page, pageSize
  }
}
