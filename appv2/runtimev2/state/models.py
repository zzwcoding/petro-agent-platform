"""state 的形状层：运行状态、模型调用 Manifest、受理与回执载荷、限额参数与触界形状。

形状真源＝`specs/state.md` 接口定义节（签名以 `specs/modules.md` `## state` 卡为准）；
`RunState` 字段集真源＝`docs/runtime-refactor/synth/S5-RunState字段矩阵.md`（首列 53 字段——
定稿 50 ＋ V2-82a 追加 `subjects`／`terms` 2 ＋ V2-82b 追加 `pending_subject_options` 1）。
本层纯形状：零行为分支、零模型调用、零落盘、零业务语义判断；写函数零供给——共享写口归
`bookkeeping`（`specs/bookkeeping.md`）。常量单点在 `constants`（三族闭世界＋限额数值真源）、
触界判定在 `limits`（纯函数 `check_limits`）。
"""

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, get_args

from appv2.infra.security import Actor
from appv2.runtimev2.state.constants import (
    ASK_CAP,
    INTENT,
    MAX_DISCOVERS_PER_ROUND,
    MAX_DISCOVERS_PER_RUN,
    MAX_EXECUTES_PER_ROUND,
    MAX_ROUNDS,
    RUN_RUNNING,
    RUN_STATUS_KINDS,
    TOOL_TIMEOUT_SECONDS,
    TOTAL_SECONDS,
)

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
    """限额参数表：键集闭世界七键，数值真源＝`recon/K` R-K-72…R-K-76（行为 10）。

    缺省面逐键引 `constants` 的数值单点（禁散落字面量）；键名与 `LimitHit.limit` 闭世界同名
    ——判定面按名取上限（`limits.check_limits`），不另立第二套键名。
    """

    rounds: int = MAX_ROUNDS
    discovers_per_round: int = MAX_DISCOVERS_PER_ROUND
    executes_per_round: int = MAX_EXECUTES_PER_ROUND
    seconds: float = TOTAL_SECONDS
    tool_timeout: float = TOOL_TIMEOUT_SECONDS
    discovers_per_run: int = MAX_DISCOVERS_PER_RUN
    ask_cap: int = ASK_CAP


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

    def __post_init__(self) -> None:
        # 行为 12 的形态互斥（fail-closed）：`hit` 非空 ⇔ `notice` 非 None——触界不得静默、
        # 未触界不得凭空产注记。只判三键**形状**，不复述 `notice.type` 的取值集（归 `transport`）。
        if bool(self.hit) != (self.notice is not None):
            raise ValueError(
                "Convergence 形态互斥：hit 非空 ⇔ notice 非 None（触界不得静默／未触界不得产注记）"
            )
        if self.notice is not None and set(self.notice) != {"type", "gates", "content"}:
            keys = "／".join(sorted(self.notice))
            raise ValueError(f"Convergence.notice 必须恰三键 type／gates／content（实为 {keys}）")


# ── 运行状态（字段集＝synth/S5 矩阵全量，逐字段读写方见该表）───────────────────


@dataclass(slots=True)
class RunState:
    """可变运行状态图状态（非 frozen）——全体 import 的形状面，不含行为。"""

    run_id: str = ""
    question: str = ""
    # 行级身份字符串投影（对象面在 `AskRequest.actor`）
    # 转换点唯一在 orchestration 受理段（规格「依赖与风险」5）
    actor: str = ""
    status: str = RUN_RUNNING
    followup_of: str = ""
    empty_probes: list[str] = field(default_factory=list)
    understanding: str = ""
    metric_candidates: list[str] = field(default_factory=list)
    # 题面主体/术语（V2-82a 2026-10-17 additive——理解相位写、后续相位读；默认空＝零漂移）
    subjects: tuple[str, ...] = ()
    terms: tuple[str, ...] = ()
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
    # 对象歧义 ask 的实例候选名单（V2-82b 2026-10-17 additive——发射时落、恢复时消费并清空；
    # 默认空＝零漂移）。语义＝`pending_ask` 是「对象歧义」那一问时所给的**油田实例选项**，
    # 恢复腿据此把选中项映射进 `state.subjects`（哨兵 `__all_fields__`＝都要）。
    pending_subject_options: tuple[str, ...] = ()
    # 澄清问答闭环三字段（V2-118 2026-10-18 additive——默认空＝零漂移；真源
    # `tickets/v2/V2-118-澄清问答闭环.md` 任务 1~4）：
    # - `answer_slots`＝**回答由程序落位**的承载位（键＝ask 帧 `detail.slot` 槽位标签，
    #   值＝用户所选原话）——恢复腿按该问的槽位标签写进对应状态位，后续决策轮经
    #   「用户已回答『{slot}』＝{value}」回喂行进上下文（不要求模型把回答编码进没有该字段的合同）；
    # - `asked_fingerprints`＝**同问指纹**列（`clarification.constants.ask_fingerprint` 单点产
    #   ——同一（槽位，选项集）问过一次即不再问；命中 ⇒ 降级一次性默认＋注记，不占 `ask_cap`）；
    # - `degraded_slots`＝已降级槽位→一次性默认值的如实留痕（降级路径的机读信号面；注记文本
    #   随下一决策轮增量条在场，答案据此注明「用了默认口径」）。
    answer_slots: dict[str, str] = field(default_factory=dict)
    asked_fingerprints: list[str] = field(default_factory=list)
    degraded_slots: dict[str, str] = field(default_factory=dict)
    observations: list[dict[str, Any]] = field(default_factory=list)
    # 主体反思逐来源判值（V2-117 2026-10-18 additive——材料到手后（L2 并集池）由编排写、
    # 核验相位读；默认空＝零漂移）。键＝来源名（观察 `source`），值 ∈ `SUBJECT_VERDICTS`
    # （属／不属／未知）；判据单点＝`orchestration.subjects.reflect_subjects`。
    subject_reflection: dict[str, str] = field(default_factory=dict)
    resume_choices: list[dict[str, Any]] = field(default_factory=list)
    approved_ids: list[str] = field(default_factory=list)
    # 作答侧有界再探（V2-96 D5 2026-10-18 additive——独立计数，默认零值＝零漂移）：
    # `explore_rounds`＝已执行的再探轮数（≤`MAX_EXPLORE_ROUNDS`，不占澄清轮／不动 discover 预算）；
    # `explore_fingerprints`＝已处理请求指纹列（`tool|query` 或 `tool|report_id|section`——拒重）；
    # `pending_explore`＝作答相位落的待执行 explore 意图投影（编排消费后清）。
    explore_rounds: int = 0
    explore_fingerprints: list[str] = field(default_factory=list)
    pending_explore: dict[str, Any] | None = None
    # 核验失败＝回炉修复（V2-115 2026-10-18 additive——独立计数，默认零值＝零漂移）：
    # `repair_rounds`＝已执行的**回炉改写**轮数（≤`MAX_REPAIR_ROUNDS`；到顶后回炉环转模型缺位
    # 说明，不再改写）。不占澄清轮／不动 discover 预算（先例 `explore_rounds`）。
    repair_rounds: int = 0
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

    def __post_init__(self) -> None:
        # 行为 9：状态字段取值必须 ∈ 对应闭世界，越界抛错（fail-closed，不吞错、不返回哨兵）。
        # `next_intent == ""`＝未设态（字段缺省；旧码路由以「`current or INTENT_ANSWER`」兜底），
        # 不在 INTENT 十值内但合法——故只在非空时把守。后续赋值面的把守归唯一写口
        # `bookkeeping.set_intent`（`specs/bookkeeping.md` 行为 6）。
        if self.status not in RUN_STATUS_KINDS:
            values = "／".join(sorted(RUN_STATUS_KINDS))
            raise ValueError(
                f"RunState.status 越界（闭世界 RUN_STATUS_KINDS＝{values}）：{self.status!r}"
            )
        if self.next_intent and self.next_intent not in INTENT:
            values = "／".join(sorted(INTENT))
            raise ValueError(
                f"RunState.next_intent 越界（闭世界 INTENT＝{values}，或未设空串）："
                f"{self.next_intent!r}"
            )
