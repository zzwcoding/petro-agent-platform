"""verification 的形状层：`specs/verification.md` 接口定义节三形状（:32–:51 逐字）。

真源＝`specs/verification.md` 接口定义节（签名以 `specs/modules.md` `## verification` 卡为准：
`verify(state) -> Verdict`）＋卡面 Seam（核验接缝：草稿＋观察 → verdict）。本层**纯形状＋结构
把守**：零行为分支（除闭世界／形态越界即拒的 fail-closed 把守外）、零 IO、零模型、零语义判断。

- `Verdict`：对外判定（**不是 answer 侧文本**）——九键齐备（五计数 `supported`／`rewritten`／
  `split`／`cited`／`attribution` ＋ `ok`／`gaps` ＋ 行集对账 `delivered_rows`／`obs_rows`），
  **缺键＝判失败**（行为 6）；
- `RewriteRecord`：被改写的原句 ＋ 原因（**闭世界两值** `no_material`｜`conflict`）——改写**不得
  静默**（行为 3／4；红线 `arch/P7a-交接包与挂账清单.md` A-P7a-37「不许静默」）；
- `Gap`：**复用 `answering` 的 `Gap` 口径**（字段与闭世界逐字同源——`specs/answering.md:50–:54`）：
  字段＝`kind`／`subtask_id`／`reason`，闭世界＝`refused`｜`missing`｜`unverified`；**核验侧产出的
  缺口 `kind="unverified"`**。相位互不 import（R1），故本层按同一口径**自持一份形状**（不引
  `appv2.runtimev2.answering`），越界值判失败。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import get_args

from appv2.runtimev2.verification.constants import (
    GAP_UNVERIFIED,
    REWRITE_REASONS,
    GapKind,
    RewriteReason,
)

# ── 缺口三档闭世界（复用 `answering` 口径：`specs/answering.md:51` 逐字）────────────
GAP_REFUSED: GapKind = "refused"
GAP_MISSING: GapKind = "missing"
GAP_KINDS: frozenset[str] = frozenset(get_args(GapKind))


@dataclass(frozen=True, slots=True)
class Gap:
    """结构化缺口（复用 `answering` 口径）：`kind`（闭世界三档）／`subtask_id`／`reason`。

    核验侧只产 `kind="unverified"`（未及核验／无据／归属对不上）；`reason` 写明文（哪一类、为什么）
    ——**不静默截断**。两维度不强行映射：`RewriteRecord.reason` 回答「为什么改写这句」，`Gap` 回答
    「哪个子问题有缺口」（`specs/verification.md:56`）。
    """

    kind: GapKind
    subtask_id: str | None
    reason: str

    def __post_init__(self) -> None:
        if self.kind not in GAP_KINDS:
            values = "／".join(sorted(GAP_KINDS))
            raise ValueError(f"Gap.kind 越界（闭世界＝{values}）：{self.kind!r}")


@dataclass(frozen=True, slots=True)
class RewriteRecord:
    """改写留痕：`line`（被改写的原句）＋ `reason`（闭世界 `no_material`｜`conflict`）。

    越界值判失败（fail-closed）；`line` 空＝无可留痕的原句，同判失败（改写必留痕——不许静默）。
    """

    line: str
    reason: RewriteReason

    def __post_init__(self) -> None:
        if self.reason not in REWRITE_REASONS:
            values = "／".join(sorted(REWRITE_REASONS))
            raise ValueError(
                f"RewriteRecord.reason 越界（闭世界＝{values}）：{self.reason!r}"
            )
        if not self.line:
            raise ValueError(
                "RewriteRecord.line 空——被改写的原句必留痕（不许静默，A-P7a-37）："
                "改写不是删掉"
            )


@dataclass(frozen=True, slots=True)
class Verdict:
    """核验判定卡（对外判定，**不是 answer 侧文本**）——九键齐备，缺键＝判失败（行为 6）。

    - `supported`：有支撑的**句子数**；
    - `rewritten`：无据被改写的句子数；
    - `split`：因矛盾被分列的**组数**；
    - `cited`：被引用的观察序号（升序、去重——引标对应窗内切片，钉 pin-10）；
    - `delivered_rows`：答案交付行数（行集对账——答案面实际交付的数据行数）；
    - `obs_rows`：在窗数据行数（材料窗内数据链行集支数；与 `delivered_rows` 确定性对账）；
    - `attribution`：归属审是否通过（引的材料与被点名对象对得上）；
    - `ok`：是否仍有「无据断言」残留（`ok=False` 才需回炉）；
    - `gaps`：结构化缺口（复用 `answering` 口径；核验侧产出 `kind="unverified"`）。

    结构把守（fail-closed）：五计数与两行数为非负整数；序号列为非负整数序；`ok=True` 时
    `rewritten` 必为 0（行为 9「`ok=True` 时不得再改写」）——越界一律抛错，不静默降级。
    """

    supported: int
    rewritten: int
    split: int
    cited: list[int]
    delivered_rows: int
    obs_rows: int
    attribution: bool
    ok: bool
    gaps: list[Gap]

    def __post_init__(self) -> None:
        for name in ("supported", "rewritten", "split", "delivered_rows", "obs_rows"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(
                    f"Verdict.{name} 须为非负整数（缺键／越界＝判失败，行为 6）：{value!r}"
                )
        if any(
            not isinstance(seq, int) or isinstance(seq, bool) or seq < 1
            for seq in self.cited
        ):
            raise ValueError(
                f"Verdict.cited 须为观察序号（≥1 的整数列——引标对应窗内切片）：{self.cited!r}"
            )
        if self.ok and self.rewritten:
            raise ValueError(
                "Verdict.ok=True 时不得再改写（行为 9）："
                f"rewritten={self.rewritten!r} 与 ok=True 矛盾"
            )
        for gap in self.gaps:
            if gap.kind not in GAP_KINDS:
                values = "／".join(sorted(GAP_KINDS))
                raise ValueError(f"Verdict.gaps 含越界 kind（闭世界＝{values}）")

    def as_dict(self) -> dict[str, object]:
        """九键投影（写 `RunState.verdict` 与 step payload 的单点——键名与字段逐字同名）。"""
        return {
            "supported": self.supported,
            "rewritten": self.rewritten,
            "split": self.split,
            "cited": list(self.cited),
            "delivered_rows": self.delivered_rows,
            "obs_rows": self.obs_rows,
            "attribution": self.attribution,
            "ok": self.ok,
            "gaps": [
                {"kind": gap.kind, "subtask_id": gap.subtask_id, "reason": gap.reason}
                for gap in self.gaps
            ],
        }


__all__ = [
    "GAP_KINDS",
    "GAP_MISSING",
    "GAP_REFUSED",
    "GAP_UNVERIFIED",
    "Gap",
    "GapKind",
    "RewriteReason",
    "RewriteRecord",
    "Verdict",
]
