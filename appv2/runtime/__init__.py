"""appv2.runtime —— 有界 ReAct agent loop 编排层（V2-06 建＋V2-31 ReAct 重构；
specs/agent-loop.md、ADR-0002/0003、V2-31 拍板七条）。

ReAct 循环（understand→decision⇄discover/execute→observe→answer→verify→收口
——轮＝LLM 决策周期 ≤3 轮，轮内发现≤2＋主执行≤2；每步落 step 记录，过程态
簿记）＋审计闭环（run 创建/终态/拒答收口/外表审批决定四事件经 security.audit
唯一写口落 audit_log 责任账——runtime/audit.py，INV-5）＋PG checkpointer
（挂起态跨进程恢复）＋Context Builder/Manifest（每次模型调用确定性编译，行为
约定 2）＋Verifier 核验步（INV-1/INV-4 机器底线，零 LLM——V2-23 表格豁免
继承）＋预算闸（轮数≤3／总时长 300s／单工具 30s——触界收敛不静默截断）＋
RunCommand seam（ADR-0003：命令入口与执行器显式分离，将来换队列消费者契约
零改动）。

三红线自守（ADR-0002，importlinter V2 契约在案）：
①langgraph/langchain 只在本包 import，不渗入 api/tools/engines 与事件契约；
②全部 LLM 调用经自写 GatewayChatModel 走 gateway.complete（caller 归因保留
＝`v2.runtime.<桶>`——understand/decision/answer 三桶闭世界，无 repair），禁止
langchain 自带 provider 直连；
③run/step 状态 schema 自有（RunState/Manifest/ASK 载荷）——checkpointer 仅存储。

边界：依赖 appv2.tools 公开接口＋appv2.infra；不 import app.** 及
knowledge/query/retrieval（agent 与世界的唯一接触面＝ToolRegistry）。

公开面（票面点名符号＋P-007 api 消费面）：
- AgentRuntime（ask/resume）＋GraphRunExecutor＋RunCommand/COMMAND_* 闭世界
  ＋RunNotFoundError/RunNotSuspendedError（api 404/409 异常源）；
- AskRequest/AskChoice/RunHandle/RunEvent/EVENT_* 八类闭世界/RunState/Manifest/
  STEP_* 六类闭世界（ReAct 周期）/RUN_STATUS_* 四态闭世界/ContextBuilder/
  CompiledContext；
- Budget 轮数/时长闸＋合同值；GatewayChatModel/Completer（B6 红线②缝）；
- DecisionEmission/parse_decision（决策发射 schema 校验单点）/ACTION_*/TASK_*/
  MODEL_KEYS（caller 桶闭世界）；
- PgCheckpointer/RunStore/ensure_agent_v2_tables（agent_v2_* 前缀隔离表）；
- ScriptedCompleter（剧本化 completer——caller 分流、多轮 replay、计数桶）；
- GuideProvider（处理指南缝——拍板⑦；占位 DefaultGuideProvider 已随 V2-34 退役，
  生产唯一指南源＝OntologyGuideProvider——appv2.api.ontology_guide 装载件）；
- QuestionGroup/Subtask/parse_question_group/parse_tool_match（V2-34 子任务图
  schema 校验单点）＋四相位路由意图；
- gate_freshness（DE-16 freshness_gate_enabled 编排层接线）/reseed_approval_id
  （V2-03 偏差 7 审批单号 run 前缀种子）；
- EVAL_FROZEN_DATE_*／resolve_eval_frozen_date／eval_frozen_today（V2-39 测评
  时钟冻结缝——评测/冒烟面统一注入冻结时钟；生产面 today=None 路径永不读 env，
  infra.clock B14 实现零改动）。
"""

from appv2.runtime.budget import (
    MAX_DISCOVERS_PER_ROUND_CONTRACT,
    MAX_DISCOVERS_PER_RUN_CONTRACT,
    MAX_EXECUTES_PER_ROUND_CONTRACT,
    MAX_ROUNDS_CONTRACT,
    TOOL_TIMEOUT_SECONDS_CONTRACT,
    TOTAL_SECONDS_CONTRACT,
    Budget,
)
from appv2.runtime.checkpointer import PgCheckpointer
from appv2.runtime.context import CompiledContext, ContextBuilder
from appv2.runtime.eval_clock import (
    EVAL_FROZEN_DATE_DEFAULT,
    EVAL_FROZEN_DATE_ENV,
    EVAL_FROZEN_DATE_REAL,
    eval_frozen_today,
    resolve_eval_frozen_date,
)
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
from appv2.runtime.graph import (
    ACTION_KINDS,
    DISCOVER_TOOLS,
    MODEL_KEYS,
    TASK_KINDS,
    DecisionEmission,
    parse_decision,
    reseed_approval_id,
)
from appv2.runtime.guide import (
    CLARIFY_CONTRACT,
    DECISION_CONTRACT,
    SUMMARY_CONTRACT,
    TOOLMATCH_CONTRACT,
    GuideProvider,
)
from appv2.runtime.llm import CALLER_PREFIX, Completer, GatewayChatModel
from appv2.runtime.orientation import (
    anchor_line,
    assemble_answer_instruction,
    assemble_understand_turn,
    build_understand_instruction,
    iso_day,
    render_metric_lines,
    render_relation_lines,
    render_term_lines,
    thin_object_lines,
)
from appv2.runtime.state import (
    INTENT_BATCH,
    INTENT_PRECONDITION,
    INTENT_TOOLMATCH,
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_RUNNING,
    RUN_STATUS_KINDS,
    RUN_WAITING_ASK,
    STEP_ANSWER,
    STEP_DECISION,
    STEP_DISCOVER,
    STEP_EXECUTE,
    STEP_KINDS,
    STEP_OBSERVE,
    STEP_VERIFY,
    AskChoice,
    AskRequest,
    Manifest,
    RunHandle,
    RunState,
)
from appv2.runtime.store import RunStore, ensure_agent_v2_tables
from appv2.runtime.subtask import (
    MAX_SUBTASKS_CONTRACT,
    ClarifyEmission,
    QuestionGroup,
    Subtask,
    SubtaskMatch,
    parse_question_group,
    parse_tool_match,
)
from appv2.runtime.wiring import gate_freshness

__all__ = [
    "ACTION_KINDS",
    "CALLER_PREFIX",
    "CLARIFY_CONTRACT",
    "COMMAND_ASK",
    "COMMAND_KINDS",
    "COMMAND_RESUME",
    "DECISION_CONTRACT",
    "DISCOVER_TOOLS",
    "EVAL_FROZEN_DATE_DEFAULT",
    "EVAL_FROZEN_DATE_ENV",
    "EVAL_FROZEN_DATE_REAL",
    "EVENT_ASK",
    "EVENT_CITATION",
    "EVENT_KINDS",
    "EVENT_NOTICE",
    "EVENT_OBSERVATION",
    "EVENT_STEP",
    "EVENT_TEXT",
    "EVENT_TOOL",
    "EVENT_VERDICT",
    "INTENT_BATCH",
    "INTENT_PRECONDITION",
    "INTENT_TOOLMATCH",
    "MAX_DISCOVERS_PER_ROUND_CONTRACT",
    "MAX_DISCOVERS_PER_RUN_CONTRACT",
    "MAX_EXECUTES_PER_ROUND_CONTRACT",
    "MAX_ROUNDS_CONTRACT",
    "MAX_SUBTASKS_CONTRACT",
    "MODEL_KEYS",
    "RUN_COMPLETED",
    "RUN_FAILED",
    "RUN_RUNNING",
    "RUN_STATUS_KINDS",
    "RUN_WAITING_ASK",
    "STEP_ANSWER",
    "STEP_DECISION",
    "STEP_DISCOVER",
    "STEP_EXECUTE",
    "STEP_KINDS",
    "STEP_OBSERVE",
    "STEP_VERIFY",
    "SUMMARY_CONTRACT",
    "TASK_KINDS",
    "TOOLMATCH_CONTRACT",
    "TOOL_TIMEOUT_SECONDS_CONTRACT",
    "TOTAL_SECONDS_CONTRACT",
    "AgentRuntime",
    "AskChoice",
    "AskRequest",
    "Budget",
    "ClarifyEmission",
    "CompiledContext",
    "Completer",
    "ContextBuilder",
    "DecisionEmission",
    "EventBus",
    "GatewayChatModel",
    "GraphRunExecutor",
    "GuideProvider",
    "Manifest",
    "PgCheckpointer",
    "QuestionGroup",
    "RunCommand",
    "RunEvent",
    "RunHandle",
    "RunNotFoundError",
    "RunNotSuspendedError",
    "RunState",
    "RunStore",
    "ScriptedCompleter",
    "Subtask",
    "SubtaskMatch",
    "anchor_line",
    "assemble_answer_instruction",
    "assemble_understand_turn",
    "build_understand_instruction",
    "echo_signature_hit",
    "ensure_agent_v2_tables",
    "eval_frozen_today",
    "gate_freshness",
    "iso_day",
    "new_run_id",
    "parse_decision",
    "parse_question_group",
    "parse_tool_match",
    "paste_ratio",
    "render_metric_lines",
    "render_relation_lines",
    "render_term_lines",
    "reseed_approval_id",
    "resolve_eval_frozen_date",
    "thin_object_lines",
]
