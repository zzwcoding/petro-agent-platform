"""persistence 的形状层：五张行投影＋引用载体＋检查点三表行投影＋审计记录。

形状真源＝`specs/persistence.md` 接口定义节（签名以 `specs/modules.md` `## persistence` 卡为准）；
列事实（表名／主键／列语义）真源＝`docs/runtime-refactor/recon/J-存储留痕与网关缝.md`。
本层只落形状与闭世界常量：零落盘、零行为分支（落盘与读回在 `store`／`checkpoint`／`tables`）。

两个闭世界**引 `state` 的常量、不复述取值**（规格 接口定义节）：`RunRecord.status`＝
`state.RUN_STATUS_KINDS`（四值）｜`StepRecord.step`＝`state.STEP_KINDS`（六值）。本块自有的闭世界：
`StepRecord.status` 三值（真源 `specs/bookkeeping.md` 已定口径）｜黑匣子键白名单
（`recon/J` R-J-02）｜审计 action 七值（`recon/J` R-J-05）。

时间列语义（规格「依赖与风险」4）：记录时间戳＝**该记录末次落盘时间**，由 `RunStore` 用
`infra.clock` 盖（B14 时间唯一出口）；首写时间不可回溯。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ── 闭世界：步记录 status 三值（真源 specs/bookkeeping.md 已定口径）────────────────
# 具名常量＋按名组集合（与 state 常量单点同款：族由名字构成，取值不散落）
STEP_STATUS_OK = "ok"
STEP_STATUS_FAILED = "failed"
STEP_STATUS_REFUSED = "refused"

STEP_STATUS_KINDS: frozenset[str] = frozenset(
    {STEP_STATUS_OK, STEP_STATUS_FAILED, STEP_STATUS_REFUSED}
)
STEP_STATUS_DEFAULT = STEP_STATUS_OK

# ── 闭世界：黑匣子记录键白名单（真源 recon/J R-J-02；顺序＝记录键插入顺序）────────
# 新增状态键须显式入列（R-J-03）——未入列键不进黑匣子（越界把守归 -b 票面）。
# 具名常量组元（与 state 常量单点同款）：取值逐键可见，且不落「裸字面集合」形——
# 全 V2 树有 `state::no_second_source_of_constants` 扫描裸字面集合与三族取值的交集。
_BLACKBOX_KEY_MESSAGES = "messages"
_BLACKBOX_KEY_DIALOGUE = "dialogue"
_BLACKBOX_KEY_PROCESS_NOTES = "process_notes"
_BLACKBOX_KEY_STEPS = "steps"
_BLACKBOX_KEY_OBSERVATIONS = "observations"
_BLACKBOX_KEY_NOTICES = "notices"
_BLACKBOX_KEY_QUESTION_GROUP = "question_group"
_BLACKBOX_KEY_PRECONDITION_VERDICTS = "precondition_verdicts"
_BLACKBOX_KEY_RESUME_CHOICES = "resume_choices"
_BLACKBOX_KEY_ANSWER = "answer"
_BLACKBOX_KEY_DRAFT = "draft"
_BLACKBOX_KEY_VERDICT = "verdict"
_BLACKBOX_KEY_ROUNDS = "rounds"
_BLACKBOX_KEY_DISCOVER_USED = "discover_used"
_BLACKBOX_KEY_BUDGET_HIT = "budget_hit"
_BLACKBOX_KEY_PENDING_ASK = "pending_ask"
_BLACKBOX_KEY_TASK_TYPE = "task_type"
_BLACKBOX_KEY_WINDOW_MISS_MARKS = "window_miss_marks"
_BLACKBOX_KEY_CHAIN_SWITCH_MARKS = "chain_switch_marks"
_BLACKBOX_KEY_DECISION_ERROR = "decision_error"

BLACKBOX_RECORD_KEYS: tuple[str, ...] = (
    _BLACKBOX_KEY_MESSAGES,
    _BLACKBOX_KEY_DIALOGUE,
    _BLACKBOX_KEY_PROCESS_NOTES,
    _BLACKBOX_KEY_STEPS,
    _BLACKBOX_KEY_OBSERVATIONS,
    _BLACKBOX_KEY_NOTICES,
    _BLACKBOX_KEY_QUESTION_GROUP,
    _BLACKBOX_KEY_PRECONDITION_VERDICTS,
    _BLACKBOX_KEY_RESUME_CHOICES,
    _BLACKBOX_KEY_ANSWER,
    _BLACKBOX_KEY_DRAFT,
    _BLACKBOX_KEY_VERDICT,
    _BLACKBOX_KEY_ROUNDS,
    _BLACKBOX_KEY_DISCOVER_USED,
    _BLACKBOX_KEY_BUDGET_HIT,
    _BLACKBOX_KEY_PENDING_ASK,
    _BLACKBOX_KEY_TASK_TYPE,
    _BLACKBOX_KEY_WINDOW_MISS_MARKS,
    _BLACKBOX_KEY_CHAIN_SWITCH_MARKS,
    _BLACKBOX_KEY_DECISION_ERROR,
)
# 身份面四键（真源 recon/J R-J-50）：记录恒含——`run_id` 全盖章的另一面（行为 9）。
BLACKBOX_IDENTITY_KEYS: tuple[str, ...] = ("run_id", "question", "status", "error")

# 记录键闭世界（写入把守面）：蒸馏白名单二十键 ＋ 身份面四键——越界键判失败（行为 11，把守在
# `RunStore._save_blackbox`）；**读面不校验**：迁移落地的历史行照旧可读、不回溯改写（风险 2）。
BLACKBOX_ALLOWED_KEYS: frozenset[str] = frozenset(BLACKBOX_RECORD_KEYS) | frozenset(
    BLACKBOX_IDENTITY_KEYS
)

# ── 闭世界：审计 action 七值、恒 `agent_v2.` 前缀（真源 recon/J R-J-05）────────────
AUDIT_ACTION_PREFIX = "agent_v2."
AUDIT_ACTION_RUN_CREATED = "agent_v2.run_created"
AUDIT_ACTION_RUN_COMPLETED = "agent_v2.run_completed"
AUDIT_ACTION_RUN_FAILED = "agent_v2.run_failed"
AUDIT_ACTION_REFUSED = "agent_v2.refused"
AUDIT_ACTION_EXTABLE_APPROVED = "agent_v2.extable_approved"
AUDIT_ACTION_EXTABLE_REJECTED = "agent_v2.extable_rejected"
AUDIT_ACTION_BAN_EXEMPT = "agent_v2.ban_exempt"

AUDIT_ACTIONS: frozenset[str] = frozenset(
    {
        AUDIT_ACTION_RUN_CREATED,
        AUDIT_ACTION_RUN_COMPLETED,
        AUDIT_ACTION_RUN_FAILED,
        AUDIT_ACTION_REFUSED,
        AUDIT_ACTION_EXTABLE_APPROVED,
        AUDIT_ACTION_EXTABLE_REJECTED,
        AUDIT_ACTION_BAN_EXEMPT,
    }
)

# ── 五张行投影 ───────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class RunRecord:
    """`agent_v2_run` 行的投影（列事实真源 `recon/J`：PK run_id／`followup_of` 空串＝链根）。

    `supplements`（2026-10-17 EB3 D1）＝增补面条目列（JSON 数组，同 `answer` 先例）——程序
    追加内容（分源块／归属块／引用清单／血缘五要素）的落库形，条目 `{block, text}`；缺位＝
    空列表（旧行如实读为空列，不回溯改写）。
    """

    run_id: str
    question: str
    actor: str  # 行级身份字符串投影（对象面＝state 的 AskRequest.actor；转换点唯一在编排块）
    status: str  # 闭世界＝state.RUN_STATUS_KINDS（四值）——写入把守见行为 2
    answer: str | None
    error: str | None
    manifest_digest: str | None
    followup_of: str
    created_at: datetime
    updated_at: datetime
    supplements: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class StepRecord:
    """`agent_v2_step` 行的投影（列事实真源 `recon/J` `AgentV2Step`；PK＝`(run_id, seq)`）。

    `payload` **原样保真**（行为 8）：不裁剪、不做假值归一——空 `{}` 与「无 payload」(`None`)
    读回必须可区分（现状 `or None` 归一是缺陷，见风险 3）。
    """

    run_id: str
    seq: int
    step: str  # 闭世界＝state.STEP_KINDS（六值）
    status: str  # 闭世界＝ok｜failed｜refused
    title: str
    manifest: dict[str, Any] | None
    payload: dict[str, Any] | None
    created_at: datetime  # 该记录末次落盘时间（现状列如实投影——recon/J；首写时间不可回溯）


@dataclass(frozen=True, slots=True)
class BlackBox:
    """`agent_v2_blackbox` 行的投影（PK run_id；只追加、首写为准——行为 4）。

    `record` 键白名单闭世界＝`BLACKBOX_RECORD_KEYS`（真源 `recon/J` R-J-02／R-J-03）。
    """

    run_id: str
    record: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class BlobRef:
    """大结果原文的引用载体回执（可寻址 handle；行为 10）。

    `handle` 与 `execution.MaterialRef.handle` **同源同值**（`specs/execution.md`：窗口侧材料条目
    `{handle, summary, row_count}`）——两处键名统一 `handle`，本块不另起第二个名字；载体的原文
    存放实现＝本块簿记表件 `agent_v2_blob`（阶段 5 定），语义不随载体变。
    """

    handle: str
    bytes: int
    sha256: str


# ── 检查点三表行投影（框架无关；列名映射：ns↔checkpoint_ns、kind↔type、
#    metadata↔metadata_json——投影改名不换列，真源 recon/J 表事实）────────────────


@dataclass(frozen=True, slots=True)
class CheckpointRow:
    """`agent_v2_checkpoint` 行的投影。`kind` ＝行类型标签（框架无关值见 `checkpoint` 模块）。"""

    thread_id: str
    ns: str
    checkpoint_id: str
    parent_checkpoint_id: str | None
    kind: str
    checkpoint: bytes
    metadata: bytes


@dataclass(frozen=True, slots=True)
class CheckpointBlobRow:
    """`agent_v2_checkpoint_blob` 行的投影（PK `(thread_id, ns, channel, version)`）。"""

    thread_id: str
    ns: str
    channel: str
    version: str
    kind: str
    blob: bytes


@dataclass(frozen=True, slots=True)
class CheckpointWriteRow:
    """`agent_v2_checkpoint_write` 行的投影（PK `(thread_id, ns, checkpoint_id, task_id, idx)`
    ——真源 `recon/J` 表事实）。"""

    thread_id: str
    ns: str
    checkpoint_id: str
    task_id: str
    idx: int
    channel: str
    kind: str
    blob: bytes


# ── 审计留痕（四要素；Owner 裁决 walk/16 §七 Q-C）──────────────────────────────


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """审计留痕：主体（`who`；`scope` 是主体的范围细化——会话线程／子问题域）／意图（`action`；
    `authorization` 是其授权依据——角色／审批单号，无则空串）／事实（`facts`）／结果（`evidence`）
    四要素齐备；缺项判失败（行为 5，-b 票面把守）。

    `run_id` ＝范围键：四类记录同源可聚合（行为 9）。既成审计行不可改写（Owner 裁决
    「原始事实不可改写」）——本块不提供任何改写入口。
    """

    run_id: str
    who: str
    scope: str
    action: str
    authorization: str
    facts: str
    evidence: dict[str, Any]
