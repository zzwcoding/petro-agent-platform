/**
 * api/quality 单测（W-E2 接线票——模块更名 api/e2 → api/quality 随迁，W-LAND）——mock → 真接口切换的形状闸：
 * - 九函数一一对应 E2-数据质量台.md v0.5 九端点（路径/方法/请求体/查询串）；
 * - PATCH 启停走统一 request（client 无 patch 便捷式）；tasks POST 空体；
 * - issues 拉满 pageSize（V1 整表消费——防预留分页 20 静默截断）＋信封归一化
 *   （page_size → pageSize，lanes 兄弟键保留）；
 * - transitions 流转空体 / rescan 带 {action:"rescan"}；
 * - 错误包路径：422 quality_rule_registered_only（13-20 仅登记档）→ ApiError
 *   且 client 层 toast 一次（页面收口依据——toast 发生在 api 层）。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, setApiNotifier } from './client.js'
import {
  LANES, getFreshness, getQualityRules, getQualityTask, listQualityIssues,
  listQualityTasks, setQualityRuleEnabled, startQualityTask, transitionQualityIssue
} from './quality.js'

const fetchMock = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
  setApiNotifier(null)
})

const json = (status, body) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json' }
})

describe('e2 九端点接线形状（E2 v0.5 合同）', () => {
  it('getQualityRules：GET /quality/rules——items 直传（autoFix 冻结 camelCase）', async () => {
    fetchMock.mockResolvedValueOnce(json(200, {
      items: [{ no: 1, kind: '重复', rule: '…', crit: '…', enabled: true, action: '告警', autoFix: false }]
    }))
    const res = await getQualityRules()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/quality/rules')
    expect(fetchMock.mock.calls[0][1].method).toBe('GET')
    expect(res.items[0].autoFix).toBe(false)
  })

  it('setQualityRuleEnabled：PATCH /quality/rules/{no} 体 {enabled}——统一 request 无便捷式', async () => {
    fetchMock.mockResolvedValueOnce(json(200, { no: 5, enabled: false }))
    const res = await setQualityRuleEnabled(5, false)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/quality/rules/5')
    expect(fetchMock.mock.calls[0][1].method).toBe('PATCH')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ enabled: false })
    expect(res).toEqual({ no: 5, enabled: false })
  })

  it('setQualityRuleEnabled：13-20 仅登记档 422 → ApiError 携 code＋client toast 一次（收口依据）', async () => {
    const notify = vi.fn()
    setApiNotifier(notify)
    fetchMock.mockResolvedValueOnce(json(422, {
      code: 'quality_rule_registered_only', message: '仅登记规则未实施，不可启用', trace_id: 'call-q1'
    }))
    const err = await setQualityRuleEnabled(13, true).catch(e => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err).toMatchObject({ status: 422, code: 'quality_rule_registered_only', traceId: 'call-q1' })
    expect(notify).toHaveBeenCalledTimes(1) // toast 只在 api 层弹——页面 catch 不重复弹
  })

  it('startQualityTask：POST /quality/tasks 空体（202 受理形状由 mock fetch 承接）', async () => {
    fetchMock.mockResolvedValueOnce(json(202, { taskId: 'QT-20261004-01' }))
    const res = await startQualityTask()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/quality/tasks')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
    expect(fetchMock.mock.calls[0][1].body).toBeUndefined()
    expect(res.taskId).toBe('QT-20261004-01')
  })

  it('getQualityTask：GET /quality/tasks/{id}——running/done 两形直传', async () => {
    fetchMock.mockResolvedValueOnce(json(200, { taskId: 'QT-20261004-01', status: 'running', step: 0 }))
    expect(await getQualityTask('QT-20261004-01')).toEqual({ taskId: 'QT-20261004-01', status: 'running', step: 0 })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/quality/tasks/QT-20261004-01')

    fetchMock.mockResolvedValueOnce(json(200, {
      taskId: 'QT-20261004-01', status: 'done',
      task: { id: 'QT-20261004-01', time: '2026-10-04 10:00', rules: 12, hits: 0,
        report: { range: '生产库 8 表', scanned: '0 行', quarantined_rows: 0, rejected_batches: 0, hits: [], verdict: null } }
    }))
    const done = await getQualityTask('QT-20261004-01')
    expect(done.task.report.quarantined_rows).toBe(0) // snake_case 直传（页面渲染层映射）
    expect(done.task.report.rejected_batches).toBe(0)
  })

  it('listQualityTasks：GET /quality/tasks——倒序历史直传', async () => {
    fetchMock.mockResolvedValueOnce(json(200, { items: [] }))
    expect(await listQualityTasks()).toEqual({ items: [] })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/quality/tasks')
  })

  it('listQualityIssues：page/pageSize 拉满查询串＋信封归一化（page_size→pageSize，lanes 保留）', async () => {
    fetchMock.mockResolvedValueOnce(json(200, {
      lanes: ['分发', '认领', '整改', '复核', '关闭'], items: [],
      page: 1, page_size: 500, total: 0
    }))
    const res = await listQualityIssues()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/quality/issues?page=1&pageSize=500')
    expect(res.lanes).toEqual(LANES)
    expect(res.page).toBe(1)
    expect(res.pageSize).toBe(500)
    expect(res.total).toBe(0)
  })

  it('transitionQualityIssue：流转空体；rescan 带 {action:"rescan"}', async () => {
    fetchMock.mockResolvedValueOnce(json(200, { id: 'd1', lane: 1, state: '认领', verify: null }))
    expect(await transitionQualityIssue('d1')).toEqual({ id: 'd1', lane: 1, state: '认领', verify: null })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/quality/issues/d1/transitions')
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({})

    fetchMock.mockResolvedValueOnce(json(200, {
      id: 'd1', lane: 3, state: '复核', verify: { batch: '批次 20261004-T1', note: '复扫全绿' }
    }))
    const rescan = await transitionQualityIssue('d1', 'rescan')
    expect(fetchMock.mock.calls[1][0]).toBe('/api/quality/issues/d1/transitions')
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ action: 'rescan' })
    expect(rescan.verify.note).toBe('复扫全绿')
  })

  it('getFreshness：GET /quality/freshness——空库如实空行', async () => {
    fetchMock.mockResolvedValueOnce(json(200, { items: [] }))
    expect(await getFreshness()).toEqual({ items: [] })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/quality/freshness')
  })

  it('身份桩：X-Dev-User 头随请求注入', async () => {
    fetchMock.mockResolvedValueOnce(json(200, { items: [] }))
    await getQualityRules()
    expect(fetchMock.mock.calls[0][1].headers['X-Dev-User']).toBeTruthy()
  })
})
