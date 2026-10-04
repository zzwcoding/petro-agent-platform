/**
 * 落地 B3 页组件测试（P1-06）——fetch 级 mock（挡 window.fetch 边界），client/faq
 * 接口层与页面全部真代码：
 * - 渲染：问答清单（卡头 grand_total＋筛选计数）＋行标四态＋候选库入口；
 * - 审核流闭环：新增（端点 3，待审核提示）→ 发布（端点 17，转服务中）；
 * - 重复校验（端点 4）：输入即检防抖警告；
 * - 相似问增删（端点 5/6）经详情弹窗；
 * - 合并（端点 7——目标由人选）与停用/启用（端点 8）；
 * - 挖掘管线：候选库渲染＋展开钮只认比对结论（端点 9/12）＋起草填入新增弹窗
 *   （端点 13）＋扫库 202 轮询收场（端点 10/11）；
 * - 导入（端点 15 multipart form-data——P1-11 依赖落位）与导出（端点 16 预签名直链）；
 * - ⚙ 弹窗（合并阈值 0.87 只读展示——配置端点撤除登记）；
 * - UI-04（阶段 1 交互优化，方案 §5-B3）：主表/候选表接 PagedTable（分页条/resetKey
 *   回页 1/信封计数/空态与失败态分立）＋页头三件套＋⚙ 去假保存＋T8 文案＋扫库失败
 *   两路提示＋关键词 350ms 防抖＋请求序号守卫＋合并目标全库化＋候选表 loading。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import B3Landing, { stateTag } from './B3.jsx'

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

// ── 合同形状夹具（后端 R1 snake_case，同 app/api/faq.py 响应模型） ──

const ITEMS = {
  items: [
    { id: 'faq-1', question: '产量完成率怎么算？', answer: 'Σ实际产油 ÷ Σ计划配产 × 100%。', similar_questions: ['「月度完成率口径」（主任常问）'], status: 'serve', hook: null },
    { id: 'faq-8', question: '"老完成率"是什么口径？', answer: '旧口径条目，已随口径改版停用。', similar_questions: [], status: 'disabled', hook: null },
    { id: 'faq-9', question: '帮我预测明年油价', answer: '（负例：不回答。库里登记为"不该答的问题"）', similar_questions: ['「油价预测」'], status: 'negative', hook: null },
    { id: 'faq-10', question: '配注合格率是什么？', answer: '分层实注÷配注，达标井次占比。', similar_questions: [], status: 'pending_review', hook: { kind: 'metric', name: '配注合格率' } }
  ],
  total: 4,
  grand_total: 9
}

const DETAIL = {
  id: 'faq-1', question: '产量完成率怎么算？', answer: 'Σ实际产油 ÷ Σ计划配产 × 100%。',
  status: 'serve', hook: null,
  similar_questions: [{ id: 'sq-101', text: '「月度完成率口径」（主任常问）' }],
  maintainer: '小李', updated_at: '2026-09-26', version: 2
}

const CANDIDATES = {
  items: [
    { id: 'c1', question: '产量完成率咋算的', variants: ['「完成率咋算的」'], freq: 23, window: '近30天', status: 'pending', compare: null, draft: null, hook: null },
    { id: 'c2', question: '自然递减率怎么算', variants: ['「递减率公式」'], freq: 11, window: '近30天', status: 'compared',
      compare: { verdict: 'ok', dup_question: null, similarity: null, onto_hit: '指标卡 · 自然递减率', hint: '向量比对：与既有问答无重复。本体命中：指标卡 · 自然递减率。' }, draft: null, hook: null },
    { id: 'c4', question: 'N-02 的完井方式是啥', variants: [], freq: 15, window: '近30天', status: 'pending', compare: null, draft: null, hook: null }
  ],
  total: 3,
  scan: { running_task_id: null, last_hint: null }
}

const METRICS = { items: [{ id: 3, name: '★自然递减率', slot_name: '自然递减率', def: '月：1 − q_t / q_(t−1)', grain: '月', unit: '%', grain_display: '月 · %', status: ['现行'], owner: '开发室', source: 'ontology/petro m3' }], total: 1, grand_total: 1, page: 1, page_size: 500 }
const TERMS = { items: [{ id: 7, term: '躺井', type: '黑话 → 停产待检泵', def: '作业区口语，指停产待检泵。', status: '有效', status_key: '有效', owner: '采油工艺所', source: 'GLS', version: 'v1', expires_at: null, expires_display: '—', expired: false }], total: 1, grand_total: 1, page: 1, page_size: 500 }
const FRAGMENTS = { items: [{ id: 'f1', report_id: 'rpt-n02', report: '《N-02 井完井报告（英文 · 200 页）》', well: 'N-02', section: '章节 01 ＞ 1.2 投产信息', type: '原文块', hit: 'N-02（渤中28-1-N2）于 2019-06-15 投产。' }], total: 1, page: 1, page_size: 500 }

// UI-04 测试夹具：25 行（resetKey 回页 1——翻第 2 页后行 21 可见、行 1 消失）
const ITEMS_25 = {
  items: Array.from({ length: 25 }, (_, i) => ({
    id: `faq-x${i + 1}`, question: `问答行第 ${i + 1} 条`, answer: `答案 ${i + 1}`,
    similar_questions: [], status: 'serve', hook: null
  })),
  total: 25,
  grand_total: 40
}
// UI-04 测试夹具：候选 25 簇（mineF resetKey 回页 1）
const CANDIDATES_25 = {
  items: Array.from({ length: 25 }, (_, i) => ({
    id: `cc-${i + 1}`, question: `候选行第 ${i + 1} 条`, variants: [], freq: 100 - i,
    window: '近30天', status: 'pending', compare: null, draft: null, hook: null
  })),
  total: 25,
  scan: { running_task_id: null, last_hint: null }
}

const json = (status, body) => ({ ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) })

/** fetch 级 mock 路由（/api/faq 十七端点＋C1/B2 下拉源；calls 记录消费面）。 */
function apiRouter(overrides = {}) {
  const calls = { itemQueries: [], dupChecks: 0, creates: 0, reviews: [], compares: [], drafts: [], imports: [], exports: 0, scans: [], scanPolls: 0, similarAdds: [], similarDels: [], merges: [], states: [] }
  let scanned = false
  fetchMock.mockImplementation(async (url, init) => {
    const u = String(url)
    const method = init?.method || 'GET'
    if (u.includes('/api/faq/dup-checks')) {
      calls.dupChecks += 1
      return json(200, { hit: { id: 'faq-1', question: '产量完成率怎么算？' }, hint: '与既有问答「产量完成率怎么算？」疑似重复：建议改用合并相似问，或确认继续入库。' })
    }
    if (/\/api\/faq\/items\/[^/]+\/review$/.test(u)) {
      calls.reviews.push(JSON.parse(init.body))
      return json(200, { id: 'faq-10', status: 'serve', version: 2, hint: '审核通过已发布：「配注合格率是什么？」——命中即秒回，不走报告检索。' })
    }
    if (/\/api\/faq\/items\/[^/]+\/similar-questions$/.test(u)) {
      calls.similarAdds.push(u)
      return json(200, { id: 'sq-104', text: '新的问法', version: 3 })
    }
    if (/\/api\/faq\/items\/[^/]+\/similar-questions\/[^/]+$/.test(u)) {
      calls.similarDels.push(u)
      return json(200, { version: 4, hint: '已删除——该问法不再命中本条。' })
    }
    if (/\/api\/faq\/items\/[^/]+\/merge$/.test(u)) {
      calls.merges.push(JSON.parse(init.body))
      return json(200, { from_id: 'faq-2', target_id: 'faq-1', merged_count: '2 条 → 1 条', target: { id: 'faq-1', similar_questions_count: 2 }, hint: '已合并：2 条 → 1 条——两种问法现在命中同一条答案。' })
    }
    if (/\/api\/faq\/items\/[^/]+\/state$/.test(u)) {
      calls.states.push(JSON.parse(init.body))
      return json(200, { id: 'faq-8', status: 'disabled', version: 2 })
    }
    if (/\/api\/faq\/items\/[^/]+$/.test(u)) {
      return overrides.detail ? overrides.detail() : json(200, DETAIL)
    }
    if (u.includes('/api/faq/items') && method === 'POST') {
      calls.creates += 1
      return json(200, { id: 'faq-11', status: 'pending_review', version: 1, hint: '已提交审核：「配注合格率是什么？」——审核发布后命中即秒回。', candidate: null })
    }
    if (u.includes('/api/faq/items')) {
      calls.itemQueries.push(u)
      return overrides.items ? overrides.items(u) : json(200, ITEMS)
    }
    if (/\/api\/faq\/scan-tasks$/.test(u) && method === 'POST') {
      calls.scans.push(u)
      if (scanned) return json(409, { code: 'faq_scan_running', message: '已有进行中的扫库任务——完成后才能再次发起' })
      scanned = true
      return json(202, { task_id: 'scan-1002', status: 'running', hint: '正在扫描用户问句库（聚类＋频次统计）……可关闭弹窗继续其他操作，扫描不会中断；重开弹窗看结果。' })
    }
    if (/\/api\/faq\/scan-tasks\/[^/]+$/.test(u)) {
      calls.scanPolls += 1
      return overrides.scanPoll
        ? overrides.scanPoll()
        : json(200, { task_id: 'scan-1002', status: 'done', new_cluster_count: 0, new_clusters: [], hint: '扫描完成：本次新增 0 个候选簇——A1 问一问历史会话尚未上线，暂无可挖掘语料；上线后扫库将自动分析历史会话归纳候选簇。' })
    }
    if (/\/api\/faq\/candidates\/[^/]+\/compare$/.test(u)) {
      calls.compares.push(u)
      return json(200, { id: 'c1', status: 'compared', compare: { verdict: 'dup', dup_question: '产量完成率怎么算？', similarity: 1, onto_hit: '指标卡 · 产量完成率', hint: '向量比对：与「产量完成率怎么算？」相似度 1.00——高于合并线，建议改用合并相似问，不新增条目。本体命中：指标卡 · 产量完成率。' } })
    }
    if (/\/api\/faq\/candidates\/[^/]+\/draft$/.test(u)) {
      calls.drafts.push(u)
      return json(200, { id: 'c2', status: 'drafted', draft: '月度递减率按环比计算。（来源：指标卡 · 自然递减率 · LLM 基于历史回答归纳，请人工核实）', hook_suggestion: { kind: 'metric', name: '自然递减率' } })
    }
    if (u.includes('/api/faq/candidates')) {
      return overrides.candidates ? overrides.candidates() : json(200, CANDIDATES)
    }
    if (u.includes('/api/faq/export')) {
      calls.exports += 1
      return json(200, { download_url: 'https://minio.test/get/faq/export/x.csv', expires_at: '2026-10-02 09:40', columns: ['标准问', '相似问法', '负例问法', '答案'], hint: '已导出 FAQ 全库（含相似问/负例列）——可线下编辑后重新导入。' })
    }
    if (u.includes('/api/faq/import')) {
      calls.imports.push(u)
      return json(200, { dry_run: false, added: 12, merged: 3, skipped: 2, failed: 1, failures: [{ row: 7, reason: '缺答案列——模板列必填' }], hint: '导入完成：新增 12 · 合并 3 · 跳过 2 · 失败 1（失败原因：1 行缺答案列——模板列必填）。' })
    }
    if (u.includes('/api/semantics/metrics')) return json(200, METRICS)
    if (u.includes('/api/semantics/terms')) return json(200, TERMS)
    if (u.includes('/api/kb/fragments')) return json(200, FRAGMENTS)
    return json(404, { code: 'test_unrouted', message: `unexpected ${method} ${u}` })
  })
  return calls
}

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  vi.spyOn(window, 'open').mockImplementation(() => null)
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()  // 防抖 fake timers 用例兜底复原（B2.test 同款纪律）
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('B3 落地页 · 问答清单（端点 1/2）', () => {
  it('渲染清单：卡头 grand_total（9）＋筛选计数（4/9）＋四态行标', async () => {
    apiRouter()
    render(<B3Landing />)

    expect(await screen.findByText('问答清单（9）')).toBeTruthy()
    expect(await screen.findByText('筛选结果 4 / 9 条')).toBeTruthy()
    expect(screen.getByText('产量完成率怎么算？')).toBeTruthy()
    expect(screen.getByText('待审核')).toBeTruthy() // 待审核行标（企业化清理批落位）
  })

  it('状态筛走服务端 query（端点 1 status 参数）', async () => {
    const calls = apiRouter()
    render(<B3Landing />)
    await screen.findByText('筛选结果 4 / 9 条')

    fireEvent.mouseDown(await screen.findByText('状态：全部'))
    await waitFor(() => {
      const opt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '待审核')
      expect(opt).toBeTruthy()
      fireEvent.click(opt)
    })
    await waitFor(() => {
      expect(calls.itemQueries.some(u => u.includes('status=pending'))).toBe(true)
    })
  })

  it('状态标函数四态互斥（合同枚举直映）', () => {
    expect(stateTag('serve').props.color).toBe('green')
    expect(stateTag('pending_review').props.color).toBe('orange')
    expect(stateTag('negative').props.color).toBe('red')
    expect(stateTag('disabled').props.color).toBeUndefined()
  })
})

describe('B3 落地页 · 新增问答与审核发布（端点 3/4/17）', () => {
  it('输入即检重复警告（端点 4 防抖）→ 入库（端点 3）出「已提交审核」提示', async () => {
    const calls = apiRouter()
    render(<B3Landing />)
    fireEvent.click(await screen.findByText('新增问答'))

    fireEvent.change(screen.getByPlaceholderText('问题'), { target: { value: '产量完成率怎么算' } })
    await waitFor(() => expect(calls.dupChecks).toBeGreaterThan(0), { timeout: 2500 })
    expect(await screen.findByText(/与既有问答「产量完成率怎么算？」疑似重复/)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '入 库' }))
    await screen.findByText(/已提交审核/)
    expect(calls.creates).toBe(1)
  })

  it('待审核行「发布」（端点 17）→ 提示命中即秒回', async () => {
    const calls = apiRouter()
    render(<B3Landing />)
    await screen.findByText('配注合格率是什么？')

    fireEvent.click(screen.getByText(/发\s*布/).closest('button'))
    await waitFor(() => expect(calls.reviews.length).toBe(1))
    expect(calls.reviews[0]).toEqual({ action: 'publish' })
  })
})

describe('B3 落地页 · 相似问增删与停用（端点 5/6/8）', () => {
  it('详情弹窗逐条增删（独立检索项即时生效）', async () => {
    const calls = apiRouter()
    render(<B3Landing />)
    await screen.findByText('产量完成率怎么算？')

    fireEvent.click(screen.getByRole('button', { name: '详情：产量完成率怎么算？' }))
    await screen.findByText('相似问法')
    expect(screen.getAllByText('「月度完成率口径」（主任常问）').length).toBeGreaterThanOrEqual(1) // 清单行＋详情弹窗各一

    fireEvent.change(screen.getByPlaceholderText('添加相似问法（如主任的另一种问法）…'), {
      target: { value: '新的问法' }
    })
    fireEvent.click(screen.getByText(/添\s*加/).closest('button'))
    await waitFor(() => expect(calls.similarAdds.length).toBe(1))

    fireEvent.click(screen.getByText(/删\s*除/).closest('button'))
    await waitFor(() => expect(calls.similarDels.length).toBe(1))
  })

  it('行尾停用（端点 8）→ POST action=disable', async () => {
    const calls = apiRouter()
    render(<B3Landing />)
    await screen.findByText('"老完成率"是什么口径？')

    fireEvent.click(screen.getByRole('button', { name: '停用：产量完成率怎么算？' }))
    await waitFor(() => expect(calls.states.length).toBe(1))
    expect(calls.states[0]).toEqual({ action: 'disable' })
  })
})

describe('B3 落地页 · 合并相似问（端点 7——目标由人选）', () => {
  it('行尾合并图标 → 目标选择 → 合并成功提示', async () => {
    const calls = apiRouter()
    render(<B3Landing />)
    await screen.findByText('产量完成率怎么算？')

    fireEvent.click(screen.getByRole('button', { name: '合并："老完成率"是什么口径？' }))
    await screen.findByText(/被并入：/)
    fireEvent.mouseDown(screen.getByText('选择目标问答…'))
    await waitFor(() => {
      const opt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '产量完成率怎么算？')
      expect(opt).toBeTruthy()
      fireEvent.click(opt)
    })
    fireEvent.click(screen.getByRole('button', { name: '合 并' }))
    await waitFor(() => expect(calls.merges.length).toBe(1))
    await screen.findByText(/已合并：2 条 → 1 条/)
  })
})

describe('B3 落地页 · 挖掘管线（端点 9/10/11/12/13）', () => {
  it('候选库渲染：频次倒序＋未比对不显示展开按钮', async () => {
    apiRouter()
    render(<B3Landing />)
    fireEvent.click(await screen.findByText('从问句挖掘'))

    expect(await screen.findByText('候选 3 簇 · 按频次排序')).toBeTruthy()
    expect(screen.getByText('产量完成率咋算的')).toBeTruthy()
    expect(screen.getAllByText(/同簇变体：/).length).toBe(2)
    // 展开按钮：只有已比对的 c2 有展开钮（compare 非 null——合同）
    const expandIcons = document.querySelectorAll('.ant-table-row-expand-icon')
    expect(expandIcons.length).toBe(1)
  })

  it('向量比对（端点 12）→ 起草（端点 13）→ 草稿自动填入新增弹窗', async () => {
    const calls = apiRouter()
    render(<B3Landing />)
    fireEvent.click(await screen.findByText('从问句挖掘'))
    await screen.findByText('产量完成率咋算的')

    fireEvent.click(screen.getByRole('button', { name: '比对：产量完成率咋算的' }))
    await waitFor(() => expect(calls.compares.length).toBe(1))

    fireEvent.click(screen.getByRole('button', { name: '起草：自然递减率怎么算' }))
    await waitFor(() => expect(calls.drafts.length).toBe(1))
    expect(await screen.findByText('入库（来自候选草稿）')).toBeTruthy()
    expect(screen.getByDisplayValue(/月度递减率按环比计算/)).toBeTruthy()
  })

  it('扫库 202 受理 → 轮询 done → 完成提示（料源空态说明——A1 未上线）', async () => {
    const calls = apiRouter()
    render(<B3Landing />)
    fireEvent.click(await screen.findByText('从问句挖掘'))

    fireEvent.click(screen.getByText('扫库'))
    await waitFor(() => expect(calls.scans.length).toBe(1))
    await screen.findByText(/扫描完成：本次新增 0 个候选簇——A1 问一问历史会话尚未上线/, undefined, { timeout: 5000 })
    expect(calls.scanPolls).toBeGreaterThan(0)
  })
})

describe('B3 落地页 · 导入导出与 ⚙（端点 15/16＋配置展示）', () => {
  it('导出（端点 16）→ 预签名直链 window.open＋成功提示', async () => {
    const calls = apiRouter()
    render(<B3Landing />)
    fireEvent.click(await screen.findByText('导出'))

    await waitFor(() => expect(calls.exports).toBe(1))
    expect(window.open).toHaveBeenCalledWith('https://minio.test/get/faq/export/x.csv', '_blank')
  })

  it('导入（端点 15 multipart form-data＋query 参数）→ 四计数提示', async () => {
    const calls = apiRouter()
    render(<B3Landing />)
    fireEvent.click(await screen.findByText('导入'))

    const file = new File(['标准问,相似问法,负例问法,答案\n'], 'faq.csv', { type: 'text/csv' })
    const input = document.querySelector('input[type="file"]')
    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByText('开始导入'))

    await screen.findByText(/导入完成：新增 12 · 合并 3 · 跳过 2 · 失败 1/)
    expect(calls.imports.length).toBe(1)
    expect(calls.imports[0]).toContain('mode=append')
    expect(calls.imports[0]).toContain('dry_run=false')
    expect(calls.imports[0]).toContain('filename=faq.csv')
    // multipart 落位（P1-11）：body＝FormData（file 字段携带上传件，不手写 Content-Type）
    const importCall = fetchMock.mock.calls.find(c => String(c[0]).includes('/api/faq/import'))
    expect(importCall[1].body).toBeInstanceOf(FormData)
    expect(importCall[1].body.get('file')).toBeInstanceOf(File)
    expect(importCall[1].headers?.['Content-Type']).toBeUndefined()
  })

  it('⚙ 弹窗：合并阈值 0.87 只读展示＋负例入口 Tag（配置端点撤除登记）', async () => {
    apiRouter()
    render(<B3Landing />)
    await screen.findByText('问答清单（9）')

    fireEvent.click(screen.getByRole('button', { name: 'setting' })
      || document.querySelector('.anticon-setting').closest('button'))
    expect(await screen.findByText('合并阈值')).toBeTruthy()
    // UI-04 T2：去假保存——标题只读化、「保存配置」按钮与「已保存」假回执消失
    expect(await screen.findByText('检索配置（只读展示）')).toBeTruthy()
    expect(screen.queryByText('保存配置')).toBeNull()
    expect(screen.queryByText(/已保存/)).toBeNull()
    const threshold = screen.getByDisplayValue('0.87')
    expect(threshold.disabled).toBe(true) // 阈值输入框仅承载数值展示（B3-4）
    expect(screen.getByText('已开')).toBeTruthy()
  })
})

describe('B3 落地页 · UI-04 交互优化（方案 §5-B3）', () => {
  it('T1 主表接 PagedTable：分页条「共 N 条」恒显（单页也显示）', async () => {
    apiRouter()
    render(<B3Landing />)
    await screen.findByText('筛选结果 4 / 9 条')
    expect(screen.getByText('共 4 条')).toBeTruthy() // hideOnSinglePage=false——单页恒显＋showTotal
  })

  it('T1 空态定死话术（Empty 形态，不吃 antd 默认「暂无数据」）', async () => {
    apiRouter({ items: () => json(200, { items: [], total: 0, grand_total: 9 }) })
    render(<B3Landing />)
    await screen.findByText('筛选结果 0 / 9 条')
    expect(await screen.findByText('还没有问答：点「新增问答」录入，或「导入」批量建。')).toBeTruthy()
    expect(document.querySelector('.ant-empty')).toBeTruthy()
    expect(screen.queryByText('暂无数据')).toBeNull()
  })

  it('T1 statusF 变化自动回页 1（resetKey 绑筛状态）', async () => {
    apiRouter({ items: () => json(200, ITEMS_25) })
    render(<B3Landing />)
    await screen.findByText('筛选结果 25 / 40 条')
    fireEvent.click(screen.getByText('2'))
    expect(screen.getByText('问答行第 21 条')).toBeTruthy() // 第 2 页只有行 21-25
    expect(screen.queryByText('问答行第 1 条')).toBeNull()
    fireEvent.mouseDown(document.querySelector('.ant-select-selection-item[title="状态：全部"]'))
    await waitFor(() => {
      const opt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '待审核')
      expect(opt).toBeTruthy()
      fireEvent.click(opt)
    })
    await waitFor(() => {
      expect(document.querySelector('.ant-pagination-item-active')?.getAttribute('title')).toBe('1')
    })
    expect(screen.getByText('问答行第 1 条')).toBeTruthy()
    expect(screen.queryByText('问答行第 21 条')).toBeNull()
  })

  it('T1 「筛选结果 N / M 条」读信封 total/grandTotal（与行数解耦）', async () => {
    apiRouter({ items: () => json(200, { items: ITEMS.items.slice(0, 3), total: 9, grand_total: 20 }) })
    render(<B3Landing />)
    expect(await screen.findByText('筛选结果 9 / 20 条')).toBeTruthy() // 统计行读信封
    expect(screen.getByText('共 3 条')).toBeTruthy() // 分页条统计＝client 模式当前行数
  })

  it('T3/T11 主表失败态分立：内联 Alert 常驻＋错误空态（非默认暂无数据）＋errText 三段含 trace', async () => {
    apiRouter({ items: () => json(500, { code: 'faq_items_broken', message: '问答清单查询失败', trace_id: 't-abc' }) })
    const { container } = render(<B3Landing />)
    expect(await screen.findByText('问答清单拉取失败——下表不是最新数据')).toBeTruthy() // 内联 Alert 常驻
    await waitFor(() => expect(container.textContent).toContain('code faq_items_broken · trace t-abc')) // errText 三段
    expect(screen.getByText('问答清单拉取失败')).toBeTruthy() // 错误空态（errorEmptyText）
    expect(screen.queryByText('暂无数据')).toBeNull() // 不再吃 antd 默认
    expect(document.querySelector('.ant-empty')).toBeTruthy()
  })

  it('T5 页头＝标题＋helpTop（UI-09 口号副标题删除，POSITION_HELP 挂标题旁）；卡头 extra 三句口号消失', async () => {
    apiRouter()
    render(<B3Landing />)
    expect(await screen.findByText('常见问题库')).toBeTruthy()
    const titleSpan = screen.getByText('常见问题库')
    expect(titleSpan.querySelector('.anticon-question-circle')).toBeTruthy() // POSITION_HELP ? 在标题旁
    expect(screen.queryByText('常问问题直接秒回')).toBeNull() // UI-09：口号副标题不再直出
    const cardHead = screen.getByText('问答清单（9）').closest('.ant-card-head')
    expect(cardHead.textContent).not.toContain('常问问题直接秒回') // 卡头 extra 三句口号消失
    expect(cardHead.querySelector('.anticon-question-circle')).toBeTruthy() // 卡头只留 helpIcon
  })

  it('T6 轮询终态 failed（HTTP 200 终态行）→「扫库任务未成功」message', async () => {
    apiRouter({
      scanPoll: () => json(200, { task_id: 'scan-1002', status: 'failed', new_cluster_count: 0, new_clusters: [], hint: '' })
    })
    render(<B3Landing />)
    fireEvent.click(await screen.findByText('从问句挖掘'))
    fireEvent.click(screen.getByText('扫库'))
    await screen.findByText(/扫库任务未成功（状态：failed）——可在本页重新发起扫库/, undefined, { timeout: 4000 })
  })

  it('T6 轮询请求连续失败 →「扫库进度查询失败」message（errText 三段含 trace）', async () => {
    apiRouter({
      scanPoll: () => json(500, { code: 'faq_scan_poll_broken', message: '扫库进度查询失败', trace_id: 't-err' })
    })
    render(<B3Landing />)
    fireEvent.click(await screen.findByText('从问句挖掘'))
    fireEvent.click(screen.getByText('扫库'))
    // 连续两次轮询失败（容忍一次重试）才向上抛——间隔一个轮询节奏（800ms）
    await screen.findByText(/扫库进度查询失败：.*code faq_scan_poll_broken.*trace t-err/, undefined, { timeout: 5000 })
  })

  it('T7 候选表接 PagedTable：分页条＋「候选 N 簇」读信封 total（与行数解耦）', async () => {
    apiRouter({ candidates: () => json(200, { ...CANDIDATES, total: 9 }) })
    render(<B3Landing />)
    fireEvent.click(await screen.findByText('从问句挖掘'))
    expect(await screen.findByText('候选 9 簇 · 按频次排序')).toBeTruthy() // N 读信封 total
    expect(screen.getByText('共 3 条')).toBeTruthy() // 分页条统计＝client 模式当前行数
  })

  it('T7 mineF 变化自动回页 1（resetKey=mineF）', async () => {
    apiRouter({ candidates: () => json(200, CANDIDATES_25) })
    render(<B3Landing />)
    fireEvent.click(await screen.findByText('从问句挖掘'))
    await screen.findByText('候选行第 1 条')
    fireEvent.click(within(screen.getByText(/候选 25 簇/).closest('.ant-modal')).getByText('2'))
    expect(screen.getByText('候选行第 21 条')).toBeTruthy()
    const modal = screen.getByText(/候选 25 簇/).closest('.ant-modal')
    fireEvent.mouseDown(within(modal).getByText('状态：全部'))
    await waitFor(() => {
      const opt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '疑似重复')
      expect(opt).toBeTruthy()
      fireEvent.click(opt)
    })
    await waitFor(() => {
      expect(modal.querySelector('.ant-pagination-item-active')?.getAttribute('title')).toBe('1')
    })
    expect(screen.getByText('候选行第 1 条')).toBeTruthy()
    expect(screen.queryByText('候选行第 21 条')).toBeNull()
  })

  it('T8 ⚙ 弹窗 ? 工程口吻改业务口吻（无实施批/D2/端点字样）', async () => {
    apiRouter()
    render(<B3Landing />)
    await screen.findByText('问答清单（9）')
    fireEvent.click(screen.getByRole('button', { name: 'setting' })
      || document.querySelector('.anticon-setting').closest('button'))
    await screen.findByText('检索配置（只读展示）')
    fireEvent.mouseEnter(document.querySelector('.ant-modal-header .anticon-question-circle'))
    expect(await screen.findByText(/阈值由系统管理员统一校准/)).toBeTruthy()
    expect(screen.queryByText(/实施批/)).toBeNull()
    expect(screen.queryByText(/收敛 D2/)).toBeNull()
    expect(screen.queryByText(/配置读写端点/)).toBeNull()
  })

  it('T10 关键词 350ms 防抖：击键窗口内多次输入只发一次请求（fake timers）', async () => {
    const calls = apiRouter()
    render(<B3Landing />)
    await screen.findByText('筛选结果 4 / 9 条') // 首拍数据到位（真计时器）
    const before = calls.itemQueries.length
    vi.useFakeTimers()
    try {
      const input = screen.getByPlaceholderText('搜问题 / 答案 / 相似问法…')
      await act(async () => {
        fireEvent.change(input, { target: { value: '产量' } })
        vi.advanceTimersByTime(100)
        fireEvent.change(input, { target: { value: '产量完成' } })
        vi.advanceTimersByTime(100)
        fireEvent.change(input, { target: { value: '产量完成率' } })
        vi.advanceTimersByTime(349) // 仍在 350ms 防抖窗口内（距上次击键 349ms）
      })
      expect(calls.itemQueries.length).toBe(before) // 窗口内零请求
      await act(async () => { vi.advanceTimersByTime(1) }) // 防抖到点（350ms）
      expect(calls.itemQueries.length).toBe(before + 1) // 只发一次
      expect(decodeURIComponent(calls.itemQueries[calls.itemQueries.length - 1])).toContain('keyword=产量完成率')
    } finally {
      vi.useRealTimers()
    }
  })

  it('T10 竞态守卫：慢的旧响应后到，不覆盖新筛选结果（序号守卫）', async () => {
    let releasePending // status=pending 响应挂起（制造过期响应）
    const calls = { queries: [] }
    fetchMock.mockImplementation(async url => {
      const u = String(url)
      if (u.includes('/api/faq/items')) {
        calls.queries.push(u)
        if (u.includes('status=pending')) {
          return new Promise(resolve => {
            releasePending = () => resolve(json(200, {
              items: [{ id: 'faq-p1', question: '竞态测试专用待审问句', answer: '仅挂起响应携带', similar_questions: [], status: 'pending_review', hook: null }],
              total: 1, grand_total: 9
            }))
          })
        }
        return json(200, ITEMS)
      }
      return json(404, { code: 'test_unrouted', message: `unexpected ${u}` })
    })
    render(<B3Landing />)
    await screen.findByText('筛选结果 4 / 9 条') // 首拍（all）
    // 切 pending（响应挂起）→ 切回 all（立即返回）
    fireEvent.mouseDown(document.querySelector('.ant-select-selection-item[title="状态：全部"]'))
    await waitFor(() => {
      const opt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '待审核')
      expect(opt).toBeTruthy()
      fireEvent.click(opt)
    })
    await waitFor(() => expect(calls.queries.some(u => u.includes('status=pending'))).toBe(true))
    fireEvent.mouseDown(document.querySelector('.ant-select-selection-item[title="待审核"]'))
    await waitFor(() => {
      const opt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '状态：全部')
      expect(opt).toBeTruthy()
      fireEvent.click(opt)
    })
    await waitFor(() => expect(calls.queries.filter(u => u.includes('status=all')).length).toBe(2)) // 首拍＋切回
    // 旧 pending 响应此刻才到——序号守卫必须丢弃（不回写旧结果）
    await act(async () => { releasePending() })
    expect(screen.queryByText('竞态测试专用待审问句')).toBeNull() // 旧 pending 专有行未回写
    expect(screen.getByText('产量完成率怎么算？')).toBeTruthy() // 仍是 all 结果
    expect(screen.getByText('筛选结果 4 / 9 条')).toBeTruthy() // 统计行未被旧响应覆盖
  })

  it('T12 合并目标全库化：不带筛 getItems 填充＋被状态筛遮住的行可选', async () => {
    const calls = apiRouter()
    render(<B3Landing />)
    await screen.findByText('筛选结果 4 / 9 条')
    // 主表先按状态筛「服务中」——其余状态行被筛遮住
    fireEvent.mouseDown(document.querySelector('.ant-select-selection-item[title="状态：全部"]'))
    await waitFor(() => {
      const opt = [...document.querySelectorAll('.ant-select-item-option')]
        .find(o => o.getAttribute('title') === '服务中')
      expect(opt).toBeTruthy()
      fireEvent.click(opt)
    })
    await waitFor(() => expect(calls.itemQueries.some(u => u.includes('status=serve'))).toBe(true))
    // 打开合并弹窗——触发独立的不带筛 getItems（status=all&keyword= 空参）
    fireEvent.click(screen.getByRole('button', { name: '合并：产量完成率怎么算？' }))
    await screen.findByText(/被并入：/)
    await waitFor(() => {
      const last = calls.itemQueries[calls.itemQueries.length - 1]
      expect(last).toContain('/api/faq/items?status=all&keyword=')
    })
    fireEvent.mouseDown(screen.getByText('选择目标问答…'))
    await waitFor(() => {
      // 被状态筛遮住的停用行可作目标；待审核行不进目标（排除条件照抄原行为）
      expect([...document.querySelectorAll('.ant-select-item-option')]
        .some(o => o.getAttribute('title') === '"老完成率"是什么口径？')).toBe(true)
      expect([...document.querySelectorAll('.ant-select-item-option')]
        .some(o => o.getAttribute('title') === '配注合格率是什么？')).toBe(false)
    })
  })

  it('T13 候选表拉取期间渲染 loading', async () => {
    let releaseCands
    fetchMock.mockImplementation(async url => {
      const u = String(url)
      if (u.includes('/api/faq/candidates')) {
        return new Promise(resolve => { releaseCands = () => resolve(json(200, CANDIDATES)) })
      }
      if (u.includes('/api/faq/items')) return json(200, ITEMS)
      return json(404, { code: 'test_unrouted', message: `unexpected ${u}` })
    })
    render(<B3Landing />)
    await screen.findByText('筛选结果 4 / 9 条')
    fireEvent.click(screen.getByText('从问句挖掘'))
    const modal = (await screen.findByText('候选 0 簇 · 按频次排序')).closest('.ant-modal')
    await waitFor(() => expect(modal.querySelector('.ant-spin-spinning')).toBeTruthy()) // 拉取期间 loading
    await act(async () => { releaseCands() })
    expect(await screen.findByText('候选 3 簇 · 按频次排序')).toBeTruthy()
    expect(modal.querySelector('.ant-spin-spinning')).toBeNull() // 到位后 loading 撤除
  })
})
