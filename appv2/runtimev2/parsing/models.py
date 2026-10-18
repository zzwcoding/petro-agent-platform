"""载荷定型类（三面解析的产物形状）——本块为五类形状的**物理定义点**（`specs/parsing.md` 行为 12：
`Understanding`／`Direct`／`Subtask`／`QuestionGroup`／`SubtaskMatch`）＋V1 发射定形
`ClarifyEmission`（行为 11）＋V2-96 作答第二出口定形 `Explore`（§五·5.1）。

- `Understanding`／`Direct`：字段集以 `specs/understanding.md` 接口定义为准
  （`text`／`metric_candidates`／`route`）——`route` 是定型常量，**不设类定义默认值**
  （缺必填字段即由消费方 `understanding` 走「拒因回喂恰一次；仍拒＝收敛拒答」修正回路——
  2026-10-17 EB3 D4.4 改判，`UnderstandingParseError` 退出该支出口）。
- `Subtask`／`QuestionGroup`／`ClarifyEmission`／`SubtaskMatch`：V1 字段表逐字迁移
  （真源 `appv2/runtime/subtask.py` L116-L176／L296-L315）——承载位换、字段名与形状不变；
  **`Subtask.tool` 退场**（Owner 裁决 #10：`tool` 归匹配相位产出）。
- `SubtaskMatch.mention_mode`＝「提及 vs 执行」结论的字段载体（闭世界 `executed`／`mentioned_only`，
  真源 `specs/tool_matching.md` 接口定义）——本类**纯装载**、不判取值：缺与越界由消费方
  （`tool_matching` 对账面）拒；**2026-10-16 增（流水 50 裁／P-05 单点归位）**。
- 投影规则（`as_payload`）逐字迁移（真源同上 L126-L136／L145-L146／L161-L176／L307-L315）：
  恒带键照抄、空值键不出现；`ask` 段以 `ask_prompt` 真假**单点**开闸（`ask_options` 单有值
  静默消失——V1 事实面 D-L1a-04）。全类 `frozen=True, slots=True`。
- `SubtaskMatch.mention_mode` 的投影同 `caliber_key` 面＝**真值才出键**（空串＝未装载，键不出现
  ——消费面 `preconditions` 以 `.get()` 空串缺省读法等价取用；**2026-10-16 增**：pin-31 断供
  修复，使「提及 vs 执行」结论经 `as_payload` 投影到得了 `state.tool_matches`）。

本模块零判定、零 IO：拒因与校验在 `parsers`，本处只定形状与投影。
"""

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class Understanding:
    """读题结论（`route="full"`）——字段集真源 `specs/understanding.md` 接口定义。

    `subjects`／`terms`＝**2026-10-17 V2-82a additive**（题面主体／术语的结构化槽；
    解析层宽松：缺省／类型不合＝空元组、不拒单；默认空＝零漂移）。
    """

    text: str
    metric_candidates: list[str]
    route: Literal["full"]
    subjects: tuple[str, ...] = ()
    terms: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Direct:
    """无业务直答（`route="direct"`）——字段集真源 `specs/understanding.md` 接口定义。

    字段集与 `Understanding` **同步**（V2-82a）：两形同持 `subjects`／`terms` 槽（直答
    形下恒空——直答无题面主体/术语；形状单点仍是本类）。
    """

    text: str
    route: Literal["direct"]
    subjects: tuple[str, ...] = ()
    terms: tuple[str, ...] = ()


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
class Explore:
    """作答第二出口定型载荷（V2-96 D5——`{"action":"explore","reason":…,"requests":[…]}`）。

    字段集真源＝`docs/runtime-refactor/接手-召回全链路最终决议与运行流程-20261018.md` §五·5.1：
    `reason`（非空——材料不足的说明）＋`requests`（1..2 条，逐条 `tool` 闭世界三值＋工具必填参）。
    `raw`＝模型整枚 JSON 原文（**照抄面**——增量消息「模型上一轮 requests 原文」的载体；
    空串＝测试直造形，消费方回落 `requests` 的 JSON 序列化）。本类**纯装载**、不判取值：
    闭世界与必填由 `parsers.parse_explore` 拒，本处只定形状与投影。
    """

    reason: str
    requests: tuple[dict[str, Any], ...] = ()
    raw: str = ""

    def as_payload(self) -> dict[str, Any]:
        """状态／步 payload 投影（键恒在场；`requests` 逐条浅拷——返回容器零共享）。"""
        return {
            "reason": self.reason,
            "requests": [dict(item) for item in self.requests],
            "raw": self.raw,
        }


@dataclass(frozen=True, slots=True)
class SubtaskMatch:
    """子问题→工具链定案（相位②产物——下游前置条件块与批量执行的输入）。

    `mention_mode`＝「提及 vs 执行」结论的字段载体（闭世界 `executed`／`mentioned_only`——
    真源 `specs/tool_matching.md` 接口定义；**2026-10-16 增（流水 50 裁／P-05 单点归位）**）：
    本类**纯装载**、不判取值——缺与越界由消费方（`tool_matching` 对账面）拒；空串＝未装载
    （投影里空值键不出现——同 `caliber_key` 面）。
    """

    id: str
    chain: str
    tool: str
    plan: dict[str, Any] | None = None
    retrieval_need: dict[str, Any] | None = None
    caliber_key: str = ""  # B5：场景词落定的口径支 key（可空）
    mention_mode: str = ""  # 闭世界 executed／mentioned_only（取值真源 specs/tool_matching.md）

    def as_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"id": self.id, "chain": self.chain, "tool": self.tool}
        if self.plan is not None:
            payload["plan"] = dict(self.plan)
        if self.retrieval_need is not None:
            payload["retrieval_need"] = dict(self.retrieval_need)
        if self.caliber_key:
            payload["caliber_key"] = self.caliber_key
        if self.mention_mode:
            payload["mention_mode"] = self.mention_mode
        return payload
