# C·现状调研报告

- 锚定：commit e4b75f1（行号以此为准）
- 覆盖：appv2/runtime/graph.py L1550-L1888（＋接缝 L1525-L1547 `_ban_exempt_preflight`——understand 豁免分支消费，随列）
- def/class 清单：逐一全列（含行号区间），不得省略
  1. `_ban_exempt_preflight`（L1525-L1547，接缝·范围外）——豁免命中出流（notice＋步记录）
  2. `_make_understand`（L1553-L1657）——工厂；内嵌 async 节点体 `understand_node`（L1556-L1655）
  3. `_decision_title`（L1663-L1671）——发射→步标题渲染
  4. `_make_decision`（L1674-L1886）——工厂；内嵌 async 节点体 `decision_node`（L1677-L1884）
  - 本范围内无 class 定义（`DecisionEmission` L497、`LoopDeps` L344 均在范围外）。
  - 两工厂调用点：graph.py L4061（understand）/L4062（decision）；均经 `_node_of` 恒等包装入 StateGraph。

---

### `_ban_exempt_preflight`（L1525-L1547，接缝·范围外）｜禁用词豁免命中出流：notice＋步记录先行，返回给 understand 合并

- 消费：state.steps（经 `_next_seq` 计 seq）；deps.bus；入参 item（BannedFact——`term`/`replacement` 字段，来自 `_n1_code_first_gate` 的 exempt 返回）。
- 装配：无（不碰 messages）。
- 调用：无 LLM/工具调用。
- 分支表（穷尽）：
  1. 无条件执行（本函数只在豁免命中时被调）→ emit notice（三键裁切）＋emit step → 返回（notice, record）给调用方 → understand 照常往下解析
- 副作用：emit notice（type="ban_exempt"，出流面只带 type/gates/content 三键，内部 notice 多携 term 机读键供 executor 审计）；step：decision 类、标题「N1 禁用词豁免放行（元问/引用形）」、payload={phase: "understand", n1_gate: "ban_exempt", term}；notice 类型：ban_exempt；持久化写：无（record 由调用方并入 steps）。
- 返回：（notice, record）二元组——notice 由调用方写 state.notices，record 由调用方写 state.steps。
- 规则条目（提取业务的核心——一句话一条：条件＋动作＋去向）：
  - R-C-01 豁免放行必留痕：notice 出流（SSE 面裁三键）＋decision 类步记录（payload 携 term）——「豁免＝放行非直出」的审计同源面。
  - R-C-02 豁免步先占 seq（此处 `_next_seq(state)` 取号，即 0 号位簿记），understand 本步 seq 由调用方顺延一位（返回时手工 +1）。
- 耦合：graph._step_record、graph._next_seq、tools.ban_exempt_notice_text（L655-663，文案携替代词，缺映射回落如实形）
- 疑点（只列不判，不静默）：
  - D-C-01 豁免步 seq 在此取号（L1541），understand 步在 L1622 以 `_next_seq(state)+1` 手工偏移——两处取号耦合、无断言，任一改动即可撞 seq。
  - D-C-02 「notice 出流裁三键、内部 notice 携 term」契约的消费方（executor 审计）不在本段可见，本段无守卫校验。

---

### `_make_understand` / `understand_node`（L1553-L1657；节点体 L1556-L1655）｜节点一·理解：入口安全闸族→任务书装配与链尾追加→模型调用与理解解析→直答分流→步/档案落账

- 消费：state.question、state.ledger_dump、state.messages、state.steps、state.process_notes、state.notices、state.budget_hit（经 `_gate_or_none`/`_converge`）；deps.bus、deps.ledger_dump、deps.watermark、deps.object_digests、deps.today、deps.model(MODEL_UNDERSTAND)。
- 装配：链尾追加 user 消息一条＝任务书（`build_understand_instruction` 产出；追加前先接 `state.messages`）→ 模型调用后追加 assistant 消息一条（模型原话）→ 整链写回 messages。一次性/每轮：任务书本 run 一次——代码无幂等标记，由图拓扑（START→understand 单入边，L4106）保证；本节点无回边。
- 调用：caller=understand（`deps.model(MODEL_UNDERSTAND)` 经 `_complete`）；输入=整条 messages 链（role→langchain 消息类）；解析=assistant 应答经 `parse_understanding` 得（理解, 指标候选）；失败怎么办=两级解析全空＝(""·空集) 如实上报，不拦停，下游照走决策轮。
- 分支表（穷尽，宁可细不可粗）：
  1. 入口预算闸 `_gate_or_none(state, deps)`（rounds_gate 缺省 False——只时长闸 total_seconds）命中且 budget_hit 为空 → `_converge`：notice budget_converged＋answer（有材料＝如实原样交付；零材料＝NO_MATERIAL_SHELL）＋draft_kind="direct"＋status=completed＋next_intent=answer → 出节点（answer 收口）
  2. state.budget_hit 非空（已收敛幂等，P-006b·R1）→ 闸返回 None（不二次收敛）→ 继续本节点
  3. N0 词面闸（`_n0_intent_word_gate`，安检序：注入→外发→写意图）任一命中 → 该闸内部已出 notice refused＋决策步＋`_direct_answer` → ("refused", updates) 直接返回（零模型零执行零 I/O）→ 去向 answer
  4. N1 禁用词非豁免命中（`_n1_code_first_gate` 返回 "refused"）→ 同形硬终止 updates 直接返回 → 去向 answer
  5. N1 豁免命中（"exempt"）→ `_ban_exempt_preflight` 出 notice＋步 → 放行（原问句照常进完整解析管线）→ 继续第 6 步
  6. 闸静默（未命中／词典层缝缺省）→ dump 读 state.ledger_dump，缺时取 `deps.ledger_dump()`，仍缺归空投影 {}；watermark 缝抛异常→watermark_date=None；装配任务书
  7. 直答分流：`parse_direct_reply(content)` 非空 → updates 抄 draft=直答文本、draft_kind="direct"、next_intent=answer（覆盖默认 decision）；本步其余产出（understanding/candidates/步/档案）照落 → 出节点（answer 免起草免核验收口）
  8. 直答为空 → next_intent=decision → 决策轮
  9. understanding 非空 → 另 emit text（kind="understanding"，灰条独立渲染）
  10. understanding 为空 → 不发 text；档案 digest 取 `direct_reply or understanding or "理解未产出"`
  11. 豁免步在场 → steps=[*state.steps, exempt_step, record]（豁免步在前）；否则 steps=[*state.steps, record]
- 副作用：emit step（decision 类；标题三形＝「无关业务——直接回答」／理解原文／「理解未产出」；payload.phase="understand"＋仅直答时 direct_reply:True）；emit text（kind="understanding"，仅 understanding 非空）；notice 类型：ban_exempt（豁免路，接缝出流）、refused（N0/N1 拒答，接缝函数内出流）；持久化写：无（全部经 updates 回写 RunState，checkpointer 由框架落）。
- 返回：updates 键全集＝understanding、metric_candidates、messages、process_notes、steps、next_intent；条件键＝notices（豁免时 [*state.notices, exempt_notice]）、draft＋draft_kind（直答时经 `_direct_answer`）；收敛路（`_converge` 接缝）另返 budget_hit、notices、answer、draft_kind、status、next_intent。
- 规则条目（提取业务的核心——一句话一条：条件＋动作＋去向）：
  - R-C-03 understand 入口先跑预算闸（只时长闸、不含轮数闸）；触界→收敛转答（已取得材料如实交付＋notice budget_converged）；已收敛（budget_hit 非空）→幂等跳过不二次收敛（单点防重复 notice）。
  - R-C-04 N0 词面闸先于 N1 禁用词闸（V1 安检序同源）：注入→外发→写意图三序任一命中＝硬终止（零模型零执行零 I/O，notice refused＋decision 步 payload.n1_gate 分型＋直答收口）。
  - R-C-05 N1 禁用词闸先于一切解析（唯一前置例外）：词面闭世界命中→豁免判定；豁免（元问/引用形）＝放行非直出（notice＋步先行，原问句进完整管线）；非豁免＝硬终止（拒因文案携「替代：X」或「见台账」，不代答废弃口径）。
  - R-C-06 词典层缝缺省（state.ledger_dump 与 deps.ledger_dump 均无）→ N1 闸静默零漂移（不判）；N0 不读词典照常判。
  - R-C-07 豁免步占 seq 0 号位（先于 understand 本步）；understand 步 seq=本步取号+1，返回 steps 豁免步在前。
  - R-C-08 任务书每 run 追加链尾一次（user 消息形态）；内容＝静态骨架＋活体环境（question/台账 dump/本体对象摘要/水位/today 同源渲染）；object_digests 缝缺省回落台账 dump.objects 薄形。
  - R-C-09 理解解析两级宽容：两行合同式（理解：／指标候选：）优先；两行全缺降级 JSON 子串（中文主键＋英文别名逐键取值，缺键不编造）；两级全空＝空值如实上报，不阻断。
  - R-C-10 无关业务直答分流（V2-78）：应答含行首「直接回答：」行→确定性直答通道（draft_kind=direct ＋ next_intent=answer，免起草免核验）；业务含糊（缺对象/窗界）不适用此形，照常两行式进决策轮。
  - R-C-11 模型原话不入对话层（V2-79a 三层分离）：理解摘要落 process_notes（digest 截 200 字）；understanding 是 state 字段与 text 事件（kind=understanding）双出口。
  - R-C-12 对话链只追加不改写：任务书＋应答各一条写回 messages（前缀延伸形态）。
  - R-C-13 直答/闸拒的 next_intent 覆盖本节点默认 INTENT_DECISION——一律转 answer 面收口。
- 耦合：graph._gate_or_none、graph._converge、graph._n0_intent_word_gate、graph._n1_code_first_gate、graph._ban_exempt_preflight、graph._complete、graph.parse_understanding、graph.parse_direct_reply、graph._note/_notes_with/_step_record/_next_seq/_direct_answer、orientation.build_understand_instruction（L165，内部 assemble_understand_turn）、state.RunState/INTENT_DECISION/INTENT_ANSWER/STEP_DECISION、llm.GatewayChatModel、events.EventBus。
- 疑点（只列不判，不静默）：
  - D-C-03 任务书链尾追加无幂等标记（对比 decision 的 contracts_appended）：每 run 一次仅由图拓扑（START→understand 单入边）保证，增回边即重复追加。
  - D-C-04 understand 读取 dump 的缝回退结果不写回 state.ledger_dump（对比 N0/N1 拒答路径 L1432-1433/L1518-1519 与 clarify 节点 L2469/2481 写回）——同一字段在三个节点三种持久化行为；state.py L158-159 注释「第 1 次澄清入口取一次随 checkpoint 走」仅对 clarify 成立。
  - D-C-05 直答分流与理解解析未互斥：direct_reply 非空时 understanding 仍可写 state 并发 text 事件（模型同产两形时两通道同时生效）。
  - D-C-06 问句原文与直答话术都不进 messages：本节点只追加任务书/模型应答；被拒问句亦只存在于 state.question——追加式链中用户问题只以任务书形出现（对追问/缓存面影响需重构时确认）。

---

### `_decision_title`（L1663-L1671）｜发射→步标题渲染（四形）

- 消费：入参 emission（DecisionEmission）、rnd（轮号）。
- 装配：无。
- 调用：无 LLM/工具调用（纯字符串）。
- 分支表（穷尽）：
  1. action=discover → 「决策 r{rnd}：发现×N（工具名顿号连接，缺 tool 键渲染 "?"）」→ 返回标题串
  2. action=execute → 「决策 r{rnd}：执行 {task_type}」→ 返回
  3. action=ask → 「决策 r{rnd}：澄清（{ask_prompt 前 24 字}）」→ 返回
  4. 其余（else 兜底，含 finalize）→ 「决策 r{rnd}：定稿」→ 返回
- 副作用：无。
- 返回：str（步标题）。
- 规则条目：
  - R-C-14 步标题四形由 action 分派；finalize 是 else 兜底（非显式判 ACTION_FINALIZE）——action 闭世界性由 parse_decision 上游保证。
  - R-C-15 标题三处截断/连接形：discover 工具名顿号连接、execute task_type、ask prompt[:24]。
- 耦合：graph.DecisionEmission、graph.ACTION_DISCOVER/ACTION_EXECUTE/ACTION_ASK
- 疑点：
  - 无。

---

### `_make_decision` / `decision_node`（L1674-L1886；节点体 L1677-L1884）｜节点二·legacy 决策：挂起恢复入口→预算闸→指南包/增量回喂装配→决策调用与解析→拒因自环／同参拦截／四 action 发射分支

- 消费：state.pending_ask、state.budget_hit（经 `_gate_or_none`）、state.budget、state.rounds、state.contracts_appended、state.messages、state.ledger_dump、state.decision_error、state.user_hint、state.process_notes、state.executed_payloads、state.consecutive_asks、state.observations＋state.last_result（封顶直答经 `_clarify_capped_answer`→material_rows）、state.notices、state.steps、state.run_id（ask 事件携行）；挂起恢复路经 `_handle_choice` 另读 state.messages/process_notes/steps；deps.bus、deps.guide、deps.ledger_dump、deps.model(MODEL_DECISION)。
- 装配：链尾追加（链只追加、相邻调用互为前缀延伸）——①指南包一条 user（首入一次性：contracts_appended 无 "decision" 时；内容=deps.guide.guide()＋「\n\n任务：输出本轮决策 JSON。」＋dump 非空时附 `_resident_block` 台账常驻块）；②拒因回喂一条 user（decision_error 非空）；③用户补充一条 user（user_hint 非空）；④已做段一条 user（process_notes 非空，`_render_process_notes` 有界 ≤400 字、截断带披露行、零档案零段）；⑤模型应答 assistant 一条。
- 调用：caller=decision（`deps.model(MODEL_DECISION)` 经 `_complete`）；输入=整条 messages 链；解析=`_parse_with_quote_repair(parse_decision)` 得 DecisionEmission 或 str 拒因；失败怎么办=拒因入 decision_error 回喂 LLM 下轮重决策（无 repair 桶），轮照耗，轮数闸下一入口兜底。
- 分支表（穷尽，含全部 return 点与去向）：
  1. state.pending_ask 非空（挂起恢复路径）→ `await _handle_choice(state, deps)`（interrupt 返回用户选择；先于闸与模型调用——挂起等人工不计预算）→ 返回其 updates → 去向 decision（澄清回喂）／其余分支由 _handle_choice 定
  2. 入口 `_gate_or_none(state, deps, rounds_gate=True)` 命中（max_rounds／total_seconds）且 budget_hit 空 → `_converge` → 返回收敛 updates（next_intent=answer）→ 去向 answer
  3. budget_hit 非空 → 幂等跳过（不二次收敛）→ 继续
  4. 指南包首入：contracts_appended 无 "decision" → package=guide()＋任务行＋（dump 非空时）台账常驻块 → 追加 user 一条，contracts_flag=True；否则 contracts_flag=False（不重发）
  5. decision_error 非空 → 追加 user 一条（「上次决策被拒：…修正后重新输出 JSON。」）
  6. user_hint 非空 → 追加 user 一条（「用户已补充：…请把它落进本轮决策。」）
  7. process_notes 非空 → 追加 user 一条（有界摘要段）
  8. 模型调用 `_complete` → assistant 追加 → `_parse_with_quote_repair`：引号修复受理 → emit notice emission_quote_repair（只出流）
  9. 解析为 str（拒因，return 点 A）→ 步「决策 r{rnd} 被拒：{parsed}」＋档案＋rounds=rnd＋decision_error=parsed＋contracts_appended 条件追加 → next_intent=decision → 自环回 decision 入口
  10. retrieval_need 非空 → `inject_retrieval_anchors` 确定性注入（代码注入项在前、模型可增补不可清空）→ 载荷定型后进入同参判定
  11. action=execute 且 `_is_same_param_replay`（全部已执行支都在 executed_payloads）（return 点 B，同参拦截）→ 步「决策 r{rnd} 同参重投被拦：{reason}」＋notice same_param_replay＋decision_error=虚拟拒因＋rounds=rnd → next_intent=decision → 自环
  12. 正常发射（return 点 C 前段）→ 步记录（标题经 `_decision_title`；payload={phase, emission.as_payload()}）→ 基础 updates（rounds=rnd、decision_error=""、user_hint=""、messages、contracts_appended、process_notes、steps、task_type=emission.task_type）
  13. emission.note 非空（任意 action）→ notice decision_note（出流＋写 notices）
  14. action=discover（return 点 C-1）→ pending_discovers=逐项 dict 拷贝＋next_intent=discover → 去向 discover
  15. action=execute（return 点 C-2）→ pending_plan＋pending_retrieval（各 dict 拷贝或 None）＋next_intent=execute → 去向 execute
  16. action=ask 且 consecutive=state.consecutive_asks+1 ≥ CLARIFY_ASK_CAP_CONTRACT(=6)（return 点 C-3a，封顶截断）→ notice clarify_capped＋`_direct_answer`（draft=带材料如实直答/NO_MATERIAL_SHELL；draft_kind="direct"；next_intent=answer 覆盖）→ 去向 answer（不再挂起）
  17. action=ask 未封顶（return 点 C-3b，挂起）→ consecutive_asks=consecutive＋pending_ask={kind:"clarify", prompt, options, detail:None}＋next_intent=decision＋emit ask（frame＋run_id）→ 去向 decision：下一入口 pending_ask 分支进 interrupt（挂起）
  18. 其余（finalize，return 点 C-4）→ next_intent=answer → 去向 answer
- 副作用：emit step（decision 类：被拒/同参被拦/`_decision_title` 四形；payload 三形＝rejection／rejection+gate／emission）；emit notice（emission_quote_repair 仅出流；same_param_replay、clarify_capped、decision_note 出流＋写 notices）；emit ask（{frame, run_id}，仅未封顶 ask）；持久化写：无（全部经 updates 回写）；挂起/恢复经 `_handle_choice` 的 interrupt 接缝（节点体外的下接缝）。
- 返回：updates 键——全路径公共：rounds、messages、contracts_appended、process_notes、steps、next_intent；拒因/同参另加 decision_error；正常发射另加 decision_error=""、user_hint=""、task_type；条件键：notices（same_param/clarify_capped/decision_note），pending_discovers、pending_plan、pending_retrieval、pending_ask、consecutive_asks、draft＋draft_kind（封顶直答）。挂起恢复分支返回 `_handle_choice` 的 updates（pending_ask None、resume_choices、user_hint、rounds 重置等，出本段）。
- 规则条目（提取业务的核心——一句话一条：条件＋动作＋去向）：
  - R-C-16 挂起恢复优先于闸与模型调用：pending_ask 非空→委托 `_handle_choice`（interrupt 返回用户选择）；挂起等人工不计预算。
  - R-C-17 澄清回收（_handle_choice 内）：user_hint=用户选择、rounds=0 重置轮预算（每用户输入周期 3 轮）、budget_reject_streak=0、用户原话落 messages（去系统前缀）、过程档案＋步随行。
  - R-C-18 决策入口是唯一开轮数闸的节点（rounds_gate=True：max_rounds＋total_seconds）；触界→收敛转答。
  - R-C-19 轮内上限（发现/主执行）从 state.budget 读、缺省合同值 2/2——随 checkpoint 走，测试可收窄。
  - R-C-20 指南包＋台账常驻块首入一次性（contracts_appended 无 "decision" 才追加一条，回炉轮不重发——链上已有缓存照命中）；后续轮只发增量条。
  - R-C-21 台账常驻块只在 dump 非空时附（空投影不造空块）；块形＝BEGIN＋字典头注 LEDGER_DICT_NOTE＋台账/别名/结构卡三块＋END。
  - R-C-22 三类增量消息均 user 形态且固定序追加：拒因（decision_error）→用户补充（user_hint）→已做摘要段（process_notes）；摘要段有界 ≤400 字、超限带披露行（已渲染 N/M 条）、零档案零段。
  - R-C-23 决策解析＝平衡块提取＋schema 闭世界校验：action 四值；discover 支数≤轮内上限且工具在白名单；execute task_type 三值＋按型必填 plan(metric_slot 非空)/retrieval_need(question 非空)；ask prompt 必填＋options 2~4；finalize 零载荷——非法产＝str 拒因。
  - R-C-24 引号自修兜底（零模型零语义）：一次确定性引号修复重解析；修好＝受理＋emission_quote_repair notice（只出流）；修不好＝原拒因路径。
  - R-C-25 拒因自环（无 repair）：轮照耗（rounds=rnd）＋decision_error=拒因＋next_intent=decision；轮数闸在下一入口收敛兜底。
  - R-C-26 anchors 确定性注入发生在同参指纹判定之前：注入随发射载荷定型，重投闸比对面一致；注入项不可被模型清空/覆盖。
  - R-C-27 同参重投机器闸：action=execute 且发射载荷全部已执行支都在 executed_payloads→确定性拦截（不触工具）＋虚拟拒因回喂＋notice same_param_replay＋轮照耗＋自环；任一支新参＝放行（改参零误伤）；审批重投/retryable 同参重试不经本出口不受辖。
  - R-C-28 正常发射步标题四形（发现×N／执行 task_type／澄清 prompt 前 24 字／定稿）；payload 携发射全投影。
  - R-C-29 正常发射统一 rounds=rnd、decision_error=""、user_hint=""（本轮已消费）、task_type=emission.task_type（非 execute 发射写空串——state.task_type 语义为「末次执行发射的任务型」）；contracts_appended 仅首入轮追加 "decision"。
  - R-C-30 emission.note 非空→notice decision_note（任意 action 生效，落 notices＋出流）。
  - R-C-31 discover 发射→pending_discovers（逐项 dict 拷贝）＋next_intent=discover。
  - R-C-32 execute 发射→pending_plan＋pending_retrieval（各 dict 拷贝或 None）＋next_intent=execute。
  - R-C-33 ask 发射→consecutive_asks+1（run 生命期不清零）；达 CLARIFY_ASK_CAP_CONTRACT（=6）→不挂起、notice clarify_capped＋带已取得材料如实直答（不落 budget_hit——机读分型走 notice）。
  - R-C-34 ask 未封顶→pending_ask 帧（kind=clarify／prompt／options 列表／detail=None）＋emit ask（携 run_id）＋next_intent=decision——下一入口挂起（interrupt）。
  - R-C-35 finalize（else 兜底）→next_intent=answer。
- 耦合：graph._handle_choice（L1892，下接缝）、graph._gate_or_none/_converge、graph._complete、graph._parse_with_quote_repair、graph._quote_repair_notice、graph.parse_decision、graph._is_same_param_replay、graph._resident_block（内部 _resident_sources）、graph._render_process_notes、graph._note/_notes_with/_step_record/_next_seq/_direct_answer/_clarify_capped_answer、graph._decision_title、graph.MODEL_DECISION、graph.ACTION_*、graph.GATE_SAME_PARAM_REPLAY/SAME_PARAM_REPLAY_REASON、budget.CLARIFY_ASK_CAP_CONTRACT/MAX_DISCOVERS_PER_ROUND_CONTRACT/MAX_EXECUTES_PER_ROUND_CONTRACT、tools.inject_retrieval_anchors（内部 entity_anchor_tokens）、tools.ASK_CLARIFY（值 "clarify"）、guide.GuideProvider.guide、state.RunState/INTENT_DECISION/INTENT_DISCOVER/INTENT_EXECUTE/INTENT_ANSWER/STEP_DECISION、dataclasses.replace、langgraph.types.interrupt（经 _handle_choice）。
- 疑点（只列不判，不静默）：
  - D-C-07 本段注释称「第 3 次 ask 即截断（V2-70 b 案上限 3）」（L1857），实际 CLARIFY_ASK_CAP_CONTRACT=6（budget.py L38，注释记同日 3→6 放宽）——注释旧值残留。
  - D-C-08 emission_quote_repair notice 只经 bus 出流、不入 state.notices（L1734-1736）；同节点内 same_param_replay/clarify_capped/decision_note 三类 notice 均落 notices——持久化面不一致。
  - D-C-09 解析拒（return 点 A）不产生任何 notice（用户面不可见），拒因只经 decision_error 指令面回喂；同参拦截（return 点 B）则同时出 notice。
  - D-C-10 解析拒路径丢失 payload.note（parse_decision 校验失败即返回 str，note 不随行）——非法发射的模型注记不达 notice 面。
  - D-C-11 max_discovers/max_executes 经 int() 截断 state.budget 浮点存值（Budget.as_dict 存 float），无下限/越界校验——checkpoint 中 1.9 类值会被收窄为 1。
  - D-C-12 four_phase=True 装配（L4068-4076）把全部 INTENT_DECISION 边重定向 clarify，NODE_DECISION 无入边（仅在 legacy 装配可达）——本节点在四相位生产装配下为注册但不可达节点；与 clarify 节点能力重叠（本段注释未标记该退役关系）。
  - D-C-13 封顶分支 consecutive_asks 不再自增（第 6 次 ask 时 state 停在 5，L1858-1870）——字段语义实为「已放行挂起次数」而非「ask 发射次数」。
  - D-C-14 contracts_appended 条件追加表达式在三个 return 点逐字重复（L1750-1753／L1798-1801／L1822-1825）——同一语义三处拷贝，重构收口候选。

---

## 覆盖自检

- def 清单差集：无——L1550-L1888 内 def 全列（`_make_understand` L1553、`_decision_title` L1663、`_make_decision` L1674，含内嵌节点体）；接缝 `_ban_exempt_preflight`（L1525-L1547，范围外）另列条目。
- 本段 emit 事件名全集：step、text、notice、ask（经接缝/_converge 仍为 step/notice；本段无 verify/answer 类事件）。
- 本段读写的 state 字段全集：
  - 读：question、messages、steps、process_notes、notices、ledger_dump、budget、budget_hit、rounds、contracts_appended、decision_error、user_hint、executed_payloads、consecutive_asks、pending_ask、run_id、observations、last_result（封顶直答经 material_rows）。
  - 写（updates）：understanding、metric_candidates、messages、process_notes、steps、next_intent、notices、draft、draft_kind、rounds、decision_error、user_hint、contracts_appended、task_type、pending_discovers、pending_plan、pending_retrieval、pending_ask、consecutive_asks；收敛路（接缝）另写 budget_hit、answer、status。
- 本段引用的外部符号全集（本文件内定义的除外）：
  - state.py：RunState、STEP_DECISION、INTENT_DECISION、INTENT_DISCOVER、INTENT_EXECUTE、INTENT_ANSWER
  - budget.py：CLARIFY_ASK_CAP_CONTRACT、MAX_DISCOVERS_PER_ROUND_CONTRACT、MAX_EXECUTES_PER_ROUND_CONTRACT、NO_MATERIAL_SHELL、budget_gate_hit、material_rows、unfinished_notice
  - events.py：EventBus；llm.py：GatewayChatModel；guide.py：GuideProvider
  - orientation.py：build_understand_instruction（间接 assemble_understand_turn）
  - subtask.py：extract_plan_json、json_syntax_feedback、repair_inner_quotes（经 parse_decision/_parse_with_quote_repair 间接）
  - tools：ASK_CLARIFY、inject_retrieval_anchors（间接 entity_anchor_tokens）、ledger_facts、is_ban_exempt、ban_exempt_notice_text（经 N1/豁免接缝间接）
  - tools.ledger：RESIDENT_BLOCK_BEGIN、RESIDENT_BLOCK_END；context.py：LEDGER_DICT_NOTE（经 _resident_block 间接）
  - 外部库：dataclasses.replace（decision 直接调用）、langgraph.types.interrupt（经 _handle_choice 间接）
