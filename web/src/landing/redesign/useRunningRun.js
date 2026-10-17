/**
 * useRunningRun · 断线重连接线（FE-03——specs/frontend-redesign.md「行为约定」R1–R4）。
 *
 * 职责（票面伪代码逐字落码）：
 * - R1 持久化：session 帧到达（拿到 run_id）即把 running run_id 写 sessionStorage
 *   （键 `a1v2r:runningRun`，与 A1V2 的 rootId/followup 键隔离）；run 收口清除。
 * - R2 重连：mount 一次 restoreRunning()——读键 → `GET /runs` 行集确认（本进程
 *   注册表语义，listRunsV2(100)）→ 行仍在且 running → 以 `postAskV2({ resumeRunId },
 *   handlers, { lastEventId: '' })` 重连（不带头＝从头全量重放，chat.py:58-87；
 *   重放帧序与 live 一致——transport.md 行为 13，V2 无 replay_truncated 帧）。
 *   重放与提问同一 dispatch 管道：handlers 直进同一 reducer（reduceV2Frame），
 *   不分两路——真流时重放尾巴与新帧天然衔接。
 * - R3 404 终态：开流前 HTTP 404（run 不在服务端缓冲）→ 合成 errorFrame 轮
 *   「本轮已结束或不可达」，不悬挂、不重试（流中途 transport 断≠404，closed='transport'）。
 * - R4 挂起还原：行 status='waiting_ask' → getRunV2 的 pending_ask 经
 *   adaptHistoryTurn 还原挂起卡（键保留）；续答 postResumeV2 本腿新帧直进同一
 *   reducer（同 runId turn 上 upsert，不重启不重放）；收口清键。
 *
 * 收口清键判据（R1「done/error 终态」＋G5 挂起判定铁律「挂起看 ask 帧不看 done」）：
 * done 帧收口时若本腿出现过 ask 帧＝挂起腿收束（run 非终态）——键保留等续答；
 * 否则（done/error/transport）清除。
 *
 * 提问腿（FE-05 发送接线）：页面 send() 走同一套腿管道——`pushAskEntry(question)` 推空
 * TurnShape 新问条，`legHandlers({ entryId, question }, onClosed)` 出流式 handlers 交
 * postAskV2。提问腿按**条目 id** 归位（session 帧之前 runId 未定——重放/续答腿仍按 runId
 * 归位）；收口回调 onClosed 供页面记本地计时（时长不入 TurnShape）。
 *
 * 零真实网络可测：chatV2 四函数经 vi.mock 注入桩（reconnect.test.jsx）。
 */
import { useCallback, useRef, useState } from 'react'
import { ApiError, errText } from '../../api/client.js'
import {
  getRunV2, listRunsV2, postAskV2, postResumeV2, resumeBodyFromAskFrame
} from '../../api/chatV2.js'
import { newTurnV2, reduceV2Frame } from '../a1v2Reducer.js'
import { adaptHistoryTurn } from './historyAdapter.js'

/** running run 持久化键（与 A1V2 的 `a1v2.session`（rootId/followup）隔离——票面伪代码定名）。 */
export const RUNNING_RUN_KEY = 'a1v2r:runningRun'

/** 读持久化 running run（无/损坏 → null；损坏键顺手清——不挡 restore）。 */
export function readRunningRun() {
  try {
    const raw = sessionStorage.getItem(RUNNING_RUN_KEY)
    if (!raw) return null
    const saved = JSON.parse(raw)
    return saved?.runId ? { runId: saved.runId, question: saved.question ?? '' } : null
  } catch {
    sessionStorage.removeItem(RUNNING_RUN_KEY)
    return null
  }
}

/** R1 受理写键（session 帧到达、拿到 run_id）。 */
export function persistRunningRun(runId, question) {
  try {
    sessionStorage.setItem(RUNNING_RUN_KEY, JSON.stringify({ runId, question, at: Date.now() }))
  } catch { /* 无 sessionStorage 环境（隐私模式）静默——持久化是增强面 */ }
}

/** 收口清键（done/error 终态或 404 终态）。 */
export function clearRunningRun() {
  try { sessionStorage.removeItem(RUNNING_RUN_KEY) } catch { /* 同上 */ }
}

/**
 * 会话数组＋重连恢复＋提问腿（新页 A1V2R 的状态核）。
 *
 * @param initialEntries 初始会话条目（[{ id, turn, durationS }]；FE-05 起页面常态为空数组
 *                       ——会话流由提问腿（pushAskEntry）与 restore 推入轮构成）
 * @returns {{ entries, restoredRef, restoreRunning, resumeEntry, pushAskEntry,
 *             dispatchEntryFrame, legHandlers, clearEntries }}
 */
export function useRunningRun(initialEntries = []) {
  const [entries, setEntries] = useState(initialEntries)
  const restoredRef = useRef(false) // mount 一次护栏（页面 useEffect 调 restoreRunning 用）
  const askSeqRef = useRef(0) // 提问腿条目序号（条目 id 稳定——session 帧前 runId 未定）

  /** 追加会话条目（restore 推入——排在本会话已有轮之后）。 */
  const pushEntry = useCallback(entry => {
    setEntries(prev => [...prev, entry])
  }, [])

  /** 条目 upsert（同 id 原位替换——R3 合成轮替换预推的重放壳轮；无则追加）。 */
  const putEntry = useCallback(entry => {
    setEntries(prev => {
      const at = prev.findIndex(e => e.id === entry.id)
      if (at < 0) return [...prev, entry]
      const next = prev.slice()
      next[at] = entry
      return next
    })
  }, [])

  /**
   * 同 runId turn 原位更新（重放/续答帧落回同一轮——不另开新轮）。
   */
  const upsertTurn = useCallback((runId, updater) => {
    setEntries(prev => {
      const at = prev.findIndex(e => e.turn?.runId === runId)
      if (at < 0) return prev
      const next = prev.slice()
      next[at] = { ...next[at], turn: updater(next[at].turn) }
      return next
    })
  }, [])

  /** 本会话流清空（页面「＋新会话」用——退出当前对话；sessionStorage 的 running run 键不动，
   *  服务端 run 照跑——本页只是回到空会话）。 */
  const clearEntries = useCallback(() => {
    setEntries([])
  }, [])

  /** 按条目 id 归约单帧（提问腿用——session 帧之前 runId 未定，条目 id 恒稳定）。 */
  const dispatchEntryFrame = useCallback((entryId, frame) => {
    setEntries(prev => prev.map(e => (e.id === entryId ? { ...e, turn: reduceV2Frame(e.turn, frame) } : e)))
  }, [])

  /** 按条目 id 改 turn（branch 用——提问腿收口形同 upsertTurn）。 */
  const updateEntryTurn = useCallback((entryId, updater) => {
    setEntries(prev => prev.map(e => (e.id === entryId ? { ...e, turn: updater(e.turn) } : e)))
  }, [])

  /** 提问腿入口：推入空 TurnShape 新问条（返回条目 id——帧按 id 归位）。 */
  const pushAskEntry = useCallback(question => {
    askSeqRef.current += 1
    const id = `ask-${askSeqRef.current}`
    setEntries(prev => [...prev, { id, turn: newTurnV2('ask', question), durationS: null }])
    return id
  }, [])

  /**
   * 同一套流式 handlers（提问/重连重放/续答三腿共一管道——票面「一处接线，不分两路」）。
   * 帧（含保留帧 done/error——先过 onFrame）直进 reducer；session 帧＝受理写键（R1）；
   * 收口清键见头注判据。
   *
   * @param target { runId, question } 按 runId 归位（重放/续答腿）｜
   *               { entryId, question } 按条目 id 归位（提问腿）
   * @param onClosed 收口回调（done/error/transport 三腿同闸——提问腿记本地计时用；可选）
   */
  const legHandlers = useCallback((target, onClosed) => {
    const question = target.question ?? ''
    const apply = f => (target.entryId
      ? dispatchEntryFrame(target.entryId, f)
      : upsertTurn(target.runId, t => reduceV2Frame(t, f)))
    const closeTurn = updater => (target.entryId
      ? updateEntryTurn(target.entryId, updater)
      : upsertTurn(target.runId, updater))
    let askSeen = false // 本腿挂起帧在场（done 收口清键的判据——挂起腿 done 非终态）
    return {
      onFrame: f => {
        if (f.event === 'session' && f.data?.run_id) persistRunningRun(f.data.run_id, question)
        if (f.event === 'ask') askSeen = true
        apply(f)
      },
      onDone: () => { if (!askSeen) clearRunningRun(); onClosed?.() },
      onError: () => { clearRunningRun(); onClosed?.() }, // error 帧已过 onFrame（errorFrame/closed 落定）
      onTransportError: () => {
        closeTurn(t => (t.closed ? t : { ...t, closed: 'transport' }))
        clearRunningRun()
        onClosed?.()
      }
    }
  }, [dispatchEntryFrame, updateEntryTurn, upsertTurn])

  /**
   * R2/R3/R4 刷新发现与重连（页面 mount 调一次）。
   * 行不在/已收口 → 清键交历史列；waiting_ask → R4 挂起还原（键保留）；
   * running → 全帧重放重连；开流前 404 → R3 合成终态轮。
   */
  const restoreRunning = useCallback(async () => {
    const saved = readRunningRun()
    if (!saved) return
    const { runId, question } = saved
    try {
      const rows = await listRunsV2(100) // 行集确认（本进程注册表语义——limit 上限 100）
      const row = rows.find(r => r.run_id === runId)
      if (!row) { clearRunningRun(); return } // 已不在行集（重启行集清空等）——交历史列
      if (row.status === 'waiting_ask') {
        // R4 挂起态刷新：pending_ask 还原挂起卡；键保留（等用户续答收口后再清）
        const view = await getRunV2(runId)
        pushEntry({ id: `t-${runId}`, turn: adaptHistoryTurn(row, view), durationS: null })
        return
      }
      if (row.status !== 'running') { clearRunningRun(); return } // 已收口，交历史列
      const turn = newTurnV2('replay', question)
      turn.runId = runId
      turn.resumed = true
      pushEntry({ id: `t-${runId}`, turn, durationS: null })
      // 不带头（lastEventId ''）＝从头全量重放（chat.py:58-87 语义）；重放帧序与 live
      // 完全一致（transport.md 行为 13）→ 同一 reducer 归一出含 events 的完整形状
      await postAskV2({ resumeRunId: runId }, legHandlers({ runId, question }), { lastEventId: '' })
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        // R3：run 不在服务端缓冲——终态灰条，不悬挂不重试（V2 无 replay_truncated 帧）。
        // 同 id 原位替换预推的重放壳轮（该轮单数——壳轮未收到任何帧，让位合成终态轮）
        clearRunningRun()
        putEntry({
          id: `t-${runId}`,
          turn: {
            ...newTurnV2('replay', question),
            runId,
            errorFrame: { code: 'run_unreachable', message: '本轮已结束或不可达' },
            runStatus: 'failed',
            closed: 'error'
          },
          durationS: null
        })
      } else { throw e } // 其他错误走页面既有错误出口，不在本 hook 吞
    }
  }, [legHandlers, putEntry, pushEntry])

  /** R4 续答：挂起卡选项点击 → postResumeV2 本腿新帧直进同一 reducer（同 runId turn upsert）。 */
  const resumeEntry = useCallback((entry, chosen) => {
    const turn = entry?.turn
    if (!turn?.askFrame || !turn.runId) return
    const body = resumeBodyFromAskFrame(turn.askFrame, chosen)
    upsertTurn(turn.runId, t => ({ ...t, askFrame: null })) // 卡让位——本腿帧接续同轮
    Promise.resolve(postResumeV2(turn.runId, body, legHandlers({ runId: turn.runId, question: turn.question })))
      .catch(err => {
        // 开流前错误（409 非挂起/400 形状等）——errorFrame 灰条如实呈现（不静默吞）
        upsertTurn(turn.runId, t => (t.closed ? t : {
          ...t,
          closed: 'error',
          runStatus: 'failed',
          errorFrame: {
            code: err instanceof ApiError ? err.code : 'resume_failed',
            message: err instanceof ApiError ? errText(err) : String(err)
          }
        }))
      })
  }, [legHandlers, upsertTurn])

  return {
    entries, restoredRef, restoreRunning, resumeEntry, pushAskEntry, dispatchEntryFrame, legHandlers,
    clearEntries
  }
}
