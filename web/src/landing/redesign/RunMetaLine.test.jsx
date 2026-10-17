/**
 * RunMetaLine 钉测（轮次卡底部小字行——设计稿 §3.7）。
 *
 * 守什么：
 * - 核验徽标＝有据/改写/分列三计数（verdict(verify) 帧）；
 * - 档案小字＝blackbox counts（步数/材料数）＋档案 KB；
 * - **本地计时**（后端无耗时字段——如实标注「本地计时」，不冒充权威耗时）；
 * - **不显示 run 号**（Owner 反馈：系统内部号不对用户展示——runId 传了也不出现）；
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
  it('核验计数＋档案小字＋本地计时（EB4-数-明2 真机值）；run 号不出现在行内', () => {
    render(<RunMetaLine runId={FULL.runId} verdict={FULL.verdicts[0]} blackbox={FULL.blackbox}
      durationS={FIXTURE_TURNS.find(e => e.id === 't-full').durationS} />)
    const line = screen.getByTestId('run-meta-line').textContent
    expect(line).toContain('已核验：有据 51 条 · 改写 0 条 · 分列 0 条')
    expect(line).toContain('12 步 · 51 材料 · 58 KB') // 58959 B → 58 KB
    expect(line).toContain('本地计时 18.5s')
    expect(line).not.toContain(FULL.runId) // run-21e45912 不外露
    expect(line).not.toContain('run-')
  })

  it('改写/分列非零时照样出（EB3-数-降1：有据 4 · 改写 2 · 分列 0）', () => {
    const SPLIT = FIXTURE_TURNS.find(e => e.id === 't-split')
    render(<RunMetaLine runId={SPLIT.turn.runId} verdict={SPLIT.turn.verdicts[0]} blackbox={SPLIT.turn.blackbox}
      durationS={SPLIT.durationS} />)
    expect(screen.getByTestId('runmeta-verify').textContent)
      .toBe('已核验：有据 4 条 · 改写 2 条 · 分列 0 条')
  })

  it('缺 blackbox/verdict ＝相应段不出（不补零、不猜）；run 号段已删', () => {
    render(<RunMetaLine runId={LEGACY.runId} durationS={12} />)
    const line = screen.getByTestId('run-meta-line').textContent
    expect(line).toBe('本地计时 12s') // 只剩时长段——run 号段整段退场
    expect(line).not.toContain(LEGACY.runId)
    expect(line).not.toContain('已核验')
    expect(line).not.toContain('材料')
  })

  it('全空（无核验无档案无时长）＝整行不渲染', () => {
    const { container } = render(<RunMetaLine />)
    expect(container.firstChild).toBeNull()
  })
})
