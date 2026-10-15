# 模块划分 · Petro Data Agent V2

> 阶段 2 产物（唯一真源）。原则：深模块；V1 `app/` 与 V2 `appv2/` 双向禁引，共享只走数据面（PG/Neo4j/MinIO）；
> appv2 内四层单向向下：api → runtimev2（重写后的运行时，17 块见下，ADR-0007）→ tools → engines（knowledge/query/retrieval）→ infra。
> 注：模块卡以 `## <名>` 为模块名（spec gate 解析契约），描述语在职责行。

## infra

职责: 从 V1 原样复制的运行基础设施（B6 出口/只读 DB/时钟/审计/配置纪律不带旧业务语义）
目录: `appv2/infra/`

### 公开接口
与 V1 `app/infra` 同形：`config.load_models_config`、`config.load_database_specs`、`config.load_chat_settings`、
`db.session(role)`、`llm_client.complete / embeddings`、`clock.now`、`security.resolve_actor`、
`security.audit`。**只许 appv2 内部消费，不构成跨版本契约。**

### 依赖
- 模块: （无——最底层）
- 外部: PostgreSQL、Redis、MinIO、Neo4j、LLM API（均经 adapter）

### Seam 与测试
- Seam: LLM completer / embedder / 时钟 / DB 会话
- Adapter: 测试桩 completer（caller 分流应答，V1 先例）、LocalHashEmbedder、FakeClock、事务回滚型会话
- 测试计划: 出口唯一性（无 litellm 逃逸）、只读守卫、审计留痕

## knowledge

职责: 把 sem_* 台账（指标/术语/对象/关系/族）读成 agent 可消费的 Knowledge Evidence
目录: `appv2/knowledge/`

### 公开接口
```python
class KnowledgeStore:
    def evidence(self, query: SemanticQuery) -> list[Evidence]: ...
    def metric_by_name(self, name: str) -> Evidence | None: ...
    def aliases(self) -> dict[str, str]: ...          # glossary 别名投影真源（非钉键数，现 12 键）
    def families(self) -> dict[str, list[str]]: ...   # 族标注
```
`Evidence = {element_id, kind, value, source, version, freshness, scope, binding_state}`
（binding_state＝绑定/在册未绑定/届满——agent 现场判断"能不能出数"的依据）

### 依赖
- 模块: `infra`
- 外部: PG sem_* 表（只读）

### Seam 与测试
- Seam: KnowledgeStore（查台账这一可替换面）
- Adapter: InMemoryKnowledgeStore（fixture 快照）
- 测试计划: 命中/未命中/别名归一/届满标注/未绑定状态如实携带

## query

职责: V1 六站链移植——计划确定性校验→模板装配 SQL→三闸→只读执行→血缘卡；新鲜度/降级语义内聚
目录: `appv2/query/`

### 公开接口
```python
class QueryEngine:
    def validate(self, plan: QueryPlan) -> PlanCheck: ...      # 确定性校验（白名单/一致性/窗界）
    def run(self, plan: QueryPlan) -> QueryOutcome: ...         # 权威表+血缘卡 或 闸结果(拦停/降级/缺参/越集)
```
`QueryOutcome` 是联合态：rows+lineage ｜ freshness_block(水位) ｜ unbound_degrade(指标,依据Evidence)
｜ need_clarify(候选窗) ｜ external_table_approval(外表,ASK) ｜ refuse(原因)

### 依赖
- 模块: `infra`、`knowledge`
- 外部: PG agg 三表＋湖表（只读账号）

### Seam 与测试
- Seam: QueryEngine / SQL 执行器
- Adapter: 假执行器（fixture 行集）、V1 题册数值钉死的行为测试
- 测试计划: 三闸/新鲜度改绑/未绑定降级/缺参反问/越集审批——V1 问数组 A~H 族行为原样保留

## retrieval

职责: V1 S4 双路召回＋精排＋生成窗供给＋图谱链移植；供给策略本体化（来源指纹/族/矛盾同窗）
目录: `appv2/retrieval/`

### 公开接口
```python
class RetrievalEngine:
    def retrieve(self, need: RetrievalNeed) -> RetrievalBundle: ...
    def graph(self, need: RetrievalNeed) -> RetrievalBundle: ...   # 图谱面（graph_query 工具消费；失败回退空集不炸链）
```
`RetrievalNeed = {question, anchors, family_hints, budget}`；
`RetrievalBundle = {observations: list[Observation], window_note: str}`——
observations 带 fragment 出处链（fragment→report→library），window_note 如实声明
"召回 N 支/送窗 M 支/矛盾来源已同窗或已列缺位"。

### 依赖
- 模块: `infra`
- 外部: PG kb_* 表、向量服务（embedding 经 infra）、Neo4j

### Seam 与测试
- Seam: RetrievalEngine / embedder
- Adapter: fixture 片段库＋LocalHashEmbedder
- 测试计划: 召回/精排回退/分池/截断显式/同型文档来源标注

## tools

职责: 把 engines 包装成 agent 可调用的只读工具；统一 Observation schema、错误分类、ASK 结果形态；
前置条件机（纯固定代码闸件——V2-34 落位本层，runtime 前置相位逐子问题消费，零 LLM）
目录: `appv2/tools/`

### 公开接口
```python
class ToolRegistry:
    def descriptors(self) -> list[ToolDescriptor]: ...      # 渐进披露：名称/描述/参数schema/只读声明
    async def call(self, name: str, args: dict, ctx: ToolContext) -> ToolResult: ...
```
五工具：`semantic_query(question|element)` → knowledge；
`data_query(plan_draft)` → query（draft 先经 validate）；
`doc_retrieve(question, anchors?, family_hints?)` → retrieval；
`graph_query(question, anchors?)` → retrieval 图谱面；
`table_schema(table?)` → 结构卡发现面（agg 三表＋sem 五账＋kb 片段清单——白名单外
raw/lake 湖表不开放，只读零 SQL；V2-31 新增发现工具）。
`ToolContext = {actor, budget, metric_candidates, approved_tables}`（逐调用上下文——
外表放行态落 approved_tables，A2 裁决：不走引擎 approved_tables、不重排计划）。
`ToolResult = {observations, status: ok|failed|ask, ask?: AskFrame}`，全部只读（INV-2）。

### 依赖
- 模块: `knowledge`、`query`、`retrieval`（只许走其公开接口）、`infra`
- 外部: （无新增）

### Seam 与测试
- Seam: ToolRegistry.call（agent 与世界的唯一接触面）
- Adapter: 假引擎
- 测试计划: 只读声明不可违背/错误分类（可重试|修参|拒答）/ASK 帧形态/参数 schema 校验

## understanding

职责: 读题——装配任务书 → 模型读 → 解析；定路由（模型判、程序机械分派、直答过结构核验）
目录: `appv2/runtimev2/understanding/`

### 公开接口
```python
def interpret(state: RunState) -> Understanding | Direct: ...
```

### 依赖
- 模块: `gate`、`prompts`、`parsing`、`gateway_adapter`、`state`；`tools`（结构卡发现面——直答结构核验读它，只经其公开面）
- 外部: （无——模型调用经 `gateway_adapter`）

### Seam 与测试
- Seam: 决策出口（模型应答 → 定型结论）
- Adapter: 剧本化 completer
- 测试计划: 直答／完整流程分流（拿不准走完整流程）；直答含数据或事实断言即退回；候选须出自名录

## clarification

职责: 澄清——意图澄清、分解问题、反问挂起与恢复
目录: `appv2/runtimev2/clarification/`

### 公开接口
```python
def clarify(state: RunState) -> ClarifyOutcome: ...
```

### 依赖
- 模块: `prompts`、`parsing`、`gateway_adapter`、`state`
- 外部: （无）

### Seam 与测试
- Seam: 反问卡载荷（挂起／恢复）
- Adapter: 剧本化 completer
- 测试计划: 挂起恢复（等待不计轮／恢复重取易变环境量）；连续澄清上限；失败子集回炉

## tool_matching

职责: 工具匹配——子问题 → 工具的提议与闭世界对账；「出数只认现行口径」结构约束落点
目录: `appv2/runtimev2/tool_matching/`

### 公开接口
```python
def match(state: RunState) -> ToolPlan | ToolMatchRejection: ...
# ToolPlan            = {matches: list[SubtaskMatch]}（与子问题一一对应）
# ToolMatchRejection  = {reasons: list[MatchReason]}（结构化拒因——回喂重配，非终局）
```

### 依赖
- 模块: `state`、`parsing`、`prompts`、`gateway_adapter`；`tools`（只许走其公开面）
- 外部: （无）

### Seam 与测试
- Seam: 工具目录（`tools` 公开面）
- Adapter: 假工具目录
- 测试计划: 每子问题恰配一条、编号对得上；旧名经本体账本归一后才出数

## preconditions

职责: 前置检查——逐子问题三态闸（放行／拒答／等用户），纯程序零 LLM，注记并入放行；**8 个判定位全部为结构／机械分派**（语义类结论——废弃词闸「提及 vs 执行」与口径归一——由 `tool_matching` 的模型产出，本块只消费；Owner 2026-10-15 裁决 #12／#13）
目录: `appv2/runtimev2/preconditions/`

### 公开接口
```python
def gate_all(state: RunState) -> list[SubtaskVerdict]: ...   # 逐子问题三态；与核验的 Verdict 区分（同名不同物）
```

### 依赖
- 模块: `state`；`tools`（前置条件机本体在 tools 侧，只经其公开面）
- 外部: （无）

### Seam 与测试
- Seam: 闸件本体（在 `tools` 侧，可替换）
- Adapter: 假闸件
- 测试计划: 三态判定；固定序＋命中即停；**全结构项**（越集／绑定／新鲜度／单井）

## execution

职责: 批量执行——发现、执行、观察回流；工具调用统一出口；只读并行
目录: `appv2/runtimev2/execution/`

### 公开接口
```python
def execute(state: RunState) -> ExecutionOutcome: ...
# ExecutionOutcome = {observations: list[Observation], subtasks: list[SubtaskExec]}
# SubtaskExec = {subtask_id, exec_status: ok|failed|need_input, answered: bool, error, row_count, ref}
#   —— **exec_status（执行状态）与 answered（是否真答上）分开记**（Owner 裁决 §13-Q-C）
```

### 依赖
- 模块: `state`、`transport`、`persistence`（大结果引用落盘，只经其公开面）；`tools`（只许走其公开面）
- 外部: （无）

### Seam 与测试
- Seam: 工具调用（`tools` 公开面）
- Adapter: 假引擎
- 测试计划: 成功不重跑、每次记账；只重做失败子集；只读并行无副作用

## answering

职责: 作答——起草（指令装配＋材料渲染）、真流式收口、引用落账
目录: `appv2/runtimev2/answering/`

### 公开接口
```python
def answer(state: RunState) -> AnswerDraft: ...
```

### 依赖
- 模块: `context`、`prompts`、`gateway_adapter`、`state`、`transport`（text 帧的增量发射，只经其公开面）
- 外部: （无）

### Seam 与测试
- Seam: 起草出口（增量文本 → 事件帧）
- Adapter: 剧本化 completer
- 测试计划: 每句带出处；一段段推（真流式）；结构化缺口；被拒／缺失如实列

## verification

职责: 核验——断言级核验（零模型）、归属审、矛盾分源、verdict
目录: `appv2/runtimev2/verification/`

### 公开接口
```python
def verify(state: RunState) -> Verdict: ...
```

### 依赖
- 模块: `state`、`transport`（verdict/notice 帧的发射，只经其公开面）
- 外部: （无）

### Seam 与测试
- Seam: 核验接缝（草稿＋观察 → verdict）
- Adapter: fixture 草稿与观察
- 测试计划: 无据句改写；矛盾分列；子串假阳／假阴（数值边界、全角标点）；精确率／召回率（人工标注）

## state

职责: 状态与限额——运行状态（53 字段重划）、Manifest、请求回执数据类、闭世界常量；限额参数与触界**判定**（纯计算，不写状态）
目录: `appv2/runtimev2/state/`

### 公开接口
```python
class RunState: ...          # 字段形状（被全体 import；不含行为）
class Manifest: ...          # 模型调用 Manifest 形状（含 as_dict 投影）
class AskRequest: ...        # 受理载荷（三形态闭世界：提问／重连／追问续会话）
class AskChoice: ...         # resume 载荷（kind 闭世界：clarify／external_table_approval）
class RunHandle: ...         # 受理回执（run_id／stream／cursor）
class Budget: ...            # 限额参数表（键集闭世界；数值不落本卡）
class Convergence: ...       # 触界判定结果形状（hit／notice）
class LimitHit: ...          # 触界命中项（limit 闭世界／used／cap）——Convergence.hit 的元素类型
# 闭世界常量族：STEP_KINDS／RUN_STATUS_KINDS／INTENT（三族都取自 RunState 字段取值域）
# 触界**判定**（纯函数——不改入参、不写状态）；数值真源＝recon/K R-K-72…R-K-78 ＋ walk/裁决表 §06-A
def check_limits(state: RunState) -> Convergence: ...
```

> **`converge` 归属裁决（2026-10-15，L0）**：本卡与 `## bookkeeping` 卡原各列一个 `converge`——**判定**归本块（更名 `check_limits`，纯计算）｜**落地写入**（`budget_hit`／`notices`／`status`／`next_intent` 六键）归 `bookkeeping` 的唯一写口 `converge`（**无回值**）。一物一处，避免双写口漂移。
> **notice 分型闭世界不落本卡（2026-10-15，L0）**：通知类型（`notice.type`）属**帧载荷面**，闭世界归 `## transport`（事件名闭世界亦在该卡）；本块只定义「触界注记必须恰三键」的形状，不复述类型取值。

### 依赖
- 模块: （无——runtimev2 内最底层）
- 外部: `infra`

### Seam 与测试
- Seam: 数据形状本身（纯结构）
- Adapter: fixture 状态工厂
- 测试计划: 字段读写矩阵（`synth/S5`）逐字段在场；限额常量单点、禁散落

## orchestration

职责: 编排与执行——图装配与路由、命令受理与执行器、挂起恢复、**检查点 saver 组合**（LangGraph PG saver 实现——组合 `persistence` 的框架无关行级口，不直连表）
目录: `appv2/runtimev2/orchestration/`

### 公开接口
```python
class AgentRuntime:
    async def ask(self, q: AskRequest) -> RunHandle: ...
    async def resume(self, run_id: str, choice: AskChoice) -> RunHandle: ...
```

### 依赖
- 模块: `state`、`bookkeeping`、`transport`、`persistence`、`infra`（身份缝与审计唯一写口，只经其公开面），以及七个业务相位
- 外部: **LangGraph**（ADR-0002 红线①：只许本块内使用；state schema 自有；框架类型不得外泄）

### Seam 与测试
- Seam: **RunCommand（ask/resume）→ 执行器 → 事件流**（将来换队列消费者，接口不变）
- Adapter: 假执行器
- 测试计划: 有界终止（轮／发现／时长）；挂起恢复；相位顺序只由本块决定

## bookkeeping

职责: 公共簿记——全节点共享的写入面：步记录、序号、**对话链与对话层追加**、过程档案、通知、触界收敛、完成收口、节点调模型单点、工具上下文装配、结果投影
目录: `appv2/runtimev2/bookkeeping/`

### 公开接口
```python
# ── 共享写口（唯一入口；相位禁直写）────────────────────────
def record_step(state, *, kind, title, status="ok", payload=None, manifest=None) -> StepRecord: ...  # status 闭世界 ok/failed/refused（由调用方如实给，本块不猜）
def next_seq(state) -> int: ...
def append_message(state, *, role, content) -> None: ...     # 对话链（messages）追加（只追加）
def append_dialogue(state, *, role, content, origin) -> None: ...  # 对话层（dialogue）追加（origin 闭世界）
def note(state, *, phase, title, digest) -> None: ...        # 过程档案（process_notes）续写（digest 有界）
def notice(state, *, type, gates=(), content) -> None: ...   # 通知追加（type 闭世界）
def set_intent(state, intent: str) -> None: ...              # next_intent 唯一写口（闭世界越界即拒；路由决策仍在 orchestration）
# ── 触界收敛与完成收口 ────────────────────────────────────
def converge(state) -> None: ...        # 落地写入（判定归 `state.check_limits`；无回值——写 budget_hit／notices／正文／draft_kind／status／next_intent）
def direct_answer(state, text) -> None: ...                  # 确定性直答标记（免起草免核验的收口旁路）
# ── 调模型与工具面 ────────────────────────────────────────
def call_model(state, caller: str, messages) -> str: ...   # 节点侧调模型单点：从 state 取 run_id → 调 gateway_adapter.complete → 向节点只回 content；回执的用量/归因面归本块记账
def tool_context(state) -> ToolContext: ...
def result_projection(result) -> dict: ...
```

> **卡级修正（2026-10-15，L0，随 bookkeeping 规格起草）**：原公开面只列五件，而职责行自称「全节点共享的写入面」——**多个共享写口没有承接函数**（现状证据 `synth/S5-RunState字段矩阵.md` §四【结构-2】列 `notices`／`steps`／`next_intent` 三件全节点共享写口；同文件 §二观察另把 `messages` 并列）。本批按「一物一处」补全：**对话链／对话层／过程档案／通知四类追加各设唯一入口**，加 `direct_answer`（完成收口的直答旁路）、`result_projection`（职责行已点名的「结果投影」）与 `set_intent`（`next_intent` 的唯一写口——「写字段」与「做路由决策」分开，决策仍在 `orchestration`）。依赖行同批补：**类型与常量形状另引 `tools`／`persistence`／`transport` 三块（只引形状，不引行为）**——原依赖行只列两块，与公开面（返回 `ToolContext`／`StepRecord`、用 `NOTICE_TYPES`）不符。

### 依赖
- 模块: `state`、`gateway_adapter`（**运行逻辑**）；`tools`、`persistence`、`transport`（**类型与常量形状面**——ToolContext 类型、StepRecord 形状、NOTICE_TYPES 常量；只引形状，不许引其行为：不调工具、不落盘、不发帧）
- 外部: （无）

### Seam 与测试
- Seam: 写口（全节点同一入口）
- Adapter: 内存写口替身
- 测试计划: 每个节点都经同一写口（禁旁路直写）；序号单调；触界即收敛交付（不静默截断）

## prompts

职责: 指令与提示词——各相位提示词合同常量与各轮指令装配（只出文本，不做判断）
目录: `appv2/runtimev2/prompts/`

### 公开接口
```python
# 合同常量 ＋ 各轮装配函数（纯文本进出）
def assemble_task_book(state: RunState) -> str: ...
def assemble_answer_prompt(state: RunState) -> str: ...
```

### 依赖
- 模块: `state`
- 外部: （无）

### Seam 与测试
- Seam: 装配函数（纯文本输入输出）
- Adapter: 固定 fixture 状态
- 测试计划: 每轮指令在位；题意锚行；样例固定集；不夹带程序判断

## parsing

职责: 解析与发射——模型输出解析、发射 schema 校验、子任务与问题组载荷定型
目录: `appv2/runtimev2/parsing/`

### 公开接口
```python
def parse_understanding(text: str) -> Understanding | Direct | None: ...
def parse_question_group(text: str) -> QuestionGroup | None: ...
```

### 依赖
- 模块: `state`
- 外部: （无）

### Seam 与测试
- Seam: 解析入口（外部文本 → 定型载荷）
- Adapter: 文本 fixture 集
- 测试计划: 缺字段／超限／引号异常分支；同类行多次出现不静默覆盖

## context

职责: 上下文——材料段渲染、过程档案（有界摘要）、术语表常驻注入、对话链追加
目录: `appv2/runtimev2/context/`

### 公开接口
```python
def compile(state: RunState) -> CompiledContext: ...
```

### 依赖
- 模块: `state`；`tools`（台账只读经其公开面，见边界规则）
- 外部: （无）

### Seam 与测试
- Seam: 上下文编译（确定性管线）
- Adapter: fixture 材料集
- 测试计划: 每次模型调用都有 Manifest；材料标来源；配额与截断显式

## transport

职责: 事件通路——事件名闭世界（9 类）、**帧载荷分型闭世界（含 `notice.type`）**、事件总线、帧通路与断线续推
目录: `appv2/runtimev2/transport/`

### 公开接口
```python
class SseEvent:                  # 帧（wire 面单元）：{seq: int, event: str, data: dict}
class EventBus:                  # per-run 总线（编排块持有、注入各相位——RunState 必须保持 JSON 可投影，故总线不挂在状态上）
    def emit(self, name: str, payload: dict) -> SseEvent: ...
    def stream(self, cursor: int = 0) -> AsyncIterator[SseEvent]: ...   # seq 即断线游标（全流单调；cursor＝下一帧 seq，排他）
    def close(self) -> None: ...
    @property
    def closed(self) -> bool: ...
def envelope(frame: SseEvent) -> str: ...      # 帧信封字节形："id: …\nevent: …\ndata: …\n\n"
# 闭世界常量族：EVENT_KINDS（runtime 九类）／WIRE_FRAMES（session/done/error）／
#   NOTICE_TYPES（通知类型，取值真源＝本卡所指规格）／VERDICT_SUBTYPES（verify/final）／ASK_FRAME_KINDS（clarify/external_table_approval）
```

> **卡级修正（2026-10-15，L0，随 transport 规格起草）**：原「`def emit(state, name, payload)`」是**现状形状的草稿**——`RunState` 必须保持 JSON 原语可投影（见 `specs/state.md` 行为 3），**总线不能挂在状态上**；故公开面收正为 **per-run `EventBus`**（编排块持有，与现状 `deps.bus.emit` 同形），`SseEvent` 由「载荷别名」收正为**帧对象**（`{seq, event, data}`）。
> **归位登记（2026-10-15，L0）**：`notice.type` 的**取值闭世界在本卡**（现状该值散落各处、无闭世界常量，属历史缺陷）——`transport` 规格定稿时须立该闭世界并**落定取值真源**；`state` 卡只定义「触界注记恰三键」的形状，不复述取值。

### 依赖
- 模块: `state`
- 外部: （无）

### Seam 与测试
- Seam: 帧出口（事件 → wire 帧）
- Adapter: 内存帧收集器
- 测试计划: 九类闭世界；**帧载荷分型闭世界（含通知类型；`state` 侧只定义「触界注记恰三键」的形状，不承载取值）**；游标全流单调；重放不位移

> **归位登记（2026-10-15，L0）**：`notice.type` 的**取值闭世界在本卡**（现状该值散落各处、无闭世界常量，属历史缺陷）——`transport` 规格定稿时须立该闭世界并**落定取值真源**；`state` 卡只定义「触界注记恰三键」的形状，不复述取值。

## persistence

职责: 存储归档——运行记录、检查点**表与读写入口**、黑匣子（只追加）、审计唯一写口、**大结果原文的引用载体**（可寻址 handle）
目录: `appv2/runtimev2/persistence/`

### 公开接口
```python
class RunStore:
    def save(record) -> None: ...          # 统一落盘入口（run 行／步记录／黑匣子；只追加面见卡注）
    def load(run_id: str) -> RunState: ...          # 检查点恢复（跨进程重放）
    def run(run_id: str) -> RunRecord | None: ...
    def steps(run_id: str) -> list[StepRecord]: ... # seq 升序
    def blackbox(run_id: str) -> BlackBox | None: ...
    def put_ref(blob: bytes) -> BlobRef: ...        # 大结果原文的引用载体（可寻址 handle）
    def read_ref(handle: str) -> bytes: ...
    def ensure_tables() -> None: ...                # 幂等建表

# 检查点三表的**框架无关行级读写口**（编排块的 LangGraph saver 组合它，不直连表）
def put_checkpoint_rows(rows) -> None: ...
def checkpoint_rows(thread_id: str) -> list[CheckpointRow]: ...
def checkpoint_blobs(thread_id: str, checkpoint_id: str) -> list[CheckpointBlobRow]: ...
def checkpoint_writes(thread_id: str, checkpoint_id: str) -> list[CheckpointWriteRow]: ...
def delete_thread(thread_id: str) -> None: ...

def audit(record) -> None: ...             # 唯一写口＝security.audit（B12）
```

> **三处卡级澄清（2026-10-15，L0，随 persistence 规格起草）**：
> ① **框架类型不进本块**——`langgraph` 的 PG saver（`BaseCheckpointSaver` 实现，需框架类型）归 `## orchestration`（ADR-0002 红线①／R5b 只许框架活在编排块内）；**本块出框架无关的检查点三表行级读写口**，编排块 saver **组合本口、不直连表**。
> ② **「只读 DB」的准确含义**——**业务数据面只读**（INV-2 全程只读）；**簿记表 `agent_v2_*` 是本块唯一写面**（表名前缀隔离）。
> ③ **公开类型的字段形状以 `specs/persistence.md` 的接口定义为准**（卡面只列类名与签名概要；字段形状、枚举闭世界、断言在规格里）——涉及 `RunRecord`／`StepRecord`／`BlackBox`／`BlobRef`／`CheckpointRow`／`CheckpointBlobRow`／`CheckpointWriteRow`／`AuditRecord` 八类。

### 依赖
- 模块: `state`
- 外部: `infra`（DB 会话／时钟／审计出口）、PostgreSQL

### Seam 与测试
- Seam: 存储入口（换载体不改调用面）
- Adapter: 内存 store／假检查点
- 测试计划: 只追加不原地改；恢复可重放；审计四要素（主体与范围／意图与授权／执行事实／结果与证据）

## gateway_adapter

职责: 网关桥——模型调用唯一出口桥、限流退避、测试替身、评测时钟
目录: `appv2/runtimev2/gateway_adapter/`

### 公开接口
```python
class ModelReply:                # 一次模型调用的回执（{content, caller, run_id, alias, prompt_tokens,
                                 #   completion_tokens, cached_tokens, usage_estimated, duration_ms, error}）
async def complete(messages, *, caller: str, run_id: str) -> ModelReply: ...
class ScriptedCompleter:         # 测试替身（**同面**：async complete ＋ counts／messages_of 观测面）
EVAL_FROZEN_DATE_DEFAULT: date   # 缺省冻结日（取值真源见规格，不落本卡）
EVAL_FROZEN_DATE_REAL: str       # 显式走真实时钟的唯一取值
def frozen_date() -> date: ...   # 评测冻结「今天」（未设/空串＝缺省冻结日；real 须显式；非法抛错）
```

> **卡级修正（2026-10-15，L0，随 gateway_adapter 规格起草——兑现织网挂账）**：原「`def complete(messages, caller) -> str`」是**按卡面收窄的替身草稿**。正式面收正三处：① **async**（真实 I/O，运行时是 async；同步桥会阻塞事件循环）；② **返回 `ModelReply` 而非裸 `str`**——调用记账要 `cached_tokens`／token 计数／服务别名／时长（钉 `pin-25`），裸串承载不了；③ **`alias` 与自由 `params` 不进公开面**（模型调参在本块内单点，服务别名由路由决定、随回执返回）——**`run_id` 进面**（每次调用盖章，计费可对账）。同批回写：替身 `appv2/runtimev2/gateway_adapter/fake.py` ＋ 包根 `__init__.py` 导出（「两边不许脱节」）；随规格同步维护的看守件＝`tests/runtimev2/test_gateway_adapter_fake.py`。

### 依赖
- 模块: （无）
- 外部: `infra`（`llm_client`／`gateway.complete` 唯一出口，B6）

### Seam 与测试
- Seam: 模型出口（换供应商不改调用面）
- Adapter: 剧本化 completer（per-caller 分流）、评测时钟
- 测试计划: 出口唯一（无旁路）；限流分类不误伤；记账 caller 归因逐调用保留

## gate

职责: **安全阀**——注入／外发／写意图的词面快路径（命中即不放行；**不承载红线**，只读硬保证在执行层）。（**废弃词闸已移出本模块**——判断归 `tool_matching` 的模型产出、分派归 `preconditions` 判定序第 1 位；Owner 2026-10-15 裁决 #12）
目录: `appv2/runtimev2/gate/`

### 公开接口
```python
def screen(text: str) -> Refusal | None: ...              # 安全阀：明显中招／越界早退
def apply_term_verdict(verdict) -> Disposition: ...        # 废弃词闸：模型结论入、机械分派出
```

### 依赖
- 模块: `state`
- 外部: （无）

### Seam 与测试
- Seam: 结论入口（模型结论 → 分派）
- Adapter: 固定词表 fixture
- 测试计划: 安全阀明显中招即拒（**漏判由执行层兜，不靠它**）；废弃词闸**程序不做语义判断**（只收模型结论）；「出数只认现行口径」由 `tool_matching` 守

## api

职责: /api/v2/chat/* 薄端点——鉴权、参数校验、SSE 事件桥接
目录: `appv2/api/`

### 公开接口
```
POST /api/v2/chat/asks            → SSE 事件流（入参三形态：question 提问｜resume_run_id 重连｜
                                    question＋followup_run_id 追问续会话——前轮须 completed，
                                    前轮消息历史随追问进新 run；重连/追问互斥同 409）
POST /api/v2/chat/runs/{run_id}/resume   → 澄清/审批选择后续跑
GET  /api/v2/chat/runs/{run_id}          → run 状态＋steps（含 payload：相位标注/discover
                                    计数埋点/Manifest）＋Manifest 摘要
```
事件九类闭世界：step/text/tool/observation/ask/verdict/citation/notice/blackbox（V1 wire 形兼容＋
loop 步/观察新形态——V2-36 终态口径，ADR-0004 拍板 5 演进位；blackbox＝V2-54 黑匣子
收口指针——V2-55 起蒸馏全文入库 agent_v2_blackbox，帧只收录瘦指针；完整面经
tools/run_replay／RunStore.get_blackbox 读库，取证面）。

### 依赖
- 模块: `orchestration`（业务面只许走其公开接口；组合根 create_app 例外——装配执行器/检查点/网关模型，V2-07 按组合缝采纳）、`infra`
- 外部: （无）

### Seam 与测试
- Seam: HTTP 接口（tests/api 接口级测试，不起真实端口）
- Adapter: FastAPI TestClient
- 测试计划: 端点契约/SSE 帧形/断线游标续传/错误码

## 页面映射

| 页面 | 数据需求 | 提供接口(模块) |
|---|---|---|
| A1 问一问 | 提问→SSE 事件流（loop 步视图＋答案＋引用） | `api` POST /api/v2/chat/asks |
| A1 问一问 | 澄清/审批选择后续跑 | `api` POST /api/v2/chat/runs/{run_id}/resume |
| A1 问一问 | run 历史/步详情回看 | `api` GET /api/v2/chat/runs/{run_id} |
| B 系管理面 | （无变化——继续走 V1 端点） | — |

## 边界规则

> 阶段 6 边界闸的唯一事实来源；每条禁令都必须能落成 CI 机器检查（ADR-0007 落位批，**R1–R6** 为 runtimev2 内部约束）。

| 禁止 | 例外 | 理由 |
|---|---|---|
| `appv2` 任何模块引用 `app`（V1）内部；`app` 引用 `appv2` | （无） | Owner 2026-10-08 拍板：共存双跑互不依赖，共享只走数据面 |
| `api` 引用 `orchestration` 以外模块 | （无） | 端点薄层，编排语义全在运行时 |
| **R6** `runtimev2` 各块引用 `tools` 以外引擎（knowledge/query/retrieval） | （无） | agent 与世界的唯一接触面＝工具注册表（受控行动链工具侧落位）；对应闸：`tools/importlinter_v2.toml` R6 契约（ADR-0007 落位批） |
| `tools` 引用 `runtimev2` | （无） | 单向向下，防环 |
| `knowledge`/`query`/`retrieval` 互引 | `query`→`knowledge`（只许走公开接口） | 未绑定指标降级需 Evidence；其余互禁 |
| 各引擎绕过 infra 直连接外部（litellm／裸 driver／裸 httpx 外部 API） | （无） | B6 出口纪律，V1 先例 |
| `langgraph`／`langchain` 出现在 `runtimev2.orchestration` 以外任何模块 | （无） | ADR-0002 红线①：框架只许活在编排块内（ADR-0007 落位） |
| **R8** `preconditions`／`verification`／`execution` 引 `appv2.runtimev2.gateway_adapter`（**零 LLM 面**：这两块的铁律是不调模型；R7 只禁「直引 infra」，不禁「经 gateway_adapter 调模型」，故单列） | （无） | 零模型铁律（ADR-0005；`walk/12` Q-A／`walk/15` A）；对应闸：`tools/importlinter_v2.toml` R8 契约 |
| **R7** `runtimev2` 各块（除 `gateway_adapter`）直引 `appv2.infra.llm_client`——模型只经 `gateway_adapter` | （无） | ADR-0002 红线②：模型出口唯一；B6 契约只禁 litellm 出 infra，**不含**「绕过 `gateway_adapter` 直引」这一面，故单列 R7（对应闸：`tools/importlinter_v2.toml` R7 契约） |
| `web/`、`eval/` 引用 `appv2` 模块内部 | tests/ 单模块 seam 级直测（SDD 惯例）；web/eval 只走 /api/v2 HTTP | spec 模板「单模块行为在模块 seam」＋V1 同先例 |
| **R1** 七个业务相位（`understanding`／`clarification`／`tool_matching`／`preconditions`／`execution`／`answering`／`verification`）之间互相 import | 只经 `state`（数据形状）与 `orchestration`（编排接口） | 相位要能单独测；顺序由编排层定（ADR-0007 同时裁决 3） |
| **R2** 业务相位 import 九个公共层块（`state`／`orchestration`／`bookkeeping`／`prompts`／`parsing`／`context`／`transport`／`persistence`／`gateway_adapter`）的深层子模块 | （无） | 稳定接口：公共面只经各块包根，深层实现属私有 |
| **R3** `parsing`／`prompts` import `state` 以外的 runtimev2 块 | （无） | 两者是「纯文本与纯解析」，不感知运行状态机 |
| **R4** `state` import runtimev2 内任何其它块 | （无） | 最底层数据形状，防环 |
| **R5** `runtimev2` 任何块引用旧 `appv2.runtime` | （无） | 新旧不互咬；旧码只作备份（ADR-0007） |
