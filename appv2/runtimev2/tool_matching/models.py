"""tool_matching 的形状层：`ToolPlan`／`RetrievalNeed`／`ToolMatchRejection`／`MatchReason`
（`SubtaskMatch` 形状单点在 `parsing`——本块**导入消费**，不重定义：`specs/parsing.md` 行为 12
「载荷类形状单点（消费面不重定义）」／P-05 单点归位 2026-10-16）。

真源＝`specs/tool_matching.md`（已定稿）「接口定义」节；卡 `specs/modules.md` `## tool_matching`
（签名以卡为准）。本层纯形状＋**闭世界 fail-closed 把守**（越界构造即抛错——不吞错、不取默认），
零行为分支、零 IO、零模型调用、零状态写入；把守面＝**本块自有类**（`ToolPlan`／`MatchReason`／
`ToolMatchRejection`）——`SubtaskMatch` 的形状与把守分家：形状归 `parsing`（纯装载），
取值闭世界（`mention_mode` 等）归消费面 `matching` 对账。

两处**只引不复述**：
- `plan` 的形状真源＝`specs/query.md` 的 `QueryPlan`（十字段）——本块**不复述其字段**，且守 R6
  不直引查询引擎，故以**映射**（`dict[str, Any]`）承载；
- `tool` 的取值真源＝tools 公开面的注册表名单（本块只判「在册且对上链」，见 `matching`）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from appv2.runtimev2.parsing import SubtaskMatch as SubtaskMatch
from appv2.runtimev2.tool_matching.constants import MATCH_REASON_KINDS


def _reject(field_name: str, value: object, world: frozenset[str]) -> ValueError:
    """闭世界越界（fail-closed）——不吞错、不返回哨兵值、不静默降级。"""
    values = "／".join(sorted(world))
    return ValueError(f"{field_name} 越界（闭世界＝{values}）：{value!r}")


@dataclass(frozen=True, slots=True)
class RetrievalNeed:
    """知识链检索参数（`retrieval_need`）：`question` 必填、`anchors` 可选。

    公开面保留（族名单闭世界，`specs/tool_matching.md` 接口定义）；**形状载体归 `parsing`**：
    `SubtaskMatch.retrieval_need` 以映射承载（P-05 单点归位后本类不再作字段类型/构造点）。
    """

    question: str
    anchors: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ToolPlan:
    """本相位定案：`matches` 与子问题**一一对应**（条数＝子问题条数）——空数组不成立。"""

    matches: list[SubtaskMatch]

    def __post_init__(self) -> None:
        if not self.matches:
            raise ValueError("ToolPlan.matches 空（每子问题恰一条匹配——空数组不成立）")


@dataclass(frozen=True, slots=True)
class MatchReason:
    """结构化拒因单条：`kind` 六类闭世界（成员名照规格 `:66`）＋ `reason` 拒文。

    `reason` 的逐字链：解析面拒文 → 本块**逐字**填入（行为 11），不摘要、不改写、不换措辞。
    """

    kind: str
    reason: str

    def __post_init__(self) -> None:
        if self.kind not in MATCH_REASON_KINDS:
            raise _reject("MatchReason.kind", self.kind, MATCH_REASON_KINDS)
        if not self.reason:
            raise ValueError("MatchReason.reason 空（拒文逐字非空——行为 11）")


@dataclass(frozen=True, slots=True)
class ToolMatchRejection:
    """结构化拒因（**回喂用，非终局**）：由 `orchestration` 回喂模型、回到本相位重配。

    **不得静默丢子问题**：漏配即判失败，不许「当作已配」或跳过该子问题（红线 A-P7a-37）。
    """

    reasons: list[MatchReason]

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError("ToolMatchRejection.reasons 空（失败必带结构化拒因）")
