"""runtime.budget —— 预算三闸（specs/agent-loop.md 行为约定 7 的合同值与判据）。

三闸：max_steps 8（图节点执行步数）／总时长 300s（单段执行时限——挂起恢复后
每段重新计时）／单工具超时 30s（工具调出口 wait_for）。触界即收敛——交付已
核实部分＋notice 明示未完成项，不得静默截断（有界终止）。

Budget 为冻结合同形（as_dict 进 RunState.budget 随 checkpoint 走，跨进程恢复
后判据仍生效）；判据函数（steps_exhausted/time_exhausted）与收敛渲染
（unfinished_items/unfinished_notice）在此单点，六节点入口统一消费。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

# 预算三闸合同值（specs/agent-loop.md 行为约定 7）。
MAX_STEPS_CONTRACT = 8
TOTAL_SECONDS_CONTRACT = 300.0
TOOL_TIMEOUT_SECONDS_CONTRACT = 30.0


@dataclass(frozen=True, slots=True)
class Budget:
    """预算三闸参数（合同缺省值；测试可收窄——合同值本身不因测试改动）。"""

    max_steps: int = MAX_STEPS_CONTRACT
    total_seconds: float = TOTAL_SECONDS_CONTRACT
    tool_timeout_seconds: float = TOOL_TIMEOUT_SECONDS_CONTRACT

    def as_dict(self) -> dict[str, float]:
        return {
            "max_steps": float(self.max_steps),
            "total_seconds": self.total_seconds,
            "tool_timeout_seconds": self.tool_timeout_seconds,
        }


def now_monotonic() -> float:
    """单调钟读数（B14 时钟纪律的预算面——墙上时钟不进判据）。"""
    return time.monotonic()


def steps_exhausted(state: Any) -> bool:  # RunState（防环不 import）
    """步数闸判据：本段已执行步数（挂起等人工不计——恢复段自基线重新起算）。"""
    max_steps = int(state.budget.get("max_steps", MAX_STEPS_CONTRACT))
    segment_steps = len(state.steps) - int(getattr(state, "segment_step_base", 0) or 0)
    return segment_steps >= max_steps


def time_exhausted(state: Any) -> bool:  # RunState
    """时长闸判据：单调钟越 deadline（挂起恢复后按段重算——executor 刷新）。"""
    return bool(now_monotonic() >= state.deadline_monotonic)


def budget_gate_hit(state: Any) -> list[str]:  # RunState
    """入口闸检查：命中的闸名列表（空列＝未触界）。"""
    gates: list[str] = []
    if steps_exhausted(state):
        gates.append("max_steps")
    if time_exhausted(state):
        gates.append("total_seconds")
    return gates


def unfinished_items(state: Any) -> list[str]:  # RunState
    """未完成项清单（触界收敛时逐条入 notice——不得静默截断）。"""
    items: list[str] = []
    if not state.understanding:
        items.append("理解（understand）未执行")
    if not state.tool_args and state.last_result is None:
        items.append("规划（plan）未执行或未产出工具调用")
    if state.last_result is None:
        items.append("工具（tool）未执行")
    if not state.observations:
        items.append("观察（observe）未入栈")
    if not state.verdict:
        items.append("核验（verify）未执行")
    if not state.answer and not state.draft:
        items.append("阐述（answer）未完成")
    return items


def unfinished_notice(state: Any, gates: list[str]) -> dict[str, Any]:
    """触界收敛 notice（gates＝命中闸名——机读判据随文案走）。"""
    items = unfinished_items(state)
    body = "；".join(items) if items else "已到执行边界——按已取得材料收敛"
    return {
        "type": "budget_converged",
        "gates": gates,
        "content": (
            f"预算触界收敛（{'、'.join(gates)}）——未完成项：{body}。"
            "已交付已取得部分，不静默截断。"
        ),
    }
