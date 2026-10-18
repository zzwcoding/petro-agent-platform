# V2 指令与提示词（prompts）

状态: 已定稿
来源: `specs/modules.md` `## prompts` 卡、`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §三 B、`docs/runtime-refactor/walk/08-澄清-意图澄清.md`、`docs/runtime-refactor/walk/09-澄清-分解问题.md`、`docs/runtime-refactor/walk/14-作答-汇总作答.md`、`docs/runtime-refactor/walk/裁决表.md`（§04／§06／§14＋项目级裁决 #12/#13）、`docs/runtime-refactor/recon/L2a-装配前半.md`、`docs/runtime-refactor/recon/L2b-作答装配与回声.md`、`docs/runtime-refactor/recon/E1-澄清节点.md`（R-E1-05/06/07/08/10）、`docs/runtime-refactor/recon/E2-工具匹配节点.md`、`docs/runtime-refactor/recon/I2b-RunState全字段.md`、`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`（V2-58／59／62）、`docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md`（A-P6b-25／A-P6b-24/34 迁移文本不变）、`docs/runtime-refactor/arch/P6a-票堆V2-80系列前半.md`（A-P6a-33/35）、`docs/runtime-refactor/proposals/M1-理解模块修订提案.md`（:160 SYSTEM_PROMPT 归属）、`docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-03／pin-13／pin-24）、`docs/runtime-refactor/research/最佳实践-3a-白话化与受众适配.md`（EB4a 白话化条款依据——第三节 3.1 术语表注入＋合并式条款＋配示例）
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
| 系统层提示词 `SYSTEM_PROMPT` 全文本（V2-80d A-P6a-33，全调用可见） | 不归本块六族——真源记「属 H9/H6 落点」，确切落块待阶段 2 对账（登记见风险 7⑥）；其内 V1 答案规则句残留副本随落块块规格销项，不在本块单点断言扫描范围 | `docs/runtime-refactor/proposals/M1-理解模块修订提案.md` :160 |
| 环节规章的**承载位**（system 位／链面） | **本块**：规章取件函数四件＋族⑦背景块（2026-10-17 H 批·角色分家）；**挂点**＝`bookkeeping.call_model` 的 `system` 注入参（前置进本次请求）与编排建链面（链首背景块恰一条）——本块只出文本、不发起调用、不写链 | `docs/runtime-refactor/proposals/H批-开票-system承载位.md` §3／§4；`specs/bookkeeping.md` 行为 15 |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| prompts | 新增 | 本块本体：合同常量族＋各轮装配函数族（纯文本进出） |
| state | 已定稿 | 唯一模块依赖（R3）；只消费其数据形状与投影字段，零写入 |

## 接口定义

```python
# ── 合同常量族（名单闭世界，六族；文本单点在本块，消费方只引用不复制）──
# ① 任务书静态骨架四常量（场景／任务／样例／红线）
# ② 澄清发射合同——含相位合同头行＋finalize 交付面边界句
#                                     #（真源 recon/E1 R-E1-05/06/07；消费方 clarification）
# ③ 工具匹配发射合同——含相位合同头行＋合同内嵌定案样例
#                                     #（真源 recon/E2 R-E2-04、arch/P4b A-P4b-60；消费方 tool_matching）
#                                     #（**2026-10-16 补（L0/L2 三病灶修复批①）：合同正文（matches 形 ＋
#                                     #  字段说明）与填写样例同批带**必填**结论字段 `mention_mode`
#                                     #  （闭世界 `executed`／`mentioned_only`）——真源
#                                     #  `specs/tool_matching.md`（`SubtaskMatch.mention_mode` 条
#                                     #  ＋行为 5 枚举条，行号 :56／:75）；原合同零提及该字段而
#                                     #  闸为必填＝提示资产缺失致工具匹配必拒循环（L2 实证 35 轮）**）
# ④ 汇总合同                          # 答案轮中段
# ⑤b 作答第二出口合同（**2026-10-18 V2-96 D5 新增**——成员 `ANSWER_EXPLORE_CONTRACT`，
#   入族⑤ `answer_draft`）：两出口（正常作答／`explore` 检索意图）＋1 示例＋预算行
#   （再探 ≤2 次、每轮 ≤2 请求）；**正向条款、不堆条款**。真源＝
#   `docs/runtime-refactor/接手-召回全链路最终决议与运行流程-20261018.md` §五·5.1；
#   注入点＝`answer_system_contract()`（system 规章段，插在汇总合同与起草答案合同之间）。
# ⑤c 材料期约束合同（**2026-10-18 V2-123 新增**——成员 `ANSWER_PERIOD_CONTRACT`，入族⑤
#   `answer_draft`）：材料报表期晚于执行日时只能作「该期资料」如实引用、不得据此断言执行日
#   时点的状态或「当前」情况（逐字稿＝`tickets/v2/V2-123-材料期与执行日标注.md` §逐字稿）；
#   注入点＝`answer_system_contract()`（system 规章段，插在族⑤b 第二出口合同与族⑤起草答案
#   合同**之前**——末段仍＝起草答案合同收尾）。
# ⑤d 作答前三步合同（**2026-10-18 V2-120 新增**——成员 `ANSWER_THREE_STEP_CONTRACT`，入族⑤
#   `answer_draft`）：先核（对照子问题覆盖表逐子问题判有支撑／无支撑）→再决（任一无支撑先
#   explore 或如实说明未覆盖；全有支撑直接起草）→后写（输出答案正文）；把 `explore` 从附带
#   第二出口升为**第二步的先决动作**（逐字稿＝`tickets/v2/V2-120-作答合同三段式.md` §逐字稿）；
#   注入点＝`answer_system_contract()`（system 规章段**第 0 段**——先于动词钉死句）；「子问题
#   覆盖表」指代 V2-119 的 user 动态段段头（`ANSWER_COVERAGE_HEAD` 逐字「子问题覆盖表：」）
#   ——**硬依赖 V2-119 先落**（反序＝合同指代悬空）。
# ⑤ 起草答案合同——构成（去重后形态，拼接序照现状）＝**缺位话术句**（段首第 1 句；
#   **2026-10-18 V2-101 逐字置换**——A-P6a-35 追加半句「（材料未覆盖所问时：只简短说明未
#   找到与所缺，不逐源铺陈无关材料）。」按票面 §逐字稿置换为「缺位只锚本轮材料：写「本次
#   材料未覆盖」，不得写「报告/资料库未载」或「没有任何一条材料提及」。」——只锚本轮材料、
#   禁库级否定升格；段内其余字面零改；真源＝`tickets/v2/V2-101-缺位话术收紧.md` §逐字稿；
#   边界＝范围限定与计数如实归 V2-122，同改本常量三票 101→121→124 串行且后票只许追加）
#   ＋行集交付规矩段（arch/P4b A-P4b-49 票面附 C 本段不得增删字）＋台账卡边界句；
#   与 V1 的差异＝删句首重复句群（其 V1 字面句首的答案规则句群＝
#   D-L2b-01 病灶副本，由族⑥单点承接去重——已裁（流水 43①，Owner 可否决）：
#   句首 V1 字面答案规则句群去重、由族⑥单点承接；见风险 2）
# ⑥ 答案要求清单（10 条——迁移照抄逐字稿见「行为约定」2；2026-10-17 EB2 D2 追加第八条；
#                  2026-10-17 EB4a 追加第九／第十条〔白话化条款〕）
#   ＋示例区常量 JARGON_PLAIN_GLOSSARY（术语白话表——静态块，注入点＝答案装配包
#     `answer_round.py`；文本单点＝`constants.py`，消费方只引不复制）
# ⑦ 系统背景块（**2026-10-17 H 批新增**——唯一新文本；逐字稿＝H 批开票 §5）：
#   `SYSTEM_BACKGROUND`——链首 system 条恰一条（每链一次，挂编排建链面：题面 user 条之前）；
#   文本单点＝`constants.py`，消费方只引不复制
# ── 装配函数族（卡面两函数逐字照录；纯文本进出＝Seam；逐成员真源可溯）──────────────
def assemble_task_book(state: RunState) -> str: ...
def assemble_answer_prompt(state: RunState) -> str: ...
#                                     #  **2026-10-18 V2-119 additive 关键字参**：
#                                     #  `assemble_answer_prompt(state, *, coverage=None)`——程序算出的
#                                     #  「子问题 id → 有支撑／零支撑」表（判据面＝`answering.subtask_coverage`，
#                                     #  零语义三 kind 分层形态判据）；零支撑者逐条出提示行
#                                     #  （`ANSWER_COVERAGE_LINE`——逐字稿＝V2-119 票面 §施工基准），
#                                     #  落**动态段**「子问题结果清单」之后、材料段之前（Kimi 评审修正 3
#                                     #  ——与 V2-120「第一步·先核」逐字对齐）；全有支撑／缺省＝零追加
#                                     #  （材料充分题零提示——零误报）。段头 `ANSWER_COVERAGE_HEAD`
#                                     #  ＝「子问题覆盖表：」（段名逐字＝V2-120 逐字稿）。
#                                     #  **两件落装配模块（非合同常量族）**——①族单源判据要求成员
#                                     #  首行 ≥12 字（段头 7 字不可入族）；②pin-24 要求合同常量无槽
#                                     #  （提示行携 `{id}` 槽）；先例＝`_QUESTION_ANCHOR`（携槽）／
#                                     #  `_SUBTASK_LIST_HEAD`（段头）。单点命名面＝`ANSWER_COVERAGE_*`
#                                     #  （Kimi 评审修正 1——禁 `COVERAGE_LINE` 与
#                                     #  `ANSWER_COVERAGE_HEAD/LINE` 两套）。
#                                     #  机读面＝`tests/domains/test_v2_v119_subtask_coverage.py`
# 族内其余成员（卡面「各轮装配函数」的展开，名单闭世界）：
#   题意锚行装配件 anchor_line(question, understanding) -> str
#                                     # 真源 recon/L2b R-L2b-10/11/12＋arch/P4b A-P4b-59
#   决策轮首入包装配（澄清轮／工具匹配轮——构成逐件见行为 7；含 §A 指南段装配
#                                     #〔文本经入参注入，装载面不归本块——真源 R-E1-05/R-E2-04/R-E2-14〕
#                                     #＋问题组 JSON 渲染〔投影原形直转 JSON——顶层 subtasks 单键形，真源 R-E2-04／V1 字面 graph.py L2706-2708〕
#                                     #＋`shared_context` 开关〔2026-10-17 补·真机消重批：§A 段与常驻块整段出／入
#                                     #  ——缺省 True＝本块行为 7 构成；判定／下传归 orchestration，同 run 只注一次〕）
#   台账常驻块渲染（BEGIN＋字典说明行＋台账/别名/结构卡三块＋END——行为 8）
#   分解发射样例渲染器（运行时现造、不进合同常量——行为约定 10）
#   决策轮增量条装配（澄清轮：探查预算条／回炉条／用户补充条／拒因回喂条；工具匹配轮：拒因回喂条
#                                     #——逐字稿见行为 16，真源 recon/E1 R-E1-08①②③④＋arch/P4b A-P4b-13；
#                                     #已做段文本由调用方传入，渲染归 context）
#   ── **规章取件函数族（2026-10-17 H 批·角色分家·system 承载位）**——各环节规章段（文本全部引
#      既有常量、零新写）；**不入链**，经 `bookkeeping.call_model(system=…)` 前置进**本次请求**：
#   understand_system_contract() -> str   # 读题规章段＝指令区（场景/任务/样例/红线）＋输出契约区
#   clarify_system_contract(max_subtasks) -> str
#                                     # 澄清规章段＝相位①头行＋族②合同正文＋finalize 交付面边界句
#   toolmatch_system_contract() -> str    # 匹配规章段＝相位②头行＋族③合同正文
#   answer_system_contract() -> str       # 作答规章段＝族⑤d 作答前三步合同（第 0 段）
#                                     #  ＋动词钉死句＋【答案要求】＋族⑥清单全文
#                                     #  ＋术语白话表＋族④汇总合同＋族⑤b 第二出口合同
#                                     #  ＋族⑤c 材料期约束合同＋族⑤起草答案合同（收尾）
#   **承载位分工**（真源 H 批开票 §3 方案 C）：**system＝规章、user＝动态段**（材料／题面／锚行／
#   增量条／数据区／子问题清单）；链本体仍只 user／assistant（＋链首背景块 system 恰一条）。
```

- **合同常量族名单是闭世界**：上列六族之外新增合同文本＝只许以「新增常量入族＋同批改本清单」方式进块；消费方私设第二合同源（合同字面复制进相位块）＝判失败。**2026-10-18 V2-96 D5**：族⑤ `answer_draft` 加成员 `ANSWER_EXPLORE_CONTRACT`（作答第二出口合同＋1 示例＋再探预算行；真源 §五·5.1）——族集合与成员名单同批改本清单，机读面＝`tests/domains/test_v2_prompts.py::contract_constant_family_closed_world`。**2026-10-18 V2-123**：族⑤ `answer_draft` 再加成员 `ANSWER_PERIOD_CONTRACT`（材料期约束合同——报表期晚于执行日只能作「该期资料」引用；逐字稿＝V2-123 票面 §逐字稿；随作答规章段 `answer_system_contract` 在场、插在末段之前）——族集合与成员名单同批改本清单，机读面＝`tests/domains/test_v2_prompts.py::contract_constant_family_closed_world` ＋ `tests/domains/test_v2_v123_material_period.py::test_answer_period_contract_verbatim_and_family`。**2026-10-17 H 批**：族名单加**第七族** `system_background`（成员＝`SYSTEM_BACKGROUND`，逐字稿＝H 批开票 §5）——「六族」口径随之读作「合同常量族（含 H 批新增背景族）」；机读面＝`tests/domains/test_v2_prompts.py::system_background_verbatim`（族⑦成员逐字＋单源）。**2026-10-18 V2-120**：族⑤ `answer_draft` 再加成员 `ANSWER_THREE_STEP_CONTRACT`（作答前三步合同——先核→再决→后写；逐字稿＝V2-120 票面 §逐字稿；随作答规章段 `answer_system_contract` 在场、置**第 0 段**先于动词钉死句）——族集合与成员名单同批改本清单，机读面＝`tests/domains/test_v2_prompts.py::contract_constant_family_closed_world` ＋ `tests/domains/test_v2_v120_three_step.py::test_answer_three_step_contract_verbatim_and_family`。
- **装配函数族名单是闭世界**：族成员即上列成员；增删成员须同批对账四消费方规格（`specs/understanding.md`／`specs/clarification.md`／`specs/tool_matching.md`／`specs/answering.md`）的触及面。常量实名与函数签名阶段 5 施工时按卡定（本规格锁的是**名单闭世界**与**纯文本进出**）。**2026-10-17 H 批**：族名单加**规章取件函数四件**（`understand_system_contract`／`clarify_system_contract`／`toolmatch_system_contract`／`answer_system_contract`）——同批已对账四消费方规格（各加 H 批注记）＋`specs/bookkeeping.md`（`call_model` 的 `system` 注入参）。
- **错误契约（纯文本进出）**：装配函数输出恒为 `str`——**不抛业务错、不返回 `None`**；投影缺位走**占位文案**（逐字见行为约定 5）或**空串段**（空串＝「该段缺位」的机读信号，调用方跳过，真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-32「台账空投影返回空串（调用方跳过）」）。
- **入参纪律**：装配函数消费 state 投影字段（字段面以 `docs/runtime-refactor/synth/S5-RunState字段矩阵.md` 为界，只读）＋调用方传入的文本（如过程段渲染产物、时间量）；**时间量只经入参注入**，本块不读时钟（时间一律 `infra.clock` 的 B14 纪律在装配面的形态＝零时钟接触，时钟值由调用方注入）。
- 真源：`specs/modules.md` `## prompts` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本块不引入任何框架；纯字符串装配零依赖）。验收写法：依赖锁文件不出现框架包＋行为测试绿。对应闸：**R5b 契约**（`tools/importlinter_v2.toml`）。
- **只许 import `state`（纯文本块）**：本块不感知运行状态机、不引任何其他 runtimev2 块。对应闸：**R3 契约**——**诚实声明覆盖面**：R3 的 forbidden 只列七个业务相位，**「禁引公共层其余块」（bookkeeping／context／transport／persistence／gateway_adapter／orchestration／gate）这半面无闸**；降维＝AST import 扫描测试（`::imports_state_only`），余面人审（见挂钩表）。
- **消费方向（R2）**：四个业务相位只许经包根 `appv2.runtimev2.prompts` 消费本块（深层子模块私有）。对应闸：**R2 契约**。
- **不引引擎**（knowledge/query/retrieval）、**不直引 `appv2.infra.llm_client`**。对应闸：**R6 契约**／**R7 契约**；本块连 `gateway_adapter` 都不 import（零模型块）——该面由 `::no_model_call_in_prompts`（AST）承载，R1–R8 无此专属闸。
- **禁手写替代**：合同文本单点在本块，禁在相位块/编排块另存一份合同字面（V1 病灶：同一答案规则三处字面并维护，真源 `docs/runtime-refactor/recon/L2b-作答装配与回声.md` D-L2b-01）。验收写法：runtimev2 面内唯一定义点断言（`::answer_requirements_single_source`）。

## 行为约定

1. **合同常量名单闭世界＋文本单点**：全仓合同文本定义点唯一（六族清单见接口定义；单点范围＝runtimev2 面——系统层 `SYSTEM_PROMPT` 的 V1 答案规则句残留副本不归本块销项，见「不做什么」与风险 7⑥）；消费方（四相位）只经包根引用常量，**任何相位块/编排块内不出现合同字面副本**。断言：答案要求清单文本在 runtimev2 面内恰一处定义；合同常量族集合与接口清单相等（集合比较）；六族各取首句特征子串在四相位块／编排块源码零命中（`::contract_constants_no_duplicate_literals`）。**2026-10-17 H 批注（角色分家·system 承载位）**：族名单加第七族 `system_background`；各环节**规章段**（读题合同／相位①②合同／答案要求等）改走**调用级 system 注入参**（`bookkeeping.call_model(system=…)`）——**文本零改、只换承载位**（真源 `docs/runtime-refactor/proposals/H批-开票-system承载位.md` §3 方案 C＋§4；机读面＝`::system_background_verbatim`／`::system_contract_carriers_split_from_user_dynamic`）。
2. **答案要求清单＝10 条逐字在场、顺序固定**（条数真源＝`docs/runtime-refactor/recon/L2b-作答装配与回声.md` R-L2b-02，现 10 条——**2026-10-17 EB2 D2 追加第八条；2026-10-17 EB4a 追加第九／第十条**；`specs/answering.md` 行为 10 以本合同为唯一真源、不复述）。十（前八）条为**迁移照抄**——逐字稿＝现行代码字面 `appv2/runtimev2/prompts/constants.py` `ANSWER_REQUIREMENTS`（V1 承载位 `appv2/runtime/orientation.py` `_ANSWER_REQUIREMENTS` L282-290 为①–⑦原稿，V2-64 拓宽形终稿；承载位换、文本不变——真源 `docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md` A-P6b-24「文本常量与渲染函数零变化、只换承载位」＋A-P6b-34 锁定逐字稿纪律；`R-L2b-02` 与票面摘录均为要点形摘要，不作逐字稿；**EB2 D2 追加条**＝方案 `docs/runtime-refactor/proposals/EB2-答案面瘦身与友好化.md` D2 引文逐字；**EB4a 追加两条**＝票面引文逐字，依据＝`docs/runtime-refactor/research/最佳实践-3a-白话化与受众适配.md` 第三节 3.1（术语表注入＋合并式条款＋配示例——防「指令诅咒」，故只增两条；第十条＝Owner 2026-10-17 裁决「召回问题的提示词侧缓解」））。十条内容：①逐条事实断言带 [n] 引标（n＝观察材料序号）；②材料未覆盖的部分不得断言、如实说明未覆盖；③材料含多个来源（不同报告／油田／井）时逐个来源分别作答（不冲突也要分别列出，不以反问代替作答）；④作答后仍有未覆盖的来源或指代不明处，如实点名未覆盖来源（含检索窗注记的未进窗来源）并请用户补充检索或指明对象，不静默略过；⑤引擎的降级/未绑定/拦停注记必须如实转述进对应子问题条目（不得静默丢弃）；⑥引用观察材料请摘录必要短语并带引标，禁整段照搬原文充当回答；⑦「理解：／指标候选：」及任何动作 JSON 是过程产物，出现在答案中即废品；⑧核验元数据（血缘卡五要素、来源表、数据批次）不写进答案正文——它们在界面『引用与口径』侧栏逐字展示；答案只在用户需要时带一句口径（如单位）；⑨面向油田业务用户作答：系统内部词首次出现时紧跟一句括号里的白话解释——如『口径（这个数是按什么规则算的）』『台账（平台里登记指标和术语的名册）』；同一词后文可直接使用。不要把内部说法整句甩给用户（『召回 51 支/送窗 12 支』应写成『检索到 51 条材料，其中 12 条用进了答案』）；⑩材料未覆盖所问时：先从已给材料中答出可能与问题相关的内容，再给用户一句更容易查到结果的提问建议（如补充井号、时间范围或报告名称）。**条间分隔与条内标点两事**（2026-10-17 EB2 D2；EB4a 同体例）：①–⑦文本零改，⑦尾「。」改「；」＝条间分隔符；⑧内文自带一「；」（逐字，不作分隔符）；**EB4a**：⑧尾「。」改「；」、⑨尾「。」改「；」＝条间分隔符（＝每条非末条尾字「；」、末条⑩尾「。」；此二字改的是分隔符位、不是条文文本），⑨内文自带一「；」（逐字，不作分隔符）。断言：十条逐字在场且顺序固定（施工以上引代码字面为逐字稿，照抄不改；偏离即停）。③的多来源分源交付面＝钉 `pin-03` 的合同侧承接（见挂钩表——本句为承接注记，不属合同文本）。**族⑥示例区＝术语白话表常量 `JARGON_PLAIN_GLOSSARY`（2026-10-17 EB4a）**：静态块文本「【术语白话表】口径＝这个数是按什么规则算的；台账＝平台里登记指标和术语的名册；水位＝数据目前更新到哪一天；窗＝统计的时间段；绑定＝登记关联；召回＝检索到的材料；送窗＝用进答案的材料。」——随答案装配包**恰一次**入链（注入点＝`appv2/runtimev2/prompts/answer_round.py` `assemble_answer_prompt`：静态文本置前、state 投影段在后；两跑／异状态逐字同源）；文本单点＝`appv2/runtimev2/prompts/constants.py`，消费方只引不复制（条款⑨的两处示例与表内同名白话一致——术语全文一致）。
3. **任务书段序固定、题干置末**：三区序唯一依据＝`specs/understanding.md` 行为 1（V2 定案）——指令区→数据区→输出契约区；题干段置末、紧邻生成点（题干非三区之一；置末、段间「\n\n」连接、题干收束句的先例＝`docs/runtime-refactor/recon/L2a-装配前半.md` R-L2a-17/R-L2a-22；understanding 行为 1 明写输出契约区「末尾」且无「题干段」表述——题干段与契约区先后随枚举缺口同批澄清，登记见风险 7①）。指令区构成＝场景／任务／样例／红线四常量（样例归位＝保持 V1 相对序「任务→样例→红线」——R-L2a-17 段序中样例在任务后、红线前；`understanding.md` 行为 1 指令区枚举未列样例＝枚举缺口，登记见风险 7①）。**与 V1 段序（R-L2a-17）的两处设计变更显式声明**：红线由「环境段之后」移入指令区（依 understanding 行为 1）；输出契约区为 V2 新增（V1 无）。断言：给定 fixture 状态，装配输出按「指令区→数据区→输出契约区→题干段」逐段可定位、题干段为末段；指令区内四常量相对序＝场景→任务→样例→红线。**2026-10-17 H 批注（承载位分家）**：本行为判据按**两段合看**——**规章段**（指令区→输出契约区）＝`understand_system_contract`（system 位、随本次请求）、**动态段**（数据区→题干段）＝`assemble_task_book`（user 条入链）；**段内相对序零改**（四常量相对序、题干置末皆不变），合看的可见序＝规章段（前置）→动态段；机读面＝`tests/domains/test_v2_prompts.py::task_book_segment_order`。**2026-10-18 V2-87 注（输出形统一·单 JSON）**：指令区四常量中的 `TASK_BOOK_TASK`／`TASK_BOOK_EXAMPLES`／`TASK_BOOK_REDLINE` 三段改**单 JSON 形**（「输出固定两行／第一行理解／第二行指标候选」措辞与三则样例的两行式输出退役），`TASK_BOOK_OUTPUT_CONTRACT` 模板补 `subjects`／`terms` 两键（消费面已读、契约必须列——代码审计 M8；真机证据 EB7 `数-降2` `run-4e524762`：两行式与单 JSON 契约并存致两次读题不合 JSON、收敛拒答）；**段序判据零改**（四常量相对序＝场景→任务→样例→红线、题干置末皆不变）；机读面＝`tests/domains/test_v2_prompts.py::task_book_output_form_single_json`。**题干收束句随 V2-87 统一为 JSON 两出口**（原「可能有关＝两行式；确定无关的寒暄闲聊＝直答」退役——模型可见面零两行式残留；机读面＝`tests/domains/test_v2_prompts.py::question_segment_single_json_tail`／`tests/domains/test_v2_understanding.py::test_route_defaults_fail_closed`）。
4. **任务书样例区＝固定示例集**（多部分题／口语映射题／判断纠错题三则；真源 `docs/runtime-refactor/walk/04-理解-读题步.md` §一「三则样例」＋`docs/runtime-refactor/walk/裁决表.md` §04-C；`specs/understanding.md` 行为 10 同源）；**不加边界对照例**。断言：三则逐字在场、装配输出中样例区文本不随 state 变化（常量直引）。**2026-10-18 V2-87 注（输出形统一·单 JSON）**：三则样例的 `输出：` 行由两行式改**单 JSON 对象**（`route`＋`text`＋`metric_candidates`＋`subjects`＋`terms` 五键；样例取舍要点逐字保留）；**三则固定集判据零改**（不增样例四、不加边界对照例）；机读面＝`tests/domains/test_v2_prompts.py::task_book_examples_json_parseable`（三则 `输出：` 行各自 `json.loads` 合法、键集含四键）。
5. **数据区从活体投影现取且空投影走占位文案**：改 fixture 投影 → 输出文本随之变（来源标记面以 `specs/understanding.md` 行为 2 为准）；空投影走**逐字占位文案**——族「（暂无族标注）」、指标／术语／对象「（空）」、关系「关系：（空）」、水位「（水位未取得）」（逐字稿真源 `docs/runtime-refactor/recon/L2a-装配前半.md` R-L2a-19）。断言：空投影 fixture → 占位文案逐字在场；投影增删一行 → 输出同步增删。**2026-10-18 V2-87 注（输出形统一·单 JSON）**：本行为判据零改——任务书指令区输出形统一（单 JSON＋模板补两键）只改指令区文字，数据区活体投影现取与空投影占位文案两形皆不动；机读面＝`tests/domains/test_v2_prompts.py::data_zone_live_projection`／`::empty_projection_placeholder_verbatim`（另见 `::task_book_output_form_single_json`）。
6. **题意锚行两形、置于决策轮指令最前**：`anchor_line(question, understanding)`——理解真值 → 单行「用户原题：{question}｜题意：{understanding}」（前缀固定「用户原题：」、全角冒号、全角「｜」直连）；理解假值 → 单段「用户原题：{question}」（**不输出空「题意：」段**）；插澄清轮／工具匹配轮指令最前（真源 `docs/runtime-refactor/recon/L2b-作答装配与回声.md` R-L2b-10/11/12＋`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-59）。断言：两形分支逐字＋锚行在装配输出的首行位。
7. **决策轮首入包构成固定、逐件可溯**（相位一次性——真源 `docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md` A-P6b-25）：澄清轮／工具匹配轮的首入装配＝①题意锚行（行为 6）＋②相位合同（合同头行＋合同正文；澄清轮另含 finalize 交付面边界句——构成真源 `docs/runtime-refactor/recon/E1-澄清节点.md` R-E1-05/06/07，字面随 A-P6b-24 迁移照抄）＋③（澄清轮）分解发射样例（行为 10）／（工具匹配轮）样例在合同内嵌（`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-60）＋④§A 指南段（文本经入参注入——装载面 GuideProvider 实现不归本块，归属登记见风险 7⑦；措辞分工真源 `docs/runtime-refactor/recon/E2-工具匹配节点.md` R-E2-14「动作类措辞以合同为准、§A 仅作业务规则参考」）＋⑤（工具匹配轮）问题组 JSON 渲染（投影原形直转 JSON——顶层 `subtasks` 单键形，真源 R-E2-04／V1 字面 `appv2/runtime/graph.py` L2706-2708）＋⑥（投影非空时）台账常驻块包裹——常驻块形＝BEGIN＋字典说明行＋台账／别名／结构卡三块＋END（构造先例真源 `docs/runtime-refactor/recon/E2-工具匹配节点.md` 相位包首入段）。断言：给定 fixture 状态，首入包按上列构成逐件在场（澄清／匹配轮各按其件）、常驻块包裹对恰一对；**四要素按轮合看逐轮在场**（`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-56「四要素制度…每条发模型的轮次四件齐」口径：任务动词＝合同头、题意锚＝锚行、产出样例＝澄清轮分解样例／匹配轮合同内嵌样例、失败反馈＝增量条拒因回喂——行为 16）。**共享上下文 run 级一次（2026-10-17 补·真机消重批·缺陷一）**：④§A 指南段与⑥台账常驻块合称**run 级共享上下文**——同一 run 的决策链里**共出现一次**，挂第一次决策装配（澄清轮首入包），后续决策调用（匹配轮首入包／回炉轮）不再重复注入（链为追加形 pin-22：前链恒为后链前缀，模型从链首可见前文，语义零损失；重复的两份＝纯重复 token——真机 `docs/runtime-refactor/ladder/L3/07` run-919ed881：末轮 answer prompt 19359 tokens 里 §A 全文与台账全量块各两遍）；两段文本**字节级不变**（只改出现次数）；**注入与否的判定与下传归 `orchestration`**（按 `state.contracts_appended` 的澄清相位标记判「本 run 是否已注」后经 `shared_context` 下传），本块只按标志拼／不拼文本。缺省 `shared_context=True`＝装配函数本体的行为 7 构成（本段为下传面口径，不改本块零判断纪律——行为 15）。断言：同 run 两次决策装配合看，§A 文本与台账常驻块各恰一次（新增测试见验收表）。**2026-10-17 H 批注（承载位分家）**：本行为的构成件**二②（相位合同：头行＋正文＋finalize 边界句）改走 `clarify_system_contract`／`toolmatch_system_contract` 的调用级 system 注入参**（不入链、随本次请求、回炉轮亦在场）；**①题意锚行／③产出样例／④§A 指南段／⑤问题组 JSON／⑥台账常驻块仍留 user 动态段**（`assemble_decision_package`，相位一次性 `pin-24` 不变）。**共享上下文（④＋⑥）留链的判据**：run 级一次性的语义前提＝「链为追加形、模型从链首可见前文」（2026-10-17 消重批）——移出链即断该前提（后续决策调用看不见这两段），故两段**不随规章改走 system**（与 H 批开票 §4② 的取件清单有意不同，理由见 `appv2/runtimev2/prompts/decision_round.py` 模块头）。
8. **台账常驻块逐字转抄、恰一份、三删不回流**：常驻块内台词条目**逐字转抄**自 state 投影（不改写、不摘要——`ledger_notes` **槽位段**逐字可求得的前提：对账口径＝段一逐字 ∈ 台账名录（指标/对象/关系/术语名）∪「无台账命中」（无台账行的报告内容题——自造名不算），非整块逐字子串，`specs/clarification.md` 行为 8 的承接面）；台账/名录信息在决策轮装配输出中**恰出现一次**（只经常驻块一份，装配不另拼名录段——V2-59 三删纪律的装配面：与相位合同逐字重复的段、名录重复份、收口硬规则旧句不回流，真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-29/30）。断言：fixture 台账每条目在输出中恰出现一次；三删段名字面在澄清轮装配输出中缺席。
9. **消歧头统一措辞**：澄清／工具匹配两轮装配的消歧头统一为「……窗词锚定/单井红线/三链路由；动作类措辞以上方合同为准」且不点名已删段（逐字稿真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-33）。断言：两轮装配输出含该逐字句；「发射判据」「指标名册」「收口硬规则」段名缺席。**落链次数注（2026-10-17 补·真机消重批）**：本行为锁的是两轮装配的**同一字面**（单点常量）；该头行与其后 §A 正文同属 run 级共享上下文，**落链次数＝run 内一次**（行为 7 注——头行随 `shared_context` 整段进出，字面零变）。
10. **分解发射样例＝运行时动态渲染、不进合同常量**：样例含台账真源词与当日日期，结构性进不了合同（「合同零业务名词」命名闸所迫，真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-32）；渲染规则：取**首条未绑定指标** → knowledge 链／doc_retrieve 形；无未绑定取首条可出数 → data 链／data_query 形；台账空投影 → 返回空串（调用方跳过）；样例窗＝「today−近 30 天 ~ today」示意（默认窗口径真源 `docs/runtime-refactor/walk/08-澄清-意图澄清.md` §七 Q-B）；payload 形＝`{"action": "decompose", "question_group": {"subtasks": [单条]}}`（两层嵌套，真源 `docs/runtime-refactor/recon/L2a-装配前半.md` R-L2a-15＋V1 字面 `appv2/runtime/orientation.py` L223-228），子问题条目五键齐全（id／question／ledger_notes／chain/tool）。**样例 `ledger_notes` 段二字面＝澄清对账闭世界值**（`已绑定`／`未绑定`——2026-10-16 微批对齐：样例教的即闸收的，真源 `specs/clarification.md` 行为 8②；旧字面「在册可出数」过不了该段对账）。**样例头行的窗词锚定说明句（2026-10-16 补（L0/L2 三病灶修复批②））**：模糊时间词（最近/近期）＝窗写 `null~null`，由引擎缺参反问兜底三选一——不要自己锚窗（拒因壳语的【期望形】同批给窗段两形示例，真源 `specs/clarification.md` 行为 8③／接口定义错误契约）。**样例头行的无台账行说明句（2026-10-16 补·流水 66）**：子问题**无台账行**（报告内容题，如「完井液密度」）＝槽位写「无台账命中」、不硬凑名（合法形真源 `specs/clarification.md` 行为 8①；真机证据 `docs/runtime-refactor/ladder/L3/01`：旧教据只教「逐字转抄台账全量块」，模型无合法形可写、三拒烧光轮次）。**无台账命中形全样例行（2026-10-17 补·分解样例补行）**：样例区**两行**——首行＝上述现造锚定指标形（三分支照旧），次行＝**无台账命中形全样例行**（逐字 `{"action": "decompose", "question_group": {"subtasks": [{"id": "s1", "question": "〈报告内容类问题〉", "ledger_notes": "无台账命中｜未绑定｜窗未定", "chain": "knowledge", "tool": "doc_retrieve"}]}}`）；且头行无台账行说明句后补半句「——三段照抄上形：无台账命中｜未绑定｜窗未定（不加解释、不改写）」；两行同属样例段（投影空／时间量缺位 → 整段空串，两行同缺）。真机证据 `docs/runtime-refactor/ladder/L3/06`（run-b5b6b056）：模型知形而凑不齐三个闭世界段——r1「无台账命中——完井液密度属于完井工程报告事实」（段尾加解释 → 段数非三）、r2「无台账命中｜无绑定｜检索式无窗」（绑定态／窗段自造形越界）→ 三轮烧光；病根＝样例区只给锚定指标形全样例行、无命中形无整行可照抄。断言：三分支各自落对；**样例区两行各自为合法 JSON** 且键形正确（顶层恰 `action`＋`question_group` 两键、`subtasks` 单条五键——V1 病灶「字符串拼接无转义产非法 JSON」不复现，真源 `docs/runtime-refactor/recon/L2a-装配前半.md` D-L2a-13）；无台账命中形全样例行逐字在场且三段位取值 ∈ 对账闭世界（`NOTE_SLOT_LITERALS`／`BINDING_STATES`／`WINDOW_LITERALS`——教的就是闸收的）；真机失败形照拒（防样例变松闸）。
11. **合同常量零业务名词**：合同常量文本不含台账真源指标名／别名／井号形／业务日期段字面（fixture 词集与水位日形扫描交集＝∅；真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-32 的命名闸记述——示例词纪律同款）。断言：合同常量族逐常量扫描交集为空（集合成员判定，属形态处理豁免面）。
12. **答案轮段序固定、材料段零渗入**：装配输出段序＝三件套置顶（行 1「用户问题：{question}」→ 行 2 动词钉死句 → 行 3「【答案要求】」内嵌答案要求清单全文）→ 术语白话表（族⑥示例区静态块，恰一份——行为 2；**2026-10-17 EB4a**）→ 汇总合同 → 子问题结果清单 → 起草答案合同（收尾）；**2026-10-18 V2-96 D5**：规章段在汇总合同与起草答案合同之间插**族⑤b 第二出口合同**（两出口＋1 示例＋预算行；末段＝起草答案合同收尾的既有判据不破）；**材料段不在装配输出内**（由调用方按 `context` 渲染产物追加于尾——材料渲染归 context）。断言：段序逐段可定位；输出末段＝起草答案合同；装配输出不含任何观察行内容子串（真源：段序 `docs/runtime-refactor/recon/L2b-作答装配与回声.md` R-L2b-04/07；三件套先例同文件 `answer_turn_preamble` 节）。**2026-10-17 H 批注（承载位分家）**：本行为判据按**两段合看**——**规章段**（动词钉死句→【答案要求】内嵌清单全文→术语白话表→汇总合同→族⑤b 第二出口合同→起草答案合同收尾）＝`answer_system_contract`（system 位、随本次请求、不入链）；**动态段**（题面件〔三件套行 1〕→子问题结果清单→**子问题覆盖表**〔2026-10-18 V2-119：零支撑子问题逐条提示行，additive `coverage` 参——全有支撑＝整段零追加〕）＝`assemble_answer_prompt`（user 条入链；材料段仍由调用方追加于尾）；段内相对序零改（白话表紧跟答案要求、起草合同收尾皆不变）。**2026-10-18 V2-120（三段式·段序）**：规章段**首件**（第 0 段）加族⑤d `ANSWER_THREE_STEP_CONTRACT`（先核→再决→后写；逐字稿＝V2-120 票面 §逐字稿）——先于动词钉死句，主指令改「先核（对照子问题覆盖表）→再决（任一无支撑先 explore／全有支撑直接起草）→后写（正文）」；承载位＝system 参（不入链）、`ANSWER_EXPLORE_CONTRACT` 仍恰一份；「子问题覆盖表」指代 V2-119 的 user 动态段段头（`ANSWER_COVERAGE_HEAD`——**硬依赖 V2-119 先落**）。**改判**：`::answer_round_segment_order_no_material` 的 `lines[0]==_VERB_PIN` 位移至 `lines[5]`（三步块 4 行＋1 空行）；族单源特征子串改取「首个 ≥12 字内容句」（三步块以 7 字段头行「【作答前三步】」起头）；机读面＝`tests/domains/test_v2_v120_three_step.py::test_answer_three_step_segment_order`。
13. **答案轮禁令件在场（钉 `pin-13` 的合同侧）**：装配输出含动词钉死句「现在：写最终答案交付用户。本步是写答案步——不再做任何决策、不再发射任何动作指令（finalize/decompose 等动作出现即废品）。」与答案要求⑦（「理解：／指标候选：」及任何动作 JSON 是过程产物，出现在答案中即废品）两字面——**提示词侧不注入回声形指令**；回声的观测面（`echo_flag` 恒 0）落 `specs/answering.md` 行为 14，本块只承接合同侧禁令件（分工见挂钩表）。断言：两句逐字在场（真源 `docs/runtime-refactor/recon/L2b-作答装配与回声.md` R-L2b-02 第⑦条＋`appv2/runtime/orientation.py` `answer_turn_preamble`（L295-300）动词钉死句；钉 `pin-13`，P1）。
14. **装配是确定性纯函数**：同入参两次装配输出逐字相等；调用前后 state 深比较相等（零写入）；AST 扫描本块——零 IO、零模型调用、零时钟读取（时间经入参注入，见接口定义）、零随机。断言：两跑逐字相等＋深比较相等＋AST 零命中。
15. **不夹带程序判断**：装配输出＝合同常量与 state 投影的确定性拼接，**不含任何程序判定的结论文本**（三选一结论／放行／拒答／覆盖自证／verdict 等语义结论不作为装配产物产生——那些是模型产出或结构判定，归 `clarification`／`preconditions`／`verification`）；AST 扫描本块无语义词表／正则判定（**豁免面＝形态处理**：集合成员判定与逐字子串校不算语义词表／正则，先例 `specs/understanding.md` 验收表同款）。断言：`::no_lexicon_or_regex_in_prompts` 绿＋行为 14 的确定性断言成立（输出无输入之外的语义增量）。
16. **决策轮增量条构成固定、逐字稿如下**（真源 `docs/runtime-refactor/recon/E1-澄清节点.md` R-E1-08＋`docs/runtime-refactor/recon/E2-工具匹配节点.md` R-E2-05；字面载体＝E1 装配段体＋`appv2/runtime/graph.py` L2394-2416；何时追加增量条＝调用方义务（编排面），本块只供条文本）：澄清轮增量（单条 user 内各段「\n」连接）＝①探查预算条「探查预算：全 run ≤{全 run 探查上限} 次，已用 {discover_used} 次。」（仅非首入轮——首入包内槽值会陈旧、机计数权威披露双保险同向；**2026-10-17 补·真机消重批·缺陷二**：族②常量内的 `{discover_used}` 槽**退场**（静态块内的槽值只在相位首入替换一次，随追加链恒冻为「已用 0 次」——真机 run-e1b6ff1e 据此误判预算、4 次 discover 全 no_hit 烧到 `budget_converged`），静态合同只留上限「全 run ≤10 次」、**真实已用数只由本条逐轮披露**；上限数值真源＝`docs/runtime-refactor/recon/E1-澄清节点.md` R-E1-10 `MAX_DISCOVERS_PER_RUN_CONTRACT`，随限额参数表收口，不写裸值）②回炉条（仅当存在 failed 子问题时）「回炉：只分解以下失败/缺失子问题（成功子问题结果已保留，禁止重复分解执行）：」＋逐行「- [id] question——拒因：reason」；拒因词面含「未绑定」或「不在台账」→ 行尾接「→改走 knowledge 链（tool=doc_retrieve）」（触发判据＝机器拒因原文的闭世界子串校——机器拒因为解析侧闭合世界产的机器面文本、原文零改动，真源 `docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md` A-P6b-05；属行为 15 豁免面「逐字子串校」，非语义词表）③用户补充条（user_hint 非空时）「用户已补充：{hint}——请把它落进本轮分解。」（与 A-P6b-26 的边界＝伪标注只禁 assistant 消息，本条为 user 增量条内前缀）④拒因回喂条（decision_error 非空时）「上次发射被拒：{decision_error}——修正后重新输出 JSON。」（`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-13；**2026-10-16 补·流水 66**：`decision_error` 若**已自带整套回喂壳体**（串首即「上次发射被拒：」——如槽位对账拒因载荷，「上游规格」`specs/clarification.md` 行为 8／接口定义错误契约）则**原样透传、不再套壳**——壳恰一遍；真机证据 `docs/runtime-refactor/ladder/L3/01`：旧形回喂「上次发射被拒：上次发射被拒：…」「——修正后重新输出 JSON。——修正后重新输出 JSON。」叠字两遍）⑤已做段（调用方传入文本原样在场、零改写——渲染归 context）。工具匹配轮增量＝拒因回喂条＋已做段（真源 R-E2-05）。断言：给定 fixture 状态，①—④在各自在场条件下按上列逐字稿逐字在场、⑤以调用方传入文本原样在场；澄清轮增量条序如上、工具匹配轮仅两件。

## 不降级与静默禁令

- **合法降级路径：无**——装配不降级：投影缺位走**占位文案**或**空串段**两形，不删段、不编造数据、不替换成通用措辞。
- **缺位的机读信号＝两形**：空串段（调用方跳过）＋占位文案（「（空）」「（水位未取得）」「（暂无族标注）」「关系：（空）」逐字在场）；断言：缺位投影 → 信号在场（行为 5／验收行）。
- **本块零截断**：装配输出不做任何静默截断／省略（截断与配额归 `context`，Manifest 记账归 `context`）；输出中不出现省略号形占位。
- 红线原文：`docs/runtime-refactor/arch/P7a-交接包与挂账清单.md`（A-P7a-37）「**不许静默**——若任何相位仍发生截断，模型面必须随材料段带明示……收口注记面同步披露」。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 合同常量族集合与接口清单相等（名单闭世界） | `tests/domains/test_v2_prompts.py::contract_constant_family_closed_world` |
| 答案要求清单 10 条逐字在场、顺序固定（2026-10-17 EB2 D2：7 条→8 条；EB4a：8 条→10 条） | `tests/domains/test_v2_prompts.py::answer_requirements_verbatim` |
| 答案要求清单 runtimev2 面内恰一处定义（消费方零字面副本；系统层不在范围） | `tests/domains/test_v2_prompts.py::answer_requirements_single_source` |
| 术语白话表（族⑥示例区）＝单源常量、随答案包恰一次入链、字节级稳定（静态块置前、投影段在后） | `tests/domains/test_v2_prompts.py::jargon_plain_glossary_injected_once` |
| 合同常量六族字面副本零残留（六族首句特征子串在四相位块／编排块源码零命中；系统层不在范围） | `tests/domains/test_v2_prompts.py::contract_constants_no_duplicate_literals` |
| 任务书段序固定、题干段置末紧邻生成点 | `tests/domains/test_v2_prompts.py::task_book_segment_order` |
| 任务书样例区＝固定三则、不随 state 变化、无边界对照例 | `tests/domains/test_v2_prompts.py::task_book_examples_fixed_set` |
| 数据区活体投影现取：改投影 → 输出随之变 | `tests/domains/test_v2_prompts.py::data_zone_live_projection` |
| 空投影 → 占位文案逐字在场（族／指标／术语／对象／关系／水位） | `tests/domains/test_v2_prompts.py::empty_projection_placeholder_verbatim` |
| 题意锚行两形（理解真值/假值）且置于决策轮指令首行 | `tests/domains/test_v2_prompts.py::anchor_line_two_forms_first_line` |
| 决策轮首入包构成逐件在场（行为 7 构成清单——澄清／匹配轮各按其件）、常驻块包裹对恰一对；四要素按轮合看逐轮在场；`shared_context=False` 时 §A 段与常驻块整段缺席（其余件照常） | `tests/domains/test_v2_prompts.py::decision_package_four_elements` |
| run 级共享上下文（§A 指南段＋台账常驻块）同 run 只注一次（挂第一次决策装配）＋链仍前缀延伸（pin-22）＋两段文本字节级不变（只改次数） | `tests/domains/test_v2_four_phase.py::test_decision_shared_context_injected_once_per_run` |
| 决策 prompt 的「已用 N 次」＝真实已发 discover 次数（静态合同不载计数——每轮动态条披露；整链零「已用 0 次」冻值） | `tests/domains/test_v2_four_phase.py::test_decision_prompt_discover_budget_shows_real_used_count` |
| 决策轮增量条构成与逐字稿（澄清轮：探查预算／回炉／用户补充／拒因回喂／已做段；匹配轮：拒因回喂／已做段；改道后缀触发＝机器拒因闭世界子串校；拒因回喂壳恰一遍——已自带壳者原样透传） | `tests/domains/test_v2_prompts.py::decision_increment_lines_present` ＋ `tests/domains/test_v2_prompts.py::rejection_feedback_frame_single` |
| 台账常驻块逐字转抄、恰一份；三删段名字面缺席 | `tests/domains/test_v2_prompts.py::ledger_resident_block_verbatim_once` |
| 消歧头统一措辞逐字在场 | `tests/domains/test_v2_prompts.py::disambiguation_header_uniform` |
| 分解样例三分支（未绑定→knowledge／可出数→data／空→空串） | `tests/domains/test_v2_prompts.py::decompose_example_three_branches` |
| 分解样例产出为合法 JSON 且键形正确（顶层恰 action＋question_group 两键、subtasks 单条五键） | `tests/domains/test_v2_prompts.py::decompose_example_valid_json` |
| 分解样例头行窗词锚定说明与无台账行说明在场（模糊时间词＝窗写 `null~null`、引擎缺参反问兜底三选一、不自行锚窗；无台账行＝槽位写「无台账命中」、不硬凑名；补句＝三段照抄上形「无台账命中｜未绑定｜窗未定」不加解释不改写） | `tests/domains/test_v2_prompts.py::decompose_example_head_window_rule` |
| 分解样例区两行：首行＝现造锚定指标形、次行＝无台账命中形全样例行逐字在场＋三段位 ∈ 对账闭世界；真机失败形（段尾加解释／自造绑定态窗形）照拒（防样例变松闸） | `tests/domains/test_v2_prompts.py::decompose_example_no_hit_full_row` ＋ `tests/domains/test_v2_clarification.py::no_ledger_hit_selfmade_forms_still_rejected` |
| 工具匹配合同带必填结论字段 `mention_mode`（合同正文＋填写样例同批在场；两值闭世界引 `tool_matching`） | `tests/domains/test_v2_prompts.py::toolmatch_contract_carries_mention_mode` |
| 合同常量零业务名词（fixture 词集与水位日形交集＝∅） | `tests/domains/test_v2_prompts.py::contract_constants_business_noun_free` |
| 答案轮段序固定（V2-120 三步合同置规章段第 0 段→动词钉死句→三件套→术语白话表→汇总合同→第二出口合同→材料期约束合同→起草合同；V2-96 D5：第二出口合同插在汇总合同与起草合同之间）；材料段零渗入 | `tests/domains/test_v2_prompts.py::answer_round_segment_order_no_material` |
| 作答前三步合同（2026-10-18 V2-120）：逐字稿照抄票面、入族⑤ `answer_draft`、随规章段恰一份、置**第 0 段**先于动词钉死句；段序＝先核→再决→后写；`ANSWER_EXPLORE_CONTRACT` 仍恰一份；承载位＝system 参不入链；端到端（脚本化／提示词条件化 completer）零支撑题先 explore、充分题不 explore | `tests/domains/test_v2_v120_three_step.py::test_answer_three_step_contract_verbatim_and_family` ／ `::test_answer_three_step_segment_order` ／ `::test_three_step_zero_support_explores_first` ／ `::test_three_step_sufficient_no_explore` |
| 子问题覆盖表（2026-10-18 V2-119）：提示行逐字（`ANSWER_COVERAGE_LINE`）＋段头（`ANSWER_COVERAGE_HEAD`）单点命名 `ANSWER_COVERAGE_*`、runtimev2 面恰一处字面定义；落动态段清单后材料前；全有支撑＝零追加 | `tests/domains/test_v2_v119_subtask_coverage.py::test_answer_coverage_line_verbatim_and_single_source` ／ `::test_answer_coverage_section_placement_before_materials` ／ `::test_answer_sufficient_material_no_line` |
| 缺位话术收紧（2026-10-18 V2-101）：起草合同**首句**逐字置换（只锚本轮材料、禁「报告/资料库未载」与「没有任何一条材料提及」升格库级否定）、逐字稿恰一份、旧首句退役、单源；`A-正6` 形端到端交付「本次材料未覆盖」而非库级否定；与 V2-122 两票逐字稿互斥不重复 | `tests/domains/test_v2_v101_absence_scope.py::test_absence_scope_verbatim_first_sentence_and_single_source` ／ `::test_absence_scope_and_v122_texts_mutually_exclusive` ／ `::test_a_positive_6_scoped_absence_end_to_end` |
| 作答第二出口合同（族⑤b `ANSWER_EXPLORE_CONTRACT`）＝两出口＋1 示例＋再探预算行在场、随规章段恰一次、单源零副本（V2-96 D5） | `tests/domains/test_v2_prompts.py::contract_constant_family_closed_world` ＋ `tests/domains/test_v2_prompts.py::contract_constants_no_duplicate_literals` |
| 答案轮禁令件在场（动词钉死句＋答案要求⑦；pin-13 合同侧） | `tests/domains/test_v2_prompts.py::answer_round_ban_lines_present` |
| 装配确定性纯函数：两跑逐字相等、不改入参、零 IO／模型／时钟（AST） | `tests/domains/test_v2_prompts.py::assembly_pure_deterministic` |
| import 面只许 state（AST 扫描——R3 半覆盖面的降维补位） | `tests/domains/test_v2_prompts.py::imports_state_only` |
| 程序侧无词表／正则语义判断（AST；豁免面＝集合成员判定与逐字子串校） | `tests/domains/test_v2_prompts.py::no_lexicon_or_regex_in_prompts` |
| 【边界集】空台账／缺水位／零未绑定指标（全可出数）／子问题清单超长 → 各落占位文案／空串段／data 链形分支 | `tests/domains/test_v2_prompts.py::boundary_empty_projection_variants` |
| 【保留集】常规投影装配输出不受空投影分支影响；四消费方既有验收断言不因本块改形回归 | `tests/domains/test_v2_prompts.py::retention_normal_assembly_unchanged` |
| **（H 批 2026-10-17）** 链首背景块＝族⑦常量、逐字稿照抄、字节稳定、单源 | `tests/domains/test_v2_prompts.py::system_background_verbatim` |
| **（H 批 2026-10-17）** 四环节规章取件函数（system 承载位）与 user 动态段分家：规章头在规章段在场、在动态段零命中、字节稳定 | `tests/domains/test_v2_prompts.py::system_contract_carriers_split_from_user_dynamic` |
| **（H 批 2026-10-17）** 承载位端到端：每环节请求首条＝system 规章段＋链首背景块恒在＋链本体 role 只含 user／assistant／system（背景一条）＋规章件零入链 | `tests/domains/test_v2_four_phase.py::test_system_slot_request_layout_end_to_end` |
| **（H 批 2026-10-17）** `system` 注入参只随本次请求走：请求首条前置、不入链、不用即散（零泄漏到下一环节）、记账面照落 | `tests/domains/test_v2_bookkeeping.py::call_model_system_injection_no_leak` |

> **测试文件归属**：本块验收测试绑**新建** `tests/domains/test_v2_prompts.py`（`prompts` 是阶段 2 新划的公共层块，与同层 `state` 规格同款归属；现状旧码装配测试在 `tests/domains/test_v2_v262_turn_selfsufficiency.py` 等，本批不改）。全部测试标识＝**待织网（阶段 5）**。

> **2026-10-16 补（L0/L2 三病灶修复批·审计）**：①**族③合同带必填结论字段 `mention_mode`**——`matches` 形＋字段说明＋填写样例三处同批（闭世界 `executed`／`mentioned_only`，真源 `specs/tool_matching.md` `SubtaskMatch.mention_mode` 条＋行为 5 枚举条）；**原缺口**＝闸把该字段当必填而合同零提及，模型无从遵守 → 工具匹配必拒循环到 recursion limit（真机证据 `docs/runtime-refactor/ladder/L2/03`：35 轮 100 步全拒）。②**分解样例头行补窗词锚定说明句**（模糊时间词＝窗写 `null~null`、引擎缺参反问兜底三选一、不自行锚窗；真机证据 `docs/runtime-refactor/ladder/L2/01` r1／r2 窗段无据必拒）。机读面＝`::toolmatch_contract_carries_mention_mode`／`::decompose_example_head_window_rule` ＋ `tests/domains/test_v2_clarification.py::boundary_slot_reconciliation_rejections`（拒因壳语窗段新形）。

> **2026-10-16 补（流水 66·L3 阻塞修复批·审计）**：①**分解样例头行补无台账行说明句**（子问题无台账行（报告内容题）＝槽位写「无台账命中」、不硬凑名——教的就是闸收的：上游闸新增该合法形，真源 `specs/clarification.md` 行为 8①；真机证据 `docs/runtime-refactor/ladder/L3/01`：完井液密度无台账行、旧教据下无合法形可写 → 三拒烧光轮次）。②**拒因回喂条去叠字**——`decision_error` 已自带整套回喂壳体（槽位对账拒因载荷，真源 `specs/clarification.md` 错误契约）者**原样透传、不再套壳**（壳恰一遍）；真机证据同文件：旧形回喂前缀与尾件各两遍。机读面＝`::decompose_example_head_window_rule`（补句逐字）／`::rejection_feedback_frame_single`（壳恰一遍＋裸拒因照套壳零回归）。

> **2026-10-17 补（L3 阻塞修复批·分解样例补行·审计）**：**分解样例区补无台账命中形全样例行**（次行逐字 `{"action": "decompose", "question_group": {"subtasks": [{"id": "s1", "question": "〈报告内容类问题〉", "ledger_notes": "无台账命中｜未绑定｜窗未定", "chain": "knowledge", "tool": "doc_retrieve"}]}}`）＋**头行补半句**「——三段照抄上形：无台账命中｜未绑定｜窗未定（不加解释、不改写）」。真机证据 `docs/runtime-refactor/ladder/L3/06`（run-b5b6b056）：模型知道要写无命中形，但两轮都没凑齐三个闭世界段（r1 段尾加解释 → 段数非三；r2 绑定态／窗段自造形越界）→ 3 轮烧光（三条「ledger_notes 槽位对账未过：s1」＋`budget_converged`）；病根＝样例区只给锚定指标形全样例行，无命中形只有一句话说明、没有三段位完整样例可照抄。机读面＝`::decompose_example_no_hit_full_row`（样例行逐字＋三段位 ∈ 对账闭世界）／`::no_ledger_hit_selfmade_forms_still_rejected`（真机失败形照拒——样例补行不改闸，防样例变松闸）＋`::decompose_example_head_window_rule`（补句逐字）／`::decompose_example_valid_json`（两行各自合法 JSON）。

> **2026-10-17 补（EB3 D3·组引标放开·审计）**：族⑤起草答案合同**行集交付段内一句逐字置换**——旧「禁汇总引标（如「[1]–[24]」写在表尾注里）」→ **「数据行禁汇总引标；组头允许 `[m]–[n]` 组引标」**（段内其余字面零改；数据行仍逐行 `[n]`，组头行的组引标不再被判违规）。逐字稿＝`docs/runtime-refactor/proposals/EB3-交付面分层与缺陷修复.md` D3；落点＝`appv2/runtimev2/prompts/constants.py` `ANSWER_DRAFT_CONTRACT`（本模块单点，相位块零字面副本纪律不变）。机读面＝`::answer_round_segment_order_no_material`／`::contract_constants_no_duplicate_literals`（段序与单点面）+ 核验侧豁免钉 `tests/domains/test_v2_verification.py::group_citation_marker_untouched`（组引标不被改）与 `::rewrite_exempt_disclosure_and_group_head`（组头行不删句）。**注**：V1 旧码 `appv2/runtime/graph.py` 的对应句不随本批改（V1 只作备份，ADR-0005）。

> **2026-10-18 补（V2-101·缺位话术收紧·审计）**：族⑤起草答案合同**段首第 1 句逐字置换**——旧 A-P6a-35 半句「（材料未覆盖所问时：只简短说明未找到与所缺，不逐源铺陈无关材料）。」→ **「缺位只锚本轮材料：写「本次材料未覆盖」，不得写「报告/资料库未载」或「没有任何一条材料提及」。」**（只锚**本轮材料**、禁库级否定升格；段内其余字面零改——置换非追加）。逐字稿＝`tickets/v2/V2-101-缺位话术收紧.md` §逐字稿（照抄、零改写）；落点＝`appv2/runtimev2/prompts/constants.py` `ANSWER_DRAFT_CONTRACT`（本模块单点，相位块零字面副本纪律不变）。**分工**＝本票只管**首句措辞**，材料范围限定与计数如实归 V2-122（两票逐字稿互斥不重复）；同改本常量的三票（V2-101→V2-121→V2-124）**串行且后票只许追加**（真源 `docs/runtime-refactor/design/统筹方案-作答提示词.md` §五）。机读面＝`tests/domains/test_v2_v101_absence_scope.py::test_absence_scope_verbatim_first_sentence_and_single_source`（逐字稿在场且恰一份／旧首句退役／单源）／`::test_absence_scope_and_v122_texts_mutually_exclusive`（两票文本互斥）／`::test_a_positive_6_scoped_absence_end_to_end`（`A-正6` 形端到端：交付「本次材料未覆盖」、零库级否定）＋改判 `::answer_requirements_single_source`（旧半句断言改判为新逐字稿断言）。**注**：V1 旧码 `appv2/runtime/graph.py` 的对应句不随本批改（V1 只作备份，ADR-0005）。

> **2026-10-17 补（EB4a·答案合同白话化·审计）**：族⑥答案要求清单**末尾追加第九／第十条**（逐字＝EB4a 票面引文；⑨＝术语注解条款，⑩＝材料未覆盖→先答相关＋给提问建议；第十条＝Owner 2026-10-17 裁决「召回问题的提示词侧缓解」）＋**族⑥示例区新增静态常量 `JARGON_PLAIN_GLOSSARY`（术语白话表）**，注入点＝`appv2/runtimev2/prompts/answer_round.py` `assemble_answer_prompt`（随答案包**恰一次**入链、字节级稳定；静态块置前、state 投影段在后；文本单点＝`constants.py`，消费方只引不复制）。依据＝`docs/runtime-refactor/research/最佳实践-3a-白话化与受众适配.md` 第三节 3.1（术语表注入＋合并式条款＋配示例——防「指令诅咒」，故本轮**只增两条**、不扩条群）。条间分隔体例同 EB2 D2（非末条尾字＝「；」、末条尾「。」；⑧／⑨尾「。」改「；」＝分隔符位，条文文本零改）。机读面＝`::answer_requirements_verbatim`（10 条逐字）／`::jargon_plain_glossary_injected_once`（单源＋恰一次＋字节稳定）／`::contract_constant_family_closed_world`（族名单闭世界含新常量）／`::answer_round_segment_order_no_material`（段序含术语白话表段）。

## 依赖与风险

- 依赖：`state`（唯一模块依赖——R3；只读投影）；消费方＝四业务相位（经 R2 包根）；真源＝`specs/modules.md` `## prompts` 卡。
- **2026-10-17 H 批（角色分家·system 承载位）风险与代价（明示接受）**：①**供应商合并行为**——请求面形＝`[system(本环节规章)] + 链（链首＝背景块 system 条）`，依赖「litellm 对 anthropic 把 messages 中的 system 消息合并为顶层 system 参数」（真源 H 批开票 §2.2）；真机探针先行，异常则回退方案 A（仅背景入 system、合同留 user）——回退只动 `call_model` 的注入面。②**KV 前缀代价**——请求首条＝环节规章 ⇒ **跨环节**首调用前缀不同、缓存重算一次（每 run 多付 3-4 次）；**环节内多轮**（澄清常 2-8 轮）规章相同 ⇒ 缓存照吃（`pin-22` 的链面前缀延伸不变，判据按**链段**比对——`tests/domains/test_v2_multi_turn_context.py::test_second_decision_context_carries_first_round_history`）。③**规章离开「每轮可见」位后模型失锚**——真机探针题对比 before/after 判分；若明显退化，可拆「system 放红线＋user 留样例行」混合位（备选，先不实现）。
- 风险与对策（每条带检测手段）：
  1. **卡与规格分叉（族成员展开）**：卡面公开接口只列两函数＋「合同常量＋各轮装配函数」注释，本规格把族成员展开成名单。**评审已裁定**＝族成员展开属卡面注释复数预留的具体化、非新公开类型，不构成 `docs/runtime-refactor/spec-review/state-评审.md` S-2 同款「卡缺公开成员」（`docs/runtime-refactor/spec-review/prompts-评审.md` P-08）；卡面补「族名单以 prompts 规格接口定义为准（闭世界）」注记＝卡级登记件交主窗（见风险 7⑤）。检测手段＝**人审**（评审工序，已完成）。
  2. **合同文本多处复制复发**（V1 病灶：同一答案规则三处字面并维护，真源 `docs/runtime-refactor/recon/L2b-作答装配与回声.md` D-L2b-01）。对策：单点断言＋消费方只引用。**已裁（流水 43①，Owner 可否决）：句首 V1 字面答案规则句群去重、由族⑥单点承接**——族⑤构成＝去重后形态（缺位话术句＋行集规矩段＋台账卡边界句，拼接序照现状；A-P6a-35 半句经 V2-101 逐字置换，见接口定义⑤）、与 V1 的差异＝删句首重复句群（A-P4b-49 票面附 C 锁定段不在去重范围）——见接口定义⑤。检测手段＝`::answer_requirements_single_source`／`::contract_constants_no_duplicate_literals`。
  3. **台账常驻块交界两说**：`specs/clarification.md` 触及面把「台账注入块」记在 prompts、`specs/modules.md` `## context` 卡有「术语表常驻注入」。本规格定界＝**固定包裹文本＋逐字转抄渲染归本块；投影取得归 context（经 tools 公开面）；Manifest 记账与不入史归 context/state 面**。检测手段＝**人审**（阶段 7 接口契约对账）＋`::ledger_resident_block_verbatim_once`。
  4. **装配滑成判断**（把三选一/放行拒答等语义结论写进装配）。对策：确定性纯函数断言＋AST 机检。检测手段＝`::assembly_pure_deterministic`／`::no_lexicon_or_regex_in_prompts`。
  5. **R3 半覆盖**（「只许依赖 state」对公共层其余块的面无闸）。对策：AST import 扫描测试补位。检测手段＝`::imports_state_only`＋人审（边界闸覆盖面声明，见挂钩表）。
  6. **样例渲染器产出非法 JSON**（V1 病灶 D-L2a-13：字符串拼接无转义）。对策：合法 JSON 形断言。检测手段＝`::decompose_example_valid_json`。
  7. **跨规格债与卡级登记清单（本批只登记、不代办——单写者纪律，交主窗统一回提）**：①`specs/understanding.md` 行为 1 指令区枚举补「样例」（或裁定样例归区——P-01 附属枚举缺口）＋题干段与输出契约区「末尾」的先后关系（SZP-05）；②`specs/answering.md` 挂钩表补 pin-03 交付面承接行（P-05）；③`specs/answering.md` 触及面「材料装配文本」措辞改述为「答案轮指令装配文本（材料段渲染归 context）」（P-11）；④`specs/modules.md` `## context` 卡「术语表常驻注入」与本规格常驻块渲染定界两说——回阶段 2 改卡（P-07，销项时点＝阶段 7 接口契约对账）；⑤`specs/modules.md` `## prompts` 卡注释补「族名单以 prompts 规格接口定义为准（闭世界）」（P-08）；⑥`SYSTEM_PROMPT` 落块归属（M1 :160 记「属 H9/H6 落点」，确切落块待阶段 2 对账——P-10）；⑦GuideProvider 装载实现落点——**已裁（流水 43⑥）：装载归 `context`（与台账同形、取一次装载进 state），prompts 只读渲染**（`synth/S1` H9 记 prompts 名下但本块零 IO——P-02 随裁销项）。检测手段＝**人审**（主窗回提＋阶段 7 接口契约对账）。

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
| 答案要求清单 10 条单点、逐字在场（`specs/answering.md` 行为 10 的唯一真源指向闭环；2026-10-17 EB2 D2：7 条→8 条；EB4a：8 条→10 条）＋术语白话表（族⑥示例区）单源、随答案包恰一次 | 测试 `::answer_requirements_verbatim`／`::answer_requirements_single_source`／`::jargon_plain_glossary_injected_once` ＋ **人审**（阶段 7 接口契约对账——`specs/answering.md` 风险 4 同款） | 待实现（阶段 5） |
| 答案要求③多来源分源（跨油田题分源列明的合同侧承接；`specs/verification.md` 挂钩表登记「prompts 规格落盘后承接」） | 钉 **`pin-03`**（P0）——本块落点＝合同侧③逐字在场（行为 2）；交付行为面待 `specs/answering.md` 回提承接（其挂钩表现无 pin-03 行——跨规格债登记交主窗，风险 7②；`specs/verification.md` 挂钩表亦只登记备查） | 待织网（阶段 5） |
| 起草回声＝0 的**提示词侧**（不注入回声形指令：动词钉死句＋答案要求⑦在场） | 钉 **`pin-13`**（P1）——**分工**：本块落点＝合同侧禁令件在场（行为 13、测试 `::answer_round_ban_lines_present`）；观测面（`echo_flag` 恒 0）落 `specs/answering.md` 行为 14（已定稿） | 待织网（阶段 5） |
| 相位合同一次性（回炉轮不重发） | 钉 **`pin-24`**（P1）——**行为不归本块**：追加记账归 `specs/state.md` 行为 5（已定稿，测试 `contracts_appended_idempotent`）；消费侧重发判定待 `context`／`orchestration` 规格；本块只承诺合同常量逐字稳定（常量无逐轮变体，行为 1） | 待织网（阶段 5）——记账面已在 state 侧落，消费侧待 context/orchestration |
| 投影缺位不静默（占位文案／空串段两形机读信号在场） | 测试 `::empty_projection_placeholder_verbatim` | 待实现（阶段 5） |
| 真源引用可解析（本规格全部引用行） | 真源引用可解析闸（`tools/ref_resolvable.py` 的 check 子命令） | 交稿前本地实跑 |
| 「不做什么」的纯范围排除（不解析／不调模型／不渲染材料等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（只引 state、零模型、零 IO）已由 R3/R7＋AST 测试覆盖 |
