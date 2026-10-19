/**
 * 重设计共享件（真流页与各展示件共用）——纯函数，无请求、无副作用。
 *
 * 守什么（调研 §3/§4/§6 的机器可验面）：
 * - trust 四值闭世界表（authoritative/ledger/report/notice）——**只作机读判据**（引用块回读
 *   的尾括号剥取，见 `parseCitations`），**白话徽标不上屏**（Owner 2026-10-19 打磨批⑩：
 *   右栏引用清单组头与悬停卡都不再渲染）；`trust=notice` 的引用指向**程序声明**而非
 *   文档，渲染方据该键分形（出「系统生成的声明」文本句，不出徽标）。
 * - 引用**按 source 去重分组**（同一份文档多支切片归一组，组内保原始 index 序）——
 *   「引用了 N 篇文档」的 N 即本函数的分组数（篇=来源，不是切片数）。
 * - 程序追加面文本切分：`strip()` 后按行扫描——`[n]` 起头＝新条目，其余行（真机 split
 *   的整段原文含全角空格表格行）续属上一条。**只按行形切分，禁硬匹配块头文本**
 *   （调研 §1：块头字面已随 EB4b 白话化演进过一次）。
 * - 条目行内「来源」抽取：取首个 `：` 之前的片段，若片段含 ` · `（真机 split 形
 *   `《报告》 · f15：正文`）再取最后一个 ` · ` 之前的来源名——取不到来源＝空串
 *   （渲染方归「来源未标注」，不伪造）。
 * - **引用块回读**（`parseCitations`）：历史读口无 citations 帧面，只有收口时程序落账的
 *   `supplement{block:'citations'}` 文本（真源 `appv2/runtimev2/answering/core.py:209`
 *   `[{seq}] {source} · {source_id}（{trust}）`）。本函数把它投回 citation 帧四键形——
 *   这是**投影读口已有的面**（同源同数据），不是补造；投影后历史轮与真流轮的引用面同形，
 *   正文 `[n]` 悬停卡／右栏引用清单在历史轮上照常可用。
 * - **追问链归属**（followup_of 上溯取根／按根成链）也放本件——左栏 ThreadList 的「一链一行」
 *   分组与真流页 A1V2R 的选中拉链（collectChain）共用同一根语义，单点真源不各写一份。
 */

/** trust 四值闭世界（键集＝引用块回读的尾括号判据；值＝调研 §4 白话名，仅留档不上屏）。 */
export const TRUST_TEXT = {
  authoritative: '权威台账',
  ledger: '台账',
  report: '报告',
  notice: '系统注记'
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

/** 条目正文里抽来源名（首 `：` 前，含 ` · ` 时取最后一段的来源名；无 `：`＝来源空串）。 */
function sourceOf(body) {
  const colon = body.indexOf('：')
  if (colon < 0) return { source: '', rest: body.trim() }
  const prefix = body.slice(0, colon)
  const dot = prefix.lastIndexOf(' · ')
  const name = (dot >= 0 ? prefix.slice(0, dot) : prefix).trim()
  return { source: name, rest: body.slice(colon + 1).trim() }
}

/**
 * 追问链归属：沿 `followup_of` 逐跳上溯取根——根＝`followup_of` 空串／指向**窗口外**
 * （窗口界兜底：窗内最老成员自成一链，如实呈现，不虚构归属；与旧页 608267b buildThreads
 * 的分组语义同源）。`byId`＝窗口 id→行表；`cache`（可选）＝行 id→根 id，调用方跨行复用时传。
 * 带环护栏（seen）：脏数据成环不死循环，停在环上第一节点＝该链根。
 */
export function chainRootId(row, byId, cache = null) {
  if (cache?.has(row.run_id)) return cache.get(row.run_id)
  const seen = new Set()
  let cur = row
  while (cur.followup_of && byId.has(cur.followup_of) && !seen.has(cur.run_id)) {
    seen.add(cur.run_id)
    cur = byId.get(cur.followup_of)
  }
  cache?.set(row.run_id, cur.run_id)
  return cur.run_id
}

/**
 * 行集 → 追问链分组（左栏「一链一行」的数据面）：按**分组键**（followup_of 上溯根）归链；
 * 链内按 `created_at` 升序（轮次顺序），`latest`＝最新轮（升序末位——副行状态/轮数/时间取它），
 * 链序按 `latest.created_at` 降序（与后端行序同向——最新对话在最上）。
 * `rootId`/`title` 取链内**created_at 最早**的成员（旧页 608267b buildThreads 的行标识与行标签
 * 口径——正常数据下即链根问句；夹具里 followup 行早于其父时才与分组键不同名）。
 * 返回 [{ rootId, title（链内最早轮问句）, rounds, latest }]。
 */
export function groupRunsIntoChains(runs) {
  const byId = new Map(runs.map(r => [r.run_id, r]))
  const cache = new Map()
  const groups = new Map()
  for (const r of runs) {
    const root = chainRootId(r, byId, cache)
    if (!groups.has(root)) groups.set(root, [])
    groups.get(root).push(r)
  }
  const chains = [...groups.values()].map(rs => {
    const rounds = [...rs].sort((a, b) => (a.created_at < b.created_at ? -1 : 1))
    return {
      rootId: rounds[0].run_id,
      title: rounds[0].question || '（无问句）',
      rounds,
      latest: rounds[rounds.length - 1]
    }
  })
  chains.sort((a, b) => (a.latest.created_at < b.latest.created_at ? 1 : -1))
  return chains
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

/** trust 闭世界（引用块尾括号只在此集内才当 trust 剥——否则原样留在出处编号里，不误切）。 */
const TRUST_VALUES = new Set(Object.keys(TRUST_TEXT))

/** 尾括号（全角／半角）——`（authoritative）` 形。 */
const TRUST_TAIL_RE = /[（(]([^（）()]*)[）)]\s*$/

/**
 * 引用块文本（`supplement{block:'citations'}`）→ 引用帧数组（与 `citation` 帧同四键形：
 * `{index, source, source_id, trust}`，按 index 升序——服务端 `_cited_seqs` 已去重升序）。
 *
 * 行形＝`[n] <来源> · <出处编号>（<trust>）`（真源 `core.py:209`）：
 * - 段头「引用：」等非 `[n]` 起头的行跳过（块头字面随演进会变，禁硬匹配——只认行形）；
 * - 尾括号值在 trust 闭世界内才剥作 trust，否则整段留在出处编号里（不猜不误切）；
 * - 无 ` · ` 分隔＝整段当来源、出处编号空串（如实空，不编）。
 * 空文本＝空数组（空态不造数据）。
 */
export function parseCitations(text) {
  const out = []
  for (const raw of String(text ?? '').split('\n')) {
    const m = /^\[(\d+)\]\s*(.*)$/.exec(raw.replace(/[ \t]+$/, ''))
    if (!m) continue
    let body = m[2].trim()
    let trust = ''
    const tail = TRUST_TAIL_RE.exec(body)
    if (tail && TRUST_VALUES.has(tail[1].trim())) {
      trust = tail[1].trim()
      body = body.slice(0, tail.index).trim()
    }
    const dot = body.lastIndexOf(' · ')
    out.push({
      index: Number(m[1]),
      source: (dot >= 0 ? body.slice(0, dot) : body).trim(),
      source_id: dot >= 0 ? body.slice(dot + 3).trim() : '',
      trust
    })
  }
  return out
}
