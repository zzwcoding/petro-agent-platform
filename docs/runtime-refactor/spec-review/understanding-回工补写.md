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
