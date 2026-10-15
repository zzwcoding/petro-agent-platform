# context 卡补录（`specs/modules.md` `## context` 卡五件＋`specs/context.md` 风险 7② 落笔＋双定稿）

- 日期：2026-10-16 ｜ 状态：**卡面补录＋风险落笔＋定稿翻牌**（context-评审 `docs/runtime-refactor/spec-review/context-评审.md` §五 卡级问题清单五件（P-16 两缺在其中）回工＋流水 46① 承载位已裁落笔——主裁见 `docs/runtime-refactor/00-决议与方法.md:118`）
- 本次改三文件：`specs/modules.md` `## context` 卡（:419 职责行改述、:424-429 公开接口注、:432 ContextBuilder 去留卡级补注）；`specs/context.md` 风险 7②（:169 一处）＋状态行（:3 草稿→已定稿）；**两卡之外的 modules.md 内容、context.md 其余内容均未动**。未 git commit（主窗统一提交）。
- 同批联动：`specs/gate.md` 状态行翻定稿（卡面补录见 `gate卡补录.md`）——gate/context 双定稿后＝17 块全定稿＝阶段 3 收官（流水 46① 口径）。

## 逐项改前改后（`specs/modules.md` `## context` 卡，改后行号）

### ① compile 初拟形注（context-评审 卡级清单①）

- **改前**（:424）：公开接口代码块只有 `def compile(state: RunState) -> CompiledContext: ...`（无注）。
- **改后**（:425-427）：函数行后补注「卡面本函数＝阶段 2 初拟形（补录 2026-10-16，context-评审 卡级清单①）——V2 定案＝compile 退役为『追加内容渲染器』（真源 `docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md` A-P6b-24），不施工；施工以 `specs/context.md` 接口定义节『V2 定案签名』为准」。
- **落法依据**：`specs/context.md` 接口定义卡面注（:42-44）与风险 7①（:163）逐字对齐；体例照 parsing 卡「初拟形」注先例（`specs/modules.md:392-394`）。

### ② 职责行「术语表常驻注入」改述（context-评审 卡级清单②／prompts-评审 P-07）

- **改前**（:419）：`职责: 上下文——材料段渲染、过程档案（有界摘要）、术语表常驻注入、对话链追加`。
- **改后**（:419）：「术语表常驻注入」→「**台账/名录投影取得（经 `tools` 公开面装载进 state**——原「术语表常驻注入」改述，补录 2026-10-16，prompts-评审 P-07；**常驻块包裹与逐字转抄渲染归 `prompts`**）」。
- **落法依据**：prompts-评审 P-07 建议改述「台账/名录投影取得〔经 tools 公开面装载进 state〕」逐字采用；定界对齐 `specs/context.md` 风险 2（取得归本块、包裹与逐字转抄渲染归 prompts）与 `specs/prompts.md` 风险 3。

### ③ 职责行「对话链追加」职责改述（context-评审 卡级清单第 4 项／P-16①）

- **改前**（:419）：「对话链追加」（与 `## bookkeeping` 卡职责行「对话链与对话层追加」双载——物理追加写口在 bookkeeping）。
- **改后**（:419）：「对话链追加」→「对话链追加（＝**追加内容渲染＋compaction 治理归本块；物理追加归 `bookkeeping.append_message` 写口、追加时点归调用方**——补录 2026-10-16 改述，context-评审 P-16①）」。
- **落法依据**：context.md 起草稿定界（评审重点 1-b 在案）＝「追加内容渲染＋compaction 治理归本块；物理追加归 `bookkeeping.append_message`、追加时点归调用方」；写口承接＝`specs/bookkeeping.md` 行为 7（`append_message` 只追加）——eng/00 拆分裁决（写口归 bookkeeping 卡、本卡只留内容面）。

### ④ ContextBuilder 去留注（context-评审 卡级清单④——已退役）

- **改前**：卡面零承载（context.md 风险 7①「含现状 `ContextBuilder` 配置载体的去留」登记态，销项＝阶段 7）。
- **改后**（:432）：公开接口代码块后补 blockquote（体例照 prompts 卡「卡级补注」先例，`specs/modules.md:372`）：「**卡级补注（2026-10-16，ContextBuilder 去留——context-评审 卡级清单④）**：现状 `ContextBuilder` 配置载体的 V2 去留＝**已退役、不进 V2 面**（与卡面 compile 退役同批定案——照 `specs/agent-loop.md` 行为 2 改述口径『compile 已退役——流水 43⑦c』；对话装配改『每步在 `messages` 整链续写＋追加内容渲染器族』，施工以 `specs/context.md`『V2 定案签名』为准）。」
- **落法依据**：主裁给定「已退役」结论＋agent-loop 行为 2 改述口径（`specs/agent-loop.md:102-104`——「compile 已退役——流水 43⑦c 改述，删 79a 形『Context Builder 确定性编译…』旧文」）；其触及表行 :38 同口径（「追加内容渲染（compile 已退役——流水 43⑦c）」）。

### ⑤ 族名单权威注（context-评审 卡级清单第 5 项／P-16②）

- **改前**：卡面对「族名单闭世界」零承载。
- **改后**（:428-429）：代码块内补注「族名单权威注（补录 2026-10-16，context-评审 P-16②）：本卡公开面以 `specs/context.md` 接口定义为准（族名单闭世界——六函数＋常量族，见其接口定义节；卡面 `compile` 为初拟形、不施工）」。
- **落法依据**：P-16② 处置原文「补『公开面以本规格「V2 定案签名」为准（族名单闭世界）』注」；六函数＋常量族计数对齐 `specs/context.md:91` 闭世界句（六函数＝`load_ledger_dump`／`render_materials`／`render_process_notes`／`compile_manifest`／`compact_messages`／`trust_of`＋常量族 `DEFAULT_MAX_OBSERVATIONS`／`PROCESS_NOTES_BUDGET`／`TRUST_AGG`／`TRUST_LEDGER`／`TRUST_REPORT`／`RESIDENT_SOURCE_ROWS`）。

## `specs/context.md` 风险 7② 落笔（流水 46①）

- **改前**（:169 风险 7② 段尾）：「……**本块落 compaction 半面＝行为 9**）；③」。
- **改后**（:169）：「**本块落 compaction 半面＝行为 9**）——**已裁（流水 46①）：承载位＝`RunState` 独立字段 `dialogue_view_tokens`**（非 Budget 键——compaction 是对话视窗机制非轮预算；注入制由编排面注入；数值 8k 档真源 A-P6a-11）；③」——任务给定文本逐字采用，落风险 7②（compaction 登记项）段尾；风险 4 的「承载位登记（风险 7②）」交叉引用由此闭合。
- 主裁原文对照（`docs/runtime-refactor/00-决议与方法.md:118` 流水 46①）：「context 风险 7② compaction 承载位＝裁 `RunState` 独立字段 `dialogue_view_tokens`（非 Budget 键——compaction 是对话视窗机制、不是轮预算，Budget 键集闭世界不加键；注入制由编排面注入，数值真源 A-P6a-11『8k 档』随流水 43④）」。

## 双定稿翻牌（先自跑双闸确认绿，后翻）

- **改前**：`specs/gate.md:3`／`specs/context.md:3` 均「状态: 草稿」。
- **改后**：均「状态: 已定稿」（LEGAL_STATUS 在册取值，`tools/check_specs.py:34`）。
- **翻牌前置**：卡级批＋风险 7② 落笔后实跑 `check_specs` PASS（0 警告）＋`ref_resolvable` 绿（22 份）——均 exit 0 后方翻。

## 疑点／登记件（不在本批票面，交主窗）

1. `specs/context.md` 三处登记态措辞随本批卡面落地成为历史态：风险 1（「只登记不改卡，交主窗回阶段 2」）、风险 7①（卡级五件登记清单）、:95 真源句（「卡面与 V2 定案差异见风险 7①」）——本批票面只授权改风险 7② 一处，未动；可随下次回工收词或按「登记态→已兑现」读法交阶段 7 对账。
2. `## context` 卡 Seam 行「上下文编译（确定性管线）」与测试计划行未在五件清单内、未动——「上下文编译」措辞与 compile 退役存在同类张力，主窗可判是否随批改述（评审未列＝本批不裁）。
3. `ContextBuilder` 去留注按主裁写「已退役、不进 V2 面」；现状 V1 码面 `appv2/runtime/context.py:114` 该类仍在（V1 运行面）——注的本体是「V2 去留」，V1 退役节奏归阶段 5/6 迁移收口，非本批面。
4. compaction 识别面参形（链位贡献表／链条目标记——context.md 行为 9 SPC-01 占位）仍随风险 4 落点裁定后入签名，本批不动。

## 验证（三闸，改后终跑 2026-10-16）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                     # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：22 份规格的真源引用与边界规则编号均可解析。   # exit 0

$ uv run lint-imports --config tools/importlinter_v2.toml
R2 runtimev2 业务相位只经公共层包根（禁深层子模块） KEPT
R3 runtimev2 parsing/prompts 只许依赖 state KEPT
R5b ADR-0002 红线① 扩展：框架只许在 runtimev2.orchestration（其余 16 块禁引） KEPT
R6 runtimev2 各块只经 tools 接触引擎 KEPT
R7 runtimev2 各块只经 gateway_adapter 调模型 KEPT
R8 runtimev2 零 LLM 面：preconditions/verification/execution 不得引 gateway_adapter KEPT
Contracts: 18 kept, 0 broken.                                # exit 0
```
