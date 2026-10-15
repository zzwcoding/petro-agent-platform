# prompts 卡补录（`specs/modules.md` `## prompts` 卡——P-07 联动注＋P-08 族名单注）

- 日期：2026-10-15 ｜ 状态：**卡面补录**（窗 B 评审产出的卡级问题清单回工——`prompts-评审.md` §二 P-07/P-08、§五 处置表、§七 复审闭合核验）
- 本次只改 `specs/modules.md` `## prompts` 卡（:366-367 注释行、:372 blockquote）＋本记录；**`## context` 卡未动**（P-07 的 context 半面＝「术语表常驻注入」改述，待其规格定稿后下一批落卡）；`specs/prompts.md` 未动。未 git commit（主窗统一提交）。

## 逐项改前改后（改后行号）

### ① 族名单注（P-08）

- **改前**（:366）：`# 合同常量 ＋ 各轮装配函数（纯文本进出）`——族名单闭世界零卡面承载（`prompts-评审.md` §七 P-08 闭合核验实证 modules.md:362 无注记）。
- **改后**（:366-367）：注释行补「——族成员名单以 `specs/prompts.md` 接口定义为准（闭世界；族名单补录 2026-10-15，P-08）」——逐字取 P-08 建议处置「卡面注释补一句『族成员名单以 prompts 规格接口定义为准（闭世界）』即可闭环」。

### ② P-07 联动注（只改 prompts 卡自己的措辞）

- **改前**：无。
- **改后**（:372）：公开接口代码块后补 blockquote 一句（体例照 bookkeeping 卡「卡级修正」blockquote 先例，modules.md:348）：「**卡级补注（2026-10-15，P-07 联动注）**：台账常驻块交界定界＝**投影取得归 `context`（经 `tools` 公开面装载进 state）；常驻块包裹与逐字转抄渲染归本块**（Manifest 记账与不入史归 context/state 面——真源 `specs/prompts.md` 行为 7／8＋风险 3）。」
- **「职责行若写『术语表常驻注入』则改述」条件核实＝不成立**：prompts 卡职责行（:361）为「指令与提示词——各相位提示词合同常量与各轮指令装配（只出文本，不做判断）」，无该措辞；「术语表常驻注入」在 `## context` 卡职责行（本批改前 :408，卡补录后顺移 :417——P-07 登记对象，本批不动）。故 P-07 落卡形＝定界注记一句，正是 P-07 处置原文的 prompts 半面：「常驻块包裹与逐字转抄渲染归 `## prompts` 卡注记一句」。
- 定界措辞对齐 `specs/prompts.md` 风险 3（:140）「本规格定界＝**固定包裹文本＋逐字转抄渲染归本块；投影取得归 context（经 tools 公开面）；Manifest 记账与不入史归 context/state 面**」。

## 疑点／登记件（交主窗）

1. P-07 的 context 半面（`## context` 卡职责行「术语表常驻注入」→「台账/名录投影取得（经 tools 公开面装载进 state）」改述）＝下一批（context 规格定稿后落卡）；`specs/prompts.md` 风险 7④ 登记态不受本批影响，销项时点仍＝阶段 7 接口契约对账。
2. 本卡「Seam 与测试」「依赖」行未动——P-07/P-08 均不触及。

## 验证（三闸，改后实跑 2026-10-15）

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                     # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：22 份规格的真源引用与边界规则编号均可解析。   # exit 0

$ uv run lint-imports --config tools/importlinter_v2.toml
R2 runtimev2 业务相位只经公共层包根（禁深层子模块） KEPT
R3 runtimev2 parsing/prompts 只许依赖 state KEPT
R5b ADR-0002 红线① 扩展：框架只许在 runtimev2.orchestration（其余 16 块禁引） KEPT
R6 runtimev2 各块只经 tools 接触引擎 KEPT
R7 runtimev2 各块只经 gateway_adapter 调模型 KEPT
R8 runtimev2 零 LLM 面：preconditions/verification/execution 不得引 gateway_adapter KEPT
Contracts: 18 kept, 0 broken.                                # exit 0
```
