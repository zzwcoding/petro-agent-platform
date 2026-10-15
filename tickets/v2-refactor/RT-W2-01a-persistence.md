# RT-W2-01a · persistence——V2 存储归档（-A：骨架＋接口＋落盘读回主干）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/persistence.md`（状态「已定稿」——前置满足）
Touches modules: `persistence`（本票建 persistence 本体骨架与公开面：`RunStore`／五张行投影／检查点三表行级口／`AuditRecord`；规格「触及的模块」表另声明 state／execution／orchestration 三关联侧，归各自票承接）
波次: W2（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W2 行：纯件层，只依赖 state/infra——本波出口判据「解析异常分支不静默；帧/游标单调；只追加可重放；模型出口唯一＋替身可注入」，本块承担「只追加可重放」半句）
施工队: A 队（eng/03 §五 终表 W2 行 A 队列＝「persistence／transport／prompts／parsing」，分配理由整行原文：「出口/计费/替身＝慢漏型缺陷，必须稳」）｜复审强度: 100%（eng/03 §五：A 队收波 100% 过独立复审；复审网在 L0 直派）
前置: ① 规格定稿（`specs/persistence.md` 已定稿——已满足）；② 波次前置：**W1 state 收波**（eng/03 §一依赖图：persistence → state）
阻塞: 无（W2 内各块互零依赖）｜被阻塞: `RT-W2-01b-persistence.md`（同包顺序施工——-b 前置＝-a 收票）；W3 收波判据的一部分（间接）；编排块（W5）消费本块检查点三表行级口

## 任务

按 `specs/persistence.md` 新建 `appv2/runtimev2/persistence/`：一次运行的**落盘与读回真源**——运行记录、检查点、黑匣子（只追加）、审计留痕、大结果原文的引用载体——**业务数据零写入（INV-2），簿记表是唯一写面**。

**本票＝persistence 的 -A 票（骨架＋接口＋落盘读回主干＋本块全部 3 条 pin 行）**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **20 行**，超 15 行上限 → 切 -A／-B 两票。本票收 **10 行**＝规格表第 1–5、9、10、11、12、15 行（三类落盘语义／只追加无改写路径／状态机把守／读回可重放／黑匣子首写为准／步记录保真与引用往返／旧记录如实读入）＋ **3 条 pin 行全量**（pin-12／pin-28／pin-30，逐字转抄见「测试网钉」节）；剩余 **10 行**＝规格表第 6、7、8、13、14、16、17、18、19、20 行（守门与红线面／元／边界·保留集）归 `RT-W2-01b-persistence.md`。两票同包**顺序施工**（同包不并行）：本票出骨架与公开面、落盘读回主干与全部 pin 行；-b 只填守门与红线行为簇、不另立第二套形状。

**骨架／接口归属（切分注）**：`RunStore`（落盘入口／读回入口／引用载体／幂等建表）＋五张行投影＋检查点三表行级读写口＋`AuditRecord` 签名（真源 `recon/J` 表事实）全在本票——-b 不得改形状（改形状＝回本票或回设计仓）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （5 份）`specs/persistence.md` 全文（十节版式）；`specs/modules.md` `## persistence` 卡（签名以卡为准）；`specs/state.md`（`RunState` 形状与 `RUN_STATUS_KINDS`／`STEP_KINDS` 闭世界真源——`load` 返回类型与状态机取值域）；`docs/runtime-refactor/recon/J-存储留痕与网关缝.md`（本块表事实与常量真源）；`docs/runtime-refactor/walk/16-收尾-归档.md`（Owner 裁决「只追加、不原地改」§七 Q-B）。本票「测试网钉」「织网义务」两节已把所引行逐字转抄，施工期不必另开。

框架红线: LangGraph／LangChain 框架类型零出现（检查点 saver `BaseCheckpointSaver` 一族归 `orchestration`，本块只出框架无关表与读写入口）——对应闸 R5b 契约
边界红线: ① 模型出口零接触（R7）；② 不直引引擎（R6）；③ DB 只经 `infra.db`、时间只经 `infra.clock`、审计只经 `security.audit`（无专属闸→人审＋AST 降维断言登记待补）；④ 不引包内其它块（只依赖 `state`——无专属闸→人审＋AST import 白名单登记待补）；⑤ 业务数据零写入（INV-2）：簿记表前缀 `agent_v2_*` 是唯一写面——对应测试 `::no_business_table_write`

## 票面对象（specs/persistence.md「验收测试」表逐行转抄——本票 10 行：规格表第 1–5、9、10、11、12、15 行）

〔来源：specs/persistence.md「验收测试」表 :165–:184（本票取自 :165–:169、:173–:176、:179），逐行原文；`#` 列＝规格表行序，-b 票续用同一行序不重编〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | 三类落盘语义各按其规则（更新／幂等／只追加） | `tests/domains/test_v2_persistence.py::three_write_semantics` | specs/persistence.md:165 |
| 2 | 黑匣子与审计行无改写／删除路径（AST＋行为双证） | `tests/domains/test_v2_persistence.py::append_only_no_mutation_path` | specs/persistence.md:166 |
| 3 | `status` 取值闭世界；`waiting_ask→running` 唯一合法方向 | `tests/domains/test_v2_persistence.py::status_machine_guarded` | specs/persistence.md:167 |
| 4 | 两次 `load` 等价且无副作用 | `tests/domains/test_v2_persistence.py::load_replayable_idempotent` | specs/persistence.md:168 |
| 5 | 黑匣子重复归档不覆盖＋跳过记账在场 | `tests/domains/test_v2_persistence.py::blackbox_first_write_wins` | specs/persistence.md:169 |
| 9 | 步记录 payload 原样保真（空结构与缺失可区分） | `tests/domains/test_v2_persistence.py::step_payload_faithful` | specs/persistence.md:173 |
| 10 | 核验对账机读字段可被读面机检（`pin-12` 落盘面） | `tests/domains/test_v2_persistence.py::verify_fields_readable_in_step` | specs/persistence.md:174 |
| 11 | `run_id` 全盖章：四类记录可按 run 聚合对账 | `tests/domains/test_v2_persistence.py::run_id_stamped_across_records` | specs/persistence.md:175 |
| 12 | 引用载体往返逐字节相同；坏 `handle` 抛错 | `tests/domains/test_v2_persistence.py::material_ref_roundtrip_and_bad_ref` | specs/persistence.md:176 |
| 15 | 旧检查点／旧黑匣子如实读入（对话通道空显） | `tests/domains/test_v2_persistence.py::legacy_read_honest` | specs/persistence.md:179 |

> 测试文件归属（spec :186 节尾原注照抄）：本块验收测试绑**新建** `tests/domains/test_v2_persistence.py`（本块是阶段 2 新划的公共层块 `appv2/runtimev2/persistence/`，与现状 `appv2/runtime/{store,checkpointer,blackbox,audit}.py` 的旧码测试形状不同）；旧码测试本批不改。

## 测试网钉（specs/persistence.md「与闸的挂钩表」pin 行逐行转抄——本块全 3 钉，全在本票）

〔来源：specs/persistence.md「与闸的挂钩表」:217–:219，逐行原文〕

1. **pin-12（P1，落盘面）**｜步记录 payload 保真（核验对账字段可机检）——**字段面在 `specs/verification.md`**｜测试 `::verify_fields_readable_in_step`｜现状：待织网（阶段 5）
2. **pin-28（P1，落盘面）**｜`run_id` 全盖章、可对账——**全盖章面挂 `specs/agent-loop.md`**｜测试 `::run_id_stamped_across_records`｜现状：待织网（阶段 5）
3. **pin-30（P2）**｜旧 run **黑匣子回放**如实（本块**唯一**挂断言的面；检查点**状态字段读入**面挂 `specs/state.md` 行为 8——两处对象不同：一是黑匣子回放、一是状态读入）｜测试 `::legacy_read_honest`｜现状：待织网（阶段 5）

- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 3 条 pin 行只落本票一处；`RT-W2-01b-persistence.md` 零 pin 行、只留归属指针。

## 施工要点（specs/persistence.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/persistence.md:138 | 行为 1 三种落盘语义 | 运行记录＝按状态机更新；步记录＝同键幂等；黑匣子与审计＝只追加（Owner 裁决 `walk/16` §七 Q-B；改写／删除路径不存在，AST＋行为双证） |
| specs/persistence.md:139 | 行为 2 状态机把守 | `status` ∈ 四值闭世界；`waiting_ask → running` 是唯一合法「恢复」方向（结构约束；「该不该迁移」决策仍在 orchestration） |
| specs/persistence.md:140 | 行为 3 恢复可重放 | 两次 `load` 得等价 `RunState`、无副作用（不写盘） |
| specs/persistence.md:141 | 行为 4 黑匣子只追加、首写为准 | 每 run 归档至多一次；重复归档不覆盖且如实记账（「已归档」异常＋调用方跳过记账）——本锚与行 2 同源（无改写／删除路径双证） |
| specs/persistence.md:145 | 行为 8 步记录 payload 原样保真 | 不裁剪、不做假值归一（空 `{}` 与「无 payload」读回可区分；钉 pin-12 落盘面——核验对账字段可被读面机检） |
| specs/persistence.md:146 | 行为 9 `run_id` 全盖章（落盘面） | 四类记录都携 `run_id` 可聚合对账（对账数据源＝`eval/results/Q15-对账报告.md` 口径；钉 pin-28 落盘面） |
| specs/persistence.md:147 | 行为 10 引用载体可寻址 | `put_ref`／`read_ref` 往返逐字节相同；坏 handle 抛错；载体实现阶段 5 定、语义不随载体变 |
| specs/persistence.md:149 | 行为 12 旧检查点／旧黑匣子如实读入（钉 pin-30 回放面） | 回放不抛错；旧 run 对话通道如实空显（不伪造补写）；状态字段读入面归 `specs/state.md` 行为 8 |

结构锚：specs/persistence.md:33 接口定义（**`RunStore`／五张行投影／检查点三表行级口／`AuditRecord` 签名＝本票交付物**，真源 `recon/J` 表事实）；:127–:134 框架与依赖红线（R5b/R7/R6 挂闸＋三条无专属闸面的降维 AST 断言）；:154–:159 不降级与静默禁令（合法降级路径＝无；审计不可改写）。

## 织网义务（eng/04-测试网设计.md §三 归本块行——本票只留指针）

- 归块事实（照实写，逐字转抄落 `RT-W2-01b-persistence.md`「织网义务」节——防两处真源漂移，转抄见该票）：**§三 盲区表无 persistence 行**。
- 本票织网义务＝①「测试网钉」3 钉（pin-12／pin-28／pin-30）对应用例落网（现状列均为「待织网（阶段 5）」；本块 pin 行全量承载于本票）；② 上述 §三 无明写行事实的转抄归 -b（本票只留指针）；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」10 行逐行实现为 `tests/domains/test_v2_persistence.py` 用例并全绿，测试标识与规格列逐字一致（`#` 保留规格表行序 1–5、9–12、15）；
- 「测试网钉」3 钉对应用例在场且绿（pin-30 为本块唯一挂断言的面）；
- 骨架与公开面按卡面与规格接口定义齐备（`RunStore`／五张行投影／检查点三表行级口／`AuditRecord`，真源 `recon/J`）；
- 只追加双证（`::append_only_no_mutation_path`，AST＋行为）与读回可重放（`::load_replayable_idempotent`）两道主干防线绿；
- 边界闸 R5b／R6／R7 在 `lint-imports` 双配置下绿；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W2-01a 完成，产物 `appv2/runtimev2/persistence/`（骨架＋接口＋落盘读回主干），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
