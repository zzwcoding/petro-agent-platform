/**
 * ExecutionPipeline 钉测（执行流水线块——串行链条模型的中段）。
 *
 * 守什么：
 * - **三态**（渲染期 phaseOf 派生驱动）：running＝默认展开（尾部 Spin 续流行）／answering＝自动
 *   收起（首条正文到达即让位）／done＝默认收起、点摘要行可再展开回看全程；
 * - **摘要行**：状态词 · 步数 · 工具数 · 材料数 · ⚠提示数 · 本地计时（durationS 由页面传入）；
 * - **行渲染映射**：理解旁白／相位白话步／工具白话（缩进＋状态）／材料聚合／notice 三级小行／
 *   核验／落账引标——事件流＝turn.events（归约器直出到达序，本件不排序）；
 * - 空态：运行中且无事件＝「正在分析问题…」占位；非运行中且无事件＝整块不渲染（旧版降级轮）。
 *
 * 素材：redesign/mockTurns.js（真帧夹具＋归约器输出——FE-02 后条目＝{id, turn, durationS}）。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import { newTurnV2 } from '../a1v2Reducer.js'
import ExecutionPipeline from './ExecutionPipeline.jsx'
import { MOCK_TURNS } from './mockTurns.js'

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

afterEach(() => cleanup())

const LIVE = MOCK_TURNS.find(e => e.id === 't-live').turn
const FULL = MOCK_TURNS.find(e => e.id === 't-full').turn
const SPLIT = MOCK_TURNS.find(e => e.id === 't-split').turn
const LEGACY = MOCK_TURNS.find(e => e.id === 't-legacy').turn

describe('ExecutionPipeline · running 态（默认展开）', () => {
  it('默认展开：摘要行「执行中…」＋事件流向下长（理解/步/工具/材料/提示）＋尾部续流 Spin', () => {
    render(<ExecutionPipeline turn={LIVE} durationS={6.2} />)
    const bar = screen.getByTestId('pipeline-bar')
    expect(bar.textContent).toContain('执行中')
    expect(bar.textContent).toContain('7 步')
    expect(bar.textContent).toContain('1 次工具')
    expect(bar.textContent).toContain('16 份材料')
    expect(bar.textContent).toContain('⚠ 1 条提示')
    expect(bar.textContent).toContain('6.2s')

    const body = screen.getByTestId('pipeline-body') // 运行中＝默认展开
    expect(body).toBeTruthy()
    expect(screen.getByTestId('ev-understanding').textContent)
      .toContain('💭 理解为：问 W-11 井生产套管的尺寸与下深。') // text 帧的「理解：」前缀不再重出
    expect(screen.getByTestId('ev-step-1').textContent).toBe('分析问题 · 模型调用：understand')
    expect(screen.getByTestId('ev-step-7').textContent).toContain('取数')
    expect(screen.getByTestId('ev-tool-7').textContent).toContain('└ 查文档库')
    expect(screen.getByTestId('ev-tool-7').textContent).toContain('完成')
    expect(screen.getByTestId('ev-materials').textContent).toContain('📄 找到 16 份材料')
    expect(screen.getByTestId('pipeline-tail').textContent).toContain('继续处理中…')
  })

  it('运行中且尚无事件＝「正在分析问题…」占位（提问到首帧之间的形态）', () => {
    render(<ExecutionPipeline turn={newTurnV2('ask', 'x')} />)
    expect(screen.getByTestId('pipeline-waiting').textContent).toContain('正在分析问题…')
  })
})

describe('ExecutionPipeline · answering / done 态（自动收起，可再展开）', () => {
  it('done＝默认收起（事件流不在 DOM），摘要行完整', () => {
    render(<ExecutionPipeline turn={FULL} durationS={18.5} />)
    expect(screen.queryByTestId('pipeline-body')).toBeNull()
    const bar = screen.getByTestId('pipeline-bar')
    expect(bar.textContent).toContain('执行完成')
    expect(bar.textContent).toContain('12 步')
    expect(bar.textContent).toContain('51 份材料')
    expect(bar.textContent).toContain('⚠ 4 条提示')
    expect(bar.textContent).toContain('18.5s')
    expect(bar.getAttribute('aria-expanded')).toBe('false')
  })

  it('点摘要行＝展开回看全程（到达序原样）；再点＝收起（用户定态优先）', () => {
    render(<ExecutionPipeline turn={FULL} />)
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    const body = screen.getByTestId('pipeline-body')
    expect(body).toBeTruthy()
    expect(body.querySelectorAll('[data-testid^="ev-step-"]')).toHaveLength(12)
    // 真机到达序钉：tool(seq8) 行先于其承载 step(seq8) 行（G4——不补排序）
    const rows = [...body.children]
    expect(rows.findIndex(n => n.dataset.testid === 'ev-tool-8'))
      .toBeLessThan(rows.findIndex(n => n.dataset.testid === 'ev-step-8'))
    expect(screen.getByTestId('ev-verify').textContent).toBe('✅ 核验完成：有据 51 条 · 改写 0 条')
    expect(screen.getByTestId('ev-citation-51').textContent).toContain('落账引标 [51]')
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    expect(screen.queryByTestId('pipeline-body')).toBeNull()
  })

  it('answering＝自动收起（首条答案正文到达即让位给正文）＋状态词「作答中」', () => {
    render(<ExecutionPipeline turn={{ ...FULL, closed: null }} />)
    expect(screen.queryByTestId('pipeline-body')).toBeNull()
    expect(screen.getByTestId('pipeline-bar').textContent).toContain('作答中')
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    expect(screen.getByTestId('pipeline-body')).toBeTruthy() // 想看仍可点开
  })
})

describe('ExecutionPipeline · 行渲染映射与空态', () => {
  it('notice 三级行：A 级彩线小行、C 级默认收起（展开见原文）', () => {
    render(<ExecutionPipeline turn={FULL} />)
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    const aRow = screen.getAllByTestId('notice-row-a')[0]
    expect(aRow.textContent).toContain('这次回答只用到检索到的 24/37 条材料') // A 级原文直给
    expect(screen.getByText('说明（window_note）')).toBeTruthy() // B 级折叠小行
    expect(screen.getByText('系统注记（unsupported_claim）· 点开看原文')).toBeTruthy() // C 级
    fireEvent.click(screen.getByText('系统注记（unsupported_claim）· 点开看原文'))
    expect(screen.getByText(/理解步指标候选出现名录外名字/)).toBeTruthy()
  })

  it('分列轮：材料聚合 18 份、核验行含分列计数（>0 才出）', () => {
    const patched = {
      ...SPLIT,
      events: SPLIT.events.map(e => (e.type === 'verify'
        ? { ...e, verdict: { supported: 4, rewritten: 2, split: 3 } }
        : e))
    }
    render(<ExecutionPipeline turn={patched} />)
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    expect(screen.getByTestId('ev-materials').textContent).toContain('📄 找到 18 份材料')
    expect(screen.getByTestId('ev-verify').textContent)
      .toBe('✅ 核验完成：有据 4 条 · 改写 2 条 · 分列 3 条')
  })

  it('未登记相位＝原样回显（不吞、不猜白话）', () => {
    render(<ExecutionPipeline turn={{
      closed: 'done',
      steps: [{ seq: 1, station: 'weird_phase', title: 't' }],
      events: [{ type: 'step', seq: 1, phase: 'weird_phase', title: 't' }]
    }} />)
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    expect(screen.getByTestId('ev-step-1').textContent).toContain('weird_phase')
  })

  it('未登记工具名/状态＝原样回显（不吞）', () => {
    render(<ExecutionPipeline turn={{
      closed: 'done',
      steps: [{ seq: 3, station: 'execute', title: 'weird_tool：ok' }],
      tools: [{ seq: 3, tool: 'weird_tool', status: 'weird_status', message: 'note' }],
      events: [
        { type: 'step', seq: 3, phase: 'execute', title: 'weird_tool：ok' },
        { type: 'tool', seq: 3, tool: 'weird_tool', status: 'weird_status', message: 'note' }
      ]
    }} />)
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    const row = screen.getByTestId('ev-tool-3').textContent
    expect(row).toContain('└ weird_tool')
    expect(row).toContain('weird_status')
    expect(row).toContain('（note）')
  })

  it('旧版降级轮（非运行中且无事件）＝整块不渲染', () => {
    const { container } = render(<ExecutionPipeline turn={LEGACY} />)
    expect(container.firstChild).toBeNull()
  })
})
