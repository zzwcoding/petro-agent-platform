- 日期：2026-10-15 ｜ 状态：**评审发现清单（待 L0 逐条处置）**
- 本清单只产发现，不修改任何现存文件。

## 一、结论摘要

1. **版式骨架合格**：十节齐、标题逐字、顺序正确；`uv run python tools/check_specs.py` 实跑 **PASS（0 警告）**，`uv run python tools/ref_resolvable.py check` 实跑 **绿**；附跑 `lint-imports --config tools/importlinter_v2.toml` = **18 契约全 KEPT**，故挂钩表「R5b／R7／R6／R2 已真跑」**属实**，`spec gate 已进 CI`／`ref_resolvable 已进 CI` 亦属实（`.github/workflows/ci.yml:32,34`）。
2. **新增节与既有节：既有一致处，也有四处打架**——（a）「框架与依赖红线」的 R2 行把「不直引引擎」记到 R2，真源 R2 只覆盖公共层包根深度、引擎禁令属 R6（**F-4**）；（b）行为 1 ③ 前置条件机仍用**四态**（`pass/blocked_ask/blocked_refuse/note`），与 `walk/12 §七 Q-B` 已定「**三态**（注记并入放行）」及已定稿 `preconditions.md` 冲突（**F-6**）；（c）「消息历史簿记」在 `触及的模块/验收/风险` 仍在用，行为 2 却称其「承载面退役」（**F-7**）；（d）行为 9 标「S1 的 H3 落位」但含 S1 **H2**（图装配与路由表）之实（**F-8**）。
3. **结构性缺项两条**：`## 不做什么` 为散文、**无「由谁承担＋锚点」表**（六份样板全为表，§二.2 硬要求，**F-1／高**）；`## 验收测试` **缺【边界集】【保留集】两行**（七份样板全有，**F-2**）。
4. **pin 挂载：三条中 pin-29 对得上、pin-23 部分对得上、pin-28 悬空**（挂钩表有行而正文无对应行为条）；**疑漏挂 P0 `pin-22`**（`RunState.messages` 只追加不改写，与行为 2／行为 10 同域）。
5. 其余为口径/真源标注类中低度偏差（数字无真源指针、闭世界命名不一致、事件真源双指、Manifest 字段 7/10 两说等），逐条见 §二。

## 二、发现清单表

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| F-1 | 高 | **`## 不做什么` 为散文式、每条排除无「由谁承担＋锚点」**：四条排除（不做记忆/跨会话个性化、不做自进化、不做写操作、不做 V1 端点改动）＋两条约束（核验不替代引擎侧 citation、schema 失败不自动 repair）全无落点锚点。§二.2 硬要求「每条排除必须带替代落点锚点……只写『不做 X』而无落点＝静默缺失的温床」；`docs/spec-format.md:19`；六份样板（`understanding.md`/`clarification.md`/`tool_matching.md`/`preconditions.md`/`execution.md`/`answering.md`）该节**全部**为「不做｜由谁承担｜锚点」三列表 | `specs/agent-loop.md:19-24`；`docs/spec-format.md:19,42-46`；对照 `specs/answering.md:11-21` | 采纳：改为三列表；「不做写操作」→落 `tools`（INV-2 只读面，`## tools`）；「schema 失败不 repair」→落 `parsing`＋ADR-0004 拍板 2；「不做 V1 端点改动」→落 `## api`／ADR-0007 |
| F-2 | 中 | **`## 验收测试` 缺【边界集】【保留集】两行**：§二.8 硬要求「另补『边界集』与『保留集』两栏」；`docs/spec-format.md:25`；七份已定稿规格**全部**含这两行（`grep -ln 边界集 specs/*.md` 命中 7 份，agent-loop 计 0） | `specs/agent-loop.md:157-194`；`docs/spec-format.md:25,53`；对照 `specs/preconditions.md:114-115`、`specs/answering.md:104-105` | 采纳：补两行（边界集＝挂起/中断/预算触界/换链回炉/坏引标 各落分支；保留集＝普通提问四相位收口行为不变） |
| F-3 | 中 | **行为约定编号跳号：7 → 9，无第 8 条**：编号 1..7 后直接 `9.`，全篇无 `8.`。须确认是「纯跳号」还是**返工漏抄丢了一条行为**（返工新增的是「编排层四行为」被编成 9）| `specs/agent-loop.md:126`（7）、`:138`（9）；`grep -nE "^[0-9]+\. " specs/agent-loop.md` 无 8 | 采纳：查明是否丢条；若纯跳号则重编为连续（并同步本文档内「行为 7／行为 9／行为 10」的交叉引用与挂钩表） |
| F-4 | 中 | **「框架与依赖红线」R2 行把「不直引引擎」的覆盖记错闸**：红线写「不直引引擎（`knowledge`／`query`／`retrieval`）与 只经 `transport` 公开面 发帧——两者的『只经包根』半面由 **R2 契约**覆盖」。但真源 R2 的禁引面是**九个公共层块的深层子模块**（`state`/`orchestration`/`bookkeeping`/`prompts`/`parsing`/`context`/`transport`/`persistence`/`gateway_adapter.*`），**不含任何引擎**；「禁直引引擎」的闸是 **R6**（`forbidden=appv2.knowledge/query/retrieval`）。挂钩表同一错配（「不直引引擎／只经 transport 包根｜R2」）| `specs/agent-loop.md:68`、`:214`；`specs/modules.md:529`（R2 定义）、`:520`（R6 定义）；`tools/importlinter_v2.toml`（R2 契约 `forbidden_modules=[…state.*…gateway_adapter.*]`；R6 契约 `forbidden_modules=[appv2.knowledge, appv2.query, appv2.retrieval]`） | 采纳：「不直引引擎」改挂 **R6**（与 `:67` 行合并去重）；`transport 包根`半面保留 **R2**；或明写「引擎面＝R6，transport 包根面＝R2」分开两行 |
| F-5 | 中 | **行为 7 预算数字为裸值、无真源指针**：`≤3 轮`／`发现 ≤10`／`单段时限 300s`／`单工具超时 30s` 均无「真源：<文件#节>」；且 `来源:` 行**未列** `walk/裁决表.md`（六份样板来源行皆列 `walk/裁决表.md §NN`）。真源 §06-A 统一预算表只含「发现≤10／大循环≤3轮／回炉一次／连续澄清≤6／同参重投即拦」，**不含 300s／30s**（这两条真源在 `recon/K` R-K-74、`recon/I2b` R-I2b-04）| `specs/agent-loop.md:126-137`、`:4`；`docs/runtime-refactor/eng/02-规格防漂移要求.md:53`（数字须写真源、禁裸字面值）；`docs/runtime-refactor/walk/裁决表.md:92`（§06-A）；`docs/runtime-refactor/recon/K-上下文事件指南预算.md:460` | 采纳：行为 7 每个数字后补真源指针（轮/发现→`walk/裁决表.md` §06-A；300s/30s→`recon/K` R-K-74）；来源行补 `walk/裁决表.md` |
| F-6 | 中 | **行为 1 ③ 前置条件机口径与已定裁决／已定稿规格冲突**：正文写「逐子问题过闸判**四态**：`pass｜blocked_ask→ASK 挂起｜blocked_refuse→子问题如实拒答｜note 注记随行`」，而 `walk/12 §七 Q-B` Owner 已裁「**改三态**（放行／拒答／等用户），『注记』并入『放行』的附加信息」，已定稿 `preconditions.md` 据此写「三态闭世界 `allow｜refuse｜ask`＋**不设第四态**、注记并入放行」。另：行为 1 ③ 列举闸项 **6 条**（禁用词/新鲜度窗/在册绑定态/外表越集/单井支持/合法口径），真源为 **8 个判定位**（缺 闸1b 模糊时间词门、闸4b 软失败域闸）| `specs/agent-loop.md:82-89`；`docs/runtime-refactor/walk/12-前置检查-前置条件机.md:89`（§七 Q-B）；`specs/preconditions.md:52-53,70,72`；`docs/runtime-refactor/synth/S3-口径裁决清单.md:16`（C-01，8 判定位） | 采纳：行为 1 ③ 改三态口径（注记并入放行）；闸项列举与 `preconditions.md` 判定序表对齐（或改为只引该表不复述条数） |
| F-7 | 中 | **「消息历史簿记」退役口径未清**：行为 2 明写「**混装消息历史退役**……V2-79a 三层分离后原『消息历史簿记』承载面**退役**」，但 `## 触及的模块` 描述 `context` 仍写「Context Builder＋**消息历史簿记**」，验收测试仍有「run 内**消息历史簿记**」行，风险 1 仍写「剧本化 completer 按**消息历史**形态驱动」。同一术语在一篇内「已退役」与「仍在用」并存 | `specs/agent-loop.md:32`、`:114`、`:179`、`:202`；`specs/agent-loop.md:97` | 采纳：三处「消息历史簿记」改口径（`dialogue`＋`process_notes` 双字段，或「对话链追加」），与行为 2 同源 |
| F-8 | 低 | **行为 9 标「S1 的 H3 落位」，但含 S1 **H2** 内容**：`synth/S1` 分列 **H2＝图装配与路由**（节点注册、路由表、条件边、编译出口）、**H3＝执行器与命令入口**（命令受理、图驱动、三终态落库、审计接线、身份缝）。行为 9 末条「组合图装配与路由表（节点注册、条件边、路由表）……一处集中」＝**H2** 之实，却被挂在「H3 落位」标题下；且 H3 原含的「图驱动」在本行为内无对应项 | `specs/agent-loop.md:138-143`；`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md:37`（H2）、`:38`（H3） | 采纳：标题改「H2＋H3 落位」或拆两条（图装配/路由表＝H2；命令受理/三终态/审计/身份＝H3） |
| F-9 | 中 | **行为 9 引入 `orchestration → infra` 直依赖，模块卡依赖未列**：行为 9 写「请求身份经 **`infra.security.resolve_actor`** 解析」「四事件经 **`security.audit`** 唯一写口」；但 `specs/modules.md` `## orchestration` 卡「依赖」只列 `state`／`bookkeeping`／`transport`／`persistence`＋七相位（外部仅 LangGraph），**无 `infra`**。且 `AskRequest` 含 `actor: Actor`（`:46`），暗示身份在 `api` 侧（`## api` 卡依赖列为 `orchestration`、`infra`）解析后注入——两处位置/依赖口径待对账。另：`## persistence` 卡公开面已有 `def audit(...) # 唯一写口＝security.audit`，行为 9 直写 `security.audit` 与该卡「审计唯一写口」落点不一致 | `specs/agent-loop.md:141-142`、`:46`；`specs/modules.md:302-304`（orchestration 依赖）、`:311`（bookkeeping）、`:424`（persistence.audit）、`:495`（api 依赖） | 采纳：按 `modules.md` 卡为准——若确在编排块解析/写审计，则**回阶段 2 补 `orchestration` 卡依赖（`infra`）**；若在 `api` 侧，则本行为措辞与位置改到边界；审计写口优先引 `persistence.audit` |
| F-10 | 低 | **pin-28 挂载悬空：挂钩表有行、正文无对应行为条**：挂钩表挂「run_id 全盖章（计费可对账）｜钉 `pin-28`」；但全篇正文无「run_id 全盖章」行为条（`run_id` 仅作为 `RunHandle` 字段/API 出参出现，未声明逐题盖章纪律）。反查：`eng/04a` 的 pin-28 行为是「run_id 全盖章＋逐题 `ledger_run_ids` 集合与 jsonl `run_id` 等值」，正文无承接 | `specs/agent-loop.md:217`；`docs/runtime-refactor/eng/04a-应钉行为清单.md:37`（pin-28） | 采纳：正文补一条「run_id 全盖章」行为条（或把该行挂到有承接的块），否则挂钩表指向空 |
| F-11 | 中 | **疑漏挂 P0 `pin-22`**：本规格挂了 `pin-23`／`pin-29`（P0）＋`pin-28`（P1），但同域的 **P0 `pin-22`「`RunState.messages` 只追加不改写：任意相邻调用互为前缀延伸」**未见挂载。`pin-22` 是行为 2（编译契约 `[system]＋dialogue 截断＋当前轮`）与行为 10（追问＝跨 run 前缀延伸）的**机制前提**；`pin-23`（追问播种）已挂而支撑它的 `pin-22` 未挂。可能归属 `context`／`state`（两块均**无独立规格**）——须 L0 明确定位 | `specs/agent-loop.md:205-218`（全表无 pin-22）；`docs/runtime-refactor/eng/04a-应钉行为清单.md:31`（pin-22，P0）；`specs/agent-loop.md:95-108,145-148` | 采纳：判定 pin-22 归本规格（则补挂）还是归 `context`/`state`（则登记待其规格）；P0 钉不得悬空 |
| F-12 | 低 | **`AskChoice.kind` 取值与真源闭世界不一致**：接口写 `AskChoice = {kind: "clarify" \| "approval", ...}`，而 ask 帧 kind 闭世界真源为 `{clarify, external_table_approval}`；已定稿 `preconditions.md` 的 `AskReason.kind = Literal["external_table_approval", "caliber_clarify"]`，`pin-29` 亦用「clarify 选项/越集审批两形态」 | `specs/agent-loop.md:49-50`；`docs/runtime-refactor/synth/S6-事件与帧目录.md:20`；`specs/preconditions.md:47-48`；`docs/runtime-refactor/eng/04a-应钉行为清单.md:38` | 采纳：`kind` 值与真源对齐（`clarify`／`external_table_approval`），或写明与 ask 帧 kind 的映射 |
| F-13 | 低 | **事件闭世界真源双指（横切事实真源单点被破）**：接口注释把九类事件枚举真源指为「`synth/S3` C-05」，不降级节又把「九类闭世界」真源指为「`synth/S6-事件与帧目录.md`」。同一横切事实两处真源不同（S3 C-05 是**口径裁决条目**、S6 是**事件与帧目录**）| `specs/agent-loop.md:53`、`:153`；`docs/runtime-refactor/synth/S3-口径裁决清单.md:20`；`docs/runtime-refactor/synth/S6-事件与帧目录.md:10-24` | 采纳：统一到 `synth/S6`（事件目录为真源），S3 C-05 作口径裁决备注 |
| F-14 | 低 | **行为 9 称 `waiting_ask` 为「三终态」之一，与行为 10 状态机措辞打架**：行为 9「`completed`／`failed`／`waiting_ask` **三终态**由本块写 run 表」；行为 10「`running→waiting_ask→（resume）→running→completed/failed`」——`waiting_ask` 是 resume 可达的**中间态**，非终态 | `specs/agent-loop.md:140`、`:145-146`；对照 `docs/runtime-refactor/recon/I1a-执行器前半.md:23`（「run 状态机**四态**落库」） | 采纳：措辞统一（如「三种收口落库态」或「终态 `completed`/`failed` ＋ 挂起态 `waiting_ask`」） |
| F-15 | 低 | **红线「禁手写替代」未进挂钩表、亦未登记「人审＋原因」**：红线末条「禁手写替代：不得自建图执行器旁路、不得自建模型客户端、不得自建帧通路」在挂钩表**无对应行**；样板 `answering.md` 对同款「自建帧通路」半面给了 R2 覆盖＋「另一半无专属闸→人审＋原因」行 | `specs/agent-loop.md:69`、`:205-218`；对照 `specs/answering.md:67,125`；`docs/spec-format.md:27,63` | 采纳：补一行挂「不得自建图执行器旁路」（可翻成 import/AST 断言）或「人审＋原因」 |
| F-16 | 低 | **行为 2 复述 Manifest 字段清单为 7 项，与 S3 钉的代码真值 10 字段两说**：行为 2 列 `source_type/source_id/version/trust_level/selected_reason/token_count/transform`（7 项）；`synth/S3` C-11 钉「**10 字段**（类体）——docstring『七字段』陈旧」。反证：`recon/I2a` 称这 7 项为「**合同七字段**」并回指本规格行为 2——故两说待确认（合同面 7 vs 类体 10，另三为 V2-61 机检键）| `specs/agent-loop.md:106-108`；`docs/runtime-refactor/synth/S3-口径裁决清单.md:26`；`docs/runtime-refactor/recon/I2a-状态常量与清单.md:55,81` | 待确认：合同面是否应含 V2-61 增的三机检键；无论结论，按 §三.2「只引不复述」改为引真源 |
| F-17 | 低 | **头部缺「版式/工序」行，`来源:` 行未列正文实际引用的真源**：七份已定稿规格皆有 `版式: docs/spec-format.md ｜ 工序: docs/spec-process.md`；本规格无。且正文引 `walk/08`、`walk/裁决表 #10`、`synth/S3`、`synth/S6`、`synth/S1`、`tickets/v2/V2-79-…`、`docs/runtime-refactor/arch/P7a-…` 等，`来源:` 行**一条未列**（样板来源行均列其 walk/裁决表/synth 真源）| `specs/agent-loop.md:1-8`；对照 `specs/preconditions.md:4-5`、`specs/answering.md:4-5` | 采纳：补「版式/工序」行；`来源:` 行补齐正文引用的 walk/synth/arch/tickets 真源 |
| F-18 | 低 | **行为 1 复述 step 类型六值闭世界无真源指针**：行为 1「每步落 step 记录（类型六值闭世界 `decision/discover/execute/observe/verify/answer`）」为横切事实复述，未给真源（真源＝`synth/S6` §一 `state.py:35-45`）；§三.2「横切事实只引用、不复述」 | `specs/agent-loop.md:92-94`；`docs/runtime-refactor/synth/S6-事件与帧目录.md:26` | 采纳：补真源指针或改为只引 S6 |

## 三、12 问 ＋ 6 条重点逐条回答

### 12 问（`docs/spec-process.md` §三）

**1 十节齐＋标题逐字？** 无发现。`## 目标`(10)／`## 不做什么`(19)／`## 触及的模块`(26)／`## 接口定义`(38)／`## 框架与依赖红线`(63)／`## 行为约定`(71)／`## 不降级与静默禁令`(150)／`## 验收测试`(157)／`## 依赖与风险`(196)／`## 与闸的挂钩表`(205)——十节齐、标题逐字（`docs/spec-format.md:33-34`）、顺序与 §二 表一致；`check_specs` 实跑 PASS。

**2 行为约定每条能否写成 `assert`？含糊词？** 无发现。判 FAIL 的含糊词「尽量／合理／必要时／视情况／适当／若干」全文 **0 命中**；各条可判（相位闭世界、对账缺/多/未知 id 拒、`status=ask`→`waiting_ask`、越界取值判失败、数字阈值可判）。唯 **F-3**（编号缺 8）非语义问题。

**3 数字有无裸值、能否指真源？** 有发现——**F-5**（行为 7 的 `≤3/≤10/300s/30s` 无真源、来源行缺 `walk/裁决表`）；**F-18**（step 六值复述）；**F-16**（Manifest 7 vs 10）。其余数字（子问题 `≤4`、`process_notes` 每条 `≤200 字`、`chain_switch` 一次、ask 上限）亦无逐条真源指针，属同族（F-5/F-18 面）。

**4 不做什么每条有无「由谁承担＋锚点」？** 有发现——**F-1（高）**。该节为散文，四条排除＋两条约束**零锚点**；六份样板全为三列表。

**5 框架红线：点名框架/唯一出口写对应闸名？闸名真存在？source 真覆盖 `appv2.runtimev2.orchestration`？** 部分有发现——**F-4**（R2 误挂）。闸名真存在且 source 真覆盖 orchestration：R5b（`importlinter_v2.toml` R5b `forbidden=langgraph/langchain*`）、R7（`forbidden=appv2.infra.llm_client`）、R6（`forbidden=knowledge/query/retrieval`）、R2（`forbidden=…公共层深层子模块`）`source_modules` 均含 `appv2.runtimev2.orchestration`；「其余 16 块」计数正确（R5b source 列 16 块）。**唯 R2 被用来覆盖「不直引引擎」＝覆盖面不实**（见 F-4）。

**6 不降级与静默禁令是否完整？** 无发现。`:152` 明写「合法降级路径：**无**」；`:153` 列机读信号（九类事件帧＋step payload＋`security.audit`）；`:155`「不许自述完成」。验收含信号在场断言（`:185` 预算触界→收敛＋notice 无静默；`:183` 无据改写＋notice；`:191-192` 三终态/审计）。

**7 验收测试：每行标识／边界集保留集／测不出的行？** 有发现——**F-2**。34 行全部绑 `tests/…py::<id>` 标识（`check_specs` 校验通过）；**但【边界集】【保留集】两行俱缺**（§二.8 硬要求）。

**8 与闸的挂钩表：填了没／「已真跑」属实否／接不上的有无原因？** 部分有发现——**F-4**（R2 行覆盖面不实）、**F-10**（pin-28 行悬空）、**F-15**（红线「禁手写替代」无行）。表已填；「已真跑」**属实**——`lint-imports --config tools/importlinter_v2.toml` 实跑 **18 契约全 KEPT**；`spec gate 已进 CI`／`真源引用闸已进 CI` 属实（`ci.yml:32,34`）。「不做什么」纯范围排除**已按 §五 登记「人审＋原因」**（`:218`）——合格。

**9 与 `walk/` 决策是否冲突？** 有发现——**F-6**（行为 1 ③ 四态 vs `walk/12 §七 Q-B` 已定三态）。逐条比对：`walk/08` 四动作闭世界→行为 1 ① **一致**（`:75` 明注「Owner 2026-10-15 按 `walk/08` 同步」）；`walk/裁决表.md` §10（`tool` 归匹配相位）→行为 1 ①「已去 `tool`」**一致**；`walk/裁决表.md` §01-A（游标全流单调、重放不位移）→接口 `cursor` **一致**；§06-A/B（等待不计轮、resume 重置轮预算、成功不重跑）→行为 7 **一致**；§12/§13（废弃词/时间词交模型）→行为 3 **一致**。

**10 覆盖（`synth/S1` H2/H3/H5 有无漏项／有无把别的块的事写进来）？** 部分有发现——**F-8**（H3 标签含 H2）。`S1` 该模块两个单元：**H2＝图装配与路由**（行为 9 末条覆盖 ✓，但标签错）、**H3＝执行器与命令入口**（行为 9 前四条覆盖 ✓）。`H5＝公共位与结果归一`归属 `bookkeeping` 块（`modules.md` 独立卡），本规格非其落点、不算漏项。**「别的块的事」**：行为 1 ①—④ 复述 clarify/toolmatch/precondition/batch 四相位内部（各有独立规格），已产生口径分叉实例（F-6）——建议四相位细节改为「只引各规格不复述」。

**11 总纪律残留（程序替模型判语义）？** 无发现。行为 1 ③ 明写前置条件机「纯固定代码零 LLM（铁律——LLM 无权判定）」，语义类（禁用词、口径归一）在 `tool_matching`／上游模型侧；行为 3 明写「无 repair、拒因回喂重发射」；行为 1 ③「换链回炉」为结构分派。全篇无「词表/正则猜语义」。（**F-6** 是口径条数/态数问题，非总纪律违例。）

**12 与模块卡一致（职责／公开接口／依赖）？** 部分有发现——**F-9**（依赖：行为 9 引 `infra.security` 而卡未列 `infra`）。职责＝卡「图装配与路由、命令受理与执行器、挂起恢复」（`modules.md:292`）↔ 行为 9 覆盖；公开接口＝卡 `AgentRuntime.ask/resume -> RunHandle`（`:297-299`）↔ `:42-43` 一致；Seam＝卡「`RunCommand（ask/resume）→执行器→事件流`」（`:307`）↔ 行为 9「`RunCommand → 执行器 → RunEvent`」一致。

**（附加）与六份已定稿样板写法一致？** 有发现——**F-1**（不做什么散文 vs 样板表）、**F-2**（缺边界集/保留集）、**F-17**（缺版式/工序行、来源行不全）。一致项：挂钩表三列列式、`## 框架与依赖红线` 闸名句式、「合法降级路径：无」＋机读信号句式、`synth/` 前缀直引。

### 6 条重点（Owner 指定）

**重点 1｜「框架与依赖红线」与正文行为 1/2/4 的框架·模型·tools·transport 表述——一致且不越界？** 有发现——**F-4**。正文行为 1 ① 的「钻取（`semantic_query`/`doc_retrieve`/`table_schema`）」是**工具名**（经 `tools`，符 R6）、行为 4「工具只经 `ToolRegistry.call`」（符 R6）、行为 2「模型调用经 `Context Builder` 编译」（模型出口符 R7）——正文**未见**「相位直调引擎/直调 `llm_client`/自拼 wire 帧」的越界句，正文与红线**未见实质冲突**。唯红线自身对 R2 的归属写错（F-4）：正文行为若被照此实现「引擎面靠 R2」，则 R2 并不覆盖引擎，会形成虚假合规感。

**重点 2｜「不降级与静默禁令」与行为 5/7/8(状态机) 同一口径？** 基本一致，一处受影响。行为 5「无支撑断言改写『未找到/材料未披露』＋notice」＝不降级节「触界不得静默＋机读信号」同口径 ✓；行为 7「预算触界交付已取得材料＋notice 明示未完成项，**不得静默截断**」＝不降级节「与行为 7 同源」✓；行为 10 状态机与不降级节「三终态…机读信号」✓。**未出现**「一处如实交代、另一处静默截断」。唯 **F-14**（`waiting_ask` 被称「终态」）为该节与行为 10 的措辞打架。

**重点 3｜「与闸的挂钩表」每条硬要求在正文有对应行为条？反向有无漏挂？** 有发现——**F-10**（pin-28 行正文无承接）、**F-4**（R2 行覆盖面不实）、**F-15**（正文红线「禁手写替代」未挂）。正向：R5b/R7/R6/R2 行 ↔ 红线节 ✓；pin-23 行 ↔ 行为 10 追问；pin-29 行 ↔ 行为 4／10；「不做什么」行 ↔ `:19-24`。反向漏挂：红线的「禁手写替代」、行为的 `three terminal states`/审计均无行（后者有验收测试覆盖，可接受）。

**重点 4｜接口面改动与正文及模块卡一致？`RunHandle.stream` 与九类闭世界自洽？** 有发现——**F-12**（`AskChoice.kind` 值）。`AskRequest` 三形态（提问/重连/追问续会话）与 `## api` 卡「入参三形态」、`## orchestration` 卡签名一致；`RunHandle.cursor＝全流单调断线游标` 与 `walk/裁决表.md` §01-A、`## transport` 卡「游标全流单调；重放不位移」一致；`RunHandle.stream: AsyncIterator[SseEvent]` ↔ 事件枚举九类闭世界（`step/text/tool/observation/ask/verdict/citation/notice/blackbox`）**自洽**（恰 9 值，与 `synth/S6` §一 一致）。唯 `AskChoice.kind` 的 `"approval"` 与真源 `external_table_approval` 不一致（F-12）。

**重点 5｜新增编排层四行为（行为 9）与正文行为 4/10、`infra.md` 行为约定 3、`synth/S1` H3 归属？** 有一处发现——**F-9**（`infra` 依赖）+**F-8**（H3/H2 标签）。行为 9 审计接线「四事件经 `security.audit`，`action` 恒 `agent_v2.*`」＝ `infra.md:41`（行为约定 3）**一致**，亦＝`recon/I1a:23`（现状四事件）；行为 9 三终态 ↔ 行为 10 状态机（除 F-14 措辞）；身份缝 ↔ AGENTS.md 硬纪律 4（身份桩）一致，但引入 `infra` 直依赖未进卡（F-9）。S1 归属：行为 9 前四条＝H3 ✓、末条＝H2（标签错，F-8）。

**重点 6｜陈旧引用是否改净？** 基本改净，一处残留。全篇**无**「`modules.md` runtime 卡」字样；旧 `appv2/runtime/` 只出现一次且**明标备份**（`:7`「旧 `appv2/runtime/` 只作备份——ADR-0007」），前置机闸件本体路径已指向现行 `appv2/tools/precondition.py`（`:8`）。**残留**：术语态（非路径）「消息历史簿记」三处未清（**F-7**）。

### pin 挂载核对（真源 `eng/04a-应钉行为清单.md`，现 31 条）

| 钉 | 优先级 | 钉的行为（真源 `04a`） | 本规格正文对应 | 判定 |
|---|---|---|---|---|
| `pin-29` | P0 | 挂起→resume 闭环：clarify 选项/越集审批两形态 ask 帧挂起→resume 带 kind 判别→同链续推收口 | 行为 4（`status=ask`→`waiting_ask`→resume 续跑）＋行为 10（状态机） | **对得上**（唯 `kind` 命名差，F-12） |
| `pin-23` | P0 | 追问播种＝前 run 检查点终链整链承接＋[user 新问]（跨 run 前缀延伸；6 轮 `dialogue` 全量传承） | 行为 10「追问＝会话线程新轮——前轮**消息历史（含问答/执行台账）**随追问进新 run」 | **部分对得上**：同域（跨 run 追问播种）✓；但正文口径「消息历史（含执行台账）」与 `pin-23`「`dialogue` 全量传承」及行为 2（过程档案不入史）有张力（F-7） |
| `pin-28` | P1 | run_id 全盖章＋逐题 `ledger_run_ids` 与 jsonl `run_id` 等值 | **正文无承接**（仅挂钩表有行） | **挂得空**（F-10） |
| 漏挂疑点 | **P0** | `pin-22`：`RunState.messages` 只追加不改写（前缀延伸） | 行为 2／行为 10 的机制前提，未挂 | **疑漏挂**（F-11） |

其余 P0（pin-01/02/03/04/05/08/10/17/18/27）分属 `answering`／`verification`／`understanding`／`execution`／`preconditions`／`gate`／`infra` 各块，非本规格落点，本轮不判其归属；唯 **pin-17**（前置条件机四态语义）与 **F-6** 面相交（本规格 行为 1 ③ 的态数口径）。

## 四、未验证清单 ＋ 覆盖自检 ＋ 两道闸实跑输出

**未验证**（已声明，不编造）：

1. `appv2/runtimev2/orchestration/` 实现面与本规格验收测试（`tests/domains/test_v2_four_phase.py`、`tests/api/test_v2_asks.py` 等）在本次评审**未实跑**（属阶段 5 承诺）；`R5b/R7/R6/R2` 的「已真跑」为**契约层 KEPT 实测**，编排块若为占位实现则属契约空过。
2. **F-3**：跳号是否为「漏抄丢条」无法从文本判定（需 L0 比对返工前的版本或提交历史）。
3. **F-9**：身份解析/审计写口的**实际落点**（`api` 侧注入 vs `orchestration` 侧直取 `infra.security`）未在规格与卡中显式定，属待 L0 裁。
4. **F-16**：Manifest「合同七字段」与「类体十字段」孰为规格应载口径，`recon/I2a` 与 `synth/S3` C-11 各执一说，未回代码核。
5. **F-11**：`pin-22` 的归属块（本规格 vs `context`/`state`）未在 `eng/04` / `eng/03` 明示。
6. `docs/runtime-refactor/arch/P7a-交接包与挂账清单.md` A-P7a-37 的红线原文本轮**未逐字回核**（评审对象引其编号；preconditions/answering 样板引同一编号）。

**覆盖自检**——本轮实读文件：

- 评审对象：`specs/agent-loop.md`（全文 219 行）。
- 判据／版式：`docs/spec-process.md`（§三 12 条）、`docs/spec-format.md`（全文）。
- 模块与边界：`specs/modules.md`（`## orchestration`／`## api`／`## persistence`／`## tools`／`## state`／## 边界规则 R1–R8）、`specs/infra.md`（行为约定 3）。
- 样板：`specs/understanding.md`／`clarification.md`／`tool_matching.md`／`preconditions.md`／`execution.md`／`answering.md`（不做什么表、边界集/保留集、挂钩表列式对账）。
- 决策：`docs/runtime-refactor/walk/08-澄清-意图澄清.md`、`walk/12-前置检查-前置条件机.md`、`walk/裁决表.md`。
- 合成／钉：`synth/S1-重写单元与证据交叉矩阵.md`、`synth/S3-口径裁决清单.md`、`synth/S6-事件与帧目录.md`、`eng/04a-应钉行为清单.md`、`eng/02-规格防漂移要求.md`。
- 取证：`recon/I1a-执行器前半.md`、`recon/I2a-状态常量与清单.md`、`recon/K-上下文事件指南预算.md`、`arch/P7b-ADR与裁决图.md`。
- 闸：`tools/importlinter_v2.toml`、`tools/check_specs.py`、`tools/ref_resolvable.py`、`.github/workflows/ci.yml`。

**计数**：共 **18 条** 发现——`L0×0`／`高×1`（F-1）／`中×8`（F-2、F-3、F-4、F-5、F-6、F-7、F-9、F-11）／`低×9`（F-8、F-10、F-12、F-13、F-14、F-15、F-16、F-17、F-18）。

**两道闸实跑输出（2026-10-15）**：

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）
（exit 0）

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：13 份规格的真源引用与边界规则编号均可解析。
（exit 0）
```

附跑（用于核挂钩表「已真跑」与框架红线 source 覆盖）：

```
$ uv run lint-imports --config tools/importlinter_v2.toml
Analyzed 129 files, 508 dependencies.
… R2 … KEPT ；R5b … KEPT ；R6 … KEPT ；R7 … KEPT ；R8 … KEPT
Contracts: 18 kept, 0 broken.
```

—— 以上为评审发现清单，供 L0 逐条处置。**评审代理只产发现、不修改任何现存文件。**
