# S5·RunState 字段矩阵（跨片合成第五件）

- 日期：2026-10-15 ｜ 状态：**草案，待 Owner 裁决**
- 上游：`recon/I2a`（常量/Manifest）＋`recon/I2b`（RunState 全字段 53）＋各 graph 片「覆盖自检」的读/写声明＋`recon/I1b`（executor 播种）＋`arch/P5b1`（写手收敛主张）
- 本文用途：把 RunState 53 个字段的**写入方 / 读取方 / 持久化面**摊成一张表——重写时状态结构属 ADR-0002 红线③（schema 自有），必须先看清每个字段由谁写、谁读、怎么写盘，才能重构（尤其 P5b1 A-P5b1-06「写手收敛」）。
- 口径声明：写入/读取以**单元**粒度（M1-M7/H1-H15，见 S1）；「经 helper 间接」单列；非 graph 片（executor/store/context 等）的读面不完整，标 `【待补】`。

---

## 一、字段矩阵（53 字段）

| 字段 | 写入方（单元） | 读取方（单元） | 持久化/投影 | 备注 |
| --- | --- | --- | --- | --- |
| `run_id` | H3（执行器播种） | M2/M3/M4/M5/M6/M7（各处 ask/审计携行） | runs 表主键 | 全流程读 |
| `question` | H3（播种） | M1/M2/M6/M7 | runs 表 | |
| `actor` | H3（播种） | M1（经 _ctx_of 注入 ToolContext） | — | 身份只从 ctx 进 |
| `status` | H5（_converge）＋H3（三终态落库） | H3/H13 | runs 表状态列 | 状态机四值 |
| `followup_of` | H3（播种）＋H13（受理段） | M1（零探查旁路）、H2 | runs 表 | V2-38 追问标记 |
| `empty_probes` | M5（discover） | M2（拒重发判定） | checkpoint | V2-56 空手探查指纹 |
| `understanding` | M1 | M2/M4（收敛交付） | checkpoint | understand 产物 |
| `metric_candidates` | M1、M3 | M2/M4/M5（_ctx_of） | checkpoint | FX-13 候选集 |
| `ledger_dump` | H6（B2 档案）、M2（E1 取一次） | M1/M2/M3/M4（闸） | checkpoint | 词典层快照；**三种持久化行为**（D-C-04，见 §四） |
| `question_group` | M2（E1 相位①）、M3（就地补 tool/chain） | M3/M4/M5/M6 | checkpoint | 四相位产物① |
| `tool_matches` | M3 | M4/M5/M6 | checkpoint | 四相位产物② |
| `precondition_verdicts` | M4 | M5/M6 | checkpoint | 四相位产物③ |
| `subtask_results` | M5 | M4/M5/M6 | checkpoint | 四相位产物④；回炉不重跑簿记 |
| `chain_switch_marks` | M4 | M4/M5 | checkpoint | V2-43 换链回炉「一次为界」 |
| `window_miss_marks` | M5 | M5 | checkpoint | V2-46 缺位回捞「一次为界」 |
| `discover_used` | M2/M5 | M2（≤10 闸） | checkpoint | 全 run 发现预算 |
| `messages` | M1/M2/M3/M6/H5（全节点追加） | 全节点（_complete 发整链） | checkpoint | 对话链追加式（V2-80h） |
| `contracts_appended` | M1/M2/M3 | M1/M2/M3 | checkpoint | 相位合同一次性标记 |
| `process_notes` | M1/M2/M3/M5/H5 | M2/M3/M6（渲染有界段） | checkpoint | 过程档案（digest≤200） |
| `dialogue` | **（零写）** | **（零读）** | v2 快照读入 | **兼容死字段**（D-I2b-01 称 executor 降级抽取用） |
| `schema_version` | H3（构造） | H13（checkpointer 读侧分流） | checkpoint | 真值 3（见 S3 C-07） |
| `rounds` | M2（重置+计轮）、M3 | M2（轮数闸）、M4 | checkpoint | 每用户输入周期 3 轮 |
| `task_type` | M2 | M2/M4 | checkpoint | 末次执行的任务型 |
| `decision_error` | M2/M3 | M2/M3（回喂） | checkpoint | 拒因回喂 |
| `user_hint` | M2（回收） | M2（下轮消费后清） | checkpoint | 澄清回收补充 |
| `budget_reject_streak` | M2 | M2（免轮例外） | checkpoint | 连续发现预算拒 |
| `pending_discovers` | M2 | M5 | checkpoint | 待执行发现步 |
| `pending_plan` | M2 | M5 | checkpoint | data_query 计划草稿 |
| `pending_retrieval` | M2 | M5 | checkpoint | doc_retrieve 参数 |
| `last_execute` | M2 | M5（审批批准后重跑） | checkpoint | 末次主执行载荷 |
| `executed_payloads` | M5 | M2（V2-37 同参闸） | checkpoint | 主执行实录指纹 |
| `consecutive_asks` | M2 | M2/M4（截断判） | checkpoint | run 生命期不清零 |
| `tool_retries` | M5 | M5（retryable 一次） | checkpoint | 按工具名计数 |
| `extable_rounds` | M2（恢复） | M2/M4 | checkpoint | 外表审批重跑轮次 |
| `last_result` | M5（execute） | M5（observe）、H/A2（material） | checkpoint | 末次工具结果 |
| `pending_ask` | M2 | M2/M4/H3（挂起帧读） | checkpoint | 挂起帧投影 |
| `observations` | M5（observe） | M6/M7/M4（材料面） | checkpoint | 全局 [n] 序 |
| `resume_choices` | M2（恢复） | H3（审计） | checkpoint | resume 留痕 |
| `approved_ids` | M2（恢复） | M4/M5（放行态） | checkpoint | 已批准审批单号 |
| `draft` | M1（直答）/M2（截断）/M6（起草，H5 _direct_answer） | M7（核验）、M6（收口） | checkpoint＋runs.answer? | 草稿文本 |
| `draft_kind` | M1/M2/M6 | M7/M6 | checkpoint | ""=待核验／"direct"=直答 |
| `answer` | M6（_finalize） | H3/H13（runs 表）、H6（播种） | runs 表 answer 列 | 最终答案 |
| `verdict` | M7 | M6/M4（unfinished） | checkpoint | 核验裁决 |
| `manifest_digest` | M6（收口） | H13（审计/黑匣子） | checkpoint | sha256 |
| `notices` | 全节点 | H3/H7（出流）、H13 | checkpoint | 全程累积 |
| `manifests` | M6/各步 | H13（黑匣子） | checkpoint | Manifest 列 |
| `steps` | 全节点（经 H5 _step_record） | H13（put_steps）、H7（step 帧） | steps 表（upsert） | 全程累积 |
| `budget` | H3（播种） | M2/M4/M5（闸） | checkpoint | 随状态走 |
| `started_monotonic` | H3（播种） | H8/M2（时长闸） | checkpoint | 单调时钟 |
| `deadline_monotonic` | H3（播种） | M2/M4/M5（时长闸） | checkpoint | 单调时钟 |
| `budget_hit` | H5（_converge）、M2/M3 | 各节点入口（幂等判） | checkpoint | 命中预算项 |
| `next_intent` | 全节点 | H2（路由表） | checkpoint | 路由意图 |
| `error` | H3（_drive 失败） | H13（收口） | runs 表？ | 错误文本 |

> 另 3 个非 RunState 数据类：`AskRequest`（H3 受理入参）、`AskChoice`（H3 resume 入参）、`RunHandle`（H3 受理回执）——`frozen=True` 不可变载荷，不进 checkpoint（见 I2b §二）。

---

## 二、按写入方归组（写手收敛面——P5b1 A-P5b1-06 的目标）

| 写入单元 | 写的字段（个数） |
| --- | --- |
| **H3 执行器**（仅播种/收口） | run_id／question／actor／status／followup_of／messages(seed)／budget／started_monotonic／deadline_monotonic／schema_version／error（新链只写这 11 个） |
| **M1 理解** | understanding／metric_candidates／messages／process_notes／steps／next_intent／notices／draft／draft_kind |
| **M2 澄清**（写手最多） | rounds／decision_error／user_hint／budget_reject_streak／ledger_dump／messages／contracts_appended／question_group／precondition_verdicts／pending_discovers／pending_plan／pending_retrieval／pending_ask／consecutive_asks／notices／process_notes／steps／next_intent／draft／draft_kind／resume_choices／approved_ids／extable_rounds／task_type |
| **M3 匹配** | rounds／decision_error／messages／contracts_appended／process_notes／steps／next_intent／question_group／tool_matches／metric_candidates |
| **M4 前置** | precondition_verdicts／chain_switch_marks／notices／steps／next_intent（+ 收敛路 budget_hit/answer/draft_kind/status） |
| **M5 批量** | subtask_results／observations／last_result／executed_payloads／tool_retries／window_miss_marks／empty_probes／discover_used／notices／steps／next_intent |
| **M6 作答** | draft／draft_kind／answer／manifest_digest／manifests／messages／steps／notices／next_intent |
| **M7 核验** | verdict／draft(改写)／steps／notices／next_intent |
| **H5 公共位** | budget_hit／notices／answer／draft_kind／status／next_intent（_converge 六键）＋ draft（_direct_answer） |

**观察**：`notices`/`steps`/`next_intent`/`messages` 是**全节点共享写口**（几乎每个单元都写）——这是写手收敛的头号目标；`M2 澄清` 单节点写 24 个字段，是**最重的写手**（重写时最该拆）。

---

## 三、持久化面（三条盘）

| 盘 | 由谁写 | 内容 |
| --- | --- | --- |
| **checkpoint**（LangGraph PG saver，3 表：checkpoint/blob/write） | H13（每步框架落） | RunState 全 53 字段投影 |
| **runs 表**（store.py） | H3（受理/终态）＋M6（answer） | run_id／question／status／answer／error |
| **steps 表**（store.py，整体 upsert） | H13（put_steps） | state.steps 重投影 |
| **blackbox 表**（store.py） | H13（put_blackbox，distill） | 终态蒸馏记录 |
| **audit_log 表**（audit.py） | H3（_audit*） | 六类审计事件 |

---

## 四、本表暴露的结构问题（重写输入）

1. `【结构-1】` **ledger_dump 三种持久化行为**（D-C-04）：N0/N1 拒答路径写回、clarify 入口取一次写回、understand 读取不写回——同一字段三个节点的三种行为，重写须统一。
2. `【结构-2】` **notices/steps/next_intent 全节点共享写口**：无归属单点，重写须定「谁唯一写」或明确「追加式公共位」。
3. `【结构-3】` **M2 澄清写手 24 字段**：单节点职责过载，重写拆分点。
4. `【结构-4】` **dialogue 兼容死字段**：`dialogue` 零读写 vs D-I2b-01 称 executor 降级抽取用它——两说并存，重写前须对 executor 侧取证判定（弃或留）。
5. `【结构-5】` **draft 两义**（""=LLM 草稿待核验 / "direct"=确定性直答）：免起草免核验旁路，重写须保留还是收口（P6a A-P6a-05 病灶）。
6. `【结构-6】` **budget 键集未定义**（D-I2b-03）：`budget: dict[str,float]` 键名与写入方在本片范围外，重写须对账。
7. `【结构-7】` **actor 两类型面**（D-I2b-02）：`AskRequest.actor: Actor`（对象）vs `RunState.actor: str`（字符串投影）——转换点在 executor，是否刻意待裁。
8. `【结构-8】` **budget_hit 与 notice 分型双轨**：截断类走 notice.type 机读分型、预算类落 budget_hit——两类「有界终止」分型不一致。

---

## 五、待补（本表未闭合）

- `【待补-1】` 非 graph 片（store/blackbox/audit 的读面、context 的读面）未全量纳表——`steps`/`answer`/`status` 的**读方**需回 J 片补。
- `【待补-2】` 字段级「写入点个数」（如 messages 在 graph.py 10 处、steps 26 处调用）未逐字段计数——写手收敛的量化依据（对应 S3 D-03）。
- `【待补-3】` `error`/`status` 的 runs 表列映射需对 store.py 核（status 四值 vs 表列）。

---

## 覆盖自检

- 字段：RunState 53（对齐 I2b 实测 53）＋3 载荷类（非状态）；持久化面 5 盘。
- 写入方归组覆盖 9 个单元（H3/M1-M7/H5）；读取方标到单元级。
- 结构问题 8 条（4 条引 D 编号疑点）；待补 3 条。数据源＝recon 各片覆盖自检的读/写声明（非我推断）。
