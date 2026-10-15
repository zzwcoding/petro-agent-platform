- 日期：2026-10-15 ｜ 状态：**评审发现清单（待 L0 逐条处置）**
- 本清单只产发现，不修改任何现存文件。

# 前置检查（preconditions）规格 · 独立评审发现清单

评审对象：`specs/preconditions.md`（`状态: 草稿`）
主尺子：`docs/spec-process.md` §三（12 条）｜版式：`docs/spec-format.md`
外部视角，全部结论自翻原始文件核实；文件存在性/闸现状均已实跑验证（见 §四）。

---

## §一 结论摘要

1. 十节齐、标题逐字、spec gate 实跑 PASS、判定位条数（8＝6 主闸＋2 子闸）与真源 `synth/S3` C-01 逐字对上、Q-A/Q-B/Q-C 三条 Owner 裁决逐条落地——骨架成立。
2. 两处「支撑/归属」硬伤：`preconditions.md:59` 的「本块连 `gateway_adapter` 都不许引」**无闸支撑**（R7 只禁 `appv2.infra.llm_client`，R2 只禁包根以下深层），且 `:127` 把「零 LLM」挂到 R7 属类别错配；`caliber_key`/口径语义在 `preconditions.md:15,68` 与已定稿 `tool_matching.md:68,84,95` 之间**循环无主**。
3. 禁用词语义归属与三份样板＋`## gate` 卡冲突；外表审批「执行前再扫」的执行时点被写进本块，与 `arch/P3b` V2-44「引擎执行面」落位不一致。
4. 与模块卡接口签名不一致（卡 `Verdict`／规格 `SubtaskVerdict`）；「闸内残留词表判语义」的检测手段指错测试（AST 检不到词表判语义）。
5. 另有三条低：缺 R5b 行／缺「拿词表猜」总纪律行（对样板）／「换链回炉一次」数字无锚点。

---

## §二 发现清单

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| F-01 | 高 | 「本块连 `gateway_adapter` 都不许引」无闸支撑。R7 契约 source 含 `appv2.runtimev2.preconditions`，但 **forbidden 仅 `["appv2.infra.llm_client"]`**，不含 `appv2.runtimev2.gateway_adapter`；R2 只禁业务相位 import `appv2.runtimev2.gateway_adapter.*`（**深层子模块**），包根不在禁列——即 preconditions 引 `gateway_adapter` **当前无任何契约会红**。且挂钩表把「零 LLM」挂到 R7 属类别错配：R7 语义是「模型只经 `gateway_adapter`」，它**允许**经 gateway_adapter 调模型，与「零 LLM」不是一回事 | `specs/preconditions.md:59`、`:127`；`tools/importlinter_v2.toml:113-117`（R7 forbidden）、`:73-77`（R2 仅 `gateway_adapter.*`）；`specs/modules.md:522` | 删「连 gateway_adapter 都不许引」或将「preconditions 禁引 gateway_adapter」升成一条独立契约（自写 AST/grep 断言亦可）；挂钩表「零 LLM」改挂 AST 测试，不挂 R7 |
| F-02 | 高 | 口径语义（`caliber_key` 归一）归属**循环无主**：本规格说已上移到 `tool_matching`、本块只收结论；已定稿 `tool_matching.md` 三处明说 `caliber_key` 归一判据**归 `preconditions` 承接**。两文互相推给对方，实际无人拥有 | `specs/preconditions.md:15`、`:68`；`specs/tool_matching.md:68`、`:84`、`:95` | 二选一定死归属（按 §12-A 语义上移，似应回改 `tool_matching.md` 承接；并说明 `tool_matching.md:68/84/95` 需同步改）；定后回阶段 2/3 对账 |
| F-03 | 中 | 禁用词（废弃口径）语义归属与样板＋gate 卡冲突：本规格把「旧叫名/要旧口径、口径对不对」归 `tool_matching`；三份已定稿样板的「不做什么」首行均把「**废弃口径**」归 `gate`；`## gate` 卡明写「废弃词闸＝业务阀、判据交模型」。另本规格「不做什么」row6（入口安全闸）漏掉样板的「废弃口径」括注 | `specs/preconditions.md:15`、`:20`、`:68`、`:80`；`specs/understanding.md:16`；`specs/clarification.md:15`；`specs/tool_matching.md:15`；`specs/modules.md:454` | L0 定「入口禁用词闸（模型结论）」属 `gate` 还是 `tool_matching`，三文对齐；本块 row6 补「废弃口径」或明确不属本块 |
| F-04 | 中 | 「外表审批双保险」把「执行前再扫」的执行时点写进本块闸 2 并挂本块验收测试；`arch/P3b` V2-44 明示该实扫由**引擎（QueryExecutor 模板构造面）在 SQL 定稿后**执行、「扫描件落位 `tools` 引擎执行面」，`P4a2` 只把 resume 后「前置条件机重判放行」归前置。二者对「再扫」执行时点归属不一致（属 `preconditions` vs `execution`） | `specs/preconditions.md:70`、`:82`、`:103`；`docs/runtime-refactor/arch/P3b-票堆V2-35至45.md:180-184`（A-P3b-59/61）；`docs/runtime-refactor/arch/P4a2-票堆V2-51至55.md:44`（A-P4a2-12） | L0 裁：若实扫属引擎侧，本块只保留「申报面判一次＋消费 approved_ids 重判」，`external_table_double_check` 需拆/移（详见 §三 附加 14） |
| F-05 | 中 | 接口签名与模块卡不一致：卡返回 `list[Verdict]`，本规格返回 `list[SubtaskVerdict]`（且未给 `Verdict` 别名）。规格自称「签名以卡为准」却已偏 | `specs/modules.md:196`；`specs/preconditions.md:33`、`:54` | 二选一：改规格用 `Verdict`，或回阶段 2 改卡（标「须回阶段 2 改卡」） |
| F-06 | 中 | 风险 1（「语义项没上移、闸内残留词表判语义」）声明的检测手段＝AST `no_model_call_in_preconditions`，但该测试名/面只管「不调模型」，**检不到词表/正则判语义**；三份样板对应项均用 `no_lexicon_or_regex_in_<块>` AST 行＋写明豁免面，本规格缺此行 | `specs/preconditions.md:116`、`:107`；`specs/understanding.md:104`；`specs/tool_matching.md:110`；`specs/clarification.md:115` | 补一条 `no_lexicon_or_regex_in_preconditions` AST 行（并写明豁免面，如形态/集合判定），风险 1 检测手段改挂它（判据 11 的机读信号，见 F-07） |
| F-07 | 中 | 判定序表把「闸 1b 模糊时间词门」标为「结构」，但其实现是**词表命中判据**：`FUZZY_TIME_MARKERS=("最近","近期","前段时间")` ＋ `any(marker in question ...)`，正落总纲「凡写得进『出现 X 词就 Y』就要警觉」的形；规格未把它列为语义余项、未给豁免定性 | `specs/preconditions.md:81`（序 2 标「结构」）；`appv2/tools/precondition.py:66`、`:336`、`:327-342`；`docs/runtime-refactor/walk/00-设计总纲.md:26`、`:15-16`；`arch/P4a2:22`（A-P4a2-02） | 明确「模糊时间词门」定性：或由 Owner 书面豁免为「确定性词面门（非语义判据）」，或归入语义上移面；规格须写明 |
| F-08 | 中 | 框架与依赖红线**缺 langgraph/langchain 行**：三份样板均有「不得直接 import `langgraph`／`langchain`；对应闸 R5b」，本规格红线只需 R7/R6，未写 R5b；preconditions 属 runtimev2 相位，R5b source 覆盖它 | `specs/preconditions.md:56-61`；`specs/understanding.md:61`；`specs/tool_matching.md:75`；`specs/clarification.md:70`；`tools/importlinter_v2.toml:101-105`（R5b source 含 preconditions） | 补 R5b 行（样板同款句式） |
| F-09 | 低 | 行为 7「换链回炉只允许一次」的数字「一次」**无真源锚点**（`文件#节`）；样板数字均指真源（如 `tool_matching.md:89` 引统一预算表、`:81` 引裁决表） | `specs/preconditions.md:71`；真源应为 `docs/runtime-refactor/arch/P3b-票堆V2-35至45.md:162-169`（V2-43）／`docs/runtime-refactor/walk/06-过程图-循环挂起判断.md:40` | 行为 7 补锚点（V2-43／`walk/06` 循环表） |
| F-10 | 低 | 三态改写未在文档内标注其与真源「四态」的差异：`synth/S1` M4 仍写「四态（放行/挂起/拒答/注记）」，`ADR-0005` 明写「判四态 pass/blocked_ask/blocked_refuse/note」；本规格按 §12-Q-B 改三态（正确），但来源行未列 `synth/S1`、正文未声明 ADR-0005/S1 需同步修订或已由 §12 裁决覆盖 | `specs/preconditions.md:4`、`:69`；`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md:27`；`docs/runtime-refactor/arch/P7b-ADR与裁决图.md`（ADR-0005 节） | 来源行补 `synth/S1` M4；正文加一句「与 ADR-0005/S1『四态』的差异由 §12-Q-B 裁决覆盖，ADR/S1 同步修订」 |
| F-11 | 低 | 「不做什么」缺样板均有的总纪律行（「拿词表/正则猜 …… | 交模型；程序只校格式」）：三份样板各有一行，本规格无（同名纪律仅在「依赖与风险」出现） | `specs/preconditions.md:13-20`；`specs/understanding.md:23`；`specs/tool_matching.md:25`；`specs/clarification.md:22` | 补一行（样板同款），与 F-06/F-07 呼应 |

**计数：高 ×2（F-01/F-02）｜中 ×6（F-03..F-08）｜低 ×3（F-09..F-11）＝共 11 条。**

---

## §三 14 问逐条回答

**1. 十节齐 ＋ 标题逐字？** 齐、逐字。十节为 目标／不做什么／触及的模块／接口定义／框架与依赖红线／行为约定／不降级与静默禁令／验收测试／依赖与风险／与闸的挂钩表，与 `spec-format.md:31-34` 逐字一致；实跑 `uv run python tools/check_specs.py` → **PASS（0 警告）**。无发现。

**2. 行为约定每条能否写成 `assert`（含糊词点名）？** 无「尽量／合理／必要时／视情况」等含糊词。b1/b2/b3/b5/b6/b7/b8/b10 均可直接写成断言；b4「闸内只做结构校验…本块只接收其结论」与 b9「全拒的处理不属本块」属**声明式排除**（非直接断言，与样板同类写法），未点名含糊词——**无硬发现**（但 b4 的「结构校验」判据是 F-06/F-07 的靶面）。

**3. 数字有无裸值、能否指真源？** 唯一的判定位条数「8（6 主闸＋2 子闸）」锚 `synth/S3` C-01，与真源逐字对上（8 位、主闸 1~6＋子闸 1b/4b 完全一致）——**合规**。余下「一次」（回炉）**无锚点**＝F-09。无其它裸值。

**4. 不做什么每条有无「由谁承担＋锚点」？** 六行均备「由谁承担＋锚点」——**无发现**。（但 row1/row6 的「承担方」内容见 F-03 冲突。）

**5. 框架/依赖红线是否写闸名、闸名真存在、source 真覆盖 runtimev2？** 闸名真存在：R6/R7 均在 `tools/importlinter_v2.toml` 且 source 含 `appv2.runtimev2.preconditions`；实跑 `lint-imports --config tools/importlinter_v2.toml` → **17 kept, 0 broken**（R6/R7 均绿，「已真跑」属实）。但——「零 LLM」的**实际形状对不上**：R7 forbidden 仅 `appv2.infra.llm_client`，不禁 `gateway_adapter` → **F-01**；缺 R5b 行 → **F-08**。

**6. 不降级与静默禁令（合法降级路径？机读信号＋断言？）？** 声明「合法降级路径：无」＋fail-closed，`spec-format.md:24` 要求满足；机读信号＝step payload（`hit_rule`/`decision`/`notes`）＋notice（`synth/S6`），且验收表 `:108 verdict_signal_present` 提供「信号在场」断言——**无发现**。

**7. 验收测试（每行有标识？边界集/保留集两行？有无测不出的行？）？** 12 行全部绑 `tests/domains/test_v2_preconditions.py::<用例名>`，路径符约定 `tests/domains/test_v2_<块>.py::用例名`；【边界集】`:109`＋【保留集】`:110` 两行齐。无「测不出东西」的空行——**无发现**（唯 `:103 external_table_double_check` 的测点归属见 F-04）。

**8. 与闸的挂钩表（填了没？「已真跑」是否属实？）？** 已填，接不上的（纯范围排除）写了「人审＋原因」（`:131`）。「R7 已真跑」「R6 已真跑」**属实**（实跑 17 kept）；「spec gate 已进 CI」「AST 测试待实现（阶段 5）」属实（CI 有 `check_specs.py`／`lint-imports --config tools/importlinter_v2.toml` 步骤，见 `.github/workflows/ci.yml`）。但挂到 R7 的那行**语义错配**（R7≠零 LLM）→ F-01。

**9. 与 `walk/` 决策是否冲突（尤其 Q-A/Q-B/Q-C）？** 三条 Owner 裁决**逐条一致**：Q-A（语义上移、保持零 LLM）＝ b4＋序表注；Q-B（改三态、注记并入放行）＝ `:37` 枚举＋`:38` 注释＋ b5「不设第四态」，与 `walk/12:89` 逐字对上；Q-C（固定序＋命中即停＋一处明文表）＝ b2/b3＋`:76-87` 判定序表，与 `walk/12:90` 一致。裁决表 §12（`:146-154`）三行亦逐条对上。**无冲突**；唯三态与 ADR-0005/S1「四态」的差异未标注 → F-10（低）。

**10. 覆盖（`walk/12` Q1–Q3、建议 1–6、`synth/S1` M4、别块的事）？** Q1（8 位）→ b3＋明文表 ✅；Q2（语义全程序判）→ b4＋序表标注＋风险 1 ✅；Q3（判定序无通用原则）→ 由建议 6 的明文表落地 ✅。建议 1–6 全落：1→b4；2→按 §12-Q-B 改三态（取代草案的「四态保留」）✅；3→b6 ✅；4→b8 ✅；5→b7 ✅；6→明文表 ✅。`synth/S1` M4「零 LLM 逐子问题（四态）」无**漏项**（零 LLM／逐子问题／各态均落，仅状态数按裁决改为三态）。「别块的事」：b9 把「全拒直答」交 `answering`、序表把 6 个结构闸写在本块——均属本块判定序，未见越界写别块正文（「全拒归 answering」与 `walk/14` 的一致性**未验证**，见 §四）。

**11. 总纪律残留（程序替模型做语义判断）？** 闸 1（禁用词）、闸 3（合法口径）的语义半句在本规格均明标「语义——已上移／语义部分已上移」（`:68`、`:80`、`:83`）——**主靶面已治**。但：闸 1b「模糊时间词门」实为词表判据却标「结构」→ **F-07**；且因缺 `no_lexicon_or_regex` AST 行，此残留**无判据可判** → F-06。

**12. 与模块卡一致（职责/公开接口/依赖）？** 职责一致（三态＋零 LLM＋注记并入放行，`modules.md:191` 对上）；依赖一致（`state`＋`tools`，`modules.md:200` 对上；`tools` 本体在 `appv2/tools/precondition.py` 与 `ADR-0007 裁决 4` 对上，`docs/adr/0007:9`）；**公开接口不一致**：卡 `list[Verdict]` vs 规格 `list[SubtaskVerdict]` → **F-05**（须回阶段 2 改卡或改签名）。

**附加 13. 与三份已定稿样板写法是否一致？** 一致面：红线句式（「无点名框架（…）」）、挂钩表列式（本规格的硬要求｜挂钩｜现状）、边界集/保留集两行、机读信号行、`synth/` 前缀——均对齐。**不一致面**：①AST 机检行：样板用 `no_lexicon_or_regex_in_<块>`＋写「豁免面」，本块用 `no_model_call_in_preconditions` 且无豁免面概念（本块是「零 LLM」而非「无词表」——但这种写法差别在本块**恰恰漏掉**「词表判语义」这一残留面）→ F-06；②缺 R5b 行 → F-08；③缺「拿词表/正则猜」总纪律行 → F-11。

**附加 14. 「执行前再扫」执行时点归属是否与 `walk/12`／`recon/F` 一致？** **不一致（存疑已升级为发现，见 F-04）**：`walk/12`（`:19`、`:69`）把「申报＋实扫双保险」整体列在前置条件机节点下，本规格沿用此写法；但 `arch/P3b` V2-44（A-P3b-59/60/61）明示该 **实扫＝引擎（QueryExecutor 模板构造面）在 SQL 定稿后提取表名集、对白名单比对**——「闸不看申报看实际执行」、「扫描件落位 `tools` 引擎执行面」；`P4a2` A-P4a2-12 只把 resume 后「前置条件机重判放行」归前置。即：**申报面**在前置、**执行前再扫**属引擎/`execution` 侧，本规格把两者一并写在闸 2 并挂本块验收测试，与 V2-44 落位不合。结论：执行时点**倾向归 `execution`/`tools` 引擎面**（不硬下最终结论，最终归属待 L0 裁）。

---

## §四 未验证清单 ＋ 覆盖自检

### 未验证（不臆断）
1. **「全拒 → 由 `answering` 承接」（`preconditions.md:73`）**与 `walk/14`（作答）决策是否一致——**未验证**：本轮未读 `docs/runtime-refactor/walk/14-作答-汇总作答.md`。
2. **判定序明文表与 `appv2/tools/precondition.py` 实际判定序是否逐位一致**——**部分验证**：对照了 code docstring `:275`（「N1 禁用词 → 外表越集（放行态）→ 合法口径校验…」，未列 1b）与片段 `:289/:327-342`；未见 1b 之后到闸 2/3 的完整位序，**未逐位核全**。
3. **F-04 的最终归属（`preconditions` vs `execution`）**——证据倾向引擎侧，但属设计裁决，**待 L0 定**（本条按「发现＋存疑」双记，非硬下结论）。
4. **R7 契约是否覆盖「经 `gateway_adapter` 间接调模型」**——`gateway_adapter` 卡外部依赖 `infra.llm_client`（`modules.md:445`）证实其为模型出口；preconditions 引包根是否会被 R2 之外任何契约拦，已核 R2/R7 **均不拦**（F-01），其余 15 条契约未逐条排查——**已核关键两条，余**未验证**。

### 覆盖自检
- **本次实读文件（全路径）**：`specs/preconditions.md`、`specs/modules.md`、`specs/understanding.md`、`specs/clarification.md`、`specs/tool_matching.md`、`docs/spec-process.md`、`docs/spec-format.md`、`tools/importlinter_v2.toml`、`docs/adr/0007-架构图v3过审.md`、`docs/runtime-refactor/walk/12-前置检查-前置条件机.md`、`walk/06-过程图-循环挂起判断.md`、`walk/00-设计总纲.md`、`walk/裁决表.md`、`walk/判断归责表.md`、`recon/F-前置条件机.md`、`synth/S1-重写单元与证据交叉矩阵.md`、`synth/S3-口径裁决清单.md`、`arch/P3b-票堆V2-35至45.md`、`arch/P4a2-票堆V2-51至55.md`、`arch/P7b-ADR与裁决图.md`、`appv2/tools/precondition.py`、`tests/domains/test_v2_four_phase.py`、`.github/workflows/ci.yml`、`pyproject.toml`。
- **实跑验证**：`tools/check_specs.py` → PASS（0 警告）；`lint-imports --config tools/importlinter_v2.toml` → 17 kept／0 broken（R6/R7 已真跑属实）。
- **发现条数**：11 条 —— 高 ×2（F-01/F-02）、中 ×6（F-03/F-04/F-05/F-06/F-07/F-08）、低 ×3（F-09/F-10/F-11）；0 条 L0。
- **每条均带 `文件:行` 或 `文件#节` 锚点**；无锚点项不写入。
- 未验证项 4 条，已逐条列明未核面，不静默吞掉。

---

## §五 L0 逐条处置（2026-10-15）

> 两条高的指控**主窗已独立核验，成立**：①「本块连 `gateway_adapter` 都不许引」**无闸支撑**（R7 forbidden 仅 `appv2.infra.llm_client`；R2 只禁深层子模块）——**是我又虚报了一次**；②`caliber_key` 归属在两份规格间**互相踢皮球**（`preconditions` 说上移 `tool_matching`，`tool_matching` 说归 `preconditions`）。

| 编号 | 严重度 | 处置 | 落点 |
| --- | --- | --- | --- |
| F-01 | 高 | **采纳→闸侧已修＋交修订步（规格侧）** | **闸侧**：新增 **R8 契约「零 LLM 面」**（`appv2.runtimev2.preconditions`／`verification` 禁引 `appv2.runtimev2.gateway_adapter`；R7 只禁"直引 infra"，不禁"经 gateway_adapter 调模型"，故单列），**探针验证会咬人**（埋违规→BROKEN，拆掉→18 条全 KEPT）；真源补 R8 行。**规格侧（修订步）**：红线表述改为按 R7／B6／**R8** 分列；挂钩表「零 LLM」行**改挂 R8 ＋ AST 测试**（不再挂 R7） |
| F-02 | 高 | **采纳→L0 已裁＋已修** | **按 `walk/裁决表.md` §12-A（语义上移到匹配相位）**：**`caliber_key` 由 `tool_matching` 产出**（模型用本体账本把旧名归一到现行名）；**`preconditions` 只做台账闭世界的结构校验**（该键在不在册），不承担语义归一。**`specs/tool_matching.md` 三处已回改**（68／84／95 行） |
| F-03 | 中 | **不自行裁决 → 升 Owner** | **入口「废弃词闸」的语义判断归 `gate` 还是 `tool_matching`？** `synth/S3` C-01 把 N1 算进前置条件机的 **8 个判定位**；但架构上废弃词闸在**入口段**（`walk/03` §一「0 号位，先于一切解析」）且**已归 `gate` 模块**，三份已定稿样板也把「废弃口径」写在 `gate` 一侧。**这一条牵动判定位条数与三份规格，须 Owner 定** |
| F-04 | 中 | **采纳→L0 已裁；交修订步改规格** | 按证据 `arch/P3b`（V2-44：实扫由**引擎在 SQL 定稿后**执行、扫描件落位 `tools` 引擎执行面）：**「执行前再扫」归引擎执行面**（`tools`／`query`）；**本块只做申报面判定**（计划里声明的外表 → `ask`／审批），resume 后消费 `approved_ids` **重判**。修订步改写该条并拆 `external_table_double_check` |
| F-05 | 中 | **采纳→回阶段 2 已改卡** | `specs/modules.md` 的 `preconditions` 卡签名改为 `list[SubtaskVerdict]`（并注明**与核验的 `Verdict` 区分**，同名不同物）；规格无需改 |
| F-06 | 中 | 采纳→修订步 | 补 AST 行 `no_lexicon_or_regex_in_preconditions`（含豁免面＝形态／集合判定）；风险 1 的检测手段改挂它 |
| F-07 | 中 | **不自行裁决 → 升 Owner** | 「闸 1b 模糊时间词门」定性：它是 `FUZZY_TIME_MARKERS` ＋ `marker in question` 的**词面判据**，正落总纲「出现 X 词就 Y 要警觉」的形。**要么 Owner 书面豁免为「确定性词面门（保守触发反问，非语义判据）」，要么归入语义上移面**。修订步先加一行「**定性待 Owner 裁**」注 |
| F-08 | 中 | 采纳→修订步 | 红线补 R5b 行（不得 import `langgraph`／`langchain`；R5b source 覆盖 `preconditions`） |
| F-09 | 低 | 采纳→修订步 | 行为 7 的「一次」补锚点（`arch/P3b` V2-43／`walk/06` 循环表） |
| F-10 | 低 | 采纳→修订步 | 来源行补 `synth/S1` M4；正文加一句「与 ADR-0005／`S1`『四态』的差异由 §12-Q-B 裁决覆盖，ADR／S1 同步修订」 |
| F-11 | 低 | 采纳→修订步 | 「不做什么」补总纪律行（「拿词表／正则猜 …… → 交模型；程序只校格式」），与三份样板同款 |

**给修订步的修复单**：P-1…P-9（对应 F-01 规格侧／F-04／F-06／F-08／F-09／F-10／F-11，＋F-03／F-07 各加一行「待 Owner 裁」注）。
**给 Owner 的（2 条）**：F-03（废弃词闸归 `gate` 还是 `tool_matching`）／F-07（模糊时间词门定性）。

---

## §六 复审（2026-10-15）

- 复审对象：`specs/preconditions.md`（实际 136 行，`状态: 草稿`）｜依据：`docs/spec-process.md` §三（12 条判据）、`docs/spec-format.md`、真源 `specs/modules.md`＋`tools/importlinter_v2.toml`。
- 只读复核，全部结论自翻文件核实；实跑 `tools/check_specs.py`（PASS，0 警告）＋`lint-imports --config tools/importlinter_v2.toml`（**18 kept／0 broken**，R5b/R6/R7/R8 全 KEPT）。

**结论**：修复单 P-1…P-9 共 9 条**全部闭合**（未闭合 0／改了但不对 0）；12 条判据**无硬红**；本轮**无新增自相矛盾／悬空引用**（唯一新增文本 `:53` 的锚编号精度低，见 C-1）。除 F-03／F-07 两处待 Owner 项外，**规格内容已具定稿条件**，仅余两条低残余（C-1 锚编号、C-2 挂钩表缺 R5b 行）待 L0 定是否顺手修。

### A. 逐条核闭合

| 条目 | 闭合？ | 证据锚点 | 备注 |
|---|---|---|---|
| P-1 | 闭合 | `specs/preconditions.md:62`（R7／B6／R8 分列，删「连 `gateway_adapter` 都不许引」）；`:132`（挂钩改挂 **R8** ＋ AST 机检） | R7＋B6 辖 `litellm`／`appv2.infra.llm_client`、R8 辖 `appv2.runtimev2.gateway_adapter`，分列正确；实跑 R8 KEPT，`:132`「R8 已真跑」属实 |
| P-2 | 闭合 | `:73`（行为 6 改写＝申报面判定／执行前再扫归引擎／消费 `approved_ids` 重判）；`:85`（判定序表序 3 同步改写，**已无「双保险」字样**）；`:106-107`（验收表拆两行） | 行为／判定序表／验收表**三处均同步**。注：修订回执末节 item1 称 `:85` 未改、仍写「双保险」——**与实文不符**（实文已同步） |
| P-3 | 闭合 | `:112`（AST 行写明**豁免面＝形态处理／集合成员判定**）；`:121`（风险 1 检测手段改挂 `no_lexicon_or_regex_in_preconditions`） | 句式照三份样板 |
| P-4 | 闭合 | `:61`（R5b 行，source 覆盖 `preconditions`） | 实跑 R5b KEPT |
| P-5 | 闭合 | `:74`（「一次」补锚 `arch/P3b…V2-43` ／ `walk/06…循环表`） | 两锚文件＋节均实存 |
| P-6 | 闭合 | `:4`（来源补 `synth/S1` M4）；`:53`（加「差异由 §12…裁决覆盖，ADR／S1 同步修订」句） | 两处落点到位；`§12-Q-B` 编号精度低（C-1） |
| P-7 | 闭合 | `:21`（总纪律行＋锚 `walk/00` §二） | 与三份样板同款 |
| P-8 | 闭合 | `:84`（序 2 性质格「**定性待 Owner 裁**」在场） | **无定性裁断**，未越权 |
| P-9 | 闭合 | `:15`（row1「**入口废弃词闸的语义判断归属待 Owner 裁**」在场） | **无定性裁断**，未越权 |

计数：**闭合 9／未闭合 0／改了但不对 0**。

### B. 12 条判据复跑

1. **十节齐 ＋ 标题逐字**：无发现。十节标题见 `:7/:11/:23/:31/:58/:66/:92/:98/:117/:126`，与 `spec-format.md` §二之二逐字一致；实跑 check_specs PASS。
2. **行为约定可写 `assert`**：无发现。含糊词扫描 0 命中；b1–b10 均可断言（b4/b9 属声明式排除，样板同类）。
3. **数字**：无发现。`:70`「8 个判定位（6 主闸号＋2 子闸）」逐字对上 `synth/S3` C-01；`:74`「一次」已补锚；无裸字面值。
4. **不做什么**：无发现。`:14-21` 七行（含新增 row7）均备「由谁承担＋锚点」。
5. **框架/依赖红线**：**低残余（非本轮引入）**。R5b/R6/R7/R8/B6 均真存在且 source 覆盖 `preconditions`；但 `:64`「禁手写替代」未写对应闸名（样板 `tool_matching.md:77` 同句挂 R6/R7）。见 C-2。
6. **不降级与静默禁令**：无发现。`:94` 声明「合法降级路径：无」；`:95` 机读信号（step payload＋notice）；验收 `:113` 断言信号在场。
7. **验收测试**：无发现。14 行全绑 `tests/domains/test_v2_preconditions.py::<名>`；边界集 `:114`／保留集 `:115` 齐。
8. **与闸的挂钩表**：无发现。已填；接不上者 `:136` 写「人审＋原因」；「R8 已真跑」「spec gate 已进 CI」经实跑核实（lint-imports R8 KEPT；`ci.yml:24/26/32`）。
9. **与 `walk/` 决策冲突**：无发现。Q-A（`:62`/b4）／Q-B（`:37-39`/b5 三态）／Q-C（b2/`:79-90` 明文表）逐条落地，与 `walk/12:88-90`、`裁决表.md:150-152` 一致。
10. **覆盖**：无发现。Q1–Q3／建议 1–6／`S1` M4 无漏项；未见越界写别块（「全拒归 `answering`」与 `walk/14` 一致性未验证，见未验证 2）。
11. **总纪律残留**：无发现。闸 1／闸 3 明标「语义已上移」（`:68/:80/:83`）；闸 1b 标「定性待 Owner 裁」（`:84`）；`:112` 补「无词表／正则」判据。
12. **与模块卡一致**：无发现。`:34` 签名 `list[SubtaskVerdict]` ＝ 卡 `modules.md:196`（卡已改，F-05 闭合）；依赖 `state`＋`tools` 一致。

### C. 新增问题清单

| 编号 | 严重度 | 发现 | 证据锚点 | 性质 |
|---|---|---|---|---|
| C-1 | 低 | 新增句锚编号「`walk/裁决表.md` §12-Q-B」为**混合编号**：「§12」属 `裁决表.md`（其 §12 表行标 A/B/C，`:148-152`），「Q-B」属 `walk/12` §七（`:79`/`:89`）。精确引法应为 `裁决表.md` §12-B 或 `walk/12…§七 Q-B` | `specs/preconditions.md:53`；`walk/裁决表.md:148-152`；`walk/12-前置检查-前置条件机.md:78-90` | **本轮新增文本**（P-6），系修复单原文照抄，修订未自作改 |
| C-2 | 低 | 挂钩表缺「不 import `langgraph`／`langchain` → 边界闸 R5b」行——三份已定稿样板均有此挂行（`understanding.md:125`／`tool_matching.md:133`／`clarification.md:136`），而本规格 `:61` 红线已列该框架 | `specs/preconditions.md:126-136`、`:61` | **非本轮修订引入**（原文既有；原评审 judge 8 未列） |

**F-03／F-07 越权检查**：`specs/preconditions.md:15` 与 `:84` 两处均只写「待 Owner 裁」注，**未见任何定性裁断**——无越权。

### 未验证清单 ＋ 覆盖自检

**未验证（不臆断）**
1. **判定序明文表 8 位与 `appv2/tools/precondition.py` 逐位一致**——**部分验证**：代码序为 闸1(`:289`)→闸1b(`:330`)→闸2(`:359`)→闸3(`:424`)→闸4(`:493`)→闸4b(`:505`)→闸3前置 C5(`:528`)→闸5(`:551`)→闸6(`:564`)；规格把「闸3（＋前置台账闭世界 C5）」合一位，与 `synth/S3` C-01 分位一致；但代码把 C5 执行序排在闸4b **之后**，与规格序 4 不完全对应。规格已声明「条数与次序以 `synth/S3` 为准」，故不判缺陷；逐位未全核。
2. **「全拒 → `answering` 承接」与 `walk/14` 决策一致性**——未验证（本轮未读 `walk/14-作答-汇总作答.md`）。
3. **`walk/12` §四是否真含 Q-A**——`:15` 锚「§四/§七 Q-A」：§四（`:51`「关键张力」）＋§七（`:86`「Owner 裁决」含 Q-A `:78`）均实存，但 §四本身未标「Q-A」字样——**部分验证**。
4. `:64`「禁手写替代」是否需显式补挂闸名（抑或已由 `:63` R6 隐含覆盖）——**待 L0 定**（C-2 同源）。

**覆盖自检**
- 本次实读：`specs/preconditions.md`、`specs/modules.md`、`specs/understanding.md`、`specs/clarification.md`、`specs/tool_matching.md`、`docs/spec-process.md`、`docs/spec-format.md`、`tools/importlinter_v2.toml`、`docs/runtime-refactor/walk/裁决表.md`、`walk/12-前置检查-前置条件机.md`、`walk/00-设计总纲.md`、`walk/06-过程图-循环挂起判断.md`、`synth/S1-重写单元与证据交叉矩阵.md`、`synth/S3-口径裁决清单.md`、`synth/S6-事件与帧目录.md`、`arch/P3b-票堆V2-35至45.md`、`arch/P7a-交接包与挂账清单.md`、`appv2/tools/precondition.py`、`tests/domains/test_v2_four_phase.py`、`.github/workflows/ci.yml`、本评审文件＋修订回执。
- 实跑：`uv run python tools/check_specs.py` → PASS（0 警告）；`uv run lint-imports --config tools/importlinter_v2.toml` → **18 kept／0 broken**（R5b/R6/R7/R8 全 KEPT）。
- 发现计数：**新问题 2 条（均低：C-1／C-2）**；闭合 9/9；12 判据 0 硬红。每条均带 `文件:行` 锚点。
- **回执自述失真记录 2 处**（以实文为准）：① 回执末节 item1 称 `:85` 未改——实文已同步；② 回执称改后 137 行——实文 136 行。

## §七 定稿（2026-10-15）

**两处待 Owner 项已裁（侧窗讨论后拍板，回主窗执行）**：

| 条目 | 裁决 | 落地 |
| --- | --- | --- |
| **F-03** 入口废弃词闸归属 | **不放门口**（裁决 #12）：**判断**（提及 vs 执行）由**模型**在**配工具那一次调用**产出；**分派**（放行／拒答）留 `preconditions` 判定序**第 1 位**（机械分派）；**`gate` 只留安全阀**，废弃词闸移出 | `specs/modules.md` `## gate` 卡职责改写 ＋ `## preconditions` 卡补注；`specs/preconditions.md` 序 1 性质改「结构分派（消费模型结论）」、行为 4 改写、去待裁注；三份已定稿规格「不做什么」拆为「判断→`tool_matching`／分派→`preconditions`」；`specs/tool_matching.md` 补明**产出「提及 vs 执行」结论**（与 `caliber_key` 同批）；`eng/00` 原「`gate` 收 H12 全量」追加裁决**标作废** |
| **F-07** 模糊时间词门定性 | **交模型（不豁免）**（裁决 #13）：判断在模型侧产出，程序只按结论分派；**删「确定性词面门」说法** | 判定序序 2 性质改「结构分派（消费模型结论）」；行为 4 纳入「时间窗能否确定」 |

**净效果**：前置检查 **8 道判定位全部为纯结构／机械分派**（条数仍 8，与 `synth/S3` C-01 一致）；`gate` 只留安全阀；**R8 契约（零 LLM 面）因此成立，无需改动**。
`walk/裁决表.md` 项目级裁决加 **#12／#13** 并写明 #12 **覆盖**此前那条追加裁决。

**结论**：`specs/preconditions.md` ＝ **已定稿**。工序六步走完（起草→评审→处置→修订→复审→定稿）。
