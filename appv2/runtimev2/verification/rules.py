"""verification 的判定规则层（纯函数：文本／观察 → 判定与文本块；零模型、零 IO、零随机）。

真源＝`specs/verification.md` 行为约定节 :71–:81 ＋ `docs/runtime-refactor/recon/A2-核验规则与
归属审.md`（逐条 R-A2-xx 见函数注）；V2 差异（相对现状 `appv2/runtime/graph.py` L668–L1046）逐条
登记在函数注内，**逐字稿之外零自造语义**。

形态面与本层纪律：

- **零正则面**（`re` 不 import——形态处理一律字符扫描／`str.find`／切片：数值记号化、引标辖域切分、
  空壳判定、subject 切分）；
- **全角／半角先归一后切分**（行为 7：判定面文本先过 `unicodedata.normalize("NFKC", …)`，
  输出面保留原句逐字）；
- **边界记号化**（行为 7：数值比对取**独立记号**相等——`52` 不命中 `1520`，非子串包含）；
- 词表／语义判断零使用（唯一取值面＝形态值集与观察自带的 `locator.kind` 成员判定——行为 9 的
  豁免面：形态处理／集合成员判定）。
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Collection, Mapping, Sequence
from typing import Any

from appv2.runtimev2.state import SUBJECT_FOREIGN, SUBJECT_MATCH
from appv2.runtimev2.transport import (
    SUPPLEMENT_BLOCK_LINEAGE,
    block_head_kind,
)
from appv2.runtimev2.transport import (
    split_block_sections as transport_split_block_sections,
)
from appv2.runtimev2.verification.constants import (
    ATTRIBUTION_ALIGNED_HEAD,
    ATTRIBUTION_BLOCK_HEAD,
    ATTRIBUTION_CARRIER_KINDS,
    ATTRIBUTION_CROSSED_HEAD,
    ATTRIBUTION_LINE_TEMPLATE,
    ATTRIBUTION_LIST_CAP,
    ATTRIBUTION_NO_ALIGNED,
    ATTRIBUTION_UNCITED_HEAD,
    ATTRIBUTION_UNCITED_MORE,
    CALIBER_KINDS,
    CARRIER_KINDS,
    CONTRADICTION_EXCLUDED_KINDS,
    DECIMAL_POINT,
    DISCLOSURE_MARKS,
    DISCLOSURE_OBSERVATION_KINDS,
    EQUATION_MARK,
    FIELD_NAME_NOUN,
    GROUP_HEAD_SUFFIX,
    ISO_DATE_LENGTH,
    ISO_DATE_SEPARATOR,
    LINE_BREAK,
    LINEAGE_OBSERVATION_KIND,
    MEASURE_GAP,
    SECTION_MARKS,
    SPLIT_BLOCK_HEAD,
    SPLIT_LINE_TEMPLATE,
    SUBJECT_SEPARATOR,
    TABLE_COLUMN_MARK,
    TABLE_ROW_COLUMN_GAP,
    TABLE_ROW_COLUMN_MIN,
    TABLE_ROW_INDENT_CHARS,
    TABLE_ROW_INDENT_MIN,
    TABLE_ROW_LINE_MIN,
    THOUSANDS_SEPARATOR,
    VALUE_UNITS,
)
from appv2.tools import entity_anchor_tokens, normalize_anchor_text

_ASCII_DIGITS = "0123456789"
# 量值记号内的连接符（小数点「.」与千分位「,」——形态字符面）。
_MEASURE_JOINERS = frozenset({DECIMAL_POINT, THOUSANDS_SEPARATOR})

Observation = Mapping[str, Any]


# ── 形态处理（行为 7：全角归一／边界记号化）────────────────────────────────────


def normalize_for_match(text: str) -> str:
    """判定面归一形（**全角与半角标点先归一**——行为 7）：NFKC 归一，输出面不受影响。

    `［１］`→`[1]`、`１０`→`10`、全角标点→半角——「先归一后切分」的落点：引标切分与数值
    记号化都在归一后的文本上做（真源 `specs/verification.md:77`；病例＝全角「：」切分错，
    `specs/verification.md:119` 风险 2）。
    """
    return unicodedata.normalize("NFKC", str(text))


def number_tokens(text: str) -> tuple[str, ...]:
    """**计量数值**记号列（数值断言的记号面——行为 7 边界记号化的记号面）：纯字符扫描，零正则。

    记号＝**量值**：连续数字（段内首个 `.` 且其后仍是数字时并入，如 `2462.0`；千分位 `,`＋数字
    并入，如 `8,824.4`→规范形 `8824.4`）；**只有下列四形入列**（2026-10-17 F1 件一修精度；
    第四形＝2026-10-18 V2-104 案 A）：

    - **小数形**（记号内含 `.`）；
    - **千分位形**（记号内含 `,`）；
    - **带单位**（记号后紧邻 `VALUE_UNITS` 之一，其间至多隔空白）；
    - **表格行裸数字**（V2-104 案 A——**结构性判据**：所在行行首缩进 ≥`TABLE_ROW_INDENT_MIN`
      且行内列空白分隔的数字列 ≥`TABLE_ROW_COLUMN_MIN`，全文此类行 ≥`TABLE_ROW_LINE_MIN`；
      真机证据＝EB1 `D-诱1` 表体「　　…　415」的 415 裸数字不入记号面 ⇒ 承载片段任一数值重叠
      判不过 ⇒「- 2025年8月：415天[10]」整行被删）。

    故**标识符**（`W-22`／`Y-24`／`渤海 302`）与**日期**（`2026 年 11 月 1 日`／`2026-08-01`）的
    数字串**不算数值断言**（真机证据＝run-c6fd52c7 删句误伤）；表格行内的**非列**裸数字（同行
    prose 尾的日期，如「428三年同比看…2024 年 8 月」的 2024／8——数字前紧邻非列空白）同样不入
    列（防误放行）。`52` 与 `1520` 仍是**不同记号**（比对取记号相等，非子串包含——病例 `52` 命中
    `1520`，`specs/verification.md:119` 风险 2）。判定前文本宜先过 `normalize_for_match`
    （全角数字／标点先归一，故单位字面与缩进空白都在归一面取）。
    """
    return _measure_tokens(text)


def _measure_tokens(text: str, *, caliber: bool = False) -> tuple[str, ...]:
    """量值记号扫描单点（`number_tokens`／`caliber_numbers_only` 共用——禁第二份扫描）。

    `caliber=True` 时**册号／节号形不入列**（量值记号前紧邻 `SECTION_MARKS` 者——2026-10-18
    V2-105；`99 §2.12` 的 `2.12` 是节号、非口径数值），且**表格行裸数字亦不入列**（V2-104 案 A
    只扩 `number_tokens` 面——V2-105 收窄面不动）。
    """
    tokens: list[str] = []
    # 表格行结构面（V2-104 案 A）：全文缩进数字行 ≥`TABLE_ROW_LINE_MIN` 才解锁；口径面不收。
    table_rows = 0 if caliber else _table_row_lines(text)
    length = len(text)
    position = 0
    while position < length:
        if text[position] not in _ASCII_DIGITS:
            position += 1
            continue
        start = position
        position = _scan_digits(text, start)
        raw = text[start:position]
        if _is_measure(raw, text, position) or (
            table_rows >= TABLE_ROW_LINE_MIN and _in_table_row(text, start)
        ):
            if not (caliber and _follows_section_mark(text, start)):
                tokens.append(raw.replace(THOUSANDS_SEPARATOR, ""))
    return tuple(tokens)


# ── 表格行结构判据（2026-10-18 V2-104 案 A；判据全为版式结构，零词表、零正则）────────────


def _line_bounds(text: str, position: int) -> tuple[int, int]:
    """`position` 所在行界（半开区间——`find`／`rfind` 结构切行，零正则）。"""
    start = text.rfind(LINE_BREAK, 0, position) + 1
    end = text.find(LINE_BREAK, position)
    return start, len(text) if end < 0 else end


def _column_gap(text: str, position: int) -> int:
    """`position` 前紧邻的空白格数（列分隔／行首缩进——版式面；换行非空白，天然止扫）。"""
    gap = 0
    cursor = position - 1
    while cursor >= 0 and text[cursor] in TABLE_ROW_INDENT_CHARS:
        gap += 1
        cursor -= 1
    return gap


def _is_table_row_line(line: str) -> bool:
    """表格行判据（版式结构）：行首缩进 ＋ 列空白分隔的多列数字（零词表、零正则）。

    数字列＝前紧邻 ≥`TABLE_ROW_COLUMN_GAP` 空白的数字记号（列与列以空白分隔——表头行「　　年份
    （8 月）　躺井(井次)…」的数字前紧邻非空白 ⇒ 零列 ⇒ 不判表行）。
    """
    indent = 0
    while indent < len(line) and line[indent] in TABLE_ROW_INDENT_CHARS:
        indent += 1
    if indent < TABLE_ROW_INDENT_MIN:
        return False
    columns = 0
    position = indent
    while position < len(line):
        if line[position] in _ASCII_DIGITS:
            if _column_gap(line, position) >= TABLE_ROW_COLUMN_GAP:
                columns += 1
            position = _scan_digits(line, position)
            continue
        position += 1
    return columns >= TABLE_ROW_COLUMN_MIN


def _table_row_lines(text: str) -> int:
    """全文表格行条数（`\\n` 结构切行——与引擎「缩进数字行 ≥2」同形，独立实现：R6 禁引引擎）。"""
    count = 0
    start = 0
    length = len(text)
    while start <= length:
        end = text.find(LINE_BREAK, start)
        if end < 0:
            end = length
        if _is_table_row_line(text[start:end]):
            count += 1
        if end >= length:
            break
        start = end + 1
    return count


def _in_table_row(text: str, position: int) -> bool:
    """`position` 处的数字是**表格行的一列**（所在行为表行 ＋ 该数字前紧邻列空白）。"""
    start, end = _line_bounds(text, position)
    if not _is_table_row_line(text[start:end]):
        return False
    return _column_gap(text, position) >= TABLE_ROW_COLUMN_GAP


def _follows_section_mark(text: str, start: int) -> bool:
    """量值记号起点前紧邻（至多隔 `MEASURE_GAP` 空白）文档结构记号者＝册号／节号形（形态判定）。"""
    position = start - 1
    while position >= 0 and text[position] == MEASURE_GAP:
        position -= 1
    return position >= 0 and text[position] in SECTION_MARKS


def _scan_digits(text: str, start: int) -> int:
    """自 `start` 扫量值记号（数字／千分位 `,`＋数字／小数点 `.`＋数字）——返回终点。"""
    length = len(text)
    position = start
    while position < length:
        char = text[position]
        if char in _ASCII_DIGITS:
            position += 1
            continue
        if (
            char in _MEASURE_JOINERS
            and position + 1 < length
            and text[position + 1] in _ASCII_DIGITS
        ):
            position += 1
            continue
        break
    return position


def _is_measure(raw: str, text: str, end: int) -> bool:
    """量值三形判定：小数形／千分位形／记号后紧邻单位（`VALUE_UNITS`）。"""
    if DECIMAL_POINT in raw or THOUSANDS_SEPARATOR in raw:
        return True
    position = end
    while position < len(text) and text[position] == MEASURE_GAP:
        position += 1
    for unit in VALUE_UNITS:
        if text[position : position + len(unit)] == unit:
            return True
    return False


def observation_tokens(obs: Observation) -> tuple[str, ...]:
    """观察 `content` 的**计量数值**记号列（归一形上取——同 `number_tokens` 判据）。

    **2026-10-18 V2-105**：台账／口径类观察（`locator.kind ∈ CALIBER_KINDS`——**生产实点五
    kind**）的记号面只取**口径数值**（`caliber_numbers_only`）：册号／节号形（`§` 紧邻的数）不入
    列——否则引用该卡的纯定性句会因「非承载全须复述」被误删（真机证据＝EB11 `Q27`：唯一观察
    `ledger｜sem_metric#201` 正文含「99 §2.12」⇒ `('2.12',)` ⇒ 只读声明句被删）。
    """
    if locator_kind(obs) in CALIBER_KINDS:
        return caliber_numbers_only(obs)
    return number_tokens(normalize_for_match(str(obs.get("content", ""))))


def caliber_numbers_only(obs: Observation) -> tuple[str, ...]:
    """台账／口径类观察的**口径数值**记号列（2026-10-18 V2-105）。

    同 `number_tokens` 的量值三形，**但册号／节号形不入列**：量值记号前紧邻（至多隔空白）文档
    结构记号 `§` 者＝册号／节号（`99 §2.12` 的 `2.12`），不是口径数值——判据面只取 kind 值域
    （`CALIBER_KINDS`）与结构记号，**零 CJK 词表**（零词表 AST 闸面）。
    """
    return _measure_tokens(
        normalize_for_match(str(obs.get("content", ""))), caliber=True
    )


def locator_kind(obs: Observation) -> str:
    """观察的 `locator.kind`（形态值——成员判定用；缺位＝空串）。"""
    return str((obs.get("locator") or {}).get("kind", ""))


def structural_line(line: str) -> bool:
    """整行即 JSON 对象／数组＝结构性残留（行为 1 的剥除面；剥除不计改写）。

    **发射围栏／裸发射令牌的剥离单点归 `answering`（答案面归属，`specs/parsing.md:24`；
    相位互不 import——R1），进核验的草稿已过那道剥离**；本层只做「整行即 JSON」这一形态剥除
    （def 面真源＝`recon/A2` `_parses_as_json` R-A2-01：仅对象／数组判剥，JSON 标量不判）。
    """
    text = line.strip()
    if not text:
        return False
    try:
        parsed = json.loads(text)
    except ValueError:
        return False
    return isinstance(parsed, (dict, list))


# ── 引标与辖域（行为 1／8；真源 `recon/A2` R-A2-08／R-A2-09／R-A2-13）────────────


def citation_chunks(line: str) -> list[tuple[int, str]]:
    """行 →（引标 n, 该引标辖断言文本）列：辖域＝行首／上一引标终点到本引标起点。

    `[n]` 只认 ASCII 数字形（占位符 `[n]` 字面不作引标——真源 V2-69）；末尾引标之后的文本不属
    任何辖域（R-A2-09）。行内零引标 → 空列表。
    """
    chunks: list[tuple[int, str]] = []
    cursor = 0
    scope_start = 0
    while True:
        start = line.find("[", cursor)
        if start < 0:
            return chunks
        end = line.find("]", start + 1)
        if end < 0:
            return chunks
        token = line[start + 1 : end]
        cursor = end + 1
        if not token or not all(char in _ASCII_DIGITS for char in token):
            continue
        chunks.append((int(token), line[scope_start:start]))
        scope_start = end + 1


def without_markers(line: str) -> str:
    """剥除全部数字引标记号（`[n]` 字面保留——占位符非引标），零正则。"""
    out: list[str] = []
    cursor = 0
    while True:
        start = line.find("[", cursor)
        if start < 0:
            out.append(line[cursor:])
            return "".join(out)
        end = line.find("]", start + 1)
        if end < 0:
            out.append(line[cursor:])
            return "".join(out)
        token = line[start + 1 : end]
        if token and all(char in _ASCII_DIGITS for char in token):
            out.append(line[cursor:start])
            cursor = end + 1
        else:
            out.append(line[cursor : end + 1])
            cursor = end + 1


def scope_usable(text: str) -> bool:
    """辖域可用判定（真源 `recon/A2` R-A2-13）：含任一文字字符（字母／数字／下划线／汉字）即可用。

    空壳辖域＝行首引标或邻接引标切出的零宽／纯符号辖域（`re.sub(r"[^\\w]+")` 的等价形态判，
    零正则：`isalnum` ＋ 下划线）。
    """
    return any(char.isalnum() or char == "_" for char in text)


# ── 支撑判定（行为 2／3／8；真源 `recon/A2` R-A2-10／R-A2-11／R-A2-12）────────────


def observation_supported(obs: Observation, assertion: str) -> bool:
    """断言级支撑判定（方向＝观察→行）：被引观察的数值须在断言文本里**复述**。

    - 承载豁免（`agg_row`／`lineage`／`fragment`）：**任一**数值记号重叠即支撑、零重叠照改
      （零重叠不回退——R-A2-11）；观察零数值＝纯文本卡恒支撑；
    - **定性句放行（2026-10-18 V2-94）**：承载片段且观察**有**量值、而断言辖域**零计量数值记号**
      时，**引标可解析即保留**（`qualitative_release`——真机实证＝`eval/results/EB9-判分.md`
      D-诱12 step13：W-24 定性断口检查句被旧判据整行删）；
    - 非承载：观察全部数值记号均须复述；观察零数值时按「零数值断言」判——支撑面只剩
      「引标可解析」（可解析性由调用方以 `by_index` 查表把守，行为 8：**不自动判过**）；
    - 比对取**记号相等**（行为 7 的边界记号化——非子串包含）。
    """
    tokens = observation_tokens(obs)
    if locator_kind(obs) in CARRIER_KINDS:
        if not tokens:
            return True
        if qualitative_release(obs, assertion):
            return True
        assertion_tokens = number_tokens(assertion)
        return any(token in assertion_tokens for token in tokens)
    assertion_tokens = number_tokens(assertion)
    return all(token in assertion_tokens for token in tokens)


def qualitative_release(obs: Observation, assertion: str) -> bool:
    """**定性句放行**判据（2026-10-18 V2-94——承载片段面唯一放宽处）。

    成立三条件（全形态面，零语义判定）：①观察为承载片段（`locator.kind ∈ CARRIER_KINDS`）；
    ②观察**有**计量数值记号（观察零量值＝纯文本卡恒支撑，不属本放宽面）；③断言辖域**零**计量
    数值记号（有量值仍走 `observation_supported` 的记号比对——**对不上照删**，防编造红线不动）。
    引标可解析性由调用方以 `by_index` 把守（`observation_supported` 同款）。
    """
    if locator_kind(obs) not in CARRIER_KINDS:
        return False
    if not observation_tokens(obs):
        return False
    return not number_tokens(assertion)


def resolvable(citation: int, by_index: Mapping[int, Observation]) -> bool:
    """引标可解析（行为 8「仍须有可解析引标支撑」＋钉 pin-10「引标对应窗内切片」）。"""
    return citation in by_index


def aligned_indices(
    line_tokens: Sequence[str], observations: Sequence[Observation]
) -> tuple[int, ...]:
    """窗内对齐放行（真源 `recon/A2` R-A2-14／R-A2-15）：断言全部数值记号在窗内可寻。

    返回**命中的观察序号**（升序去重）——零命中／零数值断言（恒不放行）＝空元组。V2 变更
    （钉 pin-10「不得 `cited=[]` 且数字在场」）：放行线命中的窗内切片**落进 `cited`**（引标
    落账面），不再出现「数字在场而引用集为空」形。
    """
    if not line_tokens:
        return ()
    covered: list[int] = []
    for token in line_tokens:
        hits = [
            int(obs["index"])
            for obs in observations
            if token in observation_tokens(obs)
        ]
        if not hits:
            return ()
        for hit in hits:
            if hit not in covered:
                covered.append(hit)
    covered.sort()
    return tuple(covered)


def line_numbers_are_asserted(line: str) -> bool:
    """行内是否有**计量数值**（无引标数字行＝无据断言行——行为 8 后半；真源 `recon/A2` D-A2-21）。

    **2026-10-17 F1 件一修精度**：判据面＝`number_tokens` 的**量值**面（带单位／小数／千分位形）
    ——行内只有**标识符**（`W-22`／`Y-24`）或**日期**（`2026 年 11 月 1 日`）数字串者**不算**数值
    断言（真机证据＝run-c6fd52c7：井号代码行被误判无据断言整段删）；行内计量数值在场＝照删
    （钉 pin-10「不得 `cited=[]` 且数字在场」的落点不变，只把「数字」收窄到「量值」）。
    """
    return bool(number_tokens(normalize_for_match(line)))


def definition_equation_line(line: str) -> bool:
    """**定义等式／口径式句**形判定（2026-10-18 V2-124——可核对象扩面；判据**全结构式、零词表**）。

    两半同真（Kimi 评审修正 1 逐字：`citation_chunks` 为空 ∧ `normalize_for_match` 后含
    ASCII `=`）：

    - **无引标辖域**（`citation_chunks` 为空——即材料中无对应登记）；
    - **归一形含 ASCII 等号**（记号单点＝`EQUATION_MARK`；全角「＝」经 NFKC 归一与 ASCII 同形）。

    ⇒ 该行＝**无据断言**（按行为 3 的删句族处置：`RewriteRecord.reason` 走既有 `no_material`
    ——闭世界仍两值、不新增第 4 值）。判据本体零 CJK 字面、零正则、零语义蕴含（零词表 AST 闸面）；
    真机证据＝EB11 `Q45`（`run-9d726969`：组合式定义句每分句可挂真实引标 ⇒ 旧判据面零计量数值
    记号 ⇒ 以结构承载行全票放行，`supported:8`）。真源＝`tickets/v2/V2-124-核验面可核对象与推断
    去处.md`（含「Kimi 评审修正」1）。
    """
    text = normalize_for_match(str(line))
    return not citation_chunks(text) and EQUATION_MARK in text


# ── 豁免两类的形态判据（2026-10-17 EB3 D3——逐字稿＝方案 D3）────────────────────
# 判据只做**形态字面在场判定**（闭世界取值 ＋ ISO 日期形 ＋ 数值记号集比对），零语义蕴含判定；
# 豁免面只作用于「贴前缀／删句」一拍（支撑判定与留痕不受影响）。


def _is_iso_date(window: str) -> bool:
    """`YYYY-MM-DD` 十字形判定（分隔位两处「-」、其余位皆数字——零正则）。"""
    if len(window) != ISO_DATE_LENGTH:
        return False
    if window[4] != ISO_DATE_SEPARATOR or window[7] != ISO_DATE_SEPARATOR:
        return False
    return all(
        char.isdigit() for position, char in enumerate(window) if position not in (4, 7)
    )


def iso_date_tokens(text: str) -> tuple[str, ...]:
    """文本内 ISO 日期记号列（`YYYY-MM-DD` 形——形态扫描，零正则）。"""
    found: list[str] = []
    for start in range(len(text) - ISO_DATE_LENGTH + 1):
        window = text[start : start + ISO_DATE_LENGTH]
        if _is_iso_date(window):
            found.append(window)
    return tuple(found)


def disclosure_text(observations: Sequence[Observation]) -> str:
    """材料披露行文本（血缘卡载荷 ＋ 引擎注记观察正文——「与材料披露行事实一致」的比对源）。

    辖域＝`locator.kind ∈ DISCLOSURE_OBSERVATION_KINDS`（`lineage`／`notice`——引擎自己的
    事实披露面）；正文与 `locator.payload`（结构化载荷）一并入比对源（原文照取，零改写）。
    """
    parts: list[str] = []
    for obs in observations:
        if locator_kind(obs) not in DISCLOSURE_OBSERVATION_KINDS:
            continue
        parts.append(str(obs.get("content", "")))
        locator = obs.get("locator")
        payload = locator.get("payload") if isinstance(locator, Mapping) else None
        if isinstance(payload, Mapping):
            parts.append(json.dumps(payload, ensure_ascii=False, default=str))
    return "\n".join(parts)


def engine_disclosure_line(line: str, observations: Sequence[Observation]) -> bool:
    """引擎披露行（EB3 D3-a）：形（窗 ISO 区间 或 披露标记四字面）＋ 与材料披露行事实一致。

    形＝行内出现 ISO 日期记号（「窗 ISO 区间」的形态面）或出现 `DISCLOSURE_MARKS` 之一
    （`封顶`／`截断`／`LIMIT`／`未覆盖`——方案 D3 逐字四值）；一致＝本行全部数值记号皆出自
    材料披露行（`disclosure_text`）的数值记号集（零数值的披露句恒一致——无自证面）。
    零语义判定：只做字面在场与记号集包含两判。
    """
    if not (iso_date_tokens(line) or _has_disclosure_mark(line)):
        return False
    disclosed = number_tokens(normalize_for_match(disclosure_text(observations)))
    return all(token in disclosed for token in number_tokens(normalize_for_match(line)))


def _has_disclosure_mark(line: str) -> bool:
    """披露标记四字面在场判定（闭世界取值成员判定——非语义词表）。"""
    return any(mark in line for mark in DISCLOSURE_MARKS)


def group_header_line(line: str, next_line: str | None) -> bool:
    """组头行（EB3 D3-b）：行尾落格「：」；或数据表头（含表格列记号 `|`）且**后邻行带引标**。

    「后邻行带引标」＝下一行有可切出的引标辖域（`citation_chunks` 非空，形态切分）；行尾判取
    切片相等（零正则、不用词面判方法）。两种形态都不改行文本——只是「不删句」的豁免面。
    """
    text = line.rstrip()
    if text[-len(GROUP_HEAD_SUFFIX) :] == GROUP_HEAD_SUFFIX:
        return True
    if TABLE_COLUMN_MARK in line and next_line is not None:
        return bool(citation_chunks(normalize_for_match(next_line)))
    return False


# ── 块剥除（2026-10-17 EB3 D2 血缘五要素整段／2026-10-17 EB5c 扩块头模式族）────────


def lineage_observation_text(observations: Sequence[Mapping[str, Any]]) -> str:
    """血缘卡观察原文（`locator.kind == LINEAGE_OBSERVATION_KIND` 条目的 `content`，入栈序）。

    **2026-10-17 EB5c（血缘统一走增补面）**：材料面自 EB2 D1 起只渲染血缘卡的一行口径行，模型
    多数不再把五要素写进草稿——故「正文剥除」单路不足以保证增补面在场。本件给**原文照抄**面
    （零二次创作、零语义：只按分型取 `content` 以空行连接），由核验剥除拍在正文无血缘段时兜底。
    """
    return "\n\n".join(
        str(obs.get("content") or "")
        for obs in observations
        if locator_kind(obs) == LINEAGE_OBSERVATION_KIND
    )


def rowset_audit(
    engine_seqs: Sequence[int], delivered_seqs: Collection[int]
) -> tuple[tuple[int, ...], bool]:
    """行集对账判据（行为 11；**2026-10-17 EB5c 扩面**——缺行 ＋ 引标错位两面）。

    返回（缺行序号列，对齐标记）——两数同出**一次形态扫描**（同一个引擎行号序）：

    - **缺行**＝引擎行号不在交付引标集（按引擎行号升序）——`delivered_rows` 只给计数，本件
      给**逐号可复算面**（L04-22 形缺的是第 24／46 号行）；
    - **对齐**＝交付的引擎行号列**恰为引擎行号序的前 L 项**（L＝已交付支数）——按引擎序
      连续取行、无跳号、无错位（`False` 即 L04-22 形的「标签 25 引 [24]」off-by-one：模型
      自编行号，跳号并整体错位一格）。

    判据纯计数（不读正文文本、不判数值语义、零模型）；**只出对账面**——补注记归调用方（本件
    不改写、不重试、不拦截，Owner 裁决②「行数对账只作诚实记账面」）。
    """
    in_scope = set(delivered_seqs)
    delivered = [seq for seq in engine_seqs if seq in in_scope]
    missing = tuple(seq for seq in engine_seqs if seq not in in_scope)
    return missing, delivered == list(engine_seqs[: len(delivered)])


def lineage_line(line: str) -> bool:
    """血缘五要素行的形态判据：行内含 `② 来源表` 或 `⑤ 收口注记`（方案 D2 逐字特征面）。

    **2026-10-17 EB5c**：判据面改引块头模式族的血缘族（`transport.block_head_kind`）——与
    answering 起草面共用同一族／同一剥除单点；本函数只作核验侧的可读别名。
    """
    return block_head_kind(line) == SUPPLEMENT_BLOCK_LINEAGE


def split_block_sections(text: str) -> tuple[list[str], str]:
    """正文块剥除（返回（保留行，血缘族剥出段文本）——EB3 D2 逐字 ＋ 2026-10-17 EB5c 扩族）。

    段界＝空行界（连续非空行为一段）；判据与归属**引块头模式族单点**
    （`transport.split_block_sections`——两相位同族同语义）：血缘族段（行内含要素键，且非单行
    口径说明例外）整段离场入 `lineage` 增补面；剥除面块型（引用清单）段整段离场（程序块由交付面
    机械再生）；其余段落原样保留（含分源／归属族段——可能承载模型逐源作答正文）。
    **例外**＝血缘族段行数 ≤ `LINEAGE_KEEP_MAX_LINES`（2026-10-17 EB5c：取值引族单点）且携 `[n]`
    引标（单行口径说明——口径说明不是血缘卡）→ 保留在正文。剥出段之间以空行连接（原文照抄）。
    """
    kept_text, lineage_text = transport_split_block_sections(text)
    return kept_text.splitlines(), lineage_text


# ── 矛盾分列（行为 4；真源 `recon/A2` R-A2-29／R-A2-30）──────────────────────────


def _value_of(obs: Observation) -> str:
    content = str(obs.get("content", ""))
    position = content.find(SUBJECT_SEPARATOR)
    return content[position + 1 :]


def _subject_of(obs: Observation) -> str:
    content = str(obs.get("content", ""))
    position = content.find(SUBJECT_SEPARATOR)
    return content[:position] if position >= 0 else ""


def contradiction_groups(
    cited: Sequence[int], observations: Sequence[Observation]
) -> tuple[tuple[Observation, ...], ...]:
    """跨源矛盾池分组：同 subject（内容首段名）≥2 支且「：」后值不同 → 全组成员成一组。

    - 辖域＝被引观察（`cited` 之外零消费）；`agg_row`／`lineage`／`notice` 不入池（行级时序事实
      与元信息无出处面——R-A2-30）；
    - subject 切分取**全角「：」**（真源字面，R-A2-29）；含半角冒号／无冒号的观察不入分组;
    - 组内成员按观察序号升序、组序按首次出现序（确定性）；返回**组数**即 `Verdict.split`。
    """
    by_subject: dict[str, list[Observation]] = {}
    for obs in observations:
        if int(obs["index"]) not in cited:
            continue
        if locator_kind(obs) in CONTRADICTION_EXCLUDED_KINDS:
            continue
        subject = _subject_of(obs)
        if not subject:
            continue
        by_subject.setdefault(subject, []).append(obs)
    groups: list[tuple[Observation, ...]] = []
    for members in by_subject.values():
        if len(members) < 2:
            continue
        if len({_value_of(obs) for obs in members}) > 1:
            groups.append(tuple(sorted(members, key=lambda obs: int(obs["index"]))))
    return tuple(groups)


def split_block(groups: Sequence[Sequence[Observation]]) -> str:
    """分列块文本（逐支带出处、不强调和、不取其一——行为 4；真源 `recon/A2` R-A2-23）。"""
    lines = [SPLIT_BLOCK_HEAD]
    for group in groups:
        for obs in group:
            lines.append(
                SPLIT_LINE_TEMPLATE.format(
                    index=obs["index"],
                    source=obs.get("source", ""),
                    content=obs.get("content", ""),
                )
            )
    return "\n".join(lines)


# ── 归属审（行为 5；真源 `recon/A2` R-A2-25／R-A2-26／R-A2-27／R-A2-28）───────────


def question_anchors(question: str) -> tuple[str, ...]:
    """题眼锚＝问句实体词（井号／油田名／报告号数字核）——**确定性零模型、零 IO**。

    单点＝`appv2.tools.anchors.entity_anchor_tokens`（现状核验步的同一调用面，
    `appv2/runtime/graph.py:3628`；闭世界匹配口径的真源在 `appv2/tools/anchors.py`）；
    本模块**不另立第二套解析**（禁手写替代）。无实体题＝空锚（归属审静默——不误伤）。
    """
    return tuple(entity_anchor_tokens(str(question or "")))


def attribution_needles(anchors: Sequence[str]) -> tuple[str, ...]:
    """锚的规范形（匹配面；显示面用原锚——真源 `recon/A2` D-A2-29 两侧口径照旧）。"""
    needles: list[str] = []
    for anchor in anchors:
        normalized = normalize_anchor_text(str(anchor))
        if normalized and normalized not in needles:
            needles.append(normalized)
    return tuple(needles)


def observation_haystack(obs: Observation) -> str:
    """观察的归属匹配面（出处名＋报告名＋内容——归属审与油田归属对账共用一处，禁第二份）。"""
    locator = obs.get("locator")
    report = locator.get("report", "") if isinstance(locator, Mapping) else ""
    return (
        str(obs.get("source", "")) + " " + str(report) + " " + str(obs.get("content", ""))
    )


def observation_aligns(obs: Observation, needles: Sequence[str]) -> bool:
    """观察与题眼锚对齐：任一锚规范形出现在（出处名＋报告名＋内容）规范形中（R-A2-25）。"""
    haystack = normalize_anchor_text(observation_haystack(obs))
    return any(needle in haystack for needle in needles)


def field_names_in(text: str) -> tuple[str, ...]:
    """文本内的**油田名**列（名录面取词——出现序去重，规范名形）。

    取词单点＝`appv2.tools.anchors` 的闭世界实体锚解析（规范名／别名／闭世界数字核同源），再以
    `FIELD_NAME_NOUN` 作**形态过滤**只留油田族；**本模块不另立第二份名录／词表**（禁新造词表
    字面——闭世界与跨形归一都引名录面单点）。
    """
    names: list[str] = []
    for token in entity_anchor_tokens(str(text or "")):
        if FIELD_NAME_NOUN not in str(token):
            continue
        if token not in names:
            names.append(str(token))
    return tuple(names)


def observation_field_names(obs: Observation) -> tuple[str, ...]:
    """观察的**归属油田名**列（出处名／报告名／内容三处的油田名并集——与归属审同 haystack）。"""
    return field_names_in(observation_haystack(obs))


def question_field_names(anchors: Sequence[str]) -> tuple[str, ...]:
    """题眼锚里的**油田名**列（题眼点名油田——如「渤中34-8」命中的规范名「渤中34-8油田」）。"""
    return tuple(
        str(anchor) for anchor in anchors if FIELD_NAME_NOUN in str(anchor)
    )


def aligned_field_names(
    anchors: Sequence[str], observations: Sequence[Observation]
) -> frozenset[str]:
    """**题眼所辖油田名**集（规范形——油田归属对账的比对面；空集＝审静默）。

    两半并集（全为形态面，零语义）：

    - **题眼点名油田**：锚里自带油田名者（`question_field_names`）；
    - **窗内对齐材料自带油田名**：该观察的 haystack 里出现油田名**且**该观察与题眼锚对齐
      （`observation_aligns`）——即「窗内材料把题眼锚承载在这个油田上」（同类题：题眼是井号时，
      正确油田的材料片段会把井号写在正文里）。**元信息／披露类**观察（`locator.kind ∈
      DISCLOSURE_OBSERVATION_KINDS`——血缘卡／引擎注记／检索窗声明）**不入面**：它们并列列出多个
      油田名只是记账（真机帧 `EB4-D-诱14.json` 的检索窗声明即此形——不排会把 34-8 也划进 34-5 题
      的所辖面、把跨油田行放行）。

    为什么要有第二半（2026-10-17 F1 件四的**收窄面**）：只按「材料油田名是否与题眼锚字面共现」判，
    会把**同油田**但引文片段未复述井号的正常行误拒（真机帧 `EB4-D-诱6.json`：题眼井号 W-31／W-42
    与材料 `《B-渤中34-5油田…》` 同油田，而该片段正文只写 W-24）——故拒收面收窄到**跨油田竞争**
    成立时：窗内另有承载题眼的油田（或题眼直接点名油田）而该行引的是别的油田。
    """
    needles = attribution_needles(anchors)
    if not needles:
        return frozenset()
    names = {normalize_anchor_text(name) for name in question_field_names(anchors)}
    for obs in observations:
        if locator_kind(obs) in DISCLOSURE_OBSERVATION_KINDS:
            continue
        obs_names = observation_field_names(obs)
        if not obs_names:
            continue
        if observation_aligns(obs, needles):
            names.update(normalize_anchor_text(name) for name in obs_names)
    return frozenset(name for name in names if name)


def field_attribution_mismatch(
    line: str,
    citations: Sequence[int],
    by_index: Mapping[int, Observation],
    field_scope: Collection[str],
) -> tuple[int, ...]:
    """油田归属对账（2026-10-17 F1 件四）：被引材料**自带油田名**却**全不属题眼所辖油田**、
    且该油田名未在本行写明（＝无分源说明）→ 返回这些被引观察序号列（非空＝该行按既有删句族
    **拒收**）。

    - `field_scope` 空（无题眼锚，或题眼与窗内材料都点不出油田）→ 空列（**审静默**——不误伤，
      同归属审 R-A2-26）；
    - 判据全为**形态面**：油田名＝名录面闭世界取词（`observation_field_names`）、所辖面＝
      `aligned_field_names`、行内写明＝规范形子串在场；零语义判定；
    - **元信息／披露类**观察（`locator.kind ∈ DISCLOSURE_OBSERVATION_KINDS`——血缘卡／引擎注记／
      检索窗声明）**不入辖域**：它们列举多个油田名只是记账，不构成数据归属（真机帧 `EB4-C-正5.json`
      的「缺位名单」即此形）；
    - **收窄面（防误伤）**：本行被引里**只要有**一支落在题眼所辖油田（或该行写明了那个别的油田名）
      → 不拒收——拒收只对「整行材料全来自另一油田、且没写明」成立（真机帧 `EB4-D-诱14.json`：一条
      口径补充行同时引 34-5 与 34-8 两油田材料，属混引不拒）。

    真机证据＝`eval/results/frames/Q14M-NQ-M4.json`（NQ-M4：题眼井号体系为 Y 系〔渤中34-8〕，
    交付行却全引 `《B-渤中34-5油田躺井治理与检泵作业月报-202608》` 的 302／305／22.5 天）。
    """
    scope = set(field_scope)
    if not scope:
        return ()
    normalized_line = normalize_anchor_text(line)
    named: list[tuple[int, tuple[str, ...]]] = []
    for seq in citations:
        obs = by_index.get(seq)
        if obs is None:
            continue
        if locator_kind(obs) in DISCLOSURE_OBSERVATION_KINDS:
            continue
        names = observation_field_names(obs)
        if names:
            named.append((int(seq), names))
    if not named:
        return ()
    if any(
        normalize_anchor_text(name) in scope for _, names in named for name in names
    ):
        return ()  # 本行有题眼所辖油田的材料支撑 → 不拒（混引不误伤）
    mismatched = [
        seq
        for seq, names in named
        if not any(
            normalize_anchor_text(name) in normalized_line for name in names
        )
    ]
    return tuple(sorted(set(mismatched)))


def subject_attribution_mismatch(
    line: str,
    citations: Sequence[int],
    by_index: Mapping[int, Observation],
    reflection: Mapping[str, str],
) -> tuple[int, ...]:
    """主体归属对账（V2-117——**件四扩面**：判据面从「油田归属」扩到「题面主体」）。

    真源＝`tickets/v2/V2-117-主体反思与下游加权.md` 任务 2 第三处加权（逐字：「核验归属：件四闸
    扩为「主体不一致的来源不得作为该主体答案的依据」；全拒时走 V2-106 零交付兜底」）。本函数与
    `field_attribution_mismatch` **同族**（同删句族处置、同机读键族），只换比对面：

    - `reflection`＝`state.subject_reflection`（逐来源主体反思判值投影——键＝来源名，值 ∈
      `state.SUBJECT_VERDICTS`；判据单点＝`orchestration.subjects.reflect_subjects`，本处只读）；
    - 判据：本行被引来源里**有一支**判「属」→ **不拒**（混引不误伤——跨主体对照题 C-正3／
      D-诱14 形：分源列明／两油田并列材料同引）；无「属」且有「不属」→ 该「不属」序号入列
      （非空＝该行按既有删句族拒收）；
    - **辖域＝归属审承载族**（`locator.kind ∈ ATTRIBUTION_CARRIER_KINDS`——检索片段／图谱边；
      与行为 5 归属审同辖域）：主体反思的判据面是「来源的**报告名**／油田标签／井号」，只对
      **文档材料来源**成立——权威表行（`agg_row`）／台账行／血缘卡的来源是表名或账 id，其主体
      归属由上游闸（单井槽位闸等）管，本闸**不入辖域**（不误伤数据行）；元信息／披露类观察同排。
    - **审静默三面**：`reflection` 空（无题面主体／材料未到）／全「未知」（泛制度类来源）／
      无「不属」⇒ 空列（不误伤）；
    - **分源说明收窄**（同 `field_attribution_mismatch` 收窄面②）：本行写明该来源自带的主体类
      token（井号／油田名——取词单点 `entity_anchor_tokens`）⇒ 不拒（该行已如实分源）；
    - **元信息／披露类**观察（`locator.kind ∈ DISCLOSURE_OBSERVATION_KINDS`）不入辖域（同件四）。

    纯形态面、零语义、零新造词表（判据本体＝`normalize_anchor_text` ＋ `entity_anchor_tokens`
    ＋反思判值查表）。
    """
    if not reflection:
        return ()
    normalized_line = normalize_anchor_text(line)
    foreign: list[int] = []
    aligned = False
    for seq in citations:
        obs = by_index.get(seq)
        if obs is None:
            continue
        kind = locator_kind(obs)
        if kind in DISCLOSURE_OBSERVATION_KINDS or kind not in ATTRIBUTION_CARRIER_KINDS:
            continue
        verdict = reflection.get(str(obs.get("source", "")).strip())
        if verdict == SUBJECT_MATCH:
            aligned = True
        elif verdict == SUBJECT_FOREIGN:
            foreign.append(int(seq))
    if aligned or not foreign:
        return ()
    mismatched = [
        seq
        for seq in foreign
        if not _line_writes_source_subject(by_index[seq], normalized_line)
    ]
    return tuple(sorted(set(mismatched)))


def _line_writes_source_subject(obs: Observation, normalized_line: str) -> bool:
    """本行是否写明该来源**身份面**的主体类 token（井号／油田名——分源说明的形态判据）。

    判据面＝**出处身份三面**（`source` 出处名 ∪ `locator.report` 报告名 ∪ `well` 油田标签），
    **不含片段正文**——「分源说明」＝行内点明该来源是哪一主体（如「另注（材料为渤中34-5油田
    月报）」），而不是正文里顺带提到的任一井号（`EB4-D-诱14` 的口径补充行形）。取词单点＝
    `entity_anchor_tokens`（井号在前、闭世界实体名随行）；两侧同规＝`normalize_anchor_text`。
    """
    locator = obs.get("locator")
    report = str(locator.get("report", "")) if isinstance(locator, Mapping) else ""
    identity = f"{obs.get('source', '')} {report} {obs.get('well') or ''}"
    return any(
        normalize_anchor_text(token) in normalized_line
        for token in entity_anchor_tokens(identity)
        if normalize_anchor_text(token)
    )


def attribution_split(
    anchors: Sequence[str], cited: Sequence[int], observations: Sequence[Observation]
) -> tuple[list[Observation], list[Observation]]:
    """归属审二分（被引检索片段 →（对齐支, 跨源支）；两表保持观察序——确定性）。

    - 辖域＝被引且 `locator.kind ∈ ATTRIBUTION_CARRIER_KINDS`（检索片段承载；数据链行级／元信息
      不入辖域——R-A2-26）；
    - 无锚（规范化后全空）→ 两空表（**审静默**——不误伤，R-A2-26）；
    - `crossed` 非空 ⇔ `Verdict.attribution=False`（行为 5）。
    """
    needles = attribution_needles(anchors)
    if not needles:
        return [], []
    aligned: list[Observation] = []
    crossed: list[Observation] = []
    for obs in observations:
        if int(obs["index"]) not in cited:
            continue
        if locator_kind(obs) not in ATTRIBUTION_CARRIER_KINDS:
            continue
        if observation_aligns(obs, needles):
            aligned.append(obs)
        else:
            crossed.append(obs)
    return aligned, crossed


def uncited_aligned(
    anchors: Sequence[str], cited: Sequence[int], observations: Sequence[Observation]
) -> list[Observation]:
    """在窗未进答案引用的对齐支（分列块的第二面——真源 `recon/A2` R-A2-27）。"""
    needles = attribution_needles(anchors)
    if not needles:
        return []
    return [
        obs
        for obs in observations
        if int(obs["index"]) not in cited
        and locator_kind(obs) in ATTRIBUTION_CARRIER_KINDS
        and observation_aligns(obs, needles)
    ]


def attribution_block(
    anchors: Sequence[str],
    aligned: Sequence[Observation],
    pending: Sequence[Observation],
    crossed: Sequence[Observation],
) -> str:
    """跨源归属审块（分源列明或如实说无——R-A2-27／R-A2-28）。

    跨源支在场才出块（全对齐＝零追加——不误伤）；块内对齐面三分：被引对齐支全列／在窗未引对齐支
    前 4 支＋余量计数／零对齐如实说无；跨源面逐支全列（各带出处）。
    """
    if not crossed:
        return ""
    needles_text = "、".join(str(anchor) for anchor in anchors)
    lines = [ATTRIBUTION_BLOCK_HEAD.format(anchors=needles_text)]
    if aligned or pending:
        if aligned:
            lines.append(ATTRIBUTION_ALIGNED_HEAD)
            lines.extend(
                ATTRIBUTION_LINE_TEMPLATE.format(
                    index=obs["index"],
                    source=obs.get("source", ""),
                    content=obs.get("content", ""),
                )
                for obs in aligned
            )
        if pending:
            lines.append(ATTRIBUTION_UNCITED_HEAD)
            lines.extend(
                ATTRIBUTION_LINE_TEMPLATE.format(
                    index=obs["index"],
                    source=obs.get("source", ""),
                    content=obs.get("content", ""),
                )
                for obs in pending[:ATTRIBUTION_LIST_CAP]
            )
            if len(pending) > ATTRIBUTION_LIST_CAP:
                lines.append(
                    ATTRIBUTION_UNCITED_MORE.format(rest=len(pending) - ATTRIBUTION_LIST_CAP)
                )
    else:
        lines.append(ATTRIBUTION_NO_ALIGNED.format(anchors=needles_text))
    lines.append(ATTRIBUTION_CROSSED_HEAD)
    lines.extend(
        ATTRIBUTION_LINE_TEMPLATE.format(
            index=obs["index"],
            source=obs.get("source", ""),
            content=obs.get("content", ""),
        )
        for obs in crossed
    )
    return "\n".join(lines)
