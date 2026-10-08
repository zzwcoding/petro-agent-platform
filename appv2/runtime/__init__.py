"""appv2.runtime —— 有界 agent loop 编排层（V2-06；specs/agent-loop.md、ADR-0002/0003）。

六步 StateGraph loop（understand/plan/tool/observe/verify/answer——每步落 step
记录，过程态簿记）＋审计闭环（run 创建/终态/拒答收口/外表审批决定四事件经
security.audit 唯一写口落 audit_log 责任账——runtime/audit.py，INV-5）＋PG
checkpointer（挂起态跨进程恢复）＋Context Builder/Manifest
（每次模型调用确定性编译，行为约定 2）＋Verifier 核验步（INV-1/INV-4）＋预算
三闸（max_steps 8／总时长 300s／单工具 30s——触界收敛不静默截断）＋RunCommand
seam（ADR-0003：命令入口与执行器显式分离，将来换队列消费者契约零改动）。

三红线自守（ADR-0002，importlinter V2 契约在案）：
①langgraph/langchain 只在本包 import，不渗入 api/tools/engines 与事件契约；
②全部 LLM 调用经自写 GatewayChatModel 走 gateway.complete（caller 归因保留
＝`v2.runtime.<step>`），禁止 langchain 自带 provider 直连；
③run/step 状态 schema 自有（RunState/Manifest/ASK 载荷）——checkpointer 仅存储。

边界：依赖 appv2.tools 公开接口＋appv2.infra；不 import app.** 及
knowledge/query/retrieval（agent 与世界的唯一接触面＝ToolRegistry）。

公开面（票面点名符号＋P-007 api 消费面）：
- AgentRuntime（ask/resume）＋GraphRunExecutor＋RunCommand/COMMAND_* 闭世界
  ＋RunNotFoundError/RunNotSuspendedError（api 404/409 异常源）；
- AskRequest/AskChoice/RunHandle/RunEvent/EVENT_* 八类闭世界/RunState/Manifest/
  STEP_* 六类闭世界/RUN_STATUS_* 四态闭世界/ContextBuilder/CompiledContext；
- Budget 三闸＋预算合同值；GatewayChatModel/Completer（B6 红线②缝）；
- PgCheckpointer/RunStore/ensure_agent_v2_tables（agent_v2_* 前缀隔离表）；
- ScriptedCompleter（剧本化 completer——caller 分流、多轮 replay，P-007 复用）；
- gate_freshness（DE-16 freshness_gate_enabled 编排层接线）/reseed_approval_id
  （V2-03 偏差 7 审批单号 run 前缀种子）。
"""

from appv2.runtime.budget import (
    MAX_STEPS_CONTRACT,
    TOOL_TIMEOUT_SECONDS_CONTRACT,
    TOTAL_SECONDS_CONTRACT,
    Budget,
)
from appv2.runtime.checkpointer import PgCheckpointer
from appv2.runtime.context import CompiledContext, ContextBuilder
from appv2.runtime.events import (
    EVENT_ASK,
    EVENT_CITATION,
    EVENT_KINDS,
    EVENT_NOTICE,
    EVENT_OBSERVATION,
    EVENT_STEP,
    EVENT_TEXT,
    EVENT_TOOL,
    EVENT_VERDICT,
    EventBus,
    RunEvent,
)
from appv2.runtime.executor import (
    COMMAND_ASK,
    COMMAND_KINDS,
    COMMAND_RESUME,
    AgentRuntime,
    GraphRunExecutor,
    RunCommand,
    RunNotFoundError,
    RunNotSuspendedError,
    new_run_id,
)
from appv2.runtime.fake import ScriptedCompleter
from appv2.runtime.graph import reseed_approval_id
from appv2.runtime.llm import CALLER_PREFIX, Completer, GatewayChatModel
from appv2.runtime.state import (
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_RUNNING,
    RUN_STATUS_KINDS,
    RUN_WAITING_ASK,
    STEP_ANSWER,
    STEP_KINDS,
    STEP_OBSERVE,
    STEP_PLAN,
    STEP_TOOL,
    STEP_UNDERSTAND,
    STEP_VERIFY,
    AskChoice,
    AskRequest,
    Manifest,
    RunHandle,
    RunState,
)
from appv2.runtime.store import RunStore, ensure_agent_v2_tables
from appv2.runtime.wiring import gate_freshness

__all__ = [
    "CALLER_PREFIX",
    "COMMAND_ASK",
    "COMMAND_KINDS",
    "COMMAND_RESUME",
    "EVENT_ASK",
    "EVENT_CITATION",
    "EVENT_KINDS",
    "EVENT_NOTICE",
    "EVENT_OBSERVATION",
    "EVENT_STEP",
    "EVENT_TEXT",
    "EVENT_TOOL",
    "EVENT_VERDICT",
    "MAX_STEPS_CONTRACT",
    "RUN_COMPLETED",
    "RUN_FAILED",
    "RUN_RUNNING",
    "RUN_STATUS_KINDS",
    "RUN_WAITING_ASK",
    "STEP_ANSWER",
    "STEP_KINDS",
    "STEP_OBSERVE",
    "STEP_PLAN",
    "STEP_TOOL",
    "STEP_UNDERSTAND",
    "STEP_VERIFY",
    "TOOL_TIMEOUT_SECONDS_CONTRACT",
    "TOTAL_SECONDS_CONTRACT",
    "AgentRuntime",
    "AskChoice",
    "AskRequest",
    "Budget",
    "CompiledContext",
    "Completer",
    "ContextBuilder",
    "EventBus",
    "GatewayChatModel",
    "GraphRunExecutor",
    "Manifest",
    "PgCheckpointer",
    "RunCommand",
    "RunEvent",
    "RunHandle",
    "RunNotFoundError",
    "RunNotSuspendedError",
    "RunState",
    "RunStore",
    "ScriptedCompleter",
    "ensure_agent_v2_tables",
    "gate_freshness",
    "new_run_id",
    "reseed_approval_id",
]
