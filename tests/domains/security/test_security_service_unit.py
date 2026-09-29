"""security audit 写口往返（sqlite 单测底座——99 §4.1 测试替身策略）。

覆盖：四槽落库与 D3 面投影（正文不出门）、Actor/「系统」两型 who、
调用方事务内追加（同事务留痕——B12）、倒序分页（R3 total）、B12 唯一
写口的结构断言（store 无 update/delete 出口）、表结构与 99 §2.1 逐字段。
PG 真库集成见 test_security_audit_pg.py。
"""

import dataclasses
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.security import AuditFilter, AuditRow, SecurityService, resolve_actor
from app.domains.security.domain import AuditLogView, audit_digest
from app.domains.security.store import AuditLog, AuditLogStore, ensure_audit_table
from app.infra.clock import ISO_FMT, freeze, set_clock
from app.infra.crypto import sm3_digest
from app.infra.db import ConnectionManager, DatabaseSpec, Repository


@pytest.fixture
async def db(tmp_path: Path) -> AsyncIterator[ConnectionManager]:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "security-unit.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    engine = create_async_engine(spec.url())
    await ensure_audit_table(engine)
    await engine.dispose()
    yield manager
    await manager.dispose()


async def _all_rows(db: ConnectionManager) -> list[AuditLog]:
    async with db.session() as session:
        rows = (
            (await session.execute(select(AuditLog).order_by(AuditLog.id))).scalars().all()
        )
    return list(rows)


# ---------- 写口往返：四槽落库、digest 应用层写入、正文不出读面 ----------


async def test_audit_roundtrip_four_slots_and_digest(db: ConnectionManager) -> None:
    with freeze("2026-09-29T10:00:00"):
        row = AuditRow(
            who="小李 · 地质/质检",
            action="kb.library_config.saved",
            content="库配置保存（下次入库定型）",
            meta={"trace_id": "call-8c31"},
        )
        async with db.transaction():
            service = SecurityService(db)
            await service.audit(row)
        expected_digest = audit_digest(row)  # 冻结语境内的指纹（写入口径）

    async with db.session() as session:
        entity = (await session.execute(select(AuditLog))).scalar_one()
    assert entity.time == datetime(2026, 9, 29, 10, 0, 0)  # 时间槽＝冻结时钟（B14）
    assert entity.who == "小李 · 地质/质检"  # 操作者槽
    assert entity.action == "kb.library_config.saved"  # 动作槽
    assert entity.content == "库配置保存（下次入库定型）"  # 内容槽落库
    assert entity.digest == expected_digest  # SM3 应用层写入（99 §1.7.3）
    assert entity.meta == {"trace_id": "call-8c31"}  # jsonb 预留位
    assert entity.created_at == entity.updated_at == entity.time  # 基线列＝写入时刻（无更新通路）


async def test_time_digest_and_baseline_share_one_clock_read(db: ConnectionManager) -> None:
    """回归（P0-04 审查 P2-1）：time/digest/基线列同源于一次取时。

    时钟逐秒行走时，digest 的时间槽与落库 time 不许跨秒错位——digest 按
    落库四槽复算恒合（旧实现 time 与 digest 两次独立读钟，审查实测复现
    错位；created_at/updated_at 列缺省是第三处独立读钟，同样收口）。
    """
    base = datetime(2026, 9, 29, 10, 0, 0)
    ticks = 0

    def ticking() -> datetime:
        nonlocal ticks
        ticks += 1
        return base + timedelta(seconds=ticks)  # 每次读钟走一秒——冻结时钟测不出此错位

    previous = set_clock(ticking)
    try:
        service = SecurityService(db)
        await service.audit(AuditRow(who="系统", action="probe.ticking", content="时钟行走"))
    finally:
        set_clock(previous)

    async with db.session() as session:
        entity = (await session.execute(select(AuditLog))).scalar_one()
    canonical = f"{entity.time.strftime(ISO_FMT)}|{entity.who}|{entity.action}|{entity.content}"
    assert entity.digest == sm3_digest(canonical)  # digest 时间槽＝落库 time（同一次取时）
    assert entity.created_at == entity.updated_at == entity.time  # 三时间一源（无更新通路）


def test_d3_view_projection_never_carries_content() -> None:
    # 结构断言：D3 面 time/who/action/digest 四列形——「digest 永不落正文」（00 §8.1）。
    assert [f.name for f in dataclasses.fields(AuditLogView)] == [
        "time",
        "who",
        "action",
        "digest",
    ]


async def test_audit_accepts_actor_who_and_system_who(db: ConnectionManager) -> None:
    service = SecurityService(db)
    actor = resolve_actor("xiaoli")
    with freeze("2026-09-29T10:00:00"):
        await service.audit(AuditRow(who=actor.who, action="kb.report.viewed", content="读报告"))
        await service.audit(
            AuditRow(who="系统", action="quality.rule.autorun", content="低风险自动执行")  # 00 §2.2
        )
    rows = await _all_rows(db)
    assert [r.who for r in rows] == [actor.display, "系统"]


async def test_audit_append_in_caller_transaction_rolls_back_with_it(db: ConnectionManager) -> None:
    service = SecurityService(db)
    with freeze("2026-09-29T10:00:00"):
        async with db.transaction() as session:
            await service.audit(
                AuditRow(who="系统", action="kept", content="同事务提交"), session=session
            )
        with pytest.raises(RuntimeError, match="abort"):
            async with db.transaction() as session:
                await service.audit(
                    AuditRow(who="系统", action="dropped", content="同事务回滚"), session=session
                )
                raise RuntimeError("abort")
    rows = await _all_rows(db)
    assert [r.action for r in rows] == ["kept"]  # 留痕随调用方事务同生同灭（B12 同事务形状）


# ---------- 读面：倒序分页与筛选（R3 total＝筛选后） ----------


async def _seed_three(db: ConnectionManager) -> SecurityService:
    service = SecurityService(db)
    with freeze("2026-09-29T10:00:00"):
        for i, (who, action) in enumerate(
            [
                ("阿强 · 平台运维", "security.query_policy.saved"),
                ("小李 · 地质/质检", "kb.report.uploaded"),
                ("阿强 · 平台运维", "security.outbound_policy.saved"),
            ]
        ):
            await service.audit(AuditRow(who=who, action=action, content=f"第{i}条"))
    return service


async def test_audit_logs_orders_time_desc_then_id_desc(db: ConnectionManager) -> None:
    service = await _seed_three(db)
    page = await service.audit_logs(page_size=20)
    # 同一冻结时刻三行——time desc 后按 id desc 决胜（分页确定性）。
    assert [v.action for v in page.items] == [
        "security.outbound_policy.saved",
        "kb.report.uploaded",
        "security.query_policy.saved",
    ]
    assert (page.total, page.page, page.page_size) == (3, 1, 20)


async def test_audit_logs_pagination_and_filter(db: ConnectionManager) -> None:
    service = await _seed_three(db)

    page2 = await service.audit_logs(page=2, page_size=2)
    assert [v.action for v in page2.items] == ["security.query_policy.saved"]
    assert page2.total == 3  # total＝当前筛选条件总数（R3），非本页条数

    by_who = await service.audit_logs(AuditFilter(who="阿强 · 平台运维"))
    assert by_who.total == 2  # 筛选后总数
    assert {v.action for v in by_who.items} == {
        "security.outbound_policy.saved",
        "security.query_policy.saved",
    }

    by_action = await service.audit_logs(AuditFilter(action="kb.report.uploaded"))
    assert by_action.total == 1


# ---------- B12 唯一写口：结构层面说明（票面约定） ----------


def test_b12_write_surface_is_unique() -> None:
    # ① service 公开面＝audit（唯一写口）＋audit_logs（读口）——无第三写路径。
    service_surface = {
        name for name, _ in vars(SecurityService).items() if not name.startswith("_")
    }
    assert service_surface == {"audit", "audit_logs"}
    # ② store 公开面只有 append/append_in（写）与 page（读）——刻意不继承
    #    Repository（通用 CRUD 基类带 add/delete 面），append-only 无 UPDATE/DELETE 出口。
    store_surface = {name for name, _ in vars(AuditLogStore).items() if not name.startswith("_")}
    assert store_surface == {"append", "append_in", "page"}
    assert not issubclass(AuditLogStore, Repository)
    # ③ 写 audit_log 的代码只存在于 app/domains/security 包内（store.append[_in]
    #    是仅有的 INSERT 路径）——其他模块经各自聚合内嵌留痕子表落痕（B12 双轨）；
    #    新增写路径＝违反 B12，审查即拒（义务声明见 store.py 模块 docstring）。


# ---------- 表结构与 99 §2.1 逐字段 ----------


def test_audit_table_matches_99_schema() -> None:
    table = AuditLog.__table__
    assert table.name == "audit_log"
    assert {c.name for c in table.columns} == {
        "id",  # bigserial
        "time",  # timestamp 无时区
        "who",
        "action",
        "content",
        "digest",  # SM3 hex 64
        "meta",  # jsonb（sqlite 底座 JSON 文本替身）
        "created_at",  # 基线列（99 §2 卷首）
        "updated_at",
    }
    assert table.c.id.primary_key and table.c.id.autoincrement
    # 方言渲染抽查（公开编译面）：PG 取 BIGINT（建表时随 PK 自增渲染 BIGSERIAL，
    # 真库断言见 PG 集成测试）；sqlite 底座取 INTEGER（rowid 别名自增前提）。
    assert table.c.id.type.compile(postgresql.dialect()) == "BIGINT"
    assert table.c.id.type.compile(sqlite.dialect()) == "INTEGER"
    assert not table.c.time.type.timezone  # 99 §1.7.4：timestamp 无时区
    assert table.c.digest.type.length == 64  # SM3 hex 64
    assert table.c.meta.type.compile(postgresql.dialect()) == "JSONB"
    assert table.c.meta.type.compile(sqlite.dialect()) == "JSON"

    # idx(time desc)——99 §2.1（text 形索引表达式，PG/SQLite 双方言可用）
    index = {ix.name: ix for ix in table.indexes}["ix_audit_log_time_desc"]
    assert "time desc" in str(index.expressions[0]).lower()


def test_audit_digest_canonical_smoke() -> None:
    row = AuditRow(
        who="系统", action="probe", content="口径抽查", at=datetime(2026, 9, 29, 10, 0, 0)
    )
    assert audit_digest(row) == sm3_digest("2026-09-29T10:00:00|系统|probe|口径抽查")
