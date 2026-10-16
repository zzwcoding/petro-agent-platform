- 日期：2026-10-15 ｜ 状态：**回工补写**（独立复审打回项落实施工）
- 本次只改 `specs/understanding.md`，其它文件未动。行号均指改后文件（133 行）。

# understanding 规格回工补写（复审发现 #6/#7）

| 修改点 | 改了什么 | 依据 |
|---|---|---|
| `specs/understanding.md:133` | 挂钩表补登记 **pin-26**（对话层纯度：dialogue 只装自然对话，过程记录入 process_notes 不混层）——落点＝行为 9「模型原话不进对话层（只进过程档案与留痕）」（原文 :81，改后行号 :80） | 复审发现 #6（【中】挂钩表补登记 pin-26）；钉面 `eng/04a` pin-26（真源 `arch/P8b2-评测病理.md:63`、`arch/P5b1-对话状态重构方案.md`） |
| `specs/understanding.md:62-64` | 「框架与依赖红线」第 2 条（模型调用唯一出口）与第 5 条（禁手写替代）**合并为一条**：两处重复引 **R7 契约**与「无旁路」断言，并为一条「模型调用唯一出口＝`gateway_adapter`（禁手写替代）」，R7 契约、B6 界注、验收写法各只出现一次；文件 134→133 行 | 复审发现 #7（【低】红线第 2/5 条重复引 R7，原文 :62 与 :65） |

## 钉落点登记（无落点不硬挂）

- 本块范围内无其他待挂钉；pin-24（相位合同一次性）归 state/context、verdict(final) 帧归属归 orchestration——均不在本块作用面，未硬挂（见各自回工补写的登记）。

## 验证

- `uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿**（红线合并后 R7/R6/R5b 编号仍在真源集内）。未 git commit。


---

## V1 发起面回改（主窗裁 doctrine）——2026-10-15

- **依据**：复审⑦处置（`docs/runtime-refactor/00-决议与方法.md` 流水 27 第①裁）——相位调模型一律经 `bookkeeping.call_model`（其内部唯一出口 `appv2.runtimev2.gateway_adapter`）。本次只改 `specs/understanding.md`（134→135 行）＋本记录，其它文件未动；未 git commit（主窗统一提交）。
- **修改点**（行号指改后文件）：
  1. 「触及的模块」依赖表（:35-36）：新增 `bookkeeping` 行（改动类型＝**新增依赖**；说明＝「模型调用发起面：经 bookkeeping.call_model（单点发起），本块不直引 gateway_adapter」）；同表 `gateway_adapter` 行说明由「模型调用唯一出口；本 spec 只消费」改为「模型出口（唯一出口仍归它）；本块不直引——经 bookkeeping.call_model 发起」。
  2. 「框架与依赖红线」（:63）：「模型调用唯一出口＝gateway_adapter（禁手写替代）」改为「**模型调用发起面＝`bookkeeping.call_model`（单点发起，禁手写替代）；其内部唯一出口＝`gateway_adapter`**」，补「import 落点＝`appv2.runtimev2.bookkeeping` 包根——R2 禁深层子模块」；R7 括注由「runtimev2 各块只经 gateway_adapter 调模型」改准为「禁直引 `appv2.infra.llm_client`——模型出口仍唯一归 `gateway_adapter`」＋「发起面收敛为规格层 doctrine，不设闸——主窗 2026-10-15 裁」；「无旁路」断言对象同步改为发起点只出现在 `bookkeeping.call_model`。
  3. 「依赖与风险」依赖行（:115）：补 `bookkeeping`（模型调用发起面——`call_model` 单点发起）；`gateway_adapter` 括注改为「经 `call_model` 的内部唯一出口，本块不直引」。
  4. 「与闸的挂钩表」（:129）：「模型调用只经 `gateway_adapter`」行改为「模型调用经 `bookkeeping.call_model` 发起（单点发起；其内部唯一出口 `gateway_adapter`）」；挂钩列注「出口面 R7；发起面为规格层 doctrine，不设闸」；现状列不变。
- **不加闸（裁定照录）**：importlinter 边界闸**不随本批加**——R7「只经出口」＋R8 语义不变，doctrine 是规格层不是闸层（主窗 2026-10-15 裁）。
- **契约字面核对（未改 toml）**：逐条实读 `tools/importlinter_v2.toml`——R7（name「R7 runtimev2 各块只经 gateway_adapter 调模型」，forbidden＝`appv2.infra.llm_client`；source 含 `appv2.runtimev2.bookkeeping`）与 R2（业务相位 forbidden 含 `appv2.runtimev2.bookkeeping.*` 深层子模块、不含包根）均与新 doctrine **无字面冲突**。实现期注意：相位 import 只许 `appv2.runtimev2.bookkeeping` 包根（R2 面）。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（20 份规格）**。均 exit 0（批次一改后实跑）。

---

## 流水 43 裁决落笔（裁决⑦a＝补 parsing None→本块转译的输入半面）——2026-10-16

- **依据**：主窗流水 43⑦（2026-10-16，真源 `docs/runtime-refactor/00-决议与方法.md` 流水 43）零散回提三项之一——understanding 补「parsing 返 None → 本块抛 `UnderstandingParseError`」输入半面（照 parsing 风险 6 措辞；真源 `specs/parsing.md` 行为 1／接口⑤）。销 `docs/runtime-refactor/spec-review/parsing-评审.md` 风险 7⑩（P-23「understanding 回认输入半面」）。
- **修改点**（行号指改后文件；135→136 行）：
  1. 接口定义「错误契约」行（:56）：句尾补「parsing 解析不合格（`parse_understanding` 返 `None`）在场时由本块转译抛 `UnderstandingParseError`（唯一转译出口；真源 `specs/parsing.md` 行为 1／接口⑤——流水 43⑦ 补落输入半面）」。
  2. 「依赖与风险」新增风险 4（:121）：「parsing 不合格信号的转译衔接（输入半面）」——转译义务＋销项登记（parsing-评审 风险 7⑩／P-23 随本句销项，流水 43⑦）＋检测手段（与 `specs/parsing.md` 行为 1 对读＋`::understanding_malformed_none_no_fallback`）。
- **未随批改面（登记交主窗）**：①行为 7（解析严格）未重复补句——错误契约是该句唯一落点，避免同文两写（验收行 `malformed_json_raises_no_fallback` 已覆盖断言面）；②`specs/parsing.md` 风险 6 的「回提登记」句未回改（其清单体例＝只登记不代办，销项以本件与本规格风险 4 为凭）。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（22 份规格）**。均 exit 0（改后实跑）。未 git commit（主窗统一提交）。

---

## 2026-10-16 流水 67 L3 阻塞修复（schema 拒回喂重试恰一次；主窗裁「参数错误应修参＋拒因带教」）

**依据（真机证据 `docs/runtime-refactor/ladder/L3/04-W-11井投产后预计躺井-summary.md`，run-60bc4aaa）**：模型应答漏 `metric_candidates` 必填（旧两行式塞进 `text`）→ `UnderstandingParseError` → 整 run 首步 `failed`、**无任何修正回路**；同题 gold 期望「优雅走到检索再拒答」。对照面＝澄清相位早有打回带教（`specs/clarification.md` 行为 17／18：拒因回喂＋三段带路）。主窗裁：**拒因回喂＋限一次重试＝修参，不是降级**——V2「不猜不降级」纪律不变（不静默补默认），但「拒因回喂一次」属于把参数说清楚再要一次。

- **改法（`appv2/runtimev2/understanding/interpret.py`）**：`interpret` 首读 → `parse_understanding` 返 `None` → **`_append_schema_feedback`**（拒因载荷追加链尾：`messages` 一条 `user` ＋ 过程档案一条「读题回喂重试」注记）→ **同相位再读一次**（`_read_and_parse` 复用——同形、非另开路径）→ 仍拒才 `report_parse_failure` ＋抛 `UnderstandingParseError`（编排收 `failed` 不变）。**上限恰一次**＝结构化（写死两段，非循环）。首读与重试**同形复用** `_read_and_parse`（call_model 单点发起 ＋ 应答追加链尾 ＋ 读题注记）。
- **载荷三段（`appv2/runtimev2/understanding/feedback.py` 新增＋`constants.py` 文案单点）**：①【拒因】＝具体不合项（取 `parsing.understanding_schema_feedback` 的**唯一诊断出口**，本块**零 schema 重判**）；②【期望形】＝理解面输出契约两形＋「`route=full` 时 `text`／`metric_candidates` 均必填、无命中指标给空数组 `[]`／`route=direct` 无 `metric_candidates` 键」；③尾行＝「只修正不合项，其余内容照旧，重新输出一个 JSON 对象（不要输出 JSON 之外的解释文字）。」。载荷**自足**（链上直投、无外层壳、不叠字）；三段「\n」连接。
- **纪律面（逐条对照票面）**：**零副作用**——直答核验／候选名录对账／`report_parse_failure` 既有行为不变（回喂支不发 notice、不记步、不落判定字段；如实上报仍在两读皆拒时出一份、不翻倍）；**两次调用都记账**（`call_model` 单点，各一条步）；**前缀延伸不破**（载荷落链尾＝追加形，`pin-22`；机检＝第二次调用链逐字包含第一次全链）；`dialogue` 零写入（pin-26 渲染面）；不补默认、不改写模型原话、不降级提取（本块**无 schema 重判**——判定单点仍在 `parsing`）。
- **规格与审计面**：`specs/understanding.md` 接口定义新增「schema 拒回喂重试恰一次」条／行为 13（全文含五条断言）／「不降级与静默禁令」节补「拒因回喂＝修参、非降级」句／验收表新增五行／文末审计块；`specs/agent-loop.md` 行为 1（understand 读题句补「拒因回喂重试恰一次→仍拒才 fail-closed 收束 `failed`」）／验收表新增两行；`specs/parsing.md` 理解面诊断面同批补录（跨块 additive，见该规 `parsing-回工补写.md` 同批节）；`docs/runtime-refactor/explain/understanding-讲释.md` 行为 7 措辞镜像同步（补行为 13 一段——旧句「必须当场喊出来」在回喂面下会自相矛盾）。
- **测试（新增 7 个）**：`tests/domains/test_v2_understanding.py::schema_reject_feedback_retry_once`（首拒→回喂→次读合规→正常分派；调用恰 2 次、步恰 2、无 notice／无报告步、链形四件、读题注记×2＋回喂注记×1）／`::schema_reject_twice_raises_with_feedback_trace`（三形脏应答各两读皆拒 → 抛错＋链上载荷＋过程档案注记＋报告步恰一，步数＝2＋1）／`::schema_feedback_three_segment_payload`（四支拒因逐字＋期望形两形＋尾行；恰三段、壳恰一遍、与注记同源）／`::schema_feedback_prefix_extension`（第二次调用链＝第一次逐字前缀＋两件）；`tests/domains/test_v2_parsing.py::understanding_schema_feedback_reasons`（诊断面逐支＋同判闭世界）；`tests/domains/test_v2_four_phase.py::test_four_phase_understand_schema_feedback_retry_recovers`（**端到端**：真机原形首读 → 回喂 → 四相位全程跑通、run `completed`、理解调用恰 2 次、载荷落库可见）／`::test_four_phase_understand_schema_feedback_twice_fails`（端到端：两读皆拒 → `failed`＋`run_failed` notice、调用恰 2 次、四相位未入场）。**既有断言改准一处**：`tests/domains/test_v2_understanding.py::test_reporting_signal_present` 解析失败案步数 2 → 3（记账步 2＋报告步 1——回喂带来的第二次调用如实记账，非翻倍）。
- **验证（改后实跑，均 exit 0）**：`pytest -q` 全量 → **2179 passed, 108 skipped**（基线 2172＋新增 7）；`ruff check app appv2 tests migrations tools` → All checks passed；`mypy app appv2` → no issues（245 files）；`lint-imports`（默认）→ 6 kept, 0 broken；`lint-imports --config tools/importlinter_v2.toml` → 18 kept, 0 broken；`tools/contract_coverage.py check` → 绿；`tools/debt_markers.py check` → 绿；`tools/check_specs.py` → PASS（0 警告）；`tools/ref_resolvable.py check` → 绿（22 份规格）。未 git commit（主窗统一提交）。
- **遗留（只记录、不处理）**：
  1. **同批旁证病灶（任务书指令区仍是 V1 两行式，与输出契约自相矛盾）**：`appv2/runtimev2/prompts/constants.py` 的 `TASK_BOOK_TASK`／样例集／红线仍教「输出固定两行」「指标候选：…」，而任务书尾段 `【输出契约】` 要单一 JSON（真机 `run-60bc4aaa` 的模型正是照指令区两行式作答、再把两行塞进 `text`）。该文案属 Owner 审定面、本批**无逐字稿故不动**（登记件真源＝`appv2/runtimev2/prompts/task_book.py` 模块注的既有登记）——建议主窗随批裁一处统一措辞（改后本回路大概率不再需要触发）。
  2. **回喂的 `user` 条与澄清面增量条的物形关系未定**：本批载荷**自带整套壳**（链上直投，故不套「上次发射被拒：」外层），与澄清面「已自带壳者原样透传」纪律同向但**不同一常量**（澄清壳体在 `prompts/decision_round.py`，理解载荷在 `understanding/constants.py`）——两处字面各自独立，无叠字风险；若日后要单点化壳体，须动 `prompts` 公开面（本批边界外）。
  3. **重试面未进审计责任账**：`security.audit` 五处留痕不含本回路（留痕面＝链＋过程档案＋调用步）——本批按「零副作用面」不做审计接线；若主窗要「重试可对账」，需另裁（合 `specs/infra.md` 行为约定 3 的 action 闭世界七值）。
  4. **两行式的直答旧通道**（`直接回答：`）仍零可达、照旧不受理——本回路只救 JSON 形态内的漏字段／类型／越界，不构成任何降级提取通道（行为 7 末句不变）。
