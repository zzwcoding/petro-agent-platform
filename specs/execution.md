# V2 批量执行（execution）

状态: 已定稿
来源: `specs/modules.md` `## execution` 卡、`docs/runtime-refactor/walk/13-批量执行-查询执行.md`、`walk/裁决表.md` §06/§13、`synth/S1`（M5）
版式: `docs/spec-format.md` ｜ 工序: `docs/spec-process.md`

## 目标

把过闸后的子问题**真去执行**（查数／搜报告），把结果收成**带出处的观察**——**只读并行、成功不重跑、失败只重做失败的**。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 子问题 → 工具 的提议与对账 | `tool_matching` | `specs/modules.md` `## tool_matching` |
| 逐子问题过闸（三态） | `preconditions` | `specs/modules.md` `## preconditions` |
| 组织答案、真流式推出 | `answering` | `specs/modules.md` `## answering` |
| 模型输出的解析 | `parsing` | `specs/modules.md` `## parsing` |
| 引擎与工具的实现 | `tools`／引擎（本块**只走其公开面**） | `specs/modules.md` `## tools` |
| 大结果原文的长期保管载体 | `persistence`（本块只经其公开面落引用） | `specs/modules.md` `## persistence` |
| 判「答案对不对／好不好」（语义判断）；拿词表／正则猜「这个结果算不算答上了」 | `verification`（答案质量）；本块的 `answered` 只按**可观察事实**（该子问题**是否拿到非空观察**）产出——**结构判定** | `specs/modules.md` `## verification`；`walk/00-设计总纲.md` §二 |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| execution | 新增 | 只读并行执行 ＋ 观察回流 ＋ 失败回炉 ＋ 记账 |
| tools | 新增 | 工具调用统一出口（本块只消费其公开面） |
| state | 新增 | 执行状态／观察序列／指纹簿记的状态形状；本 spec 只消费 |
| transport | 新增 | 执行期事件（`tool`／`observation`）经其发帧；本 spec 只消费 |
| persistence | 新增 | 大结果**原文落引用**的落盘面；本 spec 只消费 |

## 接口定义

```python
def execute(state: RunState) -> ExecutionOutcome: ...

class ExecutionOutcome:
    observations: list[Observation]      # 全局 [n] 序（引标与答案引用同一套序号）
    subtasks: list[SubtaskExec]          # 与子问题一一对应
class SubtaskExec:
    subtask_id: str
    exec_status: Literal["ok", "failed", "need_input"]   # 闭世界：**执行状态**
    answered: bool                       # **是否真拿到答案**（与 exec_status 分开记）
    error: ErrorClass | None             # 失败分类（可重试／修参／终局拒答）
    row_count: int | None                # 回来多少行（记账）
    ref: MaterialRef | None              # 大结果原文的稳定引用
class ErrorClass:
    category: Literal["retryable", "bad_args", "refused"]   # 闭世界＝三档（对齐 `## tools` 卡「可重试｜修参｜拒答」）
    reason: str
class MaterialRef:
    handle: str                          # 稳定引用（可寻址）
    summary: str                         # 窗口内只留的摘要
    row_count: int
class Observation:
    seq: int                             # 全局 [n] 序
    content: str | None                  # 小结果直接带内容
    ref: MaterialRef | None              # 大结果只带引用
    source: str                          # 出处（台账行／片段→报告→库／表名）
```

- **`exec_status`／`category` 都是闭世界**；越界值判失败（不猜、不取默认）。
- **`answered` 与 `exec_status` 不混**：`exec_status="ok"` 不等于 `answered=True`。
- 错误契约：工具调用抛错 → **不炸整批**；该子问题记 `exec_status="failed"` ＋ `error.reason`，其余子问题照常。
- 真源：`specs/modules.md` `## execution` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本模块不引入任何框架）。
- **模型调用不在本块**：本块只做确定性的工具调用与结果归一（若将来需要模型参与汇总，那属 `answering`）。
- **零 LLM 面**：`execution` 属零 LLM 面（R8），**不存在模型调用发起面**——不调模型，模型调用发起面（`bookkeeping.call_model`）不在本块作用面；**不得引 `appv2.runtimev2.gateway_adapter`**。对应闸：**R8 契约**（`tools/importlinter_v2.toml`；source 覆盖 `preconditions`／`verification`／`execution` 三块）。**R7 亦覆盖本块**（模型只经 `gateway_adapter`）——本块不调模型，R7 天然满足。
- **只经 `tools` 公开面**接触世界（本块不直引任何引擎）。对应闸：**R6 契约**。
- 大结果落引用**只经 `persistence` 公开面**（不自行写库／不直连对象存储）：**无对应边界闸**——按 `docs/spec-format.md` §五降维为 AST 断言「不许出现直连符号」（对象存储客户端／裸 DB driver 等直连符号）。原因：`tools/importlinter_v2.toml` R1–R8 未覆盖「直连对象存储／自写库」这一面（R2 只禁公共层**深层子模块**，不禁公开面与外部直连）。对应测试：`tests/domains/test_v2_execution.py::no_direct_storage_symbols`。
- **禁手写替代**：不得自建工具调用旁路、不得绕过 `tools` 直引引擎。

## 行为约定

1. **只读子问题并行执行**（本平台全部工具只读、无副作用，故并行安全）；**执行顺序不影响观察编号**——编号按子问题定序分配（同一输入两次运行得同一编号）。
2. **成功不重跑**：已成功的子问题（指纹簿记命中）**不重发工具调用**。
3. **失败分类写明文**：`retryable`（超时／上游抖动／限流）｜`bad_args`（参数错，可回炉「修参」）｜`refused`（**前置闸拒**——preconditions 拒＝终局、不回炉；与 `specs/agent-loop.md` 的「绑定闸拒＝换链回炉」是两面，绑定闸拒不落本档）；**只重跑 `retryable`**（附拒因），成功结果保留。
4. **大结果落引用**：超过阈值的原文**落 `persistence`**——**替代**旧的「渲染帽裁剪」做法。行集题交付与落引用界线（与 `specs/answering.md` 行为 12 同一规则、逐字一致）：行集题（明细行集类：问句要求明细／排名／列举全行集）全量交付为默认——引擎返回的全部数据行逐行交付、丢行＝0；非行集大结果超阈才落引用（窗口只留摘要＋稳定引用＋行数），截断与落引用必披露。阈值数值阶段 5 待定（随真机数据定），行为归属与披露义务即此定死：行集题不得因落引用而丢行。真源：`tickets/v2/V2-61-材料承载分形渲染.md`（:5——24 支一刀切截断废除、改分承载体渲染）。
5. **执行状态与是否真答上分开记**：`exec_status`（过程）与 `answered`（业务）**分别落账**，为核验与回炉提供准确输入；**`answered` 的判据＝可观察事实**——该子问题**是否拿到非空观察**（`observation.content` 非空或 `ref` 存在），**这是结构判定**；「答案对不对／好不好」归 `verification`。
6. **缺参 → 挂起等用户**：工具报缺参时该子问题 `exec_status="need_input"` 并挂起；**恢复时重取易变环境量**（等待期间可能变了的量必须重校验——真源 `docs/runtime-refactor/walk/裁决表.md` §10-B），**不重放已完成的部分**（已完成子问题不二次执行）。
7. **每次记账**：每次工具调用记**参数／回来多少行／或被拒原因**（可事后复算）。
8. **缺位回捞**：执行后如发现子问题有缺位，**按「模型给出的缺位结论」驱动回捞**——**程序不拿词面判「相不相关」**，不静默留空。（**与 `arch/P4a1`（V2-46）原口径偏离**：原口径含 `recall_relevant` 词面门；按总纪律改——真源 `walk/00-设计总纲.md` §二。）
9. **观察必带出处**：每个 `Observation` 带 `source`（台账行／片段→报告→库／表名）；缺出处＝判失败（INV-1 的输入）。
10. **失败不炸整批**：任一子问题失败不阻断其余子问题的执行与回流。
11. **发现步（discover）归本块**：本块职责含「发现」——发现步的只读工具调用与 `tool` 事件的发射同属本块（发射单元 **M5**；真源 `specs/modules.md` `## execution` 卡职责「发现、执行、观察回流」、`synth/S6-事件与帧目录.md` §一）；发现步同样只经 `tools` 公开面、同受零 LLM 约束。
12. **落引用的单一责任方**：大结果落引用**由本块（`execution`）落**、`persistence` 为**引用载体**；`answering`（作答块）**只消费引用、不重复落**（真源 `docs/runtime-refactor/walk/裁决表.md` §14-B「与 §13-B 合并」）。
13. **空手探查记指纹＋同参空手重发发射级拒**：探查空手（工具失败／`refused`／重试耗尽，或成功但本次新增非 notice 观察为 0）→ 记**同参指纹**（判定键＝工具名＋参数逐字 JSON——参数改了＝新尝试，门开着）；同参空手重发在**发射级整发射拒**（不执行工具、不占探查预算）；**首拒免轮、第 2 次起占轮**。真源：`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`（:26-28——A-P4b-04 空手记录纪律／A-P4b-05 同参判定键／A-P4b-06 发射级拒）。

## 不降级与静默禁令

- **合法降级路径：无**（本模块不自降级）。
- 大结果落引用、失败、缺参**都必须产生机读信号**：`observation`／`tool` 事件 ＋ step payload 的 `row_count`／`ref.handle`／`error.reason` 字段。
- 被落引用的原文**不得静默丢弃**：引用必须可寻址（`handle` 可读回）；红线原文 `arch/P7a-交接包与挂账清单.md`（A-P7a-37）「不许静默」。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 只读子问题并行执行；观察编号按定序分配（两次运行同序） | `tests/domains/test_v2_execution.py::parallel_and_stable_seq` |
| 已成功子问题不重发工具调用（指纹命中） | `tests/domains/test_v2_execution.py::success_not_rerun` |
| 失败分类（`retryable`／`bad_args`／`refused`）→ **只重跑 `retryable`**；`refused`（前置闸拒）终局不回炉 | `tests/domains/test_v2_execution.py::failure_classified_retry_subset_only` |
| 行集类结果不落引用（全量行随观察交付，丢行=0）；非行集大结果落引用：窗口只留摘要＋引用＋行数（不留全文） | `tests/domains/test_v2_execution.py::big_result_ref_only` |
| 引用可寻址（handle 能读回原文） | `tests/domains/test_v2_execution.py::material_ref_addressable` |
| `exec_status="ok"` 但 `answered=False` 时如实分开记 | `tests/domains/test_v2_execution.py::exec_status_vs_answered_separated` |
| 缺参 → `need_input` ＋ 挂起；恢复时重取易变环境量、不重放已完成部分 | `tests/domains/test_v2_execution.py::need_input_suspend_resume_guard` |
| `exec_status`／`category` 越界取值 → 判失败 | `tests/domains/test_v2_execution.py::enums_closed_world` |
| 程序侧无词表／正则语义判断（AST 扫描本模块；**豁免面＝形态处理／集合成员判定**——不算语义词表／正则） | `tests/domains/test_v2_execution.py::no_lexicon_or_regex_in_execution` |
| 发现步（discover）由本块发起只读调用并发射 `tool` 事件（发射单元 M5） | `tests/domains/test_v2_execution.py::discover_tool_event_emitted` |
| 大结果落引用只经 `persistence` 公开面（无直连符号：对象存储客户端／裸 DB driver） | `tests/domains/test_v2_execution.py::no_direct_storage_symbols` |
| 观察缺出处 → 判失败 | `tests/domains/test_v2_execution.py::observation_requires_source` |
| 单子问题失败不阻断其余（不炸整批） | `tests/domains/test_v2_execution.py::one_failure_does_not_abort_batch` |
| 每次记账字段齐（参数／行数／拒因） | `tests/domains/test_v2_execution.py::per_call_accounting` |
| 同参空手重发 → 发射级拒（不执行工具、不占探查预算）；首拒免轮、第 2 次起占轮；异参不拒（门开着） | `tests/domains/test_v2_execution.py::empty_probe_fingerprint_emission_reject` |
| 机读信号在场（落引用／失败／缺参） | `tests/domains/test_v2_execution.py::execution_signal_present` |
| 【边界集】空结果／超大结果／限流失败／缺参 → 各自落到对应分支 | `tests/domains/test_v2_execution.py::boundary_empty_huge_ratelimit_needinput` |
| 【保留集】全成功时无额外信号、无回炉行为不变 | `tests/domains/test_v2_execution.py::retention_all_ok_unchanged` |

## 依赖与风险

- 依赖：`tools`（公开面）、`state`（状态形状）、`transport`（事件）、`persistence`（大结果引用落盘）。
- 风险与对策：
  1. **并行引入不确定顺序** → 观察编号／记账错乱。对策：编号按子问题定序分配、与执行完成顺序解耦；检测手段＝测试 `parallel_and_stable_seq`。
  2. **大结果引用不可寻址**（写了找不回）→ 等于静默丢材料。对策：`handle` 可读回并纳入验收；检测手段＝`material_ref_addressable`。
  3. **`answered` 被当成 `exec_status` 用** → 核验与回炉输入失真。对策：两者分列字段、分别落账；检测手段＝`exec_status_vs_answered_separated`。
  4. **绕过 `tools` 直引引擎** → 违边界。对策：检测手段＝**R6 契约**（已真跑）。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 只经 `tools` 公开面接触世界 | 边界闸 **R6** | 已真跑 |
| 不直接 import `langgraph`／`langchain` | 边界闸 **R5b** | 已真跑 |
| 零 LLM 面（本块不调模型、不存在发起面；不引 `gateway_adapter`） | 边界闸 **R8**（零 LLM 面） | 已真跑 |
| 程序不判语义（无词表／正则） | 测试 `::no_lexicon_or_regex_in_execution` | 待实现（阶段 5） |
| 大结果落引用只经 `persistence` 公开面 | 无边界闸 → AST 断言 `::no_direct_storage_symbols` | 待实现（阶段 5）；原因：R1–R8 未覆盖此面 |
| 大结果不留全文（只留摘要＋引用＋行数） | 测试 `::big_result_ref_only` | 待实现（阶段 5） |
| 引用可寻址 | 测试 `::material_ref_addressable` | 待实现 |
| 执行状态与是否真答上分开 | 测试 `::exec_status_vs_answered_separated` | 待实现 |
| 机读信号在场（落引用／失败／缺参） | 测试 `::execution_signal_present` | 待实现 |
| 空手探查记指纹＋同参空手重发发射级拒（首拒免轮、第 2 次起占轮；不执行工具、不占探查预算） | 钉 **`pin-06`**（P1） | 待织网（阶段 5） |
| 软失败域闸换链回炉恰 1 次为界——**承接在 `specs/preconditions.md` 行为 7**，本块提供回炉触发面 | 钉 **`pin-16`**（P1） | 待织网（阶段 5；钉本体＝preconditions 侧 `::rewire_once_then_refuse`） |
| 「不做什么」的纯范围排除（不选工具／不作答等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（相位互不 import、只经 tools）已由边界闸 R1／R6 覆盖 |
