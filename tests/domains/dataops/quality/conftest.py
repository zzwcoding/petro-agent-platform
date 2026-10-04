"""dataops.quality 测试共享夹具：sqlite 底座（真 QualityService——管理面无外缝，
唯 rescan 执行缝按测试注入替身/缺省 None 两态）。"""

from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import pytest
from sqlalchemy import select

from app.domains.dataops.quality import QualityService, ensure_quality_tables
from app.domains.dataops.quality.domain import (
    RESCAN_GREEN_NOTE,
    RescanExecutor,
    RescanOutcome,
    RescanRequest,
)
from app.domains.dataops.quality.store import (
    QualityIssue,
    QualityIssueTransition,
    QualityRule,
    QuarantineRow,
    WaterLine,
)
from app.infra.db import ConnectionManager, DatabaseSpec


async def seed_rule(
    db: ConnectionManager,
    no: int,
    *,
    kind: str = "重复",
    rule: str = "规则原文",
    crit: str = "判据",
    enabled: bool = True,
    action: str = "告警",
    autofix: bool = False,
) -> None:
    """规则行直插（sqlite 单测底座——20 条种子真值对账归 PG 测试消费真迁移）。"""
    async with db.session() as session:
        session.add(
            QualityRule(
                no=no, kind=kind, rule=rule, crit=crit,
                enabled=enabled, action=action, autofix=autofix,
            )
        )


@pytest.fixture
async def quality_db(tmp_path: Any) -> AsyncIterator[ConnectionManager]:
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "quality.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_quality_tables(manager.engine())
    yield manager
    await manager.dispose()


@pytest.fixture
def service(quality_db: ConnectionManager) -> QualityService:
    """缺省服务（rescan 执行缝未接——501 壳语义即被测对象之一）。"""
    return QualityService(quality_db)


async def add_issue(db: ConnectionManager, **kwargs: Any) -> QualityIssue:
    """问题单直插（id/lane/rule_no/dedupe_key 必带；其余缺省空——created_at 缺省当前钟）。"""
    kwargs.setdefault("title", None)
    kwargs.setdefault("desc", None)
    kwargs.setdefault("owner", None)
    kwargs.setdefault("ai_note", None)
    kwargs.setdefault("verify", None)
    kwargs.setdefault("close_note", None)
    async with db.session() as session:
        row = QualityIssue(**kwargs)
        session.add(row)
        await session.flush()
        return row


async def add_quarantine(
    db: ConnectionManager, **kwargs: Any
) -> QuarantineRow:
    """隔离行直插（batch_id/rule_no/action/payload 必带；loc/issue_id 缺省空）。"""
    kwargs.setdefault("loc", None)
    kwargs.setdefault("issue_id", None)
    async with db.session() as session:
        row = QuarantineRow(**kwargs)
        session.add(row)
        await session.flush()
        return row


async def add_water_line(
    db: ConnectionManager, layer: str, data_date: str
) -> None:
    """水位行直插（layer 主键——同层覆盖语义由调用方保证）。"""
    async with db.session() as session:
        existing = await session.get(WaterLine, layer)
        if existing is not None:
            existing.data_date = date.fromisoformat(data_date)
        else:
            session.add(WaterLine(layer=layer, data_date=date.fromisoformat(data_date)))


async def rule_rows(db: ConnectionManager) -> list[QualityRule]:
    async with db.readonly() as session:
        rows = (
            await session.execute(select(QualityRule).order_by(QualityRule.no))
        ).scalars().all()
        return list(rows)


async def issue_rows(db: ConnectionManager) -> list[QualityIssue]:
    async with db.readonly() as session:
        result = await session.execute(select(QualityIssue).order_by(QualityIssue.id))
        return list(result.scalars().all())


async def transition_rows(
    db: ConnectionManager, issue_id: str
) -> list[QualityIssueTransition]:
    async with db.readonly() as session:
        rows = (
            await session.execute(
                select(QualityIssueTransition)
                .where(QualityIssueTransition.issue_id == issue_id)
                .order_by(QualityIssueTransition.seq)
            )
        ).scalars().all()
        return list(rows)


# 复扫执行缝替身（green 固定全绿；red 携明细——替身纪律：只许测试替身）
def green_executor(batch: str = "批次 20260922-T1") -> RescanExecutor:
    async def _exec(request: RescanRequest) -> RescanOutcome:
        return RescanOutcome(batch=batch, green=True)

    return _exec


def red_executor(
    batch: str = "批次 20260922-T1", detail: str = "规则 8 仍命中 1 行"
) -> RescanExecutor:
    async def _exec(request: RescanRequest) -> RescanOutcome:
        return RescanOutcome(batch=batch, green=False, detail=detail)

    return _exec


__all__ = [
    "RESCAN_GREEN_NOTE",
    "add_issue",
    "add_quarantine",
    "add_water_line",
    "green_executor",
    "issue_rows",
    "quality_db",
    "red_executor",
    "rule_rows",
    "seed_rule",
    "service",
    "transition_rows",
]
