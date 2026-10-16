"""tools 包根公开面看守测：askback 候选窗常量（流水 58 裁定微批）。

边界规则 R6：`runtimev2` 各块只经 `appv2.tools` 接触引擎——缺参反问的时间窗候选
常量真源在 `appv2/query/domain.py`（第 78–84 行），经 tools 包根转出供相位消费。
本看守测钉两条：①两常量在包根 `__all__` 面内、可取；②与真源**同一对象**（不复制
——复制即埋「两处各改一半」的漂移形态）。additive：既有公开面零回归。
"""

from __future__ import annotations

from appv2 import tools
from appv2.query import domain as query_domain

_PAIR = ("ASKBACK_TIME_QUESTION", "ASKBACK_TIME_CHOICES")


def test_pair_listed_on_package_root() -> None:
    """包根公开面在册：两常量进 `__all__`（消费面经包根可取，不深挖子模块）。"""
    assert set(_PAIR) <= set(tools.__all__)


def test_pair_same_object_as_true_source() -> None:
    """值同且**同对象**：包根转出与真源 `query.domain` 是同一件，不是复制的副本。"""
    for name in _PAIR:
        assert getattr(tools, name) is getattr(query_domain, name), f"{name} 被复制"


def test_pair_values_intact() -> None:
    """逐字值守卫（真源 78–84 行照抄）：问句为缺参反问原文，候选无默认项三件。"""
    assert tools.ASKBACK_TIME_QUESTION == query_domain.ASKBACK_TIME_QUESTION
    assert tuple(tools.ASKBACK_TIME_CHOICES) == ("近 3 天", "近 30 天", "本月至今")
