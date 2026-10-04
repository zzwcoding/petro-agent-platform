"""B4 /api/wiki 路由族 API 测试——v0.4 两读端点全往返：目录/全文（恒当前版）。

装配：sqlite 底座＋真实 KbService＋DerivativesService＋桩 LLM（dependency_
overrides 替换服务定位，不触 main.py lifespan；红线：任何测试不得真实调用
MiniMax/GLM 端点）。B4 v0.4（Owner 2026-10-04 拍板）：端点 3/4 删端、
?version=N 撤除、DTO 撤 version_count——版本/回滚族测试随撤除移除。
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
    test_app.include_router(security_router)
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


def _make_lib(
    c: TestClient, *, wiki: bool, name: str = "完井报告库·wiki"
) -> str:
    """建库＋按需落库配置（wiki 开关关→该库报告无百科页）；返回 lib_id。"""
    lib = c.post("/api/kb/libs", json={"lib_name": name, "biz_template": "completion"})
    assert lib.status_code == 201, lib.text
    lib_id = lib.json()["lib_id"]
    if not wiki:
        saved = c.put(
            f"/api/kb/libs/{lib_id}/config",
            json={"switches": {"semantic": True, "keyword": True, "wiki": False,
                               "graph": False},
                  "mode": "fixed", "add_summary": True, "add_questions": True},
        )
        assert saved.status_code == 200, saved.text
    return lib_id


def _make_page(
    c: TestClient, storage: FakeObjectStorage, *, wiki: bool = True,
    tag: str = "wiki", well: str = "N-02",
) -> dict[str, Any]:
    """建库→直传→confirm→五步 done→（wiki 开→百科 v1 落库）；返回标识组。

    tag/well 供多页用例分库分题名（lib＝完井报告库·{tag}、文件名＝{well} 井
    完井报告·{tag}.txt）——台账反查按 tag 收敛到本页报告。
    """
    lib_id = _make_lib(c, wiki=wiki, name=f"完井报告库·{tag}")
    up = c.post(
        "/api/kb/uploads",
        json={"filename": f"{well} 井完井报告·{tag}.txt",
              "size": len(DEMO_TEXT.encode("utf-8")), "lib_id": lib_id},
    )
    assert up.status_code == 200, up.text
    receipt = up.json()
    storage.objects[receipt["put_url"].split("/put/")[1]] = DEMO_TEXT.encode("utf-8")
    confirm = c.post(f"/api/kb/uploads/{receipt['upload_id']}/confirm")
    assert confirm.status_code == 200, confirm.text
    _wait_done(c, confirm.json()["task_id"])
    reports = c.get("/api/kb/reports", params={"keyword": tag}).json()
    assert reports["total"] == 1
    report_id = reports["items"][0]["id"]
    page_id = f"wiki-{report_id.removeprefix('rpt-')}"
    if not wiki:
        return {"lib_id": lib_id, "report_id": report_id, "page_id": page_id}
    for _ in range(200):
        resp = c.get(f"/api/wiki/pages/{page_id}")
        if resp.status_code == 200:
            return {"lib_id": lib_id, "report_id": report_id, "page_id": page_id}
        import time

        time.sleep(0.02)
    raise TimeoutError("wiki 页未在超时内生成")


def _recast_second_version(
    c: TestClient,
    made: dict[str, Any],
    completer: StubCompleter,
    *,
    stub_answer: str,
) -> None:
    """片段修正→FragmentRevised→重铸→覆盖当前版（重建计数 2；换稿避免与
    v1 逐字相同）。"""
    completer.answers["wiki.gen"] = stub_answer
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
        body = c.get(f"/api/wiki/pages/{made['page_id']}").json()
        if body.get("current_version", 0) >= 2:
            return
        time.sleep(0.05)
    raise TimeoutError("重铸未在超时内覆盖当前版")


class TestWikiReadFaces:
    def test_401_bad_actor(self, client: Any) -> None:
        c = client[0]
        resp = c.get("/api/wiki/pages", headers={"X-Dev-User": "ghost"})
        assert resp.status_code == 401
        assert resp.json()["code"] == "security_unauthenticated"

    def test_1_directory_empty_filter_and_dto(self, client: Any) -> None:
        """(b) 目录：空态/筛选（lib/keyword/status 服务端算）/DTO 无 version_count。"""
        c, storage, _completer = client
        empty = c.get("/api/wiki/pages").json()
        assert empty == {"items": [], "total": 0}
        made = _make_page(c, storage)
        listing = c.get("/api/wiki/pages").json()
        assert listing["total"] == 1
        row = listing["items"][0]
        # DTO 逐字段（B4 v0.4 端点 1）：撤 version_count
        assert set(row) == {
            "id", "title", "lib", "source_report",
            "current_version", "updated", "status",
        }
        assert set(row["source_report"]) == {"id", "doc"}
        assert row["id"] == made["page_id"]
        assert row["title"] == "《N-02 井完井报告·wiki》"
        assert row["lib"] == "完井报告库·wiki"
        assert row["source_report"]["id"] == made["report_id"]
        assert row["current_version"] == 1
        assert row["updated"]
        assert row["status"] == "正常"  # 无 [[flag:]] → 正常（服务端判定）
        # 筛选：所属库命中/关键词命中（题名/来源报告/所属库三字段模糊）/不命中
        #   ——筛选效果看 items；total 恒＝全量计数（B4 v0.4 注记，F2 修复拍）
        hit_lib = c.get("/api/wiki/pages", params={"lib": "完井报告库·wiki"}).json()
        assert len(hit_lib["items"]) == 1 and hit_lib["total"] == 1
        miss_lib = c.get("/api/wiki/pages", params={"lib": "不存在的库"}).json()
        assert miss_lib["items"] == [] and miss_lib["total"] == 1  # total 不随筛选缩
        assert len(c.get("/api/wiki/pages", params={"keyword": "N-02"}).json()["items"]) == 1
        assert len(c.get("/api/wiki/pages",
                         params={"keyword": "完井报告"}).json()["items"]) == 1
        miss_kw = c.get("/api/wiki/pages", params={"keyword": "不命中"}).json()
        assert miss_kw["items"] == [] and miss_kw["total"] == 1
        # B1 台账 wiki 字段同源同值（v0.4＝重建计数）
        reports = c.get("/api/kb/reports", params={"keyword": "wiki"}).json()
        assert reports["items"][0]["wiki"] == "v1"

    def test_1b_total_is_full_count_under_filter(self, client: Any) -> None:
        """F2（修复拍）：total＝全量计数——B4 v0.4 端点 1 DTO 注记「total＝
        全量计数；『筛选结果 X / Y 条』＝前端按 items 长度＋total 拼」。
        筛选态 total≠len(items) 且＝未筛选全量。"""
        c, storage, _completer = client
        made_a = _make_page(c, storage, tag="wikiA")
        made_b = _make_page(c, storage, tag="wikiB", well="N-03")
        full = c.get("/api/wiki/pages").json()
        assert len(full["items"]) == full["total"] == 2
        # lib 筛选：items 只余 A 库页，total 仍＝未筛选全量（≠len(items)）
        lib_view = c.get(
            "/api/wiki/pages", params={"lib": "完井报告库·wikiA"}
        ).json()
        assert [r["id"] for r in lib_view["items"]] == [made_a["page_id"]]
        assert len(lib_view["items"]) == 1
        assert lib_view["total"] == 2
        assert lib_view["total"] != len(lib_view["items"])
        # keyword 筛选：只命中 B 页题名，total 仍＝未筛选全量
        kw_view = c.get("/api/wiki/pages", params={"keyword": "N-03"}).json()
        assert [r["id"] for r in kw_view["items"]] == [made_b["page_id"]]
        assert kw_view["total"] == 2
        assert kw_view["total"] != len(kw_view["items"])

    def test_2_page_detail_full_dto_and_flag_status(self, client: Any) -> None:
        """(c) 全文：DTO 逐字段（元数据表＋content＋claims＋glossary）＋
        flag→status 两态（重铸覆盖后翻状态）。"""
        c, storage, completer = client
        made = _make_page(c, storage)
        detail = c.get(f"/api/wiki/pages/{made['page_id']}").json()
        # DTO 逐字段（B4 v0.4 端点 2）：撤 version_count；无 ?version 读法
        assert set(detail) == {
            "id", "title", "lib", "slug", "digest", "source_report",
            "current_version", "updated", "status", "generation_source",
            "operator", "related_objects", "content", "claims", "glossary_terms",
        }
        assert detail["slug"] == detail["id"] == made["page_id"]
        assert detail["source_report"]["id"] == made["report_id"]
        assert detail["generation_source"] == "自动重建"
        assert detail["operator"] == "系统（入库管线）"
        assert detail["digest"]
        assert detail["current_version"] == 1
        assert detail["status"] == "正常"
        # content＝自由 markdown 全文；claims fail-closed；glossary 固化投影
        assert WIKI_END_MARKER not in detail["content"]
        assert "[[claim:f999]]" not in detail["content"]
        assert detail["claims"] and all(c["evidence_chunk_ids"] for c in detail["claims"])
        assert set(detail["claims"][0]) == {"claim_id", "text", "evidence_chunk_ids"}
        words = {g["word"]: g for g in detail["glossary_terms"]}
        assert "综合含水率" in words and words["综合含水率"]["ref_id"] == 5
        assert set(next(iter(words.values()))) == {"word", "kind", "ref_id", "card"}
        # flag→状态两态：重铸覆盖当前版（正文携 [[flag:]]）→ 字段待核对
        _recast_second_version(
            c, made, completer,
            stub_answer=(
                "## 概述（修正重铸版）\n\n平台 CEP-B[[flag:与井档案不符，待核对]]"
                "与井档案不符。[[claim:f1]]\n"
                f"{WIKI_END_MARKER}\n"
            ),
        )
        v2 = c.get(f"/api/wiki/pages/{made['page_id']}").json()
        assert v2["current_version"] == 2  # 重建计数（覆盖非追加）
        assert "[[flag:与井档案不符，待核对]]" in v2["content"]
        assert v2["status"] == "字段待核对"
        assert v2["claims"][0]["claim_id"]
        # 目录状态同源翻状态（服务端按当前版判定）
        row = c.get("/api/wiki/pages").json()["items"][0]
        assert row["status"] == "字段待核对" and row["current_version"] == 2
        # B1 台账 wiki 字段同步 v2（同源同值）
        reports = c.get("/api/kb/reports", params={"keyword": "wiki"}).json()
        assert reports["items"][0]["wiki"] == "v2"

    def test_2b_removed_version_and_rollback_routes_are_gone(
        self, client: Any
    ) -> None:
        """v0.4 撤除面：端点 3/4 路由不存在（404 路由级），?version=N 参数撤除。"""
        c, storage, _completer = client
        made = _make_page(c, storage)
        assert c.get(f"/api/wiki/pages/{made['page_id']}/versions").status_code == 404
        assert c.post(
            f"/api/wiki/pages/{made['page_id']}/rollback",
            json={"target_version": 1},
        ).status_code == 404

    def test_404_unknown_id_and_wiki_switch_off(self, client: Any) -> None:
        """(d) 404：直调未知 id／wiki 开关关未生成（错误码 wiki_not_found）。"""
        c, storage, _completer = client
        missing = c.get("/api/wiki/pages/wiki-none")
        assert missing.status_code == 404
        assert missing.json()["code"] == "wiki_not_found"
        off = _make_page(c, storage, wiki=False)  # wiki 开关关→不生成
        assert c.get("/api/wiki/pages").json()["total"] == 0  # 目录不出现
        resp = c.get(f"/api/wiki/pages/{off['page_id']}")
        assert resp.status_code == 404
        assert resp.json()["code"] == "wiki_not_found"
