"""gateway_adapter.eval_clock —— 评测冻结时钟（本块承接的「冻结今天」）。

规格 `specs/gateway_adapter.md` 行为 9：`frozen_date()` **恒回一个日期**——
环境变量**未设或空串 → 缺省冻结日**；**`real` → 当日真实日期**（读 `infra.clock`；
**必须显式指定**，不得默认走真实钟）；**ISO 日期 → 该日**；**非法值 → 抛错**
（fail-fast，不静默回落）。这一取向是**对现状的有意收正**（旧
`resolve_eval_frozen_date` 在 `real` 时回 `None` 交调用方另取钟，两处判据易漂移；
本块统一为「恒回一个日期」，取真实钟的细节封在本件内）。

**生产装配路径不得读本模块的环境变量**（只经显式注入缝）：本件只被评测／冒烟具
显式调用；生产桥（`bridge.py`）**不 import 本件、不读 `EVAL_FROZEN_DATE`**——
机检＝`tests/domains/test_v2_gateway_adapter.py::frozen_clock_four_branches`
（AST 扫描 env 读位点只许出现在本件）。

数值真源：冻结点＝水位日 **2026-08-31**（`docs/runtime-refactor/recon/L3-网关与支撑
小件.md` 的 `resolve_eval_frozen_date` 段 R-L3-28 ＋ `docs/runtime-refactor/eng/
04-测试网设计.md` §七，Owner 2026-10-09 拍板）——取值只在真源一处，本件不另立。
"""

from __future__ import annotations

import os
from datetime import date

from appv2.infra.clock import now

# 环境变量键名照现状锚（旧 `appv2/runtime/eval_clock.py` 同名键）——env 是评测/冒烟
# 具的显式输入，生产装配不读（本件 docstring 纪律）。
EVAL_FROZEN_DATE_ENV = "EVAL_FROZEN_DATE"
# 缺省冻结日（数值真源见模块 docstring：R-L3-28）。
EVAL_FROZEN_DATE_DEFAULT = date(2026, 8, 31)
# 显式走真实时钟的唯一取值（「真实当日」须显式——不许静默回落真实钟）。
EVAL_FROZEN_DATE_REAL = "real"


def frozen_date() -> date:
    """冻结「今天」：未设/空串→缺省冻结日；`real`→当日真实日期；ISO→该日；非法→抛错。"""
    raw = os.environ.get(EVAL_FROZEN_DATE_ENV)
    if raw is None or raw == "":
        return EVAL_FROZEN_DATE_DEFAULT
    if raw == EVAL_FROZEN_DATE_REAL:
        return now().date()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError(
            f"{EVAL_FROZEN_DATE_ENV} 非法值 {raw!r}"
            f"（ISO 日期或 {EVAL_FROZEN_DATE_REAL!r}）——fail-fast 不静默回落"
        ) from None
