# V2 数据查询引擎（query＝六站链 Skill 移植）

状态: 已定稿
来源: specs/modules.md `query` 卡、docs/prd.md §③、问数组答案册（eval/answers/问数组-题目与答案.md）

## 目标

V1 六站链（模板装配 SQL→三闸→只读执行→血缘卡）原样移植为确定性引擎：
输入**计划**，输出权威表＋血缘卡或六类闸结果之一。问数组 A~H 族行为逐族钉死不回归。

## 不做什么

不做 LLM 判型/路由（V1 N5 语义不进本模块）；不做自然语言直接转 SQL（计划由 runtime 规划步产出）；
不改 V1 的计量列绑定口径（MEASURE_COLUMNS 语义原样）。

## 触及的模块

| 模块 | 改动类型 | 说明 |
|---|---|---|
| query | 新增 | QueryEngine（validate＋run）＋QueryPlan/QueryOutcome schema |

## 接口定义

```python
class QueryEngine:
    def validate(self, plan: QueryPlan) -> PlanCheck: ...   # 白名单/指标一致性(FX-13)/窗界(ground_pinned_window)
    def run(self, plan: QueryPlan) -> QueryOutcome: ...

# QueryPlan 十字段（五源槽位＋方向二值＋V2-03 采纳项回写：展示注记/默认窗标注/越集外表集/行级身份）：
# QueryPlan = {metric_slot, window_start, window_end, limit, ranking, direction,
#              window_label, is_default, external_tables, actor}
# QueryOutcome 六联合态：
#   rows+lineage(血缘五要素:口径/来源表/过滤/数据截至批次/收口注记)
# | freshness_block(水位日期,窗标签,is_default)
# | unbound_degrade(指标 Evidence,依据)
# | need_clarify(候选窗三选一)
# | external_table_approval(外表名,ASK 素材)
# | refuse(原因)
```

## 行为约定

1. validate 纯确定性：指标槽 ∈ 计划候选集（FX-13 封堵换指标）；窗界 end≤today＋366；
   条数/排名词面消歧按 V1 domain.py 合同值（明细排序 ORDER BY prod_date, well_id 等原样）。
   （**2026-10-17 EB3 D4 注**：上句「条数/排名词面消歧」的**运行时消费面**＝`execution` 计划面——
   `specs/execution.md` 行为 15「计划面确定性规则」：问句指标接地闸＋「前 N」→排名归一；本模块的
   `build_query_plan`／`parse_row_limit`／`is_ranking_question`／`parse_ranking_direction` 仍是
   该合同值的**真源件与漂移对读基准**，其 V2 链上调用面为零调用（真源件保持只读基准位）。）
2. 新鲜度闸：窗上沿晚于水位→拦停（不返回空数冒充）＋水位/窗标签/默认窗标注（is_default）如实携带。
3. 在册未绑定指标→unbound_degrade，Evidence 依据经 knowledge 取（query→knowledge 为 modules.md 登记的唯一互引例外）。
4. 缺参（模糊时间如"最近"）→need_clarify 三选一候选窗；外表越集→external_table_approval（V1 N7.4c 语义；
   别名解析修复＝本模块内的 ticket 事项，治 Q11"interrupt 不可达"病灶）。
5. 执行只读账号＋白名单 Schema（INV-2/INV-3）；血缘卡随结果必出（INV-5 的口径依据）。

## 验收测试

| 验收标准 | 对应测试 |
|---|---|
| 去年窗明细 50 行截断＝09-01 当日前 50 井，首行 N-01 21.16（题册关键数值钉死） | `tests/domains/test_v2_query.py::detail_window_50` |
| 今年窗首行 N-01 36.97 方＋改绑注记＋血缘④=2026-08-31 | `tests/domains/test_v2_query.py::rebind_notice` |
| 排名降序 Z-16 5839.6；升序末位 Z-22 1784.7/N-09 1851.5；液量 N-15 8824.4 | `tests/domains/test_v2_query.py::ranking_values` |
| 显式条数"前 30"→恰 30 行（默认 50 不顶替） | `tests/domains/test_v2_query.py::explicit_limit_30` |
| 本月/近7天/默认窗→freshness_block＋标注齐、零数值 | `tests/domains/test_v2_query.py::freshness_blocks` |
| "最近"→need_clarify 三选一 | `tests/domains/test_v2_query.py::vague_time_clarify` |
| 含水率/配产量→unbound_degrade＋Evidence 依据 | `tests/domains/test_v2_query.py::unbound_degrade` |
| "井位台账"→external_table_approval（ASK 素材齐） | `tests/domains/test_v2_query.py::external_table_ask` |
| 换指标出数被 FX-13 一致性闸拦（validate 拒） | `tests/domains/test_v2_query.py::metric_switch_blocked` |
| 只读断言：执行后库表零变化（INV-2） | `tests/domains/test_v2_query.py::readonly_inv2` |

## 依赖与风险

- 依赖：infra 复制票（只读会话/clock）；knowledge（Evidence）；agg fixture（题册绑定 CSV 真数据快照）。
- 风险：V1 词面正则（_RANKING_RE 含"前 N"坑——题册 v2 已修正题面，引擎语义照合同值不照旧正则陷阱）。
