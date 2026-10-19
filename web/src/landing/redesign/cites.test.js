/**
 * cites 共享件钉测（重设计——引用分组 / program 追加面文本切分）。
 *
 * 守什么：
 * - 「引用了 N 篇文档」的 N＝**去重来源数**（同文档多支切片算 1 篇）——真机
 *   EB4-数-明2（51 支引用来自 2 处来源）与 EB3-数-降1（16 支来自 5 处）两形都钉
 *   （素材＝__fixtures__/turns.js 真帧夹具的归约输出——FIXTURE_TURNS 条目＝{id, turn, durationS}）。
 * - trust 四值闭世界表（键集＝机读判据；白话值仅留档，徽标已不上屏——Owner 2026-10-19 打磨批⑩）。
 * - 追加面文本切分：`[n]` 起头＝新条目；真机 split 的续行（含全角空格表格行）并入上一条；
 *   条目行「来源」抽取处理 `[n] {source}：{正文}` 与 `[n] 《报告》 · f15：{正文}` 两形。
 * - 引用块回读（parseCitations）：历史读口无 citation 帧，只余收口增补面文本——按行形投回
 *   `{index, source, source_id, trust}` 四键（真源 core.py:209 `[{seq}] {source} · {source_id}（{trust}）`）；
 *   段头「引用：」跳过；尾括号值不在 trust 闭世界内＝不剥（留在出处编号里，不误切）；无 ` · `＝编号空串。
 * - 追问链归属：followup_of 逐跳上溯取根（空串/窗口外＝到顶）、成环不死循环、分组口径
 *   （链内升序＋latest＝最新轮、链序按最新轮降序）——左栏一链一行与页面拉链的同一真源。
 */
/** @vitest-environment jsdom */
import { describe, expect, it } from 'vitest'

import { chainRootId, citeSourceCount, groupCitations, groupRunsIntoChains, parseCitations, parseSupplement, TRUST_TEXT } from './cites.js'
import { FIXTURE_RUNS } from './__fixtures__/runs.js'
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

  it('trust 四值闭世界表＝机读判据（键集）＋白话留档（值不上屏——Owner 2026-10-19 打磨批⑩）', () => {
    expect(Object.keys(TRUST_TEXT)).toEqual(['authoritative', 'ledger', 'report', 'notice'])
    expect(TRUST_TEXT.authoritative).toBe('权威台账') // 白话值仅留档：徽标已不上屏（组件面零消费）
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

describe('cites · 引用块回读（历史读口增补面 → citation 帧四键形）', () => {
  it('真机 citations 形（[n] 来源 · 出处编号（trust））：段头「引用：」跳过、逐行投四键、index 转数', () => {
    const text = '引用：\n'
      + '[1] agg.fct_daily_metering · N-01@2026-08-01（authoritative）\n'
      + '[2] table_schema 白名单读面 · 表 agg.fct_daily_metering（日产计量事实表·PK well_id+prod_date）（report）\n'
      + '[5] sem_metric#201 · 201（ledger）'
    expect(parseCitations(text)).toEqual([
      { index: 1, source: 'agg.fct_daily_metering', source_id: 'N-01@2026-08-01', trust: 'authoritative' },
      {
        index: 2,
        source: 'table_schema 白名单读面',
        source_id: '表 agg.fct_daily_metering（日产计量事实表·PK well_id+prod_date）',
        trust: 'report'
      },
      { index: 5, source: 'sem_metric#201', source_id: '201', trust: 'ledger' }
    ])
  })

  it('notice 形（程序声明）：来源含全角括号、出处编号 window_note——trust=notice 照剥', () => {
    expect(parseCitations('[17] 检索供给窗声明（截断显式） · window_note（notice）')).toEqual([
      { index: 17, source: '检索供给窗声明（截断显式）', source_id: 'window_note', trust: 'notice' }
    ])
  })

  it('尾括号值不在 trust 闭世界内＝不剥（留在出处编号里，不误切）；无 ` · `＝编号空串', () => {
    expect(parseCitations('[3] 《N-02 完井报告》 · f3（2 完井段）')).toEqual([
      { index: 3, source: '《N-02 完井报告》', source_id: 'f3（2 完井段）', trust: '' }
    ])
    expect(parseCitations('[4] 一段没有分隔的出处')).toEqual([
      { index: 4, source: '一段没有分隔的出处', source_id: '', trust: '' }
    ])
  })

  it('非 `[n]` 起头的行（段头/续行）不进条目；空文本＝空数组（空态不造数据）', () => {
    expect(parseCitations('引用：\n说明行\n[1] A · 1（report）')).toEqual([
      { index: 1, source: 'A', source_id: '1', trust: 'report' }
    ])
    expect(parseCitations(null)).toEqual([])
    expect(parseCitations('')).toEqual([])
  })
})

describe('cites · 追问链归属（左栏一链一行／页面拉链的同一真源）', () => {
  const row = (run_id, followup_of, created_at, question = run_id) =>
    ({ run_id, followup_of, created_at, question, status: 'completed', updated_at: created_at })

  it('followup_of 逐跳上溯取根：空串／指向窗口外＝到顶（窗内最老成员自成一链）', () => {
    const rows = [row('b', 'a', '2026-10-17 10:10'), row('a', '', '2026-10-17 10:00'),
      row('d', 'c-outside', '2026-10-17 09:10'), row('e', 'd', '2026-10-17 09:00')]
    const byId = new Map(rows.map(r => [r.run_id, r]))
    expect(chainRootId(byId.get('b'), byId)).toBe('a')       // 随 followup_of 到顶
    expect(chainRootId(byId.get('a'), byId)).toBe('a')
    expect(chainRootId(byId.get('e'), byId)).toBe('d')       // 父在窗口外＝窗内最老成员 d 成链根
  })

  it('成环脏数据不死循环（环上各自停在自身节点——分组退化不虚构、不挂死）', () => {
    const rows = [row('x', 'y', '2026-10-17 10:00'), row('y', 'x', '2026-10-17 09:00')]
    const byId = new Map(rows.map(r => [r.run_id, r]))
    expect(chainRootId(byId.get('x'), byId)).toBe('x')
    expect(chainRootId(byId.get('y'), byId)).toBe('y')
  })

  it('分组：同根归一条链（created_at 升序、latest＝最新轮）、标题＝链内最早轮问句、链序按最新轮降序', () => {
    const chains = groupRunsIntoChains([FIXTURE_RUNS[0], FIXTURE_RUNS[1], FIXTURE_RUNS[2], FIXTURE_RUNS[3]])
    expect(chains.map(c => [c.rootId, c.rounds.length, c.latest.run_id]))
      .toEqual([['run-9e3779b1', 1, 'run-9e3779b1'], ['run-daa66d14', 2, 'run-3c6ef363'], ['run-78dde6c6', 1, 'run-78dde6c6']])
    expect(chains[0].title).toBe('W-11 井生产套管的尺寸与下深是多少？') // 链接回传原始行不裁剪（截断是渲染面）
    expect(chains[1].title).toBe('去年各井含水率是多少？')
  })

  it('空输入＝空链列（不造数据）', () => {
    expect(groupRunsIntoChains([])).toEqual([])
  })
})
