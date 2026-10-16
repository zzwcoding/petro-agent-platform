- 日期：2026-10-15 ｜ 状态：**回工补写**（独立复审打回项落实施工）
- 本次只改 `specs/tool_matching.md`，其它文件未动。行号均指改后文件（143 行）。

# tool_matching 规格回工补写（复审发现 #8）

| 修改点 | 改了什么 | 依据 |
|---|---|---|
| `specs/tool_matching.md:87` | 行为 4「不得为英文列名形（形态判定）」补**判定形**：值整体呈全小写字母开头、仅由 `[a-z0-9_]` 构成的 token 形；标注「**形状定义（本规格自立，待 Owner 过目）**，阶段 5 织网以此为准」；注记真源现状——`walk/11-匹配-工具阀.md` §一／§七仅记「禁英文列名」、未给判定形（§七 Q-A 裁的是工具描述三件套）；真源禁例 `oil_pressure`（`ontology/petro/skill-guides/eval-cases.md` AC-G11 两禁式之英文列名式） | 复审发现 #8（【中】英文列名形形状定义）；即 `spec-review/tool_matching-评审.md` F-06（改述为形态判定）的后续——形态判定无定义形则不可测 |
| `specs/tool_matching.md:109` | 验收行 `::metric_slot_not_english_column` 补判定形（全小写字母开头、仅 `[a-z0-9_]` 的 token 形——形状定义见行为 4），使断言可写：`oil_pressure` 呈形 → 判失败；`日产油量` 呈非该形 → 形状面通过 | 复审发现 #8（验收行原文 :109） |
| `specs/tool_matching.md:142` | 挂钩表补一行「`metric_slot` 英文列名形判定（形状定义见行为 4——本规格自立，待 Owner 过目）｜测试 `::metric_slot_not_english_column`｜待实现」 | 复审发现 #8 配套（硬要求逐条进挂钩表的版式纪律） |

## 上报项（升级 Owner）

1. **英文列名形形状定义无真源**：`walk/11-匹配-工具阀.md` §一仅记「禁英文列名」、§七 Q-A 裁的是工具描述三件套（要／保持／不做），`recon/K-上下文事件指南预算.md:394`（TOOLMATCH_CONTRACT）亦仅「metric_slot 必填非空禁英文列名」——**全证据面均无「何形算英文列名」的定义**。按复审预案，本规格已写为「形状定义（本规格自立，待 Owner 过目）」并升级上报：判定形暂取「值整体呈全小写字母开头、仅 `[a-z0-9_]` 构成的 token 形」（与真源禁例 `oil_pressure` 同形；`oil_output` 系复合注记禁式，归 guide 合同「禁英文列名/复合注记」的另一面）。**Owner 过目后**：若改判，须同步行为 4（:87）、验收行（:109）、挂钩行（:142）三处；若追认，建议回填 `walk/11` 作真源锚。

## 钉落点登记（无落点不硬挂）

- pin-24（相位合同一次性）在本块的回炉轮（拒因回喂）只是消费侧，本体归 state/context——**待 orchestration/context 规格**，不硬挂（与 preconditions 侧登记同源）。

## 验证

- `uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿**。未 git commit。

---

# 补记（2026-10-15 二轮）：英文列名形判定形 Owner 拍板 B 案，三处同步落地

- **拍板**：上报项 1 经 Owner 定 **B 案**——大小写不敏感 ASCII 标识符形：值整体呈 `[A-Za-z][A-Za-z0-9_]*`（首字符 `[A-Za-z]`、其余仅 `[A-Za-z0-9_]`，大小写都咬，`oil_pressure` 与 `WELL_NAME` 都咬）。fail-closed 取向：咬错的代价是模型从台账重提议，漏咬的代价是脏指标进查询——宁可误拒重提议，不可漏放列名形。
- **本轮改动面**：`specs/tool_matching.md` 行 87／109／142 三处措辞（行数不变，仍 143 行；测试标识 `::metric_slot_not_english_column` 不变）＋ `docs/runtime-refactor/walk/11-匹配-工具阀.md` 末追加补注节（只追加不改正文）。
  - `specs/tool_matching.md:87`（行为 4）：判定形改为「值整体呈 ASCII 标识符形——首字符 `[A-Za-z]`、其余仅 `[A-Za-z0-9_]`，大小写都咬」；删「**形状定义（本规格自立，待 Owner 过目）**」临时标注，改注「**Owner 2026-10-15 拍板 B 案**（fail-closed：宁可误拒重提议，不可漏放列名形）」；禁例改 `oil_pressure`／`WELL_NAME`（前者保留 AC-G11 锚，后者为大写形补例）；walk/11 现状注记由「§一／§七仅记『禁英文列名』、未给判定形」改为判定形真源锚指其末「补注（2026-10-15 Owner 拍板）」节。
  - `specs/tool_matching.md:109`（验收行）：判定形措辞同步为 ASCII 标识符形（Owner 2026-10-15 拍板 B 案，判定形见行为 4）。
  - `specs/tool_matching.md:142`（挂钩表行）：删「本规格自立，待 Owner 过目」，改「判定形＝ASCII 标识符形，见行为 4——Owner 2026-10-15 拍板 B 案」。
- **真源回填**：`walk/11-匹配-工具阀.md` 末「补注（2026-10-15 Owner 拍板）」节载：「『禁英文列名』的判定形状拍板为 ASCII 标识符形 `[A-Za-z][A-Za-z0-9_]*`（大小写都咬；禁例 oil_pressure/WELL_NAME）；真源锚回本节。」——上报项 1 的「建议回填 walk/11 作真源锚」就此落实（改判同步三处＋回填真源并行完成）。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿**。未 git commit。


---

## V1 发起面回改（主窗裁 doctrine）——2026-10-15

- **依据**：复审⑦处置（`docs/runtime-refactor/00-决议与方法.md` 流水 27 第①裁）——相位调模型一律经 `bookkeeping.call_model`（其内部唯一出口 `appv2.runtimev2.gateway_adapter`）。本次只改 `specs/tool_matching.md`（143→144 行）＋本记录，其它文件未动；未 git commit（主窗统一提交）。
- **修改点**（行号指改后文件）：
  1. 「触及的模块」依赖表（:36-37）：新增 `bookkeeping` 行（改动类型＝**新增依赖**；说明＝「模型调用发起面：经 bookkeeping.call_model（单点发起），本块不直引 gateway_adapter」）；同表 `gateway_adapter` 行说明由「模型调用唯一出口；本 spec 只消费」改为「模型出口（唯一出口仍归它）；本块不直引——经 bookkeeping.call_model 发起」。
  2. 「框架与依赖红线」（:78）：「模型调用唯一出口＝gateway_adapter」改为「**模型调用发起面＝`bookkeeping.call_model`（单点发起）；其内部唯一出口＝`gateway_adapter`**」，补「import 落点＝`appv2.runtimev2.bookkeeping` 包根——R2 禁深层子模块」；R7 括注改准为「禁直引 `appv2.infra.llm_client`——模型出口仍唯一归 `gateway_adapter`」＋「发起面收敛为规格层 doctrine，不设闸——主窗 2026-10-15 裁」。
  3. 「框架与依赖红线」禁手写替代条（:81）：R7 括注由「模型只经 `gateway_adapter`」改为「模型出口唯一归 `gateway_adapter`——发起经 `bookkeeping.call_model`」。
  4. 「依赖与风险」依赖行（:122）：补 `bookkeeping`（模型调用发起面——`call_model` 单点发起）；`gateway_adapter` 括注改为「经 `call_model` 的内部唯一出口，本块不直引」。
  5. 「与闸的挂钩表」（:138）：「模型调用只经 `gateway_adapter`」行改为「模型调用经 `bookkeeping.call_model` 发起（单点发起；其内部唯一出口 `gateway_adapter`）」；挂钩列注「出口面 R7；发起面为规格层 doctrine，不设闸」；现状列不变。
- **不加闸（裁定照录）**：importlinter 边界闸**不随本批加**——R7「只经出口」＋R8 语义不变，doctrine 是规格层不是闸层（主窗 2026-10-15 裁）。
- **契约字面核对（未改 toml）**：逐条实读 `tools/importlinter_v2.toml`——R7（forbidden＝`appv2.infra.llm_client`；source 含 `appv2.runtimev2.bookkeeping`）与 R2（业务相位 forbidden 含 `appv2.runtimev2.bookkeeping.*` 深层子模块、不含包根）均与新 doctrine **无字面冲突**。实现期注意：相位 import 只许 `appv2.runtimev2.bookkeeping` 包根（R2 面）。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（20 份规格）**。均 exit 0（批次一改后实跑）。

---

## 流水 31 裁决落笔（裁决一＝拒因转换在消费方；裁决二＝同参重投闸拦截实现归 execution）——2026-10-15

- **依据**：主窗流水 31①／②（2026-10-15）。①销 `parsing-评审.md` P-09；②销 P-10——本块「只被拦、不实现」的被拦位补明拦截实现落点。
- **修改点**（只改 `specs/tool_matching.md`，144→146 行）：
  1. 行为约定新增**行为 11**「解析拒文→结构化拒因的转换归本块（消费方）」（:95）——`str` → `ToolMatchRejection` 机械适配（str 逐字进 `reason` 字段＋映射拒因枚举）、零语义判断、parsing 不感知本块类型（R3）。
  2. 验收测试表新增一行（:114）：`tests/domains/test_v2_tool_matching.py::parse_rejection_str_to_tool_match_rejection_consumer_side`（待织网，阶段 5）。
  3. 风险 4（:129）「本块只被拦、不实现」后补一句「**拦截实现归 `execution`（dispatch 统一出口，流水 31②）**——触发／拦截／回喂均不在本块」；检测手段补 `execution`。
- **未随批改面（登记交主窗）**：「不做什么」同参重投闸行（:26）「本块只在其发射点**被拦**」未补拦截实现落点——票面只授权风险 4 补句；语义由风险 4 承载，建议主窗随批收词。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（21 份规格）**；`uv run lint-imports --config tools/importlinter_v2.toml` → **Contracts: 18 kept, 0 broken**。均 exit 0（改后实跑）。未 git commit（主窗统一提交）。

---

## 拆票期卡级修正（流水 50）——2026-10-16

- **缺口描述**：`tickets/v2-refactor/RT-W4-03-tool_matching.md`「接口缺口」条原文（逐字）：「① 规格行为 11 行要求本块产出「提及 vs 执行」结论、pin-31／pin-14 要求 `preconditions` 消费其**时间窗结论**，但 `specs/modules.md` `## tool_matching` 卡与规格「接口定义」的 `SubtaskMatch` **均未列这两个结论的字段**（名字／类型／承载物未定）；② 规格 `class MatchReason:` 正文为 `...`，**拒因枚举的字段面未定义**。」
- **裁口径（主窗 L0，2026-10-16）**：给 `SubtaskMatch` 补**一个**字段 `mention_mode`（取值闭世界＝`executed`／`mentioned_only`）；`MatchReason` 补拒因枚举成员清单（成员名与逐字拒文从规格「拒因」相关行／recon 取真源，**不许编造**）；`modules.md` 卡与规格接口节**同批改（两处不许脱节）**，两边各加一句注「2026-10-16 补：pin-31/pin-14 消费面（流水 50）」。
- **改动位置**（行号指改后文件；`specs/tool_matching.md` 146→161 行、`specs/modules.md` 635→640 行）：
  1. `specs/tool_matching.md:56`——`SubtaskMatch` 补 `mention_mode: Literal["executed", "mentioned_only"]`。
  2. `specs/tool_matching.md:65-67`——`class MatchReason:` 正文由 `...` 改为 `kind: Literal["缺配", "多配", "编号不符", "必填缺", "枚举越界"]` ＋ `reason: str`。
  3. `specs/tool_matching.md:75`——新增「`mention_mode` 是闭世界两值」条（三条逐字依据引文＋越界/缺字段判失败＋注「**2026-10-16 补：pin-31/pin-14 消费面（流水 50）**」）。
  4. `specs/tool_matching.md:76-84`——新增「`MatchReason` 的拒因枚举＝五类闭世界」条＋逐字拒文表（五类成员 × 逐字拒文 × 字面锚）。
  5. `specs/tool_matching.md:86`——新增「占位记法」条；`:87`——新增「未归类一条（不发明第六类）」条。
  6. `specs/modules.md:178-180`——`## tool_matching` 卡公开接口补 `SubtaskMatch`（含 `mention_mode`）＋ `MatchReason` 两行注释；`:183`——新增卡级修正注（逐字含「**2026-10-16 补：pin-31/pin-14 消费面（流水 50）**」「卡与规格接口节同批改，不许脱节」）。
- **依据引文（三处，逐字亲读）**：① 规格「接口定义」节 `specs/tool_matching.md:73`「**本块亦产出「提及 vs 执行」的结论**（废弃词闸的判断；Owner 裁决 #12）——**与 `caliber_key` 同批产出**，交 `preconditions` 判定序第 1 位做机械分派」；② `docs/runtime-refactor/eng/04a-应钉行为清单.md:40`（pin-31 行）「提及 vs 执行由**模型**在配工具那次调用产出；按结论放行/拒答的**机械分派**留在 `preconditions` 判定序第 1 位；出数只认现行口径（旧名归一在 `tool_matching`）」；③ `docs/runtime-refactor/walk/裁决表.md:22`（§12）「**不放门口**：**判断**（提及 vs 执行）由**模型**在**配工具那一次调用**产出；**分派**（按结论放行／拒答）留在 `preconditions` 判定序**第 1 位**（机械分派）」。
- **真源核对与偏离登记（如实报，不代裁）**：
  1. **票面指向不实一处**：票「接口缺口」① 称「规格**行为 11** 行要求本块产出「提及 vs 执行」结论」——实读不符：行为 11（`specs/tool_matching.md:110`）是「**解析拒文→结构化拒因的转换归本块**」（流水 30① 裁决）；「提及 vs 执行」的产出要求在「接口定义」节 `:73` ＋ 挂钩表 pin-31 行 `:159`。本批按**真实落点**补字段，行为 11 一字未动。**票面那处误指建议主窗随批收词**（改票归主窗）。
  2. **pin-14 的「时间窗结论」本批未落字段（口径观察，呈主窗确认载体）**：仓内现有承载面是 `specs/query.md` 的 `QueryOutcome` 联合态 `need_clarify(候选窗三选一)`（`:36`）＋同文件行为 4（`:47` 原文「缺参（模糊时间如"最近"）→need_clarify 三选一候选窗」），`QueryPlan`（`:29–:31` 十字段）随 `SubtaskMatch.plan` 进下游——**故按 L0 口径只补 `mention_mode` 一枚**，未新增时间窗字段。**若主窗判定仍需 `SubtaskMatch` 上的独立时间窗字段（或须在工具匹配侧产出该结论），属新裁**；本记录不代裁（RT-W4-04 票「施工前对账项」① 亦把「时间窗结论字段载体未定」列为待裁项）。
  3. **拒因枚举的取真源过程**：规格（`:63`／`:65`／错误契约 `:72`）只给五类**中文词**，**全仓无枚举成员名清单** → 成员名＝规格五类词原样照抄（**未发明英文名**）；逐字拒文取 **V1 码面字面**（`appv2/runtime/subtask.py:325-374`；recon `docs/runtime-refactor/recon/L1b-子任务后半.md:49-62` 逐条对应）。recon 记法与码面有两处**占位记法差异**（recon 把 `{match_id}` 写作 `{id}`、把 `{'/'.join(sorted(CHAIN_KINDS))}` 写作 `data/knowledge`）——已在规格 `:86` 注明「逐字以码面行为准，施工票照抄码面字面」。
  4. **一条未归类（留白，不发明第六类）**：V1 字面 `matches 支须为对象（{id/chain/tool/plan|retrieval_need}）`（码面 `appv2/runtime/subtask.py:332`；recon L51）＝**支形状失败**，五类成员无一逐字覆盖 → 规格 `:87` 登记为「未归类一条，呈主窗裁归」，本批不加第六类。
- **未随批改面（登记交主窗）**：① 规格「行为约定」5「枚举闭世界」行（`:104`）仍只列 `chain`／`direction`／`tool`，**未加 `mention_mode`**——加则连带须改其验收行 `:133`「【边界集】`chain`／`direction` 越界取值 → 判失败」（＝行为定义面改动，本批未授权）；② 验收测试表**未增 `mention_mode` 新行**（闭世界要求写在接口定义；pin-31 挂钩行 `:159` 已承载「待织网」）。两处补不补，提请主窗裁。
- **行号漂移（供票面回填）**：`specs/tool_matching.md` 原 `:1–:55` 不变；原 `:56–:66` **+1**；原 `:67–:74` **+2**；原 `:75` 起 **+15**——原行为 11 `:95`→`:110`；原验收表 `:107–:120`→`:122–:135`；原挂钩表 pin-31 行 `:144`→`:159`；文件 **146→161 行**。`specs/modules.md` 原 `:179` 起 **+5**——原 `## api` `:578`→`:583`；原 api 依赖行 `:598`→`:603`；原边界规则 api 行 `:622`→`:627`；文件 **635→640 行**。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（22 份规格）**；`uv run lint-imports --config tools/importlinter_v2.toml` → **Contracts: 18 kept, 0 broken**；`uv run lint-imports`（默认配置＝V1 面）→ **6 kept, 0 broken**。均 exit 0（改后实跑）。未 git commit。

---

## 2026-10-16 收尾一致批（流水 51）

- **依据**：主窗（2026-10-16）「已定稿规格／票面收尾一致修正批」。上一轮（流水 50，见上节）给 `specs/tool_matching.md` 补 `SubtaskMatch.mention_mode`＋`MatchReason` 拒因枚举后，**同一规格内五处未同步**，另有**票面误指一处**与**一条未归类拒因**待归。本批只做一致性收尾——**不动语义裁口、不发明措辞**；未 git commit（主窗统一提交）。
- **改动文件（3 个＋本记录）**：`specs/tool_matching.md`（161→166 行）、`specs/modules.md`（642→642 行，两处在位改写）、`tickets/v2-refactor/RT-W4-03-tool_matching.md`（103→105 行）、本记录。

### 逐处改动（行号指改后文件）

| # | 位置 | 改了什么 | 任务项 |
|---|---|---|---|
| 1 | `specs/tool_matching.md:106` | 行为 5「枚举闭世界」补 `mention_mode`（`executed`｜`mentioned_only`）成员＋注「**2026-10-16 补（流水 51）**」；并列明字段载体见「接口定义」节 | ① |
| 2 | `specs/tool_matching.md:138` | 「验收测试」表**表尾追加第 15 行**（`SubtaskMatch.mention_mode` 取值闭世界（`executed`／`mentioned_only`）越界即拒 ｜ `tests/domains/test_v2_tool_matching.py::mention_mode_closed_world`）；`:140` 表下加注「**增行＝流水 51 收尾一致**」 | ② |
| 3 | `specs/tool_matching.md:144` | 「依赖与风险」依赖行 `bookkeeping` 项补**写口面**：**照 `specs/preconditions.md:30` 句式**「落 step 记录/notice 经 bookkeeping 唯一写口，只引函数、不引其内部」＋注「2026-10-16 补（流水 51）」 | ③ |
| 4 | `specs/tool_matching.md:63／:65-66` | `ToolMatchRejection.reasons` 注释、`class MatchReason` 注释与 `kind: Literal[...]`：**五类→六类**，末位 `malformed_matches`，注「**成员名照码面，2026-10-16 归位（流水 51）**」；`:66` 括注由「与「错误契约」五类逐字同源」改「**前五类**…同源」（见「未随批改面」1） | ④ |
| 5 | `specs/tool_matching.md:76` | 「拒因枚举＝**六类**闭世界」；成员名取真源句同时补「第六类 `malformed_matches` 系原『未归类一条』经主窗裁归入而增」 | ④ |
| 6 | `specs/tool_matching.md:85` | 逐字拒文表**增末行**：`malformed_matches` ｜ `matches 支须为对象（{id/chain/tool/plan\|retrieval_need}）` ｜ recon L51；`appv2/runtime/subtask.py` L332（逐字照码面；表内 `\|` 系 markdown 转义） | ④ |
| 7 | `specs/tool_matching.md:87` | **新增「第六类归位注」**：＝**支形状失败**（`matches` 支不是对象）；含「**成员名照码面，2026-10-16 归位（流水 51）**」；明示**前五类成员名与逐字拒文一字未动** | ④ |
| 8 | `specs/tool_matching.md:88` | 「占位记法」条**补句**：第六类拒文里的 `{id/chain/tool/plan|retrieval_need}` **不是占位**——码面该行**无 `f` 前缀**（L332 为整串字面），不得当占位替换或改写 | ④ |
| 9 | `specs/tool_matching.md:89` | 原「**未归类一条（不发明第六类；呈主窗裁归）**」改「**未归类一条——已销项**」条：记主窗裁（kind 名照抄、拒文照码面逐字）、闭世界以上述**六类**为准、原「不新增成员／登记待主窗裁归」**就此销项** | ④ |
| 10 | `specs/modules.md:180／183` | `## tool_matching` 卡：`MatchReason` 行 `kind` 补 `\|malformed_matches`（五类→六类）；`:183` 卡级修正注**追加流水 51 段**（第六类归位＋成员名照码面＋逐字拒文锚 `appv2/runtime/subtask.py:332`） | ④连带（主窗清单未列，见「偏离登记」1） |
| 11 | 票面 `:20-21` | 「接口缺口」① 的误指改按**真实落点**引：规格「接口定义」节 `specs/tool_matching.md:73`（原文逐字引）＋「测试网钉」节所引挂钩表 **pin-31 行** `:164`（原文逐字引）；② 保留但如实记其字段面（拒因枚举） | ⑤ |
| 12 | 票面 `:21` | 加「**勘误与现状注 2026-10-16（流水 50／51）**」：行为 11（`specs/tool_matching.md:112`）实为「解析拒文→结构化拒因的转换归本块」，与原票面「行为 11 要求产出『提及 vs 执行』」**不符**；字段面现状＝`mention_mode` 已回写（①未清项只剩 **pin-14 时间窗结论字段**）、②已落（`:65-67` 六类） | ⑤（同批收词，见「偏离登记」2） |
| 13 | 票面 `:46／:48` | 「票面对象」表**补抄第 15 行**（逐字照 `specs/tool_matching.md:138`，带规格源行号）；表下加注「本批补抄…**票面对象 15 行 ＝ 小票制上限，仍 ≤ 15 ✓**」 | ⑤ |
| 14 | 票面（全表引用） | **规格源行与锚点行号回填**，逐处清单见下「行号回填清单」 | ⑥ |
| 15 | 票面 `:60` | 「测试网钉」第 3 条原「pin-31 的字段载体属**接口缺口**（`SubtaskMatch` 未列该结论字段）——L0 裁前不得自造字段名」改准：字段载体＝`SubtaskMatch.mention_mode`，**已随流水 50 回写**（`specs/modules.md:178-179`；`specs/tool_matching.md:56`／`:75`） | ⑤（同批收词，见「偏离登记」2） |
| 16 | 票面 `:18／:26／:70／:78／:97` | 行数自述与骨架同步：小票制自检「14 行→**15 行** ≤ 15 ✓」、票面对象标题「15 行」、行为 5 一句话补 `mention_mode`、结构锚「错误契约＝**六类**（五类＋`malformed_matches`）」、验收节「15 行逐行实现…」；结构锚与施工要点锚行号按回填更新 | ⑥ |

### 行号回填清单（票面逐处；任务 ⑥）

漂移成因＝①流水 50 批 +15（原 `≥:75` 段）；②本批在 `specs/tool_matching.md:85`／`:87` 各插 1 行，`≥:86` 段**再 +2**——故原 `≥:75` 段合计 **+17**。

| 票面位置 | 原引用 | 改后引用 | 依据 |
|---|---|---|---|
| `:28`（票面对象〔来源〕） | `:107–:120` | `:124–:137`（前 14 行）＋`:138`（第 15 行） | 验收表 14 行整体 +17 |
| `:32–:45`（逐行「规格行」列） | `:107`…`:120` | `:124`…`:137` | 同上，逐行 +17 |
| `:46`（新增第 15 行） | —（新） | `:138` | 本批增行位置 |
| `:54`（测试网钉〔来源〕） | `:144` | `:164` | 挂钩表 pin-31 行 +20（+15＋行内再变） |
| `:66–:76`（施工要点「锚」列） | `:85`…`:95` | `:102`…`:112` | 行为约定段 +17 |
| `:78`（结构锚） | `:41–73` | `:41–90` | 接口定义节末（含新增） |
| `:78`（结构锚） | `:75–81` | `:92–98` | 框架与依赖红线段 +17 |
| `:78`（结构锚） | `:97–101` | `:114–118` | 不降级与静默禁令段 +17 |
| `:78`（结构锚） | `:13–27`／`:29–39` | **不变** | 两段在漂移区（`:≥56`）之前——实读复核未漂移 |
| `:79`（织网义务〔来源〕eng/04） | `§三…:29–:37` | **不变** | 实读 `docs/runtime-refactor/eng/04-测试网设计.md:29–:37` 即 §三 B 表全行——未漂移 |
| `:5／:7／:16`（波次／前置／先读） | 只引节名（eng/03 §二／§五、`specs/modules.md` 卡、`specs/query.md`、`specs/tools.md`、`eng/04a`、`eng/04` §三／§五／§六） | **无需回填** | 无行号引用 |

### 真源核对（逐字亲读，如实报）

1. **第六类逐字拒文实读**：`appv2/runtime/subtask.py:332` ＝ `return "matches 支须为对象（{id/chain/tool/plan|retrieval_need}）"`——**无 `f` 前缀**，`{…}` 是字面的一部分（故 `:88` 补句为必要）；`docs/runtime-refactor/recon/L1b-子任务后半.md:51`（3a 支非 dict）逐条对应。
2. **「成员名照码面」无法在码面逐字核到（如实报）**：`grep -rn malformed_matches` **全仓零命中**；`appv2/runtime/subtask.py` 拒因面**只返回字面字符串、无任何 kind 标识符**（其余五类亦无英文名）。故第六类成员名系**主窗裁定的新标识**（前五类名＝规格中文词），本批**照抄**并连同注文（「成员名照码面，2026-10-16 归位（流水 51）」）**逐字落笔**，不代改、不代裁——**请主窗知悉该名在码面无对应物**。
3. **规格真源位**：`specs/tool_matching.md:90`「真源：`specs/modules.md` `## tool_matching` 卡（签名以卡为准）」——故卡面与规格接口节必须同批（见「偏离登记」1）。

### 偏离登记（超出主窗清单的动作，逐条交代）

1. **`specs/modules.md` 卡面同批改（清单未列，本批执行）**：流水 50 卡注自定纪律「**卡与规格接口节同批改，不许脱节**」，且规格明写「**签名以卡为准**」——卡面 `kind` 停在五类则**真源自相矛盾**（消费方按卡施工会漏第六类）。故 `:180／:183` 同批改，并把「本批同批」写进卡注。
2. **票面「接口缺口」现状注＋「测试网钉」第 3 条改准（任务⑤只授权「改票面表述」）**：原票面两处仍称「`SubtaskMatch` 未列该结论字段／拒因枚举字段面未定义」，而流水 50 已回写卡与规格——**不改则票内自相矛盾**，且会令施工子代理按**不存在的缺口停报 L0**。故按「票面表述勘误」同批收词，并把**未清项（pin-14 时间窗结论字段）**显式留下，不代裁。
3. **未发明**：`:72`「错误契约」五类中文词面**未动**（主窗裁只给 kind 名＋逐字拒文，未给第六类中文词面）；`:138` 行内判据、`:89` 销项措辞均**照主窗裁文逐字**，无自撰。

### 未随批改面（登记交主窗）

1. **「错误契约」条（`specs/tool_matching.md:72`）仍为五类中文词面**，未含第六类——本批不加（加＝发明中文词面）；现由 `:65-66` 括注「前五类…同源」＋`:89` 销项条承载。若主窗要求 `:72` 同步，请给逐字词面。
2. **挂钩表（`specs/tool_matching.md:152–166`，11 行）未为新验收行（`:138`）加挂钩行**——任务②只授权「验收测试」表增行；是否补挂（例：「`mention_mode` 闭世界断言 → 测试行」）请主窗裁。
3. **卡 `:186` 依赖行仍只记「模型调用发起面」**（未记写口面）——任务③只授权改规格「依赖与风险」依赖行；两处是否须一致，请主窗裁。
4. **他处引用本规格行号的历史评审件**（如 `docs/runtime-refactor/spec-review/preconditions-评审.md` 引 `tool_matching.md:68/84/95`、`answering-评审.md` 引 `:77/80` 与 `:74-80`）仍指流水 50 **前**编号——属**历史记录件**，按同类前例**本批不回改**；如需「行号已漂移」全局勘误，属另批。

### 验证

- `python3 tools/check_specs.py` → **PASS（0 警告）**，exit 0；
- `python3 tools/ticket_shape_check.py tickets/v2-refactor/RT-W4-03-tool_matching.md` → **GREEN**，exit 0；
- `python3 tools/ref_resolvable.py check` → **绿（22 份规格的真源引用与边界规则编号均可解析）**，exit 0；
- `uv run lint-imports --config tools/importlinter_v2.toml` → **Contracts: 18 kept, 0 broken**（本批零代码改动，随批复核未红）；
- 均于改后实跑；**未 git commit**（主窗统一提交）。

---

## 2026-10-16 卡面勘误（阶段 4 拆票·收词批）

- **审计项（`specs/modules.md` `## tool_matching` 卡「### 依赖」行）**：该「- 模块」行原直列 `gateway_adapter`，与同规格两处明写相抵——「触及的模块」表 `specs/tool_matching.md:37` 原文「gateway_adapter | 新增 | 模型出口（唯一出口仍归它）；**本块不直引**——经 bookkeeping.call_model 发起」＋「框架与依赖红线」条 `specs/tool_matching.md:95` 原文「本块不直引 `gateway_adapter`（import 落点＝`appv2.runtimev2.bookkeeping` **包根**——R2 禁深层子模块）」。**本批按主窗票面勘误逐字执行：该模块名已从「- 模块」行删除**，并在同节加注「**2026-10-16 勘误：不直引 `gateway_adapter`——经 `bookkeeping` 桥（流水 51）**」（佐证：`docs/runtime-refactor/eng/03-施工顺序与切换计划.md:17` 依赖图 `tool_matching → state` 亦不列该边）。只删**直引名**，不动签名与语义——唯一模型出口仍归 `gateway_adapter`，本块经 `bookkeeping.call_model` 桥间接到达；`check_specs` 依赖面无环、零 FAIL。
  - **前次执行留痕（勘误）**：本批此前一次执行把该行改注为「不直引——经 bookkeeping 桥」而**保留**模块名（理由＝`gateway_adapter` 仍是本块耦合面）——与票面「卡行删 `gateway_adapter`」不符，今按票面逐字改齐（删名＋加注）。
  - **同族留痕（不在本批范围，交主窗裁）**：`## understanding`／`## clarification`／`## answering` 三张卡的「- 模块」行仍直列 `gateway_adapter`（三块规格同写「本块不直引」）；是否同款勘误请主窗裁。
  - **仍开项（承上节「未随批改面」3）**：卡面「- 模块」行只记「模型调用发起面」，未记 `bookkeeping` **写口面**（规格「依赖与风险」依赖行 `specs/tool_matching.md:144` 已记）——两处是否须一致请主窗裁。
- **验证**：`python3 tools/check_specs.py` → **PASS（0 警告）**，exit 0；`python3 tools/ref_resolvable.py check` → **绿（22 份规格）**，exit 0；`python3 tools/ticket_shape_check.py tickets/v2-refactor/*.md` → **GREEN**，exit 0；`uv run lint-imports --config tools/importlinter_v2.toml` → **Contracts: 18 kept, 0 broken**。均改后实跑；**未 git commit**（主窗统一提交）。

---

## 2026-10-16 卡依赖行收齐勘误（`understanding`／`clarification`／`answering` 三卡 ＋ `eng/03` 依赖图）

- **依据**：Owner 批「卡依赖行收齐勘误」（照上一节 `tool_matching` 卡先例）；本批即处置上节 `:166`「同族留痕（不在本批范围，交主窗裁）」开项。三块规格同写「本块不直引 `gateway_adapter`」——`specs/understanding.md:63`／`specs/clarification.md:73`／`specs/answering.md:65`（各规格「框架与依赖红线」条，同款句式）；touched-module 表同向：`specs/understanding.md:35-36`／`specs/clarification.md:35-36`／`specs/answering.md:30-31`「本块不直引——经 bookkeeping.call_model 发起」。
- **改动性质**：只删**读法上的直引名**（「- 模块」行）＋加同款勘误注；只删边、不动签名、不动依赖实质——唯一模型出口仍归 `gateway_adapter`，三块经 `bookkeeping.call_model` 桥间接到达。

### 逐处改动（行号指改后文件）

| # | 位置 | 改了什么 |
|---|---|---|
| 1 | `specs/modules.md:141` | `## understanding` 卡「- 模块」行删去「、`gateway_adapter`」；`:142` 加注「**2026-10-16 勘误：不直引 `gateway_adapter`——经 `bookkeeping` 桥（流水 51 收齐批，Owner 批）**」 |
| 2 | `specs/modules.md:161` | `## clarification` 卡「- 模块」行同款删名；`:162` 加同款注 |
| 3 | `specs/modules.md:250` | `## answering` 卡「- 模块」行同款删名；`:251` 加同款注 |
| 4 | `docs/runtime-refactor/eng/03-施工顺序与切换计划.md:13-15` | §一依赖图 `answering`／`understanding`／`clarification` 三行删去「` + gateway_adapter`」边（改后：`answering → context + prompts + state`／`understanding → gate + prompts + parsing + state`／`clarification → prompts + parsing + state`）；`:31` 加注「**注（2026-10-16 收齐批）：不直引（规格红线），经 `bookkeeping` 桥**」并点名三行 |

### 未随批改面（登记交主窗）

1. `specs/modules.md:143`（`## understanding` 卡「- 外部」行「（无——模型调用经 `gateway_adapter`）」）**未动**——该括注是**解释性说明**（不在「- 模块」依赖列上），且与勘误注不抵；是否同删请主窗裁。
2. 上节 `:166` 原开项「是否同款勘误请主窗裁」**就此销项**（本批即该勘误）；该行为当时留痕，按历史记录体例**不回改**。
3. 三卡勘误集中记于本文件末节（任务指定），未另建三份回工补写文件。

### 验证（改后实跑）

- `python3 tools/check_specs.py` → **PASS（0 警告）**，exit 0；
- `.venv/bin/lint-imports --config tools/importlinter_v2.toml` → **Contracts: 18 kept, 0 broken**，exit 0；
- `.venv/bin/lint-imports`（默认配置＝V1 面）→ **Contracts: 6 kept, 0 broken**，exit 0；
- 本轮**零代码改动**（只改规格卡与设计文档），两闸随批复核未红；**未 git commit**（主窗统一提交）。

---

## 2026-10-16 P-05 单点归位（流水 55）

- **2026-10-16 P-05 单点归位（流水 55）**：`mention_mode` 物理落 `parsing.models.SubtaskMatch`（P-05 载荷类形状单点——`specs/parsing.md` 行为 12），本块 `models.py` 类体删除、改**导入消费**（`from appv2.runtimev2.parsing import SubtaskMatch`，包根 21 成员公开面不动）；随本次归位，`specs/tool_matching.md` 接口定义节的消费面类体差异（`caliber_key: str | None`／`plan: QueryPlan | None`／`retrieval_need: RetrievalNeed | None`／类内 `__post_init__` 把守）**收敛为 `parsing` 形状**——`mention_mode` 的取值闭世界（缺／越界即拒）留在消费方对账面 `matching._violation_of`，`retrieval_need` 以映射承载、`caliber_key` 取空串形；`specs/tool_matching.md` 类体回改引用句＝主窗（`specs/parsing.md` 风险 7③ 登记件）。

---

## 2026-10-16 pin-31 断供修复（`mention_mode` 端到端投影）

- **审计（本批定性）**：pin-31 的「提及 vs 执行」结论在**模型发射 → 消费面**之间**断供两处**——①`parse_tool_match` 装载 `SubtaskMatch` 时**不读**发射条目的 `mention_mode` 键（恒空串）；②同块 `SubtaskMatch.as_payload` 投影**不带**该键（即真值也进不了 `state.tool_matches`）。①②叠加 ⇒ `specs/preconditions.md` 判定序**位 1 机械分派**（`preconditions/core.py:186`）在**实链路**上零可达，此前只有测试内手工拼键在场。
- **本批改动（3 个源码／测试文件＋本记录；未 git commit）**：
  1. `appv2/runtimev2/parsing/parsers.py:262-271`（`parse_tool_match` 装载支）——发射条目带 `mention_mode` 键 → **原样载入**（值照抄、不 strip、不判语义；parsing 纯解析，闭世界把守归消费面 fail-closed）；**缺键＝空串缺省**；**带键而值非字符串形 → 拒**（fail-fast 于该支）；`parsers.py:281` 装载进 `SubtaskMatch`。
  2. `appv2/runtimev2/parsing/models.py:131-132`（`SubtaskMatch.as_payload`）——`mention_mode` 真值才出键（同 `caliber_key` 面）；类／模块注记同步（`models.py:17-19`／`:110-111`）。
  3. `tests/domains/test_v2_parsing.py:509`／`:545`——带键原样装载＋投影、非字符串拒两用例；`tests/domains/test_v2_preconditions.py:754`——端到端用例（发射文本 → `parse_tool_match` → `as_payload` → `state.tool_matches` → `gate_all` 位 1 分派，**零手工拼键**，断言只走既有公开出口）。
- **拒因措辞取证（逐字）**：`matches {match_id} mention_mode 越界（executed/mentioned_only）：{值!r}`——照挂 `specs/tool_matching.md:84` 拒因六类表**「枚举越界」族**句式（同族既有形＝`matches {match_id} chain 越界（data/knowledge）：{chain!r}`），且与消费面对账面 `appv2/runtimev2/tool_matching/matching.py:217` **逐字同款**；**未新造措辞**。
- **偏离登记（逐条交主窗核，本记录不代裁）**：
  1. **改 `models.py`（`as_payload`）超出任务书逐列的改动文件面**（任务书只列 `parsers.py`）：理由＝验收要「经 `parse_tool_match` 真链路 → **state 投影** → `preconditions` 分派」的端到端用例，而投影面不带键则 `state.tool_matches` 仍拿不到结论、端到端不可达（任务书背景原文「不投影该键」即指该投影面）——已实跑反空转取证（见下）。
  2. **投影口径选「真值才出键」**（空串键不出现——同 `caliber_key` 面；消费面 `payload.get(…) or ""` 空串读法等价），**未采「恒带键」**：理由＝本块投影规则原文「空值键不出现」＋既有断言面可**一字不改**（本批只增用例、零改形）。
  3. **拒因措辞不含「只许」二字**：任务书示例作「只许 executed/mentioned_only」，而其指令同时要求「先查六类拒因表有无同族可挂，有则照挂不新造」——同族既有形（规格 `:84`／对账面 `matching.py:217`）均**无「只许」**，故照挂同款。
  4. **`{"mention_mode": null}` 判拒**（带键即判形，值非字符串形）——**未按「视同缺键」**处理；`mention_mode` 键在场即受形判，取字面读法（更 fail-closed）。如需改判请裁。
  5. **字符串越界值（如 `maybe`）本层照抄放行**、归消费面拒——parsing 判形不判语义（与 owner 裁「`mention_mode` 物理落 `parsing`＝`str=""` 纯装载」一致）。
- **规格收尾一致（登记，不做——未授权动规格）**：`specs/parsing.md` 行为 11（`:112`）的 `SubtaskMatch` 字段表与投影规则**未列** `mention_mode`（同文接口节 `:71` 已列该字段并注 P-05 单点归位）——**规格内自相矛盾**，本批不改规格，请主窗随批收词；同理，本批新增的 3 条用例**不对应任何规格「验收测试」行**，是否补行（含 `tool_matching` 对账面族）请主窗裁。
- **验证（改后实跑）**：①`pytest tests/domains/test_v2_parsing.py tests/domains/test_v2_preconditions.py tests/domains/test_v2_tool_matching.py -q` → **74 passed**（31／22／21；改前 29／21／21，增 2＋1）；②全量 `pytest tests -q` → **2148 passed, 108 skipped**；③`mypy app appv2` → **Success: no issues found in 237 source files**；④`ruff check`（改动面）→ **All checks passed**；⑤`lint-imports --config tools/importlinter_v2.toml` → **Contracts: 18 kept, 0 broken**；默认配置 → **6 kept, 0 broken**；⑥反空转取证（临时脚本、不入仓）：同一发射文本经 `as_payload` 投影 → 位 1 **allow**（仅提及）；手工去键（＝修复前形）→ **refuse**——两处改动皆承重。未 git commit（主窗统一提交）。

---

## W4 对账批（2026-10-16）

- **定性**：W4 十二票施工期登记件的收口批——7 项**纯文本**改动（规格／卡陈旧回改＋依赖面回填），零源码改动。改动**全部收进既有行内**（不增行、不删行；`tool_matching.md` 接口节的三行声明式注记折进 `class SubtaskMatch:` 行）——逐文件行数与 `HEAD` 相等（tool_matching 166／modules 648／preconditions 146／answering 153／parsing 198／verification 143／agent-loop 241／eng/04 69），故规格内既有 `:NN` 互指（如行为 11 引接口节 `:71`）与代码注释里的规格行锚（如 `appv2/runtimev2/preconditions/constants.py` 记 `specs/tool_matching.md:56`／`:75`）**全部依旧有效——本批零行漂移**。
- **逐项（行号＝改后；各文件行数与 HEAD 相等）**：
  1. `specs/tool_matching.md:49`——接口节 `SubtaskMatch` 旧类体回改：类行加声明「**形状单点在 `parsing.models`（P-05，2026-10-16 归位；`specs/parsing.md` 行为 12）；本册只定义语义面**——字段照 parsing 类体（含 `mention_mode`——取值把守归本册消费面对账），`plan`／`retrieval_need`＝映射形（非 `QueryPlan`／`RetrievalNeed` 对象）、`caliber_key`＝空串缺省」；`:53-56` 字段行改准现行实现形（`plan: dict | None`／`retrieval_need: dict | None`／`caliber_key: str`／`mention_mode: str`＝空串即未装载）。`:120`（不降级与静默禁令节）——`caliber_key` 归一的机读信号句加旁注「成功路径零补记步，信号现由返回值 `ToolPlan.matches[].caliber_key` 承载」。
  2. `specs/parsing.md:112`（行为 11 字段表）——`SubtaskMatch{…}` 补 `mention_mode=""`、投影规则补「**`mention_mode` 真值才出键**（空串＝未装载、键不出现——同 `caliber_key` 面）」，并注「2026-10-16 增（流水 50 裁／P-05 单点归位）＝装载自发射／真值才投影／把守归消费面；同文接口节 `:71` 已列，**本条消自指不一致**」——**兑现**上文「规格收尾一致（登记，不做）」与 `spec-review/parsing-回工补写.md` 的同类登记。
  3. **verification 依赖面回填 `tools`**（只引 `entity_anchor_tokens` 公开面——行为 5 题眼锚，流水 56-W4 登记）：`specs/modules.md:272`（`## verification` 卡依赖行）＋`specs/verification.md:116`（「依赖与风险」依赖行）。**注**：卡依赖行内用**裸词** `entity_anchor_tokens`（不加反引号）——`tools/check_specs.py` 的卡依赖解析＝`TICK.findall` 整行反引号 token 全当模块名，加引号会造幻影模块 `entity_anchor_tokens`（幻觉依赖，卡面 FAIL）；同册既有 `verdict/notice`（同卡）／`NOTICE_TYPES`（`## bookkeeping` 卡）亦同款裸词先例。
  4. **preconditions 注入面回填**：`specs/modules.md:204`（`## preconditions` 卡 `gate_all` 签名补 `watermark=None, data_wells=None`）＋`:207`（卡级微注追加「卡级补注（W4 对账批，2026-10-16）」：位 7 新鲜度窗水位读数／位 6 数据链井闭世界——位 6／7 输入路径、producer＝orchestration、未注入或空＝对应闸静默；实现已在位 `appv2/runtimev2/preconditions/core.py:115-121`）＋`specs/preconditions.md:35`（旧签名行收齐三注入参，尾注「签名以卡为准」）——**兑现** `spec-review/preconditions-回工补写.md` 流水 56 节「未随批改面」②。
  5. **陈旧括注清理**：`specs/agent-loop.md:180`「旧四态断言 `test_precondition_four_states_reachable` 待退役、三态版待织」→「已退役、三态版**已织（三态版，2026-10-16）**」；`docs/runtime-refactor/eng/04-测试网设计.md:31`（§三 B2b 行）「悬空虚引」→「**已织（三态版，2026-10-16）**——W4-04 收票，悬空虚引已销」（实测锚：`tests/domains/test_v2_four_phase.py:283::test_precondition_three_states_reachable`）。
  6. `specs/agent-loop.md:194`（验收表·表内第 18 数据行＝`test_manifest_present_each_call` 行）——旁注「**W4 登记（2026-10-16）**：材料面 Manifest 现挂答案面步（`call_model` 无 manifest 注入面）；若裁定改由 `call_model` 承接 → 回 W3 `bookkeeping` 或设计仓」（兑现流水 56③ 登记；票面所述「行 18」＝表内行序，非文件行号）。
  7. `specs/answering.md:130`（「依赖与风险」节，风险 4 同行尾接登记句——行内追加，不新起列表项）——「**登记（W4 对账批，2026-10-16）——V2 发射动作全量枚举无单点真源**（`parsing.CLARIFY_ACTIONS` 与本块 `EMISSION_ACTIONS` **非同族**）：**扩域＝规格变更**，本批只登记、不扩」（兑现流水 56③ 登记；同判在码面注 `appv2/runtimev2/answering/constants.py:146` 附近「两处非同族第二定义」）。
- **未随批改面（登记交主窗）**：
  1. `specs/parsing.md:113`（行为 12）＋风险 7③ 仍写「两份消费方（`clarification.md`／`tool_matching.md`）的同类视图与本规格差异（`SubtaskMatch caliber_key: str|None`・`plan: QueryPlan|None`）」——**tool_matching 侧已随本批第 1 项收敛**，该句对 tool_matching 已不实（`clarification` 侧仍待阶段 7 回改）；改该句＝行为相邻文本，本批未授权，请主窗裁。
  2. `specs/verification.md:116` 依赖行仍不列 `bookkeeping`（卡面与「触及的模块」表已列——流水 50 已登记；本批只授权补 `tools`）；同规格「触及的模块」表（`:22-27`）亦无 `tools` 行（本批只授权依赖行——卡依赖行与触及表两侧未同批收齐）。
  3. `specs/tool_matching.md:58` 起 `RetrievalNeed` 类体保留（类名作族名单保留、形状载体归 parsing——与实现 `appv2/runtimev2/tool_matching/models.py` 注记一致），未随批删。
- **验证（改后实跑）**：①`python3 tools/check_specs.py` → **PASS（0 警告）**；②`python3 tools/ref_resolvable.py check` → **绿（22 份规格；`report` 盘点 0 条）**；③`.venv/bin/python -m pytest -q` → **2148 passed, 108 skipped**（与基线同值——纯文本改动零影响；三跑：折行前／折行后／末稿）。均 exit 0。未 git commit（主窗统一提交）。
