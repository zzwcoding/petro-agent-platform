/**
 * a1v2Reducer ＋ api/chatV2 钉测（问一问V2 对接基座）。
 *
 * 真事件序列素材（逐字转录，零编造）：eval/results/V2-场景对照-20261013/
 * runs-复测-70b72b/ 三个 jsonl 的 leg=="frame" 行转 {id, event, data}：
 * - ambig.jsonl：run-f39e6707 无挂起直接收口形（37 帧，实测 n_asks=0——无 ask 帧）；
 * - reject.jsonl：run-b951ecc7 澄清挂起形（ask(kind=clarify) 后照发 done；续推腿
 *   收口 notice 实测 type=budget_converged gates=[max_rounds]）；
 * - extable.jsonl：run-46425185 审批挂起形（ask(kind=external_table_approval，
 *   detail.approval_id=precond-s2)→续推腿 approval_recorded）。
 *
 * 素材实测与票面描述三处出入，钉测一律以真实帧为准：
 * ① ambig 无 ask 帧（澄清挂起形实测在 reject 序列第一腿）；② clarify 选项实测
 * 3 条（非 2 条）；③ reject 收口 notice 实测为 budget_converged（素材中无
 * clarify_capped）。挂起腿收束语义（ask 后照发 done→closed='done' 且
 * runStatus 保持 'waiting_ask'）由 reject/extable 两序列共同钉死。
 *
 * chatV2 层：vi.mock streamChat 捕获入参（路径/载荷形状）；getRunV2 走
 * vi.stubGlobal('fetch') 非 2xx→ApiError（同 api/chat.test.js 惯例）。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client.js'
import { streamChat } from '../api/chat.js'
import { getRunV2, postAskV2, postResumeV2, resumeBodyFromAskFrame } from '../api/chatV2.js'
import { newTurnV2, reduceV2Frame, reduceV2Frames } from './a1v2Reducer.js'

vi.mock('../api/chat.js', () => ({ streamChat: vi.fn() }))

// ── 真实帧逐字转录（runs-复测-70b72b 三 jsonl 的 leg=="frame" 行） ──

/** ambig.jsonl 第一腿（run-f39e6707——「有效产量是多少」，无挂起直接收口）。 */
const AMBIG_FRAMES = [
  { id: '0', event: 'session', data: { run_id: 'run-f39e6707', resume: false } },
  { id: '1', event: 'step', data: { step: 'decision', seq: 1, title: '问有效产量是多少。' } },
  { id: '2', event: 'text', data: { content: '问有效产量是多少。' } },
  {
    id: '19',
    event: 'notice',
    data: {
      type: 'window_note',
      gates: [],
      content: '召回 37 支/送窗 11 支；已召回未送窗 26 支；矛盾来源同窗并立（各留代表支）：'
        + '《C-渤中34-5油田三季度注水调整与生产运行分析》、《B-渤中34-5油田躺井治理与检泵作业月报-202608》、'
        + '《A-W11井完井工程报告》、《渤中34-8油田一季度注采调整与生产运行分析》；缺位来源（预算未及）：'
        + '《渤中34-8油田躺井治理与检泵作业月报-202701》、《Y-21井完井工程报告》；'
        + '节级摘要展开节内切片 +5 支（摘要命中→节内补席）'
    }
  },
  { id: '36', event: 'done', data: { run_id: 'run-f39e6707' } }
]

/** reject.jsonl 第一腿（run-b951ecc7——「帮我预测明年油价」，澄清挂起形）。 */
const REJECT_FRAMES = [
  { id: '0', event: 'session', data: { run_id: 'run-b951ecc7', resume: false } },
  { id: '1', event: 'step', data: { step: 'decision', seq: 1, title: '预测明年油价。' } },
  { id: '2', event: 'text', data: { content: '预测明年油价。' } },
  {
    id: '4',
    event: 'ask',
    data: {
      frame: {
        kind: 'clarify',
        prompt: '您的「明年油价预测」不在本系统数据范围——本系统覆盖油田生产台账与报告（产量、注水、井况等），并不接入油价市场预测模型。请确认范围：',
        options: [
          '退出本题——本系统不预测油价',
          '改问油田生产指标（例如明年产量完成率预测／明年递减率走势等）',
          '改问报告事实（例如本月油价相关条款／完井报告中是否提及油价影响）'
        ],
        detail: null
      },
      run_id: 'run-b951ecc7'
    }
  },
  { id: '6', event: 'done', data: { run_id: 'run-b951ecc7' } }
]

/** reject.jsonl 第二腿（续推——body 实录 {kind:'clarify',choice:'退出本题——本系统不预测油价'}）。 */
const REJECT_RESUME_FRAMES = [
  { id: '0', event: 'session', data: { run_id: 'run-b951ecc7', resume: true } },
  {
    id: '6',
    event: 'notice',
    data: {
      type: 'budget_converged',
      gates: ['max_rounds'],
      content: '预算触界收敛（max_rounds）——未完成项：工具（discover/execute）未执行或未取得观察；'
        + '观察（observe）未入栈；核验（verify）/阐述（answer）未执行。未取得可交付观察材料——如实回报，不编造。'
    }
  },
  { id: '11', event: 'done', data: { run_id: 'run-b951ecc7' } }
]

/** extable.jsonl 第一腿 ask 帧的 frame 载荷（逐字——审批挂起形真样本）。 */
const EXTABLE_ASK_FRAME = {
  kind: 'external_table_approval',
  prompt: '子问题 s2 的取数计划引用外部表 erp_well_register——是否批准越集查询？',
  options: ['批准', '驳回'],
  detail: {
    approval_id: 'precond-s2',
    tables: ['erp_well_register'],
    reason: '外表越集审批（前置条件机判定——放行态落 ToolContext）',
    impact: '批准后该表进放行名单（ToolContext），不重排计划',
    declared_tables: ['erp_well_register'],
    detected_tables: ['erp_well_register'],
    miss_declared: []
  }
}

/** extable.jsonl 第一腿（run-46425185——外表越集审批挂起形）。 */
const EXTABLE_FRAMES = [
  { id: '0', event: 'session', data: { run_id: 'run-46425185', resume: false } },
  { id: '5', event: 'step', data: { step: 'decision', seq: 4, title: '前置条件机：s1=pass｜s2=blocked_ask｜s3=pass' } },
  { id: '65', event: 'ask', data: { frame: EXTABLE_ASK_FRAME, run_id: 'run-46425185' } },
  { id: '67', event: 'done', data: { run_id: 'run-46425185' } }
]

/** extable.jsonl 第二腿（续推——body 实录 {kind:'approval',decision:'approve',approval_id:'precond-s2'}）。 */
const EXTABLE_RESUME_FRAMES = [
  { id: '0', event: 'session', data: { run_id: 'run-46425185', resume: true } },
  {
    id: '1',
    event: 'notice',
    data: { type: 'approval_recorded', gates: [], content: '审批单号 precond-s2 已留痕（resume 留痕，可回溯）。' }
  },
  { id: '34', event: 'done', data: { run_id: 'run-46425185' } }
]

// ── 归约器钉测 ──

describe('ambig 真序列（run-f39e6707 无挂起直接收口形）', () => {
  it('runId 非空、done 判完局（无 askFrame→completed）、answerText 非空、notices 类型实测 window_note', () => {
    const fresh = newTurnV2('ask', '有效产量是多少')
    const turn = reduceV2Frames(fresh, AMBIG_FRAMES)
    expect(turn.runId).toBe('run-f39e6707')
    expect(turn.closed).toBe('done')
    expect(turn.askFrame).toBeNull()
    expect(turn.runStatus).toBe('completed') // 无挂起：done 即完局
    expect(turn.answerText).toBe('问有效产量是多少。') // text 帧拼贴（非空）
    expect(turn.notices.map(n => n.type)).toEqual(['window_note']) // 实测仅 window_note
    expect(turn.notices[0].content).toContain('召回 37 支/送窗 11 支')
    // 首个 step 帧原位入列（station＝step 字段）
    expect(turn.steps[0]).toEqual({ seq: 1, station: 'decision', title: '问有效产量是多少。' })
  })

  it('纯函数：归约不改入参回合（reduceV2Frames/reduceV2Frame 均出新对象）', () => {
    const fresh = newTurnV2('ask', '有效产量是多少')
    reduceV2Frames(fresh, AMBIG_FRAMES)
    expect(fresh).toEqual(newTurnV2('ask', '有效产量是多少'))
    const t2 = newTurnV2('ask', '有效产量是多少')
    reduceV2Frame(t2, AMBIG_FRAMES[0])
    expect(t2.runId).toBe('')
  })
})

describe('reject 真序列（run-b951ecc7 澄清挂起形——ask 后照发 done）', () => {
  it('askFrame.kind=clarify 且 options 实测 3 条；done 后 runStatus 保持 waiting_ask（挂起腿收束语义）', () => {
    const turn = reduceV2Frames(newTurnV2('ask', '帮我预测明年油价'), REJECT_FRAMES)
    expect(turn.runId).toBe('run-b951ecc7')
    expect(turn.askFrame).not.toBeNull()
    expect(turn.askFrame.kind).toBe('clarify')
    expect(turn.askFrame.options).toHaveLength(3) // 实测 3 条（票面写 2 条，以真帧为准）
    expect(turn.askFrame.options[0]).toBe('退出本题——本系统不预测油价')
    expect(turn.askFrame.detail).toBeNull()
    expect(turn.closed).toBe('done') // 本腿流正常收束
    expect(turn.runStatus).toBe('waiting_ask') // 不以 done 判完局——ask 帧在场即仍等人工
    expect(turn.answerText).toBe('预测明年油价。')
  })

  it('续推腿（session.resume=true）收口 notice 实测 budget_converged gates=[max_rounds]；无 ask→done 判完局', () => {
    const turn = reduceV2Frames(newTurnV2('resume', '帮我预测明年油价'), REJECT_RESUME_FRAMES)
    expect(turn.resumed).toBe(true)
    expect(turn.notices.map(n => n.type)).toEqual(['budget_converged']) // 实测（票面写 clarify_capped，素材中无）
    expect(turn.notices[0].gates).toEqual(['max_rounds'])
    expect(turn.closed).toBe('done')
    expect(turn.runStatus).toBe('completed')
  })
})

describe('extable 真序列（run-46425185 审批挂起形——挂起腿＋续推腿）', () => {
  it('挂起腿：askFrame.kind=external_table_approval、detail.approval_id=precond-s2、done 后仍 waiting_ask', () => {
    const turn = reduceV2Frames(newTurnV2('ask', '渤海油田各区块的产量，和 erp 井位台账里的坐标对一下'), EXTABLE_FRAMES)
    expect(turn.runId).toBe('run-46425185')
    expect(turn.askFrame.kind).toBe('external_table_approval')
    expect(turn.askFrame.detail.approval_id).toBe('precond-s2')
    expect(turn.askFrame.options).toEqual(['批准', '驳回'])
    expect(turn.steps).toHaveLength(1) // 序列仅一个 step 帧（seq=4）
    expect(turn.steps[0].title).toContain('s2=blocked_ask')
    expect(turn.closed).toBe('done')
    expect(turn.runStatus).toBe('waiting_ask')
  })

  it('续推腿：resumed=true、approval_recorded 留痕 notice 在场、done 判完局', () => {
    const turn = reduceV2Frames(newTurnV2('resume', '渤海油田各区块的产量，和 erp 井位台账里的坐标对一下'), EXTABLE_RESUME_FRAMES)
    expect(turn.resumed).toBe(true)
    expect(turn.notices.map(n => n.type)).toEqual(['approval_recorded'])
    expect(turn.notices[0].content).toContain('precond-s2 已留痕')
    expect(turn.closed).toBe('done')
    expect(turn.runStatus).toBe('completed')
  })
})

describe('materials/citations 同 index 原位去重（upsert 合同——同 index 二发覆盖首帧）', () => {
  // 素材内无真实同 index 二发（各腿 index 均唯一）；两帧字段值均取自真实帧
  // （observation/extable leg2 id=7；citation/ambig id=27·id=28），二发为构造更新帧。
  it('materials：同 index 两帧→数组长 1 且后帧字段覆盖', () => {
    let turn = newTurnV2('resume', '渤海油田各区块的产量，和 erp 井位台账里的坐标对一下')
    turn = reduceV2Frame(turn, {
      id: '7',
      event: 'observation',
      data: {
        index: 53,
        source: '汇总层水位读面',
        content: '新鲜度闸拦停：汇总层数据水位＝2026-08-31（落后 42 天 · 超期）——查询窗「2026-09-13～2026-10-12」'
          + '尚无已出数数据，不返回空数冒充。催办：源表催办走「考核与质量 → 问题单」。',
        trust: 'notice'
      }
    })
    turn = reduceV2Frame(turn, {
      id: '8',
      event: 'observation',
      data: { index: 53, source: '汇总层水位读面', content: '新鲜度闸解除：水位已覆盖查询窗。', trust: 'report' }
    })
    expect(turn.materials).toHaveLength(1) // 同 index 不追加
    expect(turn.materials[0].index).toBe(53) // 原位保留
    expect(turn.materials[0].content).toBe('新鲜度闸解除：水位已覆盖查询窗。') // 后帧 content 覆盖
    expect(turn.materials[0].trust).toBe('report') // 后帧 trust 覆盖
  })

  it('citations：同 index 两帧→数组长 1 且后帧 source_id 覆盖', () => {
    let turn = newTurnV2('ask', '有效产量是多少')
    turn = reduceV2Frame(turn, {
      id: '27',
      event: 'citation',
      data: { index: 1, source: '《C-渤中34-5油田三季度注水调整与生产运行分析》', source_id: 'f51', trust: 'report' }
    })
    turn = reduceV2Frame(turn, {
      id: '28',
      event: 'citation',
      data: { index: 1, source: '《C-渤中34-5油田三季度注水调整与生产运行分析》', source_id: 'ensum-d4687e6c9b68', trust: 'report' }
    })
    expect(turn.citations).toHaveLength(1)
    expect(turn.citations[0].index).toBe(1)
    expect(turn.citations[0].source_id).toBe('ensum-d4687e6c9b68') // 后帧覆盖
    expect(turn.citations[0].source).toBe('《C-渤中34-5油田三季度注水调整与生产运行分析》')
  })
})

describe('未知事件与保留收场（11 事件闭世界容错）', () => {
  it('未知事件（heartbeat）→回合不变（词表外静默忽略）', () => {
    const turn = reduceV2Frame(newTurnV2('ask', '有效产量是多少'), { id: '99', event: 'heartbeat', data: {} })
    expect(turn).toEqual(newTurnV2('ask', '有效产量是多少'))
    expect(turn.closed).toBeNull()
    expect(turn.runStatus).toBe('running')
  })

  it('error 帧→closed=error 且 runStatus=failed', () => {
    const turn = reduceV2Frame(newTurnV2('ask', '有效产量是多少'), {
      id: '9', event: 'error', data: { code: 'chat_stream_failed', message: '流内异常' }
    })
    expect(turn.closed).toBe('error')
    expect(turn.runStatus).toBe('failed')
  })
})

// ── api/chatV2 层（streamChat 打桩捕获入参；fetch 打桩读口） ──

describe('api/chatV2 三端点形状', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    streamChat.mockClear()
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('postAskV2 三形态：question｜resume_run_id｜followup_run_id 互斥键名上送', async () => {
    await postAskV2({ question: '有效产量是多少' })
    expect(streamChat.mock.calls[0][0].path).toBe('/v2/chat/asks')
    expect(streamChat.mock.calls[0][0].body).toEqual({ question: '有效产量是多少' })

    await postAskV2({ question: '有效产量是多少', resumeRunId: 'run-f39e6707' })
    expect(streamChat.mock.calls[1][0].body).toEqual({
      question: '有效产量是多少', resume_run_id: 'run-f39e6707'
    })

    await postAskV2({ question: '有效产量是多少', followupRunId: 'run-46425185' })
    expect(streamChat.mock.calls[2][0].body).toEqual({
      question: '有效产量是多少', followup_run_id: 'run-46425185'
    })
  })

  it('postResumeV2：body.kind 缺失抛 TypeError 且不出网；clarify/approval 两形打 /v2/chat/runs/{id}/resume', async () => {
    expect(() => postResumeV2('r1', {})).toThrow(TypeError)
    expect(() => postResumeV2('r1')).toThrow(TypeError)
    expect(streamChat).not.toHaveBeenCalled()

    await postResumeV2('run-b951ecc7', { kind: 'clarify', choice: '退出本题——本系统不预测油价' })
    expect(streamChat.mock.calls[0][0].path).toBe('/v2/chat/runs/run-b951ecc7/resume')
    expect(streamChat.mock.calls[0][0].body).toEqual({ kind: 'clarify', choice: '退出本题——本系统不预测油价' })

    await postResumeV2('run-46425185', { kind: 'approval', decision: 'approve', approvalId: 'precond-s2' })
    expect(streamChat.mock.calls[1][0].path).toBe('/v2/chat/runs/run-46425185/resume')
    expect(streamChat.mock.calls[1][0].body).toEqual({
      kind: 'approval', decision: 'approve', approval_id: 'precond-s2'
    })
  })

  it('resumeBodyFromAskFrame 双向：审批帧 approve/reject＋澄清帧 choice（输出=客户端驼峰形，链式直连 postResumeV2）', () => {
    // V2-69 基座接缝勘误（子代理上报、已修）：统一客户端层驼峰形——approvalId 由
    // postResumeV2 上线时映射 approval_id，链式调用不再静默丢审批单号。
    expect(resumeBodyFromAskFrame(EXTABLE_ASK_FRAME, '批准')).toEqual({
      kind: 'approval', decision: 'approve', approvalId: 'precond-s2'
    })
    expect(resumeBodyFromAskFrame(EXTABLE_ASK_FRAME, '驳回')).toEqual({
      kind: 'approval', decision: 'reject', approvalId: 'precond-s2'
    })
    // 澄清帧（reject 真帧）——真机 open 腿2 实录 body {kind:'clarify',choice:'退出本题——本系统不预测油价'}
    const clarifyFrame = REJECT_FRAMES[3].data.frame
    expect(resumeBodyFromAskFrame(clarifyFrame, '退出本题——本系统不预测油价')).toEqual({
      kind: 'clarify', choice: '退出本题——本系统不预测油价'
    })
    // 链式钉：helper 输出直连 postResumeV2——wire 侧 approval_id 不丢（mock streamChat 捕获）。
    expect(resumeBodyFromAskFrame(EXTABLE_ASK_FRAME, '批准')).toMatchObject({
      kind: 'approval', decision: 'approve', approvalId: 'precond-s2'
    })
  })

  it('getRunV2：GET /api/v2/chat/runs/{id}；404 抛 ApiError 且 status 正确；200 直读状态面', async () => {
    fetchMock.mockResolvedValueOnce(new Response(
      JSON.stringify({ code: 'chat_run_not_found', message: '运行不存在或已过期：run-404' }),
      { status: 404, headers: { 'Content-Type': 'application/json' } }
    ))
    const err = await getRunV2('run-404').catch(e => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(404)
    expect(err.code).toBe('chat_run_not_found')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v2/chat/runs/run-404')
    expect(fetchMock.mock.calls[0][1].method).toBeUndefined() // GET 缺省

    fetchMock.mockResolvedValueOnce(new Response(
      JSON.stringify({ status: 'running', steps: [], manifest_digest: 'sha256:abc' }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    ))
    expect(await getRunV2('run-46425185')).toEqual({ status: 'running', steps: [], manifest_digest: 'sha256:abc' })
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v2/chat/runs/run-46425185')
  })
})
