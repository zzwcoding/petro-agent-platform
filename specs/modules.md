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
- 模块: `context`、`prompts`、`gateway_adapter`、`state`
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
- 模块: `state`
- 外部: （无）

### Seam 与测试
- Seam: 核验接缝（草稿＋观察 → verdict）
- Adapter: fixture 草稿与观察
- 测试计划: 无据句改写；矛盾分列；子串假阳／假阴（数值边界、全角标点）；精确率／召回率（人工标注）

## state

职责: 状态与限额——运行状态（53 字段重划）、Manifest、请求回执数据类、常量；限额机制
目录: `appv2/runtimev2/state/`

### 公开接口
```python
class RunState: ...          # 字段形状（被全体 import；不含行为）
class Manifest: ...
# 限额机制（触界收敛）；数值以 walk/裁决表 §06-A 统一预算表为唯一真源
def converge(state: RunState) -> Convergence: ...
```

### 依赖
- 模块: （无——runtimev2 内最底层）
- 外部: `infra`

### Seam 与测试
- Seam: 数据形状本身（纯结构）
- Adapter: fixture 状态工厂
- 测试计划: 字段读写矩阵（`synth/S5`）逐字段在场；限额常量单点、禁散落

## orchestration

职责: 编排与执行——图装配与路由、命令受理与执行器、挂起恢复
目录: `appv2/runtimev2/orchestration/`

### 公开接口
```python
class AgentRuntime:
    async def ask(self, q: AskRequest) -> RunHandle: ...
    async def resume(self, run_id: str, choice: AskChoice) -> RunHandle: ...
```

### 依赖
- 模块: `state`、`bookkeeping`、`transport`、`persistence`，以及七个业务相位
- 外部: **LangGraph**（ADR-0002 红线①：只许本块内使用；state schema 自有；框架类型不得外泄）

### Seam 与测试
- Seam: **RunCommand（ask/resume）→ 执行器 → 事件流**（将来换队列消费者，接口不变）
- Adapter: 假执行器
- 测试计划: 有界终止（轮／发现／时长）；挂起恢复；相位顺序只由本块决定

## bookkeeping

职责: 公共簿记——全节点共享的写入面：步记录、序号、触界收敛、完成收口、节点调模型单点、工具上下文装配、结果投影
目录: `appv2/runtimev2/bookkeeping/`

### 公开接口
```python
def record_step(state, **payload) -> None: ...
def next_seq(state) -> int: ...
def converge(state) -> Convergence: ...
def call_model(state, caller: str, messages) -> str: ...
def tool_context(state) -> ToolContext: ...
```

### 依赖
- 模块: `state`、`gateway_adapter`
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

职责: 事件通路——事件名闭世界（9 类）、事件总线、帧通路与断线续推
目录: `appv2/runtimev2/transport/`

### 公开接口
```python
def emit(state, name: str, payload: dict) -> None: ...
# 帧序列（seq 即断线游标）
```

### 依赖
- 模块: `state`
- 外部: （无）

### Seam 与测试
- Seam: 帧出口（事件 → wire 帧）
- Adapter: 内存帧收集器
- 测试计划: 九类闭世界；游标全流单调；重放不位移

## persistence

职责: 存储归档——运行记录、检查点、黑匣子（只追加）、审计唯一写口、**大结果原文的引用载体**（可寻址 handle）
目录: `appv2/runtimev2/persistence/`

### 公开接口
```python
class RunStore:
    def save(...) -> None: ...
    def load(run_id: str) -> RunState: ...
def audit(...) -> None: ...     # 唯一写口＝security.audit（B12）
```

### 依赖
- 模块: `state`
- 外部: `infra`（只读 DB／审计出口）、PostgreSQL

### Seam 与测试
- Seam: 存储入口（换载体不改调用面）
- Adapter: 内存 store／假检查点
- 测试计划: 只追加不原地改；恢复可重放；审计四要素（主体／意图／事实／结果）

## gateway_adapter

职责: 网关桥——模型调用唯一出口桥、限流退避、测试替身、评测时钟
目录: `appv2/runtimev2/gateway_adapter/`

### 公开接口
```python
def complete(messages, caller: str) -> str: ...
```

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
