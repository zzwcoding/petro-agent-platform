"""B2 质检复核队列 PG 集成（P1-04）——队列状态机全迁移＋驳回闭环真库实跑。

约定同 kb PG 组（TEST_DATABASE_URL 未配置即 skip；自动改用 <库名>_test 独立库）。
装配真路由族（B2 六端点＋B1 端点 4 修正＋B12 审计读面）——sqlite 单测之外
在 PG 真库上验证：部分唯一索引重复标记判据、事务活动流、closed loop
标记→驳回→重标→确认→B1 修正→销记。

loop 纪律（test_kb_smoke_real 同款）：TestClient 请求跑在 portal loop；测试内
直查 DB 用 fresh ConnectionManager＋asyncio.run（引擎不跨 loop 共用）。
"""

import asyncio
import os
import time
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

DEMO_TEXT = (
    "N-02 井完井报告\n1 基本情况\nN-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，"
    "2019-06-15 投产。\n2 完井段\n完井段详见参数表。\n"
)


class FakeObjectStorage:
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
        return self.objects[key]


class StubCompleter:
    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Any:
        from app.domains.gateway import Completion

        return Completion(
            content="应答", prompt_tokens=1, completion_tokens=1,
            usage_estimated=False, call_id="call-stub", cost_yuan=0.0,
            fallback=False, served_alias=alias,
        )


def _isolated_url() -> URL:
    url = make_url(TEST_DATABASE_URL)
    return url.set(database=f"{url.database}_test")


def _spec(url: URL) -> Any:
    from app.infra.db import DatabaseSpec

    return DatabaseSpec(
        name="primary", role="primary", driver=url.drivername.split("+", 1)[0],
        host=url.host or "localhost", port=url.port or 5433, database=url.database or "",
        user=url.username or "", password=url.password or "", pool_size=2, max_overflow=1,
    )


@pytest.fixture
async def env() -> AsyncIterator[dict[str, Any]]:
    """PG 测试环境：建表＋装配真路由族（URL/spec 供测试内 fresh manager 直查）。"""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL 未配置——PG 集成测试跳过（约定见票面）")
    from app.api.deps import get_kb, get_security
    from app.api.errors import install_error_handlers
    from app.api.kb import router as kb_router
    from app.api.security import router as security_router
    from app.domains.kb import KbService
    from app.domains.kb.store import ensure_kb_tables
    from app.domains.security import SecurityService
    from app.domains.security.store import ensure_audit_table
    from app.infra.db import ConnectionManager
    from app.infra.eventbus import InMemoryEventBus

    url = _isolated_url()
    manager = ConnectionManager([_spec(url)])
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(text(
            "DROP TABLE IF EXISTS kb_issue_report, kb_activity, kb_fragment_version, "
            "kb_fragment, kb_ingest_task, kb_report, kb_upload, kb_library_config, "
            "kb_library, audit_log CASCADE"
        ))
    await ensure_kb_tables(engine)
    await ensure_audit_table(engine)
    await engine.dispose()

    storage = FakeObjectStorage()
    service = KbService(manager, StubCompleter(), storage, eventbus=InMemoryEventBus(),
                        step_seconds=0.0)
    test_app = FastAPI()
    install_error_handlers(test_app)
    test_app.include_router(kb_router)
    test_app.include_router(security_router)
    test_app.dependency_overrides[get_kb] = lambda: service
    test_app.dependency_overrides[get_security] = lambda: SecurityService(manager)
    with TestClient(test_app) as test_client:
        yield {"client": test_client, "storage": storage, "spec": _spec(url)}
    await manager.dispose()


def _ingest(client: TestClient, storage: FakeObjectStorage) -> str:
    lib = client.post(
        "/api/kb/libs", json={"lib_name": "B2PG 库", "biz_template": "completion"}
    )
    assert lib.status_code == 201, lib.text
    up = client.post(
        "/api/kb/uploads",
        json={
            "filename": "N-02 井完井报告.pdf", "size": len(DEMO_TEXT),
            "lib_id": lib.json()["lib_id"],
        },
    )
    assert up.status_code == 200, up.text
    receipt = up.json()
    storage.objects[receipt["put_url"].split("/put/")[1]] = DEMO_TEXT.encode("utf-8")
    confirm = client.post(f"/api/kb/uploads/{receipt['upload_id']}/confirm")
    assert confirm.status_code == 200, confirm.text
    task_id = confirm.json()["task_id"]
    for _ in range(400):
        if client.get(f"/api/kb/tasks/{task_id}").json()["state"] in ("done", "failed"):
            break
        time.sleep(0.02)
    assert client.get(f"/api/kb/tasks/{task_id}").json()["state"] == "done"
    return client.get("/api/kb/reports", params={"keyword": "B2PG"}).json()["items"][0]["id"]


def _wait_done(client: TestClient, task_id: str) -> str:
    for _ in range(400):
        state = client.get(f"/api/kb/tasks/{task_id}").json()["state"]
        if state in ("done", "failed", "stuck"):
            break
        time.sleep(0.02)
    return client.get(f"/api/kb/tasks/{task_id}").json()["state"]


def test_b2_queue_closed_loop_on_pg(env: dict[str, Any]) -> None:
    """PG 真库闭环：标记→409→驳回（空 400/带理由）→重标（旧单销记）→确认→
    B1 修正→活动流＋B12 审计全留痕。"""
    c: TestClient = env["client"]
    storage: FakeObjectStorage = env["storage"]
    report_id = _ingest(c, storage)
    frag = c.get(f"/api/kb/reports/{report_id}").json()["fragments"][0]

    # ① 标记入队（F62 同事务——PG 真库事务边界）
    mark = c.post(f"/api/kb/fragments/{frag['id']}/issue-reports")
    assert mark.status_code == 200, mark.text
    issue = mark.json()
    # 部分唯一索引判据：同片段待质检复核态重复标记 409
    dup = c.post(f"/api/kb/fragments/{frag['id']}/issue-reports")
    assert dup.status_code == 409 and dup.json()["code"] == "kb_issue_duplicate"

    # ② 驳回闭环（空理由 400 → 带理由已驳回）
    assert c.post(
        f"/api/kb/issue-reports/{issue['id']}/review", json={"action": "reject"}
    ).status_code == 400
    rejected = c.post(
        f"/api/kb/issue-reports/{issue['id']}/review",
        json={"action": "reject", "reason": "PG 驳回理由（必填）"},
    )
    assert rejected.status_code == 200 and rejected.json()["state"] == "已驳回"

    # ③ 重新标记：新单入队、旧驳回单转已销记（队列零悬挂——PG UPDATE 真跑）
    remark = c.post(f"/api/kb/fragments/{frag['id']}/issue-reports")
    assert remark.status_code == 200
    issue2 = remark.json()

    from app.domains.kb.store import IssueReportRow
    from app.infra.db import ConnectionManager

    async def _check_old() -> None:
        manager = ConnectionManager([env["spec"]])
        try:
            async with manager.readonly() as session:
                old = await session.get(IssueReportRow, issue["id"])
                assert old is not None
                assert old.state == "已销记" and old.reject_reason == "PG 驳回理由（必填）"
        finally:
            await manager.dispose()

    asyncio.run(_check_old())
    assert c.get("/api/kb/issue-reports", params={"state": "待质检复核"}).json()["total"] == 1

    # ④ 复核确认转修正流（已修正终态）→ B1 端点 4 修正真跑
    confirm = c.post(
        f"/api/kb/issue-reports/{issue2['id']}/review", json={"action": "confirm"}
    )
    assert confirm.status_code == 200 and confirm.json()["state"] == "已修正"
    revise = c.post(
        f"/api/kb/reports/{report_id}/fragments/{frag['id']}/revisions",
        json={"base_version": frag["version"], "text": frag["text"] + "（勘误）"},
    )
    assert revise.status_code == 200, revise.text
    assert _wait_done(c, revise.json()["task_id"]) == "done"

    # ④' 销记腿：另一片段 标记→驳回→销记（仅已驳回态可销记——其他态 409）
    frag2 = c.get(f"/api/kb/reports/{report_id}").json()["fragments"][1]
    mark2 = c.post(f"/api/kb/fragments/{frag2['id']}/issue-reports")
    assert mark2.status_code == 200
    assert c.post(f"/api/kb/issue-reports/{mark2.json()['id']}/close").status_code == 409
    c.post(
        f"/api/kb/issue-reports/{mark2.json()['id']}/review",
        json={"action": "reject", "reason": "销记腿驳回理由"},
    )
    close2 = c.post(f"/api/kb/issue-reports/{mark2.json()['id']}/close")
    assert close2.status_code == 200 and close2.json()["state"] == "已销记 · 不修正"

    # ⑤ 队列出列（终态不出列）＋活动流/B12 全留痕
    assert c.get("/api/kb/issue-reports").json()["total"] == 0
    lib_id = c.get(f"/api/kb/reports/{report_id}").json()["lib_id"]
    acts = c.get(f"/api/kb/libs/{lib_id}/activities").json()
    assert "标记问题片段" in [a["action"] for a in acts["items"]]
    audit = c.get("/api/security/audit-logs").json()
    audit_actions = {item["action"] for item in audit["items"]}
    assert {"kb.fragment.marked", "kb.issue.reviewed", "kb.issue.closed",
            "kb.fragment.revised"} <= audit_actions


def test_b2_issue_state_check_enforced_on_pg(env: dict[str, Any]) -> None:
    """state CHECK 四态真库强制（99 §2.5 冻结值）。"""
    from sqlalchemy.exc import IntegrityError

    from app.domains.kb.store import (
        FragmentRow,
        FragmentVersionRow,
        IssueReportRow,
        LibraryRow,
        ReportRow,
    )
    from app.infra.clock import now
    from app.infra.db import ConnectionManager

    async def _check() -> None:
        manager = ConnectionManager([env["spec"]])
        try:
            async with manager.session() as session:
                session.add(LibraryRow(id="lib-ck2", name="CK2 库", biz_template="blank"))
                await session.flush()
                session.add(ReportRow(id="rpt-ck2", lib_id="lib-ck2", doc="《CK2》",
                                      object_key="k"))
                await session.flush()
                session.add(FragmentRow(id="fck2", report_id="rpt-ck2", type="原文块",
                                        section="正文", current_version=1,
                                        is_parent_only=False))
                await session.flush()
                session.add(FragmentVersionRow(fragment_id="fck2", v=1, text="t",
                                               note="原始解析"))
                await session.flush()
                session.add(IssueReportRow(id="iss-bad2", fragment_id="fck2",
                                           state="reopened", marked_by="x", marked_at=now()))
                with pytest.raises(IntegrityError):  # CHECK 四态冻结值
                    await session.flush()
                await session.rollback()
        finally:
            await manager.dispose()

    asyncio.run(_check())
