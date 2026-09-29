"""D1 路由族 API 测试——D1 方法面（7 条 HTTP 路由）全往返：身份闸/错误包/数据形状/演练三连。

装配：sqlite 底座＋桩 LLM（dependency_overrides 替换服务定位，不触 main.py
lifespan）；红线：任何测试不得真实调用 MiniMax/GLM 端点。
合同锚：D1-模型与线路.md（端点形状/错误码草案/行为规则）、00 §3（错误包）、
§5（演练 202/409/404）、§14-R1（响应字段 snake_case；query page/pageSize 保留）。
"""

import time
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.infra.config as infra_config
from app.api.deps import get_db, get_gateway, get_security
from app.api.errors import install_error_handlers
from app.api.gateway import router as gateway_router
from app.api.security import router as security_router
from app.domains.gateway import GatewayService
from app.domains.gateway.store import SpendRecord, ensure_gateway_tables
from app.domains.security import AuditRow, SecurityService
from app.domains.security.store import ensure_audit_table
from app.infra.clock import freeze
from app.infra.config import load_models_config
from app.infra.db import ConnectionManager, DatabaseSpec
from app.infra.llm_client import LlmCompletion

# 受控注册表与桩 LLM（字面假值；永不触网）。与 tests/domains/gateway/conftest.py
# 同构——tests/api 无包链，按 P0-04 先例本文件自足。
TEST_YAML = """\
# 测试用模型注册表（字面假值）
models:
  - alias: petro-main
    provider: anthropic
    model: MiniMax-M3
    base_url: https://main.example.test
    api_key: sk-test-main
    context_window: 1000000
    group: standard
    name: MiniMax-M3
    access: Anthropic 兼容接口 · 测试线路
    note: 问答/问数/问智默认出口
  - alias: petro-lite
    provider: anthropic
    model: glm-5.3-flash
    base_url: https://lite.example.test
    api_key: sk-test-lite
    context_window: 1000000
    group: lite
    name: glm-5.3-flash
    access: Anthropic 兼容接口 · 测试线路
    note: 备用/降级组——fallback 与预算熔断的便宜出口
routing:
  default: petro-main
  fallback_order: [petro-main, petro-lite]
prices:
  default:
    input_per_mtok: 1.0
    output_per_mtok: 3.0
gateway:
  allowed_fails: 2
  cooldown_seconds: 60
  num_retries: 3
  request_timeout: 30
"""

MAIN_COMPLETION = LlmCompletion(
    content="主模型应答",
    prompt_tokens=2140,
    completion_tokens=1380,
    usage_estimated=False,
    duration_ms=4000,
    model="anthropic/MiniMax-M3",
)
LITE_COMPLETION = LlmCompletion(
    content="线路正常",
    prompt_tokens=100,
    completion_tokens=50,
    usage_estimated=False,
    duration_ms=2400,
    model="anthropic/glm-5.3-flash",
)


class StubBackend:
    """按别名脚本应答；可注延迟（演练 409 用例拖住 running 态）。"""

    def __init__(self, script: dict[str, Any], delay: float = 0.0) -> None:
        self.script = script
        self.delay = delay

    async def complete(
        self,
        alias: str,
        messages: list[dict[str, str]],
        *,
        timeout_seconds: float,
        max_tokens: int = 4096,
        **params: Any,
    ) -> LlmCompletion:
        if self.delay:
            import asyncio

            await asyncio.sleep(self.delay)
        out = self.script[alias]
        if isinstance(out, Exception):
            raise out
        return out


@pytest.fixture(autouse=True)
def _reset_models_cache() -> AsyncIterator[None]:
    yield
    infra_config._models_cache = None  # 进程级注册表缓存——测试隔离


@pytest.fixture
def models_yaml(tmp_path: Path) -> Path:
    path = tmp_path / "models.yaml"
    path.write_text(TEST_YAML, encoding="utf-8")
    return path


@pytest.fixture
async def gateway_db(tmp_path: Path) -> AsyncIterator[ConnectionManager]:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "gateway-api.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    yield manager
    await manager.dispose()


@pytest.fixture
async def client(gateway_db: ConnectionManager, models_yaml: Path) -> AsyncIterator[TestClient]:
    load_models_config(models_yaml)
    await ensure_audit_table(gateway_db.engine())  # 幂等建表（P0-04 惯例）
    await ensure_gateway_tables(gateway_db.engine())  # 网关三表（99 §2.13）
    security = SecurityService(gateway_db)
    with freeze("2026-09-29T10:00:00"):
        await security.audit(
            AuditRow(
                who="小李 · 地质/质检",
                action="kb.report.uploaded",
                content="《2026年9月产量报告》入库",
            )
        )
    service = GatewayService(
        gateway_db,
        StubBackend({"petro-main": MAIN_COMPLETION, "petro-lite": LITE_COMPLETION}),
        config_path=models_yaml,
        drill_step_seconds=0.0,
    )
    test_app = FastAPI()
    install_error_handlers(test_app)
    test_app.include_router(gateway_router)
    test_app.include_router(security_router)  # config 保存审计走 B12 唯一写口的读面
    test_app.dependency_overrides[get_db] = lambda: gateway_db
    test_app.dependency_overrides[get_gateway] = lambda: service
    test_app.dependency_overrides[get_security] = lambda: security
    with TestClient(test_app) as test_client:  # 语境级 portal——演练后台任务需要存活的 loop
        yield test_client


# ---------- 身份闸（D1 权限行：页面仅「平台运维」；401/403 判例 00 §2.3） ----------


def test_unauthenticated_header_returns_401_error_package(client: TestClient) -> None:
    resp = client.get("/api/gateway/models", headers={"X-Dev-User": "ghost"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "security_unauthenticated"


def test_non_ops_role_forbidden(client: TestClient) -> None:
    resp = client.get("/api/gateway/models", headers={"X-Dev-User": "shixi"})
    assert resp.status_code == 403
    assert resp.json()["code"] == "security_forbidden"


def test_missing_header_defaults_to_ops(client: TestClient) -> None:
    # 缺头落默认角色阿强（平台运维）——可过设置中心组闸（P0-04 拍板先例）
    assert client.get("/api/gateway/models").status_code == 200


# ---------- 端点 1：GET /models ----------


def test_models_lists_registry_with_role_derivation(client: TestClient) -> None:
    resp = client.get("/api/gateway/models")
    assert resp.status_code == 200
    body = resp.json()
    assert body["gateway"]["status"] == "running"
    assert [(m["key"], m["role"], m["alias"]) for m in body["models"]] == [
        ("main", "main", "petro-main"),
        ("backup", "backup", "petro-lite"),
    ]
    assert set(body["models"][0]) == {"key", "name", "alias", "role", "access", "note"}


# ---------- 端点 2/3：GET · PUT /config ----------


def test_get_config_returns_params_and_yaml_fulltext(client: TestClient) -> None:
    resp = client.get("/api/gateway/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["params"] == {
        "allowed_fails": 2,
        "cooldown_seconds": 60,
        "num_retries": 3,
        "request_timeout": 30,
    }
    assert "gateway:" in body["yaml"] and "allowed_fails: 2" in body["yaml"]


def test_put_config_saves_hot_reloads_and_audits(client: TestClient, models_yaml: Path) -> None:
    resp = client.put(
        "/api/gateway/config",
        json={"params": {
            "allowed_fails": 4, "cooldown_seconds": 90,
            "num_retries": 2, "request_timeout": 20,
        }},
    )
    assert resp.status_code == 200
    assert resp.json()["params"]["allowed_fails"] == 4  # 返回快照为唯一真值
    text = models_yaml.read_text(encoding="utf-8")
    assert "allowed_fails: 4" in text and "cooldown_seconds: 90" in text  # 写回文件
    # B12 横切留痕：config 保存写一条审计（唯一写口；默认角色阿强）
    logs = client.get("/api/security/audit-logs").json()["items"]
    assert any(item["action"] == "gateway.config.saved" for item in logs)


def test_put_config_out_of_range_returns_400_with_field_and_range(client: TestClient) -> None:
    resp = client.put(
        "/api/gateway/config",
        json={"params": {
            "allowed_fails": 99, "cooldown_seconds": 60,
            "num_retries": 3, "request_timeout": 30,
        }},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "gateway_param_invalid"
    assert body["detail"]["violations"] == [{"field": "params.allowed_fails", "constraint": "1–10"}]


# ---------- 端点 4：GET /spend-logs（分页/筛选/数据形状红线） ----------


@pytest.fixture
async def spend_seeded(gateway_db: ConnectionManager) -> None:
    rows = [
        SpendRecord(
            id="call-8c31", time=datetime(2026, 9, 29, 9, 52, 30),
            model_key="main", alias="petro-main", input_tokens=2140, output_tokens=1380,
            first_ms=1000, total_ms=4000, cost_yuan=0.00628, fallback=False, note="",
        ),
        SpendRecord(
            id="call-9d02", time=datetime(2026, 9, 29, 9, 10, 0),
            model_key="backup", alias="petro-lite", input_tokens=500, output_tokens=300,
            first_ms=2400, total_ms=2600, cost_yuan=0.0014, fallback=True, note="故障演练流水",
        ),
        SpendRecord(
            id="call-1a77", time=datetime(2026, 9, 20, 8, 0, 0),
            model_key="main", alias="petro-main", input_tokens=10, output_tokens=5,
            first_ms=800, total_ms=900, cost_yuan=0.000025, fallback=False, note="上周",
        ),
    ]
    async with gateway_db.session() as session:
        for row in rows:
            session.add(row)


def test_spend_logs_shape_red_line_raw_numbers(client: TestClient, spend_seeded: None) -> None:
    resp = client.get("/api/gateway/spend-logs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3 and body["page"] == 1 and body["page_size"] == 15  # D1 合同默认 15
    item = body["items"][0]  # 排序恒 time 倒序
    assert item["id"] == "call-8c31"
    assert isinstance(item["input_tokens"], int) and isinstance(item["output_tokens"], int)
    assert isinstance(item["first_ms"], int) and isinstance(item["total_ms"], int)
    assert isinstance(item["cost_yuan"], float)  # 元数值——禁拼好的展示串
    assert set(item) == {
        "id", "time", "model_key", "alias", "input_tokens", "output_tokens",
        "first_ms", "total_ms", "cost_yuan", "fallback", "note",
    }


def test_spend_logs_filters(client: TestClient, spend_seeded: None) -> None:
    with freeze("2026-09-29T10:00:00"):  # range 窗口对齐种子行日期
        backup_items = client.get("/api/gateway/spend-logs?model=backup").json()["items"]
        assert [i["id"] for i in backup_items] == ["call-9d02"]
        today = client.get("/api/gateway/spend-logs?range=today").json()
        assert {i["id"] for i in today["items"]} == {"call-8c31", "call-9d02"}  # 9-20 行出窗
        assert client.get("/api/gateway/spend-logs?range=7d").json()["total"] == 2
        kw = client.get("/api/gateway/spend-logs?keyword=8c31").json()  # keyword 匹配调用号
        assert [i["id"] for i in kw["items"]] == ["call-8c31"]
        kw2 = client.get("/api/gateway/spend-logs?keyword=演练").json()  # 匹配备注
        assert [i["id"] for i in kw2["items"]] == ["call-9d02"]
        assert client.get("/api/gateway/spend-logs?model=bogus").status_code == 400
        assert client.get("/api/gateway/spend-logs?range=30d").status_code == 400


# ---------- 端点 5/6/7：演练三连（202 受理/轮询/历史；409 重入；404 未知） ----------


def _poll_done(client: TestClient, drill_id: str, timeout_s: float = 15.0) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    body: dict[str, Any] = {}
    while time.time() < deadline:
        resp = client.get(f"/api/gateway/drills/{drill_id}")
        assert resp.status_code == 200
        body = resp.json()
        if body["status"] == "done":
            return body
        time.sleep(0.05)
    raise AssertionError("演练未在超时内到达 done")


def test_drill_flow_202_poll_result_history(client: TestClient) -> None:
    resp = client.post("/api/gateway/drills")
    assert resp.status_code == 202
    drill_id = resp.json()["drill_id"]
    assert drill_id.startswith("drill-")

    done = _poll_done(client, drill_id)
    assert done["drill_id"] == drill_id
    assert [n["key"] for n in done["nodes"]] == ["fail1", "fail2", "fallback", "ledger"]
    states = {n["key"]: n["state"] for n in done["nodes"]}
    assert states == {"fail1": "error", "fail2": "error", "fallback": "finish", "ledger": "finish"}
    result = done["result"]
    assert result["fallback"]["event"] == "fallback_triggered"
    assert result["fallback"]["failed_deploy"] == "anthropic/MiniMax-M3"
    assert result["fallback"]["failover_target"] == "anthropic/glm-5.3-flash"
    assert result["fallback"]["consecutive_fails"] == 2 and result["fallback"]["cooldown_sec"] == 60
    assert result["ledger_row"]["fallback"] is True
    assert result["ledger_row"]["model_key"] == "backup"

    history = client.get("/api/gateway/drills").json()
    assert len(history) == 1
    assert history[0]["id"] == drill_id
    assert "阈值 2" in history[0]["summary"] and "冷却 60s" in history[0]["summary"]

    # 演练真切换一次模型留痕：spend-logs 出现一条备用应答行（演练即真实流量）
    logs = client.get("/api/gateway/spend-logs?model=backup").json()
    assert logs["total"] == 1 and logs["items"][0]["fallback"] is True
    assert logs["items"][0]["note"] == "gateway.drill"

    # 主用冷却期内 → 网关态 degraded（页头徽标：备用承载中）
    assert client.get("/api/gateway/models").json()["gateway"]["status"] == "degraded"


def test_drill_reentry_returns_409_while_running(client: TestClient) -> None:
    gateway = client.app.dependency_overrides[get_gateway]()  # type: ignore[union-attr]
    gateway._backend.delay = 0.5
    first = client.post("/api/gateway/drills")
    assert first.status_code == 202
    second = client.post("/api/gateway/drills")
    assert second.status_code == 409
    assert second.json()["code"] == "gateway_drill_conflict"
    _poll_done(client, first.json()["drill_id"])


def test_drill_start_writes_audit_with_actor(client: TestClient) -> None:
    """98 卡 start_drill(actor) 的 who 留痕：受理即写 gateway.drill.started 审计（B12）。

    读面只有 time/who/action/digest（正文永不出门）——who/action 即本测断言面。
    """
    resp = client.post("/api/gateway/drills", headers={"X-Dev-User": "aqiang"})
    assert resp.status_code == 202
    _poll_done(client, resp.json()["drill_id"])
    logs = client.get("/api/security/audit-logs").json()["items"]
    started = [i for i in logs if i["action"] == "gateway.drill.started"]
    assert len(started) == 1
    assert started[0]["who"] == "阿强 · 平台运维"  # actor 槽透传（label 全名）


def test_drill_unknown_id_404(client: TestClient) -> None:
    resp = client.get("/api/gateway/drills/drill-deadbeef")
    assert resp.status_code == 404
    assert resp.json()["code"] == "gateway_drill_not_found"
