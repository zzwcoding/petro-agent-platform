# V2 澄清（clarification）

状态: 已定稿
来源: `specs/modules.md` `clarification` 卡、`docs/runtime-refactor/walk/08-澄清-意图澄清.md`、`walk/09-澄清-分解问题.md`、`walk/10-澄清-澄清反问挂起.md`、`walk/06-过程图-循环挂起判断.md`、`walk/裁决表.md` §06/§08/§09/§10 ＋项目级裁决 #13、`docs/runtime-refactor/arch/P4b-票堆V2-56至65.md`（回工补写：pin-05 finalize 合法性闸＋pin-07 打回三段带路）
版式: `docs/spec-format.md`（节标题按该文 §二之二 逐字命名）

## 目标

把读题结论变成**可执行的子问题清单**——中间该探的探、该问的问；**四动作（查资料／拆题／反问／定案）由模型定，程序只做闭世界对账**。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 入口安全阀（注入／外发／写意图） | `gate` | `specs/modules.md` `## gate` |
| 废弃口径的**判断**（提及 vs 执行） | `tool_matching`（模型产出） | `walk/裁决表.md` #12 |
| 废弃口径结论的**分派**（放行／拒答） | `preconditions`（判定序第 1 位，机械分派） | `walk/裁决表.md` #12 |
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
| bookkeeping | 新增依赖 | 模型调用发起面：经 bookkeeping.call_model（单点发起），本块不直引 gateway_adapter |
| gateway_adapter | 新增 | 模型出口（唯一出口仍归它）；本块不直引——经 bookkeeping.call_model 发起 |
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
    subtasks: list[Subtask]                         # 条数上限引限额真源双指（真源 recon/K-上下文事件指南预算.md R-K-72…R-K-78 逐键 ＋ walk/裁决表.md §06-A 循环上限五项；条数键两源未单列，数值真源 walk/09-澄清-分解问题.md §七 Q-C；本规格不复制字面值）
class Subtask:
    id: str
    question: str
    ledger_notes: str                               # 必填非空；三段槽位对账形 `槽位｜绑定态｜窗`（行为 8；流水 64）
    chain: Literal["data", "knowledge"]             # 闭世界
class ClarifyRejection:                             # 拒因回喂用（非终局）
    reasons: list[ClarifyReason]                    # 结构化：动作越界／条数越界／注释为空／注释槽位对账不过／chain 越界／零实质观察禁定稿
class ClarifyReason:                                # 结构化拒因单条
    ...
```

- **四动作闭世界**：`discover`｜`decompose`｜`ask`｜`finalize`；**越界值判失败**（不猜、不取默认）。
- **`guide_text` 注入注（2026-10-16 裁·流水 63）**：签名补注入形参 `*, guide_text: str = ""`——§A 指南文本经编排注入（快照）；缺省空串＝空段头（本块只下传、不读文件；装配面归 api 组合根）。
- **`discover` 出口由 `orchestration` 承接（本块不返回）**：`discover` 不在本块内直调工具，而是**以 `next_intent="discover"` 的信道交出**、由 `orchestration` 路由到发现步执行，结果回到本相位（真源 `docs/runtime-refactor/recon/E1-澄清节点.md`「本段零工具直调」「discover→NODE_DISCOVER」）；故 `ClarifyOutcome` 的**本块返回位**＝`ClarifyAsk`｜`ClarifyFinal`｜`ClarifyRejection`（`discover` 不占返回位）。
- **`chain` 闭世界**：合法值仅 `"data"`｜`"knowledge"`。
- **错误契约**：发射不合 schema（动作越界／子问题条数越界／`ledger_notes` 为空／`ledger_notes` 槽位对账不过（槽位不在台账名录／绑定态越界／窗形不合法／段数非三）／`chain` 越界）→ **返回 `ClarifyRejection`（结构化拒因）**，由 `orchestration` **回喂模型、回到本相位重决策**（**不做自动修补**）。槽位对账不过的**拒因载荷形（逐字稿＝流水 64 裁，零模型调用）**：头行「上次发射被拒：ledger_notes 槽位对账未过：{id 列表}」＋逐子问题三行块（「【拒因】{id} 的「{段名}」段「{值}」{不过原因：不在台账名录／绑定态越界／窗形不合法}」＋「【期望形】〈台账行首名〉｜已绑定|未绑定｜〈锚定窗形：2026-09-16~2026-10-16｜检索式无窗：窗未定或 null~null〉」＋「【台账相关行】{槽位 exact-match 取到的台账整行原文；槽位不在名录＝（名录无此名——只许用台账注入块内出现的指标/对象/关系/术语名）}」）＋尾行「——修正后重新输出 JSON。」。
- **`finalize` 合法性闸（前置合规，非 schema 违例）**：判「材料足够」定案前，**窗内必须有非 notice 实质观察**（faq 命中卡／台账条目卡／检索片段；空手探查——未命中 notice／工具失败／零观察——不算数）；窗内非 notice 观察数 ＝ 0 → **返回 `ClarifyRejection`（拒因形：零实质观察禁定稿）**，同样由 `orchestration` 回喂重决策、**不得判「材料足够」直答收口**。该闸＝**纯结构判定**（数窗内非 notice 观察数，非语义判断；计数属形态处理豁免面）；真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-01「finalize 合法 ⇔ 窗内已有实质观察」；钉 `pin-05`（P0）。
- **挂起契约**：返回 `ClarifyAsk` 即进入挂起态（`pending_ask` 随检查点走）；恢复经 `orchestration` 的 `resume` 入口。
- 真源：`specs/modules.md` `## clarification` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本模块不引入任何框架）。
- **模型调用发起面＝`bookkeeping.call_model`（单点发起），禁手写替代；其内部唯一出口＝`gateway_adapter`**：本块不直引 `gateway_adapter`（import 落点＝`appv2.runtimev2.bookkeeping` 包根——R2 禁深层子模块）、不得自建模型客户端、不得绕过该发起面直连上游。对应闸：`tools/importlinter_v2.toml` 的 **R7 契约**（禁直引 `appv2.infra.llm_client`——模型出口仍唯一归 `gateway_adapter`；**B6 只管 litellm 出 `infra`，不含「绕过 `gateway_adapter` 直引」这一面**；发起面收敛为规格层 doctrine，不设闸——主窗 2026-10-15 裁）；验收写法：「无旁路」行为断言（模型调用发起点只出现在 `bookkeeping.call_model`，无自建旁路）。
- **不得直接 import `langgraph`／`langchain`**（框架只许在 `orchestration`）；对应闸：**R5b 契约**。

## 行为约定

1. **四动作由模型出结构化发射**，程序只做**闭世界 schema 对账**（动作／条数／注释／路线）。
2. **时机规则（属模型侧策略判断，程序只分派模型结论，不入程序验收面）**：时间范围能从问句确定 → **不许反问**，直接定范围——「能否从问句确定／是否需反问」的判断在模型侧产出，程序只按结论分派（含引擎缺参反问兜底）（真源 `walk/08` §一；`walk/裁决表.md` 项目级裁决 #13）。
3. **无时间词 → 默认「近 30 天」并注记**（真源 `walk/08` §七 Q-B）。
4. **口径不给默认**：口径有歧义 → **反问**，不交模型猜（真源 `walk/08` §七 Q-B）。
5. **先探后问为首选策略（属模型侧策略，不入程序验收面）**：模型先 `discover` 出候选，再带候选反问（真源 `walk/08` §七 Q-C）；**程序侧只做闭世界 schema 对账，不验收该策略**。
6. **台账全量每轮注入**（词典层小、利于前缀缓存）；**词典层变大即转按需检索**：**阈值待定、暂以全量注入为唯一现行为**（真源 `walk/08` §七 Q-A 亦未给数值）。
7. **封顶数值一律引限额真源双指**：子问题条数上限、连续反问次数上限（R-K-76）、发现次数上限（R-K-75）、返工轮次上限（R-K-72；§06-A 回炉一次）——**本规格不写字面值**（真源 `recon/K-上下文事件指南预算.md` R-K-72…R-K-78 逐键 ＋ `walk/裁决表.md` §06-A 循环上限五项；子问题条数上限两源均未单列，数值真源 `walk/09-澄清-分解问题.md` §七 Q-C）。
8. **`ledger_notes` 三段槽位对账（2026-10-16 改·流水 64，Owner 裁）**：`ledger_notes` 必填非空，形＝`槽位｜绑定态｜窗`（分隔符全角「｜」、**段位次固定**——段缺／段数非三＝判违约）。三段判据：①**槽位**＝段一，须**逐字** ∈ **台账名录**（ledger 投影的指标 slot／对象 obj／关系 rel／术语 term 名——exact membership，无语义匹配；空投影＝名录制空、fail-closed 判违约；**术语条亦台账条目行**，2026-10-16 微批随真机形补入）；②**绑定态**＝段二，∈ 闭世界 `{"已绑定", "未绑定"}`（照台账行「（绑定态：…）」中文形）；③**窗**＝段三，合法形＝窗词锚定表现算（如 `2026-09-16~2026-10-16`）或「窗未定」／同义形「无时间窗」（knowledge 链检索式问题无窗概念＝合法；两写法同为模型自发形，2026-10-16 微批收编）或双 null 发射形（窗形读法照 `appv2/tools/precondition.py`，不新造）。**拒因壳语的【期望形】窗段给两形示例**（锚定窗形：`2026-09-16~2026-10-16`｜检索式无窗：窗未定或 `null~null`——2026-10-16 补（L0/L2 三病灶修复批②）：首秀形窗段无据可依，拒因壳语是该段合法形的唯一教具面）。任一不过＝判违约：拒因回喂**指明哪一段／哪个值／为什么**＋【期望形】＋【台账相关行】（载荷形见「接口定义」错误契约；台账名**逐字转抄**——不做语义改写、不摘要；**不自动修补**）。判据＝**形态处理豁免面**（闭世界集合成员校＋日期形解析，非语义词表／正则）。
9. **覆盖校验交模型**：拆完后由**模型**自证「子问题合起来覆盖原题」；**程序只校格式，不拿词表猜覆盖**。
10. **子问题无依赖**：`Subtask` 不含依赖字段，子问题**独立并行**。
11. **反问卡合并**：同一轮里多处歧义 → **合并成一张卡**一次问清（反对逐条追问）。
12. **挂起语义**：等待**不计轮、不计时**；`resume` **重置轮预算**；用户所选**原话进对话链**（去系统前缀）。
13. **恢复时重取易变量**：恢复时对「等待期间可能变了的量」（数据水位／新鲜度／地基／落库新数据）**重取一遍**。
14. **挂起不设超时**（无限等，记录为已知选择）。
15. **到顶不环**：连续反问到上限 → **截断 ＋ 带已取得材料如实直答**（不继续环）。
16. **发射判据**：**ask 仅限两种白场**（阈值判断形口径反问／目标-对象-口径真歧义）——**属模型侧策略，由 Skill 指南承载，程序不验收、不做语义判断**（与行为 5 同款处理；真源 `CONTEXT.md`「发射判据」词条）；**台账命中且时间窗已定 → 禁再 `discover`**（机械半句，程序可验收；「时间窗已定」的判断属模型侧策略判断，程序只分派模型结论，不入程序验收面——真源 `walk/裁决表.md` 项目级裁决 #13）。
17. **`finalize` 合法性闸**：判「材料足够」直答收口的前置＝**窗内非 notice 实质观察数 ≥1**（faq 命中卡／台账条目卡／检索片段；空手探查——未命中 notice／工具失败／零观察——不算数），否则拒因「零实质观察禁定稿」回喂、**不得直答收口**；程序侧只数观察数（纯结构判定，零语义判断；计数属形态处理，在 `no_lexicon_or_regex_in_clarification` 豁免面内）（真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-01；钉 `pin-05`，P0）。
18. **`finalize` 打回三段带路**：`finalize` 被拒（打回）时，拒因载荷必带**三段拼装文本**（机器已知事实说全、**零模型调用**）——①有绑定拒／台账外形的前置判定 →「该指标材料走报告检索：分解时 chain=knowledge、tool=doc_retrieve」；②已空手探查清单 →「已空手探查：{tools}——禁再试同名同参」；③兜底句**恒在**「先 discover 取得条目（精确名单词），或 decompose 分解走 doc_retrieve 检索执行。」；段缺则跳、「；」连接成单段文本（真源 `docs/runtime-refactor/arch/P4b-票堆V2-56至65.md` A-P4b-03；钉 `pin-07`，P1）。
19. **解析拒文→结构化拒因的转换归本块（消费方）**：解析拒文（parsing 产出的 `str` 拒文）→ `ClarifyRejection` 的结构化转换归本块（消费方）：转换是机械适配（`str` 逐字进 `reason` 字段＋映射拒因枚举），零语义判断；parsing 不感知本块类型（R3）。（主窗流水 30① 裁决，2026-10-15——销 `docs/runtime-refactor/spec-review/parsing-评审.md` P-09「两头都不认」；解析本体与拒文产出归 `specs/parsing.md`，其风险 5 同步「已裁：转换在消费方」。）

## 不降级与静默禁令

- **合法降级路径：无**（本模块不自降级）。
- 截断、挂起、拒因回喂**都必须产生机读信号**：ask 帧／`pending_ask`／step payload 的拒因字段／notice（类型取自 `synth/S6-事件与帧目录.md`）。
- 到顶截断**不得静默**：必须带已取得材料交付并明示未完成项（红线原文 `arch/P7a-交接包与挂账清单.md` A-P7a-37）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 动作越界 → 判失败（不猜、不取默认） | `tests/domains/test_v2_clarification.py::emission_action_closed_world` |
| `ledger_notes` 为空 → 判失败并带拒因回喂（不自动修补） | `tests/domains/test_v2_clarification.py::ledger_notes_required_with_reject_feedback` |
| 子问题条数越界 → 判失败（上限取限额真源双指：`recon/K-上下文事件指南预算.md` R-K-72…R-K-78 ＋ `walk/裁决表.md` §06-A；条数键两源未单列，数值真源 `walk/09-澄清-分解问题.md` §七 Q-C） | `tests/domains/test_v2_clarification.py::subtask_cap_from_budget_table` |
| `chain` 越界值 → 判失败 | `tests/domains/test_v2_clarification.py::chain_enum_closed_world` |
| 零实质观察（非 notice）→ 不得判「材料足够」直答收口：`finalize` 前置＝窗内非 notice 观察数 ≥1，否则拒因「零实质观察禁定稿」回喂 | `tests/domains/test_v2_clarification.py::finalize_requires_substantive_observation` |
| `finalize` 被拒（打回）→ 拒因载荷带三段带路（前置判定指路→空手清单→兜底 discover/doc_retrieve 指引；零模型调用、段缺则跳、「；」连接） | `tests/domains/test_v2_clarification.py::finalize_rejection_three_segment_guidance` |
| 时间可确定 → 不反问，直接定范围（断的是模型结论的分派形——「能否确定」判断在模型侧（`walk/裁决表.md` 项目级裁决 #13），程序只验收分派形，不验收判断本身） | `tests/domains/test_v2_clarification.py::no_ask_when_time_resolvable` |
| 无时间词 → 默认近 30 天并带注记 | `tests/domains/test_v2_clarification.py::default_window_with_note` |
| 口径歧义 → 反问（不给默认） | `tests/domains/test_v2_clarification.py::caliber_ambiguity_asks` |
| 同轮多处歧义 → 合并成一张卡 | `tests/domains/test_v2_clarification.py::ask_card_merged` |
| 台账注入块在场且注释过**三段槽位对账**（真机 N-01 形必过；旧「注入块内逐字求得」判据必拒形） | `tests/domains/test_v2_clarification.py::ledger_notes_slot_reconciliation` |
| 挂起等待不计轮；`resume` 重置轮预算 | `tests/domains/test_v2_clarification.py::waiting_not_counted_resume_resets` |
| 恢复时重取易变量（水位／新鲜度／地基） | `tests/domains/test_v2_clarification.py::resume_reloads_volatile` |
| 到上限 → 截断＋带材料如实直答（不环） | `tests/domains/test_v2_clarification.py::ask_cap_truncate_with_material` |
| 覆盖校验由模型自证；程序不判覆盖 | `tests/domains/test_v2_clarification.py::coverage_self_proof_model_only` |
| 程序侧无词表／正则语义判断（AST 扫描本模块；**豁免面＝形态处理**——闭世界集合成员校与日期形解析不算语义词表／正则） | `tests/domains/test_v2_clarification.py::no_lexicon_or_regex_in_clarification` |
| 拒因／截断／挂起的机读信号在场（ask 帧／`pending_ask`／step payload 拒因字段／notice） | `tests/domains/test_v2_clarification.py::clarify_signal_present` |
| `discover` 经 `orchestration` 路由出去执行（本块零工具直调、不返回） | `tests/domains/test_v2_clarification.py::discover_routed_not_direct_call` |
| 台账命中且时间窗已定 → 禁再 `discover`（机械半句，断的是模型结论的分派形——「时间窗已定」判断在模型侧（`walk/裁决表.md` 项目级裁决 #13）；「两白场」属模型侧策略，程序不验收） | `tests/domains/test_v2_clarification.py::no_rediscover_when_window_set` |
| 解析拒文（parsing `str`）→ `ClarifyRejection` 结构化转换归本块（消费方）：机械适配（str 逐字进 `reason` 字段＋映射拒因枚举）、零语义判断（行为 19） | `tests/domains/test_v2_clarification.py::parse_rejection_str_to_clarify_rejection_consumer_side` |
| 【边界集】`ledger_notes` 三段槽位对账不过（槽位不在台账名录／绑定态越界／窗形不合法／段数非三）→ 判违约＋段级拒因 | `tests/domains/test_v2_clarification.py::boundary_slot_reconciliation_rejections` |
| 【保留集】非歧义问句不产生 ask；子问题独立并行行为不变 | `tests/domains/test_v2_clarification.py::retention_no_ask_no_dependency` |

> **2026-10-16 补（L0/L2 三病灶修复批②·审计）**：槽位对账拒因壳语的【期望形】窗段由「〈锚定窗或窗未定〉」改为**给具体示例**「〈锚定窗形：2026-09-16~2026-10-16｜检索式无窗：窗未定或 null~null〉」（行为 8③ ＋「接口定义」错误契约两处同步）；同批分解发射样例头行补窗词锚定说明句（模糊时间词＝窗写 `null~null`、引擎缺参反问兜底三选一、不自行锚窗，真源 `specs/prompts.md` 行为 10）。机读面＝`tests/domains/test_v2_clarification.py::boundary_slot_reconciliation_rejections`（壳语逐字断言）＋`tests/domains/test_v2_prompts.py::decompose_example_head_window_rule`。

## 依赖与风险

- 依赖：`prompts`／`parsing`（同批新增）、`bookkeeping`（模型调用发起面——`call_model` 单点发起）、`gateway_adapter`（模型出口——经 `call_model` 的内部唯一出口，本块不直引；真源 `specs/modules.md` `## gateway_adapter`）、`state`（状态形状）。
- 风险与对策：
  1. **限额数值被复制进实现** → 漂移。对策：限额数值只从真源双指读（`recon/K-上下文事件指南预算.md` R-K-72…R-K-78 逐键 ＋ `walk/裁决表.md` §06-A 循环上限五项）；检测手段＝限额常量单点测试（`state` 卡）。
  2. **覆盖校验滑成程序判** → 违总纪律。对策：判据只留在模型侧；检测手段＝AST 机检测试 `no_lexicon_or_regex_in_clarification`（**豁免面＝形态处理**：闭世界集合成员校与日期形解析不算语义词表／正则）。
  3. **恢复重取漏项**（等待期环境失效）→ 交付用旧数据。对策：明确清单（水位／新鲜度／地基／落库新数据）；检测手段＝测试 `resume_reloads_volatile`。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 不 import `langgraph`／`langchain` | 边界闸 R5b | 已真跑 |
| 模型调用经 `bookkeeping.call_model` 发起（单点发起；其内部唯一出口 `gateway_adapter`） | 边界闸 R7（出口面：禁直引 `appv2.infra.llm_client`；B6 只管 litellm 出 `infra`，不含「绕过 `gateway_adapter` 直引」面。发起面为规格层 doctrine，不设闸） | 已真跑（`tools/importlinter_v2.toml` R7 契约） |
| 程序不判语义（无词表／正则） | 测试 `::no_lexicon_or_regex_in_clarification` | 待实现（阶段 5） |
| 封顶数值不复制、只引限额真源双指（`recon/K-上下文事件指南预算.md` R-K-72…R-K-78 ＋ `walk/裁决表.md` §06-A） | 测试 `::subtask_cap_from_budget_table` ＋ `state` 侧常量单点测试 | 待实现 |
| 到顶截断不静默（带材料交付） | 测试 `::ask_cap_truncate_with_material` | 待实现 |
| 挂起不计轮／恢复重置轮预算 | 测试 `::waiting_not_counted_resume_resets` | 待实现 |
| `finalize` 合法性闸：零实质观察（非 notice）不得判「材料足够」直答收口（窗内非 notice 观察数 ≥1 才许定案——纯结构判定） | 钉 **`pin-05`**（P0）＋ 测试 `::finalize_requires_substantive_observation` | 待织网（阶段 5） |
| 连续澄清反问到顶 → 截断＋带已取得材料如实直答；挂起不计轮、恢复重置轮预算（上限值引 `recon/K-上下文事件指南预算.md` R-K-76——连续 ask 截断上限） | 钉 **`pin-15`**（P1；上限值真源＝`walk/裁决表.md` §06-A——连续澄清≤6） | 待织网（阶段 5） |
| 定稿打回理由三段带路（前置判定指路→空手清单→兜底 `doc_retrieve` 指引） | 钉 **`pin-07`**（P1；落点＝行为 18，测试 `::finalize_rejection_three_segment_guidance`） | 待织网（阶段 5） |
| 「不做什么」的纯范围排除（不查数／不选工具等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分已由边界闸 R1（相位互不 import）覆盖 |
