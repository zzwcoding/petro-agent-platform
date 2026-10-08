"""knowledge.store —— KnowledgeStore seam 与内存适配器。

Seam 裁决（specs/modules.md knowledge 卡）：KnowledgeStore＝「查台账这一可替换
面」，适配器 InMemoryKnowledgeStore（fixture 快照）——测试计划点名的 adapter。
四公开方法＝specs/knowledge.md 接口定义节原形（evidence/metric_by_name/aliases/
families），全程只读（INV-2：零写副作用、返回容器一律副本、快照注入后不改）。

行为约定对位（specs/knowledge.md）：
1. 只读 sem_* 现行行——快照即现行行投影，店零写路径；
2. metric_by_name 命中顺序：精确名→别名归一→None；别名命中 source 注
   「经别名归一（X→Y）」（evidence 面同序同注）；
3. binding_state 由台账绑定关系推导（domain.py 判定单点，店不自判）；
4. expired 带届满日期（freshness＝term_expiry 展示串）与现口径指引
   （value 携 type「别名 → X」族原文）；
5. families 返回本体导出物族标注（relation group 透传）。

匹配语义（evidence 精确名段）：指标按 slot_name→台账原名两键、术语按 term、
对象按 obj、关系按 rel 全串、族标注按导出物行 name；空 text＝浏览态（kinds 内
全要素按账本序）。子串/模糊匹配不做——读面确定性优先，召回归检索链。
"""

from __future__ import annotations

import abc
from dataclasses import replace
from datetime import date

from appv2.infra import clock
from appv2.knowledge.domain import (
    BINDING_UNBOUND,
    KIND_ALL,
    KIND_FAMILY,
    KIND_METRIC,
    KIND_OBJECT,
    KIND_RELATION,
    KIND_TERM,
    Evidence,
    SemanticQuery,
    metric_binding_state,
    term_binding_state,
    term_expiry,
)
from appv2.knowledge.snapshot import (
    FamilyRow,
    LedgerSnapshot,
    MetricRow,
    ObjectRow,
    RelationRow,
    TermRow,
)

# 别名命中注记（specs/knowledge.md 行为约定 2——source 如实注明，逐字含
# 「经别名归一」；X→Y＝原查询词→规范名）。
_ALIAS_NOTE = " · 经别名归一（{0}→{1}）"


def _append_note(hits: list[Evidence], note: str | None) -> list[Evidence]:
    """别名命中段 source 追加归一注记（精确段原样——注记只在真实发生时在位）。"""
    if note is None:
        return hits
    return [replace(ev, source=f"{ev.source}{note}") for ev in hits]


class KnowledgeStore(abc.ABC):
    """语义资产读面 seam（specs/modules.md knowledge 卡公开接口四方法）。"""

    @abc.abstractmethod
    def evidence(self, query: SemanticQuery) -> list[Evidence]:
        """语义查询→Evidence 列（空 text＝浏览态）。"""

    @abc.abstractmethod
    def metric_by_name(self, name: str) -> Evidence | None:
        """按名查指标（经别名归一后精确命中；未中＝None 不猜）。"""

    @abc.abstractmethod
    def aliases(self) -> dict[str, str]:
        """别名→规范名映射（glossary aliases 投影——副本）。"""

    @abc.abstractmethod
    def families(self) -> dict[str, list[str]]:
        """族标注（本体导出物 relation group 透传——副本）。"""


class InMemoryKnowledgeStore(KnowledgeStore):
    """快照驱动的内存读面（fixture 快照注入；零 I/O、零写路径）。"""

    def __init__(self, snapshot: LedgerSnapshot, *, today: date | None = None) -> None:
        self._snapshot = snapshot
        # 时钟唯一出口（B14）——届满判定 today 缺省取 infra.clock；测试注入固定值。
        self._today = today if today is not None else clock.now().date()
        self._metrics_by_slot: dict[str, MetricRow] = {
            row.slot_name: row for row in snapshot.metrics
        }
        self._metrics_by_name: dict[str, MetricRow] = {
            row.name: row for row in snapshot.metrics
        }
        self._terms: dict[str, TermRow] = {row.term: row for row in snapshot.terms}
        self._objects: dict[str, ObjectRow] = {row.obj: row for row in snapshot.objects}
        self._relations: dict[str, RelationRow] = {
            row.rel: row for row in snapshot.relations
        }
        self._families: dict[str, FamilyRow] = {
            row.name: row for row in snapshot.families
        }
        self._aliases: dict[str, str] = dict(snapshot.aliases)

    # ---------- 四公开方法（KnowledgeStore 实现） ----------

    def evidence(self, query: SemanticQuery) -> list[Evidence]:
        kinds = KIND_ALL if query.kinds is None else frozenset(query.kinds)
        text = query.text.strip()
        if not text:
            return self._browse(kinds)
        hits, note = self._resolve_hits(text, kinds)
        return _append_note(hits, note)

    def metric_by_name(self, name: str) -> Evidence | None:
        hits, note = self._resolve_hits(name, frozenset({KIND_METRIC}))
        if not hits:
            return None
        return _append_note(hits, note)[0]

    def aliases(self) -> dict[str, str]:
        return dict(self._aliases)

    def families(self) -> dict[str, list[str]]:
        return {row.name: list(row.group) for row in self._snapshot.families}

    # ---------- 命中装配（行为约定 2 命中顺序单点） ----------

    def _resolve_hits(
        self, text: str, kinds: frozenset[str]
    ) -> tuple[list[Evidence], str | None]:
        """精确名→别名归一 两段命中。

        返回（命中列, 归一注记）——精确段注记＝None；别名段＝「 · 经别名归一
        （原词→规范名）」，只在归一后真实命中时在位（未命中如实空列零注记）。
        """
        hits = self._exact_hits(text, kinds)
        if hits:
            return hits, None
        canonical = self._aliases.get(text)
        if canonical is None or canonical == text:
            return [], None
        hits = self._exact_hits(canonical, kinds)
        if not hits:
            return [], None
        return hits, _ALIAS_NOTE.format(text, canonical)

    def _exact_hits(self, text: str, kinds: frozenset[str]) -> list[Evidence]:
        """精确名命中（kind 固定序 metric→term→object→relation→family）。"""
        hits: list[Evidence] = []
        if KIND_METRIC in kinds:
            metric = self._metrics_by_slot.get(text)
            if metric is None:
                metric = self._metrics_by_name.get(text)
            if metric is not None:
                hits.append(self._metric_evidence(metric))
        if KIND_TERM in kinds:
            if (term := self._terms.get(text)) is not None:
                hits.append(self._term_evidence(term))
        if KIND_OBJECT in kinds:
            if (obj := self._objects.get(text)) is not None:
                hits.append(self._object_evidence(obj))
        if KIND_RELATION in kinds:
            if (relation := self._relations.get(text)) is not None:
                hits.append(self._relation_evidence(relation))
        if KIND_FAMILY in kinds:
            if (family := self._families.get(text)) is not None:
                hits.append(self._family_evidence(family))
        return hits

    def _browse(self, kinds: frozenset[str]) -> list[Evidence]:
        """浏览态：kinds 内全要素按账本序（快照构建序＝行 id 序）。"""
        out: list[Evidence] = []
        if KIND_METRIC in kinds:
            out += [self._metric_evidence(row) for row in self._snapshot.metrics]
        if KIND_TERM in kinds:
            out += [self._term_evidence(row) for row in self._snapshot.terms]
        if KIND_OBJECT in kinds:
            out += [self._object_evidence(row) for row in self._snapshot.objects]
        if KIND_RELATION in kinds:
            out += [self._relation_evidence(row) for row in self._snapshot.relations]
        if KIND_FAMILY in kinds:
            out += [self._family_evidence(row) for row in self._snapshot.families]
        return out

    # ---------- 各账行 → Evidence（value 机械拼装，零发明） ----------

    def _metric_evidence(self, row: MetricRow) -> Evidence:
        parts = [f"{row.name}：{row.def_}", f"粒度 {row.grain} · 单位 {row.unit}"]
        if row.status:
            parts.append("状态 " + "／".join(row.status))
        if row.calibers:
            branches = "；".join(
                f"{caliber['key']} {caliber['name']}"
                + ("（默认）" if caliber.get("default") else "")
                for caliber in row.calibers
            )
            parts.append(f"口径支：{branches}")
        if row.dispute:
            parts.append(f"争议注记：{row.dispute}")
        return Evidence(
            element_id=str(row.id),
            kind=KIND_METRIC,
            value="｜".join(parts),
            source=f"sem_metric#{row.id}",
            version=str(row.version),
            freshness="",  # 指标台账无时效承载列——空串不发明
            scope=row.grain,  # 统计粒度域（plan 语境消费）
            binding_state=metric_binding_state(row.slot_name),
        )

    def _term_evidence(self, row: TermRow) -> Evidence:
        _expired, display = term_expiry(row.status_key, row.expires_at, self._today)
        return Evidence(
            element_id=str(row.id),
            kind=KIND_TERM,
            value=f"{row.term}（{row.type} · {row.status}）：{row.def_}",
            source=f"sem_term#{row.id}",
            version=str(row.version),
            freshness=display,  # V1 term_expiry 展示串族（届满日期/长期/已禁用）
            scope="",
            binding_state=term_binding_state(row.status_key, row.expires_at, self._today),
        )

    def _object_evidence(self, row: ObjectRow) -> Evidence:
        return Evidence(
            element_id=str(row.id),
            kind=KIND_OBJECT,
            value=f"{row.obj}（{row.status}）：{row.attr or '—（未落）'}",
            source=f"sem_object#{row.id}",
            version=str(row.version) if row.version is not None else None,
            freshness="",
            scope="",
            binding_state=BINDING_UNBOUND,
        )

    def _relation_evidence(self, row: RelationRow) -> Evidence:
        return Evidence(
            element_id=str(row.id),
            kind=KIND_RELATION,
            value=f"{row.rel}——{row.read}",
            source=f"sem_relation#{row.id}",
            version=None,  # sem_relation 无版本列
            freshness="",
            scope="",
            binding_state=BINDING_UNBOUND,
        )

    def _family_evidence(self, row: FamilyRow) -> Evidence:
        groups = "、".join(row.group) if row.group else "—（本体未标注）"
        return Evidence(
            element_id=str(row.id),
            kind=KIND_FAMILY,
            value=f"{row.name}：族标注 {groups}",
            source="config/relation_types.json",
            version=self._snapshot.families_version,
            freshness="",
            scope="",
            binding_state=BINDING_UNBOUND,
        )
