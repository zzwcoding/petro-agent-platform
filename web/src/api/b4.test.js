/**
 * api/b4 单测（W-B4 接线批）——B4 报告百科两读端点真 API 接口层：
 * 路径/查询参数与身份头（X-Dev-User）/ wire(snake)→视图(camel) 折回 /
 * claims·glossary_terms·related_objects 三投影折回 / glossaryChipView
 * 卡片展示映射（metric/term 两族——卡字段＝C1 端点 2/3 行同形投影）/
 * loadClaimEvidence 证据弹层懒加载（复用 kb.js listFragments＋
 * getFragmentContext——锚切片不在台账即丢弃，不伪造回链）/
 * 错误包 → ApiError 透传（wiki_not_found——页面 inline errText 消费，
 * client 已 toast 页面不重复弹）。
 * 夹具形状照抄 app/api/wiki.py 实况（master cd9a9c7）与 curl spot check
 * 实测原文——空态形状（items:[] total:0）为 wiki_page 无种子的验收态。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { setApiNotifier } from './client.js'
import {
  getWikiPage, glossaryChipView, listWikiPages, loadClaimEvidence
} from './b4.js'

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

// 夹具＝B4 v0.4 合同端点 1 DTO 演示行（app/api/wiki.py WikiPageListItemBody 同形）
const PAGE_ROW = {
  id: 'wiki-n02-completion',
  title: '《N-02 井完井报告》',
  lib: '完井报告库',
  source_report: { id: 'rpt-n02-completion', doc: '《N-02 井完井报告（英文 · 200 页）》' },
  current_version: 3,
  updated: '2026-09-20',
  status: '字段待核对'
}

describe('端点 1 listWikiPages 目录', () => {
  it('GET /api/wiki/pages＋X-Dev-User；默认 lib=all；source_report 嵌套折回；total 透传', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { items: [PAGE_ROW], total: 1 }))
    const res = await listWikiPages()
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/wiki/pages?lib=all&keyword=')
    expect(init.headers['X-Dev-User']).toBeTruthy()
    expect(res.total).toBe(1)
    expect(res.items).toEqual([{
      id: 'wiki-n02-completion',
      title: '《N-02 井完井报告》',
      lib: '完井报告库',
      sourceReport: { id: 'rpt-n02-completion', doc: '《N-02 井完井报告（英文 · 200 页）》' },
      currentVersion: 3,
      updated: '2026-09-20',
      status: '字段待核对'
    }])
  })

  it('lib/keyword 服务端筛选参数化（R-WIRE B4-4——本地筛选退役）；keyword 过空省传', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { items: [], total: 2 }))
    await listWikiPages({ lib: '完井报告库', keyword: 'N-02' })
    const [url] = fetchMock.mock.calls[0]
    const qs = new URL(url, 'http://localhost').searchParams
    expect(qs.get('lib')).toBe('完井报告库')
    expect(qs.get('keyword')).toBe('N-02')
  })

  it('空库空态：items:[] total:0 原样承载（wiki_page 无种子——空态验收态）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { items: [], total: 0 }))
    const res = await listWikiPages()
    expect(res.items).toEqual([])
    expect(res.total).toBe(0)
  })
})

describe('端点 2 getWikiPage 全文（恒当前版）', () => {
  // 夹具＝B4 v0.4 合同端点 2 DTO 演示形状（content 标记族五族俱全——截取节选）
  const DETAIL = {
    id: 'wiki-n02-completion',
    title: '《N-02 井完井报告》',
    lib: '完井报告库',
    slug: 'wiki-n02-completion',
    digest: 'N-02 井完井报告：渤南区块 CEP-A 平台采油井，2019-06-15 投产，状态生产中。',
    source_report: { id: 'rpt-n02-completion', doc: '《N-02 井完井报告（英文 · 200 页）》' },
    current_version: 3,
    updated: '2026-09-20',
    status: '字段待核对',
    generation_source: '自动重建',
    operator: '系统（入库管线）',
    related_objects: [
      { type: 'well', id: 'N-02', summary: '井名 渤中28-1-N2 · 井别 采油（EW）· 状态 生产中', links: ['#/A2', '#/B5'] }
    ],
    content: '## 概述\n\n本报告为 [[well:N-02]] 井完井报告[[claim:w1-c1]]，涉及 [[term:综合含水率]]。',
    claims: [
      { claim_id: 'w1-c1', text: '井别采油，2019-06-15 投产，状态生产中', evidence_chunk_ids: ['f1'] },
      { claim_id: 'w1-c9', text: '无锚论断', evidence_chunk_ids: [] }
    ],
    glossary_terms: [
      { word: '综合含水率', kind: 'metric', ref_id: 5, card: { slot_name: '综合含水率', def: 'Q_w ÷（Q_o＋Q_w）× 100%', grain: '月', unit: '%', status: ['生效中'], owner: '开发室', source: 'A.2 日产计量＋A.6 化验' } }
    ]
  }

  it('路径含 pageId；元数据/claims/glossary_terms/related_objects 全折回 camel', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, DETAIL))
    const p = await getWikiPage('wiki-n02-completion')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/wiki/pages/wiki-n02-completion')
    expect(p).toMatchObject({
      id: 'wiki-n02-completion',
      title: '《N-02 井完井报告》',
      lib: '完井报告库',
      slug: 'wiki-n02-completion',
      sourceReport: { id: 'rpt-n02-completion', doc: '《N-02 井完井报告（英文 · 200 页）》' },
      currentVersion: 3,
      updated: '2026-09-20',
      status: '字段待核对',
      generationSource: '自动重建',
      operator: '系统（入库管线）',
      content: DETAIL.content
    })
    expect(p.relatedObjects).toEqual([
      { type: 'well', id: 'N-02', summary: '井名 渤中28-1-N2 · 井别 采油（EW）· 状态 生产中', links: ['#/A2', '#/B5'] }
    ])
    expect(p.claims[0]).toEqual({ claimId: 'w1-c1', text: '井别采油，2019-06-15 投产，状态生产中', evidenceChunkIds: ['f1'] })
    expect(p.claims[1].evidenceChunkIds).toEqual([])
    expect(p.glossaryTerms[0]).toEqual({
      word: '综合含水率', kind: 'metric', refId: 5,
      card: DETAIL.glossary_terms[0].card
    })
  })

  it('digest 可空如实透传；路径参数 encodeURIComponent（防御性编码）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { ...DETAIL, digest: null }))
    const p = await getWikiPage('wiki n02')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/wiki/pages/wiki%20n02')
    expect(p.digest).toBeNull()
  })
})

describe('glossaryChipView 台账卡展示映射（R-WIRE B4-10）', () => {
  it('metric：指标口径／ref＝指标台账 #N／extra＝统计粒度＋单位／状态数组折串／source 透传', () => {
    const v = glossaryChipView({
      word: '综合含水率', kind: 'metric', refId: 5,
      card: { slot_name: '综合含水率', def: 'Q_w ÷（Q_o＋Q_w）× 100%', grain: '月', unit: '%', status: ['生效中'], owner: '开发室', source: 'A.2 日产计量＋A.6 化验' }
    })
    expect(v).toEqual({
      word: '综合含水率', kindLabel: '指标口径', def: 'Q_w ÷（Q_o＋Q_w）× 100%',
      status: '生效中', statusColor: 'green', owner: '开发室',
      extra: '统计粒度：月 · 单位 %', ref: '指标台账 #5',
      source: 'A.2 日产计量＋A.6 化验'
    })
  })

  it('term：业务术语／ref＝术语台账 #N／expires_display 组 extra；待裁决状态取橙', () => {
    const v = glossaryChipView({
      word: '递减增油', kind: 'term', refId: 7,
      card: { type: '术语', def: '见指标 10（含口径争议注记）', status: '有效（待联席裁决）', owner: '采油工艺所', expires_display: '2027-03-31' }
    })
    expect(v.kindLabel).toBe('业务术语')
    expect(v.ref).toBe('术语台账 #7')
    expect(v.status).toBe('有效（待联席裁决）')
    expect(v.statusColor).toBe('orange')
    expect(v.extra).toBe('有效期至 2027-03-31')
    expect(v.source).toBeNull()
  })

  it('卡字段缺省兜底：expires_display 缺省 extra 空；未知状态取 default 色', () => {
    const v = glossaryChipView({ word: '剔检产量', kind: 'term', refId: 2, card: { def: '剔除检修井口径', status: '有效' } })
    expect(v.extra).toBe('')
    expect(v.statusColor).toBe('green')
    const odd = glossaryChipView({ word: 'X', kind: 'term', refId: 1, card: { status: '冻结中' } })
    expect(odd.statusColor).toBe('default')
  })
})

describe('loadClaimEvidence 证据弹层懒加载（复用 B2 端点 1/2——mock 更正清单⑨）', () => {
  it('按来源报告整组拉台账过滤锚切片＋逐条父块回捞原文；报告/章节/类型随行', async () => {
    fetchMock.mockImplementation(async url => {
      const u = String(url)
      if (u.startsWith('/api/kb/fragments?')) {
        const qs = new URL(u, 'http://localhost').searchParams
        expect(qs.get('report_id')).toBe('rpt-n02-completion')
        return jsonResponse(200, {
          items: [
            { id: 'f1', report_id: 'rpt-n02-completion', report: '《N-02 井完井报告（英文 · 200 页）》', well: 'N-02', section: '章节 01 井基本情况 ＞ 1.2 投产信息', type: '原文块', hit: 0 },
            { id: 'f2', report_id: 'rpt-n02-completion', report: '《N-02 井完井报告（英文 · 200 页）》', well: null, section: '章节 03 图件 ＞ 图 3-7', type: '图片说明块', hit: 0 }
          ],
          total: 2
        })
      }
      if (u === '/api/kb/fragments/f1/context') {
        return jsonResponse(200, { id: 'f1', type: '原文块', hit: 0, context: 'N-02（渤中28-1-N2）于 2019-06-15 投产。' })
      }
      return jsonResponse(404, { code: 'fragment_not_found', message: `unexpected ${u}` })
    })
    const chunks = await loadClaimEvidence('rpt-n02-completion', ['f1'])
    expect(chunks).toEqual([{
      id: 'f1', report: '《N-02 井完井报告（英文 · 200 页）》',
      section: '章节 01 井基本情况 ＞ 1.2 投产信息', type: '原文块',
      text: 'N-02（渤中28-1-N2）于 2019-06-15 投产。'
    }])
  })

  it('fail-closed：锚切片不在台账（重建后 id 失效）即丢弃——不伪造回链', async () => {
    fetchMock.mockImplementation(async url => {
      if (String(url).startsWith('/api/kb/fragments?')) {
        return jsonResponse(200, { items: [{ id: 'f2', report_id: 'r', report: 'R', well: null, section: 'S', type: '原文块', hit: 0 }], total: 1 })
      }
      if (String(url) === '/api/kb/fragments/f2/context') {
        return jsonResponse(200, { id: 'f2', type: '原文块', hit: 0, context: 'ctx-f2' })
      }
      return jsonResponse(404, { code: 'fragment_not_found', message: 'x' })
    })
    const chunks = await loadClaimEvidence('rpt-x', ['fX', 'f2', 'fY'])
    expect(chunks.map(c => c.id)).toEqual(['f2'])
  })

  it('无锚论断（空 chunkIds）不发起任何请求——返回空数组', async () => {
    const chunks = await loadClaimEvidence('rpt-x', [])
    expect(chunks).toEqual([])
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('错误包透传（wiki_not_found——B4 错误码草案 404）', () => {
  it('404 → ApiError 携 code/status/traceId；notifier 已弹一次（页面 inline errText 不重复弹）', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(404, {
      code: 'wiki_not_found',
      message: '百科页不存在（含 wiki 开关关未生成）：wiki-n02-completion',
      trace_id: 'tr-x1'
    }))
    await expect(getWikiPage('wiki-n02-completion')).rejects.toMatchObject({
      status: 404, code: 'wiki_not_found', traceId: 'tr-x1'
    })
    expect(notifier).toHaveBeenCalledTimes(1)
  })

  it('网络层失败 → ApiError(0)（页面 Empty 呈现 errText 三段）', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('fetch failed'))
    await expect(listWikiPages()).rejects.toMatchObject({ status: 0 })
  })
})
