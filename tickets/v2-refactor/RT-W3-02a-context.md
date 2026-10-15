# RT-W3-02a · context——V2 上下文（-A：骨架＋渲染器族功能行为簇＋全部 4 pin 行）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/context.md`（状态「已定稿」——前置满足）
Touches modules: `context`（本票只建 context 本体与渲染器族；规格「触及的模块」表另声明 `state`／`tools` 两关联侧——`state`＝字段形状与 `Manifest` 十字段、唯一写面＝`ledger_dump` 取一次装载；`tools`＝台账/名录投影取得的唯一世界接触面）
块性（spec :6 原注照抄）：本块＝**确定性渲染／装载块**（真源 `docs/runtime-refactor/walk/判断归责表.md`）——材料渲染、配额与截断、过程档案有界摘要全部是程序结构判（闭世界映射／排序／计数／截断／字符处理），**零语义判断**（无词表无正则判语义）；凡语义判断（哪支材料有用／答没答上）一律不落本块。
波次: W3 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W3 行三列原文：块列「`context` `bookkeeping` `gate`」；理由列「组合件，依赖 W2 的 gateway_adapter；bookkeeping 单写口是相位开发的共同依赖」；出口判据列「每模型调用有 Manifest；写口无旁路（AST＋import 双证）；两道闸机械分派」
复审强度: 50% 抽查（eng/03 §五 W3 行 A 列含 `context`——该表降级保留的规则原文「A 列抽 50%」；双队制已废止，A/B 分配只余复审强度语义，波序与块归属不变）
前置: ① 规格定稿（`specs/context.md` 已定稿——已满足）；② 波次前置：**W2 全收波**（eng/03 §一依赖图原文「context → state」＋ §二 W3 行理由列「组合件，依赖 W2 的 gateway_adapter」；W2 五票＝persistence／transport／gateway_adapter／prompts／parsing，其中 `parsing` 票＝`RT-W2-05a/b-parsing.md`——本批新票）；③ 票内前置：无（-A 为本块首票；占位骨架 `appv2/runtimev2/context/__init__.py` 已随阶段 2 落锤）
阻塞: W2 全收波（`RT-W2-01a/b-persistence.md`／`RT-W2-02a/b-transport.md`／`RT-W2-03a/b-gateway_adapter.md`／`RT-W2-04a/b/c-prompts.md`／`RT-W2-05a/b-parsing.md`，按子票计；票号以主窗 manifest 为准）｜被阻塞: `RT-W3-02b-context.md`（同包顺序施工——-02b 前置＝-02a 收票；六函数签名与常量族以 -02a 为唯一真源）；`RT-W3-03a/b-gate.md`（同波，依赖 W2 全收）＋W4 消费方（`answering` 材料面＋`orchestration` 装载时点与追加编排）

## 任务

按 `specs/context.md` 新建 `appv2/runtimev2/context/`：把「发给模型的上下文材料」做成**确定性渲染产物＋只读投影装载**——材料段（`[n]` 引标视图）、过程档案（有界摘要段）、台账/名录投影取得（经 `tools` 公开面装载进 `state`）、对话链追加面（追加内容渲染＋超窗 compaction 治理）、每次模型调用的**材料面 Manifest 编译**；**纯渲染与机械处理，零判断**（规格「目标」节原文：「判断在模型，渲染在程序，互不越位」）。

**本票＝context 的 -A 票（骨架＋六函数功能行为簇＋本块全部 4 pin 行）**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **21 行**，超 15 行上限 → 切 **-A／-B** 两票。本票收 **13 行**＝规格表第 1–12 行（材料段渲染／信任级映射／排序／分承载体预算／截断披露行／Manifest 三机检字段＋`selected_reason`／每次调用 Manifest 与来源行／过程档案有界段／compaction 超窗视图／compaction 预算内零漂移／投影取一次／取得失败 fail-fast）＋第 19 行（截断机读信号两面在场、本块零 emit——pin-09 的三个落点行之一，与行 5／6 同簇）＋ **4 条 pin 行全量**（pin-09／pin-08／pin-22／pin-30，逐字转抄见「测试网钉」节）；剩余 **8 行**＝规格表第 13–18、20、21 行（渲染器族纯函数确定性／import 白名单与写面唯一／无词表正则／帽预算常量单点／渲染单点／零合同字面／【边界集】／【保留集】）归 `RT-W3-02b-context.md`。两票同包**顺序施工**（同包不并行）：本票出骨架、族名单与公开面，-02b 只填元面与边界簇、不另立第二套形状（改形状＝回本票或回设计仓）。
**骨架/接口归本票**：六函数签名（`load_ledger_dump`／`render_materials`／`render_process_notes`／`compile_manifest`／`compact_messages`／`trust_of`——**族名单闭世界**）＋常量族（`DEFAULT_MAX_OBSERVATIONS`／`PROCESS_NOTES_BUDGET`／`TRUST_AGG`／`TRUST_LEDGER`／`TRUST_REPORT`／`RESIDENT_SOURCE_ROWS`）随本票落位（规格 :39–:89 接口定义）；卡面 `compile` 为阶段 2 初拟形、**不施工**（卡级登记件，风险 7①，本票不改卡）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/context.md` 全文（十节版式——行为 1–11 的渲染字面、披露行、`selected_reason` 槽位归一表、compaction 摘要形与保留窗三条保证都在规格行内，施工以规格原文为准；其行为 6 的 `selected_reason` 逐字稿载体＝`tickets/v2/V2-61-材料承载分形渲染.md` 附 A，规格行内已转写槽名）；`specs/modules.md` `## context` 卡（签名初拟形与族名单权威注——**族与签名以规格「V2 定案签名」为准**，`compile` 不施工）；`specs/state.md`（`ledger_dump`／`process_notes`／`messages`／`observations`／`Manifest` 十字段字段形状——唯一写面＝`ledger_dump`）；`appv2/runtime/context.py`（**材料段渲染的逐字稿载体**——段头／块形／空段／披露行字面）；`appv2/runtime/graph.py`（**过程档案段的迁移载体** `_render_process_notes`——头注与条目行形、预算起算、披露行）；`tickets/v2/V2-79d-compaction摘要化.md` §1.1／§1.2（**compaction 摘要形逐字稿载体**——摘要头与「问：／答：」行、截数 120）。eng/04 §三 归块行登记（按实＝无明写行；相邻面口径）在「织网义务」节，施工期不必另开；`specs/prompts.md`／`specs/answering.md` 的消费面对账面＝登记件（风险 7④／行为 14），本票只写指针。

**小票制自检（流水 48）**：票面对象 13 行 ≤ 15 ✓；先读 6 份 ≤ 6 ✓；聚焦一个行为簇＝六函数的**功能行为面**（渲染→装载→编译→compaction 一条确定性管线，含全部 pin 行承载行）✓ → 本票不派生（只切 -B 承接元面与边界簇）。

框架红线: 无点名框架（本块不引入任何框架；纯字符串与字典处理）——对应闸 R5b 契约（`tools/importlinter_v2.toml` :101）
边界红线: ① **只经 `tools` 公开面接触世界**（台账/名录投影取得唯一路径；禁直引 `knowledge`／`query`／`retrieval` 引擎、禁直连 DB）——R6（:110）；② 不引旧码 `appv2.runtime.*`——R5（:95）；③ 不直引 `appv2.infra.llm_client`——R7（:119）；④ **零模型调用**（连 `gateway_adapter` 都不 import）——AST `::imports_and_write_ports_scan`；**诚实声明**：R1–R8 无「禁引 `gateway_adapter` 于 context」专属闸；⑤ **依赖白名单＝`state`＋`tools` 两块**（禁引其余 runtimev2 块）——无专属闸→人审＋AST 断言；⑥ **写入面单点**：全块唯一状态写入＝`load_ledger_dump` 对 `state.ledger_dump` 的取一次装载；`messages`／`steps`／`notices`／`process_notes`／`dialogue`／`next_intent` 等共享写面**零写**（写口归 `bookkeeping`）；⑦ **零时钟接触**（帽、预算与视窗为注入参数、无缺省裸字面）；⑧ **禁手写替代（渲染单点）**：材料段渲染／过程档案渲染／信任映射／帽常量／三来源行映射在 runtimev2 面内各恰一处定义（消费方零副本）

## 票面对象（specs/context.md「验收测试」表逐行转抄——本票 13 行：规格表第 1–12、19 行）

〔来源：specs/context.md「验收测试」表 :135–:155（本票取自 :135–:146、:153），逐行原文；`#` 列＝规格表行序，-02b 票续用同一行序不重编〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | 材料段渲染形逐字迁移（段头／块形／空段空括号／空材料「（无）」） | `tests/domains/test_v2_context.py::material_segment_verbatim_render` | specs/context.md:135 |
| 2 | 信任级映射闭世界（十 kind 三族；异常输入落 `report`；notice 排除） | `tests/domains/test_v2_context.py::trust_mapping_closed_world` | specs/context.md:136 |
| 3 | 排序＝信任级稳定序（同 rank 保持入栈序；两跑同序） | `tests/domains/test_v2_context.py::trust_order_stable` | specs/context.md:137 |
| 4 | 分承载体预算：权威/台账族全量无帽、检索族超帽才截断 | `tests/domains/test_v2_context.py::carrier_fractal_budget` | specs/context.md:138 |
| 5 | 截断披露行逐字在场（两计数正确）；未截断零残留 | `tests/domains/test_v2_context.py::truncation_disclosure_line_verbatim` | specs/context.md:139 |
| 6 | Manifest 三机检字段（四态）＋`selected_reason` 逐字形 | `tests/domains/test_v2_context.py::manifest_material_fields_and_reason` | specs/context.md:140 |
| 7 | 每次调用 Manifest 在场（零材料亦在）且材料标来源（四列表同长；常驻来源行按呼叫分型） | `tests/domains/test_v2_context.py::manifest_present_source_rows` | specs/context.md:141 |
| 8 | 过程档案摘要段：零档案零段／有界／披露行逐字／全入预算无披露 | `tests/domains/test_v2_context.py::process_notes_bounded_summary` | specs/context.md:142 |
| 9 | compaction：超窗视图（system 摘要置位＋最新轮恒在场＋单巨轮零压缩＋合同/相位包不摘＋原史零覆盖＋披露账目追加合成） | `tests/domains/test_v2_context.py::compaction_overwindow_model_view` | specs/context.md:143 |
| 10 | compaction：预算内原样返回、披露为空（零漂移） | `tests/domains/test_v2_context.py::compaction_within_budget_no_drift` | specs/context.md:144 |
| 11 | 投影取得：经 tools 公开面、取一次（已有投影〔含空投影〕零工具调用）；返回值副本语义 | `tests/domains/test_v2_context.py::ledger_load_via_tools_take_once` | specs/context.md:145 |
| 12 | 取得失败＝run 终局失败＋用户面稳定错误提示在场＋Manifest 过程注记留痕可查（合法空结果不触发失败腿） | `tests/domains/test_v2_context.py::ledger_load_failure_run_failed_honest` | specs/context.md:146 |
| 19 | 截断机读信号两面在场（披露行＋字段）；本块零 emit（帧面归发射方） | `tests/domains/test_v2_context.py::truncation_signal_no_emit` | specs/context.md:153 |

> 测试文件归属（spec :157 节尾原注照抄）：本块验收测试绑**新建** `tests/domains/test_v2_context.py`（`context` 是阶段 2 新划的公共层块 `appv2/runtimev2/context/`；`ls tests/domains/` 实测无同名文件，无冲突）；旧承载位既有测试（如 `tests/domains/test_v2_v61_material_rendering.py`）随阶段 5 迁移重写收口（本批不改）；fixture＝材料集／投影集／状态工厂（卡面 Adapter：fixture 材料集）。全部测试标识＝**待织网（阶段 5）**。
> 行序缺口说明（票注）：本票行序跳过 13–18、20、21——`#` 列两票共用规格表行序，便于 manifest 逐行对账。
> 本块不涉面（防一头两认）：行 13–18、20、21（渲染器族纯函数确定性／import 白名单与写面唯一·零帧／无词表正则／帽预算常量单点／渲染单点／零合同字面／【边界集】／【保留集】）归 `RT-W3-02b-context.md`；行 19 保在本票＝**pin-09 的落点行之一**（pin 行与其落点行不分票，先例 `RT-W2-04a-prompts.md` 注原文「pin-13 绑行 18——答案轮装配簇必须在本票，不得划给 -04b」）；本票已落地的六函数签名与常量族**不改**（改形状＝回本票或回设计仓）。
> 规格侧缺口登记（票注，呈主窗对账；按规格原文处理、**不增设验收行**——增设＝改规格，回设计仓）：
> - **① 装载入口形＝前置核定项**（规格风险 5 原文逐字两段：「**loader 的 tools 公开面调用形未落定**」＋「**已裁（流水 43⑥）：大面维持原裁**（context 经 `tools` 装载）；tools 装载入口形＝**阶段 5 context 施工票前置核定——流水 43⑥**（`tools` 规格旧版式、现在定不出真形）」）。本票行 11／12（`load_ledger_dump` 经 `tools` 公开面取一次／失败 fail-fast）依赖该**入口形**——施工子代理按规格原文实现装载语义，**入口形未获核定时停报 L0、不自行发明 `tools` 入口形**（AGENTS.md 6b：对逐字稿与未裁项只许照抄，偏离即停）。
> - **② 识别面参形＝待裁登记项**（规格风险 4 与行为 9 原文：「**参形随风险 4 落点裁定后入签名**〔登记〕」——合同/相位包识别面的结构化参形尚未落定；键名已定＝`origin`、承载位已定＝`RunState` 独立字段 `dialogue_view_tokens`）。本票行 9 的 `compact_messages` 签名按规格「V2 定案签名」落位，**识别面参形未裁定前不得自造**——停报 L0。

## 测试网钉（specs/context.md「与闸的挂钩表」pin 行逐行转抄——全块 4 行，全在本票）

〔来源：specs/context.md「与闸的挂钩表」:186–:189，逐行原文；列名同规格「本规格的硬要求｜挂钩｜现状」〕

| 本规格的硬要求（原文） | 挂钩（原文） | 现状（原文） |
|---|---|---|
| 材料截断必披露（**渲染面**：披露行逐字＋三机检字段＋`selected_reason` 帽账） | 钉 **`pin-09`**（P1，**渲染面**）——**分工**：字段面挂 `specs/state.md`（`Manifest.material_truncated`）、披露行为面挂 `specs/answering.md`、帧面挂 `specs/transport.md`；本块落**产断面**（行为 5／6／不降级节，测试 `::truncation_disclosure_line_verbatim`／`::manifest_material_fields_and_reason`／`::truncation_signal_no_emit`） | 待织网（阶段 5） |
| 明细行集题不丢行（**渲染面**：权威/台账族全量无帽、帽只作用检索族） | 钉 **`pin-08`**（P0，**渲染面**）——**分工**：交付行为面挂 `specs/answering.md`（`::rowset_full_delivery`，钉行在册）；同一规则另见 `specs/execution.md` 行为 4（其挂钩表已补 pin-08 行——流水 43⑦b）；本块落**渲染帽分形面**（行为 4，测试 `::carrier_fractal_budget`） | 待织网（阶段 5） |
| 对话链只追加不改写（**视图面**：compaction 只产模型视图、`state.messages` 零覆盖） | 钉 **`pin-22`**（P0，**视图面**）——**分工**：字段契约面挂 `specs/state.md` 行为 4、写入面挂 `specs/bookkeeping.md` 行为 7；本块落「视图不改原史」面（行为 9，测试 `::compaction_overwindow_model_view`） | 待织网（阶段 5） |
| 超窗 compaction 摘要化（`pin-30` 的 compaction 半面；另半面＝旧 run 黑匣子回放如实空显挂 `specs/persistence.md` 行为 12、旧检查点状态读入挂 `specs/state.md` 行为 8） | 钉 **`pin-30`**（P2）——本块落 **compaction 半面**（行为 9，测试 `::compaction_overwindow_model_view`）；触发参数数值与承载位＝登记（风险 4） | 待织网（阶段 5） |

- 钉落点对读两行（**非 pin 行**，逐字转抄以防一头两认；列名同上）：

| 本规格的硬要求（原文） | 挂钩（原文） | 现状（原文） |
|---|---|---|
| `pin-24`（相位合同一次性）经逐条核实**不落本块** | 钉落点对读：记账面挂 `specs/state.md` 行为 5、写入面挂 `specs/bookkeeping.md` 行为 8、常量稳定面挂 `specs/prompts.md` 行为 1；**消费侧重发判定**＝追加编排归 `orchestration`＋标记写入归 `bookkeeping`——context 零合同、零标记、零追加时点 | 已核实（本批起草时逐条对读） |
| `pin-26`（对话层纯度）经逐条核实**不落本块** | 钉落点对读：字段面挂 `specs/state.md` 行为 6、写入面挂 `specs/bookkeeping.md` 行为 9、渲染面挂 `specs/understanding.md` 挂钩表；本块只经过程档案段渲染（本块过程段候选不入 `dialogue`——`dialogue` 写口不在本块） | 已核实（本批起草时逐条对读） |

- 分工注（票注，防两头认）：pin-09 落点＝本票行 5（披露行逐字）／行 6（三机检字段＋`selected_reason`）／**行 19**（机读信号两面在场、零 emit）——三条用例即该钉「产断面」的全部落点，故行 19 随本票不划 -02b；pin-08 落点＝本票行 4（**渲染帽分形面**，丢行=0 的渲染侧）；其**交付行为面**在 `specs/answering.md`（`RT-W4-06b-answering.md`）／**执行侧**在 `specs/execution.md` 行为 4（`RT-W4-05a-execution.md` 行 4）——本票不重复转抄他票 pin 行全文；pin-22 落点＝本票行 9（视图不改原史）——字段契约面在 `specs/state.md`、写入面在 `specs/bookkeeping.md` 行为 7（`RT-W3-01a-bookkeeping.md`）；pin-30 落点＝本票行 9（compaction 半面），另两面（黑匣子回放如实空显／旧检查点状态读入）在 `specs/persistence.md` 行为 12／`specs/state.md` 行为 8。**触发参数数值与承载位**＝登记项：数值已裁 8k 档（流水 43④）、承载位已定＝`RunState` 独立字段 `dialogue_view_tokens`（流水 46①／49），规格风险 4 按此收口。
- pin 行分布（防两处漂移，逐字稿纪律）：本块 4 条 pin 行**全在本票**逐字转抄；`RT-W3-02b-context.md` 零 pin 行、只写归属指针。

## 施工要点（specs/context.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/context.md:109 | 行为 1 材料段渲染形逐字迁移 | 段头逐字（`"\n观察材料：\n"`）；块形 `[{index}]（{label}）{content}`（`index`＝观察自带全局序号、非渲染位次）；段序 `信任级｜来源｜井`（空段跳过、三段全空＝空括号）；`content` 缺失＝空串；空材料集正文＝「（无）」——**承载位换、文本不变** |
| specs/context.md:110 | 行为 2 信任级映射闭世界＋notice 排除 | `trust_of` 只读 `locator.kind`、`str()` 归一后查表；缺 `locator`／缺 `kind`／未知 kind 统一落 `report`（不抛错）；十 kind 三族闭世界；`notice` 名义入表但材料段整体排除（不进模型面、不计任何计数） |
| specs/context.md:111 | 行为 3 排序＝信任级稳定序 | `authoritative`＜`ledger`＜`report`（rank 0／1／2，同 rank 保持入栈序、稳定排序）；两跑逐字相等（确定性不抖动） |
| specs/context.md:112 | 行为 4 分承载体预算（分形帽） | 权威/台账族恒全量渲染、不设支数帽；**帽只作用检索族**（超帽才截断）；帽值经注入参数 `max_observations`，数值单点＝常量 `DEFAULT_MAX_OBSERVATIONS` |
| specs/context.md:113 | 行为 5 截断必披露（模型面披露行逐字） | 检索族截断时材料段尾接披露行（逐字稿载体＝现状 `appv2/runtime/context.py`）；未截断样本零披露行（零残留）；两个计数与元数据一致 |
| specs/context.md:114 | 行为 6 Manifest 三机检字段与 `selected_reason` | `material_truncated` ⇔ 检索族截断；`material_rendered`＝权威/台账族支数＋实渲检索支数；`material_total`＝排除 notice 后材料总数；**零材料步＝(0, 0, False)**；`selected_reason` 按逐字形拼装（槽位归一表＝{A}／{R}／{M}／{帽}／{K}／{总}） |
| specs/context.md:115 | 行为 7 每次模型调用都有 Manifest 且材料标来源 | 材料面 Manifest 由本块编译、随步落地（缺位＝判失败）；`source_type`／`source_id`／`version`／`trust_level` 四列表**逐条对应同一来源序列（等长）**——实投材料逐支＋当轮投入常驻块时其三块来源行；三来源行映射唯一落点＝常量 `RESIDENT_SOURCE_ROWS`；`as_dict` 全键恒出（十键） |
| specs/context.md:116 | 行为 8 过程档案摘要段有界（逐字迁移） | 零档案＝零段（返回空串）；头注逐字「【本 run 已做（过程档案摘要——防重参考，不是作答材料）】」；条目行形 `- [{phase}] {title}｜{digest}`（`phase` 缺失＝`?`）；预算含头注起算、逐条累加、超即止（`budget` 注入参、数值单点＝`PROCESS_NOTES_BUDGET`）；超预算追加披露行并停止；**段永不作对话轮** |
| specs/context.md:117 | 行为 9 超窗 compaction＝模型视图压缩（`pin-30` 半面） | 触发参数 `dialogue_view_tokens` **注入制、无裸值**（数值 8k 档／承载位＝`RunState` 独立字段）；自尾向前保留近期轮（**保留窗三条保证**：至少 1 轮——最新轮恒在场；单轮独占预算＝原样放行零压缩）；最旧对话轮对摘要化（**摘要＝system 消息、置于角色红线 system 之后、近期轮之前**）；**合同与相位包永不摘除**（识别面＝结构化，标记键名已定＝`origin`）；**压缩唯一调用点＝调用方（编排面）**；**只作用于模型视图——`state.messages` 零覆盖**；披露账目追加于 `selected_reason` 之后（由调用方合成，本块只返回账目串） |
| specs/context.md:118 | 行为 10 台账投影取得：经 `tools` 公开面、取一次 | 取得路径唯一（经 `tools` 公开面只读——R6；不得直引引擎、不得直连 DB）；「取一次」＝`state.ledger_dump` 非 None 即原样复用（含空投影 `{}`）；空→取得并写回（**本块唯一状态写入面**）；返回为副本（改返回值不改 state） |
| specs/context.md:119 | 行为 11 取得失败＝run 终局失败（fail-fast） | 取得失败（**判据面**＝工具面返回 failed 态 ∪ 调用异常捕获面）→ **run 直接终局失败＋用户面输出稳定错误提示**（失败即收场、不带缺台账的投影续跑）；**Manifest 过程注记留痕义务保留**（不静默吞失败）；**合法空投影与失败不同路**（工具成功返回空 ≠ 失败） |

结构锚：specs/context.md:39–:89 接口定义（**V2 定案签名**——六函数＋常量族，族名单闭世界；卡面 `compile` 不施工）；:91–:95 返回契约／入参纪律／错误契约（渲染器输出恒为 `str` 或 `str`＋元数据、不抛业务错；缺位以**空串段**或**逐字占位文案**两形表达；`compact_messages` 预算内恒原样返回、形态越界抛参数错误）；:97–:105 框架与依赖红线；:124–:129 不降级与静默禁令（**合法降级路径＝无**；截断/压缩必披露三面分工；**本块零静默省略**——不输出省略号形占位）。剩余行（13–18、20、21）的骨架对齐随本票落位、行为断言在 `RT-W3-02b-context.md`。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三——本块无明写归块行，亦无本块侧逐字转抄的归块行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单（该表内明写块名者只有 B1→`bookkeeping`／B2→`orchestration`／B2b→`preconditions`／B4→`gate`，**无一行明写「对应 runtimev2 `context`」**）〕

- 归块注（呈主窗对账，**按实登记「无」**）：§三 表内**无一行明写本块**，本票也**不逐字转抄任何关联行**（§三 各行恰一票逐字转抄——本块侧无新行）。两处相邻面按下述口径登记：
  - B3（「每限额上限/触顶收敛行为钉」，**逐字转抄落 `RT-W1-01b-state.md` 同节**，本票只留指针）：本块的帽/预算**数值单点**（`DEFAULT_MAX_OBSERVATIONS`／`PROCESS_NOTES_BUDGET`）受「数值只引预算表」同一纪律约束，其观测面＝本块行 16（归 `RT-W3-02b-context.md`）；**H8 四限额本体**（触顶收敛／限额键集）归 `state`／`bookkeeping`，本块不承载。
  - B5（帧协议级时序）对本块的处置＝**不归本块**：材料截断 notice 帧归 `specs/answering.md` 发射面＋`specs/transport.md` 帧形闭世界，本块零帧（行 19）——登记呈主窗，本票不冒充覆盖。
- 关联行（落他票，指针）：B1（明写归 `bookkeeping`）逐字转抄与写口侧观测面义务落 `RT-W3-01a-bookkeeping.md` 同节；B4（明写归 `gate`）逐字转抄与专属钉义务落 `RT-W3-03a-gate.md` 同节——本票不重复转抄。
- 本票织网义务＝① 上述两处相邻面的 L1 特征钉（织网工序第 3 步「盲区补钉」，与 W1–W3 施工可并行——eng/04 头注）；②「测试网钉」4 行对应用例落网（pin-08／pin-22 为 P0 承重钉、pin-09 为渲染面披露钉、pin-30 为 compaction 半面钉）；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」13 行逐行实现为 `tests/domains/test_v2_context.py` 用例并全绿，测试标识与规格列逐字一致（`#` 保留规格表行序 1–12、19）；
- 「测试网钉」4 行对应用例在场且绿（pin-08／pin-22 为 P0 承重钉；pin-09 三条落点用例＝行 5／6／19；pin-30 只落 compaction 半面、另半面在他块规格——本票不重复转抄 -02b 的零 pin 行）；「钉落点对读」两行（pin-24／pin-26 不落本块）核实在案；
- 渲染字面逐字迁移零偏离（逐字稿＝`appv2/runtime/context.py` 材料段字面／`appv2/runtime/graph.py` `_render_process_notes`／`tickets/v2/V2-79d-compaction摘要化.md` §1.1／§1.2 摘要头与截数 120——照抄不改，偏离即停）；
- 骨架与族名单落位：六函数签名＋常量族齐（规格 :39–:89，族名单闭世界），返回契约与错误契约在场；-02b 不得另立第二套形状；
- 写入面单点：全块唯一状态写入＝`ledger_dump` 取一次装载；共享写面零写；取得失败＝fail-fast 终局（**合法降级路径＝无**，本票不得引入静默兜底分支）；
- 边界闸 R2／R5／R5b／R6／R7 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W3-02a 完成，产物 `appv2/runtimev2/context/`（骨架＋渲染器族功能行为簇），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
