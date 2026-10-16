"""材料段渲染与信任级映射（行为 1–6——材料面的确定性渲染单点）。

真源：`specs/context.md` 接口定义节「V2 定案签名」（`render_materials`／`trust_of`）＋
行为 1／2／3／4／5／6；材料段逐字稿载体＝`appv2/runtime/context.py`（V2-80h 承载位形：
段头／块形／披露行——**承载位换、文本不变**，规格行为 1 原注）；十 kind 三族映射真源＝
`docs/runtime-refactor/recon/K-上下文事件指南预算.md` R-K-03／R-K-15…R-K-17；帽值真源＝
同文件 R-K-07（数值不落规格）。

本模块零语义判断：只做闭世界查表、稳定排序、计数与字符拼接（`specs/context.md` 行为 12／13）。
"""

from __future__ import annotations

from typing import Any

# 三档信任级字符串（排序映射与档名——真源 recon/K R-K-01…R-K-06）。
TRUST_AGG = "authoritative"
TRUST_LEDGER = "ledger"
TRUST_REPORT = "report"

# 十 kind 三族闭世界（`notice` 名义入表——材料段整体排除，行为 2）。
_KIND_TRUST: dict[str, str] = {
    "agg_row": TRUST_AGG,
    "lineage": TRUST_AGG,
    "metric": TRUST_LEDGER,
    "term": TRUST_LEDGER,
    "object": TRUST_LEDGER,
    "relation": TRUST_LEDGER,
    "family_annotation": TRUST_LEDGER,
    "fragment": TRUST_REPORT,
    "graph": TRUST_REPORT,
    "notice": "notice",
}
_TRUST_RANK: dict[str, int] = {TRUST_AGG: 0, TRUST_LEDGER: 1, TRUST_REPORT: 2}

# 检索片段帽单点（数值真源 recon/K R-K-07——数值不落规格，行为 4／12）。
DEFAULT_MAX_OBSERVATIONS = 24


def trust_of(observation: dict[str, Any]) -> str:
    """观察信任级（`locator.kind` 确定性映射单点——行为 2）。

    判定路径唯一：只读 `locator.kind`、`str()` 归一后查表；缺 `locator`／缺 `kind`／
    未知 kind 统一落 `report`（不抛错）。`notice` 名义入表、材料段整体排除。
    """
    kind = str((observation.get("locator") or {}).get("kind", ""))
    return _KIND_TRUST.get(kind, TRUST_REPORT)


def _carrier_split(
    observations: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """材料集→（排除 notice 后材料全量，权威/台账族，检索族）——分形帽分组单点（行为 3／4）。

    排序＝信任级稳定序（`authoritative`＜`ledger`＜`report`；同 rank 保持入栈序——
    `sorted` 稳定排序）；分组＝检索族（`report`）承帽、权威/台账族恒全量（无支数帽）。
    """
    material = [
        obs for obs in observations
        if (obs.get("locator") or {}).get("kind") != "notice"
    ]
    ordered = sorted(material, key=lambda obs: _TRUST_RANK.get(trust_of(obs), 9))
    authority = [obs for obs in ordered if trust_of(obs) != TRUST_REPORT]
    reports = [obs for obs in ordered if trust_of(obs) == TRUST_REPORT]
    return material, authority, reports


def render_materials(
    observations: list[dict[str, Any]], *, max_observations: int
) -> tuple[str, dict[str, Any]]:
    """观察材料→（`[n]` 引标视图文本，截断元数据）——行为 1／4／5。

    段头逐字（`"\\n观察材料：\\n"`）；块形＝`[{index}]（{label}）{content}`——`index`＝
    观察自带全局序号（非渲染位次）、`label`＝非空段以全角「｜」连接、段序 `信任级｜来源｜井`
    （来源/井两段经 `.strip()` 归一后判空、空段跳过；三段全空＝空括号）；`content` 缺失＝
    空串；空材料集正文＝逐字「（无）」；检索族截断时材料段尾接披露行逐字（未截断零残留）。
    帽值＝注入参数 `max_observations`（数值单点＝`DEFAULT_MAX_OBSERVATIONS`）。
    形态违约（材料条目缺 `index` 或非整数形）→ 抛参数错误（V1 裸 `KeyError` 收口——
    规格「错误契约」差异声明）。
    """
    material, authority, reports = _carrier_split(observations)
    truncated = len(reports) > max_observations
    ordered = authority + reports[:max_observations]
    blocks: list[str] = []
    for obs in ordered:
        try:
            index = int(obs["index"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "观察面形态违约：材料条目缺 `index` 或非整数形（规格「错误契约」）"
            ) from exc
        trust = trust_of(obs)
        origin = str(obs.get("source") or "").strip()
        well = str(obs.get("well") or "").strip()
        label = "｜".join(part for part in (trust, origin, well) if part)
        blocks.append(f"[{index}]（{label}）{obs.get('content', '')}")
    text = (
        "\n观察材料：\n" + ("\n".join(blocks) if blocks else "（无）")
        + (
            f"\n（材料披露：检索片段共 {len(reports)} 支，本轮渲染前 "
            f"{min(len(reports), max_observations)} 支——未渲染片段不在"
            "本轮视野，不得对其断言；权威行集与台账卡已全量渲染。）"
            if truncated
            else ""
        )
    )
    return text, {
        "material_truncated": truncated,
        "material_rendered": len(ordered),
        "material_total": len(material),
    }
