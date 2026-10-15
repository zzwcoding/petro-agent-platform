# RT-W4-01a · understanding（-A）——读题：任务书装配＋解析＋定路由＋机械分派

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/understanding.md`（状态「已定稿」——前置满足）
Touches modules: `understanding`（本票在既有占位骨架 `appv2/runtimev2/understanding/` 上实现 -A 半面；规格「触及的模块」表另声明 prompts／parsing／gate／bookkeeping／gateway_adapter／state／tools 七关联侧，归各自票承接）
波次: W4 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W4 行三列原文：块列「七个业务相位（understanding → clarification → tool_matching → preconditions → execution → answering → verification）」；理由列「互零依赖，**建议按业务链序施工**（便于走查 narrative 与测试网逐块加厚），不禁止并行」；出口判据列「每相位配属规格十节版式定稿＋新规格钉绿＋触及该相位的特征钉绿」；本块＝链序第 1 位（understanding，次位 clarification）
复审强度: 50% 抽查（eng/03 §五 流水 48 规则；W4 行 A 列含 `understanding`——该表降级保留的规则原文「A 列抽 50%」，双队制已废止、A/B 分配只余复审强度语义，波序与块归属不变）
前置: ① 规格定稿（`specs/understanding.md` 已定稿——已满足）；② 波次前置：**W1＋W2＋W3 全收波**（eng/03 §一依赖图：understanding → gate ＋ prompts ＋ parsing ＋ gateway_adapter ＋ state；模型调用发起面 `bookkeeping.call_model` 归 W3——W2 的 gateway_adapter 测试替身与 W3 的 bookkeeping 单写口是相位测试地基）；③ W4 硬前置＝本块触及的特征钉已钉好（eng/03 §四原文：「W4 每相位开工的硬前置＝该相位触及的特征钉已钉好」）；④ 票内前置：无（-A 为本块首票；占位骨架 `appv2/runtimev2/understanding/__init__.py` 已随阶段 2 落锤）
阻塞: 无（-A 可开工，硬条件＝W1／W2／W3 全收波）｜被阻塞: RT-W4-01b（-B 前置＝「-A 收票」——骨架与接口在位后 -B 才动工；同包不并行）＋W5 `orchestration`（eng/03 §一依赖图：orchestration → 七个业务相位）

## 任务

按 `specs/understanding.md` 实现 -A 半面：**任务书三区装配（指令区→数据区→输出契约区）→ 经 `bookkeeping.call_model` 单点发起模型读题 → 统一 JSON 严格解析（无降级）→ `route` 闭世界定型 → 程序只按 `route` 机械分派 → 理解文本发 `text` 事件**；含解析不合格的唯一转译出口（`parse_understanding` 返 `None` → 本块抛 `UnderstandingParseError`）与「如实上报」机读信号面。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

**拆分理由（小票制，流水 48／eng/03 §五 双队制废止后的小票制）**：本块规格「验收测试」表共 **16 行 > 15 行上限**（Owner 定判据：票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇）→ **拆 -A／-B 两票**：
- **-A＝骨架＋接口＋核心行为簇**（任务书三区装配／数据区活体投影／解析严格／`route` 闭世界／按 `route` 分派／单出口互斥／候选出自名录／每 run 只装配一次＋模型原话不进对话层／`text` 事件／如实上报信号）＋**本块全部织网钉**（pin-26，唯一 pin 行）；票面对象 11 行。
- **-B＝剩余行为簇**（直答结构核验闭世界＋fail-closed 默认）＋【边界集】【保留集】两行；票面对象 5 行。
- 两票**同包顺序施工**（-B 前置＝-A 收票），不并行；-A 不收票则 -B 不动工。

先读:（6 份；其余引用面随用随查、不入必读）`specs/understanding.md` 全文（136 行，十节版式）；`specs/modules.md` `## understanding` 卡（:130–:147，签名以卡为准；含 Seam＝决策出口／Adapter＝剧本化 completer／测试计划行）；`specs/parsing.md`（`parse_understanding` 与「理解面不合格 → `None`」——本块唯一转译出口的对接面）；`specs/prompts.md`（任务书三区合同文本与样例集来源——装配消费面）；`specs/bookkeeping.md`（`call_model`／`note`／`append_message` 单点面——本块唯一模型入口与过程档案写入面）；`specs/state.md`（`RunState` 形状、`text` 事件与预算字段——只消费）
（另：`specs/tools.md` 仅在取指标名录／结构卡公开面时随用随查；`specs/gate.md` 的入口闸结论由本块消费、其实现归 W3 票——两者不入必读清单。）

框架红线: **无点名框架**（本模块不引入任何框架）；**不得直接 import `langgraph`／`langchain`**（框架只许在 `orchestration`）——对应闸 **R5b 契约**
边界红线: ① **模型调用发起面＝`bookkeeping.call_model`（单点发起，禁手写替代），其内部唯一出口＝`gateway_adapter`**——本块不直引 `gateway_adapter`、不直引 `appv2.infra.llm_client`、不自建模型客户端、不得绕过发起面直连上游（import 落点＝`appv2.runtimev2.bookkeeping` **包根**——R2 禁深层子模块）——R7 契约＋「无旁路」行为断言；② **只经 `tools` 公开面**接触世界（指标名录经 `semantic_query`、表名经 `table_schema` 发现面，不直引引擎）——R6；③ 相位互不 import（R1，只经 `state` 形状与 `orchestration` 编排接口）；④ 不落盘（本块不写库、不写文件——落盘归 `persistence`）；⑤ **本块零语义判断**：程序不判语义（无词表／正则），只按 `route` 分派——AST 机检 `::no_lexicon_or_regex_in_understanding`（豁免面＝形态处理：数字形判定与集合成员判定不算语义词表／正则）；⑥ 禁手写替代：不得绕过 `bookkeeping` 写口直改状态字段（写口单点面由 `specs/bookkeeping.md` 承接）

## 票面对象（specs/understanding.md「验收测试」表逐行转抄——本票 11 行：规格表行序 1／2／5／6／7／8／9／10／11／12／13）

〔来源：specs/understanding.md「验收测试」表 :96–:111，逐行原文；`#` 列＝规格表行序（与 -B 票同一行序、不重编），逐字转抄、未改一字；未取 5 行（行序 3／4／14／15／16）归 RT-W4-01b〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | route=full 时返回 Understanding，且候选全部出自名录 | `tests/domains/test_v2_understanding.py::full_route_candidates_in_roster` | specs/understanding.md:96 |
| 2 | 候选出现名录外名字 → 判违约（不静默丢弃） | `tests/domains/test_v2_understanding.py::candidate_out_of_roster_violates` | specs/understanding.md:97 |
| 5 | 应答 JSON 不合 schema → 抛 UnderstandingParseError，不静默降级 | `tests/domains/test_v2_understanding.py::malformed_json_raises_no_fallback` | specs/understanding.md:100 |
| 6 | route 越界取值 → 判失败（不猜、不取默认） | `tests/domains/test_v2_understanding.py::route_enum_closed_world` | specs/understanding.md:101 |
| 7 | 任务书三区顺序正确、数据区标来源且置于末尾 | `tests/domains/test_v2_understanding.py::task_book_three_zones` | specs/understanding.md:102 |
| 8 | 台账投影变化 → 数据区文本随之变 | `tests/domains/test_v2_understanding.py::data_zone_from_live_projection` | specs/understanding.md:103 |
| 9 | 任务书每 run 只装配一次；模型原话不进对话层 | `tests/domains/test_v2_understanding.py::assembled_once_raw_not_in_dialogue` | specs/understanding.md:104 |
| 10 | 程序只按 route 分派（换任意 route 取值都不触发词面判断） | `tests/domains/test_v2_understanding.py::dispatch_by_route_only` | specs/understanding.md:105 |
| 11 | 程序侧无词表／正则语义判断（AST 扫描本模块；**豁免面＝形态处理**——数字形判定与集合成员判定不算语义词表／正则） | `tests/domains/test_v2_understanding.py::no_lexicon_or_regex_in_understanding` | specs/understanding.md:106 |
| 12 | 「如实上报」的机读信号在场（notice ＋ step payload 字段） | `tests/domains/test_v2_understanding.py::reporting_signal_present` | specs/understanding.md:107 |
| 13 | 理解文本发 `text` 事件（kind=understanding） | `tests/domains/test_v2_understanding.py::understanding_text_event_emitted` | specs/understanding.md:108 |

> 测试文件归属（据规格逐行原文的标识路径照录）：本块验收测试绑**新建** `tests/domains/test_v2_understanding.py`（仓内现不存在此文件——本块为阶段 2 新划的相位块 `appv2/runtimev2/understanding/`，与旧 `appv2/runtime/` 旧码测试形状不同）；旧码测试本批不改。
> 跨文件钉（-A 验收面之一，规格「依赖与风险」风险 4 检测手段原文）：`tests/domains/test_v2_parsing.py::understanding_malformed_none_no_fallback`——转译输入半面的对读件，与本票行 5 同批在场。

## 测试网钉（specs/understanding.md「与闸的挂钩表」pin 行逐行转抄，1 行）

〔来源：specs/understanding.md「与闸的挂钩表」:127–:136，pin 行〕

1. **对话层纯度（dialogue 只装自然对话，过程记录入 process_notes 不混层）**｜钉 **`pin-26`**（落点＝行为 9 模型原话不进对话层——只进过程档案与留痕）｜现状：待织网（阶段 5）

> - 〔附：钉本体原文行，`eng/04a-应钉行为清单.md:35` 逐字照抄〕
> | 26 | 对话层纯度：dialogue 只装自然对话，过程记录入 process_notes 不混层 | P8b2:63（23/23）；`P5b1-对话状态重构方案.md` | 单元 | P1 |
> - 分工（防一头两认）：pin-26 **写入面**挂 `specs/bookkeeping.md`（`::dialogue_port_purity`，RT-W3-01a/b/c 承接）、**字段面**挂 `specs/state.md`（行为 6）、本块落**渲染面**（行为 9＝模型原话不进对话层）。本票只验本块半面：模型原话经过程档案（`note`）留痕、`dialogue` 零写入。
> - 本块规格挂钩表内其余行（R5b／R6／R7 三闸行、spec gate 两行、`::no_lexicon_or_regex_in_understanding`＋`::direct_with_assertion_rejected`＋`::reporting_signal_present` 三测试行、人审行）非 pin 行、不属本节点转抄范围——闸行现状「已真跑」由 CI 复跑验，测试行现状「待实现（阶段 5）」由本票「票面对象」行 11／12 承接（`::direct_with_assertion_rejected` 归 RT-W4-01b）。

## 施工要点（specs/understanding.md「行为约定」节骨架＋不降级节——file:line 锚＋一句话；本票只覆盖 -A 行为簇）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/understanding.md:69 | 行为 1 任务书分三区且顺序固定 | 指令区（场景／任务／红线）→ 数据区（指标名录／术语表／本体／水位）→ 输出契约区（末尾、短）；断言＝装配输出的三段边界与顺序（`::task_book_three_zones`） |
| specs/understanding.md:70 | 行为 2 数据区每轮从活体投影现取 | 标来源、置于末尾；改 fixture 投影 → 输出文本随之变且带该来源标记（`::data_zone_from_live_projection`） |
| specs/understanding.md:71 | 行为 3 输出契约＝单个 JSON 对象 | 含 `route` 与读题字段；**不使用两行式**（旧的「两行式」文本契约由本规格统一 JSON 取代，下游三消费面一并重写） |
| specs/understanding.md:72 | 行为 4 程序只按 `route` 分派 | 给定任意 `route` 取值，程序行为只由该值决定，不触发任何词面／正则判断（`::dispatch_by_route_only`） |
| specs/understanding.md:78 | 行为 6 单出口互斥 | 一次调用只返回 `Understanding` 或 `Direct` 之一，不存在两通道同时生效 |
| specs/understanding.md:79 | 行为 7 解析严格 | 不合 schema → 抛 `UnderstandingParseError`（携原始应答片段供留痕），**不静默降级**（旧「抠第一个 `{...}` 降级提取」废弃）；`parse_understanding` 返 `None` 在场时由本块转译抛同类错（**唯一转译出口**，`::malformed_json_raises_no_fallback`＋跨文件 `::understanding_malformed_none_no_fallback`） |
| specs/understanding.md:80 | 行为 8 候选须出自名录 | `metric_candidates` 出现名录外名字 → 判**违约**并如实上报（红线）；名录经 `tools` 的 `semantic_query` 取得、不直引引擎（`::full_route_candidates_in_roster`／`::candidate_out_of_roster_violates`） |
| specs/understanding.md:81 | 行为 9 每 run 只装配一次＋模型原话不进对话层（钉 pin-26 渲染面） | 模型原话只进过程档案与留痕、`dialogue` 零写入（`::assembled_once_raw_not_in_dialogue`） |
| specs/understanding.md:84 | 行为 12 理解文本发 `text` 事件 | `kind=understanding`；理解文本与指标候选**双出口**（`state` 字段 ＋ `text` 事件）；发射单元 M1（真源 `synth/S6-事件与帧目录.md` §一）（`::understanding_text_event_emitted`） |
| specs/understanding.md:89 | 不降级与静默禁令——如实上报必带机读信号 | 「如实上报」（候选违约／解析失败／直答退回）必须产生机读信号：step payload 字段 ＋ notice（类型取自事件闭世界 `synth/S6-事件与帧目录.md`）；合法降级路径＝**无**（`::reporting_signal_present`） |

结构锚：specs/understanding.md:42–53 接口定义（`interpret(state: RunState) -> Understanding | Direct`；`Understanding`／`Direct` 两型的 `route` 为定型常量 Literal、**不设类定义默认值**——缺必填字段即抛错）；:55–56 `route` 闭世界与错误契约（合法值仅 `"full"`｜`"direct"`，越界值判失败、不猜不取默认；`UnderstandingParseError` 携原始应答片段；直答退回不抛错——退回面归 RT-W4-01b）；:60–65 框架与依赖红线（无点名框架／经 `bookkeeping.call_model` 单点发起／不直引 `langgraph`／只经 `tools` 公开面）；:86–90 不降级与静默禁令（合法降级路径＝无，模型不可用由 `orchestration` 统一处置；红线原文 `arch/P7a-交接包与挂账清单.md` A-P7a-37「不许静默」）；:116 身份层单一来源声明（系统提示词 `SYSTEM_PROMPT` 全文本属他模块，本块只声明身份层单一来源）。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单——表内明写归本块的行〕

> **（无）**——§三 9 行（B1／B2／B2b／B3／B4／B5／B6／B7b／B7）逐行核对：钉法列带「对应 <块>」者三处（B1「对应 runtimev2 `bookkeeping`」／B2「对应 `orchestration`」／B4「对应 `gate`」），其余六行的钉面亦各有其块（B2b→preconditions、B3→state／bookkeeping、B5→帧流回放、B6→clarify／orchestration、B7b→gateway_adapter、B7→tools 存量面）；**无一行明写 `understanding`**——如实声明、不硬挂（照 RT-W3-01a/b/c「归块注」一节的诚实口径：无明写行即报无，不凑）。

关联行（行内无块名，但本块是其产出面之一）：

> | B5 | 帧协议级时序（step/text/ask/verdict/done/error 序与 data 形） | 从 `eval/results/frames/` 真帧流转离线 golden 回放钉 | 中 |

- 归块注：B5 的钉法是**真帧流转离线 golden 回放**（L3 面，归帧流／回放侧）；本块的贡献面＝**`text` 事件（`kind=understanding`）的发射形**（行为 12）——该事件是帧协议成员之一。本票只保证发射形由本块发出并由 `::understanding_text_event_emitted` 承接，不冒充帧序整体覆盖（帧序钉归 B5 本体）。
- 本块明确**不涉**的 §三 行（防一头两认）：B2／B2b／B4／B6／B7／B7b 各明写归 orchestration／preconditions／gate／clarify 面／tools 存量面／gateway_adapter——本块对它们只作消费方（如消费 `gate` 的入口闸结论），无独立钉。
- 本票织网义务＝① B5 关联面（本块 `text` 事件发射形）；②「测试网钉」1 行（pin-26 渲染面）对应用例落网且绿；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」11 行逐行实现为 `tests/domains/test_v2_understanding.py` 用例并全绿，测试标识与规格列逐字一致（本块为新建测试文件）；
- 跨文件对读件 `tests/domains/test_v2_parsing.py::understanding_malformed_none_no_fallback` 在场且绿（转译输入半面——规格风险 4 检测手段）；
- 「测试网钉」1 行对应用例在场且绿（`::assembled_once_raw_not_in_dialogue` 携 pin-26 渲染面断言；写入面／字段面分载不重复）；
- 边界闸 R1／R2／R5b／R6／R7 在 `lint-imports --config tools/importlinter_v2.toml` 下绿；AST 机检 `::no_lexicon_or_regex_in_understanding` 绿；
- 本票**不含** -B 半面 5 行（规格表内行序 3／4／14／15／16）——该 5 行归 RT-W4-01b，不得在本票冒充覆盖；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W4-01a 完成，产物 `appv2/runtimev2/understanding/`（-A 半面），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
