/**
 * ThreadList · 左侧历史对话列（上拉加载 + 搜索）——Owner 2026-10-17 反馈 2。
 *
 * **数据源形态对齐真接口**（`appv2/api/chat.py:189-221` 实证）：
 * `GET /api/v2/chat/runs?limit=N`——`limit` 夹取 1..100、**无 offset、无搜索参数**、按
 * `created_at` 降序返回。故「上拉加载更多」的语义**不是**分页偏移，而是**扩大 limit 重拉全量**：
 *   limit 步进 20 → 40 → 60 → 80 → 100（到 100 封顶，与后端 clamp 一致）。
 * 真接线时照此实现：`listRunsV2(limit)` 传入当前 limit，拿回全量前 N 条后整体替换列表。
 * （现状 A1V2.jsx 走的是 `listRunsV2(20)` + buildThreads 链分组；本件只做「上拉加载＋搜索」
 * 的列表语义，不做链分组——分组仍归 A1V2。）
 *
 * 交互：
 * - 滚动到列表**顶部**触发加载更多（滚轮/触控板往上）＋顶部一枚「加载更早」按钮（同一 handler
 *   ——jsdom 里滚不动，测试直调按钮即等价的回调入口）；
 * - 到 100 条后顶部出「已到最早」小字，**不再出 Spin**（不假装还能加载）；
 * - 搜索框（antd Input）：对**当前已加载窗口**的问句做前端过滤（后端无搜索参数，见上）；
 *   过滤中不再触发上拉加载（加载更多入口整体让位），无命中＝「无匹配对话」空态；
 * - 选中行高亮（与现状 A1V2 行高亮同形：蓝底 + data-selected）。
 *
 * 空态：`runs` 为空（真接线＝列表拉取失败或空库）＝「暂无历史对话」，不报错不伪造。
 */
import { useState } from 'react'
import { Button, Input, List } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { dim } from '../../components/helpIcon.jsx'

/** 状态文案（与 A1V2.jsx STATUS_TEXT 同词表——词表单源诉求见该文件头注）。 */
const STATUS_TEXT = { running: '运行中', waiting_ask: '待确认', completed: '已完成', failed: '失败' }

/** ISO/『YYYY-MM-DD HH:mm:ss』→「MM-DD HH:mm」（同 A1V2.jsx fmtTime 口径）。 */
function fmtTime(iso) {
  return (iso || '').replace('T', ' ').slice(5, 16)
}

/** 行标题截断（18 字＋省略号——截断本身如实标出，不像是渲染坏了）。 */
function short(text) {
  const s = String(text ?? '')
  return s.length > 18 ? `${s.slice(0, 18)}…` : s
}

/**
 * @param runs        运行行数组（RunListItem 形态；本件按自身 limit 取前 N 条）
 * @param pageStep    每次「加载更早」的 limit 步长（后端无 offset——步长即 limit 增量）
 * @param maxRows     上限（与后端 limit clamp 的 100 一致）
 * @param selectedId  选中行 run_id（高亮）
 * @param onSelect    行点击回调 (run) => void
 */
export default function ThreadList({
  runs = [], pageStep = 20, maxRows = 100, selectedId = '', onSelect
}) {
  const [limit, setLimit] = useState(pageStep)
  const [query, setQuery] = useState('')

  const keyword = query.trim().toLowerCase()
  const searching = keyword.length > 0
  const atEarliest = limit >= maxRows
  const window = runs.slice(0, limit)
  const rows = searching
    ? window.filter(r => (r.question || '').toLowerCase().includes(keyword))
    : window

  /** 加载更早（扩大 limit 重拉全量）：搜索中不触发；到上限不触发。 */
  const loadMore = () => {
    if (searching || atEarliest) return
    setLimit(l => Math.min(l + pageStep, maxRows))
  }

  /** 滚到顶部＝加载更早（真接线形态；jsdom 无真滚动＝测试直调 loadMore 等价入口）。 */
  const onScroll = e => {
    if (e?.currentTarget?.scrollTop <= 0) loadMore()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0, height: '100%' }}
      data-testid="thread-list">
      <Input size="small" allowClear prefix={<SearchOutlined style={{ color: '#8a94a3' }} />}
        placeholder="搜索对话" value={query} onChange={e => setQuery(e.target.value)}
        style={{ marginBottom: 6 }} />

      <div onScroll={onScroll} style={{ flex: 1, minHeight: 0, overflowY: 'auto' }} data-testid="thread-scroll">
        {/* 顶部：加载更早 / 已到最早 / 搜索中不加载（三者互斥） */}
        {!searching && !atEarliest && (
          <Button size="small" type="link" block style={{ padding: 0, marginBottom: 4 }}
            data-testid="load-more" onClick={loadMore}>
            {`加载更早（已载入 ${limit} / ${Math.min(runs.length, maxRows)}）`}
          </Button>
        )}
        {!searching && atEarliest && (
          <div style={{ ...dim, textAlign: 'center', marginBottom: 4 }} data-testid="earliest-tip">
            已到最早
          </div>
        )}
        {searching && (
          <div style={{ ...dim, marginBottom: 4 }} data-testid="search-scope">
            {`已载入 ${limit} 条中匹配 ${rows.length} 条`}
          </div>
        )}

        <List size="small" dataSource={rows} locale={{ emptyText: searching ? '无匹配对话' : '暂无历史对话' }}
          renderItem={r => {
            const sel = r.run_id === selectedId
            return (
              <List.Item data-selected={sel ? 'true' : 'false'} data-testid={`thread-row-${r.run_id}`}
                style={{
                  cursor: 'pointer', padding: '4px 6px', borderRadius: 6,
                  background: sel ? 'rgba(22,119,255,0.18)' : 'transparent'
                }}
                onClick={() => onSelect?.(r)}>
                <div style={{ width: '100%' }}>
                  <div style={{ fontSize: 13 }}>{short(r.question || r.run_id)}</div>
                  <div style={dim}>
                    {`${STATUS_TEXT[r.status] ?? r.status} · ${fmtTime(r.created_at)}`}
                  </div>
                </div>
              </List.Item>
            )
          }} />
      </div>
    </div>
  )
}
