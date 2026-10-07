/**
 * 落地 B1 页组件测试（P1-03）——fetch 级 mock（apiRouter 挡在 window.fetch 边界），
 * client/kb 接口层与页面全部真代码（含 useTaskPolling 真轮询、直传 raw PUT）：
 * - 渲染：三页签台账/任务/库（端点 1/7/11 形状，入库中 Tag 直出）；
 * - 错误包展示路径：reports 拉取失败 → 内联 Alert（message/code/trace_id）；
 * - 上传两拍＋建议确认：受理（端点 5 带 LLM 建议卡）→ 客户端 PUT 直传对象存储
 *   （raw fetch 非 /api 边界）→ confirm（端点 6 带确认 lib_id）；
 * - 建议新建库路径（mode=new → 建库端点 15 → confirm 带新库号）＋409 重名兜底；
 * - 库停用/启用（端点 13 可选 status）；
 * - 任务五步轮询终态（端点 8 真轮询→done→产物端点 9 两卡）＋failed stop_at 人话＋重试（端点 10）；
 * - 切块自检告警进真实任务卡（FX-05/R1-14：端点 8 branches.chunk_check——violations>0
 *   显示「切块自检 N 条违规 · 证据：路径」，零违规无键不显示）；
 * - 来源筛（端点 7 source 筛参）；片段修正乐观锁 409 兜底（端点 4）。
 * - UI-02（阶段 1 交互优化）：四表 PagedTable 分页/resetKey、统计读信封 total、
 *   活动流失败态分立、禁用按钮 span 包裹 Tooltip、抽屉/弹窗加载态、卡底指引收 ?、
 *   弹窗重复说明删除、「任务 N 条」双显收敛、活动流 rowKey 复合。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import B1Landing from './B1.jsx'

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

// ── 合同形状夹具（后端 R1 snake_case，同 app/api/kb.py 响应模型） ──

const LIBS_LIST = {
  items: [
    { id: 'lib-1', name: '完井报告库', biz_template: 'completion', status: 'active',
      last_ingestion: { doc: '《N-02 井完井报告（英文 · 200 页）》',
        switches: { semantic: true, keyword: true, wiki: true, graph: true } },
      annotations: {} },
    { id: 'lib-2', name: '生产月报库', biz_template: 'monthly', status: 'active',
      last_ingestion: { doc: '《渤中28-1 区块月度生产月报（2026-08）》',
        switches: { semantic: true, keyword: true, wiki: true, graph: false } },
      annotations: {} }
  ],
  total: 2
}
const REPORTS = {
  items: [
    { id: 'rpt-1', doc: '《N-02 井完井报告（英文 · 200 页）》', lib_id: 'lib-1', lib: '完井报告库',
      refs: 5, wiki: 'v1', status: '已入库' },
    { id: 'rpt-2', doc: '《渤中28-1 区块月度生产月报（2026-08）》', lib_id: 'lib-2', lib: '生产月报库',
      refs: null, wiki: null, status: '入库中' }
  ],
  total: 2
}
const REPORT_DETAIL = {
  id: 'rpt-1', doc: '《N-02 井完井报告（英文 · 200 页）》', lib_id: 'lib-1', lib: '完井报告库',
  subject: '井号 N-02', refs: 5, wiki: 'v1', status: '已入库',
  related_objects: [{ type: 'well', id: 'N-02' }],
  fragments: [
    { id: 'f1', type: '原文块', path: '章节 01 井基本情况 ＞ 1.2 投产信息',
      text: 'N-02（渤中28-1-N2）于 2019-06-15 投产。', version: 1,
      versions: [{ v: 1, text: 'N-02（渤中28-1-N2）于 2019-06-15 投产。', note: '原始解析' }] }
  ]
}
const TASKS = {
  items: [
    { id: 'task-1', doc: '《演示报告》', lib_id: 'lib-1', lib_name: '完井报告库', source: '上传入库',
      state: 'running', current_step: 1, stop_at: null, reason: null },
    { id: 'task-2', doc: '《N-11 井完井报告（英文 · 200 页）》', lib_id: 'lib-1', lib_name: '完井报告库',
      source: '上传入库', state: 'failed', current_step: 1, stop_at: '切段', reason: '扫描件某页图像质量差，无法识别' }
  ],
  total: 2
}
const TASK_RUNNING = {
  id: 'task-1', state: 'running', source: '上传入库', current_step: 1, stop_at: null, reason: null,
  nodes: [
    { key: 'parse', label: '解析（读出文字和图）', state: 'finish', note: '读出正文和插图；报告原文原样存进文件库（桶：报告原文）。' },
    { key: 'chunk', label: '切段', state: 'process', note: '切段方式：智能切段——按章节和语义边界切。' },
    { key: 'embed', label: '向量化', state: 'wait', note: null },
    { key: 'index', label: '建索引', state: 'wait', note: null },
    { key: 'enrich', label: '索引期加法（摘要＋问题）', state: 'wait', note: null }
  ],
  config_snapshot: { semantic: true, keyword: true, wiki: true, graph: true, mode: 'smart', add_summary: true, add_questions: true }
}
const TASK_DONE = {
  ...TASK_RUNNING,
  state: 'done', current_step: 4,
  nodes: TASK_RUNNING.nodes.map(n => ({ ...n, state: 'finish' }))
}
const ADDITIONS = {
  task_id: 'task-1', doc: '《演示报告》',
  summary: { type: '摘要块', title: '全文档摘要（自动生成）', text: '本报告为 N-02 井完井报告（演示）。' },
  questions: { type: '问题块', title: '这份报告可能被问的 10 个问题（自动生成）', items: ['N-02 井是什么时候投产的？'] }
}
const RETRY_SNAP = { ...TASK_RUNNING, source: '重跑定型', current_step: 0 }
const UPLOAD_RECEIPT = {
  upload_id: 'up-1', lib_id: 'lib-2', lib_name: '生产月报库',
  dup_warning: '检测到疑似重复，仍要上传？已有同名报告《演示报告》。',
  put_url: 'http://minio.test:9000/reports/up-1/demo.txt?X-Amz-Signature=abc',
  expires_at: '2026-10-01 15:30', bucket: '报告原文',
  routing: { mode: 'existing', topic: '月报', lib_id: 'lib-2', lib_name: '生产月报库',
    template: null, reason: '文件名含「月报」，与生产月报库话题一致', confidence: 0.86 }
}
const UPLOAD_NEW_RECEIPT = {
  ...UPLOAD_RECEIPT,
  upload_id: 'up-2', lib_id: null, lib_name: null, dup_warning: null,
  routing: { mode: 'new', topic: '措施效果', lib_id: null, lib_name: null,
    template: 'monthly', reason: '现有库都不匹配，建议新建', confidence: 0.42 }
}
const CONFIRM = {
  task_id: 'task-9', upload_id: 'up-1', doc: '《demo》', lib_id: 'lib-2', lib_name: '生产月报库',
  source: '上传入库', state: 'running', current_step: 0,
  config_snapshot: { semantic: true, keyword: true, wiki: true, graph: false, mode: 'smart', add_summary: true, add_questions: true }
}
const LIB_CONFIG = {
  id: 'lib-1', name: '完井报告库',
  switches: { semantic: true, keyword: true, wiki: true, graph: true },
  mode: 'smart', add_summary: true, add_questions: true,
  saved_at: '2026-09-25 10:12', saved_by: '阿强 · 平台运维'
}
const LIB_SAVE = {
  id: 'lib-1', saved_at: '2026-10-01 10:40', saved_by: '阿强 · 平台运维', status: 'active',
  hint: '已保存——开关在下次入库时生效，正在处理的报告不受影响。',
  activity_row: { time: '2026-10-01 10:40', who: '阿强 · 平台运维', action: '修改库配置', target: '完井报告库 · 切段方式：智能切段（256–1024 字）' }
}
const LIB_DISABLED_SAVE = { ...LIB_SAVE, status: 'disabled' }
const ACTIVITIES = {
  items: [{ time: '2026-09-26 16:48', who: '小李 · 地质/质检', action: '上传报告', target: '《N-02 井完井报告（英文 · 200 页）》' }],
  total: 1
}
const CREATED_LIB = {
  lib_id: 'lib-9', lib_name: '措施效果库', biz_template: 'monthly', status: 'active',
  config: { switches: { semantic: true, keyword: true, wiki: true, graph: false }, mode: 'smart', add_summary: true, add_questions: true },
  activity_row: { time: '2026-10-01 10:30', who: '阿强 · 平台运维', action: '新建库', target: '措施效果库 · 业务模板：生产月报类（默认配置已生成）' }
}

const json = (status, body) => ({ ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) })

/** fetch 级 mock 路由（/api/kb/* 十五端点＋MinIO 直传边界；overrides 按 URL 注入行为/错误）。 */
function apiRouter(overrides = {}) {
  const calls = { uploads: 0, confirm: 0, putDirect: 0, retry: 0, configPut: [], createLib: [] }
  fetchMock.mockImplementation(async (url, init) => {
    const u = String(url)
    const method = init?.method || 'GET'
    if (u.includes('minio.test:9000')) {
      calls.putDirect += 1
      return overrides.putDirect ? overrides.putDirect() : json(200, '')
    }
    if (u.includes('/api/kb/reports') && !u.includes('/api/kb/reports/')) {
      return overrides.reports ? overrides.reports() : json(200, REPORTS)
    }
    if (/\/api\/kb\/reports\/[^/]+\/fragments\/[^/]+\/revisions$/.test(u)) {
      return overrides.revise ? overrides.revise() : json(200, { id: 'f1', version: 2, versions: [], rebuild: { triggered: true, hint: '已保存——将重建检索索引。' }, activity_row: ACTIVITIES.items[0], task_id: 'task-8' })
    }
    if (/\/api\/kb\/reports\/[^/]+\/download-url$/.test(u)) {
      return overrides.download ? overrides.download() : json(200, { id: 'rpt-1', download_url: 'http://minio.test:9000/get/1', expires_at: '2026-10-01 16:00', ttl: '小时级' })
    }
    if (/\/api\/kb\/reports\/[^/]+$/.test(u)) {
      return overrides.detail ? overrides.detail() : json(200, REPORT_DETAIL)
    }
    if (/\/api\/kb\/uploads\/[^/]+\/confirm$/.test(u)) {
      calls.confirm += 1
      calls.confirmBody = init?.body
      return overrides.confirm ? overrides.confirm() : json(200, CONFIRM)
    }
    if (u.endsWith('/api/kb/uploads')) {
      calls.uploads += 1
      return overrides.upload ? overrides.upload() : json(200, UPLOAD_RECEIPT)
    }
    if (/\/api\/kb\/tasks\/[^/]+\/additions$/.test(u)) {
      return overrides.additions ? overrides.additions() : json(200, ADDITIONS)
    }
    if (/\/api\/kb\/tasks\/[^/]+\/retry$/.test(u)) {
      calls.retry += 1
      return overrides.retry ? overrides.retry() : json(200, RETRY_SNAP)
    }
    if (/\/api\/kb\/tasks\/[^/]+$/.test(u)) {
      // 覆盖函数可按 URL 分派返回体（FX-05 切块告警例按任务号区分 branches 有无）
      return overrides.task ? overrides.task(u) : json(200, TASK_RUNNING)
    }
    if (u.includes('/api/kb/tasks')) {
      return overrides.tasks ? overrides.tasks() : json(200, TASKS)
    }
    if (/\/api\/kb\/libs\/[^/]+\/config$/.test(u)) {
      if (method === 'PUT') {
        calls.configPut.push(JSON.parse(init.body))
        return overrides.putConfig ? overrides.putConfig(init) : json(200, LIB_SAVE)
      }
      return overrides.getConfig ? overrides.getConfig() : json(200, LIB_CONFIG)
    }
    if (/\/api\/kb\/libs\/[^/]+\/activities$/.test(u)) {
      return overrides.activities ? overrides.activities() : json(200, ACTIVITIES)
    }
    if (/\/api\/kb\/libs(\?|$)/.test(u)) {
      if (method === 'POST') {
        calls.createLib.push(init?.body ? JSON.parse(init.body) : null)
        return overrides.createLib ? overrides.createLib() : json(201, CREATED_LIB)
      }
      return overrides.libs ? overrides.libs() : json(200, LIBS_LIST)
    }
    return json(404, { code: 'test_unrouted', message: `unexpected ${method} ${u}` })
  })
  return calls
}

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  window.open = vi.fn()
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

/** 选一个文件触发受理（hidden file input）。 */
function pickDemoFile() {
  const file = new File(['N-02 井完井报告演示文本'], 'demo.txt', { type: 'text/plain' })
  const input = document.querySelector('input[type="file"]')
  fireEvent.change(input, { target: { files: [file] } })
  return file
}

describe('B1 落地页 · 渲染（端点 1/7/11）', () => {
  it('三页签渲染：台账两行（入库中 Tag）＋任务计数＋库开关快照 Tag', async () => {
    apiRouter()
    render(<B1Landing />)

    expect(await screen.findByText('报告台账（2）')).toBeTruthy()
    expect(await screen.findByText('入库任务（2）')).toBeTruthy()
    expect(await screen.findByText('库管理（2）')).toBeTruthy()
    expect(screen.getByText('《N-02 井完井报告（英文 · 200 页）》')).toBeTruthy()
    expect(screen.getByText('入库中')).toBeTruthy()          // 端点 1 status 直出
    expect(screen.getByText('5 段')).toBeTruthy()
    expect(screen.getByText('v1')).toBeTruthy()
    expect(await screen.findByText('共 2 条')).toBeTruthy() // UI-02 T1 PagedTable 分页条统计（单页恒显）
    // 库管理页签：开关快照 Tag（端点 11 last_ingestion.switches）
    fireEvent.click(await screen.findByText(/库管理（\d+）/))
    expect((await screen.findAllByText('语义 ✓')).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('关系图谱 ✗').length).toBeGreaterThanOrEqual(1)
    expect(await screen.findByText('筛选结果 2 条')).toBeTruthy() // UI-02 T2 计数读信封 total
    expect(await screen.findByText('共 2 条')).toBeTruthy()      // UI-02 T1 库管理表分页条统计
    // 身份桩注入
    const call = fetchMock.mock.calls.find(c => String(c[0]).includes('/api/kb/reports'))
    expect(call[1].headers['X-Dev-User']).toBe('aqiang')
  })

  it('错误包展示路径：reports 拉取 500 → 内联 Alert 带 message/code/trace（失败态≠空态）', async () => {
    apiRouter({ reports: () => json(500, { code: 'kb_internal', message: '台账读取失败', trace_id: 'call-r0' }) })
    render(<B1Landing />)
    expect(await screen.findByText('报告台账拉取失败——下表不是最新数据')).toBeTruthy()
    expect(screen.getByText(/台账读取失败 · code kb_internal · trace call-r0/)).toBeTruthy()
    expect(screen.getByText('台账拉取失败')).toBeTruthy() // 表内空态也换失败文案
  })
})

describe('B1 落地页 · 上传两拍＋入库路由（端点 5/6/15）', () => {
  it('全链路：受理带 LLM 建议卡（理由＋置信度）＋dup_warning 非阻断 → PUT 直传对象存储 → confirm 带确认库号', async () => {
    const calls = apiRouter()
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/入库任务（\d+）/))
    fireEvent.click(await screen.findByRole('button', { name: /上传报告（直传）/ }))
    pickDemoFile()

    // 受理回执：建议卡（卡题＋建议库名＋理由＋置信度）＋重复提示（非阻断）
    expect(await screen.findByText('入库路由建议（LLM 只建议 · 由你确认）')).toBeTruthy()
    expect((await screen.findAllByText('生产月报库')).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/与生产月报库话题一致/)).toBeTruthy()
    expect(screen.getByText(/置信度：86%/)).toBeTruthy()
    expect(screen.getByText(/检测到疑似重复，仍要上传？/)).toBeTruthy()
    // UI-02 T7 上传弹窗底部机制说明已删——同义内容只在「上传报告（直传）」按钮旁 helpIcon
    expect(screen.queryByText(/确认后文件字节直传文件库/)).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '确认入库' }))

    // 两拍：PUT 字节直达对象存储（raw fetch 非 /api）＋confirm 带确认 lib_id
    await waitFor(() => expect(calls.putDirect).toBe(1))
    await waitFor(() => expect(calls.confirm).toBe(1))
    expect(JSON.parse(calls.confirmBody)).toEqual({ lib_id: 'lib-2' })
    const putUrl = fetchMock.mock.calls.find(c => String(c[0]).includes('minio.test:9000'))[0]
    expect(putUrl).toContain('X-Amz-Signature=abc')
    // confirm 后切任务页签并刷新列表（UI-02 T10：「任务 N 条」卡头计数行已删——以任务列表刷新为等待锚）
    await screen.findByText('《N-11 井完井报告（英文 · 200 页）》', {}, { timeout: 3000 })
  }, 15000)

  it('建议新建库（mode=new）：确认 → 建库端点 15 → confirm 带新库号', async () => {
    const calls = apiRouter({ upload: () => json(200, UPLOAD_NEW_RECEIPT) })
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/入库任务（\d+）/))
    fireEvent.click(await screen.findByRole('button', { name: /上传报告（直传）/ }))
    pickDemoFile()

    expect(await screen.findByText(/建议新建库/)).toBeTruthy()
    expect(screen.getByText(/模板推荐：「生产月报类」/)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '确认入库' }))
    await waitFor(() => expect(calls.createLib.length).toBe(1))
    expect(calls.createLib[0]).toEqual({ lib_name: '措施效果', biz_template: 'monthly' })
    await waitFor(() => expect(calls.confirm).toBe(1))
    expect(JSON.parse(calls.confirmBody)).toEqual({ lib_id: 'lib-9' })
  }, 15000)

  it('建库 409 重名：新建库弹窗 → 内联提示「库名与现有库重复」', async () => {
    apiRouter({ createLib: () => json(409, { code: 'kb_lib_name_duplicate', message: '库名与现有库重复：完井报告库', trace_id: 'call-d0' }) })
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/库管理（\d+）/))
    fireEvent.click(screen.getByRole('button', { name: /新建库/ }))
    fireEvent.click(screen.getByRole('button', { name: '确认建库' }))
    expect(await screen.findByText('库名与现有库重复，请换一个名称。')).toBeTruthy()
    expect(screen.getByText(/code kb_lib_name_duplicate/)).toBeTruthy()
    // UI-02 T7 新建库弹窗底部停用/启用指引已删——同义内容只在列表行 Tooltip
    expect(screen.queryByText(/建成后该库即出现在列表中/)).toBeNull()
  })

  it('来源筛变更带 source 筛参重拉（端点 7）', async () => {
    apiRouter()
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/入库任务（\d+）/))
    await screen.findByText('《演示报告》')
    fireEvent.mouseDown(await screen.findByText('来源：全部'))
    fireEvent.click(await screen.findByText('片段修正'))
    await waitFor(() => {
      const last = fetchMock.mock.calls.filter(c => String(c[0]).includes('/api/kb/tasks?')).pop()
      expect(last[0]).toContain(encodeURIComponent('片段修正'))
    })
  })
})

describe('B1 落地页 · 任务五步轮询（端点 8/9/10）', () => {
  it('轮询收场：running → done → Steps 五节点＋产物两卡（端点 9）＋台账刷新', async () => {
    let poll = 0
    let task1Done = false
    apiRouter({
      task: () => {
        poll += 1
        if (poll >= 2) task1Done = true
        return poll === 1 ? json(200, TASK_RUNNING) : json(200, TASK_DONE)
      },
      tasks: () => json(200, { ...TASKS, items: TASKS.items.map(t => (t.id === 'task-1' && task1Done ? { ...t, state: 'done', source: '上传入库' } : t)) })
    })
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/入库任务（\d+）/))
    fireEvent.click(await screen.findByText('《演示报告》')) // 行点击展开（受控展开行——新任务由上传流主动展开）

    // 真轮询（useKbTaskPolling）→ done 收场读产物
    expect(await screen.findByText(/本报告为 N-02 井完井报告（演示）。/, {}, { timeout: 6000 })).toBeTruthy()
    expect(screen.getByText('全文档摘要（自动生成）')).toBeTruthy()
    expect(screen.getByText('N-02 井是什么时候投产的？')).toBeTruthy()
    expect(poll).toBeGreaterThanOrEqual(2)
  }, 15000)

  it('failed 任务：stop_at 人话 Alert＋重试（端点 10）→ 来源转「重跑定型」', async () => {
    const calls = apiRouter()
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/入库任务（\d+）/))
    // 展开失败行看人话
    fireEvent.click(await screen.findByText('《N-11 井完井报告（英文 · 200 页）》'))
    expect(await screen.findByText(/停在「切段」阶段：扫描件某页图像质量差，无法识别——可重试；仍失败请报修。/)).toBeTruthy()
    fireEvent.click(screen.getAllByRole('button', { name: /重试/ })[0])
    await waitFor(() => expect(calls.retry).toBe(1))
  }, 15000)

  // FX-05（审查 R1-14 裁决）：切块自检告警进落地页真实任务卡——渲染形状照原型树
  // pages/B1.jsx 既有行（violations>0 显示「切块自检 N 条违规 · 证据：路径」，零违规
  // 无键不显示）。载荷取自端点 8 branches（DE-06 additive 键 chunk_check）。
  it('切块自检告警进真实任务卡：violations>0 显示违规数＋证据路径；零违规任务不显示（端点 8 branches）', async () => {
    const TASK_WARN = {
      ...TASK_RUNNING, state: 'stuck', current_step: 2,
      branches: { chunk_check: { state: 'warn', violations: 2, detail: '切块自检 2 条违规', evidence: '/tmp/chunk_validate_task-1.md' } }
    }
    apiRouter({
      tasks: () => json(200, {
        items: [
          { ...TASKS.items[0], state: 'stuck', current_step: 2,
            branches: TASK_WARN.branches }, // 端点 7 列表行同载 branches（additive 透传）
          TASKS.items[1]
        ],
        total: 2
      }),
      // 端点 8 按任务号分派：task-1 带切块违规、task-2 零违规（无 chunk_check 键）
      task: u => (u.includes('task-1') ? json(200, TASK_WARN) : json(200, TASK_RUNNING))
    })
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/入库任务（\d+）/))
    // 零违规断言在先：展开无 chunk_check 的失败任务——不出现切块自检行
    fireEvent.click(await screen.findByText('《N-11 井完井报告（英文 · 200 页）》'))
    expect(await screen.findByText(/停在「切段」阶段/)).toBeTruthy() // 展开区已渲染（端点 8 已回）
    expect(screen.queryByText(/切块自检 \d+ 条违规/)).toBeNull()
    // 违规态：展开带 chunk_check 的卡住任务——行出现且携证据文件路径
    fireEvent.click(await screen.findByText('《演示报告》'))
    expect(await screen.findByText(/切块自检 2 条违规/)).toBeTruthy()
    expect(screen.getByText(/证据：\/tmp\/chunk_validate_task-1\.md/)).toBeTruthy()
  }, 15000)
})

describe('B1 落地页 · 库管理（端点 13/14）', () => {
  it('停用库：GET 配置＋PUT status=disabled（配置全量整存整取＋可选 status）', async () => {
    const calls = apiRouter({ putConfig: () => json(200, LIB_DISABLED_SAVE) })
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/库管理（\d+）/))
    const stopBtns = screen.getAllByRole('button').filter(b => b.querySelector('.anticon-pause-circle'))
    expect(stopBtns.length).toBeGreaterThanOrEqual(1)
    fireEvent.click(stopBtns[0])
    await waitFor(() => expect(calls.configPut.length).toBe(1))
    expect(calls.configPut[0]).toEqual({
      switches: { semantic: true, keyword: true, wiki: true, graph: true },
      mode: 'smart', add_summary: true, add_questions: true, status: 'disabled'
    })
  })

  it('库配置保存：PUT 端点 13 → 服务端 hint 回显', async () => {
    const calls = apiRouter()
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/库管理（\d+）/))
    const cfgBtns = screen.getAllByRole('button').filter(b => b.querySelector('.anticon-setting'))
    fireEvent.click(cfgBtns[0])
    await screen.findByText('保存本库配置')
    fireEvent.click(screen.getByRole('button', { name: '保存本库配置' }))
    await screen.findByText('已保存——开关在下次入库时生效，正在处理的报告不受影响。')
    await waitFor(() => expect(calls.configPut.length).toBe(1))
  })

  it('活动流抽屉：库操作留痕四列（端点 14）', async () => {
    apiRouter()
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/库管理（\d+）/))
    const actBtns = screen.getAllByRole('button').filter(b => b.querySelector('.anticon-history'))
    fireEvent.click(actBtns[0])
    expect(await screen.findByText('活动 · 完井报告库')).toBeTruthy()
    expect(await screen.findByText('小李 · 地质/质检')).toBeTruthy()
  })
})

describe('B1 落地页 · 报告详情与片段修正（端点 2/4）', () => {
  it('详情抽屉（双击台账行）→ 修正保存 → 乐观锁 409 内联兜底提示', async () => {
    apiRouter({ revise: () => json(409, { code: 'kb_fragment_version_conflict', message: '片段已被他人修改（当前 v2）', trace_id: 'call-f9' }) })
    render(<B1Landing />)
    fireEvent.doubleClick(await screen.findByText('《N-02 井完井报告（英文 · 200 页）》'))
    expect(await screen.findByText('井号 N-02')).toBeTruthy()
    expect(await screen.findByText('N-02（渤中28-1-N2）于 2019-06-15 投产。')).toBeTruthy()

    fireEvent.click(screen.getAllByRole('button', { name: /修正/ })[0])
    await screen.findByText('保存修正')
    fireEvent.click(screen.getByRole('button', { name: '保存修正' }))
    expect(await screen.findByText(/这段已被别人修改过（版本冲突）/)).toBeTruthy()
    expect(screen.getByText(/code kb_fragment_version_conflict/)).toBeTruthy()
  })

  it('修正成功：hint 提示＋版本刷新＋任务列表刷新（「片段修正」来源任务）', async () => {
    apiRouter({
      revise: () => json(200, {
        id: 'f1', version: 2,
        versions: [
          { v: 1, text: 'N-02（渤中28-1-N2）于 2019-06-15 投产。', note: '原始解析' },
          { v: 2, text: 'N-02（渤中28-1-N2）于 2019-06-15 投产（勘误）。', note: '人工修正' }
        ],
        rebuild: { triggered: true, hint: '已保存——将重建检索索引。' },
        activity_row: ACTIVITIES.items[0], task_id: 'task-8'
      })
    })
    render(<B1Landing />)
    fireEvent.doubleClick(await screen.findByText('《N-02 井完井报告（英文 · 200 页）》'))
    await screen.findAllByText('修正')
    fireEvent.click(screen.getAllByRole('button', { name: /修正/ })[0])
    await screen.findByText('保存修正')
    fireEvent.click(screen.getByRole('button', { name: '保存修正' }))
    expect(await screen.findByText('已保存——将重建检索索引。')).toBeTruthy()
    await waitFor(() => {
      const last = fetchMock.mock.calls.filter(c => String(c[0]).includes('/api/kb/tasks?')).pop()
      expect(last).toBeTruthy() // 修正后任务列表刷新（片段修正任务可见）
    })
  })
})

describe('B1 落地页 · UI-02 交互优化（PagedTable/失败态/加载态/说明收束）', () => {
  it('T1 resetKey：台账翻到第 2 页后筛选缩短数据自动回页 1（不出现超界空表）', async () => {
    let filtered = false
    const rows = n => ({
      items: Array.from({ length: n }, (_, i) => ({
        id: `rpt-${i + 1}`, doc: `《压舱报告 ${i + 1}》`, lib: '完井报告库', refs: null, wiki: null, status: '已入库'
      })),
      total: n
    })
    apiRouter({ reports: () => json(200, filtered ? rows(3) : rows(25)) })
    render(<B1Landing />)
    expect(await screen.findByText('共 25 条')).toBeTruthy()
    fireEvent.click(document.querySelector('.ant-pagination-item-2')) // 翻到第 2 页（第 21–25 行）
    expect(await screen.findByText('《压舱报告 25》')).toBeTruthy()
    expect(screen.queryByText('《压舱报告 1》')).toBeNull()
    filtered = true // 关键词筛变 → resetKey 变化 → 页码归 1
    fireEvent.change(screen.getByPlaceholderText('搜报告名 / 所属库…'), { target: { value: 'x' } })
    expect(await screen.findByText('《压舱报告 1》')).toBeTruthy()
    expect(screen.queryByText('《压舱报告 25》')).toBeNull()
    expect(await screen.findByText('共 3 条')).toBeTruthy()
  })

  it('T2 库管理计数读信封 total（与 items.length 解耦——UI-07 server 分页后仍成立）', async () => {
    apiRouter({
      libs: () => json(200, { items: LIBS_LIST.items, total: 5 }) // total=5 ≠ items.length=2——行为锁
    })
    render(<B1Landing />)
    expect(await screen.findByText('库管理（5）')).toBeTruthy()
    fireEvent.click(screen.getByText('库管理（5）'))
    expect(await screen.findByText('筛选结果 5 条')).toBeTruthy()
    expect(await screen.findByText('共 2 条')).toBeTruthy() // 表内分页条统计＝当前数据行数（client 模式）
  })

  it('T3 活动流拉取失败：内联 Alert＋表格错误空态（失败态≠空态）', async () => {
    apiRouter({ activities: () => json(500, { code: 'kb_internal', message: '活动读取失败', trace_id: 'call-a0' }) })
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/库管理（\d+）/))
    const actBtns = screen.getAllByRole('button').filter(b => b.querySelector('.anticon-history'))
    fireEvent.click(actBtns[0])
    expect(await screen.findByText('活动记录拉取失败——下表不是最新数据')).toBeTruthy()
    expect(screen.getByText(/活动读取失败 · code kb_internal · trace call-a0/)).toBeTruthy()
    expect(screen.getByText('活动记录拉取失败')).toBeTruthy() // 表格错误空态（errorEmptyText）
    expect(screen.queryByText('这个库还没有活动记录')).toBeNull()
  })

  it('T4 运行中任务的禁用重试按钮悬停出 Tooltip（span 包裹——方案 §3.3）', async () => {
    apiRouter()
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/入库任务（\d+）/))
    await screen.findByText('《演示报告》')
    const retryBtn = screen.getAllByRole('button').find(b => b.querySelector('.anticon-redo') && b.disabled)
    expect(retryBtn).toBeTruthy() // 运行中任务行——操作按钮禁用
    fireEvent.mouseEnter(retryBtn.closest('span')) // 禁用控件经 span 挂 Tooltip
    expect(await screen.findByText('重试/重跑入库管线', {}, { timeout: 3000 })).toBeTruthy()
  })

  it('T5 详情抽屉开窗期间渲染 Spin（加载态≠空白）', async () => {
    let resolveDetail
    apiRouter({ detail: () => new Promise(resolve => { resolveDetail = () => resolve(json(200, REPORT_DETAIL)) }) })
    render(<B1Landing />)
    fireEvent.doubleClick(await screen.findByText('《N-02 井完井报告（英文 · 200 页）》'))
    expect(document.querySelector('.ant-spin-spinning')).toBeTruthy()
    resolveDetail()
    expect(await screen.findByText('井号 N-02')).toBeTruthy()
  })

  it('T5 库配置弹窗开窗期间渲染 Spin（cfgForm 空且无 cfgError）', async () => {
    let resolveCfg
    apiRouter({ getConfig: () => new Promise(resolve => { resolveCfg = () => resolve(json(200, LIB_CONFIG)) }) })
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/库管理（\d+）/))
    const cfgBtns = screen.getAllByRole('button').filter(b => b.querySelector('.anticon-setting'))
    fireEvent.click(cfgBtns[0])
    expect(document.querySelector('.ant-spin-spinning')).toBeTruthy()
    resolveCfg()
    expect(await screen.findByText('保存本库配置')).toBeTruthy()
  })

  it('T6 台账卡底指引收进「报告台账」页签 ?（正文不再直出）', async () => {
    apiRouter()
    render(<B1Landing />)
    await screen.findByText('报告台账（2）')
    expect(screen.queryByText(/新报告入库 → 切「入库任务」上传/)).toBeNull() // 卡底指引行已删
    const tabHelpIcon = document.querySelector('.ant-tabs-tab .anticon-question-circle')
    expect(tabHelpIcon).toBeTruthy() // 页签 label 的 ? 图标
    fireEvent.mouseEnter(tabHelpIcon)
    expect(await screen.findByText(
      /新报告入库 → 切「入库任务」上传；索引与百科等产物的生成规则按库配置，见「库管理」。/, {}, { timeout: 3000 }
    )).toBeTruthy() // 同内容进 ?
  })

  it('T9 活动流同分钟两行渲染无 key 告警（rowKey 复合）', async () => {
    const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    apiRouter({
      activities: () => json(200, {
        items: [
          { time: '2026-09-26 16:48', who: '小李 · 地质/质检', action: '上传报告', target: '《N-02 井完井报告（英文 · 200 页）》' },
          { time: '2026-09-26 16:48', who: '阿强 · 平台运维', action: '修改库配置', target: '完井报告库 · 切段方式：智能切段（256–1024 字）' }
        ],
        total: 2
      })
    })
    render(<B1Landing />)
    fireEvent.click(await screen.findByText(/库管理（\d+）/))
    const actBtns = screen.getAllByRole('button').filter(b => b.querySelector('.anticon-history'))
    fireEvent.click(actBtns[0])
    expect(await screen.findByText('阿强 · 平台运维')).toBeTruthy()
    expect(screen.getAllByText('2026-09-26 16:48').length).toBe(2) // 同分钟两行都渲染
    expect(errSpy.mock.calls.filter(args => String(args[0]).includes('same key'))).toHaveLength(0)
  })
})
