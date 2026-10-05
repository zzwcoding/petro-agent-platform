/**
 * api/wells 单测（W-A2 接线批）——A2 井档案四端点真 API 接口层：
 * 路径与身份头（X-Dev-User）/ wire(snake)→视图(camel) 折回 / 检修行
 * date_end 仅检修携带的形状保真 / 下拉 option 文案拼装（末段 IW 取备注、
 * EW 取状态——展示层选择）/ 错误包 → ApiError 透传（well_not_found——
 * 页面 inline errText 消费，client 已 toast 页面不重复弹）。
 * 夹具形状照抄 app/api/wells.py 实况（master 04f9606）与 curl spot check
 * 实测原文——空态形状（items:[] total:0）为 raw 无业务数据的验收态。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { setApiNotifier } from './client.js'
import {
  getWellChain, getWellProfile, listWellChangeTickets, listWells, wellOptionLabel
} from './wells.js'

const fetchMock = vi.fn()
const notifier = vi.fn()

beforeEach(() => {
  fetchMock.mockReset()
  notifier.mockReset()
  vi.stubGlobal('fetch', fetchMock)
  setApiNotifier((level, content) => notifier(level, content))
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function jsonResponse(status, body) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('端点 1 listWells 选井下拉列表', () => {
  it('GET /api/wells＋X-Dev-User；wire snake 折回 camel；total 透传', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {
      items: [{
        well_id: 'N-02', well_name: '渤中28-1-N2', well_kind: '采油', well_kind_code: 'EW',
        block_name: '渤南', current_status: '生产中', remark: '正常'
      }],
      total: 1
    }))
    const res = await listWells()
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/wells')
    expect(init.headers['X-Dev-User']).toBeTruthy()
    expect(res.items).toEqual([{
      wellId: 'N-02', wellName: '渤中28-1-N2', wellKind: '采油', wellKindCode: 'EW',
      blockName: '渤南', currentStatus: '生产中', remark: '正常'
    }])
    expect(res.total).toBe(1)
  })

  it('空库空态：items:[] total:0 原样承载（raw 无业务数据——空态验收态）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { items: [], total: 0 }))
    const res = await listWells()
    expect(res.items).toEqual([])
    expect(res.total).toBe(0)
  })
})

describe('端点 2 getWellProfile 档案明细', () => {
  it('路径含井号；kindLabel 拼装「采油（EW）」；qualityNotes/footNote 透传', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {
      well_id: 'N-02', well_name: '渤中28-1-N2', well_kind: '采油', well_kind_code: 'EW',
      first_prod_date: '2019-06-15', platform: 'CEP-A', block_name: '渤南',
      current_status: '生产中', remark: '正常', quality_notes: [], foot_note: null
    }))
    const p = await getWellProfile('N-02')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/wells/N-02')
    expect(p).toMatchObject({
      wellId: 'N-02', wellName: '渤中28-1-N2', kindLabel: '采油（EW）',
      firstProdDate: '2019-06-15', platform: 'CEP-A', blockName: '渤南',
      currentStatus: '生产中', remark: '正常'
    })
    expect(p.qualityNotes).toEqual([])
    expect(p.footNote).toBeNull()
  })

  it('路径参数 encodeURIComponent（防御性编码）；well_name null 保真（「—」渲染归页面）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {
      well_id: 'N-06', well_name: null, well_kind: '注水', well_kind_code: 'IW',
      first_prod_date: '2019-08-01', platform: 'CEP-A', block_name: '渤南',
      current_status: '生产中', remark: '分层注水（3 层）', quality_notes: [],
      foot_note: '注水井无日产油记录，"产量最高"类排名自动排除本井。'
    }))
    const p = await getWellProfile('N 06')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/wells/N%2006')
    expect(p.wellName).toBeNull()
    expect(p.kindLabel).toBe('注水（IW）')
    expect(p.footNote).toContain('注水井无日产油记录')
  })
})

describe('端点 3 getWellChain 关系链', () => {
  it('路径 /chain；events 措施行无 dateEnd、检修行带 dateEnd（形状保真）；'
    + 'overhauls from/to→dateStart/dateEnd；计数与枚举尾注折回', async () => {
    // 夹具＝curl spot check 实测原文（master 04f9606，探针 N-02）
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {
      well_id: 'N-02',
      counts: { events: 2, measures: 1, devices: 2, overhauls: 1, changes: 0 },
      measure_types: ['压裂', '酸化', '补孔', '调剖'],
      device_types: ['电泵', '螺杆泵', '加热炉'],
      measure_foot: '措施类型枚举：压裂 / 酸化 / 补孔 / 调剖',
      device_foot: '设备类型枚举：电泵 / 螺杆泵 / 加热炉',
      events: [
        { key: 'm1', kind: '措施', date: '2026-03-18', title: '调剖 · 主力层段调剖，调整吸水剖面', outcome: '综合含水降 1.2 个点' },
        { key: 'o1', kind: '检修', date: '2024-10-09', date_end: '2024-10-11', title: '检泵（泵轴更换）', outcome: '影响产量约 18 吨 · 批次 20241012-T2' }
      ],
      measures: [
        { key: 'm1', date: '2026-03-18', type: '调剖', content: '主力层段调剖，调整吸水剖面', result: '综合含水降 1.2 个点' }
      ],
      devices: [
        { key: 'd1', type: '电泵', status: '运行中', since: '2021-04-12', note: '2021 年换泵更新；上次保养 2026-06-02' },
        { key: 'd2', type: '加热炉', status: '运行中', since: '2019-09-01', note: '冬季高负荷、夏季低负荷' }
      ],
      overhauls: [
        { key: 'o1', date_start: '2024-10-09', date_end: '2024-10-11', job: '检泵（泵轴更换）', impact: '影响产量约 18 吨', batch: '批次 20241012-T2' }
      ],
      tail: null
    }))
    const c = await getWellChain('N-02')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/wells/N-02/chain')
    expect(c.wellId).toBe('N-02')
    expect(c.counts).toEqual({ events: 2, measures: 1, devices: 2, overhauls: 1, changes: 0 })
    expect(c.measureFoot).toBe('措施类型枚举：压裂 / 酸化 / 补孔 / 调剖')
    expect(c.deviceFoot).toBe('设备类型枚举：电泵 / 螺杆泵 / 加热炉')
    // 服务端已合并排序——接口层原样透传（buildEvents 前端编排整体退役）
    expect(c.events[0]).toEqual({
      key: 'm1', kind: '措施', date: '2026-03-18', dateEnd: undefined,
      title: '调剖 · 主力层段调剖，调整吸水剖面', outcome: '综合含水降 1.2 个点'
    })
    expect(c.events[1].dateEnd).toBe('2024-10-11')
    expect(c.measures[0]).toEqual({ key: 'm1', date: '2026-03-18', type: '调剖', content: '主力层段调剖，调整吸水剖面', result: '综合含水降 1.2 个点' })
    // 设备行真 DTO 无 ok 布尔——status 原样透传（页面按状态映射 Tag 色）
    expect(c.devices[0].status).toBe('运行中')
    expect(c.devices[0]).not.toHaveProperty('ok')
    // from/to → dateStart/dateEnd 改名映射（R-WIRE A2-9）
    expect(c.overhauls[0]).toEqual({
      key: 'o1', dateStart: '2024-10-09', dateEnd: '2024-10-11',
      job: '检泵（泵轴更换）', impact: '影响产量约 18 吨', batch: '批次 20241012-T2'
    })
    expect(c.tail).toBeNull()
  })

  it('空值透传：无冻结文案行 content/result=null 如实携带（页面空值兜底渲染）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {
      well_id: 'N-99', counts: { events: 0, measures: 1, devices: 0, overhauls: 0, changes: 0 },
      measure_types: [], device_types: [],
      measure_foot: '措施类型枚举：压裂 / 酸化 / 补孔 / 调剖',
      device_foot: '设备类型枚举：电泵 / 螺杆泵 / 加热炉',
      events: [{ key: 'm1', kind: '措施', date: '2026-01-01', title: '调剖', outcome: null }],
      measures: [{ key: 'm1', date: '2026-01-01', type: '调剖', content: null, result: null }],
      devices: [], overhauls: [], tail: null
    }))
    const c = await getWellChain('N-99')
    expect(c.measures[0].content).toBeNull()
    expect(c.measures[0].result).toBeNull()
    expect(c.events[0].outcome).toBeNull()
    expect(c.devices).toEqual([])
  })
})

describe('端点 4 listWellChangeTickets 变动投影（A3 只读——V1 端点壳）', () => {
  it('路径 change-tickets；V1 恒空列表（items:[] total:0——A3 主单未建不 mock 假单）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { well_id: 'N-11', items: [], total: 0 }))
    const r = await listWellChangeTickets('N-11')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/wells/N-11/change-tickets')
    expect(r).toEqual({ wellId: 'N-11', items: [], total: 0 })
  })

  it('投影行六字段：status/plane 展示值直传（页面零加工渲染徽标）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, {
      well_id: 'N-11',
      items: [{
        id: '#WB-20260926-05', status: '待审批', plane: '数据面',
        short: 'N-11 台账状态 停产 → 复产待确认（v2）',
        proposer: '《复产确认检查》工作流（账号：复产建议）· v2 已补充含水测算',
        time: '2026-09-26 09:41'
      }],
      total: 1
    }))
    const r = await listWellChangeTickets('N-11')
    expect(r.total).toBe(1)
    expect(r.items[0]).toEqual({
      id: '#WB-20260926-05', status: '待审批', plane: '数据面',
      short: 'N-11 台账状态 停产 → 复产待确认（v2）',
      proposer: '《复产确认检查》工作流（账号：复产建议）· v2 已补充含水测算',
      time: '2026-09-26 09:41'
    })
  })
})

describe('wellOptionLabel 下拉文案拼装（展示层选择——合同端点 1 注记）', () => {
  it('N-02：井名随拼＋末段取状态（采油井）——演示文案照抄种子', () => {
    expect(wellOptionLabel({
      wellId: 'N-02', wellName: '渤中28-1-N2', wellKind: '采油', wellKindCode: 'EW',
      blockName: '渤南', currentStatus: '生产中', remark: '正常'
    })).toBe('N-02 渤中28-1-N2（渤南 · 采油 · 生产中）')
  })

  it('N-06：注水井末段取备注；well_name null 不带名字段', () => {
    expect(wellOptionLabel({
      wellId: 'N-06', wellName: null, wellKind: '注水', wellKindCode: 'IW',
      blockName: '渤南', currentStatus: '生产中', remark: '分层注水（3 层）'
    })).toBe('N-06（渤南 · 注水 · 分层注水（3 层））')
  })

  it('N-11：采油井末段取状态（停产）——备注不抢占', () => {
    expect(wellOptionLabel({
      wellId: 'N-11', wellName: null, wellKind: '采油', wellKindCode: 'EW',
      blockName: '渤中', currentStatus: '停产', remark: '2026-08-30 起检泵'
    })).toBe('N-11（渤中 · 采油 · 停产）')
  })

  it('字段缺省兜底：全 null 不抛——缺段跳过、末段回退「—」', () => {
    expect(wellOptionLabel({
      wellId: 'N-99', wellName: null, wellKind: null, wellKindCode: null,
      blockName: null, currentStatus: null, remark: null
    })).toBe('N-99（—）')
  })
})

describe('错误包透传（well_not_found——A2 错误码草案 404）', () => {
  it('404 → ApiError 携 code/status/traceId；notifier 已弹一次（页面 inline errText 不重复弹）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(404, {
      code: 'well_not_found', message: '井不存在（归一化后无此主键）：N-02', trace_id: 'tr-x1'
    }))
    await expect(getWellProfile('N-02')).rejects.toMatchObject({
      status: 404, code: 'well_not_found', traceId: 'tr-x1'
    })
    expect(notifier).toHaveBeenCalledTimes(1)
  })

  it('网络层失败 → ApiError(0)（页面 Empty 呈现 errText 三段）', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('fetch failed'))
    await expect(getWellChain('N-02')).rejects.toMatchObject({ status: 0 })
  })
})
