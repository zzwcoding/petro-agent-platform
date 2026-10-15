- 日期：2026-10-15 ｜ 状态：**评审发现清单（待 L0 逐条处置）**
- 本清单只产发现，不修改任何现存文件。

## 一、结论摘要

1. **版式骨架合格**：`specs/persistence.md` 十节齐、标题逐字、顺序正确；`uv run python tools/check_specs.py` 本地实跑 **PASS（0 警告）**。行为约定全文**无**含糊词（`grep -nE "尽量|合理|必要时|视情况"` exit 1）。
2. **三道闸实跑全绿**：`check_specs.py` PASS（0 警告）｜真源引用闸 `tools/ref_resolvable.py check` 绿（15 份规格）｜边界闸 `uv run lint-imports --config tools/importlinter_v2.toml` **Contracts: 18 kept, 0 broken**（R4／R5b／R6／R7／R8 全 KEPT）。挂钩表「R5b／R6／R7 已真跑」属实。
3. **一处 L0（跨规格公开类型冲突）**：`MaterialRef` 同名公开类型两套字段——`specs/persistence.md:69-72`＝`{ref, bytes, sha256}`，已定稿 `specs/execution.md:51-54`＝`{handle, summary, row_count}`（`specs/answering.md:57` 明标与 execution 字段口径对齐）；**两卡的公开接口都没定义 `MaterialRef` 字段形状**（`modules.md:440-441`／`:47`）——`put_ref／read_ref` 的返回/入参即以该类型为公开面（**P-1**）。
4. **一处高（审计计数三处不一＋自相矛盾）**：`specs/persistence.md:108` 称 `agent-loop.md` 行为 8 的「四事件」展开为**七值**，但其自列展开（创建 1＋三态收口 2＋拒答 1＋审批决定 2）＝**6≠7**；且 **ban_exempt（禁用词豁免）不在 `agent-loop.md:147` 的四事件内**。旁证：`walk/16:12` 现状数**六类**、`recon/J` R-J-05 数**七值**、R-J-05 自身疑点 D-J-04 记注释「四事件六值」陈旧（**P-2**，须裁）。
5. **四处中**：挂钩表把「十节标题齐备」误挂 spec gate（**P-3**，实读 `check_specs.py` 只校 `## 触及的模块`／`## 验收测试` 两节）；`pin-30` 分工声明不精确、疑似两头都认（**P-4**）；卡承诺「检查点表与读写入口」但公开接口无检查点行级读写入口（**P-5**）；卡未承载五个公开类型的字段形状（**P-6**）。
6. **五处低**：`synth/S5`「三条盘」标签与真源不符（**P-7**）；不做什么内 INV-2 只读锚点错挂 `walk/00 §二`（**P-8**）；`AuditRecord` 无显式 `run_id` 但行为 9 要求可聚合（**P-9**）；两处机读信号/真源不全（**P-10**）；三处职责口径张力（**P-11**）。
7. 计数：**11 条**发现——`L0×1`（P-1）／`高×1`（P-2）／`中×4`（P-3…P-6）／`低×5`（P-7…P-11）。**结论：不可定稿**（P-1/P-2 须先处置）。**卡须回阶段 2**（P-1 MaterialRef 定形；P-5／P-6 公开面字段形状）。

## 二、发现清单表

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| P-1 | **L0** | **跨规格公开类型同名两套字段（卡未定形）**：`persistence.MaterialRef`＝`{ref: str, bytes: int, sha256: str}`（:69-72）；已定稿 `specs/execution.md:51-54` `MaterialRef`＝`{handle: str, summary: str, row_count: int}`；`specs/answering.md:57` 明写「与 `specs/execution.md` 的字段口径**显式对齐**」。二者为**同名公开类型**（`put_ref(blob)->MaterialRef`／`read_ref(ref: MaterialRef)`，卡 `modules.md:440-441`），字段名（`ref` vs `handle`）与字段集均不同，且**两张卡（`## persistence` :433-444／`## execution` :213-218）都没有定义 `MaterialRef` 的字段形状**——真源留白，实现侧对不上口 | `specs/persistence.md:41-43,69-72,89,112`；`specs/execution.md:47,51-54`；`specs/answering.md:57`；`specs/modules.md:440-441`、`:217` | **回阶段 2**：在卡面（或明标唯一真源）定 `MaterialRef` 字段形状；两规格按定形对齐（`ref`/`handle` 必统一，字段集须一致）。若判「执行规格为准、仅改 persistence 文本」，可降为高——**但卡面留白须补** |
| P-2 | 高 | **审计计数自相矛盾＋跨规格冲突（须裁）**：`specs/persistence.md:108` 称 `agent-loop.md` 行为 8 的「四事件」是**分组口径**（创建／三态收口／拒答／审批决定）并「按 action **展开为七值**（三态收口＝完成／失败**两值**、审批决定＝批准／驳回两值）」——照其自列展开＝`1+2+1+2 = 6 ≠ 7`。且 **`ban_exempt`（禁用词豁免，七值之一）不在 agent-loop 行为 8 的「四事件」内**（`agent-loop.md:147` 四事件＝run 创建／三态收口／拒答收口／外表审批决定；`grep 豁免\|ban_exempt specs/agent-loop.md` 零命中）。旁证三处计数不一：`walk/16:12`（现状审计＝**六类**：建任务／完成／失败／拒答／禁用词豁免／外表审批决定）、`recon/J` R-J-05（**七值**，:101）、R-J-05 自身疑点 D-J-04（:104，`audit.py` 注释「action 闭世界（**四事件六值**）」陈旧）。**「四事件」本身即现状陈旧说法**，不可当分组真源 | `specs/persistence.md:108`；`specs/agent-loop.md:147`；`docs/runtime-refactor/walk/16-收尾-归档.md:12`；`docs/runtime-refactor/recon/J-存储留痕与网关缝.md:101,104` | **须裁**：以 R-J-05 **七值**为 action 闭世界唯一真源；删/改「agent-loop 四事件展开为七值」的对账句（改述为「按 R-J-05 七值；`agent-loop.md` 行为 8『四事件』为现状陈旧口径、漏 `ban_exempt`」）；涉及已定稿 `agent-loop.md` → 跨规格修，呈主窗 |
| P-3 | 中 | **挂钩表「十节标题齐备 → spec gate」不实**：实读 `tools/check_specs.py`（`check_spec` :241-279）**只**校验 `## 触及的模块` 表、`## 验收测试` 表（且状态为「草稿」时缺表不 FAIL），**不校验十节标题名/逐字/顺序**；`tools/` 内无任何闸做标题校验（`ref_resolvable.py` 只校被引卡片名/节号可解析）。CI 也只跑 `check_specs.py` | `specs/persistence.md:171`；`tools/check_specs.py:255-270`；`tools/ref_resolvable.py:49-84`；`.github/workflows/ci.yml:32` | 改述：把「十节标题齐备」从 spec gate 名下移出——标「**人审**」或补一条标题机检（`spec-format.md` §二之二 的十节名可落成 AST/正则闸）；`spec gate` 行只保留「触及模块名已声明／验收测试逐行有标识」（该两面具实） |
| P-4 | 中 | **`pin-30` 分工声明不精确（疑两头都认）**：persistence 挂钩表（:182）声明「**读面**；**字段面挂 `specs/state.md`**」，但 `state` 实挂的是**行为面**「后半面（旧 run 对话通道如实空显）」（`state.md:188` 行为 8），**不是字段面**；且 `state` 行为 8 的断言（读入 v1 fixture→不抛错、对话通道空显）与 persistence 行为 12 的断言（:114 读入 v1 fixture→不抛错、对话通道空显）**几乎逐字相同**——同一「对话通道如实空显」两处各写断言 | `specs/persistence.md:114,182`；`specs/state.md:113,188`；`docs/runtime-refactor/eng/04a-应钉行为清单.md:39` | 裁：pin-30 的「旧 run 对话通道如实空显」归**唯一**块（黑匣子回放面归 `persistence`／检查点读入面归何处须定），另一块改为**引用不复述**断言；并修正「字段面挂 state」措辞（state 挂的是行为半面） |
| P-5 | 中 | **卡承诺「检查点表与读写入口」但公开接口无检查点行级读写入口**：`## persistence` 卡职责写「检查点**表与读写入口**」、卡注①写「本块只出框架无关的检查点**表与读写入口**」（`modules.md:429,447`），而 `RunStore` 公开面只有 `load(run_id)->RunState`（整状态恢复）＋`ensure_tables`；`save` 只收 `RunRecord｜StepRecord｜BlackBox`，**不收检查点行**。归 `orchestration` 的 LangGraph saver（`BaseCheckpointSaver` 一族）如何**经 persistence 公开面**读写 `agent_v2_checkpoint/_blob/_write` 三表未交代——若 saver 直持这三表，即绕开「persistence 是表主人」的公开面 | `specs/modules.md:429,433-444,447`；`specs/persistence.md:36-44`；现状 `recon/J` checkpoint 三表（:110-112）与 `PgCheckpointer` 读面（:315-332） | 卡＋规格补检查点读写入口（如 `checkpoint(...)`／行级 get/put），或卡注明标「saver 经 persistence 的哪一面写表」——把「框架无关入口」落成可调用形状 |
| P-6 | 中 | **卡未承载公开类型字段形状**：persistence 公开签名引用 `RunRecord`／`StepRecord`／`BlackBox`／`MaterialRef`／`AuditRecord` 五类，但 `## persistence` 卡的公开接口段（`modules.md:433-444`）只列 `RunStore` 八方法与 `audit`，**五类的字段形状无卡面真源**；`RunState` 在 `## state` 卡有字段形状（对比项）。同 state 评审 **S-2**「卡缺公开类型」判例的轻量版（无对侧冲突，故暂记中） | `specs/modules.md:433-444`；`specs/persistence.md:46-80`；先例 `docs/runtime-refactor/spec-review/state-评审.md:19`（S-2） | 卡面补五类形状骨架（或以卡注声明「字段形状以 `specs/persistence.md` 为准」）；若要求卡面定形，按 S-2 判例可升 L0 |
| P-7 | 低 | **「三条盘」真源标签与真源不符**：persistence 两处引「`synth/S5`（三条盘）／`synth/S5` 的三条盘口径」，而 `synth/S5` §三标题写「持久化面（**三条盘**）」但**表列 5 盘**（checkpoint／runs／steps／blackbox／audit_log），且 `S5` 覆盖自检自写「持久化面 **5 盘**」——真源自相矛盾，persistence 沿引了错的计数 | `specs/persistence.md:4,154`；`docs/runtime-refactor/synth/S5-RunState字段矩阵.md:90,125` | 改述为「`synth/S5` §三 持久化面（**5 盘**）」或删该计数（横切事实只引不复述） |
| P-8 | 低 | **不做什么内锚点语义不符**：「业务数据（油田数据）的任何写入｜**不做**（INV-2 全程只读）」锚 `walk/00-设计总纲.md` §二，但 §二 是**总纪律**（「凡语义判断一律交模型；程序只做机械分派与结构约束」），**不是 INV-2 只读红线真源**（真源引用闸只判路径可解析，判不到「该节里是否真有那条事实」） | `specs/persistence.md:21`；`docs/runtime-refactor/walk/00-设计总纲.md:11-18` | 换锚到 INV-2 真源（ADR-0004／合同册只读红线）或删该锚；同段 row8（语义判断归模型）锚 `判断归责表.md` 正确，可作对照写法 |
| P-9 | 低 | **`AuditRecord` 无显式 `run_id`，但行为 9 要求审计记录携 `run_id` 可聚合**：`AuditRecord`＝`{who, scope, action, authorization, facts, evidence}` 无 `run_id` 字段，而行为 9（:111）断言「run／步／黑匣子／**审计**四类记录**都携 `run_id`**……按 `run_id` 聚合四类记录无遗漏」——现审计 `run_id` 落 `meta`（`recon/J` R-J-68 :623-627），新形状里落点未指明（`scope` 字符串内？`evidence` 内？） | `specs/persistence.md:73-79,111`；`docs/runtime-refactor/recon/J-存储留痕与网关缝.md:622-627` | 明指 `run_id` 落点（如 `scope="run"` 时携 `run_id`，或 `evidence` 设固定键），并把该键纳入行为 9 断言 |
| P-10 | 低 | **两处机读信号/真源不全**：①行为 4（:106）「重复归档不覆盖并如实记账（幂等跳过 ＋ **机读信号**）」**未指明信号落点**（哪一字段/表）；②行为 13（:115）「摘要截断长度真源 R-J-06」（审计 120）——但**黑匣子转写文本**的截断长度真源实为 `recon/J` **R-J-60/R-J-62**（`_head` 96／title 30/60／digest 80／source 40），未引；③行为 8（:110）引 `synth/S6` 为「核验对账机读字段」真源，但 `S6:21` verdict `verify` 载荷 6 键（`subtype,supported,rewritten,split,cited,attribution`）**不含** `delivered_rows/obs_rows`（该字段真源＝`specs/verification.md` 行为 11 ＋ `arch/P7a` A-P7a-38） | `specs/persistence.md:106,110,115`；`docs/runtime-refactor/recon/J-存储留痕与网关缝.md:102`（R-J-06）、`:538-541,557`（R-J-60/62）；`docs/runtime-refactor/synth/S6-事件与帧目录.md:21`；`specs/verification.md:80` | ①补跳过记账落点；②补黑匣子转写截断长度真源；③`S6` 改述为「step payload 面承载」真源（或删），核验字段真源只留 `verification.md` 行为 11 |
| P-11 | 低 | **三处职责/口径张力**：①行为 14（:116）括注「**发帧／发通知由 `orchestration` 承接**」与不做什么 row4（:18）「事件与帧的发射 → `transport`」口径不一（承接协调方 vs 实施发射口未区分）；②行为 2（:104）在 persistence **把守一处状态迁移方向**（`waiting_ask→running`），与不做什么 row1（:15）「**状态迁移决策** → `orchestration`」措辞张力（现状 `store.mark_running` R-J-17 唯一合法转移先例可依，宜标为结构约束）；③卡注①（:447）把 saver 归 `orchestration`，但 `## orchestration` 卡职责（:302）「**图装配与路由、命令受理与执行器、挂起恢复**」**未显名**「检查点 saver 组合」——靠「图装配」一词间接承接 | `specs/persistence.md:18,104,116`；`specs/modules.md:302,447`；`docs/runtime-refactor/recon/J-存储留痕与网关缝.md:200-201`（R-J-17） | ①发帧实施口＝`transport`、编排层只承接协调；②状态方向把守标注为「结构约束（现状先例）」；③`orchestration` 规格定稿时显名「检查点 saver 组合本块框架无关入口」 |

## 三、16 问逐条回答

**1 十节齐＋标题逐字？** **无发现。** `## 目标`(:7)／`## 不做什么`(:11)／`## 触及的模块`(:24)／`## 接口定义`(:33)／`## 框架与依赖红线`(:92)／`## 行为约定`(:101)／`## 不降级与静默禁令`(:119)／`## 验收测试`(:126)／`## 依赖与风险`(:152)／`## 与闸的挂钩表`(:167)——十节齐、逐字、顺序同 `docs/spec-format.md:31-34`；`check_specs` 实跑 PASS。（注：闸其实不校标题名，见 **P-3**。）

**2 行为约定每条能否写成 `assert`／含糊词？** **无发现。** 判 FAIL 的含糊词「尽量／合理／必要时／视情况」全文 **0 命中**（`grep` exit 1）；行为 1–15（:103-117）**每条**均带【断言：…】，且断言落成集合比较／抛错／往返等价／AST 扫描等可机检形。

**3 数字有无裸值？** **无发现（唯 P-2 的计数逻辑问题）。** `grep "[0-9]"` 命中项全为标识符与锚点（`R5b/R6/R7/S5/S6/S3/pin-12/pin-28/pin-30/§二/§七/22/53`），无配置裸值；中文数字「四值／六值／七值」同句带真源（`state`／R-J-05）。

**4 不做什么每条有无「由谁承担＋锚点」？** **无发现（8 行俱带；唯 row7 锚点语义不符，已单列 P-8）。** `:15`→`orchestration`／`agent-loop.md` 行为 8；`:16`→`orchestration`／卡注＋R5b；`:17`→`state`；`:18`→`transport`；`:19`→`gateway_adapter`（记账出口在 `infra`）；`:20`→`execution`／`execution.md` 行为 4；`:21`→引 INV-2；`:22`→`判断归责表.md`。

**5 框架红线闸名真存在／source 真覆盖 persistence？** **无发现（闸侧）。** 逐条核 `tools/importlinter_v2.toml`：**R5b**（:101-105，`source` 第 103 行**含** `appv2.runtimev2.persistence`）、**R6**（:108-111，source 第 110 行含 persistence）、**R7**（:114-117，source 第 116 行含 persistence）——编号真、覆盖真，意图对得上（R5b＝框架、R6＝不引引擎、R7＝不直引 `infra.llm_client`）。唯「模型出口零接触」（:95）单挂 R7 属**部分覆盖**（R7 `forbidden` 只含 `appv2.infra.llm_client`，不禁引 `gateway_adapter`）——但本规格 :98 已独立声明「不引包内其它块 → 无专属闸 → 人审（AST：import 只出现 state／infra）」，**合覆盖成立**（同 `state` 评审 S-9 写法），记为观察、不单列条。

**6 不降级与静默禁令？** **有发现——P-10①。** `:121` 明写「合法降级路径：**无**」；`:122` 三处信号（截断／归档跳过／写失败）里有断言的是截断（行为 13）与写失败（行为 14），归档跳过的「机读信号」落点未指明（P-10①）；`:123`「不许自述完成」；`:124`「审计不可改写」。**完成判定归 `orchestration`** 与决策真源口径一致（判断归责表「收尾·完成判定＝程序」／`agent-loop.md`「提交完成的是本块（依据核验结果）」，`orchestration`＝程序侧）——无发现。

**7 验收测试（每行标识／边界集保留集）？** **无发现。** 19 行**全部**绑 `tests/domains/test_v2_persistence.py::<id>`（:130-148）；`:147`【边界集】、`:148`【保留集】两行俱在；`:150` 有测试文件归属注（新建文件，与旧码 `appv2/runtime/{store,checkpointer,blackbox,audit}.py` 测试形状不同的说明）。

**8 与闸的挂钩表（填了没／接不上写原因／「已真跑」属实否）？** **有发现——P-3。** 表已填（:169-187）；「已进 CI」属实（`.github/workflows/ci.yml:32`＝`check_specs`、`:34`＝`ref_resolvable`）；「已真跑」属实（本子代理实跑 `lint-imports` **18 kept, 0 broken**，R5b/R6/R7 全 KEPT）；`:176`／`:177`／`:186`／`:187` 四处「人审＋原因」齐备。**唯 :171 行「十节标题齐备 → spec gate」不实**（闸不校标题名，P-3）；`:173-175` 三行「已真跑」表述准确。

**9 与 `walk/` 决策是否冲突？** **有发现——P-2（跨 `agent-loop`／`walk/16`／`recon/J` 的审计计数）。** 逐条比对：`walk/16` §七 Q-A（完成判定归程序）→ 不降级 :123（orchestration 提交）✔；Q-B（黑匣子只追加）→ 行为 1③＋行为 4 ✔；Q-C（审计四要素）→ 行为 5（四要素齐备）✔；`裁决表.md` §16 三行同 ✔；项目级裁决 #1–#13：`#12/#13`（语义交模型）→ 行为 15 零判断 ✔、`#7`（新建 runtimev2）→ 目录 ✔；`判断归责表.md`（收尾·完成判定＝程序；语义类交模型）→ 行为 15／不降级 ✔；`walk/00` §二 总纪律（不作词表替代语义）→ 行为 15 ✔（但 row7 误锚 §二，P-8）。**唯审计计数 P-2 为必须裁的冲突。**

**10 覆盖（`walk/16` 全部判断点／`synth/S1` H13）？** **有发现——P-4／P-5。** `walk/16` 三判断点 Q-A/Q-B/Q-C 全落（见 9）；`synth/S1` H13「存储·黑匣子·审计」（`S1:48`）＝`RunStore/checkpointer/blackbox/审计写口`——persistence 触及模块与接口覆盖（`RunStore` 四读口＋`put_ref/read_ref`＋`audit`）；H13 挂的票（V2-20 审计闭环／V2-33 run_id 盖章／V2-54 黑匣子观测面／V2-55 防膨胀／V2-73 历史读口）在行为 1/4/9/11 与 `arch/P4a2` 源行有落点。**越界：未见**（触及模块 `persistence/state/execution/orchestration` 均在册，写法为「只出形状/入口」）。唯检查点 saver 归位后，**读写入口未落成公开面**（P-5）、`pin-30` 与 `state` 双登（P-4）。

**11 总纪律残留（程序替模型判语义）？** **无发现。** 行为 15（:117）明文排「无词表／正则语义判定、无模型调用」；本块无「若句中出现 X 词就 Y」形设计（判据均为集合成员／抛错／往返／前缀延伸／AST 扫描等结构判）。

**12 与模块卡一致（职责／公开接口／依赖）＋卡级修正自查？** **有发现——P-1／P-5／P-6。** 一致项：职责 :9＝卡 `modules.md:429`；`RunStore` 八方法＋`audit` 与卡 `:433-444` 逐条对得上（`self` 记法差异非语义差）；依赖 :154（模块 `state`、外部 `infra`）＝卡 `:450-452`。**卡级修正自查**：①「saver 归 orchestration」——与 **R5b** 自洽（框架只许活在 orchestration），与 `## orchestration` 卡职责「图装配」可间接承接但**未显名**（P-11③）；②「业务面只读、簿记表唯一写面」——与规格目标 :9 与 :99／:109 一致 ✔；③公开面补全（`run/steps/blackbox/put_ref/read_ref/ensure_tables`）——卡与规格**逐条在** ✔，但卡面**未定义这五类公开类型的字段形状**（P-6），且**未给检查点行级读写入口**（P-5），`MaterialRef` 命名/字段与 `execution` 冲突（P-1）。

**13 接口与已定稿规格逐字对账？** **有发现——P-1（独立发现）／P-2（④）。** ① `RunState` 引用与 `specs/state.md` 一致（persistence 只以 `load` 返回，不复述字段）✔；② `RunRecord.status` **闭世界＝`state.RUN_STATUS_KINDS`（四值）**，`state.md:89` 亦写「四值」、真源 `recon/I2a` RUN×4（running/waiting_ask/completed/failed）✔——未另立一套值；③ `StepRecord.step` **＝`state.STEP_KINDS`（六值）**，与 `state.md:89` 「六值」、`recon/I2a` STEP×6（decision/discover/execute/observe/verify/answer）✔；④ 审计「四事件 vs 七值」——**两处实为两套计数**（四事件分组本身就是漏 `ban_exempt` 的陈旧说法），**须裁**（P-2）；⑤ `delivered_rows/obs_rows` 与 `specs/verification.md` 行为 11 一致（persistence 不复述字段名、只引行为 11，符合「横切事实只引不复述」）✔——唯引 `synth/S6` 作真源偏松（P-10③）。**另发现任务清单外的冲突：`MaterialRef`（P-1）。**

**14 钉（pin）登记？** **有发现——P-4。** ① 登记内容与钉原文同物：`pin-12`（`04a:21`「verify 对账机读字段（delivered_rows/obs_rows）入 step payload」）↔ persistence 挂钩表 :180「**落盘面**——字段面在 `specs/verification.md`」✔；`pin-28`（`04a:37`「run_id 全盖章＋逐题 ledger_run_ids 与 jsonl 等值」）↔ :181「**落盘面**；全盖章面挂 `specs/agent-loop.md`」✔；`pin-30`（`04a:39`「compaction＋v1 旧 run 黑匣子回放 dialogue 通道如实空显」）↔ :182 只取后半面「回放读面」——**分工声明与 state 实挂面不符**（P-4）。② **漏登核查**：`pin-25`（cached_tokens 透传 calllog JSONL）／`pin-27`（冻结时钟 EVAL_FROZEN_DATE＋帧 frozen_date）——经核**不属本块**：calllog/调用记账归 `gateway_adapter`（本规格不做什么 :19「记账出口在 `infra`」；卡 `modules.md:461` 职责「模型调用唯一出口桥…」＋测试计划「记账 caller 归因」）、冻结时钟归 `gateway_adapter`「评测时钟」（卡 :461）与帧面 `transport`——**不登记正确、非漏项**（唯一卡级观察：`## gateway_adapter` 卡职责行未显名「记账/calllog」）。与「落盘／读回／审计／黑匣子／引用载体」相关的其余钉（如 pin-09／pin-15／pin-22/23/24/26/29）实质均为他块行为面，本块无应登面。③ 钉号/优先级无写错（`pin-12` P1、`pin-28` P1、`pin-30` P2，与 `04a:5` 及各行一致）。④ 分工：`pin-12`／`pin-28` 分工清楚（落盘面 vs 字段面/全盖章面），**无两头都认**；唯 `pin-30` 的分工与 `state` 实挂面不合（P-4）。

**15 真源引用是否真实存在且该节里真有那条事实？** **有发现——P-7／P-8／P-10②③。** 逐条核实为真：`recon/J` **R-J-02**（蒸馏白名单 20 键 tuple，:85-87）✔；**R-J-05**（action 闭世界**七值**，恒 `agent_v2.*` 前缀，:99-101）✔；**R-J-06**（`SUMMARY_LIMIT=120`，:102）✔；`synth/S3` **C-07**（`RunState schema_version` 真值＝**3**，:22）✔；`walk/16` §七 **Q-B**（:77「改：黑匣子归档『只追加、不原地改』」）／**Q-C**（:78「要：审计按四要素补齐字段」）原文真 ✔；`synth/S1` **H13**（:48）✔；`arch/P7a` A-P7a-37「不许静默」真实（经 `state`／`agent-loop` 既有引用交叉印证）。**不实/不符**：`synth/S5`「三条盘」（真源实为 5 盘，P-7）；`walk/00 §二` 作 INV-2 只读真源（P-8）；黑匣子转写截断长度真源未引 R-J-60/62（P-10②）；`synth/S6` 作核验对账字段真源偏松（P-10③）。

**16 卡级问题（只报不改）？** **有发现，均须回阶段 2 处置。** ① **`MaterialRef` 命名/字段两规格冲突、卡面留白**（P-1，**L0**）；② 卡职责承诺「检查点**表与读写入口**」但公开面未落成可调用形状（P-5）；③ 五个公开类型（`RunRecord/StepRecord/BlackBox/MaterialRef/AuditRecord`）字段形状无卡面真源（P-6，同 state S-2 判例的轻量版）；④ `## orchestration` 卡职责未显名「检查点 saver 组合」（P-11③）。**卡级修正①②③本身自洽**（与 R5b 一致；「只读 DB」改准与规格一致；公开面补全属实），**仅**「检查点读写入口」与「公开类型字段形状」两项留白、「MaterialRef」与 `execution` 冲突。职责／依赖／边界三面**未见卡错**。

## 四、闸实跑记录（2026-10-15）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）        # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：15 份规格的真源引用与边界规则编号均可解析。   # exit 0

$ uv run lint-imports --config tools/importlinter_v2.toml
Analyzed 129 files, 508 dependencies.
... （R1–R8 逐条）
R5b ADR-0002 红线① 扩展：框架只许在 runtimev2.orchestration（其余 16 块禁引）  KEPT
R6 runtimev2 各块只经 tools 接触引擎  KEPT
R7 runtimev2 各块只经 gateway_adapter 调模型  KEPT
Contracts: 18 kept, 0 broken.    # exit 0
```

辅助取证命令（关键）：
- `grep -nE "尽量|合理|必要时|视情况" specs/persistence.md` → **exit 1（0 命中）**。
- `grep -rn "MaterialRef" specs/` → `execution.md:47,51,58`（`handle/summary/row_count`）／`persistence.md:42,43,69,89,112`（`ref/bytes/sha256`）／`answering.md:57`（声明与 execution 对齐）。
- 逐条核 `tools/importlinter_v2.toml`：**R5b:103／R6:110／R7:116** 的 `source_modules` **均含** `appv2.runtimev2.persistence`。
- `sed -n '225,280p' tools/check_specs.py` → `check_spec` **只校** `## 触及的模块`、`## 验收测试`；`grep -n "标题\|十节\|##" tools/ref_resolvable.py` 无标题校验（**P-3 依据**）。
- `sed -n '90,98p' synth/S5` → §三标题「三条盘」而表 5 行；`S5:125` 自写「持久化盘 5 盘」（**P-7 依据**）。
- `grep -n "豁免\|ban_exempt" specs/agent-loop.md` → 仅 :127「承载豁免」（INV-1 语境），**审计四事件行（:147）无禁用词豁免**；对照 `walk/16:12` 现状数六类、`recon/J:101` R-J-05 数七值（**P-2 依据**）。

### 未验证清单

1. `tests/domains/test_v2_persistence.py` **不存在**、`appv2/runtimev2/persistence/` 无实现——19 行验收测试只能核标识形态，无法实跑（阶段 5）。
2. 「R5b／R6／R7 已真跑」为**契约空过**（persistence 无实现代码）：契约存在且 KEPT 已实测，「persistence 实现层真合规」待阶段 5。
3. **P-2** 的三处计数中，哪一处为「应然」需 Owner/主窗裁（本清单只证「三处不一＋persistence 自列展开＝6≠7」；`agent-loop.md` 为已定稿，修它对账句属跨规格动作）。
4. **P-1** 的严重度取决于评审对「`MaterialRef` 是否须由卡面定形」的判定：若判「以 `execution.md` 为准、persistence 规格文本对齐即可」，则降为高、可不动卡；若判「公开共享类型须卡面定形」，则按 L0 回阶段 2（本清单标 L0）。
5. **P-4** 中 pin-30「旧 run 对话通道如实空显」的「唯一归属块」未定（黑匣子回放 vs 检查点读入谁主谁引），须裁后才好改分工句。

---

## 五、L0 处置表（逐条清零 · 2026-10-15）

> 按 Owner 排产阶梯（「起草→独立评审→**逐条处置（L0 清零）**→复审→定稿」），规格文本改动由 **L0 直接落笔**；**卡级修正**（窗 A 独有权限）同批落 `specs/modules.md`。

| 编号 | 处置 | 依据／落法 |
|---|---|---|
| **P-1**（L0） | **采纳 → 改名消冲突＋卡面补形** | 裁：**`execution` 的 `MaterialRef = {handle, summary, row_count}` 是「窗口侧材料条目」的既有定形（已定稿、`answering` 已对齐），保持不动**；**本块的载体回执改名 `BlobRef`，键名统一用 `handle`**（与 execution 同源同值），`read_ref(handle: str)` 收字符串——**同一标识两处同名，不再出现「同名类型两套字段」**。规格加对账条（`execution` 产出的 handle 直接喂 `read_ref` 可取回原文）；卡公开面同批改名 |
| **P-2**（高） | **采纳 → 计数只留一个口径** | 裁：**action 闭世界七值**（真源 `recon/J` R-J-05）为**唯一计数真源**；**分组说法不产生第二个数字**——本规格行为 6 改述（删「四事件展开为七值」的错算式，写明类数一律不写）；**已定稿 `specs/agent-loop.md` 行为 8 同批就地改述**（原「四事件」漏 `ban_exempt`，改为「五处留痕＋计数口径＝action 七值」）；`walk/16` 的「六类」为方法粒度分组，同样不再当计数真源（登记不回改） |
| **P-3**（中） | **采纳 → 挂钩表诚实化** | 三份规格（`persistence`／`state`／`agent-loop`）同批改：「spec gate」行收窄为「**验收测试逐行有标识 ／ 触及模块名已声明**（该闸只校这两项）」；新增一行「**十节标题齐备→人审**」并写原因（`check_specs.py` 不校标题名／顺序，仓内无标题闸；降维为一条标题机检＝登记待补）。**其余规格**经 `grep 十节 specs/*.md` 核**无同款行**，无跨规格债 |
| **P-4**（中） | **采纳 → 一个面只挂一块** | 裁：`pin-30` 的**黑匣子回放面归 `persistence`（唯一挂断言）**；`state` 行为 8 改为**只管状态字段读入**（不抛错 ∧ `schema_version` 如实 ∧ `dialogue` 零业务写），并注明回放面在 persistence；两规格挂钩表措辞同步改准（原文「字段面挂 state」不实——state 挂的是行为半面） |
| **P-5**（中） | **采纳 → 补行级口＋改卡** | 卡职责所谓「检查点表与读写入口」原来落不到调用形状。裁：**本块公开面补五个框架无关行级口**（`put_checkpoint_rows`／`checkpoint_rows`／`checkpoint_blobs`／`checkpoint_writes`／`delete_thread`）＋三个行投影类型（`CheckpointRow`／`CheckpointBlobRow`／`CheckpointWriteRow`）；卡注①改述为「编排块 saver **组合本口、不直连表**」；`## orchestration` 卡职责同步显名「**检查点 saver 组合**」 |
| **P-6**（中） | **采纳（弱）→ 卡注定约定** | 不逐类在卡面抄字段（体例与 `## state` 卡一致：卡面只列类名与签名概要）。卡注③新增一句「**公开类型的字段形状以 `specs/persistence.md` 接口定义为准**，并点名列齐八类」——把「卡面留白」变成「明确的指路」，不留真源真空 |
| **P-7**（低） | **采纳** | 删「三条盘」计数（`synth/S5` §三 标题与表内盘数自相矛盾：标题写三条、表列 **5 盘**、覆盖自检亦写 5 盘）——本规格改引「`synth/S5` §三 持久化面」并在依赖行注明「该表列 5 盘，标题『三条盘』为陈旧标注」，符合「横切事实只引不复述」 |
| **P-8**（低） | **采纳** | INV-2 的锚从「总纲 §二」改到**真源 `CONTEXT.md`（INV-2 词条：只读边界——全部工具只读、SQL 只读账号＋白名单 Schema、无任何写动作）**；并在接口定义补一句「`MaterialRef`（窗口侧材料条目）不属本块」 |
| **P-9**（低） | **采纳** | `AuditRecord` **补 `run_id: str`**（范围键），`scope` 保留为「会话线程／子问题域」——行为 9 的「四类记录都携 `run_id` 可聚合」由形状承载，不再是空口断言 |
| **P-10**（低） | **采纳（三处同修）** | ①重复归档的**跳过记账落点**写实（`save` 抛既定异常「已归档」，调用方记 notice、发帧归 `orchestration`）；②**黑匣子转写截断长度真源**补引（`recon/J` R-J-60／R-J-62；审计摘要仍 R-J-06）；③核验对账字段的真源改述为 `specs/verification.md` 行为 11 ＋ `arch/P7a` A-P7a-38，**删掉**指向 `synth/S6` verdict 载荷六键的错引（那六键里没有 `delivered_rows`／`obs_rows`） |
| **P-11**（低） | **采纳（三处同修）** | ①行为 14 口径统一：**发帧实施口＝`transport`、批次协调＝`orchestration`**（与「不做什么」row 4 一致）；②行为 2 明标为**结构约束**（先例 `recon/J` R-J-17），并写清「该不该迁移的决策仍在 `orchestration`」；③（卡面）`## orchestration` 职责已显名检查点 saver 组合（与 P-5 同批） |

**净结果**：11 条**全部采纳**（P-1／P-5／P-6 涉卡、由窗 A 亲改；P-2 连带就地改已定稿 `specs/agent-loop.md` 行为 8；P-3 连带同批改 `state`／`agent-loop` 挂钩表）。**无升 Owner 项**。

### 五之二、修复执行记录（2026-10-15，L0）

- **规格 `specs/persistence.md`**：接口定义（`BlobRef`／检查点行级口＋三类行投影／`AuditRecord` 补 `run_id`）｜行为 2／4／6／8／12／13／14｜不做什么 row（INV-2 锚）｜来源行与依赖行（S5 盘数）｜挂钩表（spec gate 行收窄＋十节行人审＋`pin-30` 分工改准）。
- **卡 `specs/modules.md`**：`## persistence` 公开面（`BlobRef`＋五个行级口＋卡注③字段形状指路）｜`## orchestration` 职责（显名检查点 saver 组合）。
- **同批跨规格**：`specs/agent-loop.md` 行为 8（审计计数口径改「action 七值」）＋挂钩表两行；`specs/state.md` 行为 8（只管状态字段读入）＋挂钩表两行。
- **闸（L0 复跑）**：spec gate PASS（0 警告）｜真源引用闸绿（15 份规格）｜边界闸 18/18 KEPT。

---

## 六、复审结论（独立子代理）

- 日期：2026-10-15 ｜ 复审对象：`specs/persistence.md` 修订稿 ＋ 同批 `modules.md`／`agent-loop.md`／`state.md`
- 纪律：只读＋只追加；本回复跑三道闸均实跑（见 §七末）。

### ① 闭合核验表

| 编号 | 判定 | 证据（实读行号） | 说明 |
|---|---|---|---|
| **P-1** | **未闭合（改了但不对）** | 改名到位：`specs/persistence.md:42`（`put_ref->BlobRef`）／`:43`（`read_ref(handle: str)`）／`:76-79`（`class BlobRef`）／`:119`（同源同值对账条）；卡到位：`specs/modules.md:440`（`put_ref->BlobRef`）。**残留**：`specs/persistence.md:123`＝「**`MaterialRef`** 的原文存放载体」、`:146`（行为 10）＝「`put_ref(blob)` 返回 **`MaterialRef`**；`read_ref(**ref**)`……`ref` 不可解析」。execution 逐字核：`specs/execution.md:47,51-54,58`＝`MaterialRef{handle, summary, row_count}`；`specs/answering.md:57` 声明与 execution 对齐 | 接口段已改对，但**行为 10 与接口注释两处仍用旧名 `MaterialRef`、入参仍写 `ref`**——同一规格内「接口说 `handle`、行为说 `ref`」自相矛盾，且 resurrect 了被裁掉的名字。`BlobRef.handle` 与 `execution.MaterialRef.handle` 的**键名同源**确认（execution 侧确为 `handle`）；`read_ref` 入参类型与文档**不一致**（接口 `handle` vs 行为 `ref`）。**这是唯一未闭合项，必须收尾** |
| **P-2** | **闭合** | `specs/persistence.md:142`（行为 6 改述：计数口径以「action 七值」为唯一真源，不写类数，附「四事件为陈旧口径」说明）；`specs/agent-loop.md:147`（行为 8＝「五处留痕＋计数口径以 action 闭世界七值为准，本处不写类数」）；真源逐字：`recon/J:101` R-J-05＝`agent_v2.run_created/run_completed/run_failed/refused/extable_approved/extable_rejected/ban_exempt` 七值 | persistence 与 agent-loop 行为 8 **只剩一个数字（七值）**；`grep -n 四事件\|六类\|七值\|五处` 中 behavior 面已无第二个口径数字（`agent-loop.md:7`「六类型」指 step 类、无关）。R-J-05 七值逐字对得上。**残留一处**（非行为面）→ 见 **PZ-2** |
| **P-3** | **闭合** | `specs/persistence.md:205-206`／`specs/state.md:178-179`／`specs/agent-loop.md:221-222` 三处同款：「spec gate（该闸只校这两项——十节标题不在其作用面）＋十节标题齐备→人审（原因：`check_specs.py` 不校标题名）」。`grep -n 十节 specs/*.md` 命中**仅这 6 行**，其余规格无同款行 | 移出 spec gate 属实；实读 `tools/check_specs.py:255,267` 只校 `## 触及的模块`／`## 验收测试`，P-3 依据成立。无遗漏同款行 |
| **P-4** | **闭合** | `specs/persistence.md:217`＝「旧 run **黑匣子回放**如实（本块**唯一**挂断言的面；检查点状态字段读入面挂 `specs/state.md` 行为 8）」；`specs/state.md:113`（行为 8＝**状态字段面**：读入不抛错／`schema_version` 如实／`dialogue` 零业务写，并注「对话通道空显断言归 persistence 行为 12」）＋`:189`（挂钩行同口径）；`specs/persistence.md:148` 交叉引 state 行为 8 | pin-30 **只在一处（persistence 回放面）挂断言**；state 已收窄为「状态字段读入面」；两处措辞互为引用、一致。**另发现**：state:189 还称「compaction 半面挂 `context`」→ 见 **PZ-3** |
| **P-5** | **闭合** | 规格五口：`specs/persistence.md:47-51`（`put_checkpoint_rows`／`checkpoint_rows`／`checkpoint_blobs`／`checkpoint_writes`／`delete_thread`）＋三行投影：`:80`（`CheckpointRow`）／`:88`（`CheckpointBlobRow`）／`:95`（`CheckpointWriteRow`）；卡同款：`specs/modules.md:436-443`（同五名／同三类型名）；卡注①改述：`:455`（saver 组合本口、不直连表）；`## orchestration` 职责显名：`:302` | 卡面与规格**逐字对得上**（口名／类型名／`BlobRef` 全一致）。**附带**：接口 `:120` 的硬断言「saver 写操作全经这五口」无验收测试行／挂钩行 → 见 **PZ-4** |
| **P-6** | **闭合** | `specs/modules.md:457` 卡注③＝「公开类型的字段形状以 `specs/persistence.md` 的接口定义为准」，名录 `RunRecord/StepRecord/BlackBox/BlobRef/CheckpointRow/CheckpointBlobRow/CheckpointWriteRow/AuditRecord` 八类；规格 `specs/persistence.md:53-112` 定义全这八类 | 八类名**逐字对得上**；「卡面留白」已变「明确指路」。**唯一瑕疵**：注③「同 `## state` 卡约定」的类比不实 → 见 **PZ-5**（卡级，只报不改） |
| **P-7** | **闭合** | `specs/persistence.md:4` 引「`synth/S5` §三（持久化面）」无「三条盘」；`:188` 依赖行注「该表列 **5 盘**——其标题『三条盘』为陈旧标注，本规格只引该节不复述盘数」。真源核实：`synth/S5:90` 标题「持久化面（三条盘）」而表列 **5 行**（checkpoint／runs／steps／blackbox／audit_log），`:125` 覆盖自检「持久化面 5 盘」 | 沿引错计数已消除，处置与真源自相矛盾的事实一致 |
| **P-8** | **闭合** | `specs/persistence.md:21`＝INV-2 锚改 `CONTEXT.md`（INV-2 词条：只读边界——全部工具只读、SQL 只读账号＋白名单 Schema）。真源核实：`CONTEXT.md:9`「INV-2 只读边界：agent 全部工具只读；SQL 经只读账号＋白名单 Schema；无任何写动作」 | 锚点语义与真源词条逐字相符；原误锚 `walk/00 §二` 已撤 |
| **P-9** | **闭合** | `specs/persistence.md:105`＝`AuditRecord.run_id: str  # 范围键（四类记录同源可聚合）`；行为 9 `:145`＝run／步／黑匣子／审计**四类都携 `run_id`**、按 `run_id` 聚合无遗漏；验收行 `:174` 绑测 | 「四类携 run_id 可聚合」由形状承载，不再是空口断言；范围键与 `scope` 分工写明 |
| **P-10** | **闭合（三处）** | ①`specs/persistence.md:140`（行为 4 跳过记账落点写明：`save` 抛既定异常「已归档」、调用方记 notice、发帧归 `orchestration`）；②`:149`（行为 13 补引 `recon/J` R-J-60／R-J-62；审计仍 R-J-06）——真源核实 `recon/J:539,557` 原文在；③`:144`（行为 8 改引 `specs/verification.md` 行为 11 ＋ `arch/P7a` A-P7a-38，删 `synth/S6` 错引）——真源核实 `specs/verification.md:80` 与 `arch/P7a:99` 原文在场 | 三处落点／真源全部补齐 |
| **P-11** | **闭合（三处）** | ①`specs/persistence.md:150`（行为 14：发帧实施口＝`transport`、批次协调＝`orchestration`）与不做什么 row4 `:18`（事件与帧发射→`transport`）一致；②`:138`（行为 2 明标**结构约束**，先例 `recon/J` R-J-17，决策仍在 `orchestration`）——真源核实 `recon/J:201`「唯一合法转移 waiting_ask→running」；③`specs/modules.md:302` 职责显名「检查点 saver 组合」 | 三处张力全部消解 |

**闭合统计：11 条中 10 条闭合、1 条（P-1）未闭合。**

### ② 结论一句话

**不可定稿。** 必须先修：**P-1 收尾**——`specs/persistence.md:123` 与 `:146` 两处 `MaterialRef`／`ref` 残留未随改名清掉（接口段已改 `BlobRef.handle`，行为 10 与接口注释仍写旧名旧参），同规格内自相矛盾。P-1 的**卡面**本批已改对（`modules.md:440` 已 `BlobRef`），agg 只需规格文本收尾，**无需回阶段 2**。其余为低severity新增（PZ-2…PZ-5，建议同批修、不阻塞）。

---

## 七、新增发现清单（复审轮）

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| **PZ-1** | 中 | **P-1 的未闭合实质（同名残留）**：`specs/persistence.md:123`「`MaterialRef` 的原文存放载体」与 `:146`（行为 10）「`put_ref(blob)` 返回 `MaterialRef`；`read_ref(ref)`」仍用旧类型名与旧入参名，而接口段 `:42-43,76-79` 已改 `BlobRef`／`handle`——同规格内类型名与参数名两套 | `specs/persistence.md:123,146` vs `:42,43,76-79`；`specs/execution.md:47,51-54` | 两处改名收尾：`MaterialRef`→`BlobRef`、`read_ref(ref)`→`read_ref(handle)`、「坏 ref」→「不可解析 handle」；改毕 P-1 即闭合 |
| **PZ-2** | 低 | **审计计数口径在验收行残留第二个数字**：`specs/agent-loop.md:202` 验收测试行标题仍写「**审计四事件**接线」、测试标识为 `::test_audit_wiring_four_events`——P-2 已废「四事件」说法，唯此行文本／标识未同步（`grep 四事件` 于 agent-loop 仅 :147 说明句与 :202 此行两处） | `specs/agent-loop.md:202`；对照 `:147`（已改五处留痕／七值） | 已定稿规格跨规格收尾：改行标与测试标识（如 `test_audit_wiring_action_closed_world`），或注「旧标识，语义随行为 8 已改」（登记）。属主窗跨规格动作 |
| **PZ-3** | 低 | **`pin-30` compaction 半面的归属是悬空指针／疑未登记**：`specs/state.md:189` 挂钩行称「`pin-30` 另两面：回放面挂 `specs/persistence.md`、**compaction 半面挂 `context`**（`synth/S1` H6／V2-79d）」，但仓内**无 `specs/context.md`**，且 `grep -rn pin-30 specs/` 仅命中 `state.md`／`persistence.md` 两处——`context` 侧**并无 pin-30 登记**。04a `pin-30` 原文（`:39`）确为「compaction 摘要化＋v1 旧 run 黑匣子回放 dialogue 空显」两半，compaction 半面**当前无处挂** | `specs/state.md:189`；`ls specs/`（无 context.md）；`grep -rn pin-30 specs/`；`eng/04a:39`；`synth/S1:106`（H6→V2-79d compaction） | 核实 context 规格何时起草：若已起草→补登 `pin-30` compaction 面；若未起草→把 `:189` 改述为前向指针（「待 `context` 规格起草时登记」），不写成已挂 |
| **PZ-4** | 低 | **检查点行级口唯一性的硬要求未挂闸／测／人审**：`specs/persistence.md:120` 断言「saver 路径上出现的写操作**全经这五个函数**（AST／行为双证）」是硬要求，但 `## 验收测试`（`:163-182` 19 行）与 `## 与闸的挂钩表`（`:203-222`）**均无对应行**——按 `docs/spec-format.md` §三.3「每条硬要求要么有闸、要么有测试、要么写人审＋原因」，此条落空 | `specs/persistence.md:120` vs `:163-182,203-222` | 补一行验收测试（如 `::checkpoint_rows_only_write_path`，AST 断言）或补挂钩表人审行 |
| **PZ-5** | 低 | **卡注③的类比不实（卡级，只报不改）**：`specs/modules.md:457` 写「**同 `## state` 卡约定**：卡面只列类名与签名概要」，但 `## state` 卡（`specs/modules.md:268-298`）**无此显式约定**——只以 `class RunState: ...  # 字段形状`（`:275`）的**实践**列类名，未声明「字段形状以规格为准」。两卡「约定」并非同款（persistence 有明文约定、state 无） | `specs/modules.md:457` vs `:268-298`（全卡无「以规格为准」字样；`grep 以规格为准` 仅 :457） | 收尾时二选一：在 `## state` 卡补同款一句，或把 persistence 注③的类比改为「沿 `## state` 卡做法（卡面只列类名）」而不称「约定」。卡级问题，须回阶段 2 权限改 |

**新增计数：5 条**——`中×1`（PZ-1＝P-1 未闭合实质）／`低×4`（PZ-2／PZ-3／PZ-4／PZ-5，其中 PZ-5 为卡级只报不改）。

### 16 问复跑（逐条）

1. **十节齐＋标题逐字**：**无发现。** `specs/persistence.md` 十节齐（`:7,11,24,33,126,135,153,160,186,201`）、标题逐字、顺序同 `docs/spec-format.md`。
2. **每条可写 `assert`／含糊词**：**无发现。** `grep -nE "尽量|合理|必要时|视情况" specs/persistence.md` → **exit 1（0 命中）**；行为 1–15 每条带【断言：…】。
3. **数字裸值**：**无发现。** 命中项全为标识符／锚点／带真源的计数（「七值」携 R-J-05）；无配置裸字面值。
4. **不做什么「由谁承担＋锚点」**：**无发现。** 8 行俱带；row7 锚已修正为 `CONTEXT.md`（P-8 闭合）。
5. **框架红线／闸名覆盖**：**无发现。** `tools/importlinter_v2.toml` **R5b:103／R6:110／R7:116** 的 `source_modules` **均含** `appv2.runtimev2.persistence`；实跑三条 KEPT。
6. **不降级与静默禁令**：**无发现。** `:155`「合法降级路径：无」；`:156` 三处信号（截断／归档跳过／写失败）各有断言。
7. **验收测试（每行标识／边界集保留集）**：**无发现。** 19 行全绑 `tests/domains/test_v2_persistence.py::<id>`；`:181`【边界集】／`:182`【保留集】两行俱在。（唯 PZ-4：接口 :120 的硬断言无对应行。）
8. **挂钩表（填了／接不上写原因／「已真跑」亲自跑）**：**无发现。** 表已填（`:203-222`）；`已真跑` 由本子代理亲跑属实（见末）。唯 PZ-4 指另一处硬要求未入表。
9. **与 `walk/` 决策冲突**：**无发现。** `walk/16` §七 Q-A/Q-B/Q-C（`:77-79`）→ 不降级「不许自述完成」／行为 1③＋4／行为 5，逐条落；`裁决表 §16`（`:191-200`）三行同；`判断归责表:23`（收尾·完成判定＝程序）✔。
10. **覆盖（`synth/S1` H13）／越界**：**无发现。** `synth/S1:48` H13「存储·黑匣子·审计」→ persistence 触及模块与接口覆盖；`:113` 挂票（V2-20/33/54/55/73）在行为 1/4/9/11 有落点；未见越界写别块事。
11. **总纪律残留（程序替模型判语义）**：**无发现。** 行为 15（`:151`）明文排除词表／正则语义判定与模型调用；判据均结构形。
12. **与模块卡一致（职责／接口／依赖）**：**有发现 → PZ-1／PZ-4／PZ-5。** 职责 `:9`＝卡 `modules.md:427`；`RunStore` 八方法＋五口＋`audit` 与卡 `:433-443` 逐条对得上；依赖 `:188`（`state`／`infra`）＝卡。唯规格行为 10／注 :123 用旧名（PZ-1）、检查点口硬断言无挂（PZ-4）、卡注③类比不实（PZ-5，卡级）。
13. **接口与已定稿规格逐字对账**：**有发现 → PZ-1。** `RunState`（本块只以 `load` 返回、不复述字段）✔；`RunRecord.status` 闭世界＝`state.RUN_STATUS_KINDS`（四值）、`state.md:89` 亦写四值 ✔；`StepRecord.step`＝`state.STEP_KINDS`（六值）、`state.md:89` 写六值 ✔；审计口径与 `agent-loop.md:147` 一致（七值）✔；核验字段与 `verification.md` 行为 11＋A-P7a-38 一致 ✔；**独 `BlobRef.handle` 的规格文本引名在 :123／:146 仍作 `MaterialRef`／`ref`**（PZ-1）。
14. **钉登记（全表扫）**：**有发现 → PZ-3。** `pin-12`（`04a:21`，P1）↔ `persistence:215` 落盘面 ✔；`pin-28`（`04a:37`，P1）↔ `:216` 落盘面（全盖章面挂 agent-loop `:233`）✔；`pin-30`（`04a:39`，P2）↔ `:217` 回放面 ✔。钉号／优先级无写错。**漏检**：`pin-25`（calllog）／`pin-27`（冻结时钟）经核不属本块（归 `gateway_adapter`），不登记正确；**唯 pin-30 compaction 半面在 `state:189` 声称挂 `context` 但实际无 `specs/context.md`、无登记**（PZ-3）。
15. **真源引用真实且该节真有事实**：**无发现。** 逐条核实为真：`recon/J` R-J-02（`:87`）／R-J-05（`:101`）／R-J-06（`:102`）／R-J-17（`:201`）／R-J-60（`:539`）／R-J-62（`:557`）；`synth/S5` §三（`:90`，标题三条盘／表 5 盘）；`CONTEXT.md:9` INV-2；`verification.md:80` 行为 11；`arch/P7a:99` A-P7a-38／`:98` A-P7a-37；`synth/S1:48` H13。
16. **卡级问题（只报不改）**：**有发现 → PZ-5。** `## persistence` 卡与规格接口**逐字对得上**（八类名／五口名／三类型名／`BlobRef`）；`## orchestration` 卡职责已显名（`:302`）。**唯** `卡注③:457`「同 `## state` 卡约定」类比不实（state 卡无该显式约定）；**无其他卡错**。「卡须回阶段 2」仅 PZ-5 一项低severity措辞问题，不构成回阶段 2 阻塞。

### 闸实跑记录（复审轮，2026-10-15）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                        # exit 0
$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：15 份规格的真源引用与边界规则编号均可解析。   # exit 0
$ uv run lint-imports --config tools/importlinter_v2.toml
Contracts: 18 kept, 0 broken.                    # exit 0
（R5b／R6／R7 逐条 KEPT；source 含 appv2.runtimev2.persistence）
```

**未验证项**：`appv2/runtimev2/persistence/` 仅 `__init__.py`、`tests/domains/test_v2_persistence.py` 不存在——验收测试只能核标识形态（阶段 5 实跑）；「R5b／R6／R7 已真跑」为契约空过。

---

## 八、复审轮新增发现的 L0 处置（2026-10-15）

| 编号 | 处置 | 落法 |
|---|---|---|
| **P-1 未闭合**（＝PZ-1，中） | **采纳 → 文本收尾** | 规格内两处旧名收净：`:123`「`MaterialRef` 的原文存放载体」→ **`BlobRef`**；行为 10「`put_ref` 返回 `MaterialRef`；`read_ref(ref)`」→ **「返回 `BlobRef`；`read_ref(handle)`」**；错误契约行「ref 不可解析」→「`handle` 不可解析」。全篇复扫：剩余 `MaterialRef` 字样**只出现在对账条**（「与 `execution.MaterialRef.handle` 同源」），是**有意引用他块类型**，非本块类型 |
| **PZ-2**（低） | **采纳** | `specs/agent-loop.md` 验收行改述：「审计四事件接线（…）｜`::test_audit_wiring_four_events`」→「**审计留痕经 `security.audit` 唯一写口（action 闭世界七值，计数只此一个口径）**｜`::test_audit_wiring_action_closed_world`」——**钉住的测试标识同步改名**，避免「四事件」作为第二个数字残留在验收面 |
| **PZ-3**（低） | **采纳** | `specs/state.md` 挂钩表把 `pin-30` 的 compaction 半面登记写**准**：「归 `context`（`synth/S1` H6／V2-79d）——**该规格尚未定稿，待 `context` 规格（窗 B 编写）定稿时登记**」——不把「打算登记」写成「已登记」 |
| **PZ-4**（低） | **采纳** | 「saver 路径上的写操作全经五个行级口」这条硬断言原来只有断言没有落点。补：**验收测试行** `::saver_writes_only_via_port_functions`（标「编排块侧同测」）＋**挂钩表行**「检查点三表写操作只经本块五个行级口」 |
| **PZ-5**（低，卡级） | **采纳** | `specs/modules.md` 卡注③ 删掉不实的类比「同 `## state` 卡约定」（state 卡并无该显式约定），改为自立的直陈：「卡面只列类名与签名概要；字段形状、枚举闭世界、断言在规格里」＋点名列齐八类 |

**净结果**：复审 11 条＝**10 闭合／1 未闭合（P-1 文本残留）**；新增 5 条（中×1／低×4）**全部采纳并清**，其中「必须先修」的 P-1 已收尾。**无升 Owner 项**、**无须回阶段 2 的卡错**（P-1 的卡面本批已改对，PZ-5 属卡面措辞已同批改准）。
