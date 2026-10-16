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
| 入口安全阀（注入／外发／写意图） | `gate` | `specs/modules.md` `## gate` |
| 废弃口径的**判断**（提及 vs 执行） | `tool_matching`（模型产出） | `walk/裁决表.md` #12 |
| 废弃口径结论的**分派**（放行／拒答） | `preconditions`（判定序第 1 位，机械分派） | `walk/裁决表.md` #12 |
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
| bookkeeping | 新增依赖 | 模型调用发起面：经 bookkeeping.call_model（单点发起），本块不直引 gateway_adapter |
| gateway_adapter | 新增 | 模型出口（唯一出口仍归它）；本块不直引——经 bookkeeping.call_model 发起 |
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
- **错误契约**：应答不是合法 JSON／缺必填字段／字段类型不符 → **抛 `UnderstandingParseError`**（携带原始应答片段供留痕）。**不返回半成品**。parsing 解析不合格（`parse_understanding` 返 `None`）在场时由本块转译抛 `UnderstandingParseError`（唯一转译出口；真源 `specs/parsing.md` 行为 1／接口⑤——流水 43⑦ 补落输入半面）。
- **直答退回不抛错**：结构核验不合格（见「行为约定」第 5 条）→ 返回 `route="full"` 的 `Understanding`，并在过程档案记一条「直答退回」。
- **schema 拒回喂重试恰一次（行为 13，2026-10-16 补·流水 67）**：首读不合 schema（`UnderstandingParseError` 路径）**不当场判死**——向链尾追加**拒因载荷**（【拒因】〈具体不合项〉＋【期望形】＋尾行；不合项取 `parsing.understanding_schema_feedback` 的**唯一诊断出口**——本块不重判 schema）→ **同相位再读一次**；**仍拒**方抛 `UnderstandingParseError`（编排收 `failed` 不变）。上限**恰一次**（结构化无环）；**不静默补默认**（回喂＝修参、非降级）；两次调用各记一条步（`bookkeeping.call_model` 单点）。
- 真源：`specs/modules.md` `## understanding` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本模块不引入任何框架）。
- **模型调用发起面＝`bookkeeping.call_model`（单点发起，禁手写替代）；其内部唯一出口＝`gateway_adapter`**：本块不直引 `gateway_adapter`（import 落点＝`appv2.runtimev2.bookkeeping` 包根——R2 禁深层子模块）、不自建模型客户端、不得绕过该发起面直连上游。对应闸：`tools/importlinter_v2.toml` 的 **R7 契约**（禁直引 `appv2.infra.llm_client`——模型出口仍唯一归 `gateway_adapter`；**B6 只管 litellm 出 `infra`，不含「绕过 `gateway_adapter` 直引」这一面**；发起面收敛为规格层 doctrine，不设闸——主窗 2026-10-15 裁）；验收写法：「无旁路」行为断言（模型调用发起点只出现在 `bookkeeping.call_model`、无自建旁路；写法照 `specs/tool_matching.md` 同款）。
- **不得直接 import `langgraph`／`langchain`**（框架只许在 `orchestration`）。对应闸：**R5b 契约**。
- **只经 `tools` 公开面**接触世界（结构卡与名录面均经它取自引擎）；对应闸：`specs/modules.md` 边界规则 **R6**（`runtimev2` 各块只经 `appv2.tools` 公开面）。

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
13. **schema 拒回喂重试恰一次（2026-10-16 补·流水 67——L3 阻塞修复，真机 `run-60bc4aaa`）**：读题应答不合 schema（非合法 JSON／缺必填字段／字段类型不符／`route` 越界）→ **不直接失败**：向链尾**追加**拒因载荷 → **同相位再调模型一次**；**仍不合 schema** 才抛 `UnderstandingParseError`（编排收 `failed` 照旧）。载荷三段（体例照澄清相位拒因载荷，`specs/clarification.md` 接口定义「错误契约」）：①【拒因】＝**具体不合项**（`缺必填字段 \`metric_candidates\``／`字段类型不符：…`／`\`route\` 取值越界（闭世界仅「full」｜「direct」）`——取 `parsing.understanding_schema_feedback` 诊断出口，**本块不重判 schema**）；②【期望形】＝`{"route":"full","text":"理解：〈一句话题意〉","metric_candidates":["〈台账名录里的指标名〉"]}`（或 `{"route":"direct","text":"〈回复内容〉"}`）＋「route 只许这两个取值／`route=full` 时 `text` 与 `metric_candidates` 均为必填、无命中指标给空数组 `[]`／`route=direct` 无 `metric_candidates` 键」；③尾行「只修正不合项，其余内容照旧，重新输出一个 JSON 对象（不要输出 JSON 之外的解释文字）。」。纪律：**上限恰一次**（第二次后不再回喂——钉死防环）；**追加形**（载荷落链尾、前置内容逐字不动——`pin-22`，第二次调用的消息链＝第一次的**前缀延伸**）；载荷**自足**（链上直投、无外层壳）；角色＝`user`（系统侧指令条，同澄清面增量条体例）；只入 `messages` 与过程档案（`dialogue` 零写入——行为 9）；**回喂面零副作用**（不发 notice、不记步、不落判定字段——如实上报仍只在两读皆拒时由 `report_parse_failure` 出一份；调用记账仍归 `call_model` 单点，两次各一条）。**不静默补默认、不改写模型原话、不降级提取**。断言：①首读缺 `metric_candidates` → 回喂 → 次读合规 → 正常分派（零 `failed`）；②两读皆拒 → 抛 `UnderstandingParseError` ＋拒因留痕（链上载荷＋过程档案注记＋报告步）；③上限恰一次（模型调用恰 2 次，绝无第三次）；④载荷三段形逐字在场（【拒因】指名不合项）；⑤第二次调用的消息链前缀延伸（开门即包含第一次全链）。

## 不降级与静默禁令

- **合法降级路径：无**。本模块不做任何降级；模型不可用由 `orchestration` 统一处置，不在此处自降级。
- **拒因回喂＝修参、非降级**（行为 13）：schema 拒先回喂拒因再读一次，程序**不补默认、不改写模型原话、不降级提取**；上限恰一次，仍拒恒以 `UnderstandingParseError` 收口（不返回半成品）。
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
| schema 拒回喂重试恰一次：首读缺 `metric_candidates` → 回喂 → 次读合规 → 正常分派（零 failed，模型调用恰 2 次、两次各记一条步） | `tests/domains/test_v2_understanding.py::schema_reject_feedback_retry_once` |
| 两读皆拒 → 抛 `UnderstandingParseError`＋拒因留痕（链上载荷＋过程档案注记＋报告步）；上限恰一次（无第三次调用） | `tests/domains/test_v2_understanding.py::schema_reject_twice_raises_with_feedback_trace` |
| 拒因载荷三段带路形（【拒因】指名不合项〔缺必填字段／类型不符／route 越界〕＋【期望形】＋尾行；自足无外层壳） | `tests/domains/test_v2_understanding.py::schema_feedback_three_segment_payload` |
| 回喂＝追加形：第二次调用消息链＝第一次的**前缀延伸**（前置内容逐字不动） | `tests/domains/test_v2_understanding.py::schema_feedback_prefix_extension` |
| 端到端：理解步首拒回喂后次读合规 → 四相位正常走通（run `completed`）；两读皆拒 → run `failed` | `tests/domains/test_v2_four_phase.py::test_four_phase_understand_schema_feedback_retry_recovers` |

> **2026-10-16 补（流水 67·L3 阻塞修复·审计）**：**schema 拒回喂重试恰一次**（行为 13／接口定义「schema 拒回喂重试恰一次」条／「不降级与静默禁令」节第二句）。**病灶**：理解步 schema 拒**无任何修正回路**——整 run 直接 `failed`；真机证据 `docs/runtime-refactor/ladder/L3/04-W-11井投产后预计躺井-summary.md`（`run-60bc4aaa`：模型漏 `metric_candidates` 必填、把旧两行式塞进 `text`，首拒即死，同题 gold 期望的「优雅走到检索再拒答」连第一步都进不去），而同仓澄清相位早有打回带教面（`specs/clarification.md` 行为 17／18 拒因回喂＋三段带路）。**改法**（照澄清相位打回模式，**不静默补默认**——回喂是修参、非降级）：解析/schema 拒 → 向链尾追加**拒因载荷**（【拒因】具体不合项＋【期望形】＋尾行；具体不合项的**唯一诊断出口**＝`parsing.understanding_schema_feedback`，2026-10-16 同批新增——理解面 schema 判定仍恰一处、**本块零 schema 重判**）→ 同相位再读一次 → 仍拒才抛 `UnderstandingParseError`（编排收 `failed` 不变）；上限**恰一次**（结构化无环）；两次调用各记一条步（`call_model` 单点）；**前缀延伸不破**（载荷落链尾＝追加形，`pin-22`）；**零副作用面**（直答核验／候选名录对账／`report_parse_failure` 既有行为不变；回喂支不发 notice、不记步）。落点：`appv2/runtimev2/understanding/interpret.py`（`interpret` 重试支＋`_read_and_parse`／`_append_schema_feedback`）、`appv2/runtimev2/understanding/feedback.py`（载荷三段拼装，新增）、`appv2/runtimev2/understanding/constants.py`（载荷文案与注记标题）、`appv2/runtimev2/parsing/parsers.py`（诊断面 `understanding_schema_feedback`，与 `parse_understanding` 共用判定内核 `_understand_schema`）。**登记（交主窗）**：①`specs/parsing.md` 接口定义⑤／行为 1／验收表同批补录该新增公开成员（跨块 additive，非语义改动）；②**同一真机的旁证病灶**——任务书指令区与样例集仍是 V1「两行式」措辞（`appv2/runtimev2/prompts/constants.py` 的 `TASK_BOOK_TASK`／样例／红线），与 `【输出契约】` 的 JSON 契约**自相矛盾**（模型正是照指令区两行式答的）；该文案属 Owner 审定面、本批**无逐字稿、不动**（登记件真源＝`appv2/runtimev2/prompts/task_book.py` 模块注的既有登记），建议主窗随批裁一处统一措辞。

## 依赖与风险

- 依赖：`gate`（入口闸结论）、`prompts`／`parsing`（同批新增）、`bookkeeping`（模型调用发起面——`call_model` 单点发起）、`gateway_adapter`（模型出口——经 `call_model` 的内部唯一出口，本块不直引；真源 `specs/modules.md` `## gateway_adapter`）、`state`（状态形状，只消费）、`tools`（结构卡与名录面，只消费其公开面）。
- 声明：**身份层单一来源**（`V2-80d`）——系统提示词（`SYSTEM_PROMPT`）全文本属他模块，本块**只声明身份层单一来源**（真源 `docs/runtime-refactor/proposals/M1-理解模块修订提案.md`）。
- 风险与对策：
  1. **JSON 字段集变更牵连下游** → 对策：三消费面（**候选白名单闸／理解旁白灰条／直答通道**，真源 `walk/裁决表.md` §04-B）**同批改**；检测手段＝`understanding` 与 `parsing` 的契约测试。
  2. **第 5 条滑成语义判断** → 对策：判据锁在闭世界（数值形／名录集合／结构卡集合）；检测手段＝AST 机检测试 `no_lexicon_or_regex_in_understanding`（**豁免面＝形态处理**：数字形判定与集合成员判定不算语义词表／正则；先例 `tests/domains/test_v2_four_phase.py:446`）。
  3. **模型出口被绕过** → 对策：交付前跑边界闸；检测手段＝**R7**／R5b／B6 契约（CI 真跑）。
  4. **parsing 不合格信号的转译衔接（输入半面）**：parsing 解析不合格（`parse_understanding` 返 `None`）在场时由本块转译抛 `UnderstandingParseError`（唯一转译出口——真源 `specs/parsing.md` 行为 1／接口⑤；落笔见接口定义错误契约）；**销项登记**＝`docs/runtime-refactor/spec-review/parsing-评审.md` 风险 7⑩（P-23「understanding 回认输入半面」）随本句销项（流水 43⑦）；检测手段＝与 `specs/parsing.md` 行为 1 对读＋`::understanding_malformed_none_no_fallback`。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | **已进 CI**（本轮补挂） |
| 不 import `langgraph`／`langchain` | 边界闸 R5b | 已真跑 |
| 只经 `tools` 公开面接触世界 | 边界闸 R6 | 已真跑（`tools/importlinter_v2.toml` R6 契约；探针验证会红） |
| 模型调用经 `bookkeeping.call_model` 发起（单点发起；其内部唯一出口 `gateway_adapter`） | 边界闸 R7（出口面：禁直引 `appv2.infra.llm_client`；B6 只管 litellm 出 `infra`，不含「绕过 `gateway_adapter` 直引」面。发起面为规格层 doctrine，不设闸） | 已真跑（`tools/importlinter_v2.toml` R7 契约） |
| 程序不判语义（无词表／正则） | 测试 `::no_lexicon_or_regex_in_understanding` | 待实现（阶段 5） |
| 直答结构核验闭世界 | 测试 `::direct_with_assertion_rejected` ＋边界集行 | 待实现 |
| 如实上报带机读信号 | 测试 `::reporting_signal_present` | 待实现 |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 对话层纯度（dialogue 只装自然对话，过程记录入 process_notes 不混层） | 钉 **`pin-26`**（落点＝行为 9 模型原话不进对话层——只进过程档案与留痕） | 待织网（阶段 5） |
| 「不做什么」的纯范围排除（不做澄清／查数等） | **人审** | 原因：纯范围排除没有形状／存在性／退出码判据，接不上闸；能降维的部分（相位互不 import）已由边界闸 R1 覆盖 |
