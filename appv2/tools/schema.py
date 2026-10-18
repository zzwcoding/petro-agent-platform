"""tools.schema —— 工具层 schema 定稿（specs/tools.md 接口定义节；票面点名随本票定稿）。

四 schema＋两伴生件（票面点名）：
- ToolDescriptor＝{name, description, args_schema(jsonschema), readonly: True}
  ——渐进披露发现面（书 5.5 三层披露之发现层：只暴露名称/一句话用途/参数
  schema/只读声明）；
- ToolContext＝{actor, budget, metric_candidates, approved_tables, run_id,
  sub_question_id}——逐调用上下文：actor＝行级注入身份（data_query→plan.actor；
  身份只从 ctx 进、不从 args 进——伪造面收口），budget＝检索送窗预算
  （doc_retrieve/graph_query→RetrievalNeed.budget），metric_candidates＝问句指标
  候选集（FX-13 一致性闸素材，runtime 规划步供给，data_query 逐字转发
  query.validate），run_id/sub_question_id＝留痕身份两键（V2-89b——编排投影注入，
  `retrieval_calls` 行的身份值源）；
- ToolResult＝{status: ok|failed|ask, observations, ask: AskFrame|None,
  error: ToolError|None}——三态构造即定型不变式：ok 无 ask/error、failed 必有
  error、ask 必有 ask（C1 slots domain 同款纪律）；
- AskFrame＝{kind: clarify|external_table_approval, prompt, options, detail}
  ——detail＝审批卡素材（approval_id/scene/title/reason/impact，A1 帧 15 形状
  透传，resume 留痕必需——specs 注记三字段之外的定稿补充，票面验收有查）；
- ToolError＝{category: retryable|bad_args|refused, message, hint}——错误三
  分类（行为约定 3：超时/上游抖动→retryable；计划或参数错→bad_args；闸拒→
  refused）；
- Observation＝{content, source, source_id, version, freshness, scope, locator}
  ——统一观察（INV-1 的输入）：来源链必带（台账行/fragment→report→library/
  表名），locator 机读（kind 键分型：ledger 卡/agg_row/lineage/fragment/graph/
  notice）。knowledge Evidence 同形位映射＝content←value、source_id←
  element_id、locator←source（V2-02 票面留位，本票落定）。
  **locator 结构化载荷槽**（2026-10-17 EB2）：血缘卡五要素以
  `locator.payload` 结构化随观察走（键名单点见下方 `LOCATOR_PAYLOAD_KEY` 族）
  ——消费面＝`runtimev2.context`（材料段合成口径行）与 `runtimev2.execution`
  （`observation` 帧载荷透传前端）；两处只引本处名字。

零 I/O、零第三方依赖（纯 stdlib dataclass）。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# ---------- ToolResult.status 三态闭世界 ----------

STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_ASK = "ask"
STATUS_ALL: frozenset[str] = frozenset({STATUS_OK, STATUS_FAILED, STATUS_ASK})

# ---------- ToolError.category 三分类闭世界（行为约定 3） ----------

CATEGORY_RETRYABLE = "retryable"  # 超时/上游抖动——可同参重试一次
CATEGORY_BAD_ARGS = "bad_args"  # 计划或参数错——修参重试
CATEGORY_REFUSED = "refused"  # 闸拒（无据/越权口径）——不重试
CATEGORY_ALL: frozenset[str] = frozenset(
    {CATEGORY_RETRYABLE, CATEGORY_BAD_ARGS, CATEGORY_REFUSED}
)

# ---------- AskFrame.kind 闭世界 ----------

ASK_CLARIFY = "clarify"  # 缺参反问（askback 时间窗三选一）
ASK_EXTERNAL_TABLE_APPROVAL = "external_table_approval"  # 外表越集审批
ASK_KINDS: frozenset[str] = frozenset({ASK_CLARIFY, ASK_EXTERNAL_TABLE_APPROVAL})


# ---------- 观察 locator 结构化载荷槽（2026-10-17 EB2：血缘卡五要素） ----------
# 键名单点：生产面＝本包 `handlers`（血缘观察装配），消费面＝`runtimev2.context`
# （材料段合成一行口径行）与 `runtimev2.execution`（`observation` 帧载荷透传前端）。
# 两侧只引本处名字（经本包包根转出）——禁第二份字面。五要素子键＝血缘卡合同键
# 本身（取值真源 `appv2.query.domain` `LINEAGE_KEY_*`，生产面按契约键装配）。

LOCATOR_PAYLOAD_KEY = "payload"      # locator 结构化载荷槽（嵌套映射）
LINEAGE_PAYLOAD_KEY = "lineage"      # 血缘卡载荷（键＝五要素合同键、值＝该行原文）
LINEAGE_LIMIT_KEY = "limit"          # 限量面（LIMIT 触顶事实——口径行尾缀的原料）
LINEAGE_LIMIT_HIT_KEY = "hit"        # LIMIT 是否触顶（整窗 SUM／非行数限量型恒 False）
LINEAGE_LIMIT_ROWS_KEY = "rows"      # 本次限量内交付行数（未触顶＝0）
# 实际取数窗标签（2026-10-18 V2-107 additive：载荷兄弟键）——答案面日期标注的**唯一**
# 只读取值口；值＝`query.domain.TimeWindow.label`（生产单点＝血缘③行、读回单点＝
# `query.lineage_filter_window_label`——**不另算窗**）。缺位／空串＝无实际窗可标（不猜）。
LINEAGE_WINDOW_LABEL_KEY = "window_label"


@dataclass(frozen=True, slots=True)
class ToolDescriptor:
    """工具描述卡（渐进披露发现面——registry 只透出这四个字段）。"""

    name: str
    description: str
    args_schema: Mapping[str, Any]  # JSON Schema 常用子集（argscheck 校验器消费）
    readonly: bool = True  # INV-2——registry 拒绝注册 readonly!=True 的工具


@dataclass(frozen=True, slots=True)
class ToolContext:
    """逐调用上下文（身份/预算/候选集/外表放行态——运行策略归调用方，不进 args）。

    approved_tables（V2-34 任务 8——A2 裁决落点；P-051b 审查③注记改型随实现
    同步）：外表越集放行名单/审批态（批准过的表名集）——放行态放工具上下文，
    并随执行进引擎 approved_tables（data_query 传参——已批表放行续跑，批准后
    重执行零二次挂审批；未批子集照挂），不重排计划；前置条件机按同一状态判
    外表越集闸（runtime 侧 state.approved_ids 同源）。

    budget（V2-45 R1a 送窗预算动态化）：检索送窗预算 M（doc_retrieve/graph_query
    →RetrievalNeed.budget）——runtime 侧经 resolve_send_budget 按调用上下文赋值
    （问题组子问题数×基线 6、上限 24）；本 schema 缺省 4 保留给直接构造面
    （测试/旧调用形），生产运行面不再落硬编码。

    run_id／sub_question_id（V2-89b 留痕身份——`retrieval_calls` 行的两身份键
    值源，`tools.retrieval_calllog` 消费）：由编排投影（`runtimev2.bookkeeping
    .projection.tool_context`）从**状态**注入，不从 args 进（伪造面收口同
    actor）。缺省空串＝旧构造面零漂移（如实留白，不发明身份）。
    """

    actor: str = ""  # 行级注入身份（data_query→plan.actor；两步缝第一步）
    budget: int = 4  # 检索送窗预算 M（RetrievalNeed.budget——截断显式的 M）
    metric_candidates: tuple[str, ...] | None = None  # FX-13 候选集（None＝不启用）
    approved_tables: tuple[str, ...] = ()  # 外表放行态（A2 裁决——批准过的表名集）
    run_id: str = ""  # 运行身份（V2-89b——编排投影注入；留痕行 run_id 值源）
    sub_question_id: str = ""  # 子问题身份（V2-89b——编排投影注入；逐支归因）

    def __post_init__(self) -> None:
        if isinstance(self.budget, bool) or not isinstance(self.budget, int):
            raise ValueError(f"ToolContext.budget 须为整数：{self.budget!r}")
        if self.budget < 1:
            raise ValueError(f"ToolContext.budget 须 ≥1：{self.budget!r}")


# ---------- 送窗预算动态化（V2-45 R1a——ToolContext.budget 赋值规则单点） ----------

# 每子问题基线（票面「如每子问题基线 6」）与多子问题组上限（票面「上限 24」）。
# 旧缺省 4（本文件 ToolContext.budget 字面值——动态化前的硬编码）由单支基线
# 6 自然覆盖（只扩不缩），不另设下限常量。
SEND_BUDGET_PER_SUBTASK = 6
SEND_BUDGET_CAP = 24

# 按来源取节／取篇的字符上界（V2-96 D5 `fetch_cap`——数值单点；真源 §五·5.4
# 「受 `fetch_cap` 与截断披露」）。`fetch_report` 的 `max_chars` 缺省取本值；
# 超界必截断＋披露（判据与话术在 `retrieval.domain`／`retrieval.engine`）。
FETCH_CAP_CHARS = 6000


def resolve_send_budget(subtask_count: int) -> int:
    """送窗预算动态化（每次 doc_retrieve/graph_query 调用的送窗预算 M）。

    M＝每子问题基线 6 × 问题组子问题数（至少按 1 支计），上限 24——长题干
    多子问题组的检索配额随子问题数扩（batch 相位逐支执行各自调用，组尺寸
    是逐支共享的调用上下文）；单支问句 6（≥ 旧缺省 4，只扩不缩）。

    表格/明细类的「整行集优先」不在本数值面——其目标表格所在片段整组由供给
    层追加进窗、不计入 M（appv2.retrieval.domain.supply_window 的 rowset 通道，
    题面词面判定归检索域）。
    """
    count = max(1, int(subtask_count))
    return min(SEND_BUDGET_CAP, SEND_BUDGET_PER_SUBTASK * count)


@dataclass(frozen=True, slots=True)
class ToolError:
    """工具错误（三分类闭世界——构造即拒越界）。"""

    category: str  # CATEGORY_* 三值
    message: str
    hint: str | None = None  # 处置指引（可重试/修参/不重试转人工）

    def __post_init__(self) -> None:
        if self.category not in CATEGORY_ALL:
            raise ValueError(
                f"ToolError.category 越界（三分类闭世界 {sorted(CATEGORY_ALL)}）："
                f"{self.category!r}"
            )


@dataclass(frozen=True, slots=True)
class AskFrame:
    """ASK 帧（agent 挂起等人工的两形态——缺参反问/外表越集审批）。

    detail＝审批卡素材透传（A1 帧 15 合同形状：approval_id/scene/title/reason/
    impact/audit_hint——approval_id 供 resume 留痕必需；clarify 态 detail＝None）。
    """

    kind: str  # ASK_* 两值闭世界
    prompt: str
    options: tuple[str, ...] = ()  # 选项（clarify＝三选一；审批＝批准/驳回）
    detail: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.kind not in ASK_KINDS:
            raise ValueError(
                f"AskFrame.kind 越界（闭世界 {sorted(ASK_KINDS)}）：{self.kind!r}"
            )


@dataclass(frozen=True, slots=True)
class Observation:
    """统一观察（specs/tools.md 接口定义节原形——agent 与世界接触的素材单元）。

    来源链必带（INV-1 的输入）：台账行（source＝sem_*#行 id）、权威表行
    （source/locator.table＝表名）、检索支（fragment→report→library 三级）；
    locator 恒机读（kind 键分型＋定位键）；well＝切片本体标签（V2-64——检索支
    透传 kb_fragment.well；其余观察缺省 None，装配面按缺省省略）。
    locator 取值面＝机读定位键（字符串）＋**结构化载荷槽** `payload`（嵌套映射——
    血缘卡五要素，2026-10-17 EB2；消费面按槽名取，不解析观察正文文本串）。
    """

    content: str
    source: str
    source_id: str
    version: str | None
    freshness: str
    scope: str
    locator: Mapping[str, Any]
    well: str | None = None


@dataclass(frozen=True, slots=True)
class ToolResult:
    """工具统一出口（三态构造即定型：ok 无 ask/error、failed 必有 error、ask 必有 ask）。"""

    status: str  # STATUS_* 三值闭世界
    observations: tuple[Observation, ...]
    ask: AskFrame | None
    error: ToolError | None

    def __post_init__(self) -> None:
        if self.status not in STATUS_ALL:
            raise ValueError(
                f"ToolResult.status 越界（三态闭世界 {sorted(STATUS_ALL)}）：{self.status!r}"
            )
        if self.status == STATUS_OK and (self.ask is not None or self.error is not None):
            raise ValueError("ToolResult status=ok 不得携带 ask/error")
        if self.status == STATUS_FAILED and self.error is None:
            raise ValueError("ToolResult status=failed 必携 error（三分类）")
        if self.status == STATUS_ASK and self.ask is None:
            raise ValueError("ToolResult status=ask 必携 AskFrame")

    @classmethod
    def ok(cls, observations: Sequence[Observation] = ()) -> ToolResult:
        return cls(STATUS_OK, tuple(observations), None, None)

    @classmethod
    def failed(
        cls,
        category: str,
        message: str,
        *,
        hint: str | None = None,
        observations: Sequence[Observation] = (),
    ) -> ToolResult:
        return cls(
            STATUS_FAILED, tuple(observations), None,
            ToolError(category=category, message=message, hint=hint),
        )

    @classmethod
    def ask_frame(
        cls, frame: AskFrame, *, observations: Sequence[Observation] = ()
    ) -> ToolResult:
        return cls(STATUS_ASK, tuple(observations), frame, None)


# 工具执行器形状（handler 签名——registry 调出口唯一消费形）。
ToolHandler = Callable[[dict[str, Any], ToolContext], Awaitable[ToolResult]]


@dataclass(frozen=True, slots=True)
class Tool:
    """注册项（描述卡＋执行器捆绑——registry.register 的入参单元）。"""

    descriptor: ToolDescriptor
    handler: ToolHandler
