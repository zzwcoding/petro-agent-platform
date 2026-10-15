# RT-W3-03a · gate——V2 安全阀（-A：骨架＋三族判定与命中收口核心簇＋全部 pin 行）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/gate.md`（状态「已定稿」——前置满足）
Touches modules: `gate`（本票只建 gate 本体与三族判定；规格「触及的模块」表另声明 `state` 关联侧——卡面依赖行承接，本块判定为纯文本进出、**零 state 字段与常量消费点**）
块性（spec :6 原注照抄）：本块＝**结构早退块**（真源 `docs/runtime-refactor/walk/判断归责表.md`——「词面安全阀｜明显中招/越界的快路径早退（不是判据）｜程序（仅辅助快路径）｜结构（早退）」）——三族判定＝闭世界词表子串／共现（结构早退，非判据）；**零语义判断**（豁免／意图／「提及 vs 执行」一律不落本块）；「只读」（INV-2）硬保证在**执行层**（真源 `docs/runtime-refactor/walk/裁决表.md` §07）。
波次: W3 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W3 行三列原文：块列「`context` `bookkeeping` `gate`」；理由列「组合件，依赖 W2 的 gateway_adapter；bookkeeping 单写口是相位开发的共同依赖」；出口判据列「每模型调用有 Manifest；写口无旁路（AST＋import 双证）；两道闸机械分派」
复审强度: 50% 抽查（eng/03 §五 W3 行 A 列含 `gate`——该表降级保留的规则原文「A 列抽 50%」；双队制已废止，A/B 分配只余复审强度语义，波序与块归属不变）
前置: ① 规格定稿（`specs/gate.md` 已定稿——已满足）；② 波次前置：**W2 全收波**（eng/03 §一依赖图原文「gate → state」＋ §二 W3 行理由列「组合件，依赖 W2 的 gateway_adapter」；W2 五票＝persistence／transport／gateway_adapter／prompts／parsing，其中 `parsing` 票＝`RT-W2-05a/b-parsing.md`——本批新票）；③ 票内前置：无（-A 为本块首票；占位骨架 `appv2/runtimev2/gate/__init__.py` 已随阶段 2 落锤）
阻塞: W2 全收波（`RT-W2-01a/b-persistence.md`／`RT-W2-02a/b-transport.md`／`RT-W2-03a/b-gateway_adapter.md`／`RT-W2-04a/b/c-prompts.md`／`RT-W2-05a/b-parsing.md`，按子票计；票号以主窗 manifest 为准）｜被阻塞: `RT-W3-03b-gate.md`（同包顺序施工——-03b 前置＝-03a 收票；`screen` 签名、`Refusal` 形状与常量族以 -03a 为唯一真源）；W4 入口消费相位（`understanding`——早退与收口执行面）

## 任务

按 `specs/gate.md` 新建 `appv2/runtimev2/gate/`：把入口问句里**明显中招／越界**的三类情形（注入／外发／写意图）做成一次**零模型零执行的词面早退**——命中即不放行、以固定话术拒答收口；本块是**辅助快路径、不承载红线**——「只读」（INV-2）的硬保证在执行层，漏判由执行层兜（规格「目标」节原文）。

**本票＝gate 的 -A 票（骨架＋三族判定与命中收口核心簇＋本块全部 pin 行）**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **20 行**，超 15 行上限 → 切 **-A／-B** 两票。本票收 **10 行**＝规格表第 1–10 行（三族先命先断／注入族／外发族／写意图族／拒答话术三条／步标题三形／`Refusal` 形状闭世界／命中早退零模型零执行／收口信号形状／A 类零误伤——**三族判定与命中收口全簇**）＋ **1 条 pin 行全量**（pin-18，逐字转抄见「测试网钉」节）；剩余 **10 行**＝规格表第 11–20 行（零语义判断／纯函数确定性／命中路径零台账／迁移字面逐字／早退位次与零漂移／词表闭世界单点／import 白名单／废弃词闸符号零命中／【边界集】／【保留集】）归 `RT-W3-03b-gate.md`。两票同包**顺序施工**（同包不并行）：本票出骨架、`screen` 签名、`Refusal` 形状与常量族，-03b 只填元面与边界簇、不另立第二套形状（改形状＝回本票或回设计仓）。
**骨架/接口归本票**：`screen(text) -> Refusal | None` 签名＋`Refusal` 形状（`{family, hit, content}` 三字段）＋常量族（八件＋`STEP_TITLES` 映射——**族名单闭世界**）随本票落位（规格 :39–:96 接口定义）；卡面 `apply_term_verdict(verdict) -> Disposition` 一行＝**移出件、不施工**（Owner 裁决 #12；卡级登记件，风险 7①，本票不改卡）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/gate.md` 全文（十节版式——三族判据、三条话术逐字稿、`STEP_TITLES` 三形、收口三件套、A 类零误伤与收窄口径、V2 定案差异点表五行都在规格行内）；`specs/modules.md` `## gate` 卡（`screen` 签名逐字；`apply_term_verdict` 一行＝移出件；卡面族成员补录与权威注）；`appv2/runtime/graph.py`（**迁移源字面**：L1360-L1387 词表与话术常量、L1390-L1468 `_n0_intent_word_gate` 及族内三 matcher、L1452／L1458／L1466 步标题三形）；`tickets/v2/V2-66-注入拦截闸.md`（**注入族逐字稿载体**）；`tickets/v2/V2-67-外发写意图闸.md`（**外发／写意图族逐字稿载体**）；`tests/domains/test_v2_n0_word_gates.py`（**A 类问句语料**——`::test_n0_no_false_positive_corpus` 实存 20 条，行 10 的语料来源）。eng/04 §三 B4 归块行与 eng/04a 的 pin-18 原文已在本票「织网义务」「测试网钉」两节逐字转抄，施工期不必另开。

**小票制自检（流水 48）**：票面对象 10 行 ≤ 15 ✓；先读 6 份 ≤ 6 ✓；聚焦一个行为簇＝「三族判定 → 命中 → 固定话术与收口信号」单链（单一入口 `screen`）✓ → 本票不派生（只切 -B 承接元面与边界簇）。

框架红线: 无点名框架（本块不引入任何框架；纯字符串处理零依赖）——对应闸 R5b 契约（`tools/importlinter_v2.toml` :101，source 含 `appv2.runtimev2.gate`——亲读属实）
边界红线: ① **只许 import `state`（纯判定块）**：不引其余 runtimev2 块、不引旧码 `appv2.runtime.*`（R5——:95）；**诚实声明**：R1–R8 无「gate 依赖白名单」专属闸（R3 的 source 只列 parsing／prompts——:81）→降维＝AST 断言 `::imports_state_only`＋人审；② 不引引擎（`knowledge`／`query`／`retrieval`）——R6（:110，source 含 gate）；③ 不直引 `appv2.infra.llm_client`——R7（:119，source 含 gate）；④ **零模型调用**（连 `gateway_adapter` 都不 import）——无专属闸→AST 断言（`::imports_state_only`／`::screen_pure_deterministic`）；⑤ 消费方向（R2）**半覆盖诚实声明**：R2 的 forbidden 现含九个公共层块深层、**不含 `appv2.runtimev2.gate.*`**（亲读属实，:74）——消费方只经包根＝规格层 doctrine，补闸＝回阶段 2 登记（风险 3），降维＝AST 断言（登记待补）；⑥ **零 IO／零写／零帧／零审计**：命中路径零台账接触（V1「当场再取一次词典层缝并写回」属现状缺陷、重写不复刻），帧面与落账归消费方；⑦ **禁手写替代（判定单点）**：三族词表、三条话术与步标题映射在 runtimev2 面内各恰一处定义，禁相位块另存副本（`::word_families_closed_world_single_source`）；⑧ **禁手写替代（本票面）**：不得定义 `apply_term_verdict`／`Disposition`，不得改 -03a 形状另立第二套

## 票面对象（specs/gate.md「验收测试」表逐行转抄——本票 10 行：规格表第 1–10 行）

〔来源：specs/gate.md「验收测试」表 :151–:170（本票取自 :151–:160），逐行原文；`#` 列＝规格表行序，-03b 票续用同一行序不重编〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | 三族先命先断：序固定（注入→外发→写意图）、第一命中即返；注入＋写意图同句 → `injection` | `tests/domains/test_v2_gate.py::family_order_first_hit_wins` | specs/gate.md:151 |
| 2 | 注入族：五条模式逐字＋casefold 折叠（英文大小写样本）＋模式原形返回值 | `tests/domains/test_v2_gate.py::injection_patterns_verbatim_casefold` | specs/gate.md:152 |
| 3 | 外发族：动词×通道共现命中、槽值＝通道词；两单边不命中 | `tests/domains/test_v2_gate.py::outbound_verb_channel_cooccurrence` | specs/gate.md:153 |
| 4 | 写意图族：动词×对象共现命中、槽值＝对象词、取序对；两单边不命中 | `tests/domains/test_v2_gate.py::write_verb_target_cooccurrence` | specs/gate.md:154 |
| 5 | 拒答话术三条逐字＋槽填充（命中词原文） | `tests/domains/test_v2_gate.py::refusal_texts_verbatim_slots` | specs/gate.md:155 |
| 6 | 步标题三形逐字（迁移照抄） | `tests/domains/test_v2_gate.py::step_titles_verbatim` | specs/gate.md:156 |
| 7 | `Refusal` 形状闭世界（`family` 三值／`hit`／`content` 非空）＋越界判失败 | `tests/domains/test_v2_gate.py::refusal_shape_closed_world` | specs/gate.md:157 |
| 8 | 命中＝早退：零模型零执行＋notice refused 恰一条＋`draft_kind="direct"`＋answer 话术逐字（**pin-18 承接**） | `tests/domains/test_v2_gate.py::hit_early_exit_zero_model` | specs/gate.md:158 |
| 9 | 收口信号形状：notice 恰三键＋步 payload（`gate` 分型三值／`term` 对齐 `hit`／`phase`）＋步 `status="refused"` | `tests/domains/test_v2_gate.py::refusal_signal_shape` | specs/gate.md:159 |
| 10 | A 类问句零误伤（语料逐条 `None`——**pin-18 承接**） | `tests/domains/test_v2_gate.py::class_a_no_false_positive` | specs/gate.md:160 |

> 测试文件归属（spec :172 节尾原注照抄）：本块验收测试绑**新建** `tests/domains/test_v2_gate.py`（`gate` 是阶段 2 新划的入口闸块 `appv2/runtimev2/gate/`；`ls tests/domains/` 实测无同名文件，无冲突）；旧承载位测试 `tests/domains/test_v2_n0_word_gates.py`（直引旧码私名 `_n0_injection_hit` 等）随阶段 5 迁移重写收口（本批不改）；fixture＝**固定词表 fixture**（卡面 Adapter）＋A 类问句语料。全部测试标识＝**待织网（阶段 5）**。
> 行序缺口说明（票注）：本票行序跳过 11–20——`#` 列两票共用规格表行序，便于 manifest 逐行对账。
> 本块不涉面（防一头两认）：行 11–20（零语义判断／纯函数确定性／命中路径零台账／迁移字面逐字／早退位次与零漂移／词表闭世界单点／import 白名单／废弃词闸符号零命中／【边界集】／【保留集】）归 `RT-W3-03b-gate.md`；本票已落地的 `screen` 签名、`Refusal` 形状与常量族**不改**（改形状＝回本票或回设计仓）。
> 规格侧缺口登记（票注，呈主窗对账；按规格原文处理、**不增设验收行**——增设＝改规格，回设计仓）：
> - **① 收口行为面承接缺口**（规格风险 2 原文逐字：「`specs/understanding.md` 认「入口安全阀→`gate`」「本 spec 只消费其结论」，但**无收口行为／验收行**（早退位次／零模型零执行／收口三件套的执行面）——**回提登记**（understanding 补承接，或主窗裁定落 `orchestration`；本规格持行为与断言、执行者以落地为准）」）。本票行 8／9 的**执行面**（谁在入口跑早退、谁落收口三件套）以落地为准——施工期按规格行为与断言实现本块，**承接位未落定时停报 L0、不自行发明承接方**。
> - **② R2 覆盖面缺 gate 深层子模块**（规格风险 3 原文逐字：「`tools/importlinter_v2.toml` R2 forbidden 实建九块、不含 `appv2.runtimev2.gate.*`」——补闸＝回阶段 2 登记）。本块自身依赖白名单由 `::imports_state_only` 守；**消费方 import 形 AST 扫描＝登记待补**——本票不代补该闸。
> - **③ 占位 docstring 残留＝同批改述项**（规格风险 7⑦原文：「`appv2/runtimev2/gate/__init__.py` 占位 docstring 残留（旧双件定界——阶段 5 施工同批改述，登记）」）。现占位 docstring 首行为「入口闸族：安全阀（辅助快路径，命中即不放行）＋废弃词闸（判据交模型，程序只按结论机械分派）」——**废弃词闸半句已随裁决 #12 移出**，本票施工时同批改述（只改 docstring 措辞，不动规格）。

## 测试网钉（specs/gate.md「与闸的挂钩表」pin 行逐行转抄——全块 1 行，在本票）

〔来源：specs/gate.md「与闸的挂钩表」:199，逐行原文；列名同规格「本规格的硬要求｜挂钩｜现状」〕

| 本规格的硬要求（原文） | 挂钩（原文） | 现状（原文） |
|---|---|---|
| 命中＝早退、零模型零执行、notice `type=refused`、A 类零误伤（**pin-18 承接**，P0） | 钉 **`pin-18`**——本块落点＝行为 1–9＋验收 `::family_order_first_hit_wins`／`::hit_early_exit_zero_model`／`::refusal_signal_shape`／`::class_a_no_false_positive`；**分工**：notice 类型闭世界面＝`specs/transport.md`（`NOTICE_TYPES` 含 `refused`）、收口落账面＝`specs/bookkeeping.md` | 待织网（阶段 5） |

- 钉落点对读一行（**非 pin 行**，逐字转抄以防一头两认；列名同上）：

| 本规格的硬要求（原文） | 挂钩（原文） | 现状（原文） |
|---|---|---|
| `pin-31`（废弃词闸新行为）经逐条核实**不落本块**（防一头两认） | 钉落点对读：判断＝`specs/tool_matching.md`（其挂钩表 pin-31 行）；分派＝`specs/preconditions.md` 判定序第 1 位（其挂钩表 pin-31 行）；出数只认现行口径＝`specs/tool_matching.md` 行为 7——**两头认核成立**；本块反向保证＝行为 15＋`::no_writeback_of_term_gate` | 已核实（本批起草时逐条对读） |

- 分工注（票注，防两头认）：pin-18 的**四条命定用例全在本票**（行 1／8／9／10）——与规格挂钩表「本块落点＝行为 1–9＋四个验收标识」逐字一致；**notice 类型闭世界面**在 `specs/transport.md` `NOTICE_TYPES`（含 `refused`）、**收口落账面**在 `specs/bookkeeping.md`（行为 7 链只追加／行为 14 直答收口三键／行为 11 notice）——两处均为他块真源，本票只承接其**信号形状与判定**（本块零 emit、零写）。`pin-31`（废弃词闸新行为，`docs/runtime-refactor/eng/04a-应钉行为清单.md` :40 全表第 31 行）判在模型／派在 `preconditions`／旧名归一 `tool_matching` 三面俱不在本块（规格风险 7⑤）。
- `pin-21`（faq 五站链）零落点＝已裁定（`eng/04a` pin-21 行注记「主窗 2026-10-15 裁：零落点＝正确状态非缺陷」）——本块知悉不挂（规格风险 7⑥）。
- pin 行分布（防两处漂移，逐字稿纪律）：本块 pin 行**全在本票**逐字转抄；`RT-W3-03b-gate.md` 零 pin 行、只写归属指针。

## 施工要点（specs/gate.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/gate.md:116 | 行为 1 三族闭世界＋先命先断（序＝注入→外发→写意图） | `screen` 按固定序判定、**第一命中即返**；三族皆未命中 → `None`（闸静默）；注入＋写意图同句 → `family="injection"` |
| specs/gate.md:117 | 行为 2 注入族判据（逐字迁移） | 五条模式**大小写折叠（casefold）子串**匹配；命中 → 返回**列表序首个命中的模式原形**（槽值） |
| specs/gate.md:118 | 行为 3 外发族判据（逐字迁移） | 动词（七条）×通道（八条）**同问句共现**（子串；**不折叠**）才命中——单一词面不拦；命中 → 返回**列表序首个命中的通道词**（槽值） |
| specs/gate.md:119 | 行为 4 写意图族判据（逐字迁移） | 动词（十条）×对象（六条）共现才命中（**对象按列表序取首个命中者**＝可观测面）；命中 → 返回**对象词**（槽值；动词分量不携——差异点②）；两单边 → `None` |
| specs/gate.md:120 | 行为 5 匹配方式三族面（迁移照抄） | 注入折叠、外发／写意图不折叠（纯子串）——三族不齐＝V1 事实面（统一折叠＝规格变更） |
| specs/gate.md:121 | 行为 6 拒答话术三条逐字＋槽填充 | 注入模板 `{feature}`＝命中模式词原文；外发话术固定（无槽）；写意图模板 `{target}`＝命中对象词原文；三条文本逐字（承载位换、文本不变） |
| specs/gate.md:128 | 行为 8 步标题三形逐字（迁移照抄） | `N0 注入拦截硬终止`／`N0 外发拦截硬终止`／`N0 写意图拦截硬终止`（「N0」为迁移字面——编号体系本身不入 V2，改名＝规格变更） |
| specs/gate.md:132 | 行为 11 `Refusal` 形状与越界行为 | `{family, hit, content}` 三字段；`family` 闭世界三值；`hit`＝槽值非空；`content`＝话术逐字非空；越界构造＝判失败（fail-closed 抛错，不猜、不取默认） |
| specs/gate.md:122 | 行为 7 命中＝早退（零模型零执行）＋收口信号形状 | 命中 → 入口在**任务书装配与模型调用之前**早退；收口三件套＝notice 恰三键 `{type="refused", gates=[], content}`／步记录 `decision` 类·标题＝三形逐字·payload＝`{"phase": "understand", "gate": <分型>, "term": Refusal.hit}`·`status="refused"`／直答收口（`draft`／`draft_kind="direct"`）＋过程档案一条；**本块产判定与话术（零 IO），早退位次与落账由入口消费方经 `bookkeeping` 执行、帧面归 `transport`** |
| specs/gate.md:129 | 行为 9 A 类问句零误伤＋收窄口径 | 零误伤判据＝A 类语料**逐条过三族全 `None`**（以迁移钉测语料为准，实存 20 条）；收窄口径三条＝命中须动词＋通道／对象**共现**、注入为**固定短语**、不靠扩词表覆盖间接／元问表达；**净收窄为零**、D-B2-01 残留样本按已知接受态保留 |

结构锚：specs/gate.md:39–:96 接口定义（**V2 定案签名**——`screen`＋`Refusal`＋常量族八件＋`STEP_TITLES`，族名单闭世界；卡面 `apply_term_verdict` 一行＝移出件不施工）；:98–:103 返回两态闭世界／错误契约（`screen` **不抛业务错**——任意 `str` 入参恒返回两态之一）／入参纪律（纯文本进出、**零 state 字段读**、无数值面）／Adapter 定界；:138 V2 定案差异点表（五点：分型键名 `n1_gate`→`gate`／写意图槽值只携对象词／命中路径零台账 I/O／步 payload 增 `term` 键／步 `status="refused"`）；:105–:112 框架与依赖红线；:140–:145 不降级与静默禁令（**合法降级路径＝无**；命中必留机读信号（**信号形状由本块锁定、发射与落账＝消费方义务**）；本块零截断——话术全文出、槽值＝命中词原文不截断）。剩余行（11–20）的骨架对齐随本票落位、行为断言在 `RT-W3-03b-gate.md`。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三 归本块行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单——表内明写归本块的行〕

> | B4 | N1 禁用词闸族（仅 1 个豁免族被间接测到） | 专属钉（对应 `gate`） | 中 |

- 归块注：B4 是 §三 表内**明写**「对应 `gate`」的行（严重度「中」）——本票落其专属钉。**钉法口径注（票注，呈主窗对账）**：B4 原文的「禁用词闸族」系裁决 #12 **移出前**的族名（`docs/runtime-refactor/walk/裁决表.md` #12：「**`gate` 只留安全阀**（注入／外发／写意图＝代码快路径），废弃词闸从 `gate` 移出」；`eng/04a` :27 pin-18 行同款改写注「按裁决 #12 改写：注入→外发→写意图三族（~~禁用词~~已移出门口）」）——故本块落**三族安全阀**的专属钉（`::family_order_first_hit_wins`／`::hit_early_exit_zero_model`／`::refusal_signal_shape`／`::class_a_no_false_positive`／`::migrated_literals_verbatim`／`::word_families_closed_world_single_source`），即为 pin-18 的 P0 落点面；**废弃词闸新行为的钉面**（pin-31）在 `tool_matching`／`preconditions` 两侧（本块零落点，已核实）。引擎侧遗留的「仅 1 个豁免族被间接测到」＝现状缺陷描述，重写后由上述专属钉替代——原文如实登记、不改写。
- 关联行（落他票，指针）：B1（明写归 `bookkeeping`）落 `RT-W3-01a-bookkeeping.md`；B3（限额上限／触顶收敛）落 `state`／`bookkeeping` 侧票——本票不重复转抄。
- 本票织网义务＝① B4 专属钉（钉法＝「专属钉（对应 `gate`）」，织网工序第 3 步「盲区补钉」，与 W1–W3 施工可并行——eng/04 头注）；②「测试网钉」pin-18 对应用例落网（P0 承重钉——四条命定用例即其落点）；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」10 行逐行实现为 `tests/domains/test_v2_gate.py` 用例并全绿，测试标识与规格列逐字一致（`#` 保留规格表行序 1–10）；
- 「测试网钉」pin-18 行对应用例在场且绿（P0 承重钉——四条命定用例在行 1／8／9／10，与规格挂钩表逐字一致）；「钉落点对读」一行（pin-31 不落本块）核实在案；本票不重复转抄 -03b 的零 pin 行；
- 迁移字面逐字零偏离（逐字稿载体＝`tickets/v2/V2-66-注入拦截闸.md`／`tickets/v2/V2-67-外发写意图闸.md`＋现行代码 `appv2/runtime/graph.py` L1360-L1387／L1390-L1468——照抄不改，差异点表外零偏离，偏离即停）；
- 骨架与族名单落位：`screen` 签名＋`Refusal` 形状＋常量族八件＋`STEP_TITLES` 齐（规格 :39–:96，族名单闭世界），返回两态闭世界与错误契约在场；-03b 不得另立第二套形状；
- 收口分工不越界：本块产判定与话术（零 IO、零 emit、零写）；早退位次与落账归入口消费方（`bookkeeping` 写口）、帧面归 `transport`——notice 类型闭世界面在 `transport`、收口落账面在 `bookkeeping`；
- 边界闸 R5／R5b／R6／R7 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；gate 依赖白名单与 R2 深层子模块两半面无专属闸——按规格诚实声明以 AST 断言＋人审补位（登记待补）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W3-03a 完成，产物 `appv2/runtimev2/gate/`（骨架＋三族判定与命中收口核心簇），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
