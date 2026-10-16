"""preconditions 的形状层：三态判定与两形理由（`specs/preconditions.md` 接口定义节逐字）。

真源＝`specs/preconditions.md` 接口定义节（`:34–:51`）／卡 `specs/modules.md` `## preconditions`
（签名以卡为准）。本层**纯形状＋闭世界把守**：零行为分支（除闭世界／配对越界即拒的 fail-closed
把守外）、零 IO、零模型、零落盘、零业务语义判断——语义判据全在上游 `tool_matching`（模型产出），
本块只做机械分派（行为 4）。

- `SubtaskVerdict`：逐子问题三态结论（`decision` 三态闭世界；`notes`＝**注记并入放行**的附加
  信息——**不是第四态**；`hit_rule`＝命中的判定位标识，非 `allow` 必携、`allow` 支空串）。
- `RefusalReason`：拒因（`rule_id` 命中的判定位／`human_text` 人话／`alternatives` 替代项）。
- `AskReason`：等用户的理由（`kind` 两形闭世界／`prompt`／`options`）——`kind` → 帧 `frame.kind`
  的唯一映射表在 `constants.FRAME_KIND_BY_ASK_KIND`（发帧归 `orchestration`／`transport`）。

**下游投影契约**（`execution` 已收票的消费面）：`as_payload()` 恒出
`subtask_id`／`decision`／`hit_rule`／`notes`／`reason` 五键，`reason` 投影携
`human_text`／`rule_id`／`prompt`／`kind`（拒因三键／等用户三键互斥）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from appv2.runtimev2.preconditions.constants import (
    ASK_KINDS,
    DECISION_ALLOW,
    DECISION_ASK,
    DECISION_REFUSE,
    DECISIONS,
)


def _reject(field: str, value: object, world: frozenset[str]) -> ValueError:
    """闭世界越界（fail-closed）——不吞错、不返回哨兵值、不静默降级。"""
    values = "／".join(sorted(world))
    return ValueError(f"{field} 越界（闭世界＝{values}）：{value!r}")


@dataclass(frozen=True, slots=True)
class RefusalReason:
    """拒答理由（接口定义节逐字）：命中的判定位 ＋ 人话 ＋ 替代项。

    `alternatives`＝替代项（如替代口径）——**口径类拒答必携**（行为 8「缺项＝判失败」的承载面）；
    本块按台账面结构化派生（`core._alternatives_of`），不按文案反推、不做词面判断。
    """

    rule_id: str
    human_text: str
    alternatives: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.rule_id:
            raise ValueError("RefusalReason.rule_id 必填（命中的判定位——可解释性契约，行为 8）")
        if not self.human_text:
            raise ValueError("RefusalReason.human_text 必填（人话原因——行为 8，缺项＝判失败）")

    def as_payload(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "human_text": self.human_text,
            "alternatives": list(self.alternatives),
        }


@dataclass(frozen=True, slots=True)
class AskReason:
    """等用户理由（接口定义节逐字）：`kind` 两形闭世界 ＋ 提示 ＋ 选项。

    `kind` 越界即拒（闭世界＝`external_table_approval`｜`caliber_clarify`——不猜、不取默认）；
    帧侧取值经 `constants.FRAME_KIND_BY_ASK_KIND` 映射，本类**只产本块侧取值**。
    """

    kind: str
    prompt: str
    options: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in ASK_KINDS:
            raise _reject("AskReason.kind", self.kind, ASK_KINDS)
        if not self.prompt:
            raise ValueError("AskReason.prompt 必填（等用户的提示——行为 8，缺项＝判失败）")

    def as_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "prompt": self.prompt,
            "options": list(self.options),
        }


@dataclass(frozen=True, slots=True)
class SubtaskVerdict:
    """逐子问题三态结论（接口定义节逐字；行为 1／5／8／10 的承载形）。

    三态闭世界 ＋ 配对把守（fail-closed）：

    - `decision="allow"`：`reason` 必空（放行不带拒因／等用户理由）；`notes` 携注记（**注记并入
      放行**——不设第四态）；`hit_rule` 空串。
    - `decision="refuse"`：`reason` 必为 `RefusalReason`（`hit_rule` 必携——行为 8）。
    - `decision="ask"`：`reason` 必为 `AskReason`（`hit_rule` 必携——位 2 时间窗／位 3 外表越集／
      位 4 口径反问）。
    """

    subtask_id: str
    decision: str
    notes: tuple[str, ...] = ()
    reason: RefusalReason | AskReason | None = None
    hit_rule: str | None = None

    def __post_init__(self) -> None:
        if not self.subtask_id:
            raise ValueError("SubtaskVerdict.subtask_id 必填（逐子问题判定的比对面——行为 1）")
        if self.decision not in DECISIONS:
            raise _reject("SubtaskVerdict.decision", self.decision, DECISIONS)
        if self.decision == DECISION_ALLOW:
            if self.reason is not None:
                raise ValueError(
                    "`allow` 不得携 reason（拒因／等用户理由与放行互斥——注记并入放行，不设第四态）"
                )
            return
        if not self.hit_rule:
            raise ValueError(
                f"非 `allow`（{self.decision}）必携 hit_rule（命中的判定位标识——行为 8）"
            )
        if self.decision == DECISION_REFUSE and not isinstance(self.reason, RefusalReason):
            raise ValueError("`refuse` 必携 RefusalReason（rule_id／human_text 齐备——行为 8）")
        if self.decision == DECISION_ASK and not isinstance(self.reason, AskReason):
            raise ValueError("`ask` 必携 AskReason（kind／prompt 齐备——行为 8）")

    def as_payload(self) -> dict[str, Any]:
        """下游投影（`state.precondition_verdicts` 条目形）——五键恒在场、值诚实。"""
        return {
            "subtask_id": self.subtask_id,
            "decision": self.decision,
            "hit_rule": self.hit_rule or "",
            "notes": list(self.notes),
            "reason": None if self.reason is None else self.reason.as_payload(),
        }
