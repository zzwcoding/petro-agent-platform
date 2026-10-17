/**
 * 问一问V2 重设计（方案 A）· mock 轮次数据——静态页专用：不接 SSE、不调真接口。
 *
 * 数据来源（逐条取自真机帧/真机备份，用 jq 抽取，未改一字；轮内跨帧拼接处已注明）：
 *   轮 1 「运行中」：eval/results/frames/EB4-A-正1.json 的**流式前缀**——信封 id ≤ 25 的全部帧
 *     （session/text(理解)/notice/step×7/tool(seq7)/observation×16），即**首条答案正文帧（id=26）
 *     之前**的真机现场；问句取该帧 blackbox.question。时长 6.2s ＝ mock 计时值（真机实测 18.7s；
 *     真接 SSE 时由前端本地计时——此处只让运行中摘要行的形状与完成态一致）。
 *   轮 2 「完整轮」（数据题）：主体 eval/results/frames/EB4-数-明2.json——问句/理解旁白/正文（含
 *     [51] 引标）/51 条引用/51 支材料/血缘 payload.lineage＋limit 与 supplement(lineage) 原文/
 *     attribution 归属面/verdict 核验/blackbox 档案，全取自该帧。跨帧借入（同属 EB 系列真机帧）：
 *     · A 级 notice material_truncated 与 C 级 contradiction_split ← eval/results/frames/EB4-A-正3.json
 *     · B 级 notice window_note ← eval/results/frames/P045B20b-C-正5.json
 *     · C 级 notice unsupported_claim ← eval/results/frames/EB4-A-正1.json
 *     · split 块 ← eval/results/frames/EB4-A-正3.json（该帧第 2 个 split 块；本帧自身无 split）
 *   轮 3 「分列轮」：eval/results/frames/EB3-数-降1.json——长 split 块（1160 字，单条约 350 字含
 *     全角空格表格）/引用含 trust=notice 一条（检索供给窗声明，程序声明非文档）/核验计数。
 *   轮 4 「旧版历史轮」：logs/old-runs-backup-20261014.json 的 run-307959ec（2026-10-13 旧轮）——
 *     正文内嵌旧式「引用：」块，无 supplements／无引用材料（前端按降级态渲染）。
 *
 * 左栏行：`MOCK_RUNS`（120 条 RunListItem 形态——供 ThreadList 的上拉加载/搜索）。
 * 形状：单轮对象＝归约器 newTurnV2 的字段面（steps/tools/materials/notices/citations/understanding/
 * answerText/verdicts/blackbox/runStatus/closed）＋ 重设计新增位（supplement 四槽、lineage/limit、
 * durationS、phase、legacy）。tools 带 seq＝设计稿 §5 第 2 步「tool seq 保留」的目标形状（现归约器丢 seq）。
 * phase＝链条状态机（Owner 2026-10-17 串行链条模型）：'running'（流水线展开，回答块占位）→
 *   'answering'（流水线自动收起，正文流式；本 mock 四轮无此态样本）→ 'done'（链条完整，流水线默认收起）。
 *
 * DEBT(docs/runtime-refactor/frontend-redesign-设计.md)：本文件只服务施工顺序第 1 步「mock 静态页对
 * 版面」；第 2 步接归约器后本文件随 mock 页一并删除或替换为真帧回放。
 */

/** 多行文本装配（逐行字面量——保真机原文换行，避免一条 4 KB 长行）。 */
const joinText = lines => lines.join('\n')

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

/** 中栏轮次（自上而下＝对话流顺序）。 */
export const MOCK_TURNS = [
  {
    id: 't-running',
    label: '运行中（流水线展开态——真机流式前缀）',
    kind: 'ask',
    question: 'W-11 井生产套管的尺寸与下深是多少？',
    runId: '',
    runStatus: 'running',
    phase: 'running',
    closed: null,
    steps: [
      {
        seq: 1,
        station: 'decision',
        title: '模型调用：understand'
      },
      {
        seq: 2,
        station: 'decision',
        title: '理解候选违约：名录外 1 个'
      },
      {
        seq: 3,
        station: 'decision',
        title: '模型调用：decision'
      },
      {
        seq: 4,
        station: 'decision',
        title: '澄清 r1：分解 1 子问题'
      },
      {
        seq: 5,
        station: 'decision',
        title: '模型调用：decision'
      },
      {
        seq: 6,
        station: 'decision',
        title: '前置条件机：s1=allow'
      },
      {
        seq: 7,
        station: 'execute',
        title: 'doc_retrieve：ok（子问题 s1）'
      }
    ],
    tools: [
      {
        seq: 7,
        tool: 'doc_retrieve',
        status: 'ok',
        message: ''
      }
    ],
    materials: [
      {
        index: 1,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: joinText([
          '1.2 井身结构（实钻）　　层次　　　　套管尺寸　　下深（米）　　　水泥返高',
          '　　隔水管　　　30″　　　　0 ～ 118.5　　　泥面',
          '　　表层套管　　20″　　　　322.4　　　　　 泥面',
          '　　技术套管　　13-3/8″　　1258.6　　　　　 地面',
          '　　生产套管　　9-5/8″　　 2462.0　　　　　 地面生产套管钢级 N80、壁厚 10.03 毫米，固井质量测井评价合格段占比 96.8%，油层顶界 2380 米以上 200 米内无明显窜槽。人工井底 2532.6 米。'
        ])
      },
      {
        index: 2,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: joinText([
          '第十章 邻井完井情况对照━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━　　井号　　完井方式　　　射孔段厚(米)　孔密(孔/米)　初期日产油(m³/d)　投产地层',
          '　　W-07　　套管射孔＋筛管　22.0　　　　 13　　　　　 291　　　　　　　 2023-05',
          '　　W-09　　套管射孔　　　　31.5　　　　 16　　　　　 402　　　　　　　 2024-11',
          '　　W-11　　筛管适度防砂　　28.0　　　　 16　　　　　 386　　　　　　　 2026-07对照说明：W-09 井未下防砂筛管（地层评价结论当时偏乐观），生产两年余未见出砂，是本井敢于采用筛管适度防砂（而非砾石充填）的重要参照；W-07 井历史上曾发生筛管堵塞（2024 年 3 月，堵塞段集中于上段），处理方式为酸洗解堵，未影响筛管继续使用。W-07 井目前日产油已递减至 96 m³/d，含水 71.4%，处于双高阶段。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━附录A 主要入井物资与用量━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━　　物资　　　　　　　　规格　　　　　　　数量',
          '　　精密冲缝筛管　　　　7″·150μm　　　　 41.0 米（三段跨装）',
          '　　油管　　　　　　　　4-1/2″·N80　　　 2486.5 米',
          '　　射孔枪　　　　　　　SYD-102　　　　　 3 支（合计弹 448 发）',
          '　　永久封隔器　　　　　7″·液压坐封　　　 1 套',
          '　　井下安全阀　　　　　SCSSV·液控　　　　1 套（液控管线 291.0 米）',
          '　　滑套　　　　　　　　7″·开关式　　　　 1 套　　扶正套　　　　　　　φ148　　　　　　 36 只　　完井液　　　　　　　过滤海水 KCl 体系 320 立方米（含损耗）注：液控管线到 SCSSV 悬挂点长度 291.0 米（285.3 米阀深＋地面余量），与第五章安全阀深 285.3 米为两个不同口径数值，引用时注意区分。（本报告为评测用拟造数据，井号、数值均非真实生产数据。）'
        ])
      },
      {
        index: 3,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: '〔节级摘要｜《A-W11井完井工程报告》·章节 01 第一章 井基本情况｜覆盖 4 支切片〕W-11井位于渤中34-5油田三号构造高部位、CEP-C平台西侧8号井槽，为常规定向生产井，设计井深2530米（垂深2360米），完钻井深2541米，垂深2368米。目的层为东营组二段（Ed2），油层中深2399米，孔隙度24.3%，渗透率486 mD。四层套管结构：30″隔水管、20″表层套管（322.4米）、13-3/8″技术套管（1258.6米）、9-5/8″N80生产套管（2462.0米，壁厚10.03毫米，固井合格段96.8%），人工井底2532.6米。与A版设计差异：完井液密度由1.10 g/cm³下调至1.05 g/cm³，其余一致。'
      },
      {
        index: 4,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: 'W-11井位于渤中34-5油田三号构造高部位,为常规定向生产井,完钻井深2541米,目的层为东营组二段,采用9-5/8"生产套管固井合格段占比96.8%。完井段密度由设计1.10 g/cm³依据邻井压力复核下调至1.05 g/cm³,采用过滤海水+KCl体系完井液。射孔采用TCP加压延时起爆,分三段共28.0米、448发,发射率100%;防砂选用7"精密冲缝筛管150微米精度适度防砂,未充填砾石。施工中第三射孔段漏失115立方米经堵漏浆处理后恢复,筛管下入2410米遇阻经顶驱循环旋转通过。12mm油嘴求产折算日产油386 m³/d,采油指数208.6,表皮系数预计-2.0~-1.0,完井质量综合94.2分,建议按12mm油嘴投产。'
      },
      {
        index: 5,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: '第九章 结论与建议━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━（1）W-11 井完井施工按 B 版方案完成，射孔、防砂、管柱三项主作业质量评价优良；（2）完井段密度按实钻压力复核由设计 1.10 下调至 1.05 g/cm³，实践证明近平衡微正压设计有效（漏失可控、产能正常）；（3）建议生产前 3 个月每月取样化验含砂量，验证 150 微米防砂精度适应性；（4）建议 W-111 观察井压力数据每旬回传一次，用于标定本井生产压差与地层能量；（5）后续如需分层措施，可开启 1520.8 米滑套配合下入插入密封。附：主要工期统计——搬迁安装 2.0 天、射孔 1.5 天、防砂完井 4.5 天、诱喷求产 2.0 天、合计 10.0 天（计划 9.5 天，超期 0.5 天，原因为插曲一漏失处理）。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      },
      {
        index: 6,
        source: '《Y-21井完井工程报告》',
        trust: 'report',
        content: '〔节级摘要｜《Y-21井完井工程报告》·章节 01 第一章 井基本情况｜覆盖 4 支切片〕Y-21井位于渤中34-8油田一号构造东高点CEP-D平台12号井槽，为常规定向生产井，完钻井深2996米（垂深2772.5米）。目的层为沙河街组Es2主力油层（中深2826米），平均孔隙度21.6%、渗透率320mD。井身结构为四层套管（30″/20″/13-3/8″/9-5/8″）+7″尾管，固井质量合格率97.2%。完井段密度由A版1.05下调至1.02g/cm³，射孔负压由2.5上调至3.0MPa。'
      },
      {
        index: 7,
        source: '《C-渤中34-5油田三季度注水调整与生产运行分析》',
        trust: 'report',
        content: '五、递减与能量分析━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━三季度自然递减率 4.6%，同比下降 0.9 个百分点；综合递减率 6.1%，同比上升 0.2 个百分点——自然递减改善主要来自 W-33 酸化增油与含水回落，综合递减上升反映措施总量偏少（季度仅 1 井次）。递减增油口径提示：自然递减率与综合递减率之间的差值部分即为措施贡献量，台账中"递减增油"指标存在口径争议注记（待联席裁决），本报告暂按"措施后产量与递减基线之差"的作业区口径统计，不直接与台账对比。注采比长期低于 1.0 的能量后果：地层压力由年初 21.9 MPa 降至当前 21.4 MPa（参照 W-111 观察井实测），压力保持率 97.7%。若四季度月注采比不能稳定在 1.0 附近，预计年末地层压力降至 21.1 MPa 以下，将触及 96% 保持率的开发红线。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      },
      {
        index: 8,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: '第一章 井基本情况━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      },
      {
        index: 9,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: '1.1 井位与井别W-11 井位于渤中 34-5 油田三号构造高部位，CEP-C 生产平台西侧井槽 8 号位。本井为生产井，井型为常规定向井，设计井深 2530 米（垂深 2360 米），完钻井深 2541 米，垂深 2368 米。目的层为东营组二段（Ed2）主力油层，油层中深 2399 米，属常规中高渗砂岩油藏，平均孔隙度 24.3%，平均渗透率 486 mD。同平台 W-111 井为观察井，不承担生产任务，主要用于油藏压力监测与注水推进观察，其压力计于 2026 年 6 月 30 日完成下放，基线压力 21.4 MPa。本报告涉及的地面流程与 W-111 井共用测试分离器，但井下作业互相独立。'
      },
      {
        index: 10,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: '1.3 与 A 版设计的差异说明A 版设计文件中完井液完井段密度设计值为 1.10 g/cm³；现场依据邻井 W-09 井实钻压力复核，将完井段密度下调至 1.05 g/cm³（详见第三章），其余井身结构、射孔井段与 A 版一致。本报告所有数据除特别注明外均为现场实际执行值。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      },
      {
        index: 11,
        source: '《Y-21井完井工程报告》',
        trust: 'report',
        content: '第一章 井基本情况━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      },
      {
        index: 12,
        source: '《Y-21井完井工程报告》',
        trust: 'report',
        content: '1.1 井位与井别Y-21 井位于渤中 34-8 油田一号构造东高点，CEP-D 生产平台东侧井槽 12 号位。本井为生产井，常规定向井，设计井深 2980 米（垂深 2760 米），完钻井深 2996 米，垂深 2772.5 米。目的层为沙河街组二段（Es2）主力油层，油层中深 2826 米、顶界 2748 米，属中渗疏松细砂岩油藏，平均孔隙度 21.6%，平均渗透率 320 mD，层内渗透率变异系数 0.38。同平台 Y-19、Y-23 井为本井邻井，均生产 Es2 层系。本报告数据除注明外均为现场实际执行值。'
      },
      {
        index: 13,
        source: '《Y-21井完井工程报告》',
        trust: 'report',
        content: joinText([
          '1.2 井身结构（实钻）　　层次　　　　套管尺寸　　下深（米）　　　水泥返高',
          '　　隔水管　　　30″　　　　0 ～ 126.0　　　泥面',
          '　　表层套管　　20″　　　　348.2　　　　　 泥面',
          '　　技术套管　　13-3/8″　　1425.8　　　　　 地面',
          '　　生产套管　　9-5/8″　　 2680.4　　　　　 地面',
          '　　尾管　　　　7″　　　　 2680.4 ～ 2975.0　返至悬挂器顶生产套管钢级 N80、壁厚 10.03 毫米，固井质量测井合格段占比 97.2%，油层顶界以上 200 米内无明显窜槽。7″ 尾管钢级 N80、壁厚 9.19 毫米，悬挂器坐挂于 9-5/8″ 生产套管内 2665.2 米，尾管固井碰压 12.5 MPa。钻井人工井底 2968.8 米，完井丝堵底界 2951.6 米。'
        ])
      },
      {
        index: 14,
        source: '《Y-21井完井工程报告》',
        trust: 'report',
        content: '1.3 与 A 版设计的差异说明A 版设计完井段密度 1.05 g/cm³；现场依据四开实测地层压力复核下调至 1.02 g/cm³（见第二章），射孔负压相应由 2.5 MPa 上调至 3.0 MPa，其余与 A 版一致。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      },
      {
        index: 15,
        source: '检索供给窗声明（截断显式）',
        trust: 'notice',
        content: '召回 56 支/送窗 14 支；已召回未送窗 42 支；矛盾来源同窗并立（各留代表支）：《A-W11井完井工程报告》、《Y-21井完井工程报告》、《C-渤中34-5油田三季度注水调整与生产运行分析》；缺位来源（预算未及）：《渤中34-8油田一季度注采调整与生产运行分析》、《B-渤中34-5油田躺井治理与检泵作业月报-202608》；题眼锚保底席位：《C-渤中34-5油田三季度注水调整与生产运行分析》；节级摘要展开节内切片 +7 支（摘要命中→节内补席）'
      },
      {
        index: 16,
        source: '检索供给窗声明（缺位名单）',
        trust: 'report',
        content: '检索窗注记：缺位来源（预算未及）：《渤中34-8油田一季度注采调整与生产运行分析》、《B-渤中34-5油田躺井治理与检泵作业月报-202608》'
      }
    ],
    notices: [
      {
        type: 'unsupported_claim',
        gates: [],
        content: '理解步指标候选出现名录外名字（无）——判违约，如实上报，不静默丢弃。'
      }
    ],
    citations: [],
    understanding: '理解：问 W-11 井生产套管的尺寸与下深。',
    answerText: '',
    verdicts: [],
    blackbox: null,
    supplement: {
      lineage: null,
      attribution: null,
      split: null,
      citations: null
    },
    lineage: null,
    limit: null,
    durationS: 6.2,
    createdAt: null,
    legacy: false
  },
  {
    id: 't-full',
    label: '完整轮（数据题——全形态）',
    kind: 'ask',
    question: '今年各井的日产液量按天列出来',
    runId: 'run-21e45912',
    runStatus: 'completed',
    phase: 'done',
    closed: 'done',
    steps: [
      {
        seq: 1,
        station: 'decision',
        title: '模型调用：understand'
      },
      {
        seq: 2,
        station: 'decision',
        title: '模型调用：decision'
      },
      {
        seq: 3,
        station: 'decision',
        title: '澄清 r1 被拒：ledger_notes 槽位对账未过：s1'
      },
      {
        seq: 4,
        station: 'decision',
        title: '模型调用：decision'
      },
      {
        seq: 5,
        station: 'decision',
        title: '澄清 r2：分解 1 子问题'
      },
      {
        seq: 6,
        station: 'decision',
        title: '模型调用：decision'
      },
      {
        seq: 7,
        station: 'decision',
        title: '前置条件机：s1=allow'
      },
      {
        seq: 8,
        station: 'execute',
        title: 'data_query：ok（子问题 s1）'
      },
      {
        seq: 9,
        station: 'answer',
        title: '模型调用：answer'
      },
      {
        seq: 10,
        station: 'answer',
        title: '起草答案'
      },
      {
        seq: 11,
        station: 'verify',
        title: '核验：支撑 51｜改写 0｜分源 否'
      },
      {
        seq: 12,
        station: 'answer',
        title: '答案收口'
      }
    ],
    tools: [
      {
        seq: 8,
        tool: 'data_query',
        status: 'ok',
        message: ''
      }
    ],
    materials: [
      {
        index: 1,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-01；区块=渤南；日期=2026-01-01；日产液量（方）=36.97'
      },
      {
        index: 2,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-02；区块=渤南；日期=2026-01-01；日产液量（方）=48.72'
      },
      {
        index: 3,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-03；区块=渤南；日期=2026-01-01；日产液量（方）=45.67'
      },
      {
        index: 4,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-04；区块=渤南；日期=2026-01-01；日产液量（方）=38.92'
      },
      {
        index: 5,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-05；区块=渤南；日期=2026-01-01；日产液量（方）=69.97'
      },
      {
        index: 6,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-06；区块=渤南；日期=2026-01-01；日产液量（方）=67.86'
      },
      {
        index: 7,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-07；区块=渤南；日期=2026-01-01；日产液量（方）=43.97'
      },
      {
        index: 8,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-08；区块=渤南；日期=2026-01-01；日产液量（方）=33.68'
      },
      {
        index: 9,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-09；区块=渤南；日期=2026-01-01；日产液量（方）=26.79'
      },
      {
        index: 10,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-10；区块=渤南；日期=2026-01-01；日产液量（方）=47.65'
      },
      {
        index: 11,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-11；区块=渤南；日期=2026-01-01；日产液量（方）=67.92'
      },
      {
        index: 12,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-12；区块=渤南；日期=2026-01-01；日产液量（方）=53.76'
      },
      {
        index: 13,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-13；区块=渤南；日期=2026-01-01；日产液量（方）=41.16'
      },
      {
        index: 14,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-14；区块=渤南；日期=2026-01-01；日产液量（方）=38.54'
      },
      {
        index: 15,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-15；区块=渤南；日期=2026-01-01；日产液量（方）=84.89'
      },
      {
        index: 16,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-16；区块=渤南；日期=2026-01-01；日产液量（方）=28.76'
      },
      {
        index: 17,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-17；区块=渤南；日期=2026-01-01；日产液量（方）=24.57'
      },
      {
        index: 18,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-18；区块=渤南；日期=2026-01-01；日产液量（方）=48.48'
      },
      {
        index: 19,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-19；区块=渤南；日期=2026-01-01；日产液量（方）=45.29'
      },
      {
        index: 20,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-20；区块=渤南；日期=2026-01-01；日产液量（方）=66.12'
      },
      {
        index: 21,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-21；区块=渤南；日期=2026-01-01；日产液量（方）=45.57'
      },
      {
        index: 22,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-22；区块=渤南；日期=2026-01-01；日产液量（方）=29.49'
      },
      {
        index: 23,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-23；区块=渤南；日期=2026-01-01；日产液量（方）=70.82'
      },
      {
        index: 24,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-24；区块=渤南；日期=2026-01-01；日产液量（方）=44.06'
      },
      {
        index: 25,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-25；区块=渤南；日期=2026-01-01；日产液量（方）=49.45'
      },
      {
        index: 26,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-26；区块=渤南；日期=2026-01-01；日产液量（方）=39.78'
      },
      {
        index: 27,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=N-27；区块=渤南；日期=2026-01-01；日产液量（方）=31.64'
      },
      {
        index: 28,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-01；区块=渤西；日期=2026-01-01；日产液量（方）=39.48'
      },
      {
        index: 29,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-02；区块=渤西；日期=2026-01-01；日产液量（方）=28.99'
      },
      {
        index: 30,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-03；区块=渤西；日期=2026-01-01；日产液量（方）=53.89'
      },
      {
        index: 31,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-04；区块=渤西；日期=2026-01-01；日产液量（方）=51.78'
      },
      {
        index: 32,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-05；区块=渤西；日期=2026-01-01；日产液量（方）=66.88'
      },
      {
        index: 33,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-06；区块=渤西；日期=2026-01-01；日产液量（方）=37.20'
      },
      {
        index: 34,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-07；区块=渤西；日期=2026-01-01；日产液量（方）=58.12'
      },
      {
        index: 35,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-08；区块=渤西；日期=2026-01-01；日产液量（方）=56.44'
      },
      {
        index: 36,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-09；区块=渤西；日期=2026-01-01；日产液量（方）=21.25'
      },
      {
        index: 37,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-10；区块=渤西；日期=2026-01-01；日产液量（方）=44.70'
      },
      {
        index: 38,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-11；区块=渤西；日期=2026-01-01；日产液量（方）=45.26'
      },
      {
        index: 39,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-12；区块=渤西；日期=2026-01-01；日产液量（方）=44.17'
      },
      {
        index: 40,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-13；区块=渤西；日期=2026-01-01；日产液量（方）=58.83'
      },
      {
        index: 41,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-14；区块=渤西；日期=2026-01-01；日产液量（方）=25.20'
      },
      {
        index: 42,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-15；区块=渤西；日期=2026-01-01；日产液量（方）=29.23'
      },
      {
        index: 43,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-16；区块=渤西；日期=2026-01-01；日产液量（方）=32.25'
      },
      {
        index: 44,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-17；区块=渤西；日期=2026-01-01；日产液量（方）=23.47'
      },
      {
        index: 45,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-18；区块=渤西；日期=2026-01-01；日产液量（方）=46.89'
      },
      {
        index: 46,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-19；区块=渤西；日期=2026-01-01；日产液量（方）=27.03'
      },
      {
        index: 47,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-20；区块=渤西；日期=2026-01-01；日产液量（方）=29.23'
      },
      {
        index: 48,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-21；区块=渤西；日期=2026-01-01；日产液量（方）=32.18'
      },
      {
        index: 49,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-22；区块=渤西；日期=2026-01-01；日产液量（方）=68.51'
      },
      {
        index: 50,
        source: 'agg.fct_daily_metering',
        trust: 'authoritative',
        content: '井号=X-23；区块=渤西；日期=2026-01-01；日产液量（方）=52.67'
      },
      {
        index: 51,
        source: 'agg.fct_daily_metering ⋈ agg.dim_well ⋈ agg.dim_date',
        trust: 'authoritative',
        content: joinText([
          '① 口径 日产液量（方）（单位：方）——指标台账注册声明：日产计量的日产液量——源 oil_production_daily.liquid_output（R5·A.2）；agg 读模型绑定列 agg.fct_daily_metering.liquid_output（99 §2.12），口径随答案标注',
          '② 来源表 agg.fct_daily_metering（agg 星型读模型 · 即汇总层「日产计量表」——99 册 §2.12/D6 star_model，机器名＝A1 解释链②冻结）⋈ agg.dim_well（井维度·按井号）⋈ agg.dim_date（日期维度·按日期）',
          '③ 过滤条件 时间＝2026-01-01～2026-08-30 [2026-01-01, 2026-08-31)',
          '　└（权限注入） 数据域＝全量——行级注入经 M-01 两步缝拼入 WHERE，不靠模型自觉（预埋期谓词恒空＝恒真；真分权只换谓词生产实现，注入点形状冻结）（actor＝aqiang · 落点 agg.fct_daily_metering——谓词随执行并语句）',
          '④ 数据截至批次 批次 b-a1a61db9f458 · 汇总层水位 2026-08-31（承诺 T-1 · 落后 37 天 · 超期）',
          '⑤ 收口注记 LIMIT 50——强制限量纪律：没写补默认 50、超 200 截到 200，只封顶不抬底'
        ])
      }
    ],
    notices: [
      {
        type: 'material_truncated',
        gates: [],
        content: '这次回答只用到检索到的 24/37 条材料——没用上的部分不作答。'
      },
      {
        type: 'window_note',
        gates: [],
        content: '召回 49 支/送窗 6 支；已召回未送窗 43 支；矛盾来源同窗并立（各留代表支）：《C-渤中34-5油田三季度注水调整与生产运行分析》、《渤中34-8油田一季度注采调整与生产运行分析》、《Y-21井完井工程报告》、《渤中34-8油田躺井治理与检泵作业月报-202701》、《A-W11井完井工程报告》、《B-渤中34-5油田躺井治理与检泵作业月报-202608》'
      },
      {
        type: 'unsupported_claim',
        gates: [],
        content: '核验步删去无据断言 2 行（EB3 D3：真无据断言删句、不贴前缀——禁止无据断言进答案；留痕＝rewrites 逐行原句 ＋ 本计数）'
      },
      {
        type: 'contradiction_split',
        gates: [],
        content: '多来源不一致——答案分源列明（INV-4——禁止无出处调和）'
      }
    ],
    citations: [
      {
        index: 1,
        source: 'agg.fct_daily_metering',
        source_id: 'N-01@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 2,
        source: 'agg.fct_daily_metering',
        source_id: 'N-02@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 3,
        source: 'agg.fct_daily_metering',
        source_id: 'N-03@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 4,
        source: 'agg.fct_daily_metering',
        source_id: 'N-04@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 5,
        source: 'agg.fct_daily_metering',
        source_id: 'N-05@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 6,
        source: 'agg.fct_daily_metering',
        source_id: 'N-06@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 7,
        source: 'agg.fct_daily_metering',
        source_id: 'N-07@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 8,
        source: 'agg.fct_daily_metering',
        source_id: 'N-08@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 9,
        source: 'agg.fct_daily_metering',
        source_id: 'N-09@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 10,
        source: 'agg.fct_daily_metering',
        source_id: 'N-10@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 11,
        source: 'agg.fct_daily_metering',
        source_id: 'N-11@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 12,
        source: 'agg.fct_daily_metering',
        source_id: 'N-12@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 13,
        source: 'agg.fct_daily_metering',
        source_id: 'N-13@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 14,
        source: 'agg.fct_daily_metering',
        source_id: 'N-14@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 15,
        source: 'agg.fct_daily_metering',
        source_id: 'N-15@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 16,
        source: 'agg.fct_daily_metering',
        source_id: 'N-16@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 17,
        source: 'agg.fct_daily_metering',
        source_id: 'N-17@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 18,
        source: 'agg.fct_daily_metering',
        source_id: 'N-18@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 19,
        source: 'agg.fct_daily_metering',
        source_id: 'N-19@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 20,
        source: 'agg.fct_daily_metering',
        source_id: 'N-20@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 21,
        source: 'agg.fct_daily_metering',
        source_id: 'N-21@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 22,
        source: 'agg.fct_daily_metering',
        source_id: 'N-22@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 23,
        source: 'agg.fct_daily_metering',
        source_id: 'N-23@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 24,
        source: 'agg.fct_daily_metering',
        source_id: 'N-24@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 25,
        source: 'agg.fct_daily_metering',
        source_id: 'N-25@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 26,
        source: 'agg.fct_daily_metering',
        source_id: 'N-26@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 27,
        source: 'agg.fct_daily_metering',
        source_id: 'N-27@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 28,
        source: 'agg.fct_daily_metering',
        source_id: 'X-01@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 29,
        source: 'agg.fct_daily_metering',
        source_id: 'X-02@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 30,
        source: 'agg.fct_daily_metering',
        source_id: 'X-03@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 31,
        source: 'agg.fct_daily_metering',
        source_id: 'X-04@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 32,
        source: 'agg.fct_daily_metering',
        source_id: 'X-05@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 33,
        source: 'agg.fct_daily_metering',
        source_id: 'X-06@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 34,
        source: 'agg.fct_daily_metering',
        source_id: 'X-07@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 35,
        source: 'agg.fct_daily_metering',
        source_id: 'X-08@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 36,
        source: 'agg.fct_daily_metering',
        source_id: 'X-09@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 37,
        source: 'agg.fct_daily_metering',
        source_id: 'X-10@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 38,
        source: 'agg.fct_daily_metering',
        source_id: 'X-11@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 39,
        source: 'agg.fct_daily_metering',
        source_id: 'X-12@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 40,
        source: 'agg.fct_daily_metering',
        source_id: 'X-13@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 41,
        source: 'agg.fct_daily_metering',
        source_id: 'X-14@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 42,
        source: 'agg.fct_daily_metering',
        source_id: 'X-15@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 43,
        source: 'agg.fct_daily_metering',
        source_id: 'X-16@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 44,
        source: 'agg.fct_daily_metering',
        source_id: 'X-17@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 45,
        source: 'agg.fct_daily_metering',
        source_id: 'X-18@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 46,
        source: 'agg.fct_daily_metering',
        source_id: 'X-19@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 47,
        source: 'agg.fct_daily_metering',
        source_id: 'X-20@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 48,
        source: 'agg.fct_daily_metering',
        source_id: 'X-21@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 49,
        source: 'agg.fct_daily_metering',
        source_id: 'X-22@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 50,
        source: 'agg.fct_daily_metering',
        source_id: 'X-23@2026-01-01',
        trust: 'authoritative'
      },
      {
        index: 51,
        source: 'agg.fct_daily_metering ⋈ agg.dim_well ⋈ agg.dim_date',
        source_id: 'lineage',
        trust: 'authoritative'
      }
    ],
    understanding: joinText([
      '理解：问今年各井按天列出的日产液量。',
      '指标候选：日产液量'
    ]),
    answerText: joinText([
      '今年各井按天列出的日产液量如下（口径：日产计量的日产液量，单位方；时间窗：2026-01-01 至 2026-08-31；来源表：日产计量事实表）：渤南区块：',
      '- N-01 井：2026-01-01 = 36.97 [1]',
      '- N-02 井：2026-01-01 = 48.72 [2]',
      '- N-03 井：2026-01-01 = 45.67 [3]',
      '- N-04 井：2026-01-01 = 38.92 [4]',
      '- N-05 井：2026-01-01 = 69.97 [5]',
      '- N-06 井：2026-01-01 = 67.86 [6]',
      '- N-07 井：2026-01-01 = 43.97 [7]',
      '- N-08 井：2026-01-01 = 33.68 [8]',
      '- N-09 井：2026-01-01 = 26.79 [9]',
      '- N-10 井：2026-01-01 = 47.65 [10]',
      '- N-11 井：2026-01-01 = 67.92 [11]',
      '- N-12 井：2026-01-01 = 53.76 [12]',
      '- N-13 井：2026-01-01 = 41.16 [13]',
      '- N-14 井：2026-01-01 = 38.54 [14]',
      '- N-15 井：2026-01-01 = 84.89 [15]',
      '- N-16 井：2026-01-01 = 28.76 [16]',
      '- N-17 井：2026-01-01 = 24.57 [17]',
      '- N-18 井：2026-01-01 = 48.48 [18]',
      '- N-19 井：2026-01-01 = 45.29 [19]',
      '- N-20 井：2026-01-01 = 66.12 [20]',
      '- N-21 井：2026-01-01 = 45.57 [21]',
      '- N-22 井：2026-01-01 = 29.49 [22]',
      '- N-23 井：2026-01-01 = 70.82 [23]',
      '- N-24 井：2026-01-01 = 44.06 [24]',
      '- N-25 井：2026-01-01 = 49.45 [25]',
      '- N-26 井：2026-01-01 = 39.78 [26]',
      '- N-27 井：2026-01-01 = 31.64 [27]渤西区块：',
      '- X-01 井：2026-01-01 = 39.48 [28]',
      '- X-02 井：2026-01-01 = 28.99 [29]',
      '- X-03 井：2026-01-01 = 53.89 [30]',
      '- X-04 井：2026-01-01 = 51.78 [31]',
      '- X-05 井：2026-01-01 = 66.88 [32]',
      '- X-06 井：2026-01-01 = 37.20 [33]',
      '- X-07 井：2026-01-01 = 58.12 [34]',
      '- X-08 井：2026-01-01 = 56.44 [35]',
      '- X-09 井：2026-01-01 = 21.25 [36]',
      '- X-10 井：2026-01-01 = 44.70 [37]',
      '- X-11 井：2026-01-01 = 45.26 [38]',
      '- X-12 井：2026-01-01 = 44.17 [39]',
      '- X-13 井：2026-01-01 = 58.83 [40]',
      '- X-14 井：2026-01-01 = 25.20 [41]',
      '- X-15 井：2026-01-01 = 29.23 [42]',
      '- X-16 井：2026-01-01 = 32.25 [43]',
      '- X-17 井：2026-01-01 = 23.47 [44]',
      '- X-18 井：2026-01-01 = 46.89 [45]',
      '- X-19 井：2026-01-01 = 27.03 [46]',
      '- X-20 井：2026-01-01 = 29.23 [47]',
      '- X-21 井：2026-01-01 = 32.18 [48]',
      '- X-22 井：2026-01-01 = 68.51 [49]',
      '- X-23 井：2026-01-01 = 52.67 [50]说明：本次检索因行数封顶仅返回 2026-01-01 这一天的各井日产液量 [51]。若需要 2026-01-01 至 2026-08-31 完整时间窗内逐井逐日的全部明细数据，建议按井号或按日期分批进一步检索，可有效避免单次返回行数受限的问题。'
    ]),
    verdicts: [
      {
        supported: 51,
        rewritten: 0,
        split: 0,
        cited: [
          1,
          2,
          3,
          4,
          5,
          6,
          7,
          8,
          9,
          10,
          11,
          12,
          13,
          14,
          15,
          16,
          17,
          18,
          19,
          20,
          21,
          22,
          23,
          24,
          25,
          26,
          27,
          28,
          29,
          30,
          31,
          32,
          33,
          34,
          35,
          36,
          37,
          38,
          39,
          40,
          41,
          42,
          43,
          44,
          45,
          46,
          47,
          48,
          49,
          50,
          51
        ],
        attribution: true,
        subtype: 'verify'
      }
    ],
    blackbox: {
      run_id: 'run-21e45912',
      question: '今年各井的日产液量按天列出来',
      status: 'completed',
      error: '',
      stored: true,
      bytes: 58959,
      counts: {
        messages: 11,
        dialogue: 0,
        process_notes: 6,
        observations: 51,
        steps: 12
      }
    },
    supplement: {
      lineage: joinText([
        '① 口径 日产液量（方）（单位：方）——指标台账注册声明：日产计量的日产液量——源 oil_production_daily.liquid_output（R5·A.2）；agg 读模型绑定列 agg.fct_daily_metering.liquid_output（99 §2.12），口径随答案标注',
        '② 来源表 agg.fct_daily_metering（agg 星型读模型 · 即汇总层「日产计量表」——99 册 §2.12/D6 star_model，机器名＝A1 解释链②冻结）⋈ agg.dim_well（井维度·按井号）⋈ agg.dim_date（日期维度·按日期）',
        '③ 过滤条件 时间＝2026-01-01～2026-08-30 [2026-01-01, 2026-08-31)',
        '　└（权限注入） 数据域＝全量——行级注入经 M-01 两步缝拼入 WHERE，不靠模型自觉（预埋期谓词恒空＝恒真；真分权只换谓词生产实现，注入点形状冻结）（actor＝aqiang · 落点 agg.fct_daily_metering——谓词随执行并语句）',
        '④ 数据截至批次 批次 b-a1a61db9f458 · 汇总层水位 2026-08-31（承诺 T-1 · 落后 37 天 · 超期）',
        '⑤ 收口注记 LIMIT 50——强制限量纪律：没写补默认 50、超 200 截到 200，只封顶不抬底'
      ]),
      attribution: joinText([
        '按来源分别列出（每条结论都标出它来自哪个来源）：',
        '[1] agg.fct_daily_metering：井号=N-01；区块=渤南；日期=2026-01-01；日产液量（方）=36.97',
        '[2] agg.fct_daily_metering：井号=N-02；区块=渤南；日期=2026-01-01；日产液量（方）=48.72',
        '[3] agg.fct_daily_metering：井号=N-03；区块=渤南；日期=2026-01-01；日产液量（方）=45.67',
        '[4] agg.fct_daily_metering：井号=N-04；区块=渤南；日期=2026-01-01；日产液量（方）=38.92',
        '[5] agg.fct_daily_metering：井号=N-05；区块=渤南；日期=2026-01-01；日产液量（方）=69.97',
        '[6] agg.fct_daily_metering：井号=N-06；区块=渤南；日期=2026-01-01；日产液量（方）=67.86',
        '[7] agg.fct_daily_metering：井号=N-07；区块=渤南；日期=2026-01-01；日产液量（方）=43.97',
        '[8] agg.fct_daily_metering：井号=N-08；区块=渤南；日期=2026-01-01；日产液量（方）=33.68',
        '[9] agg.fct_daily_metering：井号=N-09；区块=渤南；日期=2026-01-01；日产液量（方）=26.79',
        '[10] agg.fct_daily_metering：井号=N-10；区块=渤南；日期=2026-01-01；日产液量（方）=47.65',
        '[11] agg.fct_daily_metering：井号=N-11；区块=渤南；日期=2026-01-01；日产液量（方）=67.92',
        '[12] agg.fct_daily_metering：井号=N-12；区块=渤南；日期=2026-01-01；日产液量（方）=53.76',
        '[13] agg.fct_daily_metering：井号=N-13；区块=渤南；日期=2026-01-01；日产液量（方）=41.16',
        '[14] agg.fct_daily_metering：井号=N-14；区块=渤南；日期=2026-01-01；日产液量（方）=38.54',
        '[15] agg.fct_daily_metering：井号=N-15；区块=渤南；日期=2026-01-01；日产液量（方）=84.89',
        '[16] agg.fct_daily_metering：井号=N-16；区块=渤南；日期=2026-01-01；日产液量（方）=28.76',
        '[17] agg.fct_daily_metering：井号=N-17；区块=渤南；日期=2026-01-01；日产液量（方）=24.57',
        '[18] agg.fct_daily_metering：井号=N-18；区块=渤南；日期=2026-01-01；日产液量（方）=48.48',
        '[19] agg.fct_daily_metering：井号=N-19；区块=渤南；日期=2026-01-01；日产液量（方）=45.29',
        '[20] agg.fct_daily_metering：井号=N-20；区块=渤南；日期=2026-01-01；日产液量（方）=66.12',
        '[21] agg.fct_daily_metering：井号=N-21；区块=渤南；日期=2026-01-01；日产液量（方）=45.57',
        '[22] agg.fct_daily_metering：井号=N-22；区块=渤南；日期=2026-01-01；日产液量（方）=29.49',
        '[23] agg.fct_daily_metering：井号=N-23；区块=渤南；日期=2026-01-01；日产液量（方）=70.82',
        '[24] agg.fct_daily_metering：井号=N-24；区块=渤南；日期=2026-01-01；日产液量（方）=44.06',
        '[25] agg.fct_daily_metering：井号=N-25；区块=渤南；日期=2026-01-01；日产液量（方）=49.45',
        '[26] agg.fct_daily_metering：井号=N-26；区块=渤南；日期=2026-01-01；日产液量（方）=39.78',
        '[27] agg.fct_daily_metering：井号=N-27；区块=渤南；日期=2026-01-01；日产液量（方）=31.64',
        '[28] agg.fct_daily_metering：井号=X-01；区块=渤西；日期=2026-01-01；日产液量（方）=39.48',
        '[29] agg.fct_daily_metering：井号=X-02；区块=渤西；日期=2026-01-01；日产液量（方）=28.99',
        '[30] agg.fct_daily_metering：井号=X-03；区块=渤西；日期=2026-01-01；日产液量（方）=53.89',
        '[31] agg.fct_daily_metering：井号=X-04；区块=渤西；日期=2026-01-01；日产液量（方）=51.78',
        '[32] agg.fct_daily_metering：井号=X-05；区块=渤西；日期=2026-01-01；日产液量（方）=66.88',
        '[33] agg.fct_daily_metering：井号=X-06；区块=渤西；日期=2026-01-01；日产液量（方）=37.20',
        '[34] agg.fct_daily_metering：井号=X-07；区块=渤西；日期=2026-01-01；日产液量（方）=58.12',
        '[35] agg.fct_daily_metering：井号=X-08；区块=渤西；日期=2026-01-01；日产液量（方）=56.44',
        '[36] agg.fct_daily_metering：井号=X-09；区块=渤西；日期=2026-01-01；日产液量（方）=21.25',
        '[37] agg.fct_daily_metering：井号=X-10；区块=渤西；日期=2026-01-01；日产液量（方）=44.70',
        '[38] agg.fct_daily_metering：井号=X-11；区块=渤西；日期=2026-01-01；日产液量（方）=45.26',
        '[39] agg.fct_daily_metering：井号=X-12；区块=渤西；日期=2026-01-01；日产液量（方）=44.17',
        '[40] agg.fct_daily_metering：井号=X-13；区块=渤西；日期=2026-01-01；日产液量（方）=58.83',
        '[41] agg.fct_daily_metering：井号=X-14；区块=渤西；日期=2026-01-01；日产液量（方）=25.20',
        '[42] agg.fct_daily_metering：井号=X-15；区块=渤西；日期=2026-01-01；日产液量（方）=29.23',
        '[43] agg.fct_daily_metering：井号=X-16；区块=渤西；日期=2026-01-01；日产液量（方）=32.25',
        '[44] agg.fct_daily_metering：井号=X-17；区块=渤西；日期=2026-01-01；日产液量（方）=23.47',
        '[45] agg.fct_daily_metering：井号=X-18；区块=渤西；日期=2026-01-01；日产液量（方）=46.89',
        '[46] agg.fct_daily_metering：井号=X-19；区块=渤西；日期=2026-01-01；日产液量（方）=27.03',
        '[47] agg.fct_daily_metering：井号=X-20；区块=渤西；日期=2026-01-01；日产液量（方）=29.23',
        '[48] agg.fct_daily_metering：井号=X-21；区块=渤西；日期=2026-01-01；日产液量（方）=32.18',
        '[49] agg.fct_daily_metering：井号=X-22；区块=渤西；日期=2026-01-01；日产液量（方）=68.51',
        '[50] agg.fct_daily_metering：井号=X-23；区块=渤西；日期=2026-01-01；日产液量（方）=52.67',
        '[51] agg.fct_daily_metering ⋈ agg.dim_well ⋈ agg.dim_date：① 口径 日产液量（方）（单位：方）——指标台账注册声明：日产计量的日产液量——源 oil_production_daily.liquid_output（R5·A.2）；agg 读模型绑定列 agg.fct_daily_metering.liquid_output（99 §2.12），口径随答案标注',
        '② 来源表 agg.fct_daily_metering（agg 星型读模型 · 即汇总层「日产计量表」——99 册 §2.12/D6 star_model，机器名＝A1 解释链②冻结）⋈ agg.dim_well（井维度·按井号）⋈ agg.dim_date（日期维度·按日期）',
        '③ 过滤条件 时间＝2026-01-01～2026-08-30 [2026-01-01, 2026-08-31)',
        '　└（权限注入） 数据域＝全量——行级注入经 M-01 两步缝拼入 WHERE，不靠模型自觉（预埋期谓词恒空＝恒真；真分权只换谓词生产实现，注入点形状冻结）（actor＝aqiang · 落点 agg.fct_daily_metering——谓词随执行并语句）',
        '④ 数据截至批次 批次 b-a1a61db9f458 · 汇总层水位 2026-08-31（承诺 T-1 · 落后 37 天 · 超期）',
        '⑤ 收口注记 LIMIT 50——强制限量纪律：没写补默认 50、超 200 截到 200，只封顶不抬底'
      ]),
      split: joinText([
        '互不一致——各来源说法如下，按来源分别列出：',
        '[22] 检索供给窗声明（缺位名单） · window_miss：检索窗注记：缺位来源（预算未及）：《渤中34-8油田一季度注采调整与生产运行分析》',
        '[43] 检索供给窗声明（缺位名单） · window_miss：检索窗注记：缺位来源（预算未及）：《渤中34-8油田一季度注采调整与生产运行分析》、《渤中34-8油田躺井治理与检泵作业月报-202701》'
      ]),
      citations: null
    },
    lineage: {
      '① 口径': '日产液量（方）（单位：方）——指标台账注册声明：日产计量的日产液量——源 oil_production_daily.liquid_output（R5·A.2）；agg 读模型绑定列 agg.fct_daily_metering.liquid_output（99 §2.12），口径随答案标注',
      '② 来源表': 'agg.fct_daily_metering（agg 星型读模型 · 即汇总层「日产计量表」——99 册 §2.12/D6 star_model，机器名＝A1 解释链②冻结）⋈ agg.dim_well（井维度·按井号）⋈ agg.dim_date（日期维度·按日期）',
      '③ 过滤条件': '时间＝2026-01-01～2026-08-30 [2026-01-01, 2026-08-31)',
      '　└（权限注入）': '数据域＝全量——行级注入经 M-01 两步缝拼入 WHERE，不靠模型自觉（预埋期谓词恒空＝恒真；真分权只换谓词生产实现，注入点形状冻结）（actor＝aqiang · 落点 agg.fct_daily_metering——谓词随执行并语句）',
      '④ 数据截至批次': '批次 b-a1a61db9f458 · 汇总层水位 2026-08-31（承诺 T-1 · 落后 37 天 · 超期）',
      '⑤ 收口注记': 'LIMIT 50——强制限量纪律：没写补默认 50、超 200 截到 200，只封顶不抬底'
    },
    limit: {
      hit: true,
      rows: 50
    },
    durationS: 18.5,
    createdAt: '2026-10-17 09:12:41',
    legacy: false
  },
  {
    id: 't-split',
    label: '分列轮（多来源说法不一）',
    kind: 'ask',
    question: '去年各井含水率是多少？',
    runId: 'run-f2a0dec7',
    runStatus: 'completed',
    phase: 'done',
    closed: 'done',
    steps: [
      {
        seq: 1,
        station: 'decision',
        title: '模型调用：understand'
      },
      {
        seq: 2,
        station: 'decision',
        title: '模型调用：decision'
      },
      {
        seq: 3,
        station: 'decision',
        title: '澄清 r1：分解 1 子问题'
      },
      {
        seq: 4,
        station: 'decision',
        title: '模型调用：decision'
      },
      {
        seq: 5,
        station: 'decision',
        title: '前置条件机：s1=allow'
      },
      {
        seq: 6,
        station: 'execute',
        title: 'doc_retrieve：ok（子问题 s1）'
      },
      {
        seq: 7,
        station: 'answer',
        title: '模型调用：answer'
      },
      {
        seq: 8,
        station: 'answer',
        title: '起草答案'
      },
      {
        seq: 9,
        station: 'verify',
        title: '核验：支撑 4｜改写 2｜分源 否'
      },
      {
        seq: 10,
        station: 'answer',
        title: '答案收口'
      }
    ],
    tools: [
      {
        seq: 6,
        tool: 'doc_retrieve',
        status: 'ok',
        message: ''
      }
    ],
    materials: [
      {
        index: 1,
        source: '《C-渤中34-5油田三季度注水调整与生产运行分析》',
        trust: 'report',
        content: joinText([
          '七、注水井分层测试汇总（三季度）━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━　　井号　　测试日期　　I 层吸水　II 层吸水　III 层吸水　全井吸水指数(m³/d/MPa)',
          '　　W-51　　9 月 5 日　 62%　　　 28%　　　 10%　　　　 21.6',
          '　　W-52　　9 月 12 日　54%　　　 33%　　　 13%　　　　 8.9',
          '　　W-57　　7 月 18 日　41%　　　 38%　　　 21%　　　　 33.4W-57 井为分层均衡型注水井，本次列为对照组，不参与本轮治理。分层测试频次要求：欠注井每季度一次、正常井每半年一次；测试停注对月注水量的影响已在 2.1 表中如实体现（8 月注水量 13.5 万方含 W-56 停注 6 天影响约 0.2 万方）。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        ])
      },
      {
        index: 2,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: '〔节级摘要｜《A-W11井完井工程报告》·章节 04 第四章 防砂设计与实施｜覆盖 4 支切片〕易出砂储层，地层砂粒度中值0.18mm，均匀系数3.2；结合邻井W-09未砂堵、W-07筛管堵塞历史，按防砂完井设计。采用精密冲缝筛管（Star-PS型）适度防砂，防砂精度150μm，筛管外径5-1/2″，缝密320缝/米，按d10挡砂比准则设计；未采用砾石充填（均质性好、船日限制）。筛管柱组合：丝堵+密封+7″筛管（2380–2419m）+盲管+悬挂器（坐挂2205.4m，9-5/8″套管内），φ118mm通井规全井段通过无遇阻；预留20/40目砾石挤压充填应急预案。'
      },
      {
        index: 3,
        source: '《Y-21井完井工程报告》',
        trust: 'report',
        content: '〔节级摘要｜《Y-21井完井工程报告》·章节 04 第四章 防砂设计与实施｜覆盖 4 支切片〕Y-21井地层砂粒度中值0.21mm，泥质含量5.8%，属胶结疏松易出砂层；邻井Y-23未防砂出砂，Y-19砾石充填有效。防砂方式选用Star-PSⅡ型精密冲缝筛管（5-1/2″），防砂精度175μm，缝密320缝/米，基于d10挡砂比设计，不采用砾石充填。筛管柱组合：丝堵+密封总成+筛管（2756.0～2824.0米，68.0米，跨三射孔段）+盲管+双密封总成。φ148mm通井规通过无阻，预备20/40目砾石挤压充填预案。'
      },
      {
        index: 4,
        source: '《B-渤中34-5油田躺井治理与检泵作业月报-202608》',
        trust: 'report',
        content: '4.2 W-24 井杆断（短周期案例）W-24 井检泵周期仅 295 天，为去年 11 月补孔改层井。断点 1650 米，检查发现为新旧杆混配段（新杆 D 级、旧杆 C 级混用），旧杆强度不足先断。教训：改层加深泵挂后未按新工况整体校核杆柱，混配段应力超出旧杆许用范围。本次作业已整串更换 D 级杆，并按加深后的泵挂重新设计杆柱组合（一级杆 18 毫米×520 米＋二级杆 22 毫米×840 米＋三级杆 19 毫米×840 米，待复算确认）。'
      },
      {
        index: 5,
        source: '《B-渤中34-5油田躺井治理与检泵作业月报-202608》',
        trust: 'report',
        content: '一、月度生产与躺井总体情况━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━本月渤中 34-5 油田平均开井数 156 口（月初开井 154 口、月末 158 口，均值取 156），机械采油井全部为抽油机井（无电潜泵生产井）。当月发生躺井 7 井次，躺井率 4.5%（口径：当月躺井井次 ÷ 当月平均开井数 × 100%，作业区统计口径；与开发部按年累计口径的躺井率不可直接对比）。同比看，去年 8 月躺井 9 井次、躺井率 5.8%，今年同比下降 1.3 个百分点；环比 7 月（6 井次、3.8%）上升 0.7 个百分点，主因 8 月高温期地面设备故障增多。当月抽油机时率 94.2%，同比提高 0.8 个百分点，环比提高 0.3 个百分点。时率损失构成中，躺井停产损失占 2.1 个百分点，计划性检修占 1.9 个百分点，待机占 1.8 个百分点。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      },
      {
        index: 6,
        source: '《C-渤中34-5油田三季度注水调整与生产运行分析》',
        trust: 'report',
        content: '〔节级摘要｜《C-渤中34-5油田三季度注水调整与生产运行分析》·二、注水运行｜覆盖 2 支切片〕三季度月注水量13.5～14.1万m³，月产液量14.42～15.35万m³，季度累计注水量41.4万m³、产液量44.63万m³，月注采比0.90→0.91→0.98，季度均值0.93，长期低于1.0，累计亏空扩大至−128.6万m³。存水率0.68与上季度持平，注水利用率良好。14口注水井中W-51（吸水剖面不均，欠注20%）和W-52（近井堵塞，欠注35%）两口井欠注，W-56测试停注6天已恢复。'
      },
      {
        index: 7,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: '第四章 防砂设计与实施━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      },
      {
        index: 8,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: '4.1 出砂风险评估依据三颗岩心样粒度分析，地层砂粒度中值 0.18 毫米，均匀系数 3.2，属易出砂储层；结合邻井 W-09 井生产 14 个月未见砂堵、但 W-07 井（同层位）曾出现筛管堵塞的历史，本井按防砂完井设计。'
      },
      {
        index: 9,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: joinText([
          '4.2 防砂方式与参数防砂方式：精密冲缝筛管适度防砂（不砾石充填）。　　项目　　　　　　　参数　　筛管类型　　　　　精密冲缝筛管（Star-PS 型）',
          '　　防砂精度　　　　　150 微米（0.15 毫米）',
          '　　筛管外径　　　　　5-1/2″　　缝密　　　　　　　320 缝/米　　挡砂机制　　　　　地层砂架桥规则（d10 挡砂比设计）按挡砂比设计准则，筛管防砂精度取地层砂粒度中值（0.18 毫米）的约 0.83 倍即 150 微米，允许细粉产出、阻挡骨架砂。本井未采用砾石充填：一是油层均质性较好（层内渗透率变异系数 0.42），二是充填作业占船日 3.5 天，经济性评价不划算。若后期出砂加剧，预备井内补下 20/40 目砾石挤压充填的应急预案（砾石尺寸按孔眼充填准则预留）。'
        ])
      },
      {
        index: 10,
        source: '《A-W11井完井工程报告》',
        trust: 'report',
        content: '4.3 防砂实施筛管柱组合（自下而上）：丝堵＋密封＋7″ 精密冲缝筛管（2380～2419 米，跨三个射孔段）＋隔离液＋7″ 盲管＋悬挂器（坐挂于 9-5/8″ 生产套管内 2205.4 米）。筛管下入过程见第六章 6.2 节（遇阻处理）。筛管就位后通井规（φ118 毫米×2.0 米）全井段通过无遇阻。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      },
      {
        index: 11,
        source: '《Y-21井完井工程报告》',
        trust: 'report',
        content: '第四章 防砂设计与实施━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      },
      {
        index: 12,
        source: '《Y-21井完井工程报告》',
        trust: 'report',
        content: '4.1 出砂风险评估五颗密闭取心样粒度分析：地层砂粒度中值 0.21 毫米，均匀系数 4.1，泥质含量 5.8%，属胶结疏松易出砂储层。邻井证据：Y-23 井同层位未防砂投产 8 个月后井口取样见砂（见第十章）；Y-19 井砾石充填生产 19 个月未见砂堵。本井按防砂完井设计。'
      },
      {
        index: 13,
        source: '《Y-21井完井工程报告》',
        trust: 'report',
        content: joinText([
          '4.2 防砂方式与参数防砂方式：精密冲缝筛管适度防砂（不砾石充填）。　　项目　　　　　　　参数　　筛管类型　　　　　精密冲缝筛管（Star-PSⅡ 型）',
          '　　防砂精度　　　　　175 微米（0.175 毫米）',
          '　　筛管外径　　　　　5-1/2″　　缝密　　　　　　　320 缝/米　　挡砂机制　　　　　地层砂架桥规则（d10 挡砂比设计）按挡砂比设计准则，防砂精度取地层砂粒度中值（0.21 毫米）的约 0.83 倍即 175 微米，允许细粉产出、阻挡骨架砂。本井不用砾石充填：层内均质性较好（变异系数 0.38）；充填作业占船日 4.0 天，经济性不划算；若出砂加剧，预备补下 20/40 目砾石挤压充填预案。'
        ])
      },
      {
        index: 14,
        source: '《Y-21井完井工程报告》',
        trust: 'report',
        content: '4.3 防砂实施筛管柱组合（自下而上）：丝堵＋密封总成＋5-1/2″ 精密冲缝筛管（2756.0～2824.0 米，共 68.0 米，跨三个射孔段含夹层）＋5-1/2″ 盲管（2824.0～2951.6 米）＋双密封总成（插入尾管回接密封筒）。下入遇阻处理见 6.1 节。筛管就位后通井规（φ148 毫米×1.2 米）通过无二次遇阻。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      },
      {
        index: 15,
        source: '《C-渤中34-5油田三季度注水调整与生产运行分析》',
        trust: 'report',
        content: joinText([
          '二、注水运行━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━2.1 注水月度数据',
          '　　项目　　　　　　　　7 月　　8 月　　9 月　　季度合计',
          '　　月注水量(万m³)　　　13.8　　13.5　　14.1　　41.4',
          '　　月产液量(万m³)　　　15.35　 14.86　 14.42　 44.63',
          '　　月注采比　　　　　　0.90　　0.91　　0.98　　0.93',
          '　　月注水井开井(口)　　14　　　14　　　14注采比（口径：月注水量 ÷ 月产液量，体积折算，与台账一致）三季度均低于 1.0，季度累计 0.93。9 月上调注水后月注采比回升至 0.98、已进入合理区间（0.95～1.05）但尚未站稳，整体仍处于补欠注的追赶状态。2.2 累积亏空与存水率截至 9 月 30 日，油田累积亏空 −128.6 万方（累积注水量 − 累积产液量，负值为亏空），较二季度末扩大 3.2 万方。存水率 0.68，与二季度持平，注水利用率尚好，主要矛盾在注得不够而非注得无效。2.3 欠注井情况14 口注水井中 2 口欠注：　　井号　　配注(m³/d)　实注(m³/d)　欠注率　原因初判'
        ])
      },
      {
        index: 16,
        source: '《C-渤中34-5油田三季度注水调整与生产运行分析》',
        trust: 'report',
        content: joinText([
          '　　W-51　　180　　　　 144　　　　 20%　　 层间矛盾——吸水剖面严重不均',
          '　　W-52　　150　　　　 97.5　　　　35%　　 近井地带堵塞（注压升高 1.8 MPa）另：W-56 井于 8 月 14～19 日吸水指示曲线测试停注 6 天，测试后注水正常，不计入欠注。W-51 吸水剖面测试（9 月 5 日）显示三段吸水严重不均：I 层吸水 62%、II 层 28%、III 层仅 10%，III 层基本不吸。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
        ])
      },
      {
        index: 17,
        source: '检索供给窗声明（截断显式）',
        trust: 'notice',
        content: '召回 60 支/送窗 16 支；已召回未送窗 44 支；矛盾来源同窗并立（各留代表支）：《C-渤中34-5油田三季度注水调整与生产运行分析》、《A-W11井完井工程报告》、《Y-21井完井工程报告》、《B-渤中34-5油田躺井治理与检泵作业月报-202608》；缺位来源（预算未及）：《渤中34-8油田一季度注采调整与生产运行分析》、《渤中34-8油田躺井治理与检泵作业月报-202701》；节级摘要展开节内切片 +10 支（摘要命中→节内补席）'
      },
      {
        index: 18,
        source: '检索供给窗声明（缺位名单）',
        trust: 'report',
        content: '检索窗注记：缺位来源（预算未及）：《渤中34-8油田一季度注采调整与生产运行分析》、《渤中34-8油田躺井治理与检泵作业月报-202701》'
      }
    ],
    notices: [
      {
        type: 'unsupported_claim',
        gates: [],
        content: '核验步删去无据断言 2 行（EB3 D3：真无据断言删句、不贴前缀——禁止无据断言进答案；留痕＝rewrites 逐行原句 ＋ 本计数）'
      }
    ],
    citations: [
      {
        index: 1,
        source: '《C-渤中34-5油田三季度注水调整与生产运行分析》',
        source_id: 'f64',
        trust: 'report'
      },
      {
        index: 2,
        source: '《A-W11井完井工程报告》',
        source_id: 'ensum-71e64e896dbf',
        trust: 'report'
      },
      {
        index: 3,
        source: '《Y-21井完井工程报告》',
        source_id: 'ensum-0f09b562af3f',
        trust: 'report'
      },
      {
        index: 4,
        source: '《B-渤中34-5油田躺井治理与检泵作业月报-202608》',
        source_id: 'f37',
        trust: 'report'
      },
      {
        index: 5,
        source: '《B-渤中34-5油田躺井治理与检泵作业月报-202608》',
        source_id: 'f32',
        trust: 'report'
      },
      {
        index: 6,
        source: '《C-渤中34-5油田三季度注水调整与生产运行分析》',
        source_id: 'ensum-e2e7ea3f358d',
        trust: 'report'
      },
      {
        index: 7,
        source: '《A-W11井完井工程报告》',
        source_id: 'f13',
        trust: 'report'
      },
      {
        index: 8,
        source: '《A-W11井完井工程报告》',
        source_id: 'f14',
        trust: 'report'
      },
      {
        index: 9,
        source: '《A-W11井完井工程报告》',
        source_id: 'f15',
        trust: 'report'
      },
      {
        index: 10,
        source: '《A-W11井完井工程报告》',
        source_id: 'f16',
        trust: 'report'
      },
      {
        index: 11,
        source: '《Y-21井完井工程报告》',
        source_id: 'f83',
        trust: 'report'
      },
      {
        index: 12,
        source: '《Y-21井完井工程报告》',
        source_id: 'f84',
        trust: 'report'
      },
      {
        index: 13,
        source: '《Y-21井完井工程报告》',
        source_id: 'f85',
        trust: 'report'
      },
      {
        index: 14,
        source: '《Y-21井完井工程报告》',
        source_id: 'f86',
        trust: 'report'
      },
      {
        index: 15,
        source: '《C-渤中34-5油田三季度注水调整与生产运行分析》',
        source_id: 'f53',
        trust: 'report'
      },
      {
        index: 17,
        source: '检索供给窗声明（截断显式）',
        source_id: 'window_note',
        trust: 'notice'
      }
    ],
    understanding: joinText([
      '理解：问去年各井的含水率是多少。',
      '指标候选：含水率'
    ]),
    answerText: joinText([
      '去年各井含水率是多少？据现有材料，未找到覆盖「去年（2025 年）各井含水率」这一问的取数依据——所引报告未披露 2025 年全油田分井含水率明细。已检索到的报告覆盖范围如下：- 渤中 34-5 油田三季度注水调整与生产运行分析（2025 年 7–9 月）：仅披露油田级月注水量、月产液量、注采比与累积亏空 [6][15]，未列分井含水率。',
      '- 渤中 34-5 油田躺井治理与检泵作业月报（2026-08）：仅披露当月抽油机时率与时率损失构成 [5]，未列分井含水率。',
      '- W-11 井、Y-21 井完井工程报告：仅披露防砂设计与出砂风险评估 [2][7][8][9][10][3][11][12][13][14]，未含含水率。',
      '- W-24 井杆断案例 [4]：为检泵作业类事实，未含含水率。口径说明：台账「含水率」指标当前为未绑定态（agg 事实表未落该列），单井日度数据源在 oil_production_daily.water_cut，但缺乏 2025 年分井含水率的报告级披露，本次检索未命中。去年分井含水率明细暂不可答。未覆盖来源：渤中 34-8 油田一季度注采调整与生产运行分析、渤中 34-8 油田躺井治理与检泵作业月报（2027-01）——本次检索窗未送入，如需覆盖该油田 2025 年数据请补充指明。'
    ]),
    verdicts: [
      {
        supported: 4,
        rewritten: 2,
        split: 0,
        cited: [
          1,
          2,
          3,
          4,
          5,
          6,
          15,
          17
        ],
        attribution: true,
        subtype: 'verify'
      }
    ],
    blackbox: {
      run_id: 'run-f2a0dec7',
      question: '去年各井含水率是多少？',
      status: 'completed',
      error: '',
      stored: true,
      bytes: 41701,
      counts: {
        messages: 9,
        dialogue: 0,
        process_notes: 5,
        observations: 18,
        steps: 10
      }
    },
    supplement: {
      lineage: null,
      attribution: null,
      split: joinText([
        '互不一致——各来源说法如下，按来源分别列出：',
        '[9] 《A-W11井完井工程报告》 · f15：4.2 防砂方式与参数防砂方式：精密冲缝筛管适度防砂（不砾石充填）。　　项目　　　　　　　参数　　筛管类型　　　　　精密冲缝筛管（Star-PS 型）',
        '　　防砂精度　　　　　150 微米（0.15 毫米）',
        '　　筛管外径　　　　　5-1/2″　　缝密　　　　　　　320 缝/米　　挡砂机制　　　　　地层砂架桥规则（d10 挡砂比设计）按挡砂比设计准则，筛管防砂精度取地层砂粒度中值（0.18 毫米）的约 0.83 倍即 150 微米，允许细粉产出、阻挡骨架砂。本井未采用砾石充填：一是油层均质性较好（层内渗透率变异系数 0.42），二是充填作业占船日 3.5 天，经济性评价不划算。若后期出砂加剧，预备井内补下 20/40 目砾石挤压充填的应急预案（砾石尺寸按孔眼充填准则预留）。',
        '[13] 《Y-21井完井工程报告》 · f85：4.2 防砂方式与参数防砂方式：精密冲缝筛管适度防砂（不砾石充填）。　　项目　　　　　　　参数　　筛管类型　　　　　精密冲缝筛管（Star-PSⅡ 型）',
        '　　防砂精度　　　　　175 微米（0.175 毫米）',
        '　　筛管外径　　　　　5-1/2″　　缝密　　　　　　　320 缝/米　　挡砂机制　　　　　地层砂架桥规则（d10 挡砂比设计）按挡砂比设计准则，防砂精度取地层砂粒度中值（0.21 毫米）的约 0.83 倍即 175 微米，允许细粉产出、阻挡骨架砂。本井不用砾石充填：层内均质性较好（变异系数 0.38）；充填作业占船日 4.0 天，经济性不划算；若出砂加剧，预备补下 20/40 目砾石挤压充填预案。',
        '[10] 《A-W11井完井工程报告》 · f16：4.3 防砂实施筛管柱组合（自下而上）：丝堵＋密封＋7″ 精密冲缝筛管（2380～2419 米，跨三个射孔段）＋隔离液＋7″ 盲管＋悬挂器（坐挂于 9-5/8″ 生产套管内 2205.4 米）。筛管下入过程见第六章 6.2 节（遇阻处理）。筛管就位后通井规（φ118 毫米×2.0 米）全井段通过无遇阻。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━',
        '[14] 《Y-21井完井工程报告》 · f86：4.3 防砂实施筛管柱组合（自下而上）：丝堵＋密封总成＋5-1/2″ 精密冲缝筛管（2756.0～2824.0 米，共 68.0 米，跨三个射孔段含夹层）＋5-1/2″ 盲管（2824.0～2951.6 米）＋双密封总成（插入尾管回接密封筒）。下入遇阻处理见 6.1 节。筛管就位后通井规（φ148 毫米×1.2 米）通过无二次遇阻。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      ]),
      citations: null
    },
    lineage: null,
    limit: null,
    durationS: 10.5,
    createdAt: '2026-10-17 09:14:02',
    legacy: false
  },
  {
    id: 't-legacy',
    label: '旧版历史轮（降级）',
    kind: 'ask',
    question: '什么是躺井？',
    runId: 'run-307959ec',
    runStatus: 'completed',
    phase: 'done',
    closed: 'done',
    steps: [],
    tools: [],
    materials: [],
    notices: [],
    citations: [],
    understanding: '',
    answerText: joinText([
      '「躺井」是作业区口语，对应的规范术语为「停产待检泵」[1]。',
      '',
      '注：本观察仅给出术语对应关系，未载「停产待检泵」的完整业务定义；如需更详细的定义说明，请告知。',
      '',
      '引用：',
      '[1] sem_term#4 · 4（ledger）'
    ]),
    verdicts: [],
    blackbox: null,
    supplement: {
      lineage: null,
      attribution: null,
      split: null,
      citations: null
    },
    lineage: null,
    limit: null,
    durationS: null,
    createdAt: '2026-10-13 00:22:53',
    legacy: true
  }
]
