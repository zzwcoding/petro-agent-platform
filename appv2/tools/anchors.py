r"""tools.anchors —— 问句实体锚解析与检索需求锚注入（V2-50 族 C——P-049 开发拍）。

族 C 病灶（Q14 归因：跨报告/跨油田/近值双源在窗、消费面无归属校验）两层修向的
第①层确定性落点：retrieval_need.anchors 从「可选、模型常不填」改为**确定性注
入**——问句实体词（井号/油田名/报告名）由代码解析注入 anchors，模型可增补不
可清空。

实体词闭世界匹配（本体对象账为源，零模型零 I/O）：
- 井号：对象「井」井号词面形（[A-Z]{1,3}-\d{1,4}——precondition 单井点名闸
  同款词面，题册井号形）；
- 油田名/平台名：glossary 别名表投影（appv2.knowledge.snapshot.glossary_aliases
  ——台账无承载列、生产读面与快照同源单点）中的实体侧规范名＋别名，问句命中
  （跨形对齐：空白/连字符/书名号剥除后子串）→注入规范名；
- 报告号数字核（34-8 形）：问句数字-数字 token，被某闭世界实体名包含才注入
  （「34-8」⊂「渤中34-8油田」✓；「2025-11」⊄ ✗——日期噪声不注入）。

红线：检索排序/召回零改动——本模块只产 RetrievalNeed.anchors 输入面（检索引
擎的保送/席位通道既有语义消费锚，本模块不触引擎）。
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from appv2.knowledge import glossary_aliases

# 井号词面（对象「井」井号形——precondition._WELL_RE 同款：题册井号族
# N-01/Z-16/W-111 形；纯字母前缀＋连字号＋数字，纯数字/纯字母词不作井号）。
WELL_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z]{1,3}-\d{1,4}(?![0-9])")

# 报告号数字核词面（34-8/2025-11 形——数字-数字；是否注入由闭世界包含门裁定）。
_NUMERIC_CORE_RE = re.compile(r"(?<![A-Za-z0-9])\d{1,4}-\d{1,4}(?![0-9])")

# 闭世界实体名词面类（对象账实体侧的专名承载词——油田名/平台名；术语/指标别名
# （剔检产量/躺井/时率/日产液量）与类型名（永久式封隔器）不作实体锚源）。
_ENTITY_NOUNS: tuple[str, ...] = ("油田", "平台")


def normalize_anchor_text(text: str) -> str:
    """跨形对齐规范形（匹配面）：非字母数字汉字字符全剥＋casefold。

    「渤中 34-5 油田」/「渤中34-5油田」→「渤中345油田」；「W-11」→「w11」；
    「《A-W11井完井工程报告》」→「aw11井完井工程报告」。两侧同规——出处名/
    内容与锚的包含判定共用本单点。
    """
    return "".join(ch for ch in str(text) if ch.isalnum()).casefold()


def entity_closed_world(
    aliases: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """实体锚闭世界（规范名全集——glossary 别名表投影的实体侧过滤）。

    aliases 缺省取 glossary_aliases()（生产读面与快照同源单点）；过滤＝规范名
    或别名含实体专名词（油田/平台）。去重保序（规范名在前——注入序确定性）。
    """
    table = dict(glossary_aliases() if aliases is None else aliases)
    names: list[str] = []
    for canonical, alias in table.items():
        for candidate in (str(canonical), str(alias)):
            if any(noun in candidate for noun in _ENTITY_NOUNS) and candidate not in names:
                names.append(candidate)
    return tuple(names)


def entity_anchor_tokens(
    question: str, aliases: Mapping[str, str] | None = None
) -> tuple[str, ...]:
    """问句实体词锚集（井号/油田名/报告号——闭世界匹配，确定性零模型）。

    - 井号在前（问井题最高置信题眼）；
    - 闭世界实体名命中（别名形问句归一注入规范名）随行；
    - 报告号数字核收尾（闭世界包含门——日期噪声不注入）；
    - 去重保序；无实体题＝空集（注入与归属审双双静默——不误伤半边）。
    """
    text = str(question or "")
    if not text.strip():
        return ()
    table = dict(glossary_aliases() if aliases is None else aliases)
    world = entity_closed_world(table)
    anchors: list[str] = []
    for match in WELL_TOKEN_RE.finditer(text):
        token = match.group(0)
        if token not in anchors:
            anchors.append(token)
    normalized_question = normalize_anchor_text(text)
    for alias, canonical_name in table.items():
        for form in (str(alias), str(canonical_name)):
            if not any(noun in form for noun in _ENTITY_NOUNS):
                continue
            if normalize_anchor_text(form) in normalized_question:
                if str(canonical_name) not in anchors:
                    anchors.append(str(canonical_name))
                break
    for match in _NUMERIC_CORE_RE.finditer(text):
        token = match.group(0)
        if token in anchors:
            continue
        normalized_token = normalize_anchor_text(token)
        if any(normalized_token in normalize_anchor_text(name) for name in world):
            anchors.append(token)
    return tuple(anchors)


def inject_retrieval_anchors(
    need: Mapping[str, Any], aliases: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """retrieval_need 锚确定性注入（模型可增补不可清空——V2-50 ①主语义）。

    注入锚（need.question 实体词解析）在前，模型已填锚去重续后——注入项不可
    被模型清空/覆盖（票面钉：模型不填也填／模型填错不覆盖注入项）。返回副本
    （入参零改——INV-2 同款纪律）；need.question 为唯一解析面（检索问句原文
    ＝子问题原文，合同逐字转抄语义）。
    """
    payload = dict(need)
    question = str(payload.get("question") or "")
    injected = list(entity_anchor_tokens(question, aliases))
    model_raw = payload.get("anchors")
    model_items: Sequence[Any] = (
        model_raw
        if isinstance(model_raw, Sequence) and not isinstance(model_raw, str)
        else []
    )
    model = [
        str(anchor).strip() for anchor in model_items if str(anchor).strip()
    ]
    merged = injected + [anchor for anchor in model if anchor not in injected]
    payload["anchors"] = merged
    return payload
