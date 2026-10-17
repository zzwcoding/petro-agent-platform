/**
 * reconnect · 断线重连接线钉测（FE-03——specs/frontend-redesign.md「验收测试」表第 10–13 行）。
 *
 * 守什么（票面伪代码第 5 节 4 用例＋验收 11 边界集）：
 * - persist_running_run_id：session 帧 → KEY（a1v2r:runningRun）在场且含 runId；done 帧 → KEY 清除；
 * - reconnect_replays_full_stream：预置 KEY＋listRunsV2 桩 running 行 → postAskV2 桩收到
 *   {resumeRunId} 且 handlers 被喂 EB4-数-明2.json 全帧（128 帧真机）→ 会话数组该 turn 的
 *   answerText/citations/events 与 live 归约逐键相等；
 * - reconnect_404_terminal：postAskV2 桩抛 ApiError(404) → 合成 turn 在场、灰条文案
 *   「本轮已结束或不可达」、无重试（postAskV2 调用计数===1）、KEY 已清；
 * - pending_ask_restore：listRunsV2 桩 waiting_ask 行＋getRunV2 桩 pending_ask → 挂起卡渲染；
 *   选选项 → postResumeV2 桩断言 body.kind 正确；done 帧 → KEY 清除。
 *
 * 测试形态：SSE 用可注入的假事件源驱动（chatV2 四函数 vi.mock 注入桩——测试显式喂帧，
 * 照 a1v2Reducer 测试的帧序列风格）；HTTP 读口同桩——零真实网络。真帧夹具与 FE-01
 * reducer 测试同源（__fixtures__/）。
 */
/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  act, cleanup, fireEvent, render, renderHook, screen, waitFor, within
} from '@testing-library/react'

vi.mock('../../api/chatV2.js', async importOriginal => ({
  ...await importOriginal(),
  listRunsV2: vi.fn(),
  getRunV2: vi.fn(),
  postAskV2: vi.fn(),
  postResumeV2: vi.fn()
}))

import { ApiError } from '../../api/client.js'
import { getRunV2, listRunsV2, postAskV2, postResumeV2 } from '../../api/chatV2.js'
import { newTurnV2, reduceV2Frames } from '../a1v2Reducer.js'
import A1V2R from './A1V2R.jsx'
import { RUNNING_RUN_KEY, useRunningRun } from './useRunningRun.js'
import prefixFrames from './__fixtures__/EB4-A-正1-prefix.json'
import fullFrames from './__fixtures__/EB4-数-明2.json'

if (!window.matchMedia) {
  window.matchMedia = query => ({
    matches: false, media: query, onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn()
  })
}
if (!window.ResizeObserver) {
  window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }
}

/** RunListItem 行桩（新行语义——supplements=[]，BE-01 修复后 null=旧行）。 */
const runRow = (runId, status, question) => ({
  run_id: runId,
  question,
  status,
  answer: null,
  followup_of: '',
  created_at: '2026-10-17T09:12:41',
  updated_at: '2026-10-17T09:13:00',
  supplements: []
})

const setKey = (runId, question) => {
  sessionStorage.setItem(RUNNING_RUN_KEY, JSON.stringify({ runId, question, at: 1 }))
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
})
afterEach(() => {
  cleanup()
})

describe('FE-03 重连接线（R1–R4）', () => {
  it('persist_running_run_id：session 帧 → KEY 在场且含 runId；done 帧 → KEY 清除', async () => {
    setKey('run-p', '重连问句')
    vi.mocked(listRunsV2).mockResolvedValue([runRow('run-p', 'running', '重连问句')])
    let handlers = null
    vi.mocked(postAskV2).mockImplementation((_body, h) => {
      handlers = h
      return Promise.resolve({ lastEventId: '' })
    })
    render(<A1V2R />)
    await waitFor(() => expect(handlers).not.toBeNull()) // restore 已开流（replay 腿）
    sessionStorage.removeItem(RUNNING_RUN_KEY) // 清场——只认 session 帧的受理写点（R1）
    act(() => {
      handlers.onFrame({ id: '-1', event: 'session', data: { run_id: 'run-p', resume: true } })
    })
    const saved = JSON.parse(sessionStorage.getItem(RUNNING_RUN_KEY))
    expect(saved?.runId).toBe('run-p')
    expect(saved?.question).toBe('重连问句')
    act(() => {
      handlers.onFrame({ id: 9, event: 'done', data: { run_id: 'run-p' } })
      handlers.onDone()
    })
    expect(sessionStorage.getItem(RUNNING_RUN_KEY)).toBeNull() // 收口清除（R1）
  })

  it('reconnect_replays_full_stream：running 行 → postAskV2 收到 {resumeRunId}，全帧重放归一与 live 归约逐键相等', async () => {
    setKey('run-21e45912', '查一下 8 月各井的日产液量')
    vi.mocked(listRunsV2).mockResolvedValue([runRow('run-21e45912', 'running', '查一下 8 月各井的日产液量')])
    let handlers = null
    let askBody = null
    let askOpts = null
    vi.mocked(postAskV2).mockImplementation((body, h, opts) => {
      askBody = body
      handlers = h
      askOpts = opts
      return Promise.resolve({ lastEventId: '' })
    })
    const { result } = renderHook(() => useRunningRun([{
      id: 't-mock', turn: { ...newTurnV2('ask', 'mock 轮'), runId: 'run-mock' }, durationS: null
    }]))
    await act(async () => { await result.current.restoreRunning() })
    expect(askBody).toEqual({ resumeRunId: 'run-21e45912' }) // 重连底座＝postAskV2 resumeRunId 形
    expect(askOpts).toEqual({ lastEventId: '' }) // 不带头＝从头全量重放（chat.py:58-87）
    expect(vi.mocked(listRunsV2)).toHaveBeenCalledWith(100) // 行集确认（本进程注册表语义）
    expect(result.current.entries.at(-1).id).toBe('t-run-21e45912') // 推入条目在 mock 轮之后
    // 全帧重放（EB4-数-明2.json 真机 128 帧——末帧 done，保留帧回调 onDone 照发）
    act(() => {
      for (const f of fullFrames) handlers.onFrame(f)
      handlers.onDone()
    })
    const turn = result.current.entries.find(e => e.id === 't-run-21e45912').turn
    const expected = reduceV2Frames(newTurnV2('replay', '查一下 8 月各井的日产液量'), fullFrames)
    expect(turn.answerText).toBe(expected.answerText)
    expect(turn.citations).toEqual(expected.citations)
    expect(turn.events).toEqual(expected.events)
    expect(turn.runStatus).toBe('completed')
    expect(turn.closed).toBe('done')
  })

  it('reconnect_404_terminal：开流前 404 → 合成轮灰条「本轮已结束或不可达」、不重试、KEY 已清', async () => {
    setKey('run-404', '不可达问句')
    vi.mocked(listRunsV2).mockResolvedValue([runRow('run-404', 'running', '不可达问句')])
    vi.mocked(postAskV2).mockRejectedValue(new ApiError(
      404,
      { code: 'chat_run_not_found', message: 'run 不存在（或不在本进程缓冲内）：run-404' },
      'run 不存在（或不在本进程缓冲内）：run-404'
    ))
    render(<A1V2R />)
    const alert = await screen.findByTestId('error-frame-alert') // 合成轮灰条在场
    expect(alert.textContent).toContain('本轮已结束或不可达')
    expect(vi.mocked(postAskV2)).toHaveBeenCalledTimes(1) // 不悬挂不重试
    expect(sessionStorage.getItem(RUNNING_RUN_KEY)).toBeNull() // 终态清键
    // 流水线块无事件不渲染（合成轮 events 空——空态纪律整块不出）
    const synthetic = screen.getByTestId('round-t-run-404')
    expect(synthetic.querySelector('[data-testid="pipeline"]')).toBeNull()
    expect(screen.getAllByTestId(/^round-/)).toHaveLength(5) // mock 四轮＋合成轮
  })

  it('pending_ask_restore：waiting_ask 行＋pending_ask → 挂起卡渲染；选选项 → body.kind 正确；done 帧 → KEY 清', async () => {
    setKey('run-w', '挂起问句')
    vi.mocked(listRunsV2).mockResolvedValue([runRow('run-w', 'waiting_ask', '挂起问句')])
    vi.mocked(getRunV2).mockResolvedValue({
      status: 'waiting_ask',
      steps: [],
      manifest_digest: null,
      pending_ask: { kind: 'clarify', prompt: '按哪个口径统计？', options: ['按自然日', '按生产日'], detail: null }
    })
    render(<A1V2R />)
    const card = await screen.findByTestId('suspend-card') // 挂起卡还原（R4）
    expect(card.textContent).toContain('按哪个口径统计？')
    let resumeCall = null
    vi.mocked(postResumeV2).mockImplementation((runId, body, h) => {
      resumeCall = { runId, body, handlers: h }
      return Promise.resolve({ lastEventId: '' })
    })
    fireEvent.click(within(card).getByRole('button', { name: '按自然日' }))
    expect(resumeCall?.runId).toBe('run-w')
    expect(resumeCall?.body).toEqual({ kind: 'clarify', choice: '按自然日' }) // resumeBodyFromAskFrame 真通
    // 本腿新帧直进同一 reducer（session+text+done——不重启不重放：postAskV2 不在场）
    act(() => {
      resumeCall.handlers.onFrame({ id: '-1', event: 'session', data: { run_id: 'run-w', resume: true } })
      resumeCall.handlers.onFrame({ id: 7, event: 'text', data: { content: '续答正文一段。' } })
      resumeCall.handlers.onFrame({ id: 8, event: 'done', data: { run_id: 'run-w' } })
      resumeCall.handlers.onDone()
    })
    expect(vi.mocked(postAskV2)).not.toHaveBeenCalled() // resume 只消费本腿新帧
    expect(screen.getAllByTestId('round-t-run-w')).toHaveLength(1) // 续答帧落回同一轮（upsert 不另开轮）
    expect(screen.getByTestId('round-t-run-w').textContent).toContain('续答正文一段。')
    expect(sessionStorage.getItem(RUNNING_RUN_KEY)).toBeNull() // done 收口清键
  })

  it('replay_then_trailing_frames：前缀重放（27 帧无收口帧）后尾随新帧接续进同轮（验收 11 边界集「重放后可尾随新帧」）', async () => {
    setKey('run-b8e6d07c', 'W-11 井生产套管的尺寸与下深')
    vi.mocked(listRunsV2).mockResolvedValue([runRow('run-b8e6d07c', 'running', 'W-11 井生产套管的尺寸与下深')])
    let handlers = null
    vi.mocked(postAskV2).mockImplementation((_body, h) => {
      handlers = h
      return Promise.resolve({ lastEventId: '25' })
    })
    const { result } = renderHook(() => useRunningRun([{
      id: 't-mock', turn: { ...newTurnV2('ask', 'mock 轮'), runId: 'run-mock' }, durationS: null
    }]))
    await act(async () => { await result.current.restoreRunning() })
    act(() => {
      for (const f of prefixFrames) handlers.onFrame(f) // EB4-A-正1 前缀（session→…→step seq7，无 done）
    })
    let turn = result.current.entries.find(e => e.id === 't-run-b8e6d07c').turn
    expect(turn.closed).toBeNull() // 前缀无收口帧——轮在跑
    expect(turn.answerText).toBe('') // 首条答案正文帧（id=26）在前缀之外
    // 尾随新帧（eval/results/frames/EB4-A-正1.json id=26 逐字）——重放尾巴与新帧同管道天然衔接
    act(() => {
      handlers.onFrame({ id: 26, event: 'text', data: { content: 'W-11 井生产套管的尺寸与下深，来自《A-W11井完井工程报告》第一章井身结构：' } })
    })
    turn = result.current.entries.find(e => e.id === 't-run-b8e6d07c').turn
    expect(turn.answerText).toContain('A-W11井完井工程报告')
    expect(turn.closed).toBeNull() // 仍未收口——同一 handlers 管道继续消费
  })
})
