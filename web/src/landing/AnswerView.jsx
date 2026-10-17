/**
 * AnswerView · 答案正文渲染器（EB2-D4 前端答案友好化）。
 *
 * 背景：模型答案本身是 Markdown（真机实录 eval/results/frames/EB1-数-明1.json：
 * 粗体当小标题、`- ` 列表、逐行引标 [n]），旧的 pre-wrap 纯文本把 **粗体**、`- `
 * 原样当记号显示——「乱七八糟」的主因。
 *
 * 实现纪律（D4 逐字）：
 * - 只用 marked 的 **lexer**（`marked.lexer(text)`）出 token，自己映射 React 元素；
 *   不经 marked 的 HTML 输出面（不用 dangerouslySetInnerHTML）——html token 直接忽略，
 *   天然免注入（答案里的 `<script>`/`<div>` 一律不落 DOM）。
 * - token 白名单：paragraph/strong/em/del/list/list_item/table/tablecell/tablerow/
 *   code/heading/space；白名单外一律降级为纯文本（原文照现，不静默吞内容）。
 * - `text` 叶子带嵌套 tokens 时按 marked 自家 TextRenderer 同语义递归（松散清单项/懒续行
 *   会把整段包成 text、内联结构挂 .tokens——真机实测：`- N-27：… [27]**渤西区块…**`
 *   的粗体就挂在 text.tokens 里；不递归则记号原样漏出）。
 * - 文本节点里的引标 `[n]` → 可点击锚点，点击经 props `onCite(index)` 上抛；
 *   **不传 onCite＝不切分**（正文原样单文本节点——历史轮次无引用数据可查，页面走此形）。
 * - 引标悬停预览（重设计新增，**可选 prop**）：传 `citeHoverCard(index)` → 该引标外包
 *   antd `Popover`（受控 hover），内容由调用方给（内容件在 landing/redesign/ 下，**零请求**：
 *   直查内存材料）。不传＝引标行为与旧版逐字一致（V1 与真流页不受影响）；传了而不传
 *   onCite 时引标仍切分（只悬停不点击）。
 *
 * 两处对逐字稿的最小让位（均有真机样本依据，改动一处即可回退）：
 * ① 内联代码 token 名是 `codespan`（marked v18 实测）而非 `code`——D4 写「code 用
 *    <code> 行内样式」，故 codespan→<code>（行内态）、code→<pre><code>（块态）两形均支持；
 * ② 软换行保真：真机答案用**单换行**分行（不是 Markdown 的空行分段），CommonMark 会把
 *    软换行折叠成空格——整段并成一行、清单尾注（口径/批次/截断声明）与末项并流。
 *    故纯文本叶子维持 pre-wrap（原文即所见），块结构仍全由渲染器出（D4「pre-wrap 去掉」
 *    指答案容器不再整块当预格式文本，此点已落）。
 */
import { createContext, useContext, useMemo, useState } from 'react'
import { Popover } from 'antd'
import { marked } from 'marked'

const ROOT = { fontSize: 13, lineHeight: 1.7 }
const PLAIN = { whiteSpace: 'pre-wrap' } // 软换行保真（见头注②）
const P = { margin: '0 0 6px' }
const HEAD_SIZE = { 1: 16, 2: 15, 3: 14, 4: 13, 5: 13, 6: 13 }
const HEAD = { margin: '10px 0 6px', fontWeight: 600 }
const LIST = { margin: '0 0 6px', paddingLeft: 22 }
const ITEM = { marginBottom: 2 }
const MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
const CODE_INLINE = {
  background: 'rgba(127,127,127,0.18)', padding: '1px 4px', borderRadius: 4,
  fontFamily: MONO, fontSize: 12
}
const CODE_BLOCK = { fontFamily: MONO, fontSize: 12, whiteSpace: 'pre-wrap' }
const PRE = {
  background: 'rgba(127,127,127,0.12)', padding: '6px 8px', borderRadius: 4,
  overflowX: 'auto', margin: '0 0 6px'
}
const TABLE = { borderCollapse: 'collapse', margin: '0 0 6px' }
const CELL = { border: '1px solid #e0e4e8', padding: '3px 8px' }
const TH = { ...CELL, background: 'rgba(127,127,127,0.12)', fontWeight: 600, textAlign: 'left' }
const CITE = { color: '#4a9dff', cursor: 'pointer' }

/** 引标正则（闭世界：方括号数字；正文里的 `[标签]` 不误中）。 */
const CITE_RE = /\[(\d+)\]/g

/**
 * 引标悬停上下文（可选注入面）：`citeHoverCard` 在场时，引标外包受控 Popover。
 * 上下文而非逐层传参＝递归渲染器（children/tokenNode/tableNode）零改动，行为默认不变。
 */
const CiteCtx = createContext(null)

/** 单个引标：可点击锚点（onCite 在场）＋可选悬停卡（citeHoverCard 在场）。 */
function CiteAnchor({ index, onCite }) {
  const ctx = useContext(CiteCtx)
  const anchor = (
    <a data-cite={index} style={CITE} onClick={onCite ? () => onCite(index) : undefined}>
      {`[${index}]`}
    </a>
  )
  const content = ctx?.citeHoverCard ? ctx.citeHoverCard(index) : null
  if (!content) return anchor
  return (
    <Popover
      content={content} placement="topLeft" trigger="hover"
      open={ctx.hoverIndex === index}
      onOpenChange={o => ctx.setHoverIndex(o ? index : null)}>
      {anchor}
    </Popover>
  )
}

/**
 * 文本 → React 子节点：`[n]` 切出可点击锚点，其余原样。
 * 无 onCite 且无悬停卡（历史轮次）＝整串原样返回——不切分，正文保持单一文本节点。
 */
function textParts(text, onCite, hasHoverCard) {
  const s = String(text ?? '')
  if (!onCite && !hasHoverCard) return s
  const out = []
  let last = 0
  for (const m of s.matchAll(CITE_RE)) {
    if (m.index > last) out.push(s.slice(last, m.index))
    const idx = Number(m[1])
    out.push(<CiteAnchor key={`cite-${idx}-${m.index}`} index={idx} onCite={onCite} />)
    last = m.index + m[0].length
  }
  if (last < s.length) out.push(s.slice(last))
  return out
}

/** 纯文本叶子（text token／白名单外降级／表格无 tokens 的格子）——统一 pre-wrap 保真。 */
function PlainText({ text, onCite }) {
  const ctx = useContext(CiteCtx)
  return <span style={PLAIN}>{textParts(text, onCite, Boolean(ctx?.citeHoverCard))}</span>
}

/** 子 token 列表 → React 子节点（inline/block 同一递归）。 */
function children(tokens, keyPrefix, onCite) {
  if (!Array.isArray(tokens) || tokens.length === 0) return null
  return tokens.map((tk, i) => tokenNode(tk, `${keyPrefix}.${i}`, onCite))
}

/**
 * 单 token → React 元素（白名单映射；未识别降级纯文本）。
 * key 必传：调用点均在数组里。
 */
function tokenNode(token, key, onCite) {
  if (!token || typeof token !== 'object') return null
  switch (token.type) {
    case 'paragraph':
      return <p key={key} style={P}>{children(token.tokens, key, onCite) ?? <PlainText text={token.text} onCite={onCite} />}</p>
    case 'heading': {
      const depth = Math.min(Math.max(Number(token.depth) || 1, 1), 6)
      const Tag = `h${depth}`
      return <Tag key={key} style={{ ...HEAD, fontSize: HEAD_SIZE[depth] }}>{children(token.tokens, key, onCite)}</Tag>
    }
    case 'strong':
      return <strong key={key}>{children(token.tokens, key, onCite)}</strong>
    case 'em':
      return <em key={key}>{children(token.tokens, key, onCite)}</em>
    case 'del':
      return <del key={key}>{children(token.tokens, key, onCite)}</del>
    case 'text':
      // 纯文本叶子。**但有嵌套必须递归**：marked 把「松散清单项／懒续行的整段」包成 text
      // 且内联结构挂在 .tokens（真机 EB1-数-明1 实测：`- N-27：… [27]**渤西区块…**` 的粗体
      // 就挂在 text.tokens 里）——不递归则 `**` 记号原样漏出（正是 D4 要修的那类原形）。
      // marked 自身 TextRenderer 同语义（有 tokens 走 parseInline，无则出 text）。
      return Array.isArray(token.tokens) && token.tokens.length > 0
        ? <span key={key} style={PLAIN}>{children(token.tokens, key, onCite)}</span>
        : <PlainText key={key} text={token.text} onCite={onCite} />
    case 'code': // 块态：``` 围栏
      return (
        <pre key={key} style={PRE}>
          <code style={CODE_BLOCK}>{token.text ?? ''}</code>
        </pre>
      )
    case 'codespan': // 行内态：`code`（见头注①）
      return <code key={key} style={CODE_INLINE}>{token.text ?? ''}</code>
    case 'list': {
      const Tag = token.ordered ? 'ol' : 'ul'
      const props = token.ordered && Number(token.start) ? { start: Number(token.start) } : {}
      return <Tag key={key} style={LIST} {...props}>{children(token.items, key, onCite)}</Tag>
    }
    case 'list_item':
      return <li key={key} style={ITEM}>{children(token.tokens, key, onCite) ?? <PlainText text={token.text} onCite={onCite} />}</li>
    case 'table':
      return tableNode(token, key, onCite)
    case 'tablecell': // v18 实测表格格子无 type（见 tableNode），此形兼容旧 token 面
      return <td key={key} style={CELL}>{cellNodes(token, key, onCite)}</td>
    case 'tablerow':
      return <tr key={key}>{children(token.cells ?? token.tokens, key, onCite)}</tr>
    case 'space': // 块间空行——间隔由块元素 margin 出，不落节点
      return null
    case 'html': // 白名单外且危险面：一律忽略（答案里的 HTML 记号不落 DOM）
      return null
    default:
      // 未识别 token（link/blockquote/hr/br 等）→ 纯文本降级：原文照现（raw 含记号，
      // 不丢 URL/marker）；无 raw 用 text。
      return <PlainText key={key} text={token.raw ?? token.text ?? ''} onCite={onCite} />
  }
}

/** 表格格子子节点：v18 实测格子＝{text,tokens,header,align}（无 type 字段）。 */
function cellNodes(cell, keyPrefix, onCite) {
  if (Array.isArray(cell?.tokens) && cell.tokens.length > 0) return children(cell.tokens, keyPrefix, onCite)
  return <PlainText text={cell?.text ?? cell?.raw ?? ''} onCite={onCite} />
}

/** 表格：header（有表头行）＋ rows 两段结构（marked v18 token 形）。 */
function tableNode(token, key, onCite) {
  const head = Array.isArray(token.header) ? token.header : []
  const rows = Array.isArray(token.rows) ? token.rows : []
  return (
    <table key={key} style={TABLE}>
      {head.length > 0 && (
        <thead>
          <tr>
            {head.map((c, i) => <th key={i} style={TH}>{cellNodes(c, `${key}.h${i}`, onCite)}</th>)}
          </tr>
        </thead>
      )}
      <tbody>
        {rows.map((row, ri) => (
          <tr key={ri}>
            {(row || []).map((c, ci) => <td key={ci} style={CELL}>{cellNodes(c, `${key}.r${ri}c${ci}`, onCite)}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/**
 * 答案正文（A1V2 中栏答案面用）。
 * @param content       答案文本（text 帧拼贴的 answerText；空串＝不渲染块）
 * @param onCite        引标点击回调 (index) => void；缺省＝引标不切分（历史轮次无引用数据）
 * @param citeHoverCard 引标悬停卡内容回调 (index) => ReactNode|null；缺省＝无悬停卡
 *                      （返回空＝该引标不弹——无对应材料时不弹，不空弹）
 */
export default function AnswerView({ content, onCite, citeHoverCard }) {
  const tokens = useMemo(() => marked.lexer(String(content ?? '')), [content])
  const [hoverIndex, setHoverIndex] = useState(null)
  const ctx = useMemo(
    () => (citeHoverCard ? { citeHoverCard, hoverIndex, setHoverIndex } : null),
    [citeHoverCard, hoverIndex]
  )
  return (
    <CiteCtx.Provider value={ctx}>
      <div style={ROOT} data-testid="answer-view">
        {tokens.map((tk, i) => tokenNode(tk, `tk${i}`, onCite))}
      </div>
    </CiteCtx.Provider>
  )
}
