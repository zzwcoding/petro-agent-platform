- 日期：2026-10-15 ｜ 状态：**修订回执**
- 本次只改 specs/clarification.md，其它文件未动。

## 逐条回执

| 修复单编号 | 已改／未改 | 改在哪（节名＋行号） | 备注 |
|---|---|---|---|
| C-1 | 已改 | 「框架与依赖红线」第 69 行；「与闸的挂钩表」第 137 行 | 两处均由 **B6 → R7**，并注明「B6 只管 litellm 出 `infra`，不含「绕过 `gateway_adapter` 直引」这一面」；写法照 `specs/understanding.md` 同款条。挂钩表「现状」列同步为「已真跑（`tools/importlinter_v2.toml` R7 契约）」 |
| C-2 | 已改 | 「行为约定」第 79 行（行为 5） | 采用「模型侧策略」写法（三选一之一，见文末取舍）；删去含糊词「尽量」 |
| C-3 | 已改 | 「验收测试」第 116 行（新增行） | 测试标识 `tests/domains/test_v2_clarification.py::clarify_signal_present`，命名照两样板风格（同 `reporting_signal_present`／`rejection_signal_present`） |
| C-4 | 已改 | 「验收测试」第 115 行（AST 机检行） | 补「**豁免面＝形态处理**——逐字子串校与集合成员判定不算语义词表／正则」，照两样板同款写法 |
| C-5 | 已改 | 「接口定义」第 60 行（新增 bullet）；「验收测试」第 117 行（新增行） | 采用「由 `orchestration` 承接、本块不返回」写法（三选一之一）；同步补验收行 `::discover_routed_not_direct_call`。真源 `docs/runtime-refactor/recon/E1-澄清节点.md` |
| C-6 | 已改 | 「接口定义」第 62 行（错误契约） | 拒绝原因枚举补「`ledger_notes` 非逐字（在台账注入块内求不得）」，与行为 8 及「【边界集】`ledger_notes` 语义改写（非逐字）→ 判违约」行对齐 |
| C-7 | 已改 | 「不做什么」第 18 行（新增行） | 「模型输出的解析与 schema 校验本体 \| `parsing` \| `specs/modules.md` `## parsing`」，逐字照样板 |
| C-8 | 已改 | 「框架与依赖红线」第 71 行（禁手写替代） | 补闸名 **R7 契约** ＋「无旁路」行为断言；照 `specs/understanding.md` 同款 |
| C-9 | 已改 | 「行为约定」第 80 行（行为 6） | 采用「阈值待定、暂以全量注入为唯一现行为」写法（三选一之一）；未编数字，明记真源 `walk/08` §七 Q-A 亦未给数值 |
| C-10 | 已改 | 「接口定义」第 62 行（错误契约）；同节第 41 行（`ClarifyOutcome` 注释）＋第 53–55 行（新增 `ClarifyRejection`／`ClarifyReason` 类） | 统一为样板「返回结构化拒因」写法（不抛异常）＋写明回喂接缝（谁回喂＝`orchestration`；回喂到哪＝回喂模型、回到本相位重决策）；照 `specs/tool_matching.md` 同款（该样板含 `class ToolMatchRejection`／`class MatchReason`，故此处同款补类型，避免引用未定义类型） |
| C-11 | 已改 | 「行为约定」第 90 行（新增行为 16）；「验收测试」第 118 行（新增行） | 补「ask 仅限两种白场（阈值判断形口径反问／目标-对象-口径真歧义）＋台账命中且时间窗已定 → 禁再 `discover`」；真源 `CONTEXT.md`「发射判据」词条；同步验收行 `::ask_whitelist_no_rediscover` |

**计：已改 11 ／ 未改 0。**

## 改动行数

- `git diff --stat`：**18 增 ／ 8 删**（净 +9 行；文件 133 → 142 行）。
- 十节标题逐字保留、`状态: 草稿` 未动；全篇已无「尽量／合理／必要时／视情况／酌情／适当／若干」（`grep` 零命中）。

## 三处留选择的取舍（供复审核）

- **C-2（F-02）**：选「**标明属模型侧策略、不入程序验收面**」。理由：真源 `walk/08` §七 Q-C 定性为「首选策略」、`CONTEXT.md`「发射判据」明记「澄清相位的发射纪律（Skill 指南承载）」——本质是给模型的策略，程序只做闭世界 schema 对账；写成可判条件会要求程序判「口径歧义／台账已有候选」，与「四动作由模型定、程序只对账」总纪律相抵。故未走「可判条件」那条。
- **C-5（F-05）**：选「**注明由 `orchestration` 承接、本块不返回**」（未加显式出口）。理由：真源 `recon/E1` 记「本段零工具直调」「`discover`…交 `discover` 节点」，`discover` 是出去再回来的路由意图，非本块返回位；据卡签名 `-> ClarifyOutcome`（签名以卡为准，不可改）保留两返回出口，故用注明写法。
- **C-9（F-10）**：选「**明示阈值待定、暂以全量注入为唯一现行为**」（未编阈值数值）。理由：真源 `walk/08` §七 Q-A 只给「阈值纪律」未给数值，硬纪律禁自编数字。

## 发现但修复单未覆盖的问题（只记录、不处理）

1. **「依赖与风险」风险 2 的检测手段行（第 127 行）未同步豁免面**：C-4 只在「验收测试」AST 行补了「豁免面＝形态处理」，而「依赖与风险」风险 2 检测手段仍只写 `no_lexicon_or_regex_in_clarification`（对照样板 `understanding.md` 风险 2 亦含豁免面注）。修复单未覆盖此行，故未动。
2. **`specs/tool_matching.md` 仍写 B6**：评审 §五 F-01 称「L0 直接更正」`tool_matching.md` 的错挂，但该文第 74／134 行现仍为 **B6**。非本次可改文件（唯一可改＝`clarification.md`），故只记录。
3. **`ClarifyAsk.options` 基数约束未落**：`recon/E1` R-E1-10 记「ask 需 prompt＋2~4 选项（校验在解析侧）」，本规格 `options` 未给基数、亦未进错误契约（评审 §四「未验证清单」第 4 项已列）。修复单未覆盖，故未动。

## 纪律自查

- 唯一改动文件＝`specs/clarification.md`；未改其它任何文件，未在 `CONTEXT.md` 加词条。
- 未改 `状态` 行；十节标题逐字未动、未删节、未重排。
- 引用真源均已先读：`tools/importlinter_v2.toml`（R7/B6 契约）、`specs/modules.md`（R6／R7 边界规则、`## parsing` 卡、`## clarification` 卡）、`recon/E1-澄清节点.md`、`walk/08` §七、`CONTEXT.md`「发射判据」、两已定稿样板。
