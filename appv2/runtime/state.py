"""runtime.state —— RunState 自有状态 schema 与 run 面 schema（ADR-0002 红线③）。

三红线之「state schema 自有（checkpointer 仅存储）」的落点：六步 loop 的图状态
RunState 为本模块自定义 dataclass（LangGraph StateGraph 只把它当 schema 消费，
checkpoint 落库内容＝本 schema 的逐字段投影）；step 类型/Manifest/ASK 帧载荷
全部自有，不借框架类型。

票面点名符号随本票定稿：
- RunState：图状态（understand/plan/tool/observe/verify/answer 六节点共享读写）；
- AskRequest＝{question, actor}（specs/agent-loop.md 接口定义节原形）；
- AskChoice＝{value, approval_id?}（resume 的选择——clarify 选窗文本／审批批准
  驳回＋审批单号留痕，接线①）；
- RunHandle＝{run_id, stream}（ask/resume 的受理回执——事件流游标消费面）；
- Manifest 七字段（source_type/source_id/version/trust_level/selected_reason/
  token_count/transform——specs/agent-loop.md 行为约定 2 合同形）。

零框架依赖；字段值全部 JSON 原语可投影（checkpointer 序列化面最简）。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from appv2.infra.security import Actor
from appv2.runtime.events import RunEvent

# ---------- step 类型六值闭世界（行为约定 1：只许六种） ----------

STEP_UNDERSTAND = "understand"
STEP_PLAN = "plan"
STEP_TOOL = "tool"
STEP_OBSERVE = "observe"
STEP_VERIFY = "verify"
STEP_ANSWER = "answer"
STEP_KINDS: frozenset[str] = frozenset(
    {STEP_UNDERSTAND, STEP_PLAN, STEP_TOOL, STEP_OBSERVE, STEP_VERIFY, STEP_ANSWER}
)

# ---------- run 状态机（行为约定 8：running→waiting_ask→（resume）→终态） ----------

RUN_RUNNING = "running"
RUN_WAITING_ASK = "waiting_ask"
RUN_COMPLETED = "completed"
RUN_FAILED = "failed"
RUN_STATUS_KINDS: frozenset[str] = frozenset(
    {RUN_RUNNING, RUN_WAITING_ASK, RUN_COMPLETED, RUN_FAILED}
)

# 节点间显式路由意图（next_intent 闭世界——条件边唯一判据）。
INTENT_PLAN = "plan"
INTENT_TOOL = "tool"
INTENT_OBSERVE = "observe"
INTENT_VERIFY = "verify"
INTENT_ANSWER = "answer"
INTENT_END = "end"


@dataclass(frozen=True, slots=True)
class Manifest:
    """模型调用 Manifest（行为约定 2——随 step 存档，过程态簿记）。"""

    source_type: list[str] = field(default_factory=list)
    source_id: list[str] = field(default_factory=list)
    version: list[str | None] = field(default_factory=list)
    trust_level: list[str] = field(default_factory=list)
    selected_reason: str = ""
    token_count: int = 0
    transform: str = "filter→rank→budget→cite"

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_type": list(self.source_type),
            "source_id": list(self.source_id),
            "version": list(self.version),
            "trust_level": list(self.trust_level),
            "selected_reason": self.selected_reason,
            "token_count": self.token_count,
            "transform": self.transform,
        }


@dataclass(frozen=True, slots=True)
class AskRequest:
    """提问受理（specs/agent-loop.md 接口定义节原形：{question, actor}）。"""

    question: str
    actor: Actor


@dataclass(frozen=True, slots=True)
class AskChoice:
    """resume 的选择（clarify＝选窗文本；审批＝批准/驳回＋审批单号留痕——接线①）。"""

    value: str
    approval_id: str | None = None

    def as_payload(self) -> dict[str, Any]:
        return {"value": self.value, "approval_id": self.approval_id}


@dataclass(frozen=True, slots=True)
class RunHandle:
    """run 受理回执（接口定义节原形：{run_id, stream}）。"""

    run_id: str
    stream: AsyncIterator[RunEvent]


@dataclass(slots=True)
class RunState:
    """六步 loop 图状态（自有 schema——checkpointer 仅存储本 schema 的投影）。

    字段值全部 JSON 原语（observations/frames 均为 dict 投影）——checkpointer
    序列化面最简、跨进程恢复无损。预算三闸参数随状态走（行为约定 7 合同值
    max_steps=8／总时长 300s／单工具 30s，测试可收窄）。
    """

    run_id: str = ""
    question: str = ""
    actor: str = ""  # 行级身份（ctx.actor 注入——身份只从 ctx 进）
    status: str = RUN_RUNNING
    # —— understand 产物 ——
    understanding: str = ""
    metric_candidates: list[str] = field(default_factory=list)  # FX-13 候选集
    # —— plan 产物（行为约定 3）——
    tool_name: str | None = None
    tool_args: dict[str, Any] = field(default_factory=dict)
    plan_repairs: int = 0  # 校验不过→repair 一次（合同上限）
    repairs_since_input: int = 0  # 距上一次用户输入的 repair 次数（用户输入重置）
    replan_hint: str = ""  # 澄清回收的补充（plan 下轮消费后清空）
    plan_error: str = ""  # 计划解析失败缘由（repair 提示素材）
    # —— tool 产物 ——
    tool_retries: int = 0  # retryable 同参重试一次（合同上限）
    extable_rounds: int = 0  # 外表审批批准后的重跑轮次（骨架上限 1）
    last_result: dict[str, Any] | None = None  # ToolResult dict 投影
    pending_ask: dict[str, Any] | None = None  # AskFrame dict 投影（挂起帧）
    # —— observe 产物 ——
    observations: list[dict[str, Any]] = field(default_factory=list)  # 全局 [n] 序
    # —— resume 留痕（接线①）——
    resume_choices: list[dict[str, Any]] = field(default_factory=list)
    approved_ids: list[str] = field(default_factory=list)
    # —— verify/answer 产物 ——
    draft: str = ""
    answer: str = ""
    verdict: dict[str, Any] | None = None
    manifest_digest: str = ""  # Manifest 摘要（sha256——answer 步收口）
    # —— 全程累积 ——
    notices: list[dict[str, Any]] = field(default_factory=list)
    manifests: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    # —— 预算三闸（行为约定 7；随状态走，跨进程恢复后仍生效） ——
    budget: dict[str, float] = field(default_factory=dict)
    started_monotonic: float = 0.0
    deadline_monotonic: float = 0.0
    segment_step_base: int = 0  # 本段步数基线（挂起等人工不计预算——恢复段重置）
    budget_hit: list[str] = field(default_factory=list)
    # —— 路由意图与错误 ——
    next_intent: str = ""
    error: str | None = None
