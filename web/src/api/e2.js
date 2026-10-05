// E2 数据质量台 —— 接口层（真后端接线，W-E2）
// 契约真源：teach-petro-agent/specs/api/E2-数据质量台.md v0.5（九端点——本文件函数与之一一对应）
// 后端实现：app/api/quality.py（M-05a 管理面六端点 ＋ M-05b 任务表轮询通道三端点）
// 约定：一律走 api/client 统一出口（错误包 {code,message,detail,trace_id} 非 2xx 由 client
// 先弹 toast 再抛 ApiError——页面 catch 不重复弹）；分页信封经 unwrapEnvelope 归一化。
// mock 内存 store（RULES 种子/预置问题单/固定报告/假进度）已随接线撤除——
// 规则种子真源＝迁移 0015（本体 M3 投影 20 行，1-12 enabled、13-20 仅登记恒停用）。

import { get, post, request } from './client'

// 问题单五态状态机（设定书 §1/§4）：分发 → 认领 → 整改 → 复核 → 关闭（终态锁定）
// 与后端 domain.LANES 同值（端点 6 响应 lanes 字段同源回显——前端常量仅作渲染骨架）
export const LANES = ['分发', '认领', '整改', '复核', '关闭']

// 问题单列表 pageSize 拉满（合同 v0.5 分页预留——页面五态页签计数/责任岗·规则筛选
// 全量本地呈现，V1 整表消费语义；server 缺省 20 防超 20 张单静默截断）
const ISSUE_PAGE_SIZE = 500

// GET /api/quality/rules —— 规则列表（20 条种子投影，含启用状态/命中动作/自动修分级）
export function getQualityRules() {
  return get('/quality/rules')
}

// PATCH /api/quality/rules/{no} —— 启停；停用＝质检任务跳过、不删规则（审计留痕）
// 规则 13-20 仅登记档拒启用：422 quality_rule_registered_only（M-05a rev F1 档位守卫——错误包 client 已弹）
export function setQualityRuleEnabled(no, enabled) {
  return request(`/quality/rules/${no}`, { method: 'PATCH', body: { enabled } })
}

// POST /api/quality/tasks —— 发起质检任务（202 受理 {taskId}；异步四步走数据面质检通道）
// 同一时刻最多一个任务进行中，重入 409 quality_task_running；重跑只清「分发未认领」动态单（v0.5 在途单保护）
export function startQualityTask() {
  return post('/quality/tasks')
}

// GET /api/quality/tasks/{id} —— 轮询任务进度
// running 形 {taskId,status,step}（step∈0/2/4——受理/数据面报告回/建单分发完成）；
// done 形 {taskId,status,task}（task 含合规报告，quarantined_rows/rejected_batches 为 snake_case）
export function getQualityTask(taskId) {
  return get(`/quality/tasks/${encodeURIComponent(taskId)}`)
}

// GET /api/quality/tasks —— 任务记录列表（倒序，历史保留可回看；running 在途不进列表）
export function listQualityTasks() {
  return get('/quality/tasks')
}

// GET /api/quality/issues —— 问题单列表（lanes＋items＋分页信封 page/pageSize/total）
// 五态页签与责任岗/规则筛选由前端本地呈现（v0.3 表格管理——服务端 lane/rule_no 筛参 V1 不用）
export function listQualityIssues() {
  return get('/quality/issues', { page: 1, pageSize: ISSUE_PAGE_SIZE })
}

// POST /api/quality/issues/{id}/transitions —— 流转到下一态（响应 {id,lane,state,verify}）
// 可选 action:"rescan"＝复核态人工触发复扫（lane 不变，回填 verify；走数据面通道限时轮询，
// 通道超时 501 quality_task_channel_deferred）；终态再流转 409 quality_issue_state；
// 复验未全绿关闭 422 quality_close_not_verified——错误包 client 已弹
export function transitionQualityIssue(id, action) {
  return post(`/quality/issues/${encodeURIComponent(id)}/transitions`, action ? { action } : {})
}

// GET /api/quality/freshness —— 三层数据新鲜度水位（原始/清洗/汇总，承诺 T-1）
// 写权在数据面入湖/加工管道——空库如实空行（不 mock 假水位）
export function getFreshness() {
  return get('/quality/freshness')
}
