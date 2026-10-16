"""批量执行：发现、执行、观察回流；只读并行、成功不重跑、失败只重做失败的

模块卡见 `specs/modules.md` 的 `## execution` 一节；规格见 `specs/execution.md`（形状与行为
真源）；架构图见 `docs/architecture-v3.html`。包根即公开面（R2：消费方只经
`appv2.runtimev2.execution` 消费，深层子模块私有）：

- `execute(state, *, bus, registry, store)`——相位单入口（卡面签名 `execute(state) ->
  ExecutionOutcome`；三处关键词注入面见 `core` 模块注：`bus`＝编排块持有的 per-run 总线、
  `registry`＝`tools` 公开面的工具调用唯一入口、`store`＝`persistence` 公开面的引用载体）；
- 六形状（规格接口定义节逐字）：`ExecutionOutcome`／`SubtaskExec`／`ErrorClass`／
  `MaterialRef`／`Observation`（形状单点在 `models`）；
- 两处闭世界常量族：`EXEC_STATUS_KINDS`（执行状态三值）／`ERROR_CATEGORIES`（失败分类三档）；
- 闸门名与阈值单点：`GATE_EMPTY_PROBE`／`GATE_SAME_PARAM_REPLAY`（行为 13／14 两闸勿混）、
  `BIG_RESULT_THRESHOLD_CHARS`（行为 4 大结果阈——数值阶段 5 待定，只引名字）；
- 机读面键名与文案：`PAYLOAD_*`（步 payload 记账字段与帧载荷键）／`NOTICE_*`（通知类型字面——
  取值真源 `transport.NOTICE_TYPES`，本块不私扩）／`EVENT_*`（本块发射的三类事件名）／
  `SAME_PARAM_REPLAY_REASON`／`MISSING_SOURCE_REASON`（拒因原文，逐字迁移）。
- 机读信号三键（「不降级与静默禁令」节）：本块写的**每一步** payload 恒携 `row_count`／
  `ref`（`handle`／`summary`／`row_count`）／`error`（`category`／`reason`）——单点在
  `core._signal_payload`；落引用／失败／缺参三面由此可机检（缺参面另发 `ask` 帧＋`pending_ask`）。

依赖面（规格「框架与依赖红线」）：`state`（形状）／`transport`（事件）／`persistence`（大结果
引用载体）／`bookkeeping`（写口与结果归一投影）／`tools`（**只许走其公开面**——工具调用唯一
入口）／`context.trust_of`（观察信任级映射单点——本块不复制映射表；该依赖不在规格「依赖」
行内，**登记呈主窗**）／`parsing`（指纹器材四件——规格行为 14 点名的指纹来源）。**零 LLM 面**
（R8：不调模型、不引 `gateway_adapter`）；不引框架（R5b）、不引旧码（R5）、不直引引擎（R6）。
"""

from appv2.runtimev2.execution.constants import (
    BIG_RESULT_THRESHOLD_CHARS,
    EMPTY_PROBE_FEEDBACK_TEMPLATE,
    ERROR_BAD_ARGS,
    ERROR_CATEGORIES,
    ERROR_REFUSED,
    ERROR_RETRYABLE,
    EVENT_ASK,
    EVENT_OBSERVATION,
    EVENT_TOOL,
    EXEC_STATUS_FAILED,
    EXEC_STATUS_KINDS,
    EXEC_STATUS_NEED_INPUT,
    EXEC_STATUS_OK,
    GATE_EMPTY_PROBE,
    GATE_SAME_PARAM_REPLAY,
    LEDGER_NOTE_PHASE,
    MISSING_SOURCE_REASON,
    NOTICE_MATERIAL_TRUNCATED,
    NOTICE_SAME_PARAM_REPLAY,
    NOTICE_SUBTASK_FAILED,
    NOTICE_SUBTASK_REFUSED,
    NOTICE_TOOL_UNAVAILABLE,
    PAYLOAD_ARGS_FINGERPRINT_KEY,
    PAYLOAD_ARGS_KEY,
    PAYLOAD_ATTEMPTS_KEY,
    PAYLOAD_CHAIN_KEY,
    PAYLOAD_CONSUMES_ROUND_KEY,
    PAYLOAD_ERROR_CATEGORY_KEY,
    PAYLOAD_ERROR_KEY,
    PAYLOAD_ERROR_REASON_KEY,
    PAYLOAD_GATE_KEY,
    PAYLOAD_HANDLE_KEY,
    PAYLOAD_INDEX,
    PAYLOAD_PHASE_KEY,
    PAYLOAD_REF_KEY,
    PAYLOAD_REJECT_REASON_KEY,
    PAYLOAD_ROW_COUNT_KEY,
    PAYLOAD_SUBTASK_ID_KEY,
    PAYLOAD_TOOL,
    PAYLOAD_VOLATILE_KEY,
    PHASE,
    ROWSET_OBSERVATION_KINDS,
    SAME_PARAM_REPLAY_REASON,
)
from appv2.runtimev2.execution.core import execute
from appv2.runtimev2.execution.models import (
    ErrorClass,
    ExecutionOutcome,
    MaterialRef,
    Observation,
    SubtaskExec,
)

__all__ = [
    "BIG_RESULT_THRESHOLD_CHARS",
    "EMPTY_PROBE_FEEDBACK_TEMPLATE",
    "ERROR_BAD_ARGS",
    "ERROR_CATEGORIES",
    "ERROR_REFUSED",
    "ERROR_RETRYABLE",
    "EVENT_ASK",
    "EVENT_OBSERVATION",
    "EVENT_TOOL",
    "EXEC_STATUS_FAILED",
    "EXEC_STATUS_KINDS",
    "EXEC_STATUS_NEED_INPUT",
    "EXEC_STATUS_OK",
    "GATE_EMPTY_PROBE",
    "GATE_SAME_PARAM_REPLAY",
    "LEDGER_NOTE_PHASE",
    "MISSING_SOURCE_REASON",
    "NOTICE_MATERIAL_TRUNCATED",
    "NOTICE_SAME_PARAM_REPLAY",
    "NOTICE_SUBTASK_FAILED",
    "NOTICE_SUBTASK_REFUSED",
    "NOTICE_TOOL_UNAVAILABLE",
    "PAYLOAD_ARGS_FINGERPRINT_KEY",
    "PAYLOAD_ARGS_KEY",
    "PAYLOAD_ATTEMPTS_KEY",
    "PAYLOAD_CHAIN_KEY",
    "PAYLOAD_CONSUMES_ROUND_KEY",
    "PAYLOAD_ERROR_CATEGORY_KEY",
    "PAYLOAD_ERROR_KEY",
    "PAYLOAD_ERROR_REASON_KEY",
    "PAYLOAD_GATE_KEY",
    "PAYLOAD_HANDLE_KEY",
    "PAYLOAD_INDEX",
    "PAYLOAD_PHASE_KEY",
    "PAYLOAD_REF_KEY",
    "PAYLOAD_REJECT_REASON_KEY",
    "PAYLOAD_ROW_COUNT_KEY",
    "PAYLOAD_SUBTASK_ID_KEY",
    "PAYLOAD_TOOL",
    "PAYLOAD_VOLATILE_KEY",
    "PHASE",
    "ROWSET_OBSERVATION_KINDS",
    "SAME_PARAM_REPLAY_REASON",
    "ErrorClass",
    "ExecutionOutcome",
    "MaterialRef",
    "Observation",
    "SubtaskExec",
    "execute",
]
