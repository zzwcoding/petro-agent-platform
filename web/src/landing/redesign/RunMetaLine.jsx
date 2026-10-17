/**
 * RunMetaLine · 轮次卡底部小字行（设计稿 §3.7）。
 *
 * 三段（有则出、无则不出——空态纪律）：
 * - **核验徽标**：`verdict(verify)` 的计数——有据 N 条 · 改写 M 条 · 分列 K 条
 *   （有据＝被核验支撑的结论数；改写＝核验时删改过的无据断言；分列＝多来源不一致分列）；
 * - **档案小字**：`blackbox` counts（步数/材料数）＋ 档案 KB（stored/bytes）；
 * - **运行号＋本地计时**：run 号；时长**本地计时**（后端无耗时字段），标注「本地计时」。
 *
 * 挂起腿无 blackbox／无 verdict ＝ 相应段不渲染（不猜、不补零——「0 条」与「没有这项数据」
 * 是两回事）。全空（无 run 号、无 blackbox、无核验）＝整行不渲染。
 */
import { dim } from '../../components/helpIcon.jsx'

const OK = { ...dim, color: '#52c41a' }

/**
 * @param runId       run 号（''＝不显示）
 * @param verdict     verdict(verify) 帧 data（无＝null）
 * @param blackbox    blackbox 帧 data（无＝null，如挂起腿）
 * @param durationS   本地计时秒数（null＝不显示）
 */
export default function RunMetaLine({ runId = '', verdict = null, blackbox = null, durationS = null }) {
  const parts = []
  if (verdict) {
    parts.push(
      <span key="verify" style={OK} data-testid="runmeta-verify">
        {`已核验：有据 ${verdict.supported ?? 0} 条 · 改写 ${verdict.rewritten ?? 0} 条 · 分列 ${verdict.split ?? 0} 条`}
      </span>
    )
  }
  if (blackbox) {
    const c = blackbox.counts || {}
    const kb = typeof blackbox.bytes === 'number' ? `${Math.round(blackbox.bytes / 1024)} KB` : ''
    parts.push(<span key="bb">{[
      `${c.steps ?? 0} 步`, `${c.observations ?? 0} 材料`, kb || null
    ].filter(Boolean).join(' · ')}</span>)
  }
  if (runId) parts.push(<span key="run">{runId}</span>)
  if (durationS != null) parts.push(<span key="dur">{`本地计时 ${durationS}s`}</span>)

  if (parts.length === 0) return null
  return (
    <div data-testid="run-meta-line" style={{ ...dim, marginTop: 6, lineHeight: 1.8 }}>
      {parts.map((p, i) => (
        <span key={i}>
          {i > 0 && ' · '}
          {p}
        </span>
      ))}
    </div>
  )
}
