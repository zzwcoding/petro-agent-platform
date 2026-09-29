/**
 * 落地 D1 页组件测试（P0-07）——fetch 级 mock（apiRouter 挡在 window.fetch 边界），
 * client/gateway 接口层与页面全部真代码：
 * - 渲染：页头徽标＋模型表＋四页签（端点 1 形状）；
 * - 错误包展示路径：models 拉取失败 → 内联 Alert（message/code/trace_id）；
 * - 配置读写：表单编辑 → PUT body snake_case → 服务端快照回显（端点 2/3）；
 * - 409 重入兜底：受理拒绝 → 内联提示＋按钮禁用（端点 5）；
 * - 演练轮询收场：202 → useTaskPolling running→done → 结论/切换留痕/历史与流水
 *   刷新（端点 5/6/7 全链路）。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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
  params: { allowed_fails: 2, cooldown_seconds: 60, num_retries: 3, request_timeout: 30 },
  yaml: '# models.yaml（夹具全文）\ngateway:\n  allowed_fails: 2\n  num_retries: 3\n'
}
const CONFIG_SAVED = {
  params: { allowed_fails: 5, cooldown_seconds: 60, num_retries: 3, request_timeout: 30 },
  yaml: '# models.yaml（夹具全文·保存后）\ngateway:\n  allowed_fails: 5\n  num_retries: 3\n'
}
const SPEND = {
  items: [
    { id: 'call-8c31', time: '2026-09-28T09:52:30', model_key: 'main', alias: 'petro-main',
      input_tokens: 2140, output_tokens: 1380, first_ms: 1000, total_ms: 4000, cost_yuan: 0.007,
      fallback: false, note: '' },
    { id: 'call-8c32', time: '2026-09-28T10:00:00', model_key: 'backup', alias: 'petro-lite',
      input_tokens: 1010, output_tokens: 590, first_ms: 1300, total_ms: 3800, cost_yuan: 0.0038,
      fallback: true, note: '故障自动切换：请求别名 petro-main → 备用 petro-lite 应答' }
  ],
  total: 2, page: 1, page_size: 15
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
      fallback: true, note: '故障自动切换'
    }
  }
}

const json = (status, body) => ({ ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) })

/**
 * fetch 级 mock 路由（/api/gateway/* 七端点；overrides 按 URL 注入行为/错误）。
 */
function apiRouter(overrides = {}) {
  const calls = { spend: 0, drills: 0, drillGet: 0, post: 0 }
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
    expect(screen.getByText('调用参数（4）')).toBeTruthy()

    // client 底座：X-Dev-User 身份桩注入
    const modelsCall = fetchMock.mock.calls.find(c => String(c[0]).includes('/api/gateway/models'))
    expect(modelsCall[1].headers['X-Dev-User']).toBe('aqiang')
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

    // query 组装：model/range/keyword/page/pageSize（pageSize 别名合同保留 camel）
    const spendUrl = fetchMock.mock.calls.find(c => String(c[0]).includes('/api/gateway/spend-logs'))[0]
    expect(spendUrl).toContain('page=1')
    expect(spendUrl).toContain('pageSize=15')

    // 行点击 → 抽屉（明细用行内真值 alias）
    fireEvent.click(screen.getByText('call-8c31'))
    expect(await screen.findByText('调用别名')).toBeTruthy()
    expect(await screen.findByText('petro-main')).toBeTruthy()
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

describe('D1 落地页 · 配置读写（端点 2/3：表单对应「文件里的一行」）', () => {
  it('编辑参数 → dirty → 保存 PUT snake_case → 服务端快照回显＋热加载提示', async () => {
    apiRouter()
    render(<D1Landing />)
    fireEvent.click(await screen.findByText('调用参数（4）'))

    // 初始：保存禁用（无更改）；yaml 为服务端全文
    const saveBtn = await screen.findByRole('button', { name: /保存设置/ })
    expect(saveBtn.disabled).toBe(true)
    expect(await screen.findByText(/allowed_fails: 2/)).toBeTruthy()

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
      params: { allowed_fails: 5, cooldown_seconds: 60, num_retries: 3, request_timeout: 30 }
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
    fireEvent.click(await screen.findByText('调用参数（4）'))
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
