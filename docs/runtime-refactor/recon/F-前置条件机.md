# F·现状调研报告

- 锚定：commit e4b75f1（行号以此为准；本段在 e4b75f1→HEAD（085b294）间零 diff，行号两处一致）
- 覆盖：appv2/runtime/graph.py L2844-L3225
- def/class 清单：逐一全列（含行号区间），不得省略
  - `_make_precondition`（def，L2844-L3150）——相位③工厂：返回 `precondition_node`
  - `precondition_node`（async def，L2849-L3148；嵌套于 `_make_precondition`）——前置条件机节点本体
  - `_refusal_with_hint`（def，L3153-L3158）
  - `_humanize_refusal`（def，L3161-L3171）
  - `_watermark_date_of`（def，L3174-L3186）
  - `_data_wells_set`（def，L3189-L3201）
  - `_subtask_result`（def，L3204-L3222）
  - 无 class；段内无模块级分节注释标题（L2889-L2896、L3024-L3025、L3110 内注释均为函数内说明）。L3223-L3224 空行，L3225 起为下一段 `_make_batch`（本段边界外，仅列不析）。
- 本段定位（行号锚点）：`precondition_node` 是四相位循环的相位③（前置条件机）——纯固定代码零 LLM（docstring L2847「逐子问题判四态；LLM 无权判定」），装配于 `build_graph(four_phase=True)` 的 L4072；入边两处——toolmatch 定案 `INTENT_PRECONDITION → NODE_PRECONDITION`（L4091）与 clarify 审批恢复边（`_handle_choice` 批准分支设 INTENT_PRECONDITION，L4081-L4085，注释「前置条件机重判——A2 裁决落点」）；出边路由表 L4095-L4100（batch／clarify（blocked_ask 挂起恢复→clarify interrupt）／answer）。`judge`（四态判定）在 appv2/tools/precondition.py L264-L587，本段只消费其输出。**本段全段零 LLM 调用、零工具调用，不触碰 `messages`／`contracts_appended` 链（无装配动作）**——四态判定与拒答/回炉/挂起三态消费全在固定代码。

---

### `_make_precondition`（L2844-L3150）｜相位③工厂：返回前置条件机节点（纯固定代码零 LLM——逐子问题判四态，判定权不在 LLM）
- 消费：形参 `deps: LoopDeps`（构造期仅捕获，不触字段）。
- 调用：caller=`build_graph` L4072（`builder.add_node(NODE_PRECONDITION, _node_of(_make_precondition(deps)))`，four_phase=True 装配）；工厂本身无 LLM/工具调用。
- 分支表：无（仅闭包定义与 `return precondition_node`（L3150））。
- 副作用：无。
- 返回：`precondition_node`（async callable，`Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]`）。
- 规则条目：
  - R-F-01 相位③＝纯固定代码零 LLM：四态（pass｜note｜blocked_ask｜blocked_refuse）判定权全在 `judge` 纯函数，节点只做消费面（拦放、回炉、挂起、直答）。
- 耦合：`LoopDeps`（本文件 L344-L387）、`_node_of`（L4039）。
- 疑点：无。

### `precondition_node`（L2849-L3148）｜逐子问题判定并分岔：四态放行/注记、换链回炉一次为界、审批与口径挂起、全拒直答、进批量
- 消费：`deps.bus`（事件出口）、`deps.watermark`（水位读缝）、`deps.data_wells`（井闭世界读缝）；state：`budget_hit`／`budget`／`deadline_monotonic`（经 `_gate_or_none`→`budget_gate_hit(include_rounds=False)`，L1092-L1108）、`question_group`（经 `_group_subtasks`）、`ledger_dump`、`resume_choices`、`tool_matches`、`approved_ids`、`chain_switch_marks`、`subtask_results`、`notices`、`consecutive_asks`、`steps`、`metric_candidates`、`run_id`；收敛路径另经 `_converge` 读 `observations`／`last_result`／`understanding`／`rounds`／`verdict`／`draft`／`answer`（委托面）。
- 调用：caller=图装配（入边：toolmatch 定案与 clarify 审批恢复，见本段定位）；本节点零 LLM 零工具；判定委托 `judge`（appv2/tools/precondition.py L264-L587）——纯函数无失败分支；读缝 `deps.watermark()`／`deps.data_wells()` 调用的异常由 helper 兜住（见两 helper 条目）；ask 帧原样使用 judge 产 payload（不做 reseed／不改写 detail——对比批量段对引擎源审批帧的 reseed 事实 L3456-L3463）。
- 分支表（穷尽，按代码顺序）：
  1. 入口闸（L2850-L2851）：`_gate_or_none(state, deps)`（缺省 `rounds_gate=False`＝只判时长闸；`state.budget_hit` 非空＝幂等短路返回 None）非 None → 直接 return 收敛更新（`_converge` 形：`budget_hit/notices/answer/draft_kind="direct"/status="completed"/next_intent=answer`，L1072-L1089）→ 去向 answer；本节点判定不再发生。
  2. 组空兜底（L2852-L2854）：`_group_subtasks(state)` 空列 → `return {"next_intent": INTENT_DECISION}`（零 emit、零 step、零其它键）→ 去向 clarify（恢复段边界兜底「无组＝回澄清」）。
  3. 主路径（组非空）逐支判定（L2855-L2888）：
     - 3a. `facts = ledger_facts(state.ledger_dump or {})`；`watermark = _watermark_date_of(deps)`；`data_wells = _data_wells_set(deps)`；`window_resolved`＝`state.resume_choices` 中任一 dict 且 `kind == ASK_CLARIFY`（run 级布尔，L2860-L2863）；`matches_by_id` 以 `str(m["id"])` 建索引。
     - 3b. 逐子问题调 `judge(SubtaskInput(...), facts, approved_tables=tuple(state.approved_ids), watermark, window_resolved, data_wells or None)`（L2872-L2885）——入参 `chain = match.chain or st.chain or "data"`（三级回落）、`plan=match.plan`、`retrieval_need=match.retrieval_need`；结果收 `judged`（Verdict 列）。
     - 3c. `plan_prints[sid] = _payload_fingerprint({"plan": dict(match.plan or {}), "retrieval_need": None})`（逐支全记——含未触发支；指纹恒带 `retrieval_need: None`）。
  4. 换链簿记环（L2897-L2923；`marks=dict(state.chain_switch_marks)`、`chain_pending=∅`、`chain_kinds={}`）：逐 `judged` 下标遍历——
     - 4a. `verdict.chain_switch_trigger` 为 False → 跳过（其余闸四态语义一字不动）。
     - 4b. True 且（`sid in marks` 或 `fingerprint in marks.values()`）→ `judged[index] = replace(verdict, state=STATE_BLOCKED_REFUSE, reason="换链回炉已用尽（一次为界）：坚持 data 链同参（指纹 {指纹[:12]}…在簿）——{terminal_tail}")`；`terminal_tail` 依 kind：UNBOUND→「未绑定口径如实拒答，不代答」，DOMAIN→「题眼井不在数据链井闭世界——域错如实拒答，不代答」；continue（不簿记、不入 chain_pending）。
     - 4c. True 且未簿记 → `marks[sid]=指纹`；`chain_pending.add(sid)`；`chain_kinds[sid]=kind`（`kind = verdict.chain_switch_kind or CHAIN_SWITCH_KIND_UNBOUND`——UNBOUND 是空串 `""`，空串归 UNBOUND 型）。注意：触发支判词 state 仍为 note（拦截只在 runtime 消费面）。
  5. payload 化＋step 落载（L2924-L2929）：`verdicts=[v.as_payload() for v in judged]`；`seq=_next_seq(state)`；`title="前置条件机："＋"｜".join("{subtask_id}={state}")`；`deps.bus.emit("step", {"step": STEP_DECISION, "seq": seq, "title": title})`。
  6. 归一/词面门落载（L2936-L2977）：
     - 6a. `normalized_slots={sid→normalized_slot 非空者}`；`fuzzy_ids={sid | fuzzy_window_rewrite}`。
     - 6b. 两者任一非空 → 双面改写（`state.tool_matches` 逐条 dict 拷贝＋`_group_subtasks(state)` 重投影逐条拷贝，L2944-L2974）：命中 sid 且 plan 为 dict 时——fuzzy→`window_start/window_end` 置 None（键必写）；slot→`metric_slot=归一 slot`；同 sid 两标记并存时两改都做（计划载荷子字典替换，item 浅拷贝）。
     - 6c. 两者皆空 → 双面原样复制（`list(state.tool_matches)`／`_group_subtasks(state)`，L2975-L2977）。
  7. 候选集刷新（L2980-L2986）：`canonical_slots`＝改写后 `tool_matches` 中 `chain=="data"` 且 `plan.metric_slot` 非空的 slot 去重保序（`dict.fromkeys`）。
  8. `updates` 基建（L2987-L3009）：`precondition_verdicts=verdicts`；`tool_matches=rewritten_matches`；`question_group={"subtasks": rewritten_group}`；`metric_candidates=list(canonical_slots) 或 list(state.metric_candidates)`；`steps=[*state.steps, _step_record(seq, STEP_DECISION, title, None, payload={phase:"precondition", pure_code:True, verdicts:verdicts, **({"chain_switch_marks": dict(marks)} if marks)})]`。
  9. 结果条目构造（L3010-L3052）：
     - 9a. `questions={sid→question}`（源 subtasks）。
     - 9b. `refusals`：verdicts 中 `state==STATE_BLOCKED_REFUSE` 的逐条 `{id, status:"refused", reason:原文, question, obs_count:0, fingerprint:"", chain:"data"}`（chain 硬编码 "data"）。
     - 9c. `chain_entries`：`sid in chain_pending` 的逐条 `{id, status:"failed", reason:原文+"（换链提议：回炉①改链重决策——一次为界）", question, obs_count:0, fingerprint=marks[sid], chain:"data", chain_switch:True}`。
     - 9d. `refusals` 或 `chain_entries` 非空 → `updates["subtask_results"]`：两批各自先按批内 id 集剔旧行、再 extend（批序＝先 refusals 后 chain_entries；同 id 只留最新判定）。
  10. 换链通知（L3053-L3095，仅 `chain_pending` 非空）：
      - 10a. `unbound_ids`／`domain_ids`＝按 `chain_kinds` 分列 sorted。
      - 10b. `segments` 拼接：unbound 段「子问题 {id、id} 绑定闸拒（data 链在册未绑定 agg）」；domain 段「子问题 {id、id} 题眼井不在数据链井闭世界（data 链域错成功返回——软失败域闸）」；两段以「；」相接。
      - 10c. `header`＝「换链回炉闸（V2-43）：」／含 domain_ids 时「换链回炉闸（V2-43/V2-51）：」。
      - 10d. `notice={type:"chain_switch_reentry", gates:[], content: header+segments+"——携拒因＋改链 hint 回炉①澄清相位（一次为界；坚持原链同参再触发＝直答终局，不环）"}`；emit notice；`updates["notices"]=[*state.notices, *extra_notices]`；`updates["chain_switch_marks"]=marks`。
  11. 路由分岔（L3096-L3148；`asks`＝blocked_ask 列；`executable`＝pass/note 且 `sid∉chain_pending` 列）：
      - 11a. `asks` 非空 且 `executable` 非空 → `next_intent=INTENT_BATCH` → return（部分结果先行；换链触发支已在 chain_switch_marks 落载，批量段据此跳过其执行 L3269-L3274；blocked_ask 交批量段收尾挂起 L3516-L3540）→ 去向 batch。
      - 11b. 仅 `asks` 非空（executable 空）→ `consecutive = state.consecutive_asks + 1`：
        - 11b-i. `consecutive >= CLARIFY_ASK_CAP_CONTRACT`（=6，budget.py L38）→ `notice={type:"clarify_capped", gates:[], content:"连续澄清已达上限（连续 ask ≥6）——不再挂起，带已取得材料如实直答。"}`；emit notice；`updates["notices"]=[*state.notices, *extra_notices, notice]`；`_direct_answer(updates, _clarify_capped_answer(state))` → return（draft／draft_kind="direct"／next_intent=answer）→ 去向 answer。
        - 11b-ii. 否则 → `updates["consecutive_asks"]=consecutive`；`frame=dict(asks[0].get("ask") or {})`；`updates["pending_ask"]=frame`；`updates["next_intent"]=INTENT_DECISION`（注释「挂起：interrupt 在 clarify 入口」）；`deps.bus.emit("ask", {"frame": frame, "run_id": state.run_id})` → return → 去向 clarify（interrupt 挂起）。**只取第一个 blocked_ask 的帧。**
      - 11c. `chain_pending` 非空 且 `executable` 空（asks 已排除）→ `next_intent=INTENT_DECISION` → return（纯触发组回炉①；notice 已在 10d 落）→ 去向 clarify。
      - 11d. `executable` 空（asks 空、chain_pending 空——按控制流全为 blocked_refuse）→ `lines`＝逐条 `"- [{id}] {question}——{_humanize_refusal(reason 剥 CHAIN_SWITCH_HINT 后缀)}"`（空则兜底文案「（无可执行子问题。）」）；`_direct_answer(updates, "这几件事我在数据里都没能给出现成的答案，原因和下一步：\n"+lines)`；`updates["next_intent"]=INTENT_ANSWER` → return → 去向 answer（零执行零冒充，终局不携改链 hint）。
      - 11e. 其余（executable 非空、asks 空）→ `next_intent=INTENT_BATCH` → return → 去向 batch。
- 副作用：emit `step`（L2929，`step=STEP_DECISION`，恒发——除 1/2 提前返回）；emit `notice`（`chain_switch_reentry` L3092 条件、`clarify_capped` L3117 条件）；emit `ask`（L3125 条件，`{frame, run_id}`）；持久化写：无（只产 state updates，落库经 executor/checkpointer）。
- 返回：见分支表——1＝`_converge` 形；2＝仅 `{"next_intent"}`；3-11 主路径恒有 `precondition_verdicts/tool_matches/question_group/metric_candidates/steps`；条件键 `subtask_results`（9d）、`notices`（10d／11b-i）、`chain_switch_marks`（10d）、`consecutive_asks`／`pending_ask`（11b-ii）、`draft`／`draft_kind`／`next_intent`（各出口）。
- 规则条目：
  - R-F-02 入口只守时长闸（`rounds_gate=False`——轮数闸不在此开）；触界＝收敛交付已取得部分＋notice 明示未完成项，本节点判定不再发生。
  - R-F-03 无问题组＝回澄清（`next_intent=decision`），零事件零留痕（恢复段边界兜底）。
  - R-F-04 判定输入装配：`judge` 纯函数（台账事实＋放行名单＝`approved_ids`＋水位＋窗口锚定态＋井闭世界）；chain 三级回落 `match→st→"data"`；同子问题未定案（match 缺）也判（plan=None）。
  - R-F-05 换链一次为界：首次 `chain_switch_trigger`＝指纹入 `marks[sid]`＋入 `chain_pending` 回炉①（failed 条目＋通知）；同 id 或同参指纹再触发＝判词改 blocked_refuse 终局（不环）。
  - R-F-06 换链终局尾分型：UNBOUND＝「未绑定口径如实拒答，不代答」；DOMAIN＝「题眼井不在数据链井闭世界——域错如实拒答，不代答」。
  - R-F-07 F7 名归一落载：命中归一的子问题 `plan.metric_slot` 双面改写为台账 slot（tool_matches＋question_group 同改，防双面漂移）。
  - R-F-08 词面门落载：`fuzzy_window_rewrite` 子问题窗双槽双面改写 None（「最近」类不解析不默认——引擎缺参反问兜底）。
  - R-F-09 候选集随改写刷新：data 链 `metric_slot` 去重列；空则保原值（FX-13——防归一 slot 被误判为「指标替换」）。
  - R-F-10 判定留痕：每次判定落一条 decision step（title 逐支 `{sid=state}`；payload 携 `verdicts` 全集，marks 非空时 `chain_switch_marks` 随行）。
  - R-F-11 拒答簿记：blocked_refuse 子问题入 `subtask_results`（`status="refused"` 终局；chain 恒 "data"、fingerprint 恒空）。
  - R-F-12 回炉簿记：`chain_pending` 子问题入 `subtask_results`（`status="failed"`＋`chain_switch=True`＋指纹）——供澄清相位失败子集回炉消费（回炉面与执行面指纹分簿）。
  - R-F-13 结果面同 id 单行：新判定（refused／回炉 failed）先剔旧行再追加，不残留双行。
  - R-F-14 换链通知：`chain_switch_reentry` notice 按 unbound／domain 分型分段措辞（语义同轨零改动）；marks 随 state 落载（批量段据此跳过触发支执行 L3269-L3274）。
  - R-F-15 部分结果先行：有可执行子问题即进批量；blocked_ask 留待批量段收尾挂起（L3516-L3540）。
  - R-F-16 澄清截断：连续 ask 将达上限（≥6）＝不再挂起——`clarify_capped` notice＋带材料如实直答收口（不占预算三闸）。
  - R-F-17 挂起：仅第一个 blocked_ask 的帧入 `pending_ask`＋emit ask；`next_intent=decision`（interrupt 在 clarify 入口）；挂起不占轮；帧原样（judge 产 payload，无 reseed）。
  - R-F-18 纯换链组（无可执行、无 ask）：回炉①澄清相位——零挂起零 ask 预算（failed 回喂是发射回喂非 ASK）。
  - R-F-19 全拒终局：全部 blocked_refuse＝零执行零冒充——直答逐条列拒因（剥改链 hint 后人话化）；直答是终局不再给 hint。
  - R-F-20 默认出口：可执行子问题非空且无 ask＝批量执行。
- 耦合：`appv2.tools`：`judge`、`SubtaskInput`、`ledger_facts`、`CHAIN_SWITCH_HINT`、`CHAIN_SWITCH_KIND_UNBOUND`（=""）、`CHAIN_SWITCH_KIND_DOMAIN`（="domain"）、`STATE_PASS/STATE_NOTE/STATE_BLOCKED_ASK/STATE_BLOCKED_REFUSE`、`ASK_CLARIFY`（L135-L152 导入；常量真源 appv2/tools/precondition.py L41-L44、L73-L80，`ASK_CLARIFY` 真源 appv2/tools/schema.py L54="clarify"）；`appv2.runtime.budget.CLARIFY_ASK_CAP_CONTRACT`（=6）；`appv2.runtime.state.INTENT_DECISION/INTENT_BATCH/INTENT_ANSWER`、`STEP_DECISION`；本文件：`_gate_or_none`(L1092)、`_group_subtasks`(L2287)、`_payload_fingerprint`(L537)、`_next_seq`(L1068)、`_step_record`(L1051)、`_direct_answer`(L1203)、`_clarify_capped_answer`(L1210)、`_refusal_*`/`_watermark_date_of`/`_data_wells_set`（本段内）；`dataclasses.replace`(L59 导入)；`deps.bus.emit`。
- 疑点（只列不判）：
  - D-F-01 换链指纹只含 plan（`retrieval_need` 恒 None 入指纹，L2887）——同参判定不覆盖检索载荷（触发面若仅可能 data 链，实际影响面待核）。
  - D-F-02 `fingerprint in marks.values()` 为跨 id 同参比对（L2906）：两支 plan 载荷相同的子问题，任一已簿记即让另一支直接终局拒答；同轮内亦可能（先到者入 chain_pending，后到者终局）。
  - D-F-03 `marks` 只增不减且随 state 跨轮保留（L2897 读全量、L3095 全量写回；含已 pass／已不存在的子问题旧指纹）——旧指纹对后续轮同参判定面是否应继续生效未核。
  - D-F-04 多 blocked_ask 只挂 `asks[0]` 帧（L3122）；其余帧既不挂起也不落通知（恢复后重判）。
  - D-F-05 `notices` 写入形两路不一致：ask 路沿用 10d 已置值（不重写），cap 路重写为 `[*state.notices, *extra_notices, notice]`（L3118）——当前控制流下 ask 路恰无二次写入（无重复），但两形并存。
  - D-F-06 本段自造 `refusals`/`chain_entries` 条目不走 `_subtask_result`（字段形两处重复；chain 硬编码 "data"——跨链场景面存疑）。
  - D-F-07 `refusals` 条目 `fingerprint` 恒空串（L3018）——终局拒答无指纹留痕（对比 chain_entries 携 marks 指纹）。
  - D-F-08 11d 兜底句「（无可执行子问题。）」可达性存疑：进入该支时 asks 与 chain_pending 均已排除，组非空下 verdict 四态中 refusals 理论恒非空。
  - D-F-09 `window_resolved` 为 run 级布尔（L2860-L2863）：run 内任一次 clarify resume 即让全部子问题（含其后新组）词面门静默——非按子问题／按窗粒度。
  - D-F-10 换链终局拒答原文（含「指纹 …… 在簿」机器字样）经 11d `_humanize_refusal` 未知形兜底直接携出用户面（`系统没法直接给这条的数：{原文}`）——用户面文案待核。
  - D-F-11 11b-i cap 路不落 `consecutive_asks`（L3108-L3120 无写回）——截断时计数保持原值，截断后计数语义待核。
  - D-F-12 ask 帧原样用 judge 产 payload（无 reseed／re-project）——对比批量段对引擎源外表审批帧做 `reseed_approval_id`（L3456-L3463）；两类帧的 approval_id 来源形不同（本段帧为 judge 产 `precond-{sid}`，precondition.py L390）。
  - D-F-13 `_watermark_date_of` duck 回落 face 本体（L3186）；`judge` 内 `end > watermark` 比较无类型/异常兜底（precondition.py L558）——非 date 实体行为未核（读缝异常只兜住调用本身）。
  - D-F-14 `_data_wells_set` 全宽 `except Exception`（L3197）：读缝实现异常与「未接线」同为静默空集——域闸零留痕、两态不可区分。
  - D-F-15 `_humanize_refusal` 已知形仅一型；其余拒因型（禁用词／非法口径／场景词矛盾／换链终局／外表审批）全落通用兜底——逐型人话未覆盖。
  - D-F-16 `_refusal_with_hint`/`_humanize_refusal` 的剥/贴以 `CHAIN_SWITCH_HINT` 逐字为键（`removesuffix`/`endswith` 精确匹配，L3156-L3157）——hint 文案一处改即双双失配。
  - D-F-17 `_subtask_result` status 三值仅注释约定无运行时校验；precondition 段与 batch 段两处构造面并存（值域靠调用方自律）。

### `_refusal_with_hint`（L3153-L3158）｜汇总清单拒因转述形：人话核心＋保留改链 hint，包「（）」
- 消费：形参 `reason: str`。
- 调用：caller=answer 节点子问题清单渲染 L3862（仅 `r.reason` 非空时调用；对 subtask_results 全行统一转述）；纯函数无 LLM；失败处理：无（命中判 `removesuffix`/`endswith`，无需异常分支）。
- 分支表（穷尽）：
  1. reason 以 `CHAIN_SWITCH_HINT` 结尾 → `core=剥后缀`、`hint=CHAIN_SWITCH_HINT` → 返回 `f"（{_humanize_refusal(core)}{hint}）"`。
  2. 否则 → `hint=""` → 返回 `f"（{_humanize_refusal(reason)}）"`。
- 副作用：无。
- 返回：str。
- 规则条目：
  - R-F-21 汇总清单转述保留 hint：hint 面向汇总模型（供改链重决策路径），用户面由 `_ANSWER_INSTRUCTION` 检查话术规则管转述（docstring L3154-L3155）；机器拒因原文零改动。
- 耦合：`CHAIN_SWITCH_HINT`（appv2.tools 导出，真源 precondition.py L73）；`_humanize_refusal`（L3161）。
- 疑点：
  - D-F-16（同前，剥/贴逐字键失配面）。

### `_humanize_refusal`（L3161-L3171）｜机读拒因→用户面人话的转述单点（已答对照表翻译，未知形兜底）
- 消费：形参 `reason: str`。
- 调用：caller=`precondition_node` 全拒直答 L3137／`_refusal_with_hint` L3158；纯函数无 LLM；失败处理：无（正则不中即兜底分支）。
- 分支表（穷尽）：
  1. `re.match(r"指标 (.+?) 不在台账全量", reason)` 命中 → 返回「「{捕获名}」不在可查询的指标名录里——系统按名录里的指标名查数。想知道都能查什么，可以直接问我。」
  2. 否则 → 返回 `f"系统没法直接给这条的数：{reason}"`（原文照携）。
- 副作用：无。
- 返回：str。
- 规则条目：
  - R-F-22 转述翻译单点（V2-80d）：已知形「指标 … 不在台账全量」→ 人话模板；未知形兜底原文；机器拒因原文零改动（回炉重决策与审计仍消费原文——precondition.py 生成面不动）。
- 耦合：`re`（L57 导入）。
- 疑点：
  - D-F-15（同前，逐型人话未覆盖面）。

### `_watermark_date_of`（L3174-L3186）｜水位读缝→水位日期投影（新鲜度窗判定输入，缺态归一 None）
- 消费：`deps.watermark`（`LoopDeps` 读缝，Callable｜None；L365/L378）。
- 调用：caller=`precondition_node` L2856；无 LLM；读缝调用 `except Exception: return None`（全宽兜底）。
- 分支表（穷尽）：
  1. `deps.watermark is None` → None（缺接线——judge 收 None＝新鲜度窗注记跳过，引擎闸仍权威）。
  2. `deps.watermark()` 抛异常 → None。
  3. `face is None` → None。
  4. 否则 → `getattr(face, "data_date", face)`（duck 属性优先，缺则 face 本体）。
- 副作用：无。
- 返回：Any（期望 date｜None）。
- 规则条目：
  - R-F-23 水位投影三态归一 None；duck 读 `data_date`——类型真源在 query 引擎侧，防环不直接 import（运行策略面归 runtime）。
- 耦合：`deps.watermark`（LoopDeps 缝）；调用者 `judge` 消费该值（precondition.py L553-L562）。
- 疑点：
  - D-F-13（同前，duck 回落与 judge 比较面无类型兜底面）。

### `_data_wells_set`（L3189-L3201）｜井闭世界读缝→井号 str 集（软失败域闸判定输入，缺态归一空集）
- 消费：`deps.data_wells`（`LoopDeps` 读缝，L366/L379）。
- 调用：caller=`precondition_node` L2857；无 LLM；读缝调用 `except Exception` 全宽兜底。
- 分支表（穷尽）：
  1. `deps.data_wells is None` → `frozenset()`。
  2. `deps.data_wells()` 抛异常 → `frozenset()`。
  3. `not world`（None/空世界）→ `frozenset()`。
  4. 否则 → `frozenset(str(well) for well in world)`（井号 str 归一——judge 侧 `_WELL_RE` 文本比对面）。
- 副作用：无。
- 返回：`frozenset[str]`。
- 规则条目：
  - R-F-24 井闭世界四态归一空集（缺缝／异常／空世界＝域闸静默零漂移，不发明域语义）；消费面 `data_wells or None` 传给 judge（空集＝None 同态）。
- 耦合：`deps.data_wells`（LoopDeps 缝）；`judge` 的 `data_wells` 形参（precondition.py L282-L283、L513-L525）。
- 疑点：
  - D-F-14（同前，异常与未接线同为静默空集面）。

### `_subtask_result`（L3204-L3222）｜子问题结果条目七字段构造单点（batch 段消费）
- 消费：形参 `subtask_id/question/chain`（位置）＋keyword-only `status/reason/obs_count/fingerprint`（带缺省）。
- 调用：caller=batch 节点四处——L3381（缺位回捞用尽→ok）／L3400（缺位回捞开闸→failed）／L3426（常规成功→ok）／L3475（执行错误→refused/failed 按 `CATEGORY_REFUSED` 分型）；无 LLM。
- 分支表：无（单一路径 dict 构造）。
- 副作用：无。
- 返回：`{"id", "status", "reason", "question", "obs_count", "fingerprint", "chain"}`（status 注释闭语 `ok | failed | refused`——failed＝可回炉、refused＝终局拒答，L3216）。
- 规则条目：
  - R-F-25 子问题结果行七字段形单点：ok（完成）｜failed（可回炉）｜refused（终局）三值语义；回炉不重跑（R4）与全拒直答都消费本形。
- 耦合：无外部符号（纯 dict 构造）。
- 疑点：
  - D-F-17（同前，status 无枚举校验；precondition 段自造条目与之形近不全同——见 D-F-06）。

---

## 覆盖自检
- def 清单差集：无（L2844-L3225 内全部 6 个 def 全列全析：`_make_precondition`／`precondition_node`（嵌套）／`_refusal_with_hint`／`_humanize_refusal`／`_watermark_date_of`／`_data_wells_set`／`_subtask_result`；L3225 的 `_make_batch` def 行属下一段边界，不计入覆盖）。无 class。
- 本段 emit 事件名全集：`step`（STEP_DECISION）；`notice`（`chain_switch_reentry`、`clarify_capped`）；`ask`。
- 本段读写的 state 字段全集（e4b75f1 的 state.py 字段名）：
  - 读：`budget_hit`（`_gate_or_none` 幂等判）、`budget`/`deadline_monotonic`（`budget_gate_hit`）、`question_group`、`ledger_dump`、`resume_choices`、`tool_matches`、`approved_ids`、`chain_switch_marks`、`subtask_results`、`notices`、`consecutive_asks`、`steps`、`metric_candidates`、`run_id`；收敛/截断委托面另读 `observations`/`last_result`（material_rows）、`understanding`/`rounds`/`verdict`/`draft`/`answer`（unfinished_items）。
  - 写（updates 键）：`precondition_verdicts`、`tool_matches`、`question_group`、`metric_candidates`、`steps`、`next_intent`（各出口）；条件键 `subtask_results`、`notices`、`chain_switch_marks`、`consecutive_asks`、`pending_ask`、`draft`、`draft_kind`；收敛路径另写 `budget_hit`/`answer`/`status`。
- 本段引用的外部符号全集（本文件内定义的除外）：`judge`、`SubtaskInput`、`ledger_facts`、`CHAIN_SWITCH_HINT`、`CHAIN_SWITCH_KIND_UNBOUND`、`CHAIN_SWITCH_KIND_DOMAIN`、`STATE_PASS`、`STATE_NOTE`、`STATE_BLOCKED_ASK`、`STATE_BLOCKED_REFUSE`、`ASK_CLARIFY`（均经 `appv2.tools` 导出，L135-L171 导入）；`CLARIFY_ASK_CAP_CONTRACT`（appv2/runtime/budget.py L38）；`INTENT_DECISION`、`INTENT_BATCH`、`INTENT_ANSWER`、`STEP_DECISION`（appv2/runtime/state.py）；`dataclasses.replace`；`re`；`deps.bus.emit`／`deps.watermark`／`deps.data_wells`（LoopDeps 缝）；类型注记 `Callable`/`Coroutine`/`Any`（工厂签名，L58-L60 导入）。
