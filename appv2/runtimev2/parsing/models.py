"""载荷定型类（三面解析的产物形状）——本块为五类形状的**物理定义点**（`specs/parsing.md` 行为 12：
`Understanding`／`Direct`／`Subtask`／`QuestionGroup`／`SubtaskMatch`）＋V1 发射定形
`ClarifyEmission`（行为 11）。

- `Understanding`／`Direct`：字段集以 `specs/understanding.md` 接口定义为准
  （`text`／`metric_candidates`／`route`）——`route` 是定型常量，**不设类定义默认值**
  （缺必填字段即由消费方 `understanding` 抛 `UnderstandingParseError`）。
- `Subtask`／`QuestionGroup`／`ClarifyEmission`／`SubtaskMatch`：V1 字段表逐字迁移
  （真源 `appv2/runtime/subtask.py` L116-L176／L296-L315）——承载位换、字段名与形状不变；
  **`Subtask.tool` 退场**（Owner 裁决 #10：`tool` 归匹配相位产出）。
- 投影规则（`as_payload`）逐字迁移（真源同上 L126-L136／L145-L146／L161-L176／L307-L315）：
  恒带键照抄、空值键不出现；`ask` 段以 `ask_prompt` 真假**单点**开闸（`ask_options` 单有值
  静默消失——V1 事实面 D-L1a-04）。全类 `frozen=True, slots=True`。

本模块零判定、零 IO：拒因与校验在 `parsers`，本处只定形状与投影。
"""

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class Understanding:
    """读题结论（`route="full"`）——字段集真源 `specs/understanding.md` 接口定义。"""

    text: str
    metric_candidates: list[str]
    route: Literal["full"]


@dataclass(frozen=True, slots=True)
class Direct:
    """无业务直答（`route="direct"`）——字段集真源 `specs/understanding.md` 接口定义。"""

    text: str
    route: Literal["direct"]


@dataclass(frozen=True, slots=True)
class Subtask:
    """子问题（问题组最小单元——id／问题／台账注释＋工具链提议）。"""

    id: str
    question: str
    ledger_notes: str
    chain: str = ""  # 提议（可空——相位②收口定案）

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "question": self.question,
            "ledger_notes": self.ledger_notes,
        }
        if self.chain:
            payload["chain"] = self.chain
        return payload


@dataclass(frozen=True, slots=True)
class QuestionGroup:
    """问题组（相位①产物——带台账注释的子任务图）。"""

    subtasks: tuple[Subtask, ...]

    def as_payload(self) -> dict[str, Any]:
        return {"subtasks": [subtask.as_payload() for subtask in self.subtasks]}


@dataclass(frozen=True, slots=True)
class ClarifyEmission:
    """相位①发射（四动作闭世界的定型形——step payload 断言面）。"""

    kind: str  # discover|decompose|ask|finalize
    group: QuestionGroup | None = None
    discovers: tuple[dict[str, Any], ...] = ()
    ask_prompt: str = ""
    ask_options: tuple[str, ...] = ()
    thought: str = ""
    note: str = ""

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"action": self.kind}
        if self.thought:
            payload["thought"] = self.thought
        if self.note:
            payload["note"] = self.note
        if self.group is not None:
            payload["question_group"] = self.group.as_payload()
        if self.discovers:
            payload["discovers"] = [dict(item) for item in self.discovers]
        if self.ask_prompt:
            payload["ask"] = {
                "prompt": self.ask_prompt,
                "options": list(self.ask_options),
            }
        return payload


@dataclass(frozen=True, slots=True)
class SubtaskMatch:
    """子问题→工具链定案（相位②产物——下游前置条件块与批量执行的输入）。"""

    id: str
    chain: str
    tool: str
    plan: dict[str, Any] | None = None
    retrieval_need: dict[str, Any] | None = None
    caliber_key: str = ""  # B5：场景词落定的口径支 key（可空）

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"id": self.id, "chain": self.chain, "tool": self.tool}
        if self.plan is not None:
            payload["plan"] = dict(self.plan)
        if self.retrieval_need is not None:
            payload["retrieval_need"] = dict(self.retrieval_need)
        if self.caliber_key:
            payload["caliber_key"] = self.caliber_key
        return payload
