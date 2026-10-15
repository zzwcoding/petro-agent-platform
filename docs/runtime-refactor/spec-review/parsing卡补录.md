# parsing 卡补录（`specs/modules.md` `## parsing` 卡——P-01 清算包余项三项）

- 日期：2026-10-15 ｜ 状态：**卡面补录**（窗 B 评审产出的卡级问题清单回工——`parsing-评审.md` §五.1、§七 P-01/P-04 处置表、§十一清算包）
- 本次只改 `specs/modules.md` `## parsing` 卡「公开接口」节（:388-406）＋本记录；**`## context` 等其余卡、`specs/parsing.md` 均未动**。未 git commit（主窗统一提交）。
- 前批：指纹器材四件已补（`821968f`，留痕 `modules-回工补写.md`）；本批补其清算包余项三项——**三项补齐即视为 P-01（L0）清零完成**（`parsing-评审.md` §十一口径；状态翻转待主窗）。

## 逐项改前改后（改后行号）

### ① `parse_tool_match` 成员补入公开面（清算包①）

- **改前**（821968f 后状态，`specs/modules.md` :387-388）：公开接口只有卡面两函数 `parse_understanding`／`parse_question_group`（＋指纹四件），`parse_tool_match` 连引用都无（`parsing-评审.md` §五.1 ②「V2 定案公开成员缺件」）。
- **改后**（:395-397）：紧随卡面两函数注新增
  `def parse_tool_match(content: str, group: QuestionGroup) -> tuple[SubtaskMatch, ...] | str: ...`
  ——签名逐字取自 `specs/parsing.md` 接口定义节「V2 定案签名」块（parsing.md:52）与①发射面解析器条目（parsing.md:57-60）；注「工具匹配发射解析＋闭合世界对账（matches ↔ 问题组一一对应），真源 R-L1b-05…R-L1b-21」。

### ② `parse_question_group` 返回形——按 P-04 裁决落「初拟形」注（不勘正卡面签名行）

- **改前**（:388）：`def parse_question_group(text: str) -> QuestionGroup | None: ...`（无注）。
- **改后**（:392-394）：卡面两函数后补注三行「卡面两函数＝阶段 2 初拟形（补录 2026-10-15，P-04 裁决『以迁移照抄为准』）——施工以 `specs/parsing.md` 接口定义节『V2 定案签名』为准：parse_understanding 两处同形；parse_question_group 返回形勘正后＝`ClarifyEmission | str`＋注入制限额参数（参数名以卡为准）」。
- **落法依据**：P-04 处置表裁决＝「判『以迁移照抄为准』……卡面两函数注『初拟形（阶段 2），施工以 V2 签名为准』（若判卡为准＝推翻已定稿 clarification 接口面，成本否决）」；§十一②同列「勘正**或**补『初拟形（阶段 2），施工以 V2 定案签名为准』注」两形——本批取**注形**（与 parsing.md:43-44／:86 既有「施工以 V2 定案签名为准」宣告一致，不产生新的两说）。

### ③ 族名单权威注（清算包③）

- **改前**：卡面对「族名单闭世界」零承载。
- **改后**（:404-405）：代码块末补注两行「族名单权威注（补录 2026-10-15，P-01 清算包③）：本卡公开面以 `specs/parsing.md` 接口定义为准（族名单闭世界——卡面未逐件重抄的其余成员＝②共用件四件／③载荷定型类四件，见其接口定义节）」——措辞对齐 parsing.md:82「**族名单是闭世界**」与 P-01 处置表「或卡面注记『族名单以 parsing 规格接口定义为准（闭世界）』」。

## 成员数对账（「数一遍，不一致以规格为准补齐或注明」）

- `specs/parsing.md` 接口定义节公开成员全计 **15**＝函数 11（`parse_understanding`／`parse_question_group`／`parse_tool_match`／`extract_plan_json`／`json_syntax_feedback`／`repair_inner_quotes`／`parse_with_quote_repair`／`payload_fingerprint`／`discover_fingerprint`／`emission_fingerprints`／`is_same_param_replay`）＋载荷定型类 4（`Subtask`／`QuestionGroup`／`SubtaskMatch`／`ClarifyEmission`）。
- 卡面补录后逐字列出 **7**（卡面两函数＋`parse_tool_match`＋指纹四件），其余 8（②共用件四件＋③载荷定型类四件）由③族名单权威注承接＝**「注明」路线**（P-01 处置表「或卡面注记……＋逐成员补录」的 sanctioned 形），非缺件。

## 疑点／登记件（不在本批票面，交主窗）

1. `specs/parsing.md:40`「卡面两函数（逐字照录……）」与 :43-44「两者差异＝卡级登记件（风险 7①，本规格不改卡，单写者纪律）」——本批卡面补录后卡面实有三函数、返回形差异已按 P-04 落注定形；该两处「两函数／差异在案」措辞可在下次 parsing 规格侧回工随批收词（销风险 7①）。本批票面未授权，未动。
2. §十一口径「三项补齐即视为 P-01（L0）清零完成，`specs/parsing.md` 翻『已定稿』（一行提交，窗 B 执行）」——parsing.md 状态行已是「已定稿」（流水 31 批 73eb965）；**P-01 清零的流水确认属主窗动作**，本补录只落卡面。

## 验证（三闸，改后实跑 2026-10-15）

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
