"""解析与发射：模型输出解析、发射 schema 校验、子任务与问题组载荷定型

模块卡见 `specs/modules.md` 的 `## parsing` 一节；规格见 `specs/parsing.md`（形状与行为真源）；
架构图见 docs/architecture-v3.html。包根即公开面（R2：三个业务相位只许经 `appv2.runtimev2.parsing`
消费，深层子模块私有）——**族名单闭世界**（`specs/parsing.md` 接口定义节 :39-:80）：

- 三面解析器族：`parse_understanding`（统一 JSON 严格解析）／`parse_question_group`（四动作闭世界
  ＋分派）／`parse_tool_match`（`matches` ↔ 问题组闭合世界对账）；
- 共用件族四件：`extract_plan_json`／`json_syntax_feedback`／`repair_inner_quotes`／
  `parse_with_quote_repair`（单点——相位块零字面副本）；
- 载荷定型类：`Understanding`／`Direct`／`Subtask`／`QuestionGroup`／`ClarifyEmission`／
  `SubtaskMatch`（行为 11／行为 12）；
- 指纹器材四件：`payload_fingerprint`／`discover_fingerprint`／`emission_fingerprints`／
  `is_same_param_replay`。

**返回三态闭世界**：定型载荷｜拒因正文（`str`）｜`None`（无回喂形）。本块不抛业务异常、不吞错；
纯结构判定（零词表零正则语义判定）、零模型调用／零 IO／零时钟／零随机／零事件／零状态写入
（唯一 `state` 接触＝限额参数的注入面与指纹簿记字段的形状——只消费、零写入）。
"""

from appv2.runtimev2.parsing.constants import (
    BUDGET_REJECT_MARK,
    CHAIN_DATA,
    CHAIN_KINDS,
    CHAIN_KNOWLEDGE,
    CLARIFY_ACTIONS,
    CLARIFY_ASK,
    CLARIFY_DECOMPOSE,
    CLARIFY_DISCOVER,
    CLARIFY_FINALIZE,
    ROUTE_DIRECT,
    ROUTE_FULL,
    TOOL_DATA_QUERY,
    TOOL_DOC_RETRIEVE,
)
from appv2.runtimev2.parsing.fingerprints import (
    discover_fingerprint,
    emission_fingerprints,
    is_same_param_replay,
    payload_fingerprint,
)
from appv2.runtimev2.parsing.helpers import (
    extract_plan_json,
    json_syntax_feedback,
    parse_with_quote_repair,
    repair_inner_quotes,
)
from appv2.runtimev2.parsing.models import (
    ClarifyEmission,
    Direct,
    QuestionGroup,
    Subtask,
    SubtaskMatch,
    Understanding,
)
from appv2.runtimev2.parsing.parsers import (
    parse_question_group,
    parse_tool_match,
    parse_understanding,
)

__all__ = [
    "BUDGET_REJECT_MARK",
    "CHAIN_DATA",
    "CHAIN_KINDS",
    "CHAIN_KNOWLEDGE",
    "CLARIFY_ACTIONS",
    "CLARIFY_ASK",
    "CLARIFY_DECOMPOSE",
    "CLARIFY_DISCOVER",
    "CLARIFY_FINALIZE",
    "ROUTE_DIRECT",
    "ROUTE_FULL",
    "TOOL_DATA_QUERY",
    "TOOL_DOC_RETRIEVE",
    "ClarifyEmission",
    "Direct",
    "QuestionGroup",
    "Subtask",
    "SubtaskMatch",
    "Understanding",
    "discover_fingerprint",
    "emission_fingerprints",
    "extract_plan_json",
    "is_same_param_replay",
    "json_syntax_feedback",
    "parse_question_group",
    "parse_tool_match",
    "parse_understanding",
    "parse_with_quote_repair",
    "payload_fingerprint",
    "repair_inner_quotes",
]
