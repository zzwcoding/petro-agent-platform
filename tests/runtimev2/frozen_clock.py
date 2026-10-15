"""tests.runtimev2.frozen_clock —— 评测冻结钟处理（harness 件：EVAL_FROZEN_DATE 缝）。

真源锚定：docs/runtime-refactor/eng/04-测试网设计.md §七（评测钟冻结在
2026-08-31）＋旧钉 tests/domains/test_v2_eval_clock.py——缝形照抄（含 fail-fast：
非法值 ValueError 不静默回落）。旧实现居 appv2/runtime/eval_clock.py（R5 禁
runtimev2 引旧码），本件是测试侧等价面；runtimev2 的评测时钟 adapter 随阶段 3
gateway_adapter 规格落锤后由其承接，本件退役。

env 纪律同旧钉：env 只被评测/冒烟具显式解析后经构造缝（today= callable）传入，
生产装配路径永不读 env。
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import date

EVAL_FROZEN_DATE_ENV = "EVAL_FROZEN_DATE"
# 冻结点＝水位日 2026-08-31（Owner 2026-10-09 拍板；数值真源见模块 docstring，不在本件自造）。
EVAL_FROZEN_DATE_DEFAULT = date(2026, 8, 31)
EVAL_FROZEN_DATE_REAL = "real"


def resolve_eval_frozen_date() -> date | None:
    """EVAL_FROZEN_DATE 解析单点：未设/空串→冻结日；"real"→None；ISO→该日；非法→ValueError。"""
    raw = os.environ.get(EVAL_FROZEN_DATE_ENV)
    if raw is None or raw == "":
        return EVAL_FROZEN_DATE_DEFAULT
    if raw == EVAL_FROZEN_DATE_REAL:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError(
            f"{EVAL_FROZEN_DATE_ENV} 非法值 {raw!r}"
            f"（ISO 日期或 {EVAL_FROZEN_DATE_REAL!r}）——fail-fast 不静默回落"
        ) from None


def eval_frozen_today() -> Callable[[], date] | None:
    """组合根 today 缝注入形：冻结日→恒值 callable；real→None（传构造缝→真实时钟）。"""
    frozen = resolve_eval_frozen_date()
    if frozen is None:
        return None
    return lambda: frozen
