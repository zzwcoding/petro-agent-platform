/**
 * events.js · 执行流水线纯逻辑（Owner 2026-10-17 串行链条模型）。
 *
 * 模型：每轮＝三段串行块——**用户输入块 → 系统执行流水线块（typed 事件流）→ 系统回答块**。
 * 本件只余两块纯面：**白话映射常量**（相位/工具/notice 三级——渲染件 ExecutionPipeline.jsx
 * 与 NoticeBand.jsx 消费）与**摘要行计数**（summarizePipeline）。零副作用、零请求——可直喂单测。
 *
 * 事件流真源＝归约器直出的 `turn.events`（按帧到达序追加，specs/frontend-redesign.md G4；
 * FE-02 起本件不再派生显示序——原 deriveEvents 已退役删除，其「显示口径」排序规则随
 * reducer events 到达序取而代之，事件元素形状消费真源＝ExecutionPipeline.jsx）。
 */
import { phaseOf } from '../a1v2Reducer.js'

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

/** C 级 notice type → 归属相位（未登记＝无相位归属）。 */
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

/**
 * 流水线摘要行计数（折叠态一行）。
 * @returns {state, stateWord, steps, tools, materials, notices, durationS}
 *   state＝'running'|'answering'|'done'——渲染期 phaseOf(t) 派生（FE-02 按票面把原
 *   `t.phase ?? …` 字面替换为 `phaseOf(t)`；phaseOf 恒有值，turn 形下 runStatus 兜底分支
 *   不可达，仅按字面保留）。
 */
export function summarizePipeline(turn) {
  const t = turn || {}
  const state = phaseOf(t) ?? (t.runStatus === 'running' ? 'running' : 'done')
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
