# V2 公共簿记（bookkeeping）

状态: 已定稿
来源: `specs/modules.md` `## bookkeeping` 卡、`docs/runtime-refactor/synth/S5-RunState字段矩阵.md` §四（共享写口无归属）、`docs/runtime-refactor/recon/B1-公共位与结果归一.md`（公共位与结果归一）、`docs/runtime-refactor/recon/H-观察核验作答与图装配.md`（节点读写面）、`docs/runtime-refactor/walk/裁决表.md` §06（预算与收敛）、`specs/state.md`（形状与判定）、`specs/persistence.md`（落盘面）、`specs/transport.md`（帧与通知分型）、`specs/gateway_adapter.md`（模型出口）
版式: `docs/spec-format.md`（节标题按该文 §二之二 逐字命名） ｜ 工序: `docs/spec-process.md`

## 目标

全节点共享的**唯一写入面**：步记录与序号、对话链与对话层追加、过程档案、通知、触界收敛落地、完成收口旁路、调模型单点、工具上下文装配、工具结果归一投影——**多节点写同一份状态，只有这一个门口**。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 状态字段**形状**与限额**判定** | `state`（`RunState`／`Manifest`／`check_limits`） | `specs/state.md` |
| 落盘与读回（步记录／黑匣子／审计写库） | `persistence` | `specs/persistence.md` |
| 事件与帧的发射（含通知出帧） | `transport`（本块只把通知**记进状态**，发帧归它） | `specs/transport.md` |
| 模型调用的**实作**（重试退避／供应商细节） | `gateway_adapter`（本块只**发起**） | `specs/gateway_adapter.md` |
| 材料段渲染、材料挑选、术语表常驻块编译 | `context` | `specs/modules.md` `## context` |
| 相位的业务判断（该不该收口、该不该反问） | 各相位 ＋ `orchestration` | `specs/agent-loop.md` 行为 1 |
| 用程序替模型做语义判断（本块只记账与分派） | **不做** | `docs/runtime-refactor/walk/判断归责表.md` |

### 旧码公共位承接对照（`recon/B1-公共位与结果归一.md` 十六项，逐条落点）

| 旧码符号 | 落点 |
|---|---|
| `_step_record` ／ `_next_seq` | **承接** → `record_step` ／ `next_seq`（行为 2／3） |
| `_converge` | **拆分** → 判定归 `state.check_limits`；落地归本块 `converge`（行为 12） |
| `_note` ／ `_notes_with` | **承接** → `note`（只追加＋写入点截断，行为 10） |
| `_result_dict` ／ `_observations_of` | **承接** → `result_projection`（观察列随投影一体输出，行为 17） |
| `_ctx_of` | **承接** → `tool_context`（行为 16） |
| `_direct_answer` | **承接** → `direct_answer`（行为 14） |
| `_gate_or_none` | **排除**：入口闸的判定归 `state.check_limits`、节点入口的调用归 `orchestration`／各相位——本块不管 |
| `_MESSAGE_CLS` | **排除**：role→框架消息类映射含**框架类型**，只许活在 `orchestration`（边界闸 **R5b**）；本块只做文本层 `append_message(role, content)` |
| `_complete` | **拆分**：实作归 `gateway_adapter`；本块 `call_model` 只转发并记账（行为 15） |
| `_timeout_result` | **排除**：单工具超时结果构造随工具调用点归 `execution` |
| `_clarify_capped_answer` | **排除**：截断话术属文本面（`clarification`／`answering`）；本块只落地结论 |
| `_user_turn` | **排除（退役）**：旧码已零调用点（`recon/B1` D-B1-15），其形由 `append_message(role="user", …)` 覆盖 |
| `_tool_note` | **排除/分派**：台账条目的**措辞五形**归 `execution`（它决定写什么），本块 `note` 只收定型条目 |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| bookkeeping | 新增 | 本块本体：共享写口 ＋ 收敛落地 ＋ 收口旁路 ＋ 调模型/工具面 |
| state | 新增 | 字段形状与限额判定（本块只消费其形状与 `check_limits`） |
| gateway_adapter | 新增 | 模型出口（本块只发起调用） |
| tools | 新增 | `ToolContext` 类型与送窗预算公式（**只引形状与数值，不走其行为面**） |
| persistence | 新增 | `StepRecord` 形状（落盘归它；本块只产形状、不写库） |
| transport | 新增 | 帧发射与通知分型闭世界（本块只按闭世界记账） |

## 接口定义

```python
# ── 共享写口（唯一入口；相位只能经此写，禁直写）─────────────
def record_step(state, *, kind: str, title: str,
                status: str = "ok",
                payload: dict[str, Any] | None = None,
                manifest: Manifest | None = None) -> StepRecord: ...
def next_seq(state) -> int: ...
def append_message(state, *, role: str, content: str) -> None: ...
def append_dialogue(state, *, role: str, content: str, origin: str) -> None: ...
def note(state, *, phase: str, title: str, digest: str) -> None: ...
def notice(state, *, type: str, gates: Sequence[str] = (), content: str) -> None: ...
def set_intent(state, intent: str) -> None: ...           # next_intent 唯一写口（闭世界越界即拒；路由决策仍在 orchestration——行为 6）
def append_contract(state, phase: str) -> None: ...       # contracts_appended 唯一写口（幂等；越界相位抛错——钉 pin-24 写入面，行为 8）

# ── 触界收敛与完成收口 ───────────────────────────────────
def converge(state, *, elapsed_seconds: float | None = None,
             consecutive_asks: int | None = None) -> None: ...
                                          # 落地写入（判定归 state.check_limits）；无回值
                                          # 两注入参＝**转交判定面**（`seconds`／`ask_cap` 用量不在
                                          # 状态形状内——注入形真源 specs/state.md 行为 11；2026-10-16
                                          # 裁·流水 61：轮闸入口把编排计时与连续反问计数交来）
def direct_answer(state, text: str) -> None: ...

# ── 调模型与工具面 ─────────────────────────────────────
def call_model(state, caller: str, messages: Sequence[Mapping[str, str]],
               *, system: str | None = None) -> str: ...
                                          # system＝**本环节规章段**（2026-10-17 H 批·角色分家）：
                                          # 有值 → 请求首条前置 `{"role": "system", "content": system}`；
                                          # **不入链、不进检查点、不用即散**（承载位＝调用级注入参）
def tool_context(state) -> ToolContext: ...
def result_projection(result) -> dict[str, Any]: ...
```

- **写口入参形状**：`StepRecord`（形状真源＝`specs/persistence.md` 接口定义）；`append_message` 的 `role` ∈ `user`｜`assistant`｜`system`（同 `state.messages` 口径；**2026-10-17 H 批**加第三值——`system` 只承载**链首背景块**（每链恰一条），环节规章不入链）；`append_dialogue` 的 `origin` ∈ `user_verbatim`｜`assistant_final`｜`clarify_approval_replay`（闭世界真源＝`specs/state.md` 行为 6）；`notice` 的 `type` ∈ `NOTICE_TYPES`（真源＝`specs/transport.md`）；`gates` 取值闭世界＝`LimitHit.limit` 七限额键名（**2026-10-16 裁·流水 52-B**；原「轮数／时长两项」为旧两限额世界措辞，见行为 11 注；取值真源＝`recon/B1-公共位与结果归一.md` R-B1-04「gates 取值闭世界＝max_rounds／total_seconds」；限额数值真源＝`walk/裁决表.md` §06-A 与 `recon/K-上下文事件指南预算.md` R-K-72…R-K-78）。
- **`append_contract` 的 `phase`** ∈ **合同追加相位闭世界**（`decision`｜`clarify`｜`toolmatch`——合同文本追加面的相位标记集；现状锚＝`appv2/runtime/graph.py` 三处 `contracts_appended` 标记写入，写手面真源＝`synth/S5-RunState字段矩阵.md` `contracts_appended` 行——写手 M1／M2／M3）；**越界相位抛错**（fail-closed，同本块错误契约）；**幂等**：已标记相位再标记＝无操作。**`contracts_appended` 的字段语义真源＝`specs/state.md` 行为 5**（本规格不复制其语义；本块只认领**唯一写入面**——复审⑦ V4 主窗裁「谁写口谁拥有」）。
- **`record_step` 的 `kind`** ∈ `STEP_KINDS`（六值，真源 `specs/state.md`）；**`status` 是显式关键词参**（闭世界 `ok`｜`failed`｜`refused`，越界抛错；缺省 `ok`）——**由调用方如实给**（本块**不猜**、不从 payload 推断语义，守总纪律），**不得恒 `ok`**（现状恒 `ok` 是缺陷，见「依赖与风险」）。
- **`payload` 原样保真**：不做假值归一（空 `{}` 与缺省是两件事）——契约与 `specs/persistence.md` 行为 8 同源。
- **错误契约**：闭世界越界（`role`／`origin`／`type`／`kind`／`gates` 取值）→ **抛错（fail-closed）**；**在已收敛的状态上二次收敛 → 幂等无操作**（不抛错、不重复追加）。
- 真源：`specs/modules.md` `## bookkeeping` 卡（签名以卡为准；卡面已随本规格补全共享写口）。

## 框架与依赖红线

- **无点名框架**（本块不引入任何框架）。对应闸：**R5b 契约**。
- **不直引模型出口**（模型只经 `gateway_adapter`）。对应闸：**R7 契约**（禁直引 `appv2.infra.llm_client`）。
- **不直引引擎**（`knowledge`／`query`／`retrieval`）。对应闸：**R6 契约**。
- **运行逻辑只依赖两处**（`state` 形状／判定 ＋ `gateway_adapter` 模型出口）；**类型与常量形状**另引三处：`tools`（`ToolContext`）／`persistence`（`StepRecord`）／`transport`（`NOTICE_TYPES`）——**只许引类型与常量，不许引其行为**（不调工具、不落盘、不发帧）。对应闸：**无该面的专属闸 → 人审**（原因：R1–R8 没有「bookkeeping 依赖白名单」这一面；可降维面＝AST 断言「import 只出现这五块」＋「三处形状块只用于类型/常量」）。
- **不落盘**：本块不写库、不写文件（落盘归 `persistence`）。对应闸：**无专属闸 → 人审**＋AST 断言「本块无 DB／文件写路径」。
- **禁手写替代**：不得绕过写口直改状态字段（相位侧同禁）。对应闸：**无专属闸 → 人审**＋测试 `::no_direct_state_write_in_phases`。

## 行为约定

1. **写口单点**：全节点共享的可变写面（步记录／对话链／对话层／过程档案／通知）**只经本块函数**；相位**不得直写**这些字段。断言：AST／grep 扫描——`state.messages`／`steps`／`process_notes`／`notices`／`dialogue`／`next_intent` 的写操作只出现在本块（钉 `pin-22` 的**写入点单点面**）。
2. **序号单调且与步记录成对**：`next_seq(state)` ＝ **已有步记录数 ＋ 1**；`record_step` 内部取号——**禁调用方手加偏移**（现状的手工偏移导致序号与步数可不等，重写收正）。断言：连记三步后序号为 1／2／3 且步数＝3；`next_seq` 与 `len(steps)+1` 恒等。
3. **步记录形状＝`StepRecord` 全字段（含 `run_id`）且状态如实**：`record_step` 产出 **`StepRecord` 的七个字段**——`run_id`（自 `state.run_id` 取，**不由调用方传**）＋`seq`＋`step`＋`status`＋`title`＋`manifest`＋`payload`（形状真源＝`specs/persistence.md` 接口定义；现状「入状态的六键 dict」不含 `run_id`，那是**旧形**，重写以七字段为准）；**`status` 表达真实态**（`ok`｜`failed`｜`refused`，显式入参）——**不得恒 `ok`**。断言：键集合恒七；`run_id` 与状态一致；失败步 `status="failed"`。
4. **`payload` 原样保真**：`payload` 直写（空 `{}` 照写 `{}`、缺省写缺省，**两者读回可区分**）；**禁 `payload or {}` 式假值归一**。断言：空与缺失两态的步记录读回不等价（钉 `pin-12` 的**承接面**——钉本体挂 `specs/persistence.md` 的落盘面）。
5. **`manifest` 随步投影**：`manifest` 非空 → 以 `Manifest.as_dict()` 投影进步记录；为空 → 写空（**不得省略键**）。断言：两种路径的键集合相同。
6. **`next_intent` 的唯一写口＝本块 `set_intent`**：取值 ∈ `INTENT`（闭世界真源 `specs/state.md` 行为 9；越界即拒）；**各相位经它给路由意图**，收敛（行为 12）与直答旁路（行为 14）两处由本块内部写；**「去哪」的决策仍在 `orchestration`**（路由表读该字段并决定跳转——写字段≠做路由决策）。断言：越界取值抛错；全仓 `next_intent` 的写操作只出现在本块（`grep`／AST；并入行为 1 的写口单点断言集）。
7. **对话链只追加**（钉 `pin-22`，P0 的**写入面**）：`append_message` **只追加、不改写**（不替换、不重排、不删除既有条目）。断言：追加 N 条后前 N-1 条逐字不变。**2026-10-17 H 批注（角色分家）**：`role` 闭世界加第三值 `system`——**只承载链首背景块**（每链恰一条，挂编排建链点：题面 user 条之前；逐字稿真源＝`specs/prompts.md` 族⑦）；**环节规章不入链**（走 `call_model` 的 `system` 注入参）。机读面＝`tests/domains/test_v2_bookkeeping.py::messages_append_only`／`tests/domains/test_v2_four_phase.py::test_system_slot_request_layout_end_to_end`。
8. **相位合同一次性**（钉 `pin-24` 的**写入面**）：`contracts_appended` 的**唯一写函数＝本块 `append_contract(state, phase)`**——相位经它标记「合同已追加」；已标记相位再标记＝**幂等无操作**（不重复追加、不重复标记），`append_message` 的调用方据此不重发合同文本；**越界相位抛错**（闭世界见接口节）。断言：同相位二次进入后合同条数不变；`contracts_appended` 的写操作只出现在本块该函数（并入行为 1 的写口单点断言集）。
9. **对话层纯度**：`append_dialogue` 的 `origin` 越界即拒；**过程内容（任务书／指令／注记）不得经该入口**（要写过程内容走 `note`）。断言：注入含任务书的一轮后，`dialogue` 条目 `origin` 全落在三值内；越界调用抛错。
10. **过程档案有界且只追加**：`note` 在**写入点**截断 `digest`（上限真源＝`synth/S5-RunState字段矩阵.md` 的 `process_notes` 条目口径，本规格不复述数字）；只追加、不改写既有条目。断言：超长 `digest` 落库后长度受控且截断可见；既有条目逐字不变。
11. **通知恰三键＋分型闭世界**：`notice` 落 `{type, gates, content}` 恰三键；`type` ∈ `NOTICE_TYPES`、`gates` ⊆ 轮数／时长两项（**2026-10-16 裁（流水 52-B）**：闭世界以 `LimitHit.limit` 七限额键名为准（旧两限额世界措辞更新）；converge 注记 `gates` 取命中键名），越界即拒；**只追加**。断言：缺键／多键／越界各判失败；通知列只增不减。
12. **触界收敛落地（幂等）**：`converge(state, …)` 先调 `state.check_limits`（判定归 `state`）；**命中** → 落地六键（`budget_hit` 追加命中项／通知追加如实注记／答案正文＝已取得材料逐条如实交付／`draft_kind="direct"`／`status="completed"`／`next_intent=answer`）；**未命中** → **零副作用**。**幂等**：已收敛（`budget_hit` 非空）再调 → **无操作**（不重复追加通知、不重复追加 gates、不覆盖答案与状态）。断言：二次调用后通知条数与 gates 长度不变（治现状「已收敛仍可二次收敛」的疑点）。**注入形两参（2026-10-16 裁·流水 61）**：`elapsed_seconds`／`consecutive_asks` 可选关键词参——本口**原样转交**判定面（`seconds`／`ask_cap` 两键的用量不在 `RunState` 形状内，注入口＝编排侧轮闸入口；本口不自算、不兜底），缺省时判定面与无注入形逐字节等价。
13. **收敛答案与通知材料面同源**：收敛交付的正文材料与通知里的未完成项清单**取自同一材料面**（不存在两处漂移：答案说交付了 X、通知说未完成 X）。断言：同一状态快照下两处的材料标识集合一致。
14. **完成收口旁路单点**：`direct_answer(state, text)` 恒写三键（`draft=text`／`draft_kind="direct"`／`next_intent=answer`）——拒答、闸拒、收敛转答、直答共用**同一出口**（免起草免核验）。断言：三键齐备且取值固定。
15. **调模型单点（桥接）**：`call_model(state, caller, messages)` 从状态取 `run_id` → 调 `gateway_adapter.complete` → **向节点只回 `content`**；**回执的用量与归因面（token／`cached_tokens`／`alias`／时长／`caller`／`run_id`）由本块记进步记录与 Manifest**——**禁裸文本吞掉记账面**（真源 `specs/gateway_adapter.md` 行为 1）。断言：一次调用后步记录/Manifest 里可读到用量与归因字段。**2026-10-17 H 批注（角色分家·system 承载位）**：签名加关键词参 `system: str | None = None`——有值 ⇒ **请求首条前置**一条 `{"role": "system", "content": system}`（本环节规章段，文本真源＝`specs/prompts.md` 规章取件函数族），**不入链、不进 `state.messages`／检查点、不用即散**（下一次不带 `system` 的调用零残留——无槽位可泄漏）；**承载位＝调用级注入参、不新增 `RunState` 字段**（`specs/state.md` 行为 1 的字段集断言零改；若落成字段则 `checkpoint.encode_state` 的全字段投影会把它落盘，与「不进持久化」相抵）；假值（`None`／空串）＝入参链原样（缺省形与旧调用零行为差）；记账面不受注入影响。机读面＝`tests/domains/test_v2_bookkeeping.py::call_model_system_injection_no_leak`。
16. **工具上下文装配**：`tool_context(state)` **身份只从状态取**（不接调用方传身份）；**外表放行态随上下文走**（不进工具参数、不重排计划）；送窗预算按**子问题数**取值（数值与公式真源＝`appv2/tools/schema.py` 的 `resolve_send_budget` 与其配套常量；`ToolContext` 的形状真源＝`specs/modules.md` `## tools` 卡——**本规格不复述数值**）。断言：上下文里的身份／放行集／预算与状态一致；参数里无放行态。
17. **结果归一投影**：`result_projection(result)` 逐字段**原样投影**（无增删改名）；**空值语义统一**——「有该字段但为空」与「无该字段」**读回可区分**（禁真假值归一）。断言：投影键集合固定；空值与缺省两态不等价。
18. **本块零判断**：除 `call_model` 的转发与两侧闭世界分派外，无词表／正则语义判定。断言：AST 扫描本块源码。

## 不降级与静默禁令

- **合法降级路径：无**（本块不降级：闭世界越界即抛错；收敛只做「有界终止」的如实交付，不是降级）。
- **触界不静默**：注记必落（行为 11／12）且正文如实交付已取得材料——红线 `docs/runtime-refactor/arch/P7a-交接包与挂账清单.md`（A-P7a-37「不许静默」）。
- **记账不丢**：`call_model` 的用量与归因面**必须**落到步记录／Manifest（行为 15）——「裸文本吞掉记账面」视为缺陷。
- **不许自述完成**：完成由程序侧判定（`state.check_limits` 与核验结论），本块只**落地**它给的结论（行为 12／14）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 共享写面只经本块（相位禁直写） | `tests/domains/test_v2_bookkeeping.py::single_write_port` |
| 相位侧不得绕过写口直改状态字段（红线「禁手写替代」的相位侧半面——与 `::single_write_port` 同断言集的相位侧扫描） | `tests/domains/test_v2_bookkeeping.py::no_direct_state_write_in_phases` |
| 序号单调且与步数成对（禁手工偏移） | `tests/domains/test_v2_bookkeeping.py::seq_monotonic_paired` |
| 步记录 `StepRecord` 全字段（含 `run_id`）＋`status` 如实（失败态可表达） | `tests/domains/test_v2_bookkeeping.py::step_record_all_fields_and_status` |
| `payload` 原样保真（空与缺失可区分） | `tests/domains/test_v2_bookkeeping.py::payload_faithful` |
| `manifest` 投影随步且键恒在场 | `tests/domains/test_v2_bookkeeping.py::manifest_projected_or_empty` |
| 对话链只追加不改写 | `tests/domains/test_v2_bookkeeping.py::messages_append_only` |
| 相位合同一次性（回炉轮不重发） | `tests/domains/test_v2_bookkeeping.py::contract_once` |
| `contracts_appended` 唯一写口＝`append_contract`（幂等；越界相位抛错） | `tests/domains/test_v2_bookkeeping.py::append_contract_sole_write_idempotent_closed_world` |
| 对话层纯度：`origin` 闭世界且过程内容不入层 | `tests/domains/test_v2_bookkeeping.py::dialogue_port_purity` |
| 过程档案 `note` 写入点截断且只追加 | `tests/domains/test_v2_bookkeeping.py::note_bounded_append_only` |
| 通知恰三键＋`type`／`gates` 闭世界 | `tests/domains/test_v2_bookkeeping.py::notice_three_keys_closed_world` |
| 触界收敛落地六键；未命中零副作用 | `tests/domains/test_v2_bookkeeping.py::converge_lands_six_keys` |
| 收敛幂等（二次调用不重复追加／不覆盖） | `tests/domains/test_v2_bookkeeping.py::converge_idempotent` |
| 收敛答案与通知材料面同源（不漂移） | `tests/domains/test_v2_bookkeeping.py::converge_material_same_source` |
| 直答旁路恒写三键 | `tests/domains/test_v2_bookkeeping.py::direct_answer_three_keys` |
| 调模型单点：只回 `content`，用量/归因落记账 | `tests/domains/test_v2_bookkeeping.py::call_model_keeps_accounting` |
| **（H 批 2026-10-17）** `system` 注入参只随本次请求走：请求首条前置、不入链、不用即散（零泄漏）、记账面照落 | `tests/domains/test_v2_bookkeeping.py::call_model_system_injection_no_leak` |
| **（H 批 2026-10-17）** 链首背景块 role＝`system` 恰一条、只追加不改写（对话链角色闭世界三值） | `tests/domains/test_v2_bookkeeping.py::messages_append_only` |
| 工具上下文：身份只从状态取、放行态随上下文、预算按子问题数 | `tests/domains/test_v2_bookkeeping.py::tool_context_assembly` |
| 结果投影原样（空值与缺省可区分） | `tests/domains/test_v2_bookkeeping.py::result_projection_faithful` |
| `next_intent` 唯一写口＋闭世界越界即拒 | `tests/domains/test_v2_bookkeeping.py::set_intent_single_port_closed_world` |
| 本块零判断（AST 扫描） | `tests/domains/test_v2_bookkeeping.py::no_judgement_in_bookkeeping` |
| 【边界集】空步列／超长 digest／已收敛再收敛／越界枚举 → 各落对应分支 | `tests/domains/test_v2_bookkeeping.py::boundary_empty_huge_converged_enum` |
| 【保留集】常规三步流程的记录形状与顺序不变 | `tests/domains/test_v2_bookkeeping.py::retention_normal_three_steps` |

> **测试文件归属**：本块验收测试绑**新建** `tests/domains/test_v2_bookkeeping.py`（本块是阶段 2 新划的公共层块 `appv2/runtimev2/bookkeeping/`，与现状 `appv2/runtime/graph.py` 公共位函数的旧码测试形状不同）；旧码测试本批不改。

## 依赖与风险

- **旧码残留登记**：`recon/B1` 的 `_user_turn`（user 消息条目构造单点）在旧码里**已零调用点**（各节点内联 `{"role":"user",…}` 字面量——`recon/B1` D-B1-15）——重写**不承接该函数**：其形由本块 `append_message(role="user", …)` 覆盖（见行为 7）。
- 依赖：`state`（形状／`Manifest`／`check_limits`／三族常量）｜`gateway_adapter`（`complete` 与 `ModelReply`）｜`specs/modules.md` `## tools` 卡（`ToolContext` 形状）＋`appv2/tools/schema.py`（送窗预算公式与常量的现状锚）｜`specs/persistence.md`（`StepRecord` 形状）｜`specs/transport.md`（`NOTICE_TYPES`）。
- 风险与对策（每条带检测手段）：
  1. **共享写口无归属**（现状：`synth/S5-RunState字段矩阵.md` §四【结构-2】列 `notices`／`steps`／`next_intent` 三件全节点共享写口，§二观察另把 `messages` 并列）→ 对策＝行为 1 单点写口＋相位禁直写。检测＝`::single_write_port` ＋ AST 断言。
  2. **步状态恒 `ok`**（现状没有失败态表达面——`recon/B1` D-B1-01）→ 对策＝行为 3（`status` 如实三值）。检测＝`::step_record_all_fields_and_status`。
  3. **`payload` 假值归一**（现状 `payload or {}` 使空与缺失不可分）→ 对策＝行为 4 保真（与 `specs/persistence.md` 行为 8 同源）。检测＝`::payload_faithful`。
  4. **序号与步数可不等**（现状豁免步由调用方手加偏移——`recon/B1` D-B1-02）→ 对策＝行为 2 取号内置。检测＝`::seq_monotonic_paired`。
  5. **二次收敛**（现状 `toolmatch` 直调收敛不经幂等守卫——`recon/B1` D-B1-03）→ 对策＝行为 12 幂等。检测＝`::converge_idempotent`。
  6. **收敛措辞与实际阶段不符**（现状前缀恒称「已取得材料未及核验」——`recon/B1` D-B1-04）→ 对策＝正文**由材料面决定**（行为 13），措辞随实际态；若仍要固定前缀，**属规格变更**。检测＝`::converge_material_same_source` ＋ **人审**（措辞）。
  7. **裸文本吞掉记账面**（若 `call_model` 只回 `content` 而不落用量/归因）→ 对策＝行为 15。检测＝`::call_model_keeps_accounting`。
  8. **身份从参数进**（若调用方把身份传进工具上下文）→ 对策＝行为 16（身份只从状态取）。检测＝`::tool_context_assembly`。
  9. **假值归一造成两态不可分**（现状 `detail` 空 dict 归 None 后与「无 detail」不可分——`recon/B1` D-B1-13）→ 对策＝行为 17 保真。检测＝`::result_projection_faithful`。
  10. **本块依赖面窄但无专属闸** → 对策＝AST 断言（import 白名单）＋人审。检测＝**人审**（登记）。
  11. **`contracts_appended` 写入悬空**（复审⑦ V4：字段语义在 `specs/state.md` 行为 5、`prompts` 侧称「追加记账归 state 行为 5」——**写函数无人认领**，写入面悬空）→ **已清（本批）**：写入面归本块 `append_contract`（唯一写函数；谁写口谁拥有，主窗 2026-10-15 裁）。检测＝`::append_contract_sole_write_idempotent_closed_world`。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 验收测试逐行有标识 ／ 触及模块名已声明 | spec gate（**该闸只校这两项**——十节标题不在其作用面） | 已进 CI |
| 十节标题齐备、逐字、有序 | **人审** | 原因：仓内无标题闸（登记：可降维为一条标题机检） |
| 真源引用可解析（路径／边界规则编号／被引卡片在册） | 真源引用闸 `tools/ref_resolvable.py` | 已进 CI |
| 不引框架 | 边界闸 **R5b** | 已真跑 |
| 不直引模型出口（只经 `gateway_adapter`） | 边界闸 **R7** | 已真跑 |
| 不直引引擎 | 边界闸 **R6** | 已真跑 |
| 依赖：**运行逻辑**只许 `state`／`gateway_adapter`；`tools`／`persistence`／`transport` **只许引类型与常量形状**；不落盘；禁旁路直写 | **无该面的专属闸 → 人审**（降维 AST 断言：import 白名单＋「形状块只用于类型/常量」） | 原因：R1–R8 无 bookkeeping 边界条 |
| 共享写口单点、相位禁直写 | 测试 `::single_write_port` ＋ `::no_direct_state_write_in_phases`（钉 `pin-22` 的**写入点单点面**；字段面挂 `specs/state.md`） | 待实现 |
| 对话链只追加不改写（写入面） | 钉 **`pin-22`**（P0）；测试 `::messages_append_only` | 待织网（阶段 5） |
| 相位合同一次性（写入面落点＝`append_contract`——`contracts_appended` 唯一写函数，越界相位抛错） | 钉 **`pin-24`**（P1）；测试 `::contract_once` ＋ `::append_contract_sole_write_idempotent_closed_world` | 待织网（阶段 5） |
| 对话层纯度（**写入面**：`append_dialogue` 的 `origin` 闭世界＋过程内容不入层） | 钉 **`pin-26`**（P1；字段面挂 `specs/state.md`、渲染面挂 `specs/understanding.md`）；测试 `::dialogue_port_purity` | 待织网（阶段 5） |
| `payload` 原样保真（写入面） | 钉 **`pin-12`**（P1，**承接面**——钉本体落 `specs/persistence.md` 落盘面）；测试 `::payload_faithful` | 待织网（阶段 5） |
| 触界不静默（注记＋如实交付） | 测试 `::converge_lands_six_keys`／`::converge_material_same_source` | 待实现 |
| 记账面不丢（用量／归因落步记录与 Manifest） | 测试 `::call_model_keeps_accounting` | 待实现 |
| 本块零判断 | AST 断言 `::no_judgement_in_bookkeeping` | 待实现（阶段 5） |
| 卡级修正（共享写口补全／`record_step` 签名／`status` 三值） | **人审** | 原因：无「卡与规格一致」机检闸；本批已改卡并记施工流水 |
| 「不做什么」的纯范围排除（不判定触界／不落盘／不发射帧／不实作模型出口） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（不引框架／引擎／模型出口）已由边界闸 R5b／R6／R7 覆盖 |
