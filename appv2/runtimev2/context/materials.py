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

from appv2.text_tokens import boundary_hit, num_token_hit
from appv2.tools import (
    LINEAGE_LIMIT_HIT_KEY,
    LINEAGE_LIMIT_KEY,
    LINEAGE_LIMIT_ROWS_KEY,
    LINEAGE_PAYLOAD_KEY,
    LOCATOR_PAYLOAD_KEY,
)
from appv2.tools.schema import SEND_BUDGET_CAP

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
    "family": TRUST_LEDGER,
    "fragment": TRUST_REPORT,
    "graph": TRUST_REPORT,
    "notice": "notice",
}
_TRUST_RANK: dict[str, int] = {TRUST_AGG: 0, TRUST_LEDGER: 1, TRUST_REPORT: 2}

# 检索片段帽单点（数值真源 recon/K R-K-07——数值不落规格，行为 4／12）。
# **V2-93 D2 帽单一真源**：本值不再是本块第二份裸字面，而是 `appv2/tools/schema.py` 的
# `SEND_BUDGET_CAP`（送窗预算上限——L1 供给窗与 L3 渲染窗共用的唯一数值单点）的导入别名；
# 相等性断言＝`tests/domains/test_v2_context.py::cap_single_source`。
DEFAULT_MAX_OBSERVATIONS = SEND_BUDGET_CAP

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

# ── V2-93 席位选择机读位（D1／D4／D8——本块只读标记，标记由上游单点打） ──────────────
# 声明类观察标记（D4——`tools.handlers` 声明支构造点写 `{"declaration": True}`）：命中者
# **不进检索族候选**（渲染走 note／引擎注记通道——材料段与三机检字段零改）。
_LOCATOR_DECLARATION_KEY = "declaration"
# 表格承载标记（`retrieval.engine` 依 `domain._is_table_bearing` 单点写；L3 只读——表格保底席判据）。
_LOCATOR_TABLE_BEARING_KEY = "table_bearing"
# 语料节点分型取值（缺位＝`slice`——引擎对切片不写该键，旧形零漂移；原文保底席判据）。
_NODE_KIND_KEY = "node_kind"
_NODE_KIND_SLICE = "slice"

# 选席理由字面（`window_materials.selected[].reason` 闭世界取值；逐锚/保底/补席各一值——
# 字面散名定义、不作集合字面，规格「程序不判语义」形态面）。
_SEAT_REASON_TOPIC_TABLE = "题眼表保底"
_SEAT_REASON_TOPIC_SECTION = "题眼节保底"
_SEAT_REASON_ORIGINAL = "原文保底"
_SEAT_REASON_TABLE = "表格保底"
_SEAT_REASON_ANCHOR_FILL = "锚共现补席"
_SEAT_REASON_SOURCE = "来源保底"
_SEAT_REASON_ROTATION = "来源轮转补席"

# `render_materials` 元数据 additive 键（V2-93——渲染窗选席实录：入选 `index`／来源／理由＋
# 帽／实渲检索席数／候选总数；答案步 payload 由此键原样取用——`specs/context.md` 行为 5／6）。
_WINDOW_MATERIALS_KEY = "window_materials"

# ── V2-123 材料期 vs 执行日（材料头 additive 两字段＋期错位注记） ─────────────────────
# 材料头两字段形（**缺位＝该段跳过**——缺期材料如实缺行；执行日缺省空串＝本批前逐字零漂移）。
_PERIOD_LABEL_TEMPLATE = "报表期：{period}"
_EXECUTION_DATE_LABEL_TEMPLATE = "执行日：{execution_date}"
# 期错位注记逐字（真源 `tickets/v2/V2-123-材料期与执行日标注.md` §逐字稿——材料报表期晚于
# 执行日时随该材料块尾接一行；**不静默**、不改写材料本体、不删段）。
PERIOD_MISMATCH_NOTE = "【材料期】该材料报表期晚于执行日——只能作为「该期资料」引用。"
# 报告名尾期形的形态字符集与形长（纯字符扫描——非语义判定，行为 13 形态处理豁免面）。
_PERIOD_DIGITS = "0123456789"
_PERIOD_LENGTHS = (6, 8)
# `render_materials` 元数据 additive 键（V2-123——逐支报表期实录 `{index: period}`；
# 缺期材料不入键＝如实缺行；答案步 payload 由此键原样取用——`specs/context.md` 行为 5／6）。
_MATERIAL_PERIODS_KEY = "material_periods"


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


def _locator_flag(observation: Mapping[str, Any], key: str) -> bool:
    """观察 `locator` 上的布尔机读位（缺位／非 `True` 一律假——零语义、零回落）。"""
    locator = observation.get("locator")
    if not isinstance(locator, Mapping):
        return False
    return locator.get(key) is True


def _is_declaration(observation: Mapping[str, Any]) -> bool:
    """身份声明支判定（V2-93 D4——`locator.declaration is True`；不进检索族候选）。"""
    return _locator_flag(observation, _LOCATOR_DECLARATION_KEY)


def _table_bearing(observation: Mapping[str, Any]) -> bool:
    """表格承载片段判定（V2-93 D8——只读 `locator.table_bearing` 标记，标记单点在引擎侧）。"""
    return _locator_flag(observation, _LOCATOR_TABLE_BEARING_KEY)


def _node_kind(observation: Mapping[str, Any]) -> str:
    """语料节点分型（缺位＝`slice`——引擎对切片不写该键，旧形零漂移；原文保底席判据）。"""
    locator = observation.get("locator")
    if not isinstance(locator, Mapping):
        return _NODE_KIND_SLICE
    return str(locator.get(_NODE_KIND_KEY) or _NODE_KIND_SLICE)


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


def report_period(source: str) -> str:
    """报告名尾**报表期**（`-YYYYMM`／`-YYYYMMDD`——纯字符扫描；缺期＝空串，如实缺行）。

    取值面＝材料出处名（观察 `source`）的**尾段**：可选书名号包裹（`《…》`）剥除后，形如
    `-`＋6 位（`YYYYMM`）或 8 位（`YYYYMMDD`）阿拉伯数字者取其期形（`YYYY-MM`／
    `YYYY-MM-DD`）；其余（无期、位数不符、尾接扩展名等）＝空串——**不猜、不回落当前期**。
    本函数零语义判断：只做字符集判定、字符截取与字符拼接（规格行为 13 形态处理豁免面；
    报表期解析单点，真源 `tickets/v2/V2-123-材料期与执行日标注.md` 任务 1）。
    """
    name = source.strip()
    if name.startswith("《"):
        name = name[1:]
    if name.endswith("》"):
        name = name[:-1]
    if "-" not in name:
        return ""
    tail = name.rsplit("-", 1)[1]
    if not tail or any(char not in _PERIOD_DIGITS for char in tail):
        return ""
    if len(tail) not in _PERIOD_LENGTHS:
        return ""
    if len(tail) == 6:
        return f"{tail[:4]}-{tail[4:]}"
    return f"{tail[:4]}-{tail[4:6]}-{tail[6:]}"


def _period_digits(text: str) -> str:
    """期形归一为**纯数字串**（比较键——剔除非数字字符；零日期解析、零时钟）。"""
    return "".join(char for char in text if char in _PERIOD_DIGITS)


def _period_is_future(period: str, execution_date: str) -> bool:
    """材料报表期是否**晚于**执行日（纯数字串字典序比较——零日期解析）。

    归一为数字串后字典序比较：`YYYYMM`／`YYYYMMDD` 与 `YYYY-MM-DD` 左对齐，同前缀下
    短者＝该前缀的更早期（如 `2026-10` **不**晚于 `2026-10-08`——该期含执行日）；
    任一侧无数字位（缺期／执行日非日期形）＝不可比（返回假——不猜、不造比较）。
    """
    left = _period_digits(period)
    right = _period_digits(execution_date)
    if not left or not right:
        return False
    return left > right


def _index_key(observation: Mapping[str, Any]) -> int:
    """观察自带全局序号（`[n]` 引标键；形态违约 → 抛参数错误）。

    席位选择与渲染两处共用本取法（单点），故 `index` 缺失／非整数形的收口在两处同形同文
    （规格「错误契约」：抛参数错误，不吞错）。
    """
    try:
        return int(observation["index"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(_INDEX_SHAPE_ERROR) from exc


# 边界／数字 token 全等两判据的**本体单点真源＝`appv2.text_tokens`**（V2-100 D-a——L1/L3
# 双方直引，本块零第二份实现；形态处理豁免面 `specs/context.md` 行为 13）。本块只保留
# 分层锚分 `_anchor_score`／`_anchor_hit_count`（L3 专有面，不下沉）。


def _anchor_score(
    observation: Mapping[str, Any], anchors: Sequence[tuple[str, str]]
) -> float:
    """锚分（V2-90 锚分分层——锚＝`(kind, text)`，kind∈`{"subject", "term", "number"}`；
    `section`（章节号／表名）与其余未登记 kind 按**弱锚**处理——V2-93 题眼锚含章节号面）。

    分层判据（**内容命中优先、来源名命中降权**）：
    - `subject`（强锚：井号／油田／区块／平台名）＝边界命中内容 +3；否则来源名含锚 +0.5；
    - `term`（弱锚：术语）＝内容含锚 +2；否则来源名含锚 +0.5；
    - `number`（数字锚：最弱）＝内容数字 token 全等 +1（**不**回落来源名——数字锚只认题面数字
      与内容的 token 全等）。

    同一 `(kind, text)` 锚只计一次（重复锚串不虚增分数）、空锚串不计；大小写敏感原样比。本函数
    纯字符包含／边界／全等判定，零语义判断（行为 13 形态处理豁免面）。边界／全等**本体**＝
    `appv2.text_tokens.boundary_hit`／`num_token_hit`（V2-100 D-a 单点真源——本函数只做分层加权）。
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
            if num_token_hit(content, pair[1]):
                score += 1
        elif pair[0] == "subject":
            if boundary_hit(content, pair[1]):
                score += 3
            elif pair[1] in origin:
                score += 0.5
        else:  # term（弱锚）
            if pair[1] in content:
                score += 2
            elif pair[1] in origin:
                score += 0.5
    return score


def _anchor_hit_count(
    observation: Mapping[str, Any], anchors: Sequence[tuple[str, str]]
) -> int:
    """观察命中的锚**类型数**（V2-93 题眼席同分排序键——多锚共现者优先）。

    逐 `(kind, text)` 锚判命中（判据单点＝`_anchor_score`：内容边界／全等／包含＋来源名降权），
    重复锚串只计一次、空锚串不计；零语义（行为 13 形态处理豁免面）。
    """
    counted: set[tuple[str, str]] = set()
    hits = 0
    for kind, text in anchors:
        pair = (str(kind), str(text))
        if not pair[1] or pair in counted:
            continue
        counted.add(pair)
        if _anchor_score(observation, (pair,)) > 0:
            hits += 1
    return hits


def _select_seats(
    reports: list[dict[str, Any]],
    cap: int,
    anchors: Sequence[tuple[str, str]],
) -> list[tuple[dict[str, Any], str]]:
    """检索族席位选择（行为 4——V2-93：题眼表/节＋原文＋表格保底席＋声明支出池）。

    确定性席位选择（**只换「选谁」、不换「选多少」**：总席恒 ≤ `cap`；「排序」亦不动——返回序
    ＝入参信任级稳定序的子序），并逐席给出选席理由（`window_materials` 用）：

    ⓪ **声明类观察出池**（D4）——`locator.declaration is True` 的身份声明支不进候选（渲染走
       note／引擎注记通道；材料段与三机检字段零改）；
    ① **题眼表/节保底席**（D8——题眼按锚保底）：按「强锚（`subject`）→弱锚（`term`）→数字锚
       （`number`）」的锚序，每个锚取**一条**最佳未选片段占锚席；同分排序＝「表格承载优先
       （`table_bearing`）→ 锚命中类型数降序 → 片段长度升序 → `index` 升序」——锚命中的**原文
       切片／表格承载支优先入选**（摘要不得顶替题眼）；锚席不占单源上限；
    ② **同源原文保底席**（D8）：每个来源首个未选 `node_kind=slice` **原文**各占一席（摘要不得
       顶替——该席占常规席位计数）；
    ③ **表格保底席**（D8）：每个来源若有未选 `table_bearing` 片段，保一席（不占单源上限）；
    ④ **锚共现补席**：未选且总锚分 >0 者按「总锚分降序→片段长度升序→`index` 升序」补足锚席
       （最多 `ANCHOR_SEATS` 条；仍按分数、不按 `index`；不占单源上限）；
    ⑤ **来源保底席**：每个已检索来源首个未选片段各占一席（来源序＝首次出现序）；
    ⑥ **来源轮转补席**：按来源轮转取未选片段直到 `cap`（单一来源不吃满席位）；
    ⑦ **单来源上限**：任一来源**常规**席位数恒 ≤ `MAX_REPORT_SEATS_PER_SOURCE`（题眼／锚／表格
       保底席不计数——题眼优先于来源均衡）；原文保底席计常规席位。

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

    # ⓪ 声明类观察不进检索族候选（D4——材料段与三机检字段口径零改）
    candidates = [obs for obs in reports if not _is_declaration(obs)]
    by_source: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for obs in candidates:
        by_source.setdefault(_source_of(obs), []).append(obs)
    chosen_keys: set[int] = set()
    reasons: dict[int, str] = {}
    source_count: Counter[str] = Counter()

    def _content_length(obs: Mapping[str, Any]) -> int:
        return len(str(obs.get("content") or ""))

    def _take(obs: dict[str, Any], *, reason: str, reserved: bool = False) -> bool:
        key = _index_key(obs)
        origin = _source_of(obs)
        if key in chosen_keys or len(chosen_keys) >= cap:
            return False
        if not reserved and source_count[origin] >= MAX_REPORT_SEATS_PER_SOURCE:
            return False
        chosen_keys.add(key)
        reasons[key] = reason
        if not reserved:
            # 保底／锚席不占单源上限（题眼优先于来源均衡——V2-90 行为 4⑤／V2-93 行为 4⑦）
            source_count[origin] += 1
        return True

    # ① 题眼表/节保底席（锚命中的原文切片／表格承载支优先；同分＝锚命中类型数→长度→index）
    for kind, text in unique_anchors:
        pair = (kind, text)
        hit = [
            obs for obs in candidates
            if _index_key(obs) not in chosen_keys and _anchor_score(obs, (pair,)) > 0
        ]
        hit.sort(
            key=lambda obs: (
                not _table_bearing(obs),
                -_anchor_hit_count(obs, unique_anchors),
                _content_length(obs),
                _index_key(obs),
            )
        )
        if hit:
            best = hit[0]
            _take(
                best,
                reason=(
                    _SEAT_REASON_TOPIC_TABLE
                    if _table_bearing(best)
                    else _SEAT_REASON_TOPIC_SECTION
                ),
                reserved=True,
            )
    # ② 同源原文保底席（每来源 1 席给 `node_kind=slice` 原文——摘要不得顶替；占常规席位）
    for rows in by_source.values():
        original = next(
            (
                obs for obs in rows
                if _node_kind(obs) == _NODE_KIND_SLICE
                and _index_key(obs) not in chosen_keys
            ),
            None,
        )
        if original is not None:
            _take(original, reason=_SEAT_REASON_ORIGINAL)
    # ③ 表格保底席（每来源 1 席给 `table_bearing` 片段——不占单源上限）
    for rows in by_source.values():
        table = next(
            (
                obs for obs in rows
                if _table_bearing(obs) and _index_key(obs) not in chosen_keys
            ),
            None,
        )
        if table is not None:
            _take(table, reason=_SEAT_REASON_TABLE, reserved=True)
    # ④ 锚共现补席（最多 `ANCHOR_SEATS` 条；仍按分数与长度、不按 index；不占单源上限）
    scored = [
        (_anchor_score(obs, unique_anchors), _content_length(obs), _index_key(obs), obs)
        for obs in candidates
        if _index_key(obs) not in chosen_keys
    ]
    scored = [row for row in scored if row[0] > 0]
    scored.sort(key=lambda row: (-row[0], row[1], row[2]))
    for _score, _length, _key, obs in scored[:ANCHOR_SEATS]:
        _take(obs, reason=_SEAT_REASON_ANCHOR_FILL, reserved=True)
    # ⑤ 来源保底席（每个已检索来源至少一席）
    for rows in by_source.values():
        for obs in rows:
            if _index_key(obs) not in chosen_keys:
                _take(obs, reason=_SEAT_REASON_SOURCE)
                break
    # ⑥ 来源轮转补席（来源之间轮转，直到 cap；受单来源上限）
    cursor = {origin: 0 for origin in by_source}
    while len(chosen_keys) < cap:
        progressed = False
        for origin, rows in by_source.items():
            while cursor[origin] < len(rows):
                obs = rows[cursor[origin]]
                cursor[origin] += 1
                if _take(obs, reason=_SEAT_REASON_ROTATION):
                    progressed = True
                    break
        if not progressed:
            break
    # 输出序＝入参信任级稳定序的子序（行为 3 排序面零改：席位选择只决定入选集合）
    return [
        (obs, reasons[_index_key(obs)])
        for obs in reports
        if _index_key(obs) in chosen_keys
    ]


def _select_reports(
    reports: list[dict[str, Any]],
    cap: int,
    anchors: Sequence[tuple[str, str]],
) -> list[dict[str, Any]]:
    """检索族入选观察列（`_select_seats` 的观察面投影——Manifest 来源四列与材料段同源单点）。

    本取法＝**席位集合与序的唯一消费面**（`manifest.compile_manifest` 与 `render_materials` 同调
    本函数／同参同序）；选席理由不进本面（`window_materials` 走 `_select_seats` 元数据面）。
    """
    return [obs for obs, _reason in _select_seats(reports, cap, anchors)]


def render_materials(
    observations: list[dict[str, Any]],
    *,
    max_observations: int,
    anchors: Sequence[tuple[str, str]] = (),
    execution_date: str = "",
) -> tuple[str, dict[str, Any]]:
    """观察材料→（`[n]` 引标视图文本，截断元数据）——行为 1／4／5。

    段头逐字（`"\\n观察材料：\\n"`）；块形＝`[{index}]（{label}）{content}`——`index`＝
    观察自带全局序号（非渲染位次）、`label`＝非空段以全角「｜」连接、段序 `信任级｜来源｜井`
    （来源/井两段经 `.strip()` 归一后判空、空段跳过；三段全空＝空括号）；`content` 缺失＝
    空串；空材料集正文＝逐字「（无）」；检索族截断时材料段尾接披露行逐字（未截断零残留）。
    帽值＝注入参数 `max_observations`（数值单点＝`DEFAULT_MAX_OBSERVATIONS`）。
    形态违约（材料条目缺 `index` 或非整数形）→ 抛参数错误（V1 裸 `KeyError` 收口——
    规格「错误契约」差异声明）。

    **检索族＝确定性席位选择**（V2-90 锚分边界化与逐锚席位／V2-93 题眼表·节＋原文/表格保底席
    ——行为 4）：检索族（`report`）不再按信任级排序后原序取前 N 支，改由 `_select_seats` 做席位
    选择（声明支出池／题眼表·节保底／同源原文保底／表格保底／锚共现补席／来源保底席／来源轮转／
    单来源上限 `MAX_REPORT_SEATS_PER_SOURCE`，保底与锚席不占单源上限）——**总帽不变**（席位恒
    ≤ `max_observations`）、权威/台账族全量不变、披露行与三机检字段口径不变；**输出序不因席位
    选择改形**（行为 3：权威/台账族原序在前，检索族按信任级稳定序的子序）。
    `anchors`＝**additive 可选参**（题面锚点对 `(kind, text)`，kind∈`{"subject", "term",
    "number", "section"}`——未知 kind 按弱锚处理；锚分分层＋边界／数字 token 全等判定即锚席位
    判据；缺省空元组＝缺省行为与本批前一致）。

    **元数据面**：三机检字段（`material_truncated`／`material_rendered`／`material_total`）
    口径与逐字值零改；**V2-93 additive 键 `window_materials`**＝本轮渲染窗选席实录
    （`selected` 逐支 `index`／`source`／`reason`＋`cap`／`rendered`／`total`——答案步 payload
    原样取用；`rendered`＝实渲**检索族**席数，与 `material_rendered`（含权威/台账族）不同物）。

    **血缘卡＝口径行**（2026-10-17 EB2 D1——材料面瘦身）：`locator.kind == "lineage"` 的
    条目不渲染五要素全文，原位渲染一行 `_lineage_caliber_line` 合成文本（原料＝
    `locator.payload` 结构化载荷，**不解析五要素文本串**）；载荷缺位＝空串（不回落全文）。
    血缘卡全文仍以 `observation` 帧全量下发（前端核验面不受损）。

    **材料期 vs 执行日**（V2-123——材料头 additive 两字段＋期错位注记；L0 裁定 D-g）：
    `execution_date`＝**调用方注入的时间量**（orchestration 下传；本块**不读时钟**——入参
    纪律「时间量经注入参」）；`label` 尾追加 `报表期：{期}`（＝`report_period(source)`，
    **缺期＝该段跳过、如实缺行**）与 `执行日：{execution_date}`（缺省空串＝该段跳过——
    无执行日锚时报表期段仍按名尾取、期错位比对不成立故零注记）。材料报表期**晚于**执行日（纯数字串字典序，零日期解析）时，
    该材料块尾接一行 `PERIOD_MISMATCH_NOTE`（逐字——不静默、不改写材料本体）。
    元数据 additive 键 `material_periods`＝逐支报表期实录 `{index: 期}`（缺期不入键）。
    """
    material, authority, reports = _carrier_split(observations)
    truncated = len(reports) > max_observations
    seats = _select_seats(reports, max_observations, anchors)
    ordered = authority + [obs for obs, _reason in seats]
    exec_text = str(execution_date or "").strip()
    blocks: list[str] = []
    periods: dict[str, str] = {}
    for obs in ordered:
        index = _index_key(obs)
        trust = trust_of(obs)
        origin = str(obs.get("source") or "").strip()
        well = str(obs.get("well") or "").strip()
        period = report_period(origin)
        if period:
            periods[str(index)] = period
        label = "｜".join(
            part
            for part in (
                trust,
                origin,
                well,
                _PERIOD_LABEL_TEMPLATE.format(period=period) if period else "",
                _EXECUTION_DATE_LABEL_TEMPLATE.format(execution_date=exec_text)
                if exec_text
                else "",
            )
            if part
        )
        content = (
            _lineage_caliber_line(obs)
            if _kind_of(obs) == _KIND_LINEAGE
            else obs.get("content", "")
        )
        block = f"[{index}]（{label}）{content}"
        if _period_is_future(period, exec_text):
            block += "\n" + PERIOD_MISMATCH_NOTE
        blocks.append(block)
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
        _MATERIAL_PERIODS_KEY: periods,
        _WINDOW_MATERIALS_KEY: {
            "selected": [
                {
                    "index": _index_key(obs),
                    "source": _source_of(obs),
                    "reason": reason,
                }
                for obs, reason in seats
            ],
            "cap": max_observations,
            "rendered": len(seats),
            "total": len(material),
        },
    }
