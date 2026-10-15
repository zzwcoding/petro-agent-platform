# RT-W5-02 · api——V2 端点与 SSE 事件桥（`appv2/api/` 存量六件改接 runtimev2）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/agent-loop.md`（状态「已定稿」）触及表 api 行——本票为其施工落点（该行原文见「票面对象」行 1）；帧面承接规格 `specs/transport.md`「触及的模块」表 api 行（原文见行 12）
Touches modules: `api`（落点＝存量目录 `appv2/api/`：`app.py`／`chat.py`／`bridge.py`／`wire.py`／`deps.py`／`errors.py`＋包根 `__init__.py`，`wc -l` 实测合计 1235 行——**不在 eng/03 §二 五波序列的 17 块内**；17 块规格不覆盖本块，卡面即其规格真源）
波次: W5 尾票（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W5 行三列原文：块列「`orchestration`」；理由列「依赖全部相位＋persistence/transport/bookkeeping，天然最后」；出口判据列「有界终止；挂起恢复；相位顺序只由本块决定」——**该行块列不含 `api`**）｜主窗裁注（原文）：「api 归 W5 尾票，eng/03 五波表未列，挂 W5（流水 50 登记）」——「流水 50 登记」＝`docs/runtime-refactor/00-决议与方法.md` §十 裁决流水待追加的第 50 条（本票起草时该节止于第 49 条；追加动作归主窗——该节头注原文「新条目一律**追加到本节末尾**，禁止锚点插入」，本票不代改该文件）
复审强度: 50% 抽查（`api` **非六质量关键块**——`docs/runtime-refactor/00-决议与方法.md` 裁决流水 48③ 原文「质量关键块（gateway_adapter／bookkeeping／preconditions／answering／verification／orchestration）施工后 100% 复审、其余抽 50%，交界归消费者验证」；eng/03 §五 头注同口径原文「B 列六块＝质量关键块施工后 100% 复审，A 列抽 50%，交界归消费者验证」）
前置: ① **orchestration 三票收票**（`tickets/v2-refactor/RT-W5-01a-orchestration.md`／`RT-W5-01b-orchestration.md`／`RT-W5-01c-orchestration.md`——主窗裁定原文：「api 的 V2 改造单独立票 RT-W5-02，挂 W5 末尾」，「前置＝orchestration 三票收票」）；② 规格前置已满足（`specs/agent-loop.md` 已定稿／`specs/transport.md` 已定稿／`specs/modules.md` `## api` 卡在册——`api` 非 17 块、无独立十节规格；`api` **十节规格不存在也不新开**：新建＝改规格，回设计仓）；③ 存量实件面在册（`ls` 实测：`appv2/api/` 八件在册〔含包根 `__init__.py`〕；`tests/api/test_v2_asks.py`／`test_v2_runs_list.py`／`test_v2_composition.py` 三文件在册）
阻塞: `RT-W5-01a-orchestration.md`／`RT-W5-01b-orchestration.md`／`RT-W5-01c-orchestration.md`（前置①三条）＋票注①–③三处对账条目（本票与主窗对账结论落地前不动 `appv2/api/` 进口面）｜被阻塞: 切换（eng/03 §三 切换前提原文：「W1–W5 全绿 ＋ 特征钉全绿 ＋ **重写出口判据达成**（Owner 已裁＝《规划》§八-B 题二 A：Q17 复考检索域 ❌=0、全卷 ❌≤5＋六闸全绿＋合同覆盖率 V2 面无缺口＋真机多轮前缀延伸不回归）＋ 生产冒烟通过」；切换动作第 1 条原文「`q12_v2_launcher.py`（:8001 生产装配）的运行时引用从 `appv2.runtime` 改指 `appv2.runtimev2`——单点改动，重启生效」——**该动作不在本票**）

## 任务

把 `appv2/api/` 这一层从旧运行时**改接**到 `appv2.runtimev2`，并让它的 SSE 桥**只渲染、不编号**：四端点形（行 2–6）、入参三形态（行 3）、四错误码（行 7）、`session` 首帧形（行 12 所引载荷 `{run_id, resume}`）**逐字不变**；本层今天自建的帧号／游标／重放缓冲语义（`appv2/api/bridge.py` 自述原文：「重放流自 L＋1 续枚举帧号（重放帧号与原流不对齐——能补的是缓冲内容而非原流帧序，V1 重放同形，如实登记）」）按帧面规格收口——帧对象、信封、游标归 `transport`，`api` 只做渲染（行 11／12 原文）。

**本票＝`api` 的 V2 改造单票（不派生）**。改接对象＝现状**八处旧包进口**（`grep -n "appv2\.runtime" appv2/api/*.py` 实测：`app.py:36`＋`:46`（`GraphRunExecutor`）＋`:47`（`Completer`）、`bridge.py:36`（`RunEvent`／`RunHandle`）、`chat.py:41`（`AskChoice`／`AskRequest`）、`deps.py:20`（`AgentRuntime`／`RunStore`）、`errors.py:24`（`RunNotFoundError`／`RunNotSuspendedError`）、`wire.py:27`（事件闭世界常量族）、`ontology_guide.py:27`（`DECISION_CONTRACT`））。**判据＝改装后 `appv2/api/*.py` 对 `appv2.runtime` 零命中**（旧包本批保留不删——eng/03 §三 废弃节奏第 1 步原文「删 `appv2/runtime/` 旧码包 ＋ 移除 `tools/importlinter_v2.toml` 的旧 `appv2.runtime` 契约」）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不裁量。

> 范围外（防一头两认）：① 切换动作（eng/03 §三 上文所引第 1 条）归切换票；② 旧码与旧码测试的删除／改写归 eng/03 §三 废弃节奏与 eng/04 §五 织网②；③ `RT-W5-01a`～`-01c` 已逐字转抄的规格行与 pin 行本票不重复转抄（先例 `tickets/v2-refactor/RT-W4-05b-execution.md:42` 分票理由原文：「同一 pin 行在两票重复转抄＝两处真源必漂移」）；④ 「与闸的挂钩表」中非 pin 行（spec gate／真源引用闸／各边界闸行）由各自闸承接，本票只转抄与 `api` 面直接相关的行（行 11／12 与「施工要点」节）。

**小票制自检（流水 48）**：票面对象 12 行 ≤ 15 ✓；先读 6 份 ≤ 6 ✓；聚焦一个行为簇＝「端点进、SSE 帧出」的**接缝改接**（本层单一 seam＝`specs/modules.md:610` 行原文「Seam: HTTP 接口（tests/api 接口级测试，不起真实端口）」）✓ → 本票不派生。

先读: （6 份）`specs/agent-loop.md`（接口定义节 :44–:67 端点四行与错误码行＋触及表 :31–:42＋验收测试表 :173–:212——本块对外规格真源）；`specs/modules.md`（`## api` 卡 :586–:612 公开面/依赖/Seam 与测试＋`## 边界规则` :623–:643 第 630 行 api 行＋`## orchestration` 卡 :310–:329 公开接口与依赖行——公开面与边界以卡为准）；`specs/transport.md`（帧对象 `SseEvent`／`envelope`／游标语义／`session`·`done`·`error` 三帧／`api` 面三处表行与风险 7·9·11 行——本层只渲染）；`specs/state.md`（`AskRequest`／`AskChoice`／`RunHandle` 三形状与形态闭世界 :55–:71＋行为 14＋错误契约行 :93——受理载荷与回执的形状真源）；`appv2/api/` 存量七件（`app.py`／`chat.py`／`bridge.py`／`wire.py`／`deps.py`／`errors.py`／`ontology_guide.py`——现状端点形与八处旧进口面清单）；登记面与既有契约（`config/runtimev2_endpoints.json` E1–E4 冻结基线＋`config/contract_endpoints.json` V2 三条挂账登记＋`tools/importlinter_v2.toml` :49–:53 与 :5–:9 两条 api 面契约＋既有测试 `tests/api/test_v2_asks.py`／`test_v2_runs_list.py`／`test_v2_composition.py`）。

框架红线: **`api` 面无点名框架**——本层不得直接 import `langgraph`／`langchain*`。承接面＝既有契约 `tools/importlinter_v2.toml:49–:53`（`source_modules` 含 `appv2.api`，`forbidden_modules` 含 `langgraph`／`langchain`／`langchain_core`／`langchain_community`，`allow_indirect_imports = true`），其注原文：「api→runtime→langgraph 传递链是设计路径非触界（P-008·V2-07 起 api 真消费 runtime；R6 同款判例：直接引用才违规，红线咬合面＝本模块不得直接 import 框架）」；改接后同一判例随面平移（`api`→`orchestration`→框架）。**R5b 不覆盖本块**（其 `source_modules` 实列 runtimev2 16 块、不含 `appv2.api`——`tools/importlinter_v2.toml:100–:107` 亲读属实）。装配面（`create_app`）同样不得出现框架类型（`specs/modules.md:324` 行原文「框架类型不得外泄」）；SSE 帧载荷全 JSON 原语（`appv2/api/__init__.py:7–:8` 现状自述照旧）。
边界红线: ① **只经 `orchestration` 公开接口**（行 8／9 原文）——八处旧进口改接后的落点以主窗对账结论为准（票注①），本票**不裁量进口面**；② **无专属闸 → 人审**：`api` 引用 `orchestration` 以外模块（行 9 原文）在 `tools/importlinter_v2.toml` 无对应契约（`:5–:9` 契约只覆盖「runtime 侧不得引 `appv2.api`」；`R1–R8` 契约 source 均不含 `appv2.api`）——降维 AST 断言需新增验收行、本批未授权 → 登记待补（照 `RT-W5-01a-orchestration.md` 同款登记手法）；③ **禁自建帧通路**（帧对象、信封、游标只在 `transport` 实现——`specs/transport.md:154` 行原文），本层只渲染；④ **端点与错误码零发明**：四端点路径／四码／三形态／`session` 首帧形（行 2–7／12）逐字照抄，不私改语义（改＝回设计仓）；⑤ **不引旧码**：改接后本层对 `appv2.runtime*` 零命中（切换动作与旧码删除归 eng/03 §三 其票——范围外）；⑥ **身份缝不破**：`appv2/api/deps.py:19` 现状进口 `appv2.infra.security.Actor`／`resolve_actor` 不动（`specs/agent-loop.md:154` 行原文「请求身份经 `infra.security.resolve_actor` 解析（开发期身份桩；正式接 OAuth2.0 **只换该函数实现**，其余零改动）」）。

## 票面对象（规格原文行逐行转抄——本票 12 行；**规格无专属验收行**，见票注⑤）

〔来源：`specs/agent-loop.md`「接口定义」节 :61–:66 与「触及的模块」表 :41；`specs/modules.md` `## api` 卡 :606／:612 与 `## 边界规则` 表 :630；`specs/transport.md`「触及的模块」表 :32 与「不做什么」表 :22——逐行原文；`#` 列＝本票行序，与 W5-01 三票的规格表行序不混编（本票不占用 agent-loop「验收测试」表任何行）；含竖线的原文行（行 1／9／11／12＝所引表行的整行）在表内以 `\|` 转义以保表格结构——**`\|` 即原文的 `|`，逐字比对时按原文读**，无增删无换述〕

| # | 票面对象（规格原文照抄） | 规格源行 | 核对面（存量用例标识／人审——**非规格验收行**） |
|---|---|---|---|
| 1 | 「\| api \| 新增 \| 三端点＋SSE 事件桥（asks 三形态：提问/重连/追问续会话） \|」 | specs/agent-loop.md:41 | 人审（该行由 spec gate 校「触及模块名已声明」——`specs/agent-loop.md:227` 行原文） |
| 2 | 「POST /api/v2/chat/asks                 200 → text/event-stream（首帧 run_id）」 | specs/agent-loop.md:61 | 存量 `tests/api/test_v2_asks.py::test_v1_wire_form_compatible`（首帧 `session` 字节形） |
| 3 | 「    入参三形态：question 提问｜resume_run_id 重连｜question＋followup_run_id 追问续会话」 | specs/agent-loop.md:62 | 存量 `::test_sse_replay_from_zero_replays_all_events`（重连形态）／`::test_resume_and_followup_together_is_409_not_silent`（②③互斥）／`::test_followup_requires_question` |
| 4 | 「POST /api/v2/chat/runs/{run_id}/resume 200 → text/event-stream」 | specs/agent-loop.md:63 | 存量 `::test_resume_body_shape_guards`／`::test_redecision_clarify_resume`（`::test_resume_error_paths` 属 W5-01b 票面对象行 28——本票只引用不 claim） |
| 5 | 「GET  /api/v2/chat/runs/{run_id}        200 → {status, steps, manifest_digest, pending_ask?}（pending_ask＝挂起帧投影，仅 waiting_ask 在场——V2-78 刷新还原面）」 | specs/agent-loop.md:64 | 人审（读口字段面归本层——`specs/transport.md:141` 行原文「检测＝**人审**（`api` 读口的字段面归 `api` 块）」）＋引用 W5-01a 行 18／W5-01b 行 22 用例不 claim |
| 6 | 「GET  /api/v2/chat/runs?limit=N        200 → [{run_id,question,status,answer,followup_of,created_at,updated_at}]（V2-73 最近任务读口，created_at 降序；followup_of＝追问链前轮——V2-74 对话任务分组，空串＝链根）」 | specs/agent-loop.md:65 | 存量 `tests/api/test_v2_runs_list.py` 四用例（`::test_empty_store_returns_empty_list`／`::test_list_contains_completed_run`／`::test_limit_one_returns_newest_and_large_limit_clamps`／`::test_followup_run_carries_followup_of`） |
| 7 | 「错误：400 参数非法｜401 身份缺失｜404 run 不存在｜409 run 非挂起态不可 resume（重连/追问互斥同 409）」 | specs/agent-loop.md:66 | 存量 `::test_ask_param_and_actor_guards`（400／401）／`::test_get_unknown_run_is_404`／`::test_sse_replay_unknown_run_is_404`／`::test_followup_unknown_run_is_404`／`::test_followup_unfinished_run_is_409`／`::test_invalid_last_event_id_returns_400` |
| 8 | 「- 模块: `orchestration`（业务面只许走其公开接口；**受理三形状 AskRequest／AskChoice／RunHandle 与组合根装配面经其包根 re-export**；组合根 create_app 例外——装配执行器/检查点/网关模型，V2-07 按组合缝采纳）、`transport`、`persistence`（**帧类型与读口行投影面**——SseEvent 帧类型、两读口（run 行／步记录）行投影；**类型/常量面只引形状**，不许引其行为：不自建帧通路、不落盘）、`infra`」 | specs/modules.md:606 | 人审（无专属闸——见票注①；`tools/importlinter_v2.toml` 无 `appv2.api` 侧进口契约） |
| 9 | 「\| `api` 引用 `orchestration` 以外模块 \| `transport`／`persistence`／`state`——**只许类型/常量形状面**（帧类型 SseEvent、读口行投影、Budget 装配形状），行为只经 orchestration \| 端点薄层，编排语义全在运行时 \|」 | specs/modules.md:630 | 人审（登记：`R1–R8` 契约 `source_modules` 均以 runtimev2 块为源、不含 `appv2.api`——`tools/importlinter_v2.toml` :66–:123 亲读属实） |
| 10 | 「- 测试计划: 端点契约/SSE 帧形/断线游标续传/错误码」 | specs/modules.md:612 | 文件级核对面＝`tests/api/` 三文件（`test_v2_asks.py` 20 用例／`test_v2_runs_list.py` 4 用例／`test_v2_composition.py` 组合根两向行为） |
| 11 | 「\| api \| 新增 \| 帧→SSE 的渲染与断线游标的接缝（本块只出帧与游标语义） \|」 | specs/transport.md:32 | 存量 `::test_sse_replay_from_zero_replays_all_events`／`::test_sse_replay_unknown_run_is_404` |
| 12 | 「\| **`session` 首帧的发射时机与载荷**（`{run_id, resume}`，三端点流首恒发） \| `api`（开流段）——本块只保证**帧名在闭世界内**与信封形状 \| `specs/modules.md` `## api`；`synth/S6-事件与帧目录.md` §二；`docs/runtime-refactor/iface/P9a1-端点与帧通路.md`（T-P9a1-07） \|」 | specs/transport.md:22 | 存量 `::test_v1_wire_form_compatible`（首帧字节形 `id/event/data` 三行＋`{run_id, resume}` 逐字） |

> **规格无专属验收行（票注⑤，逐字稿纪律照实登记）**：`specs/agent-loop.md`「验收测试」表 api 侧共 6 行（:193／:194／:198／:202／:204／:205）——W5-01 三票已全量登记（`-01a` 行 17／18／29 与 `-01b` 行 22／26／28；两票「测试文件归属」票注原文均写「落既有文件……`tests/api/test_v2_asks.py`」），本票**不重复 claim、不增设验收行**（增设＝改规格，回设计仓）——故票面对象改以规格**原文行**（端点四行＋三形态＋错误码＋卡面依赖/边界/测试计划＋帧面两行）承载，核对面用**存量用例标识**（该文件另 14 用例＋`test_v2_runs_list.py` 4 用例＋`test_v2_composition.py`，非规格验收行）。
> 跨块登记（票注，呈主窗对账；**不自行增设验收行、不自裁量进口落点**）：① **进口面落点四处——卡面改批后已定（2026-10-16，流水 50／51）**：`api` 卡依赖行（行 8 现文）列 `orchestration`＋`transport`＋`persistence`＋`infra`——受理三形状（卡面签名 `AgentRuntime.ask(q: AskRequest) -> RunHandle`／`resume`——`specs/modules.md:316–:317`）与**组合根装配面**经 `orchestration` 包根 re-export（卡面注原文 `specs/modules.md:320`：「**公开面注（流水 51 卡级修正）**：受理三形状（AskRequest/AskChoice/RunHandle）与装配面经包根 re-export 供 api 消费（2026-10-16，流水 51）。」）；帧类型（`SseEvent`——真源行 11／12）与读面（行 5／6 两读口的 `status/steps/manifest_digest/pending_ask`）经新列支 `transport`／`persistence`（**类型/常量面只引形状**，行为只经 orchestration）；`specs/modules.md:630` 边界行例外列同步放行 `transport`／`persistence`／`state`——**只许类型/常量形状面**（帧类型 SseEvent、读口行投影、Budget 装配形状）。四处落点均有卡面落点，本票按卡面施工、不再另裁量（原「四处均无卡面落点／呈主窗对账」已由卡面改批消化）。② **两读口归属**——**已消化（流水 50/51）**：行 5／6 数据来源在 V2 落到 `persistence` 读面（`specs/persistence.md` 公开面 `run`／`steps`／`blackbox`），卡面依赖行（现引文＝`specs/modules.md:606` 原文「`orchestration`（……）、`transport`、`persistence`（**帧类型与读口行投影面**——SseEvent 帧类型、两读口（run 行／步记录）行投影；**类型/常量面只引形状**，不许引其行为：不自建帧通路、不落盘）、`infra`」）已列 `transport`／`persistence` 读口行投影面，两读口有卡面落点。③ **组合根装配面**——**已消化（流水 50/51）**：orchestration 卡公开面注（现引文＝`specs/modules.md:320`：「**公开面注（流水 51 卡级修正）**：受理三形状（AskRequest/AskChoice/RunHandle）与装配面经包根 re-export 供 api 消费（2026-10-16，流水 51）。」）已覆盖装配面落点——V2 的 `AgentRuntime` 构造／注入形（db／completer／registry／bus／saver）经 orchestration 包根 re-export 供 api 消费；框架类型仍不得出现在本层（`specs/modules.md:324` 行原文「外部: **LangGraph**（ADR-0002 红线①：只许本块内使用；state schema 自有；框架类型不得外泄）」），本票不造构造签名。④ **覆盖率闸 owner 注记**：`config/runtimev2_endpoints.json` 的 E1–E4 `owner` 现记「冻结基线……」（原文）、`config/contract_endpoints.json` 的 V2 三条 `owner` 现记「V2-08 合同挂账登记……」（原文）——是否改挂 `RT-W5-02` 由主窗 manifest 对账批统一处理（本票不动这两份配置）。⑤ 本票未列入票面对象的同行：`specs/modules.md:600–:603` 事件九类闭世界行（取值真源已由 `specs/transport.md` 的 `EVENT_KINDS` 承接，本层只渲染）与 `specs/transport.md:21` 行（「HTTP 鉴权、参数校验、开流前的错误码（400／401／404／409）」归 `api` 开流前同步段——与行 7 同源）——均不重复转抄。

## 测试网钉（**规格无专属 pin 行**——照实登记，不增设）

- `specs/agent-loop.md`「与闸的挂钩表」共 5 条 pin 行（:236–:240＝pin-23／pin-22／pin-24／pin-29／pin-28），已由 W5-01 三票逐字转抄完毕（`-01a` 载 3 行＝pin-23／pin-22／pin-24；`-01b` 载 pin-29；`-01c` 载 pin-28）——本块**无剩余 pin 行可载**，故本票「测试网钉」节照实登记为**规格无专属 pin 行**（登记，不增设）。
- 帧面三钉的 `api` 半边**不重复转抄**（归属已定，同 pin 行只在一票逐字转抄）：pin-29（挂起→resume 闭环）的帧面半边挂 `specs/transport.md` 其挂钩表行、整行已落 `RT-W5-01b-orchestration.md`；pin-09（材料截断披露）与 pin-04（发射 JSON 不进答案）的**帧形面**挂 `specs/transport.md` 其挂钩表两行、行为面归 `specs/answering.md` 与 `specs/state.md` 各自票——本票只作**消费者侧核对**（eng/03 §五 原文「交界归消费者验证」，本层是 `transport` 帧面的唯一消费者）。

## 织网义务（eng/04-测试网设计.md §三 盲区清单**无明写归 `api` 的行**——照实登记）

- eng/04 §三 B1–B7b 逐行归属：B5（帧协议级时序）与 B6（挂起恢复多场景）两关联行已由 `RT-W5-01b-orchestration.md`「织网义务」节逐字转抄（该票原文「B5／B6 两关联行的 L1／L3 钉」）；B1 明写归 `bookkeeping`、B2 明写归 `orchestration`、B2b／B7b 归四相位各票、B3／B4／B7 各有其块——**本块照实登记为无专属行**（登记，不增设）。
- 本票织网义务＝① eng/04 §五 织网工序第 2 步「48 文件改接线」的 **api 面半边**（eng/04 §二 原文：「48 个离线文件本质已是特征测试……重写后改接线（import 面从 `appv2.runtime.*` 改指 runtimev2 17 子包）＋ runtimev2 提供等价替身即可复用」——本层消费面＝`tests/api/` 三文件的 import 面改写）；**旧码测试本批不改**（本批＝阶段 4 拆票，改写属织网②，随本票施工期落）；② 消费者侧核对：`specs/transport.md:137` 行原文「7. **帧与 api 的接缝漂移**（信封／`id`／收场帧三处跨块）→ 对策＝本块出帧与游标语义、`api` 只渲染；检测＝`api` 块定稿时的对照（**人审**，登记）」——**本票即该「定稿时的对照」的落点**；③ L2 新规格钉不入门（eng/04 §五 原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

## 施工要点（规格原文行骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/agent-loop.md:150 | 行为 8 命令受理（H3） | 原文「**命令受理（H3）**：`ask`／`resume` 是唯一入口——**`RunCommand → 执行器 → RunEvent` 为显式接缝**（将来换队列消费者，`api`／`tools`／事件契约零改动）」——本层＝该接缝的消费侧，端点形与错误码零改动 |
| specs/transport.md:81 | 行为 3 游标一处编号 | 原文「**响应内不再另起计数器**（治现状「首段／resume 段／重放流三套编号互不同源」的历史缺陷）」——本层现自建帧号（`appv2/api/bridge.py`）按此收口 |
| specs/transport.md:154 | 与闸的挂钩表 禁手写行 | 原文「\| 禁手写第二套帧通路 \| **无专属闸 → 人审**（降维：信封实现单点断言） \| 登记待补 \|」——`api` 只做渲染，不建第二套帧通路 |
| specs/transport.md:139 | 风险 9 背压 | 原文「**本批不新增背压机制**，定性归 `api`（SSE 流桥）——**呈主窗定性**，落地时在 `api` 规格登记。检测＝**人审**」——登记为对账条目，本票不落背压机制 |
| specs/transport.md:141 | 风险 11 帧 vs 步记录字段不同源 | 原文「检测＝**人审**（`api` 读口的字段面归 `api` 块）」——读口字段面归本票（与票注②同源） |
| specs/modules.md:610 | `## api` 卡 Seam 行 | 原文「Seam: HTTP 接口（tests/api 接口级测试，不起真实端口）」＋`:611` 行原文「Adapter: FastAPI TestClient」——核对面＝接口级测试，不起真实端口 |
| specs/agent-loop.md:57 | 接口定义 `RunHandle` | 原文「RunHandle  = {run_id: str, stream: AsyncIterator[SseEvent], cursor: int}」＋`:58` 行原文「#   cursor＝**全流单调**断线游标（重放不位移）」——本层消费侧接受此形态 |
| specs/agent-loop.md:59 | 接口定义 事件枚举 | 原文「# 事件枚举: step/text/tool/observation/ask/verdict/citation/notice/blackbox（九类闭世界；真源 `synth/S6-事件与帧目录.md`）」——本层只按闭世界渲染 |
| specs/agent-loop.md:159–:160 | 行为 9 run 状态机（开流前错误包；该条起 :157） | 原文（跨行整句）「追问（followup_run_id）＝会话线程新轮——前轮消息历史（含问答/执行台账）随追问进新 run 上下文，前轮须 completed（404/409 开流前错误包）」——行 7 的四条错误路径即此表 |

验收: 以下判据逐条全绿为过——
- 「票面对象」12 行逐行在场且逐字一致（行 1–12），每行按其「核对面」列核（存量用例标识或人审）——**规格无专属验收行**（票注⑤登记，不增设）；
- 进口面切换：`grep -n "appv2\.runtime" appv2/api/*.py` **零命中**（八处旧进口全清；新进口落点按票注①／③对账结论）；
- 端点契约不破：四端点路径与四错误码（行 2–7）／入参三形态／`session` 首帧形（`{run_id, resume}`）逐字不变——存量用例改接线后全绿（`tests/api/test_v2_asks.py` 20 用例＋`test_v2_runs_list.py` 4 用例＋`test_v2_composition.py`；其中 6 用例＝W5-01 三票票面对象，本票只保证其经本层跑通、不改其断言）；
- 覆盖率闸 V2 面绿：`python3 tools/contract_coverage.py check`——E1–E4 四端点「实现有/清单无」＝0（`config/runtimev2_endpoints.json` 冻结基线；该闸 `V2_API_DIR = appv2/api` 实读本层路由）；
- 帧通路收口：本层零自建帧号／游标计数器／第二套帧通路（帧对象、信封、游标只在 `transport` 实现——`specs/transport.md:154` 行原文；检测＝AST／grep 断言「帧信封实现只在该包外的 `transport` 出现一次」）；
- 边界：既有契约不红——`lint-imports` 双配置绿（V1 侧「ADR-0002 红线①langgraph 只许在 appv2.runtime」契约 `tools/importlinter_v2.toml:49–:53`（`source_modules` 含 `appv2.api`）KEPT＋V2 侧 18 契约 KEPT 基线不红）；本层 SSE 帧不携带框架类型（`appv2/api/__init__.py:7–:8` 现状自述原文「SSE 帧不携带 langgraph 类型（ADR-0002 红线①——载荷全 JSON 原语）」）；
- 「`api` 引用 `orchestration` 以外模块」（行 9）**无专属闸 → 人审**（登记：`R1–R8` 契约 source 不含 `appv2.api`）；
- 回报附 pytest 全量输出与 `lint-imports` 输出原文。

回报: 完成后回主窗——「RT-W5-02 完成，产物 `appv2/api/`（六件＋包根改接 runtimev2＋SSE 桥收口），进口面零命中旧包，偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
