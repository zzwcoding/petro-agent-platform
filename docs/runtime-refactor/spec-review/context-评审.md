# context 规格评审（独立评审代理用）

- 日期：2026-10-15 ｜ 状态：**待评审（`specs/context.md` 起草稿已落盘，评审发现清单敞口待填）**
- 被评对象：`specs/context.md`（起草稿——十节版式，真源 `docs/spec-format.md`；工序真源 `docs/runtime-refactor/规划.md` §三 六步：起草 → **独立评审** → 逐条处置（L0 必须清零）→ 修订 → 复审 → 定稿）
- 评审工序：起草 → **独立评审** → 逐条处置（L0 必须清零）→ 修订 → 复审 → 定稿
- 评审人纪律：全新上下文（无起草会话记忆）、**只产发现、不改任何现存文件**；每条发现带证据锚点＋建议处置；**L0 清零前 `specs/context.md` 不得定稿**。
- 起草人自报：本稿为「全新上下文起草」——起草时实读了下列全部基准件与行为真源；对**卡面初拟形→V2 定案**的差异采取「照抄卡面＋V2 定案签名双列＋卡级登记」处理（照 `specs/parsing.md` 先例）。

## 评审基准（只读参考）

- 版式与三判据：`docs/spec-format.md` §二（十节硬要求）／§二之二（节标题逐字）／§三（可判真伪／数字单点／闸在前面）；工序判据清单（16 问）见 `docs/spec-process.md` §三。
- 块真源：`specs/modules.md` `## context` 卡（职责／公开接口 `compile(state) -> CompiledContext`／依赖 `state`＋`tools`／Seam「上下文编译（确定性管线）」／测试计划三项）；`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §二（定制裁决 6＝常驻注入走工具门）。
- 归责尺子：`docs/runtime-refactor/walk/判断归责表.md`——本块是**确定性编译/渲染块**，**重点扫「渲染滑成语义判断」与「截断静默」**。
- 行为真源抽查面（起草稿逐条所引，评审建议亲读）：
  - `docs/runtime-refactor/recon/K-上下文事件指南预算.md`（context.py 段：R-K-01…R-K-28；信任级映射／排序／帽／披露句／Manifest 三字段）
  - `docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md`（L1278-L1347：过程档案有界摘要 `_PROCESS_NOTES_BUDGET`／`_PROCESS_NOTES_HEADER`；`_resident_sources` 三来源行）
  - `docs/runtime-refactor/recon/L2b-作答装配与回声.md`（R-L2b-04——材料段追加位）
  - `docs/runtime-refactor/recon/I2a-状态常量与清单.md`（Manifest 十字段骨架）／`recon/I2b-RunState全字段.md`（`ledger_dump`／`process_notes` 字段注）
  - `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`（V2-61：A-P4b-32／44…48——分承载体、披露行、Manifest 三字段、selected_reason）
  - `docs/runtime-refactor/arch/P5b2-票堆V2-79a至79b.md`（A-P5b2-03／04——process_notes 条目形／当前轮不入史）
  - `docs/runtime-refactor/arch/P5b3-票堆V2-79c至79d.md`（V2-79c／79d：A-P5b3-02…04／10…17——摘要段有界／compaction 规则）
  - `docs/runtime-refactor/arch/P6a-票堆V2-80系列前半.md`（A-P6a-11——compaction「保留 vs 退役」矛盾登记）
  - `docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md`（A-P6b-24 compile 退役→渲染器／A-P6b-29 compaction 定案／A-P6b-34 承载位换文本不变）
  - `docs/runtime-refactor/arch/P7a-交接包与挂账清单.md`（A-P7a-37 不许静默红线）
  - `docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md`（H6 单元行）／`synth/S3-口径裁决清单.md`（D-02 帽分母）／`synth/S5-RunState字段矩阵.md`（`ledger_dump` 行＋§四【结构-1】）
  - `docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-08／09／22／24／26／30 原文）
  - `tickets/v2/V2-61-材料承载分形渲染.md`（附 A selected_reason／披露行逐字稿）／`tickets/v2/V2-80h-对话链追加式架构.md`（§6 compile 退役与 compaction）
- 跨块登记件（前批评审产出，本块须承接——逐条核）：
  - `docs/runtime-refactor/spec-review/prompts-评审.md` 风险 7④（`## context` 卡「术语表常驻注入」与常驻块渲染归 prompts 两说——建议卡改述「台账/名录投影取得〕经 tools 公开面装载进 state〕」）；风险 7⑦（GuideProvider 装载实现落点）
  - `docs/runtime-refactor/spec-review/state-评审.md` S-5／SZ-3：`pin-30` **compaction 半面归 context**（`synth/S1` H6／V2-79d）
  - `docs/runtime-refactor/spec-review/parsing-评审.md` 风险 7⑩（understanding 回认——非本块事，知悉即可）
- 已定稿消费/交界方对账：`specs/prompts.md`（行为 7／8／12／16——常驻块/材料段/过程段/时间量交界逐字对）、`specs/answering.md`（行为 4「Manifest 的编译归 context」；不做什么「材料段与 Manifest 的编译→context」；pin-09 行为面）、`specs/state.md`（行为 4／5／8；Manifest 十字段；`pin-30` 状态读入半面）、`specs/bookkeeping.md`（行为 7／8／9／10／15；写口清单）、`specs/transport.md`（`NOTICE_TYPES` 二十二值含 `material_truncated`）、`specs/persistence.md`（行为 12——pin-30 回放半面）、`specs/understanding.md`、`specs/clarification.md`、`specs/tool_matching.md`、`specs/agent-loop.md`（行为 2／行为 7；pin-22／23 挂钩）
- 双闸＋边界闸（评审人本地复跑）：`uv run python tools/check_specs.py`；`uv run python tools/ref_resolvable.py check`；`uv run lint-imports --config tools/importlinter_v2.toml`

### 起草方转写注（闸面导致的唯一一处转写）

- 行为 6 的 `selected_reason` 逐字形内含 `{M}/{N}`、`{K}/{总}` 斜杠段；`tools/ref_resolvable.py` 的「真源行内反引号 token 含 `/` 即当路径解析」把该片段误判为路径——起草稿把斜杠形**移出反引号**（用「」包裹）以过闸，文本本身按 `tickets/v2/V2-61-材料承载分形渲染.md` 附 A 逐字照录。评审若认为需另择写法（如改列行/拆段），请列发现并给落法。

## 重点核对项（起草方自评风险，供优先看）

1. **卡-迁移张力（`compile`→渲染器族）是否处理到位**（照 `specs/parsing.md` 先例）：卡面 `compile(state) -> CompiledContext`（初拟形）与 V2-80h 定案「compile 退役→追加内容渲染器」（`docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md` A-P6b-24）分叉。起草稿落法＝接口定义**双列**（卡面初拟形逐字照录＋注「施工以 V2 定案签名」；V2 定案给六函数＋常量族闭世界名单）＋`ContextBuilder` 去留与「卡面 compile 签名」列风险 7① 卡级登记（不改卡）。**请核**：(a) 双列形是否与 parsing 先例等价、有无漏载卡面字段；(b) 卡职责「对话链追加」在 V2 的定界（起草稿＝「追加内容渲染＋compaction 治理归本块；物理追加归 `bookkeeping.append_message`、追加时点归调用方」）是否成立、是否属自加；(c)「实名与参形阶段 5 按卡定」的留白是否过度（六函数的输入输出口径是否已够可判）。

2. **与 prompts 的交界定界是否逐条对得上**（prompts 已定稿，反查）：起草稿定界＝**台账/名录投影取得归本块（经 tools 装载进 state）｜常驻块包裹文本＋逐字转抄渲染归 prompts｜材料段渲染归本块｜过程档案有界摘要归本块（prompts 行为 16⑤ 只接渲染产物入参）**。**请核**：(a) 与 `specs/prompts.md` 行为 7（决策轮首入包含常驻块包裹）、行为 8（台账常驻块逐字转抄、恰一份、三删不回流）、行为 12（材料段不在装配输出内）、行为 16⑤（已做段调用方传入原样在场）逐条是否互斥且无缝；(b) 行为 14「本块零合同零指令」（六族特征子串零命中）与 prompts 行为 1 的扫描范围是否形成互补而**不重复扫**；(c) `docs/runtime-refactor/spec-review/prompts-评审.md` 风险 7⑦（GuideProvider 装载落点）的承接是否够（起草稿＝「本块装载面只含台账/名录投影；指南装载面仍待阶段 2」——登记是否如实）；(d) 行为 10 loader 写 `state.ledger_dump` 是否与其唯一写口纪律冲突（`specs/bookkeeping.md` 行为 1 的共享写面清单**不含** `ledger_dump`——起草稿自述「非共享写面、S5 写手 H6 在册」，此论是否成立）。

3. **截断与静默面（本块重头）是否逐条可判**：起草稿落法＝分承载体（权威/台账族全量无帽、帽只作用检索族，`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-44）＋模型面披露行逐字（A-P4b-45）＋Manifest 三机检字段与 `selected_reason` 逐字形（A-P4b-47）＋notice 发射面归 `answering`／帧面归 `transport`（本块零帧）＋过程档案披露行逐字（`docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md`）＋compaction 披露账目。**请核**：(a)「检索族」「权威/台账族」的判定是否仍然只是**闭世界映射 + 分组**而非语义判断（行为 2／4 与 `::no_lexicon_or_regex_in_context` 是否自洽）；(b) 披露行之「两个计数」与 `material_*` 三字段是否同源不漂移（行为 5 断言是否写得能红）；(c) pin-09 三面分工（本块产断面／state 字段面／answering 行为面／transport 帧面）是否「两头都认或两头都不认」；(d) A-P7a-37 的红线原文引用是否语义一致。

4. **`pin-08／09／22／24／26`（＋`pin-30` compaction 半面）核实结论是否成立**（本批起草时逐条对读 `docs/runtime-refactor/eng/04a-应钉行为清单.md` 原文；起草稿挂钩表已逐行落分工注）：
   - `pin-08`（P0）＝「明细行集题：答案交付行数＝引擎返回行数（50 行全交付，丢行=0）」——**落本块的是渲染面**：权威/台账族不设帽、帽只作用检索族（行为 4）；交付行为面在 `specs/answering.md`（`::rowset_full_delivery`）。请核是否构成「两头都认」。
   - `pin-09`（P1）＝「材料截断必披露：`material_truncated` notice＋『未渲染部分不作答』声明」——**落本块的是产断面**：披露行逐字＋三字段＋帽账（行为 5／6／不降级节）；字段面在 `specs/state.md`（S-4 分工注）、披露行为/帧面在 `specs/answering.md`／`specs/transport.md`。请核分工是否闭合。
   - `pin-22`（P0）＝「`messages` 只追加不改写：相邻调用互为前缀延伸」——**落本块的是视图面**：compaction 只产模型视图、`state.messages` 零覆盖（行为 9）；字段面 `specs/state.md` 行为 4、写入面 `specs/bookkeeping.md` 行为 7。请核「视图 vs 原史」的两层写法是否会被误读为绕过 pin-22。
   - `pin-24`（P1）＝「相位合同一次性：`contracts_appended` 标记——回炉轮不重发」——**起草稿核实＝不落本块**（记账 `specs/state.md` 行为 5／写入 `specs/bookkeeping.md` 行为 8／常量稳定 `specs/prompts.md` 行为 1；消费侧重发判定＝追加编排归 `orchestration`＋标记写入归 `bookkeeping`）。请核：prompts 挂钩表说「消费侧重发判定待 `context`／`orchestration` 规格」——本稿把它推给 `orchestration` 是否算「转走」、抑或应落本块（若是，缺少的器面是什么）。
   - `pin-26`（P1）＝「对话层纯度：`dialogue` 只装自然对话，过程记录入 `process_notes` 不混层」——**起草稿核实＝不落本块**（字段面 `specs/state.md` 行为 6／写入面 `specs/bookkeeping.md` 行为 9／渲染面 `specs/understanding.md` 挂钩表）。请核本块过程段候选（`render_process_notes` 输出）只作指令材料、不入 `dialogue` 的声明是否够。
   - `pin-30`（P2）＝「compaction 视窗预算触发摘要化＋v1 旧 run 黑匣子回放 dialogue 通道如实空显」——按 `docs/runtime-refactor/spec-review/state-评审.md` S-5 指「待 context 规格定稿时登记」，**本稿落 compaction 半面**（行为 9）；请核该半面是否落全（触发/保留/摘要形/披露/原史零覆盖），及与 `specs/persistence.md` 行为 12／`specs/state.md` 行为 8 的分工互认。

5. **`synth/S1` H6 覆盖（含 compaction）与越界**：`synth/S1` H6＝「材料渲染、过程档案（有界摘要）、常驻台账注入、对话链追加」（`context.py`＋`graph.py _render_process_notes/_resident_block`；票面面＝V2-38／79c／79d／80g／80h；P5b1 A-P5b1-09/11；ADR-0006）。起草稿落点＝材料渲染（行为 1–6）／过程档案（行为 8）／常驻台账注入（行为 10 装载面；渲染面按定界归 prompts）／对话链追加（行为 9；＋15 边界注）。**请核**：(a) 有无漏项——特别是 80g（变量后置/前缀稳定）在 80h 追加式下退役后是否仍有本块残留断言义务；(b) `_resident_block`（常驻块拼装单点）归 prompts 后本块是否保留任何义务（三来源行记账在行为 7）；(c) 有无把别的块的事写进来（`_render_process_notes` 的**消费点**（decision/clarify/toolmatch 拼接）是否已正确让渡给 prompts 的增量条装配）。

6. **数字／枚举单点（逐个可指真源、无裸字面值）**：起草稿出现的每个数字与枚举的锚点——十 kind 三族映射（`docs/runtime-refactor/recon/K-上下文事件指南预算.md` R-K-03）｜帽值 `DEFAULT_MAX_OBSERVATIONS`（R-K-07，「具体值不落本规格」）｜档案预算与头注（`docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md` `_PROCESS_NOTES_BUDGET`／`_PROCESS_NOTES_HEADER`）｜compaction 截数 120（`docs/runtime-refactor/arch/P5b3-票堆V2-79c至79d.md` A-P5b3-13）｜compaction 视窗数值两说（A-P5b3-11「4000 tokens」vs `docs/runtime-refactor/arch/P6a-票堆V2-80系列前半.md` A-P6a-11「8k tokens 档」——起草稿不写值、登记）｜三来源行（B2 R-B2-05）｜S3 D-02 三组帽分母（24/47、24/51、24/88——引用＋登记）。**请核**：有无遗漏锚的裸值；「具体值不落本规格」与「逐字形含 {step} 槽」两处留白是否会被阶段 5 施工按错源取值；`（合计入选 {K}/{总}）` 因闸转写是否可接受（见上文转写注）。

## 待填：评审发现清单

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| （待填） | | | | |

## 闸实跑记录（起草方，2026-10-15）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                   # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：21 份规格的真源引用与边界规则编号均可解析。  # exit 0
（首跑曾红一处：行为 6 `（合计入选 {K}/{总}）` 反引号 token 含「/」被当路径
 ——已把斜杠形移出反引号，复跑绿；转写注见上文）

$ uv run lint-imports --config tools/importlinter_v2.toml
R1…R8 全 KEPT（R2／R3／R4／R5／R5b／R6／R7／R8 亲跑）
Contracts: 18 kept, 0 broken.                              # exit 0
```

辅助取证（起草方实跑）：

- `grep -nE "尽量|合理|必要时|视情况" specs/context.md` → **0 命中（exit 1）**。
- `awk '/## 验收测试/,/## 依赖与风险/' specs/context.md | grep -c "::"` → **21**（验收表 21 行，含【边界集】／【保留集】两行）。
- `ls tests/domains/ | grep -c test_v2_context` → **0**（无同名文件，新建承诺成立）；`ls appv2/runtimev2/context/` → 仅 `__init__.py`（占位空包）。
- 实读逐字稿载体：`appv2/runtime/context.py`（材料段渲染全文＋`DEFAULT_MAX_OBSERVATIONS`／三档信任常量／十 kind 映射）；`appv2/runtime/graph.py` L1271-L1347（`_render_process_notes`／`_resident_sources`／`_resident_block` 逐字）；`tickets/v2/V2-61-材料承载分形渲染.md` 附 A／附 D（selected_reason／披露行／notice 载荷）。
- 亲读 `tools/importlinter_v2.toml`：R2（forbidden 含 `appv2.runtimev2.context.*`）／R5（source `appv2.runtimev2` 全体）／R5b／R6／R7 的 source 均含 `appv2.runtimev2.context`——「已真跑」五行属实；R4 的 source 只含 `state`、R8 只列三相位——起草稿「无禁引 gateway_adapter 专属闸」的诚实声明属实。

### 未验证清单

1. `tests/domains/test_v2_context.py` **不存在**、`appv2/runtimev2/context/` 仅占位 `__init__.py`——21 行验收测试只能核标识形态，无法实跑；边界闸对 context 是**契约空过**（与 state／prompts／parsing 同款），实现层真合规待阶段 5。
2. 行为 6 `selected_reason` 与行为 9 compaction 披露账目的**逐字拼装**（含槽位）——真源附 A／A-P5b3-17 为要点形带槽文案，施工逐字稿须以票面/方案原文为准（起草稿已声明载体，未逐字比对**全部**字符）；评审建议按 `specs/parsing.md` 先例要求「逐字稿载体＋差异点表」再核一遍。
3. 行为 9 compaction 的**触发参数承载位**（`dialogue_view_tokens` 在 V2 落 `state` `Budget` 键集之外／新字段／注入参数）——未定案（风险 4）；本稿按「注入制、无裸值」写，若评审认为该留白过大会给出可判性缺口。
4. 行为 10 loader 的 **tools 公开面调用形**（工具名/参形/async 形）——`tools` 规格为旧版式、V2 tools 卡只列 `ToolRegistry` 两方法；本稿按「经其公开面」写，具体调用形阶段 5／阶段 7 对账（风险 5）。
5. 行为 4 的「引擎侧已封顶」两句（agg 行集 `limit_effective` 上限／台账卡 ≤ discover 预算量级）——真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-44 为要点形；引擎具体上限值未在本块复述（属 `query` 面），未验证其与 V2 query 规格的数值一致性。
6. `synth/S3` **D-02 帽分母口径**（24/47、24/51、24/88）——属 Owner 待裁项（`docs/runtime-refactor/synth/S3-口径裁决清单.md` §二）；本稿只声明「帽只作用检索族、分母＝检索片段数」，报告分母口径未裁，未验证。
