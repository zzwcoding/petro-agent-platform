/**
 * events.js · 执行流水线纯逻辑（Owner 2026-10-17 串行链条模型）。
 *
 * 模型：每轮＝三段串行块——**用户输入块 → 系统执行流水线块（typed 事件流）→ 系统回答块**。
 * 本件只管流水线块的数据面：把单轮 turn 的归约结果**派生成有序事件流**（渲染序＝真机到达序
 * 的显示口径），以及摘要行的计数。零副作用、零请求——可直喂单测。
 *
 * 事件类型 → 行渲染（渲染件在 ExecutionPipeline.jsx）：
 *   understanding｜step｜tool｜materials（聚合行）｜notice｜verify｜citation
 *
 * ⚠ 排序口径（真机**信封 id 跨类型序**在归约后的 turn 里不可得——turn 只有分类型的数组；
 * 真接 SSE 后事件流由归约器按到达序直接产出，本件即退役。当前规则逐条写死可测）：
 *   ① 步按 `seq` 升序（真机实录 tool(seq7) 先于其承载 step(seq7) 到达——归组后不体现，
 *      横幅「工具挂到同 seq 步下」按设计稿 §3.1 归组纪律）；
 *   ② 材料聚合行插在**材料相位末步之后**（相位优先级 execute > discover/observe > decision）；
 *   ③ A/B 级与「相位归属未登记」的 notice ＝材料面提示，紧随材料聚合行（未取到材料＝排理解旁白之后）；
 *   ④ C 级 notice 挂其相位末步之后（NOTICE_PHASE）；**该相位无步在场**（如运行中前缀未到核验步）
 *      → 退材料面提示位——不静默丢；
 *   ⑤ verify 事件在全部步与 notice 之后、citation 之前；
 *   ⑥ citation 逐条按 index 升序。
 *
 * ⚠ 材料明细不进流水线（只记聚合「找到 N 份材料」——明细在右栏「引用与口径」）。
 */

/** 引用按 index 升序（真机 citation 帧即按 index 发出；兜底排序防乱序输入）。 */
const byIndex = (a, b) => (a.index ?? 0) - (b.index ?? 0)
const bySeq = (a, b) => (a.seq ?? 0) - (b.seq ?? 0)

/** 六相位 → 白话（设计稿 §3.1 映射表；未登记相位原样回显）。 */
export const PHASE_TEXT = {
  decision: '分析问题',
  discover: '检索资料',
  execute: '取数',
  observe: '查看材料',
  verify: '核验',
  answer: '作答'
}

/** 工具名 → 白话（设计稿 §3.1 映射表；未登记工具原样回显）。 */
export const TOOL_TEXT = {
  doc_retrieve: '查文档库',
  semantic_query: '查指标台账',
  data_query: '取数',
  faq_lookup: '查常见问题',
  table_schema: '查表结构'
}

/** 相位白话（未登记值原样回显——闭世界会增补，不静默丢）。 */
export const phaseText = phase => PHASE_TEXT[phase] ?? phase

/** 工具白话（同上）。 */
export const toolText = tool => TOOL_TEXT[tool] ?? tool

/** A 级：醒目（拒答/失败/截断/域外降级/写档失败）。 */
export const NOTICE_LEVEL_A = new Set([
  'refused', 'run_failed', 'freshness_block', 'unbound_degrade', 'schema_not_allowed',
  'material_truncated', 'emission_strip', 'blackbox_write_failed', 'audit_write_failed'
])

/** B 级：过程说明（灰）。 */
export const NOTICE_LEVEL_B = new Set([
  'rebind', 'window_note', 'no_hit', 'approval_recorded', 'ban_exempt',
  'clarify_capped', 'budget_converged', 'window_miss_reentry'
])

/** C 级：回喂面工序腔（默认收起）。 */
export const NOTICE_LEVEL_C = new Set([
  'decision_rejected', 'same_param_replay', 'emission_quote_repair', 'decision_note',
  'chain_switch_reentry', 'subtask_failed', 'subtask_refused', 'tool_unavailable',
  'unsupported_claim', 'contradiction_split', 'attribution_split'
])

/** 未登记 type ＝ 'unknown'（通用灰条兜底，不静默丢弃）。 */
export function noticeLevel(type) {
  if (NOTICE_LEVEL_A.has(type)) return 'A'
  if (NOTICE_LEVEL_B.has(type)) return 'B'
  if (NOTICE_LEVEL_C.has(type)) return 'C'
  return 'unknown'
}

/** C 级 notice type → 归属相位（③④ 规则用；未登记＝无相位归属）。 */
export const NOTICE_PHASE = {
  decision_rejected: 'decision',
  same_param_replay: 'decision',
  decision_note: 'decision',
  chain_switch_reentry: 'decision',
  tool_unavailable: 'execute',
  subtask_failed: 'execute',
  subtask_refused: 'execute',
  unsupported_claim: 'verify',
  contradiction_split: 'verify',
  attribution_split: 'verify',
  emission_quote_repair: 'verify'
}

/** 材料相位优先级（② 规则）：取末个命中相位的步作为材料聚合行插入点。 */
const MATERIAL_PHASES = ['execute', 'discover', 'observe', 'decision']

/**
 * 材料聚合行插入点＝第几个 step 之后（-1＝无步，退理解旁白之后）。
 * 规则：MATERIAL_PHASES 里优先级最高的、在步表里**最后出现**的那步。
 */
function materialBoundary(steps) {
  for (const ph of MATERIAL_PHASES) {
    const idx = steps.map((s, i) => (s.station === ph ? i : -1)).filter(i => i >= 0).pop()
    if (idx !== undefined) return idx
  }
  return -1
}

/**
 * turn → 有序事件流（渲染序）。
 * @param turn 归约器 turn 形状（steps/tools/materials/notices/citations/verdicts/understanding）
 * @returns 事件数组：{type:'understanding'|'step'|'tool'|'materials'|'notice'|'verify'|'citation'}
 */
export function deriveEvents(turn) {
  const t = turn || {}
  const steps = [...(t.steps || [])].sort(bySeq)
  const tools = [...(t.tools || [])].sort(bySeq)
  const citations = [...(t.citations || [])].sort(byIndex)
  const events = []

  // notice 分派（③④）：有相位归属且该相位有步在场＝挂相位；否则＝材料面提示
  const phaseNotices = {}
  const materialNotices = []
  for (const n of t.notices || []) {
    const ph = NOTICE_PHASE[n?.type]
    if (ph && steps.some(s => s.station === ph)) {
      phaseNotices[ph] = [...(phaseNotices[ph] || []), n]
    } else {
      materialNotices.push(n)
    }
  }
  const pushNotice = (n, into) => into.push({ type: 'notice', level: noticeLevel(n?.type), notice: n })

  if (t.understanding) events.push({ type: 'understanding', text: t.understanding })

  const boundary = materialBoundary(steps)
  const pushMaterials = () => {
    if ((t.materials || []).length > 0) events.push({ type: 'materials', count: t.materials.length })
    materialNotices.forEach(n => pushNotice(n, events))
  }

  const lastOfPhase = ph => steps.map((s, i) => (s.station === ph ? i : -1)).filter(i => i >= 0).pop()
  steps.forEach((s, i) => {
    events.push({ type: 'step', seq: s.seq, phase: s.station, title: s.title || '' })
    tools.filter(x => x.seq === s.seq).forEach(x => events.push({
      type: 'tool', seq: s.seq, tool: x.tool, status: x.status || '', message: x.message || ''
    }))
    if (i === boundary) pushMaterials()
    if (i === lastOfPhase(s.station)) (phaseNotices[s.station] || []).forEach(n => pushNotice(n, events))
  })
  // 无步兜底（② 无步＝材料聚合排理解旁白之后）＋未排出者一律补位（不静默丢）
  if (steps.length === 0 || boundary < 0) pushMaterials()
  else if (materialNotices.length > 0 && !events.some(e => e.type === 'materials')) pushMaterials()

  const v = (t.verdicts || [])[0]
  if (v) events.push({ type: 'verify', verdict: v })
  citations.forEach(c => events.push({ type: 'citation', cite: c }))
  return events
}

/**
 * 流水线摘要行计数（折叠态一行）。
 * @returns {state, stateWord, steps, tools, materials, notices, durationS}
 *   state＝'running'|'answering'|'done'（缺省按 turn.runStatus 推：running→running，其余 done）
 */
export function summarizePipeline(turn) {
  const t = turn || {}
  const state = t.phase ?? (t.runStatus === 'running' ? 'running' : 'done')
  const stateWord = state === 'running' ? '执行中' : state === 'answering' ? '作答中' : '执行完成'
  return {
    state,
    stateWord,
    steps: (t.steps || []).length,
    tools: (t.tools || []).length,
    materials: (t.materials || []).length,
    notices: (t.notices || []).length,
    durationS: t.durationS ?? null
  }
}
