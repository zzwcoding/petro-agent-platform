/**
 * api/wells —— A2 井档案·真 API 接口层（W-A2 接线批 2/3）。
 *
 * 与内嵌种子原型（pages/A2.jsx WELLS 常量＋data/changeTickets.jsx 变动单——
 * 本批在页面侧退役）不同：本层只做「wire 形状 → 页面视图形状」映射，不持有
 * 业务数据（api/graph.js 先例同构）。后端响应 snake_case（app/api/wells.py
 * 实况——M-02 交付），本层折回 camel；检修行 `date_end` 仅检修 kind 携带
 * （合同端点 3——措施/状态变更行无该键），折回后 dateEnd 键缺省同形。
 *
 * 合同：teach-petro-agent/specs/api/A2-井档案.md v0.2（四端点＋合同常量表；
 * 「纪录」合并与排序、五页签计数、变动投影过滤全部服务端完成——前端零编排
 * 零拼算，pages/A2.jsx 的 buildEvents 前端合并整体退役）。
 */

import { get } from './client.js'

// ── wire(snake) → 视图(camel) ──

function summaryToView(r) {
  return {
    wellId: r.well_id,
    wellName: r.well_name,
    wellKind: r.well_kind,
    wellKindCode: r.well_kind_code,
    blockName: r.block_name,
    currentStatus: r.current_status,
    remark: r.remark
  }
}

function profileToView(r) {
  return {
    wellId: r.well_id,
    wellName: r.well_name, // 空缺以 null 返回——页面渲染「—」（合同端点 1/2 注记）
    // 井别展示拼装「采油（EW）」（合同端点 2——well_kind＋well_kind_code
    // 服务端分携、前端拼装；缺段如实跳过）
    kindLabel: [r.well_kind, r.well_kind_code ? `（${r.well_kind_code}）` : '']
      .filter(Boolean).join('') || null,
    firstProdDate: r.first_prod_date,
    platform: r.platform,
    blockName: r.block_name,
    currentStatus: r.current_status,
    remark: r.remark,
    qualityNotes: Array.isArray(r.quality_notes) ? r.quality_notes : [],
    footNote: r.foot_note
  }
}

function measureToView(m) {
  return { key: m.key, date: m.date, type: m.type, content: m.content, result: m.result }
}

function deviceToView(d) {
  // 真 DTO 无 ok 布尔（种子形状退役）——状态 Tag 色由页面按 status 映射（R-WIRE A2-8）
  return { key: d.key, type: d.type, status: d.status, since: d.since, note: d.note }
}

function overhaulToView(o) {
  // from/to → date_start/date_end 改名映射（R-WIRE A2-9——消费点＝检修页签起止列）
  return {
    key: o.key, dateStart: o.date_start, dateEnd: o.date_end,
    job: o.job, impact: o.impact, batch: o.batch
  }
}

function eventToView(e) {
  // 服务端已合并排序（buildEvents 前端编排整体退役——R-WIRE A2-10）；
  // date_end 仅检修行携带（app/api/wells.py 两响应体类型承载），折回同形
  return {
    key: e.key, kind: e.kind, date: e.date, dateEnd: e.date_end,
    title: e.title, outcome: e.outcome
  }
}

function chainToView(c) {
  return {
    wellId: c.well_id,
    counts: c.counts, // 五页签计数（changes＝端点 4 total 同源同值——页面零拼算）
    measureFoot: c.measure_foot,
    deviceFoot: c.device_foot,
    events: (c.events || []).map(eventToView),
    measures: (c.measures || []).map(measureToView),
    devices: (c.devices || []).map(deviceToView),
    overhauls: (c.overhauls || []).map(overhaulToView),
    tail: c.tail
  }
}

function ticketToView(t) {
  // status/plane 直接返回展示值（合同端点 4——本页零加工渲染徽标；
  // 机器状态码与状态机归 A3 主单合同）
  return { id: t.id, status: t.status, plane: t.plane, short: t.short, proposer: t.proposer, time: t.time }
}

// ── 展示层拼装（合同端点 1 注记——下拉 option 文案为前端展示层职责） ──

/**
 * 选井下拉 option 文案（「N-02 渤中28-1-N2（渤南 · 采油 · 生产中）」形）。
 * 末段取当前状态或备注属展示层选择（合同端点 1 注记：N-06 用备注、
 * N-02/N-11 用状态）——本层规则＝注水井（IW）末段取备注（注水配置信息量
 * 高于产量状态）、采油井取状态；备注缺省回退状态。well_name 空缺时不带
 * 名字段（档案明细处才按合同渲染「—」）。
 */
export function wellOptionLabel(w) {
  const nameSeg = w.wellName ? ` ${w.wellName}` : ''
  const last = (w.wellKindCode === 'IW' && w.remark) ? w.remark : (w.currentStatus || '—')
  const mid = [w.blockName, w.wellKind, last].filter(Boolean).join(' · ')
  return `${w.wellId}${nameSeg}（${mid}）`
}

// ── 端点（GET 四读——A2 页无任何变动单写操作端点，写端点全部归 A3） ──

/**
 * 端点 1：GET /wells 选井下拉列表（服务端按当前角色数据域过滤——无权限的井
 * 不在响应里，前端不做打码不做二次过滤；排序 well_id 升序；total＝过滤后计数）。
 */
export function listWells(opts = {}) {
  return get('/wells', undefined, opts).then(res => ({
    ...res,
    items: (res.items || []).map(summaryToView)
  }))
}

/** 端点 2：GET /wells/{well_id} 档案明细（8 字段＋红字质量备注＋卡底注记）。 */
export function getWellProfile(wellId, opts = {}) {
  return get(`/wells/${encodeURIComponent(wellId)}`, undefined, opts).then(profileToView)
}

/**
 * 端点 3：GET /wells/{well_id}/chain 关系链（纪录合并视图＋措施/设备/检修
 * 三台账＋五页签计数＋枚举尾注全文＋随井尾注——合并排序与计数拼装服务端
 * 完成，前端零编排；措施 content/result 空值如实透传，页面空值兜底渲染）。
 */
export function getWellChain(wellId, opts = {}) {
  return get(`/wells/${encodeURIComponent(wellId)}/chain`, undefined, opts).then(chainToView)
}

/**
 * 端点 4：GET /wells/{well_id}/change-tickets 变动页签只读投影（主单在 A3，
 * A2 无审批操作端点）。V1 端点壳恒 items=[] total=0（A3 主单未建——空态
 * 文案「本井暂无变动单」照合同渲染，不 mock 假单）。
 */
export function listWellChangeTickets(wellId, opts = {}) {
  return get(`/wells/${encodeURIComponent(wellId)}/change-tickets`, undefined, opts).then(res => ({
    wellId: res.well_id,
    items: (res.items || []).map(ticketToView),
    total: res.total
  }))
}
