# RT-W5-01c · orchestration——V2 编排（-C：收口与红线收束簇：三态落库／收敛收口／审计与身份缝／检查点 saver 组合／边界·保留集）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/agent-loop.md`（状态「已定稿」——前置满足）
Touches modules: `orchestration`（本票只填 orchestration 的收口与红线收束簇；规格「触及的模块」表另声明 bookkeeping／preconditions／context／verification／persistence／api／tools 七关联侧，归各自票承接）
波次: W5（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W5 行三列原文：块列「`orchestration`」；理由列「依赖全部相位＋persistence/transport/bookkeeping，天然最后」；出口判据列「有界终止；挂起恢复；相位顺序只由本块决定」）
复审强度: 100%（eng/03 §五 流水 48 规则，质量关键块全复审——§五 W5 行理由列原文：「系统性缺陷藏匿点；在关键路径末端，B 的慢不阻塞人」；§五 头注原文「B 列六块＝质量关键块施工后 100% 复审……波序与块归属不变」；复审网在 L0 直派、报告直送主窗——§五 扣件④原文「复审网在 L0 直派（复审代理不经过 Kimi-A、报告直送主窗）」）
前置: ① 规格定稿（`specs/agent-loop.md` 已定稿——已满足）；② **`RT-W5-01b-orchestration.md` 收票**（同包顺序施工、同包不并行；收口挂在 -01a 落地的图与执行器接缝、-01b 落地的挂起—恢复链上——本票不另立第二套形状）；③ W1–W4 全收波（经 -01a／-01b 传递，已满足）
阻塞: `RT-W5-01b-orchestration.md`（-01c 前置＝-01b 收票）｜被阻塞: 切换（eng/03 §三 切换前提原文：「W1–W5 全绿 ＋ 特征钉全绿 ＋ **重写出口判据达成**（Owner 已裁＝《规划》§八-B 题二 A：Q17 复考检索域 ❌=0、全卷 ❌≤5＋六闸全绿＋合同覆盖率 V2 面无缺口＋真机多轮前缀延伸不回归）＋ 生产冒烟通过」——本票为 W5 收波的最后一块）

## 任务

接 `RT-W5-01a-orchestration.md`／`RT-W5-01b-orchestration.md` 落地的骨架与挂起恢复链，把**收口**接实：run 走完四相位后由本块**决定并落**三态（`completed`／`failed`／`waiting_ask`）、预算触界时**收敛交付**（已取得材料＋未完成项 notice，不静默截断）、完成判定不出模型之手（规格原文 `specs/agent-loop.md:171`：「**不许自述完成**：模型只能**申请**完成，**提交完成的是本块**（依据核验结果）」）；同时把**红线收束**落到断言：全程业务事实零写（INV-2）、审计走 `security.audit` 唯一写口、身份解析走单一入口、零 LLM 双证扫描、检查点 saver 组合只在本块且不直连表。

**本票＝orchestration 的 -C 票**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **36 行**（`specs/agent-loop.md:177–:212`），超 15 行上限 → 切 -A／-B／-C 三票；本票收 **11 行**＝规格表第 5、23–25、27、30–33、35、36 行（零 LLM 双证扫描／核验收口与收敛交付／跨进程恢复与 saver 组合／只读与三态落库／审计与身份缝／边界·保留集）；另 25 行与 4 条 pin 行在 -01a／-01b，本票**只承载 1 条 pin 行**（pin-28，逐字转抄见「测试网钉」节），其余 4 条 pin 行不重复转抄。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/agent-loop.md` 全文（241 行十节版式）；`specs/persistence.md`（三态落库的调用侧与读写口、检查点可恢复面、黑匣子只追加幂等——行 27 的**框架无关行级口**真源，saver 组合在本块）；`specs/bookkeeping.md`（`converge` 触界收敛落地六键、`direct_answer` 完成收口旁路恒写三键、`notice` 通知恰三键——行 25 的落地面与「不静默截断」材料面）；`specs/infra.md`（`security.audit` 唯一写口与责任账五处留痕（其行为约定 3）、`infra.security.resolve_actor` 身份缝、`infra.clock` 时钟——行 32／33）；`specs/state.md`（run 状态四值与终态取值闭世界、`answer`／`manifest_digest` 字段面、`check_limits` 判定面）；`specs/verification.md`（`Verdict.ok` 与改写／notice——行 23／24 的消费面：本块据此收口、核验器本体不在本块）。eng/04 §三 B3 行已在本票「织网义务」节逐字转抄，施工期不必另开。

**小票制自检（流水 48）**：票面对象 11 行 ≤ 15 ✓；先读 6 份 ≤ 6 ✓；聚焦一个行为簇＝收口收束链（收口时点→终态落库→审计留痕→只读与边界断言）✓ → 本票不派生。

框架红线: **LangGraph（含 `langchain*`）只许活在本块**——本块是 17 块中**唯一**允许框架的块（其余 16 块禁引）；对应闸 **R5b 契约**（`tools/importlinter_v2.toml` :100–:107，`forbidden_modules` 含 `langgraph`／`langchain`／`langchain_core`／`langchain_community`）。规格原文（`specs/agent-loop.md:71`）：「**框架只许本模块内部**：LangGraph（含 `langchain*`）**不得渗漏出本模块**；state schema 自有（`RunState` 为自有 dataclass，框架只当 schema 消费）」。**检查点 saver 组合＝卡面职责行的本块专责**（`specs/modules.md` `## orchestration` 职责行原文：「编排与执行——图装配与路由、命令受理与执行器、挂起恢复、**检查点 saver 组合**（LangGraph PG saver 实现——组合 `persistence` 的框架无关行级口，不直连表）」）；框架类型（`BaseCheckpointSaver` 一族）只许在本块出现，且**不得直连表**（行 27）。
边界红线: ① **模型调用发起面＝`bookkeeping.call_model`（单点发起；其内部唯一出口＝`gateway_adapter`）**：不直引 `gateway_adapter`、不直引 `appv2.infra.llm_client`、不自建模型客户端——**R7 契约**（:114–:119）＋「无旁路」行为断言；② 只经 `tools` 公开面接触世界、不直引引擎——**R6 契约**（:108–:112）；③ 只经 `transport` **包根**发帧（不自行拼 wire 帧）：**R2 契约不覆盖本块**（source 只含七个业务相位）→ **无专属闸 → 人审**（规格挂钩表 :234 行）；④ **禁手写替代**：不得自建图执行器旁路、不得自建模型客户端、不得自建帧通路——R5b／R7 可降维面＋余面**人审**（:235 行）；⑤ **统一出口三处**：审计唯一写口 `security.audit`（B12）、身份只经 `infra.security.resolve_actor`（身份桩——规格 :154 原文「开发期身份桩；正式接 OAuth2.0 **只换该函数实现**，其余零改动」）、时间只经 `infra.clock`（B14）——本块不自开旁路；⑥ 不引旧码 `appv2.runtime`——**R5 契约**（:95–:100）；⑦ **只读铁律（INV-2）**：全程零业务事实写入（run 簿记表 `agent_v2_*` 除外）；⑧ 三态落库的**值域**不在本块定：`RunRecord.status` 四值由 `persistence` 侧把守（`specs/persistence.md:139` 原文「`RunRecord.status` 写入值必须 ∈ `RUN_STATUS_KINDS`（四值）」），本块只决定写成哪个终态

## 票面对象（specs/agent-loop.md「验收测试」表逐行转抄——本票 11 行：规格表第 5、23、24、25、27、30、31、32、33、35、36 行）

〔来源：specs/agent-loop.md「验收测试」表 :181–:212（本票取自 :181、:199–:201、:203、:206–:209、:211–:212），逐行原文；`#` 列＝规格表行序（与 -01a／-01b 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 5 | 前置条件机零 LLM（AST＋import 双证扫描） | `tests/domains/test_v2_four_phase.py::test_precondition_and_parse_layers_are_zero_llm` | specs/agent-loop.md:181 |
| 23 | 断言无 Observation 支撑→verify 改写为"未找到"＋notice | `tests/domains/test_v2_agent_verify.py::test_unsupported_claim_rewritten` | specs/agent-loop.md:199 |
| 24 | 矛盾两来源→答案分源列明各带 citation（INV-4） | `tests/domains/test_v2_agent_verify.py::test_contradiction_split_source` | specs/agent-loop.md:200 |
| 25 | 预算触界→收敛答案＋未完成项 notice，无静默截断 | `tests/domains/test_v2_agent_loop.py::test_budget_termination` | specs/agent-loop.md:201 |
| 27 | run 挂起态跨进程恢复（checkpoint 落 PG） | `tests/domains/test_v2_agent_loop.py::test_run_recover_after_restart` | specs/agent-loop.md:203 |
| 30 | 全程业务事实零写（run 簿记表 agent_v2_* 除外，INV-2） | `tests/domains/test_v2_agent_loop.py::test_readonly_inv2` | specs/agent-loop.md:206 |
| 31 | 三态落库（completed／failed／waiting_ask 写 run 表） | `tests/domains/test_v2_agent_loop.py::test_three_terminal_states_persisted` | specs/agent-loop.md:207 |
| 32 | 审计留痕经 `security.audit` 唯一写口（**action 闭世界七值**，计数只此一个口径） | `tests/domains/test_v2_agent_loop.py::test_audit_wiring_action_closed_world` | specs/agent-loop.md:208 |
| 33 | 身份缝单一入口（身份解析只经 resolve_actor） | `tests/domains/test_v2_agent_loop.py::test_identity_seam_single_entry` | specs/agent-loop.md:209 |
| 35 | 【边界集】挂起／中断／预算触界／换链回炉／坏引标 → 各自落到对应分支 | `tests/domains/test_v2_four_phase.py::boundary_suspend_interrupt_budget_rewire_bad_cite` | specs/agent-loop.md:211 |
| 36 | 【保留集】普通提问四相位收口行为不变（无挂起、无触界、无回炉） | `tests/domains/test_v2_four_phase.py::retention_plain_four_phase_unchanged` | specs/agent-loop.md:212 |

> 测试文件归属（票注，非规格引文，呈主窗对账）：本票 11 行的测试标识**落既有文件**（`tests/domains/test_v2_agent_loop.py` 6 行、`tests/domains/test_v2_four_phase.py` 3 行、`tests/domains/test_v2_agent_verify.py` 2 行——`ls` 实测三文件均在册），属 eng/04 §二／§五 的**存量测试改写面**（改接线：import 面从 `appv2.runtime.*` 改指 runtimev2 17 子包）；**旧码测试本批不改**（本批＝阶段 4 拆票，改写属织网②）。
> 跨块登记（票注，呈主窗对账；**不自行增设验收行**）：行 23／24 的测试标识落 `tests/domains/test_v2_agent_verify.py`——`specs/verification.md` 节尾原注照抄：「**测试文件归属（与既有 `tests/domains/test_v2_agent_verify.py` 的关系）**：本块验收测试绑**新建**的 `tests/domains/test_v2_verification.py`……与既有 `test_v2_agent_verify.py`（现状 agent-loop 核验步：`verify_draft` 直测／表格·血缘卡·fragment 承载豁免现状行为）所测形状不同；故本块落新文件，既有文件继续覆盖现状核验步、本批不改」——故本票行 23／24 是**核验结果的收口侧断言**（本块据 `Verdict` 收口），核验器本体与本块新建测试文件的边界呈主窗 manifest 对账。行 5 的测试对象＝`preconditions`／`parsing` 两层的零 LLM 双证（该两面各归其块），本块侧承载编排层不引入 LLM 判定这同一红线。
> 行序缺口说明（票注）：本票行序跳过 1–4、6–22、26、28、29、34——`#` 列三票共用规格表行序，便于 manifest 逐行对账。

## 测试网钉（specs/agent-loop.md「与闸的挂钩表」pin 行逐行转抄——本块 5 行，本票承载 1 行，余 4 行归 -01a／-01b）

〔来源：specs/agent-loop.md「与闸的挂钩表」:240，逐行原文；列名同规格「本规格的硬要求｜挂钩｜现状」〕

| 本规格的硬要求（原文） | 挂钩（原文） | 现状（原文） |
|---|---|---|
| run_id 全盖章（计费可对账） | 钉 **`pin-28`**（P1） | 待织网 |

- 分工注（票注，防两头认）：`pin-28`＝**全盖章面**（本票行 31／32 承载——三态落库与审计留痕的记录都携 `run_id`；规格行为 10 原文 `specs/agent-loop.md:162`：「每个 run（及其子问题）盖 `run_id`，逐题 `ledger_run_ids` 集合与 jsonl 账的 `run_id` **等值**（计费可逐题对账）」）；**落盘面**在 `specs/persistence.md`（其挂钩表 :218 行原文：「`run_id` 全盖章、可对账（**落盘面**）」／「钉 **`pin-28`**（P1；全盖章面挂 `specs/agent-loop.md`）；测试 `::run_id_stamped_across_records`」）；**调用盖章面**在 `specs/gateway_adapter.md`（其挂钩表 :152 行原文：「每次调用 `run_id` 盖章、计费可对账（**调用盖章面**）」）；`specs/state.md:198` 钉的字段面分工注原文：「`pin-28`（`run_id` 的**字段面**←本块；全盖章与计费对账面←`specs/agent-loop.md`）」。
- 本块 pin 行分布（防两处漂移，逐字稿纪律）：本块 5 条 pin 行＝pin-23／pin-22／pin-24（`RT-W5-01a-orchestration.md`）＋ pin-29（`RT-W5-01b-orchestration.md`）＋ pin-28（本票）——**同一 pin 行只在一票逐字转抄**，其余票只写核对关系（先例 `RT-W4-05b-execution.md` 分票理由原文：「同一 pin 行在两票重复转抄＝两处真源必漂移」）。
- 规格「与闸的挂钩表」其余行（spec gate／人审两行／R5b／R7／R6／R2 人审行／真源引用闸）非 pin 行，本票不转抄。

## 施工要点（specs/agent-loop.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/agent-loop.md:149 | 行为 8 三态落库（H3）＋审计接线（H3）＋身份缝（H3） | `completed`／`failed`／`waiting_ask` 三态由本块写 run 表（`answer`／`manifest_digest` 随三态落）；受理／三态收口／拒答收口／外表审批决定／禁用词豁免**五处留痕**都经 `security.audit` 唯一写口（**计数口径以「action 闭世界七值」为准**，**本处不写类数**）；请求身份经 `infra.security.resolve_actor` 解析 |
| specs/agent-loop.md:137 | 行为 7 预算闸（触界即收敛） | 触界即收敛——交付已取得观察材料（未核实的直排标注"未及核验"，非断言不违反 INV-1）＋notice 明示未完成项，**不得静默截断**；单段时限 300s／单工具超时 30s（数值真源 `recon/K` R-K-74，本规格不复述） |
| specs/agent-loop.md:131 | 行为 5 核验收口（verify） | 逐条检查阐述草稿的断言有 Observation 支撑；无支撑断言改写为"未找到/材料未披露"并出 notice——**禁止无据断言进答案**（INV-1、INV-4；表格行／血缘卡／fragment 承载豁免随 P-024b 口径继承）；本块据 `Verdict.ok` 决定回炉或收口 |
| specs/agent-loop.md:162 | 行为 10 `run_id` 全盖章 | 每个 run（及其子问题）盖 `run_id`，逐题 `ledger_run_ids` 集合与 jsonl 账的 `run_id` 等值（计费可逐题对账） |
| specs/agent-loop.md:169 | 不降级与静默禁令 机读信号 | 三态落库、挂起、预算触界、审计**都必须产生机读信号**：事件帧（九类闭世界）＋ step payload ＋ `security.audit` 责任账 |
| specs/agent-loop.md:170 | 不降级与静默禁令 触界不得静默 | 预算到顶时交付已取得材料 ＋ notice 明示未完成项（与行为 7 同源）；红线原文 `docs/runtime-refactor/arch/P7a-交接包与挂账清单.md`（A-P7a-37） |
| specs/agent-loop.md:122 | 行为 3 拒因回喂（无 repair） | schema 校验失败＝拒因回喂重发射，**无 repair**；同参重投闸落 `execution`（dispatch 统一出口），本块保留**轮数闸／自旋收敛的预算面层** |
| specs/agent-loop.md:171 | 不降级与静默禁令 不许自述完成 | **模型只能申请完成，提交完成的是本块**（依据核验结果）——三态终值由本块写、不由模型文本触发 |
| specs/agent-loop.md:134 | 行为 6 caliber_key 三态（**不涉面**——防一头两认） | 口径三态的判定归 `preconditions`（该行验收由 -01a 行 6 承载）；本票不复制其取值与判据 |

结构锚：specs/agent-loop.md:46–:67 接口定义（`RunHandle`／四端点与错误码；`GET /api/v2/chat/runs/{run_id}` 返回 `{status, steps, manifest_digest, pending_ask?}`——行 31 三态与 `answer`／`manifest_digest` 的读面）；:166–:171 不降级与静默禁令（**三态落库／挂起／预算触界／审计四者必产机读信号**；**不许自述完成**——提交完成的是本块）；:214–:221 依赖与风险（风险原文：「LangGraph checkpointer 的 PG saver 与 V1 表共存（新表前缀 agent_v2_ 隔离）」——行 27 的表前缀隔离面）；`specs/modules.md` `## persistence` 卡注原文：「① **框架类型不进本块**——`langgraph` 的 PG saver（`BaseCheckpointSaver` 实现，需框架类型）归 `## orchestration`……**本块出框架无关的检查点三表行级读写口**，编排块 saver **组合本口、不直连表**」（行 27 的 saver 组合契约）。规格「与闸的挂钩表」末行（**人审**，:241）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。
规格侧缺口登记（票注，呈主窗对账；**不自行增设验收行**——增设＝改规格，回设计仓）：① 行为 7 的「**单段时限 300s**」与「**单工具超时 30s**」两限额在「验收测试」表**无专属验收行**（表内只覆盖轮数（行 10）／发现预算（行 11）／免轮例外（行 12）／触界收敛（行 25））——数值与计时口径真源 `recon/K-上下文事件指南预算.md` R-K-74，本票不复制；② 行为 8 的审计五处留痕（`specs/agent-loop.md:153`）在表内只有行 32 一条断言（action 闭世界七值＋唯一写口），五处各自的时点断言无专属行；③ 行为 5 的承载豁免面（表格行／血缘卡／fragment 豁免随 P-024b 口径继承）无专属行——归 `verification` 侧；④ **`gate` 早退收口链尾收口时点**（`specs/gate.md` 风险 2 原文：「**收口行为面承接缺口**……**回提登记**（understanding 补承接，或主窗裁定落 `orchestration`；本规格持行为与断言、执行者以落地为准）」＋其风险 7⑧ 原文「链尾收口时点（agent-loop 未明写——随②对账登记）」）——**本规格未明写该时点**，本票只登记该缺口、不自行增设验收行、不自创时点。
本块不涉面（防一头两认）：行 1–4、6、7、13、16–21、29、34 归 `RT-W5-01a-orchestration.md`；行 8–12、14、15、22、26、28 归 `RT-W5-01b-orchestration.md`。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单（本块明写归块行为 B2、已由 -01a 逐字转抄；下列为逐字转抄的关联行）〕

> | B3 | H8 预算四限额边界（现只钉了 CLARIFY_ASK_CAP=6） | 每限额上限/触顶收敛行为钉（数值只引预算表） | 中 |

- 归块注（呈主窗对账）：B3 的**触顶收敛半面**＝本票行 25（预算触界→收敛答案＋未完成项 notice，无静默截断）——落地写口＝`bookkeeping.converge`（RT-W3-01a/b/c 行为 12）；**键集与数值半面**归 `state`（RT-W1-01a/b 预算表／`check_limits`），**轮与路由面**归 `RT-W5-01b-orchestration.md`（其行 11／12 的探查预算与免轮例外）；切分呈主窗对账。
- 关联行（逐字转抄落他票，本票不重复）：B2（`_ROUTES` 路由表逐项，§三表内明写归 `orchestration`）逐字转抄落 `RT-W5-01a-orchestration.md`；B5／B6 逐字转抄落 `RT-W5-01b-orchestration.md`；B1（公共位与结果归一，明写归 `bookkeeping`——钉法＝经 checkpoint 快照／帧流钉「每步通道值归一形」）已由 `RT-W3-01a/b/c-bookkeeping.md` 逐字转抄，本票不另抄；**但本票行 27 的 checkpoint saver 组合是该钉的观测口**（checkpoint 快照由本块 saver 落）——如此链关系登记，切分呈主窗。
- 本票织网义务＝① B3 触顶收敛半面的 L1／L3 钉（织网工序第 3 步「盲区补钉」，与 W1–W4 施工可并行——eng/04 头注）；②「测试网钉」1 行（pin-28）对应用例落网；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」11 行逐行实现为对应既有测试文件用例并全绿（`tests/domains/test_v2_agent_loop.py` 6 行、`tests/domains/test_v2_four_phase.py` 3 行、`tests/domains/test_v2_agent_verify.py` 2 行），测试标识与规格列逐字一致（`#` 保留规格表行序 5、23–25、27、30–33、35、36，含【边界集】／【保留集】两行）；
- 「测试网钉」pin-28 行对应用例在场且绿（本票不重复转抄 pin-23／pin-22／pin-24／pin-29）；
- 收口三面断言绿：三态落库（行 31，`answer`／`manifest_digest` 随三态落、值域由 `persistence` 侧把守）＋触界收敛交付（行 25，notice 明示未完成项、无静默截断）＋审计唯一写口（行 32，五处留痕经 `security.audit`、action 闭世界七值）；
- 检查点 saver 组合契约绿（行 27）：saver 只在本块、**组合 `persistence` 的框架无关行级口、不直连表**（AST 断言：本块零裸 DB driver／零表级直连符号），表前缀 `agent_v2_*` 隔离；
- 只读铁律（行 30）＋身份缝单一入口（行 33）＋零 LLM 双证（行 5）三条红线断言绿；
- 边界闸 R5／R5b／R6／R7 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；「只经 `transport` 包根」与「禁手写替代」两面按规格挂钩表原文走**人审**；
- 形状单点：三态取值／`RunHandle`／接缝仍以 -01a／-01b 落地的与 `state`／`persistence` 卡面为唯一真源，本票不改形状（改形状＝回设计仓）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W5-01c 完成，产物 `appv2/runtimev2/orchestration/`（收口与红线收束簇：三态落库／收敛收口／审计与身份缝／saver 组合／边界·保留集），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
