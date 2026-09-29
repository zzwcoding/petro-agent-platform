/**
 * api/sse —— SSE 事件流客户端骨架（底座五件之二，P0-06）。
 *
 * 设计真源：
 * - teach-petro-agent/specs/frontend-foundation.md §2.2（原生 EventSource 不引库 /
 *   帧分发 / Last-Event-ID 断线续传 / 三帧语义全通道复用）；
 * - teach-petro-agent/specs/api/00-系统级API.md §6（帧信封 id/event/data；
 *   done/error/replay_truncated 三收场；断线恢复三收场——窗内重连补发 /
 *   缓冲耗尽话术 / replay_truncated）。
 *
 * 本票（P0-06）范围＝骨架＋单测桩，不接 A1（A1 会话域在阶段 1 落地）。
 *
 * Last-Event-ID 续传接线说明（00 §6.2 三收场的分工）：
 * - 收场①（窗内重连）：浏览器原生 EventSource **自动重连时自动携带
 *   Last-Event-ID 头**（值＝最后收到帧的 id），服务端按断点补发——客户端零代码，
 *   本封装不干预（onNativeError 只做观测上报，不 close，让浏览器继续重连）；
 * - 收场②（缓冲耗尽）：服务端补不动了，发「会话中断较久…请重新提问」话术帧
 *   或 replay_truncated 帧——本封装收到 replay_truncated 即 close 并回调
 *   onReplayTruncated（不静默丢帧）；
 * - 收场③（生成已取消）：同以 replay_truncated 帧收场（A1 合同值）。
 * - A1 的 `resume_run_id` 手动续传（POST 流式形态悬置，00 §6.1）在 A1 落地批
 *   接线：届时经 options.url 组装 resume 参数或换 fetch 读流，本骨架的
 *   getLastEventId() 供其取断点帧号。
 *
 * 帧分发：每页面只订自己关心的帧类型（events 数组），done/error/
 * replay_truncated 三帧语义内置全通道复用；error 帧区分服务端业务帧
 * （带 data）与原生传输错误（无 data）。
 */

/** 00 §6.1 结束/异常/截断三帧——全通道复用的保留帧型。 */
export const RESERVED_FRAMES = ['done', 'error', 'replay_truncated']

/**
 * 创建一条 SSE 事件流。
 * @param {string} url 流地址（GET 形态；POST 流式待 00 §6.1 悬置收敛后经 fetch 读流扩展）
 * @param {object} [opts]
 * @param {string[]} [opts.events] 要订阅的业务帧类型集（如 ['stage','sec_check','answer']）；
 *   done/error/replay_truncated 三帧无需声明、恒内置
 * @param {(frame: {event: string, data: any, id: string}) => void} [opts.onFrame]
 *   业务帧回调（含保留三帧——onDone/onError/onReplayTruncated 触发时同样先过这里）
 * @param {() => void} [opts.onDone] 收到 done 帧（正常收尾，随后 close）
 * @param {(pkg: {code?: string, message?: string, hint?: unknown}) => void} [opts.onError]
 *   收到服务端 error 帧（发出后服务端关流——00 §6.1；本端 close）
 * @param {() => void} [opts.onReplayTruncated] 收到 replay_truncated 帧（收场②/③；本端 close）
 * @param {(evt: Event) => void} [opts.onNativeError] 原生传输错误（不 close——
 *   浏览器自动重连带 Last-Event-ID，即收场①；仅观测缝）
 * @param {() => void} [opts.onOpen] 连接建立（观测缝）
 * @param {typeof EventSource} [opts.EventSourceImpl] 注入实现（单测桩）；
 *   缺省用 globalThis.EventSource
 * @param {boolean} [opts.withCredentials] 跨域是否带凭证（同源 dev 场景无需）
 * @returns {{close: () => void, getLastEventId: () => string, source: unknown}}
 */
export function createEventStream(url, opts = {}) {
  const {
    events = [],
    onFrame,
    onDone,
    onError,
    onReplayTruncated,
    onNativeError,
    onOpen,
    EventSourceImpl = globalThis.EventSource,
    withCredentials = false
  } = opts
  if (!EventSourceImpl) throw new Error('sse: 当前环境无 EventSource，且未注入 EventSourceImpl')

  /** @type {any} */
  const source = new EventSourceImpl(url, { withCredentials })
  let lastEventId = ''
  let closed = false

  const close = () => {
    if (closed) return
    closed = true
    source.close()
  }

  const emit = event => evt => {
    // 原生传输错误无 data 体——交给浏览器自动重连（收场①），不 close
    if (event === 'error' && (evt.data === undefined || evt.data === null)) {
      onNativeError?.(evt)
      return
    }
    lastEventId = evt.lastEventId || lastEventId
    let data = null
    if (evt.data) {
      try { data = JSON.parse(evt.data) } catch { data = evt.data }
    }
    onFrame?.({ event, data, id: evt.lastEventId || '' })
    switch (event) {
      case 'done':
        onDone?.()
        close()
        break
      case 'error':
        onError?.(data || {})
        close() // 00 §6.1：异常帧发出后服务端关流，客户端同步收口
        break
      case 'replay_truncated':
        onReplayTruncated?.()
        close()
        break
      default:
        break // 业务帧只分发，生命周期由保留三帧决定
    }
  }

  source.onopen = () => { onOpen?.() }
  // 原生 onerror：传输层错误（含自动重连过程）——观测缝，不干预重连
  source.addEventListener('error', emit('error'))
  for (const type of new Set([...events, ...RESERVED_FRAMES])) {
    if (type === 'error') continue // 上面已挂（需区分原生/业务帧）
    source.addEventListener(type, emit(type))
  }

  return {
    close,
    /** @returns {string} 最后收到帧的 id（A1 resume_run_id 续传接线点） */
    getLastEventId: () => lastEventId,
    source
  }
}
