- 日期：2026-10-15 ｜ 状态：**评审发现清单（待 L0 逐条处置）**
- 本清单只产发现，不修改任何现存文件。

---

## 一、结论摘要

1. **骨架站得住**：十节齐、标题逐字、无裸字面值、不做什么表锚点齐、不降级节有「合法降级路径：无」＋机读信号＋断言在场行——主干方向与 `walk/11` A/B/C、`裁决表` §06/§07/§11 一致，不需推翻。
2. **但闸层有一处 L0**：核心红线「只经 `tools` 公开面接触世界」挂的 `R7` 在唯一真源 `specs/modules.md` 里**不存在**（该文件边界规则只有 R1–R5），且 `importlinter_v2.toml` 里的 tools-only 契约 source 是旧包 `appv2.runtime`、**没有 runtimev2 版本**——「已真跑」为假（`specs/tool_matching.md:70,124`）。
3. **最要紧三条**：①R7 幻影闸＋「已真跑」虚报（L0，`tool_matching.md:70,124,130`）；②接口签名与模块卡不一致且自相矛盾（高，`tool_matching.md:39,63` vs `modules.md:176`）；③「工具描述写全」与已定稿 `specs/tools.md` 的披露纪律冲突（高，`tool_matching.md:80` vs `tools.md:50`）。
4. **共 14 条发现：L0 一条 ／ 高 2 条 ／ 中 7 条 ／ 低 4 条。**
5. **横向扫 17 卡**：`tool_matching` 卡依赖**漏 `prompts`**（同类遗漏）；`understanding` 卡（及 spec）**漏 `tools`**；均须回阶段 2 改卡。

---

## 二、发现清单表

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
| --- | --- | --- | --- | --- |
| F-01 | **L0** | **幻影闸＋虚报「已真跑」**：框架红线与挂钩表把「只经 `tools` 公开面」挂到「边界规则 R7」，但唯一真源 `specs/modules.md` 的 `## 边界规则` 只有 **R1–R5**，无 R6/R7；`R7` 仅存在于阶段 2 草案 `eng/00`（非真源）。同时 `tools/importlinter_v2.toml` 里「V2 runtime 只经 tools 接触世界」契约的 `source_modules=["appv2.runtime"]`（旧包），**无 `appv2.runtimev2` 版本**——本规格声称该红线「已真跑」不成立。此即本仓病史「闸自称存在实为未接线」（`eng/02:24`）。 | `specs/tool_matching.md:70,124,130`；`specs/modules.md:507-527`（R1–R5）；`tools/importlinter_v2.toml`「V2 runtime 只经 tools 接触世界」契约；`eng/00-阶段2-模块划分草案.md:90` | 把锚点改指真源：`specs/modules.md` 边界规则「`runtimev2` 各块引用 `tools` 以外引擎」行（未编号）；把 runtimev2 的 tools-only 契约落闸列为**出口条件**，`已真跑`→`待落闸`/`已真跑（旧包）/待迁移`。 |
| F-02 | **高** | **接口签名与模块卡不一致且自相矛盾**：spec 定义 `def match(state: RunState) -> ToolPlan \| ToolMatchRejection`，模块卡写 `def match(state: RunState) -> ToolPlan`；而 spec 自陈「签名以卡为准」（`tool_matching.md:63`）——自身打架，且 spec 新增的 `ToolMatchRejection/SubtaskMatch/RetrievalNeed/MatchReason` 卡内均无。 | `specs/tool_matching.md:39,56-63`；`specs/modules.md:176` | 回阶段 2 改卡（补拒因返回形与四类型），或按卡改 spec；二者取一，勿并存。 |
| F-03 | **高** | **「工具描述写全」与已定稿 `tools.md` 披露纪律冲突**：本规格要求每个工具描述含「何时用／不能做什么／参数示例」三件套（真源 `walk/11:77`），而 `specs/tools.md`（**已定稿**）行为 6 写「descriptors 渐进披露：只暴露名称／**一句话用途**／参数 schema／只读声明」。三件套与「一句话用途」是否同一字段、发现层是否扩披露，两处未对齐；spec 风险 2 只声明「不动 tools 公开接口签名」，未提此冲突。 | `specs/tool_matching.md:80,115`；`specs/tools.md:29,50`；`walk/11-匹配-工具阀.md:77` | 明确三件套落在 `ToolDescriptor.description` 还是发现层；回 `specs/tools.md` 同步披露纪律（该文为真源，冲突以它为准并改它 or 说明扩展）。 |
| F-04 | 中 | **把别的块的事写进来（且与 `synth/S1` 归属冲突）**：行为 11「聚合下推保留」按 `synth/S1` 归 **M5 批量执行**（V2-71 聚合下推），不属 M3 工具匹配；保留集测试还把 M3 的「名归一」与 M5 的「聚合下推」并成一行。 | `specs/tool_matching.md:85,108`；`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md:98`（M5→V2-71）；`arch/P5a2-票堆V2-70至73.md:32`（V2-71 涉 query 引擎面） | 移出「聚合下推」（或改述为本块只产 `plan.aggregate` 提议、库内算归 query/execution）；保留集测试拆两行。 |
| F-05 | 中 | **与 §12-A 口径张力**：`裁决表` §12-A 裁定语义归一「**上移到匹配相位（模型产出归一后的指标名/口径）**」，而行为 7 写「旧名／别名先由**本体账本归一**」，未写模型产出归一名的角色——照字面实现易滑成「程序/账本替模型做语义映射」，违总纪律与 §12-A。 | `specs/tool_matching.md:81`；`docs/runtime-refactor/walk/裁决表.md:148`（§12-A）；`walk/裁决表.md:99`（§07「旧名由本体账本归一＝结构约束」） | 写明「模型产出归一后名字；本体账本只提供 alias↔canonical 结构映射」，把语义判断留在模型侧。 |
| F-06 | 中 | **自相矛盾风险**：行为 4「禁英文列名」与行为 10「名归一闸（精确键未命中按名归一扫描）」都需字符串/形态处理（`arch/P3b` A-P3b-44：normalize 删装饰符号＋token 包含匹配），而验收行 `::no_lexicon_or_regex_in_tool_matching` 断言本模块**无词表/正则**——「结构归一」与「语义词表」边界未界定，两处直接打架。 | `specs/tool_matching.md:78,84,105`；`arch/P3b-票堆V2-35至45.md:137`（A-P3b-44 名归一实现） | 在 spec 界定 AST 扫描豁免面（本体账本归一属结构操作），或把名归一落 preconditions/别处并同步行为 10 与保留集。 |
| F-07 | 中 | **与 `CONTEXT.md` 真源冲突（职责边界）**：`CONTEXT.md` 说四相位①业务澄清的产物 `QuestionGroup` subtasks 已含 **`tool`**（`{id/question/ledger_notes/tool/chain}`），暗示选工具是澄清相位输出；而本 spec（与 `clarification.md`）把「子问题→工具」交给 tool_matching，且 `clarification.md` 的 `Subtask` **无 tool 字段**。三处口径不一致。 | `CONTEXT.md:22`；`specs/clarification.md:47-51`；`specs/tool_matching.md:9,75` | 回 Owner 定 `tool` 字段归属（澄清出 or 匹配出），同步 `CONTEXT.md`／`clarification.md`／本 spec。 |
| F-08 | 中 | **同批卡遗漏（横向扫 17 卡）**：`tool_matching` 卡依赖缺 **`prompts`**——它是调模型相位且消费提示词合同（`TOOLMATCH_CONTRACT` 在 `guide.py` → H9 `prompts`；`CONTEXT.md`「Skill 指南随指南装载进 clarify/**toolmatch** 相位」）。其余三个调模型相位（`understanding`／`clarification`／`answering`）卡都列了 `prompts`，唯 `tool_matching` 未列，spec 触及表同漏。 | `specs/modules.md:179`；`arch/P8b1-归因票病理.md:12`（TOOLMATCH_CONTRACT guide.py:67-79）；`synth/S1-...:44`（H9=prompts）；`CONTEXT.md:25` | **须回阶段 2 改卡**：给 `tool_matching` 卡补 `prompts` 依赖（spec「触及的模块」同步）。 |
| F-09 | 中 | **同批卡遗漏（横向扫 17 卡）**：`understanding` 卡（及 `understanding.md` 触及表）缺 **`tools`** 依赖，而 `understanding.md` 行为 5 明确直答结构核验的真源取 `tools` 的 `table_schema` 发现面（结构卡集合）——它消费 tools 公开面却没声明。 | `specs/modules.md:141`；`specs/understanding.md:69` | **须回阶段 2 改卡**：给 `understanding` 卡补 `tools`（公开面）。 |
| F-10 | 中 | **接口字段无行为/验收兜底**：`caliber_key` 出现在接口 `SubtaskMatch`（`tool_matching.md:50`）与降级信号句（`:90`），但行为约定与验收表无一条定义其语义、生成者与归一判据，也无测试覆盖。 | `specs/tool_matching.md:50,90`；`CONTEXT.md:30`；`arch/P3b-票堆V2-35至45.md:137`（A-P3b-41：caliber_key 由前置条件机三态处理） | 补 `caliber_key` 的生成/归一行为＋验收行，或明确注明「本块只透传、归 preconditions 承接」。 |
| F-11 | 低 | **闭环覆盖缺口（不确定）**：`synth/S1` 把 `V2-37 同参重投闸（决策出口）` 归 M3，本 spec 行为/验收无对应条目。 | `synth/S1-...:96`；`specs/tool_matching.md:73-108` | 确认同参重投是否本块责任；若是补行为与验收行，若否标注归属（state/orchestration）。 |
| F-12 | 低 | **框架红线缺闸名**：第 4 条「禁手写替代：不得自建模型客户端／自建工具目录」未写「对应闸名／验收写法」，而前三条都写了。 | `specs/tool_matching.md:71` | 补检测闸（B6「无旁路」行为测试/AST），与 `understanding.md:58` 同款。 |
| F-13 | 低 | **验收行对象不在本规格接口面**：`descriptor_covers_three_parts` 断言的是 `tools` 侧 descriptor，非本模块接口面（本块只消费 tools 公开面）。 | `specs/tool_matching.md:104`；`specs/modules.md:183`（Seam＝工具目录） | 明确该断言经 tools seam 测，或移入 `specs/tools.md` 验收。 |
| F-14 | 低 | **`QueryPlan` 真源疑似不全**：spec 行为 4 校验 plan（`metric_slot/ranking/direction…`）且声明 `QueryPlan` 只引不复述，但 `V2-71` 已给 `QueryPlan` 加 `aggregate: bool`，而 `specs/query.md` 的「QueryPlan 十字段」未含 `aggregate`。 | `specs/query.md:29-31`；`arch/P5a2-票堆V2-70至73.md:41,45`（A-P5a2-09／A-P5a2-13） | 确认 `specs/query.md` 是否补 `aggregate`；本 spec 若需校验该键则补行为与验收。 |

---

## 三、逐条回答 12 问

**Q1 十节齐 ＋ 标题逐字？——无发现。**
十节齐、标题逐字命中 `docs/spec-format.md` §二之二 的十个固定名：`## 目标`(7)｜`## 不做什么`(11)｜`## 触及的模块`(26)｜`## 接口定义`(36)｜`## 框架与依赖红线`(65)｜`## 行为约定`(73)｜`## 不降级与静默禁令`(87)｜`## 验收测试`(93)｜`## 依赖与风险`(110)｜`## 与闸的挂钩表`(118)。`状态: 草稿` 行在场（`:3`）。触及模块首列（tool_matching/parsing/gateway_adapter/state/tools）∈ `modules.md` 已声明。

**Q2 行为约定每条能否写成 `assert`？——基本合格，两点存疑。**
全篇无「尽量／合理／必要时／视情况」（grep 零命中）。逐条可断言（`:75-85`）。存疑：①行为 11 是他块之事（见 F-04），不是本块可断言行为；②行为 8「不做主动发现」、9「熔断暂不加」是范围否定句，与「不做什么」表重复（可断言但宜归位，非缺陷）。

**Q3 数字（裸字面值）？——无发现。**
grep `[0-9]` 仅命中标题/锚点，无裸限值；限额显式「引统一预算表…本规格不写字面值」（`:83`，真源 `裁决表.md:83` §06-A）。枚举 `data|knowledge`、`asc|desc` 为闭世界非数字。

**Q4 不做什么每条「由谁承担＋锚点」？——无发现（一处措辞小瑕）。**
10 行全部有锚点（`:15-24`），替代落点均点名模块（gate/clarification/preconditions/execution/tools/parsing/gateway_adapter）或指向裁决（`walk/11` §七 Q-B/Q-C、`walk/00` §二）。小瑕：熔断行「由谁承担」写「靠轮数闸兜底」，未点名模块（轮数闸实为 `state` 侧限额，可补）。

**Q5 框架与依赖红线：点名框架／唯一出口是否写对应闸名？——有 2 条发现。**
无点名框架✔（`:68`）。模型出口＝`gateway_adapter`→B6✔、禁 langgraph/langchain→R5b✔。**F-01**：tools-only 红线挂 `R7`（真源无此条、无 runtimev2 契约）。**F-12**：第 4 条「禁手写替代」无闸名。

**Q6 不降级与静默禁令？——无发现。**
合法降级路径声明「无」✔（`:89`）；「如实上报」配机读信号（step payload 拒因字段＋notice，类型取自 `S6`，`:90`，`S6:23` 证 notice 类型真实）＋验收断言在场行 `::rejection_signal_present`（`:106`）✔；静默禁令引红线原文 `arch/P7a` A-P7a-37（`:91`，`P7a:98` 核实原文在场）✔。

**Q7 验收测试：每行有标识／边界集保留集／有无测不出东西的行？——有 2 条发现。**
每行反引号测试标识✔；边界集（`:107`）与保留集（`:108`）两行齐✔。**F-13**：`:104` 断言对象在 tools 面（非本规格接口面）。**F-04**：`:108` 混入 M5 的聚合下推。

**Q8 与闸的挂钩表？——已填，有一行错（F-01）。**
表在场且逐条填（`:120-130`）；末行「纯范围排除→人审」写了接不上的原因且理由站得住✔。但「只经 tools 公开面→边界闸 R7→已真跑」错（F-01）；`R1/R7` 同指（`:130`）同病。

**Q9 与 `walk/` 决策是否冲突？——1 条张力（F-05）。**
语义交模型✔（`:24,75`）；前置三态归 preconditions✔（`:17`）；统一预算表数值不复制✔（`:83`）；「出数只认现行口径」为结构约束✔（`:81`，`裁决表:99` §07）。张力：§12-A「模型产出归一后的指标名」vs 行为 7「账本归一」未写模型角色（F-05）。核验零模型／真流式／重写不是改不涉本块。

**Q10 覆盖：`walk/11` Q1–Q3、D1–D6、`synth/S1` M3？——Q1–Q3 与 D1–D6 全覆盖；1 处越界＋1 处可能漏。**
Q1 描述写全→行为 6＋`:104`✔；Q2 熔断→「不做什么」＋行为 9✔；Q3 主动发现→「不做什么」＋行为 8✔。D1 闭世界对账✔／D2 拒因回喂不修补✔／D3 参数必填✔／D4 描述写全✔／D5 熔断保持✔／D6 不做发现✔。**越界（F-04）**：聚合下推属 M5。**可能漏（F-11）**：M3 证据列 V2-37 同参重投闸无对应条目。

**Q11 总纪律残留（程序替模型判语义）？——1 条发现。**
无「词表/正则猜该配哪个工具」设计✔（`:24,75,116`）。**F-06**：行为 4「禁英文列名」＋行为 10「名归一扫描」需形态处理，与 `::no_lexicon_or_regex_in_tool_matching` 的「无词表/正则」断言边界未界定（自相矛盾风险）。

**Q12 与模块卡一致？——2 条不一致，标须回阶段 2 改卡；横向扫 17 卡另有同类遗漏。**
①**签名不一致**（F-02）：spec `-> ToolPlan | ToolMatchRejection` vs 卡 `-> ToolPlan`——**须回阶段 2 改卡**（或改 spec）。
②**依赖**：卡（`state/parsing/gateway_adapter`＋`tools`）与 spec「触及的模块」表**一致**——即阶段 2 侧「补 `parsing`／`gateway_adapter`」的改动与规格一致✔。
③**横向扫 17 卡同类遗漏**：`tool_matching` 卡**漏 `prompts`**（F-08）、`understanding` 卡**漏 `tools`**（F-09）——均**须回阶段 2 改卡**。（`clarification` 是否漏 `tools`（discover 面）见未验证清单。）

---

## 四、未验证清单 ＋ 覆盖自检

**未验证（查了什么、查到什么程度）**

1. **runtimev2 的 tools-only 边界是否已有别的契约兜底**：已通读 `tools/importlinter_v2.toml` 全文——仅有 R1–R5b 六条 runtimev2 契约，未见「runtimev2 禁引 knowledge/query/retrieval」；但**未跑 import-linter 实测**，只读契约文件。
2. **`specs/tools.md` 的 `description` 字段与「一句话用途」是否为同一载体**：只读 `tools.md:29,50` 原文判定冲突，未读 `appv2/tools` 实现。
3. **`clarification` 是否应依赖 `tools`**：其 spec 行为 5「先探后问 discover」理论上消费 tools（`CONTEXT.md:20`），但 spec/卡都未列——**存疑，未定论**，故未计入发现。
4. **`synth/S1` M3 证据列 `V2-24 doc_retrieve 零选中`／`V2-29 槽位归一`／`V2-52` 是否有对应条目**：只核到 V2-41（名归一）与本块有关，V2-24/V2-29/V2-52 未逐票读，未据此下结论。
5. **`walk/` 其余 16 篇全文**：本块相关只实读 `walk/11`、`walk/00`、`裁决表.md`，其余经 `裁决表.md`／`S1` 摘要采信。
6. **本仓 `importlinter` 是否在 CI 真跑**：未重核 CI 配置（沿用 `eng/02` 结论：边界闸在 CI），未实测。

**覆盖自检**

- **已实读文件**：`specs/tool_matching.md`（主对象，全文）；`docs/spec-process.md`（§三判据清单）；`docs/spec-format.md`；`docs/runtime-refactor/walk/11-匹配-工具阀.md`、`walk/裁决表.md`、`walk/00-设计总纲.md`；`specs/modules.md`（17 卡＋边界规则，全文）；`specs/query.md`、`specs/tools.md`；`specs/understanding.md`、`specs/clarification.md`；`CONTEXT.md`（全文）；`docs/runtime-refactor/synth/S1`、`synth/S6`（相关节）；`arch/P7a`（A-P7a-37 核实）、`arch/P3b`（V2-41 节）、`arch/P5a2`（V2-71 节）、`arch/P8b1`（相关条目）；`eng/01-阶段2评审发现清单.md`、`eng/02-规格防漂移要求.md`；`tools/importlinter_v2.toml`（全文）、`tools/check_specs.py`（全文）。
- **发现条数**：14 条。
- **按严重度计数**：**L0 1 条 ｜ 高 2 条 ｜ 中 7 条 ｜ 低 4 条**。
- **12 问逐条回答**：Q1–Q12 全部作答，每条带 `file:line` 或 `file#节` 锚点；无锚点条目已剔除。

---

## 五、L0 逐条处置（2026-10-15）

> 主窗已独立核验 L0 那条（F-01）：`specs/modules.md` 边界规则确只有 R1–R5（R7 只活在阶段 2 草案 `eng/00`），`tools/importlinter_v2.toml` 的 tools-only 契约 `source_modules` 确为旧包 `appv2.runtime`。**指控成立——这是我的错。**

| 编号 | 严重度 | 处置 | 落点 |
| --- | --- | --- | --- |
| F-01 | **L0** | **采纳→已修（闸侧）＋交修订步（规格侧）** | 闸侧：`specs/modules.md` 把 tools-only 那行**编号为 R6**；`tools/importlinter_v2.toml` **新增 R6 契约**（source＝runtimev2 十七块，forbidden＝knowledge/query/retrieval），**探针验证会咬人**（埋违规→BROKEN，拆掉→16 条 KEPT）。规格侧：交修订步把引用由 `R7` 改为 `R6`，并把「已真跑」改为「已真跑（R6 契约，探针验证过）」 |
| F-02 | 高 | **采纳→回阶段 2 改卡（已完成）** | `tool_matching` 卡签名补 `-> ToolPlan \| ToolMatchRejection`（并点出 `ToolPlan`／`ToolMatchRejection` 两个形）；spec 侧同步交修订步 |
| F-03 | 高 | **采纳→交修订步；并牵动已定稿 `specs/tools.md`** | 三件套的载体＝`ToolDescriptor.description`（**模型选工具时看到的就是它**），故须进 `descriptors()`；`specs/tools.md` 行为 6 要补三件套。**该文为已定稿 spec，属变更路由，须 Owner 知悉后再改** |
| F-04 | 中 | **采纳→交修订步** | 移出「聚合下推」（归 `execution`／M5）；保留集测试拆两行 |
| F-05 | 中 | **采纳→交修订步** | 写明「**模型产出归一后的名字**；本体账本只提供 alias↔canonical 的**结构映射**」——把语义判断留在模型侧（对齐 §12-A 与 §07） |
| F-06 | 中 | **采纳→交修订步** | 界定 AST 扫描豁免面：**结构归一（形态处理）不算语义词表**；并把「禁英文列名」改述为形态判定 |
| F-07 | 中 | **不自行裁决 → 升 Owner** | `tool` 字段归属三处口径不一（`CONTEXT.md:22` 说 `QuestionGroup.subtasks` 含 `tool`；`clarification.md` 的 `Subtask` 无 `tool`；本 spec 把选工具放 `tool_matching`）。**须 Owner 定「选工具是澄清出还是匹配出」**，再同步三处 |
| F-08 | 中 | **采纳→回阶段 2 改卡（已完成）** | `tool_matching` 卡依赖补 `prompts`（它是调模型相位，消费提示词合同） |
| F-09 | 中 | **采纳→回阶段 2 改卡（已完成）** | `understanding` 卡依赖补 `tools`（其直答结构核验读结构卡集合） |
| F-10 | 中 | **采纳→交修订步** | 明确 `caliber_key` **本块只透传**、归一判据归 `preconditions` 承接，并补一句行为 |
| F-11 | 低 | **采纳→交修订步** | 标注 `V2-37` 同参重投闸的归属（属 `orchestration`／`state` 的限额面），或补行为＋验收 |
| F-12 | 低 | **采纳→交修订步** | 第 4 条「禁手写替代」补对应闸名（B6 无旁路断言） |
| F-13 | 低 | **采纳→交修订步** | 标注该断言**经 tools seam 测**（或移入 `specs/tools.md` 验收） |
| F-14 | 低 | **采纳→交修订步** | `QueryPlan` 真源以 `specs/query.md` 为准；若该文缺 `aggregate` 字段则**回阶段 3 补**，本块只引不复述 |

**处置统计**：采纳 13 条（其中回阶段 2 改卡 3 条已完成、闸侧 1 条已完成、余 9 条交修订步）；升 Owner 1 条（F-07）。

**给修订步的修复单**：F-01（规格侧）／F-02／F-03／F-04／F-05／F-06／F-10／F-11／F-12／F-13／F-14，共 11 处。
**给 Owner 的**：F-07（`tool` 字段归属）。
