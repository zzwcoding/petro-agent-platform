/**
 * A1V2R 页面钉测（串行链条 mock 静态版面页——临时路由）。
 *
 * 守什么（本页红线，机器可验）：
 * - **零请求**：全页数据来自 redesign/mockTurns.js——不接 SSE、不调 `/api/v2/*`（stub fetch 断言零次）；
 * - **链条顺序**：每轮＝用户输入块 → 系统执行流水线块 → 系统回答块；回答块内＝A 级 notice Alert →
 *   正文 → 血缘卡 → 追加面 → 核验/档案小字（DOM 序断言）；
 * - 四轮覆盖：①运行中（流水线展开、回答块「正在作答…」占位）②完整轮（流水线收起、链条完整）
 *   ③分列轮（长 split 限高）④旧版降级（无流水线、无引用、[n] 死文本）；
 * - 引标联动：点正文 [n] ＝右栏面板切到该轮并「已定位」；
 * - A 级 notice 在回答块顶部可见（折叠态流水线下也感知可信度），B/C 级只在流水线里；
 * - 右栏「决策树」入口在位（mock 点开说明 Modal）。
 */
/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'

import A1V2R from './A1V2R.jsx'
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
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
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
    const round = screen.getByTestId('round-t-running')
    const pipeline = round.querySelector('[data-testid="pipeline"]')
    expect(pipeline).toBeTruthy()
    expect(within(pipeline).getByTestId('pipeline-body')).toBeTruthy() // 展开态
    expect(within(pipeline).getByTestId('ev-understanding').textContent).toContain('💭 理解为：')
    expect(within(pipeline).getByTestId('ev-materials').textContent).toContain('16 份材料')
    expect(within(pipeline).getByTestId('pipeline-tail').textContent).toContain('继续处理中…')

    const answerBlock = screen.getByTestId('turn-t-running')
    expect(within(answerBlock).getByTestId('answer-placeholder').textContent).toBe('正在作答…')
    expect(within(answerBlock).queryByTestId('answer-view')).toBeNull()
    expect(within(answerBlock).queryByTestId('run-meta-line')).toBeNull() // 未收口＝无核验/档案小字
  })
})

describe('A1V2R · 其余三轮形态', () => {
  it('四轮都在位；分列轮长 split 限高；旧版轮无流水线＋降级说明；全程零请求', () => {
    render(<A1V2R />)
    for (const id of ['t-running', 't-full', 't-split', 't-legacy']) {
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

describe('A1V2R · 左侧历史对话（上拉加载＋搜索）', () => {
  it('左栏＝ThreadList：初始 20 条、搜索框在位、加载入口在位；点行＝高亮切换', () => {
    render(<A1V2R />)
    const list = screen.getByTestId('thread-list')
    expect(within(list).getAllByTestId(/^thread-row-/)).toHaveLength(20)
    expect(within(list).getByPlaceholderText('搜索对话')).toBeTruthy()
    expect(within(list).getByTestId('load-more')).toBeTruthy()
    // 首页行＝运行中轮的问句（选中）
    const first = within(list).getByTestId(`thread-row-${MOCK_RUNS[0].run_id}`)
    expect(first.dataset.selected).toBe('true')
    fireEvent.click(within(list).getByTestId(`thread-row-${MOCK_RUNS[3].run_id}`))
    expect(within(list).getByTestId(`thread-row-${MOCK_RUNS[3].run_id}`).dataset.selected).toBe('true')
    expect(within(list).getByTestId(`thread-row-${MOCK_RUNS[0].run_id}`).dataset.selected).toBe('false')
    expect(fetchMock).not.toHaveBeenCalled() // 全假数据——不真拉列表
  })

  it('左栏搜索＝前端过滤（不发请求）', () => {
    render(<A1V2R />)
    fireEvent.change(screen.getByPlaceholderText('搜索对话'), { target: { value: '含水率' } })
    const hit = MOCK_RUNS.slice(0, 20).filter(r => r.question.includes('含水率'))
    expect(screen.getAllByTestId(/^thread-row-/)).toHaveLength(hit.length)
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
