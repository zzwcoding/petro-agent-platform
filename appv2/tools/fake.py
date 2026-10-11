"""tools.fake —— 假引擎 adapter（specs/modules.md tools 卡「Adapter: 假引擎」；
P-006 runtime 票复用件）。

三个假引擎与三引擎缝同形（结构性类型——QueryFace/RetrievalFace Protocol、
KnowledgeStore 抽象基类），供测试与 runtime 票注入：
- FakeKnowledgeStore：剧本化台账读面（应答罐头＋四方法调用计数——零触测试的
  观测面）；
- FakeQueryEngine：剧本化问数引擎（validate 按 ledger/candidates 面模拟合同
  拒因；run 应答罐头/异常注入——错误三分类与六联合态映射的被控源）；
- FakeRetrievalEngine：剧本化检索引擎（RetrievalNeed 全量捕获——anchors/
  family_hints/budget 参数契约断言面；retrieve/graph 应答罐头）；
- FakeUpstreamRejection：上游 4xx/5xx 类拒绝桩（status_code 属性——与真实
  网关/HTTP 异常形状对齐的 duck 型，classify_exception 同判）。

全部只读（INV-2）：应答罐头返回副本容器，注入后不改；调用计数是观测面不是
写路径。
"""

from __future__ import annotations

from collections.abc import Iterable

from appv2.knowledge import Evidence, KnowledgeStore, SemanticQuery
from appv2.query import PlanCheck, QueryOutcome, QueryPlan
from appv2.retrieval import RetrievalBundle, RetrievalNeed


class FakeUpstreamRejection(Exception):
    """上游拒绝桩（status_code 属性——4xx→bad_args／5xx→retryable 的被测对象）。"""

    def __init__(self, status_code: int, message: str = "上游拒绝") -> None:
        super().__init__(message)
        self.status_code = status_code


class FakeKnowledgeStore(KnowledgeStore):
    """剧本化台账读面（evidence/metric_by_name 应答罐头＋调用计数）。"""

    def __init__(
        self,
        *,
        evidence_hits: list[Evidence] | None = None,
        metric_hit: Evidence | None = None,
        aliases: dict[str, str] | None = None,
        families: dict[str, list[str]] | None = None,
    ) -> None:
        self._evidence_hits = list(evidence_hits or [])
        self._metric_hit = metric_hit
        self._aliases = dict(aliases or {})
        self._families = {key: list(value) for key, value in (families or {}).items()}
        self.evidence_calls = 0
        self.metric_calls = 0
        self.alias_calls = 0
        self.family_calls = 0

    def evidence(self, query: SemanticQuery) -> list[Evidence]:
        self.evidence_calls += 1
        return list(self._evidence_hits)

    def metric_by_name(self, name: str) -> Evidence | None:
        self.metric_calls += 1
        return self._metric_hit

    def aliases(self) -> dict[str, str]:
        self.alias_calls += 1
        return dict(self._aliases)

    def families(self) -> dict[str, list[str]]:
        self.family_calls += 1
        return {key: list(value) for key, value in self._families.items()}


class FakeQueryEngine:
    """剧本化问数引擎（validate 合同拒因面＋run 应答罐头/异常注入）。

    validate 未剧本 check 时按假台账面模拟合同拒因：槽位不在
    ledger_metric_slots→「不在指标台账」；candidates 给定且槽位越集→FX-13
    「不在问句指标候选集」。run 优先注入异常（run_error），否则吐 outcome
    罐头（未剧本即断言失败——装配缺应答当场暴露）。
    """

    def __init__(
        self,
        *,
        ledger_metric_slots: frozenset[str] = frozenset(
            {"日产油量", "日产液量", "油压"}
        ),
        check: PlanCheck | None = None,
        outcome: QueryOutcome | None = None,
        run_error: Exception | None = None,
    ) -> None:
        self.ledger_metric_slots: set[str] = set(ledger_metric_slots)
        self.check = check
        self.outcome = outcome
        self.run_error = run_error
        self.validate_calls = 0
        self.run_calls = 0
        self.plans: list[QueryPlan] = []

    def validate(
        self, plan: QueryPlan, *, candidates: Iterable[str] | None = None
    ) -> PlanCheck:
        self.validate_calls += 1
        self.plans.append(plan)
        if self.check is not None:
            return self.check
        if plan.metric_slot not in self.ledger_metric_slots:
            return PlanCheck(
                ok=False,
                reason=(
                    f"metric_slot {plan.metric_slot!r} 不在指标台账——"
                    "不在目录不代答（台账绑定校验）"
                ),
            )
        if candidates is not None:
            allowed = frozenset(candidates)
            if plan.metric_slot not in allowed:
                return PlanCheck(
                    ok=False,
                    reason=(
                        f"metric_slot {plan.metric_slot!r} 不在问句指标候选集 "
                        f"{sorted(allowed)}——指标替换封堵（FX-13）：不代问句外指标出数"
                    ),
                )
        return PlanCheck(ok=True, reason=None)

    def run(
        self, plan: QueryPlan, *, approved_tables: tuple[str, ...] = ()
    ) -> QueryOutcome:
        self.run_calls += 1
        if self.run_error is not None:
            raise self.run_error
        if self.outcome is None:
            raise AssertionError("FakeQueryEngine.outcome 未剧本化——测试装配缺应答")
        return self.outcome


class FakeRetrievalEngine:
    """剧本化检索引擎（RetrievalNeed 全量捕获——参数契约断言面；应答罐头）。"""

    def __init__(
        self,
        *,
        bundle: RetrievalBundle | None = None,
        graph_bundle: RetrievalBundle | None = None,
    ) -> None:
        self.bundle = bundle or RetrievalBundle(
            observations=[], window_note="召回 0 支/送窗 0 支"
        )
        self.graph_bundle = graph_bundle or RetrievalBundle(
            observations=[], window_note="召回 0 支/送窗 0 支"
        )
        self.needs: list[RetrievalNeed] = []
        self.retrieve_calls = 0
        self.graph_calls = 0

    async def retrieve(self, need: RetrievalNeed) -> RetrievalBundle:
        self.retrieve_calls += 1
        self.needs.append(need)
        return self.bundle

    async def graph(self, need: RetrievalNeed) -> RetrievalBundle:
        self.graph_calls += 1
        self.needs.append(need)
        return self.graph_bundle
