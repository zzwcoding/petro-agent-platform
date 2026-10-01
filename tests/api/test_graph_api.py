"""B5 /api/graph 路由族 API 测试——四条合同路由＋起草端点全往返。

装配：sqlite 底座＋真实 KbService＋DerivativesService＋图存储桩＋桩 LLM
（dependency_overrides 替换服务定位，不触 main.py lifespan；红线：任何测试
不得真实调用 MiniMax/GLM 端点）。
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_derivatives, get_kb, get_security
from app.api.errors import install_error_handlers
from app.api.graph import router as graph_router
from app.api.kb import router as kb_router
from app.api.security import router as security_router
from app.domains.derivatives import DerivativesService
from app.domains.derivatives.store import ensure_derivatives_tables
from app.domains.kb import KbService
from app.domains.kb.store import ensure_kb_tables
from app.domains.security import SecurityService
from app.domains.security.store import ensure_audit_table
from app.infra.db import ConnectionManager, DatabaseSpec
from app.infra.eventbus import InMemoryEventBus
from tests.domains.derivatives.conftest import DEMO_TEXT
from tests.domains.derivatives.test_graph_service_unit import FakeGraphStore
from tests.domains.kb.conftest import FakeObjectStorage, StubCompleter

SAVED_CONFIG = {
    "entity_types": ["井", "区块", "平台", "油田", "措施"],
    "relation_tags": [
        {"rel": "隶属", "example": "N-02 —隶属→ 渤南", "desc": "井属于哪个区块"},
        {"rel": "承载", "example": "", "desc": "井装在哪个平台上"},
        {"rel": "受效", "example": "", "desc": "劈分系数合计＝1"},
        {"rel": "作用于", "example": "", "desc": "措施做在哪口井上"},
    ],
    "few_shot_examples": [
        {"sentence": "N-02 井隶属渤南区块。", "triple": "N-02 —隶属→ 渤南"}
    ],
    "custom_instructions": "关系必须原文有依据；拿不准宁可跳过，不许创造新类型",
}


@pytest.fixture
async def client(
    tmp_path: Any,
) -> AsyncIterator[tuple[TestClient, FakeObjectStorage, StubCompleter, FakeGraphStore]]:
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "graph-api.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_kb_tables(manager.engine())
    await ensure_derivatives_tables(manager.engine())
    await ensure_audit_table(manager.engine())
    storage = FakeObjectStorage()
    completer = StubCompleter(
        answers={
            "kb.ingest.summary": "N-02 井完井报告摘要。",
            "kb.ingest.questions": "N-02 井是什么时候投产的？",
            "graph.draft": "N-02 井隶属渤南区块。\nN-02 —隶属→ 渤南",
        }
    )
    bus = InMemoryEventBus()
    kb = KbService(manager, completer, storage, eventbus=bus)
    graph = FakeGraphStore()
    derivatives = DerivativesService(manager, completer, kb, None, graph=graph)
    test_app = FastAPI()
    install_error_handlers(test_app)
    test_app.include_router(kb_router)
    test_app.include_router(graph_router)
    test_app.include_router(security_router)  # B12 审计读面（断言消费）
    test_app.dependency_overrides[get_kb] = lambda: kb
    test_app.dependency_overrides[get_derivatives] = lambda: derivatives
    test_app.dependency_overrides[get_security] = lambda: SecurityService(manager)
    with TestClient(test_app) as test_client:
        yield test_client, storage, completer, graph
    await manager.dispose()


def _make_lib(c: TestClient, storage: FakeObjectStorage) -> str:
    """建库（graph 开）→受理→直传→confirm（graph 支路事件不抽——图存储为桩
    且 LLM 桩无 graph.extract 应答 → 抽取为空操作；本文件只测端点形状）。"""
    lib = c.post(
        "/api/kb/libs",
        json={"lib_name": "完井报告库·图", "biz_template": "completion"},
    )
    assert lib.status_code == 201, lib.text
    lib_id = lib.json()["lib_id"]
    up = c.post(
        "/api/kb/uploads",
        json={"filename": "N-02 井完井报告·图.txt",
              "size": len(DEMO_TEXT.encode("utf-8")), "lib_id": lib_id},
    )
    receipt = up.json()
    storage.objects[receipt["put_url"].split("/put/")[1]] = DEMO_TEXT.encode("utf-8")
    confirm = c.post(f"/api/kb/uploads/{receipt['upload_id']}/confirm")
    assert confirm.status_code == 200, confirm.text
    return lib_id


class TestGraphApi:
    def test_401_bad_actor(self, client: Any) -> None:
        c = client[0]
        resp = c.get("/api/graph/net", params={"lib_id": "lib-x"},
                     headers={"X-Dev-User": "ghost"})
        assert resp.status_code == 401
        assert resp.json()["code"] == "security_unauthenticated"

    def test_net_empty_then_404(self, client: Any) -> None:
        c, storage, _completer, _g = client
        lib_id = _make_lib(c, storage)
        # completion 模板缺省 graph 开——整图空（图存储桩无数据）
        net = c.get("/api/graph/net", params={"lib_id": lib_id}).json()
        assert net["lib_id"] == lib_id and net["lib_name"] == "完井报告库·图"
        assert net["nodes"] == [] and net["edges"] == [] and net["legend"] == []
        assert net["stats"] == {"nodes": 0, "edges": 0}
        # 库不存在 404（错误码草案：端点 1/2/3/4 同）
        resp = c.get("/api/graph/net", params={"lib_id": "lib-none"})
        assert resp.status_code == 404
        assert resp.json()["code"] == "graph_not_found"
        # lib_id 缺参 → 400（00 §3.2 请求没进门）
        assert c.get("/api/graph/net").status_code == 400

    def test_extract_config_default_and_save_roundtrip(self, client: Any) -> None:
        c, storage, _completer, _g = client
        lib_id = _make_lib(c, storage)
        # 未保存过 → 出厂默认（本体对号表投影——差异登记）
        default = c.get("/api/graph/extract-config",
                        params={"lib_id": lib_id}).json()
        assert default["lib_id"] == lib_id
        assert "井" in default["entity_types"]
        assert [t["rel"] for t in default["relation_tags"]] == [
            "隶属", "承载", "受效", "作用于", "取样自",
        ]
        assert default["saved_at"] is None and default["saved_by"] is None
        # 保存（对号强校通过）→ hint 服务端返回 → 读回含轻量审计两字段
        body = {"lib_id": lib_id, **SAVED_CONFIG}
        saved = c.put("/api/graph/extract-config", json=body)
        assert saved.status_code == 200, saved.text
        receipt = saved.json()
        assert receipt["lib_id"] == lib_id
        assert receipt["hint"] == "已保存——设置在下次入库时生效。"
        assert receipt["saved_by"]  # who 服务端解析（身份桩缺省 aqiang）
        view = c.get("/api/graph/extract-config", params={"lib_id": lib_id}).json()
        assert view["entity_types"] == SAVED_CONFIG["entity_types"]
        assert view["relation_tags"][0]["example"] == "N-02 —隶属→ 渤南"
        assert view["few_shot_examples"] == SAVED_CONFIG["few_shot_examples"]
        assert view["saved_at"] == receipt["saved_at"]
        # B12 平台审计留痕（api 层编排——P0-05 同款）
        audit = c.get("/api/security/audit-logs").json()
        assert any(a["action"] == "graph.extract_config.saved" for a in audit["items"])

    def test_save_strong_check_rejects_with_mismatch_detail(self, client: Any) -> None:
        c, storage, _completer, _g = client
        lib_id = _make_lib(c, storage)
        resp = c.put("/api/graph/extract-config", json={
            "lib_id": lib_id,
            "entity_types": ["井", "机灵鬼"],
            "relation_tags": [{"rel": "管辖着", "example": "", "desc": ""}],
            "custom_instructions": "",
        })
        assert resp.status_code == 400, resp.text
        body = resp.json()
        assert body["code"] == "graph_ontology_mismatch"
        mismatches = body["detail"]["mismatches"]
        values = {m["value"]: m["kind"] for m in mismatches}
        assert values == {"机灵鬼": "entity_type", "管辖着": "relation_tag"}
        assert all(m["nearest"] for m in mismatches)  # 最接近台账词条逐项带出

    def test_save_shape_validation_400s(self, client: Any) -> None:
        c, storage, _completer, _g = client
        lib_id = _make_lib(c, storage)
        # entity_types 空
        resp = c.put("/api/graph/extract-config", json={
            "lib_id": lib_id, "entity_types": [], "relation_tags": [],
            "custom_instructions": "",
        })
        assert resp.status_code == 400
        assert resp.json()["code"] == "graph_param_invalid"
        # relation_tags 重复 rel
        resp = c.put("/api/graph/extract-config", json={
            "lib_id": lib_id, "entity_types": ["井"],
            "relation_tags": [{"rel": "隶属"}, {"rel": "隶属"}],
            "custom_instructions": "",
        })
        assert resp.status_code == 400
        assert "重复" in resp.json()["message"]

    def test_draft_example_endpoint(self, client: Any) -> None:
        c, storage, completer, _g = client
        lib_id = _make_lib(c, storage)
        resp = c.post("/api/graph/extract-config/draft-example",
                      json={"lib_id": lib_id, "rel": "隶属"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["sentence"] and body["triple"] == "N-02 —隶属→ 渤南"
        # 起草走真 complete 出口（caller=graph.draft——B6 统一出口）
        assert any(caller == "graph.draft" for caller, _ in completer.calls)

    def test_blocked_edges_endpoint(self, client: Any) -> None:
        c, storage, _completer, graph = client
        lib_id = _make_lib(c, storage)
        # 拦边留痕（图存储桩内存直写——管线落库面在域单测/Neo4j 集成覆盖）
        graph.blocked[(lib_id, "化验样 H-01|取样自|N-02", "rpt-017")] = {
            "key": "化验样 H-01|取样自|N-02", "from": "化验样 H-01",
            "from_type": "化验样", "rel": "取样自", "to": "N-02", "to_type": "井",
            "reason_code": "type_mismatch",
            "reason": "关系标签「取样自」不在该库抽取配置 relation_tags 清单内"
                      "（类型闸拦下）",
            "report_id": "rpt-017", "report_title": "N-02 井完井报告",
            "chunk_id": "chk-0173", "blocked_at": "2026-10-01 10:12",
        }
        page = c.get("/api/graph/blocked-edges", params={"lib_id": lib_id}).json()
        assert page["lib_id"] == lib_id and page["lib_name"] == "完井报告库·图"
        assert page["stats"] == {"blocked": 1}
        row = page["blocked_edges"][0]
        # 端点 4 DTO 逐字段（B5 合同：key/from/from_type/rel/to/to_type/
        # reason_code/reason/report_id/report_title/chunk_id/blocked_at）
        assert row["key"] == "化验样 H-01|取样自|N-02"
        assert row["from"] == "化验样 H-01" and row["to"] == "N-02"
        assert row["reason_code"] == "type_mismatch" and "类型闸" in row["reason"]
        assert row["report_id"] == "rpt-017"
        assert row["report_title"] == "N-02 井完井报告"
        assert row["chunk_id"] == "chk-0173" and row["blocked_at"]
        # namespace 隔离＋库不存在 404
        assert c.get("/api/graph/blocked-edges",
                     params={"lib_id": "lib-none"}).status_code == 404
