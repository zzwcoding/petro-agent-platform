"""answering 的形状层：`specs/answering.md` 接口定义节五形状（:37–:60 逐字）。

真源＝`specs/answering.md` 接口定义节（签名以 `specs/modules.md` `## answering` 卡为准：
`answer(state) -> AnswerDraft`）＋卡面 Seam（起草出口：增量文本 → 事件帧）。本层**纯形状＋结构
把守**：零行为分支（除闭世界／形态越界即拒的 fail-closed 把守外）、零 IO、零模型、零语义判断。

- `AnswerDraft`：本块出口——增量片段（流式逐段、顺序即呈现顺序）＋引用块（引标 → 观察序号）
  ＋结构化缺口（被拒／缺失／未及核验）；
- `AnswerSegment`：一段答案文本 ＋ 本段引用的观察序号（`[n]`；与全局观察同一套序）；
- `Citation`：`seq`＝引标编号（＝观察序号）、`locator`＝**可机读出处**（台账行／片段→报告→库／
  表名）——**不另设 `handle` 字段**（大结果引用经 `seq → observation.ref`（`MaterialRef`）可达，
  与 `specs/execution.md` 字段口径显式对齐）；
- `Gap`：**`kind` 是闭世界**（`refused`｜`missing`｜`unverified`）——越界值判失败（fail-closed）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, get_args

# ── 缺口三档闭世界（`specs/answering.md:51` 逐字；`verification` 复用同一口径）──────────
GapKind = Literal["refused", "missing", "unverified"]
GAP_REFUSED: GapKind = "refused"
GAP_MISSING: GapKind = "missing"
GAP_UNVERIFIED: GapKind = "unverified"
GAP_KINDS: frozenset[str] = frozenset(get_args(GapKind))


@dataclass(frozen=True, slots=True)
class Gap:
    """结构化缺口：`kind`（闭世界三档）／`subtask_id`（缺位＝无归属子问题）／`reason`。

    「被拒／缺失／未及核验」三档分别对应 `refused`／`missing`／`unverified`；`reason` 写明文
    （「哪个子问题、哪一类、为什么、还差什么」的明说面）——**不静默截断**。
    """

    kind: GapKind
    subtask_id: str | None
    reason: str

    def __post_init__(self) -> None:
        if self.kind not in GAP_KINDS:
            values = "／".join(sorted(GAP_KINDS))
            raise ValueError(f"Gap.kind 越界（闭世界＝{values}）：{self.kind!r}")


@dataclass(frozen=True, slots=True)
class AnswerSegment:
    """答案的一段：`text`＋本段引用的观察序号（`[n]`；与全局观察同一套序）。"""

    text: str
    citation_seqs: list[int] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Citation:
    """引用块条目：引标编号（＝观察序号）＋可机读出处（**不设 `handle` 字段**）。"""

    seq: int
    locator: str

    def __post_init__(self) -> None:
        if self.seq < 1:
            raise ValueError(f"Citation.seq 须为观察序号（≥1）：{self.seq!r}")
        if not self.locator.strip():
            raise ValueError(
                "Citation.locator 必填（可机读出处——写了找不回＝静默丢材料）：引标须可寻址"
            )


@dataclass(frozen=True, slots=True)
class AnswerDraft:
    """作答出口：增量片段（流式逐段、顺序即呈现顺序）＋引用块＋结构化缺口。"""

    segments: list[AnswerSegment] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
