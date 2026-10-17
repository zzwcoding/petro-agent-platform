"""工具匹配：子问题 → 工具的提议与闭世界对账；「出数只认现行口径」结构约束落点

模块卡见 `specs/modules.md` 的 `## tool_matching` 一节；规格见 `specs/tool_matching.md`
（形状与行为真源）；架构图见 docs/architecture-v3.html。包根即公开面（R2：消费方只经
`appv2.runtimev2.tool_matching` 消费，深层子模块私有）——**族名单闭世界**（规格「接口定义」节）：

- 相位单入口：`match(state, *, guide_text="", shared_context=True)`（返回**三形互斥**：`ToolPlan`｜
  `ToolPlan(matches=[], converged=True)`（**收敛让位形**：run 已触界收敛 → 零模型调用、零定案，
  交下游既有「无支可执行 → 作答收口」路由落答——行为 9，2026-10-17 EB3 D4.3 补）｜
  `ToolMatchRejection`；`guide_text`＝§A 指南段文本注入参——流水 63，编排面按启动快照注入，缺省
  空串＝空段头；`shared_context`＝run 级共享上下文（§A 指南段＋台账常驻块）本次是否注入——
  判定归编排面〔同 run 只注一次，挂澄清轮首入包〕，本块只下传）；
- 定型类五件：`ToolPlan`（matches 与子问题一一对应）／`SubtaskMatch`（含 `mention_mode`
  ——「提及 vs 执行」结论，pin-31 判断产出面）／`RetrievalNeed`／`ToolMatchRejection`／
  `MatchReason`（`kind` 六类闭世界＋逐字拒文）；
- 闭世界常量族：`MATCH_REASON_KINDS`／`KIND_*`（六类）／`MENTION_MODES`／`MENTION_*`／
  `DIRECTIONS`／`DATA_CHAIN`／`KNOWLEDGE_CHAIN`（chain 两值别名转出，取值真源＝`parsing` 单点）
  ／`REJECTION_KIND_BY_MARK`（解析面逐字拒文 → 拒因枚举的机械适配表，行为 11）；
- 接线字面：`MODEL_CALLER`／`PHASE`。

**同形拒因熔断（行为 9，2026-10-17 EB3 D4.3）**：拒因回喂自环不再只靠轮数闸（自环不经澄清入口，
轮数闸到不了）——每次拒因**占一轮** ＋ 拒因回喂 `decision_error` ＋ 同形拒因（`kind`＋逐字拒文）
既有次数 ≥ **熔断参数**（`constants.RETRY_CAP_SAME_REJECTION`＝`2`；该参数**不在本包公开面**——
同 `clarification.constants.REJECT_FREE_STREAK` 体例，公开面名单以规格「接口定义」节为准）时
**触界收敛**（显式顶轮到 `Budget.rounds` → `bookkeeping.converge` 落 `budget_converged`＋材料直答
＋`status=completed`），收敛后入口返**收敛让位形**（零模型调用）；配套执行面「收敛态零派遣」
（`specs/execution.md` 行为 16）。

**分工**：模型只提议（子问题 → 工具 ＋ 参数 ＋ `mention_mode`／`caliber_key` 两个结论）；
程序做闭世界对账（存在性／一致性／枚举三类结构判定），**绝不替模型选工具**——判据全在
`matching` 单点，机检面＝
`tests/domains/test_v2_tool_matching.py::no_lexicon_or_regex_in_tool_matching`。

**边界**（规格「框架与依赖红线」＋卡「依赖」）：无点名框架（R5b）；模型调用经
`bookkeeping.call_model` 单点发起、本块不直引 `gateway_adapter`（R7——import 落点＝
`appv2.runtimev2.bookkeeping` 包根）；只经 `tools` 公开面接触世界（R6）；不引旧码
`appv2.runtime`（R5）；不 import 其它相位（R1）。**相位不直写状态**：写面全经 `bookkeeping`
唯一写口（`append_message`／`append_contract`／`record_step`／`notice`），模型调用步与用量记账
由 `call_model` 单点统一记账（本块不为同一调用重复记步）。
"""

from appv2.runtimev2.tool_matching.constants import (
    DATA_CHAIN,
    DIRECTIONS,
    KIND_DUPLICATE,
    KIND_ENUM_OUT_OF_RANGE,
    KIND_MALFORMED,
    KIND_MISSING_REQUIRED,
    KIND_MISSING_SUBTASK,
    KIND_UNKNOWN_ID,
    KNOWLEDGE_CHAIN,
    MATCH_REASON_KINDS,
    MENTION_EXECUTED,
    MENTION_MENTIONED_ONLY,
    MENTION_MODES,
    MODEL_CALLER,
    PHASE,
    REJECTION_KIND_BY_MARK,
)
from appv2.runtimev2.tool_matching.matching import match
from appv2.runtimev2.tool_matching.models import (
    MatchReason,
    RetrievalNeed,
    SubtaskMatch,
    ToolMatchRejection,
    ToolPlan,
)

__all__ = [
    "DATA_CHAIN",
    "DIRECTIONS",
    "KIND_DUPLICATE",
    "KIND_ENUM_OUT_OF_RANGE",
    "KIND_MALFORMED",
    "KIND_MISSING_REQUIRED",
    "KIND_MISSING_SUBTASK",
    "KIND_UNKNOWN_ID",
    "KNOWLEDGE_CHAIN",
    "MATCH_REASON_KINDS",
    "MENTION_EXECUTED",
    "MENTION_MENTIONED_ONLY",
    "MENTION_MODES",
    "MODEL_CALLER",
    "PHASE",
    "REJECTION_KIND_BY_MARK",
    "MatchReason",
    "RetrievalNeed",
    "SubtaskMatch",
    "ToolMatchRejection",
    "ToolPlan",
    "match",
]
