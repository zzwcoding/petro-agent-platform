/**
 * 问一问V2 帧归约器（纯函数——单测直喂真事件序列，不经渲染）。
 *
 * V2 SSE 事件词表（11 事件闭世界，三行帧已由 streamChat 解出 {id, event, data}）：
 * session{run_id,resume}｜step{step,seq,title}｜tool{tool,seq,status,message}｜
 * observation{index,source,trust,content}｜citation{index,source,source_id,trust}｜
 * notice{type,gates,content}｜ask{frame{kind,prompt,options,detail},run_id}｜
 * text{content}｜verdict{...核验面}｜blackbox{...收口档案}｜done{run_id}
 * （保留帧 error/replay_truncated 走 streamChat 回调，页面经 closed 字段感知）。
 *
 * 挂起语义（真机踩坑实录）：ask 帧＝run 转 waiting_ask；其后照发 done（本腿流
 * 正常收束）——归约器把 closed 记 'done' 但 runStatus 保持 'waiting_ask'，页面
 * 以 askFrame 在场与否驱动续推 UI，不以 done 判完局。
 *
 * 引擎异常腿（收束语义三分之三）：executor 落库 failed 后 bus 干净收束、桥面照发
 * done（appv2/runtime/executor.py:380-385 发 notice run_failed；api/bridge.py:149-156
 * stream.error 为空即 done）——done 无 ask 帧但 run_failed notice 在场 ⇒ runStatus
 * 'failed' 不判完局（页面锚推进同判据：A1V2.jsx handlers runFailed 旗标）。
 */

/** 空回合（一次提问/一次续推/一次重连＝一个 assistant 回合的帧容器）。 */
export function newTurnV2(kind, question) {
  return {
    kind, // ask | resume | replay
    question,
    runId: '',
    resumed: false, // session.resume=true（重连/续推标识）
    steps: [], // {seq, station, title}——按 seq 原位升更新
    tools: [], // {tool, status, message}——追加
    materials: [], // {index, source, trust, content}——按 index 原位升更新
    notices: [], // {type, gates, content}——追加
    citations: [], // {index, source, source_id, trust}——按 index 原位升更新
    understanding: '', // V2-77 理解旁白（text 帧 kind=understanding——独立渲染灰条，不混入答案）
    answerText: '', // text 帧拼贴（流式——最终答案面）
    verdicts: [], // 核验帧依序（中途 verify＋收口各一）
    blackbox: null,
    askFrame: null, // 挂起帧 {kind,prompt,options,detail}（在场＝等人工）
    runStatus: 'running', // running|waiting_ask|completed|failed
    closed: null // done|error|transport|replay_truncated（流收场形）
  }
}

function _upsertBy(list, key, item) {
  const at = list.findIndex(x => x[key] === item[key])
  if (at < 0) return [...list, item]
  const next = list.slice()
  next[at] = { ...next[at], ...item }
  return next
}

/** 单帧归约（纯——返回新回合对象，不改入参）。未知事件静默忽略（词表闭世界外容错）。 */
export function reduceV2Frame(turn, frame) {
  const data = frame.data ?? {}
  const t = { ...turn }
  switch (frame.event) {
    case 'session':
      t.runId = data.run_id ?? t.runId
      t.resumed = Boolean(data.resume)
      break
    case 'step':
      t.steps = _upsertBy(t.steps, 'seq', {
        seq: data.seq,
        station: data.step ?? '',
        title: data.title ?? ''
      })
      break
    case 'tool':
      t.tools = [...t.tools, {
        tool: data.tool ?? '',
        status: data.status ?? '',
        message: data.message ?? ''
      }]
      break
    case 'observation':
      t.materials = _upsertBy(t.materials, 'index', {
        index: data.index,
        source: data.source ?? '',
        trust: data.trust ?? '',
        content: data.content ?? ''
      })
      break
    case 'citation':
      t.citations = _upsertBy(t.citations, 'index', {
        index: data.index,
        source: data.source ?? '',
        source_id: data.source_id ?? '',
        trust: data.trust ?? ''
      })
      break
    case 'notice':
      t.notices = [...t.notices, {
        type: data.type ?? '',
        gates: data.gates ?? [],
        content: data.content ?? ''
      }]
      break
    case 'ask':
      t.askFrame = data.frame ?? null
      t.runStatus = 'waiting_ask'
      break
    case 'text':
      // V2-77 理解旁白分流：kind=understanding＝理解步旁白——进独立字段渲染灰条，
      // 不再与最终答案同块拼接（后端 graph.py 理解步随行键；无 kind＝答案正文）。
      if (data.kind === 'understanding') {
        t.understanding = t.understanding + (data.content ?? '')
      } else {
        t.answerText = t.answerText + (data.content ?? '')
      }
      break
    case 'verdict':
      t.verdicts = [...t.verdicts, data]
      break
    case 'blackbox':
      t.blackbox = data
      break
    case 'done':
      t.closed = 'done'
      // 收束语义三分：askFrame 在场＝仍等人工（挂起腿收束）；run_failed notice
      // 在场＝引擎异常腿——run 已落库 failed，不判完局（流尾 done 只代表本腿收束）；
      // 其余＝completed。判据与页面锚推进同源（run_failed notice 字面量）
      t.runStatus = t.askFrame ? 'waiting_ask'
        : t.notices.some(n => n.type === 'run_failed') ? 'failed'
          : 'completed'
      break
    case 'error':
      t.closed = 'error'
      t.runStatus = 'failed'
      break
    default:
      break
  }
  return t
}

/** 帧序列归约（reduce 快捷式）。 */
export function reduceV2Frames(turn, frames) {
  return frames.reduce(reduceV2Frame, turn)
}
