# execution 规格回工补写（2026-10-15）

- 依据：独立复审判 `specs/execution.md` **PASS with findings**——回工令必修 6–9（下表记为复审发现 R6–R9，编号对应回工令必修序号）。
- 范围：只改 `specs/execution.md`（本文件是修改点台账）；不碰 `specs/agent-loop.md`（另一窗口施工中）。
- 施工纪律：行为约定每条可写成 pytest 断言；数字只引真源；阈值数值保持「阶段 5 待定」但行为归属与披露义务定死；pin-08 交叉面规则与 `specs/answering.md` 行为 12 **逐字一致**（已机比 538 字节相同）。
- 闸验证：`uv run python tools/check_specs.py`＝**PASS（0 警告）**；`uv run python tools/ref_resolvable.py check`＝**绿（13 份规格可解析，含新增真源 `裁决表.md` §10-B／`P4b-票堆V2-56至65.md`／`V2-61-材料承载分形渲染.md`）**。

## 修改点清单

| # | 落点 file:line | 一句话 | 依据复审发现 |
|---|---|---|---|
| 1 | `specs/execution.md:80`（行为 3 措辞修正） | 「refused（闸拒＝终局、不回炉）」改为「refused（**前置闸拒**——preconditions 拒＝终局、不回炉）」，并注明与 `specs/agent-loop.md` 的「绑定闸拒＝换链回炉」是两面、绑定闸拒不落本档——消除「闸拒」一词两义（agent-loop 侧由另一窗口改，本批只动本文件） | R9【P2】「闸拒」两义 |
| 2 | `specs/execution.md:81`（行为 4 重写） | 原「阈值待定」尾巴替换为**行集题交付与落引用界线**：行集题（明细行集类）全量交付为默认、丢行=0；非行集大结果超阈才落引用＋截断/落引用必披露；阈值数值阶段 5 待定、行为归属与披露义务即此定死；真源 `tickets/v2/V2-61-材料承载分形渲染.md`:5；与 `specs/answering.md` 行为 12 互指「同一规则、逐字一致」 | R6 交叉面（pin-08 与落引用规则合并，两规格同一说法） |
| 3 | `specs/execution.md:83`（行为 6 判据修正） | 「恢复时校验『事件未过期、未重复』」改为「**恢复时重取易变环境量**（等待期间可能变了的量必须重校验——真源 `docs/runtime-refactor/walk/裁决表.md` §10-B），**不重放已完成的部分**（已完成子问题不二次执行）」——删掉写不成 assert 的「过期」措辞，改用裁决表 §10-B 的机读判据（重取易变量＝可断言；不重放＝可断言） | R8【P2】行为 6「过期」无判据 |
| 4 | `specs/execution.md:90`（行为 13 新增） | 空手探查记指纹＋同参空手重发**发射级拒**：空手（工具失败／refused／重试耗尽，或成功但零新增非 notice 观察）→记同参指纹（判定键＝工具名＋参数逐字 JSON——参数改了＝新尝试）；发射级拒不执行工具、不占探查预算；首拒免轮、第 2 次起占轮；真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`:26-28（A-P4b-04/05/06）——发现步已归本块（行为 11），此钉落本块 | R7【P1】pin-06 落点 |
| 5 | `specs/execution.md:104`（验收表 refused 行措辞同步） | 「refused（闸拒）终局不回炉」→「refused（**前置闸拒**）终局不回炉」——与行为 3 同一措辞，不留块内两说 | R9【P2】配套 |
| 6 | `specs/execution.md:105`（验收表落引用行改写） | 「大结果落引用」行改为「**行集类结果不落引用**（全量行随观察交付，丢行=0）；**非行集**大结果落引用：窗口只留摘要＋引用＋行数（不留全文）」——测试标识 `::big_result_ref_only` 不变，判据对齐行为 4 新界线 | R6 交叉面配套 |
| 7 | `specs/execution.md:108`（验收表缺参恢复行改写） | 「恢复校验未过期未重复」→「恢复时**重取易变环境量**、**不重放已完成部分**」；测试标识 `::need_input_suspend_resume_guard` 不变 | R8【P2】配套 |
| 8 | `specs/execution.md:116`（验收表新增 pin-06 行） | 「同参空手重发→发射级拒（不执行工具、不占探查预算）；首拒免轮、第 2 次起占轮；**异参不拒（门开着）**」→ `::empty_probe_fingerprint_emission_reject`（阶段 5 承诺） | R7【P1】配套验收 |
| 9 | `specs/execution.md:145`（挂钩表新增 pin-06 行） | 空手探查记指纹＋同参空手重发发射级拒｜钉 **`pin-06`**（P1）｜待织网（阶段 5）——格式照 `specs/agent-loop.md` 钉行同款 | R7【P1】挂钩表补登记 |
| 10 | `specs/execution.md:146`（挂钩表新增 pin-16 行） | 软失败域闸换链回炉恰 1 次为界｜钉 **`pin-16`**（P1）｜注明「**承接在 `specs/preconditions.md` 行为 7**，本块提供回炉触发面；钉本体＝preconditions 侧 `::rewire_once_then_refuse`」——不重复建钉 | R7【P1】挂钩表补登记（pin-16 承接注记） |

## pin-08 交叉面规则的最终表述（本规格落点原文）

`specs/execution.md:81`（行为 4）——与 `specs/answering.md:82`（行为 12）冒号后**逐字一致**（机比 538 字节相同）：

> 行集题（明细行集类：问句要求明细／排名／列举全行集）全量交付为默认——引擎返回的全部数据行逐行交付、丢行＝0；非行集大结果超阈才落引用（窗口只留摘要＋稳定引用＋行数），截断与落引用必披露。阈值数值阶段 5 待定（随真机数据定），行为归属与披露义务即此定死：行集题不得因落引用而丢行。真源：`tickets/v2/V2-61-材料承载分形渲染.md`（:5——24 支一刀切截断废除、改分承载体渲染）。

## 遗留与移交

1. **阈值数值**：仍为阶段 5 待定（随真机数据定）——本批只定死行为归属（行集题全量交付／非行集超阈落引用）与披露义务（截断与落引用必披露），数值落定后回写行为 4 括注即可。
2. **「绑定闸拒＝换链回炉」侧**：在 `specs/agent-loop.md`，由另一窗口施工——本批只在行为 3 做了区分性措辞，未改 agent-loop 任何内容；两侧措辞最终对齐待 agent-loop 回工完成后人审一遍。
3. **发射级拒的机读信号形**：真源 A-P4b-06 只定「不执行工具、不占探查预算」的拒语义，未定义专用事件形；本批未新增信号要求（不发明业务事实），发射级拒的留痕面随阶段 5 织网时按 `tool` 事件实态定。
4. pin-16 的钉本体在 preconditions 侧（`::rewire_once_then_refuse`，`specs/preconditions.md:108` 已有验收行）——本块触发面（域错→回炉发起）的独立断言是否需要、归谁，待主窗核定后随织网补。


---

## V1 发起面回改（主窗裁 doctrine）——2026-10-15

- **依据**：复审⑦处置（`docs/runtime-refactor/00-决议与方法.md` 流水 27 第①裁）——相位调模型一律经 `bookkeeping.call_model`（其内部唯一出口 `appv2.runtimev2.gateway_adapter`）。本次只改 `specs/execution.md`（147 行不变）＋本记录，其它文件未动；未 git commit（主窗统一提交）。
- **本块定性**：`execution` 属**零 LLM 面**（R8 契约 source 覆盖 `preconditions`／`verification`／`execution` 三块）——**不调模型、不存在发起面**。按主窗裁注「零 LLM 不调模型，不加 bookkeeping 依赖」，本次**不新增 bookkeeping 依赖行**，只改措辞声明：
  1. 「框架与依赖红线」零 LLM 条（:71）：补「本块零 LLM 面（R8），**不存在模型调用发起面**——不调模型，模型调用发起面（`bookkeeping.call_model`）不在本块作用面」；「不得引 `appv2.runtimev2.gateway_adapter`」与 R8/R7 括注不变。
  2. 「与闸的挂钩表」零 LLM 行（:138）：硬要求列由「零 LLM 面（本块不引 `gateway_adapter`）」改为「零 LLM 面（本块不调模型、不存在发起面；不引 `gateway_adapter`）」；挂钩与现状列不变。
- **不加闸（裁定照录）**：importlinter 边界闸**不随本批加**——R8 零 LLM 面语义不变，doctrine 是规格层不是闸层（主窗 2026-10-15 裁）。
- **契约字面核对（未改 toml）**：R8（forbidden＝`appv2.runtimev2.gateway_adapter`，source 含本块）与新 doctrine 无字面冲突；R7 对本块「天然满足」的表述不受影响。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（20 份规格）**。均 exit 0（批次一改后实跑）。
