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
    CARRIER_KINDS,
    CONTRADICTION_EXCLUDED_KINDS,
    DISCLOSURE_MARKS,
    DISCLOSURE_OBSERVATION_KINDS,
    GROUP_HEAD_SUFFIX,
    ISO_DATE_LENGTH,
    ISO_DATE_SEPARATOR,
    LINEAGE_OBSERVATION_KIND,
    SPLIT_BLOCK_HEAD,
    SPLIT_LINE_TEMPLATE,
    SUBJECT_SEPARATOR,
    TABLE_COLUMN_MARK,
)
from appv2.tools import entity_anchor_tokens, normalize_anchor_text

_ASCII_DIGITS = "0123456789"

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
    """数值记号列（**边界记号化**的记号面——行为 7）：纯字符扫描，零正则。

    记号＝连续数字（同记号内的第一个 `.` 且其后仍是数字时并入，如 `2462.0`）；`52` 与 `1520`
    是**不同记号**（比对取记号相等，非子串包含——病例 `52` 命中 `1520`，`specs/verification.md:119`
    风险 2）。判定前文本宜先过 `normalize_for_match`。
    """
    tokens: list[str] = []
    current: list[str] = []
    length = len(text)
    for position, char in enumerate(text):
        if char.isdigit():
            current.append(char)
            continue
        if (
            char == "."
            and current
            and position + 1 < length
            and text[position + 1].isdigit()
        ):
            current.append(char)
            continue
        if current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tuple(tokens)


def observation_tokens(obs: Observation) -> tuple[str, ...]:
    """观察 `content` 的数值记号列（归一形上取）。"""
    return number_tokens(normalize_for_match(str(obs.get("content", ""))))


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
    - 非承载：观察全部数值记号均须复述；观察零数值时按「零数值断言」判——支撑面只剩
      「引标可解析」（可解析性由调用方以 `by_index` 查表把守，行为 8：**不自动判过**）；
    - 比对取**记号相等**（行为 7 的边界记号化——非子串包含）。
    """
    tokens = observation_tokens(obs)
    if locator_kind(obs) in CARRIER_KINDS:
        if not tokens:
            return True
        assertion_tokens = number_tokens(assertion)
        return any(token in assertion_tokens for token in tokens)
    assertion_tokens = number_tokens(assertion)
    return all(token in assertion_tokens for token in tokens)


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
    """行内是否有数值记号（无引标数字行＝无据断言行——行为 8 后半；真源 `recon/A2` D-A2-21）。"""
    return bool(number_tokens(normalize_for_match(line)))


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


def observation_aligns(obs: Observation, needles: Sequence[str]) -> bool:
    """观察与题眼锚对齐：任一锚规范形出现在（出处名＋报告名＋内容）规范形中（R-A2-25）。"""
    haystack = normalize_anchor_text(
        str(obs.get("source", ""))
        + " "
        + str((obs.get("locator") or {}).get("report", ""))
        + " "
        + str(obs.get("content", ""))
    )
    return any(needle in haystack for needle in needles)


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
