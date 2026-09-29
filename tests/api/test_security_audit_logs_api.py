"""D3 端点 14 骨架 API 测试——身份桩 401/默认角色/组闸 403/统一错误包/分页形状。

路由以 sqlite 底座装配（dependency_overrides 替换服务定位，不触 main.py
lifespan）；合同锚：D3 端点 14 形状、00 §2.3/2.4、§3.1/3.2、§14-R1/R3。
"""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.deps import get_db, get_security
from app.api.errors import install_error_handlers
from app.api.security import router as security_router
from app.domains.security import AuditRow, SecurityService
from app.domains.security.store import ensure_audit_table
from app.infra.clock import freeze
from app.infra.db import ConnectionManager, DatabaseSpec


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[TestClient]:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "security-api.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    engine = create_async_engine(spec.url())
    await ensure_audit_table(engine)
    await engine.dispose()

    service = SecurityService(manager)
    with freeze("2026-09-29T10:00:00"):
        await service.audit(
            AuditRow(
                who="阿强 · 平台运维",
                action="security.query_policy.saved",
                content="查询安检配置保存（进 C3 审批）",
            )
        )
        await service.audit(
            AuditRow(
                who="小李 · 地质/质检",
                action="kb.report.uploaded",
                content="《2026年9月产量报告》入库",
            )
        )

    test_app = FastAPI()
    install_error_handlers(test_app)
    test_app.include_router(security_router)
    test_app.dependency_overrides[get_db] = lambda: manager
    test_app.dependency_overrides[get_security] = lambda: service
    yield TestClient(test_app)
    await manager.dispose()


# ---------- 身份桩（缺头→默认角色阿强过设置中心组闸；00 §2.4/PRD 拍板） ----------


def test_missing_header_defaults_to_aqiang_and_passes_gate(client: TestClient) -> None:
    resp = client.get("/api/security/audit-logs")
    assert resp.status_code == 200  # 缺头不 401——缺省落默认角色（aqiang ∈ 设置中心组）
    body = resp.json()
    assert body["total"] == 2 and body["page"] == 1 and body["page_size"] == 20
    assert [item["who"] for item in body["items"]] == [
        "小李 · 地质/质检",  # 同时刻 id desc 决胜——后写在前
        "阿强 · 平台运维",
    ]


def test_aqiang_header_passes_settings_gate(client: TestClient) -> None:
    resp = client.get("/api/security/audit-logs", headers={"X-Dev-User": "aqiang"})
    assert resp.status_code == 200


def test_unknown_role_key_is_401_error_package(client: TestClient) -> None:
    resp = client.get("/api/security/audit-logs", headers={"X-Dev-User": "ghost"})
    assert resp.status_code == 401  # 00 §2.3：401＝身份解析失败
    body = resp.json()
    assert body["code"] == "security_unauthenticated"
    assert "身份解析失败" in body["message"] and "ghost" in body["message"]


def test_xiaoli_direct_call_is_403_forbidden_package(client: TestClient) -> None:
    # 00 §2.3：403 留给直调越权（设置中心组＝运维角色——D3 权限行）。
    resp = client.get("/api/security/audit-logs", headers={"X-Dev-User": "xiaoli"})
    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == "security_forbidden"
    assert "设置中心" in body["message"]


# ---------- 响应形状（D3 端点 14；R1 snake；R3 total；00 §1.4 ISO 时间） ----------


def test_items_shape_and_iso_time_never_carries_content(client: TestClient) -> None:
    body = client.get("/api/security/audit-logs").json()
    assert set(body["items"][0]) == {"time", "who", "action", "digest"}  # 正文不出门
    assert body["items"][0]["time"] == "2026-09-29T10:00:00"  # ISO 8601 无时区后缀
    assert len(body["items"][0]["digest"]) == 64  # SM3 hex 64
    assert all("content" not in item for item in body["items"])


def test_page_params_respected(client: TestClient) -> None:
    body = client.get("/api/security/audit-logs", params={"page": 2, "pageSize": 1}).json()
    assert (body["page"], body["page_size"], body["total"]) == (2, 1, 2)  # R3 total 筛选后
    assert len(body["items"]) == 1


def test_page_zero_is_400_error_package(client: TestClient) -> None:
    # 00 §3.2：请求还没进门（数值越界）＝400；FastAPI 缺省 422 已收口为错误包 400。
    resp = client.get("/api/security/audit-logs", params={"page": 0})
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "request_invalid"
    assert body["detail"]["errors"]  # detail 带字段与问题（00 §3.1）
