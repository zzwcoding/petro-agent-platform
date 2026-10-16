"""tools.well_ids —— 井号归一（RULE-PETRO-005）与井名录比对单点（2026-10-17 流水 70）。

真源＝本体规则模型 `RULE-PETRO-005`（`ontology/petro/m3-rule-model.yaml`，
R5·§4 规则 7）：`normalizeWellId(rawWellId)`——trim→upper→全角连字符/下划线
归一→去内部空格→匹配 `^([A-Z]+)-?(\\d{1,3})$` → 前缀+「-」+数字左补零至 2 位；
**匹配失败返回 not-ok（不猜测归一）**。四类变体形态（去连字符／乱连字符／空白
污染／大小写混写）归一到同一规范形：`N2`／`n-2`／`N 02`／`N_2` → `N-02`；
`w-11`／`W011` → `W-11`。幂等（规范形再归一等值）。

**本模块是 V2 侧该规则的唯一实现**（不复制第二份算法）：V1 面
`app/domains/wells/domain.py` 的 `normalize_well_id` 是同规则的 V1 窄形（只认
N 系两位），而 V2 禁咬 V1（`tools/importlinter_v2.toml` 双向禁引）——不可复用，
故本模块按本体规则原文实现一次，井名录展示与查值共用它（`anchors.py` 的
`normalize_anchor_text` 是**问句跨形对齐**（剥标点＋折叠大小写，服务于检索锚
包含判定），不做补零规范形，非同一算法、不复制）。

零模型、零 I/O、零语义判定（纯形态处理：闭世界字符归一＋正则形判定）。
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# 井号形（RULE-PETRO-005 expression 逐字：`^([A-Z]+)\-?(\d{1,3})$`——归一前
# 已 upper，故此处只留大写面）。
_WELL_ID_RE = re.compile(r"^([A-Z]+)-?(\d{1,3})$")

# 连字符/下划线归一表（expression「全角连字符/下划线归一」——全角连字符「－」、
# 全角下划线「＿」、ASCII 下划线「_」、破折号「—」一并归到 ASCII 连字符）。
_SEPARATOR_CHARS = "－—–_＿"
_CANONICAL_SEPARATOR = "-"

# 井号形的最小位数（左补零至 2 位——expression「数字左补零至 2 位」）。
_MIN_DIGITS = 2


def normalize_well_id(raw_well_id: str) -> str:
    """井号归一（RULE-PETRO-005；不可归一＝空串——调用方据此如实 no_hit、不猜）。

    步骤逐字照规则：trim → upper → 全角连字符/下划线归一 → 去内部空格 → 形匹配
    → 前缀+「-」+数字左补零至 2 位；**匹配失败返回空串**（not-ok：不猜测归一，
    不返回近似形——「最近井」猜测是查证面红线）。
    """
    text = str(raw_well_id or "").strip().upper()
    for char in _SEPARATOR_CHARS:
        text = text.replace(char, _CANONICAL_SEPARATOR)
    text = "".join(char for char in text if not char.isspace())
    matched = _WELL_ID_RE.match(text)
    if matched is None:
        return ""
    prefix, digits = matched.group(1), matched.group(2)
    return f"{prefix}{_CANONICAL_SEPARATOR}{int(digits):0{_MIN_DIGITS}d}"


def roster_entries(roster: Iterable[tuple[str, str]]) -> tuple[tuple[str, str], ...]:
    """名录条目归一面（井号, 区块）——逐行归一、同名去重保序（首条为准）。

    不可归一的井号**原样承载**（零发明：数据面有这行就照实列出，不丢行、不猜
    归一形）；去重键＝归一形（归一未成者用原样形）——同一口井两种写法只列一口。
    """
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for well_id, block_name in roster:
        raw = str(well_id).strip()
        if not raw:
            continue
        key = normalize_well_id(raw) or raw
        if key in seen:
            continue
        seen.add(key)
        entries.append((key, str(block_name or "").strip()))
    return tuple(entries)


def roster_lookup(
    name: str, roster: Iterable[tuple[str, str]]
) -> tuple[str, str] | None:
    """名录查值（RULE-PETRO-005 归一后成员判定）——命中＝（归一井号, 区块）。

    查值名先归一（变体形 `w-11`／`W011` 命中共册井 `W-11`），与名录条目归一面
    **同一单点比对**；未命中＝`None`（如实 no_hit——**不猜最近井、不做近似匹配**：
    查证面程序做、语义面（哪一个是井号）模型做，分工不变）。
    """
    key = normalize_well_id(name) or str(name or "").strip()
    if not key:
        return None
    for well_id, block_name in roster_entries(roster):
        if well_id == key:
            return well_id, block_name
    return None
