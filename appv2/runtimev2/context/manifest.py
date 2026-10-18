"""材料面 Manifest 编译（行为 6／7——三机检字段＋`selected_reason`＋四列表来源行）。

真源：`specs/context.md` 接口定义节 `compile_manifest` 签名＋行为 6／7；字段形状真源＝
`specs/state.md` 接口定义节（`Manifest` 十字段，`transform` 取形状缺省、`token_count` 由
记账面回填）；`selected_reason` 逐字稿＝`tickets/v2/V2-61-材料承载分形渲染.md` 附 A
（两形＋零材料步形「步骤 {step}：理解步零材料渲染」——迁移照抄）；三来源行三元组映射
真源＝`docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md` R-B2-05。

常驻注入后缀（V1 形「；词典层常驻注入 {n} 块（ledger_dump 族——第 1 轮全量，非懒加载：
注入不依赖未命中）」）的 V2 适配＝**登记**（`specs/context.md` 风险 8 扩面），本块不写该后缀。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from appv2.runtimev2.context.materials import (
    TRUST_LEDGER,
    _carrier_split,
    _select_reports,
    trust_of,
)
from appv2.runtimev2.state import Manifest

# 三来源行三元组映射（`ledger_dump`→`ledger_full_dump`／`alias_dump`→`ledger_aliases`／
# `schema_card`→`schema_cards`——**唯一映射点**；两编码面各一面、同源 dump schema，
# 真源 recon/B2 R-B2-05：台账全量／别名／结构卡三块逐块各记一行来源）。
RESIDENT_SOURCE_ROWS: Mapping[str, str] = {
    "ledger_dump": "ledger_full_dump",
    "alias_dump": "ledger_aliases",
    "schema_card": "schema_cards",
}


def compile_manifest(
    observations: list[dict[str, Any]], *, step: str,
    max_observations: int,
    anchors: Sequence[tuple[str, str]] = (),
    ledger_dump: dict[str, Any] | None = None,
    token_count: int = 0,
) -> Manifest:
    """一次模型调用的材料面 Manifest（行为 6／7——每次调用都在场，零材料亦在）。

    - 三机检字段：`material_truncated` ⇔ 检索族截断；`material_rendered`＝权威/台账族支数＋
      实渲检索支数；`material_total`＝排除 notice 后材料总数；零材料步＝(0, 0, False)。
    - `selected_reason`：带材料＝「步骤 {step}：信任级降序稳定排序；权威 {A} 支全量；」＋
      截断形「检索片段帽 {帽} 支截断（{M}/{R}）」／未截断形「检索片段 {R} 支全量」＋
      「（合计入选 {K}/{总}）」；零材料＝「步骤 {step}：理解步零材料渲染」（迁移照抄）。
    - 来源四列表逐条对应同一来源序列（**等长**）：实投材料逐支（源类型＝`locator.kind`、
      源 id＝观察 `source_id`、版本＝观察 `version`、信任级＝`trust_of`）＋**当轮投入常驻块时**
      其三块来源行（唯一映射点＝`RESIDENT_SOURCE_ROWS`，信任级＝`ledger`）；`notice` 不计。
    - `ledger_dump`＝`None`（未投入常驻块）或空投影（`{}`——无块可渲染）⇒ 零常驻来源行
      （行为 7 断言：台账空投影 → 零台账来源行且材料字段不受影响）；非空投影 ⇒ 恰三行。
    - **本块零合同零标记**：合同／相位包重发判定与追加时点不落本块（`specs/prompts.md`
      行为 7／8＋`specs/bookkeeping.md` 行为 8）。
    """
    material, authority, reports = _carrier_split(observations)
    truncated = len(reports) > max_observations
    # 来源序列＝**本调用实投材料逐支**（V2-86 补丁）：与 `render_materials` 同一席位选择
    # （同函数、同 `anchors`、同出参序）——Manifest 的来源四列必须与模型窗里实际渲染的
    # `[n]` 逐支同源，否则来源账记的是「前缀支」而窗里是「席位支」（行为 7 要求）。
    rendered = authority + _select_reports(reports, max_observations, anchors)
    source_type: list[str] = []
    source_id: list[str] = []
    version: list[str | None] = []
    trust_level: list[str] = []
    for obs in rendered:
        source_type.append(str((obs.get("locator") or {}).get("kind", "")))
        source_id.append(str(obs.get("source_id", "")))
        version.append(obs.get("version"))
        trust_level.append(trust_of(obs))
    if ledger_dump:
        for resident_type, resident_id in RESIDENT_SOURCE_ROWS.items():
            source_type.append(resident_type)
            source_id.append(resident_id)
            version.append(None)
            trust_level.append(TRUST_LEDGER)
    if not material:
        selected_reason = f"步骤 {step}：理解步零材料渲染"
    else:
        selected_reason = (
            f"步骤 {step}：信任级降序稳定排序；权威 {len(authority)} 支全量；"
            + (
                f"检索片段帽 {max_observations} 支截断"
                f"（{min(len(reports), max_observations)}/{len(reports)}）"
                if truncated
                else f"检索片段 {len(reports)} 支全量"
            )
            + f"（合计入选 {len(rendered)}/{len(material)}）"
        )
    return Manifest(
        source_type=source_type,
        source_id=source_id,
        version=version,
        trust_level=trust_level,
        selected_reason=selected_reason,
        token_count=token_count,
        material_total=len(material),
        material_rendered=len(rendered),
        material_truncated=truncated,
    )
