"""bookkeeping.projection —— 工具上下文装配与工具结果归一投影。

真源＝`specs/bookkeeping.md` 接口定义节「调模型与工具面」＋行为 16／17。两块都只借形状、不走
形状块的行为面（不调工具、不落盘、不发帧）：

- `tool_context`：**身份只从状态取**（不接调用方传身份）；**外表放行态随上下文走**（不进工具
  参数、不重排计划）；送窗预算按**子问题数**取值（数值与公式真源＝`appv2/tools/schema.py` 的
  `resolve_send_budget` 与其配套常量——本块不复述数值）。
- `result_projection`：逐字段**原样投影**（无增删改名）；**空值语义统一**——「有该字段但为空」与
  「无该字段」读回可区分（禁真假值归一；旧码 `_result_dict` 的 `detail or None` 归一是缺陷，
  `recon/B1` D-B1-13）。

两个成员的行为体随 `RT-W3-01c-bookkeeping.md` 落地（本票只出签名与公开面）；未落地前调用一律
fail-closed（`NotImplementedError`）——不静默兜底、不返回哨兵值。
"""

from __future__ import annotations

from typing import Any

from appv2.runtimev2.state import RunState
from appv2.tools import ToolContext, ToolResult


def tool_context(state: RunState) -> ToolContext:
    """逐调用工具上下文装配（行为 16）：身份／放行集／预算与状态一致，参数里无放行态。

    行为体随 `RT-W3-01c-bookkeeping.md` 落地。
    """
    raise NotImplementedError(
        "bookkeeping.tool_context 的行为体随 RT-W3-01c-bookkeeping.md 落地（本票只出签名与公开面）"
    )


def result_projection(result: ToolResult) -> dict[str, Any]:
    """工具结果 → dict 投影（行为 17）：逐字段原样、空值与缺省两态可区分。行为体随
    `RT-W3-01c-bookkeeping.md` 落地。
    """
    raise NotImplementedError(
        "bookkeeping.result_projection 的行为体随 RT-W3-01c-bookkeeping.md 落地"
        "（本票只出签名与公开面）"
    )
