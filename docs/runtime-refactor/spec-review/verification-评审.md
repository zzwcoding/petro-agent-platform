- 日期：2026-10-15 ｜ 状态：**评审发现清单（待 L0 逐条处置）**
- 本清单只产发现，不修改任何现存文件。

## 一、结论摘要

1. 版式骨架合格：十节齐、标题逐字、顺序正确；`spec gate`（`tools/check_specs.py`）本地实跑 **PASS（0 警告）**。
2. 三类高危形态中，**「边界规则编号／真源路径指向不存在」本轮未复发**——`tools/ref_resolvable.py check` 实跑绿（13 份规格 0 违规），R8／R7／R5b／R2 编号真存在且 `source_modules` 均含 `appv2.runtimev2.verification`（`toml:122`/`:116`/`:103`/`:76`）。
3. 但**「指向不存在的类型」+ 闸覆盖不实各出一处**：接口里的 `GapRef` **全仓仅此一处、无定义**（跨块口径未落地）；`R7` 被用来声称「模型只经 `gateway_adapter`」属**部分覆盖**，且挂钩表有一行是从别的样板照搬的错配行。
4. 与**已定稿 `specs/agent-loop.md` 未对账**：同一核验判定（承载豁免）两文口径宽窄不一，验收测试文件命名也分歧。
5. 与模块卡**接口／职责／依赖三面一致**（卡 `-> Verdict`＝规格 `:32`；依赖＝`state`/`transport`）；但 `Verdict`/`VerdictResult` 的返回关系自相矛盾，若修法改成返回 `VerdictResult` 则**须回阶段 2 改卡**。

## 二、发现清单表

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| V-1 | 高 | **指向不存在的类型 + 跨块口径未落地**：接口写 `gaps: list[GapRef]` 并注「引 answering 的 Gap 口径」，但 `GapRef` **全仓只此一处、无字段定义**（`grep -rn GapRef` 仅命中本行）；`answering` 真源里是 `Gap`（`{kind: Literal["refused","missing","unverified"]; subtask_id; reason}`），本规格既未复述其字段/闭世界，又自带**另一个不同的闭世界** `RewriteRecord.reason∈{no_material, conflict}`，两闭世界之间**无映射**。属「同物异名意图 + 落空 + 闭世界可能真冲突」 | `specs/verification.md:45`、`:42`；`specs/answering.md:49-51`；对照 `specs/modules.md:256`（卡只给签名） | 采纳：把 `GapRef` 改为引 `answering` 的 `Gap` 类型，并逐字给出继承字段＋说明 verification 产出的缺口 `kind` 取值（`no_material`→？`conflict`→？ 须裁定或回阶段 2 对齐口径） |
| V-2 | 高 | **接口自相矛盾（ok/gaps 取不到）**：`verify` 声明返回 `Verdict`（无 `ok`/`gaps`），但 `ok`／`gaps` 定义在**另一个类** `VerdictResult`；行为 9 与错误契约都以 `ok` 决定回炉、对外给 `gaps`——`ok` 不在返回类型里，`orchestration` 无从取值；两类的包含关系未声明 | `specs/verification.md:32,:43-45,:50,:71`；`specs/modules.md:256`（卡签名 `-> Verdict`） | 采纳：改 `def verify(...) -> VerdictResult`（`VerdictResult` 内嵌 `Verdict` 五键＋`ok`＋`gaps`），或把 `ok`/`gaps` 并入 `Verdict` **并同步模块卡（走阶段 2）** |
| V-3 | 中 | **R7 部分覆盖被当成完整覆盖 + 挂钩行错配**：`R7 亦覆盖本块（模型只经 gateway_adapter）`、挂钩表行「模型只经 `gateway_adapter`（天然满足）｜边界闸 R7」——但 `R7` 契约 `forbidden` 面**只有** `appv2.infra.llm_client`（不含「经其它旁路调模型」）；对本块真正成立的是 **R8**（`forbidden=gateway_adapter`），且本块硬要求应是「**不调模型**」而非「模型只经 gateway_adapter」（后者是从别的块样板照搬的行、与 `:117` 行重复） | `specs/verification.md:56,:118`；`tools/importlinter_v2.toml:113-117`（R7）、`:119-123`（R8）；对照样板 `specs/execution.md:71,:136` | 采纳：`:56` 注明「R7 只覆盖『不得直引 `appv2.infra.llm_client`』一面」；`:118` 行改为「零模型（不调模型）｜边界闸 R8（＋R7 直引面）」并与 `:117` 合并去重 |
| V-4 | 中 | **与已定稿 `specs/agent-loop.md` 未对账（跨规格覆盖/口径）**：`agent-loop.md` 同覆盖核验（触及模块 `verification`；行为 5 核验收口明写「**表格行/血缘卡/fragment 承载豁免**随 P-024b 口径继承」；验收测试落 `tests/domains/test_v2_agent_verify.py`）。本规格行为 2 为**绝对口径**（数值须复述）、**未承接承载豁免**（现状真源 `recon/A2` R-A2-11）；两文对同一判定给出宽窄不一的判据；且本规格验收测试落 `test_v2_verification.py`，与既有 `test_v2_agent_verify.py` 分歧 | `specs/agent-loop.md:33,:106-108,:155-156`；`specs/verification.md:64,:84-100`；`docs/runtime-refactor/recon/A2-核验规则与归属审.md:105`（R-A2-11） | 采纳：行为 2 补承载豁免（或写明本块不承接）；与 `agent-loop.md` 对账测试文件归属，必要时回阶段 2 同步 `agent-loop.md`（先例：`clarification-评审` F-07） |
| V-5 | 低 | **数字/真源标注自相矛盾（第三档 vs 第二档）**：风险 3 标题写「第三档」，同句正文却写「若将来要引**第二档**」；`:19` 亦写「第三档」；真源 `research/最佳实践-节点-核验.md` 明列「第三档＝中文 NLI 蕴含小模型」 | `specs/verification.md:108`（标题 vs 正文）、`:19`；`docs/runtime-refactor/research/最佳实践-节点-核验.md:73,:129` | 采纳：统一为「第三档」，删「第二档」笔误 |
| V-6 | 低 | **红线「禁手写替代」无对应闸名 + 未登记无闸半面**：`:59` 「不得自建模型客户端、不得自建帧通路」未给对应闸（样板 `answering.md:67` 给 R7；本块更该给 R8）；`:58` 只声明「只经包根半面由 R2 覆盖」，另一半「不自行拼 wire 帧」**无闸却未按 `spec-format` §五 登记「人审＋原因」**（样板 `answering.md:125` 有该行） | `specs/verification.md:58,:59`；`docs/spec-format.md` §五；对照 `specs/answering.md:67,:125`、`specs/preconditions.md:62-64` | 采纳：`:59` 补对应闸名（R8／R2）；后半面按样板登记「无专属闸→人审或降维断言」 |
| V-7 | 低 | **覆盖漏项（walk/15 §五.5 未落点）**：`walk/15` 建议「引标与流式对齐（承接 §14-A）：答案真流式后，核验要能对上**增量**里的引标」，本规格行为 1 只写「剥结构性残留→逐行判定」，**未涉增量对齐**；`## 依赖与风险` 也未登记该跨块待办 | `docs/runtime-refactor/walk/15-核验-核验收口.md:61`；`specs/verification.md:63,:102-109` | 采纳（弱）：补一条行为，或在「依赖与风险」登记「核验对增量引标」随 `answering` 真流式协同定稿 |

## 三、14 问逐条回答

**1 十节齐＋标题逐字？** 无发现。`## 目标`／`## 不做什么`／`## 触及的模块`／`## 接口定义`／`## 框架与依赖红线`／`## 行为约定`／`## 不降级与静默禁令`／`## 验收测试`／`## 依赖与风险`／`## 与闸的挂钩表` 十节齐、逐字、顺序与 `docs/spec-format.md:16-34` 一致；`check_specs` 实跑 PASS。

**2 行为约定每条能否写成 assert？含糊词？** 无发现。仍以判 FAIL 的含糊词「尽量／合理／必要时／视情况」全文 **0 命中**；唯 `:124` 出现「等」，但在挂钩表说明行、非行为约定。逐条可判（逐行＝行级判定；数值复述＝token 在场；`ok=False`＝布尔）。

**3 数字有无裸值？** 有发现——**V-5**（`:108` 第三档/第二档自相矛盾）。其余数字为：`52`／`1520`（`:69,:71` 边界例示，可补 `recon/A2` D-A2-10 真源但属例示、非配置裸值）、「五键／五个计数」（接口自述）、「两次运行」（例示）——未构成「无出处的配置裸值」。

**4 不做什么每条有无「由谁承担＋锚点」？** 无发现。`:15`→`answering`（`## answering`）／`:16`→`execution`／`:17`→`context`／`:18`→`gateway_adapter`；`:19` 为自排除（「不做——语义蕴含属第三档」），带 `walk/00-设计总纲.md` §二 锚点。

**5 框架红线是否写对应闸名、闸名真存在、source 真覆盖 verification？** 有发现——**V-3**。真存在且 `source` 真覆盖 verification：R8 `toml:122`、R7 `toml:116`、R5b `toml:103`、R2 `toml:76`（`source_modules` 均含 `appv2.runtimev2.verification`）；R8 `forbidden=gateway_adapter`、R5b `forbidden=框架`、R2 `forbidden=公共层深层子模块` 均与红线意图对得上。但 R7 `forbidden` 只有 `appv2.infra.llm_client`，被用来声称「模型只经 gateway_adapter」＝部分覆盖；`:118` 行错配。

**6 不降级与静默禁令？** 无发现。`:76` 明写「合法降级路径：无」；`:77` 列机读信号（`verdict`／`notice` 帧，引 `synth/S6-事件与帧目录.md`＋step payload）；`:98` 有「信号在场」断言行；`:78` 留痕 `RewriteRecord`＋引红线原文 `arch/P7a-交接包与挂账清单.md` A-P7a-37（核：`P7a:98` 原文一致）。

**7 验收测试（每行标识／边界集保留集／测不出的行）？** 无发现。16 行全部绑 `tests/domains/test_v2_verification.py::<id>`；`:99`【边界集】、`:100`【保留集】两行俱在；无空判行（AST 行 `:96`／`:97` 可测）。

**8 与闸的挂钩表（填了没／「已真跑」属实否）？** 有发现（**V-3**）。表已填；「已真跑」属实——`lint-imports --config tools/importlinter_v2.toml` 实跑 **18 契约全 KEPT**（含 R2/R5b/R7/R8；verification 目录为占位、契约空过）；`spec gate 已进 CI` 属实（`.github/workflows/ci.yml:32`）。唯 `:118` 的 R7 行覆盖面不实（见 V-3）。

**9 与 `walk/` 决策是否冲突？** 无发现（逐条比对 Q-A／Q-B／Q-C）。Q-A 保持零模型→`## 目标`／`:56`／行为 8；Q-B 补质量度量进测试网→风险 1（`:106`）＋挂钩表 `:123`；Q-C 保持「行＋引标」→风险 4（`:109`）。与 `walk/15 §七 Owner 裁决`、`walk/裁决表.md §15` 一致；与总纲 §二（`:19` 声明不拿模型判语义）一致。

**10 覆盖（`walk/15` Q1–Q4／D1–D6／`synth/S1` M7／越界）？** 有发现（**V-7**）。Q1→风险 1（`:106`）；Q2→风险 2（`:107`）＋行为 7；Q3→行为 8（`:70`）；Q4→风险 4（`:109`）。D1（行＋引标 vs claim 保留）→行为 1／风险 4；D2→行为 3；D3→行为 4；D4→`目标`＋行为 7；D5→风险 1；D6→行为 7。`synth/S1` M7（`:30` 断言级核验＋归属审＋分源＋verdict）**无漏项**。越界：未见。**唯漏** `walk/15 §五.5` 引标增量对齐（V-7）。

**11 总纪律残留（程序替模型判语义）？** 无发现。核心判据是**结构判**而非语义判：无据＝「被引观察的数值未在断言文本复述」（token 在场，结构性）；矛盾＝「同 subject ≥2 支且值不同」（集合/字段比对）；`:19` 明文「语义蕴含判定属第三档——不做」，`:97` 挂 AST 机检行。未出现「词表/正则猜『这句意思上有没有支撑』」。

**12 与模块卡一致（职责／公开接口／依赖）？** 基本一致。职责 `:25` ＝ 卡 `modules.md:251`；公开接口 `:32` ＝ 卡 `:256`（`-> Verdict`）；依赖 `:104`（`state`／`transport`）＝ 卡 `:260`。**但** V-2：`ok`/`gaps` 落在 `VerdictResult`，与卡的 `-> Verdict` 签名对不上——**若修法改为返回 `VerdictResult`，须回阶段 2 改卡**。

**13 与六份样板写法一致性？（红线句式／挂钩表列式／AST 豁免面／边界集保留集／机读信号／`synth/` 前缀）** 有发现——**V-6**。一致项：挂钩表列式（三列）＝样板；AST 豁免面 `:97`「（AST 扫描；豁免面＝形态处理／集合成员判定）」＝ `execution.md:109`／`preconditions.md:112` 同款；边界集/保留集 `:99/:100` 俱在；机读信号 `:77` 引 `synth/S6-事件与帧目录.md`；`synth/` 前缀（`来源` 行 `synth/S1`（M7））＝样板同款。**不一致 2 处**：V-6（红线「禁手写替代」缺「对应闸名」子句＋「不自行拼帧」半面未登记无闸）；V-3（R7 行「部分覆盖」未照样板补「验收写法：无旁路」以外还错配了要求面）。

**附加 14、跨块（`GapRef` 与 `answering` 的 `Gap` 是否同一口径）？** 判定：**「同物异名的意图」+ 落空 + 闭世界可能真冲突**（＝发现 **V-1**，高）。理由三层：(a) 本规格自述「引 answering 的 Gap 口径」＝**意图指向 `answering` 的 `Gap`**；(b) 但落笔的类型名是 `GapRef`，而 `GapRef` **全仓仅 `:45` 一处、无定义**——引用**未落地**，读不出它到底是不是 `Gap`；(c) 字段/闭世界既未复述，且本规格另有 `RewriteRecord.reason∈{no_material, conflict}`（`:42`），与 `answering` 的 `Gap.kind∈{refused, missing, unverified}`（`answering.md:50`）**取值无交集语义**——`no_material` 尚可映 `unverified`，`conflict`（矛盾）在 `Gap.kind` 里**无对应值**。故不是「纯同物异名可忽略」，而是**真口径冲突待裁**：须裁定 verification 的缺口是复用 `Gap`（则补映射）、另立 `GapRef`（则定义字段并回阶段 2 改卡），还是显式声明两者不同物。**另**：跨块协调说法「verdict 帧批次落定归 `orchestration`」与已定稿 `answering.md:77` **一致**（两文均「由 `orchestration` 协调、本块只保证自产部分」），此处无冲突。

## 四、未验证清单 ＋ 覆盖自检

**未验证**（已声明，不编造）：

1. `appv2/runtimev2/verification/` 仅有占位 `__init__.py`，`tests/domains/test_v2_verification.py` **不存在**（阶段 5 承诺）——16 行验收测试只能核标识形态，无法实跑。既有 `tests/domains/test_v2_agent_verify.py` 覆盖同族核验步（见 V-4）。
2. R2／R5b／R7／R8 的「已真跑」为**契约空过**（verification 无实现代码）——契约存在且 KEPT 已实测，「verification 实现层是否真合规」未验证（阶段 5 才有对象）。
3. V-4 中「承载豁免在本块是否应承接」为设计取舍，未见 Owner 对本块的显式裁决；`recon/A2` R-A2-11 是**现状取证**（非定稿规格），是否约束新设计**未在 `walk/15` 明示**——按 `walk/裁决表.md`「重写不是改」总原则应回看，但**本评审不代裁**。
4. `research/最佳实践-节点-核验.md` §三.2／§五「第三档」=`中文 NLI 蕴含小模型` 系从 `2b1a §三取舍二` 转引，未回原始 `资料/` 核（该文件自陈「引用任何做法前请回原始资料核对」）。

**覆盖自检**——本轮实读文件：

- 评审对象：`specs/verification.md`（全文 125 行）。
- 判据／版式：`docs/spec-process.md`（§三）、`docs/spec-format.md`（全文）。
- 决策：`docs/runtime-refactor/walk/15-核验-核验收口.md`、`walk/裁决表.md`、`walk/00-设计总纲.md`、`walk/07-理解段重估.md`。
- 模块与边界：`specs/modules.md`（`## verification`／`## transport`／`## answering` 卡＋`## 边界规则` R1–R8）。
- 现状取证：`docs/runtime-refactor/recon/A2-核验规则与归属审.md`（R-A2-01..31）、`recon/H-观察核验作答与图装配.md`（verify 节点／T8a/T8b）、`arch/P4a1-票堆V2-46至50.md`（V2-48）、`arch/P4a2-票堆V2-51至55.md`（V2-54）、`arch/P7a-交接包与挂账清单.md`（A-P7a-37）。
- 样板：`specs/understanding.md`／`clarification.md`／`tool_matching.md`／`preconditions.md`／`execution.md`／`answering.md`；跨规格对账：`specs/agent-loop.md`；上轮产物：`spec-review/answering-评审.md`、`spec-review/clarification-评审.md`。
- 合成／研究：`synth/S1-重写单元与证据交叉矩阵.md`、`synth/S6-事件与帧目录.md`、`research/最佳实践-节点-核验.md`、`CONTEXT.md`。
- 闸：`tools/importlinter_v2.toml`、`tools/ref_resolvable.py`、`tools/check_specs.py`、`.github/workflows/ci.yml`。

**计数**：共 **7 条** 发现——`L0×0`／`高×2`（V-1、V-2）／`中×2`（V-3、V-4）／`低×3`（V-5、V-6、V-7）。

**两道闸实跑输出（2026-10-15）**：

- `uv run python tools/ref_resolvable.py check` → **绿**：`真源引用可解析闸绿：13 份规格的真源引用与边界规则编号均可解析。`（exit 0）
- `uv run python tools/check_specs.py` → **PASS（0 警告）**（exit 0）。
- 附跑 `uv run lint-imports --config tools/importlinter_v2.toml` → **Contracts: 18 kept, 0 broken**（R2/R5b/R7/R8 均 KEPT，verification 为空模块过闸）。

---

## §五 L0 逐条处置（2026-10-15）

> 两条高的指控**主窗已核验，成立**：①`GapRef` 全仓无定义、跨块口径未落地；②`ok`／`gaps` 不在返回类型里。7 条**全部采纳**。

| 编号 | 严重度 | 处置 | 落点 |
| --- | --- | --- | --- |
| V-1 | 高 | **采纳→L0 裁决＋交修订步** | **统一到 `answering` 的 `Gap` 口径**：`gaps` 类型改为 `list[Gap]` 并**复述其字段与闭世界**（`kind ∈ refused｜missing｜unverified`；核验侧产出的是 **`unverified`**）。**`RewriteRecord.reason`（`no_material`｜`conflict`）不是 `Gap` 的同类**——它是「**为什么改写这句**」，与「哪个子问题缺口」是两个维度，**不强行映射**，规格须写明这层区分 |
| V-2 | 高 | **采纳→L0 裁决（合类）＋交修订步** | **合并为单一返回类型**：把 `ok`／`gaps` **并入 `Verdict`**，删除 `VerdictResult`——卡签名 `-> Verdict` 保持不变，自相矛盾消除（比改卡更小） |
| V-3 | 中 | 采纳→修订步 | 红线与挂钩表：本块硬要求是「**不调模型**」，**真正覆盖它的闸是 R8**；R7 行**改述**（R7 只禁直引 `infra.llm_client`，对本块仅是「天然满足」）并**删掉与 `:117` 重复的照搬行** |
| V-4 | 中 | 采纳→修订步 | 与已定稿 `specs/agent-loop.md` **对账**：核验的「**承载豁免**」（表格行／血缘卡／fragment 承载，真源 `recon/A2` R-A2-11）必须在场或被**显式登记为差异**——本规格行为 2 现为绝对口径（数值须复述），宽窄不一；并说明本块验收测试文件与既有 `tests/domains/test_v2_agent_verify.py` 的关系（新建 `test_v2_verification.py` 的理由，或对齐） |
| V-5 | 低 | 采纳→修订步 | 统一为「**第三档**」，删「第二档」笔误（真源 `research/最佳实践-节点-核验.md` 明列第三档＝中文 NLI 蕴含小模型） |
| V-6 | 低 | 采纳→修订步 | 红线「禁手写替代」**补对应闸名**（本块给 **R8**）；「不自行拼 wire 帧」那一半**按 `docs/spec-format.md` §五 登记「人审＋原因」**（照 `answering.md` 同款行） |
| V-7 | 低 | 采纳→修订步 | 补「**核验对增量引标**（承接 §14-A）」一条行为，或在「依赖与风险」**登记跨块待办**（随 `answering` 真流式协同定稿） |

**给修订步的修复单**：Y-1…Y-7（对应 V-1…V-7）。
**给 Owner 的**：无。

---

## §六 复审（2026-10-15）

**结论**：Y-1…Y-7 **7 条全部闭合**（逐条以 `specs/verification.md` 实际内容＋真源文件核实，不采信回执自述）；12 条判据复跑**无红**；三个废名「第二档」「VerdictResult」「GapRef」在本规格中**均已清零**；两道闸实跑绿。**未发现阻断级新增问题**，仅 2 处非阻断低度观察（见 C）。判**够「可定稿」**。

### A. 逐条核「闭合」

| 条目 | 闭合？ | 证据锚点 | 备注 |
|---|---|---|---|
| Y-1 | 闭合 | `specs/verification.md:45-48`（`class Gap` 逐字复述 `kind: Literal["refused", "missing", "unverified"]`／`subtask_id: str \| None`／`reason: str`）＝ `specs/answering.md:49-53` 逐字同源；`:52` 注「核验侧产出 `kind="unverified"`」＋闭世界越界判失败；`:53` 写「两维度、不强行映射」；`:41` 字段注释 | `GapRef` 本规格已无（`grep -rn GapRef` 仅命中 `*-评审.md`／`*-修订回执.md` 自身） |
| Y-2 | 闭合 | `specs/verification.md:40-41`（`ok`／`gaps` 已在 `Verdict` 内）；`:55`「不判 `Verdict.ok=True`」；`:76`「`Verdict.ok=False` 才回炉」；`:32` `-> Verdict` | `VerdictResult` 本规格已无（`grep` 仅命中 `*-评审.md`／`*-修订回执.md`）；卡签名未动，**不需回阶段 2** |
| Y-3 | 闭合 | `specs/verification.md:61`（R7 改述＝「只禁直引 `appv2.infra.llm_client` 一面，对本块仅『天然满足』」、明写「真正覆盖本块的是 R8」）；`:119-132` 挂钩表已无 R7 重复行 | 与 `tools/importlinter_v2.toml:113-117`（R7 `forbidden=[appv2.infra.llm_client]`）、`:119-123`（R8 `forbidden=[appv2.runtimev2.gateway_adapter]`）核对一致 |
| Y-4 | 闭合 | `specs/verification.md:69`（表格行／血缘卡／fragment 豁免「全数值复述」，任一数值重叠即支撑、零重叠照改）引 `docs/runtime-refactor/recon/A2-核验规则与归属审.md` **R-A2-11**；`:107` 测试文件归属注（新建 `test_v2_verification.py` 与既有 `test_v2_agent_verify.py` 的关系） | **真源核实**：`A2-核验规则与归属审.md` 存在，`:105`＝「R-A2-11 carrier 豁免（agg_row/lineage/fragment）＝权威承载不做全数值复述，任一数值重叠即支撑、零重叠照改」——节真实存在、口径一致 |
| Y-5 | 闭合 | 全篇「第二档」**0 命中**（`grep` exit 1）；`:19`／`:115` 均「第三档」 | 回执称 `:19` 原本即第三档，核实属实 |
| Y-6 | 闭合 | `specs/verification.md:64`（「禁手写替代」补 R8；「自建帧通路」半面引 R2＋「另一半无专属闸 → 人审＋原因」）；`:128` 挂钩表「另一半」人审行 | 与样板 `specs/answering.md:67,:125` 同款句式 |
| Y-7 | 闭合 | `specs/verification.md:117`（风险 5「核验对增量引标（承接真流式）」登记为跨块待办）引 `walk/裁决表.md` §14-A | **真源核实**：`walk/裁决表.md:171-179` §14-A＝「答案一次性推全量 vs 真流式 → 改真流式」存在（`walk/15:61` §五.5 即「承接 §14-A」，同指一裁决） |

### B. 12 条判据复跑（＋样板一致性）

1. **十节齐＋标题逐字**：无发现。`specs/verification.md:7,11,21,29,58,66,79,85,109,119` 十节齐、逐字、顺序同 `docs/spec-format.md:31-34`。
2. **行为约定可写 `assert`／含糊词**：无发现。「尽量／合理／必要时／视情况」全文 **0 命中**（`grep` exit 1）。
3. **数字裸值**：无发现。唯 `52`／`1520`（`:74`）为边界例示、`五键`／`五个计数`（`:73,:54`）为接口自述，非外部配置裸值。
4. **不做什么每条「由谁承担＋锚点」**：无发现。`:15-19` 五行俱带「由谁承担＋锚点」。
5. **框架红线写对应闸名／闸名真存在／source 真覆盖**：无发现。R8/R7/R5b/R2 编号真存在且 `source_modules` 均含 `appv2.runtimev2.verification`（toml `:122`/`:116`/`:103`/`:76`）；R7 部分覆盖误用已消（＝Y-3）。
6. **不降级与静默禁令**：无发现。`:81` 明写「合法降级路径：无」；`:82` 机读信号（`verdict`／`notice`＋step payload）；`:103` 信号在场断言；`:83` 留痕 `RewriteRecord` 引红线 `P7a:98` A-P7a-37（原文一致）。
7. **验收测试每行标识＋边界集／保留集**：无发现。16 行全绑 `tests/domains/test_v2_verification.py::<id>`；`:104`【边界集】、`:105`【保留集】俱在。
8. **挂钩表填了／已真跑属实／接不上写原因**：无发现。表已填；`:128`／`:132` 两处「人审＋原因」；实测 `lint-imports` 18 契约 kept。
9. **与 `walk/` 决策冲突**：无发现。Q-A 零模型→`:19`／`:61`／行为 8；Q-B 质量度量→风险 1（`:113`）＋挂钩 `:131`；Q-C 行＋引标→风险 4（`:116`）。与 `walk/15 §七`、`裁决表 §15` 一致。
10. **覆盖（walk/15 Q-D／`synth/S1` M7／越界）**：无发现。Q1-Q4／D1-D6 均落点（V-7 已补风险 5）；`synth/S1:30` M7（断言级核验＋归属审＋分源＋verdict）无漏项；未见越界写入他块事。
11. **总纪律残留（程序替模型判语义）**：无发现。`:19` 明文「语义蕴含判定属第三档——不做」；判据为「数值 token 在场／同 subject 值比对」结构判；`:102` 挂 AST 机检行。
12. **与模块卡一致**：无发现。职责 `:25`＝卡 `modules.md:251`；签名 `:32`＝卡 `:256`（`-> Verdict`，合并后未动，自相矛盾消）；依赖 `:111`＝卡 `:260`。

**样板写法一致性**：无发现。挂钩表三列式、AST 豁免面（`:102`）、边界集／保留集、机读信号引 `synth/S6`、来源行 `synth/S1`（M7）均与 `answering.md`／`execution.md`／`preconditions.md` 同款；「无专属闸 → 人审」行（`:128`）＝ `answering.md:125` 同款。

### C. 新增问题清单

**未发现阻断级新增问题。** 两条低度观察（非缺陷、不阻断定稿，供 L0 定稿时一句带过）：

- **观察 1（低，措辞）**：`Verdict` 已并入 `ok`／`gaps`（共 7 字段），但 `:73`「`Verdict` 五键」、`:54`「五个计数与 `ok`」、`:94`／`:105` 仍用「五键」旧措辞。三处**自洽**（均枚举了是哪五键，且 `ok` 另有行为 9 承接），仅措辞未随合并刷新——回执「发现但修复单未覆盖」第 4 条已如实披露，无矛盾。
- **观察 2（低，跨文）**：`specs/agent-loop.md:108` 承载豁免写作「血缘卡/fragment」，本规格 `:69` 与真源 A2 R-A2-11 写作「表格行／血缘卡／fragment」——本规格更宽且与真源一致；差异在 `agent-loop.md` 侧（该文本轮未动），非本规格缺陷。

### 未验证清单

1. `appv2/runtimev2/verification/` 仍仅 `__init__.py`；`tests/domains/test_v2_verification.py` **不存在**（阶段 5）——16 行验收只能核标识形态，无法实跑。
2. R2／R5b／R7／R8「已真跑」为**契约空过**（verification 无实现代码）——契约存在且 kept 已实测，「实现层真合规」待阶段 5。
3. Y-4「本块是否应承接承载豁免」为设计取舍——L0 已在 §五 V-4 处置为「承接」，非本复审代裁。

### 覆盖自检（本轮实读）

- 复审对象：`specs/verification.md`（全文 132 行）。
- 上轮／修订：`docs/runtime-refactor/spec-review/verification-评审.md`、`verification-修订回执.md`。
- 判据／版式：`docs/spec-process.md` §三、`docs/spec-format.md`。
- 真源：`specs/modules.md`（`## verification`／`## answering`／`## transport` 卡＋R1-R8 边界规则）、`tools/importlinter_v2.toml`、`docs/runtime-refactor/recon/A2-核验规则与归属审.md`（R-A2-11）、`walk/15-核验-核验收口.md`（§五.5）、`walk/裁决表.md`（§14-A／§15）、`synth/S1-重写单元与证据交叉矩阵.md`（M7）、`specs/answering.md`、`specs/agent-loop.md`；样板 6 份对读。
- 闸：`tools/ref_resolvable.py`、`tools/check_specs.py`。
- 命令：`grep -rn "第二档"／"VerdictResult"／"GapRef"`；`ls tests/domains/test_v2_verification.py appv2/runtimev2/verification/`；`grep -n "R-A2-11"` A2。

**两道闸实跑输出（2026-10-15）**：

- `uv run python tools/ref_resolvable.py check` → **绿**：`真源引用可解析闸绿：13 份规格的真源引用与边界规则编号均可解析。`（exit 0）
- `uv run python tools/check_specs.py` → **spec gate: PASS（0 警告）**（exit 0）

**计数**：闭合 **7/7**；判据红 **0/12**；新增问题 **0 阻断级**（2 低度观察，非缺陷）。

## §七 定稿（2026-10-15）

复审提的 2 条低已办：**①「五键」措辞跟上合类**（全篇改为「各字段齐备（五计数 ＋ `ok`／`gaps`）」）；**②** `specs/agent-loop.md:108` 的承载豁免未含「表格行」——该差异在 `agent-loop.md` 侧，**登记待随其同步**（本规格已按 `recon/A2` R-A2-11 承接表格行／血缘卡／fragment 三种承载）。

**结论**：`specs/verification.md` ＝ **已定稿**。工序六步走完。**主干七块全部定稿。**
