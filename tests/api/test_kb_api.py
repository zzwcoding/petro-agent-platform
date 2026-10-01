"""B1 路由族 API 测试——15 条 HTTP 路由全往返：形状/错误包/身份闸/两拍。

装配：sqlite 底座＋假对象存储＋桩 LLM（dependency_overrides 替换服务定位，
不触 main.py lifespan；红线：任何测试不得真实调用 MiniMax/GLM 端点）。
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_kb, get_security
from app.api.errors import install_error_handlers
from app.api.kb import router as kb_router
from app.api.security import router as security_router
from app.domains.kb import KbService

DEMO_TEXT = (
    "N-02 井完井报告\n1 基本情况\nN-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，"
    "2019-06-15 投产。\n2 完井段\n完井段详见参数表。\n"
)

class FakeObjectStorage:
    """内存对象存储（presign 登记待传 key——对象落桶由测试显式写 objects）。"""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.signed: list[str] = []

    async def put(self, key: str, data: bytes) -> None:
        self.objects[key] = data

    async def presign_put(self, key: str, *, ttl_seconds: int = 1800) -> str:
        self.signed.append(key)
        return f"https://minio.test/put/{key}"

    async def presign_get(self, key: str, *, ttl_seconds: int = 3600) -> str:
        return f"https://minio.test/get/{key}"

    async def exists(self, key: str) -> bool:
        return key in self.objects

    async def get_bytes(self, key: str) -> bytes:
        if key not in self.objects:
            raise KeyError(key)
        return self.objects[key]


class StubCompleter:
    """桩 LLM：按 caller 脚本应答；记录调用序（B6 断言用）。"""

    def __init__(
        self, answers: dict[str, str | Exception] | None = None, default: str = "应答"
    ) -> None:
        self.answers = answers or {}
        self.default = default
        self.calls: list[tuple[str, str]] = []

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any:
        from app.domains.gateway import Completion

        content = messages[-1]["content"]
        self.calls.append((caller, content))
        answer: str | Exception = self.answers.get(caller, self.default)
        if isinstance(answer, Exception):
            raise answer
        return Completion(
            content=answer, prompt_tokens=10, completion_tokens=5,
            usage_estimated=False, call_id="call-stub", cost_yuan=0.0001,
            fallback=False, served_alias=alias,
        )


ROUTE_ANSWER = (
    '{"mode": "existing", "lib_name": "完井报告库", "reason": "完井话题", "confidence": 0.9}'
)


@pytest.fixture
async def client(
    tmp_path: Any,
) -> AsyncIterator[tuple[TestClient, FakeObjectStorage, StubCompleter]]:
    from app.domains.kb.store import ensure_kb_tables
    from app.domains.security import SecurityService
    from app.domains.security.store import ensure_audit_table
    from app.infra.db import ConnectionManager, DatabaseSpec
    from app.infra.eventbus import InMemoryEventBus

    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "kb-api.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_kb_tables(manager.engine())
    await ensure_audit_table(manager.engine())  # B12 审计表（api 层写口）
    storage = FakeObjectStorage()
    completer = StubCompleter(
        answers={
            "kb.ingest.summary": "N-02 井完井报告摘要。",
            "kb.ingest.questions": "N-02 井是什么时候投产的？",
            "kb.route": ROUTE_ANSWER,
        }
    )
    service = KbService(manager, completer, storage, eventbus=InMemoryEventBus())
    test_app = FastAPI()
    install_error_handlers(test_app)
    test_app.include_router(kb_router)
    test_app.include_router(security_router)  # B12 审计读面（补齐断言消费）
    test_app.dependency_overrides[get_kb] = lambda: service
    test_app.dependency_overrides[get_security] = lambda: SecurityService(manager)
    with TestClient(test_app) as test_client:
        yield test_client, storage, completer
    await manager.dispose()


def _make_lib(client: TestClient, name: str = "完井报告库", template: str = "completion") -> str:
    resp = client.post("/api/kb/libs", json={"lib_name": name, "biz_template": template})
    assert resp.status_code == 201, resp.text
    return resp.json()["lib_id"]


def _ingest(
    client: TestClient, storage: FakeObjectStorage, lib_id: str,
    filename: str = "N-02 井完井报告.pdf", content: bytes = DEMO_TEXT.encode("utf-8"),
) -> str:
    up = client.post(
        "/api/kb/uploads",
        json={"filename": filename, "size": len(content), "lib_id": lib_id},
    )
    assert up.status_code == 200, up.text
    upload_id = up.json()["upload_id"]
    key = storage.signed[-1]
    storage.objects[key] = content
    confirm = client.post(f"/api/kb/uploads/{upload_id}/confirm")
    assert confirm.status_code == 200, confirm.text
    return confirm.json()["task_id"]


def _wait_done(client: TestClient, task_id: str, attempts: int = 200) -> dict[str, Any]:
    import time

    for _ in range(attempts):
        body = client.get(f"/api/kb/tasks/{task_id}").json()
        if body["state"] in ("done", "failed"):
            return body
        time.sleep(0.02)
    raise TimeoutError("任务未在超时内终态")


class TestLibraryEndpoints:
    def test_15_create_lib_201(self, client: Any) -> None:
        c = client[0]
        resp = c.post("/api/kb/libs", json={"lib_name": "措施库", "biz_template": "completion"})
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "active"
        assert body["config"]["graph"] is True
        assert body["activity_row"]["action"] == "新建库"

    def test_15_create_lib_400_409(self, client: Any) -> None:
        c = client[0]
        assert c.post(
            "/api/kb/libs", json={"lib_name": " ", "biz_template": "completion"}
        ).status_code == 400
        assert c.post(
            "/api/kb/libs", json={"lib_name": "X", "biz_template": "wiki"}
        ).status_code == 400
        _make_lib(c)
        dup = c.post("/api/kb/libs", json={"lib_name": "完井报告库", "biz_template": "monthly"})
        assert dup.status_code == 409
        assert dup.json()["code"] == "kb_lib_name_duplicate"
        assert dup.json()["message"]  # 00 §3.1：message 人话

    def test_11_12_13_lib_config_flow(self, client: Any) -> None:
        c = client[0]
        lib_id = _make_lib(c)
        listing = c.get("/api/kb/libs").json()
        assert listing["total"] == 1 and listing["items"][0]["last_ingestion"] is None
        config = c.get(f"/api/kb/libs/{lib_id}/config").json()
        assert config["switches"]["graph"] is True and config["saved_at"] is None
        saved = c.put(
            f"/api/kb/libs/{lib_id}/config",
            json={"switches": {"semantic": True, "keyword": True, "wiki": True, "graph": False},
                  "mode": "fixed", "add_summary": True, "add_questions": True},
        )
        assert saved.status_code == 200
        assert saved.json()["hint"].startswith("已保存——")
        assert saved.json()["activity_row"]["action"] == "修改库配置"
        # 400 族：mode 越界 / switches 缺键 / status 越界
        assert c.put(f"/api/kb/libs/{lib_id}/config", json={
            "switches": {"semantic": True, "keyword": True, "wiki": True, "graph": False},
            "mode": "bad", "add_summary": True, "add_questions": True}).status_code == 400
        assert c.put(f"/api/kb/libs/{lib_id}/config", json={
            "switches": {"semantic": True}, "mode": "smart",
            "add_summary": True, "add_questions": True}).status_code == 400
        assert c.put(f"/api/kb/libs/{lib_id}/config", json={
            "switches": {"semantic": True, "keyword": True, "wiki": True, "graph": False},
            "mode": "smart", "add_summary": True, "add_questions": True,
            "status": "archived"}).status_code == 400
        # 14 活动流只读
        acts = c.get(f"/api/kb/libs/{lib_id}/activities").json()
        assert acts["total"] >= 2 and acts["items"][0]["action"] == "修改库配置"

    def test_13_disable_blocks_upload_400_with_code(self, client: Any) -> None:
        c = client[0]
        lib_id = _make_lib(c)
        saved = c.put(
            f"/api/kb/libs/{lib_id}/config",
            json={"switches": {"semantic": True, "keyword": True, "wiki": True, "graph": False},
                  "mode": "smart", "add_summary": True, "add_questions": True,
                  "status": "disabled"},
        )
        assert saved.json()["status"] == "disabled"
        listing = c.get("/api/kb/libs").json()
        assert listing["items"][0]["status"] == "disabled"
        up = c.post("/api/kb/uploads", json={"filename": "a.pdf", "size": 10, "lib_id": lib_id})
        assert up.status_code == 400
        assert up.json()["code"] == "kb_lib_disabled"
        # 启用恢复受理
        c.put(
            f"/api/kb/libs/{lib_id}/config",
            json={"switches": {"semantic": True, "keyword": True, "wiki": True, "graph": False},
                  "mode": "smart", "add_summary": True, "add_questions": True,
                  "status": "active"},
        )
        assert c.post(
            "/api/kb/uploads", json={"filename": "a.pdf", "size": 10, "lib_id": lib_id}
        ).status_code == 200


class TestUploadTaskFlow:
    def test_5_6_7_8_9_upload_to_done(self, client: Any) -> None:
        c, storage, _ = client
        lib_id = _make_lib(c)
        up = c.post(
            "/api/kb/uploads",
            json={"filename": "N-02 井完井报告.pdf", "size": 1024, "lib_id": lib_id},
        ).json()
        assert up["bucket"] == "报告原文" and up["dup_warning"] is None
        assert up["put_url"].startswith("https://minio.test/put/")
        # confirm 前未落桶 → 409
        pending_confirm = c.post(f"/api/kb/uploads/{up['upload_id']}/confirm")
        assert pending_confirm.status_code == 409
        storage.objects[up["put_url"].split("/put/")[1]] = DEMO_TEXT.encode("utf-8")
        confirm = c.post(f"/api/kb/uploads/{up['upload_id']}/confirm").json()
        assert confirm["state"] == "running" and confirm["source"] == "上传入库"
        assert set(confirm["config_snapshot"]) == {
            "semantic", "keyword", "wiki", "graph", "mode", "add_summary", "add_questions",
        }
        final = _wait_done(c, confirm["task_id"])
        assert final["state"] == "done"
        # 7 任务列表（source 筛）
        tasks = c.get("/api/kb/tasks", params={"source": "上传入库"}).json()
        assert tasks["total"] >= 1 and tasks["items"][0]["source"] == "上传入库"
        assert c.get("/api/kb/tasks", params={"source": "片段修正"}).json()["total"] == 0
        assert c.get("/api/kb/tasks", params={"source": "越界"}).status_code == 400
        # 8 轮询节点四态＋服务端说明
        assert [n["key"] for n in final["nodes"]] == ["parse", "chunk", "embed", "index", "enrich"]
        assert final["nodes"][4]["note"] is None
        # 9 产物
        adds = c.get(f"/api/kb/tasks/{confirm['task_id']}/additions").json()
        assert adds["summary"]["type"] == "摘要块"
        assert adds["questions"]["type"] == "问题块"
        # 1/2 台账与详情
        reports = c.get("/api/kb/reports").json()
        assert reports["total"] == 1 and reports["items"][0]["status"] == "已入库"
        detail = c.get(f"/api/kb/reports/{reports['items'][0]['id']}").json()
        assert detail["fragments"] and detail["fragments"][0]["versions"][0]["v"] == 1
        # 3 下载直链
        dl = c.post(f"/api/kb/reports/{reports['items'][0]['id']}/download-url")
        assert dl.status_code == 200
        assert dl.json()["ttl"] == "小时级" and dl.json()["download_url"]

    def test_10_retry_running_409_and_done_flow(self, client: Any) -> None:
        c, storage, _ = client
        lib_id = _make_lib(c)
        task_id = _ingest(c, storage, lib_id)
        _wait_done(c, task_id)
        retried = c.post(f"/api/kb/tasks/{task_id}/retry")
        assert retried.status_code == 200
        assert retried.json()["source"] == "重跑定型"
        _wait_done(c, retried.json()["id"])
        assert c.post("/api/kb/tasks/task-none/retry").status_code == 404

    def test_b12_audit_upload_confirm_download_retry(self, client: Any) -> None:
        """P1-05b 审查补齐：受理/确认/直链签发/重试四写口经 security.audit；
        confirm 失败路径不审计（未定型不记——409 后审计无 confirmed 动作）。"""
        c, storage, _ = client
        lib_id = _make_lib(c, name="审计补齐库")
        # 受理 → kb.upload.accepted
        up = c.post(
            "/api/kb/uploads",
            json={"filename": "N-02 井完井报告.pdf", "size": 1024, "lib_id": lib_id},
        )
        assert up.status_code == 200
        # confirm 失败（未落桶 409）→ 不达审计（未定型不记）
        upload_id = up.json()["upload_id"]
        failed = c.post(f"/api/kb/uploads/{upload_id}/confirm")
        assert failed.status_code == 409
        audit = c.get("/api/security/audit-logs").json()
        assert "kb.upload.confirmed" not in [i["action"] for i in audit["items"]]
        # 落桶后 confirm 成功 → kb.upload.confirmed
        storage.objects[up.json()["put_url"].split("/put/")[1]] = DEMO_TEXT.encode("utf-8")
        confirm = c.post(f"/api/kb/uploads/{upload_id}/confirm")
        assert confirm.status_code == 200
        task_id = confirm.json()["task_id"]
        # 下载直链签发（安全敏感）→ kb.download_url.issued
        _wait_done(c, task_id)
        reports = c.get("/api/kb/reports").json()
        report_id = reports["items"][0]["id"]
        assert c.post(f"/api/kb/reports/{report_id}/download-url").status_code == 200
        # 重试/重跑 → kb.task.retried
        retried = c.post(f"/api/kb/tasks/{task_id}/retry")
        assert retried.status_code == 200
        audit = c.get("/api/security/audit-logs").json()
        actions = [item["action"] for item in audit["items"]]
        assert "kb.upload.accepted" in actions
        assert "kb.upload.confirmed" in actions
        assert "kb.download_url.issued" in actions
        assert "kb.task.retried" in actions

    def test_2_3_404_envelope(self, client: Any) -> None:
        c = client[0]
        missing = c.get("/api/kb/reports/rpt-none")
        assert missing.status_code == 404
        assert missing.json()["code"] == "kb_not_found"
        assert c.post("/api/kb/reports/rpt-none/download-url").status_code == 404

    def test_1_lib_filter_400(self, client: Any) -> None:
        c = client[0]
        resp = c.get("/api/kb/reports", params={"lib": "不存在的库"})
        assert resp.status_code == 400
        assert resp.json()["code"] == "kb_param_invalid"


class TestRoutingApi:
    def test_5_suggested_topic_suggestion_then_confirm(self, client: Any) -> None:
        c, storage, _ = client
        lib_id = _make_lib(c)
        up = c.post(
            "/api/kb/uploads",
            json={"filename": "完井总结.pdf", "size": 100, "suggested_topic": "完井投产"},
        ).json()
        assert up["routing"]["mode"] == "existing"
        assert up["routing"]["lib_id"] == lib_id
        storage.objects[up["put_url"].split("/put/")[1]] = DEMO_TEXT.encode("utf-8")
        confirm = c.post(f"/api/kb/uploads/{up['upload_id']}/confirm")
        assert confirm.status_code == 200
        assert confirm.json()["lib_id"] == lib_id


class TestAuthAndShell:
    def test_401_bad_actor(self, client: Any) -> None:
        c = client[0]
        resp = c.get("/api/kb/libs", headers={"X-Dev-User": "hacker"})
        assert resp.status_code == 401
        assert resp.json()["code"] == "security_unauthenticated"

    def test_default_actor_aqiang(self, client: Any) -> None:
        c = client[0]
        resp = c.get("/api/kb/libs")  # 缺头→默认角色
        assert resp.status_code == 200


class TestFragmentRevision:
    """端点 4（P1-02b 激活）：乐观锁＋记版＋重建折算任务＋B12 审计。"""

    def _make_report(self, client: Any) -> str:
        c, storage, _ = client
        lib_id = _make_lib(c, name="修正库")
        task_id = _ingest(c, storage, lib_id)
        _wait_done(c, task_id)
        reports = c.get("/api/kb/reports", params={"keyword": "修正库"}).json()
        assert reports["total"] == 1
        return reports["items"][0]["id"]

    def test_4_revise_optimistic_lock_and_validation(self, client: Any) -> None:
        c = client[0]
        report_id = self._make_report(client)
        detail = c.get(f"/api/kb/reports/{report_id}").json()
        frag = detail["fragments"][0]
        # 404：报告/片段不存在
        assert c.post(
            "/api/kb/reports/rpt-none/fragments/f1/revisions",
            json={"base_version": 1, "text": "x"},
        ).status_code == 404
        assert c.post(
            f"/api/kb/reports/{report_id}/fragments/f-none/revisions",
            json={"base_version": 1, "text": "x"},
        ).status_code == 404
        # 409：乐观锁（base_version 落后）
        resp = c.post(
            f"/api/kb/reports/{report_id}/fragments/{frag['id']}/revisions",
            json={"base_version": 99, "text": "勘误"},
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "kb_fragment_version_conflict"
        # 400：空文本
        resp = c.post(
            f"/api/kb/reports/{report_id}/fragments/{frag['id']}/revisions",
            json={"base_version": frag["version"], "text": "  "},
        )
        assert resp.status_code == 400

    def test_4_revise_success_records_version_and_rebuild(
        self, client: Any
    ) -> None:
        c, _storage, _ = client
        report_id = self._make_report(client)
        detail = c.get(f"/api/kb/reports/{report_id}").json()
        frag = detail["fragments"][0]
        resp = c.post(
            f"/api/kb/reports/{report_id}/fragments/{frag['id']}/revisions",
            json={"base_version": frag["version"],
                  "text": frag["text"] + "（勘误：补状态注记）"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == frag["id"] and body["version"] == frag["version"] + 1
        assert [v["v"] for v in body["versions"]] == [1, body["version"]]
        assert body["versions"][0]["note"] == "原始解析"  # v1 原始不可变
        assert body["versions"][-1]["note"] == "人工修正"
        assert body["rebuild"] == {"triggered": True, "hint": "已保存——将重建检索索引。"}
        assert body["activity_row"]["action"] == "修正片段"
        assert body["activity_row"]["who"]
        # 重建折算「片段修正」任务并跑完
        progress = _wait_done(c, body["task_id"])
        assert progress["source"] == "片段修正"
        assert progress["state"] == "done"
        # 详情随新版本（同源投影）
        revised = c.get(f"/api/kb/reports/{report_id}").json()
        target = next(f for f in revised["fragments"] if f["id"] == frag["id"])
        assert target["version"] == body["version"]
        assert target["text"].endswith("（勘误：补状态注记）")

    def test_b12_audit_writes_for_kb_write_ops(self, client: Any) -> None:
        """裁决指令①：建库/配置保存/停用启用/修正确认四写口经 security.audit。"""
        c, _storage, _ = client
        lib_id = _make_lib(c, name="审计库")
        report_id = self._make_report(client)
        detail = c.get(f"/api/kb/reports/{report_id}").json()
        frag = detail["fragments"][0]
        c.put(
            f"/api/kb/libs/{lib_id}/config",
            json={"switches": {"semantic": True, "keyword": True, "wiki": True,
                               "graph": False},
                  "mode": "smart", "add_summary": True, "add_questions": True,
                  "status": "disabled"},
        )
        c.post(
            f"/api/kb/reports/{report_id}/fragments/{frag['id']}/revisions",
            json={"base_version": frag["version"], "text": frag["text"] + "（勘误）"},
        )
        audit = c.get("/api/security/audit-logs").json()
        actions = [item["action"] for item in audit["items"]]
        assert "kb.lib.created" in actions
        assert "kb.config.saved" in actions
        assert "kb.fragment.revised" in actions


class TestB2FragmentsAndQueue:
    """B2 六端点（P1-04）：扁平清单/父块回捞/标记/队列/复核/销记＋B12 审计。"""

    def _make_report(self, client: Any, name: str = "B2 库") -> str:
        c, storage, _ = client
        lib_id = _make_lib(c, name=name)
        task_id = _ingest(c, storage, lib_id)
        _wait_done(c, task_id)
        reports = c.get("/api/kb/reports", params={"keyword": name}).json()
        assert reports["total"] == 1
        return reports["items"][0]["id"]

    def test_1_fragments_report_mode_and_inv(self, client: Any) -> None:
        c = client[0]
        report_id = self._make_report(client)
        resp = c.get("/api/kb/fragments", params={"report_id": report_id})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1 and body["items"]
        first = body["items"][0]
        assert set(first) == {"id", "report_id", "report", "well", "section", "type", "hit"}
        assert "context" not in first  # INV：列表只给子块、无 context 字段
        # 摘要/问题块带类型标入列（F37）
        types = {i["type"] for i in body["items"]}
        assert "原文块" in types
        # 404：报告不存在
        assert c.get("/api/kb/fragments", params={"report_id": "rpt-none"}).status_code == 404

    def test_1_library_mode_pagination_required(self, client: Any) -> None:
        c = client[0]
        self._make_report(client)
        # 缺任一分页参数 400（全库扁平清单读法强制分页）
        assert c.get("/api/kb/fragments").status_code == 400
        assert c.get("/api/kb/fragments", params={"page": 1}).status_code == 400
        resp = c.get("/api/kb/fragments", params={"page": 1, "pageSize": 2})
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1 and body["page_size"] == 2 and body["total"] >= 2
        # type 越界 400 / keyword 筛
        assert c.get(
            "/api/kb/fragments", params={"page": 1, "pageSize": 5, "type": "图片块"}
        ).status_code == 400
        kw = c.get(
            "/api/kb/fragments", params={"page": 1, "pageSize": 20, "keyword": "N-02"}
        ).json()
        assert kw["total"] >= 1

    def test_2_context_lazy_load(self, client: Any) -> None:
        c = client[0]
        report_id = self._make_report(client)
        frags = c.get("/api/kb/fragments", params={"report_id": report_id}).json()["items"]
        target = next(f for f in frags if f["type"] == "原文块")
        resp = c.get(f"/api/kb/fragments/{target['id']}/context")
        assert resp.status_code == 200
        body = resp.json()
        assert set(body) == {"id", "type", "hit", "context"}
        assert body["hit"] == target["hit"]
        assert c.get("/api/kb/fragments/f-none/context").status_code == 404

    def test_3_4_5_6_queue_closed_loop_and_b12(self, client: Any) -> None:
        c = client[0]
        report_id = self._make_report(client)
        frag = c.get(f"/api/kb/reports/{report_id}").json()["fragments"][0]
        # 端点 3 标记入队（hint 服务端返回）
        mark = c.post(f"/api/kb/fragments/{frag['id']}/issue-reports")
        assert mark.status_code == 200, mark.text
        issue = mark.json()
        assert issue["state"] == "待质检复核"
        assert issue["hint"].startswith("已标记 · 待质检复核")
        assert issue["fragment_label"].startswith("《")  # 三件套同源拼装
        # 重复标记 409（待质检复核态）
        dup = c.post(f"/api/kb/fragments/{frag['id']}/issue-reports")
        assert dup.status_code == 409
        assert dup.json()["code"] == "kb_issue_duplicate"
        # 端点 4 队列列表（state 筛）
        queue = c.get("/api/kb/issue-reports", params={"state": "待质检复核"})
        assert queue.status_code == 200 and queue.json()["total"] == 1
        assert c.get(
            "/api/kb/issue-reports", params={"state": "已销记"}
        ).status_code == 400  # 终态查询归后续批（400 枚举越界）
        # 端点 5 驳回：空理由 400 → 带理由已驳回
        empty = c.post(
            f"/api/kb/issue-reports/{issue['id']}/review",
            json={"action": "reject", "reason": "  "},
        )
        assert empty.status_code == 400
        assert empty.json()["code"] == "kb_issue_reject_reason_required"
        reject = c.post(
            f"/api/kb/issue-reports/{issue['id']}/review",
            json={"action": "reject", "reason": "检泵日期与台账对不上，请核对后重新标记"},
        )
        assert reject.status_code == 200
        assert reject.json()["state"] == "已驳回"
        # 端点 6 销记（仅已驳回态；已修正态销记 409）
        close = c.post(f"/api/kb/issue-reports/{issue['id']}/close")
        assert close.status_code == 200
        assert close.json()["state"] == "已销记 · 不修正"
        assert c.get("/api/kb/issue-reports").json()["total"] == 0  # 队列零悬挂
        # 重新标记闭环：新单入队 → confirm → B1 端点 4 修正流
        remark = c.post(f"/api/kb/fragments/{frag['id']}/issue-reports")
        assert remark.status_code == 200
        issue2 = remark.json()
        assert issue2["id"] != issue["id"]
        confirm = c.post(
            f"/api/kb/issue-reports/{issue2['id']}/review", json={"action": "confirm"}
        )
        assert confirm.status_code == 200
        assert confirm.json()["state"] == "已修正"
        revise = c.post(
            f"/api/kb/reports/{report_id}/fragments/{frag['id']}/revisions",
            json={"base_version": frag["version"], "text": frag["text"] + "（勘误）"},
        )
        assert revise.status_code == 200  # 确认后管理员修正（B1 端点 4）
        # 404 族：片段/标记单不存在
        assert c.post("/api/kb/fragments/f-none/issue-reports").status_code == 404
        assert c.post(
            "/api/kb/issue-reports/iss-none/review", json={"action": "confirm"}
        ).status_code == 404
        assert c.post("/api/kb/issue-reports/iss-none/close").status_code == 404
        # B12 平台审计三写口（标记/复核/销记——api 层编排）
        audit = c.get("/api/security/audit-logs").json()
        actions = [item["action"] for item in audit["items"]]
        assert "kb.fragment.marked" in actions
        assert "kb.issue.reviewed" in actions
        assert "kb.issue.closed" in actions
        # F62 活动流同事务「标记问题片段」
        lib_id = c.get(f"/api/kb/reports/{report_id}").json()["lib_id"]
        acts = c.get(f"/api/kb/libs/{lib_id}/activities").json()
        assert any(a["action"] == "标记问题片段" for a in acts["items"])

    def test_b2_401_identity_gate(self, client: Any) -> None:
        c = client[0]
        assert c.get(
            "/api/kb/fragments", params={"page": 1, "pageSize": 5},
            headers={"X-Dev-User": "hacker"},
        ).status_code == 401
        assert c.post(
            "/api/kb/fragments/f1/issue-reports", headers={"X-Dev-User": "hacker"}
        ).status_code == 401
