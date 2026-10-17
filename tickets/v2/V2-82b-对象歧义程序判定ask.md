# V2-82b 对象歧义程序判定 ask（票②a-2）

- 日期：2026-10-17 ｜ 批次：V2-82
- 依据：流水 88（Owner 设计：术语识别→主体确认→歧义反问→否则分源作答＋提示）＋取证 agent-185（B6：对象歧义 ask 现状零程序判定点）
- 前置依赖：**V2-82a 必须先收**（消费 state.subjects / subject_terms）
- 施工代理：全新实例，禁 commit

## 背景

裁决⑥ 本有「目标/对象/口径歧义→ask」但全靠 LLM 自觉（程序只验形状）；B-正6（近三年8月平均检泵周期——两个油田数据都在材料里，模型没反问也没干净分源）就是漏网例。本票把这条变成**程序行为**：术语命中 ∧ 指标粒度要求主体 ∧ 题面无主体 ∧ 系统内油田实例≥2 → 程序直接弹 ask，不等 LLM。

## 判定门（伪代码，全部条件同时成立才弹）

```python
def 对象歧义门(state) -> AskRequest | None:
    if state.route != "full": return None
    if state.subjects: return None                      # LLM 已给主体（V2-82a 通道）
    if not state.terms and not state.metric_candidates: return None
    # 指标粒度要求主体：台账 grain 含 单井/区块/油田/平台 任一
    names = state.terms or state.metric_candidates
    if not any(粒度要求主体(dump名) for 名 in names): return None
    fields = 油田实例名单()                              # dim_well field_name distinct 归一（≤3 个，保序）
    if len(fields) < 2: return None
    if ask_count(state) >= budget.ask_cap: return None  # 预算尊重
    return AskRequest(prompt=PROMPT, options=fields[:3] + [OPTION_ALL])
```

「油田实例名单」数据源：dim_well 卡读面（`appv2/tools/handlers.py:388-467` 井号名录同源的 well_rows，取其 field_name 列 distinct 归一）——放 tools 侧新函数（如 `subject_terms.oilfield_instances(well_rows)`），runtimev2 经公开面调用。粒度判定读 `state.ledger_dump["metrics"]` 各条 grain 字段（含「单井」「区块」「油田」「平台」子串即要求主体）。

## ask 发射与恢复（复用既有挂起机制，不新造帧型）

- 发射点：`orchestration/graph.py` `_make_clarify` 节点入口——先跑对象歧义门，命中则直接构造 `ClarifyAsk`（同 `clarification/core.py:828` 返回形），走既有 `_suspend`（:237）挂起；**不调澄清 LLM**。
- 帧：复用 `ASK_KIND_CLARIFY`（`transport/frames.py:58 _check_ask` 形状把守天然兼容），options 恰 2~4 闭世界天然满足。
- prompt/option 逐字稿：

```
prompt: 这道题问的是「{术语或指标名}」——系统里有多个油田的数据。请确认要查哪一个：
options: [油田实例1, 油田实例2, 油田实例3, "都要（分源对比）"]
```

（实例 <3 时按实际个数；prompt 中术语取 names[0]。）

- 选项→主体映射：发射时把候选名单存 `state.pending_ask` 的 `detail` 字段之外的**新 state 字段** `pending_subject_options: tuple[str,...]`（models.py additive）；恢复时 `orchestration/runtime.py:308 _apply_choice` → 澄清消费前，由编排把选中项写入 `state.subjects`：选「都要（分源对比）」→ `state.subjects = ("__all_fields__",)`（哨兵，下游分源逻辑认这个值＝全油田）；选实例 → `state.subjects = (实例,)`。写后清 `pending_subject_options`，继续正常澄清流。
- 哨兵字面量逐字：`__all_fields__`（常量单点，tools 或 state 常量均可，禁止散写字面）。

## 测试

- 门四分支：无主体+粒度要求+实例≥2 → 弹（prompt/options 逐字断言）；已给 subjects → 不弹；粒度不要求（如纯术语解释）→ 不弹；实例<2 → 不弹。
- 恢复三分支：选实例 → subjects=(实例,)；选都要 → 哨兵；ask 预算到顶 → 不弹（走原路）。
- 全链黑盒：理解（无主体）→ 编排弹 ask → 挂起帧四键 → resume 选实例 → subjects 落状态。
- **golden 回归风险题**（「产量完成率是多少？」类无主体聚合题）若因粒度要求主体而改道 ask → 逐题记录清单报主窗（**不自行豁免、不自行回退**）。

## 验收

- 相关 pytest 全绿；全量 `pytest -q` 无新增红；
- 弹 ask 路径零澄清 LLM 调用（黑盒断言）。

## 非目标

- 不改 LLM 侧澄清合同文本；不动 preconditions 既有位 2/3/4；不做「都要」之后的下游分源装配改造（本票只落 subjects，消费面后续批）。
