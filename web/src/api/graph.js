/**
 * api/graph —— B5 关系图谱·真 API 接口层（P1-05）。
 *
 * 与原型树 mock（数据内嵌 pages/B5.jsx）不同：本层只做「wire 形状 → 页面视图
 * 形状」映射，不持有业务数据。后端响应 snake_case（app/api/graph.py 实况），
 * 本层统一折回 camel；`from` 为合同字段名（Python 保留字由后端 alias 承载）。
 *
 * 合同：teach-petro-agent/specs/api/B5-关系图谱.md v0.2（端点 1–4＋LLM 起草
 * 实施端点——差异登记见 tickets/phase1/README.md P1-05）。
 */

import { get, post, put } from './client.js'

// ── wire(snake) → 视图(camel) ──

function nodeToCamel(n) {
  return { id: n.id, label: n.label, type: n.type, short: n.short, sub: n.sub }
}

/** 边折回：合同字段名 `from` → 视图 from；key＝`from|rel|to`（合同冻结）。 */
function edgeToCamel(e) {
  const from = e.from ?? e.from_ ?? ''
  return {
    key: e.key || `${from}|${e.rel}|${e.to}`,
    from,
    rel: e.rel,
    to: e.to,
    note: e.note,
    evidenceChunkId: e.evidence_chunk_id || '',
    reportId: e.report_id || ''
  }
}

function blockedToCamel(b) {
  const from = b.from ?? b.from_ ?? ''
  return {
    key: b.key,
    from,
    fromType: b.from_type,
    rel: b.rel,
    to: b.to,
    toType: b.to_type,
    reasonCode: b.reason_code,
    reason: b.reason,
    reportId: b.report_id,
    reportTitle: b.report_title,
    chunkId: b.chunk_id,
    blockedAt: b.blocked_at
  }
}

function configToCamel(d) {
  return {
    libId: d.lib_id,
    libName: d.lib_name,
    entityTypes: d.entity_types || [],
    relationTags: (d.relation_tags || []).map(t => ({
      rel: t.rel, example: t.example || '', desc: t.desc || ''
    })),
    fewShotExamples: (d.few_shot_examples || []).map(p => ({
      sentence: p.sentence || '', triple: p.triple || ''
    })),
    customInstructions: d.custom_instructions || '',
    savedAt: d.saved_at,
    savedBy: d.saved_by
  }
}

// ── 端点 1：GET /graph/net 整图读（整图一次给——高亮/隐显/邻接过滤全前端本地） ──

/**
 * @param {string} libId 库号（合同必传）
 * @returns {Promise<{libId: string, libName: string, nodes: any[], edges: any[],
 *   legend: {type: string, count: number}[], stats: {nodes: number, edges: number}}>}
 */
export async function getGraphNet(libId) {
  const d = await get('/graph/net', { lib_id: libId })
  return {
    libId: d.lib_id,
    libName: d.lib_name,
    nodes: (d.nodes || []).map(nodeToCamel),
    edges: (d.edges || []).map(edgeToCamel),
    legend: d.legend || [],
    stats: d.stats || { nodes: 0, edges: 0 }
  }
}

// ── 端点 2：GET /graph/extract-config 抽取设置读 ──

/** @param {string} libId */
export async function getExtractConfig(libId) {
  return configToCamel(await get('/graph/extract-config', { lib_id: libId }))
}

// ── 端点 3：PUT /graph/extract-config 保存（对号强校不过 400 带对号明细） ──

/**
 * @param {string} libId
 * @param {{entityTypes: string[], relationTags: {rel: string, example: string,
 *   desc: string}[], fewShotExamples?: {sentence: string, triple: string}[],
 *   customInstructions: string}} cfg 视图形状（本层折回 wire snake）
 * @returns {Promise<{libId: string, savedAt: string, savedBy: string, hint: string}>}
 */
export async function saveExtractConfig(libId, cfg) {
  const d = await put('/graph/extract-config', {
    lib_id: libId,
    entity_types: cfg.entityTypes,
    relation_tags: cfg.relationTags,
    few_shot_examples: cfg.fewShotExamples || [],
    custom_instructions: cfg.customInstructions
  })
  return { libId: d.lib_id, savedAt: d.saved_at, savedBy: d.saved_by, hint: d.hint }
}

// ── LLM 起草示例（实施端点——三源辅助③，起草走 gateway.complete） ──

/**
 * @param {string} libId
 * @param {{rel: string, sentence?: string}} p 带 sentence＝为报告原句预填三元组
 * @returns {Promise<{sentence: string, triple: string}>}
 */
export async function draftExample(libId, p) {
  const d = await post('/graph/extract-config/draft-example', {
    lib_id: libId, rel: p.rel, sentence: p.sentence ?? null
  })
  return { sentence: d.sentence, triple: d.triple }
}

// ── 端点 4：GET /graph/blocked-edges 被拦边清单（只读——治理/E3 消费，页面不加 UI） ──

/** @param {string} libId */
export async function listBlockedEdges(libId) {
  const d = await get('/graph/blocked-edges', { lib_id: libId })
  return {
    libId: d.lib_id,
    libName: d.lib_name,
    blockedEdges: (d.blocked_edges || []).map(blockedToCamel),
    stats: d.stats || { blocked: 0 }
  }
}
