/**
 * api/gateway —— D1 模型与线路·真 API 接口层（P0-07）。
 *
 * 与原型树 mock 模块 api/d1.js 的契约函数一一对应（getModels/getGatewayConfig/
 * saveGatewayConfig/getSpendLogs/startDrill/getDrill/listDrills），函数体从
 * mock 状态机换 client 真 HTTP——页面组件得以零改动换数据源。
 *
 * 职责边界：
 * - 只做「wire 形状 → 页面视图形状」的映射，不持有业务数据（mock 只在 d1.js）；
 * - 后端响应按 00 §14-R1 裁决统一 snake_case（D1 册 camel 为合同原稿；P0-05
 *   差异登记第 2 条），本层统一折回 camel，页面列定义与原型同形；
 * - 全部走 api/client（X-Dev-User 注入/错误包解包/分页信封归一化在底座）。
 *
 * 合同：teach-petro-agent/specs/api/D1-模型与线路.md（端点 1–7）。
 */

import { get, post, put } from './client.js'

/** 调用参数四件的允许区间（合同 §2/§2-3；越界后端 400 错误体带字段与区间）。 */
export const PARAM_LIMITS = {
  allowedFails: { min: 1, max: 10 },
  cooldownSeconds: { min: 10, max: 600 },
  numRetries: { min: 0, max: 5 },
  requestTimeout: { min: 5, max: 120 }
}

// ── wire(snake) → 视图(camel) ──

/** @param {Record<string, number>} p 后端 GatewayParamsBody */
function paramsToCamel(p) {
  return {
    allowedFails: p.allowed_fails,
    cooldownSeconds: p.cooldown_seconds,
    numRetries: p.num_retries,
    requestTimeout: p.request_timeout
  }
}

/** @param {Record<string, number>} p 页面 camel 参数 → PUT 体 snake 形 */
function paramsToSnake(p) {
  return {
    allowed_fails: p.allowedFails,
    cooldown_seconds: p.cooldownSeconds,
    num_retries: p.numRetries,
    request_timeout: p.requestTimeout
  }
}

/** 记账流水单行（数据形状红线：token 两整数/耗时毫秒整数/花费元数值——格式化归页面）。 */
function spendRowToCamel(r) {
  return {
    id: r.id,
    time: r.time,
    modelKey: r.model_key,
    alias: r.alias,
    inputTokens: r.input_tokens,
    outputTokens: r.output_tokens,
    firstMs: r.first_ms,
    totalMs: r.total_ms,
    costYuan: r.cost_yuan,
    fallback: Boolean(r.fallback),
    note: r.note || ''
  }
}

/**
 * 演练快照映射（轮询 hook 直连 client，拿到的是 wire 形——页面用本函数
 * 统一折 camel，与 getDrill 出口同形）。
 * @param {any} d GET /gateway/drills/{id} 响应
 */
export function mapDrillSnapshot(d) {
  const result = d.result
  return {
    drillId: d.drill_id,
    status: d.status,
    nodes: (d.nodes || []).map(n => ({ key: n.key, label: n.label, state: n.state, note: n.note || '' })),
    result: result
      ? {
          conclusion: result.conclusion,
          fallback: result.fallback, // 切换留痕（request_alias/failed_deploy…——合同原稿即 snake，JSON 原样展示）
          ledgerRow: result.ledger_row ? spendRowToCamel(result.ledger_row) : null
        }
      : null
  }
}

// ── 契约函数（签名同原型 api/d1.js） ──

/** 端点 1：GET /api/gateway/models —— 模型清单＋网关运行态（响应本就 camel，透传）。 */
export async function getModels() {
  return get('/gateway/models')
}

/** 端点 2：GET /api/gateway/config —— 读取调用参数＋配置文件全文。 */
export async function getGatewayConfig() {
  const d = await get('/gateway/config')
  return { params: paramsToCamel(d.params), yaml: d.yaml }
}

/**
 * 端点 3：PUT /api/gateway/config —— 保存调用参数（写回 models.yaml 并热加载）。
 * 返回保存后服务端快照（以服务端回值为准，不本地拼装）；越界 400 由 client
 * 统一解错误包抛 ApiError（detail 带字段与允许区间）。
 * @param {{allowedFails: number, cooldownSeconds: number, numRetries: number, requestTimeout: number}} params
 */
export async function saveGatewayConfig(params) {
  const d = await put('/gateway/config', { params: paramsToSnake(params) })
  return { params: paramsToCamel(d.params), yaml: d.yaml }
}

/**
 * 端点 4：GET /api/gateway/spend-logs —— 记账流水分页（恒 time 倒序）。
 * @param {{model?: string, range?: string, keyword?: string, page?: number, pageSize?: number}} [q]
 */
export async function getSpendLogs(q = {}) {
  const { model = 'all', range = 'all', keyword = '', page = 1, pageSize = 15 } = q
  const d = await get('/gateway/spend-logs', {
    model, range, keyword, page: String(page), pageSize: String(pageSize)
  })
  const items = Array.isArray(d.items) ? d.items.map(spendRowToCamel) : []
  return { items, total: d.total ?? items.length, page: d.page ?? page, pageSize: d.pageSize ?? pageSize }
}

/** 端点 5：POST /api/gateway/drills —— 受理 202 {drill_id}；重入 409（client 抛 ApiError）。 */
export async function startDrill() {
  const d = await post('/gateway/drills')
  return { drillId: d.drill_id }
}

/** 端点 6：GET /api/gateway/drills/{id} —— 轮询进度与结果（404=任务不存在）。 */
export async function getDrill(drillId) {
  const d = await get(`/gateway/drills/${encodeURIComponent(drillId)}`)
  return mapDrillSnapshot(d)
}

/** 端点 7：GET /api/gateway/drills —— 演练历史 [{id,time,summary}] 倒序。 */
export async function listDrills() {
  const d = await get('/gateway/drills')
  return (Array.isArray(d) ? d : []).map(r => ({ id: r.id, time: r.time, summary: r.summary }))
}
