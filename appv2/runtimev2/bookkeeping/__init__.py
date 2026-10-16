"""公共簿记：全节点共享的唯一写口——步记录与序号、对话链与对话层追加、过程档案、通知、
触界收敛落地、完成收口旁路、调模型单点、工具上下文装配、结果归一投影

模块卡见 `specs/modules.md` 的 `## bookkeeping` 一节；规格见 `specs/bookkeeping.md`（形状真源）；
架构图见 `docs/architecture-v3.html`。包根即公开面（卡「公开接口」节 13 成员）：

- 共享写口（唯一入口；相位禁直写）：`record_step`／`next_seq`／`append_message`／
  `append_dialogue`／`note`／`notice`／`set_intent`／`append_contract`（`ports`）；
- 触界收敛与完成收口：`converge`／`direct_answer`（`closing`）；
- 调模型与工具面：`call_model`（`closing`）／`tool_context`／`result_projection`（`projection`）。

依赖面（规格「框架与依赖红线」）：**运行逻辑只依赖两处**——`state`（形状／判定）与
`gateway_adapter`（模型出口）；**类型与常量形状**另引三处——`tools`（`ToolContext`）／
`persistence`（`StepRecord` 与步状态闭世界常量）／`transport`（`NOTICE_TYPES`），**只许引类型与
常量、不许引其行为**（不调工具、不落盘、不发帧）；不引入框架（R5b）、不直引模型出口（R7）、
不直引引擎（R6）、不落盘。机检＝`tests/domains/test_v2_bookkeeping.py`（写口无旁路双证 ＋ AST
import 白名单 ＋ 每步通道值归一形）。

本批（`RT-W3-01b`）落地面：触界收敛与收口簇（`closing` 的 `converge`／`direct_answer`／
`call_model`）已落地——收敛六键／幂等与零副作用／正文与通知材料同源（单一材料面）、直答三键、
调模型只回 `content` 而用量与归因面记步记录与 `Manifest`。余下未落地面：`note`／`notice` 的写入点
行为随 `RT-W3-01c-bookkeeping.md`（`tool_context`／`result_projection` 同票）——未落地前一律
fail-closed（`NotImplementedError`），不静默兜底、不假成功（合法降级路径＝无）。
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
