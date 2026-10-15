# RT-W4-02a · clarification（-A）——四动作发射对账＋收口/挂起/拒因回路

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/clarification.md`（状态「已定稿」——前置满足）
Touches modules: `clarification`（本票在既有占位骨架 `appv2/runtimev2/clarification/` 上实现 -A 半面；规格「触及的模块」表另声明 prompts／parsing／bookkeeping／gateway_adapter／state 五关联侧，归各自票承接）
波次: W4 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W4 行三列原文：块列「七个业务相位（understanding → clarification → tool_matching → preconditions → execution → answering → verification）」；理由列「互零依赖，**建议按业务链序施工**（便于走查 narrative 与测试网逐块加厚），不禁止并行」；出口判据列「每相位配属规格十节版式定稿＋新规格钉绿＋触及该相位的特征钉绿」；本块＝链序第 2 位（前位 understanding、后位 tool_matching）
复审强度: 50% 抽查（eng/03 §五 流水 48 规则；W4 行 A 列含 `clarification`——该表降级保留的规则原文「A 列抽 50%」，双队制已废止、A/B 分配只余复审强度语义，波序与块归属不变）
前置: ① 规格定稿（`specs/clarification.md` 已定稿——已满足）；② 波次前置：**W1＋W2＋W3 全收波**（eng/03 §一依赖图：clarification → prompts ＋ parsing ＋ gateway_adapter ＋ state；模型调用发起面 `bookkeeping.call_model` 归 W3）；③ W4 硬前置＝本块触及的特征钉已钉好（eng/03 §四原文：「W4 每相位开工的硬前置＝该相位触及的特征钉已钉好」）；④ 业务链序建议：同波 understanding（RT-W4-01a／-01b）先收——**非硬前置**（eng/03 §一 结构事实②「七个业务相位互相零依赖」）；⑤ 票内前置：无（-A 为本块首票；占位骨架 `appv2/runtimev2/clarification/__init__.py` 已随阶段 2 落锤）
阻塞: 无（-A 可开工，硬条件＝W1／W2／W3 全收波）｜被阻塞: RT-W4-02b（-B 前置＝「-A 收票」——三返回位与对账链路在位后 -B 才动工；同包不并行）＋W5 `orchestration`（eng/03 §一依赖图：orchestration → 七个业务相位）

## 任务

按 `specs/clarification.md` 实现 -A 半面：**四动作结构化发射的闭世界对账**（动作／条数／注释／路线）→ **单出口互斥三返回位**（`ClarifyAsk`｜`ClarifyFinal`｜`ClarifyRejection`；`discover` 不占返回位——以 `next_intent="discover"` 交出、由 `orchestration` 路由出去执行）→ **拒因回路**（schema 违例与 `finalize` 前置不合规一律返回结构化 `ClarifyRejection`、由 `orchestration` 回喂重决策、不做自动修补）→ **`finalize` 合法性闸**（零实质观察禁定稿）→ **打回三段带路** → **挂起/恢复语义与到顶截断** → **机读信号面**；含解析拒文（parsing `str`）→ `ClarifyRejection` 的消费方机械转换。**本块零工具直调、零落盘、零语义判断**。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

**拆分理由（小票制，流水 48／eng/03 §五 双队制废止后的小票制）**：本块规格「验收测试」表共 **22 行 > 15 行上限**（Owner 定判据：票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇）→ **拆 -A／-B 两票**：
- **-A＝骨架＋接口＋核心行为簇**（四动作闭世界对账／注释必填非空＋逐字求得／限额双指／`finalize` 合法性闸与打回带路／挂起·恢复·到顶截断／锁 `discover` 机械半句／AST 红线／机读信号／拒文转换）＋**本块全部织网钉**（pin-05／pin-07／pin-15 三行的断言面全部落在本票——收口与拒因回路是本块钉最密的一簇）；票面对象 15 行（**正好触上限，不再加行**）。
- **-B＝剩余行为簇**（反问卡生产：时间窗可确定不反问／无时间词默认近 30 天／口径歧义反问／同轮合并一卡）＋覆盖校验归模型＋子问题无依赖＋【边界集】【保留集】两行；票面对象 7 行。
- 两票**同包顺序施工**（-B 前置＝-A 收票），不并行；-A 不收票则 -B 不动工。

先读:（6 份；其余引用面随用随查、不入必读）`specs/clarification.md` 全文（154 行，十节版式；本票相关面＝接口定义＋闭世界/契约六条、行为 1／6／7／8／12–19、不降级与静默禁令、验收表行序 1／2／3／4／5／6／11／12／13／14／16／17／18／19／20）；`specs/modules.md` `## clarification` 卡（:149–:166，签名以卡为准；含 Seam＝反问卡载荷（挂起／恢复）／Adapter＝剧本化 completer）；`specs/state.md`（`pending_ask`／子问题列形状与限额常量单点面——限额数值不许复制进本块）；`specs/parsing.md`（发射解析与**拒文产出**面——本块是其消费方，转换在本块）；`specs/bookkeeping.md`（`call_model`／`note`／`set_intent` 单点面——本块唯一模型入口与信道交出点）；`specs/prompts.md`（澄清轮指令与台账注入块——`ledger_notes` 逐字求得的注入面）

框架红线: **无点名框架**（本模块不引入任何框架）；**不得直接 import `langgraph`／`langchain`**（框架只许在 `orchestration`）——对应闸 **R5b 契约**
边界红线: ① **模型调用发起面＝`bookkeeping.call_model`（单点发起，禁手写替代），其内部唯一出口＝`gateway_adapter`**——本块不直引 `gateway_adapter`／`appv2.infra.llm_client`、不自建模型客户端、不得绕过发起面直连上游（import 落点＝`appv2.runtimev2.bookkeeping` **包根**——R2 禁深层子模块）——R7 契约＋「无旁路」行为断言；② **本块零工具直调**：`discover` 以 `next_intent="discover"` 交出、由 `orchestration` 路由到发现步执行（卡依赖列无 `tools`——本块不 import 任何引擎／工具面）；③ **零语义判断**：程序只做闭世界 schema 对账与结构判定（动作／条数／注释逐字子串／`chain` 成员／观察计数），禁词表／正则猜「要不要问」「覆盖有没有漏」——AST 机检 `::no_lexicon_or_regex_in_clarification`（豁免面＝形态处理：逐字子串校与集合成员判定不算语义词表／正则）；④ 不落盘（挂起态落库与恢复重放归 `persistence`；本块只返 `ClarifyAsk`）；⑤ 不直改状态字段（写口单点归 `bookkeeping`）；⑥ 相位互不 import（R1）；⑦ `parsing` 不感知本块类型（R3）——拒文转换在本块

## 票面对象（specs/clarification.md「验收测试」表逐行转抄——本票 15 行：规格表行序 1／2／3／4／5／6／11／12／13／14／16／17／18／19／20）

〔来源：specs/clarification.md「验收测试」表 :108–:129，逐行原文；`#` 列＝规格表行序（与 -B 票同一行序、不重编），逐字转抄、未改一字；余 7 行（行序 7／8／9／10／15／21／22）归 RT-W4-02b〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | 动作越界 → 判失败（不猜、不取默认） | `tests/domains/test_v2_clarification.py::emission_action_closed_world` | specs/clarification.md:108 |
| 2 | `ledger_notes` 为空 → 判失败并带拒因回喂（不自动修补） | `tests/domains/test_v2_clarification.py::ledger_notes_required_with_reject_feedback` | specs/clarification.md:109 |
| 3 | 子问题条数越界 → 判失败（上限取限额真源双指：`recon/K-上下文事件指南预算.md` R-K-72…R-K-78 ＋ `walk/裁决表.md` §06-A；条数键两源未单列，数值真源 `walk/09-澄清-分解问题.md` §七 Q-C） | `tests/domains/test_v2_clarification.py::subtask_cap_from_budget_table` | specs/clarification.md:110 |
| 4 | `chain` 越界值 → 判失败 | `tests/domains/test_v2_clarification.py::chain_enum_closed_world` | specs/clarification.md:111 |
| 5 | 零实质观察（非 notice）→ 不得判「材料足够」直答收口：`finalize` 前置＝窗内非 notice 观察数 ≥1，否则拒因「零实质观察禁定稿」回喂 | `tests/domains/test_v2_clarification.py::finalize_requires_substantive_observation` | specs/clarification.md:112 |
| 6 | `finalize` 被拒（打回）→ 拒因载荷带三段带路（前置判定指路→空手清单→兜底 discover/doc_retrieve 指引；零模型调用、段缺则跳、「；」连接） | `tests/domains/test_v2_clarification.py::finalize_rejection_three_segment_guidance` | specs/clarification.md:113 |
| 11 | 台账注入块存在且注释可逐字求得 | `tests/domains/test_v2_clarification.py::ledger_notes_verbatim_from_injection` | specs/clarification.md:118 |
| 12 | 挂起等待不计轮；`resume` 重置轮预算 | `tests/domains/test_v2_clarification.py::waiting_not_counted_resume_resets` | specs/clarification.md:119 |
| 13 | 恢复时重取易变量（水位／新鲜度／地基） | `tests/domains/test_v2_clarification.py::resume_reloads_volatile` | specs/clarification.md:120 |
| 14 | 到上限 → 截断＋带材料如实直答（不环） | `tests/domains/test_v2_clarification.py::ask_cap_truncate_with_material` | specs/clarification.md:121 |
| 16 | 程序侧无词表／正则语义判断（AST 扫描本模块；**豁免面＝形态处理**——逐字子串校与集合成员判定不算语义词表／正则） | `tests/domains/test_v2_clarification.py::no_lexicon_or_regex_in_clarification` | specs/clarification.md:123 |
| 17 | 拒因／截断／挂起的机读信号在场（ask 帧／`pending_ask`／step payload 拒因字段／notice） | `tests/domains/test_v2_clarification.py::clarify_signal_present` | specs/clarification.md:124 |
| 18 | `discover` 经 `orchestration` 路由出去执行（本块零工具直调、不返回） | `tests/domains/test_v2_clarification.py::discover_routed_not_direct_call` | specs/clarification.md:125 |
| 19 | 台账命中且时间窗已定 → 禁再 `discover`（机械半句，断的是模型结论的分派形——「时间窗已定」判断在模型侧（`walk/裁决表.md` 项目级裁决 #13）；「两白场」属模型侧策略，程序不验收） | `tests/domains/test_v2_clarification.py::no_rediscover_when_window_set` | specs/clarification.md:126 |
| 20 | 解析拒文（parsing `str`）→ `ClarifyRejection` 结构化转换归本块（消费方）：机械适配（str 逐字进 `reason` 字段＋映射拒因枚举）、零语义判断（行为 19） | `tests/domains/test_v2_clarification.py::parse_rejection_str_to_clarify_rejection_consumer_side` | specs/clarification.md:127 |

> 测试文件归属（据规格逐行原文的标识路径照录）：本块验收测试绑**新建** `tests/domains/test_v2_clarification.py`（仓内现不存在此文件——本块为阶段 2 新划的相位块 `appv2/runtimev2/clarification/`，与旧 `appv2/runtime/` 旧码测试形状不同）；旧码测试本批不改。

## 测试网钉（specs/clarification.md「与闸的挂钩表」pin 行逐行转抄，3 行）

〔来源：specs/clarification.md「与闸的挂钩表」:143–:154，pin 行 3 行（:151–:153）逐行原文〕

1. **`finalize` 合法性闸：零实质观察（非 notice）不得判「材料足够」直答收口（窗内非 notice 观察数 ≥1 才许定案——纯结构判定）**｜钉 **`pin-05`**（P0）＋ 测试 `::finalize_requires_substantive_observation`｜现状：待织网（阶段 5）
2. **连续澄清反问到顶 → 截断＋带已取得材料如实直答；挂起不计轮、恢复重置轮预算（上限值引 `recon/K-上下文事件指南预算.md` R-K-76——连续 ask 截断上限）**｜钉 **`pin-15`**（P1；上限值真源＝`walk/裁决表.md` §06-A——连续澄清≤6）｜现状：待织网（阶段 5）
3. **定稿打回理由三段带路（前置判定指路→空手清单→兜底 `doc_retrieve` 指引）**｜钉 **`pin-07`**（P1；落点＝行为 18，测试 `::finalize_rejection_three_segment_guidance`）｜现状：待织网（阶段 5）

> 〔附：钉本体原文行，eng/04a-应钉行为清单.md 逐字照抄——:14／:16／:24〕
> | 5 | 零实质观察（非 notice）时 decision 不得判「材料足够」直答收口 | `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md:23-24` | 单元 | P0 |
> | 7 | 定稿打回理由必须三段带路（前置判定指路→空手清单→兜底 doc_retrieve 指引） | `P4b-票堆V2-56至65.md:25` | 单元 | P1 |
> | 15 | 连续澄清反问上限＝**6**（合同值），到顶收敛截断必带已取得材料；挂起不计轮、恢复重置 | synth/S3:19（C-04）；`appv2/runtime/budget.py:38`；`walk/裁决表.md:92`（§06-A）；commit d1300ea（~~c46de21 的 3~~已作废） | 单元 | P1 |
> - 三钉的钉形式＝**单元**（ScriptedCompleter／桩数据单测）；行 2 的「上限值」是**数值真源引用面**（本块不复制字面值——限额常量单点面在 `state`，见 `::subtask_cap_from_budget_table`）。
> - 本块规格挂钩表内其余行（R5b／R7 两闸行、spec gate 两行、`::no_lexicon_or_regex_in_clarification`／`::subtask_cap_from_budget_table`／`::ask_cap_truncate_with_material`／`::waiting_not_counted_resume_resets` 四测试行、人审行）非 pin 行、不属本节点转抄范围——测试行现状「待实现（阶段 5）」由本票「票面对象」行 3／12／14／16 与本票验收面承接。

## 施工要点（specs/clarification.md「行为约定」节骨架＋接口／不降级节——file:line 锚＋一句话；本票只覆盖 -A 行为簇）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/clarification.md:78 | 行为 1 四动作由模型出结构化发射 | 程序只做**闭世界 schema 对账**（动作／条数／注释／路线）；四动作闭世界＝`discover`｜`decompose`｜`ask`｜`finalize`，越界值判失败（不猜、不取默认）（`::emission_action_closed_world`） |
| specs/clarification.md:83 | 行为 6 台账全量每轮注入 | 词典层小、利于前缀缓存；「词典层变大即转按需检索」＝**阈值待定、暂以全量注入为唯一现行为**；本块消费注入块作 `ledger_notes` 逐字求得面（`::ledger_notes_verbatim_from_injection`） |
| specs/clarification.md:84 | 行为 7 封顶数值一律引限额真源双指 | 子问题条数上限、连续反问次数上限（R-K-76）、发现次数上限（R-K-75）、返工轮次上限（R-K-72；§06-A 回炉一次）——**本规格不写字面值**（真源 `recon/K-上下文事件指南预算.md` R-K-72…R-K-78 ＋ `walk/裁决表.md` §06-A；条数真源 `walk/09-澄清-分解问题.md` §七 Q-C）；数值单点面在 `state`（`::subtask_cap_from_budget_table`） |
| specs/clarification.md:85 | 行为 8 注释逐字抄台账 | `ledger_notes` 必填非空、内容须能在台账注入块里**逐字求得**（不做语义改写、不摘要）（`::ledger_notes_required_with_reject_feedback`） |
| specs/clarification.md:89 | 行为 12 挂起语义 | 等待**不计轮、不计时**；`resume` **重置轮预算**；用户所选**原话进对话链**（去系统前缀）（`::waiting_not_counted_resume_resets`） |
| specs/clarification.md:90 | 行为 13 恢复时重取易变量 | 恢复时对等待期间可能变了的量（数据水位／新鲜度／地基／落库新数据）**重取一遍**（`::resume_reloads_volatile`） |
| specs/clarification.md:91 | 行为 14 挂起不设超时 | 无限等，**记录为已知选择**（不是缺陷、不得自行加超时） |
| specs/clarification.md:92 | 行为 15 到顶不环 | 连续反问到上限 → **截断 ＋ 带已取得材料如实直答**（不继续环）——**不得静默**，须明示未完成项（`::ask_cap_truncate_with_material`；上限值引 R-K-76／§06-A） |
| specs/clarification.md:93 | 行为 16 发射判据（机械半句） | 「**台账命中且时间窗已定 → 禁再 `discover`**」＝程序可验收的机械半句（「时间窗已定」的判断在模型侧，程序只分派模型结论）；「两白场」属模型侧策略、程序不验收、不做语义判断（`::no_rediscover_when_window_set`） |
| specs/clarification.md:94 | 行为 17 `finalize` 合法性闸（钉 pin-05，P0） | 判「材料足够」直答收口的前置＝**窗内非 notice 实质观察数 ≥1**（faq 命中卡／台账条目卡／检索片段；空手探查——未命中 notice／工具失败／零观察——不算数），否则拒因「零实质观察禁定稿」回喂、**不得直答收口**；程序侧只数观察数（纯结构判定、计数在 AST 豁免面内）（`::finalize_requires_substantive_observation`） |
| specs/clarification.md:95 | 行为 18 `finalize` 打回三段带路（钉 pin-07，P1） | 拒因载荷必带三段拼装文本（机器已知事实说全、**零模型调用**）：①有绑定拒／台账外形的前置判定指路②已空手探查清单③兜底句**恒在**；段缺则跳、「；」连接成单段（`::finalize_rejection_three_segment_guidance`） |
| specs/clarification.md:96 | 行为 19 解析拒文→结构化拒因转换归本块 | 解析（parsing 产出 `str` 拒文）→ `ClarifyRejection` 的转换归本块（消费方）：机械适配（`str` 逐字进 `reason` 字段＋映射拒因枚举）、**零语义判断**；`parsing` 不感知本块类型（R3）（`::parse_rejection_str_to_clarify_rejection_consumer_side`） |
| specs/clarification.md:100 | 不降级与静默禁令——机读信号 | 截断、挂起、拒因回喂**都必须产生机读信号**：ask 帧／`pending_ask`／step payload 的拒因字段／notice（类型取自 `synth/S6-事件与帧目录.md`）（`::clarify_signal_present`） |
| specs/clarification.md:101 | 不降级与静默禁令——到顶截断不得静默 | 必须带已取得材料交付并明示未完成项（红线原文 `arch/P7a-交接包与挂账清单.md` A-P7a-37） |

结构锚：specs/clarification.md:41–:60 接口定义（`clarify(state: RunState) -> ClarifyOutcome`；`ClarifyAsk`＝`kind`／`prompt`／`options`，`ClarifyFinal`＝`subtasks`，`ClarifyRejection`＝`reasons`；`Subtask`＝`id`／`question`／`ledger_notes`／`chain`）；:62–:68 闭世界与契约六条（四动作闭世界｜`discover` 出口由 `orchestration` 承接、不占返回位｜`chain` 闭世界｜错误契约＝返回 `ClarifyRejection` 由 `orchestration` 回喂、**不做自动修补**｜`finalize` 合法性闸（前置合规，非 schema 违例）｜挂起契约＝返回 `ClarifyAsk` 即挂起、恢复经 `orchestration` 的 `resume` 入口）；:70–:74 框架与依赖红线（无点名框架／经 `bookkeeping.call_model` 单点发起＋禁手写替代／不直引 `langgraph`）；:98–:102 不降级与静默禁令（合法降级路径＝**无**——本模块不自降级）；:133 依赖行；:134–:137 风险 1／2／3（限额数值不复制；覆盖校验只留模型侧；恢复重取清单）。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单——表内点名本块的行〕

> | B6 | 挂起恢复多场景（clarify 二级／越集审批／跨实例） | 专属钉＋回放钉（跨实例条保持门控） | 中 |

- 归块注：B6 是 §三表内唯一点名 `clarify` 的行（盲区列「clarify 二级／越集审批／跨实例」）——本块落**「clarify 二级」半面**（`ClarifyAsk` 二级反问＝挂起→resume→续推），「越集审批」属审批面、「跨实例」条明写**保持门控**；钉法＝**专属钉＋回放钉**，回放面（真帧流）归帧流／回放侧。本块贡献面＝挂起契约（返回 `ClarifyAsk` 即挂起）＋恢复语义（不计轮／重置轮预算／重取易变量）——对应本票票面对象行 12／13 与行为 12／13（规格表行序与行为号同号，纯属巧合、非同一套编号）。
- 本块**不涉**：跨实例条与越集审批（按 B6 原文保持门控／属他面）——`orchestration`（W5 票）承接闭环面，本块不冒充覆盖。

关联行（行内无块名，但本块是其消费面或产出面之一）：

> | B3 | H8 预算四限额边界（现只钉了 CLARIFY_ASK_CAP=6） | 每限额上限/触顶收敛行为钉（数值只引预算表） | 中 |

> | B5 | 帧协议级时序（step/text/ask/verdict/done/error 序与 data 形） | 从 `eval/results/frames/` 真帧流转离线 golden 回放钉 | 中 |

- B3 归块注：B3 明写的 `CLARIFY_ASK_CAP=6` 是**本块行为 15（到顶截断）的上限面**——数值真源归预算表、常量单点面在 `state`（本块不复制字面值），本块落「触顶截断行为」面（钉 pin-15，票面对象行 10）。上限值真源二指：`recon/K-上下文事件指南预算.md` R-K-76 ＋ `walk/裁决表.md` §06-A（连续澄清≤6）。
- B5 归块注：B5 的钉法是**真帧流转离线 golden 回放**（L3 面）；本块贡献面＝`ask` 帧（`ClarifyAsk` 承载）与挂起后照发 `done` 的时序成员——帧序钉本体归帧流／`transport`／`orchestration` 侧（`pin-29` 帧面挂 `specs/transport.md`），本块只保证 `ClarifyAsk` 发射形与挂起语义正确。
- 本票织网义务＝① B6 归块行「clarify 二级」半面；② B3 触顶截断行为面（数值引真源、不复制）；③ B5 `ask` 帧产出面；④「测试网钉」3 行（pin-05／07／15）对应用例落网且绿；⑤ L2 新规格钉随本票施工 TDD 生长（eng/04 §五：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」15 行逐行实现为 `tests/domains/test_v2_clarification.py` 用例并全绿，测试标识与规格列逐字一致（本块为新建测试文件）；
- 「测试网钉」3 行对应用例在场且绿（pin-05 为 P0 承重钉——`finalize` 合法性闸的拒因回路必须可机检）；
- 限额数值零复制：本块源码不出现 R-K-75／76／72 或 §06-A 的字面值（grep 断言＋`state` 侧常量单点测试对读）；
- 边界闸 R1／R2／R5b／R7 在 `lint-imports --config tools/importlinter_v2.toml` 下绿；AST 机检 `::no_lexicon_or_regex_in_clarification` 绿；本块零工具直调（源码无 `appv2.tools`／引擎 import）；
- 本票**不含** -B 半面 7 行（规格表内行序 7／8／9／10／15／21／22）——该 7 行归 RT-W4-02b，不得在本票冒充覆盖；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W4-02a 完成，产物 `appv2/runtimev2/clarification/`（-A 半面），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
