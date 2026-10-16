/**
 * A1V2 落地页钉测（对话任务状态机——V2-74 对话任务面，ZCode 会话式交互）。
 *
 * 守什么（A1V2.jsx 交互面——机器可验）：
 * - mount 拉最近任务 listRunsV2(20)；对话行在档、状态文案与 waiting_ask 金色询问图标；
 * - V2-74 分组：followup_of 链分组＝一链一行（行＝链根问句标题；行 2＝最新轮状态/轮数/
 *   时间，最近活跃在前）；链根不在窗内＝自成一对话（窗界兜底）；
 * - 打开对话（整行点击）：行高亮（data-selected）、中栏全轮次连续呈现（问＋答＋状态；
 *   未收口占位/挂起轮批准/驳回卡）、右栏拉最新轮 getRunV2 steps（两态切换——实时回合
 *   过程帧优先）；
 * - 续聊（选中即对话）：placeholder 换追问形「追问此对话」；发送 postAskV2 入参带
 *   followupRunId＝对话内最新收口轮（客户端层驼峰键——上送映射 followup_run_id 由
 *   a1v2Reducer.test.js 钉死）；锚随收口推进（下一发跟进新锚——链式追问）；
 *   「＋新会话」（左栏头部）＝唯一显式退出对话入口——清对话选中＋实时流＋锚；
 * - 未收口对话（全链无 completed 轮）不武装锚（后端 _seed_history：非 completed 409）——
 *   指示区如实说明「当前输入＝新会话」＋发送不带线程＋挂起轮批准/驳回在场（批准＝
 *   postResumeV2 审批回流）；
 * - 追问回合收口态闸（第 2 轮评审 medium 两钉）：追问轮挂起（ask 帧在场）→锚立即拆
 *   （placeholder 复位，done 不复活，下一发不带线程键）；追问轮流内失败→锚保持原
 *   completed run（placeholder 仍追问形、下一发仍带原锚 followupRunId）；失败腿左栏复拉
 *   （settleTurn 统一出口——成功/失败/传输断/预流错误全腿同闸）；
 * - 右栏 getRunV2 失败→错误 Alert 内联且不出假步数；列表读口失败→计数行撤下（失败态≠
 *   空库「共 0 个对话」，UI-14 同位纪律）；
 * - 挂起卡渲染回归锚（AskCard 曾因 antd Space 未导入崩页）。
 *
 * 搭法：vi.mock '../api/chatV2.js' 捕获入参（listRunsV2 假任务列／getRunV2 steps 桩／
 * postAskV2·postResumeV2 桩收调用）；jsdom＋matchMedia/ResizeObserver 环境桩同
 * landing/A1.test.jsx 头部。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'

import A1V2Landing from './A1V2.jsx'
import { ApiError } from '../api/client.js'
import { getRunV2, listRunsV2, postAskV2, postResumeV2 } from '../api/chatV2.js'

vi.mock('../api/chatV2.js', () => ({
  listRunsV2: vi.fn(),
  postAskV2: vi.fn(),
  postResumeV2: vi.fn(),
  resumeBodyFromAskFrame: vi.fn(),
  getRunV2: vi.fn()
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

/** 假任务列（completed/waiting_ask 各一——question/answer 真实感文本；followup_of 空＝各自成对话）。 */
const COMPLETED_RUN = {
  run_id: 'run-v73a',
  question: '9 月上旬各井日产油量是多少？',
  status: 'completed',
  answer: 'N-01 井 2025-09-01 日产油量 21.16 吨[1]。',
  followup_of: '',
  created_at: '2026-10-12T09:00:00',
  updated_at: '2026-10-12T09:00:05'
}
const WAITING_RUN = {
  run_id: 'run-v73b',
  question: '帮我预测明年油价走势',
  status: 'waiting_ask',
  answer: null,
  followup_of: '',
  created_at: '2026-10-12T08:30:00',
  updated_at: '2026-10-12T08:31:00'
}

/** getRunV2 桩的 steps（形同 appv2/api/chat.py StepView：seq/step/status/title/manifest/payload）。 */
const RUN_STEPS = [
  { seq: 1, step: 'decision', status: 'ok', title: '问有效产量是多少。', manifest: null, payload: null },
  { seq: 2, step: 'decision', status: 'ok', title: '澄清 r1：分解 1 子问题', manifest: null, payload: null }
]

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear() // V2-78 持久化随变随写——每测清场（跨测不串现场）
  listRunsV2.mockResolvedValue([COMPLETED_RUN, WAITING_RUN])
  getRunV2.mockResolvedValue({ status: 'completed', steps: RUN_STEPS, manifest_digest: 'sha256:abc' })
  postAskV2.mockReturnValue(undefined)
  postResumeV2.mockReturnValue(undefined)
})

afterEach(() => {
  cleanup()
})

/** 左栏某条任务所在行（question 文本选中后同时在中栏回放卡——行 li 是唯一锚）。 */
function runRowOf(questionText) {
  const row = screen.getAllByText(questionText).map(m => m.closest('li')).find(Boolean)
  expect(row).toBeTruthy()
  return row
}

/** 点左栏行（行内 question 文本节点冒泡到整行 onClick）。 */
function clickRunRow(questionText) {
  fireEvent.click(within(runRowOf(questionText)).getByText(questionText))
}

/** 回车发送（IME 守卫绕过——keyCode 13 直发）。 */
function pressEnter(input) {
  fireEvent.keyDown(input, { key: 'Enter', keyCode: 13 })
}

// antd v5 Button 双字 CJK 自动插空格（「批准」渲染为「批 准」）——按钮文本断言统一走此匹配
//（锚定全串：提示行「批准/驳回续推后可追问」里的裸「批准」不误中）
const approveBtn = () => screen.getByText(/^批\s*准$/)
const rejectBtn = () => screen.getByText(/^驳\s*回$/)

describe('A1V2 历史对话栏 · mount 拉取与行状态（V2-73）', () => {
  it('listRunsV2(20) 首拉；两行在档＋状态文案＋waiting_ask 金色询问图标；行内无「追问此任务」链接（R1）', async () => {
    render(<A1V2Landing />)
    expect(await screen.findByText('9 月上旬各井日产油量是多少？')).toBeTruthy()
    expect(screen.getByText('帮我预测明年油价走势')).toBeTruthy()
    expect(listRunsV2).toHaveBeenCalledTimes(1)
    expect(listRunsV2).toHaveBeenCalledWith(20) // mount 缺省 20 条
    expect(screen.getByText('共 2 个对话')).toBeTruthy() // 数据在位→计数行渲染（失败态撤下，另钉）

    // V1 式列内 UI：行1 标题（waiting_ask 前缀金色询问图标）＋行2 dim 状态文案
    const doneRow = runRowOf('9 月上旬各井日产油量是多少？')
    expect(doneRow.textContent).toContain('已完成')
    const waitingRow = runRowOf('帮我预测明年油价走势')
    expect(waitingRow.textContent).toContain('待确认')
    expect(waitingRow.querySelector('.anticon-question-circle')).toBeTruthy()

    // R1：整行点击＝选中——「追问此任务」链接已删
    expect(screen.queryByText('追问此任务')).toBeNull()
    // 未选中态：两行 data-selected=false（高亮与未选中可辨）
    expect(doneRow.dataset.selected).toBe('false')
    expect(waitingRow.dataset.selected).toBe('false')
  })
})

describe('A1V2 · 打开对话（整行点击＝行高亮＋中栏全轮次＋右栏最新轮过程步）', () => {
  it('点 completed 对话行：行高亮翻面；中栏全轮次（问＋答＋状态徽标）；右栏「历史过程」＝getRunV2 steps 渲染；无回放横幅', async () => {
    render(<A1V2Landing />)
    await screen.findByText('9 月上旬各井日产油量是多少？')
    const doneRow = runRowOf('9 月上旬各井日产油量是多少？')
    const waitingRow = runRowOf('帮我预测明年油价走势')

    fireEvent.click(doneRow)
    // 选中行高亮（data-selected 互斥翻面）
    expect(doneRow.dataset.selected).toBe('true')
    expect(waitingRow.dataset.selected).toBe('false')
    // 中栏全轮次：问题＋答案全文（listRunsV2 answer 字段）——无「只读回放」横幅（对话可直接续聊）
    expect(await screen.findByText('N-01 井 2025-09-01 日产油量 21.16 吨[1]。')).toBeTruthy()
    expect(screen.queryByText(/只读回放/)).toBeNull()
    // 轮次卡状态徽标与左栏同词表（STATUS_TEXT 单源——中文词非英文原码）
    const answerCard = screen.getByText('N-01 井 2025-09-01 日产油量 21.16 吨[1]。').closest('.ant-card')
    expect(within(answerCard).getByText('已完成')).toBeTruthy()

    // 右栏切历史过程态：getRunV2 以最新轮 run_id 调用，steps（seq/title/step）渲染
    await waitFor(() => expect(getRunV2).toHaveBeenCalledWith('run-v73a'))
    expect(await screen.findByText('历史过程 · run-v73a')).toBeTruthy()
    expect(await screen.findByText('2 步')).toBeTruthy() // 步数只在加载落定后出（加载中不显假「0 步」）
    expect(screen.getByText('澄清 r1：分解 1 子问题')).toBeTruthy()
  })

  it('单选模型：点另一对话收起前条（未收口占位＋「暂无已收口轮」说明）且高亮跟着翻面', async () => {
    render(<A1V2Landing />)
    await screen.findByText('9 月上旬各井日产油量是多少？')
    clickRunRow('9 月上旬各井日产油量是多少？')
    expect(await screen.findByText('N-01 井 2025-09-01 日产油量 21.16 吨[1]。')).toBeTruthy()

    clickRunRow('帮我预测明年油价走势') // 问题文本已在轮次卡同现——行 li 锚定点击
    expect(await screen.findByText('（未收口——无答案文本）')).toBeTruthy() // answer=null 占位
    expect(screen.queryByText('N-01 井 2025-09-01 日产油量 21.16 吨[1]。')).toBeNull()
    // 轮次卡状态徽标同词表（waiting_ask → 待确认）
    const waitCard = screen.getByText('（未收口——无答案文本）').closest('.ant-card')
    expect(within(waitCard).getByText('待确认')).toBeTruthy()
    // 全链无收口轮＝锚无从武装——如实说明（后端 followup 前轮须 completed）
    expect(screen.getByText('本对话暂无已收口轮——追问不可用；当前输入＝新会话。')).toBeTruthy()
    expect(runRowOf('帮我预测明年油价走势').dataset.selected).toBe('true')
    expect(runRowOf('9 月上旬各井日产油量是多少？').dataset.selected).toBe('false')
  })

  it('右栏两态切换：实时回合过程帧优先；打开对话切历史 steps；续发追问实时帧回归', async () => {
    let h = null
    postAskV2.mockImplementation((body, handlers) => { h = handlers; return Promise.resolve({ lastEventId: '' }) })
    render(<A1V2Landing />)
    // 实时回合：右栏出实时过程帧
    fireEvent.change(await screen.findByPlaceholderText('输入问题（Enter 发送）'),
      { target: { value: '有效产量是多少' } })
    fireEvent.click(screen.getByText('发送'))
    h.onFrame({ event: 'session', data: { run_id: 'run-live', resume: false } })
    h.onFrame({ event: 'step', data: { step: 'decision', seq: 1, title: '问有效产量是多少。' } })
    h.onDone()
    expect(await screen.findByText('1 步 · 0 次工具 · 0 支材料 · 0 引')).toBeTruthy()
    expect(screen.getByText('问有效产量是多少。')).toBeTruthy()

    // 打开对话 → 右栏切「历史过程」态（getRunV2 steps；实时流清零）
    clickRunRow('9 月上旬各井日产油量是多少？')
    expect(await screen.findByText('历史过程 · run-v73a')).toBeTruthy()
    expect(screen.getByText('澄清 r1：分解 1 子问题')).toBeTruthy()

    // 续发追问 → 实时过程帧回归（两态切换）
    const inp = screen.getByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(inp, { target: { value: '那下旬呢？' } })
    pressEnter(inp)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(2))
    h.onFrame({ event: 'session', data: { run_id: 'run-live2', resume: false } })
    h.onFrame({ event: 'step', data: { step: 'decision', seq: 1, title: '问下旬日产油量。' } })
    expect(await screen.findByText('1 步 · 0 次工具 · 0 支材料 · 0 引')).toBeTruthy()
  })

  it('右栏 getRunV2 失败→错误 Alert 内联且不出假步数；重开对话＝放行重拉成功', async () => {
    getRunV2.mockRejectedValueOnce(new ApiError(404, { code: 'chat_run_not_found' }, '运行不存在：run-v73a'))
    render(<A1V2Landing />)
    await screen.findByText('9 月上旬各井日产油量是多少？')
    clickRunRow('9 月上旬各井日产油量是多少？')
    expect(await screen.findByText(/运行不存在：run-v73a/)).toBeTruthy() // errText 内联（message · code）
    expect(screen.queryByText(/^\d+ 步$/)).toBeNull() // 失败态不出假步数

    // 重开对话→重新拉取成功→步数与 steps 落定
    getRunV2.mockResolvedValue({ status: 'completed', steps: RUN_STEPS, manifest_digest: null })
    clickRunRow('9 月上旬各井日产油量是多少？')
    expect(await screen.findByText('2 步')).toBeTruthy()
    expect(getRunV2).toHaveBeenCalledTimes(2)
  })
})

describe('A1V2 · V2-74 对话任务分组（followup_of 链＝一链一行）', () => {
  const FOLLOWUP_RUN = {
    run_id: 'run-fu1',
    question: '那中旬呢？',
    status: 'completed',
    answer: 'N-01 井 2025-09-15 日产油量 19.8 吨[1]。',
    followup_of: 'run-v73a',
    created_at: '2026-10-12T10:00:00',
    updated_at: '2026-10-12T10:00:05'
  }

  it('链分组：追问轮并入链根行（一链一行）——行标题＝链根问句、行 2＝2 轮；最近活跃在前', async () => {
    listRunsV2.mockResolvedValue([FOLLOWUP_RUN, COMPLETED_RUN, WAITING_RUN])
    render(<A1V2Landing />)
    expect(await screen.findByText('共 2 个对话')).toBeTruthy() // 三 run 两链
    // 链根行：标题＝链根问句（非追问轮问句）；行 2＝2 轮
    const rootRow = runRowOf('9 月上旬各井日产油量是多少？')
    expect(rootRow.textContent).toContain('2 轮')
    expect(rootRow.textContent).toContain('已完成')
    expect(screen.queryByText('那中旬呢？')).toBeNull() // 追问轮不单列——并入链根行
    // 最近活跃在前：链根行（最新轮 10:00）排在 waiting 行（08:30）前
    const rows = [...document.querySelectorAll('li[data-selected]')]
    expect(rows[0].textContent).toContain('9 月上旬各井日产油量是多少？')
    expect(rows[1].textContent).toContain('帮我预测明年油价走势')
  })

  it('打开两轮对话：中栏全轮次按序呈现（链根＋追问）；右栏拉最新轮；发送锚＝最新收口轮', async () => {
    listRunsV2.mockResolvedValue([FOLLOWUP_RUN, COMPLETED_RUN, WAITING_RUN])
    postAskV2.mockImplementation(() => Promise.resolve({ lastEventId: '' }))
    render(<A1V2Landing />)
    await screen.findByText('共 2 个对话') // 列表落定再点行
    clickRunRow('9 月上旬各井日产油量是多少？')
    // 全轮次按序：链根问答在前、追问轮在后
    expect(await screen.findByText('N-01 井 2025-09-01 日产油量 21.16 吨[1]。')).toBeTruthy()
    expect(screen.getByText('N-01 井 2025-09-15 日产油量 19.8 吨[1]。')).toBeTruthy()
    expect(screen.getByText('对话 · 2 轮 —— 输入默认继续本对话')).toBeTruthy()
    // 右栏＝最新轮（追问轮）过程步
    await waitFor(() => expect(getRunV2).toHaveBeenCalledWith('run-fu1'))
    // 发送锚＝对话内最新收口轮（追问轮 run-fu1）
    const inp = screen.getByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(inp, { target: { value: '那下旬呢？' } })
    pressEnter(inp)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(1))
    expect(postAskV2.mock.calls[0][0]).toEqual({ question: '那下旬呢？', followupRunId: 'run-fu1' })
  })
})

describe('A1V2 · R4 续聊（选中即对话——输入默认追问该对话）', () => {
  it('打开对话→placeholder 换追问形；发送带 followupRunId＝锚 run；收口锚推进（下一发跟进新锚——链式追问）', async () => {
    let h = null
    postAskV2.mockImplementation((body, handlers) => { h = handlers; return Promise.resolve({ lastEventId: '' }) })
    render(<A1V2Landing />)
    await screen.findByText('9 月上旬各井日产油量是多少？')
    clickRunRow('9 月上旬各井日产油量是多少？')
    // R4：对话打开即续聊态（无 Tag／退出链接——V2-74 全轮次视图即上下文）
    expect(screen.queryByText(/追问线程/)).toBeNull()
    expect(screen.queryByText('退出线程，开新会话')).toBeNull()
    expect(await screen.findByPlaceholderText('追问此对话（Enter 发送）')).toBeTruthy()

    const askInput = screen.getByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(askInput, { target: { value: '那 9 月中旬呢？' } })
    pressEnter(askInput)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(1))
    expect(postAskV2.mock.calls[0][0]).toEqual({
      question: '那 9 月中旬呢？',
      followupRunId: 'run-v73a' // 客户端层驼峰键——上送映射 followup_run_id（a1v2Reducer.test.js 已钉）
    })

    // session 帧→收口判据就位；done 帧且本腿无挂起＝新 run 已收口→锚推进（下一发跟进新锚）
    h.onFrame({ event: 'session', data: { run_id: 'run-next', resume: false } })
    h.onFrame({ event: 'done', data: { run_id: 'run-next' } })
    h.onDone() // 流收束→左栏复拉
    await waitFor(() => expect(listRunsV2).toHaveBeenCalledTimes(2))

    // 第二发跟进新锚——链式追问历史不断链
    const askInput2 = screen.getByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(askInput2, { target: { value: '那下旬呢？' } })
    pressEnter(askInput2)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(2))
    expect(postAskV2.mock.calls[1][0]).toEqual({ question: '那下旬呢？', followupRunId: 'run-next' })
  })

  it('＋新会话一键回新会话：清实时流＋回放＋线程锚；后续发送不带 followupRunId', async () => {
    render(<A1V2Landing />)
    fireEvent.click(await screen.findByText('9 月上旬各井日产油量是多少？'))
    expect(await screen.findByPlaceholderText('追问此对话（Enter 发送）')).toBeTruthy()

    // 左栏头部「＋新会话」＝唯一显式退出对话入口
    fireEvent.click(screen.getByText('＋新会话'))
    expect(screen.getByText(/输入问题开始/)).toBeTruthy() // 实时流清空回空态
    expect(screen.getByPlaceholderText('输入问题（Enter 发送）')).toBeTruthy()

    const askInput = screen.getByPlaceholderText('输入问题（Enter 发送）')
    fireEvent.change(askInput, { target: { value: '新问题' } })
    pressEnter(askInput)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(1))
    expect(postAskV2.mock.calls[0][0]).toEqual({ question: '新问题' }) // 无 followupRunId 键
  })

  it('V2-78 链连续（独立首问也武装）：无锚首问收口→锚推进到它；下一发并入本对话带 followupRunId', async () => {
    let h = null
    postAskV2.mockImplementation((body, handlers) => { h = handlers; return Promise.resolve({ lastEventId: '' }) })
    render(<A1V2Landing />)
    // 独立首问（无锚——真机分家实录 19:31→19:32 的修复面）
    const inp = await screen.findByPlaceholderText('输入问题（Enter 发送）')
    fireEvent.change(inp, { target: { value: '查一下井的数据' } })
    pressEnter(inp)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(1))
    expect(postAskV2.mock.calls[0][0]).toEqual({ question: '查一下井的数据' }) // 首问无键
    h.onFrame({ event: 'session', data: { run_id: 'run-root1', resume: false } })
    h.onFrame({ event: 'done', data: { run_id: 'run-root1' } })
    h.onDone()
    // 收口→锚武装到首问 run：下一发带 followupRunId（不再分家）
    const inp2 = await screen.findByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(inp2, { target: { value: '查一下 日常油' } })
    pressEnter(inp2)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(2))
    expect(postAskV2.mock.calls[1][0]).toEqual({ question: '查一下 日常油', followupRunId: 'run-root1' })
  })

  it('V2-77 理解旁白灰条：kind=understanding 的 text 帧→「系统理解」折叠条独立在档，答案面不再混入旁白', async () => {
    let h = null
    postAskV2.mockImplementation((body, handlers) => { h = handlers; return Promise.resolve({ lastEventId: '' }) })
    render(<A1V2Landing />)
    const inp = await screen.findByPlaceholderText('输入问题（Enter 发送）')
    fireEvent.change(inp, { target: { value: '你好啊' } })
    pressEnter(inp)
    h.onFrame({ event: 'session', data: { run_id: 'run-u', resume: false } })
    h.onFrame({ event: 'text', data: { content: '用户发出问候「你好啊」。', kind: 'understanding' } })
    h.onFrame({ event: 'text', data: { content: '您好！请问想查什么油田数据？' } })
    h.onFrame({ event: 'done', data: { run_id: 'run-u' } })
    // 折叠头在档；旁白收进折叠体（antd 惰性挂载——收起态不在 DOM＝不与答案混排，
    // 旧混排形下答案节点是「旁白＋答案」拼接串、此断言必失败）；答案独立成块。
    expect(await screen.findByText('系统理解')).toBeTruthy()
    expect(screen.queryByText('用户发出问候「你好啊」。')).toBeNull()
    expect(screen.getByText('您好！请问想查什么油田数据？')).toBeTruthy()
  })

  it('追问轮挂起（ask 帧在场）→线程立即拆：指示消失＋placeholder 复位；done 不复活；下一发不带线程键', async () => {
    let h = null
    postAskV2.mockImplementation((body, handlers) => { h = handlers; return Promise.resolve({ lastEventId: '' }) })
    render(<A1V2Landing />)
    await screen.findByText('9 月上旬各井日产油量是多少？')
    clickRunRow('9 月上旬各井日产油量是多少？')
    expect(await screen.findByPlaceholderText('追问此对话（Enter 发送）')).toBeTruthy()

    const askInput = screen.getByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(askInput, { target: { value: '那 9 月中旬呢？' } })
    pressEnter(askInput)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(1))

    h.onFrame({ event: 'session', data: { run_id: 'run-susp2', resume: false } })
    h.onFrame({ event: 'ask', data: { run_id: 'run-susp2', frame: {
      kind: 'clarify', prompt: '请确认范围', options: ['按产量改问'], detail: null
    } } })
    // ask 帧在场＝挂起——锚不得停在未收口 run：回锚原收口轮（对话保持武装，续推走挂起卡）
    expect(await screen.findByText('请确认范围')).toBeTruthy()

    // 挂起腿 done 照发——锚保持原收口轮（V2-78：挂起后输入仍并本链，不锚未收口轮）
    h.onFrame({ event: 'done', data: { run_id: 'run-susp2' } })
    h.onDone()
    const inp2 = screen.getByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(inp2, { target: { value: '换个问法' } })
    pressEnter(inp2)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(2))
    expect(postAskV2.mock.calls[1][0]).toEqual({
      question: '换个问法', followupRunId: 'run-v73a', // 必失败循环切断——不锚未收口轮
    })
  })

  it('追问轮流内失败→锚保持原 completed run（不停在失败 run 上）：指示仍武装＋下一发仍带原锚；失败腿左栏复拉', async () => {
    let h = null
    postAskV2.mockImplementation((body, handlers) => { h = handlers; return Promise.resolve({ lastEventId: '' }) })
    render(<A1V2Landing />)
    await screen.findByText('9 月上旬各井日产油量是多少？')
    clickRunRow('9 月上旬各井日产油量是多少？')
    expect(await screen.findByPlaceholderText('追问此对话（Enter 发送）')).toBeTruthy()

    const askInput = screen.getByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(askInput, { target: { value: '那 9 月中旬呢？' } })
    pressEnter(askInput)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(1))

    h.onFrame({ event: 'session', data: { run_id: 'run-fail', resume: false } })
    h.onError({ message: '流内异常' })
    // 失败不拆线程：锚保持原 completed run（run-v73a）——placeholder 仍追问形，重试仍打同一线程
    expect(screen.getByPlaceholderText('追问此对话（Enter 发送）')).toBeTruthy()
    // 失败腿左栏复拉（失败 run 已落库——最需回看过程步的对象；settleTurn 统一出口）
    await waitFor(() => expect(listRunsV2).toHaveBeenCalledTimes(2))

    const inp2 = screen.getByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(inp2, { target: { value: '再试一次' } })
    pressEnter(inp2)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(2))
    expect(postAskV2.mock.calls[1][0]).toEqual({ question: '再试一次', followupRunId: 'run-v73a' })
  })

  it('追问轮引擎异常腿（run_failed notice 随行、流尾照发 done）→锚保持原 completed run：卡面告警＋下一发仍带原锚', async () => {
    let h = null
    postAskV2.mockImplementation((body, handlers) => { h = handlers; return Promise.resolve({ lastEventId: '' }) })
    render(<A1V2Landing />)
    await screen.findByText('9 月上旬各井日产油量是多少？')
    clickRunRow('9 月上旬各井日产油量是多少？')
    expect(await screen.findByPlaceholderText('追问此对话（Enter 发送）')).toBeTruthy()

    const askInput = screen.getByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(askInput, { target: { value: '那 9 月中旬呢？' } })
    pressEnter(askInput)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(1))

    // 引擎异常腿实录形：executor 落库 failed 发 run_failed notice，bus 干净收束、桥面照发 done
    h.onFrame({ event: 'session', data: { run_id: 'run-engfail', resume: false } })
    h.onFrame({ event: 'notice', data: { type: 'run_failed', gates: [], content: 'run 执行失败：引擎异常' } })
    h.onFrame({ event: 'done', data: { run_id: 'run-engfail' } })
    h.onDone()
    // 卡面如实告警（engineFailed Alert——不再只有一行灰 notice；notice 行与 Alert 同文双在）
    await waitFor(() => {
      const el = document.querySelector('.ant-alert-error')
      expect(el).toBeTruthy()
      expect(el.textContent).toContain('run 执行失败：引擎异常')
    })
    // 锚不推进到 failed run：placeholder 仍追问形（409 循环不残腿）＋下一发仍带原锚
    expect(screen.getByPlaceholderText('追问此对话（Enter 发送）')).toBeTruthy()

    const inp2 = screen.getByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(inp2, { target: { value: '再试一次' } })
    pressEnter(inp2)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(2))
    expect(postAskV2.mock.calls[1][0]).toEqual({ question: '再试一次', followupRunId: 'run-v73a' })
  })
})

describe('A1V2 · 未收口任务不武装线程（后端 followup 前轮须 completed）', () => {
  it('点 waiting_ask 对话行：指示区如实说明「当前输入＝新会话」；发送不带线程；挂起轮批准/驳回在场（批准＝审批回流）', async () => {
    getRunV2.mockResolvedValue({ status: 'waiting_ask', steps: [], manifest_digest: null })
    render(<A1V2Landing />)
    fireEvent.click(await screen.findByText('帮我预测明年油价走势'))

    expect(await screen.findByText('本对话暂无已收口轮——追问不可用；当前输入＝新会话。')).toBeTruthy()
    expect(screen.queryByPlaceholderText('追问此对话（Enter 发送）')).toBeNull() // 不武装线程
    expect(screen.getByPlaceholderText('输入问题（Enter 发送）')).toBeTruthy() // placeholder 不换追问形
    await waitFor(() => expect(getRunV2).toHaveBeenCalledWith('run-v73b')) // 右栏仍拉该轮 steps

    // 挂起轮卡（对话视图审批按钮）在场——antd 双字 CJK 按钮自动插空格（批 准）
    expect(screen.getByText('该轮挂起待确认')).toBeTruthy()
    expect(approveBtn()).toBeTruthy()
    expect(rejectBtn()).toBeTruthy()

    // 发送不带 followupRunId
    const askInput = screen.getByPlaceholderText('输入问题（Enter 发送）')
    fireEvent.change(askInput, { target: { value: '换个问法' } })
    pressEnter(askInput)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(1))
    expect(postAskV2.mock.calls[0][0]).toEqual({ question: '换个问法' })
  })

  it('V2-78 挂起帧还原：getRunV2 带 pending_ask(clarify)→对话视图出系统反问＋选项；点选项即 clarify 续推', async () => {
    getRunV2.mockResolvedValue({
      status: 'waiting_ask', steps: [], manifest_digest: null,
      pending_ask: { kind: 'clarify', prompt: '请确认时间窗', options: ['近 3 天', '近 30 天'], detail: null }
    })
    render(<A1V2Landing />)
    await screen.findByText('帮我预测明年油价走势')
    clickRunRow('帮我预测明年油价走势')
    // 反问卡（非批准/驳回形）——刷新后选项由此还原
    expect(await screen.findByText('系统反问')).toBeTruthy()
    expect(screen.getByText('请确认时间窗')).toBeTruthy()
    fireEvent.click(screen.getByText('近 3 天'))
    await waitFor(() => expect(postResumeV2).toHaveBeenCalledTimes(1))
    expect(postResumeV2.mock.calls[0][0]).toBe('run-v73b')
    expect(postResumeV2.mock.calls[0][1]).toEqual({ kind: 'clarify', choice: '近 3 天' })
  })

  it('V2-78 刷新现场恢复：sessionStorage 有对话选中→mount 即还原对话视图＋锚（追问并原链）', async () => {
    sessionStorage.setItem('a1v2.session', JSON.stringify({
      rootId: 'run-v73a',
      followup: { runId: 'run-v73a', label: '9 月上旬各井日产油量是多少？' }
    }))
    postAskV2.mockImplementation(() => Promise.resolve({ lastEventId: '' }))
    render(<A1V2Landing />)
    // 对话视图直接还原（无需再点行）
    expect(await screen.findByText(/对话 · 1 轮/)).toBeTruthy()
    const inp = screen.getByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(inp, { target: { value: '继续聊' } })
    pressEnter(inp)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(1))
    expect(postAskV2.mock.calls[0][0]).toEqual({ question: '继续聊', followupRunId: 'run-v73a' })
    sessionStorage.removeItem('a1v2.session')
  })

  it('对话视图挂起轮批准→postResumeV2 审批回流（转实时续推回合）；续推收口→锚回武装（下一发跟进该对话）', async () => {
    getRunV2.mockResolvedValue({ status: 'waiting_ask', steps: [], manifest_digest: null })
    let h = null
    postResumeV2.mockImplementation((runId, body, handlers) => { h = handlers; return Promise.resolve({ lastEventId: '' }) })
    render(<A1V2Landing />)
    await screen.findByText('帮我预测明年油价走势')
    clickRunRow('帮我预测明年油价走势')
    await waitFor(() => expect(approveBtn()).toBeTruthy())
    fireEvent.click(approveBtn())
    await waitFor(() => expect(postResumeV2).toHaveBeenCalledTimes(1))
    expect(postResumeV2.mock.calls[0][0]).toBe('run-v73b')
    expect(postResumeV2.mock.calls[0][1]).toEqual({ kind: 'approval', decision: 'approve' })

    // 续推收口（session＋done，无挂起帧）→ 锚武装到该 run——输入继续追问该对话
    h.onFrame({ event: 'session', data: { run_id: 'run-v73b', resume: true } })
    h.onFrame({ event: 'done', data: { run_id: 'run-v73b' } })
    h.onDone()
    const askInput = await screen.findByPlaceholderText('追问此对话（Enter 发送）')
    fireEvent.change(askInput, { target: { value: '那后年呢？' } })
    pressEnter(askInput)
    await waitFor(() => expect(postAskV2).toHaveBeenCalledTimes(1))
    expect(postAskV2.mock.calls[0][0]).toEqual({ question: '那后年呢？', followupRunId: 'run-v73b' })
  })
})

describe('A1V2 · 列表读口失败态与空态分离（UI-14 同位纪律）', () => {
  it('listRunsV2 拒绝→计数行撤下（不出「共 0 条」假话）＋列表出「暂无数据」', async () => {
    listRunsV2.mockRejectedValue(new Error('network down'))
    render(<A1V2Landing />)
    await waitFor(() => expect(listRunsV2).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(screen.getByText('暂无数据')).toBeTruthy())
    expect(screen.queryByText(/^共 /)).toBeNull() // 失败态≠空库——计数行不渲染
  })
})

// ---------- 附钉：挂起卡渲染（AskCard 曾因 antd Space 未导入崩页——回归锚） ----------
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

// ---------- 附钉：EB2-D4 答案友好化（答案正文 Markdown 渲染＋[n] 引标联动引用抽屉） ----------
it('答案面：正文 Markdown 成元素、[n] 点击＝开引用抽屉＋高亮定位该 index 条目', async () => {
  listRunsV2.mockResolvedValue([])
  postAskV2.mockImplementation((body, handlers) => {
    handlers.onFrame({ event: 'session', data: { run_id: 'run-eb2', resume: false } })
    // 真机答案真形（eval/results/frames/EB1-数-明1.json）：粗体当小标题＋`- ` 清单＋逐行引标
    handlers.onFrame({ event: 'text', data: { content: '**结论**\n- N-01：21.16 吨[1]\n' } })
    handlers.onFrame({
      event: 'observation',
      data: { index: 1, source: '日产计量事实表', trust: 'db', content: 'N-01 2025-09-01 日产油量 21.16 吨。' }
    })
    handlers.onFrame({
      event: 'citation',
      data: { index: 1, source: '日产计量事实表', source_id: 'f51', trust: 'db' }
    })
    handlers.onDone()
    return Promise.resolve({ lastEventId: '' })
  })
  const { container } = render(<A1V2Landing />)
  fireEvent.change(await screen.findByPlaceholderText('输入问题（Enter 发送）'),
    { target: { value: '9 月上旬各井日产油量' } })
  fireEvent.click(screen.getByText('发送'))

  // 记号成元素：**结论**→<strong>、`- ` 清单→<li>（不再是 pre-wrap 原文记号）
  expect(await screen.findByText('结论')).toBeTruthy()
  const answer = container.querySelector('[data-testid="answer-view"]')
  expect(answer.querySelector('strong').textContent).toBe('结论')
  expect(answer.querySelector('li').textContent).toBe('N-01：21.16 吨[1]')
  expect(answer.textContent).not.toContain('**')

  // 正文 [1]＝可点击锚点；点击开引用抽屉、高亮并定位到 index=1 条目（observation 配对内容）
  const anchor = answer.querySelector('a[data-cite="1"]')
  expect(anchor).toBeTruthy()
  fireEvent.click(anchor)
  await waitFor(() => expect(document.getElementById('cite-1')).toBeTruthy())
  const entry = document.getElementById('cite-1')
  expect(entry.textContent).toContain('日产计量事实表')
  expect(entry.textContent).toContain('N-01 2025-09-01 日产油量 21.16 吨。')
  expect(entry.textContent).toContain('已定位')
})
