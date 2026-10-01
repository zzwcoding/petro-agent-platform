/**
 * api/chat 单测（P1-09）——POST SSE 流消费（fetch+ReadableStream 选型）＋
 * 保留三帧同源语义＋resume/reconnect 形状＋会话读口静默容错。
 * 帧序列夹具照抄 P1-08c 金样本帧序（session→stage→…→token→citation→answer→done）。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from './client.js'
import { RESERVED_FRAMES as SSE_RESERVED } from './sse.js'
import {
  listAnchorCandidates, listSessions, parseSseFrames, postAsk, postResume,
  reconnectRun, RESERVED_FRAMES, streamChat
} from './chat.js'

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

/** SSE 文本 → Response（真 ReadableStream——jsdom/node 全局 Response 消费）。 */
function sseResponse(text, { status = 200 } = {}) {
  return new Response(text, { status, headers: { 'Content-Type': 'text/event-stream' } })
}

/** 金样本帧序列（检索问答链主路径——树帧全在首个 token 之前，P1-08c 时序）。 */
function goldenFrames() {
  return [
    ['session', { run_id: 'run-x1', thread_id: 'sess-9' }],
    ['stage', { stage: 0 }],
    ['sec_check', { seq: 1, name: '注入扫描', result: 'pass', note: '字面规则未命中' }],
    ['node', { key: 'N1', name: '统一安检', label: '统一安检', state: 'process' }],
    ['node', { key: 'N1', name: '统一安检', label: '统一安检', state: 'finish', note: '三道全过——放行' }],
    ['token', { delta: '筛管' }],
    ['token', { delta: '完井' }],
    ['citation', { ref: 'c1', kind: '报告引用', label: '出处 1 · N-02 完井报告', locator: { fragment_id: 'f3', report: 'N-02 完井报告' } }],
    ['answer', { kind: 'text', text: '筛管完井', citations: [{ ref: 'c1', kind: '报告引用', label: '出处 1', locator: {} }] }],
    ['done', {}]
  ]
}

function goldenText() {
  return goldenFrames().map(([event, data]) =>
    `id: ${event === 'done' ? 9 : 1}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`
  ).join('')
}

describe('parseSseFrames 信封解析（00 §6.1）', () => {
  it('id/event/data 三行＋空行收束；多帧同缓冲；data 自动 JSON', () => {
    const { frames, leftover } = parseSseFrames(goldenText())
    expect(frames).toHaveLength(goldenFrames().length)
    expect(frames[0]).toEqual({ id: '1', event: 'session', data: { run_id: 'run-x1', thread_id: 'sess-9' } })
    expect(frames[frames.length - 1].event).toBe('done')
    expect(leftover).toBe('')
  })

  it('跨 chunk 断帧：半截帧留 leftover，续上后完整解析', () => {
    const full = 'event: token\ndata: {"delta":"筛"}\n\n'
    const first = parseSseFrames(full.slice(0, 20))
    expect(first.frames).toHaveLength(0)
    expect(first.leftover.length).toBeGreaterThan(0)
    const second = parseSseFrames(first.leftover + full.slice(20))
    expect(second.frames).toEqual([{ id: '', event: 'token', data: { delta: '筛' } }])
  })

  it('data 非 JSON 原样透传；纯注释行（: keep-alive）不计帧', () => {
    const { frames } = parseSseFrames(': ping\n\nevent: notice\ndata: plain-text\n\n')
    expect(frames).toHaveLength(1)
    expect(frames[0].data).toBe('plain-text')
  })
})

describe('streamChat 保留三帧（与 api/sse.js RESERVED_FRAMES 同源）', () => {
  it('RESERVED_FRAMES 直接复用 sse.js——done/error/replay_truncated', () => {
    expect(RESERVED_FRAMES).toBe(SSE_RESERVED)
  })

  it('金样本帧序逐帧分发；done 后收流并返回断点帧号', async () => {
    fetchMock.mockResolvedValueOnce(sseResponse(goldenText()))
    const seen = []
    const res = await streamChat({
      path: '/chat/asks',
      body: { question: '防砂方式是什么' },
      onFrame: f => seen.push(f)
    })
    expect(seen.map(f => f.event)).toEqual(goldenFrames().map(([e]) => e))
    expect(res.lastEventId).toBe('9')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/chat/asks')
    const init = fetchMock.mock.calls[0][1]
    expect(init.method).toBe('POST')
    expect(init.headers.Accept).toBe('text/event-stream')
    expect(init.headers['X-Dev-User']).toBeTruthy()
    expect(JSON.parse(init.body)).toEqual({ question: '防砂方式是什么' })
  })

  it('error 帧（带 data）→ onError 错误包；replay_truncated → onReplayTruncated', async () => {
    const onError = vi.fn()
    fetchMock.mockResolvedValueOnce(sseResponse(
      'event: error\ndata: {"code":"chat_stream_failed","message":"流内异常"}\n\n'
    ))
    const r1 = await streamChat({ path: '/chat/asks', onError })
    expect(onError).toHaveBeenCalledWith({ code: 'chat_stream_failed', message: '流内异常' })
    expect(r1.lastEventId).toBe('')

    const onReplayTruncated = vi.fn()
    fetchMock.mockResolvedValueOnce(sseResponse(
      'event: replay_truncated\ndata: {"message":"会话中断较久，中间漏了一段（超出缓冲窗口），请重新提问。","resume_point":47}\n\n'
    ))
    const r2 = await streamChat({ path: '/chat/asks', onReplayTruncated })
    expect(onReplayTruncated).toHaveBeenCalledWith(expect.objectContaining({ resume_point: 47 }))
    expect(r2.lastEventId).toBe('')
  })

  it('Last-Event-ID 头随重连形态携带；非 2xx 解统一错误包抛 ApiError（不弹 toast）', async () => {
    fetchMock.mockResolvedValueOnce(sseResponse('event: token\ndata: {"delta":"x"}\n\n'))
    await streamChat({ path: '/chat/asks', lastEventId: '41' })
    expect(fetchMock.mock.calls[0][1].headers['Last-Event-ID']).toBe('41')

    fetchMock.mockResolvedValueOnce(new Response(
      JSON.stringify({ code: 'chat_run_not_found', message: '运行不存在或已过期：run-404' }),
      { status: 404, headers: { 'Content-Type': 'application/json' } }
    ))
    await expect(streamChat({ path: '/chat/asks', body: { resume_run_id: 'run-404' } }))
      .rejects.toMatchObject({ status: 404, code: 'chat_run_not_found' })
    fetchMock.mockResolvedValueOnce(new Response(
      JSON.stringify({ code: 'chat_param_invalid', message: 'question 为空' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    ))
    await expect(streamChat({ path: '/chat/asks', body: {} })).rejects.toBeInstanceOf(ApiError)
  })
})

describe('postAsk / postResume / reconnectRun 形状（端点 4/5）', () => {
  it('postAsk：question/session_id/anchors 上送；空 sessionId/anchors 不带键', async () => {
    fetchMock.mockImplementation(async () => sseResponse(''))
    await postAsk({ question: '产量完成率怎么算', sessionId: 'sess-9', anchors: ['FAQ·产量完成率怎么算'] })
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      question: '产量完成率怎么算', session_id: 'sess-9', anchors: ['FAQ·产量完成率怎么算']
    })
    await postAsk({ question: '有效产量是多少' })
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ question: '有效产量是多少' })
  })

  it('postResume：clarify choice / approval reject+reason 形状（A1 端点 5）', async () => {
    fetchMock.mockImplementation(async () => sseResponse(''))
    await postResume('run-1', { kind: 'clarify', choice: '默认口径 B' })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/chat/runs/run-1/resume')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ kind: 'clarify', choice: '默认口径 B' })
    await postResume('run-2', { kind: 'approval', decision: 'reject', reason: '表未登记' })
    expect(fetchMock.mock.calls[1][0]).toBe('/api/chat/runs/run-2/resume')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ kind: 'approval', decision: 'reject', reason: '表未登记' })
  })

  it('reconnectRun：resume_run_id 体＋Last-Event-ID 头（断点续推，不重新执行）', async () => {
    fetchMock.mockImplementation(async () => sseResponse(''))
    await reconnectRun('run-x1', '47')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/chat/asks')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ resume_run_id: 'run-x1' })
    expect(fetchMock.mock.calls[0][1].headers['Last-Event-ID']).toBe('47')
  })
})

describe('会话读口与 @ 候选（端点 2/6 未接线替代读缝）', () => {
  it('listSessions：200 → camel 折回；失败静默 {items:[],available:false} 不抛', async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({
      items: [{ id: 'sess-0318', title: '上个月产量最高的三口井', group: '问数据 · 状态机', scenario_id: 'data-fix', updated_at: '2026-09-27T18:40:00' }],
      total: 1
    }), { status: 200 }))
    expect(await listSessions()).toEqual({
      items: [{ id: 'sess-0318', title: '上个月产量最高的三口井', group: '问数据 · 状态机', scenarioId: 'data-fix', updatedAt: '2026-09-27T18:40:00' }],
      available: true
    })

    fetchMock.mockResolvedValueOnce(new Response('not found', { status: 404 }))
    expect(await listSessions()).toEqual({ items: [], available: false })
    fetchMock.mockRejectedValueOnce(new Error('网络断'))
    expect(await listSessions()).toEqual({ items: [], available: false })
  })

  it('listAnchorCandidates：semantics 读口（指标卡＋术语）→ 端点 6 token 结晶体', async () => {
    fetchMock.mockImplementation(async url => {
      const u = String(url)
      if (u.includes('/semantics/metrics')) {
        return new Response(JSON.stringify({ items: [{ id: 3, name: '★自然递减率', slot_name: '自然递减率', def: '月：1 − q_t / q_(t−1)' }] }), { status: 200 })
      }
      if (u.includes('/semantics/terms')) {
        return new Response(JSON.stringify({ items: [{ id: 7, term: '躺井', type: '黑话', def: '停产待检泵' }] }), { status: 200 })
      }
      return new Response('{}', { status: 404 })
    })
    const list = await listAnchorCandidates()
    expect(list).toEqual([
      { type: '指标卡', name: '自然递减率', token: '指标卡·自然递减率', hint: '月：1 − q_t / q_(t−1)' },
      { type: '术语', name: '躺井', token: '术语·躺井', hint: '停产待检泵' }
    ])
    const filtered = await listAnchorCandidates({ q: '躺' })
    expect(filtered).toHaveLength(1)
    expect(filtered[0].token).toBe('术语·躺井')
  })
})
