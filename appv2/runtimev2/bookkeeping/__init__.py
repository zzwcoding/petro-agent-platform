"""公共簿记：全节点共享的唯一写口——步记录与序号、对话链与对话层追加、过程档案、通知、
触界收敛落地、完成收口旁路、调模型单点、工具上下文装配、结果归一投影

模块卡见 `specs/modules.md` 的 `## bookkeeping` 一节；规格见 `specs/bookkeeping.md`（形状真源）；
架构图见 `docs/architecture-v3.html`。包根即公开面（卡「公开接口」节 13 成员）：

- 共享写口（唯一入口；相位禁直写）：`record_step`／`next_seq`／`append_message`／
  `append_dialogue`／`note`／`notice`／`set_intent`／`append_contract`（`ports`）；
- 触界收敛与完成收口：`converge`／`direct_answer`（`closing`）；
- 调模型与工具面：`call_model`（`closing`）／`tool_context`／`result_projection`（`projection`）。

依赖面（规格「框架与依赖红线」）：**运行逻辑只依赖两处**——`state`（形状／判定）与
`gateway_adapter`（模型出口）；**类型与常量形状**另引三处——`tools`（`ToolContext` 类型 ＋ 送窗
预算**公式函数** `resolve_send_budget`——行为 16 点名的「数值与公式真源」，只引不算、本块不复述
数值）／`persistence`（`StepRecord` 与步状态闭世界常量）／`transport`（`NOTICE_TYPES`），**只许引
类型与常量、不许引其行为**（不调工具、不落盘、不发帧）；不引入框架（R5b）、不直引模型出口（R7）、
不直引引擎（R6）、不落盘。机检＝`tests/domains/test_v2_bookkeeping.py`（写口无旁路双证 ＋ AST
import 白名单 ＋ 每步通道值归一形）。

本批（`RT-W3-01c`）落地面：装配与归一簇（`ports` 的 `note`／`notice` 写入点行为；
`projection` 的 `tool_context`／`result_projection`）——过程档案写入点截断且只追加（截断可见）、
通知恰三键且 `type`／`gates` 双闭世界、工具上下文身份只从状态取／放行态随上下文／送窗预算按
子问题数、结果投影逐字段原样而空值与缺省可区分。前批（`RT-W3-01a`／`-01b`）落地面：共享写口
骨架与触界收敛、收口簇（写口九函数／`converge`／`direct_answer`／`call_model`）。本块公开面 13
成员至此全部落地，无 fail-closed 占位。
"""

from appv2.runtimev2.bookkeeping.closing import call_model, converge, direct_answer
from appv2.runtimev2.bookkeeping.ports import (
    append_contract,
    append_dialogue,
    append_message,
    next_seq,
    note,
    notice,
    record_step,
    set_intent,
)
from appv2.runtimev2.bookkeeping.projection import result_projection, tool_context

__all__ = [
    "append_contract",
    "append_dialogue",
    "append_message",
    "call_model",
    "converge",
    "direct_answer",
    "next_seq",
    "note",
    "notice",
    "record_step",
    "result_projection",
    "set_intent",
    "tool_context",
]
