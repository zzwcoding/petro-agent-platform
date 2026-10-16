"""bookkeeping.projection —— 工具上下文装配与工具结果归一投影。

真源＝`specs/bookkeeping.md` 接口定义节「调模型与工具面」＋行为 16／17。两块都只借形状、不走
形状块的行为面（不调工具、不落盘、不发帧）：

- `tool_context`：**身份只从状态取**（不接调用方传身份）；**外表放行态随上下文走**（不进工具
  参数、不重排计划）；送窗预算按**子问题数**取值（数值与公式真源＝`appv2/tools/schema.py` 的
  `resolve_send_budget` 与其配套常量——本块只**引该函数**，不复述数值与公式）。
- `result_projection`：逐字段**原样投影**（无增删改名）；**空值语义统一**——「有该字段但为空」与
  「无该字段」读回可区分（禁真假值归一；旧码 `_result_dict` 的 `detail or None` 归一是缺陷，
  `recon/B1` D-B1-13）。

两块**零判断**（行为 18）：无词表、无正则、无语义判定；`tool_context` 的预算算式完全不落本块
（只调 `appv2.tools` 的公式函数），`result_projection` 是纯字段搬迁。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from appv2.runtimev2.state import RunState
from appv2.tools import ToolContext, ToolResult, resolve_send_budget


def tool_context(state: RunState) -> ToolContext:
    """逐调用工具上下文装配（行为 16）：身份／放行集／预算与状态一致，参数里无放行态。

    四字段逐项取自**状态**（不接调用方传任何一项——签名只有 `state`）：

    - `actor`＝`state.actor`（**身份只从状态取**：现状锚 `recon/B1` R-B1-16——行级身份注入
      `data_query → plan.actor` 两步缝第一步）；
    - `budget`＝`resolve_send_budget(问题组子问题数)`——**公式与常量真源＝`appv2.tools`**（本块
      只引该函数、**不复述数值与公式**；亦不引 tools 的行为面——它不调工具、只是纯算式）；
      子问题数取 `state.question_group["subtasks"]` 的 mapping 条目数（现状锚 `recon/B1`
      R-B1-14；无组／旧形按 1 支计，下限由该函数自身兜）；
    - `metric_candidates`＝`tuple(state.metric_candidates)`，空列 → `None`（候选集「不参与」态——
      现状形照抄 `recon/B1` `_ctx_of` 分支 2；`recon/B1` D-B1-08 登记的「空列与不参与态不可分」是
      现状遗留疑点，不在本票行为面内，本块不自行收窄或扩义）；
    - `approved_tables`＝`tuple(state.approved_ids)`（**外表放行态随上下文走**：现状锚
      `recon/B1` R-B1-15——**不进工具参数、不重排计划**）。

    参数里无放行态是**结构性质**：放行态只在本上下文字段里，工具调用面＝`ToolRegistry.call(name,
    args, ctx)`——`args` 逐工具 schema 面，`ctx` 才是本函数产物。
    """
    return ToolContext(
        actor=state.actor,
        budget=resolve_send_budget(_group_subtask_count(state)),
        metric_candidates=tuple(state.metric_candidates) or None,
        approved_tables=tuple(state.approved_ids),
    )


def _group_subtask_count(state: RunState) -> int:
    """问题组子问题数（`question_group` 投影——非 mapping 条目不计，旧检查点残形不炸链）。"""
    group = state.question_group
    if not isinstance(group, Mapping):
        return 0
    subtasks = group.get("subtasks")
    if not isinstance(subtasks, Sequence):
        return 0
    return sum(1 for subtask in subtasks if isinstance(subtask, Mapping))


def _observation_projection(observation: Any) -> dict[str, Any]:
    """观测行投影：`Observation` 八字段逐字同名、同序（`locator` 取浅拷——JSON 可投影形）。"""
    return {
        "content": observation.content,
        "source": observation.source,
        "source_id": observation.source_id,
        "version": observation.version,
        "freshness": observation.freshness,
        "scope": observation.scope,
        "locator": dict(observation.locator),
        "well": observation.well,
    }


def result_projection(result: ToolResult) -> dict[str, Any]:
    """工具结果 → dict 投影（行为 17）：逐字段**原样投影**、键集合固定、空值与缺省读回可区分。

    顶层四键（`status`／`observations`／`ask`／`error`）与三个嵌套行（`Observation` 八字段／
    `AskFrame` 四字段／`ToolError` 三字段）**键恒在场、与形状同序、无增删改名**（现状锚
    `recon/B1` R-B1-18；形状真源 `specs/modules.md` `## tools` 卡）。

    **禁真假值归一**（行为 17 要点；现状缺陷 `recon/B1` D-B1-13）：空值只按 `is None` 判「有无
    该字段的取值」，不按真值——
    - `ask.detail`：`{}`（有 detail 但为空）**照写 `{}`**，只有 `None`（无 detail）才写 `None`
      ——两态投影后**不等价**（旧码 `if result.ask.detail` 把两者糊成一件事，重写收正）；
    - `well`／`hint`／`version` 一类可空字段原样透传（`""` 与 `None` 亦不等价）；
    - `observations` 空列 → `[]`（在场且为空），不归 `None`。

    无模型、无词表、无 IO——纯字段搬迁（行为 18）。
    """
    ask = result.ask
    error = result.error
    return {
        "status": result.status,
        "observations": [
            _observation_projection(observation) for observation in result.observations
        ],
        "ask": (
            {
                "kind": ask.kind,
                "prompt": ask.prompt,
                "options": list(ask.options),
                "detail": (
                    dict(ask.detail) if ask.detail is not None else None
                ),
            }
            if ask is not None
            else None
        ),
        "error": (
            {
                "category": error.category,
                "message": error.message,
                "hint": error.hint,
            }
            if error is not None
            else None
        ),
    }
