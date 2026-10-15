# V2 上下文（context）

状态: 已定稿
来源: `specs/modules.md` `## context` 卡、`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §二（定制裁决 6）、`docs/runtime-refactor/walk/判断归责表.md`、`docs/runtime-refactor/recon/K-上下文事件指南预算.md`（context.py 段：R-K-01…R-K-28）、`docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md`（L1278-L1347 档案渲染＋常驻注入；R-B2-01…R-B2-08〔R-B2-09 系安检序、超该区间——引注面注〕）、`docs/runtime-refactor/recon/L2b-作答装配与回声.md`（R-L2b-04）、`docs/runtime-refactor/recon/I2a-状态常量与清单.md`（Manifest 段）、`docs/runtime-refactor/recon/I2b-RunState全字段.md`、`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`（V2-61：A-P4b-32／44…48）、`docs/runtime-refactor/arch/P5b2-票堆V2-79a至79b.md`（A-P5b2-03／04）、`docs/runtime-refactor/arch/P5b3-票堆V2-79c至79d.md`（V2-79c／79d：A-P5b3-02…04／10…17）、`docs/runtime-refactor/arch/P6a-票堆V2-80系列前半.md`（A-P6a-11）、`docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md`（A-P6b-24／29／34）、`docs/runtime-refactor/arch/P7a-交接包与挂账清单.md`（A-P7a-37）、`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md`（H6）、`docs/runtime-refactor/synth/S3-口径裁决清单.md`（D-02）、`docs/runtime-refactor/synth/S5-RunState字段矩阵.md`、`docs/runtime-refactor/eng/04a-应钉行为清单.md`（pin-08／09／22／24／26／30）、`docs/runtime-refactor/research/最佳实践-2a-上下文与工具执行.md`（compaction 隐患）、`docs/runtime-refactor/spec-review/prompts-评审.md`（风险 7④／⑦）、`docs/runtime-refactor/spec-review/state-评审.md`（S-5）、`docs/runtime-refactor/spec-review/parsing-评审.md`（风险 7⑩——知悉）、`specs/state.md`、`specs/answering.md`、`specs/bookkeeping.md`、`specs/prompts.md`、`specs/transport.md`、`tickets/v2/V2-61-材料承载分形渲染.md`（附 A/B/D 逐字稿）、`tickets/v2/V2-80h-对话链追加式架构.md`（compile 退役／compaction 定案）、`appv2/runtime/context.py`（材料渲染逐字稿载体）、`appv2/runtime/graph.py`（过程档案渲染迁移载体）、`appv2/tools/ledger.py`（投影 dump schema 迁移契约）
版式: `docs/spec-format.md`（节标题按该文 §二之二 逐字命名） ｜ 工序: `docs/spec-process.md`
块性: 本块＝**确定性渲染／装载块**（真源 `docs/runtime-refactor/walk/判断归责表.md`）——材料渲染、配额与截断、过程档案有界摘要全部是程序结构判（闭世界映射／排序／计数／截断／字符处理），**零语义判断**（无词表无正则判语义）；凡语义判断（哪支材料有用／答没答上）一律不落本块。

## 目标

把「发给模型的上下文材料」做成**确定性渲染产物＋只读投影装载**——材料段（`[n]` 引标视图）、过程档案（有界摘要段）、台账/名录投影取得（经 `tools` 公开面装载进 `state`）、对话链追加面（追加内容渲染＋超窗 compaction 治理）、每次模型调用的**材料面 Manifest 编译**；**纯渲染与机械处理，零判断**（判断在模型，渲染在程序，互不越位）。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 常驻块的**包裹文本与逐字转抄渲染**（BEGIN/END 包裹＋字典头注＋台账/别名/结构卡三块行渲染）、任务书/答案轮/决策轮指令装配 | `prompts`（本块只装载投影进 `state`，供其从 state 投影渲染） | `specs/prompts.md` 行为 7／8／12 |
| 链上消息的**物理追加**与追加时点、相位包一次性重发判定 | `bookkeeping`（唯一写口 `append_message`／`append_contract`）＋`orchestration`（追加时点） | `specs/bookkeeping.md` 行为 7／8；`specs/agent-loop.md` |
| 材料截断的**通知帧发射**（`material_truncated` notice）与其用户/审计面披露文本 | `answering`（发射行为面）；`transport`（帧形与类型闭世界） | `specs/answering.md` 行为面与验收行；`specs/transport.md` 行为 7 |
| Manifest 的**用量与归因面**记账（token／cached_tokens／alias／caller／run_id） | `bookkeeping.call_model`（本块只编材料面字段；`token_count` 由记账面回填） | `specs/bookkeeping.md` 行为 15 |
| 过程档案的**写入点**截断与只追加（digest 有界） | `bookkeeping.note` | `specs/bookkeeping.md` 行为 10 |
| 黑匣子回放／旧 run 对话通道如实空显 | `persistence`（`pin-30` 另半面） | `specs/persistence.md` 行为 12 |
| 旧检查点的状态字段读入（`dialogue` 兼容字段等） | `state` | `specs/state.md` 行为 8 |
| 材料挑选、工具结果→观察列归一、大结果落引用 | `execution`；`bookkeeping.result_projection` | `specs/execution.md` 行为 4；`specs/bookkeeping.md` 行为 17 |
| 模型调用、限流退避 | `gateway_adapter`（本块**零模型调用**，连该出口都不 import） | `specs/modules.md` `## gateway_adapter` |
| 台账/名录的**结构化判定消费**（前置闸绑定态/口径面、旧名归一、结构核验名录面） | `preconditions`／`tool_matching`／`understanding`（各自经 `tools` 公开面） | `specs/preconditions.md`；`specs/tool_matching.md`；`specs/understanding.md` 行为 5 |
| 指南文本（§A）的**渲染**与合同文本的装载 | 指南**装载**已裁归本块（与台账同形：取一次装载进 state——流水 43⑥，见风险 5）；**渲染**仍归 `prompts`（只读 state 投影渲染；`prompts` 零 IO 不变）；合同文本装载不归本块 | `docs/runtime-refactor/spec-review/prompts-评审.md`（风险 7⑦——装载落点已裁：流水 43⑥；登记见风险 7） |
| 用词表／正则替模型判语义（哪支有用／有没有覆盖） | **不做**——程序只做闭世界映射、排序、计数与字符处理 | `docs/runtime-refactor/walk/判断归责表.md` |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| context | 新增 | 本块本体：投影装载器＋渲染器族（材料段／过程档案／compaction）＋材料面 Manifest 编译 |
| state | 已定稿 | 唯一运行状态依赖（字段形状：`ledger_dump`／`process_notes`／`messages`／`observations`／`Manifest` 十字段）；唯一写面＝`ledger_dump` 取一次装载，其余全只读 |
| tools | 只消费 | 台账/名录投影取得的**唯一世界接触面**（经其公开面；R6）；不改其接口（若确需新增装载面 → 回阶段 2） |

## 接口定义

```python
# ── 卡面初拟形（逐字照录——真源 specs/modules.md `## context` 卡）──
def compile(state: RunState) -> CompiledContext: ...
# 注：卡面为阶段 2 初拟形；V2 定案＝compile 退役为「追加内容渲染器」
#     （真源 docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md A-P6b-24）
#     ——施工以「V2 定案签名」为准；两者差异＝卡级登记件（风险 7①，本规格不改卡）。

# ── V2 定案签名（名单＝本规格自定〔V2 承载位设计〕，逐成员真源见各行注；
#    逐件标【迁移】/【迁移＋显式改动】/【重建】）──
async def load_ledger_dump(state: RunState) -> dict[str, Any]: ...
#   【重建（new-state）】台账/名录投影取得（经 `tools` 公开面只读；**取一次**：
#   state.ledger_dump 非空→原样复用，空→取得并写回 state.ledger_dump；投影形＝
#   `appv2/tools/ledger.py` 模块 docstring 的 dump schema（迁移契约）；真源
#   docs/runtime-refactor/eng/00-阶段2-模块划分草案.md §二 定制裁决 6（常驻注入走工具门）
#   ＋ docs/runtime-refactor/synth/S5-RunState字段矩阵.md ledger_dump 行（写手 H6／M2——
#   统一后唯一写手＝H6））
def render_materials(observations: list[dict[str, Any]], *,
                     max_observations: int) -> tuple[str, dict[str, Any]]: ...
#   【迁移】材料段 [n] 渲染＋截断元数据（逐字迁移——现状载体 appv2/runtime/context.py；
#   真源 docs/runtime-refactor/recon/K-上下文事件指南预算.md R-K-18…R-K-26；行为 1–6）
def render_process_notes(state: RunState, *, budget: int) -> str: ...
#   【迁移＋显式改动】过程档案有界摘要段（逐字迁移——现状载体 appv2/runtime/graph.py
#   `_render_process_notes`；显式改动＝下划线去前缀、budget 转显式注入参〔无缺省裸字面——
#   值＝常量 PROCESS_NOTES_BUDGET〕；真源 docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md
#   R-B2-01…R-B2-04；行为 8）
def compile_manifest(observations: list[dict[str, Any]], *, step: str,
                     max_observations: int,
                     ledger_dump: dict[str, Any] | None = None,
                     token_count: int = 0) -> "Manifest": ...
#   【重建】材料面 Manifest 编译（V1 生产面已退役、本块重建靠 specs/answering.md 行为 4 承接；
#   `step`＝本调用步名（V1 为相位名字面；取值面随步记录面登记）；`ledger_dump` 非 None＝
#   本调用投入常驻块（→附三来源行）、None＝无；字段形状真源 specs/state.md 接口定义；
#   selected_reason 逐字稿真源 tickets/v2/V2-61-材料承载分形渲染.md 附 A；行为 6／7）
def compact_messages(messages: Sequence[Mapping[str, str]], *,
                     dialogue_view_tokens: int) -> tuple[list[dict[str, str]], str]: ...
#   【重建（依票面重落——无现状载体：compaction 族已随 V2-80h 退役）】超窗 compaction
#   （模型视图＋披露账目；触发参数 dialogue_view_tokens 注入制、无裸值；逐字稿载体＝
#   tickets/v2/V2-79d-compaction摘要化.md §1.1/§1.2＋docs/runtime-refactor/arch/P5b3-票堆V2-79c至79d.md
#   A-P5b3-13/15/17；行为 9）
def trust_of(observation: dict[str, Any]) -> str: ...
#   【迁移】信任级判定单点（只读 locator.kind 查表；真源 recon/K R-K-15…R-K-17；行为 2）
# 注：A-P6b-24 点名的另一渲染器 render_task_book（理解任务书）归 prompts
#     （其 assemble_task_book）——不在本名单。
# ── 常量族（名单闭世界；数值不落本规格）──
# DEFAULT_MAX_OBSERVATIONS（检索片段帽单点——数值真源 recon/K R-K-07；行为 4／12）
# PROCESS_NOTES_BUDGET（过程档案预算单点——数值真源 recon/B2 `_PROCESS_NOTES_BUDGET`；行为 8）
# TRUST_AGG／TRUST_LEDGER／TRUST_REPORT（三档信任级字符串＋排序映射——真源 R-K-01…R-K-06）
# RESIDENT_SOURCE_ROWS（三来源行三元组映射：`ledger_dump`→`ledger_full_dump`／`alias_dump`→
#   `ledger_aliases`／`schema_card`→`schema_cards`——**唯一映射点**〔两编码面各一面、同源
#   dump schema〕；真源 recon/B2 R-B2-05；行为 7）
```

- **族名单是闭世界**：上列成员（六函数＋常量族）之外新增公开成员＝只许以「新增成员入名单＋同批对账消费方规格（`specs/answering.md`／`specs/prompts.md`／`specs/agent-loop.md`）」方式进块；消费方在相位块内私建同形副本（自写材料渲染／摘段循环／信任映射）＝判失败（单点纪律，先例 `specs/parsing.md` 共用件单点）。**实名与参形以本规格「V2 定案签名」为准**（卡面 `compile` 为初拟形、不施工——卡级登记见风险 7①）；本规格锁名单闭世界与输入输出口径。
- **返回契约**：渲染器输出恒为 `str`（或 `str`＋元数据）——不抛业务错；缺位以**空串段**（调用方跳过——真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-32，同族先例〔主语系样例渲染器〕）或**逐字占位文案**（行为 1／8）两形表达；`load_ledger_dump` 失败→ run 终局失败（行为 11——fail-fast，Owner 流水 44，不走空投影续跑）。
- **入参纪律**：渲染函数消费 state 投影字段（字段面以 `docs/runtime-refactor/synth/S5-RunState字段矩阵.md` 为界，只读）＋调用方注入的参量（材料集、帽、预算、视窗）；**时间量不经本块**（零时钟接触）；帽、预算与视窗为**注入参数、无缺省裸字面**（数值单点＝常量族 `DEFAULT_MAX_OBSERVATIONS`／`PROCESS_NOTES_BUDGET`／视窗登记——行为 4／8／9）。
- **错误契约**：`compile_manifest` 的 `token_count` 缺省 0（记账面回填）；`compact_messages` 预算内**恒原样返回**（零漂移、不抛错）；形态越界（如 `dialogue_view_tokens` 非法）→ 抛参数错误，不吞错；`index` 缺失／非整数形（观察面形态违约）→ 抛参数错误（V1 裸 `KeyError` 收口——差异声明）。
- 真源：`specs/modules.md` `## context` 卡（参数名与常量实名以卡为准；**族与签名以本规格「V2 定案签名」为准**——卡面 `compile` 不施工，卡面与 V2 定案差异见风险 7①）。

## 框架与依赖红线

- **无点名框架**（本块不引入任何框架；纯字符串与字典处理）。验收写法：依赖锁文件不出现框架包＋行为测试绿。对应闸：**R5b 契约**。
- **只经 `tools` 公开面接触世界**（台账/名录投影取得唯一路径；禁直引 `knowledge`／`query`／`retrieval` 引擎、禁直连 DB）。对应闸：**R6 契约**（`tools/importlinter_v2.toml` 的 source 含 `appv2.runtimev2.context`）。
- **不引旧码**（`appv2.runtime.*`——本块「迁移照抄」是把旧码字面搬进新块、不是 import 旧模块）。对应闸：**R5 契约**。
- **不直引 `appv2.infra.llm_client`**＝**R7 契约**；**零模型调用**（连 `gateway_adapter` 都不 import）——该面由 AST 测试 `::imports_and_write_ports_scan` 承载。**诚实声明**：R1–R8 无「禁引 `gateway_adapter` 于 context」专属闸（R4 的 source 只含 `state`、R8 只列三个零 LLM 相位）。
- **依赖白名单＝`state`＋`tools` 两块**（卡面依赖行）：禁引其余 runtimev2 块。对应闸：**无该面的专属闸 → 人审**（原因：R1–R8 无「context 依赖白名单」一面）；降维＝AST 断言（`::imports_and_write_ports_scan` 的 import 白名单面）。
- **写入面单点**：全块唯一状态写入＝`load_ledger_dump` 对 `state.ledger_dump` 的取一次装载；`messages`／`steps`／`notices`／`process_notes`／`dialogue`／`next_intent` 等共享写面**零写**（写口归 `bookkeeping`，其行为 1）。对应闸：**无专属闸 → 人审**＋AST 断言（`::imports_and_write_ports_scan` 的写面扫描）。
- **禁手写替代（渲染单点）**：材料段渲染／过程档案渲染／信任映射／帽常量／三来源行映射（`RESIDENT_SOURCE_ROWS`）在 runtimev2 面内各恰一处定义（禁相位块另存副本——V1 病灶先例：渲染函数与消费点分居两文件，真源 `docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md`）。验收写法：runtimev2 面内唯一定义点断言（`::renderers_single_source`）。

## 行为约定

1. **材料段渲染形逐字迁移**（承载位换、文本不变——真源 `docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md` A-P6b-24／A-P6b-34）：文本以段头起（逐字稿载体＝现状 `appv2/runtime/context.py`：`"\n观察材料：\n"`）；块形＝`[{index}]（{label}）{content}`——`index`＝观察自带全局序号（非渲染位次）、`label`＝非空段以全角「｜」连接、段序 `信任级｜来源｜井`（空段跳过；**来源/井两段经 `.strip()` 归一后判空**〔空白串→空段跳过——现状载体逐字含 strip〕；三段全空＝空括号 `（）`——现状固有、迁移不修）；`content` 缺失＝空串（现状缺省——真源 R-K-20）；空材料集正文＝逐字「（无）」（真源 `docs/runtime-refactor/recon/K-上下文事件指南预算.md` R-K-18／R-K-19／R-K-20／R-K-25；V2-64 出处形＝`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-69）。断言：四类 fixture（常规／多段标签／空段／空材料）逐字比对；`index` 与观察序号一致。
2. **信任级映射闭世界＋notice 排除**：`trust_of` 判定路径唯一（只读 `locator.kind`，`str()` 归一后查表；缺 `locator`／缺 `kind`／未知 kind 统一落 `report`——不抛错）；映射闭世界＝十 kind 三族（权威：`agg_row`／`lineage`；台账：`metric`／`term`／`object`／`relation`／`family_annotation`；检索：`fragment`／`graph`；`notice` 名义入表但材料段整体排除——不进模型面、不计任何计数）（真源 R-K-03／R-K-15…R-K-17）。断言：十 kind 各落对；三种异常输入落 `report`；notice 条目不在渲染文本、不计计数。
3. **排序＝信任级稳定序**：`authoritative`＜`ledger`＜`report`（rank 0／1／2，同 rank 保持入栈序、稳定排序）；两跑逐字相等（确定性不抖动——真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-48〔V2-61 事实面〕；R-K-05 排序键面；未登记信任级排序兜底〔现状不可达——notice 已前置排除〕迁移照抄、无行为面）。断言：乱序入栈 fixture → 输出按档聚簇且组内原序；两跑逐字相等。
4. **分承载体预算（分形帽）**：权威/台账族（信任级非 `report`）**恒全量渲染、不设支数帽**（引擎侧已封顶、装配不重复封顶——真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-44）；检索族（`report`）超帽才截断（**帽只作用检索族**）；帽值经注入参数（`render_materials` 的 `max_observations`），**数值单点＝本块常量 `DEFAULT_MAX_OBSERVATIONS`**（真源 `docs/runtime-refactor/recon/K-上下文事件指南预算.md` R-K-07；具体值不落本规格）。**与 walk §13-B／§14-B 的分工**：单支超阈「落引用」归 `execution`（`specs/execution.md` 行为 4 已收口）；本块检索族支数帽＝token 安全面存续（V2-61 设计），与「渲染帽裁剪」不同物。断言：权威族超帽 fixture → 全渲染、零披露、`material_truncated=False`；检索族超帽 → 只渲染帽内支、披露在场。
5. **截断必披露（模型面披露行逐字）**：检索族截断时材料段尾接披露行——逐字稿载体＝现状 `appv2/runtime/context.py`（「（材料披露：检索片段共 {检索支数} 支，本轮渲染前 {实渲支数} 支——未渲染片段不在本轮视野，不得对其断言；权威行集与台账卡已全量渲染。）」；行为真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-45／A-P4b-46）；未截断样本零披露行（零残留）。断言：两态各落对、披露行逐字（两个计数与元数据一致）；未截断输出对披露特征子串零命中。
6. **Manifest 三机检字段与 `selected_reason`**：`material_truncated` ⇔ 检索族截断（未截断恒 False）；`material_rendered`＝权威/台账族支数＋实渲检索支数；`material_total`＝排除 notice 后材料总数；**零材料步＝(0, 0, False)**（真源 A-P4b-47）；`selected_reason` 按逐字形拼装——逐字稿载体＝`tickets/v2/V2-61-材料承载分形渲染.md` 附 A（带材料两形：「步骤 {step}：信任级降序稳定排序；权威 {A} 支全量；」＋截断形「检索片段帽 {帽} 支截断（{M}/{R}）」／未截断形「检索片段 {R} 支全量」＋「（合计入选 {K}/{总}）」；**零材料步形**＝「步骤 {step}：理解步零材料渲染」（迁移照抄）——`{step}` 为**步号槽**、文案恒为「理解步」（**零材料步仅生于理解步**）（2026-10-16 收词）；**槽位归一表**：{A}＝权威/台账支数、{R}＝检索支数、{M}＝实渲检索支数（＝min(检索支数, 帽)）、{帽}、{K}＝合计数、{总}＝材料总数——附 A 载体系代码表达式，本规格归一为槽名〔转写声明见风险 8〕；常驻注入后缀（V1「；词典层常驻注入 {n} 块（ledger_dump 族——第 1 轮全量，非懒加载：注入不依赖未命中）」）的 V2 适配〔相位一次性口头〕＝登记〔风险 8 扩面〕）。断言：四态 fixture（零材料／全量／检索截断／权威超帽）三字段逐条对；`selected_reason` 逐字比对（**无 compaction 态逐字**——超窗态按行为 9 合成规则〔追加〕比对）。
7. **每次模型调用都有 Manifest 且材料标来源**：材料面 Manifest 由本块编译、随步落地（缺位＝判失败——`specs/answering.md` 行为 4 的同源要求）；`source_type`／`source_id`／`version`／`trust_level` 四列表**逐条对应同一来源序列（等长）**——来源序列＝**本调用实投材料逐支（实渲支）**＋**当轮投入常驻块时**其三块来源行（decision／clarify／toolmatch 首入恰 3 行、answer 轮零常驻行；notice 不计；三元组映射唯一落点＝本块常量 `RESIDENT_SOURCE_ROWS`，对字真源 `docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md` R-B2-05；现状无消费者〔D-B2-09〕——本块重建该记账面）；`transform` 取形状缺省（真源 `specs/state.md` 接口定义）。断言：常规 fixture → 四列表等长、每条材料 `source_id` 与观察 `source_id` 逐字对应（**空串如实**——图谱无锚边形 V1 事实面）、按呼叫分型（decision／clarify／toolmatch 首入**且投影非空时**恰 3 常驻来源行、answer 轮零常驻行）；**零材料步 → 三机检字段 0/0/False**；**台账空投影 → 零台账来源行且材料字段不受影响**；**截断态 → 来源行只含实渲支**；`as_dict` 全键恒出（十键）。
8. **过程档案摘要段有界（逐字迁移）**：零档案＝零段（返回空串——调用方跳过，首轮零噪声）；头注逐字「【本 run 已做（过程档案摘要——防重参考，不是作答材料）】」；条目行形 `- [{phase}] {title}｜{digest}`（`phase` 缺失＝`?`、`title`／`digest` 缺失＝空串——现状缺省回落，迁移照抄）；预算含头注起算、逐条累加、超即止（有界值＝**注入参数 `budget`〔无缺省〕、数值单点＝常量 `PROCESS_NOTES_BUDGET`**——真源 `docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md` `_PROCESS_NOTES_BUDGET`／`_PROCESS_NOTES_HEADER`；具体值不落本规格）；超预算追加披露行（条数前后账——逐字「-（过程档案摘要有界截断——已渲染 {n}/{N} 条）」）并停止（披露行免预算复检——现状固有，源疑点 D-B2-07 如实登记）；**段永不作对话轮**（只作当前指令的材料片段，由调用方拼接；`specs/prompts.md` 行为 16⑤ 只接其渲染产物入参）。断言：零档案 → `""`；超长 fixture → 披露行逐字、n 与已渲行数一致；完整 fixture → 全行、零披露行；两跑逐字相等。
9. **超窗 compaction＝模型视图压缩（`pin-30` 半面；依票面重落——无现状载体：compaction 族已随 V2-80h 退役）**：messages 总量超视窗（触发参数 `dialogue_view_tokens` **注入制、无裸值**；数值已裁 8k 档（流水 43④——风险 4）＋承载位已定＝`RunState` 独立字段 `dialogue_view_tokens`（流水 46①／49，S5 定稿字段行——风险 4 销）→ 自尾向前保留近期轮（**保留窗保证三条**（2026-10-16 收词：原文「三语」系笔误——该条列三条保证，与语言无关）：保留窗自尾向前累积、**至少 1 轮——最新轮恒在场，哪怕单轮超预算**；**单轮独占预算（巨轮）＝原样放行零压缩**——真源 `docs/runtime-refactor/arch/P5b3-票堆V2-79c至79d.md` A-P5b3-14／A-P5b3-19）；最旧「对话轮对」（user＋assistant）摘要化（**摘要＝system 消息、置于角色红线 system 之后、近期轮之前**——真源 A-P5b3-15）；**合同与相位包永不摘除**（识别面＝**结构化**——标记随 `messages` 条目字段携带（**键名已定＝`origin`**——与 `dialogue` 条目 `{role, content, origin}` 同词表，流水 49③），或由调用方以链位贡献表随调用传入；**参形随风险 4 落点裁定后入签名**〔登记〕；本块不采内容子串识别）；**压缩唯一调用点＝调用方（编排面）**——`bookkeeping.call_model` 无此面、各相位不得自压缩；摘要形逐字（**依票面重落**——逐字稿载体 `tickets/v2/V2-79d-compaction摘要化.md` §1.1/§1.2：摘要头逐字「（前情摘要——旧轮原文已压缩，完整原史在会话档案可查）」＋「问：{问句原文截 120}」「答：{答首行截 120}」行——截数 120 有真源 A-P5b3-13）；**只作用于模型视图——`state.messages` 零覆盖**（只压不删、原史全量在 checkpoint 可查——真源 A-P5b3-12）；**compaction 触发＝前缀延伸／缓存命中的显式例外**（真源 `docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md` A-P6b-29「触发即断缓存」；留痕前缀断言按此豁免——对账 `specs/agent-loop.md` 断言面）；披露账目（轮数前后账＋原史可查注记）**追加于材料面 `selected_reason` 之后（分隔「；」）——由调用方（编排面）在合成最终 Manifest 时执行（同 `token_count` 回填先例；本块 `compact_messages` 只返回账目串）**（合成规则——真源 A-P5b3-17 追加形态；预算槽随数值裁定收口）；预算内**原样返回、披露为空**（零漂移）。断言：超窗 fixture → 视图＝system 摘要（置位对）＋保留近轮逐字、**最新轮单轮超预算仍恒在场**、**单巨轮视图＝入参逐字**、合同/相位包条全数保留、`state.messages` 深比较不变、披露账目在场（合成位对）；预算内 → 视图与入参逐字相等、披露为空串；无 compaction 态 → 行为 6 逐字比对不涉合成。
10. **台账投影取得：经 `tools` 公开面、取一次**：取得路径唯一（经 `tools` 公开面只读——R6；不得直引引擎、不得直连 DB）；「取一次」＝`state.ledger_dump` **非 None 即原样复用**（含空投影 `{}`＝已取之空态、不再取；`None`＝未取得→取；快照随 checkpoint 走、后继轮复用——取一次语义真源 `docs/runtime-refactor/recon/I2b-RunState全字段.md` `ledger_dump` 字段注「第 1 次澄清入口从 ledger_dump 缝取一次」＋`docs/runtime-refactor/synth/S5-RunState字段矩阵.md`）；空→取得并写回 `state.ledger_dump`（**本块唯一状态写入面**）；返回为副本（改返回值不改 state）；消费面（`prompts` 常驻块渲染）只读 `state` 投影渲染（真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-34「台账全量块（下方注入）」措辞面〔A-P4b-33 系消歧头随动条〕＋`docs/runtime-refactor/synth/S5-RunState字段矩阵.md` §四【结构-1】：三种持久化行为重写须统一〔**统一形「取一次装载」＝本规格定**〕；S5 行载 H6／M2 两写手——统一后唯一写手＝H6）。断言：state 已有 dump → 零工具调用、原样返回；空 state → 恰一次取得＋写回；改写返回值 → state 深比较不变。
11. **取得失败＝run 终局失败（fail-fast——Owner 流水 44 翻案：原「如实空投影不炸链」裁决〔流水 43③〕否决）**：台账/名录投影取得失败（**「失败」判据面不变＝工具面返回 failed 态 ∪ 调用异常捕获面**——判据即此定死；loader 的 tools 装载入口形仍随风险 5——「阶段 5 施工票前置核定——流水 43⑥」）→ **run 直接终局失败＋用户面输出稳定错误提示**（失败即收场、不带缺台账的投影续跑；三态收口归编排面——真源 `specs/agent-loop.md` 行为 8 三态落库；翻案理由＝辅助材料失败硬撑会产出缺材料的低质答案，宁可诚实报错）；**Manifest 过程注记留痕义务保留**（失败事实记过程档案——机读披露，A-P7a-37 同族诚实纪律，不静默吞失败）；用户面帧面走 `transport` 既有失败腿规格（`run_failed` notice＋正常 `done`；`error` 帧仅流级〔帧通路自身异常〕——真源 `specs/transport.md` 行为 9＋不降级节）；本块零编造（不冒充已取得；锚＝总纪律「业务事实零发明」；**合法空投影与失败不同路**——工具成功返回空 ≠ 失败，成功路径原样〔行为 10 空投影＝已取之空态〕）。断言：工具 failed fixture → run 终局失败态、用户面稳定错误提示在场、Manifest 过程注记含失败留痕（机读可查）；合法空结果 fixture → 行为 10 原样取得＋写回（不触发失败腿）。
12. **渲染器族纯函数确定性＋IO 面单点**：`render_materials`／`render_process_notes`／`compile_manifest`／`compact_messages`／`trust_of` 同入参两跑逐字相等（或深比较相等）、**调用前后入参深比较相等**（零写入）；零 IO、零模型调用、零时钟读取、零随机、零事件发射；**唯一 IO 面＝`load_ledger_dump` 的 tools 调用**。断言：两跑相等＋入参深比较＋AST 扫描零命中（模型/时钟/随机/emit/DB/文件）。
13. **程序不判语义**：本块全部判定＝闭世界查表／排序／计数／截断／字符串归一／字符截取——零词表零正则语义判定；豁免面＝形态处理（集合成员判定、字符串归一、字符截取）。断言：`::no_lexicon_or_regex_in_context` 绿＋判定清单逐条可指真源条目（真源 `docs/runtime-refactor/walk/判断归责表.md`）。
14. **本块零合同零指令**：不定义、不复制合同常量文本与指令骨架（材料段/过程段是唯一文本产物面）；相位包组成（合同＋样例＋§A＋常驻块包裹）与重发判定均不落本块（`specs/prompts.md` 行为 7／8＋`specs/bookkeeping.md` 行为 8）。断言：合同六族特征子串在本块源码零命中（扫描范围对偶于 `specs/prompts.md` 行为 1）。

## 不降级与静默禁令

- **合法降级路径：无**——台账投影取得失败＝fail-fast 终局失败（行为 11，Owner 流水 44——失败即诚实收场，非降级）；其余**无降级**（材料渲染不删段、不改写、不缩措辞、不冒充）。
- **截断/压缩必披露（机读信号三面分工）**：(a) 模型面——材料披露行（行为 5）／compaction 摘要头（行为 9）逐字在场；(b) 机读字段——`material_total`／`material_rendered`／`material_truncated`＋`selected_reason` 帽账（行为 6）／compaction 披露账目（行为 9）／台账装载失败留痕（行为 11）；(c) 用户/审计面 `material_truncated` notice＝**发射方义务**（`specs/answering.md` 行为面／`specs/transport.md` 帧面），本块零帧、不冒充覆盖。断言：截断 fixture → (a)(b) 在场；AST 扫描本块零 `emit`。
- **本块零静默省略**：不输出省略号形占位；一切有界处理（帽/预算/视窗）均以披露行或披露账目显式表达。
- 红线原文：`docs/runtime-refactor/arch/P7a-交接包与挂账清单.md`（A-P7a-37）「红线——不许静默：任何相位仍发生截断，模型面必须随材料段带明示「（材料仅渲染 N/M 支）」，收口注记面同步披露（对齐 V2-53「注入不进交付面」诚实纪律）」〔注：其中「（材料仅渲染 N/M 支）」为示意形——操作形以行为 5 锁定稿为准〕。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 材料段渲染形逐字迁移（段头／块形／空段空括号／空材料「（无）」） | `tests/domains/test_v2_context.py::material_segment_verbatim_render` |
| 信任级映射闭世界（十 kind 三族；异常输入落 `report`；notice 排除） | `tests/domains/test_v2_context.py::trust_mapping_closed_world` |
| 排序＝信任级稳定序（同 rank 保持入栈序；两跑同序） | `tests/domains/test_v2_context.py::trust_order_stable` |
| 分承载体预算：权威/台账族全量无帽、检索族超帽才截断 | `tests/domains/test_v2_context.py::carrier_fractal_budget` |
| 截断披露行逐字在场（两计数正确）；未截断零残留 | `tests/domains/test_v2_context.py::truncation_disclosure_line_verbatim` |
| Manifest 三机检字段（四态）＋`selected_reason` 逐字形 | `tests/domains/test_v2_context.py::manifest_material_fields_and_reason` |
| 每次调用 Manifest 在场（零材料亦在）且材料标来源（四列表同长；常驻来源行按呼叫分型） | `tests/domains/test_v2_context.py::manifest_present_source_rows` |
| 过程档案摘要段：零档案零段／有界／披露行逐字／全入预算无披露 | `tests/domains/test_v2_context.py::process_notes_bounded_summary` |
| compaction：超窗视图（system 摘要置位＋最新轮恒在场＋单巨轮零压缩＋合同/相位包不摘＋原史零覆盖＋披露账目追加合成） | `tests/domains/test_v2_context.py::compaction_overwindow_model_view` |
| compaction：预算内原样返回、披露为空（零漂移） | `tests/domains/test_v2_context.py::compaction_within_budget_no_drift` |
| 投影取得：经 tools 公开面、取一次（已有投影〔含空投影〕零工具调用）；返回值副本语义 | `tests/domains/test_v2_context.py::ledger_load_via_tools_take_once` |
| 取得失败＝run 终局失败＋用户面稳定错误提示在场＋Manifest 过程注记留痕可查（合法空结果不触发失败腿） | `tests/domains/test_v2_context.py::ledger_load_failure_run_failed_honest` |
| 渲染器族纯函数确定性：两跑相等、入参深比较不变、零 IO/模型/时钟/随机/emit（AST） | `tests/domains/test_v2_context.py::renderers_pure_deterministic` |
| import 白名单（只 `state`＋`tools`）＋写面唯一（`ledger_dump`）＋零帧（AST 扫描） | `tests/domains/test_v2_context.py::imports_and_write_ports_scan` |
| 程序侧无词表／正则语义判断（AST；豁免面＝形态处理） | `tests/domains/test_v2_context.py::no_lexicon_or_regex_in_context` |
| 帽/预算常量单点（`DEFAULT_MAX_OBSERVATIONS`／`PROCESS_NOTES_BUDGET` 各一处、注入制无缺省裸字面） | `tests/domains/test_v2_context.py::cap_constant_single_point` |
| 渲染单点：材料/过程档/信任映射/帽/三来源行映射（`RESIDENT_SOURCE_ROWS`）在 runtimev2 面内各恰一处定义（消费方零副本） | `tests/domains/test_v2_context.py::renderers_single_source` |
| 本块零合同字面（六族特征子串零命中） | `tests/domains/test_v2_context.py::no_contract_literals_in_context` |
| 截断机读信号两面在场（披露行＋字段）；本块零 emit（帧面归发射方） | `tests/domains/test_v2_context.py::truncation_signal_no_emit` |
| 【边界集】空材料／全 notice／权威超帽／检索超帽／超长档案／超窗链 → 各落空段、全量、披露、摘要各分支 | `tests/domains/test_v2_context.py::boundary_empty_overcap_overwindow` |
| 【保留集】常规材料渲染与常规档案（无截断、预算内）输出逐字不变；既有 `[n]` 序号与排序行为不因本批改形回归 | `tests/domains/test_v2_context.py::retention_normal_render_unchanged` |

> **测试文件归属**：本块验收测试绑**新建** `tests/domains/test_v2_context.py`（`context` 是阶段 2 新划的公共层块 `appv2/runtimev2/context/`；`ls tests/domains/` 实测无同名文件，无冲突）；旧承载位既有测试（如 `tests/domains/test_v2_v61_material_rendering.py`）随阶段 5 迁移重写收口（本批不改）；fixture＝材料集／投影集／状态工厂（卡面 Adapter：fixture 材料集）。全部测试标识＝**待织网（阶段 5）**。

## 依赖与风险

- 依赖：`state`（字段形状＋`Manifest` 十字段＋常量；唯一写面＝`ledger_dump` 取一次装载）｜`tools`（台账/名录投影取得的唯一接触面——经公开面，R6）；消费方＝`answering`（材料段＋Manifest）、决策轮装配（过程档案段文本——`specs/prompts.md` 行为 16⑤）、`orchestration`（装载时点与追加编排）；真源＝`specs/modules.md` `## context` 卡。
- 风险与对策（每条带检测手段）：
  1. **卡与规格分叉（compile→渲染器族）**：卡面 `compile(state) -> CompiledContext` 为阶段 2 初拟形，V2 定案＝compile 退役（`docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md` A-P6b-24）。**登记件**（卡级，只登记不改卡，交主窗回阶段 2；含现状 `ContextBuilder` 配置载体的去留）。检测手段＝**人审**（评审工序＋卡级登记见风险 7①）。
  2. **卡「术语表常驻注入」与常驻块渲染归 prompts 两说**（打分界：**取得归本块、包裹与逐字转抄渲染归 prompts**——`docs/runtime-refactor/spec-review/prompts-评审.md` P-07 建议卡改述「台账/名录投影取得〔经 tools 公开面装载进 state〕」）。检测手段＝**人审**（阶段 7 接口契约对账）＋`::ledger_load_via_tools_take_once`。
  3. **截断帽分值口径未统一**（`docs/runtime-refactor/synth/S3-口径裁决清单.md` D-02：24/47、24/51、24/88 三说属**分母**未统一——**已裁（流水 43⑤）：分母＝该题排除 notice 后候选观察支总数（与行为 6 `material_total` 同口径）**；本块帽**只作用检索族**、帽值本身不变——分母口径随裁收口）。检测手段＝`::carrier_fractal_budget` ＋ **人审**（S3 D-02 留档）。
  4. **compaction 两说＋触发参数无承载位**：设计面 `docs/runtime-refactor/arch/P6b-票堆V2-80系列后半.md` A-P6b-29 记「机制保留（改作用于 messages 链）」、实现讯息／`docs/runtime-refactor/arch/P5b1-对话状态重构方案.md` A-P5b1-09 记「已退役（现状码面无该函数）」；数值两说（A-P5b3-11「4000 tokens」vs `docs/runtime-refactor/arch/P6a-票堆V2-80系列前半.md` A-P6a-11「超视窗（8k tokens 档）」）——**已裁（流水 43④）：8k 档**（A-P6a-11「最后手段」口径；A-P5b3-11「4000 tokens」系已退役票面定案值、23 场景实测从未触发；常量阶段 5 落 8192、披露文案随改）；`state` 的 `Budget` 键集闭世界无该键；**触发参数已随真源口径更名 `dialogue_view_tokens`**（A-P6b-29／A-P5b3-11）＋**识别面落点**（结构化——链位贡献表／链条目标记，参形随落点入签名；真源 A-P6b-29「合同与相位包永不摘除」）＋**触发＝前缀延伸显式例外**（A-P6b-29，对账 `specs/agent-loop.md` 断言面）。**本规格按 A-P6b-29 落设计、触发参数注入制**；承载位登记（风险 7②——数值已裁随上），变更须走规格变更。检测手段＝`::compaction_overwindow_model_view`／`::compaction_within_budget_no_drift` ＋ **人审**。
  5. **loader 的 tools 公开面调用形未落定**（哪一工具/参形——`tools` 规格为旧版式；设计口径＝「走工具门」，真源 `docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §二 定制裁决 6）——**已裁（流水 43⑥）：大面维持原裁**（context 经 `tools` 装载）；tools 装载入口形＝**阶段 5 context 施工票前置核定——流水 43⑥**（`tools` 规格旧版式、现在定不出真形）；GuideProvider 指南装载＝**与台账同形：本块取一次装载进 state、prompts 只读渲染（流水 43⑥）**（指南装载器入族随阶段 5 施工票——族名单闭世界扩员须同批对账；「不做什么」指南行已随裁改述）。检测手段＝**人审**（阶段 5／阶段 7 对账）＋`::imports_and_write_ports_scan`（AST——经 `tools` 包根取得）。
  6. **compaction 若真触发需配完整治理链**（Commit→Compact→Rebuild→Validate——`docs/runtime-refactor/research/最佳实践-2a-上下文与工具执行.md` 所记隐患；本仓 run 内轮数上限与总时长为有界终止面（数值真源＝`docs/runtime-refactor/recon/K-上下文事件指南预算.md` R-K-72…R-K-74），run 内膨胀有限）。对策＝机制落为最后手段（A-P6b-29 语义）；检测手段＝**人审**（Q16 后按证据另批）。
  7. **跨规格债与卡级登记清单（本批只登记、不代办——单写者纪律，交主窗统一回提）**：①`specs/modules.md` `## context` 卡：`compile` 签名初拟形标注＋职责「术语表常驻注入」改述（prompts-评审 P-07 建议）＋`ContextBuilder` 去留（销项＝阶段 7）＋职责「对话链追加」改述（**卡级清单第 4 项**；与 `## bookkeeping` 卡职责行双载——P-16①）＋族名单权威注「公开面以本规格『V2 定案签名』为准（族名单闭世界）」（**卡级清单第 5 项**——P-16②）；②compaction 半面登记（`docs/runtime-refactor/spec-review/state-评审.md` S-5 指「待 context 规格定稿时登记」——已登记：`pin-30` 后半面在 `specs/state.md` 行为 8／`specs/persistence.md` 行为 12，**本块落 compaction 半面＝行为 9**）——**已裁（流水 46①）：承载位＝`RunState` 独立字段 `dialogue_view_tokens`**（非 Budget 键——compaction 是对话视窗机制非轮预算；注入制由编排面注入；数值 8k 档真源 A-P6a-11）；③`GuideProvider` 装载实现落点（prompts-评审 风险 7⑦）——**已裁（流水 43⑥）：指南装载与台账同形归本块**（本块装载面由只含台账/名录投影扩及指南取得面，见风险 5）；④`specs/answering.md` 行为 4「Manifest 的编译归 context」——本规格 `compile_manifest` 承接（其引用可用）；⑤`docs/runtime-refactor/spec-review/parsing-评审.md` 风险 7⑩（understanding 回认）——知悉，与本块无涉；⑥S3 D-02 帽分母已裁（流水 43⑤——风险 3）；⑦`tickets/v2/V2-61-材料承载分形渲染.md` 附 A 段头形（`"\n\n观察材料：\n"`）与 80h 迁移后现状（`"\n观察材料：\n"`）的差异——本块以**现状代码字面**为迁移逐字稿（承载位换、文本不变），差异点登记（风险 8）；⑧`pin-24` 消费侧重发判定落 `orchestration`（追加编排）＋标记写入落 `bookkeeping.append_contract`——`specs/agent-loop.md` 挂钩表已补 `pin-24` 行（流水 43⑦c，本批回提销项）；⑨**`render_task_book` 落点**（A-P6b-24 点名的另一渲染器——归 `prompts` 其 `assemble_task_book`；落点登记，P-26）；⑩**`specs/agent-loop.md` 行为 2 两说**——已回提改述（流水 43⑦c：行为 2 改「每步在 `messages` 整链续写」、compile 已退役，P-29 销项）；⑪**`specs/execution.md` 挂钩表已补 `pin-08` 行**（流水 43⑦b，本批回提销项，P-24；其行为 4 载同一规则）。检测手段＝**人审**（主窗回提＋阶段 7 接口契约对账）。
  8. **迁移文本两载体差异面**：材料段逐字稿取现状 `appv2/runtime/context.py`（80h 承载位形），V2-61 附 A 为拼接位形——两处文本同一行为的两个承载位，施工以现状代码为准；若裁定以票面附 A 为准＝规格变更；**槽位归一表**（附 A 载体系代码表达式→`{A}`／`{R}`／`{帽}`／`{K}`／`{总}` 槽名——转写声明，P-18）；`render_process_notes` 显式改动清单（去 `budget` **缺省值**改注入制〔形参保留〕、去下划线前缀）；零材料步文案已补；常驻注入后缀 V2 适配（相位一次性口头）＝登记（P-08）。检测手段＝**人审**＋`::material_segment_verbatim_render`。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 不引框架 | 边界闸 **R5b** | 已真跑（`tools/importlinter_v2.toml`） |
| 只经 `tools` 接触引擎（禁直引 knowledge/query/retrieval） | 边界闸 **R6**（source 含 `appv2.runtimev2.context`） | 已真跑 |
| 不直引 `appv2.infra.llm_client` | 边界闸 **R7** | 已真跑 |
| 不引旧码（`appv2.runtime.*`） | 边界闸 **R5**（source＝`appv2.runtimev2` 全体） | 已真跑 |
| 消费方（业务相位）只经包根取本块（禁深层子模块） | 边界闸 **R2**（forbidden 含 `appv2.runtimev2.context.*`） | 已真跑 |
| 零模型调用（连 `gateway_adapter` 都不 import） | 测试 `::imports_and_write_ports_scan`（AST） | 待实现（阶段 5）；**诚实声明**：R1–R8 无此专属闸（R4 只源 `state`、R8 只列三相位） |
| 依赖白名单＝`state`＋`tools`（禁引其余 runtimev2 块） | 测试 `::imports_and_write_ports_scan`（import 白名单面）＋ **人审** | 待实现（阶段 5）；人审原因：R1–R8 无「context 依赖白名单」一面 |
| 唯一状态写入＝`ledger_dump` 取一次装载（共享写面零写） | 测试 `::imports_and_write_ports_scan`（写面扫描）＋ **人审** | 待实现（阶段 5）；人审原因：无「写面白名单」专属闸 |
| 材料截断必披露（**渲染面**：披露行逐字＋三机检字段＋`selected_reason` 帽账） | 钉 **`pin-09`**（P1，**渲染面**）——**分工**：字段面挂 `specs/state.md`（`Manifest.material_truncated`）、披露行为面挂 `specs/answering.md`、帧面挂 `specs/transport.md`；本块落**产断面**（行为 5／6／不降级节，测试 `::truncation_disclosure_line_verbatim`／`::manifest_material_fields_and_reason`／`::truncation_signal_no_emit`） | 待织网（阶段 5） |
| 明细行集题不丢行（**渲染面**：权威/台账族全量无帽、帽只作用检索族） | 钉 **`pin-08`**（P0，**渲染面**）——**分工**：交付行为面挂 `specs/answering.md`（`::rowset_full_delivery`，钉行在册）；同一规则另见 `specs/execution.md` 行为 4（其挂钩表已补 pin-08 行——流水 43⑦b）；本块落**渲染帽分形面**（行为 4，测试 `::carrier_fractal_budget`） | 待织网（阶段 5） |
| 对话链只追加不改写（**视图面**：compaction 只产模型视图、`state.messages` 零覆盖） | 钉 **`pin-22`**（P0，**视图面**）——**分工**：字段契约面挂 `specs/state.md` 行为 4、写入面挂 `specs/bookkeeping.md` 行为 7；本块落「视图不改原史」面（行为 9，测试 `::compaction_overwindow_model_view`） | 待织网（阶段 5） |
| 超窗 compaction 摘要化（`pin-30` 的 compaction 半面；另半面＝旧 run 黑匣子回放如实空显挂 `specs/persistence.md` 行为 12、旧检查点状态读入挂 `specs/state.md` 行为 8） | 钉 **`pin-30`**（P2）——本块落 **compaction 半面**（行为 9，测试 `::compaction_overwindow_model_view`）；触发参数数值与承载位＝登记（风险 4） | 待织网（阶段 5） |
| `pin-24`（相位合同一次性）经逐条核实**不落本块** | 钉落点对读：记账面挂 `specs/state.md` 行为 5、写入面挂 `specs/bookkeeping.md` 行为 8、常量稳定面挂 `specs/prompts.md` 行为 1；**消费侧重发判定**＝追加编排归 `orchestration`＋标记写入归 `bookkeeping`——context 零合同、零标记、零追加时点 | 已核实（本批起草时逐条对读） |
| `pin-26`（对话层纯度）经逐条核实**不落本块** | 钉落点对读：字段面挂 `specs/state.md` 行为 6、写入面挂 `specs/bookkeeping.md` 行为 9、渲染面挂 `specs/understanding.md` 挂钩表；本块只经过程档案段渲染（本块过程段候选不入 `dialogue`——`dialogue` 写口不在本块） | 已核实（本批起草时逐条对读） |
| 帽/视窗数值单点、注入制、无裸字面（帽值引 `recon/K` R-K-07；视窗已裁 8k 档——流水 43④，承载位登记） | 测试 `::cap_constant_single_point` ＋ **人审**（风险 4） | 待实现（阶段 5） |
| 程序不判语义（无词表／正则） | 测试 `::no_lexicon_or_regex_in_context` | 待实现（阶段 5） |
| 渲染单点（消费方零字面副本） | 测试 `::renderers_single_source` | 待实现（阶段 5） |
| 所有有界处理必披露（截断/压缩机读信号在场） | 测试 `::truncation_signal_no_emit`／`::process_notes_bounded_summary` | 待实现（阶段 5） |
| 真源引用可解析（本规格全部引用行） | 真源引用闸（`tools/ref_resolvable.py` 的 check 子命令） | 交稿前本地实跑 |
| 「不做什么」的纯范围排除（不追加／不发帧／不判语义／不装指南等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（只引两块、零模型、零帧、写面单点）已由 R5/R6/R7＋AST 测试覆盖 |
