# V2 工具匹配（tool_matching）

状态: 已定稿
来源: `specs/modules.md` `tool_matching` 卡、`docs/runtime-refactor/walk/11-匹配-工具阀.md`、`walk/裁决表.md` §06/§07/§11、`specs/query.md`（`QueryPlan` 真源）、`specs/tools.md`（工具注册表真源）
版式: `docs/spec-format.md` ｜ 工序: `docs/spec-process.md`

## 目标

给每个子问题配上**恰好一个**工具／路线，并把参数校验到**可执行**——**模型提议，程序做闭世界对账**。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 入口安全阀（注入／外发／写意图） | `gate` | `specs/modules.md` `## gate` |
| 废弃口径的**判断**（提及 vs 执行） | `tool_matching`（模型产出） | `walk/裁决表.md` #12 |
| 废弃口径结论的**分派**（放行／拒答） | `preconditions`（判定序第 1 位，机械分派） | `walk/裁决表.md` #12 |
| 澄清与反问 | `clarification` | `specs/modules.md` `## clarification` |
| 逐子问题过闸（三态） | `preconditions` | `specs/modules.md` `## preconditions` |
| 真正执行工具 | `execution` | `specs/modules.md` `## execution` |
| 引擎与工具的实现 | `tools`／引擎（本块**只走其公开面**） | `specs/modules.md` `## tools` |
| 模型输出的解析与 schema 校验 | `parsing` | `specs/modules.md` `## parsing` |
| 模型调用出口 | `gateway_adapter` | `specs/modules.md` `## gateway_adapter` |
| 工具**主动发现**（检索式选工具） | **不做**（工具集小，不上重设施） | `walk/11-匹配-工具阀.md` §七 Q-C |
| 拒因回喂自环的**熔断** | `tool_matching`（**本块自持同形拒因熔断**——行为 9；2026-10-17 EB3 D4.3 改判，原「暂不加」退役） | `walk/11-匹配-工具阀.md` §七 Q-B；真机证据 `eval/results/frames/EB2-D-诱9.json` |
| **同参重投闸的实现** | `parsing`（发射指纹）＋ `state`（限额计数）；本块只在其发射点**被拦** | L0 裁决：`synth/S1` 表 B 同一条两处归属（M3「决策出口」／H4「指纹面」）——按架构「闸件本体归公共层、相位不实现闸」定 |
| 拿词表／正则猜「该配哪个工具」 | 交模型；程序只对账 | `walk/00-设计总纲.md` §二（总纪律） |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| tool_matching | 新增 | 提议 ＋ 闭世界对账（恰配一条） |
| parsing | 新增 | 工具匹配发射的解析（同批新增） |
| prompts | 新增 | 工具匹配轮的指令与提示词合同（只出文本）；本 spec 只消费 |
| bookkeeping | 新增依赖 | 模型调用发起面：经 bookkeeping.call_model（单点发起），本块不直引 gateway_adapter |
| gateway_adapter | 新增 | 模型出口（唯一出口仍归它）；本块不直引——经 bookkeeping.call_model 发起 |
| state | 新增 | 匹配列等状态形状；本 spec 只消费 |
| tools | 改实现 | **工具描述写全**（何时用／不能做什么／参数示例）——本块只消费其公开面（含锚解析／注入件 `inject_retrieval_anchors`，行为 12） |

## 接口定义

```python
def match(state: RunState) -> ToolPlan | ToolMatchRejection: ...

class ToolPlan:
    matches: list[SubtaskMatch]            # 与子问题一一对应；条数＝子问题条数
    converged: bool = False                # 收敛让位形标记（2026-10-17 EB3 D4.3——见下条「收敛让位形」）

class SubtaskMatch:                        # **形状单点在 `parsing.models`（P-05，2026-10-16 归位；`specs/parsing.md` 行为 12）；本册只定义语义面**——字段照 parsing 类体（含 `mention_mode`——取值把守归本册消费面对账），`plan`／`retrieval_need`＝映射形（非 `QueryPlan`／`RetrievalNeed` 对象）、`caliber_key`＝空串缺省
    id: str                                # 必须对上某个子问题 id
    tool: str                              # 闭世界：工具注册表名单内的名字
    chain: Literal["data", "knowledge"]    # 闭世界
    plan: dict | None                      # chain == "data" 时必填（映射承载）
    retrieval_need: dict | None            # chain == "knowledge" 时必填（映射形，非 `RetrievalNeed` 对象）
    caliber_key: str                       # 空串缺省（真值才出键）
    mention_mode: str                      # 闭世界 executed｜mentioned_only；空串＝未装载（模型产出）

class RetrievalNeed:
    question: str                          # 必填；逐字转抄子问题原文
    anchors: list[str]                     # 可选（注入面见行为 12）
    family_hints: list[str]                # 可选（族机器名——闭世界四族真源＝`specs/retrieval.md` 的 `RetrievalNeed`；驱动供给分池配额）

class ToolMatchRejection:                  # 拒因回喂用（非终局）
    reasons: list[MatchReason]             # 结构化：缺配/多配/编号不符/必填缺/枚举越界/malformed_matches

class MatchReason:                         # 结构化拒因单条：kind 六类闭世界（成员见下表）＋ reason 拒文
    kind: Literal["缺配", "多配", "编号不符", "必填缺", "枚举越界", "malformed_matches"]   # 闭世界六类（前五类与「错误契约」逐字同源；第六类＝**支形状失败**，成员名照码面，2026-10-16 归位（流水 51））
    reason: str                            # 拒文（行为 11：`str` 逐字进 `reason` 字段）
```

- `QueryPlan` 的真源是 `specs/query.md`（**真源以该文为准**；若该文缺 `aggregate` 字段则记「待回阶段 3 补」——本块只引不复述字段）。
- **收敛让位形（2026-10-17 补·EB3 D4.3）**：`ToolPlan(converged=True, matches=[])`＝**第三形**（与「定案非空」「`ToolMatchRejection`」互斥）——语义＝**本 run 已触界收敛**（本相位同形拒因熔断／他处触界），本相位**不再产定案**：**零模型调用、零匹配**，交下游既有「无支可执行 → 作答收口」路由落答（材料直答已由 `bookkeeping.converge` 落 `draft`）。两形互斥由类体把守（`converged=True` ⇒ `matches=[]`；`matches=[]` ⇒ `converged=True`——空数组不成立的原断言就此让位于两形互斥）。行为面见行为 9。
- **`guide_text` 注入注（2026-10-16 裁·流水 63）**：签名补注入形参 `*, guide_text: str = ""`——§A 指南文本经编排注入（快照）；缺省空串＝空段头（本块只下传、不读文件；装配面归 api 组合根）。
- **`shared_context` 注入注（2026-10-17 补·真机消重批·缺陷一）**：签名补注入形参 `*, shared_context: bool = True`——**run 级共享上下文**（§A 指南段＋台账常驻块）本次是否注入；**判定归 `orchestration`**（同 run 只注一次、挂澄清轮首入包——本相位是同一 run 的第二次决策装配，故编排面通常下传 `False`），本块只下传（缺省 `True`＝本块行为不变）。口径真源＝`specs/prompts.md` 行为 7「共享上下文 run 级一次」注。
- **`retrieval_need` 透传注（2026-10-17 补·L3-02 检索透传断点批）**：知识链定案面的 `retrieval_need` **整 dict 原样透传**（键名／键形零改写——`question`／`anchors`／`family_hints` 全键，键形照 `appv2/retrieval/domain.py` 的 `RetrievalNeed` 消费面），并接**确定性锚注入**（行为 12）——旧实现只重建 `question`／`anchors` 两键、模型发的 `family_hints` 被丢（族配额退化成每族 1 席、gold 章被裁）。
- **`tool` 与 `chain` 都是闭世界**：`tool` ∈ 工具注册表名单；`chain` ∈ `data`｜`knowledge`。**越界值判失败**。
- **错误契约**：**漏配／多配／编号对不上／必填缺／枚举越界** → 返回 `ToolMatchRejection`（**结构化拒因**），由 `orchestration` **回喂模型、回到本相位重配**（**不做自动修补**）。
- **本块亦产出「提及 vs 执行」的结论**（废弃词闸的判断；Owner 裁决 #12）——**与 `caliber_key` 同批产出**，交 `preconditions` 判定序第 1 位做机械分派。
- **`caliber_key` 由本块产出**（L0 2026-10-15 裁决，按 `walk/裁决表.md` §12-A「语义上移到匹配相位」）：**模型在配工具时用本体账本把旧名归一到现行名、产出 `caliber_key`**；`preconditions` 只做**台账闭世界的结构校验**（该键在不在册），不承担语义归一。
- **`mention_mode` 是闭世界两值**：`executed`｜`mentioned_only`——「提及 vs 执行」结论的**字段载体**（**2026-10-16 补：pin-31/pin-14 消费面（流水 50）**）。取值与产出归属的逐字依据引文三条：本节「本块亦产出「提及 vs 执行」的结论」条（`:73`）「**本块亦产出「提及 vs 执行」的结论**（废弃词闸的判断；Owner 裁决 #12）——**与 `caliber_key` 同批产出**，交 `preconditions` 判定序第 1 位做机械分派」；`docs/runtime-refactor/eng/04a-应钉行为清单.md` pin-31 行原文「提及 vs 执行由**模型**在配工具那次调用产出；按结论放行/拒答的**机械分派**留在 `preconditions` 判定序第 1 位；出数只认现行口径（旧名归一在 `tool_matching`）」；`walk/裁决表.md` §12 行原文「**判断**（提及 vs 执行）由**模型**在**配工具那一次调用**产出；**分派**（按结论放行／拒答）留在 `preconditions` 判定序**第 1 位**（机械分派）」。**越界取值或缺该字段 → 判失败**（不猜、不取默认）。
- **`MatchReason` 的拒因枚举＝六类闭世界**（前五类成员名逐字取本规格 :63／:65 与「错误契约」:72 的五类词；第六类 `malformed_matches` 系原「未归类一条」经主窗裁归入而增——**逐字拒文＝V1 码面字面，字面真源 `recon/L1b-子任务后半.md` 所记 `appv2/runtime/subtask.py` 行——施工票照抄，偏离即停报，不许改写**）：

| 成员（`kind`） | 逐字拒文（照抄；`{…}` 为原 f-string 占位） | 字面锚（recon 行／码面行） |
|---|---|---|
| 缺配 | `缺 matches（非空数组——组内每个子问题恰一条）` ／ `matches 覆盖缺口（组内子问题缺匹配：{missing}）——每子问题恰一条` | recon L49／L62；`appv2/runtime/subtask.py` L325／L372-374 |
| 多配 | `matches id 重复：{match_id!r}（每子问题恰一条匹配）` | recon L54；`appv2/runtime/subtask.py` L338-339 |
| 编号不符 | `matches 支缺 id` ／ `matches id {match_id!r} 不在问题组内（闭合世界：{group_ids}）` | recon L52／L53；`appv2/runtime/subtask.py` L335／L336-337 |
| 必填缺 | `matches {match_id} 缺 tool` ／ `matches {match_id} data 链缺 plan（data_query 计划草案对象）` ／ `matches {match_id} plan 缺 metric_slot（必填非空）` ／ `matches {match_id} knowledge 链缺 retrieval_need（参数对象）` ／ `matches {match_id} retrieval_need 缺 question（必填非空）` | recon L56／L58／L59；`appv2/runtime/subtask.py` L345／L353／L355／L360／L362 |
| 枚举越界 | `matches {match_id} chain 越界（{'/'.join(sorted(CHAIN_KINDS))}）：{chain!r}` ／ `matches {match_id} chain/tool 不一致（{chain} 链须配 {_CHAIN_TOOL[chain]}）` | recon L55／L57；`appv2/runtime/subtask.py` L340-342／L346-347 |
| malformed_matches | `matches 支须为对象（{id/chain/tool/plan\|retrieval_need}）` | recon L51；`appv2/runtime/subtask.py` L332 |

- **第六类归位注（2026-10-16，流水 51）**：上表末行＝**支形状失败**（`matches` 数组的**支不是对象**时拒）；**成员名照码面，2026-10-16 归位（流水 51）**——本类系原「未归类一条」（原 :87）经主窗裁归入而增，**前五类成员名与逐字拒文一字未动**；表内 `\|` 系 markdown 转义，逐字照抄为 `plan|retrieval_need`。
- **占位记法**：上表逐字拒文按**码面字面**照抄（`{match_id}`）；recon 记法把 `{match_id}` 写作 `{id}`、把 `{'/'.join(sorted(CHAIN_KINDS))}` 写作 `data/knowledge`——两处**仅占位记法差异**，逐字以码面行为准（施工票照抄码面字面）。**第六类拒文里的 `{id/chain/tool/plan|retrieval_need}` 不是占位**——码面该行**无 `f` 前缀**（`appv2/runtime/subtask.py` L332 为整串字面），不得当占位替换或改写。
- **未归类一条——已销项（2026-10-16，流水 51）**：V1 字面 `matches 支须为对象（{id/chain/tool/plan|retrieval_need}）`（字面锚 recon L51；`appv2/runtime/subtask.py` L332）＝**支形状失败**，原五类成员无一逐字覆盖；**主窗裁：增第六类**（kind 名 `malformed_matches`，拒文照码面逐字，注「成员名照码面，2026-10-16 归位（流水 51）」）——闭世界以上述**六类**为准，原「**不新增成员**／登记待主窗裁归」**就此销项**。
- 真源：`specs/modules.md` `## tool_matching` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本模块不引入任何框架）。
- **模型调用发起面＝`bookkeeping.call_model`（单点发起）；其内部唯一出口＝`gateway_adapter`**：本块不直引 `gateway_adapter`（import 落点＝`appv2.runtimev2.bookkeeping` 包根——R2 禁深层子模块）。对应闸：`tools/importlinter_v2.toml` 的 **R7 契约**（禁直引 `appv2.infra.llm_client`——模型出口仍唯一归 `gateway_adapter`；**B6 只管 litellm 出 `infra`，不含「绕过 `gateway_adapter` 直引」这一面**；发起面收敛为规格层 doctrine，不设闸——主窗 2026-10-15 裁）。
- **不得直接 import `langgraph`／`langchain`**；对应闸：**R5b 契约**。
- **只经 `tools` 公开面**接触世界；对应闸：`specs/modules.md` 边界规则 R6（`runtimev2` 各块只经 `appv2.tools` 公开面）。
- **禁手写替代**：不得自建模型客户端／自建工具目录。对应闸：`tools/importlinter_v2.toml` 的 **R7 契约**（模型出口唯一归 `gateway_adapter`——发起经 `bookkeeping.call_model`）＋ **R6 契约**（只经 `tools` 公开面）；验收写法：「无旁路」行为断言。

## 行为约定

1. **模型只提议**（子问题 → 工具 ＋ 参数）；程序做**闭世界对账**，不替模型选工具。
2. **恰配一条**：每个子问题**恰好一条**匹配；**漏配／多配／编号对不上**任一 → 判失败。
3. **拒因回喂、不自动修补**：失败一律带**结构化拒因**回喂模型重配；程序不补齐、不猜。
4. **参数强校验**：`chain="data"` → `plan` 必填；`chain="knowledge"` → `retrieval_need` 必填；`metric_slot` 必填非空且**不得为英文列名形**（**形态判定**——只判形状，不判语义；**判定形**＝值整体呈 ASCII 标识符形——首字符 `[A-Za-z]`、其余仅 `[A-Za-z0-9_]`，大小写都咬——**Owner 2026-10-15 拍板 B 案**（fail-closed：宁可误拒重提议，不可漏放列名形），阶段 5 织网以此为准；禁例 `oil_pressure`／`WELL_NAME`——前者见 `ontology/petro/skill-guides/eval-cases.md` AC-G11，判定形真源锚 `walk/11-匹配-工具阀.md` 末「补注（2026-10-15 Owner 拍板）」节）；`ranking` 必填布尔且与 `direction` 同现；`caliber_key` **由本块产出**（模型用账本归一旧名到现行名；`preconditions` 只做台账闭世界结构校验）。
5. **枚举闭世界**：`chain`（`data`｜`knowledge`）、`direction`（`asc`｜`desc`）、`tool`（注册表名单）、`mention_mode`（`executed`｜`mentioned_only`——**2026-10-16 补（流水 51）**；字段载体见「接口定义」节 `SubtaskMatch`）——越界值判失败。
6. **工具描述写全**：每个工具的**载体＝`ToolDescriptor.description`**（模型选工具时看到的就是它），必须含**何时用／不能做什么／参数示例**三项（真源 `walk/11-匹配-工具阀.md` §七 Q-A）。这是选得准的**第一因**——**不加额外选型规则**。
7. **「出数只认现行口径」的结构约束落点**：`metric_slot` 到查询引擎前**只认现行名**；**模型产出归一后的名字**，本体账本只提供 alias↔canonical 的**「结构映射」**（不替模型做语义判断）（真源 `walk/裁决表.md` §12-A／§07）。
8. **不做主动发现**：不引入检索式选工具／工具主动发现设施（工具集小）。
9. **同形拒因熔断**（2026-10-17 EB3 D4.3 改判；原「熔断暂不加」退役）：拒因回喂自环**不再只靠轮数闸**——自环（`NODE_TOOLMATCH → NODE_TOOLMATCH`）不经澄清入口，**轮数闸在该路上到不了**（自环不计轮；真机证据 `eval/results/frames/EB2-D-诱9.json`：同形拒因连发 68 步 → 撞框架递归上限 35 → `run_failed`、整 run 零交付）。本块自持**三步**：
    - ① **占轮**：每次拒因回炉**占一轮**（`rounds` 加一——照澄清相位 `_record_rejection` 的占轮纪律，轮数闸在该路上保有兜底力）；
    - ② **拒因回喂**：逐字拒文落 `decision_error`（增量条「上次发射被拒」行的渲染面）——模型据此重决策（旧形该字段从未由本块写过＝模型学不到的真因）；
    - ③ **同形熔断**：**同形拒因**（`kind` ＋ 逐字拒文）既有次数 ≥ `RETRY_CAP_SAME_REJECTION` 时**触界收敛**——**显式触界**（`rounds` 顶到 `Budget.rounds`，补齐该自环上的轮数缺口，使 `check_limits` 的 rounds 键必命中）＋ `bookkeeping.converge`（落 `budget_converged` 注记／材料如实直答／`draft_kind="direct"`／`status="completed"`——六键全归唯一写口）＋熔断留痕（步 ＋ notice ＋ 过程档案注记）；收敛后的下一次入口返**收敛让位形**（零模型调用）。
    **同形判据**＝`kind` ＋ **逐字拒文**相等（拒文里带模型坏点片段 ⇒ 内容变即不同形——即逐字「同一 malformed 内容」的机读承载面）；计数面＝**只读本块步记录**的 `payload.rejection.{kind,reason}`，**不新增状态字段**（手法同执行相位既有拒因计数）。**异形不入同一计数**：两形交替夹发时各形独立累计（真机夹发形＝第 5 次拒因熔断）。
    **限额数值**仍只引**真源双指**（`walk/裁决表.md` §06-A 循环上限五项 ＋ `recon/K-上下文事件指南预算.md` R-K-72…R-K-78 逐键——轮数＝R-K-72；**轮上限值只归 `state.Budget`**）；本块自有参数**恰一件**＝同形重试次数上限（`constants.RETRY_CAP_SAME_REJECTION`，**不在本包公开面**——同澄清块 `REJECT_FREE_STREAK` 体例）——它是**熔断参数，非轮预算**。
10. **名归一闸保留**：精确键未命中时按名归一扫描（真源 `walk/11-匹配-工具阀.md` §一）。
11. **解析拒文→结构化拒因的转换归本块（消费方）**：解析拒文（parsing 产出的 `str` 拒文）→ `ToolMatchRejection` 的结构化转换归本块（消费方）：转换是机械适配（`str` 逐字进 `reason` 字段＋映射拒因枚举），零语义判断；parsing 不感知本块类型（R3）。（主窗流水 30① 裁决，2026-10-15——销 `docs/runtime-refactor/spec-review/parsing-评审.md` P-09「两头都不认」；解析本体与拒文产出归 `specs/parsing.md`，其风险 5 同步「已裁：转换在消费方」。）
12. **定案面参数不缩水（原样透传＋确定性锚注入）**（2026-10-17 补·L3-02 检索透传断点批）：知识链 `retrieval_need` 由本块**整 dict 原样透传**——键名不改、键不裁（`question`／`anchors`／`family_hints` 全键；键形照 `appv2/retrieval/domain.py` 的 `RetrievalNeed` 消费面），旧实现只重建两键致 `family_hints` 被丢（L3-02 病灶 A，证据源 `docs/runtime-refactor/ladder/L3/02-完井液在二开钻进段与三开-summary.md`）；透传后按 **V2-50 族 C ①**（`tickets/v2/V2-50-族C归属校验治理.md`；锚解析单点＝`appv2/tools/anchors.py`）做**确定性锚注入**：**模型已填锚不覆盖**（注入项在前、模型锚去重续后）、**缺锚按题面实体确定性补**（井号／油田名／平台名／报告号数字核——本体对象闭世界匹配，无实体题零注入）。锚解析件只经 `tools` 公开面**复用**（本块不自立第二套词面／正则——行 10 扫描面照旧）；注入项随定案载荷承载（**成功路径零补记步**：留痕面＝返回值 `ToolPlan.matches[].retrieval_need`，落 `state.tool_matches` 后与批量执行输入面同源零漂移——同 `caliber_key` 承载口径）。

## 不降级与静默禁令

- **合法降级路径：无**（本模块不自降级）。
- 失败与拒因必须产生**机读信号**：step payload 拒因字段 ＋ notice（类型取自 `synth/S6-事件与帧目录.md`）。`caliber_key` 由本块产出（语义归一在模型侧），其归一的机读信号落本块 step payload（**旁注 2026-10-16（W4 对账批）**：成功路径零补记步，信号现由返回值 `ToolPlan.matches[].caliber_key` 承载）。
- **不得静默丢子问题**：漏配即判失败，**不许"当作已配"**或跳过该子问题（红线原文 `arch/P7a-交接包与挂账清单.md` A-P7a-37）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 子问题恰配一条；漏配 → 判失败带结构化拒因 | `tests/domains/test_v2_tool_matching.py::exactly_one_match_per_subtask` |
| 多配／编号对不上 → 判失败 | `tests/domains/test_v2_tool_matching.py::duplicate_or_unknown_id_rejected` |
| 工具名不在注册表名单 → 判失败（闭世界） | `tests/domains/test_v2_tool_matching.py::tool_name_closed_world` |
| `chain="data"` 缺 `plan` ／ `chain="knowledge"` 缺 `retrieval_need` → 判失败 | `tests/domains/test_v2_tool_matching.py::required_by_chain` |
| `metric_slot` 为空，或呈英文列名**形态**（形态判定；判定形＝ASCII 标识符形——首字符 `[A-Za-z]`、其余仅 `[A-Za-z0-9_]`，大小写都咬；Owner 2026-10-15 拍板 B 案，判定形见行为 4）→ 判失败 | `tests/domains/test_v2_tool_matching.py::metric_slot_not_english_column` |
| `ranking` 与 `direction` 同现约束 | `tests/domains/test_v2_tool_matching.py::ranking_direction_paired` |
| 旧名经账本归一后才出数（出数只认现行口径） | `tests/domains/test_v2_tool_matching.py::legacy_name_normalized_before_query` |
| 解析拒文（parsing `str`）→ `ToolMatchRejection` 结构化转换归本块（消费方）：机械适配（str 逐字进 `reason` 字段＋映射拒因枚举）、零语义判断（行为 11） | `tests/domains/test_v2_tool_matching.py::parse_rejection_str_to_tool_match_rejection_consumer_side` |
| 每个工具描述含「何时用／不能做什么／参数示例」三项（**经 tools seam 测**；本块只消费其公开面） | `tests/domains/test_v2_tool_matching.py::descriptor_covers_three_parts` |
| 程序只对账、不替模型选工具（AST 扫描本模块；**豁免面＝结构归一／形态处理**，如去装饰符号、token 包含匹配，**不算语义词表**） | `tests/domains/test_v2_tool_matching.py::no_lexicon_or_regex_in_tool_matching` |
| 失败与拒因的机读信号在场（step payload ＋ notice） | `tests/domains/test_v2_tool_matching.py::rejection_signal_present` |
| 【边界集】`chain`／`direction` 越界取值 → 判失败 | `tests/domains/test_v2_tool_matching.py::boundary_enum_out_of_range` |
| 【保留集】名归一闸行为不变（本块） | `tests/domains/test_v2_tool_matching.py::retention_normalize` |
| 【保留集】聚合下推行为不变（归属 `execution`） | `tests/domains/test_v2_tool_matching.py::retention_pushdown` |
| `SubtaskMatch.mention_mode` 取值闭世界（`executed`／`mentioned_only`）越界即拒 | `tests/domains/test_v2_tool_matching.py::mention_mode_closed_world` |
| 【透传钉】知识链 `retrieval_need` 整 dict 原样透传（`family_hints` 不被丢）；旧形（anchors-only）不拒不造键 | `tests/domains/test_v2_tool_matching.py::test_retrieval_need_passthrough_keeps_family_hints` |
| 【到达性钉】族提示随定案载荷到达引擎侧 `RetrievalNeed`（四相位端到端） | `tests/domains/test_v2_four_phase.py::test_four_phase_knowledge_need_full_form_reaches_engine` |
| 【注入钉】题面实体确定性补锚（模型已填锚不覆盖）；零实体题零注入；注入随定案载荷留痕（行为 12） | `tests/domains/test_v2_tool_matching.py::test_deterministic_anchors_injected_and_never_overwritten` |
| 【熔断钉】同形拒因连发 → 触界收敛（模型调用恰 3、`budget_converged` 在场、`status=completed`、非 `run_failed`）；收敛后入口返让位形（零模型调用、零定案） | `tests/domains/test_v2_tool_matching.py::test_same_shape_rejection_fuses_to_convergence_within_three_calls` ＋ `tests/domains/test_v2_tool_matching.py::test_converged_entry_yields_letgo_plan_without_model_call` |
| 【回喂钉】拒因回炉占一轮 ＋ 逐字拒因回喂 `decision_error`（增量条渲染面）；异形不提前熔断；带材料收敛正文如实 | `tests/domains/test_v2_tool_matching.py::test_rejection_history_feeds_decision_error_verbatim` ＋ `tests/domains/test_v2_tool_matching.py::test_distinct_shapes_do_not_fuse_before_cap` ＋ `tests/domains/test_v2_tool_matching.py::test_convergence_answer_carries_materials_and_zero_type_notice` |
| 【真机回归】EB2-D-诱9 题面原句重演：同形／夹发拒因连发 → 熔断收口（run `completed`、零 `run_failed`、材料面如实、步数远小于旧形 68） | `tests/domains/test_v2_eb3_d4_defects.py::test_d43_dy9_same_shape_rejections_fuse_instead_of_run_failed` ＋ `tests/domains/test_v2_eb3_d4_defects.py::test_d43_dy9_mixed_rejection_shapes_fuse_at_fifth` |

> **增行＝2026-10-17 L3-02 检索透传断点批**（三行）：前两行为病灶 A（`family_hints` 被丢），第三行为行为 12 的锚注入三条（补锚／不覆盖／零注入＋留痕），落测文件＝`tests/domains/test_v2_tool_matching.py::test_retrieval_need_reaches_engine_with_family_hints`／`::test_deterministic_anchors_silent_on_entity_free_question`／`::test_anchor_injection_trace_in_determination_payload`（同批同面，不逐条增行）。

> **增行＝流水 51 收尾一致**（2026-10-16，第 15 行）：随行为 5「枚举闭世界」补 `mention_mode` 成员（`2026-10-16 补（流水 51）`）同批增；字段载体见「接口定义」节 `SubtaskMatch.mention_mode` 条，越界取值或缺该字段 → 判失败（不猜、不取默认）。

> **增行＝2026-10-17 EB3 D4.3 同形拒因熔断**（三行）：前两行为行为 9 的三步（占轮／拒因回喂／同形熔断）与让位形；第三行为真机题面重演（`eval/results/frames/EB2-D-诱9.json`）；落测文件＝`tests/domains/test_v2_tool_matching.py`（单元面四条）＋`tests/domains/test_v2_eb3_d4_defects.py`（链级两条）。

## 依赖与风险

- 依赖：`parsing`（发射解析）、`prompts`（本相位指令与合同）、`bookkeeping`（模型调用发起面——`call_model` 单点发起；**写口面**——落 step 记录/notice 经 bookkeeping 唯一写口，只引函数、不引其内部。2026-10-16 补（流水 51）——照 `specs/preconditions.md:30` 句式，本块「不降级与静默禁令」的 step payload 拒因字段＋notice 即该写口面的产出物，本块**不自建写路径**）、`gateway_adapter`（模型出口——经 `call_model` 的内部唯一出口，本块不直引）、`state`（状态形状）、`tools`（公开面＋描述文本）。
- 风险与对策：
  1. **参数校验与 `query` 卡的 `QueryPlan` 真源漂移** → 两处规则不一致。对策：`QueryPlan` 只引用不复制；检测手段＝与 `specs/query.md` 的字段对照测试。
  2. **工具描述写全落在 `tools` 侧**（本块唯一涉及 runtimev2 之外文件的地方）。对策：改动限于描述文本，不动 `tools` 公开接口签名；检测手段＝`tools` 卡公开接口对账（阶段 7 体检）。
  3. **对账滑成"程序替模型选工具"** → 违总纪律。对策：程序只做存在性/一致性/枚举三类结构判定；检测手段＝AST 机检 `no_lexicon_or_regex_in_tool_matching`。
  4. **同参重投闸归属**（原评审 F-11）：`synth/S1` 表 B 给了两个面（M3 决策出口／H4 指纹面）——**L0 裁决：闸件本体归 `parsing`（指纹）＋ `state`（限额），本块只被拦、不实现**；**拦截实现归 `execution`（dispatch 统一出口，流水 30②）**——触发／拦截／回喂均不在本块；检测手段＝`parsing`／`state`／`execution` 各自测试（不在本块验收表）。
  5. **工具描述三件套与 `specs/tools.md` 的对齐**（原评审 F-03）→ **Owner 2026-10-15 已裁「要」**：`specs/tools.md` 行为 6 已同步补三件套（`descriptors()` 的 `description` 含何时用／不能做什么／参数示例），本规格不再挂待办；检测手段＝`tests/domains/test_v2_tools.py::descriptor_covers_three_parts`。
  6. **同一坏内容长期不收敛 → 撞框架递归上限**（2026-10-17 EB3 D4.3）：拒因回喂自环**不计轮**，轮数闸在该路上到不了，同形拒因可无限连发（真机 68 步 → `run_failed` 零交付）。对策＝本块同形拒因熔断（行为 9，显式触界收敛）；**残余敞口＝异形交替但各形不重复**（每形各出现 1 次时可拉到轮闸前更多次）——敞口大小＝拒因形数（有限闭世界六类），故非无界；检测手段＝`tests/domains/test_v2_eb3_d4_defects.py::test_d43_dy9_mixed_rejection_shapes_fuse_at_fifth`（夹发形第 5 次熔断）＋单元面 `::test_distinct_shapes_do_not_fuse_before_cap`。
  7. **让位形依赖下游既有路由**（2026-10-17 EB3 D4.3 登记）：收敛让位形（`converged=True`）交「无支可执行 → 作答收口」路由落答——该路由归 `orchestration`（`_route_after_precondition`）与 `execution`（收敛态零派遣，`specs/execution.md` 行为 16）两处既有面，**本块不改它们**；对策＝`execution` 侧零派遣兜住「过闸支空但放行」的支（知识链形），检测手段＝链级真机重演（本表第三行两件）＋`specs/execution.md` 行为 16 验收行。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 只经 `tools` 公开面接触世界 | 边界闸 R6 | 已真跑（`tools/importlinter_v2.toml` R6 契约；已用探针验证会红） |
| 不 import `langgraph`／`langchain` | 边界闸 R5b | 已真跑 |
| 模型调用经 `bookkeeping.call_model` 发起（单点发起；其内部唯一出口 `gateway_adapter`） | 边界闸 **R7**（出口面：禁直引 `appv2.infra.llm_client`；B6 只管 litellm 出 `infra`，不含绕过面。发起面为规格层 doctrine，不设闸） | 已真跑 |
| 程序只对账、不替模型选工具 | 测试 `::no_lexicon_or_regex_in_tool_matching` | 待实现（阶段 5） |
| 限额数值不复制、只引限额真源双指（`recon/K-上下文事件指南预算.md` R-K-72…R-K-78 ＋ `walk/裁决表.md` §06-A） | `state` 侧常量单点测试 ＋ `::exactly_one_match_per_subtask` ＋ `::test_no_limit_literals_only_sources_cited`（本块自有上限**恰一件**＝同形熔断参数，非轮预算） | 待实现 |
| 工具描述三件套 | 测试 `::descriptor_covers_three_parts` | 待实现 |
| 产出「提及 vs 执行」结论（废弃词闸的判断；与 `caliber_key` 同批产出） | 钉 **`pin-31`** | 待织网（阶段 5） |
| `metric_slot` 英文列名形判定（判定形＝ASCII 标识符形，见行为 4——Owner 2026-10-15 拍板 B 案） | 测试 `::metric_slot_not_english_column` | 待实现 |
| 「不做什么」的纯范围排除（不查数／不做主动发现等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分已由边界闸 R1/R6 覆盖 |

> **2026-10-17 补（EB3 D4.3·同形拒因熔断→触界收敛·审计）**：**行为 9 改判**（原「熔断暂不加」退役）；「不做什么」表熔断行、接口定义 `ToolPlan.converged`、风险 6／7、验收表三行同批。**病灶**：拒因回喂自环（`NODE_TOOLMATCH → NODE_TOOLMATCH`）**不经澄清入口**，轮数闸在该路上到不了（自环不计轮）；同一 malformed 内容连发时**拒因从不回喂到 `decision_error`**（本块旧形零写过该字段）——模型学不到，遂无限重发同形坏 JSON，一路撞框架 recursion limit 35 → `run_failed`、整 run 零交付。**真机证据**：`eval/results/frames/EB2-D-诱9.json`＝`run-4c83211c`（题面＝「按台账口径，8 月 5 口检泵井的检泵周期最长的是哪口井、多少天？最短的比它短多少天？这 5 口井的检泵作业费合计多少万元？」；68 步、32 条 notice（含 `malformed_matches`／`缺配` 交替连发）、末条 `run_failed`＝`Recursion limit of 35 reached without hitting a stop condition`、`final.status="failed"`）。**改法**（手法照澄清相位占轮纪律与执行相位拒因计数）：①每次拒因**占一轮**；②逐字拒因回喂 `decision_error`（增量条渲染面）；③同形拒因（`kind`＋逐字拒文）既有次数 ≥ 熔断参数时**显式触界**（`rounds` 顶到 `Budget.rounds`——补该自环的轮数缺口）＋`bookkeeping.converge` 落六键（`budget_converged`／材料如实直答／`draft_kind="direct"`／`status="completed"`）＋熔断留痕（步／notice／过程档案注记）；④收敛后入口返**收敛让位形**（零模型调用、零定案）。**新行为下的真机重演**：understand 1 ＋ decision 4（澄清 1／熔断内 3）、12 步、run `completed`、零 `run_failed`、收敛正文如实（**本帧零观察／零工具 ⇒ 零材料如实形**，材料清单恰在场——带材料收敛正文字面另由单元面 `::test_convergence_answer_carries_materials_and_zero_type_notice` 钉）。**让位形的零依赖序**：`match` 内收敛让位形**先于「取问题组」**（让位形不消费任何上游产物，故上游缺组亦不影响收口——单元面 `::test_converged_entry_yields_letgo_plan_without_model_call` 以清空问题组断在案）。**落点**：`appv2/runtimev2/tool_matching/matching.py`（`match` 让位形支＋`_reject` 三步＋`_same_shape_streak`＋`_converge_on_cap`）、`appv2/runtimev2/tool_matching/constants.py`（熔断参数与文案）、`appv2/runtimev2/tool_matching/models.py`（`ToolPlan.converged` 两形互斥）、`appv2/runtimev2/tool_matching/__init__.py`（公开面再声明）、`appv2/runtimev2/execution/core.py`（收敛态零派遣——见 `specs/execution.md` 行为 16）、`tests/domains/test_v2_tool_matching.py`（两机器闸口径随行为 9 改判＋四条新测）、`tests/domains/test_v2_eb3_d4_defects.py`（两条链级真机重演）。**登记（交主窗）**：①**超授权清单面的三件**——本票逐字清单只列 `matching.py`，实施中同批改动了同块 `models.py`（收敛让位形的形状承载）／`constants.py`（熔断参数与文案）／`__init__.py`（公开面）——三者皆本块内形状／常量／公开面，跨块零触碰，但属**越清单实施**，如实登记；②**熔断参数的公开面口径**——`RETRY_CAP_SAME_REJECTION` 按澄清块 `REJECT_FREE_STREAK` 先例**不上公开面**（`__all__` 与规格接口名单不含它；测试经 `constants` 子模块直读）；③**拒因回炉的直写例外**——`rounds`／`decision_error` 两字段由本块直写（`bookkeeping` 包根无其写口；同款先例＝`clarification/core.py`／`execution/core.py`），全局闸 `test_no_direct_state_write_in_phases` 的扫描面＝共享写面七字段（两字段不在其内）；本块局部闸 `::test_no_direct_state_write_in_tool_matching` 的同批口径＝「零写七共享字段＋两字段登记例外」；④**让位形对下游两处的依赖**＝`orchestration` 既有路由（`_route_after_precondition`：放行支空 → 作答收口）＋`execution` 收敛态零派遣（本批新增，兜住知识链形「过闸支空却放行」的口）——**可替代方案**＝`orchestration` 里 2 行显式钩子（识 `converged` 直落 answer），但编排面不在本票范围、且另一代理同批改该文件，故取「不改编排面」形；⑤**异形交替敞口**：每形各出现 1 次时熔断不触发（拒因形数＝闭世界六类，故敞口有界）；若需按「家族」而非「逐字」计数，属口径变更、回头裁。
