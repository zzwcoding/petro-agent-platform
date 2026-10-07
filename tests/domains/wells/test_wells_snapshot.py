"""DE-01 湖当前版快照解析器单测——三态语义逐态断言＋warning 一次＋取数路径钉死。

纯函数面（resolve_current_snapshot 三态）无 DB、无框架（B1）；薄查询面
（LakeSnapshotReader）以假 ConnectionManager（readonly 缝替身——infra.db
「测试替身：消费方只依赖 ConnectionManager」惯例）注入断言三态与日志；
PG16 实账本集成＋midplatform 授权面对账见 test_wells_snapshot_pg.py
（TEST_DATABASE_URL 门控，同仓 PG 测试约定）。
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

import pytest
from asyncpg.exceptions import UndefinedTableError
from sqlalchemy.exc import ProgrammingError

from app.domains.wells.snapshot import (
    LakeSnapshotReader,
    SnapshotLedgerRow,
    resolve_current_snapshot,
)

_LOGGER_NAME = "app.domains.wells.snapshot"


def _ledger(*pairs: tuple[int, str]) -> list[SnapshotLedgerRow]:
    return [SnapshotLedgerRow(snapshot_id=sid, batch_id=batch) for sid, batch in pairs]


# ---------- 纯函数三态（无 DB） ----------


def test_pure_multi_batch_picks_latest() -> None:
    """多批→最新批（snapshot_id 最大；入参乱序也取最大——不依赖查询排序）。"""
    face = resolve_current_snapshot(
        _ledger((1, "batch-a"), (5, "batch-c"), (3, "batch-b")), "well_info"
    )
    assert face is not None
    assert face.table_name == "well_info"
    assert face.snapshot_id == 5
    assert face.batch_id == "batch-c"


def test_pure_single_batch_returns_that_batch() -> None:
    """单批→该批（demo 单批环境即此态——过滤后仍全量可见）。"""
    face = resolve_current_snapshot(_ledger((7, "batch-only")), "well_measures")
    assert face is not None
    assert face.snapshot_id == 7
    assert face.batch_id == "batch-only"


def test_pure_no_ledger_record_returns_none() -> None:
    """账本无该表记录→None＝不过滤（该表未经湖管道，读全量是合理缺省）。"""
    assert resolve_current_snapshot([], "equip_status") is None


# ---------- 薄查询替身（readonly 缝——照 infra.db 测试替身策略） ----------


class _FakeResult:
    def __init__(self, rows: list[tuple[int, str]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[int, str]]:
        return list(self._rows)


class _FakeSession:
    def __init__(self, rows: list[tuple[int, str]]) -> None:
        self._rows = rows
        self.executed: list[Any] = []

    async def execute(self, stmt: Any) -> _FakeResult:
        self.executed.append(stmt)
        return _FakeResult(self._rows)


class _FakeDb:
    """ConnectionManager 测试替身——只承载 readonly(role) 一缝（读面足够）。"""

    def __init__(self, rows: list[tuple[int, str]]) -> None:
        self._session = _FakeSession(rows)
        self.readonly_roles: list[str] = []

    @asynccontextmanager
    async def readonly(self, role: str = "primary") -> Any:
        self.readonly_roles.append(role)
        yield self._session


def _reader(rows: list[tuple[int, str]]) -> tuple[LakeSnapshotReader, _FakeDb]:
    db = _FakeDb(rows)
    return LakeSnapshotReader(db), db  # type: ignore[arg-type]


async def test_reader_multi_batch_returns_latest_via_primary_route() -> None:
    """多批→最新批；取数路径钉死 primary 只读路由（midplatform 闭世界零授权
    不承担账本读面——DE-01 红线「不扩权」）。"""
    reader, db = _reader([(1, "batch-a"), (2, "batch-b")])
    face = await reader.current_snapshot("well_info")
    assert face is not None
    assert (face.table_name, face.snapshot_id, face.batch_id) == (
        "well_info", 2, "batch-b",
    )
    assert db.readonly_roles == ["primary"]


async def test_reader_single_batch_returns_that_batch() -> None:
    reader, _db = _reader([(4, "batch-only")])
    face = await reader.current_snapshot("well_overhaul")
    assert face is not None
    assert face.snapshot_id == 4 and face.batch_id == "batch-only"


async def test_reader_no_record_returns_none_and_warns_once(caplog: Any) -> None:
    """无记录态：None＋warning 一次（同表重复调用不刷屏——每表去重一次）。"""
    reader, _db = _reader([])
    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        first = await reader.current_snapshot("equip_status")
        second = await reader.current_snapshot("equip_status")
    assert first is None and second is None
    warnings = [r for r in caplog.records if r.name == _LOGGER_NAME]
    assert len(warnings) == 1
    assert warnings[0].levelno == logging.WARNING
    assert "equip_status" in warnings[0].getMessage()


async def test_reader_warning_dedupes_per_table(caplog: Any) -> None:
    """两表各自无记录→各警告一次（去重键＝表名，不是全局一次）。"""
    reader, _db = _reader([])
    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        await reader.current_snapshot("equip_status")
        await reader.current_snapshot("fluid_test")
    messages = [r.getMessage() for r in caplog.records if r.name == _LOGGER_NAME]
    assert len(messages) == 2
    assert any("equip_status" in m for m in messages)
    assert any("fluid_test" in m for m in messages)


# ---------- FX-01：账本表本身不存在（数据面未 boot）→ None＋warning，不再 500 ----------


class _FailingSession:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def execute(self, stmt: Any) -> Any:
        raise self._error


class _FailingDb:
    """ConnectionManager 测试替身——readonly 缝里 execute 必抛给定错误。"""

    def __init__(self, error: Exception) -> None:
        self._session = _FailingSession(error)

    @asynccontextmanager
    async def readonly(self, role: str = "primary") -> Any:
        yield self._session


def _undefined_table_error() -> ProgrammingError:
    """模拟账本表缺失态的异常形态（FX-01）：asyncpg UndefinedTableError
    （SQLSTATE 42P01）被 SQLAlchemy 包装后 ``orig`` 指回驱动异常。"""
    orig = UndefinedTableError(
        'relation "data_plane.lake_snapshot" does not exist'
    )
    return ProgrammingError(
        "SELECT data_plane.lake_snapshot.snapshot_id ...", {}, orig
    )


def _failing_reader(error: Exception) -> LakeSnapshotReader:
    return LakeSnapshotReader(_FailingDb(error))  # type: ignore[arg-type]


async def test_reader_undefined_table_returns_none_and_warns_once(
    caplog: Any,
) -> None:
    """账本表不存在（undefined_table/42P01）→ 与「无记录」同归 None＋
    warning 一次（读面回落全量，不再 500——R1-02 裁决修复）。"""
    reader = _failing_reader(_undefined_table_error())
    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        first = await reader.current_snapshot("well_info")
        second = await reader.current_snapshot("well_info")
    assert first is None and second is None
    warnings = [r for r in caplog.records if r.name == _LOGGER_NAME]
    assert len(warnings) == 1
    assert warnings[0].levelno == logging.WARNING
    assert "well_info" in warnings[0].getMessage()
    assert "lake_snapshot" in warnings[0].getMessage()  # 报文点出账本表缺失


async def test_reader_undefined_table_warning_dedupes_per_table(
    caplog: Any,
) -> None:
    """账本表缺失态对两表各警告一次（去重键＝表名，与无记录态同机制）。"""
    reader = _failing_reader(_undefined_table_error())
    with caplog.at_level(logging.WARNING, logger=_LOGGER_NAME):
        await reader.current_snapshot("well_info")
        await reader.current_snapshot("well_measures")
    messages = [r.getMessage() for r in caplog.records if r.name == _LOGGER_NAME]
    assert len(messages) == 2
    assert any("well_info" in m for m in messages)
    assert any("well_measures" in m for m in messages)


async def test_reader_other_dbapi_errors_propagate() -> None:
    """非 undefined_table 的 DBAPIError（sqlstate 非 42P01）不吞——原样上抛。"""
    foreign = ProgrammingError("SELECT ...", {}, RuntimeError("backend gone"))
    reader = _failing_reader(foreign)
    with pytest.raises(ProgrammingError, match="backend gone"):
        await reader.current_snapshot("well_info")
