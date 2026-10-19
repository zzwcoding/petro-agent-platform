/**
 * V2 问答 API 层（问一问V2 对接——specs/agent-loop.md 三端点）。
 *
 * 流式基座复用 V1 chat.js 的 streamChat（SSE 三行帧同构——00 §6.1）；本层只做
 * 路径与载荷形状差异：
 * - 提问 POST /api/v2/chat/asks：question｜resume_run_id 重连｜question＋followup_run_id
 *   追问（后两者互斥，同在场 409）；
 * - 续推 POST /api/v2/chat/runs/{run_id}/resume：body 必带 kind 判别（澄清
 *   {"kind":"clarify","choice":"<选项原串>"}／审批 {"kind":"approval",
 *   "decision":"approve"|"reject","approval_id":...}）——**续推必须打本端点**，
 *   打回 asks 会 400（真机踩坑实录 2026-10-13）；
 * - 状态读口 GET /api/v2/chat/runs/{run_id} → {status, steps, manifest_digest}。
 *
 * 挂起判定铁律（真机踩坑实录）：V2 挂起后 SSE 流「正常收束」——ask 帧之后照发
 * done 帧。**挂起看 ask 帧，不看 done**；done 只代表本腿流结束。
 */
import { API_BASE, ApiError, authHeaders } from './client.js'
import { streamChat } from './chat.js'

/** 三形态提问（question 必填；resume_run_id 与 followup_run_id 互斥——后端 409）。 */
export function postAskV2(body, handlers, opts = {}) {
  return streamChat({
    path: '/v2/chat/asks',
    body: {
      question: body.question,
      ...(body.resumeRunId ? { resume_run_id: body.resumeRunId } : {}),
      ...(body.followupRunId ? { followup_run_id: body.followupRunId } : {})
    },
    ...handlers,
    ...opts
  })
}

/**
 * 挂起续推（kind 必填判别）。askFrame 传 V2 ask 帧的 frame 载荷
 * （{kind, prompt, options, detail}）；用户选择由页面装配。
 * @param {string} runId 挂起 run
 * @param {{kind:'clarify'|'approval', choice?:string, decision?:'approve'|'reject',
 *          approvalId?:string}} body
 * @param {object} handlers streamChat 五回调
 */
export function postResumeV2(runId, body, handlers, opts = {}) {
  if (!body || !body.kind) throw new TypeError('resume body.kind 必填（clarify|approval）')
  return streamChat({
    path: `/v2/chat/runs/${encodeURIComponent(runId)}/resume`,
    body: {
      kind: body.kind,
      ...(body.choice ? { choice: body.choice } : {}),
      ...(body.decision ? { decision: body.decision } : {}),
      ...(body.approvalId ? { approval_id: body.approvalId } : {})
    },
    ...handlers,
    ...opts
  })
}

/** 从 ask 帧装配续推 body（审批帧 kind=external_table_approval → resume kind=approval）。
 * 输出＝客户端层驼峰形（与 postResumeV2 入参同键——approvalId；上线映射由其后统一做，
 * V2-69 基座接缝勘误：不得直产 snake 键，否则链式调用静默丢审批单号）。 */
export function resumeBodyFromAskFrame(askFrame, chosen) {
  if (askFrame.kind === 'external_table_approval') {
    return {
      kind: 'approval',
      decision: chosen === '驳回' ? 'reject' : 'approve',
      ...(askFrame.detail?.approval_id ? { approvalId: askFrame.detail.approval_id } : {})
    }
  }
  return { kind: 'clarify', choice: chosen }
}

/** 状态读口（run 不存在 404 → ApiError 抛页面内联）。 */
export async function getRunV2(runId) {
  const res = await fetch(`${API_BASE}/v2/chat/runs/${encodeURIComponent(runId)}`, {
    headers: { ...authHeaders() }
  })
  if (!res.ok) {
    let pkg = {}
    try { pkg = await res.json() } catch { /* 空体容错 */ }
    throw new ApiError(res.status, pkg, pkg.message || `查询失败（HTTP ${res.status}）`)
  }
  return res.json()
}

/** 最近任务列表（V2-73 会话历史读口——created_at 降序；V2-142 瘦身：列表行六键
 *  {run_id,question,status,followup_of,created_at,updated_at}＋supplements，全文 answer
 *  不再随行——正文由 `GET /runs/{id}` 的 answer 面供给）。 */
export async function listRunsV2(limit = 20) {
  const res = await fetch(`${API_BASE}/v2/chat/runs?limit=${limit}`, {
    headers: { ...authHeaders() }
  })
  if (!res.ok) {
    let pkg = {}
    try { pkg = await res.json() } catch { /* 空体容错 */ }
    throw new ApiError(res.status, pkg, pkg.message || `查询失败（HTTP ${res.status}）`)
  }
  return res.json()
}
