/**
 * 问一问V2 重设计（方案 A）· mock 轮次数据——真帧夹具 + 归约器输出（FE-02 归一改造）。
 *
 * 数据来源（eval/results/frames/ 真机帧经 python 抽取为 redesign/__fixtures__/ 夹具，
 * 未改一字；JSON 不带注——来源/拼接全部注于本头注与行尾注；轮内跨帧拼接处逐条注明）：
 *   轮 1 「运行中」：__fixtures__/EB4-A-正1-prefix.json——eval/results/frames/EB4-A-正1.json
 *     的**流式前缀**（信封 id ≤ 25 的全部帧，即首条答案正文帧（id=26）之前的真机现场：
 *     session/text(理解)/notice/step×7/tool(seq7)/observation×16）。问句取该帧文件
 *     blackbox.question（前缀帧内无问句帧）。时长 6.2s ＝ mock 计时值（真机实测 18.7s；
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
 * 形状：`MOCK_TURNS` 条目＝{ id, turn, durationS }——turn 为 FE-01 归约器输出
 * reduceV2Frames(newTurnV2(...), 帧序列)（TurnShape：events 按到达序／supplements 四槽／
 * materials[].payload／verdicts＋verdictFinal／blackbox／runStatus／closed），轮 4 为
 * historyAdapter.adaptHistoryTurn 的输出；id／durationS 是页面临时面（durationS 不入
 * turn——由页面传 RunMetaLine/流水线摘要行）。
 *
 * 左栏行：`MOCK_RUNS`（120 条 RunListItem 形态——供 ThreadList 的上拉加载/搜索；不受
 * 本票归一改造影响，原样保留）。
 *
 * DEBT(docs/runtime-refactor/frontend-redesign-设计.md)：本文件只服务「mock 静态页对版面」
 * 施工段（数据已改真帧夹具＋归约器输出）；真流页面（FE-05）接线后本文件随 mock 页一并
 * 删除或收缩为纯夹具引用。
 */
import { newTurnV2, reduceV2Frames } from '../a1v2Reducer.js'
import { adaptHistoryTurn } from './historyAdapter.js'
import legacyListItem from './__fixtures__/legacy-run-307959ec.json'
import prefixFrames from './__fixtures__/EB4-A-正1-prefix.json'
import fullFrames3 from './__fixtures__/EB3-数-降1.json'
import SHU2_ALL from './__fixtures__/EB4-数-明2.json'

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

/** 左侧历史对话的 mock 运行行（形态＝后端 `GET /api/v2/chat/runs` 的 RunListItem：
 *  run_id/question/status/followup_of/created_at/updated_at）。**120 条**＝为让「初始 20 / 上拉 +20 /
 *  100 封顶」三态可见可测；问句取真机 `blackbox.question` 轮换（不发明业务问句），状态按
 *  completed/waiting_ask/failed 轮换（让行状态位有样本），created_at 自 2026-10-17 09:20 起按
 *  47 分钟步进回溯（前三行＝中栏三轮的真实时刻）。run_id 为确定性假 hex。 */
export const MOCK_RUNS = [
  { run_id: 'run-9e3779b1', question: 'W-11 井生产套管的尺寸与下深是多少？', status: 'running', followup_of: '', created_at: '2026-10-17 09:20:00', updated_at: '2026-10-17 09:20:42' },
  { run_id: 'run-3c6ef363', question: '今年各井的日产液量按天列出来', status: 'completed', followup_of: '', created_at: '2026-10-17 09:12:00', updated_at: '2026-10-17 09:12:42' },
  { run_id: 'run-daa66d14', question: '去年各井含水率是多少？', status: 'completed', followup_of: 'run-3c6ef363', created_at: '2026-10-17 09:10:00', updated_at: '2026-10-17 09:10:42' },
  { run_id: 'run-78dde6c6', question: '11 月和 12 月的配注是怎么安排的？', status: 'completed', followup_of: '', created_at: '2026-10-17 08:13:00', updated_at: '2026-10-17 08:13:42' },
  { run_id: 'run-17156078', question: 'N-01 井去年的日产油量是多少？', status: 'waiting_ask', followup_of: '', created_at: '2026-10-17 07:26:00', updated_at: '2026-10-17 07:26:42' },
  { run_id: 'run-b54cda29', question: 'N-02 井是什么时候投产的？', status: 'completed', followup_of: 'run-17156078', created_at: '2026-10-17 06:39:00', updated_at: '2026-10-17 06:39:42' },
  { run_id: 'run-538453db', question: 'W-11 井的造斜点在多少米？', status: 'failed', followup_of: '', created_at: '2026-10-17 05:52:00', updated_at: '2026-10-17 05:52:42' },
  { run_id: 'run-f1bbcd8c', question: 'W-11 井生产套管的尺寸与下深是多少？', status: 'completed', followup_of: '', created_at: '2026-10-17 05:05:00', updated_at: '2026-10-17 05:05:42' },
  { run_id: 'run-8ff3473e', question: 'W-11 井投产后预计躺井率是多少？', status: 'completed', followup_of: 'run-f1bbcd8c', created_at: '2026-10-17 04:18:00', updated_at: '2026-10-17 04:18:42' },
  { run_id: 'run-2e2ac0f0', question: 'W-21 井的检泵周期和作业费用各是多少？', status: 'completed', followup_of: '', created_at: '2026-10-17 03:31:00', updated_at: '2026-10-17 03:31:42' },
  { run_id: 'run-cc623aa1', question: 'W-32 井“检泵周期”栏的 215 天是什么口径？', status: 'completed', followup_of: '', created_at: '2026-10-17 02:44:00', updated_at: '2026-10-17 02:44:42' },
  { run_id: 'run-6a99b453', question: 'W-33 井酸化措施的效果四要素？', status: 'completed', followup_of: 'run-cc623aa1', created_at: '2026-10-17 01:57:00', updated_at: '2026-10-17 01:57:42' },
  { run_id: 'run-08d12e05', question: 'W-45 井现在的泵效是多少？', status: 'waiting_ask', followup_of: '', created_at: '2026-10-17 01:10:00', updated_at: '2026-10-17 01:10:42' },
  { run_id: 'run-a708a7b6', question: 'W-57 井的吸水剖面各层占比是多少？', status: 'completed', followup_of: '', created_at: '2026-10-17 00:23:00', updated_at: '2026-10-17 00:23:42' },
  { run_id: 'run-45402168', question: '本月各井日产油量是多少？', status: 'failed', followup_of: 'run-a708a7b6', created_at: '2026-10-16 23:36:00', updated_at: '2026-10-16 23:36:42' },
  { run_id: 'run-e3779b19', question: '本月执行的三项躺井治理措施是什么？', status: 'completed', followup_of: '', created_at: '2026-10-16 22:49:00', updated_at: '2026-10-16 22:49:42' },
  { run_id: 'run-81af14cb', question: '渤中 34-5 油田三季度注采比是多少？', status: 'completed', followup_of: '', created_at: '2026-10-16 22:02:00', updated_at: '2026-10-16 22:02:42' },
  { run_id: 'run-1fe68e7d', question: '杆断的是哪几口井？平均检泵周期多少？', status: 'completed', followup_of: 'run-81af14cb', created_at: '2026-10-16 21:15:00', updated_at: '2026-10-16 21:15:42' },
  { run_id: 'run-be1e082e', question: '各井日产油量排名', status: 'completed', followup_of: '', created_at: '2026-10-16 20:28:00', updated_at: '2026-10-16 20:28:42' },
  { run_id: 'run-5c5581e0', question: '各井日产油量是多少？', status: 'completed', followup_of: '', created_at: '2026-10-16 19:41:00', updated_at: '2026-10-16 19:41:42' },
  { run_id: 'run-fa8cfb91', question: '今年各井的日产液量按天列出来', status: 'waiting_ask', followup_of: 'run-5c5581e0', created_at: '2026-10-16 18:54:00', updated_at: '2026-10-16 18:54:42' },
  { run_id: 'run-98c47543', question: '近 7 天各井日产液量是多少？', status: 'completed', followup_of: '', created_at: '2026-10-16 18:07:00', updated_at: '2026-10-16 18:07:42' },
  { run_id: 'run-36fbeef5', question: '近三年 8 月平均检泵周期的变化趋势？', status: 'failed', followup_of: '', created_at: '2026-10-16 17:20:00', updated_at: '2026-10-16 17:20:42' },
  { run_id: 'run-d53368a6', question: '老完成率是多少？', status: 'completed', followup_of: 'run-36fbeef5', created_at: '2026-10-16 16:33:00', updated_at: '2026-10-16 16:33:42' },
  { run_id: 'run-736ae258', question: '两口欠注井分别是什么原因、什么对策？', status: 'completed', followup_of: '', created_at: '2026-10-16 15:46:00', updated_at: '2026-10-16 15:46:42' },
  { run_id: 'run-11a25c0a', question: '邻井 W-07 井初期日产油多少？现在呢？', status: 'completed', followup_of: '', created_at: '2026-10-16 14:59:00', updated_at: '2026-10-16 14:59:42' },
  { run_id: 'run-afd9d5bb', question: '去年各井含水率是多少？', status: 'completed', followup_of: 'run-11a25c0a', created_at: '2026-10-16 14:12:00', updated_at: '2026-10-16 14:12:42' },
  { run_id: 'run-4e114f6d', question: '去年各井每天的日产油量是多少？', status: 'completed', followup_of: '', created_at: '2026-10-16 13:25:00', updated_at: '2026-10-16 13:25:42' },
  { run_id: 'run-ec48c91e', question: '去年各井每天的油压是多少？', status: 'waiting_ask', followup_of: '', created_at: '2026-10-16 12:38:00', updated_at: '2026-10-16 12:38:42' },
  { run_id: 'run-8a8042d0', question: '去年各井配产量是多少？', status: 'completed', followup_of: 'run-ec48c91e', created_at: '2026-10-16 11:51:00', updated_at: '2026-10-16 11:51:42' },
  { run_id: 'run-28b7bc82', question: '去年日产液量最高的井是哪口？', status: 'failed', followup_of: '', created_at: '2026-10-16 11:04:00', updated_at: '2026-10-16 11:04:42' },
  { run_id: 'run-c6ef3633', question: '去年日产油量排名前 30', status: 'completed', followup_of: '', created_at: '2026-10-16 10:17:00', updated_at: '2026-10-16 10:17:42' },
  { run_id: 'run-6526afe5', question: '去年日产油量最低的两口井是哪两口？', status: 'completed', followup_of: 'run-c6ef3633', created_at: '2026-10-16 09:30:00', updated_at: '2026-10-16 09:30:42' },
  { run_id: 'run-035e2997', question: '去年日产油量最高的井是哪口？', status: 'completed', followup_of: '', created_at: '2026-10-16 08:43:00', updated_at: '2026-10-16 08:43:42' },
  { run_id: 'run-a195a348', question: '全油田全年躺井率控制目标是多少？', status: 'completed', followup_of: '', created_at: '2026-10-16 07:56:00', updated_at: '2026-10-16 07:56:42' },
  { run_id: 'run-3fcd1cfa', question: '三季度产量完成率是多少（报告主口径）？', status: 'completed', followup_of: 'run-a195a348', created_at: '2026-10-16 07:09:00', updated_at: '2026-10-16 07:09:42' },
  { run_id: 'run-de0496ab', question: '三季度有效产量完成情况如何？', status: 'waiting_ask', followup_of: '', created_at: '2026-10-16 06:22:00', updated_at: '2026-10-16 06:22:42' },
  { run_id: 'run-7c3c105d', question: '什么是日产液？', status: 'completed', followup_of: '', created_at: '2026-10-16 05:35:00', updated_at: '2026-10-16 05:35:42' },
  { run_id: 'run-1a738a0f', question: '什么是躺井？', status: 'failed', followup_of: 'run-7c3c105d', created_at: '2026-10-16 04:48:00', updated_at: '2026-10-16 04:48:42' },
  { run_id: 'run-b8ab03c0', question: '油田注水水质的主要控制指标执行情况如何？', status: 'completed', followup_of: '', created_at: '2026-10-16 04:01:00', updated_at: '2026-10-16 04:01:42' },
  { run_id: 'run-56e27d72', question: '自然递减率是多少？', status: 'completed', followup_of: '', created_at: '2026-10-16 03:14:00', updated_at: '2026-10-16 03:14:42' },
  { run_id: 'run-f519f723', question: '11 月和 12 月的配注是怎么安排的？', status: 'completed', followup_of: 'run-56e27d72', created_at: '2026-10-16 02:27:00', updated_at: '2026-10-16 02:27:42' },
  { run_id: 'run-935170d5', question: 'N-01 井去年的日产油量是多少？', status: 'completed', followup_of: '', created_at: '2026-10-16 01:40:00', updated_at: '2026-10-16 01:40:42' },
  { run_id: 'run-3188ea87', question: 'N-02 井是什么时候投产的？', status: 'completed', followup_of: '', created_at: '2026-10-16 00:53:00', updated_at: '2026-10-16 00:53:42' },
  { run_id: 'run-cfc06438', question: 'W-11 井的造斜点在多少米？', status: 'waiting_ask', followup_of: 'run-3188ea87', created_at: '2026-10-16 00:06:00', updated_at: '2026-10-16 00:06:42' },
  { run_id: 'run-6df7ddea', question: 'W-11 井生产套管的尺寸与下深是多少？', status: 'completed', followup_of: '', created_at: '2026-10-15 23:19:00', updated_at: '2026-10-15 23:19:42' },
  { run_id: 'run-0c2f579c', question: 'W-11 井投产后预计躺井率是多少？', status: 'failed', followup_of: '', created_at: '2026-10-15 22:32:00', updated_at: '2026-10-15 22:32:42' },
  { run_id: 'run-aa66d14d', question: 'W-21 井的检泵周期和作业费用各是多少？', status: 'completed', followup_of: 'run-0c2f579c', created_at: '2026-10-15 21:45:00', updated_at: '2026-10-15 21:45:42' },
  { run_id: 'run-489e4aff', question: 'W-32 井“检泵周期”栏的 215 天是什么口径？', status: 'completed', followup_of: '', created_at: '2026-10-15 20:58:00', updated_at: '2026-10-15 20:58:42' },
  { run_id: 'run-e6d5c4b0', question: 'W-33 井酸化措施的效果四要素？', status: 'completed', followup_of: '', created_at: '2026-10-15 20:11:00', updated_at: '2026-10-15 20:11:42' },
  { run_id: 'run-850d3e62', question: 'W-45 井现在的泵效是多少？', status: 'completed', followup_of: 'run-e6d5c4b0', created_at: '2026-10-15 19:24:00', updated_at: '2026-10-15 19:24:42' },
  { run_id: 'run-2344b814', question: 'W-57 井的吸水剖面各层占比是多少？', status: 'completed', followup_of: '', created_at: '2026-10-15 18:37:00', updated_at: '2026-10-15 18:37:42' },
  { run_id: 'run-c17c31c5', question: '本月各井日产油量是多少？', status: 'waiting_ask', followup_of: '', created_at: '2026-10-15 17:50:00', updated_at: '2026-10-15 17:50:42' },
  { run_id: 'run-5fb3ab77', question: '本月执行的三项躺井治理措施是什么？', status: 'completed', followup_of: 'run-c17c31c5', created_at: '2026-10-15 17:03:00', updated_at: '2026-10-15 17:03:42' },
  { run_id: 'run-fdeb2528', question: '渤中 34-5 油田三季度注采比是多少？', status: 'failed', followup_of: '', created_at: '2026-10-15 16:16:00', updated_at: '2026-10-15 16:16:42' },
  { run_id: 'run-9c229eda', question: '杆断的是哪几口井？平均检泵周期多少？', status: 'completed', followup_of: '', created_at: '2026-10-15 15:29:00', updated_at: '2026-10-15 15:29:42' },
  { run_id: 'run-3a5a188c', question: '各井日产油量排名', status: 'completed', followup_of: 'run-9c229eda', created_at: '2026-10-15 14:42:00', updated_at: '2026-10-15 14:42:42' },
  { run_id: 'run-d891923d', question: '各井日产油量是多少？', status: 'completed', followup_of: '', created_at: '2026-10-15 13:55:00', updated_at: '2026-10-15 13:55:42' },
  { run_id: 'run-76c90bef', question: '今年各井的日产液量按天列出来', status: 'completed', followup_of: '', created_at: '2026-10-15 13:08:00', updated_at: '2026-10-15 13:08:42' },
  { run_id: 'run-150085a1', question: '近 7 天各井日产液量是多少？', status: 'completed', followup_of: 'run-76c90bef', created_at: '2026-10-15 12:21:00', updated_at: '2026-10-15 12:21:42' },
  { run_id: 'run-b337ff52', question: '近三年 8 月平均检泵周期的变化趋势？', status: 'waiting_ask', followup_of: '', created_at: '2026-10-15 11:34:00', updated_at: '2026-10-15 11:34:42' },
  { run_id: 'run-516f7904', question: '老完成率是多少？', status: 'completed', followup_of: '', created_at: '2026-10-15 10:47:00', updated_at: '2026-10-15 10:47:42' },
  { run_id: 'run-efa6f2b5', question: '两口欠注井分别是什么原因、什么对策？', status: 'failed', followup_of: 'run-516f7904', created_at: '2026-10-15 10:00:00', updated_at: '2026-10-15 10:00:42' },
  { run_id: 'run-8dde6c67', question: '邻井 W-07 井初期日产油多少？现在呢？', status: 'completed', followup_of: '', created_at: '2026-10-15 09:13:00', updated_at: '2026-10-15 09:13:42' },
  { run_id: 'run-2c15e619', question: '去年各井含水率是多少？', status: 'completed', followup_of: '', created_at: '2026-10-15 08:26:00', updated_at: '2026-10-15 08:26:42' },
  { run_id: 'run-ca4d5fca', question: '去年各井每天的日产油量是多少？', status: 'completed', followup_of: 'run-2c15e619', created_at: '2026-10-15 07:39:00', updated_at: '2026-10-15 07:39:42' },
  { run_id: 'run-6884d97c', question: '去年各井每天的油压是多少？', status: 'completed', followup_of: '', created_at: '2026-10-15 06:52:00', updated_at: '2026-10-15 06:52:42' },
  { run_id: 'run-06bc532e', question: '去年各井配产量是多少？', status: 'completed', followup_of: '', created_at: '2026-10-15 06:05:00', updated_at: '2026-10-15 06:05:42' },
  { run_id: 'run-a4f3ccdf', question: '去年日产液量最高的井是哪口？', status: 'waiting_ask', followup_of: 'run-06bc532e', created_at: '2026-10-15 05:18:00', updated_at: '2026-10-15 05:18:42' },
  { run_id: 'run-432b4691', question: '去年日产油量排名前 30', status: 'completed', followup_of: '', created_at: '2026-10-15 04:31:00', updated_at: '2026-10-15 04:31:42' },
  { run_id: 'run-e162c042', question: '去年日产油量最低的两口井是哪两口？', status: 'failed', followup_of: '', created_at: '2026-10-15 03:44:00', updated_at: '2026-10-15 03:44:42' },
  { run_id: 'run-7f9a39f4', question: '去年日产油量最高的井是哪口？', status: 'completed', followup_of: 'run-e162c042', created_at: '2026-10-15 02:57:00', updated_at: '2026-10-15 02:57:42' },
  { run_id: 'run-1dd1b3a6', question: '全油田全年躺井率控制目标是多少？', status: 'completed', followup_of: '', created_at: '2026-10-15 02:10:00', updated_at: '2026-10-15 02:10:42' },
  { run_id: 'run-bc092d57', question: '三季度产量完成率是多少（报告主口径）？', status: 'completed', followup_of: '', created_at: '2026-10-15 01:23:00', updated_at: '2026-10-15 01:23:42' },
  { run_id: 'run-5a40a709', question: '三季度有效产量完成情况如何？', status: 'completed', followup_of: 'run-bc092d57', created_at: '2026-10-15 00:36:00', updated_at: '2026-10-15 00:36:42' },
  { run_id: 'run-f87820ba', question: '什么是日产液？', status: 'completed', followup_of: '', created_at: '2026-10-14 23:49:00', updated_at: '2026-10-14 23:49:42' },
  { run_id: 'run-96af9a6c', question: '什么是躺井？', status: 'waiting_ask', followup_of: '', created_at: '2026-10-14 23:02:00', updated_at: '2026-10-14 23:02:42' },
  { run_id: 'run-34e7141e', question: '油田注水水质的主要控制指标执行情况如何？', status: 'completed', followup_of: 'run-96af9a6c', created_at: '2026-10-14 22:15:00', updated_at: '2026-10-14 22:15:42' },
  { run_id: 'run-d31e8dcf', question: '自然递减率是多少？', status: 'failed', followup_of: '', created_at: '2026-10-14 21:28:00', updated_at: '2026-10-14 21:28:42' },
  { run_id: 'run-71560781', question: '11 月和 12 月的配注是怎么安排的？', status: 'completed', followup_of: '', created_at: '2026-10-14 20:41:00', updated_at: '2026-10-14 20:41:42' },
  { run_id: 'run-0f8d8133', question: 'N-01 井去年的日产油量是多少？', status: 'completed', followup_of: 'run-71560781', created_at: '2026-10-14 19:54:00', updated_at: '2026-10-14 19:54:42' },
  { run_id: 'run-adc4fae4', question: 'N-02 井是什么时候投产的？', status: 'completed', followup_of: '', created_at: '2026-10-14 19:07:00', updated_at: '2026-10-14 19:07:42' },
  { run_id: 'run-4bfc7496', question: 'W-11 井的造斜点在多少米？', status: 'completed', followup_of: '', created_at: '2026-10-14 18:20:00', updated_at: '2026-10-14 18:20:42' },
  { run_id: 'run-ea33ee47', question: 'W-11 井生产套管的尺寸与下深是多少？', status: 'completed', followup_of: 'run-4bfc7496', created_at: '2026-10-14 17:33:00', updated_at: '2026-10-14 17:33:42' },
  { run_id: 'run-886b67f9', question: 'W-11 井投产后预计躺井率是多少？', status: 'waiting_ask', followup_of: '', created_at: '2026-10-14 16:46:00', updated_at: '2026-10-14 16:46:42' },
  { run_id: 'run-26a2e1ab', question: 'W-21 井的检泵周期和作业费用各是多少？', status: 'completed', followup_of: '', created_at: '2026-10-14 15:59:00', updated_at: '2026-10-14 15:59:42' },
  { run_id: 'run-c4da5b5c', question: 'W-32 井“检泵周期”栏的 215 天是什么口径？', status: 'failed', followup_of: 'run-26a2e1ab', created_at: '2026-10-14 15:12:00', updated_at: '2026-10-14 15:12:42' },
  { run_id: 'run-6311d50e', question: 'W-33 井酸化措施的效果四要素？', status: 'completed', followup_of: '', created_at: '2026-10-14 14:25:00', updated_at: '2026-10-14 14:25:42' },
  { run_id: 'run-01494ec0', question: 'W-45 井现在的泵效是多少？', status: 'completed', followup_of: '', created_at: '2026-10-14 13:38:00', updated_at: '2026-10-14 13:38:42' },
  { run_id: 'run-9f80c871', question: 'W-57 井的吸水剖面各层占比是多少？', status: 'completed', followup_of: 'run-01494ec0', created_at: '2026-10-14 12:51:00', updated_at: '2026-10-14 12:51:42' },
  { run_id: 'run-3db84223', question: '本月各井日产油量是多少？', status: 'completed', followup_of: '', created_at: '2026-10-14 12:04:00', updated_at: '2026-10-14 12:04:42' },
  { run_id: 'run-dbefbbd4', question: '本月执行的三项躺井治理措施是什么？', status: 'completed', followup_of: '', created_at: '2026-10-14 11:17:00', updated_at: '2026-10-14 11:17:42' },
  { run_id: 'run-7a273586', question: '渤中 34-5 油田三季度注采比是多少？', status: 'waiting_ask', followup_of: 'run-dbefbbd4', created_at: '2026-10-14 10:30:00', updated_at: '2026-10-14 10:30:42' },
  { run_id: 'run-185eaf38', question: '杆断的是哪几口井？平均检泵周期多少？', status: 'completed', followup_of: '', created_at: '2026-10-14 09:43:00', updated_at: '2026-10-14 09:43:42' },
  { run_id: 'run-b69628e9', question: '各井日产油量排名', status: 'failed', followup_of: '', created_at: '2026-10-14 08:56:00', updated_at: '2026-10-14 08:56:42' },
  { run_id: 'run-54cda29b', question: '各井日产油量是多少？', status: 'completed', followup_of: 'run-b69628e9', created_at: '2026-10-14 08:09:00', updated_at: '2026-10-14 08:09:42' },
  { run_id: 'run-f3051c4c', question: '今年各井的日产液量按天列出来', status: 'completed', followup_of: '', created_at: '2026-10-14 07:22:00', updated_at: '2026-10-14 07:22:42' },
  { run_id: 'run-913c95fe', question: '近 7 天各井日产液量是多少？', status: 'completed', followup_of: '', created_at: '2026-10-14 06:35:00', updated_at: '2026-10-14 06:35:42' },
  { run_id: 'run-2f740fb0', question: '近三年 8 月平均检泵周期的变化趋势？', status: 'completed', followup_of: 'run-913c95fe', created_at: '2026-10-14 05:48:00', updated_at: '2026-10-14 05:48:42' },
  { run_id: 'run-cdab8961', question: '老完成率是多少？', status: 'completed', followup_of: '', created_at: '2026-10-14 05:01:00', updated_at: '2026-10-14 05:01:42' },
  { run_id: 'run-6be30313', question: '两口欠注井分别是什么原因、什么对策？', status: 'waiting_ask', followup_of: '', created_at: '2026-10-14 04:14:00', updated_at: '2026-10-14 04:14:42' },
  { run_id: 'run-0a1a7cc5', question: '邻井 W-07 井初期日产油多少？现在呢？', status: 'completed', followup_of: 'run-6be30313', created_at: '2026-10-14 03:27:00', updated_at: '2026-10-14 03:27:42' },
  { run_id: 'run-a851f676', question: '去年各井含水率是多少？', status: 'failed', followup_of: '', created_at: '2026-10-14 02:40:00', updated_at: '2026-10-14 02:40:42' },
  { run_id: 'run-46897028', question: '去年各井每天的日产油量是多少？', status: 'completed', followup_of: '', created_at: '2026-10-14 01:53:00', updated_at: '2026-10-14 01:53:42' },
  { run_id: 'run-e4c0e9d9', question: '去年各井每天的油压是多少？', status: 'completed', followup_of: 'run-46897028', created_at: '2026-10-14 01:06:00', updated_at: '2026-10-14 01:06:42' },
  { run_id: 'run-82f8638b', question: '去年各井配产量是多少？', status: 'completed', followup_of: '', created_at: '2026-10-14 00:19:00', updated_at: '2026-10-14 00:19:42' },
  { run_id: 'run-212fdd3d', question: '去年日产液量最高的井是哪口？', status: 'completed', followup_of: '', created_at: '2026-10-13 23:32:00', updated_at: '2026-10-13 23:32:42' },
  { run_id: 'run-bf6756ee', question: '去年日产油量排名前 30', status: 'completed', followup_of: 'run-212fdd3d', created_at: '2026-10-13 22:45:00', updated_at: '2026-10-13 22:45:42' },
  { run_id: 'run-5d9ed0a0', question: '去年日产油量最低的两口井是哪两口？', status: 'waiting_ask', followup_of: '', created_at: '2026-10-13 21:58:00', updated_at: '2026-10-13 21:58:42' },
  { run_id: 'run-fbd64a51', question: '去年日产油量最高的井是哪口？', status: 'completed', followup_of: '', created_at: '2026-10-13 21:11:00', updated_at: '2026-10-13 21:11:42' },
  { run_id: 'run-9a0dc403', question: '全油田全年躺井率控制目标是多少？', status: 'failed', followup_of: 'run-fbd64a51', created_at: '2026-10-13 20:24:00', updated_at: '2026-10-13 20:24:42' },
  { run_id: 'run-38453db5', question: '三季度产量完成率是多少（报告主口径）？', status: 'completed', followup_of: '', created_at: '2026-10-13 19:37:00', updated_at: '2026-10-13 19:37:42' },
  { run_id: 'run-d67cb766', question: '三季度有效产量完成情况如何？', status: 'completed', followup_of: '', created_at: '2026-10-13 18:50:00', updated_at: '2026-10-13 18:50:42' },
  { run_id: 'run-74b43118', question: '什么是日产液？', status: 'completed', followup_of: 'run-d67cb766', created_at: '2026-10-13 18:03:00', updated_at: '2026-10-13 18:03:42' },
  { run_id: 'run-12ebaaca', question: '什么是躺井？', status: 'completed', followup_of: '', created_at: '2026-10-13 17:16:00', updated_at: '2026-10-13 17:16:42' },
  { run_id: 'run-b123247b', question: '油田注水水质的主要控制指标执行情况如何？', status: 'completed', followup_of: '', created_at: '2026-10-13 16:29:00', updated_at: '2026-10-13 16:29:42' },
  { run_id: 'run-4f5a9e2d', question: '自然递减率是多少？', status: 'waiting_ask', followup_of: 'run-b123247b', created_at: '2026-10-13 15:42:00', updated_at: '2026-10-13 15:42:42' },
  { run_id: 'run-ed9217de', question: '11 月和 12 月的配注是怎么安排的？', status: 'completed', followup_of: '', created_at: '2026-10-13 14:55:00', updated_at: '2026-10-13 14:55:42' },
  { run_id: 'run-8bc99190', question: 'N-01 井去年的日产油量是多少？', status: 'failed', followup_of: '', created_at: '2026-10-13 14:08:00', updated_at: '2026-10-13 14:08:42' },
  { run_id: 'run-2a010b42', question: 'N-02 井是什么时候投产的？', status: 'completed', followup_of: 'run-8bc99190', created_at: '2026-10-13 13:21:00', updated_at: '2026-10-13 13:21:42' }
]

/** 中栏轮次（自上而下＝对话流顺序）。turn＝归约器/historyAdapter 产出（TurnShape）。 */
export const MOCK_TURNS = [
  { id: 't-live', turn: reduceV2Frames(newTurnV2('ask', q1), prefixFrames), durationS: 6.2 },
  { id: 't-full', turn: reduceV2Frames(newTurnV2('ask', q2), fullFrames2), durationS: 18.5 },
  { id: 't-split', turn: reduceV2Frames(newTurnV2('ask', q3), fullFrames3), durationS: 10.5 },
  { id: 't-legacy', turn: adaptHistoryTurn(legacyListItem, null), durationS: null },
]
