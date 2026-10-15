- 日期：2026-10-15 ｜ 状态：**修订回执**
- 本次只改 specs/verification.md，其它文件未动。

## 逐条回执

| 修复单编号 | 已改／未改 | 改在哪（节名＋行号） | 备注（未改必写原因） |
|---|---|---|---|
| Y-1 | 已改 | 接口定义（`gaps: list[Gap]` 行 41、新增 `class Gap` 行 45-48、复述 bullet 行 51-53） | `GapRef` → `Gap`；逐字复述 `Gap` 字段与闭世界（`refused｜missing｜unverified`）＋注明核验侧产出 `kind="unverified"`＋写明 `RewriteRecord.reason` 与 `Gap` 两维度不强行映射 |
| Y-2 | 已改 | 接口定义（`Verdict` 类 34-41 并入 `ok`/`gaps`，删 `VerdictResult`）、错误契约 55、行为约定 9（行 76） | 合并为单一返回类型；`ok` 引用改指 `Verdict.ok`；卡签名 `-> Verdict` 未动 |
| Y-3 | 已改 | 框架与依赖红线（行 61 改述）＋与闸的挂钩表（行 125 保留 R8 行、删除原 R7 照搬行） | 硬要求＝「不调模型」、真正覆盖＝R8；R7 改述为「只禁直引 `appv2.infra.llm_client`，本块天然满足」；删去重复照搬行 |
| Y-4 | 已改 | 行为约定 2（行 69 放宽）＋验收测试节末「测试文件归属」注（行 107） | 行为 2 承接承载豁免（表格行／血缘卡／fragment，任一数值重叠即支撑）引 A2 R-A2-11；测试文件沿用新建 `test_v2_verification.py` 并注明与既有 `test_v2_agent_verify.py` 的关系 |
| Y-5 | 已改 | 依赖与风险 风险 3（行 115：「第二档」→「第三档」） | 删「第二档」笔误、统一「第三档」；`:19` 处原本即写「第三档」，无需改 |
| Y-6 | 已改 | 框架与依赖红线 禁手写替代（行 64 补 R8＋帧半面人审）＋与闸的挂钩表（行 128 新增「另一半」人审行） | 「禁手写替代」补 R8；「不自行拼 wire 帧」半面按 spec-format §五 登记「人审＋原因」（照 answering.md 同款行） |
| Y-7 | 已改 | 依赖与风险 新增风险 5（行 117） | 登记跨块待办「核验对增量引标」（承接 `walk/裁决表.md` §14-A 真流式），随 `answering` 真流式协同定稿 |

**计数**：7 条全部**已改**（0 未改）。

## 改动行数

- 文件未入 git 索引（`git status` 显示 `??`），以下由逐处改动统计：
- **增 34 行 ／ 删 27 行（净 +7）**，全文 125 行 → 132 行。
- 十节标题逐字保留、顺序不变；`状态: 草稿` 未动。

## 两道闸实跑输出（2026-10-15）

- `uv run python tools/ref_resolvable.py check` → **绿**：`真源引用可解析闸绿：13 份规格的真源引用与边界规则编号均可解析。`（exit 0）
- `uv run python tools/check_specs.py` → **spec gate: PASS（0 警告）**（exit 0）

## 发现但修复单未覆盖的问题（只记录，未处理）

1. 修复单 Y-1／Y-4 给出的真源路径 `docs/runtime-refactor/recon/A2-核验规则族.md` **不存在**；实际文件为 `docs/runtime-refactor/recon/A2-核验规则与归属审.md`（评审 §二 V-4 证据亦指向后者）。已按真实文件落笔。
2. A2 真源 R-A2-11 原文含「**R9** 反例不回退」，但 `R9` 不是已声明的边界规则编号（`specs/modules.md` 边界规则表＋`tools/importlinter_v2.toml` 均无 R9）；首稿照抄使 `ref_resolvable` 闸红，已改写为「零重叠不回退」去掉裸 `R9`。
3. 与闸的挂钩表原 R8 行标签「零 LLM 面（不引模型面）」随红线改述统一为「（不调模型）」——属 V-3 改述的连带对齐，供复审核。
4. 行为约定 6「`Verdict` 五键」、确定性 bullet「五个计数与 `ok`」、保留集行「`ok=True`」仍用旧措辞：因 `ok`/`gaps` 已并入 `Verdict`，这些措辞与修复单不冲突、不在修复单覆盖范围，未动。

## Y-1／Y-4 取舍（供复审核）

- **Y-1**：选「**复用 `answering` 的 `Gap`**」写法——接口新增 `class Gap` 逐字复述（`kind`／`subtask_id`／`reason`，闭世界 `refused｜missing｜unverified`），bullet 注明核验侧产出 `kind="unverified"`，并写明 `RewriteRecord.reason`（`no_material`｜`conflict`）与 `Gap` 是两维度、不做一一映射。未另立 `GapRef`；与卡签名 `-> Verdict` 相容，**不需回阶段 2 改卡**。
- **Y-4**：行为 2 采「**放宽到承接承载豁免**」写法（表格行／血缘卡／fragment 任一数值重叠即支撑、零重叠照改，引 A2 R-A2-11）；测试文件采「**新建 `test_v2_verification.py` ＋ 注明与既有 `test_v2_agent_verify.py` 的关系**」写法（未改为对齐既有文件）。
