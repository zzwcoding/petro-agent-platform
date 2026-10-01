"""B5 graph 子域服务编排单测（sqlite 底座＋桩 LLM＋FakeGraphStore——永不触网）。

覆盖：抽取设置读写（出厂默认/强校两态/400 族/B1 活动流）、整图读（404/开关
空态/legend stats）、抽取管线（IngestCompleted graph 支路——chunk 挑选闸/
三道闸/过闸写图/拦边留痕）、extract_snapshot confirm 定型（B9 组合根注入）、
LLM 起草、被拦边清单。
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.domains.derivatives import DerivativesService
from app.domains.derivatives import domain as d
from app.domains.derivatives.service import load_extract_config_snapshot
from app.domains.gateway import Completion
from app.domains.kb import KbService
from app.infra.db import ConnectionManager
from tests.domains.derivatives.conftest import DEMO_TEXT, make_report
from tests.domains.kb.conftest import FakeObjectStorage, StubCompleter

# graph.extract 桩应答：三道闸各一票——过闸（evidence＝切片原句逐字摘录）、
# 类型闸拦下（rel「管辖着」不在清单）、依据闸拦下（evidence 非原文）、
# 弃权闸自报（uncertain）。
DEMO_SENTENCE = "位于渤南区块 CEP-A 平台"
GRAPH_EXTRACT_ANSWER = (
    '[{"from":"N-02","from_type":"井","rel":"隶属","to":"渤南","to_type":"区块",'
    f'"evidence":"{DEMO_SENTENCE}","note":null,"uncertain":false}},'
    '{"from":"N-02","from_type":"井","rel":"管辖着","to":"N-02","to_type":"井",'
    '"evidence":"x","uncertain":false},'
    '{"from":"N-02","from_type":"井","rel":"隶属","to":"渤中","to_type":"区块",'
    '"evidence":"这句话不在切片原文里","uncertain":false},'
    '{"from":"N-06","from_type":"井","rel":"承载","to":"CEP-A","to_type":"平台",'
    f'"evidence":"{DEMO_SENTENCE}","uncertain":true}}]'
).replace("}}", "}")

SAVED_CONFIG = {
    "entity_types": ["井", "区块", "平台"],
    "relation_tags": [{"rel": "隶属", "example": "", "desc": "井属于哪个区块"}],
    "few_shot_examples": [],
    "custom_instructions": "关系必须原文有依据；拿不准宁可跳过",
}


class FakeGraphStore:
    """图存储桩（内存字典——seam 形状照 infra.graph_store.GraphStore）。"""

    def __init__(self) -> None:
        self.nodes: dict[tuple[str, str], dict[str, Any]] = {}
        self.edges: dict[tuple[str, str], dict[str, Any]] = {}
        self.blocked: dict[tuple[str, str, str], dict[str, Any]] = {}

    async def upsert_node(self, lib_id: str, *, node_id: str, label: str,
                          node_type: str, short: str, sub: str) -> None:
        self.nodes[(lib_id, node_id)] = {
            "id": node_id, "label": label, "type": node_type,
            "short": short, "sub": sub,
        }

    async def upsert_edge(self, lib_id: str, *, key: str, from_id: str, rel: str,
                          to_id: str, note: str | None, evidence: str,
                          chunk_id: str, report_id: str) -> None:
        self.edges[(lib_id, key)] = {
            "key": key, "from": from_id, "rel": rel, "to": to_id, "note": note,
            "evidence": evidence, "chunk_id": chunk_id, "report_id": report_id,
        }

    async def record_blocked(self, lib_id: str, *, key: str, from_id: str,
                             from_type: str, rel: str, to_id: str, to_type: str,
                             reason_code: str, reason: str, report_id: str,
                             report_title: str, chunk_id: str | None,
                             blocked_at: str) -> None:
        self.blocked[(lib_id, key, report_id)] = {
            "key": key, "from": from_id, "from_type": from_type, "rel": rel,
            "to": to_id, "to_type": to_type, "reason_code": reason_code,
            "reason": reason, "report_id": report_id,
            "report_title": report_title, "chunk_id": chunk_id,
            "blocked_at": blocked_at,
        }

    async def read_net(self, lib_id: str) -> dict[str, Any]:
        return {
            "nodes": [n for (lib, _), n in sorted(self.nodes.items()) if lib == lib_id],
            "edges": [e for (lib, _), e in sorted(self.edges.items()) if lib == lib_id],
        }

    async def list_blocked(self, lib_id: str) -> list[dict[str, Any]]:
        return [b for (lib, _k, _r), b in sorted(self.blocked.items()) if lib == lib_id]


class ChunkAwareCompleter:
    """graph.extract 按切片内容出脚本：不含依据句的切片返回空数组（同 LLM
    弃权答辩纪律——f1/f3 短切片无该句，避免拦边跨切片覆盖干扰三值断言）。"""

    def __init__(self, inner: StubCompleter) -> None:
        self._inner = inner
        self.calls = inner.calls

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str,
        **params: Any,
    ) -> Completion:
        if caller == "graph.extract" and DEMO_SENTENCE not in messages[-1]["content"]:
            self.calls.append((caller, messages[-1]["content"]))
            return Completion(
                content="[]", prompt_tokens=1, completion_tokens=1,
                usage_estimated=False, call_id="call-stub", cost_yuan=0.0,
                fallback=False, served_alias=alias,
            )
        return await self._inner.complete(alias, messages, caller=caller, **params)


Env = tuple[KbService, DerivativesService, FakeGraphStore, StubCompleter]


@pytest.fixture
def graph() -> FakeGraphStore:
    return FakeGraphStore()


@pytest.fixture
async def env(
    wiki_env: tuple[KbService, DerivativesService, FakeObjectStorage,
                    StubCompleter, Any],
    graph: FakeGraphStore,
) -> AsyncIterator[Env]:
    """kb＋derivatives＋图存储桩（graph 注入位＝main.py 组合根同位）。"""
    kb, derivatives, _storage, completer, _bus = wiki_env
    derivatives._graph = graph
    completer.answers["graph.extract"] = GRAPH_EXTRACT_ANSWER
    completer.answers["graph.draft"] = "N-02 井隶属渤南区块。\nN-02 —隶属→ 渤南"
    yield kb, derivatives, graph, completer


# ---------- 抽取设置读写（端点 2/3） ----------


class TestExtractConfig:
    async def test_default_before_save_is_ontology_aligned(self, env: Env) -> None:
        kb, derivatives, _g, _c = env
        lib_id, _r, _t = await make_report(kb, _kb_storage(kb))
        view = await derivatives.get_extract_config(lib_id)
        assert view.lib_name.startswith("完井报告库")
        assert view.saved_at is None and view.saved_by is None
        assert "井" in view.config.entity_types
        assert [t.rel for t in view.config.relation_tags] == [
            "隶属", "承载", "受效", "作用于", "取样自",
        ]

    async def test_save_and_read_back(self, env: Env) -> None:
        kb, derivatives, _g, _c = env
        lib_id, _r, _t = await make_report(kb, _kb_storage(kb))
        receipt = await derivatives.save_extract_config(
            lib_id,
            {
                "entity_types": ["井", "区块", "平台", "油田", "措施"],
                "relation_tags": [
                    {"rel": "隶属", "example": "N-02 —隶属→ 渤南",
                     "desc": "井属于哪个区块"},
                    {"rel": "承载", "example": "", "desc": "井装在哪个平台上"},
                    {"rel": "受效", "example": "", "desc": "劈分系数合计＝1"},
                    {"rel": "作用于", "example": "", "desc": "措施做在哪口井上"},
                ],
                "few_shot_examples": [
                    {"sentence": "N-02 井隶属渤南区块。", "triple": "N-02 —隶属→ 渤南"}
                ],
                "custom_instructions": "关系必须原文有依据；拿不准宁可跳过",
            },
            "小李 · 地质/质检",
        )
        assert receipt.hint == d.SAVE_HINT
        assert receipt.saved_by == "小李 · 地质/质检"
        view = await derivatives.get_extract_config(lib_id)
        assert view.saved_at == receipt.saved_at
        assert [t.rel for t in view.config.relation_tags] == [
            "隶属", "承载", "受效", "作用于",
        ]
        assert view.config.few_shot_examples[0].triple == "N-02 —隶属→ 渤南"
        # 同事务记 B1 活动流（F62 跨页留痕——「修改抽取设置」）
        activities = await kb.library_activities(lib_id)
        row = next(a for a in activities if a.action == "修改抽取设置")
        assert row.who == "小李 · 地质/质检"
        assert "实体类型 5 类 · 关系标签 4 个" in row.target

    async def test_strong_check_rejects_with_detail(self, env: Env) -> None:
        kb, derivatives, _g, _c = env
        lib_id, _r, _t = await make_report(kb, _kb_storage(kb))
        with pytest.raises(d.GraphOntologyMismatchError) as ei:
            await derivatives.save_extract_config(
                lib_id,
                {"entity_types": ["机灵鬼"], "relation_tags": [{"rel": "管辖着"}],
                 "custom_instructions": ""},
                "小李 · 地质/质检",
            )
        kinds = {m["kind"]: m for m in ei.value.mismatches}
        assert set(kinds) == {"entity_type", "relation_tag"}
        assert kinds["entity_type"]["value"] == "机灵鬼"
        assert kinds["entity_type"]["nearest"]  # 最接近台账词条不空

    async def test_weak_state_before_wiring(self, env: Env) -> None:
        # 接线前过渡态（strong_check=False——仅形状校验照跑，B5 端点 3 两态注记）。
        kb, derivatives, _g, _c = env
        lib_id, _r, _t = await make_report(kb, _kb_storage(kb))
        receipt = await derivatives.save_extract_config(
            lib_id,
            {"entity_types": ["Person"], "relation_tags": [], "custom_instructions": ""},
            "小李 · 地质/质检",
            strong_check=False,
        )
        assert receipt.hint == d.SAVE_HINT

    async def test_shape_validation_400s(self, env: Env) -> None:
        kb, derivatives, _g, _c = env
        lib_id, _r, _t = await make_report(kb, _kb_storage(kb))
        with pytest.raises(d.GraphParamError):  # entity_types 空
            await derivatives.save_extract_config(
                lib_id, {"entity_types": [], "relation_tags": [],
                         "custom_instructions": ""},
                "x",
            )
        with pytest.raises(d.GraphParamError):  # relation_tags 重复 rel
            await derivatives.save_extract_config(
                lib_id,
                {"entity_types": ["井"],
                 "relation_tags": [{"rel": "隶属"}, {"rel": "隶属"}],
                 "custom_instructions": ""},
                "x",
            )
        with pytest.raises(d.GraphParamError):  # 缺段
            await derivatives.save_extract_config(
                lib_id, {"entity_types": ["井"], "relation_tags": []}, "x"
            )

    async def test_unknown_lib_404(self, env: Env) -> None:
        _kb, derivatives, _g, _c = env
        with pytest.raises(d.GraphNotFoundError):
            await derivatives.get_extract_config("lib-none")
        with pytest.raises(d.GraphNotFoundError):
            await derivatives.graph_net("lib-none")
        with pytest.raises(d.GraphNotFoundError):
            await derivatives.blocked_edges("lib-none")


def _kb_storage(kb: KbService) -> FakeObjectStorage:
    return kb._storage  # 夹具装配直取（测试同构先例）


# ---------- 整图读（端点 1——开关空态/legend stats/namespace 隔离） ----------


class TestGraphNet:
    async def test_switch_off_returns_empty_net(self, env: Env) -> None:
        kb, derivatives, g, _c = env
        lib_id, _r, _t = await make_report(kb, _kb_storage(kb))
        # 既有图数据仍留在图存储（保留/清理属图存储生命周期批）——读面空态。
        await g.upsert_node(lib_id, node_id="N-02", label="N-02", node_type="井",
                            short="N-02", sub="井")
        await kb.save_library_config(
            lib_id,
            switches={"semantic": True, "keyword": True, "wiki": True, "graph": False},
            mode="smart", add_summary=True, add_questions=True,
            status=None, actor_who="aqiang",
        )
        net = await derivatives.graph_net(lib_id)
        assert net.lib_name
        assert net.nodes == [] and net.edges == [] and net.legend == []
        assert net.stats == {"nodes": 0, "edges": 0}

    async def test_net_shape_with_data(self, env: Env) -> None:
        kb, derivatives, g, _c = env
        lib_id, _r, _t = await make_report(kb, _kb_storage(kb))
        await g.upsert_node(lib_id, node_id="N-02", label="N-02", node_type="井",
                            short="N-02", sub="井")
        await g.upsert_node(lib_id, node_id="N-06", label="N-06", node_type="井",
                            short="N-06", sub="井")
        await g.upsert_node(lib_id, node_id="渤南", label="渤南", node_type="区块",
                            short="渤南", sub="区块")
        await g.upsert_edge(lib_id, key="N-02|隶属|渤南", from_id="N-02",
                            rel="隶属", to_id="渤南", note=None,
                            evidence="e", chunk_id="f1", report_id="r1")
        # namespace 隔离：他库数据不进本库整图读
        await g.upsert_node("lib-other", node_id="X", label="X", node_type="井",
                            short="X", sub="井")
        net = await derivatives.graph_net(lib_id)
        assert net.stats == {"nodes": 3, "edges": 1}
        assert {lg.type: lg.count for lg in net.legend} == {"井": 2, "区块": 1}
        assert net.edges[0].key == "N-02|隶属|渤南"
        assert net.edges[0].evidence_chunk_id == "f1"


# ---------- 抽取管线（IngestCompleted graph 支路——三道闸真跑） ----------


class TestExtractionPipeline:
    async def test_ingest_with_graph_on_extracts_and_blocks(self, env: Env) -> None:
        kb, derivatives, g, completer = env
        derivatives._gateway = ChunkAwareCompleter(completer)
        lib_id, _r, _t = await make_report(
            kb, _kb_storage(kb),
            lib_config={"semantic": True, "keyword": True, "wiki": False,
                        "graph": True},
        )
        assert len(g.edges) == 1, "只有过闸边入图（铁律消费面）"
        (edge,) = g.edges.values()
        assert edge["key"] == "N-02|隶属|渤南"
        assert edge["evidence"] == DEMO_SENTENCE
        assert edge["chunk_id"] and edge["report_id"]
        assert {n["id"] for n in g.nodes.values()} == {"N-02", "渤南"}
        # 三道闸拦下三票：类型闸（取样自）/依据闸（非原文）/弃权闸（uncertain）
        reasons = {b["reason_code"] for b in g.blocked.values()}
        assert reasons == {"type_mismatch", "no_evidence", "uncertain"}
        assert all(b["report_title"] for b in g.blocked.values())
        # few-shot 配置进 prompt（ExtractConfig 四段全在提示词里）
        extract_calls = [c for caller, c in completer.calls if caller == "graph.extract"]
        assert extract_calls and "隶属" in extract_calls[0]
        assert '"evidence"' in extract_calls[0]
        # 端点 4 只读消费面：被拦边清单真留痕
        page = await derivatives.blocked_edges(lib_id)
        assert page.stats == {"blocked": 3}
        assert {b.reason_code for b in page.blocked_edges} == {
            "type_mismatch", "no_evidence", "uncertain",
        }
        assert all(b.report_title for b in page.blocked_edges)

    async def test_graph_off_no_extraction(self, env: Env) -> None:
        kb, _derivatives, g, completer = env
        await make_report(
            kb, _kb_storage(kb),
            lib_config={"semantic": True, "keyword": True, "wiki": False,
                        "graph": False},
        )
        assert g.edges == {} and g.blocked == {}
        assert not any(c == "graph.extract" for _, c in completer.calls)


# ---------- extract_snapshot confirm 定型（B9 组合根注入——main.py 同位） ----------


class TestExtractSnapshot:
    async def test_typed_at_confirm_into_task_and_event(
        self,
        wiki_db: ConnectionManager,
        wiki_env: tuple[KbService, DerivativesService, FakeObjectStorage,
                        StubCompleter, Any],
        graph: FakeGraphStore,
    ) -> None:
        kb, derivatives, storage, completer, bus = wiki_env
        derivatives._graph = graph
        completer.answers["graph.extract"] = GRAPH_EXTRACT_ANSWER
        captured: list[Any] = []

        async def _capture(event: Any) -> None:
            captured.append(event)

        await bus.subscribe("IngestCompleted", _capture)
        # 组合根注入（main.py lifespan 同位——kb 只见 callable，B9 无 import）
        kb._extract_snapshot_loader = (
            lambda lib_id: load_extract_config_snapshot(wiki_db, lib_id)
        )
        lib = await kb.create_library("快照库", "completion", "aqiang · 平台运维")
        await derivatives.save_extract_config(
            lib.lib_id, SAVED_CONFIG, "小李 · 地质/质检"
        )
        receipt = await kb.upload_init("快照.txt", len(DEMO_TEXT.encode()),
                                       lib.lib_id, "xiaoli · 地质/质检")
        await storage.put(receipt.put_url.split("/put/")[-1], DEMO_TEXT.encode())
        await kb.upload_confirm(receipt.upload_id, "xiaoli · 地质/质检")
        for _ in range(200):
            if captured and captured[0].payload.get("extract_snapshot"):
                break
            await __import__("asyncio").sleep(0.02)
        assert captured, "IngestCompleted 未发出"
        payload = captured[0].payload
        # confirm 时刻定型的抽取设置快照（B5 端点 3 注记——非保存后再变）
        snapshot = payload["extract_snapshot"]
        assert snapshot["entity_types"] == ["井", "区块", "平台"]
        assert snapshot["custom_instructions"] == "关系必须原文有依据；拿不准宁可跳过"
        assert snapshot["relation_tags"][0]["rel"] == "隶属"
        # 定型快照随任务行持久（99 §2.5 kb_ingest_task.extract_snapshot）
        from app.domains.kb.store import TaskStore

        row = await TaskStore(wiki_db).get(payload["task_id"])
        assert row is not None and row.extract_snapshot is not None
        assert row.extract_snapshot["entity_types"] == ["井", "区块", "平台"]

    async def test_loader_without_saved_config_returns_default(
        self, wiki_db: ConnectionManager
    ) -> None:
        snapshot = await load_extract_config_snapshot(wiki_db, "lib-x")
        assert snapshot["entity_types"] and snapshot["relation_tags"]
        assert snapshot["custom_instructions"] == d.DEFAULT_CUSTOM_INSTRUCTIONS


# ---------- LLM 起草（三源辅助③——真实实现走 gateway.complete） ----------


class TestDraftExample:
    async def test_draft_by_rel(self, env: Env) -> None:
        kb, derivatives, _g, completer = env
        lib_id, _r, _t = await make_report(kb, _kb_storage(kb))
        drafted = await derivatives.draft_example(lib_id, rel="隶属")
        assert drafted.triple == "N-02 —隶属→ 渤南"
        assert any(caller == "graph.draft" for caller, _ in completer.calls)

    async def test_draft_with_sentence_prefills_triple(self, env: Env) -> None:
        kb, derivatives, _g, _c = env
        lib_id, _r, _t = await make_report(kb, _kb_storage(kb))
        drafted = await derivatives.draft_example(
            lib_id, rel="隶属", sentence="N-02 井隶属渤南区块。"
        )
        assert drafted.sentence and drafted.triple

    async def test_empty_rel_rejected(self, env: Env) -> None:
        kb, derivatives, _g, _c = env
        lib_id, _r, _t = await make_report(kb, _kb_storage(kb))
        with pytest.raises(d.GraphParamError):
            await derivatives.draft_example(lib_id, rel="  ")
