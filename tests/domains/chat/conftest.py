"""chat 测试共享夹具：sqlite 底座＋假缝装配（98 §3.1 chat 测试计划——seam 处
假实现驱动四层流水线；LLM/检索/审批/SSE 通道全部可注桩）。

假缝清单（组合根生产装配的镜像——main.py 同名 callable）：
- qa_config_loader：合同默认值（D2 qa_behavior 五字段——faq_direct_hit=true /
  ask_missing / 0.8-0.4 等）；`qa` 夹具参数可覆写驱动 D2 配置行为变化。
- metrics_loader / terms_loader：台账面（含 ambiguous 口径两译行——澄清帧消费源）。
- faq_matcher / index_searcher：FAQ 索引与报告索引（向量＋trigram 两腿在 kb 侧，
  本夹具直接给命中面——kb 读面自身归 kb 测试）。
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import pytest

from app.domains.chat import ChatService
from app.domains.chat.domain import (
    FaqHitFace,
    GraphHitFace,
    IndexHitFace,
    MetricFace,
    QaBehaviorFace,
    TermFace,
)
from app.domains.chat.store import ensure_chat_tables
from app.domains.security import SecurityService
from app.domains.security.store import ensure_audit_table
from app.infra.db import ConnectionManager, DatabaseSpec

AQIANG = "阿强 · 平台运维"

DEFAULT_QA = QaBehaviorFace(
    faq_direct_hit=True,
    refuse_threshold=0.4,
    clarify_strategy="ask_missing",
    confidence_high=0.8,
    confidence_low=0.4,
    faq_expand_rounds=3,
)


def default_metrics() -> list[MetricFace]:
    """台账面（产量完成率精确行＋有效产量口径两译行——A1 澄清场景同源）。"""
    return [
        MetricFace(metric_id=1, name="★产量完成率", slot_name="产量完成率",
                   ambiguous=False, calibers=[], default_caliber=None),
        MetricFace(
            metric_id=2, name="★有效产量（两支口径）", slot_name="有效产量",
            ambiguous=True,
            calibers=[
                {"key": "A", "name": "开井日历折算", "default": True,
                 "desc": "分子含关井日折产"},
                {"key": "B", "name": "检修剔除", "default": False,
                 "desc": "分子剔检泵期"},
            ],
            default_caliber="A",
        ),
    ]


def default_terms() -> list[TermFace]:
    return [
        TermFace(term_id=1, term="躺井", type="黑话 → 躺井", def_text="限作业区语境"),
    ]


@dataclass
class Seams:
    """假缝登记（调用计数——「六路真扫」断言的观测面）。"""

    metrics: list[MetricFace] = field(default_factory=default_metrics)
    terms: list[TermFace] = field(default_factory=default_terms)
    faq_hit: FaqHitFace | None = None
    index_hits: list[IndexHitFace] = field(default_factory=list)
    graph_hits: list[GraphHitFace] = field(default_factory=list)  # 08b 前恒空（票面）
    qa: QaBehaviorFace = DEFAULT_QA
    calls: dict[str, int] = field(default_factory=dict)

    def _bump(self, key: str) -> None:
        self.calls[key] = self.calls.get(key, 0) + 1

    async def load_qa(self) -> QaBehaviorFace:
        self._bump("qa")
        return self.qa

    async def load_metrics(self) -> list[MetricFace]:
        self._bump("metrics")
        return list(self.metrics)

    async def load_terms(self) -> list[TermFace]:
        self._bump("terms")
        return list(self.terms)

    async def match_faq(self, question: str) -> FaqHitFace | None:
        self._bump("faq")
        return self.faq_hit

    async def search_index(self, question: str) -> list[IndexHitFace]:
        self._bump("index")
        return list(self.index_hits)

    async def search_graph(self, question: str) -> list[GraphHitFace]:
        self._bump("graph")
        return list(self.graph_hits)


Loader = Callable[[Seams], Awaitable[Any]]


@pytest.fixture
async def chat_db(tmp_path: Any) -> AsyncIterator[ConnectionManager]:
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "chat.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_chat_tables(manager.engine())
    await ensure_audit_table(manager.engine())
    yield manager
    await manager.dispose()


@pytest.fixture
def seams() -> Seams:
    return Seams()


@pytest.fixture
def service(chat_db: ConnectionManager, seams: Seams) -> ChatService:
    return make_service(chat_db, seams)


def make_service(db: ConnectionManager, seams: Seams) -> ChatService:
    """假缝装配（生产＝main.py 组合根同构——qa/台账/FAQ 索引/报告索引 callable）。"""
    return ChatService(
        db,
        audit=SecurityService(db),  # B12 真写口（sqlite 底座——审计断言直读表）
        qa_config_loader=seams.load_qa,
        metrics_loader=seams.load_metrics,
        terms_loader=seams.load_terms,
        faq_matcher=seams.match_faq,
        index_searcher=seams.search_index,
        graph_searcher=seams.search_graph,
    )


async def collect(events: Any) -> list[Any]:
    """SSE 事件帧流收帧（域面 SseEvent 序——api 层信封渲染归 API 测试）。"""
    return [event async for event in events]
