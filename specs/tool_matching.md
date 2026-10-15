# V2 工具匹配（tool_matching）

状态: 已定稿
来源: `specs/modules.md` `tool_matching` 卡、`docs/runtime-refactor/walk/11-匹配-工具阀.md`、`walk/裁决表.md` §06/§07/§11、`specs/query.md`（`QueryPlan` 真源）、`specs/tools.md`（工具注册表真源）
版式: `docs/spec-format.md` ｜ 工序: `docs/spec-process.md`

## 目标

给每个子问题配上**恰好一个**工具／路线，并把参数校验到**可执行**——**模型提议，程序做闭世界对账**。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 入口安全闸（注入／外发／写意图、废弃口径） | `gate` | `specs/modules.md` `## gate` |
| 澄清与反问 | `clarification` | `specs/modules.md` `## clarification` |
| 逐子问题过闸（三态） | `preconditions` | `specs/modules.md` `## preconditions` |
| 真正执行工具 | `execution` | `specs/modules.md` `## execution` |
| 引擎与工具的实现 | `tools`／引擎（本块**只走其公开面**） | `specs/modules.md` `## tools` |
| 模型输出的解析与 schema 校验 | `parsing` | `specs/modules.md` `## parsing` |
| 模型调用出口 | `gateway_adapter` | `specs/modules.md` `## gateway_adapter` |
| 工具**主动发现**（检索式选工具） | **不做**（工具集小，不上重设施） | `walk/11-匹配-工具阀.md` §七 Q-C |
| 拒因回喂自环的**熔断** | **暂不加**（靠轮数闸兜底） | `walk/11-匹配-工具阀.md` §七 Q-B |
| **同参重投闸的实现** | `parsing`（发射指纹）＋ `state`（限额计数）；本块只在其发射点**被拦** | L0 裁决：`synth/S1` 表 B 同一条两处归属（M3「决策出口」／H4「指纹面」）——按架构「闸件本体归公共层、相位不实现闸」定 |
| 拿词表／正则猜「该配哪个工具」 | 交模型；程序只对账 | `walk/00-设计总纲.md` §二（总纪律） |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| tool_matching | 新增 | 提议 ＋ 闭世界对账（恰配一条） |
| parsing | 新增 | 工具匹配发射的解析（同批新增） |
| prompts | 新增 | 工具匹配轮的指令与提示词合同（只出文本）；本 spec 只消费 |
| gateway_adapter | 新增 | 模型调用唯一出口；本 spec 只消费 |
| state | 新增 | 匹配列等状态形状；本 spec 只消费 |
| tools | 改实现 | **工具描述写全**（何时用／不能做什么／参数示例）——本块只消费其公开面 |

## 接口定义

```python
def match(state: RunState) -> ToolPlan | ToolMatchRejection: ...

class ToolPlan:
    matches: list[SubtaskMatch]            # 与子问题一一对应；条数＝子问题条数

class SubtaskMatch:
    id: str                                # 必须对上某个子问题 id
    tool: str                              # 闭世界：工具注册表名单内的名字
    chain: Literal["data", "knowledge"]    # 闭世界
    plan: QueryPlan | None                 # chain == "data" 时必填
    retrieval_need: RetrievalNeed | None   # chain == "knowledge" 时必填
    caliber_key: str | None

class RetrievalNeed:
    question: str                          # 必填；逐字转抄子问题原文
    anchors: list[str]                     # 可选

class ToolMatchRejection:                  # 拒因回喂用（非终局）
    reasons: list[MatchReason]             # 结构化：缺配/多配/编号不符/必填缺/枚举越界

class MatchReason:                         # 结构化拒因单条：缺配／多配／编号不符／必填缺／枚举越界
    ...
```

- `QueryPlan` 的真源是 `specs/query.md`（**真源以该文为准**；若该文缺 `aggregate` 字段则记「待回阶段 3 补」——本块只引不复述字段）。
- **`tool` 与 `chain` 都是闭世界**：`tool` ∈ 工具注册表名单；`chain` ∈ `data`｜`knowledge`。**越界值判失败**。
- **错误契约**：**漏配／多配／编号对不上／必填缺／枚举越界** → 返回 `ToolMatchRejection`（**结构化拒因**），由 `orchestration` **回喂模型、回到本相位重配**（**不做自动修补**）。
- **`caliber_key` 本块只透传**：其归一判据归 `preconditions` 承接（本块不做 caliber 语义归一）。
- 真源：`specs/modules.md` `## tool_matching` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本模块不引入任何框架）。
- **模型调用唯一出口＝`gateway_adapter`**；对应闸：`tools/importlinter_v2.toml` 的 **B6 契约**。
- **不得直接 import `langgraph`／`langchain`**；对应闸：**R5b 契约**。
- **只经 `tools` 公开面**接触世界；对应闸：`specs/modules.md` 边界规则 R6（`runtimev2` 各块只经 `appv2.tools` 公开面）。
- **禁手写替代**：不得自建模型客户端／自建工具目录。对应闸：`tools/importlinter_v2.toml` 的 **B6 契约**；验收写法：「无旁路」行为断言（模型调用点只出现在 `gateway_adapter`、工具访问只经 `tools` 公开面，无自建旁路）。

## 行为约定

1. **模型只提议**（子问题 → 工具 ＋ 参数）；程序做**闭世界对账**，不替模型选工具。
2. **恰配一条**：每个子问题**恰好一条**匹配；**漏配／多配／编号对不上**任一 → 判失败。
3. **拒因回喂、不自动修补**：失败一律带**结构化拒因**回喂模型重配；程序不补齐、不猜。
4. **参数强校验**：`chain="data"` → `plan` 必填；`chain="knowledge"` → `retrieval_need` 必填；`metric_slot` 必填非空且**不得为英文列名形**（**形态判定**——只判形状，不判语义）；`ranking` 必填布尔且与 `direction` 同现；`caliber_key` **本块只透传**，其归一判据归 `preconditions` 承接。
5. **枚举闭世界**：`chain`（`data`｜`knowledge`）、`direction`（`asc`｜`desc`）、`tool`（注册表名单）——越界值判失败。
6. **工具描述写全**：每个工具的**载体＝`ToolDescriptor.description`**（模型选工具时看到的就是它），必须含**何时用／不能做什么／参数示例**三项（真源 `walk/11-匹配-工具阀.md` §七 Q-A）。这是选得准的**第一因**——**不加额外选型规则**。
7. **「出数只认现行口径」的结构约束落点**：`metric_slot` 到查询引擎前**只认现行名**；**模型产出归一后的名字**，本体账本只提供 alias↔canonical 的**「结构映射」**（不替模型做语义判断）（真源 `walk/裁决表.md` §12-A／§07）。
8. **不做主动发现**：不引入检索式选工具／工具主动发现设施（工具集小）。
9. **熔断暂不加**：拒因回喂自环**靠轮数闸兜底**；轮数等限额**引统一预算表**（真源 `walk/裁决表.md` §06-A），**本规格不写字面值**。
10. **名归一闸保留**：精确键未命中时按名归一扫描（真源 `walk/11-匹配-工具阀.md` §一）。

## 不降级与静默禁令

- **合法降级路径：无**（本模块不自降级）。
- 失败与拒因必须产生**机读信号**：step payload 拒因字段 ＋ notice（类型取自 `synth/S6-事件与帧目录.md`）。`caliber_key` 的归一由 `preconditions` 承担，其信号**不在本块**。
- **不得静默丢子问题**：漏配即判失败，**不许"当作已配"**或跳过该子问题（红线原文 `arch/P7a-交接包与挂账清单.md` A-P7a-37）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 子问题恰配一条；漏配 → 判失败带结构化拒因 | `tests/domains/test_v2_tool_matching.py::exactly_one_match_per_subtask` |
| 多配／编号对不上 → 判失败 | `tests/domains/test_v2_tool_matching.py::duplicate_or_unknown_id_rejected` |
| 工具名不在注册表名单 → 判失败（闭世界） | `tests/domains/test_v2_tool_matching.py::tool_name_closed_world` |
| `chain="data"` 缺 `plan` ／ `chain="knowledge"` 缺 `retrieval_need` → 判失败 | `tests/domains/test_v2_tool_matching.py::required_by_chain` |
| `metric_slot` 为空，或呈英文列名**形态**（形态判定）→ 判失败 | `tests/domains/test_v2_tool_matching.py::metric_slot_not_english_column` |
| `ranking` 与 `direction` 同现约束 | `tests/domains/test_v2_tool_matching.py::ranking_direction_paired` |
| 旧名经账本归一后才出数（出数只认现行口径） | `tests/domains/test_v2_tool_matching.py::legacy_name_normalized_before_query` |
| 每个工具描述含「何时用／不能做什么／参数示例」三项（**经 tools seam 测**；本块只消费其公开面） | `tests/domains/test_v2_tool_matching.py::descriptor_covers_three_parts` |
| 程序只对账、不替模型选工具（AST 扫描本模块；**豁免面＝结构归一／形态处理**，如去装饰符号、token 包含匹配，**不算语义词表**） | `tests/domains/test_v2_tool_matching.py::no_lexicon_or_regex_in_tool_matching` |
| 失败与拒因的机读信号在场（step payload ＋ notice） | `tests/domains/test_v2_tool_matching.py::rejection_signal_present` |
| 【边界集】`chain`／`direction` 越界取值 → 判失败 | `tests/domains/test_v2_tool_matching.py::boundary_enum_out_of_range` |
| 【保留集】名归一闸行为不变（本块） | `tests/domains/test_v2_tool_matching.py::retention_normalize` |
| 【保留集】聚合下推行为不变（归属 `execution`） | `tests/domains/test_v2_tool_matching.py::retention_pushdown` |

## 依赖与风险

- 依赖：`parsing`（发射解析）、`prompts`（本相位指令与合同）、`gateway_adapter`（模型出口）、`state`（状态形状）、`tools`（公开面＋描述文本）。
- 风险与对策：
  1. **参数校验与 `query` 卡的 `QueryPlan` 真源漂移** → 两处规则不一致。对策：`QueryPlan` 只引用不复制；检测手段＝与 `specs/query.md` 的字段对照测试。
  2. **工具描述写全落在 `tools` 侧**（本块唯一涉及 runtimev2 之外文件的地方）。对策：改动限于描述文本，不动 `tools` 公开接口签名；检测手段＝`tools` 卡公开接口对账（阶段 7 体检）。
  3. **对账滑成"程序替模型选工具"** → 违总纪律。对策：程序只做存在性/一致性/枚举三类结构判定；检测手段＝AST 机检 `no_lexicon_or_regex_in_tool_matching`。
  4. **同参重投闸归属**（原评审 F-11）：`synth/S1` 表 B 给了两个面（M3 决策出口／H4 指纹面）——**L0 裁决：闸件本体归 `parsing`（指纹）＋ `state`（限额），本块只被拦、不实现**；检测手段＝`parsing`／`state` 各自测试（不在本块验收表）。
  5. **工具描述三件套与 `specs/tools.md` 的对齐**（原评审 F-03）→ **Owner 2026-10-15 已裁「要」**：`specs/tools.md` 行为 6 已同步补三件套（`descriptors()` 的 `description` 含何时用／不能做什么／参数示例），本规格不再挂待办；检测手段＝`tests/domains/test_v2_tools.py::descriptor_covers_three_parts`。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 只经 `tools` 公开面接触世界 | 边界闸 R6 | 已真跑（`tools/importlinter_v2.toml` R6 契约；已用探针验证会红） |
| 不 import `langgraph`／`langchain` | 边界闸 R5b | 已真跑 |
| 模型调用只经 `gateway_adapter` | 边界闸 B6 | 已真跑 |
| 程序只对账、不替模型选工具 | 测试 `::no_lexicon_or_regex_in_tool_matching` | 待实现（阶段 5） |
| 限额数值不复制、只引预算表 | `state` 侧常量单点测试 ＋ `::exactly_one_match_per_subtask` | 待实现 |
| 工具描述三件套 | 测试 `::descriptor_covers_three_parts` | 待实现 |
| 「不做什么」的纯范围排除（不查数／不做主动发现等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分已由边界闸 R1/R6 覆盖 |
