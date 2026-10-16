"""gate 的判定形状：`Refusal`——命中结论（三字段闭世界，越界构造 fail-closed 抛错）。

【重建（V2 承载位设计）】V1 无此类型（`_n0_refuse` 直产 updates dict）——形状以
`specs/gate.md` 接口定义节「V2 定案签名」为准；事实面真源
`docs/runtime-refactor/arch/P5a1-票堆V2-66至69.md` A-P5a1-03／08（收口三件套）。

本层纯形状：零行为分支（唯一行为＝构造期越界校验）、零模型调用、零 I/O、零事件发射。
"""

from dataclasses import dataclass
from typing import Literal

from appv2.runtimev2.gate.constants import _FAMILIES


@dataclass(frozen=True, slots=True)
class Refusal:
    # 三族闭世界（收口步分型＝family＋"_refused"；恰回 V1 三字面——R-B2-25）
    family: Literal["injection", "outbound", "write"]
    # 命中槽值：注入＝模式词原形｜外发＝通道词｜写意图＝对象词（话术槽与步 term 取此值）
    hit: str
    # 拒答话术（三条模板逐字、槽已填——见 constants；恒非空）
    content: str

    def __post_init__(self) -> None:
        """越界构造＝判失败（fail-closed 抛错，不猜、不取默认——`specs/gate.md` 行为 11）。"""
        if self.family not in _FAMILIES:
            raise ValueError(
                f"Refusal.family 越界（闭世界三值 {sorted(_FAMILIES)}）：{self.family!r}"
            )
        if not self.hit:
            raise ValueError("Refusal.hit 空——命中槽值恒非空（fail-closed，不取默认）")
        if not self.content:
            raise ValueError("Refusal.content 空——拒答话术恒非空（fail-closed，不取默认）")
