# I2b·现状调研报告

- 锚定：commit e4b75f1（行号以此为准）
- 覆盖：appv2/runtime/state.py L102-文末（文件全长 250 行）
- def/class 清单：逐一全列（含行号区间），不得省略

## def/class 清单（全列）

| 序号 | 符号 | 行号区间 |
| --- | --- | --- |
| 1 | `class AskRequest`（装饰器 L101；类体 L102-L112） | L101-L112 |
| 2 | `class AskChoice`（装饰器 L115；类体 L116-L121；方法 `as_payload` L122-L123） | L115-L123 |
| 3 | `class RunHandle`（装饰器 L126；类体 L127-L131） | L126-L131 |
| 4 | `class RunState`（装饰器 L134；类体 L135-L250；53 字段、无方法） | L134-L250 |

边界说明：本段无模块级函数、无嵌套函数；L153／L156／L197／L217／L228／L230／L233／L239／L243／L248 为分节注释行（非符号）。覆盖区上游邻接 `Manifest`（L70-L98，含 `as_dict` L86-L98）不在本报告范围；L113-L114／L124-L125／L132-L133 为空行；文件止于 L250（RunState 末字段 `error`）。

## 一、RunState 字段表（每个字段一行，务必全量——与 __dataclass_fields__ 数对账）

类签名：`@dataclass(slots=True)`（L134，非 frozen）`class RunState:`（L135-L250）；docstring L136-L141，字段 L143-L250。

| 字段名 | 类型/默认值 | 语义（一句话） | 字段注释要点（版本注记/生命周期注记原文要点） |
| --- | --- | --- | --- |
| `run_id`（L143） | str = "" | run 标识。 | 无注释 |
| `question`（L144） | str = "" | 受理问句。 | 无注释 |
| `actor`（L145） | str = "" | 行级身份（字符串投影）。 | 「行级身份（ctx.actor 注入——身份只从 ctx 进）」 |
| `status`（L146） | str = RUN_RUNNING（＝"running"） | run 状态机当前值。 | 无行注释；默认引用文件内常量 `RUN_RUNNING`（L47）；状态机四值 `RUN_STATUS_KINDS` L45-L53（本片上游区） |
| `followup_of`（L149） | str = "" | 追问续会话标记（前轮 run id）。 | 「追问续会话标记（V2-38；V2-53 零探查拒回闸的追问旁路判据——前轮材料在史的追问 run 零探查定稿放行）。executor 受理段随 RunCommand 播种，仅读」 |
| `empty_probes`（L152） | list[str] = field(default_factory=list) | 同款空手探查指纹列。 | 「V2-56 同款空手探查指纹（discover 拒重发判定键——逐字 json 指纹；空手才记录，命中不记录——允许同参复查）」 |
| `understanding`（L154） | str = "" | understand 产物：理解文本。 | 无行注释；段头「—— understand 产物 ——」（L153） |
| `metric_candidates`（L155） | list[str] = field(default_factory=list) | understand 产物：指标候选集。 | 「FX-13 候选集」（段头 L153） |
| `ledger_dump`（L159） | dict[str, Any] \| None = None | 词典层全量快照（澄清入口缝取一次）。 | 「词典层全量注入（拍板 a）：第 1 次澄清入口从 ledger_dump 缝取一次（现行态快照），随 checkpoint 走——后续轮复用不再取」；段头「—— V2-34 子任务图产物（四相位——ADR-0005）——」（L156） |
| `question_group`（L162） | dict[str, Any] \| None = None | 相位①产物：问题组。 | 「相位①产物：问题组（subtasks[{id/question/ledger_notes/chain?/tool?}]——相位②匹配定案后 subtasks 就地补 tool/chain/plan/retrieval_need/caliber_key）」 |
| `tool_matches`（L164） | list[dict[str, Any]] = field(default_factory=list) | 相位②产物：子问题→工具链定案列。 | 「相位②产物：matches（子问题→工具链定案列——批量执行输入）」 |
| `precondition_verdicts`（L166） | list[dict[str, Any]] = field(default_factory=list) | 相位③产物：四态判定列。 | 「相位③产物：四态判定列（前置条件机 payload——blocked_ask 挂起帧随行）」 |
| `subtask_results`（L169） | list[dict[str, Any]] = field(default_factory=list) | 相位④产物：子问题执行结果列。 | 「相位④产物：子问题执行结果列（{id,status: ok\|failed\|refused,reason,obs_count,fingerprint}）——回炉不重跑的簿记面（R4：成功子问题指纹零重复）」 |
| `chain_switch_marks`（L175） | dict[str, str] = field(default_factory=dict) | 换链回炉簿记：子问题 id→计划载荷规范指纹。 | 「换链回炉簿记（V2-43）：绑定闸拒（data 链＋在册未绑定 agg）触发过回炉①的子问题 id → 触发时计划载荷规范指纹（同参比对面）。一次为界：标记在册后同支（同 id 或同参指纹）再触发＝blocked_refuse 直答终局（不环）；与 V2-37 executed_payloads 执行面簿记同向互替——本簿记辖前置条件机回炉面，执行面指纹照旧归 executed_payloads」 |
| `window_miss_marks`（L181） | dict[str, str] = field(default_factory=dict) | 缺位回捞簿记：子问题 id→检索载荷规范指纹。 | 「缺位回捞簿记（V2-46 R1c）：knowledge 链检索窗载缺位来源（window_miss 观察在场）触发过回捞门的子问题 id → 触发时检索载荷规范指纹（同参比对面）。一次为界：标记在册后同支（同 id 或同参指纹）再触发＝直答如实终局（不环）；与 V2-43 chain_switch_marks（前置条件机回炉面）/V2-37 executed_payloads（执行面）同构分辖——本簿记辖批量相位缺位回捞面」 |
| `discover_used`（L183） | int = 0 | 全 run 发现预算已用数。 | 「全 run 发现预算已用数（澄清相位 ≤10 合同闸判据——Owner 拍板放宽）」 |
| `messages`（L190） | list[dict[str, str]] = field(default_factory=list) | 对话链（只追加不改写）。 | 「—— 对话链追加式（V2-80h——KV 缓存本源形态）：messages＝整条对话链（只追加不改写——每次 LLM 调用发送整链，任意相邻调用互为前缀延伸）。类型正确性红线：user＝任务书/相位合同/工具台账行/回喂/用户选择/材料段；assistant＝模型原样输出/话术/最终答案；伪标注形永不出现。相位合同一次性：clarify/toolmatch 包在相位首次进入时追加一条（contracts_appended 标记——回炉轮不重发，链上已有缓存照命中）」 |
| `contracts_appended`（L191） | list[str] = field(default_factory=list) | 相位合同已追加标记列。 | 无行注释；语义由 `messages` 块注释（L184-L189）覆盖——相位合同一次性标记 |
| `process_notes`（L192） | list[dict[str, str]] = field(default_factory=list) | 过程档案段列。 | 无注释（state.py 内；渲染/消费面在 graph.py 档案族，本片范围外） |
| `dialogue`（L195） | list[dict[str, str]] = field(default_factory=list) | 80a 自然对话层（兼容死字段）。 | 「【V2-80h 兼容死字段】dialogue（80a 自然对话层）——零读写，仅保 v2 快照（含 dialogue 通道）读入不炸；追问种子降级抽取用它（executor）」 |
| `schema_version`（L196） | int = 3 | checkpoint schema 版本。 | 「checkpoint 版本（v1＝history 混装/v2＝dialogue 层）」 |
| `rounds`（L198） | int = 0 | 已消耗的 LLM 决策周期数。 | 「已消耗的 LLM 决策周期数（≤3 轮上限闸判据）」；段头「—— decision 产物（ReAct 决策出口——行为断言锁定面）——」（L197） |
| `task_type`（L199） | str = "" | 末次执行发射的任务型。 | 「末次执行发射的任务型 data\|knowledge\|mixed」 |
| `decision_error`（L200） | str = "" | 末次拒因。 | 「末次拒因（schema 校验/工具 bad_args——回喂重决策）」 |
| `user_hint`（L201） | str = "" | 澄清回收的用户补充。 | 「澄清回收的用户补充（decision 下轮消费后清空）」 |
| `budget_reject_streak`（L205） | int = 0 | 连续发现预算拒计数。 | 「连续发现预算拒计数（S2 落闸，P-033 中途审查）：预算驱动的 discover 拒不占轮的免轮例外只留首次——连续第 2 次起转占轮（轮数闸确定性收敛，顽投自环不环）；任何非预算拒结局（分解/钻取成功/反问/其他拒因）与澄清回收即清零」 |
| `pending_discovers`（L206） | list[dict[str, Any]] = field(default_factory=list) | 待执行发现步列。 | 无注释 |
| `pending_plan`（L207） | dict[str, Any] \| None = None | data_query 计划草稿。 | 「data_query plan_draft（data\|mixed）」 |
| `pending_retrieval`（L208） | dict[str, Any] \| None = None | 检索调用参数。 | 「doc_retrieve args（knowledge\|mixed）」 |
| `last_execute`（L209） | dict[str, Any] \| None = None | 末次主执行载荷。 | 「末次主执行载荷（审批批准后重跑）」 |
| `executed_payloads`（L213） | list[str] = field(default_factory=list) | 主执行实录指纹列。 | 「主执行实录（V2-37 同参重投机器闸）：实际执行过的主执行载荷规范指纹列（execute 支 ok/ask 逐支记一条——decision 出口对同参二次发射比对该簿记；审批重投／retryable 同参重试走各自通道不经 decision 出口，不受闸辖）」 |
| `consecutive_asks`（L216） | int = 0 | 连续澄清 ask 计数。 | 「连续澄清 ask 计数（run 生命期累计不清零——P-024b 疑点2）：第 2 次 ask 截断带材料直答」 |
| `tool_retries`（L218） | dict[str, int] = field(default_factory=dict) | 按工具名计数的重试簿记。 | 「retryable 同参重试一次（合同上限）——按工具名计数（P-024b C2：discover 链上的重试不挤占 execute 的重试份额）」；段头「—— 工具步产物 ——」（L217） |
| `extable_rounds`（L225） | int = 0 | 外表审批批准后的重跑轮次。 | 「外表审批批准后的重跑轮次（V2-52 越集全通道：四相位下双审批为常态——extable_rounds 可达 2＝前置闸＋引擎闸各一轮，四相位批准分支无 cap、单调收敛无死循环〔放行集只增、plan 不重排〕；legacy 骨架通道保留 cap 1——C1 裁决登记 2026-10-11：生产 four_phase=True，legacy 不补全通道）」 |
| `last_result`（L226） | dict[str, Any] \| None = None | 末次工具结果。 | 「ToolResult dict 投影」 |
| `pending_ask`（L227） | dict[str, Any] \| None = None | 挂起帧。 | 「AskFrame dict 投影（挂起帧）」 |
| `observations`（L229） | list[dict[str, Any]] = field(default_factory=list) | 观察列。 | 「全局 [n] 序」；段头「—— observe 产物 ——」（L228） |
| `resume_choices`（L231） | list[dict[str, Any]] = field(default_factory=list) | resume 选择留痕列。 | 无行注释；段头「—— resume 留痕（接线①）——」（L230） |
| `approved_ids`（L232） | list[str] = field(default_factory=list) | 已批准审批单号列。 | 无行注释；段头 resume 留痕（接线①）（L230） |
| `draft`（L234） | str = "" | 草稿文本。 | 无行注释；段头「—— verify/answer 产物 ——」（L233） |
| `draft_kind`（L235） | str = "" | 草稿类型标记。 | 「""=LLM 草稿待核验；"direct"＝确定性直答（拒答/闸拒——免起草免核验）」 |
| `answer`（L236） | str = "" | 最终答案。 | 无行注释；段头 verify/answer 产物（L233） |
| `verdict`（L237） | dict[str, Any] \| None = None | 核验裁决。 | 无注释 |
| `manifest_digest`（L238） | str = "" | Manifest 摘要。 | 「Manifest 摘要（sha256——answer 步收口）」 |
| `notices`（L240） | list[dict[str, Any]] = field(default_factory=list) | 通知列。 | 无行注释；段头「—— 全程累积 ——」（L239） |
| `manifests`（L241） | list[dict[str, Any]] = field(default_factory=list) | Manifest 列。 | 无行注释；段头全程累积（L239） |
| `steps`（L242） | list[dict[str, Any]] = field(default_factory=list) | step 列。 | 无行注释；段头全程累积（L239） |
| `budget`（L244） | dict[str, float] = field(default_factory=dict) | 预算参数表。 | 无行注释；段头「—— 预算闸（ReAct 语义；随状态走，跨进程恢复后仍生效）——」（L243） |
| `started_monotonic`（L245） | float = 0.0 | 起始单调时钟。 | 无行注释；段头预算闸（L243） |
| `deadline_monotonic`（L246） | float = 0.0 | 截止单调时钟。 | 无行注释；段头预算闸（L243） |
| `budget_hit`（L247） | list[str] = field(default_factory=list) | 命中预算项列。 | 无行注释；段头预算闸（L243） |
| `next_intent`（L249） | str = "" | 路由意图。 | 无行注释；段头「—— 路由意图与错误 ——」（L248） |
| `error`（L250） | str \| None = None | 错误文本。 | 无注释；RunState 类体止于此行（文件末行） |

RunState 类级规则条目：

- R-I2b-01 RunState 为 `@dataclass(slots=True)` 且非 frozen（L134）——可变图状态；同文件 AskRequest／AskChoice／RunHandle 均 `frozen=True, slots=True`（L101／L115／L126）——「载荷不可变／状态可变」两类形态。
- R-I2b-02 类 docstring：ReAct loop 图状态、六节点共享读写；LangGraph 只把它当 schema 消费，checkpoint 落库内容＝本 schema 的逐字段投影（L136，另见模块 docstring L1-L6）。
- R-I2b-03 字段值全部 JSON 原语可投影（observations/emission 均为 dict 投影）——checkpointer 序列化面最简、跨进程恢复无损（L138-L139）。
- R-I2b-04 预算闸参数随状态走（行为约定 7 的 ReAct 语义：轮数≤3／轮内发现≤2＋主执行≤2／总时长 300s／单工具 30s，测试可收窄）（L139-L140）。
- R-I2b-05 `messages`＝整条对话链，只追加不改写；每次 LLM 调用发送整链，任意相邻调用互为前缀延伸（V2-80h KV 缓存本源形态）（L184-L185）。
- R-I2b-06 `messages` 类型正确性红线：user＝任务书/相位合同/工具台账行/回喂/用户选择/材料段；assistant＝模型原样输出/话术/最终答案；伪标注形永不出现（L186-L187）。
- R-I2b-07 相位合同一次性：clarify/toolmatch 包在相位首次进入时追加一条（`contracts_appended` 标记——回炉轮不重发，链上已有缓存照命中）（L188-L189）。
- R-I2b-08 回炉/回捞簿记「一次为界」：`chain_switch_marks` 与 `window_miss_marks` 标记在册后同支（同 id 或同参指纹）再触发＝终局直答（不环）——两簿记同构分辖（前置条件机回炉面／批量相位缺位回捞面），执行面指纹归 `executed_payloads`（L170-L181 原文要点）。
- R-I2b-09 `schema_version` 默认 3——checkpoint 版本注记：v1＝history 混装／v2＝dialogue 层（L196）。
- R-I2b-10 `consecutive_asks` run 生命期累计「不清零」（P-024b 疑点2）：第 2 次 ask 截断带材料直答（L214-L216）。
- R-I2b-11 `extable_rounds`：四相位批准分支无 cap（可达 2＝前置闸＋引擎闸各一轮；单调收敛无死循环〔放行集只增、plan 不重排〕）；legacy 骨架通道保留 cap 1（C1 裁决 2026-10-11：生产 four_phase=True）（L221-L225）。

疑点（只列不判）：

- D-I2b-01 `dialogue` 注释（L193-L195）内部两说并存：既称「零读写……读入不炸」，又称「追问种子降级抽取用它（executor）」——若 executor 实读则非零读写；需对 executor 侧取证后判定。
- D-I2b-02 同语义两类型面：`AskRequest.actor: Actor`（L111，受理面对象）vs `RunState.actor: str`（L145，行级身份字符串投影）——两符号间转换点在 executor 播种段（本片范围外），是否刻意属重构议题。
- D-I2b-03 `budget: dict[str, float]`（L244）键集在本文件未定义——键名与写入方均在本片范围外，重构对账时需另行取证。
- D-I2b-04 RunState 非 frozen 而同文件三个载荷 dataclass 均 frozen（L134 vs L101/L115/L126）——「状态可变／载荷不可变」是否刻意纪律，只列不判。

## 二、其余数据类

### `AskRequest`（L102-L112，装饰器 L101）｜提问受理（{question, actor} 原形＋V2-38 追问续会话字段）

- 字段表：

| 字段名 | 类型/默认值 | 语义 | 注释要点 |
| --- | --- | --- | --- |
| `question`（L110） | str（无默认，必填） | 提问问句。 | 无注释 |
| `actor`（L111） | Actor（无默认，必填；appv2.infra.security.Actor） | 提交人身份对象。 | 无注释 |
| `followup_of`（L112） | str = "" | 追问续会话的前轮 run id；非空＝追问形态。 | V2-38 追问续会话：新 run 播种该前轮线程的消息历史（前轮问句/决策/台账/答案随追问进上下文）；前轮须 completed（未收口轮走 resume——执行器把守，映射 404/409） |

- 规则条目：
  - R-I2b-12 `frozen=True, slots=True`（L101）——不可变受理载荷。
  - R-I2b-13 `followup_of` 非空＝追问形态——新 run 播种前轮消息历史（前轮问句/决策/台账/答案随追问进上下文）（L105-L107）。
  - R-I2b-14 追问前轮须 completed；未收口轮走 resume——执行器把守，映射 404/409（L107-L108）。
- 疑点：
  - 见 D-I2b-02（actor 类型面对照）；本类无新增疑点。

### `AskChoice`（L116-L123，装饰器 L115）｜resume 的选择（clarify 选窗文本／审批批准驳回＋单号留痕）

- 字段表：

| 字段名 | 类型/默认值 | 语义 | 注释要点 |
| --- | --- | --- | --- |
| `value`（L119） | str（无默认，必填） | 选择值（clarify＝选窗文本）。 | docstring：clarify＝选窗文本；审批＝批准/驳回＋审批单号留痕——接线①（L117） |
| `approval_id`（L120） | str \| None = None | 审批单号（无审批＝None）。 | 同 docstring（L117） |

- 方法：`as_payload`（L122-L123）→ `{"value": self.value, "approval_id": self.approval_id}`。
- 规则条目：
  - R-I2b-15 `frozen=True, slots=True`（L115）——不可变 resume 载荷；字段语义＝clarify 选窗文本／审批批准驳回＋审批单号留痕（接线①）（L117）。
  - R-I2b-16 `as_payload` 固定两键投影 `{"value","approval_id"}`（approval_id 可 None）——落库/事件载荷形（L122-L123）。
- 疑点：无（显式记「无」，不静默）。

### `RunHandle`（L127-L131，装饰器 L126）｜run 受理回执（{run_id, stream}）

- 字段表：

| 字段名 | 类型/默认值 | 语义 | 注释要点 |
| --- | --- | --- | --- |
| `run_id`（L130） | str（无默认，必填） | run 标识。 | docstring：「run 受理回执（接口定义节原形：{run_id, stream}）」（L128） |
| `stream`（L131） | AsyncIterator[RunEvent]（无默认，必填；appv2.runtime.events.RunEvent） | 事件流游标消费面。 | 同 docstring（L128） |

- 规则条目：
  - R-I2b-17 `frozen=True, slots=True`（L126）——不可变受理回执；{run_id, stream} 为接口定义节原形（L128）。
  - R-I2b-18 `stream` 类型 `AsyncIterator[RunEvent]`（L131）——本片唯一非 JSON 投影类型字段（对照 RunState 全部字段 JSON 可投影约束，L138-L139）；RunHandle 非 RunState 字段、不进 checkpoint 投影。
- 疑点：无（显式记「无」，不静默）。

## 覆盖自检

- RunState `__dataclass_fields__` 数＝53（实测：`.venv/bin/python` 对 HEAD 工作树导入 `appv2.runtime.state`，`len(RunState.__dataclass_fields__)`＝53；`git diff e4b75f1 HEAD -- appv2/runtime/state.py` 为空、两态同文件同为 250 行，故实测结果即锚定态）；本报告表内条目数＝53——对账无差。
- def/class 清单差集：无——L102-文末 4 类＋1 方法全列（`AskRequest`／`AskChoice`／`AskChoice.as_payload`／`RunHandle`／`RunState`）；本段无模块级函数、无嵌套函数；分节注释行 10 处已注（非符号）。边界说明：`Manifest`／`Manifest.as_dict`（L70-L98）为上游邻接、不在覆盖；文件止于 L250。
- 引用的外部符号全集（本文件内定义的除外；内建类型不列）：`Actor`（appv2.infra.security——AskRequest.actor L111）；`RunEvent`（appv2.runtime.events——RunHandle.stream L131）；`AsyncIterator`（collections.abc——L131）；`Any`（typing——多处类型注记）；`dataclass`／`field`（L101／L115／L126／L134 装饰器与默认工厂）。文件内引用但不计外引：`RUN_RUNNING`（L47，作 `status` 默认值 L146）。
