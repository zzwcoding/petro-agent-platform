# RT-W3-02b · context——V2 上下文（-B：元面与边界簇——纯函数确定性／import 与写面扫描／常量与渲染单点／边界·保留集）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/context.md`（状态「已定稿」——前置满足）
Touches modules: `context`（本票只填 context 元面与边界簇；六函数签名与常量族以 -02a 落地的为唯一真源；规格「触及的模块」表另声明 `state`／`tools` 两关联侧，归各自票承接）
波次: W3 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W3 行三列原文：块列「`context` `bookkeeping` `gate`」；理由列「组合件，依赖 W2 的 gateway_adapter；bookkeeping 单写口是相位开发的共同依赖」；出口判据列「每模型调用有 Manifest；写口无旁路（AST＋import 双证）；两道闸机械分派」
复审强度: 50% 抽查（eng/03 §五 W3 行 A 列含 `context`——该表降级保留的规则原文「A 列抽 50%」；双队制已废止，A/B 分配只余复审强度语义，波序与块归属不变）
前置: ① 规格定稿（`specs/context.md` 已定稿——已满足）；② **`RT-W3-02a-context.md` 收票**（同包顺序施工、同包不并行——六函数签名与常量族以 -02a 为唯一真源）；③ 波次前置：**W2 全收波**（eng/03 §一依赖图原文「context → state」＋ §二 W3 行理由列「组合件，依赖 W2 的 gateway_adapter」，经 -02a 传递，已满足）
阻塞: `RT-W3-02a-context.md`（-02b 前置＝-02a 收票）｜被阻塞: W4 消费方（`answering` 材料面＋`orchestration` 装载时点与追加编排）

## 任务

接 `RT-W3-02a-context.md` 落地的骨架与渲染器族，填 `appv2/runtimev2/context/` 的**元面与边界簇**：渲染器族纯函数确定性（两跑相等、入参深比较不变、AST 零 IO／模型／时钟／随机／emit）、import 白名单与写面唯一（只 `state`＋`tools`；唯一写面 `ledger_dump`；零帧）、程序侧零词表零正则、帽/预算常量单点（注入制无缺省裸字面）、渲染单点（消费方零副本）、本块零合同字面，以及【边界集】／【保留集】两行。

**本票＝context 的 -B 票**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **21 行**，超 15 行上限 → 切 -A／-B 两票；本票收**剩余 8 行**＝规格表第 13–18、20、21 行（渲染器族纯函数确定性／import 白名单与写面唯一·零帧／无词表正则／帽预算常量单点／渲染单点／零合同字面／【边界集】／【保留集】）；前 13 行（第 1–12、19 行）与**本块 4 条 pin 行**（pin-09／pin-08／pin-22／pin-30）全在 -02a，本票零 pin 行、不重复转抄（同一 pin 行两票重复转抄＝两处真源必漂移）。两票同包**顺序施工**（同包不并行）：本票只填元面与边界行为、**不改 -02a 落地的形状**（六函数签名＋常量族——改形状＝回 -02a 或回设计仓）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （5 份）`specs/context.md` 全文（十节版式——行为 12–14 的元面清单、不降级节的「零静默省略」红线、行为 4／8／9 的常量单点句都在规格行内）；`specs/modules.md` `## context` 卡（签名以卡为准、族与签名以规格「V2 定案签名」为准——本票不改形状）；`specs/state.md`（`ledger_dump` 写面＋`Manifest` 十字段＋字段形状——写面扫描与形状真源）；`specs/prompts.md`（合同常量六族与答案要求清单——`::no_contract_literals_in_context` 的扫描对偶面，六族首句特征子串定义源）；`tools/importlinter_v2.toml`（R2／R5／R5b／R6／R7 契约——边界闸落点与 AST 断言的对照面）。eng/04 §三 关联行已在 `RT-W3-02a-context.md`「织网义务」节逐字转抄，本票不重复、只写指针。

**小票制自检（流水 48）**：票面对象 8 行 ≤ 15 ✓；先读 5 份 ≤ 6 ✓；聚焦一个行为簇＝「元面与边界」（AST 与单点断言＋边界集／保留集）✓ → 本票不派生。

框架红线: 无点名框架（本块不引入任何框架；纯字符串与字典处理）——对应闸 R5b 契约（`tools/importlinter_v2.toml` :101）
边界红线: ① **只经 `tools` 公开面接触世界**——R6（:110）；② 不引旧码 `appv2.runtime.*`——R5（:95）；③ 不直引 `appv2.infra.llm_client`——R7（:119）；④ 消费方向（R2）＝消费方只经包根 `appv2.runtimev2.context`（forbidden 含 `appv2.runtimev2.context.*`——:74）；⑤ **零模型调用**（连 `gateway_adapter` 都不 import）＋**依赖白名单＝`state`＋`tools` 两块**（禁引其余 runtimev2 块）——两条均无专属闸→AST 断言 `::imports_and_write_ports_scan`＋人审；⑥ **写入面单点扫描面**：全块唯一状态写入＝`ledger_dump` 取一次装载，`messages`／`steps`／`notices`／`process_notes`／`dialogue`／`next_intent` 零写；⑦ **零帧**（本块零 `emit`——帧面归发射方）；⑧ **程序侧零词表／零正则语义判定**（AST；豁免面＝形态处理——集合成员判定／字符串归一／字符截取）；⑨ **禁手写替代（渲染单点）＋本票面**：不得改 -02a 已定的六函数签名与常量族另立第二套，不得在消费方块私建同形副本

## 票面对象（specs/context.md「验收测试」表逐行转抄——本票 8 行：规格表第 13–18、20、21 行）

〔来源：specs/context.md「验收测试」表 :135–:155（本票取自 :147–:152、:154–:155），逐行原文；`#` 列＝规格表行序（与 -02a 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 13 | 渲染器族纯函数确定性：两跑相等、入参深比较不变、零 IO/模型/时钟/随机/emit（AST） | `tests/domains/test_v2_context.py::renderers_pure_deterministic` | specs/context.md:147 |
| 14 | import 白名单（只 `state`＋`tools`）＋写面唯一（`ledger_dump`）＋零帧（AST 扫描） | `tests/domains/test_v2_context.py::imports_and_write_ports_scan` | specs/context.md:148 |
| 15 | 程序侧无词表／正则语义判断（AST；豁免面＝形态处理） | `tests/domains/test_v2_context.py::no_lexicon_or_regex_in_context` | specs/context.md:149 |
| 16 | 帽/预算常量单点（`DEFAULT_MAX_OBSERVATIONS`／`PROCESS_NOTES_BUDGET` 各一处、注入制无缺省裸字面） | `tests/domains/test_v2_context.py::cap_constant_single_point` | specs/context.md:150 |
| 17 | 渲染单点：材料/过程档/信任映射/帽/三来源行映射（`RESIDENT_SOURCE_ROWS`）在 runtimev2 面内各恰一处定义（消费方零副本） | `tests/domains/test_v2_context.py::renderers_single_source` | specs/context.md:151 |
| 18 | 本块零合同字面（六族特征子串零命中） | `tests/domains/test_v2_context.py::no_contract_literals_in_context` | specs/context.md:152 |
| 20 | 【边界集】空材料／全 notice／权威超帽／检索超帽／超长档案／超窗链 → 各落空段、全量、披露、摘要各分支 | `tests/domains/test_v2_context.py::boundary_empty_overcap_overwindow` | specs/context.md:154 |
| 21 | 【保留集】常规材料渲染与常规档案（无截断、预算内）输出逐字不变；既有 `[n]` 序号与排序行为不因本批改形回归 | `tests/domains/test_v2_context.py::retention_normal_render_unchanged` | specs/context.md:155 |

> 测试文件归属（票注，非规格引文）：本票 8 行与 -02a 的 13 行同落**同一个新建文件** `tests/domains/test_v2_context.py`（spec :157 节尾原注已在 `RT-W3-02a-context.md` 同节照抄，本票不重复转抄，防两处漂移）；旧承载位既有测试随阶段 5 迁移重写收口（本批不改）。
> 行序缺口说明（票注）：本票行序跳过 1–12、19——`#` 列两票共用规格表行序，便于 manifest 逐行对账。
> 核对注（防两处漂移）：行 19（`::truncation_signal_no_emit`）＝pin-09 的落点行之一，随 -02a 不划本票——本票行 14 的「零帧」扫描面与其**同源不重复**（行 14 覆盖 import／写面／零帧的 AST 扫描面；行 19 覆盖披露行＋字段两面在场与零 emit 的语义断言，二者同断言集不重写）。

## 测试网钉（本块 4 条 pin 行已在 `RT-W3-02a-context.md` 同节全量逐字转抄——本票零 pin 行，不重复转抄）

- 核对关系（防两处漂移）：pin-09（渲染面披露）↔ 行 5／6／19、pin-08（渲染帽分形面）↔ 行 4、pin-22（视图面）↔ 行 9、pin-30（compaction 半面）↔ 行 9——四条钉的逐字转抄与机检用例全在 -02a；本票 8 行不承载任何 pin 行。
- 分工注（防两头认）：本票行 16（常量单点）与行 17（渲染单点）**只加固** -02a 已落地的常量族与渲染件定义点（不改其值、不改其形）——定义点真源在 -02a；行 18 的合同六族特征子串扫描范围对偶于 `specs/prompts.md` 行为 1（六族定义点在 `prompts`，本块零合同、零指令）。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 pin 行只落 -02a 一处（先例 `RT-W4-05b-execution.md` 分票理由原文）。

## 施工要点（specs/context.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/context.md:120 | 行为 12 渲染器族纯函数确定性＋IO 面单点 | 五个渲染器同入参两跑逐字（或深比较）相等、**调用前后入参深比较相等**（零写入）；零 IO、零模型调用、零时钟读取、零随机、零事件发射；**唯一 IO 面＝`load_ledger_dump` 的 tools 调用** |
| specs/context.md:121 | 行为 13 程序不判语义 | 全部判定＝闭世界查表／排序／计数／截断／字符串归一／字符截取——零词表零正则语义判定；豁免面＝形态处理（集合成员判定／字符串归一／字符截取） |
| specs/context.md:122 | 行为 14 本块零合同零指令 | 不定义、不复制合同常量文本与指令骨架（材料段/过程段是唯一文本产物面）；相位包组成与重发判定均不落本块；断言＝合同六族特征子串在本块源码零命中 |
| specs/context.md:112 | 行为 4 数值单点（帽） | 帽值经注入参数、**数值单点＝常量 `DEFAULT_MAX_OBSERVATIONS`**（具体值不落规格） |
| specs/context.md:116 | 行为 8 数值单点（过程档案预算） | 有界值＝注入参数 `budget`〔无缺省〕、**数值单点＝常量 `PROCESS_NOTES_BUDGET`** |
| specs/context.md:117 | 行为 9 数值单点（视窗） | 触发参数 `dialogue_view_tokens` **注入制、无裸值**（数值已裁 8k 档、承载位＝`RunState` 独立字段） |
| specs/context.md:102 | 红线 零模型／依赖白名单 | 不直引 `appv2.infra.llm_client`；依赖白名单＝`state`＋`tools` 两块、禁引其余 runtimev2 块——无专属闸→人审＋AST 断言 |
| specs/context.md:104 | 红线 写入面单点 | 全块唯一状态写入＝`load_ledger_dump` 对 `state.ledger_dump` 的取一次装载；共享写面零写（写口归 `bookkeeping`） |
| specs/context.md:105 | 红线 禁手写替代（渲染单点） | 材料段渲染／过程档案渲染／信任映射／帽常量／三来源行映射在 runtimev2 面内各恰一处定义，禁相位块另存副本（`::renderers_single_source`） |

结构锚：specs/context.md:39–:89 接口定义（**形状真源＝-02a 已落地的六函数与常量族**，本票只加元面断言、不改形状）；:91–:95 返回契约／入参纪律／错误契约；:124–:129 不降级与静默禁令（**合法降级路径＝无**；**本块零静默省略**——不输出省略号形占位，一切有界处理以披露行或披露账目显式表达；AST 扫描本块零 `emit`）；:131–:155 验收测试表（`#` 行序与 -02a 共用）。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三——关联行指针，不重复转抄）

- §三 表内**无一行明写本块**（该表明写块名者只有 B1→`bookkeeping`／B2→`orchestration`／B2b→`preconditions`／B4→`gate`）；本块侧**无新行可逐字转抄**——B3（「每限额上限/触顶收敛行为钉」）的逐字转抄落 `RT-W1-01b-state.md` 同节、B1 落 `RT-W3-01a-bookkeeping.md`、B4 落 `RT-W3-03a-gate.md`（§三 各行恰一票逐字转抄）；相邻面口径的登记在 `RT-W3-02a-context.md` 同节（指针，防两处真源漂移）——本票不重复转抄、不冒充覆盖。
- 本票织网义务＝① 本票 8 行对应用例落网（其中行 16／17 是常量单点与渲染单点的「零副本」观测面，行 20／21 是边界与保留网面）；② L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」8 行逐行实现为 `tests/domains/test_v2_context.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行；`#` 保留规格表行序 13–18、20、21）；
- 「测试网钉」零 pin 行——本票只写归属指针，不重复转抄（4 条全在 -02a）；
- 四条 AST 断言绿：`::renderers_pure_deterministic`（两跑相等＋入参深比较＋零 IO/模型/时钟/随机/emit）／`::imports_and_write_ports_scan`（只 `state`＋`tools`；写面唯一 `ledger_dump`；零帧）／`::no_lexicon_or_regex_in_context`（豁免面按规格原文）／`::no_contract_literals_in_context`（合同六族特征子串零命中）；
- 单点两条绿：`::cap_constant_single_point`（两类常量各一处、注入制无缺省裸字面）／`::renderers_single_source`（五组渲染件在 runtimev2 面内各恰一处定义、消费方零副本）；
- 边界与保留：空材料／全 notice／权威超帽／检索超帽／超长档案／超窗链六形各落对应分支（行 20）；常规渲染与常规档案逐字不变、既有 `[n]` 序号与排序行为不回归（行 21）；
- 形状单点：六函数签名与常量族仍以 -02a 落地的为唯一真源，本票不改形状（改形状＝回 -02a 或回设计仓）；
- 边界闸 R2／R5／R5b／R6／R7 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W3-02b 完成，产物 `appv2/runtimev2/context/`（元面与边界簇），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
