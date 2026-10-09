"""tools.ledger —— 词典层全量投影（V2-34 票面任务 6——拍板 a「第 1 轮全量注入」的取数件）。

台账小（46 行级），注入胜检索：本模块把 KnowledgeStore 公开读面（evidence
浏览态＋aliases＋families——INV-2 只读）一次性投影成结构化 dump dict，供：

- 澄清相位上下文注入（runtime 经 LoopDeps.ledger_dump 缝取本件产物——第 1 轮
  全量编进上下文，非懒加载；semantic_query 转钻取）；
- 前置条件机 facts（precondition.ledger_facts 消费同一 dump——绑定态/口径支/
  禁用词的结构化判定面）。

投影契约（dump schema——本模块与 precondition 的机读界面）：
- metrics: [{slot, name, binding_state, calibers: [{key, name, default}],
  default_caliber, value, source_id, version}]——slot＝台账原名剥法纯名（★☆
  前缀与括注尾缀剥离——snapshot「slot_name＝剥法纯名」同规则）；calibers 从
  Evidence.value 的「口径支：」段解析（渲染契约＝knowledge 读面 _metric_
  evidence 单点，格式被 tests/domains/test_v2_knowledge.py 钉死）；
- terms: [{term, banned, freshness, value, source_id}]——banned＝届满展示串
  「—（已禁用）」（term_expiry 展示串族契约）；
- objects/relations/families: 值串投影；aliases: 别名→规范名；cards: 发现面
  白名单结构卡（handlers 同源——agg 三表＋sem 五账＋kb 片段清单）。

零 LLM、零写路径（INV-2）：只读公开方法，返回副本容器。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from appv2.knowledge import (
    KIND_FAMILY,
    KIND_METRIC,
    KIND_OBJECT,
    KIND_RELATION,
    KIND_TERM,
    Evidence,
    KnowledgeStore,
    SemanticQuery,
)
from appv2.tools.handlers import _AGG_CARDS, _KB_CARDS, _SEM_CARDS

# 发现面白名单结构卡（handlers 同源——dump 卡片段真源）。
ALL_SCHEMA_CARDS: tuple[str, ...] = (*_AGG_CARDS, *_SEM_CARDS, *_KB_CARDS)

# 「口径支：A 班次合计日口径（默认）；B 化验实测（月度/正式）」的解析式
# （渲染契约＝knowledge 读面单点：支间「；」分隔、支内「key 名称（默认）?」）。
_CALIBERS_HEAD = re.compile(r"口径支：(.+)$")
_CALIBER_ENTRY = re.compile(r"^(\S+)\s+(.+)$")
_CALIBER_DEFAULT_SUFFIX = "（默认）"
# 禁用词替代提示（term value「禁用（替代：产量完成率）」段）。
_REPLACEMENT_RE = re.compile(r"替代：([^）]+)")


def _slot_of(metric_value: str) -> str:
    """指标台账原名→剥法纯名（slot 投影——★☆ 前缀与括注尾缀剥离）。"""
    head = metric_value.split("：", 1)[0]
    return head.strip("★☆ ").split("（", 1)[0].strip()


def _calibers_of(metric_value: str) -> tuple[dict[str, Any], ...]:
    """Evidence.value「口径支：」段→结构化支列（key/name/default）。"""
    match = _CALIBERS_HEAD.search(metric_value)
    if match is None:
        return ()
    calibers: list[dict[str, Any]] = []
    for part in match.group(1).split("；"):
        entry = _CALIBER_ENTRY.match(part.strip())
        if entry is None:
            continue
        key, name = entry.group(1), entry.group(2).strip()
        default = name.endswith(_CALIBER_DEFAULT_SUFFIX)
        if default:
            name = name[: -len(_CALIBER_DEFAULT_SUFFIX)].strip()
        calibers.append({"key": key, "name": name, "default": default})
    return tuple(calibers)


def dump_from_store(knowledge: KnowledgeStore) -> dict[str, Any]:
    """KnowledgeStore 公开读面→词典层全量 dump（INV-2 只读——注入真源单点）。"""
    by_kind: dict[str, list[Evidence]] = {
        KIND_METRIC: [],
        KIND_TERM: [],
        KIND_OBJECT: [],
        KIND_RELATION: [],
        KIND_FAMILY: [],
    }
    for evidence in knowledge.evidence(SemanticQuery(text="")):
        by_kind.setdefault(evidence.kind, []).append(evidence)

    metrics: list[dict[str, Any]] = []
    for evidence in by_kind[KIND_METRIC]:
        value = evidence.value
        calibers = _calibers_of(value)
        default = next(
            (c["key"] for c in calibers if c.get("default")), None
        )
        metrics.append(
            {
                "slot": _slot_of(value),
                "name": value.split("：", 1)[0].strip(),
                "binding_state": evidence.binding_state,
                "calibers": [dict(c) for c in calibers],
                "default_caliber": default,
                "value": value,
                "source_id": evidence.element_id,
                "version": evidence.version,
            }
        )

    terms: list[dict[str, Any]] = []
    for evidence in by_kind[KIND_TERM]:
        terms.append(
            {
                "term": evidence.value.split("（", 1)[0].strip(),
                "banned": "已禁用" in evidence.freshness,
                "freshness": evidence.freshness,
                "value": evidence.value,
                "source_id": evidence.element_id,
            }
        )

    return {
        "metrics": metrics,
        "terms": terms,
        "objects": [
            {"obj": evidence.value.split("（", 1)[0].strip(), "value": evidence.value,
             "source_id": evidence.element_id}
            for evidence in by_kind[KIND_OBJECT]
        ],
        "relations": [
            {"rel": evidence.value.split("——", 1)[0].strip(), "value": evidence.value,
             "source_id": evidence.element_id}
            for evidence in by_kind[KIND_RELATION]
        ],
        "families": [
            {"name": evidence.value.split("：", 1)[0].strip(), "value": evidence.value,
             "source_id": evidence.element_id}
            for evidence in by_kind[KIND_FAMILY]
        ],
        "aliases": knowledge.aliases(),
        "families_map": knowledge.families(),
        "cards": list(ALL_SCHEMA_CARDS),
    }


# ---------- 上下文渲染（澄清相位注入块——三块各记一行 Manifest 来源行） ----------

# 常驻注入块标记（ContextBuilder 包裹全部注入块——graph 侧历史簿记按这对标记
# 收窄：常驻材料不重复入史，防 token 放大）。
RESIDENT_BLOCK_BEGIN = "〖台账全量·常驻注入（ledger_dump 族）〗"
RESIDENT_BLOCK_END = "〖/常驻注入〗"


def render_ledger_rows(dump: Mapping[str, Any]) -> str:
    """台账行渲染（指标/术语/对象/关系/族标注——ledger_dump 来源块正文）。"""
    lines: list[str] = []
    for metric in dump.get("metrics") or []:
        lines.append(
            f"指标｜{metric.get('value', '')}（绑定态：{metric.get('binding_state', '')}）"
        )
    for term in dump.get("terms") or []:
        lines.append(f"术语｜{term.get('value', '')}（时效：{term.get('freshness', '')}）")
    for obj in dump.get("objects") or []:
        lines.append(f"对象｜{obj.get('value', '')}")
    for relation in dump.get("relations") or []:
        lines.append(f"关系｜{relation.get('value', '')}")
    for family in dump.get("families") or []:
        lines.append(f"族标注｜{family.get('value', '')}")
    return "\n".join(lines)


def render_aliases(dump: Mapping[str, Any]) -> str:
    """别名表渲染（alias_dump 来源块正文——「别名→规范名」行族）。"""
    aliases = dump.get("aliases") or {}
    return "；".join(f"{alias}→{canonical}" for alias, canonical in aliases.items())


def render_cards(dump: Mapping[str, Any]) -> str:
    """结构卡渲染（schema_card 来源块正文——发现面白名单卡）。"""
    return "\n".join(f"- {card}" for card in (dump.get("cards") or []))
