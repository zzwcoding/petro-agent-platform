"""runtime.state —— RunState 自有状态 schema 与 run 面 schema（ADR-0002 红线③）。

三红线之「state schema 自有（checkpointer 仅存储）」的落点：ReAct loop 的图状态
RunState 为本模块自定义 dataclass（LangGraph StateGraph 只把它当 schema 消费，
checkpoint 落库内容＝本 schema 的逐字段投影）；step 类型/Manifest/ASK 帧载荷
全部自有，不借框架类型。

V2-31 ReAct 重构（Owner 2026-10-09 拍板——票面 wire 演进）：step 类型六值闭世界
按 ReAct 周期重定＝decision/discover/execute/observe/verify/answer（轮＝LLM 决策
周期；discover/execute＝固定代码执行的工具步；verify 保留零 LLM）。

票面点名符号随本票定稿：
- RunState：图状态（六节点共享读写）；
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

# ---------- step 类型六值闭世界（ReAct 周期——wire 演进后只许六种） ----------

STEP_DECISION = "decision"
STEP_DISCOVER = "discover"
STEP_EXECUTE = "execute"
STEP_OBSERVE = "observe"
STEP_VERIFY = "verify"
STEP_ANSWER = "answer"
STEP_KINDS: frozenset[str] = frozenset(
    {STEP_DECISION, STEP_DISCOVER, STEP_EXECUTE, STEP_OBSERVE, STEP_VERIFY, STEP_ANSWER}
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
INTENT_DECISION = "decision"
INTENT_DISCOVER = "discover"
INTENT_EXECUTE = "execute"
INTENT_OBSERVE = "observe"
INTENT_VERIFY = "verify"
INTENT_ANSWER = "answer"
INTENT_END = "end"
# V2-34 四相位路由意图（clarify 经既有 INTENT_DECISION 值承载——图装配按
# four_phase 把该值重定向 clarify 节点；三相新意图随本票加入闭世界）。
INTENT_TOOLMATCH = "toolmatch"
INTENT_PRECONDITION = "precondition"
INTENT_BATCH = "batch"


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
    """提问受理（specs/agent-loop.md 接口定义节原形：{question, actor}）。

    followup_of（V2-38 追问续会话）：非空＝追问形态——新 run 播种该前轮线程的
    消息历史（前轮问句/决策/台账/答案随追问进上下文）；前轮须 completed
    （未收口轮走 resume——执行器把守，映射 404/409）。
    """

    question: str
    actor: Actor
    followup_of: str = ""


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
    """ReAct loop 图状态（自有 schema——checkpointer 仅存储本 schema 的投影）。

    字段值全部 JSON 原语（observations/emission 均为 dict 投影）——checkpointer
    序列化面最简、跨进程恢复无损。预算闸参数随状态走（行为约定 7 的 ReAct
    语义：轮数≤3／轮内发现≤2＋主执行≤2／总时长 300s／单工具 30s，测试可收窄）。
    """

    run_id: str = ""
    question: str = ""
    actor: str = ""  # 行级身份（ctx.actor 注入——身份只从 ctx 进）
    status: str = RUN_RUNNING
    # —— understand 产物 ——
    understanding: str = ""
    metric_candidates: list[str] = field(default_factory=list)  # FX-13 候选集
    # —— V2-34 子任务图产物（四相位——ADR-0005） ——
    # 词典层全量注入（拍板 a）：第 1 次澄清入口从 ledger_dump 缝取一次（现行态
    # 快照），随 checkpoint 走——后续轮复用不再取。
    ledger_dump: dict[str, Any] | None = None
    # 相位①产物：问题组（subtasks[{id/question/ledger_notes/chain?/tool?}]——
    # 相位②匹配定案后 subtasks 就地补 tool/chain/plan/retrieval_need/caliber_key）。
    question_group: dict[str, Any] | None = None
    # 相位②产物：matches（子问题→工具链定案列——批量执行输入）。
    tool_matches: list[dict[str, Any]] = field(default_factory=list)
    # 相位③产物：四态判定列（前置条件机 payload——blocked_ask 挂起帧随行）。
    precondition_verdicts: list[dict[str, Any]] = field(default_factory=list)
    # 相位④产物：子问题执行结果列（{id,status: ok|failed|refused,reason,
    # obs_count,fingerprint}）——回炉不重跑的簿记面（R4：成功子问题指纹零重复）。
    subtask_results: list[dict[str, Any]] = field(default_factory=list)
    # 全 run 发现预算已用数（澄清相位 ≤10 合同闸判据——Owner 拍板放宽）。
    discover_used: int = 0
    # —— 消息历史簿记（ADR-0006/V2-38）：understand/decision/answer 的调用与输出、
    # 工具执行台账（参数 → 结果：N 行／分型拒因：校验拒／暂不可用／闸拒）、拒因回
    # 喂、用户澄清/审批回收
    # 全部作为轮次进历史；后续每步在完整历史上续写（替换「每步全新两条消息」伪
    # 多轮形态）。值全 JSON 原语（checkpointer 序列化面最简）；追问续会话经
    # executor 播种前轮线程历史（followup_of）。
    history: list[dict[str, str]] = field(default_factory=list)
    # —— decision 产物（ReAct 决策出口——行为断言锁定面） ——
    rounds: int = 0  # 已消耗的 LLM 决策周期数（≤3 轮上限闸判据）
    task_type: str = ""  # 末次执行发射的任务型 data|knowledge|mixed
    decision_error: str = ""  # 末次拒因（schema 校验/工具 bad_args——回喂重决策）
    user_hint: str = ""  # 澄清回收的用户补充（decision 下轮消费后清空）
    pending_discovers: list[dict[str, Any]] = field(default_factory=list)
    pending_plan: dict[str, Any] | None = None  # data_query plan_draft（data|mixed）
    pending_retrieval: dict[str, Any] | None = None  # doc_retrieve args（knowledge|mixed）
    last_execute: dict[str, Any] | None = None  # 末次主执行载荷（审批批准后重跑）
    # 主执行实录（V2-37 同参重投机器闸）：实际执行过的主执行载荷规范指纹列
    # （execute 支 ok/ask 逐支记一条——decision 出口对同参二次发射比对该簿记；
    # 审批重投／retryable 同参重试走各自通道不经 decision 出口，不受闸辖）。
    executed_payloads: list[str] = field(default_factory=list)
    # 连续澄清 ask 计数（run 生命期累计不清零——P-024b 疑点2）：第 2 次 ask
    # 截断带材料直答。
    consecutive_asks: int = 0
    # —— 工具步产物 ——
    tool_retries: dict[str, int] = field(default_factory=dict)
    # retryable 同参重试一次（合同上限）——按工具名计数（P-024b C2：discover 链
    # 上的重试不挤占 execute 的重试份额）。
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
    draft_kind: str = ""  # ""=LLM 草稿待核验；"direct"＝确定性直答（拒答/闸拒——免起草免核验）
    answer: str = ""
    verdict: dict[str, Any] | None = None
    manifest_digest: str = ""  # Manifest 摘要（sha256——answer 步收口）
    # —— 全程累积 ——
    notices: list[dict[str, Any]] = field(default_factory=list)
    manifests: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    # —— 预算闸（ReAct 语义；随状态走，跨进程恢复后仍生效） ——
    budget: dict[str, float] = field(default_factory=dict)
    started_monotonic: float = 0.0
    deadline_monotonic: float = 0.0
    budget_hit: list[str] = field(default_factory=list)
    # —— 路由意图与错误 ——
    next_intent: str = ""
    error: str | None = None
