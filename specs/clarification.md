# V2 澄清（clarification）

状态: 已定稿
来源: `specs/modules.md` `clarification` 卡、`docs/runtime-refactor/walk/08-澄清-意图澄清.md`、`walk/09-澄清-分解问题.md`、`walk/10-澄清-澄清反问挂起.md`、`walk/06-过程图-循环挂起判断.md`、`walk/裁决表.md` §06/§08/§09/§10
版式: `docs/spec-format.md`（节标题按该文 §二之二 逐字命名）

## 目标

把读题结论变成**可执行的子问题清单**——中间该探的探、该问的问；**四动作（查资料／拆题／反问／定案）由模型定，程序只做闭世界对账**。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 入口安全闸（注入／外发／写意图、废弃口径） | `gate` | `specs/modules.md` `## gate` |
| 工具选择与闭世界对账 | `tool_matching` | `specs/modules.md` `## tool_matching` |
| 查数与检索 | `execution`（只经 `tools` 公开面） | `specs/modules.md` `## execution` |
| 模型输出的解析与 schema 校验本体 | `parsing` | `specs/modules.md` `## parsing` |
| 逐子问题过闸 | `preconditions` | `specs/modules.md` `## preconditions` |
| 挂起态落库与恢复重放 | `persistence` | `specs/modules.md` `## persistence` |
| 往上游发请求／退避／记账 | `gateway_adapter` | `specs/modules.md` `## gateway_adapter` |
| 拿词表／正则猜「要不要问」「覆盖有没有漏」 | 交模型；程序只校格式 | `walk/00-设计总纲.md` §二（总纪律） |
| 子问题之间的依赖声明与顺序执行 | **不做**（子问题独立并行） | `walk/09-澄清-分解问题.md` §七 Q-B |
| 挂起超时 | **不做**（无限等，记录为已知选择） | `walk/10-澄清-澄清反问挂起.md` §七 Q-C |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| clarification | 新增 | 四动作澄清 ＋ 反问挂起与恢复 ＋ 覆盖校验 |
| prompts | 新增 | 澄清轮指令与台账注入块（只出文本） |
| parsing | 新增 | 发射与问题组的解析、闭世界 schema 对账 |
| gateway_adapter | 新增 | 模型调用唯一出口；本 spec 只消费 |
| state | 新增 | `pending_ask`／子问题列等状态形状 |

## 接口定义

```python
def clarify(state: RunState) -> ClarifyOutcome: ...

# ClarifyOutcome = ClarifyAsk | ClarifyFinal | ClarifyRejection（单出口互斥）
class ClarifyAsk:                                   # 反问卡 → interrupt 挂起
    kind: Literal["clarify"]
    prompt: str
    options: list[str]
class ClarifyFinal:                                 # 定案 → 进下一相位
    subtasks: list[Subtask]                         # 条数上限见统一预算表（本规格不复制字面值）
class Subtask:
    id: str
    question: str
    ledger_notes: str                               # 必填非空；从台账逐字转抄
    chain: Literal["data", "knowledge"]             # 闭世界
class ClarifyRejection:                             # 拒因回喂用（非终局）
    reasons: list[ClarifyReason]                    # 结构化：动作越界／条数越界／注释为空／注释非逐字／chain 越界
class ClarifyReason:                                # 结构化拒因单条
    ...
```

- **四动作闭世界**：`discover`｜`decompose`｜`ask`｜`finalize`；**越界值判失败**（不猜、不取默认）。
- **`discover` 出口由 `orchestration` 承接（本块不返回）**：`discover` 不在本块内直调工具，而是**以 `next_intent="discover"` 的信道交出**、由 `orchestration` 路由到发现步执行，结果回到本相位（真源 `docs/runtime-refactor/recon/E1-澄清节点.md`「本段零工具直调」「discover→NODE_DISCOVER」）；故 `ClarifyOutcome` 的**本块返回位**＝`ClarifyAsk`｜`ClarifyFinal`｜`ClarifyRejection`（`discover` 不占返回位）。
- **`chain` 闭世界**：合法值仅 `"data"`｜`"knowledge"`。
- **错误契约**：发射不合 schema（动作越界／子问题条数越界／`ledger_notes` 为空／`ledger_notes` 非逐字（在台账注入块内求不得）／`chain` 越界）→ **返回 `ClarifyRejection`（结构化拒因）**，由 `orchestration` **回喂模型、回到本相位重决策**（**不做自动修补**）。
- **挂起契约**：返回 `ClarifyAsk` 即进入挂起态（`pending_ask` 随检查点走）；恢复经 `orchestration` 的 `resume` 入口。
- 真源：`specs/modules.md` `## clarification` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本模块不引入任何框架）。
- **模型调用唯一出口＝`gateway_adapter`**；对应闸：`tools/importlinter_v2.toml` 的 **R7 契约**（runtimev2 各块只经 `gateway_adapter` 调模型；**B6 只管 litellm 出 `infra`，不含「绕过 `gateway_adapter` 直引」这一面**）。
- **不得直接 import `langgraph`／`langchain`**（框架只许在 `orchestration`）；对应闸：**R5b 契约**。
- **禁手写替代**：不得自建模型客户端、不得绕过 `gateway_adapter` 直连上游。对应闸：`tools/importlinter_v2.toml` **R7 契约**（runtimev2 各块只经 `gateway_adapter` 调模型）；验收写法：「无旁路」行为断言（模型调用点只出现在 `gateway_adapter`，无自建旁路）。

## 行为约定

1. **四动作由模型出结构化发射**，程序只做**闭世界 schema 对账**（动作／条数／注释／路线）。
2. **时机规则**：时间范围能从问句确定 → **不许反问**，直接定范围（真源 `walk/08` §一）。
3. **无时间词 → 默认「近 30 天」并注记**（真源 `walk/08` §七 Q-B）。
4. **口径不给默认**：口径有歧义 → **反问**，不交模型猜（真源 `walk/08` §七 Q-B）。
5. **先探后问为首选策略（属模型侧策略，不入程序验收面）**：模型先 `discover` 出候选，再带候选反问（真源 `walk/08` §七 Q-C）；**程序侧只做闭世界 schema 对账，不验收该策略**。
6. **台账全量每轮注入**（词典层小、利于前缀缓存）；**词典层变大即转按需检索**：**阈值待定、暂以全量注入为唯一现行为**（真源 `walk/08` §七 Q-A 亦未给数值）。
7. **封顶数值一律引统一预算表**：子问题条数上限、连续反问次数上限、发现次数上限、返工轮次上限——**本规格不写字面值**（真源 `walk/裁决表.md` §06-A 统一预算表）。
8. **注释逐字抄台账**：`ledger_notes` 必填非空，内容须能在**台账注入块里逐字求得**（不做语义改写、不摘要）。
9. **覆盖校验交模型**：拆完后由**模型**自证「子问题合起来覆盖原题」；**程序只校格式，不拿词表猜覆盖**。
10. **子问题无依赖**：`Subtask` 不含依赖字段，子问题**独立并行**。
11. **反问卡合并**：同一轮里多处歧义 → **合并成一张卡**一次问清（反对逐条追问）。
12. **挂起语义**：等待**不计轮、不计时**；`resume` **重置轮预算**；用户所选**原话进对话链**（去系统前缀）。
13. **恢复时重取易变量**：恢复时对「等待期间可能变了的量」（数据水位／新鲜度／地基／落库新数据）**重取一遍**。
14. **挂起不设超时**（无限等，记录为已知选择）。
15. **到顶不环**：连续反问到上限 → **截断 ＋ 带已取得材料如实直答**（不继续环）。
16. **发射判据**：**ask 仅限两种白场**（阈值判断形口径反问／目标-对象-口径真歧义）——**属模型侧策略，由 Skill 指南承载，程序不验收、不做语义判断**（与行为 5 同款处理；真源 `CONTEXT.md`「发射判据」词条）；**台账命中且时间窗已定 → 禁再 `discover`**（机械半句，程序可验收）。

## 不降级与静默禁令

- **合法降级路径：无**（本模块不自降级）。
- 截断、挂起、拒因回喂**都必须产生机读信号**：ask 帧／`pending_ask`／step payload 的拒因字段／notice（类型取自 `synth/S6-事件与帧目录.md`）。
- 到顶截断**不得静默**：必须带已取得材料交付并明示未完成项（红线原文 `arch/P7a-交接包与挂账清单.md` A-P7a-37）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 动作越界 → 判失败（不猜、不取默认） | `tests/domains/test_v2_clarification.py::emission_action_closed_world` |
| `ledger_notes` 为空 → 判失败并带拒因回喂（不自动修补） | `tests/domains/test_v2_clarification.py::ledger_notes_required_with_reject_feedback` |
| 子问题条数越界 → 判失败（上限取统一预算表） | `tests/domains/test_v2_clarification.py::subtask_cap_from_budget_table` |
| `chain` 越界值 → 判失败 | `tests/domains/test_v2_clarification.py::chain_enum_closed_world` |
| 时间可确定 → 不反问，直接定范围 | `tests/domains/test_v2_clarification.py::no_ask_when_time_resolvable` |
| 无时间词 → 默认近 30 天并带注记 | `tests/domains/test_v2_clarification.py::default_window_with_note` |
| 口径歧义 → 反问（不给默认） | `tests/domains/test_v2_clarification.py::caliber_ambiguity_asks` |
| 同轮多处歧义 → 合并成一张卡 | `tests/domains/test_v2_clarification.py::ask_card_merged` |
| 台账注入块存在且注释可逐字求得 | `tests/domains/test_v2_clarification.py::ledger_notes_verbatim_from_injection` |
| 挂起等待不计轮；`resume` 重置轮预算 | `tests/domains/test_v2_clarification.py::waiting_not_counted_resume_resets` |
| 恢复时重取易变量（水位／新鲜度／地基） | `tests/domains/test_v2_clarification.py::resume_reloads_volatile` |
| 到上限 → 截断＋带材料如实直答（不环） | `tests/domains/test_v2_clarification.py::ask_cap_truncate_with_material` |
| 覆盖校验由模型自证；程序不判覆盖 | `tests/domains/test_v2_clarification.py::coverage_self_proof_model_only` |
| 程序侧无词表／正则语义判断（AST 扫描本模块；**豁免面＝形态处理**——逐字子串校与集合成员判定不算语义词表／正则） | `tests/domains/test_v2_clarification.py::no_lexicon_or_regex_in_clarification` |
| 拒因／截断／挂起的机读信号在场（ask 帧／`pending_ask`／step payload 拒因字段／notice） | `tests/domains/test_v2_clarification.py::clarify_signal_present` |
| `discover` 经 `orchestration` 路由出去执行（本块零工具直调、不返回） | `tests/domains/test_v2_clarification.py::discover_routed_not_direct_call` |
| 台账命中且时间窗已定 → 禁再 `discover`（机械半句；「两白场」属模型侧策略，程序不验收） | `tests/domains/test_v2_clarification.py::no_rediscover_when_window_set` |
| 【边界集】`ledger_notes` 语义改写（非逐字）→ 判违约 | `tests/domains/test_v2_clarification.py::boundary_paraphrased_notes_rejected` |
| 【保留集】非歧义问句不产生 ask；子问题独立并行行为不变 | `tests/domains/test_v2_clarification.py::retention_no_ask_no_dependency` |

## 依赖与风险

- 依赖：`prompts`／`parsing`（同批新增）、`gateway_adapter`（模型出口，真源 `specs/modules.md` `## gateway_adapter`）、`state`（状态形状）。
- 风险与对策：
  1. **预算表数值被复制进实现** → 漂移。对策：只从统一预算表读；检测手段＝限额常量单点测试（`state` 卡）。
  2. **覆盖校验滑成程序判** → 违总纪律。对策：判据只留在模型侧；检测手段＝AST 机检测试 `no_lexicon_or_regex_in_clarification`（**豁免面＝形态处理**：逐字子串校与集合成员判定不算语义词表／正则）。
  3. **恢复重取漏项**（等待期环境失效）→ 交付用旧数据。对策：明确清单（水位／新鲜度／地基／落库新数据）；检测手段＝测试 `resume_reloads_volatile`。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 不 import `langgraph`／`langchain` | 边界闸 R5b | 已真跑 |
| 模型调用只经 `gateway_adapter` | 边界闸 R7（B6 只管 litellm 出 `infra`，不含「绕过 `gateway_adapter` 直引」面） | 已真跑（`tools/importlinter_v2.toml` R7 契约） |
| 程序不判语义（无词表／正则） | 测试 `::no_lexicon_or_regex_in_clarification` | 待实现（阶段 5） |
| 封顶数值不复制、只引预算表 | 测试 `::subtask_cap_from_budget_table` ＋ `state` 侧常量单点测试 | 待实现 |
| 到顶截断不静默（带材料交付） | 测试 `::ask_cap_truncate_with_material` | 待实现 |
| 挂起不计轮／恢复重置轮预算 | 测试 `::waiting_not_counted_resume_resets` | 待实现 |
| 「不做什么」的纯范围排除（不查数／不选工具等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分已由边界闸 R1（相位互不 import）覆盖 |
