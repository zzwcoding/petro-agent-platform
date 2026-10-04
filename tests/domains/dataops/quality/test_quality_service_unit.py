"""quality 服务单测——五态状态机全路径/挂单语义/水位 T-1/隔离区过滤/规则启停。

sqlite 底座（conftest.quality_db）＋ freeze 时钟（B14）；B12 审计由 api 层
编排（audit 行断言归 tests/api/test_quality_api.py），本文件不涉 security。
合同锚：E2-数据质量台.md v0.5（端点 2/6/7/8/9＋行为约定 3/4/5）。
"""

from typing import Any

import pytest

from app.domains.dataops.quality import (
    RESCAN_GREEN_NOTE,
    QualityCloseBlockedError,
    QualityIssueNotFoundError,
    QualityIssueStateError,
    QualityParamError,
    QualityRuleNotFoundError,
    QualityTaskChannelDeferredError,
)
from app.domains.dataops.quality.domain import QrowView, build_dedupe_key, freshness_judgment
from app.domains.dataops.quality.service import QualityService
from app.domains.dataops.quality.store import QualityIssue, QuarantineRow
from app.infra.clock import freeze
from app.infra.db import ConnectionManager
from tests.domains.dataops.quality.conftest import (
    add_issue,
    add_quarantine,
    add_water_line,
    green_executor,
    issue_rows,
    red_executor,
    seed_rule,
    transition_rows,
)

DAY = "2026-09-14"


async def _seed_rules(db: ConnectionManager) -> None:
    """状态机/挂单用最小规则集（判据值取 0015 种子同款——投影对账归 PG 测试）。"""
    await seed_rule(db, 5, kind="超范围", crit="越界即 fail；矛盾行清单制")
    await seed_rule(db, 7, kind="写法不统一", crit="归一表全命中", action="隔离", autofix=True)
    await seed_rule(db, 8, kind="写法不统一", crit="映射表全命中", action="隔离", autofix=True)


class TestRuleFace:
    async def test_list_rules_projects_seed_columns(
        self, quality_db: Any
    ) -> None:
        await _seed_rules(quality_db)
        service = QualityService(quality_db)
        rules = await service.list_rules()
        assert [(r.no, r.kind, r.enabled, r.action, r.auto_fix) for r in rules] == [
            (5, "超范围", True, "告警", False),
            (7, "写法不统一", True, "隔离", True),
            (8, "写法不统一", True, "隔离", True),
        ]
        assert rules[0].crit == "越界即 fail；矛盾行清单制"

    async def test_toggle_flips_enabled_and_read_face_reflects(
        self, quality_db: Any
    ) -> None:
        await _seed_rules(quality_db)
        service = QualityService(quality_db)
        receipt = await service.set_rule_enabled(7, False)
        assert (receipt.no, receipt.enabled) == (7, False)
        rules = {r.no: r for r in await service.list_rules()}
        assert rules[7].enabled is False  # 读面反映（停用＝任务跳过不删——行还在）
        assert rules[8].enabled is True  # 其余规则不受牵连
        again = await service.set_rule_enabled(7, False)  # 重复置位幂等照收
        assert again.enabled is False

    async def test_toggle_unknown_rule_404(self, service: Any) -> None:
        with pytest.raises(QualityRuleNotFoundError):
            await service.set_rule_enabled(99, False)


async def _p8_at(db: ConnectionManager, lane: int) -> None:
    """规则 8 问题单直插（id=p8——状态机各用例共用底座）。"""
    await _seed_rules(db)
    await add_issue(
        db, id="p8", lane=lane, rule_no=8, hit_count=1,
        dedupe_key=build_dedupe_key(8, "EQUIP-01", DAY),
    )


class TestTransitionStateMachine:

    async def test_full_path_five_lanes(self, quality_db: Any) -> None:
        await _p8_at(quality_db, 0)
        service = QualityService(quality_db)
        receipt = await service.transition_issue("p8", "小李 · 地质/质检")
        assert (receipt.lane, receipt.state) == (1, "认领")
        receipt = await service.transition_issue("p8", "小李 · 地质/质检")
        assert (receipt.lane, receipt.state) == (2, "整改")
        receipt = await service.transition_issue("p8", "小李 · 地质/质检")
        # 推进到「复核」仅登记待复扫——verify 仍空（v0.5 降级，自动复扫挂观察）
        assert (receipt.lane, receipt.state, receipt.verify) == (3, "复核", None)
        rows = await issue_rows(quality_db)
        assert rows[0].lane == 3 and rows[0].verify is None

    async def test_terminal_closed_rejected_409(self, quality_db: Any) -> None:
        await _p8_at(quality_db, 4)
        service = QualityService(quality_db)
        with pytest.raises(QualityIssueStateError):
            await service.transition_issue("p8", "小李 · 地质/质检")

    async def test_close_guard_422_without_verify_and_close_note(
        self, quality_db: Any
    ) -> None:
        await _p8_at(quality_db, 3)
        service = QualityService(quality_db)
        with pytest.raises(QualityCloseBlockedError):
            await service.transition_issue("p8", "小李 · 地质/质检")

    async def test_close_guard_422_with_red_verify(self, quality_db: Any) -> None:
        await _p8_at(quality_db, 3)
        async with quality_db.session() as session:
            row = await session.get(QualityIssue, "p8")
            assert row is not None
            row.verify = {"batch": "批次 20260922-T1", "note": "仍有命中：规则 8 旧码未映射"}
        service = QualityService(quality_db)
        with pytest.raises(QualityCloseBlockedError):
            await service.transition_issue("p8", "小李 · 地质/质检")

    async def test_close_with_close_note_exempt_path(self, quality_db: Any) -> None:
        await _seed_rules(quality_db)
        await add_issue(
            quality_db, id="p10", lane=3, rule_no=10, hit_count=1,
            dedupe_key=build_dedupe_key(10, "N-10", DAY),
            close_note="告警类规则核实为真实关井——不涉及隔离行，记录原因后关闭",
        )
        service = QualityService(quality_db)
        receipt = await service.transition_issue("p10", "小李 · 地质/质检")
        assert (receipt.lane, receipt.state) == (4, "关闭")

    async def test_close_with_green_verify(self, quality_db: Any) -> None:
        await _p8_at(quality_db, 3)
        async with quality_db.session() as session:
            row = await session.get(QualityIssue, "p8")
            assert row is not None
            row.verify = {"batch": "批次 20260922-T1", "note": RESCAN_GREEN_NOTE}
        service = QualityService(quality_db)
        receipt = await service.transition_issue("p8", "小李 · 地质/质检")
        assert receipt.lane == 4

    async def test_transition_writes_trace_rows(self, quality_db: Any) -> None:
        await _p8_at(quality_db, 0)
        service = QualityService(quality_db)
        for _ in range(3):
            await service.transition_issue("p8", "小李 · 地质/质检")
        rows = await transition_rows(quality_db, "p8")
        assert [(r.seq, r.from_lane, r.to_lane, r.operator) for r in rows] == [
            (1, 0, 1, "小李 · 地质/质检"),
            (2, 1, 2, "小李 · 地质/质检"),
            (3, 2, 3, "小李 · 地质/质检"),
        ]
        assert rows[0].time is not None

    async def test_unknown_issue_404_and_unknown_action_400(
        self, quality_db: Any
    ) -> None:
        await _p8_at(quality_db, 0)
        service = QualityService(quality_db)
        with pytest.raises(QualityIssueNotFoundError):
            await service.transition_issue("p99", "小李 · 地质/质检")
        with pytest.raises(QualityParamError):
            await service.transition_issue("p8", "小李 · 地质/质检", action="rollback")


class TestRescanAction:
    async def test_rescan_only_at_review_lane(self, quality_db: Any) -> None:
        await _p8_at(quality_db, 2)
        service = QualityService(quality_db)
        with pytest.raises(QualityIssueStateError):
            await service.transition_issue("p8", "小李 · 地质/质检", action="rescan")

    async def test_rescan_without_channel_deferred_501(self, quality_db: Any) -> None:
        await _p8_at(quality_db, 3)
        service = QualityService(quality_db)  # 执行缝缺省未接
        with pytest.raises(QualityTaskChannelDeferredError):
            await service.transition_issue("p8", "小李 · 地质/质检", action="rescan")

    async def test_rescan_green_backfills_verify_lane_unchanged(
        self, quality_db: Any
    ) -> None:
        await _p8_at(quality_db, 3)
        service = QualityService(quality_db, rescan_executor=green_executor())
        receipt = await service.transition_issue(
            "p8", "小李 · 地质/质检", action="rescan"
        )
        # 复扫不是流转——lane 不变；verify 回填（全绿哨兵＋修正批次标识）
        assert (receipt.lane, receipt.state) == (3, "复核")
        assert receipt.verify is not None
        assert receipt.verify.batch == "批次 20260922-T1"
        assert receipt.verify.note == RESCAN_GREEN_NOTE
        rows = await issue_rows(quality_db)
        assert rows[0].lane == 3
        assert rows[0].verify == {"batch": "批次 20260922-T1", "note": RESCAN_GREEN_NOTE}
        assert await transition_rows(quality_db, "p8") == []  # 复扫不留痕流转行

    async def test_rescan_red_then_close_still_blocked(
        self, quality_db: Any
    ) -> None:
        await _p8_at(quality_db, 3)
        service = QualityService(quality_db, rescan_executor=red_executor())
        receipt = await service.transition_issue(
            "p8", "小李 · 地质/质检", action="rescan"
        )
        assert receipt.verify is not None
        assert receipt.verify.note.startswith("仍有命中")
        with pytest.raises(QualityCloseBlockedError):
            await service.transition_issue("p8", "小李 · 地质/质检")


class TestRegisterHit:
    async def test_new_hit_creates_distribution_issue_with_backlink(
        self, quality_db: Any
    ) -> None:
        await _seed_rules(quality_db)
        qrow = await add_quarantine(
            quality_db, batch_id="QT-20260914-01", rule_no=8, action="隔离",
            loc="设备状态 equip_status", issue_id=None,
            payload={"code": "R3", "note": "停机原因旧码 R3 未按映射表换成 BELT"},
        )
        service = QualityService(quality_db)
        receipt = await service.register_hit(
            rule_no=8, object_key="EQUIP-01", data_date=DAY,
            title="规则 8 · 停机原因码旧码未映射",
            desc="equip_status 旧码 R3 未按映射表换成 BELT",
            owner="责任：作业区资料员", quarantine_row_ids=[qrow.id],
        )
        assert (receipt.issue_id, receipt.attached, receipt.hit_count, receipt.lane) == (
            "d1", False, 1, 0,
        )
        rows = await issue_rows(quality_db)
        assert len(rows) == 1
        assert rows[0].lane == 0 and rows[0].hit_count == 1
        assert rows[0].dedupe_key == build_dedupe_key(8, "EQUIP-01", DAY)
        assert rows[0].owner == "责任：作业区资料员"
        # 隔离行回挂（qrows 可追溯链）
        async with quality_db.readonly() as session:
            attached = await session.get(QuarantineRow, qrow.id)
            assert attached is not None and attached.issue_id == "d1"

    async def test_repeat_hit_attaches_same_issue_hit_count_plus_one(
        self, quality_db: Any
    ) -> None:
        await _seed_rules(quality_db)
        service = QualityService(quality_db)
        first = await service.register_hit(
            rule_no=8, object_key="EQUIP-01", data_date=DAY, title="规则 8 · x",
        )
        second = await service.register_hit(
            rule_no=8, object_key="EQUIP-01", data_date=DAY, title="规则 8 · x 重跑",
            quarantine_row_ids=[],
        )
        # 挂同单不重复开（hit_count +1 不翻倍）——即便首轮单已流转（在途单保护）
        assert (first.attached, first.hit_count) == (False, 1)
        assert (second.attached, second.hit_count) == (True, 2)
        assert second.issue_id == first.issue_id
        assert len(await issue_rows(quality_db)) == 1

    async def test_in_transit_issue_survives_and_attaches(self, quality_db: Any) -> None:
        await _seed_rules(quality_db)
        await add_issue(
            quality_db, id="d9", lane=2, rule_no=7, hit_count=1,
            dedupe_key=build_dedupe_key(7, "N2", DAY), owner="整改：作业区资料员",
        )
        service = QualityService(quality_db)
        receipt = await service.register_hit(
            rule_no=7, object_key="N2", data_date=DAY, title="规则 7 · 井号未归一",
        )
        # 在途单（整改中）跨轮不清、新命中挂同单——lane 不变、计数 +1
        assert (receipt.issue_id, receipt.attached, receipt.lane) == ("d9", True, 2)
        rows = await issue_rows(quality_db)
        assert rows[0].lane == 2 and rows[0].hit_count == 2

    async def test_different_dedupe_key_creates_new_issue(self, quality_db: Any) -> None:
        await _seed_rules(quality_db)
        service = QualityService(quality_db)
        await service.register_hit(
            rule_no=8, object_key="EQUIP-01", data_date=DAY, title="a",
        )
        other = await service.register_hit(
            rule_no=8, object_key="EQUIP-02", data_date=DAY, title="b",
        )
        # 对象不同＝不同问题——另开单（d 序号单调不复用）
        assert (other.attached, other.issue_id) == (False, "d2")

    async def test_unknown_rule_rejected(self, quality_db: Any) -> None:
        service = QualityService(quality_db)
        with pytest.raises(QualityRuleNotFoundError):
            await service.register_hit(
                rule_no=42, object_key="X", data_date=DAY, title="t",
            )

    async def test_oversize_dedupe_key_rejected_not_truncated(
        self, quality_db: Any
    ) -> None:
        service = QualityService(quality_db)
        with pytest.raises(QualityParamError):
            await service.register_hit(
                rule_no=8, object_key="X" * 200, data_date=DAY, title="t",
            )


class TestFreshness:
    async def test_three_tiers_judged_against_t_minus_one(
        self, quality_db: Any
    ) -> None:
        await add_water_line(quality_db, "原始层", "2026-09-14")
        await add_water_line(quality_db, "清洗层", "2026-09-14")
        await add_water_line(quality_db, "汇总层", "2026-09-11")
        service = QualityService(quality_db)
        with freeze("2026-09-15 08:00:00"):
            views = await service.freshness()
        assert [(v.layer, v.to, v.promise, v.tag, v.color) for v in views] == [
            ("原始层", "到 2026-09-14", "T-1", "达标（承诺 T-1）", "green"),
            ("清洗层", "到 2026-09-14", "T-1", "达标（承诺 T-1）", "green"),
            # 合同端点 8 示例同款：汇总层（问数用）落后 3 天 · 超期
            ("汇总层（问数用）", "到 2026-09-11", "T-1", "落后 3 天 · 超期", "gold"),
        ]

    async def test_missing_layer_absent_not_fabricated(self, quality_db: Any) -> None:
        await add_water_line(quality_db, "原始层", "2026-09-14")
        service = QualityService(quality_db)
        with freeze("2026-09-15 08:00:00"):
            views = await service.freshness()
        assert [v.layer for v in views] == ["原始层"]  # 未回写层如实缺行

    def test_judgment_pure_function_boundary(self) -> None:
        from datetime import date

        base = date(2026, 9, 15)
        assert freshness_judgment(date(2026, 9, 14), base)[2] == 0  # 恰 T-1 达标
        assert freshness_judgment(date(2026, 9, 15), base)[:2] == ("达标（承诺 T-1）", "green")
        tag, color, late = freshness_judgment(date(2026, 9, 11), base)
        assert (tag, color, late) == ("落后 3 天 · 超期", "gold", 3)


class TestQuarantineRead:
    async def _fixture(self, db: Any) -> None:
        await _seed_rules(db)
        await add_issue(
            db, id="d1", lane=0, rule_no=8, hit_count=1,
            dedupe_key=build_dedupe_key(8, "EQUIP-01", DAY),
        )
        await add_quarantine(
            db, batch_id="QT-20260914-01", rule_no=1, action="隔离",
            loc="生产日报 · N-02 · 2026-09-14", payload={"oil": 12.4}, issue_id="d1",
        )
        await add_quarantine(
            db, batch_id="QT-20260914-01", rule_no=8, action="隔离",
            loc="设备状态 equip_status", payload={"code": "R3"}, issue_id="d1",
        )
        await add_quarantine(
            db, batch_id="b-20260913-T2", rule_no=2, action="整批拒收",
            loc="批次 b-20260913-T2", payload={"rows": 120}, issue_id=None,
        )

    async def test_filters_combinable(self, quality_db: Any) -> None:
        await self._fixture(quality_db)
        service = QualityService(quality_db)
        assert len(await service.list_quarantine()) == 3
        by_batch = await service.list_quarantine(batch_id="QT-20260914-01")
        assert [q.rule_no for q in by_batch] == [1, 8]  # append 序（id 升序）
        by_rule = await service.list_quarantine(rule_no=8)
        assert [q.loc for q in by_rule] == ["设备状态 equip_status"]
        by_issue = await service.list_quarantine(issue_id="d1")
        assert len(by_issue) == 2
        both = await service.list_quarantine(
            batch_id="QT-20260914-01", rule_no=8, issue_id="d1"
        )
        assert len(both) == 1
        assert await service.list_quarantine(issue_id="d9") == []

    async def test_created_at_display_and_payload_asis(
        self, quality_db: Any
    ) -> None:
        await self._fixture(quality_db)
        service = QualityService(quality_db)
        with freeze("2026-09-14 19:58:00"):
            await add_quarantine(
                quality_db, batch_id="QT-20260914-02", rule_no=1, action="隔离",
                loc="生产日报 · N-06", payload={"well": "N-06"}, issue_id=None,
            )
        rows = await service.list_quarantine(batch_id="QT-20260914-02")
        assert rows[0].created_at == "2026-09-14 19:58"  # 展示串（R2——合同示例同形）
        assert rows[0].payload == {"well": "N-06"}  # 坏行原样（append-only 不改写）


class TestIssueListProjection:
    async def test_lanes_filter_rule_filter_pagination_and_projections(
        self, quality_db: Any
    ) -> None:
        await _seed_rules(quality_db)
        qrow = await add_quarantine(
            quality_db, batch_id="QT-20260914-01", rule_no=8, action="隔离",
            loc="设备状态 equip_status", payload={"code": "R3", "note": "旧码 R3 未映射"},
        )
        await add_issue(
            quality_db, id="d1", lane=0, rule_no=8, hit_count=1,
            dedupe_key=build_dedupe_key(8, "EQUIP-01", DAY),
            title="规则 8 · 停机原因码旧码未映射",
            desc="equip_status 旧码 R3 未按映射表换成 BELT",
            owner="责任：作业区资料员", verify=None, close_note=None,
        )
        await add_issue(
            quality_db, id="d2", lane=3, rule_no=7, hit_count=2,
            dedupe_key=build_dedupe_key(7, "N2", DAY),
            verify={"batch": "批次 20260922-T1", "note": RESCAN_GREEN_NOTE},
            close_note=None,
        )
        # qrow 回挂 d1（payload 自带说明键约定——d2 告警类无 qrows）
        async with quality_db.session() as session:
            row = await session.get(QuarantineRow, qrow.id)
            assert row is not None
            row.issue_id = "d1"

        service = QualityService(quality_db)
        page = await service.list_issues()
        assert page.lanes == ("分发", "认领", "整改", "复核", "关闭")
        assert page.total == 2 and page.page == 1 and page.page_size == 20
        assert [i.id for i in page.items] == ["d1", "d2"]  # lane 升序＋id 序
        d1, d2 = page.items
        assert d1.qrows == [QrowView(loc="设备状态 equip_status", note="旧码 R3 未映射")]
        # ai_note＝规则判据说明投影（v0.5 降级——零 LLM，存储恒空读侧拼装）
        assert d1.ai_note == "规则 8 判据：映射表全命中"
        assert d1.verify is None and d1.close_note is None
        assert d2.verify is not None
        assert (d2.verify.batch, d2.verify.note) == ("批次 20260922-T1", RESCAN_GREEN_NOTE)
        assert d2.qrows == []

        by_lane = await service.list_issues(lane=3)
        assert [i.id for i in by_lane.items] == ["d2"] and by_lane.total == 1
        by_rule = await service.list_issues(rule_no=8)
        assert [i.id for i in by_rule.items] == ["d1"]
        paged = await service.list_issues(page=1, page_size=1)
        assert [i.id for i in paged.items] == ["d1"] and paged.total == 2
