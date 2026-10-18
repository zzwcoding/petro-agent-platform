"""上下文：材料段渲染、过程档案有界摘要、台账/名录投影装载、超窗 compaction、材料面 Manifest 编译

模块卡见 `specs/modules.md` 的 `## context` 一节；规格与行为真源见 `specs/context.md`
（接口定义节「V2 定案签名」＝族名单真源，卡面 `compile` 为阶段 2 初拟形、不施工——风险 7①）。

包根即公开面（`specs/modules.md` `## context` 卡「公开接口」节＋`specs/context.md` 接口定义节
「V2 定案签名」——**族名单闭世界**）：六函数 `load_ledger_dump`／`render_materials`／
`render_process_notes`／`compile_manifest`／`compact_messages`／`trust_of`（＋**V2-123
新增** `report_period`——报表期解析单点）＋常量族
`DEFAULT_MAX_OBSERVATIONS`／`PROCESS_NOTES_BUDGET`／`TRUST_AGG`／`TRUST_LEDGER`／
`TRUST_REPORT`／`RESIDENT_SOURCE_ROWS`／`MAX_REPORT_SEATS_PER_SOURCE`／`ANCHOR_SEATS`；
另携装载端口件（`LedgerProjectionPort` 端口／
`wire_ledger_projection` 注入缝／`LedgerLoadError`——真实现形待核定，规格风险 5）与
视窗数值单点 `DEFAULT_DIALOGUE_VIEW_TOKENS`（规格风险 4「数值已裁 8k 档，常量阶段 5 落 8192」）。

本块＝**确定性渲染／装载块**：零语义判断、零模型调用（连 `gateway_adapter` 都不 import）、
零帧、零时钟接触、零静默省略（一切有界处理必以披露行或披露账目显式表达）；
**唯一状态写入面**＝`load_ledger_dump` 对 `state.ledger_dump` 的取一次装载，其余共享写面零写。
依赖白名单＝`state`＋`tools` 两块；材料渲染／过程档案／信任映射／帽常量／三来源行映射在
runtimev2 面内各恰一处定义（消费方零副本）。
"""

from appv2.runtimev2.context.compaction import (
    DEFAULT_DIALOGUE_VIEW_TOKENS,
    compact_messages,
)
from appv2.runtimev2.context.ledger import (
    LedgerLoadError,
    LedgerProjectionPort,
    load_ledger_dump,
    wire_ledger_projection,
)
from appv2.runtimev2.context.manifest import RESIDENT_SOURCE_ROWS, compile_manifest
from appv2.runtimev2.context.materials import (
    ANCHOR_SEATS,
    DEFAULT_MAX_OBSERVATIONS,
    MAX_REPORT_SEATS_PER_SOURCE,
    TRUST_AGG,
    TRUST_LEDGER,
    TRUST_REPORT,
    render_materials,
    report_period,
    trust_of,
)
from appv2.runtimev2.context.process_notes import (
    PROCESS_NOTES_BUDGET,
    render_process_notes,
)

__all__ = [
    "ANCHOR_SEATS",
    "DEFAULT_DIALOGUE_VIEW_TOKENS",
    "DEFAULT_MAX_OBSERVATIONS",
    "MAX_REPORT_SEATS_PER_SOURCE",
    "PROCESS_NOTES_BUDGET",
    "RESIDENT_SOURCE_ROWS",
    "TRUST_AGG",
    "TRUST_LEDGER",
    "TRUST_REPORT",
    "LedgerLoadError",
    "LedgerProjectionPort",
    "compact_messages",
    "compile_manifest",
    "load_ledger_dump",
    "render_materials",
    "render_process_notes",
    "report_period",
    "trust_of",
    "wire_ledger_projection",
]
