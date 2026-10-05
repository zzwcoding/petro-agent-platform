"""quality 表族 PG16 集成——DP-05 真迁移 0015 消费（种子投影对账＋管理面语义实跑）。

跑法：TEST_DATABASE_URL=postgresql://...@localhost:5433/petro uv run pytest
tests/domains/dataops/quality/test_quality_tables_pg.py -q（未配置即 skip——
约定见票面）。测试自动落 <库名>_test 独立库；表结构/种子＝**真迁移 0015**
程序化执行（importlib 装载版本文件＋Operations.context——非 ORM 仿造，
DP-05 交付物原样消费）。

覆盖：规则种子 20 条逐项对账（E2 v0.5 冻结值——1-12 启用判据/13-20 仅登记
enabled=false/autoFix 白名单恰 7/8/v0.4 本体对齐行 1/5/6/11）；五态状态机
PG 实跑（挂单语义→流转全路径→rescan 替身回填→关闭守卫/终态 409）；水位
T-1 判定；隔离区 append-only 读＋CHECK 约束实证（PG 侧）。
"""

import asyncio
import importlib.util
import os
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.dataops.quality import (
    RESCAN_GREEN_NOTE,
    QualityCloseBlockedError,
    QualityIssueStateError,
    QualityService,
    QualityTaskNotFoundError,
    QualityTaskRunningError,
    TransitionReceipt,
    bind_channel_rescan,
)
from app.domains.dataops.quality.domain import QrowView
from app.domains.dataops.quality.store import QualityStore, QualityTask, QuarantineRow, WaterLine
from app.infra.clock import freeze
from app.infra.db import ConnectionManager, DatabaseSpec
from tests.domains.dataops.quality.conftest import (
    add_water_line,
    finish_like_data_plane,
    green_executor,
    issue_rows,
    transition_rows,
)

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

_MIGRATION_0015 = (
    Path(__file__).resolve().parents[4]
    / "migrations" / "versions" / "20261004_0015_quality_waterline.py"
)

# 0015 六表（downgrade 依赖逆序——用例间复位即全清重灌）
_MIGRATION_TABLES = (
    "quarantine_row", "quality_issue_transition", "quality_issue",
    "quality_task", "water_line", "quality_rule",
)


async def _reset_tables(url: URL) -> None:
    """用例间复位（retrieval PG fixture 同款——DROP IF EXISTS CASCADE 后重灌）。"""
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            for table in _MIGRATION_TABLES:
                await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
    finally:
        await engine.dispose()


def _isolated_url() -> URL:
    url = make_url(TEST_DATABASE_URL)
    return url.set(database=f"{url.database}_test")


async def _ensure_test_database(url: URL) -> None:
    admin = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = (
                await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": url.database},
                )
            ).scalar()
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        await admin.dispose()


def _load_migration(path: Path) -> Any:
    """版本文件名以日期开头非合法标识符——importlib 文件位装载。"""
    spec = importlib.util.spec_from_file_location("m0015_quality_waterline", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _apply_migration_0015(url: URL) -> None:
    """真迁移 0015 upgrade() 程序化执行（Operations.context 桥 alembic.op 代理）。"""
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            def _upgrade(sync_conn: Any) -> None:
                context = MigrationContext.configure(sync_conn)
                with Operations.context(context):
                    _load_migration(_MIGRATION_0015).upgrade()

            await conn.run_sync(_upgrade)
    finally:
        await engine.dispose()


def _spec(url: URL) -> DatabaseSpec:
    return DatabaseSpec(
        name="primary", role="primary", driver=url.drivername.split("+", 1)[0],
        host=url.host or "localhost", port=url.port or 5433,
        database=url.database or "", user=url.username or "",
        password=url.password or "", pool_size=2, max_overflow=1,
    )


@pytest.fixture
async def manager() -> AsyncIterator[ConnectionManager]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL 未配置——PG 集成测试跳过（约定见票面）")
    if not _MIGRATION_0015.is_file():
        raise RuntimeError(f"DP-05 迁移件缺失：{_MIGRATION_0015}")
    url = _isolated_url()
    await _ensure_test_database(url)
    await _reset_tables(url)
    await _apply_migration_0015(url)
    instance = ConnectionManager([_spec(url)])
    yield instance
    await instance.dispose()


# ---------- (a) 规则种子投影对账（E2 v0.5 冻结值 × DP-05 真迁移） ----------

# 1-12 判据冻结值（E2 端点 1 DTO＋v0.4 本体对齐——0015 _RULE_SEED 逐字）
_IMPLEMENTED_CRIT: dict[int, str] = {
    1: "班次三元组（井,日,班次）唯一；重复/缺失行进问题单人工复核，不静默去重",
    2: "非空率 ≥ 99.5%",
    3: "折算密度 ∈ [0.82, 0.98]",
    4: "偏差 ≤ 5 个百分点",
    5: "越界即 fail；矛盾行清单制",
    6: "≤ T-5；超窗不拒收转问题单",
    7: "归一表全命中",
    8: "映射表全命中",
    9: "主键唯一＋迁移合法",
    10: "连续 30 日同值 → 告警",
    11: "当日批内全零 → 告警",
    12: "偏差 ≤ 3%",
}
_REGISTRY_KIND: dict[int, str] = {
    13: "引用完整", 14: "跨表一致", 15: "枚举合法", 16: "正则格式",
    17: "极值", 18: "波动率", 19: "钩稽", 20: "洗数规则",
}


class TestRuleSeedProjection:
    async def test_twenty_rules_with_v05_freeze_values(
        self, manager: ConnectionManager
    ) -> None:
        service = QualityService(manager)
        rules = await service.list_rules()
        assert [r.no for r in rules] == list(range(1, 21))  # 20 条种子全投影
        assert all(r.enabled for r in rules if r.no <= 12)  # 1-12 实施
        assert not any(r.enabled for r in rules if r.no >= 13)  # 13-20 仅登记不实施
        assert {r.no for r in rules if r.auto_fix} == {7, 8}  # autoFix 白名单（v0.4 收窄）
        assert all(r.action == "—（总册）" for r in rules if r.no >= 13)
        assert {r.no: r.crit for r in rules if r.no <= 12} == _IMPLEMENTED_CRIT
        assert {r.no: r.kind for r in rules if r.no >= 13} == _REGISTRY_KIND
        # v0.4 本体对齐行（权威源＝本体 M3 RULE-BOHAI-030/023/025/038——E2 行为约定 9）
        by_no = {r.no: r for r in rules}
        assert by_no[1].action == "告警"  # 规则 1＝RULE-BOHAI-030（隔离→告警，不静默去重）
        assert by_no[5].action == "告警"  # 规则 5＝RULE-BOHAI-023（矛盾行清单制）
        assert by_no[6].action == "告警"  # 规则 6＝RULE-BOHAI-025（T-5 不拒收转问题单）
        assert by_no[11].action == "告警"  # 规则 11＝RULE-BOHAI-038（批面近似）
        # action 值域＝命中动作三档＋总册占位（CHECK 约束同域）
        assert {r.action for r in rules} <= {"隔离", "整批拒收", "告警", "—（总册）"}

    async def test_toggle_persists_and_read_reflects(
        self, manager: ConnectionManager
    ) -> None:
        service = QualityService(manager)
        await service.set_rule_enabled(3, False)
        rules = {r.no: r for r in await service.list_rules()}
        assert rules[3].enabled is False
        # 复位（种子态还原——用例互不污染）
        await service.set_rule_enabled(3, True)
        rules = {r.no: r for r in await service.list_rules()}
        assert rules[3].enabled is True


# ---------- (b) 五态状态机 PG 实跑（挂单→流转→rescan→关闭守卫） ----------


class TestStateMachineOnPg:
    async def test_full_lifecycle(self, manager: ConnectionManager) -> None:
        service = QualityService(manager)
        # 命中登记→建单（初始态分发）→挂同单→五态流转→复扫→关闭
        first = await service.register_hit(
            rule_no=8, object_key="EQUIP-01", data_date="2026-09-14",
            title="规则 8 · 停机原因码旧码未映射",
            owner="责任：作业区资料员",
        )
        assert (first.attached, first.lane) == (False, 0)
        again = await service.register_hit(
            rule_no=8, object_key="EQUIP-01", data_date="2026-09-14", title="重跑命中",
        )
        assert (again.attached, again.hit_count) == (True, 2)

        for lane in (1, 2, 3):
            receipt = await service.transition_issue(first.issue_id, "小李 · 地质/质检")
            assert receipt.lane == lane
        assert receipt.verify is None  # 推进「复核」仅登记待复扫
        # 关闭守卫：verify 仍空且无 close_note → 422 拒收（合同冻结码）
        with pytest.raises(QualityCloseBlockedError):
            await service.transition_issue(first.issue_id, "小李 · 地质/质检")

        executor_service = QualityService(manager, rescan_executor=green_executor())
        rescanned = await executor_service.transition_issue(
            first.issue_id, "小李 · 地质/质检", action="rescan"
        )
        assert rescanned.lane == 3  # 复扫不是流转
        assert rescanned.verify is not None
        assert rescanned.verify.note == RESCAN_GREEN_NOTE

        closed = await executor_service.transition_issue(first.issue_id, "小李 · 地质/质检")
        assert closed.lane == 4
        with pytest.raises(QualityIssueStateError):
            await executor_service.transition_issue(first.issue_id, "小李 · 地质/质检")

    async def test_issue_list_qrows_join_on_pg(self, manager: ConnectionManager) -> None:
        service = QualityService(manager)
        hit = await service.register_hit(
            rule_no=8, object_key="EQUIP-02", data_date="2026-09-14",
            title="规则 8 · 停机原因码旧码未映射",
            owner="责任：作业区资料员",
        )
        async with manager.session() as session:
            session.add(
                QuarantineRow(
                    batch_id="QT-20260914-01", rule_no=8, action="隔离",
                    loc="设备状态 equip_status",
                    payload={"code": "R3", "note": "停机原因旧码 R3 未按映射表换成 BELT"},
                    issue_id=hit.issue_id,
                )
            )
        page = await service.list_issues(rule_no=8)
        row = page.items[0]
        assert row.qrows == [
            QrowView(loc="设备状态 equip_status", note="停机原因旧码 R3 未按映射表换成 BELT")
        ]

    async def test_concurrent_transition_single_winner_on_pg(
        self, manager: ConnectionManager
    ) -> None:
        """并发两流转不同时成功（M-07 F-02——FOR UPDATE 行锁＋锁内复检）。

        两路各持同一受理快照（get_issue 桩固化同窗＝真实并发的「读后写前被
        对手方推进」）并发进场：PG 行锁串行化后，后到路锁内复检发现 lane 已动
        → 409 拒绝——不双写、不留痕（丢更新/两张同距留痕行零发生）。
        """
        service = QualityService(manager)
        hit = await service.register_hit(
            rule_no=8, object_key="EQUIP-01", data_date="2026-09-14",
            title="规则 8 · 停机原因码旧码未映射",
        )
        assert hit.attached is False
        snapshot = await service._store.get_issue(hit.issue_id)
        assert snapshot is not None and int(snapshot.lane) == 0

        async def _stale_get(issue_id: str) -> Any:
            return snapshot  # 两路同窗：各持同一份对手方提交前的快照

        service._store.get_issue = _stale_get  # type: ignore[method-assign]
        results = await asyncio.gather(
            service.transition_issue(hit.issue_id, "小李 · 地质/质检"),
            service.transition_issue(hit.issue_id, "小李 · 地质/质检"),
            return_exceptions=True,
        )
        receipts = [r for r in results if isinstance(r, TransitionReceipt)]
        conflicts = [r for r in results if isinstance(r, QualityIssueStateError)]
        assert len(receipts) == 1 and len(conflicts) == 1  # 并发两流转不同时成功
        assert receipts[0].lane == 1
        rows = await issue_rows(manager)
        assert len(rows) == 1 and rows[0].lane == 1  # 只推进一次
        trace = await transition_rows(manager, hit.issue_id)
        assert [(r.from_lane, r.to_lane) for r in trace] == [(0, 1)]  # 恰一张留痕行


# ---------- (c) 水位 T-1 判定（PG 真列形 Date） ----------


class TestFreshnessOnPg:
    async def test_water_line_rows_judged(self, manager: ConnectionManager) -> None:
        await add_water_line(manager, "原始层", "2026-09-14")
        await add_water_line(manager, "清洗层", "2026-09-14")
        await add_water_line(manager, "汇总层", "2026-09-11")
        service = QualityService(manager)
        with freeze("2026-09-15 08:00:00"):
            views = await service.freshness()
        assert [(v.layer, v.tag, v.color) for v in views] == [
            ("原始层", "达标（承诺 T-1）", "green"),
            ("清洗层", "达标（承诺 T-1）", "green"),
            ("汇总层（问数用）", "落后 3 天 · 超期", "gold"),
        ]
        assert all(v.promise == "T-1" for v in views)  # promise 常量（DP-05 列默认）

    async def test_layer_check_constraint_enforced(self, manager: ConnectionManager) -> None:
        # PG 侧 CHECK（0015 ck_water_line_layer）实证——非法 tier 拒收
        # （pytest.raises 包在会话外——异常穿透 ctx 管理器触发回滚，不留脏会话）
        with pytest.raises(IntegrityError):
            async with manager.session() as session:
                session.add(WaterLine(layer="明细层", data_date=date(2026, 9, 14)))
                await session.flush()


# ---------- (d) 隔离区 append-only 读（PG 真列形＋CHECK） ----------


class TestQuarantineOnPg:
    async def test_filter_by_rule_and_action_domain_check(
        self, manager: ConnectionManager
    ) -> None:
        service = QualityService(manager)
        async with manager.session() as session:
            session.add(
                QuarantineRow(
                    batch_id="QT-20260914-01", rule_no=1, action="隔离",
                    loc="生产日报 · N-02 · 2026-09-14", payload={"oil": 12.4},
                )
            )
        rows = await service.list_quarantine(batch_id="QT-20260914-01", rule_no=1)
        assert rows[0].action == "隔离" and rows[0].loc == "生产日报 · N-02 · 2026-09-14"
        assert rows[0].payload == {"oil": 12.4}  # 坏行原样（append-only 读面）
        assert rows[0].created_at != ""  # 展示串已拼装（格式见 sqlite API 测试）
        # CHECK（ck_quarantine_row_action）——告警类不产生隔离行，写入域即拒
        with pytest.raises(IntegrityError):
            async with manager.session() as session:
                session.add(
                    QuarantineRow(
                        batch_id="QT-20260914-01", rule_no=10, action="告警", payload={},
                    )
                )
                await session.flush()


# ---------- (e) 任务执行通道 PG 实跑（M-05b——真 0015 quality_task 行形＋条件认领原子闸） ----------

_DP_REPORT = {
    "range": "生产库 8 表",
    "tables": {"oil_production_daily": 3},
    "scanned_rows": 12604,
    "rules_run": 2,
    "quarantined_rows": 1,
    "rejected_batches": 0,
    "hits": [{
        "rule_no": 8, "kind": "写法不统一", "action": "隔离",
        "hit_count": 1, "sample": [{"equip_id": "EQUIP-01", "code": "R3"}],
    }],
    "verdict": "质检完成：2 条启用规则——问题单建单与责任岗分发归主平台 E2 接续",
}


async def _running_step0(manager: ConnectionManager) -> str | None:
    async with manager.readonly() as session:
        stmt = select(QualityTask.id).where(
            QualityTask.status == "running", QualityTask.step == 0
        )
        return (await session.execute(stmt)).scalars().first()


class TestTaskChannelOnPg:
    async def test_accept_followup_and_history(self, manager: ConnectionManager) -> None:
        service = QualityService(manager)
        receipt = await service.accept_task()
        assert receipt.rules_count == 12  # 0015 种子启用集（1-12 实施）
        row = await QualityStore(manager).get_task(receipt.task_id)
        assert row is not None
        assert (row.status, row.step, row.rules_count) == ("running", 0, 12)
        # 单任务闸（合同端点 3 重入 409）＋quality_task status CHECK 实证
        with pytest.raises(QualityTaskRunningError):
            await service.accept_task()
        with pytest.raises(IntegrityError):
            async with manager.session() as session:
                session.add(QualityTask(id="QT-X-99", status="failed", time=row.time))
                await session.flush()
        # 数据面管道替身执行（隔离行落表＋报告 1:1 完任务——同批次 id）
        async with manager.session() as session:
            session.add(QuarantineRow(
                batch_id=receipt.task_id, rule_no=8, action="隔离",
                loc="设备状态 · EQUIP-01",
                payload={"equip_id": "EQUIP-01", "code": "R3", "note": "旧码 R3"},
            ))
        await finish_like_data_plane(
            manager, receipt.task_id, report=_DP_REPORT, hits=1
        )
        view = await service.get_task(receipt.task_id)
        assert view.status == "done" and view.step == 4  # E2 接续（条件认领原子闸）
        assert view.followup is not None
        assert (view.followup.created, view.followup.rows_linked) == (1, 1)
        assert view.task is not None and view.task.report is not None
        assert view.task.report["scanned"] == "12,604 行"
        page = await service.list_issues(rule_no=8)
        fresh = [i for i in page.items if i.id.startswith("d")]
        assert len(fresh) == 1 and fresh[0].lane == 0
        # 条件认领闸：step=4 后再认领＝False（幂等不重复建单）
        async with manager.session() as session:
            assert not await QualityStore.claim_task_followup(session, receipt.task_id)
        # 历史（端点 5 倒序）＋未知任务 404
        history = await service.list_tasks()
        assert [t.id for t in history] == [receipt.task_id]
        with pytest.raises(QualityTaskNotFoundError):
            await service.get_task("QT-19700101-01")

    async def test_rescan_channel_green_with_worker_pickup(
        self, manager: ConnectionManager
    ) -> None:
        service = QualityService(manager)
        hit = await service.register_hit(
            rule_no=8, object_key="equip_id=EQUIP-01;code=R3", data_date="",
            title="规则 8 · 写法不统一 · EQUIP-01 · R3",
        )
        await service.transition_issue(hit.issue_id, "小李")
        await service.transition_issue(hit.issue_id, "小李")
        await service.transition_issue(hit.issue_id, "小李")  # 复核态
        bind_channel_rescan(service, manager)

        async def worker() -> None:
            for _ in range(400):
                task_id = await _running_step0(manager)
                if task_id is not None:
                    await finish_like_data_plane(
                        manager, task_id,
                        report={**_DP_REPORT, "hits": [{
                            "rule_no": 8, "kind": "写法不统一", "action": "隔离",
                            "hit_count": 1,
                            "sample": [{"equip_id": "EQUIP-99", "code": "R3"}],
                        }]},
                        hits=1,
                    )
                    return
                await asyncio.sleep(0.01)
            raise AssertionError("拾取替身超时")

        pick = asyncio.ensure_future(worker())
        receipt = await service.transition_issue(hit.issue_id, "小李", action="rescan")
        await pick
        assert receipt.lane == 3
        assert receipt.verify is not None
        assert receipt.verify.note == RESCAN_GREEN_NOTE  # F2 哨兵同词表（PG 侧）
