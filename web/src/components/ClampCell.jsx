import { Tooltip } from 'antd'

/**
 * 表格单元格长文本截断（refactoring-ui §4.3 行宽 / §2.2 扫读性）。
 *
 * 改造前「规则」「判据 · 阈值」两列塞整句长文本，行高从 2 行到 4 行参差，
 * 整张表没法竖着扫。现按 2 行截断，完整原文挂 Tooltip——内容一字不删，
 * 只把「需要展开才知道」的细节收进悬停层，表格恢复等高、可纵向扫读。
 * —— 共享件（从 landing/E2.jsx 提取，落地树三页共用）
 */
export default function ClampCell({ text, rows = 2 }) {
  const s = String(text ?? '')
  if (!s) return null
  return (
    <Tooltip title={s} placement="topLeft">
      <div style={{
        display: '-webkit-box', WebkitLineClamp: rows, WebkitBoxOrient: 'vertical',
        overflow: 'hidden', whiteSpace: 'normal',
      }}>{s}</div>
    </Tooltip>
  )
}
