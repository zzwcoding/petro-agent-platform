/**
 * RunMetaLine 钉测（轮次卡底部小字行——设计稿 §3.7）。
 *
 * 守什么：
 * - 核验徽标＝有据/改写/分列三计数（verdict(verify) 帧）；
 * - 档案小字＝blackbox counts（步数/材料数）＋档案 KB；
 * - run 号＋**本地计时**（后端无耗时字段——如实标注「本地计时」，不冒充权威耗时）；
 * - 缺项即不出：挂起腿无 blackbox／无 verdict ＝相应段不渲染（不补零、不猜）；
 * - 全空＝整行不渲染。
 */
/** @vitest-environment jsdom */
import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'

import RunMetaLine from './RunMetaLine.jsx'
import { FIXTURE_TURNS } from './__fixtures__/turns.js'

afterEach(() => cleanup())

const FULL = FIXTURE_TURNS.find(e => e.id === 't-full').turn
const LEGACY = FIXTURE_TURNS.find(e => e.id === 't-legacy').turn

describe('RunMetaLine · 三段小字', () => {
  it('核验计数＋档案小字＋run 号＋本地计时（EB4-数-明2 真机值）', () => {
    render(<RunMetaLine runId={FULL.runId} verdict={FULL.verdicts[0]} blackbox={FULL.blackbox}
      durationS={FIXTURE_TURNS.find(e => e.id === 't-full').durationS} />)
    const line = screen.getByTestId('run-meta-line').textContent
    expect(line).toContain('已核验：有据 51 条 · 改写 0 条 · 分列 0 条')
    expect(line).toContain('12 步 · 51 材料 · 58 KB') // 58959 B → 58 KB
    expect(line).toContain('run-21e45912')
    expect(line).toContain('本地计时 18.5s')
  })

  it('改写/分列非零时照样出（EB3-数-降1：有据 4 · 改写 2 · 分列 0）', () => {
    const SPLIT = FIXTURE_TURNS.find(e => e.id === 't-split')
    render(<RunMetaLine runId={SPLIT.turn.runId} verdict={SPLIT.turn.verdicts[0]} blackbox={SPLIT.turn.blackbox}
      durationS={SPLIT.durationS} />)
    expect(screen.getByTestId('runmeta-verify').textContent)
      .toBe('已核验：有据 4 条 · 改写 2 条 · 分列 0 条')
  })

  it('缺 blackbox/verdict ＝相应段不出（不补零、不猜；旧版轮只剩 run 号）', () => {
    render(<RunMetaLine runId={LEGACY.runId} />)
    const line = screen.getByTestId('run-meta-line').textContent
    expect(line).toBe('run-307959ec')
    expect(line).not.toContain('已核验')
    expect(line).not.toContain('材料')
    expect(line).not.toContain('本地计时')
  })

  it('全空（无 run 号无核验无档案）＝整行不渲染', () => {
    const { container } = render(<RunMetaLine />)
    expect(container.firstChild).toBeNull()
  })
})
