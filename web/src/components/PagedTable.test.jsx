/**
 * PagedTable 组件直测（UI-00——方案-阶段1交互优化 §2.1 五组断言逐组落）：
 * ① client 切片翻页（23 行 pageSize 20 → 第 2 页 3 行；单页也恒显分页条＋「共 N 条」）；
 * ② resetKey 变化归页 1（筛条件联动）；
 * ③ 超界钳制（第 2 页停驻时数据缩短至 5 行 → 自动归页 1 非空表）；
 * ④ error 非空时空态描述切 errorEmptyText（缺省「数据拉取失败」）；
 * ⑤ server 模式受控（page/pageSize/total 驱动渲染，onPageChange(page, pageSize) 上抛）。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import PagedTable from './PagedTable.jsx'
import { ApiError } from '../api/client.js'

// antd v5 在 jsdom 下的两个环境桩（同 B1.test.jsx：matchMedia＝响应式断点；ResizeObserver＝Table 测宽）
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

const COLS = [{ title: '名称', dataIndex: 'name' }]
const rows = n => Array.from({ length: n }, (_, i) => ({ id: `r${i + 1}`, name: `行${i + 1}` }))
const rowCount = container => container.querySelectorAll('.ant-table-tbody tr.ant-table-row').length

beforeEach(() => {})
afterEach(() => { cleanup() })

describe('PagedTable（UI-00 共享分页封装）', () => {
  it('① client 切片翻页：23 行/pageSize 20 → 第 2 页 3 行；单页数据分页条恒显且统计「共 N 条」', () => {
    const { container, rerender } = render(
      <PagedTable dataSource={rows(3)} columns={COLS} rowKey="id" emptyText="还没有数据" />
    )
    // hideOnSinglePage=false：单页（3 行）分页条仍显示，统计为「共 3 条」
    expect(container.querySelector('.ant-pagination')).toBeTruthy()
    expect(screen.getByText('共 3 条')).toBeTruthy()

    rerender(<PagedTable dataSource={rows(23)} columns={COLS} rowKey="id" emptyText="还没有数据" />)
    expect(rowCount(container)).toBe(20) // 第 1 页内存切片 20 行
    expect(screen.getByText('共 23 条')).toBeTruthy()

    fireEvent.click(container.querySelector('.ant-pagination-item-2'))
    expect(rowCount(container)).toBe(3) // 第 2 页剩 3 行
    expect(screen.getByText('行21')).toBeTruthy()
  })

  it('② resetKey 变化归页 1（显式筛条件联动）', () => {
    const { container, rerender } = render(
      <PagedTable dataSource={rows(23)} columns={COLS} rowKey="id" emptyText="x" resetKey="a" />
    )
    fireEvent.click(container.querySelector('.ant-pagination-item-2'))
    expect(rowCount(container)).toBe(3)

    rerender(<PagedTable dataSource={rows(23)} columns={COLS} rowKey="id" emptyText="x" resetKey="b" />)
    expect(rowCount(container)).toBe(20) // 页码随 resetKey 变化归 1
  })

  it('③ 超界钳制：第 2 页停驻时数据缩短至 5 行 → 自动归页 1 非空表（隐式筛变兜底）', () => {
    const { container, rerender } = render(
      <PagedTable dataSource={rows(23)} columns={COLS} rowKey="id" emptyText="x" />
    )
    fireEvent.click(container.querySelector('.ant-pagination-item-2'))
    expect(rowCount(container)).toBe(3)

    // 不改 resetKey（隐式筛变——resetKey 覆盖不到的场景）直接缩短数据
    rerender(<PagedTable dataSource={rows(5)} columns={COLS} rowKey="id" emptyText="x" />)
    expect(rowCount(container)).toBe(5) // 钳制归页 1，非空表
    expect(screen.getByText('行1')).toBeTruthy()
    expect(screen.queryByText('行6')).toBeNull()
  })

  it('④ error 非空时空态描述切 errorEmptyText（缺省「数据拉取失败」）', () => {
    const { rerender } = render(
      <PagedTable dataSource={[]} columns={COLS} rowKey="id" emptyText="还没有报告入库" />
    )
    expect(screen.getByText('还没有报告入库')).toBeTruthy()

    rerender(
      <PagedTable dataSource={[]} columns={COLS} rowKey="id" emptyText="还没有报告入库"
        error={new ApiError(500, { code: 'kb_x', message: '拉取失败', trace_id: 't-1' }, '拉取失败')} />
    )
    expect(screen.getByText('数据拉取失败')).toBeTruthy() // 缺省 errorEmptyText
    expect(screen.queryByText('还没有报告入库')).toBeNull()

    rerender(
      <PagedTable dataSource={[]} columns={COLS} rowKey="id" emptyText="还没有报告入库"
        error={new ApiError(0, {}, '网络异常')} errorEmptyText="台账拉取失败" />
    )
    expect(screen.getByText('台账拉取失败')).toBeTruthy() // 自定义 errorEmptyText
  })

  it('⑤ server 模式受控：page/pageSize/total 驱动渲染，onPageChange(page, pageSize) 上抛', () => {
    const onPageChange = vi.fn()
    const { container } = render(
      <PagedTable mode="server" dataSource={rows(2)} columns={COLS} rowKey="id" emptyText="x"
        page={2} pageSize={15} total={40} onPageChange={onPageChange} />
    )
    // 受控：当页数据原样渲染（2 行），不按内存切片吞掉
    expect(rowCount(container)).toBe(2)
    expect(screen.getByText('共 40 条')).toBeTruthy()

    fireEvent.click(container.querySelector('.ant-pagination-item-3'))
    expect(onPageChange).toHaveBeenCalledTimes(1)
    expect(onPageChange).toHaveBeenCalledWith(3, 15)
  })
})
