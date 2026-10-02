/**
 * api/kb —— B1 报告库·真 API 接口层（P1-03）。
 *
 * 与原型树 mock（数据内嵌 pages/B1.jsx）不同：本层只做「wire 形状 → 页面视图
 * 形状」映射，不持有业务数据。后端 R1 裁决响应统一 snake_case（app/api/kb.py
 * 实况——P1-02a/P1-02b 已真实现 15 端点），本层统一折回 camel，页面列定义与
 * 原型同形（api/gateway.js 先例同构）。
 *
 * 职责边界：
 * - 全部走 api/client（X-Dev-User 注入/错误包解包/分页信封归一化在底座）；
 * - 直传两拍的第一拍受理（POST /kb/uploads）与第二拍 confirm 是两个契约函数；
 *   **文件字节 PUT 直传对象存储不绕平台**（F5 presigned PUT）——走 raw fetch
 *   （凭证 URL 指向 MinIO，非 /api 同源路径，client 的 JSON 封装不适用），
 *   见 putObjectDirect；
 * - 轮询 hook 直连 client 拿 wire 形——页面用 mapTaskSnapshot 统一折 camel
 *   （与 getTask 出口同形，gateway mapDrillSnapshot 先例）。
 *
 * 合同：teach-petro-agent/specs/api/B1-报告库.md v0.3（端点 1–15）。
 */

import { get, post, put, useTaskPolling } from './client.js'

/** 业务模板四枚举（B1 v0.3 建库批冻结——建库弹窗下拉与建议卡共用）。 */
export const BIZ_TEMPLATES = [
  { value: 'completion', label: '完井报告类' },
  { value: 'monthly', label: '生产月报类' },
  { value: 'dynamic', label: '动态分析类' },
  { value: 'blank', label: '空白默认' }
]

/** 任务来源三值（B1 v0.2 冻结值域——来源列/筛参消费面）。 */
export const TASK_SOURCES = ['上传入库', '片段修正', '重跑定型']

// ── wire(snake) → 视图(camel) ──

// ── B1 任务轮询：底座 client.pollTaskUntilDone 已改认 `status ?? state` 终态
// 字段（P1-03 收尾裁决——P1-04 落地），本层重复适配版退役，useKbTaskPolling
// 退化为带 /kb/tasks 路径缺省的薄壳（B1 页调用点零改动）。──

/**
 * useKbTaskPolling —— B1/B2 任务轮询 hook（client.useTaskPolling 薄壳：
 * path 缺省 /kb/tasks；瞬时失败容忍/AbortError 直通/onProgress 保护全同底座）。
 *
 * @param {string | null} taskId 任务号；null/空串不轮询
 * @param {{intervalMs?: number, onProgress?: (snap: any) => void}} opts
 *   onProgress 每次成功轮询（含进行中快照）回调一次（wire 形，回调方自行折 camel）
 * @returns {{status: 'idle'|'polling'|'done'|'failed', data: any, error: Error | null}}
 */
export function useKbTaskPolling(taskId, opts = {}) {
  const { intervalMs = 1500, onProgress } = opts
  return useTaskPolling(taskId, { path: '/kb/tasks', intervalMs, onProgress })
}

/** 任务行/轮询快照共用的 camel 折回（stop_at＝权威停止点；current_step 0–4）。 */
function taskToCamel(t) {
  return {
    id: t.id,
    doc: t.doc,
    libId: t.lib_id,
    libName: t.lib_name,
    source: t.source,
    state: t.state,
    currentStep: t.current_step,
    stopAt: t.stop_at || null,
    reason: t.reason || null,
    nodes: (t.nodes || []).map(n => ({ key: n.key, label: n.label, state: n.state, note: n.note || null })),
    configSnapshot: t.config_snapshot
      ? {
          semantic: Boolean(t.config_snapshot.semantic),
          keyword: Boolean(t.config_snapshot.keyword),
          wiki: Boolean(t.config_snapshot.wiki),
          graph: Boolean(t.config_snapshot.graph),
          mode: t.config_snapshot.mode,
          addSummary: Boolean(t.config_snapshot.add_summary),
          addQuestions: Boolean(t.config_snapshot.add_questions)
        }
      : null
  }
}

function fragmentToCamel(f) {
  return {
    id: f.id,
    type: f.type,
    path: f.path,
    text: f.text,
    version: f.version,
    versions: (f.versions || []).map(v => ({ v: v.v, text: v.text, note: v.note }))
  }
}

/** F62 库活动行折回（端点 4/13/15 共用——P1-11c 折回收口）。 */
function activityRowToCamel(r) {
  return r ? { time: r.time, who: r.who, action: r.action, target: r.target } : null
}

/** 质检复核单行折回（B2 端点 3/4/5 共用——P1-11c 折回收口）。 */
function issueReportToCamel(d) {
  return {
    id: d.id,
    fragmentId: d.fragment_id,
    reportId: d.report_id,
    fragmentLabel: d.fragment_label,
    state: d.state,
    markedBy: d.marked_by,
    markedAt: d.marked_at,
    rejectReason: d.reject_reason || null,
    hint: d.hint || null
  }
}

/**
 * 轮询快照映射（useTaskPolling 直连 client 拿 wire 形——页面用本函数统一折
 * camel，与 getTask/retryTask 出口同形）。
 * @param {any} d GET /kb/tasks/{id} 响应
 */
export function mapTaskSnapshot(d) {
  return taskToCamel(d)
}

// ── 端点 1/2/3/4：报告台账 · 详情 · 下载直链 · 片段修正 ──

/**
 * 端点 1：GET /api/kb/reports —— 报告台账（服务端筛选：所属库＋关键词；
 * 「入库中」状态标由 status 直出——v0.2 裁决）。
 * @param {{lib?: string, keyword?: string}} [q]
 */
export async function getReports(q = {}) {
  const d = await get('/kb/reports', { lib: q.lib || 'all', keyword: q.keyword || '' })
  const items = Array.isArray(d.items) ? d.items : []
  return {
    items: items.map(r => ({
      id: r.id, doc: r.doc, libId: r.lib_id, lib: r.lib,
      refs: r.refs, wiki: r.wiki, status: r.status
    })),
    total: d.total ?? items.length
  }
}

/** 端点 2：GET /api/kb/reports/{id} —— 详情（片段预览含版本——F30 恒有 v1）。 */
export async function getReportDetail(id) {
  const d = await get(`/kb/reports/${encodeURIComponent(id)}`)
  return {
    id: d.id, doc: d.doc, libId: d.lib_id, lib: d.lib,
    subject: d.subject || null, refs: d.refs, wiki: d.wiki, status: d.status,
    relatedObjects: d.related_objects || [],
    fragments: (d.fragments || []).map(fragmentToCamel)
  }
}

/**
 * 端点 3：POST /api/kb/reports/{id}/download-url —— 下载原件直链（预签名
 * GET，小时级有效；返回的 downloadUrl 直接交给浏览器下载，不走平台转发）。
 */
export async function getDownloadUrl(id) {
  const d = await post(`/kb/reports/${encodeURIComponent(id)}/download-url`)
  return { id: d.id, downloadUrl: d.download_url, expiresAt: d.expires_at, ttl: d.ttl }
}

/**
 * 端点 4：POST /api/kb/reports/{id}/fragments/{fragId}/revisions —— 片段人工
 * 修正（乐观锁：base_version 落后 409 kb_fragment_version_conflict；空文本
 * 400；重建折算「片段修正」任务——taskId 携回供任务页签可见）。
 * @param {string} reportId
 * @param {string} fragId
 * @param {{baseVersion: number, text: string}} p
 */
export async function reviseFragment(reportId, fragId, p) {
  const d = await post(
    `/kb/reports/${encodeURIComponent(reportId)}/fragments/${encodeURIComponent(fragId)}/revisions`,
    { base_version: p.baseVersion, text: p.text }
  )
  return {
    id: d.id,
    version: d.version,
    versions: (d.versions || []).map(v => ({ v: v.v, text: v.text, note: v.note })),
    rebuild: { triggered: Boolean(d.rebuild?.triggered), hint: d.rebuild?.hint || '' },
    activityRow: activityRowToCamel(d.activity_row),
    taskId: d.task_id || null
  }
}

// ── 端点 5/6：直传两拍（受理→PUT 直传→confirm 定型） ──

/**
 * 端点 5：POST /api/kb/uploads —— 直传受理（两拍第一拍）。
 * lib_id 缺省＝走入库路由（LLM＋本体话题分析——LLM 只建议、人确认后执行）；
 * 建议随响应 routing 携回（mode existing|new|null＋理由＋置信度＋模板推荐）。
 * dup_warning 非阻断提示；停用库 400 带码（kb_lib_disabled）。
 * @param {{filename: string, size: number, libId?: string, suggestedTopic?: string}} p
 */
export async function initUpload(p) {
  const d = await post('/kb/uploads', {
    filename: p.filename,
    size: p.size,
    lib_id: p.libId || null,
    suggested_topic: p.suggestedTopic || null
  })
  return {
    uploadId: d.upload_id,
    libId: d.lib_id || null,
    libName: d.lib_name || null,
    dupWarning: d.dup_warning || null,
    putUrl: d.put_url,
    expiresAt: d.expires_at,
    bucket: d.bucket,
    routing: d.routing
      ? {
          mode: d.routing.mode || null,
          topic: d.routing.topic || null,
          libId: d.routing.lib_id || null,
          libName: d.routing.lib_name || null,
          template: d.routing.template || null,
          reason: d.routing.reason || null,
          confidence: typeof d.routing.confidence === 'number' ? d.routing.confidence : null
        }
      : null
  }
}

/**
 * 直传第二拍前置：客户端 PUT 文件字节直达对象存储（F5 预签名直传——平台不经
 * 手文件字节；凭证 URL 指向 MinIO 非 /api，raw fetch 直传，凭证已用/过期由
 * 对象存储侧报错）。受理（initUpload）与 confirm（confirmUpload）走 client
 * 惯例，本函数只承载字节段。
 * @param {string} putUrl 预签名 PUT 凭证 URL（受理响应 put_url 原样）
 * @param {Blob | ArrayBuffer | string} body 文件字节（演示文本可直接传字符串）
 */
export async function putObjectDirect(putUrl, body) {
  const res = await fetch(putUrl, {
    method: 'PUT',
    body,
    headers: { 'Content-Type': 'application/octet-stream' }
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`直传对象存储失败（HTTP ${res.status}）${text ? `：${text.slice(0, 200)}` : ''}`)
  }
}

/**
 * 端点 6：POST /api/kb/uploads/{uploadId}/confirm —— 确认入库（核实落桶→
 * 建任务开跑，config_snapshot 定型）。可选体带 lib_id＝路由确认通道（人确认
 * 建议库/人工改选/新建库落点——P1-02a 收尾裁决采纳）；空体＝沿用受理已定库。
 * @param {string} uploadId
 * @param {{libId?: string}} [p]
 */
export async function confirmUpload(uploadId, p = {}) {
  const d = await post(
    `/kb/uploads/${encodeURIComponent(uploadId)}/confirm`,
    p.libId ? { lib_id: p.libId } : {}
  )
  return {
    taskId: d.task_id,
    uploadId: d.upload_id,
    doc: d.doc,
    libId: d.lib_id,
    libName: d.lib_name,
    source: d.source,
    state: d.state,
    currentStep: d.current_step,
    configSnapshot: d.config_snapshot
  }
}

// ── 端点 7/8/9/10：任务列表 · 轮询 · 产物 · 重试 ──

/**
 * 端点 7：GET /api/kb/tasks —— 入库任务列表（创建时间倒序；来源筛参——
 * v0.2 拍板；source 越界 400）。
 * @param {{source?: string}} [q]
 */
export async function listTasks(q = {}) {
  const d = await get('/kb/tasks', { source: q.source || 'all' })
  const items = Array.isArray(d.items) ? d.items : []
  return { items: items.map(taskToCamel), total: d.total ?? items.length }
}

/** 端点 8：GET /api/kb/tasks/{id} —— 轮询进度（五步节点＋服务端组装说明）。 */
export async function getTask(id) {
  const d = await get(`/kb/tasks/${encodeURIComponent(id)}`)
  return mapTaskSnapshot(d)
}

/**
 * 端点 9：GET /api/kb/tasks/{id}/additions —— 索引期加法产物（done 后可读，
 * 未 done 409；add_summary/add_questions=false 的卡为 null——按快照展示）。
 */
export async function getAdditions(id) {
  const d = await get(`/kb/tasks/${encodeURIComponent(id)}/additions`)
  return { taskId: d.task_id, doc: d.doc, summary: d.summary || null, questions: d.questions || null }
}

/**
 * 端点 10：POST /api/kb/tasks/{id}/retry —— 重试/重跑（stuck 内含停止；重跑
 * ＝按当前待生效配置重新定型；来源转「重跑定型」）。返回轮询形状快照。
 */
export async function retryTask(id) {
  const d = await post(`/kb/tasks/${encodeURIComponent(id)}/retry`)
  return mapTaskSnapshot(d)
}

// ── 端点 11/12/13/14/15：库列表 · 配置读写（含停用启用） · 活动流 · 建库 ──

/**
 * 端点 11：GET /api/kb/libs —— 库列表（last_ingestion＝最近一次入库所用开关
 * 快照——与待生效配置两态分离；图谱筛 graph=all|on|off）。
 * @param {{graph?: string, keyword?: string}} [q]
 */
export async function listLibraries(q = {}) {
  const d = await get('/kb/libs', { graph: q.graph || 'all', keyword: q.keyword || '' })
  const items = Array.isArray(d.items) ? d.items : []
  return {
    items: items.map(l => ({
      id: l.id,
      name: l.name,
      bizTemplate: l.biz_template,
      status: l.status,
      lastIngestion: l.last_ingestion
        ? { doc: l.last_ingestion.doc, switches: { ...l.last_ingestion.switches } }
        : null,
      annotations: l.annotations || {}
    })),
    total: d.total ?? items.length
  }
}

/** 端点 12：GET /api/kb/libs/{id}/config —— 库配置读取（上传预览/配置弹窗双消费）。 */
export async function getLibraryConfig(libId) {
  const d = await get(`/kb/libs/${encodeURIComponent(libId)}/config`)
  return {
    id: d.id, name: d.name,
    switches: {
      semantic: Boolean(d.switches.semantic), keyword: Boolean(d.switches.keyword),
      wiki: Boolean(d.switches.wiki), graph: Boolean(d.switches.graph)
    },
    mode: d.mode,
    addSummary: Boolean(d.add_summary),
    addQuestions: Boolean(d.add_questions),
    savedAt: d.saved_at || null,
    savedBy: d.saved_by || null
  }
}

/**
 * 端点 13：PUT /api/kb/libs/{id}/config —— 保存本库配置（待生效——下次入库
 * 定型不热切换）；可选 status 携 'active'|'disabled' 承载停用/启用（v0.3——
 * 缺省不动库状态）。
 * @param {string} libId
 * @param {{switches: {semantic: boolean, keyword: boolean, wiki: boolean, graph: boolean},
 *          mode: string, addSummary: boolean, addQuestions: boolean, status?: string}} p
 */
export async function saveLibraryConfig(libId, p) {
  const d = await put(`/kb/libs/${encodeURIComponent(libId)}/config`, {
    switches: { ...p.switches },
    mode: p.mode,
    add_summary: p.addSummary,
    add_questions: p.addQuestions,
    status: p.status || null
  })
  return {
    id: d.id,
    savedAt: d.saved_at,
    savedBy: d.saved_by,
    status: d.status,
    hint: d.hint,
    activityRow: activityRowToCamel(d.activity_row)
  }
}

/** 端点 14：GET /api/kb/libs/{id}/activities —— 库活动流（F62 只读，时间倒序）。 */
export async function listLibraryActivities(libId) {
  const d = await get(`/kb/libs/${encodeURIComponent(libId)}/activities`)
  const items = Array.isArray(d.items) ? d.items : []
  return {
    items: items.map(r => ({ time: r.time, who: r.who, action: r.action, target: r.target })),
    total: d.total ?? items.length
  }
}

/**
 * 端点 15：POST /api/kb/libs —— 建库（业务模板带出默认配置档案——模板只定
 * 初始档、建后可调；空名 400 / 重名 409 kb_lib_name_duplicate / 模板越界 400）。
 * @param {{libName: string, bizTemplate: string}} p
 */
export async function createLibrary(p) {
  const d = await post('/kb/libs', { lib_name: p.libName, biz_template: p.bizTemplate })
  return {
    libId: d.lib_id,
    libName: d.lib_name,
    bizTemplate: d.biz_template,
    status: d.status,
    config: d.config,
    activityRow: activityRowToCamel(d.activity_row)
  }
}

// ── B2 切片管理（B2-答案出处.md v0.3——六端点消费面，P1-04） ──

/** 片段类型五枚举（B2 合同常量——类型筛下拉与 Tag 色映射共用）。 */
export const FRAGMENT_TYPES = ['原文块', '图片说明块', '图片文字块', '摘要块', '问题块']

/** 队列在途态（B2 端点 4 出列域——终态默认不出列，state=all 亦只出两在途态）。 */
export const ISSUE_OPEN_STATES = ['待质检复核', '已驳回']

/**
 * 端点 1：GET /api/kb/fragments —— 片段台账（两读法分派）：reportId 携带＝按
 * 报告整组取数（整表返回）；缺省＝全库扁平清单（page/pageSize 必带——B3 消费）。
 * @param {{reportId?: string, page?: number, pageSize?: number, type?: string, keyword?: string}} [q]
 */
export async function listFragments(q = {}) {
  const query = { type: q.type || 'all', keyword: q.keyword || '' }
  if (q.reportId) query.report_id = q.reportId
  if (q.page != null) query.page = q.page
  if (q.pageSize != null) query.pageSize = q.pageSize
  const d = await get('/kb/fragments', query)
  const items = Array.isArray(d.items) ? d.items : []
  return {
    items: items.map(f => ({
      id: f.id, reportId: f.report_id, report: f.report,
      well: f.well || null, section: f.section || null, type: f.type, hit: f.hit
    })),
    total: d.total ?? items.length,
    page: d.page ?? null,
    pageSize: d.page_size ?? null
  }
}

/**
 * 端点 2：GET /api/kb/fragments/{id}/context —— 父块回捞（展开/详情弹窗懒加载；
 * 摘要块/问题块 context＝产物说明行——无父块的唯一例外）。
 */
export async function getFragmentContext(id) {
  const d = await get(`/kb/fragments/${encodeURIComponent(id)}/context`)
  return { id: d.id, type: d.type, hit: d.hit, context: d.context }
}

/**
 * 端点 3：POST /api/kb/fragments/{id}/issue-reports —— 标记问题片段（只标记不
 * 直改，进复核队列；待质检复核态重复 409 kb_issue_duplicate；hint 服务端返回）。
 */
export async function markFragmentIssue(id) {
  const d = await post(`/kb/fragments/${encodeURIComponent(id)}/issue-reports`)
  return issueReportToCamel(d)
}

/**
 * 端点 4：GET /api/kb/issue-reports —— 质检复核队列（state=all|待质检复核|
 * 已驳回；终态默认不出列；标记时间倒序；state 越界 400）。
 * @param {{state?: string}} [q]
 */
export async function listIssueReports(q = {}) {
  const d = await get('/kb/issue-reports', { state: q.state || 'all' })
  const items = Array.isArray(d.items) ? d.items : []
  return {
    items: items.map(issueReportToCamel),
    total: d.total ?? items.length
  }
}

/**
 * 端点 5：POST /api/kb/issue-reports/{id}/review —— 复核确认/驳回（confirm 转
 * 修正流；reject 必带 reason——空理由 400 kb_issue_reject_reason_required；
 * 仅待质检复核态可复核，重复 409 kb_issue_state）。
 * @param {string} id
 * @param {{action: 'confirm'|'reject', reason?: string}} p
 */
export async function reviewIssueReport(id, p) {
  const d = await post(
    `/kb/issue-reports/${encodeURIComponent(id)}/review`,
    { action: p.action, reason: p.reason || null }
  )
  return issueReportToCamel(d)
}

/**
 * 端点 6：POST /api/kb/issue-reports/{id}/close —— 驳回后销记（仅已驳回态，
 * 其他态 409；响应 state＝「已销记 · 不修正」合同展示串）。
 */
export async function closeIssueReport(id) {
  const d = await post(`/kb/issue-reports/${encodeURIComponent(id)}/close`)
  return { id: d.id, state: d.state }
}
