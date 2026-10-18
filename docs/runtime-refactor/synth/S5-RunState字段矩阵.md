# S5·RunState 字段矩阵（跨片合成第五件）

- 日期：2026-10-15 ｜ 状态：**定稿（2026-10-16，流水 49——Owner 四裁；核对报告＝`synth/S5-核对报告.md`，审计链＝`spec-review/S5定稿回填-审计.md`）**
- 上游：`recon/I2a`（常量/Manifest）＋`recon/I2b`（RunState 全字段 53）＋各 graph 片「覆盖自检」的读/写声明＋`recon/I1b`（executor 播种）＋`arch/P5b1`（写手收敛主张）
- 本文用途：把 RunState 字段的**写入方 / 读取方 / 持久化面**摊成一张表——重写时状态结构属 ADR-0002 红线③（schema 自有），必须先看清每个字段由谁写、谁读、怎么写盘，才能重构（尤其 P5b1 A-P5b1-06「写手收敛」）。
- **字段数口径（定稿）**：**50 字段**＝旧码实测 53 − 取消 4（`consecutive_asks`／`manifests`／`started_monotonic`／`deadline_monotonic`，流水 49①）＋ 新增 1（`dialogue_view_tokens`，流水 49②）。
- **字段数口径（现行）**：**57 字段**＝定稿 50 ＋ V2-82a 追加 2（`subjects`／`terms`，2026-10-17 流水 88——理解相位落题面主体/术语，默认空＝零漂移）＋ V2-82b 追加 1（`pending_subject_options`，2026-10-17 流水 88——对象歧义 ask 的实例候选名单，发射落/恢复清，默认空＝零漂移）＋ V2-96 追加 3（`explore_rounds`／`explore_fingerprints`／`pending_explore`，2026-10-18——作答侧有界再探的独立计数/指纹/待执行意图，默认零值＝零漂移）＋ V2-115 追加 1（`repair_rounds`，2026-10-18——核验失败回炉的独立改写轮计数，默认零值＝零漂移）。
- 口径声明：写入/读取**未回填行**以**单元**粒度记旧码实测面（M1-M7/H1-H15，见 S1）；**写手收敛 9 行（§四【结构-1/2/4/6】对象）已按已定稿规格的目标态口径回填**（块级唯一写口），两类并存、各行自明。

---

## 一、字段矩阵（定稿 50 字段 ＋ V2-82a 追加 2 ＋ V2-82b 追加 1 ＋ V2-96 追加 3 ＋ V2-115 追加 1＝现行 57 字段）

| 字段 | 写入方 | 读取方 | 持久化/投影 | 备注 |
| --- | --- | --- | --- | --- |
| `run_id` | H3（执行器播种） | M2/M3/M4/M5/M6/M7（各处 ask/审计携行） | runs 表主键 | 全流程读 |
| `question` | H3（播种） | M1/M2/M6/M7 | runs 表 | |
| `actor` | H3（播种） | M1（经 _ctx_of 注入 ToolContext） | — | 身份只从 ctx 进 |
| `status` | H5（_converge）＋H3（三终态落库） | H3/H13 | runs 表状态列 | 状态机四值 |
| `followup_of` | H3（播种）＋H13（受理段） | M1（零探查旁路）、H2 | runs 表 | V2-38 追问标记 |
| `empty_probes` | M5（discover） | M2（拒重发判定） | checkpoint | V2-56 空手探查指纹 |
| `understanding` | M1 | M2/M4（收敛交付） | checkpoint | understand 产物 |
| `metric_candidates` | M1、M3、**M4**（更正：recon F L49/L189 漏记） | M2/M4/M5（_ctx_of） | checkpoint | FX-13 候选集 |
| `subjects` | **M1（V2-82a 2026-10-17 追加）** | 后续相位（V2-82b 对象歧义门等） | checkpoint | 题面主体（归一形；默认空＝零漂移） |
| `terms` | **M1（V2-82a 2026-10-17 追加）** | 后续相位（V2-82b 粒度判据等） | checkpoint | 题面术语（台账指标/术语名；默认空） |
| `ledger_dump` | 旧码实测＝M1 闸族（N0/N1 拒答路径）＋M2（E1 取一次）〔更正：闸族原误记 H6 名下〕；**目标态唯一写面＝context**（装载取一次写回，context.md 行为 10） | 旧码 M1/M2/M3/M4（闸）；**目标态＝prompts 常驻块渲染只读** | checkpoint | 词典层快照；三种旧持久化行为（D-C-04）**已统一**；gate 命中路径零台账 I/O |
| `question_group` | M2（E1 相位①）、M3（就地补 tool/chain）、**M4**（重写步，更正：recon F L49） | M3/M4/M5/M6 | checkpoint | 四相位产物① |
| `tool_matches` | M3、**M4**（更正：recon F L49 漏记） | M4/M5/M6 | checkpoint | 四相位产物② |
| `precondition_verdicts` | M4 | M5/M6 | checkpoint | 四相位产物③ |
| `subtask_results` | M5（**M4 条件写**，更正：recon F L69 分支 9d） | M4/M5/M6 | checkpoint | 四相位产物④；回炉不重跑簿记 |
| `chain_switch_marks` | M4 | M4/M5 | checkpoint | V2-43 换链回炉「一次为界」 |
| `window_miss_marks` | M5 | M5 | checkpoint | V2-46 缺位回捞「一次为界」 |
| `discover_used` | M2/M5 | M2（≤10 闸） | checkpoint | 全 run 发现预算 |
| `messages` | **目标态＝bookkeeping.append_message 唯一写口**（相位禁直写；旧码全节点追加） | 全节点（经上下文投影）＋bookkeeping.call_model（发整链） | checkpoint | 对话链追加式（V2-80h）；pin-22 |
| `contracts_appended` | **目标态＝bookkeeping.append_contract 唯一写函数**（越界相位抛错；旧码 M1/M2/M3） | 相位（经 bookkeeping） | checkpoint | 相位合同一次性标记 |
| `process_notes` | **目标态＝bookkeeping.note 唯一写口**（写入点截断 digest≤200；旧码 M1/M2/M3/M5/H5） | M2/M3/M6 渲染（context.render_process_notes／prompts） | checkpoint | 过程档案（digest≤200，真源 A-P5b2-03） |
| `dialogue` | **目标态＝bookkeeping.append_dialogue**（对话层唯一入口；state 本块零业务写） | persistence（v2 快照投影） | v2 快照读入 | 兼容字段复活为活动字段；条目三键 `{role, content, origin}`（origin 三值明标 state.md 行为 6） |
| `dialogue_view_tokens` | orchestration（注入制、无裸值） | context（行为 9 超窗触发） | checkpoint | **新增（流水 49②）**——compaction 触发参数；8k 档真源 A-P6a-11（流水 43④／46①） |
| `schema_version` | H3（构造） | H13（checkpointer 读侧分流） | checkpoint | 真值 3（见 S3 C-07） |
| `rounds` | M2（重置＋计轮）、M3（**回写原值非增量**，更正：recon E2 L59） | M2（轮数闸）/M4 | checkpoint | 每用户输入周期 3 轮 |
| `task_type` | M2 | M2/M4 | checkpoint | 末次执行的任务型 |
| `decision_error` | M2/M3 | M2/M3（回喂） | checkpoint | 拒因回喂 |
| `user_hint` | M2（回收） | M2（下轮消费后清） | checkpoint | 澄清回收补充 |
| `budget_reject_streak` | M2 | M2（免轮例外） | checkpoint | 连续发现预算拒 |
| `pending_discovers` | M2 | M5 | checkpoint | 待执行发现步（挂起行李） |
| `pending_plan` | M2 | M5 | checkpoint | data_query 计划草稿（挂起行李） |
| `pending_retrieval` | M2 | M5 | checkpoint | doc_retrieve 参数（挂起行李） |
| `last_execute` | M2 | M5（审批批准后重跑） | checkpoint | 末次主执行载荷（挂起行李） |
| `executed_payloads` | M5 | M2（V2-37 同参闸） | checkpoint | 主执行实录指纹（同参重投闸载体，闸归 execution） |
| `tool_retries` | M5 | M5（retryable 一次） | checkpoint | 按工具名计数 |
| `extable_rounds` | M2（恢复） | M2/M4 | checkpoint | 外表审批重跑轮次 |
| `last_result` | M5（execute） | M5（observe）、H/A2（material） | checkpoint | 末次工具结果 |
| `pending_ask` | M2 | M2/M4/H3（挂起帧读） | checkpoint | 挂起帧投影 |
| `pending_subject_options` | **H2（V2-82b 2026-10-17 追加，对象歧义门发射时落）** | **H3（恢复腿 `_apply_choice` 映射 `subjects` 后清空）** | checkpoint | 对象歧义 ask 的油田实例候选（一问一答，写后即清；默认空＝零漂移） |
| `explore_rounds` | **M6（V2-96 2026-10-18 追加，再探轮执行后 +1）** | M6/H2（轮数上限 `MAX_EXPLORE_ROUNDS` 与硬停止判据） | checkpoint | 作答侧再探已执行轮数（≤2；不占澄清轮、不动 discover 预算；默认 0＝零漂移） |
| `explore_fingerprints` | **M6（V2-96 2026-10-18 追加，请求过闸时追加）** | M6（同参指纹拒重） | checkpoint | 已处理再探请求指纹列（`tool|query` 或 `tool|report_id|section`；默认空） |
| `pending_explore` | **M6（V2-96 2026-10-18 追加，作答相位落意图）** | H2/M6（编排执行后清） | checkpoint | 待执行 explore 意图投影（`{reason,requests,raw}`；默认 None） |
| `repair_rounds` | **H2（V2-115 2026-10-18 追加，回炉改写轮执行后 +1）** | H2（轮数上限 `MAX_REPAIR_ROUNDS` 与缺位说明判据） | checkpoint | 核验失败回炉的已执行**改写**轮数（≤2；不占澄清轮、不动 discover 预算；默认 0＝零漂移） |
| `observations` | M5（observe） | M6/M7/M4（材料面） | checkpoint | 全局 [n] 序 |
| `resume_choices` | M2（恢复） | H3（审计） | checkpoint | resume 留痕 |
| `approved_ids` | M2（恢复） | M4/M5（放行态） | checkpoint | 已批准审批单号 |
| `draft` | M1（直答）/M2（截断）/M6（起草，H5 _direct_answer） | M7（核验）、M6（收口） | checkpoint＋runs.answer? | 草稿文本 |
| `draft_kind` | M1/M2/M6 | M7/M6 | checkpoint | ""=待核验／"direct"=直答 |
| `answer` | M6（_finalize） | H3/H13（runs 表）、H6（播种） | runs 表 answer 列 | 最终答案 |
| `verdict` | M7 | M6/M4（unfinished） | checkpoint | 核验裁决 |
| `manifest_digest` | M6（收口） | H13（审计/黑匣子） | checkpoint | sha256 |
| `notices` | **目标态＝bookkeeping.notice 唯一写口**（恰三键 `{type, gates, content}`、只追加；旧码全节点） | H3/H7（出流）、H13 | checkpoint | 全程累积 |
| `steps` | **目标态＝bookkeeping.record_step 唯一写口**（内置取号；旧码全节点经 H5 _step_record） | H13（put_steps）/H7（step 帧） | steps 表（upsert） | 全程累积 |
| `budget` | H3（播种） | M2/M4/M5（闸）、state.check_limits | checkpoint | **形状已裁**：`@dataclass(frozen=True, slots=True)` 闭世界七键（非裸 dict——D-I2b-03 收口） |
| `budget_hit` | H5（_converge）、M2/M3 | 各节点入口（幂等判） | checkpoint | 命中预算项；写法归一＝bookkeeping.converge 单点 |
| `next_intent` | **目标态＝bookkeeping.set_intent 唯一写口**（INTENT 十值闭世界；路由决策仍在 orchestration） | H2（路由表） | checkpoint | 路由意图 |
| `error` | H3（_drive 失败） | H13（收口） | runs 表 error 列（persistence.md 已定） | 错误文本 |

> ~~`consecutive_asks`~~／~~`manifests`~~／~~`started_monotonic`~~／~~`deadline_monotonic`~~ **已取消（流水 49①）**：上限改由 Budget「连续反问上限」键承载；Manifest 改 `StepRecord.manifest` 随步投影；计时并入 Budget「段时长」键／`LimitHit("seconds")`。

> 另 3 个非 RunState 数据类：`AskRequest`（H3 受理入参）＝**`{question, resume_run_id, followup_run_id, actor}`**、`AskChoice`（H3 resume 入参）＝**`{kind, choice, decision, approval_id}`**、`RunHandle`（H3 受理回执）＝**`{run_id, stream, cursor}`**——`frozen=True` 不可变载荷，不进 checkpoint（见 I2b §二）；**三形已对齐 `specs/state.md`（流水 49 改正）**。

---

## 二、按写入方归组（旧码实测写手面——取证保留原貌）

| 写入单元 | 写的字段（个数） |
| --- | --- |
| **H3 执行器**（仅播种/收口） | run_id／question／actor／status／followup_of／messages(seed)／budget／started_monotonic／deadline_monotonic／schema_version／error（新链只写这 11 个） |
| **M1 理解** | understanding／metric_candidates／subjects／terms（后二者 V2-82a 追加）／messages／process_notes／steps／next_intent／notices／draft／draft_kind |
| **M2 澄清**（写手最多） | rounds／decision_error／user_hint／budget_reject_streak／ledger_dump／messages／contracts_appended／question_group／precondition_verdicts／pending_discovers／pending_plan／pending_retrieval／pending_ask／consecutive_asks／notices／process_notes／steps／next_intent／draft／draft_kind／resume_choices／approved_ids／extable_rounds／task_type／pending_subject_options（V2-82b 追加） |
| **M3 匹配** | rounds／decision_error／messages／contracts_appended／process_notes／steps／next_intent／question_group／tool_matches／metric_candidates |
| **M4 前置** | precondition_verdicts／chain_switch_marks／notices／steps／next_intent（+ 收敛路 budget_hit/answer/draft_kind/status） |
| **M5 批量** | subtask_results／observations／last_result／executed_payloads／tool_retries／window_miss_marks／empty_probes／discover_used／notices／steps／next_intent |
| **M6 作答** | draft／draft_kind／answer／manifest_digest／manifests／messages／steps／notices／next_intent |
| **M7 核验** | verdict／draft(改写)／steps／notices／next_intent |
| **H5 公共位** | budget_hit／notices／answer／draft_kind／status／next_intent（_converge 六键）＋ draft（_direct_answer） |

**观察**：`notices`/`steps`/`next_intent`/`messages` 是**全节点共享写口**（几乎每个单元都写）——这是写手收敛的头号目标；`M2 澄清` 单节点写 24 个字段，是**最重的写手**（重写时最该拆）。

> 本节为**旧码实测**写手归组（取证面，保留原貌含已取消字段）；**目标态写口收敛见 §一各行回填**（bookkeeping 单点写口／context 唯一写面——已定稿规格口径）。

---

## 三、持久化面（三条盘）

| 盘 | 由谁写 | 内容 |
| --- | --- | --- |
| **checkpoint**（LangGraph PG saver，3 表：checkpoint/blob/write） | H13（每步框架落） | RunState 全字段投影（旧码实测 53；定稿口径 50，见 §一） |
| **runs 表**（store.py） | H3（受理/终态）＋M6（answer） | run_id／question／status／answer／error |
| **steps 表**（store.py，整体 upsert） | H13（put_steps） | state.steps 重投影 |
| **blackbox 表**（store.py） | H13（put_blackbox，distill） | 终态蒸馏记录 |
| **audit_log 表**（audit.py） | H3（_audit*） | 六类审计事件 |

---

## 四、本表暴露的结构问题（重写输入）

1. `【结构-1】` **ledger_dump 三种持久化行为**（D-C-04）：N0/N1 拒答路径写回、clarify 入口取一次写回、understand 读取不写回——同一字段三个节点的三种行为，重写须统一。**→ 已裁：唯一写面＝context 装载取一次（context.md 行为 10）**。
2. `【结构-2】` **notices/steps/next_intent/messages 全节点共享写口**：无归属单点，重写须定「谁唯一写」或明确「追加式公共位」。**→ 已裁：各归 bookkeeping 唯一写口（§一回填）**。
3. `【结构-3】` **M2 澄清写手 24 字段**：单节点职责过载，重写拆分点。→ 归各相位规格／施工票。
4. `【结构-4】` **dialogue 兼容死字段**：`dialogue` 零读写 vs D-I2b-01 称 executor 降级抽取用它——两说并存，重写前须对 executor 侧取证判定（弃或留）。**→ 已裁：复活为活动字段（bookkeeping.append_dialogue 唯一入口，条目三键 `{role, content, origin}`）**。
5. `【结构-5】` **draft 两义**（""=LLM 草稿待核验 / "direct"=确定性直答）：免起草免核验旁路，重写须保留还是收口（P6a A-P6a-05 病灶）。→ 归 answering／gate 规格。
6. `【结构-6】` **budget 键集未定义**（D-I2b-03）：`budget: dict[str,float]` 键名与写入方在本片范围外，重写须对账。**→ 已裁：`Budget` frozen 闭世界七键（state.md 行为 10）**。
7. `【结构-7】` **回合/轮两词混用**：现状「一轮=一问一答」与「轮数闸=模型迭代轮」混记（D-B1-02），重写命名须分层。→ 归 state／clarification 规格。
8. `【结构-8】` **budget_hit 与 notice 分型双轨**：截断类走 notice.type 机读分型、预算类落 budget_hit——两类「有界终止」分型不一致。→ 归 state／transport 规格。

---

## 五、待补（定稿清零，流水 49）

- ~~`【待补-1】` 非 graph 片读面~~ → **已闭合**：`persistence.md`（`RunRecord` 列／行为 12）＋`context.md` 依赖行给出读面。
- ~~`【待补-2】` 字段级「写入点个数」~~ → **不再补**：写口单点化后该计数降为旧码量化证据，非重写输入。
- ~~`【待补-3】` `error`/`status` 的 runs 表列映射~~ → **已闭合**：`persistence.md` 接口 `RunRecord.status`/`error` 定死、行为 2 定状态机。

---

## 覆盖自检

- 字段：定稿口径 **50**（旧码实测 53 − 取消 4 ＋ 新增 `dialogue_view_tokens` 1）＋ V2-82a 追加 2（`subjects`／`terms`）＋ V2-82b 追加 1（`pending_subject_options`）＋ V2-96 追加 3（`explore_rounds`／`explore_fingerprints`／`pending_explore`）＋ V2-115 追加 1（`repair_rounds`）＝**现行 57** ＋3 载荷类（非状态）；持久化面 5 盘。
- 写手收敛 9 行已按已定稿规格口径回填（bookkeeping 单点写口／context 唯一写面／Budget 闭世界／dialogue 复活）；转录更正 6 处（metric_candidates／question_group／tool_matches 漏 M4、subtask_results 漏 M4 条件、ledger_dump 闸族归属、rounds 回写原值）；尾注 3 载荷类对齐 state.md。
- §二／§三 为旧码实测面（保留原貌含已取消字段）；结构问题 8 条（4 条已裁收口）；待补 3 条清零。数据源＝recon 各片覆盖自检的读/写声明（非我推断）。
