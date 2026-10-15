- 日期：2026-10-15 ｜ 状态：**修订回执**
- 本次只改 specs/execution.md，其它文件未动。

> 依据：`specs/execution.md` 原文 ＋ `docs/runtime-refactor/spec-review/execution-评审.md` §二／§五（修复单 E-1…E-10）。
> 落笔前已读真源：`specs/modules.md`（`## execution`／`## tools`／`## persistence` 卡、边界规则 R8）、`tools/importlinter_v2.toml`（R8 契约 source 含 `execution`）、`docs/runtime-refactor/walk/裁决表.md` §06-A／§13-B／§14-B、`synth/S6` §一（`tool` 事件发射单元 M5）、`docs/spec-format.md` §五、四份定稿样板。

## 逐条回执

| 修复单编号 | 已改／未改 | 改在哪（节名＋行号） | 备注（未改必写原因） |
|---|---|---|---|
| E-1（F-01） | 未改 | — | 签名已与卡逐字一致：`## 接口定义` 第 36 行 `def execute(state: RunState) -> ExecutionOutcome: ...` ＝ `specs/modules.md` `## execution` 卡公开接口（签名行）；两形（`ExecutionOutcome`／`SubtaskExec`）已在接口块以类定义点出。全篇无「与卡打架的自述」——原被指认的 `## 接口定义` 第 65 行「（签名以卡为准）」现与卡一致（卡片已由阶段 2 改为同一签名），不再打架，故无正文可删改。（签名项已由阶段 2 改卡达成，规格侧无需再动） |
| E-2（F-02） | 已改 | `## 不做什么` 第 21 行；`## 行为约定` 第 5 条 第 82 行 | 第 21 行改写：`answered` 由本块按**可观察事实**（该子问题**是否拿到非空观察**）产出——**结构判定**；「答案对不对／好不好」归 `verification`。行为 5 同步写明判据（`observation.content` 非空或 `ref` 存在）。 |
| E-3（F-03） | 已改 | `## 行为约定` 第 4 条 第 81 行 | 删「阈值引统一预算表（真源 `walk/裁决表.md` §06-A）」；改为「**阈值待定**：阶段 5 实现时随真机数据定；本规格只写机制（超阈即落引用）」。已核 §06-A 仅循环上限、无此阈值。 |
| E-4（F-05） | 已改 | `## 框架与依赖红线` 第 71 行；`## 与闸的挂钩表` 第 136 行 | 红线补一行：`execution` 属零 LLM 面，不得引 `appv2.runtimev2.gateway_adapter`，对应闸 **R8 契约**（source 覆盖 `preconditions`／`verification`／`execution`，已核 `tools/importlinter_v2.toml` 第 120–123 行）；挂钩表补 R8 行。 |
| E-5（F-06） | 已改 | `## 接口定义` 第 45／49 行；`## 行为约定` 第 3 条 第 80 行；`## 验收测试` 第 103 行 | 错误分类补一档：`category` 闭世界扩为 `retryable`／`fatal`／`refused`（与 `## tools` 卡「可重试｜修参｜拒答」对齐）；`refused`＝闸拒＝**终局、不回炉**。行为 3 改「只重跑 `retryable`」。验收行改写为三档＋只重跑 `retryable`＋`refused` 终局。 |
| E-6（F-07） | 已改 | `## 行为约定` 第 8 条 第 85 行 | 回捞改按「模型给出的缺位结论」驱动，**程序不拿词面判「相不相关」**；并注明与 `arch/P4a1`（V2-46）原口径（`recall_relevant` 词面门）**偏离**，按总纪律（`walk/00` §二）改。 |
| E-7（F-08） | 已改 | `## 行为约定` 第 11 条 第 88 行；`## 验收测试` 第 110 行 | 补「发现（discover）归本块」条目（经 `tools` 公开面只读调用、`tool` 事件发射单元 **M5**；真源卡职责＋`synth/S6` §一）＋对应验收行。 |
| E-8（F-09） | 已改 | `## 验收测试` 第 109 行；`## 与闸的挂钩表` 第 137 行 | 补 AST 机检行 `::no_lexicon_or_regex_in_execution`（豁免面＝形态处理／集合成员判定，不算语义词表／正则），句式照样板；挂钩表同步补一行（依 F-09 原建议「＋挂钩表一行」）。 |
| E-9（F-10） | 已改 | `## 框架与依赖红线` 第 73 行；`## 验收测试` 第 111 行；`## 与闸的挂钩表` 第 138 行 | `tools/importlinter_v2.toml` R1–R8 确无「直连对象存储／自写库」契约 → 按 `docs/spec-format.md` §五**降维为 AST 断言「不许出现直连符号」**（`::no_direct_storage_symbols`）并写明原因；验收／挂钩表各补一行。 |
| E-10（F-11） | 已改 | `## 行为约定` 第 12 条 第 89 行 | 补明落引用单一责任方：**`execution` 落、`persistence` 为载体**；`answering` **只消费引用、不重复落**（真源 `walk/裁决表.md` §14-B「与 §13-B 合并」）。 |

## 收尾

- **改动行数**：新增 **9** 行、删除 **0** 行（另**原地改写 8 行**）。十个节标题逐字保留、`状态: 草稿` 未动；spec gate 本地实跑 `uv run python tools/check_specs.py` ＝ **PASS（0 警告）**。
- **E-5 的写法选择**：选「**扩充 `category` 闭世界为三档**」——保留 `retryable`／`fatal` 并**补 `refused`**（闸拒＝终局、不回炉），与 `## tools` 卡「可重试｜修参｜拒答」对齐；**未另设字段**（`fatal` 对应「修参」、`refused` 对应「拒答」，已在字段注释写明）。
- **E-9 的写法选择**：选「**降维 AST 断言**」——核实 `tools/importlinter_v2.toml` 的 R1–R8 无「直连对象存储／自写库」契约（R2 只禁公共层**深层子模块**），故按 `docs/spec-format.md` §五降维为「**不许出现直连符号**」AST 断言（`::no_direct_storage_symbols`）**并写明原因**，未虚构闸名。
- **发现但修复单未覆盖的问题（只记录、不处理）**：
  1. `## tools` 卡三档名为「可重试｜修参｜拒答」，而 `execution` 卡 `SubtaskExec.error` 未细分；本规格二档名沿用 `fatal`（非「修参」），与卡术语不逐字对齐（E-5 只要求「补一档」，未要求改名，故未动；留待复核/卡侧）。
  2. `synth/S1` 表 A（E1→M2 澄清）与 M5 含「发现」并存，「发现」最终归块在仓内仍未钉死（即 F-08 的未验证项）；本规格按 `## execution` 卡职责与 `synth/S6` M5 落为 `execution` 职责，未回溯校正 S1。
  3. E-2 改写后的 `## 不做什么` 行新增了锚点 `specs/modules.md` `## verification`（原行仅有 `walk/00` §二）；此为把「由谁承担」补全所致，若视为越出修复单范围请复核。
