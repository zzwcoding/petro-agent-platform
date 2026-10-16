/**
 * AnswerView 钉测（EB2-D4 前端答案友好化——答案正文渲染器）。
 *
 * 守什么（A1V2 中栏答案面——机器可验）：
 * - Markdown 记号成元素：**粗体**→<strong>、`- ` 列表→<ul>/<li>、### 标题→<h3>、
 *   围栏码→<pre><code>、行内码→<code>、表格→<table>/<th>/<td>；
 * - 引标 [n]→可点击锚点，点击上抛 onCite(index)；不传 onCite＝不切分（正文单文本节点——
 *   历史轮次无引用数据可查，A1V2.jsx renderRound 走此形）；
 * - html token 不落 DOM（`<script>`/`<div>`/`<img>` 一律忽略——天然免注入，无
 *   dangerouslySetInnerHTML）；
 * - 白名单外 token（blockquote/hr）降级纯文本原文照现（不静默吞内容）；
 * - 软换行保真：真机答案用单换行分行（非 Markdown 空行分段），纯文本叶子 pre-wrap
 *   保换行——清单尾注（口径/批次/截断声明）不并流跑成一行。
 *
 * 素材（逐字转录，零编造）：eval/results/frames/EB1-数-明1.json 的 text 帧拼贴答案——
 * 粗体当小标题＋`- ` 逐井清单＋逐行引标 [n] ＋尾注三行（口径/批次/截断）。
 */

/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render } from '@testing-library/react'
import AnswerView from './AnswerView.jsx'

afterEach(() => {
  cleanup() // 跨测不串现场（同 landing/A1V2.test.jsx 惯例）
})

/** 真机答案逐字片段（EB1-数-明1.json）：粗体小标题＋两行清单＋引标。 */
const BOLD_LIST_EXCERPT = '**渤南区块（2025-09-01，单位：吨）**\n- N-01：21.16 [1]\n- N-02：30.79 [2]\n'

/** 真机答案尾注逐字片段（同文件）：单换行分行、行行带引标。 */
const TAIL_EXCERPT = '口径：日产油量（A 班次合计日口径）[51]\n数据截至批次 b-a1a61db9f458，水位 2026-08-31（批次落后 46 天，处于超期）[51]\n'

describe('Markdown 记号成元素（D4 白名单映射）', () => {
  it('真机片段：粗体→<strong>、`- ` 清单→<ul>＋<li>×2，且记号本身不再出现', () => {
    const { container } = render(<AnswerView content={BOLD_LIST_EXCERPT} />)
    const strong = container.querySelector('strong')
    expect(strong).toBeTruthy()
    expect(strong.textContent).toBe('渤南区块（2025-09-01，单位：吨）')
    const ul = container.querySelector('ul')
    expect(ul).toBeTruthy()
    const items = container.querySelectorAll('li')
    expect(items).toHaveLength(2)
    expect(items[0].textContent).toBe('N-01：21.16 [1]')
    expect(items[1].textContent).toBe('N-02：30.79 [2]')
    // 记号标记不再原样显示（`**`/`- ` 不当文本出）
    expect(container.textContent).not.toContain('**')
    expect(container.textContent).not.toContain('- N-01')
  })

  it('清单项内的粗体：text 叶子带嵌套 tokens 时递归（真机 `- N-27：… [27]**渤西区块…**` 形——不递归则 ** 原样漏出）', () => {
    // 逐字片段（EB1-数-明1.json 清单第 27 项与紧邻下一项）：marked 把该清单项整段包成
    // text 且粗体挂在其 .tokens 里——渲染器须递归，否则记号漏出。
    const { container } = render(<AnswerView content={'- N-27：21.57 [27]**渤西区块（2025-09-01，单位：吨）**\n- X-01：28.21 [28]\n'} />)
    const items = container.querySelectorAll('li')
    expect(items).toHaveLength(2)
    expect(items[0].textContent).toBe('N-27：21.57 [27]渤西区块（2025-09-01，单位：吨）')
    expect(items[0].querySelector('strong')?.textContent).toBe('渤西区块（2025-09-01，单位：吨）')
    expect(container.textContent).not.toContain('**')
  })

  it('标题/块码/行内码/表格各出对应元素', () => {
    const { container } = render(<AnswerView content={'### 小标题\n\n```\ncode block\n```\n\n行内 `code` 记号\n\n| 井号 | 产量 |\n| --- | --- |\n| A1 | 100 |\n'} />)
    expect(container.querySelector('h3')?.textContent).toBe('小标题')
    expect(container.querySelector('pre code')?.textContent).toBe('code block')
    const inline = [...container.querySelectorAll('code')].find(c => c.textContent === 'code')
    expect(inline).toBeTruthy() // 行内态（codespan）——不是块码
    expect(container.querySelectorAll('table th')).toHaveLength(2)
    expect([...container.querySelectorAll('table th')].map(c => c.textContent)).toEqual(['井号', '产量'])
    expect([...container.querySelectorAll('table td')].map(c => c.textContent)).toEqual(['A1', '100'])
  })

  it('白名单外 token（引用段/分隔线）降级纯文本原文照现——不静默吞内容', () => {
    const { container } = render(<AnswerView content={'> 引用段\n\n---\n'} />)
    expect(container.textContent).toContain('> 引用段')
    expect(container.textContent).toContain('---')
  })

  it('软换行保真：真机尾注两行仍分两行（pre-wrap——不并流跑成一行）', () => {
    const { container } = render(<AnswerView content={TAIL_EXCERPT} />)
    expect(container.textContent).toContain('（A 班次合计日口径）[51]\n数据截至批次')
  })
})

describe('引标 [n] → 可点击锚点（引用抽屉联动入口）', () => {
  it('[3] 渲染为锚点且点击上抛 onCite(3)', () => {
    const onCite = vi.fn()
    const { container } = render(<AnswerView content={'有效产量 21.16 吨[3]。'} onCite={onCite} />)
    const a = container.querySelector('a[data-cite="3"]')
    expect(a).toBeTruthy()
    expect(a.textContent).toBe('[3]')
    fireEvent.click(a)
    expect(onCite).toHaveBeenCalledTimes(1)
    expect(onCite).toHaveBeenCalledWith(3)
  })

  it('多引标各成锚点、按正文序排列（[1][2] 与 [51] 并存）', () => {
    const onCite = vi.fn()
    const { container } = render(<AnswerView content={BOLD_LIST_EXCERPT + TAIL_EXCERPT} onCite={onCite} />)
    const cites = [...container.querySelectorAll('a[data-cite]')].map(a => a.getAttribute('data-cite'))
    expect(cites).toEqual(['1', '2', '51', '51'])
    fireEvent.click([...container.querySelectorAll('a[data-cite]')][2])
    expect(onCite).toHaveBeenCalledWith(51)
  })

  it('不传 onCite＝不切分：正文单文本节点、无锚点（历史轮次形）', () => {
    const { container } = render(<AnswerView content={'N-01 井 2025-09-01 日产油量 21.16 吨[1]。'} />)
    expect(container.querySelectorAll('a')).toHaveLength(0)
    expect(container.textContent).toBe('N-01 井 2025-09-01 日产油量 21.16 吨[1]。')
  })

  it('空正文不渲染答案块内容（不抛错——answerText 空串时不白屏）', () => {
    const { container } = render(<AnswerView content="" />)
    expect(container.textContent).toBe('')
  })
})

describe('html token 不落 DOM（免注入——不用 dangerouslySetInnerHTML）', () => {
  it('块级 <script>/<div> 与行内 <img onerror> 一律忽略，正常文本照渲染', () => {
    const { container } = render(<AnswerView content={'正常文本\n\n<script>alert(1)</script>\n\n<div onclick="boom()">块 html</div>\n\n行内 <img src=x onerror=alert(2)> 记号\n'} />)
    expect(container.textContent).toContain('正常文本')
    expect(container.textContent).toContain('记号')
    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('div[onclick]')).toBeNull()
    expect(container.querySelectorAll('div')).toHaveLength(1) // 只有渲染器根 div
    expect(container.innerHTML).not.toContain('<script')
    expect(container.textContent).not.toContain('alert(1)')
    expect(container.textContent).not.toContain('alert(2)')
    expect(container.textContent).not.toContain('块 html') // html token 整段忽略（不吃内容）
  })

  it('引标在 html 记号旁仍照常成锚点（忽略 html 不影响正文切分）', () => {
    const onCite = vi.fn()
    const { container } = render(<AnswerView content={'结论 21.16 吨[1]\n\n<span>装饰</span>\n'} onCite={onCite} />)
    fireEvent.click(container.querySelector('a[data-cite="1"]'))
    expect(onCite).toHaveBeenCalledWith(1)
  })
})

describe('渲染冒烟（清理）', () => {
  it('多次挂载不残留（cleanup 后文档无答案块）', () => {
    render(<AnswerView content="冒烟文本" />)
    cleanup()
    expect(document.querySelector('[data-testid="answer-view"]')).toBeNull()
  })
})
