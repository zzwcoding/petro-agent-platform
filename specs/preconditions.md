# V2 前置检查（preconditions）

状态: 已定稿
来源: `specs/modules.md` `## preconditions` 卡、`docs/runtime-refactor/walk/12-前置检查-前置条件机.md`、`walk/06-过程图-循环挂起判断.md`、`walk/裁决表.md` §06/§07/§12、`synth/S3`（判定位条数真源）、`synth/S1` M4
版式: `docs/spec-format.md` ｜ 工序: `docs/spec-process.md`

## 目标

每个子问题在**真去查之前**过一串**固定检查**，出**三态**之一——**放行／拒答／等用户**；**纯程序零 LLM**（语义判断已上移到匹配相位）。

## 不做什么

| 不做 | 由谁承担 | 锚点 |
|---|---|---|
| 语义判断（「提旧名」还是「要旧口径」、口径对不对、时间窗能否确定） | `tool_matching`（模型产出归一后的指标名与口径、废弃词结论、时间窗结论）——**Owner 已裁**（`walk/裁决表.md` #12／#13） | `walk/裁决表.md` #12／#13；`walk/12-前置检查-前置条件机.md` §四/§七 Q-A |
| 产出子问题与路线 | `clarification` | `specs/modules.md` `## clarification` |
| 真正执行查询 | `execution` | `specs/modules.md` `## execution` |
| 模型输出的解析与 schema 校验本体 | `parsing` | `specs/modules.md` `## parsing` |
| 任何模型调用 | **本模块不调模型**（零 LLM 铁律）；模型调用出口属 `gateway_adapter` | `walk/12-前置检查-前置条件机.md` §七 Q-A |
| 入口安全闸（注入／外发／写意图） | `gate` | `specs/modules.md` `## gate` |
| 拿词表／正则猜「该不该放行」 | 交模型；程序只校格式 | `walk/00-设计总纲.md` §二（总纪律） |

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| preconditions | 新增 | 三态闸的调度与结果汇总 |
| tools | 改实现 | **闸件本体在 `appv2/tools/precondition.py`**（ADR-0007 同时裁决 4）：语义类判定位上移后，闸内只留结构校验；本块只经其公开面 |
| state | 新增 | 判定结果与注记的状态形状；本 spec 只消费 |
| bookkeeping | 新增依赖 | **写口面**——落 step 记录/notice 经 bookkeeping 唯一写口，只引函数、不引其内部 |

## 接口定义

```python
def gate_all(state: RunState, *, window_candidates=None, watermark=None, data_wells=None) -> list[SubtaskVerdict]: ...   # 签名以卡为准（`specs/modules.md` `## preconditions`）；三注入参＝位 2／6／7 输入路径（W4 对账批 2026-10-16 回填——卡面已列、本行旧签名收齐；producer＝orchestration）

class SubtaskVerdict:
    subtask_id: str
    decision: Literal["allow", "refuse", "ask"]   # 三态闭世界
    notes: list[str]             # **注记并入放行的附加信息**（Owner 2026-10-15；不是第四态）
    reason: RefusalReason | AskReason | None
    hit_rule: str | None         # 命中的判定位标识（可解释性）
class RefusalReason:
    rule_id: str                 # 命中的判定位
    human_text: str              # 人话（供如实直答）
    alternatives: list[str]      # 替代项（如替代口径）
class AskReason:
    kind: Literal["external_table_approval", "caliber_clarify"]
    prompt: str
    options: list[str]
```

- **`AskReason.kind` → ask 帧 `frame.kind` 的映射（唯一映射表）**：`external_table_approval` → `external_table_approval`；`caliber_clarify` → `clarify`。帧侧 `frame.kind` 是闭世界 `clarify`｜`external_table_approval`（真源 `docs/runtime-refactor/synth/S6-事件与帧目录.md` §一）；本块产出的是 `AskReason.kind`，**发帧与映射由 `orchestration`／`transport` 承接**——两处取值**不得各说各话**（本表即对账依据）。

- **`decision` 是三态闭世界**：`allow`｜`refuse`｜`ask`；**越界值判失败**（不猜、不取默认）。
- **三态与真源「四态」的差异**：与 ADR-0005／`synth/S1` 所记「四态」的差异，由 `walk/12-前置检查-前置条件机.md` §七 Q-B（另见 `walk/裁决表.md` §12-B）裁决覆盖；ADR／S1 同步修订**已兑现**（2026-10-15）——`docs/adr/0005-子任务图与前置条件机.md` 末附修订注记（原文保留加注）、`synth/S1` M4 行改「三态闸」。
- **唯一确定性来源**：本函数**不做任何模型调用**（可机检，见「框架与依赖红线」）。
- 错误契约：判定器抛错（闸件不可用）→ **不着`allow`**（fail-closed），转为 `refuse` 并带拒因，由 `orchestration` 承接留痕。
- 真源：`specs/modules.md` `## preconditions` 卡（签名以卡为准）。

## 框架与依赖红线

- **无点名框架**（本模块不引入任何框架、**不调模型**）。
- **不得直接 import `langgraph`／`langchain`**（框架只许在 `orchestration`）。对应闸：**R5b 契约**（source 覆盖 `preconditions`）。
- **零 LLM 铁律**：本模块及其闸件**不得 import 任何模型客户端**——**不得引 `litellm`／`appv2.infra.llm_client`（R7 契约 ＋ B6）**，**且不得引 `appv2.runtimev2.gateway_adapter`（R8 契约「零 LLM 面」）**。对应闸：`tools/importlinter_v2.toml` 的 **R7／R8 契约** ＋ 一条 **AST 机检**测试（先例 `tests/domains/test_v2_four_phase.py:446`）。
- **只经 `tools` 公开面**接触世界（闸件本体在 tools 侧）。对应闸：**R6 契约**。
- **禁手写替代**：不得自建闸件旁路、不得绕过 `tools` 直引引擎。

## 行为约定

1. **逐子问题判定**：对每个子问题**恰好一条** `SubtaskVerdict`；`subtask_id` 必须对上某子问题（对不上＝判失败）。
2. **判定序固定＋命中即停**（同一处明文表，见下）；**不得乱序、不得并行判定同一子问题**。
3. **判定位的条数与次序以真源为准**：现为 `synth/S3` C-01 所记的 **8 个判定位（6 主闸号 ＋ 2 子闸）**——本规格不复制该数字以外的新值、不新增判定位。
4. **闸内只做结构校验与机械分派**：语义类结论——禁用词「提及 vs 执行」、口径归一、**时间窗能否确定**——**一律由 `tool_matching` 的模型产出**（Owner 裁决 #12／#13）；本块只接收结论并按其**机械分派**，不判语义。
5. **注记并入放行**：命中带注记的判定位时，`decision="allow"` 且把注记写进 `notes`；**不设第四态**。
6. **外表审批（申报面）**：闸 2 **只做申报面判定**（计划里声明的外表 → `ask`／审批）；**「执行前再扫」归引擎执行面**（`tools`／`query`，真源 `docs/runtime-refactor/arch/P3b-票堆V2-35至45.md` V2-44：实扫由引擎在 SQL 定稿后执行）；恢复后本块**消费 `approved_ids` 重判**。
7. **换链回炉一次为界**：同一子问题因换链回炉**只允许一次**（真源：`docs/runtime-refactor/arch/P3b-票堆V2-35至45.md` V2-43 ／ `docs/runtime-refactor/walk/06-过程图-循环挂起判断.md` 循环表）；再触发同支 → 转 `refuse`（不给第三次）。
8. **可解释性**：任一非 `allow` 的结论必须带 `hit_rule` ＋ 人话原因（`human_text`）；口径类拒答还必须带**替代项**（`alternatives`）——缺项＝判失败。
9. **全拒的处理不属本块**：本块只逐子问题出结论；「全拒 → 带拒因如实直答」由 `answering` 承接（本块只保证拒因齐备）。
10. **判定结果全部留痕**：每个 `SubtaskVerdict` 落 step 记录（含 `hit_rule`）；**静默放行是已知失败模式**，故 `allow` 且带 `notes` 时注记必须落在 step payload 里。

**判定序明文表**（次序＝执行序，命中即停）：

| 序 | 判定位 | 判什么 | 性质 |
|---|---|---|---|
| 1 | 闸1 禁用词 | 旧叫法／合法提及 | **结构分派（消费模型结论）**——判断在 `tool_matching`（Owner 裁决 #12） |
| 2 | 闸1b 模糊时间词门 | 时间窗能否确定／是否需反问 | **结构分派（消费模型结论）**——判断在 `tool_matching`（Owner 裁决 #13；**不设「确定性词面门」**） |
| 3 | 闸2 外表越集 | 计划**声明**用到平台外的表 → `ask`（申报面判定；**「执行前再扫」归引擎执行面**，见行为 6） | 结构 |
| 4 | 闸3 合法口径（＋前置台账闭世界） | 口径合法性（语义部分**已上移**）／指标在不在台账 | 结构 |
| 5 | 闸4 在册绑定态 | 指标绑没绑汇总表 | 结构 |
| 6 | 闸4b 软失败域闸 | 题眼域↔链路域一致 | 结构 |
| 7 | 闸5 新鲜度窗 | 时间范围 vs 数据水位 | 结构 |
| 8 | 闸6 单井支持 | 单井查得了吗 | 结构 |

> **序 2 位输入口径注**：**结构判据**＝模型发射载荷窗槽双 null＝不能确定（不写词面门，裁决 #13）；ask 支候选窗＝**注入参** `window_candidates`（producer＝orchestration，本块不直引 query）——2026-10-16 裁（流水 56）。

## 不降级与静默禁令

- **合法降级路径：无**（本模块不降级；闸件不可用时按 fail-closed 转 `refuse`，不静默放行）。
- 任何非 `allow` 与任何带注记的 `allow` **必须产生机读信号**：step payload 的 `hit_rule`／`decision`／`notes` 字段 ＋ notice（类型取自 `synth/S6-事件与帧目录.md`）。
- 红线原文：`arch/P7a-交接包与挂账清单.md`（A-P7a-37）「**不许静默**——若任何相位仍发生截断，模型面必须随材料段带明示……收口注记面同步披露」。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 每子问题恰一条 verdict；`subtask_id` 对不上 → 判失败 | `tests/domains/test_v2_preconditions.py::exactly_one_verdict_per_subtask` |
| `decision` 越界取值 → 判失败（三态闭世界） | `tests/domains/test_v2_preconditions.py::decision_enum_closed_world` |
| 判定序固定＋命中即停（打在序 3 上不进序 4） | `tests/domains/test_v2_preconditions.py::fixed_order_short_circuit` |
| 带注记的判定位 → `allow` ＋ `notes` 非空（**不设第四态**） | `tests/domains/test_v2_preconditions.py::note_merges_into_allow` |
| 外表越集（申报面）→ `ask`（kind=external_table_approval） | `tests/domains/test_v2_preconditions.py::declared_external_table_asks` |
| 恢复后消费 `approved_ids` 重判放行 | `tests/domains/test_v2_preconditions.py::resume_reconsume_approved_ids` |
| 换链回炉只允许一次；二次触发 → `refuse` | `tests/domains/test_v2_preconditions.py::rewire_once_then_refuse` |
| 非 `allow` 必带 `hit_rule` ＋ 人话；口径类拒答必带替代项 | `tests/domains/test_v2_preconditions.py::refusal_has_rule_text_alternatives` |
| 闸件抛错 → fail-closed 转 `refuse`（**不静默放行**） | `tests/domains/test_v2_preconditions.py::gate_error_fail_closed` |
| 本模块与闸件零 LLM（AST＋import 双证） | `tests/domains/test_v2_preconditions.py::no_model_call_in_preconditions` |
| 程序侧无词表／正则语义判断（AST 扫描本模块；**豁免面＝形态处理／集合成员判定**——不算语义词表／正则） | `tests/domains/test_v2_preconditions.py::no_lexicon_or_regex_in_preconditions` |
| 判定结果的机读信号在场（step payload ＋ notice） | `tests/domains/test_v2_preconditions.py::verdict_signal_present` |
| 【边界集】空窗／越界水位／未绑定指标／单井不支持 → 各自命中对应判定位 | `tests/domains/test_v2_preconditions.py::boundary_each_rule_hits` |
| 【保留集】`allow` 的普通子问题行为不变（无注记、无额外信号） | `tests/domains/test_v2_preconditions.py::retention_plain_allow_unchanged` |

## 依赖与风险

- 依赖：`state`（状态形状）、`tools`（闸件本体在 `appv2/tools/precondition.py`，只经其公开面）。
- 风险与对策：
  1. **语义项没真的上移**（闸内残留词表判「提及 vs 执行」）→ 违总纪律。对策：闸内只做结构校验；检测手段＝AST 机检 `no_lexicon_or_regex_in_preconditions`（**豁免面＝形态处理／集合成员判定**：不算语义词表／正则）＋ 与 `tool_matching` 的接口对照测试。
  2. **判定位条数/次序漂移**（历史三说 5/6/8）→ 对策：以 `synth/S3` C-01 为唯一真源，写成上文一处明文表；检测手段＝判定序测试 `fixed_order_short_circuit`。
  3. **闸件在 `tools` 侧被别处绕过直调**（跳过三态收口）→ 对策：闸件本体仍为 `tools` 公开面的一部分；检测手段＝**R6 契约**（只经 `tools` 公开面）＋ 阶段 7 体检的接口契约对账。
  4. **静默放行**（已知失败模式三变体之一）→ 对策：`allow` 带注记时强制落 step payload；检测手段＝测试 `verdict_signal_present`。

## 与闸的挂钩表

| 本规格的硬要求 | 挂钩 | 现状 |
|---|---|---|
| 触及模块名已声明 | spec gate | 已进 CI |
| 验收测试逐行有标识 | spec gate | 已进 CI |
| 本模块零 LLM（不调模型） | 边界闸 **R8**（零 LLM 面）＋ AST 机检 `::no_model_call_in_preconditions` | R8 已真跑；AST 测试待实现（阶段 5） |
| 只经 `tools` 公开面接触世界 | 边界闸 **R6** | 已真跑 |
| 不直接 import `langgraph`／`langchain` | 边界闸 **R5b** | 已真跑 |
| 三态闭世界 / 判定序固定 / 注记并入放行 | 测试 `::decision_enum_closed_world`／`::fixed_order_short_circuit`／`::note_merges_into_allow` | 待实现 |
| 静默禁令（非 allow 与注记均留痕） | 测试 `::verdict_signal_present` | 待实现 |
| 废弃词结论的**分派**（判定序第 1 位，机械分派；判断在 `tool_matching`） | 钉 **`pin-31`**（模型判「提及 vs 执行」／机械分派在 `preconditions` 判定序第 1 位／出数只认现行口径） | 待织网（阶段 5） |
| 模糊时间词＋plan 非空 → 确定性改判走 clarify 三选一反问帧 | 钉 **`pin-14`**（落点＝判定序第 2 位闸1b——消费 `tool_matching` 时间窗结论 → `ask` 反问） | 待织网（阶段 5） |
| 软失败域闸：data/semantic 成功返回但域错 → 换链回炉恰 1 次为界 | 钉 **`pin-16`**（落点＝行为 7 换链回炉一次为界） | 待织网（阶段 5） |
| 前置条件机**三态**语义一字不动（放行／拒答／等用户，注记并入放行）＋判定固定序命中即停＋零 LLM 面＋扩口未批不得直答终局 | 钉 **`pin-17`**（落点＝行为 2／3／5 ＋ 判定序明文表 ＋ 零 LLM 红线；真源 `walk/裁决表.md` §12-B/C） | 待织网（阶段 5） |
| 「不做什么」的纯范围排除（不查数／不出子问题等） | **人审** | 接不上闸的原因：纯范围排除没有形状／存在性／退出码判据；能降维的部分（相位互不 import、只经 tools）已由边界闸 R1／R6 覆盖 |
