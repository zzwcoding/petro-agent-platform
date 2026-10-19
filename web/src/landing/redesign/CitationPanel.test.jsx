/**
 * CitationPanel 钉测（右栏「引用与口径」——设计稿 §2 方案 A、§3.3）。
 *
 * 守什么：
 * - 引用**按 source 分组**（组头＝来源＋支数；**trust 白话徽标不上屏**——Owner 2026-10-19 打磨批⑩）；
 * - 点某条＝该条高亮＋「已定位」并出材料原文；`trust=notice` 的按**程序声明**渲染
 *   （点明不是文档原文）；无配对材料＝如实写「材料未在回合内渲染」；
 * - 外部联动（正文引标点击传 focusIndex）＝面板自动定位该条；
 * - 面板内含血缘卡与**各来源说法不一**（split）块——**打磨批③**：「按来源列出」（attribution）
 *   块整块退场（与引用清单同源重复），split 是右栏唯一出现处（原先在中栏的追加面整个移除）；
 * - split 块默认收起、单条限高（真机长条 >6 行/240 字）、短条不出开关、前导说明照录；
 * - 决策树入口在位（mock 点开说明 Modal）；
 * - 空态＝「本回合无引用」；进行中＝「检索中…」。
 *
 * 素材：__fixtures__/turns.js 真帧夹具——EB3-数-降1（16 支引用 5 处来源，含一条 trust=notice／
 * 长 split 条）／EB4-数-明2（含血缘与追加面）；FE-02 后 FIXTURE_TURNS 条目＝{id, turn, durationS}。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import CitationPanel from './CitationPanel.jsx'
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

const FULL = FIXTURE_TURNS.find(t => t.id === 't-full').turn
/** 血缘结构化源（对账 D-5）：materials[].payload（FE-02 起 lineage/limit 从此取）。 */
const FULL_PAYLOAD = FULL.materials.find(m => m.payload?.lineage).payload
const SPLIT = FIXTURE_TURNS.find(t => t.id === 't-split').turn
const LEGACY = FIXTURE_TURNS.find(t => t.id === 't-legacy').turn

describe('CitationPanel · 分组与条数（trust 徽标不上屏——Owner 2026-10-19 打磨批⑩）', () => {
  it('按 source 分组：组头＝来源＋支数；组头无 trust 白话徽标（四值一律不出）', () => {
    render(<CitationPanel citations={SPLIT.citations} materials={SPLIT.materials} />)
    expect(screen.getByText('共 16 支引用 · 来自 5 处来源')).toBeTruthy()
    expect(screen.getByText('《A-W11井完井工程报告》')).toBeTruthy()
    expect(screen.getByText('检索供给窗声明（截断显式）')).toBeTruthy()
    // 组头只出「来源 · N 支」——报告/台账/权威台账/系统注记四个白话徽标一律不上屏
    expect(screen.queryByText('报告')).toBeNull()
    expect(screen.queryByText('权威台账')).toBeNull()
    expect(screen.queryByText('系统注记')).toBeNull()
    expect(screen.getByText('《A-W11井完井工程报告》').parentElement.textContent)
      .toBe('《A-W11井完井工程报告》 · 5 支') // 组头只出「来源 · N 支」
  })

  it('点某条＝高亮＋「已定位」＋出该条材料原文（citation↔observation 按 index 配对）', () => {
    render(<CitationPanel citations={FULL.citations} materials={FULL.materials} />)
    expect(screen.queryByText('已定位')).toBeNull()
    fireEvent.click(screen.getByTestId('cite-item-2'))
    expect(screen.getByTestId('cite-item-2').textContent).toContain('已定位')
    expect(screen.getByTestId('cite-item-2').textContent).toContain('井号=N-02；区块=渤南；日期=2026-01-01；日产液量（方）=48.72')
  })

  it('trust=notice 的条目按程序声明渲染（点明不是文档原文）', () => {
    render(<CitationPanel citations={SPLIT.citations} materials={SPLIT.materials} />)
    fireEvent.click(screen.getByTestId('cite-item-17'))
    const item = screen.getByTestId('cite-item-17')
    expect(item.textContent).toContain('系统生成的声明，不是文档原文')
    expect(item.textContent).toContain('以下材料来源说法不一，各保留了代表条目：') // 该条材料＝检索供给窗声明原文
    expect(screen.queryByText('系统注记')).toBeNull() // 组头不再出 trust 白话徽标（点明靠上面那句文本）
  })

  it('无配对材料＝如实写「材料未在回合内渲染」（不虚构材料内容）', () => {
    render(<CitationPanel citations={[SPLIT.citations[0]]} materials={[]} />)
    fireEvent.click(screen.getByTestId('cite-item-1'))
    expect(screen.getByTestId('cite-item-1').textContent).toContain('（材料未在回合内渲染）')
  })

  it('外部联动：focusIndex 传入＝该条自动定位（正文引标点击的落点）', () => {
    const { rerender } = render(<CitationPanel citations={FULL.citations} materials={FULL.materials} />)
    rerender(<CitationPanel citations={FULL.citations} materials={FULL.materials} focusIndex={51} />)
    expect(screen.getByTestId('cite-item-51').textContent).toContain('已定位')
  })

  it('split_only_right_panel：面板内含血缘卡与各来源说法不一（split）块；「按来源列出」已整块退场', () => {
    render(<CitationPanel citations={FULL.citations} materials={FULL.materials}
      lineage={FULL_PAYLOAD.lineage} limit={FULL_PAYLOAD.limit}
      lineageText={FULL.supplements.lineage} splitText={FULL.supplements.split} />)
    expect(screen.getByTestId('lineage-card')).toBeTruthy()
    expect(screen.getByTestId('supp-split-block')).toBeTruthy() // 各来源说法不一＝右栏唯一出现处
    expect(screen.getByText('各来源说法不一 · 点开对照')).toBeTruthy()
    // 「按来源列出」（attribution）块已整块退场（打磨批③——与引用清单同源重复）
    expect(screen.queryByText('按来源列出（每条结论标明出处）')).toBeNull()
    expect(screen.queryByTestId('supp-attribution')).toBeNull()
    expect(screen.queryByTestId('supplement-blocks')).toBeNull()
  })

  it('split 块默认收起；展开＝逐条 [n]＋来源＋原文（前导说明照录）', () => {
    render(<CitationPanel citations={FULL.citations} materials={FULL.materials}
      splitText={FULL.supplements.split} />)
    expect(screen.queryByTestId('supp-split')).toBeNull() // 默认收起（次要位不抢引用清单）
    fireEvent.click(screen.getByText('各来源说法不一 · 点开对照'))
    const box = screen.getByTestId('supp-split')
    expect(box.textContent).toContain('互不一致——各来源说法如下，按来源分别列出：') // 前导说明照录
    expect(screen.getByTestId('supp-item-22').dataset.clamped).toBe('false') // 短条不限高
    expect(screen.queryByText(/展开看全文/)).toBeNull() // 短条不出多余开关
  })

  it('split 长条（真机 340 字）＝限高态（-webkit-line-clamp 6）＋「展开看全文」（只影响该条）', () => {
    render(<CitationPanel citations={SPLIT.citations} materials={SPLIT.materials}
      splitText={SPLIT.supplements.split} />)
    fireEvent.click(screen.getByText('各来源说法不一 · 点开对照'))
    const item = screen.getByTestId('supp-item-9')
    expect(item.dataset.clamped).toBe('true')
    expect(item.style.webkitLineClamp).toBe('6')
    expect(item.textContent).toContain('4.2 防砂方式与参数')
    expect(screen.getByTestId('supp-split').textContent).toContain('《A-W11井完井工程报告》') // 条目带来源名
    fireEvent.click(screen.getAllByText(/展开看全文/)[0])
    expect(screen.getByTestId('supp-item-9').dataset.clamped).toBe('false')
    expect(screen.getByTestId('supp-item-13').dataset.clamped).toBe('true') // 不越权展开别的条
  })

  it('无 split 文本＝该块不出（不报错不伪造）', () => {
    render(<CitationPanel citations={FULL.citations} materials={FULL.materials} />)
    expect(screen.queryByTestId('supp-split-block')).toBeNull()
  })

  it('决策树入口在位（占位 Modal——真树本体接回在后续版本）', () => {
    render(<CitationPanel citations={[]} materials={[]} />)
    fireEvent.click(screen.getByRole('button', { name: /决策树/ }))
    expect(screen.getByText('决策树（占位）')).toBeTruthy()
  })
})

describe('CitationPanel · 空态', () => {
  it('无引用＝「本回合无引用。」（旧版历史轮同形）', () => {
    render(<CitationPanel citations={LEGACY.citations} materials={LEGACY.materials} />)
    expect(screen.getByText('本回合无引用。')).toBeTruthy()
    expect(screen.queryByTestId('lineage-card')).toBeNull()
  })

  it('进行中＝「检索中——材料到位后这里出引用清单。」', () => {
    render(<CitationPanel citations={[]} materials={[]} running />)
    expect(screen.getByText('检索中——材料到位后这里出引用清单。')).toBeTruthy()
  })
})
