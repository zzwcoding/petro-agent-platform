- 日期：2026-10-15 ｜ 状态：**评审发现清单（待 L0 逐条处置）**
- 本清单只产发现，不修改任何现存文件。

---

## 一、结论摘要

1. **骨架站得住**：十节齐、标题逐字、无裸限值、不做什么表锚点齐、不降级节有「合法降级路径：无」＋机读信号声明；行为与 `walk/08/09/10` 及 `裁决表` §06/§08/§09/§10 逐条对得上，不需推翻。
2. **但闸层有一处高**：「模型调用唯一出口＝`gateway_adapter`」错挂 **B6 契约**并称「已真跑」——B6 只禁 `litellm` 出 `appv2.infra.llm_client`，**不含**「runtimev2 各块绕过 `gateway_adapter` 直引」这一面，该面由 **R7 契约**覆盖（`specs/clarification.md:63,127`）。
3. **一致性与覆盖另有多处**：行为 5 含含糊词「尽量」；缺一条「机读信号在场」验收行；AST 机检行缺豁免面；四动作含 `discover` 但接口只建模 ask/finalize 两出口；错误契约与行为 8／边界集不自洽；与已定稿 `agent-loop.md` 冲突（三动作／子问题含 `tool`）。
4. **无幻影闸**：本规格引用的 `B6`／`R5b`／`R1` 在 `specs/modules.md` 与 `tools/importlinter_v2.toml` 均在；`R5b` 契约 source 显式含 `appv2.runtimev2.clarification`，**真覆盖 runtimev2**。
5. **共 12 条发现：L0 零 ｜ 高 1 ｜ 中 6 ｜ 低 5。**

---

## 二、发现清单表

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
| --- | --- | --- | --- | --- |
| F-01 | **高** | **模型出口红线错挂闸、且称「已真跑」不成立**：框架红线把「模型调用唯一出口＝`gateway_adapter`」挂到 **B6 契约**，挂钩表同挂「边界闸 B6｜已真跑」。但 `tools/importlinter_v2.toml` 的 B6 契约 `source_modules=["appv2"]`、`forbidden=["litellm"]`（只禁 litellm 出 infra），**不覆盖 runtimev2 块绕过 `gateway_adapter` 直引这一面**；覆盖该面的是 **R7 契约**（`forbidden=["appv2.infra.llm_client"]`，source 含 runtimev2 十七块）。真源 `specs/modules.md` 该行明说「B6 契约只禁 litellm 出 infra，**不含**『绕过 `gateway_adapter` 直引』这一面，故单列 R7」。已定稿样板 `understanding.md` 已改指 R7（含 B6 注），本规格与 `tool_matching.md:74` 同款错挂。 | `specs/clarification.md:63,127`；`tools/importlinter_v2.toml:55-62`（B6）／`:113-117`（R7）；`specs/modules.md:522`（R7 行）；`specs/understanding.md:60,63,127` | 红线第 1 条与挂钩表该行均改指 **R7 契约**，并注明「B6 只管 litellm 出 `infra`，不含绕过 `gateway_adapter` 直引面」；写法照 `understanding.md:60` 同款 |
| F-02 | 中 | **行为 5 含含糊词「尽量」**：判据 §三-2 明列「凡出现『尽量／合理／必要时／视情况』即不合格」，行为 5「先探后问为首选策略：**尽量**先 `discover`」直接命中。该句是给模型的策略，落不到唯一 `assert`。 | `specs/clarification.md:73`；`docs/spec-process.md:36`（§三-2） | 把「尽量」改为可断言口径（如「口径歧义且台账已有候选时，发射 `discover` 取候选后再 ask」）或标为模型侧策略并说明不属程序验收面 |
| F-03 | 中 | **缺「机读信号在场」验收行**：`docs/spec-format.md` §二 第 7 节／自查 10 要求「任何截断／缺位／降级必须产生机读信号，且验收里有一条断言『该信号在场』」。本规格在「不降级」节声明了信号（ask 帧／`pending_ask`／step payload 拒因字段／notice），但验收表（17 行）**无一条断言信号在场**；两份样板均有专行（`understanding.md:105::reporting_signal_present`／`tool_matching.md:111::rejection_signal_present`）。 | `specs/clarification.md:88-89`（信号声明）↔`:93-110`（无该行）；`specs/understanding.md:105`；`specs/tool_matching.md:111` | 补一行验收（如「拒因／截断的机读信号在场（ask 帧／`pending_ask`／step payload／notice）」＋测试标识） |
| F-04 | 中 | **AST 机检行缺「豁免面」界定（与两样板不一致）**：验收行断言「程序侧无词表／正则语义判断」，但本模块必须做**逐字子串**校（行为 8「内容须能在台账注入块里逐字求得」）与闭世界 schema 对账——属形态处理，豁免面未界定，与「无词表／正则」断言边界不清（自相矛盾风险）。两份样板都在 AST 行写明豁免面。 | `specs/clarification.md:108`；`:76,109`（逐字校）↔ `specs/understanding.md:104`；`specs/tool_matching.md:110` | 照样板在同款行补「豁免面＝形态处理（逐字子串／集合成员判定不算语义词表／正则）」 |
| F-05 | 中 | **`discover` 出口未建模（接口与行为不自洽）**：行为 1／接口「四动作闭世界＝`discover｜decompose｜ask｜finalize`」（闭世界校验四值），但 `ClarifyOutcome` 只建模两出口 `ClarifyAsk｜ClarifyFinal`——`discover` 的返回形／去向无着落。据现状 `discover` 经 `next_intent=discover` **交 `discover` 节点**执行（不在本节点内直调工具），故 `discover` 是一次「出去再回来」的出口，接口应显式建模或写明由 `orchestration` 路由承接。 | `specs/clarification.md:40,54`（两出口 vs 四动作）／`:73`（先探后问）；`docs/runtime-refactor/recon/E1-澄清节点.md:64,74`（零工具直调；`discover→NODE_DISCOVER`） | 在接口定义补 `discover` 的出口形（或写明该动作经 `orchestration` 路由、本块不返回），并同步验收 |
| F-06 | 中 | **错误契约与行为 8／边界集不自洽**：错误契约列出的拒绝原因只有「动作越界／子问题条数越界／`ledger_notes` 为空／`chain` 越界」；而行为 8 要求 `ledger_notes`「须能在台账注入块里逐字求得」、边界集行断言「`ledger_notes` 语义改写（非逐字）→ 判违约」——**「非逐字」未进闭世界 schema 拒绝原因清单**，程序对账面缺这条判据。 | `specs/clarification.md:56`（错误契约）↔`:76`（行为 8）／`:109`（边界集） | 把「`ledger_notes` 非逐字（注入块内求不得）」补进错误契约的拒绝原因枚举，与行为 8／边界集对齐 |
| F-07 | 中 | **与已定稿 `specs/agent-loop.md` 冲突（澄清动作集与子问题字段）**：`agent-loop.md` 行为 1 写「业务澄清…发射**三动作**闭世界 `discover｜decompose｜ask`」，且 `QuestionGroup` 子任务形为 `subtasks[{id/question/ledger_notes/**tool**/chain}]`；本规格为**四动作**（含 `finalize`）、`Subtask` **无 `tool`**。按已定裁决（`裁决表` §10：`tool` 归匹配相位；`walk/08` §一：四动作含 finalize）本规格为对，`agent-loop.md` 待同步。 | `specs/clarification.md:54,47-52` ↔ `specs/agent-loop.md:61-64`；`docs/runtime-refactor/walk/裁决表.md:20`（§10）；`CONTEXT.md:22`（`QuestionGroup` 已去 `tool`） | 回阶段 2 同步 `specs/agent-loop.md`（三动作→四动作；子任务形去 `tool`），或标其为陈旧待改 |
| F-08 | 低 | **「不做什么」缺「解析与 schema 校验本体」行**：两份样板均有「模型输出的解析与 schema 校验本体 → `parsing`」一行，本规格范围围栏无此排除，而本块把「闭世界 schema 对账」写在行为 1、错误契约（抛错），与 `parsing` 卡职责（「模型输出解析、发射 schema 校验、子任务与问题组载荷定型」）重叠。 | `specs/clarification.md:13-23`（无不含该行）↔ `specs/understanding.md:20`；`specs/tool_matching.md:20`；`specs/modules.md:359`（`parsing` 卡职责） | 补一行「解析与 schema 校验本体 → `parsing`」，或写明本块只消费 `parsing` 出口 |
| F-09 | 低 | **红线「禁手写替代」未写对应闸名**：第 4 条「禁手写替代：不得自建模型客户端、不得绕过 `gateway_adapter` 直连上游」未写「对应闸名／验收写法」，而前三条都写了；两样板同条均补了闸名（＋「无旁路」行为断言）。 | `specs/clarification.md:65` ↔ `specs/understanding.md:63`；`specs/tool_matching.md:77` | 补「对应闸：R7 契约 ＋『无旁路』行为断言」（与 F-01 一并落） |
| F-10 | 低 | **行为 6 阈值不可断言**：「词典层**变大**即转按需检索（阈值纪律）」——「变大」无数量口径，`assert` 落不到唯一结果（承 `walk/08` §七 Q-A 的「阈值纪律」但真源亦未给数值）。 | `specs/clarification.md:74`；`docs/runtime-refactor/walk/08-澄清-意图澄清.md:74` | 补可判口径（如词典条数阈值）或明示「阈值待定、暂以全量注入为唯一现行为」 |
| F-11 | 低 | **错误契约用「抛异常」而同类样板用「返回拒因」写法不一致**：本规格写「发射不合 schema … → **抛 `ClarifyEmissionError`**（携带拒因），并拒因回喂、回到澄清相位重决策」；已定稿 `tool_matching.md` 对同一「拒因回喂重发射」模式用**返回结构化拒因**（`ToolMatchRejection`，由 `orchestration` 回喂），不抛异常。「抛异常」＋「同相位回喂重决策」的控制流两说，写法与样板不统一。 | `specs/clarification.md:56` ↔ `specs/tool_matching.md:67` | 统一为样板写法（返回结构化拒因），或写明抛出方／捕获方与回喂接缝 |
| F-12 | 低 | **覆盖：`CONTEXT.md`「发射判据」词条的『ask 仅限两白场』与『台账命中＋窗已定＝禁再 discover』未落本规格任何节**：本规格行为 2–5 覆盖时间窗规则与「口径歧义→反问」，但未写「ask 只在两种白场」的闭集，也未写「台账命中且窗已定→禁再 discover（直发分解）」。 | `CONTEXT.md:24`（发射判据）；`specs/agent-loop.md:95-97` ↔ `specs/clarification.md:69-83`（无对应条） | 补一条行为（或写明该纪律落在 `prompts` 合同文本／`gate` 侧），并同步验收 |

---

## 三、逐条回答 14 问

**Q1 十节齐 ＋ 标题逐字？——无发现。**
十节齐、逐字命中 `docs/spec-format.md` §二之二的十个固定名：`## 目标`(`:7`)｜`## 不做什么`(`:11`)｜`## 触及的模块`(`:25`)｜`## 接口定义`(`:35`)｜`## 框架与依赖红线`(`:60`)｜`## 行为约定`(`:67`)｜`## 不降级与静默禁令`(`:85`)｜`## 验收测试`(`:91`)｜`## 依赖与风险`(`:112`)｜`## 与闸的挂钩表`(`:120`)；`状态: 草稿` 行在场（`:3`）。触及模块首列（clarification／prompts／parsing／gateway_adapter／state）∈ `modules.md` 已声明。

**Q2 行为约定每条能否写成 `assert`？——有 2 条发现。**
含糊词 `grep 尽量|合理|必要时|视情况|酌情|适当|若干` **命中 1 处**：行为 5 的「尽量」（**F-02**）。其余行为 1–15 连续无缺号（`:69-83`），大体为条件→结果形。另 **F-10**：行为 6「变大即转按需」阈值不可判。

**Q3 数字有无裸值、能否指真源？——无发现（无裸限值）。**
`grep [0-9]` 仅命中原可追溯项：`近 30 天`（`:71`，真源 `walk/08` §七 Q-B；验收行 `:100` 同述）、章节互指；封顶数值显式「一律引统一预算表…本规格不写字面值」（`:75`，真源 `裁决表.md` §06-A）。无裸限值、无横切事实复述。

**Q4 不做什么每条「由谁承担＋锚点」？——无发现（一处缺项见 F-08）。**
9 行（`:13-23`）全部有落点（模块 `gate`／`tool_matching`／`execution`／`preconditions`／`persistence`／`gateway_adapter` 或裁决 `walk/00` §二、`walk/09/10` §七），锚点均为 `文件#节` 形式。**F-08**：缺「解析与 schema 校验本体 → `parsing`」一行（两样板均有）。

**Q5 框架红线闸名是否真存在／source 是否真覆盖 runtimev2？——无幻影编号；1 条高（F-01）＋1 条低（F-09）。**
「无点名框架」✔（`:62`）。`R5b`（`:64,126`）在 `tools/importlinter_v2.toml:100-105` **真实存在且 source 含 `appv2.runtimev2.clarification` 等 16 块**，「已真跑」属实 ✔。**F-01**：`B6`（`:63,127`）虽真实存在，但 source＝`appv2`、`forbidden=litellm`，**不覆盖** gateway_adapter-only 面；真覆盖者为 `R7`。全篇 `R*` 引用仅 R5b／R1（R1 在 `modules.md` 与 linter 均在），**无真源不存在的编号**。**F-09**：第 4 条无闸名。

**Q6 不降级与静默禁令？——有 1 条中（F-03）。**
合法降级路径「**无**」在场（`:87`）✔；信号声明（`:88-89`）＋静默禁令引红线原文 `arch/P7a-交接包与挂账清单.md` A-P7a-37（`:89`）✔。**F-03**：缺一条断言「机读信号在场」的验收行（样板均有）。

**Q7 验收测试：每行有标识／边界集保留集／有无测不出东西的行？——有 1 条中（F-04）。**
17 行（`:95-110`）**逐行有反引号测试标识**；路径约定 `tests/domains/test_v2_clarification.py::…` 与本仓既有约定一致（先例 `spec-review/tool_matching-评审.md:198`）；【边界集】`:109`＋【保留集】`:110` **两行齐** ✔。**F-04**：`:108` AST 行缺豁免面（`assert` 边界不清）。`:109`（非逐字→违约）落不到错误契约枚举见 **F-06**。

**Q8 与闸的挂钩表？——已填；1 条高（F-01）。**
表在场逐条填（`:122-132`）；末行「纯范围排除→人审」写了接不上的原因且理由站得住（`:132`）✔；「已进 CI」经先例核实（spec gate 在册）✔。**F-01**：`B6` 行错（覆盖面对不上，「已真跑」为部分覆盖）。`R5b` 行属实。

**Q9 与 `walk/` 决策是否冲突？——无直接冲突；1 处跨规格冲突（F-07）。**
逐条：`walk/08` §一 时机规则→行为 2；§七 Q-A 台账注入→行为 6；Q-B 默认窗＋口径不默认→行为 3/4；Q-C 先探后问→行为 5。`walk/09` §七 Q-A 覆盖交模型→行为 9；Q-B 无依赖→行为 10；Q-C ≤4 进预算表→行为 7。`walk/10` §七 Q-A 合并卡→行为 11；Q-B 恢复重取→行为 13；Q-C 无限等→行为 14；§一 封顶≥6→行为 15。`walk/06` §三/§六-B 挂起语义→行为 12。语义交模型／只读落执行层／真流式／禁用词交模型／核验零模型／重写不是改：本块只涉「语义交模型」（行为 1/9）与「重写不是改」，均已守。**F-07**：与已定稿 `agent-loop.md`（三动作／含 `tool`）冲突。

**Q10 覆盖：`walk/08/09/10` 疑问与差异＋`synth/S1` M2？——全覆盖；无越界；2 处缺口（F-05、F-12）。**
`walk/08` Q1(6)/Q2(注入)/Q3(默认窗)/Q4(discover 边界)→行为 1/6/3/5；`walk/09` Q1(≤4)/Q2(覆盖校验)/Q3(无依赖)/Q4(路线模型标)→行为 7/9/10/1；`walk/10` Q1(6)/Q2(计数)/Q3(重取)/Q4(无超时)→行为 15/12/13/14。`S1` M2（`S1:25`）的清晰项（挂起/恢复、连续澄清截断、决策语义）均有落（行为 11–15）；`S1` 表 B 的票级项（V2-25/V2-52/V2-59/V2-70/V2-80e）未逐票核（见未验证）。**F-05**：`discover` 出口未建模（`walk/06` 发现小循环无对口接口）；**F-12**：`CONTEXT.md` 发射判据未落。**把别的块的事写进来：未发现**（查数／选工具／过闸／挂起落库均显式排除）。

**Q11 总纪律残留（程序替模型做语义判断）？——无「词表/正则猜语义」设计；1 处须处置（F-04）。**
四动作由模型出结构化发射、程序只做闭世界 schema 对账（行为 1）＋覆盖校验交模型（行为 9）＋程序只校格式，方向与 `00` §二一致 ✔。**F-04**：`ledger_notes` 逐字子串校与「无词表／正则」断言的边界（豁免面）未界定。

**Q12 与模块卡一致？——一致（无「须回阶段 2 改卡」项，除 F-07 涉他文）。**
①职责：卡 `modules.md:149-152`（「澄清——意图澄清、分解问题、反问挂起与恢复」）＝本规格目标 ✔。②公开接口：卡 `modules.md:156`＝`def clarify(state: RunState) -> ClarifyOutcome: ...`，规格 `:38` **逐字一致** ✔。③依赖：卡 `modules.md:160`（`prompts`／`parsing`／`gateway_adapter`／`state`）与本规格「触及的模块」表（`:27-33`）＋依赖节（`:114`）**完全一致** ✔。**F-07** 的冲突在 `agent-loop.md` 侧（非本卡），建议回阶段 2 同步该文。

**Q13（附加）与两份已定稿样板同类条款写法是否一致？——大体一致，4 处不一致。**
- **一致**：框架红线句式（「无点名框架」＋禁 langgraph→R5b）；挂钩表列式与末行人审行＋原因；边界集／保留集两行结构；`synth/` 前缀（`:88` 写 `synth/S6-…` ✔）。
- **不一致 ①（F-01）**：`understanding.md:60,63` 模型出口已改指 **R7**（并注 B6 不含该面），本规格仍写 **B6**（`tool_matching.md:74` 同款——该文为已定稿样板，两样板间亦不一致）。
- **不一致 ②（F-04）**：两样板 AST 机检行均有**豁免面**（`understanding.md:104`／`tool_matching.md:110`），本规格无。
- **不一致 ③（F-03）**：两样板均有「机读信号在场」验收行（`understanding.md:105`／`tool_matching.md:111`），本规格无。
- **不一致 ④（F-11）**：同类「拒因回喂不修补」，`tool_matching.md:67` 用**返回结构化拒因**，本规格用**抛异常**。

**Q14（附加）`clarification` 是否也该依赖 `tools`（公开面）？——倾向「不依赖」（卡正确）；但规格需写明 discover 是发射/路由出去。**
证据：①`recon/E1` 明记 clarify_node「**本段零工具直调**（`discover` 经 `next_intent=discover` 交 `discover` 节点）」(`E1:64,74`)；②`synth/S6` 事件 3 `tool`（工具调用结果）**发射单元＝M5（discover/execute）**，非 M2（`S6:18`）；③`modules.md` `execution` 卡职责含「**发现**、执行、观察回流」(`modules.md:209`)、`tools` 卡 `ToolRegistry.call` 为「agent 与世界的唯一接触面」(`modules.md:126`)。据此，`discover` 的工具调用在 `execution` 侧执行，`clarification` 只发射意图并消费观察，**不需要直接依赖 `tools`**——卡依赖（`prompts`／`parsing`／`gateway_adapter`／`state`）正确，**不建议改卡**。遗留：本规格未写明「`discover` 是发射/路由出去、由 `execution` 执行」，易被读作本块直调工具（与 **F-05** 同一处，建议一并补写）。**未验证**：`appv2/runtimev2/` 新码未落，无法以运行时证据复核（见 §四）。

---

## 四、未验证清单 ＋ 覆盖自检

**未验证（查了什么、查到什么程度）**

1. **`appv2/runtimev2/` 新码是否已落**：未核目录；`tools/importlinter_v2.toml` 的 R5b／R6／R7 契约对空模块集恒 KEPT，本次「真覆盖」结论只据契约 source 判定，未跑 `lint-imports` 实测（本步只读、不跑闸，避与工作时间线冲突）。
2. **`synth/S1` M2 表 B 的票级项**（`V2-25` 反问卡拒因分形／`V2-52` 工具目录化澄清／`V2-59` 澄清轮2装配／`V2-70 clarify_capped`／`V2-80e` 拒因人话＋反问接地）：只据 `S1:25` 单元行采信，未逐票读票面，未据此判定覆盖。
3. **`synth/S6` notice 的 `type` 闭世界**：本规格写「类型取自 `synth/S6-事件与帧目录.md`」，`S6` §一 notice 行只列键集 `{type,gates,content}` 未列 `type` 值；「到顶截断」是否有对应 type 未核（沿用先例 `understanding-评审.md` 同项）。
4. **`ask` 选项个数上限（2–4）**：`recon/E1` R-E1-10 记「ask 需 prompt＋2~4 选项（校验在解析侧）」，`walk/10` §三列为缺口（「本地无直接论述」）；本规格 `ClarifyAsk.options` 未给基数约束——是否应进错误契约**未定论**，故未计入发现。
5. **`import-linter` 是否已挂 CI**：未重核 CI 配置（沿用先例结论：边界闸在 CI）。
6. **F-07 的另一侧修法**：`specs/agent-loop.md` 是否属「变更路由」需 Owner 知悉、由谁同步未定。

**覆盖自检**

- **已实读文件**：`specs/clarification.md`（主对象，全文 133 行）；`docs/spec-process.md`（§三）；`docs/spec-format.md`（全文）；`docs/runtime-refactor/walk/08-澄清-意图澄清.md`、`walk/09-澄清-分解问题.md`、`walk/10-澄清-澄清反问挂起.md`、`walk/06-过程图-循环挂起判断.md`、`walk/裁决表.md`、`walk/00-设计总纲.md`、`walk/判断归责表.md`（全文）；`specs/modules.md`（17 卡＋`## 边界规则`，全文）；`specs/understanding.md`、`specs/tool_matching.md`、`specs/agent-loop.md`、`specs/tools.md`（全文）；`CONTEXT.md`（全文）；`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md`、`synth/S6-事件与帧目录.md`；`docs/runtime-refactor/recon/E1-澄清节点.md`；`docs/runtime-refactor/spec-review/tool_matching-评审.md`、`understanding-评审.md`（全文）；`tools/importlinter_v2.toml`（全文）。
- **发现条数**：**12 条**。**按严重度计数**：**L0 0 条 ｜ 高 1 条 ｜ 中 6 条 ｜ 低 5 条**。
- **14 问逐条回答**：Q1–Q12 ＋附加 Q13／Q14 **全部作答**，每条带 `file:line` 或 `file#节` 锚点；无锚点条目已剔除。
- **本步只读声明**：除本产物文件外未修改任何现存文件，未写入仓库其他位置；未跑任何闸（只读契约文件与文档）。

---

## 五、L0 逐条处置（2026-10-15）

> 12 条**全部采纳**（L0 零条，无需 Owner 裁）。其中两条由 L0 直接办，其余 10 条交修订步。

| 编号 | 严重度 | 处置 | 落点 |
| --- | --- | --- | --- |
| F-01 | 高 | **采纳→L0 已修（样板）＋交修订步（本规格）** | **样板不齐一并治**：已定稿的 `specs/tool_matching.md` 同款错挂 **B6**（应 **R7**）——L0 直接更正并记录；本规格交修订步改指 **R7**（注明 B6 只管 litellm 出 `infra`） |
| F-02 | 中 | 采纳→修订步 | 行为 5 的「**尽量**先 discover」改为可断言口径（或标明属模型侧策略、不入程序验收面） |
| F-03 | 中 | 采纳→修订步 | 补一行验收：**机读信号在场**（ask 帧／`pending_ask`／step payload 拒因／notice），与两样板同款 |
| F-04 | 中 | 采纳→修订步 | AST 行补**豁免面**（逐字子串／集合成员判定＝形态处理，不算语义词表／正则） |
| F-05 | 中 | 采纳→修订步 | 接口补 `discover` 出口的着落（**经 `orchestration` 路由、本块不直调工具**——真源 `recon/E1:64,74`「零工具直调」「discover→NODE_DISCOVER」） |
| F-06 | 中 | 采纳→修订步 | 错误契约的拒绝原因枚举**补「`ledger_notes` 非逐字（注入块内求不得）」**，与行为 8／边界集对齐 |
| F-07 | 中 | **采纳→L0 已修** | `specs/agent-loop.md` 同步已定裁决：**三动作→四动作**（含 `finalize`）、子任务形**去 `tool`** |
| F-08 | 低 | 采纳→修订步 | 「不做什么」补一行「模型输出的解析与 schema 校验本体 → `parsing`」 |
| F-09 | 低 | 采纳→修订步 | 红线第 4 条「禁手写替代」补闸名（**R7 契约**＋「无旁路」行为断言），与 F-01 一并落 |
| F-10 | 低 | 采纳→修订步 | 行为 6「词典层变大即转按需」补可判口径，**或明示「阈值待定、暂以全量注入为唯一现行为」** |
| F-11 | 低 | 采纳→修订步 | 错误契约**统一为样板的「返回结构化拒因」写法**（不抛异常），并写明回喂接缝 |
| F-12 | 低 | 采纳→修订步 | 补一条行为：**ask 仅限两种白场**（阈值判断形口径反问／目标-对象-口径真歧义）＋**台账命中且窗已定 → 禁再 discover**（真源 `CONTEXT.md` 发射判据词条） |

**给修订步的修复单**：C-1…C-11（对应 F-01（规格侧）／F-02／F-03／F-04／F-05／F-06／F-08／F-09／F-10／F-11／F-12）。

> 笔误（本表行）：本条写「C-1…C-10」，实际条目数＝**11**（C-11 对应 F-12）——详见 §六 N-5。

---

## 六、复审（2026-10-15）

**结论**：C-1…C-11 **11 条全部闭合**（逐条以文件实际内容为凭，不采信回执自述）；12 条判据中 **第 2 条与第 11 条各有一处同源发现（N-1）**，其余 10 条无发现；另出 **5 条新问题**（2 中／3 低，其中 N-1 是本轮最要紧者）。修订**未推翻骨架**，但有 1 处新增行为（行为 16）**不可程序断言且无出口**，属判据 §三-2 不合格。**判定：不宜直接定稿**——须先处置 N-1（推荐：把行为 16 的「白场」半句按行为 5 同款标为模型侧／Skill 指南承载，验收行只留机械半句；或补接口字段＋拒因枚举），N-2／N-3 建议一并顺改，改完即可定稿。

### A. C-1…C-11 逐条闭合核（以文件实际内容为准）

| 条目 | 闭合？ | 证据锚点 | 备注 |
| --- | --- | --- | --- |
| C-1（F-01 规格侧） | **闭合** | `specs/clarification.md:69`、`:137`；`tools/importlinter_v2.toml:114-117`（R7）、`:56-59`（B6，source=`appv2`、forbidden=`litellm`）；`specs/modules.md` R7 行 | 红线第 1 条与挂钩表两侧均由 B6→**R7**，并注「B6 只管 litellm 出 `infra`，不含绕过 `gateway_adapter` 直引面」；写法与已定稿 `understanding.md:60,127` 同款。R7 **真实存在且 source 含 `appv2.runtimev2.clarification`**——「已真跑」在契约层面属实 |
| C-2（F-02） | **闭合** | `specs/clarification.md:79` | 「尽量」已删；改为「**属模型侧策略，不入程序验收面**」＋「程序侧只做闭世界 schema 对账，不验收该策略」。取舍写法**落进正文**（不止回执） |
| C-3（F-03） | **闭合** | `specs/clarification.md:116`；信号声明 `:95` | 新增验收行 `::clarify_signal_present`（ask 帧／`pending_ask`／step payload 拒因字段／notice），与两样板同款 |
| C-4（F-04） | **闭合** | `specs/clarification.md:115`、`:127` | 验收 AST 行**与**「依赖与风险」风险 2 检测手段**两处**均已补「豁免面＝形态处理（逐字子串校／集合成员判定不算语义词表／正则）」——回执「未覆盖风险 2」一条已不成立（现文两处齐） |
| C-5（F-05） | **闭合（有残余）** | `specs/clarification.md:60`＋验收 `:117`；真源 `recon/E1-澄清节点.md:64,74` | 采修复单选项 b（注明由 `orchestration` 承接、本块不返回）＋补验收行。**与「四动作闭世界」的校验声明基本自洽**：`:59` 仍保留 `discover` 为合法发射值（读得通「能发射」）。**残余**：发射 `discover` 后「本块不返回」与「经 `orchestration` 路由出去」之间的**信道未写**（无出口形／无字段）——见 N-2 |
| C-6（F-06） | **闭合** | `specs/clarification.md:62`（枚举含「`ledger_notes` 非逐字（在台账注入块内求不得）」）↔ `:82` 行为 8／`:119` 边界集 | 三处口径已对齐 |
| C-7（F-08） | **闭合** | `specs/clarification.md:18` | 「模型输出的解析与 schema 校验本体 ｜ `parsing` ｜ `specs/modules.md` `## parsing`」逐字照样板 |
| C-8（F-09） | **闭合** | `specs/clarification.md:71` | 「禁手写替代」已补 **R7 契约**＋「无旁路」行为断言，与 `understanding.md:63` 同款 |
| C-9（F-10） | **闭合** | `specs/clarification.md:80` | 「**阈值待定、暂以全量注入为唯一现行为**」落进正文；未编数字 |
| C-10（F-11） | **闭合** | `specs/clarification.md:41`、`:53-55`、`:62` | `ClarifyRejection`／`ClarifyReason` **规格内已定义**（`:53-55`），被 `:41`（ClarifyOutcome 成员）与 `:62`（错误契约）**一致引用**；写法与样板 `tool_matching.md:58-62` 同款；`ClarifyEmissionError` 已全篇无残留（grep 零命中）。**但引出 N-3**（`:60` 措辞漏列拒因出口） |
| C-11（F-12） | **闭合（有残余）** | `specs/clarification.md:90`＋验收 `:118`；真源 `CONTEXT.md:24` | 行为 16 与验收行均落，来源词条逐字对得上（`CONTEXT.md:24`「无场景词阈值判断形的口径反问、目标/对象/口径真歧义」「台账命中＋窗已定＝禁再 discover」）。**残余**：行为 16 前半不可程序断言且无出口——见 N-1 |

### B. 12 条判据逐条复跑

1. **十节齐 ＋ 标题逐字——无发现。** 逐字命中且顺序未变：`## 目标`(`:7`)｜`## 不做什么`(`:11`)｜`## 触及的模块`(`:26`)｜`## 接口定义`(`:36`)｜`## 框架与依赖红线`(`:66`)｜`## 行为约定`(`:73`)｜`## 不降级与静默禁令`(`:92`)｜`## 验收测试`(`:98`)｜`## 依赖与风险`(`:122`)｜`## 与闸的挂钩表`(`:130`)；`状态: 草稿` 在场（`:3`）。
2. **行为每条可 `assert`——1 处发现（N-1）。** 含糊词 grep（`尽量|合理|必要时|视情况|酌情|适当|若干`）**零命中**；行为 1–16 连续无缺号，1–15 均条件→结果形。**行为 16 前半「ask 仅限两白场（阈值判断形口径／真歧义）」不可写成唯一 `assert`**（需程序判「是否白场」＝语义判断，且无接口载体）——详见 N-1。
3. **数字有无裸值——无发现。** `近 30 天`(`:77`) 可溯 `walk/08` §七 Q-B（`walk/08:75,87`），验收行 `:107` 同述；封顶值显式「本规格不写字面值」(`:81`)。无裸限值、无横切事实复述。
4. **不做什么每条「由谁承担＋锚点」——无发现。** 表 10 行（`:13-24`），新增 `parsing` 行(`:18`)已在；各行锚点均为 `文件#节` 或模块卡。
5. **框架红线闸名——无发现（幻影编号为零）。** `R7`／`R5b`／`B6`／`R1` 均真实存在：`R7`(`linter:114-117`)、`R5b`(`:101-104`)、`B6`(`:56-59`)、`R1`(`modules.md` 边界规则；linter `:67-70`)。本规格 `R*` 引用仅 R7／R5b／R1，**无真源不存在的编号**。
6. **不降级与静默禁令——无发现。** 「合法降级路径：无」(`:94`)；信号声明(`:95`)＋截断不得静默引红线原文(`:96`，`arch/P7a-…md:98` A-P7a-37 存在，`arch/…` 为 RTF 语料惯用简写、两样板同款)；验收有信号在场行(`:116`)。
7. **验收测试——无发现（但 N-1 涉及的验收行不可实现）。** 19 行（`:102-120`）逐行有反引号标识；【边界集】`:119`＋【保留集】`:120` 两行齐；路径 `tests/domains/test_v2_clarification.py::…` 合本仓先例。
8. **与闸的挂钩表——无发现。** 表在场逐条填(`:132-142`)；`R7` 行已更正(`:137`)；末行「纯范围排除→人审」写明接不上原因(`:142`)，理由站得住。
9. **与 `walk/` 决策冲突——无发现。** 逐条对得上：`walk/08` §一→行为 2、§七 Q-A→行为 6(已补「阈值待定」)、Q-B→行为 3/4、Q-C→行为 5；`walk/09` §七 Q-A→行为 9、Q-B→行为 10、Q-C→行为 7；`walk/10` §七 Q-A→行为 11、Q-B→行为 13、Q-C→行为 14；`walk/06` §三/§六-B→行为 12。**跨规格冲突已消**：`specs/agent-loop.md:61-63` 已同步为**四动作**＋子任务形**已去 `tool`**（F-07 的 L0 修已落）。
10. **覆盖——无发现（N-1 属「落法」问题，非漏项）。** `CONTEXT.md:24`「发射判据」已落行为 16(`:90`)；`walk/08/09/10` 疑问全覆盖；`synth/S1:25` M2 单元（澄清＋挂起/恢复＋连续澄清截断）均有落；「把别块的事写进来」未见（查数／选工具／过闸／挂起落库均显式排除）。
11. **总纪律残留——1 处发现（N-1）。** 主体方向正确（四动作由模型定、程序只对账；覆盖校验交模型；程序只校格式）。**但行为 16 前半若按验收行程序化判定，即「程序替模型判语义」，与 `:115` AST 行 `::no_lexicon_or_regex_in_clarification` 相抵**——详见 N-1。
12. **与模块卡一致——无发现。** 签名 `def clarify(state: RunState) -> ClarifyOutcome: ...`(`:38`) 与 `specs/modules.md:156` **逐字一致**；依赖（`prompts`／`parsing`／`gateway_adapter`／`state`）与卡 `modules.md:160` 及本规格「触及的模块」表一致；卡未列举 `ClarifyOutcome` 成员，故新增 `ClarifyRejection` 成员**不违卡**，无需回阶段 2。

### C. 新增问题清单（修订引入／带出）

| 编号 | 严重度 | 发现 | 证据锚点 | 建议 |
| --- | --- | --- | --- | --- |
| **N-1** | **中** | **行为 16 前半（ask 仅限两白场）不可程序断言、无出口、且与总纪律相抵**：该条要求「ask 仅限阈值判断形口径反问／目标-对象-口径真歧义」，但①`ClarifyAsk`(`:42-45`) 无承载「白场类型」的字段，程序无从判定；②错误契约拒因枚举(`:62`)与 `ClarifyRejection` 注释(`:54`)**均未含该违规**——即违规无出口；③要程序判「是否白场」＝词表／语义判断，与总纪律（`walk/00` §二）及本规格验收行 `:115`（`no_lexicon_or_regex_in_clarification`）**相抵**。真源 `CONTEXT.md:24` 明记该纪律系「**Skill 指南承载**」（模型侧），故与行为 5 已采的「属模型侧策略、不入程序验收面」写法不一致。 | `specs/clarification.md:90`（行为 16）↔`:42-45`（无字段）／`:59,62`（无拒因）／`:115`（AST 行）／`:79`（行为 5 对照）；`CONTEXT.md:24` | 二选一：**(推荐)** 白场半句照行为 5 标为「模型侧／Skill 指南承载，不入程序验收面」，验收行 `:118` 只留机械半句「台账命中且窗已定 → 禁再 `discover`」；或补接口字段（如白场类型）+ 拒因枚举项，使可断言 |
| **N-2** | **中** | **C-5 路由信道未写（自洽性残余）**：`:60` 称「本块不返回」`discover`、由 `orchestration` 路由出去，但**未写本块把 `discover` 交给 `orchestration` 的信道**（出口形／字段皆无，且 `ClarifyOutcome` 已排除 `discover`）；验收行 `:117`「不返回」因此落不到具体可断言对象。零上下文实现者会卡在「模型发射 `discover` 后，本块返回什么／怎么告知编排」。真源 `recon/E1:64` 事实为经 `next_intent=discover` 交出——信道即此类，写清即可闭合。 | `specs/clarification.md:59,60,117`；`recon/E1-澄清节点.md:64` | 在 `:60` 补一句路由信道（如「经 `next_intent=discover`／编排协议交出」），验收行相应写实断言对象 |
| **N-3** | **低** | **接口节内部措辞不一致**：`:60` 写「`ClarifyOutcome` 的本块返回位**只含 `ClarifyAsk`｜`ClarifyFinal`**」，与 `:41`「`ClarifyOutcome = ClarifyAsk | ClarifyFinal | **ClarifyRejection**」及错误契约 `:62`（返回拒因）**不一致**——漏列拒因出口，易被读作拒因不是本块返回。 | `specs/clarification.md:41,60,62` | `:60` 补「｜`ClarifyRejection`」，或改写为「`discover` 不占返回位」而不列举 |
| **N-4** | **低**（非本规格行） | **跨文件引用偏差（F-07 修补带出）**：`specs/agent-loop.md:63` 把「选工具归②匹配相位」的真源写作「`裁决表` §10」，但 §10 实为「澄清 · 澄清反问（反问卡／重取／超时）」，与 `tool` 归属无关；「`tool` 归匹配相位」的真源是 `裁决表.md` **项目级裁决 #10**。 | `specs/agent-loop.md:63`；`docs/runtime-refactor/walk/裁决表.md:126-134`（§10 内容）／项目级裁决 #10（`裁决表.md` 项目级表内） | 将 `agent-loop.md:63` 的 §10 改指「项目级裁决 #10」 |
| **N-5** | **低**（本文件行） | **§五末行笔误**：写「修复单：C-1…C-10」，实际为 **C-1…C-11**（11 项，C-11 对应 F-12）；与本轮修订回执「已改 11」及本次复审口径不符。 | 本文件 `:124` | 改为「C-1…C-11」 |

### 未验证清单 ＋ 覆盖自检

**未验证**

1. **未跑 import-linter**：本步只读、未执行 `lint-imports`；`R5b`／`R7`「真覆盖 runtimev2」结论据契约 source（`tools/importlinter_v2.toml`）判定（对空模块集恒 KEPT），非运行时证实——沿用上轮同项。
2. **`appv2/runtimev2/` 新码未核**：`discover` 路由信道（N-2）与行为 16 的落地形态无可执行证据可对照。
3. **`synth/S6` notice 的 `type` 值闭世界未列**：`:95` 只引目录；`S6:23` notice 行仅列键集 `{type,gates,content}` 未列值，`type` 值集未核（沿用上轮同项）。
4. **`ClarifyAsk.options` 2~4 基数**：按 L0 判定不报（无真源依据，`walk/10` 只给 `{kind,prompt,options}`）。
5. **12 条判据之「与 walk 冲突」**只逐条核 `walk/06`／`08`／`09`／`10` 与 `裁决表` §06/§08/§09/§10，未重读全部 `walk/` 文。
6. **CI 是否已挂 spec gate／边界闸**：未重核 CI 配置（沿用先例结论）。

**覆盖自检**

- **本步实读文件**：`specs/clarification.md`（全文 142 行，逐行核）；`docs/runtime-refactor/spec-review/clarification-评审.md`（全文，含 §五处置表）；`clarification-修订回执.md`（全文）；`docs/spec-process.md`（§三）；`docs/spec-format.md`（全文）；`specs/understanding.md`、`specs/tool_matching.md`（两定稿样板全文）；`specs/agent-loop.md`（涉 F-07 段）；`specs/modules.md`（`## clarification` 卡＋边界规则 R1–R7）；`tools/importlinter_v2.toml`（B6／R1–R7 契约）；`CONTEXT.md`（发射判据等词条）；`docs/runtime-refactor/recon/E1-澄清节点.md`（全文）；`docs/runtime-refactor/walk/08`、`walk/09`、`walk/10`、`walk/06`（§七等目标节）、`walk/裁决表.md`（§06/§08/§09/§10＋项目级裁决）；`docs/runtime-refactor/synth/S6-事件与帧目录.md`（notice 行）、`synth/S1-重写单元与证据交叉矩阵.md`（M2 行）；`docs/runtime-refactor/arch/P7a-交接包与挂账清单.md`（A-P7a-37）；`docs/runtime-refactor/walk/00-设计总纲.md`（§二）。
- **发现条数**：A＝11 条闭合（含 2 条带残余）；B＝12 条判据（第 2、11 两条各 1 处同源发现；其余 10 条无发现）；C＝新增 5 条（**中 2／低 3**，其中 N-4／N-5 属跨文件与本文件行）。合计新增 **中 2 ／ 低 3**。
- **本步只读声明**：除本复审结论追加进本文件外，未修改任何现存文件；未写入仓库其他位置；未跑任何闸。

## 七、定稿（2026-10-15）

**复审提的 5 项 L0 收尾已办**：

| 复审条目 | 处置 |
| --- | --- |
| **N-1**（中，**卡定稿的一条**） | 行为 16 的「ask 仅限两白场」**改标为模型侧策略**（Skill 指南承载，**程序不验收、不做语义判断**——与行为 5 同款）；验收行只留**机械半句**「台账命中且时间窗已定 → 禁再 `discover`」，测试标识改 `::no_rediscover_when_window_set` |
| **N-2**（中） | `discover` 的**信道写实**：以 `next_intent="discover"` 交出、由 `orchestration` 路由到发现步执行、结果回本相位；并统一「本块返回位＝Ask｜Final｜Rejection」 |
| **N-3**（低） | 返回位口径统一（补上 `ClarifyRejection`），消除与接口块的不一致 |
| **N-4**（低，跨文件） | `specs/agent-loop.md` 的「`裁决表` §10」→「`裁决表` **项目级裁决 #10**」 |
| **N-5**（低，本文件） | §五 末行笔误 `C-1…C-10` → **C-1…C-11** |

**结论**：`specs/clarification.md` ＝ **已定稿**。工序六步走完。
