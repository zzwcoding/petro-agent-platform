/**
 * 重设计共享件（mock 静态页与后续接归约器共用）——纯函数，无请求、无副作用。
 *
 * 守什么（调研 §3/§4/§6 的机器可验面）：
 * - trust 四值 → 白话徽标（authoritative→权威台账 / ledger→台账 / report→报告 /
 *   notice→系统注记）；`trust=notice` 的引用指向**程序声明**而非文档，渲染方据此分形。
 * - 引用**按 source 去重分组**（同一份文档多支切片归一组，组内保原始 index 序）——
 *   「引用了 N 篇文档」的 N 即本函数的分组数（篇=来源，不是切片数）。
 * - 程序追加面文本切分：`strip()` 后按行扫描——`[n]` 起头＝新条目，其余行（真机 split
 *   的整段原文含全角空格表格行）续属上一条。**只按行形切分，禁硬匹配块头文本**
 *   （调研 §1：块头字面已随 EB4b 白话化演进过一次）。
 * - 条目行内「来源」抽取：取首个 `：` 之前的片段，若片段含 ` · `（真机 split 形
 *   `《报告》 · f15：正文`）再取最后一个 ` · ` 之前的来源名——取不到来源＝空串
 *   （渲染方归「来源未标注」，不伪造）。
 */

/** trust 四值 → 白话徽标（调研 §4：前端不再原样显示英文 trust）。 */
export const TRUST_TEXT = {
  authoritative: '权威台账',
  ledger: '台账',
  report: '报告',
  notice: '系统注记'
}

/** trust → 白话徽标文本（未知值＝原样回显，不外推）。 */
export function trustLabel(trust) {
  return TRUST_TEXT[trust] ?? (trust || '来源未标注')
}

/** 引用按 source 去重分组（保首见序；组内条目保原始 index 序）。 */
export function groupCitations(citations) {
  const groups = []
  const at = new Map()
  for (const c of citations || []) {
    const key = c?.source ?? ''
    if (!at.has(key)) {
      at.set(key, groups.length)
      groups.push({ source: key, trust: c?.trust ?? '', items: [] })
    }
    groups[at.get(key)].items.push(c)
  }
  return groups
}

/** 「引用了 N 篇文档」的 N＝去重来源数。 */
export function citeSourceCount(citations) {
  return groupCitations(citations).length
}

/** 条目正文里抽来源名（首 `：` 前，含 ` · ` 时取最后一段的来源名）。 */
function sourceOf(body) {
  const colon = body.indexOf('：')
  const prefix = colon >= 0 ? body.slice(0, colon) : body
  const dot = prefix.lastIndexOf(' · ')
  const name = (dot >= 0 ? prefix.slice(0, dot) : prefix).trim()
  return { source: name, rest: colon >= 0 ? body.slice(colon + 1).trim() : body.trim() }
}

/**
 * 程序追加面文本（attribution/split）→ { head, items }。
 * head＝前导说明行（真机 split 的「互不一致——各来源说法如下…」）；items＝逐条
 * {index, source, text}（text 已去来源前缀）。
 */
export function parseSupplement(text) {
  const head = []
  const items = []
  for (const raw of String(text ?? '').split('\n')) {
    const line = raw.replace(/[ \t]+$/, '')
    const m = /^\[(\d+)\]\s*(.*)$/.exec(line)
    if (m) {
      const { source, rest } = sourceOf(m[2])
      items.push({ index: Number(m[1]), source, text: rest })
      continue
    }
    if (items.length === 0) {
      if (line.trim()) head.push(line.trim())
      continue
    }
    // 续行（真机 split 的表格行/分隔行）——并入上一条，保原文换行。
    items[items.length - 1].text += '\n' + line
  }
  return { head: head.join('\n'), items }
}
