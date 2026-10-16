"""安全阀：注入／外发／写意图的词面快路径（命中即不放行；不承载红线，只读硬保证在执行层）

模块卡见 `specs/modules.md` 的 `## gate` 一节；规格见 `specs/gate.md`（形状与行为真源）；
架构图见 docs/architecture-v3.html。**废弃词闸已移出本模块**（Owner 2026-10-15 裁决 #12：
判断＝`tool_matching` 的模型产出、分派＝`preconditions` 判定序第 1 位——本块不定义该件、
不读台账／术语表、不判「提及 vs 执行」）。包根即公开面（R2：消费方只经 `appv2.runtimev2.gate`
消费，深层子模块私有）——**族名单闭世界**（`specs/gate.md` 接口定义节「V2 定案签名」）：

- 判定：`screen`（纯函数：文本 → 命中结论；三族先命先断、命中即返）＋形状 `Refusal`
  （`{family, hit, content}` 三字段，越界构造 fail-closed 抛错）；
- 常量族八件：`INJECTION_PATTERNS`／`INJECTION_ANSWER_TEMPLATE`／`OUTBOUND_VERBS`／
  `OUTBOUND_CHANNELS`／`OUTBOUND_ANSWER`／`WRITE_VERBS`／`WRITE_TARGETS`／
  `WRITE_ANSWER_TEMPLATE`（逐字迁移，承载位换、文本不变——只扩不删）；
- `STEP_TITLES`：family→步标题映射闭世界（三形逐字，迁移照抄）。

**返回两态闭世界**（行为 1／错误契约）：`Refusal`（命中）｜`None`（未命中——闸静默）；无半成品、
无默认族、无「疑似」形，任意 `str` 入参（含空串）恒返回两态之一、不抛业务错。**零模型面／
零 I/O／零写／零帧／零审计**（纯字符串处理、零依赖；连模型桥与工具面都不 import）——命中路径
零台账接触，早退位次与收口落账归入口消费方（写口归 `bookkeeping`、帧面归 `transport`），
本块零 emit、不冒充覆盖。含公开成员之外新增成员＝只许「新增成员入名单＋同批对账消费方规格」进块；
消费方私建同源副本（自写词表／话术字面）＝判失败（判定单点）。
"""

from appv2.runtimev2.gate.constants import (
    INJECTION_ANSWER_TEMPLATE,
    INJECTION_PATTERNS,
    OUTBOUND_ANSWER,
    OUTBOUND_CHANNELS,
    OUTBOUND_VERBS,
    STEP_TITLES,
    WRITE_ANSWER_TEMPLATE,
    WRITE_TARGETS,
    WRITE_VERBS,
)
from appv2.runtimev2.gate.models import Refusal
from appv2.runtimev2.gate.screen import screen

__all__ = [
    "INJECTION_ANSWER_TEMPLATE",
    "INJECTION_PATTERNS",
    "OUTBOUND_ANSWER",
    "OUTBOUND_CHANNELS",
    "OUTBOUND_VERBS",
    "STEP_TITLES",
    "WRITE_ANSWER_TEMPLATE",
    "WRITE_TARGETS",
    "WRITE_VERBS",
    "Refusal",
    "screen",
]
