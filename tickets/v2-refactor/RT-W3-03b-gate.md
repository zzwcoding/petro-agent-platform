# RT-W3-03b · gate——V2 安全阀（-B：元面与边界簇——零语义判断／纯函数确定性／零台账／迁移字面／单点／import 白名单／边界·保留集）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/gate.md`（状态「已定稿」——前置满足）
Touches modules: `gate`（本票只填 gate 元面与边界簇；`screen` 签名、`Refusal` 形状与常量族以 -03a 落地的为唯一真源；规格「触及的模块」表另声明 `state` 关联侧——卡面依赖行承接，本块零 state 字段与常量消费点）
波次: W3 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W3 行三列原文：块列「`context` `bookkeeping` `gate`」；理由列「组合件，依赖 W2 的 gateway_adapter；bookkeeping 单写口是相位开发的共同依赖」；出口判据列「每模型调用有 Manifest；写口无旁路（AST＋import 双证）；两道闸机械分派」
复审强度: 50% 抽查（eng/03 §五 W3 行 A 列含 `gate`——该表降级保留的规则原文「A 列抽 50%」；双队制已废止，A/B 分配只余复审强度语义，波序与块归属不变）
前置: ① 规格定稿（`specs/gate.md` 已定稿——已满足）；② **`RT-W3-03a-gate.md` 收票**（同包顺序施工、同包不并行——`screen` 签名、`Refusal` 形状与常量族以 -03a 为唯一真源）；③ 波次前置：**W2 全收波**（eng/03 §一依赖图原文「gate → state」＋ §二 W3 行理由列「组合件，依赖 W2 的 gateway_adapter」，经 -03a 传递，已满足）
阻塞: `RT-W3-03a-gate.md`（-03b 前置＝-03a 收票）｜被阻塞: W4 入口消费相位（`understanding`——早退与收口执行面）

## 任务

接 `RT-W3-03a-gate.md` 落地的骨架与三族判定，填 `appv2/runtimev2/gate/` 的**元面与边界簇**：程序侧零语义判断（无豁免／意图／正则判定）、纯函数确定性（两跑相等；零 IO／模型／时钟／随机／emit／写）、命中路径零台账接触、迁移字面逐字（词表／话术／步标题 vs V1 快照）、早退位次与闸静默零漂移、词表闭世界只扩不删＋步标题映射＋runtimev2 面单点、import 白名单（只 `state`）、废弃词闸符号零命中，以及【边界集】／【保留集】两行。

**本票＝gate 的 -B 票**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **20 行**，超 15 行上限 → 切 -A／-B 两票；本票收**剩余 10 行**＝规格表第 11–20 行（零语义判断／纯函数确定性／命中路径零台账／迁移字面逐字／早退位次与零漂移／词表闭世界单点／import 白名单／废弃词闸符号零命中／【边界集】／【保留集】）；前 10 行与**本块 1 条 pin 行**（pin-18）全在 -03a，本票零 pin 行、不重复转抄（同一 pin 行两票重复转抄＝两处真源必漂移）。两票同包**顺序施工**（同包不并行）：本票只填元面与边界行为、**不改 -03a 落地的形状**（`screen` 签名＋`Refusal` 形状＋常量族——改形状＝回 -03a 或回设计仓）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/gate.md` 全文（十节版式——行为 12–15 的元面与零台账红线、行为 10 的「只扩不删」、行为 9 的收窄口径与三口径登记都在规格行内）；`specs/modules.md` `## gate` 卡（`screen` 签名与族成员权威注——形状以 -03a 落地为准）；`specs/understanding.md`（入口相位对接面——「只消费其结论」；早退位次与收口执行面的承接缺口＝风险 2 登记）；`specs/transport.md`（`NOTICE_TYPES` 含 `refused`——notice 分型闭世界面，行 19 边界集的帧面对读）；`specs/bookkeeping.md`（收口落账写口：行为 7 链只追加／行为 11 notice／行为 14 直答收口三键）；`tests/domains/test_v2_n0_word_gates.py`（**A 类问句语料**——`::test_n0_no_false_positive_corpus` 实存 20 条，行 19 边界集与行 14 迁移字面的对读语料）。eng/04 §三 B4 归块行已在 `RT-W3-03a-gate.md`「织网义务」节逐字转抄，本票不重复、只写指针。

**小票制自检（流水 48）**：票面对象 10 行 ≤ 15 ✓；先读 6 份 ≤ 6 ✓；聚焦一个行为簇＝「元面与边界」（AST 与单点断言＋迁移字面比对＋边界集／保留集）✓ → 本票不派生。

框架红线: 无点名框架（本块不引入任何框架；纯字符串处理零依赖）——对应闸 R5b 契约（`tools/importlinter_v2.toml` :101）
边界红线: ① **只许 import `state`（纯判定块）**——R3 的 source 只列 parsing／prompts（:81）、**无「gate 依赖白名单」专属闸**→AST 断言 `::imports_state_only`＋人审；② 不引旧码 `appv2.runtime.*`——R5（:95）；③ 不引引擎——R6（:110）；④ 不直引 `appv2.infra.llm_client`——R7（:119）；⑤ 消费方向（R2）半覆盖诚实声明：R2 forbidden **不含 `appv2.runtimev2.gate.*`**（:74）——降维＝AST 断言（登记待补）＋人审；⑥ **零模型调用**（连 `gateway_adapter` 都不 import）——AST 断言（`::imports_state_only`／`::screen_pure_deterministic`）；⑦ **零 IO／零写／零帧／零审计＋命中路径零台账接触**（AST 零 ledger／DB／文件／emit 符号——差异点③）；⑧ **本块零语义判断**：不做豁免／元问／引用形判定、不判「提及 vs 执行」，词表只作明显命中的结构早退（非判据）；⑨ **废弃词闸不落本块**：本块源码零 `apply_term_verdict`／`Disposition` 符号（`::no_writeback_of_term_gate`）；⑩ **禁手写替代**：不得改 -03a 已定的形状与常量族另立第二套，不得在消费方块私建词表／话术字面副本

## 票面对象（specs/gate.md「验收测试」表逐行转抄——本票 10 行：规格表第 11–20 行）

〔来源：specs/gate.md「验收测试」表 :151–:170（本票取自 :161–:170），逐行原文；`#` 列＝规格表行序（与 -03a 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 11 | 零语义判断（无豁免／意图／正则判定；词表＝结构快路径） | `tests/domains/test_v2_gate.py::no_semantic_judgement_in_gate` | specs/gate.md:161 |
| 12 | 纯函数确定性：两跑相等；零 IO／模型／时钟／随机／emit／写（AST） | `tests/domains/test_v2_gate.py::screen_pure_deterministic` | specs/gate.md:162 |
| 13 | 命中路径零台账接触（AST 零 ledger／DB 符号——差异点③） | `tests/domains/test_v2_gate.py::hit_path_zero_io` | specs/gate.md:163 |
| 14 | 迁移字面逐字（词表／话术／步标题 vs V1 快照；差异点表外零偏离） | `tests/domains/test_v2_gate.py::migrated_literals_verbatim` | specs/gate.md:164 |
| 15 | 早退位次（先于任务书装配与模型调用）＋闸静默零漂移（未命中零 refused 信号） | `tests/domains/test_v2_gate.py::early_exit_position_no_drift` | specs/gate.md:165 |
| 16 | 词表闭世界只扩不删＋步标题映射＋runtimev2 面单点（消费方零副本） | `tests/domains/test_v2_gate.py::word_families_closed_world_single_source` | specs/gate.md:166 |
| 17 | import 白名单（只 `state`；AST 扫描——依赖白名单半覆盖面的降维补位） | `tests/domains/test_v2_gate.py::imports_state_only` | specs/gate.md:167 |
| 18 | 废弃词闸符号零命中（`apply_term_verdict`／`Disposition`／术语表接触零） | `tests/domains/test_v2_gate.py::no_writeback_of_term_gate` | specs/gate.md:168 |
| 19 | 【边界集】A 类语料逐条零命中；三族明显中招样本各拒；注入＋写意图同句；单边样本零命中；空串零命中 | `tests/domains/test_v2_gate.py::boundary_corpus_and_single_side` | specs/gate.md:169 |
| 20 | 【保留集】普通业务问句（语料内）过闸零命中零漂移；词表／话术迁移字面不变 | `tests/domains/test_v2_gate.py::retention_normal_questions_unchanged` | specs/gate.md:170 |

> 测试文件归属（票注，非规格引文）：本票 10 行与 -03a 的 10 行同落**同一个新建文件** `tests/domains/test_v2_gate.py`（spec :172 节尾原注已在 `RT-W3-03a-gate.md` 同节照抄，本票不重复转抄，防两处漂移）；旧承载位测试 `tests/domains/test_v2_n0_word_gates.py` 随阶段 5 迁移重写收口（本批不改）。
> 行序缺口说明（票注）：本票行序跳过 1–10——`#` 列两票共用规格表行序，便于 manifest 逐行对账。
> 规格侧缺口登记（票注，呈主窗对账）：A 类语料条数**三口径**（票面 23／自检面 14／钉测实存 20）以钉测实存 20 条为准（规格行为 9＋风险 5）；本票行 19 的语料来源锚＝`tests/domains/test_v2_n0_word_gates.py::test_n0_no_false_positive_corpus`——本票**不自行增设验收行**（增设＝改规格，回设计仓），此处只登记事实。

## 测试网钉（本块 1 条 pin 行已在 `RT-W3-03a-gate.md` 同节全量逐字转抄——本票零 pin 行，不重复转抄）

- 核对关系（防两处漂移）：pin-18 ↔ 行 1／8／9／10（四条命定用例）；其钉行逐字转抄与机检用例全在 -03a；本票 10 行不承载任何 pin 行（行 14／15／16 是其**加固观测面**——迁移字面逐字、早退位次、词表单点，与 -03a 的行 2–6 同断言集不重写）。
- 分工注（防两头认）：`pin-31`（废弃词闸新行为）**不落本块**——本票反向保证＝行 18（零符号）＋行 11（零语义判断）；`pin-21`（faq 五站链）零落点＝已裁定（本块知悉不挂）。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 pin 行只落 -03a 一处（先例 `RT-W4-05b-execution.md` 分票理由原文）。

## 施工要点（specs/gate.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/gate.md:134 | 行为 13 本块零语义判断 | 不做豁免／元问／引用形判定（V1 禁用词豁免机制不落本块、V2 亦不引入）；不判「提及 vs 执行」（已移出）；词表只作**明显命中的结构早退**（非判据） |
| specs/gate.md:133 | 行为 12 确定性纯函数、零副作用 | 同入参两跑输出相等；**零 IO、零模型调用、零时钟、零随机、零事件发射、零状态写**；**命中路径零台账接触**（V1「当场再取一次词典层缝并写回」属现状缺陷 D-B2-02——无人读的无效 I/O，重写不复刻；差异点③） |
| specs/gate.md:131 | 行为 10 词表闭世界、只扩不删、单点 | 三族清单＋三条话术为闭世界常量；**只扩不删**（扩容随红队用例回流）；runtimev2 面内各恰一处定义、消费方零副本 |
| specs/gate.md:135 | 行为 14 定位＝辅助快路径、非防线 | 命中即不放行是**快路径早退**（省一次模型调用＋给固定友好话术），**不是防线**；漏判由执行层兜——「只读」（INV-2）硬保证在执行层；断言＝本块零红线判定面（行为 12／13 的 AST 面）＋**人审** |
| specs/gate.md:136 | 行为 15 废弃词闸不落本块（防写回门口） | 本块不定义 `apply_term_verdict`、不定义 `Disposition`、不读台账／术语表、不判「提及 vs 执行」——判断＝`tool_matching` 模型产出、分派＝`preconditions` 判定序第 1 位（两头认核） |
| specs/gate.md:129 | 行为 9 零误伤与收窄口径（语料面） | A 类语料逐条过三族全 `None`（以迁移钉测语料为准，实存 20 条）；**净收窄为零**——三条口径＝V1 既有判据的规格层成立化 |
| specs/gate.md:120 | 行为 5 匹配方式三族面（迁移照抄） | 注入折叠、外发／写意图不折叠（纯子串）——三族不齐＝V1 事实面（现状证据 D-B2-04，仅作证据；统一折叠＝规格变更） |

结构锚：specs/gate.md:39–:96 接口定义（**形状真源＝-03a 已落地的 `screen`＋`Refusal`＋常量族八件＋`STEP_TITLES`**，本票只加元面断言、不改形状）；:98–:103 返回两态闭世界／错误契约／入参纪律（**纯文本进出、零 state 字段读、无数值面、零时钟零随机零 IO 零模型**）；:105–:112 框架与依赖红线（R5b／R5／R6／R7 已真跑；依赖白名单、零模型、R2 深层子模块三半面**诚实声明无专属闸**→AST 断言＋人审）；:138 V2 定案差异点表（本票行 14 按其逐条比对，**差异点表外零偏离**）；:140–:145 不降级与静默禁令（**合法降级路径＝无**；未命中＝静默放行——**漏判非降级面**，执行层兜；命中必留机读信号但发射与落账＝消费方义务）。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三——归块行指针，不重复转抄）

- B4（§三 表内明写「专属钉（对应 `gate`）」，严重度「中」）的逐字转抄、钉法口径注（「禁用词闸族」系裁决 #12 移出前族名）与专属钉义务在 **`RT-W3-03a-gate.md`** 同节落定（指针，防两处真源漂移）——本票不重复转抄、不冒充覆盖。
- 本票织网义务＝① 本票 10 行对应用例落网（其中行 14 迁移字面对比件、行 15 早退位次、行 16 词表单点、行 19／20 边界与保留网面）；② L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」10 行逐行实现为 `tests/domains/test_v2_gate.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行；`#` 保留规格表行序 11–20）；
- 「测试网钉」零 pin 行——本票只写归属指针，不重复转抄（pin-18 行本体与四条命定用例全在 -03a）；
- 四条元面 AST 断言绿：`::no_semantic_judgement_in_gate`／`::screen_pure_deterministic`（零 IO／模型／时钟／随机／emit／写）／`::hit_path_zero_io`（零 ledger／DB 符号）／`::imports_state_only`（只 `state`）；
- 两条单点断言绿：`::migrated_literals_verbatim`（词表／话术／步标题 vs V1 快照逐字，差异点表外零偏离）／`::word_families_closed_world_single_source`（词表闭世界只扩不删、消费方零副本）；
- 零写回保证绿：`::no_writeback_of_term_gate`（`apply_term_verdict`／`Disposition`／术语表接触零命中）；
- 早退位次与静默零漂移（行 15）＋边界与保留（行 19／20：A 类语料逐条零命中、三族明显中招各拒、单边与空串零命中；普通业务问句过闸零漂移）；A 类语料以钉测实存 **20 条**为准（三口径差已登记）；
- 形状单点：`screen` 签名、`Refusal` 形状与常量族仍以 -03a 落地的为唯一真源，本票不改形状（改形状＝回 -03a 或回设计仓）；
- 边界闸 R5／R5b／R6／R7 在 `lint-imports` 双配置下绿；gate 依赖白名单／零模型／R2 深层子模块三半面无专属闸——按规格诚实声明以 AST 断言＋人审补位（登记待补）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W3-03b 完成，产物 `appv2/runtimev2/gate/`（元面与边界簇），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
