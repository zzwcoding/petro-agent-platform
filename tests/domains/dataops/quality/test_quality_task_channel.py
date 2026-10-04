"""quality 任务执行通道单测——端点 3/4/5 服务端语义（M-05b）。

sqlite 底座（conftest.quality_db）＋两层数据面替身（替身纪律：只许测试替身）：
- 管道替身 ``finish_like_data_plane``（DP-05 run_quality_task 落库语义——
  status done/step=2/报告 1:1/hits 单据数）；
- 拾取替身 ``_pickup_worker``（asyncio 协程轮询 step=0 running 行＝任务表
  轮询拾取半边的同进程模拟——DP-04 管道节奏的测试等价形）。
复扫通道＝生产适配器 DataPlaneChannelRescanExecutor 实体（非替身——替身
只替数据面拾取半边）。合同锚：E2-数据质量台.md v0.5（端点 3/4/5＋行为约定
1/2/4）；义务项锚：M-05a rev F2（哨兵同词表）/F4（并发窗）。
"""

import asyncio
from typing import Any

import pytest
from sqlalchemy import select

from app.domains.dataops.quality import (
    DISTRIBUTION_OWNER,
    RESCAN_ACTION,
    RESCAN_GREEN_NOTE,
    DataPlaneChannelRescanExecutor,
    QualityTaskNotFoundError,
    QualityTaskRunningError,
    bind_channel_rescan,
)
from app.domains.dataops.quality.domain import build_dedupe_key, rescan_note
from app.domains.dataops.quality.service import QualityService
from app.domains.dataops.quality.store import QualityStore, QualityTask, QuarantineRow
from app.infra.db import ConnectionManager
from tests.domains.dataops.quality.conftest import (
    add_issue,
    add_quarantine,
    add_task,
    finish_like_data_plane,
    issue_rows,
    seed_rule,
)

FAR_DAY = "20990101"  # 409 守卫用例的远日任务号（不与当日取号碰撞）


def _hit(rule_no: int, kind: str, action: str, sample: list[dict[str, Any]]) -> dict:
    """DP-05 报告 hits[] 条目形（机器值——rule_no/kind/action/hit_count/sample）。"""
    return {
        "rule_no": rule_no, "kind": kind, "action": action,
        "hit_count": len(sample), "sample": sample,
    }


def _report(*hits: dict[str, Any], quarantined: int = 1) -> dict[str, Any]:
    """DP-05 报告 jsonb 机器形（quarantined_rows/rejected_batches 合同键必带）。"""
    return {
        "range": "生产库 8 表",
        "tables": {"oil_production_daily": 3, "equip_status": 2},
        "scanned_rows": 12604,
        "rules_run": 2,
        "quarantined_rows": quarantined,
        "rejected_batches": 0,
        "hits": list(hits),
        "verdict": "质检完成：2 条启用规则——问题单建单与责任岗分发归主平台 E2 接续",
    }


EQUIP_SAMPLE = [{"equip_id": "EQUIP-01", "code": "R3"}]
EQUIP_HIT = _hit(8, "写法不统一", "隔离", EQUIP_SAMPLE)
WELL_HIT = _hit(
    5, "超范围", "告警",
    [{"well_id": "N-05", "prod_date": "2026-09-14", "open_days": 25}],
)


async def seed_rules(db: ConnectionManager) -> None:
    await seed_rule(db, 5, kind="超范围", crit="越界即 fail；矛盾行清单制")
    await seed_rule(db, 8, kind="写法不统一", crit="映射表全命中", action="隔离")
    await seed_rule(db, 6, kind="迟到", crit="≤ T-5；超窗不拒收转问题单")
    await seed_rule(
        db, 13, kind="引用完整", crit="详见规则库总册",
        enabled=False, action="—（总册）",
    )


async def running_step0_task_id(db: ConnectionManager) -> str | None:
    async with db.readonly() as session:
        stmt = select(QualityTask.id).where(
            QualityTask.status == "running", QualityTask.step == 0
        )
        return (await session.execute(stmt)).scalars().first()


async def pickup_worker(
    db: ConnectionManager, report: dict[str, Any], *, hits: int = 1
) -> str:
    """数据面拾取半边替身：轮询 step=0 running 行→按 DP-05 落库语义完任务。"""
    for _ in range(400):
        task_id = await running_step0_task_id(db)
        if task_id is not None:
            await finish_like_data_plane(db, task_id, report=report, hits=hits)
            return task_id
        await asyncio.sleep(0.01)
    raise AssertionError("拾取替身超时：未见 step=0 running 任务")


# ---------- 端点 3：受理 ----------


class TestAcceptTask:
    async def test_mints_running_task_with_enabled_snapshot(
        self, quality_db: ConnectionManager
    ) -> None:
        await seed_rules(quality_db)
        service = QualityService(quality_db)
        receipt = await service.accept_task()
        assert receipt.rules_count == 3  # 启用集快照（13 仅登记 enabled=false 不计）
        assert receipt.cleared == 0  # 首轮无单可撤
        row = await QualityStore(quality_db).get_task(receipt.task_id)
        assert row is not None
        assert row.status == "running" and int(row.step or 0) == 0  # 落行即触发面
        day = receipt.task_id.split("-")[1]
        assert receipt.task_id == f"QT-{day}-01"  # 当日序号 01 起（两位补零）

    async def test_reentry_409_then_seq_increments_after_done(
        self, quality_db: ConnectionManager
    ) -> None:
        await seed_rules(quality_db)
        service = QualityService(quality_db)
        first = await service.accept_task()
        with pytest.raises(QualityTaskRunningError) as err:
            await service.accept_task()
        assert first.task_id in str(err.value)  # 报文携在途任务号
        # 远日在途任务同样挡受理（单任务闸不限当日）
        await add_task(quality_db, id=f"QT-{FAR_DAY}-99")
        with pytest.raises(QualityTaskRunningError):
            await service.accept_task()
        await finish_like_data_plane(quality_db, first.task_id, report=_report(), hits=0)
        await finish_like_data_plane(
            quality_db, f"QT-{FAR_DAY}-99", report=_report(), hits=0
        )
        second = await service.accept_task()
        assert second.task_id.endswith("-02")  # 当日序号递增（任务历史不清）

    async def test_clears_only_unclaimed_dynamic_distribution(
        self, quality_db: ConnectionManager
    ) -> None:
        await seed_rules(quality_db)
        service = QualityService(quality_db)
        await add_issue(
            quality_db, id="d9", lane=0, rule_no=8,
            dedupe_key=build_dedupe_key(8, "EQUIP-OLD", "2026-09-13"),
        )
        backlink = await add_quarantine(
            quality_db, batch_id="QT-OLD", rule_no=8, action="隔离",
            payload={"equip_id": "EQUIP-OLD"}, issue_id="d9",
        )
        await add_issue(  # 预置单（p 前缀）——不受重跑影响
            quality_db, id="p8", lane=0, rule_no=8,
            dedupe_key=build_dedupe_key(8, "EQUIP-01", "2026-09-14"),
        )
        await add_issue(  # 在途动态单（整改中）——v0.5 在途单保护
            quality_db, id="d2", lane=2, rule_no=5,
            dedupe_key=build_dedupe_key(5, "N-05", "2026-09-14"),
        )
        receipt = await service.accept_task()
        assert receipt.cleared == 1  # 只撤 d9（d 前缀＋lane 0）
        rows = {row.id: row for row in await issue_rows(quality_db)}
        assert "d9" not in rows and "p8" in rows and "d2" in rows
        async with quality_db.readonly() as session:
            detached = await session.get(type(backlink), backlink.id)
            assert detached is not None and detached.issue_id is None  # 回挂摘钩
        # 复扫受理（clear_stale=False）不撤任何单
        await finish_like_data_plane(quality_db, receipt.task_id, report=_report(), hits=0)
        receipt2 = await service.accept_task(clear_stale=False)
        assert receipt2.cleared == 0
        assert {row.id for row in await issue_rows(quality_db)} == {"p8", "d2"}


# ---------- 端点 4：轮询接续（三落地同源） ----------


class TestPollFollowup:
    async def test_end_to_end_three_landings_same_source(
        self, quality_db: ConnectionManager
    ) -> None:
        await seed_rules(quality_db)
        service = QualityService(quality_db)
        receipt = await service.accept_task()
        task_id = receipt.task_id
        # 数据面管道替身执行：报告＋隔离行落表（同批次 id＝任务号——票 105 同源）
        qrow = await add_quarantine(
            quality_db, batch_id=task_id, rule_no=8, action="隔离",
            loc="设备状态 · EQUIP-01",
            payload={"equip_id": "EQUIP-01", "code": "R3", "note": "旧码 R3 未映射"},
        )
        await finish_like_data_plane(
            quality_db, task_id,
            report=_report(EQUIP_HIT, WELL_HIT, quarantined=1), hits=2,
        )
        view = await service.get_task(task_id)
        assert view.status == "done" and view.step == 4  # E2 接续完成（DP-05 偏差 2）
        assert view.followup is not None
        f = view.followup
        assert (f.created, f.attached, f.rows_linked) == (2, 0, 1)
        # 任务记录投影（合同端点 4 done 形——展示串读侧拼装）
        assert view.task is not None
        assert view.task.rules == 3 and view.task.hits == 2  # 启用集快照＋数据面单据数
        assert view.task.report is not None
        assert view.task.report["scanned"] == "12,604 行"  # 合同示例形
        assert view.task.report["quarantined_rows"] == 1
        assert view.task.report["rejected_batches"] == 0
        assert view.task.report["hits"][0].startswith("① 规则 8：")
        assert view.task.report["hits"][1].startswith("② 规则 5：")
        # 三落地同源：报告身份＝批次 id＝问题单回挂链（验收 3）
        rows = {row.id: row for row in await issue_rows(quality_db)}
        rule8 = next(
            row for row in rows.values()
            if row.dedupe_key == build_dedupe_key(8, "equip_id=EQUIP-01;code=R3", "")
        )
        rule5 = next(
            row for row in rows.values()
            if row.dedupe_key == build_dedupe_key(5, "well_id=N-05", "2026-09-14")
        )
        assert rule8.lane == 0 and rule5.lane == 0  # 初始态分发
        assert rule8.owner == DISTRIBUTION_OWNER  # 责任岗文案（原型锚）
        assert rule8.title == "规则 8 · 写法不统一 · EQUIP-01 · R3"
        assert await qrow_issue_id(quality_db, qrow.id) == rule8.id  # 隔离行身份对位回挂
        assert rule5.dedupe_key.count("|") == 2 and "2026-09-14" in rule5.dedupe_key
        # 幂等：二次轮询不重复建单（接续认领原子闸——输者直读）
        again = await service.get_task(task_id)
        assert again.followup is None
        assert again.step == 4
        assert len(await issue_rows(quality_db)) == 2

    async def test_batch_level_rejection_row_attaches_by_locators_payload(
        self, quality_db: ConnectionManager
    ) -> None:
        await seed_rules(quality_db)
        service = QualityService(quality_db)
        receipt = await service.accept_task()
        hit6 = _hit(6, "迟到", "告警", [{"batch_id": "20260911-T3"}])
        await add_quarantine(  # 整批拒收批次级记录（DP-05 载荷形 locators）
            quality_db, batch_id=receipt.task_id, rule_no=6, action="整批拒收",
            loc="检修台账 · 批次级", payload={"locators": [{"batch_id": "20260911-T3"}]},
        )
        await finish_like_data_plane(quality_db, receipt.task_id, report=_report(hit6), hits=1)
        view = await service.get_task(receipt.task_id)
        assert view.followup is not None and view.followup.rows_linked == 1
        rows = await issue_rows(quality_db)
        assert rows[0].dedupe_key == build_dedupe_key(6, "batch_id=20260911-T3", "")

    async def test_attaches_in_transit_issue_across_rounds(
        self, quality_db: ConnectionManager
    ) -> None:
        await seed_rules(quality_db)
        service = QualityService(quality_db)
        # 第一轮：建单 → 责任人推进到整改（在途）
        first = await service.accept_task()
        qrow = await add_quarantine(
            quality_db, batch_id=first.task_id, rule_no=8, action="隔离",
            payload={"equip_id": "EQUIP-01", "code": "R3"},
        )
        await finish_like_data_plane(quality_db, first.task_id, report=_report(EQUIP_HIT), hits=1)
        await service.get_task(first.task_id)
        issue = (await issue_rows(quality_db))[0]
        assert issue.id == "d1"
        await service.transition_issue(issue.id, "小李")  # 认领
        await service.transition_issue(issue.id, "小李")  # 整改
        # 第二轮：受理（在途单不清）→ 同命中挂同单
        second = await service.accept_task()
        assert second.cleared == 0
        await add_quarantine(
            quality_db, batch_id=second.task_id, rule_no=8, action="隔离",
            payload={"equip_id": "EQUIP-01", "code": "R3"},
        )
        await finish_like_data_plane(quality_db, second.task_id, report=_report(EQUIP_HIT), hits=1)
        view = await service.get_task(second.task_id)
        assert view.followup is not None
        assert (view.followup.created, view.followup.attached) == (0, 1)
        rows = await issue_rows(quality_db)
        assert len(rows) == 1 and rows[0].id == "d1"  # 不翻倍不换单
        assert rows[0].hit_count == 2 and rows[0].lane == 2  # 挂单 +1、态不变
        assert await qrow_issue_id(quality_db, qrow.id) == "d1"

    async def test_claim_guard_exclusive_after_followup(
        self, quality_db: ConnectionManager
    ) -> None:
        await seed_rules(quality_db)
        service = QualityService(quality_db)
        receipt = await service.accept_task()
        await finish_like_data_plane(quality_db, receipt.task_id, report=_report(), hits=0)
        await service.get_task(receipt.task_id)  # 接续完成 step→4
        async with quality_db.session() as session:
            assert not await QualityStore.claim_task_followup(session, receipt.task_id)

    async def test_unknown_task_404(self, quality_db: ConnectionManager) -> None:
        service = QualityService(quality_db)
        with pytest.raises(QualityTaskNotFoundError):
            await service.get_task("QT-19700101-01")


# ---------- 端点 5：历史倒序 ----------


class TestTaskHistory:
    async def test_done_desc_running_excluded(
        self, quality_db: ConnectionManager
    ) -> None:
        await seed_rules(quality_db)
        service = QualityService(quality_db)
        first = await service.accept_task()
        await finish_like_data_plane(quality_db, first.task_id, report=_report(), hits=0)
        second = await service.accept_task()
        await finish_like_data_plane(quality_db, second.task_id, report=_report(), hits=0)
        await add_task(quality_db, id=f"QT-{FAR_DAY}-77")  # 在途任务不进历史
        items = await service.list_tasks()
        assert [t.id for t in items] == [second.task_id, first.task_id]  # 最新在前
        assert all(t.report is not None for t in items)


# ---------- 复扫通道（生产适配器 × 拾取替身） ----------


class TestRescanChannel:
    async def test_green_backfills_sentinel_via_rescan_note(
        self, quality_db: ConnectionManager
    ) -> None:
        """F2 义务：通道结论经 domain.rescan_note 落 verify——全绿＝哨兵同词表。"""
        await seed_rules(quality_db)
        service = QualityService(quality_db)
        await add_issue(
            quality_db, id="d1", lane=3, rule_no=8,
            dedupe_key=build_dedupe_key(8, "equip_id=EQUIP-01;code=R3", ""),
        )
        bind_channel_rescan(service, quality_db)
        # 拾取替身：报告仍挂规则 8 但**他对象**——本单对象已修正＝增量全绿
        other = _hit(8, "写法不统一", "隔离", [{"equip_id": "EQUIP-99", "code": "R3"}])
        worker = asyncio.ensure_future(pickup_worker(quality_db, _report(other)))
        receipt = await service.transition_issue("d1", "小李", action=RESCAN_ACTION)
        await worker
        assert receipt.lane == 3  # 复扫不是流转
        assert receipt.verify is not None
        assert receipt.verify.note == RESCAN_GREEN_NOTE  # 哨兵同词表（F2）
        assert receipt.verify.batch.startswith("QT-")  # 修正批次标识＝复扫任务号

    async def test_red_when_object_still_hits(
        self, quality_db: ConnectionManager
    ) -> None:
        await seed_rules(quality_db)
        service = QualityService(quality_db)
        await add_issue(
            quality_db, id="d1", lane=3, rule_no=8,
            dedupe_key=build_dedupe_key(8, "equip_id=EQUIP-01;code=R3", ""),
        )
        bind_channel_rescan(service, quality_db)
        worker = asyncio.ensure_future(
            pickup_worker(quality_db, _report(EQUIP_HIT))
        )
        receipt = await service.transition_issue("d1", "小李", action=RESCAN_ACTION)
        await worker
        assert receipt.verify is not None
        assert receipt.verify.note == rescan_note(False, "规则 8 仍命中：EQUIP-01 · R3")
        assert receipt.verify.note.startswith("仍有命中：")

    async def test_timeout_maps_deferred_501(
        self, quality_db: ConnectionManager
    ) -> None:
        from app.domains.dataops.quality import QualityTaskChannelDeferredError

        await seed_rules(quality_db)
        service = QualityService(quality_db)
        await add_issue(
            quality_db, id="d1", lane=3, rule_no=8,
            dedupe_key=build_dedupe_key(8, "equip_id=EQUIP-01;code=R3", ""),
        )
        # 通道装配但拾取半边不运行（数据面 worker 缺位）——限时诚实 501，不 mock
        service.bind_rescan_executor(
            DataPlaneChannelRescanExecutor(
                quality_db, service.accept_task,
                timeout_seconds=0.05, poll_seconds=0.01,
            )
        )
        with pytest.raises(QualityTaskChannelDeferredError) as err:
            await service.transition_issue("d1", "小李", action=RESCAN_ACTION)
        assert "未被数据面" in str(err.value)
        # 超时前已落复扫任务行（受理半边真实发生——历史可溯）
        assert await running_step0_task_id(quality_db) is not None

    async def test_running_task_conflict_maps_409(
        self, quality_db: ConnectionManager
    ) -> None:
        await seed_rules(quality_db)
        service = QualityService(quality_db)
        await add_issue(
            quality_db, id="d1", lane=3, rule_no=8,
            dedupe_key=build_dedupe_key(8, "equip_id=EQUIP-01;code=R3", ""),
        )
        await add_task(quality_db, id=f"QT-{FAR_DAY}-99")  # 他任务在途
        bind_channel_rescan(service, quality_db)
        with pytest.raises(QualityTaskRunningError):
            await service.transition_issue("d1", "小李", action=RESCAN_ACTION)

    async def test_rescan_does_not_clear_stale_distribution(
        self, quality_db: ConnectionManager
    ) -> None:
        await seed_rules(quality_db)
        service = QualityService(quality_db)
        await add_issue(
            quality_db, id="d1", lane=3, rule_no=8,
            dedupe_key=build_dedupe_key(8, "equip_id=EQUIP-01;code=R3", ""),
        )
        await add_issue(  # 他单在分发未认领——复扫不撤单（复扫不是重跑）
            quality_db, id="d9", lane=0, rule_no=5,
            dedupe_key=build_dedupe_key(5, "N-09", "2026-09-14"),
        )
        bind_channel_rescan(service, quality_db)
        worker = asyncio.ensure_future(pickup_worker(quality_db, _report()))
        await service.transition_issue("d1", "小李", action=RESCAN_ACTION)
        await worker
        assert {row.id for row in await issue_rows(quality_db)} == {"d1", "d9"}


async def qrow_issue_id(db: ConnectionManager, qrow_pk: int) -> str | None:
    """隔离行回挂读（readonly 面——接续回挂断言便道）。"""
    async with db.readonly() as session:
        row = await session.get(QuarantineRow, qrow_pk)
        return None if row is None else row.issue_id
