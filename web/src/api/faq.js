/**
 * api/faq —— B3 常见问题库·真 API 接口层（P1-06）。
 *
 * 合同：teach-petro-agent/specs/api/B3-常见问题库.md v0.2（端点 1–17）。
 * 与 api/kb.js 同纪律：本层只做「wire 形（snake_case）→ 页面视图形（camel）」
 * 映射，不持有业务数据；全部走 api/client（X-Dev-User 注入/错误包解包）。
 *
 * 端点注记：
 * - 端点 3 新增入库恒先进「待审核」（v0.2 审核流）——发布走端点 17；
 * - 端点 4 重复校验非阻断（hit/hint 直出，命中与否都 200）；
 * - 端点 10 扫库受理 202（fetch 不抛），轮询走 useTaskPolling（/faq/scan-tasks）；
 * - 端点 15 导入＝raw body 上传件＋query 参数（mode/dry_run/filename——
 *   合同「传输形态结合实际框架定」落点，见 app/api/faq.py 同名注记）；
 * - 端点 16 导出返回预签名直链，页面直接交给浏览器下载（不经平台转发）。
 */

import { API_BASE, del, get, post, useTaskPolling } from './client.js'

// ── wire(snake) → 视图(camel) ──

function hookToCamel(h) {
  return h ? { kind: h.kind, name: h.name } : null
}

function compareToCamel(cmp) {
  if (!cmp) return null
  return {
    verdict: cmp.verdict,
    dupQuestion: cmp.dup_question || null,
    similarity: cmp.similarity ?? null,
    ontoHit: cmp.onto_hit || null,
    hint: cmp.hint || ''
  }
}

/** 端点 9 行/比对结论共用的折回。 */
export function mapCandidate(d) {
  return {
    id: d.id,
    question: d.question,
    variants: d.variants || [],
    freq: d.freq,
    window: d.window,
    status: d.status,
    compare: compareToCamel(d.compare),
    draft: d.draft || null,
    hook: hookToCamel(d.hook)
  }
}

// ── 端点 1/2：问答清单 · 详情 ──

/**
 * 端点 1：GET /api/faq/items —— 问答清单（状态筛 all|serve|pending|neg|disabled
 * ＋关键词搜问题/答案/相似问法；创建时间正序）。
 * @param {{status?: string, keyword?: string}} [q]
 */
export async function getItems(q = {}) {
  const d = await get('/faq/items', {
    status: q.status || 'all',
    keyword: q.keyword || ''
  })
  const items = Array.isArray(d.items) ? d.items : []
  return {
    items: items.map(r => ({
      id: r.id,
      question: r.question,
      answer: r.answer,
      similarQuestions: r.similar_questions || [],
      status: r.status,
      hook: hookToCamel(r.hook)
    })),
    total: d.total ?? items.length,
    grandTotal: d.grand_total ?? items.length
  }
}

/** 端点 2：GET /api/faq/items/{id} —— 详情（相似问含 id 寻址键＋维护人/版本）。 */
export async function getItemDetail(id) {
  const d = await get(`/faq/items/${encodeURIComponent(id)}`)
  return {
    id: d.id,
    question: d.question,
    answer: d.answer,
    status: d.status,
    hook: hookToCamel(d.hook),
    similarQuestions: (d.similar_questions || []).map(s => ({ id: s.id, text: s.text })),
    maintainer: d.maintainer,
    updatedAt: d.updated_at,
    version: d.version
  }
}

// ── 端点 3/4/17：新增 · 重复校验 · 审核发布 ──

/**
 * 端点 3：POST /api/faq/items —— 新增问答（负例登记/空值占位/关联口径/候选回写）。
 * 恒先进「待审核」；candidate 随行＝回写锚登记（发布事务内落 published）。
 * @param {{question?: string, answer?: string, isNegative?: boolean,
 *          hook?: {kind: string, name: string} | null, sourceCandidateId?: string | null}} body
 */
export function createEntry(body) {
  return post('/faq/items', {
    question: body.question || '',
    answer: body.answer || '',
    is_negative: Boolean(body.isNegative),
    hook: body.hook ? { kind: body.hook.kind, name: body.hook.name } : null,
    source_candidate_id: body.sourceCandidateId || null
  })
}

/** 端点 4：POST /api/faq/dup-checks —— 入库前重复校验（非阻断警告）。 */
export async function dupCheck(question) {
  const d = await post('/faq/dup-checks', { question })
  return {
    hit: d.hit ? { id: d.hit.id, question: d.hit.question } : null,
    hint: d.hint || null
  }
}

/** 端点 17：POST /api/faq/items/{id}/review —— 审核发布/驳回（v0.2 增设）。 */
export function reviewEntry(id, action) {
  return post(`/faq/items/${encodeURIComponent(id)}/review`, { action })
}

// ── 端点 5/6/7/8：相似问增删 · 合并 · 停用启用 ──

/** 端点 5：POST /api/faq/items/{id}/similar-questions —— 添加相似问法。 */
export function addSimilar(entryId, text) {
  return post(`/faq/items/${encodeURIComponent(entryId)}/similar-questions`, { text })
}

/** 端点 6：DELETE /api/faq/items/{id}/similar-questions/{simId} —— 删除相似问法。 */
export function removeSimilar(entryId, simId) {
  return del(
    `/faq/items/${encodeURIComponent(entryId)}/similar-questions/${encodeURIComponent(simId)}`
  )
}

/** 端点 7：POST /api/faq/items/{id}/merge —— 合并相似问（path id＝被并入方）。 */
export function mergeEntry(entryId, targetId) {
  return post(`/faq/items/${encodeURIComponent(entryId)}/merge`, { target_id: targetId })
}

/** 端点 8：POST /api/faq/items/{id}/state —— 停用/启用（disable|enable）。 */
export function toggleState(entryId, action) {
  return post(`/faq/items/${encodeURIComponent(entryId)}/state`, { action })
}

// ── 端点 9/10/11/12/13：候选库 · 扫库 · 比对 · 起草 ──

/**
 * 端点 9：GET /api/faq/candidates —— 候选问题库（状态筛＋扫库态随行；频次倒序）。
 * @param {{status?: string}} [q]
 */
export async function getCandidates(q = {}) {
  const d = await get('/faq/candidates', { status: q.status || 'all' })
  const items = Array.isArray(d.items) ? d.items : []
  return {
    items: items.map(mapCandidate),
    total: d.total ?? items.length,
    scan: {
      runningTaskId: d.scan?.running_task_id || null,
      lastHint: d.scan?.last_hint || null
    }
  }
}

/** 端点 10：POST /api/faq/scan-tasks —— 扫库受理（202＋任务号；重入 409）。 */
export function startScan() {
  return post('/faq/scan-tasks')
}

/** 端点 11 轮询 hook（client.useTaskPolling 薄壳——路径缺省 /faq/scan-tasks）。 */
export function useFaqScanPolling(taskId, opts = {}) {
  const { intervalMs = 800, onProgress } = opts
  return useTaskPolling(taskId, { path: '/faq/scan-tasks', intervalMs, onProgress })
}

/** 端点 12：POST /api/faq/candidates/{id}/compare —— 向量比对（三面去重）。 */
export async function compareCandidate(id) {
  const d = await post(`/faq/candidates/${encodeURIComponent(id)}/compare`)
  return { id: d.id, status: d.status, compare: compareToCamel(d.compare) }
}

/** 端点 13：POST /api/faq/candidates/{id}/draft —— 候选 LLM 起草（溯源后缀）。 */
export async function draftCandidate(id) {
  const d = await post(`/faq/candidates/${encodeURIComponent(id)}/draft`)
  return {
    id: d.id,
    status: d.status,
    draft: d.draft,
    hookSuggestion: hookToCamel(d.hook_suggestion)
  }
}

// ── 端点 14：引用知识起草 ──

/**
 * 端点 14：POST /api/faq/drafts —— 引用知识起草（台账口径/切片原文两选可组合；
 * 服务端直取台账/片段原文——不信任前端文本）。
 * @param {{ledgerRef?: {kind: string, id: number} | null,
 *          sliceRef?: {reportId: string, fragmentId: string} | null}} body
 */
export function draftFromRefs(body) {
  return post('/faq/drafts', {
    ledger_ref: body.ledgerRef ? { kind: body.ledgerRef.kind, id: body.ledgerRef.id } : null,
    slice_ref: body.sliceRef
      ? { report_id: body.sliceRef.reportId, fragment_id: body.sliceRef.fragmentId }
      : null
  })
}

// ── 端点 15/16：导入 · 导出 ──

/**
 * 端点 15：POST /api/faq/import —— 批量导入（append/replace＋试校验＋四计数）。
 * 上传件走 raw body、参数走 query（传输形态合同悬置落点——见模块注记）；
 * 走原生 fetch 绕开 client 的 JSON 封装（错误包解包保留）。
 * @param {{mode: 'append' | 'replace', dryRun: boolean, filename: string, file: File}}
 * @returns {Promise<any>} { dryRun, added, merged, skipped, failed, failures, hint }
 */
export async function importLibrary({ mode, dryRun, filename, file }) {
  const bytes = await file.arrayBuffer()
  const query = new URLSearchParams({
    mode,
    dry_run: String(Boolean(dryRun)),
    filename
  })
  const res = await fetch(`${API_BASE}/faq/import?${query.toString()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/octet-stream' },
    body: bytes
  })
  const text = await res.text()
  let data = null
  if (text) { try { data = JSON.parse(text) } catch { data = null } }
  if (!res.ok) {
    const pkg = data || {}
    const err = new Error(pkg.message || `导入失败（HTTP ${res.status}）`)
    err.code = pkg.code || ''
    err.status = res.status
    throw err
  }
  return {
    dryRun: data.dry_run,
    added: data.added,
    merged: data.merged,
    skipped: data.skipped,
    failed: data.failed,
    failures: (data.failures || []).map(f => ({ row: f.row, reason: f.reason })),
    hint: data.hint || ''
  }
}

/** 端点 16：POST /api/faq/export —— 导出全库（预签名直链＋模板列对称）。 */
export async function exportLibrary() {
  const d = await post('/faq/export')
  return {
    downloadUrl: d.download_url,
    expiresAt: d.expires_at,
    columns: d.columns || [],
    hint: d.hint || ''
  }
}

// ── 跨页锚点：下拉数据源（C1 台账读端点/B2 片段扁平清单——票 93 同源纪律） ──

/**
 * 台账口径/关联口径选项（C1 端点 2/3 读面——同源投影，不建第二份拷贝）。
 * @returns {Promise<{ledgerOptions: {value: string, label: string, ref: any}[],
 *                    hookOptions: {value: string, label: string}[]}>}
 */
export async function listLedgerOptions() {
  const [metrics, terms] = await Promise.all([
    get('/semantics/metrics', { pageSize: 500 }),
    get('/semantics/terms', { pageSize: 500 })
  ])
  const metricRows = Array.isArray(metrics.items) ? metrics.items : []
  const termRows = Array.isArray(terms.items) ? terms.items : []
  const ledgerOptions = [
    ...metricRows.map(m => ({
      value: `m${m.id}`,
      label: `指标卡 · ${m.slot_name || m.name}`,
      ref: { kind: 'metric', id: m.id, name: m.slot_name || m.name }
    })),
    ...termRows.map(t => ({
      value: `t${t.id}`,
      label: `术语 · ${t.term}`,
      ref: { kind: 'term', id: t.id, name: t.term }
    }))
  ]
  const hookOptions = [
    { value: '', label: '不挂接', kind: null },
    ...metricRows.map(m => ({ value: m.slot_name || m.name, label: `指标 · ${m.slot_name || m.name}`, kind: 'metric' })),
    ...termRows.map(t => ({ value: t.term, label: `术语 · ${t.term}`, kind: 'term' }))
  ]
  return { ledgerOptions, hookOptions }
}

/**
 * 切片原文选项（B2 端点 1 全库扁平清单读法——report_id 缺省＋分页必带）。
 * @returns {Promise<{value: string, label: string, reportId: string, fragmentId: string}[]>}
 */
export async function listSliceOptions() {
  const d = await get('/kb/fragments', { page: 1, pageSize: 500 })
  const items = Array.isArray(d.items) ? d.items : []
  return items.map(f => ({
    value: `${f.report_id}-${f.id}`,
    label: `${f.report}｜${f.type}｜${(f.hit || '').slice(0, 14)}…`,
    reportId: f.report_id,
    fragmentId: f.id
  }))
}
