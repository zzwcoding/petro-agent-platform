- 日期：2026-10-15 ｜ 状态：**评审发现清单（待 L0 逐条处置）**
- 本清单只产发现，不修改任何现存文件。

## 一、结论摘要

1. 十节齐、标题逐字、边界集/保留集/机读信号/挂钩表列式均与四份已定稿样板一致，spec gate 本地实跑 PASS（0 警告）。
2. 三条硬伤：`execute` 返回值签名与模块卡冲突（F-01）；`answered` 的判定归属自相矛盾（F-02）；「大结果阈值」指向的真源 `walk/裁决表.md` §06-A 里根本没有这条阈值（F-03）。
3. 依赖面：`persistence` 不在执行卡依赖里、其职责也未含「大结果原文落盘」，规格却把它当落盘面（F-04）——须回阶段 2 改卡。
4. 总纪律残留两处：`answered` 判定（F-02）与「缺位回捞」照抄的 V2-46 口径内含 `recall_relevant` 词面门（F-07）。
5. Q-A／Q-B／Q-C 三条已定裁决与本规格逐条一致，walk/13 的 Q1–Q3 与建议 1–6 全部落地。

## 二、发现清单表

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| F-01 | 高 | **公开接口签名与模块卡冲突**：卡定义 `def execute(state: RunState) -> list[Observation]`，规格写成 `-> ExecutionOutcome`（含 observations＋subtasks），而规格自称「签名以卡为准」。 | `specs/execution.md:36`、`specs/execution.md:65` vs `specs/modules.md:214`（`## execution` 公开接口） | 二选一：按卡为准把签名收成 `list[Observation]`，或**回阶段 2 改卡**（改卡后执行卡公开接口须同步） |
| F-02 | 高 | **`answered` 的判定归属自相矛盾**：接口把 `answered` 定义为执行块输出字段、行为 5 要求执行块「分别落账」，但「不做什么」把「这个结果算不算答上了」的判定交核验与模型、并声明「程序只记可观察事实」——执行块若不判语义就产不出 `answered`，若判则违总纪律。判定依据（结构判定还是模型结论）全篇未写。 | `specs/execution.md:44`、`:46`（字段）、`:81`（行为 5）vs `:21`（不做什么行）；判据冲突另见 `docs/spec-process.md:44`（程序不替模型判语义） | 明确 `answered` 的产出方与判定依据：或改为由 `verification`/模型结论回填、本块只落可观察事实；或写清是哪一个结构判定 |
| F-03 | 高 | **大结果阈值指向不存在的真源**：行为 4 称「阈值引统一预算表（真源 `walk/裁决表.md` §06-A）」，但 §06-A 只有循环上限一行，全表无「大结果/原文落盘阈值」；且「统一预算表」在仓内无落盘文件（仅被多处引用，无同名文档）。→ 阈值既无真源，`::big_result_ref_only` 与边界集行不可判。 | `specs/execution.md:80` vs `docs/runtime-refactor/walk/裁决表.md:92`（§06 A 行）；`find` 无「预算」文件、`docs/runtime-refactor/recon/K-上下文事件指南预算.md:1` 非该表 | 标明阈值真源（若尚无 → 先落一处统一预算表并声明）；在此之前不得声称「本规格不写字面值」 |
| F-04 | 中 | **`persistence` 是硬塞的依赖**：执行卡依赖＝`state`／`transport`／`tools`，卡内无 `persistence`；`persistence` 卡职责＝运行记录/检查点/黑匣子/审计，**未含「大结果原文落盘」**。规格却把 `persistence` 列为触及模块与依赖，并令其承担落盘面。 | `specs/execution.md:31`、`:115` vs `specs/modules.md:219`（execution 依赖）、`specs/modules.md:413`（persistence 职责） | **须回阶段 2 改卡**：执行卡补 `persistence` 依赖；`persistence` 卡职责补「大结果原文落盘（引用可寻址）」或在别处给出该职责的真源 |
| F-05 | 中 | **「模型调用不在本块」是红线却无闸**：规格声明本块只做确定性工具调用与结果归一（模型相关属 answering），但**没有任何闸覆盖它**——R8「零 LLM 面」只列 `preconditions`／`verification`，R7 只禁直引 `llm_client`，「execution 引 gateway_adapter」无规则可拦，挂钩表也无该行。 | `specs/execution.md:70` vs `tools/importlinter_v2.toml`（R8 契约 source 仅 `preconditions`/`verification`）、`specs/modules.md:522`（R8 定义） | 把 R8 扩到 `execution`（该块本即零 LLM，recon 亦证其不调模型），或退一步在本块加一条 AST/行为断言并进挂钩表 |
| F-06 | 中 | **失败分类粒度与现状/工具卡不一致，且「只重做失败子集」连带了终局拒答**：本块 `category` 闭世界仅 `retryable`／`fatal`（参数错／闸拒并入 fatal），`exec_status` 闭世界仅 `ok`／`failed`／`need_input`——**无法表达「闸拒＝终局拒答、不回炉」**；而现状 refused 是终局（不回炉），工具卡错误分类为「可重试｜修参｜拒答」三档。行为 3 又笼统说「只重做失败子集」，闸拒会被卷入回炉面。 | `specs/execution.md:43`、`:49`、`:79` vs `docs/runtime-refactor/recon/G-批量执行节点.md:79`（R-G-19 refused 终局不回炉）、`specs/modules.md:128`（tools 三档错误分类） | 补一档「终局拒答」（或明确 `fatal` 内「参数错可回炉 / 闸拒终局」的机械分派），并把行为 3「重做」的适用范围写成闭世界 |
| F-07 | 中 | **缺位回捞照抄的 V2-46 口径内含「词面门」，违总纪律且未标注**：行为 8 令「按真源 `arch/P4a1`（V2-46）的口径回捞」；V2-46 口径明载「回捞白场必须带条件门（`recall_relevant` 词面门）」，而该门是程序零模型词面判定（问句资产 token 命中缺位注记文本即判相关）——正是 walk/00 判定的「句子里出现 X 词就 Y＝程序替模型做语义判断」。 | `specs/execution.md:84` vs `docs/runtime-refactor/arch/P4a1-票堆V2-46至50.md:22`（A-P4a1-05）、`appv2/tools/handlers.py:829`（`recall_relevant`）、`docs/runtime-refactor/walk/00-设计总纲.md` §三.5 | 要么把回捞相关性判定交模型、程序只按结论分派；要么在规格里对这个继承口径显式标注「词面门仅作辅助快路径、非判据」并说明落点 |
| F-08 | 中 | **执行卡职责含「发现」（discover），规格全篇未落**：卡职责＝「批量执行——发现、执行、观察回流」；`synth/S1` M5＝「发现/执行/观察回流三节点」。本规格目标/接口只有执行＋观察回流，无「发现步」；发现步归属（clarification 还是一处未指明的发现节点）无人写清。 | `specs/modules.md:210`、`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md:28` vs `specs/execution.md:7-9`、`:36` | 二选一：补齐「发现」在本块的契约；或**回阶段 2 改卡**把「发现」从执行职责移出并指向承接块（S1 亦自相矛盾，需一并校正） |
| F-09 | 中 | **缺 AST 机检行，与四份已定稿样板不一致**：四份样板每份都有一条 `tests/domains/test_v2_<块>.py::no_lexicon_or_regex_in_<块>` 验收行（＋挂钩表行）；本规格验收表与挂钩表均无该行，而本规格明写「不拿词表／正则猜」的禁令。 | `specs/execution.md:94-111`、`:122-134` vs `specs/understanding.md:106`、`specs/clarification.md:117`、`specs/tool_matching.md:113`、`specs/preconditions.md:112` | 补一条 `::no_lexicon_or_regex_in_execution`（本块形状处理豁免面写清）＋挂钩表一行 |
| F-10 | 低 | **`persistence` 唯一出口红线无闸名**：框架红线写「大结果落引用只经 `persistence` 公开面（不自行写库／不直连对象存储）」，但未写对应闸名（对照理解/匹配块对模型出口都点了 R7）。 | `specs/execution.md:72` vs 同批样板 `specs/tool_matching.md:77`、`specs/understanding.md:62` 的「对应闸：R7」写法 | 点出对应闸（无则按 spec-format §五降维成「不许出现直连符号」AST 断言并写明原因） |
| F-11 | 低 | **跨块「落引用」责任归属未写清**：walk/14 §B 明示「大结果落引用」与 §13-B **合并为同一件事**，作答块也要用；本规格只写了执行块落引用＋persistence 为载体，**未写回答（answering）侧材料的落引用由谁落**（execution 落 vs answering 落 vs persistence 统一落）。 | `specs/execution.md:31`、`:80` vs `docs/runtime-refactor/walk/14-作答-汇总作答.md:58`、`docs/runtime-refactor/walk/裁决表.md:176`（§14-B「与 §13-B 合并」） | 在规格（或跨块约定）里写清落引用的单一责任方与 answering 的消费方式 |

## 三、14 问逐条回答

1. **十节齐＋标题逐字**：齐。`## 目标`／`## 不做什么`／`## 触及的模块`／`## 接口定义`／`## 框架与依赖红线`／`## 行为约定`／`## 不降级与静默禁令`／`## 验收测试`／`## 依赖与风险`／`## 与闸的挂钩表`，顺序与 `docs/spec-format.md` §二/§二之二 逐字一致（`specs/execution.md:7-135`）。本地实跑 `uv run python tools/check_specs.py`＝PASS（0 警告）。**无发现**。
2. **行为约定每条能否写成 assert**：绝大多数可（无「尽量／合理／必要时／视情况」级含糊词）。三处不可直接写死：行为 4（阈值无真源，见 F-03）、行为 3（「只重做失败子集」未界定范围，见 F-06）、行为 8（引外部口径，见 F-07）。
3. **数字／裸值／指真源**：全篇唯一「数字性」表述是行为 4 的「阈值」——**指向不存在的真源**（§06-A 无此阈值），故不可判，见 **F-03**。
4. **不做什么每条有「由谁承担＋锚点」**：7 行全有（`specs/execution.md:13-21`）。**无发现**（锚点为模块卡章节或 walk/00 §二，齐备）。
5. **框架与依赖红线：闸名真存在、source 真覆盖 execution**：R6 契约真存在且 `source_modules` 含 `appv2.runtimev2.execution`（`tools/importlinter_v2.toml` 的「R6 runtimev2 各块只经 tools 接触引擎」条）；R5b 契约同样含 `execution`。故「只经 tools 公开面→R6」「不 import langgraph→R5b」属实。**但**「模型调用不在本块」这条红线**无闸**（R8 未覆盖 execution），见 **F-05**；`persistence` 唯一出口红线无闸名，见 **F-10**。
6. **不降级与静默禁令**：声明「合法降级路径：无」（`specs/execution.md:90`）✓；「落引用／失败／缺参→机读信号」配了断言行 `::execution_signal_present`（`:91`、`:109`）✓；红线原文 `arch/P7a-交接包与挂账清单.md` A-P7a-37 真实存在（`docs/runtime-refactor/arch/P7a-交接包与挂账清单.md:98`）✓。**无硬发现**（信号行未逐字段枚举，属可接受）。
7. **验收测试**：每行都绑了 `tests/domains/test_v2_execution.py::<用例名>`（`:98-111`），路径约定符合 `test_v2_<块>.py`；**边界集行**（`:110`）与**保留集行**（`:111`）两行齐。偏「测不出确定性」的行：`::big_result_ref_only` 依赖未定义阈值（连 F-03）；其余可测。**发现归 F-03**。
8. **与闸的挂钩表**：已填（`:122-134`），接不上闸的行写了原因（`:134`）。「R6/R5b 已真跑」与真源相符——契约真存在、`source` 含 execution、CI 真跑 `uv run lint-imports --config tools/importlinter_v2.toml`（`.github/workflows/ci.yml:26`）。挂钩表缺「模型调用不在本块」「persistence 唯一出口」两行（见 F-05／F-10）。
9. **与 walk/ 决策冲突**：Q-A（改并行）→ 行为 1 ✓；Q-B（原文落引用、窗口留摘要＋引用、替代渲染帽）→ 行为 4 ✓；Q-C（执行状态与是否真答上分开记）→ 行为 5 ✓。三条裁决逐条一致（`docs/runtime-refactor/walk/13-批量执行-查询执行.md:80-82`、`walk/裁决表.md:163-167`）。另：行为 3 的失败语义与现状「闸拒终局不回炉」有摩擦（F-06），非直接冲突但需钉死。
10. **覆盖（walk/13 Q1–Q3＋建议 1–6；S1 M5；有无别块内容）**：walk/13 的 Q1–Q3 与建议 1–6 全部落地（行为 1–8 一一对应）。**S1 M5 漏项**：M5 含「发现」节点，本规格未落 → **F-08**。未发现把别块的事写进来（answering 的动作只在「不做什么」里排除，未实际越界）。
11. **总纪律残留（尤其 answered）**：两处。①`answered` 的判定归属矛盾（**F-02**）——这是核心：程序凭什么说「真答上了」全篇未定，且与「程序只记可观察事实」打架；②缺位回捞继承了含 `recall_relevant` 词面门的 V2-46 口径（**F-07**）。
12. **与模块卡一致**：三处不一致——**职责**（卡含「发现」，规格未落，F-08）、**公开接口**（签名冲突，F-01）、**依赖**（本块多列 `persistence`，F-04）。均标「须回阶段 2 改卡」（或按卡改规格）。

**附加 13（与四份样板同类条款一致性）**：红线句式（「**...**；对应闸：**R6**」）一致；挂钩表列式（本规格的硬要求｜挂钩｜现状）一致；边界集/保留集两行齐；机读信号行（`::execution_signal_present`）与样板的 `*_signal_present` 同款；`synth/` 前缀在「来源」节写了 `synth/S1`（M5）。**唯一不一致＝缺 AST 机检行**（样板均有 `::no_lexicon_or_regex_in_<块>`，本规格无）→ **F-09**。
**附加 14（与作答块「大结果落引用」是否同一件事＋责任归属）**：walk/14 §B 明示二者「合并」为同一件事（`walk/14-作答-汇总作答.md:58`、`walk/裁决表.md:176`）——故**是同一件事**。但**落引用的责任归属未写清**：本规格只写了执行块落＋persistence 为载体，未写回答（answering）侧材料的落引用由谁落 → **F-11**；answering 规格尚未写，其侧归属**未验证**（见 §四）。

## 四、未验证清单 ＋ 覆盖自检

### 未验证（不硬下结论）
1. 「R6/R5b 已真跑」中的「探针验证会红」措辞只在 `specs/tool_matching.md:135` 出现，`specs/execution.md:128-129` 仅写「已真跑」；我核到契约真存在＋CI 真挂 `lint-imports`，**未实跑**验证其当前绿色（部分未验证）。
2. 回答块 (`specs/` 未写、`walk/14` 已定) 的「大结果落引用」由谁落——**未验证**（F-11 只报「未写清」）。
3. 「统一预算表」是否有另行落盘：仓内 `find` 无同名文件，判为**未落盘**；不排除藏在别仓（teach）——**未验证**。
4. S1 M5「发现」与 S1 表 A（E1→M2 澄清）自相矛盾；「发现」最终归块为**未验证**（F-08 已如实标注）。

### 覆盖自检
- 已读文件（均本地实读，非二手）：`specs/execution.md`；判据 `docs/spec-process.md`、`docs/spec-format.md`；真源 `specs/modules.md`、`tools/importlinter_v2.toml`、`tools/check_specs.py`、`.github/workflows/ci.yml`；裁决 `docs/runtime-refactor/walk/{00-设计总纲,06-过程图-循环挂起判断,13-批量执行-查询执行,14-作答-汇总作答,17-全树收官总览,裁决表}.md`；取证 `docs/runtime-refactor/recon/{D,H,G}`、`arch/{P4a1,P4b,P7a}`、`synth/{S1,S3}`；样板 `specs/{understanding,clarification,tool_matching,preconditions}.md`；代码抽查 `appv2/tools/handlers.py`、`appv2/runtimev2/execution/__init__.py`。
- 发现计数：**11 条**（高 3／中 6／低 2）。
- 机检：`uv run python tools/check_specs.py` ＝ PASS（0 警告）；`lint-imports --config tools/importlinter_v2.toml` 未实跑（见上 1）。

---

## §五 L0 逐条处置（2026-10-15）

> 三条高的指控**主窗已核验，全部成立**。其中 F-03 又是「指向不存在的真源」——与 `tool_matching` 那轮的幻影闸同族。11 条**全部采纳**。

| 编号 | 严重度 | 处置 | 落点 |
| --- | --- | --- | --- |
| F-01 | 高 | **采纳→回阶段 2 已改卡＋交修订步** | `execution` 卡签名已改 `-> ExecutionOutcome`（并点出 `ExecutionOutcome`／`SubtaskExec` 两形）；规格侧交修订步对齐卡并去掉自相矛盾的自述 |
| F-02 | 高 | **采纳→L0 裁决＋交修订步** | **`answered` 由 `execution` 按「可观察事实」产出**（该子问题是否拿到**非空观察**）——**这是结构判定，不是语义判断**；「答案好不好、对不对」归 `verification`。修订步据此改写「不做什么」与行为 5，消除"要么程序判语义、要么产不出字段"的两难 |
| F-03 | 高 | **采纳→交修订步** | **删掉「阈值引统一预算表」**——`walk/裁决表.md` §06-A 只有循环上限，**无此阈值**（指向不存在的真源）。改为「**阈值待定**：阶段 5 实现时随真机数据定；本规格只写机制（超阈即落引用）」 |
| F-04 | 中 | **采纳→回阶段 2 已改卡** | `execution` 卡依赖补 `persistence`（大结果引用落盘，只经其公开面）；`persistence` 卡职责补「**大结果原文的引用载体**（可寻址 handle）」 |
| F-05 | 中 | **采纳→闸侧已扩＋交修订步** | **R8 已扩到 `execution`**（`preconditions`／`verification`／`execution` 三块禁引 `appv2.runtimev2.gateway_adapter`），**探针验证会咬人**；真源 R8 行同步。修订步红线补 R8 行 |
| F-06 | 中 | **采纳→交修订步** | 错误分类**补「终局拒答」档**（闸拒＝终局、**不回炉**），与 `tools` 卡三档（可重试｜修参｜拒答）对齐；行为 3 改写为「**只重跑 `retryable`**」 |
| F-07 | 中 | **采纳→L0 裁决＋交修订步** | **缺位回捞按「模型给出的缺位结论」驱动**，程序**不拿词面判「相不相关」**（**不照抄** `V2-46` 的 `recall_relevant` 词面门）——与裁决 #13 同一取向。修订步据此改写该条，并注明与 V2-46 原口径的偏离 |
| F-08 | 中 | **采纳→交修订步** | 补「**发现（discover）**」条目：`execution` 卡职责含「发现」（`synth/S6` 的 `tool` 事件发射单元＝M5），规格须落该职责 |
| F-09 | 中 | **采纳→交修订步** | 补 AST 机检行 `no_lexicon_or_regex_in_execution`（含**豁免面**），与四份样板同款 |
| F-10 | 低 | **采纳→交修订步** | 「只经 `persistence` 公开面」补**对应闸名**；若确实无闸，按 `docs/spec-format.md` §五 降维为「不许出现直连符号」AST 断言并写明原因 |
| F-11 | 低 | **采纳→交修订步** | 写清**落引用的单一责任方**：**`execution` 落、`persistence` 为载体**；`answering`（作答块）**只消费引用**，不重复落（`walk/裁决表.md` §14-B「与 §13-B 合并」） |

**给修订步的修复单**：E-1…E-10（对应 F-01 规格侧／F-02／F-03／F-05／F-06／F-07／F-08／F-09／F-10／F-11）。F-04 已由阶段 2 改卡办结。
**给 Owner 的**：无（本轮无需 Owner 裁；F-03 的「阈值待定」登记为阶段 5 事项）。

---

## §六 复审（2026-10-15）

### 结论

修复单 E-1…E-10 **全部闭合（10/10）**，12 条判据**无红**；四处口径（接口／行为／验收／挂钩）在三档分类与签名两处改动后**互相一致**，十节标题仍逐字，spec gate 本地实跑 PASS（0 警告，本轮复审实跑）。上轮 11 条发现均已消解，未发现自相矛盾、悬空引用或覆盖漏洞。仅两处**低**级真源侧备注（R8 契约名与 source 不同步；零 LLM 红线未并点 R7），**均不构成定稿阻塞**。判：**够「可定稿」**——可转阶段 6（L0 判 `状态: 已定稿`）。

### A. E-1…E-10 逐条闭合核对

| 条目 | 闭合？ | 证据锚点 | 备注 |
|---|---|---|---|
| E-1（F-01 签名） | 闭合 | `specs/execution.md:36` ＝ `specs/modules.md:215`（均 `-> ExecutionOutcome`）；`:65`「签名以卡为准」现与卡一致 | 回执自报「未改」**成立**：卡已在阶段 2 改为同一签名，规格侧无需改。全篇 grep 无 `list[Observation]` 作 `execute` 签名，无残留自述 |
| E-2（F-02 answered） | 闭合 | `specs/execution.md:21`（`answered` 只按可观察事实／结构判定）；`:82`（判据＝可观察事实：`observation.content` 非空或 `ref` 存在） | 判据=结构判定（非程序判语义），无「程序替模型判语义」；`:21` 新增锚点 `## verification` 属补全「由谁承担」，非越界 |
| E-3（F-03 幻影阈值） | 闭合 | `specs/execution.md:81` 已改「**阈值待定**：阶段 5 随真机数据定」；grep 全篇无「预算」；无把阈值挂 `裁决表.md` §06-A 的表述 | 删净。`:4` 来源行的 `§06/§13` 系一般来源引用，非阈值真源 |
| E-4（F-05 零 LLM 闸） | 闭合 | `specs/execution.md:71`（R8；source 覆盖 `preconditions`／`verification`／`execution` 三块）；`tools/importlinter_v2.toml:122`（R8 `source_modules` 真含 `appv2.runtimev2.execution`）；挂钩表 `:136` | source 对得上。**低**：契约**名**（`toml:120`）仍只写 `preconditions/verification`——见 C-1 |
| E-5（F-06 三档分类） | 闭合 | `specs/execution.md:49`（接口 `retryable`／`bad_args`／`refused`）、`:80`（行为 3）、`:103`（验收行）三处一致；grep 全篇**无 `fatal`**；对齐 `specs/modules.md:128`「可重试｜修参｜拒答」 | L0 后续把 `fatal` 改 `bad_args` 已落地；术语统一、无残留；接口／行为／验收口径一致 |
| E-6（F-07 recall_relevant） | 闭合 | `specs/execution.md:85`「按模型给出的缺位结论……程序**不拿词面判**」＋注明与 V2-46 口径偏离；`arch/P4a1-票堆V2-46至50.md:22` 确认原口径含 `recall_relevant` 词面门 | 已去词面门并如实标注偏离 |
| E-7（F-08 发现） | 闭合 | `specs/execution.md:88`（发现归本块；`tool` 事件 M5）；验收 `:110`；真源 `specs/modules.md:210`（职责含「发现」）＋`synth/S6-事件与帧目录.md:10,18`（M5） | 职责落地，含验收行 |
| E-8（F-09 AST 行） | 闭合 | `specs/execution.md:109`（`::no_lexicon_or_regex_in_execution`，豁免面写清）；挂钩表 `:137` | 与样板同款（`specs/understanding.md:106`） |
| E-9（F-10 降维 AST＋原因） | 闭合 | `specs/execution.md:73`（降维为 AST 断言 `::no_direct_storage_symbols`）**并写明原因**（R1–R8 未覆盖「直连对象存储／自写库」，R2 只禁深层子模块）；验收 `:111`；挂钩表 `:138`（重复原因） | 原因确已写明，未虚构闸名 |
| E-10（F-11 落引用责任方） | 闭合 | `specs/execution.md:89`（`execution` 落、`persistence` 为载体、`answering` 只消费不重复落）；真源 `walk/裁决表.md:176`（§14-B「与 §13-B 合并」） | 责任方单一，与真源一致 |

### B. 12 条判据逐条复跑

1. **十节齐＋标题逐字**：齐。`specs/execution.md:7/11/23/33/67/76/91/97/119/128` 逐字匹配 `docs/spec-format.md` §二之二。**无发现**。
2. **行为约定能否写 `assert`**：12 条无「尽量／合理／必要时／视情况」。行为 4 虽「阈值待定」，但机制（超阈即落引用）可断言，不依赖字面值。**无发现**。
3. **数字／裸值／指真源**：全篇无裸字面值；唯一曾悬空的阈值已改「待定」（E-3），无「指向不存在的真源」。**无发现**。
4. **不做什么每条「由谁承担＋锚点」**：7 行（`:13-21`）全有锚点。**无发现**。
5. **框架红线闸名**：R5b／R6／R8 真存在且 source 含 `execution`（`toml:103,110,122`）；`persistence` 面降维 AST 并写原因（E-9）。**无发现**（R7 并点的样板差异属可选，见 C-2）。
6. **不降级与静默禁令**：声明「合法降级路径：无」（`:93`）；机读信号配断言 `::execution_signal_present`（`:94`、`:115`）；红线 `arch/P7a-交接包与挂账清单.md` A-P7a-37 真实。**无发现**。
7. **验收测试**：每行绑 `tests/domains/test_v2_execution.py::<用例>`；【边界集】`:116`、【保留集】`:117` 两行齐。**无发现**。
8. **与闸的挂钩表**：已填（`:128-143`）；接不上闸的「人审」行写明原因（`:143`）。**无发现**。
9. **与 walk/ 决策冲突**：Q-A（并行）→行为 1；Q-B（原文落引用、窗口留摘要＋引用、替代渲染帽）→行为 4；Q-C（分开记）→行为 5，逐条一致（`walk/13-批量执行-查询执行.md:80-82`、`walk/裁决表.md:163-167`）；行为 3 失败语义已与「闸拒终局不回炉」钉死（E-5）。**无发现**。
10. **覆盖**：walk/13 Q1–Q3＋建议 1–6 与行为 1–12 一一对上；S1 M5「发现」已落地（E-7）；未见把别块的事写进本规格（answering 等只在「不做什么」排除）。**无发现**。
11. **总纪律残留**：`answered` 已锁为结构判定（`observation` 非空／`ref` 存在），无词表／正则语义判断；`recall_relevant` 词面门已去（E-6）。**无发现**。
12. **与模块卡一致**：职责（卡含「发现」→已落 `:88`）／公开接口（`-> ExecutionOutcome` 逐字一致）／依赖（卡已补 `persistence`，`specs/modules.md:222`）三项现均一致。**无发现**。

### C. 新增问题清单

1. **低｜R8 契约名与 source 未同步**：`tools/importlinter_v2.toml:120` 契约名仍写「preconditions/verification 不得引 gateway_adapter」，而其 `source_modules`（`toml:122`）已含 `appv2.runtimev2.execution`。`specs/execution.md:71` 对 source 的描述正确，但 §五「真源 R8 行同步」只在 source 侧同步、未改契约名字符串。属**真源侧**文案一致性，不阻塞本规格定稿；建议在闸侧补一次改名。
2. **低｜零 LLM 红线未并点 R7**：`specs/execution.md:71` 对零 LLM 面只点 R8（禁 `gateway_adapter`），未像样板 `specs/preconditions.md:62` 那样并点 R7（禁 `appv2.infra.llm_client`）。R7 的 `source_modules` 已含 `execution`（`toml:116`），禁令实际仍被强制，**非缺口**，仅样板一致性问题。

> 除上述两条外，改动未引入新的自相矛盾、悬空引用或覆盖漏洞；未发现真源里不存在的编号。

### 未验证清单 ＋ 覆盖自检

**未验证（不硬下结论）**
1. 边界闸 R6／R5b／R8「已真跑」的**当前绿色**未实跑验证（承上一轮）；本轮只核契约真存在＋ source 含 `execution`。
2. R8 **契约名字符串**是否会被某闸（`check_specs.py`／CI）逐字比对——未验证（未见此类校验），故 C-1 记为低。
3. `synth/S1` 表 A（E1→M2 澄清）与 M5 含「发现」并存、「发现」最终归块未回溯校正 S1（沿用上轮未验证项；本规格按卡＋`synth/S6` 落为 `execution` 职责）。

**覆盖自检**
- 已读文件（均本地实读）：`specs/execution.md`；判据 `docs/spec-process.md`、`docs/spec-format.md`；真源 `specs/modules.md`（`## execution`／`## tools`／`## persistence`／`## verification` 卡、R8）、`tools/importlinter_v2.toml`（R1/R2/R5b/R6/R7/R8）；样板 `specs/understanding.md`、`specs/preconditions.md`、`specs/tool_matching.md`；依据 `docs/runtime-refactor/arch/P4a1-票堆V2-46至50.md`、`walk/00-设计总纲.md`、`walk/13-批量执行-查询执行.md`、`walk/裁决表.md`、`synth/S6-事件与帧目录.md`。
- A 计数：**闭合 10／10**（未闭合 0、改了但不对 0）。
- B 计数：**12 条判据 0 红**。
- C 计数：**新增 2 条（均低）**。
- 机检：`uv run python tools/check_specs.py` ＝ **PASS（0 警告）**（本轮复审实跑）。

## §七 定稿（2026-10-15）

复审提的 2 条低已由 L0 收尾：**C-1** `importlinter_v2.toml` 的 R8 契约**名**同步为 `preconditions/verification/execution`（source 早已含 execution）；**C-2** 零 LLM 红线补注「**R7 亦覆盖本块**（本块不调模型，R7 天然满足）」。

**结论**：`specs/execution.md` ＝ **已定稿**。工序六步走完。
**登记待定**：大结果落引用的**阈值**＝阶段 5 事项（随真机数据定），本规格只写机制。
