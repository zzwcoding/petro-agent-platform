/**
 * 落地 D1 页组件测试（P0-07；P1-10 增强批）——fetch 级 mock（apiRouter 挡在
 * window.fetch 边界），client/gateway 接口层与页面全部真代码：
 * - 渲染：页头徽标＋模型表＋四页签（端点 1 形状）＋观测（Langfuse）外链按钮；
 * - 错误包展示路径：models 拉取失败 → 内联 Alert（message/code/trace_id）；
 * - 配置读写：表单编辑（含预算双阈值六件）→ PUT body snake_case → 服务端快照
 *   回显（端点 2/3 v0.2 扩段）；
 * - 聚合页签：流水/聚合 Segmented → 端点 8 真接（group_by 切换/sums 期间合计/
 *   day·month 趋势列/拉取失败内联 Alert）；
 * - 409 重入兜底：受理拒绝 → 内联提示＋按钮禁用（端点 5）；
 * - 演练轮询收场：202 → useTaskPolling running→done → 结论/切换留痕/历史与流水
 *   刷新（端点 5/6/7 全链路）；
 * - UI-06 交互优化（阶段 1）：四表接 PagedTable（流水 server 模式形状不变／聚合·
 *   线路·演练 client 统计恒显）、演练日志失败态分立、流水关键词 300ms 防抖、
 *   「适用范围」收束页头 helpTop、时间列补年（fmtTime 单点）、复制降级、scroll.x 联调。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import D1Landing from './D1.jsx'

// antd v5 在 jsdom 下的两个环境桩（matchMedia＝响应式断点；ResizeObserver＝Table 测宽）
if (!window.matchMedia) {
  window.matchMedia = query => ({
    matches: false, media: query, onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn()
  })
}
if (!window.ResizeObserver) {
  window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }
}

// ── 合同形状夹具（后端 R1 snake_case，同 app/api/gateway.py 响应模型） ──

const MODELS = {
  gateway: { status: 'running' },
  models: [
    { key: 'main', name: 'MiniMax-M3', alias: 'petro-main', role: 'main',
      access: 'Anthropic 兼容接口 · MiniMax 线路', note: '问答/问数/问智默认出口' },
    { key: 'backup', name: 'glm-5.3-flash', alias: 'petro-lite', role: 'backup',
      access: 'Anthropic 兼容接口 · 智谱线路', note: '备用/降级组——fallback 与预算熔断的便宜出口' }
  ]
}
const CONFIG = {
  params: {
    allowed_fails: 2, cooldown_seconds: 60, num_retries: 3, request_timeout: 30,
    per_call_cost_limit_yuan: 0.05, gateway_budget_yuan_per_month: 800
  },
  yaml: '# models.yaml（夹具全文）\ngateway:\n  allowed_fails: 2\n  num_retries: 3\n'
}
const CONFIG_SAVED = {
  params: {
    allowed_fails: 5, cooldown_seconds: 60, num_retries: 3, request_timeout: 30,
    per_call_cost_limit_yuan: 0.05, gateway_budget_yuan_per_month: 800
  },
  yaml: '# models.yaml（夹具全文·保存后）\ngateway:\n  allowed_fails: 5\n  num_retries: 3\n'
}
const SPEND = {
  items: [
    { id: 'call-8c31', time: '2026-09-28T09:52:30', model_key: 'main', alias: 'petro-main',
      input_tokens: 2140, output_tokens: 1380, first_ms: 1000, total_ms: 4000, cost_yuan: 0.007,
      fallback: false, note: '', caller: 'chat.retrieval.answer' },
    { id: 'call-8c32', time: '2026-09-28T10:00:00', model_key: 'backup', alias: 'petro-lite',
      input_tokens: 1010, output_tokens: 590, first_ms: 1300, total_ms: 3800, cost_yuan: 0.0038,
      fallback: true, note: '故障自动切换：请求别名 petro-main → 备用 petro-lite 应答', caller: 'gateway.drill' }
  ],
  total: 2, page: 1, page_size: 15
}
// 端点 8 聚合读面（wire snake 形——caller 维度两桶＋存量 unattributed）
const SPEND_STATS = {
  group_by: 'caller', range: '30d',
  items: [
    { caller: 'chat.retrieval.answer', calls: 12, fallback_calls: 1, input_tokens: 24000, output_tokens: 13000, cost_yuan: 0.031 },
    { caller: 'gateway.drill', calls: 1, fallback_calls: 1, input_tokens: 1010, output_tokens: 590, cost_yuan: 0.0038 },
    { caller: 'unattributed', calls: 2, fallback_calls: 0, input_tokens: 220, output_tokens: 110, cost_yuan: 0.0011 }
  ],
  sums: { calls: 15, fallback_calls: 2, cost_yuan: 0.0359 },
  total: 3, page: 1, page_size: 15
}
// day 维度（趋势时序升序全量）
const SPEND_STATS_DAY = {
  group_by: 'day', range: '30d',
  items: [
    { day: '2026-09-27', calls: 8, fallback_calls: 0, input_tokens: 12000, output_tokens: 6000, cost_yuan: 0.015 },
    { day: '2026-09-28', calls: 7, fallback_calls: 2, input_tokens: 13230, output_tokens: 7700, cost_yuan: 0.0209 }
  ],
  sums: { calls: 15, fallback_calls: 2, cost_yuan: 0.0359 },
  total: 2, page: 1, page_size: 15
}
// caller 维度 21 桶（UI-06 T2：client 分页两页夹具——翻页后 resetKey 归页断言用）
const SPEND_STATS_MANY = {
  group_by: 'caller', range: '30d',
  items: Array.from({ length: 21 }, (_, i) => ({
    caller: `chat.bulk.${i}`, calls: 1, fallback_calls: 0, input_tokens: 100, output_tokens: 50, cost_yuan: 0.001
  })),
  sums: { calls: 21, fallback_calls: 0, cost_yuan: 0.021 },
  total: 21, page: 1, page_size: 15
}
const DRILLS_HISTORY = [
  { id: 'drill-9018', time: '2026-09-28T09:12:30', summary: '演练：主用连续失败 2 次（阈值 2，冷却 60s）→ 备用应答正常' }
]
const DRILL_RUNNING = {
  drill_id: 'drill-9019', status: 'running',
  nodes: [
    { key: 'fail1', label: '第 1 次调用失败（注入）', state: 'finish', note: '演练注入：主模型路由摘除，第 1 次失败（无上游流量）' },
    { key: 'fail2', label: '第 2 次调用失败（注入）', state: 'process', note: '' },
    { key: 'fallback', label: '主备切换 · 备用应答', state: 'wait', note: '' },
    { key: 'ledger', label: '记账落账（备用应答行 fallback=true）', state: 'wait', note: '' }
  ],
  result: null
}
const DRILL_DONE = {
  drill_id: 'drill-9019', status: 'done',
  nodes: [
    { key: 'fail1', label: '第 1 次调用失败（注入）', state: 'error', note: '演练注入' },
    { key: 'fail2', label: '第 2 次调用失败（注入）', state: 'error', note: '演练注入' },
    { key: 'fallback', label: '主备切换 · 备用应答', state: 'finish', note: '主用进入冷却 60s，备用 anthropic/glm-5.3-flash 应答正常' },
    { key: 'ledger', label: '记账落账（备用应答行 fallback=true）', state: 'finish', note: '记账流水 +1（fallback=true，¥0.0038）' }
  ],
  result: {
    conclusion: '主用停机期间备用应答正常：注入 2 次失败后主用进入冷却 60s。',
    fallback: {
      time: '2026-09-28T10:05:00', event: 'fallback_triggered',
      request_alias: 'petro-main', failed_deploy: 'anthropic/MiniMax-M3',
      failover_target: 'anthropic/glm-5.3-flash', consecutive_fails: 2, cooldown_sec: 60
    },
    ledger_row: {
      id: 'call-8c33', time: '2026-09-28T10:05:00', model_key: 'backup', alias: 'petro-lite',
      input_tokens: 1010, output_tokens: 590, first_ms: 1300, total_ms: 3800, cost_yuan: 0.0038,
      fallback: true, note: '故障自动切换', caller: 'gateway.drill'
    }
  }
}

const json = (status, body) => ({ ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) })

/**
 * fetch 级 mock 路由（/api/gateway/* 八端点；overrides 按 URL 注入行为/错误）。
 */
function apiRouter(overrides = {}) {
  const calls = { spend: 0, stats: [], drills: 0, drillGet: 0, post: 0 }
  fetchMock.mockImplementation(async (url, init) => {
    const u = String(url)
    const method = init?.method || 'GET'
    if (u.includes('/api/gateway/models')) {
      return overrides.models ? overrides.models() : json(200, MODELS)
    }
    if (u.includes('/api/gateway/config')) {
      if (method === 'PUT') return overrides.putConfig ? overrides.putConfig(init) : json(200, CONFIG_SAVED)
      return overrides.getConfig ? overrides.getConfig() : json(200, CONFIG)
    }
    if (u.includes('/api/gateway/spend-stats')) {
      calls.stats.push(u)
      return overrides.stats ? overrides.stats(u) : json(200, SPEND_STATS)
    }
    if (u.includes('/api/gateway/spend-logs')) {
      calls.spend += 1
      return overrides.spend ? overrides.spend(u) : json(200, SPEND)
    }
    if (/\/api\/gateway\/drills\/[^/?]+$/.test(u)) {
      calls.drillGet += 1
      return overrides.drill ? overrides.drill(u) : json(200, DRILL_RUNNING)
    }
    if (u.includes('/api/gateway/drills')) {
      if (method === 'POST') {
        calls.post += 1
        return overrides.start ? overrides.start() : json(202, { drill_id: 'drill-9019' })
      }
      calls.drills += 1
      return overrides.drills ? overrides.drills() : json(200, DRILLS_HISTORY)
    }
    return json(404, { code: 'test_unrouted', message: `unexpected ${method} ${u}` })
  })
  return calls
}

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('D1 落地页 · 渲染（端点 1：页头徽标＋模型线路）', () => {
  it('页头「网关运行中」徽标＋主备副标题＋模型表两行＋四页签计数', async () => {
    apiRouter()
    render(<D1Landing />)

    expect(await screen.findByText('网关运行中')).toBeTruthy()
    expect(await screen.findByText('主用 MiniMax-M3 · 备用 glm-5.3-flash 待命')).toBeTruthy()
    expect(await screen.findByText('petro-main')).toBeTruthy()
    expect(screen.getByText('备用')).toBeTruthy() // 角色列
    expect(await screen.findByText('模型线路（2）')).toBeTruthy()
    expect(screen.getByText('调用参数（6）')).toBeTruthy()

    // client 底座：X-Dev-User 身份桩注入
    const modelsCall = fetchMock.mock.calls.find(c => String(c[0]).includes('/api/gateway/models'))
    expect(modelsCall[1].headers['X-Dev-User']).toBe('aqiang')

    // 观测（Langfuse）外链按钮（D1 v0.2 专节——页头外链，默认 :3000）
    const observe = await screen.findByTestId('observe-link')
    expect(observe.href).toContain('localhost:3000')
  })

  it('degraded 状态徽标（页头徽标消费 degraded）', async () => {
    apiRouter({ models: () => json(200, { ...MODELS, gateway: { status: 'degraded' } }) })
    render(<D1Landing />)
    expect(await screen.findByText('网关降级中（备用承载）')).toBeTruthy()
  })

  it('错误包展示路径：models 拉取 500 → 内联 Alert 带 message/code/trace', async () => {
    apiRouter({ models: () => json(500, { code: 'gateway_internal', message: '模型注册表读取失败', trace_id: 'call-abc' }) })
    render(<D1Landing />)
    expect(await screen.findByText('模型清单拉取失败（页头徽标与线路表暂不可用）')).toBeTruthy()
    expect(screen.getByText(/模型注册表读取失败/)).toBeTruthy()
    expect(screen.getByText(/code gateway_internal/)).toBeTruthy()
    expect(screen.getByText(/trace call-abc/)).toBeTruthy()
  })
})

describe('D1 落地页 · 记账流水（端点 4：分页信封＋snake→camel）', () => {
  it('流水表渲染 camel 列＋分页 total，行点击开抽屉看明细', async () => {
    const calls = apiRouter()
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('记账流水（2）'))

    expect(await screen.findByText('call-8c31')).toBeTruthy()
    expect(screen.getByText('2,140')).toBeTruthy()          // 输入 token（两整数，前端格式化）
    expect(screen.getByText('¥0.0070')).toBeTruthy()        // 花费元数值→前端格式化
    expect(screen.getByText('故障切换')).toBeTruthy()        // fallback=true 行
    expect(screen.getByText('共 2 条')).toBeTruthy()
    // UI-06 T8：时间列含年份（fmtTime 单点 YYYY-MM-DD HH:mm——跨年账目可辨）
    expect(screen.getByText('2026-09-28 09:52')).toBeTruthy()
    expect(screen.getByText('2026-09-28 10:00')).toBeTruthy()

    // query 组装：model/range/keyword/page/pageSize（pageSize 别名合同保留 camel）
    const spendUrl = fetchMock.mock.calls.find(c => String(c[0]).includes('/api/gateway/spend-logs'))[0]
    expect(spendUrl).toContain('page=1')
    expect(spendUrl).toContain('pageSize=15')

    // 行点击 → 抽屉（明细用行内真值 alias）
    fireEvent.click(screen.getByText('call-8c31'))
    expect(await screen.findByText('调用别名')).toBeTruthy()
    expect(await screen.findByText('petro-main')).toBeTruthy()
    // UI-06 T8：抽屉「调用时间」与表格同源 fmtTime（表格单元格＋抽屉两处含年）
    expect(screen.getAllByText('2026-09-28 09:52').length).toBeGreaterThanOrEqual(2)
    expect(calls.spend).toBeGreaterThanOrEqual(1)
  })

  it('筛选变更回第一页并带新 query（model=backup）', async () => {
    apiRouter()
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('记账流水（2）'))
    await screen.findByText('call-8c31')
    // 打开模型下拉选「备用」
    fireEvent.mouseDown(await screen.findByText('模型：全部'))
    fireEvent.click(await screen.findByText(/备用 · glm-5.3-flash/))
    await waitFor(() => {
      const last = fetchMock.mock.calls.filter(c => String(c[0]).includes('/api/gateway/spend-logs')).pop()
      expect(last[0]).toContain('model=backup')
      expect(last[0]).toContain('page=1')
    })
  })
})

describe('D1 落地页 · 花费聚合页签（端点 8——D5 撤页归并真接）', () => {
  it('流水/聚合 Segmented 切换 → 端点 8 真接（默认 caller+30d）＋caller 人话标签＋unattributed 桶＋期间合计行', async () => {
    const calls = apiRouter()
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('记账流水（2）'))
    await screen.findByText('call-8c31')

    fireEvent.click(screen.getByText('聚合'))
    await waitFor(() => expect(calls.stats.length).toBeGreaterThanOrEqual(1))
    const statsUrl = calls.stats[0]
    expect(statsUrl).toContain('group_by=caller')
    expect(statsUrl).toContain('range=30d')
    expect(statsUrl).toContain('pageSize=15')

    // caller 维度行：人话标签＋mono 原值＋存量 unattributed 桶
    expect(await screen.findByText('问一问 · 检索问答')).toBeTruthy()
    expect(screen.getByText('chat.retrieval.answer')).toBeTruthy()
    expect(screen.getByText('未归因（存量流水）')).toBeTruthy()
    // 期间合计＝sums（窗口全量，不随分页截断——前端拼装展示串）
    expect(await screen.findByText(/期间合计：15 次调用 · 故障切换 2 次 · 花费 ¥0\.0359/)).toBeTruthy()
  })

  it('维度切到按日趋势 → 重拉 group_by=day＋趋势列渲染（时序升序行）', async () => {
    const calls = apiRouter({ stats: u => (String(u).includes('group_by=day') ? json(200, SPEND_STATS_DAY) : json(200, SPEND_STATS)) })
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('记账流水（2）'))
    await screen.findByText('call-8c31')
    fireEvent.click(screen.getByText('聚合'))
    await screen.findByText('问一问 · 检索问答')

    fireEvent.mouseDown(screen.getByText('按调用方'))
    fireEvent.click(await screen.findByText('按日趋势'))
    await waitFor(() => {
      const last = calls.stats[calls.stats.length - 1]
      expect(last).toContain('group_by=day')
    })
    expect(await screen.findByText('2026-09-27')).toBeTruthy()  // 时序升序首行
    expect(screen.getByText('2026-09-28')).toBeTruthy()
    expect(screen.getByText('趋势')).toBeTruthy()               // day 维度趋势列在场
  })

  it('聚合拉取失败（500）→ 内联 Alert 常驻（失败态≠空态）', async () => {
    apiRouter({ stats: () => json(500, { code: 'gateway_internal', message: '聚合读取失败', trace_id: 'call-agg0' }) })
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('记账流水（2）'))
    await screen.findByText('call-8c31')
    fireEvent.click(screen.getByText('聚合'))
    expect(await screen.findByText(/花费聚合拉取失败——下表不是最新数据/)).toBeTruthy()
    expect(screen.getByText(/聚合读取失败 · code gateway_internal · trace call-agg0/)).toBeTruthy()
    expect(screen.queryByText(/期间合计：/)).toBeNull()  // 失败态不显示 sums
    expect(screen.getByText('聚合拉取失败')).toBeTruthy() // UI-06 T2：表内错误空态（errorEmptyText）
  })
})

describe('D1 落地页 · 配置读写（端点 2/3 v0.2：参数六件——含预算双阈值）', () => {
  it('编辑参数 → dirty → 保存 PUT snake_case（六件）→ 服务端快照回显＋热加载提示', async () => {
    apiRouter()
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('调用参数（6）'))

    // 初始：保存禁用（无更改）；yaml 为服务端全文；预算双阈值字段在场
    const saveBtn = await screen.findByRole('button', { name: /保存设置/ })
    expect(saveBtn.disabled).toBe(true)
    expect(await screen.findByText(/allowed_fails: 2/)).toBeTruthy()
    expect(screen.getByText('单次调用成本上限（元 · 默认 ¥0.05）')).toBeTruthy()
    expect(screen.getByText('累计预算 GATEWAY_BUDGET（元/月）')).toBeTruthy()

    // 改第一格 allowedFails 2 → 5
    const firstInput = screen.getAllByRole('spinbutton')[0]
    fireEvent.change(firstInput, { target: { value: '5' } })
    expect(await screen.findByText('有未保存的更改')).toBeTruthy()
    expect(screen.getByRole('button', { name: /保存设置/ }).disabled).toBe(false)

    fireEvent.click(screen.getByRole('button', { name: /保存设置/ }))
    await screen.findByText(/已保存 · 配置写回网关并热加载，全平台生效/)
    expect(await screen.findByText(/allowed_fails: 5/)).toBeTruthy() // PUT 后回显（服务端回值）

    const putCall = fetchMock.mock.calls.find(c => String(c[0]).includes('/api/gateway/config') && c[1]?.method === 'PUT')
    expect(putCall).toBeTruthy()
    expect(JSON.parse(putCall[1].body)).toEqual({
      params: {
        allowed_fails: 5, cooldown_seconds: 60, num_retries: 3, request_timeout: 30,
        per_call_cost_limit_yuan: 0.05, gateway_budget_yuan_per_month: 800
      }
    })
    // 保存后 dirty 清零 → 按钮复归禁用
    expect(screen.getByRole('button', { name: /保存设置/ }).disabled).toBe(true)
  })

  it('保存失败（500 热加载失败）→ 内联错误常驻（需回滚提示语义）', async () => {
    // 注：antd InputNumber 对越界输入不触发 onChange（blur 即钳回区间）——
    // 400 越界是 API 直调路径，UI 可达的保存失败面是 500 写回/热加载失败。
    apiRouter({ putConfig: () => json(500, {
      code: 'gateway_config_write_failed', message: '配置写回失败：热加载失败（yaml 解析错误）',
      trace_id: 'call-err1'
    }) })
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('调用参数（6）'))
    await screen.findByRole('button', { name: /保存设置/ })

    fireEvent.change(screen.getAllByRole('spinbutton')[0], { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: /保存设置/ }))
    expect(await screen.findByText(/保存失败——配置未生效/)).toBeTruthy()
    // errText 拼装行：人话 message＋code＋trace 三段一体
    expect(screen.getByText(/配置写回失败：热加载失败（yaml 解析错误） · code gateway_config_write_failed · trace call-err1/)).toBeTruthy()
    // 失败后可编辑重试：dirty 提示仍在、保存可再点
    expect(screen.getByText('有未保存的更改')).toBeTruthy()
    expect(screen.getByRole('button', { name: /保存设置/ }).disabled).toBe(false)
  })
})

describe('D1 落地页 · 失败态内联（P0-07 审查 P3：失败态≠空态）', () => {
  it('配置拉取失败（GET config 500）→ 调用参数页签内联 Alert 常驻（不伪装成空态）', async () => {
    apiRouter({ getConfig: () => json(500, { code: 'gateway_internal', message: '配置读取失败', trace_id: 'call-cfg0' }) })
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('调用参数（6）'))
    expect(await screen.findByText(/配置加载失败——调用参数暂不可编辑/)).toBeTruthy()
    // errText 拼装行：人话 message＋code＋trace 三段一体（对齐 models/保存错误路径）
    expect(screen.getByText(/配置读取失败 · code gateway_internal · trace call-cfg0/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /保存设置/ })).toBeNull() // 失败态无表单可编辑
  })

  it('流水拉取失败（500）→ 内联 Alert＋表内空态改「流水拉取失败」，不再伪装「没有匹配的调用记录」', async () => {
    apiRouter({ spend: () => json(500, { code: 'gateway_internal', message: '账本读取失败', trace_id: 'call-led0' }) })
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('记账流水（0）'))
    expect(await screen.findByText(/记账流水拉取失败——下表不是最新数据/)).toBeTruthy()
    expect(screen.getByText(/账本读取失败 · code gateway_internal · trace call-led0/)).toBeTruthy()
    expect(screen.queryByText('没有匹配的调用记录')).toBeNull()
    expect(screen.getByText('流水拉取失败')).toBeTruthy()
  })
})

describe('D1 落地页 · 故障演练（端点 5/6/7）', () => {
  it('允许演练开关默认关；409 重入兜底：受理被拒 → 内联提示＋开始按钮禁用', async () => {
    apiRouter({ start: () => json(409, { code: 'gateway_drill_conflict', message: '已有进行中的演练任务（重入 409）' }) })
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('故障演练（1）'))

    // 行为规则 2：破坏性操作开关默认关——关着时开始按钮禁用
    const startBtn = await screen.findByRole('button', { name: /开始故障演练/ })
    expect(startBtn.disabled).toBe(true)

    fireEvent.click(screen.getByRole('switch'))
    expect(screen.getByRole('button', { name: /开始故障演练/ }).disabled).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: /开始故障演练/ }))

    expect(await screen.findByText(/已有演练进行中（网关返回 409）/)).toBeTruthy()
    expect(screen.getByText(/code gateway_drill_conflict/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /开始故障演练/ }).disabled).toBe(true)
  })

  it('全链路：202 受理 → 轮询 running→done → 结论＋切换留痕＋落账行＋历史与流水刷新', async () => {
    let drillPoll = 0
    const calls = apiRouter({
      drill: () => {
        drillPoll += 1
        return drillPoll === 1 ? json(200, DRILL_RUNNING) : json(200, DRILL_DONE)
      }
    })
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('故障演练（1）'))
    await screen.findByRole('button', { name: /开始故障演练/ })
    fireEvent.click(screen.getByRole('switch'))
    fireEvent.click(screen.getByRole('button', { name: /开始故障演练/ }))

    // POST /drills 202 受理
    await waitFor(() => {
      expect(fetchMock.mock.calls.some(c =>
        String(c[0]).endsWith('/api/gateway/drills') && c[1]?.method === 'POST')).toBe(true)
    })

    // 轮询（300ms 节奏，真 useTaskPolling 链路）→ done 收场
    expect(await screen.findByText(/主用停机期间备用应答正常/, {}, { timeout: 4000 })).toBeTruthy()
    expect(await screen.findByText(/fallback_triggered/)).toBeTruthy() // 切换结构化日志原样展示
    expect(screen.getByText(/call-8c33/)).toBeTruthy()                  // 落账行（done 落两笔账之第一笔）
    expect(screen.getAllByText(/¥0\.0038/).length).toBeGreaterThanOrEqual(1) // 落账行（同额数字亦在节点 note 里）

    // done 后刷新演练历史＋流水回第一页（服务端刚落一条流水）
    await waitFor(() => {
      const lastSpend = fetchMock.mock.calls.filter(c => String(c[0]).includes('/api/gateway/spend-logs')).pop()
      expect(lastSpend[0]).toContain('page=1')
    })
    expect(calls.drills).toBeGreaterThanOrEqual(2) // 初始一次＋done 后刷新一次
    expect(drillPoll).toBeGreaterThanOrEqual(2)    // 至少 running 一拍＋done 一拍
    // 执行中提示退场
    await waitFor(() => expect(screen.queryByText('演练执行中…')).toBeNull())
  }, 15000)

  it('进行中快照可见：轮询未收场时 Steps 展示节点与「演练执行中…」', async () => {
    apiRouter({ drill: () => json(200, DRILL_RUNNING) }) // 恒 running（只看进行中渲染即收）
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('故障演练（1）'))
    await screen.findByRole('button', { name: /开始故障演练/ })
    fireEvent.click(screen.getByRole('switch'))
    fireEvent.click(screen.getByRole('button', { name: /开始故障演练/ }))

    expect(await screen.findByText('演练执行中…', {}, { timeout: 4000 })).toBeTruthy()
    expect(await screen.findByText(/第 1 次调用失败（注入）/)).toBeTruthy()
    // 进行中禁止再次发起（重入兜底的前端面）
    expect(screen.getByRole('button', { name: /开始故障演练/ }).disabled).toBe(true)
  }, 15000)
})

describe('D1 落地页 · UI-06 交互优化（阶段 1：PagedTable 接线／防抖／收束／联调）', () => {
  it('T3 模型线路表接 PagedTable：单页也显示分页条＋「共 N 条」（items.length 合法读法）', async () => {
    apiRouter()
    render(<D1Landing />)
    expect(await screen.findByText('petro-main')).toBeTruthy()
    expect(screen.getByText('共 2 条')).toBeTruthy() // models.length=2（端点 1 信封无 total）
  })

  it('T2 聚合表接 PagedTable client：分页条＋「共 3 条」恒显；「期间合计」行保留正文', async () => {
    apiRouter()
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('记账流水（2）'))
    await screen.findByText('call-8c31')
    fireEvent.click(screen.getByText('聚合'))
    expect(await screen.findByText('问一问 · 检索问答')).toBeTruthy()
    expect(screen.getByText('共 3 条')).toBeTruthy() // client 模式 dataSource.length（分页条统计恒显）
    expect(screen.getByTestId('agg-sums')).toBeTruthy() // 期间合计行（关键合计不收束）
  })

  it('T2 resetKey=groupBy|range：翻到第 2 页后切窗口自动回页 1', async () => {
    const calls = apiRouter({ stats: u => (String(u).includes('group_by=caller') ? json(200, SPEND_STATS_MANY) : json(200, SPEND_STATS)) })
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('记账流水（2）'))
    await screen.findByText('call-8c31')
    fireEvent.click(screen.getByText('聚合'))
    expect(await screen.findByText('共 21 条')).toBeTruthy()
    const page2 = document.querySelector('.ant-pagination-item-2')
    expect(page2).toBeTruthy() // 21 行 / pageSize 20 → 两页
    fireEvent.click(page2)
    expect(await screen.findByText('chat.bulk.20')).toBeTruthy() // 第 21 行（首页 20 行之外）
    fireEvent.click(screen.getByText('全部')) // range 变化 → resetKey 变化
    expect(await screen.findByText('chat.bulk.0')).toBeTruthy() // 回页 1：首页首行复现
    expect(document.querySelector('.ant-pagination-item-1').className).toContain('ant-pagination-item-active')
    await waitFor(() => expect(calls.stats[calls.stats.length - 1]).toContain('range=all'))
  })

  it('T4 演练日志拉取失败：内联 Alert＋错误空态「演练记录拉取失败」，不出现「暂无演练记录」假空态', async () => {
    apiRouter({ drills: () => json(500, { code: 'gateway_internal', message: '演练历史读取失败', trace_id: 'call-drl0' }) })
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('故障演练（0）'))
    expect(await screen.findByText('演练记录拉取失败——下表不是最新数据')).toBeTruthy()
    expect(screen.getByText(/演练历史读取失败 · code gateway_internal · trace call-drl0/)).toBeTruthy()
    expect(screen.getByText('演练记录拉取失败')).toBeTruthy() // 表内错误空态（errorEmptyText）
    expect(screen.queryByText('暂无演练记录')).toBeNull()
  })

  it('T4 演练日志加载中出 loading；装载完成渲染行＋分页条＋时间含年', async () => {
    let release
    apiRouter({ drills: () => new Promise(resolve => { release = resolve }) })
    const { container } = render(<D1Landing />)
    fireEvent.click(await screen.findByText('故障演练（0）'))
    expect(container.querySelector('.ant-table-wrapper .ant-spin-spinning')).toBeTruthy() // 表 loading
    release(json(200, DRILLS_HISTORY))
    expect(await screen.findByText(/演练：主用连续失败 2 次/)).toBeTruthy()
    expect(screen.getByText('共 1 条')).toBeTruthy() // drillLogs.length（端点 7 裸数组合法读法）
    expect(screen.getByText('2026-09-28 09:12')).toBeTruthy() // T8：时间列含年（fmtTime 单点）
  })

  it('T5 流水关键词 300ms 防抖：击键只动本地态，静止后并入 query（携 page=1）', async () => {
    const calls = apiRouter()
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('记账流水（2）'))
    const input = await screen.findByPlaceholderText('搜调用号 / 备注…')
    const before = calls.spend
    vi.useFakeTimers()
    try {
      fireEvent.change(input, { target: { value: 'call' } })
      fireEvent.change(input, { target: { value: 'call-8' } })
      fireEvent.change(input, { target: { value: 'call-8c' } })
      vi.advanceTimersByTime(299) // 防抖窗内：零请求
      expect(calls.spend).toBe(before)
      await act(async () => { await vi.advanceTimersByTimeAsync(1) }) // 300ms 静止 → 并入 query
    } finally {
      vi.useRealTimers()
    }
    expect(calls.spend).toBe(before + 1) // 三连击键只发一次请求
    const last = fetchMock.mock.calls.filter(c => String(c[0]).includes('/api/gateway/spend-logs')).pop()
    expect(last[0]).toContain('keyword=call-8c')
    expect(last[0]).toContain('page=1') // 防抖并入携 page:1（对齐三筛控件归页语义）
  })

  it('T6 「适用范围」行收束进页头 helpTop：正文行消失、? 悬停可见内容', async () => {
    apiRouter()
    render(<D1Landing />)
    expect(await screen.findByText('petro-main')).toBeTruthy()
    expect(screen.queryByText('适用范围')).toBeNull() // 正文行不再直出
    const subtitle = screen.getByText(/平台所有模型调用的唯一出口/)
    const q = subtitle.closest('div').querySelector('.anticon-question-circle')
    expect(q).toBeTruthy() // 页头 helpTop 在场（副标题旁 ?）
    fireEvent.mouseEnter(q)
    expect(await screen.findByText(/问一问、报告库回答、问数/)).toBeTruthy() // 内容原话迁入
  })

  it('T7 流水表 scroll.x 联调降至 ≤1000：1280 视口可用宽（≈976）内无恒显横滚', async () => {
    apiRouter()
    const { container } = render(<D1Landing />)
    fireEvent.click(await screen.findByText('记账流水（2）'))
    await screen.findByText('call-8c31')
    const table = container.querySelector('.ant-table-content table')
    expect(table).toBeTruthy()
    expect(table.style.width).toBeTruthy()
    expect(Number.parseFloat(table.style.width)).toBeLessThanOrEqual(1000)
  })
})

describe('D1 落地页 · UI-06 T9 复制降级', () => {
  const realExec = document.execCommand // jsdom 未实现 execCommand（undefined）——直接赋桩、 afterEach 还原

  afterEach(() => {
    document.execCommand = realExec
    Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true })
  })

  it('无 clipboard 环境降级 textarea＋execCommand——成功仍有「已复制」反馈', async () => {
    apiRouter()
    const execSpy = vi.fn(() => true)
    document.execCommand = execSpy
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('调用参数（6）'))
    fireEvent.click(await screen.findByRole('button', { name: /复制/ }))
    expect(await screen.findByText('已复制')).toBeTruthy()
    expect(execSpy).toHaveBeenCalledWith('copy')
  })

  it('降级复制失败（execCommand false）——message.error「复制失败，请手动选择文本复制」', async () => {
    apiRouter()
    document.execCommand = vi.fn(() => false)
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('调用参数（6）'))
    fireEvent.click(await screen.findByRole('button', { name: /复制/ }))
    expect(await screen.findByText('复制失败，请手动选择文本复制')).toBeTruthy()
  })

  it('clipboard 可用路径维持现状——writeText 成功出「已复制」', async () => {
    apiRouter()
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('调用参数（6）'))
    fireEvent.click(await screen.findByRole('button', { name: /复制/ }))
    expect(await screen.findByText('已复制')).toBeTruthy()
    expect(writeText).toHaveBeenCalledTimes(1)
  })
})
