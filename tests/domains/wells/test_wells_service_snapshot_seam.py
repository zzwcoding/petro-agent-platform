"""DE-02 wells 服务缝单测——LakeSnapshotLoader 注入缝消费形状（无 DB——B1）。

断言面（DE-02 接线语义，store 以替身记录入参——service 内部构造 WellsStore，
monkeypatch 替换构造面，SQL 落点真实验证归 PG 集成 test_wells_snapshot_
filter_pg.py）：
- 缝已装配：三端点解析出的当前版键逐表透传 store（well_info/well_measures/
  well_overhaul 各自解析各自过滤——DE-01 解析器表名参数化的消费侧形状）；
- loader 返 None（账本无该表记录）→ 键 None＝不过滤（三态语义回落全量）；
- 缝缺省（未装配）→ 键 None＝不过滤（向后兼容——DE-01 前行为原样）；
- 井只在旧批存在（当前版世界查无）→ 404（well_not_found——不洗白成可见）；
- 平台补位表 well_status_log 不收键（不经湖管道——签名即闸，误传即 TypeError）。
"""

from typing import Any

import pytest

from app.domains.security import Actor, ForbiddenError
from app.domains.wells import LakeSnapshotFace, WellNotFoundError
from app.domains.wells import service as wells_service_module
from app.domains.wells.service import WellsService
from app.domains.wells.store import (
    MeasureLedgerRow,
    OverhaulLedgerRow,
    StatusLogLedgerRow,
    WellInfoRow,
)

_ACTOR = Actor(user_id="aqiang", display="工强（平台运维）")

# 账本替身投影：三表各返回一个不同 snapshot_id（透传对账用）
_LEDGER = {
    "well_info": LakeSnapshotFace(
        table_name="well_info", snapshot_id=42, batch_id="UT-B2"
    ),
    "well_measures": LakeSnapshotFace(
        table_name="well_measures", snapshot_id=43, batch_id="UT-M2"
    ),
    "well_overhaul": LakeSnapshotFace(
        table_name="well_overhaul", snapshot_id=44, batch_id="UT-O2"
    ),
}


class _RecordingStore:
    """WellsStore 替身——记录每次调用的 snapshot_id 入参（键透传断言面）。"""

    def __init__(self, db: Any) -> None:
        self.calls: dict[str, int | None] = {}
        self.get_well_result: WellInfoRow | None = None
        self.get_well_unfiltered_result: WellInfoRow | None = None

    async def list_wells(
        self, actor: Actor, snapshot_id: int | None = None
    ) -> list[WellInfoRow]:
        self.calls["list_wells"] = snapshot_id
        return []

    async def get_well(
        self, well_id: str, actor: Actor, snapshot_id: int | None = None
    ) -> WellInfoRow | None:
        self.calls["get_well"] = snapshot_id
        return self.get_well_result

    async def get_well_unfiltered(
        self, well_id: str, snapshot_id: int | None = None
    ) -> WellInfoRow | None:
        self.calls["get_well_unfiltered"] = snapshot_id
        return self.get_well_unfiltered_result

    async def list_measures(
        self, well_id: str, snapshot_id: int | None = None
    ) -> list[MeasureLedgerRow]:
        self.calls["list_measures"] = snapshot_id
        return []

    async def list_overhauls(
        self, well_id: str, snapshot_id: int | None = None
    ) -> list[OverhaulLedgerRow]:
        self.calls["list_overhauls"] = snapshot_id
        return []

    async def list_status_changes(self, well_id: str) -> list[StatusLogLedgerRow]:
        # 平台补位表不经湖管道——签名不带 snapshot_id（服务误传键即此处炸）
        return []


def _service(
    monkeypatch: pytest.MonkeyPatch,
    loader: Any,  # LakeSnapshotLoader | None——替身/真签名由各测试给定
) -> tuple[WellsService, _RecordingStore]:
    """生产装配形状（loader 注入构造参数）＋store 替身换入。"""
    store = _RecordingStore(db=None)
    monkeypatch.setattr(wells_service_module, "WellsStore", lambda db: store)
    return WellsService(db=None, snapshot_loader=loader), store


_ROW = WellInfoRow(("N-02", "渤中28-1-N2", "EW", None, None, None, None, None))


# loader 替身（真签名形状——Callable[[str], Awaitable[LakeSnapshotFace | None]]）


async def _ledger_loader(table: str) -> LakeSnapshotFace | None:
    """三表各有当前版批（42/43/44）的账本替身。"""
    return _LEDGER.get(table)


async def _empty_loader(table: str) -> LakeSnapshotFace | None:
    """账本全空替身（无记录态——任何表都返 None）。"""
    return None


# ---------- 缝已装配：当前版键逐表透传 ----------


async def test_face_snapshot_id_reaches_store_per_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """端点 1/2/3 解析出的当前版键逐表透传 store（各表各解析——42/43/44）。"""
    service, store = _service(monkeypatch, _ledger_loader)
    store.get_well_result = _ROW

    await service.wells_visible(_ACTOR)
    assert store.calls["list_wells"] == 42

    await service.well_profile("N-02", _ACTOR)
    assert store.calls["get_well"] == 42  # 闸与取数同键（一请求一次解析）

    await service.well_chain("N-02", _ACTOR)
    assert store.calls == {
        "list_wells": 42,
        "get_well": 42,
        "list_measures": 43,
        "list_overhauls": 44,
    }


async def test_gate_and_unfiltered_half_share_same_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """闸两半边同键（get_well 落空→get_well_unfiltered 收同一当前版键）。

    unfiltered 半边有行＝「当前版世界有井、仅行级域无权」→ 403 路径
    （真库预埋期谓词恒空走不到；替身直接落该分支——键透传照断）。"""
    service, store = _service(monkeypatch, _ledger_loader)
    store.get_well_result = None  # 过滤内无行 → 判别走 unfiltered 半边
    store.get_well_unfiltered_result = _ROW  # 当前版世界有井、仅无权 → 403

    with pytest.raises(ForbiddenError, match="N-02"):
        await service.well_profile("N-02", _ACTOR)
    assert store.calls["get_well"] == 42 and store.calls["get_well_unfiltered"] == 42


# ---------- 回落态：loader 返 None／缝未装配 → 键 None＝不过滤 ----------


async def test_loader_none_ledger_falls_back_to_unfiltered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """账本无该表记录（loader 返 None）→ 全部查询收键 None（回落全量）。"""
    service, store = _service(monkeypatch, _empty_loader)
    store.get_well_result = _ROW

    await service.wells_visible(_ACTOR)
    await service.well_profile("N-02", _ACTOR)
    await service.well_chain("N-02", _ACTOR)
    assert store.calls == {
        "list_wells": None,
        "get_well": None,
        "list_measures": None,
        "list_overhauls": None,
    }


async def test_seam_not_assembled_defaults_to_unfiltered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """缝缺省（构造不传 loader——DE-01 前装配形状）→ 键 None＝不过滤。"""
    store = _RecordingStore(db=None)
    monkeypatch.setattr(wells_service_module, "WellsStore", lambda db: store)
    service = WellsService(db=None)  # 未装配——向后兼容缺省
    store.get_well_result = _ROW

    await service.wells_visible(_ACTOR)
    await service.well_profile("N-02", _ACTOR)
    assert store.calls["list_wells"] is None and store.calls["get_well"] is None


# ---------- 当前版世界的 404 语义 ----------


async def test_well_only_in_old_batch_is_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """井只在旧批存在＝当前版世界没有 → 404（不洗白成可见）。"""
    service, store = _service(monkeypatch, _ledger_loader)
    store.get_well_result = None
    store.get_well_unfiltered_result = None  # 当前版过滤后两半边都无行

    with pytest.raises(WellNotFoundError, match="N-99"):
        await service.well_profile("N-99", _ACTOR)
