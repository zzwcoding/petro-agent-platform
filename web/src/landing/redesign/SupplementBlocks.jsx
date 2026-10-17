/**
 * SupplementBlocks · 程序追加面（设计稿 §3.5）——次要位，不抢正文。
 *
 * 两块（`supplement` 帧按 `block` 值分派，**禁硬匹配块头文本**——调研 §1/§6）：
 * - **attribution**（按来源列出）：逐条 `[n] {source}：{内容}` → 按来源分组列示（来源＋条数）。
 * - **split**（各来源说法不一）：多来源不一致分列——**单条真机可至 700+ 字（含全角空格
 *   表格行）**，故单条限高（≈6 行），超出出「展开看全文」；展开只影响该条，不撑破正文。
 *
 * 两个折叠块默认收起（次要位纪律）；条目标题只给 `[n]`＋来源，正文原样（程序面不洗白）。
 * 空态：两块都没有＝整件不渲染。
 *
 * 说明：`citations` 块与右栏引用面板同源（同一批 citation 帧），本件**不重复占位**——
 * 仅历史轮/无面板场景才需兜底渲染（未列进本次 mock 版面，见设计稿 §3.5）。
 */
import { useState } from 'react'
import { Button, Collapse, Tag } from 'antd'
import { DownOutlined, UpOutlined } from '@ant-design/icons'
import { dim } from '../../components/helpIcon.jsx'
import { parseSupplement } from './cites.js'

const CLAMP_LINES = 6
/** 限高判定：真行数超限，或单行折行后估计超限（≈6 行 × 40 字/行；jsdom 无排版量测）。 */
const CLAMP_CHARS = 240

/** 单条内容（限高 + 展开看全文）。 */
function ClampedText({ text, testId }) {
  const [open, setOpen] = useState(false)
  const long = String(text ?? '').split('\n').length > CLAMP_LINES || String(text ?? '').length > CLAMP_CHARS
  const clamped = long && !open
  return (
    <div>
      <div data-testid={testId} data-clamped={clamped ? 'true' : 'false'}
        style={{
          fontSize: 12, lineHeight: 1.7, whiteSpace: 'pre-wrap',
          ...(clamped
            ? { display: '-webkit-box', WebkitLineClamp: CLAMP_LINES, WebkitBoxOrient: 'vertical', overflow: 'hidden' }
            : {})
        }}>
        {text}
      </div>
      {long && (
        <Button size="small" type="link" style={{ padding: 0, height: 18 }} onClick={() => setOpen(o => !o)}>
          {open ? <>收起 <UpOutlined style={{ fontSize: 10 }} /></> : <>展开看全文 <DownOutlined style={{ fontSize: 10 }} /></>}
        </Button>
      )}
    </div>
  )
}

/** 按来源分组（保首见序）。 */
function bySource(items) {
  const groups = []
  for (const it of items) {
    let g = groups.find(x => x.source === it.source)
    if (!g) { g = { source: it.source, items: [] }; groups.push(g) }
    g.items.push(it)
  }
  return groups
}

function ItemLine({ it }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ fontSize: 12 }}>
        <Tag style={{ fontSize: 10 }}>{`[${it.index}]`}</Tag>
        {it.source && <span>{it.source}</span>}
      </div>
      <ClampedText text={it.text} testId={`supp-item-${it.index}`} />
    </div>
  )
}

/**
 * @param split       supplement{block:'split'}.text（无＝null）
 * @param attribution supplement{block:'attribution'}.text（无＝null）
 */
export default function SupplementBlocks({ split = null, attribution = null }) {
  const splitParsed = split ? parseSupplement(split) : null
  const attrParsed = attribution ? parseSupplement(attribution) : null
  const items = []
  if (attrParsed && attrParsed.items.length > 0) {
    items.push({
      key: 'attribution',
      label: <span style={dim}>按来源列出（每条结论标明出处）</span>,
      children: (
        <div data-testid="supp-attribution">
          {attrParsed.head && <div style={{ ...dim, marginBottom: 4 }}>{attrParsed.head}</div>}
          {bySource(attrParsed.items).map(g => (
            <div key={g.source} style={{ marginBottom: 6 }}>
              <div style={{ fontSize: 12 }}>{`${g.source || '来源未标注'}（${g.items.length} 条）`}</div>
              {g.items.map(it => <ItemLine key={it.index} it={{ ...it, source: '' }} />)}
            </div>
          ))}
        </div>
      )
    })
  }
  if (splitParsed && splitParsed.items.length > 0) {
    items.push({
      key: 'split',
      label: <span style={dim}>各来源说法不一 · 点开对照</span>,
      children: (
        <div data-testid="supp-split">
          {splitParsed.head && <div style={{ ...dim, marginBottom: 4 }}>{splitParsed.head}</div>}
          {splitParsed.items.map(it => <ItemLine key={it.index} it={it} />)}
        </div>
      )
    })
  }
  if (items.length === 0) return null
  return (
    <Collapse size="small" style={{ margin: '6px 0' }} data-testid="supplement-blocks" items={items} />
  )
}
