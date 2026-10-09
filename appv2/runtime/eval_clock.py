"""runtime.eval_clock —— 测评时钟冻结缝（V2-39——Owner 2026-10-09 拍板落码）。

评测/冒烟面把系统「今天」冻结在水位日 **2026-08-31**：该日下四窗词锚定全部
干净通过——「近3天」[08-28, 08-31)／「近30天」[08-01, 08-31)／「本月」
[08-01, 08-31)／「去年」[2025 全年]，零新鲜度拦停零改绑——评测评的是系统能力，
不被数据面水位落后（不追数据面赶水位）的注记噪声污染。

纪律边界（票面红线）：
- **生产时钟不动**——infra.clock B14 单点实现零改动；本模块只产「构造注入
  形」的 today 缝值（Callable[[], date] | None），由评测/冒烟具显式传入组合根
  （create_app／compose_production_registry 的 today 参数）或 QueryEngine 等
  消费面构造缝。生产装配路径（today=None→infra.clock 实时）**永不读本模块、
  永不读 env**——冻结只落评测面。
- 消费面＝评测/冒烟具三处：RUNTIME_SMOKE 冒烟、rerun 跑批（jsonl frozen_date
  溯源字段）、:801x 评测组合根启动器。

env 合同（EVAL_FROZEN_DATE）：
- 未设/空串 → 冻结水位日 2026-08-31（缺省才冻结）；
- 显式 "real" → None（回真实时钟做对照——调用方把 None 传构造缝）；
- 显式 ISO 日期（YYYY-MM-DD）→ 冻结该日；
- 其他值 → ValueError fail-fast（不静默回落——装配纪律同 P-035 收口）。
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from datetime import date

# env 键与合同值（票面落字——rerun/冒烟/启动器三处同源引用，禁第二份字面量）。
EVAL_FROZEN_DATE_ENV = "EVAL_FROZEN_DATE"
EVAL_FROZEN_DATE_DEFAULT = date(2026, 8, 31)  # 水位日（water_line 三层 data_date）
EVAL_FROZEN_DATE_REAL = "real"  # 显式对照态——回真实时钟


def resolve_eval_frozen_date(
    environ: Mapping[str, str] | None = None,
) -> date | None:
    """EVAL_FROZEN_DATE 解析单点：→ 冻结日；real 态 → None（真实时钟）。

    environ 缺省取 os.environ（参数化供测试/嵌入方注入）。空串同未设（容器
    env 常见置空形，不另设第二布尔量）。非法值 ValueError 带键名与合法形
    （fail-fast，不静默回落）。
    """
    raw = (os.environ if environ is None else environ).get(EVAL_FROZEN_DATE_ENV)
    if raw is None or raw.strip() == "":
        return EVAL_FROZEN_DATE_DEFAULT
    value = raw.strip()
    if value == EVAL_FROZEN_DATE_REAL:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{EVAL_FROZEN_DATE_ENV}={value!r} 非法——合法形：未设/空（冻结缺省 "
            f"{EVAL_FROZEN_DATE_DEFAULT.isoformat()}）｜{EVAL_FROZEN_DATE_REAL}"
            f"（真实时钟对照）｜ISO 日期（YYYY-MM-DD）。原因：{exc}"
        ) from exc


def eval_frozen_today(
    environ: Mapping[str, str] | None = None,
) -> Callable[[], date] | None:
    """组合根 today 缝注入形：冻结日 → 恒值 callable；real 态 → None。

    返回值直接传 create_app／compose_production_registry 的 today 参数——
    None 沿构造缝落到各消费面缺省（infra.clock 实时，B14 不换实现）。
    """
    frozen = resolve_eval_frozen_date(environ)
    if frozen is None:
        return None
    return lambda: frozen
