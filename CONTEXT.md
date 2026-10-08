# CONTEXT.md · petro-agent-platform

> 共享术语表（SDD 产物；V1 资产术语以 ontology/ 与 teach 合同册为准，此处只列 V2 新增/变义）。
> 状态：随 V2 阶段 1 逼问持续更新。

## 语义核心（不变量原文唯一出处）

- INV-1 无引用不给数：答案中的每个数/事实断言必须有 fail-closed 校验过的引用，失锚断言剥除并计数。
- INV-2 只读边界：agent 全部工具只读；SQL 经只读账号＋白名单 Schema；无任何写动作。
- INV-3 权限谓词优先：用户筛选条件顶不掉权限/口径谓词（沿用 V1 N7.4b 语义）。
- INV-4 矛盾分源：多来源矛盾数据必须分源列明（各标出处）或显式声明歧义；禁止无出处调和/混写。
- INV-5 审计闭环：每次回答留痕（谁/何时/何输入/何输出/依据口径），审计责任账唯一写口 security.audit（落 audit_log 表，action 恒 `agent_v2.*` 前缀）；run/step 簿记＝过程态留痕，与责任账分工不互替（specs/infra.md 行为约定 3 口径——V2-20 对齐）。

## V2 术语

| 术语 | 定义 |
|---|---|
| **agent loop** | V2 核心执行结构：理解→规划→工具→观察→核验→阐述的有界循环（替代 V1 十七站瀑布） |
| **Harness 编排层** | 持有任务语义的代码层（model 看到什么/能调什么/何时停/交付前过哪些验证），与 Runtime 解耦 |
| **工具（Tool）** | agent 可调用的确定性能力：semantic_query／data_query／doc_retrieve／graph_query，全只读 |
| **Skill** | data_query 的定性——V1 六站链降格为可验证方法资产（模板装配＋三闸＋血缘卡封装在工具内） |
| **Observation** | 工具返回的统一结构：值/来源/版本/时效/适用范围（Knowledge Evidence 形） |
| **计划（plan）** | loop 中模型产出的查询意图（指标槽/时间窗/条数/排名…），经确定性校验后成为 Task State |
| **Context Manifest** | 每次模型调用的输入账目：来源/版本/信任级/选中理由/token/变换——"模型为什么看到这个" |
| **ASK 帧** | 人在回路挂起点：缺参澄清（三选一）或外表越集审批（批准/驳回） |
| **核验步（Verifier）** | loop 内答案交付前检查：每个断言有 Observation 支撑；无支撑→"未找到"，禁止编造 |
| **Knowledge 化** | sem_* 台账从管理面 CRUD 升级为 agent 可消费的 Knowledge（Evidence 结构读接口） |
| **run / step** | 一次提问的执行实例 / loop 内一步（理解/规划/工具/观察/核验/阐述各有 step 记录） |

## V1 沿用术语（不变义）

台账（sem_*）、血缘卡（五要素）、新鲜度闸、在册未绑定降级、fail-closed citation、
合同册（teach 真源）、B6 出口、四层边界（B1–B16）。
