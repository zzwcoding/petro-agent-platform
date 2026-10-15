- 日期：2026-10-15 ｜ 状态：**评审发现清单（待 L0 逐条处置）**
- 本清单只产发现，不修改任何现存文件。

## 一、结论摘要

1. 版式骨架合格：十节齐、标题逐字、顺序正确；`spec gate`（`tools/check_specs.py`）本地实跑 PASS（0 警告）。
2. 三类高危中，**「指向不存在的真源」本轮未复发**——`tools/ref_resolvable.py check` 实跑绿（12 份规格 0 违规），R5b／R6／R7 编号真存在且 source 均含 `appv2.runtimev2.answering`（`toml:103/:110/:116`）；P7a-37 红线引文核实一致（`arch/P7a-交接包与挂账清单.md:98`）。
3. 但**闸覆盖有部分不实**：`R7`／`R6` 被用来声称的面比契约实际 forbidden 面更宽，且挂钩表出现一条本规格并不涉的工具面硬要求（照搬 `execution` 样板残留）。
4. 与模块卡**一处不一致**：规格依赖含 `transport`，卡 `## answering` 的「### 依赖」没有——须回阶段 2 改卡。
5. 与 `execution.md` 的「大结果落引用」责任方一致（无踢皮球）；仅 `MaterialRef` 字段口径未在作答块显式承接（非硬冲突）。

## 二、发现清单表

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| A-1 | 中 | **与模块卡依赖不一致**：本规格「触及的模块」把 `transport` 列为改动模块（「本块只经其公开面」）、「依赖」与行为 1／红线 65 行都要经 `transport` 发 `text` 帧；但真源卡 `## answering`「### 依赖」只列 `context`／`prompts`／`gateway_adapter`／`state`，**无 `transport`**。规则：以卡为准并标「须回阶段 2 改卡」 | `specs/answering.md:32,:65,:108`；`specs/modules.md:240-242`（卡依赖）；对照 `specs/execution.md:121`（execution 依赖与卡一致，含 transport） | 采纳：加注「须回阶段 2 改卡（`## answering` 依赖补 `transport`）」；或若判本块不直依 transport，则删本规格 transport 依赖并改由 `orchestration` 落帧 |
| A-2 | 中 | **数字裸值**：行为 10「答案要求（**7 条**）」未给 `文件#节` 真源锚点（只写「以 `prompts` 的合同文本为唯一真源」，而 `prompts` 是模块非文件、卡里也未列条数）。违反版式 §二 6「数字只许引真源，禁写裸字面值」 | `specs/answering.md:79`；现状真源 `docs/runtime-refactor/recon/L2b-作答装配与回声.md:25`（`_ANSWER_REQUIREMENTS` 7 条）；对照 `specs/preconditions.md:70`（8 判定位已锚 `synth/S3` C-01） | 采纳：给「7 条」补 `文件#节`（现状锚 L2b，或注明 V2 真源待 `prompts` 合同定稿），照 preconditions 样板 |
| A-3 | 中 | **R7 部分覆盖**：`R7 契约`被用来声称「模型调用只经 `gateway_adapter`」，但 R7 forbidden 面只有 `appv2.infra.llm_client`（不含「经其它 infra 面调模型」等旁路）。样板对同一红线补了「**＋一条「无旁路」行为断言**」（写法照 tool_matching），本规格未补，单靠 R7 不足 | `specs/answering.md:63,:121`；`tools/importlinter_v2.toml:113-117`（R7 forbidden=llm_client）；`specs/modules.md:526`；样板 `specs/understanding.md:62`、`specs/tool_matching.md:77` | 采纳：照样板补「无旁路」行为断言（或红线写法注明 R7 只覆盖直引面） |
| A-4 | 中 | **挂钩表覆盖声明不实**：挂钩表列「只经 `tools` 公开面接触引擎｜边界闸 R6」并称「接不上闸的部分（…只经 tools／transport）已由 R1／R6 覆盖」——但（a）本规格红线与依赖**并不涉 `tools`**（红线只写 `transport` 公开面），该行系照搬 `execution` 样板的硬要求；（b）**`transport` 公开面无任何边界闸覆盖**，R6 forbidden 面是引擎（knowledge/query/retrieval），与 transport 无涉 | `specs/answering.md:123,:128`；`tools/importlinter_v2.toml:107-111`（R6 forbidden=引擎）；本规格红线清单 `specs/answering.md:62-66` 无 tools 项 | 采纳：删/改 :123 行（本规格不涉 tools）；:128 覆盖声明改写——「只经 transport 公开面」目前无闸，应标明「无边界闸→AST 断言或人审＋原因」，不得归 R6 |
| A-5 | 低 | **锚点悬空**：`## 不做什么`「大结果原文的落盘与引用载体」行锚点写「评审 E-10 处置」，未指明文件；读者无法直接定位 | `specs/answering.md:17`；对应 `docs/runtime-refactor/spec-review/execution-评审.md:103`（E-10＝落引用责任方） | 采纳：补文件路径（`spec-review/execution-评审.md` E-10） |
| A-6 | 低 | **跨块字段口径未显式对齐**：`execution` 定义 `MaterialRef{handle,summary,row_count}` 且 `Observation.ref` 携带；本规格 `Citation` 只有 `seq`＋`locator`，大结果引用的 `handle` 在作答块无字段承接（经 `seq → observation.ref` 可达，非硬冲突，但两文未声明同一口径，与 §14-B「合并」要求不符） | `specs/execution.md:51-53,:58`；`specs/answering.md:46-48`；`walk/裁决表.md:176`（§14-B） | 采纳（弱）：在 `Citation` 或说明处注明「大结果引用经 `seq→Observation.ref` 取 handle」，或补一个可选 `ref` 字段 |
| A-7 | 低 | **红线句式偏离样板**：`## 框架与依赖红线` 的 R7 行缺样板都有的「验收写法：…」子句；「禁手写替代」行未给对应闸名（样板给 R7＋R6） | `specs/answering.md:63,:66`；样板 `specs/understanding.md:62`、`specs/tool_matching.md:80`、`specs/clarification.md:73` | 采纳：照样板补「验收写法」与「禁手写替代」的对应闸名 |
| A-8 | 低 | **机读信号未引真源**：`## 不降级与静默禁令` 列 `text`／`citation`／`verdict` 事件但未引事件目录真源；样板同类句均引 `synth/S6-事件与帧目录.md` | `specs/answering.md:84`；样板 `specs/clarification.md:97`、`specs/preconditions.md:95`、`specs/understanding.md:89` | 采纳：补引 `docs/runtime-refactor/synth/S6-事件与帧目录.md` |
| A-9 | 低 | **职责归属含混**：行为 4「每次模型调用都有 Manifest」是 `context` 的产出（卡 `## context` 测试计划即此项），却写成本块行为约定并挂本块验收；与 `## 不做什么`「材料段与 Manifest 的编译→`context`」并存，易读成两处皆负 | `specs/answering.md:73,:94`；`specs/modules.md:375-393`（context 卡）；`specs/answering.md:18` | 采纳：改写为「消费 `context` 编译出口：Manifest 必须在场（缺失＝判失败）」，明确本块只断言不实现 |
| A-10 | 低 | **`verdict` 帧归属未明**：行为 7 把「`verdict` 帧」与 citation 帧、链尾同批落定纳入本块收口，但裁决产出（`Verdict`）归 `## verification`；两处归属未指明协调方（`orchestration`？），有踢皮球风险 | `specs/answering.md:76`；`specs/modules.md:249-257`（verification 卡）、`specs/modules.md:290-309`（orchestration） | 采纳（弱）：注明「帧的批次落定由 `orchestration` 协调；本块只保证自产部分就位」 |

## 三、14 问逐条回答

**1 十节齐＋标题逐字？** 无发现。`## 目标`／`## 不做什么`／`## 触及的模块`／`## 接口定义`／`## 框架与依赖红线`／`## 行为约定`／`## 不降级与静默禁令`／`## 验收测试`／`## 依赖与风险`／`## 与闸的挂钩表` 十节齐、逐字、顺序与 `docs/spec-format.md:16-27` 一致；`spec gate` 本地实跑 PASS（0 警告）。

**2 行为约定每条能否写成 assert？含糊词？** 无发现（判 FAIL 的含糊词「尽量／合理／必要时／视情况」全文 0 命中；`:128` 出现「等」但在挂钩表说明行、非行为约定）。逐条可判：真流式＝帧计数；引标解析＝序号集合判定；空稿不推＝输出判定。

**3 数字有无裸值？** 有发现——A-2（`:79`「7 条」无 `文件#节`）。

**4 不做什么每条有无「由谁承担＋锚点」？** 基本齐（`:15/:16/:18/:19/:20/:21` 均带模块＋`specs/modules.md` 卡锚点）；一处弱——A-5（`:17`「评审 E-10 处置」未指明文件）。

**5 框架红线是否写对应闸名、闸名真存在、source 真覆盖 answering？** 闸名真存在且 source 真覆盖 answering：R7 `toml:116`、R5b `toml:103`、R6 `toml:110` 的 `source_modules` 均含 `appv2.runtimev2.answering`；R6 forbidden＝引擎、R5b forbidden＝框架、R7 forbidden＝`appv2.infra.llm_client`，「对应于哪个面」对得上红线意图。但有**部分覆盖**（A-3）与**覆盖声明不实**（A-4）。

**6 不降级与静默禁令？** 无发现。`:83` 明写「合法降级路径：无」；`:84` 列机读信号（`text`／`citation`／`verdict` 帧＋step payload `citations`／`gaps`）；`:102` 有「信号在场」断言行。仅 A-8（未引 S6 真源）为写法瑕疵。

**7 验收测试（每行标识／边界集保留集／测不出的行）？** 无发现。14 行全部有 `tests/domains/test_v2_answering.py::<id>` 标识；`:103`【边界集】、`:104`【保留集】两行俱在；逐行可判（含 AST 行 `:101`）。无空判行。

**8 挂钩表（填了没／「已真跑」属实否）？** 填了；`spec gate`／R5b／R6／R7 行「已进 CI／已真跑」属实——`uv run lint-imports --config tools/importlinter_v2.toml` 实跑 18 契约全 KEPT（含 R5b／R6／R7；answering 目录为占位，契约空过）。但 A-4：`:123` 挂的 tools 面硬要求本规格并不涉、`:128` 覆盖声明把 transport 面错归 R6。

**9 与 `walk/` 决策冲突？** 无冲突。逐条比对 `walk/14`：Q-A 真流式→行为 1 `:70`；Q-B Manifest＋大结果落引用→行为 4 `:73`；Q-C 结构化缺口→行为 5 `:74`＋`Gap.kind` 闭世界 `:49-51`。与 `walk/裁决表.md:171-179` §14-Owner 裁决一致；与总纲 §二（`:21` 声明不拿词表判语义）一致。

**10 覆盖（walk/14 Q1–Q3、建议 1–5、S1 M6、有无越界）？** 无漏项/无越界发现。Q1–Q3＝行为 1／4／5；建议 1–5 逐条落（1→`:70-71`、2→`:73`、3→`:74`、4→`:72/:75/:76/:77`、5→`:75`）。`synth/S1` M6（`:29`「起草（指令装配＋材料渲染）＋答案收口与引用块落账」）——起草的「指令装配／材料渲染」在 `## 不做什么` `:18/:19` 显式分派给 `context`／`prompts`，收口与引用落账由本块承担（`:76`），无遗漏。越界：A-9／A-4 属「把 context／execution 样板的事写进来」的轻度表现。

**11 总纪律残留（程序替模型判语义）？** 无发现。`:21` 明写「拿词表／正则猜『答没答上』→交模型与 `verification`，程序只做结构判据」；`:101` 挂 AST 机检行；行为 3／6／7 均为结构判（引标在场／分源列明／同批落定）。

**12 与模块卡一致（职责／公开接口／依赖）？** 接口与职责一致（卡签名 `def answer(state: RunState) -> AnswerDraft: ...`＝规格 `:37`；职责「起草／真流式收口／引用落账」＝卡 `:232`）。**依赖不一致**：A-1（卡缺 `transport`）→ 标「须回阶段 2 改卡」。另 A-10（`verdict` 帧归属）。

## 附加 13、与五份已定稿样板写法一致性

`synth/` 前缀、`边界集／保留集`、`AST 机检行豁免面`、挂钩表列式均一致；`AST` 行 `:101`「（AST 扫描；豁免面＝形态处理／集合成员判定）」与 `specs/execution.md:109`、`specs/preconditions.md:112` 同款。**不一致 3 处**：A-7（缺「验收写法」子句＋「禁手写替代」无闸名）、A-8（机读信号未引 `synth/S6`）、A-1（依赖口径与 execution 样板不同：execution 依赖与卡一致，answering 多 transport）。

## 附加 14、跨块一致性（与 `specs/execution.md`）

- **落引用责任方：一致，无踢皮球。** `execution.md:89`「由本块（`execution`）落、`persistence` 为引用载体；`answering` 只消费引用、不重复落」；`answering.md:17`「`execution` 落、`persistence` 为载体（本块只消费引用）」——同一口径，符合 `walk/裁决表.md:176` §14-B「与 §13-B 合并」。
- **引标序号口径：一致。** `execution` `Observation.seq`＝「全局 [n] 序（引标与答案引用同一套序号）」＋`Observation.source`＝「台账行／片段→报告→库／表名」（`execution.md:39,:57,:58`）；`answering` `Citation.seq`＝「＝观察序号」、`Citation.locator`＝同款出处描述（`answering.md:46-48,:71`）。无冲突。
- **`MaterialRef` 口径：未显式对齐（A-6）。** `execution` 用 `MaterialRef{handle,summary,row_count}` 承载大结果引用，`answering` 的 `Citation` 无 handle 字段；经 `seq→Observation.ref` 可达，非硬冲突，但两文未声明同一取用口径。**报 A-6（低）。**

## 四、未验证清单 ＋ 覆盖自检

**未验证**（已声明，不编造）：

1. `prompts` 合同文本（答案要求 7 条的 V2 真源）尚未存在实体文件，A-2 只能指现状真源 `recon/L2b`（推测 V2 真源将落 `## prompts`，未在卡中确认条数）。
2. `answering` 目录仅占位 `__init__.py`，`tests/domains/test_v2_answering.py` 不存在（阶段 5 承诺）——验收测试行无法实跑，仅核标识形态。
3. R5b／R6／R7「已真跑」为契约空过（answering 无实现代码）——已实跑 `lint-imports` 确认契约存在且 KEPT，但「answering 实现层是否真合规」未验证（阶段 5 才有对象）。
4. `import-linter` `forbidden` 的 `allow_indirect_imports` 默认语义（R7 未显式设值）对「间接引用是否被判」的影响，未实测（仅据 R5b／红线①注释「直接引用才违规」旁证）。

**覆盖自检**——实读文件清单：

- 评审对象：`specs/answering.md`（全文 129 行）。
- 判据／版式：`docs/spec-process.md`（§三）、`docs/spec-format.md`。
- 决策：`docs/runtime-refactor/walk/14-作答-汇总作答.md`、`walk/裁决表.md`、`walk/00-设计总纲.md`。
- 模块与边界：`specs/modules.md`（answering／context／transport／persistence／verification／prompts 卡＋边界规则 R1–R8）。
- 现状／证据：`recon/L2b-作答装配与回声.md`、`recon/H-观察核验作答与图装配.md`、`arch/P4b-票堆V2-56至65.md`、`arch/P5a1-票堆V2-66至69.md`、`arch/P7a-交接包与挂账清单.md`、`synth/S1-重写单元与证据交叉矩阵.md`。
- 样板：`specs/understanding.md`／`clarification.md`／`tool_matching.md`／`preconditions.md`／`execution.md`。
- 闸：`tools/importlinter_v2.toml`、`tools/ref_resolvable.py`、`tools/check_specs.py`（实跑 `ref_resolvable check`＝绿、`check_specs`＝PASS、`lint-imports`＝18 契约 KEPT）。
- 跨块对照：`docs/runtime-refactor/spec-review/execution-评审.md`（E-10）。

**计数**：共 **10 条** 发现——`L0×0`／`高×0`／`中×4`（A-1～A-4）／`低×6`（A-5～A-10）。

---

## §五 L0 逐条处置（2026-10-15）

> **本轮三件值得记的事**：①「指向不存在的真源」**未复发**（新闸 `ref_resolvable` ＋ 评审双验）；②**L0／高均为 0**——前十块的两类高危形态这轮都没出；③跨块一致性（与已定稿 `execution.md` 的落引用责任方）**已对上**，说明前几轮定下的口径在起作用。10 条**全部采纳**。

| 编号 | 严重度 | 处置 | 落点 |
| --- | --- | --- | --- |
| A-1 | 中 | **采纳→回阶段 2 已改卡** | `## answering` 卡依赖补 `transport`（`text` 帧的增量发射，只经其公开面） |
| A-2 | 中 | 采纳→修订步 | 行为 10 的「答案要求 **7 条**」**补 `文件#节` 锚点**（现状锚 `docs/runtime-refactor/recon/L2b-作答装配与回声.md`），或注明「V2 真源待 `prompts` 合同定稿」——**不许留裸数字** |
| A-3 | 中 | 采纳→修订步 | 红线 R7 行**补「验收写法」子句 ＋ 一条「无旁路」行为断言**（写法照 `tool_matching`／`understanding`）——单靠 R7 是**部分覆盖** |
| A-4 | 中 | 采纳→修订步 | **挂钩表修正**：(a) 删掉照搬的「只经 `tools` 公开面｜R6」行（本规格不涉 `tools`）；(b) **如实写明「`transport` 公开面当前无边界闸覆盖」**（R6 的 forbidden 是引擎，与 transport 无涉），并按 `docs/spec-format.md` §五 降维为 AST／断言或标人审 |
| A-5 | 低 | 采纳→修订步 | 「大结果落引用」行的锚点补文件路径（`spec-review/execution-评审.md` E-10） |
| A-6 | 低 | 采纳→修订步 | `Citation` 处注明「**大结果引用经 `seq → observation.ref`（`MaterialRef`）可达**」，与 `execution` 的字段口径显式对齐（`walk/裁决表.md` §14-B） |
| A-7 | 低 | 采纳→修订步 | 红线补样板的「验收写法：…」子句；「禁手写替代」行补对应闸名 |
| A-8 | 低 | 采纳→修订步 | 「不降级与静默禁令」的事件类型**补引真源** `synth/S6-事件与帧目录.md` |
| A-9 | 低 | 采纳→修订步 | 行为 4 改写为「**消费 `context` 编译出口**：Manifest 必须在场（缺失＝判失败）」——本块只断言、不实现 |
| A-10 | 低 | 采纳→修订步 | 行为 7 注明「`verdict` 帧的**批次落定由 `orchestration` 协调**；本块只保证自产部分就位」 |

**给修订步的修复单**：X-1…X-9（对应 A-2…A-10）。A-1 已由阶段 2 改卡办结。
**给 Owner 的**：无。

---

## §六 复审（2026-10-15）

> 复审对象＝修订后 `specs/answering.md`（129 行）。只读核实，不采信回执自述。两道闸实跑：`ref_resolvable` 绿、`check_specs` PASS（附跑 `lint-imports` 18 KEPT）。

**结论**：X-1…X-9 逐条到文件核验，**8 条闭合、1 条「改了但不对」（X-3）、0 条未改**（A-1 已由阶段 2 改卡办结，卡与规格依赖口径现已一致）；12 条判据**无硬红**，十节标题仍逐字、四处口径（接口／行为／验收／挂钩表）一致，未发现新增悬空引用或覆盖漏洞；**唯一新问题**是 X-3 落笔的「`transport` 公开面**无任何**边界闸覆盖」与真源 `R2` 契约不符（R2 已覆盖「只经 `transport` 包根」这一半）。**够「可定稿」的前提是先改这一处措辞**——其余无须回炉。

### A. 逐条闭合核对表

| 条目 | 闭合？ | 证据锚点 | 备注 |
|---|---|---|---|
| X-1（A-2） | **闭合** | `specs/answering.md:80`：条数现状真源＝`docs/runtime-refactor/recon/L2b-作答装配与回声.md`（`_ANSWER_REQUIREMENTS`，现 **7 条**） | 复核锚点真存在：`recon/L2b-作答装配与回声.md:25` 节标题 `### _ANSWER_REQUIREMENTS…7 条`。写法照 `specs/preconditions.md:70`（`synth/S3` C-01）同款。**未采「去裸数字」写法但已非无出处裸数字**，可接受 |
| X-2（A-3） | **闭合** | `specs/answering.md:64`：补「验收写法：模型调用点只出现在该出口 ＋ 调用行为测试绿」＋「一条『无旁路』行为断言（写法照 `specs/tool_matching.md` 同款）」 | 与样板逐字同款：`specs/understanding.md:62` 完全一致 |
| X-3（A-4） | **改了但不对** | (a) tools/R6 行已删：`specs/answering.md:124` 现为 transport 行；红线清单 `:64-:67` 无 tools 项——**处置正确**。(b) 但「`transport` 公开面**无任何**边界闸覆盖」（`:67`／`:124`）**不实**：`tools/importlinter_v2.toml:74-78` **R2 契约**（source 含 `appv2.runtimev2.answering`，forbidden 含 `appv2.runtimev2.transport.*`）即禁业务相位引 `transport` 深层子模块＝「只经 transport 包根」。`:124` 理由句「R1–R8 的 forbidden 面无『`transport` 公开面』一面」亦不实 | 详见 C-1。回执 §四.2 已自认张力却按住「无闸」落笔，属取舍不当 |
| X-4（A-5） | **闭合** | `specs/answering.md:17`：已补文件路径 `docs/runtime-refactor/spec-review/execution-评审.md` E-10 | — |
| X-5（A-6） | **闭合** | `specs/answering.md:57`：新增「大结果引用经 `seq → observation.ref`（`MaterialRef`）可达…与 `specs/execution.md` 字段口径显式对齐（真源 `walk/裁决表.md` §14-B）」 | §14-B 真源存在（`walk/裁决表.md` §14 行 B） |
| X-6（A-7） | **闭合** | `specs/answering.md:67`：禁手写替代行补对应闸名（R7）＋验收写法「无旁路」；`:65` R5b 行补「（框架只许在 `orchestration`）」 | 句式对齐样板 |
| X-7（A-8） | **闭合** | `specs/answering.md:85`：事件类型补引 `synth/S6-事件与帧目录.md` | 复核 `docs/runtime-refactor/synth/S6-事件与帧目录.md` 存在；写法照 `specs/execution.md:88` 同款 |
| X-8（A-9） | **闭合** | `specs/answering.md:74`：改写为「本块只消费 `context` 的编译出口、只断言不实现」＋「每次模型调用必须有 Manifest 在场…Manifest 的编译归 `context`」 | — |
| X-9（A-10） | **闭合** | `specs/answering.md:77`：「`verdict` 帧的批次落定由 `orchestration` 协调，本块只保证自产部分（引用块／`citation` 帧）就位」 | — |

### B. 12 条判据复跑结论

1. **十节齐＋标题逐字**：无发现。十节标题 `:7/11/23/34/61/69/82/88/107/116` 逐字、顺序与 `docs/spec-format.md` §二之二一致；`check_specs` 实跑 PASS（0 警告）。
2. **行为约定可写 assert／含糊词**：无发现。`尽量／合理／必要时／视情况` 全文 0 命中；`拒/缺失/未及核验` 等为闭世界取值非含糊词。
3. **数字裸值**：无发现。唯一实数「7 条」`:80` 已锚 `recon/L2b`（`_ANSWER_REQUIREMENTS`）；其余均为编号（R1–R8／B6／R5b／M6／§14-B／A-P7a-37）。
4. **不做什么每条有「由谁承担＋锚点」**：无发现。`:15-:21` 每条均带模块＋锚点；`:17` 已补 E-10 文件路径。
5. **框架红线闸名**：有发现（＝X-3 的 transport 面，非本修订新增的其余红线）。R7/R5b/R6 编号真存在且 `source_modules` 含 `appv2.runtimev2.answering`（`toml:116/:103/:110`）；但 transport 行的「对应闸名＝无」声明不实（R2 部分覆盖），见 C-1。
6. **不降级与静默禁令**：无发现。`:83` 明写「合法降级路径：无」；`:84` 机读信号＋真源 S6；`:103` 配「信号在场」断言。
7. **验收测试**：无发现。14 行均绑 `test_v2_answering.py::<id>`；`:104`【边界集】、`:105`【保留集】俱在；`AST 扫描豁免面` 行 `:102` 与样板同款。
8. **挂钩表**：有发现。已填；tools/R6 行已删（处置正确）；但 `:124` transport「无闸」与 `:129` 措辞不实（见 C-1）。「已真跑」属实——`lint-imports` 实跑 **18 契约全 KEPT**（含 R2/R5b/R6/R7）。
9. **与 `walk/` 决策冲突**：无发现。`walk/裁决表.md` §14 A/B/C ↔ `:70/:74/:75`；总纲 §二 ↔ `:21`。
10. **覆盖（walk 节点／S1 单元／越界）**：无发现。`synth/S1` M6 复核存在（`synth/S1-重写单元与证据交叉矩阵.md:29`）；Q1–Q3 与建议 1–5 逐条有落点；无新越界。
11. **总纪律残留（程序判语义）**：无发现。`:21`＋`:102` AST 机检行。
12. **与模块卡一致**：无发现（A-1 已办结）。卡 `## answering` 依赖现含 `transport`（`specs/modules.md:241`），与规格 `:32`／`:109` 一致；接口 `:37`＝卡 `:237`；职责一致。

### C. 新增问题清单

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| C-1 | 中 | **「`transport` 公开面无任何边界闸覆盖」不实**：`R2` 契约已覆盖「只经 `transport` 包根（禁深层子模块）」这一半——`source_modules` 含 `appv2.runtimev2.answering`，`forbidden_modules` 含 `appv2.runtimev2.transport.*`。`R2` 的 forbidden 面 literally 就是「公共层块（含 transport）的深层子模块」，故 `:124` 理由句「R1–R8 的 forbidden 面无『`transport` 公开面』一面」亦不成立。真正**无闸**的只是另一半——「不自行拼 wire 帧／不直连 SSE 通道」 | `specs/answering.md:67,:124`；`tools/importlinter_v2.toml:74-78`（R2）；回执 §四.2 已自认张力 | 照 `spec-format.md` §五改写：「`transport` 公开面＝**R2 覆盖『只经包根』一半**；未覆盖面＝『不自行拼 wire 帧／不直连 SSE』→ 人审（或降维为 AST 断言）」——即把 `:124` 的「无任何闸」改为「部分覆盖＋残余面人审」，`:67` 括注同改 |

> 说明：无「指向不存在的真源」「重复编号」类新问题；`Gap.kind` 闭世界、`Citation` 字段、四处口径均自洽。

### 未验证清单 ＋ 覆盖自检

**未验证**（已声明，不编造）：

1. `answering` 目录仅占位、`tests/domains/test_v2_answering.py` 不存在（阶段 5 承诺）——14 行验收测试只能核标识形态，无法实跑。
2. `prompts` 合同（答案要求 V2 真源条数）未定稿；X-1 只能锚 V1 现状 `recon/L2b`（7 条）。
3. R2/R5b/R6/R7 的「已真跑」为**契约空过**（无实现代码）——契约存在且 KEPT 已实测，「answering 实现层是否真合规」未验证。

**覆盖自检**——本轮实读文件：

- 复审对象：`specs/answering.md`（全文 130 行区间，129 行正文）。
- 判据／版式：`docs/spec-process.md` §三、`docs/spec-format.md`。
- 真源：`specs/modules.md`（`## answering:230-248`／`## context:375-393`／`## transport:394-413`；边界规则表 `:512-533` 含 R1–R8）、`tools/importlinter_v2.toml`（全文 124 行）。
- 样板：`specs/understanding.md:60-65`、`specs/tool_matching.md:74-80`与验收表、`specs/preconditions.md:66-74`、`specs/execution.md:86-92,:105-112`。
- 证据／决策：`docs/runtime-refactor/recon/L2b-作答装配与回声.md`、`synth/S1-重写单元与证据交叉矩阵.md`、`synth/S6-事件与帧目录.md`（存在性）、`walk/裁决表.md` §14、`arch/P7a-交接包与挂账清单.md:98`。
- 上轮产物：本文件 §二／§五、`answering-修订回执.md` 全文。
- 闸：实跑 `uv run python tools/ref_resolvable.py check`、`uv run python tools/check_specs.py`、`uv run lint-imports --config tools/importlinter_v2.toml`。

**两道闸实跑输出（2026-10-15）**：

- `uv run python tools/ref_resolvable.py check` → **绿**：`真源引用可解析闸绿：12 份规格的真源引用与边界规则编号均可解析。`（exit 0）
- `uv run python tools/check_specs.py` → **PASS（0 警告）**（exit 0）。**注**：回执 §三报的 FAIL（`modules.md` 依赖 `text`）已被 L0 补修消除——`specs/modules.md:241` 现为「`transport`（text 帧的增量发射，只经其公开面）」，帧名 `text` 已去反引号，故本闸绿；回执 §四.1 登记的红源已闭合。
- 附跑 `uv run lint-imports --config tools/importlinter_v2.toml` → **Contracts: 18 kept, 0 broken**（R2/R5b/R6/R7 均 KEPT，answering 为空模块过闸）。

## §七 定稿（2026-10-15）

**复审唯一未闭合项 C-1 已修**（并纠正 L0 修复单自身的错）：**「`transport` 公开面无任何边界闸覆盖」不实**——真源 `tools/importlinter_v2.toml` 的 **R2 契约**（业务相位禁引公共层块**深层子模块**，`forbidden` 含 `appv2.runtimev2.transport.*`）已覆盖「**只经包根**」这一半。已改为两行分列：**只经包根半面 → R2（已真跑）**；**「不自行拼 wire 帧／不直连 SSE」另一半 → 无专属闸，登记待补（降维 AST 断言需新增验收行，本批未授权）**。

**结论**：`specs/answering.md` ＝ **已定稿**。工序六步走完。
**登记待补**：`transport` 无专属闸的那一半（降维 AST 断言），随阶段 5／6 补。
