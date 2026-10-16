- 日期：2026-10-15 ｜ 状态：**回工补写记录（独立复审打回件）**
- 本次只改 `specs/clarification.md`（已定稿规格的增量修订）＋ 本记录文件，其它任何文件未动（另一窗口在改 `agent-loop.md`，未触碰）。未 git commit（主窗统一提交）。
- 行号均指**改后**的 `specs/clarification.md`（149 行）。复审提示词所引行号（挂钩表「约 :122-134」、R7 重复「:62 与 :65」）与现行文件有位移（复审基于较早已定稿版），本次按**语义定位**落点，实际行号逐条列下。

## 复审发现 → 修改对照

### 必修 1【P0·FAIL】pin-05 落点（零实质观察不得直答收口）——已补

- **真源核对**：pin-05 原文「零实质观察（非 notice）时 decision 不得判「材料足够」直答收口」（`docs/runtime-refactor/eng/04a-应钉行为清单.md:14`，P0，钉形式＝单元）；证据 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-01（`:25`「finalize 合法 ⇔ 窗内已有实质观察：非 notice 观察（faq 命中卡/台账条目卡/检索片段）才算数，空手探查不算——V2-53 的 discover_used≥1 通行证废除」）＋关键拍板原文（`:38`）。**行为落点＝clarification**：finalize 合法性闸＝数窗内非 notice 观察的纯结构判定，属本块闭世界对账职责。
- **三处同补**：
  1. **拒因枚举**（`specs/clarification.md:56`）：`ClarifyRejection.reasons` 注释枚举追加拒因形「**零实质观察禁定稿**」。
  2. **行为约定**（`specs/clarification.md:93` 新增行为 17，assert 形）：`finalize` 前置＝窗内非 notice 实质观察数 ≥1，否则拒因「零实质观察禁定稿」回喂、不得直答收口；程序侧只数观察数（纯结构判定，计数属 `no_lexicon_or_regex_in_clarification` 豁免面）。配套在接口定义新增「**`finalize` 合法性闸**」条款（`specs/clarification.md:65`）承载触发条件与拒因回路（走 `ClarifyRejection`→`orchestration` 回喂重决策）。
  3. **验收测试表**（`specs/clarification.md:109` 新增行，绑测试标识 `tests/domains/test_v2_clarification.py::finalize_requires_substantive_observation`，标识格式照既有行 `tests/domains/test_v2_clarification.py::…` 体例）。
- **做没做什么的边界说明**：接口定义「错误契约」的 schema 违例枚举（`specs/clarification.md:64`）**未动**——finalize 闸是**前置合规**不是 schema 违例（P4b A-P4b-19「程序只干两件事：装配上下文／检查发射物的格式与前置合规」两面之别），故触发条件以独立条款承载；拒因形仍走同一 `ClarifyRejection` 通道，机读信号面（step payload 拒因字段）由既有「不降级与静默禁令」节覆盖，未重复加行。
- **挂钩登记**：见必修 2。

### 必修 2【P1】挂钩表补登记（pin-05／pin-15／pin-07）——已补

- `specs/clarification.md:146-148` 新增三行（照 `agent-loop.md:227-230`／`preconditions.md:137` 既有钉登记体例：钉行独立成行、「待织网（阶段 5）」，插在末行人审行之前）：
  - **pin-05**（P0，:146）：finalize 合法性闸行，挂钩列附测试 `::finalize_requires_substantive_observation`。
  - **pin-15**（P1，:147）：连续澄清反问到顶截断带料＋挂起不计轮／恢复重置行。**上限值只写真源口径**：「上限值真源＝`walk/裁决表.md` §06-A 统一预算表——连续澄清≤6」（§06-A 在 `裁决表.md:92`），**未写字面 3**（复审②已纠偏：3 为 c46de21 废值，合同值 6——`eng/04a:5,24`）。
  - **pin-07**（P1，:148）：定稿打回理由三段带路（前置判定指路→空手清单→兜底 `doc_retrieve` 指引）行。
- **未做**：pin-07 只按复审口径做挂钩登记，**未**在本规格行为约定／验收表为其加行为行（复审未要求；见「遗留」第 1 条）。

### 必修 3【P1】行为 2/16 执行者归位——已补

- **行为 2**（`specs/clarification.md:78`）：标题标注「**属模型侧策略判断，程序只分派模型结论，不入程序验收面**」，正文写明「能否从问句确定／是否需反问」的判断在模型侧产出、程序只按结论分派（含引擎缺参反问兜底）；真源补 `walk/裁决表.md` 项目级裁决 #13。体例照行为 5（:81）「属模型侧策略，不入程序验收面」同款。
- **行为 16 后半**（`specs/clarification.md:92`）：「台账命中且时间窗已定 → 禁再 `discover`」的括注补同款标注（机械半句程序可验收；「时间窗已定」的判断属模型侧策略判断，程序只分派模型结论）。
- **验收行断言语义**：`no_ask_when_time_resolvable`（:110）与 `no_rediscover_when_window_set`（:122）均写明「**断的是模型结论的分派形**」——程序只验收分派形，不验收判断本身。
- **真源写法核对**：复审提示词给的真源「`walk/裁决表.md` §13＃13」按字面找不到（§13＝「批量执行·查询执行」，无 #13 条）；实际落在**项目级裁决表 #13**（`walk/裁决表.md:23`「『闸 1b 模糊时间词门』定性——交模型（不豁免）：判断在模型侧产出（时间窗能否确定／是否需反问），程序只按结论分派（含引擎缺参反问兜底）；删『确定性词面门』说法」）。规格与回执均按「**项目级裁决 #13**」落笔，语义与复审意图一致。

### 必修 4【低】框架红线 R7 重复引用合并——已补

- 原「模型调用唯一出口」（复审稿 :62）与「禁手写替代」（复审稿 :65）两条各自引 R7 → **合并为一条**（`specs/clarification.md:72`），保留两边较完整的写法：唯一出口定性＋禁手写替代两条禁令（不得自建模型客户端／不得绕过直连上游）＋R7 契约＋「B6 只管 litellm 出 `infra`，不含绕过直引面」边界澄清＋「无旁路」行为断言验收写法。红线节 4 条 → 3 条，R5b 条（:73）内容未动。

## 验证

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：13 份规格的真源引用与边界规则编号均可解析。
```

- 两闸均 exit 0。新增真源引用（`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`、`walk/裁决表.md` §06-A／项目级裁决 #13）均实读核对存在；`§06-A` 的节号机检（`## 06 …` 标题在 `裁决表.md`）经闸实跑确认可解析。
- 改动规模：144 → 149 行（＋5：接口 +1、行为 +1、验收 +1、挂钩表 +3、红线 −1；其余为原行内改写）。

## 遗留（只记录、不处理）

1. **pin-07 无行为正文行**：三段带路只在挂钩表登记（P1）；其行为约定／验收行未加——复审只要求登记。织网阶段落钉前需定行为行落点（语义上属 finalize 拒因内容，落本规格合理，但归属裁决待主窗）。
2. **`::finalize_requires_substantive_observation` 未实现**：阶段 5 承诺，与全表其他「待实现」行同态；spec 状态＝已定稿，闸不要求测试在场。
3. **pin-15 的挂起不计轮面**在挂钩表走 pin-15 单行承载，既有「挂起不计轮／恢复重置轮预算」行（:145）未重复挂钉——一钉一行登记，避免同钉散挂；复审若要求两行都挂可再补。
4. **复审稿行号位移**：复审提示词的 :62/:65/:122-134 与现行文件行号对不上（基于较早版本），本回执已按语义定位并给出实际行号；若复审需按行号复验，请以本记录行号为准。

---

## 补充任务（主窗核定：pin-07 归本块）——2026-10-15

- **核定**：eng/04a pin-07（P1，「定稿打回理由必须三段带路：前置判定指路→空手清单→兜底 doc_retrieve 指引」）**归 clarification 块**（finalize 拒因内容，与 pin-05 同块）。本规格由「仅挂钩登记」升级为三处补齐：
  1. **行为约定**（`specs/clarification.md:94` 新增行为 18，assert 形）：`finalize` 被拒（打回）时拒因载荷必带**三段拼装文本**（机器已知事实说全、零模型调用）——①有绑定拒／台账外形的前置判定→「该指标材料走报告检索：分解时 chain=knowledge、tool=doc_retrieve」；②已空手探查清单→「已空手探查：{tools}——禁再试同名同参」；③兜底句恒在「先 discover 取得条目（精确名单词），或 decompose 分解走 doc_retrieve 检索执行。」；段缺则跳、「；」连接成单段文本。真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-03（:27）；三段措辞逐字引真源，未自造。
  2. **验收测试表**（`specs/clarification.md:111` 新增行，紧随 finalize 合法性闸行 :110）：绑 `tests/domains/test_v2_clarification.py::finalize_rejection_three_segment_guidance`（标识格式照既有行体例）。
  3. **挂钩表**（`specs/clarification.md:150`）：pin-07 行由「仅登记」改为「钉 **`pin-07`**（P1；**落点＝行为 18**，测试 `::finalize_rejection_three_segment_guidance`）｜待织网（阶段 5）」。
  4. 来源行（`specs/clarification.md:4`）补「＋pin-07 打回三段带路」。
- **遗留第 1 条消解**：pin-07 不再是「无行为正文行」——行为行／验收行／挂钩落点均已落本规格。
- **行号位移**：本轮净增 2 行（行为 18＋验收行），规格 149→**151** 行；上节所记行号中，验收 finalize 闸行 ：109→:110、挂钩 pin-05／pin-15／pin-07 :146/:147/:148→:147/:148/:150，其余不变。
- **验证（改后复跑）**：

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：14 份规格的真源引用与边界规则编号均可解析。
```

（均 exit 0；未 commit。注：闸计数「14 份规格」含并行窗口新增的规格文件，非本轮所动。）


---

## V1 发起面回改（主窗裁 doctrine）——2026-10-15

- **依据**：复审⑦处置（`docs/runtime-refactor/00-决议与方法.md` 流水 27 第①裁）——相位调模型一律经 `bookkeeping.call_model`（其内部唯一出口 `appv2.runtimev2.gateway_adapter`）。本次只改 `specs/clarification.md`（151→152 行）＋本记录，其它文件未动；未 git commit（主窗统一提交）。
- **修改点**（行号指改后文件）：
  1. 「触及的模块」依赖表（:35-36）：新增 `bookkeeping` 行（改动类型＝**新增依赖**；说明＝「模型调用发起面：经 bookkeeping.call_model（单点发起），本块不直引 gateway_adapter」）；同表 `gateway_adapter` 行说明由「模型调用唯一出口；本 spec 只消费」改为「模型出口（唯一出口仍归它）；本块不直引——经 bookkeeping.call_model 发起」。
  2. 「框架与依赖红线」（:73）：「模型调用唯一出口＝gateway_adapter，禁手写替代」改为「**模型调用发起面＝`bookkeeping.call_model`（单点发起），禁手写替代；其内部唯一出口＝`gateway_adapter`**」，补「import 落点＝`appv2.runtimev2.bookkeeping` 包根——R2 禁深层子模块」；R7 括注改准为「禁直引 `appv2.infra.llm_client`——模型出口仍唯一归 `gateway_adapter`」＋「发起面收敛为规格层 doctrine，不设闸——主窗 2026-10-15 裁」；「无旁路」断言对象同步改为发起点只出现在 `bookkeeping.call_model`。
  3. 「依赖与风险」依赖行（:131）：补 `bookkeeping`（模型调用发起面——`call_model` 单点发起）；`gateway_adapter` 括注改为「经 `call_model` 的内部唯一出口，本块不直引」。
  4. 「与闸的挂钩表」（:144）：「模型调用只经 `gateway_adapter`」行改为「模型调用经 `bookkeeping.call_model` 发起（单点发起；其内部唯一出口 `gateway_adapter`）」；挂钩列注「出口面 R7；发起面为规格层 doctrine，不设闸」；现状列不变。
- **不加闸（裁定照录）**：importlinter 边界闸**不随本批加**——R7「只经出口」＋R8 语义不变，doctrine 是规格层不是闸层（主窗 2026-10-15 裁）。
- **契约字面核对（未改 toml）**：逐条实读 `tools/importlinter_v2.toml`——R7（forbidden＝`appv2.infra.llm_client`；source 含 `appv2.runtimev2.bookkeeping`）与 R2（业务相位 forbidden 含 `appv2.runtimev2.bookkeeping.*` 深层子模块、不含包根）均与新 doctrine **无字面冲突**。实现期注意：相位 import 只许 `appv2.runtimev2.bookkeeping` 包根（R2 面）。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（20 份规格）**。均 exit 0（批次一改后实跑）。

---

## 流水 31 裁决落笔（裁决一＝拒因转换点在消费方）——2026-10-15

- **依据**：主窗流水 31①（2026-10-15）——解析拒文（parsing 产出的 `str` 拒文）→ `ClarifyRejection` 的结构化转换归本块（消费方）：转换是机械适配（`str` 逐字进 `reason` 字段＋映射拒因枚举），零语义判断；parsing 不感知本块类型（R3）。销 `parsing-评审.md` P-09（原判「两头都不认」）；`specs/parsing.md` 风险 5 同批改「已裁：转换在消费方」。
- **修改点**（只改 `specs/clarification.md`，152→154 行）：
  1. 行为约定新增**行为 19**「解析拒文→结构化拒因的转换归本块（消费方）」（:96）——机械适配（str 逐字进 `reason` 字段＋映射拒因枚举）、零语义判断、parsing 不感知本块类型（R3）。
  2. 验收测试表新增一行（:127，【边界集】前）：`tests/domains/test_v2_clarification.py::parse_rejection_str_to_clarify_rejection_consumer_side`——测试标识待织网（阶段 5），同表口径。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（21 份规格）**；`uv run lint-imports --config tools/importlinter_v2.toml` → **Contracts: 18 kept, 0 broken**。均 exit 0（改后实跑）。未 git commit（主窗统一提交）。

---

## 2026-10-16 逐字闸改槽位对账（流水 64）

- **依据（真机证据）**：合同「填写样例」教拼装短形 `产量完成率｜未绑定｜2026-09-16~2026-10-16`（`appv2/runtimev2/prompts/decision_round.py` 的 `render_decompose_example`），模型照做后被 `_verbatim_note`（判据 `note_text in injection_block`）以「非逐字」驳回——台账真实行是长句形（`指标｜★产量完成率：Σ实际产油 ÷ Σ计划配产 × 100%｜粒度 …（绑定态：unbound）`），样例形**永远不是块内子串** → **闸设计不可通过**（真机 run-0d2e0274／run-1f5792d8 各烧 2–3 轮；日志 `logs/llm_calls/20261016.jsonl` 实测该驳回文本 32 处）。
- **裁法（Owner 已裁，流水 64）**：判据由「注入块内逐字子串」改**三段槽位对账**（形 `槽位｜绑定态｜窗`，分隔符全角「｜」）：①段一**逐字** ∈ 台账名录（exact membership，无语义匹配）；②段二 ∈ 闭世界 `{"已绑定", "未绑定"}`；③段三＝锚定窗形（`ISO~ISO`）／「窗未定」／双 null 发射形。三段位次固定，段缺／段数非三＝拒；任一不过＝拒并指明**哪一段／哪个值／为什么**（新拒因逐字稿照裁）。
- **实现落点**（行号为改后）：
  1. `appv2/runtimev2/clarification/core.py:547` 新增 `_note_slot_mismatch`（三段对账主判）＋ `:604` `_slot_mismatch_reason`（拒因逐字稿拼装：头行＋逐子问题三行块＋尾行）＋ `:631` `_split_on`（`find` 手切——本块源码禁 `split`／`partition` 族方法词面，AST 闸 `::no_lexicon_or_regex_in_clarification` 咬合）＋ `:646` `_ledger_row_line`（【台账相关行】整行原文：块内以投影行 `value` 串为锚扩到行界，零第二次渲染）＋ `:662` `_window_legal`／`:672` `_is_iso_day`（窗形读法照 `appv2/tools/precondition.py` 的 `date.fromisoformat(window_end[:10])`，不新造）；`:477` `_on_decompose` 改调对账、拒因码换新；旧 `_verbatim_note` 退场。
  2. `appv2/runtimev2/clarification/constants.py:69` 拒因码 `ledger_notes_not_verbatim` → `ledger_notes_slot_mismatch`（**枚举仍九值、未扩员**；明面文案别处无消费方，全仓仅本块＋本块测试引用）；`:117`–`:139` 新增槽位对账常量块（分隔符／段名表／`BINDING_STATES` 闭世界／窗三形）；`:179`–`:195` 新增拒因文案（头行／单行标题形／三行块——逐字稿照裁）＋段级原因四值＋名录无此名壳语。段数与 ISO 日形长度取自形串（`len(NOTE_SEGMENTS)`／`len(ISO_DAY_SHAPE)`）——避裸整数常量撞限额数值探针（`::subtask_cap_from_budget_table`）。
  3. `appv2/runtimev2/clarification/volatile.py:62` 新增 `ledger_name_rows`（**名录来源单点**）：名→行原文，名取投影行结构列（`_NAME_COLUMNS`＝`metrics[].slot`／`objects[].obj`／`relations[].rel`），行原文取同行 `value` 串；与 `render_ledger_resident_block` **同源**（皆自本模块 `ledger_projection` 单点投影）——**不新造第二名录源**，且本块不 import `appv2.tools`（票面边界红线②与本块依赖白名单断言不变）。
  4. `specs/clarification.md`：接口定义 `Subtask.ledger_notes` 注释（:54）／`ClarifyRejection.reasons` 枚举（:57）／错误契约（:66，含**拒因载荷形逐字稿**）／**行为 8 整条换裁法**（:86，注「2026-10-16 改·流水 64，Owner 裁」）／验收两行（:119／:129）与风险 2 措辞（:137）同步。
- **名录取法的取舍（先读现有输入面再定）**：旧 `_verbatim_note` 输入面＝`(note_text, injection_block)`；本改沿用「块在场」这一输入，但**段一名录取投影结构列、不取块内行首串**——理由：块内行首是台账原名 `★产量完成率`（含 ★☆／括注尾缀），逐字取会把合同样例教的剥法纯名 `产量完成率` 一起拒（正是本改要拆的墙）；且块内剥法要在本块重演一遍词面操作（与 AST 闸冲突）。**台账名录集合＝投影的指标/对象/关系名**（照裁）。空投影＝名录制空 → 一切槽位判「不在台账名录」（fail-closed，与旧判据同向不降级）。
- **测试（改前改后对比＋段级拒例）**：
  - `tests/domains/test_v2_clarification.py::ledger_notes_slot_reconciliation`（原 `::ledger_notes_verbatim_from_injection`，:549）＝正例：真机 N-01 形 `油田｜未绑定｜2026-09-16~2026-10-16` **必过**（用例内 `assert note not in block` 逐字记旧判据必拒、docstring 记墙拆面）；同时核段一名两种写法（`产液量` 指标 slot／`油田` 对象名）。
  - `::boundary_slot_reconciliation_rejections`（原 `::boundary_paraphrased_notes_rejected`，:1047）＝【边界集】十形四类：槽位不在名录（自造／摘要改写／真机外名）／绑定态越界（`草案`＋真机英文形 `bound`）／窗形不合法（胡写／单端非法／空段）／段数非三（缺／多）；逐形核**段名＋原因＋期望形＋台账相关行**四要素、拒因回喂面（`decision_error`／step payload）与「不静默放行、不自动修补」；另核多名同发（头行 `s1、s2`、逐 id 一块）＋三合法形放行面＋空投影 fail-closed。
  - **既有 V2 链测的注释 fixture 随判据换形**（同批，均为真机 V2 引擎面）：`tests/domains/test_v2_four_phase.py:146` `v2_ledger_note`（原返回注入块整行 → 改返三段形；就地核 keyword 真在名录）、`tests/api/test_v2_composition.py:164` `_ledger_note`（同上，dump 源＝生产缝）；真机 ledger 面另由 `tests/domains/test_v2_clarification.py:165` `_real_ledger_dump`（问数组台账态快照）就地自证：N-01 形在**真投影**下同过、「油田」真在真对象名录。
- **验证（改后实跑，均 exit 0）**：`pytest tests/domains/test_v2_clarification.py -q` → **22 passed**；`pytest -q` 全量 → **2165 passed, 108 skipped**（不回归）；`ruff check app appv2 tests migrations tools` → All checks passed；`mypy app appv2` → no issues（244 files）；`lint-imports --config tools/importlinter_v2.toml` → **18 kept, 0 broken**；`tools/check_specs.py` → PASS（0 警告）；`tools/ref_resolvable.py check` → 绿（22 份规格）。未 git commit（主窗统一提交）。
- **遗留（只记录、不处理——超本裁改动面或需 Owner 复议）**：
  1. **样例绑定态字面与闭世界不相交**：`appv2/runtimev2/prompts/decision_round.py` 的样例段二仍教 `在册可出数`（`_BOUND_BINDING`），而闭世界只有 `{"已绑定", "未绑定"}`——**已绑定支的样例形过不了新闸**（未绑定支＝`未绑定` 已对齐）。真机实测模型还写过 `bound`／`可出数`（`logs/llm_calls/20261016.jsonl` 统计：`日产油量｜bound｜…` 9 处、`可出数` 3 处）——同一病灶的绑定支不面。建议随批把 `_BOUND_BINDING` 改 `已绑定`（１ 行＋`specs/prompts.md` 行为 10 注）；本批未动（超裁改动面）。
  2. **术语／族标注名是否进名录待裁**：裁文列举「指标/对象/关系名」，故 `术语`（如 `老完成率`／`躺井`）与 `族标注`行首名**不在名录**。代价面有三处既存事实：①真机日志有术语作段一的形（`躺井（黑话 → …）｜未绑定｜…`、`老完成率｜…`）；②`tests/domains/test_v2_four_phase.py:1774/1930` 两处与 `tests/domains/test_v2_multi_turn_context.py:903` 原来正是拿术语名（`老完成率`）当段一（本批已改名录内名并就地留注）；③拒因壳语「只许用台账注入块内出现的指标/对象名」与块内 `术语｜…` 行并存，读来自相矛盾（模型会看到该名就在块里）。若裁「术语名也是台账条目名」，落法＝`_NAME_COLUMNS` 加 `("terms", "term")`（族标注同理加 `("families", "name")`），一行改。
  3. **双 null 发射形的字面**：裁文列「双 null 发射形」未给字面，本批取 `null~null`（对齐 `ISO~ISO` 槽形）；真机日志未见该形（模型宁写「窗未定」／「无时间窗」）。字面待裁；`无时间窗` 未纳入（裁文只列「窗未定」）。
  4. **裁外文档措辞未同步**（本批只动 `specs/clarification.md`＋本记录）：`specs/agent-loop.md:85`「ledger_notes 必填——从词典层注入块逐字转抄的台账注释」、`specs/prompts.md:89` 行为 8 括注「`ledger_notes` 逐字可求得的前提」、`docs/runtime-refactor/explain/clarification-讲释.md:69`（行为 8 人话）三处仍述旧判据。
  5. **票面引用过时**：`tickets/v2-refactor/RT-W4-02a-clarification.md:38/70` 与 `RT-W4-02b-clarification.md:35/58` 仍引旧测试标识与旧判据措辞（已收票历史件，未回改）。
  6. **名录机取面**（原票面登记项）：名取自投影结构列（`ledger_name_rows` 单点）；若后续 `tools` 侧新增正式「名录面」读口（如 `tools.ledger_facts` 的对账面），本块应改经该单点取（现不 import `tools`——边界红线②）。
  7. **★☆／括注指标名的段一形**：名录取**剥法纯名**（`metrics[].slot`——`产量完成率`），而台账行首串是原名 `★产量完成率`；故模型照块内行首抄 `★产量完成率｜…` 会被判「不在台账名录」。真机探针：`产量完成率｜未绑定｜2026-09-16~2026-10-16` ✅／`★产量完成率｜未绑定｜2026-09-16~2026-10-16` ❌（槽位段）。裁文【期望形】占位语是「〈台账行首名〉」（逐字稿照裁未改），与剥法纯名的口径需在下一轮措辞里对齐（块内 `value` 串仍在【台账相关行】里给到全名，模型可自纠）。

---

## 2026-10-16 闸对齐微批（顺流水 64 裁方向，3 项）

**依据（真机日志 `logs/llm_calls/20261016.jsonl` 本轮实测）**：段二非闭世界值确有实测——`未绑定｜` 196 处、`｜bound｜20xx-` 33 处、`｜可出数｜…` 3 处；段三另有「无时间窗」**6 处**三段形（如 `N-02 井防砂方式｜未绑定｜无时间窗`、`无指标命中｜未绑定｜无时间窗`）——上节遗留 1／2／3 的病灶面皆有真机形。

- ①**样例绑定态对齐闭世界**：`appv2/runtimev2/prompts/decision_round.py:121` `_BOUND_BINDING`「在册可出数」→「**已绑定**」（样例教的即闸收的）＋就地注；`specs/prompts.md` 行为 10 补注（样例 `ledger_notes` 段二字面＝闭世界值 `已绑定`／`未绑定`）。**V1 面不动**：`appv2/runtime/orientation.py:216` 仍「在册可出数」（V1 无三段对账闸；`tests/domains/test_v2_v259_clarify_assembly.py:51` 测的正是 V1 该渲染器，就地留注不改值）。
- ②**术语进名录**：`appv2/runtimev2/clarification/volatile.py:56` `_NAME_COLUMNS` 加 `("terms", "term")`（:60；术语条亦台账条目行，块内 `术语｜…` 行与名录同源）；`appv2/runtimev2/clarification/constants.py:205` `NO_LEDGER_ROW_SHELL` 壳语改「指标/对象/**关系/术语**名」；`specs/clarification.md` 行为 8①（`:86`）与错误契约拒因载荷形（`:66`）同步。
- ③**「无时间窗」入窗段合法形**：`constants.py:140` 新增 `WINDOW_UNTIMED`＋合法字面集合 `WINDOW_LITERALS`（:143，＝「窗未定」／「无时间窗」／`null~null`）；`appv2/runtimev2/clarification/core.py:664` `_window_legal` 改**集合成员校**（`window in WINDOW_LITERALS`——集合字面落常量单点，本块源码零字面表／零汉字成员判据，AST 闸咬合）；`specs/clarification.md` 行为 8③ 同步（同义形收编；【期望形】逐字稿仍书「锚定窗或窗未定」，**不改 Owner 逐字稿**）。
- ④**旧措辞同步**（裁外文档＋代码注）：`specs/agent-loop.md:85`（ledger_notes 改述三段槽位对账口径）／`specs/prompts.md:89` 行为 8 括注（`ledger_notes` **槽位段**逐字可求得＝段一逐字 ∈ 名录，非整块逐字子串）／`docs/runtime-refactor/explain/clarification-讲释.md:69`（行为 8 人话换三段对账口径）；**同源镜像四处一并同步**（同一旧措辞的镜像面，漏改即自相矛盾）：`docs/runtime-refactor/explain/orchestration-讲释.md:47`（行为 1 的讲释）／`appv2/runtimev2/prompts/decision_round.py:172`（`render_ledger_resident_block` 注）／`docs/runtime-refactor/explain/prompts-讲释.md:64`（行为 10 讲释补绑定态段闭世界值）／`specs/prompts.md` 行为 10 注。
- **测试**：`tests/domains/test_v2_prompts.py:994/1026` 段二字面随闭世界改「已绑定」；`tests/domains/test_v2_tool_matching.py:93` 注释 fixture 同步；`tests/domains/test_v2_clarification.py` 正例新增**术语名作段一**（`_TERM_ROW` 面：块内 `术语｜…` 行在场＋段一必过）与**「无时间窗」放行形**（`::boundary_slot_reconciliation_rejections` 三合法形改四形）。
- **验证（改后实跑，均 exit 0——CI `.github/workflows/ci.yml` 本仓步骤全量）**：`pytest -q` 全量 → **2165 passed, 108 skipped**（不回归，同上批基线）；`ruff check app appv2 tests migrations tools` → All checks passed；`mypy app appv2` → no issues（244 files）；`lint-imports`（默认配置：B16／B1）→ **6 kept, 0 broken**；`lint-imports --config tools/importlinter_v2.toml` → **18 kept, 0 broken**；`tools/contract_coverage.py check` → 绿（V1 173＋V2 4 条双向对账）；`tools/debt_markers.py check` → 绿；`tools/check_specs.py` → PASS（0 警告）；`tools/ref_resolvable.py check` → 绿（22 份规格）；`tools/prototype_guard.py check` → GREEN（web 未动）。未 git commit（主窗统一提交）。
- **余留（仍开口）**：上节遗留 5（票面历史件引用过时）／6（名录机取面）／7（★☆ 括注名段一形）不变；**族标注名仍未进名录**（本微批只补术语，族标注同理加 `("families", …)` 待裁）；`prompts` 样例段头逐字「ledger_notes 逐字转抄台账全量块」（`_DECOMPOSE_EXAMPLE_HEAD`）未动——V1 迁移逐字字面，与新对账口径的字面差待措辞轮处理。
