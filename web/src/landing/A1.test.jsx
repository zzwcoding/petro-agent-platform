/**
 * 落地 A1 页组件测试（P1-09）——fetch 级 mock（挡 window.fetch 边界），
 * api/chat 接口层与页面全部真代码；SSE 流以真 Response(ReadableStream) 回放
 * P1-08c 金样本帧序（树帧全在首 token 之前——时序合同）：
 * - 思考树：node 四态原位升更新（N1 两拍不重复）/skipped 灰显/note 小字/缩进链内；
 * - 答案流式：token 拼贴→answer 帧收口；置信度徽标/兜底标注/FAQ 直出标注；
 * - citation 角标点击→出处抽屉→报告跳 #/B2?chunk= 定位、图谱跳 #/B5；
 * - 澄清帧交互→端点 5 resume 回流续推（同一回合续写）；
 * - replay_truncated 收场话术＋从断点恢复（端点 4 重连形态真发 resume_run_id）；
 * - @ 点名面板（端点 6 assets 投影）→ token 结晶体落输入框。
 * - UI-01（阶段 1 交互优化）：发送清空/IME 守卫/左栏封顶计数/滚底跟随阈值/
 *   会话收场复拉/错误三段化/审批驳回反馈/说明收束与文案收束（尾部 describe 群）。
 * - UI-14（空态巡检）：本机最近运行块整显隐置顶用例（RUN_HISTORY 模块级状态——
 *   空态判定须先于全文件其他用例）＋回放大 Alert→轻量条断言镜像（意见 1＋2＋3）。
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { applyFrame, clarifyCardView, confidenceTag, citationJump, intentSourceLine, newTurn } from './A1.jsx'
import A1Landing from './A1.jsx'
import { useAppStore } from '../store/app.js'

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

// ── SSE 夹具（帧序照抄 app/domains/chat 三链帧产出） ──

/** 帧 → SSE 文本 → Response（id 自增枚举——00 §6.1 信封）。 */
function sseResponse(frames) {
  const text = frames.map(([event, data], i) =>
    `id: ${i + 1}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`
  ).join('')
  return new Response(text, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

const CITATION_C1 = { ref: 'c1', kind: '报告引用', label: '出处 1 · N-02 完井报告', locator: { fragment_id: 'f3', report: 'N-02 完井报告', section: '2 完井段' } }
const CITATION_C2 = { ref: 'c2', kind: '图谱', label: '出处 2 · 关系图谱', locator: { entity: 'N-02', relation: '隶属' } }

/** 检索问答链直答金样本（树帧→token→citation→answer→done）。 */
function askFullFrames() {
  return [
    ['session', { run_id: 'run-g1', thread_id: 'sess-g1' }],
    ['stage', { stage: 0 }],
    ['stage', { stage: 1 }],
    ['node', { key: 'N1', name: '统一安检', label: '统一安检', state: 'process', tag: '代码 · 字面规则', note: '统一安检——三道逐条翻' }],
    ['sec_check', { seq: 1, name: '注入扫描', result: 'pass', note: '字面规则未命中' }],
    ['sec_check', { seq: 2, name: '禁用词索引', result: 'pass', note: '字面规则未命中' }],
    ['sec_check', { seq: 3, name: '身份与数据域', result: 'pass', note: 'aqiang' }],
    ['node', { key: 'N1', name: '统一安检', label: '统一安检', state: 'finish', note: '三道全过——放行' }],
    ['match', { matcher: 'FAQ 索引', status: 'miss' }],
    ['match', { matcher: '报告索引', status: 'hit', confidence: 'high', note: 'N-02 完井报告' }],
    ['assembly', { anchor_line: null, slots: '意图＝防砂方式', terms: [], candidates: [{ matcher: '报告索引', name: 'N-02 完井报告', confidence: 'high', kind: 'report' }], chains: ['统一安检链', '检索问答链'] }],
    ['stage', { stage: 2 }],
    ['verdict', { chain: '检索问答链', slots: '意图＝防砂方式', confidence: '高（检索证据分 0.62）', need_clarify: false }],
    ['stage', { stage: 3 }],
    ['node', { key: 'N17', name: '检索问答', label: '检索问答', state: 'process', tag: '代码 · 语义瀑布逐级推进' }],
    ['node', { key: 'S0', name: '身份四要素', label: '身份四要素', state: 'process' }],
    ['node', { key: 'S0', name: '身份四要素', label: '身份四要素', state: 'finish', note: '身份四要素核验通过' }],
    ['node', { key: 'S1', name: '显式锚定', label: '显式锚定', state: 'finish', note: '无 @ 锚定——进入下一级' }],
    ['node', { key: 'S5', name: '图扩展', label: '图扩展', state: 'wait', skipped: true, note: '命中即停——本级跳过' }],
    ['node', { key: 'S6', name: '资格裁决', label: '资格裁决', state: 'finish', note: '资格裁决：候选 1 支（上限 4）' }],
    ['node', { key: 'GEN', name: '限定作答＋引用登记', label: '限定作答＋引用登记', state: 'process', tag: '模型第 1 次调用' }],
    ['node_line', { key: 'GEN', mark: '→', text: '模型第 1 次调用——限定作答（只按编号材料作答）' }],
    ['node', { key: 'GEN', name: '限定作答＋引用登记', label: '限定作答＋引用登记', state: 'finish', note: '生成完成——引用登记 2 条' }],
    ['node', { key: 'N17', name: '检索问答', label: '检索问答', state: 'finish', note: '检索问答收束——引用 2 条逐条核验通过' }],
    ['token', { delta: '防砂方式为' }],
    ['token', { delta: '筛管完井。' }],
    ['citation', CITATION_C1],
    ['citation', CITATION_C2],
    ['answer', { kind: 'text', text: '防砂方式为筛管完井。', citations: [CITATION_C1, CITATION_C2] }],
    ['done', {}]
  ]
}

/** 口径两译澄清挂起（流收束不发 done——interrupt）。 */
function askClarifyFrames() {
  return [
    ['session', { run_id: 'run-c1', thread_id: 'sess-c1' }],
    ['stage', { stage: 0 }],
    ['stage', { stage: 1 }],
    ['node', { key: 'N1', name: '统一安检', label: '统一安检', state: 'finish', note: '三道全过——放行' }],
    ['stage', { stage: 2 }],
    ['verdict', { chain: null, slots: '指标＝有效产量', confidence: '低（一词两译未消歧）', need_clarify: true }],
    ['node', { key: 'N5a', name: '澄清帧', label: '澄清帧', state: 'finish', tag: '最多弹一次 · 两跳到终态' }],
    ['clarify', {
      frame_id: 'cf-1', question: '有效产量 → A 开井日历折算 or B 剔除检修？',
      choices: [
        { value: 'A · 开井日历折算', label: '选 A：开井日历折算（含关井日折产，约高 3%）' },
        { value: '默认口径 B', label: '不选了，按默认口径出数并标注', primary: true }
      ]
    }]
  ]
}

/** 低分带改写澄清挂起（P1F-06——clarify 帧 additive subtype 键；链内 S6 弹出，流不发 done）。 */
function askRewriteClarifyFrames(subtype = 'rewrite') {
  return [
    ['session', { run_id: 'run-rw1', thread_id: 'sess-rw1' }],
    ['stage', { stage: 0 }],
    ['stage', { stage: 1 }],
    ['node', { key: 'N1', name: '统一安检', label: '统一安检', state: 'finish', note: '三道全过——放行' }],
    ['stage', { stage: 2 }],
    ['verdict', { chain: '检索问答链', slots: '意图＝注水动态', confidence: '高（检索证据分 0.92）', need_clarify: false }],
    ['stage', { stage: 3 }],
    ['node', { key: 'N17', name: '检索问答', label: '检索问答', state: 'process' }],
    ['node', { key: 'S6', name: '资格裁决', label: '资格裁决', state: 'finish', note: '改写过闸——弹改写澄清帧（两跳到终态）' }],
    ['clarify', {
      frame_id: 'clarify-run-rw1', subtype,
      question: '原问法在报告库里检索把握不足——要不要按优化问法再查一次？\n优化问法：二季度注水月度动态',
      choices: [
        { value: 'rewrite_accept', label: '按优化问法「二季度注水月度动态」作答' },
        { value: 'rewrite_keep', label: '坚持原问法' }
      ]
    }]
  ]
}

/** 澄清续推流（session resume→带参重判→answer→done）。 */
function resumeFrames() {
  return [
    ['session', { run_id: 'run-c1', thread_id: 'sess-c1', resume: true }],
    ['stage', { stage: 0 }],
    ['node', { key: 'N1', name: '统一安检', label: '统一安检', state: 'finish', note: '三道全过——放行' }],
    ['notice', { level: 'info', text: '已按默认口径「剔除检修」锁定并标注——澄清帧有界循环（最多弹一次），两跳到终态。' }],
    ['token', { delta: '按默认口径' }],
    ['token', { delta: '出数并标注。' }],
    ['answer', { kind: 'text', text: '按默认口径出数并标注。' }],
    ['done', {}]
  ]
}

/** done 运行的重连重放流（session resume→verdict→citation×N→answer→done——P1-08c 重放形状）。 */
function replayFrames() {
  return [
    ['session', { run_id: 'run-replay', thread_id: 'sess-replay', resume: true }],
    ['verdict', { chain: '检索问答链', slots: '意图＝防砂方式', confidence: '高（检索证据分 0.62）', need_clarify: false }],
    ['citation', CITATION_C1],
    ['answer', { kind: 'text', text: '防砂方式为筛管完井。', citations: [CITATION_C1] }],
    ['done', {}]
  ]
}

/** 断线收场③（生成已被取消——replay_truncated 收场）。 */
function askTruncatedFrames() {
  return [
    ['session', { run_id: 'run-t1', thread_id: 'sess-t1' }],
    ['stage', { stage: 0 }],
    ['token', { delta: '部分答案' }],
    ['replay_truncated', { message: '回答生成已被取消——以上为重连前的内容，请重新提问。', resume_point: 2 }]
  ]
}

/** 审批 interrupt 挂起（帧族合同注册——approval 帧渲染＋端点 5 决策回流）。 */
function askApprovalFrames() {
  return [
    ['session', { run_id: 'run-ap1', thread_id: 'sess-ap1' }],
    ['stage', { stage: 0 }],
    ['approval', { scene: 'write_op', title: '写操作审批', reason: '待执行台账写入', impact: '影响台账数据' }],
    ['done', {}]
  ]
}

/** @ 资产面板夹具随 apiRouter 内联（端点 6 投影形状——token 结晶体）。 */

const fetchMock = vi.fn()

/** fetch 路由：POST /chat/asks 按问句分路；resume 按挂起 run 回流。 */
function apiRouter(overrides = {}) {
  const calls = { asks: [], resumes: [] }
  fetchMock.mockImplementation(async (url, init) => {
    const u = String(url)
    const method = init?.method || 'GET'
    if (u.includes('/api/chat/asks') && method === 'POST') {
      const body = JSON.parse(init.body || '{}')
      calls.asks.push({ body, headers: init.headers })
      if (body.resume_run_id) return sseResponse(overrides.replayFrames || replayFrames())
      if (overrides.asks) return overrides.asks(body)
      return sseResponse(askFullFrames())
    }
    if (u.includes('/api/chat/runs/') && method === 'POST') {
      calls.resumes.push({ url: u, body: JSON.parse(init.body || '{}') })
      return sseResponse(resumeFrames())
    }
    if (u.includes('/api/chat/sessions') && u.includes('/messages')) {
      return overrides.messages ? overrides.messages(u) : new Response(JSON.stringify({ items: [] }), { status: 200 })
    }
    if (u.includes('/api/chat/sessions')) {
      return overrides.sessions ? overrides.sessions() : new Response('not found', { status: 404 })
    }
    if (u.includes('/api/chat/assets')) {
      return new Response(JSON.stringify({ items: [
        { type: '指标卡', name: '有效产量', token: '指标卡·有效产量' },
        { type: '术语', name: '躺井', token: '术语·躺井' }
      ] }), { status: 200 })
    }
    return new Response(JSON.stringify({ code: 'test_unrouted', message: `unexpected ${method} ${u}` }), { status: 404 })
  })
  return calls
}

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  location.hash = ''
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

async function ask(page, text) {
  fireEvent.change(screen.getByPlaceholderText(/输入问题/), { target: { value: text } })
  fireEvent.click(screen.getByRole('button', { name: /发\s*送/ }))
}

// ════ UI-14 空态巡检（Owner 2026-10-05 意见 1＋2——本机最近运行块条件整显隐） ════

describe('A1 落地页 · UI-14 本机最近运行块整显隐（意见 1＋2）', () => {
  // RUN_HISTORY 为模块级状态且全文件共享——本用例必须置顶先跑（首个 ask 前
  // 模块刚加载、记录为空），「无本机记录」初态才可测。
  it('空时三件套整段零残留（标题/空文案/暂无数据大图均不渲染）；ask 后整段出现', async () => {
    apiRouter()
    render(<A1Landing />)

    // UI-14 翻转：无本机记录时标题「本机最近运行」、空文案「本次进入还没有问答
    // 记录。」、空 List（其默认 Empty「暂无数据」大图）三者一起不渲染
    expect(screen.queryByText('本机最近运行')).toBeNull()
    expect(screen.queryByText('本次进入还没有问答记录。')).toBeNull()
    // UI-16 改：会话列表失败/空库自身合法显示「暂无数据」（仅 1 处——本机块不再贡献第二个）
    expect(screen.getAllByText('暂无数据').length).toBe(1)

    await ask(screen, '首问本机记录')
    await screen.findByText('防砂方式为筛管完井。')
    // ask 后本机记录出现：标题＋列表条目（历史卡内，非对话流用户气泡）
    expect(screen.getByText('本机最近运行')).toBeTruthy()
    const histItem = screen.getAllByText('首问本机记录')
      .map(el => el.closest('.ant-list-item')).find(Boolean)
    expect(histItem).toBeTruthy()
  })
})

describe('A1 落地页 · 思考树与答案流（帧渲染）', () => {
  it('金样本全链：node 四态原位升更新＋skipped 灰显＋note/token 拼贴/置信度徽标/citation 角标', async () => {
    apiRouter()
    render(<A1Landing />)
    await ask(screen, '射孔与防砂参数表里防砂方式是什么？')

    // token 拼贴 → answer 帧收口（同一文本）
    expect(await screen.findByText('防砂方式为筛管完井。')).toBeTruthy()
    // node 按 key 原位升更新：N1 两帧不重复、终态 finish
    const n1 = document.querySelector('[data-node-key="N1"]')
    expect(n1).toBeTruthy()
    expect(n1.dataset.nodeState).toBe('finish')
    expect(document.querySelectorAll('[data-node-key="N1"]')).toHaveLength(1)
    // skipped 灰显＋四态在树
    const s5 = document.querySelector('[data-node-key="S5"]')
    expect(s5.dataset.nodeState).toBe('wait')
    expect(s5.textContent).toContain('已跳过')
    expect(document.querySelector('[data-node-key="GEN"]').dataset.nodeState).toBe('finish')
    // 安检三道逐条翻（第三道 note＝身份）
    expect(screen.getByText('身份与数据域').textContent).toBeTruthy()
    // 裁决帧 → 置信度档位徽标
    expect(screen.getAllByText(/置信度 高（检索证据分 0\.62）/).length).toBeGreaterThanOrEqual(1)
    // node_line 小字
    expect(screen.getByText(/限定作答（只按编号材料作答）/)).toBeTruthy()
    // citation 角标（citation 帧族——ref 去重两枚）
    expect(screen.getByText('证 c1')).toBeTruthy()
    expect(screen.getByText('证 c2')).toBeTruthy()
    // run id + store 会话死槽零写入（UI-01 T7：页面直连端点 2 复拉，store.sessions 写入块已删——
    // 槽位物理清理随共享件清理批，方案 §5-壳层-4 同批性质）
    expect(screen.getByText(/run run-g1/)).toBeTruthy()
    expect(useAppStore.getState().sessions).toEqual([])
  })

  it('FAQ 直出标注（answer.no_model）与兜底标注（未依据报告库）徽标', async () => {
    apiRouter({ asks: body => sseResponse([
      ['session', { run_id: 'run-f1', thread_id: 'sess-f1' }],
      ['verdict', { chain: 'FAQ直出链', slots: '标准问＝N-02 井是什么时候投产的', confidence: '高（FAQ 精确命中——直出）', need_clarify: false }],
      ['token', { delta: '2019-06-15 投产（未依据报告库）' }],
      ['answer', { kind: 'text', no_model: true, text: '2019-06-15 投产（未依据报告库）' }],
      ['done', {}]
    ]) })
    render(<A1Landing />)
    await ask(screen, 'N-02 井是什么时候投产的？')

    expect(await screen.findByText('2019-06-15 投产（未依据报告库）')).toBeTruthy()
    expect(screen.getByText('本条命中 FAQ 直出——未调用模型，无生成过程。')).toBeTruthy()
    expect(screen.getByText('未依据报告库')).toBeTruthy()
    expect(screen.getAllByText(/置信度 高（FAQ 精确命中——直出）/).length).toBeGreaterThanOrEqual(1)
  })
})

describe('A1 落地页 · citation 回跳链路', () => {
  it('角标→出处抽屉：报告引用跳 #/B2?chunk= 定位、图谱跳 #/B5', async () => {
    apiRouter()
    render(<A1Landing />)
    await ask(screen, '防砂方式是什么？')
    await screen.findByText('证 c1')

    fireEvent.click(screen.getByText('证 c1'))
    await screen.findByText('引用别名')
    expect(screen.getByText('出处 1 · N-02 完井报告')).toBeTruthy()
    expect(screen.getByText('f3')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /去切片管理定位/ }))
    expect(location.hash).toBe('#/B2?chunk=f3')

    fireEvent.click(screen.getByText('证 c2'))
    await screen.findByText('出处 2 · 关系图谱')
    fireEvent.click(screen.getByRole('button', { name: /去关系图谱/ }))
    expect(location.hash).toBe('#/B5')
  })

  it('citationJump 链路函数：台账条目族读面预留（无死跳）', () => {
    expect(citationJump({ kind: '报告引用', locator: { fragment_id: 'f3' } })).toEqual({ hash: '/B2?chunk=f3', label: '去切片管理定位' })
    expect(citationJump({ kind: '报告引用', locator: {} })).toEqual({ hash: '/B2', label: '去切片管理' })
    expect(citationJump({ kind: '图谱', locator: {} })).toEqual({ hash: '/B5', label: '去关系图谱' })
    expect(citationJump({ kind: '台账条目', locator: {} })).toBeNull()
  })

  it('confidenceTag 档位徽标（高/中/低→绿/橙/红）', () => {
    expect(confidenceTag('高（检索证据分 0.62）').props.color).toBe('green')
    expect(confidenceTag('中（检索证据分 0.55——直连执行）').props.color).toBe('orange')
    expect(confidenceTag('低（证据不足——低于低分线 0.40）').props.color).toBe('red')
    expect(confidenceTag('')).toBeNull()
  })
})

describe('A1 落地页 · 历史会话回放（端点 3——P1-12 接线）', () => {
  const historySession = {
    id: 'sess-h1', title: 'N-02 井隶属哪个区块?', group: null, scenario_id: null,
    updated_at: '2026-10-02T09:37:03'
  }
  const historyMessages = { items: [
    { id: 'msg-1', role: 'user', text: 'N-02 井隶属哪个区块?', run_id: 'run-h1', answer: null },
    { id: 'msg-2', role: 'assistant', text: '位于渤南区块。', run_id: 'run-h1',
      answer: { kind: 'text', text: '位于渤南区块。', citations: [
        { ref: 'c1', kind: '台账条目', label: '区块归属', locator: { section: '常见问题库' } }
      ] } }
  ] }

  it('点服务端会话→消息折进中栏：轻量条＋user 气泡＋答案卡＋citation 角标开出处抽屉＋返回当前（UI-14 意见 3 镜像）', async () => {
    apiRouter({
      sessions: () => new Response(JSON.stringify({ items: [historySession] }), { status: 200 }),
      messages: () => new Response(JSON.stringify(historyMessages), { status: 200 })
    })
    render(<A1Landing />)
    fireEvent.click(await screen.findByText('N-02 井隶属哪个区块?'))

    // UI-14 翻转：回放大 Alert 换贴顶轻量一行（文案「正在查看历史会话——只读回放。」）
    expect(await screen.findByText('正在查看历史会话——只读回放。')).toBeTruthy()
    expect(await screen.findByText('位于渤南区块。')).toBeTruthy()
    // answer 与 SSE answer 帧同形直出——citation 角标可开出处抽屉（一份 DTO 两处消费）
    fireEvent.click(screen.getByText('证 c1'))
    await screen.findByText('引用别名')
    expect(screen.getByText('区块归属')).toBeTruthy()
    // 返回当前＝退出回放（轻量条消失，回实时会话空态）
    fireEvent.click(screen.getByRole('button', { name: /返回当前/ }))
    expect(screen.queryByText(/正在查看历史会话/)).toBeNull()
    // UI-09：空态教学段删除——回到实时空态以右栏「暂无思考过程。」为标志
    expect(screen.getByText('暂无思考过程。')).toBeTruthy()
  })

  it('回放读取失败内联提示；发送新问题＝退出回放（新会话诚实口径）', async () => {
    apiRouter({
      sessions: () => new Response(JSON.stringify({ items: [historySession] }), { status: 200 }),
      messages: () => new Response(JSON.stringify({ code: 'chat_session_not_found', message: '会话不存在或已过期' }), { status: 404 })
    })
    render(<A1Landing />)
    fireEvent.click(await screen.findByText('N-02 井隶属哪个区块?'))
    expect(await screen.findByText(/读取失败：会话不存在或已过期/)).toBeTruthy()

    // 新提问退出回放（实时对话流接管——asks 照常）
    await ask(screen, '新问题')
    expect(screen.queryByText(/正在查看历史会话/)).toBeNull()
    expect(screen.getByText('新问题')).toBeTruthy()
  })
})

describe('A1 落地页 · 澄清帧交互与 resume 回流', () => {
  it('澄清选项点选→POST /chat/runs/{run}/resume 带参→同一回合续推到 done', async () => {
    const calls = apiRouter({ asks: body => (body.question.includes('有效产量') ? sseResponse(askClarifyFrames()) : sseResponse(askFullFrames())) })
    render(<A1Landing />)
    await ask(screen, '有效产量是多少？')

    expect(await screen.findByText('有效产量 → A 开井日历折算 or B 剔除检修？')).toBeTruthy()
    expect(screen.getByText(/置信度 低（一词两译未消歧）/)).toBeTruthy()
    const primary = screen.getByText('不选了，按默认口径出数并标注')
    expect(primary.closest('button').className).toContain('primary')

    fireEvent.click(screen.getByText('选 A：开井日历折算（含关井日折产，约高 3%）').closest('button'))
    await waitFor(() => expect(calls.resumes).toHaveLength(1))
    expect(calls.resumes[0].url).toBe('/api/chat/runs/run-c1/resume')
    expect(calls.resumes[0].body).toEqual({ kind: 'clarify', choice: 'A · 开井日历折算' })
    // 续推流折进同一回合：answer 出现、已选标注、resume 标识、done 收口
    expect(await screen.findByText('按默认口径出数并标注。')).toBeTruthy()
    expect(screen.getByText(/已选：选 A：开井日历折算/)).toBeTruthy()
    expect(screen.getByText('续推/重放')).toBeTruthy()
    // 澄清按钮随 done 收口禁用（有界循环——两跳到终态）
    expect(screen.getByText('不选了，按默认口径出数并标注').closest('button').disabled).toBe(true)
  })
})

describe('A1 落地页 · 澄清帧 subtype 分支渲染（P1F-06）', () => {
  it('clarifyCardView 分支：rewrite 出专属标题与提示；未知/缺省 subtype 兜底＝既有形状', () => {
    const rewrite = clarifyCardView({ subtype: 'rewrite', question: 'q', choices: [] })
    expect(rewrite.title).toContain('改写澄清')
    expect(rewrite.hint).toContain('优化问法')
    const generic = clarifyCardView({ subtype: 'caliber', question: 'q', choices: [] })
    expect(generic.title).toContain('澄清帧')
    expect(generic.hint).toBe('')
    expect(clarifyCardView({ subtype: 'candidates', question: 'q', choices: [] })).toEqual(generic)
    // 未知 subtype 兜底——同 caliber/candidates 形状（不崩不空白）
    expect(clarifyCardView({ subtype: 'mystery', question: 'q', choices: [] })).toEqual(generic)
    expect(clarifyCardView({ question: 'q', choices: [] })).toEqual(generic) // 缺省＝旧帧兼容
  })

  it('rewrite 分支渲染：专属标题＋提示文案＋两选项按钮；点选回流带 choice 值', async () => {
    const calls = apiRouter({ asks: () => sseResponse(askRewriteClarifyFrames()) })
    render(<A1Landing />)
    await ask(screen, '请帮忙梳理二季度注水开发月度动态并逐月合计对比')

    expect(await screen.findByText(/要不要按优化问法再查一次？/)).toBeTruthy()
    expect(screen.getByText('改写澄清 · 低分带重评（最多弹一次，两跳到终态）')).toBeTruthy()
    expect(screen.getByText(/原问法检索把握不足——可按优化问法重新检索作答；坚持原问法则如实兜底，不硬答。/)).toBeTruthy()
    expect(screen.getByText('按优化问法「二季度注水月度动态」作答')).toBeTruthy()
    expect(screen.getByText('坚持原问法')).toBeTruthy()

    fireEvent.click(screen.getByText('按优化问法「二季度注水月度动态」作答').closest('button'))
    await waitFor(() => expect(calls.resumes).toHaveLength(1))
    expect(calls.resumes[0].body).toEqual({ kind: 'clarify', choice: 'rewrite_accept' })
    expect(await screen.findByText('按默认口径出数并标注。')).toBeTruthy() // 续推流折进同一回合
  })

  it('未知 subtype 兜底渲染：既有形状（澄清帧标题＋问句＋按钮齐），不崩不空白', async () => {
    apiRouter({ asks: () => sseResponse(askRewriteClarifyFrames('mystery')) })
    render(<A1Landing />)
    await ask(screen, '随便问点什么')

    expect(await screen.findByText('澄清帧 · interrupt 挂起（最多弹一次，两跳到终态）')).toBeTruthy()
    expect(screen.queryByText('改写澄清 · 低分带重评（最多弹一次，两跳到终态）')).toBeNull()
    expect(screen.getByText(/原问法在报告库里检索把握不足/)).toBeTruthy()
    expect(screen.getByText('坚持原问法').closest('button')).toBeTruthy()
    expect(screen.getByText('按优化问法「二季度注水月度动态」作答').closest('button')).toBeTruthy()
  })
})

describe('A1 落地页 · 断线收场与重连（端点 4 重连形态）', () => {
  it('replay_truncated 收场话术直出→从断点恢复发 resume_run_id＋Last-Event-ID', async () => {
    const calls = apiRouter({ asks: body => (body.resume_run_id ? sseResponse(replayFrames()) : sseResponse(askTruncatedFrames())) })
    render(<A1Landing />)
    await ask(screen, '油价预测')
    expect(await screen.findByText('回答生成已被取消——以上为重连前的内容，请重新提问。')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '从断点恢复' }))
    await waitFor(() => expect(calls.asks).toHaveLength(2))
    expect(calls.asks[1].body).toEqual({ resume_run_id: 'run-t1' })
    expect(calls.asks[1].headers['Last-Event-ID']).toBe('4')
    // 重放帧折进新回合（session resume 标识——P1-08c 重放语义）
    expect(await screen.findByText('续推/重放')).toBeTruthy()
    expect(await screen.findByText('防砂方式为筛管完井。')).toBeTruthy()
  })

  it('本机运行史（点开＝重连重放）＋服务端会话读口 available 才渲染', async () => {
    const calls = apiRouter({
      asks: body => (body.resume_run_id ? sseResponse(askFullFrames()) : sseResponse(askFullFrames())),
      sessions: () => new Response(JSON.stringify({ items: [{ id: 'sess-9', title: '上个月产量最高的三口井', group: '问数据 · 状态机', scenario_id: 'data-fix', updated_at: '2026-09-27T18:40:00' }] }), { status: 200 })
    })
    render(<A1Landing />)

    // 服务端分组（端点 2 形状直出——P1-12 起会话可点开回放；UI-01 T11 文案撤出裸端点号；UI-09「点会话＝回放」教学行删除）
    expect(await screen.findByText('上个月产量最高的三口井')).toBeTruthy()

    await ask(screen, '再问一次防砂')
    await screen.findByText('防砂方式为筛管完井。')
    // 本机运行史条目（历史卡内，非对话流里的用户气泡）→ 点开＝重连重放
    const histItem = screen.getAllByText('再问一次防砂')
      .map(el => el.closest('.ant-list-item')).find(Boolean)
    expect(histItem).toBeTruthy()
    fireEvent.click(histItem)
    await waitFor(() => expect(calls.asks.length).toBeGreaterThanOrEqual(2))
    expect(calls.asks[calls.asks.length - 1].body).toEqual({ resume_run_id: 'run-g1' })
    expect(await screen.findByText('续推/重放')).toBeTruthy()
  })
})

describe('A1 落地页 · @ 点名辅助（端点 6 assets 投影）', () => {
  it('输入 @ 弹资产面板→过滤→点选落 token 结晶体→anchors 随 asks 上送', async () => {
    const calls = apiRouter()
    render(<A1Landing />)
    const input = screen.getByPlaceholderText(/输入问题/)

    fireEvent.change(input, { target: { value: '帮我查 @' } })
    await screen.findByText('躺井') // 资产行 name（端点 6 投影回填）
    expect(document.querySelector('[data-asset="指标卡·有效产量"]')).toBeTruthy()
    expect(document.querySelector('[data-asset="术语·躺井"]')).toBeTruthy()

    fireEvent.change(input, { target: { value: '帮我查 @躺' } })
    await waitFor(() => expect(document.querySelector('[data-asset="指标卡·有效产量"]')).toBeNull())
    expect(document.querySelector('[data-asset="术语·躺井"]')).toBeTruthy()

    fireEvent.click(document.querySelector('[data-asset="术语·躺井"]'))
    expect(screen.getByPlaceholderText(/输入问题/).value).toBe('帮我查 @术语·躺井 ')

    fireEvent.change(input, { target: { value: '帮我查 @术语·躺井 是什么意思' } })
    fireEvent.click(screen.getByRole('button', { name: /发\s*送/ }))
    await screen.findByText('防砂方式为筛管完井。')
    expect(calls.asks[0].body.anchors).toEqual(['术语·躺井'])
  })
})

describe('A1 帧归约纯函数（不经渲染）', () => {
  it('node 同键两拍合一；token 拼贴；citation 去重；error/replay_truncated 收口', () => {
    let t = newTurn('ask', 'q')
    t = applyFrame(t, { id: '1', event: 'node', data: { key: 'N1', name: '统一安检', state: 'process' } })
    t = applyFrame(t, { id: '2', event: 'node', data: { key: 'N1', name: '统一安检', state: 'finish', note: '放行' } })
    expect(t.nodes).toHaveLength(1)
    expect(t.nodes[0].state).toBe('finish')
    expect(t.nodes[0].note).toBe('放行')

    t = applyFrame(t, { id: '3', event: 'token', data: { delta: '你好' } })
    t = applyFrame(t, { id: '4', event: 'token', data: { delta: '油田' } })
    expect(t.answerText).toBe('你好油田')

    const cit = { ref: 'c1', kind: '报告引用', label: 'L', locator: {} }
    t = applyFrame(t, { id: '5', event: 'citation', data: cit })
    t = applyFrame(t, { id: '6', event: 'citation', data: cit })
    expect(t.citations).toHaveLength(1)

    t = applyFrame(t, { id: '7', event: 'replay_truncated', data: { resume_point: 4 } })
    expect(t.closed).toBe('replay_truncated')
    expect(t.truncMsg).toBe('会话中断，已出内容保留——请重新提问。')
  })
})

// ════ 阶段 1 交互优化（UI-01——方案-阶段1交互优化-20261004 §5-A1＋票面 T1…T16） ════

describe('A1 落地页 · UI-01 交互优化（T1/T2 发送清空＋IME 守卫）', () => {
  it('T1：发送后输入框清空；busy 中回车不发送不清空', async () => {
    const calls = apiRouter()
    render(<A1Landing />)
    const input = screen.getByPlaceholderText(/输入问题/)
    fireEvent.change(input, { target: { value: '测试问题' } })
    fireEvent.click(screen.getByRole('button', { name: /发\s*送/ }))
    // 守卫通过且两条 items 入列后即清空——此刻流仍在读（busy）
    expect(input.value).toBe('')
    expect(input.disabled).toBe(true)
    fireEvent.keyDown(input, { key: 'Enter', keyCode: 13 })
    await screen.findByText('防砂方式为筛管完井。')
    expect(calls.asks).toHaveLength(1) // busy 中回车未新增请求
    expect(input.value).toBe('') // 收场后仍为空串——原样重发路径已断
  })

  it('T2：中文输入法组词回车（isComposing=true）不发送；确认后（false）正常发送', async () => {
    const calls = apiRouter()
    render(<A1Landing />)
    const input = screen.getByPlaceholderText(/输入问题/)
    fireEvent.change(input, { target: { value: '防砂方式是什么' } })
    // 组词确认回车——半截问题不误发
    fireEvent.keyDown(input, { key: 'Enter', keyCode: 13, isComposing: true })
    expect(calls.asks).toHaveLength(0)
    // 物理松键（rc-input keyLock 随 Enter keyUp 释放）＋组合确认后的回车——正常发送
    fireEvent.keyUp(input, { key: 'Enter', keyCode: 13 })
    fireEvent.keyDown(input, { key: 'Enter', keyCode: 13, isComposing: false })
    await screen.findByText('防砂方式为筛管完井。')
    expect(calls.asks).toHaveLength(1)
    expect(calls.asks[0].body.question).toBe('防砂方式是什么')
  })
})

describe('A1 落地页 · UI-01 左栏（T3 封顶＋T5 计数＋T10 收 ?＋T11 新话术＋T15 失败留痕）', () => {
  it('T3/T5：40 条服务端会话——左栏 Card 随行容器拉伸＋body 内滚＋计数「共 40 条」', async () => {
    const many = Array.from({ length: 40 }, (_, i) => ({
      id: `sess-${i}`, title: `会话 ${i}`, group: '问数据', scenario_id: null, updated_at: ''
    }))
    apiRouter({ sessions: () => new Response(JSON.stringify({ items: many }), { status: 200 }) })
    render(<A1Landing />)
    expect(await screen.findByText('会话 39')).toBeTruthy()
    const card = screen.getByText('历史会话').closest('.ant-card')
    expect(card.parentElement.style.height).toBe('100%') // 行容器定高（UI-08：Shell Content flex 定高项，子级百分比可解析）
    expect(card.style.alignSelf).not.toBe('flex-start') // 左卡随行容器拉伸，不再缩为内容高
    expect(card.style.display).toBe('flex')
    expect(card.querySelector('.ant-card-body').style.overflowY).toBe('auto')
    // T5：N=items.length 计数（端点 2 信封无 total——P3 定死合法读法）；「端点 2」撤出可见文案；UI-09 计数改「共 N 条」
    expect(screen.getByText('共 40 条')).toBeTruthy()
    expect(screen.queryByText(/服务端会话（端点 2）/)).toBeNull()
  })

  it('T5：计数形态「共 3 条」——N＝items.length（端点 2 信封无 total；UI-09 去 dev 语汇）', async () => {
    const three = Array.from({ length: 3 }, (_, i) => ({
      id: `s${i}`, title: `会话 ${i}`, group: '', scenario_id: null, updated_at: ''
    }))
    apiRouter({ sessions: () => new Response(JSON.stringify({ items: three }), { status: 200 }) })
    render(<A1Landing />)
    expect(await screen.findByText('共 3 条')).toBeTruthy()
  })

  it('T10：左栏机制说明收进标题 ?（悬停出「服务端留存」；正文该行消失）', async () => {
    apiRouter()
    render(<A1Landing />)
    const titleSpan = screen.getByText('历史会话')
    const titleIcon = within(titleSpan).getByRole('img', { name: 'question-circle' })
    fireEvent.mouseEnter(titleIcon)
    expect(await screen.findByText('会话在服务端留存：连接中断后重新进入，可从历史会话继续，已生成的内容不丢。')).toBeTruthy()
    // 正文该行消失（左栏 body 文本不含该句——Tooltip 内容只在悬停时进 portal）
    const leftCard = screen.getByText('历史会话').closest('.ant-card')
    expect(leftCard.querySelector('.ant-card-body').textContent).not.toContain('会话在服务端留存')
  })

  it('T11：回放提示新话术；「端点 3」「D5 产品化批」撤出全页可见文案', async () => {
    apiRouter({ sessions: () => new Response(JSON.stringify({ items: [{ id: 'sess-9', title: '上个月产量最高的三口井', group: '', scenario_id: null, updated_at: '' }] }), { status: 200 }) })
    render(<A1Landing />)
    expect(await screen.findByText('上个月产量最高的三口井')).toBeTruthy()
    expect(screen.queryByText(/端点 \d/)).toBeNull()
    expect(screen.queryByText(/D5 产品化批/)).toBeNull()
  })

  it('T15（UI-16 改）：服务端会话读失败＝无数据——显示标准「暂无数据」空态，失败长文案不再出现', async () => {
    apiRouter() // 默认 sessions 404 → available=false
    render(<A1Landing />)
    expect(await screen.findByText('暂无数据')).toBeTruthy()
    expect(screen.queryByText(/历史会话暂不可用/)).toBeNull() // 失败长文案废除（Owner 裁决：没有数据则显示暂无数据）
    expect(screen.queryByText(/共 \d+ 条/)).toBeNull() // 失败时无计数行
  })
})

describe('A1 落地页 · UI-01 滚底跟随（T4）', () => {
  it('T4：距底 >80px 新 items 不拽回底部；≤80px 跟随滚底（对话流＋思考树同阈值）', async () => {
    apiRouter()
    render(<A1Landing />)
    // 初始三卡：左（历史会话）/中（问答）/右（思考过程）——先取两处滚动容器再挂桩
    // 中栏定位：改造后中栏补了与左右平行的标题「问答」，原「无标题卡」的定位法失效
    // （那只是旧布局的偶然特征，不是被测行为）。改按标题取，并保留旧法兜底。
    const cards = [...document.querySelectorAll('.ant-card')]
    const midCard = cards.find(c => c.querySelector('.ant-card-head')?.textContent.includes('问答'))
      ?? cards.find(c => !c.querySelector('.ant-card-head'))
    const treeCard = cards.find(c => c.querySelector('.ant-card-head')?.textContent.includes('思考过程'))
    const convEl = midCard.querySelector('.ant-card-body > div')
    const treeEl = [...treeCard.querySelectorAll('.ant-card-body div')].find(d => d.style.overflowY === 'auto')
    expect(convEl).toBeTruthy()
    expect(treeEl).toBeTruthy()
    // 对话流：距底 700px（>80）→ 不跟随
    Object.defineProperty(convEl, 'scrollHeight', { configurable: true, get: () => 1000 })
    Object.defineProperty(convEl, 'clientHeight', { configurable: true, get: () => 300 })
    Object.defineProperty(convEl, 'scrollTop', { configurable: true, get: () => 0 })
    const convScroll = vi.fn()
    convEl.scrollTo = convScroll
    // 思考树：距底 50px（≤80）→ 跟随滚底
    Object.defineProperty(treeEl, 'scrollHeight', { configurable: true, get: () => 500 })
    Object.defineProperty(treeEl, 'clientHeight', { configurable: true, get: () => 300 })
    Object.defineProperty(treeEl, 'scrollTop', { configurable: true, get: () => 150 })
    const treeScroll = vi.fn()
    treeEl.scrollTo = treeScroll

    await ask(screen, '防砂方式是什么？')
    await screen.findByText('防砂方式为筛管完井。')
    expect(convScroll).not.toHaveBeenCalled()
    expect(treeScroll).toHaveBeenCalledWith({ top: 500 })
  })
})

describe('A1 落地页 · UI-01 会话刷新与错误三段化（T7/T8）', () => {
  it('T7：回合收场复拉端点 2 且 available 结果并入左栏；store 死槽零写入', async () => {
    let sessionReads = 0
    apiRouter({
      sessions: () => {
        sessionReads += 1
        const items = sessionReads >= 2
          ? [{ id: 'sess-new', title: '新回合落库会话', group: '', scenario_id: null, updated_at: '' }]
          : []
        return new Response(JSON.stringify({ items }), { status: 200 })
      }
    })
    render(<A1Landing />)
    await waitFor(() => expect(sessionReads).toBe(1)) // 挂载首拉
    expect(screen.queryByText('新回合落库会话')).toBeNull()
    await ask(screen, '再问一次')
    expect(await screen.findByText('新回合落库会话')).toBeTruthy() // 收场复拉并入
    expect(sessionReads).toBeGreaterThanOrEqual(2)
    expect(useAppStore.getState().sessions).toEqual([]) // 死槽写入已删
  })

  it('T8：error 帧三段化（message＋code＋trace）＋hint 有则「｜提示：」尾拼', async () => {
    apiRouter({ asks: () => sseResponse([
      ['session', { run_id: 'run-e1', thread_id: 'sess-e1' }],
      ['error', { code: 'chat_upstream_failed', message: '上游模型调用失败', trace_id: 'tr-abc', hint: '稍后重试或换线路' }]
    ]) })
    render(<A1Landing />)
    await ask(screen, '触发错误帧')
    expect(await screen.findByText(/上游模型调用失败 · code chat_upstream_failed · trace tr-abc｜提示：稍后重试或换线路/)).toBeTruthy()
  })

  it('T8：流开前非 2xx——有 code 走 errText 三段；无 code 拼（HTTP 状态）', async () => {
    let n = 0
    apiRouter({ asks: () => {
      n += 1
      return n === 1
        ? new Response(JSON.stringify({ code: 'chat_rejected', message: '安检拦截', trace_id: 'tr-9' }), { status: 400 })
        : new Response(JSON.stringify({ message: '内部错误' }), { status: 500 })
    } })
    render(<A1Landing />)
    await ask(screen, '第一问')
    expect(await screen.findByText(/安检拦截 · code chat_rejected · trace tr-9/)).toBeTruthy()
    await ask(screen, '第二问')
    expect(await screen.findByText('内部错误（HTTP 500）')).toBeTruthy()
  })
})

describe('A1 落地页 · UI-01 审批驳回反馈（T14）', () => {
  it('T14：空理由点驳回——Input error 态＋红字提示且无网络请求；输入后 error 清除、再点正常回流', async () => {
    const calls = apiRouter({ asks: body => (body.resume_run_id ? sseResponse(replayFrames()) : sseResponse(askApprovalFrames())) })
    render(<A1Landing />)
    await ask(screen, '需要审批的问题')
    expect(await screen.findByText('审批 interrupt · 写操作审批')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /驳\s*回/ })) // antd 两字按钮自动插空格
    expect(calls.resumes).toHaveLength(0) // 空理由不发请求
    const rejectInput = screen.getByPlaceholderText('驳回必写理由（N12）')
    expect(rejectInput.className).toContain('ant-input-status-error')
    expect(screen.getByText('驳回必写理由（N12）')).toBeTruthy() // 红字一行

    fireEvent.change(rejectInput, { target: { value: '不同意该操作' } })
    expect(rejectInput.className).not.toContain('ant-input-status-error') // 输入后清除

    fireEvent.click(screen.getByRole('button', { name: /驳\s*回/ })) // antd 两字按钮自动插空格
    await waitFor(() => expect(calls.resumes).toHaveLength(1))
    expect(calls.resumes[0].body).toEqual({ kind: 'approval', decision: 'reject', reason: '不同意该操作' })
  })
})

describe('A1 落地页 · UI-01 说明收束与 @ 面板（T9/T12）', () => {
  it('T9：底部教学 ? 行删除', async () => {
    apiRouter()
    render(<A1Landing />)
    expect(screen.queryByText(/POST \/api\/chat\/asks/)).toBeNull()
    expect(screen.queryByText(/单一入口/)).toBeNull()
    // UI-09 翻转：右对齐兜底容器连同行内「统一入口」? 整块删除——全部 question-circle 图标中无 flex-end 兜底行者
    const bottomIcon = screen.getAllByRole('img', { name: 'question-circle' })
      .find(i => i.closest('div')?.style.justifyContent === 'flex-end')
    expect(bottomIcon).toBeUndefined()
    expect(screen.queryByText(/安检→装配/)).toBeNull()
  })

  it('T12/T13：@ 面板头去合同行话；hint 死分支删除（行内无 hint 小字）', async () => {
    apiRouter()
    render(<A1Landing />)
    fireEvent.change(screen.getByPlaceholderText(/输入问题/), { target: { value: '帮我查 @' } })
    expect(await screen.findByText('@ 呼唤现成资产（指标卡/术语/FAQ/工作流/报告——被 @ 的资产服务端直接取用）：')).toBeTruthy()
    expect(screen.queryByText(/端点 6/)).toBeNull()
    expect(screen.queryByText(/前门直取/)).toBeNull()
    // T13：api 层 hint 恒空串（死分支已删）——资产行不含 hint 小字节点
    const row = document.querySelector('[data-asset="术语·躺井"]')
    expect(row.textContent).not.toContain('undefined')
  })
})

// ════ L-05 最小披露（D5——verdict intent_source additive 键白名单渲染，同批落地） ════

/** verdict 携 additive intent_source 键的最小帧序（六站链裁决形态；键可缺省＝既有形状）。 */
function askIntentSourceFrames(intentSource) {
  const verdict = {
    chain: '状态机六站链',
    slots: '指标＝日产油量',
    confidence: '高（指标台账命中——数据问句走状态机六站链）',
    need_clarify: false
  }
  if (intentSource) verdict.intent_source = intentSource
  return [
    ['session', { run_id: 'run-l05', thread_id: 'sess-l05' }],
    ['stage', { stage: 0 }],
    ['stage', { stage: 1 }],
    ['verdict', verdict],
    ['done', {}]
  ]
}

describe('A1 落地页 · L-05 最小披露（verdict intent_source 渲染）', () => {
  it('intent_source=llm_plan → 来源行渲染「LLM 精解析（经校验）」', async () => {
    apiRouter({ asks: () => sseResponse(askIntentSourceFrames('llm_plan')) })
    render(<A1Landing />)
    await ask(screen, '去年日产油量最高的井是哪口？')
    expect(await screen.findByText('意图来源：LLM 精解析（经校验）')).toBeTruthy()
  })

  it('intent_source=deterministic → 来源行渲染「确定性解析（快路）」', async () => {
    apiRouter({ asks: () => sseResponse(askIntentSourceFrames('deterministic')) })
    render(<A1Landing />)
    await ask(screen, '各井日产油量排名')
    expect(await screen.findByText('意图来源：确定性解析（快路）')).toBeTruthy()
  })

  it('verdict 无 intent_source 键 → 零变化（不渲染来源行——既有形状不变）', async () => {
    apiRouter({ asks: () => sseResponse(askIntentSourceFrames(null)) })
    render(<A1Landing />)
    await ask(screen, '防砂方式是什么')
    await screen.findByText('置信度 高（指标台账命中——数据问句走状态机六站链）') // verdict 块已渲染（整串精确匹配——链名裸文本节点被多元素包含不可直查）
    expect(screen.queryByText(/意图来源：/)).toBeNull()
  })

  it('intentSourceLine：缺键 null／两值域映射／未知值原样透出（不吞不猜）', () => {
    expect(intentSourceLine(undefined)).toBeNull()
    expect(intentSourceLine(null)).toBeNull()
    expect(intentSourceLine('llm_plan')).toBe('意图来源：LLM 精解析（经校验）')
    expect(intentSourceLine('deterministic')).toBe('意图来源：确定性解析（快路）')
    expect(intentSourceLine('mystery')).toBe('意图来源：mystery')
  })
})
