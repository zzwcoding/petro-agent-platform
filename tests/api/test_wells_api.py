"""A2 /api/wells 路由族 API 形状测试——错误包/权限预埋行/端点壳/响应模型。

装配：假 WellsService 注入（dependency_overrides——不触 DB；DTO 逐字段投影的
真装配验证归 tests/domains/wells/test_wells_contract_pg.py PG16 集成）。
合同锚：A2-井档案.md v0.2（端点清单/错误码草案/行为规则 1）、00 §3（错误包）。
"""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_wells
from app.api.errors import install_error_handlers
from app.api.wells import router as wells_router
from app.domains.security import Actor
from app.domains.wells import (
    ChainCounts,
    ChainView,
    ChangeTicketProjection,
    WellNotFoundError,
    WellProfile,
    WellSummary,
)


class _FakeWellsService:
    """形状验证用假服务（方法面＝WellsService 公开接口的子集）。"""

    def __init__(self) -> None:
        self.got_404 = False

    async def wells_visible(self, actor: Actor) -> list[WellSummary]:
        return [
            WellSummary(
                well_id="N-02", well_name="渤中28-1-N2", well_kind="采油",
                well_kind_code="EW", block_name="渤南", current_status="生产中",
                remark="正常",
            ),
            WellSummary(
                well_id="N-06", well_name=None, well_kind="注水",
                well_kind_code="IW", block_name="渤南", current_status="生产中",
                remark="分层注水（3 层）",
            ),
        ]

    async def well_profile(self, well_id: str, actor: Actor) -> WellProfile:
        if well_id == "N-99":
            raise WellNotFoundError(f"井不存在（归一化后无此主键）：{well_id}")
        return WellProfile(
            well_id=well_id, well_name=None, well_kind="注水", well_kind_code="IW",
            first_prod_date="2019-08-01", platform="CEP-A", block_name="渤南",
            current_status="生产中", remark="分层注水（3 层）",
            quality_notes=[], foot_note='注水井无日产油记录，"产量最高"类排名自动排除本井。',
        )

    async def well_chain(self, well_id: str, actor: Actor) -> ChainView:
        from app.domains.wells import (
            DeviceView,
            EventView,
            MeasureView,
        )

        return ChainView(
            well_id=well_id,
            counts=ChainCounts(events=1, measures=1, devices=1, overhauls=0, changes=0),
            measure_types=["压裂", "酸化", "补孔", "调剖"],
            device_types=["电泵", "螺杆泵", "加热炉"],
            measure_foot="措施类型枚举：压裂 / 酸化 / 补孔 / 调剖",
            device_foot="设备类型枚举：电泵 / 螺杆泵 / 加热炉",
            events=[
                EventView(key="m1", kind="措施", date="2026-03-18", date_end=None,
                          title="调剖 · 主力层段调剖，调整吸水剖面", outcome="综合含水降 1.2 个点"),
            ],
            measures=[
                MeasureView(key="m1", date="2026-03-18", type="调剖",
                            content="主力层段调剖，调整吸水剖面", result="综合含水降 1.2 个点"),
            ],
            devices=[
                DeviceView(key="d1", type="电泵", status="运行中", since="2021-04-12", note="n"),
            ],
            overhauls=[],
            tail=None,
        )

    async def well_change_tickets(
        self, well_id: str, actor: Actor
    ) -> ChangeTicketProjection:
        return ChangeTicketProjection(well_id=well_id, items=[], total=0)


def _client() -> TestClient:
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(wells_router)
    app.dependency_overrides[get_wells] = _FakeWellsService
    return TestClient(app)


HEADERS = {"X-Dev-User": "aqiang"}


def test_401_bad_actor() -> None:
    """身份桩：非五角色键 → 401 错误包（00 §2.3——A2 错误码草案同闸）。"""
    resp = _client().get("/api/wells", headers={"X-Dev-User": "hacker"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "security_unauthenticated"


def test_list_wells_shape() -> None:
    """端点 1：items 行七字段＋total＝过滤后计数（服务端过滤——响应外无井）。"""
    body: dict[str, Any] = _client().get("/api/wells", headers=HEADERS).json()
    assert body["total"] == 2
    assert body["items"][0] == {
        "well_id": "N-02", "well_name": "渤中28-1-N2", "well_kind": "采油",
        "well_kind_code": "EW", "block_name": "渤南", "current_status": "生产中",
        "remark": "正常",
    }
    assert body["items"][1]["well_name"] is None  # 空缺井名以 null 返回（页面渲染「—」）


def test_profile_404_error_payload() -> None:
    """井不存在 → 404 错误包 well_not_found（A2 错误码草案——世界里的判别）。"""
    resp = _client().get("/api/wells/N-99", headers=HEADERS)
    assert resp.status_code == 404
    assert resp.json()["code"] == "well_not_found"


def test_profile_foot_note_iw() -> None:
    """端点 2：卡底注记随井别派生（注水井＝冻结文案）；quality_notes 空数组。"""
    body: dict[str, Any] = _client().get("/api/wells/N-06", headers=HEADERS).json()
    assert body["well_id"] == "N-06"
    assert body["foot_note"] == '注水井无日产油记录，"产量最高"类排名自动排除本井。'
    assert body["quality_notes"] == []


def test_chain_shape() -> None:
    """端点 3：counts 五页签计数＋尾注结构化枚举＋恒返回 foot；检修行带
    date_end 键、措施行不携带（DTO 逐字段）。"""
    body: dict[str, Any] = _client().get("/api/wells/N-02/chain", headers=HEADERS).json()
    assert body["counts"] == {
        "events": 1, "measures": 1, "devices": 1, "overhauls": 0, "changes": 0,
    }
    assert body["measure_types"] == ["压裂", "酸化", "补孔", "调剖"]
    assert body["device_types"] == ["电泵", "螺杆泵", "加热炉"]
    assert body["measure_foot"] == "措施类型枚举：压裂 / 酸化 / 补孔 / 调剖"
    assert body["device_foot"] == "设备类型枚举：电泵 / 螺杆泵 / 加热炉"
    assert body["events"][0] == {
        "key": "m1", "kind": "措施", "date": "2026-03-18",
        "title": "调剖 · 主力层段调剖，调整吸水剖面", "outcome": "综合含水降 1.2 个点",
    }
    assert "date_end" not in body["events"][0]  # date_end 仅检修行携带
    assert body["measures"][0]["type"] == "调剖"
    assert body["tail"] is None


def test_change_tickets_shell() -> None:
    """端点 4 端点壳：V1（A3 主单未建）照合同形状返空列表＋total=0——不 mock 假单。"""
    body: dict[str, Any] = (
        _client().get("/api/wells/N-02/change-tickets", headers=HEADERS).json()
    )
    assert body == {"well_id": "N-02", "items": [], "total": 0}
