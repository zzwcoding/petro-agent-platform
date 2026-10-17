/**
 * cites 共享件钉测（重设计——引用分组 / program 追加面文本切分）。
 *
 * 守什么：
 * - 「引用了 N 篇文档」的 N＝**去重来源数**（同文档多支切片算 1 篇）——真机
 *   EB4-数-明2（51 支引用来自 2 处来源）与 EB3-数-降1（16 支来自 5 处）两形都钉
 *   （素材＝__fixtures__/turns.js 真帧夹具的归约输出——FIXTURE_TURNS 条目＝{id, turn, durationS}）。
 * - trust 四值→白话徽标；未知值原样回显（不外推、不编）。
 * - 追加面文本切分：`[n]` 起头＝新条目；真机 split 的续行（含全角空格表格行）并入上一条；
 *   条目行「来源」抽取处理 `[n] {source}：{正文}` 与 `[n] 《报告》 · f15：{正文}` 两形。
 */
/** @vitest-environment jsdom */
import { describe, expect, it } from 'vitest'

import { citeSourceCount, groupCitations, parseSupplement, trustLabel } from './cites.js'
import { FIXTURE_TURNS } from './__fixtures__/turns.js'

const FULL = FIXTURE_TURNS.find(t => t.id === 't-full').turn
const SPLIT = FIXTURE_TURNS.find(t => t.id === 't-split').turn

describe('cites · 引用去重分组与 trust 白话', () => {
  it('按 source 去重分组：EB4-数-明2 的 51 支引用归 2 组（保首见序、组内保 index 序）', () => {
    const groups = groupCitations(FULL.citations)
    expect(groups.map(g => [g.source, g.items.length])).toEqual([
      ['agg.fct_daily_metering', 50],
      ['agg.fct_daily_metering ⋈ agg.dim_well ⋈ agg.dim_date', 1]
    ])
    expect(groups[0].items[0].index).toBe(1)
    expect(groups[1].items[0].index).toBe(51)
  })

  it('「引用了 N 篇文档」的 N＝去重来源数：明2=2、降1=5（切片数 51/16 不作篇数）', () => {
    expect(citeSourceCount(FULL.citations)).toBe(2)
    expect(citeSourceCount(SPLIT.citations)).toBe(5)
    expect(SPLIT.citations).toHaveLength(16)
  })

  it('trust 四值→白话徽标；未知值原样回显、空值「来源未标注」', () => {
    expect(trustLabel('authoritative')).toBe('权威台账')
    expect(trustLabel('ledger')).toBe('台账')
    expect(trustLabel('report')).toBe('报告')
    expect(trustLabel('notice')).toBe('系统注记')
    expect(trustLabel('weird')).toBe('weird')
    expect(trustLabel('')).toBe('来源未标注')
  })
})

describe('cites · 程序追加面文本切分（禁硬匹配块头，只按行形）', () => {
  it('真机 attribution 形（[n] source：内容）：51 条逐条切出、来源＝首冒号前片段、前导说明进 head', () => {
    const { head, items } = parseSupplement(FULL.supplements.attribution)
    expect(head).toBe('按来源分别列出（每条结论都标出它来自哪个来源）：')
    expect(items).toHaveLength(51)
    expect(items[0]).toEqual({
      index: 1,
      source: 'agg.fct_daily_metering',
      text: '井号=N-01；区块=渤南；日期=2026-01-01；日产液量（方）=36.97'
    })
  })

  it('真机 split 形（[n] 《报告》 · f15：正文）：来源取 ` · ` 前的报告名；续行（表格/分隔行）并入上一条', () => {
    const { head, items } = parseSupplement(SPLIT.supplements.split)
    expect(head).toBe('互不一致——各来源说法如下，按来源分别列出：')
    expect(items.map(i => i.index)).toEqual([9, 13, 10, 14])
    expect(items[0].source).toBe('《A-W11井完井工程报告》')
    expect(items[0].text).toContain('4.2 防砂方式与参数')
    expect(items[0].text).toContain('\n') // 续行（真机表格行）保原文换行
    expect(items[0].text.length).toBeGreaterThan(200)
  })

  it('条目行无 `：` 分隔＝来源空串、正文原样（不伪造来源）', () => {
    const { items } = parseSupplement('[7] 一段没有来源分隔的说明\n[8] 另一条')
    expect(items).toEqual([
      { index: 7, source: '', text: '一段没有来源分隔的说明' },
      { index: 8, source: '', text: '另一条' }
    ])
  })

  it('空文本＝空 head 空 items（空态不造数据）', () => {
    expect(parseSupplement(null)).toEqual({ head: '', items: [] })
    expect(parseSupplement('')).toEqual({ head: '', items: [] })
  })
})
