# 模块划分 · Petro Data Agent V2

> 阶段 2 产物（唯一真源）。原则：深模块；V1 `app/` 与 V2 `appv2/` 双向禁引，共享只走数据面（PG/Neo4j/MinIO）；
> appv2 内四层单向向下：api → runtime → tools → engines（knowledge/query/retrieval）→ infra。
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

## runtime

职责: 有界 agent loop——一轮＝四相位：业务澄清（LLM＋discover 钻取，发射 QuestionGroup
- LLM 触点装配四要素（V2-62 起）：任务动词／题意锚／产出样例／失败反馈——新触点按此审查（装配件：runtime/orientation.py）。

问题组）→工具匹配（子问题→工具/链，闭世界对账收口）→前置条件机（纯固定代码零 LLM，
逐子问题判四态）→批量执行＋LLM 汇总；每用户输入周期 ≤3 轮部分续找（成功子结果不重跑）；
预算与终止；Context Builder＋Manifest＋多轮消息历史簿记（ADR-0006）；Verifier；
run/steps 持久化；SSE 事件流（LangGraph 实现，ADR-0002 三红线；ADR-0004/0005/0006 终态）
目录: `appv2/runtime/`

### 公开接口
```python
class AgentRuntime:
    async def ask(self, q: AskRequest) -> RunHandle: ...        # 建 run，返 run_id＋事件流游标
    async def resume(self, run_id: str, choice: AskChoice) -> RunHandle: ...
class ContextBuilder:
    def compile(self, run_state: RunState) -> CompiledContext: ...   # 确定性管线：消息历史簿记→词典层常驻注入→过滤→排序→预算→引用化
```
step 类型枚举（六值闭世界）：decision/discover/execute/observe/verify/answer；四相位以
step payload 的 phase 字段标注（clarify/toolmatch/precondition/batch）；每步落 step 记录
（Manifest 随模型调用生成；discover 每次落计数埋点：次数/查询词/命中形态）。
QuestionGroup（LangGraph 校验单点）：subtasks[{id/question/ledger_notes/tool/chain}]，
子问题上限 ≤4，ledger_notes 必填（台账注释纪律）。

### 依赖
- 模块: `tools`（只许走 ToolRegistry 公开接口）、`infra`
- 外部: **LangGraph**（ADR-0002：只许本模块内部使用，三红线——LLM 必经 gateway ChatModel adapter；
  state schema 自有；框架类型禁止渗漏出本模块）

### Seam 与测试
- Seam: AgentRuntime.ask（整个系统的 seam）；LLM completer 经 infra adapter；
  **RunCommand（ask/resume）→执行器→RunEvent 为显式接缝（ADR-0003：将来可换队列消费者，接口不变）**
- Adapter: 剧本化 completer（按消息历史形态分流，多轮 replay）
- 测试计划: 有界终止（轮数/发现预算/时长闸）/四相位端到端（分解→过闸四态→批量→失败子集回炉）/
  前置条件机零 LLM 扫描/ASK 挂起恢复/核验拦截无据断言/Manifest 每次模型调用在场/
  消息历史簿记（闸拒负信息在史）/run 状态可恢复

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
- 模块: `runtime`（业务面只许走 AgentRuntime 公开接口；组合根 create_app 例外——装配 GraphRunExecutor/PgCheckpointer/GatewayChatModel，V2-07 按组合缝采纳）、`infra`
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

| 禁止 | 例外 | 理由 |
|---|---|---|
| `appv2` 任何模块引用 `app`（V1）内部；`app` 引用 `appv2` | （无） | Owner 2026-10-08 拍板：共存双跑互不依赖，共享只走数据面 |
| `api` 引用 `runtime` 以外模块 | （无） | 端点薄层，编排语义全在 runtime |
| `runtime` 引用 `tools` 以外引擎（knowledge/query/retrieval） | （无） | agent 与世界的唯一接触面＝ToolRegistry（受控行动链工具侧落位） |
| `tools` 引用 `runtime` | （无） | 单向向下，防环 |
| `knowledge`/`query`/`retrieval` 互引 | `query`→`knowledge`（只许走公开接口） | 未绑定指标降级需 Evidence；其余互禁 |
| 各引擎绕过 infra 直连接外部（litellm/裸 driver/裸 httpx 外部 API） | （无） | B6 出口纪律，V1 先例 |
| `langgraph`/`langchain` 出现在 `runtime` 以外任何模块 | （无） | ADR-0002 红线①：框架只许活在 runtime 内部 |
| LLM 调用绕过 gateway.complete（含经 langchain 自带 provider 直连） | （无） | ADR-0002 红线②：B6 出口纪律 |
| `web/`、`eval/` 引用 `appv2` 模块内部 | tests/ 单模块 seam 级直测（SDD 惯例，infra.md/query.md 等验收表指定）；web/eval 只走 /api/v2 HTTP | spec 模板「单模块行为在模块 seam」＋V1 同先例；跨模块黑盒仍走 HTTP |
