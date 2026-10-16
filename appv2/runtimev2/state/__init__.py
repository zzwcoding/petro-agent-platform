"""状态与限额：运行状态、Manifest、受理与回执载荷、限额参数与触界形状。

模块卡见 specs/modules.md 的 `## state` 一节；规格见 specs/state.md（形状真源）。
包根即公开面（`specs/modules.md` `## state` 卡「公开接口」节）：八类形状＋来源闭世界常量；
限额数值真源＝`recon/K` R-K-72…R-K-76 ＋ `walk/裁决表.md` §06-A（数值不落本包卡面）。
"""

from appv2.runtimev2.state.models import (
    DIALOGUE_ORIGIN_ROLES,
    DIALOGUE_ORIGINS,
    AskChoice,
    AskRequest,
    Budget,
    Convergence,
    LimitHit,
    Manifest,
    RunHandle,
    RunState,
)

__all__ = [
    "DIALOGUE_ORIGINS",
    "DIALOGUE_ORIGIN_ROLES",
    "AskChoice",
    "AskRequest",
    "Budget",
    "Convergence",
    "LimitHit",
    "Manifest",
    "RunHandle",
    "RunState",
]
