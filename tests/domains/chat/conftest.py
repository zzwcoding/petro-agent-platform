"""chat 测试共享夹具：sqlite 底座＋假缝装配（98 §3.1 chat 测试计划——seam 处
假实现驱动四层流水线与三链链体；LLM/检索/图谱/锚校验全部可注桩）。

假缝清单（组合根生产装配的镜像——main.py 同名 callable）：
- config_loader：D2 六配置节全量投影（合同默认值——三级全开/命中即停开/
  20-20-20/rrf_rank/fast/page/fixed/qa_behavior 五字段默认）；`config` 夹具
  参数可覆写驱动 D2 配置行为变化（P1-08b 验收——配置改动可见行为变化）。
- metrics_loader / terms_loader：台账面（含 ambiguous 口径两译行——澄清帧消费源）。
- faq_matcher / faq_searcher：FAQ 索引精确路＋扩检路（P1-08b FAQ 路消费）。
- index_searcher / index_searcher_dual：报告索引合并路＋双路（S4 两路并发）。
- anchor_loader：片段锚校验（fail-closed——默认对已知 fragment 真实，可注入 None）。
- completer：LLM 出口桩（返回固定 completion.content——生成/打分/兜底 free 消费）。
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pytest

from app.domains.chat import ChatService
from app.domains.chat.domain import (
    FaqHitFace,
    FragmentAnchorFace,
    GraphHitFace,
    IndexHitFace,
    MetricFace,
    RetrievalConfigFace,
    TermFace,
)
from app.domains.chat.store import ensure_chat_tables
from app.domains.security import SecurityService
from app.domains.security.store import ensure_audit_table
from app.infra.db import ConnectionManager, DatabaseSpec

AQIANG = "阿强 · 平台运维"

DEFAULT_CONFIG = RetrievalConfigFace(
    order_levels=(True, True, True),
    early_stop=True,
    semantic_top_k=20,
    keyword_top_k=20,
    merge="rrf_rank",
    top_n=20,
    rerank="fast",
    citation_format="page",
    fallback_strategy="fixed",
    fallback_text="报告库里没有找到能回答这个问题的内容。我不能凭空编——请换个问法，或联系资料员补充报告。",
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
    """假缝登记（调用计数——「六路真扫」「精排逐条打分」等断言的观测面）。"""

    metrics: list[MetricFace] = field(default_factory=default_metrics)
    terms: list[TermFace] = field(default_factory=default_terms)
    faq_hit: FaqHitFace | None = None
    faq_similar: list[FaqHitFace] = field(default_factory=list)
    index_hits: list[IndexHitFace] = field(default_factory=list)  # 装配合并路
    index_vector: list[IndexHitFace] = field(default_factory=list)  # 双路·向量腿
    index_keyword: list[IndexHitFace] = field(default_factory=list)  # 双路·关键词腿
    graph_hits: list[GraphHitFace] = field(default_factory=list)
    anchors: dict[str, FragmentAnchorFace | None] = field(default_factory=dict)
    config: RetrievalConfigFace = DEFAULT_CONFIG
    completion: str = "依据材料作答 [c1]。"
    calls: dict[str, int] = field(default_factory=dict)
    completions: list[str] = field(default_factory=list)  # caller 归因记录
    intent_reply: str | None = None  # LLM 意图裁决返回（None＝生成文案混答→解析坏兜底）
    fail_intent: bool = False  # True＝意图裁决调用直接抛（超时/网络错兜底路径）
    intent_delay: float = 0.0  # 意图裁决延迟秒（超时兜底路径）
    faq_served: list[str] = field(default_factory=lambda: ["N-02 井是什么时候投产的？"])
    workflows: list[tuple[str, str]] = field(default_factory=lambda: [("月度产量核查", "登记")])
    reports: list[str] = field(default_factory=list)

    def _bump(self, key: str) -> None:
        self.calls[key] = self.calls.get(key, 0) + 1

    async def load_config(self) -> RetrievalConfigFace:
        self._bump("config")
        return self.config

    async def load_metrics(self) -> list[MetricFace]:
        self._bump("metrics")
        return list(self.metrics)

    async def load_terms(self) -> list[TermFace]:
        self._bump("terms")
        return list(self.terms)

    async def match_faq(self, question: str) -> FaqHitFace | None:
        self._bump("faq")
        return self.faq_hit

    async def search_faq_similar(self, question: str, top_k: int) -> list[FaqHitFace]:
        self._bump("faq_search")
        return list(self.faq_similar[:top_k])

    async def search_index(self, question: str) -> list[IndexHitFace]:
        self._bump("index")
        return list(self.index_hits)

    async def search_index_dual(
        self, question: str, vector_top_k: int, keyword_top_k: int
    ) -> tuple[list[IndexHitFace], list[IndexHitFace]]:
        self._bump("index_dual")
        return list(self.index_vector[:vector_top_k]), list(self.index_keyword[:keyword_top_k])

    async def search_graph(self, question: str) -> list[GraphHitFace]:
        self._bump("graph")
        return list(self.graph_hits)

    async def load_anchor(self, fragment_id: str) -> FragmentAnchorFace | None:
        self._bump("anchor")
        if fragment_id in self.anchors:
            return self.anchors[fragment_id]
        # 默认锚＝标准命中报告（_hit 工厂的 report_id 约定 rpt-1）——fail-closed
        # 反例（片段不存在/归属他报告）由 anchors 显式覆写承载。
        return FragmentAnchorFace(
            fragment_id=fragment_id, report_id="rpt-1", report="N-02 完井报告",
            section="01 井基本情况",
        )

    async def list_faq_served(self) -> list[str]:
        self._bump("faq_list")
        return list(self.faq_served)

    async def list_workflows(self) -> list[tuple[str, str]]:
        self._bump("wf_list")
        return list(self.workflows)

    async def list_reports(self) -> list[str]:
        self._bump("rpt_list")
        return list(self.reports)

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any:
        self._bump("complete")
        self.completions.append(caller)
        if caller == "chat.intent.verdict":
            if self.fail_intent:
                raise RuntimeError("意图裁决上游失败（桩）")
            if self.intent_delay:
                await asyncio.sleep(self.intent_delay)
            if self.intent_reply is not None:
                return SimpleNamespace(content=self.intent_reply, call_id="call-intent",
                                       served_alias=alias)
        return SimpleNamespace(content=self.completion, call_id="call-test", served_alias=alias)


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
    """假缝装配（生产＝main.py 组合根同构——配置/台账/FAQ/报告索引/图谱/锚/LLM）。"""
    return ChatService(
        db,
        audit=SecurityService(db),  # B12 真写口（sqlite 底座——审计断言直读表）
        config_loader=seams.load_config,
        metrics_loader=seams.load_metrics,
        terms_loader=seams.load_terms,
        faq_matcher=seams.match_faq,
        faq_searcher=seams.search_faq_similar,
        index_searcher=seams.search_index,
        index_searcher_dual=seams.search_index_dual,
        graph_searcher=seams.search_graph,
        anchor_loader=seams.load_anchor,
        completer=seams,  # Seams.complete 满足 Completer 协议（生产＝GatewayService）
        faq_lister=seams.list_faq_served,
        workflow_lister=seams.list_workflows,
        report_lister=seams.list_reports,
    )


async def collect(events: Any) -> list[Any]:
    """SSE 事件帧流收帧（域面 SseEvent 序——api 层信封渲染归 API 测试）。"""
    return [event async for event in events]


def events_by_name(events: list[Any]) -> dict[str, list[dict[str, Any]]]:
    """事件帧按类型分组（树叙事断言面——node/node_line 逐帧可断言）。"""
    out: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        out.setdefault(event.event, []).append(event.data)
    return out


def node_walk(events: list[Any]) -> list[tuple[str, str]]:
    """node 帧步进投影（key, state) 序——树叙事时序金样本断言用。"""
    return [
        (event.data["key"], event.data["state"])
        for event in events
        if event.event == "node"
    ]


def walk_projection(events: list[Any]) -> list[tuple[str, ...]]:
    """全帧序列投影：node 帧展开为 (event, key, state)、其余帧为 (event,)——
    帧序金样本断言的单源形状。"""
    out: list[tuple[str, ...]] = []
    for event in events:
        if event.event == "node":
            out.append(("node", event.data["key"], event.data["state"]))
        else:
            out.append((event.event,))
    return out
