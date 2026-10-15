# V2 指令与提示词（prompts）

状态: 草稿
来源: `specs/modules.md` `## prompts` 卡、`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §三 B、`docs/runtime-refactor/walk/08-澄清-意图澄清.md`、`docs/runtime-refactor/walk/09-澄清-分解问题.md`、`docs/runtime-refactor/walk/14-作答-汇总作答.md`、`docs/runtime-refactor/walk/裁决表.md`（§04／§06／§14＋项目级裁决 #12/#13）、`docs/runtime-refactor/recon/L2a-装配前半.md`、`docs/runtime-refactor/recon/L2b-作答装配与回声.md`、`docs/runtime-refactor/recon/E2-工具匹配节点.md`、`docs/runtime-refactor/recon/I2b-RunState全字段.md`、`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`（V2-58／59／62）、`docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md`（A-P6b-25 相位一次性）、`docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-03／pin-13／pin-24）
版式: `docs/spec-format.md`（节标题按该文 §二之二 逐字命名） ｜ 工序: `docs/spec-process.md`
块性: 本块＝**「只出文本」块**（真源 `docs/runtime-refactor/walk/判断归责表.md`）——本规格全部行为约定都是**纯文本装配**断言，无一处程序语义判定；凡语义判断（要不要问／提及 vs 执行／覆盖没覆盖）一律不落本块。

## 目标

把发给模型的每一轮指令变成**合同常量＋确定性装配的纯文本**——各相位提示词合同常量、任务书／决策轮／答案轮的指令装配；**只出文本、不做判断**（判断在模型，装配在程序，互不越位）。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 模型输出的解析与发射 schema 校验 | `parsing` | `specs/modules.md` `## parsing` |
| 材料段渲染、Manifest 编译、配额与截断、术语表常驻注入的动态内容来源装载 | `context` | `specs/modules.md` `## context` |
| 模型调用、限流退避、记账 | `gateway_adapter`（本块**零模型调用**，连该出口都不 import） | `specs/modules.md` `## gateway_adapter` |
| 合同消息的追加记账与重发判定（`contracts_appended`） | `state`（行为 5 已定稿）＋追加执行归 `orchestration`；本块只供给逐字稳定的合同文本 | `specs/state.md` 行为 5；钉 `pin-24` |
| 发射判据的语义判断（窗可锚定／要不要问／提及 vs 执行） | 模型侧产出；分派归 `clarification`／`preconditions` | `docs/runtime-refactor/walk/裁决表.md` 项目级裁决 #12/#13 |
| 用词表／正则挑选装配内容（装配面语义判断） | **不做**——只按 state 投影与合同常量机械拼接 | `docs/runtime-refactor/walk/判断归责表.md` |
| 步记录／序号／触界收敛等状态写口 | `bookkeeping`（唯一写口） | `specs/modules.md` `## bookkeeping` |
| 台账／名录投影的**取得**（查台账、调工具） | `context` 经 `tools` 公开面只读装载进 state；本块只读 state 投影渲染 | `specs/modules.md` `## context` |
| 过程档案（已做段）的有界摘要渲染 | `context`（本块增量条装配只接其渲染产物文本作入参） | `specs/modules.md` `## context` |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| prompts | 新增 | 本块本体：合同常量族＋各轮装配函数族（纯文本进出） |
| state | 已定稿 | 唯一模块依赖（R3）；只消费其数据形状与投影字段，零写入 |

## 接口定义

```python
# ── 合同常量族（名单闭世界，六族；文本单点在本块，消费方只引用不复制）──
# ① 任务书静态骨架四常量（场景／任务／样例／红线）
# ② 澄清发射合同                      # 澄清相位四动作发射契约（消费方 clarification）
# ③ 工具匹配发射合同                  # 匹配相位发射契约（消费方 tool_matching）
# ④ 汇总合同                          # 答案轮中段
# ⑤ 起草答案合同                      # 答案轮收尾段（承载行集交付规矩，真源 arch/P4b A-P4b-49）
# ⑥ 答案要求清单（7 条——逐字稿见「行为约定」2）
# ── 装配函数族（卡面两函数逐字照录；纯文本进出＝Seam）──────────────
def assemble_task_book(state: RunState) -> str: ...
def assemble_answer_prompt(state: RunState) -> str: ...
# 族内其余成员（卡面「各轮装配函数」的展开，名单闭世界）：
#   题意锚行装配件 anchor_line(question, understanding) -> str
#   决策轮首入包装配（澄清轮／工具匹配轮——锚行＋相位合同＋样例＋台账常驻块包裹）
#   拒因回喂条装配／用户补充条装配（决策轮增量条；过程段文本由调用方传入）
#   分解发射样例渲染器（运行时现造、不进合同常量——行为约定 10）
```

- **合同常量族名单是闭世界**：上列六族之外新增合同文本＝只许以「新增常量入族＋同批改本清单」方式进块；消费方私设第二合同源（合同字面复制进相位块）＝判失败。
- **装配函数族名单是闭世界**：族成员即上列成员；增删成员须同批对账四消费方规格（`specs/understanding.md`／`specs/clarification.md`／`specs/tool_matching.md`／`specs/answering.md`）的触及面。常量实名与函数签名阶段 5 施工时按卡定（本规格锁的是**名单闭世界**与**纯文本进出**）。
- **错误契约（纯文本进出）**：装配函数输出恒为 `str`——**不抛业务错、不返回 `None`**；投影缺位走**占位文案**（逐字见行为约定 5）或**空串段**（空串＝「该段缺位」的机读信号，调用方跳过，真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-32「台账空投影返回空串（调用方跳过）」）。
- **入参纪律**：装配函数消费 state 投影字段（字段面以 `docs/runtime-refactor/synth/S5-RunState字段矩阵.md` 为界，只读）＋调用方传入的文本（如过程段渲染产物、时间量）；**时间量只经入参注入**，本块不读时钟（时间一律 `infra.clock` 的 B14 纪律在装配面的形态＝零时钟接触，时钟值由调用方注入）。
- 真源：`specs/modules.md` `## prompts` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本块不引入任何框架；纯字符串装配零依赖）。验收写法：依赖锁文件不出现框架包＋行为测试绿。对应闸：**R5b 契约**（`tools/importlinter_v2.toml`）。
- **只许 import `state`（纯文本块）**：本块不感知运行状态机、不引任何其他 runtimev2 块。对应闸：**R3 契约**——**诚实声明覆盖面**：R3 的 forbidden 只列七个业务相位，**「禁引公共层其余块」（bookkeeping／context／transport／persistence／gateway_adapter／orchestration／gate）这半面无闸**；降维＝AST import 扫描测试（`::imports_state_only`），余面人审（见挂钩表）。
- **消费方向（R2）**：四个业务相位只许经包根 `appv2.runtimev2.prompts` 消费本块（深层子模块私有）。对应闸：**R2 契约**。
- **不引引擎**（knowledge/query/retrieval）、**不直引 `appv2.infra.llm_client`**。对应闸：**R6 契约**／**R7 契约**；本块连 `gateway_adapter` 都不 import（零模型块）——该面由 `::no_model_call_in_prompts`（AST）承载，R1–R8 无此专属闸。
- **禁手写替代**：合同文本单点在本块，禁在相位块/编排块另存一份合同字面（V1 病灶：同一答案规则三处字面并维护，真源 `docs/runtime-refactor/recon/L2b-作答装配与回声.md` D-L2b-01）。验收写法：全仓唯一定义点断言（`::answer_requirements_single_source`）。

## 行为约定

1. **合同常量名单闭世界＋文本单点**：全仓合同文本定义点唯一（六族清单见接口定义）；消费方（四相位）只经包根引用常量，**任何相位块/编排块内不出现合同字面副本**。断言：答案要求清单文本在仓内恰一处定义；合同常量族集合与接口清单相等（集合比较）。
2. **答案要求清单＝7 条逐字在场、顺序固定、以「；」分隔**（条数真源＝`docs/runtime-refactor/recon/L2b-作答装配与回声.md` R-L2b-02，现 7 条；`specs/answering.md` 行为 10 以本合同为唯一真源、不复述）。七条内容：①逐条事实断言带 [n] 引标；②材料未覆盖部分不得断言、须如实说明未覆盖；③材料含多个来源（不同报告／油田／井）时逐个来源分别作答——不冲突也要分别列出、不以反问代替作答（钉 `pin-03` 的合同侧承接面，见挂钩表）；④作答后仍有未覆盖来源或指代不明处，如实点名未覆盖来源（含检索窗注记的未进窗来源）并请用户补充检索或指明对象、不静默略过；⑤引擎的降级／未绑定／拦停注记必须如实转述进对应子问题条目、不得静默丢弃；⑥引用观察材料摘录必要短语并带引标、禁整段照搬原文充当回答；⑦「理解：／指标候选：」及任何动作 JSON 出现即废品。断言：七条逐字在场且顺序固定（施工以本条为逐字稿，照抄不改；偏离即停）。
3. **任务书段序固定、题干置末**：指令区（场景／任务／样例／红线）→ 数据区（活体投影环境段）→ 输出契约区（统一 JSON 契约，末尾、短）→ 题干段置末、紧邻生成点；三区划分与顺序以 `specs/understanding.md` 行为 1 为准，本块断言**段边界与段序**（V1 六段先例真源 `docs/runtime-refactor/recon/L2a-装配前半.md` R-L2a-17/R-L2a-22）。断言：给定 fixture 状态，装配输出按上述段序逐段可定位、题干段为末段。
4. **任务书样例区＝固定示例集**（多部分题／口语映射题／判断纠错题三则；真源 `docs/runtime-refactor/walk/04-理解-读题步.md` §一「三则样例」＋`docs/runtime-refactor/walk/裁决表.md` §04-C；`specs/understanding.md` 行为 10 同源）；**不加边界对照例**。断言：三则逐字在场、装配输出中样例区文本不随 state 变化（常量直引）。
5. **数据区从活体投影现取且空投影走占位文案**：改 fixture 投影 → 输出文本随之变（来源标记面以 `specs/understanding.md` 行为 2 为准）；空投影走**逐字占位文案**——族「（暂无族标注）」、指标／术语／对象「（空）」、关系「关系：（空）」、水位「（水位未取得）」（逐字稿真源 `docs/runtime-refactor/recon/L2a-装配前半.md` R-L2a-19）。断言：空投影 fixture → 占位文案逐字在场；投影增删一行 → 输出同步增删。
6. **题意锚行两形、置于决策轮指令最前**：`anchor_line(question, understanding)`——理解真值 → 单行「用户原题：{question}｜题意：{understanding}」（前缀固定「用户原题：」、全角冒号、全角「｜」直连）；理解假值 → 单段「用户原题：{question}」（**不输出空「题意：」段**）；插澄清轮／工具匹配轮指令最前（真源 `docs/runtime-refactor/recon/L2b-作答装配与回声.md` R-L2b-10/11/12＋`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-59）。断言：两形分支逐字＋锚行在装配输出的首行位。
7. **决策轮首入包构成固定**：澄清轮／工具匹配轮的首入装配＝题意锚行＋相位合同＋（澄清轮另加）分解发射样例＋台账常驻块包裹——常驻块形＝BEGIN＋字典说明行＋台账／别名／结构卡三块＋END（构造先例真源 `docs/runtime-refactor/recon/E2-工具匹配节点.md` 相位包首入段）。断言：给定 fixture 状态，首入包四件齐（四要素制度的任务动词／题意锚／产出样例／失败反馈逐轮在场——制度真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-56）、块包裹对恰一对。
8. **台账常驻块逐字转抄、恰一份、三删不回流**：常驻块内台词条目**逐字转抄**自 state 投影（不改写、不摘要——`ledger_notes` 逐字可求得的前提，`specs/clarification.md` 行为 8 的承接面）；台账/名录信息在决策轮装配输出中**恰出现一次**（只经常驻块一份，装配不另拼名录段——V2-59 三删纪律的装配面：与相位合同逐字重复的段、名录重复份、收口硬规则旧句不回流，真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-29/30）。断言：fixture 台账每条目在输出中恰出现一次；三删段名字面在澄清轮装配输出中缺席。
9. **消歧头统一措辞**：澄清／工具匹配两轮装配的消歧头统一为「……窗词锚定/单井红线/三链路由；动作类措辞以上方合同为准」且不点名已删段（逐字稿真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-33）。断言：两轮装配输出含该逐字句；「发射判据」「指标名册」「收口硬规则」段名缺席。
10. **分解发射样例＝运行时动态渲染、不进合同常量**：样例含台账真源词与当日日期，结构性进不了合同（「合同零业务名词」命名闸所迫，真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-32）；渲染规则：取**首条未绑定指标** → knowledge 链／doc_retrieve 形；无未绑定取首条可出数 → data 链／data_query 形；台账空投影 → 返回空串（调用方跳过）；样例窗＝「today−近 30 天 ~ today」示意（默认窗口径真源 `docs/runtime-refactor/walk/08-澄清-意图澄清.md` §七 Q-B）；payload 五键齐全（action／id／question／ledger_notes／chain/tool）。断言：三分支各自落对；产出样例段为合法 JSON 形（可解析——V1 病灶「字符串拼接无转义产非法 JSON」不复现，真源 `docs/runtime-refactor/recon/L2a-装配前半.md` D-L2a-13）。
11. **合同常量零业务名词**：合同常量文本不含台账真源指标名／别名／井号形／业务日期段字面（fixture 词集与水位日形扫描交集＝∅；真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-32 的命名闸记述——示例词纪律同款）。断言：合同常量族逐常量扫描交集为空（集合成员判定，属形态处理豁免面）。
12. **答案轮段序固定、材料段零渗入**：装配输出段序＝三件套置顶（行 1「用户问题：{question}」→ 行 2 动词钉死句 → 行 3「【答案要求】」内嵌答案要求清单全文）→ 汇总合同 → 子问题结果清单 → 起草答案合同（收尾）；**材料段不在装配输出内**（由调用方按 `context` 渲染产物追加于尾——材料渲染归 context）。断言：段序逐段可定位；输出末段＝起草答案合同；装配输出不含任何观察行内容子串（真源：段序 `docs/runtime-refactor/recon/L2b-作答装配与回声.md` R-L2b-04/07；三件套先例同文件 `answer_turn_preamble` 节）。
13. **答案轮禁令件在场（钉 `pin-13` 的合同侧）**：装配输出含动词钉死句（本步是写答案步、不再做任何决策、不再发射任何动作指令）与答案要求⑦（「理解：／指标候选：」及任何动作 JSON 出现即废品）两字面——**提示词侧不注入回声形指令**；回声的观测面（`echo_flag` 恒 0）落 `specs/answering.md` 行为 14，本块只承接合同侧禁令件（分工见挂钩表）。断言：两句逐字在场（真源 `docs/runtime-refactor/recon/L2b-作答装配与回声.md` R-L2b-02 第⑦条＋`answer_turn_preamble` 动词钉死句；钉 `pin-13`，P1）。
14. **装配是确定性纯函数**：同入参两次装配输出逐字相等；调用前后 state 深比较相等（零写入）；AST 扫描本块——零 IO、零模型调用、零时钟读取（时间经入参注入，见接口定义）、零随机。断言：两跑逐字相等＋深比较相等＋AST 零命中。
15. **不夹带程序判断**：装配输出＝合同常量与 state 投影的确定性拼接，**不含任何程序判定的结论文本**（三选一结论／放行／拒答／覆盖自证／verdict 等语义结论不作为装配产物产生——那些是模型产出或结构判定，归 `clarification`／`preconditions`／`verification`）；AST 扫描本块无语义词表／正则判定（**豁免面＝形态处理**：集合成员判定与逐字子串校不算语义词表／正则，先例 `specs/understanding.md` 验收表同款）。断言：`::no_lexicon_or_regex_in_prompts` 绿＋行为 14 的确定性断言成立（输出无输入之外的语义增量）。

## 不降级与静默禁令

- **合法降级路径：无**——装配不降级：投影缺位走**占位文案**或**空串段**两形，不删段、不编造数据、不替换成通用措辞。
- **缺位的机读信号＝两形**：空串段（调用方跳过）＋占位文案（「（空）」「（水位未取得）」「（暂无族标注）」「关系：（空）」逐字在场）；断言：缺位投影 → 信号在场（行为 5／验收行）。
- **本块零截断**：装配输出不做任何静默截断／省略（截断与配额归 `context`，Manifest 记账归 `context`）；输出中不出现省略号形占位。
- 红线原文：`docs/runtime-refactor/arch/P7a-交接包与挂账清单.md`（A-P7a-37）「**不许静默**——若任何相位仍发生截断，模型面必须随材料段带明示……收口注记面同步披露」。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 合同常量族集合与接口清单相等（名单闭世界） | `tests/domains/test_v2_prompts.py::contract_constant_family_closed_world` |
| 答案要求清单 7 条逐字在场、顺序固定、以「；」分隔 | `tests/domains/test_v2_prompts.py::answer_requirements_verbatim_seven` |
| 合同文本全仓唯一定义点（消费方零字面副本） | `tests/domains/test_v2_prompts.py::answer_requirements_single_source` |
| 任务书段序固定、题干段置末紧邻生成点 | `tests/domains/test_v2_prompts.py::task_book_segment_order` |
| 任务书样例区＝固定三则、不随 state 变化、无边界对照例 | `tests/domains/test_v2_prompts.py::task_book_examples_fixed_set` |
| 数据区活体投影现取：改投影 → 输出随之变 | `tests/domains/test_v2_prompts.py::data_zone_live_projection` |
| 空投影 → 占位文案逐字在场（族／指标／术语／对象／关系／水位） | `tests/domains/test_v2_prompts.py::empty_projection_placeholder_verbatim` |
| 题意锚行两形（理解真值/假值）且置于决策轮指令首行 | `tests/domains/test_v2_prompts.py::anchor_line_two_forms_first_line` |
| 决策轮首入包四件齐（四要素逐轮在场）、常驻块包裹对恰一对 | `tests/domains/test_v2_prompts.py::decision_package_four_elements` |
| 台账常驻块逐字转抄、恰一份；三删段名字面缺席 | `tests/domains/test_v2_prompts.py::ledger_resident_block_verbatim_once` |
| 消歧头统一措辞逐字在场 | `tests/domains/test_v2_prompts.py::disambiguation_header_uniform` |
| 分解样例三分支（未绑定→knowledge／可出数→data／空→空串） | `tests/domains/test_v2_prompts.py::decompose_example_three_branches` |
| 分解样例产出为合法 JSON 形（可解析） | `tests/domains/test_v2_prompts.py::decompose_example_valid_json` |
| 合同常量零业务名词（fixture 词集与水位日形交集＝∅） | `tests/domains/test_v2_prompts.py::contract_constants_business_noun_free` |
| 答案轮段序固定（三件套→汇总合同→子问题清单→起草合同）；材料段零渗入 | `tests/domains/test_v2_prompts.py::answer_round_segment_order_no_material` |
| 答案轮禁令件在场（动词钉死句＋答案要求⑦；pin-13 合同侧） | `tests/domains/test_v2_prompts.py::answer_round_ban_lines_present` |
| 装配确定性纯函数：两跑逐字相等、不改入参、零 IO／模型／时钟（AST） | `tests/domains/test_v2_prompts.py::assembly_pure_deterministic` |
| import 面只许 state（AST 扫描——R3 半覆盖面的降维补位） | `tests/domains/test_v2_prompts.py::imports_state_only` |
| 程序侧无词表／正则语义判断（AST；豁免面＝集合成员判定与逐字子串校） | `tests/domains/test_v2_prompts.py::no_lexicon_or_regex_in_prompts` |
| 【边界集】空台账／缺水位／零未绑定指标（全可出数）／子问题清单超长 → 各落占位文案／空串段／data 链形分支 | `tests/domains/test_v2_prompts.py::boundary_empty_projection_variants` |
| 【保留集】常规投影装配输出不受空投影分支影响；四消费方既有验收断言不因本块改形回归 | `tests/domains/test_v2_prompts.py::retention_normal_assembly_unchanged` |

> **测试文件归属**：本块验收测试绑**新建** `tests/domains/test_v2_prompts.py`（`prompts` 是阶段 2 新划的公共层块，与同层 `state` 规格同款归属；现状旧码装配测试在 `tests/domains/test_v2_v262_turn_selfsufficiency.py` 等，本批不改）。全部测试标识＝**待织网（阶段 5）**。

## 依赖与风险

- 依赖：`state`（唯一模块依赖——R3；只读投影）；消费方＝四业务相位（经 R2 包根）；真源＝`specs/modules.md` `## prompts` 卡。
- 风险与对策（每条带检测手段）：
  1. **卡与规格分叉（族成员展开）**：卡面公开接口只列两函数＋「合同常量＋各轮装配函数」注释，本规格把族成员展开成名单——有「卡缺公开成员」前科（`docs/runtime-refactor/spec-review/state-评审.md` S-2 同款）。对策：评审期裁定——或回阶段 2 把族成员补进 `## prompts` 卡，或裁「族成员＝卡面注释的展开、非新公开类型」；两处口径不得并存。检测手段＝**人审**（评审工序）。
  2. **合同文本多处复制复发**（V1 病灶：同一答案规则三处字面并维护，真源 `docs/runtime-refactor/recon/L2b-作答装配与回声.md` D-L2b-01）。对策：单点断言＋消费方只引用。检测手段＝`::answer_requirements_single_source`。
  3. **台账常驻块交界两说**：`specs/clarification.md` 触及面把「台账注入块」记在 prompts、`specs/modules.md` `## context` 卡有「术语表常驻注入」。本规格定界＝**固定包裹文本＋逐字转抄渲染归本块；投影取得归 context（经 tools 公开面）；Manifest 记账与不入史归 context/state 面**。检测手段＝**人审**（阶段 7 接口契约对账）＋`::ledger_resident_block_verbatim_once`。
  4. **装配滑成判断**（把三选一/放行拒答等语义结论写进装配）。对策：确定性纯函数断言＋AST 机检。检测手段＝`::assembly_pure_deterministic`／`::no_lexicon_or_regex_in_prompts`。
  5. **R3 半覆盖**（「只许依赖 state」对公共层其余块的面无闸）。对策：AST import 扫描测试补位。检测手段＝`::imports_state_only`＋人审（边界闸覆盖面声明，见挂钩表）。
  6. **样例渲染器产出非法 JSON**（V1 病灶 D-L2a-13：字符串拼接无转义）。对策：合法 JSON 形断言。检测手段＝`::decompose_example_valid_json`。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 只 import state（禁引七业务相位半面） | 边界闸 **R3** | 已真跑（`tools/importlinter_v2.toml` R3 契约） |
| 只 import state（禁引公共层其余块半面） | 测试 `::imports_state_only` ＋ **人审** | 待实现（阶段 5）；人审原因：R3 的 forbidden 只列七业务相位，公共层半面无闸、AST 补位是测试非闸 |
| 消费方只经包根（深层子模块私有） | 边界闸 **R2**（业务相位禁引公共层块深层子模块，`forbidden` 含 `appv2.runtimev2.prompts.*`） | 已真跑 |
| 不引框架 | 边界闸 **R5b** | 已真跑 |
| 不引引擎 | 边界闸 **R6** | 已真跑 |
| 不直引 `appv2.infra.llm_client` | 边界闸 **R7** | 已真跑 |
| 零模型调用（连 `gateway_adapter` 都不 import） | 测试 `::assembly_pure_deterministic`（AST 零模型面） | 待实现（阶段 5）；R1–R8 无「禁引 gateway_adapter 于 prompts」专属闸（R8 只列零 LLM 三相位） |
| 合同常量零业务名词（「合同零业务名词」命名闸的结构面） | 测试 `::contract_constants_business_noun_free` | 待实现（阶段 5） |
| 答案要求清单 7 条单点、逐字在场（`specs/answering.md` 行为 10 的唯一真源指向闭环） | 测试 `::answer_requirements_verbatim_seven`／`::answer_requirements_single_source` ＋ **人审**（阶段 7 接口契约对账——`specs/answering.md` 风险 4 同款） | 待实现（阶段 5） |
| 答案要求③多来源分源（跨油田题分源列明的合同侧承接；`specs/verification.md` 挂钩表登记「prompts 规格落盘后承接」） | 钉 **`pin-03`**（P0）——本块落点＝合同侧③逐字在场（行为 2）；交付行为面归 `specs/answering.md`（其挂钩表承接） | 待织网（阶段 5） |
| 起草回声＝0 的**提示词侧**（不注入回声形指令：动词钉死句＋答案要求⑦在场） | 钉 **`pin-13`**（P1）——**分工**：本块落点＝合同侧禁令件在场（行为 13、测试 `::answer_round_ban_lines_present`）；观测面（`echo_flag` 恒 0）落 `specs/answering.md` 行为 14（已定稿） | 待织网（阶段 5） |
| 相位合同一次性（回炉轮不重发） | 钉 **`pin-24`**（P1）——**行为不归本块**：追加记账归 `specs/state.md` 行为 5（已定稿，测试 `contracts_appended_idempotent`）；消费侧重发判定待 `context`／`orchestration` 规格；本块只承诺合同常量逐字稳定（常量无逐轮变体，行为 1） | 待织网（阶段 5）——记账面已在 state 侧落，消费侧待 context/orchestration |
| 投影缺位不静默（占位文案／空串段两形机读信号在场） | 测试 `::empty_projection_placeholder_verbatim` | 待实现（阶段 5） |
| 真源引用可解析（本规格全部引用行） | 真源引用可解析闸（`tools/ref_resolvable.py` 的 check 子命令） | 交稿前本地实跑 |
| 「不做什么」的纯范围排除（不解析／不调模型／不渲染材料等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（只引 state、零模型、零 IO）已由 R3/R7＋AST 测试覆盖 |
