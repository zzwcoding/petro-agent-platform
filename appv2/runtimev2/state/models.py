"""state 的形状层：运行状态、模型调用 Manifest、受理与回执载荷、限额参数与触界形状。

形状真源＝`specs/state.md` 接口定义节（签名以 `specs/modules.md` `## state` 卡为准）；
`RunState` 字段集真源＝`docs/runtime-refactor/synth/S5-RunState字段矩阵.md`（首列 50 字段）。
本层纯形状：零行为分支、零模型调用、零落盘、零业务语义判断；写函数零供给——共享写口归
`bookkeeping`（`specs/bookkeeping.md`）。
"""

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, get_args

from appv2.infra.security import Actor

# ── 对话层来源闭世界（规格 行为 6 明列三值；新增第四值须走裁决/ADR）──────────────
DialogueOrigin = Literal["user_verbatim", "assistant_final", "clarify_approval_replay"]
DIALOGUE_ORIGINS: frozenset[str] = frozenset(get_args(DialogueOrigin))
# origin↔role 一致性不变量（规格 行为 6：user_verbatim⇒user／assistant_final⇒assistant／
# clarify_approval_replay⇒user）——对话层写口（`bookkeeping.append_dialogue`）的把守面。
DIALOGUE_ORIGIN_ROLES: Mapping[str, str] = {
    "user_verbatim": "user",
    "assistant_final": "assistant",
    "clarify_approval_replay": "user",
}

# ── 受理载荷两枚举闭世界（规格 行为 14）──────────────────────────────────────
AskChoiceKind = Literal["clarify", "external_table_approval"]
AskDecision = Literal["approve", "reject"]

_ASK_CHOICE_KINDS: frozenset[str] = frozenset(get_args(AskChoiceKind))
_ASK_DECISIONS: frozenset[str] = frozenset(get_args(AskDecision))

# ── 触界命中项闭世界（`LimitHit.limit`，规格 接口定义节）────────────────────────
LimitKind = Literal[
    "rounds",
    "discovers_per_round",
    "executes_per_round",
    "seconds",
    "tool_timeout",
    "discovers_per_run",
    "ask_cap",
]


# ── 模型调用 Manifest ────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Manifest:
    """模型调用 Manifest：合同七字段＋材料三机检字段；缺省面真源 `recon/I2a` R-I2a-05。"""

    source_type: list[str] = field(default_factory=list)
    source_id: list[str] = field(default_factory=list)
    version: list[str | None] = field(default_factory=list)
    trust_level: list[str] = field(default_factory=list)
    selected_reason: str = ""
    token_count: int = 0
    transform: str = "filter→rank→budget→cite"
    material_total: int = 0
    material_rendered: int = 0
    material_truncated: bool = False

    def as_dict(self) -> dict[str, Any]:
        """全键恒出投影（行为 15）：键名与字段同名；列表值返回拷贝——改返回值不改原对象。"""
        return {
            "source_type": list(self.source_type),
            "source_id": list(self.source_id),
            "version": list(self.version),
            "trust_level": list(self.trust_level),
            "selected_reason": self.selected_reason,
            "token_count": self.token_count,
            "transform": self.transform,
            "material_total": self.material_total,
            "material_rendered": self.material_rendered,
            "material_truncated": self.material_truncated,
        }


# ── 受理载荷与回执 ───────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class AskRequest:
    """受理载荷：三形态——仅 `question`＝提问｜`resume_run_id`＝断线重连｜
    `question`＋`followup_run_id`＝追问续会话；`resume_run_id` 与 `followup_run_id`
    同在场＝判失败（行为 14）。`actor` 为必填 kw-only（否则「必填字段跟在缺省字段后」不合法）。
    """

    question: str | None = None
    resume_run_id: str | None = None
    followup_run_id: str | None = None
    actor: Actor = field(kw_only=True)

    def __post_init__(self) -> None:
        if self.resume_run_id is not None and self.followup_run_id is not None:
            raise ValueError(
                "受理形态互斥：resume_run_id（断线重连）与 followup_run_id（追问续会话）不得同在场"
            )


@dataclass(frozen=True, slots=True)
class AskChoice:
    """resume 载荷：`kind`／`decision` 两枚举闭世界（行为 14），越界值判失败。"""

    kind: AskChoiceKind
    choice: str | None = None
    decision: AskDecision | None = None
    approval_id: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in _ASK_CHOICE_KINDS:
            kinds = "／".join(sorted(_ASK_CHOICE_KINDS))
            raise ValueError(f"AskChoice.kind 越界（闭世界 {kinds}）：{self.kind!r}")
        if self.decision is not None and self.decision not in _ASK_DECISIONS:
            decisions = "／".join(sorted(_ASK_DECISIONS))
            raise ValueError(
                f"AskChoice.decision 越界（闭世界 {decisions} 或 None）：{self.decision!r}"
            )


@dataclass(frozen=True, slots=True)
class RunHandle:
    """run 受理回执。`cursor`＝全流单调断线游标（＝下一帧 seq；真源 `transport.md` 行为 3／5）。"""

    run_id: str
    # 元素类型＝`transport` 的帧对象 `{seq, event, data}`——本块守 R4 不 import，故只作字符串前向
    # 引用：本块不定义它的形状，也不得给它安第二套含义（禁当载荷 dict 别名）。
    stream: AsyncIterator["SseEvent"]  # type: ignore[name-defined]  # noqa: F821
    cursor: int


# ── 限额参数与触界判定结果 ───────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Budget:
    """限额参数表：键集闭世界七键，数值真源＝`recon/K` R-K-72…R-K-76（行为 10）。"""

    rounds: int = 3
    discovers_per_round: int = 2
    executes_per_round: int = 2
    seconds: float = 300.0
    tool_timeout: float = 30.0
    discovers_per_run: int = 10
    ask_cap: int = 6


@dataclass(frozen=True, slots=True)
class LimitHit:
    """触界命中项：`Convergence.hit` 的元素类型（`limit` 闭世界／`used`／`cap`）。"""

    limit: LimitKind
    used: float
    cap: float


@dataclass(frozen=True, slots=True)
class Convergence:
    """触界判定结果（行为 12）。

    `hit` 空元组＝未触界；`notice` 触界必带（恰三键）、未触界恒 `None`。
    """

    hit: tuple[LimitHit, ...]
    notice: dict[str, Any] | None


# ── 运行状态（字段集＝synth/S5 矩阵全量，逐字段读写方见该表）───────────────────


@dataclass(slots=True)
class RunState:
    """可变运行状态图状态（非 frozen）——全体 import 的形状面，不含行为。"""

    run_id: str = ""
    question: str = ""
    # 行级身份字符串投影（对象面在 `AskRequest.actor`）
    # 转换点唯一在 orchestration 受理段（规格「依赖与风险」5）
    actor: str = ""
    status: str = "running"
    followup_of: str = ""
    empty_probes: list[str] = field(default_factory=list)
    understanding: str = ""
    metric_candidates: list[str] = field(default_factory=list)
    ledger_dump: dict[str, Any] | None = None
    question_group: dict[str, Any] | None = None
    tool_matches: list[dict[str, Any]] = field(default_factory=list)
    precondition_verdicts: list[dict[str, Any]] = field(default_factory=list)
    subtask_results: list[dict[str, Any]] = field(default_factory=list)
    chain_switch_marks: dict[str, str] = field(default_factory=dict)
    window_miss_marks: dict[str, str] = field(default_factory=dict)
    discover_used: int = 0
    messages: list[dict[str, str]] = field(default_factory=list)  # 对话链，只追加不改写（pin-22）
    contracts_appended: list[str] = field(default_factory=list)  # 相位合同一次性标记（pin-24）
    process_notes: list[dict[str, str]] = field(default_factory=list)  # 过程档案（有界摘要）
    dialogue: list[dict[str, str]] = field(default_factory=list)  # 自然对话层（条目三键，pin-26）
    dialogue_view_tokens: int = 0  # compaction 触发参数（流水 49②）
    schema_version: int = 3  # checkpoint 版本；真值真源 synth/S3 C-07
    rounds: int = 0
    task_type: str = ""
    decision_error: str = ""
    user_hint: str = ""
    budget_reject_streak: int = 0
    pending_discovers: list[dict[str, Any]] = field(default_factory=list)
    pending_plan: dict[str, Any] | None = None
    pending_retrieval: dict[str, Any] | None = None
    last_execute: dict[str, Any] | None = None
    executed_payloads: list[str] = field(default_factory=list)
    tool_retries: dict[str, int] = field(default_factory=dict)
    extable_rounds: int = 0
    last_result: dict[str, Any] | None = None
    pending_ask: dict[str, Any] | None = None
    observations: list[dict[str, Any]] = field(default_factory=list)
    resume_choices: list[dict[str, Any]] = field(default_factory=list)
    approved_ids: list[str] = field(default_factory=list)
    draft: str = ""
    draft_kind: str = ""  # ""=待核验草稿；"direct"=确定性直答（释义真源 specs/answering.md）
    answer: str = ""
    verdict: dict[str, Any] | None = None
    manifest_digest: str = ""
    notices: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    budget: Budget = field(default_factory=Budget)
    budget_hit: list[str] = field(default_factory=list)
    next_intent: str = ""
    error: str | None = None
