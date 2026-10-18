"""材料段渲染与信任级映射（行为 1–6——材料面的确定性渲染单点）。

真源：`specs/context.md` 接口定义节「V2 定案签名」（`render_materials`／`trust_of`）＋
行为 1／2／3／4／5／6；材料段逐字稿载体＝`appv2/runtime/context.py`（V2-80h 承载位形：
段头／块形／披露行——**承载位换、文本不变**，规格行为 1 原注）；十 kind 三族映射真源＝
`docs/runtime-refactor/recon/K-上下文事件指南预算.md` R-K-03／R-K-15…R-K-17；帽值真源＝
同文件 R-K-07（数值不落规格）。
**血缘卡口径行**（2026-10-17 EB2 D1）＝本块对上述逐字形的唯一追加面：血缘卡不进五要素
全文、原位渲染一行口径行（`docs/runtime-refactor/proposals/EB2-答案面瘦身与友好化.md` D1）。

本模块零语义判断：只做闭世界查表、稳定排序、计数与字符拼接（`specs/context.md` 行为 12／13）。
"""

from __future__ import annotations

from collections import Counter, OrderedDict
from collections.abc import Mapping, Sequence
from typing import Any

from appv2.tools import (
    LINEAGE_LIMIT_HIT_KEY,
    LINEAGE_LIMIT_KEY,
    LINEAGE_LIMIT_ROWS_KEY,
    LINEAGE_PAYLOAD_KEY,
    LOCATOR_PAYLOAD_KEY,
)

# 三档信任级字符串（排序映射与档名——真源 recon/K R-K-01…R-K-06）。
TRUST_AGG = "authoritative"
TRUST_LEDGER = "ledger"
TRUST_REPORT = "report"

# 血缘卡观察分型（`locator.kind` 取值指针——真源 `appv2/tools` 血缘观察装配面
# `{"kind": "lineage", …}`；本块只作闭世界取值字面，不引其它相位）。
_KIND_LINEAGE = "lineage"
# 口径行两个原料的取值指针（真源 `appv2/query/domain.py` `LINEAGE_KEY_CALIBER`／
# `LINEAGE_KEY_SOURCE`——血缘五要素合同键；本块 import 白名单只 `state`＋`tools`，
# 故以取值指针落此、落点唯一，装配面按同键写载荷）。
_LINEAGE_KEY_CALIBER = "① 口径"
_LINEAGE_KEY_SOURCE = "② 来源表"

# 口径行形（2026-10-17 EB2 D1——材料面瘦身：血缘卡五要素全文不进模型窗，只留一行口径）。
_LINEAGE_CALIBER_LINE_TEMPLATE = "【口径】{caliber}｜来源：{source_table}"
_LINEAGE_LIMIT_SUFFIX_TEMPLATE = "｜本次封顶前 {rows} 行"

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

# 单来源席位上界（V2-86 材料供给席次——来源份额不被单一来源吃满；数值不落规格，行为 4）。
# 与总帽 `DEFAULT_MAX_OBSERVATIONS` 并列两点：席位上限管「一个来源最多几席」、总帽管「检索族
# 一共几支」——两值互不替代（席位数恒不越总帽）。V2-90 起本上限只约束**常规席位**（来源保底／
# 轮转）——锚席不占本上限（题眼优先于来源均衡，行为 4⑤）。
MAX_REPORT_SEATS_PER_SOURCE = 6

# 锚席补席位数上界（V2-90 逐锚席位——逐锚各保一席后，高锚分补席最多取 N 条；数值不落规格，
# 行为 4）。与单来源席位上界同处定义：两者是不同判据的两个数值（锚席位保题眼、单来源席位保
# 来源均衡）；锚席不占单来源席位上界。
ANCHOR_SEATS = 6

# 观察 `index` 形态违约的收口文案（材料条目缺 `index`／非整数形——规格「错误契约」差异声明；
# 席位选择与渲染两处同源同文，避免两套错误面）。
_INDEX_SHAPE_ERROR = "观察面形态违约：材料条目缺 `index` 或非整数形（规格「错误契约」）"


def trust_of(observation: dict[str, Any]) -> str:
    """观察信任级（`locator.kind` 确定性映射单点——行为 2）。

    判定路径唯一：只读 `locator.kind`、`str()` 归一后查表；缺 `locator`／缺 `kind`／
    未知 kind 统一落 `report`（不抛错）。`notice` 名义入表、材料段整体排除。
    """
    kind = str((observation.get("locator") or {}).get("kind", ""))
    return _KIND_TRUST.get(kind, TRUST_REPORT)


def _kind_of(observation: Mapping[str, Any]) -> str:
    """观察的 `locator.kind` 取值（形态读取：缺 `locator`／缺 `kind` 取空串——零语义）。"""
    locator = observation.get("locator")
    if not isinstance(locator, Mapping):
        return ""
    return str(locator.get("kind") or "")


def _lineage_caliber_line(observation: Mapping[str, Any]) -> str:
    """血缘卡口径行（五要素全文化的替代——2026-10-17 EB2 D1）。

    原料＝`locator.payload` 结构化载荷（**不解析五要素文本串**）：取①口径原文与
    〔②〕来源表原文合成 `【口径】{①}｜来源：{②}`；载荷限量面触顶（`limit.hit`）时
    追加 `｜本次封顶前 {N} 行`（N＝本次限量内交付行数）。
    载荷缺位／形态违约＝空串——不回落五要素全文（全文仍随 `observation` 帧全量下发，
    前端核验面不受损）。
    """
    locator = observation.get("locator")
    if not isinstance(locator, Mapping):
        return ""
    payload = locator.get(LOCATOR_PAYLOAD_KEY)
    if not isinstance(payload, Mapping):
        return ""
    lineage = payload.get(LINEAGE_PAYLOAD_KEY)
    if not isinstance(lineage, Mapping):
        return ""
    caliber = str(lineage.get(_LINEAGE_KEY_CALIBER) or "").strip()
    source_table = str(lineage.get(_LINEAGE_KEY_SOURCE) or "").strip()
    if not caliber and not source_table:
        return ""
    line = _LINEAGE_CALIBER_LINE_TEMPLATE.format(caliber=caliber, source_table=source_table)
    limit = payload.get(LINEAGE_LIMIT_KEY)
    if isinstance(limit, Mapping) and limit.get(LINEAGE_LIMIT_HIT_KEY) is True:
        rows = limit.get(LINEAGE_LIMIT_ROWS_KEY)
        if isinstance(rows, int) and not isinstance(rows, bool) and rows > 0:
            line += _LINEAGE_LIMIT_SUFFIX_TEMPLATE.format(rows=rows)
    return line


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


def _source_of(observation: Mapping[str, Any]) -> str:
    """观察的来源段（席位选择的分源键——`source` 经 `.strip()` 归一；缺位＝空串）。"""
    return str(observation.get("source") or "").strip()


def _index_key(observation: Mapping[str, Any]) -> int:
    """观察自带全局序号（`[n]` 引标键；形态违约 → 抛参数错误）。

    席位选择与渲染两处共用本取法（单点），故 `index` 缺失／非整数形的收口在两处同形同文
    （规格「错误契约」：抛参数错误，不吞错）。
    """
    try:
        return int(observation["index"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(_INDEX_SHAPE_ERROR) from exc


# 数字 token 全等的边界字符集（前后紧邻任一字符即非全等——V2-90 锚分边界化；
# 纯字符扫描、禁 `re`，形态处理豁免面 `specs/context.md` 行为 13）。
_ASCII_DIGITS = "0123456789"
_ASCII_LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_NUMERIC_BOUNDARY_CHARS = _ASCII_DIGITS + ".,"
# 井号／油田等强锚的边界字符集（前后紧邻字母／数字／连字符即非边界——`W-11` 与 `W-111` 可辨）。
_SUBJECT_BOUNDARY_CHARS = _ASCII_LETTERS + _ASCII_DIGITS + "-"


def _num_token_hit(token: str, text: str) -> bool:
    """数字 token **全等**命中（V2-90——`22` 不得命中 `2200`／`202608`；`12.5` 命中 `12.5`）。

    纯字符扫描（禁 `re`）：锚串在文本中的每次出现，前后字符都不得是数字或 `.`／`,`；任一出现
    满足全等即命中。故 `12.5` 命中 `12.5 MPa`、不命中 `112.5`／`12.55`（落在更长数字串内）。
    """
    if not token or not text:
        return False
    start = 0
    while True:
        found = text.find(token, start)
        if found < 0:
            return False
        end = found + len(token)
        before_ok = found == 0 or text[found - 1] not in _NUMERIC_BOUNDARY_CHARS
        after_ok = end == len(text) or text[end] not in _NUMERIC_BOUNDARY_CHARS
        if before_ok and after_ok:
            return True
        start = found + 1


def _boundary_hit(anchor: str, text: str) -> bool:
    """强锚（井号／油田／区块／平台名）**边界**命中（V2-90——`W-11` 不得命中 `W-111`）。

    纯字符扫描（禁 `re`）：锚串在文本中的每次出现，前后字符都不得是字母／数字／连字符；任一
    出现满足边界即命中。中文等非 ASCII 字母数字字符不作边界字符（`W-11井位于` 仍命中）。
    """
    if not anchor or not text:
        return False
    start = 0
    while True:
        found = text.find(anchor, start)
        if found < 0:
            return False
        end = found + len(anchor)
        before_ok = found == 0 or text[found - 1] not in _SUBJECT_BOUNDARY_CHARS
        after_ok = end == len(text) or text[end] not in _SUBJECT_BOUNDARY_CHARS
        if before_ok and after_ok:
            return True
        start = found + 1


def _anchor_score(
    observation: Mapping[str, Any], anchors: Sequence[tuple[str, str]]
) -> float:
    """锚分（V2-90 锚分分层——锚＝`(kind, text)`，kind∈`{"subject", "term", "number"}`）。

    分层判据（**内容命中优先、来源名命中降权**）：
    - `subject`（强锚：井号／油田／区块／平台名）＝边界命中内容 +3；否则来源名含锚 +0.5；
    - `term`（弱锚：术语）＝内容含锚 +2；否则来源名含锚 +0.5；
    - `number`（数字锚：最弱）＝内容数字 token 全等 +1（**不**回落来源名——数字锚只认题面数字
      与内容的 token 全等）。

    同一 `(kind, text)` 锚只计一次（重复锚串不虚增分数）、空锚串不计；大小写敏感原样比。本函数
    纯字符包含／边界／全等判定，零语义判断（行为 13 形态处理豁免面）。
    """
    content = str(observation.get("content") or "")
    origin = _source_of(observation)
    counted: set[tuple[str, str]] = set()
    score = 0.0
    for kind, anchor in anchors:
        pair = (str(kind), str(anchor))
        if not pair[1] or pair in counted:
            continue
        counted.add(pair)
        if pair[0] == "number":
            if _num_token_hit(pair[1], content):
                score += 1
        elif pair[0] == "subject":
            if _boundary_hit(pair[1], content):
                score += 3
            elif pair[1] in origin:
                score += 0.5
        else:  # term（弱锚）
            if pair[1] in content:
                score += 2
            elif pair[1] in origin:
                score += 0.5
    return score


def _select_reports(
    reports: list[dict[str, Any]],
    cap: int,
    anchors: Sequence[tuple[str, str]],
) -> list[dict[str, Any]]:
    """检索族席位选择（行为 4——V2-90：逐锚席位＋来源保底席＋来源轮转＋单来源上限）。

    确定性席位选择（**只换「选谁」、不换「选多少」**：总席恒 ≤ `cap`；「排序」亦不动——返回序
    ＝入参信任级稳定序的子序）：

    ① **逐锚各保一席**（V2-90——题眼按锚保底、不按片）：按「强锚（`subject`）→弱锚（`term`）→
       数字锚（`number`）」的锚序，每个锚取**一条**最佳未选片段占锚席；同分排序＝该锚分降序→
       片段长度升序（更具体）→ `index` 升序；**不再按 `index` 取前 `ANCHOR_SEATS`**；
    ② **高锚分补席**（最多 `ANCHOR_SEATS` 条，边际收益）：未选且总锚分 >0 者按「总锚分降序→
       片段长度升序→`index` 升序」补足锚席（仍按分数、不按 `index`）；
    ③ **来源保底席**：每个来源首个未选片段各占一席（来源序＝首次出现序）——每个已检索来源
       至少进窗一支；
    ④ **来源轮转补席**：按来源轮转取未选片段直到 `cap`（单一来源不吃满席位）；
    ⑤ **单来源上限**：任一来源常规席位数恒 ≤ `MAX_REPORT_SEATS_PER_SOURCE`；**锚席（①②）不占
       单源上限**（题眼优先于来源均衡——锚席先落且不计数，剩余席位再受上限约束）。

    席位键＝观察自带 `index`（重复 `index` 只占一席——`[n]` 引标唯一）；`cap` 内取不满＝席位
    穷尽，正常返回（不抛错、不补空席）。本函数零 IO、零语义判断（纯计数／成员判定／字符包含）。
    """
    unique_anchors: list[tuple[str, str]] = []
    seen_anchors: set[tuple[str, str]] = set()
    for kind, text in anchors:
        pair = (str(kind), str(text))
        if not pair[1] or pair in seen_anchors:
            continue
        seen_anchors.add(pair)
        unique_anchors.append(pair)

    by_source: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for obs in reports:
        by_source.setdefault(_source_of(obs), []).append(obs)
    chosen_keys: set[int] = set()
    source_count: Counter[str] = Counter()

    def _content_length(obs: Mapping[str, Any]) -> int:
        return len(str(obs.get("content") or ""))

    def _take(obs: dict[str, Any], *, anchor: bool = False) -> bool:
        key = _index_key(obs)
        origin = _source_of(obs)
        if key in chosen_keys or len(chosen_keys) >= cap:
            return False
        if not anchor and source_count[origin] >= MAX_REPORT_SEATS_PER_SOURCE:
            return False
        chosen_keys.add(key)
        if not anchor:
            # 锚席不占单源上限（题眼优先于来源均衡——V2-90 行为 4⑤）
            source_count[origin] += 1
        return True

    # ① 逐锚各保一席（**强锚→弱锚→数字锚**的锚序即席位优先级；同分长度升序→index）
    for kind, text in unique_anchors:
        pair = [(kind, text)]
        candidates = [
            obs for obs in reports
            if _index_key(obs) not in chosen_keys and _anchor_score(obs, pair) > 0
        ]
        candidates.sort(
            key=lambda obs: (-_anchor_score(obs, pair), _content_length(obs), _index_key(obs))
        )
        if candidates:
            _take(candidates[0], anchor=True)
    # ② 高锚分补席（最多 `ANCHOR_SEATS` 条；仍按分数与长度、不按 index）
    scored = [
        (_anchor_score(obs, unique_anchors), _content_length(obs), _index_key(obs), obs)
        for obs in reports
        if _index_key(obs) not in chosen_keys
    ]
    scored = [row for row in scored if row[0] > 0]
    scored.sort(key=lambda row: (-row[0], row[1], row[2]))
    for _score, _length, _key, obs in scored[:ANCHOR_SEATS]:
        _take(obs, anchor=True)
    # ③ 来源保底席（每个已检索来源至少一席）
    for rows in by_source.values():
        for obs in rows:
            if _index_key(obs) not in chosen_keys:
                _take(obs)
                break
    # ④ 来源轮转补席（来源之间轮转，直到 cap；受单来源上限）
    cursor = {origin: 0 for origin in by_source}
    while len(chosen_keys) < cap:
        progressed = False
        for origin, rows in by_source.items():
            while cursor[origin] < len(rows):
                obs = rows[cursor[origin]]
                cursor[origin] += 1
                if _take(obs):
                    progressed = True
                    break
        if not progressed:
            break
    # 输出序＝入参信任级稳定序的子序（行为 3 排序面零改：席位选择只决定入选集合）
    return [obs for obs in reports if _index_key(obs) in chosen_keys]


def render_materials(
    observations: list[dict[str, Any]],
    *,
    max_observations: int,
    anchors: Sequence[tuple[str, str]] = (),
) -> tuple[str, dict[str, Any]]:
    """观察材料→（`[n]` 引标视图文本，截断元数据）——行为 1／4／5。

    段头逐字（`"\\n观察材料：\\n"`）；块形＝`[{index}]（{label}）{content}`——`index`＝
    观察自带全局序号（非渲染位次）、`label`＝非空段以全角「｜」连接、段序 `信任级｜来源｜井`
    （来源/井两段经 `.strip()` 归一后判空、空段跳过；三段全空＝空括号）；`content` 缺失＝
    空串；空材料集正文＝逐字「（无）」；检索族截断时材料段尾接披露行逐字（未截断零残留）。
    帽值＝注入参数 `max_observations`（数值单点＝`DEFAULT_MAX_OBSERVATIONS`）。
    形态违约（材料条目缺 `index` 或非整数形）→ 抛参数错误（V1 裸 `KeyError` 收口——
    规格「错误契约」差异声明）。

    **检索族＝确定性席位选择**（V2-90 锚分边界化与逐锚席位——行为 4）：检索族（`report`）不再按
    信任级排序后原序取前 N 支，改由 `_select_reports` 做席位选择（逐锚各保一席／高锚分补席／
    来源保底席／来源轮转／单来源上限 `MAX_REPORT_SEATS_PER_SOURCE`，锚席不占单源上限）——
    **总帽不变**（席位恒 ≤ `max_observations`）、权威/台账族全量不变、披露行与三机检字段口径
    不变；**输出序不因席位选择改形**（行为 3：权威/台账族原序在前，检索族按信任级稳定序的子序）。
    `anchors`＝**additive 可选参**（题面锚点对 `(kind, text)`，kind∈`{"subject", "term",
    "number"}`；锚分分层＋边界／数字 token 全等判定即锚席位判据；缺省空元组＝缺省行为与本批前
    一致）。

    **血缘卡＝口径行**（2026-10-17 EB2 D1——材料面瘦身）：`locator.kind == "lineage"` 的
    条目不渲染五要素全文，原位渲染一行 `_lineage_caliber_line` 合成文本（原料＝
    `locator.payload` 结构化载荷，**不解析五要素文本串**）；载荷缺位＝空串（不回落全文）。
    血缘卡全文仍以 `observation` 帧全量下发（前端核验面不受损）。
    """
    material, authority, reports = _carrier_split(observations)
    truncated = len(reports) > max_observations
    ordered = authority + _select_reports(reports, max_observations, anchors)
    blocks: list[str] = []
    for obs in ordered:
        index = _index_key(obs)
        trust = trust_of(obs)
        origin = str(obs.get("source") or "").strip()
        well = str(obs.get("well") or "").strip()
        label = "｜".join(part for part in (trust, origin, well) if part)
        content = (
            _lineage_caliber_line(obs)
            if _kind_of(obs) == _KIND_LINEAGE
            else obs.get("content", "")
        )
        blocks.append(f"[{index}]（{label}）{content}")
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
