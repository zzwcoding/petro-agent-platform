# prompts 规格评审（独立评审代理用）

- 日期：2026-10-15 ｜ 状态：**框架已建，发现清单待填（本文件由起草方留空，评审代理填）**
- 被评对象：`specs/prompts.md`（起草稿——十节版式，真源 `docs/spec-format.md`）
- 评审工序：起草 → **独立评审** → 逐条处置（L0 必须清零）→ 修订 → 复审 → 定稿（真源 `docs/runtime-refactor/规划.md` §三 工序纪律六步）
- 评审人纪律：全新上下文、只产发现不改任何现存文件；每条发现带证据锚点＋建议处置；**L0 清零前 `specs/prompts.md` 不得定稿**。

## 评审基准（只读参考）

- 版式与三判据：`docs/spec-format.md` §二（十节硬要求）／§二之二（节标题逐字）／§三（可判真伪／数字单点／闸在前面）
- 块真源：`specs/modules.md` `## prompts` 卡（职责／公开接口／依赖／Seam／测试计划）；`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md` §三 B
- 归责尺子：`docs/runtime-refactor/walk/判断归责表.md`——prompts 是「只出文本」块，**重点扫「装配滑成程序语义判断」**
- 行为真源抽查面：`docs/runtime-refactor/walk/08-澄清-意图澄清.md`、`walk/09-澄清-分解问题.md`、`walk/14-作答-汇总作答.md`、`walk/裁决表.md`（§04／§06／§14、项目级裁决 #12/#13）、`recon/L2a-装配前半.md`、`recon/L2b-作答装配与回声.md`、`recon/E2-工具匹配节点.md`、`recon/I2b-RunState全字段.md`、`arch/P4b-票堆V2-56至65.md`（V2-58／59／62）、`arch/P6b-票堆V2-80系列后半.md`（A-P6b-25）、`eng/04a-应钉行为清单.md`（pin-03／pin-13／pin-24）
- 已定稿消费方对账：`specs/understanding.md`、`specs/clarification.md`、`specs/tool_matching.md`、`specs/answering.md`、`specs/verification.md`（挂钩表 pin-03 承接登记）、`specs/state.md`（行为 5＝pin-24 记账面）
- 双闸（评审人本地复跑）：`uv run python tools/check_specs.py`；`uv run python tools/ref_resolvable.py check`

## 重点核对项（起草方自评风险，供优先看）

1. **接口定义的「装配函数族成员展开」是否构成卡与规格分叉**——卡面公开接口只列 `assemble_task_book`／`assemble_answer_prompt` 两函数＋「合同常量＋各轮装配函数」注释，本规格把族成员展开成闭世界名单（前科参照：`docs/runtime-refactor/spec-review/state-评审.md` S-2 判 L0）。
2. **台账常驻块交界**——`specs/clarification.md` 触及面把「台账注入块」记在 prompts、`specs/modules.md` `## context` 卡有「术语表常驻注入」：本规格行为 7/8 与风险 3 的定界是否自洽、是否须回阶段 2 改卡。
3. **R3 半覆盖**——`tools/importlinter_v2.toml` R3 的 forbidden 只列七业务相位，「禁引公共层其余块」半面以 AST 测试补位＋人审：降维是否充分、表述是否诚实。
4. **「7 条答案要求」唯一真源指向闭环**——本规格行为 2 逐字稿 ↔ `specs/answering.md` 行为 10（以 prompts 合同为唯一真源）↔ `recon/L2b` R-L2b-02 三方是否一致、V2-64 拓宽形是否漏带。
5. **pin-13／pin-24 分工注记**——与 `eng/04a-应钉行为清单.md` 原文、`specs/answering.md` 行为 14、`specs/state.md` 行为 5 的分工是否「两头都认／两头都不认」（state-评审 §一 第 6 条的判法）。
6. **数字/枚举单点**——全规格每个数字（7 条／三则／两形／六族等）是否都有真源锚、无裸字面值。

## 待填：评审发现清单

> 填表纪律：编号 P-01 起；严重度取 L0／高／中／低；「发现」一句话说清病灶；「证据锚点」给 file:line 或实跑输出；「建议处置」给可执行动作。

| 编号 | 严重度 | 发现 | 证据锚点 | 建议处置 |
|---|---|---|---|---|
|  |  |  |  |  |
