"""S-01 语义台账种子——真迁移 0018 PG16 集成（双向/幂等＋本体锚对账＋问数链真消费）。

约定（同 tests/domains/dataops/quality/test_quality_tables_pg.py）：TEST_DATABASE_URL
未配置即 skip；测试自动落 <库名>_test 独立库。表结构＝**真迁移**程序化执行
（importlib 装载版本文件＋Operations.context——非 ORM 仿造）：0002 sem 九表→
0014 agg 星型→0018 种子；种子行消费＝真读口真链体（非夹具）：
- 覆盖 ① 0018 upgrade/downgrade 双向＋幂等（重放不翻倍、down 只删种子行）；
- ② 种子投影保真：与 ontology/bohai/ 权威定义**逐字对照**（防投影失真——T1
  审查项机检化：术语 term/def/status/owner 照抄 GLS、指标 name＝M1 label、
  slot_name＝剥法纯名与 MEASURE_COLUMNS 键合、计量列绑定注记逐行在场）＋
  sem_ledger_revision v1 配套行 payload 全行快照；
- ③ 问数链真消费（票面验收 3 红先证据）：未种子库「上个月日产油量最高的三口井」
  N7.1 降级解释链；0018 落库后同问句命中注册声明、真 QueryStore 只读执行出
  真表卡（agg fixture 行——量级样本，业务事实零发明）；术语种子经真装配层
  出词条卡（躺井·限作业区语境标注随卡）。
"""

from __future__ import annotations

import importlib.util
import os
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from typing import Any, ClassVar

import pytest
import yaml
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.chat import ChatService, QueryStore
from app.domains.chat import chains as chains_mod
from app.domains.chat import domain as d
from app.domains.chat.domain import MetricFace, RetrievalConfigFace, TermFace, WaterlineFace
from app.domains.security import SecurityService
from app.domains.semantics import SemanticsService
from app.infra.clock import now
from app.infra.db import ConnectionManager, DatabaseSpec
from tests.domains.chat.conftest import DEFAULT_CONFIG

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL 未配置——PG 集成测试跳过"
)

_VERSIONS = Path(__file__).resolve().parents[3] / "migrations" / "versions"
_MIGRATION_0002 = _VERSIONS / "20261001_0002_sem_baseline.py"
_MIGRATION_0014 = _VERSIONS / "20261004_0014_agg_star_model.py"
_MIGRATION_0018 = _VERSIONS / "20261005_0018_sem_ledger_seed.py"
_ONTOLOGY_BOHAI = Path(__file__).resolve().parents[3] / "ontology" / "bohai"

_QUESTION = "上个月日产油量最高的三口井"
_ACTOR = "阿强 · 平台运维"

# 种子键位（0018——bohai 段 200+，与同步器 petro 投影键空间 1~15/1~11 隔离）。
_METRIC_IDS = [201, 202, 203, 204, 205]
_TERM_IDS = [211, 212, 213, 214, 215, 216]

# 0002 九表（重跑复位面——真迁移 create_table 非 IF NOT EXISTS，残留表先 DROP）。
_SEM_TABLES = (
    "sem_action", "sem_join_whitelist", "sem_ledger_revision", "sem_metric",
    "sem_object", "sem_relation", "sem_term", "sem_version", "sem_workflow",
)


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


async def _reset_tables(url: URL) -> None:
    """重跑复位（retrieval PG fixture 同款——DROP IF EXISTS CASCADE 后重灌）。"""
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            for table in _SEM_TABLES:
                await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            await conn.execute(text("DROP SCHEMA IF EXISTS agg CASCADE"))
    finally:
        await engine.dispose()


def _load_migration(path: Path, name: str) -> Any:
    """版本文件名以日期开头非合法标识符——importlib 文件位装载。"""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def _run_migration_op(url: URL, path: Path, name: str, op_name: str) -> None:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            def _run(sync_conn: Any) -> None:
                context = MigrationContext.configure(sync_conn)
                with Operations.context(context):
                    getattr(_load_migration(path, name), op_name)()

            await conn.run_sync(_run)
    finally:
        await engine.dispose()


async def _seed_up(url: URL) -> None:
    await _run_migration_op(url, _MIGRATION_0018, "m0018_sem_ledger_seed", "upgrade")


async def _seed_down(url: URL) -> None:
    """0018 downgrade（种子未在场时＝空删——归零态归一，用例间互不依赖顺序）。"""
    await _run_migration_op(url, _MIGRATION_0018, "m0018_sem_ledger_seed", "downgrade")


async def _seed_counts(manager: ConnectionManager) -> tuple[int, int, int]:
    async with manager.readonly() as session:
        metric = int(await session.scalar(text("SELECT count(*) FROM sem_metric")) or 0)
        term = int(await session.scalar(text("SELECT count(*) FROM sem_term")) or 0)
        revision = int(
            await session.scalar(text("SELECT count(*) FROM sem_ledger_revision")) or 0
        )
    return metric, term, revision


@pytest.fixture
async def pg_db() -> AsyncIterator[ConnectionManager]:
    """独立测试库：真迁移 0002（sem 九表）＋0014（agg 星型）落结构，0018 归零态。"""
    if not _MIGRATION_0018.is_file():
        raise RuntimeError(f"S-01 迁移件缺失：{_MIGRATION_0018}")
    url = _isolated_url()
    await _ensure_test_database(url)
    await _reset_tables(url)
    await _run_migration_op(url, _MIGRATION_0002, "m0002_sem_baseline", "upgrade")
    await _run_migration_op(url, _MIGRATION_0014, "m0014_agg_star_model", "upgrade")
    await _seed_down(url)
    spec = DatabaseSpec(
        name="primary", role="primary", driver=url.drivername.split("+", 1)[0],
        host=url.host or "localhost", port=url.port or 5433,
        database=url.database or "", user=url.username or "",
        password=url.password or "", pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    yield manager
    await manager.dispose()


# ---------- 消费面装配（生产组合根镜像——main.py 同款读口投影，非夹具） ----------


def _metrics_loader(semantics: SemanticsService) -> Any:
    async def load() -> list[MetricFace]:
        page = await semantics.list_metrics(page_size=1000)
        return [
            MetricFace(
                metric_id=int(row.id), name=str(row.name), slot_name=str(row.slot_name),
                ambiguous=bool(row.ambiguous), calibers=list(row.calibers or []),
                default_caliber=row.default_caliber, status=list(row.status),
            )
            for row in page.items
        ]

    return load


def _terms_loader(semantics: SemanticsService) -> Any:
    async def load() -> list[TermFace]:
        page = await semantics.list_terms(page_size=1000)
        return [
            TermFace(
                term_id=int(row.id), term=str(row.term), type=str(row.type),
                def_text=str(row.def_), status=str(row.status),
                status_key=str(row.status_key), expires_at=row.expires_at,
            )
            for row in page.items
        ]

    return load


def _make_consumer(manager: ConnectionManager) -> ChatService:
    """问数链消费面＝生产装配镜像：semantics 公开读口喂 ChatService＋真
    QueryStore 执行缝（agg fixture 行见 _load_agg_fixture）；其余缝中性桩。"""
    semantics = SemanticsService(manager, SecurityService(manager))

    async def config_loader() -> RetrievalConfigFace:
        return DEFAULT_CONFIG

    async def faq_matcher(_question: str) -> None:
        return None

    async def faq_searcher(_question: str, _top_k: int) -> list[Any]:
        return []

    async def index_searcher(_question: str) -> list[Any]:
        return []

    async def index_searcher_dual(
        _question: str, _k1: int, _k2: int,
    ) -> tuple[list[Any], list[Any]]:
        return ([], [])

    async def waterline_loader() -> WaterlineFace:
        # E2 判定缝替身（水位读面真值归 M-05a/E2——本票验证面是 N7.1 声明消费，
        # 水位给「昨天达标」面让链走到执行站；不触 water_line 表）。
        return WaterlineFace(
            layer="汇总层", data_date=now().date() - timedelta(days=1),
            promise="T-1", tag="达标（承诺 T-1）", late_days=0,
        )

    return ChatService(
        manager,
        audit=None,
        config_loader=config_loader,
        metrics_loader=_metrics_loader(semantics),
        terms_loader=_terms_loader(semantics),
        faq_matcher=faq_matcher,
        faq_searcher=faq_searcher,
        index_searcher=index_searcher,
        index_searcher_dual=index_searcher_dual,
        graph_searcher=None,
        anchor_loader=None,
        completer=None,
        query_executor=QueryStore(manager).execute_plan,  # M-06 取数缝（main.py 同款）
        waterline_loader=waterline_loader,
    )


async def _run_query_chain(service: ChatService, question: str) -> list[Any]:
    """真装配层＋真链体（确定性解析面——零模型调用）：_assemble 六路匹配器
    全扫（真读口）→ query_chain 状态机六站。"""
    assembly = await service._assemble(question, [])
    ctx = d.ChainContext(
        run_id="run-s01seed", question=question, actor_who=_ACTOR, assembly=assembly,
    )
    return [event async for event in chains_mod.query_chain(service._deps, ctx)]


def _node_notes(events: list[Any]) -> list[str]:
    return [str(e.data.get("note") or "") for e in events if e.event == "node"]


def _answers(events: list[Any]) -> list[dict[str, Any]]:
    return [dict(e.data) for e in events if e.event == "answer"]


# ---------- ① 双向＋幂等（真迁移程序化执行） ----------


class TestSeedLifecycle:
    async def test_upgrade_idempotent_downgrade_restores(
        self, pg_db: ConnectionManager,
    ) -> None:
        """upgrade→重放幂等→downgrade 复原空表态→再 upgrade 种子回场（双向）。"""
        url = _isolated_url()
        await _seed_down(url)  # 归零态（fixture 已归零——此处冗余归一，防顺序耦合）
        assert await _seed_counts(pg_db) == (0, 0, 0)

        await _seed_up(url)
        assert await _seed_counts(pg_db) == (5, 6, 11)  # 指标 5＋术语 6＋版本轴 11
        await _seed_up(url)  # 重放（幂等——ON CONFLICT DO NOTHING 不翻倍）
        assert await _seed_counts(pg_db) == (5, 6, 11)

        await _seed_down(url)  # downgrade：种子行删净、表结构与九表原样保留
        assert await _seed_counts(pg_db) == (0, 0, 0)
        async with pg_db.readonly() as session:
            nine = await session.execute(text("SELECT count(*) FROM sem_version"))
            assert nine.scalar() is not None  # 九表结构在（不删表）
        await _seed_up(url)  # 再 upgrade——双向复原
        assert await _seed_counts(pg_db) == (5, 6, 11)


# ---------- ② 投影保真（本体权威定义逐字对照——T1 审查项机检化） ----------


def _glossary_entries() -> dict[str, dict[str, Any]]:
    raw = (_ONTOLOGY_BOHAI / "glossary-model.yaml").read_text(encoding="utf-8")
    return {str(e["id"]): e for e in yaml.safe_load(raw)["terms"]}


def _m1_attributes() -> dict[str, dict[str, Any]]:
    raw = (_ONTOLOGY_BOHAI / "m1-object-model.yaml").read_text(encoding="utf-8")
    for agg in yaml.safe_load(raw)["aggregates"]:
        if str(agg["id"]) == "AGG-BOHAI-002":
            return {str(a["name"]): a for a in agg["attributes"]}
    raise AssertionError("M1 AGG-BOHAI-002 缺失")


def _anchor_id(source: str) -> str:
    return source.split("glossary-model.yaml ")[1].split("（")[0]


class TestSeedProjectionFidelity:
    async def test_terms_verbatim_against_glossary(self, pg_db: ConnectionManager) -> None:
        """术语 6 条：term/def/status/owner 与 GLS 权威定义逐字一致（锚在 source）。"""
        url = _isolated_url()
        await _seed_down(url)
        await _seed_up(url)
        entries = _glossary_entries()
        async with pg_db.readonly() as session:
            rows = (
                (await session.execute(
                    text("SELECT id, term, type, def AS def_text, status, status_key, "
                         "owner, source FROM sem_term ORDER BY id")
                )).all()
            )
        assert [r.id for r in rows] == _TERM_IDS
        for row in rows:
            entry = entries[_anchor_id(str(row.source))]
            assert row.term == entry["term"]
            assert row.def_text == entry["definition"]  # 逐字对照（防投影失真）
            assert row.status == entry["status"]
            assert row.status_key == entry["status"]  # GLS status 串即六值键（映射直同）
            assert row.owner == entry["owner"]
        assert {r.term for r in rows} == {
            "躺井", "剔检产量", "有效产量", "时率", "递减增油", "存水率",
        }

    async def test_metrics_names_slots_bindings_against_m1(
        self, pg_db: ConnectionManager,
    ) -> None:
        """指标 5 条：name＝M1 label 逐字、slot＝剥法纯名（三键合 MEASURE_COLUMNS）、
        绑定列注记在场、未绑定两行如实标注「暂不可出数」。"""
        url = _isolated_url()
        await _seed_down(url)
        await _seed_up(url)
        attrs = _m1_attributes()
        async with pg_db.readonly() as session:
            rows = (
                (await session.execute(
                    text("SELECT id, name, mark, slot_name, def AS def_text, unit, "
                         "ambiguous, calibers, default_caliber, source "
                         "FROM sem_metric ORDER BY id")
                )).all()
            )
        assert [r.id for r in rows] == _METRIC_IDS
        by_slot = {r.slot_name: r for r in rows}
        # name＝M1 label 逐字；slot＝剥法纯名（剥尾括注）；单位随 label 括注。
        for row in rows:
            attr = attrs[
                str(row.source).split("AGG-BOHAI-002.")[1].split("（")[0]
            ]
            assert row.name == attr["label"]
            assert str(row.name).endswith(f"（{row.unit}）")
            assert row.mark is None  # M1 无 ★☆——不发明徽标
            assert row.ambiguous is False
        assert set(by_slot) == {"日产油量", "日产液量", "含水率", "配产量", "油压"}
        # 三键与消费面代码注册（MEASURE_COLUMNS，M-06 冻结）逐字合——出数前提。
        assert {"日产油量", "日产液量", "油压"} <= set(d.MEASURE_COLUMNS)
        # 绑定列注记（99 §2.12 agg 列／§A.2 源列）逐行在场。
        assert "agg.fct_daily_metering.oil_output" in str(by_slot["日产油量"].def_text)
        assert "agg.fct_daily_metering.liquid_output" in str(by_slot["日产液量"].def_text)
        assert "agg.fct_daily_metering.oil_pressure" in str(by_slot["油压"].def_text)
        assert "oil_production_daily.water_cut" in str(by_slot["含水率"].def_text)
        assert "oil_production_daily.plan_output" in str(by_slot["配产量"].def_text)
        # agg 未落列两行（含水率/配产量）——降级解释链兜底注记如实在场。
        assert "暂不可出数" in str(by_slot["含水率"].def_text)
        assert "暂不可出数" in str(by_slot["配产量"].def_text)

    async def test_revision_rows_carry_full_payload_snapshot(
        self, pg_db: ConnectionManager,
    ) -> None:
        """版本轴配套行（ADR-0004）：11 行 v1、payload＝全行快照（基线列除外）、
        changed_by＝迁移投影身份。"""
        url = _isolated_url()
        await _seed_down(url)
        await _seed_up(url)
        async with pg_db.readonly() as session:
            rows = (
                (await session.execute(
                    text("SELECT domain, row_id, version, payload, changed_by "
                         "FROM sem_ledger_revision ORDER BY domain, row_id")
                )).all()
            )
        assert len(rows) == 11
        assert {r.domain for r in rows} == {"metric", "term"}
        assert all(int(r.version) == 1 for r in rows)
        assert all("S-01" in str(r.changed_by) for r in rows)
        metric_payloads = [dict(r.payload) for r in rows if r.domain == "metric"]
        assert all(
            {"id", "name", "slot_name", "def", "grain", "unit", "status", "calibers",
             "version"} <= set(p) for p in metric_payloads
        )
        term_payloads = [dict(r.payload) for r in rows if r.domain == "term"]
        assert all(
            {"id", "term", "type", "def", "status", "status_key", "owner", "version"}
            <= set(p) for p in term_payloads
        )


# ---------- ③ 问数链真消费（票面验收 3——红先证据，真种子非夹具） ----------


class _AggFixture:
    """agg 星型 fixture 行（量级样本——数值只服务命中/排序断言；设定书 §A 样本
    井号；日期动态推导「上个月」窗内——不依赖运行日历）。"""

    wells: ClassVar[list[tuple[str, str]]] = [
        ("N-02", "渤南"), ("N-11", "渤中"), ("N-06", "渤西"),
    ]
    batch: ClassVar[str] = "B20260911-T3"

    @classmethod
    def dates(cls) -> list[Any]:
        last_prev = now().date().replace(day=1) - timedelta(days=1)
        return [last_prev - timedelta(days=8), last_prev - timedelta(days=7)]

    @classmethod
    def facts(cls) -> list[tuple[str, Any, str, str, str]]:
        oil = {"N-02": ("100.10", "120.20"), "N-11": ("80.30", "60.40"),
               "N-06": ("40.50", "30.25")}
        return [
            (well_id, day, oil[well_id][index], "500.00", cls.batch)
            for index, day in enumerate(cls.dates())
            for well_id, _block in cls.wells
        ]


async def _load_agg_fixture(manager: ConnectionManager) -> None:
    async with manager.session() as session:
        for day in _AggFixture.dates():
            await session.execute(text(
                "INSERT INTO agg.dim_date (date, month, quarter) VALUES (:d, :m, :q) "
                "ON CONFLICT DO NOTHING"
            ), {"d": day, "m": f"{day.year}-{day.month:02d}",
                "q": f"{day.year}-Q{(day.month - 1) // 3 + 1}"})
        for well_id, block in _AggFixture.wells:
            await session.execute(text(
                "INSERT INTO agg.dim_well (well_id, block_name, field_name) "
                "VALUES (:w, :b, '渤中油田') ON CONFLICT DO NOTHING"
            ), {"w": well_id, "b": block})
        for well_id, day, oil, liquid, batch in _AggFixture.facts():
            await session.execute(text(
                "INSERT INTO agg.fct_daily_metering (well_id, prod_date, oil_output, "
                "liquid_output, oil_pressure, batch_id, quality_flag) "
                "VALUES (:w, :d, :o, :l, NULL, :b, NULL) ON CONFLICT DO NOTHING"
            ), {"w": well_id, "d": day, "o": oil, "l": liquid, "b": batch})


class TestQueryChainRealConsumption:
    async def test_daily_oil_question_degraded_then_hit(
        self, pg_db: ConnectionManager,
    ) -> None:
        """未种子库同问句 N7.1 降级（红）→ 0018 落库后命中注册声明全链出真表卡（绿）。"""
        url = _isolated_url()
        await _seed_down(url)
        await _load_agg_fixture(pg_db)
        service = _make_consumer(pg_db)

        # —— 红：sem_metric 空——N7.1 无可绑定计量列的注册声明，降级解释链 ——
        red = await _run_query_chain(service, _QUESTION)
        red_notes = _node_notes(red)
        assert any("未命中可出数的注册声明" in note for note in red_notes)
        red_answer = _answers(red)[0]
        assert red_answer["kind"] == "alert"
        assert "未命中注册指标声明" in str(red_answer["text"])
        assert not any(e.event == "tool_call" for e in red)  # 未执行不出数

        # —— 绿：0018 种子落库（真迁移非夹具）——同问句确定性命中 ——
        await _seed_up(url)
        green = await _run_query_chain(service, _QUESTION)
        green_notes = _node_notes(green)
        assert any(
            "三要素齐：指标＝日产油量" in note and "确定性校验通过" in note
            for note in green_notes
        )
        assert not any("未命中可出数的注册声明" in note for note in green_notes)
        tool_calls = [dict(e.data) for e in green if e.event == "tool_call"]
        assert tool_calls and tool_calls[0]["name"] == "sql_query.readonly"
        assert tool_calls[0]["readonly"] is True
        assert tool_calls[0]["rows_returned"] == 3  # 排名型——3 井合计行（GROUP BY 井）
        answer = _answers(green)[0]
        assert answer["kind"] == "table"
        columns = [c["dataIndex"] for c in answer["columns"]]
        assert columns == ["well_id", "block_name", "日产油量合计（吨）"]
        assert [row["well_id"] for row in answer["rows"]] == ["N-02", "N-11", "N-06"]
        assert round(float(answer["rows"][0]["日产油量合计（吨）"]), 2) == 220.3
        # 血缘卡①：口径行消费种子 calibers 声明（非「台账未登记口径声明」占位句）。
        lineage = next(dict(e.data) for e in green if e.event == "lineage")
        caliber_line = next(
            item["value"] for item in lineage["items"] if item["key"] == "① 口径"
        )
        assert "班次合计日口径" in caliber_line
        assert "台账未登记口径声明" not in caliber_line

    async def test_term_seed_feeds_assembly_term_card(
        self, pg_db: ConnectionManager,
    ) -> None:
        """术语种子经真装配层（路 3 术语台账）出词条卡——躺井·限作业区语境随卡。"""
        url = _isolated_url()
        await _seed_down(url)
        service = _make_consumer(pg_db)
        red_assembly = await service._assemble("躺井是什么意思", [])
        assert red_assembly.term_cards == []  # 未种子——词条卡无源

        await _seed_up(url)
        green_assembly = await service._assemble("躺井是什么意思", [])
        assert [card.term for card in green_assembly.term_cards] == ["躺井"]
        card = green_assembly.term_cards[0]
        assert "停产待检泵" in card.type  # GLS aliases 展示拼装随卡
        assert "限作业区语境" in card.status_note  # 状态标注串（P1F-02 投影）
