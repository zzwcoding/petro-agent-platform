/**
 * ProcessTimeline 钉测（过程折叠条——重设计核心件）。
 *
 * 守什么：
 * - 折叠态一行摘要＝状态词 · 引用篇数（去重来源数）· 步数 · 工具数 · 本地计时；
 *   无引用时退「N 步 · M 次工具」（不出「引用了 0 篇」）。
 * - 展开态＝antd Timeline 树状：步＝白话相位名＋原文标题，工具挂同 seq 步下（白话工具名），
 *   **C 级 notice 收进对应步下**（工序腔原文，不丢）。
 * - 加载中（进行中且无步）＝Spin＋「正在分析问题…」占位（不展开、不出假步数）。
 * - 空态（无步无工具且非加载中）＝整行不渲染。
 *
 * 素材：redesign/mockTurns.js（真机帧抽出）——完整轮/加载轮两组。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import ProcessTimeline from './ProcessTimeline.jsx'
import { MOCK_TURNS } from './mockTurns.js'

// antd v5 在 jsdom 下的两个环境桩（同 landing/A1V2.test.jsx）
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

const FULL = MOCK_TURNS.find(t => t.id === 't-full')
const LOADING = MOCK_TURNS.find(t => t.id === 't-loading')

describe('ProcessTimeline · 折叠态摘要', () => {
  it('摘要＝检索完成 · 引用了 2 篇文档 · 12 步 · 1 次工具 · 18.5s（篇数＝去重来源数）', () => {
    render(<ProcessTimeline steps={FULL.steps} tools={FULL.tools} notices={FULL.notices}
      citations={FULL.citations} durationS={FULL.durationS} />)
    const bar = screen.getByTestId('process-timeline-bar')
    expect(bar.textContent).toContain('检索完成')
    expect(bar.textContent).toContain('引用了 2 篇文档')
    expect(bar.textContent).toContain('12 步')
    expect(bar.textContent).toContain('1 次工具')
    expect(bar.textContent).toContain('18.5s')
    expect(screen.queryByTestId('process-timeline-body')).toBeNull() // 默认折叠
  })

  it('无引用＝退「N 步 · M 次工具」（不出「引用了 0 篇文档」）', () => {
    render(<ProcessTimeline steps={[{ seq: 1, station: 'decision', title: '模型调用：understand' }]} />)
    const bar = screen.getByTestId('process-timeline-bar')
    expect(bar.textContent).toContain('1 步')
    expect(bar.textContent).not.toContain('引用了')
  })

  it('进行中且无步＝Spin＋「正在分析问题…」占位（不展开、不出步数）', () => {
    render(<ProcessTimeline steps={[]} tools={[]} running />)
    expect(screen.getByText('正在分析问题…')).toBeTruthy()
    expect(screen.getByTestId('process-timeline-bar').textContent).not.toContain('步')
    fireEvent.click(screen.getByTestId('process-timeline-bar'))
    expect(screen.queryByTestId('process-timeline-body')).toBeNull() // 占位态不可展开
  })

  it('空态（无步无工具且非加载中）＝整行不渲染', () => {
    const { container } = render(<ProcessTimeline steps={[]} tools={[]} />)
    expect(container.firstChild).toBeNull()
  })
})

describe('ProcessTimeline · 展开态树状时间线', () => {
  it('展开＝白话相位标题＋原文标题＋同 seq 工具行（白话工具名）＋步状态 ✓', () => {
    render(<ProcessTimeline steps={FULL.steps} tools={FULL.tools} notices={FULL.notices}
      citations={FULL.citations} durationS={FULL.durationS} />)
    fireEvent.click(screen.getByTestId('process-timeline-bar'))

    const body = screen.getByTestId('process-timeline-body')
    expect(body.textContent).toContain('分析问题') // decision 相位白话
    expect(body.textContent).toContain('取数') // execute 相位白话
    expect(body.textContent).toContain('核验') // verify 相位白话
    expect(body.textContent).toContain('模型调用：understand') // 原文标题（可追溯）
    expect(body.textContent).toContain('└ 取数：完成') // data_query 工具白话＋状态
  })

  it('C 级 notice 收进对应步下（核验相位）——工序腔原文不丢', () => {
    render(<ProcessTimeline steps={FULL.steps} tools={FULL.tools} notices={FULL.notices} />)
    fireEvent.click(screen.getByTestId('process-timeline-bar'))
    const body = screen.getByTestId('process-timeline-body')
    expect(body.textContent).toContain('系统注记（unsupported_claim）')
    expect(body.textContent).toContain('核验步删去无据断言 2 行')
    expect(body.textContent).toContain('系统注记（contradiction_split）')
  })

  it('A/B 级 notice 不进时间线（由 NoticeBand 出，不重复占位）', () => {
    render(<ProcessTimeline steps={FULL.steps} tools={FULL.tools} notices={FULL.notices} />)
    fireEvent.click(screen.getByTestId('process-timeline-bar'))
    expect(screen.getByTestId('process-timeline-body').textContent).not.toContain('窗口注记')
    expect(screen.getByTestId('process-timeline-body').textContent).not.toContain('material_truncated')
  })

  it('失败工具＝✗ 且如实写「失败」（不吞失败态）', () => {
    render(<ProcessTimeline steps={[{ seq: 7, station: 'execute', title: 'doc_retrieve：失败' }]}
      tools={[{ seq: 7, tool: 'doc_retrieve', status: 'failed', message: 'timeout' }]} />)
    fireEvent.click(screen.getByTestId('process-timeline-bar'))
    expect(screen.getByTestId('process-timeline-body').textContent).toContain('└ 查文档库：失败（timeout）')
  })

  it('加载轮（真机 mock 同上）：进行中回合的最后一步＝Spin（进行中态可视）', () => {
    render(<ProcessTimeline steps={FULL.steps} tools={FULL.tools} running durationS={null} />)
    fireEvent.click(screen.getByTestId('process-timeline-bar'))
    expect(screen.getByTestId('process-timeline-bar').textContent).toContain('检索中')
  })
})

describe('ProcessTimeline · 真机 mock 数据源在位', () => {
  it('加载轮 mock 无步无工具（占位态数据面）', () => {
    expect(LOADING.steps).toHaveLength(0)
    expect(LOADING.tools).toHaveLength(0)
    expect(LOADING.runStatus).toBe('running')
  })
})
