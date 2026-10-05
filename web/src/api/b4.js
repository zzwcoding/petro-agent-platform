/**
 * api/b4 —— B4 报告百科·真 API 接口层（W-B4 接线批 3/3）。
 *
 * 与内嵌种子原型（pages/B4.jsx 的 PAGES/EVIDENCE/CLAIMS/GLOSSARY/正文快照
 * 常量——本批在页面侧退役）不同：本层只做「wire 形状 → 页面视图形状」映射，
 * 不持有业务数据（api/wells.js 先例同构）。后端响应 snake_case（app/api/wiki.py
 * 实况——P2-04 交付），本层折回 camel。
 *
 * 合同：teach-petro-agent/specs/api/B4-报告百科.md v0.4（两读端点——版本族
 * 已撤、恒当前版；纯读零写操作）。status 两态由服务端按当前版正文 [[flag:]]
 * 有无判定直返（行为规则 5 服务端组装——前端零拼装业务文案）。
 */

import { get } from './client.js'
import { getFragmentContext, listFragments } from './kb.js'

// ── wire(snake) → 视图(camel) ──

function sourceReportToView(s) {
  return { id: s?.id ?? null, doc: s?.doc ?? null }
}

function listItemToView(r) {
  return {
    id: r.id,
    title: r.title,
    lib: r.lib,
    sourceReport: sourceReportToView(r.source_report),
    currentVersion: r.current_version,
    updated: r.updated,
    status: r.status
  }
}

function relatedObjectToView(o) {
  return {
    type: o.type, id: o.id, summary: o.summary,
    links: Array.isArray(o.links) ? o.links : []
  }
}

function claimToView(c) {
  return {
    claimId: c.claim_id,
    text: c.text,
    evidenceChunkIds: Array.isArray(c.evidence_chunk_ids) ? c.evidence_chunk_ids : []
  }
}

function glossaryTermToView(g) {
  return { word: g.word, kind: g.kind, refId: g.ref_id, card: g.card || {} }
}

function detailToView(d) {
  return {
    id: d.id,
    title: d.title,
    lib: d.lib,
    slug: d.slug,
    digest: d.digest,
    sourceReport: sourceReportToView(d.source_report),
    currentVersion: d.current_version,
    updated: d.updated,
    status: d.status,
    generationSource: d.generation_source,
    operator: d.operator,
    relatedObjects: (d.related_objects || []).map(relatedObjectToView),
    content: d.content,
    claims: (d.claims || []).map(claimToView),
    glossaryTerms: (d.glossary_terms || []).map(glossaryTermToView)
  }
}

// ── 端点（v0.4 两读——端点 3/4 版本族随 v0.4 撤除，无回滚/无 ?version=） ──

/**
 * 端点 1：GET /wiki/pages 百科页目录（lib/keyword 服务端筛选——keyword 冻结
 * 匹配题名/来源报告/所属库三字段；按 updated 倒序；total＝全量计数——
 * 「筛选结果 X / Y 条」＝items.length＋total 拼，前端零二次计数）。
 * @param {{lib?: string, keyword?: string}} [q]
 */
export function listWikiPages(q = {}) {
  const query = { lib: q.lib || 'all', keyword: (q.keyword || '').trim() }
  return get('/wiki/pages', query).then(res => ({
    items: (res.items || []).map(listItemToView),
    total: res.total ?? (res.items || []).length
  }))
}

/**
 * 端点 2：GET /wiki/pages/{pageId} 百科页全文（元数据字段表＋自由 markdown
 * 正文 content＋claims[]＋glossary_terms[]＋related_objects[]；恒当前版
 * 快照——v0.4 撤 ?version=N）。404 wiki_not_found（含 wiki 开关关未生成）。
 */
export function getWikiPage(pageId, opts = {}) {
  return get(`/wiki/pages/${encodeURIComponent(pageId)}`, undefined, opts).then(detailToView)
}

// ── 证据弹层懒加载（mock 更正清单⑨：证据条目细节 report/section/type/text
//    不在 B4 端点 2——展开时懒加载 B2 端点 1/2 只读投影，kb.js 复用件） ──

/**
 * 论断证据切片懒加载：按百科页来源报告整组拉片段台账（kb.listFragments 的
 * reportId 读法），过滤出该论断的锚切片，再逐条父块回捞原文（kb.
 * getFragmentContext）。fail-closed：锚切片不在台账（chunk 重建后 id 失效）
 * 即丢弃——不伪造回链（B4 错误码草案 fail-closed 行）；无锚论断（空
 * chunkIds）零请求直接返回空数组。
 * @param {string} sourceReportId 百科页来源报告 id（detail.sourceReport.id）
 * @param {string[]} chunkIds 论断锚切片 id 列表（claims[].evidenceChunkIds）
 * @returns {Promise<Array<{id: string, report: string, section: string | null,
 *   type: string, text: string}>>}
 */
export async function loadClaimEvidence(sourceReportId, chunkIds) {
  if (!chunkIds || !chunkIds.length) return []
  const ids = [...new Set(chunkIds)] // 锚 id 去重（W-B4.rev F4）——同 claim 重复锚不重复回捞/不重复渲染
  const lib = await listFragments({ reportId: sourceReportId })
  const index = new Map(lib.items.map(f => [f.id, f]))
  const metas = ids.map(id => index.get(id)).filter(Boolean)
  return Promise.all(metas.map(async m => {
    const ctx = await getFragmentContext(m.id)
    return { id: m.id, report: m.report, section: m.section, type: m.type, text: ctx.context }
  }))
}

// ── 台账挂接 chip 展示映射（R-WIRE B4-10：card→展示字段映射函数；
//    卡＝C1 端点 2/3 行同形的生成时固化投影——服务端直取不建仓） ──

const GLOSSARY_KIND_LABEL = { metric: '指标口径', term: '业务术语' }
const GLOSSARY_LEDGER = { metric: '指标台账', term: '术语台账' }
// 状态值来自 C1 台账（生效中/有效/有效（待联席裁决）…）——色映射照页面
// 种子同值；未知值兜底 default（不发明第三色）。
const GLOSSARY_STATUS_COLOR = { 生效中: 'green', 有效: 'green', '有效（待联席裁决）': 'orange' }

/**
 * glossary_terms 行 → chip 弹层展示视图：kind 折展示名、ref 拼「台账 #N」、
 * extra 按族组装（指标＝统计粒度/单位、术语＝有效期——后端 term 卡暂无
 * expires_display 键时如实留空）、状态数组（指标）折串。
 * @param {{word: string, kind: string, refId: number, card: Record<string, unknown>}} g
 */
export function glossaryChipView(g) {
  const card = g.card || {}
  const isMetric = g.kind === 'metric'
  const status = isMetric
    ? (Array.isArray(card.status) ? card.status.join('、') : (card.status ?? ''))
    : (card.status ?? '')
  const extraParts = isMetric
    ? [card.grain ? `统计粒度：${card.grain}` : '', card.unit ? `单位 ${card.unit}` : '']
    : [card.expires_display ? `有效期至 ${card.expires_display}` : '']
  return {
    word: g.word,
    kindLabel: GLOSSARY_KIND_LABEL[g.kind] || '台账词条',
    def: card.def ?? null,
    status,
    statusColor: GLOSSARY_STATUS_COLOR[status] || 'default',
    owner: card.owner ?? null,
    extra: extraParts.filter(Boolean).join(' · '),
    ref: `${GLOSSARY_LEDGER[g.kind] || '台账'} #${g.refId}`,
    source: card.source ?? null
  }
}
