/**
 * api/client 单测（P0-06 验收：client 单测过）——
 * 覆盖：分页信封解包（含 total/page 守卫＋兄弟字段保留）/ X-Dev-User 注入 /
 * 错误包解包＋提示＋抛出 / 409 兜底话术 / 网络异常 / AbortError 直通（unmount
 * 竞窗不弹错不包 ApiError，P0-07 审查 P3）/
 * pollTaskUntilDone 终态判定＋瞬时失败容忍（一次重试，二连败才 failed）。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ApiError, DEFAULT_DEV_USER, getDevUser, get, isTerminalStatus, pollTaskUntilDone, put,
  request, setApiNotifier, unwrapEnvelope
} from './client.js'

const fetchMock = vi.fn()
vi.stubGlobal('fetch', fetchMock)
const notifier = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  notifier.mockReset()
  setApiNotifier((level, content) => notifier(level, content))
})

afterEach(() => {
  vi.restoreAllMocks()
})

function jsonResponse(status, body) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body)
  }
}

describe('unwrapEnvelope 分页信封（00 册 §4）', () => {
  it('items+total+page 归一化补齐缺省字段', () => {
    const out = unwrapEnvelope({ items: [1, 2, 3], total: 42, page: 2, pageSize: 15, counts: { all: 42 } })
    expect(out).toEqual({ items: [1, 2, 3], page: 2, pageSize: 15, total: 42, counts: { all: 42 } })
  })

  it('带 page 缺 total/pageSize 时按 items 长度补齐（P0-06 收口：守卫要求 total/page 任一在场）', () => {
    const out = unwrapEnvelope({ items: ['a', 'b'], page: 3 })
    expect(out.total).toBe(2)
    expect(out.pageSize).toBe(2)
    expect(out.page).toBe(3)
    expect(out.counts).toBeNull()
  })

  it('守卫：items 数组但无 total/page＝普通整表对象，原样返回不误归一化', () => {
    const d = { items: [{ id: 1 }, { id: 2 }] }
    expect(unwrapEnvelope(d)).toBe(d)
  })

  it('兄弟字段保留：A1 端点 1 合同 DTO {items,total,groups} 的 groups 不被吞（P0-06 审查 P2）', () => {
    const groups = { by_model: { 'petro-main': 3, 'petro-lite': 1 } }
    const out = unwrapEnvelope({ items: [1, 2], total: 5, groups })
    expect(out.groups).toBe(groups)
    expect(out.total).toBe(5)
    expect(out.page).toBe(1)
    expect(out.pageSize).toBe(2)
  })

  it('非分页形状原样返回（整表返回为常态）', () => {
    const obj = { gateway: { status: 'running' }, models: [] }
    expect(unwrapEnvelope(obj)).toBe(obj)
    const arr = [1, 2]
    expect(unwrapEnvelope(arr)).toBe(arr)
    expect(unwrapEnvelope(null)).toBeNull()
  })
})

describe('request —— X-Dev-User 注入与成功路径', () => {
  it('默认身份 aqiang 注入请求头（身份桩 00 §2）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { ok: true }))
    await request('/gateway/models')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/gateway/models')
    expect(init.headers['X-Dev-User']).toBe(DEFAULT_DEV_USER)
    expect(getDevUser()).toBe(DEFAULT_DEV_USER)
  })

  it('GET 便捷式拼 query', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { items: [] }))
    await get('/security/audit-logs', { page: '2', pageSize: '15' })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/security/audit-logs?page=2&pageSize=15')
  })
})

describe('request —— 统一错误包（00 册 §3）', () => {
  it('400 错误包解包：message/detail/trace_id 进 ApiError，antd 提示带 trace', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(400, {
      code: 'gateway_param_invalid',
      message: '条数越界——pageSize 上限 100',
      detail: { field: 'pageSize', constraint: '<=100' },
      trace_id: 'call-8c31'
    }))
    const err = await request('/gateway/spend-logs?pageSize=999').catch(e => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(400)
    expect(err.code).toBe('gateway_param_invalid')
    expect(err.message).toBe('条数越界——pageSize 上限 100')
    expect(err.detail).toEqual({ field: 'pageSize', constraint: '<=100' })
    expect(err.traceId).toBe('call-8c31')
    expect(notifier).toHaveBeenCalledWith('error', '条数越界——pageSize 上限 100（trace call-8c31）')
  })

  it('409 无 message 时用集中兜底话术（frontend-foundation §2.1）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(409, { code: 'gateway_drill_conflict' }))
    const err = await request('/gateway/drills', { method: 'POST', body: {} }).catch(e => e)
    expect(err.status).toBe(409)
    expect(err.code).toBe('gateway_drill_conflict')
    expect(err.message).toContain('状态冲突')
    expect(notifier).toHaveBeenCalledWith('error', expect.stringContaining('状态冲突'))
  })

  it('网络层失败 → ApiError(0) 提示服务不可达', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const err = await request('/gateway/models').catch(e => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(0)
    expect(err.message).toContain('服务不可达')
  })

  it('AbortError 直通（unmount 竞窗）：不弹错、不上抛 ApiError，原样透传（P0-07 审查 P3）', async () => {
    const abortErr = new DOMException('The operation was aborted.', 'AbortError')
    fetchMock.mockRejectedValueOnce(abortErr)
    const err = await request('/gateway/models', { signal: new AbortController().signal }).catch(e => e)
    expect(err).toBe(abortErr)
    expect(err).not.toBeInstanceOf(ApiError)
    expect(notifier).not.toHaveBeenCalled() // 取消≠网络故障，不弹「网络异常」toast
  })
})

describe('pollTaskUntilDone / isTerminalStatus（00 册 §5）', () => {
  it('进行中状态集覆盖 11 处先例；未知状态按终态 fail-safe', () => {
    for (const s of ['queued', 'accepted', 'pending', 'processing', 'running', 'generating']) {
      expect(isTerminalStatus(s)).toBe(false)
    }
    for (const s of ['done', 'failed', 'stuck', 'ready', 'stored']) {
      expect(isTerminalStatus(s)).toBe(true)
    }
    expect(isTerminalStatus('')).toBe(false)
    expect(isTerminalStatus('whatever_new')).toBe(true)
  })

  it('202 受理后轮询 running→done：终态返回任务行', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { status: 'running', nodes: [] }))
      .mockResolvedValueOnce(jsonResponse(200, { status: 'running', nodes: [] }))
      .mockResolvedValueOnce(jsonResponse(200, { status: 'done', result: { switched_to: 'petro-lite' } }))
    const { status, data } = await pollTaskUntilDone({ taskId: 'drill-9019', path: '/gateway/drills', intervalMs: 1 })
    expect(status).toBe('done')
    expect(data.result.switched_to).toBe('petro-lite')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/gateway/drills/drill-9019')
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('failed 终态立即返回不重试', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { status: 'failed', reason: '生成超时', stop_at: 'deck.render' }))
    const { status, data } = await pollTaskUntilDone({ taskId: 'art-task-1', path: '/chat/artifacts', intervalMs: 1 })
    expect(status).toBe('failed')
    expect(data.stop_at).toBe('deck.render')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('瞬时失败容忍一次：单次网络抖动下一节奏重试照常收场（P0-06 审查 P3）', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(jsonResponse(200, { status: 'running' }))
      .mockResolvedValueOnce(jsonResponse(200, { status: 'done', result: { ok: 1 } }))
    const { status, data } = await pollTaskUntilDone({ taskId: 'drill-t1', path: '/gateway/drills', intervalMs: 1 })
    expect(status).toBe('done')
    expect(data.result.ok).toBe(1)
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('二连败才整体 failed：连续两次失败向上抛（网络异常包成 ApiError(0)）', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))
    const err = await pollTaskUntilDone({ taskId: 'drill-t2', path: '/gateway/drills', intervalMs: 1 }).catch(e => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(0)
    expect(err.message).toContain('服务不可达')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('轮询中请求被 abort：AbortError 直通不占容忍额度（一拍即抛、不重试、不包 ApiError）', async () => {
    // 前提＝request() 对 AbortError 原样透传——否则这里会被包成 ApiError(0) 计一次
    // 瞬时失败并重试（旧缺陷行为：两次调用后抛 ApiError）。
    fetchMock.mockRejectedValue(new DOMException('The operation was aborted.', 'AbortError'))
    const err = await pollTaskUntilDone({ taskId: 'drill-ab', path: '/gateway/drills', intervalMs: 1 }).catch(e => e)
    expect(err.name).toBe('AbortError')
    expect(err).not.toBeInstanceOf(ApiError)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('成功一次归零容忍：失败→成功→再失败仍被容忍，照常到 done', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('boom'))
      .mockResolvedValueOnce(jsonResponse(200, { status: 'running' }))
      .mockRejectedValueOnce(new TypeError('boom again'))
      .mockResolvedValueOnce(jsonResponse(200, { status: 'done' }))
    const { status } = await pollTaskUntilDone({ taskId: 'drill-t3', path: '/gateway/drills', intervalMs: 1 })
    expect(status).toBe('done')
    expect(fetchMock).toHaveBeenCalledTimes(4)
  })
})

// ── P0-07 底座补件增测：snake 信封 page_size / put 便捷式 / 轮询 onProgress ──

describe('unwrapEnvelope —— snake 信封 page_size 同义归一（P0-07 底座补件）', () => {
  it('后端 R1 snake 回显 page_size 归一为 camel pageSize（D1 端点 4 实测形状）', () => {
    const out = unwrapEnvelope({ items: [{ id: 'call-1' }], total: 31, page: 3, page_size: 15 })
    expect(out.pageSize).toBe(15)
    expect(out.total).toBe(31)
    expect(out.page).toBe(3)
    expect(out.page_size).toBe(15) // 兄弟字段照旧保留
  })

  it('camel pageSize 在场时优先 camel（向后兼容 mock 形状）', () => {
    const out = unwrapEnvelope({ items: [], total: 0, page: 1, pageSize: 15 })
    expect(out.pageSize).toBe(15)
  })
})

describe('put 便捷式（P0-07 底座补件：D1 端点 3 首个 PUT 消费方）', () => {
  it('PUT 方法 + JSON 体拼装，走统一错误包与信封路径', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { params: { allowed_fails: 2 }, yaml: '# y' }))
    const out = await put('/gateway/config', { params: { allowedFails: 2 } })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/gateway/config')
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual({ params: { allowedFails: 2 } })
    expect(out.yaml).toBe('# y')
  })

  it('PUT 非 2xx 照常抛 ApiError（400 参数越界）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(400, {
      code: 'gateway_param_invalid', message: '参数越界', detail: [{ field: 'allowed_fails', range: '1-10' }]
    }))
    const err = await put('/gateway/config', { params: {} }).catch(e => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(400)
  })
})

describe('pollTaskUntilDone onProgress（P0-07 底座补件：进行中快照实时回调）', () => {
  it('每次成功轮询（含 running 中间态）都回调，终态那次也回调后返回', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { status: 'running', nodes: [{ key: 'fail1', state: 'process' }] }))
      .mockResolvedValueOnce(jsonResponse(200, { status: 'done', nodes: [{ key: 'fail1', state: 'finish' }], result: { ok: 1 } }))
    const seen = []
    const { status } = await pollTaskUntilDone({
      taskId: 'drill-p1', path: '/gateway/drills', intervalMs: 1, onProgress: d => seen.push(d.status)
    })
    expect(status).toBe('done')
    expect(seen).toEqual(['running', 'done'])
  })

  it('onProgress 抛错不打断轮询（fail-safe），照常收场 done', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { status: 'running' }))
      .mockResolvedValueOnce(jsonResponse(200, { status: 'done' }))
    const { status } = await pollTaskUntilDone({
      taskId: 'drill-p2', path: '/gateway/drills', intervalMs: 1, onProgress: () => { throw new Error('render boom') }
    })
    expect(status).toBe('done')
  })

  it('不传 onProgress 行为不变（向后兼容）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { status: 'done', result: { x: 1 } }))
    const { data } = await pollTaskUntilDone({ taskId: 'drill-p3', path: '/gateway/drills', intervalMs: 1 })
    expect(data.result.x).toBe(1)
  })
})
