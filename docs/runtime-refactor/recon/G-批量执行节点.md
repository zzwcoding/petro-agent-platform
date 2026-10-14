# G·现状调研报告

- 锚定：commit e4b75f1（行号以此为准）
- 覆盖：appv2/runtime/graph.py L3225-L3552
- def/class 清单（逐一全列，含行号区间）：
  - `_make_batch`（L3225-L3550）：工厂函数，签名 `(deps: LoopDeps) -> Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]`；L3550 `return batch_node`
  - `batch_node`（L3236-L3548）：内层 async 节点函数，本段唯一执行体
  - 段内无 class；L3225-L3234 为 `_make_batch` 的外层 docstring（相位④固定代码说明），L3552 起进入下一节（`# ---------- 节点五：observe ----------`，L3553）
  - 本段无其他 def：已用 awk 对 L3225-L3552 全量枚举，仅上述两条

---

### `_make_batch`（L3225-L3550）｜相位④批量执行的节点工厂：包住 deps 缝，返回 batch_node
- 消费：deps（闭包捕获，节点内逐处使用——registry/bus/store/guide 等缝）
- 装配：无（本函数不碰链尾；链尾追加行为全部在 batch_node 内）
- 调用：caller=无（工厂本身不调 LLM/工具，只构造闭包）
- 分支表（穷尽）：
  1. 恒等 → 返回 `batch_node`（L3550） → 图装配侧 `_node_of(_make_batch(deps))` 挂 `NODE_BATCH`（`build_graph` four_phase 支，L4077）
- 副作用：无（工厂零 IO、零 emit）
- 返回：`Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]`
- 规则条目：
  - R-G-00（工厂级）批量节点不吃构造期参数：全部判定用到的预算/簿记都从 state 与 deps 现读——节点体可在任意 checkpoint 恢复段重入
- 耦合：`Callable`/`Coroutine`/`Any`（collections.abc、typing）；`RunState`（appv2.runtime.state）；`LoopDeps`（本文件 L344）
- 疑点：无（另见 batch_node 条目）

### `batch_node`（L3236-L3548）｜逐子问题执行 ready 过滤后的支：调工具、观察入栈与索引、台账入链、缺位回捞、挂起/回炉/直答三种去向裁决
- 消费：state.budget（max_rounds、tool_timeout_seconds）、state.question_group（经 `_group_subtasks`）、state.tool_matches、state.precondition_verdicts、state.subtask_results、state.observations、state.steps、state.process_notes、state.messages、state.executed_payloads、state.window_miss_marks、state.chain_switch_marks、state.rounds、state.consecutive_asks、state.notices、state.run_id、state.actor（经 `_ctx_of`）、state.metric_candidates、state.approved_ids、state.budget_hit/state.deadline_monotonic（经 `_gate_or_none`）；deps.registry.call、deps.bus.emit
- 装配：链尾追加 `{"role": "user", "content": "〔工具执行台账〕子问题 <sid>：<tool>，参数指纹 <指纹前 12 字>… → <outcome>。"}`——**逐支、就地**追加（L3360-L3363，V2-80h §4.4 工具台账行）；一子问题一条，ok/ask/failed 三形都有（outcome 三态措辞见分支表）；本节点不发 assistant 行、不做相位合同包追加
- 调用：caller=`_invoke_tool(deps, state, tool_name, args)`（L3297，内部 `asyncio.wait_for(deps.registry.call(tool_name, args, _ctx_of(state)), timeout=state.budget["tool_timeout_seconds"]缺省30.0)`）；解析＝工具返回值经 `_result_dict(raw)` 投影（`{"status","observations","ask","error"}`，L1164）；失败怎么办：`raw is None`（超时）→ `_timeout_result(tool_name, timeout)`（status=failed、category=retryable、hint=「可重试——同参重调一次」）；工具自身 failed → 本节点按 error.category 分两路（refused=终局／其余=回炉面），统一 `continue` 跑余下子问题
- 分支表（穷尽）：
  1. L3237 `_gate_or_none` 非 None（时长闸常开、轮数闸本节点关闭）→ 直接 `return converged`（收敛更新：budget_hit/notices/answer/draft_kind/status/next_intent=answer） → NODE_ANSWER
  2. L3240 问题组为空（`_group_subtasks` 得空列）→ `return {"next_intent": INTENT_DECISION}` → clarify（恢复段边界兜底）
  3. L3267 子问题无 verdict 记录或 verdict.state ∉ {pass, note}（blocked_ask/blocked_refuse 或无记录）→ `continue` 跳过 → 本支零执行、零簿记（余下支继续）
  4. L3269 verdict.state==note 且 verdict.chain_switch_trigger 真 且 sid ∈ state.chain_switch_marks → `continue` 跳过（V2-43 换链回炉标记面） → 回炉①改链重决策侧处理
  5. L3276 subtask_results 入口快照中同 id 状态 == "ok" → `continue` 跳过（R4 成功不重跑） → 该支不产生任何新事件
  6. L3280 match.chain == "data" → tool=data_query；args={"plan_draft": plan_exec}（plan 去 "caliber_key" 键，L3282-L3286）；fingerprint=json({plan: plan_exec, retrieval_need: null}) → 继续执行
  7. L3291 match.chain 非 "data"（含 "" / "knowledge"）→ tool=doc_retrieve；args=retrieval_need 原样（无则 {}）；fingerprint=json({plan: null, retrieval_need: args}) → 继续执行
  8. L3297 raw is None（超时）→ result=_timeout_result（failed/retryable） → 落入下方 failed 支（分支 13/14）
  9. L3304 逐观察编索引：entry=dict(obs)；entry["index"]=len(observations)+offset（offset 从 1 起）；entry["trust"]=trust_of(entry)；aggregated += len(indexed) → 无分支
  10. L3312 本支 indexed 中首个 locator.kind=="window_miss" 的观察 → miss_obs 记为缺位信号源；无则 miss_obs=None → 决定 ok 支三岔（分支 11/12/13）
  11. L3364 status==ok 且（miss_obs 在场 且（sid ∈ marks 或 fingerprint ∈ marks.values()））→ results 追加该支 ok＋reason「缺位回捞已用尽（一次为界）…」 → 不消耗轮、不回炉；余下支继续
  12. L3390 status==ok 且 miss_obs 在场 且 int(state.rounds) < max_rounds 且 `recall_relevant(question, miss_obs.content)` 真 → marks[sid]=fingerprint；results 追加该支 failed＋reason（引缺位注记原文＋「缺位回捞白场」话术）；notice={type:"window_miss_reentry"} emit；recall_notices 累积 → 收尾按 failed 判定（分支 20/21），去 clarify 回炉
  13. L3422 status==ok 且无 miss_obs（或门条件不成立）→ results 追加该支 ok（obs_count/fingerprint 实录） → 原形零漂移；余下支继续
  14. L3431 status==ok 收尾扫 indexed：locator.kind=="notice" 的观察 → emit notice（type=locator.notice_type 缺省 "notice"）；随后每支 emit observation{index,source,content,trust} → 事件面
  15. L3454 status==ask → frame=dict(result.ask)；若 frame.kind=="external_table_approval" 且 detail.approval_id 非空 → detail["approval_id"]=reseed_approval_id(run_id, seed)、frame["detail"]=detail；emit ask{frame,run_id}；pending_frame=frame；`break` 跳出整循环 → 余下子问题本轮不执行、待恢复后随批重入
  16. L3467 status==failed 且 error.category=="refused" → results 去同 id 后追加该支 status="refused"（终局拒答）；emit notice type="subtask_refused" → `continue`，去汇总如实陈述
  17. L3467 status==failed 且 category 为其他（bad_args/retryable/空）→ results 去同 id 后追加该支 status="failed"（回炉面）；emit notice type="subtask_failed" → `continue`，收尾按 failed 判定
  18. L3492 循环结束（正常走完或 break 跳出）→ 恒记录汇聚步：seq=len(steps)+1、title=`批量汇聚 {aggregated} 支`、emit step{step=observe}、steps 追加 `_step_record(..., STEP_OBSERVE, ..., payload={"phase":"batch","count":aggregated})`（0 支也记） → 收尾裁决
  19. L3512 pending_frame 非 None（本批曾 break 于引擎 ask）→ updates 加 pending_ask=frame、next_intent=INTENT_DECISION → **return（挂起）** → clarify（interrupt 在 clarify 入口）
  20. L3520 state.precondition_verdicts 存在 state=="blocked_ask" 且 consecutive_asks+1 >= 6 → notice type="clarify_capped" emit；updates["notices"]=[*state.notices, notice]；`_direct_answer(updates, _clarify_capped_answer(state))`（draft=材料如实交付文本或 NO_MATERIAL_SHELL、draft_kind="direct"） → **return（截断直答）** → answer
  21. L3535 同上 unresolved 非空但未达上限 → updates["consecutive_asks"]=consecutive；pending_ask=unresolved[0].ask；next_intent=INTENT_DECISION；emit ask{frame,run_id} → **return（blocked_ask 挂起）** → clarify
  22. L3542 results 中存在 status=="failed" 且 int(state.rounds) < max_rounds → next_intent=INTENT_DECISION → **return（失败子集回炉①）** → clarify
  23. L3547 无 failed，或轮预算已耗尽（failed 在但 rounds >= max_rounds）→ next_intent=INTENT_ANSWER → **return（带部分结果如实收口）** → answer
- 副作用：
  - emit 事件：`tool`（L3326，per 支：{tool,status,seq,message}）；`step`（L3332 STEP_EXECUTE 逐支、L3495 STEP_OBSERVE 一次）；`notice`（L3420 window_miss_reentry、L3433 notice 类观察分型、L3480 subtask_refused/subtask_failed、L3531 clarify_capped）；`observation`（L3445，逐支逐观察 {index,source,content,trust}）；`ask`（L3464 引擎帧、L3539 blocked_ask 帧）
  - step：类型 execute，标题形 `{tool_name}：{status}（子问题 {sid}）`（L3331），payload={subtask_id,chain,tool,status,fingerprint[,window_miss]}；类型 observe 一次，标题形 `批量汇聚 {aggregated} 支`（L3494），payload={phase:"batch",count}
  - notice 类型：window_miss_reentry / <locator.notice_type 缺省 "notice"> / subtask_refused / subtask_failed / clarify_capped
  - 持久化写：无（本节点只回 updates；checkpoint 落库在图调用侧）
- 返回：updates 键清单——恒有 observations、steps、process_notes、executed_payloads、subtask_results、messages（L3500-L3507）＋next_intent（各 return 前必写）；条件有 window_miss_marks（marks 与入口不等时）、notices（recall_notices 非空，或被 capped 覆盖写）、pending_ask（引擎 ask 或 blocked_ask）、consecutive_asks（blocked_ask 未达上限支）、draft＋draft_kind（capped 支经 `_direct_answer`）；三个早退形：L3238 返回收敛更新、L3241 返回 {"next_intent": INTENT_DECISION}
- 规则条目（提取业务的核心）：
  - R-G-01 入口预算闸触界（`_gate_or_none` 非 None，本节点不开轮数闸、只守时长闸）→ 不执行任何子问题，返回收敛更新 → answer
  - R-G-02 问题组为空 → 直接回决策意图，不做汇聚步、不写任何簿记 → clarify（恢复段边界兜底）
  - R-G-03 ready 过滤第一层：子问题的前置判定不是 pass/note（含无判定记录）→ 跳过不执行 → 该支零事件、零簿记
  - R-G-04 ready 过滤第二层：note＋chain_switch_trigger＋该子问题已在 chain_switch_marks → 跳过（换链回炉面） → 交回炉①改链
  - R-G-05 ready 过滤第三层：入口快照里该子问题已是 ok → 跳过（成功不重跑＝R4 指纹零重复）
  - R-G-06 data 链执行载荷＝plan_draft，plan 内的 caliber_key 在本节点被剥掉（键不传工具——caliber 只在预置条件机消费）
  - R-G-07 非 data 链一律走 doc_retrieve，参数＝match.retrieval_need 原样
  - R-G-08 执行指纹逐支实录：data 支＝json({plan,retrieval_need:null})，knowledge 支＝json({plan:null,retrieval_need})——同参判定面对得上 execute 侧单键形
  - R-G-09 单工具超时（wait_for 超时→raw None）→ 合成 failed/retryable 结果，走失败回炉面，不当异常抛出
  - R-G-10 观察入栈索引＝全局 len(observations)+本支序位（1 起），trust 由 locator.kind 确定性映射（trust_of）
  - R-G-11 缺位信号＝本支观察中 locator.kind=="window_miss" 的首条；观察在场即缺位来源名单非空
  - R-G-12 缺位回捞一次为界（簿记面）：sid 已在 marks 或本支指纹已在 marks.values() → 该支直接定 ok＋「回捞已用尽」终局注记，不再回炉
  - R-G-13 缺位回捞开门三条件同时成立（miss_obs 在场 且 rounds<max_rounds 且 recall_relevant(question, content) 真）→ 写 marks[sid]=指纹、该支定 failed（拒因携缺位注记原文＋回捞白场话术）、发 window_miss_reentry notice → 收尾回炉①（每子问题限一次、消耗一轮、不挂起不占 ask）
  - R-G-14 缺位在场但轮预算无余或名单与题面无表面关联 → 门不开，该支按 ok 原形记账（注记照常在窗，零漂移）
  - R-G-15 无缺位 → 该支 ok 原形（obs_count＋fingerprint 实录）
  - R-G-16 ok 支才入栈观察与执行指纹：observations.extend(indexed)、executed_payloads 追加 fingerprint（ask/failed 支的观察不入栈、指纹不记）
  - R-G-17 ask 支＝挂起：帧入 pending_frame、emit ask、跳出整个循环（余下子问题不执行、该支不写 subtask_results、不写 executed_payloads）→ 恢复后该支按「无 prior ok」重跑
  - R-G-18 外表审批帧（kind==external_table_approval）且 approval_id 非空 → approval_id 重种子为 `{run_id}#{engine_seed}` 回写 frame.detail → 挂起帧留痕可溯
  - R-G-19 failed 且 category==refused → 子问题终局 refused（进汇总如实陈述，不回炉）；其余 category → failed（进回炉面）
  - R-G-20 同 id 结果只留最新（先删同 id 旧条再追加新条）——防旧 failed 滞留造出假回炉环
  - R-G-21 每支执行三段留痕：execute 步（payload 携 subtask_id/chain/tool/status/fingerprint，缺位时加 window_miss 键）＋过程档案条目（_tool_note 三分类措辞）＋对话链工具台账行（user 角色）
  - R-G-22 循环收尾恒记一条 observe 步（payload.phase=="batch"、count=aggregated）——包括一支未跑与 break 跳出两形
  - R-G-23 去向优先级（return 顺序）：引擎 ask 挂起 > blocked_ask 截断直答（≥6）> blocked_ask 挂起 > 失败子集回炉（rounds<max_rounds）> 正常收口 answer
  - R-G-24 连续澄清上限：blocked_ask 在场且 consecutive_asks+1 >= CLARIFY_ASK_CAP_CONTRACT(=6) → 不挂起，发 clarify_capped notice＋确定性直答（已取得材料如实交付，无材料则 NO_MATERIAL_SHELL）→ answer
  - R-G-25 blocked_ask 挂起不占轮：consecutive_asks 自增、pending_ask=首个 unresolved 帧、emit ask、intent=decision → clarify（interrupt 在此）
  - R-G-26 失败回炉不重跑成功支：只把 failed 子问题带回 clarify（成功支结果留 subtask_results）；轮预算耗尽则带部分结果直接 answer
  - R-G-27 本节点不消耗轮：rounds 只读不写（轮消耗发生在 clarify 相位）
  - R-G-28 window_miss_marks 仅在内容变化时写回（marks 为入口拷贝，内容相等则不产生该 updates 键）
- 耦合：`_gate_or_none`、`_group_subtasks`、`_payload_fingerprint`、`_invoke_tool`、`_timeout_result`、`_result_dict`、`_observations_of`、`_step_record`、`_tool_note`、`_direct_answer`、`_clarify_capped_answer`、`_subtask_result`（本文件 L3204-L3222，本段上方 30 行内接缝——被 L3381/L3400/L3426/L3475 消费）＋`LoopDeps`/`RunState`（本文件）；`trust_of`（appv2.runtime.context L61）；`recall_relevant`（appv2.tools.handlers L829）；`reseed_approval_id`（本文件 L1332）；`deps.registry.call`（appv2.tools.ToolRegistry）、`deps.bus.emit`（appv2.runtime.events.EventBus L70）；常量 `DATA_QUERY`/`DOC_RETRIEVE`、`STATE_PASS`/`STATE_NOTE`/`STATE_BLOCKED_ASK`、`STATUS_OK`/`STATUS_ASK`/`STATUS_FAILED`、`CATEGORY_REFUSED`、`ASK_EXTERNAL_TABLE_APPROVAL`（appv2.tools）、`STEP_EXECUTE`/`STEP_OBSERVE`/`INTENT_DECISION`/`INTENT_ANSWER`（appv2.runtime.state）、`MAX_ROUNDS_CONTRACT`/`CLARIFY_ASK_CAP_CONTRACT`/`NO_MATERIAL_SHELL`/`material_rows`（appv2.runtime.budget，常量值 3/6）
- 疑点（只列不判，不静默）：
  - D-G-01 L3510-L3511 先写 `updates["notices"]=[*state.notices, *recall_notices]`，L3532（同一节点调用内的 capped 分支）再以 `[*state.notices, notice]` 整体覆盖同一键——同批既有缺位回捞 notice 又达连续澄清上限时，回捞 notice 不进 state.notices（bus 事件已发过）。对照：precondition 节点同场景写法为 `[*state.notices, *extra_notices, notice]`（L3118）。
  - D-G-02 aggregated 在状态分岔之前累加（L3310）：ask/failed 子问题携带观察时计入汇聚数，但这些观察不入 observations（仅 ok 支 extend，L3365）；ask 支 break 时该支观察同样只计数不入栈。
  - D-G-03 ask 挂起支不写 subtask_results（L3454-L3466 无 results 追加）、不写 executed_payloads；但该支已 append 的 step/note/message（L3333/L3351/L3360）随 updates 返回——恢复后该支按无 prior ok 重跑，重跑会再生成一条 execute 步与一条台账行。
  - D-G-04 results_by_id 仅在入口构建一次（L3251）、循环内不刷新——问题组若同 id 重复出现，第二支的「成功不重跑」判据读的是入口快照，不是本节点内刚写入的结果。
  - D-G-05 无 verdict 记录的子问题（verdicts_by_id 缺该 sid，`verdict={}`）与 verdict 为 blocked_ask/blocked_refuse 的子问题走同一条 continue（L3267）——两种情形在本节点零区分、无独立留痕。
  - D-G-06 循环内 emit 的 subtask_failed/subtask_refused notice（L3480）与 notice 类观察的 emit（L3433）不写入 state.notices；本段只有 window_miss_reentry（L3421）与 clarify_capped（L3532）进 notices。
  - D-G-07 L3456-L3463 外表审批重种子只在 approval_id 非空时回写 `frame["detail"]`（该赋值在 if 内）——seed 为空时不重种子、detail 保持原帧值，帧仍以原样挂起。
  - D-G-08 执行步 seq 用局部 `len(steps)+1` 现算（L3320），不同于同文件他处用的 `_next_seq(state)`（基于 state.steps）——本节点内 seq 单调性依赖循环内每轮 steps.append（L3333）；汇聚步 seq 同法现算（L3493）。
  - D-G-09 L3367-L3375 注释把「消耗一轮」记在缺位回捞分支，而 L3392 判据读的是 `state.rounds`（本节点只读不写）——轮消耗实际发生在本节点之外。
  - D-G-10 匹配/判定索引键归一不一致：matches_by_id 用 `str(m.get("id"))`（None→"None"）、verdicts_by_id 用 `str(v.get("subtask_id"))`（None→"None"），而循环内 sid 用 `str(st.get("id") or "")`（None→""）——id 为空值时三键不同形。
  - D-G-11 failed 支写的 subtask_results 条目不传 obs_count/fingerprint（L3474-L3479），取 `_subtask_result` 缺省 0/""；同支在更早的 failed 谓词（L3541）只按 status 判定，指纹面在 failed 行上无实录。
  - D-G-12 本节点不重跑/不回炉 ask 支也不为其留 failed 标记：若恢复后重跑再得 ask 同帧，可反复挂起（受 clarify 侧 consecutive_asks 上限约束）；本节点内无自环保护代码。

---

## 覆盖自检
- def 清单差集：无（L3225-L3552 内 def 仅 `_make_batch`、`batch_node`，两条均已覆盖；段内无 class）
- 本段 emit 事件名全集：`tool`、`step`、`notice`、`observation`、`ask`（共 5 种；notice 分型：window_miss_reentry、<locator.notice_type 缺省 notice>、subtask_refused、subtask_failed、clarify_capped）
- 本段读写的 state 字段全集：
  - 读：budget、question_group、tool_matches、precondition_verdicts、subtask_results、observations、steps、process_notes、messages、executed_payloads、window_miss_marks、chain_switch_marks、rounds、consecutive_asks、notices、run_id、actor、metric_candidates、approved_ids、budget_hit、deadline_monotonic（后二经 `_gate_or_none`→`budget_gate_hit`）
  - 写（updates 键）：observations、steps、process_notes、executed_payloads、subtask_results、messages、window_miss_marks、notices、pending_ask、next_intent、consecutive_asks、draft、draft_kind（末二经 `_direct_answer`）；早退形另写 budget_hit、answer、status（经 `_converge`）
- 本段引用的外部符号全集（本文件内定义的除外）：
  - appv2.runtime.context：trust_of
  - appv2.runtime.budget：MAX_ROUNDS_CONTRACT、CLARIFY_ASK_CAP_CONTRACT、NO_MATERIAL_SHELL、material_rows
  - appv2.runtime.state：STEP_EXECUTE、STEP_OBSERVE、INTENT_DECISION、INTENT_ANSWER（及类型 RunState）
  - appv2.runtime.events：EventBus.emit
  - appv2.tools：DATA_QUERY、DOC_RETRIEVE、STATE_PASS、STATE_NOTE、STATE_BLOCKED_ASK、STATUS_OK、STATUS_ASK、STATUS_FAILED、CATEGORY_REFUSED、ASK_EXTERNAL_TABLE_APPROVAL、ToolRegistry.call、recall_relevant
  - langgraph：无直接引用（仅 `build_graph` 装配侧）
