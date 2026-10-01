/**
 * api/client —— 统一请求层（底座五件之一，P0-06）。
 *
 * 设计真源：
 * - teach-petro-agent/specs/frontend-foundation.md §2.1（fetch 封装不引 axios /
 *   X-Dev-User 注入 / 错误包与分页信封统一解包 / useTaskPolling）；
 * - teach-petro-agent/specs/api/00-系统级API.md §3（统一错误包
 *   {code,message,detail,trace_id}）、§4（分页信封 items/page/pageSize/total/counts）、
 *   §5（异步任务 202 受理＋轮询＋终态，11 处先例）。
 *
 * 约定：
 * - 路径参数一律填「/api 之后的 Relative Path」（如 '/gateway/models'）；
 *   API_BASE 默认 '/api'（dev 走 vite proxy → FastAPI :8000），可用
 *   VITE_API_BASE 覆盖（直连后端场景）；
 * - 身份桩：X-Dev-User 请求头（00 册 §2）。开发期默认 'aqiang'（平台运维，
 *   过 D 组组闸），localStorage 可改；生产 OAuth2.0 换 token 注入（切换时点
 *   未拍板——frontend-foundation §2.1 原文），替换缝＝authHeaders()；
 * - 非 2xx：解错误包 → antd message 提示（人话 message＋trace_id）→ 抛
 *   ApiError（页面可 catch 做进一步 UI 态）；401/403/409/422 兜底话术在
 *   STATUS_FALLBACKS 集中处理；
 * - 本文件不静态 import antd（保持 node 测试环境可加载），提示器经
 *   dynamic import + setApiNotifier 可替换。
 */

import { useRef, useState, useEffect } from 'react'

/** API 根路径：默认 '/api'（同源＋vite proxy），VITE_API_BASE 可覆盖。 */
export const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE) || '/api'

const DEV_USER_KEY = 'petro.dev-user'
/** 开发期默认身份（阿强 · 平台运维——过设置中心组闸；与后端桩默认一致）。 */
export const DEFAULT_DEV_USER = 'aqiang'

/**
 * 读当前开发期身份（X-Dev-User 头值）。
 * @returns {string} localStorage『petro.dev-user』缺省回退 'aqiang'
 */
export function getDevUser() {
  try {
    return localStorage.getItem(DEV_USER_KEY) || DEFAULT_DEV_USER
  } catch {
    return DEFAULT_DEV_USER
  }
}

/**
 * 改开发期身份（仅 X-Dev-User 桩；生产 OAuth2.0 上线后本函数退役）。
 * @param {string} user 五角色 key（roles.js：laowang/xiaoli/zhuren/aqiang/shixi）
 */
export function setDevUser(user) {
  try {
    localStorage.setItem(DEV_USER_KEY, user)
  } catch {
    /* 无 localStorage 环境（隐私模式）静默忽略 */
  }
}

/**
 * 组装鉴权头（OAuth2.0 替换缝：届时仅改本函数体）。
 * @returns {Record<string, string>}
 */
export function authHeaders() {
  return { 'X-Dev-User': getDevUser() }
}

// ── 提示器（默认 antd message；测试可替换） ──

let notify = (level, content) => {
  import('antd')
    .then(m => { m.message[level]?.(content) })
    .catch(() => { /* 非 DOM 环境静默 */ })
}

/**
 * 替换错误提示器（单测桩 / 特殊页面定制）。传 null 恢复默认。
 * @param {null | ((level: 'error'|'warning'|'info', content: string) => void)} fn
 */
export function setApiNotifier(fn) {
  notify = fn || ((level, content) => {
    import('antd').then(m => { m.message[level]?.(content) }).catch(() => {})
  })
}

/** 统一错误包（00 册 §3.1）。 */
export class ApiError extends Error {
  /**
   * @param {number} status HTTP 状态码
   * @param {{code?: string, message?: string, detail?: unknown, trace_id?: string}} pkg 错误包（可能残缺）
   * @param {string} displayMessage 兜底补齐后的人话消息
   */
  constructor(status, pkg, displayMessage) {
    super(displayMessage)
    this.name = 'ApiError'
    /** @type {number} HTTP 状态码 */
    this.status = status
    /** @type {string} 业务错误码（<域>_<语义> 蛇形，00 §3.3） */
    this.code = pkg.code || ''
    /** @type {unknown} 结构化附加（字段名＋允许区间等） */
    this.detail = pkg.detail ?? null
    /** @type {string} 网关调用号 / run_id，供 D5 排障 */
    this.traceId = pkg.trace_id || ''
  }
}

/**
 * 从响应体提取错误包（非 JSON / 空体安全）。
 * @param {unknown} data
 * @returns {{code: string, message: string, detail: unknown, trace_id: string}}
 */
function asErrorPackage(data) {
  const o = (data && typeof data === 'object') ? /** @type {Record<string, unknown>} */ (data) : {}
  return {
    code: typeof o.code === 'string' ? o.code : '',
    message: typeof o.message === 'string' ? o.message : '',
    detail: o.detail ?? null,
    trace_id: typeof o.trace_id === 'string' ? o.trace_id : ''
  }
}

/** 401/403/409/422 兜底话术（frontend-foundation §2.1「状态语义集中处理」；错误包缺 message 时用）。 */
const STATUS_FALLBACKS = /** @type {Record<number, string>} */ ({
  401: '登录态无效：身份桩未识别（检查 X-Dev-User）',
  403: '无权限：当前角色不可访问该资源',
  409: '状态冲突：已有任务进行中或状态迁移前置不满足（刷新后重试或放弃）',
  422: '业务规则拒绝：形状合法但语义校验不通过',
  500: '服务端内部错误（可凭 trace_id 到 D5 运行追踪排障）'
})

/**
 * 分页信封解包（00 册 §4）：items＋page/pageSize/total/counts 归一化。
 * 非分页形状（整对象/数组/标量）原样返回——「本版整表返回为常态」，检测条件
 * 刻意保守：items 为数组**且**带 total/page 任一（两者皆无＝普通整表对象，不动）。
 * 归一化保留信封内兄弟字段（A1 端点 1 合同 DTO {items,total,groups} 的 groups
 * 不吞）——先 `...d` 展开，再覆盖分页四字段。
 * @template T
 * @param {T | {items: T[], page?: number, pageSize?: number, total?: number, counts?: Record<string, number>, [k: string]: unknown}} data
 * @returns {T | {items: T[], page: number, pageSize: number, total: number, counts: Record<string, number> | null, [k: string]: unknown}}
 */
export function unwrapEnvelope(data) {
  if (!data || typeof data !== 'object' || !Array.isArray(/** @type {any} */ (data).items)) return data
  const d = /** @type {any} */ (data)
  if (!('total' in d) && !('page' in d)) return data
  return {
    ...d,
    page: typeof d.page === 'number' ? d.page : 1,
    // 后端 R1 裁决响应字段统一 snake_case——分页信封回显为 page_size（D1 端点 4 实测），
    // 归一化时作为 camel pageSize 的同义来源；两者皆缺才按 items 长度兜底。
    pageSize: typeof d.pageSize === 'number'
      ? d.pageSize
      : (typeof d.page_size === 'number' ? d.page_size : d.items.length),
    total: typeof d.total === 'number' ? d.total : d.items.length,
    counts: (d.counts && typeof d.counts === 'object') ? d.counts : null
  }
}

/**
 * 统一请求入口（fetch 封装，不引 axios）。
 * @param {string} path '/api' 之后的相对路径（如 '/gateway/models'、'/security/audit-logs'）
 * @param {{method?: string, body?: unknown, headers?: Record<string, string>, signal?: AbortSignal}} [opts]
 * @returns {Promise<any>} 解包后的响应体（分页形状经 unwrapEnvelope 归一化）
 * @throws {ApiError} 非 2xx——错误包已提示（antd message）后抛出
 */
export async function request(path, opts = {}) {
  const { method = 'GET', body, headers, signal } = opts
  let res
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', ...authHeaders(), ...headers },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal
    })
  } catch (err) {
    // AbortError 直通（unmount 竞窗 / 主动取消不属网络故障，P0-07 审查 P3）：
    // 包成 ApiError(0) 会误弹「网络异常」toast、且被 pollTaskUntilDone 误计一次
    // 瞬时失败——「AbortError 直通不占容忍额度」的承诺由本行兑现。
    if (err && err.name === 'AbortError') throw err
    // 网络层失败（后端未起 / 断网）——没有错误包，提示＋抛 ApiError(0)
    const msg = '网络异常：服务不可达（检查后端 :8000 与 vite proxy）'
    notify('error', msg)
    throw new ApiError(0, {}, msg)
  }

  const text = await res.text()
  /** @type {any} */
  let data = null
  if (text) {
    try { data = JSON.parse(text) } catch { data = text }
  }

  if (!res.ok) {
    const pkg = asErrorPackage(data)
    const msg = pkg.message || STATUS_FALLBACKS[res.status] || `请求失败（HTTP ${res.status}）`
    // trace_id 随提示带出——「失败原因只到停在哪一步＋人话原因」（B1 F32 红线同族）
    notify('error', pkg.trace_id ? `${msg}（trace ${pkg.trace_id}）` : msg)
    throw new ApiError(res.status, pkg, msg)
  }
  return unwrapEnvelope(data)
}

/** GET 便捷式。 @param {string} path @param {Record<string, string>} [query] @param {{signal?: AbortSignal}} [opts] */
export async function get(path, query, opts = {}) {
  const qs = query ? `?${new URLSearchParams(query).toString()}` : ''
  return request(`${path}${qs}`, { signal: opts.signal })
}

/** POST 便捷式。 @param {string} path @param {unknown} [body] @param {{signal?: AbortSignal}} [opts] */
export function post(path, body, opts = {}) {
  return request(path, { method: 'POST', body, signal: opts.signal })
}

/**
 * PUT 便捷式（P0-07 底座补件：D1 端点 3「保存调用参数」是平台第一个 PUT 消费方）。
 * @param {string} path @param {unknown} [body] @param {{signal?: AbortSignal}} [opts]
 */
export function put(path, body, opts = {}) {
  return request(path, { method: 'PUT', body, signal: opts.signal })
}

// ── 异步任务轮询（00 册 §5：202 受理 → 轮询 → 终态；11 处先例同构） ──

/**
 * 进行中状态集（00 §5.1 全部先例的并集）：
 * running/done（C3/D1/D3/D2/E1）、running/done/failed/stuck（B1）、
 * accepted/generating/stored/ready/failed（A1/F1 五态）、running→done（B3/E2/E3）。
 * 判定规则：不在此集即终态——后端新增状态默认按终态处理（fail-safe）。
 */
export const TASK_IN_FLIGHT = new Set(['queued', 'accepted', 'pending', 'processing', 'running', 'generating'])

/**
 * 状态是否终态（00 §5.2：done/failed/stuck/ready/stored…）。
 * @param {string} status
 * @returns {boolean}
 */
export function isTerminalStatus(status) {
  return Boolean(status) && !TASK_IN_FLIGHT.has(status)
}

/** 失败终态集（B1 四态的 failed/stuck；其余终态视为成功收场）。 */
const TASK_FAILED = new Set(['failed', 'stuck'])

/**
 * 轮询一次任务直到终态（纯函数版，供 useTaskPolling 与单测复用）。
 * 瞬时失败容忍：轮询中单次请求失败（网络抖动/网关 5xx）不立判整体 failed——
 * 同任务容忍一次、下一节奏重试；连续两次失败才向上抛（useTaskPolling 收到
 * 置 failed）；期间任一次成功即归零计数。AbortError 直通不占容忍额度。
 * @param {{taskId: string, path: string, intervalMs?: number, signal?: AbortSignal,
 *   onProgress?: (data: any) => void}} args
 *   path 为任务资源 GET 前缀（如 '/gateway/drills' → GET /api/gateway/drills/{taskId}）；
 *   onProgress（P0-07 底座补件）：每次成功轮询（含进行中快照）即回调一次——
 *   D1 演练四步节点进度靠它实时渲染（原型页 300ms 一拍逐步点亮）；回调抛错
 *   不打断轮询（fail-safe，进度渲染失败不该弄死任务收场）。
 * @returns {Promise<{status: string, data: any}>} 终态行（含 status/nodes/current_step/result…）
 */
export async function pollTaskUntilDone({ taskId, path, intervalMs = 1500, signal, onProgress }) {
  let transientFailures = 0
  while (true) {
    /** @type {any} */ let data = null
    try {
      data = await request(`${path}/${encodeURIComponent(taskId)}`, { signal })
      transientFailures = 0
    } catch (err) {
      if (err && err.name === 'AbortError') throw err
      transientFailures += 1
      if (transientFailures >= 2) throw err
    }
    if (data) {
      if (onProgress) {
        try { onProgress(data) } catch { /* 进度回调失败不影响轮询收场 */ }
      }
      // 终态字段兼容双 wire 形：status（D1 drills 等先例）∥ state（B1/B2 任务族）——
      // P1-03 收尾裁决：底座一行通改，消灭每接口层重复适配 hook。
      const status = String(data.status || data.state || '')
      if (isTerminalStatus(status)) return { status, data }
    }
    await new Promise(resolve => setTimeout(resolve, intervalMs))
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
  }
}

/**
 * useTaskPolling —— 通用任务轮询 hook（frontend-foundation §2.1；00 §5）。
 *
 * 用法（受理 202 拿到任务号后挂上）：
 *   const { status, data, error } = useTaskPolling(drillId, { path: '/gateway/drills' })
 *   // status: 'idle'（无任务号）| 'polling' | 'done' | 'failed'
 *   // data:   终态任务行（nodes 四态/current_step/result…，形状按各册合同）
 *
 * onProgress（P0-07 底座补件）：轮询中每次成功快照即回调（进行中状态可见）——
 * 回调身份允许每渲染变化（内部 ref 转发，不触发重新轮询）。
 *
 * @param {string | null} taskId 受理响应里的任务号（drill-…/task-…/run-…）；null/空串不轮询
 * @param {{path: string, intervalMs?: number, onProgress?: (data: any) => void}} opts
 *   path＝任务资源 GET 前缀；intervalMs 轮询节奏
 *   （00 §5.2：轮询节奏由服务端真实进度决定，页面演示动画不入合同）
 * @returns {{status: 'idle'|'polling'|'done'|'failed', data: any, error: Error | null}}
 */
export function useTaskPolling(taskId, opts) {
  const { path, intervalMs = 1500, onProgress } = opts
  const progressRef = useRef(onProgress)
  progressRef.current = onProgress
  const [state, setState] = useState(/** @type {{status: any, data: any, error: any}} */ ({ status: taskId ? 'polling' : 'idle', data: null, error: null }))

  useEffect(() => {
    if (!taskId) {
      setState({ status: 'idle', data: null, error: null })
      return undefined
    }
    const ctrl = new AbortController()
    setState({ status: 'polling', data: null, error: null })
    pollTaskUntilDone({ taskId, path, intervalMs, signal: ctrl.signal, onProgress: d => progressRef.current?.(d) })
      .then(({ status, data }) => setState({
        status: TASK_FAILED.has(status) ? 'failed' : 'done',
        data,
        error: null
      }))
      .catch(err => {
        if (err && err.name === 'AbortError') return
        setState({ status: 'failed', data: null, error: err })
      })
    return () => ctrl.abort()
  }, [taskId, path, intervalMs])

  return state
}
