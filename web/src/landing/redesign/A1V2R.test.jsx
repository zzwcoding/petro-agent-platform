/**
 * A1V2R 真流页钉测（落地树 `#/A1V2`——FE-05 转正后：零夹具轮，中栏链条由真提问流／重连还原／
 * 选中链三来源驱动）。
 *
 * 守什么（specs/frontend-redesign.md「验收测试」表第 9/16/17 行＋本票红线）：
 * - **零真实网络**：chatV2 四函数 vi.mock 注桩（提问流帧由测试直喂 handlers）；raw fetch 层
 *   断言零调用（读口与流全在桩面）；
 * - **chain_order**（第 17 行）：真提问流驱动一轮——问句块→流水线块（running 展开）→首个正文帧
 *   后流水线收起＋正文出现→收口后 notice-alerts→正文→血缘卡→追加面→核验/档案小字依次在场；
 * - 发送接线：首问不带 followupRunId；前轮收口后追问带；流内 error 帧落 errorFrame（灰条）；
 *   传输断＝closed='transport'（收口清 running run 键）；流开前 409＝输入区 Alert 透传 message；
 * - 轮渲染（夹具轮 FIXTURE_TURNS——组件面）：链条节点序/流水线展开收起/A 级 notice 位/降级轮空态；
 * - 三场景归一（第 9 行 one_shape_three_scenarios）：同一 TurnChain 喂 live/replay/history 三形状，
 *   DOM 结构快照一致；history 缺的展示位＝整位不渲染；
 * - 左栏真接 ThreadList（第 16 行 select_thread_renders_turns）：点行＝选中链→中栏切链轮；
 * - 引标联动：点正文 [n] ＝右栏面板切到该轮并「已定位」；链内挂起轮＝续答真通（FE-04 遗留接通）；
 * - Owner 反馈回归（旧页 608267b 对照）：＋新会话＝退出链视图回本会话流＋输入/选中清空；
 *   中栏贴底跟随＝贴底态滚到底、上翻阅读不被拽回（jsdom 桩化 scrollHeight/clientHeight，
 *   页面无 Element.scrollTo＝回退置 scrollTop，即被测路径）。
 */
/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'

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
import { FIXTURE_RUNS } from './__fixtures__/runs.js'
import { FIXTURE_TURNS, FULL_FRAMES } from './__fixtures__/turns.js'
import A1V2R, { TurnChain } from './A1V2R.jsx'
import { adaptHistoryTurn } from './historyAdapter.js'
import { RUNNING_RUN_KEY } from './useRunningRun.js'

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

const fetchMock = vi.fn()
const RUN_VIEW = { status: 'completed', steps: [], manifest_digest: null, pending_ask: null }

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
  vi.stubGlobal('fetch', fetchMock)
  // ThreadList 真接读口默认桩（FE-04）：初载返回夹具行——页面级零真实网络
  vi.mocked(listRunsV2).mockResolvedValue(FIXTURE_RUNS)
  vi.mocked(getRunV2).mockResolvedValue(RUN_VIEW)
  vi.mocked(postAskV2).mockResolvedValue({ lastEventId: '' })
  vi.mocked(postResumeV2).mockResolvedValue({ lastEventId: '' })
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const FULL = FIXTURE_TURNS.find(t => t.id === 't-full').turn
const LIVE = FIXTURE_TURNS.find(t => t.id === 't-live').turn
const SPLIT = FIXTURE_TURNS.find(t => t.id === 't-split').turn
const LEGACY = FIXTURE_TURNS.find(t => t.id === 't-legacy').turn

/** 容器内若干 testid 的 DOM 出现序（断言链条顺序用）。 */
function orderOf(scope, testids) {
  const nodes = [...scope.querySelectorAll('[data-testid]')]
  return testids
    .map(id => ({ id, at: nodes.findIndex(n => n.dataset.testid === id) }))
    .sort((a, b) => a.at - b.at)
    .map(x => x.id)
}

/** 发一问（填输入＋点发送），返回该发的 postAskV2 入参与 handlers 桩。 */
async function sendAsk(question) {
  const before = vi.mocked(postAskV2).mock.calls.length
  const input = screen.getByPlaceholderText(/Enter 发送/)
  fireEvent.change(input, { target: { value: question } })
  fireEvent.click(screen.getByRole('button', { name: /发送/ }))
  await waitFor(() => expect(vi.mocked(postAskV2).mock.calls.length).toBe(before + 1))
  const [body, handlers] = vi.mocked(postAskV2).mock.calls.at(-1)
  return { body, handlers }
}

/** 一轮收口腿（session→正文→done＋onDone）——喂给 sendAsk 返回的 handlers。 */
function finishLeg(handlers, { runId, answer = '答案正文。', question = '' }) {
  act(() => {
    handlers.onFrame({ id: '-1', event: 'session', data: { run_id: runId, resume: false } })
    handlers.onFrame({ id: 0, event: 'text', data: { content: question || answer } })
    handlers.onFrame({ id: 1, event: 'done', data: { run_id: runId } })
    handlers.onDone()
  })
}

describe('A1V2R · 真流发送（FE-05——specs「验收测试」表第 17 行 chain_order）', () => {
  it('chain_order：问句块→流水线块（running 展开）→首个正文帧后流水线收起＋正文→收口后 notice-alerts→正文→血缘→追加面→小字', async () => {
    render(<A1V2R />)
    expect(screen.getByTestId('flow-empty')).toBeTruthy() // 空态：无轮不出链条

    const { body, handlers } = await sendAsk('今年各井的日产液量按天列出来')
    expect(body).toEqual({ question: '今年各井的日产液量按天列出来' }) // 首问不带 followupRunId
    // 整轮块序：问句块 → 流水线块 → 回答块
    expect(orderOf(screen.getByTestId('round-ask-1'), ['block-question', 'pipeline-block', 'turn-ask-1']))
      .toEqual(['block-question', 'pipeline-block', 'turn-ask-1'])

    // 运行中（真机帧：session→理解→步→工具→材料）：流水线默认展开，回答块＝占位
    const firstText = FULL_FRAMES.findIndex(f => f.event === 'text' && f.data?.kind !== 'understanding')
    act(() => { FULL_FRAMES.slice(0, firstText).forEach(f => handlers.onFrame(f)) })
    const round = () => screen.getByTestId('round-ask-1')
    expect(round().querySelector('[data-testid="pipeline-body"]')).toBeTruthy() // running＝展开
    expect(within(round()).getByTestId('answer-placeholder').textContent).toBe('正在作答…')

    // 首个正文帧到达＝流水线让位（自动收起）＋正文出现
    act(() => { handlers.onFrame(FULL_FRAMES[firstText]) })
    expect(round().querySelector('[data-testid="pipeline-body"]')).toBeNull()
    expect(within(round()).getByTestId('answer-view')).toBeTruthy()

    // 收口（余下全帧＋done）：回答块内节点序＝A 级 notice Alert → 正文 → 血缘卡 → 追加面 → 小字
    act(() => {
      FULL_FRAMES.slice(firstText + 1).forEach(f => handlers.onFrame(f))
      handlers.onDone()
    })
    expect(orderOf(within(round()).getByTestId('turn-ask-1'),
      ['notice-alerts', 'answer-view', 'lineage-card', 'supplement-blocks', 'run-meta-line']))
      .toEqual(['notice-alerts', 'answer-view', 'lineage-card', 'supplement-blocks', 'run-meta-line'])
    expect(within(round()).getByTestId('run-meta-line').textContent).toContain('本地计时') // E5 本地计时标注
    expect(fetchMock).not.toHaveBeenCalled() // 读口与流全在 chatV2 桩面——raw fetch 零调用
  })

  it('追问：前轮已收口后发送带 followupRunId；流内 error 帧落 errorFrame 灰条（不静默）', async () => {
    render(<A1V2R />)
    const first = await sendAsk('一轮问句')
    finishLeg(first.handlers, { runId: 'run-one' })
    expect(await screen.findByTestId('followup-hint')).toBeTruthy() // 已收口轮＝追问锚（输入区提示）

    const second = await sendAsk('二轮追问')
    expect(second.body).toEqual({ question: '二轮追问', followupRunId: 'run-one' })
    // 流内 error 帧（chat.js 保留帧先过 onFrame，onError 只清键）→ errorFrame 灰条
    act(() => {
      second.handlers.onFrame({ id: '-1', event: 'session', data: { run_id: 'run-two', resume: false } })
      second.handlers.onFrame({ id: 9, event: 'error', data: { code: 'engine_failed', message: '流内异常' } })
      second.handlers.onError({ code: 'engine_failed', message: '流内异常' })
    })
    expect(within(screen.getByTestId('round-ask-2')).getByTestId('error-frame-alert').textContent)
      .toContain('流内异常')
  })

  it('传输断＝closed=transport：R1 键收口清除、不落 errorFrame、轮按收口小字渲染', async () => {
    render(<A1V2R />)
    const { handlers } = await sendAsk('断线问句')
    act(() => {
      handlers.onFrame({ id: '-1', event: 'session', data: { run_id: 'run-drop', resume: false } })
      handlers.onFrame({ id: 1, event: 'step', data: { step: 'decision', seq: 1, title: '模型调用：decision' } })
    })
    expect(JSON.parse(sessionStorage.getItem(RUNNING_RUN_KEY))?.runId).toBe('run-drop') // R1 受理写键
    act(() => { handlers.onTransportError(new Error('connection reset')) })
    expect(sessionStorage.getItem(RUNNING_RUN_KEY)).toBeNull() // 收口清键
    const round = screen.getByTestId('round-ask-1')
    expect(round.querySelector('[data-testid="error-frame-alert"]')).toBeNull() // 传输断≠闭环 error 帧
    expect(round.querySelector('[data-testid="answer-placeholder"]')).toBeNull() // 已收口（不再「正在作答」）
    expect(round.querySelector('[data-testid="run-meta-line"]')).toBeTruthy()
  })

  it('流开前 409（追问前轮未收口）→ 输入区 Alert 透传 message＋该轮落 errorFrame（不静默）', async () => {
    render(<A1V2R />)
    const first = await sendAsk('一轮问句')
    finishLeg(first.handlers, { runId: 'run-one' })
    await screen.findByTestId('followup-hint')

    vi.mocked(postAskV2).mockRejectedValueOnce(new ApiError(
      409, { code: 'run_not_completed', message: '前轮未收口，不可追问' }, '前轮未收口，不可追问'
    ))
    const second = await sendAsk('追问被拒')
    expect(second.body).toEqual({ question: '追问被拒', followupRunId: 'run-one' })
    const alert = await screen.findByTestId('ask-error-alert')
    expect(alert.textContent).toContain('前轮未收口，不可追问')
    expect(within(screen.getByTestId('round-ask-2')).getByTestId('error-frame-alert').textContent)
      .toContain('前轮未收口，不可追问')
  })
})

describe('A1V2R · 轮渲染（夹具轮——链条节点与空态纪律）', () => {
  it('完整轮：流水线默认收起＋摘要行计数在位；点开＝事件流全量可回看', () => {
    render(<TurnChain id="t-full" turn={FULL} />)
    const round = screen.getByTestId('round-t-full')
    expect(round.querySelector('[data-testid="pipeline-body"]')).toBeNull()
    const bar = round.querySelector('[data-testid="pipeline-bar"]')
    expect(bar.textContent).toContain('执行完成')
    expect(bar.textContent).toContain('12 步')
    expect(bar.textContent).toContain('51 份材料')
    fireEvent.click(bar)
    expect(round.querySelectorAll('[data-testid^="ev-step-"]')).toHaveLength(12)
    expect(round.querySelector('[data-testid="ev-citation-51"]')).toBeTruthy()
  })

  it('A 级 notice 在回答块顶部；B/C 级不在回答块里（只在流水线）', () => {
    render(<TurnChain id="t-full" turn={FULL} />)
    const answerBlock = screen.getByTestId('turn-t-full')
    expect(within(answerBlock).getByTestId('notice-alerts').textContent)
      .toContain('这次回答只用到检索到的 24/37 条材料')
    expect(answerBlock.textContent).not.toContain('window_note') // B 级不在回答块
    expect(answerBlock.textContent).not.toContain('unsupported_claim') // C 级不在回答块
  })

  it('运行中轮：流水线默认展开＝流式事件追加；回答块＝「正在作答…」占位（无正文、无核验小字）', () => {
    render(<TurnChain id="t-live" turn={LIVE} />)
    const round = screen.getByTestId('round-t-live')
    const pipeline = round.querySelector('[data-testid="pipeline"]')
    expect(within(pipeline).getByTestId('pipeline-body')).toBeTruthy() // 展开态
    expect(within(pipeline).getByTestId('ev-understanding').textContent).toContain('💭 理解为：')
    expect(within(pipeline).getByTestId('ev-materials').textContent).toContain('16 份材料')
    expect(within(pipeline).getByTestId('pipeline-tail').textContent).toContain('继续处理中…')

    const answerBlock = screen.getByTestId('turn-t-live')
    expect(within(answerBlock).getByTestId('answer-placeholder').textContent).toBe('正在作答…')
    expect(within(answerBlock).queryByTestId('answer-view')).toBeNull()
    expect(within(answerBlock).queryByTestId('run-meta-line')).toBeNull() // 未收口＝无核验/档案小字
  })

  it('分列轮长 split 限高；旧版降级轮无流水线＋降级灰字；旧版轮 [n] 是死文本', () => {
    render(<>
      <TurnChain id="t-split" turn={SPLIT} />
      <TurnChain id="t-legacy" turn={LEGACY} />
    </>)
    const split = within(screen.getByTestId('turn-t-split'))
    fireEvent.click(split.getByText('各来源说法不一 · 点开对照'))
    expect(split.getAllByText(/展开看全文/).length).toBeGreaterThan(0) // 长条限高

    const legacy = screen.getByTestId('turn-t-legacy')
    expect(legacy.parentElement.querySelectorAll('[data-testid="pipeline"]')).toHaveLength(0) // 无流水线块
    expect(within(legacy).getByTestId('legacy-note').textContent)
      .toContain('本轮为旧版记录，无引用/口径明细')
    expect(legacy.querySelector('[data-cite]')).toBeNull() // 旧轮无引用数据——[n] 不成锚点
    expect(legacy.textContent).toContain('「躺井」是作业区口语')
    expect(legacy.textContent).toContain('[1]')
  })

  it('答案正文面：三条有正文的轮都渲染（旧版轮内嵌旧式「引用：」块——原样，不解析）', () => {
    render(<>
      <TurnChain id="t-full" turn={FULL} />
      <TurnChain id="t-split" turn={SPLIT} />
      <TurnChain id="t-legacy" turn={LEGACY} />
    </>)
    expect(screen.getAllByTestId('answer-view')).toHaveLength(3)
    expect(screen.getByText(/引用：/)).toBeTruthy()
  })
})

describe('A1V2R · 三场景归一（H5 零分支——specs「验收测试」表第 9 行）', () => {
  /** 同一轮内容的两种来源：live/replay＝归约器帧归约（H1——replay 帧序与原流逐字相同，
   *  输出与 live 同形，仅 kind 不同）；history＝adaptHistoryTurn 投影。
   *  materials/notices 留空（history 读口无此面）——同一内容喂同一 TurnChain。 */
  const ONE_SHAPE_FRAMES = [
    { id: '-1', event: 'session', data: { run_id: 'run-one-shape', resume: false } },
    { id: 0, event: 'text', data: { content: '答案正文一段。' } },
    { id: 1, event: 'supplement', data: { block: 'lineage', text: '① 口径 日产液量（方）' } },
    { id: 2, event: 'supplement', data: { block: 'split', text: '互不一致——各来源说法如下，按来源分别列出：\n[1] 《源A》：说法一' } },
    { id: 3, event: 'supplement', data: { block: 'attribution', text: '按来源分别列出（每条结论标明出处）：\n[1] 《源A》：说法一' } },
    { id: 4, event: 'done', data: { run_id: 'run-one-shape' } }
  ]
  const ONE_SHAPE_LIST_ITEM = {
    run_id: 'run-one-shape',
    question: '问句一',
    status: 'completed',
    answer: '答案正文一段。',
    followup_of: '',
    created_at: '2026-10-17 09:12:41',
    updated_at: '2026-10-17 09:13:00',
    supplements: [
      { block: 'lineage', text: '① 口径 日产液量（方）' },
      { block: 'split', text: '互不一致——各来源说法如下，按来源分别列出：\n[1] 《源A》：说法一' },
      { block: 'attribution', text: '按来源分别列出（每条结论标明出处）：\n[1] 《源A》：说法一' }
    ]
  }
  const live = reduceV2Frames(newTurnV2('ask', '问句一'), ONE_SHAPE_FRAMES)
  const replay = reduceV2Frames(newTurnV2('replay', '问句一'), ONE_SHAPE_FRAMES)
  const history = adaptHistoryTurn(ONE_SHAPE_LIST_ITEM, null)

  /** 结构快照签名：标签＋data-testid＋直属文本＋子结构（剥类名/style/aria 等 SDK 实现细节
   *  ——antd 折叠件内部 id 非稳态，不进签名；testid 面与文本面与层级面即「结构」）。 */
  function signature(el) {
    const ownText = [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('')
    return JSON.stringify([
      el.tagName,
      el.getAttribute?.('data-testid') ?? null,
      ownText,
      [...el.children].map(child => signature(child))
    ])
  }

  it('one_shape_three_scenarios：live/replay/history 三形状喂同一 TurnChain——DOM 结构快照一致', () => {
    const a = render(<TurnChain id="t-x" turn={live} />)
    const b = render(<TurnChain id="t-x" turn={replay} />)
    const c = render(<TurnChain id="t-x" turn={history} />)
    const liveSig = signature(a.container.firstElementChild)
    expect(signature(b.container.firstElementChild)).toBe(liveSig) // replay 与 live 同归约器——kind 不落 DOM
    expect(signature(c.container.firstElementChild)).toBe(liveSig) // history 投影同形——零场景分支
  })

  it('history 缺的展示位＝整位不渲染（不是渲染占位——空态纪律在展示件内）', () => {
    const { container } = render(<TurnChain id="t-x" turn={history} />)
    expect(container.querySelector('[data-testid="pipeline"]')).toBeNull() // events 恒空→流水线整块不出
    expect(container.querySelector('[data-testid="answer-placeholder"]')).toBeNull()
    expect(container.querySelector('[data-testid="legacy-note"]')).toBeNull() // 新行 supplements=[]→legacy=false
    // 链条仍完整：正文/血缘卡/追加面/核验小字照常渲染（同 live 的节点集）
    for (const id of ['block-question', 'answer-view', 'lineage-card', 'supplement-blocks', 'run-meta-line']) {
      expect(container.querySelector(`[data-testid="${id}"]`)).toBeTruthy()
    }
    expect(container.querySelector('[data-testid="run-meta-line"]').textContent).toBe('run-one-shape')
  })
})

describe('A1V2R · 左侧历史对话（真接 ThreadList——FE-04）', () => {
  it('左栏＝ThreadList 真接：初始拉 20 条、搜索框在位、加载入口在位；点行＝高亮切换＋中栏切链', async () => {
    render(<A1V2R />)
    const list = screen.getByTestId('thread-list')
    await within(list).findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    expect(within(list).getAllByTestId(/^thread-row-/)).toHaveLength(20)
    expect(within(list).getByPlaceholderText('搜索对话')).toBeTruthy()
    expect(within(list).getByTestId('load-more')).toBeTruthy()
    expect(vi.mocked(listRunsV2)).toHaveBeenCalledWith(20) // 真接读口：初始 limit=20
    // 点行＝高亮切换（真接后无预选中——选中态由点击驱动）＋中栏切该链
    expect(within(list).getByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`).dataset.selected).toBe('false')
    fireEvent.click(within(list).getByTestId(`thread-row-${FIXTURE_RUNS[3].run_id}`))
    expect(within(list).getByTestId(`thread-row-${FIXTURE_RUNS[3].run_id}`).dataset.selected).toBe('true')
    expect(within(list).getByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`).dataset.selected).toBe('false')
    await screen.findByTestId(`round-${FIXTURE_RUNS[3].run_id}`) // 中栏切链（选中行拉链——单轮链）
    expect(fetchMock).not.toHaveBeenCalled() // 读口走 chatV2 桩——raw fetch 层零调用
  })

  it('左栏搜索＝前端过滤（搜索期零新增请求——listRunsV2 调用次数不变）', async () => {
    render(<A1V2R />)
    await screen.findByTestId(`thread-row-${FIXTURE_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '含水率' } })
    const hit = FIXTURE_RUNS.slice(0, 20).filter(r => r.question.includes('含水率'))
    expect(screen.getAllByTestId(/^thread-row-/)).toHaveLength(hit.length)
    expect(vi.mocked(listRunsV2)).toHaveBeenCalledTimes(1) // 只有初载一次
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('A1V2R · 右栏联动', () => {
  it('缺省＝最新轮；点正文 [n] ＝右栏切到该轮并定位（「已定位」＋该条材料原文）', async () => {
    render(<A1V2R />)
    const first = await sendAsk('一轮问句')
    act(() => {
      first.handlers.onFrame({ id: '-1', event: 'session', data: { run_id: 'run-a', resume: false } })
      first.handlers.onFrame({ id: 0, event: 'text', data: { content: 'N-01 2025-09-01 日产油量 21.16 吨[1]。' } })
      first.handlers.onFrame({ id: 1, event: 'observation', data: { index: 1, source: '源A', trust: 'db', content: 'N-01 2025-09-01 日产油量 21.16 吨。' } })
      first.handlers.onFrame({ id: 2, event: 'citation', data: { index: 1, source: '源A', source_id: 'f51', trust: 'db' } })
      first.handlers.onFrame({ id: 3, event: 'done', data: { run_id: 'run-a' } })
      first.handlers.onDone()
    })
    const second = await sendAsk('二轮问句')
    act(() => {
      second.handlers.onFrame({ id: '-1', event: 'session', data: { run_id: 'run-b', resume: false } })
      second.handlers.onFrame({ id: 0, event: 'text', data: { content: 'N-01 2025-09-02 日产油量 19.8 吨[2]。' } })
      second.handlers.onFrame({ id: 1, event: 'observation', data: { index: 2, source: '源B', trust: 'db', content: 'N-01 2025-09-02 日产油量 19.8 吨。' } })
      second.handlers.onFrame({ id: 2, event: 'citation', data: { index: 2, source: '源B', source_id: 'f52', trust: 'db' } })
      second.handlers.onFrame({ id: 3, event: 'done', data: { run_id: 'run-b' } })
      second.handlers.onDone()
    })
    expect(screen.getByTestId('citation-panel').textContent).toContain('源B') // 缺省＝最新轮
    // 点一轮正文 [n]：面板切到该轮＋该条「已定位」
    const cite = screen.getByTestId('turn-ask-1').querySelector('[data-cite="1"]')
    expect(cite).toBeTruthy()
    fireEvent.click(cite)
    const panel = screen.getByTestId('citation-panel')
    expect(panel.textContent).toContain('源A')
    expect(screen.getByTestId('cite-item-1').textContent).toContain('已定位')
    expect(screen.getByTestId('cite-item-1').textContent).toContain('N-01 2025-09-01 日产油量 21.16 吨。')
  })

  it('整轮无引用＝面板空态「本回合无引用」（不虚构）', async () => {
    render(<A1V2R />)
    const { handlers } = await sendAsk('无引用问句')
    finishLeg(handlers, { runId: 'run-none', answer: '本回答没有引用任何材料。' })
    expect(await screen.findByText('本回合无引用。')).toBeTruthy()
  })

  it('回答块不再有「引用与口径」跳转入口（Owner 反馈 1：整条删掉）', () => {
    render(<A1V2R />)
    expect(screen.queryByRole('button', { name: '引用与口径' })).toBeNull()
    expect(screen.queryByText('引用与口径', { selector: 'button' })).toBeNull()
  })

  it('右栏决策树入口在位（占位 Modal——真树本体接回在后续版本）', () => {
    render(<A1V2R />)
    fireEvent.click(screen.getByRole('button', { name: /决策树/ }))
    expect(screen.getByText('决策树（占位）')).toBeTruthy()
  })
})

describe('A1V2R · 选中拉链（FE-04 L3——specs「验收测试」表第 16 行）', () => {
  /** 窗口内造链（root＋第 2 轮 followup，followup_of 逐跳指向）＋无关单轮；
   *  listRunsV2 桩按 created_at 降序回窗（后端排序语义）。root＝旧版行（supplements=null→
   *  legacy 灰字）；followup 轮带 lineage 块——右栏默认联动链尾轮，以此分辨面板切到位。 */
  const CHAIN_WINDOW = [
    { run_id: 'run-next', question: '追问问句', status: 'completed', answer: '追问轮答案正文。',
      followup_of: 'run-root', created_at: '2026-10-17 10:05:00', updated_at: '2026-10-17 10:05:30',
      supplements: [{ block: 'lineage', text: '追问轮口径：含水率按生产日' }] },
    { run_id: 'run-root', question: '链根问句', status: 'completed', answer: '根轮答案正文。',
      followup_of: '', created_at: '2026-10-17 10:00:00', updated_at: '2026-10-17 10:00:30',
      supplements: null },
    { run_id: 'run-other', question: '无关问句', status: 'completed', answer: '无关轮答案正文。',
      followup_of: '', created_at: '2026-10-17 09:00:00', updated_at: '2026-10-17 09:00:30',
      supplements: [] }
  ]
  const runViewOf = runId => ({
    status: 'completed',
    steps: [{ seq: 1, step: 'understand', status: 'ok', title: `理解问题（${runId}）` }],
    manifest_digest: `digest-${runId}`,
    pending_ask: null
  })

  it('select_thread_renders_turns：点链根行 → 逐轮 getRunV2 → 中栏两轮 created_at 升序；supplements=null 轮灰字在场', async () => {
    vi.mocked(listRunsV2).mockResolvedValue(CHAIN_WINDOW)
    vi.mocked(getRunV2).mockImplementation(runId => Promise.resolve(runViewOf(runId)))
    render(<A1V2R />)
    await screen.findByTestId('thread-row-run-root')
    fireEvent.click(screen.getByTestId('thread-row-run-root')) // 点链根行
    // 中栏＝该链两轮（无关单轮不入链），DOM 序＝created_at 升序（root→next）
    await screen.findByTestId('round-run-root')
    expect(screen.getByTestId('round-run-next')).toBeTruthy()
    expect(screen.queryByTestId('round-run-other')).toBeNull()
    expect(screen.getByText('对话 · 2 轮（选中链——created_at 升序）')).toBeTruthy() // 中栏在链视图
    expect(screen.queryByTestId('flow-empty')).toBeNull() // 链视图下不出本会话流空态
    const order = [...document.querySelectorAll('[data-testid="round-run-root"], [data-testid="round-run-next"]')]
      .map(el => el.dataset.testid)
    expect(order).toEqual(['round-run-root', 'round-run-next'])
    // 每轮 getRunV2（仅链内两轮——逐轮归一）
    expect(vi.mocked(getRunV2)).toHaveBeenCalledTimes(2)
    expect(vi.mocked(getRunV2)).toHaveBeenNthCalledWith(1, 'run-root')
    expect(vi.mocked(getRunV2)).toHaveBeenNthCalledWith(2, 'run-next')
    // supplements=null 旧轮 → 灰字在场（E4 降级——adaptHistoryTurn legacy 形）；新轮无灰字
    expect(within(screen.getByTestId('round-run-root')).getByTestId('legacy-note').textContent)
      .toContain('本轮为旧版记录，无引用/口径明细')
    expect(within(screen.getByTestId('round-run-next')).queryByTestId('legacy-note')).toBeNull()
    // 右栏联动＝当前选中链最后一轮（followup 轮）：链轮无引用帧＋lineage 块落面板
    // （根轮 legacy 无 supplements→无血缘卡）
    const panel = screen.getByTestId('citation-panel')
    expect(panel.textContent).toContain('本回合无引用')
    expect(within(panel).getByTestId('lineage-card')).toBeTruthy()
  })

  it('select_thread_renders_turns · 404 轮降级：getRunV2 404 → adaptHistoryTurn(r,null)＋errorFrame 灰条，链内他轮照常', async () => {
    vi.mocked(listRunsV2).mockResolvedValue(CHAIN_WINDOW)
    vi.mocked(getRunV2).mockImplementation(runId => (runId === 'run-next'
      ? Promise.reject(new ApiError(404, { code: 'chat_run_not_found', message: 'run 不存在' }, 'run 不存在'))
      : Promise.resolve(runViewOf(runId))))
    render(<A1V2R />)
    await screen.findByTestId('thread-row-run-root')
    fireEvent.click(screen.getByTestId('thread-row-run-root'))
    // 404 轮仍渲染（降级形）：errorFrame 灰条「本轮已结束或不可达」；根轮正常无灰条
    await screen.findByTestId('round-run-next')
    expect(within(screen.getByTestId('round-run-next')).getByTestId('error-frame-alert').textContent)
      .toContain('本轮已结束或不可达')
    expect(within(screen.getByTestId('round-run-root')).queryByTestId('error-frame-alert')).toBeNull()
    expect(within(screen.getByTestId('round-run-root')).getByTestId('answer-view')).toBeTruthy()
    expect(vi.mocked(getRunV2)).toHaveBeenCalledTimes(2) // 不重试（404 轮降级不重拉）
  })

  it('链内挂起轮续答接通（FE-04 遗留）：点选项 → postResumeV2 真通，本腿帧落回该链轮', async () => {
    vi.mocked(listRunsV2).mockResolvedValue([{
      run_id: 'run-wait', question: '挂起问句', status: 'waiting_ask', answer: null,
      followup_of: '', created_at: '2026-10-17 11:00:00', updated_at: '2026-10-17 11:00:30',
      supplements: []
    }])
    vi.mocked(getRunV2).mockResolvedValue({
      status: 'waiting_ask', steps: [], manifest_digest: null,
      pending_ask: { kind: 'clarify', prompt: '按哪个口径统计？', options: ['按自然日', '按生产日'], detail: null }
    })
    render(<A1V2R />)
    await screen.findByTestId('thread-row-run-wait')
    fireEvent.click(screen.getByTestId('thread-row-run-wait'))
    const card = await screen.findByTestId('suspend-card') // 链轮挂起卡还原（askFrame 驱动）
    expect(card.textContent).toContain('按哪个口径统计？')
    fireEvent.click(within(card).getByRole('button', { name: '按自然日' }))
    await waitFor(() => expect(vi.mocked(postResumeV2)).toHaveBeenCalledTimes(1))
    expect(vi.mocked(postResumeV2).mock.calls[0][0]).toBe('run-wait')
    expect(vi.mocked(postResumeV2).mock.calls[0][1]).toEqual({ kind: 'clarify', choice: '按自然日' })
    // 本腿新帧直进同一 reducer（同 runId 落回该链轮——不另开轮）
    const handlers = vi.mocked(postResumeV2).mock.calls[0][2]
    act(() => {
      handlers.onFrame({ id: '-1', event: 'session', data: { run_id: 'run-wait', resume: true } })
      handlers.onFrame({ id: 7, event: 'text', data: { content: '按生产日统计的续答正文。' } })
      handlers.onFrame({ id: 8, event: 'done', data: { run_id: 'run-wait' } })
      handlers.onDone()
    })
    expect(screen.getAllByTestId('round-run-wait')).toHaveLength(1)
    expect(screen.getByTestId('round-run-wait').textContent).toContain('按生产日统计的续答正文。')
    expect(vi.mocked(postAskV2)).not.toHaveBeenCalled() // 续答只消费本腿新帧（不重启不重放）
  })
})

describe('A1V2R · Owner 反馈回归（＋新会话退出对话／中栏贴底跟随）', () => {
  it('＋新会话：左栏 Card extra 在位；选中链状态下点击＝退出链视图回本会话流＋输入与选中清空', async () => {
    render(<A1V2R />)
    const btn = screen.getByTestId('new-session')
    expect(btn.textContent).toBe('＋新会话')
    expect(btn.disabled).toBe(false) // 非发送中＝可点（旧页 busy 同义才 disabled）

    // 进链视图：点单轮链行（run-78dde6c6——窗口内无同根行）
    await screen.findByTestId('thread-row-run-78dde6c6')
    fireEvent.click(screen.getByTestId('thread-row-run-78dde6c6'))
    await screen.findByTestId('round-run-78dde6c6')
    expect(screen.getByText(/选中链——created_at 升序/)).toBeTruthy() // 中栏在链视图
    expect(screen.getByTestId('thread-row-run-78dde6c6').dataset.selected).toBe('true')

    const input = screen.getByPlaceholderText(/Enter 发送/)
    fireEvent.change(input, { target: { value: '打了一半的字' } })
    fireEvent.click(screen.getByTestId('new-session'))

    // 中栏回本会话流视图（链头/链轮退场；本会话流空＝空态）
    expect(screen.queryByText(/选中链——created_at 升序/)).toBeNull()
    expect(screen.queryByTestId('round-run-78dde6c6')).toBeNull()
    expect(screen.getByTestId('flow-empty')).toBeTruthy()
    expect(screen.getByTestId('new-session')).toBeTruthy() // 退回本会话流仍在本栏
    expect(input.value).toBe('') // 输入清空
    expect(screen.getByTestId('thread-row-run-78dde6c6').dataset.selected).toBe('false') // 对话选中清
    expect(fetchMock).not.toHaveBeenCalled() // 零真实网络
  })

  it('中栏贴底跟随：贴底态下内容变化滚到底；上翻阅读（离底 ≥80px）＝不强拽回底', async () => {
    render(<A1V2R />)
    const el = screen.getByTestId('conv-scroll')
    // jsdom 无布局：scrollHeight/clientHeight 桩化（scrollTop 可读可写）
    Object.defineProperty(el, 'scrollHeight', { configurable: true, value: 1000 })
    Object.defineProperty(el, 'clientHeight', { configurable: true, value: 100 })

    // 用户滚到底（离底 0 < 80px）＝跟随态；随后 scrollTop 桩回 0（模拟新内容到达前的滚动位置）
    el.scrollTop = 900
    fireEvent.scroll(el)
    el.scrollTop = 0
    const { handlers } = await sendAsk('贴底问句')
    expect(el.scrollTop).toBe(1000) // 贴底态：滚到 scrollHeight（jsdom 无 scrollTo＝回退置 scrollTop）

    // 用户上翻阅读（离底 900 ≥ 80px）＝解除跟随——新内容到达也不拽回
    el.scrollTop = 0
    fireEvent.scroll(el)
    act(() => {
      handlers.onFrame({ id: '-1', event: 'session', data: { run_id: 'run-stick', resume: false } })
      handlers.onFrame({ id: 0, event: 'text', data: { content: '继续追加的正文。' } })
    })
    expect(el.scrollTop).toBe(0)
    expect(screen.getByTestId('round-ask-1').textContent).toContain('继续追加的正文。') // 内容照常追加
  })

  it('中栏滚动容器链视图内同挂 conv-scroll（同一 ref——同时只渲染一个）', async () => {
    render(<A1V2R />)
    expect(screen.getAllByTestId('conv-scroll')).toHaveLength(1) // 本会话流分支
    await screen.findByTestId('thread-row-run-78dde6c6')
    fireEvent.click(screen.getByTestId('thread-row-run-78dde6c6'))
    await screen.findByTestId('round-run-78dde6c6')
    expect(screen.getAllByTestId('conv-scroll')).toHaveLength(1) // 链视图分支（本会话流分支已退场）
  })
})
