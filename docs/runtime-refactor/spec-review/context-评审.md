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

## 评审产物（四片并行评审＋窗B 合并，2026-10-15）

> 评审方式：**分片并行**——A（骨架机械）／B（行为 1-7×真源）／C（行为 8-14×真源）／D（接口·卡·钉·交界·对账·幻影），四片独立子代理实读取证；本产物窗 B 合并去重、重编号 P-01…P-29（四片原始件在 A-01…／B-01…／C-01…／D-01…，合并映射见各行括注）。只产发现，未改任何现存文件。三闸由 A／C／D 三片各自亲跑均绿。

### 一、结论摘要

1. 版式骨架合格（十节逐字）；`spec gate` PASS；含糊词 0 命中；14 条行为均带【断言】；21 行验收全绑 `test_v2_context.py` 含边界集/保留集。
2. 三闸全绿（18/18 KEPT）；`appv2/runtimev2/context/` 占位空包＝契约空过。
3. **L0＝0**（核 D：六函数各有卡职责/测试计划承载或已入登记，对照 parsing P-01 判例**不构成卡缺公开成员**）；卡级登记两缺＝P-16（对话链追加职责改述＋族名单权威注）。
4. **高×1＝P-01**：行为 9 漏载 compaction **保留窗保证**（至少 1 轮／最新轮恒在场／单巨轮零压缩——V2-79d 有专门新钉，按现文施工可得「最新轮被摘要化」的实现）。
5. **中×15**：compaction 面五条（摘要承载位／识别面与调用点／无现状载体／selected_reason 合成与迁移不全）＋行为 7 三处断言无界/相抵（常驻行条件／source_id 空串／空投影 vs 零材料）＋签名真源标注过度与权威句对撞＋预算承载形／触发参数命名＋失败面新立无锚＋三来源行归属＋卡级登记缺。
6. **低×13**：缺省/异常三处·槽位归一·引注精度合辑·strip·实渲支·帽vs落引用注·pin-22 例外·execution 缺行·旧测试去留·render_task_book·{N} 一符两义·step 闭世界·agent-loop 两说。
7. 干净面：迁移照抄体例实（材料段逐字、附 A char 级核过、转写注亲验成立）；**幻影真源零命中**（D 片逐条实读）；pin 六钉钉号/优先级全对；与 prompts／answering／state／bookkeeping／transport／persistence 对账大体互认。

### 二、发现清单表（P-01…P-29）

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| P-01 | **高**（C-01＋D-07合） | **行为 9 漏载保留窗保证**：真源明定「保留窗自尾向前累积、**至少 1 轮——最新轮恒在场（哪怕单轮超预算）**；单轮独占预算（巨轮）＝原样放行零压缩」，V2-79d 有专门新钉（最新轮恒在场钉／单巨轮零压缩钉）；本稿无此三语，按字面施工可得「最新轮也被摘要化」 | `specs/context.md:103`；`arch/P5b3-票堆V2-79c至79d.md:44,:49`（A-P5b3-14／A-P5b3-19）；`tickets/v2/V2-79d-compaction摘要化.md`（§1.1 :29-30／验收 :52） | 行为 9 补三语＋验收行补两态（最新轮单轮超预算恒在场；单巨轮视图＝入参逐字） |
| P-02 | 中（C-02＋D-07半） | **摘要承载位与角色置位漏载**：真源＝摘要以 **system 消息置于角色红线 system 之后、近期轮之前**；本稿只写头与行形，无角色/位置判据 | `specs/context.md:103`；`A-P5b3-15`（P5b3:45） | 行为 9 补「摘要＝system 消息、置位红线后近轮前」＋断言按序列位 |
| P-03 | 中（C-03） | **「合同/相位包永不摘除」缺机械识别面与压缩调用点**：messages 条目只有 `[role, content]`、`contracts_appended` 不记链位——识别只能靠内容子串（恐撞行为 13）；压缩由谁调用未定（`bookkeeping.call_model` 无此面） | `specs/context.md:103,:111`；`tickets/v2/V2-80h:56-64`；`recon/I2b:40`；`specs/state.md:111` | 行为 9 声明识别面为**结构化**（调用方传入链位贡献表或链条目标记——落点登记风险 4 扩面；若采子串须扩行为 13 豁免面照 prompts 先例）＋声明压缩唯一调用点＝调用方 |
| P-04 | 中（C-04＋D-11合） | **「V2 定案签名（真源 A-P6b-24／34）」标注过度＋无差异声明**：A-P6b-24 只点名两个渲染器（`render_materials`＋`render_task_book`——后者不在名单且未注让渡）；六函数中五件系本规格自定/退役重建，头部「承载位换、内容零变化」与实况不齐；`render_process_notes` 相对 V1（去 `budget` 形参/下划线）无显式改动清单 | `specs/context.md:46-75`；`arch/P6b:85,:95`；`graph.py:1278-1279`；`arch/P5b1:93-94` | 头注改「名单＝本规格自定（V2 承载位设计），逐成员真源见各行注；`render_task_book` 归 prompts」＋逐件标「迁移/新增/重建＋显式改动」 |
| P-05 | 中（C-05＋D-01合） | **签名权威句对撞**：`:81`「签名以卡为准」vs `:42-44`「施工以 V2 定案签名」vs `:77`「实名与参形阶段 5 按卡定」——卡面唯一签名 `compile` 已退役，三句并存可导出「照卡实现 compile」 | `specs/context.md:41-44,:77,:81`；`specs/modules.md:407`；先例 `specs/parsing.md:85` | 照 SPZ-04 落法改分权句：「参数名与常量实名以卡为准；族与签名以『V2 定案签名』为准」；:77 同步 |
| P-06 | 中（C-06） | **行为 9「摘要形迁移照抄」无现状载体**：compaction 族已随 V2-80h 退役（现码无符号、有退役钉），「照抄」无对象 | `specs/context.md:103`；`appv2/runtime/context.py`（无 compaction 符号）；`tests/domains/test_v2_multi_turn_context.py:447` | 改「依票面重落（无现状载体）」；逐字稿载体点名 `tickets/v2/V2-79d-compaction摘要化.md` §1.1/§1.2＋A-P5b3-13/15/17 |
| P-07 | 中（C-07） | **selected_reason 两写者合成规则未写**：真源为**追加**（旧码 `reason = material_reason; if summary: reason += "；对话层 compaction：…"`）；本稿行为 6 锁逐字、行为 9 又令 disclosure 随它落——超窗调用同时命中两条逐字要求 | `specs/context.md:100,:103`；`A-P5b3-17`（P5b3:47）；旧 compile 尾段 | 行为 9 明写「追加于材料面之后（分隔「；」）」；行为 6 断言限定「无 compaction 态逐字」 |
| P-08 | 中（C-08＋D-03合） | **selected_reason 迁移不全**：只载附 A 带材料两形；**零材料步文案**（「步骤 {step}：理解步零材料渲染」）与**常驻注入后缀**（「；词典层常驻注入 {n} 块（ledger_dump 族——第 1 轮全量，非懒加载：注入不依赖未命中）」）两形未载（前者断言含零材料 fixture 但目标文本缺） | `specs/context.md:100`；旧码 else 分支与 extra 分支（git 历史态）；`tickets/v2/V2-61` 附 A（只材料分支） | 行为 6 补零材料文案（迁移照抄）；常驻后缀的 V2 适配（相位一次性）＝登记（风险 8 扩面） |
| P-09 | 中（C-09＋D-08合） | **行为 11 失败面系新立、无真源锚**：B2 只记疑点 D-B2-06（V1 无 try/except）；「失败→空投影、不炸链」为本规格新决策 | `specs/context.md:78,:105,:112`；`recon/B2:207` | 补锚（总纪律零编造＋A-P7a-37 类推）或标**待 Owner 过目**；写明「失败」判据面（随风险 5 落定） |
| P-10 | 中（C-13＋D-09合） | **三来源行归属分裂**：三元组（`ledger_dump`→`ledger_full_dump`／`alias_dump`→`ledger_aliases`／`schema_card`→`schema_cards`）记本块、常驻块渲染归 prompts（prompts 依赖白名单不含 context——不能互 import）；两处各写＝副本漂移风险；D-B2-09 记现状无消费者 | `specs/context.md:101`；`recon/B2:63-80`；`specs/prompts.md:86` | 声明三元组唯一定义点＝本块（两映射各一面、同源 dump schema）＋`::renderers_single_source` 覆盖＋括注「现状无消费者——本块重建该记账面」 |
| P-11 | 中（B-01） | **行为 7 常驻行条件未界**：三来源行绑在「投影非空」上未绑「当轮投入常驻块」——80h 下 answer 轮不投常驻块，按现文 answer 轮 Manifest 带 3 行＝归因不实且断言不可满足 | `specs/context.md:101`；`graph.py:1704/:2382/:2727`（携常驻）vs `:3876`（answer 只投材料） | 改述「本调用实投材料逐支＋**当轮投入常驻块时**三来源行」；断言按呼叫分型（answer 轮零常驻行） |
| P-12 | 中（B-02） | **行为 7「source_id 非空」断言与现状空串如实相抵**：V1 观察面明载空串为如实态（图谱无锚边），编译原样直投不筛空 | `specs/context.md:101`；`appv2/tools/handlers.py:884`；旧 compile 段 | 改「与观察 `source_id` 逐字对应（空串如实）」＋fixture 补空串态 |
| P-13 | 中（B-08＋D-04合） | **行为 7 空投影断言与行为 6 相抵＋零材料 reason 形缺**：「空投影→0/0/False」把「台账投影空」与「零材料」并置——有材料＋空投影时三字段非零必误红 | `specs/context.md:100,:101`；旧码 else 分支；`tickets/v2/V2-61:96-98` | 断言拆两句（零材料→0/0/False；空投影→零台账来源行、材料字段不动） |
| P-14 | 中（A-01＋C-12合） | **过程档案预算承载形/注入面未声明**：现状载体有注入缝（`budget=_PROCESS_NOTES_BUDGET`），本稿签名无 budget；「帽/视窗注入」行不含该值——阶段 5 照现状＝裸值 400 进新码 | `specs/context.md:57,:79,:102,:178`；`graph.py:1274-1281` | 照帽同款：预算经注入参数（无缺省）＋本块常量 `PROCESS_NOTES_BUDGET` 为数值单点；常量族与 `::cap_constant_single_point` 覆盖 |
| P-15 | 中（A-02＋C-15合） | **compaction 触发参数命名与真源口径名不一致且未登记**：本稿 `view_tokens`，真源 `dialogue_view_tokens`（A-P6b-29／A-P5b3-11） | `specs/context.md:66-67,:103`；`arch/P6b:90`；`arch/P5b3:41` | 签名参数改 `dialogue_view_tokens`（或风险 4 补更名登记） |
| P-16 | 中（C-17＋D-02合，卡级） | **卡级登记两缺**：①卡职责「对话链追加」的 V2 定界未入风险 7①（context 卡与 bookkeeping 卡职责行同载）；②补「公开面以本规格『V2 定案签名』为准（族名单闭世界）」注未登记 | `specs/context.md:149`；`specs/modules.md:402,:323-326` | 风险 7① 补两项（只登记，主窗派卡） |
| P-17 | 低（A-04＋C-11合） | 迁移缺省/异常三处未载：phase 缺省 `'?'`、content 缺省空串（R-K-20 已载可引）、`index` 缺失＝现状裸 KeyError | `specs/context.md:95,:102`；`graph.py:1289-1292`；`context.py:89,:94` | 行为 1/8 补缺省半句；错误契约补 index 缺失口径（差异声明） |
| P-18 | 低（A-03） | 槽位归一未声明：附 A 槽位系代码表达式（`{len(authority)}` 等），规格归一为 `{N}`／`{帽}`／`{M}/{N}`／`{K}/{总}`——转写注只说包裹符变更 | `specs/context.md:99,:100`；`tickets/v2/V2-61:70-81` | 转写注/风险 8 补槽位归一表句 |
| P-19 | 低（B-06＋B-07＋B-09＋C-10＋C-16＋D-10合） | **引注精度合辑六小处**：①红线原文插「若」＋省略（应逐字或标省略）；②行为 10「A-P4b-33」应 A-P4b-34；③行为 3 引 R-K-06（实为兜底条目）证确定性（应 A-P4b-48）；④行为 10／接口注「写手 H6」宜注 M2 旧写手被统一＋「取一次装载＝本规格定」声明；⑤来源行「R-B2-01…09」含 R-B2-09（N0 安检序，超 L1278-L1347 面）；⑥A-P4b-32 主语系样例渲染器未注 | 各处 file:line（B/D 片表内） | 六处随批改锚/补注 |
| P-20 | 低（B-05） | 行为 1 未落来源/井两段 `.strip()` 归一（空白串→空段跳过） | `specs/context.md:95`；`context.py:91-92` | 补半句（或标「按载体逐字含 strip」） |
| P-21 | 低（B-03） | 行为 7「材料逐支」未界定**实渲支**（V1 只逐实渲支入来源行；截断态判据缺） | `specs/context.md:101`；`recon/K:191`（R-K-24） | 改「实渲支」＋补截断 fixture 来源行数断言（随 P-11 合并落笔） |
| P-22 | 低（B-04） | walk §13-B／§14-B（Owner 2026-10-15：大结果落引用替代渲染帽裁剪）与行为 4 检索族支数帽的关系全稿无分工注 | `specs/context.md:23,:98`；`walk/裁决表.md:166,:176`；`specs/execution.md:81` | 补半句分工注（单支超阈落引用归 execution；检索族支数帽＝token 安全面存续） |
| P-23 | 低（D-05） | pin-22 触发点例外未登记：compaction 触发即视图重写（断缓存），「相邻调用前缀延伸」留痕断言在该点不成立 | `specs/context.md:103,:174`；`arch/P6b:90`；`tickets/v2/V2-80h:160-171` | 行为 9 补「触发＝显式例外（真源 A-P6b-29）；留痕前缀断言按此豁免」＋登记对账 |
| P-24 | 低（D-06） | pin-08 分工注「execution 侧」半符实况：`specs/execution.md` 挂钩表无 pin-08 行（行为 4 载同一规则） | `specs/context.md:173`；`specs/execution.md:130-148` | 措辞收窄＋登记交主窗回提 |
| P-25 | 低（A-06） | 归属注未提旧承载位既有测试（`test_v2_v61_material_rendering.py` 直引 V1 `render_materials`）的去留 | `specs/context.md:143`；`tests/domains/test_v2_v61_material_rendering.py:1-18` | 归属注补旧测试处置口径 |
| P-26 | 低（A-07） | A-P6b-24 的 `render_task_book` 无落地、未登记（specs 全零命中；其落点仅由「不做什么」推给 prompts） | `arch/P6b:85`；`specs/context.md:16` | 风险 7 补一行（归 prompts） |
| P-27 | 低（B-10） | selected_reason 形 `{N}` 一符两义（权威支数 vs 检索支数分母） | `specs/context.md:100`；`tickets/v2/V2-61:73-81` | 槽名区分（{A}／{R}）或注明「随位置指代」（随 P-18 槽位归一表落笔） |
| P-28 | 低（C-14） | `compile_manifest` 契约两缺：`step` 槽取值闭世界与越界行为未列；`ledger_dump` 参语义未写 | `specs/context.md:60-65`；`docs/spec-format.md` §二第 4 行 | 补 step 取值面（登记形或引真源）＋ledger_dump 参一句 |
| P-29 | 低（D-12，登记交主窗） | `specs/agent-loop.md` 行为 2 仍载 79a 形编译契约（「Context Builder 确定性编译」「[system]＋dialogue 截断」），与 state 行为 4（messages 整链）＋80h（compile 退役）两说（非本稿缺陷） | `specs/agent-loop.md:102-107` vs `specs/state.md:110` | 风险 7 登记（agent-loop 回提改述） |

**计数**：**L0×0／高×1（P-01）／中×15（P-02…P-16）／低×13（P-17…P-29），共 29 条**。

### 三、16 问逐条回答（四片合并）

1. 十节齐＋标题逐字 ✓（A 片 10/10 逐字符＋check_specs PASS）。2. 行为可 assert＋含糊词：0 命中；14 条均带断言；弱化点＝行为 4 括号理由（跨块事实）、行为 9 四处不可判（P-01/02/03/07）、行为 8 两留白（P-14）、接口 step/ledger_dump（P-28）——经处置可判。3. 数字机械归类：510 token 全量分类，**无锚裸配置值 0 条**；值类清单（rank 0/1/2、0/0/False、120、24 帽、24/47 等）全带锚；两处跨句指针形可内联。4. 不做什么承担者＋锚点：12 行俱带；plan/ranking 类无（本块）；row 1 锚点列加 understanding 行为 1 可补（未列条）。5. 框架红线：亲读 toml——R2 forbidden 含 context.\*、R5/R5b/R6/R7 source 含 context；「无禁引 gateway_adapter 专属闸」诚实声明属实（R4 只源 state、R8 只三相位）。6. 不降级静默：合法降级恰一处（行为 11）声明清晰；三面披露分工（模型面/机读/发射方）带断言；红线 A-P7a-37 语义一致、字面非逐字（P-19①）。7. 验收：21 行、id 唯一、边界集/保留集在、归属注在；外引 `::rowset_full_delivery` 实存。8. 挂钩表：22 行；「已真跑」5 行亲跑属实；「已进 CI」属实；人审行 4 带原因；注记级两处（:182 措辞、:178 指形）。9. 与 walk 冲突：无硬冲突；§13-B/§14-B 分工注缺（P-22）。10. S1 H6：四落点全落、越界零、80g 无残留义务、消费点让渡正确；未闭合＝P-10／P-16。11. 总纪律：零残留（行为 8-14 全机械；唯一风险＝行为 9 识别面——P-03 处置）。12. 卡一致：职责/接口两处△（P-16／P-05）；依赖/Seam/Adapter/测试计划四项有落。13. 已定稿对账（八份）：互认大体成立；三处缺口（P-24／P-29／P-23 例外登记）。14. 钉登记：六钉钉号/优先级全对；三缺口（P-23/P-24/P-01+P-02 落全性）。15. 幻影真源：**零命中**（代码行号/条目逐一实读实存）；引注精度入 P-19。16. 卡级问题：见五。

### 四、闸实跑记录（A／C／D 片亲跑，2026-10-15）

```
$ uv run python tools/check_specs.py → spec gate: PASS（0 警告）        # exit 0
$ uv run python tools/ref_resolvable.py check → 绿：21 份规格            # exit 0
$ uv run lint-imports --config tools/importlinter_v2.toml → 18 kept, 0 broken  # exit 0
```
辅助：含糊词 0 命中；验收 `::`＝21；`uniq -d` 空；`ls tests/domains/` 无 v2_context；占位空包核实；转写注探针（`resolve_ref_at("{M}/{N}")=None`）证明转写必要性成立；`git status` 干净（被评文本＝提交 94cdba3）。

### 五、卡级问题清单（只报不改）

- `## context` 卡（回阶段 2，主窗派卡）：①`compile` 初拟形标注（已登记）；②「术语表常驻注入」改述（已登记）；③**「对话链追加」职责改述未登记（P-16①）**；④`ContextBuilder` 去留（已登记）；⑤**族名单权威注未登记（P-16②）**。**无 L0 级缺件**。
- 已定稿侧登记（交主窗回提）：`specs/execution.md` 无 pin-08 行（P-24）；`specs/agent-loop.md` 行为 2 两说（P-29）＋挂钩表无 pin-24 行（本稿风险 7⑧ 已自登记）。

### 六、未验证/未证实清单

1. 21 行验收不可实跑（测试文件/空包）；边界闸契约空过。
2. compaction 触发参数数值（4000 vs 8k）与承载位无裁决文本（风险 4）。
3. loader 的 tools 公开面调用形未落定（风险 5；且 `dump_from_store` 现需 KnowledgeStore 实例、「经 tools 公开面」入口未证——可能须回阶段 2 定装载入口）。
4. 「引擎侧已封顶」的 V2 query 数值一致性未复证（V1 `QUERY_LIMIT_CAP=200` 实存）。
5. S3 D-02 帽分母未裁；行为 6 零材料文案/常驻后缀的 V2 沿用面无后继票面定案；行为 9 user 轮非问句适配未定。
6. 行为 11 失败语义与行为 7 三来源行两处新立性无直接裁决文本（P-09／P-10 处置为待过目/登记）。

---

## 七、逐条处置表（2026-10-15，窗 B 逐条处置——L0×0；高×1 采纳；中×15／低×13 全处置）

> 处置原则：规格文本改动逐条落笔（落法＝可逐字比对）；卡级登记（P-16）只登记（主窗派卡）；已定稿侧登记（P-24／P-29）交主窗回提；「待 Owner 过目」件 1（P-09 行为 11 新立失败语义）。

| 编号 | 处置 | 落法（逐字可比对） |
|---|---|---|
| **P-01**（高） | **采纳** | 行为 9 补保留窗保证三语（至少 1 轮／最新轮恒在场／单巨轮原样放行零压缩——A-P5b3-14/19）；验收 compaction 行补两态 |
| **P-02**（中） | **采纳** | 行为 9 补「摘要＝system 消息、置于角色红线之后、近期轮之前」（A-P5b3-15）＋断言按序列位 |
| **P-03**（中） | **采纳** | 行为 9 声明识别面＝**结构化**（调用方传入链位贡献表／链条目标记——落点登记，风险 4 扩面；不采内容子串）＋「压缩唯一调用点＝调用方」 |
| **P-04**（中） | **采纳** | 接口头注改「名单＝本规格自定（V2 承载位设计），逐成员真源见各行注」＋逐件标【迁移/迁移＋显式改动/重建】＋补 `render_task_book` 归 prompts 注 |
| **P-05**（中） | **采纳** | 接口 :77/:81 照 SPZ-04 分权句：「参数名与常量实名以卡为准；族与签名以『V2 定案签名』为准（卡面 compile 不施工）」 |
| **P-06**（中） | **采纳** | 行为 9 改「依票面重落（无现状载体）」＋逐字稿载体点名 V2-79d §1.1/§1.2＋A-P5b3-13/15/17 |
| **P-07**（中） | **采纳** | 行为 9 明写披露账目**追加于材料面之后（分隔「；」）**（A-P5b3-17）；行为 6 断言限定「无 compaction 态逐字」 |
| **P-08**（中） | **采纳** | 行为 6 补零材料步文案（迁移照抄「步骤 {step}：理解步零材料渲染」）；常驻后缀 V2 适配＝登记（风险 8 扩面） |
| **P-09**（中） | **采纳（待 Owner 过目）** | 行为 11 补锚（总纪律零编造＋A-P7a-37 同族）＋「失败」判据面（随风险 5）＋**待 Owner 过目**标注 |
| **P-10**（中） | **采纳** | 行为 7 声明三元组唯一定义点＝本块常量 `RESIDENT_SOURCE_ROWS`（两编码面各一面、同源 dump schema）＋`::renderers_single_source` 覆盖＋「现状无消费者——本块重建」括注 |
| **P-11**（中） | **采纳** | 行为 7 改述「实投材料（实渲支）＋**当轮投入常驻块时**三来源行」；断言按呼叫分型（answer 轮零常驻行） |
| **P-12**（中） | **采纳** | 行为 7 断言改「与观察 `source_id` 逐字对应（空串如实——图谱无锚边 V1 事实面）」 |
| **P-13**（中） | **采纳** | 行为 7 断言拆两句（零材料→0/0/False；台账空投影→零台账来源行、材料字段不动） |
| **P-14**（中） | **采纳** | `render_process_notes(state, *, budget)` 显式注入（无缺省）＋常量 `PROCESS_NOTES_BUDGET` 入常量族；行为 8／入参纪律／验收 :136 同步 |
| **P-15**（中） | **采纳** | 签名参数改 `dialogue_view_tokens`（V2 口径名）；风险 4 补更名注 |
| **P-16**（中，卡级） | **登记（不改卡）** | 风险 7① 补两项：④「对话链追加」职责改述；⑤族名单权威注（主窗回阶段 2 一并落） |
| **P-17**（低） | **采纳** | 行为 1 补 content 缺省空串（R-K-20）；行为 8 补 phase 缺省 `?`／title·digest 空串；错误契约补 index 缺失口径（V1 裸 KeyError 收口——差异声明） |
| **P-18**（低） | **采纳** | 行为 6 补**槽位归一表**（{A}＝权威/台账支数、{R}＝检索支数、{帽}、{K}、{总}——附 A 载体系代码表达式；转写声明入风险 8） |
| **P-19**（低） | **采纳（六小处）** | ①红线原文去「若」＋补省略标注；②行为 10 改锚 A-P4b-34；③行为 3 确定性锚改 A-P4b-48（R-K-06 系兜底条目）＋兜底 9 不可达注；④行为 10 补「统一形＝本规格定」＋M2 注；⑤来源行 R-B2 面注；⑥A-P4b-32 主语注 |
| **P-20**（低） | **采纳** | 行为 1 补来源/井 `.strip()` 归一半句 |
| **P-21**（低） | **采纳** | 并入 P-11（实渲支界定＋截断 fixture 断言） |
| **P-22**（低） | **采纳** | 行为 4 补 walk §13-B/§14-B 分工注（落引用归 execution；支数帽＝token 安全面存续） |
| **P-23**（低） | **采纳** | 行为 9 补「触发＝前缀延伸/缓存命中的显式例外（A-P6b-29）；留痕前缀断言按此豁免——对账 agent-loop 断言面」 |
| **P-24**（低） | **采纳＋登记** | 挂钩表 pin-08 行措辞收窄（execution 侧无钉行——登记交主窗回提） |
| **P-25**（低） | **采纳** | 归属注补旧承载位测试（`test_v2_v61_material_rendering.py`）去留口径（随阶段 5 迁移收口，本批不改） |
| **P-26**（低） | **采纳** | 风险 7 补⑨：`render_task_book` 归 prompts（落点登记） |
| **P-27**（低） | **采纳** | 并入 P-18（槽名 {A}/{R} 区分） |
| **P-28**（低） | **采纳** | 接口 `compile_manifest` 注补 `step`＝本调用步名（取值面随步记录面登记）＋`ledger_dump` 参语义（非 None＝投入常驻块→附三来源行） |
| **P-29**（低，登记） | **登记** | 风险 7 补⑩：`specs/agent-loop.md` 行为 2 两说（回提改述） |

**净结果**：29 条——规格侧改动 25 条；纯登记 2 条（P-16 卡级／P-29 已定稿回提）＋登记联动 2 条（P-24／P-08 半）；「待 Owner 过目」1 件（P-09）。无升 Owner 裁决项（除待过目件）。主窗回提清单：卡级三项（P-16＋既有登记）、execution pin-08 行（P-24）、agent-loop 行为 2＋pin-24 行（P-29＋7⑧）。

## 八、修复执行记录（2026-10-15，窗 B 直接落笔——处置表「落法」列即逐字替换依据）

- **已改 `specs/context.md`**：接口定义（卡面注保留；V2 签名块重写——逐件标【迁移/迁移＋显式改动/重建】＋`render_task_book` 归 prompts 注＋`render_process_notes(state, *, budget)`＋`dialogue_view_tokens`＋`compile_manifest` 两注＋常量族补 `PROCESS_NOTES_BUDGET`／`RESIDENT_SOURCE_ROWS`）｜接口 bullets（闭世界句分权、返回契约 A-P4b-32 主语注、入参纪律帽/预算/视窗、错误契约 index＋更名、真源句分权）｜行为 1（strip 归一＋content 缺省）｜行为 3（确定性锚改＋兜底注）｜行为 4（walk §13-B/§14-B 分工注）｜行为 6（{A}/{R} 槽位归一表＋零材料文案＋常驻后缀登记＋断言限定）｜行为 7（实渲支/常驻分型/空串如实/断言拆二/截断态/三元组单点）｜行为 8（budget 注入＋常量单点＋缺省回落）｜行为 9（保留窗三语/system 置位/识别面结构化/唯一调用点/依票面重落/追加合成/前缀例外/断言四态）｜行为 10（锚改 A-P4b-34＋统一形自定＋M2 注）｜行为 11（待过目＋失败判据）｜不降级节（红线原文逐字）｜验收表（:125 数行改述；compaction/manifest/cap 三行扩写）｜测试归属注（旧测试去留）｜风险 4（更名/识别面/例外）｜风险 7（①扩④⑤＋⑨⑩⑪）｜风险 8（槽位归一/改动清单/后缀登记）｜挂钩表 pin-08 行｜来源行 R-B2 面注。
- **未改**：`specs/modules.md`（卡级 P-16 登记交主窗派卡）｜`specs/execution.md`／`specs/agent-loop.md`（已定稿侧登记）｜任何主窗文件。
- **复跑（2026-10-15，窗 B）**：`check_specs` PASS（0 警告）／`ref_resolvable` 绿（21 份）／`lint-imports` 18 kept 0 broken；残留自查（旧措辞「view_tokens 非法」「签名以卡为准）」「R-B2-01…R-B2-09」「A-P4b-33 同族」「按卡定」）零命中；行为 14 条／验收 21 行计数不变。

---

## 九、复审结论（独立子代理，分片 R-A／R-B／R-C 三片）

- 日期：2026-10-15 ｜ 复审对象：`specs/context.md` 修订稿（diff 基线 94cdba3）｜ 方法：三片独立上下文——R-A 闭合 P-01…P-15／R-B 闭合 P-16…P-29／R-C 16 问复跑＋三闸亲跑＋修订引入面扫查。

### 九之一、闭合核验（P-01…P-29）

**R-A（P-01…P-15）：15/15 闭合。** 要点：P-01 三语逐字在＋验收两态在；P-02/03/04/05/06/07/08/09 逐条按落法落地（P-05 旧对撞句零残留）；P-10 主体三件在（残留：`RESIDENT_SOURCE_ROWS` 未入单点断言名单＝SPC-05）；P-11/12/13/14/15 闭合（14 五处同步齐）。
**R-B（P-16…P-29）：14/14 闭合。** P-16 登记在两处、卡未改（另注：`specs/modules.md` 的 parsing 卡 +6 行系他窗补录 821968f、非本修订）；P-17…P-29 逐条落笔（P-19③ 新误引〔V2-62〕、{M} 槽缺、P-19① 微残＝SPC-03/04/09）。
**净结果：29/29 闭合**；无未闭合项。

### 九之二、16 问复跑（R-C）

十节齐 ✓；含糊词 0 命中；数字新扫查点过（预算注入五处一致、槽位表在〔漏 {M}＝SPC-04〕、`dialogue_view_tokens` 四处一致旧词零残留）；不做什么 12 行俱带；红线闸名亲读 toml 逐条相符；不降级（红线引文仍有一处内插注＝SPC-09）；验收 21 行/唯一/边界集保留集在；挂钩表 pin-08 行收窄属实；walk 冲突重扫无新硬冲突；S1 H6 四落点全；总纪律零残留（识别面结构化后）；卡一致（L0=0、两缺登记）；九份对账无新增两头认；钉六枚全对＋pin-30 半面落全；真源实存（**幻影零命中**）；卡级 P-16 登记态。

### 九之三、新增发现清单（SPC-01 起——修订引入面）

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| SPC-01 | **中** | 行为 9 识别面承载与签名不闭环：声明「结构化（贡献表/标记）」，但签名无对应参量、条目字段面未定义——施工无合法通道，断言不可构造 | `specs/context.md:117`／`:73`／`:91`／`:166` | 补参形占位；不得改子串识别 |
| SPC-02 | **中** | 披露账目「追加于材料面之后」无执行者：`compact_messages` 只返回串、`compile_manifest` 无接收参量、`Manifest` frozen——验收行无施工面 | `specs/context.md:117`／`:64-67`／`:143`；`specs/state.md:108` | 点名执行者（调用方合成，同 `token_count` 回填先例） |
| SPC-03 | 低 | 风险 4 识别面误锚：「A-P5b3-14 语面」——该条无链位/合同语面；真源应 A-P6b-29 | `specs/context.md:166` vs `P5b3:44`／`P6b:90` | 改指 A-P6b-29 |
| SPC-04 | 低 | 槽位归一表漏 {M}（截断形 `{M}/{R}` 的 M＝实渲检索支数） | `specs/context.md:114`／`:170`；`V2-61:76` | 补 {M} 一行 |
| SPC-05 | 低 | `RESIDENT_SOURCE_ROWS` 无单点断言落点（`::renderers_single_source` 与红线枚举均未含） | `specs/context.md:86-88`／`:105`／`:151` | 两处枚举补「三来源行映射」 |
| SPC-06 | 低 | 风险 8 措辞「去 budget 形参」与实况（形参保留、去缺省）相抵 | `specs/context.md:170` vs `:59` | 改「去缺省值改注入制（形参保留）」 |
| SPC-07 | 低 | 风险 7① 内嵌④⑤编号断链（系评审文件卡级清单项号） | `specs/context.md:169` | 改注「卡级清单第 4／5 项」 |
| SPC-08 | 低 | 行为 7 断言 A/B 交叉态互斥（「首入恰 3 行」×「空投影零行」）缺「投影非空」条件 | `specs/context.md:115` vs `specs/prompts.md:86` | 断言 A 补条件 |
| SPC-09 | 低 | 红线引文内插编辑注未标记（P-19① 残留） | `specs/context.md:129` vs `P7a:98` | 编辑注移出引号/〔〕标注 |
| SPC-10 | 低 | 「非空即复用」×「{} 写回」→ 空投影逐轮重取未定 | `specs/context.md:118`／`:119`／`:145` | 明确「已取」判据＝`is not None` |
| （R-B 附）| 低 | 行为 3「A-P4b-48〔V2-62 事实面〕」误（实为 V2-61 块） | `specs/context.md:111` vs `P4b:128` | 改〔V2-61〕 |

**计数**：**SPC×10（中×2＋低×8）＋R-B 附 1（低）＝11 条**；无 L0、无高。另 R-A 残留（P-05 措辞观察）非缺口、随批可忽略。

### 九之四、闸实跑记录（R-A／R-C 亲跑）

```
$ uv run python tools/check_specs.py → spec gate: PASS（0 警告）
$ uv run python tools/ref_resolvable.py check → 绿：21 份规格
$ uv run lint-imports --config tools/importlinter_v2.toml → Contracts: 18 kept, 0 broken
```

### 九之五、复审判定

**规格侧：可定稿**（L0=0；29/29 闭合；三闸全绿）。**建议定稿前同批修**：SPC-01／02（两中件——断言可构造性）＋SPC-03（误锚）；其余八低随批。**L0 卡级状态**：P-16 两项系登记件（预期态，不阻规格文本；卡补录由主窗派窗 A）。

## 十、SPC 逐条处置与收尾执行记录（2026-10-15，窗 B 直接落笔）

| 编号 | 处置 | 落法 |
|---|---|---|
| **SPC-01**（中） | **采纳** | 行为 9 识别面句补参形占位：「标记随 `messages` 条目字段携带（键名随落点裁定落定），或由调用方以链位贡献表随调用传入；**参形随风险 4 落点裁定后入签名**〔登记〕」——断言可构造通道在 |
| **SPC-02**（中） | **采纳** | 行为 9 补「——由调用方（编排面）在合成最终 Manifest 时执行（同 `token_count` 回填先例；本块 `compact_messages` 只返回账目串）」 |
| **SPC-03**（低） | **采纳** | 风险 4 括注改指 A-P6b-29 |
| **SPC-04**（低） | **采纳** | 槽位归一表补「{M}＝实渲检索支数（＝min(检索支数, 帽)）」 |
| **SPC-05**（低） | **采纳** | 红线 bullet＋验收 `::renderers_single_source` 行两处枚举补「三来源行映射（`RESIDENT_SOURCE_ROWS`）」 |
| **SPC-06**（低） | **采纳** | 风险 8 改「去 `budget` **缺省值**改注入制（形参保留）」 |
| **SPC-07**（低） | **采纳** | 风险 7① ④⑤改注「卡级清单第 4／5 项」 |
| **SPC-08**（低） | **采纳** | 行为 7 断言 A 补「且投影非空时」 |
| **SPC-09**（低） | **采纳** | 红线引文改全文逐字引（「红线——不许静默：…（对齐 V2-53…）」）＋示意形注移出引号用〔〕 |
| **SPC-10**（低） | **采纳** | 行为 10 复用判据改「**非 None 即原样复用**（含空投影 `{}`＝已取之空态）」＋验收 :145 同步 |
| （R-B 附） | **采纳** | 行为 3 改〔V2-61 事实面〕 |

**净结果**：11 条全部采纳（10 项直接落笔＋1 处编号勘误）。**context 规格侧工序完结**：29/29 闭合＋SPC 全清＋三闸绿＝规格文本层可定稿；卡级登记（P-16 等）与回提件（P-24／P-29）交主窗。**收尾复跑（窗 B）**：`check_specs` PASS／`ref_resolvable` 绿（21 份）／`lint-imports` 18 kept 0 broken。

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
