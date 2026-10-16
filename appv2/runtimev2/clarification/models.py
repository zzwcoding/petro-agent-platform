"""澄清相位的返回位形状（`specs/clarification.md` 接口定义节 :41–:60 逐字照录）。

- `ClarifyOutcome = ClarifyAsk | ClarifyFinal | ClarifyRejection`——**单出口互斥**；
  `discover` 与「到顶截断」两形**不占返回位**（路由意图经 `state.next_intent` 交出：
  `discover→orchestration` 路由到发现步执行／截断→`answer` 收口），故实现形另含 `None`
  （「本次调用不占三返回位」的显式形——非第四种结论）。
- `ClarifyAsk.kind` 是定型常量 `Literal["clarify"]`（反问卡 → interrupt 挂起）；
- `ClarifyFinal.subtasks` 的元素类型＝`parsing.Subtask`（载荷类**物理定义点**归 `parsing`，
  `specs/parsing.md` 行为 12）——本块**不另立第二套 `Subtask`**；本规格 :51–55 的类体
  （`chain` 必填形）与 parsing 行为 11 的差异已由 parsing 风险 7③ 登记（阶段 7 对账）。
- `ClarifyRejection.reasons` 元素＝`ClarifyReason`（结构化拒因单条：**码**＋**原文**——
  码∈闭世界（`constants.REASON_CODES`），原文＝机器面拒文**逐字**（行为 19 的机械适配面）。

全类 `frozen=True, slots=True`（同 `parsing` 载荷类形态）；本模块零判定零 IO，只定形状与
形状把守（越界 fail-closed，不吞错、不返回哨兵）。
"""

from dataclasses import dataclass, field
from typing import Literal

from appv2.runtimev2.clarification.constants import ASK_KIND_CLARIFY, REASON_CODES
from appv2.runtimev2.parsing import Subtask


@dataclass(frozen=True, slots=True)
class ClarifyAsk:
    """反问卡（→ interrupt 挂起）：`kind` 定型 `"clarify"`；`prompt`／`options` 三键之三。"""

    kind: Literal["clarify"] = "clarify"
    prompt: str = ""
    options: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.kind != ASK_KIND_CLARIFY:  # 定型常量——越界即拒（不猜、不取默认）
            raise ValueError(f"ClarifyAsk.kind 必须为 {ASK_KIND_CLARIFY!r}：{self.kind!r}")


@dataclass(frozen=True, slots=True)
class ClarifyFinal:
    """定案（→ 进下一相位 `tool_matching`）：带子问题清单。"""

    subtasks: list[Subtask]


@dataclass(frozen=True, slots=True)
class ClarifyReason:
    """结构化拒因单条：`code` 闭世界＋`reason` 机器面原文（解析拒文逐字／本块机器文案）。"""

    code: str
    reason: str

    def __post_init__(self) -> None:
        if self.code not in REASON_CODES:
            codes = "／".join(sorted(REASON_CODES))
            raise ValueError(f"ClarifyReason.code 越界（闭世界＝{codes}）：{self.code!r}")
        if not self.reason:
            raise ValueError("ClarifyReason.reason 不得为空（机器面原文逐字承载）")


@dataclass(frozen=True, slots=True)
class ClarifyRejection:
    """拒因回喂用（非终局）：由 `orchestration` 回喂模型、回到本相位重决策（不做自动修补）。"""

    reasons: list[ClarifyReason]

    def __post_init__(self) -> None:
        if not self.reasons:
            raise ValueError("ClarifyRejection.reasons 不得为空（拒因回喂不得空手）")


# 单出口互斥三返回位；`None`＝本次调用不占返回位（`discover`／到顶截断——意图经 `next_intent`）。
type ClarifyOutcome = ClarifyAsk | ClarifyFinal | ClarifyRejection | None
