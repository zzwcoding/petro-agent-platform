- 日期：2026-10-15 ｜ 状态：**评审发现清单（待 L0 逐条处置）**
- 本清单只产发现，不修改任何现存文件。

## 一、结论摘要

1. **版式骨架合格**：`specs/state.md` 十节齐、标题逐字、顺序正确；`uv run python tools/check_specs.py` 本地实跑 **PASS（0 警告）**。
2. 两道闸实跑**全绿**：真源引用闸（`tools/ref_resolvable.py check`，14 份规格 0 违规）、边界闸（`uv run lint-imports --config tools/importlinter_v2.toml`，**Contracts: 18 kept, 0 broken**，含 R4／R5b／R6／R7）。
3. **两处「幻影／不实真源」**——最要紧：①`NOTICE_TYPES`（:89/:114）声称「取值与条数真源＝`synth/S6` §一 与 `recon/I2a`」，但两处**都没有**该族（`grep -rn NOTICE_TYPES` 全仓只命中 `specs/modules.md:282` 与 `specs/state.md:89,114`）——所谓「闭世界」无取值真源（**S-1**）；②`Budget` 数值真源挂 `walk/裁决表.md` §06-A「统一预算表」，而 §06-A 仅一行循环上限、**不含**轮内发现／轮内执行／段时长／单工具超时四项，「统一预算表」仓内未落盘为表（**S-3**）。
4. **一处卡级不一致（须回阶段 2）**：接口定义新增公开类型 `class LimitHit`（:77-81），`Convergence.hit` 以其为元素类型（:84），但 `## state` 卡公开接口（`specs/modules.md:274-285`）**无 `LimitHit`**（**S-2**，判 **L0**）。
5. **与已定稿 `specs/agent-loop.md` 的载荷对账逐字一致**（`AskRequest`／`AskChoice`／`RunHandle` 字段名／类型／可空性／枚举全同，对照 `agent-loop.md:50-56`）；`Manifest` 10 字段＝`recon/I2a` 骨架；`RunState` 字段集引 `synth/S5`（53 字段，与卡、`recon/I2b` 实测 53 一致）——**判据 13 无发现**。
6. **应钉面**：登记行为与钉原文大体同一件事（pin-22/23/24/26）；`pin-29` 明收窄为形状面并声明闭环面挂 `agent-loop.md`——**分工清楚，无「两头都认／两头都不认」**。但 `pin-30` 只登记半面未声明另半面去向（**S-5**），且 pin-09／15／28 的**字段面**未声明归属（**S-4**）。
7. 计数：**10 条**发现——`L0×1`（S-2）／`高×1`（S-1）／`中×2`（S-3、S-4）／`低×6`（S-5…S-10）。

## 二、发现清单表

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| S-1 | 高 | **幻影真源：`NOTICE_TYPES` 无取值／条数真源**。规格称「`NOTICE_TYPES`（通知类型）…取值与条数真源＝`synth/S6-事件与帧目录.md` §一 与 `recon/I2a`」，但 `S6` §一 是**事件九类闭世界**（无通知类型族）、`recon/I2a` §一是 22 条常量（`STEP×6／RUN×4／INTENT×10`，**无 `NOTICE_TYPES`**）。所谓「闭世界常量族」只在本卡与规格出现，取值/条数无真源；现状 notice 的 `type` 字面值（`budget_converged`／`material_truncated`／`refused`／`run_failed`）**散在各处、无闭世界常量**（`recon/K` D-K-48／D-K-56 自陈） | `specs/state.md:89`、`:114`；`docs/runtime-refactor/synth/S6-事件与帧目录.md:10-26`；`docs/runtime-refactor/recon/I2a-状态常量与清单.md:16-41`；`docs/runtime-refactor/recon/K-上下文事件指南预算.md:557,613`；`grep -rn NOTICE_TYPES` 仅 `specs/modules.md:282`／`specs/state.md:89,114` | 采纳：先落定该族**取值真源**（`synth/S6` notice 键或新落一处 notice 类型闭世界），否则删该族并声明「通知类型不由本块闭世界把守」；与卡（`modules.md:282`）同批修（**涉卡→回阶段 2**） |
| S-2 | **L0** | **卡与规格不一致（卡缺公开类型）**：接口定义新增 `@dataclass(frozen=True, slots=True) class LimitHit`（`limit: Literal[七值]`／`used`／`cap`），并作为 `Convergence.hit: tuple[LimitHit, ...]` 的**公开**元素类型；`## state` 卡公开接口**只列** `RunState/Manifest/AskRequest/AskChoice/RunHandle/Budget/Convergence`＋常量族＋`check_limits`，**未列 `LimitHit`**。规格自陈「签名以卡为准」（:93）与卡口径冲突 | `specs/state.md:77-84`、`:93`；`specs/modules.md:274-285` | 采纳：**回阶段 2 补卡**（`## state` 公开接口补 `class LimitHit: ...`，同流水 20② 的补件性质）；若认定 `LimitHit` 仅是 `Convergence` 内部表示、无需公开，则改为规格内说明（可不回阶段 2），但不可两处口径并存 |
| S-3 | 中 | **「统一预算表」真源不实（同类幻影）**：`Budget` 数值/缺省真源挂 `walk/裁决表.md` §06-A「统一预算表」；实读 §06-A（`裁决表.md:92`）**只有一行循环上限**（「发现≤10／大循环≤3轮／回炉一次／连续澄清≤6／同参重投即拦」），**不含**「轮内发现／轮内执行／段时长／单工具超时」四项；且「统一预算表」仓内**无同名落盘文件**（`grep 统一预算表` 只见引用）。实际能覆盖全部 7 键的是同行并列的 `recon/K` R-K-72…R-K-78（:458-464）。真源闸只判 §06-A 节号可解析，不判语义（判据 15 的「闸管不到」层） | `specs/state.md:115`、`:21`、`:158`；`docs/runtime-refactor/walk/裁决表.md:88-97`（§06-A 在 `:92`）；`docs/runtime-refactor/recon/K-上下文事件指南预算.md:458-464`；先例 `docs/runtime-refactor/spec-review/execution-评审.md:18,69`（F-03 同款） | 采纳：改述真源为「数值真源＝`recon/K` R-K-72…R-K-78；`裁决表.md` §06-A 只承载循环上限五项（统一预算表未落盘）」，删「统一预算表」这一无落盘的名为真源 |
| S-4 | 中 | **应钉面漏登记（字段面归属未声明）**：与「状态字段／常量／限额／载荷形状」相关的三钉只在他规格登记**行为面**，其**字段面**（本块承载）未在本规格挂钩表出现或声明归属——`pin-09`（`Manifest.material_truncated` 字段面）、`pin-15`（`Budget` 的连续反问上限键面）、`pin-28`（`run_id` 字段面）。本规格既已为同类「字段契约面／形状面」登记 pin-22/23/26/30，此三钉若不归本块应明写分工，否则成「两头都不认」 | `specs/state.md:172-192`；`docs/runtime-refactor/eng/04a-应钉行为清单.md:18,24,37`；行为面落点 `specs/answering.md:143`（pin-09）／`specs/clarification.md:149`（pin-15）／`specs/agent-loop.md:230`（pin-28） | 采纳（弱）：挂钩表逐条声明分工——归他块则注明「字段面随 <卡>，本块不挂」，或补挂字段面测试 |
| S-5 | 低 | **`pin-30` 只登记半面且未声明另半面去向**：`04a` pin-30 原文＝「**compaction 视窗预算触发摘要化**＋v1 旧 run 黑匣子回放 dialogue 通道如实空显」，本规格行为 8／挂钩表只登记后半面（「旧 run 对话通道如实空显」），**未声明 compaction 半面归谁**（按 S1 归属应为 H6／`context`，V2-79d） | `specs/state.md:113`、`:186`；`docs/runtime-refactor/eng/04a-应钉行为清单.md:39`；`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md:106`（H6 含 V2-79d compaction） | 采纳（弱）：补一句「compaction 半面挂 `context`／H6，另规约承接」 |
| S-6 | 低 | **不降级信号的断言只覆盖两处、未覆盖第三处**：`:126` 列三处机读信号（`budget_hit`＋`Convergence.notice`＋**触界步的过程记录（计数与命中项）**），断言引「行为 13」；而行为 13（:118）只断言「`Convergence` 与 `budget_hit` **同现**」，**未覆盖**「触界步的过程记录」——信号清单与断言不齐（`spec-format` §二.7 要求「验收里有一条断言该信号在场」） | `specs/state.md:126` vs `:118`；`specs/state.md:147`（验收行 `::budget_hit_signal_present`） | 采纳（弱）：把「触界步过程记录」纳入行为 13 断言，或从信号清单删去 |
| S-7 | 低 | **行为 6 判据偏「形」、难照写 assert**：断言「`dialogue` 中零**任务书／指令形**内容，且两者**内容域互斥**」——「指令形内容」「内容域互斥」无客观机读边界（fixture 只能覆盖已知注入形态），与 `spec-format` §三.1「能直接写成 assert」有张力（pin-26 原文只要求「不混层」） | `specs/state.md:111`、`:139`；`docs/runtime-refactor/eng/04a-应钉行为清单.md:35` | 采纳（弱）：落成结构判——`dialogue` 条目来源白名单 ＋ 每条携来源标签（来源∉白名单即失败） |
| S-8 | 低 | **两条红线缺「对应闸名」**：`:101`「外部依赖只许 `infra`」、`:102`「禁手写替代（不得自建第二套帧形状，只许引 `transport` 结构别名）」均**未给对应闸名**，不合 `spec-format` §二.5（点名框架／唯一出口须写「验收写法 ＋ 对应闸名」；接不上须登记「人审＋原因」，见样板 `specs/answering.md:125`） | `specs/state.md:101-102`；`docs/spec-format.md` §二（第 5 行）、§五；样板 `specs/answering.md:67,125` | 采纳（弱）：`:102` 补「无专属闸 → 人审（降维为 AST 断言：禁自建帧类型符号）」；`:101` 说明由 R4（不引包内块）＋B6 出口纪律覆盖 |
| S-9 | 低 | **R7 被当成「零接触模型出口」的完整覆盖**：`:99`／`:181` 把「不调模型／不引用模型出口」挂 **R7 契约**；R7（`toml:113-117`）`forbidden` **只有** `appv2.infra.llm_client`。本块真正「不引 `gateway_adapter`」的一面由 **R4** 覆盖（`toml:87-92` forbidden 含 `appv2.runtimev2.gateway_adapter`）——两闸合起来才成立，单挂 R7 属**部分覆盖**（同 `spec-review/verification-评审.md` V-3 判例） | `specs/state.md:99`、`:181`；`tools/importlinter_v2.toml:113-117`（R7）、`:87-92`（R4） | 采纳（弱）：改述为「不直引 `infra.llm_client`＝R7；不引 `gateway_adapter`＝R4（两者合覆盖）」 |
| S-10 | 低 | **`converge` 拆分的卡面残留**：判定/写入分层在流水 20①、`## state` 卡 note（`modules.md:287`）与规格风险 1（:160）**三处口径一致**（判定→`state.check_limits`；落地写入→`bookkeeping.converge`），但 `## bookkeeping` 卡（`modules.md:326-328`）仍写 `def converge(state) -> Convergence: ...`，**签名/返回未随本批更新**，与「落地写入（写口）」语义在卡面未澄清——「同名同返回类型」的双函数歧义未被卡面消掉 | `specs/modules.md:326-328`（书卡）vs `:274-287`（state 卡 note）；`specs/state.md:160`；`docs/runtime-refactor/00-决议与方法.md:90`（流水 20①） | 采纳（弱）：登记以便阶段 2 澄清 `bookkeeping.converge` 返回（写入无回值／返回写入结果）——非阻断 |

## 三、16 问逐条回答

**1 十节齐＋标题逐字？** 无发现。`## 目标`(:7)／`## 不做什么`(:11)／`## 触及的模块`(:23)／`## 接口定义`(:31)／`## 框架与依赖红线`(:95)／`## 行为约定`(:104)／`## 不降级与静默禁令`(:123)／`## 验收测试`(:130)／`## 依赖与风险`(:156)／`## 与闸的挂钩表`(:172)——十节齐、逐字、顺序同 `docs/spec-format.md:31-34`；`check_specs` 实跑 PASS。

**2 行为约定每条能否写成 `assert`／含糊词？** 无发现（判 FAIL 的含糊词「尽量／合理／必要时／视情况」全文 **0 命中**，`grep` exit 1）；16 条行为均带【断言：…】。唯行为 6 的「指令形内容／内容域互斥」措辞偏软——已单列 **S-7**（低），非硬伤。

**3 数字有无裸值？** 无发现。`grep "[0-9]"` 命中项**全是标识符与锚点**（`R4`／`R5b`／`R6`／`R7`／`S1`／`S3`／`S5`／`S6`／`§06-A`／`18/18`），无配置裸值。中文数字「六值／四值／十值」（:89）均同句带真源指针；**唯 `NOTICE_TYPES` 的条数无真源**——并入 **S-1**（非独立数字问题）。

**4 不做什么每条有无「由谁承担＋锚点」？** 无发现。7 行俱带（`:15`→`orchestration`／`agent-loop.md` 行为 8；`:16`→`bookkeeping`；`:17`→`persistence`；`:18`→`transport`；`:19`→`gateway_adapter`；`:20`→语义归相位模型产出＋`判断归责表.md`；`:21`→引唯一数值真源＋`裁决表.md` §06-A）。

**5 框架红线写对应闸名／闸名真存在／source 真覆盖 state？** 有发现——**S-8**（两条红线缺闸名）、**S-9**（R7 部分覆盖）。真存在且 `source_modules` 真覆盖 `appv2.runtimev2.state` 的闸（逐条核 toml）：**R4**（`toml:87-92`，含 state）、**R5b**（`toml:101-105`，含 state）、**R6**（`toml:108-111`，含 state）、**R7**（`toml:114-117`，含 state）——编号真、覆盖真。红线与闸意图对应：R5b＝框架、R4＝不引包内块、R6＝不引引擎、R7＝不直引 `infra.llm_client`，均对得上（R7 覆盖面窄见 S-9）。

**6 不降级与静默禁令？** 有发现——**S-6**。`:125` 明写「合法降级路径：无」；`:127` 旧检查点读入为唯一降级并给机读信号（`schema_version`＋读入注记）＋断言（行为 8）；`:128`「不许自述完成」；`:126` 列三处触界信号——但断言只覆盖两处（S-6）。

**7 验收测试（每行标识／边界集保留集）？** 无发现。18 行**全部**绑 `tests/domains/test_v2_state.py::<id>`（`:134-152`）；`:151`【边界集】、`:152`【保留集】两行俱在；`:154` 有测试文件归属注（新建 `test_v2_state.py`，`ls tests/domains/` 确认无同名冲突）。

**8 与闸的挂钩表（填了没／接不上写原因／「已真跑」属实否）？** 有发现（**S-8**／**S-9** 覆盖面与归属）。表已填；「已进 CI」属实（`.github/workflows/ci.yml:32`＝`check_specs`、`:34`＝`ref_resolvable`）；「已真跑」属实——实跑 `lint-imports` **18/18 KEPT**（R4/R5b/R6/R7 均 KEPT，state 为空模块过闸）；`:191`／`:192` 两处「人审＋原因」齐备。唯 **S-9** 的 R7 行覆盖面表述不准。

**9 与 `walk/` 决策是否冲突？** 无发现（逐条比对）。总纪律 §二（语义交模型）→`:20`／`:121` 明排词表/正则；「前置三态」「只读落执行层」「真流式」均非本块事（本块仅持 `SseEvent` 别名，:71/:91）；「废弃词交模型」→`:20`；`裁决表` §06-A（循环上限收一致一处）→ 本块 `Budget` 收口（:115）；§06-B 挂起恢复＝非本块；「重写不是改」——本块以卡＋`synth/S5` 为新形状真源（未照抄旧 `state.py` 形状）。`walk/06` Q-A/B/C/D 逐条无相悖。

**10 覆盖（`synth/S1` H1／H8／越界）？** 有发现——**S-4**／**S-5**。H1（状态与数据模型）：`RunState` 引 `S5` 全量、`Manifest`＝`recon/I2a` 骨架、三载荷＋常量族齐（`S1:36` H1 覆盖项全落点）✔。H8（预算与闸）：`Budget` 键集七项＝`recon/K` `budget.py` 七常量（R-K-72…78）✔；触界**收敛交付**（`unfinished_items`／`material_rows`／`unfinished_notice`／`NO_MATERIAL_SHELL`）按不做什么归 `bookkeeping`（其卡职责含「触界收敛」）✔。越界：**未见**（触及的模块含 `bookkeeping`／`orchestration`，写法与样板 `understanding.md`／`verification.md` 同款「本块只消费／只出形状」，非越界）。

**11 总纪律残留（程序替模型判语义）？** 无发现。`:20`／`:121` 明文排词表／正则语义判定；本块无「若句中出现 X 词就 Y」形设计（限额触界＝纯数值比较，:20）；`no_judgement_or_io_in_state`（:150）以 AST 扫描把守。

**12 与模块卡一致（职责／公开接口／依赖）？** 有发现——**S-2**（卡缺 `LimitHit`）、**S-10**（`bookkeeping.converge` 卡面残留）。一致项：职责 `:9`＝卡 `modules.md:270`；`RunState`／`Manifest`／`AskRequest`／`AskChoice`／`RunHandle`／`Budget`／`Convergence` / 常量族 / `check_limits(state)->Convergence` 与卡 `:274-285` 一一对上；依赖 `:158`（模块无、外部 `infra`）＝卡 `:289-291`。`converge` 拆分处理**自洽**（卡 note＋规格风险 1＋流水 20 三处同口径，判定/写入一物一处），残留仅在书卡签名未更新（S-10）。

**13 接口与已定稿规格对账？** 无发现。逐字比对 `specs/agent-loop.md:50-56`：`AskRequest{question: str|None, resume_run_id: str|None, followup_run_id: str|None, actor: Actor}`／`AskChoice{kind: "clarify"|"external_table_approval", choice: str|None, decision: "approve"|"reject"|None, approval_id: str|None}`／`RunHandle{run_id: str, stream: AsyncIterator[SseEvent], cursor: int}`——**字段名／类型／可空性／枚举值全同**。`Manifest` 10 字段＝`recon/I2a-状态常量与清单.md:53-64` 骨架（source_type／source_id／version／trust_level／selected_reason／token_count／transform／material_total／material_rendered／material_truncated）逐字一致。`RunState` 字段数与 `synth/S5`（`S5:10` 53 字段）对得上（规格引矩阵全量，卡 `:270` 亦写 53，`recon/I2b:149` 实测 53）。

**14 钉（pin）登记？** 有发现——**S-4**／**S-5**。①登记与钉原文同一件事：`pin-22`（04a:31）↔ `:109` ✔；`pin-23`（04a:32）↔ `:112` ✔；`pin-24`（04a:33）↔ `:110` ✔；`pin-26`（04a:35）↔ `:111` ✔；`pin-29`（04a:38）↔ `:119`（明写「形状面」，闭环面挂 `agent-loop.md`）✔；`pin-30`（04a:39）只半面（S-5）。②漏登记：`pin-09`／`pin-15`／`pin-28` 的字段面（S-4）。③钉号/优先级：无写错——`pin-22/23/29`＝P0、`pin-30`＝P2 与 04a 一致；`pin-24/26` 未标优先级（04a 为 P1），不冲突。分工：state 侧对 `pin-22/23/29` 明写「字段契约面／形状面」、行为面挂 `agent-loop.md`——**无「两头都认／两头都不认」**（唯 `agent-loop.md`（已定稿）三行未回提 state 侧形状面，属 `agent-loop.md` 侧观察，非本规格缺陷）。

**15 真源引用是否指向真实存在的东西？** 有发现——**S-1**（`NOTICE_TYPES` 无真源）、**S-3**（「统一预算表」不实）。其余逐条核实为真：`arch/P7a-交接包与挂账清单.md` A-P7a-37（:118 引）**真实**且原文含「不许静默」（`P7a:98`）✔；`synth/S3` C-07（:113 引 schema_version 真值）**真实**（`S3:22`）✔；`synth/S6` §一 notice 恰三键（:117 引）**真实**（`S6:23`）✔；`recon/K` R-K-72…R-K-78（:115 引）**真实**（`K:458-464`）✔；`synth/S5`／`S1`／`S6`／`recon/I2a/I2b` 路径皆可解析（真源闸绿）。

**16 卡级问题？** 有发现——**S-2（L0，须回阶段 2 补 `LimitHit`）**；兼卡级倾向：**S-1**（`NOTICE_TYPES` 若判无真源，须回阶段 2 落定取值或撤卡面）、**S-10**（`bookkeeping.converge` 卡面签名待澄清）。除此，职责／依赖／边界未见卡错。

## 四、闸实跑记录（2026-10-15）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）        # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：14 份规格的真源引用与边界规则编号均可解析。   # exit 0

$ uv run lint-imports --config tools/importlinter_v2.toml
...
R4 runtimev2 state 不 import 本包内任何其它块  KEPT
R5b ADR-0002 红线① 扩展：框架只许在 runtimev2.orchestration（其余 16 块禁引）  KEPT
R6 runtimev2 各块只经 tools 接触引擎  KEPT
R7 runtimev2 各块只经 gateway_adapter 调模型  KEPT
Contracts: 18 kept, 0 broken.    # exit 0
```

辅助取证命令：`grep -rn "NOTICE_TYPES"`（仅 `modules.md:282`／`state.md:89,114`）；`grep -rn "统一预算表"`（仅引用、无落盘表）；`grep -nE "尽量|合理|必要时|视情况" specs/state.md`（0 命中，exit 1）；`ls tests/domains/test_v2_state.py`（不存在，阶段 5 承诺）；`ls appv2/runtimev2/state/`（仅 `__init__.py`，探针已移除→18/18 KEPT 属实）。

### 未验证清单

1. `tests/domains/test_v2_state.py` **不存在**、`appv2/runtimev2/state/` 仅占位 `__init__.py`（阶段 5）——18 行验收测试只能核标识形态，无法实跑。
2. R4／R5b／R6／R7 的「已真跑」为**契约空过**（state 无实现代码）——契约存在且 KEPT 已实测，「state 实现层真合规」待阶段 5。
3. **S-1** 中「本仓是否另有 notice 类型闭世界的设计动议」未穷搜（仅据 `grep NOTICE_TYPES` 与 `recon/K` D-K-48/D-K-56 判定无可解析真源）；若在 teach 仓或未合并文档另有定义，S-1 应降级——**未证实**，不代裁。
4. **S-2** 的严重度取决于评审对「`LimitHit` 是否须为公开类型」的判定：若判为 `Convergence` 内部表示，则不回阶段 2（见建议）。

---

## 五、L0 处置表（逐条清零 · 2026-10-15）

> 处置原则：**卡级问题 L0 亲征**（阶段 2 范畴，不派子代理）；**规格文本改动**逐条写成「原文 → 新文」的照抄式修复单，交修订子代理执行。

| 编号 | 处置 | 依据／落法 |
|---|---|---|
| **S-2**（L0） | **采纳 → L0 已改卡** | 「`LimitHit` 是 `Convergence.hit` 的**公开**元素类型」成立（消费方要按命中项分派），故**回阶段 2 补卡**：`specs/modules.md` `## state` 公开接口已补 `class LimitHit: ...`。规格侧无需改（它本就按公开类型写） |
| **S-1**（高） | **采纳 → 判「移出本块」＋L0 已改卡** | 结论：**通知类型的闭世界不属本块**——`notice` 是**帧载荷面**，其分型闭世界与事件名闭世界同属 `## transport`（卡职责「事件通路／事件名闭世界」）。故本块常量族**收为三族**（`STEP_KINDS`／`RUN_STATUS_KINDS`／`INTENT`，三族都取自 `RunState` 字段取值域，真源 `recon/I2a` 实测 22 常量）；`NOTICE_TYPES` 从卡与本规格**一并删除**，改在 `## transport` 卡注记归属（已加注）。**登记待补**：`transport` 规格定稿时须立 notice 类型闭世界并**落定取值真源**（现状字面值散落各处：`recon/K` D-K-56／D-K-48），否则「同一件事多处数字」照旧——该债随 `transport` 块销项 |
| **S-3**（中） | **采纳** | 「统一预算表」是**未落盘**的口径说法（`grep` 只见引用、无同名文件），且 `裁决表.md` §06-A 只有循环上限一行，覆盖不了 `Budget` 的另四项键。修法：数值真源改述为**双指**——①`recon/K` R-K-72…R-K-78（逐键承载七项）｜②`walk/裁决表.md` §06-A（承载循环上限五项）；全文删「统一预算表」作为**真源名**。**跨规格债登记**：同款引用亦在 `specs/clarification.md`／`specs/tool_matching.md`（已定稿，主窗侧文件），本批不动，登记待主窗统一改述 |
| **S-4**（中） | **采纳（弱）→ 挂钩表补「字段面分工」** | 三钉的**字段面**确由本块承载，逐条声明分工，不留「两头不认」：`pin-09`（`Manifest.material_truncated` 字段面←本块；披露行为面←`specs/answering.md`）｜`pin-15`（连续反问上限的**键面**←本块；到顶截断行为面←`specs/clarification.md`）｜`pin-28`（`run_id` 字段面←本块；全盖章面←`specs/agent-loop.md`）。**不**重复挂行为测（避双头） |
| **S-5**（低） | **采纳（弱）** | `pin-30` 补声明另半面去向：**compaction 半面归 `context`（`synth/S1` H6／V2-79d）**，本块只挂「旧 run 对话通道如实空显」半面 |
| **S-6**（低） | **采纳（弱）** | 「触发盘不静默」的信号清单与断言对齐：本块只断言**自己产的两处**（`budget_hit`＋`Convergence.notice` 同现）；「触界步的过程记录」是**消费方义务**（`bookkeeping` 的写口），改述为「由 `bookkeeping` 侧断言」，不在本块冒充覆盖 |
| **S-7**（低） | **采纳（弱）** | 行为 6 落成**结构判**（pin-26 只要求「不混层」）：`dialogue` 条目形态固定为 `{role, content, origin}`，`origin` 闭世界＝用户原话／assistant 终稿／澄清与审批回收原文，越界即失败——这样「不混层」有了机读边界 |
| **S-8**（低） | **采纳（弱）** | 两条红线补闸名：①「外部依赖只许 `infra`」← **R7**（禁直引 `appv2.infra.llm_client`）＋ B6 出口纪律（`appv2` 禁 litellm）；②「禁手写替代（不得自建第二套帧形状）」← **无专属闸 → 人审**（降维面＝AST 断言「不出现自建帧类型符号」，登记待补） |
| **S-9**（低） | **采纳（弱）** | 「不调模型／不引用模型出口」改述为**两闸合覆盖**：不直引 `infra.llm_client`＝**R7**；不引 `gateway_adapter`＝**R4**（本批补全后的 forbidden 含它）——单挂 R7 属部分覆盖（同 `verification-评审` V-3 判例） |
| **S-10**（低） | **采纳 → L0 已改卡** | `## bookkeeping` 卡的 `converge` 签名已随裁决更新为 **`-> None`**（落地写入无回值），卡面「同名同返回」歧义消掉；规格侧无需改 |

**净结果**：10 条全部采纳（其中 3 条由 L0 直接改卡／改归位：S-1 移族、S-2 补类型、S-10 改签名），其余 7 条组成规格文本修复单交修订子代理照抄执行。**无升 Owner 项**（无业务语义裁决需求）。

### 五之二、修复执行记录（2026-10-15，L0）

- **执行者**：按 Owner 排产阶梯（「起草→独立评审→**逐条处置（L0 清零）**→复审→定稿」），本块**不另派「修订」子代理**——七条规格文本改动由 **L0 直接落笔**（改动内容与逐字替换对已在本表列明，可逐条比对）；**复审仍由独立子代理执行**（下一步）。
- **已改（规格 `specs/state.md`）**：S-1（三族，删 `NOTICE_TYPES`，并写明通知类型闭世界归 `transport`）｜S-3（数值真源改双指、删「统一预算表」作为真源名、新增风险 12 登记跨规格命名债）｜S-4（挂钩表加「钉的字段面分工」注）｜S-5（`pin-30` 补 compaction 半面去向）｜S-6（信号清单与断言对齐：本块两处承诺、第三处归 `bookkeeping`）｜S-7（行为 6 落结构判：`dialogue` 条目 `origin` 来源闭世界）｜S-8（两条红线补闸名／人审登记）｜S-9（「不调模型」改两闸合覆盖）。
- **已改（阶段 2 卡面 `specs/modules.md`）**：S-2（`## state` 公开接口补 `class LimitHit`）｜S-1 卡面（常量族收为三族＋加「notice 分型闭世界归 `## transport`」注）｜S-10（`## bookkeeping` 的 `converge` 签名改 `-> None`）。
- **闸**：`check_specs` PASS（0 警告）｜`ref_resolvable` 绿（14 份规格）｜`lint-imports` 18/18 KEPT。

---

## 六、复审结论（独立子代理）

- 日期 2026-10-15 ｜ 复审对象：`specs/state.md`（修订稿）＋ `specs/modules.md` `## state`（:268-298）／`## bookkeeping`（:321-343）卡 ｜ 纪律：只读＋只追加（未改任何现存文件）。
- **闸亲手复跑（本子代理）**：`uv run python tools/check_specs.py` → `spec gate: PASS（0 警告）`（exit 0）；`uv run python tools/ref_resolvable.py check` → 绿（14 份规格）；`uv run lint-imports --config tools/importlinter_v2.toml` → `Contracts: 18 kept, 0 broken`（R4／R5b／R6／R7／R8 全 KEPT）。

### 六之一、闭合核验表（S-1…S-10）

| 编号 | 判定 | 证据（实读） | 说明 |
|---|---|---|---|
| S-1 | **闭合**（规格侧） | `specs/state.md:89`「三族…STEP_KINDS｜RUN_STATUS_KINDS｜INTENT…通知类型（`notice.type`）的闭世界不属本块…归 `transport`」；`:114`／`:142` 均只余三族；`specs/modules.md:283` 卡面只余三族、`:289` 卡注「notice 分型闭世界不落本卡…归 `## transport`」；`grep -rn NOTICE_TYPES specs/ appv2/` **0 命中**（前轮命中 :89/:114/:282 全部消失） | 幻影真源族已全篇根除、归位声明双向可读；唯处置表称「改在 `## transport` 卡注记归属（已加注）」，实读 `## transport` 卡（`modules.md:404-423`）**无任何 notice 注记**（`grep -n notice modules.md` 只命 260/281/288/289/330/499）→ 低度残留见 **SZ-3** |
| S-2 | **闭合** | 卡已列 `specs/modules.md:282`「`class LimitHit: ...` # 触界命中项（limit 闭世界／used／cap）——Convergence.hit 的元素类型」；规格侧 `specs/state.md:77-81`（limit 七值 Literal／used／cap）、`:84`（`Convergence.hit`）、`:107`（`LimitHit` 入 frozen 列表）三处自洽 | 卡↔规格口径已一致 |
| S-3 | **闭合** | `specs/state.md:21`／`:115`／`:158` 已改**双指**（`recon/K` R-K-72…R-K-78 逐键 ＋ `walk/裁决表.md` §06-A 循环上限五项）；`grep -n 统一预算表 specs/state.md` 仅 `:171`（风险 12，自述为「未落盘的引用名」，非当值真源）。**亲读真源逐键核**：`recon/K:458-464` R-K-72 轮数＝3｜R-K-73 轮内发现≤2、执行≤2｜R-K-74 段时长 300.0、单工具超时 30.0｜R-K-75 全 run 发现≤10｜R-K-76 连续 ask≤6 —— `Budget` 七键（:115）逐键有承载；`裁决表.md:92` §06-A 恰五项（发现≤10／大循环≤3轮／回炉一次／连续澄清≤6／同参重投即拦），「五项」计数属实 | 双指真覆盖七键、无「统一预算表」当真源名残留；**跨规格债登记不全**（漏 `agent-loop.md`）→ **SZ-2** |
| S-4 | **闭合** | `specs/state.md:195` 钉分工注逐钉写明：`pin-09`（`Manifest.material_truncated` 字段面←本块／披露行为面←`specs/answering.md`）｜`pin-15`（连续反问上限参数键面←本块／到顶截断行为面←`specs/clarification.md`）｜`pin-28`（`run_id` 字段面←本块／全盖章计费面←`specs/agent-loop.md`）。与钉原文同物：`eng/04a:18`（pin-09）／`:24`（pin-15）／`:37`（pin-28）；对侧行为面确在册（`answering.md:143`／`clarification.md:149`／`agent-loop.md:230`） | 「两头不认」已消；三钉字段面归属与卡面（`Manifest` 字段／`Budget` 键／`RunState.run_id`）对得上 |
| S-5 | **闭合** | `specs/state.md:187`「`pin-30` 的**后半面**；**compaction 半面**归 `context`——`synth/S1` H6／V2-79d」；钉原文 `eng/04a:39` 确含 compaction＋旧 run 空显两半；`synth/S1:106` H6 行确含「V2-79d compaction」 | 另半面去向已声明且落点真实 |
| S-6 | **闭合** | `specs/state.md:126` 已改述为「本块承诺面＝两处（`budget_hit`＋`Convergence.notice`）…第三处触界步过程记录**由 `bookkeeping` 落账并在其规格断言**」；行为 13（`:118`）断言只写「`Convergence` 与 `budget_hit` 同现」；验收行 `:147` `::budget_hit_signal_present` 同述 | 信号清单／断言／验收行三处口径一致，无「两处 vs 三处」错位 |
| S-7 | **闭合**（改法到位） | `specs/state.md:111` 已落**结构判**：条目形态固定 `{role, content, origin}`、`origin`＝来源闭世界三值、越界即失败；验收行 `:139` 同述（`origin` 全部落在闭世界内） | 「不混层」已有机读边界；**唯该闭世界无取值真源与落点**（`recon/I2b:43` 现状为 `list[dict[str,str]]` 无 `origin` 键；`synth/S5:33` 只记兼容死字段；`arch/P5b1:50` 定义为 `[{"role","content"}]`）→ **SZ-1** |
| S-8 | **闭合** | `specs/state.md:101` 补「对应闸：**R7 契约**（禁直引 `appv2.infra.llm_client`）＋ **B6 出口纪律**」；`:102` 补「对应闸：**无专属闸 → 人审**（原因：R1–R8 无此一面；降维面＝AST 断言…）」 | 两条红线均不再裸奔；唯 `:101` 的闸名映射偏窄且与处置表所写「由 R4＋B6 覆盖」不一致 → **SZ-4** |
| S-9 | **闭合** | `specs/state.md:99`「两闸合覆盖：不直引 `appv2.infra.llm_client`＝**R7**；不引 `gateway_adapter`＝**R4**（单挂 R7 属部分覆盖）」；挂钩表 `:182` 同述。亲核 `tools/importlinter_v2.toml`：R7（:114-117）`forbidden` **仅** `appv2.infra.llm_client`；R4（:88-92）`forbidden` 含 `appv2.runtimev2.gateway_adapter` | 「部分覆盖当完整覆盖」的旧表述已消，两闸各自的覆盖面描述准确 |
| S-10 | **闭合** | `specs/modules.md:330` 已改「`def converge(state) -> None: ...` # 触界收敛的**落地写入**…本函数无回值——写入 budget_hit／notices／status／next_intent 六键」；`:288` 卡注「判定归本块（更名 `check_limits`，纯计算）｜落地写入归 `bookkeeping` 唯一写口 `converge`（无回值）」；规格 `:160` 风险 1 同口径 | 书卡签名/返回已随裁决更新，「同名同返回」歧义消掉 |

**计数**：10 条全部**闭合**；其中 S-1 有一处卡面注记落点与处置表不符（SZ-3）、S-7/S-8 各有低度残留（SZ-1/SZ-4）。

### 六之二、结论

**不可定稿**。上轮 10 条处置全部闭合，但本轮独立复跑发现 **7 条新增**（中×2、低×5），其中**必须先修 2 条**：

1. **SZ-1（中）**——行为 6 新立的 `dialogue` 条目 `origin` 字段＋三值来源闭世界**无取值真源、无落点**（现状/矩阵/方案三处皆无该键，卡也未承载条目形状）。这是 S-7 修复**新引入**的「无锚闭世界」，与 S-1／S-3 同类病灶，不补锚点则行为 6 的 assert 无据可依。
2. **SZ-2（中）**——跨规格「统一预算表」命名债登记不全：风险 12（`:171`）只列 `specs/clarification.md`／`specs/tool_matching.md`，漏 **`specs/agent-loop.md:15,:133,:137`** 三处（同为已定稿规格）。

其余 5 条（SZ-3…SZ-7）为登记／一致性级，可随批处理或随主窗统一改述；其中**卡面登记项**（SZ-3 `## transport` 卡未接 notice 归位注记、SZ-5 `SseEvent` 无卡承载）属「卡须回阶段 2」范畴（**登记即可，不阻断本规格文本修复**）。

## 七、新增发现清单（复审轮）

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
| SZ-1 | 中 | **S-7 修复新引入「无锚闭世界」：`dialogue` 条目 `origin` 字段与三值来源闭世界无真源、无落点**。规格行为 6 把 `dialogue` 条目形态定为 `{role, content, origin}`、`origin` 闭世界＝「用户原话／assistant 终稿／澄清与审批回收原文」，越界即失败；但该键**在现状与全部真源里都不存在**——`recon/I2b:43` 记 `dialogue: list[dict[str, str]]`（只注 80a 自然对话层，无 `origin`）、`synth/S5:33` 只把它记为兼容死字段、`arch/P5b1-对话状态重构方案.md:50` 的对话层定义是 `[{"role","content"}]`；`## state` 卡（`modules.md:268-298`）也不承载条目形状。**且三值为中文描述、无字面量、无真源指针**——实现者与阶段 5 测试无据可抄（与 `spec-format` §二.4「枚举闭世界列全合法值」、§三.2「口径只许引真源，横切事实只引用不复述」有张力） | `specs/state.md:111`、`:139`；`docs/runtime-refactor/recon/I2b-RunState全字段.md:43`；`docs/runtime-refactor/synth/S5-RunState字段矩阵.md:33`；`docs/runtime-refactor/arch/P5b1-对话状态重构方案.md:50`；`specs/modules.md:268-298`（卡无条目形状） | 二选一：①补真源指针＋逐字列出 `origin` 三值（若为本次重写新立设计，则落到一处设计记录并在 `synth/S5` 矩阵／`## state` 卡注记条目形状）；②把行为 6 降回可判的**结构判**（如「`dialogue` 每条必含三键且 `origin ∈ {枚举常量}`」并把枚举常量列入本块闭世界常量族，与 STEP_KINDS 同款落 `recon/I2a` 真源）。**不可两处并存**（同 S-2 判例） |
| SZ-2 | 中 | **跨规格命名债登记不全（S-3 的连带面）**：风险 12（`specs/state.md:171`）声明「同款引用亦在已定稿的 `specs/clarification.md`／`specs/tool_matching.md`——登记待主窗统一改述」，但**同款「统一预算表」当真源名**还出现在 **`specs/agent-loop.md:15`／`:133`／`:137`**（`grep -n 统一预算表 specs/` 实读命中：agent-loop.md 三处、clarification.md:49/83/108/132/149、tool_matching.md:92），而 `agent-loop.md` 不在登记名单内——主窗按此清单改述会**漏改该文件三处**，债照旧 | `specs/state.md:171`；`specs/agent-loop.md:15,:133,:137`；`specs/clarification.md:49,:83,:149`；`specs/tool_matching.md:92` | 把 `specs/agent-loop.md:15/:133/:137` 补入风险 12 的登记清单（或改为「`grep 统一预算表 specs/` 全量为主窗改述对象」的照抄式表述） |
| SZ-3 | 低 | **归位声明单向：`## transport` 卡未接 notice 分型闭世界**。`specs/modules.md:289`（`## state` 卡注）与 `specs/state.md:89` 均声明「`notice.type` 闭世界归 `## transport`」，但 `## transport` 卡（`modules.md:404-423`）职责只写「事件名闭世界（9 类）」、测试计划只写「九类闭世界」，**未提帧载荷/通知分型闭世界**（`grep -n notice specs/modules.md` 仅命 260/281/288/289/330/499，均非 transport 卡）。处置表 S-1 行称「已加注」不实（注记落在 `## state` 卡） | `specs/modules.md:289`、`:404-423`；`specs/state.md:89`；`specs/modules.md:499`（九类闭世界口径在 `## api` 卡） | 在 `## transport` 卡职责加一句「帧载荷分型闭世界（含 `notice.type`）归本卡」（本块债随 transport 规格销项）——与 S-2/S-10 同批卡面登记 |
| SZ-4 | 低 | **红线 `:101` 的闸名映射与红线语义不匹配，且与处置表写法不一致**。红线为「外部依赖只许 `infra`」（白名单口径），对应闸却只挂 **R7**（`forbidden` 仅 `appv2.infra.llm_client` 一面）＋ B6（纪律非闸）。R7 覆盖不了「只许 `infra`」这一白名单语义（引 `pydantic`／`requests` 等第三方不改判 R7、亦不在 R5b 框架名单、不在 R6 引擎名单）；处置表 S-8 行（`state-评审.md:105`）写的是「由 **R4**（不引包内块）＋B6 出口纪律覆盖」，文件里写的是 **R7**——两处口径不一 | `specs/state.md:101`；`tools/importlinter_v2.toml:114-117`（R7 forbidden 仅 llm_client）、`:88-92`（R4）、`:101-105`（R5b）、`:108-111`（R6）；`docs/runtime-refactor/spec-review/state-评审.md:105` | 改述为「**无专属闸 → 人审**（原因：R1–R8 无『依赖白名单』一面；可降维的部分＝不引包内其它块 R4／不引框架 R5b／不引引擎 R6／不直引 `infra.llm_client` R7 合覆盖）」——与 S-9 同款「合覆盖」写法，并修处置表记录 |
| SZ-5 | 低 | **公开类型别名 `SseEvent` 无任一张卡承载**：`specs/state.md:71` 定义 `SseEvent = Mapping[str, Any]` 并用作 `RunHandle.stream` 的元素类型（`:69`），但 `## state` 卡公开接口（`modules.md:273-286`）**未列该别名**，`## transport` 卡（`modules.md:404-423`）**未定义该别名**；`specs/agent-loop.md:56` 亦只使用不定义（`grep -rn SseEvent` 全仓仅 state.md 三处＋agent-loop.md 一处）。与 S-2 同类（规格定义公开符号、卡面缺件），但无行为、降一级 | `specs/state.md:69,:71,:91`；`specs/modules.md:273-286`、`:404-423`；`specs/agent-loop.md:56`；`docs/runtime-refactor/00-决议与方法.md:90`（流水 20 ③ 已裁「以结构别名表示，形状真源仍在 `transport` 规格」） | 卡面登记：`## transport` 卡公开接口补该别名（或 `## state` 卡注一句「`SseEvent` 为别名，形状真源在 `transport`」）——本块为登记项，**卡须回阶段 2** |
| SZ-6 | 低（疑点，未证实） | **`pin-12` 的字段面未在本块登记、也未在分工注中声明去向**。`pin-12`（`eng/04a:21`）＝「verify 对账机读字段（`delivered_rows`／`obs_rows`）入 step payload」，其**载荷容器 `steps` 是本块字段**；本块挂钩表（`state.md:175-195`）既未挂它，分工注（`:195`）的三钉也不含它（现挂 `specs/verification.md:139`＝字段属 `Verdict`、行为属 verification，故**可能**无本块义务）。**是否应登记，未证实**（同款边界：pin-06 的 `empty_probes`／pin-16 的 `chain_switch_marks` 亦为本块字段但钉的实质是行为，不属漏登） | `docs/runtime-refactor/eng/04a-应钉行为清单.md:21`；`specs/state.md:175-195`；`specs/verification.md:139`；`docs/runtime-refactor/synth/S5-RunState字段矩阵.md:20,:26`（`empty_probes`／`chain_switch_marks` 为本块字段） | 不建议强挂；建议在分工注里补一句边界口径（「**钉的主体是行为时，其载体字段不另挂本块**」），把「字段面／行为面」的划分判据写死，避免逐轮重问 |
| SZ-7 | 低 | **被引施工流水记录与本批改动已不一致**：`specs/state.md:192` 以 `docs/runtime-refactor/00-决议与方法.md` 流水 20 为「本批已裁」的锚点，但该条（`:90`）原文仍写「补…闭世界常量族 `STEP_KINDS`／`RUN_STATUS_KINDS`／`INTENT`／**`NOTICE_TYPES`**」——本批 S-1 已把 `NOTICE_TYPES` 从卡与规格删除，流水记录未同步（读者按锚点回查会读到已废族） | `specs/state.md:192`；`docs/runtime-refactor/00-决议与方法.md:90` | 在流水 20 条目补一句「同日 S-1 处置后 `NOTICE_TYPES` 已删、改归 `## transport`」（记录同步，不改规格） |

### 七之二、16 问复跑（逐条结论）

1. **十节齐＋标题逐字**：**无发现**。`## 目标`(:7)／`## 不做什么`(:11)／`## 触及的模块`(:23)／`## 接口定义`(:31)／`## 框架与依赖红线`(:95)／`## 行为约定`(:104)／`## 不降级与静默禁令`(:123)／`## 验收测试`(:130)／`## 依赖与风险`(:156)／`## 与闸的挂钩表`(:173) 十节齐、逐字、顺序同 `docs/spec-format.md:31-34`；`check_specs` 实跑 PASS。
2. **行为逐条可 assert／含糊词**：**无发现**。`grep -nE "尽量|合理|必要时|视情况" specs/state.md` **exit 1（0 命中）**；16 条行为均带【断言：…】。唯行为 6 的 assert 依赖一个无真源的闭世界 —— 已列 **SZ-1**（非含糊词问题）。
3. **数字裸值／可指真源**：**无发现**。`grep -nE "[0-9]"` 命中项全为标识符／锚点（`R4`／`R5b`／`R6`／`R7`／`S1`／`S3`／`S5`／`S6`／`R-K-72…78`／`§06-A`／`18/18`／行号式 `53` 仅出现在卡面）；中文数字「六值／四值／十值／22 条」( :89) 同句带真源 `recon/I2a`；行为 10 不写字面值。
4. **「不做什么」每条有「由谁承担＋锚点」**：**无发现**。7 行俱带（`:15`→`orchestration`／`agent-loop.md` 行为 8；`:16`→`bookkeeping`；`:17`→`persistence`；`:18`→`transport`；`:19`→`gateway_adapter`；`:20`→相位模型产出＋`判断归责表.md`；`:21`→双指真源）。唯 `:21` 锚点列只写 `recon/K` 路径、未带 `§06-A`（琐碎，不列条）。
5. **框架红线闸名真存在／真覆盖 state**：**无发现（闸侧）**。逐条核 `tools/importlinter_v2.toml`：**R4**（`:88`，`source_modules`＝`["appv2.runtimev2.state"]` @`:90`；`forbidden` 含公共层九块＋`gateway_adapter`）、**R5b**（`:101`，source 含 `state` @`:103`）、**R6**（`:108`，source 含 `state` @`:110`）、**R7**（`:114`，source 含 `state` @`:116`）——编号真、覆盖真。红线↔闸意图：R5b＝框架、R4＝不引包内块（含 gateway_adapter）、R6＝不引引擎、R7＝不直引 `infra.llm_client`，均对得上；唯 `:101` 白名单红线挂 R7 偏窄 → **SZ-4**。
6. **不降级与静默禁令**：**无发现**（S-6 已闭合）。`:125` 明写「合法降级路径：无」；`:127` 旧检查点读入＝唯一允许降级，机读信号（`schema_version`＋读入注记）＋断言（行为 8）；`:128` 不许自述完成；`:126` 两处承诺＋第三处归 `bookkeeping`，与行为 13／验收 `:147` 口径一致。（第三处义务的承接规格 `bookkeeping.md` 尚未存在于 `specs/`，属跨块待办，本规格表述已如实——不列条。）
7. **验收测试（每行标识／边界集保留集）**：**无发现**。18 行全部绑 `tests/domains/test_v2_state.py::<id>`（`:134-152`）；`:151`【边界集】、`:152`【保留集】两行俱在；`:154` 有测试文件归属注（新建文件；`ls tests/domains/` 无同名冲突——实测无 `test_v2_state.py`）。
8. **与闸的挂钩表（「已真跑」亲自跑）**：**核实属实**。本子代理实跑三条闸：`check_specs` PASS（0 警告）／`ref_resolvable` 绿（14 份）／`lint-imports` **18 kept, 0 broken**（R4/R5b/R6/R7/R8 全 KEPT）；「已进 CI」属实（`.github/workflows/ci.yml:32`＝`check_specs`、`:34`＝`ref_resolvable`；另 `:28`／`:30` 为合同覆盖率闸与债务标记闸）；`:192`／`:193` 两处「人审＋原因」齐备。唯 `:182` 行 R7＋R4 合覆盖表述与 `:101` 行不一致（见 SZ-4）。
9. **与 `walk/` 决策冲突**：**无发现**。项目级裁决 #1–#13 逐条比对无相悖（#7 新建 `runtimev2`＝本块目录 `appv2/runtimev2/state/`；#12／#13 gate 只留安全阀、语义交模型→本块 `:20`／`:121` 明排词表正则）；`walk/06` §二挂起三态＝非本块、§三循环表（发现≤10／大循环3轮／回炉一次／连续≤6／同参重投）→本块 `Budget` 收口（`:115`）；`walk/00` §二 总纪律（语义交模型；「若句中出现 X 词就 Y」＝程序替模型判语义）→本块无此形设计；`判断归责表.md`「收尾·完成判定＝程序」「语义类交模型」→本块 `:20`／`:128` 同口径。`synth/S1` H1/H8 与 M/H 单元落点无冲突。
10. **覆盖（`synth/S1` H1／H8／越界）**：**无发现**（S-4／S-5 已闭合修补）。H1（状态与数据模型＝`RunState 53 字段＋Manifest＋请求/回执数据类＋常量`，`S1:36`）：`RunState` 引 `S5` 全量（`:36`／`:106`）、`Manifest` 10 字段（`:40-51`）、三载荷（`:54-70`）、三族常量（`:89`）✔。H8（预算与闸＝`轮/时长/发现/执行四限额＋触界收敛交付`，`S1:41`）：七键闭世界（`:115`）✔、触界收敛交付归 `bookkeeping`（卡职责含「触界收敛」）✔。越界：未见（触及模块 `state`／`bookkeeping`／`orchestration` 均在册，写法为「只出形状／只消费」）。
11. **总纪律残留（程序替模型判语义）**：**无发现**。`:20`／`:121` 明文排词表／正则语义判定；本块判据均为结构判（数值比较、集合成员、前缀延伸、AST 扫描）；无「若句中出现 X 词就 Y」形设计。
12. **与模块卡一致（职责／公开接口／依赖）**：**无发现**（S-2／S-10 已闭合）。职责 `:9`＝卡 `modules.md:270`；公开接口 `RunState/Manifest/AskRequest/AskChoice/RunHandle/Budget/Convergence/LimitHit/三族/check_limits`（`:34-86`）＝卡 `:273-286` 逐一对上；依赖 `:158`（模块无、外部 `infra`）＝卡 `:291-293`。唯 `SseEvent` 别名不在卡 → **SZ-5**（登记级）。
13. **接口与已定稿规格逐字对账**：**无发现**。逐字比 `specs/agent-loop.md:50-56`：`AskRequest{question: str|None, resume_run_id: str|None, followup_run_id: str|None, actor: Actor}`／`AskChoice{kind: "clarify"|"external_table_approval", choice: str|None, decision: "approve"|"reject"|None, approval_id: str|None}`／`RunHandle{run_id: str, stream: AsyncIterator[SseEvent], cursor: int}`——字段名／类型／可空性／枚举值**全同**（`state.md:54-70`）。`Manifest` 10 字段逐字＝`recon/I2a:53-64` 骨架（`source_type/source_id/version/trust_level/selected_reason/token_count/transform/material_total/material_rendered/material_truncated`）＋`as_dict`✔。`RunState` 字段数＝`synth/S5`（`S5:10` 标题「53 字段」；**实测表行数＝53**）✔。
14. **钉登记**：**无发现（S-4／S-5 已闭合）**。①登记内容与钉原文同物：`pin-22`（`04a:31`）↔`:109`✔；`pin-23`（`:32`）↔`:112`✔；`pin-24`（`:33`）↔`:110`✔；`pin-26`（`:35`）↔`:111`✔；`pin-29`（`:38`）↔`:119`（明写「形状面」，闭环面挂 `agent-loop.md`）✔；`pin-30`（`:39`）↔`:113`／`:187`（半面＋另半面去向）✔。②漏登记：三钉字段面已在 `:195` 声明（S-4 闭合）；`pin-12` 疑点列 **SZ-6**（未证实）。③钉号／优先级无写错（`:183` pin-22 P0、`:184` pin-23 P0、`:188` pin-29 P0、`:187` pin-30 P2，均与 `04a:5` 及各行一致；`:185` `pin-24`／`:186` `pin-26` 未标优先级，与 `04a` P1 不冲突）。④分工写清（`:195` 明标「字段／参数键面←本块、行为面←他块」），无「两头都认／两头都不认」。
15. **真源引用是否真实存在且含该事实**：**有发现（SZ-1／SZ-2）**，其余逐条核实为真：`arch/P7a:98` A-P7a-37「不许静默」（`:118` 引）真；`synth/S3:22` C-07 schema_version＝3（`:113` 引）真；`synth/S6:23` §一 notice 恰三键（`:117` 引）真；`recon/K:458-464` R-K-72…78 七值（`:115` 引）真、逐键能对上 `Budget` 七键；`walk/裁决表.md:92` §06-A 五项（`:21`／`:115` 引）真；`synth/S1:106` H6 含 V2-79d（`:187` 引）真；`synth/S5` 53 字段（`:36` 引）真；`recon/I2a` 22 条常量（`:89` 引）真（实测表 22 行＝STEP 6＋RUN 4＋INTENT 10＋两个 `*_KINDS` 集）。
16. **卡级问题（只报不改）**：**有三项，均低度**——① `## transport` 卡未承接 `notice.type` 闭世界（**SZ-3**）；② `SseEvent` 别名无卡承载（**SZ-5**）；③ 处置表 S-8 行文字（`state-评审.md:105`「由 R4＋B6 覆盖」）与规格 `:101`（写 R7＋B6）不一致（**SZ-4**）。职责／边界／依赖三面未见卡错：`## state` 卡职责「限额参数与触界判定（纯计算，不写状态）」与规格目标/行为 11 一致；`## bookkeeping` 卡 `converge -> None` 与 `## state` 卡 note、规格风险 1 三处同口径。

---

## 八、复审轮新增发现的 L0 处置（2026-10-15）

| 编号 | 处置 | 落法（可逐字比对） |
|---|---|---|
| **SZ-1**（中） | **采纳（取建议①）** | 保留 `origin`，但**把「无锚」补成「明标自立」**：行为 6 改为**列全合法值**（`user_verbatim`／`assistant_final`／`clarify_approval_replay`，`role` ∈ `user`｜`assistant`），并明写「**`origin` 是本次重写自立的新结构**（现状条目只有 `role`／`content`）——**待 Owner 过目**，阶段 5 以本规格为准」，附现状锚点（`docs/runtime-refactor/arch/P5b1-对话状态重构方案.md`／`recon/I2b-RunState全字段.md`）；**依赖与风险新增风险 13** 登记该自立形状＋检测手段（`::dialogue_layer_purity` ＋ 人审） |
| **SZ-2**（中） | **采纳** | 风险 12 改述为**照抄式对象**：「改述对象＝`grep -n 统一预算表 specs/` 的全量命中」，并写明 `specs/agent-loop.md` 三处**已由本批就地改述**（`specs/agent-loop.md:15/:133/:137`→ 双指真源）、`clarification`／`tool_matching` 登记待主窗。**已就地完成 agent-loop 三处改述** |
| **SZ-3**（低） | **采纳 → 已改卡** | `## transport` 卡职责补「**帧载荷分型闭世界（含 `notice.type`）**」、测试计划补该闭世界、并加「归位登记」注（策略＝`transport` 规格定稿时立该闭世界并落定取值真源） |
| **SZ-4**（低） | **采纳** | `specs/state.md:101` 红线改述为「**无专属闸 → 人审**（R1–R8 无『依赖白名单』一面）；可降维面＝**四闸合覆盖**（R4 不引包内其它块／R5b 不引框架／R6 不引引擎／R7 不直引 `infra.llm_client`）＋ B6 出口纪律」——**并勘误本表 S-8 行**：该行原写「由 R4＋B6 覆盖」，与规格写的 R7 不一致，**以规格现文本为准**（四闸合覆盖＋人审） |
| **SZ-5**（低） | **采纳 → 已改卡** | `## transport` 卡公开接口补 `SseEvent = ...`（帧载荷形状在本卡定义；`state.RunHandle.stream` 以结构别名引用、不 import 守 R4） |
| **SZ-6**（低，疑点） | **采纳（弱）→ 写死分工判据** | 「钉的字段面分工」注补**判据句**：「**钉的主体是行为时，其载体字段不另挂本块**」，并点名 `pin-06`（`empty_probes`）／`pin-16`（`chain_switch_marks`）／`pin-12`（`delivered_rows`／`obs_rows`）三例——`pin-12` 由此**明确不属本块**（其字段属 `Verdict`、行为面挂 `specs/verification.md`） |
| **SZ-7**（低） | **采纳** | `docs/runtime-refactor/00-决议与方法.md` 流水 20 的 `NOTICE_TYPES` 表述已就地更正（改为「三族＋通知类型不在本块，见流水 24」）；同日新增**流水 24** 记录本块整条评审批 |

**净结果**：SZ-1…SZ-7 **全部采纳**（其中 SZ-3／SZ-5 改卡、SZ-2 另就地改 `specs/agent-loop.md` 三处、SZ-7 改流水）。复审给出的**两条必须先修（SZ-1／SZ-2）已清**，其余随批已清。**无升 Owner 项**（`origin` 自立形状已标「待 Owner 过目」，属过目件而非裁决件）。
