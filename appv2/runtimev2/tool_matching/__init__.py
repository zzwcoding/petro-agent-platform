"""工具匹配：子问题 → 工具的提议与闭世界对账；「出数只认现行口径」结构约束落点

模块卡见 `specs/modules.md` 的 `## tool_matching` 一节；规格见 `specs/tool_matching.md`
（形状与行为真源）；架构图见 docs/architecture-v3.html。包根即公开面（R2：消费方只经
`appv2.runtimev2.tool_matching` 消费，深层子模块私有）——**族名单闭世界**（规格「接口定义」节）：

- 相位单入口：`match`（返回两态互斥：`ToolPlan`｜`ToolMatchRejection`）；
- 定型类五件：`ToolPlan`（matches 与子问题一一对应）／`SubtaskMatch`（含 `mention_mode`
  ——「提及 vs 执行」结论，pin-31 判断产出面）／`RetrievalNeed`／`ToolMatchRejection`／
  `MatchReason`（`kind` 六类闭世界＋逐字拒文）；
- 闭世界常量族：`MATCH_REASON_KINDS`／`KIND_*`（六类）／`MENTION_MODES`／`MENTION_*`／
  `DIRECTIONS`／`DATA_CHAIN`／`KNOWLEDGE_CHAIN`（chain 两值别名转出，取值真源＝`parsing` 单点）
  ／`REJECTION_KIND_BY_MARK`（解析面逐字拒文 → 拒因枚举的机械适配表，行为 11）；
- 接线字面：`MODEL_CALLER`／`PHASE`。

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
