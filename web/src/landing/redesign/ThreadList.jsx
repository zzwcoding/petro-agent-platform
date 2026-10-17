/**
 * ThreadList · 左侧历史对话列（FE-04 真接 listRunsV2——上拉加载 + 搜索）。
 *
 * 数据源（specs/frontend-redesign.md 行为约定 L1 真接）：props 喂数改**内部态＋读口注入**——
 * `fetchRuns` 默认 `listRunsV2`（chatV2 既有读口，只调用不改；测试注桩零网络）。
 * `GET /api/v2/chat/runs?limit=N`（`appv2/api/chat.py:189-221` 实证）：`limit` 夹取 1..100、
 * **无 offset、无搜索参数**、按 `created_at` 降序返回。故「上拉加载更多」的语义**不是**分页
 * 偏移，而是**扩大 limit 重拉全量替换**：limit 步进 20 → 40 → 60 → 80 → 100（到 100 封顶，
 * 与后端 clamp 一致）。`pageStep`/`maxRows` 默认值＝20/100，与后端夹取同形。
 *
 * 读口失败态（UI-14 同位纪律——**失败≠空库**）：`loadState` 分离——读口失败＝计数行（加载
 * 入口）撤下＋「暂无数据」失败空态（沿用词表文案，已有行不销毁）；读口如实返回
 * 空列＝「暂无历史对话」。加载中 Spin 只挂在「加载更早」按钮位（不整块遮罩）。
 *
 * 窗口回传（L3 拉链用）：每次成功拉取经 `onRuns` 把**当前窗口**（前 limit 条）交回页面——
 * A1V2R 据此 collectChain（followup_of 逐跳上溯定根，按 created_at 升序成链）。
 *
 * 交互（L2 行为不动）：
 * - 滚动到列表**顶部**触发加载更多（滚轮/触控板往上）＋顶部一枚「加载更早」按钮（同一 handler
 *   ——jsdom 里滚不动，测试直调按钮即等价的回调入口）；
 * - 到 100 条后顶部出「已到最早」小字，**不再出 Spin**（不假装还能加载）；
 * - 搜索框（antd Input）：对**当前已加载窗口**的问句做前端过滤（后端无搜索参数，零请求）；
 *   过滤中不再触发上拉加载（加载更多入口整体让位），无命中＝「无匹配对话」空态；
 * - 选中行高亮（蓝底 + data-selected）。
 */
import { useEffect, useState } from 'react'
import { Button, Input, List } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { listRunsV2 } from '../../api/chatV2.js'
import { dim } from '../../components/helpIcon.jsx'

/** 状态文案（与后端 status 闭世界同词表：running/waiting_ask/completed/failed）。 */
const STATUS_TEXT = { running: '运行中', waiting_ask: '待确认', completed: '已完成', failed: '失败' }

/** ISO/『YYYY-MM-DD HH:mm:ss』→「MM-DD HH:mm」（列表行时间口径）。 */
function fmtTime(iso) {
  return (iso || '').replace('T', ' ').slice(5, 16)
}

/** 行标题截断（18 字＋省略号——截断本身如实标出，不像是渲染坏了）。 */
function short(text) {
  const s = String(text ?? '')
  return s.length > 18 ? `${s.slice(0, 18)}…` : s
}

/**
 * @param fetchRuns   读口注入点（默认 listRunsV2——只调用不改；测试注桩零网络）
 *                    (limit) => Promise<RunListItem[]>
 * @param onRuns      当前窗口回传（每次成功拉取后调 (前 limit 条) => void）——页面拉链分组用
 * @param pageStep    每次「加载更早」的 limit 步长（后端无 offset——步长即 limit 增量）
 * @param maxRows     上限（与后端 limit clamp 的 100 一致）
 * @param selectedId  选中行 run_id（高亮）
 * @param onSelect    行点击回调 (run) => void
 */
export default function ThreadList({
  fetchRuns = listRunsV2, onRuns = null, pageStep = 20, maxRows = 100,
  selectedId = '', onSelect
}) {
  const [runs, setRuns] = useState([])     // 全量窗口（created_at 降序——后端已排序，前端不重排）
  const [limit, setLimit] = useState(pageStep)
  const [loadState, setLoadState] = useState('ok') // 'ok'|'error'——失败≠空库（UI-14 同位纪律）
  const [query, setQuery] = useState('')   // 搜索态（L2 维持前端过滤，零请求）

  /** 初载与「加载更早」共用：按 limitValue 重拉全量替换（后端无 offset 的既定映射）。 */
  const load = async limitValue => {
    setLoadState('loading')
    try {
      const rows = await fetchRuns(limitValue)
      setRuns(rows)
      setLoadState('ok')
      onRuns?.(rows.slice(0, limitValue)) // 当前窗口回传（A1V2R collectChain 拉链分组用）
    } catch {
      setLoadState('error')               // 计数行撤下＋「暂无数据」失败空态；已有行不销毁
    }
  }

  useEffect(() => {
    load(pageStep) // 初始 limit=pageStep＝20（specs/frontend-redesign.md「验收测试」表第 14 行）
  // eslint-disable-next-line react-hooks/exhaustive-deps -- mount 一次（初载读口＝注入的 fetchRuns）
  }, [])

  const keyword = query.trim().toLowerCase()
  const searching = keyword.length > 0
  const atEarliest = limit >= maxRows
  const window = runs.slice(0, limit)
  const rows = searching
    ? window.filter(r => (r.question || '').toLowerCase().includes(keyword))
    : window

  /** 加载更早（扩大 limit 重拉全量替换）：搜索中不触发；到上限不触发。 */
  const loadMore = () => {
    if (searching || atEarliest) return
    const next = Math.min(limit + pageStep, maxRows)
    setLimit(next)
    load(next)
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
        {/* 顶部：加载更早 / 已到最早 / 搜索中不加载（三者互斥）；读口失败＝计数行撤下（失败≠空库） */}
        {!searching && loadState !== 'error' && !atEarliest && (
          <Button size="small" type="link" block style={{ padding: 0, marginBottom: 4 }}
            data-testid="load-more" onClick={loadMore} loading={loadState === 'loading'}>
            {`加载更早（已载入 ${limit} / ${Math.min(runs.length, maxRows)}）`}
          </Button>
        )}
        {!searching && loadState !== 'error' && atEarliest && (
          <div style={{ ...dim, textAlign: 'center', marginBottom: 4 }} data-testid="earliest-tip">
            已到最早
          </div>
        )}
        {searching && (
          <div style={{ ...dim, marginBottom: 4 }} data-testid="search-scope">
            {`已载入 ${limit} 条中匹配 ${rows.length} 条`}
          </div>
        )}

        <List size="small" dataSource={rows}
          locale={{ emptyText: loadState === 'error' ? '暂无数据' : searching ? '无匹配对话' : '暂无历史对话' }}
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
