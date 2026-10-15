- 日期：2026-10-15 ｜ 状态：**评审发现清单（待 L0 逐条处置）**
- 被评对象：`specs/transport.md`（`状态: 草稿`）＋ 同批 `specs/modules.md` `## transport` 卡级修正（流水 28）
- 本清单只产发现，不修改任何现存文件。凡断言「X 不存在／X 与 Y 不一致」均附实读行号或 `grep` 证据；未证实的怀疑写成「疑点」。

## 一、结论摘要

1. **版式骨架合格**：`specs/transport.md` 十节齐、标题逐字、顺序正确（同 `docs/spec-format.md` §二之二 与已定稿 `state`／`persistence`／`agent-loop` 的排布）；行为约定**无**含糊词（`grep -nE "尽量|合理|必要时|视情况"` exit 1）。三道闸实跑**全绿**（见 §四）。
2. **一处 L0（跨规格公开类型表示冲突且本规格「已收正」的断言不实）**：本规格多处写「本批把『结构别名』收正为**字符串前向引用**」「卡注已定」，但 `specs/state.md:71` **仍是** `SseEvent = Mapping[str, Any]`（`# 帧载荷的结构别名`）＋`:91` 仍称「SseEvent 只作类型别名（帧载荷是 JSON 对象）」；`git status` 显示 state.md **本批未改**。同一公开名 `SseEvent` 两侧两种表示（state＝载荷别名／transport＝帧对象 `{seq,event,data}`），语义也不同（之一）（**T-1**）。
3. **两处中偏「钉/锚」**：本规格引 `synth/S6 §二 附注` 两处，但 S6 **无「附注」、§二 也无该事实**（失败腿实在 S6 §六【边界-2】／无 `replay_truncated` 实在 T-P9a1-33）（**T-2**）；登记 `pin-09` 的措辞与钉原文**不是同一件事**（pin-09＝材料截断披露，被登记成「失败披露／不泄漏内部细节」）（**T-3**）。
4. **四处中**：行为 9「流内异常→error」与「不降级」节「引擎/网关异常→`notice{run_failed}`＋done（不发 error）」措辞未对齐（**T-4**）；`session`（wire 三帧之一）载荷形状与发射方未落点（**T-5**）；`stream(cursor)` 游标语义含不含义含混（含 cursor 帧 vs 排他，与行为 4／R-K-49 不一致）（**T-6**）；`NOTICE_TYPES` 的 22 值来源锚 `recon/K`／`arch 票堆` 未列该枚举（**T-7**）。
5. **五处低**：框架红线括号方向混淆（**T-8**）；verdict 两形键集／step 帧键集未落点（可能正确排除、未显名）（**T-9**）；接口新增 `EventBus.closed` 不在模块卡公开面（**T-10**，卡级）；`pin-27` 的「帧 frozen_date」归属疑点（**T-11**）；`walk/01` D6（无背压）未接亦未登记（**T-12**）。
6. **22 值实测核对**：规格 `NOTICE_TYPES` 二十二个取值**逐字对得上码面**（21 个显式 `"type":` 字面 ＋ `subtask_failed` 条件字面，共 22；`graph.py:3483`＝`"subtask_refused" if final else "subtask_failed"`）；**不多不少**。唯现状另有**隐式兜底值 `"notice"`**（`graph.py:3438/3581` 的 `("notice_type", "notice")`），本规格已明标**取消该兜底**（行为 7）——非漏列，属有意收正。
7. 计数：**12 条**发现——`L0×1`（T-1）／`高×0`／`中×6`（T-2…T-7）／`低×5`（T-8…T-12）。**结论：不可定稿**（T-1 须先处置；T-2／T-3 为锚点/钉登记纠错）。**卡级**：仅 T-10（`closed` 属性未入卡）一项属卡面欠账，**无「卡须回阶段 2 重做」的结论**（卡级修正本身自洽，见问答 12／16）。

## 二、发现清单表

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| T-1 | **L0** | **跨规格同名公开类型两种表示／两种含义，且本规格「已收正」的断言不实**：`specs/state.md:71` 仍写 `SseEvent = Mapping[str, Any]  # 帧载荷的结构别名`，`:91` 仍称「`SseEvent` 只作类型别名（帧载荷是 JSON 对象）」；而本规格 `:29`（触及模块）／`:128`（依赖）／`:137`（风险 8）／`:150`（挂钩表）／`:158` 均写「本批把『结构别名』**收正为字符串前向引用**」「卡注已定」；`specs/modules.md:421` 卡注只说「`SseEvent` 由『载荷别名』收正为**帧对象**」、未提 state 侧表示。`git status --short` 仅 `M specs/modules.md`／`M docs/runtime-refactor/00-决议与方法.md`／`?? specs/transport.md`——**state.md 本批未改**。`00-决议与方法.md` 流水 28 亦已宣称「`state.RunHandle.stream` 的元素类型以字符串前向引用指它」。**后果**：`state.SseEvent`（载荷 dict）与 `transport.SseEvent`（帧 `{seq,event,data}`）同名不同物，`RunHandle.stream: AsyncIterator[SseEvent]` 的静态类型与实际产出（帧对象）不符 | `specs/state.md:69,71,91`；`specs/transport.md:29,128,137,150,158`；`specs/modules.md:411,421`；`docs/runtime-refactor/00-决议与方法.md`（流水 20／24／28）；`git status --short` | **先处置再定稿**：①（首选）按流水 28 的既定意图**同批改 `specs/state.md`**——`RunHandle.stream` 元素类型改为指向本块帧类型的**字符串前向引用**、删「载荷别名」表述与 `:71` 的 `Mapping[str, Any]`（跨规格，与 `persistence` P-1 同款；`state` 已定稿，属跨规格动作，呈主窗）；②若判「state 本批不动」，则改本规格 `:29/:137/:150` 三处**如实写「收正待 state 侧落地」**，不得写成已改 |
| T-2 | 中 | **真源锚点不实：`synth/S6 §二 附注` 不存在**。本规格 `:90`（行为 13）与 `:98`（不降级「失败披露一律走帧」）各引一次「真源 `synth/S6-事件与帧目录.md` §二 附注」。实读 `synth/S6` 六节标题＝一/二/三/四/五/六（`:10,30,44,57,72,88`），**无「附注」节**；§二（`:30-41`）只有 wire 三帧表＋verdict 拆形。①「失败腿＝引擎/网关异常→`notice{run_failed}`＋done」实在 **S6 §六【边界-2】（`:91`）／`iface/P9a1` T-P9a1-27（`:133`）**；②「wire 面无 `replay_truncated`」实在 **T-P9a1-33（`:145`）**，S6 全篇无 `replay_truncated` 字样（`grep` 零命中）。真源引用闸只判路径/节号可解析（`§二` 可解析），判不到「该节里真有那条事实」 | `specs/transport.md:90,98`；`docs/runtime-refactor/synth/S6-事件与帧目录.md:10,30-41,88,91`；`docs/runtime-refactor/iface/P9a1-端点与帧通路.md:133,145` | 两处锚点改准：行为 13 → 引 `iface/P9a1` T-P9a1-33；「失败披露」→ 引 `synth/S6` §六【边界-2】＋ `iface/P9a1` T-P9a1-27（删「§二 附注」） |
| T-3 | 中 | **钉登记与钉原文不是同一件事（误登记）**：本规格挂钩表 `:156` 登记「失败披露走 `notice`、不泄漏内部细节（帧面）｜钉 `pin-09` 的帧面（披露行为面挂 `specs/answering.md`）」；行为 14（`:91`）写「钉 `pin-09` 的帧面：截断与失败披露一律走 `notice`，不泄漏内部细节」。但 `eng/04a` **pin-09 原文**＝「材料截断必披露：`material_truncated` notice＋『未渲染部分不作答』声明」（`:18`，来源 V2-61／G4）。**pin-09 讲的是「材料截断披露」，不是「失败披露／不泄漏内部细节」**——后两件其实是 `synth/S6` §六【边界-2】＋ `walk/裁决表.md` §01-D（error 帧不给原始异常文本），**仓内无对应钉**。旁证：`specs/state.md:197` 把 pin-09 的**字段面**（`Manifest.material_truncated`）记在本块、披露行为面记 `answering`——与「材料截断」同物 | `specs/transport.md:91,156`；`docs/runtime-refactor/eng/04a-应钉行为清单.md:18`；`specs/state.md:197`；`docs/runtime-refactor/synth/S6-事件与帧目录.md:91`；`docs/runtime-refactor/walk/裁决表.md:42` | 二选一：①如实登记 pin-09＝**材料截断（`material_truncated` notice）的帧面**（并删「失败披露／不泄漏内部细节」措辞）；②行为 14 的「不泄漏内部细节」改挂 `walk/裁决表.md` §01-D 真源（无钉可登），pin-09 按①写 |
| T-4 | 中 | **异常分派措辞未对齐（易误实现）**：行为 9（`:86`）写「流末恒发 `done`，**流内异常**改发 `error`」；「不降级与静默禁令」节（`:98`）写「**引擎／网关异常** → `notice{type:"run_failed"}` ＋ 正常 `done`（**不触发 `error` 帧**）；**帧通路自身异常**才发 `error`」。「流内异常」未限定为「帧通路自身异常」，零上下文实现者可能把引擎/网关异常也发成 `error` 帧，与 §01-D／S6【边界-2】冲突 | `specs/transport.md:86,98`；`docs/runtime-refactor/synth/S6-事件与帧目录.md:91`；`docs/runtime-refactor/walk/裁决表.md:42` | 行为 9 的「流内异常」改述为「**帧通路/流渲染自身异常**」；与「不降级」节口径统一（引擎/网关异常走 `run_failed` notice＋done） |
| T-5 | 中 | **覆盖缺口：`session` 帧载荷与发射方未落点**。本规格 `目标`（`:9`）与 `WIRE_FRAMES`（`:53,:60`）宣布「wire 三帧闭世界」归本块，但 `session` 帧的载荷形状 `{run_id, resume:bool}` 与发射时机**全篇无落点**（行为 8 只给 `ask` 帧、行为 9 只给 `done`／`error`）；「不做什么」8 行亦**未显名**把 session 帧划给 `api`（row7 只列「HTTP 鉴权、参数校验、开流前错误码」）。真源：`synth/S6:36`（session 载荷 2 键）、`iface/P9a1:104`（T-P9a1-07/08 session 首帧恒发／占帧号） | `specs/transport.md:9,53,60,85,86`；`docs/runtime-refactor/synth/S6-事件与帧目录.md:36`；`docs/runtime-refactor/iface/P9a1-端点与帧通路.md:104` | 二选一：①在接口定义补 `session` 帧载荷 `{run_id, resume:bool}`（归本块 wire 三帧闭世界）；②在「不做什么」显名「`session` 首帧的发射与载荷 → `api`（开流段）」，并把 `WIRE_FRAMES` 的归属写清（本块只管帧名闭世界与信封） |
| T-6 | 中 | **游标语义含混（off-by-one 隐患）**：行为 5（`:82`）「`stream(cursor)` **从 `cursor` 起**给出其后全部帧…＝原流从该游标起的后缀（逐帧同 `seq`）」读作**含** `cursor` 那帧；行为 4（`:81`）「客户端以 `id` 回送 `Last-Event-ID` 即可**无位移续传**」要求**不含**已收帧；`recon/K` R-K-49（`:354`）定义 `cursor`＝**已收最大 `seq` ＋ 1**（排他）。三处口径不一致，重连可能重复投递或漏帧（正是 §01-A 要治的病） | `specs/transport.md:64,81,82`；`docs/runtime-refactor/recon/K-上下文事件指南预算.md:354`（R-K-49） | 定死一句：`stream(cursor)` 的起点＝**排他**（`cursor`＝下一帧 `seq`，等价 R-K-49）；并写明 `Last-Event-ID（id）→ cursor` 的转换（`cursor = id + 1`）；行为 5 断言同步改准 |
| T-7 | 中 | **`NOTICE_TYPES` 二十二值的来源锚不实**：规格 `:61` 写「来源＝现状码面全量实测，**锚 `recon/K-上下文事件指南预算.md` 与 `arch` 票堆**」。实读 `recon/K`：仅在 **D-K-48（`:557`）／D-K-56（`:613`）** 记「`type` 字面量无闭世界常量（对比 `EVENT_KINDS`）」，举例 `material_truncated`／`budget_converged` 两值——**未列全 22 值**；`grep -rho '"type": *"[a-z_]*"' appv2/runtime/*.py` 得 21 值＋`subtask_failed` 条件字面＝22（实测真源是码面，非 recon/K／票堆） | `specs/transport.md:61`；`docs/runtime-refactor/recon/K-上下文事件指南预算.md:557,613`；`grep` 实证（`graph.py`／`executor.py`／`budget.py`／`context.py`） | 改锚为「现状码面实测（`appv2/runtime/graph.py`／`executor.py`／`budget.py`／`context.py` 的 `"type":` 发射点全量）」；或补一条机检（grep/AST）把 22 值钉住，避免「来源」与实际不符 |
| T-8 | 低 | **框架红线括号方向混淆**：`:70`「不引包内其它块（本块只依赖 `state` 的类型名，**且是字符串前向引用**）」——「字符串前向引用」是 **state→transport** 的表示（见 `:29`「`RunHandle.stream` 的元素类型引用本块的帧类型…字符串前向引用」），不是 **transport→state** 的依赖形态；`:150` 同款「不引包内其它块（`state` 仅字符串前向引用）」亦把方向记反 | `specs/transport.md:70,150 vs :29` | 改述：删「且是字符串前向引用」（那是 state 侧的事），只留「本块只依赖 `state` 的类型名」 |
| T-9 | 低 | **覆盖留白（可能正确排除、未显名）**：`verdict` 两形载荷键集（`iface/P9a1` T-P9a1-06：`verify` 6 键／`final` 4 键）未在本规格落点（行为 6 `:83` 只给 `subtype` 判定与「键集越出契约判 `verify` 且透传」）；`step` 帧 3 键（T-P9a1-29）／`text`/`tool`/`observation`/`citation` 键集（T-P9a1-30）同理 | `specs/transport.md:83`；`docs/runtime-refactor/iface/P9a1-端点与帧通路.md:100,138-139` | 显名一句「帧载荷**键集归发射方**（本块只透传，见行为 6）」，把 T-P9a1-06/29/30 的键集明确划给 emitter（避免「越界/漏项」两可） |
| T-10 | 低 | **卡级：接口新增 `EventBus.closed` 不在模块卡公开面**。本规格接口定义（`:47`）列 `@property def closed(self) -> bool`；`specs/modules.md` `## transport` 卡公开面（`:413-415`）只列 `emit`／`stream`／`close`，**无 `closed`**。（其余签名逐条对得上：`emit(name,payload)->SseEvent`／`stream(cursor:int=0)->AsyncIterator[SseEvent]`／`close()->None`／`envelope`／常量族） | `specs/transport.md:42-47`；`specs/modules.md:411-418` | 回阶段 2 在卡公开面补 `closed` 属性，或规格删该属性（判据 12「以卡为准」） |
| T-11 | 低 | **`pin-27` 归属疑点（未证实）**：`eng/04a` pin-27＝「冻结时钟：`EVAL_FROZEN_DATE` 缺省 2026-08-31、**帧 `frozen_date` 全在场**；real 须显式」（`:36`，来源 `Q15-对账报告.md:4`／`tests/domains/test_v2_eval_clock.py`）。仓内 `frozen_date` **只出现在评测 jsonl 跑批记录**（`eval/results/*.jsonl` 的 `"frozen_date": "2026-08-31"`）与 `appv2/runtime/eval_clock.py`（其自述消费面＝「rerun 跑批（jsonl frozen_date 溯源字段）」，`:14`）；**SSE 帧代码（`graph.py`／`executor.py`／`wire.py`／`bridge.py`）无此键**。故该钉的「帧」是否指 SSE 帧**须辨明**：若指 SSE 帧，则本块**漏登记**且**现状无此事实**；若「帧」实指 jsonl 跑批记录，则该钉不属本块、不登记正确（旁证：`specs/persistence-评审.md` §复审曾把 pin-27 的「帧面」判给 transport——与「仓内无此事实」相左，须裁） | `docs/runtime-refactor/eng/04a-应钉行为清单.md:36`；`appv2/runtime/eval_clock.py:14,31-33`；`eval/results/*.jsonl`；`specs/transport.md`（未登记）；`grep -rn frozen_date appv2 web eval` | 辨明 pin-27 的「帧」所指：若是 SSE 帧→本块补登记（并核现状是否真「全在场」，如否先修钉原文）；若指跑批记录→改钉原文措辞为「跑批记录 frozen_date 全在场」，本块不登记（正确） |
| T-12 | 低 | **`walk/01` D6（无背压）未接、亦未登记（未结差异）**：`walk/01-进门.md` §四 D6＝「无背压声明 ↔ 通信契约含背压（HandBook ch12）」，属**差异项**；但 Owner 裁决（`walk/裁决表.md` §01 只 A/B/C/D，`:37-43`）**未含背压**，§七「现状缺陷」清单（`:43`／`walk/01:110`）亦**未列背压**。本规格 风险 5 只提「缓冲无上限/无淘汰/无 TTL」，未提背压——该差异**无人承接**（归属未证：属 `api` 流桥还是 `transport`） | `docs/runtime-refactor/walk/01-进门.md:58,74,110`；`docs/runtime-refactor/walk/裁决表.md:37-43`；`specs/transport.md:134` | 呈主窗定性：背压差异归 `api` 块（SSE 流桥）还是 `transport`；若归本块，在依赖与风险补一条（检测＝人审/登记）；若不归，在 `api` 规格登记 |

## 三、16 问逐条回答

**1 十节齐＋标题逐字？** **无发现。** 十节标题逐字且顺序正确：`## 目标`(:7)／`## 不做什么`(:11)／`## 触及的模块`(:24)／`## 接口定义`(:33)／`## 框架与依赖红线`(:67)／`## 行为约定`(:76)／`## 不降级与静默禁令`(:94)／`## 验收测试`(:101)／`## 依赖与风险`(:126)／`## 与闸的挂钩表`(:140)——与 `docs/spec-format.md` §二之二（`:33-34`）逐字一致；与已定稿 `state`／`persistence`／`agent-loop` 同序（框架红线在接口定义后、行为约定前）。`check_specs.py` 实跑 PASS（注：该闸其实不校标题名，见问答 8）。

**2 行为约定每条能否写成 `assert`／含糊词？** **无发现。** 判 FAIL 的含糊词「尽量／合理／必要时／视情况」全文 **0 命中**（`grep` exit 1）；行为 1–15（`:78-92`）**每条**带【断言：…】，落成集合比较／抛错／往返等价／AST 扫描等机检形。

**3 数字有无裸值？** **无发现。** 数字命中项全为标识符／锚点／带真源的计数——「十二值」（:39＝九类＋三帧）／「九值」（:59 携 `synth/S6` §一）／「二十二值」（:61 携码面实测）／「0 起」（:80，同 `recon/K` R-K-41）／「三行＋空行」（:79 携 T-P9a1-03）；无配置裸字面值。

**4 不做什么每条「由谁承担＋锚点」？** **无发现。** 8 行俱带：`:15`→各相位/编排层＋`agent-loop.md` 行为 1/8 与各相位卡；`:16`→`orchestration`＋`agent-loop.md` 行为 8；`:17`→各发射方＋「同上」；`:18`→`persistence`＋`persistence.md` 与 `## persistence`；`:19`→`state`(判定)＋`bookkeeping`(落地)＋`state.md` 行为 12/13；`:20`→`gateway_adapter`＋`## gateway_adapter`；`:21`→`api`＋`## api` 与 `iface/P9a1`(T-P9a1-25)；`:22`→`判断归责表.md`。（`:17` 锚「同上」略弱，可补一句，非阻断。）

**5 框架红线闸名真存在／source 真覆盖 transport？** **无发现（闸侧）。** 逐条实读 `tools/importlinter_v2.toml`：**R5b**（`:101-105`，`source` 第 103 行**含** `appv2.runtimev2.transport`）、**R6**（`:110` 含 transport）、**R7**（`:116` 含 transport）——编号真、覆盖真；实跑三条均 KEPT。「无点名框架」（:69）写法符合 `spec-format.md` §二。唯**未点名 R5**（`appv2.runtimev2` 不得引旧 `appv2.runtime`；R5 source 含 transport）——本块无相关红线声明，不构成漏闸，记为观察。

**6 不降级与静默禁令？** **有发现——T-2（失败披露锚点）／T-4（异常分派措辞）。** `:96`「合法降级路径：**无**」；`:97` 四条「不得静默」（行为 3/5/7/12）各配断言；`:99`「脱敏是硬要求」。唯「失败披露一律走帧」的锚（`:98`「S6 §二 附注」）不实（T-2），且「流内异常」措辞与「不降级」节口径未对齐（T-4）。

**7 验收测试（每行标识／边界集保留集）？** **无发现。** 18 行**全部**绑 `tests/domains/test_v2_transport.py::<id>`（`:105-122`）；`:121`【边界集】、`:122`【保留集】两行俱在；`:124` 有测试文件归属注（新建文件，与旧码 `appv2/runtime/events.py` 测试形状不同的说明）。

**8 与闸的挂钩表（填了没／接不上写原因／「已真跑」属实否）？** **有发现——T-3（pin-09 行）。** 表已填（`:142-159`）；`:144`「spec gate（该闸只校这两项——十节标题不在其作用面）」**诚实属实**（实读 `check_specs.py` 只校 `## 触及的模块`／`## 验收测试`，与 `persistence-评审` P-3 同判）；`:146`「已进 CI」属实；`:147-149`「R5b／R7／R6 已真跑」**由本子代理亲跑属实**（18/18 KEPT）；`:150/:151/:158/:159` 四处「无专属闸→人审＋原因」齐备。唯 `:156`（pin-09）登记与钉原文不同物（T-3）。

**9 与 `walk/` 决策是否冲突？** **无发现（主线一致）＋两处边缘。** 逐条比对：`裁决表.md` §01-A（游标全流单调，`:39`）→ 行为 3/4 ✔；§01-D（error 帧不给原始异常文本，`:42`）→ 行为 9/14 ✔；§01-B（身份头清头）／§01-C（权限过滤口子）→ 本规格正确排除（「不做什么」row7 归 `api`）✔；§01 现状缺陷（缓冲无上限、公开面缺 `EVENT_BLACKBOX`…登记为现状证据，`:43`）→ 风险 5 与 `EVENT_KINDS` 收正 ✔；`01-进门.md` §七 Q-A/Q-D（`:106,109`）✔；项目级裁决 #7（新建 runtimev2）／#12／#13（语义交模型，→ 行为 15 零判断）✔；`判断归责表.md`（进门全结构、收尾完成判定＝程序，`:23-25`）✔；`00-设计总纲` §二 总纪律 ✔。**边缘**：`walk/01` §四 D6（无背压）未接亦未登记（T-12，未结差异）；S6 §三「runtime `seq` ≠ 帧 `id`」为本规格**有意废止的现状**（目标/风险已声明 S6 退为现状证据），非冲突。

**10 覆盖（`synth/S6` 事件/帧目录 ＋ `iface/P9a1` T-P9a1-01…35）？** **有发现——T-5／T-9。** 逐条对账（逐条列漏项）：
- **T-P9a1-01/02**（事件类型集＝`EVENT_KINDS`∪wire 三帧／九类闭世界）→ 行为 1＋`EVENT_KINDS`/`WIRE_FRAMES` ✔；**03**（信封字节形/`ensure_ascii=False`）→ 行为 2 ✔；**04/05**（透传／verdict 拆形单点/`VERDICT_SUBTYPES`）→ 行为 6 ✔；**06**（verdict 两形**载荷键集**）→ **未落点**（T-9，疑属发射方）。
- **07/08**（`session` 首帧恒发＋载荷 `{run_id,resume}`／占帧号）→ **未落点**（T-5）；**09/10/11**（帧号＝响应内计数器／帧号≠seq／缓冲位映射）→ 本规格**有意废止的现状**（行为 3/4 统一为 `id`＝`seq`）✔。
- **12/13/14**（`Last-Event-ID` 解析／仅头缺参／重连定位 404）→ **属 `api` 块**（开流前），本规格**正确排除**（「不做什么」row7；行为 13 `:90` 明标「由 `api` 开流前拒」）✔；**15/16**（重放游标／尾随在跑 run）→ 行为 5/11 ✔（但游标含混见 T-6）；**17**（重放帧号 +1）→ 有意废止 ✔。
- **18/19/20/21/22**（缓冲结构／api 唯一排空点、多消费者各自游标／段续拼同一缓冲／resume 段帧号重启／排空异常留痕）→ 行为 3/11/9＋风险 5 ✔（18「无淘汰/无 TTL」作现状证据入风险 5）。
- **23/24/25**（流尾恒发 done/error／error 形态／流内异常不走 HTTP）→ 行为 9 ✓；**26**（挂起铁律 ask 后照发 done）→ 行为 8 ✔；**27**（失败腿 `run_failed` notice＋done）→ 不降级「失败披露一律走帧」✔（锚点 T-2）。
- **28**（ask 帧载荷/`kind` 闭世界）→ 行为 8 ✔；**29/30**（`step` 3 键／其余业务帧键集）→ **未落点**（T-9，透传机制由行为 6 覆盖）；**31**（`blackbox` 瘦指针 7 键恒发一帧）→ 行为 10 ✔。
- **32**（响应头 `text/event-stream`/`Cache-Control`）→ **属 `api`**（HTTP），正确排除；**33**（无 `replay_truncated`）→ 行为 13 ✔（锚点 T-2）；**34**（E3 入参值映射）→ **属 `api`**，正确排除；**35**（追问形态帧面同形/不新增帧类型）→ 属 `api`，正确排除。
- **越界**：未见把别块的事写进来（`session` 归属是**漏项**不是越界；行为 9/13 提及 `api` 拒/收束均作**边界标注**）。**结论**：属本块而**没接**的＝**T-06（verdict 键集，低）／T-07·08（`session`，中）／T-29·30（业务帧键集，低）**；属 `api` 且**正确排除**的＝**T-12/13/14/32/34/35**（开流前错误码、响应头、入参映射、追问端点面）。

**11 总纪律残留（程序替模型判语义）？** **无发现。** 行为 15（`:92`）明文排「无词表／正则语义判定、无模型调用、无落盘」；本块无「若出现 X 词就 Y」形设计（判据均为集合成员／抛错／帧序列比较／AST 扫描等结构判）。

**12 与模块卡一致（职责／公开接口／依赖）＋卡级修正自查？** **有发现——T-1／T-10。** 一致项：职责 `transport.md:9` 与卡 `modules.md:406`（事件名闭世界 9 类／帧载荷分型闭世界含 `notice.type`／事件总线／帧通路与断线续推）对得上；`EventBus.emit/stream/close`＋`envelope`＋五常量族与卡 `:411-418`/`:431` 逐条对得上；依赖 `:128`（模块 `state`）＝卡 `:425`。**卡级修正自查**：①「总线不能挂状态上」与 `state.md:108`（`RunHandle.stream` 非状态字段）＋`state.md` 行为 3（状态可投影）自洽 ✔；②「`SseEvent` 由载荷别名收正为帧对象」与「帧出口／九类闭世界／游标全流单调」卡职责自洽 ✔；③**但卡注未含 state 侧「字符串前向引用」的表示切换**（卡 `:421` 只说帧对象），且 state.md 未随之改（**T-1**）；④接口新增 `closed` 不在卡公开面（**T-10**，须回阶段 2 改卡或删）。

**13 接口与已定稿规格逐字对账？** **有发现——T-1（独立发现）／T-6。** ① **`RunHandle.stream` 类型表示**：`state.md:69`＝`AsyncIterator[SseEvent]`、`:71`＝`SseEvent = Mapping[str, Any]`（**残留**，非字符串前向引用）、`:91` 明写「`SseEvent` 只作类型别名（帧载荷是 JSON 对象）」——**收正未落地**（T-1）。② **`ask` 帧 `kind` ↔ `AskReason.kind` 映射**：`preconditions.md:47` `AskReason.kind ∈ {external_table_approval, caliber_clarify}`、`:52` 唯一映射表（`external_table_approval`→同名、`caliber_clarify`→`clarify`），帧侧闭世界 `clarify｜external_table_approval`——本规格 `ASK_FRAME_KINDS`（`:56,:63`）**对得上** ✔。③ **`notice` 恰三键**：本规格行为 7（`:84`）`{type,gates,content}` 与 `state.md` 行为 12（`:117`「`notice` 恰三键 `type`／`gates`／`content`，形状真源 `synth/S6` §一」）**一致** ✔；`persistence.md` 行为 14（`:150`）是**落盘失败 fail-closed**（「发帧的实施口是 `transport`、批次协调归 `orchestration`」），**不涉及** notice 三键，故**无口径冲突**（触界注记 vs 失败披露两处都看：`state` 行为 12＝触界注记✔、`persistence` 行为 14＋本规格行为 9/不降级＝失败披露✔）。

**14 钉登记（全表扫）？** **有发现——T-3／T-11。** ① **同物核对**：`pin-29`（`04a:38`「挂起→resume 闭环…两形态 ask 帧…kind 判别字段」）↔ 本规格挂钩表 `:155`「挂起→resume 的帧面（`ask` 帧 `kind` 闭世界＋挂起后照发 `done`），闭环面挂 `agent-loop.md`」✔ 同物、分工清楚；`pin-09`（`04a:18`「材料截断必披露」）↔ `:156`「失败披露／不泄漏内部细节」✘ **不是同一件事**（T-3）。② **漏登核查（逐个判）**：`pin-02`（无据差值，`04a:11`）＝答案面内容，归 `verification`／`answering`——**不应登本块**（本块只搬帧）；`pin-04`（发射 JSON 不进答案面，`04a:13`）＝答案面内容（`emission_strip` 只是 22 值之一）——**不应登本块**；`pin-10`（`citation` 落账，`04a:19`）＝引标正确性，归 `verification`／`answering`——**不应登本块**；`pin-27`（冻结时钟「帧 `frozen_date` 全在场」，`04a:36`）＝**归属疑点**（T-11：仓内 `frozen_date` 只在评测 jsonl、SSE 帧无此键）。③ **钉号/优先级**：`pin-29` 标 P0，与 `04a:5`／`:38` 一致 ✔；`pin-09` 未标优先级（`04a:18`＝P1），非写错、系漏标。④ **分工面**：`pin-29` 清楚（帧面本块／闭环面 `agent-loop`）；`pin-09` 分工不清（既称「帧面」又称「披露行为面挂 `answering`」，且本块与 `state`／`answering` 三方对同一钉各说一面，**有「两头都认」风险**——见 T-3）。

**15 真源引用真实且该节真有事实？** **有发现——T-2／T-7。** 逐条核实为真：`synth/S6` §一（九类事件及各帧载荷键集，含 `blackbox` 7 键，`:14-24`）✔；§二 wire 三帧与 verdict 拆形（`:30-41`）✔；`synth/S3` **C-05**（事件九类、八类为陈旧注记，`:20`）✔／**C-10**（`__all__` 未导出 `EVENT_BLACKBOX`，`:25`）✔；`recon/K` events.py 段的 `EventBus` 行为与 `seq = len(self._events)`（R-K-41「`seq` 由历史长度唯一决定（单调、0 起、无跳号）」，`:301`；R-K-34「`seq` ＝断线游标」，`:259`）✔；`iface/P9a1` **T-P9a1-26/27/31/33**（`:132,133,140,145`）原文真 ✔；`walk/裁决表.md` §01-A/§01-D（`:39,42`）原文真 ✔。**不实／不符**：`synth/S6 §二 附注`（S6 无「附注」，T-2）；`NOTICE_TYPES` 来源锚 `recon/K`／`arch 票堆`（未列 22 值，T-7）。**22 值专核**（`grep -rho '"type": *"[a-z_]*"' appv2/runtime/*.py`）：**21 显式值 ＋ `graph.py:3483` 条件字面 `subtask_failed`＝22**，与规格**逐一相符、不多不少**；码面另有隐式兜底值 `"notice"`（`graph.py:3438/3581`），本规格已明标取消（行为 7），非漏列。

**16 卡级问题（只报不改）？** **有发现，均非「卡须重做」。** ① 接口新增 `EventBus.closed` 未入 `## transport` 卡公开面（T-10，须回阶段 2 改卡或规格删）；② 卡注（`modules.md:421`）未承载 state 侧「字符串前向引用」的表示切换、且该切换在 state.md 未落地（T-1，卡修正「已改卡」属实但连带面留白）；③ 卡依赖行（`modules.md:425`）＝`state`，与规格一致；职责／边界／依赖三面**未见卡错**；卡级修正（`EventBus`／帧对象）**本身自洽**（与 R5b、`state` 行为 3 不冲突）。**无「卡须回阶段 2 重做」的结论。**

## 四、闸实跑记录（2026-10-15）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                       # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：17 份规格的真源引用与边界规则编号均可解析。   # exit 0

$ uv run lint-imports --config tools/importlinter_v2.toml
Analyzed 129 files, 508 dependencies.
... （R1–R8 逐条 KEPT）
R5b ADR-0002 红线① 扩展：框架只许在 runtimev2.orchestration（其余 16 块禁引）  KEPT
R6 runtimev2 各块只经 tools 接触引擎  KEPT
R7 runtimev2 各块只经 gateway_adapter 调模型  KEPT
Contracts: 18 kept, 0 broken.                   # exit 0
```

辅助取证命令（关键）：
- `grep -nE "尽量|合理|必要时|视情况" specs/transport.md` → **exit 1（0 命中）**。
- `grep -rho '"type": *"[a-z_]*"' appv2/runtime/*.py | sort | uniq -c` → 21 个 `"type":` 值；`subtask_failed` 为 `graph.py:3483` 条件字面（`sed -n '3481,3489p'`）＝共 22；隐式兜底 `"notice"` 见 `graph.py:3438,3581`（`("notice_type", "notice")`）。
- 逐条核 `tools/importlinter_v2.toml`：**R5b:103／R6:110／R7:116** 的 `source_modules` **均含** `appv2.runtimev2.transport`；R5:97 的 source 为 `appv2.runtimev2`（含 transport，本规格未点名）。
- `grep -n "SseEvent\|前向引用\|Mapping\[str, Any\]" specs/` → `state.md:69,71,91`（**残留 `SseEvent = Mapping[str, Any]`**）／`modules.md:411,421`／`transport.md:29,128,137,150,158`（**T-1 依据**）。
- `git status --short` → `M specs/modules.md`／`M docs/runtime-refactor/00-决议与方法.md`／`?? specs/transport.md`——**`specs/state.md` 未在本批改动**（T-1 依据）。
- `grep -n "附注\|replay_truncated\|run_failed" docs/runtime-refactor/synth/S6-事件与帧目录.md` → 仅 `:91`（【边界-2】失败腿）；S6 无「附注」（**T-2 依据**）。
- `grep -n "frozen_date" appv2/runtime/eval_clock.py`（`:14,31-33`）＋ `eval/results/*.jsonl`（`"frozen_date": "2026-08-31"`）——SSE 帧代码无此键（**T-11 依据**）。
- `grep -n "decision_note\|...\|22\|notice 的 type" docs/runtime-refactor/recon/K-上下文事件指南预算.md` → 仅 D-K-48（`:557`）／D-K-56（`:613`）举例两值（**T-7 依据**）。

### 未验证清单

1. `tests/domains/test_v2_transport.py` **不存在**、`appv2/runtimev2/transport/` 无实现——18 行验收测试只能核标识形态，无法实跑（阶段 5）。
2. 「R5b／R6／R7 已真跑」为**契约空过**（transport 无实现代码）：契约存在且 KEPT 已实测，「transport 实现层真合规」待阶段 5。
3. **T-1** 的最终严重度取决于评审对「`state` 侧表示切换是否须在本批随 `transport` 一起落地」的判定：若判「须先改已定稿 `state.md`」→ 保持 L0；若判「state 本批不动、本规格改述为待落地」→ 降为中。本清单按「本规格多处断言『已收正』而仓内无改动」维持 **L0**。
4. **T-11**（pin-27 的「帧」是否指 SSE 帧）须辨明后才好定「漏登记 vs 不登记正确」；`persistence-评审` 复审曾把 pin-27 的「帧面」判给 `transport`，与本清单「仓内无此事实」相左，须裁。
5. **T-12**（背压差异归属）须主窗定性（`api` vs `transport`）。

---

## 五、L0 处置表（逐条清零 · 2026-10-15）

> 按 Owner 排产阶梯，规格文本改动由 **L0 直接落笔**；**卡级修正**（窗 A 权限）同批落 `specs/modules.md`；**已定稿 `specs/state.md`** 的跨规格收正在本批一并落地（与流水 28 既定意图一致）。

| 编号 | 处置 | 落法 |
|---|---|---|
| **T-1**（L0） | **采纳 → 同批改 state（首选路）** | 按流水 28 的既定意图**落地 state 侧**：删 `SseEvent = Mapping[str, Any]` 载荷别名，`RunHandle.stream` 改**字符串前向引用** `AsyncIterator["SseEvent"]`（注释点明「元素类型＝transport 的帧对象 `{seq, event, data}`」），接口节那条改述为「本块不定义它、也不得给它安第二套含义（禁当载荷 dict 别名）」，框架红线「禁手写替代」同款改述。**跨规格动作已记流水**（state 为已定稿件、主窗知悉路径） |
| **T-2**（中） | **采纳** | 两处错锚改准：「无截断重放帧」→ `iface/P9a1` **T-P9a1-33**；「失败披露一律走帧」→ `synth/S6` **§六 边界-2** ＋ `iface/P9a1` **T-P9a1-27**；删「§二 附注」（该节不存在） |
| **T-3**（中） | **采纳（按建议①）** | `pin-09` 改回**它与原文同一件事**的面：「**材料截断披露的帧面**——`material_truncated` 帧必发且其 `type` 在闭世界内」；「失败披露／不泄漏内部细节」从 pin-09 摘出，**改锚红线 Owner 裁决 `walk/裁决表.md` §01-D**（仓内无对应钉，登记为人审面） |
| **T-4**（中） | **采纳** | 行为 9 改述为「**帧通路自身异常**改发 `error`」，并显写「**引擎／网关异常不发 `error` 帧**（走 `run_failed` notice ＋ 正常 `done`）」——与「不降级与静默禁令」节口径统一，杜绝零上下文实现者误实现 |
| **T-5**（中） | **采纳（按建议②＋①各取一面）** | 「不做什么」**新增一行显名**：`session` 首帧的发射时机与载荷归 `api`（开流段），本块只保证**帧名在闭世界内**与信封形状；`WIRE_FRAMES` 的归属在接口定义写清（本块管帧名闭世界＋信封） |
| **T-6**（中） | **采纳** | 行为 5 定死 **`cursor` 是排他起点**（＝下一帧 `seq`，等价 `recon/K` R-K-49），并写明换算「`Last-Event-ID(id) → cursor = id + 1`」；断言同步改准（`seq ≥ cursor` 的后缀；重复或漏帧即失败） |
| **T-7**（中） | **采纳** | `NOTICE_TYPES` 来源锚改准：**现状码面实测**（`appv2/runtime/` 的 `graph.py`／`executor.py`／`budget.py`／`context.py` 的 `"type":` 发射点全量），并写明 `recon/K` 的 D-K-48／D-K-56 只记「无闭世界常量、未列全」——不冒认它为取值真源 |
| **T-8**（低） | **采纳** | 删两处方向记反的括注（「且是字符串前向引用」是 state→transport 的表示，不是本块依赖形态） |
| **T-9**（低） | **采纳** | 行为 6 补显名：**帧载荷的键集归发射方**（真源 `iface/P9a1` T-P9a1-06／29／30 ＋发射点），**本块只透传、不校键不补键不删键**——把「未落点」正名为「正确排除」 |
| **T-10**（低） | **采纳 → 已改卡** | `## transport` 卡公开面补 `@property closed -> bool`（并顺手把 `stream` 行的注释补上「cursor＝下一帧 seq，排他」），与规格逐字对齐 |
| **T-11**（低，疑点） | **采纳 → 辨明并登记** | 去码面核：`frozen_date` 只见于**评测跑批 jsonl 记录**与 `appv2/runtime/eval_clock.py`（自述消费面＝跑批溯源字段），**SSE 帧代码无此键**——故 `pin-27` 的「帧」＝**跑批记录**，**不属本块**（不登记即正确）；建议 `eng/04a` 钉文措辞改准为「跑批记录 frozen_date 全在场」，**呈主窗**（`04a` 是主窗文件）。**并勘误**：`specs/persistence-评审.md` 复审段曾把 pin-27 帧面判给 transport——**该判据作废**，以本条为准 |
| **T-12**（低） | **采纳 → 登记并呈主窗** | 背压差异（`walk/01` §四 D6）Owner 裁决未含、现状缺陷清单亦未列 → 本批**不新增机制**，定性拟归 `api`（SSE 流桥），**呈主窗定性**；已在「依赖与风险」补一条（检测＝人审） |

**净结果**：12 条**全部采纳**（T-1／T-10 涉卡、T-1 连带改已定稿 `state` 侧表示；T-11／T-12 两项**呈主窗**定性／改钉文）。**无升 Owner 的业务裁决项**。

---

## 六、复审结论（独立子代理）

- 日期：2026-10-15 ｜ 复审人：独立子代理 ｜ 只读现存文件，仅追加本件
- 复审对象：`specs/transport.md`（修订稿）＋同批 `specs/modules.md`／`specs/state.md` 改动
- 依据：实读行号／`grep` 实证；三道闸**亲跑**；真源锚点**逐条去原文件核**。

### 6.1 逐条闭合核验（T-1…T-12）

| 编号 | 判定 | 证据（文件:行 ＋ 实读） |
|---|---|---|
| **T-1** | **闭合** | `specs/state.md` 本批**已真改**（`git status --short`＝` M specs/state.md`；`git diff HEAD -- specs/state.md` 删去 `-    stream: AsyncIterator[SseEvent]`／`-SseEvent = Mapping[str, Any]  # 帧载荷的结构别名`）。现 `state.md:69`＝`stream: AsyncIterator["SseEvent"]  # 元素类型＝transport 的帧对象 {seq, event, data}`；`:71-72` 注释点明「以字符串前向引用标注，不得安第二套含义」；`:92` 明写「禁把 `SseEvent` 当成"载荷 dict 别名"」；`:103` 改述「帧类型只许以字符串前向引用指向 transport 的 `SseEvent`」。`grep -n "SseEvent\|Mapping" specs/state.md` **无 `Mapping[str, Any]` 命中**（载荷别名已删净）。故 `transport.md:30`「本批把『结构别名』收正为字符串前向引用」**名副其实**。卡注 `modules.md:423` 描述的是 transport 自身 `SseEvent`（帧对象），与 state 侧表示不冲突 |
| **T-2** | **闭合** | `grep -n "附注" specs/transport.md` → **exit 1（0 命中）**。两处新锚**逐条去原文件核**：① 行为 13 `transport.md:91` 引 `iface/P9a1` **T-P9a1-33**——实读 `P9a1:145`＝「V2 帧面**无 `replay_truncated`** 帧……V2 对应语义＝404 诚实拒」，**事实真**；② 不降级 `transport.md:99` 引 `synth/S6` **§六 边界-2** ＋ `iface/P9a1` **T-P9a1-27**——实读 `S6:91`＝「`【边界-2】` **失败腿**：引擎/网关异常→`notice{type:"run_failed"}`＋正常 done（不触发 error 帧）」，`P9a1:133` 同事实，**两处均真有该事实**。S6 六节标题＝一/二/三/四/五/六（`:10,30,44,57,72,88`），确无「附注」 |
| **T-3** | **闭合** | 挂钩表 `transport.md:159` 登记改回「**材料截断披露的帧面**：`material_truncated` 帧必发且其 `type` 在闭世界内（披露行为面挂 `specs/answering.md`、字段面挂 `specs/state.md`）｜钉 **`pin-09`**（P1）」——实读 `eng/04a` 第 9 行＝「材料截断必披露：material_truncated notice＋『未渲染部分不作答』声明｜P1」，**与钉原文同一件事**；优先级 P1 **对**。`transport.md:160` 新行＝「失败披露走 `notice`／`error` 帧不泄漏内部细节 ｜ **无对应钉** → 红线锚 Owner 裁决 `walk/裁决表.md` §01-D」——已从 pin-09 摘出并改锚（实读 `裁决表:42` §01-D「error 帧还给不给用户原始异常文本｜**不给**」，真）。行为 14 `transport.md:92` 同口径 |
| **T-4** | **闭合** | 行为 9 `transport.md:87`＝「**引擎／网关异常不发 `error` 帧**——它走 `notice{type:"run_failed"}`＋正常 `done`」；不降级节 `transport.md:99`＝同款「引擎／网关异常 → `notice{type:"run_failed"}`＋正常 `done`（**不触发 `error` 帧**）；帧通路自身异常才发 `error`」。两处口径**已统一**，且与 `S6:91`／`P9a1:133`／`裁决表:42` 一致 |
| **T-5** | **闭合** | 「不做什么」新增行 `transport.md:22`＝「**`session` 首帧的发射时机与载荷**（`{run_id, resume}`……）｜`api`（开流段）——本块只保证**帧名在闭世界内**与信封形状｜…T-P9a1-07」；接口定义 `transport.md:52` 明标「闭世界常量族（**本块唯一真源**）」，`WIRE_FRAMES`（`:54`）归属由此显名。真源 `P9a1:104`（T-P9a1-07 session 载荷 2 键）实读真 |
| **T-6** | **闭合** | 行为 5 `transport.md:83`＝「`cursor` 语义＝**下一帧的 `seq`**……`stream(cursor)` 给出 `seq ≥ cursor` 的**全部帧**……**换算＝`cursor = id + 1`**」；断言同步为「帧序列＝原流中 `seq ≥ cursor` 的后缀」。与 `recon/K` R-K-49 口径一致。旁证：`state.md:70` `cursor` 注释＝「全流单调断线游标（＝下一帧 seq）」，模块卡 `modules.md:414` 注释同款「cursor＝下一帧 seq，排他」——**但 state.md 引的行为号有误，见 TZ-1** |
| **T-7** | **闭合** | `transport.md:62` 来源锚已改＝「**来源＝现状码面实测**：`appv2/runtime/` 下 `graph.py`／`executor.py`／`budget.py`／`context.py` 的 `"type":` 发射点全量；`recon/K` 的 D-K-48／D-K-56 只记『该值集合无闭世界常量』，未列全」。本子代理**亲跑** `grep -rho '"type": *"[a-z_]*"' appv2/runtime/*.py`＝**21 显式值**＋`graph.py:3483` 条件字面 `"subtask_refused" if final else "subtask_failed"` 的 `subtask_failed`＝**22**，与 `transport.md:62` 二十二值**逐字对齐、不多不少**（隐式兜底 `"notice"` 见 `graph.py:3438/3581`，规格行为 7 已明标取消，非漏列） |
| **T-8** | **闭合** | 框架红线 `transport.md:71`＝「**不引包内其它块**（本块只依赖 `state` 的类型名）。对应闸：**无专属闸 → 人审**」——原「且是字符串前向引用」括注**已删**；挂钩表 `transport.md:153` 同款已删 |
| **T-9** | **闭合** | 行为 6 `transport.md:84` 补显名「——**帧载荷的键集归发射方**（`step`／`text`／`tool`／`observation`／`citation`／`verdict` 各帧的键集真源＝`iface/P9a1` T-P9a1-06／29／30 与发射点本身；**本块只透传、不校键、不补键、不删键**）」。真源 `P9a1:100,138,139` 实读真 |
| **T-10** | **闭合** | 模块卡 `modules.md:416-417` 已补 `@property def closed(self) -> bool`（`git diff` 可见新增），与规格接口定义 `transport.md:47-48` 逐字一致 |
| **T-11** | **闭合** | `transport.md:140` 风险 10 登记「`pin-27` 的『帧』＝**跑批记录**，**不属本块**……建议 04a 钉文措辞改准（呈主窗）」；实读 `eng/04a` 第 27 行＝「冻结时钟……帧 frozen_date 全在场」，`grep -rn frozen_date appv2` 仅 `eval_clock.py`（跑批溯源面）、SSE 帧代码无此键——辨明**正确**。**挂钩表内无 `pin-27`**（`grep -n "pin-" specs/transport.md` 仅 `:158 pin-29`／`:159 pin-09`／`:140` 风险节提及），**未误登记** |
| **T-12** | **闭合** | `transport.md:139` 风险 9 登记「背压差异无人承接（`walk/01` §四 D6……）→ **本批不新增背压机制**，定性归 `api`……**呈主窗定性**……检测＝**人审**」；实读 `walk/01:74` D6＝「无背压声明｜通信契约含背压｜一般」，确实存在且原未承接 |

**闭合计数：12／12 全部闭合**（无「未闭合」；无「改了但不对」——T-6 的 state 侧引用行为号错误另计为新发现 TZ-1，非 T-6 本体未闭合）。

### 6.2 结论（一句话）

**可定稿。** 上轮 12 条发现**全部闭合**（T-1 的 state 侧跨规格收正已**真落地**、`Mapping` 载荷别名删净、字符串前向引用到位）；三道闸**亲跑全绿**；22 值**逐字复核无差**；真源锚点**逐条去原文件核实为真**。新增 4 条**低／疑点**（见 §七；1 条 cross-ref 行为号笔误＋1 条须辨明的口径张力），**均非阻断项，建议同批或后续随修**。**无「卡须回阶段 2 重做」的结论**（T-10 卡级欠账已随批补齐）。

### 6.3 建议先修项（非阻断）

1. **TZ-1**（`state.md:70` 行为号笔误）——建议随本批改为 `行为 5`。
2. **TZ-2**（行为 4「wire 帧 id＝当前游标值，可与前帧相同」vs 行为 5「cursor＝下一帧 seq」）——建议补一句辨明（wire 帧 id 的确切取值＋客户端仅从事件帧续传），消除零上下文实现者的两可读法。

## 七、新增发现清单（复审轮）

| 编号 | 严重度 | 发现 | 证据锚点 |
|---|---|---|---|
| **TZ-1** | 低（改了但引错） | **`state.md` 新写的 `cursor` 注引错行为号**：`state.md:70`＝`cursor: int  # 全流单调断线游标（＝下一帧 seq；语义真源 specs/transport.md 行为 3／4）`。但「cursor＝**下一帧** seq（排他）」这一定义实在 `transport.md:83`**行为 5**；`行为 3`（`:81`）只讲 `seq` 全流单调、`行为 4`（`:82`）只讲 `id＝seq` 与 wire 帧不推进游标，**均未给「下一帧/排他」语义**。同批新增的模块卡 `modules.md:414` 注释「cursor＝下一帧 seq，排他」**未引行为号**，无此误 | `specs/state.md:70`；`specs/transport.md:81,82,83`；`specs/modules.md:414` |
| **TZ-2** | 低（疑点，须辨明） | **行为 4 与行为 5 的 wire 帧 `id` 口径存张力（未证实是否有意）**：行为 4（`transport.md:82`）写「wire 三帧不推进游标（session／done／error 的 `id` 写作**当前游标值**，**可与前帧相同**）」；行为 5（`:83`）定义「`cursor`＝**下一帧的 `seq`**」且「`cursor = id + 1`」。若「游标值」＝下一帧 seq，则 wire 帧 `id` 应比前一事件帧 `id` **大 1**，不会「与前帧相同」（两处措辞不能同真）；且客户端若以 wire 帧 `id` 回送 `Last-Event-ID`，`cursor = id + 1` 会**跳过一帧**（如 session 帧 `id`＝0 → cursor＝1，跳过 `seq`＝0 的首帧）。疑为「客户端只从事件帧续传」的隐含约定，但规格**未显名**。注：本疑点**非** T-6 未闭合（T-6 本体已闭合），系其旁生的措辞两可 | `specs/transport.md:82,83`；`specs/transport.md:110`（`::frame_id_equals_cursor` 断言） |
| **TZ-3** | 低（疑点，未证实） | **`transport.md:4` 来源行引 `specs/persistence.md 行为 12`，与本块关系不明**：`persistence.md:148` 行为 12 实为「**旧检查点／旧黑匣子如实读入**（`pin-30` 回放面）」，本规格（transport）**无任何行为**取自该面；与「帧内不出现原始异常／瘦指针落盘」相关的是 `persistence.md:150` **行为 14**（落盘失败 fail-closed、发帧实施口＝transport）。疑为笔误（12↔14）或另有所指，**未证实**。该引在 `ref_resolvable` 可解析（`行为 12` 存在），闸不报 | `specs/transport.md:4`；`specs/persistence.md:148,150` |
| **TZ-4** | 低 | **挂钩表与验收测试对同一条测试的措辞不一致**：挂钩表 `transport.md:155`＝「事件名闭世界**九类**（`blackbox` 同列）｜测试 `::event_kinds_closed_world`」；而验收测试 `transport.md:106` 把同一 `::event_kinds_closed_world` 描述为「事件名闭世界**十二值**」（行为 1 `:79` 亦为十二值＝`EVENT_KINDS ∪ WIRE_FRAMES`）。同一测试标识两种口径，易致织网争议 | `specs/transport.md:79,106,155` |

**新增计：4 条——高 0／中 0／低 4（其中 TZ-2／TZ-3 标「疑点」）。** 均**不阻断定稿**。

### 7.1 16 问复跑逐条结论

1. **十节齐＋标题逐字**：**无发现**。`grep -n "^## " specs/transport.md`＝目标:7／不做什么:11／触及的模块:25／接口定义:34／框架与依赖红线:68／行为约定:77／不降级与静默禁令:95／验收测试:102／依赖与风险:127／与闸的挂钩表:143，与 `docs/spec-format.md` §二之二（`:33-34`）逐字同。
2. **行为可 assert／含糊词**：**无发现**。`grep -nE "尽量|合理|必要时|视情况" specs/transport.md`→**exit 1（0 命中）**；行为 1–15 每条带【断言：…】。
3. **数字裸值**：**无发现**。数字项均带真源／为标识符（十二值:40、九值:53／:60、二十二值:62、0 起:81、三行＋空行:80）；无配置裸字面。
4. **不做什么「由谁承担＋锚点」**：**无发现**。9 行俱带（含新增 `:22` session 行）；`:17` 锚「同上」略弱（非阻断，承上轮观察）。
5. **框架红线闸名真存在／source 真覆盖 transport**：**无发现**。逐条实读 `tools/importlinter_v2.toml`：**R5b:103／R6:110／R7:116** 的 `source_modules` **均含** `appv2.runtimev2.transport`；R5:97 source＝`appv2.runtimev2`（含 transport）。实跑三条 KEPT。
6. **不降级与静默禁令**：**无发现（T-2／T-4 已闭合）**。`:97`「合法降级路径：无」；`:98` 四条不得静默各配断言；`:99` 失败披露锚改准；`:100` 脱敏硬要求。
7. **验收测试每行绑标识＋边界／保留集**：**无发现**。18 行全绑 `tests/domains/test_v2_transport.py::<id>`（`:106-123`）；`:122`【边界集】／`:123`【保留集】俱在。
8. **挂钩表「已真跑」属实**：**无发现（T-3 已闭合）**。**亲跑**：`uv run python tools/check_specs.py`→PASS（exit 0）；`uv run python tools/ref_resolvable.py check`→17 份规格可解析（exit 0）；`uv run lint-imports --config tools/importlinter_v2.toml`→`Contracts: 18 kept, 0 broken`（exit 0）。`transport.md:150-152` 三行「已真跑」**属实**。
9. **与 `walk/` 决策冲突**：**无发现**。§01-A（游标全流单调:39）→行为 3/4/5 ✔；§01-D（:42）→行为 9/14 ✔；§01-B/C→「不做什么」正确排除 ✔；`D6` 无背压已由风险 9 承接（T-12）；`判断归责表.md`（程序判结构/模型判语义）→行为 15 零判断 ✔；`00-设计总纲` §二 总纪律 ✔。
10. **覆盖（`S6`／`P9a1` T-P9a1-01…35）**：**无发现（T-5／T-9 已闭合）**。`:22` 承接 07/08（session）；行为 6 `:84` 正名键集归发射方（06/29/30 属本块透传面）；33 →行为 13 真锚；12/13/14/32/34/35 正确排除归 `api`；未见把别块事写进来（`session` 已由「漏项」转为「显名排除」）。
11. **总纪律残留**：**无发现**。行为 15（`:93`）明排词表/正则语义判定、模型调用、落盘。
12. **与模块卡一致**：**无发现（T-1／T-10 已闭合）**。职责 `transport.md:9`↔卡 `modules.md:406`；公开面 `:42-57`↔卡 `:411-421`（含补入的 `closed`）；依赖 `:129`↔卡 `:427`＝`state`。
13. **与已定稿规格逐字对账**：**有发现——TZ-1（state.md:70 行为号笔误）**。`AskReason.kind` 映射（`preconditions.md:47,52`）↔`ASK_FRAME_KINDS`（`transport.md:57,64`）**对得上**；`state.md` 行为 12（notice 恰三键）↔`transport.md:85` 行为 7 **一致**；`persistence.md` 行为 14（fail-closed、发帧口＝transport）与本规格失败披露**不冲突**。唯 `state.md:70` 的 cursor 注引 `行为 3／4` 应指 `行为 5`（TZ-1）。
14. **钉登记全表扫**：**无发现（T-3／T-11 已闭合）**。`pin-29`（`04a` 第 29 行「挂起→resume 闭环…kind 判别字段」）↔`transport.md:158` 同物、分工清（帧面本块／闭环面 `agent-loop.md`）、P0 对；`pin-09` ↔`:159` 同物、P1 对；`pin-27` **不登记为正确**（风险 10 辨明）。漏登核查：`pin-02`（答案面无据差值）／`pin-04`（发射 JSON 进答案面）／`pin-10`（citation 落账）均属 `answering`／`verification`，**不应登本块**（本块只搬帧）——**无应登而漏登项**。
15. **真源引用真实且该节真有事实**：**无发现（T-2／T-7 已闭合）**。逐条核实为真：`S6` §六 `:91`（边界-2 失败腿）✔；`P9a1` T-P9a1-33（`:145`）／T-P9a1-27（`:133`）／T-P9a1-07（`:104`）／T-P9a1-06·29·30（`:100,138,139`）✔；`recon/K` R-K-49（行为 5 引用）✔；`walk/裁决表.md` §01-A/§01-D（`:39,42`）✔；22 值**逐字实测相符**。唯 `transport.md:4` 来源行 `persistence.md 行为 12` 存疑（TZ-3，来源清单非内联锚）。
16. **卡级问题（只报不改）**：**无发现**。`## transport` 卡公开面已含 `closed`（`modules.md:416-417`，T-10 已补）；职责/边界/依赖三面与规格一致；卡注 `:423-424` 自洽。**无「卡须回阶段 2 重做」的结论**。

---

## 八、复审轮新增发现的 L0 处置（2026-10-15）

| 编号 | 处置 | 落法 |
|---|---|---|
| **TZ-1**（低，笔误） | **采纳** | `specs/state.md` 的 `cursor` 注把语义真源写成「`specs/transport.md` 行为 3／4」，实为**行为 3（`seq` 单调）＋行为 5（`cursor` 排他）**——已改准 |
| **TZ-2**（低，疑点） | **采纳 → 补一句辨明** | 行为 4 把 wire 帧的 `id` 值写实：「写作**当前游标值**（即紧随其后会被消费的下一个 `seq`，与 `cursor` 同义；故可与前帧相同、且不改动续传位置）」——消除与行为 5 的措辞张力 |
| **TZ-3**（低，疑点） | **采纳** | 来源行把 `specs/persistence.md` 的引节由**行为 12**（旧检查点回放，与本块无直接关系）改为**行为 14**（失败 fail-closed／发帧实施口＝transport），名副其实 |
| **TZ-4**（低） | **采纳** | 同一测试标识两处计数口径不一（挂钩表「九类」vs 验收「十二值」）→ 统一为「**事件名闭世界（九 runtime ＋ 三 wire ＝十二值）**」，并保留「九类口径真源＝`synth/S3` C-05／C-10」的说明 |

**净结果**：复审 12 条**全部闭合**（无未闭合、无「改了但不对」）；新增 4 条（全低）**全部采纳并清**。复审结论＝**可定稿**（两条建议随修项已在本批清掉）；**无「卡须回阶段 2 修改」的结论**。

### 八之二、留痕

- 本块跨规格动作两处（已记主窗路径）：① `specs/state.md`（已定稿）的 `SseEvent` 表示收正（删 `Mapping` 载荷别名 → 字符串前向引用）；② `specs/modules.md` 两处卡面（`## transport` 补 `closed`＋公开面收正；`## state` 无关）。
- 呈主窗两项：① `eng/04a` 的 `pin-27` 钉文措辞建议改准为「**跑批记录** `frozen_date` 全在场」（该钉的「帧」经码面取证＝跑批 jsonl 记录，非 SSE 帧）；② **背压**差异（`walk/01` §四 D6）定性归 `api`（SSE 流桥）——需主窗定性后落地登记。
