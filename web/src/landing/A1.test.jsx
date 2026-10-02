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
 */

/** @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { applyFrame, confidenceTag, citationJump, newTurn } from './A1.jsx'
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
    // run id + 会话槽（store A1 预留槽接线）
    expect(screen.getByText(/run run-g1/)).toBeTruthy()
    expect(useAppStore.getState().sessions[0]).toEqual({ session_id: 'sess-g1', title: '射孔与防砂参数表里防砂方式是什么？' })
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

  it('点服务端会话→消息折进中栏：横幅＋user 气泡＋答案卡＋citation 角标开出处抽屉＋返回当前', async () => {
    apiRouter({
      sessions: () => new Response(JSON.stringify({ items: [historySession] }), { status: 200 }),
      messages: () => new Response(JSON.stringify(historyMessages), { status: 200 })
    })
    render(<A1Landing />)
    fireEvent.click(await screen.findByText('N-02 井隶属哪个区块?'))

    expect(await screen.findByText(/正在查看历史会话/)).toBeTruthy()
    expect(await screen.findByText('位于渤南区块。')).toBeTruthy()
    // answer 与 SSE answer 帧同形直出——citation 角标可开出处抽屉（一份 DTO 两处消费）
    fireEvent.click(screen.getByText('证 c1'))
    await screen.findByText('引用别名')
    expect(screen.getByText('区块归属')).toBeTruthy()
    // 返回当前＝退出回放（横幅消失，回实时会话空态）
    fireEvent.click(screen.getByRole('button', { name: /返回当前/ }))
    expect(screen.queryByText(/正在查看历史会话/)).toBeNull()
    expect(screen.getByText(/输入问题开始提问/)).toBeTruthy()
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

    // 服务端分组（端点 2 形状直出——P1-12 起会话可点开回放，注记换新口径）
    expect(await screen.findByText('上个月产量最高的三口井')).toBeTruthy()
    expect(screen.getByText(/点会话＝回放消息与答案卡（端点 3）/)).toBeTruthy()

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
