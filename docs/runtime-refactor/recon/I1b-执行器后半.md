# I1b·现状调研报告
- 锚定：commit e4b75f1（行号以此为准）
- 覆盖：appv2/runtime/executor.py L265-638（文件止于 L638）
- 锚点核验：`git diff e4b75f1 HEAD -- appv2/runtime/executor.py` 为空——锚定 commit 与 HEAD(085b294) 逐字节同，行号一致。
- def/class 清单：15 项逐一全列（含行号区间），无省略。

| 符号 | 行区间 |
|---|---|
| `GraphRunExecutor._seed_messages` | L265-L319 |
| `GraphRunExecutor.pending_ask_of` | L321-L337 |
| `GraphRunExecutor._deps` | L339-L361 |
| `GraphRunExecutor._initial_state` | L363-L388 |
| `GraphRunExecutor._spawn` | L390-L410 |
| `GraphRunExecutor._drive` | L412-L511 |
| `GraphRunExecutor._audit` | L515-L533 |
| `GraphRunExecutor._audit_closeout` | L535-L563 |
| `GraphRunExecutor._audit_decisions` | L565-L586 |
| `GraphRunExecutor._audit_ban_exempts` | L588-L607 |
| `AgentRuntime`（class） | L610-L638 |
| `AgentRuntime.__init__` | L613-L614 |
| `AgentRuntime.ask` | L616-L628 |
| `AgentRuntime.resume` | L630-L634 |
| `AgentRuntime.pending_ask` | L636-L638 |

接缝上下文（L230-263，段外）：`execute` 的 COMMAND_RESUME 支在 L233-242 读 checkpoint 快照算 `resume_choice_base`（resume_choices 长度）与 `ban_exempt_base`（notices 中 type=="ban_exempt" 计数），L243-248 刷新 `deadline_monotonic`，L250-259 经 `_spawn` 送 Command(resume=choice.as_payload())、who=str(run.actor)。这两个 base 值即本段两个 `_audit*` 的切片起点。

---

### `_seed_messages`（executor.py L265-L319）｜前轮对话播种：v3 整链承接／v2 dialogue 降级／v1 旧 checkpoint 兼容抽取三态
- 消费：self（`_store`/`_saver`/`_deps`/`_four_phase`）；参数 `followup_of`（前轮 run 号）；`prior = self._store.get_run(followup_of)` 的 status/answer/question；checkpointer 线程态 values 的 `messages`/`dialogue` 两键。
- 装配：v3 分支不追加不前置（整链原样返回）；v2/v1 分支链首前置一条 system（SYSTEM_PROMPT）；v2 分支链尾防御位追加一条 assistant（prior.answer，仅当末轮 role 非 assistant 且 prior.answer 非空）。
- 调用：caller=`GraphRunExecutor.execute`（L186，COMMAND_ASK 支、create_run 之前）；抛 `RunNotFoundError`（前轮缺）与 `RunNotSuspendedError`（前轮非 completed），execute 不捕获——上抛 api 映射 404/409。
- 分支表（穷尽）：
  1. `not followup_of`（空串）→ 返回 `[]` → execute 走非追问播种（_initial_state 的 else 支）
  2. prior 为 None → raise RunNotFoundError → api 404
  3. prior.status != "completed" → raise RunNotSuspendedError → api 409（在途/失败轮不可续；挂起轮走 resume）
  4. `messages` 键过滤 dict 后非空（v3）→ 原样返回 chain → 新 run 状态 messages＝前链＋新问（system 首条不重复）
  5. `messages` 空且 `dialogue` 过滤后非空（v2）→ 若末轮 role != assistant 且 prior.answer 真值则追加 assistant 终稿 → 返回 [system, *dialogue]
  6. `dialogue` 空（v1/无 checkpoint）→ `extract_dialogue_from_legacy_history(values, question=prior.question, answer=prior.answer)` → 返回 [system, *legacy]
  - 注：`messages` 键在场但条目全为非 dict 时过滤为空，落到第 5 支；两通道的 role/content 一律 `str()` 强转。
- 副作用：emit 无（内部 `EventBus()` 一次性实例，无 emit/stream/close 调用）；持久化写 无（仅 `aget_state` 只读）。
- 返回：`list[dict[str, str]]`（空列表＝非追问播种）。
- 规则条目（一句话一条：条件＋动作＋去向）：
  - R-I1b-01 followup_of 空 → 直接返回空列表（不触库、不建图）→ 新 run 全新链
  - R-I1b-02 前轮不存在 → RunNotFoundError 上抛 → api 404
  - R-I1b-03 前轮非 RUN_COMPLETED → RunNotSuspendedError 上抛 → api 409
  - R-I1b-04 v3 承接：messages 非空 → 整链原样返回（不重复前链 system 首条）
  - R-I1b-05 v2 降级：dialogue 非空 → 末轮非 assistant 且 prior.answer 非空才补 assistant 终稿 → 前置 system 返回
  - R-I1b-06 v1 兼容：两通道皆空 → extract_dialogue_from_legacy_history 抽取 → 前置 system 返回
  - R-I1b-07 只读零写回：仅 build_graph＋aget_state 读前轮态，前轮 checkpoint 零写
  - R-I1b-08 逐条净化：role/content 强转 str、仅 dict 条目入链（两通道同款）
- 耦合：appv2.runtime.graph.build_graph；appv2.runtime.graph.LoopDeps；appv2.runtime.events.EventBus；appv2.runtime.store.RunStore.get_run；appv2.runtime.context.SYSTEM_PROMPT；appv2.runtime.state.RUN_COMPLETED；文件内 L99 的 extract_dialogue_from_legacy_history（段外定义）。
- 疑点（只列不判，不静默）：
  - D-I1b-01 v3 分支不校验前链末轮角色（v2 分支备有防御位终稿、v3 无）——前链以 user 轮收尾时新问句与旧 user 轮相邻；图侧处置不在本文件。
  - D-I1b-02 本函数内 `EventBus()` 仅满足 LoopDeps 必填（guide/bus 无缺省），无任何消费点——读态重建实际不产事件。
  - D-I1b-03 v2 分支在 prior.answer 为空时不补终稿——对话链可能以 user 轮收尾；此形态无口径。

### `pending_ask_of`（executor.py L321-L337）｜挂起帧读面：checkpointer 线程态 pending_ask 投影
- 消费：self（`_saver`/`_deps`/`_four_phase`）；参数 `run_id`；checkpointer values 的 `pending_ask` 键。
- 装配：不涉及（不装配消息链）。
- 调用：caller=`AgentRuntime.pending_ask`（L638）→ api GET run 详情；无异常捕获（aget_state 异常直接上抛）；无帧返回 None 不抛。
- 分支表（穷尽）：
  1. `pending_ask` 是 dict → 返回 `dict(frame)`（浅拷贝）→ 调用方得帧投影
  2. 否则（键缺/None/非 dict）→ 返回 None（非挂起与无帧同语）
- 副作用：emit 无；持久化写 无（只读，零写）。
- 返回：`dict[str, Any] | None`。
- 规则条目：
  - R-I1b-09 只读零写：图重建＋aget_state 取帧，不落任何持久化写
  - R-I1b-10 帧非 dict 一律 None——与"无帧"不可区分、不抛错
- 耦合：appv2.runtime.graph.build_graph；LoopDeps；appv2.runtime.events.EventBus；RunState.pending_ask（状态字段）。
- 疑点（只列不判，不静默）：
  - D-I1b-04 docstring 称"与 _seed_history 同款"，但全仓检索 `_seed_history` 仅此一处（L325）出现——无同名符号定义，属文档性引用。
  - D-I1b-05 `dict(frame)` 浅拷贝——嵌套值（如 options 列表）与原帧共享引用；当前调用方只读故无实测影响。

### `_deps`（executor.py L339-L361）｜LoopDeps 装配：per-run 模型副本盖章＋组合根缝透传
- 消费：参数 `bus`/`run_id`；self 的 `_models`/`_registry`/`_builder`/`_store`/`_guide`/`_ledger_dump`/`_watermark`/`_data_wells`/`_object_digests`/`_today`。
- 装配：不涉及。
- 调用：caller=`execute`（L199 ask/L225 resume）、`_seed_messages`（L288）、`pending_ask_of`（L328）；无失败路径（纯构造）。
- 分支表（穷尽）：
  1. run_id 真值 → models＝逐项 `model_copy(update={"run_id": run_id})` 的新字典（per-run 副本）→ LoopDeps 携副本
  2. run_id 空串 → models＝self._models 原字典（共享引用）
- 副作用：emit 无；持久化写 无。
- 返回：`LoopDeps`（11 参：registry/models/builder/store/bus/guide/ledger_dump/watermark/data_wells/object_digests/today）。
- 规则条目：
  - R-I1b-11 run_id 非空 → 每模型副本盖章 run_id（GatewayChatModel.run_id → 网关记账归属链）→ 共享字典零变异
  - R-I1b-12 缝参数原样透传（builder/guide/ledger_dump/watermark/data_wells/object_digests/today）——缺省 None 即缝关
- 耦合：appv2.runtime.graph.LoopDeps；appv2.runtime.llm.GatewayChatModel.model_copy；appv2.runtime.events.EventBus。
- 疑点（只列不判，不静默）：
  - D-I1b-06 读态重建两调用点传的 run_id 是"被读 run"（_seed_messages 传前轮 followup_of、pending_ask_of 传目标 run）——同参两名（本 run／被读 run）；读态不调模型故无记账后果。
  - D-I1b-07 builder 仍从组合根透传——LoopDeps 注释称 V2-80h compile 退役后缝仅为 blackbox/测试注入位，_deps 侧无退役标记。

### `_initial_state`（executor.py L363-L388）｜初始 RunState 构造：追问链 vs 全新链＋预算/时限播种
- 消费：参数 run_id/question/actor_id/seed_messages/followup_of；self._budget。
- 装配：seed_messages 真值 → messages＝[*seed_messages, {role:"user", content:question}]（链尾追加新问）；否则 messages＝[{role:"system", content:SYSTEM_PROMPT}]。
- 调用：caller=`execute`（L203-206，COMMAND_ASK 支）；无失败路径。
- 分支表（穷尽）：
  1. `seed_messages` 真值非空 → 前链承接＋新 user 问句 → 新跑图输入
  2. 空/None（falsy，含空列表）→ system 独条全新链
- 副作用：emit 无；持久化写 无（构造值随图输入由 checkpointer 落）。
- 返回：`RunState`（run_id/question/actor/status=RUN_RUNNING/followup_of/messages/budget=Budget.as_dict()/started_monotonic/deadline_monotonic=started+total_seconds）。
- 规则条目：
  - R-I1b-13 追问链＝前链＋新 user 问（system 不重复）
  - R-I1b-14 时限随状态播种：deadline_monotonic＝段首 now_monotonic＋budget.total_seconds
  - R-I1b-15 followup_of 随 RunCommand 播种（V2-53 追问旁路判据，入库后仅读）
- 耦合：appv2.runtime.state.RunState/RUN_RUNNING；appv2.runtime.context.SYSTEM_PROMPT；appv2.runtime.budget.now_monotonic；Budget.as_dict/total_seconds。
- 疑点（只列不判，不静默）：
  - D-I1b-08 `seed_messages=[]`（空列表）与 None 不可区分（同走 else）——"非追问"恰以空列表形态传入，语义依赖 falsy 判定。

### `_spawn`（executor.py L390-L410）｜后台任务点火：create_task(_drive)＋任务集自清
- 消费：参数 graph/graph_input/config/bus/run_id/who/resume_choice_base/ban_exempt_base；self._tasks。
- 装配：不涉及。
- 调用：caller=`execute`（L208 ask、L250 resume）；无异常路径（_drive 以协程交给事件循环，异常不由本函数处理）。
- 分支表（穷尽）：无分支（单路径：create_task → 任务集 add → done 回调 discard）。
- 副作用：emit 无；持久化写 无（_drive 内发生）；创建 asyncio.Task，self._tasks 增删。
- 返回：None（不返 task 句柄——fire-and-forget）。
- 规则条目：
  - R-I1b-16 fire-and-forget：后台驱动 _drive，受理路径立即返回 RunHandle
  - R-I1b-17 任务集只供持引用与自清（done 回调 discard）——无异常接收点、无取消入口
- 耦合：asyncio.create_task；GraphRunExecutor._drive。
- 疑点（只列不判，不静默）：
  - D-I1b-09 _drive 异常若逃出（见 D-I1b-12），done 回调只 discard——任务异常无 retrieve 点（asyncio "Task exception was never retrieved" 面），受理方无从感知。

### `_drive`（executor.py L412-L511）｜图驱动收口：ainvoke 后台跑图＋三终态落库＋审计四事件＋事件流收束
- 消费：参数 graph/graph_input/config/bus/run_id/who/resume_choice_base/ban_exempt_base；self（`_store`/`_auditor`）；final 的 steps/pending_ask/error/answer/manifest_digest/notices/resume_choices 键（后四者经 _audit* 消费）。
- 装配：不涉及（消息链由图节点在图内维护）。
- 调用：caller=`_spawn`（L403）；内部调 put_steps/finish_run/_audit/_audit_decisions/_audit_ban_exempts/_audit_closeout/distill/put_blackbox/pointer/bus.emit/close。
- 分支表（穷尽；try/except/finally 三层）：
  1. ainvoke 返回 final → `put_steps(run_id, final.steps)` 整量落库（空列表早退）
  2. `final.pending_ask` 真值 → `finish_run(waiting_ask)` → _audit_decisions（base=resume_choice_base）→ _audit_ban_exempts（base=ban_exempt_base）→ 不发收口审计
  3. 否则 `final.error` 真值 → `finish_run(failed, error)` → `_audit(run_failed)` → _audit_decisions → _audit_ban_exempts
  4. 否则 → `finish_run(completed, answer, manifest_digest or None)` → _audit_decisions → _audit_ban_exempts → `_audit_closeout`（拒答/正常互斥）
  5. except Exception → `run_error=str(exc)` → `finish_run(failed, error)` → `_audit(run_failed)` → `bus.emit("notice", {type:"run_failed", gates:[], content:"run 执行失败：…"})`
  6. finally → `record=distill(final, run_id, error=run_error)`（final=None＝骨架记录）
  7. finally → `blob_bytes=len(json.dumps(record, ensure_ascii=False))` → `put_blackbox` 成功置 `stored=True`；序列化或入库异常 → notice{blackbox_write_failed}（stored 保持 False）
  8. finally → `bus.emit("blackbox", pointer(record, stored, bytes_written=blob_bytes))`
  9. finally → `bus.close()`（幂等收束）
  - 帧泵说明（事实）：本函数无逐帧分发语句；step/text/tool/observation/ask/verdict/citation/notice 各帧由 graph.py 图节点在 ainvoke 期间经共享 bus 直接 emit（graph.py 73 处 bus.emit），本函数自身只 emit 第 5/7/8 条所列帧。
- 副作用：emit `"notice"`（type＝run_failed／blackbox_write_failed；另经 `_audit` 可出 audit_write_failed）与 `EVENT_BLACKBOX`（="blackbox"）；持久化写 `agent_v2_step`（put_steps）、`agent_v2_run`（finish_run 三态之一）、`agent_v2_blackbox`（put_blackbox）、`audit_log`（经 _audit* → RunAuditor → security.audit）；`bus.close()` 收束事件流。
- 返回：None（async，无返回值）。
- 规则条目：
  - R-I1b-18 ainvoke 异常 → run failed 落库＋审计 run_failed＋notice{run_failed} 出流（不静默）
  - R-I1b-19 三终态判定优先级 pending_ask ＞ error ＞ completed——互斥恰一支
  - R-I1b-20 写序：steps → 决定行/豁免行 → 收口行（写入序＝时序）
  - R-I1b-21 waiting_ask 支不写收口审计（closeout 仅 completed 支）
  - R-I1b-22 黑匣子无条件收口（finally）：distill＋best-effort 入库＋指针帧，任何支都执行
  - R-I1b-23 黑匣子写口失败 → notice{blackbox_write_failed}、stored=False——run 终态与已落状态零翻盘
  - R-I1b-24 指针 bytes＝json 序列化字符数（ensure_ascii=False）而非入库字节数
  - R-I1b-25 bus.close() 无条件执行（finally 尾）——事件流必有收束
  - R-I1b-26 run_error 仅 except 段赋值——error-final 支的黑匣子 error 面为空串
- 耦合：RunStore.put_steps/finish_run/put_blackbox；RunAuditor.run_failed（及经 _audit 族）；appv2.runtime.blackbox.distill/pointer；appv2.runtime.events.EVENT_BLACKBOX/EventBus.emit/close；json.dumps；RUN_WAITING_ASK/RUN_FAILED/RUN_COMPLETED。
- 疑点（只列不判，不静默）：
  - D-I1b-10 任务书归入本函数的"事件泵逐帧处置（step/text/tool/ask/notice/verdict/citation/blackbox/error）"在 e4b75f1 实现中不存在——本函数无帧分发；帧由图节点 emit（见上"帧泵说明"）。
  - D-I1b-11 error-final 支（第 3 条）不赋值 run_error → distill 的 error 面为空串（"error" 不在 blackbox._DISTILL_KEYS 白名单，无覆写路径）；同一失败在 agent_v2_run.error 列有值、黑匣子无——两处留痕不一致。
  - D-I1b-12 except 段（第 5 条）finish_run 无二次守卫——DB 写口持续异常时异常逃出 _drive；finally 仍执行黑匣子与 close，但任务异常无接收点（配合 D-I1b-09）。
  - D-I1b-13 events.py "八类闭世界"报错文案与 EVENT_KINDS 实际 9 常量（step/text/tool/observation/ask/verdict/citation/notice/blackbox）不符，且无 "error" 事件类——任务书帧表里的 error 面在本实现走 notice{type:run_failed}＋run 行 error 列（events.py 段外，记供对账）。

### `_audit`（executor.py L515-L533）｜审计写口守卫：异常转 notice、状态机零改动
- 消费：参数 bus；位置参 `method`（审计方法引用）；`**kwargs`（run_id/error/answer/who/approved/approval_id/term 等全透传）。
- 装配：不涉及。
- 调用：caller=本段 `_drive`（L442/L474）、`_audit_closeout`（L548/L556）、`_audit_decisions`（L579）、`_audit_ban_exempts`（L601）；另有段外 caller=`execute`（L191 run_created）。失败处理即本函数自身。
- 分支表（穷尽）：
  1. `await method(**kwargs)` 正常 → 静默返回（无出流）
  2. method 抛任意异常 → `bus.emit("notice", {type:"audit_write_failed", gates:[], content:"审计写口异常…：{exc}"})` → 调用方继续，run 状态机零改动
- 副作用：正常＝经 method→RunAuditor→security.audit 写 `audit_log`（本函数不直接写）；异常＝emit notice{audit_write_failed}。
- 返回：None。
- 规则条目：
  - R-I1b-27 审计异常一律转 notice 出流（留痕缺口可见）→ run 状态机零改动（不翻盘）
  - R-I1b-28 位置参 method＋kwargs 全量透传（不筛选、不改名）
- 耦合：appv2.runtime.events.EventBus.emit；typing.Callable/Awaitable。
- 疑点（只列不判，不静默）：
  - D-I1b-14 异常文本 `{exc}` 随 notice 进入 run 事件流（消费方可见）——审计/DB 异常细节外泄面，无脱敏层。
  - D-I1b-15 守卫只包 method 调用；若 bus 已 close，则 notice emit 自身 RuntimeError（events.py L73）逃出 _audit——当前时序（close 仅在 _drive finally 尾）下不可达，属隐式时序依赖。

### `_audit_closeout`（executor.py L535-L563）｜completed 段收口审计分型：refused 与 run_completed 互斥恰一行
- 消费：参数 bus/run_id/final/answer/who；self._auditor；final.notices、final.manifest_digest。
- 装配：不涉及。
- 调用：caller=`_drive`（L468，completed 支唯一调用点）；写经 `_audit` 守卫。
- 分支表（穷尽）：
  1. notices 中 type=="refused" 存在 → 取最后一条（refused[-1]）的 content 作 reason → `auditor.refused(run_id, reason, who)` → return（不发 run_completed）
  2. 无 refused → `auditor.run_completed(run_id, answer, manifest_digest=str(final.get("manifest_digest") or ""), who)`
- 副作用：emit 无直接；持久化写 `audit_log` 恰一行（action＝agent_v2.refused 或 agent_v2.run_completed，经 _audit）。
- 返回：None。
- 规则条目：
  - R-I1b-29 拒答与正常收口互斥恰一行——completed 支唯一收口审计
  - R-I1b-30 refused 取 final.notices 全量过滤后末条的 content 作 reason（无 base 切片）
  - R-I1b-31 refused 行不携 answer/manifest_digest，正常行不携 reason——字段面不对称
- 耦合：appv2.runtime.audit.RunAuditor.refused/run_completed；RunState.notices/manifest_digest。
- 疑点（只列不判，不静默）：
  - D-I1b-16 refused 扫描无 base 切片（与 _audit_decisions/_audit_ban_exempts 的增量切片纪律相反）——恢复段收口时，历史累计 notices 中的 refused 帧会决定本段分型；"恰一行"依赖本段调用次数而非切片去重（恢复段该形态可达性未验证）。
  - D-I1b-17 多帧 refused 只取末条——前条在审计面静默消失（notices 帧仍留 final/黑匣子）。

### `_audit_decisions`（executor.py L565-L586）｜本段新增 resume 决定审计（外表审批批准/驳回）
- 消费：参数 bus/run_id/final/who/base；self._auditor；final.resume_choices（dict 过滤后列表）。
- 装配：不涉及。
- 调用：caller=`_drive` 三支（L433 waiting_ask/L445 failed/L461 completed）；写经 `_audit` 守卫。
- 分支表（穷尽）：
  1. 逐条 `choices[max(base, 0):]`（外层循环；base 下界钳 0）
  2. `record.kind != ASK_EXTERNAL_TABLE_APPROVAL`（值 "external_table_approval"）→ continue（clarify 等非审批决定零溢行）
  3. kind 匹配 → `approved=(record.get("value") == "批准")` → `auditor.extable_decided(run_id, approved, approval_id=str(record.get("approval_id") or ""), who)`（每条一行）
- 副作用：emit 无直接；持久化写 `audit_log`（action＝agent_v2.extable_approved／extable_rejected，由 auditor 按 approved 选分支）。
- 返回：None。
- 规则条目：
  - R-I1b-32 只审本段增量（切片 base 起）——挂起前已落账行不重放
  - R-I1b-33 非外表审批决定（clarify 等）零溢行（四事件闭世界）
  - R-I1b-34 approved 判据＝value 字面量"批准"精确等值
  - R-I1b-35 approval_id 缺失 → 空串（auditor 侧再兜底展示"（未携）"）
- 耦合：appv2.tools.ASK_EXTERNAL_TABLE_APPROVAL；RunAuditor.extable_decided；RunState.resume_choices；execute L235 的 resume_choice_base（切片起点，段外）。
- 疑点（只列不判，不静默）：
  - D-I1b-18 "批准"字面量多处硬编码（本文件 L583、appv2/runtime/graph.py:1939、audit.py:144、tools/handlers.py:631、tools/precondition.py:388）——无共享常量，跨文件一致性无机器闸。
  - D-I1b-19 遍历依赖 final.resume_choices 的 dict 形态与追加序（切片按位置，非身份键）。

### `_audit_ban_exempts`（executor.py L588-L607）｜本段 N1 豁免放行审计（三终态全覆盖）
- 消费：参数 bus/run_id/final/who/base；self._auditor；final.notices（dict 过滤后列表）。
- 装配：不涉及。
- 调用：caller=`_drive` 三支（L436 waiting_ask/L448 failed/L465 completed）——waiting_ask/failed/completed 全覆盖；写经 `_audit` 守卫。
- 分支表（穷尽）：
  1. 逐条 `notices[max(base, 0):]`（外层循环；base 下界钳 0）
  2. `notice.type != "ban_exempt"` → continue
  3. 匹配 → `auditor.ban_exempt(run_id, term=str(notice.get("term") or ""), who)`（每条一行）
- 副作用：emit 无直接；持久化写 `audit_log`（action＝agent_v2.ban_exempt，meta 携 term）。
- 返回：None。
- 规则条目：
  - R-I1b-36 豁免必留痕：三终态支均调本函数（挂起/失败/收口不漏）
  - R-I1b-37 切片 base 只补本段增量——防累计 notices 重放重复行
  - R-I1b-38 term 取 notice.term，缺失空串兜底
- 耦合：appv2.runtime.audit.RunAuditor.ban_exempt；RunState.notices；appv2/runtime/graph.py L1525-1536（ban_exempt 帧生产侧，段外）；execute L238-242 ban_exempt_base 计数（段外）。
- 疑点（只列不判，不静默）：
  - D-I1b-20 字面量 "ban_exempt" 本文件双写（execute L241 计数与本函数 L599 过滤）——同一字符串两处硬编码，无共享常量。
  - D-I1b-21 增量切片按位置（notices[base:]）——前提 notices 只追加不重排；写入序为图侧外部前提，本文件无校验。
  - D-I1b-22 切片非身份去重——同 term 二次命中会再写一审计行（图侧是否重发本文件不判）。

### `AgentRuntime`（executor.py L610-L638，class）｜命令入口门面（modules.md runtime 卡公开接口——api 只见此层）
- 类事实：`__init__`（L613-L614）只存 `self._executor`；类体无状态、无校验逻辑、无事件面；三公开方法均薄透传。
- 装配：不涉及。
- 调用：caller＝api 层（本文件内无调用点）。
- 分支表（穷尽）：不适用（类级别；各方法分支见下）。
- 副作用：emit 无；持久化写 无（类自身——实际写入经 executor）。
- 返回：不适用（类级别）。
- 规则条目：
  - R-I1b-39 门面纪律：三方法零状态零捕获——命令构造＋执行器调用＋返回值透传（kind 闭世界由 RunCommand.__post_init__ 把关）
- 耦合：RunCommand/COMMAND_ASK/COMMAND_RESUME（同文件段外）；GraphRunExecutor。
- 疑点（只列不判，不静默）：无。

### `AgentRuntime.__init__`（executor.py L613-L614）｜执行器引用持有
- 消费：参数 executor。
- 装配：不涉及。
- 调用：caller＝组合根装配（本文件内无）；无失败路径。
- 分支表（穷尽）：无分支。
- 副作用：emit 无；持久化写 无。
- 返回：None。
- 规则条目：
  - R-I1b-40 单一引用持有——无校验、无缺省（executor 必填）
- 耦合：GraphRunExecutor。
- 疑点（只列不判，不静默）：无。

### `AgentRuntime.ask`（executor.py L616-L628）｜提问受理透传
- 消费：参数 q（AskRequest：question/actor/followup_of）；self._executor。
- 装配：不涉及。
- 调用：`executor.execute(RunCommand(kind=COMMAND_ASK, question=q.question, actor=q.actor, followup_of=q.followup_of))`；`_seed_messages` 的 RunNotFoundError/RunNotSuspendedError 不捕获，透传 api（追问前轮校验失败面）。
- 分支表（穷尽）：无分支（单路径构造＋单调用）。
- 副作用：emit 无；持久化写 无（本方法自身——execute 链路另计）。
- 返回：`RunHandle(run_id, stream)`。
- 规则条目：
  - R-I1b-41 三字段原样映射 RunCommand（question/actor/followup_of）——不做存在性/格式校验
- 耦合：appv2.runtime.state.AskRequest/RunHandle；RunCommand/COMMAND_ASK（同文件段外）；GraphRunExecutor.execute。
- 疑点（只列不判，不静默）：
  - D-I1b-23 question 空串/超长无本层校验——校验口径在 api 层或他处（本文件未见）。

### `AgentRuntime.resume`（executor.py L630-L634）｜挂起恢复透传
- 消费：参数 run_id/choice（AskChoice）；self._executor。
- 装配：不涉及。
- 调用：`executor.execute(RunCommand(kind=COMMAND_RESUME, run_id=run_id, choice=choice))`；RunNotFoundError/RunNotSuspendedError 不捕获，透传 api。
- 分支表（穷尽）：无分支。
- 副作用：emit 无；持久化写 无（本方法自身——execute 内 mark_running/图恢复另计）。
- 返回：`RunHandle(run_id, stream)`。
- 规则条目：
  - R-I1b-42 resume 不携 who/actor——身份在 execute 内取 run 行 actor（L256，段外）
- 耦合：appv2.runtime.state.AskChoice/RunHandle；RunCommand/COMMAND_RESUME（同文件段外）；GraphRunExecutor.execute。
- 疑点（只列不判，不静默）：
  - D-I1b-24 resume 与 ask 的身份来源不同口（run 行 actor vs 命令 actor）——本层不校验两者一致性。

### `AgentRuntime.pending_ask`（executor.py L636-L638）｜挂起帧只读透传
- 消费：参数 run_id；self._executor。
- 装配：不涉及。
- 调用：`executor.pending_ask_of(run_id)`；无捕获（读态异常上抛）。
- 分支表（穷尽）：无分支。
- 副作用：emit 无；持久化写 无（只读零写）。
- 返回：`dict[str, Any] | None`。
- 规则条目：
  - R-I1b-43 只读透传——零写面、零校验
- 耦合：appv2.runtime.state（dict 形态）；GraphRunExecutor.pending_ask_of。
- 疑点（只列不判，不静默）：
  - D-I1b-25 run 不存在与"非挂起/无帧"同返 None——api 层无法由本面区分 404 与空帧（是否另查 run 行不在本文件）。

---

## 覆盖自检
- def/class 清单差集：无——本段 15 符号（4 个 `_audit*` 含 `_audit` 共 4、其余 6 方法、`AgentRuntime` 类＋4 方法）逐条覆盖；L513-514 为分节注释、L608-609 为类前空行，无遗漏符号。
- 本段 emit 事件名全集：
  - 字面量 `"notice"`——三种 type：`run_failed`（_drive except 支）、`blackbox_write_failed`（_drive finally 支）、`audit_write_failed`（_audit 守卫）
  - `EVENT_BLACKBOX`（appv2/runtime/events.py L31，值 `"blackbox"`，_drive finally 支）
  - 本段无其它 emit；任务书列举的 step/text/tool/ask/verdict/citation 与 observation 帧不由本段发射（graph.py 73 处 bus.emit 生产）；events.py EVENT_KINDS 九常量，无 "error" 事件类（error 面走 notice{run_failed}＋run 行 error 列）。
- 引用的外部符号全集（executor.py 内定义的除外）：
  - appv2.runtime.events：`EventBus`（.emit/.close）、`EVENT_BLACKBOX`
  - appv2.runtime.graph：`build_graph`、`LoopDeps`
  - appv2.runtime.llm：`GatewayChatModel`（.model_copy）
  - appv2.runtime.state：`RunState`、`RUN_RUNNING`、`RUN_WAITING_ASK`、`RUN_COMPLETED`、`RUN_FAILED`、`AskChoice`、`AskRequest`、`RunHandle`
  - appv2.runtime.context：`SYSTEM_PROMPT`
  - appv2.runtime.budget：`now_monotonic`（＋ self._budget 的 `Budget.as_dict`/`Budget.total_seconds`）
  - appv2.runtime.blackbox：`distill`、`pointer`
  - appv2.runtime.store：`RunStore`（.get_run/.put_steps/.finish_run/.put_blackbox）
  - appv2.runtime.audit：`RunAuditor`（.run_failed/.refused/.run_completed/.extable_decided/.ban_exempt）
  - appv2.tools：`ASK_EXTERNAL_TABLE_APPROVAL`（值 "external_table_approval"）
  - 标准库：`asyncio.create_task`/`asyncio.Task`、`json.dumps`、typing 的 `Any`/`Callable`/`Awaitable`
  - 同文件段外引用（不计入外部，列备对账）：`RunCommand`/`COMMAND_ASK`/`COMMAND_RESUME`、`new_run_id`、`RunNotFoundError`、`RunNotSuspendedError`、`extract_dialogue_from_legacy_history`、`who_of`（引用点 L181 段外）
- 条目计数：15 条目；R-I1b-01 至 R-I1b-43（43 条）；D-I1b-01 至 D-I1b-25（25 条）。
