"""tools.subject_terms —— 题面主体/术语候选的程序预识别（V2-82a——流水 88）。

理解环节的**推荐面**：程序先按确定性规则从题面抽出**主体候选**（油田／平台名归一形＋
井号归一形）与**术语候选**（台账指标／术语名），经环境块「程序预识别」行注入供读题
模型参考——**判断仍在模型**（推荐行逐字自带「仅供参考」；本模块只产推荐，不做 ask
判定、不触检索——ask 归 V2-82b、席位归 V2-82c/d）。

**2026-10-17 V2-82b 追加**（对象歧义程序判定 ask 的两件程序侧素材——本模块仍零模型零
I/O）：`oilfield_instances`（井名录同源读面 field_name 列值集 → ask 选项名单）与
`metric_requires_subject`（名字 → 台账指标 grain 是否含「单井／区块／油田／平台」）。
**判定门本体归 runtimev2**（`clarification.subject_ask`——澄清包零工具直调红线，故本模块
两件纯函数由编排绑定注入）；ask 两侧的闭世界字面（哨兵 `__all_fields__`／选项「都要（分源
对比）」）真源归 `runtimev2.state.constants`（票面「常量单点，tools 或 state 常量均可」），
本模块不持第二份。

复用（零重写——现成件都在本包内）：
- `anchors.entity_anchor_tokens`／`entity_closed_world`——实体词闭世界匹配（油田／平台
  别名形 → 规范名；零模型零 I/O）；
- `well_ids.normalize_well_id`——RULE-PETRO-005 井号归一（**唯一形判定单点**：返空串
  ＝非井号，不猜、不做近似）；
- v1 术语匹配器算法 essence（`app/domains/chat/service.py:1391-1429` 两路：指标路取
  槽位名／台账名、术语路取术语名，归一后子串包含判定、逐名全扫不早停）——V2 禁
  import `app/**`，故按 essence 就地重写。

与 `anchors.term_anchor_tokens` 的关系＝**同款 essence 两处各持一份就地内核**（两模块
注释互相指路，不复用 import——避环；语义改动须两处同步，同步纪律见 `anchors` 同注）。

零模型、零 I/O、零语义判定（纯形态处理：闭世界成员判定与子串包含判定）。
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any, Final

from appv2.tools.anchors import entity_anchor_tokens, entity_closed_world
from appv2.tools.precondition import ledger_facts, resolve_metric_slot
from appv2.tools.well_ids import normalize_well_id

# ── 对象歧义 ask 的**素材**面（V2-82b——两侧字面真源归 `runtimev2.state.constants`）──
# 选项体量纪律（票面「≤3 个，保序」）：选项组＝实例（≤3）＋「都要」恒 ≤4——恰在
# `transport` ask options 闭世界（2~4）内。
OILFIELD_INSTANCES_CAP: Final[int] = 3
# 「粒度要求主体」标记：指标 grain 含任一子串 ⇒ 该指标的统计域必须点名主体（票面逐字：
# 单井／区块／油田／平台——如检泵周期「单井」、产量完成率「月/区块·油田」）。
GRAIN_SUBJECT_MARKERS: Final[tuple[str, ...]] = ("单井", "区块", "油田", "平台")

# 井号候选 token 的**切分**词面（字母/数字起首、连字符或下划线〔含全角变体〕串接的
# 字符块）——切分只定候选边界，**形判定与归一全归 `well_ids.normalize_well_id` 单点**
# （RULE-PETRO-005：`W11`／`w-11`／`W_11` 等变体形归一到同一规范形，非井号形返空串）。
_WELL_TOKEN_SCAN_RE = re.compile(r"[A-Za-z0-9]+(?:[-_－—–][A-Za-z0-9]+)*")


def _alias_table(dump: Mapping[str, Any]) -> Mapping[str, str] | None:
    """台账投影的别名表（`aliases` 键＝别名→规范名）——缺位/形不合＝`None`。

    `None`＝回退 `anchors` 的 glossary 别名单点缺省面（`knowledge.snapshot.glossary_aliases`
    同源）；空表亦按缺位计（零漂移：未接线 run 与空 dump 同形）。
    """
    if not isinstance(dump, Mapping):
        return None
    raw = dump.get("aliases")
    if not isinstance(raw, Mapping) or not raw:
        return None
    return {str(alias): str(canonical) for alias, canonical in raw.items()}


def subject_candidates(question: str, dump: Mapping[str, Any]) -> tuple[str, ...]:
    """题面主体候选（油田／平台名归一形 ＋ 井号归一形，保序去重）。

    两源合并（只从题面提取——**题面没有的主体绝不推测**）：
    - 井号：题面 token 逐块过 `well_ids.normalize_well_id`（返空串＝非井号，不猜；变体形
      `W11`／`w-11`／`W_11` 一并归到规范形）；
    - 油田／平台名：`entity_anchor_tokens` 的闭世界实体面（别名形问句 → 规范名），数字核
      （报告号片段形）不作主体故剔除。

    `dump`＝台账投影（`state.ledger_dump` 同形）——其 `aliases` 作实体闭世界别名源，
    缺位回退 glossary 单点（见 `_alias_table`）。
    """
    text = str(question or "")
    if not text.strip():
        return ()
    alias_table = _alias_table(dump)
    subjects: list[str] = []
    for token in _WELL_TOKEN_SCAN_RE.findall(text):
        well_id = normalize_well_id(token)
        if well_id and well_id not in subjects:
            subjects.append(well_id)
    entity_names = set(entity_closed_world(alias_table))
    for token in entity_anchor_tokens(text, alias_table):
        if token in entity_names and token not in subjects:
            subjects.append(token)
    return tuple(subjects)


def _normalize_term_text(text: str) -> str:
    """术语匹配归一面（NFKC 全半角折叠＋casefold＋去空白——双侧同规）。

    与 `anchors._normalize_term_text` **同款 essence，两处各持一份就地内核**（本模块反向
    引其实体锚件——不复用 import，避环；语义改动须两处同步）。
    """
    return "".join(unicodedata.normalize("NFKC", str(text)).casefold().split())


def _ledger_term_names(dump: Mapping[str, Any]) -> tuple[str, ...]:
    """台账术语面（指标 slot ＋ 术语名——保序去重，零发明）。"""
    names: list[str] = []
    for block, key in (("metrics", "slot"), ("terms", "term")):
        for row in dump.get(block) or []:
            if not isinstance(row, Mapping):
                continue
            name = str(row.get(key) or "").strip()
            if name and name not in names:
                names.append(name)
    return tuple(names)


def _aliases_of(name: str, alias_table: Mapping[str, str]) -> tuple[str, ...]:
    """该词条的别名词面（别名表里规范名与之**归一等值**者——双侧同规归一比对）。"""
    normalized = _normalize_term_text(name)
    if not normalized:
        return ()
    return tuple(
        str(alias)
        for alias, canonical in alias_table.items()
        if _normalize_term_text(canonical) == normalized
    )


def term_candidates(question: str, dump: Mapping[str, Any]) -> tuple[str, ...]:
    """题面术语候选（台账指标名／术语名，保序去重）。

    v1 essence 重写（`app/domains/chat/service.py:1391-1429`）：`needle`＝归一后题面，
    对 `dump["metrics"]`（slot）与 `dump["terms"]`（term）**各名＋其全部别名**逐名子串
    包含判定（全扫不早停），命中收**规范名**（指标取槽位名、术语取术语名）。

    名录源**必须直读 dump**：`roster.metric_roster` 的闭世界不含术语正名。
    空 dump／无命中＝空集（additive：未命中 run 零漂移）。
    """
    text = str(question or "")
    if not text.strip() or not isinstance(dump, Mapping):
        return ()
    needle = _normalize_term_text(text)
    if not needle:
        return ()
    alias_table = _alias_table(dump) or {}
    names: list[str] = []
    for name in _ledger_term_names(dump):
        for form in (name, *_aliases_of(name, alias_table)):
            normalized = _normalize_term_text(form)
            if normalized and normalized in needle:
                names.append(name)
                break
    return tuple(names)


# ── 对象歧义 ask 的两件程序侧素材（V2-82b）───────────────────────────────────

# 实例名归一面＝NFKC 全半角折叠＋空白折叠（**展示形归一、零改写业务名**：中文／数字不动，
# 只折全角与多余空白；井名录读面可能带首尾空白）。
_WS_RE = re.compile(r"\s+")


def _normalize_instance(name: Any) -> str:
    """实例名归一（NFKC＋空白折叠＋首尾去空——空＝非实例名，调用方丢弃）。"""
    text = unicodedata.normalize("NFKC", str(name if name is not None else ""))
    return _WS_RE.sub(" ", text).strip()


def oilfield_instances(field_rows: Iterable[Any]) -> tuple[str, ...]:
    """油田实例名单（井名录同源读面的 **field_name 列值集** → ask 选项名单）。

    `field_rows`＝`agg.dim_well.field_name` 列的行值集（生产读缝＝`query.production_field_instances`
    ——与 dim_well 卡【井号名录】段同一张表；票面示例名 `oilfield_instances(well_rows)` 的
    well_rows 即该列的行投影）。处理全为形态面：归一（NFKC＋空白折叠）→ 去空 → **按归一形
    去重（首条为准、保序）** → 封顶 `OILFIELD_INSTANCES_CAP`（选项体量纪律，见该常量注）。

    空集／非名行＝不产出（零发明：库里有几行就照实几个，不补默认油田、不猜归一形）。
    """
    names: list[str] = []
    for row in field_rows or ():
        name = _normalize_instance(row)
        if name and name not in names:
            names.append(name)
    return tuple(names[:OILFIELD_INSTANCES_CAP])


def metric_requires_subject(name: str, dump: Mapping[str, Any]) -> bool:
    """该名（题面术语／指标候选名）对应的台账指标是否**粒度要求主体**（V2-82b）。

    解析链**复用台账键解析单点**（`precondition.ledger_facts`／`resolve_metric_slot`——
    slot／指标名／别名三形＋名归一扫描，与指标闸同一判据面），解析到指标后读该行的 `grain`
    字段（`tools.ledger` dump schema＝`sem_metric.grain` 的投影）；grain 含
    `GRAIN_SUBJECT_MARKERS` 任一子串 ⇒ `True`。

    解析不到指标（纯术语／未命中／空投影／dump 形不合）⇒ `False`——**纯形态判定、零发明**：
    名字不在台账指标面就不外扩（术语题不因本条弹 ask）。
    """
    if not isinstance(dump, Mapping):
        return False
    slot = resolve_metric_slot(ledger_facts(dump), str(name or ""))
    if slot is None:
        return False
    for row in dump.get("metrics") or []:
        if not isinstance(row, Mapping) or str(row.get("slot") or "") != slot:
            continue
        grain = str(row.get("grain") or "")
        return any(marker in grain for marker in GRAIN_SUBJECT_MARKERS)
    return False
