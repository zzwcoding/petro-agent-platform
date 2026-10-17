/**
 * A1V2R 页面钉测（串行链条版面页——临时路由；FE-04 历史列真接后左栏读口走 chatV2 桩）。
 *
 * 守什么（本页红线，机器可验）：
 * - **零真实网络**：mock 四轮来自 redesign/mockTurns.js（真帧夹具＋归约器输出）；左栏
 *   ThreadList 真接读口（listRunsV2/getRunV2——FE-04）以 vi.mock 注桩零网络，raw fetch 层
 *   断言零次调用（读口调用不触 fetch 层）；
 * - **链条顺序**：每轮＝用户输入块 → 系统执行流水线块 → 系统回答块；回答块内＝A 级 notice Alert →
 *   正文 → 血缘卡 → 追加面 → 核验/档案小字（DOM 序断言）；
 * - 四轮覆盖：①运行中（流水线展开、回答块「正在作答…」占位）②完整轮（流水线收起、链条完整）
 *   ③分列轮（长 split 限高）④旧版降级（无流水线、无引用、[n] 死文本）；
 * - **三场景归一**（H5 零分支）：同一 TurnChain 喂 live/replay（归约器）与 history
 *   （historyAdapter）三形状——DOM 结构快照一致，history 缺的展示位不渲染；
 * - 引标联动：点正文 [n] ＝右栏面板切到该轮并「已定位」；
 * - A 级 notice 在回答块顶部可见（折叠态流水线下也感知可信度），B/C 级只在流水线里；
 * - 右栏「决策树」入口在位（mock 点开说明 Modal）。
 */
/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'

vi.mock('../../api/chatV2.js', async importOriginal => ({
  ...await importOriginal(),
  listRunsV2: vi.fn(),
  getRunV2: vi.fn()
}))

import { ApiError } from '../../api/client.js'
import { getRunV2, listRunsV2 } from '../../api/chatV2.js'
import { newTurnV2, reduceV2Frames } from '../a1v2Reducer.js'
import A1V2R, { TurnChain } from './A1V2R.jsx'
import { adaptHistoryTurn } from './historyAdapter.js'
import { MOCK_RUNS } from './mockTurns.js'

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
beforeEach(() => {
  vi.clearAllMocks()
  vi.stubGlobal('fetch', fetchMock)
  // ThreadList 真接读口默认桩（FE-04）：初载返回 MOCK_RUNS 夹具——页面级零真实网络
  vi.mocked(listRunsV2).mockResolvedValue(MOCK_RUNS)
  vi.mocked(getRunV2).mockResolvedValue({
    status: 'completed', steps: [], manifest_digest: null, pending_ask: null
  })
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

/** 容器内若干 testid 的 DOM 出现序（断言链条顺序用）。 */
function orderOf(scope, testids) {
  const nodes = [...scope.querySelectorAll('[data-testid]')]
  return testids
    .map(id => ({ id, at: nodes.findIndex(n => n.dataset.testid === id) }))
    .sort((a, b) => a.at - b.at)
    .map(x => x.id)
}

describe('A1V2R · 串行链条（完整轮）', () => {
  it('链条顺序：问句块 → 流水线块 → 回答块 → 正文 → 血缘卡 → 追加面 → 小字行', () => {
    render(<A1V2R />)
    const round = screen.getByTestId('round-t-full')
    // 整轮块序：问句块 → 流水线块 → 回答块
    expect(orderOf(round, ['block-question', 'pipeline-block', 'turn-t-full']))
      .toEqual(['block-question', 'pipeline-block', 'turn-t-full'])
    // 回答块内节点序：A 级 notice Alert → 正文 → 血缘卡 → 追加面 → 核验/档案小字
    expect(orderOf(screen.getByTestId('turn-t-full'),
      ['notice-alerts', 'answer-view', 'lineage-card', 'supplement-blocks', 'run-meta-line']))
      .toEqual(['notice-alerts', 'answer-view', 'lineage-card', 'supplement-blocks', 'run-meta-line'])
  })

  it('完整轮（done）：流水线默认收起，摘要行在位；点开＝事件流全量可回看', () => {
    render(<A1V2R />)
    expect(screen.getAllByTestId('pipeline-body')).toHaveLength(1) // 只有运行中轮默认展开
    const fullRound = screen.getByTestId('round-t-full')
    expect(fullRound.querySelector('[data-testid="pipeline-body"]')).toBeNull()
    const bar = fullRound.querySelector('[data-testid="pipeline-bar"]')
    expect(bar.textContent).toContain('执行完成')
    expect(bar.textContent).toContain('12 步')
    expect(bar.textContent).toContain('51 份材料')
    fireEvent.click(bar)
    expect(fullRound.querySelectorAll('[data-testid^="ev-step-"]')).toHaveLength(12)
    expect(fullRound.querySelector('[data-testid="ev-citation-51"]')).toBeTruthy()
  })

  it('A 级 notice 在回答块顶部；B/C 级不在回答块里（只在流水线）', () => {
    render(<A1V2R />)
    const answerBlock = screen.getByTestId('turn-t-full')
    expect(within(answerBlock).getByTestId('notice-alerts').textContent)
      .toContain('这次回答只用到检索到的 24/37 条材料')
    expect(answerBlock.textContent).not.toContain('window_note') // B 级不在回答块
    expect(answerBlock.textContent).not.toContain('unsupported_claim') // C 级不在回答块
  })
})

describe('A1V2R · 运行中轮（流水线展开态）', () => {
  it('流水线默认展开＝流式事件追加；回答块＝「正在作答…」占位（无正文、无核验小字）', () => {
    render(<A1V2R />)
    const round = screen.getByTestId('round-t-live')
    const pipeline = round.querySelector('[data-testid="pipeline"]')
    expect(pipeline).toBeTruthy()
    expect(within(pipeline).getByTestId('pipeline-body')).toBeTruthy() // 展开态
    expect(within(pipeline).getByTestId('ev-understanding').textContent).toContain('💭 理解为：')
    expect(within(pipeline).getByTestId('ev-materials').textContent).toContain('16 份材料')
    expect(within(pipeline).getByTestId('pipeline-tail').textContent).toContain('继续处理中…')

    const answerBlock = screen.getByTestId('turn-t-live')
    expect(within(answerBlock).getByTestId('answer-placeholder').textContent).toBe('正在作答…')
    expect(within(answerBlock).queryByTestId('answer-view')).toBeNull()
    expect(within(answerBlock).queryByTestId('run-meta-line')).toBeNull() // 未收口＝无核验/档案小字
  })
})

describe('A1V2R · 其余三轮形态', () => {
  it('四轮都在位；分列轮长 split 限高；旧版轮无流水线＋降级说明；全程零请求', () => {
    render(<A1V2R />)
    for (const id of ['t-live', 't-full', 't-split', 't-legacy']) {
      expect(screen.getByTestId(`turn-${id}`)).toBeTruthy()
    }
    const split = within(screen.getByTestId('turn-t-split'))
    fireEvent.click(split.getByText('各来源说法不一 · 点开对照'))
    expect(split.getAllByText(/展开看全文/).length).toBeGreaterThan(0) // 长条限高

    const legacy = screen.getByTestId('turn-t-legacy')
    expect(legacy.parentElement.querySelectorAll('[data-testid="pipeline"]')).toHaveLength(0) // 无流水线块
    expect(within(legacy).getByTestId('legacy-note').textContent).toContain('本轮为旧版记录，无引用/口径明细')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('每条答案正文都渲染（旧版轮含内嵌旧式「引用：」块文本——原样，不解析）', () => {
    render(<A1V2R />)
    expect(screen.getAllByTestId('answer-view')).toHaveLength(3) // 运行中轮无正文
    expect(screen.getByText(/引用：/)).toBeTruthy()
  })

  it('旧版轮 [n] 是死文本（无锚点、无悬停卡——旧轮无引用数据可查）', () => {
    render(<A1V2R />)
    const legacy = screen.getByTestId('turn-t-legacy')
    expect(legacy.querySelector('[data-cite]')).toBeNull()
    expect(legacy.textContent).toContain('「躺井」是作业区口语')
    expect(legacy.textContent).toContain('[1]')
  })
})

describe('A1V2R · 左侧历史对话（真接 ThreadList——FE-04）', () => {
  it('左栏＝ThreadList 真接：初始拉 20 条、搜索框在位、加载入口在位；点行＝高亮切换＋中栏切链', async () => {
    render(<A1V2R />)
    const list = screen.getByTestId('thread-list')
    await within(list).findByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    expect(within(list).getAllByTestId(/^thread-row-/)).toHaveLength(20)
    expect(within(list).getByPlaceholderText('搜索对话')).toBeTruthy()
    expect(within(list).getByTestId('load-more')).toBeTruthy()
    expect(vi.mocked(listRunsV2)).toHaveBeenCalledWith(20) // 真接读口：初始 limit=20
    // 点行＝高亮切换（真接后无预选中——选中态由点击驱动）＋中栏切该链
    expect(within(list).getByTestId(`thread-row-${MOCK_RUNS[0].run_id}`).dataset.selected).toBe('false')
    fireEvent.click(within(list).getByTestId(`thread-row-${MOCK_RUNS[3].run_id}`))
    expect(within(list).getByTestId(`thread-row-${MOCK_RUNS[3].run_id}`).dataset.selected).toBe('true')
    expect(within(list).getByTestId(`thread-row-${MOCK_RUNS[0].run_id}`).dataset.selected).toBe('false')
    await screen.findByTestId(`round-${MOCK_RUNS[3].run_id}`) // 中栏切链（选中行拉链——单轮链）
    expect(fetchMock).not.toHaveBeenCalled() // 读口走 chatV2 桩——raw fetch 层零调用
  })

  it('左栏搜索＝前端过滤（搜索期零新增请求——listRunsV2 调用次数不变）', async () => {
    render(<A1V2R />)
    await screen.findByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '含水率' } })
    const hit = MOCK_RUNS.slice(0, 20).filter(r => r.question.includes('含水率'))
    expect(screen.getAllByTestId(/^thread-row-/)).toHaveLength(hit.length)
    expect(vi.mocked(listRunsV2)).toHaveBeenCalledTimes(1) // 只有初载一次
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('A1V2R · 右栏联动', () => {
  it('点正文 [n] ＝右栏切到该轮并定位（「已定位」＋该条材料原文）', () => {
    render(<A1V2R />)
    const cite = screen.getByTestId('turn-t-full').querySelector('[data-cite="51"]')
    expect(cite).toBeTruthy()
    fireEvent.click(cite)
    const item = screen.getByTestId('cite-item-51')
    expect(item.textContent).toContain('已定位')
    expect(item.textContent).toContain('日产液量（方）')
  })

  it('点分列轮正文 [n] ＝右栏切到该轮（默认完整轮 2 处来源 → 分列轮 5 处来源）', () => {
    render(<A1V2R />)
    expect(screen.getByText('共 51 支引用 · 来自 2 处来源')).toBeTruthy()
    const cite = screen.getByTestId('turn-t-split').querySelector('[data-cite="6"]')
    expect(cite).toBeTruthy()
    fireEvent.click(cite)
    expect(screen.getByText('共 16 支引用 · 来自 5 处来源')).toBeTruthy()
    expect(screen.getByTestId('cite-item-6').textContent).toContain('已定位')
  })

  it('回答块不再有「引用与口径」跳转入口（Owner 反馈 1：整条删掉）', () => {
    render(<A1V2R />)
    expect(screen.queryByRole('button', { name: '引用与口径' })).toBeNull()
    expect(screen.queryByText('引用与口径', { selector: 'button' })).toBeNull()
  })

  it('右栏决策树入口在位（mock 点开说明 Modal——真树接线在后）', () => {
    render(<A1V2R />)
    fireEvent.click(screen.getByRole('button', { name: /决策树/ }))
    expect(screen.getByText('决策树（mock 占位）')).toBeTruthy()
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

describe('A1V2R · 选中拉链（FE-04 L3——specs「验收测试」表第 16 行）', () => {
  /** 窗口内造链（票面伪代码第 3 节：root＋第 2 轮 followup，followup_of 逐跳指向）＋无关单轮；
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
    expect(screen.queryByTestId('round-t-full')).toBeNull() // mock 轮让位（选中链显示链——并存最小实现）
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
    // （根轮 legacy 无 supplements→无血缘卡；mock 完整轮有 51 支引用——已切走）
    const panel = screen.getByTestId('citation-panel')
    expect(panel.textContent).toContain('本回合无引用')
    expect(within(panel).getByTestId('lineage-card')).toBeTruthy()
    expect(screen.queryByText('共 51 支引用 · 来自 2 处来源')).toBeNull()
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
})
