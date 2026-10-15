# gate 规格评审（独立评审代理用）

- 日期：2026-10-15 ｜ 状态：**待评审（`specs/gate.md` 起草稿已落盘，评审发现清单敞口待填）**
- 被评对象：`specs/gate.md`（起草稿——十节版式，真源 `docs/spec-format.md`；工序真源 `docs/spec-process.md` 六步：起草 → **独立评审** → 逐条处置（L0 必须清零）→ 修订 → 复审 → 定稿）
- 评审工序：起草 → **独立评审** → 逐条处置（L0 必须清零）→ 修订 → 复审 → 定稿
- 评审人纪律：全新上下文（无起草会话记忆）、**只产发现、不改任何现存文件**；每条发现带证据锚点＋建议处置；**L0 清零前 `specs/gate.md` 不得定稿**。
- 起草人自报：本稿为「全新上下文起草」——起草时实读下列全部基准件与行为真源；对**卡面初拟形→V2 定案**的差异采取「照抄卡面＋V2 定案签名双列＋卡级登记」处理（照 `specs/parsing.md` 先例）。**上游硬承接已办**：窗 A 收官对账「pin-18 待窗 B gate」——本稿把 pin-18 落成行为 1–9＋验收 4 行＋挂钩表行（P0 正面承接）；**pin-31 逐条核实移出本块**（判断在 `tool_matching`／分派在 `preconditions` 判定序第 1 位——两头认核成立，见重点核对项 2）；**`pin-21`**（faq 五站链）零落点呈主窗件——源文本无 gate 落点，**知悉、本块不挂**。**全表 31 钉已逐条扫**：本块落 pin-18 一枚；pin-31 移出；其余 29 枚与 gate 无涉（各落其块，见各块挂钩表）。

## 评审基准（只读参考）

- 版式与三判据：`docs/spec-format.md` §二（十节硬要求）／§二之二（节标题逐字）／§三（可判真伪／数字单点／闸在前面）；工序判据清单见 `docs/spec-process.md` §三（评审照此逐条核）。
- 块真源：`specs/modules.md` `## gate` 卡（职责「安全阀——注入／外发／写意图的词面快路径（命中即不放行；不承载红线，只读硬保证在执行层）」；公开接口 `screen`＋`apply_term_verdict`（**张力见重点 4**）；依赖 `state`；Seam「结论入口（模型结论 → 分派）」（**移出件遗物——见重点 4**）；测试计划三句）；`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §三 C gate 行＋§四 R2 注（「10 块全护」）＋§五 覆盖声明（「`gate` 收 H12 全量」**已作废**——裁决 #12）＋§七 H12 行。
- 归责尺子：`docs/runtime-refactor/walk/判断归责表.md`（「词面安全阀」行＝程序（仅辅助快路径）｜结构（早退）；「硬保证落执行层、词表不作判据」）；`docs/runtime-refactor/walk/裁决表.md`（项目级 #3／#5／#12；§02／§04★／§07）。
- 行为真源抽查面（起草稿逐条所引，评审建议亲读）：
  - `docs/runtime-refactor/walk/02-理解-词面安全阀.md`（§一 现状三族／判定序／收口三件套；§八 重估：辅助快路径＋收窄标准进规格层）
  - `docs/runtime-refactor/walk/03-理解-禁用词闸.md`（废弃词闸原貌与移出后归属；§八 改判）
  - `docs/runtime-refactor/walk/07-理解段重估.md`（§一 重估逻辑；§五 Owner 裁决）
  - `docs/runtime-refactor/arch/P5a1-票堆V2-66至69.md`（V2-66：A-P5a1-01…07；V2-67：A-P5a1-08…14）
  - `docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md`（L1353-L1468：常量行号区间／R-B2-09…15／R-B2-21／R-B2-24／R-B2-25；疑点 D-B2-01…04／11…15）
  - `docs/runtime-refactor/recon/C-理解与legacy决策节点.md`（R-C-04／R-C-06／R-C-07／R-C-13——闸位次／静默面／收口形）
  - `docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md`（H12 行）／`docs/runtime-refactor/synth/S4-调用图.md`（understand 入口调用位）／`docs/runtime-refactor/synth/S6-事件与帧目录.md`（notice 恰三键／refused）
  - `docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-18／pin-31 原文＋头注改写记录）
  - 逐字稿载体：`tickets/v2/V2-66-注入拦截闸.md`／`tickets/v2/V2-67-外发写意图闸.md`；现行代码字面 `appv2/runtime/graph.py`（L1353-L1468）；V1 钉测与 A 类语料 `tests/domains/test_v2_n0_word_gates.py`
- 已定稿消费/交界方对账：`specs/preconditions.md`（判定序第 1 位＝结构分派（消费模型结论）＋挂钩表 pin-31 行——「两头认」的彼面）、`specs/tool_matching.md`（行为 7「出数只认现行口径」＋挂钩表 pin-31 行——判断面）、`specs/transport.md`（`NOTICE_TYPES` 含 `refused`；notice 恰三键）、`specs/bookkeeping.md`（步记录／写口——收口落账面）、`specs/state.md`（`STEP_KINDS`；`draft_kind` 风险 6「direct＝确定性直答」）、`specs/understanding.md`（不做什么认「入口安全阀→`gate`」；触及面「只消费其结论」——**收口承接缺口见风险 2**）、`specs/answering.md`（`Gap.kind` 含 `refused`——子问题级拒答面，与本块入口拒答不混）、`specs/parsing.md`／`specs/context.md`（先在体例：双列＋卡级登记＋风险 7 清单）
- 双闸＋边界闸（评审人本地复跑）：`uv run python tools/check_specs.py`；`uv run python tools/ref_resolvable.py check`；`uv run lint-imports --config tools/importlinter_v2.toml`

## 重点核对项（起草方自评风险，供优先看）

1. **pin-18 承接完整性**（本块硬承接——窗 A 对账「pin-18 待窗 B gate」登记在 `docs/runtime-refactor/00-决议与方法.md` 流水 42）。起草稿落法＝行为 1–9＋验收 4 行（`::family_order_first_hit_wins`／`::hit_early_exit_zero_model`／`::refusal_signal_shape`／`::class_a_no_false_positive`）＋挂钩表 pin-18 行。**请核**：(a) pin-18 逐要件全落——三族（注入→外发→写意图）／禁用词已移出门口／命中零模型零执行／notice `type=refused`／A 类问句零误伤；(b) 「零模型零执行」断言的可构造性（集成面执行者＝入口消费方——起草稿列为「早退与收口落账由入口消费方执行」＋understanding 回提登记，见风险 2；此分工是否可接受）；(c) pin 文「（~~禁用词~~已移出门口）」的移出落点与 #12 两头认是否一致（重点 2 联动）。
2. **pin-31 与 `preconditions`／`tool_matching` 分工两头认核**。起草稿落法＝接口定义「废弃词闸移出、不施工」判定＋行为 15＋挂钩表「`pin-31` 经逐条核实不落本块（防一头两认）」行（对读：判断＝`specs/tool_matching.md` 挂钩表 pin-31 行／分派＝`specs/preconditions.md` 判定序第 1 位＋其挂钩表 pin-31 行／出数只认现行口径＝`specs/tool_matching.md` 行为 7——**两规格各认其面，成立**）。**请核**：(a) 两头认核结论是否属实（亲读两规格逐字）；(b) 起草稿对弃用件是否**零残留行为面**（应零——行为 15 反向锁：`::no_writeback_of_term_gate`）；(c) `Disposition` 形状的 V2 归属说明（本块不定义；分派形状在 `specs/preconditions.md` 的 `SubtaskVerdict`）是否成立、有无第三处偷定义。
3. **裁决 #12 纪律「别写回门口」核**。**请核**：(a) 起草稿三族与 #12 原文逐字（「注入／外发／写意图＝代码快路径」）一致、**无自行扩缩**；(b) 有无把「提及 vs 执行」／术语表／台账读进球场（应零——行为 15＋不做什么两行）；(c) `synth/S1` H12 行（「N0＋N1＋豁免判定」）与 `docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §三 C／§七「H12 全量」残留措辞的处理是否如实（#12 覆盖声明在 §五；本稿只按 **N0 安全阀半面**承接、N1 半面零落——§三／§七 改述＝风险 7④登记）。
4. **卡级张力：`apply_term_verdict`＋「固定词表 fixture」＋Seam 行**（双列＋登记，不改卡；先例 `specs/parsing.md`）。**请核**：(a) 接口定义「卡面初拟形逐字照录＋注＋V2 定案签名」双列是否与 parsing 先例等价、`apply_term_verdict` 的「移出、不施工」判定与卡面职责行「已移出」是否互证；(b) 卡级登记**三件**（接口行／Seam 行「结论入口（模型结论 → 分派）」＝移出件遗物／族成员补录需求）是否齐、有无漏项（风险 1 检测手段＝人审是否如实）；(c) 「固定词表 fixture」（卡 Adapter 行）与「程序不做语义判断」（卡测试计划行）的边界定界（接口「Adapter 定界」bullet＋行为 13）是否成立、措辞能否被误读成「程序可拿词表判语义」；(d) 卡面测试计划首句「安全阀明显中招即拒（漏判由执行层兜，不靠它）」与行为 9／14 的对读是否完整。
5. **H12 单元覆盖与越界**。**请核**：(a) H12 的 N0 半面（三族／序／静默／收口／零误伤）全落、无漏项（对照 `docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md` L1353-L1468 逐 def：三 matcher／`_n0_refuse`／`_n0_intent_word_gate`）；(b) N1 半面（禁用词闸＋豁免判定 `is_ban_exempt` 面）零残留（无行为、无符号、无豁免逻辑——D-B2-01 的误伤面不复刻）；(c) 有无把别的单元的事写进来（M1 理解的任务书／模型／解析、H4 解析件、preconditions 判定位、tools 台账、context 渲染——应零）；(d) 押注点：起草稿把「收口三件套」行为写在本块（执行面分工给消费方）——对照 `specs/understanding.md`「只消费其结论」与风险 2 回提登记，「本块持行为＋他块执行」的写法是否算越界或两头不认。
6. **零误伤与漏判兜底口径**。**请核**：(a) 零误伤判据（A 类语料逐条 `None`）的样本集来源可迁移性（`tests/domains/test_v2_n0_word_gates.py::test_n0_no_false_positive_corpus`＋票面自检面——语料逐字承接）；(b) 「收窄到最明显命中」（`docs/runtime-refactor/walk/裁决表.md` §02-A）的规格层落法（行为 9 三条）是否足以支撑「不加豁免」的误伤面判定——**收窄不足／收窄过度两面都看**（本稿自评：行为 9 三条系起草方自拟落地，无 Owner 逐字条款——见风险 5）；(c) 「漏判由执行层兜，不靠它」的非防线定位（行为 14＋不做什么行）可判性——本块零红线判定面的 AST 断言＋人审是否够（硬保证在执行层的结构面不属本块）；(d) 三族匹配方式不齐（折叠／不折叠——D-B2-04）迁移照抄的取舍是否可接受（统一折叠＝另裁／规格变更，起草稿已声明）。

## 待填：评审发现清单

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
|  |  |  |  |  |

## 闸实跑记录（起草方，2026-10-15）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                   # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：22 份规格的真源引用与边界规则编号均可解析。  # exit 0

$ uv run lint-imports --config tools/importlinter_v2.toml
Contracts: 18 kept, 0 broken.                              # exit 0
（R5b／R6／R7 的 source 含 appv2.runtimev2.gate——亲读属实；
  R2 的 forbidden 实建九块、不含 gate.* ——半覆盖，见起草稿风险 3）
```

辅助取证（起草方实跑）：

- `grep -nE "尽量|合理|必要时|视情况" specs/gate.md` → **0 命中（exit 1）**。
- `awk '/## 验收测试/,/## 依赖与风险/' specs/gate.md | grep -c "::"` → **20**（验收表 20 行，含【边界集】／【保留集】两行）；`uniq -d` 空（无重复标识）。
- 行为约定 **15 条**（逐条带【断言：…】面）；挂钩表 **16 行**。
- `ls tests/domains/ | grep -c test_v2_gate` → **0**（无同名文件，新建承诺成立）；`appv2/runtimev2/gate/` 仅占位 `__init__.py`（阶段 2 骨架）。
- 首跑曾红一处（真源引用闸）：行为 9 行内同时含票面路径与裁决 `§02-A` 节号——闸把 `§02` 配到票面文件上（票面无该节）；**已把该行拆为两行**（收窄标准另起行），复跑绿。评审若认为该拆行影响可读性，请列发现并给落法。

### 未验证清单

1. `tests/domains/test_v2_gate.py` **不存在**、`appv2/runtimev2/gate/` 仅占位 `__init__.py`——20 行验收测试只能核标识形态，无法实跑；边界闸对 gate 是**契约空过**（与 state／parsing／prompts／context 同款），实现层真合规待阶段 5。
2. **收口行为面的执行者落定**：早退位次／零模型零执行／收口三件套的**执行面**在 `specs/understanding.md` 无承接行（风险 2）——`::hit_early_exit_zero_model`／`::early_exit_position_no_drift` 的绑定以落地者为准（understanding 补写或主窗裁定落 `orchestration`），未验证。
3. **收窄标准**（行为 9 三条）系规格层自拟落地（裁决 §02-A 授权「收窄标准进规格层」、无 Owner 逐字条款）——未验证其「最明显情形」界定的充分性（须评审按重点 6-b 两面核）。
4. **步标题「N0」前缀**（行为 8）系 V1 字面迁移照抄决定——未验证评审是否认该字面保留（改名＝规格变更；起草稿已在接口注释与行为 8 双处声明）。
5. **A 类语料**的逐字承接（迁移钉测 → 新测试）未做实体比对——条数与条目以 `tests/domains/test_v2_n0_word_gates.py` 现状为准，本规格不复述，未验证织网（阶段 5）时无洗白式删条。
6. **`pin-21`（faq 五站链）零落点**处置属主窗件（窗 A 呈报）——本块知悉不挂，未验证主窗归属决定。
