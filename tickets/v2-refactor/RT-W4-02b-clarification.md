# RT-W4-02b · clarification（-B）——反问卡生产（时机／口径／合并）＋覆盖自证＋边界·保留集

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/clarification.md`（状态「已定稿」——前置满足）
Touches modules: `clarification`（本票在 -A 已落骨架 `appv2/runtimev2/clarification/` 上实现 -B 半面；规格「触及的模块」表另声明 prompts／parsing／bookkeeping／gateway_adapter／state 五关联侧，归各自票承接）
波次: W4 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W4 行三列原文：块列「七个业务相位（understanding → clarification → tool_matching → preconditions → execution → answering → verification）」；理由列「互零依赖，**建议按业务链序施工**（便于走查 narrative 与测试网逐块加厚），不禁止并行」；出口判据列「每相位配属规格十节版式定稿＋新规格钉绿＋触及该相位的特征钉绿」；本块＝链序第 2 位（前位 understanding、后位 tool_matching）
复审强度: 50% 抽查（eng/03 §五 流水 48 规则；W4 行 A 列含 `clarification`——该表降级保留的规则原文「A 列抽 50%」，双队制已废止、A/B 分配只余复审强度语义，波序与块归属不变）
前置: ① 规格定稿（`specs/clarification.md` 已定稿——已满足）；② 波次前置：**W1＋W2＋W3 全收波**（同理 -A）；③ **票内前置：RT-W4-02a 收票**——`clarify(state)` 签名、`ClarifyOutcome` 三返回位（`ClarifyAsk`／`ClarifyFinal`／`ClarifyRejection`）、四动作闭世界对账链路、机读信号面在位后本票才动工（-B 不新建骨架、不新增模型调用链路、不新增返回位）；④ W4 硬前置＝本块触及的特征钉已钉好（eng/03 §四原文：「W4 每相位开工的硬前置＝该相位触及的特征钉已钉好」）；⑤ 业务链序建议：同波 understanding（RT-W4-01a／-01b）先收——**非硬前置**（eng/03 §一 结构事实②「七个业务相位互相零依赖」）
阻塞: **RT-W4-02a 收票**（-A 未收票则 -B 不动工）｜被阻塞: W5 `orchestration`（eng/03 §一依赖图：orchestration → 七个业务相位——本块 7 行与其 -A 15 行共同构成 W4 clarification 的出口判据「新规格钉绿」）

## 任务

按 `specs/clarification.md` 实现 -B 半面——**反问卡生产簇**：时间范围能从问句确定 → **不反问、直接定范围**（「能否确定／是否需反问」的判断在模型侧产出，程序只按结论分派，含引擎缺参反问兜底）；无时间词 → **默认「近 30 天」并注记**；口径有歧义 → **反问、不给默认**；同一轮多处歧义 → **合并成一张卡**一次问清（反对逐条追问）。另含**覆盖校验归模型自证**（拆完后由模型自证「子问题合起来覆盖原题」，**程序只校格式、不拿词表猜覆盖**）与**子问题无依赖**（`Subtask` 不含依赖字段、独立并行）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

**拆分理由（承 -A 票「拆分理由」节，同一条）**：本块规格「验收测试」表 22 行 > 15 行上限（小票制判据：票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇）→ 拆 -A／-B。**-A**＝骨架＋接口＋核心行为簇（四动作闭世界对账／`finalize` 合法性闸与打回带路／挂起·恢复·到顶截断／机读信号／拒文转换）＋**本块全部织网钉**（pin-05／07／15）；**-B**＝剩余行为簇（**反问卡生产**：时机分派形／默认窗／口径歧义／合并一卡＋覆盖校验归模型＋子问题无依赖）＋【边界集】【保留集】两行。本票 7 行 ≤15、必读 5 份 ≤6，聚焦「反问卡生产与覆盖自证」这一行为簇；两票同包顺序施工（-B 前置＝-A 收票），不并行。

先读:（5 份；其余引用面随用随查、不入必读）`specs/clarification.md` 全文（154 行；本票相关面＝行为 2／3／4／5／8（边界半面）／9／10／11、验收表行序 7／8／9／10／15／21／22、风险 2）；`specs/modules.md` `## clarification` 卡（:149–:166，签名以卡为准；测试计划行原文「挂起恢复（等待不计轮／恢复重取易变环境量）；连续澄清上限；失败子集回炉」）；`specs/prompts.md`（澄清轮指令与**台账注入块**——`ledger_notes` 逐字求得的注入面，本票边界集行的判据载体）；`specs/state.md`（`pending_ask`／子问题列与轮预算字段的消费面——本票只消费、不直写）；`specs/bookkeeping.md`（`call_model`／`note`／`set_intent` 单点面——反问卡的模型发起与注记落点）
（另：`specs/tools.md`、引擎侧引用面不属本块——本块零工具直调，`discover` 出口归 -A 票与 `orchestration`。）

框架红线: **无点名框架**（本模块不引入任何框架）；**不得直接 import `langgraph`／`langchain`**（框架只许在 `orchestration`）——对应闸 **R5b 契约**
边界红线: ① **不替模型做语义判断**——程序不判「要不要问」「覆盖有没有漏」，禁词表／正则（AST 机检 `::no_lexicon_or_regex_in_clarification`，豁免面＝形态处理：逐字子串校与集合成员判定）；本票新增代码不得使 -A 票落地的该扫描转红；② 模型调用仍只经 `bookkeeping.call_model`（R7）——本块不直引 `gateway_adapter`／`appv2.infra.llm_client`、不自建客户端；③ **零工具直调**（卡依赖列无 `tools`）——本块不 import 引擎／工具面；④ 反问卡载荷**只许** `ClarifyAsk` 三键（`kind`／`prompt`／`options`）——不新增返回位、不夹带过程材料；⑤ 不落盘（挂起态落库归 `persistence`）、不直改状态字段（写口单点归 `bookkeeping`）；⑥ 相位互不 import（R1）；⑦ `parsing` 不感知本块类型（R3）；⑧ 边界集口径：`ledger_notes` 非逐字（语义改写／摘要）→ **判违约**，不静默放行、不自动修补

## 票面对象（specs/clarification.md「验收测试」表逐行转抄——本票 7 行：规格表行序 7／8／9／10／15／21／22）

〔来源：specs/clarification.md「验收测试」表 :108–:129，逐行原文；`#` 列＝规格表行序（与 -A 票同一行序、不重编），逐字转抄、未改一字；余 15 行（行序 1／2／3／4／5／6／11／12／13／14／16／17／18／19／20）归 RT-W4-02a〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 7 | 时间可确定 → 不反问，直接定范围（断的是模型结论的分派形——「能否确定」判断在模型侧（`walk/裁决表.md` 项目级裁决 #13），程序只验收分派形，不验收判断本身） | `tests/domains/test_v2_clarification.py::no_ask_when_time_resolvable` | specs/clarification.md:114 |
| 8 | 无时间词 → 默认近 30 天并带注记 | `tests/domains/test_v2_clarification.py::default_window_with_note` | specs/clarification.md:115 |
| 9 | 口径歧义 → 反问（不给默认） | `tests/domains/test_v2_clarification.py::caliber_ambiguity_asks` | specs/clarification.md:116 |
| 10 | 同轮多处歧义 → 合并成一张卡 | `tests/domains/test_v2_clarification.py::ask_card_merged` | specs/clarification.md:117 |
| 15 | 覆盖校验由模型自证；程序不判覆盖 | `tests/domains/test_v2_clarification.py::coverage_self_proof_model_only` | specs/clarification.md:122 |
| 21 | 【边界集】`ledger_notes` 语义改写（非逐字）→ 判违约 | `tests/domains/test_v2_clarification.py::boundary_paraphrased_notes_rejected` | specs/clarification.md:128 |
| 22 | 【保留集】非歧义问句不产生 ask；子问题独立并行行为不变 | `tests/domains/test_v2_clarification.py::retention_no_ask_no_dependency` | specs/clarification.md:129 |

> 测试文件归属（据规格逐行原文的标识路径照录）：本块验收测试绑**新建** `tests/domains/test_v2_clarification.py`（与 -A 票同一文件、同一批用例集——本票在 -A 已建文件上追加，不另起文件）；旧码测试本批不改。

## 测试网钉（specs/clarification.md「与闸的挂钩表」pin 行逐行转抄，0 行——本块三行 pin 全随 RT-W4-02a 落地）

〔来源：specs/clarification.md「与闸的挂钩表」:143–:154——表内 pin 行 3 行（pin-05／pin-15／pin-07）已随 `RT-W4-02a-clarification.md`「测试网钉」节转抄并落地；本票**零 pin 行、不重复转抄**（同一 pin 行两处转抄＝两处真源必漂移——照 `RT-W4-05b-execution.md` 同款纪律）〕

- 归块注：本块三行 pin 的断言面（`finalize` 合法性闸／到顶截断与挂起语义／打回三段带路）全部属 -A 行为簇；本票**只产反问卡与覆盖判定**，不产钉。与本票相关的口径自守两则：① 反问卡的轮次计数与到顶截断（行为 15）归 -A——本票不得自行加轮次上限数值或截断逻辑；② 「同轮合并一卡」（行为 11）只改**卡片条数**，不绕 `ClarifyAsk` 三键载荷形状。
- 本块规格挂钩表内其余行（R5b／R7 两闸行、spec gate 两行、四测试行、人审行）非 pin 行——本票「票面对象」行 7／9／15 对应其中 `::no_ask_when_time_resolvable`／`::caliber_ambiguity_asks`／`::coverage_self_proof_model_only` 的印证面。

## 施工要点（specs/clarification.md「行为约定」节骨架＋接口节——file:line 锚＋一句话；本票只覆盖 -B 行为簇）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/clarification.md:79 | 行为 2 时机规则（**属模型侧策略判断，程序只分派模型结论，不入程序验收面**） | 时间范围能从问句确定 → **不许反问**、直接定范围（含引擎缺参反问兜底）；「能否从问句确定／是否需反问」的判断在模型侧产出，程序只按结论分派（真源 `walk/08` §一；`walk/裁决表.md` 项目级裁决 #13）（`::no_ask_when_time_resolvable`） |
| specs/clarification.md:80 | 行为 3 无时间词 → 默认「近 30 天」并注记 | 默认值＋注记同批产出（真源 `walk/08` §七 Q-B）（`::default_window_with_note`） |
| specs/clarification.md:81 | 行为 4 口径不给默认 | 口径有歧义 → **反问**，不交模型猜（真源 `walk/08` §七 Q-B）（`::caliber_ambiguity_asks`） |
| specs/clarification.md:82 | 行为 5 先探后问为首选策略（属模型侧策略，不入程序验收面） | 模型先 `discover` 出候选、再带候选反问（真源 `walk/08` §七 Q-C）；**程序侧只做闭世界 schema 对账，不验收该策略** |
| specs/clarification.md:86 | 行为 9 覆盖校验交模型 | 拆完后由**模型**自证「子问题合起来覆盖原题」；**程序只校格式，不拿词表猜覆盖**（`::coverage_self_proof_model_only`；AST 机检 `::no_lexicon_or_regex_in_clarification` 随 -A 票落地） |
| specs/clarification.md:87 | 行为 10 子问题无依赖 | `Subtask` 不含依赖字段，子问题**独立并行**（子问题间依赖声明与顺序执行＝**不做**）（`::retention_no_ask_no_dependency`） |
| specs/clarification.md:88 | 行为 11 反问卡合并 | 同一轮里多处歧义 → **合并成一张卡**一次问清（反对逐条追问）（`::ask_card_merged`） |
| specs/clarification.md:85 | 行为 8 注释逐字抄台账（**边界半面**；对账主体在 -A） | 本票落非逐字形：`ledger_notes` 语义改写／摘要 → **判违约**（判据＝在台账注入块内**逐字求得**；形态处理豁免面内）（`::boundary_paraphrased_notes_rejected`） |

结构锚：specs/clarification.md:41–:60 接口定义（`ClarifyAsk`＝`kind: Literal["clarify"]`／`prompt`／`options` 三键；`Subtask`＝`id`／`question`／`ledger_notes`／`chain`（闭世界 `"data"`｜`"knowledge"`）——`Subtask` **不含依赖字段**）；:62–:68 闭世界与契约六条（四动作闭世界含 `ask`／`decompose` 两出口形；错误契约＝不合 schema 返 `ClarifyRejection` 回喂）；:70–:74 框架与依赖红线；:133 依赖行（`prompts`／`parsing`／`bookkeeping`／`gateway_adapter`／`state`；外部＝无）；:136 风险 2（覆盖校验滑成程序判 → 判据只留模型侧＋AST 机检，**豁免面＝形态处理**：逐字子串校与集合成员判定不算语义词表／正则）；:137 风险 3（恢复重取漏项——本票不涉，归 -A 行为 13）。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单——表内明写归本块的行〕

> **（无）**——§三表内唯一点名本块的行＝B6（挂起恢复多场景，盲区列「clarify 二级／越集审批／跨实例」），其断言面（挂起契约／恢复语义）属 **-A 票面**；本票不产帧、不涉挂起恢复、不落 §三 钉。

- 同一节的关联行 B3（H8 预算四限额边界）与 B5（帧协议级时序）在本块的落点亦全部在 -A（触顶截断行为面／`ask` 帧产出面）——本票**不新增织网钉**，不动 -A 已落口径。
- 本票织网义务＝L2 新规格钉随本票施工 TDD 生长（eng/04 §五：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。
- 挂账登记（不静默吞掉）：规格「与闸的挂钩表」末行「『不做什么』的纯范围排除（不查数／不选工具等）」现状＝**人审**（接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分已由边界闸 R1（相位互不 import）覆盖）——本票交付时按人审口径自述范围排除，不冒充机检覆盖；另规格「不做什么」两行明写**不做**项（子问题依赖声明与顺序执行、挂起超时）＝本票两张保留集/边界集行的对照面，不得实现为额外功能。

验收: 以下判据逐条全绿为过——
- 「票面对象」7 行逐行实现为 `tests/domains/test_v2_clarification.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】【保留集】两行）；
- -A 票 15 行同文件回归绿（本票改动不得使既有用例转红，尤其 `::ask_cap_truncate_with_material`／`::waiting_not_counted_resume_resets`）；
- 反问卡载荷形状自守：只出 `ClarifyAsk` 三键、不新增返回位、不夹带过程材料；合并一卡只改条数（用例断言）
- 程序侧零语义判断：AST 机检 `::no_lexicon_or_regex_in_clarification` 绿；本块零工具直调（源码无 `appv2.tools`／引擎 import）；
- 边界闸 R1／R2／R5b／R7 在 `lint-imports --config tools/importlinter_v2.toml` 下绿；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W4-02b 完成，产物 `appv2/runtimev2/clarification/`（-B 半面），偏差: 有/无（有则逐条列），测试: pytest 摘要（含 -A 15 行回归）＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
