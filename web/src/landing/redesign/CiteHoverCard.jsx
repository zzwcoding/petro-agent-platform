/**
 * CiteHoverCard · 引标悬停预览卡（设计稿 §3.2）——正文 `[n]` 悬停出的材料切片小卡。
 *
 * **零请求**：内容直查内存 `materials[index].content`（与 WeKnora「每次悬停发一次请求」
 * 不同——我方内容已在回合内）。无对应材料＝调用方不弹（AnswerView 的 `citeHoverCard`
 * 返回空即不弹，见 AnswerView.jsx 头注）。
 *
 * 「点引标打开原文全文＋定位高亮」短期做不了（后端无切片→原文位置锚点接口，设计 §4），
 * 本卡如实只给切片内容＋出处，不给「看原文」按钮（不承诺做不到的事）。
 * `trust=notice` 的条目是**程序声明**不是文档原文——卡头点明，不伪装文档。
 */
import { Tag } from 'antd'
import { dim } from '../../components/helpIcon.jsx'
import { trustLabel } from './cites.js'

/**
 * @param cite     引用帧 {index, source, source_id, trust}
 * @param material 同 index 的材料帧 {content, ...}（无配对＝null）
 */
export default function CiteHoverCard({ cite, material }) {
  if (!cite) return null
  const isNotice = cite.trust === 'notice'
  return (
    <div style={{ maxWidth: 420 }} data-testid="cite-hover-card">
      <div style={{ fontSize: 12, marginBottom: 4 }}>
        <Tag style={{ fontSize: 10 }}>{`[${cite.index}]`}</Tag>
        <span>{cite.source}</span>
        <Tag style={{ marginLeft: 6, fontSize: 10 }}>{trustLabel(cite.trust)}</Tag>
      </div>
      {cite.source_id && <div style={{ ...dim, marginBottom: 4 }}>{`出处编号：${cite.source_id}`}</div>}
      {isNotice && <div style={{ ...dim, marginBottom: 4 }}>这一条是系统生成的声明，不是文档原文。</div>}
      <div data-testid="cite-hover-body"
        style={{ fontSize: 12, lineHeight: 1.7, whiteSpace: 'pre-wrap', maxHeight: 180, overflowY: 'auto' }}>
        {material?.content || '（材料未在回合内渲染）'}
      </div>
    </div>
  )
}
