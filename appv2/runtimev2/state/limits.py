"""限额触界**判定**（纯计算）：`specs/state.md` 行为 11–13 的落地面。

判定只吃状态、只吐判定结果：同输入两次结果相等、不改入参、不写状态、无 IO、无模型、无随机
（行为 11）；触界必带恰三键如实注记、未触界恒无注记（行为 12）；触界必留机读信号（行为 13）。
**落地写入**（`budget_hit`／`notices`／`status`／`next_intent` 六键）归 `bookkeeping` 的唯一
写口 `converge`（`specs/bookkeeping.md` 行为 12）——判定／落地分层、一物一处
（`specs/modules.md` `## state` 卡注／流水 20①）。

用量面＝状态自身携带的字段（不发明字段、不做兜底字面量）＋ 调用方注入的两键（见下）：

- `rounds` ← `state.rounds`（`synth/S5`：M2 计轮／轮数闸读方）；
- `discovers_per_run` ← `state.discover_used`（`synth/S5`：全 run 发现预算）；
- `discovers_per_round`／`executes_per_round` ← 当前轮的 `discover`／`execute` 步记录数
  （轮界＝末条 `decision` 步之后；R-K-72「轮＝LLM 决策周期」；步记录形状＝`persistence.StepRecord`
  七字段、`step` ∈ `STEP_KINDS`）。

余下两键（`seconds`／`ask_cap`）的用量面**不在 `RunState` 形状内**：计时字段与连续反问计数字段已
随「流水 49①」取消（`synth/S5` 已取消四字段），状态侧无载体——本函数不为其发明载体；**用量由调用
方注入**（`elapsed_seconds`／`consecutive_asks`，`None`＝该项不判定）——注入形＝2026-10-16 裁·流水
52-A，判定落地随流水 61 的轮闸接线（计时段内用时＝`seconds`；连续反问＝澄清相位既有口径）。
`tool_timeout` 为单次调用时限、归执行侧实时面，不经本判定。
"""

from dataclasses import fields
from typing import Any, cast, get_args

from appv2.runtimev2.state.constants import (
    _CONVERGENCE_NOTICE_TYPE,
    STEP_DECISION,
    STEP_DISCOVER,
    STEP_EXECUTE,
    STEP_KINDS,
)
from appv2.runtimev2.state.models import Budget, Convergence, LimitHit, LimitKind, RunState

# 限额键闭世界（真源＝`LimitHit.limit` 的 Literal；与 `Budget` 字段名同名同集——判定按名取上限）
_LIMIT_ORDER: tuple[str, ...] = get_args(LimitKind)
LIMIT_KINDS: frozenset[str] = frozenset(_LIMIT_ORDER)


def _step_kind(record: dict[str, Any]) -> str | None:
    """步记录的步类型。

    V2 形＝`StepRecord.step`（七字段，`step` ∈ `STEP_KINDS`）；缺 `step` 键＝旧形六键 dict
    （`specs/bookkeeping.md` 行为 3 已判为旧形）→ `None`（不计）；键在而值越界 → 抛错
    （fail-closed）。
    """
    if "step" not in record:
        return None
    kind: Any = record["step"]
    if not isinstance(kind, str) or kind not in STEP_KINDS:
        values = "／".join(sorted(STEP_KINDS))
        raise ValueError(f"步记录 step 越界（闭世界 STEP_KINDS＝{values}）：{kind!r}")
    return kind


def _current_round_records(state: RunState) -> list[dict[str, Any]]:
    """当前轮的步记录：末条 `decision` 步之后（无 `decision` 步＝全部计入）。"""
    start = 0
    for index, record in enumerate(state.steps):
        if _step_kind(record) == STEP_DECISION:
            start = index + 1
    return state.steps[start:]


def _limit_usage(state: RunState) -> dict[str, float]:
    """状态携带的用量投影（键 ⊆ `LIMIT_KINDS`；逐键来源见模块 docstring）。"""
    round_records = _current_round_records(state)
    return {
        "rounds": float(state.rounds),
        "discovers_per_round": float(
            sum(1 for record in round_records if _step_kind(record) == STEP_DISCOVER)
        ),
        "executes_per_round": float(
            sum(1 for record in round_records if _step_kind(record) == STEP_EXECUTE)
        ),
        "discovers_per_run": float(state.discover_used),
    }


def _injected_usage(
    elapsed_seconds: float | None, consecutive_asks: int | None
) -> dict[str, float]:
    """注入用量（键名同 `LimitHit.limit`）：`seconds` ← 调用方计的段内已用时；`ask_cap` ←
    调用方按既定口径计的连续反问计数。`None`＝该键不判定（缺省注入＝两键皆不判定）。"""
    injected: dict[str, float] = {}
    if elapsed_seconds is not None:
        injected["seconds"] = float(elapsed_seconds)
    if consecutive_asks is not None:
        injected["ask_cap"] = float(consecutive_asks)
    return injected


def _budget_cap(budget: Budget, limit: str) -> float:
    """限额上限：按名引 `Budget` 字段（「缺键取缺省」由 `Budget` 缺省面承担，不在此兜底字面量）。"""
    if not isinstance(budget, Budget):
        raise ValueError(f"限额表形态越界（期望 Budget）：{type(budget).__name__}")
    if limit not in {field.name for field in fields(Budget)}:
        keys = "／".join(sorted(field.name for field in fields(Budget)))
        raise ValueError(f"限额键越界（闭世界 Budget 键＝{keys}）：{limit!r}")
    return float(getattr(budget, limit))


def _convergence_notice(hits: tuple[LimitHit, ...]) -> dict[str, Any]:
    """触界如实注记：恰三键 `type`／`gates`／`content`（行为 12，形状真源＝`synth/S6` §一）。

    `gates`＝命中项名的列表（真源＝本块 `LimitHit.limit` 闭世界，不另立第二套闸名集合）；
    `type` 值真源＝`specs/transport.md` `NOTICE_TYPES`（以值引用，见 `constants` 注）；
    「未完成项」明细由 `bookkeeping` 装配进注记（行为 13），不在本块。
    """
    detail = "；".join(f"{hit.limit} 已用 {hit.used:g}／上限 {hit.cap:g}" for hit in hits)
    return {
        "type": _CONVERGENCE_NOTICE_TYPE,
        "gates": [hit.limit for hit in hits],
        "content": f"预算触界收敛：{detail}",
    }


def check_limits(
    state: RunState,
    *,
    elapsed_seconds: float | None = None,
    consecutive_asks: int | None = None,
) -> Convergence:
    """触界判定（纯函数）：判据＝`used >= cap`（达上限即触界——真源 `recon/K` R-K-86）。

    用量面两源：状态自带四键（`_limit_usage`）＋ **调用方注入两键**（2026-10-16 裁·流水 52-A 的
    注入形、流水 61 落地判定）——`elapsed_seconds`（`seconds` 键用量：调用方计的段内已用时，真源
    `specs/agent-loop.md` 行为 7「单段时限」）与 `consecutive_asks`（`ask_cap` 键用量：调用方按澄清
    相位既有口径计的连续反问计数），`None`＝该项不判定。两参缺省时行为与注入面落地前逐字节等价
    （两键不判定、状态携带四键判定不变）；返回形不因注入参在场而变，恒为 `Convergence`（未触界＝
    `Convergence(hit=(), notice=None)`）。
    """
    usage = {
        **_limit_usage(state),
        **_injected_usage(elapsed_seconds, consecutive_asks),
    }
    unknown = sorted(set(usage) - LIMIT_KINDS)
    if unknown:
        raise ValueError(f"用量键越界（闭世界 LIMIT_KINDS）：{unknown}")
    hits: list[LimitHit] = []
    for limit in _LIMIT_ORDER:
        used = usage.get(limit)
        if used is None:
            continue
        cap = _budget_cap(state.budget, limit)
        if used >= cap:
            hits.append(LimitHit(limit=cast(LimitKind, limit), used=used, cap=cap))
    if not hits:
        return Convergence(hit=(), notice=None)
    hit = tuple(hits)
    return Convergence(hit=hit, notice=_convergence_notice(hit))
