"""runtime.wiring —— 编排层接线缝（票面「接线项四条」的装配面落点）。

gate_freshness＝DE-16 freshness_gate_enabled 开关的编排层接线（挂账自 V2-03——
config 已在复制层，接线归编排层）：开关决定是否向问数引擎供给水位读面——
false＝不供给（引擎不读水位、不拦停不改绑，N7.4a 关）；true＝照常供给（现状）。
开关语义只翻水位供给，行级权限（N7.4b）/外表审批（N7.4c）零触碰。

泛型签名：本模块不 import 引擎（runtime 只经 tools 接触世界——边界红线），
水位读面类型由装配点（组合根/测试）自带。
"""

from __future__ import annotations

from collections.abc import Callable


def gate_freshness[T](loader: Callable[[], T] | None, *, enabled: bool) -> Callable[[], T] | None:
    """水位供给翻板（DE-16）：enabled=True 原样透传；False＝不供给水位（None）。"""
    return loader if enabled else None
