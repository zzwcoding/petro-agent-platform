"""semantics 种子投影与同步器幂等（sqlite 单测底座——99 §4.1 测试替身策略）。

验收项（tickets/phase1/README.md P1-01）：同步器幂等（跑两遍结果一致）；
占位行种子断言（wf3–wf10 八条/白名单 #2/Action 三条）；行版本轴留痕；
钉版 schema 拒同步；B12 审计动作。PG 真库逐列断言见 test_semantics_pg.py。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.security.domain import AuditRow, resolve_actor
from app.domains.semantics import (
    SCHEMA_VERSION_PIN,
    OntologyDriftError,
    OntologySchemaUnsupported,
    metric_grain_display,
    registered_items,
    term_expiry,
)
from app.domains.semantics import domain as sem_domain
from app.domains.semantics.service import OntologyModels, SemanticsService, load_ontology_models
from app.domains.semantics.store import (
    SemAction,
    SemJoinWhitelist,
    SemLedgerRevision,
    SemMetric,
    SemObject,
    SemRelation,
    SemTerm,
    SemVersion,
    SemWorkflow,
    ensure_semantics_tables,
)
from app.infra.db import ConnectionManager, DatabaseSpec


class RecordingAudit:
    """B12 审计替身——记录 security.audit 入参（写口形状不旁路直写审计表）。"""

    def __init__(self) -> None:
        self.rows: list[AuditRow] = []

    async def audit(self, row: AuditRow, *, session: object | None = None) -> None:
        self.rows.append(row)


@pytest.fixture
async def db(tmp_path: Path) -> AsyncIterator[ConnectionManager]:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "semantics-unit.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    engine = create_async_engine(spec.url())
    await ensure_semantics_tables(engine)
    await engine.dispose()
    yield manager
    await manager.dispose()


@pytest.fixture
def service(db: ConnectionManager) -> SemanticsService:
    return SemanticsService(db, RecordingAudit())


async def _count(db: ConnectionManager, model: type) -> int:
    async with db.readonly() as session:
        return int(await session.scalar(select(func.count()).select_from(model)))


async def test_first_run_seeds_seven_accounts_and_version(
    db: ConnectionManager, service: SemanticsService
) -> None:
    report = await service.sync_from_ontology_repo("mr#1", resolve_actor(None))
    assert report.warnings == []  # P1-01b：口径名三处统一（设定书 §3）后告警消除
    assert report.counts == {
        "term": 11, "metric": 15, "object": 10, "relation": 10,  # G-05 词表扩充 5→10
        "whitelist": 4, "workflow": 10, "action": 3,
    }  # C1 合同页签计数（11/15/10＋5/10/3）
    assert report.revisions_appended == 63  # 11+15+10+10+4+10+3（G-05 关系 5→10）
    assert await _count(db, SemTerm) == 11
    assert await _count(db, SemMetric) == 15
    assert await _count(db, SemObject) == 10
    assert await _count(db, SemRelation) == 10
    assert await _count(db, SemJoinWhitelist) == 4
    assert await _count(db, SemWorkflow) == 10
    assert await _count(db, SemAction) == 3
    assert await _count(db, SemLedgerRevision) == 63
    async with db.readonly() as session:
        version = await session.get(SemVersion, "current")
        assert version is not None and version.current == "v37"  # C1/C3 演示值同源


async def test_sync_is_idempotent_second_run_zero_writes(
    db: ConnectionManager, service: SemanticsService
) -> None:
    await service.sync_from_ontology_repo("mr#1", resolve_actor(None))
    report = await service.sync_from_ontology_repo("mr#1", resolve_actor(None))
    assert report.revisions_appended == 0
    assert report.rows_unchanged == 63
    assert report.warnings == []  # P1-01b 口径名统一后同步零告警（含幂等重跑）
    assert await _count(db, SemLedgerRevision) == 63  # 行版本轴不因重放膨胀


async def test_revision_rows_carry_snapshot_and_actor(
    db: ConnectionManager, service: SemanticsService
) -> None:
    actor = resolve_actor("aqiang")
    await service.sync_from_ontology_repo("mr#42", actor)
    async with db.readonly() as session:
        rows = (
            (
                await session.execute(
                    select(SemLedgerRevision)
                    .where(SemLedgerRevision.domain == "metric", SemLedgerRevision.row_id == "2")
                )
            )
            .scalars()
            .all()
        )
    assert len(rows) == 1
    revision = rows[0]
    assert revision.version == 1
    assert revision.changed_by == actor.who
    assert revision.source_proposal_id is None  # 同步器投影非提案汇入
    # 该版全行快照（99 §2.8）——M3 口径字段组随行入档
    assert revision.payload["name"] == "★有效产量（两支口径）"
    assert revision.payload["grain"] == "月"
    assert revision.payload["calibers"][0]["key"] == "A"


async def test_metric_projection_carries_m3_caliber_fields(
    db: ConnectionManager, service: SemanticsService
) -> None:
    await service.sync_from_ontology_repo("mr#1", resolve_actor(None))
    async with db.readonly() as session:
        ambiguous = await session.get(SemMetric, 2)
        joint = await session.get(SemMetric, 10)
        fact_carrier = await session.get(SemMetric, 11)
        placeholder = await session.get(SemMetric, 15)
    assert ambiguous is not None
    assert ambiguous.mark == "★"
    assert ambiguous.slot_name == "有效产量"  # 剥法单点：★/括注/尾缀全剥
    assert ambiguous.ambiguous is True
    assert ambiguous.default_caliber == "A"
    # P1-01b 统一后权威名（设定书 §3 指标 2「开井日历折算 / 检修剔除」）
    assert [c["name"] for c in ambiguous.calibers] == ["开井日历折算", "检修剔除"]
    assert joint is not None
    assert joint.status == ["生效中", "待联席裁决"]  # 双徽标（#10）
    assert (joint.grain, joint.unit) == ("井组·年", "吨")  # M3 口径字段组真源投影
    assert joint.modifiers is None  # RULE-PETRO-018 无修饰词登记
    assert fact_carrier is not None
    assert fact_carrier.mark == "★" and fact_carrier.dispute == "与井口口径天然不等"
    assert placeholder is not None
    assert (placeholder.grain, placeholder.unit) == ("批次", "元/桶")
    assert placeholder.dispute == "经营 × 技术联席"  # deferredAdditions 占位如实投影


async def test_slot_name_strip_rules_over_fifteen_metrics(
    db: ConnectionManager, service: SemanticsService
) -> None:
    await service.sync_from_ontology_repo("mr#1", resolve_actor(None))
    async with db.readonly() as session:
        rows = (await session.execute(select(SemMetric))).scalars().all()
    by_id = {row.id: row for row in rows}
    assert by_id[6].slot_name == "注采比 β"  # β 保留（只剥 η/T）
    assert by_id[8].slot_name == "措施有效率"  # 剥 η
    assert by_id[9].slot_name == "措施有效期"  # 剥 T
    assert by_id[3].slot_name == "自然递减率"
    assert len({row.slot_name for row in rows}) == 15  # slot_name uq——剥法结果全 uniqe


async def test_placeholder_rows_wf3_wf10_whitelist2_and_actions(
    db: ConnectionManager, service: SemanticsService
) -> None:
    await service.sync_from_ontology_repo("mr#1", resolve_actor(None))
    async with db.readonly() as session:
        workflows = (await session.execute(select(SemWorkflow))).scalars().all()
        whitelist = (await session.execute(select(SemJoinWhitelist))).scalars().all()
        actions = (await session.execute(select(SemAction))).scalars().all()
        terms = (await session.execute(select(SemTerm))).scalars().all()
    by_wf = {wf.id: wf for wf in workflows}
    assert len(workflows) == 10
    assert by_wf["wf1"].status == "登记" and by_wf["wf1"].account == "产量分析"  # 唯一登记态
    assert registered_items(by_wf["wf1"].card) == 5
    assert registered_items(by_wf["wf2"].card) == 2
    placeholders = [f"wf{i}" for i in range(3, 11)]  # wf3–wf10 八条占位行
    for wf_id in placeholders:
        row = by_wf[wf_id]
        assert row.status == "草案" and row.account is None
        assert row.source is None
        assert all(row.card[key] is None for key in ("steps", "defaults", "confirm"))
    assert registered_items(by_wf["wf3"].card) == 2  # 开工条件＋输出合同
    assert registered_items(by_wf["wf5"].card) == 0  # 全项未登记
    # 白名单 #2＝deferredAdditions 占位（date_dim 非本体元素）
    wl2 = next(row for row in whitelist if row.id == 2)
    assert (wl2.left_table, wl2.right_table) == ("oil_production_daily", "date_dim")
    assert wl2.verdict == "可以"
    # Action 三条（照抄 C1 ACTIONS——票 92/103 下线备查资产）
    assert sorted(a.register_name for a in actions) == [
        "adjust_injection_volume", "adjust_production_plan", "update_well_remark",
    ]
    # 术语 #11 页面增补行（漂移演示源；expires_at 落日期——expired 读侧现算）
    term11 = next(t for t in terms if t.id == 11)
    assert term11.term == "日产液" and term11.status_key == "有效（已届满）"
    assert term11.expires_at is not None and term11.expires_at.isoformat() == "2026-06-30"


async def test_sync_action_audited_via_b12_write_port(service: SemanticsService) -> None:
    sink = RecordingAudit()
    svc = SemanticsService(service._db, sink)
    report = await svc.sync_from_ontology_repo("mr#7", resolve_actor("zhuren"))
    assert len(sink.rows) == 1
    row = sink.rows[0]
    assert row.action == "semantics.ontology_synced"
    assert row.who == "主任 · 汇报人"
    assert "mr#7" in row.content and "1.1.0" in row.content
    assert row.meta is not None and row.meta["counts"] == report.counts


async def test_schema_version_below_pin_rejected(service: SemanticsService) -> None:
    with pytest.raises(OntologySchemaUnsupported):
        await service.sync_from_ontology_repo("mr#1", resolve_actor(None), schema_version="1.0.9")


async def test_schema_version_above_pin_rejected(service: SemanticsService) -> None:
    # 高于钉版同样拒同步——本体仓 schema 升级须先仓后同步器联合变更（ontology 纪律 4）
    with pytest.raises(OntologySchemaUnsupported):
        await service.sync_from_ontology_repo(
            "mr#1", resolve_actor(None), schema_version="1.2.0"
        )


def test_validate_against_ontology_drift_raises() -> None:
    models = OntologyModels(
        models={"glossary": {"terms": []}, "m1": {}, "m3": {}, "m6": {}, "m2": {}},
        raw_text={"m2": ""},
        manifest_version=SCHEMA_VERSION_PIN,
    )
    with pytest.raises(OntologyDriftError):
        sem_domain.validate_against_ontology(models.models, models.raw_text)


def test_registered_items_counts_five_items_only() -> None:
    card = {"trigger": "t", "steps": ["s"], "defaults": None, "confirm": None,
            "contract": "c", "source": "设定书 §7", "meta": "…"}  # 来源/版本行不计数
    assert registered_items(card) == 3


def test_caliber_name_drift_warning_fires_only_on_real_mismatch() -> None:
    """P1-01b 看守闸：M3 calibers 与 C1 口径卡名一致＝零告警；名字集漂移才告警。"""
    ontology = load_ontology_models()
    m3_rules = {str(rule["id"]): rule for rule in ontology.models["m3"]["rules"]}
    _, warnings = sem_domain.enrich_metric_seeds(m3_rules)
    assert warnings == []  # 设定书 §3 权威名统一后——同步零告警
    m3_rules["RULE-PETRO-019"]["calibers"] = ["剔检口径", "开井日历口径"]  # 模拟本体侧旧值漂移
    _, warnings = sem_domain.enrich_metric_seeds(m3_rules)
    assert len(warnings) == 1
    assert "RULE-PETRO-019" in warnings[0] and "剔检口径" in warnings[0]


def test_metric_grain_display_c1_column_shape() -> None:
    """grain_display＝C1 页签列形「粒度 · 单位」（合同冻结拼装公式 grain+' · '+unit——可逆）。

    M3 斜杠分维形转 C1 括注族（裁决 e：sem_metric.grain/unit 存储值不动）；
    · 两侧恒带空格（C1 合同常量「月 · 年 · %」族——票面例「月（按区块 / 油田）· %」
    为行文脱空格，以合同拼装公式为准）。
    """
    assert metric_grain_display("月/区块·油田", "%") == "月（按区块 / 油田） · %"  # #1
    assert metric_grain_display("月", "吨") == "月 · 吨"  # #2
    assert metric_grain_display("月·年", "%") == "月·年 · %"  # #3/#4
    assert metric_grain_display("批次", "元/桶") == "批次 · 元/桶"  # #15（unit 内斜杠不拆）


def test_term_expiry_display_families() -> None:
    """expires_display 读侧派生复现 C1 全部展示串族；expired 到日即标（F60）。"""
    today = date(2026, 10, 1)
    assert term_expiry("禁用词", None, today) == (False, "—（已禁用）")  # #1
    assert term_expiry("有效", None, today) == (False, "长期")  # #8
    assert term_expiry("有效（引用马涛）", None, today) == (False, "长期（引用类）")  # #10
    assert term_expiry("有效（已届满）", date(2026, 6, 30), today) == (
        True, "2026-06-30（已届满）"
    )  # #11
    assert term_expiry("有效", date(2027, 12, 31), today) == (False, "2027-12-31")  # #2
    expired, _ = term_expiry("有效", today, today)  # 到日即标（含当日）
    assert expired is True
