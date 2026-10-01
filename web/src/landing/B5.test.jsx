/**
 * 落地 B5 页组件测试（P1-05）——fetch 级 mock（挡 window.fetch 边界），client/
 * graph/kb 接口层与页面全部真代码；@antv/g6 打桩（jsdom 无 canvas——图渲染
 * 细节不入合同，交互与数据接线真跑）：
 * - 渲染：库选择器（lib_id 必传化）＋两页签＋整图一次给（图例计数/关系清单）；
 * - 端点 1 消费：图例开关→清单同步；查看节点选中→清单邻接过滤；带此节点提问
 *   （选中可用/未选中置灰，mock 提示＋导航 #/A1——A1 anchors 页面侧消费）；
 * - 端点 2/3 消费：抽取设置四段可交互＋保存（hint 服务端返回）＋对号强校
 *   400 对号明细弹窗（逐项未收录＋最接近台账词条）；
 * - 示例三源：从已抽结果生成（出处句回捞）/从报告库选句（LLM 预填三元组）/
 *   LLM 起草（真走统一出口端点）。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import B5Landing from './B5.jsx'

vi.mock('@antv/g6', () => {
  class Graph {
    on() {}
    async render() {}
    setElementState() {}
    setElementVisibility() {}
    destroy() {}
  }
  return { Graph }
})

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

// ── 合同形状夹具（后端 R1 snake_case，同 app/api/graph.py 响应模型） ──

const LIBS = {
  items: [
    { id: 'lib-1', name: '完井报告库', biz_template: 'completion', status: 'active', last_ingestion: null, annotations: {} },
    { id: 'lib-2', name: '生产月报库', biz_template: 'monthly', status: 'active', last_ingestion: null, annotations: {} }
  ],
  total: 2
}

const NET = {
  lib_id: 'lib-1', lib_name: '完井报告库',
  nodes: [
    { id: 'N-06', label: 'N-06', type: '井', short: 'N-06', sub: '井' },
    { id: 'N-02', label: 'N-02', type: '井', short: 'N-02', sub: '井' },
    { id: '渤南', label: '渤南', type: '区块', short: '渤南', sub: '区块' }
  ],
  edges: [
    { key: 'N-02|隶属|渤南', from: 'N-02', rel: '隶属', to: '渤南', note: null, evidence_chunk_id: 'f1', report_id: 'rpt-1' },
    { key: 'N-06|受效|N-02', from: 'N-06', rel: '受效', to: 'N-02', note: '劈分系数合计＝1', evidence_chunk_id: 'f2', report_id: 'rpt-1' }
  ],
  legend: [{ type: '井', count: 2 }, { type: '区块', count: 1 }],
  stats: { nodes: 3, edges: 2 }
}

const EMPTY_NET = { lib_id: 'lib-2', lib_name: '生产月报库', nodes: [], edges: [], legend: [], stats: { nodes: 0, edges: 0 } }

const CONFIG = {
  lib_id: 'lib-1', lib_name: '完井报告库',
  entity_types: ['井', '区块', '平台', '油田', '措施'],
  relation_tags: [
    { rel: '隶属', example: 'N-02 —隶属→ 渤南', desc: '井属于哪个区块' },
    { rel: '承载', example: '', desc: '井装在哪个平台上' }
  ],
  few_shot_examples: [{ sentence: 'N-02 井隶属渤南区块。', triple: 'N-02 —隶属→ 渤南' }],
  custom_instructions: '关系必须原文有依据；拿不准宁可跳过，不许创造新类型',
  saved_at: '2026-10-01 10:00', saved_by: '小李 · 地质/质检'
}

const REPORTS = {
  items: [
    { id: 'rpt-1', doc: '《N-02 井完井报告》', lib_id: 'lib-1', lib: '完井报告库', refs: 2, wiki: null, status: '已入库' }
  ],
  total: 1
}
const REPORT_DETAIL = {
  id: 'rpt-1', doc: '《N-02 井完井报告》', lib_id: 'lib-1', lib: '完井报告库',
  subject: null, refs: 2, wiki: null, status: '已入库', related_objects: [],
  fragments: [
    { id: 'f1', type: '原文块', path: '章节 01 ＞ 1.1 基本情况', text: 'N-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，井别采油。', version: 1, versions: [] }
  ]
}
const CONTEXT = { id: 'f1', type: '原文块', hit: 'N-02 井隶属渤南区块。', context: '1.1 基本情况：N-02 井隶属渤南区块。' }

const SAVE_OK = { lib_id: 'lib-1', saved_at: '2026-10-01 11:00', saved_by: '阿强 · 平台运维', hint: '已保存——设置在下次入库时生效。' }
const MISMATCH_400 = {
  code: 'graph_ontology_mismatch',
  message: '对号强校不过——以下类型/标签未收录进本体对号表，对不上拒存',
  detail: { mismatches: [
    { kind: 'entity_type', value: '机灵鬼', nearest: '设备' },
    { kind: 'relation_tag', value: '管辖着', nearest: '隶属' }
  ] }
}

const json = (status, body) => ({ ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) })

/** antd Select 下拉项点击（按 textContent 定位——避开页面同名文本歧义）。 */
async function selectOption(text) {
  return waitFor(() => {
    const el = [...document.querySelectorAll('.ant-select-item-option')]
      .find(o => o.textContent.includes(text))
    if (!el) throw new Error(`option not found: ${text}`)
    return el
  })
}

/** fetch 级 mock 路由（/api/kb 库/报告＋/api/graph 四端点＋起草端点）。 */
function apiRouter(overrides = {}) {
  const calls = { saves: [], drafts: [], contexts: 0 }
  fetchMock.mockImplementation(async (url, init) => {
    const u = String(url)
    const method = init?.method || 'GET'
    if (u.includes('/api/graph/net')) {
      const lib = new URLSearchParams(u.split('?')[1] || '').get('lib_id')
      if (overrides.net) return overrides.net(lib)
      return json(200, lib === 'lib-2' ? EMPTY_NET : NET)
    }
    if (u.includes('/api/graph/extract-config/draft-example')) {
      calls.drafts.push(JSON.parse(init.body))
      return overrides.draft
        ? overrides.draft(JSON.parse(init.body))
        : json(200, { sentence: 'N-11 井实施检泵措施（批次 20260911-T3）。', triple: '措施：检泵 —作用于→ N-11' })
    }
    if (u.includes('/api/graph/extract-config')) {
      if (method === 'PUT') {
        calls.saves.push(JSON.parse(init.body))
        if (overrides.save) return overrides.save(JSON.parse(init.body))
        return json(200, SAVE_OK)
      }
      const lib = new URLSearchParams(u.split('?')[1] || '').get('lib_id')
      return json(200, { ...CONFIG, lib_id: lib })
    }
    if (u.includes('/api/graph/blocked-edges')) {
      return json(200, { lib_id: 'lib-1', lib_name: '完井报告库', blocked_edges: [], stats: { blocked: 0 } })
    }
    if (/\/api\/kb\/fragments\/[^/]+\/context$/.test(u)) {
      calls.contexts += 1
      return json(200, CONTEXT)
    }
    if (/\/api\/kb\/reports\/[^/]+$/.test(u)) {
      return json(200, REPORT_DETAIL)
    }
    if (u.includes('/api/kb/reports')) {
      return json(200, REPORTS)
    }
    if (u.includes('/api/kb/libs')) {
      return json(200, LIBS)
    }
    return json(404, { code: 'test_unrouted', message: `unexpected ${method} ${u}` })
  })
  return calls
}

const fetchMock = vi.fn()

/** 打开页→切抽取设置页签（等待四段装载完成）。 */
async function openExtract() {
  render(<B5Landing />)
  await screen.findByText('完井报告库')
  fireEvent.click(await screen.findByText(/抽取设置/))
  await screen.findByText('实体类型清单（勾选启用）')
  await screen.findByDisplayValue('关系必须原文有依据；拿不准宁可跳过，不许创造新类型')
}

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  window.localStorage.clear()
  window.location.hash = ''
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  window.location.hash = ''
})

describe('B5 落地页 · 关系网（端点 1——整图一次给，过滤全前端本地）', () => {
  it('渲染：库选择器＋图例计数＋页签边数＝stats.edges＋关系清单全量', async () => {
    apiRouter()
    render(<B5Landing />)
    expect(await screen.findByText('完井报告库')).toBeTruthy()
    expect(await screen.findByText('井（2）')).toBeTruthy()
    expect(await screen.findByText('区块（1）')).toBeTruthy()
    expect(await screen.findByText(/关系网（2）/)).toBeTruthy()
    // 关系清单全量两条（未选中→全量）
    expect(await screen.findByText('隶属')).toBeTruthy()
    expect(await screen.findByText('受效')).toBeTruthy()
  })

  it('图例开关隐去整类→关系清单同步过滤（前端本地计算）', async () => {
    apiRouter()
    render(<B5Landing />)
    await screen.findByText('井（2）')
    // 关掉「井」类——两条边两端含井 → 全部隐去，清单空态文案出现
    const switches = screen.getAllByRole('switch')
    fireEvent.click(switches[0])
    expect(await screen.findByText('当前图例下没有可见关系。')).toBeTruthy()
  })

  it('查看节点选中→清单过滤为相邻关系＋带此节点提问可用（未选中置灰）', async () => {
    apiRouter()
    render(<B5Landing />)
    await screen.findByText('隶属')
    const ask = screen.getByRole('button', { name: '带此节点提问' })
    expect(ask.disabled).toBe(true) // 未选中置灰
    fireEvent.mouseDown(screen.getByText('选择节点'))
    fireEvent.click(await selectOption('N-06'))
    await waitFor(() => expect(ask.disabled).toBe(false))
    // 清单只列 N-06 的相邻关系（受效一条；隶属 N-02—渤南 不相邻不出列）
    expect(screen.queryByText('隶属')).toBeNull()
    expect(screen.getByText('受效')).toBeTruthy()
    // 点击→mock 提示＋导航 #/A1（A1 anchors 机制页面侧消费——A1 落地前 mock）
    fireEvent.click(ask)
    await screen.findByText(/已带上节点：N-06/)
  })

  it('空态：图谱开关关/无数据→空态自拟文案（不抽取即无图）', async () => {
    apiRouter()
    render(<B5Landing />)
    fireEvent.mouseDown(await screen.findByText('完井报告库'))
    fireEvent.click(await screen.findByText('生产月报库'))
    expect(await screen.findByText(/当前库暂无图谱数据/)).toBeTruthy()
    expect(await screen.findByText(/关系网（0）/)).toBeTruthy()
  })
})

describe('B5 落地页 · 抽取设置（端点 2/3——四段可交互＋对号强校两态）', () => {
  it('四段渲染＋保存成功：hint 服务端返回＋PUT body 全量整存整取', async () => {
    const calls = apiRouter()
    await openExtract()
    // 四段都来自端点 2（对号表投影实体类型/关系标签/few-shot/指令）
    expect(screen.getByText('措施')).toBeTruthy()
    expect(screen.getByText('隶属')).toBeTruthy()
    expect(screen.getByDisplayValue('N-02 井隶属渤南区块。')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '保存抽取设置' }))
    expect(await screen.findByText('已保存——设置在下次入库时生效。')).toBeTruthy()
    await waitFor(() => expect(calls.saves.length).toBe(1))
    const body = calls.saves[0]
    expect(body.lib_id).toBe('lib-1')
    expect(body.entity_types).toEqual(CONFIG.entity_types)
    expect(body.relation_tags[0].rel).toBe('隶属')
    expect(body.few_shot_examples).toEqual(CONFIG.few_shot_examples)
  })

  it('对号强校 400：对号明细弹窗逐项展示未收录词条＋最接近台账词条', async () => {
    apiRouter({
      save: () => json(400, MISMATCH_400)
    })
    await openExtract()
    fireEvent.click(screen.getByRole('button', { name: '保存抽取设置' }))
    expect(await screen.findByText('对号强校不过——拒存')).toBeTruthy()
    expect(await screen.findByText('机灵鬼')).toBeTruthy()
    expect(screen.getByText('管辖着')).toBeTruthy()
    expect(screen.getByText('设备')).toBeTruthy() // 最接近台账词条列
  })

  it('新增类型/新增关系/添加示例→进保存清单（可交互四段）', async () => {
    apiRouter()
    await openExtract()
    fireEvent.change(screen.getByPlaceholderText('新增类型'), { target: { value: '配注层' } })
    const addBtns = () => screen.getAllByRole('button', { name: /添\s*加/ })
    fireEvent.click(addBtns()[0]) // 实体类型面板添加
    expect(await screen.findByText('配注层')).toBeTruthy()
    fireEvent.change(screen.getByPlaceholderText('新增关系'), { target: { value: '取样自' } })
    fireEvent.click(addBtns()[1]) // 关系标签面板添加
    expect(await screen.findByText('取样自')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '添加示例' }))
    expect(screen.getAllByPlaceholderText('报告原句').length).toBe(2)
  })
})

describe('B5 落地页 · 示例三源辅助（对账 11——起草走真统一出口）', () => {
  it('三源①：从已抽结果生成——选用边回捞出处句自动配对', async () => {
    const calls = apiRouter()
    await openExtract()
    fireEvent.click(screen.getByRole('button', { name: '从已抽结果生成' }))
    fireEvent.click(screen.getAllByText('选用')[0])
    await screen.findByText('已生成示例，请核对后保存。')
    await waitFor(() => expect(calls.contexts).toBe(1)) // 出处句经片段回捞端点带出
    expect(screen.getAllByDisplayValue('N-02 井隶属渤南区块。').length).toBeGreaterThan(0) // 原句侧
    expect(screen.getAllByDisplayValue(/N-02 —隶属→ 渤南/).length).toBeGreaterThan(0) // 三元组侧
  })

  it('三源②：从报告库选句——报告→原句清单→LLM 预填三元组', async () => {
    const calls = apiRouter()
    await openExtract()
    fireEvent.click(screen.getByRole('button', { name: '从报告库选句' }))
    fireEvent.mouseDown(await screen.findByText('选择报告'))
    fireEvent.click(await selectOption('《N-02 井完井报告》'))
    await screen.findByText(/位于渤南区块 CEP-A 平台/) // 原句清单装载完成
    fireEvent.click(screen.getAllByText('选用')[0]) // 选句行内选用（LLM 预填三元组）
    await screen.findByText('已按所选原句预填三元组，请核对后保存。')
    await waitFor(() => expect(calls.drafts.length).toBe(1))
    expect(calls.drafts[0].sentence).toContain('位于渤南区块 CEP-A 平台')
    expect(calls.drafts[0].lib_id).toBe('lib-1')
  })

  it('三源③：LLM 起草——输入关系词点生成（POST draft-example）', async () => {
    const calls = apiRouter()
    await openExtract()
    fireEvent.click(screen.getByRole('button', { name: 'LLM 起草' }))
    fireEvent.change(screen.getByPlaceholderText('输入关系词，如：受效'), { target: { value: '作用于' } })
    // antd 两字按钮自动插空格（「生 成」）——按归一文本定位
    const genBtn = [...screen.getAllByRole('button')]
      .find(b => (b.textContent || '').replace(/\s/g, '') === '生成')
    fireEvent.click(genBtn)
    await screen.findByText('已生成示例草案，请核对后保存。')
    await waitFor(() => expect(calls.drafts.length).toBe(1))
    expect(calls.drafts[0].rel).toBe('作用于')
    expect(screen.getByDisplayValue('措施：检泵 —作用于→ N-11')).toBeTruthy()
  })
})
