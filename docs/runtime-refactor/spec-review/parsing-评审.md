# parsing 规格评审（独立评审代理用）

- 日期：2026-10-15 ｜ 状态：**框架已建，发现清单待填（本文件由起草方留空，评审代理填）**
- 被评对象：`specs/parsing.md`（起草稿——十节版式，真源 `docs/spec-format.md`）
- 评审工序：起草 → **独立评审** → 逐条处置（L0 必须清零）→ 修订 → 复审 → 定稿（真源 `docs/runtime-refactor/规划.md` §三 工序纪律六步）
- 评审人纪律：全新上下文、只产发现不改任何现存文件；每条发现带证据锚点＋建议处置；**L0 清零前 `specs/parsing.md` 不得定稿**。

## 评审基准（只读参考）

- 版式与三判据：`docs/spec-format.md` §二（十节硬要求）／§二之二（节标题逐字）／§三（可判真伪／数字单点／闸在前面）
- 块真源：`specs/modules.md` `## parsing` 卡（职责／公开接口两函数／依赖／Seam／测试计划「缺字段／超限／引号异常分支；同类行多次出现不静默覆盖」）；`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §三 B
- 归责尺子：`docs/runtime-refactor/walk/判断归责表.md`——parsing 是**纯结构判定块**，**重点扫「解析滑成程序语义判断」与「语义判断误落本块」两侧**
- 行为真源抽查面（起草方实读并锚，供评审代理抽查）：
  - 解析现状：`docs/runtime-refactor/recon/A1-头部常量与解析校验.md`（R-A1-12…R-A1-36＋D-A1-01…D-A1-18）、`docs/runtime-refactor/recon/L1a-子任务前半.md`（R-L1a-01…R-L1a-41）、`docs/runtime-refactor/recon/L1b-子任务后半.md`（R-L1b-01…R-L1b-21）、`docs/runtime-refactor/recon/C-理解与legacy决策节点.md`（R-C-09／R-C-10／R-C-24）、`docs/runtime-refactor/recon/E1-澄清节点.md`（R-E1-10…R-E1-16）、`docs/runtime-refactor/recon/E2-工具匹配节点.md`（R-E2-04…R-E2-07）、`docs/runtime-refactor/recon/I2b-RunState全字段.md`（`executed_payloads`／`empty_probes` 字段面）
  - 决策面：`docs/runtime-refactor/walk/04-理解-读题步.md` §七（统一 JSON Owner 直令）、`docs/runtime-refactor/walk/05-理解-定路由.md` §七（解析严格、不取默认）、`docs/runtime-refactor/walk/09-澄清-分解问题.md` §七（子问题无依赖）、`docs/runtime-refactor/walk/11-匹配-工具阀.md` §七与末「补注」（参数枚举收紧）、`docs/runtime-refactor/walk/裁决表.md` §04-B／§07／§11＋项目级裁决 #12/#13
  - 治理票：`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`（A-P4b-10/11/12 拒因带定位；A-P4b-37/38/39 引号三层；A-P4b-13 回喂线）、`docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md`（A-P6b-05 机器拒因原文零改动；A-P6b-24/34 迁移文本不变）
  - 单元归属：`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md`（H4 解析与载荷定型（主体＝A1 L392-665）＋H11 子任务与发射 schema（L1a/L1b 全部）；表 B：V2-37 指纹面→H4）、`docs/runtime-refactor/synth/S4-调用图.md`（节点→helper 面；结构-1 legacy decision 整体废弃）
  - 已定稿消费方对账：`specs/understanding.md`（接口定义／行为 5／7／错误契约）、`specs/clarification.md`（接口定义 `ClarifyOutcome`／行为 8）、`specs/tool_matching.md`（接口定义／「不做什么」行／风险 4——「闸件本体归 parsing（发射指纹）＋ state（限额）」）、`specs/answering.md`（行为 11／14——发射剥离与回声观测面）、`specs/state.md`（行为 10 限额键面）、`specs/execution.md`（行为 13 空手指纹闸）、`specs/agent-loop.md`（行为 3「decision 出口同参重投闸保留」）
  - 交叉核对（起草方实读，确认**零落点**）：`docs/runtime-refactor/walk/02-理解-词面安全阀.md`、`docs/runtime-refactor/walk/03-理解-禁用词闸.md`（两道闸族归 `gate`／模型侧，parsing 无落点——评审可复核该判定）
  - 逐字稿载体（V1 现行代码）：`appv2/runtime/subtask.py`（L48-L58 常量／L61-L110 提取与拒因带定位／L116-L176 载荷类／L179-L290 澄清面／L296-L375 匹配面／L381-L428 引号自修）
- 钉清单：`docs/runtime-refactor/eng/04a-应钉行为清单.md`（**起草方核实结论：pin-04／pin-13 均不落本块**——见「重点核对项」5）
- 双闸＋边界闸（评审人本地复跑，命令与期望输出见起草方留档）：
  - `uv run python tools/check_specs.py`（期望 PASS 0 警告）
  - `uv run python tools/ref_resolvable.py check`（期望绿）
  - `uv run lint-imports --config tools/importlinter_v2.toml`（期望 Contracts: 18 kept, 0 broken）

## 重点核对项（起草方自评风险，供优先看）

1. **卡与规格分叉（返回形＋成员展开＋载荷类定义点）**：卡面公开接口为两函数且 `parse_question_group` 为**初拟返回形**（问题组容器单件），本规格按 V1 逐字迁移形（四动作定形＋拒因正文）展开族名单（`parse_tool_match`／共用件三件／载荷四类／指纹器材四件），并宣告载荷定型类**物理定义点在 parsing**（依据＝卡面 `parse_understanding` 已在本块引用 `Understanding | Direct` ＋R3 禁 parsing 引 understanding 的组合推论）。请评审判：①族成员展开是否属卡面职责（「模型输出解析、发射 schema 校验、子任务与问题组载荷定型」）的具体化（判例参照 `docs/runtime-refactor/spec-review/prompts-评审.md` P-08「非新公开类型」）还是构成卡缺公开成员（判例参照 `docs/runtime-refactor/spec-review/state-评审.md` S-2）；②`parse_question_group` 返回形差异「以卡为准」还是「以迁移照抄为准」；③载荷类定义点宣告是否越出本块单写者权限（登记件是否足够）。
2. **迁移照抄 vs 数字单点两处相抵**：行为 7 断言拒因正文「逐字迁移、零改动」（A-P6b-05），但 V1 预算拒文内嵌数值（载体 L258-L261）与 V1 缺省裸字面（D-L1a-12）在「数字单点」判据下是病灶；行为 16 声明「待裁」。请评审：该双轨（照抄＋差异点登记）是否有自相矛盾处、行为 4／7／16 三处是否口径一致；另核「V2 定案差异点②」（V1 两处裸抛收口为拒因）是否属未授权改形。
3. **与消费方交接面三处未定案**：①拒因正文（`str`）↔ `clarification` 的 `ClarifyRejection`／`tool_matching` 的 `ToolMatchRejection` 转换点归属（风险 5）；②理解面 `None`→`UnderstandingParseError` 的分工（本块不抛 vs understanding 抛，风险 6）；③同参重投闸的触发面与拦截落点（本块只锁指纹器材纯函数面——`specs/tool_matching.md` 风险 4／`specs/execution.md` 行为 13／`specs/agent-loop.md` 行为 3 三处对读，风险 4）。请评审逐条判「两头都认／两头都不认／一头认得住」。
4. **闸半覆盖与降维诚实性**：**亲读 `tools/importlinter_v2.toml` 核实**——R2（forbidden 含 `appv2.runtimev2.parsing.*`）／R3（source 含 `appv2.runtimev2.parsing`，forbidden 恰七个业务相位）／R5b／R6／R7 的编号与覆盖面是否与规格挂钩表逐行相符；「R3 半覆盖」声明与「零模型面无专属闸（R8 只列三相位）」声明是否属实；「禁手写替代（共用件单点）」无闸、只靠 `::shared_helpers_single_source` 测试的降维是否充分。注意：`appv2/runtimev2/parsing/` 现仅有占位 `__init__.py`——边界闸对本块是**契约空过**（同 prompts 评审先例）。
5. **pin-04／pin-13 核实结论自曝（起草方逐条核实：两钉均不落本块）**：pin-04「发射 JSON 不得进答案面（emission_strip 确定性剥离）」——落点在 `specs/answering.md` 行为 11＋其挂钩表（已定稿在册，测试 `::emission_strip_zero_leak`），剥离动作属答案面（起草／收口相位），**不落 parsing**；pin-13「起草回声=0（`echo_flag` 恒 0）」——两侧已落：合同侧 `specs/prompts.md` 行为 13（动词钉死句＋答案要求⑦），观测面 `specs/answering.md` 行为 14（测试 `::echo_flag_zero`），**parsing 无第三面缺口，本块不挂**（防一头两认）。请评审复读 `docs/runtime-refactor/eng/04a-应钉行为清单.md` :13／:22 两行原文与上述两侧登记，判「不落本块」是否成立（漏挂／错挂两向）。
6. **真源缺口（起草时未决——评审可直接查红/黄）**：①预算拒因内嵌数值是否可插槽化（无裁决文本；`docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md` A-P6b-05 只说「机器拒因原文零改动」）；②JSON 重复键形（解析后取后者）无真源裁决——卡面测试计划「同类行多次出现不静默覆盖」的 V2 对应面（风险 7⑥）；③`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md` H4「载荷指纹」与行为 13 器材名单的粒度（`is_same_param_replay` 是否属「器材」）无反证文本；④子问题条数上限（`MAX_SUBTASKS_CONTRACT` 的 V2 承载位）——`specs/state.md` 行为 10 键面读数与 `docs/runtime-refactor/walk/裁决表.md` §06-A 五项均未含它，行为 16「取自 state 限额单点」的落点待落定。

## 评审产物（四片并行评审＋窗B 合并，2026-10-15）

> 评审方式：**分片并行**——A 片（骨架与机械面）／B 片（行为 1-9×真源）／C 片（行为 10-末×真源＋迁移/单点＋缺口）／D 片（接口·卡·闸·钉·对账·幻影），四片各为独立子代理（全新上下文）分别实读取证，本产物由窗 B 合并去重、重编号 P-01…P-24。只产发现，未改任何现存文件。三闸由 A／D 两片各自亲跑，均绿。

### 一、结论摘要

1. **版式骨架合格**：十节齐、标题逐字、顺序正确；`spec gate` PASS（0 警告）；含糊词 0 命中；18 条行为均带【断言】；28 行验收全绑 `test_v2_parsing.py` 且含边界集/保留集。
2. 三条闸实跑**全绿**：spec gate PASS／ref_resolvable 绿（20 份）／lint-imports **18 kept, 0 broken**（R2／R3／R5b／R6／R7／R8 均 KEPT）；`appv2/runtimev2/parsing/` 为占位空包＝**契约空过**。
3. **L0×1**：**P-01**——指纹器材四件＝卡缺公开成员（S-2 类）：`## parsing` 卡三面与阶段 2 草案零承载，归属仅由 `specs/tool_matching.md` 风险 4 的 L0 裁决＋`synth/S1` H4 外部分派，本该随该 L0 裁决补录卡面而未录。**L0 清零前本规格不得定稿**（回阶段 2 补卡，登记交主窗）。
4. **高×1**：**P-02**——行为 3／11（兼验收 :127）保留 V1 `Subtask.tool` 字段与 `tool` 闭世界校验，与 Owner 项目级裁决 #10（`CONTEXT.md` 词条「**不含 `tool`**（Owner 2026-10-15 裁定）」；clarification 的 `Subtask` 无 tool；agent-loop「已去 `tool`」）相抵——按现稿实现＝澄清相位回归「模型提议 tool」旧形。
5. **中×8**（P-03…P-10）：max_subtasks 承载指认不实（三片同报）／接口未逐字落 V2 签名／载荷类口径与两份已定稿类体不一致／数字单点两解各破一断言（互斥未消）／args 新分支无拒因字面／引号自修编排无承载位／拒因转换点「两头都不认」／同参重投闸触发面「两头都不认」。
6. **低×14**（P-11…P-24）：引注精度·归一措辞·计数器·豁免面白名单等随批级。
7. 评分要点：**迁移照抄体例执行得实**（13 处拒文抽查逐字相符、差异点表五点+两点可审计）；真源锚实读抽查全实存（幻影真源零命中）；pin-04／pin-13「不落本块」两向核实成立；04a 全表 31 钉扫漏仅 pin-06（登记级）。

### 二、发现清单表

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| P-01 | **L0**（卡级，只登记） | **指纹器材四件（`payload_fingerprint`／`discover_fingerprint`／`emission_fingerprints`／`is_same_param_replay`）＝卡缺公开成员（S-2 类）**：`## parsing` 卡职责／接口／测试计划三面与阶段 2 草案均无「指纹／同参／重投」承载，归属仅由 `specs/tool_matching.md` 风险 4 的 L0 裁决＋`synth/S1` H4 外部分派——本该随该 L0 裁决补录卡面而未录。**L0 清零前本规格不得定稿** | `specs/modules.md:379-395`（亲核零命中）；`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md:54`；`specs/tool_matching.md:26,:127`；`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md:39,:104`；判例 `docs/runtime-refactor/spec-review/state-评审.md` S-2 | 回阶段 2 补卡（登记交主窗派窗 A；本规格不改卡）：补录指纹器材四件＋V2 定案公开成员（`parse_tool_match`／`ClarifyEmission`／`Subtask` 等）＋返回形勘正（`-> ClarifyEmission | str`）；或卡面注记「族名单以 parsing 规格接口定义为准（闭世界）」＋逐成员补录 |
| P-02 | **高** | **行为 3／11（兼验收 :127）保留 V1 `Subtask.tool` 字段与 `tool` 闭世界校验，与 Owner 裁决 #10＋三处已定稿文本相抵**：`CONTEXT.md`「不含 `tool`（Owner 2026-10-15 裁定）」；`specs/clarification.md` 的 `Subtask` 无 tool 字段；`specs/agent-loop.md`「已去 `tool`」。按现稿实现＝澄清相位回归「模型提议 tool」旧形，功能性背离裁决；差异点表未列该退场 | `specs/parsing.md:91,:99,:127,:77`；`CONTEXT.md:22`；`docs/runtime-refactor/walk/裁决表.md:20`（#10）；`specs/clarification.md:51-55`；`specs/agent-loop.md:84`；V1 载源 `appv2/runtime/subtask.py:120-124` | 修订：行为 3 删 `tool` 越界分支（`tool` 键＝未知键静默丢弃）；行为 11 字段表去 `tool`、投影改「恒三键＋`chain` 真值才出」；验收 :127 缩面（仅 chain）；差异点表补「`Subtask.tool` 退场（裁决 #10）」 |
| P-03 | 中 | **「`max_subtasks` 解析默认上限取自 `state` 限额单点（真源 state.md 行为 10）」指认不实**（三片同报）：state 行为 10 键集＝七键闭世界无子问题条数（全文零「子问题」）；已定稿侧口径＝clarification 行为 7「条数键两源未单列，数值真源 `walk/09` §七 Q-C」＋`eng/00` F-14「统一预算表（…子问题 ≤4…）是唯一数值真源」；行为 16 断言「默认参数取值＝state 常量」对该值不可满足 | `specs/parsing.md:91,:104,:161`；`specs/state.md:105-115`；`specs/clarification.md:50,:84`；`docs/runtime-refactor/walk/09-澄清-分解问题.md:79`；`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md:71`（F-14，亲核）；`appv2/runtime/subtask.py:30` | 修订：行为 3／16 对 `max_subtasks` 改述「数值真源＝walk/09 §七 Q-C＋F-14 统一预算表口径；state 承载键未落定（风险 7⑤）」；`max_discovers` 半边指认成立、保留；登记交主窗落定承载位 |
| P-04 | 中 | **接口定义未逐字落 V2 定案签名**：卡面初拟形（`-> QuestionGroup | None`）逐字照录，V2 定案形（`ClarifyEmission | str`＋keyword 限额参数）散在注／入参纪律／行为内，无签名行可施工；「卡面签名以卡为准」与「V2 定案返回形与卡不同」并存，实现者不知照哪个 | `specs/parsing.md:40-44,:74,:90-95,:104`；`specs/modules.md:384-385`；V1 实读 `appv2/runtime/subtask.py:226-232`；`specs/clarification.md:42-68` | 判「以迁移照抄为准」：接口定义补 V2 签名行（参数名以卡为准）；卡面两函数注「初拟形（阶段 2），施工以 V2 签名为准」；卡级登记随 P-01 同批（若判卡为准＝推翻已定稿 clarification 接口面，成本否决） |
| P-05 | 中 | **载荷类消费面口径三处不一致（登记不足）**：①行为 12「同物一套形状」只锁 Understanding／Direct 两类，未覆盖 Subtask／SubtaskMatch／ClarifyEmission；②两份已定稿接口定义的类体与行为 11 字段表逐字不一致——clarification `Subtask`（无 tool、chain 必填形）vs 行为 11（`chain=""`、含 tool）；tool_matching `SubtaskMatch`（`caliber_key: str\|None`、`plan: QueryPlan\|None`）vs 行为 11（`caliber_key=""`、`plan: dict\|None`）；③风险 3「三份规格消费面视图措辞」实读零「视图」措辞 | `specs/parsing.md:100,:157`；`specs/clarification.md:49-59`；`specs/tool_matching.md:46-65` | 修订：风险 3 改述为字段/类型差异清单＋「消费面形状以本规格行为 11 为准」；行为 12 扩面（五类逐类）；登记交主窗（阶段 7 对账把两份已定稿类体回改为引用句） |
| P-06 | 中 | **数字单点两解各破一条断言（互斥未消）**：行为 16「本块源码无裸上限字面（扫描）」vs 行为 7「全部拒因文本逐字迁移、零改动」（保留预算拒文内嵌「全 run ≤10」）互斥；`ask` 边界「2~4」同类却完全未入登记（风险 7② 只含预算件）且无真源锚；验收 `::limits_from_state_constants` 扫描范围未定豁免面 | `specs/parsing.md:104,:95,:92,:93,:142`；`appv2/runtime/subtask.py:259,:288-289`；`docs/runtime-refactor/recon/E1-澄清节点.md:87`；`docs/runtime-refactor/recon/L1a-子任务前半.md:206` | 修订：①扫描断言限定豁免面（迁移照抄的拒文与 `ask` 边界字面）；插槽化待主窗裁、裁定后随批收窄——两解不得并存；②`ask`「2~4」补真源锚（R-L1a-38…41／R-E1-10）并纳入数字单点登记（风险 7② 扩面）；③验收行补扫描范围声明 |
| P-07 | 中 | **差异点②「`args` 非对象＝拒」新分支无拒因文本真源**：V1 该形为裸抛（D-L1a-10），迁移载体无此字面；「对齐同族 R-A1-31 口径」的现形文本在决策面 `graph.py:617`（跨面借文，未显式 adopt 字面）；行为 7 golden「与迁移前快照逐字相等」对该新分支无快照可依 | `specs/parsing.md:92,:77,:95`；`appv2/runtime/subtask.py:266`；`appv2/runtime/graph.py:617`；`docs/runtime-refactor/recon/L1a-子任务前半.md:211` | 修订：行为 4 明写该分支拒文＝R-A1-31 同族文本逐字（指名 `graph.py:617` 形，**待主窗过目**）；golden 行补该分支期望文本来源 |
| P-08 | 中 | **引号自修受理编排（单包装器）在 V2 无承载位**：V1 单点 `_parse_with_quote_repair`（修复→重解析一次→首拒因保留→受理标志）＋notice，入口共用；真源明言「单函数三调用不复制三份」（A-P4b-39）。本块族名单只有纯函数 `repair_inner_quotes`，「不做什么」只退 notice——消费方各自实现＝同形副本（违 A-P4b-39）；理解面是否受理自修亦未声明 | `specs/parsing.md:98,:106,:21`；`appv2/runtime/graph.py:392-408,:411-417`（调用点 :1728/:2425/:2736）；`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md:108`；`docs/runtime-refactor/recon/E1-澄清节点.md:88`；`docs/runtime-refactor/recon/E2-工具匹配节点.md:69` | 修订：接口／行为 10 补编排归属（入族名单作成员，或明定归 `orchestration` 经同一入口调用）＋定「理解面是否受理自修」（V1 事实面：否）；若归本块同批对账消费方 |
| P-09 | 中 | **拒因正文 `str` ↔ `ClarifyRejection`／`ToolMatchRejection` 转换点＝「两头都不认」**：parsing 不认领（风险 5 明写未定案）；clarification 错误契约写「返回 `ClarifyRejection`」未提 str 输入面且其 reasons 枚举横跨两块；tool_matching 同形未切转换面 | `specs/parsing.md:72,:73,:159`；`specs/clarification.md:65,:57`；`specs/tool_matching.md:70,:22` | 登记交主窗三选一定案（转换在消费方／结构化拒因相位自建＋str 作回喂正文／转换归 parsing 回阶段 2 改卡）；本规格侧按裁定落笔 |
| P-10 | 中 | **同参重投闸触发/拦截/回喂面＝「两头都不认」**（指纹器材面两头都认）：parsing 明示不认领（风险 4）；tool_matching 自认「被拦位、不实现」；execution 行为 13 系另一闸（空手同参）；agent-loop 行为 3「decision 出口」在 legacy 废弃后 V2 无落点（`synth/S4` 结构-1） | `specs/parsing.md:27,:101,:158`；`specs/tool_matching.md:26,:127`；`specs/execution.md:90`；`specs/agent-loop.md:119`；`docs/runtime-refactor/synth/S4-调用图.md:105` | 登记交主窗裁定落点（含与 S4 结构-1 决策语义并入澄清相位的衔接）；对应块规格补行为＋测试；agent-loop 行为 3 表述同批回提 |
| P-11 | 低 | 行为 6 括注两处不实：R-A1-36 系 `parse_decision`（legacy 决策面）条目（匹配面对应事实锚＝D-L1b-03，其自陈「下游是否补检＝段外未证」）；「其余必填键（`ranking` 等）→ 工具层」与已定稿 tool_matching 行为 4（相位自身「参数强校验」＋验收 `::ranking_direction_paired`）互为排他归属 | `specs/parsing.md:94,:22`；`docs/runtime-refactor/recon/A1-头部常量与解析校验.md:344`；`docs/runtime-refactor/recon/L1b-子任务后半.md:86`；`specs/tool_matching.md:88,:110` | 采纳：行为 6 括注改锚 D-L1b-03 并注「落层归属待对账」；`ranking` 归属与 tool_matching 行为 4 同批对账（登记交主窗，阶段 7 销项） |
| P-12 | 低 | 行为 2 括注「登记件风险 7①同族」指向不明（风险 7①＝卡面勘正，不含「未知键静默忽略」该 V1 事实 D-L1a-14）；且「未知键静默忽略」与不降级节「不静默丢字段」边界未写明（「字段」是否含 schema 外未知键无界定） | `specs/parsing.md:90,:110,:161`；`docs/runtime-refactor/recon/L1a-子任务前半.md:215` | 采纳：括注改明确；补边界句「字段＝schema 内键；schema 外未知键忽略为 V1 事实面，非静默丢字段」 |
| P-13 | 低 | 引注精度四处：①行为 7 条目区间 R-L1a-16…41 未含定位族 R-L1a-06…08；②断言行 R-L1a-28（提取失败 fallback）误配「预算拒前缀」（应为 R-L1a-32）；③行为 7 载体列表缺 L82-L110（`json_syntax_feedback` 本体，含未逐字引的两句）；④接口②／行为 10「A-P4b-37/38」混列（37＝②层合同侧引号规矩、38＝③层自修；真源为 38） | `specs/parsing.md:95,:96,:53,:98`；`docs/runtime-refactor/recon/L1a-子任务前半.md:69-71,:194,:198`；`appv2/runtime/subtask.py:82-110`；`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md:106-107` | 采纳：四处随批改锚（行为 8 补「按 L104-L108 逐字照抄」句或行为 7 载体补 L82-L110） |
| P-14 | 低 | 「归一」措辞三处不齐：行为 3 `chain`／`tool` 未写「归一后」（V1 `str(x or "").strip()`）；行为 6 `caliber_key`「非空串原样」漏去空白归一（空白串 V1 归一为空串、投影不出键） | `specs/parsing.md:91,:94`；`appv2/runtime/subtask.py:207,:210,:364,:313-314`；`docs/runtime-refactor/recon/L1a-子任务前半.md:157-159`；`docs/runtime-refactor/recon/L1b-子任务后半.md:80` | 采纳：行为 3 `chain` 补「归一后」；行为 6 `caliber_key` 改「经 `str().strip()` 归一后零值域校验装载」 |
| P-15 | 低 | 行为 5 未声明 `options` 非 list 归一（V1：非 list→空列表→按个数越界拒，D-L1a-11）；按现文实现可能裸抛（违本块「不裸抛业务异常」承诺面） | `specs/parsing.md:93,:72,:73`；`appv2/runtime/subtask.py:280-285`；`docs/runtime-refactor/recon/L1a-子任务前半.md:212` | 采纳：行为 5 补「非 list（缺失／None／标量）→ 归一为空列表（随后按个数拒）」 |
| P-16 | 低 | 「共用件三解析入口」与行为 9「两发射面共用同一件」口径不齐（第三入口未列明；V1 三入口含已退场 `parse_decision`；理解面是否使用提取/自修件未列明） | `specs/parsing.md:53,:97,:106,:77,:141` | 采纳：改述为「两发射面共用（V1 三入口含已退场 `parse_decision`——差异点⑤）」；理解面零使用声明 |
| P-17 | 低 | 差异点清单自称「迁移照抄之外的改动全在此列」但漏列两条：指纹四件私有→公开去下划线；`is_same_param_replay` 形参由 `emission` 改 `fingerprints` | `specs/parsing.md:60-65,:77`；`appv2/runtime/graph.py:537-571`；`docs/runtime-refactor/recon/A1-头部常量与解析校验.md:250-302` | 采纳：差异点补两条（或在族名单成员注释逐件标） |
| P-18 | 低 | 行为 17 与卡面测试计划映射不齐：行为 17 只覆盖重复 id；JSON 重复键半面「待裁」未标 V1 病灶锚（D-A1-09＝两行式同类行后覆盖前，随行为 1 退场）；不降级节映射行口径过宽 | `specs/parsing.md:105,:113`；`specs/modules.md:395`；`docs/runtime-refactor/recon/A1-头部常量与解析校验.md:197` | 采纳：映射行拆两半（重复 id＝行为 17；JSON 重复键＝风险 7⑥ 登记）＋登记处补 D-A1-09 锚 |
| P-19 | 低 | 行为 4 断言「四型拒各自落对」与自身五型拒（非空数组／单次上限／预算／支缺 `tool`／`args` 非对象）及验收五项不符（「四型」系 V1 残留计数） | `specs/parsing.md:92,:128` | 采纳：按 P-02／P-07 定文本后同步计数（五型） |
| P-20 | 低 | 行为 14 豁免面枚举含本块不存在面（「逐字子串校」「数字／ASCII 形判定」——属他块），空白授权将成 AST 测试白名单 | `specs/parsing.md:102`；`specs/tool_matching.md:88`；`appv2/runtime/subtask.py:23-25` | 采纳：豁免面收窄为本块实际形态（闭世界成员判定／字符串归一／字符扫描） |
| P-21 | 低 | R3 半覆盖枚举「禁引公共层其余块」括注列 7 名，实为 8 块面（漏 `prompts`） | `specs/parsing.md:82,:170`；`tools/importlinter_v2.toml:80-85` | 采纳：枚举补 `prompts` |
| P-22 | 低 | pin-06（空手探查记指纹）为唯一触本块器材面的钉，现注册于 execution＋state 字段面——parsing 不挂可接受，但挂钩表未设分工注，「同参」两闸（V2-37 载荷指纹 vs 空手闸 `discover_fingerprint`）易混 | `docs/runtime-refactor/eng/04a-应钉行为清单.md:15`；`specs/execution.md:90,:145`；`specs/state.md:198`；`specs/parsing.md:101,:178` | 采纳：挂钩表指纹行补分工注 |
| P-23 | 低 | 理解面 `None`→`UnderstandingParseError` 分工「一头认得住」：parsing 侧分工注在册；understanding 侧未回认输入半面（未写「parsing 不合格（None）在场时抛」） | `specs/parsing.md:66-68,:73`；`specs/understanding.md:56,:79` | 已定稿侧由主窗回提补一句即闭环（登记） |
| P-24 | 低 | 验收行「`finalize` 支：零载荷直通（不读载荷）」在行为约定无对应行为条目（`finalize` 全篇仅见行为 2 动作枚举） | `specs/parsing.md:130,:90` | 采纳：行为 2 补半句「`finalize` 支零载荷直通（不读 payload）」 |

**计数**：**24 条＝L0×1（P-01）／高×1（P-02）／中×8（P-03…P-10）／低×14（P-11…P-24）**。

### 三、16 问逐条回答（四片合并）

1. **十节齐＋标题逐字**：无发现（10/10 逐字符相等；check_specs PASS）。
2. **行为可 assert＋含糊词**：含糊词 0 命中；18 条均带【断言】。两处弱化随批修：行为 17「如实记录（待裁）」半句（A-01，待裁态如实、可接受）＋行为 16 两处待裁（P-03／P-06）。
3. **数字裸值（机械归类）**：461 个数字命中全量归类——配置值仅「2~4」（句内真源锚在场；V2 承载声明缺＝P-06）；无锚配置值 0 条；行为 16 两缺省上限以 `state` 锚引（半键不实＝P-03）。
4. **不做什么承担者＋锚点**：15 行俱带；两行归属待对账（plan/ranking＝P-11；同参触发面＝P-10）。
5. **框架红线闸名**：亲读 toml 逐条真——R2／R3（含 parsing，forbidden 恰七业务相位）／R5b／R6／R7／R8（恰三相位）编号与覆盖面全对；「R3 半覆盖」「零模型面无专属闸」声明属实；枚举漏 `prompts`＝P-21。
6. **不降级与静默禁令**：合法降级路径「无」明写；拒因恒非空＋预算前缀两处信号带断言；红线 A-P7a-37 实读相符。边界句缺＝P-12；映射行口径＝P-18。
7. **验收测试**：28 行全绑 `test_v2_parsing.py`（标识互不重复）；边界集 :146／保留集 :147 在；测试文件归属注在（实测无同名）。机械缺口＝P-24（finalize 行无对应行为）。
8. **与闸挂钩表**：19 数据行；「已真跑」5 行两片亲手复跑属实；「已进 CI」实测 ci.yml :26/:31-34 属实；人审行 4 处全带原因（两处指针形可择机内联）。
9. **与 walk 决策冲突**：唯一张力＝预算拒文内嵌数值（§06-A 收成一处统一声明 vs 迁移照抄）——已登记待裁（P-06）；其余逐条无相悖（§04-B／§07／§09-C／§11＋补注、#12/#13 全对）。
10. **synth/S1 覆盖（H4／H11）**：基本全落，**半件缺落＝引号自修受理编排**（P-08）；`_json_candidates` 退场随差异点①；A2 L677-694 系显式再分配（不做什么元）；越界零。
11. **总纪律残留（程序替模型判语义）**：零——三面全结构判；唯一文本甄别面＝「发现预算」前缀（程序自产机读标记）；行为 14 豁免面白名单过宽＝P-20（非越界）。
12. **与模块卡一致**：职责／依赖／Seam 一致；分叉集中公开接口（P-01／P-04）＋返回形勘正（同批）。
13. **与已定稿规格对账（九份）**：understanding／clarification／tool_matching／answering／state／execution／agent-loop／verification／prompts 逐份实读——矛盾与两说：P-02（tool）／P-03（state 键）／P-05（类体两处）／P-09／P-10；单向声明：P-23。
14. **钉登记**：pin-04／pin-13「不落本块」两向核实成立；挂钩表两行与 04a 原文逐字相符；31 钉全表扫漏仅 pin-06（P-22，登记级）。
15. **真源引用实存（幻影专项）**：代码行号与 R-xx 条目逐一实读**全实存**（subtask.py 六段／R-A1-×／R-L1a/1b-×／R-E1/E2-×／A-P4b/P6b-×／S1/S4）；ref_resolvable 绿；引注精度四处＝P-13。
16. **卡级问题**：见「五、卡级问题清单」。

### 四、闸实跑记录（2026-10-15，A／D 两片亲手实跑）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                     # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：20 份规格的真源引用与边界规则编号均可解析。   # exit 0

$ uv run lint-imports --config tools/importlinter_v2.toml
R2 runtimev2 业务相位只经公共层包根（禁深层子模块） KEPT
R3 runtimev2 parsing/prompts 只许依赖 state KEPT
R5b ADR-0002 红线① 扩展：框架只许在 runtimev2.orchestration（其余 16 块禁引） KEPT
R6 runtimev2 各块只经 tools 接触引擎 KEPT
R7 runtimev2 各块只经 gateway_adapter 调模型 KEPT
R8 runtimev2 零 LLM 面：preconditions/verification/execution 不得引 gateway_adapter KEPT
Contracts: 18 kept, 0 broken.                                # exit 0
```

辅助取证：含糊词 0 命中；节标题逐字符 10/10；`::` 计数 28；配置值扫描「2~4」有锚；`ls tests/domains/ | grep v2_parsing` 无命中；`ls appv2/runtimev2/parsing/` 仅 `__init__.py`（契约空过）；`git diff 58f5de5 -- specs/parsing.md` 空（被评文本＝提交文本逐字）。

### 五、卡级问题清单（只报不改——单写者纪律，登记交主窗）

1. **`## parsing` 卡**（回阶段 2 补录）：①**指纹器材四件缺件（P-01，L0）**；②V2 定案公开成员缺件（`parse_tool_match`／`ClarifyEmission`／`Subtask` 等，连引用都无）；③`parse_question_group` 返回形勘正（V2＝`ClarifyEmission | str`）（P-04）；④建议补「族名单以 parsing 规格接口定义为准（闭世界）」注记。补录行文建议以 `specs/parsing.md` 接口定义区为逐字来源（窗 A 机械执行即可）。
2. **卡面实读澄清（无需改卡）**：`## understanding` 卡与 `## tool_matching` 卡均未声称持有载荷类（前者只列 `interpret` 签名；后者注释仅引用 `SubtaskMatch`）——载荷类「物理定义点＝parsing」的承载问题在 parsing 卡补录。
3. **已定稿规格侧登记（交主窗回提）**：`specs/clarification.md` `Subtask` 类体（chain 必填形）与 `specs/tool_matching.md` `SubtaskMatch` 类体（`caliber_key: str|None`／`plan: QueryPlan|None`）对行为 11 的差异（P-05）；`specs/state.md` 键集缺 `max_subtasks`（P-03）；`specs/understanding.md` 回认输入半面（P-23）；`specs/agent-loop.md` 行为 3 表述（P-10）。

### 六、未验证/未证实清单

1. `tests/domains/test_v2_parsing.py` 不存在、`appv2/runtimev2/parsing/` 仅占位 `__init__.py`——28 行验收只核标识形态；边界闸为**契约空过**，实现层合规待阶段 5。
2. 预算拒文插槽化与 `ask` 边界「2~4」的最终立足——无裁决文本（待主窗）。
3. 同参重投闸 V2 触发面——无裁决文本（两说不一在案）。
4. 载荷类物理定义点的最终对账形态——**无直接真源文本**，为卡面签名＋R3 组合推论（P-05 登记加固后仍待阶段 7 对账）。
5. B 片实读时 `git status` 干净（其他窗口改动已提交）——若后续再有改动，`specs/clarification.md`／`specs/tool_matching.md` 两条消费方证据需复核。
6. 三片未验证细节：pin-13 `echo_flag` 判据原文（P4b A-P4b-61）未实读（只核两侧登记）；D-L1b-12 recon 误述一处（规格未承接，属正确——不影响判定）。

---

## 七、逐条处置表（2026-10-15，窗 B 逐条处置——L0×1 登记交主窗派卡、高×1 采纳、中×8／低×14 全处置）

> 处置原则：规格文本改动逐条落笔（落法＝可逐字比对）；**卡级问题（P-01）只登记不代办**（`specs/modules.md` 单写者＝窗 A——L0 清零依赖卡面补录，主窗派改）；已定稿规格侧问题（P-05 两处类体／P-03 state 键／P-23 回认／P-10 表述）只登记交主窗；「待主窗过目」件 1（P-07 新拒文字面）。

| 编号 | 处置 | 依据／落法 |
|---|---|---|
| **P-01**（L0，卡级） | **登记（不改卡）＋规格侧配合项在 P-04／接口族名单** | 回阶段 2 补卡：指纹器材四件＋V2 定案公开成员（`parse_tool_match`／`ClarifyEmission`／`Subtask`）＋返回形勘正；补录行文以 `specs/parsing.md` 接口定义区为逐字来源。风险 7① 改述为 L0 登记项；**L0 清零（卡补录）后本规格方可定稿**——卡补录由主窗派窗 A 执行 |
| **P-02**（高） | **采纳** | 行为 3 删 `tool` 越界分支（`tool` 键＝未知键静默丢弃）；行为 11 字段表去 `tool`、投影改「恒三键＋`chain` 真值才出」；验收 :127 缩面改名（`question_group_chain_closed_world`）；差异点表补第⑥条「`Subtask.tool` 退场（裁决 #10）」 |
| **P-03**（中） | **采纳** | 行为 3 与行为 16 对 `max_subtasks` 改述「数值真源＝`walk/09` §七 Q-C＋`eng/00` F-14 统一预算表口径；`state` 承载键未落定（风险 7⑤）」；`max_discovers` 半边保留；触及模块行同步；验收 :125 改述；风险 7⑤ 改述（并入 walk/09 §七 Q-C 与 F-14） |
| **P-04**（中） | **采纳** | 接口定义补「V2 定案签名」块（`parse_question_group(text, *, max_discovers, discover_budget_left=None, max_subtasks) -> ClarifyEmission | str`；`parse_tool_match(content, group) -> tuple[SubtaskMatch, ...] | str`——施工以此为准）；卡面两函数注改「初拟形（阶段 2），施工以 V2 签名为准」；卡级登记随 P-01 |
| **P-05**（中） | **采纳＋登记** | 风险 3 改述为两处类体差异清单（clarification `Subtask` chain 必填形；tool_matching `SubtaskMatch` `caliber_key`／`plan` 形）＋「消费面形状以本规格行为 11 为准」；行为 12 扩面为**载荷类形状单点**（五类逐类）；已定稿两处类体回改＝登记交主窗（风险 7③） |
| **P-06**（中） | **采纳（保守解）** | 两解择一取「保留 V1 字面」（A-P6b-05／24／34 零改动为唯一有授权解）：行为 16 扫描断言补豁免面「迁移照抄的拒文与行为 5 边界字面」；行为 7 断言补例外指针（风险 7② 待裁项，裁定后随批同步）；行为 5「2~4」补真源锚；风险 7② 扩面（预算数值＋`ask` 边界） |
| **P-07**（中） | **采纳（待主窗过目）** | 行为 4 该分支拒文改述「＝R-A1-31 同族文本逐字（现形 `appv2/runtime/graph.py` L617）」；差异点② 同步标注「待主窗过目」 |
| **P-08**（中） | **采纳** | 接口②补第四件「引号自修受理编排（组合协议单点——A-P4b-39；形随 V1 `graph.py` L392-408 迁移）」；行为 10 补编排归属与「理解面不受理自修（V1 事实面零调用点）」；行为 18 与验收 :141 口径同步；消费方对账＝登记（`specs/clarification.md`／`tool_matching.md` 引号自修面） |
| **P-09**（中） | **登记（不改已定稿侧）** | 转换点三选一定案＝交主窗（风险 5 保留在案；风险 7④ 改述为「定案动作」）；本规格侧按裁定落笔 |
| **P-10**（中） | **登记（不改已定稿侧）** | 触发/拦截/回喂落点裁定＝交主窗；风险 4 补注「`specs/execution.md` 行为 13 系空手探查闸＝另一件闸，勿混」；风险 7 新增⑧（含 agent-loop 表述回提） |
| **P-11**（低） | **采纳** | 行为 6 括注改锚 D-L1b-03（自陈「段外未证」）＋「落层归属待对账」；「不做什么」plan 行改述为两说待对账（风险 7⑨） |
| **P-12**（低） | **采纳** | 行为 2 括注改「V1 事实面 D-L1a-14，V2 不改」；不降级节补边界句（「字段」＝schema 内键） |
| **P-13**（低） | **采纳** | 行为 7 条目区间补前置族 R-L1a-06…08、载体列表补 L82-L110、断言锚 R-L1a-28 改「提取失败 fallback 同场抽查」；行为 10／接口②「A-P4b-37/38」改「A-P4b-38（③层）；②层＝A-P4b-37 归合同文本面」 |
| **P-14**（低） | **采纳** | 行为 3 `chain` 补「归一后」；行为 6 `caliber_key` 改「经 `str().strip()` 归一后零值域校验装载」 |
| **P-15**（低） | **采纳** | 行为 5 补「`options` 非 list（缺失／None／标量）→ 归一为空列表（随后按个数拒）」 |
| **P-16**（低） | **采纳** | 接口②「三解析入口共用」改「两发射面共用（V1 三入口含已退场 `parse_decision`——差异点⑤）」；行为 18 同口径 |
| **P-17**（低） | **采纳** | 差异点表补第⑦条（指纹四件私有→公开＋`is_same_param_replay` 形参拆解） |
| **P-18**（低） | **采纳** | 行为 17 补 D-A1-09 病灶锚；不降级节映射行拆两半（重复 id／JSON 重复键） |
| **P-19**（低） | **采纳** | 行为 4 断言「四型拒」改「五型拒（非空数组／单次上限／预算／支缺 `tool`／`args` 非对象）」 |
| **P-20**（低） | **采纳** | 行为 14 豁免面收窄为本块实际形态（闭世界成员判定／字符串归一／字符扫描；白名单按实现出现面核定） |
| **P-21**（低） | **采纳** | 红线段 R3 半覆盖枚举补 `prompts`（八块面） |
| **P-22**（低） | **采纳** | 挂钩表指纹行补 pin-06 分工注（行为面挂 execution 空手闸；本块只供器材） |
| **P-23**（低） | **登记（不改已定稿侧）** | 主窗回提：`specs/understanding.md` 补「parsing 不合格（None）→ 本块抛」输入半面；风险 7 新增⑩ |
| **P-24**（低） | **采纳** | 行为 2 补「`finalize` 支零载荷直通（不读 payload）」 |

**净结果**：24 条——**规格侧改动 18 条**（P-02/03/04/05/06/07/08/11/12/13/14/15/16/17/18/19/20/21/22/24 中含登记联动的取整列）；**纯登记 4 条**（P-01 卡级 L0／P-09／P-10／P-23——全部交主窗）；「待主窗过目」1 件（P-07 新拒文字面）。**L0 状态：未清零**（依赖卡面补录，主窗派窗 A）——L0 清零前本规格不定稿。

## 八、复审轮前修复执行记录（2026-10-15，窗 B 直接落笔——处置表「落法」列即逐字替换依据）

- **已改 `specs/parsing.md`**：来源行（不变）｜接口定义（V2 签名块新增；②共用件「两发射面」＋受理编排第四件；③④锚补）｜不做什么（plan 行改述）｜触及模块（state 行限额半边改述）｜行为 2（finalize 直通＋括注改指）｜行为 3（tool 退场／chain 归一／max_subtasks 改述）｜行为 4（五型拒＋args 拒文待过目）｜行为 5（非 list 归一＋2~4 锚）｜行为 6（caliber_key 归一＋深形归属对账）｜行为 7（载体与条目补全＋例外指针）｜行为 8（照抄声明）｜行为 10（编排归属＋37/38 更正）｜行为 11（tool 退场投影）｜行为 12（五类形状单点扩面）｜行为 14（豁免面收窄）｜行为 16（改述＋豁免面）｜行为 17（D-A1-09 锚）｜行为 18（两发射面口径）｜差异点表（②改述＋⑥⑦新增）｜不降级节（边界句＋映射行拆分）｜验收 :125/:127/:141/:142 改述与改名｜风险 1/3/4/5/6 改述｜风险 7 扩为①…⑩｜挂钩表 :178 分工注。
- **未改**：`specs/modules.md`（卡级 P-01／P-04 登记交主窗派窗 A）｜`specs/clarification.md`／`specs/tool_matching.md`／`specs/state.md`／`specs/understanding.md`／`specs/agent-loop.md`（已定稿侧登记件）｜任何主窗文件。
- 行为约定 18 条、验收行 28 行计数不变（改述与改名非增删）；口径核对：P-02 改名后 `::question_group_chain_closed_world` 与验收他行不重名（实跑 `uniq -d` 复核）。

---

## 九、复审结论（独立子代理，分片 R-A／R-B／R-C 三片）

- 日期：2026-10-15 ｜ 复审对象：`specs/parsing.md` 修订稿（工作区，diff 基线 58f5de5）｜ 方法：三片各自独立上下文实读——R-A 闭合核验 P-01…P-12／R-B 闭合核验 P-13…P-24／R-C 16 问全量复跑＋三闸亲跑＋修订引入面扫查。

### 九之一、闭合核验（P-01…P-24）

**R-A（P-01…P-12）：12/12 闭合。** 要点实证：P-01 闭合（规格侧族名单＋风险 7① L0 登记如实；`specs/modules.md` `## parsing` 卡实读仍两函数旧返回形、零指纹承载——**L0 仍开放、规格无过度声明**；V2 签名块在位 `:46-51`）；P-02 闭合（tool 退场三处落点齐＋旧名零残留；发现支 `tool`／SubtaskMatch.tool／链-工具一致性**未被误删**）；P-03／P-04／P-05／P-06／P-07／P-08 均按处置落法逐字落地（R-A 附残留三小项，见九之三并入 SPZ）；P-09／P-10 登记如实；P-11／P-12 闭合。
**R-B（P-13…P-24）：12/12 闭合**（无未闭合项）。要点：P-13 锚全补（R-L1a-06…08／L82-L110／R-L1a-32 主锚／A-P4b-38）；P-14／P-15／P-16／P-17／P-18／P-19／P-20／P-21／P-22／P-23／P-24 逐条与处置落法逐字对上（各带 file:line 证据）。
**净结果：24/24 闭合**（实改 18＋登记 4＋待过目 1 在案）；无未闭合项。

### 九之二、16 问复跑（R-C，对修订稿）

十节齐（10/10 逐字）✓；含糊词 0 命中；18 条均带【断言】；数字裸值新扫查点全过（walk/09 §七 Q-C、F-14、「2~4」四处带锚、豁免面声明一致）；不做什么 plan 行改述后仍具「由谁承担」形 ✓；红线闸名亲读 toml 逐行相符（R3 枚举 8 块齐）✓；不降级节边界句与映射行拆分后自洽 ✓；28 行验收改名后无重复 ✓；#10 tool 落点后 walk 冲突重扫无新冲突 ✓；S1 H4/H11＋编排件归位覆盖闭合 ✓；卡一致（L0 未清零属实、无过度声明）✓；钉 pin-04/13/06 两向核过 ✓；真源引用新引逐一实读实存（**唯 L617 实为 L616＝SPZ-03**）；无新卡级问题。

### 九之三、新增发现清单（SPZ-01 起——修订引入面）

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| SPZ-01 | **中** | **V2 定案签名块（无缺省值）与行为 16「缺省／默认参数取值」口径相抵**：签名 `max_discovers: int`／`max_subtasks: int` 必填（注入制），行为 16 却写「缺省…取自 `state`」并断言「默认参数取值＝`state` 常量」——签名无默认值时该断言不可满足；验收 :152 同病（对照 V1 带缺省 `=2`／`=MAX_SUBTASKS_CONTRACT`） | `specs/parsing.md:48-50,:84,:87,:114,:152`；`appv2/runtime/subtask.py:226-232` | 择一收口（建议按签名块方向＝注入制）：行为 16 改「由调用方注入、签名无缺省；取值来源＝`state` 限额键」；断言行改「签名无裸默认值＋注入面断言」；验收 :152 同步；差异点③改述注入制 |
| SPZ-02 | 低 | 挂钩表 :190「数字单点（默认上限只引 `state` 单点）」未随 P-03 收窄同步 | `specs/parsing.md:190` vs `:114／:152` | 改述（`max_discovers` 侧引 state；`max_subtasks` 承载待落定） |
| SPZ-03 | 低 | **引注差一（两处）**：差异点②与行为 4 写「现形 graph.py L617」，实读该拒文在 **L616** | `specs/parsing.md:87,:102`；`appv2/runtime/graph.py:616`（实读，自 f58ada9 未动） | 两处改 L616 |
| SPZ-04 | 低 | 签名权威句对撞：`:43`「施工以『V2 定案签名』为准」vs `:85`「卡面两函数签名以卡为准」（draft 旧句未同步） | `specs/parsing.md:43-44` vs `:85` | `:85` 改「参数名以卡为准；返回形与限额参数以『V2 定案签名』为准」 |
| SPZ-05 | 低 | 签名块「逐字迁移」措辞与实文不符（首参 `content`→`text`、缺省去除两处改动未入差异点表） | `specs/parsing.md:46-47,:87`；`subtask.py:226-232` | 注文改「迁移＋两处显式改动」；差异点③并述（随 SPZ-01） |
| SPZ-06 | 低 | 行为 12 扩五类遗留两处：①验收 :148 仍两类型口径；②行为 12「三份消费方规格…差异」实为两份（understanding 已声明为准） | `specs/parsing.md:110` vs `:148`；`:167` | ①:148 扩五类；②改「两份（clarification／tool_matching）」 |
| SPZ-07 | 低 | 行为 16 键面锚不齐：`discover_budget_left` 系全 run 剩余预算面，state 行为 10 有「轮内发现」与「全 run 发现」两键——两参引同一键 | `specs/parsing.md:114`；`subtask.py:235`；`recon/E1:87`；`specs/state.md:116` | 拆引用（`max_discovers`→轮内发现；`discover_budget_left`→全 run 发现） |
| SPZ-08 | 低 | 来源行未列 `appv2/runtime/graph.py`（修订新增其直引两处） | `specs/parsing.md:4,:66,:87,:102` | 来源行补列 |

**计数：8 条＝中×1（SPZ-01）＋低×7；无 L0、无高。** 另 R-A 附残留三项：L617→L616（并入 SPZ-03）｜行为 7 golden 未显式排除 `args` 新分支（并入 SPZ 修复）｜P-04 注文措辞（并入 SPZ-05）。

### 九之四、闸实跑记录（R-C 亲跑）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                     # exit 0
$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：20 份规格的真源引用与边界规则编号均可解析。   # exit 0
$ uv run lint-imports --config tools/importlinter_v2.toml
Contracts: 18 kept, 0 broken.（R2/R3/R5b/R6/R7/R8 全 KEPT）   # exit 0
```

### 九之五、复审判定

**规格侧：可定稿**（无 L0、无高；三闸全绿；24/24 闭合）。
- **定稿提交前必修**：SPZ-01（中——断言不可满足，按注入制方向收口）。
- **同批修**：SPZ-02…08（七低件，随批微修）。
- **L0 卡级状态**：P-01 未清零——依赖主窗派窗 A 卡面补录，**为预期状态**（规格侧登记如实、无过度声明）；**不阻判规格文本，但按工序纪律规格定稿须待卡补录后**。

## 十、SPZ 逐条处置与修复执行记录（2026-10-15，窗 B 直接落笔）

| 编号 | 处置 | 落法 |
|---|---|---|
| **SPZ-01**（中，定稿前必修） | **采纳（按签名块方向＝注入制）** | 行为 16 重写（「注入制」：三参由调用方注入、签名无缺省；`max_discovers`→「轮内发现」键／`discover_budget_left`→「全 run 发现」键；断言改「签名无裸默认值＋注入面逐参可指」）；验收 :152 同步；差异点③改述注入制（V1 缺省裸字面 D-L1a-12 就地消解） |
| SPZ-02（低） | 采纳 | 挂钩表 :190 改述 |
| SPZ-03（低） | 采纳 | 差异点②／行为 4 两处 L617→L616 |
| SPZ-04（低） | 采纳 | :85 改「参数名以卡为准；返回形与限额参数以『V2 定案签名』为准」 |
| SPZ-05（低） | 采纳 | 接口签名块注「迁移＋两处显式改动（首参按卡改名／缺省去除改注入制）」；差异点③并述 |
| SPZ-06（低） | 采纳 | 验收 :148 扩五类口径；行为 12「三份→两份」 |
| SPZ-07（低） | 采纳 | 并入 SPZ-01 重写（键面拆分） |
| SPZ-08（低） | 采纳 | 来源行补 `appv2/runtime/graph.py` |
| R-A 残留 2 | 采纳（随批） | 行为 7 golden 断言补除外项「`args` 非对象新分支〔无 V1 快照，字面待主窗过目〕」 |
| R-C 旁注（16 问 #11） | 采纳（随批） | 接口⑤补「不使用提取件」显式声明 |

**净结果**：SPZ-01…08 全部采纳＋R-A 残留 2／R-C 旁注 随批（10 项直接落笔）。**规格侧工序完结：24/24 闭合＋SPZ 全清＋三闸绿＝规格文本层可定稿；整块定稿待 P-01（L0）卡面补录**（主窗派窗 A）。

### 修复后复跑（窗 B）

```
$ uv run python tools/check_specs.py && uv run python tools/ref_resolvable.py check
spec gate: PASS（0 警告）／真源引用可解析闸绿：20 份规格      # exit 0
$ uv run lint-imports --config tools/importlinter_v2.toml | tail -1
Contracts: 18 kept, 0 broken.                                # exit 0
```

---

## 十一、L0 补录进度追记（2026-10-15 夜，窗 B）

- **已补（`821968f`，主窗「流水31」批）**：`specs/modules.md` `## parsing` 卡公开接口区已补**指纹器材四件**（`payload_fingerprint`／`discover_fingerprint`／`emission_fingerprints`／`is_same_param_replay`；卡注标明「L0 补录 2026-10-15——签名照 `specs/parsing.md` 接口定义节④逐字」）——P-01 的核心缺件（S-2 类）已消除。
- **待补（按 P-01／P-04 登记的清算包余项）**：①`parse_tool_match` 成员（V2 定案公开成员）；②`parse_question_group` 返回形勘正（`-> ClarifyEmission | str`）或补「初拟形（阶段 2），施工以 V2 定案签名为准」注；③族名单权威注「公开面以 parsing 规格接口定义为准（族名单闭世界）」。
- **口径**：三项补齐即视为 P-01（L0）清零完成，`specs/parsing.md` 翻「已定稿」（一行提交，窗 B 执行）；若主窗裁「指纹四件＝L0 已清、余三项随阶段 7 接口契约对账收口」亦可——**请主窗定夺**后窗 B 执行状态翻转。

## 起草方留档：三闸实跑记录（2026-10-15）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                     # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：20 份规格的真源引用与边界规则编号均可解析。   # exit 0

$ uv run lint-imports --config tools/importlinter_v2.toml
R2 runtimev2 业务相位只经公共层包根（禁深层子模块） KEPT
R3 runtimev2 parsing/prompts 只许依赖 state KEPT
R5b ADR-0002 红线① 扩展：框架只许在 runtimev2.orchestration（其余 16 块禁引） KEPT
R6 runtimev2 各块只经 tools 接触引擎 KEPT
R7 runtimev2 各块只经 gateway_adapter 调模型 KEPT
R8 runtimev2 零 LLM 面：preconditions/verification/execution 不得引 gateway_adapter KEPT
Contracts: 18 kept, 0 broken.                                # exit 0
```

辅助取证：`ls tests/domains/` 实测无 `test_v2_parsing.py`（新建归属无冲突）；`ls appv2/runtimev2/parsing/` 仅 `__init__.py`（占位空包——边界闸为契约空过）。

### 未验证清单（交评审代理）

1. `tests/domains/test_v2_parsing.py` 不存在、`appv2/runtimev2/parsing/` 仅占位 `__init__.py`——验收行只能核标识形态，实现层合规待阶段 5。
2. 「V2 定案差异点」五点中的②③④（裸抛收口／常量迁移／内嵌数值待裁）**无既有裁决文本**——起草方按迁移纪律＋总纪律组合推出，属**待主窗过目件**（评审可判其对错，但处置归 L0／主窗）。
3. 行为 12 的「物理定义点＝本块」为组合推论（卡面签名＋R3），**无直接真源文本**——见重点核对项 1③。
