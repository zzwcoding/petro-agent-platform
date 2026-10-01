"""C1 台账读面三件套 API 测试（P1-01b——C1 册端点 2/3/5/6 列形＋00 §4.1/§4.5 横切）。

路由以 sqlite 底座装配（dependency_overrides 替换服务定位，不触 main.py
lifespan）；台账数据＝同步器种子（零手养——读面直读即有数）。
合同锚：C1 端点 2/3/5/6 DTO、筛选语义精确等值、F60 到日即标、粒度·单位
双形态；00 §4.1 分页回显、§4.2 total/grand_total、§4.5 keyword/status、
§3 统一错误包（400 semantics_param_invalid）、纯读面 405 兜底。
"""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.deps import get_db, get_semantics
from app.api.errors import install_error_handlers
from app.api.semantics import router as semantics_router
from app.domains.security.domain import resolve_actor
from app.domains.semantics import SemanticsService
from app.domains.semantics.store import ensure_semantics_tables
from app.infra.clock import freeze
from app.infra.db import ConnectionManager, DatabaseSpec

TODAY = "2026-10-01T10:00:00"  # 术语 #11（2026-06-30 届满）已过期、#2/#4 未到期的判定位


class RecordingAudit:
    """B12 审计替身（同步动作写口形状不旁路）。"""

    async def audit(self, row: object, *, session: object | None = None) -> None: ...


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[TestClient]:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "semantics-api.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    engine = create_async_engine(spec.url())
    await ensure_semantics_tables(engine)
    await engine.dispose()
    service = SemanticsService(manager, RecordingAudit())
    await service.sync_from_ontology_repo("mr#1", resolve_actor(None))  # 首跑种子零手养

    test_app = FastAPI()
    install_error_handlers(test_app)
    test_app.include_router(semantics_router)
    test_app.dependency_overrides[get_db] = lambda: manager
    test_app.dependency_overrides[get_semantics] = lambda: service
    with freeze(TODAY):
        yield TestClient(test_app)
    await manager.dispose()


# ---------- 术语读面（C1 端点 2） ----------


def test_terms_default_lists_full_ledger_with_envelope(client: TestClient) -> None:
    resp = client.get("/api/semantics/terms")
    assert resp.status_code == 200
    body = resp.json()
    assert body["grand_total"] == 11 and body["total"] == 11  # C1 页签计数
    assert body["page"] == 1 and body["page_size"] == 20  # 00 §4.1 回显（R1 snake）
    assert [item["id"] for item in body["items"]] == list(range(1, 12))  # 台账序 id 升序
    first = body["items"][0]
    assert first["term"] == "老完成率" and first["def"] == "v1 口径（不含自用油折算），2024 年废弃"
    assert first["status_key"] == "禁用词" and first["owner"] == "开发室"


def test_terms_keyword_hits_alias_via_type_display(client: TestClient) -> None:
    # 别名命中：类型展示串「别名 → X」「缩写 → X」族＝GLS 别名的台账载体
    body = client.get("/api/semantics/terms", params={"keyword": "净产量"}).json()
    assert [item["id"] for item in body["items"]] == [2]  # 剔检产量（别名 → 净产量）
    assert body["total"] == 1 and body["grand_total"] == 11
    body = client.get("/api/semantics/terms", params={"keyword": "抽油机时率"}).json()
    assert [item["id"] for item in body["items"]] == [5]  # 时率（缩写 → 抽油机时率）


def test_terms_status_filter_exact_and_invalid_400(client: TestClient) -> None:
    body = client.get(
        "/api/semantics/terms", params={"status": "有效（已届满）"}
    ).json()
    assert [item["id"] for item in body["items"]] == [11]
    assert body["items"][0]["expired"] is True  # F60 到日即标（2026-06-30 ≤ 冻结今日）
    assert body["items"][0]["expires_display"] == "2026-06-30（已届满）"
    # 多值逗号分隔（00 §4.5）
    body = client.get("/api/semantics/terms", params={"status": "禁用词,有效（引用马涛）"}).json()
    assert [item["id"] for item in body["items"]] == [1, 10]
    resp = client.get("/api/semantics/terms", params={"status": "下线"})
    assert resp.status_code == 400
    error = resp.json()
    assert error["code"] == "semantics_param_invalid" and "下线" in error["message"]
    assert error["detail"]["allowed"][0] == "有效"  # 越界 400 带允许值


def test_terms_owner_exact_match_excludes_nothing_unexpected(client: TestClient) -> None:
    body = client.get("/api/semantics/terms", params={"owner": "语义 Owner"}).json()
    assert [item["id"] for item in body["items"]] == [10]
    body = client.get("/api/semantics/terms", params={"owner": "all"}).json()
    assert body["total"] == 11  # 「全部负责人」＝all
    assert body["items"][9]["expires_display"] == "长期（引用类）"  # 引用类展示串派生


def test_terms_pagination_echo_and_slice(client: TestClient) -> None:
    body = client.get(
        "/api/semantics/terms", params={"page": 2, "pageSize": 5}
    ).json()
    assert [item["id"] for item in body["items"]] == [6, 7, 8, 9, 10]
    assert (body["page"], body["page_size"], body["total"], body["grand_total"]) == (2, 5, 11, 11)


def test_terms_expiry_display_families_at_freeze(client: TestClient) -> None:
    items = {item["id"]: item for item in client.get("/api/semantics/terms").json()["items"]}
    assert items[1]["expires_display"] == "—（已禁用）" and items[1]["expired"] is False
    assert items[8]["expires_display"] == "长期"
    assert items[2]["expires_display"] == "2027-12-31" and items[2]["expired"] is False


# ---------- 指标读面（C1 端点 3） ----------


def test_metrics_list_grain_display_c1_column_shape(client: TestClient) -> None:
    body = client.get("/api/semantics/metrics").json()
    assert body["grand_total"] == 15 and body["total"] == 15
    items = {item["id"]: item for item in body["items"]}
    assert items[1]["grain_display"] == "月（按区块 / 油田） · %"  # C1 页签列形（斜杠形转换）
    assert items[1]["grain"] == "月/区块·油田" and items[1]["unit"] == "%"  # 存储值不动＝裁决 e
    assert items[2]["grain_display"] == "月 · 吨"
    assert items[3]["grain_display"] == "月·年 · %"
    assert items[2]["mark"] == "★" and items[2]["slot_name"] == "有效产量"
    assert items[10]["status"] == ["生效中", "待联席裁决"]  # 双徽标
    assert items[2]["name"] == "★有效产量（两支口径）"


def test_metrics_filters_keyword_status_owner(client: TestClient) -> None:
    body = client.get("/api/semantics/metrics", params={"keyword": "有效产量"}).json()
    assert [item["id"] for item in body["items"]] == [2]  # name/slot_name 命中
    body = client.get("/api/semantics/metrics", params={"status": "待联席裁决"}).json()
    assert [item["id"] for item in body["items"]] == [10]  # 状态数组包含命中
    body = client.get("/api/semantics/metrics", params={"owner": "采油工艺所"}).json()
    assert 10 not in [item["id"] for item in body["items"]]  # 精确等值——联席行不入
    assert {item["id"] for item in body["items"]} == {6, 8, 9, 12, 13, 14}
    body = client.get("/api/semantics/metrics", params={"owner": "all"}).json()
    assert body["total"] == 15
    resp = client.get("/api/semantics/metrics", params={"status": "已下线"})
    assert resp.status_code == 400 and resp.json()["code"] == "semantics_param_invalid"


# ---------- 对象与关系读面（C1 端点 5/6） ----------


def test_objects_list_draft_fixed_values_and_keyword(client: TestClient) -> None:
    body = client.get("/api/semantics/objects").json()
    assert body["grand_total"] == 10 and body["total"] == 10
    assert all(item["status"] == "草案" for item in body["items"])  # 对象行固定值
    assert body["items"][0] == {
        "id": 1, "obj": "井", "attr": "井号 / 井别 / 投产日 / 状态机",
        "status": "草案", "owner": None, "source": "设定书 §5", "version": None,
    }
    body = client.get("/api/semantics/objects", params={"keyword": "受效"}).json()
    assert [item["id"] for item in body["items"]] == [9]  # 受效关系


def test_relations_list_reference_rows_and_keyword(client: TestClient) -> None:
    body = client.get("/api/semantics/relations").json()
    assert body["grand_total"] == 5 and body["total"] == 5
    assert body["items"][2]["rel"] == "注水井 —受效→ 油井"
    assert body["items"][2]["read"] == "哪口注水井的注水，效果落在哪口油井上"
    body = client.get("/api/semantics/relations", params={"keyword": "受效"}).json()
    assert [item["id"] for item in body["items"]] == [3]
    body = client.get(
        "/api/semantics/relations", params={"page": 1, "pageSize": 2}
    ).json()
    assert [item["id"] for item in body["items"]] == [1, 2] and body["page_size"] == 2


# ---------- 横切（纯读面 405 兜底；身份桩缺省角色可读） ----------


def test_write_requests_fall_back_to_405(client: TestClient) -> None:
    for method in ("post", "put", "delete"):
        resp = getattr(client, method)("/api/semantics/terms")
        assert resp.status_code == 405  # C1 纯读面裁决——无写路由（框架兜底）


def test_read_endpoints_open_to_all_roles(client: TestClient) -> None:
    for who in ("laowang", "xiaoli", "zhuren", "aqiang", "shixi"):
        resp = client.get("/api/semantics/terms", headers={"X-Dev-User": who})
        assert resp.status_code == 200  # C1 全员可见（MENU 无 roles 限制）
