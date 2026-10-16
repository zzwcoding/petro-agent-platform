"""execution 的形状层：`specs/execution.md` 接口定义节六形状（:35–:60 逐字）。

真源＝`specs/execution.md` 接口定义节（签名以 `specs/modules.md` `## execution` 卡为准）：
`execute(state) -> ExecutionOutcome` 的返回形与两处闭世界。本层**纯形状＋结构把守**：
零行为分支（除闭世界／形态越界即拒的 fail-closed 把守外）、零 IO、零模型、零业务语义判断。

- `MaterialRef`：大结果原文的窗口侧凭据（`handle` 稳定可寻址／`summary` 窗口内只留的摘要／
  `row_count` 行数）——与 `persistence.BlobRef.handle` **同源同值**（真源 `specs/persistence.md`
  接口定义节：`execution` 产窗口侧材料条目、`persistence` 产载体回执，两处键名统一为 `handle`）。
- `Observation`：执行块交付的观察（全局 `[n]` 序——引标与答案引用同一套序号）；**出处必带**
  （行为 9：缺出处＝判失败——构造期 fail-closed 抛错，不猜、不补）。
- `SubtaskExec`：逐子问题执行状态；**`exec_status`（过程）与 `answered`（业务）分开记**
  （行为 5：`exec_status="ok"` 不等于 `answered=True`）。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from appv2.runtimev2.execution.constants import ERROR_CATEGORIES, EXEC_STATUS_KINDS


@dataclass(frozen=True, slots=True)
class MaterialRef:
    """大结果原文的稳定引用（窗口侧只留 `summary` ＋ `row_count`；原文在 `persistence`）。"""

    handle: str  # 稳定引用（可寻址——行为 4／5「引用可寻址」）
    summary: str  # 窗口内只留的摘要（截断经 persistence 截断单点、带可见标记）
    row_count: int  # 被落引用原文的行数

    def __post_init__(self) -> None:
        if not self.handle:
            raise ValueError(
                "MaterialRef.handle 必填（稳定引用须可寻址——行为 4／5：写了找不回＝静默丢材料）"
            )
        if self.row_count < 0:
            raise ValueError(f"MaterialRef.row_count 不得为负：{self.row_count!r}")


@dataclass(frozen=True, slots=True)
class ErrorClass:
    """失败分类（闭世界三档——对齐 `specs/tools.md` 错误三档「可重试｜修参｜拒答」）。"""

    category: str  # ERROR_CATEGORIES 三值
    reason: str  # 拒因写明文（行为 3；机读信号必在场）

    def __post_init__(self) -> None:
        if self.category not in ERROR_CATEGORIES:
            values = "／".join(sorted(ERROR_CATEGORIES))
            raise ValueError(f"ErrorClass.category 越界（闭世界＝{values}）：{self.category!r}")
        if not self.reason.strip():
            raise ValueError(
                "ErrorClass.reason 不得为空（行为 3「失败分类写明文」＋机读信号必在场）："
                "拒因缺失＝静默失败"
            )


@dataclass(frozen=True, slots=True)
class Observation:
    """执行块交付的观察（全局 `[n]` 序；小结果带 `content`、大结果只带 `ref`）。"""

    seq: int  # 全局 [n] 序（引标与答案引用同一套序号）
    content: str | None  # 小结果／行集直接带内容（行集全量、丢行＝0）
    ref: MaterialRef | None  # 非行集大结果只带引用（窗口不留全文）
    source: str  # 出处（台账行／片段→报告→库／表名）

    def __post_init__(self) -> None:
        if self.seq < 1:
            raise ValueError(f"Observation.seq 须为全局 [n] 序（≥1，引标同源）：{self.seq!r}")
        if not self.source.strip():
            raise ValueError(
                "Observation.source 必填（行为 9：观察必带出处，缺出处＝判失败——INV-1 的输入）"
            )


@dataclass(frozen=True, slots=True)
class SubtaskExec:
    """逐子问题执行结果：`exec_status`（过程）与 `answered`（业务）**分开记**。"""

    subtask_id: str
    exec_status: str  # EXEC_STATUS_KINDS 三值（闭世界，越界判失败）
    answered: bool  # 是否真拿到答案（结构判定＝是否拿到非空观察）
    error: ErrorClass | None  # 失败分类（可重试／修参／终局拒答）
    row_count: int | None  # 回来多少行（记账）
    ref: MaterialRef | None  # 大结果原文的稳定引用

    def __post_init__(self) -> None:
        if self.exec_status not in EXEC_STATUS_KINDS:
            values = "／".join(sorted(EXEC_STATUS_KINDS))
            raise ValueError(
                f"SubtaskExec.exec_status 越界（闭世界＝{values}）：{self.exec_status!r}"
            )


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    """批量执行的出口（观察回流 ＋ 逐子问题账）。"""

    observations: list[Observation] = field(default_factory=list)
    subtasks: list[SubtaskExec] = field(default_factory=list)
