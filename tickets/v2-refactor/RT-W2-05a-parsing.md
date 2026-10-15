# RT-W2-05a · parsing——V2 解析与发射（-A：骨架＋三面解析器族核心簇＋全部 pin 行）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/parsing.md`（状态「已定稿」——前置满足）
Touches modules: `parsing`（本票只建 parsing 本体与三面解析器族；规格「触及的模块」表另声明 `state` 关联侧——**唯一模块依赖**（R3；`max_discovers` 侧限额常量＋指纹簿记字段的形状面；`max_subtasks` 承载键待落定＝风险 7⑤），只消费、零写入）
块性（spec :6 原注照抄）：本块＝**纯结构判定块**（真源 `docs/runtime-refactor/walk/判断归责表.md`）——解析拒收（缺字段／超限／引号异常／闭世界对账）＝结构判可做；语义判断（语义词表判「提及 vs 执行」／要不要问／覆盖没覆盖）一律不落本块。
波次: W2 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W2 行三列原文：块列「`parsing` `prompts` `transport` `persistence` `gateway_adapter`」；理由列「纯件层，只依赖 state/infra；其中 **gateway_adapter 的测试替身（fake）是后续所有相位测试的地基**，必须最先可用」；出口判据列「解析异常分支不静默；帧/游标单调；只追加可重放；模型出口唯一＋**替身可注入**」
复审强度: 50% 抽查（eng/03 §五 W2 行 A 列含 `parsing`——该表降级保留的规则原文「A 列抽 50%」；双队制已废止，A/B 分配只余复审强度语义，波序与块归属不变）
前置: ① 规格定稿（`specs/parsing.md` 已定稿——已满足）；② 波次前置：**W1 state 收波**（eng/03 §一依赖图原文「parsing → state」——唯一模块依赖）；③ 票内前置：无（-A 为本块首票；占位骨架 `appv2/runtimev2/parsing/__init__.py` 已随阶段 2 落锤）
阻塞: W1 state 收波（state 包 `RT-W1-01a/b`，按子票计；票号以主窗 manifest 为准）｜被阻塞: `RT-W2-05b-parsing.md`（同包顺序施工——-05b 前置＝-05a 收票；族名单与公开面以 -05a 为唯一真源，-05b 不另立第二套形状）；W3 `context`／`gate`（eng/03 §二 W3 行：组合件，依赖 W2 的 gateway_adapter——本块为 W2 五票之一，W2 全收即其开工条件）＋W4 三消费相位（`understanding`／`clarification`／`tool_matching`——经 R2 包根 `appv2.runtimev2.parsing` 消费）

## 任务

按 `specs/parsing.md` 新建 `appv2/runtimev2/parsing/`：把模型应答的外部文本变成**定型载荷**——理解／澄清／工具匹配三面应答的解析、发射 schema 结构校验、子任务与问题组载荷定型；**纯结构判定，零语义判断**（规格「目标」节原文：「外部文本 → 定型载荷＝卡面 Seam」）。

**本票＝parsing 的 -A 票（骨架＋三面解析器族核心簇＋本块全部 pin 行）**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **28 行**，超 15 行上限 → 切 **-A／-B** 两票。本票收 **13 行**＝规格表第 1–13 行（理解面三行／澄清面四动作两行／问题组三行／发现支一行／`ask` 一行／`finalize` 一行／匹配面两行——**三面解析器族全簇**）＋ **pin 相关两行全量**（规格「与闸的挂钩表」:189 的同参重投闸指纹面行〔内含 `pin-06` 器材面分工注〕＋ :194 的「`pin-04`／`pin-13` 不落本块」核实行，逐字转抄见「测试网钉」节）；剩余 **15 行**＝规格表第 14–28 行（拒因逐字迁移与带定位／提取单点／引号自修／载荷定型类两行／指纹器材两行／共用件单点／数字单点／元面三行／【边界集】／【保留集】）归 `RT-W2-05b-parsing.md`。两票同包**顺序施工**（同包不并行）：本票出骨架、族名单与公开面，-05b 只填剩余行为簇、不另立第二套形状（改形状＝回本票或回设计仓）。
**骨架/接口归本票**：三面解析器族签名（`parse_understanding`／`parse_question_group`／`parse_tool_match` 三函数＋共用件族四件＋载荷定型类四件＋指纹器材四件——**族名单闭世界**，规格 :39–:80 接口定义）随本票落位；`parse_question_group` 卡面初拟返回形与 V2 定案签名的差异＝卡级登记件（风险 7①，本票不改卡）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/parsing.md` 全文（十节版式——行为 1–6 的拒因清单、V2 定案差异点表、接口定义族的逐字稿都在规格行内，施工以规格原文为准）；`specs/modules.md` `## parsing` 卡（卡面两函数签名与族名单权威注——**参数名以卡为准**，返回形与限额参数以规格「V2 定案签名」为准）；`specs/state.md`（限额键「轮内发现」／「全 run 发现」＋指纹簿记字段的形状面——本块唯一模块依赖，只读）；`appv2/runtime/subtask.py`（**拒因与载荷定型的逐字稿载体**：L48-L54 四动作字面／L58 预算前缀／L82-L110 带定位拼装／L179-L290 澄清面／L318-L375 匹配面／L116-L176 与 L296-L315 字段表）；`docs/runtime-refactor/recon/L1a-子任务前半.md`（R-L1a-01…R-L1a-41——理解／澄清／发现／`ask` 面条目真源）；`docs/runtime-refactor/recon/L1b-子任务后半.md`（R-L1b-01…R-L1b-21——载荷字段与匹配面条目真源）。eng/04 §三 关联行与 eng/04a 的 `pin-06` 面已在本票「织网义务」「测试网钉」两节逐字转抄，施工期不必另开；消费方两规格（`specs/clarification.md`／`specs/tool_matching.md`）的类体差异＝登记件（风险 7③），施工以本规格行为 11 字段表为准。

**小票制自检（流水 48）**：票面对象 13 行 ≤ 15 ✓；先读 6 份 ≤ 6 ✓；聚焦一个行为簇＝「外部文本 → 定型载荷」三面解析器族（理解／澄清＋问题组＋发现＋`ask`＋`finalize`／工具匹配）✓ → 本票不派生（只切 -B 承接剩余簇）。

框架红线: 无点名框架（纯解析零框架依赖；只用标准库 `json`／`dataclasses`）——对应闸 R5b 契约（`tools/importlinter_v2.toml` :101）
边界红线: ① **只许 import `state`**（纯解析块）——R3 契约（`tools/importlinter_v2.toml` :81）；**诚实声明**：R3 的 forbidden 只列七个业务相位（亲读属实），**「禁引公共层其余块」半面无闸**→降维＝AST 断言 `::imports_state_only`＋人审；② 消费方向（R2）：三业务相位只许经包根 `appv2.runtimev2.parsing`（forbidden 含 `appv2.runtimev2.parsing.*`——:74）；③ 不引引擎（R6）、不直引 `appv2.infra.llm_client`（R7）——本块**连 `gateway_adapter` 都不 import**（零模型调用，`::parsing_pure_deterministic`）；④ 不引旧码 `appv2.runtime.*`——R5；⑤ 禁手写替代（解析单点）：提取件／拒因带定位件／引号自修件在 runtimev2 面内各恰一处定义，禁相位块另存副本（`::shared_helpers_single_source`）；⑥ **返回三态闭世界**：定型载荷｜拒因正文（`str`）｜`None`——越界返回形态（半成品载荷／部分字段／哨兵值／裸抛业务异常）＝判失败

## 票面对象（specs/parsing.md「验收测试」表逐行转抄——本票 13 行：规格表第 1–13 行）

〔来源：specs/parsing.md「验收测试」表 :131–:158（本票取自 :131–:143），逐行原文；`#` 列＝规格表行序，-05b 票续用同一行序不重编〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | 理解面：合法 JSON 两形（`route="full"`／`route="direct"`）落对，互斥单出口 | `tests/domains/test_v2_parsing.py::understanding_json_two_forms` | specs/parsing.md:131 |
| 2 | 理解面：缺必填字段／类型不符／`route` 越界 → `None`（不猜、不取默认、不降级） | `tests/domains/test_v2_parsing.py::understanding_malformed_none_no_fallback` | specs/parsing.md:132 |
| 3 | 理解面：两行式与「直接回答：」通道样本不再受理（旧降级提取零可达） | `tests/domains/test_v2_parsing.py::understanding_two_line_retired` | specs/parsing.md:133 |
| 4 | 澄清面：四动作闭世界各形落对 | `tests/domains/test_v2_parsing.py::clarify_actions_closed_world` | specs/parsing.md:134 |
| 5 | 澄清面：`action` 越界／缺失 → 拒因正文（原文逐字） | `tests/domains/test_v2_parsing.py::clarify_action_out_of_range_rejected` | specs/parsing.md:135 |
| 6 | 问题组：支条数上限（数值真源 walk/09 §七 Q-C／F-14；承载待落定）／支非对象／缺 `question`／`id` 重复 → 逐条拒 | `tests/domains/test_v2_parsing.py::question_group_schema_rejections` | specs/parsing.md:136 |
| 7 | 问题组：缺 `ledger_notes` → 拒（台账注释必带机检点） | `tests/domains/test_v2_parsing.py::ledger_notes_required` | specs/parsing.md:137 |
| 8 | 问题组：`chain` 非空越界 → 拒；支内 `tool` 键＝未知键静默丢弃（裁决 #10 退场）；本层不做链-工具一致性 | `tests/domains/test_v2_parsing.py::question_group_chain_closed_world` | specs/parsing.md:138 |
| 9 | 发现支：非空数组／单次上限／全 run 预算（前缀「发现预算」）／支缺 `tool`／`args` 非对象 → 逐条拒 | `tests/domains/test_v2_parsing.py::discover_shape_and_budget_rejections` | specs/parsing.md:139 |
| 10 | `ask` 支：缺 `ask` 对象／`prompt` 空／`options` 个数越界 → 拒；重复选项照样过 | `tests/domains/test_v2_parsing.py::ask_shape_rejections` | specs/parsing.md:140 |
| 11 | `finalize` 支：零载荷直通（不读载荷） | `tests/domains/test_v2_parsing.py::finalize_passthrough` | specs/parsing.md:141 |
| 12 | 匹配面：恰配一条全过 → tuple（顺序＝发射顺序）；缺／多／未知／重复 id → 逐条拒 | `tests/domains/test_v2_parsing.py::matches_exactly_one_per_subtask` | specs/parsing.md:142 |
| 13 | 匹配面：`chain` 闭世界／chain-tool 一致性／按链必填（`plan.metric_slot`／`retrieval_need.question`）→ 逐条拒 | `tests/domains/test_v2_parsing.py::matches_chain_tool_consistency` | specs/parsing.md:143 |

> 测试文件归属（spec :160 节尾原注照抄）：本块验收测试绑**新建** `tests/domains/test_v2_parsing.py`（`parsing` 是阶段 2 新划的公共层块，与同层 `state`／`prompts` 规格同款归属；`ls tests/domains/` 实测无同名文件，无冲突）；fixture＝**文本 fixture 集**（卡面 Adapter）。全部测试标识＝**待织网（阶段 5）**。
> 行序缺口说明（票注）：本票行序跳过 14–28——`#` 列两票共用规格表行序，便于 manifest 逐行对账。
> 本块不涉面（防一头两认）：行 14–28（拒因逐字迁移／带定位／提取单点／引号自修／载荷定型类两行／指纹器材两行／共用件单点／数字单点／元面三行／【边界集】／【保留集】）归 `RT-W2-05b-parsing.md`；本票已落地的三面解析器族签名与载荷定型类形状**不改**（改形状＝回本票或回设计仓）。

## 测试网钉（specs/parsing.md「与闸的挂钩表」pin 相关行逐行转抄——本块全表**零 `钉 **pin-NN**` 行**，pin 面只此两行，全在本票）

〔来源：specs/parsing.md「与闸的挂钩表」:189、:194，逐行原文；列名同规格「本规格的硬要求｜挂钩｜现状」〕

| 本规格的硬要求（原文） | 挂钩（原文） | 现状（原文） |
|---|---|---|
| 同参重投闸指纹面（闸件本体归本块——真源 `specs/tool_matching.md` 风险 4） | 测试 `::fingerprints_deterministic_per_branch`／`::same_param_replay_three_cases`；触发面归属＝**人审**（风险 4）；**分工注**：pin-06（空手探查记指纹）行为面挂 `specs/execution.md`（空手闸），本块只供 `discover_fingerprint` 器材——两「同参」闸勿混 | 待实现（阶段 5） |
| pin-04／pin-13 经逐条核实**不落本块**（防一头两认） | 钉落点对读：`pin-04`（发射 JSON 不进答案面）已落 `specs/answering.md` 行为 11＋其挂钩表；`pin-13`（起草回声=0）已落 `specs/prompts.md` 行为 13（合同侧）＋`specs/answering.md` 行为 14（观测面）——parsing 无第三面缺口 | 已核实（本批起草时逐条对读） |

- 分工注（票注，防两头认）：`pin-06`（空手探查记指纹＋同参空手重发发射级拒，`docs/runtime-refactor/eng/04a-应钉行为清单.md` :15 全表第 6 行）的**行为面**挂 `specs/execution.md` 行为 13（`RT-W4-05a-execution.md` 行 15，其「测试网钉」节已按 execution 规格挂钩表逐字转抄该 pin 行）；本块只落其**器材面**＝本票行 20／21 的指纹四件（`payload_fingerprint`／`discover_fingerprint`／`emission_fingerprints`／`is_same_param_replay`，行 20／21 归 `RT-W2-05b-parsing.md` 承载）——**两「同参」闸勿混**（空手探查闸＝execution 行为 13；同参重投闸＝execution 行为 14，其触发/拦截/回喂已裁归 `execution`，本块只产纯函数器材——规格风险 4，`docs/runtime-refactor/00-决议与方法.md` :102 流水 30②）。本票不重复转抄 execution 侧 pin 行全文，只写归属指针（防两处真源漂移——先例 `RT-W4-05b-execution.md` 分票理由原文「同一 pin 行在两票重复转抄＝两处真源必漂移」）。
- `pin-04`／`pin-13` 两钉的落点对读结论（本块零落点、零缺失）随上表第二行逐字在案——本票不另立第三面对账，反向保证＝行 1–3（理解面严格解析，旧降级通道零可达）。
- pin 行分布（防两处漂移，逐字稿纪律）：本块 pin 相关两行**全在本票**逐字转抄；`RT-W2-05b-parsing.md` 零 pin 行、只写归属指针。

## 施工要点（specs/parsing.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/parsing.md:100 | 行为 1 理解面＝统一 JSON 严格解析（V2 定案） | 合格 → `Understanding`（`route="full"`）｜`Direct`（`route="direct"`）两形互斥；缺 `route`／越界／缺 `text` → `None`；两行式与「直接回答：」通道不再受理（旧降级提取零可达） |
| specs/parsing.md:101 | 行为 2 澄清面＝四动作闭世界＋分派 | `action` 闭世界恰四（`discover`／`decompose`／`ask`／`finalize`）；越界或缺失 → 拒因正文（回喂）；`finalize` 支零载荷直通；`thought`／`note` 经字符串归一随定形携带；payload 无键白名单（未知键静默忽略） |
| specs/parsing.md:102 | 行为 3 问题组载荷校验（`decompose` 支） | `question_group` 须对象／`subtasks` 须非空数组／支条数超上限 → 拒；逐支按序过闸（`id` 归一后非空且组内唯一／`question`／`ledger_notes` 非空／`chain` 非空时 ∈ `data`｜`knowledge`；`tool` 键＝未知键静默丢弃）；本层不做链-工具一致性 |
| specs/parsing.md:103 | 行为 4 发现支校验＋预算闸 | `discovers` 须非空数组／支数超单次上限 → 拒／超剩余预算 → **预算拒**（拒文以机读前缀「发现预算」开头）；支须对象且含 `tool`；`args` 缺省归一空对象、**非对象＝拒**（拒文＝`appv2/runtime/graph.py` L616 字面「发现工具 {tool} 的 args 须为对象」） |
| specs/parsing.md:104 | 行为 5 `ask` 支校验 | `ask` 须对象／`prompt` 归一后非空；`options` 非 list → 归一空列表（随后按个数越界拒）；list 逐项字符串化去空白、空白项丢弃（不去重）；个数不在「2~4」→ 拒（拒文＝`appv2/runtime/subtask.py` L288-L289 字面） |
| specs/parsing.md:105 | 行为 6 工具匹配面＝闭合世界对账（恰一一对应） | `matches` 须非空数组、逐支按序 fail-fast：`id` 在问题组 id 集内／组内不重复；`chain` ∈ `data`｜`knowledge` 且 `tool` ＝该链唯一工具；按链必填（`data`→`plan.metric_slot`／`knowledge`→`retrieval_need.question`）；覆盖缺口拒（拒文列缺失 id 全量）；返回顺序＝发射顺序 |
| specs/parsing.md:106 | 行为 7 拒因正文＝机器拒因原文（迁移照抄，零改动） | 全部分支拒因文本逐字迁移、承载位换文本不变；逐字稿载体＝迁移前现行代码 `appv2/runtime/subtask.py`（L82-L110／L179-L290／L318-L375）；机读甄别面恰一值：前缀「发现预算」（行 14 归 -05b 承载，本票行 5／9 的拒文须与之同源） |

结构锚：specs/parsing.md:39–:80 接口定义（**V2 定案签名**——三面解析器族＋共用件族四件＋载荷定型类四件＋指纹器材四件，族名单闭世界；卡面 `parse_understanding`／`parse_question_group` 两函数为阶段 2 初拟形，返回形以 V2 定案为准）；:82–:86 返回三态闭世界／错误契约／入参纪律；:88 V2 定案差异点表（七点，供逐字比对——① 理解面统一 JSON 严格解析／② 不裸抛业务异常／③ 解析上限注入制／④ 预算拒文内嵌数值待裁／⑤ `parse_decision` 退场／⑥ `Subtask.tool` 退场／⑦ 指纹器材公开化）；:90–:96 框架与依赖红线；:119–:125 不降级与静默禁令（**合法降级路径＝无**；拒因恒非空＋预算前缀两处机读信号；本块零截断）。剩余行（14–28）的骨架对齐随本票落位、行为断言在 `RT-W2-05b-parsing.md`。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三——本块无明写归块行，下列一行为逐字转抄的关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单（该表内明写块名者只有 B1→`bookkeeping`／B2→`orchestration`／B2b→`preconditions`／B4→`gate`，**无一行明写「对应 runtimev2 `parsing`」**；下表一行为关联行）〕

> | B6 | 挂起恢复多场景（clarify 二级／越集审批／跨实例） | 专属钉＋回放钉（跨实例条保持门控） | 中 |

- 归块注（呈主窗对账）：§三 表内**无一行明写本块**——上引 B6 为**关联行**：B6 的「clarify 二级」形里，本块的 `ask` 支载荷校验（行为 5，行 10）是**二级反问发射载荷的定型点**（挂起前的载荷由此定型）；挂起/恢复行为体在 `clarification`／`execution`／`orchestration`，本块不承载——切分呈主窗。本行逐字转抄＝**§三 表内本块侧的唯一一处**（防两处真源漂移）。
- 关联行（落他票，**只留指针、不重复转抄**——§三 各行恰一票逐字转抄）：B1（明写归 `bookkeeping`；`RT-W3-01a-bookkeeping.md` 同节逐字转抄）、B3（「限额上限」半面；本块的**解析侧上限判定**＝行 6／行 9／行 10，其**触顶收敛**半面归 `state`／`bookkeeping`——逐字转抄落 **`RT-W1-01b-state.md`** 同节）、B4（明写归 `gate`；`RT-W3-03a-gate.md` 同节逐字转抄）——本票不重复转抄、不冒充覆盖。
- 本票织网义务＝① 上引 B6 关联行的 L1／L3 钉（织网工序第 3 步「盲区补钉」，与 W1–W2 施工可并行——eng/04 头注）；②「测试网钉」pin 相关两行对应用例落网（`pin-06` **器材面**：本票行 20／21 的指纹四件用例，行为面用例在 execution 侧——织网以规格分工注为准、不双写）；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」13 行逐行实现为 `tests/domains/test_v2_parsing.py` 用例并全绿，测试标识与规格列逐字一致（`#` 保留规格表行序 1–13）；
- 「测试网钉」pin 相关两行对应用例在场且绿（`pin-06` 器材面用例；`pin-04`／`pin-13` 零落点核实在案——本票不重复转抄 -05b 的零 pin 行）；
- 骨架与族名单落位：三面解析器族签名＋共用件族＋载荷定型类＋指纹器材齐（规格 :39–:80，族名单闭世界），返回三态闭世界与错误契约在场；-05b 不得另立第二套形状；
- 三面拒因与迁移前字面同源（逐字稿＝`appv2/runtime/subtask.py`——行 5／9 的拒文照抄不改，偏离即停）；
- 边界闸 R2／R3／R5／R5b／R6／R7 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W2-05a 完成，产物 `appv2/runtimev2/parsing/`（骨架＋三面解析器族核心簇），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
