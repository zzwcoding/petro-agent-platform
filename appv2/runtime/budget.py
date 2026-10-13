"""runtime.budget —— 预算闸（specs/agent-loop.md 行为约定 7 的 ReAct 语义判据）。

V2-31 ReAct 重构后的闸语义（Owner 2026-10-09 拍板①）：≤3 轮（轮＝LLM 决策周期）
×轮内（发现≤2＋主执行≤2）＋单段总时长 300s＋单工具超时 30s。轮内双上限在决策
发射 schema 校验时执行（graph.parse_decision——超限＝拒因回喂重决策）；本模块
单点收轮数闸/时长闸判据、材料面单源（material_rows）与收敛渲染
（unfinished_items/unfinished_notice），节点入口统一消费。触界即收敛——交付已
取得部分＋notice 明示未完成项，不得静默截断（有界终止）。

Budget 为冻结合同形（as_dict 进 RunState.budget 随 checkpoint 走，跨进程恢复
后判据仍生效）。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

# 预算闸合同值（ReAct 语义——拍板①；测试可收窄，合同值本身不因测试改动）。
MAX_ROUNDS_CONTRACT = 3
MAX_DISCOVERS_PER_ROUND_CONTRACT = 2
MAX_EXECUTES_PER_ROUND_CONTRACT = 2
TOTAL_SECONDS_CONTRACT = 300.0
TOOL_TIMEOUT_SECONDS_CONTRACT = 30.0
# 澄清相位发现预算（V2-34——Owner 2026-10-09 拍板放宽原 3-4：全 run ≤10）。
MAX_DISCOVERS_PER_RUN_CONTRACT = 10
# 连续 ask 截断上限（V2-70 b 案——Owner 2026-10-13：2→3，与轮预算同档对齐）。
# 防环语义不变：run 生命期计数任何路径不清零（run-69517e02 实测封环面）。
CLARIFY_ASK_CAP_CONTRACT = 3


@dataclass(frozen=True, slots=True)
class Budget:
    """预算闸参数（合同缺省值；测试可收窄——合同值本身不因测试改动）。"""

    max_rounds: int = MAX_ROUNDS_CONTRACT
    max_discovers_per_round: int = MAX_DISCOVERS_PER_ROUND_CONTRACT
    max_executes_per_round: int = MAX_EXECUTES_PER_ROUND_CONTRACT
    total_seconds: float = TOTAL_SECONDS_CONTRACT
    tool_timeout_seconds: float = TOOL_TIMEOUT_SECONDS_CONTRACT

    def as_dict(self) -> dict[str, float]:
        return {
            "max_rounds": float(self.max_rounds),
            "max_discovers_per_round": float(self.max_discovers_per_round),
            "max_executes_per_round": float(self.max_executes_per_round),
            "total_seconds": self.total_seconds,
            "tool_timeout_seconds": self.tool_timeout_seconds,
        }


def now_monotonic() -> float:
    """单调钟读数（B14 时钟纪律的预算面——墙上时钟不进判据）。"""
    return time.monotonic()


def rounds_exhausted(state: Any) -> bool:  # RunState（防环不 import）
    """轮数闸判据：已消耗 LLM 决策周期数达上限（ReAct 有界自主的上界）。"""
    max_rounds = int(state.budget.get("max_rounds", MAX_ROUNDS_CONTRACT))
    return int(getattr(state, "rounds", 0)) >= max_rounds


def time_exhausted(state: Any) -> bool:  # RunState
    """时长闸判据：单调钟越 deadline（挂起恢复后按段重算——executor 刷新）。"""
    return bool(now_monotonic() >= state.deadline_monotonic)


def budget_gate_hit(state: Any, *, include_rounds: bool = True) -> list[str]:  # RunState
    """入口闸检查：命中的闸名列表（空列＝未触界）。

    include_rounds＝轮数闸开关（ReAct 语义：轮数闸只守 decision 入口——轮内的
    execute/observe 与定稿后的 answer/verify 不受轮数闸拦，否则 finalize 会被
    自家预算吞掉；时长闸全节点守）。
    """
    gates: list[str] = []
    if include_rounds and rounds_exhausted(state):
        gates.append("max_rounds")
    if time_exhausted(state):
        gates.append("total_seconds")
    return gates


def unfinished_items(state: Any) -> list[str]:
    """未完成项清单（触界收敛时逐条入 notice——不得静默截断）。"""
    items: list[str] = []
    if not state.understanding:
        items.append("理解（understand）未执行")
    if state.rounds < 1:
        items.append("决策（decision）未执行")
    if state.last_result is None and not state.observations:
        items.append("工具（discover/execute）未执行或未取得观察")
    if not state.observations:
        items.append("观察（observe）未入栈")
    if not state.verdict and not state.draft and not state.answer:
        items.append("核验（verify）/阐述（answer）未执行")
    return items


def material_rows(state: Any) -> list[dict[str, Any]]:  # RunState
    """已取得观察材料（收敛交付面＝已入栈观察＋末次工具结果自带观察）。

    R2 单源：graph._converge 的交付正文与 unfinished_notice 的文案分叉同判
    此处——材料面一个真源，notice 与答案永不漂移。
    """
    rows: list[dict[str, Any]] = list(state.observations)
    if state.last_result is not None:
        rows.extend(state.last_result.get("observations") or [])
    return rows


def unfinished_notice(state: Any, gates: list[str]) -> dict[str, Any]:
    """触界收敛 notice（gates＝命中闸名——机读判据随文案走）。

    文案随材料面分叉（P-006b·R2）：零材料情形与答案同口径（「未取得可交付
    观察材料」——不冒充已交付）；有材料情形维持「已交付已取得部分」。
    """
    items = unfinished_items(state)
    body = "；".join(items) if items else "已到执行边界——按已取得材料收敛"
    if material_rows(state):
        tail = "已交付已取得部分，不静默截断。"
    else:
        tail = "未取得可交付观察材料——如实回报，不编造。"
    return {
        "type": "budget_converged",
        "gates": gates,
        "content": (
            f"预算触界收敛（{'、'.join(gates)}）——未完成项：{body}。{tail}"
        ),
    }
