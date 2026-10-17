/**
 * ExecutionPipeline 钉测（执行流水线块——串行链条模型的中段）。
 *
 * 守什么：
 * - **三态**（渲染期 phaseOf 派生驱动）：running＝默认展开（尾部 Spin 续流行）／answering＝自动
 *   收起（首条正文到达即让位）／done＝默认收起、点摘要行可再展开回看全程；
 * - **摘要行**：状态词 · 步数 · 工具数 · 材料数 · ⚠可见提示数（隐藏型不计） · 本地计时（durationS 由页面传入）；
 * - **行渲染映射**：理解旁白／相位白话步／工具白话（缩进＋状态）／材料聚合／notice 小行／
 *   核验／落账引标——事件流＝turn.events（归约器直出到达序，本件不排序）；
 * - **四类折叠**（Owner 打磨批④⑤⑥）：连续 citation 段→「🔖 落账引标 N 条 · 来自 M 处来源」、
 *   连续同（相位＋标题）步→「… ×N」、连续 materials 段→「📄 检索到材料 a · b 份（N 次子检索）」、
 *   B/C/未登记 notice→灰纯文本行（点开内联原文，无 Collapse 盒）；隐藏型 notice 行不出；
 * - 空态：运行中且无事件＝「正在分析问题…」占位；非运行中且无事件＝整块不渲染（旧版降级轮）。
 *
 * 素材：__fixtures__/turns.js 的 FIXTURE_TURNS（真帧夹具＋归约器输出——条目＝{id, turn, durationS}）。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import { newTurnV2 } from '../a1v2Reducer.js'
import ExecutionPipeline from './ExecutionPipeline.jsx'
import { FIXTURE_TURNS } from './__fixtures__/turns.js'

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

const LIVE = FIXTURE_TURNS.find(e => e.id === 't-live').turn
const FULL = FIXTURE_TURNS.find(e => e.id === 't-full').turn
const SPLIT = FIXTURE_TURNS.find(e => e.id === 't-split').turn
const LEGACY = FIXTURE_TURNS.find(e => e.id === 't-legacy').turn

describe('ExecutionPipeline · running 态（默认展开）', () => {
  it('默认展开：摘要行「执行中…」＋事件流向下长（理解/步/工具/材料/提示）＋尾部续流 Spin', () => {
    render(<ExecutionPipeline turn={LIVE} durationS={6.2} />)
    const bar = screen.getByTestId('pipeline-bar')
    expect(bar.textContent).toContain('执行中')
    expect(bar.textContent).toContain('7 步')
    expect(bar.textContent).toContain('1 次工具')
    expect(bar.textContent).toContain('16 份材料')
    expect(bar.textContent).toContain('⚠ 1 条提示') // LIVE 唯一 notice＝C 级（可见）
    expect(bar.textContent).toContain('6.2s')

    const body = screen.getByTestId('pipeline-body') // 运行中＝默认展开
    expect(body).toBeTruthy()
    expect(screen.getByTestId('ev-understanding').textContent)
      .toContain('💭 理解为：问 W-11 井生产套管的尺寸与下深。') // text 帧的「理解：」前缀不再重出
    expect(screen.getByTestId('ev-step-1').textContent).toBe('分析问题 · 模型调用：understand')
    expect(screen.getByTestId('ev-step-7').textContent).toContain('取数')
    expect(screen.getByTestId('ev-tool-7').textContent).toContain('└ 查文档库')
    expect(screen.getByTestId('ev-tool-7').textContent).toContain('完成')
    expect(screen.getByTestId('ev-materials').textContent).toContain('📄 检索到材料 16 份')
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
    // 4 条 notice 里 material_truncated 属隐藏型（打磨批⑧）→ 可见提示 3 条
    expect(bar.textContent).toContain('⚠ 3 条提示')
    expect(bar.textContent).toContain('18.5s')
    expect(bar.getAttribute('aria-expanded')).toBe('false')
  })

  it('点摘要行＝展开回看全程（到达序原样）；再点＝收起（用户定态优先）', () => {
    render(<ExecutionPipeline turn={FULL} />)
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    const body = screen.getByTestId('pipeline-body')
    expect(body).toBeTruthy()
    expect(body.querySelectorAll('[data-testid^="ev-step-"]')).toHaveLength(12) // 真机 12 步标题各不相同＝零折叠
    // 真机到达序钉：tool(seq8) 行先于其承载 step(seq8) 行（G4——不补排序）
    const rows = [...body.children]
    expect(rows.findIndex(n => n.dataset.testid === 'ev-tool-8'))
      .toBeLessThan(rows.findIndex(n => n.dataset.testid === 'ev-step-8'))
    expect(screen.getByTestId('ev-verify').textContent).toBe('✅ 核验完成：有据 51 条 · 改写 0 条')
    // 51 条连续引用折成一行（打磨批④）：计数＋去重来源数（真机两处来源）
    expect(screen.getByTestId('ev-citations').textContent).toBe('🔖 落账引标 51 条 · 来自 2 处来源')
    expect(body.querySelectorAll('[data-testid^="ev-citation-"]')).toHaveLength(0) // 逐条行不再出
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
  it('notice 行：A 级彩条小行（原文直给）；B/C 级灰纯文本行（点开内联原文、再点收起，无 Collapse 盒）', () => {
    const patched = {
      ...FULL,
      events: FULL.events.map(e => (e.type === 'notice' && e.notice.type === 'material_truncated'
        ? { ...e, notice: { ...e.notice, type: 'refused' } } // 借 A 级可见型（material_truncated 已隐藏）
        : e))
    }
    render(<ExecutionPipeline turn={patched} />)
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    const aRow = screen.getAllByTestId('notice-row-a')[0]
    expect(aRow.textContent).toContain('这次回答只用到检索到的 24/37 条材料') // A 级原文直给
    expect(aRow.style.borderLeft).toContain('3px') // 彩条样式不动
    expect(document.querySelector('.ant-collapse')).toBeNull() // 注记行不再是 Collapse 边框盒
    const plain = screen.getAllByTestId('notice-row-plain')
    expect(plain.map(el => el.textContent)).toEqual([
      '⚙ 系统注记（unsupported_claim）· 点开看原文', // C 级
      '⚙ 系统注记（window_note）· 点开看原文', // B 级并入统一注记行（打磨批⑥）
      '⚙ 系统注记（contradiction_split）· 点开看原文'
    ])
    expect(screen.queryByText(/理解步指标候选出现名录外名字/)).toBeNull() // 原文默认收起
    // 点开＝原文内联（不是 Collapse 面板）；再点＝收起
    fireEvent.click(screen.getByText('⚙ 系统注记（unsupported_claim）· 点开看原文'))
    expect(screen.getByText(/理解步指标候选出现名录外名字/)).toBeTruthy()
    fireEvent.click(screen.getByText('⚙ 系统注记（unsupported_claim）· 点开看原文'))
    expect(screen.queryByText(/理解步指标候选出现名录外名字/)).toBeNull()
  })

  it('pipeline_hidden_notice_absent：隐藏型 notice 整行不出——展示口径，原数据不动', () => {
    render(<ExecutionPipeline turn={FULL} />)
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    expect(screen.queryByText(/只用到检索到的 24\/37 条材料/)).toBeNull() // 该条＝material_truncated（隐藏）
    expect(screen.queryAllByTestId('notice-row-a')).toHaveLength(0)
    cleanup()
    // emission_strip 同样不出（合成流）；原数据仍在（组件不改 turn）
    const strip = { type: 'emission_strip', content: '剥离发射 JSON' }
    const turn = { closed: 'done', notices: [strip], events: [{ type: 'notice', notice: strip }] }
    render(<ExecutionPipeline turn={turn} />)
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    expect(screen.queryByText('剥离发射 JSON')).toBeNull()
    expect(screen.queryAllByTestId('notice-row-plain')).toHaveLength(0)
    expect(turn.notices).toEqual([strip])
    expect(FULL.events.some(e => e.type === 'notice' && e.notice.type === 'material_truncated')).toBe(true)
  })

  it('pipeline_fold_four_kinds · 材料行合并：连续 materials 事件折一行「检索到材料 32 · 36 · 38 · 32 份（4 次子检索）」', () => {
    render(<ExecutionPipeline turn={{
      closed: 'done',
      materials: [1, 2, 3, 4],
      events: [
        { type: 'materials', count: 32 }, { type: 'materials', count: 36 },
        { type: 'materials', count: 38 }, { type: 'materials', count: 32 }
      ]
    }} />)
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    expect(screen.getAllByTestId('ev-materials')).toHaveLength(1)
    expect(screen.getByTestId('ev-materials').textContent)
      .toContain('📄 检索到材料 32 · 36 · 38 · 32 份（4 次子检索）')
  })

  it('pipeline_fold_four_kinds · 重复步合并：连续同（相位＋标题）步折一行挂「×N」（单条不挂）', () => {
    render(<ExecutionPipeline turn={{
      closed: 'done',
      steps: [1, 2, 3, 4].map(seq => ({ seq, station: 'decision', title: '模型调用：decision' })),
      events: [
        { type: 'step', seq: 1, phase: 'decision', title: '模型调用：decision' },
        { type: 'step', seq: 2, phase: 'decision', title: '模型调用：decision' },
        { type: 'step', seq: 3, phase: 'decision', title: '模型调用：decision' },
        { type: 'step', seq: 4, phase: 'decision', title: '模型调用：understand' }
      ]
    }} />)
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    expect(screen.getByTestId('ev-step-1').textContent).toBe('分析问题 · 模型调用：decision ×3')
    expect(screen.getByTestId('ev-step-4').textContent).toBe('分析问题 · 模型调用：understand') // 单条不挂 ×N
  })

  it('pipeline_fold_four_kinds · 落账引标合并：不跨段——两段引用各一行', () => {
    render(<ExecutionPipeline turn={{
      closed: 'done',
      events: [
        { type: 'citation', cite: { index: 1, source: '甲' } },
        { type: 'citation', cite: { index: 2, source: '甲' } },
        { type: 'step', seq: 1, phase: 'answer', title: '答案收口' },
        { type: 'citation', cite: { index: 3, source: '乙' } }
      ]
    }} />)
    fireEvent.click(screen.getByTestId('pipeline-bar'))
    expect(screen.getAllByTestId('ev-citations').map(el => el.textContent)).toEqual([
      '🔖 落账引标 2 条 · 来自 1 处来源',
      '🔖 落账引标 1 条 · 来自 1 处来源'
    ])
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
    expect(screen.getByTestId('ev-materials').textContent).toContain('📄 检索到材料 18 份')
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
