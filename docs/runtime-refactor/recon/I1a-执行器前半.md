# I1a·现状调研报告

- 锚定：commit e4b75f1（行号以此为准）
- 覆盖：appv2/runtime/executor.py L1-L264
- def/class 清单：逐一全列（含行号区间），不得省略

| 序号 | 符号 | 行号区间 |
| --- | --- | --- |
| 1 | `class RunCommand`（装饰器 L58；docstring L60-64；字段 L66-71） | L58-L71（类体）+L73-L75（含 `__post_init__`） |
| 2 | `RunCommand.__post_init__` | L73-L75 |
| 3 | `class RunNotFoundError` | L78-L79 |
| 4 | `class RunNotSuspendedError` | L82-L83 |
| 5 | `new_run_id` | L86-L88 |
| 6 | `extract_dialogue_from_legacy_history` | L99-L134 |
| 7 | `class GraphRunExecutor`（类声明与 docstring） | L137-L138 |
| 8 | `GraphRunExecutor.__init__` | L140-L173 |
| 9 | `GraphRunExecutor.execute` | L175-L261 |

本段无嵌套函数、无 lambda。边界说明：L1-16 为模块 docstring；L18-49 为 import 块；L51-55 为命令 kinds 常量；L91-96 为旧史抽取常量；L263-264 为下一节「内部位」注释头——`_seed_messages`（L265）起不在本报告范围（下文仅以其作 caller/接缝锚点引用）。

## 模块头与常量清单（只标行号与短标识，不抄正文）

- 模块 docstring（L1-16）三句事实：L1 标题「RunCommand seam＋GraphRunExecutor＋AgentRuntime（ADR-0003）」；L3-5 seam 动机（命令入口与执行器为显式 seam，将来执行器换 Redis Stream 消费者而 api/tools/事件契约零改动）；L7-10 执行器职责（受理→装配六步图（checkpointer 注入）→后台驱动→run 状态机四态落库→事件流收束；挂起恢复刷新段时限——总时长 300s 按段计）；L12-15 审计闭环（run 创建/终态/拒答/外表审批决定四事件经 RunAuditor 落 audit_log，action 恒 `agent_v2.*` 前缀；审计写口异常转 notice 出流）。
- 命令常量：`COMMAND_ASK`（值＝"ask"）L53、`COMMAND_RESUME`（值＝"resume"）L54、`COMMAND_KINDS`（frozenset 两值）L55。
- 旧史抽取常量（L91 节注释「纯函数零 I/O，golden 钉测守」）：`_LEDGER_LINE_MARK`（值＝"参数："）L93、`_LEDGER_LINE_RESULT`（值＝"→ 结果"）L94、`_RECYCLE_CLARIFY_PREFIX`（值＝"用户补充："）L95、`_RECYCLE_APPROVAL_PREFIX`（值＝"外表引用审批决定："）L96。
- import 块 L18-49：标准库 asyncio L20／json L21／uuid L22／collections.abc（Awaitable、Callable）L23／dataclasses（dataclass）L24／typing（Any）L25；第三方 langgraph.types.Command L27；同仓 appv2.infra.db.ConnectionManager L29；appv2.infra.security（Actor、SecurityService）L30；appv2.runtime.audit（RunAuditor、who_of）L31；appv2.runtime.blackbox（distill、pointer）L32；appv2.runtime.budget（Budget、now_monotonic）L33；appv2.runtime.context（SYSTEM_PROMPT、ContextBuilder）L34；appv2.runtime.events（EVENT_BLACKBOX、EventBus）L35；appv2.runtime.graph（LoopDeps、build_graph）L36；appv2.runtime.llm.GatewayChatModel L37；appv2.runtime.state 八符号 L38-47；appv2.runtime.store.RunStore L48；appv2.tools（ASK_EXTERNAL_TABLE_APPROVAL、ToolRegistry）L49。

---

### `RunCommand`（file L58-L71）｜run 命令值对象（ask/resume 两态闭世界）

- 消费：无（纯数据载体）。
- 调用：callers=AgentRuntime.ask（L622-627，构造 kind=COMMAND_ASK＋question＋actor＋followup_of）／AgentRuntime.resume（L632-634，构造 kind=COMMAND_RESUME＋run_id＋choice）——两者均在本文件 L610 起的 AgentRuntime 内（超出 L264，仅为构造点事实）；失败＝字段组合不合法本类不拒（唯一校验是 kind 闭世界，见 `__post_init__`）。
- 分支表（穷尽）：
  1. 类声明为 frozen＋slots dataclass，字段六项（kind／question／actor／run_id／choice／followup_of）——无运行分支；校验归 `__post_init__`（L73-75）。
- 副作用：无。
- 返回：不可变实例；缺省值 question=""、actor=None、run_id=""、choice=None、followup_of=""（L67-71）。
- 规则条目：
  - R-I1a-01 `followup_of` 非空＝追问形态（docstring L62-63）：新 run 播种前轮线程消息历史、前轮须 completed——播种与前轮校验的把守点在 execute（L186 调用 `_seed_messages`，其实现 L265 起），本类零校验。
- 耦合：`appv2.infra.security.Actor`（L67 注解）、`appv2.runtime.state.AskChoice`（L70 注解）；`COMMAND_KINDS`（本文件 L55）。
- 疑点：
  - D-I1a-01 六字段无组合校验：kind=ask 不带 question、kind=resume 不带 run_id、ask 形态携 choice 等均构造期放行（`__post_init__` 只查 kind 闭世界）——字段—形态一致性责任在调用方/execute，类内无把守。

### `RunCommand.__post_init__`（file L73-L75）｜kind 闭世界校验

- 消费：self.kind。
- 调用：caller=dataclass 构造器（每次 `RunCommand(...)` 自动触发；本文件构造点=L622／L632）；失败＝抛 ValueError（消息含 `sorted(COMMAND_KINDS)` 与 kind 的 repr）。
- 分支表（穷尽）：
  1. kind ∈ COMMAND_KINDS（"ask"／"resume"）→ 通过（返回 None）。
  2. kind ∉ COMMAND_KINDS → `raise ValueError`（越界拒构造）。
- 副作用：无。
- 返回：None。
- 规则条目：
  - R-I1a-02 命令种类两值闭世界（ask/resume，L55 常量）——越界即拒（ValueError）；无未知态兼容、无默认值归一。

### `RunNotFoundError`（file L78-L79）｜run 不存在的异常源

- 消费：无（仅类声明＋docstring）。
- 调用：抛出点（事实）＝execute L213（resume 查库无行）、`_seed_messages` L282（追问前轮查无，超出本段）；失败去向＝api 层映射 404（docstring L79「V2-07 api 404 的 runtime 侧异常源」；映射实现不在本段）。
- 分支表（穷尽）：
  1. 无分支——类声明（Exception 子类）。
- 副作用：无。
- 返回：异常实例（构造）。
- 规则条目：
  - R-I1a-03 run 查无 → 抛 RunNotFoundError → api 层映射 404（本文件只做异常源，不映射）。
- 耦合：无（内建 Exception 子类）。
- 疑点：无。

### `RunNotSuspendedError`（file L82-L83）｜非挂起态不可 resume 的异常源

- 消费：无（仅类声明＋docstring）。
- 调用：抛出点（事实）＝execute L215-217（status 非 waiting_ask）、L222-223（mark_running 的 ValueError 折算）、`_seed_messages` L284（前轮未 completed，超出本段）；失败去向＝api 层映射 409（docstring L83；映射实现不在本段）。
- 分支表（穷尽）：
  1. 无分支——类声明（Exception 子类）。
- 副作用：无。
- 返回：异常实例（构造）。
- 规则条目：
  - R-I1a-04 run 非挂起态（含状态机转移越界、追问前轮未收口）→ 抛 RunNotSuspendedError → api 层映射 409。
- 耦合：无。
- 疑点：无。

### `new_run_id`（file L86-L88）｜run 号生成

- 消费：无。
- 调用：caller=execute L182（每次 ask 恰好一次）；失败＝无异常路径。
- 分支表（穷尽）：
  1. 无分支——`uuid.uuid4().hex` 取前 8 字符拼前缀 "run-" 返回。
- 副作用：无。
- 返回：str（形如 `run-`＋8 个十六进制字符）。
- 规则条目：
  - R-I1a-05 每次 ask 生成 `run-`＋uuid4 低 32 位的 8 个十六进制字符（docstring L87：与 00 §1.5 机器短 id 族同族）——作为新 run 主键与 checkpointer thread_id；本函数不查库、不做唯一性校验。
- 耦合：标准库 `uuid`。
- 疑点：
  - D-I1a-02 8 字符＝32 比特随机空间，无与库内既有 run 的去重/冲突检测——碰撞时 create_run 主键冲突的表现与该处异常处理，代码内无说明。

### `extract_dialogue_from_legacy_history`（file L99-L134）｜旧 v1 checkpoint 混装历史→对话层抽取（纯函数零 I/O）

- 消费：参数 values（旧 checkpoint values dict，只读 `values.get("history")`）；关键词参数 question（前轮 question 权威字段）、answer（前轮 answer 权威字段）。零模型、零数据库、零网络（节注释 L91「golden 钉测守」）。
- 装配：链尾追加——turns 首元素恒为 `{"role":"user","content":question}`（L114）；history 逐轮命中的回收轮按原顺序 append（L126／L130）；末位 answer 非空才追加 `{"role":"assistant","content":answer}`（L132-133）；system 首条由调用方 `_seed_messages` 补（L319，超出本段）。
- 调用：caller=`_seed_messages` L314-318（仅 v1/无 checkpoint 兜底路径——前序分流：messages 链非空走 v3 整链承接 L301-302、dialogue 非空走 v2 降级 L308-312）；失败＝无异常路径（全部 fail-closed 跳过）。
- 分支表（穷尽——单 for 循环逐轮，共 9 条出口）：
  1. `values.get("history")` 为 None/空 → 循环零迭代 → 仅产出 [user(question)]（answer 非空时再加 assistant）。
  2. 轮非 dict（`not isinstance(turn, dict)`，L116）→ 跳过。
  3. `str(turn.get("role")) != "user"`（含缺 role 时 str(None)="None"）→ 跳过（L116-117 注释：assistant 过程原话不进对话层——终稿以 runs.answer 权威字段落）。
  4. content 含「【待解构的题干】」（L119 字面量）→ 跳过（任务书轮——题干嵌任务书尾部，不做尾部剥离再抽取；多份任务书同形，question 权威字段已承载，L107-108 注释）。
  5. content 同时含 `_LEDGER_LINE_MARK`（"参数："）与 `_LEDGER_LINE_RESULT`（"→ 结果"）（L121）→ 跳过（执行台账轮）。
  6. content 以 `_RECYCLE_CLARIFY_PREFIX`（"用户补充："）开头（L123）→ 去前缀 `strip()` 得 value；value 非空 → append user(value)；value 空 → 不追加（静默消失）。
  7. content 以 `_RECYCLE_APPROVAL_PREFIX`（"外表引用审批决定："）开头（且未命中第 6 条，elif L127）→ 去前缀后按全角「（」`split("（", 1)[0]`、`strip()` 得 value（即批准/驳回判定词，审批单号段被剔除）；value 非空 → append user(value)；空 → 不追加。
  8. 其余不可分类轮（决策/澄清指令等）→ 跳过（fail-closed，L131 注释）。
  9. 循环后 answer 为空 → 不追加 assistant（L132 条件）。
- 副作用：无（docstring L102「只读不改写」）。
- 返回：list[dict[str,str]]＝[user question, *回收轮自然化, assistant answer?]（answer 空则省，docstring L112）。
- 规则条目：
  - R-I1a-06 fail-closed 白名单：仅首轮 question 权威字段＋两类可分类回收轮（用户补充／外表审批决定）进对话层；其余（非 user 轮、任务书轮、台账轮、不可分类 user 轮）全跳过（docstring L104-111）。
  - R-I1a-07 首轮 user 恒为 question 权威字段（不抽 history 首轮、不做任务书尾部剥离——L107-108 注释说明多份任务书同形故取字段权威）。
  - R-I1a-08 回收轮自然化：用户补充轮＝去系统前缀后的正文（L124）；审批决定轮＝去前缀后取全角「（」前第一段判定词（批准/驳回），审批单号随文案剔除（L128）。
  - R-I1a-09 终稿 assistant 恰一条、恒取自 answer 权威字段（不用 history 中的 assistant 轮）；answer 空则无 assistant 轮（L132-133）。
  - R-I1a-10 判定优先级：任务书（L119）→ 台账（L121）→ 回收前缀（用户补充 elif 审批决定，L123/L127）——台账判定先于回收前缀判定。
- 耦合：无外部模块（纯内建与模块常量 `_LEDGER_LINE_*`／`_RECYCLE_*`，L93-96）。
- 疑点：
  - D-I1a-03 判定次序事实：台账判定（L121）在回收前缀判定之前——以「用户补充：」开头、正文同时含「参数：…→ 结果」的轮会被判台账轮跳过，回收语义被遮蔽；代码无说明。
  - D-I1a-04 审批轮切分只认全角「（」（L128）：半角「(」或无反括号形不剥离（value 保留整段）；切分只取第一段，判定词后若另有内容不保留。
  - D-I1a-05 content 一律 `str()` 强转（L118）：非字符串载荷（None／list 等）被字符串化后参与匹配——None→"None" 归不可分类跳过；无类型拒、无告警。
  - D-I1a-06 去前缀后 value 为空（如「用户补充：」后仅空白）→ 该轮静默消失，无痕，与「不可分类跳过」不可区分（L125／L129）。
  - D-I1a-07 四类判定之外无保留路径且无其余形态清单（docstring 仅举「决策/澄清指令等」）——v1 老史中不以前缀出现的自然 user 轮信息全部丢弃（docstring 自述 fail-closed）；重构若换史源需重估。
  - D-I1a-08 question 为空串时仍产出空内容 user 首轮（函数不做非空过滤；调用方传 `prior.question or ""`，L316）。

### `GraphRunExecutor`（file L137-L138）｜命令执行器类声明

- 分支表（穷尽）：
  1. 类声明与 docstring（L138「命令执行器：RunCommand →六步图驱动→RunEvent 流（seam 的默认实现）」）——无运行分支；装配与行为归 `__init__`／`execute` 两条目。
- 副作用：无（类声明本体）。
- 返回：构造实例（见 `__init__`）。
- 规则条目：
  - R-I1a-11 执行器＝ADR-0003 seam 的默认实现（模块 docstring L3-5）：命令入口（AgentRuntime）与执行器之间为显式 seam，将来换 Redis Stream 消费者时 api/tools/事件契约零改动。
- 耦合：无（类声明本体）。
- 疑点：无。

### `GraphRunExecutor.__init__`（file L140-L173）｜执行器依赖装配

- 消费：keyword-only 十四参数——registry（ToolRegistry）L143、models（dict[str, GatewayChatModel]）L144、db（ConnectionManager）L145、saver（Any，注释注明 PgCheckpointer/BaseCheckpointSaver，防环不直接 import 类型）L146、budget（Budget|None=None）L147、builder（ContextBuilder|None=None）L148、security（SecurityService|None=None）L149、guide（Any=None，注释 GuideProvider 防环）L150、today（Any=None，注释「指南缺省实现的今天锚点——测试钉日；缺省 infra.clock」）L151、four_phase（bool=False，注释 V2-34 四相位装配、骨架期缺省 False）L152、ledger_dump/watermark/data_wells/object_digests（四个可选读缝 Callable，缺省 None）L153-156。
- 调用：caller=组合根 appv2/api/app.py L232-245（生产装配：registry、models 三键字典、db、saver=PgCheckpointer(db)、budget、guide=OntologyGuideProvider、four_phase、ledger_dump、watermark、data_wells、object_digests=load_object_digests——未传 security/builder/today）。
- 分支表（穷尽）：
  1. budget 为 None → `self._budget = Budget()`（内置缺省预算）；显式传入 → 原值（L162）。
  2. builder 为 None → `self._builder = ContextBuilder()`；显式 → 原值（L163）。
  3. guide/today/four_phase/ledger_dump/watermark/data_wells/object_digests 无校验直存（L164-170）——None/False 原样保存，语义由消费点（`_deps` L339 起透传 LoopDeps、图节点）决定。
  4. 四个必填参数（registry/models/db/saver）无默认值——不传即 TypeError。
  5. 恒构造 `self._store = RunStore(db)`（L171）与 `self._auditor = RunAuditor(db, security)`（L172，security=None 时 RunAuditor 内自建 SecurityService(db)，audit.py L70-73）。
  6. `self._tasks: set[asyncio.Task[None]] = set()` 建空集（L173）——后台任务强引用容器；add/discard 在 `_spawn` L409-410（超出本段）。
- 副作用：无（仅实例属性赋值；RunStore/RunAuditor 构造零 I/O——审计建表延后到 `ensure_ready`）。
- 返回：None（构造器）。
- 规则条目：
  - R-I1a-12 budget/builder 缺省即内置缺省实例（Budget()／ContextBuilder()）——不是 None 透传；其余可选缝缺省原样透传、零降级分支。
  - R-I1a-13 必填 kw 参数缺即 TypeError；saver/guide/today 及四读缝以 Any 注解（防循环 import 策略，L146/L150 注释）——类型契约仅由注释承载，运行期无类型校验。
  - R-I1a-14 每实例自建 RunStore 与 RunAuditor（共用 db）；审计 security 可注入桩，缺省由 RunAuditor 自建 SecurityService(db)——生产装配缺省 security/builder/today（app.py L232-245 未传），today=None 经 `_deps` 透传 LoopDeps 由其内 clock 兜底。
- 耦合：`appv2.tools.ToolRegistry`、`appv2.runtime.llm.GatewayChatModel`、`appv2.infra.db.ConnectionManager`、`appv2.infra.security.SecurityService`、`appv2.runtime.budget.Budget`、`appv2.runtime.context.ContextBuilder`、`appv2.runtime.store.RunStore`、`appv2.runtime.audit.RunAuditor`、标准库 `asyncio`（注解）。
- 疑点：
  - D-I1a-09 guide 缺省 None 不拒：生产组合根必传（app.py L238），但本构造器不拒绝 None——失败点推迟到图节点消费处（本段不可见）。
  - D-I1a-10 saver/guide/today 等以 Any 注解（防环策略）——若重构引入类型检查/依赖注入容器，这些「注释承载的契约」无机器可检面。
  - D-I1a-11 `self._tasks` 仅 add/discard 两处（L173／L409-410），类内无等待/取消/排空（drain）方法——进程退出时在途后台任务的收尾语义代码内无说明。

### `GraphRunExecutor.execute`（file L175-L261）｜命令受理主入口（同步返回，图后台驱动）

- 消费：command（RunCommand——kind／question／actor／run_id／choice／followup_of）；self 各依赖（`_auditor`／`_store`／`_budget`／`_four_phase`／`_saver`／`_deps`／`_initial_state`／`_spawn`／`_audit`）；resume 分支另读 checkpointer 线程态（`resume_choices`／`notices`）。
- 装配：本函数不拼消息链（ask 的 messages 装配在 `_initial_state` L363-388，本段外）；装配的是图输入（ask＝RunState 经 `_initial_state`；resume＝`Command(resume=choice.as_payload())`）与 config（`{"configurable": {"thread_id": …}}`）。
- 调用：callers=AgentRuntime.ask L621-627（kind=ask）／AgentRuntime.resume L630-634（kind=resume），AgentRuntime 挂于 app.state.agent_runtime（app.py L250）供 api 消费；失败＝同步抛 RunNotFoundError／RunNotSuspendedError／ValueError（见编排步骤 3d／4a／4b／5），成功即返回 RunHandle（图由后台任务驱动）。
- 编排步骤（逐步，行锚前置）：
  1. L177 建 EventBus（每命令一支进程内事件流；经 RunHandle.stream 交消费方）。
  2. L178 `await self._auditor.ensure_ready()`——audit_log 幂等建表，在 kind 分派之前执行。
  3. L179-209 ask 分支：
     3a. L180 actor 归一——command.actor 或空 `Actor(user_id="", display="")`。
     3b. L181 `who = who_of(actor)`（Actor.who 优先；空则 resolve_actor(user_id) 缺省角色，audit.py L57-59）。
     3c. L182 `run_id = new_run_id()`。
     3d. L186 `seed_messages = await self._seed_messages(command.followup_of)`——followup_of 空则 []；非空读前轮（RunNotFoundError／RunNotSuspendedError 在此抛出，先于 create_run；失败不产生 run 行）。
     3e. L187-190 落 run 行：`_store.create_run(run_id, question, actor.who, followup_of)`——行 status="running"（store.py L143-145）。
     3f. L191-197 审计 run_created：经 `self._audit` 守卫（写口异常转 notice，`_audit` 在 L515-533，本段外）。
     3g. L198-202 `build_graph(self._deps(bus, run_id=run_id), checkpointer=self._saver, four_phase=self._four_phase)`——per-run 模型副本盖章 run_id（`_deps` L339-361，本段外）。
     3h. L203-206 `state = self._initial_state(run_id, command.question, actor.user_id, seed_messages, followup_of)`——status=RUN_RUNNING、budget 字典播种（as_dict）、started/deadline=now_monotonic()+budget.total_seconds（实现 L363-388，本段外）。
     3i. L207 `config = {"configurable": {"thread_id": run_id}}`。
     3j. L208 `self._spawn(graph, state, config, bus, run_id, who=who)`——asyncio.create_task(`_drive`) 后台驱动（`_spawn` L390-410，本段外）。
     3k. L209 返回 `RunHandle(run_id, stream=bus.stream())`。
  4. L210-260 resume 分支：
     4a. L211-213 读 run——`_store.get_run(command.run_id)` 为 None → 抛 RunNotFoundError。
     4b. L214-217 status != RUN_WAITING_ASK → 抛 RunNotSuspendedError。
     4c. L220-223 `_store.mark_running(command.run_id)`（waiting_ask→running 回写，行为约定 8；ValueError 折算为 RunNotSuspendedError——状态行级竞态把守）。
     4d. L224-228 `build_graph(self._deps(bus, run_id=command.run_id), checkpointer=self._saver, four_phase=self._four_phase)`。
     4e. L229 config thread_id=command.run_id。
     4f. L233-235 `await graph.aget_state(config)` 读线程态；`resume_choice_base = len(values.resume_choices or [])`。
     4g. L238-242 `ban_exempt_base` ＝ notices 中 dict 且 type=="ban_exempt" 的计数（豁免审计切片基线）。
     4h. L243-248 `await graph.aupdate_state(config, {"deadline_monotonic": now_monotonic() + self._budget.total_seconds})`——段时限刷新：挂起等人工不计预算、恢复段重新起算（L230-232 注释：原「段步基线 segment_step_base」死字段已删，P-024b C1）；本写只含 deadline 一键，其余预算参数沿用挂起前 checkpoint 原值。
     4i. L249 `choice = command.choice or AskChoice(value="")`。
     4j. L250-259 `self._spawn(graph, Command(resume=choice.as_payload()), config, bus, command.run_id, who=str(run.actor), resume_choice_base, ban_exempt_base)`（as_payload 形＝{"value","approval_id"}，state.py L122-124）。
     4k. L260 返回 RunHandle(run_id=command.run_id, stream=bus.stream())。
  5. L261 未知 kind → `raise ValueError`（兜底）。
- 副作用：emit 无（本段零 bus.emit；事件由后台 `_drive` 与 `_audit` 发出，L>264）；持久化写=run 行（create_run L187-190；mark_running L221）；checkpointer 写=aupdate_state 的 `deadline_monotonic` 一键（L243-248）。
- 返回：RunHandle（run_id＋进程内事件流 AsyncIterator）；终态落库/耗时收束不在本函数（`_drive` L412-511，本段外）——execute 止于 spawn。
- 规则条目：
  - R-I1a-15 受理即返（docstring L176）：execute 同步返回 RunHandle，图在后台任务（`_spawn`→`_drive`）驱动，事件流实时消费。
  - R-I1a-16 ensure_ready 先于一切分派（含未知 kind 的 ValueError 之前，L178 先于 L179/L261）——audit_log 建表每实例至多一次幂等。
  - R-I1a-17 ask 身份两槽口径：who 经 who_of 归一（解决空 actor）；落库 actor 列=actor.who（display 全名），初始状态 actor=actor.user_id（角色键）——两处取不同槽（L188 对 L204）。
  - R-I1a-18 ask 次序：播种校验（followup）→ create_run → 审计 run_created → 建图 → 初始状态 → spawn → 返回——followup 失败（404/409）先于落库，不留空 run 行。
  - R-I1a-19 resume 前置三闸：run 存在（否则 404 异常）→ status==waiting_ask（否则 409 异常）→ mark_running 状态机转移（越界/竞态再折算 409）——三闸齐过才续跑。
  - R-I1a-20 resume 段时限刷新：aupdate_state 只写 deadline_monotonic=now+budget.total_seconds——挂起等人工不计预算、段重新起算（注释 L230-232）。
  - R-I1a-21 resume 审计基线切片：resume_choice_base＝既有 resume_choices 条数、ban_exempt_base＝既有 ban_exempt notice 条数——恢复段审计只补增量（防累计 notices 重放重复行，注释 L236-242）。
  - R-I1a-22 resume 缺 choice → 归一 AskChoice(value="") 照走 spawn——空值合法性下游（收 resume 的图侧）把守，本段不判。
  - R-I1a-23 未知 kind → ValueError（运行时兜底）——正常不可达（RunCommand 构造期 R-I1a-02 已拦截）。
- 耦合：`appv2.runtime.events.EventBus`（＋stream 方法）、`appv2.runtime.audit.who_of`、`appv2.runtime.audit.RunAuditor`（ensure_ready／run_created）、`appv2.runtime.graph.build_graph`、`appv2.runtime.budget.now_monotonic`、`appv2.runtime.state.RunHandle`／`AskChoice`（as_payload）／`RUN_WAITING_ASK`、`appv2.runtime.store.RunStore`（create_run／get_run／mark_running）、`appv2.infra.security.Actor`、`langgraph.types.Command`、checkpointer 线程态方法（aget_state／aupdate_state）。
- 疑点：
  - D-I1a-12 ask 与 resume 的 who 口径不一：ask 走 `who_of(actor)` 归一（缺省角色兜底），resume 直接 `str(run.actor)` 取库内 actor 列（display 全名）——两路审计 who 生成路径不同，代码无说明。
  - D-I1a-13 同步异常路径的 bus 无收束：3d／4a／4b／4c／5 抛异常时 bus 已建（L177）但未 close、stream 未交付调用方（正常路径 close 在 `_drive` finally L511）——异常路径事件流收束语义代码内无说明。
  - D-I1a-14 未知 kind 的 ValueError 殿后至 L261（ensure_ready 之后）：冒烟路径也会先执行建表副作用，然后才拒命令。
  - D-I1a-15 resume 的 who=str(run.actor)：若库行 actor 为空串，审计 who 为空，无 who_of 兜底（与 ask 分支不对称）。
  - D-I1a-16 ask/resume 为两个独立 if（L179/L210）非 elif：第一分支 return 后第二条件恒求值；L261 raise 分支正常不可达（冗余兜底）。
  - D-I1a-17 resume 的线程态读（L233）与 aupdate_state 写（L243）之间无跨进程互斥——mark_running 仅行级把守；多实例并发 resume 的 checkpointer 竞争语义代码内无说明。

---

## 覆盖自检

- def/class 清单差集：无。L1-264 内全部 def/class 共 9 条（`RunCommand`／`RunCommand.__post_init__`／`RunNotFoundError`／`RunNotSuspendedError`／`new_run_id`／`extract_dialogue_from_legacy_history`／`GraphRunExecutor`／`GraphRunExecutor.__init__`／`GraphRunExecutor.execute`），已逐一列条目。边界：L263-264 起为「内部位」节注释头，`_seed_messages`（L265）起不在本报告范围（仅作 caller 锚点引用）。
- 本段 emit 事件名全集：无（L1-264 零 `bus.emit`、零 `bus.close` 调用；bus 只被创建 L177 与交付出流 L209/L260）。段内 import 但段内未使用的事件名常量：`EVENT_BLACKBOX`（L35，消费点在 `_drive` L508）。
- 引用的外部符号全集（本文件内定义的除外）：
  - 段内实际引用：标准库 `uuid.uuid4`（L88）、`asyncio.Task`（L173 注解）、`dataclasses.dataclass`（L58）、`typing.Any`（L99/L146-156/L207 等注解）；`langgraph.types.Command`（L252）；`appv2.infra.db.ConnectionManager`（L145）；`appv2.infra.security.Actor`（L67 注解/L180 构造）、`SecurityService`（L149 注解）；`appv2.runtime.audit.RunAuditor`（L172 构造/L178/L193）、`who_of`（L181）；`appv2.runtime.budget.Budget`（L147/L162）、`now_monotonic`（L246）；`appv2.runtime.context.ContextBuilder`（L148/L163）；`appv2.runtime.events.EventBus`（L177/L209/L260）；`appv2.runtime.graph.build_graph`（L198/L224）；`appv2.runtime.llm.GatewayChatModel`（L144 注解）；`appv2.runtime.state.AskChoice`（L70 注解/L249）、`RunHandle`（L175/L209/L260）、`RUN_WAITING_ASK`（L214）；`appv2.runtime.store.RunStore`（L171；方法 create_run/L187、get_run/L211、mark_running/L221）；`appv2.tools.ToolRegistry`（L143 注解）。
  - 段内 import 但段内未再引用（供 L>264 消费）：标准库 `json`（L21→L493）、`collections.abc` 的 `Awaitable`/`Callable`（L23→L518）；`appv2.runtime.blackbox` 的 `distill`/`pointer`（L32→L490/L509）；`appv2.runtime.context.SYSTEM_PROMPT`（L34→L312/L319/L377）；`appv2.runtime.events.EVENT_BLACKBOX`（L35→L508）；`appv2.runtime.graph.LoopDeps`（L36→L349）；`appv2.runtime.state` 的 `RUN_COMPLETED`/`RUN_FAILED`/`RUN_RUNNING`（L40-42→L283/L382/L431 等）、`AskRequest`（L43→L616 起）、`RunState`（L45→L370/L378）；`appv2.tools.ASK_EXTERNAL_TABLE_APPROVAL`（L49→L577）。
