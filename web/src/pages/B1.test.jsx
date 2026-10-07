/**
 * 原型树 B1 任务卡测试（DE-06 切块自检告警进卡——G-02 branches 渲染位增量）：
 * - 违规 >0：展开任务卡出现「切块自检 N 条违规」行＋证据文件路径；
 * - 零违规（无 chunk_check 键）：任务卡不出现切块自检行。
 * 页面为原型树 mock 数据页（SEED_TASKS 卡住样例带 chunk_check 违规）——
 * 真组件真渲染，不抽函数桩。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import B1 from './B1.jsx'

// antd v5 在 jsdom 下的两个环境桩（同 landing/B1.test.jsx 惯例）
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

describe('B1 任务卡切块自检告警（DE-06）', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  afterEach(cleanup)

  it('违规 >0 显示「切块自检 N 条违规」＋证据路径；零违规任务不显示', async () => {
    render(<B1 />)
    // 切到入库任务页签
    fireEvent.click(await screen.findByText(/入库任务（\d+）/))
    // 零违规断言在先：展开无 branches 的失败任务——不出现切块自检行
    fireEvent.click(await screen.findByText('《N-11 井完井报告（英文 · 200 页）》'))
    expect(screen.queryByText(/切块自检 \d+ 条违规/)).toBeNull()
    // 违规态：展开带 chunk_check 的卡住任务——行出现且携证据文件路径
    fireEvent.click(await screen.findByText('《渤中28-1 区块月度生产月报（2026-07）》'))
    const row = await screen.findByText(/切块自检 2 条违规/)
    expect(row).toBeTruthy()
    expect(screen.getByText(/证据：\/tmp\/chunk_validate_task-ts01\.md/)).toBeTruthy()
  })
})
