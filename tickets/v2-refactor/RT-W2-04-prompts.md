# RT-W2-04 · prompts——V2 指令与提示词

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/prompts.md`（状态「已定稿」——前置满足）
Touches modules: `prompts`（本票只建 prompts 本体；规格「触及的模块」表：`state` 已定稿——唯一模块依赖，只消费其形状与投影字段，零写入）
块性（spec :6 原注）：本块＝**「只出文本」块**——全部行为约定都是**纯文本装配**断言，无一处程序语义判定；凡语义判断（要不要问／提及 vs 执行／覆盖没覆盖）一律不落本块。
波次: W2（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W2 行：纯件层，只依赖 state/infra）
施工队: A 队（eng/03 §五 终表 W2 行 A 队列＝「persistence／transport／prompts／parsing」；已按 eng/03 §五 终表对齐）｜复审强度: 100%（A 队收波 100% 过独立复审；复审网在 L0 直派）
前置: ① 规格定稿（`specs/prompts.md` 已定稿——已满足）；② 波次前置：**W1 state 收波**（eng/03 §一依赖图：prompts → state——唯一模块依赖）
阻塞: W1 state 收波（RT-W1-01）｜被阻塞: 四业务相位消费方（understanding／clarification／tool_matching／answering——经 R2 包根 `appv2.runtimev2.prompts` 消费，W4 波）

## 任务

按 `specs/prompts.md` 新建 `appv2/runtimev2/prompts/`：把发给模型的每一轮指令变成**合同常量＋确定性装配的纯文本**——各相位提示词合同常量、任务书／决策轮／答案轮的指令装配；**只出文本、不做判断**（判断在模型，装配在程序，互不越位）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: `specs/prompts.md` 全文（十节版式——行为 2 的答案要求清单七条、行为 16 的增量条逐字稿都在规格行内，施工以规格原文为准）；`specs/modules.md` `## prompts` 卡（签名以卡为准）；`specs/understanding.md` 行为 1／行为 2／行为 10（三区序／来源标记面／三则样例同源）；`appv2/runtime/orientation.py` `_ANSWER_REQUIREMENTS`（L282-290，答案要求七条迁移逐字稿）与 `answer_turn_preamble`（L295-300，动词钉死句）；`docs/runtime-refactor/recon/L2a-装配前半.md`／`L2b-作答装配与回声.md`（装配真源）；`docs/runtime-refactor/recon/E1-澄清节点.md`／`E2-工具匹配节点.md`（合同与增量条真源）；`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二／§五；`docs/runtime-refactor/eng/04-测试网设计.md` §三／§五；AGENTS.md 硬纪律 6b（逐字稿纪律）

框架红线: 无点名框架（本块不引入任何框架；纯字符串装配零依赖）——对应闸 R5b 契约
边界红线: ① 只许 import `state`（R3——「禁引公共层其余块」半面无闸，AST 测试 `::imports_state_only` 补位＋人审）；② 消费方向（R2）：四业务相位只许经包根 `appv2.runtimev2.prompts` 消费（深层子模块私有）；③ 不引引擎（R6）、不直引 `appv2.infra.llm_client`（R7）——本块连 `gateway_adapter` 都不 import（零模型块）；④ 零时钟接触（时间量只经入参注入——B14 纪律在装配面的形态）；⑤ 禁手写替代：合同文本单点在本块，禁相位块／编排块另存合同字面（V1 病灶 D-L2b-01——`::answer_requirements_single_source`）

## 票面对象（specs/prompts.md「验收测试」表逐行转抄，23 行）

〔来源：specs/prompts.md「验收测试」表 :108–:130，逐行原文〕

| # | 验收标准（原文） | 对应测试（原文标识） |
|---|---|---|
| 1 | 合同常量族集合与接口清单相等（名单闭世界） | `tests/domains/test_v2_prompts.py::contract_constant_family_closed_world` |
| 2 | 答案要求清单 7 条逐字在场、顺序固定、以「；」分隔 | `tests/domains/test_v2_prompts.py::answer_requirements_verbatim_seven` |
| 3 | 答案要求清单 runtimev2 面内恰一处定义（消费方零字面副本；系统层不在范围） | `tests/domains/test_v2_prompts.py::answer_requirements_single_source` |
| 4 | 合同常量六族字面副本零残留（六族首句特征子串在四相位块／编排块源码零命中；系统层不在范围） | `tests/domains/test_v2_prompts.py::contract_constants_no_duplicate_literals` |
| 5 | 任务书段序固定、题干段置末紧邻生成点 | `tests/domains/test_v2_prompts.py::task_book_segment_order` |
| 6 | 任务书样例区＝固定三则、不随 state 变化、无边界对照例 | `tests/domains/test_v2_prompts.py::task_book_examples_fixed_set` |
| 7 | 数据区活体投影现取：改投影 → 输出随之变 | `tests/domains/test_v2_prompts.py::data_zone_live_projection` |
| 8 | 空投影 → 占位文案逐字在场（族／指标／术语／对象／关系／水位） | `tests/domains/test_v2_prompts.py::empty_projection_placeholder_verbatim` |
| 9 | 题意锚行两形（理解真值/假值）且置于决策轮指令首行 | `tests/domains/test_v2_prompts.py::anchor_line_two_forms_first_line` |
| 10 | 决策轮首入包构成逐件在场（行为 7 构成清单——澄清／匹配轮各按其件）、常驻块包裹对恰一对；四要素按轮合看逐轮在场 | `tests/domains/test_v2_prompts.py::decision_package_four_elements` |
| 11 | 决策轮增量条构成与逐字稿（澄清轮：探查预算／回炉／用户补充／拒因回喂／已做段；匹配轮：拒因回喂／已做段；改道后缀触发＝机器拒因闭世界子串校） | `tests/domains/test_v2_prompts.py::decision_increment_lines_present` |
| 12 | 台账常驻块逐字转抄、恰一份；三删段名字面缺席 | `tests/domains/test_v2_prompts.py::ledger_resident_block_verbatim_once` |
| 13 | 消歧头统一措辞逐字在场 | `tests/domains/test_v2_prompts.py::disambiguation_header_uniform` |
| 14 | 分解样例三分支（未绑定→knowledge／可出数→data／空→空串） | `tests/domains/test_v2_prompts.py::decompose_example_three_branches` |
| 15 | 分解样例产出为合法 JSON 且键形正确（顶层恰 action＋question_group 两键、subtasks 单条五键） | `tests/domains/test_v2_prompts.py::decompose_example_valid_json` |
| 16 | 合同常量零业务名词（fixture 词集与水位日形交集＝∅） | `tests/domains/test_v2_prompts.py::contract_constants_business_noun_free` |
| 17 | 答案轮段序固定（三件套→汇总合同→子问题清单→起草合同）；材料段零渗入 | `tests/domains/test_v2_prompts.py::answer_round_segment_order_no_material` |
| 18 | 答案轮禁令件在场（动词钉死句＋答案要求⑦；pin-13 合同侧） | `tests/domains/test_v2_prompts.py::answer_round_ban_lines_present` |
| 19 | 装配确定性纯函数：两跑逐字相等、不改入参、零 IO／模型／时钟（AST） | `tests/domains/test_v2_prompts.py::assembly_pure_deterministic` |
| 20 | import 面只许 state（AST 扫描——R3 半覆盖面的降维补位） | `tests/domains/test_v2_prompts.py::imports_state_only` |
| 21 | 程序侧无词表／正则语义判断（AST；豁免面＝集合成员判定与逐字子串校） | `tests/domains/test_v2_prompts.py::no_lexicon_or_regex_in_prompts` |
| 22 | 【边界集】空台账／缺水位／零未绑定指标（全可出数）／子问题清单超长 → 各落占位文案／空串段／data 链形分支 | `tests/domains/test_v2_prompts.py::boundary_empty_projection_variants` |
| 23 | 【保留集】常规投影装配输出不受空投影分支影响；四消费方既有验收断言不因本块改形回归 | `tests/domains/test_v2_prompts.py::retention_normal_assembly_unchanged` |

> 测试文件归属（spec :132 节尾原注照抄）：本块验收测试绑**新建** `tests/domains/test_v2_prompts.py`（`prompts` 是阶段 2 新划的公共层块，与同层 `state` 规格同款归属；现状旧码装配测试在 `tests/domains/test_v2_v262_turn_selfsufficiency.py` 等，本批不改）。全部测试标识＝**待织网（阶段 5）**。

## 测试网钉（specs/prompts.md「与闸的挂钩表」pin 行逐行转抄，3 钉）

〔来源：specs/prompts.md「与闸的挂钩表」:161–:163，逐行原文〕

1. **pin-03（P0）**｜硬要求原文：答案要求③多来源分源（跨油田题分源列明的合同侧承接；`specs/verification.md` 挂钩表登记「prompts 规格落盘后承接」）｜挂钩原文：钉 **`pin-03`**（P0）——本块落点＝合同侧③逐字在场（行为 2）；**交付行为面待 `specs/answering.md` 回提承接**（其挂钩表现无 pin-03 行——跨规格债登记交主窗，风险 7②；`specs/verification.md` 挂钩表亦只登记备查）｜现状原文：待织网（阶段 5）
2. **pin-13（P1）**｜硬要求原文：起草回声＝0 的**提示词侧**（不注入回声形指令：动词钉死句＋答案要求⑦在场）｜挂钩原文：钉 **`pin-13`**（P1）——**分工**：本块落点＝合同侧禁令件在场（行为 13、测试 `::answer_round_ban_lines_present`）；观测面（`echo_flag` 恒 0）落 `specs/answering.md` 行为 14（已定稿）｜现状原文：待织网（阶段 5）
3. **pin-24（P1）**｜硬要求原文：相位合同一次性（回炉轮不重发）｜挂钩原文：钉 **`pin-24`**（P1）——**行为不归本块**：追加记账归 `specs/state.md` 行为 5（已定稿，测试 `contracts_appended_idempotent`）；消费侧重发判定待 `context`／`orchestration` 规格；本块只承诺合同常量逐字稳定（常量无逐轮变体，行为 1）｜现状原文：待织网（阶段 5）——记账面已在 state 侧落，消费侧待 context/orchestration

## 施工要点（specs/prompts.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/prompts.md:80 | 行为 1 合同常量名单闭世界＋文本单点 | 全仓合同文本定义点唯一（六族）；消费方只经包根引用，相位块／编排块零字面副本 |
| specs/prompts.md:81 | 行为 2 答案要求清单七条逐字（迁移照抄） | 逐字稿＝`orientation.py` `_ANSWER_REQUIREMENTS`（L282-290）；承载位换、文本不变；③多来源分源＝pin-03 合同侧承接（承接注记，不属合同文本） |
| specs/prompts.md:82 | 行为 3 任务书段序固定、题干置末 | 三区序＝指令区→数据区→输出契约区；对 V1 的两处设计变更已显式声明（红线移入指令区、输出契约区 V2 新增） |
| specs/prompts.md:83 | 行为 4 样例区固定三则 | 多部分题／口语映射题／判断纠错题；不加边界对照例；样例区文本不随 state 变化（常量直引） |
| specs/prompts.md:84 | 行为 5 数据区活体投影＋空投影占位文案 | 改投影输出随变；占位文案逐字稿真源 `R-L2a-19`（「（暂无族标注）」「（空）」「关系：（空）」「（水位未取得）」） |
| specs/prompts.md:85 | 行为 6 题意锚行两形 | 理解真值→单行「用户原题：{question}｜题意：{understanding}」；假值→单段不输出空「题意：」段；置于决策轮指令最前 |
| specs/prompts.md:86 | 行为 7 决策轮首入包构成固定、逐件可溯 | 锚行＋相位合同＋（澄清轮）分解样例／（匹配轮）合同内嵌样例＋§A 指南段（文本经入参注入）＋问题组 JSON＋台账常驻块；四要素按轮合看逐轮在场 |
| specs/prompts.md:87 | 行为 8 台账常驻块逐字转抄、恰一份、三删不回流 | 台词条目逐字转抄自 state 投影；与合同逐字重复段／名录重复份／收口硬规则旧句不回流（V2-59 纪律装配面） |
| specs/prompts.md:88 | 行为 9 消歧头统一措辞 | 两轮统一「……窗词锚定/单井红线/三链路由；动作类措辞以上方合同为准」；「发射判据」「指标名册」「收口硬规则」段名缺席 |
| specs/prompts.md:89 | 行为 10 分解发射样例动态渲染、不进合同常量 | 三分支＝未绑定→knowledge／可出数→data／空投影→空串（调用方跳过）；payload 两层嵌套、子问题条目五键齐全 |
| specs/prompts.md:90 | 行为 11 合同常量零业务名词 | 合同文本不含台账真源指标名／别名／井号形／业务日期段字面（fixture 词集与水位日形扫描交集＝∅） |
| specs/prompts.md:91 | 行为 12 答案轮段序固定、材料段零渗入 | 三件套置顶→汇总合同→子问题清单→起草合同收尾；材料段由调用方按 context 渲染产物追加于尾 |
| specs/prompts.md:92 | 行为 13 答案轮禁令件在场（pin-13 合同侧） | 动词钉死句＋答案要求⑦两字面在场；提示词侧不注入回声形指令 |
| specs/prompts.md:93 | 行为 14 装配确定性纯函数 | 同入参两跑逐字相等；调用前后 state 深比较相等；零 IO／模型／时钟／随机（AST） |
| specs/prompts.md:94 | 行为 15 不夹带程序判断 | 装配输出无程序语义结论文本；豁免面＝形态处理（集合成员判定与逐字子串校不算语义词表／正则） |
| specs/prompts.md:95 | 行为 16 决策轮增量条构成固定、逐字稿在行内 | 澄清轮五件（探查预算／回炉／用户补充／拒因回喂／已做段）＋匹配轮两件（拒因回喂／已做段）；何时追加＝调用方义务，本块只供条文本 |

结构锚：specs/prompts.md:34 接口定义（合同常量六族名单＋装配函数族 `assemble_task_book`／`assemble_answer_prompt` 签名＋族成员名单闭世界）；:70–76 框架与依赖红线（R5b／R3 半覆盖诚实声明／R2／R6／R7）；:97–102 不降级与静默禁令（合法降级路径＝无；缺位机读信号两形＝占位文案＋空串段；本块零截断）。跨规格债登记（spec 风险 7①–⑦，本批只登记不代办——交主窗统一回提）：understanding 行为 1 枚举缺口（P-01/SZP-05）／answering 挂钩表补 pin-03 行（P-05）／answering 触及面改述（P-11）／context 卡「术语表常驻注入」两说（P-07）／prompts 卡注释补族名单注记（P-08）／SYSTEM_PROMPT 落块归属（P-10）／GuideProvider 装载落点（P-02）。

## 织网义务（eng/04-测试网设计.md §三 归本块行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单，B1–B7b/B7 逐行核对〕

- **无**（按实写）：§三盲区表 B1–B7b/B7 无 prompts 行（B1→bookkeeping、B2→orchestration、B2b→preconditions、B3→预算、B4→gate、B5→transport、B6→挂起恢复、B7b→gateway_adapter、B7→tools）。
- 本票织网义务＝①「测试网钉」3 钉（pin-03／pin-13／pin-24）对应用例落网（现状列均为「待织网（阶段 5）」——pin-03 的交付行为面与 pin-24 的消费侧重发判定面在他块规格，织网以规格分工注为准、不双写）；② L2 新规格钉随本票施工 TDD 生长（eng/04 §五：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」23 行逐行实现为 `tests/domains/test_v2_prompts.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行）；
- 「测试网钉」3 钉对应用例在场且绿（pin-03 为 P0 承重钉——本票落点＝合同侧③逐字在场）；
- 答案要求七条迁移照抄零偏离（逐字稿＝`orientation.py` `_ANSWER_REQUIREMENTS` L282-290——照抄不改，偏离即停）；
- 边界闸 R2／R3／R5b／R6／R7 在 `lint-imports` 双配置下绿；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W2-04 完成，产物 `appv2/runtimev2/prompts/`，偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
