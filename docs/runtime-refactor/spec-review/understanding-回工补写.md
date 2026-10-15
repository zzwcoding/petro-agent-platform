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
