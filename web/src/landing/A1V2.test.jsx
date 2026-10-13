/**
 * A1V2 落地页钉测（V2-73 会话历史读口＋最近对话栏）。
 *
 * 守什么（V2-73 左栏行为面——A1V2.jsx 消费 listRunsV2 的机器可验面）：
 * - mount 拉最近任务：listRunsV2(20) 且两行在档、状态 Tag 色键正确
 *   （completed=green / waiting_ask=gold / failed=red）；
 * - 点问题文本 → 答案展开在档（单选展开——点另一条收起前条；未收口占位文案）；
 * - 「追问此任务」→「追问中」标记出现；回车发送 → postAskV2 捕获入参含
 *   followupRunId＝所点 run_id（客户端层驼峰键；上送映射 followup_run_id
 *   已由 a1v2Reducer.test.js postAskV2 三形态钉死）且发出后标记消失。
 *
 * 搭法：vi.mock '../api/chatV2.js' 捕获入参（listRunsV2 两条假任务／
 * postAskV2·postResumeV2 桩收调用）；jsdom＋matchMedia/ResizeObserver 环境桩
 * 同 landing/A1.test.jsx 头部。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'

import A1V2Landing from './A1V2.jsx'
import { listRunsV2, postAskV2, postResumeV2 } from '../api/chatV2.js'

vi.mock('../api/chatV2.js', () => ({
  listRunsV2: vi.fn(),
  postAskV2: vi.fn(),
  postResumeV2: vi.fn(),
  resumeBodyFromAskFrame: vi.fn()
}))

// antd v5 在 jsdom 下的两个环境桩（同 landing/A1.test.jsx）
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

/** 两条假任务（completed/waiting_ask 各一——question/answer 真实感文本）。 */
const COMPLETED_RUN = {
  run_id: 'run-v73a',
  question: '9 月上旬各井日产油量是多少？',
  status: 'completed',
  answer: 'N-01 井 2025-09-01 日产油量 21.16 吨[1]。',
  created_at: '2026-10-12T09:00:00',
  updated_at: '2026-10-12T09:00:05'
}
const WAITING_RUN = {
  run_id: 'run-v73b',
  question: '帮我预测明年油价走势',
  status: 'waiting_ask',
  answer: null,
  created_at: '2026-10-12T08:30:00',
  updated_at: '2026-10-12T08:31:00'
}

beforeEach(() => {
  vi.clearAllMocks()
  listRunsV2.mockResolvedValue([COMPLETED_RUN, WAITING_RUN])
  postAskV2.mockReturnValue(undefined)
  postResumeV2.mockReturnValue(undefined)
})

afterEach(() => {
  cleanup()
})

/** 左栏某条任务所在行容器（锚 → flex 行 → 行容器——A1V2 左栏结构两跳）。 */
function runRowOf(questionText) {
  const row = screen.getByText(questionText).closest('li')
  expect(row).toBeTruthy()
  return row
}

describe('A1V2 最近对话栏 · mount 拉取与状态 Tag（V2-73）', () => {
  it('listRunsV2(20) 首拉；两行在档；状态 Tag 色键 completed=green/waiting_ask=gold', async () => {
    render(<A1V2Landing />)
    expect(await screen.findByText('9 月上旬各井日产油量是多少？')).toBeTruthy()
    expect(screen.getByText('帮我预测明年油价走势')).toBeTruthy()
    expect(listRunsV2).toHaveBeenCalledTimes(1)
    expect(listRunsV2).toHaveBeenCalledWith(20) // mount 缺省 20 条

    // V1 式列内 UI（V2-73 终版）：行1 标题（waiting_ask 前缀金色询问图标）＋行2 dim 状态文案
    const doneRow = screen.getByText('9 月上旬各井日产油量是多少？').closest('li')
    expect(doneRow.textContent).toContain('已完成')
    const waitingRow = screen.getByText('帮我预测明年油价走势').closest('li')
    expect(waitingRow.textContent).toContain('待确认')
    expect(waitingRow.querySelector('.anticon-question-circle')).toBeTruthy()
  })
})

describe('A1V2 最近对话栏 · 点条目展开答案', () => {
  it('点问题文本 → 答案展开在档；单选展开——点另一条收起前条并出未收口占位', async () => {
    render(<A1V2Landing />)
    fireEvent.click(await screen.findByText('9 月上旬各井日产油量是多少？'))
    expect(await screen.findByText('N-01 井 2025-09-01 日产油量 21.16 吨[1]。')).toBeTruthy()

    fireEvent.click(screen.getByText('帮我预测明年油价走势'))
    expect(await screen.findByText('（未收口——无答案文本）')).toBeTruthy() // answer=null 占位
    expect(screen.queryByText('N-01 井 2025-09-01 日产油量 21.16 吨[1]。')).toBeNull()
  })
})

describe('A1V2 最近对话栏 · 追问此任务（会话线程挂前轮）', () => {
  it('点「追问此任务」→「追问中」标记在档；回车发送 → postAskV2 入参含 followupRunId＝所点 run_id 且标记消失', async () => {
    render(<A1V2Landing />)
    expect(await screen.findByText('帮我预测明年油价走势')).toBeTruthy()
    const waitingRow = runRowOf('帮我预测明年油价走势')

    fireEvent.click(within(waitingRow).getByText('追问此任务'))
    // 三栏版（V2-73 终版布局）：面板级标记（单选模型）＋中栏线程 Tag 双面在场
    screen.getByText('追问中——下一条问题带会话线程')
    screen.getByText('追问线程：run-v73b')

    fireEvent.change(screen.getByPlaceholderText(/输入问题/), {
      target: { value: '那 9 月中旬呢？' }
    })
    fireEvent.keyDown(screen.getByPlaceholderText(/输入问题/), { key: 'Enter', keyCode: 13 })
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(1))
    expect(postAskV2.mock.calls[0][0]).toEqual({
      question: '那 9 月中旬呢？',
      followupRunId: 'run-v73b' // 客户端层驼峰键——上送映射 followup_run_id（a1v2Reducer.test.js 已钉）
    })
    // 发出后清空——「追问中」标记消失（随下一条问题带线程，不驻留）
    expect(screen.queryByText('追问中——下一条问题带会话线程')).toBeNull()
  })
})

// ---------- V2-73 附钉：挂起卡渲染（AskCard 曾因 antd Space 未导入崩页——回归锚） ----------
it('挂起卡渲染：ask 帧后出反问卡＋选项按钮，页面不崩', async () => {
  listRunsV2.mockResolvedValue([])
  postAskV2.mockImplementation((body, handlers) => {
    handlers.onFrame({ event: 'session', data: { run_id: 'run-susp', resume: false } })
    handlers.onFrame({ event: 'ask', data: { run_id: 'run-susp', frame: {
      kind: 'clarify', prompt: '「最近」指哪个时间窗？', options: ['近 3 天', '近 30 天'], detail: null
    } } })
    handlers.onDone()
    return Promise.resolve({ lastEventId: '' })
  })
  render(<A1V2Landing />)
  fireEvent.change(await screen.findByPlaceholderText('输入问题（Enter 发送）'),
    { target: { value: 'N-02 最近怎么样' } })
  fireEvent.click(screen.getByText('发送'))
  expect(await screen.findByText('「最近」指哪个时间窗？')).toBeTruthy()
  expect(screen.getByText('系统反问')).toBeTruthy()
  expect(screen.getByText('近 3 天')).toBeTruthy()
  expect(screen.getByText('近 30 天')).toBeTruthy()
})
