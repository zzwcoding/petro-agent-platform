- 日期：2026-10-15 ｜ 状态：**回工补写**（独立复审打回项落实施工）
- 本次改 `specs/preconditions.md` ＋ 真源侧两处（`docs/adr/0005-子任务图与前置条件机.md` 修订注记、`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md` 仅 M4 一行）。行号均指改后文件（preconditions 141 行）。

# preconditions 规格回工补写（复审发现 #4/#5）

| 修改点 | 改了什么 | 依据 |
|---|---|---|
| `specs/preconditions.md:138` | 挂钩表补登记 **pin-14**（模糊时间词＋plan 非空 → 确定性改判走 clarify 三选一反问帧）——落点＝判定序第 2 位闸1b，消费 `tool_matching` 时间窗结论 → `ask` 反问 | 复审发现 #4（【P1】挂钩表补登记）；钉面 `eng/04a` pin-14（真源 `arch/P4a2-票堆V2-51至55.md:21-22`） |
| `specs/preconditions.md:139` | 挂钩表补登记 **pin-16**（软失败域闸：data/semantic 成功返回但域错 → 换链回炉恰 1 次为界）——落点＝行为 7 换链回炉一次为界 | 复审发现 #4；钉面 `eng/04a` pin-16（真源 `arch/P4a2-票堆V2-51至55.md:20`） |
| `specs/preconditions.md:140` | 挂钩表补登记 **pin-17**（前置条件机**三态**语义一字不动：放行／拒答／等用户，注记并入放行；判定固定序命中即停；零 LLM 面；扩口未批不得直答终局）——落点＝行为 2／3／5＋判定序明文表＋零 LLM 红线；真源 `walk/裁决表.md` §12-B/C | 复审发现 #4；钉面 `eng/04a` pin-17（已按裁决 §12-B 记三态） |
| `specs/preconditions.md:53` | 「三态与真源『四态』的差异」条：§12-A 更正为 **§12-B**（§12-A 是语义上移裁决且注「不动 ADR-0005」，三态裁决在 §12-B——原引用系修订回执 P-6 落笔时的编号误差）；「ADR／S1 同步修订」标注**已兑现**（2026-10-15），指向 ADR 修订注记与 S1 M4 行 | 复审发现 #5（【中】ADR-0005／S1 四态同步）；即 `spec-review/preconditions-评审.md` F-10 的兑现补完（修订回执 P-6 只落了声明句，ADR/S1 本体未动） |
| `docs/adr/0005-子任务图与前置条件机.md:36-38` | 末尾新增「修订注记（2026-10-15）」一节：随裁决 `walk/裁决表.md` §12-B 改**三态**（放行／拒答／等用户，注记并入放行）；决策段「判四态」原文**保留加注不改**；现行口径以 `specs/preconditions.md` 三态闭世界为准 | 复审发现 #5 处置之一（ADR-0005 加修订注记，原文保留加注） |
| `docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md:27` | M4 行「零 LLM 逐子问题四态闸（放行/挂起/拒答/注记）」改「零 LLM 逐子问题**三态闸（放行／拒答／等用户；2026-10-15 随裁决 §12-B，注记并入放行）**」——**仅此一行，S1 其余未动** | 复审发现 #5 处置之二（S1 的 M4 行同步） |

## 钉落点登记（无落点不硬挂）

- **pin-24（相位合同一次性：contracts_appended 回炉轮不重发）**：属 state/context 记账面（真源 `recon/I2b-RunState全字段.md:40`），本块只有回炉轮的消费侧——**待 orchestration/context 规格**，不硬挂本块挂钩表。

## 验证

- `uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿**。未 git commit。

---

## 拆票期卡级修正（流水 50）——2026-10-16

- **缺口描述**：`tickets/v2-refactor/RT-W4-04-preconditions.md`「施工前对账项」③ 原文（逐字）：「**信号落地写口**：规格「触及的模块」只列 `preconditions`／`tools`／`state`，未列 `bookkeeping`——行为 10「落 step 记录」与 notice 的**写入承接方**须由主窗对账明确（本块只产信号值，不直写状态——W3 `bookkeeping` 单写口的「相位不得直写」约束面；测试 `::verdict_signal_present` 经写口断言）；若对账结论为本块须直引写口，属接口变更、停报 L0。」
- **裁口径（主窗 L0，2026-10-16）**：相位禁直写是全局铁律（`bookkeeping` 是唯一写面），写口＝`bookkeeping.record_step`／`bookkeeping.notice`——**触及表加一行 bookkeeping**（注「**写口面**——落 step 记录/notice 经 bookkeeping 唯一写口，只引函数、不引其内部」），**`modules.md` `## preconditions` 卡依赖行同步补注**；**不改任何行为定义**。
- **改动位置**（行号指改后文件；`specs/preconditions.md` 143→144 行、`specs/modules.md` 到 640 行）：
  1. `specs/preconditions.md:30`——「触及的模块」表新增行：`| bookkeeping | 新增依赖 | **写口面**——落 step 记录/notice 经 bookkeeping 唯一写口，只引函数、不引其内部 |`。
  2. `specs/modules.md:205`——`## preconditions` 卡依赖行补 `；\`bookkeeping\`（**写口面**——落 step 记录/notice 经其唯一写口，只引函数、不引其内部）`。
- **依据（逐字）**：写口面＝`specs/modules.md` `## bookkeeping` 卡职责行（「全节点共享的写入面」）＋其公开接口节树「**共享写口（唯一入口；相位禁直写）**」与两行签名 `def record_step(state, *, kind, title, status="ok", payload=None, manifest=None) -> StepRecord: ...`／`def notice(state, *, type, gates=(), content) -> None: ...`；本规格行为 10（`:80`）「每个 `SubtaskVerdict` 落 step 记录（含 `hit_rule`）」＋「不降级与静默禁令」（`:98`）「任何非 `allow` 与任何带注记的 `allow` 必须产生机读信号：step payload 的 `hit_rule`／`decision`／`notes` 字段 ＋ notice」——**行为定义一字未动**（行为 1–10、判定序明文表 `:82–:93`、验收表 `:105–:118` 均未改）。
- **未随批改面（登记交主窗）**：① 本规格「依赖与风险」依赖行（`:122`）仍只列 `state`／`tools`——本批只授权「触及表＋卡依赖行」两处，该行**未同步**（先例：tool_matching 的 V1 发起面回改曾四处同步；是否随批补，提请主窗裁）；② **`tools/importlinter_v2.toml` 的 R8 语义面发现**（探针实测，见下）——**写口面在现配置下会撞 R8**。
- **R8 探针实测（重要，未改 toml——「不许放宽闸」）**：临时探针（`appv2/runtimev2/verification/__init__.py` 加 `from appv2.runtimev2.bookkeeping import record_step`；`appv2/runtimev2/bookkeeping/__init__.py` 加 `from appv2.runtimev2.gateway_adapter import complete`）后实跑 `uv run lint-imports --config tools/importlinter_v2.toml` → **`Contracts: 16 kept, 2 broken`**，R8 报「appv2.runtimev2.verification is not allowed to import appv2.runtimev2.gateway_adapter」并给出链 `verification → bookkeeping (l.7) → gateway_adapter (l.7)`（R2 同时红，链经 `gateway_adapter.fake`）。**根因**：R8 契约未设 `allow_indirect_imports`，import-linter 的 forbidden 契约默认为**检间接链**（对照 `tools/importlinter_v2.toml:16` R6 侧注释「`allow_indirect_imports = true`＝直接引用才违规」——即已显式放宽的两条才只咬直引）。**结论**：`preconditions`／`verification` 一旦按本批卡面 import `bookkeeping` 包根，R8 必红（`execution` 同理）。**修法须主窗裁**（加 `ignore_imports`／对 R8 设 `allow_indirect_imports = true`／或写口改经 `state` 形状而非 `bookkeeping`），**探针已全部回退**（`git checkout --` 三文件；回退后复跑 18 kept／0 broken、6 kept／0 broken）。
- **行号漂移（供票面回填）**：`specs/preconditions.md` 原 `:1–:30` 不变、原 `:31` 起 **+1**——原判定序明文表 `:83–:92`→`:84–:93`；原验收表 `:104–:117`→`:105–:118`；原「依赖与风险」依赖行 `:121`→`:122`；原 pin-31 挂钩行 `:139`→`:140`；文件 **143→144 行**。`specs/modules.md`：`## preconditions` 卡依赖行 `:200`→`:205`（该卡位于 tool_matching 卡之后，含前述 +5 漂移）。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（22 份规格）**；`uv run lint-imports --config tools/importlinter_v2.toml` → **Contracts: 18 kept, 0 broken**；`uv run lint-imports`（默认配置）→ **6 kept, 0 broken**。均 exit 0（改后／探针回退后实跑）。未 git commit。
