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
 * 显示粒度＝**一链一行**（旧页 608267b A1V2.jsx buildThreads 的分组语义回归）：窗口内行先按
 * 追问链归属分组（followup_of 逐跳上溯取根，根＝followup_of 空串或指向窗口外——与真流页
 * A1V2R collectChain 同一 `cites.js::chainRootId`），链序按最新轮 `created_at` 降序。链分组
 * **只作用于显示**：上拉加载语义、读口回传窗口（onRuns）皆按原始行不变。
 * 行＝链内 created_at 最早的一轮（旧页 buildThreads 的行标识口径，正常数据下即链根：
 * `title`＝该轮问句，18 字截断沿 short()；testid 用该轮 run_id）；副行＝
 * `{最新轮状态白话} · {链轮数} 轮 · {MM-DD HH:mm}`（最新轮＝窗口内 created_at 最大者）；
 * 点击行 → `onSelect(链内最新轮行)`（拉链由页面从任意成员破窗展开——本件不拉链）；
 * 选中高亮＝selectedId 所在**链整行**高亮（链成员含 selectedId 即高亮）。
 *
 * 读口失败态（UI-14 同位纪律——**失败≠空库**）：`loadState` 分离——读口失败＝计数行（加载
 * 入口）撤下＋「暂无数据」失败空态（沿用词表文案，已有行不销毁）；读口如实返回
 * 空列＝「暂无历史对话」。加载中 Spin 只挂在「加载更早」按钮位（不整块遮罩）。
 *
 * 窗口回传（L3 拉链用）：每次成功拉取经 `onRuns` 把**当前窗口**（前 limit 条）交回页面——
 * A1V2R 据此 collectChain（followup_of 逐跳上溯定根，按 created_at 升序成链）。
 *
 * 交互（L2 搜索不动；加载入口按 Owner 反馈调到**底部**）：
 * - 列表最新在上、更早在下——**滚到列表底部**（离底 ≤ 40px）触发加载更早（滚轮/触控板往下），
 *   入口按钮同置于列表之后（同一 handler——jsdom 里滚不动，测试桩化滚动量或直调按钮等价）；
 * - 到 100 条后底部出「已到最早」小字，**不再出 Spin**（不假装还能加载）；
 * - 搜索框（antd Input）：对**当前已加载窗口**的问句做前端过滤（后端无搜索参数，零请求）；
 *   命中任一链轮＝该链全部成员保留（链不因搜索残缺），再分组；过滤中不再触发上拉加载
 *   （加载更多入口整体让位），无命中＝「无匹配对话」空态；
 * - 选中行高亮（蓝底 + data-selected）。
 */
import { useEffect, useState } from 'react'
import { Button, Input, List } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { listRunsV2 } from '../../api/chatV2.js'
import { dim } from '../../components/helpIcon.jsx'
import { groupRunsIntoChains } from './cites.js'

/** 状态文案（与后端 status 闭世界同词表：running/waiting_ask/completed/failed）。 */
const STATUS_TEXT = { running: '运行中', waiting_ask: '待确认', completed: '已完成', failed: '失败' }

/** 触底判定阈值（px——离底这么近就当作到底，滚轮惯性到位即触发）。 */
const BOTTOM_GAP_PX = 40

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
 * @param selectedId  选中轮 run_id（所在链整行高亮）
 * @param onSelect    行点击回调 (链内最新轮行) => void
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
  const allChains = groupRunsIntoChains(window) // 一链一行（行＝链根，副行＝最新轮状态·轮数·时间）
  // 搜索（L2）：命中任一链轮＝该链全部成员保留（先分组再按链过滤——链不因搜索残缺、轮数如实）
  const chains = searching
    ? allChains.filter(c => c.rounds.some(r => (r.question || '').toLowerCase().includes(keyword)))
    : allChains

  /** 加载更早（扩大 limit 重拉全量替换）：搜索中不触发；到上限不触发。 */
  const loadMore = () => {
    if (searching || atEarliest) return
    const next = Math.min(limit + pageStep, maxRows)
    setLimit(next)
    load(next)
  }

  /** 滚到列表底部＝加载更早（列表最新在上、更早在下：滚到底＝看更早）。 */
  const onScroll = e => {
    const el = e?.currentTarget
    if (!el) return
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - BOTTOM_GAP_PX) loadMore()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}
      data-testid="thread-list">
      <Input size="small" allowClear prefix={<SearchOutlined style={{ color: '#8a94a3' }} />}
        placeholder="搜索对话" value={query} onChange={e => setQuery(e.target.value)}
        style={{ marginBottom: 6 }} />

      <div onScroll={onScroll} style={{ flex: 1, minHeight: 0, overflowY: 'auto' }} data-testid="thread-scroll">
        {searching && (
          <div style={{ ...dim, marginBottom: 4 }} data-testid="search-scope">
            {`已载入 ${limit} 条中匹配 ${chains.length} 个对话`}
          </div>
        )}

        <List size="small" dataSource={chains}
          locale={{ emptyText: loadState === 'error' ? '暂无数据' : searching ? '无匹配对话' : '暂无历史对话' }}
          renderItem={c => {
            const sel = c.rounds.some(r => r.run_id === selectedId)
            return (
              <List.Item data-selected={sel ? 'true' : 'false'} data-testid={`thread-row-${c.rootId}`}
                style={{
                  cursor: 'pointer', padding: '4px 6px', borderRadius: 6,
                  background: sel ? 'rgba(22,119,255,0.18)' : 'transparent'
                }}
                onClick={() => onSelect?.(c.latest)}>
                <div style={{ width: '100%' }}>
                  <div style={{ fontSize: 13 }}>{short(c.title)}</div>
                  <div style={dim}>
                    {`${STATUS_TEXT[c.latest.status] ?? c.latest.status} · ${c.rounds.length} 轮`
                      + ` · ${fmtTime(c.latest.created_at)}`}
                  </div>
                </div>
              </List.Item>
            )
          }} />

        {/* 底部（列表之后＝滚到底的方向）：加载更早 / 已到最早；二者与搜索互斥。
            读口失败＝入口撤下（失败≠空库——不撒「还能加载」的谎） */}
        {!searching && loadState !== 'error' && !atEarliest && (
          <Button size="small" type="link" block style={{ padding: 0, marginTop: 4 }}
            data-testid="load-more" onClick={loadMore} loading={loadState === 'loading'}>
            {`加载更早（已载入 ${limit} / ${Math.min(runs.length, maxRows)}）`}
          </Button>
        )}
        {!searching && loadState !== 'error' && atEarliest && (
          <div style={{ ...dim, textAlign: 'center', marginTop: 4 }} data-testid="earliest-tip">
            已到最早
          </div>
        )}
      </div>
    </div>
  )
}
