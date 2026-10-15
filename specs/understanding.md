# V2 读题（understanding）

状态: 已定稿
来源: `specs/modules.md` `understanding` 卡、`docs/runtime-refactor/walk/04-理解-读题步.md`、`walk/05-理解-定路由.md`、`walk/07-理解段重估.md`、`walk/裁决表.md` §04/§07/项目级裁决 11
版式: `docs/spec-format.md`（本仓规格写作纪律；节标题按该文 §二之二 逐字命名）
术语: 「读题结论（Understanding）」「指标名录 / 结构卡集合」已立 `CONTEXT.md` 词条（2026-10-15）

## 目标

把一句用户问话变成**结构化的读题结论**，并定下这一轮走完整流程还是直接作答——**语义判断交模型，程序只按结论机械分派**。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 入口安全闸（注入／外发／写意图、废弃口径） | `gate` | `specs/modules.md` `## gate`；`walk/07-理解段重估.md` §一/§二 |
| 澄清与反问 | `clarification` | `specs/modules.md` `## clarification` |
| 工具选择与闭世界对账 | `tool_matching` | `specs/modules.md` `## tool_matching` |
| 查数与检索 | `execution`（只经 `tools` 公开面） | `specs/modules.md` `## execution` |
| 模型输出的解析与 schema 校验本体 | `parsing` | `specs/modules.md` `## parsing` |
| 往上游发请求／退避／记账 | `gateway_adapter` | `specs/modules.md` `## gateway_adapter` |
| 旧的「两行式」文本契约 | 由本规格的统一 JSON 契约取代（下游三消费面一并重写） | `walk/裁决表.md` §04-B |
| 替模型判断「这句话什么意思」 | 交模型；程序只按 `route` 分派 | `walk/00-设计总纲.md` §二（总纪律） |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| understanding | 新增 | 任务书装配 ＋ 模型读题 ＋ 解析 ＋ 定路由 |
| prompts | 新增 | 任务书三区的合同文本与装配函数 |
| parsing | 新增 | 统一 JSON 的解析与 schema 校验 |
| gate | 新增 | 入口两道闸；本 spec 只消费其结论 |
| gateway_adapter | 新增 | 模型调用唯一出口；本 spec 只消费 |
| state | 新增 | 状态形状；本 spec 只消费 |
| tools | 新增 | 结构卡与名录面；本 spec 只消费其公开面 |

## 接口定义

```python
def interpret(state: RunState) -> Understanding | Direct: ...

class Understanding:                       # route 闭世界
    text: str                              # 读题结论原文
    metric_candidates: list[str]           # 候选指标（须出自指标名录）
    route: Literal["full"]                 # 定型常量："full"（不设类定义默认值——缺必填字段即抛 UnderstandingParseError）

class Direct:                              # route 闭世界
    text: str
    route: Literal["direct"]               # 定型常量："direct"（不设类定义默认值——缺必填字段即抛 UnderstandingParseError）
```

- **`route` 是闭世界**：合法值仅 `"full"`｜`"direct"`；**越界值判失败**（不猜、不取默认）。
- **错误契约**：应答不是合法 JSON／缺必填字段／字段类型不符 → **抛 `UnderstandingParseError`**（携带原始应答片段供留痕）。**不返回半成品**。
- **直答退回不抛错**：结构核验不合格（见「行为约定」第 5 条）→ 返回 `route="full"` 的 `Understanding`，并在过程档案记一条「直答退回」。
- 真源：`specs/modules.md` `## understanding` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本模块不引入任何框架）。
- **模型调用唯一出口＝`gateway_adapter`**；验收写法：模型调用点只出现在该出口 ＋ 调用行为测试绿。对应闸：`tools/importlinter_v2.toml` 的 **R7 契约**（runtimev2 各块只经 `gateway_adapter` 调模型；**B6 只管 litellm 出 `infra`，不含「绕过 `gateway_adapter` 直引」这一面**）＋ 一条「无旁路」行为断言（写法照 `specs/tool_matching.md` 同款）。
- **不得直接 import `langgraph`／`langchain`**（框架只许在 `orchestration`）。对应闸：**R5b 契约**。
- **只经 `tools` 公开面**接触世界（结构卡与名录面均经它取自引擎）；对应闸：`specs/modules.md` 边界规则 **R6**（`runtimev2` 各块只经 `appv2.tools` 公开面）。
- **禁手写替代**：不得自建模型客户端、不得绕过 `gateway_adapter` 直连上游。对应闸：`tools/importlinter_v2.toml` **R7 契约**（runtimev2 各块只经 `gateway_adapter` 调模型）；验收写法：「无旁路」行为断言（模型调用点只出现在 `gateway_adapter`，无自建旁路）。

## 行为约定

1. 任务书**分三区且顺序固定**：指令区（场景／任务／红线）→ 数据区（指标名录／术语表／本体／水位）→ 输出契约区（末尾、短）。断言：装配输出的三段边界与顺序。
2. **数据区每轮从活体投影现取**，且**标来源、置于末尾**。断言：改 fixture 投影 → 输出文本随之变且带该来源标记。
3. 输出契约＝**单个 JSON 对象**（含 `route` 与读题字段）；**不使用两行式**。
4. **程序只按 `route` 分派**：给定任意 `route` 取值，程序行为只由该值决定，**不触发任何词面／正则判断**。
5. **直答结构核验（闭世界判据）**：`route="direct"` 时，若 `text` 命中下列**任一闭世界** → 判不合格 → 退回 `route="full"`：
   - **数值**：**≥1 位**连续阿拉伯数字形（含全角；**含小数、百分号、千分位分隔一并算命中**）；
   - **指标名**：属于**指标名录集合**的名字（**经 `tools` 的 `semantic_query` 工具**取得的名录／别名面——与结构卡面同路，本块不直引引擎）；
   - **表名**：属于**结构卡集合**的名字（真源：`tools` 的 `table_schema` 发现面）。
   **闭世界外的生词不算命中**——这是结构判据，不做语义猜测。
6. **单出口互斥**：一次调用只返回 `Understanding` 或 `Direct` 之一，不存在两通道同时生效。
7. **解析严格**：不合 schema → 抛 `UnderstandingParseError`；**不静默降级**（旧「抠第一个 `{...}` 降级提取」废弃）。
8. **候选须出自名录**：`metric_candidates` 出现名录外名字 → 判**违约**并如实上报（红线）。
9. 任务书**每 run 只装配一次**；**模型原话不进对话层**（只进过程档案与留痕）。
10. 样例＝**固定示例集**（多部分题／口语映射题／判断纠错题三则；真源：`walk/04-理解-读题步.md` §一「三则样例」＋`walk/裁决表.md` §04-C）；**不加边界对照例**。
11. **默认倾向 fail-closed**：理解判「可能有关／含糊／拿不准」→ 走**完整流程**；只有**确定无关**（寒暄／道谢／道别）才直答。**灰区归属**：「系统自身能力问句（我能问什么）」「预测类（明年油价）」→ 归**完整流程**（真源：`walk/05-理解-定路由.md` §七 第 3 条与灰区归属）。
12. **理解文本发 `text` 事件**（`kind=understanding`）：理解文本与指标候选**双出口**（`state` 字段 ＋ `text` 事件）；发射单元 M1（真源 `synth/S6-事件与帧目录.md` §一）。

## 不降级与静默禁令

- **合法降级路径：无**。本模块不做任何降级；模型不可用由 `orchestration` 统一处置，不在此处自降级。
- 任何「如实上报」（候选违约／解析失败／直答退回）**必须产生机读信号**：step payload 字段 ＋ notice（类型取自事件闭世界 `synth/S6-事件与帧目录.md`）。
- 红线原文：`arch/P7a-交接包与挂账清单.md`（A-P7a-37）「**不许静默**——若任何相位仍发生截断，模型面必须随材料段带明示……收口注记面同步披露」。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| route=full 时返回 Understanding，且候选全部出自名录 | `tests/domains/test_v2_understanding.py::full_route_candidates_in_roster` |
| 候选出现名录外名字 → 判违约（不静默丢弃） | `tests/domains/test_v2_understanding.py::candidate_out_of_roster_violates` |
| 寒暄句（道谢／道别）→ route=direct，文本不含数据或事实断言 | `tests/domains/test_v2_understanding.py::direct_on_greeting` |
| route=direct 但文本命中闭世界 → 不合格，退回 full | `tests/domains/test_v2_understanding.py::direct_with_assertion_rejected` |
| 应答 JSON 不合 schema → 抛 UnderstandingParseError，不静默降级 | `tests/domains/test_v2_understanding.py::malformed_json_raises_no_fallback` |
| route 越界取值 → 判失败（不猜、不取默认） | `tests/domains/test_v2_understanding.py::route_enum_closed_world` |
| 任务书三区顺序正确、数据区标来源且置于末尾 | `tests/domains/test_v2_understanding.py::task_book_three_zones` |
| 台账投影变化 → 数据区文本随之变 | `tests/domains/test_v2_understanding.py::data_zone_from_live_projection` |
| 任务书每 run 只装配一次；模型原话不进对话层 | `tests/domains/test_v2_understanding.py::assembled_once_raw_not_in_dialogue` |
| 程序只按 route 分派（换任意 route 取值都不触发词面判断） | `tests/domains/test_v2_understanding.py::dispatch_by_route_only` |
| 程序侧无词表／正则语义判断（AST 扫描本模块；**豁免面＝形态处理**——数字形判定与集合成员判定不算语义词表／正则） | `tests/domains/test_v2_understanding.py::no_lexicon_or_regex_in_understanding` |
| 「如实上报」的机读信号在场（notice ＋ step payload 字段） | `tests/domains/test_v2_understanding.py::reporting_signal_present` |
| 理解文本发 `text` 事件（kind=understanding） | `tests/domains/test_v2_understanding.py::understanding_text_event_emitted` |
| 路由默认 fail-closed：拿不准／可能有关 → 完整流程；灰区（我能问什么／预测明年油价）→ 完整流程 | `tests/domains/test_v2_understanding.py::route_defaults_fail_closed` |
| 【边界集】**名录内**指标名／**结构卡内**表名／全角数字 → 直答判不合格 | `tests/domains/test_v2_understanding.py::direct_boundary_cases_rejected` |
| 【保留集】寒暄仍走 direct；route=full 的既有候选校验行为不变 | `tests/domains/test_v2_understanding.py::retention_non_direct_unchanged` |

## 依赖与风险

- 依赖：`gate`（入口闸结论）、`prompts`／`parsing`（同批新增）、`gateway_adapter`（模型出口，真源 `specs/modules.md` `## gateway_adapter`）、`state`（状态形状，只消费）、`tools`（结构卡与名录面，只消费其公开面）。
- 声明：**身份层单一来源**（`V2-80d`）——系统提示词（`SYSTEM_PROMPT`）全文本属他模块，本块**只声明身份层单一来源**（真源 `docs/runtime-refactor/proposals/M1-理解模块修订提案.md`）。
- 风险与对策：
  1. **JSON 字段集变更牵连下游** → 对策：三消费面（**候选白名单闸／理解旁白灰条／直答通道**，真源 `walk/裁决表.md` §04-B）**同批改**；检测手段＝`understanding` 与 `parsing` 的契约测试。
  2. **第 5 条滑成语义判断** → 对策：判据锁在闭世界（数值形／名录集合／结构卡集合）；检测手段＝AST 机检测试 `no_lexicon_or_regex_in_understanding`（**豁免面＝形态处理**：数字形判定与集合成员判定不算语义词表／正则；先例 `tests/domains/test_v2_four_phase.py:446`）。
  3. **模型出口被绕过** → 对策：交付前跑边界闸；检测手段＝**R7**／R5b／B6 契约（CI 真跑）。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | **已进 CI**（本轮补挂） |
| 不 import `langgraph`／`langchain` | 边界闸 R5b | 已真跑 |
| 只经 `tools` 公开面接触世界 | 边界闸 R6 | 已真跑（`tools/importlinter_v2.toml` R6 契约；探针验证会红） |
| 模型调用只经 `gateway_adapter` | 边界闸 R7（B6 只管 litellm 出 `infra`，不含「绕过 `gateway_adapter` 直引」面） | 已真跑（`tools/importlinter_v2.toml` R7 契约） |
| 程序不判语义（无词表／正则） | 测试 `::no_lexicon_or_regex_in_understanding` | 待实现（阶段 5） |
| 直答结构核验闭世界 | 测试 `::direct_with_assertion_rejected` ＋边界集行 | 待实现 |
| 如实上报带机读信号 | 测试 `::reporting_signal_present` | 待实现 |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 「不做什么」的纯范围排除（不做澄清／查数等） | **人审** | 原因：纯范围排除没有形状／存在性／退出码判据，接不上闸；能降维的部分（相位互不 import）已由边界闸 R1 覆盖 |
