/**
 * api/chat —— A1 问一问·真 API 接口层（P1-09）。
 *
 * 合同：teach-petro-agent/specs/api/A1-问一问.md（端点 4 asks／端点 5 resume／
 * 端点 2 sessions／端点 6 assets）＋ 00-系统级API.md §6（帧信封 id/event/data、
 * done/error/replay_truncated 三保留帧、Last-Event-ID 断点）。后端帧类型集
 * 真源＝app/domains/chat/domain.py FRAME_NAMES（19 类，本层不重列业务帧名）。
 *
 * SSE 消费选型（票面「选型说明」落点）：
 * - A1 主端点是 **POST** /api/chat/asks（统一入口无旁路，A1 行为规则 1），而
 *   原生 EventSource 仅支持 GET（00 §6.1 同款悬置点——「POST 流式需 fetch 读
 *   流或网关配合，结合实际框架定」）。本层落定：**fetch + ReadableStream 读
 *   text/event-stream**（不引 sse.js 扩展库、不引第三方 EventSource polyfill）。
 *   理由：① POST 语义是合同硬约束，EventSource/reywood:sse 类方案给不了；
 *   ② fetch 流信封解析做成纯函数（parseSseFrames），帧分发与 api/sse.js 的
 *   RESERVED_FRAMES 同源同语义（done/error/replay_truncated 三收场逐一对齐），
 *   单测可离线喂字节；③ POST 流无浏览器自动重连，断线续推走合同明示的
 *   resume_run_id＋Last-Event-ID 手动形态（端点 4 重连模式——本层 reconnect）
 *   ——自动重连语义留给未来 GET 形态端点，不在本层发明。
 * - 错误出口不走 api/client.request（那里统一 antd message——SSE 页的错误要
 *   内联渲染进对话流，不弹全局 toast）：流开前非 2xx 解统一错误包抛 ApiError；
 *   流内异常按 00 §6.1 只可能是 error 帧（onError 收口）。
 *
 * 端点接线现状（P1-11 收口批）：
 * - 端点 2/4/5/6 全接线（端点 2 sessions / 端点 6 assets 为 P1-11 补齐——
 *   此前两读口按降级标静默兜底，本批去标）；端点 3 sessions/{id}/messages
 *   仍未接线（历史消息回放读口，挂后续批）。
 */

import { API_BASE, ApiError, authHeaders } from './client.js'
import { RESERVED_FRAMES } from './sse.js'

export { RESERVED_FRAMES }

/** 00 §6.1 帧信封行前缀。 */
const ID_PREFIX = 'id: '
const EVENT_PREFIX = 'event: '
const DATA_PREFIX = 'data: '

/**
 * SSE 字节缓冲 → 帧序列（纯函数——单测离线喂字节）。
 *
 * 00 §6.1 信封＝`id:`/`event:`/`data:` 三行＋空行收束；一个缓冲可含多帧，
 * 末帧可能不完整（返回 leftover 续传）。data 非 JSON 原样透传（api/sse.js
 * 同语义）。
 *
 * @param {string} buffer 累积的文本缓冲（可含上一拍 leftover）
 * @returns {{frames: Array<{id: string, event: string, data: any}>, leftover: string}}
 */
export function parseSseFrames(buffer) {
  const blocks = buffer.split('\n\n')
  const leftover = blocks.pop() ?? ''
  const frames = []
  for (const block of blocks) {
    let id = ''
    let event = ''
    let data = null
    let hasData = false
    for (const line of block.split('\n')) {
      if (line.startsWith(ID_PREFIX)) id = line.slice(ID_PREFIX.length)
      else if (line.startsWith(EVENT_PREFIX)) event = line.slice(EVENT_PREFIX.length)
      else if (line.startsWith(DATA_PREFIX)) {
        hasData = true
        const raw = line.slice(DATA_PREFIX.length)
        try { data = JSON.parse(raw) } catch { data = raw }
      }
    }
    if (!event && !hasData) continue // 纯注释行（: keep-alive）不计帧
    frames.push({ id, event, data })
  }
  return { frames, leftover }
}

/** 统一组装鉴权/接受头（X-Dev-User 身份桩——api/client 同源）。 */
function sseHeaders(extra) {
  return {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
    ...authHeaders(),
    ...extra
  }
}

/**
 * 流式读一条 POST SSE（端点 4/5 共用核心）。
 *
 * 保留三帧语义与 api/sse.js 逐条同源（RESERVED_FRAMES 单源）：
 * - done → onDone 后收流；error（带 data）→ onError(错误包) 后收流；
 *   replay_truncated → onReplayTruncated 后收流；三帧同样先过 onFrame。
 * - 传输层断（reader 抛错）→ onTransportError(err)——POST 流无自动重连，
 *   页面凭 lastEventId/run_id 走 reconnect 手动续推（收场①的 POST 形态）。
 * - 流开前非 2xx → 解统一错误包抛 ApiError（00 §3.1：流未开才有状态码）。
 *
 * @param {{path: string, body?: unknown, lastEventId?: string, signal?: AbortSignal,
 *   onFrame?: (f: {id: string, event: string, data: any}) => void,
 *   onDone?: () => void,
 *   onError?: (pkg: {code?: string, message?: string, hint?: unknown}) => void,
 *   onReplayTruncated?: (data: any) => void,
 *   onTransportError?: (err: Error) => void}} args
 * @returns {Promise<{lastEventId: string}>} 正常/保留帧收场后的断点帧号
 */
export async function streamChat(args) {
  const { path, body, lastEventId, signal, onFrame, onDone, onError, onReplayTruncated, onTransportError } = args
  const headers = sseHeaders(lastEventId ? { 'Last-Event-ID': String(lastEventId) } : {})
  let res
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body ?? {}),
      signal
    })
  } catch (err) {
    if (err && err.name === 'AbortError') throw err
    onTransportError?.(err instanceof Error ? err : new Error(String(err)))
    return { lastEventId: lastEventId || '' }
  }
  if (!res.ok) {
    // 流未开（00 §3.1）——统一错误包：ApiError 抛给页面内联渲染（不弹 toast）
    let pkg = {}
    try { pkg = await res.json() } catch { /* 空体/非 JSON 容错 */ }
    throw new ApiError(res.status, pkg, pkg.message || `请求失败（HTTP ${res.status}）`)
  }
  const reader = res.body?.getReader?.()
  if (!reader) throw new ApiError(0, {}, '当前环境不支持流式读取（response.body 为空）')
  const decoder = new TextDecoder()
  let buffer = ''
  let lastId = lastEventId || ''
  let closedByReserved = false
  const finish = () => { try { reader.cancel() } catch { /* 已收口容错 */ } }
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const { frames, leftover } = parseSseFrames(buffer)
      buffer = leftover
      for (const f of frames) {
        if (f.id) lastId = f.id
        onFrame?.(f)
        if (!RESERVED_FRAMES.includes(f.event)) continue
        closedByReserved = true
        if (f.event === 'done') onDone?.()
        else if (f.event === 'error') onError?.(f.data || {})
        else onReplayTruncated?.(f.data ?? {})
        finish()
        return { lastEventId: lastId }
      }
    }
  } catch (err) {
    if (err && err.name === 'AbortError') throw err
    if (!closedByReserved) {
      onTransportError?.(err instanceof Error ? err : new Error(String(err)))
      return { lastEventId: lastId }
    }
  }
  // 服务端未发保留帧先断了流——按传输断处理（不假装 done）
  if (!closedByReserved) onTransportError?.(new Error('SSE 流未以保留帧收场即中断'))
  return { lastEventId: lastId }
}

/**
 * 端点 4 提问形态（question 必填——空问句由后端 400，本层不复制判据）。
 * @param {{question: string, sessionId?: string, anchors?: string[]}} body
 * @param {object} handlers streamChat 五回调（onFrame/onDone/onError/…）
 */
export function postAsk(body, handlers, opts = {}) {
  return streamChat({
    path: '/chat/asks',
    body: {
      question: body.question,
      ...(body.sessionId ? { session_id: body.sessionId } : {}),
      ...(body.anchors && body.anchors.length ? { anchors: body.anchors } : {})
    },
    ...handlers,
    ...opts
  })
}

/**
 * 端点 5 interrupt 决策回流（澄清点选／审批批准·驳回）→ 续推 SSE。
 * @param {string} runId 挂起 run
 * @param {{kind: 'clarify'|'approval', choice?: string, decision?: 'approve'|'reject', reason?: string}} body
 * @param {object} handlers streamChat 五回调
 */
export function postResume(runId, body, handlers, opts = {}) {
  return streamChat({
    path: `/chat/runs/${encodeURIComponent(runId)}/resume`,
    body: { kind: body.kind, ...(body.choice ? { choice: body.choice } : {}),
      ...(body.decision ? { decision: body.decision } : {}),
      ...(body.reason ? { reason: body.reason } : {}) },
    ...handlers,
    ...opts
  })
}

/**
 * 端点 4 断线重连形态（resume_run_id＋Last-Event-ID 头——不重新执行，
 * 服务端重放已持久化帧；404＝run 不存在，ApiError 抛页面内联）。
 * @param {string} runId 待恢复 run
 * @param {string} [lastEventId] 断点帧号（可空——服务端按 run 重放全量持久帧）
 * @param {object} handlers streamChat 五回调
 */
export function reconnectRun(runId, lastEventId, handlers, opts = {}) {
  return streamChat({
    path: '/chat/asks',
    body: { resume_run_id: runId },
    lastEventId,
    ...handlers,
    ...opts
  })
}

// ── 会话读口（端点 2）与 @ 资产面板（端点 6——P1-11 真接线） ──

/** 端点 2 会话行 wire 形（snake）→ 视图形（camel）。 */
function sessionToCamel(s) {
  return {
    id: s.id,
    title: s.title,
    group: s.group || '',
    scenarioId: s.scenario_id || '',
    updatedAt: s.updated_at || ''
  }
}

/**
 * 端点 2 历史会话列表（服务端持久读口——P1-11 真接线）。
 *
 * 读失败/非 2xx 仍静默回 {items:[],available:false}（网络韧性——历史列表
 * 是增强面不是阻断面，不走 client 全局 toast；available 才渲染服务端分组）。
 *
 * @returns {Promise<{items: Array<{id: string, title: string, group: string,
 *   scenarioId: string, updatedAt: string}>, available: boolean}>}
 */
export async function listSessions() {
  try {
    const res = await fetch(`${API_BASE}/chat/sessions`, { headers: sseHeaders() })
    if (!res.ok) return { items: [], available: false }
    const data = await res.json()
    return { items: (data.items || []).map(sessionToCamel), available: true }
  } catch {
    return { items: [], available: false }
  }
}

/**
 * 端点 6 @ 资产面板（各注册表现取投影——指标卡/术语/FAQ/工作流/报告；工具
 * 注册表未建投影为空）。token＝「类型·名称」结晶体（后端出形照抄），随 asks
 * anchors 上送（服务端 S1 前门直取）。
 *
 * @param {{q?: string, type?: string}} [query] q＝name 过滤词；type∈六类
 * @returns {Promise<Array<{type: string, name: string, token: string, hint: string}>>}
 */
export async function listAssets(query = {}) {
  const params = new URLSearchParams()
  if (query.q) params.set('q', query.q)
  if (query.type) params.set('type', query.type)
  const qs = params.toString()
  const res = await fetch(`${API_BASE}/chat/assets${qs ? `?${qs}` : ''}`, { headers: sseHeaders() })
  if (!res.ok) return []
  const data = await res.json()
  return (data.items || []).map(a => ({ type: a.type, name: a.name, token: a.token, hint: '' }))
}
