# H·现状调研报告

- 锚定：commit e4b75f1（行号以此为准；本段在 e4b75f1→HEAD（085b294）间 graph.py 零 diff，行号两处一致）
- 覆盖：appv2/runtime/graph.py L3553-L4109
- def/class 清单：逐一全列（含行号区间），不得省略
  - `_make_observe`（def，L3556-L3611）——节点五工厂：返回 `observe_node`
  - `observe_node`（async def，L3559-L3609；嵌套于 `_make_observe`）——观察回流节点本体
  - `_make_verify`（def，L3617-L3731）——节点六工厂：返回 `verify_node`
  - `verify_node`（async def，L3620-L3729；嵌套于 `_make_verify`）——核验节点本体（零 LLM）
  - `_finalize`（def，L3737-L3800）——答案收口单体（非图节点：answer_node 与本段各直答路径的收口调用面）
  - `_make_answer`（def，L3803-L3987）——节点七工厂：返回 `answer_node`
  - `answer_node`（async def，L3806-L3985；嵌套于 `_make_answer`）——起草＋收口节点本体
  - `_route`（def，L4035-L4036）——条件边判据（next_intent 取值）
  - `_node_of`（def，L4039-L4049）——add_node 形参恒等转换缝
  - `build_graph`（def，L4052-L4109）——图装配与编译出口
  - 无 class；L4109 为文件末行（build_graph 为文件末函数）。
- 段内模块级常量/注释（非 def，区段标注）：
  - `_ROUTES`（L3992-L4032）——七节点路由表（dict[str, dict[Hashable, str]]，逐键穷尽见条目）；
  - 分节注释：L3553「节点五：observe（观察回流——回喂决策）」；L3614「节点六：verify（零 LLM——INV-1/4 机器底线；拍板③保留件）」；L3734「节点七：answer（起草[caller answer]→verify→收口——两段一节点）」；L3990「图装配（七节点＋条件边——StateGraph 真承载 loop）」；
  - 段内行内注释（关键处）：L3623-L3624 归属审锚面（无实体题＝空锚）；L3632-L3633 零实质材料；L3637-L3640 V2-72 b 案/V2-77 C 项；L3711-L3712 V2-80h 就地替换唯一例外；L3742 V2-23 收口注记；L3746-L3749 V2-48 citation 落账；L3782-L3785 V2-80h 收口链同步单点；L3798 V2-80h 追加式；L3816-L3818 V2-77 追问可答面；L3837-L3839 V2-51 plan 支配标记；L3874-L3875 V2-80h 作答指令追加；L3881-L3883 V2-61 截断必披露；L3900-L3902 V2-48 JSON 通道隔离；L3906 零余量重试；L3917-L3918 V2-77 C 项；L3946 V2-62 观察字段；L3954-L3955 V2-79a；L3962 V2-80h 核验前原稿；L3982 零材料先过 verify；L4014 retryable 自环（P-024b C2）；L4055-L4058 four_phase 语义（V2-34/ADR-0005）；L4078 CLARIFY 拒因自环／ask 恢复入口；L4081-L4085 审批恢复边（B1/P-033）；L4090 TOOLMATCH 回喂自环；L4097 blocked_ask 挂起恢复；L4102 引擎 ask 挂起／失败子集回炉①。
- 本段定位（行号锚点，不抄正文）：observe/verify/answer 三节点经 build_graph L4065-L4067 装配；`_ROUTES` 为 legacy 与 four_phase 两态条件边共用真源（four_phase=True 时 build_graph 把含 INTENT_DECISION 的表值重定向 NODE_CLARIFY，L4074-L4076，并追加四张相位表 L4077-L4105）。verify 在「answer 起草 → verify 核验就地改写 → answer 收口」链上（answer_node L3979 设 INTENT_VERIFY；_ROUTES[NODE_ANSWER] L4028 verify→verify；verify 尾 L3728 设 INTENT_ANSWER 回 answer）。收敛更新面（`_converge`／预算闸）在段外 L1083-L1118。

---

### `_make_observe`（L3556-L3611）｜节点五工厂：返回观察回流节点闭包
- 消费：形参 `deps: LoopDeps`（构造期捕获，不取字段）。
- 调用：caller=`build_graph` L4065（`builder.add_node(NODE_OBSERVE, _node_of(_make_observe(deps)))`）；工厂本身无 LLM/工具调用。
- 分支表：无（仅闭包定义与 `return observe_node` L3611）。
- 副作用：无。
- 返回：`observe_node`（async callable，`Callable[[RunState], Coroutine[Any, Any, dict[str, Any]]]`）。
- 规则条目：
  - R-H-01 observe 节点仅捕获 `deps.bus` 事件出口：节点体零 LLM、零工具、零持久化——纯事件发射＋路由。
- 耦合：`LoopDeps`（本文件 L344-L387）、`_node_of`（L4039）。
- 疑点：无。

### `observe_node`（L3559-L3609）｜观察回流：last_result 观察编号入栈、notice 型机读分型、路由回决策或继续执行
- 消费：`state.last_result`／`state.observations`／`state.pending_discovers`／`state.pending_plan`／`state.pending_retrieval`／`state.steps`（经 `_next_seq`）／`state.budget_hit`／`state.deadline_monotonic`（经 `_gate_or_none`→`budget_gate_hit(include_rounds=False)`，L1092-L1108）；`deps.bus`。
- 装配：无（不触 messages/对话链）。
- 调用：无 LLM/工具调用（trust_of 为 locator.kind 确定性映射；事件发射确定性）。
- 分支表（穷尽）：
  1. `_gate_or_none(state, deps)` 返回非 None（`budget_hit` 非空＝不重复收敛；或时长闸 total_seconds 触界）→ 直接返回收敛 updates（段外 `_converge` L1083-L1090：budget_hit/notices/answer/draft_kind="direct"/status="completed"/next_intent=answer）→ 不记 observe step、不发 observation/notice 事件。
  2. 回流观察列为空（`last_result` 缺省 `{}` 或 observations 键空列）→ indexed=[] → 仍记一条 step（标题「观察回流 0 支」、payload count=0），路由按支 4 分岔。
  3. 逐条回流观察：副本 entry 赋值 `index=state.observations 当前长度+偏移`（从 1 起）与 `trust=trust_of(entry)`（locator.kind 映射）。
  4. 逐条事件：`locator.kind == "notice"` → 先 emit notice（type=locator.notice_type 缺省 "notice"、gates=[]、content=str(obs.content)），再 emit observation；其余 kind → 只 emit observation。
  5. 路由分岔：`state.pending_discovers` 非空 → INTENT_DISCOVER；否则 `pending_plan is not None` 或 `pending_retrieval is not None` → INTENT_EXECUTE；否则 → INTENT_DECISION。
  6. 返回三元组 updates（observations 追加、steps 追加、next_intent）。
- 副作用：emit step（observe，标题形「观察回流 {n} 支」）；emit notice（仅 notice 型观察，type 取 locator.notice_type 或 "notice"）；emit observation（逐支 {index,source,content,trust}）；持久化写：无（step 记录随返回值入 state.steps）。
- 返回：`{"observations": 旧列+新列, "steps": 旧列+新记录, "next_intent": intent}`。
- 规则条目：
  - R-H-02 入口闸语义（时长闸守、轮数闸不守）：预算收敛已发生不二次收敛；时长闸触界→收敛直返（收敛答案由 answer 节点收口），本节点不做事件/step。
  - R-H-03 观察进场编号：index＝全局 [n] 序（现有 observations 长度＋偏移），trust＝locator.kind 确定性映射（零模型）。
  - R-H-04 notice 型观察机读分型：发 notice 事件（拦停非数据），但观察本体照常发 observation 事件并追加进 observations。
  - R-H-05 回流路由：待投载荷在位优先——pending_discovers→discover；pending_plan/pending_retrieval→execute；否则回 decision（模型自主再轮或定稿）。
  - R-H-06 每轮回流恒记一条 observe step（payload `{"count": n}`、manifest=None 不入账）。
- 耦合：`trust_of`（appv2.runtime.context）；`_gate_or_none`／`_step_record`／`_next_seq`／`_observations_of`（本文件段外）；`INTENT_DISCOVER`／`INTENT_EXECUTE`／`INTENT_DECISION`、`STEP_OBSERVE`（appv2.runtime.state）；`deps.bus.emit`。
- 疑点（只列不判，不静默）：
  - D-H-01 notice 型观察只经 `deps.bus.emit`（L3577-L3586）发事件，本段未见写入 `state.notices`（本段内 state.notices 仅经段外 `_converge` 收敛路径追加）。
  - D-H-02 observe step 的 payload 只有 count：回流观察的 source/trust 分布入事件流但不入 step 档案。

### `_make_verify`（L3617-L3731）｜节点六工厂：返回核验节点闭包（零 LLM）
- 消费：形参 `deps: LoopDeps`（构造期捕获，不取字段）。
- 调用：caller=`build_graph` L4066；工厂本身无 LLM/工具调用。
- 分支表：无（仅闭包定义与 `return verify_node` L3731）。
- 副作用：无。
- 返回：`verify_node`（async callable）。
- 规则条目：
  - R-H-07 verify 节点零 LLM（分节注释 L3614）：核验＝纯函数（verify_draft/_attribution_conflicts）＋闭世界锚解析（entity_anchor_tokens），无模型调用。
- 耦合：`LoopDeps`、`_node_of`。
- 疑点：无。

### `verify_node`（L3620-L3729）｜核验单点：零实质材料三分支装配、verify_draft 断言级核验、归属审、verdict 装配、链尾就地替换
- 消费：`state.question`／`state.observations`／`state.draft`／`state.followup_of`／`state.messages`／`state.steps`（经 `_next_seq`）／`state.process_notes`（经 `_notes_with`）／`state.budget_hit`／`state.deadline_monotonic`（经 `_gate_or_none`）；`deps.bus`。
- 装配：messages 副本链尾若为 assistant → 其 content 就地替换为核验后文本（V2-80h append-only 唯一例外；无 assistant 尾则副本原样返回）。
- 调用：无 LLM/工具调用。verify_draft（纯函数 L796-L895，含 strip_emission_fences 入口剥除/断言行改写/分源列明/归属审块）、entity_anchor_tokens（闭世界确定性零模型）、_attribution_conflicts（纯函数 L923-L946）。
- 分支表（穷尽）：
  1. `_gate_or_none(state, deps)` 非 None → 返回收敛 updates（next_intent=answer；不动链、不记 step）。
  2. 题眼锚 `anchors = entity_anchor_tokens(state.question)`（L3625）：空问句→()；井号优先、闭世界实体名归一、报告号数字核；无实体题→空锚（归属审静默）。
  3. 实质材料列 `material`＝observations 中 `locator.kind != "notice"` 的项（L3626-L3630）。
  4. `not material`（零实质材料）→ 三分支（L3634-L3659）：
     a. `state.draft` 真且 `state.observations` 为空列 → `text = state.draft` 原样（拒绝话术非断言，不走改写）；`rewritten, cited, split = 0, list[int](), False`。
     b. 否则 `state.followup_of` 真且 `not state.draft` → `text`＝固定人话「这个问题在本对话的材料和前轮问答里都没有找到依据，我不能编造答案。可以换个问法，或让我先去查相关数据。」；emit notice `{"type": "decision_note", "gates": [], "content": "追问零实质材料——如实说明无依据（不编造）"}`；rewritten/cited/split 同归零。
     c. 其余（含 observations 仅 notice 型、或 draft 空且非 followup、或全零观察）→ `notice_texts`＝全部观察 content；`body`＝非空项以「；」连接；body 非空→`text = f"{body}（闸依据如实转答——零数值，不冒充出数。）"`；body 空→`text = NO_MATERIAL_SHELL`；rewritten/cited/split 同归零。
  5. `material` 非空 → `text, rewritten, cited, split = verify_draft(state.draft, state.observations, anchors=anchors)`（L3662-L3664；传全量 observations 含 notice 型）。
  6. 归属审（支 4/5 后恒执行）：`_aligned, crossed = _attribution_conflicts(anchors, set(cited), state.observations)`（L3665-L3667；`_aligned` 弃用）；`attribution = {"anchors": list(anchors), "cross": sorted(int(obs["index"]) for obs in crossed)}`（跨源支序号升序）。
  7. verdict 装配（恒执行）`{"supported": len(cited), "rewritten": rewritten, "split": split, "cited": cited, "attribution": attribution}`（L3672-L3678）。
  8. 事件（恒执行）：emit step（verify，标题「核验：支撑 {len(cited)}｜改写 {rewritten}｜分源 是/否」）；emit verdict（verdict 字典原样 dict(verdict)）。
  9. `rewritten` 非零 → emit notice `unsupported_claim`（content 含改写行数与「INV-1」）。
  10. `split` 真 → emit notice `contradiction_split`（content「多来源不一致——答案分源列明（INV-4——禁止无出处调和）」）。
  11. `crossed` 非空 → emit notice `attribution_split`（content 含跨源支 `[n]` 列、题眼锚列与「跨源引用按出处如实区分」）。
  12. 链尾同步：`replaced = [*state.messages]`；尾条 `role == "assistant"` → 替换为 `{**尾条, "content": text}`；否则 replaced 原样。
  13. 返回 updates（恒设 next_intent=INTENT_ANSWER）。
- 副作用：emit step（verify，标题形「核验：支撑 x｜改写 y｜分源 是/否」）；emit verdict（核验计数字典）；emit notice（unsupported_claim／contradiction_split／attribution_split／decision_note，全为事件流，未落 state.notices）；持久化写：无。
- 返回：`{"messages", "draft": text, "verdict", "process_notes": 旧+verify 条目, "steps": 旧+verify 记录(payload={"zero_llm": True}), "next_intent": INTENT_ANSWER}`。
- 规则条目：
  - R-H-08 入口闸：同 observe 语义（时长闸守、轮数闸不守）；触界收敛直返 answer。
  - R-H-09 题眼锚闭世界解析（井号/实体名/报告号数字核；无实体题＝空锚——归属审静默不误伤）。
  - R-H-10 实体材料判据＝非 notice 观察；零实质材料不烧模型、不冒充出数。
  - R-H-11 分支①：draft 在场且零观察 → 原样过核验（拒答话术非断言）。
  - R-H-12 分支②：追问轮且 draft 空 → 人话「无依据」＋decision_note（V2-72 b 案延续、V2-77 C 项措辞）。
  - R-H-13 分支③：闸依据（notice 观察文本）如实转答；无文本→NO_MATERIAL_SHELL 人话壳（零数值不冒充出数）。
  - R-H-14 有材料 → verify_draft 断言级核验（改写无据断言/分源列明/归属审块，INV-1/INV-4）。
  - R-H-15 归属审二分：仅被引（cited）且 locator.kind ∈ {fragment, graph} 的观察入辖域；按题眼锚对齐/跨源二分；verdict.attribution 记锚列与跨源序号。
  - R-H-16 verdict 五键：supported＝支撑引标数、rewritten、split、cited、attribution。
  - R-H-17 三类机读 notice 随改写/分源/跨源如实披露（只事件，不追加 notices）。
  - R-H-18 就地替换：链尾 assistant 原稿→核验稿（append-only 唯一例外之一）；无 assistant 尾零动作。
  - R-H-19 过程档案 verify 条目（统计摘要，`_note` 截 200 字）＋step 零 LLM 标记；去向恒 answer。
- 耦合：`entity_anchor_tokens`（appv2.tools）；`verify_draft`／`_attribution_conflicts`／`_gate_or_none`／`_step_record`／`_next_seq`／`_note`／`_notes_with`（本文件段外）；`NO_MATERIAL_SHELL`（appv2.runtime.budget）；`STEP_VERIFY`、`INTENT_ANSWER`（appv2.runtime.state）；`deps.bus.emit`。
- 疑点（只列不判，不静默）：
  - D-H-03 零实质材料三分支条件与「零实质材料」判据不完全对应（L3626-L3630 vs L3634-L3659）：分支①以「observations 全空」判定；draft 非空且 observations 仅 notice 型时落分支③——草稿被弃、以 notice 文本拼装转答。
  - D-H-04 有材料分支把 state.observations 全量（含 notice 型）传入 verify_draft 与 _attribution_conflicts（L3662-L3667）；notice 过滤只用于零材料分支判定。
  - D-H-05 注释称「原稿入 step 档案可查」（L3711-L3712），但本段 verify 步 payload 仅 `{"zero_llm": True}`（L3726-L3727），原稿文本未见写入 steps/process_notes（process_notes 的 draft/verify 条目只记摘要统计）。
  - D-H-06 `_aligned` 返回值弃用（L3665）：对齐支信息不进 verify 返回面（归因结果只以 cross 序号落 verdict.attribution）。
  - D-H-07 分支②人话文本与 decision_note 文案和 answer 空稿追问兜底（L3916-L3927）逐字相同——同型文本/notice 两处硬编码。

### `_finalize`（L3737-L3800）｜答案收口：引用块装配、citation 帧落账、verdict 帧、链尾同步单点
- 消费：`state.verdict`／`state.observations`／`state.draft`／`state.answer`／`state.manifests`／`state.messages`／`state.steps`（经 `_next_seq`）／`state.run_id`。
- 装配：messages 副本链尾同步——尾条 assistant → 就地替换为 `{"role": "assistant", "content": answer}`；否则追加同一终稿轮（收口链同步单点，全路径经此一处）。
- 调用：无 LLM/工具调用（hashlib/json 确定性摘要，零二次创作）。
- 分支表（穷尽）：
  1. answer 取值链（L3741）：`state.draft` 非空→draft；draft 空且 `state.answer` 非空→answer；均空→固定兜底「（未取得可交付答案——如实回报，不编造。）」。
  2. 血缘收口注记（L3743-L3745）：`_lineage_closing_note(observations)` 非空且 answer 不含子串「收口注记」→ answer += "\n\n"+注记；否则不追加。
  3. 引用块（L3750-L3758）：`supported`＝verdict.cited 转 int 去重升序；非空 → 逐号取 by_index（index→obs），在界号生成行「[n] source · source_id（trust）」→ answer += "\n\n引用：\n"+行集；supported 为空→无引用块。
  4. citation 帧集（L3759-L3762）：`cited`＝supported ∪ 答案文本 `_CITE_RE` 命中且序号 in by_index 的号；升序。
  5. digest（L3763-L3765）：sha256(json.dumps(manifests, ensure_ascii=False, sort_keys=True).encode())。
  6. 事件序列（L3766-L3781）：emit step（answer/「答案收口」）→ 逐号 emit citation（index/source/source_id/trust；by_index 缺失号跳过）→ emit text（answer 全文）→ emit verdict（`{"status": "completed", "run_id", "manifest_digest": digest}`）。
  7. 链尾同步（L3786-L3791）：尾 assistant → messages[-1] 替换终稿；否则 append 终稿。
  8. 返回 updates（见返回）。
- 副作用：emit step（answer，标题「答案收口」，payload `{"phase": "finalize"}`）；emit citation（逐号）；emit text（全量答案）；emit verdict（completed 帧）；emit notice：无；持久化写：无。
- 返回：`{"answer", "messages", "status": "completed", "manifest_digest", "steps": 旧+收口记录, "next_intent": INTENT_END}`。
- 规则条目：
  - R-H-20 收口取值链：draft→answer→兜底文本（零二次创作）。
  - R-H-21 血缘⑤收口注记确定性随行（不靠模型自觉；答案已含「收口注记」则去重不加）。
  - R-H-22 引用块只列核验支撑集（R9 语义：无支撑引标不进引用集）；by_index 缺失号跳过。
  - R-H-23 citation 帧＝支撑集∪答案文本合法 [n]（观察在界）；悬空 [n] 只落帧不进引用块（V2-48 citation 落账）。
  - R-H-24 manifest_digest＝manifests 规范化 JSON 的 sha256。
  - R-H-25 事件序恒为 step→citation→text→verdict(completed)。
  - R-H-26 链尾同步单点：LLM 收口路径就地成形；直答/拒答/闸拦/收敛路径追加话术轮。
  - R-H-27 收口终态：status=completed、next_intent=end。
- 耦合：`_lineage_closing_note`／`_CITE_RE`／`_step_record`／`_next_seq`（本文件段外）；`STEP_ANSWER`、`INTENT_END`（appv2.runtime.state）；hashlib／json（stdlib）；`deps.bus.emit`。
- 疑点（只列不判，不静默）：
  - D-H-08 `_finalize` 无入口预算闸（L3737 为独立单体；闸由 answer_node 入口 L3807 承担，本段其他潜在直调路径无闸）。
  - D-H-09 verdict 事件同名两种帧形：本函数 `{status, run_id, manifest_digest}`（L3778-L3781）与 verify 的核验计数字典（L3682）。
  - D-H-10 verdict.cited 中不在 by_index 的序号：引用块行与 citation 帧均静默跳过（不生成、不告警）。
  - D-H-11 血缘注记追加判据是子串「收口注记」不在 answer 中（L3744）——答案正文恰含该四字则不追加注记。

### `_make_answer`（L3803-L3987）｜节点七工厂：返回起草＋收口节点闭包
- 消费：形参 `deps: LoopDeps`（构造期捕获；节点体消费 deps.model/deps.bus/deps.builder.max_observations）。
- 调用：caller=`build_graph` L4067；工厂本身无 LLM/工具调用。
- 分支表：无（仅闭包定义与 `return answer_node` L3987）。
- 副作用：无。
- 返回：`answer_node`（async callable）。
- 规则条目：
  - R-H-28 answer 节点两段一节点：起草段（caller=answer 唯一模型调用点）→ verify 路由；收口段（_finalize 确定性装配）。
- 耦合：`LoopDeps`、`_node_of`。
- 疑点：无。

### `answer_node`（L3806-L3985）｜起草（门收敛拦截/零材料与直答旁路/汇总指令/材料渲染/空稿重试）与收口（_finalize 委托）
- 消费：`state.answer`／`state.verdict`／`state.draft_kind`／`state.draft`／`state.observations`／`state.followup_of`／`state.question`／`state.question_group`／`state.tool_matches`／`state.subtask_results`／`state.messages`／`state.steps`／`state.process_notes`／`state.budget_hit`／`state.deadline_monotonic`（经 `_gate_or_none`）；`deps.bus`／`deps.model(MODEL_ANSWER)`／`deps.builder.max_observations`。
- 装配：messages 追加一条 user（作答指令＋全量材料段）＋一条 assistant（起草原稿）——每次作答一次；核验/收口不重发（核验就地替换、终稿由收口单点追加）。
- 调用：caller=answer（`deps.model(MODEL_ANSWER)`，键 "answer"）；格式＝整链（state.messages＋本轮 user 指令）经 `_complete`（GatewayChatModel.ainvoke）；失败/空稿：空草稿同相位重试一次（同一 new_messages 再调一次，不追加新消息）；发射围栏泄漏确定性剥离；重试仍空走三分支兜底。
- 分支表（穷尽）：
  1. `_gate_or_none` 非 None → `converged["next_intent"] = INTENT_END`（覆写收敛值的 answer）→ 返回（防 answer→answer 自环，L3807-L3809）。
  2. 起草段进入条件（五者同时，L3810-L3825）：`not state.answer` ∧ `state.verdict is None` ∧ `state.draft_kind != "direct"` ∧ `not state.draft` ∧（任一非 notice 观察 或 `state.followup_of` 真）。
     - 指令初装：`answer_turn_preamble(state.question) + "\n" + _ANSWER_INSTRUCTION`（L3828-L3832）。
     - `state.followup_of` 真 → 追加 "\n" + `_FOLLOWUP_HISTORY_ANSWER_CLAUSE`（L3833-L3834）。
     - `state.question_group` 真 → 指令整体重建 `assemble_answer_instruction(question, SUMMARY_CONTRACT, subtask_list, _ANSWER_INSTRUCTION)`（L3868-L3873）；subtask_list 由 `state.subtask_results` 逐条（非 dict 跳过）构行「- [id] question——标记原因（支配句）」；标记映射 ok→完成/refused→已拒答/failed→失败，其他状态字符串原样；reason 非空经 `_refusal_with_hint`；`ranking=true` 的对应匹配计划（state.tool_matches 的 id→plan）追加「（排名型——结论必须从本子问题排名观察支（合计行口径）取值……）」支配句；无行→"（无）"（L3836-L3873）。
     - 材料段：`render_materials(state.observations, max_observations=deps.builder.max_observations)` → instruction_full＝指令＋材料段；new_messages＝`[*state.messages, {"role": "user", "content": instruction_full}]`（L3876-L3880）。
     - `materials_meta["material_truncated"]` 真 → emit notice `material_truncated`（渲染数/总数，V2-61 截断必披露；权威行集恒全量，截断只可能落检索族）（L3884-L3898）。
     - `first_content = await _complete(deps.model(MODEL_ANSWER), new_messages)`（L3899）。
     - `draft, leaked = strip_emission_fences(first_content.strip())`（L3903）。
     - `not draft.strip()` → `retry_content = await _complete(同 new_messages)`；`draft, retry_leaked = strip_emission_fences(retry_content.strip())`；`leaked = leaked or retry_leaked`（L3905-L3909）。
     - 仍 `not draft.strip()` → 三分支兜底（L3910-L3929）：leaked 真→「（模型草稿为 JSON 通道残留——剥离重试仍未取得有效草稿，如实收口。）」；elif `state.followup_of`→人话「这个问题在本对话的材料和前轮问答里都没有找到依据，我不能编造答案。可以换个问法，或让我先去查相关数据。」＋emit notice decision_note；else→「（模型未产出草稿——如实收口。）」。
     - `leaked` 真 → emit notice `emission_strip`（content 含是否重试注记与「V2-48 JSON 通道隔离」（L3930-L3943）。
     - 起草观察值：step_payload＝`{"phase": "draft", "echo_flag": echo_signature_hit(draft), "paste_ratio": paste_ratio(draft, list(state.observations or []))}`；draft_digest＝「echo=… paste=…（含同相位重试）」；emit step（answer/「起草答案」）（L3944-L3961）。
     - answer_messages＝`[*new_messages, {"role": "assistant", "content": draft}]`（核验前原稿入链；核验就地替换）（L3963-L3966）。
     - 返回 updates（见返回）。
  3. 未起草兜底（L3981-L3983）：`state.verdict is None` ∧ `state.draft_kind != "direct"` ∧ `not state.answer` → 仅返回 `{"next_intent": INTENT_VERIFY}`（零材料/在稿未核验先过 verify）。
  4. 其余（verdict 在场／draft_kind=="direct"／answer 已存在）→ `_finalize(state, deps)` 收口出流（L3985）。
- 副作用：emit notice material_truncated／decision_note／emission_strip；emit step（answer，起草态标题「起草答案」，payload phase=draft/echo_flag/paste_ratio）；收口段副作用见 `_finalize`（step/citation/text/verdict）；持久化写：无。
- 返回：起草段 `{"messages": answer_messages, "process_notes": 旧+draft 条目, "draft", "steps": 旧+起草记录, "next_intent": INTENT_VERIFY}`；分支 3 `{"next_intent": INTENT_VERIFY}`；分支 1＝收敛 updates（next_intent 覆写 end）；分支 4＝_finalize 返回（answer/messages/status/manifest_digest/steps/next_intent=end）。
- 规则条目：
  - R-H-29 入口收敛特例：收敛 updates 的 next_intent 覆写 end（防 answer→answer 环）。
  - R-H-30 起草触发五条件；零材料且非追问不烧模型（不起草）。
  - R-H-31 追问历史可答面：followup 轮起草指令追加历史条款（历史可答直答、不写 [n] 引标）。
  - R-H-32 相位④汇总：question_group 在场 → 汇总指令替换（SUMMARY_CONTRACT＋逐子问题清单＋作答合同）；ranking 支配句防跨子问题取值。
  - R-H-33 材料段渲染经 render_materials（帽＝deps.builder.max_observations）；截断→material_truncated notice。
  - R-H-34 起草调用 caller=answer、整链调用；空草稿同相位重试一次（同消息）。
  - R-H-35 空稿兜底三支：泄漏残留说明／追问人话＋decision_note／通用空稿壳。
  - R-H-36 泄漏检出（首试或重试）→emission_strip notice（确定性剥离，不进答案面；含是否重试注记）。
  - R-H-37 起草观察值只记不拦（echo_flag/paste_ratio 入 step payload＋process_notes draft digest）。
  - R-H-38 草稿链装配：一条 user 指令（含材料）＋一条 assistant 原稿；next_intent=verify。
  - R-H-39 未起草兜底路由：verdict 缺且 draft_kind!=direct 且 answer 空 → verify。
  - R-H-40 收口路径（verdict 在场／direct／answer 已有）→ _finalize。
- 耦合：`_complete`／`_gate_or_none`／`_finalize`／`_notes_with`／`_note`／`_step_record`／`_next_seq`／`_ANSWER_INSTRUCTION`／`_FOLLOWUP_HISTORY_ANSWER_CLAUSE`／`MODEL_ANSWER`／`strip_emission_fences`（本文件段外）；`answer_turn_preamble`／`assemble_answer_instruction`／`echo_signature_hit`／`paste_ratio`（appv2.runtime.orientation）；`render_materials`（appv2.runtime.context）；`SUMMARY_CONTRACT`（appv2.runtime.guide）；`_refusal_with_hint`（本文件 L3153）；`INTENT_VERIFY`／`INTENT_END`、`STEP_ANSWER`（appv2.runtime.state）；`deps.model`／`deps.bus`／`deps.builder.max_observations`。
- 疑点（只列不判，不静默）：
  - D-H-12 question_group 分支下追问条款丢失：`_FOLLOWUP_HISTORY_ANSWER_CLAUSE` 先追加（L3833-L3834），随后被 `assemble_answer_instruction` 整体重建指令覆盖（L3868-L3873）——同轮既追问又存在问题组时历史可答条款不进指令。
  - D-H-13 分支 3 条件不含「draft 空」：draft 已在手但 verdict None 时同样回 verify（走核验改写而非直接收口）。
  - D-H-14 起草触发条件的材料判据 `any(非 notice 观察)` 不校验 content 非空（L3819-L3823）：空壳观察（content 空串）也触发模型起草。
  - D-H-15 重试判据只看草稿是否空白（L3905-L3909）：首稿泄漏但剥离后有余量时直接交付、不重试；leaked 仅作聚合与 notice 披露。
  - D-H-16 起草分支要求 `not state.draft`：draft 已有值（非空）而 verdict 缺时直接走分支 3 回 verify，不再重新起草。
  - D-H-17 material_truncated notice 的渲染/总数取自 render_materials 元数据（material_rendered=len(ordered)、material_total=非 notice 全量；段外 appv2/runtime/context.py L72-L118）。

### `_ROUTES`（L3992-L4032，段内模块级常量表）｜七节点路由表：intent→节点名（legacy 与 four_phase 共用真源）
- 映射表（穷尽，逐键）：
  - `NODE_UNDERSTAND`（L3993-L3997）：decision→decision；answer→answer；end→END。
  - `NODE_DECISION`（L3998-L4004）：decision→decision（自环）；discover→discover；execute→execute；answer→answer；end→END。
  - `NODE_DISCOVER`（L4005-L4011）：observe→observe；discover→discover（自环）；decision→decision；answer→answer；end→END。
  - `NODE_EXECUTE`（L4012-L4018）：observe→observe；execute→execute（自环，行注释 L4014「retryable 同参重试自环」）；decision→decision；answer→answer；end→END。
  - `NODE_OBSERVE`（L4019-L4025）：discover→discover；execute→execute；decision→decision；answer→answer；end→END。
  - `NODE_VERIFY`（L4026）：answer→answer；end→END（仅两键，无 decision/discover/execute/observe/verify）。
  - `NODE_ANSWER`（L4027-L4031）：verify→verify；answer→answer（自环）；end→END（仅三键，无 decision）。
- 固定边：START 不在表内（build_graph L4106 定边 START→NODE_UNDERSTAND）。
- 副作用：无（纯常量；build_graph 只读并拷副本）。
- 规则条目：
  - R-H-41 白名单路由：每节点只接受表中键，其余 intent 无映射（判据函数见 `_route`）。
- 耦合：`NODE_*` 常量（本文件 L329-L341）、`INTENT_*` 常量（appv2.runtime.state）、`END`（langgraph.graph）、`Hashable`（collections.abc）。
- 疑点（只列不判，不静默）：
  - D-H-18 `NODE_VERIFY`／`NODE_ANSWER` 两表无 INTENT_DECISION 键：这两节点若发射 decision 值，条件边 mapping 缺键。
  - D-H-19 `NODE_ANSWER` 表含 answer→answer 自环：answer 节点自身返回 answer 意图（非收敛路径）时会再入 answer。

### `_route`（L4035-L4036）｜条件边判据：返回 next_intent（空值缺省 answer）
- 消费：`state.next_intent`。
- 分支表（穷尽）：
  1. `state.next_intent` 为真值（非空串）→ 原值返回（由对应节点路由表映射到目标节点）。
  2. `state.next_intent` 为空串／None → 返回 `INTENT_ANSWER`（缺省路由＝进 answer 收口）。
- 副作用：无。
- 返回：str（意图值）。
- 规则条目：
  - R-H-42 条件边唯一判据＝next_intent；空值缺省 answer（缺省路由即收口）。
- 耦合：`INTENT_ANSWER`（appv2.runtime.state）。
- 疑点（只列不判，不静默）：
  - D-H-20 不校验 next_intent 值域：闭世界外非空值原样返回，由条件边 mapping 缺键时在 langgraph 侧出错（本函数零兜底）。

### `_node_of`（L4039-L4049）｜add_node 形参恒等转换缝（形认缝，运行时零行为差）
- 消费：形参 `fn`（async callable）。
- 分支表：无（恒等返回 fn，零逻辑）。
- 副作用：无。
- 返回：`fn` 原对象（不改包装）。
- 规则条目：
  - R-H-43 恒等转换收口 langgraph `add_node` 的 `_Node` Protocol 在 mypy 下对「工厂返回的 async callable」解不出泛型的类型限制（docstring L4042-L4048）；节点签名仍受本模块 Callable 注记约束。
- 耦合：无（仅类型层；调用方 build_graph L4061-L4073）。
- 疑点：无。

### `build_graph`（L4052-L4109）｜图装配：七节点/四相位节点、START 定边、路由表条件边、compile 出口
- 消费：形参 `deps`（转交各工厂）、`checkpointer`（编译参数）、`four_phase`（装配开关）；RunState 类型。
- 调用：caller=executor（docstring「checkpointer 由 executor 注入」）；无 LLM/工具调用。
- 分支表（穷尽）：
  1. 恒定：`StateGraph(RunState)`；add_node 七节点——understand/decision/discover/execute/observe/verify/answer（各 `_node_of(_make_*(deps))`，L4061-L4067）。
  2. 恒定：`routes = {name: dict(mapping) for name, mapping in _ROUTES.items()}`（L4068，浅拷贝一层，模块常量不被改写）。
  3. `four_phase=False`（缺省）→ 跳过支 4，直接支 5/6/7（V2-31 七节点装配零漂移）。
  4. `four_phase=True`（L4069-L4105）→
     a. add_node 四相位节点 clarify/toolmatch/precondition/batch（L4070-L4073）；
     b. 遍历 routes 全部表：含 `INTENT_DECISION` 键者把该键值改写为 `NODE_CLARIFY`（L4074-L4076；值复用语义＝回第一决策相位）；
     c. 追加四张新表：
        - `routes[NODE_CLARIFY]`（L4077-L4088）：decision→clarify（拒因回喂自环／ask 挂起恢复入口）；discover→discover；toolmatch→toolmatch；precondition→precondition（审批恢复边，注释 B1/P-033）；answer→answer；end→END。
        - `routes[NODE_TOOLMATCH]`（L4089-L4094）：toolmatch→toolmatch（匹配拒因回喂自环）；precondition→precondition；answer→answer；end→END。
        - `routes[NODE_PRECONDITION]`（L4095-L4100）：batch→batch；decision→clarify（blocked_ask 挂起恢复→clarify interrupt）；answer→answer；end→END。
        - `routes[NODE_BATCH]`（L4101-L4105）：decision→clarify（引擎 ask 挂起／失败子集回炉①）；answer→answer；end→END。
  5. 恒定：`add_edge(START, NODE_UNDERSTAND)`（L4106）。
  6. 恒定：遍历 routes 全部表 `add_conditional_edges(name, _route, mapping)`（L4107-L4108）——legacy 七表；four_phase 追加四相位表后为十一表。
  7. 恒定：`builder.compile(checkpointer=checkpointer)` 返回（L4109）。
- 副作用：无（图构造；不 emit、不写 state）。
- 返回：编译后的图对象（`builder.compile(...)`）。
- 规则条目：
  - R-H-44 七节点全装配＋START→understand 定边；节点间全部路径经条件边（判据 `_route`）。
  - R-H-45 缺省 four_phase=False＝现行七节点图（骨架期既有装配零漂移）。
  - R-H-46 four_phase=True 加四相位真节点；所有「回决策」边（INTENT_DECISION 值）重定向 clarify。
  - R-H-47 四相位新增意图（toolmatch/precondition/batch）与新恢复边均由四张新表承载；审批恢复经 clarify→precondition（缺键会 KeyError，注释 L4081-L4085）。
  - R-H-48 checkpointer 由调用方注入（挂起/恢复存储机制）；compile 为唯一出口。
- 耦合：`StateGraph`／`START`／`END`（langgraph.graph）；`NODE_*` 常量（本文件）；`_ROUTES`／`_route`／`_node_of`／各 `_make_*` 工厂（本文件，含段外 understand/decision/discover/execute/clarify/toolmatch/precondition/batch 工厂）；`LoopDeps`／`RunState`（本文件／state）。
- 疑点（只列不判，不静默）：
  - D-H-21 four_phase 重定向为「值改写」而非新增键：legacy 表内注释书名「回决策」，四相位下同一值（decision）指向 clarify（语义＝回第一决策相位）；verify/answer 表无该键零改动。
  - D-H-22 checkpointer 缺省 None（无持久化图）；挂起/恢复语义依赖调用方注入，本函数不校验。
  - D-H-23 routes 由 `dict(mapping)` 浅拷贝后改写（L4068）：`_ROUTES` 模块常量零污染；四相位新增四表仅在副本字典内存在（four_phase=False 路径零泄漏）。

---

## 覆盖自检
- def 清单差集：无。本段 def 全部覆盖：`_make_observe`／`observe_node`／`_make_verify`／`verify_node`／`_finalize`／`_make_answer`／`answer_node`／`_route`／`_node_of`／`build_graph`；class：本段无；`_ROUTES` 为模块级常量（已按条目展开）。
- 本段 emit 事件名全集：`step`、`notice`、`observation`、`verdict`、`citation`、`text`（共六种；另 `ask` 事件由段外节点发射，不在本段）。
- 本段 notice 类型字面全集（事件帧 `type` 值）：`notice`（缺省型）、`decision_note`、`unsupported_claim`、`contradiction_split`、`attribution_split`、`material_truncated`、`emission_strip`（共七种；收敛 `budget_converged` 经段外 `_converge`）。
- 本段读写的 state 字段全集：
  - 读：`run_id`、`question`、`followup_of`、`observations`、`last_result`、`pending_discovers`、`pending_plan`、`pending_retrieval`、`draft`、`draft_kind`、`answer`、`verdict`、`messages`、`manifests`、`steps`（经 `_next_seq`）、`process_notes`（经 `_notes_with`）、`question_group`、`tool_matches`、`subtask_results`、`budget_hit`、`deadline_monotonic`（后二者经段外 `_gate_or_none`→`budget_gate_hit(include_rounds=False)`；`rounds`/`budget` 未被本段闸读取——轮数闸未开）。
  - 写（经返回 updates）：`observations`、`steps`、`next_intent`、`messages`、`draft`、`verdict`、`process_notes`、`answer`、`status`、`manifest_digest`；收敛路径另写 `budget_hit`、`notices`、`draft_kind`（段外 `_converge` 面）。
- 本段引用的外部符号全集（本文件内定义的除外）：
  - `appv2.runtime.budget`：`NO_MATERIAL_SHELL`；
  - `appv2.runtime.context`：`render_materials`、`trust_of`；
  - `appv2.runtime.guide`：`SUMMARY_CONTRACT`；
  - `appv2.runtime.orientation`：`answer_turn_preamble`、`assemble_answer_instruction`、`echo_signature_hit`、`paste_ratio`；
  - `appv2.tools`：`entity_anchor_tokens`；
  - `appv2.runtime.state`：`RunState`、`INTENT_ANSWER`／`INTENT_DECISION`／`INTENT_DISCOVER`／`INTENT_END`／`INTENT_EXECUTE`／`INTENT_OBSERVE`／`INTENT_VERIFY`／`INTENT_BATCH`／`INTENT_PRECONDITION`／`INTENT_TOOLMATCH`、`STEP_ANSWER`／`STEP_OBSERVE`／`STEP_VERIFY`；
  - `langgraph.graph`：`START`、`END`、`StateGraph`；
  - 标准库：`hashlib`、`json`、`re`（经 `_CITE_RE`）、`collections.abc`（`Callable`／`Coroutine`／`Hashable`）、`typing`（`Any`）；
  - deps 缝：`deps.bus.emit`（EventBus）、`deps.model`（`GatewayChatModel`，经 `_complete`）、`deps.builder.max_observations`。
- 补充（本文件内、段外被引用符号，接缝核查用）：`verify_draft`（L796）、`strip_emission_fences`（L697）、`_attribution_conflicts`（L923）、`_lineage_closing_note`（L1035）、`_step_record`（L1051）、`_next_seq`（L1068）、`_gate_or_none`（L1092）、`_converge`（L1083）、`_complete`（L1120）、`_observations_of`（L1131）、`_note`（L1227）、`_notes_with`（L1232）、`_refusal_with_hint`（L3153）、`_CITE_RE`（L260）、`_ANSWER_INSTRUCTION`（L273）、`_FOLLOWUP_HISTORY_ANSWER_CLAUSE`（L306）、`MODEL_ANSWER`（L324）、`NODE_*` 常量（L329-L341）、段外节点工厂 `_make_understand`／`_make_decision`／`_make_discover`／`_make_execute`／`_make_clarify`／`_make_toolmatch`／`_make_precondition`／`_make_batch`（build_graph 装配引用）。
