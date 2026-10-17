/**
 * LineageCard 钉测（血缘／查询口径卡——设计稿 §3.4）。
 *
 * 守什么：
 * - 默认收起（不抢正文）；展开＝五要素分行渲染（① 口径／② 来源表／③ 过滤条件／
 *   ④ 数据截至批次／⑤ 收口注记），含「└（权限注入）」子行；
 * - 「数据截至批次」要素**高亮**（用户最关心更新到哪天）；
 * - `payload.limit.hit` ＝补一行「只取了前 N 条」（截断如实披露）；
 * - 数据源优先级：结构化 `lineage` 对象优先，纯文本 `supplement(lineage)` 兜底；
 * - 空态（无血缘）＝整卡不渲染（非数据题不出）。
 *
 * 素材：EB4-数-明2 的 `observation.payload.lineage` 与 `supplement{block:'lineage'}.text`。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'

import LineageCard from './LineageCard.jsx'
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

describe('LineageCard · 结构化 lineage（首选源）', () => {
  it('默认收起→展开出五要素（口径/来源表/过滤条件/数据截至批次/收口注记）', () => {
    render(<LineageCard lineage={FULL_PAYLOAD.lineage} limit={FULL_PAYLOAD.limit} />)
    expect(screen.queryByTestId('lineage-body')).toBeNull() // 默认收起
    fireEvent.click(screen.getByTestId('lineage-toggle'))
    const body = screen.getByTestId('lineage-body')
    for (const key of ['① 口径', '② 来源表', '③ 过滤条件', '④ 数据截至批次', '⑤ 收口注记']) {
      expect(body.textContent).toContain(key)
    }
    expect(body.textContent).toContain('└（权限注入）') // 过滤条件子行
  })

  it('「数据截至批次」要素高亮（结构位＋「更新到哪天」标）', () => {
    render(<LineageCard lineage={FULL_PAYLOAD.lineage} limit={FULL_PAYLOAD.limit} defaultOpen />)
    const row = screen.getByTestId('lineage-batch-row')
    expect(row.textContent).toContain('批次 b-a1a61db9f458')
    expect(row.textContent).toContain('更新到哪天')
    expect(row.style.borderLeft).toContain('3px') // 高亮边
  })

  it('payload.limit.hit ＝补一行截断披露（只取了前 50 条）', () => {
    render(<LineageCard lineage={FULL_PAYLOAD.lineage} limit={FULL_PAYLOAD.limit} defaultOpen />)
    expect(screen.getByTestId('lineage-body').textContent).toContain('只取了前 50 条')
  })

  it('limit 未命中＝不出截断行（不伪造截断）', () => {
    render(<LineageCard lineage={FULL_PAYLOAD.lineage} limit={{ hit: false, rows: 50 }} defaultOpen />)
    expect(screen.getByTestId('lineage-body').textContent).not.toContain('只取了前')
  })
})

describe('LineageCard · 纯文本兜底与空态', () => {
  it('无结构化 lineage＝按 supplement 文本兜底切五要素（含子行）', () => {
    render(<LineageCard lineage={null} text={FULL.supplements.lineage} defaultOpen />)
    const body = screen.getByTestId('lineage-body')
    expect(body.textContent).toContain('① 口径')
    expect(body.textContent).toContain('⑤ 收口注记')
    expect(body.textContent).toContain('└（权限注入）')
    expect(screen.getByTestId('lineage-batch-row')).toBeTruthy()
  })

  it('两者都没有（非数据题）＝整卡不渲染', () => {
    const { container } = render(<LineageCard lineage={null} text={null} />)
    expect(container.firstChild).toBeNull()
  })
})
