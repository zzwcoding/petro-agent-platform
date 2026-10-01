"""B4 /api/wiki 路由族 API 测试——四条路由全往返：目录/全文 ?version=N/版本列表/回滚。

装配：sqlite 底座＋真实 KbService＋DerivativesService＋桩 LLM（dependency_
overrides 替换服务定位，不触 main.py lifespan；红线：任何测试不得真实调用
MiniMax/GLM 端点）。
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_derivatives, get_kb, get_security
from app.api.errors import install_error_handlers
from app.api.kb import router as kb_router
from app.api.security import router as security_router
from app.api.wiki import router as wiki_router
from app.domains.derivatives import DerivativesService
from app.domains.derivatives.domain import WIKI_END_MARKER
from app.domains.derivatives.store import ensure_derivatives_tables
from app.domains.kb import KbService
from app.domains.kb.store import ensure_kb_tables
from app.domains.security import SecurityService
from app.domains.security.store import ensure_audit_table
from app.infra.db import ConnectionManager, DatabaseSpec
from app.infra.eventbus import InMemoryEventBus
from tests.domains.derivatives.conftest import (
    GLOSSARY_METRICS,
    GLOSSARY_TERMS,
    WIKI_STUB_ANSWER,
    FakeSemantics,
)
from tests.domains.kb.conftest import FakeObjectStorage, StubCompleter

DEMO_TEXT = (
    "N-02 井完井报告\n1 基本情况\nN-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，"
    "井别采油（EW），2019-06-15 投产。\n2 完井段\n完井段详见参数表，"
    "防砂方式筛管完井。\n"
)


@pytest.fixture
async def client(
    tmp_path: Any,
) -> AsyncIterator[tuple[TestClient, FakeObjectStorage, StubCompleter]]:
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "wiki-api.db"), user="", password="",
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
            "wiki.gen": WIKI_STUB_ANSWER,
        }
    )
    bus = InMemoryEventBus()
    kb = KbService(manager, completer, storage, eventbus=bus)
    derivatives = DerivativesService(
        manager, completer, kb,
        FakeSemantics(GLOSSARY_TERMS, GLOSSARY_METRICS),
    )
    await bus.subscribe("IngestCompleted", derivatives.on_ingest_completed)
    await bus.subscribe("FragmentRevised", derivatives.on_fragment_revised)
    test_app = FastAPI()
    install_error_handlers(test_app)
    test_app.include_router(kb_router)
    test_app.include_router(wiki_router)
    test_app.include_router(security_router)  # B12 审计读面（补齐断言消费）
    test_app.dependency_overrides[get_kb] = lambda: kb
    test_app.dependency_overrides[get_derivatives] = lambda: derivatives
    test_app.dependency_overrides[get_security] = lambda: SecurityService(manager)
    with TestClient(test_app) as test_client:
        yield test_client, storage, completer
    await manager.dispose()


def _wait_done(c: TestClient, task_id: str, attempts: int = 200) -> dict[str, Any]:
    import time

    for _ in range(attempts):
        body = c.get(f"/api/kb/tasks/{task_id}").json()
        if body["state"] in ("done", "failed"):
            return body
        time.sleep(0.02)
    raise TimeoutError("任务未在超时内终态")


def _make_page(c: TestClient, storage: FakeObjectStorage) -> dict[str, Any]:
    """建库→直传→confirm→五步 done→wiki v1 落库；返回 {lib_id, report_id}。"""
    lib = c.post(
        "/api/kb/libs",
        json={"lib_name": "完井报告库·wiki", "biz_template": "completion"},
    )
    assert lib.status_code == 201, lib.text
    lib_id = lib.json()["lib_id"]
    up = c.post(
        "/api/kb/uploads",
        json={"filename": "N-02 井完井报告·wiki.txt",
              "size": len(DEMO_TEXT.encode("utf-8")), "lib_id": lib_id},
    )
    assert up.status_code == 200, up.text
    receipt = up.json()
    storage.objects[receipt["put_url"].split("/put/")[1]] = DEMO_TEXT.encode("utf-8")
    confirm = c.post(f"/api/kb/uploads/{receipt['upload_id']}/confirm")
    assert confirm.status_code == 200, confirm.text
    _wait_done(c, confirm.json()["task_id"])
    reports = c.get("/api/kb/reports", params={"keyword": "wiki"}).json()
    assert reports["total"] == 1
    report_id = reports["items"][0]["id"]
    page_id = f"wiki-{report_id.removeprefix('rpt-')}"
    for _ in range(200):
        resp = c.get(f"/api/wiki/pages/{page_id}")
        if resp.status_code == 200:
            return {"lib_id": lib_id, "report_id": report_id, "page_id": page_id}
        import time

        time.sleep(0.02)
    raise TimeoutError("wiki 页未在超时内生成")


def _make_second_version(
    c: TestClient, made: dict[str, Any], completer: StubCompleter
) -> None:
    """片段修正→FragmentRevised→重铸→wiki v2（联动真跑；换稿避免与 v1 逐字相同）。"""
    completer.answers["wiki.gen"] = (
        "## 概述（修正重铸版）\n\n正文第二版，含勘误注记。[[claim:f1]]\n"
        f"{WIKI_END_MARKER}\n"
    )
    report_id = made["report_id"]
    detail = c.get(f"/api/kb/reports/{report_id}").json()
    frag = detail["fragments"][0]
    resp = c.post(
        f"/api/kb/reports/{report_id}/fragments/{frag['id']}/revisions",
        json={"base_version": frag["version"], "text": frag["text"] + "（勘误）"},
    )
    assert resp.status_code == 200, resp.text
    import time

    for _ in range(200):
        versions = c.get(f"/api/wiki/pages/{made['page_id']}/versions").json()
        if versions["total"] >= 2:
            return
        time.sleep(0.05)
    raise TimeoutError("重铸版本未在超时内追加")


class TestWikiReadFaces:
    def test_401_bad_actor(self, client: Any) -> None:
        c = client[0]
        resp = c.get("/api/wiki/pages", headers={"X-Dev-User": "ghost"})
        assert resp.status_code == 401
        assert resp.json()["code"] == "security_unauthenticated"

    def test_1_directory_empty_and_after_generation(self, client: Any) -> None:
        c, storage, _completer = client
        empty = c.get("/api/wiki/pages").json()
        assert empty == {"items": [], "total": 0}
        made = _make_page(c, storage)
        listing = c.get("/api/wiki/pages").json()
        assert listing["total"] == 1
        row = listing["items"][0]
        assert row["id"] == made["page_id"]
        assert row["title"] == "《N-02 井完井报告·wiki》"
        assert row["lib"] == "完井报告库·wiki"
        assert row["source_report"]["id"] == made["report_id"]
        assert row["current_version"] == 1 and row["version_count"] == 1
        assert row["status"] == "正常"  # 无 [[flag:]] → 正常
        # 筛选：所属库命中/关键词命中/不命中
        assert c.get("/api/wiki/pages", params={"lib": "完井报告库·wiki"}).json()["total"] == 1
        assert c.get("/api/wiki/pages", params={"keyword": "N-02"}).json()["total"] == 1
        assert c.get("/api/wiki/pages", params={"keyword": "不命中"}).json()["total"] == 0
        # B1 台账 wiki 字段同源同值
        reports = c.get("/api/kb/reports", params={"keyword": "wiki"}).json()
        assert reports["items"][0]["wiki"] == "v1"

    def test_2_page_detail_dto_and_version_snapshot(self, client: Any) -> None:
        c, storage, _completer = client
        made = _make_page(c, storage)
        detail = c.get(f"/api/wiki/pages/{made['page_id']}").json()
        # 元数据字段表（B4 端点 2）
        assert detail["slug"] == detail["id"] == made["page_id"]
        assert detail["source_report"]["id"] == made["report_id"]
        assert detail["generation_source"] == "自动重建"
        assert detail["operator"] == "系统（入库管线）"
        assert detail["digest"]
        assert detail["status"] == "正常"
        # content＝自由 markdown 全文；claims fail-closed；glossary 固化投影
        assert WIKI_END_MARKER not in detail["content"]
        assert "[[claim:f999]]" not in detail["content"]
        assert detail["claims"] and all(c["evidence_chunk_ids"] for c in detail["claims"])
        words = {g["word"]: g for g in detail["glossary_terms"]}
        assert "综合含水率" in words and words["综合含水率"]["ref_id"] == 5
        # ?version=1 与不带参数同版同形；404：未知页/未知版本
        v1 = c.get(f"/api/wiki/pages/{made['page_id']}", params={"version": 1}).json()
        assert v1["content"] == detail["content"]
        assert c.get("/api/wiki/pages/wiki-none").status_code == 404
        assert c.get("/api/wiki/pages/wiki-none").json()["code"] == "wiki_not_found"
        assert c.get(
            f"/api/wiki/pages/{made['page_id']}", params={"version": 99}
        ).status_code == 404


class TestWikiVersionsAndRollback:
    def test_3_version_list(self, client: Any) -> None:
        c, storage, _completer = client
        made = _make_page(c, storage)
        versions = c.get(f"/api/wiki/pages/{made['page_id']}/versions").json()
        assert versions["total"] == 1
        row = versions["items"][0]
        assert row["v"] == 1 and row["current"] is True
        assert row["source"] == "自动重建"
        assert row["operator"] == "系统（入库管线）"
        assert row["task_no"] and row["task_no"].startswith("task-")
        assert row["desc"] == "首次生成（报告入库自动建页）"
        assert c.get("/api/wiki/pages/wiki-none/versions").status_code == 404

    def test_4_rollback_roundtrip(self, client: Any) -> None:
        c, storage, completer = client
        made = _make_page(c, storage)
        page_id = made["page_id"]
        _make_second_version(c, made, completer)  # v2＝片段修正重铸联动真跑
        # 404：页面不存在/目标版不存在；400：target_version 等于当前版
        assert c.post("/api/wiki/pages/wiki-none/rollback",
                      json={"target_version": 1}).status_code == 404
        assert c.post(f"/api/wiki/pages/{page_id}/rollback",
                      json={"target_version": 99}).status_code == 404
        assert c.post(f"/api/wiki/pages/{page_id}/rollback",
                      json={"target_version": 2}).status_code == 400
        # 回滚成功＝追加「回滚」来源新版本（指针前进）
        resp = c.post(f"/api/wiki/pages/{page_id}/rollback",
                      json={"target_version": 1})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["page_id"] == page_id
        assert body["current_version"] == 3
        assert body["new_version"]["source"] == "回滚"
        assert body["new_version"]["operator"]  # who 服务端解析
        assert body["new_version"]["task_no"] is None  # 回滚无经由单号
        assert "内容恢复自 v1" in body["banner"]
        assert body["status"] == "正常"
        versions = c.get(f"/api/wiki/pages/{page_id}/versions").json()
        assert [v["v"] for v in versions["items"]] == [1, 2, 3]
        assert versions["items"][2]["current"] is True
        # 防呆 409：目标版内容与当前版逐字相同（v3 即 v1 快照，再滚 v1）
        guard = c.post(f"/api/wiki/pages/{page_id}/rollback",
                       json={"target_version": 1})
        assert guard.status_code == 409
        assert "回滚" in guard.json()["message"]
        # 目录状态随当前版派生；B12 审计留痕
        assert c.get("/api/wiki/pages").json()["items"][0]["current_version"] == 3
        audit = c.get("/api/security/audit-logs").json()
        assert any(a["action"] == "wiki.page.rolled_back" for a in audit["items"])
