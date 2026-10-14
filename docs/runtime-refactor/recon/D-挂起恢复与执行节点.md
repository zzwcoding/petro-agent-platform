# D·现状调研报告

- 锚定：commit e4b75f1（行号以此为准）
- 覆盖：appv2/runtime/graph.py L1889-L2283
- def/class 清单：逐一全列（含行号区间），不得省略
  - `_handle_choice`（async def，L1892-L2020）
  - `_apply_result`（def，L2026-L2139）
  - `_invoke_tool`（async def，L2142-L2152）
  - `_make_discover`（def，L2155-L2229）
  - `discover_node`（async def，L2158-L2227，嵌套于 `_make_discover`）
  - `_make_execute`（def，L2232-L2281）
  - `execute_node`（async def，L2235-L2279，嵌套于 `_make_execute`）
  - 无 class；另有两个分节注释（L1889-L1890「挂起恢复（clarify 回喂／外表审批——接线①③）」、L2023-L2024「节点三/四：discover／execute」），非 def。
- 本段定位（行号锚点，不抄正文）：`_handle_choice` 是挂起帧恢复的唯一收敛点，legacy 由 `decision_node` 调（L1681，不传 four_phase）、四相位由 `clarify_node` 调（L2326，four_phase=True）；`_apply_result` 是「工具结果→状态更新与路由」的单点（ReAct 语义：bad_args 拒因回喂重决策、无 repair），由 discover/execute 两节点共用；`_invoke_tool` 是工具调用统一出口＋单工具超时闸；`_make_discover`/`_make_execute` 造图节点（L4063-L4064 装配），节点入口只做预算闸与载荷取出，执行结果一律交 `_apply_result`。

---

### `_handle_choice`（L1892-L2020）｜挂起恢复单点：读回 interrupt 的用户选择，按帧 kind 走澄清回收或外表审批回收两条路
- 消费：`state.pending_ask`（挂起帧）、`state.run_id`、`state.resume_choices`、`state.messages`、`state.process_notes`、`state.steps`、`state.approved_ids`、`state.extable_rounds`、`state.last_execute`；`deps.bus`（事件出口）； `four_phase` 为调用方参数（非状态字段）
- 装配：`messages` 链尾追加 `{"role": "user", "content": value}`（用户原话；一次性，两条路径各一条——澄清路在 L1923，审批路在 L2002；注释记「对话纯度红线：去系统前缀」）
- 调用：caller=`decision_node`（L1681，legacy，four_phase 缺省 False）／`clarify_node`（L2326，four_phase=True）；恢复载荷来自 `langgraph.types.interrupt`（L1896）；无 LLM 调用。失败处理：`payload` 非 dict 时包成 `{"value": str(payload)}`（L1899）；`value` 缺省空串。
- 分支表·澄清回收路径（`frame.get("kind") == ASK_CLARIFY`，L1912-L1937）：
  1. 任意 `value`（含空串，无判空/无枚举）→ 写 `user_hint=value`、`rounds=0`、`budget_reject_streak=0`，`messages` 追加用户原话，`process_notes` 追加 `_note("clarify", "澄清回收", value)`，emit step `{step: decision, seq: _next_seq(state), title: "澄清回收：{value}"}`，`steps` 追加同题记录（payload=`{"resume": resume_record}`）→ **提前 return**（审批侧追加一律不发生），去向 `next_intent=decision`（四相位装配下该值经 build_graph 重写路由到 clarify 节点；legacy 路由到 decision 节点）
  2. `consecutive_asks` 在本路**不重置**（state.py L214-L216 注明「run 生命期累计不清零」）；`rounds` 清零依据注释（L1914-L1916）：用户输入＝新周期，轮预算按「每用户输入周期 3 轮」计
- 分支表·审批回收路径（`frame.kind != ASK_CLARIFY`，L1938-L2020）：
  1. `value == "批准"` → emit notice `approval_recorded`（`gates: []`，内容「审批单号 {approval_id} 已留痕（resume 留痕，可回溯）。」）＋`notices` 追加（L1939-L1946，三条批准子分支共用）
     - 1a. 且 `four_phase=True` → `approved_ids` 追加 `[str(approval_id or ""), *帧 detail.tables 里 strip 非空的表名]`，`extable_rounds+1` → `next_intent=precondition`（回前置条件机重判放行，不重排计划、不走 last_execute 重投通道；注释 L1948-L1953）
     - 1b. 且 `four_phase=False` 且 `state.extable_rounds >= 1`（legacy cap 1 已达）→ emit notice `approval_gate_pending`＋`notices` 追加，`_direct_answer` 写 draft/draft_kind=direct 并置 `next_intent=answer`（文案「外表引用审批已通过（单号 {approval_id}）；权威引擎侧闸未放行续跑，如实收口不冒充。」L1978-L1982）→ 去向 answer
     - 1c. 且 `four_phase=False` 且 `state.extable_rounds < 1` → `approved_ids` 追加单号，`extable_rounds+1`；从 `state.last_execute` 取 `plan`/`retrieval_need` 原样写 `pending_plan`/`pending_retrieval`（L1989-L1992「末次主执行载荷原样重投」）
       - 1c-i. `plan` 与 `retrieval_need` 皆 None → `next_intent=decision`（无载荷可重投＝回决策，L1993-L1994）
       - 1c-ii. 否则 → `next_intent=execute`（重投主执行）
  2. `value != "批准"`（含「驳回」及任意其他文本）→ `impact=str((帧 detail or {}).get("impact", ""))`（常量 `_EXTABLE_REJECT_BASIS_KEY="impact"`，L315；引擎卡 impact 原文零二次创作）→ `_direct_answer` 直答「外表引用审批驳回：{impact}」→ 去向 answer；**本支不发 notice**（L1997-L1999）
  3. 审批路径共同尾（L2000-L2019，含驳回）：`messages` 追加用户原文；`process_notes` 追加 `_note("approval", "审批回收", "外表引用审批 {value}" + ("（审批单号 {approval_id}）" if approval_id else ""))`；emit step `{step: decision, seq, title: "审批回收：{value}"}`；`steps` 追加同题记录（payload=`{"resume": resume_record}`）
  4. 入口共同簿记（L1902-L1911）：`resume_record={"kind": 帧kind, "value", "approval_id"}` 追加 `resume_choices`；`pending_ask=None`；`next_intent=decision`（初值，后被审批各支覆写）
- 副作用：emit `step`（澄清路与审批路各一次，`step=decision`）；emit `notice`（`approval_recorded`／`approval_gate_pending`）；持久化写：无（只写 state updates，落库经 checkpointer 在调用方）
- 返回：updates 键——澄清路：`pending_ask / resume_choices / next_intent / user_hint / rounds / budget_reject_streak / messages / process_notes / steps`；审批路：`pending_ask / resume_choices / next_intent / notices / approved_ids / extable_rounds / pending_plan / pending_retrieval`（1c）或 `draft / draft_kind`（1b、2 经 `_direct_answer`）／`messages / process_notes / steps`
- 规则条目：
  - R-D-01 恢复入口：`pending_ask` 非空即 interrupt 挂起帧；恢复载荷 value/approval_id 记入 `resume_choices`（kind/value/approval_id 三键），`pending_ask` 清空，`next_intent` 初值 decision（后被分支覆写）。
  - R-D-02 澄清回收：用户选择即 `user_hint`（决策下轮消费后清空），`rounds` 与 `budget_reject_streak` 同周期清零（挂起等人工不计轮预算），原话追加 `messages` 与过程档案「澄清回收」，decision 步「澄清回收：{value}」入 `steps`（payload.resume 留痕），提前 return 不进审批簿记。
  - R-D-03 四相位批准：放行名单＝审批单号＋帧 detail.tables 非空表名，一并追加 `approved_ids`（ToolContext 随行），`extable_rounds+1`，`next_intent=precondition`——回前置条件机重判（放行后 pass/note），不重排计划。
  - R-D-04 legacy 批准已重跑过一轮（`extable_rounds>=1`）：不再重投，notice「引擎侧闸未放行续跑」＋如实直答收口（不冒充）。
  - R-D-05 legacy 首轮批准：单号入 `approved_ids`，`extable_rounds+1`，`last_execute` 载荷原样重投；两载荷皆空则回决策，否则回执行（审批前 ask 帧侧未执行工具，批准后才真正调用）。
  - R-D-06 驳回（value≠「批准」）：驳回依据＝帧 detail.impact 原文，直答「外表引用审批驳回：{impact}」，拒因不由 runtime 改写。
  - R-D-07 审批路径共同簿记：批准/驳回原文入 `messages`、过程档案「审批回收（单号…）」、decision 步「审批回收：{value}」入 `steps`；与澄清路的簿记互斥（澄清路提前 return）。
- 耦合：`appv2.runtime.state.ASK_CLARIFY` 语义常量（经 `appv2.tools` 导出，L136-L137 导入）、`STEP_DECISION`、`INTENT_DECISION/INTENT_PRECONDITION/INTENT_EXECUTE/INTENT_ANSWER`；本文件辅助：`_note`(L1227)、`_notes_with`(L1232)、`_step_record`(L1051)、`_next_seq`(L1068)、`_direct_answer`(L1203)、`_EXTABLE_REJECT_BASIS_KEY`(L315)；外部：`langgraph.types.interrupt`(L64)、`deps.bus.emit`(EventBus)。
- 疑点：
  - D-D-01 批准判定是 `value == "批准"` 字面精确匹配：其余任何值（含「驳回」、近似文本、空串）全部落驳回路径——value 的归一化/校验是否在本段之外（executor resume 侧）未核。
  - D-D-02 四相位批准在 `approval_id` 为空时仍向 `approved_ids` 追加空串 `""`（L1962 `str(approval_id or "")`）。
  - D-D-03 恢复时不校验用户回传 `approval_id` 与帧内 `detail.approval_id` 是否一致（留痕直接用用户回传值）。
  - D-D-04 四相位放行名单只取帧 `detail.tables`；帧无 tables 时仅单号（或空串）入 `approved_ids`，表放行面为空。
  - D-D-05 legacy「无载荷可重投」与「`last_execute` 缺失（None）」同落 1c-i 分支，且该分支无 notice（静默回决策）。
  - D-D-06 驳回路径不发 notice：审批事件面批准侧有所谓「留痕」notice、驳回侧只有 draft 直答，机读面无驳回收据。
  - D-D-07 `four_phase` 语义由调用方参数决定而非帧/state 字段：同一挂起帧若装配参数与挂起时不同，会走另一条分支（装配一致性依赖调用面）。

### `_apply_result`（L2026-L2139）｜工具结果→状态更新与路由的单点（ok/ask/bad_args/retryable/refused 五形态穷尽）
- 消费：`state.steps`、`state.process_notes`、`state.tool_retries`、`state.notices`、`state.run_id`；形参 `result`（ToolResult dict）、`seq`、`kind`、`tool_name`、`args`、`record_payload`、`retry_state` 由调用方给
- 调用：caller=`discover_node`（kind=STEP_DISCOVER）／`execute_node`（kind=STEP_EXECUTE）；无 LLM 调用；`result["status"]` 直接下标取（无缺省保护）；失败分型读 `result["error"]["category"]`／`["message"]`。
- 分支表（穷尽）：
  1. 任意 status → emit `tool`（`{tool, status, seq, message}`，message 仅 `STATUS_FAILED` 时携 `error.message`，否则 None）＋emit `step`（title=`"{tool_name}：{status}"`）＋`steps` 追加 `_step_record(seq, kind, title, None, payload=record_payload)`＋`process_notes` 追加 `_tool_note(tool_name, args, result)`（执行台账全形态入档：ok＝N 行／ask＝0 行挂起／failed 三分类分型措辞，L2060-L2069）
  2. `status == STATUS_OK` → `last_result=result`、`next_intent=INTENT_OBSERVE`（观察回流）
  3. `status == STATUS_ASK` → `frame=result["ask"]`；`frame.kind == ASK_EXTERNAL_TABLE_APPROVAL` 且 `detail.approval_id`（引擎种子）非空 → `detail["approval_id"]=reseed_approval_id(state.run_id, engine_seed)`（=`"{run_id}#{engine_seed}"`，L1332-L1334）并回写 `frame["detail"]`；`pending_ask=frame`、`next_intent=INTENT_DECISION`（挂起：interrupt 在 decision/clarify 入口）；emit `ask`（`{frame, run_id}`）
     - 3a. kind 非外表审批 或 approval_id 为空 → 帧原样挂起（不重种子）
  4. `error.category == CATEGORY_BAD_ARGS` → `reason=message 或 "校验未过"`；notice `decision_rejected`（内容「工具校验拒因回喂重决策：{reason}」）＋`notices` 追加；`decision_error=reason`；`pending_plan=None`、`pending_retrieval=None`、`pending_discovers=[]`；`next_intent=INTENT_DECISION`（拍板②：取消自动 repair，拒因回喂 LLM 由它重决策、轮预算照耗）
  5. `error.category == CATEGORY_RETRYABLE` 且 `state.tool_retries[tool_name] < 1` → `updates.update(retry_state)`（调用方给的重投载荷更新）、`tool_retries[tool_name]+1`；`next_intent = INTENT_DISCOVER if kind == STEP_DISCOVER else INTENT_EXECUTE`（同参重试一次，按工具名各自计数——P-024b C2）
  6. `error.category == CATEGORY_RETRYABLE` 且已重试 ≥1（耗尽）→ notice `tool_unavailable`（「工具 {tool_name} 重试后仍不可用——如实收敛。（{message}）」）＋`notices`；清 `pending_plan/pending_retrieval/pending_discovers`；`_direct_answer("（工具重试后仍不可用——如实收敛，不编造。）")` → 去向 answer
  7. else（注释标 refused 闸拒，含 `CATEGORY_REFUSED` 及任何未列 category）→ `reason=message 或 "口径/数据闸拒"`；notice `refused`（「口径/数据闸拒——拒因如实转答：{reason}」）＋`notices`；清三载荷；`_direct_answer(reason)`（拒因原样如实转答，不重试不改写）→ 去向 answer
- 副作用：emit `tool`、emit `step`、emit `ask`（仅 3）、emit `notice`（4/6/7）；step 类型由 kind 参数定（discover/execute）；notice 类型 `decision_rejected`／`tool_unavailable`／`refused`；持久化写：无
- 返回：updates 键——恒有 `steps / process_notes`；按支追加 `last_result / next_intent`（2）、`pending_ask`（3）、`decision_error / notices / pending_plan / pending_retrieval / pending_discovers`（4/6/7）、`tool_retries`（5）、`draft / draft_kind`（6/7 经 `_direct_answer`）
- 规则条目：
  - R-D-08 每次工具执行（含被拒/挂起）都留两份痕：step 记录（payload=调用方 record_payload）＋过程档案 `_tool_note`（参数 JSON 键序归一 → 结果行数或分型拒因）。
  - R-D-09 ok：结果存 `last_result`，回 observe（观察回流后续投）。
  - R-D-10 ask：帧挂 `pending_ask` 并回 decision 入口挂起；外表审批单号重种子为「run 前缀#引擎种子」（引擎种子保留可溯；接线③），事件流发 ask 帧后正常收束。
  - R-D-11 bad_args：拒因写 `decision_error` 回喂 LLM 重决策，三载荷清空（无自动 repair）。
  - R-D-12 retryable 首拒：按工具名计数各得一次同参重试，重投载荷由调用方 retry_state 给，路由回本节点（discover→discover、execute→execute）。
  - R-D-13 retryable 耗尽：notice 明示＋如实收敛直答（清三载荷）。
  - R-D-14 其余（refused）：notice `refused`＋拒因原样直答（清三载荷）。
- 耦合：`STATUS_OK/STATUS_FAILED/STATUS_ASK`、`CATEGORY_BAD_ARGS/CATEGORY_RETRYABLE`（`appv2.tools`，L135-L172 导入）、`ASK_EXTERNAL_TABLE_APPROVAL`、`INTENT_OBSERVE/DECISION`、`STEP_DISCOVER/STEP_EXECUTE`；本文件：`_step_record`、`_notes_with`、`_tool_note`(L1237)、`_direct_answer`、`reseed_approval_id`(L1332)、`deps.bus.emit`。
- 疑点：
  - D-D-08 else 分支兜住一切未列 category：未知/未来分型会被统一写成「闸拒」notice（`CATEGORY_REFUSED` 本段未显式引用，靠兜底命中）。
  - D-D-09 notice 的 `gates` 恒为空列表（五处 notice 构造均 `"gates": []`）——门名信息只走文案。

### `_invoke_tool`（L2142-L2152）｜工具调用统一出口＋单工具超时闸
- 消费：`state.budget["tool_timeout_seconds"]`（缺省 30.0，float 化）；经 `_ctx_of(state)` 读 `state.actor`、`state.metric_candidates`、`state.approved_ids`（放行态随 ToolContext 走，不进 args）
- 调用：caller=`discover_node`(L2167)、`execute_node`(L2250)、四相位 batch 节点(L3297)；工具只经 `deps.registry.call(tool_name, args, ctx)` 单出口；`asyncio.wait_for` 包超时；`TimeoutError` → 返回 `None`（调用方按 `_timeout_result` 转 retryable 超时结果，同参重试一次）
- 分支表：
  1. 超时 → 返回 None → 调用方生成 `_timeout_result`（status=failed、category=retryable、message「工具 {tool_name} 超 {timeout:g}s 未返回（单工具超时闸）」）
  2. 未超时 → 返回 registry.call 原值（ToolResult 等）
- 副作用：无（emit/step/notice 全在调用方）
- 返回：`Any`（工具原返回值）或 `None`（超时）
- 规则条目：
  - R-D-15 一切工具调用（discover/execute/四相位 batch）都经 `_invoke_tool`：wait_for 超时即转 retryable 通道（三闸之三），工具侧无例外出口。
- 耦合：`appv2.tools.ToolRegistry.call`（经 deps.registry）、本文件 `_ctx_of`(L1135)、`_timeout_result`(L1150) 由调用方引用。
- 疑点：
  - D-D-10 超时与工具真实返回 None 不可区分（返回值即 None 一律被调用方当超时）——registry 契约是否可能返回 None 未核。

### `_make_discover`（L2155-L2229）｜造 discover 节点闭包：逐次执行队首发现工具，记 tap/空手/预算
- 消费：`state.pending_discovers`（队列）、`state.discover_used`、`state.empty_probes`、`state.budget`（超时值）；写：`pending_discovers`、`discover_used`、`empty_probes`＋`_apply_result` 的全部键
- 调用：caller=图装配 `build_graph`（L4063，`_node_of(_make_discover(deps))`）；运行时入口由路由 `_route` 按 `next_intent` 选中；工具经 `_invoke_tool`→`deps.registry.call`；失败分型全文交 `_apply_result`
- 分支表（discover_node，穷尽）：
  1. `_gate_or_none(state, deps)` 非 None（时长闸触界等）→ 直接返回收敛更新（不执行工具）——挂起恢复后重入同样先过此闸
  2. `pending_discovers` 空 → `{"next_intent": INTENT_DECISION}`（恢复段边界兜底）
  3. 队首 `call` 执行：`tool_name=str(call.get("tool",""))`、`args=dict(call.get("args") or {})`；`raw is None` → `_timeout_result`，否则 `_result_dict(raw)`
  4. 无论结果：`discover_used+1`（全 run 计数），tap 记入步 payload——`{index: discover_used, tool, query: _payload_fingerprint(args), hits: len(全部观察）, shape: "no_hit"|"rows:{n}"|"empty"}`（no_hit 判据＝观察 locator.notice_type=="no_hit"；V2-34 任务 5/R5 跑批分析面）
  5. `status==failed` 或（`status==ok` 且本次新增非 notice 观察数 0）→ `empty_probes` 追加 `_discover_fingerprint(tool_name, args)`（V2-56 空手指纹；命中不记——允许同参复查）
  6. `status==ok` → `pending_discovers=queue[1:]`（本支已消费；观察回流后续投）
  7. 其他 status → 队列处置全由 `_apply_result` 定：bad_args/refused/retryable 耗尽＝清空；retryable 首拒＝`retry_state` 回填 `[call, *queue[1:]]`（＝原队列，队首不消费、同参重投）
- 副作用：step 记录经 `_apply_result`（kind=discover，payload 含 discover_tap）＋emit `tool`/`step`/可能的 `notice`/`ask`；持久化写：无
- 返回：updates 键——`pending_discovers / discover_used / empty_probes`＋`_apply_result` 键（`steps / process_notes / next_intent / last_result / pending_ask / notices / decision_error / pending_plan / pending_retrieval / draft / draft_kind / tool_retries` 视支）；闸触界支＝收敛更新或空队列支＝`{"next_intent": INTENT_DECISION}`
- 规则条目：
  - R-D-16 discover 入口：预算闸先于一切；队列空＝回决策（恢复段边界兜底，不空转）。
  - R-D-17 每次 discover 调用都计入 `discover_used` 并记 tap（次数/查询词指纹/命中数/命中形态）——no_hit 循环回归的判定面。
  - R-D-18 空手判定（V2-56）：failed，或 ok 且新增非 notice 观察为 0 → 记空手指纹到 `empty_probes`（同参拒重发键）；有料即非空手不记。
  - R-D-19 ok 才出队（`queue[1:]`）；结果路由（observe/decision/answer）由 `_apply_result` 统一裁决。
- 耦合：`INTENT_DECISION`、`STEP_DISCOVER`;本文件：`_gate_or_none`(L1092)、`_invoke_tool`、`_timeout_result`、`_result_dict`(L1164)、`_apply_result`、`_next_seq`、`_observations_of`(L1131)、`_payload_fingerprint`(L537)、`_discover_fingerprint`(L544)、`_node_of`(L4038)；deps：`registry`、`bus`。
- 疑点：
  - D-D-11 tap.hits 计全部观察（含 notice 形态），空手判据却按「非 notice 观察为 0」过滤——同一结果两套口径并存（跑批分析字段与拒重发判据不同源）。

### `_make_execute`（L2232-L2281）｜造 execute 节点闭包：主执行载荷（plan/retrieval）二选一投递，ok/ask 才消费
- 消费：`state.pending_plan`、`state.pending_retrieval`、`state.executed_payloads`、`state.budget`；写：`pending_plan`/`pending_retrieval`（消费）、`last_execute`、`executed_payloads`＋`_apply_result` 的全部键
- 调用：caller=图装配 `build_graph`（L4064）；工具经 `_invoke_tool`→`deps.registry.call`；失败分型全文交 `_apply_result`（`retry_state={}`——自环重投靠载荷仍在位，L2265 注释）
- 分支表（execute_node，穷尽）：
  1. `_gate_or_none(state, deps)` 非 None → 返回收敛更新（不执行）
  2. `pending_plan is not None` → `tool_name=DATA_QUERY`，`args={"plan_draft": plan 副本}`，`executed={"plan": plan 副本}`，`consume={"pending_plan": None}`
  3. 否则 `pending_retrieval is not None` → `tool_name=DOC_RETRIEVE`，`args=retrieval_need 副本`，`executed={"retrieval_need": …}`，`consume={"pending_retrieval": None}`（data 优先于 knowledge，二选一）
  4. 两者皆 None → `{"next_intent": INTENT_DECISION}`（恢复段边界兜底）
  5. 调用结果：`raw is None`（超时）→ retryable 超时结果；否则 `_result_dict`
  6. `status in (ok, ask)` → `updates.update(consume)`（清对应载荷）＋`last_execute=executed`（审批批准后重投的源）＋`executed_payloads` 追加 `_emission_fingerprints(plan, retrieval_need)`（V2-37 同参重投机器闸簿记：ok/ask 才算「已执行」；bad_args 拒＝引擎未执行，不记——修正后重发不被误拦）
  7. `status` 其他（failed 各分型）→ 不消费载荷（载荷原位＝retryable 自环同参重投的隐式依赖）；bad_args/refused/retryable 耗尽的路由与清载荷由 `_apply_result` 定
- 副作用：step 记录经 `_apply_result`（kind=execute，payload=`{"tool","status", plan|retrieval_need}`）＋emit `tool`/`step`/可能的 `notice`/`ask`；持久化写：无
- 返回：updates 键——`pending_plan / pending_retrieval / last_execute / executed_payloads`＋`_apply_result` 键（见上）；闸触界/空载荷支＝收敛更新或 `{"next_intent": INTENT_DECISION}`
- 规则条目：
  - R-D-20 主执行载荷优先序：先 `pending_plan`→`data_query`（args.plan_draft），后 `pending_retrieval`→`doc_retrieve`（args=检索载荷）；单节点一次只投一支。
  - R-D-21 双载荷皆空＝回决策（恢复段边界兜底）。
  - R-D-22 ok/ask 才消费载荷并记 `last_execute`＋按支发射指纹入 `executed_payloads`（ok＝本支已消费；ask＝载荷留 `last_execute` 供审批批准后重投）。
  - R-D-23 非 ok/ask 不消费载荷：retryable 首拒自环时 execute 节点重入仍见载荷（同参重试）；bad_args/refused/耗尽则由 `_apply_result` 清载荷并改道 decision/answer。
- 耦合：`DATA_QUERY`、`DOC_RETRIEVE`、`STATUS_OK`、`STATUS_ASK`（`appv2.tools`）；`INTENT_DECISION/INTENT_EXECUTE`、`STEP_EXECUTE`；本文件：`_gate_or_none`、`_invoke_tool`、`_timeout_result`、`_result_dict`、`_apply_result`、`_next_seq`、`_emission_fingerprints`(L550)、`_node_of`。
- 疑点：
  - D-D-12 同参重试语义两种承载并存：discover 显式回填 `retry_state={"pending_discovers": [call,*queue[1:]]}`，execute 用 `retry_state={}` 靠「载荷未清」隐式约定——一致性风险在重构时需留意（本段只见事实，不判优劣）。
  - D-D-13 `args` 是载荷 dict 的浅拷贝（`dict(...)`）：嵌套结构共享引用，工具若就地改写会回写 state 载荷（registry 契约是否保证只读未核）。

---

## 覆盖自检
- def 清单差集：无。全段 7 个 def 全数覆盖（`_handle_choice`／`_apply_result`／`_invoke_tool`／`_make_discover`＋嵌套 `discover_node`／`_make_execute`＋嵌套 `execute_node`）；无 class；L1889-L1890、L2023-L2024 为分节注释（非符号，已记清单）。
- 本段 emit 事件名全集：`ask`、`notice`、`step`、`tool`（notice 子型：`approval_recorded`／`approval_gate_pending`／`decision_rejected`／`tool_unavailable`／`refused`；step 子型：decision／discover／execute）。
- 本段读写的 state 字段全集（按出现计）：`run_id`、`pending_ask`、`resume_choices`、`next_intent`、`user_hint`、`rounds`、`budget_reject_streak`、`messages`、`process_notes`、`steps`、`notices`、`approved_ids`、`extable_rounds`、`last_execute`、`pending_plan`、`pending_retrieval`、`draft`、`draft_kind`、`tool_retries`、`decision_error`、`pending_discovers`、`last_result`、`discover_used`、`empty_probes`、`executed_payloads`、`budget`（超时值）；经 `_ctx_of` 读 `actor`、`metric_candidates`、`approved_ids`。
- 本段引用的外部符号全集（本文件内定义的除外）：
  - `langgraph.types.interrupt`（L64）、`asyncio.wait_for`
  - `appv2.runtime.state`：`INTENT_DECISION`／`INTENT_DISCOVER`／`INTENT_EXECUTE`／`INTENT_PRECONDITION`／`INTENT_OBSERVE`／`INTENT_ANSWER`（经 `_direct_answer`）、`STEP_DECISION`／`STEP_DISCOVER`／`STEP_EXECUTE`、`RunState`
  - `appv2.tools`：`STATUS_OK`／`STATUS_FAILED`／`STATUS_ASK`、`CATEGORY_BAD_ARGS`／`CATEGORY_RETRYABLE`、`ASK_CLARIFY`／`ASK_EXTERNAL_TABLE_APPROVAL`、`DATA_QUERY`／`DOC_RETRIEVE`、`ToolContext`（经 `_ctx_of`）、`ToolRegistry.call`（经 `deps.registry`）
  - 本文件内但本段外被引用：`_EXTABLE_REJECT_BASIS_KEY`(L315)、`_payload_fingerprint`(L537)、`_discover_fingerprint`(L544)、`_emission_fingerprints`(L550)、`_step_record`(L1051)、`_next_seq`(L1068)、`_gate_or_none`(L1092)、`_observations_of`(L1131)、`_ctx_of`(L1135)、`_timeout_result`(L1150)、`_result_dict`(L1164)、`_direct_answer`(L1203)、`_note`(L1227)、`_notes_with`(L1232)、`_tool_note`(L1237)、`reseed_approval_id`(L1332)、`_node_of`(L4038)、`_route`(L4036)
