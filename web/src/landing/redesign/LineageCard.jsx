/**
 * LineageCard · 血缘／查询口径卡（设计稿 §3.4）。
 *
 * 回答用户三问：「这数哪来的、按什么口径算、数据更新到哪天」。
 * 数据源优先级：① `observation.payload.lineage`（结构化键值——首选，免正则解文本）；
 * ② `supplement{block:'lineage'}.text`（纯文本兜底——按 ①-⑤ 行切）。
 * `payload.limit.hit` 为真时补一行「结果超上限，只取了前 N 条」（截断如实披露）。
 *
 * 白话纪律（锚例：《最佳实践-3a-白话化与受众适配.md》§3.1「口径（即统计标准）」
 * 「台账（系统里的指标与术语登记表）」）：卡头一句白话 ＋ 「?」注解一次性给出
 * 「口径／台账」两个行话的白话注解——本页行话首现处即此卡头。
 * 工程腔原文（M-01 两步缝、D6 star_model、actor=aqiang…）**原样保留**在卡内（可追溯，
 * 不洗白不翻译），只在视觉上退为小字。
 *
 * 「数据截至批次」要素高亮——用户最关心「更新到哪天」（超期与否直接影响敢不敢引用该数）。
 * 空态：无血缘（非数据题）＝整卡不渲染。
 */
import { useState } from 'react'
import { Button, Tag } from 'antd'
import { DownOutlined, UpOutlined } from '@ant-design/icons'
import { dim, helpIcon } from '../../components/helpIcon.jsx'

/** 卡头白话（同行话注解一次给全——口径/台账）。 */
const HEAD_HELP = (
  <>
    这里说明上面的数字从哪来、按什么口径算、数据更新到哪天。
    <br />
    口径＝统计标准（这数按什么标准算出来的）；台账＝系统里的指标与术语登记表。
    <br />
    卡里的表名、批次号、权限注入等是系统原文，照录不改——看不懂可忽略，不影响读数。
  </>
)

/** 五要素标签形如「① 口径」；子行形如「　└（权限注入）」。 */
const ELEMENT_RE = /^[①②③④⑤]/

/** structured lineage（对象）→ 行数组 [{label, value, sub}]。 */
function rowsFromObject(lineage) {
  return Object.entries(lineage || {}).map(([label, value]) => ({
    label: label.trim(),
    value: String(value ?? ''),
    sub: /^[　\s]*(└|├)/.test(label)
  }))
}

/** 纯文本兜底 → 行数组（①-⑤ 起新行；缩进/└ 续行归上一行）。 */
function rowsFromText(text) {
  const rows = []
  for (const raw of String(text ?? '').split('\n')) {
    const line = raw.replace(/[ \t]+$/, '')
    if (!line.trim()) continue
    if (ELEMENT_RE.test(line.trim())) {
      rows.push({ label: line.trim().split(/\s+/)[0], value: line.trim(), sub: false })
      continue
    }
    if (rows.length === 0) { rows.push({ label: '', value: line.trim(), sub: false }); continue }
    const last = rows[rows.length - 1]
    last.value += '\n' + line.trim()
  }
  return rows
}

/**
 * @param lineage    observation.payload.lineage（结构化五要素；无＝null）
 * @param limit      observation.payload.limit（{hit, rows}；无＝null）
 * @param text       supplement{block:'lineage'}.text（纯文本兜底）
 * @param defaultOpen 初态是否展开（默认收起——过程/口径类默认不抢正文）
 */
export default function LineageCard({ lineage = null, limit = null, text = '', defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  const rows = lineage ? rowsFromObject(lineage) : rowsFromText(text)
  if (rows.length === 0) return null

  return (
    <div data-testid="lineage-card"
      style={{ border: '1px solid #e0e4e8', borderRadius: 6, margin: '8px 0', background: 'rgba(127,127,127,0.05)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', fontSize: 12 }}>
        <span>📖 这数哪来的 · 查询口径</span>
        {helpIcon(HEAD_HELP)}
        <Button size="small" type="link" style={{ marginLeft: 'auto', padding: 0 }}
          data-testid="lineage-toggle" onClick={() => setOpen(o => !o)}>
          {open ? <>收起 <UpOutlined style={{ fontSize: 10 }} /></> : <>展开看口径 <DownOutlined style={{ fontSize: 10 }} /></>}
        </Button>
      </div>

      {open && (
        <div style={{ padding: '0 10px 8px' }} data-testid="lineage-body">
          {rows.map((r, i) => {
            const isBatch = r.label.includes('数据截至批次') || r.value.startsWith('④ 数据截至批次')
            return (
              <div key={i} data-testid={isBatch ? 'lineage-batch-row' : undefined}
                style={{
                  fontSize: 12, lineHeight: 1.7, whiteSpace: 'pre-wrap', padding: '2px 6px', borderRadius: 4,
                  ...(r.sub ? { ...dim, paddingLeft: 18 } : {}),
                  ...(isBatch
                    ? { background: 'rgba(232,179,57,0.16)', borderLeft: '3px solid #e8b339', fontWeight: 600 }
                    : {})
                }}>
                {isBatch && <Tag color="gold" style={{ fontSize: 10, marginRight: 6 }}>更新到哪天</Tag>}
                {r.value}
              </div>
            )
          })}
          {limit?.hit && (
            <div style={{ ...dim, marginTop: 6 }}>
              {`结果超过单次上限，只取了前 ${limit.rows ?? ''} 条——超上限部分未取，未取到的范围不作答。`}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
