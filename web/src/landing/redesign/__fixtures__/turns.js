/**
 * 轮次夹具（测试专用）· 真机帧序列 + 归约器/historyAdapter 输出。
 *
 * 数据来源（eval/results/frames/ 真机帧经 python 抽取为 redesign/__fixtures__/ 夹具，
 * 未改一字；JSON 不带注——来源/拼接全部注于本头注与行尾注；轮内跨帧拼接处逐条注明）：
 *   轮 1 「运行中」：__fixtures__/EB4-A-正1-prefix.json——eval/results/frames/EB4-A-正1.json
 *     的**流式前缀**（信封 id ≤ 25 的全部帧，即首条答案正文帧（id=26）之前的真机现场：
 *     session/text(理解)/notice/step×7/tool(seq7)/observation×16）。问句取该帧文件
 *     blackbox.question（前缀帧内无问句帧）。时长 6.2s ＝夹具计时值（真机实测 18.7s；
 *     真接 SSE 时由前端本地计时——此处只让运行中摘要行的形状与完成态一致）。
 *   轮 2 「完整轮」（数据题）：__fixtures__/EB4-数-明2.json 全帧（128 帧——问句/理解旁白/
 *     正文（含 [51] 引标）/51 条引用/51 支材料/血缘 payload.lineage＋limit/supplement 三块/
 *     verdict verify＋final/blackbox）。跨帧借入（真机帧逐字转录，拼接位＝各帧在原流中的
 *     同部位，见 FULL_FRAMES2 内行尾注）：
 *     · C 级 notice unsupported_claim ← eval/results/frames/EB4-A-正1.json id=1（理解步违约
 *       ——同帧已在前缀夹具内，经 prefixFrames 取用，不重复转录）；
 *     · B 级 notice window_note ← eval/results/frames/P045B20b-C-正5.json id=14（原流位在
 *       材料相位中段；拼接在观察帧列之后——插进观察列会把材料聚合行拆成两行）；
 *     · A 级 notice material_truncated 与 C 级 contradiction_split ← eval/results/frames/
 *       EB4-A-正3.json id=78／id=82（原流位＝正文之后、作答/核验步之间）；
 *     · split 块 ← eval/results/frames/EB4-A-正3.json id=110（明2 自身无 split 块——同批
 *       EB4-A 补齐第四块；supplement 帧不产事件，拼接位排在 citations 块之后）。
 *   轮 3 「分列轮」：__fixtures__/EB3-数-降1.json 全帧（60 帧——长 split 块（1160 字，单条约
 *     350 字含全角空格表格）/引用含 trust=notice 一条（检索供给窗声明，程序声明非文档）/
 *     核验计数）。
 *   轮 4 「旧版历史轮」：__fixtures__/legacy-run-307959ec.json——logs/old-runs-backup-20261014.json
 *     的 run-307959ec（2026-10-13 旧轮）逐字；备份记录无 supplements 键（旧版无此字段），按
 *     RunListItem 旧行语义补 null（→legacy=true）、无 updated_at（适配器不消费，如实缺省）。
 *     走 adaptHistoryTurn 投影（不走归约器）——正文内嵌旧式「引用：」块，无 supplements／
 *     无引用材料（前端按降级态渲染）。
 *
 * 形状：`FIXTURE_TURNS` 条目＝{ id, turn, durationS }——turn 为 FE-01 归约器输出
 * reduceV2Frames(newTurnV2(...), 帧序列)（TurnShape：events 按到达序／supplements 四槽／
 * materials[].payload／verdicts＋verdictFinal／blackbox／runStatus／closed），轮 4 为
 * historyAdapter.adaptHistoryTurn 的输出；id／durationS 是页面临时面（durationS 不入
 * turn——由页面传 RunMetaLine/流水线摘要行）。
 *
 * 消费方＝redesign/ 各组件单测（ExecutionPipeline/CitationPanel/LineageCard/RunMetaLine/
 * CiteHoverCard/cites/events）——页面临时面已切真流（A1V2R），本件只喂测试，页面不引用。
 * （2026-10-17 打磨批②③：中栏追加面与右栏「按来源列出」块退场，split 改由 CitationPanel 内联渲染。）
 */
import { newTurnV2, reduceV2Frames } from '../../a1v2Reducer.js'
import { adaptHistoryTurn } from '../historyAdapter.js'
import legacyListItem from './legacy-run-307959ec.json'
import prefixFrames from './EB4-A-正1-prefix.json'
import fullFrames3 from './EB3-数-降1.json'
import SHU2_ALL from './EB4-数-明2.json'

// ── 轮 2 跨帧借入帧（真机逐字转录——来源文件/信封 id 见头注与行尾注）──

/** C 级 notice unsupported_claim ← eval/results/frames/EB4-A-正1.json id=1（前缀夹具内同帧）。 */
const A1_UNSUPPORTED_CLAIM = prefixFrames.find(f => f.id === 1)

/** B 级 notice window_note ← eval/results/frames/P045B20b-C-正5.json id=14（真机逐字）。 */
const P045_WINDOW_NOTE = { id: 14, event: 'notice', data: { type: 'window_note', gates: [], content: '召回 49 支/送窗 6 支；已召回未送窗 43 支；矛盾来源同窗并立（各留代表支）：《C-渤中34-5油田三季度注水调整与生产运行分析》、《渤中34-8油田一季度注采调整与生产运行分析》、《Y-21井完井工程报告》、《渤中34-8油田躺井治理与检泵作业月报-202701》、《A-W11井完井工程报告》、《B-渤中34-5油田躺井治理与检泵作业月报-202608》' } }

/** A 级 notice material_truncated ← eval/results/frames/EB4-A-正3.json id=78（真机逐字）。 */
const A3_MATERIAL_TRUNCATED = { id: 78, event: 'notice', data: { type: 'material_truncated', gates: [], content: '这次回答只用到检索到的 24/37 条材料——没用上的部分不作答。' } }

/** C 级 notice contradiction_split ← eval/results/frames/EB4-A-正3.json id=82（真机逐字）。 */
const A3_CONTRADICTION_SPLIT = { id: 82, event: 'notice', data: { type: 'contradiction_split', gates: [], content: '多来源不一致——答案分源列明（INV-4——禁止无出处调和）' } }

/** split 块 ← eval/results/frames/EB4-A-正3.json id=110（真机逐字——补齐第四块）。 */
const A3_SPLIT_BLOCK = { id: 110, event: 'supplement', data: { block: 'split', text: '\n\n互不一致——各来源说法如下，按来源分别列出：\n[22] 检索供给窗声明（缺位名单） · window_miss：检索窗注记：缺位来源（预算未及）：《渤中34-8油田一季度注采调整与生产运行分析》\n[43] 检索供给窗声明（缺位名单） · window_miss：检索窗注记：缺位来源（预算未及）：《渤中34-8油田一季度注采调整与生产运行分析》、《渤中34-8油田躺井治理与检泵作业月报-202701》' } }

/** 帧列按信封 id 定位（帧序＝信封到达序；blackbox 与 done 同 id=125——按数组位切，不按 id 查重）。 */
const atId = (frames, id) => frames.findIndex(f => f.id === id)

/** 轮 2 帧序列＝EB4-数-明2 全帧＋借入帧拼接（拼接位＝各借入帧在原流中的同部位，见头注）。 */
const fullFrames2 = [
  ...SHU2_ALL.slice(0, atId(SHU2_ALL, 1)), // session(-1)＋理解旁白 text(id=0)
  A1_UNSUPPORTED_CLAIM, // 借入① EB4-A-正1 id=1——理解步 C 级（原流位：理解旁白之后、决策步之前）
  ...SHU2_ALL.slice(atId(SHU2_ALL, 1), atId(SHU2_ALL, 60)), // 决策步×7→tool(seq8)→observation×51（id 1..59）
  P045_WINDOW_NOTE, // 借入② P045B20b-C-正5 id=14——材料相位中段（观察列后拼接，保材料聚合单行）
  ...SHU2_ALL.slice(atId(SHU2_ALL, 60), atId(SHU2_ALL, 65)), // execute step(seq8)＋正文 text×4（id 60..64）
  A3_MATERIAL_TRUNCATED, // 借入③ EB4-A-正3 id=78——A 级（原流位：正文后、作答步前）
  ...SHU2_ALL.slice(atId(SHU2_ALL, 65), atId(SHU2_ALL, 67)), // 作答步 seq9/seq10（id 65..66）
  A3_CONTRADICTION_SPLIT, // 借入④ EB4-A-正3 id=82——C 级（原流位：起草答案后、verify 前）
  ...SHU2_ALL.slice(atId(SHU2_ALL, 67)), // verify verdict→verify 步→引用×51→三块→收口步→final→blackbox→done（id 67..末）
  A3_SPLIT_BLOCK, // 借入⑤ EB4-A-正3 id=110——split 块（supplement 帧不产事件）
]

/** 问句常量（真源＝各帧文件 blackbox.question——帧流无问句帧，归约器入参逐字取用）。 */
const q1 = 'W-11 井生产套管的尺寸与下深是多少？'
const q2 = '今年各井的日产液量按天列出来'
const q3 = '去年各井含水率是多少？'

/** 测试用轮次夹具（自上而下＝对话流顺序）。turn＝归约器/historyAdapter 产出（TurnShape）。 */
export const FIXTURE_TURNS = [
  { id: 't-live', turn: reduceV2Frames(newTurnV2('ask', q1), prefixFrames), durationS: 6.2 },
  { id: 't-full', turn: reduceV2Frames(newTurnV2('ask', q2), fullFrames2), durationS: 18.5 },
  { id: 't-split', turn: reduceV2Frames(newTurnV2('ask', q3), fullFrames3), durationS: 10.5 },
  { id: 't-legacy', turn: adaptHistoryTurn(legacyListItem, null), durationS: null },
]

/** 轮 2 全帧（真流腿测试直喂 handlers 用——EB4-数-明2 全帧＋借入，同 FIXTURE_TURNS t-full）。 */
export const FULL_FRAMES = fullFrames2

/** 前缀帧（真流腿测试：收口前现场——EB4-A-正1 流式前缀）。 */
export const PREFIX_FRAMES = prefixFrames
