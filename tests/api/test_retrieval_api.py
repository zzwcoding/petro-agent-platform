"""D2 /api/retrieval 路由族 API 测试——两端点全往返：身份闸/默认形状/变更往返/400 带区间/B12 审计。

装配：sqlite 底座＋真 RetrievalService＋真 SecurityService（dependency_overrides
替换服务定位，不触 main.py lifespan；红线：本域零 LLM 调用）。
合同锚：D2-搜索与回答.md v0.2（端点形状/错误码草案）、00 §3（错误包）、
§14-R1（响应字段 snake_case——本端点即真实接线直接落 snake）。
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_retrieval, get_security
from app.api.errors import install_error_handlers
from app.api.retrieval import router as retrieval_router
from app.api.security import router as security_router
from app.domains.retrieval import RetrievalService
from app.domains.retrieval.store import ensure_retrieval_tables
from app.domains.security import SecurityService
from app.domains.security.store import ensure_audit_table
from app.infra.clock import freeze
from app.infra.db import ConnectionManager, DatabaseSpec

AQIANG_HEADERS: dict[str, str] = {"X-Dev-User": "aqiang"}

PARAMS_PATCH = {
    "params": {"semantic_top_k": 12, "keyword_top_k": 25, "merge": "concat", "top_n": 8},
}


@pytest.fixture
async def client(tmp_path: Any) -> AsyncIterator[tuple[TestClient, str]]:
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "retrieval-api.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_retrieval_tables(manager.engine())
    await ensure_audit_table(manager.engine())
    test_app = FastAPI()
    install_error_handlers(test_app)
    test_app.include_router(retrieval_router)
    test_app.include_router(security_router)  # B12 审计读面（断言消费）
    test_app.dependency_overrides[get_retrieval] = lambda: RetrievalService(manager)
    test_app.dependency_overrides[get_security] = lambda: SecurityService(manager)
    with TestClient(test_app) as test_client:
        yield test_client, str(tmp_path / "retrieval-api.db")
    await manager.dispose()


def _config(c: TestClient) -> dict[str, Any]:
    resp = c.get("/api/retrieval/config", headers=AQIANG_HEADERS)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _audit_rows(db_path: str) -> list[tuple[str, str, str]]:
    """audit_log 全行（stdlib sqlite3 直读库文件——D3 读面不出正文，content 断言绕行）。

    db.session() 每次退出即 commit（轻会话语义）——文件态即落定态，无跨 loop
    访问 aiosqlite 连接的问题。
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT who, action, content FROM audit_log ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


class TestAuthGate:
    def test_401_bad_actor(self, client: Any) -> None:
        c = client[0]
        resp = c.get("/api/retrieval/config", headers={"X-Dev-User": "ghost"})
        assert resp.status_code == 401
        assert resp.json()["code"] == "security_unauthenticated"

    def test_403_out_of_settings_group(self, client: Any) -> None:
        c = client[0]
        resp = c.get("/api/retrieval/config", headers={"X-Dev-User": "xiaoli"})
        assert resp.status_code == 403
        assert resp.json()["code"] == "security_forbidden"

    def test_401_on_submit(self, client: Any) -> None:
        c = client[0]
        resp = c.post(
            "/api/retrieval/change-requests",
            json={"patch": PARAMS_PATCH},
            headers={"X-Dev-User": "ghost"},
        )
        assert resp.status_code == 401
        assert resp.json()["code"] == "security_unauthenticated"


class TestGetConfig:
    def test_default_snapshot_shape(self, client: Any) -> None:
        """端点 1 默认快照：七节＋qa_behavior 五字段＋version{no,via}＋pending_change 恒空。"""
        c = client[0]
        body = _config(c)
        version = body["version"]
        assert version["no"] == "v1" and version["via"] is None
        assert version["updated_by"] == "系统"
        assert len(version["updated_at"]) == len("2026-10-02 12:00")  # R2 展示串形
        assert body["order"]["levels"] == [
            {"level": 1, "enabled": True},
            {"level": 2, "enabled": True},
            {"level": 3, "enabled": True},
        ]
        assert body["order"]["early_stop"] is True
        assert body["params"] == {
            "semantic_top_k": 20, "keyword_top_k": 20, "merge": "rrf_rank", "top_n": 20,
        }
        assert body["rerank"] == "fast"
        assert body["citation_format"] == "page"
        assert body["fallback"]["strategy"] == "fixed"
        assert body["fallback"]["text"].startswith("报告库里没有找到能回答这个问题的内容")
        qa = body["qa_behavior"]
        assert qa == {
            "faq_direct_hit": True,
            "refuse_threshold": 0.4,
            "clarify_strategy": "ask_missing",
            "confidence_thresholds": {"high": 0.8, "low": 0.4},
            "faq_expand_rounds": 3,
        }
        assert body["pending_change"] is None  # 阶段 1 恒空（提交即生效——两态语义挂 A3 批）

    def test_get_reflects_submitted_change(self, client: Any) -> None:
        c = client[0]
        submitted = c.post(
            "/api/retrieval/change-requests", json={"patch": PARAMS_PATCH}, headers=AQIANG_HEADERS
        )
        assert submitted.status_code == 202, submitted.text
        body = _config(c)
        assert body["version"]["no"] == "v2"
        assert body["version"]["via"] == submitted.json()["change_request_id"]
        assert body["params"]["semantic_top_k"] == 12 and body["params"]["top_n"] == 8
        assert body["rerank"] == "fast"  # 未提交节保持现值


class TestSubmitChangeRequest:
    def test_202_roundtrip_contract_fields(self, client: Any) -> None:
        """202 受理：合同冻结字段（changeRequestId/state）＋票面追加的新配置与版本。"""
        c, _db = client
        with freeze("2026-10-02 12:00:00"):
            resp = c.post(
                "/api/retrieval/change-requests",
                json={"patch": PARAMS_PATCH},
                headers=AQIANG_HEADERS,
            )
        assert resp.status_code == 202
        body = resp.json()
        assert body["change_request_id"] == "#CFG-20261002-01"
        assert body["state"] == "pending"  # 合同字面（A3 形态值——生效性由 version.via 回链）
        assert body["config"]["params"] == PARAMS_PATCH["params"]
        assert body["version"]["no"] == "v2"
        assert body["version"]["via"] == "#CFG-20261002-01"
        assert body["version"]["updated_by"] == "阿强 · 平台运维"

    def test_400_out_of_range_carries_range(self, client: Any) -> None:
        """越界 400 retrieval_param_invalid 带区间（D1 400 先例同形——violations 逐项）。"""
        c, _db = client
        bad = {
            "qa_behavior": {
                "faq_direct_hit": True,
                "refuse_threshold": 0.4,
                "clarify_strategy": "ask_missing",
                "confidence_thresholds": {"high": 0.8, "low": 0.4},
                "faq_expand_rounds": 6,
            }
        }
        resp = c.post("/api/retrieval/change-requests", json={"patch": bad}, headers=AQIANG_HEADERS)
        assert resp.status_code == 400
        payload = resp.json()
        assert payload["code"] == "retrieval_param_invalid"
        assert payload["detail"]["violations"] == [
            {"field": "patch.qa_behavior.faq_expand_rounds", "constraint": "1–5"}
        ]

    def test_400_unknown_section_and_empty_patch(self, client: Any) -> None:
        c, _db = client
        unknown = c.post(
            "/api/retrieval/change-requests", json={"patch": {"citationFormat": "code"}},
            headers=AQIANG_HEADERS,
        )
        assert unknown.status_code == 400
        assert unknown.json()["code"] == "retrieval_param_invalid"
        empty = c.post(
            "/api/retrieval/change-requests", json={"patch": {}}, headers=AQIANG_HEADERS
        )
        assert empty.status_code == 400
        assert "至少一个配置节" in empty.json()["message"]
        missing = c.post("/api/retrieval/change-requests", json={}, headers=AQIANG_HEADERS)
        assert missing.status_code == 400  # R8：请求还没进门（缺 patch）＝400 错误包
        assert missing.json()["code"] == "request_invalid"

    def test_b12_audit_written_after_success(self, client: Any) -> None:
        """B12 审计（retrieval.config_changed——api 层编排经 security.audit 唯一写口）。

        D3 读面只出门 time/who/action/digest（正文永不出门）——content 断言直读
        audit_log 存储行（00 §8.1 列形纪律）。
        """
        c, db_path = client
        resp = c.post(
            "/api/retrieval/change-requests", json={"patch": PARAMS_PATCH}, headers=AQIANG_HEADERS
        )
        assert resp.status_code == 202
        change_request_id = resp.json()["change_request_id"]
        logs = c.get(
            "/api/security/audit-logs",
            params={"action": "retrieval.config_changed"},
            headers=AQIANG_HEADERS,
        ).json()
        assert logs["total"] == 1
        assert logs["items"][0]["who"] == "阿强 · 平台运维"
        rows = _audit_rows(db_path)
        assert len(rows) == 1
        assert rows[0][1] == "retrieval.config_changed"
        assert change_request_id in rows[0][2]  # 单号留痕（回链可查）
        assert "v2" in rows[0][2] and "params" in rows[0][2]

    def test_b12_audit_not_written_on_400(self, client: Any) -> None:
        """失败路径不达审计行（P0-05 先例——审计在服务成功返回后落笔）。"""
        c, db_path = client
        bad = c.post(
            "/api/retrieval/change-requests", json={"patch": {"rerank": "极速"}},
            headers=AQIANG_HEADERS,
        )
        assert bad.status_code == 400
        assert _audit_rows(db_path) == []
