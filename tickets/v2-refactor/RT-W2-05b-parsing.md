# RT-W2-05b · parsing——V2 解析与发射（-B：迁移照抄与器材面／载荷定型类／元面与边界·保留集）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/parsing.md`（状态「已定稿」——前置满足）
Touches modules: `parsing`（本票只填 parsing 剩余行为簇；族名单与公开面以 -05a 落地的为唯一真源；规格「触及的模块」表另声明 `state` 关联侧——唯一模块依赖 R3，只消费、零写入）
波次: W2 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W2 行三列原文：块列「`parsing` `prompts` `transport` `persistence` `gateway_adapter`」；理由列「纯件层，只依赖 state/infra；其中 **gateway_adapter 的测试替身（fake）是后续所有相位测试的地基**，必须最先可用」；出口判据列「解析异常分支不静默；帧/游标单调；只追加可重放；模型出口唯一＋**替身可注入**」
复审强度: 50% 抽查（eng/03 §五 W2 行 A 列含 `parsing`——该表降级保留的规则原文「A 列抽 50%」；双队制已废止，A/B 分配只余复审强度语义，波序与块归属不变）
前置: ① 规格定稿（`specs/parsing.md` 已定稿——已满足）；② **`RT-W2-05a-parsing.md` 收票**（同包顺序施工、同包不并行——三面解析器族签名、族名单与载荷定型类形状以 -05a 为唯一真源）；③ 波次前置：**W1 state 收波**（eng/03 §一依赖图：parsing → state，经 -05a 传递，已满足）
阻塞: `RT-W2-05a-parsing.md`（-05b 前置＝-05a 收票）｜被阻塞: W3 `context`／`gate`（eng/03 §二 W3 行：组合件，依赖 W2 的 gateway_adapter——本票为 W2 五票之一，W2 全收即其开工条件）＋W4 三消费相位（`understanding`／`clarification`／`tool_matching`）

## 任务

接 `RT-W2-05a-parsing.md` 落地的骨架与族名单，填 `appv2/runtimev2/parsing/` 的**剩余行为簇**：拒因正文与带定位件的逐字迁移、提取单点、引号自修与受理编排、载荷定型类字段表与投影、指纹器材四件、共用件单点、数字单点（注入制）、三条元面（无词表正则／纯函数确定性／import 白名单）与边界集／保留集两行。

**本票＝parsing 的 -B 票**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **28 行**，超 15 行上限 → 切 -A／-B 两票；本票收**剩余 15 行**＝规格表第 14–28 行（拒因逐字迁移／带定位／提取单点／引号自修／载荷定型类两行／指纹器材两行／共用件单点／数字单点／元面三行／【边界集】／【保留集】）；前 13 行与**本块 pin 相关两行**（`pin-06` 器材半面分工注＋`pin-04`／`pin-13` 不落本块核实）全在 -05a，本票零 pin 行、不重复转抄（同一 pin 行两处转抄＝两处真源必漂移）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/parsing.md` 全文（十节版式——行为 7／8／10 的迁移字面与受理编排、行为 11 字段表、行为 13 指纹器材三形、行为 16 数字单点的逐字稿都在规格行内）；`specs/modules.md` `## parsing` 卡（卡面两函数与族名单权威注——签名以卡为准）；`appv2/runtime/subtask.py`（**拒因逐字稿载体**：L82-L110 带定位拼装／L116-L176 与 L296-L315 字段表与 `as_payload` 投影／L179-L290 澄清面／L318-L375 匹配面；L48-L54 四动作／L58 预算前缀）；`appv2/runtime/graph.py`（**引号自修与受理编排的迁移形**：L392-L408「单函数三调用不复制三份」；L616 `args` 拒文字面）；`docs/runtime-refactor/recon/L1a-子任务前半.md`（R-L1a-01…R-L1a-15——提取单点／带定位／字段表条目真源）；`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`（A-P4b-10／A-P4b-11 带定位真源；A-P4b-38／A-P4b-39 引号自修与受理编排真源）。eng/04 §三 关联行与 eng/04a 的 `pin-06` 面已在 `RT-W2-05a-parsing.md`「织网义务」「测试网钉」两节逐字转抄，本票不重复、只写指针。

**小票制自检（流水 48）**：票面对象 15 行 ≤ 15 ✓；先读 6 份 ≤ 6 ✓；聚焦一个行为簇＝「迁移照抄与器材面」（共用件族＋载荷定型类＋指纹器材）＋元面与边界两行 ✓ → 本票不派生。

框架红线: 无点名框架（纯解析零框架依赖；只用标准库 `json`／`dataclasses`）——对应闸 R5b 契约（`tools/importlinter_v2.toml` :101）
边界红线: ① **只许 import `state`**（纯解析块）——R3 契约（`:81`）＋AST 断言 `::imports_state_only`（公共层半面无闸的降维补位，人审余面）；② 消费方向（R2）＝只许经包根 `appv2.runtimev2.parsing`（`:74`）；③ 不引引擎（R6）、不直引 `appv2.infra.llm_client`（R7）、不引旧码（R5）；④ **零模型调用**（连 `gateway_adapter` 都不 import）——`::parsing_pure_deterministic`；⑤ **零 IO／零时钟／零随机／零事件发射／零状态写入**（唯一 `state` 接触＝限额常量与指纹簿记字段的形状）；⑥ **程序侧零词表／零正则语义判定**（AST；豁免面＝形态处理——闭世界成员判定／字符串归一／字符扫描，`::no_lexicon_or_regex_in_parsing`）；⑦ **禁手写替代（解析单点）**：提取件／拒因带定位件／引号自修件／受理编排件在 runtimev2 面内各恰一处定义（`::shared_helpers_single_source`——相位块零字面副本）；⑧ **禁手写替代（本票面）**：不得改 -05a 已定的族名单与载荷定型类形状另立第二套

## 票面对象（specs/parsing.md「验收测试」表逐行转抄——本票 15 行：规格表第 14–28 行）

〔来源：specs/parsing.md「验收测试」表 :131–:158（本票取自 :144–:158），逐行原文；`#` 列＝规格表行序（与 -05a 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 14 | 拒因原文逐字迁移（golden＝迁移前 `appv2/runtime/subtask.py` 快照逐字比对；预算前缀「发现预算」在场） | `tests/domains/test_v2_parsing.py::rejection_texts_verbatim_from_v1` | specs/parsing.md:144 |
| 15 | 拒因带定位：坏点字符序＋前后窗在场；无花括号专门提示；括号失衡形退裸 fallback | `tests/domains/test_v2_parsing.py::rejection_feedback_locus` | specs/parsing.md:145 |
| 16 | 提取单点：首平衡块／首块坏不续扫／顶层非对象 → `None` | `tests/domains/test_v2_parsing.py::extract_first_balanced_block` | specs/parsing.md:146 |
| 17 | 引号自修四形（转义不误伤／值内引号受理／无病不修／修后仍失败）＋修后全文可解析 | `tests/domains/test_v2_parsing.py::quote_repair_four_forms` | specs/parsing.md:147 |
| 18 | 载荷定型类：字段集与投影键形（`as_payload`）逐字；空值键不出现；`ask` 段开闸单点 | `tests/domains/test_v2_parsing.py::payload_types_field_tables` | specs/parsing.md:148 |
| 19 | 载荷类五类形状与行为 11（及 `understanding` 所列集合）相等；本块无第二处形状定义（AST／集合比较） | `tests/domains/test_v2_parsing.py::understanding_payload_shape_single_source` | specs/parsing.md:149 |
| 20 | 指纹器材：两跑同串（确定性）；按支拆算单支单形／两支两值 | `tests/domains/test_v2_parsing.py::fingerprints_deterministic_per_branch` | specs/parsing.md:150 |
| 21 | 同参判定三支（全在→拦／新参→放行／零支→放行） | `tests/domains/test_v2_parsing.py::same_param_replay_three_cases` | specs/parsing.md:151 |
| 22 | 共用件（含受理编排）单点：特征子串在 `understanding`／`clarification`／`tool_matching` 块源码零命中（零副本） | `tests/domains/test_v2_parsing.py::shared_helpers_single_source` | specs/parsing.md:152 |
| 23 | 数字单点：签名无裸默认值（注入制）；注入参数取值来源逐参可指 `state` 键或登记项；裸字面扫描（豁免面＝迁移拒文与 `ask` 边界字面） | `tests/domains/test_v2_parsing.py::limits_from_state_constants` | specs/parsing.md:153 |
| 24 | 程序侧无词表／正则语义判断（AST；豁免面＝形态处理） | `tests/domains/test_v2_parsing.py::no_lexicon_or_regex_in_parsing` | specs/parsing.md:154 |
| 25 | 确定性纯函数：两跑逐字相等；零 IO／模型／时钟／随机／事件／状态写（AST） | `tests/domains/test_v2_parsing.py::parsing_pure_deterministic` | specs/parsing.md:155 |
| 26 | import 面只许 `state`（AST 扫描——R3 半覆盖面的降维补位） | `tests/domains/test_v2_parsing.py::imports_state_only` | specs/parsing.md:156 |
| 27 | 【边界集】缺字段／超限／引号异常／重复 `id`／括号失衡截断 → 各落拒因正文或 `None` | `tests/domains/test_v2_parsing.py::boundary_missing_overlimit_quote_duplicate` | specs/parsing.md:157 |
| 28 | 【保留集】常规三面文本解析不受边界分支影响；消费方既有 schema 断言不因迁移改形回归 | `tests/domains/test_v2_parsing.py::retention_normal_parses_unchanged` | specs/parsing.md:158 |

> 测试文件归属（票注，非规格引文）：本票 15 行与 -05a 的 13 行同落**同一个新建文件** `tests/domains/test_v2_parsing.py`（spec :160 节尾原注已在 `RT-W2-05a-parsing.md` 同节照抄，本票不重复转抄，防两处漂移）；旧码测试本批不改。
> 行序缺口说明（票注）：本票行序跳过 1–13——`#` 列两票共用规格表行序，便于 manifest 逐行对账。
> 规格侧缺口登记（票注，呈主窗对账）：规格「行为约定」行为 17 的 **JSON 重复键形**（同键出现多次、解析后取后者）＝真源未裁落点（风险 7⑥），「本块不自行加严」——本票行 27 的「缺字段／超限／引号异常／重复 `id`／括号失衡截断」按规格原文处理、**不自行增设验收行**（增设＝改规格，回设计仓），此处只登记事实。

## 测试网钉（本块 pin 相关两行已在 `RT-W2-05a-parsing.md` 同节全量逐字转抄——本票零 pin 行，不重复转抄）

- 核对关系（防两处漂移）：`pin-06`（空手探查记指纹）**器材面** ↔ 本票行 20／21（指纹四件）；其**行为面** ↔ `specs/execution.md` 行为 13（`RT-W4-05a-execution.md` 行 15，pin 行逐字转抄在该票）；`pin-04`／`pin-13` ↔ 零落点（核实结论在 -05a 同节第二行）。
- 分工注（防两头认）：本票产出的指纹四件＝**纯函数器材**（`payload_fingerprint`／`discover_fingerprint`／`emission_fingerprints`／`is_same_param_replay`）；触发、拦截与回喂归 `execution`（规格风险 4；`docs/runtime-refactor/00-决议与方法.md` :102 流水 30②）——本块零触发面。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 pin 相关行只落 -05a 一处（先例 `RT-W4-05b-execution.md` 分票理由原文）。

## 施工要点（specs/parsing.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/parsing.md:106 | 行为 7 拒因正文＝机器拒因原文（迁移照抄，零改动） | 全部分支拒因文本**逐字迁移、承载位换文本不变**；逐字稿载体＝迁移前现行代码 `appv2/runtime/subtask.py`（L82-L110 带定位／L179-L290 澄清面／L318-L375 匹配面）；机读甄别面恰一值＝前缀「发现预算」（L58） |
| specs/parsing.md:107 | 行为 8 拒因带定位（V2-57） | 提取失败 → 带定位件拼装：无左花括号形含逐字提示（L88-L89）；语法坏点形含异常消息＋绝对坏点字符序＋坏点前后窗原文＋逐字修复指令（L104-L108 全段照抄）；**括号始终不平衡形退裸 fallback（零定位）**——V1 事实面，本块不自行裁量 |
| specs/parsing.md:108 | 行为 9 提取单点＝首个花括号平衡块 | 只读首块、首块坏即 `None`（不续扫后续块）；深度归零处切片交 JSON 解析；成功且顶层为对象 → 返回该对象；无左花括号／未平衡／顶层非对象 → `None`；两发射面共用同一件（单点） |
| specs/parsing.md:109 | 行为 10 引号自修＝确定性纯字符处理（V2-60 ③层） | 逐字符串态扫描；串内裸引号替换为「／」（按出现次序开闭交替）、结构引号原样；无病不修 → `None`；修后全文可解析 → 修复文本，仍失败 → `None`；**受理编排（解析拒→自修一次→重解析→首拒因保留＋受理标志）＝本块末件单点**，受理 notice 由调用方发（本块零事件）；**理解面不受理自修** |
| specs/parsing.md:110 | 行为 11 载荷定型类＝V1 字段表逐字迁移 | `Subtask{id, question, ledger_notes, chain=""}`（**`tool` 退场**）／`QuestionGroup{subtasks: 元组}`／`SubtaskMatch{id, chain, tool, plan=None, retrieval_need=None, caliber_key=""}`＋`ClarifyEmission`；全 `frozen=True, slots=True`；投影规则（`as_payload`）逐字：空值键不出现、`ask` 段以 `ask_prompt` 真假单点开闸 |
| specs/parsing.md:111 | 行为 12 载荷类形状单点（消费面不重定义） | 五类（`Understanding`／`Direct`／`Subtask`／`QuestionGroup`／`SubtaskMatch`）字段形状**物理定义点＝本块**；`Understanding`／`Direct` 以 `specs/understanding.md` 接口定义为准，其余三类以行为 11 为准；两份消费方规格的类体差异＝登记待阶段 7 对账（风险 7③） |
| specs/parsing.md:112 | 行为 13 指纹器材（同参重投闸指纹面） | 载荷规范指纹＝键序归一＋紧凑分隔符＋不转义非 ASCII 的 JSON 串；发现调用指纹＝`{"tool": 名, "args": 参}` 键序归一（两规范各自保留、不跨面比较）；按支拆算＝单支单形（`plan` 支在前；两皆空 → 空元组）；同参判定＝空元组放行／全支在实录拦／任一支新参放行；**触发点与拦截／回喂归消费方** |
| specs/parsing.md:113 | 行为 14 纯结构判定 | 全部判定＝存在性／类型／闭世界成员／计数／字符串归一／字符扫描——**零词表零正则语义判定**；豁免面＝形态处理（本块实际形态：闭世界成员判定／字符串归一／字符扫描） |
| specs/parsing.md:114 | 行为 15 确定性纯函数 | 同入参两次调用输出逐字相等；零 IO／零模型调用／零时钟／零随机／零事件发射／零状态写入 |
| specs/parsing.md:115 | 行为 16 数字与上限单点（注入制） | 三个限额参数由调用方注入、签名无缺省值；`max_discovers`／`discover_budget_left` 取值来源＝`state` 限额键；`max_subtasks` 数值真源＝`walk/09` §七 Q-C＋`eng/00` F-14、`state` 承载键未落定（风险 7⑤）；本块源码无裸上限字面（豁免面＝迁移拒文与行为 5 边界字面） |
| specs/parsing.md:116 | 行为 17 同类条目多次出现不静默覆盖 | 重复 `id`（问题组支／匹配支）逐条拒（拒因原文逐字，载体 L199／L339）；**JSON 重复键形＝真源未裁落点**（风险 7⑥）——本块不自行加严，样本行为＝如实记录 |
| specs/parsing.md:117 | 行为 18 共用件单点、消费方零副本 | 两发射面共用的提取件／拒因带定位件／引号自修件＋受理编排件在 runtimev2 面内各恰一处定义；相位块内出现同形字面副本（提取循环／引号扫描）＝判失败 |

结构锚：specs/parsing.md:39–:80 接口定义（**V2 定案签名**与共用件族逐字稿——本票所填各件的实名与参形以该节为准）；:82–:86 返回三态闭世界／错误契约（**不抛业务异常、不吞错**——不合格一律走三态返回）／入参纪律（纯文本进出＋调用方注入的限额参数、本块源码不写裸值）；:88 V2 定案差异点表（② 不裸抛业务异常＝本块两处收口／③ 注入制／⑦ 指纹公开化）；:119–:125 不降级与静默禁令（**合法降级路径＝无**——不半成品、不静默丢 schema 内字段、不改写模型原文；机读信号两处＝拒因恒非空＋预算前缀；本块零截断，坏点前后窗＝设计内明文摘录）。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三——关联行指针，不重复转抄）

- §三 表内**无一行明写本块**（该表明写块名者只有 B1→`bookkeeping`／B2→`orchestration`／B2b→`preconditions`／B4→`gate`）；本票的 B6 关联行逐字转抄与归块注在 **`RT-W2-05a-parsing.md`** 同节，B3 相邻面（「限额上限」半面的解析侧判定；其逐字转抄落 `RT-W1-01b-state.md`）另在 -05a 同节留指针（防两处真源漂移）——本票不重复转抄、不冒充覆盖。
- 本票织网义务＝① 本票 15 行对应用例落网（其中行 20／21 同时是 `pin-06` **器材面**的落网用例）；② L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」15 行逐行实现为 `tests/domains/test_v2_parsing.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行；`#` 保留规格表行序 14–28）；
- 「测试网钉」零 pin 行——本票只写归属指针，不重复转抄（pin 相关两行全在 -05a）；`pin-06` **器材面**用例（行 20／21）在场且绿；
- 迁移字面逐字绿：拒因正文（行 14，golden＝迁移前 `appv2/runtime/subtask.py` 快照）与带定位三形（行 15）逐字相符，差异点表外零偏离；预算前缀「发现预算」在场；
- 载荷定型类字段集与投影键形逐字（行 18／19）、本块无第二处形状定义；指纹器材确定性两跑同串、同参判定三支落对（行 20／21）；
- 三条元面 AST 断言绿：`::no_lexicon_or_regex_in_parsing`（豁免面＝形态处理）／`::parsing_pure_deterministic`（零 IO／模型／时钟／随机／事件／写）／`::imports_state_only`；共用件单点绿（`::shared_helpers_single_source`——相位块零副本）；
- 数字单点绿（行 23）：签名无裸默认值；豁免面＝迁移拒文与 `ask` 边界字面（风险 7② 裁定后随批收窄）；
- 形状单点：三面解析器族签名与族名单仍以 -05a 落地的为唯一真源，本票不改形状（改形状＝回 -05a 或回设计仓）；
- 边界闸 R2／R3／R5／R5b／R6／R7 在 `lint-imports` 双配置下绿；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W2-05b 完成，产物 `appv2/runtimev2/parsing/`（迁移照抄与器材面／载荷定型类／元面与边界·保留集），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
